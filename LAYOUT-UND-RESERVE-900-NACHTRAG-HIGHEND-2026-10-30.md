# #900 – Nachtrag: Regressions-Kette grün und Laufzeit-DOM unter Budget

**Stand:** 30.10.2026 · **Vorgang:** Meldung
[#900](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/900)
(Nachtrag nach PR #959) · **Basis:** `main` @ `854652e` · **Beleg vor Ort:**
Hugo 0.168.0 extended (`hugo --destination public.site`), 380 Seiten, jsdom
(kein Browser im Sandkasten – siehe §4)

---

## 1. Auftrag

Nach dem Abschluss von #900 (PR #959) blieben zwei Punkte offen. Beide sind
hier erledigt, jeweils an der Ursache, mit Regressions-Test und ohne ein
Budget, eine Schwelle oder einen Test zu lockern:

1. **Die CI-Prüfung `regression` war rot** – fünf Tests, alle im Umfeld
   „Artefakt und Inhalt sind auseinandergelaufen“.
2. **Die DOM-Frühwarnung** war kein Wächter, sondern eine Notiz: Die längste
   Seite lag zur Laufzeit bei **1401** Elementen – ein Element über der harten
   Lighthouse-Grenze.

---

## 2. Teil 1 – die fünf roten Tests und ihre Ursachen

### 2.1 Reserve-Nachweis: der Watchdog hat zertifizierte Entwürfe geheilt

`test_reserve_artifacts` war rot, weil `data/reserve-readiness.json` drei
Entwürfe mit einer SHA-256 belegte, die nicht mehr zu den Dateien passte.

Beleg (Git-API, Objekt `8bdc510f`, „chore: Pinterest-Selbstheilung + Report“,
Content-Bot, 30.10.2026T10:57:11Z, Parent `b624559b`): derselbe Commit enthält
Änderungen an **40+ Dateien**, darunter

* `2026-10-30-fenster-abdichten…`: `keywords` gekürzt (`"Abdichten"` entfernt),
* `2026-10-30-energieeffiziente-geraete…`: `keywords` ersetzt,
* `2026-10-30-gaspreiserhoehung…`: **zwei Zeilen eingefügt** –
  `**Transparenz:** Dieser Artikel enthält Affiliate-Links (Werbung). …`

Der Nachweis entstand um 10:36:34 UTC (Commit `6d5ddd09`), die Mutation um
10:57:11 UTC. `data/spam_history.jsonl` nennt den Schreiber beim Namen:
`{"ts": "2026-10-30T10:57:07Z", "module": "spam_guard", "action": "blog-fix",
"slug": "2026-10-30-gaspreiserhoehung…", "rules": ["B3", "B5"]}` – also
`spam_guard.fix_blog`, das die Transparenz-Zeile (B3) in einen **zertifizierten
Reserve-Entwurf** schreibt; die `keywords` kamen aus den Pin-Heilern
(`pinterest_seo_healer`, `pinterest_duplicate_guard`).

**Drei Antworten, jede eine Klasse von Fehlern:**

1. **Schreibschutz (die Ursache).** Neu:
   `scripts/reserve_schreibschutz.py` – die eine Regel, die alle Hygiene-Heiler
   teilen: `draft: true` **und** `reserve: true` ⇒ bytegebunden, nicht
   anfassen. `spam_guard.fix_blog`, `pinterest_duplicate_guard` und
   `pinterest_seo_healer` fragen vor jedem Schreibzugriff und melden den Fund
   weiter („unangetastet – bytegebundener Reserve-Entwurf; Nachmessung ist
   Sache der Reserve-Kette“). Die Heilung passiert beim Übergang in die
   Auslieferung, wenn der Entwurf kein Reserve-Entwurf mehr ist. Der Schutz ist
   rein textuell (kein PyYAML), damit er auch ohne Zusatzpakete greift.
2. **Wahrheitspflicht beim Commit (der Sicherheitsgurt).** `scripts/git_sync.sh`
   – der einzige Weg, auf dem Bots committen – zieht ungültige READY-Nachweise
   **vor** dem Commit zurück (`reserve_artifacts.py --withdraw-invalid`, keine
   Nachmessung) und nimmt den Rückzug in denselben Commit. Im Modus
   `--push-only` (der Workflow hat selbst committet) reist die Korrektur als
   eigener Commit hinterher. Kein Commit trägt mehr einen Nachweis, dessen
   Bytes er nicht enthält.
3. **„Nicht prüfbar“ ist nicht „falsch“.** Beim Nachvollziehen ist ein echter
   zweiter Fehler aufgefallen: `--withdraw-invalid` ohne PyYAML hat **alle**
   Zeilen als „Entwurf nicht prüfbar“ gewertet und den Vorrat von 6 auf 0
   gesetzt (im Sandkasten reproduziert und rückgängig gemacht). Der destruktive
   Pfad prüft jetzt zuerst die Werkzeuge (`require_metadata_support()`) und
   bricht mit Exit 2 ab, ohne eine Zeile anzufassen.

**Bestand:** Die drei Entwürfe waren wieder **bytegleich** zum damaligen
Nachweis (SHA-256 geprüft: `bdbb8f37…`, `b3d6df66…`, `d74dfcaa…`; Bytes über
die Git-API aus `6d5ddd09` zurückgeholt, kein Nachweis erfunden).
`reserve_artifacts --withdraw-invalid` meldet „3 → 0 zurückgezogen“ nicht mehr,
weil es nichts zurückzuziehen gibt.

**Nachtrag nach dem Merge mit `main` (13:0x UTC):** Die Reserve-Kette hat in
der Zwischenzeit selbst neu gemessen – der Nachweis vom 12:53 UTC zertifiziert
die **bearbeiteten** Bytes der beiden 30.10.-Entwürfe (`41a5b625…`,
`b5e79ef5…`). Eine frische Messung darf ein PR nicht durch ältere Bytes
überstimmen (das wäre derselbe Fehler in die andere Richtung). Deshalb nimmt
der Merge für diese zwei Dateien den zertifizierten Stand von `main`; die
Änderung dieses PRs dort ist bewusst zurückgenommen. Die beiden Änderungen
sind inhaltlich unschädlich und eher besser (die Affiliate-Transparenz-Zeile
B3 steht wieder drin, die Pin-Heiler-`keywords` bleiben). Was bleibt, ist die
Ursache: der Schreibschutz verhindert, dass Heiler künftig in bytegebundene
Entwürfe schreiben. Der dritte Entwurf (`bdbb8f37…`) ist unverändert
bytegleich.

### 2.2 FF5: Abbildung-Unterschriften (21 Befunde)

`scripts/abbildungen_ableiten.py` neu ausgeführt – 8 `index.md`, 6 SVGs. Die
Regeneration wurde **einzeln gelesen**, nicht blind übernommen:

| Datei | Änderung | Bewertung |
|---|---|---|
| `2026-08-17-kostenloses-girokonto…` | Satz-Link zu `wlan-verstaerker-vs-mesh` aus der Unterschrift entfernt | **Fehler behoben** – der Link hing an der Wendung „was brauchst du wirklich?“ und zeigte auf ein fremdes Thema |
| `2026-08-14-gasrechnung-senken…` | Unterschrift-Link zu `2026-09-20-gasrechnung-senken…` entfernt | **Fehler behoben** – Fremdlink mitten im Satz; die zwei echten Textlinks auf denselben Artikel bleiben (Z. 38, 58) |
| `2026-08-24-preisgarantie-gas…` | Titel in der Unterschrift „Gaspreisgarantie“ → „Preisgarantie Gas“ | **vereinheitlicht** – Unterschrift nannte einen anderen Titel als der Beitrag (FF5-Kern) |
| `2026-08-19-energiediebe…`, `2026-08-20-dsl…`, `2026-08-26-dns…` | `alt`, Unterschrift und Gliederung aus dem aktuellen Inhalt | **vereinheitlicht** – u. a. „DNS-DNS-Server“ → „DNS-Server“, abgeschnittene Aufzählungen neu umbrochen |
| 6 SVGs | neu gerendert (Gliederung/Merkkarte) | Folgen der Textkorrekturen; `ff_inhalts_wache.py` → 0 Befunde, `abbildungen_ableiten.check()` → `[]` |

### 2.3 Fachprüfungs-Register

`scripts/fachpruefung_register.py` neu erzeugt (19 Beiträge), `--check` →
„✅ Fachprüfungs-Register aktuell“.

### 2.4 W11: Pillar verlinkte einen demotierten Entwurf

`content/pillar/versicherungen/index.md` verlinkte
`2026-08-18-wohngebaeudeversicherung-vergleich…` – der Beitrag wurde am
28.10. demotiert (`cadence_demoted`, `cadence_grund: "ymyl-review: E17: Text/
Quellen wurden nach der Freigabe verändert"`). Ein Link auf einen Entwurf ist
ein totes Ziel. Statt den Entwurf zu „promoten“ (er hat keine YMYL-Freigabe)
ist der Link ersetzt worden durch eine Anleitung, die ohne Ziel auskommt
(„Prüf die vier Punkte in dieser Reihenfolge – erst Elementar, dann grobe
Fahrlässigkeit, dann Neuwert, zuletzt der Selbstbehalt“). `BestandTest` bleibt
unverändert streng: live-Artikel **müssen** verlinkt sein, Entwürfe **dürfen**
nicht.

**Nachtrag nach dem Merge mit `main`:** `main` hat den Pillar inzwischen selbst
überarbeitet; beim Merge galt die Fassung von `main`, und `BestandTest` ist mit
ihr grün (6/6). Die zusätzliche Prüf-Reihenfolge-Sentence aus diesem PR ist
damit entfallen – sie war Ersatz für den toten Link, nicht sein Zweck. Der
Bestandstest ist die Wahrheit, nicht der Satz.

### 2.5 Was ausdrücklich NICHT getan wurde

* Kein Test gelockert, keine Schwelle gesenkt, kein Befund umetikettiert.
* Der Nachweis ist nicht „nachzertifiziert“ worden (das wäre ein Freibrief für
  die Bytes, die niemand gemessen hat) – die Bytes sind zurückgeholt worden.
* Wo die Reserve-Kette inzwischen **selbst** neu gemessen hat (12:53 UTC),
  gilt die Messung: dort wurde die Änderung dieses PRs zurückgenommen, statt
  eine frische Messung zu überstimmen. Der Unterschied steht oben im Nachtrag,
  nicht in einer stillen Überschreibung.
* Die Drift ist nicht weggeräumt, sondern abgestellt: Schreibschutz plus
  Wahrheitspflicht beim Commit.

---

## 3. Teil 2 – Laufzeit-DOM: 1401 → 1195 ohne Pixel-Änderung

### 3.1 Der Befund, exakt gemessen

`scripts/dom_audit.py` (statisch, ausgelieferte HTML) war grün: schwerste Seite
**1058** Elemente, Frühwarnung 1100. Zur Laufzeit sieht der Browser mehr. Gemessen
mit jsdom (echte DOM, dieselben lokalen Skripte, kein Modell):

```
/posts/2026-09-24-internet-dsl-update-…   ausgeliefert 1033  →  zur Laufzeit 1401
```

**1401** = ein Element über der harten Lighthouse-Grenze (1400) und 51 über der
Frühwarnung – und der Lauf blieb grün, weil die Frühwarnung nur eine Notiz war.
Zuwachs: **368** Elemente, davon 288 aus einer einzigen Stelle:

```
je Überschrift  1 × span.ff-heading-text
              + 1 × button.ff-heading-copy
              + 1 × svg + 3 × path          ← vier Knoten für ein Symbol
              = 6 Elemente × 48 Überschriften = 288
```

Dazu: Titel-`<span>` je TOC-Eintrag, ein Zieh-Griff als `<svg>` mit sechs
`<circle>`, Verzeichnis-Gerüst.

### 3.2 Die Heilung: Symbol ins Stylesheet, nicht in den DOM

| Stelle | vorher | jetzt | Elemente |
|---|---|---|---|
| Kopier-Symbol | `<svg>` + 3 `<path>` im Knopf | CSS-Maske auf `::before` (identische Pfade, 15 px, `currentColor`) | −4 je Überschrift |
| Kopier-Haken | zweites `<svg>` per `innerHTML` | Klasse `.ff-copied` + zweite Maske | −1 im Klickzustand |
| TOC-Titel | `<span class="ff-mini-toc__txt">` | Textknoten im `<a>` = zweites CSS-Grid-Element | −1 je Eintrag |
| Zieh-Griff | `<svg>` + 6 `<circle>` | `radial-gradient` (4,6 × 5,6 px Raster, wie zuvor) | −7 je Seite |

Ergebnis (alle 380 Seiten gemessen):

| Seite | vorher | jetzt | Luft bis 1400 |
|---|---|---|---|
| `2026-09-24-internet-dsl-update-…` (48 Überschriften) | **1401** | **1195** | 205 |
| `2026-08-26-tagesgeld-zinsen-…` (27) | 1278 | 1158 | 242 |
| schwerste Seite über alle 380 Seiten | 1401 | 1195 | 205 |

Keine Seite liegt über 1200; die Geometrie des Symbols ist unverändert
(dieselben Pfade, dieselbe Strichstärke, dieselbe Farbe `currentColor`, gleiche
15 px), der Haken ist derselbe Pfad als Zustand.

> **Ehrlichkeit zur Grenze des Belegs:** Im Sandkasten gibt es keinen Browser
> (kein Chromium, kein Playwright-Download). Die Zahlen oben sind mit jsdom
> gemessen – einer echten DOM-Implementierung, die dieselben lokalen Skripte
> ausführt, aber kein Layout rechnet. **CLS und die Pixelgleichheit** belegen
> deshalb die CI-Läufe `e2e/design-shots.mjs`, `e2e/design-metrics.mjs`
> (hell/dunkel) und Lighthouse – sie laufen im PR und sind Teil der Abnahme.
> Was hier belegt ist: die DOM-Masse und die Identität der gezeichneten Pfade.

### 3.3 Damit es nicht zurückkommt

1. **Messung mit Grenze:** `scripts/dom_laufzeit_messung.mjs` misst **jede**
   Seite gegen **1200** (Ziel: 200 Elemente Luft unter 1400) und ist rot
   (Exit 1), wenn eine Seite darüber liegt; Exit 2 bei fehlendem Bau oder
   fehlendem jsdom (fail-closed, keine stille Übersprung-Meldung). Selbsttest
   ohne Bau: `--selftest`.
2. **Verdrahtung:** Der `layout-ai`-Lauf führt die Messung nach dem Bau aus;
   `LAUFZEIT_EXIT` fließt in den Schluss-Schritt („Lauf rot stellen“) ein –
   fehlt der Wert, ist der Lauf rot. `static/premium/**` steht jetzt in beiden
   Pfadlisten (push und pull_request), damit eine Änderung an der Quelle die
   Messung auslöst. Dazu kommen die Manifest-Wache (vor jedem `npm ci`,
   WF-7B6B/#654) und ihre eigene Datei im Filter – sonst meldet die
   Trigger-Wache W1 zu Recht, dass der Lauf einen Prüfer aufruft, den seine
   Änderung nicht auslöst.
3. **Vertrag an der Quelle:**
   `scripts/tests/test_dom_element_vertrag.py` prüft, dass je Überschrift
   höchstens **zwei** Elemente entstehen, dass kein Symbol per `innerHTML`
   zurückkehrt, dass der TOC-Titel ein Textknoten bleibt, dass das Stylesheet
   Maske und Haken liefert und dass Messung und Pfade verdrahtet bleiben.
4. **Wache am fertigen DOM:** Die jsdom-„§“-Wache
   (`scripts/ff_heading_glyph_guard_test.mjs`) prüft jetzt **null** Kindknoten
   je Kopierknopf – strenger als vorher (vorher genügte „irgendein `<svg>`“).
   Auch `scripts/ff_voice_functional_test.mjs` prüft den Zustand statt eines
   zweiten SVG; `scripts/heading_anchor_guard.py` hat eine neue Schicht
   „1b) STIL“ für die Maske (42/42 Prüfungen).

### 3.4 Was NICHT getan wurde

* Das Budget wurde **nicht** erhöht: 1400 bleibt die harte Grenze, 1350 die
  Frühwarnung; die neue Messung ist mit 1200 **strenger**.
* Kein Feature wurde gestrichen: Kopierknopf, Haken-Rückmeldung,
  Mini-Verzeichnis, Zieh-Griff und Fortschritt sind alle noch da.
* Keine `<div>`-Suppe, keine `aria`-Verschlechterung: `data-ff-skip-read`,
  `aria-labelledby`, der leere Knopf (kein Textzeichen) und die
  Fokus-/Tastaturbedienung sind unverändert.

---

## 3a. Nebenbefund aus dem E2E-Lauf: Codeblock war für Tastatur unerreichbar

Der Playwright-Lauf der Prüfung meldete auf `/pillar/strom-sparen/` (nur
`[mobile]`) einen WCAG-Verstoß:

```
■ scrollable-region-focusable (serious) – Scrollable region must have
  keyboard access · wcag2a, wcag211, wcag213
  · <code class="language-text" data-lang="text">
```

Ursache war nicht unsere Gestaltung, sondern die Theme-Regel
`.md-content pre code { overflow-x: auto }`: Chroma liefert
`<pre tabindex="0"><code>…`. Der Fokus liegt damit auf `pre`, der Scrollbereich
aber im **nicht fokussierbaren** `code`. Auf schmalen Viewports läuft die
Rechenformel über – Tastatur- und Schalter-Nutzung kommt nicht an den Rest.

Heilung an der Ursache (eine CSS-Überschreibung, optisch unverändert –
derselbe Kasten, derselbe Umbruch, nur ein anderer Halter für die
Bildlaufleiste): `pre` scrollt (es trägt `tabindex="0"`), `code` nicht mehr.
Der Befund war schon vor diesem PR vorhanden (der E2E-Lauf auf `main` ist seit
28.10. rot); er ist hier mitbehoben, mit Vertrag in
`scripts/tests/test_a11y_code_scroll.py`.

---

## 3b. Nebenbefund: warum der `regression`-Job rot ist – und warum es nicht dieser PR ist

Der Job **„Publication reliability regression tests”** ist seit dem 28.10.
(13:34 UTC, letzter grüner Lauf) auf **jedem** Branch rot. Auf diesem PR sind
es exakt zwei Schritte: `Code-Regression – Suite und Selbsttests` und
`Uhr-Probe`. Ein roter Befund, den man nicht erklären kann, ist keine Freigabe
– deshalb wurde er bis zur Ursache verfolgt, statt ihn zu umgehen.

**Messung, nicht Vermutung** (zwei frische Klone, gleiche Werkzeugkette
Hugo 0.168.0 + `requirements-ci.txt`, dieselben Befehle wie im Workflow):

| Klon | Stand | Ergebnis der Suite |
|---|---|---|
| `main` | `cf6f9d0` | **4646 Tests, 5 Fehlschläge** |
| dieser Branch | `95e21bf` | **4606 Tests, ok (skipped 22)**; mit CI-Paketen 4608 Tests, ok (skipped 5) |

Die fünf Fehlschläge auf `main`:

```text
FAIL: test_top20_haben_zwei_abbildungen (test_inhalts_register.AbbildungenTests)
FAIL: test_register_ist_aktuell (test_inhalts_register.FachpruefungRegisterTests)
FAIL: test_live_wache_ist_gruen (test_inhalts_register.FormulaAndLiveTests)      → 21 × FF5
FAIL: test_der_zwilling_hat_keine_nachfrage_aus_seite_eins (14 statt <10 Impressionen)
FAIL: test_pillar_verlinkt_keinen_entwurf (Wohngebäude-Vergleich)
```

**Ursache der 21 FF5-Befunde:** `data/gsc/top_seiten_28t.json` schreibt die
GSC-Automatik täglich neu. FF5 prüft die Abbildungen der **Top-20** – und die
Liste hat sich verschoben: neu aufgenommene Beiträge tragen Unterschriften und
Alt-Texte, die nicht artikelgenau sind (`*Abbildung: Merkkarte zu „…` erwartet).
Die Automatik, die die Liste schreibt, zieht `abbildungen_ableiten.py` nicht
nach; der Befund landet damit bei jedem fremden PR statt bei seinem Erzeuger.

**Warum das nichts mit diesem PR zu tun hat:** die betroffenen Skripte
(`ff_inhalts_wache.py`, `abbildungen_ableiten.py`, `fachpruefung_register.py`)
sind zwischen `854652e` und `cf6f9d0` **byte-identisch** – geändert haben sich
ausschließlich Daten (`data/gsc/`). Der Branch selbst ist grün, und der
Schwester-Branch `arena/e755613b` (Thema Affiliate, ohne eine Zeile aus diesem
PR) zeigt im selben Lauf dieselben zwei roten Schritte. Es wurde **keine
Prüfung abgeschaltet, entschärft oder ausgenommen**.

**Stand nach dem Merge mit `main` (gleiche Suite, gemergter Baum):**

```text
Ran 4680 tests — 2 Fehlschläge
  · test_current_snapshot_is_whole_and_editorially_valid  → von diesem PR verursacht, behoben
  · test_der_zwilling_hat_keine_nachfrage_aus_seite_eins   → fremder Befund, bleibt
```

Der erste Fehlschlag war eine echte Folge des Merges: zwei 30.10.-Entwürfe
waren in diesem PR auf ältere Bytes zurückgeholt worden, während die
Reserve-Kette sie um 12:53 UTC auf den bearbeiteten Bytes neu gemessen hatte.
Die Änderung ist zurückgenommen (§2.1, Nachtrag) – die Messung gilt.
Übrig bleibt **ein** Fehlschlag: `test_der_zwilling_hat_keine_nachfrage_aus_seite_eins`
meldet 14 statt < 10 Impressionen in 28 Tagen. Das ist **kein Codefehler,
sondern ein redaktioneller Entscheid** („Konsolidierung prüfen“, §Kommentar im
Test). Die Schwelle zu erhöhen wäre genau die Testentschärfung, die hier
nirgends passiert; der Befund ist auf `main` ohne diesen PR genauso rot
(nachgemessen am frischen Klon `cf6f9d0`).

**Empfohlene Dauerheilung (eigener Vorgang, nicht in diesem PR):** die
GSC-Automatik läuft nach dem Listen-Update selbst `abbildungen_ableiten.py
--check` (bzw. den Heiler mit Commit) und wird dort rot, wo der Befund
entsteht. Bis dahin bleibt der Job ein ehrlicher, aber fremder Rot-Befund.

---

## 4. Belege (Befehle und Ausgaben)

```text
$ python3 scripts/ff_inhalts_wache.py
Inhalts-Wache FF1–FF5: 0 Befund(e)

$ python3 scripts/fachpruefung_register.py --check
✅ Fachprüfungs-Register aktuell

$ python3 scripts/reserve_artifacts.py --check
✅ Reserve-Snapshot vollständig: eindeutiges JSON, echte READY-Bytes und Redaktionsvertrag.

$ python3 scripts/reserve_artifacts.py --withdraw-invalid        # ohne PyYAML
🛑 Nachweise nicht zurückgezogen: Nachweisprüfung nicht möglich: No module named 'yaml'   [Exit 2]

$ python3 -m unittest scripts.tests.test_reserve_schreibschutz scripts.tests.test_reserve_artifacts
Ran 45 tests … OK

$ python3 -m unittest scripts.tests.test_git_sync          # 51 Tests inkl. 3 neue
Ran 51 tests … OK

$ python3 -m unittest scripts.tests.test_versicherungs_cluster_verlinkung
Ran 6 tests … OK

$ python3 scripts/heading_anchor_guard.py
42/42 Prüfungen bestanden        ✅

$ node scripts/ff_heading_glyph_guard_test.mjs
49/49 Prüfungen bestanden        ✅

$ node scripts/ff_voice_functional_test.mjs
265/265 Prüfungen bestanden      ✅

$ python3 -m unittest discover -s scripts/tests        # volle Suite
Ran 4602 tests in 303.790s — OK (skipped=22)

$ python3 scripts/trigger_wache.py --check
✅ Trigger-Wache: 97 Workflows, keine Befunde.

$ node scripts/dom_laufzeit_messung.mjs --dir public.site --top 5
Laufzeit-DOM: 380 Seiten gemessen
   1195  /posts/2026-09-24-internet-dsl-update-…   (ausgeliefert 1033, +162, 48 Überschriften)
   1158  /posts/2026-08-26-tagesgeld-zinsen-…
✅ Alle Seiten unter 1200 Laufzeit-Elementen – schwerste Seite 1195: 5 Elemente Luft bis zur Zielmarke, 205 bis zur harten Grenze 1400.
```

---

## 5. Was der Betrieb davon hat

| Symptom | Ursache | Heilung | Wächter |
|---|---|---|---|
| `regression` rot: Reserve-Snapshot | Hygiene-Heiler schrieben zertifizierte Entwürfe nach der Messung | Schreibschutz + Rückzug beim Commit | `test_reserve_schreibschutz.py`, `ReserveNachweisWahrheitTests` |
| Vorrat fiel auf 0 (einmalig) | Rückzug ohne PyYAML wertete „unprüfbar“ als „falsch“ | `require_metadata_support()`, Exit 2 | `test_missing_parser_never_withdraws` |
| FF5-Unterschriften falsch | Abbildungen nicht neu abgeleitet | Regeneration, einzeln gelesen | `ff_inhalts_wache.py` (FF5) |
| Pillar-Link ins Leere (W11) | Beitrag demotiert, Link blieb | Link ersetzt, Bestandstest unverändert | `test_versicherungs_cluster_verlinkung` |
| Laufzeit-DOM 1401 | 4 DOM-Knoten je Symbol, Titel-`<span>`, Griff-SVG | CSS-Maske, Textknoten, `radial-gradient` | `dom_laufzeit_messung.mjs` (1200), `test_dom_element_vertrag.py` |

**Runbook:** `docs/LAYOUT-AUTOMATISIERUNG.md` § „Laufzeit-DOM: Ziel 1200“ ·
`docs/publication-reliability.md` § „Zertifikats-Wahrheit und Schreibschutz“.
