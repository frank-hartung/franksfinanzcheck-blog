# Recht-Update-Report

**Zweck:** Abgleich-Historie der Rechtstexte und rechtlichen Einordnungen des Blogs
(FranksFinanzcheck). Jeder Eintrag ist datiert, nennt die zugehörige Frist-ID aus
`data/recht-fristen.yaml` und bleibt auch nach Erledigung stehen. Neue Einträge
stehen oben.

**Hinweis:** Dies ist eine dokumentierte Selbsteinschätzung des Betreibers, keine
Rechtsberatung. Bei Zweifeln oder einer Änderung der Geschäftsmodelle wird eine
fachanwaltliche Prüfung empfohlen (siehe Abschnitt „Nächste Schritte“).

---

## Nachtrag 2026-11-10 · Unbelegte Herkunftsausnahmen fail-closed geschlossen (#1028)

**Frist-ID:** `ki-vo-kennzeichnung-bestand` (Frist 02.12.2026) ·
**Status: alle zwölf ungeklärten Register-Einträge entschieden; neun konservativ
gekennzeichnet, drei durch fassungsgebundene Redaktionsnachweise belegt.
Anbieter-Nachweise und betriebliche Freigabe bleiben menschliche Aufgaben.**
Dokumentierte technische Selbsteinschätzung, keine Rechtsberatung.

### Entscheidung statt Dauer-Eskalation

Die Wache meldete seit dem 07.11.2026 zwölf `menschlich`-Einträge ohne Beleg.
Drei Artikel besitzen inzwischen einen freigegebenen Prüfblock mit benannter
Redaktion, Prüfdatum und einem gegen die aktuelle Fassung neu berechneten
`inhalt_sha256`. Sie nutzen den bereits vorhandenen Redaktionspfad nach K2.
Die übrigen neun Artikel hatten keinen Prüfblock und wurden auf
`ai_generated: true` gesetzt. Das behauptet keine rekonstruierte Herkunft,
vermeidet aber eine unbelegte Nicht-Kennzeichnung.

`scripts/ki_kennzeichnung_gate.py` akzeptiert die Ausnahme jetzt nur noch mit
Status, Prüfername und -rolle, Prüfdatum und passendem Fassungs-Hash. Ein
Listeneintrag oder `status: freigegeben` allein reicht nicht mehr. Nach einer
Textänderung schlägt K2 fehl; die vorhandene Selbstheilung setzt konservativ
`ai_generated: true`, ohne einen Prüfblock zu erfinden. Sechs Unit-Tests und
der erweiterte Selbsttest sichern diesen Vertrag; die Suite läuft über
`npm run test:ki`. Die tägliche Wache führt Selbsttest, Heilung und beide
Regressionssuiten nun selbst aus und committet geheilte Artikel. Ein weiterer
Regressionstest stellt sicher, dass geklärte Einträge auch wirklich aus dem
Dauerzustand verschwinden statt als historische „offene“ Leichen zu bleiben.

### Messung und Live-Befund

Lokaler Hugo-Build: 121 Seiten, kein Fehler. `ki_provenienz_gate.py --gate`:
111/111 reguläre Seiten in 19 Abschnitten, 50 Feed-Items, 0 Funde.
`ki_kennzeichnung_gate.py --gate`, `ki_bild_markierung.py --gate` und die
KI-Unit-Suiten sind grün. Der Live-Stand aus `origin/gh-pages` (Artefakt
`305a07e`, Quelle `2b8c37c`) trägt Meta/scope/`describedby`, schema.org
`creditText`, das sichtbare KI-Stimmen-Siegel, den erreichbaren Impressum-Anker
sowie den `ffki:`-Feed-Kanal. Der aktuellste Deploy des Hauptbranches scheitert
am 10.11.2026 dagegen vor dem Build am separaten Weiterleitungs-Gate; dieser
allgemeine Auslieferungsbefund wird nicht als erfolgreiche neue Live-Abnahme
ausgegeben. Die drei fehlerhaft zusammengeführten GSC-Artefakte wurden in
diesem Paket auf den letzten konsistenten Messcommit `6c9d473` zurückgeholt;
Artefakt-Wache, Weiterleitungs- und Konsolidierungstests sind wieder grün.

### Weiterhin nicht automatisch abschließbar

Anbieterinventar und schriftliche Anbieterauskünfte nach Art. 50 Abs. 2,
Bildherkunft/Deepfake-Prüfung je tatsächlich verwendetem Bild und die finale
Betreiberfreigabe erfordern Tatsachen außerhalb des Repos. Kein KI-Cover wird
ohne Beleg deklariert. Der Workflow `erledigt=ki-vo-kennzeichnung-bestand`
wurde nicht ausgeführt.

---

## Nachtrag 2026-11-07 · Kanaltreue, Verbreitungsweg und Dauerwache (#1028)

**Frist-ID:** `ki-vo-kennzeichnung-bestand` (Frist 02.12.2026) ·
**Status: Betreiberebene auf sieben Kanälen vollständig und dauerhaft gesichert;
Anbieter-Nachweise, Bildherkunft und Live-Abnahme weiter offen. Frist bleibt
offen.** Selbsteinschätzung des Betreibers, keine Rechtsberatung.
**Akte:** `KI-VO-MASCHINENLESBAR-1028-KANALTREUE-DAUERWACHE-HIGHEND-2026-11-07.md`

### Anlass

Der Nachtrag vom 05.11.2026 meldete die maschinenlesbare Ebene als gebaut und
gegate. Am 07.11.2026 wurde **derselbe Baum gemessen statt gelesen**: Das Gate
war grün, der Bestand hatte trotzdem Lücken. Vier Befunde, alle am gebauten
Produkt belegt:

1. **Deckung.** Geprüft wurden 78 Seiten aus `content/posts`; ausgeliefert
   werden **109** reguläre Seiten in **19** Abschnitten. Die sechs
   Ratgeber-Säulen unter `pillar/` tragen eine synthetische Stimme und waren
   von keiner Regel erfasst.
2. **Kanaltreue.** Die Regel verglich das Signal gegen einen Textanker.
   Gemessen: 84 Seiten spielen eine Stimme ab, 66 zeigten einen Hinweis auf den
   **Text**, 18 zeigten sichtbar **nichts**. Ein halber Kanal war grün.
3. **Verbreitungsweg.** `public/index.xml` lieferte 50 Items, 45 mit
   `ai_generated: true`, **ohne** Herkunftsangabe – und aus diesem Feed
   publiziert Pinterest automatisch weiter. Der Verhaltenskodex der Kommission
   vom 10.06.2026 will gerade verhindern, dass Markierungen auf dem
   Verbreitungsweg verloren gehen.
4. **Robustheit.** Fiel PyYAML aus, starb das Gate mit Traceback und Exit 1
   („Inhaltsbefund"). Ein kaputtes Messwerkzeug sah aus wie ein roter Artikel –
   C33/C38 verletzt. Dazu: Der Bild-Optimizer kannte `cover.ai_generated` nicht
   und hätte aus einem deklarierten KI-Original unmarkierte, öffentlich
   erreichbare AVIF/WebP/JPEG-Geschwister erzeugt.

Rechtlich ändert das die Rollenverteilung nicht: Art. 50 Abs. 2 bleibt eine
**Anbieterpflicht** (Nachfrist bis 02.12.2026 für Systeme, die vor dem
02.08.2026 in Verkehr gebracht wurden). Was der Betreiber kann, ist die eigene
Erklärung maschinenlesbar zu machen und sie auf jedem Ausspielweg zu erhalten.
Genau das war unvollständig.

### Was jetzt gilt

Sieben Kanäle aus **einer** Quelle (`layouts/_partials/_funcs/ki_modalitaeten.html`):
Meta-Signale mit `scope` und `rel="describedby"`, schema.org `creditText`,
Bildattribute am `<img>`, IPTC `DigitalSourceType` in der Bilddatei,
**sichtbare Angabe zur Tonspur** je Modalität, **Feed-Kanal** auf Kanal- und
Item-Ebene, und der Schutz vor unmarkierten Bild-Ableitungen.

Regel M4 prüft Kanaltreue je Modalität **in beide Richtungen**; M1 prüft den
ganzen gebauten Baum. Werkzeugausfall ist Exit **2** über
`scripts/werkzeugbefund.py`, nicht Exit 1.

**Automatische Selbstheilung** (`ki_provenienz_gate.py --heilen`, `--wache`)
repariert nur, was mechanisch eindeutig ist – Impressum-Anker, Bytgleichheit
der RSS-Spiegelung, Entfernung unmarkierter Ableitungen – und schreibt jede
Heilung als Belegzeile nach `data/ki_provenienz_history.jsonl`. Was nur ein
Mensch entscheiden kann (Bildherkunft, tatsächliche redaktionelle
Verantwortung, Anbieteranfrage, widersprüchliche Vorlagenfassungen), wird
**eskaliert, nicht erfunden**. Eine Angabe ohne Beleg wird nie zu einer Angabe
mit Beleg geheilt.

Die Wache läuft bei jeder Änderung an Kennzeichnungs-Pfaden und täglich
(`.github/workflows/ki-provenienz-wache.yml`), im Deploy vor und nach dem
Build. Sie führt das Erst-Datum jedes ungeklärten `menschlich`-Eintrags und
nennt den Abstand zur Frist.

### Messung am 07.11.2026

`ki_provenienz_gate.py --gate`: **109/109** Seiten, 19 Abschnitte, **50**
Feed-Items, **0 Funde**. Selbsttest 12 Szenarien grün. 31 neue Unit-Tests plus
4 Kontrast-Tests (das Siegel wird aus `ff-voice.css` aufgelöst: **12.34:1**
hell, **12.28:1** dunkel). A11y-Audit 0 Probleme. Vorlese-Suiten 118/118,
265/265, 387/387. Spam-Wache F-OK. Bild-Optimizer 164 Quellen, 0 Probleme.
Gegenproben belegen, dass das Gate anschlägt (Siegel entfernt → 85 Funde;
Spiegel gebrochen → M7; Anker entfernt → M2; Werkzeug fehlt → Exit 2).

### Offen vor Fristabschluss

Die Punkte 1–4 des Nachtrags vom 05.11.2026 bleiben **unverändert offen**;
kein Punkt davon ist technisch heilbar. Neu ist die Messbarkeit: Die Wache
nennt die 12 ungeklärten `menschlich`-Einträge (14.08.–03.09.2026) jetzt mit
Alter und Fristabstand, statt sie zu übersehen. Zusätzlich ist die Live-Abnahme
(`docs/KI-TRANSPARENZ-ABNAHME.md` §4) um zwei Kanäle gewachsen: Tonspur (mit
und ohne JavaScript, helles und dunkles Thema) und Feed (`/index.xml` auf
Kanal- und Item-Ebene).

---

## Nachtrag 2026-11-05 · Maschinenlesbare KI-Kennzeichnung umgesetzt (#1028)

**Frist-ID:** `ki-vo-kennzeichnung-bestand` (Frist 02.12.2026) ·
**Status: maschinenlesbare Betreiberebene gebaut und gated; Anbieter-Nachweise
und Live-Abnahme weiter offen. Frist bleibt offen.**
Selbsteinschätzung des Betreibers, keine Rechtsberatung.

### Rechtslage am 05.11.2026 (neu geprüft, Stand gegenüber 03.11. erweitert)

Der Eintrag vom 03.11.2026 stützte sich auf die FAQ der Kommission. Seither
liegen die Durchführungsinstrumente final vor; sie ändern die Rollenteilung
nicht, benennen aber erstmals konkret, was „maschinenlesbar" heißen soll:

| Datum | Instrument | Was daraus folgt |
|---|---|---|
| 10.06.2026 | Verhaltenskodex zur Transparenz KI-generierter Inhalte (Art. 50 Abs. 7) | Abschnitt 1 = Anbieter (Markierung), Abschnitt 2 = Betreiber (Kennzeichnung). Geschichteter Ansatz: **digital signierte, zeitgestempelte Metadaten** plus **unwahrnehmbares Wasserzeichen**, optional Fingerabdruck/Register. Bei Freitext gilt die Wasserzeichenmaßnahme oberhalb von 200 Tokens. Beitritt freiwillig und je Abschnitt. |
| 08./09.07.2026 | Angemessenheitsbewertung von Kommission und KI-Ausschuss | Der Kodex gilt als geeigneter Nachweisweg für die von ihm adressierten Pflichten – er ersetzt die Verordnung nicht. |
| 20.07.2026 | Leitlinien der Kommission zu Art. 50, C(2026) 5054 final | Auslegungshilfe, u. a. zu Deepfakes und redaktioneller Kontrolle; enthält auch ein freiwilliges EU-Kennzeichnungssymbol. |
| 27.08.2026 | Verordnung (EU) 2026/1744 („Digital Omnibus") in Kraft | Verschiebt die Hochrisiko-Pflichten, **nicht** Art. 50. Einzige Erleichterung: Art. 50 Abs. 2 erst bis **02.12.2026** für Systeme, die vor dem 02.08.2026 in Verkehr gebracht wurden (Art. 113 n. F.). |
| 29.07.2026 | KI-MIG (Gesetz zur Durchführung der VO (EU) 2024/1689) in Kraft | **Bundesnetzagentur** ist zentrale Marktüberwachungsbehörde; Verstöße gegen Art. 50 sind nach Art. 99 Abs. 4 bußgeldbewehrt (bis 15 Mio. € oder 3 %, für KMU der niedrigere Betrag). |

Quellen: [Kommission: Verhaltenskodex](https://digital-strategy.ec.europa.eu/en/news/commission-publishes-code-practice-marking-and-labelling-ai-generated-content),
[EU-Kommission: FAQ zu Art. 50](https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act),
[eRecht24](https://www.e-recht24.de/ki/13539-deepfakes.html),
[IT-Recht Kanzlei](https://www.it-recht-kanzlei.de/ki-bilder-online-shop-kennzeichnungspflicht.html).
Zur Technik: IPTC-NewsCodes-Vokabular
[`digitalsourcetype`](http://cv.iptc.org/newscodes/digitalsourcetype/) (die
Werte `trainedAlgorithmicMedia` und `compositeWithTrainedAlgorithmicMedia`,
die C2PA in `c2pa.actions` übernimmt),
[IANA-Link-Relationen](https://www.iana.org/assignments/link-relations/link-relations.xhtml)
(geprüft: `describedby` und `c2pa-manifest` sind registriert),
[schema.org #3391](https://github.com/schemaorg/schemaorg/issues/3391)
(Stand 05.11.2026: **keine** fertige AI-Eigenschaft im Vokabular, daher
`creditText` statt einer erfundenen Eigenschaft) und
[WICG-Vorschlag #261](https://github.com/WICG/proposals/issues/261)
(HTML-Meta-Tag für KI-Inhalte ist Vorschlag, nicht Norm – `ai-generated`
deshalb als Betreiberangabe, nicht als Standard deklariert).
Recherchestand 05.11.2026; keine der Quellen ist eine Auskunft an diesen
Betreiber. Im Einzelfall bleibt fachanwaltliche Prüfung vorbehalten.

**Rollenklärung (unverändert, jetzt mit Belegkette):** Dieser Blog ist
**Betreiber** (er setzt fremde Modelle ein), nicht Anbieter. Die
maschinenlesbare Markierung der Ausgabe schuldet der Anbieter des jeweiligen
Systems – für Bestandssysteme bis 02.12.2026. Was der Betreiber schuldet, ist
die wahrnehmbare Offenlegung (Art. 50 Abs. 4/5) und – wenn er Inhalte unter
eigenem Namen weitergibt – der Nachweis, dass er die Anbieter-Markierung nicht
entfernt. Ein eigenes Meta-Tag ist deshalb keine Erfüllung von Abs. 2; es ist
eine **zusätzliche, maschinenlesbare Betreiberangabe**.

### Was gebaut wurde (maschinenlesbare Betreiberebene, vier Kanäle)

Vor diesem Nachtrag gab es genau einen maschinenlesbaren Haken: das lokale
`data-ff-ki-label` im sichtbaren Hinweistext – ein Selektor für eigene Tests,
für Dritte wertlos. Neu:

| Kanal | Wo | Was |
|---|---|---|
| Dokument-Meta | `layouts/_partials/ki_provenienz.html`, eingebunden in `head.html` | `<meta name="ai-generated" content="true">`, `<meta name="ai-generated-scope" content="text,image,audio">`, `<link rel="describedby" href="…/impressum/#ki-hinweis">` (bei IANA registrierte Relation) |
| Strukturierte Daten | `layouts/_partials/schema_article.html` | `creditText` am `Article`-Knoten, rollengetrennt: Text (Autor/Freigabe), Bild, Tonspur |
| DOM am Bild | `layouts/_partials/cover.html` | `data-ai-generated="true"` und `data-digital-source-type` im IPTC-Vokabular, nur bei belegter Erzeugungsart |
| Bilddatei selbst | `scripts/ki_bild_markierung.py` | IPTC `DigitalSourceType` als XMP-Paket im JPEG-APP1-Segment, **ohne Neukodierung**; optional `dcterms:provenance` auf ein C2PA-Manifest |

Bewusste Grenzen der Umsetzung:

- **`ai_generated: false` erzeugt kein Signal.** Die Abwesenheit ist keine
  Behauptung „rein menschlich"; das Register weist selbst ungeklärte
  `menschlich`-Einträge aus. Eine unbelegte Positivaussage wäre schlechter als
  keine Angabe.
- **Bild und Ton sind getrennt.** Die Tonspur (TTS) ist immer synthetisch und
  wird auf jeder Seite mit Lesehilfe ausgewiesen; das Cover nur bei belegter
  Bildherkunft. Text-, Bild- und Tonflag bleiben unabhängig.
- **Kein erfundener IPTC-Wert.** Ohne `cover.ki_pruefung.digital_source_type`
  (`trainedAlgorithmicMedia` oder `compositeWithTrainedAlgorithmicMedia`) wird
  weder geschrieben noch im DOM behauptet.
- **Fremde Metadaten werden nicht still überschrieben.** Enthält eine Datei
  bereits abweichendes XMP, blockiert das Werkzeug und verlangt eine bewusste
  Entscheidung (`--force`) – im Sinne des Kodex, vorhandene Markierungen zu
  erhalten.
- **Kein HTTP-Header.** GitHub Pages setzt keine Header, und eine globale
  Transform Rule wäre für 12 von 108 Artikeln ohne KI-Text eine falsche
  Aussage. Bewusst nicht gebaut.
- **Kein C2PA-Signaturdienst.** Signieren braucht Betreiber-Schlüssel und
  `c2patool`; das gehört nicht unbeaufsichtigt in den Deploy. Vorgesehen ist
  der Verweis auf ein externes Manifest (`c2pa_manifest_url`).

### Dauerhaft gesichert

`scripts/ki_provenienz_gate.py` (Regeln M1–M4) läuft im Deploy **nach** dem
Build: M1 prüft das Meta-Signal in jeder gebauten Seite gegen das
Frontmatter, M2 den Vorlagenvertrag (Einbindung, `creditText`,
`data-digital-source-type`, Impressum-Anker), M3 die Bilddatei, M4 die
Kanaltreue (maschinenlesbares Signal nur zusammen mit dem sichtbaren Hinweis).
`scripts/ki_bild_markierung.py --gate` meldet deklarierte KI-Cover ohne
IPTC-Feld. Beide sind im Blustradius-Register als `inhalt` eingetragen und
dürfen blockieren; die Selbsttests sind als `gate-selbsttest` registriert.
NPM-Zugänge: `ki:provenienz[:gate]`, `ki:bild[:gate|:markieren]`, `test:ki`.

### Prüfergebnisse dieser Änderung (lokal, Hugo 0.169.0, Pillow 13.0.0)

- `scripts/ki_provenienz_gate.py --gate`: **76 gebaute Artikelseiten geprüft,
  0 Funde** (96 von 108 Artikeln tragen `ai_generated: true`, 12 nicht;
  32 Entwürfe sind nicht gebaut).
- `scripts/schema_seo_gate.py --gate`: 408 gebaute Seiten, 82 Money-Pages,
  **0 harte Funde** – `creditText` bricht das Schema nicht.
- `scripts/ki_bild_markierung.py --selftest` und
  `scripts/tests/test_ki_bild_markierung.py`: echter Rundlauf an einem JPEG –
  Feld lesbar, **Pixel-SHA-256 vor und nach der Markierung identisch**,
  Segmentkette führt weiter auf den Start of Scan, idempotent, PNG abgelehnt.
  Gegenprobe am realen Blog-Cover: Pixel-SHA `97d0d7be7af7f62d…` unverändert,
  Datei +909 Bytes, unabhängiger Leser (Pillow/defusedxml) erkennt
  `DigitalSourceType`.
- `scripts/tests/test_ki_provenienz_render.py`: 6 Render-Fälle mit echten
  Vorlagen grün; `python3 -m unittest` über die KI- und Schema-/DOM-/Editorial-
  Tests: 23 + 136 Tests grün.
- **0 Cover sind derzeit als KI deklariert.** Die Bildebene ist damit
  Infrastruktur für den ersten belegten Fall, kein Vollzug am Bestand.

### Offen vor Fristabschluss (unverändert zum 03.11.)

1. Anbieter-Inventar und schriftliche Auskunft je Anbieter zur
   Art.-50-Abs.-2-Markierung (Vorlage: `docs/KI-TRANSPARENZ-ABNAHME.md`).
2. Bildherkunft und Deepfake-Prüfung je tatsächlich verwendetem Bild und
   Ausspielweg; erst danach `cover.ai_generated` und IPTC-Wert setzen.
3. Register `data/ki_kennzeichnung.yaml`: ungeklärte `menschlich`-Einträge
   gegen die veröffentlichte Fassung prüfen.
4. Live-Abnahme nach erfolgreichem offiziellen Deployment (Runbook
   `docs/KI-TRANSPARENZ-ABNAHME.md`, Abschnitt 4) und Betreiberfreigabe.
   Erst danach den Workflow mit `erledigt=ki-vo-kennzeichnung-bestand`
   ausführen. Issue #1028 und Frist bleiben bis dahin offen.

**Neu offener Punkt:** Die Ausspielwege OG-Bild, Pinterest-Pin und
RSS/Feeds tragen die neuen Angaben nicht. Für Text ist das unschädlich
(keine Deepfake-Pflicht ohne öffentliches Interesse), für ein künftig
deklariertes KI-Cover müssten OG-/Pinterest-Dateien gesondert markiert oder
die Ausspielung unterbunden werden.

---

## Nachtrag 2026-11-04 · Betreiberfreigabe des Integritäts-Locks (#1056)

Nach ausdrücklicher Betreiberentscheidung wurden die drei im folgenden
Nachtrag genannten Kernänderungen mit `--set-current` neu signiert. Die
Herkunft ist in `data/integrity_lock.json` und `data/integrity_history.jsonl`
festgehalten; das lokale Integritäts-Gate war danach grün. Bei der späteren
Integration des fortgeschriebenen `main` wurde dessen gültiges Siegel als
Grundlage genommen und ausschließlich dieselben drei freigegebenen Dateien
erneut signiert; die vorherige Signatur bleibt in der Git-Historie erhalten.
Dies ersetzt weder
die noch ausstehenden Anbieter- und Bildherkunftsnachweise noch die
Live-Abnahme nach einem offiziellen Deployment.

---

## Nachtrag 2026-11-04 · Stand des Integritäts-Locks und CI (#1051)

Im aktuellen Ausgangsstand `038b04f` ist das Integritäts-Siegel nach
`--repair-lock --dry-run` gültig und verkettet; der historische Befund vom
03.11. bleibt als damalige Beobachtung bestehen. Das Gate meldet die drei
hier geänderten geschützten Dateien (`head.html`, `cover.html`,
`generate_covers.py`) als nicht signiert. Zu diesem Zeitpunkt standen Betreiberfreigabe und Neu-Signatur noch aus;
siehe den späteren Nachtrag darüber. Die Deployment-Schritte sind im Blustradius-Register erfasst.
Der neue Bestandsschutz läuft auch im PR-Test bei Änderungen an Originalbildern.

Aktuelle lokale Probe mit Pillow 13.0.0: 114 Referenzen auf 113 Dateien,
80 byteidentisch und 33 abweichend; keine als KI deklariert. Weder die
Bytegleichheit noch eine Abweichung beweist die tatsächliche Herkunft. Der
Hugo-Produktionsbuild und 29 gezielte Tests waren erfolgreich; der
Integritäts-Test war zu diesem Zeitpunkt wegen der unsignierten Kernänderungen rot. Eine
Live-Abnahme und Anbieterbestätigungen liegen nicht vor.

---

## Nachtrag 2026-11-03 · Reproduktionsprobe und Deploy-Blocker

Die dateigenaue Reproduktionsprobe
`python3 scripts/ki_cover_render_audit.py --json` erzeugt jedes referenzierte
Cover anhand des Manifest-Titels, Badges und der Spar-Pille in einem
Temp-Verzeichnis neu und vergleicht Hash und Pixel. Sie verändert keine
Originale. Der [Einzelbeleg](data/beweise/ki-cover-render-audit-2026-11-03.json)
enthält Quellpfade, Bildhash, Vergleichshash und Hashes von Generator, Schrift
und Manifest. Ergebnis im Checkout mit Pillow 13.0.0: **113 Referenzen auf
112 Dateien, davon 80 byteidentisch und 32 abweichend**. Betrachtet man nur
Dateien, die mindestens eine Seite ohne `draft: true` referenziert, sind es
81 Dateien: 61 byteidentisch, 20 abweichend. `draft: false` ist kein Nachweis
der tatsächlichen Live-Auslieferung. Bei byteidentischen Dateien kann die
regelbasierte Pipeline denselben Dateiinhalt reproduzieren; das ist ein
starkes technisches Indiz, aber weder ein historischer Erzeugungsnachweis noch
ein KI-Detektor. Die 32 Abweichungen sind nicht automatisch KI-Bilder. Die
Einzelprüfung und externe Herkunftsdaten bleiben erforderlich. Änderungen am
Bestand entwerten die Momentaufnahme; für neue Entscheidungen erneut prüfen.

Beim im letzten Nachtrag genannten Deploy-Fehler ließ sich der konkrete
Rückfallschutz im lokalen Checkout reproduzieren: Zwei Gasartikel trugen
wieder unbelegte Preis- und Ersparnisversprechen in `pin_description`. Die
Quelle `data/pinterest_plan.yaml` hätte sie beim Pin-Sync erneut eingespielt.
Frontmatter und alle drei betroffenen Plan-Beschreibungen zum ersten Artikel
sowie die Beschreibung zum zweiten Artikel wurden sachlich bereinigt; der
Rückfallschutz prüft jetzt auch die Planquelle. Der Test läuft lokal grün.
Dies belegt nicht, dass der vollständige nächste Deploy oder das
Auslieferungs-Siegel erfolgreich sein wird; Laufprotokolle des alten Jobs
waren aus der Sandbox nicht abrufbar.

Zusätzlicher Integritätsbefund: `scripts/integrity_guard.py --gate` meldet im
Checkout ein bereits beschädigtes `data/integrity_lock.json`; die
`--repair-lock --dry-run`-Probe fand im flachen Klon keine belegte gültige
Quelle. Ein gezielter lesender GitHub-API-Abgleich fand in Commit
`8af76b5520fba6a073d20630db356546f73237a4` vom 01.11.2026 ein strukturell
intaktes älteres Siegel (Kette und Map-Prüfsumme laut `lock_zustand`). Von
seinen 55 Dateihashes weichen sieben vom Arbeitsbaum ab oder fehlen, darunter
die in dieser Arbeit geänderten `cover.html`, `head.html` und
`generate_covers.py`; es wäre also kein unveränderter Wiederherstellungsstand.
Die beiden jüngeren geprüften Fassungen `c2c83bf` und `cf1b807` sind kein gültiges
JSON. Das ältere Siegel ist nicht auf Übereinstimmung mit dem heutigen Kern
freigegeben und wurde **nicht** übernommen. Zudem ist
`scripts/generate_covers.py` für den Schutz deklarierter KI-Originale geändert
und eine geschützte Kerndatei. **Keine** menschliche
Neu-Signatur oder Freigabe wurde fingiert. Betreiber muss den Lock anhand
vollständiger Historie prüfen/reparieren und die Änderung bewusst freigeben,
bevor ein grünes Integritäts-Gate behauptet werden darf.

---

## Nachtrag 2026-11-03 · Anbieter, Cover-Bestand und Live-Stand (#1028)

**Status: technische Sicherungen ergänzt; Fremdnachweise und Live-Abnahme offen.**

### Anbieter-Recherche: Beleglage, keine erfundene Anbieterbestätigung

`data/ki_redaktion.yaml`, `scripts/llm_client.py` und die Laufdaten im Repo
zeigen als konfigurierte Textpfade Groq, NVIDIA NIM und Cloudflare Workers AI
mit `openai/gpt-oss-120b` (Workers-AI-ID mit `@cf/`) sowie Gemini als Fallback.
Umgebungsvariablen können Modell/Anbieter ändern; Konfiguration ist kein Beweis,
dass ein bestimmter Dienst zuletzt produktiv genutzt wurde. Die Sprachpipeline
`ff_voice_audio.py` nennt ElevenLabs, Microsoft Edge TTS und Piper als mögliche
Backends; tatsächlich verwendete Varianten sind gesondert zu inventarisieren.

| Quelle des Anbieters | Was sie belegt | Was offen bleibt |
|---|---|---|
| [OpenAI: gpt-oss](https://openai.com/index/introducing-gpt-oss/) | Open-weight-Modell, anderweitig betreibbar. | Kein Beleg für eine Markierung beim konkreten Hosting. |
| [Groq Services Agreement, § 6](https://console.groq.com/docs/legal/services-agreement) | Verbietet u. a. das Verändern ggf. vorhandener Provenienzinformationen. | Ob konkret genutzte Ausgaben markiert sind, Methode, Erkennung und Zeitpunkt. |
| [Cloudflare Responsible AI](https://www.cloudflare.com/trust-hub/responsible-ai/) und [Cloudflare: Watermark-Forschung](https://blog.cloudflare.com/an-early-look-at-cryptographic-watermarks-for-ai-generated-content/) | Cloudflare beschreibt Drittanbieter-Modelle und technische Forschung. | Keine produktspezifische Bestätigung für unser Workers-AI-Modell. |
| [NVIDIA Risk Assessment](https://images.nvidia.com/content/pdf/NVIDIA-Frontier-AI-Risk-Assessment.pdf) | Beschreibt mögliche Markierungstechniken allgemein. | Kein Nachweis für unsere konkrete NIM-Ausgabe. |
| [Google DeepMind: SynthID für Text](https://deepmind.google/blog/watermarking-ai-generated-text-and-video-with-synthid/) | Erklärt Verfahren und Grenzen bei Umarbeitung. | Nicht der Nachweis, dass die konkret genutzte Gemini-API-Fassung markiert ist oder nach Bearbeitung erkennbar bleibt. |
| [Gemini API: Bilder](https://ai.google.dev/gemini-api/docs/image-generation) | Google beschreibt SynthID für dort generierte Bilder. | Nicht der Nachweis, dass irgendein Blog-Cover damit entstand oder nach Konvertierung erkennbar bleibt. |

Diese Quellen wurden am 03.11.2026 recherchiert. Es gibt hier **keine** belegte
Anfrage oder Antwort von Groq, NVIDIA, Cloudflare, Google oder TTS-Anbietern.
Anfragevorlage und Abnahmeverfahren: `docs/KI-TRANSPARENZ-ABNAHME.md`.
Die Rolle je konkretem Produkt und alle Ausspielwege sind noch zu klären.

### Cover und Auslieferung

Das reproduzierbare Inventar `python3 scripts/ki_cover_provenienz.py --json`
zählte im Checkout am 03.11.2026 **113 Cover-Referenzen** über alle Bereiche,
darunter 82 nicht als Entwurf markierte und 31 Entwürfe; keine Referenz war
als KI-Bild deklariert. Alle 82 nicht als Entwurf markierten Referenzen hatten
lokale Originale und einen namensgleichen Eintrag in `data/covers_manifest.json`.
Das Manifest allein ist ein Indiz für die Pillow-Cover-Pipeline, aber **kein**
Datei-Hash oder Herkunftsnachweis; die spätere dateigenaue Reproduktionsprobe
steht im Nachtrag darüber. Auch Entwurfsstatus ist keine Live-Zählung; Inline-Bilder,
Dateien ohne Cover-Referenz und externe Kanäle sind nicht enthalten.

Die neue Wache prüft für deklarierte KI-Cover Original-SHA-256, Quellenangabe,
Prüfdatum und ausdrückliche Deepfake-Einzelfallprüfung. Bei Deepfake oder
fehlendem/veraltetem Nachweis wird Deploy gestoppt, weil OG, Pinterest und
weitere Ausspielwege nicht automatisch eine sichtbare Kennzeichnung tragen.
Das Flag ist keine automatische Herkunftserkennung. Für diese Covers liefert
Hugo die lokale Originaldatei statt neu encodierter Varianten aus; der
Cover-Generator schützt deklarierte Originale auch bei `--force`. Diese
Maßnahmen bestätigen weder die Echtheit eines Nachweises noch die Erhaltung
unsichtbarer Wasserzeichen durch externe Dienste oder CDNs.

**Live-Baseline:** Am 03.11.2026 war das [Impressum](https://franksfinanzcheck.de/impressum/)
abrufbar und zeigte noch den alten KI-Wortlaut. Das jüngste über die
GitHub-Pages-API sichtbare Deployment vom 02.11.2026 trägt SHA
`69f08c40c654e63eda3d8030eec790ee85fdbaf1`, nicht diesen Arbeitsstand.
Der jüngste Deploy-Lauf [41592649761](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/41592649761)
endete mit Fehler in „Faktenfrische Gas – Rückfallschutz“ und im
Auslieferungs-Siegel. Die Live-Baseline ist daher **keine Abnahme dieser
Änderung**. Nach Integration und erfolgreichem Deployment müssen die im
Runbook genannten Text-, Cover-, Listen-, Datei- und Social-Proben erneut
an der live ausgelieferten Fassung erfolgen. Frist und Issue bleiben offen.

---

## Eintrag 2026-11-03 · KI-Transparenz und Bestandssysteme (Issue #1028)

**Frist-ID:** `ki-vo-kennzeichnung-bestand` · **Status: teilweise umgesetzt,
Betreiberprüfung und Anbieter-Nachweise offen; Frist nicht erledigt.**
Dies ist eine technische und redaktionelle Selbsteinschätzung, keine Rechtsberatung.

### Quellen und Einordnung (geprüft am 03.11.2026)

- [EU-Kommission: FAQ zu Art. 50](https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act):
  Art. 50 Abs. 2 verpflichtet **Anbieter** generativer KI zur
  maschinenlesbaren Markierung und Erkennbarkeit ihrer Ausgaben; bei vor
  02.08.2026 in Verkehr gebrachten Systemen ist diese Pflicht bis 02.12.2026
  zu erfüllen. Für neue Systeme gilt kein solcher Aufschub. Maßgeblich ist
  das Inverkehrbringen des Systems, nicht das Alter eines Blogbeitrags.
- Dieselbe FAQ unterscheidet davon die seit 02.08.2026 anwendbare
  **Betreiberpflicht** aus Abs. 4: Deepfakes sichtbar bzw. hörbar offenlegen;
  bei KI-Texten zur Information der Öffentlichkeit über Angelegenheiten von
  öffentlichem Interesse entfällt die Offenlegung nur bei tatsächlicher
  menschlicher Überprüfung oder redaktioneller Kontrolle **und** wenn eine
  natürliche oder juristische Person die redaktionelle Verantwortung trägt.
  Bloße Rechtschreib- oder automatische Qualitätsprüfung genügt nicht.
  Finanzratgeber sind vorsorglich einzeln auf öffentliches Interesse zu prüfen.
- [eRecht24: Deepfakes und Textausnahme](https://www.e-recht24.de/ki/13539-deepfakes.html)
  und [IT-Recht Kanzlei: KI-Bilder und Produkttexte](https://www.it-recht-kanzlei.de/ki-bilder-online-shop-kennzeichnungspflicht.html)
  bestätigen die Differenzierung. Die Kommission erläutert zudem, dass vor
  02.08.2026 erzeugte Inhalte nicht rückwirkend gekennzeichnet werden müssen;
  freiwillige Kennzeichnung bleibt sinnvoll. Im Einzelfall Rechtsstand prüfen.

### Entscheidung und Umsetzung

Ein allgemeiner Impressum-Hinweis allein ist **kein Ersatz** für einen ggf.
notwendigen klaren Hinweis am konkreten Inhalt bei erster Wahrnehmung. Ein
HTML-Meta-Tag, ein `data-`Attribut oder ein Footer sind kein Nachweis für die
robuste, interoperable Anbieter-Markierung der Ausgabedatei nach Abs. 2.
Keine pauschale Behauptung einer erfüllten Anbieterpflicht oder C2PA-Signatur.

- Artikel mit `ai_generated: true` zeigen nun „Mit KI erstellt oder bearbeitet“
  am Artikelanfang, auch wenn eine redaktionelle Freigabe vorliegt. Der alte
  Wortlaut „Mit KI-Unterstützung recherchiert“ deckte das Erstellen nicht ab.
  Das `data-ff-ki-label` ist lediglich ein lokal maschinenlesbarer HTML-Haken,
  kein Wasserzeichen. Das Gate kann bei ungeklärter Herkunft vorsorglich
  `true` setzen: Das ist keine verifizierte Provenienz.
- Bild und Text werden getrennt behandelt: Nur bei **belegter** KI-Erzeugung
  oder -Bearbeitung eines Covers `cover.ai_generated: true` im Frontmatter
  setzen. Dann erscheint die sichtbare Bildunterschrift im Artikel **und** in
  Listen. Andere Covers bleiben unverändert; bestehende Bildunterschriften
  bleiben erhalten. Beispiel:

  ```yaml
  cover:
    image: images/covers/beispiel.jpg
    alt: Beschreibung des Bildinhalts
    ai_generated: true
    ki_pruefung:
      sha256: "<SHA-256 der unveränderten Originaldatei>"
      quelle: "<konkreter Herkunftsnachweis>"
      geprueft_am: 2026-11-03
      deepfake: false # nur nach tatsächlicher Einzelfallprüfung
  ```

  Die eigene `scripts/generate_covers.py`-Pipeline zeichnet Branding-Cover
  mit Pillow regelbasiert; KI-Text im Cover macht das Bild nicht automatisch
  zu einem KI-generierten Bild. Ein Flag wird deshalb nicht pauschal gesetzt.
  Ein neuer Bildnachweis muss sich auf die tatsächlich ausgelieferte Datei
  beziehen und bei Austausch/Neugenerierung aktualisiert werden. Es wurde
  kein einzelnes Bestandsbild als KI-generiert verifiziert.
- Der Hinweis gilt für das Hugo-Cover auf diesen Seiten, **nicht** automatisch
  für OG-/Pinterest-Dateien, externe Plattformen, RSS, einzelne andere Bilder
  oder heruntergeladene Bilddateien. Falls ein Deepfake dort erscheint, vor
  Veröffentlichung auf jedem Ausspielweg gesondert sichtbar kennzeichnen
  oder die Ausspielung unterbinden. Bildunterschrift ersetzt keine
  Provider-Markierung; Varianten und Metadaten nach Umwandlung prüfen.
- Das Widget ist in `layouts/baseof.html` eingebunden, aber laut
  `layouts/_partials/ki_assistent.html` ohne konfigurierten Endpoint deaktiviert;
  im eingecheckten `hugo.toml` ist keiner gesetzt. Eine Aussage über eine
  abweichende Live-/Deploy-Konfiguration ist damit nicht belegt. Vor
  Aktivierung Interaktionshinweis und Verantwortlichkeiten erneut prüfen.

### Offen vor Fristabschluss

1. Betreiber inventarisiert tatsächlich eingesetzte Text-/Bild-/Audio-Systeme,
   Anbieter, Versionen, Rolle (auch mögliche Eigenanbieterrolle) und Datum des
   Inverkehrbringens; fragt Anbieter nach Art.-50-Abs.-2-Markierung,
   Erkennbarkeit und deren Grenzen und dokumentiert Antworten. Das Repo nennt
   z. B. in `scripts/ki_shared.py` Groq, NVIDIA, Cloudflare und Gemini; welche
   davon aktuell produktiv genutzt werden und wie sie markieren, ist offen.
2. Betreiber prüft alle real verwendeten Bilder und Ausspielwege auf Herkunft
   und Deepfake-Risiko, setzt nur belegte Flags und dokumentiert Entscheidungen.
   Auch eine Bildgenerierung außerhalb des Repos ist möglich; aus dem Repo
   allein ist Vollständigkeit nicht belegbar.
3. Das Register `data/ki_kennzeichnung.yaml` enthält selbst als ungeklärt
   beschriebene `menschlich`-Einträge; ein bloßer `freigegeben`-Status im
   Kennzeichnungsgate beweist keine tatsächliche Prüfung. Betreiber muss diese
   Einträge und die jeweilige veröffentlichte Fassung prüfen, gegebenenfalls
   kennzeichnen; automatische Prüfungen nicht als menschliche Freigabe ausgeben.
4. Nach Merge/Deploy Live-Artikel, Listen und ggf. externe Ausspielungen prüfen;
   Freigabe und ggf. Rechtsberatung dokumentieren. Erst danach den vorgesehenen
   Workflow mit `erledigt=ki-vo-kennzeichnung-bestand` ausführen. Issue #1028
   und Fristenstatus bleiben bis dahin offen.

**Regression:** `scripts/tests/test_ki_transparenz_render.py` rendert echte
Hugo-Fixtures für KI-Text, Freigabe, KI-Bild und unbekannte Bildherkunft; der
Deploy führt den Test aus. Der Test belegt weder Bildinventar noch Rechtskonformität.

---

## Eintrag 2026-10-11 · Tarifcheck-Anbieterkennzeichnung im Impressum

| | |
|---|---|
| **Frist-ID** | keine (Umsetzung einer Programm-Vorgabe, kein Fristen-Eintrag) |
| **Kategorie** | Anbieterkennzeichnung / Datenschutz |
| **Ergebnis** | iframe des Tarifcheck-Partnerprogramms im Impressum, Datenschutzhinweis ergänzt |

Das Partnerprogramm verlangt die Einbindung von
`a.partner-versicherung.de/filestore/ad/1166/` mit der Partner-ID 47086.
Das Snippet allein wäre 150 px hoch und mit `scrolling="no"` abgeschnitten.
Es liegt deshalb in `layouts/shortcodes/partner_impressum.html` (nicht im
Markdown, damit der Affiliate-Shield die URL nicht auf eine `/go/`-Route
umbiegt), mit Titel, ausreichender Höhe, Fallback-Link und Hinweis auf den
Datenabruf.

Die Datenschutzerklärung nennt den Abruf beim Seitenaufruf, die Rechtsgrundlage
Art. 6 Abs. 1 lit. f DSGVO und die offene Prüfung zu Cookies und § 25 TDDDG.
Eine Einwilligungs-Wand vor dem Dokument wurde nicht gesetzt: die Kennzeichnung
soll im Impressum sichtbar sein. Ob das Dokument Cookies setzt, ist an der
Live-Antwort noch nicht geprüft.

Dies ist eine dokumentierte Umsetzung, keine Rechtsberatung.

---

## Eintrag 2026-10-10 · BFSG-Scope-Bewertung

| | |
|---|---|
| **Frist-ID** | `bfsg-barrierefreiheit-bewertung` (Issue #689) |
| **Kategorie** | Barrierefreiheit |
| **Gewicht** | Empfehlung (einmalig) |
| **Fällig am** | 31.10.2026 |
| **Ergebnis** | Kein BFSG-Scope. Die Bewertung stützt sich auf zwei unabhängige Gründe. |

### Kurz-Bewertung

Das Barrierefreiheitsstärkungsgesetz (BFSG, in Kraft seit 28.06.2025) erfasst
Dienstleistungen im elektronischen Geschäftsverkehr, also digitale Dienste, die
auf individuelle Anfrage eines Verbrauchers im Hinblick auf den Abschluss eines
Verbrauchervertrags erbracht werden. FranksFinanzcheck schließt selbst keine
Verbraucherverträge ab. Die Werkzeuge rechnen im Browser, die Artikel informieren,
und die Partnerlinks führen zu Verträgen, die Dritte (CHECK24, Tarifcheck) mit den
Lesern schließen. Selbst wenn ein Teil davon als Dienstleistung im Sinne des BFSG
gälte, greift für Kleinstunternehmen die Ausnahme des § 3 Abs. 3 Satz 1 BFSG für
Dienstleistungen, sofern die Schwellen (weniger als zehn Beschäftigte, Jahresumsatz
oder Bilanzsumme jeweils höchstens 2 Mio. €) erfüllt sind. Diese Angaben sind vom
Betreiber noch zu bestätigen (siehe unten). Der Blog verkauft keine Produkte, auf
die die Ausnahme nicht anwendbar wäre.

### Prüfrahmen

- **Rechtsgrundlage:** BFSG (Fassung ab 28.06.2025), insbesondere
  - § 1 Abs. 3 Nr. 5: Dienstleistungen im elektronischen Geschäftsverkehr,
  - § 2 Nr. 26: Definition (digitale Dienste über Webseiten oder Apps, elektronisch
    und auf individuelle Anfrage eines Verbrauchers im Hinblick auf den Abschluss
    eines Verbrauchervertrags),
  - § 3 Abs. 3 Satz 1: Ausnahme für Kleinstunternehmen, die Dienstleistungen
    anbieten oder erbringen (gilt nicht für Produkte),
  - § 2 Nr. 17: Definition Kleinstunternehmen (weniger als zehn Personen und
    Jahresumsatz oder Jahresbilanzsumme jeweils höchstens 2 Mio. €).
- **Quellenstand:** Abgleich über Fachkommentierungen (u. a. IHK München, Stand
  2026; sitebrunch-Überblick). Vor einer Veröffentlichung ist der amtliche
  Gesetzestext zu prüfen. Die Paragrafen sind in dieser Fassung aus der
  Sekundärliteratur übernommen.

### Prüfung der Angebotsbestandteile

| Bestandteil | Vertragsabschluss durch den Betreiber? | Einordnung |
|---|---|---|
| Ratgeber-Artikel (`content/posts`, Pillar-Seiten) | nein | Kein BFSG-Scope |
| Werkzeuge (Rechner, Kündigungsfristen-Kalender, Tarifwechsel-Entscheidungsbaum, Budget) | nein, Berechnung im Browser | Kein BFSG-Scope |
| Fixkosten-Cockpit | nein, Speicherung lokal im Browser | Kein BFSG-Scope |
| Newsletter (kostenlose Anmeldung) | nein, kein Entgelt | Kein BFSG-Scope; Restrisiko gering |
| Affiliate-Links zu CHECK24 und Tarifcheck | nein, der Vertrag kommt bei Dritten zustande | Grauzone bei der Vermittlung; hier trägt die Kleinstunternehmen-Ausnahme |
| Verkauf von Produkten (Shop, E-Books, Merchandise) | nicht vorhanden | Ausnahme gilt nicht für Produkte, daher Neubewertung bei Einführung |

### Tragende Begründung

1. **Kein eigener Verbraucher-Vertragsabschluss.** Die Angebote informieren oder
   rechnen. Ein Vertrag entsteht immer bei einem Dritten.
2. **Kleinstunternehmen-Ausnahme (§ 3 Abs. 3 Satz 1 BFSG).** Der Betreiber tritt
   als natürliche Person auf (Impressum: Frank Hartung, ohne Firmenzusatz). Die
   Schwellen sind nachzuweisen (siehe „Zu bestätigen“).

### Zu bestätigen (Betreiber)

- [ ] Anzahl der Beschäftigten (einschließlich Inhaber) unter zehn.
- [ ] Jahresumsatz oder Jahresbilanzsumme jeweils höchstens 2 Mio. €
  (Nachweis: letzter Steuerbescheid bzw. Jahresabschluss oder EÜR).

Solange diese Punkte nicht bestätigt sind, gilt die Bewertung als vorläufig.

### Neubewertung auslösen, wenn …

- ein Shop oder Produktverkauf eingeführt wird (auch E-Books, Printprodukte, Merchandise),
- Terminbuchungen oder Vertragsabschlüsse direkt auf der Website angeboten werden,
- ein Vermittlungsangebot mit eigenem Abschluss im Haus entsteht (keine reinen
  Affiliate-Links),
- die Kleinstunternehmen-Schwellen überschritten werden,
- das BFSG oder die Auslegung durch die Marktüberwachung geändert wird.

### Goodwill-Nachweis: Stand Barrierefreiheit (Verweis)

Der Blog betreibt unabhängig von der Pflicht ein laufendes Barrierefreiheits-Audit:

- **Automatisches Audit:** `scripts/a11y_audit.py` prüft gebaute Seiten auf
  lang-Attribut, Seitentitel, genau eine H1, alt-Texte, Skip-Link, sichtbare
  Fokus-Styles, `prefers-reduced-motion` und Kontrast der Branding-Farben
  (WCAG-2.1-Teilmenge). Seit der Härtung vom 07.10.2026 läuft es über alle gebauten
  Seiten statt über eine Stichprobe von 20 Seiten.
- **Stand 08.10.2026:** 85 Seiten vollständig geprüft, 0 Befunde, 0 Kontrast-Fehler
  (Quelle: `A11Y-EINE-H1-DAUERHEILUNG-PREMIUM-2026-10-08.md`, Abschnitt „Nachweis“).
  Vorgängerbericht: `A11Y-EINE-H1-DAUERHEILUNG-PREMIUM-2026-10-07.md`.
- **Grenzen:** Ein automatisches Audit deckt nur einen Teil der WCAG ab. Der Blog
  veröffentlicht daher keine Konformitätsaussage und keine Barrierefreiheitserklärung,
  weil diese nur für in Scope befindliche Angebote verpflichtend und nur mit
  manueller Prüfung belastbar wären.

### Quellen im Repo

- `data/recht-fristen.yaml` (Frist `bfsg-barrierefreiheit-bewertung`)
- `docs/INFRASTRUKTUR.md` (Fristen-Übersicht, BFSG-Scope-Bewertung einmalig)
- `scripts/a11y_audit.py`, `scripts/h1_wache.py`
- `A11Y-EINE-H1-DAUERHEILUNG-PREMIUM-2026-10-07.md`, `A11Y-EINE-H1-DAUERHEILUNG-PREMIUM-2026-10-08.md`

### Nächste Schritte

1. Beschäftigten- und Umsatzschwellen bestätigen (Betreiber, bis 31.10.2026).
2. Bewertung bei jedem Neubewertungs-Auslöser erneut prüfen.
3. Die Bewertung im quartalsweisen Rechtslage-Screening mitführen.
4. Bei Zweifeln eine fachanwaltliche Prüfung (IT-/Medienrecht) einholen.

---

*Verantwortlich: Frank Hartung. Pflege gemäß Frist `bfsg-barrierefreiheit-bewertung`.*
