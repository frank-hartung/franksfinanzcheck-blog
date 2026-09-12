# 📬 ANLEITUNG: Vollautomatisierter Newsletter (Brevo, kostenlos)

An Werktagen um 07:05 (MESZ) baut der Blog **eine** Mail mit den Artikeln des
Tages – Double-Opt-In, Abmeldelink, kein manueller Eingriff. Diese Anleitung:
einmalig ca. 15 Minuten (danach nie wieder anfassen).

**Stand 12.09.2026 – was im Repo schon liegt und was noch fehlt.** Repo-seitig
ist alles gebaut: Anmeldeseite `content/newsletter/` (Shortcode
`layouts/shortcodes/newsletter_form.html`), Bau + Versand + Duplikatsschutz
`scripts/newsletter_digest.py`, Workflow `.github/workflows/newsletter-daily.yml`
(Cron Mo–Fr 05:05 UTC), und eine Wache, die den Leerzustand laut meldet, statt
ihn für grün zu halten. Es fehlen ausschließlich die drei Klicks in deinem
Brevo-Konto (Schritte 1–4) und der Datenschutz-Block (Schritt 5). Bis dahin ist
die Anmeldeseite NoIndex, der Footer-Button unsichtbar und der Workflow inert.

## Wichtig vorab (Recht, DE)

✅ Double-Opt-In (Brevo-Standard, das gehört so) · ✅ Abmeldelink in jeder Mail
(automatisch `{{ unsubscribe }}`) · ✅ Impressum + Datenschutz-Links in jeder Mail
(eingebaut) · ☐ Datenschutzerklärung um Newsletter-Punkt erweitern (Textbaustein
unten) · ☐ Website: Datenschutz/AVV prüfen (Brevo bietet AVV in den Einstellungen).

## 1. Brevo-Konto (5 Min.)

1. [brevo.com/de](https://www.brevo.com/de/) → **Kostenlos registrieren** (Free-Plan,
   300 Mails/Tag – ausreichend bis ca. 300 Abonnenten täglich)
2. Absendername eingeben: `Frank von FranksFinanzcheck` · E-Mail (vorläufig):
   deine private Mail **ODER** `kontakt@franksfinanzcheck.de` (s. Schritt 2)
3. Konto bestätigen (Mail-Link), Fragebogen überspringen/simply fill.

## 2. Absender-Adresse (profi = eigene Domain, ~10 Min.)

**Empfohlen (kostenlos): Zoho Mail Free** für `kontakt@franksfinanzcheck.de`
(beim Domain-Anbieter MX-Einträge setzen – Wizard führt dich).
Dann in Brevo: **Senders → Add sender** → `kontakt@franksfinanzcheck.de`
und die **Authentifizierung** (SPF + DKIM) per DNS-Einträgen abschließen
(Brevo zeigt exakt die Werte; beim Anbieter in die DNS-Zone eintragen).
→ bessere Zustellbarkeit + „professioneller Absender".
*(Notlösung: private Mail bleibt, funktioniert – aber weniger schick.)*

## 3. Empfängerliste + Formular (5 Min.)

1. Brevo → **Contacts → Listen** → neue Liste: `Blog-Abonnenten`
   → Die **ID** ist die Zahl in der URL (z. B. `…/lists/7` → ID `7`) 📌 notieren!
2. **Contacts → Formulare → Create**: Name „Blog-Anmeldung", **Double-Opt-In**
   AN (Pflicht!), Felder nur „E-Mail", Design schlicht, Captcha gegen Bots an.
   → Beim Speichern bekommst du eine **gehostete Formular-URL**
   (https://…sendinblue.com/… bzw. …brevo.com/…) 📌 notieren! Das ist der Wert für
   `newsletterFormAction` (Inline) bzw. `newsletterFormUrl` (Button) in Schritt 4.

## 4. GitHub hinterlegen (2 Min.)

Repo → **Settings → Secrets and variables → Actions**:
- Secret: **`BREVO_API_KEY`** (Brevo → oben rechts Name → *SMTP & API → API Keys → Generate*)
- Variable: **`BREVO_LIST_ID`** = Listen-Zahl aus Schritt 3
- (optional) `BREVO_TEST_LIST_ID` + `NEWSLETTER_TEST=1` → sendet nur an dich zur Probe
- (optional) `BREVO_SENDER_EMAIL` = `kontakt@franksfinanzcheck.de`

**Anmeldeweg auf der Website sichtbar machen** – zwei Varianten, beide in
`hugo.toml` unter `[params]`, der Shortcode entscheidet in dieser Reihenfolge:

| Parameter | Wirkung |
|---|---|
| `newsletterFormAction` | echtes Inline-Formular auf `/newsletter/` (POST an die gehostete Brevo-Formular-URL, Feld `email`) – Leser verlässt die Seite nicht |
| `newsletterFormUrl` | Button, der das gehostete Brevo-Formular in neuem Tab öffnet |
| `newsletterPromise` | der Satz über dem Feld („eine Mail pro Werktag …") |

Sobald eines der beiden Felder gefüllt ist: Footer-CTA auf allen Inhaltsseiten,
Formular auf `/newsletter/`, und die Wache verlangt zusätzlich den
Datenschutz-Abschnitt (Schritt 5) – zu Recht, denn ab jetzt werden Adressen
gesammelt. Beides leer = nichts sichtbar, kein toter Button.

## 5. Datenschutz-Block zuerst (Pflicht, bevor das Formular läuft)

`content/datenschutz/index.md`, Abschnitt 8, behauptet derzeit: *„Diese Website
bietet derzeit keinen Newsletter an."* Das muss weg, sobald Adressen angenommen
werden – fertiger Text inkl. Doppel-Opt-In-Nachweis, Speicherdauer und Widerruf in
`docs/NEWSLETTER-RECHTSTEXT-VORLAGE.md`. Die Wache meldet den Widerspruch, solange
das Formular aus ist (Hinweis), und als harten Fund, sobald es an ist.

## 6. Probelauf

Actions → **Newsletter-Daily (Capture-Wache + Digest) → Run workflow**:

1. ohne etwas anzukreuzen starten → der Lauf zeigt nur, was die Wache sieht (INERT oder
   Konfigurationsbefunde) und baut den Digest nach `/tmp`.
2. `test_adresse` = deine Adresse, `live` **aus** → Testversand über Brevo
   (`sendTest`), die Liste wird nicht angefasst.
3. `live` **an** + `tage=1` → echter Versand an die Liste; der Digest merkt sich
   die Artikel in `data/newsletter_state.json` und baute sie nicht noch einmal
   (deshalb ist die Datei versioniert).

Von Hand: `python3 scripts/newsletter_digest.py --check` /
`--build --days 1` / `--build --send --live`. Status: `data/newsletter_state.json`
(zuletzt_versandt, kampagne_id, versandene_artikel) und der Lauf selbst.

## ✂️ Rechtstext – Kurzform (Langfassung: docs/NEWSLETTER-RECHTSTEXT-VORLAGE.md)

> **Newsletter:** Bei Anmeldung speichern wir deine E-Mail-Adresse zur Versendung
> unseres Blogs (Tages-Digest). Rechtsgrundlage Art. 6 Abs. 1 lit. a DSGVO
> (Einwilligung). Dienstleister: Brevo (Sendinblue SAS, Frankreich; AVV abgeschlossen,
> EU-Hosting). Anmeldung per Double-Opt-In; Abmeldung jederzeit per Link in jeder
> E-Mail. Versand-Statistik (Öffnungs-/Klickraten, anonym).

## ❓ FAQ

- **Zwei Artikel in einem Tag?** Beide landen in EINER Abend-Mail (Digest). Leser-Freundlichkeit > Frequenz.
- **Anmeldezahlen sehen?** Brevo → Contacts → Listen.
- **Kostenlos bis?** 300 Mails/Tag. Danach Entscheidung: ab 9 $/Monat oder Sub-Listen.
- **Kill-Switch:** Workflow deaktivieren oder Secret löschen
  (ohne `BREVO_API_KEY` baut der Lauf nur, er versendet nichts).
- **Was, wenn ich den Digest nicht täglich will?** Cron im Workflow ändern
  (`5 5 * * 1-5`) – Versandfrequenz ist eine Datei, kein Umbau.
