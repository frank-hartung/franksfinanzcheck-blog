# KI-VO: maschinenlesbare KI-Kennzeichnung – Cover-Pipeline, CI-Gate und Freigabe (#1028)

**Datum:** 13.11.2026 · **Frist-ID:** `ki-vo-kennzeichnung-bestand` (02.12.2026)  
**Ebene:** Technik + Gate + Vertrag + Freigabe · keine Rechtsberatung  
**Issue:** #1028 bleibt offen bis Merge, Deploy, Live-Abnahme (§4 `docs/KI-TRANSPARENZ-ABNAHME.md`) und Betreiberfreigabe (`erledigt=ki-vo-kennzeichnung-bestand`).

---

## 1. Befund (war diese Akte nötig)

Die Covers des Blogs waren ohne beweiskräftigen Herkunfts-Nachweis:
* Kein Frontmatter-Beleg, ob ein Titelbild deterministisch gerendert oder modellbasiert erzeugt ist.
* Keine Herkunft **in der Datei** selbst – Herunterladen, Weiterreichen oder Spiegeln hätten jede Angabe entfernt.
* Keine Wache, die ein nachträglich verändertes oder ausgetauschtes Cover erkennt.
* 17 von 131 Cover-Referenzen wichen vom Renderer ab (veraltete Dateinamen im Frontmatter, Doppel-Schreibvorgang des Generators), ohne dass jemand es bemerkte.

Das war die technische Kernlücke von #1028 auf der Bild-Ebene.

---

## 2. Dauerhafte Heilung (nicht einmalig)

### 2.1 Ein Schreibpfad statt zwei (`scripts/generate_covers.py`)

`make_cover` rendert das Cover und schreibt seine responsive Varianten selbst (`save_modern_variants` innerhalb der Funktion). Der bisherige zweite Durchlauf `ensure_responsive_variants` öffnete das fertige JPG mit Pillow und speicherte es erneut – bei byteidentischen Pixeln aber byteunterschiedlichem Ergebnis. Das war die Ursache für die 17/131 XMP-Verluste und die sha256-Abweichungen: Ein Attestation-Beleg war nach dem zweiten Schreiben falsch, obwohl niemand das Bild geändert hatte.

Jetzt: **ein Erzeugungspfad**. `make_cover` gibt die Variant-Liste zurück; `ensure_responsive_variants` läuft nur als Reparaturpfad, wenn nichts (re-)gerendert wurde. Ein Lauf ohne `--force` rendert nichts.

### 2.2 Herkunft in die Datei (`make_cover` → `_herkunft_markieren`)

Jedes gerenderte Cover bekommt direkt nach dem JPG-Schreiben IPTC-XMP `DigitalSourceType=algorithmicMedia` (APP1-Segment vor den Bilddaten, kein Neukodieren). Die Pixel bleiben unverändert; die Datei trägt ihre Herkunft selbst und überlebt Herunterladen, Weiterreichen, Spiegeln. Der Aufruf sitzt in allen drei Erzeugungszweigen (Artikel, Pillar, Marke) und kann nicht vergessen werden. Fehlertolerant: Eine fehlende Schrift oder ein voller Datenträger stoppt die Cover-Produktion nicht (C34).

### 2.3 Frontmatter-Beleg (`scripts/ki_cover_herkunft.py --attestieren`)

Je Cover wird `cover.ki_pruefung` ins Frontmatter geschrieben:
`digital_source_type: algorithmicMedia`, `variante: renderer-v3`, `sha256` der markierten Datei, `verfahren: "generate_covers.py (Pillow, deterministisch)"`, `geprueft_am`.

### 2.4 Stale-Referenzen selbstheilend (`ensure_cover_in_frontmatter`)

Weist auf ein altes Cover-JPG (anderes Datum im Dateinamen, z. B. Slug-Datum geändert, Cover-Datei nicht mitgezogen) um auf `images/covers/<slug>.jpg`. Geschieht bei jedem Lauf selbstheilend. Das war die Ursache der 17 Drift-Befunde.

### 2.5 Reproduktionswache (`--pruefen`) und Selbsttest (`--selftest`)

`--pruefen` rendert jedes Cover neu (ohne Schreibzugriff) und verlangt Pixelgleichheit plus Frontmatter-Beleg. `--selftest` führt 5 Sabotage-Proben (fehlender Beleg, Attestation, manipuliertes Bild, KI-Beleg-Schutz, IPTC-Lesbarkeit).

---

## 3. Messung am 13.11.2026

| Prüfung | Ergebnis |
|---|---|
| `scripts/ki_cover_herkunft.py --selftest` | 5/5 grün |
| `scripts/ki_cover_herkunft.py --attestieren` | 132 Belege geschrieben, 2 bereits belegt, 0 Fehler |
| `scripts/ki_cover_herkunft.py --markieren` | 133 Dateien markiert, 0 Fehler |
| `scripts/ki_cover_herkunft.py --pruefen` | 132/132 reproduziert, 2 außerhalb des Renderbereichs, 0 Befunde |
| `scripts/blustradius_register.py --check` | 90 Schritte, Vertrag erfüllt |

**Reihenfolge ist Pflicht:** erst `--markieren` (Datei), dann `--attestieren` (sha256 der markierten Datei), dann `--pruefen`.

### Außerhalb des Renderbereichs (2)

Die statischen Seiten `/newsletter/` und `/newsletter-checkliste/` teilen sich das Markenbild `brand-franksfinanzcheck.jpg` und haben keinen eigenen Renderer-Lauf. Sie werden gezählt, aber nicht als Drift bewertet (Filter via `im_renderbereich`).

### Rechtliche Einordnung (keine Rechtsberatung)

Ein deterministischer Pillow-Render ist `algorithmicMedia` im IPTC-Vokabular (von einem Algorithmus erzeugt, aber **nicht** mit Trainingsdaten eines generativen Modells). Die Covers sind daher **nicht** kennzeichnungspflichtig nach Art. 50 Abs. 2 KI-VO – genau deshalb ist der Beleg nötig: Ohne ihn ist „nicht deklariert" nicht von „nicht geprüft" zu unterscheiden. Mit Beleg ist es eine Aussage.

Ausdrücklich **nicht** behauptet:
* Freiheit von Rechten Dritter (Schrift, Farben, Marke)
* Nachprüfbarkeit der Herkunft ohne dieses Repo
* Gültigkeit der Aussage für spätere modelbasierte Renders (dagegen steht die Reproduktionswache)

---

## 4. CI-Gate (fail-closed)

Zwei neue Schritte in `.github/workflows/deploy.yml` (vor dem Hugo-Block):
1. `Cover-Herkunft – Selbsttest (Wache muss lauffähig sein)` — Klasse `gate-selbsttest`, schützt die Reproduktionswache.
2. `Cover-Herkunft – Reproduktionswache (fail-closed)` — Klasse `inhalt`; ein driftendes oder unbelegtes Cover stoppt den Deploy, bevor etwas gebaut wird.

Eintrag in `data/blustradius-deploy.yml` für beide Schritte (90/90 Schritte erklären ihren Blustradius, exakter Schrittname-Abgleich Workflow ↔ Register).

---

## 5. Freigabe-Liste und Betreiberfreigabe (Operator, nicht der Agent)

Die 12 unter `data/ki_kennzeichnung.yaml` als `menschlich` geführten Einträge (14.08.–03.09.2026, keine Herkunft belegt) bleiben **unangetastet**, bis der Betreiber sie einzeln abhakt:

* `python3 scripts/freigabe_liste.py --liste` — Checkliste mit Erst-Erwähnung und Tagen bis 02.12.2026 (19 Tage am 13.11.2026)
* `python3 scripts/freigabe_liste.py --abhaken <Slug>` — je Eintrag (Zustand in `data/freigabe_state.json`; `ki_kennzeichnung.yaml` wird nicht verändert)
* `python3 scripts/freigabe_liste.py --freigabe` — erzeugt die Betreibererklärung mit `erledigt=ki-vo-kennzeichnung-bestand` und Unterschriftszeilen, **nur wenn alle 12 getickt**

Die auszufüllende Vorlage liegt in `docs/FREIGABE-VORLAGE-KI-VO-KENNZEICHNUNG-BESTAND.md`. Die Freigabeerklärung wird vom Betreiber unterzeichnet und in der Fristen-Check (Recht) als `erledigt=ki-vo-kennzeichnung-bestand` ausgeführt.

---

## 6. Was danach noch offen ist

* Anbieter-Inventar + schriftliche Bestätigung zur Markierung nach Art. 50 Abs. 2 (Anfragevorlage in `docs/KI-TRANSPARENZ-ABNAHME.md` §1)
* Live-Abnahme nach `docs/KI-TRANSPARENZ-ABNAHME.md` §4 (jetzt 11 Kanäle, nur am ausgelieferten Stand)
* Betreiberfreigabe (`erledigt=ki-vo-kennzeichnung-bestand`)
* Issue #1028 bleibt offen bis Merge, Deploy, Live-Abnahme und Operator-Release
