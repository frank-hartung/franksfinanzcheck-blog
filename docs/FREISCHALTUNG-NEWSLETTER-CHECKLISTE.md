# 📬 FREISCHALTUNG NEWSLETTER – Agentur-Runbook (Kopier-los)

**Stand: 22. September 2026.**
- ✅ Brevo-Konto, Liste `Blog-Abonnenten`, Formular `Blog-Anmeldung` (URL übernommen)
- ✅ Repo: `capture.form_action` gefüllt, Footer-CTA/Wache/Doku-Sync, neue
  *Newsletter-Wache* in der CI — PR
  [#354](https://github.com/frank-hartung/franksfinanzcheck-blog/pull/354),
  alle Checks grün (u. a. Wache am frischen Build, Playwright)
- ☐ Offen: Absender in Brevo auf `active` (Zone: SPF/DKIM/DMARC sind gemessen
  vorhanden, 23.09.2026), Secrets `BREVO_API_KEY` + `BREVO_LIST_ID` in GitHub
  (Schritt 4), AVV/DPA (Schritt 5), Testlauf (6a), `news@`-Routing-Regel
- ✅ Erledigt (23.09.2026): Versand-Kante repariert (Signatur-Blockage der
  Standard-Kennung, Fehldeutung als „Absender-Problem“, Doppelversand-Risiko bei
  Zeitüberschreitung) und die neue
  [Zustellbarkeits-Wache](NEWSLETTER-ZUSTELLBARKEIT-CLOUDFLARE-BREVO.md) im
  Versandlauf verankert

**Befehlsdokumente:**
`ANLEITUNG-NEWSLETTER.md` (Schritte 1–6, Brevo-Konto) und
`ANLEITUNG-NEWSLETTER-STUDIO.md` § 7 (Freischalten). Dieses Runbook ist nur
die Reihenfolge mit den exakten Werten aus der Studio-SSOT
(`data/newsletter_studio.json`) – keine zweite Wahrheit.

## 0. Ausgangslage (geprüft am 22.09.2026)

| Schicht | Zustand |
|---|---|
| Formular `/newsletter/`, Streifen, Footer-CTA, Journey-Seiten | ✅ gebaut, zeigt ehrlichen Leerzustand |
| § 8 Datenschutz | ✅ liest den Schaltstand aus dem Studio (`{{< newsletter_status >}}`) |
| Wache / QA / Digest / Export | ✅ `--selftest` grün, CI verriegelt |
| Versand-Cron (Di + Fr 05:05 UTC) + Kadenz-Wache (Di + Fr 08:11 UTC) | ✅ laufen; die Wache holt still verworfene Crons nach |
| **Capture** | ⚠️ **INERT** – `--check`: „kein Anmeldeweg konfiguriert“ |

Fehlt also genau das, was **außerhalb des Repos** liegt: Brevo-Konto +
Sender/DNS, Liste + Formular, zwei Secrets, eine JSON-Zeile. Kein Code-Umbau.

**Reihenfolge (wichtig):** erst 1–3 und 5 (Formular live) **dann** 4 (Secrets).
Sind die Secrets vor der Formular-Zeile da, schickt der nächste Cron eine Mail
an eine (leere) Liste – harmlos, aber sinnlos, und der Zustandsstand ändert sich.

## 1. Brevo-Konto (5 Min.)

1. [brevo.com/de](https://www.brevo.com/de/) → **Kostenlos registrieren**
   (Free-Plan, 300 Mails/Tag – reicht bis ~300 Abonnenten).
2. Absendername: **`Frank von FranksFinanzcheck`** (Studio: `email.absender.name`).
3. Konto per Mail-Link bestätigen.

## 2. Sender + DNS (≈ 10 Min.)

Brevo → **Senders → Add sender** → exakt diese Adresse:

| Feld | Wert |
|---|---|
| Absender-E-Mail | **`news@franksfinanzcheck.de`** (Studio-SSOT; der Versand-Code nutzt denselben Standard) |
| Reply-To | `kontakt@franksfinanzcheck.de` (Cloudflare Email Routing, s. `E-MAIL-WEITERLEITUNG-CLOUDFLARE.md`) |

Danach Authentifizierung per DNS (Zone `franksfinanzcheck.de`, Cloudflare) –
und die wird **nicht getippt, sondern nachgemessen**. Gemessener Stand
23.09.2026 (abgefragt per DNS-over-HTTPS): **alle vier Records sind gesetzt** –
wer nach der alten Tabelle sucht (TXT `mail._domainkey`, SPF mit Brevo-Include),
hält drei von ihnen für fehlend und greift in eine laufende Zone:

| Eintrag | Soll | Ist am 23.09.2026 |
|---|---|---|
| **Domain-Code** | TXT `@` = `brevo-code:<hash>` aus dem Brevo-Dialog | ✅ vorhanden |
| **DKIM** | **zwei CNAMEs**, nicht ein TXT: `brevo1._domainkey` → `b1.franksfinanzcheck-de.dkim.brevo.com`, `brevo2._domainkey` → `b2.…`. (Brevo nutzt TXT `mail._domainkey` nur bei manuell eingefügtem Schlüssel – die Delegation ist der Normalfall.) | ✅ vorhanden, beide CNAMEs laufen |
| **SPF** | **genau ein** TXT. Für E-Mail-Routing: `v=spf1 include:_spf.mx.cloudflare.net ~all` | ✅ `v=spf1 include:_spf.mx.cloudflare.net ~all` |
| **DMARC** | TXT `_dmarc` mit `rua=` (Berichte) | ⚠️ vorhanden, aber `p=reject; adkim=s; aspf=s` – dazu unten |

> **Korrektur (23.09.2026):** hier stand früher, der SPF-Eintrag sei um
> `include:spf.brevo.com` zu erweitern, damit der Absender „verifiziert“ werde.
> Auf Brevos geteiltem Versandweg ist das ein Blindgang: Der Return-Path bleibt
> beim Anbieter, also entsteht daraus **kein** DMARC-Alignement, und die
> Signatur der Mail kommt ohnehin aus dem schon vorhandenen Domain-DKIM.
> Das Include wird **erst** nötig, wenn eine Dedicated IP oder ein eigener
> Return-Path gebucht wird. Unbedingt bleiben darf die Regel dahinter:
> **nie zwei SPF-TXT-Einträge** – das ist ein `permerror` und betrifft dann
> *jede* Mail der Domain, auch die bisher grünen.
>
> Und die DMARC-Zeile: `p=none` wäre für den Probelauf richtig, die Zone steht
> aber auf `p=reject; aspf=s`. `aspf=s` kann auf dieser Strecke niemals alignen;
> bleibt DKIM als einziger Beleg – fällt der aus, wird **hart abgelehnt** statt
> „nur“ gefiltert. Für Probeläufe auf `v=DMARC1; p=none; aspf=r; rua=…`
> zurückstufen, nach dem Beweislauf auf `p=quarantine`. Stufenfolge und Begründung:
> [NEWSLETTER-ZUSTELLBARKEIT-CLOUDFLARE-BREVO.md](NEWSLETTER-ZUSTELLBARKEIT-CLOUDFLARE-BREVO.md).

> **AVV ist kein DNS-Eintrag**, sondern ein Vertrag – und in Brevos UI gibt es
> dafür **kein Menü**: Die DSV ist **Anhang 3 der deutschen
> [Nutzungsbedingungen](https://www.brevo.com/de/legal/termsofuse/)**
> (Version 16.10.2025) und mit dem Klick auf „Konto erstellen“ bereits
> akzeptiert. „Sichern“ heißt deshalb nur: die Seite als PDF speichern
> (Drucken → Als PDF speichern), mit Datum benennen
> (z. B. `brevo-dsv_2026-09-22.pdf`) und im Dokumentenordner ablegen.
> § 8 Datenschutz ist darauf abgestimmt.

Zustellbar wird der Absender, sobald die **Domain** in Brevo auf „verifiziert“
steht (`active: true` in `GET /v3/senders`; Brevo färbt grün, kann einige Minuten
dauern). DNS-Einträge sind dafür die Voraussetzung, nicht der Beweis – Beweis
ist der API-Status, und den liest der Zwischenschritt darunter.

**Zwischenschritt: nachmessen statt Gefühl (neu, 23.09.2026):**

```bash
python3 scripts/newsletter_zustellbarkeit.py --pruefen --strict
```

Die Wache prüft Zone (SPF-Eindeutigkeit, DKIM als TXT **und** CNAME, DMARC, MX,
Null-MX, `news@`-Routing), die Status-Datei `data/newsletter_state.json` (Halt,
wartende Artikel, Versandnachweis) und – sobald `BREVO_API_KEY` gesetzt ist
(Schritt 4) – das Konto: Absender `active`, Liste vorhanden und befüllt,
**Plan-Grenze gegen Listenstärke**, Präferenzfeld. Sie
schreibt zu jedem Befund den Klickweg, ruft **nur GETs** auf und hält bei einem
bestätigten Fund einen Listen-Versand an. Einzelfund, der sonst unbemerkt bleibt:
`news@franksfinanzcheck.de` hat **keine** Routing-Regel in Cloudflare (nur
`kontakt`) → Antworten und Rückläufer an den Absender laufen ins Leere. Abhilfe:
*Email → Routing → Routing Rules → Create rule*, Muster `news` → dieselbe
Zieladresse (bewusst keine Catch-all-Regel).

## 3. Liste + Formular (5 Min.)

1. **Contacts → Listen** → neue Liste: **`Blog-Abonnenten`** (im Ordner-Dialog
   den normalen Benutzer-Ordner wählen — bei frischen Konten „Dein erster
   Ordner“; `Conversations` und `marketing_automation` sind Brevo-Systemlisten,
   keine Ziele für die Blog-Liste).
   Die **List-ID** = Zahl in der URL (`…/lists/7` → `7`) 📌 notieren → Schritt 4.
2. **Contacts → Formulare → Create**: Name **`Blog-Anmeldung`**,
   **Double-Opt-In AN** (Pflicht), Felder **nur „E-Mail“** (Name `email` –
   die Wache N4 verlangt exakt das), Captcha gegen Bots an, Design schlicht.
   Den Text über dem Feld (optional): *„Zweimal pro Woche: Spartipps und Rechner –
   dienstags und freitags.“*
3. 📌 **Formular-URL kopieren** – die Embed-/Action-URL aus dem
   Formular-Editor (heute sieht sie aus wie `https://…sibforms.com/serve/…` –
   Brevos Formularhost-Domain, von der Wache erlaubt).
   Das ist der Wert für Schritt 5.
4. *(Für später, optional:)* **Interests** anlegen mit exakt den
   Studio-Namen, damit die Themen-Chips später ankommen:
   `Strom & Gas` · `Internet, DSL & Handy` · `Versicherungen` ·
   `Konto & Karten` · `Reisen` · `Budget & Frugalismus`.

## 4. Secrets in GitHub (2 Min.)

Repo → **Settings → Secrets and variables → Actions**:

| Name | Typ | Wert |
|---|---|---|
| `BREVO_API_KEY` | **Secret** | Brevo → oben rechts Name → *SMTP & API → API Keys → Generate* |
| `BREVO_LIST_ID` | **Secret** | List-ID aus Schritt 3 (Nicht-Nummer wie `7`) |

⚠️ **`BREVO_LIST_ID` als Variable wäre ein stiller Deaktivierer**: Der
Workflow liest `secrets.BREVO_LIST_ID`; ohne ihn streicht die Wache `--send`
und meldet nur „nur gebaut“. (Die alten Anleitungen sagten „Variable“ – das war
ein Fehler, am 22.09. korrigiert.)

Optional: Variable `NEWSLETTER_ABSENDER`, falls der Absender sich je von
`news@franksfinanzcheck.de` unterscheiden soll. Kein `BREVO_TEST_LIST_ID` /
`NEWSLETTER_TEST` – das existiert nicht; die Probe ist die Workflow-Eingabe
`test_adresse` (Schritt 6a).

## 5. Die eine JSON-Zeile — ✅ erledigt (22.09., PR #354)

`data/newsletter_studio.json` → `capture` → `form_action` ist gefüllt
(`hugo.toml` bleibt versiegelt, das JSON ist der vorgesehene Weg), die URL
bytegenau aus dem Brevo-Formular. Damit folgen **automatisch**: Inline-Formular
auf `/newsletter/`, Streifen- und Footer-CTA auf allen Inhaltsseiten, § 8
wechselt auf „Anmeldung aktiv“, die Wache meldet `aktiv` statt INERT.

## 6. Verifikation & erster Versand (in dieser Reihenfolge)

**6a. Testlauf** – zuerst die Zustellbarkeits-Wache lokal:
`python3 scripts/newsletter_zustellbarkeit.py --pruefen` (meldet pro Befund den
Klickweg; `--strict` ist das Freigabe-Gate, und im Versandlauf läuft sie vor
jedem Versand). Dann Actions → *Newsletter-Daily (Capture-Wache + Digest)* →
*Run workflow*: `test_adresse` = deine Adresse, `live` **aus**, `tage` = 7.
Erwartet: `sendTest`-Mail in deinem Postfach (Double-Opt-In-Bestätigung
inklusive, Abmeldelink funktioniert), Liste unangetastet.
Mehrere Proben: Adressen im Feld mit Komma trennen. Der Lauf schickt sie
als `emailTo`-Liste, nie als einzelnen String und nie leer (leer träfe die
ganze Testliste des Kontos).
Der Kampagnen-Payload spricht CreateEmailCampaign: `replyTo` ist die Adresse
als String (`kontakt@franksfinanzcheck.de`), nicht `{"email": "…"}`. Genau
dieses Objekt hat Lauf 35904226864 (23.09.2026) mit
`HTTP 400: ReplyTo email should be valid` abgelehnt – Test und Live, denn
beide legen zuerst die Kampagne an. Lehnt Brevo die Antwortadresse trotzdem
ab, fällt der Lauf laut auf den verifizierten Absender zurück und sendet
dennoch; Antworten landen dann bei `news@…`, bis `kontakt@…` unter
Senders & IPs als Absender steht. Ein Live-Lauf außerhalb Dienstag/Freitag
endet mit der Warnung „Versandpause“ und schickt nichts – das ist der
Vertrag, kein stiller Erfolg.
Kommt keine Mail, sagt der Lauf seit der Versand-Reparatur (23.09.) selbst,
warum – die Ursache steht in der roten Annotation und im Step-Summary:
„Digest ist leer“ (gelbe Warnung) heißt, im Zeitraum liegt kein
veröffentlichter Artikel (alles `draft: true` oder schon versandt):
`tage` vergrößern (z. B. 3) und erneut laufen lassen; „kein Absender“ heißt,
`BREVO_API_KEY`/`BREVO_LIST_ID` fehlen; „Absender … nicht verifiziert“,
„existiert im Brevo-Konto nicht“, „Liste … existiert nicht“ oder „0
Abonnenten“ heißt, Schritt 2 bzw. 3 oben ist (noch) nicht abgeschlossen –
die Vorprüfung bricht dann ab, BEVOR bei Brevo eine Kampagne entsteht
(Report: `NEWSLETTER-VERSAND-REPARATUR-2026-09-23.md`).

**6b. Freigabe** – entweder `live` **an** + `tage` = 7 manuell, oder einfach
den nächsten Cron laufen lassen (Di/Fr 05:05 UTC = 07:05 MESZ / 06:05 MEZ).
`data/newsletter_state.json` merkt sich, was draußen war – keine Dopplung.
Fällt der Cron still aus (GitHub verwirft/verschiebt `schedule`-Ereignisse
unter Last – geschehen am 23.09.), holt die **Newsletter-Kadenz-Wache**
(`newsletter-cadence.yml`, Di/Fr ~08:11 UTC) den Lauf mit derselben
Freigabestufe nach; ein FEHLGESCHLAGENER Lauf wird nicht automatisch
wiederholt, sondern per Fehler-Alerting gemeldet (Report:
`NEWSLETTER-KADENZ-ABSICHERUNG-2026-09-23.md`).

**6c. Nach dem ersten Versand** – Datenschutzerklärung gegen den tatsächlichen
Stand lesen (Wortlaut-Entwurf: `NEWSLETTER-RECHTSTEXT-VORLAGE.md`).

## 7. Zeitplan & Türe zum Ausgang

- Nächster Cron: **morgen, Mi 23.09. 05:05 UTC**. Ohne Secrets baut er nur und
  meldet – er versendet nie. Wer den ersten Versand selbst steuern will,
  macht 6a/6b vor dem Cron; wer nicht, für den *ist* der Cron der erste
  Versand (das designierte Pfade).
- **Kill-Switch:** `BREVO_API_KEY` löschen (Settings → Secrets) – der Lauf
  baut weiter, sendet nie. Alternativ Workflow deaktivieren.
- Rückbau der Freischaltung: `form_action` auf `""` – die Site fällt lautlos
  in den Leerzustand zurück, § 8 mit ihr (ein Zustand, eine Quelle).
