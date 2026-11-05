# KI-VO: maschinenlesbare KI-Kennzeichnung – Dauerheilung (#1028)

**Datum:** 05.11.2026 · **Frist-ID:** `ki-vo-kennzeichnung-bestand` (02.12.2026)
**Ebene:** Technik + Vertrag · keine Rechtsberatung

## Befund

Die sichtbare Kennzeichnung („Mit KI erstellt oder bearbeitet") war seit dem
02.08.2026 im Bestand und durch `ki_kennzeichnung_gate.py` gesichert. Der
einzige **maschinenlesbare** Anteil war `data-ff-ki-label` – ein Selektor für
eigene Tests. Für Dritte (Plattform, Detektor, Aufsicht) war die Herkunft
eines Artikels aus dem Dokument nicht auslesbar, und aus einer Bilddatei schon
gar nicht. Issue #1028 benennt genau diese Lücke; die Frist für
Bestandssysteme läuft am 02.12.2026 ab.

Rechtlich ist die Rollenteilung entscheidend: Art. 50 Abs. 2 KI-VO verpflichtet
den **Anbieter** des generativen Systems zur maschinenlesbaren Markierung
(Nachfrist bis 02.12.2026 für Systeme, die vor dem 02.08.2026 in Verkehr
gebracht wurden, Art. 113 i. d. F. der Verordnung (EU) 2026/1744). Der
Verhaltenskodex der Kommission vom 10.06.2026 konkretisiert das als
geschichteten Ansatz aus signierten Metadaten, Wasserzeichen und optional
Fingerabdrücken. Ein Betreiber kann diese Pflicht nicht selbst erfüllen – er
kann aber seine **eigene** Erklärung maschinenlesbar machen und die
Anbieter-Markierung erhalten, statt sie zu zerstören. Beides fehlte.

## Heilung

Vier Kanäle, alle aus demselben Frontmatter, kein zweiter Pflegeort:

| # | Kanal | Fundstelle |
|---|---|---|
| 1 | `<meta name="ai-generated">`, `ai-generated-scope` (text/image/audio), `<link rel="describedby">` | `layouts/_partials/ki_provenienz.html`, eingebunden in `head.html` |
| 2 | schema.org `creditText` am `Article`-Knoten (rollengetrennt Text/Bild/Ton) | `layouts/_partials/schema_article.html` |
| 3 | `data-ai-generated`, `data-digital-source-type` (IPTC-Vokabular) am `<img>` | `layouts/_partials/cover.html` |
| 4 | IPTC `DigitalSourceType` als XMP **in der Bilddatei**, ohne Neukodierung | `scripts/ki_bild_markierung.py` |

Dazu der Anker `{#ki-hinweis}` im Impressum (Ziel von `rel="describedby"`) und
ein Absatz, der die maschinenlesbaren Angaben offenlegt und ihre Grenze nennt.

**Bewusst nicht gebaut:**

- **Kein Signal bei `ai_generated: false`.** Abwesenheit ist keine Behauptung
  „rein menschlich"; das Register weist selbst ungeklärte `menschlich`-Einträge
  aus. Über-Kennzeichnen ist rechtlich unschädlich, eine erfundene
  Positivaussage nicht.
- **Kein erfundener IPTC-Wert.** Ohne belegtes `digital_source_type` wird weder
  geschrieben noch im DOM behauptet.
- **Kein HTTP-Header.** GitHub Pages setzt keine Header; eine globale
  Transform Rule wäre für die 12 Artikel ohne KI-Text eine falsche Aussage.
- **Kein C2PA-Signaturdienst.** Signieren braucht Betreiber-Schlüssel und
  gehört nicht unbeaufsichtigt in den Deploy. Vorgesehen ist der Verweis auf
  ein externes Manifest (`c2pa_manifest_url` → `dcterms:provenance`).
- **Kein still überschriebenes Fremd-XMP.** Weicht vorhandenes XMP ab,
  blockiert das Werkzeug; `--force` verlangt eine bewusste Entscheidung
  (Erhaltungsgebot des Verhaltenskodex).

## Dauerhaft gesichert

`scripts/ki_provenienz_gate.py` läuft im Deploy **nach** dem Build:

- **M1** Meta-Signal jeder gebauten Seite gegen das Frontmatter
- **M2** Vorlagenvertrag (Einbindung, `creditText`, Bildattribut, Impressum-Anker)
- **M3** IPTC-Feld in jeder deklarierten KI-Bilddatei
- **M4** Kanaltreue: kein Signal ohne sichtbaren Hinweis und umgekehrt

Beide neuen Schritte sind im Blustradius-Register (`data/blustradius-deploy.yml`)
als `inhalt` eingetragen, ihre Selbsttests als `gate-selbsttest` – ein neuer
Deploy-Schritt ohne Eintrag ist dort fail-closed rot (C38).
NPM: `ki:provenienz[:gate]`, `ki:bild[:gate|:markieren]`, erweitert in `test:ki`.

## Prüfung (lokal: Hugo 0.169.0 extended, Pillow 13.0.0)

| Prüfung | Ergebnis |
|---|---|
| `hugo --minify` (voller Bestand) | grün |
| `ki_provenienz_gate.py --gate` | 76 gebaute Seiten, **0 Funde** |
| `ki_bild_markierung.py --gate` | 0 deklarierte KI-Cover, 0 Befunde |
| `schema_seo_gate.py --gate` | 408 Seiten, 82 Money-Pages, **0 harte Funde** |
| `blustradius_register.py --check` | 80 Schritte erklärt, grün |
| KI-/Schema-/DOM-/Editorial-Tests | 23 + 136 Tests grün |
| Bildrundlauf | Pixel-SHA-256 vor/nach identisch, Segmentkette führt auf Start of Scan, idempotent |
| Gegenprobe reales Cover | +909 Bytes, Pixel unverändert, unabhängiger Leser (Pillow/defusedxml) erkennt `DigitalSourceType` |

Während der Arbeit gefundener und behobener Fehler: das JPEG-Längenfeld des
XMP-Segments war um zwei Bytes zu kurz – strikte Metadaten-Leser wären mitten
im Paket aufgesetzt. Der Selbsttest prüft die Segmentkette deshalb jetzt bis
zum Start of Scan, nicht nur die Feldwerte.

## Offen

1. Anbieter-Inventar und schriftliche Auskunft zur Art.-50-Abs.-2-Markierung
   je tatsächlich genutztem Produkt (Vorlage in `docs/KI-TRANSPARENZ-ABNAHME.md`).
2. Bildherkunft und Deepfake-Prüfung je verwendetem Bild; **0 Cover** sind
   derzeit als KI deklariert – die Bildebene ist Infrastruktur für den ersten
   belegten Fall, kein Vollzug am Bestand.
3. Register `data/ki_kennzeichnung.yaml`: ungeklärte `menschlich`-Einträge.
4. Live-Abnahme nach offiziellem Deployment (Runbook-Abschnitt 4) und
   Betreiberfreigabe. Erst danach `erledigt=ki-vo-kennzeichnung-bestand`.
5. OG-Bild, Pinterest-Pin und Feeds tragen die neuen Angaben nicht – für ein
   künftig deklariertes KI-Cover gesondert zu lösen.
