# 📬 Anleitung: Newsletter-Eigenbetrieb (Worker + Actions + Resend)

**Stand: 24. September 2026.** Dies ist die Quelle der Wahrheit für den
Betrieb des Newsletters: Was es gibt, wer was ausführt, wie es freigeschaltet
wird, wie es betrieben wird und was man tut, wenn etwas rot wird.
Die übrigen Newsletter-Dokumente hängen daran:

| Thema | Dokument |
|---|---|
| Marke, Blöcke, QA, Betreff, Themen | [ANLEITUNG-NEWSLETTER-STUDIO.md](ANLEITUNG-NEWSLETTER-STUDIO.md) |
| Rechtstexte (Datenschutz-Abschnitt) | [NEWSLETTER-RECHTSTEXT-VORLAGE.md](NEWSLETTER-RECHTSTEXT-VORLAGE.md) |
| Mail-Weiterleitung `news@` (Cloudflare Email Routing) | [E-MAIL-WEITERLEITUNG-CLOUDFLARE.md](E-MAIL-WEITERLEITUNG-CLOUDFLARE.md) |
| Zustellbarkeits-Wache (Regeln C/B/S) | `scripts/newsletter_zustellbarkeit.py` (Regeltexte in den Befunden) |

## 1. Architektur – und warum sie diese Form hat

```
Besucher ──> /newsletter/ (Hugo, Shortcode) ──POST──> Worker abos.franksfinanzcheck.de
                                                         │  KV: Adresse + Token + Themen + Consent-Nachweis
                                                         │  (Double-Opt-In, One-Klick-Abmeldung,
                                                         │   Präferenzen, Rate-Limit, Bot-Fallen)
                                                         └─Dispatch─> GitHub Actions (Lifecycle)
                                                                        │  Bestätigungs-Mail (14 Tage)
                                                                        ▼
Besucher <──Resend API──  GitHub Actions (daily 04:30 UTC)  <──Export── Worker (x-ff-Key)
   └── Mail-Links zeigen auf den Worker:
        abmelden:  abos…/abmeldung?token=T   (One-Klick, = List-Unsubscribe)
        Themen:    abos…/praferenzen?token=T (Formular, pre-checked, ohne JS)
        Status:    abos…/status?token=T
```

Die drei Entscheide, die diese Form festlegen:

1. **Das Repo ist öffentlich.** Keine E-Mail-Adresse darf in Git landen –
   nicht als Datei, nicht als Commit-Message, nicht als Log in einem
   Screenshot. Die Adressliste lebt nur in Cloudflare KV; das Journal und
   der Status im Repo tragen **nur Hashes**.
2. **Der Worker versendet keine Mail.** Capture und Zustellung zu trennen,
   macht beide Seiten unabhängig testbar und hält das teure Ding (einen
   Sende-Aufruf) an genau einer Stelle: in den GitHub Actions.
3. **Token-Forms gehören auf den Worker, nicht in den statischen Build.**
   Hugo rendert beim Bauen; einen Query-String (`?token=…`) sieht es nie,
   und seit der Hugo-Template-Reform (≥0.146, hier 0.164) laufen
   Inline-Actions in Page-Content überhaupt nicht mehr. Eine statische
   „Abmelde“-Seite kann den Klick also nicht ausführen – sie wäre ein
   Vorgaukeln. Deshalb rendert der Worker die Journey-Seiten **pro Anfrage**
   (Token im HTML, normales POST-Formular, ohne JavaScript nutzbar) und die
   Blog-Seiten `/newsletter/{bestaetigung,abmelden,praeferenzen}/` sind
   ehrliche **Info-Seiten** (Rechtliches, Wege, Daten) mit dem
   Wegweiser „der Link in deiner Mail ist die Aktion“.

## 2. Inventar – wo was lebt

| Baustein | Ort | Secrets / Variablen | Wache |
|---|---|---|---|
| Capture-Worker | `newsletter-worker/` (deploy: `wrangler deploy`) | `GITHUB_PAT`, `EXPORT_KEY` | Wache `--brand` (Themen), C7 (Endpunkt) |
| Adressliste + Tokens | Cloudflare KV (`ABO`) | – | B2 (Export, unabhängig vom Resend-Key) |
| Digest (Bau + Versand) | `scripts/newsletter_digest.py` | – | Selftest 50, Capture-Wache `--check` |
| Mailer (Resend/SMTP) | `scripts/newsletter_versand.py` | – | Selftest 28 |
| QA der Ausgabe | `scripts/newsletter_qa.py` | – | Selftest 40 (21 Regeln) |
| Kadenz (Di/Fr-Vertrag) | `scripts/newsletter_schedule.py`, `scripts/newsletter_cadence.py` | – | Selftests 14 + site-Test |
| Studio (Marke/Themen) | `scripts/newsletter_studio.py` + `data/newsletter_studio.json` | – | Selftest 48, `--brand` |
| Zustellbarkeit | `scripts/newsletter_zustellbarkeit.py` | `RESEND_API_KEY` (optional) | Selftest 25 |
| Daily-Versand | `.github/workflows/newsletter-daily.yml` | `RESEND_API_KEY`, `NEWSLETTER_WORKER_EXPORT_KEY` | Wachen-Schritt im Lauf |
| Lifecycle (Bestätigung/Nachgang) | `.github/workflows/newsletter-lifecycle.yml` | – | – |
| Cadence-Nachholung | `.github/workflows/newsletter-cadence.yml` | – | Cadence-Selftest |
| Journal (Hashes) | `data/newsletter_journal.jsonl` | – | Zustellbarkeits-Wache S1 |
| Status (Halt/Idempotenz) | `data/newsletter_state.json` | – | Zustellbarkeits-Wache S1–S3 |
| Capture-Endpunkt (SSOT) | `hugo.toml` → `newsletterFormAction` | – | Studio `--brand`, Digest `--check` |
| Themen (Worker) | `newsletter-worker/wrangler.toml` → `THEMEN_IDS`/`THEMEN_LABELS` | – | Studio `--brand` |

## 3. Einmaliges Setup (Reihenfolge zwingend)

### Schritt 1 – Cloudflare-Worker

Eigener Cloudflare-Account (kostenlos; der Worker ist Teil des Free-Plans).

```bash
cd newsletter-worker
wrangler login
wrangler kv namespace create ABO     # Bindung: ABO (schon in wrangler.toml)
wrangler secret put GITHUB_PAT       # mit Repository-Scopes workflow+contents
wrangler secret put EXPORT_KEY       # 32+ Zeichen, zufällig (z. B. openssl rand -hex 24)
wrangler deploy
```

Die Worker-Domain (z. B. `ff-newsletter.<account>.workers.dev`) wird im
nächsten Schritt zugeordnet. `SITE_ORIGIN`, `GITHUB_REPO`,
`GITHUB_WORKFLOW`, `GITHUB_REF`, `THEMEN_IDS`, `THEMEN_LABELS`,
`BESTAETIGUNG_TAGE` stehen in `wrangler.toml` (Variablen, keine Secrets).

### Schritt 2 – CNAME auf die eigene Subdomain

Im Cloudflare-Dashboard → **DNS → Records → Record**:

| Typ | Name | Ziel | Proxy |
|---|---|---|---|
| `CNAME` | `abos` | `<worker>.workers.dev` | orange cloud (proxiert) |

TLS stellt Cloudflare automatisch für `abos.franksfinanzcheck.de` aus.
Verifizieren: `https://abos.franksfinanzcheck.de/healthz` muss
`{"ok":true,"kv":"ok"}` antworten.

### Schritt 3 – Resend-Konto und Domain-Authentifizierung

Resend (Free: 3000 Mails/Monat, 100/Tag). Seit dem SES-Modell läuft die
Authentifizierung über eine **Send-Subdomain** (Default `send.`) – die
**Apex-SPF der Zone bleibt unverändert** (kein Include an der Spitze, und
zwei SPF-Records wären ein permanenter Fehler):

1. Konto anlegen, **Sending Domain** `franksfinanzcheck.de` hinzufügen.
2. **Empfohlen: One-Click-Cloudflare-Autorisierung** (Resend → Domains →
   Domain → „DNS Setup“ → Cloudflare/„Authorize“ wählen). Resend fragt
   einmalig ein Cloudflare-API-Token mit Zone-DNS-Rechten ab und legt
   die Einträge SELBST in der Zone an – kein Abtippen, keine
   UI-Trunkatur. Resend legt an (2026, CNAME-Modell):
   - **CNAME** `send` → `send.forge.rmta.net` – die Send-Subdomain;
     SPF und Bounce-Host sitzen auf dem Ziel und werden per CNAME
     mitgeliefert.
   - **CNAME** `rsend` → `rsend.forge.rmta.net` – Resends
     Tracking-Subdomain. Bei uns **harmlos**: der Mailer schaltet
     `click_tracking`/`open_tracking` explizit aus, der Eintrag wird
     nie bedient.
   - **TXT** `resend._domainkey` → DKIM-Key (ein Eintrag, Wert beginnt
     mit `p=`).
3. **Alternativ manuell** (gleiche drei Einträge über Cloudflare →
   DNS → Records → hinzufügen; Werte 1:1 aus der Resend-Checkliste,
   DKIM als EIN Stück kopieren): CNAME `send`, CNAME `rsend`,
   TXT `resend._domainkey`. Ältere Konten können statt der CNAMEs noch
   das SES-Direktmodell verlangen (TXT `send` mit
   `v=spf1 include:amazonses.com ~all` + MX `send` mit
   `feedback-smtp.<region>.amazonses.com`) – die Wache akzeptiert
   beide Formen.
4. DMARC: bereits in der Zone (`_dmarc`, `p=reject` mit `rua`) – bleibt.
5. Verifizierung abwarten, bis Resend `verified` meldet. Die Wache
   prüft die Send-Subdomain (C2: CNAME-Ziel ODER SPF-TXT+MX), den
   DKIM-Eintrag (C3) und – mit `RESEND_API_KEY` – Resends eigenen
   Record-Status pro Eintrag (B1; offener Tracking-Record ist nur
   Hinweis, weil Tracking bewusst aus ist).

### Schritt 4 – GitHub Secrets und Variablen

Repository → **Settings → Secrets and variables → Actions**:

| Name | Art | Wert |
|---|---|---|
| `RESEND_API_KEY` | Secret | Resend-API-Key |
| `NEWSLETTER_WORKER_EXPORT_KEY` | Secret | = Worker-Secret `EXPORT_KEY` (derselbe Schlüssel, beide Seiten) |
| `NEWSLETTER_WORKER_BASE` | Variable | `https://abos.franksfinanzcheck.de` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` | optional | nur wenn `NEWSLETTER_TRANSPORT=smtp` |
| `NEWSLETTER_TRANSPORT` | Variable, optional | `smtp` (Default: `resend`) |

### Schritt 5 – Repo freischalten (der eine Schalter)

`hugo.toml`:

```toml
newsletterFormAction = "https://abos.franksfinanzcheck.de/anmeldung"
```

Dieser Wert ist **KRITISCH** im Integrity-Guard
(`scripts/integrity_guard.py`): nach der Änderung
`python3 scripts/integrity_guard.py --set-current` ausführen, damit der
Wert versiegelt ist und ein versehentliches Zurückstellen als Fund
meldet. Die Studio-Wache `--brand` beweist außerdem, dass dieser Wert auf
der festen Worker-Subdomain bleibt (die Info-Seiten benennen sie als Text)
– eine Subdomain-Änderung ohne Doku-/Seiten-Anpassung wird rot gemeldet.

### Schritt 6 – Vor der Freigabe: alles messen

```bash
python3 scripts/newsletter_zustellbarkeit.py --pruefen     # C1–C7, B0–B3, S1–S3
python3 scripts/newsletter_digest.py --check               # Capture-Wache (N-Regeln)
python3 scripts/newsletter_studio.py --brand               # Marke + Themen + Worker-Basis
```

Erst wenn die Zustellbarkeits-Wache keine `fund` meldet, ist die
Absender-Domain bereit (SPF+DKIM+DMARC live).

### Schritt 7 – Testlauf (noch nicht an die Liste)

Workflow **Newsletter-Daily** → *Run workflow* → `test_adresse`:
`probe@eigene-domain.de`. Ergebnis muss lauten
`✅ TESTVERSAND ERFOLGT: 1 Adresse(n)` – die Mail kommt, Abmelde- und
Themen-Links führen auf die Infoseiten (ohne Token), `--check` bleibt grün.

### Schritt 8 – Freigabe (erste Live-Ausgabe)

Derselbe Workflow ohne `test_adresse` (oder am nächsten regulären
Versandtag, Di/Fr 04:30 UTC). Bei 0 Abonnenten sendet der Listen-Versand
ehrlich nichts und sagt es (`B2 … 0 aktive Abonnenten (leer –
Normalzustand vor der Freischaltung)`).

## 4. Betrieb – was läuft wann

| Uhr (UTC) | Workflow | Was passiert |
|---|---|---|
| Di & Fr 04:30 | `newsletter-daily.yml` | Wachen (Zustellbarkeit mit Netz, Selftests, Capture) → Digest-Bau → QA → **nur an die Liste**, wenn Versandtag + kein Halt; Status-Commit (State + Journal, nur Hashes) |
| Di & Fr 08:11 | `newsletter-cadence.yml` | Vorfall-Erkennung: lief der tägliche Versand nicht / rot? → Nachhol-Trigger (08:11 UTC = 10:11 MESZ, nach dem Soll-Termin; `planmaessig` = Ruhe am Ruhtag) |
| stündlich :17 | `newsletter-lifecycle.yml` | Nachgang: Bestätigungs-Mails, deren Worker-Dispatch fehlgeschlagen ist (idempotent über Token) |
| manuell | `newsletter-lifecycle.yml` | `aktion=bestaetigung` + `token` (einzelne Bestätigung neu) bzw. `aktion=nachgang` |
| manuell | `newsletter-daily.yml` | `test_adresse` für jeden Probelauf |

Der **Halt** (`versand_unklar` im `data/newsletter_state.json`) blockiert
jeden Listen-Versand, wenn ein Sende-Aufruf ohne belegbares Ergebnis
geblieben ist. Auflösen ist eine **Menschenaufgabe**: zuerst in den
Transport-Logs/Postfächern nachsehen (Journal trägt nur Hashes – der
Beleg steht bei Resend unter *Emails*), dann den Block
`versand_unklar` aus der Statusdatei entfernen und committen. Ein Test-
versand ist vom Halt ausdrücklich **ausgenommen** – er ist die Suche
nach dem Beleg, keine zweite Liste.

## 5. Die Journey – der Weg eines Besuchers

1. **Anmeldung** (`/newsletter/`, Formular POSTet auf den Worker):
   Validierung, Consent-Pflicht, Bot-Fallen (Honigtopf + Zeitfalle,
   still), Rate-Limit pro IP, Themen-Filterung. Die Adresse steht `pending`
   in KV, die Bestätigungs-Mail kommt über den Lifecycle-Workflow.
2. **Bestätigung**: Link in der Mail → `abos…/bestaetigung?token=T`
   (servergerendert, ein Klick, auch ohne JavaScript). Der Link ist
   **14 Tage** gültig; danach meldet die Seite ehrlich „abgelaufen“
   (410) und die Anmeldung ist neu zu starten.
3. **Empfang**: jede Ausgabe trägt pro Empfänger echte Links:
   **Abmelden** (`/abmeldung?token=T`, GET = One-Klick, identisch mit dem
   List-Unsubscribe-Header) und **Themen ändern**
   (`/praferenzen?token=T`, Auswahl pre-checked, gilt ab der nächsten
   Ausgabe).
4. **Abmeldung**: sofort aus der Liste, vollständiges Löschen der
   Adresse **innerhalb von 30 Tage**. Der Einwilligungsnachweis
   (Zeitpunkt + IP, Hash-Schlüssel in KV) bleibt **bis zu 3 Jahre** –
   das verlangt Art. 7 Abs. 1 DSGVO (§ 7 UWG), nicht unser Interesse.
   Wiederanmeldung ist jederzeit möglich und bekommt ein neues Token.

## 6. Wenn etwas rot wird

| Befund / Symptom | Regel | Was es heißt | Weg |
|---|---|---|---|
| `403 … Error 1010` (Kanten-Block) | C7 / B0 | Cloudflare **Kante** blockiert den Worker bzw. die Resend-API – der Anbieter hat die Anfrage nie gesehen. Nicht als „Absender-Problem“ verallgemeinern. | Cloudflare → Security → Bots/WAF: Pfade freigeben; Wache erneut ausführen |
| `B0: Kante durchlässig, Key fehlt` | B0 | Netzweg ok, aber `RESEND_API_KEY` fehlt – Konto bewusst ungemessen (kein Grün, kein Fund) | Secret setzen, Wache erneut |
| `B0: API-Aufruf fehlgeschlagen (401/403)` | B0 | Key ungültig oder Domain nicht dem Key zugeordnet | Resend → API Keys prüfen |
| `B1: Sende-Domain nicht verifiziert` | B1 | SPF/DKIM nicht komplett live | Resend-Dashboard → Domain → Einträge vervollständigen (C1/C2/C3 nachmessen) |
| `B2: Worker-Export abgelehnt (401/403)` | B2 | `NEWSLETTER_WORKER_EXPORT_KEY` ≠ Worker-Secret `EXPORT_KEY` | Beide Schlüssel exakt abgleichen (derselbe, beide Seiten) |
| `C7: Worker-Domain löst sich nicht auf` | C7 | CNAME `abos` fehlt oder falsch | Cloudflare → DNS: CNAME auf Worker-Domain, orange cloud |
| `C7: keine Antwort / 5xx` | C7 | CNAME steht, Worker antwortet nicht / ist kaputt | Cloudflare → Workers → Logs; Stand neu deployen |
| Halt aktiv (`versand_unklar`) | S1 | Ein Sende-Aufruf ist ohne Beleg geblieben – kein zweiter Listen-Versand, bis ein Mensch nachgesehen hat | § 4 (Halt): Beleg suchen, Block auflösen, committen |
| `S3: noch kein Versand protokolliert` | S3 | Normal vor der ersten Live-Ausgabe | – |
| Bestätigung kommt nicht beim Leser | – | Spam-Ordner / Zehn Minuten / Neuanforderung | Info-Seite `/newsletter/bestaetigung/` sagt den Weg; manuell: Lifecycle `bestaetigung` + Token |
| Dieselbe Ausgabe doppelt im Postfach? | – | **Nicht möglich über den Listenweg**: Idempotenz über `letzte_ausgabe` (Datum+Betreff) und versandene Artikel-Hashes; zweiter Lauf derselben Ausgabe springt bediente Empfänger über. Ein doppeltes Anlegen über den Testweg ist möglich und ok (Testadresse, kein Subscriber) | – |
| Subdomain/Worker umgezogen | – | Studio `--brand` meldet den Widerspruch (hugo.toml vs. feste Basis) | hugo.toml + wrangler-Route + CNAME + Doku in einem Commit |

## 7. Rechtliches in Kurzform

- **Double-Opt-In** ist Pflicht (EU, § 7 UWG): erst die Mail mit Link,
  erst der Klick bringt die Adresse auf die Liste. Der Worker kennt den
  Token, nicht die E-Mail-Adresse im URL-Sinn – der Link ist persönlich.
- **Einwilligungsnachweis**: Zeitpunkt, IP, User-Agent, Consent-Stand –
  in KV unter einem Hash-Schlüssel, TTL 3 Jahre. Beweisbar, wer wann
  eingewilligt hat; überlebt die Abmeldung (muss).
- **Löschung**: Abmeldung → sofort keine Zustellung, Adresse vollständig
  in 30 Tagen. Bounces (>3 „gesendet“-Versuche) werden unterdrückt,
  nicht gelöscht (der Empfänger kann sich neu anmelden).
- **Rechtstext im Mail**: Impressum-, Datenschutz- und
  Double-Opt-In-Zeile sind QA-Pflicht (Regel Q: Rechtsbaustein fehlt im
  E-Mail → Fund). Der Datenschutz-Abschnitt der Site liest seinen
  Schaltstand aus dem Studio (`{{< newsletter_status >}}`) – er behauptet
  nie einen Zustand, den die Konfiguration nicht trägt.

## 8. Wachen und Selftests – wer bewahrt was

| Prüfung | Befehl | Wo läuft sie |
|---|---|---|
| Digest (Marken, Themen, Idempotenz, Sperre, Journal) | `python3 scripts/newsletter_digest.py --selftest` | lokal + daily-Wachen-Schritt |
| Mailer (Resend-Payload, MIME, SMTP-Sink, Bestätigung) | `python3 scripts/newsletter_versand.py --selftest` | lokal + daily |
| Zustellbarkeit (C/B/S hermetisch) | `python3 scripts/newsletter_zustellbarkeit.py --selftest` | lokal + daily |
| Studio (Marke, Kontrast, Themen, **Worker-Basis + wrangler-Themen**) | `python3 scripts/newsletter_studio.py --selftest` + `--brand` | lokal + daily |
| QA (21 Regeln der Ausgabe) | `python3 scripts/newsletter_qa.py --selftest` | lokal |
| Cadence (Di/Fr-Vertrag) | `python3 scripts/newsletter_cadence.py --selftest` | lokal |
| Worker (38 Fälle: DOIP, One-Klick, Journey-GETs, Export) | `cd newsletter-worker && node --test test/index.test.js` | lokal |
| Site-Verdrahtung (Shortcodes, Rechtstexte, Doku-Namen) | `python3 scripts/tests/test_newsletter_site.py` (+ die anderen `test_newsletter_*.py`) | lokal |
| Capture (N-Regeln gegen echten Build) | `python3 scripts/newsletter_digest.py --check` | daily |
| Zustellbarkeit **gemessen** | `python3 scripts/newsletter_zustellbarkeit.py --pruefen` | daily (mit Netz) |
| Integrity (KRITISCH-Werte, u. a. `newsletterFormAction`) | `python3 scripts/integrity_guard.py --verify` | CI |

Grundsatz aller Wachen: **Ohne Messung kein Grün.** Ein nicht
ausgeführter Check meldet `nicht gemessen`/`nicht messbar` – nie
`ok`. Und ein Zustand, den die Wache nicht kennt, wird nicht still
repariert (defekter Status bleibt defekt, Halt bleibt Halt).

## 9. Ändern ohne Bruch – was mitwas wandert

| Änderung | Muss mitwandern | Beweist es |
|---|---|---|
| Neue/andere Themenwelt | `data/themenwelten.json` → Studio-JSON `themen` → `wrangler.toml` `THEMEN_IDS` + `THEMEN_LABELS` | Studio `--brand` (deckungsgleich) + Wache N4 |
| Subdomain/Worker-URL | `hugo.toml` `newsletterFormAction`, `wrangler.toml`-Route, CNAME, `SITE_ORIGIN` | Studio `--brand` (feste Basis), C7, Capture `--check` |
| Absenderadresse | Studio-JSON `email.absender` (+ `NEWSLETTER_ABSENDER`-Var, falls abweichend) | C6 (Absender-Domain nimmt Mail an), Absender-Konfig im Mailer |
| Versand-Transport (Resend ↔ SMTP) | `NEWSLETTER_TRANSPORT`-Var (+ SMTP-Vars) | Mailer-Selftest (beide Umsetzungen), `--test-adresse`-Lauf |
| Sende-Fenster/Kadenz | `scripts/newsletter_schedule.py` (Vertrag) | Cadence-Selftest, site-Test (keine alten Versprechen), `data/newsletter_kadenz.json` |
| Sendefrequenz-Versprechen | Studio-JSON `capture.versprechen`/`newsletterPromise` | site-Test (Oberflächen deckungsgleich) |
