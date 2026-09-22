# 📬 ANLEITUNG: Vollautomatisierter Newsletter (Brevo, kostenlos)

An Werktagen um 07:05 (MESZ) baut der Blog **eine** Mail mit den Artikeln des
Tages – Double-Opt-In, Abmeldelink, kein manueller Eingriff. Diese Anleitung:
einmalig ca. 15 Minuten (danach nie wieder anfassen).

**Was im Repo liegt – und wer es prüft.** (Schicht für Schicht, damit „gebaut“
nicht heißt „unbelegt“.)

| Schicht | Datei | Wache |
|---|---|---|
| baut die Mail: Marke, Blöcke, Betreff, Textalternative | `scripts/newsletter_studio.py` | `--selftest`, `--brand` |
| prüft vor dem Versand: 20 Regeln, gemessen statt geschätzt | `scripts/newsletter_qa.py` | `--selftest`; läuft vor jedem `--send` |
| Watchdog, Bau, Versand, Duplikatsschutz | `scripts/newsletter_digest.py` | `--selftest`, `--check` |
| Anmeldung, Präferenzen, Bestätigung, Abmeldung | `layouts/shortcodes/newsletter_form.html`, `content/newsletter*/` | `--check`, `e2e/newsletter.spec.mjs` |
| Design-Schicht des Formulars | `assets/css/extended/zz-newsletter.css` | `scripts/tests/test_newsletter_site.py` |

Konfiguration (Marke, Betreff-Ton, Feldnamen, Journeys) steht an einer Stelle:
`data/newsletter_studio.json`. Das Weitere – Layout-Engine, QA-Regeln,
Freischalten, ESP-Export – in **`ANLEITUNG-NEWSLETTER-STUDIO.md`**; dieses
Dokument bleibt der kurze Weg durchs Brevo-Konto. Solange kein Anmeldeweg
eingetragen ist, bleibt die Anmeldeseite NoIndex, zeigt der Streifen seinen
Leerzustand, und `.github/workflows/newsletter-daily.yml` baut ohne zu senden.

## Wichtig vorab (Recht, DE)

✅ Double-Opt-In (Brevo-Standard, das gehört so) · ✅ Abmeldelink in jeder Mail
(`{{unsubscribe}}` – doppelte Klammer; die Einzelklammer der alten
Vorlagen-Sprache ersetzt Brevo in `htmlContent`-Kampagnen nie) · ✅ Impressum- und
Datenschutz-Links in jeder Mail (eingebaut, von `newsletter_qa.py` in Q10
verlangt) · ✅ § 8 der Datenschutzerklärung ist gesetzt und liest den
Schaltzustand aus dem Studio (`{{< newsletter_status >}}`) · ☐ AVV/DPA mit Brevo
abschließen (Einstellungen → Rechtliches) · ☐ nach dem ersten Versand:
Datenschutzerklärung gegen den tatsächlichen Stand lesen (Wortlaut-Entwurf:
`NEWSLETTER-RECHTSTEXT-VORLAGE.md`).

## 1. Brevo-Konto (5 Min.)

1. [brevo.com/de](https://www.brevo.com/de/) → **Kostenlos registrieren** (Free-Plan,
   300 Mails/Tag – ausreichend bis ca. 300 Abonnenten täglich)
2. Absendername eingeben: `Frank von FranksFinanzcheck` · E-Mail (vorläufig):
   deine private Mail **ODER** `kontakt@franksfinanzcheck.de` (s. Schritt 2)
3. Konto bestätigen (Mail-Link), Fragebogen überspringen/simply fill.

## 2. Absender-Adresse (profi = eigene Domain, ~10 Min.)

> **Für den gewünschten Blog-Kontakt: Cloudflare Email Routing** für
> `kontakt@franksfinanzcheck.de` – siehe
> [Einrichtungsanleitung](E-MAIL-WEITERLEITUNG-CLOUDFLARE.md). Das nimmt
> eingehende Antworten an und leitet sie an das persönliche Postfach
> weiter; es ist bewusst **keine** eigene Mailbox (kein SMTP-Versand).

Für den **Absender-Versand aus Brevo** ist zusätzlich zu der Cloudflare-
Weiterleitung die Brevo-Sender-Authentifizierung nötig: In Brevo
**Senders → Add sender** → `kontakt@franksfinanzcheck.de` und die
**Authentifizierung** (SPF + DKIM) per DNS-Einträgen abschließen.

> (Brevo zeigt exakt die Werte; beim Anbieter in die DNS-Zone eintragen).
> Beim SPF darf **kein zweiter TXT-Eintrag** entstehen: den vorhandenen
> SPF-Eintrag gemäß Brevo-/Cloudflare-Vorgaben zusammenführen (z. B.
> `v=spf1 include:_spf.mx.cloudflare.net include:spf.brevo.com ~all`).
> Die Cloudflare-Routing-MX-Einträge bleiben dabei bestehen.
> → bessere Zustellbarkeit + „professioneller Absender".

*(Notlösung: private Mail bleibt als Absender, funktioniert – aber
weniger schick und ohne `kontakt@franksfinanzcheck.de`-Absenderadresse.)*

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

**Erledigt im Repo, und zwar so, dass der Widerspruch nicht wieder entstehen
kann:** § 8 in `content/datenschutz/index.md` enthält Double-Opt-In-Nachweis,
Speicherdauer, Widerruf und den Auftragsverarbeiter, und der erste Satz kommt aus
`{{< newsletter_status >}}`, das `data/newsletter_studio.json` liest. Solange kein
Anmeldeweg konfiguriert ist, steht dort „Anmeldung noch nicht geschaltet“ – derselbe
Zustand, den Wache und Website melden; es gibt keine Prosa mehr, die der
Konfiguration hinterherlaufen müsste. Die Überschrift bleibt unverändert
(„## 8. Newsletter / Kontaktaufnahme“), weil die Wache den Abschnitt darüber findet.
Wortlaut-Entwurf für E-Mail-Signatur und Präferenzseite:
`docs/NEWSLETTER-RECHTSTEXT-VORLAGE.md`.

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
> (Einwilligung). Dienstleister: Brevo (Sendinblue SAS, Frankreich; AVV vor dem
> ersten Versand abschließen, EU-Hosting). Anmeldung per Double-Opt-In; Abmeldung
> jederzeit per Link in jeder E-Mail. **Keine** Öffnungs- oder Klickmessung:
> `email.tracking_oeffnungen` steht in `data/newsletter_studio.json` auf `false`,
> und `newsletter_qa.py` (Q19) bricht den Versand ab, falls die Mail trotzdem ein
> Tracking-Pixel enthält. Wer Statistik will, schaltet sie im Studio und hier
> gleichzeitig ein – sonst beschreibt der Rechtstext etwas, das nicht passiert.

## ❓ FAQ

- **Zwei Artikel in einem Tag?** Beide landen in EINER Abend-Mail (Digest). Leser-Freundlichkeit > Frequenz.
- **Anmeldezahlen sehen?** Brevo → Contacts → Listen.
- **Kostenlos bis?** 300 Mails/Tag. Danach Entscheidung: ab 9 $/Monat oder Sub-Listen.
- **Kill-Switch:** Workflow deaktivieren oder Secret löschen
  (ohne `BREVO_API_KEY` baut der Lauf nur, er versendet nichts).
- **Was, wenn ich den Digest nicht täglich will?** Cron im Workflow ändern
  (`5 5 * * 1-5`) – Versandfrequenz ist eine Datei, kein Umbau.
