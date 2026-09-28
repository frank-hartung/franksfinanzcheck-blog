# Ratgeber-Cluster „Alle vertiefenden Artikel“ ungestylt + falsches Stand-Datum – behoben (28.09.2026)

**Auslöser (Frank):** „Siehe dir folgendes genauer an:
franksfinanzcheck.de/pillar/strom-sparen/ – Alle vertiefenden Artikel in
diesem Ratgeber: Der Text auf der Seite wird nicht richtig dargestellt.
Bitte auf Premium-Level einer Profi-Agentur beheben.“

**Betroffen:** alle 6 Themenwelten (`/pillar/strom-sparen/`, `/pillar/
versicherungen/`, `/pillar/mietwagen/`, `/pillar/frugalismus/`,
`/pillar/internet-dsl/`, `/pillar/konto-karten/`) – jeweils der komplette
Block „📚 Alle vertiefenden Artikel in diesem Ratgeber“ inklusive Karten-Raster
und „Weitere Ratgeber“-Chips; zusätzlich die 404 (Themen-Chips) und die
Stand-Datum-Zeile im Ratgeber-Kopf. Befund bestätigt am gebauten HTML
(derselbe Template-Stand, der auch Produktion deployt).

---

## 1 · Befund (nachgestellt und messbar gemacht)

Auf `/pillar/strom-sparen/` floss der gesamte Cluster-Block unten als ein
unformatierter Inline-Textstrom zusammen: Cover-Bild (360×540), fetter Titel,
Beschreibung und „Jetzt lesen →“ je Karte standen in einer Zeile hintereinander,
zehn Karten ohne Raster, Zähler-Pill („10 Beiträge“) klebte am Untertitel, die
Themen-Chips („🛡️ Versicherungen → …“) erschienen als reine Textwurst.

Messbar nachgewiesen am gebauten HTML (Hugo-Build des Repo-Stands):

* **27 `.ff-pc-*`-Klassen im Markup, 0 `.ff-pc-*`-Selektoren in der
  ausgelieferten CSS.** Die Klassenvermessung (Brace-Matching-Parser über alle
  10 Inline-`<style>`-Blöcke der Seite) listete exakt die komplette
  Komponentenfamilie als „unstyled“: Brotkrumen, Titel-Hook, Meta-Zeile,
  Prüfbadge, Cluster-Kopf (Head/Title/Sub/Count), Karten-Raster
  (Grid/Card/Cover/Fallback/Img/Body/Title/Desc/CTA) und die
  Themen-Chips (Related/Title/Chips/Chip).
* Alle anderen Klassen der Seite waren stylbar versorgt (`.post-title`,
  `.post-meta`, `.breadcrumbs` über PaperMod; `.ff-quellen__*`,
  `.ff-rechner__*`, `.ff-voice-*` über z-premium-blog.css/ff-voice.css bzw.
  Inline-Styles der Shortcodes). Der Schaden war also präzise auf die
  Ratgeber-Cluster-Familie begrenzt.

Dazu ein zweiter, unabhängiger Textfehler im selben Kopf: **„📅 Stand:
28. Januar 2026“** – obwohl der Ratgeber am 28. September 2026 überarbeitet
wurde.

## 2 · Ursachen – zwei getrennte Lieferlücken

1. **Die dokumentierte CSS-Lieferung fand nie statt.** Das
   Design-Skills-Rollout (12.09.2026) stellte `layouts/pillar/single.html`
   von Inline-Styles auf semantische `.ff-pc-*`-Klassen um und dokumentierte
   das System in DESIGN.md §5 als „Light+Dark definiert
   (zzz-agency-polish.css)“ – inklusive Chip-Spezifikation („Pill,
   Smaragd-Soft hell / 12 % Smaragd-Bright dunkel“). Der Template-Kommentar
   verwies auf „Abschnitt 7“ dieser Datei. Dort steht aber die 404-Seite;
   **ein `.ff-pc-*`-Abschnitt existierte in keiner CSS-Datei des Repos.**
   Das Markup war korrekt gebaut, die zugehörige CSS-Familie wurde nie
   ausgeliefert – deshalb fiel alles auf Inline-Default-Rendering zurück.
2. **„Januar“ ist kein Go-Layout-Token.** In
   `$ffPillarStand.modified.Format "2. Januar 2006"` ist `Januar` (deutsch)
   für die Go-Referenzzeit kein Monatsplatzhalter, sondern Literaltext.
   Nachgestellt mit Hugo 0.166: Der Layoutstring formatiert JEDES Datum als
   „… Januar …“ (`2026-03-15` → „15. Januar 2026“, `2026-09-28` →
   „28. Januar 2026“). Der Monat wurde nie aus dem Datum gelesen.

## 3 · Reparatur –Stylesheet-Nachlieferung ohne Markup-Eingriff

**`assets/css/extended/zzz-agency-polish.css` – neuer Abschnitt 10
„PILLAR-RATGEBER-SEITEN – DAS .ff-pc-*-SYSTEM“** (zwischen Abschnitt 9 und
dem Spar-Signet). Das Markup blieb vollständig unangetastet – die Templates
sind korrekt, es fehlte nur die CSS-Lieferung. Geliefert wurden alle 25
Klassen nach den Vorgaben des Design-Systems:

* **Kopf:** Brotkrumen eine Stufe leiser als PaperMod-Default (0.82rem,
  Trenner gedimmt, aktuelle Seite halbfett), Meta-Atom-Anteile unteilbar
  (`white-space:nowrap` – Datum/Lesezeit brechen nicht mittendrin, die
  „·“-Trenner bleiben im Inline-Fluss, PRODUCT.md-Konvention), Prüfbadge
  „Geprüfter Praxis-Leitfaden“ als Smaragd-Soft-Pill (Dark Mode:
  Smaragd-Bright auf 12 %-Fläche – automatisch über das Dark-Override von
  `--ff-emerald-soft`).
* **Cluster-Kopf:** Flex-Zeile Titel/Untertitel links, Zähler-Pill rechts
  (bricht auf schmalen Screens sauber um); Titel mit der H2-Identität des
  Hauses (Inter 800, Smaragd, 2px Signalgelb-Unterstreichung wie
  `.post-content h2`, `inline-block`, damit die Linie nur unter dem Titel
  liegt).
* **Karten-Raster:** `repeat(auto-fill, minmax(min(100%, 220px), 1fr))` →
  3 Spalten in der 720px-Inhaltsspalte (gleiche Kartenproportion wie die
  Verwandte-Artikel-Karten in Posts), 1 Spalte mobil, kein horizontaler
  Overflow. Karten-Optik 1:1 nach `.ff-related-card`: Fläche `--entry`,
  1px-Border, `--ff-shadow-1`, Radius-md, Hover-Lift −3px mit Schatten-2 und
  Cover-Zoom 1.03 (0.18s cubic-bezier(.2,.7,.2,1)). Cover bleiben im
  natürlichen 2:3-Verhältnis (width/height-Attribute im Markup → kein CLS),
  Fallback-Cover als Smaragd-Gradiente im 2:3-Format. CTA über
  `margin-top:auto` unten bündig – gerades Kartenraster auch bei
  unterschiedlich langen Titeln.
* **Themen-Chips:** exakt die DESIGN.md-§5-Spezifikation (Pill, Smaragd-Soft
  hell / 12 % Smaragd-Bright dunkel), Hover nach dem Button-Muster
  (Vollton-Smaragd/Weißtext, dunkel Smaragd-Bright/Tiefgrün-Text). Wirkt
  damit auch auf der 404 (Themen-Schnellzugriff).
* **Dark Mode:** jede Akzentfarbe hat eine `:root[data-theme="dark"]`-
  Variante (Kartenfläche, Titel/CTA in Smaragd-Bright, Hover #a8ecd2);
  Flächen laufen über die ohnehin themenbewussten Tokens `--entry/--border/
  --secondary/--ff-emerald-soft`.
* **Motion & A11y:** nur Transform/Farb-Übergänge (keine Layout-Properties),
  `.ff-pc-card:hover`/`.ff-pc-chip:hover` in die bestehende
  Reduced-Motion-Reset-Liste (Abschnitt 9) aufgenommen; Fokus-Ringe und
  ≥24px-Tap-Ziele erben aus Abschnitt 9 bzw. Pill-Padding (34px). Kontraste
  nach Token-Rechnung: Badge/Chip-Ruhe ≥ 5.4:1, Chip-Hover 4.6–8.2:1.

**`layouts/pillar/single.html`** – zwei Zeilen repariert:

* Stand-Datum: `.Format "2. Januar 2006"` → `time.Format "2. January 2006"`
  (Referenz-Monat „January“ + `time.Format` lokalisiert die Monatsnamen zur
  Site-Sprache de). Aus „Stand: 28. Januar 2026“ wird „Stand:
  28. September 2026“. Der Reparaturgrund steht als Template-Kommentar am
  Fundort.
* Kommentar-Zeiger von „Abschnitt 7“ (404) auf den echten Ort korrigiert
  (Abschnitt 10).

**`DESIGN.md` §5** – die Komponentenzeile „Pillar-Cluster“ nennt jetzt den
tatsächlichen Abschnitt (§10) und vermerkt die Nachlieferung; die
Chip-Spezifikation war bereits korrekt dokumentiert und ist jetzt erfüllt.

**`data/integrity_lock.json`** – `layouts/pillar/single.html` ist eine
gesperrte Kerndatei (Klasse FEST). Die Layout-Änderung wurde nach dem Commit
bewusst neu signiert (`python3 scripts/integrity_guard.py --set-current`),
die Akte führt Commit, Grund und Herkunft. CSS und DESIGN.md stehen nicht
unter Siegel.

## 4 · Was bewusst NICHT geändert wurde

* **Kein Markup, keine Struktur, kein JavaScript** – die Templates des
  Rollouts vom 12.09.2026 sind korrekt; nur die CSS-Lieferung fehlte. Damit
  ist die Reparatur keine Layout-Variante im Sinne der Design-Governance
  (CLAUDE.md: „Layout-Umbauten gehören in eine Variante“): Es wird keine
  neue Gestaltung entworfen, sondern die in DESIGN.md §5 bereits
  spezifizierte und freigegebene Komponenten-Optik ausgeliefert.
* PaperMod-Basisklassen (`.post-title`, `.post-meta`, `.breadcrumbs`) bleiben
  führend; `.ff-pc-*` verfeinert nur dort, wo der Ratgeber-Kopf davon
  abweicht.

## 5 · Verifikation

* `hugo --destination …` – Build grün (211 Seiten, 1517 statische Dateien).
* **Klassenabdeckung, maschinell:** Brace-Matching-Parser über das gebaute
  HTML aller 6 Ratgeber-Seiten + 404 gegen die ausgelieferte (minifizierte)
  Inline-CSS: **24/24 `ff-pc-*`-Klassen je Ratgeber-Seite + 1 (`ff-pc-chip`)
  auf der 404 vollständig stylbar versorgt, 0 fehlend.** (25. Klasse
  `__cover--fallback` ist im CSS versorgt und tritt nur in Erscheinung, wenn
  ein Cluster-Beitrag ohne Cover erscheint.)
* Stand-Datum im Build: „📅 Stand: 28. September 2026“ ✓ (vorher: 28. Januar
  2026). Alle 6 Ratgeber geprüft.
* Minifier-Rücklesprobe: Alle Regeln liegen intakt in der Produktionssuite
  (Grid-/Karten-/Chip-/Dark-Regeln stichprobenartig gegen die minifizierte
  CSS geprüft, Klammerbilanz 0).
* `scripts/layout_audit.py` – 0 kaputte interne Links (2512 geprüft), DOM-
  Budget im Limit, Alt-Texte/Covers vollständig (einzige Warnung: known
  hreflang-Paginierungsbefund, vor der Änderung identisch, unrelated).
* `scripts/dom_audit.py` – alle Budgets grün (max. 1000 Elemente, Tiefe 13).
* `python3 -m unittest discover -s scripts/tests` – Vorher/Nachher-Diff der
  Failures: einzig neuer Befund war der erwartete Siegel-Drift
  (`test_ausgelieferter_baum_passt_zum_siegel`) bis zur Neu-Signatur; danach
  wieder Stand wie main (5 failures/14 errors sind Bestandsbefunde aus
  Content-/Workflow-Tests, von dieser Änderung unberührt – per
  git-stash-Vergleich belegt).
* **Browser-Verifikation (Playwright-Suite, design-metrics, design-shots)
  läuft in der CI dieses PRs** – im Sandbox-Betrieb ohne Browser nicht
  ausführbar; die 25 E2E-Tests greifen nicht auf `.ff-pc-*`-Selektoren zu
  (grepped), brechen also durch die Nachlieferung nicht.

## 6 · Folge-Auftrag an die Messung (nicht blockierend)

`e2e/design-shots.mjs` hat `/pillar/versicherungen/` in der Shot-Liste –
empfohlen: Screenshots der 6 Ratgeber-Seiten (hell+dunkel, Desktop+390px)
in den nächsten Design-Review aufnehmen, um die Nachlieferung visuell
zu archivieren.
