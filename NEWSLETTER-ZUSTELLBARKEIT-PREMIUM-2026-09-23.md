# 🛡 Newsletter-Zustellbarkeit auf Agentur-Niveau – Audit und Heilung (23.09.2026)

**Auftrag:** „Bitte prüfe die Newsletter-Einstellungen von Cloudflare und Brevo auf
Premium-Level einer Profi-Agentur und behebe sämtliche Fehler auf Premium-Level.“
**Auslöser:** Newsletter-Daily **Lauf #21** (12:16 UTC, Exit 1, Job
`107175675766`).

**Maßstab, den ich angelegt habe:** nicht „Lauf #21 wird grün“, sondern die
**Fehlerklasse** schließen. Ein grüner Lauf, der eine Kantenblockage als
Absenderproblem meldet, ist schlimmer als ein roter – er bildet Sicherheit ab,
wo keine ist. Und eine Freischalt-Anweisung, die einen DNS-Griff in eine
laufende Zone empfiehlt, der nichts ändert, ist ein Fehler im Dokument, nicht
im Feld. Deshalb bestehen die folgenden Änderungen aus drei Teilen: **Transport
reparieren**, **Zustand messbar machen** (neue Wache), **Doku-SOLL an den
gemessenen IST-Wert annähern**.

---

## 1. Was Lauf #21 tatsächlich war

```
Digest-Versand fehlgeschlagen (Exit 1) – es ist nichts versandt.
❌ Vorprüfung fehlgeschlagen: Absender-Vorprüfung nicht möglich (HTTP 403:
{"type":"https://developers.cloudflare.com/support/troubleshooting/http-status-codes/
cloudflare-1xxx-errors/error-1010/","title":"Error 1010: Access denied","status":403,
"detail":"The site owner has blocked access based on your browser's signature.", …})
```

Drei Fehler in dieser einen Meldung, und keiner war ein Brevo-Kontofehler:

| # | Fehler | Klasse | Schwere |
|---|---|---|---|
| 1.1 | Der Client sandte die Standardkennung `Python-urllib/3.11` (kein `User-Agent` gesetzt). Brevos Cloudflare-Kante filtert genau die – **vor** jeder Authentifizierung. Der API-Key wurde in diesem Lauf nie gelesen. | Config/Transport | blockierend |
| 1.2 | `brevo_fehler()` stempelt jeden Nicht-2xx als „Absender-Vorprüfung nicht möglich“ → **falscher Adressat**: ein Mensch sucht im Brevo-Konto, das an diesem Tag nichts falsch machte. | Diagnose | schwer (Zeitfresser, Kelasentarnung) |
| 1.3 | `_mit_wiederholung()` wiederholte auch **POSTs** bei 429/5xx bis zu dreimal. Auf `/emailCampaigns/{id}/sendNow` heißt das: dieselbe Ausgabe bis zu dreimal an die ganze Liste – bei einem Netz-Timeout, nicht bei einem Fehler. | Datenverlust-Risiko | kritisch |

Dazu, unabhängig vom Lauf, zwei weitere Klassen, die die Prüfung der
„Einstellungen“ zutage förderte:

| # | Befund | Klasse | Schwere |
|---|---|---|---|
| 1.4 | Doku (Checkliste + `ANLEITUNG-NEWSLETTER.md`) schrieb: „SPF um `include:spf.brevo.com` erweitern, dann ist der Absender authentifiziert“. Auf Brevos geteiltem Weg bleibt der Return-Path beim Anbieter → kein SPF-Alignement; das Include ändert an der Zustellung nichts, ein **zweiter** SPF-TXT hätte dagegen die ganze Domain auf `permerror` gesetzt. | falsche Anweisung | schwer (aktiver Schadenspfad) |
| 1.5 | `data/newsletter_state.json`-Schreibpfad nach Versand lief nur bei Erfolg; ein Abbruch nach angenommenem `sendNow` hinterließ keinen Halt → nächster Lauf konnte dieselben Artikel erneut senden (Duplikat) oder der Zustand blieb unbeweisbar. | Fehlertoleranz | mittel |

---

## 2. Heilung im Transport (`scripts/newsletter_digest.py`)

* **Eigene, ehrliche Client-Kennung.** `franksfinanzcheck-newsletter/1.1
  (+https://franksfinanzcheck.de/; Brevo-REST-v3; GitHub-Actions)`; bei
  Kanten-Blockage Wechsel auf eine zweite Kennung
  (`Mozilla/5.0 (compatible; …)`) – Selbstauskunft, **kein** Browser-Imitat.
  Ein gespieltes Browser-Fingerprint wäre Betrug an der Kante und beim nächsten
  strengeren Filter wieder eine Störung.
* **`kanten_block()`** trennt Kante von Anbieter: HTTP 403/406/429/503 mit
  Nicht-JSON-Leib bzw. Cloudflare-Marken (`error code: 1010`, `cf-ray`,
  `cloudflare`) = „Brevo hat die Anfrage nie gesehen“; JSON mit `code`/`message`
  = echte Anbieter-Absage. Die Meldung nennt jetzt Ursache + nächsten Schritt
  (Kennung beim Support zur Freigabe nennen, oder aus anderem Egress-Netz
  starten) statt „Absender prüfen“.
* **`_mit_wiederholung()`: lesen = wiederholen, schreiben = niemals.**
  Ein `POST …/sendNow` mit verlorengegangener Antwort wird nicht wiederholt,
  sondern **nachgelesen**: `versand_nachlesen()` zieht `GET
  /emailCampaigns/{id}` und entscheidet nach `status`/`statistics`:
  * belegt → „✅ VERSAND ERFOLGT (Kampagne N)“, Duplikatsschutz wird trotzdem
    geschrieben, Exit bleibt 1 (eine unbezeugte Kette ist ein Befund);
  * widerlegt (kein Versand) → normaler Fehlerpfad;
  * **nicht entscheidbar** → Halt.
* **Versand-Halt (`versand_unklar`)** in `data/newsletter_state.json`,
  geschrieben von `sperre_setzen()`; `sperre_pruefen()` blockiert jeden
  **Listen**-Versand (Testversand über `test_adresse` bleibt möglich) und
  `main()` meldet ihn vor jedem Build:
  „🛑 Der Versand ist angehalten: … Erst in Brevo nachsehen (Kampagnen →
  Detail → Sends) und den Block auflösen.“ Aufheben kann ihn nur ein Mensch
  (Block löschen oder `versand_unklar_geloest: <ISO>`) – **kein CLI-Override**,
  damit ein automatischer Lauf sich nie selbst freischaltet.
* **Host-Guard** `api_host_fehler()`: `BREVO_API_HOST` nur für Brevos eigene
  Domains; ein fremder Host würde den `api-key`-Header mitnehmen → Befund statt
  Netzversuch.
* Alles existierende blieb: Fail-Closed-Vorflug (`vorflug()`), 20-QA-Regeln,
  Duplikatsschutz (gleicher Artikel/derselbe Betreff), `NEWSLETTER_SEND`-Triple,
  DO-Liste nie automatisiert angefasst.

**Testabdeckung:** 55 Selbsttest-Fälle (u. a. „Kante vs. Konto“,
„Identitätsleiter“, „GET wird wiederholt, POST nie“, „Nachlese statt
Wiederholung“, „Halt blockiert Liste, nicht Test“), dazu die Unit-Fälle in
`scripts/tests/test_newsletter_digest.py` (27). Der alte Fall, der die
POST-Wiederholung *verlangte*, wurde durch `test_lesen_wird_wiederholt_schreiben_niemals`
ersetzt – er hätte den Doppelversand-Bug festgeschrieben.

---

## 3. Neue Wache: `scripts/newsletter_zustellbarkeit.py`

Sie prüft die beiden Schichten, die bisher nirgends gemessen wurden, **read-only**
(DoH für DNS, ausschließlich `GET` für die Brevo-API) und meldet pro Befund Ist,
Soll, Klickweg und Begründung. 40 Selbsttest-Fälle, netzfrei, hängen im
Governance-Minimum (`scripts/governance_contract.py`, GUARDS → C6).

| Regel | Prüft | Fund nur wenn |
|---|---|---|
| C0 | DNS-Messlücke – **welche** Abfrage blind war | die übrigen Schichten laufen weiter; nie pauschales „nichts geprüft“ |
| C1/C2 | SPF: genau ein Eintrag, Routing-Include drin; Brevo-Include fehlt → **Hinweis** mit Begründung | 0 oder ≥2 SPF-TXT |
| C3 | DKIM als TXT **und** als `brevo1`/`brevo2`-CNAME-Delegation; halbe Lage = Hinweis | nichts gemessen und nichts gefunden |
| C4 | `brevo-code`-TXT (Eigentumsnachweis) | fehlt |
| C5…C5e | DMARC: Policy, `p=` schärfer als die Belege, `aspf=s` auf geteilter Strecke, `adkim=s` ohne DKIM, `rua` fehlt, `pct` | Policy > Beleglage |
| C6/C7 | MX/Reply-To-Briefkasten, Null-MX-Falle, `news@`-Routing-Regel | Reply-To läuft ins Leere |
| B0 | Netzweg/Kantenblockage (403 + Signaturfilter-Marke = Kante, nicht Konto) | Blockage oder Netzfehler **mit** Key |
| B1…B4 | Absender `active`, Liste + Abonnentenstand, **Plan-Grenze gegen Listenstärke**, inertes Themenfeld | Absender inaktiv, Liste 404, Liste > Tageskontingent |
| S1…S3 | Versand-Halt, wartende Artikel, fehlender Versandnachweis | Halt aktiv |

Bewusste Lücken (nicht als „geprüft“ verbucht, im Runbook dokumentiert):
Bot Fight Mode, Security Level, WAF-Regeln, Email-Routing-Regelsatz, DNSSEC,
Double-Opt-In pro Formular, Präferenzfeld im Konto.

---

## 4. Der gemessene Ist-Zustand der Zone (DoH, 23.09.2026)

```
TXT @        v=spf1 include:_spf.mx.cloudflare.net ~all          ✅ (einer)
TXT @        brevo-code:81fd84cb3fdce1639e158278d0d75cb1          ✅
CNAME brevo1._domainkey → b1.franksfinanzcheck-de.dkim.brevo.com. ✅
CNAME brevo2._domainkey → b2.franksfinanzcheck-de.dkim.brevo.com. ✅
TXT _dmarc   v=DMARC1; p=reject; adkim=s; aspf=s;
              rua=mailto:215c…@dmarc-reports.cloudflare.net; ⚠️ Schärfe ohne Not
MX @         41 route1 / 17 route2 / 3 route3 .mx.cloudflare.net. ✅
TXT spf.brevo.com  v=spf1 ip4:185.41.28.0/22 … -all               ✅ Include-Ziel gültig
```

**Korrekturen an meinem eigenen früheren Befund** (die hier stehen, damit sie
nicht nochmal als Wahrheit umlaufen):

* „Brevo-DKIM fehlt“ ist **falsch**. Es existiert als die zwei
  `brevo1`/`brevo2._domainkey`-CNAMEs; eine reine TXT-Selektorsuche
  (`mail`, `default`, `s1`, `k1`, `dkim`) übersieht die Delegation. Genau dieser
  Fehler steckt jetzt als `C3`-Doppelabfrage in der Wache.
* Der Vorflug-Befund des Digests schrieb „SPF/DKIM auf ‚verifiziert‘ bringen“ –
  die SPF-Hälfte ist gestrichen (er alignt auf dieser Strecke nie); die Meldung
  verweist jetzt auf `brevo-code`-TXT und die zwei DKIM-CNAMEs.
* Die Zone ist für die Website **DNS only** (CNAME → `frank-hartung.github.io`),
  es sitzt also **kein eigener Cloudflare-Proxy** vor dem HTTP-Pfad; die
  403/1010 kam von **Brevos** Kante, nicht von unserer Konfiguration. Unsere
  Cloudflare-Sicherheitseinstellungen sind für den API-Weg irrelevant.
* Offene Konto-Frage, aus dieser Laufumgebung **nicht** entscheidbar (TLS zu
  `api.brevo.com` hier geblockt): steht `news@franksfinanzcheck.de` in Brevo auf
  `active`? Das ist der einzige echte Kandidat für „Vorprüfung schlägt fehl“ –
  und der erste Lauf mit gesetztem `BREVO_API_KEY` beantwortet ihn (B1).

Verdikt der Wache auf diesem Repo (Live-Lauf, DoH zeitweise instabil):
`fund 1 (B0, Sandbox-Ausgang) · hinweis 4 (C2, C5b aspf=s, C7 news@-Regel, S3
kein Versandnachweis) · info 1 (S2, 2 Artikel pending) · nicht messbar 2 · ok 5`.

---

## 5. Was ein Mensch tun muss (bewusst nicht automatisiert)

1. **Brevo → Senders, Domains & Dedicated IPs → Domains**: Domain
   `franksfinanzcheck.de` auf `active` setzen (der `brevo-code`-TXT liegt; es
   fehlt allenfalls der Klick „Verify“). Kontrolle: `GET /v3/senders` oder
   `python3 scripts/newsletter_zustellbarkeit.py --pruefen`.
2. **Cloudflare → Email → Routing → Routing Rules → Create rule**: Muster
   `news` → dasselbe Ziel wie `kontakt`. Ohne diese Regel sind Antworten und
   Rückläufer an den Absender weg (C7, Hinweis).
3. **DMARC entschärfen, bis ein Beweislauf da ist**: `p=reject; aspf=s` ist auf
   dieser Strecke Schärfe ohne zweiten Beleg. Für Probeläufe
   `v=DMARC1; p=none; aspf=r; rua=…`, danach `p=quarantine`; `p=reject` erst mit
   vier Wochen sauberer Berichte. Stufenfolge: Runbook § 3.
4. **Präferenzfeld im Konto anlegen** (sonst bleiben die Themen-Chips der Site
   Dekoration): Brevo → Contacts → Attributes → `attributes[THEMEN]` (o. ä.),
   dann `data/newsletter_studio.json` → `capture.feld_themen` auf genau diesen
   Namen. Die Wache meldet den Ist-Zustand als B4-Hinweis, die UI der Site ist
   **unverändert** geblieben (kein Feld erfinden).
5. **Plan-Grenze beachten**: Free = 300 Mails/Tag. Bei > 300 bestätigten
   Abonnenten erreicht ein Werktagsversand nicht alle – der Lauf bleibt grün,
   die Hälfte bekommt nichts. B3 meldet das als Fund, sobald die API lesbar ist.
6. **Secrets**: `BREVO_API_KEY`, `BREVO_LIST_ID` als *Secrets* (nicht Variablen);
   `NEWSLETTER_ABSENDER` nur bei Abweichen vom Studio-SSOT.

---

## 6. Nachweis (alle Läufe wiederholbar)

| Prüfung | Ergebnis |
|---|---|
| `python3 -m unittest discover -s scripts/tests` | **722 Tests OK** (skipped 21) – Basis vorher: 701, also +21 neue Fälle |
| `python3 scripts/newsletter_digest.py --selftest` | ✅ 55 Fälle grün |
| `python3 scripts/newsletter_zustellbarkeit.py --selftest` | ✅ 40 Fälle grün |
| `python3 scripts/governance_contract.py` (voll) | 🔒 erfüllt – alle 18 Regeln, inkl. C6 mit der neuen Wache |
| `python3 scripts/newsletter_zustellbarkeit.py --pruefen` | läuft, meldet Befunde + Lücken wie in § 4 |
| `.github/workflows/newsletter-daily.yml` + `scripts/tests/test_workflow_yaml.py` | 6/6 OK (Schritt-Namen, Struktur) |
| Doku ↔ Code | neuer Fall `test_doku_und_vorflug_nennen_dieselbe_authentifizierungslehre`: weder die Anleitungs-/Checklistentexte noch der Vorflug-Befund dürfen den Betreiber zum SPF-Eintrag schicken, und die Wache muss in beiden verlinkt sein |

Der Workflow ruft die Wache **vor** dem Versand auf und lässt die
Zustands-Kommitierung nur laufen, wenn der Job nicht abgebrochen wurde
(`if: always() && !cancelled()`); die Annotation unterscheidet jetzt drei Äste:
`UNKLAR` (Nachlese nötig), `VERSAND IST RAUS` (Kampagnennummer belegt),
`nichts versandt`.

---

## 7. Doku-Änderungen

* `docs/FREISCHALTUNG-NEWSLETTER-CHECKLISTE.md` – § 2 in eine Soll/Ist-Tabelle
  mit gemessenem Stand 23.09.2026 umgebaut (Domain-Code, DKIM als zwei CNAMEs,
  SPF, DMARC), SPF-Merge-Anweisung als **korrigiert** gekennzeichnet, neuer
  Zwischenschritt „nachmessen statt Gefühl“, `news@`-Routing-Regel, DMARC-
  Rückstufung vor Probeläufen, 6a um den Wache-Aufruf ergänzt.
* `docs/ANLEITUNG-NEWSLETTER.md` – § 2 (Absender) auf die gemessene Wahrheit
  umgestellt, Probelauf-Schritt 4 „Zustellbarkeit messen“ ergänzt.
* `docs/E-MAIL-WEITERLEITUNG-CLOUDFLARE.md` – SPF-Bullet entwirrt (kein
  Brevo-Include-Zwang, keine zwei Einträge), `news@`-Regel, MX-Hinweis.
* **neu** `docs/NEWSLETTER-ZUSTELLBARKEIT-CLOUDFLARE-BREVO.md` – das Runbook:
  Klassentrennung, Zonentabelle Ist/Soll, DMARC-Stufen, was die API nicht hergibt,
  Abnahme-Kopierblock.
* `scripts/governance_contract.py` – neue Wache in `GUARDS` (mit Begründung, warum
  sie dort hingehört).

## 8. Was ich nicht angefasst habe (und warum)

* **Kein DNS-Schreibvorgang, kein POST an Brevo, kein Release eines Versands.**
  Zone, Konto und Freigabe bleiben Betreiberentscheidungen; die Wache misst nur.
* **Die Anmelde-UI** (`layouts/shortcodes/newsletter_form.html`,
  `static/premium/ff-newsletter.js`) – die Themen-Chips haben keinen Empfänger im
  Konto; ein Feld zu erfinden, das Brevo nicht annimmt, wäre eine neue Lüge.
  B4 + Schritt 5 oben sind der Weg, das ehrlich zu schließen.
* **DO-Listenbehandlung** – Bestätigungsstrecke bleibt unverändert streng.
* **Cron-Kadenz** (Mo–Fr 05:05 UTC) und `newsletter-cadence.yml` – der Watchdog
  für ausgefallene Läufe ist unabhängig von diesem Befund und unverändert grün.
