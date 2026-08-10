# 📬 ANLEITUNG: Vollautomatisierter Newsletter (Brevo, kostenlos)

Täglich 21:45 Uhr versendet der Blog **eine** Mail mit den Artikeln des Tages –
vollautomatisch, rechtssicher (DOI), mit Abmeldelink. Diese Anleitung: einmalig
ca. 15 Minuten (danach nie wieder anfassen).

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
   (https://…sendinblue.com/…) 📌 notieren!

## 4. GitHub hinterlegen (2 Min.)

Repo → **Settings → Secrets and variables → Actions**:
- Secret: **`BREVO_API_KEY`** (Brevo → oben rechts Name → *SMTP & API → API Keys → Generate*)
- Variable: **`BREVO_LIST_ID`** = Listen-Zahl aus Schritt 3
- (optional) `BREVO_TEST_LIST_ID` + `NEWSLETTER_TEST=1` → sendet nur an dich zur Probe
- (optional) `BREVO_SENDER_EMAIL` = `kontakt@franksfinanzcheck.de`

**Anmelde-Button auf der Website sichtbar machen:** in `hugo.toml` den
Parameter `newsletterFormUrl` mit der Formular-URL aus Schritt 3 befüllen
→ Footer-Button erscheint automatisch auf allen Inhaltsseiten. (Leer = versteckt.)

## 5. Probelauf

Actions → **Newsletter-AI → Run workflow**. Mit `NEWSLETTER_TEST=1` geht die Mail
nur an die Testliste. Dann Variable entfernen = live. Status: `NEWSLETTER-STATUS.md`.

## ✂️ Rechtstext-Baustein (Datenschutz ergänzen)

> **Newsletter:** Bei Anmeldung speichern wir deine E-Mail-Adresse zur Versendung
> unseres Blogs (Tages-Digest). Rechtsgrundlage Art. 6 Abs. 1 lit. a DSGVO
> (Einwilligung). Dienstleister: Brevo (Sendinblue SAS, Frankreich; AVV abgeschlossen,
> EU-Hosting). Anmeldung per Double-Opt-In; Abmeldung jederzeit per Link in jeder
> E-Mail. Versand-Statistik (Öffnungs-/Klickraten, anonym).

## ❓ FAQ

- **Zwei Artikel in einem Tag?** Beide landen in EINER Abend-Mail (Digest). Leser-Freundlichkeit > Frequenz.
- **Anmeldezahlen sehen?** Brevo → Contacts → Listen.
- **Kostenlos bis?** 300 Mails/Tag. Danach Entscheidung: ab 9 $/Monat oder Sub-Listen.
- **Kill-Switch:** Workflow deaktivieren oder Secret löschen.
