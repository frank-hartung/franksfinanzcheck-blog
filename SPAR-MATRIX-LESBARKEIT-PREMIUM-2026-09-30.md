# Spar-Matrix auf /pillar/ – Tabelle wieder lesbar, dauerhaft (30.09.2026)

**Auslöser (Frank):** „https://franksfinanzcheck.de/pillar/ – *Die
FranksFinanzcheck Spar-Matrix auf einen Blick*. Bitte die Lesbarkeit der
Tabelle dauerhaft auf Premium-Level einer Profi-Agentur beheben.“

**Betroffen:** die Ratgeber-Zentrale `/pillar/` – die sechszeilige
Spar-Matrix mit den umsatznächsten Knöpfen der Seite.

| | |
|---|---|
| **Befund** | Die Tabelle war **vollständig ungestylt**: 0 Deklarationen erreichten ihre Zellen |
| **Ursache** | Premium-Tabellen-System komplett auf `.post-content` gescopt + tote Selektor-Leiche `.ff-spar-matrix` in custom.css |
| **Reparatur** | Basis-Schicht ohne Scope-Fessel (zzz-agency-polish.css §11), Markup-Vertrag im Layout, mobile Kartenansicht < 760 px |
| **Dauerhaft** | `scripts/tabellen_lesbarkeit_guard.py` (L1–L5, 9 Proben inkl. Aktionsziel-Sabotage) + 7 Unit-Tests + 6 Browser-Tests + 2 Workflows |
| **Beweis** | Wache auf dem alten Stand: **13 Funde** · auf dem neuen Stand: **0** |

---

## 1 · Befund – was live wirklich passierte

Die Matrix wird nicht aus Markdown gerendert, sondern vom Layout
(`layouts/pillar/list.html`). Sie steht damit **außerhalb von
`.post-content`** – und genau dorthin ist das Premium-Tabellen-System
(`assets/css/extended/z-premium-blog.css`, Abschnitt „TABELLEN-SYSTEM“)
vollständig gescopt: *jede* seiner rund 20 Regeln beginnt mit
`.post-content`. Die einzige Regel, die die Matrix je meinte, stand in
`custom.css` als `.ff-spar-matrix table` – ein Klassenname, den das
Markup seit dem Agentur-Layout nicht mehr trägt
(`ff-spar-matrix-section` / `ff-spar-matrix-table`).

Übrig blieb also der PaperMod-Reset:

```css
table { display: block; width: 100%; border-collapse: collapse;
        overflow-x: auto; word-break: keep-all; }
```

Kein Zellpolster, kein Kopfkontrast, keine Zeilentrenner, kein
Scroll-Container – fünf Spalten („Themenbereich · Sparpotenzial ·
Aufwand · Wichtigster Hebel · Aktion“) klebten als Textband zusammen,
auf dem Handy zusätzlich quer aus dem Fenster.

**Maschinell nachgewiesen** (Kaskaden-Probe über alle ausgelieferten
Stylesheets, Selektor-Matching + Spezifitätsrechnung gegen den echten
DOM-Pfad der Matrix):

| Eigenschaft der Datenzelle | vorher (Produktionsstand) | nachher |
|---|---|---|
| `padding` | *keine Regel* | `12px 14px` (mobil `10px 14px`) |
| `border-bottom` | *keine Regel* | `1px solid var(--border)` |
| `background` | *keine Regel* | `var(--entry)` + Zebra |
| `vertical-align` | *keine Regel* | `top` |
| `color` (Geldspalte) | *keine Regel* | `var(--ff-emerald)`, 700 |
| Kopfzeile | Browser-Default | Smaragd/Weiß, sticky, 2px-Unterkante |

Das ist dieselbe Ursachenklasse wie der `.ff-pc-*`-Befund vom
28.09.2026: **Markup korrekt gebaut, CSS nie geliefert.** Nur traf es
diesmal nicht eine neue Komponente, sondern eine alte, deren
Klassennamen umbenannt wurden, ohne die CSS mitzunehmen.

## 2 · Reparatur

### 2.1 CSS – `assets/css/extended/zzz-agency-polish.css` §11 (neu)

* **Basis-Schicht ohne `.post-content`-Fessel:** `.ff-table-scroll` und
  `.ff-tbl` funktionieren jetzt überall – Layouts, Partials, künftige
  Komponenten. Werte 1:1 aus dem bestehenden System (Polster 12/14 px,
  Sticky-Kopf Smaragd auf Weiß, Zebra 4,5 %, Hover, `tabular-nums`,
  `hyphens: manual`, Radius-md, Ebene-3-Schatten). Innerhalb von
  `.post-content` gewinnen weiterhin die dortigen, spezifischeren
  Regeln – **kein Artikel ändert sein Aussehen** (Spezifitätsrechnung
  geprüft: 0,3,1 schlägt 0,2,1).
* **Tastatur/A11y:** Der Scroll-Container ist fokussierbar
  (`tabindex="0"`, `role="region"`, `aria-label`) und trägt jetzt einen
  sichtbaren 3px-Fokusring in Signalgelb – vorher konnte man ihn
  fokussieren, ohne es zu sehen.
* **Spar-Matrix-Politur:** `<colgroup>`-Spaltenmaß (22/18/14/30/16 %,
  je mit `min-width`), Caption über der Tabelle, Themenspalte sticky
  und halbfett, Geldspalte smaragdgrün mit tabellarischen Ziffern,
  Aktionsspalte rechtsbündig, CTA-Knopf mit echtem 44-px-Tap-Ziel
  auf allen Viewports statt der alten 4-px-Zeile, weicher Scroll-Hinweis
  an beiden Kanten.
* **Mobile Kartenansicht (< 760 px):** Jede Zeile wird zur Karte –
  Themenname als Kartenkopf auf Smaragd-Soft, darunter je Angabe eine
  Zeile „Feldname → Wert“ (Feldname aus `data-label`), Knopf über die
  volle Kartenbreite mit 44-px-Tap-Ziel. **Kein zweites Markup** (die
  Shortcode-Lösung dupliziert dafür die Tabelle als Karten) – hier wäre
  das fatal, weil die Werbe-Offenlegung jeden Affiliate-Knopf zählt:
  eine Kopie hieße doppelte Zählung und O3-Drift.
* **Dark Mode, Print, Reduced Motion:** jede Fläche mit
  `:root[data-theme="dark"]`-Variante (Kopf in Smaragd-Dunkel, Zebra
  über Smaragd-Bright 7 %), Druckfassung ohne Schatten/Sticky, keine
  neuen Animationen.

### 2.2 Markup – `layouts/pillar/list.html`

`<caption>`, `<colgroup>`, `scope="col"` in der Kopfzeile, Zeilenkopf
als `<th scope="row">` (Screenreader behalten den Themenbezug),
`data-label` an jeder Datenzelle, `ff-tbl-corner` / `ff-tbl-num` /
`ff-tbl-a-right` als Haken des Tabellen-Systems, Scroll-Container mit
`tabindex="0"`. Der Affiliate-CTA läuft unverändert durch
`ff_affiliate_cta.html` – gleiche Ziele, gleiche SubIDs, gleiches
`placement="spar-matrix"`, gleiche Anzahl.

### 2.3 Aufgeräumt

* `custom.css`: die drei toten `.ff-spar-matrix`-Regeln entfernt
  (mit Begründung und Verweis auf §11 an Ort und Stelle).
* `z-premium-blog.css`: der Fallback-Ausschluss `:not(.ff-spar-matrix)`
  zeigte auf denselben Geist – jetzt `:not(.ff-spar-matrix-table)`.

## 3 · Damit es nicht wiederkommt

**`scripts/tabellen_lesbarkeit_guard.py`** – fünf Regeln, statisch, ohne
Build und ohne Browser (Laufzeit < 1 s):

| Regel | Prüft |
|---|---|
| **L1** Klassenabdeckung | Jede Tabellen-Klasse aus dem Template hat mindestens einen Selektor in der ausgelieferten CSS |
| **L2** Scope-Falle | Für Tabellen außerhalb von `.post-content` existiert mindestens ein deckender Selektor **ohne** `.post-content`/`.md-content`-Präfix |
| **L3** Lesbarkeits-Floor | Zellpolster ≥ 10 px, Kopfzeile mit eigener Fläche, Zeilentrenner, Aktionsziel ≥ 44 px, Mobilpfad (`@media max-width`) |
| **L4** Tote Selektoren | Kein `.ff-*`-Tabellenselektor, dessen Klasse in keinem Markup vorkommt (genau die `.ff-spar-matrix`-Leiche) |
| **L5** Markup-Vertrag | Spaltenzahl = `<colgroup>` = `scope="col"`, Zeilenkopf als `th scope="row"`, `data-label` je Datenzelle, Scroll-Container mit role/aria-label/tabindex |

Sabotage-Schutz: **9 Miniatur-Repos** im Temp (eine gesunde Referenz,
acht gezielte Defekte – darunter ein auf 32 px geschrumpftes Aktionsziel);
schlägt eine Probe nicht an, endet die Wache mit Exit 2, bevor sie
irgendetwas bewertet.

**Verankert:**

* `.github/workflows/e2e.yml` – Schritt vor Build und Browser (PRs auf
  `layouts/**`, `assets/**`).
* `.github/workflows/blog-health-daily.yml` – täglich als Wache gegen
  stillen Verfall.
* `npm run tabellen` · `npm run test:tabellen`.
* `scripts/tests/test_tabellen_lesbarkeit_guard.py` – 7 Unit-Tests
  (Selbsttest, Bestand, nachgestellter Originalschaden, Markup-Vertrag,
  „Affiliate-Knöpfe bleiben einmalig“).
* Browser-Wahrheit: `e2e/spar-matrix.spec.mjs` (5 Desktop-Tests:
  `display:table`, Polster, Kopf-Kontrast ≥ 4,5:1 gerechnet, Sticky,
  Tap-Ziele, kein Seitenüberlauf) und ein neuer Fall in
  `e2e/mobile.spec.mjs` (Karten statt Quer-Scroll, Feldnamen sichtbar,
  Knopfbreite, 44-px-Tap-Ziel).
* Dokumentiert in `DESIGN.md` §5 (zwei neue Komponentenzeilen) und
  `docs/QUALITAETS-REGELWERK.md` (R7 präzisiert, **R9 neu**).

## 4 · Verifikation

* **Wache gegen den alten Stand** (Git-Worktree auf `HEAD`):
  **13 Funde** – L1 (2 Klassen ohne CSS), L2 (`.ff-table-scroll`,
  `.ff-tbl` nur unter `.post-content`), L3 (Polster 0 px, kein Trenner,
  keine Kopf-Fläche, kein Mobilpfad), L5 (0 `<col>`, 0 `scope`,
  kein Zeilenkopf, kein Scroll-Container), L4 (`.ff-spar-matrix` tot in
  zwei Dateien). Gegen den neuen Stand: **0 Funde**.
* **Kaskaden-Probe ohne Browser** (Spezifitätsrechnung über alle
  Stylesheets, Tabelle in Abschnitt 1): vorher keine einzige greifende
  Deklaration, nachher vollständige Versorgung bei 1280 px **und**
  390 px; die mobile Schicht gewinnt nachweislich gegen die
  Basis-Schicht (deshalb `.ff-spar-matrix-scroll .ff-tbl.ff-spar-matrix-table …`).
* `python3 scripts/tabellen_lesbarkeit_guard.py --selftest` → 9/9 Proben grün.
* `python3 -m unittest scripts.tests.test_tabellen_lesbarkeit_guard` →
  7/7 grün.
* `python3 scripts/report_hygiene.py --check` → Root sortenrein.
* Klammerbilanz aller drei geänderten Stylesheets: 0.
* Hugo-Build und Playwright laufen in der CI dieses PRs – die Sandbox
  hat weder Hugo-Binary (GitHub-Release-Download blockiert) noch
  Browser; deshalb der statische Doppelbeweis oben.

## 5 · Was bewusst NICHT geändert wurde

* **Keine neue Gestaltung.** Ausgeliefert wird exakt die in DESIGN.md
  beschriebene Tabellen-Optik des Hauses – dieselbe, die Artikeltabellen
  seit dem 30.08.2026 tragen. Damit ist das keine Layout-Variante im
  Sinne der Design-Governance (CLAUDE.md), sondern eine
  Lieferungs-Reparatur (Präzedenz: `.ff-pc-*`, 28.09.2026).
* **Keine Änderung an Zahlen, Zielen oder CTA-Texten** der Matrix –
  der Affiliate-Intent-Vertrag bleibt unberührt.
* **Keine zweite Markup-Kopie für Mobil** – siehe 2.1 (Offenlegung).

## 6 · Gesiegelte Dateien

`assets/css/extended/custom.css` und `layouts/pillar/list.html` stehen
unter Siegel (Klasse FEST). Beide wurden nach dem Commit bewusst neu
signiert (`python3 scripts/integrity_guard.py --set-current`); die Akte
führt Commit, Grund und Herkunft.
