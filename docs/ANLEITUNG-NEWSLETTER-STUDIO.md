# 🎛 ANLEITUNG: Newsletter-Studio (Marke, QA, Journeys – 0 €)

Nachgebaut ist die *Arbeitsteilung* eines Agentur-Newsletters – Creative → Design →
QA → Versand –, nicht sein Preisschild. Alles hier läuft mit den Werkzeugen, die im
Repo schon sind: Hugo, Python-Standardbibliothek, GitHub Actions, Brevo Free.
**Kein Abo, kein API-Key einer KI, kein Bild-Dienst, kein Cookie-Banner-Zuwachs.**

Falls du nur einrichten willst, dass Mails laufen: `ANLEITUNG-NEWSLETTER.md` (die
fünf Klicks im Brevo-Konto). Dieses Dokument ist die Werkstatt dahinter.

## 1. Die vier Schichten

| Schicht | Datei | Was sie entscheidet |
|---|---|---|
| Studio | `scripts/newsletter_studio.py` | wie eine Mail aussieht und was drinsteht (Farben, Blöcke, Betreff, Preheader, Textalternative) |
| QA | `scripts/newsletter_qa.py` | ob sie rausdarf (20 Regeln, gemessen: Kontrast, Größe, Links, Rechtliches, Zahlen-Belege) |
| Digest | `scripts/newsletter_digest.py` | ob der Anmeldeweg echt ist, welcher Bestand noch nicht versendet ist, und der eigentliche API-Ruf |
| Website | `layouts/shortcodes/newsletter_*.html`, `layouts/_partials/newsletter_strip.html`, `assets/css/extended/zz-newsletter.css`, `static/premium/ff-newsletter.js` | Anmeldung, Präferenzen, Bestätigung, Abmeldung |

Konfiguration steht an **einer** Stelle: `data/newsletter_studio.json`. Alles, was
dort nicht steht, hat einen Code-Default und wird von `--selftest` verlangt.

## 2. Befehle

```bash
# 1) Marke: leitet jede E-Mail-Farbe aus dem Build-CSS her, misst Kontraste
python3 scripts/newsletter_studio.py --brand            # Exit 0 = deckungsgleich
python3 scripts/newsletter_studio.py --brand --json     # für Skripte/Summaries

# 2) Bauen (schreibt NIE nach public/, nur ins --out-Verzeichnis)
python3 scripts/newsletter_studio.py --build --days 1 --vorschau --out .cache/nl
python3 scripts/newsletter_studio.py --build --days 7 --datum 2026-09-22 --variante 1

# 3) Prüfen – dasselbe Gate, das vor jedem Live-Versand läuft
python3 scripts/newsletter_qa.py --build --days 1        # Exit 0/1, Score 100 = frei
python3 scripts/newsletter_qa.py --datei .cache/nl/ausgabe-2026-09-22.html --md
python3 scripts/newsletter_qa.py --build --days 1 --json # Messwerte für die CI-Summary

# 4) Zustand der Strecke + Versand
python3 scripts/newsletter_digest.py --check --strict-inert
python3 scripts/newsletter_digest.py --build --send --live --test-adresse news@franksfinanzcheck.de

# 5) Alles grün? (Selftests der Wachen + Regressionstests)
python3 scripts/newsletter_studio.py --selftest
python3 scripts/newsletter_qa.py --selftest
python3 scripts/newsletter_digest.py --selftest
python3 -m unittest scripts.tests.test_newsletter_studio scripts.tests.test_newsletter_qa \
  scripts.tests.test_newsletter_site scripts.tests.test_newsletter_digest
npx playwright test e2e/newsletter.spec.mjs               # braucht public/-Build
```

`--datum` und `--variante` sind kein Spielzeug: ein Bau ist nur dann überprüfbar,
wenn er ohne Uhr und ohne Zufall auskommt. Gleiches Material + gleiches Datum =
Byte-für-Byte dieselbe Datei (der Test hält genau das fest).

## 3. Was in `data/newsletter_studio.json` steht

| Block | Schlüssel | Wirkung |
|---|---|---|
| `capture` | `form_action`, `form_url`, `versprechen`, `feld_email`, `feld_themen`, `bestaetigungs_url`, `abmelde_url`, `praferenz_url`, `bot_falle`, `mindest_alter` | Anmeldeweg, Feldnamen, Journeys, Bot-Falle an/aus |
| `email` | `breite`, `max_artikel`, `vorlagen_sprache`, `marken`, `header_bild`, `absender`, `antwort_an`, `rechtliches`, `ein_klick_abmeldung`, `tracking_oeffnungen` | Layoutbreite, Artikelzahl, Brevo-Marker, Absender, Rechtstext, Tracking aus |
| `design` | `hell`, `dunkel`, `herleitung`, `email_eigene`, `pflicht_rollen`, `schrift`, `radius`, `kontraste` | Farbrollen, ihre Token-Herleitung, Kontrastpflichtpaare |
| `creative` | `marke_kurz`, `du_form`, `betreff` (`min_zeichen`, `max_zeichen`, `varianten`), `preheader`, `block_text_zeichen`, `min_woerter`, `max_Ausrufezeichen`, `verbotene_woerter` | Tonalität, Betreff-Rotation (30–45 Zeichen, 3 Varianten), Wort- und Zeichenbudgets |
| `themen` | 6 Einträge mit `id`, `label`, `brevo_interest` | Präferenz-Chips – `id` muss eine Themenwelt der Site sein |
| `journeys` | `anmeldung`, `bestaetigung`, `praeferenzen`, `abmelden` | die vier Seiten, auch für Rechtstexte |
| `zustand` | `datei`, `betreff_historie`, `artikel_historie` | Pfad und Länge des Versandgedächtnisses: Duplikatsschutz (welche Artikel schon draußen waren) und Betreff-Wiederholung (Q15) |

`_doku`-Schlüssel sind Kommentare für dich; sie werden vor jedem Gebrauch
entfernt und landen nie im Mail.

**Präzedenz hugo.toml > JSON** für `newsletterFormAction`/`newsletterFormUrl`/
`newsletterPromise`: `hugo.toml` ist durch `data/integrity_lock.json` versiegelt,
deshalb ist das JSON der Schalter, den du anfassen darfst. beide gefüllt → hugo.toml
gewinnt, in Website, Wache *und* Studio (dieselbe Reihenfolge, sonst melden die
Seiten verschiedene Zustände).

## 4. Die Markenregel (warum „schick“ hier messbar ist)

Jede Farbe im Mail hat eine `herleitung` auf einen CSS-Token, den der Build wirklich
benutzt (`assets/css/extended/*.css`, `themes/PaperMod/assets/css/core/`).
`--brand` löst die Tokens auf, vergleicht und misst zusätzlich jedes Paar aus
`design.kontraste` in Hell **und** Dunkel nach WCAG 2.1. Eine Rolle, die weder ein
Token der Site ist noch in `email_eigene` mit Begründung steht (derzeit: die
Soft-Fläche `#293432`, ein `color-mix()`-Ergebnis, das es als Token nicht gibt), ist
ein Fund. Der Grund ist die teure Fehlerart, die dieses Repo kennt: ein Studio mit
eigenen Farbwerten sieht nach drei Monaten aus wie ein anderes Unternehmen.

`newsletter_qa.py` misst dieselben Paare vor jedem Versand noch einmal (Q11) – die
Konfiguration kann nicht durch eine Editierpause entkommen.

## 5. Das Vor-Versand-Gate

20 Regeln, Exit-Code statt Bauchgefühl: **0** frei, **1** Fund, **2** Prüfung
ausgefallen (fehlende Datei, kaputte Konfiguration). Fund blockiert den Live-Versand,
Warnung nicht – sonst wird die Wache am ersten Montag abgeschaltet, an dem nichts
kaputt war.

| | Regel | | Regel |
|---|---|---|---|
| Q1 | Größe (Gmail clippt bei 102 400 Bytes – dann fehlen Abmeldelink und Impressum) · Textalternative mindestens 240 Bytes | Q11 | Kontrast gemessen in hell und dunkel |
| Q2 | Tabellen-Layout, kein `<script>`/`<form>`/`@import`/Iframe, kein Flex/Grid/Absolute | Q12 | HTML ↔ Text gleichwertig (Links, Hero-Zahl, Abmelden) |
| Q3 | nur `{{unsubscribe}}`, `{{mirror}}`, `{{update_profile}}`; keine Einzelklammer, kein Platzhalter-Leak | Q13 | Viewport, `max-width`, Schriftgrößen, ≥ 40 px Tipp-Höhe |
| Q4 | absolute https-Links, erlaubte Hosts, Linktext, ≥ 2 Ziele, Ziel existiert wirklich | Q14 | Doctype, `lang`, Charset, `color-scheme`, Titel |
| Q5 | Bilder mit `alt`/Breite/Höhe, keine fremden Hosts, kein `background-image` | Q15 | Betreff nicht zweimal in Folge (aus `zustand.betreff_historie`) |
| Q6 | Substanz: Wörter statt Bildern (Bildermail = Spamnote, dünne Mail = Abmeldegrund) | Q16 | jede €-Zahl in Betreff/Preheader/Hero muss im Artikel stehen (Ziffernvergleich, Tausenderpunkt egal) |
| Q7 | Ton: verbotene Wörter, Ausrufezeichen-Budget, GROSSSCHREIBEN, €€€ | Q17 | Blöcke vollständig, ≤ `max_artikel`, keine doppelten Slugs |
| Q8 | Betreff: Länge, Marke, kein „Re:/AW:“, kein Markup | Q18 | Zeichensatz: kein Mojibake, kein `&amp;amp;`, keine unbekannte Entity |
| Q9 | Preheader als eigener Satz, keine Betreff-Kopie, kein Klischee | Q19 | Datenschutz: kein Tracking-Pixel (Konfiguration `tracking_oeffnungen: false`), Abmeldung mit einem Klick |
| Q10 | Fußzeile: Anschrift, Impressum, Datenschutz, Double-Opt-In-Hinweis, Werbehinweis | Q20 | Absendername und Antwortadresse auf der eigenen Domain |

Das Gate läuft **zweimal**: manuell (`--build`) und hart vor jedem Live-Versand in
`newsletter_digest.py` (der Versand bricht mit Exit 1 ab; `--trotz-qa` ist der
Notausstieg und steht im Workflow nicht zur Verfügung). Zusätzlich prüft
`newsletter_qa.py --selftest` die Wache selbst: pro Regel eine gezielte
Manipulation, die den passenden Code melden muss – 35 Fälle, kein Netz, kein
Schreibzugriff, uhrfest.

## 6. Capture und Journeys (das, was Leser sehen)

* `/newsletter/` – `{{< newsletter_form >}}`. Drei Zweige, einer wahr:
  `form_action` → echtes Inline-Formular (Leser verlässt die Seite nicht);
  nur `form_url` → Button zum gehosteten Formular; beides leer → ein Satz, kein
  Formular. **Kein Dummy-Feld, das ins Leere postet.**
* Felder: `email` (Name aus `capture.feld_email`, damit du bei einem anderen
  Anbieter nicht das Template anfassen musst), `themen[]` (Präferenz-Chips aus
  `themen`), `consent` (Pflicht-Häkchen mit Art. 6 Abs. 1 lit. a), `website`
  (Honigtopf) und `_zeit` (Zeitstempel).
* `static/premium/ff-newsletter.js` ist eine Verstärkung, kein Gate: ohne JS POSTet
  der Browser direkt, mit JS bleibt die Meldung auf dem Blatt. Die Zeitfalle wird
  **übermittelt, aber hier nicht gegen Menschen gekehrt** – eine echte Anmeldung
  nach 1,2 Sekunden ist schnell, nicht verdächtig. Blockiert wird nur bei gefülltem
  Honigtopf, und dann ohne Begründung.
* Nach erfolgreichem Absenden steht `localStorage.ff_nl = "angemeldet"`; der
  Artikel- und Footer-Streifen tauscht dann den Anmelde-Knopf gegen den Weg zu den
  Präferenzen. Mehr Merken findet nicht statt (kein Cookie, kein third-party).
* Journeys: `/newsletter/bestaetigung/` (Prüfliste, wenn die DOI-Mail fehlt),
  `/newsletter/praeferenzen/` (`{{< newsletter_themen >}}` aus
  `data/themenwelten.json`), `/newsletter/abmelden/` (Rechte, Löschfristen,
  Widerruf). Alle vier `robotsNoIndex` + aus der Sitemap draußen.
* Bewusst **nicht** eingebaut: Exit-Intent-Modal (unterbricht beim Rechnen),
  Double-Opt-In-Falle im Formular (§ 7 UWG will den Nachweis, den das Verfahren des
  Anbieters liefert), ein Bild-Carousel im Kasten (CLS-Budget).
* Der Streifen wird **nicht** doppelbaut: `layouts/_partials/extend_footer.html`
  (markenversiegelt) zeigt seinen CTA, sobald ein hugo.toml-Parameter gesetzt ist –
  `newsletter_strip.html` rückt im Fuß nur ein, wenn dort nichts anderes greift, und
  gar nicht auf `/newsletter*`, `/impressum/`, `/datenschutz/`.

## 7. Freischalten (der eine Satz, der dir bleibt)

Der Zustand „geschaltet“ ist eine Konfigurationszeile, kein Code-Umbau:

```toml
# hugo.toml – versiegelt, also nur mit Absicht anfassen
[params]
  newsletterFormAction = "https://l.brevo.com/landing/DEINE-FORMULAR-ID"
```

oder, ohne Siegel zu berühren, im Studio-JSON:

```json
{ "capture": { "form_action": "https://l.brevo.com/landing/DEINE-FORMULAR-ID" } }
```

Danach in dieser Reihenfolge:

1. `python3 scripts/newsletter_digest.py --check` → `aktiv`, keine N-Funde.
2. `hugo` (bzw. den Deploy-Build) und `npx playwright test e2e/newsletter.spec.mjs`.
3. `python3 scripts/newsletter_qa.py --build --days 1` → 100/100.
4. Secrets in den GitHub-Actions-Settings: `BREVO_API_KEY`, `BREVO_LIST_ID`
   (+ optional `BREVO_TEST_LIST_ID`, `NEWSLETTER_TEST=1`).
5. Actions → *Newsletter-Daily* → `test_adresse` = deine Adresse, `live` aus →
   echter `sendTest` durch Brevo, Liste unangetastet.
6. `live` an. Ab jetzt liefert der Cron Mo–Fr 05:05 UTC eine geprüfte Mail, und
   `data/newsletter_state.json` (versioniert!) merkt, was schon draußen war.

Der letzte Klick bleibt bei dir, weil er ein Konto braucht: Signup, SPF/DKIM, AVV.
Das hier zu erfinden – ein Endpunkt, eine Listen-ID, eine Signup-Bestätigung – wäre
die Sorte Selbstbetrug, gegen die die Wachen in diesem Repo geschrieben sind.

## 8. Export statt API (wenn du mal wechselt)

`--build --out DIR` schreibt `ausgabe-<datum>.html` (Mail-HTML mit Brevo-Markern),
`ausgabe-<datum>.txt` (Textalternative) und auf Wunsch `vorschau.html` (drei Breiten,
hell/dunkel, zum Anschauen statt Raten). Diese drei Dateien sind der Export: in
**jedem** Tool, das HTML-Mails kennt, Einfügen → Senden. Der API-Weg
(`newsletter_digest.py --send`) tut dasselbe automatisch und legt die Kampagne als
`draft` an, bevor er `sendNow` aufruft – abbrechen kann man also jederzeit.

## 9. Grenzen (damit du nichts vermisst, das nie versprochen war)

* **Kein KI-Texten.** Betreff, Preheader und Anriss werden deterministisch aus dem
  Artikel-Frontmatter gebaut (`kurzantwort` schlägt `description`). Zahlen kommen
  ausschließlich aus dem Quelltext, mit Belegstelle; Q16 blockiert jede Zahl, die
  kein Artikel hergibt. Ein LLM-API-Key wäre eine Kostenquelle und eine
  Halluzinationsquelle – deshalb: 0 € für immer, wie gewünscht.
* **Keine Render-Matrix** (Apple Mail/Gmail/Outlook-Echtgeräte-Screenshots wie bei
  teuren Tools). Ersatz: harte Regeln für das, was diese Clients kaputtmachen –
  Tabellen-Layout, VML-Knopf, `max-width`, keins von Flex/Grid/`@import`, keine
  CDN-Schriften. Outlook-Prüfung bleibt manuell: `vorschau.html` in Outlook öffnen.
* **Keine KI-Bilder.** Cover bleiben Handarbeit des Blogs (die Bilder in der Mail
  sind bewusst optional: Q5 verlangt `alt`/Breite/Höhe, wenn welche drin sind).
* **Kein Konkurrenz-Newsletter-Abo** („competitor tracking“) – Listenbereinigung per
  Proxy-Mail wäre ein Anti-Pattern und kostet zusätzlich.

## 10. Störungsbild

| Meldung | Ursache | Tun |
|---|---|---|
| `--brand`: „Rolle ohne Herleitung“ | Farbe im JSON, die kein Site-Token ist | `design.hell/dunkel` auf den Token-Wert setzen oder in `email_eigene` begründen |
| `Q16 … hat keinen Beleg` | Zahl in Betreff/Hero, die im Artikel so nicht steht | Zahl aus dem Betreff nehmen oder Artikel nachziehen – nicht den Beleg nachbauen |
| `Q3 … Einzelklammer {unsubscribe}` | Alte Vorlagen-Sprache | `{{unsubscribe}}` (die Einzelklammer ersetzt Brevo in `htmlContent`-Kampagnen nicht) |
| `Q10 … kein Abmeldelink` | Fußblock-editiert | `email.marken` und den Fußblock aus `baue_email` wiederherstellen |
| `N1 … wirbt ohne Anmeldeweg` | Werbesatz auf einer Seite außerhalb von `/newsletter/`, aber kein `form_*` | Weg eintragen **oder** den Werbetext auf den Leerzustand zurückziehen |
| „Streifen bleibt unsichtbar“, obwohl `form_action` gesetzt ist | Include in `layouts/single.html` gesetzt – die Datei wird von `layouts/_default/single.html` verdeckt und rendert für Posts nie | Include in die lebende Datei, direkt nach `{{ partial "extend_post_content.html" . }}` |
| `N4 … ohne Feld „email“` | Shortcode umgeschrieben | `capture.feld_email` setzen (erlaubter zweiter Weg) oder literal `name="email"` |
| `N5 … Seite nicht gebaut` | `public/` fehlt/veraltet | `hugo` laufen lassen; im CI baut der Deploy |
| `ds-platzhalter` | `[Platzhalter]` im Rechtstext | ausformulieren – die Wache prüft auf eckige Klammern ohne Link |
| QA-Selbsttest „DATUMABHÄNGIG“ | Test hängt an der echten Uhr | Fixtures relativ zum Testdatum bauen (`scripts/selftest_clock.py`) |
| Build: `function "set" not defined` | Hugo kennt kein `set`/`unset` (das kommen aus anderen Template-Sprachen) | Karte mit `merge` bauen: `$karten = merge $karten (dict $id $wert)` – Zuweisung per `=` |

## 11. Was die CI davon hält

`scripts/newsletter_studio.py`, `scripts/newsletter_qa.py` und
`scripts/newsletter_digest.py` stehen in `governance_contract.GUARDS`, ihr
`--selftest` läuft also in `selftest_runner` (und `--selftest` der Wachen ist der
einzige Weg, in dem diese Anleitungen „geprüft“ bedeutet). Dazu:
`.github/workflows/link-check.yml` → Job *Newsletter-Wache* (`--check
--strict-inert`, `newsletter_qa.py --build`) und die E2E-Suite mit
`e2e/newsletter.spec.mjs`. `data/newsletter_state.json` wird vom Workflow
zurückgeschrieben; der Arbeitbaum muss frei sein, sonst verweigert der Versand
(`assert_worktree`).

Reihenfolge für einen Check zu Hause – die Template-Schicht ist nur mit echtem
Build bewiesen, die Python-Schicht nur mit `--selftest` unter verschobener Uhr:

```bash
hugo --gc --minify                      # 1. Bau (CI nutzt `--quiet --destination public`)
python3 scripts/layout_audit.py         # 2. Layout- und DOM-Budgets gegen public/
bash scripts/check_internal_links.sh    # 3. jeder interne Link, auch /newsletter/
python3 scripts/newsletter_digest.py --check   # 4. Capture-Kette (inert ist erlaubt)
python3 -m unittest discover -s scripts/tests -p 'test_newsletter*'
```

Ohne `hugo` im Container lässt sich das Rad aus PyPI holen: `python3 -m pip install
--target /tmp/hugopy hugo` → Binary unter `/tmp/hugopy/hugo/binaries/hugo`.
