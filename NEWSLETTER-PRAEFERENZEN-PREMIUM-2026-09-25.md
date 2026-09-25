# Newsletter-Präferenzen: Premium-Upgrade der Themen-Auswahl

**Stand: 25. September 2026.** Auftrag: die Präferenz-Seite
`/newsletter/praeferenzen/` auf Premium-Level einer Profi-Agentur bringen –
mit den beiden konkreten Befunden aus dem Live-Betrachtung:

| # | Befund | Ursache | Reparatur |
|---|---|---|---|
| 1 | **Es fehlen Auswahlkästchen** bei den Themen-Welten | Der Shortcode `newsletter_themen` rendernte eine statische `<dl>`-Liste – die Seite *erzählte* von Häkchen, die es dort nicht gab | Echter Picker: sechs Karten, jede ein `<label>` um ein echtes `<input type="checkbox">`, plus drei ehrliche Zustände (Vorschau / Direkt-mit-Token / ohne JavaScript) |
| 2 | **Der Zeilenumbruch ist störend** | Name + Beschreibung saßen als lose Zeilen in 2 px Abstand in einer vollen Zeile pro Welt; auf schmalen Breiten brach der Name unvorbereitet | Karten-Raster (2 Spalten ab 520 px), `text-wrap: balance` auf dem Namen (bricht nie mitten im Wort), `text-wrap: pretty` auf der Beschreibung (keine Halbwaise) |

---

## 1. Der Picker ist Interface, keine Dekoration

Neu in `layouts/shortcodes/newsletter_themen.html`:

* **Sechs Karten im Raster** (`repeat(2, minmax(0, 1fr))` ab 520 px, darunter
  einspaltig), jede mit Checkbox (20 px, `accent-color` Smaragd), Emoji,
  Name und Beschreibung. Die Checkbox bleibt sichtbar – der Auswahlzustand
  trägt die native Checkbox, `:has()` malt nur die Kartengestaltung darüber.
  Ohne `:has()`-Support verschwindet nichts.
* **Live-Statuszeile** (`role="status"`): „0 von 6 → Deine Auswahl: 3 von 6
  Welten …“ in einem reservierten Slot (min-height, kein CLS).
* **Aktionszeile mit festem Slot**: Link *und* Knopf teilen sich dieselbe
  44-px-Zeile – der Wechsel erzeugt keinen Sprung.

Die Daten bleiben an der einen Quelle: IDs + Labels aus
`data/newsletter_studio.json` (`themen`), Emoji + Beschreibung aus
`data/themenwelten.json` – dieselbe Datei wie Startseite und Ratgeber-Cluster
(Wache `newsletter_studio.py --brand` hält die IDs deckungsgleich).

### Die drei ehrlichen Zustände (kein Klick-Vorgaukeln)

1. **Vorschau** (ohne Token in der Adresse): Häkchen zählen live mit; der
   Link „Mit deiner Auswahl zum Anmeldeformular“ schreibt die Auswahl in
   `localStorage` (`ff_nl_themen`) – das Anmelde-Formular auf `/newsletter/`
   setzt diese Chips **vor** (`ff-newsletter.js`) und räumt die Auswahl nach
   dem Versand ab. Ohne Abo gibt es nichts zu speichern – die Seite behauptet
   auch nichts anderes.
2. **Direkt** (`?token=…` in der Adresse): `static/premium/ff-nl-praef.js`
   lädt die aktuelle Auswahl vom Worker (`GET /status?token=…`, `Accept:
   application/json` – der Token ist die einzige Legitimation, die E-Mail-
   Adresse geht nicht mit) und speichert „Auswahl speichern“ per
   `POST /praferenzen`. Erfolg und Fehler druckt die Seite so, wie der
   Worker es sagt; bei Netzwerk-/CORS-Fehlern zeigt sie den
   servergerenderten Weg (funktioniert ohne JavaScript) statt tot zu gehen.
   Die Worker-Basis kommt aus dem DOM (`data-basis`, im Shortcode aus
   `capture.form_action` abgeleitet) – das Skript kennt keine einzige
   Domäne, lädt kein Third-Party (gleiche Wache-Regel wie
   `ff-newsletter.js`).
3. **Ohne JavaScript**: `<noscript>`-Zeile weist auf den Link „Präferenzen“
   im Fuß jeder Mail – der zeigt auf `abos.franksfinanzcheck.de` und
   funktioniert in jedem Browser.

Ohne Capture-Endpunkt (form_action leer) rendert der Shortcode die gleiche
Karte ohne `data-basis` und ohne Script: eine saubere Liste, kein Knopf, der
nirgends anklopfen kann (der „ehrliche Leerzustand“ bleibt erhalten).

## 2. Der Umbruch, gemessen statt geschätzt

* Namen: `text-wrap: balance` – „Versicherungen & Vorsorge“ bricht nie mitten
  im Wort, keine einsamen Silben.
* Beschreibungen: `text-wrap: pretty` – die letzte Zeile wird nicht zur
  Halbwaise.
* Name und Beschreibung stehen in EINER Karte (Grid-Areas „check kopf / .
  text“), nicht als lose Zeile mit 2 px Abstand.
* Der Button-Text bricht nie („Auswahl spei-chern“ unmöglich):
  `white-space: nowrap` auf dem Text, der Knopf wächst.

## 3. Der Worker: zwei Reparaturen am Weg

* **Stiller Datenverlust bei der Anmeldung** (Befund nebenbei): Das
  HTML-Formular sendet das Themenfeld als `themen[]` (Hugo rendert
  `name="{{ feld_themen }}[]"`), der Worker las aber nur `themen` – jede
  Themenwahl bei der **Anmeldung** wurde still verworfen, alle Abo-Belege
  fuhren mit leerer Auswahl. `anmeldung` und `praferenzen` normalisieren
  jetzt beide Feldnamen. Tests: `anmeldung: Feldname themen[] …` und
  `praferenzen: themen[] (HTML-Feldname) …`.
  *Konsequenz für den Bestand:* Bestehende Abo-Belege tragen weiterhin die
  (verlorene) Auswahl `[]` = „alles“. Wer seine Welt haben will, setzt sie
  jetzt einfach über die Präferenz-Seite – der Bestand braucht keinen
  Migrationslauf.
* **Brücke in die Vollversion**: Die servergerenderte Auswahl-Seite des
  Workers (`GET /praferenzen?token=…`) verlinkt jetzt die Premium-Seite
  (`franksfinanzcheck.de/newsletter/praeferenzen/?token=…`) – dieselbe
  Legitimation, dasselbe Ergebnis, bessere Oberfläche. Die Mail-Links
  selbst zeigen unverändert auf den Worker (funktioniert ohne JavaScript),
  der Digest und seine QA-Gates bleiben angetastet.

## 4. Was geprüft ist

* `python3 scripts/tests/test_newsletter_site.py` – **43/43** (6 neue:
  Picker-Hooks, First-Party/keine URLs, echte Checkboxes, Hand-off-Vertrag
  in beiden Skripten, Worker-Feldnamen, node --check).
* `npm test` (Worker) – **49/49** (2 neue + 1 erweitert).
* `python3 scripts/tests/test_newsletter_digest.py` – 24/24,
  `test_newsletter_schedule.py` – grün (keine Folgeänderung).
* Design-Regeln eingehalten: Radien 12/16/999, Schatten-Skala, Übergänge nur
  transform/opacity/color, `prefers-reduced-motion`, Fokusring 3 px
  Signalgelb (Dark: Akzent-2), jede Fläche mit Dark-Variante, Fehler-/
  Erfolgstoken (`--ff-nl-fehler/-erfolg`) auf `.ff-nl-themen` mitgeführt –
  die Wache zählt exakt zwei Definitionen je Token und bleibt grün.
* Hugo-Binary steht in dieser Umgebung nicht zur Verfügung (Download
  blockiert) – der Build läuft in der CI (`deploy.yml`: `hugo --minify` +
  Playwright-Suite). Die Template-Logik wurde zeilenweise gegen die
  Trim-Semantik von `{{-`/`-}}` nachvollzogen; dabei ist ein Whitespace-Bug
  im `data-basis`-Attribut gefunden und behoben worden.

## 5. Nach dem Deploy

1. **Worker neu deployen** (`cd newsletter-worker && npx wrangler deploy`) –
   ohne den Deploy wirken weder die `themen[]`-Reparatur noch der
   Vollversions-Link.
2. E2E-Suite läuft in der CI (Playwright); der Journeys-Test
   (`/newsletter/praeferenzen/` existiert, noindex, in der Sitemap draußen)
   bleibt ohne Änderung grün.
3. Manueller Probelauf: Präferenz-Seite öffnen → Häkchen setzen →
   „Mit deiner Auswahl zum Anmeldeformular“ → Formular zeigt die Chips
   vorgestzt. Mit Token (Testabo): Worker-Auswahlseite → „Vollversion
   öffnen“ → Häkchen laden, speichern, Meldung in Grün.
