# Themenwelten: Umsetzung, Pflege und Schutz vor Rückfällen

Stand: 11.09.2026 · betrifft `/posts/` und die gemeinsame Themen-Navigation.

## Befund und Ursache

Auf der öffentlichen Blog-Übersicht standen „Ddeine6 Themenwelten“ und
„Hhierfindest du“. Beide Fehler lagen bereits in `content/posts/_index.md`;
es war kein Browser- oder Cache-Problem. Neben der Markdown-Themenliste gab
es sieben zusätzliche „Filter“-Links, die tatsächlich nur auf sechs
Ratgeber verwiesen. Namen und Beschreibungen wurden mehrfach separat gepflegt.

Der bestehende `textverstaendnis_guard.py` erkannte die Klebewörter (R9),
aber sein Bestandsmodus gab auch bei harten Funden **Exit 0** zurück. Der
Modus `--new-only` übersprang die Hub-Seite. Ein früherer Reparaturbericht
ersetzte damit keinen verbindlichen Auslieferungsschutz. Welcher historische
Text-Schreiber die ursprünglichen Artefakte eingefügt hat, ist damit nicht
bewiesen; die aktuelle Schutzlücke ist dagegen im Code nachvollziehbar.

## Neue Struktur

- **Eine Datenquelle:** `data/themenwelten.json` enthält Reihenfolge, Titel,
  Beschreibungen, Einleitung und Tipp. Blog, Startseite und die Themen-Namen
  der Ratgeber-Zentrale greifen darauf zu.
- **Ein Karten-Partial:** `layouts/_partials/themenwelten.html` rendert sechs
  vollständige Link-Karten mit lokalen SVG-Icons. Kein neues Client-JavaScript,
  keine externen Fonts/Bilder oder zusätzliche Bibliothek für die Navigation.
- **Echte Ziele:** Hugo löst jede Pillar-Seite per `site.GetPage` auf und nutzt
  deren `.RelPermalink`. Fehlende, als Entwurf markierte oder nicht gerenderte
  Ziele brechen den Build ab, statt still eine Karte zu verschlucken.
- **Live-Zähler:** Nur von Hugo veröffentlichte `posts` mit passendem `pillar`
  zählen. Bei null Artikeln bleibt der Einstieg als „Basis-Ratgeber“ sinnvoll.
- **Klare Reihenfolge auf `/posts/`:** kurze Einführung → Themen → neueste
  Artikel → Seitennavigation → Hilfetext/FAQ. Folgeseiten wiederholen die
  Themen und Einleitung nicht; ein Link führt zur Themenauswahl zurück.
- **Stabile Abschnittslinks:** `#deine-6-themenwelten` ist die kanonische H2.
  Der frühere Link `#ddeine6-themenwelten` bleibt als leerer, für Screenreader
  verborgener Kompatibilitätsanker erhalten. Der Tippfehler ist kein Text mehr.
- **Darstellung:** drei, zwei oder eine Kartenspalte je nach verfügbarem Platz;
  begrenzte Breiten nur für die Blog-Übersicht, nicht für Einzelartikel.
  Dunkelmodus, No-JS, sichtbarer Tastaturfokus, reduzierte Bewegung und
  System-Kontrastfarben werden berücksichtigt.

Die Themen-Komponente liegt **außerhalb** von `.post-content`. So wird sie
weder von Markdown-Insertern noch von der Artikel-Reveal-Animation oder den
Überschriften-Kopierknöpfen umgeschrieben/versteckt. Die schwebende
„Im Artikel“-Navigation wird auf der Blog-Übersicht nicht mehr erzeugt.

Ein zusätzlicher CSS-Ursachenfix begrenzt `li { text-wrap: pretty }` auf
Inhaltslisten: Die globale Regel hatte das geerbte `nowrap` des Hauptmenüs
überschrieben und „Über mich“ auf Mobilgeräten in zwei hohe Zeilen gebrochen.

### Warum nicht `hugo.Data` / `site.Data`?

Im vorhandenen `data/` liegen auch Bot-Protokolle (`*.jsonl`). Das erstmalige
Laden des gesamten Hugo-Datenbaums scheitert an diesen nicht unterstützten
Formaten; `site.Data` ist außerdem in der verwendeten Hugo-Version deprecated.
`themenwelten_data.html` liest deshalb gezielt nur die JSON-Navigationsdatei
mit `os.ReadFile | transform.Unmarshal`, gecacht pro Build. Die Protokolle und
Bot-Pfade bleiben unverändert.

## Texte und Themen pflegen

1. Namen, Beschreibungen und den Einstiegstext ausschließlich in
   `data/themenwelten.json` ändern. Nur Klartext, kein HTML/Markdown.
2. Die sechs IDs entsprechen den Verzeichnissen `content/pillar/<id>/`.
   Ein geänderter Link benötigt eine veröffentlichte, gerenderte Zielseite.
3. Neue Artikel bekommen im Frontmatter `pillar: "<id>"`. Den Zähler nicht
   von Hand pflegen; er folgt dem nächsten Build automatisch.
4. In `_index.md` **keine zweite Themenliste oder Themen-Überschrift** anlegen.
   Die Datei enthält Metadaten, den Blog-Einstieg und die nachgelagerte FAQ.
5. Keine Pagination-Aliase auf `/posts/page/2/` usw. setzen; das sind echte
   Hugo-Listenseiten. Der alte Themen-Anker darf nicht entfernt werden.

## Verbindliche Prüfungen

`scripts/themenwelten_guard.py` ist schreibfrei und benötigt keine externe
Python-Bibliothek oder API. Ein Fehler führt zu Exit 1:

- Schema, korrekter Titel und genau sechs eindeutige Themen;
- R8/R9-Textprüfung der Daten und der Hub-Quelle unabhängig vom Artikeldatum;
- fertiges HTML mit einem Themenbereich, sechs beschrifteten Karten, sauberen
  H2/H3, eindeutigen IDs und ohne verschachtelte Bedienelemente;
- reale Ratgeber- und Artikel-Zieldateien statt 404/Redirect-Platzhaltern;
- Artikelzähler stimmen mit den veröffentlichten Links im Ziel-Ratgeber überein;
- Sprungziele, Rückweg von Folgeseiten und keine doppelte Pseudo-Filterleiste;
- ein fehlender Build wird nicht als Erfolg übersprungen.

**Deploy-Verdrahtung:** Quellprüfung vor dem ersten Build, Auslieferungsprüfung
nach den Content-Heilungen und dem letzten Rebuild, vor TTS und dem Publish.
Beide Schritte sind verpflichtend, ohne `|| true` oder `continue-on-error`.
Ein Regressionstest prüft diese Position und die unveränderten Gate-Aufrufe.

**Zusätzliche CI:** `.github/workflows/themenwelten-gate.yml` testet Änderungen
auf Pull Requests und `main`, inklusive echter Chromium-Tests und eines
Unterverzeichnis-Builds. Sie verwendet das vorhandene Browser-Lockfile unter
`tools/ff-voice-browser/`. Die Tests sperren externe Netzwerkdienste und
überspringen einen fehlenden Browser nicht still. Browserabhängigkeiten sind
nur Testwerkzeuge, kein Bestandteil der ausgelieferten Website.

## Lokal prüfen

Mit Hugo Extended 0.164.0, Python 3.11+ und Node 22 auf dem PATH:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_themenwelten.py' -v
python3 scripts/themenwelten_guard.py --source-only
hugo --minify
python3 scripts/themenwelten_guard.py --public public
npm ci --prefix tools/ff-voice-browser --no-audit --no-fund
node scripts/themenwelten_browser_test.mjs --public public

hugo --minify --baseURL https://example.invalid/blog/ --destination tmp/themenwelten-subdir
python3 scripts/themenwelten_guard.py --public tmp/themenwelten-subdir --base-path /blog/
node scripts/themenwelten_browser_test.mjs --public tmp/themenwelten-subdir --base-path /blog/
```

Die Hugo-Negativtests arbeiten mit temporären Kopien des Inhalts, nicht am
Checkout: gelöschte/gesperrte/zukünftige Pillar-Ziele müssen den Build stoppen;
Entwürfe sowie zukünftige und abgelaufene Artikel dürfen nicht gezählt oder
verlinkt werden. Ohne installiertes Hugo laufen nur die Python-Vertragstests;
der CI-Job installiert Hugo ausdrücklich für die Integrationstests.

Geprüft bei dieser Änderung: 22 gezielte Python-Tests; 308 Browser-Assertions
je Root- und Unterverzeichnis-Build (Desktop, Tablet, 320/390 px, 200 %
Textgröße, Hell/Dunkel, No-JS, reduzierte Bewegung, Tastatur, sechs echte
Zielnavigationen und Pagination). Die Themen-Texte erreichten in beiden
Farbschemata mindestens 4,5:1 Kontrast. Der vollständige interne Linkcheck
meldete 2.549 geprüfte Links und keine defekten Ziele. Bestehende
Überschriften-/Kurzfassungs-Tests blieben grün.

Builds, Testbilder und lokale Logs gehören nach `public/` bzw. `tmp/` und
bleiben ignoriert. Die Reparatur ist erst nach Übernahme in `main` und einem
erfolgreichen regulären Deploy auf der öffentlichen Domain verfügbar.
