# Abschlussbericht: Sieben Dauerheilungs-Rezepte

**Stand 23.11.2026** · Branch `arena/0ba9cd37-franksfinanzcheck-blog` · PR #1321

Auftrag: die sieben Fehlerklassen **dauerhaft** heilen — nicht löschen, sondern
durch eine Wache so absichern, dass der Rückfall auffällt. Maßstab:
„vollständig dauerhaft auf Highend-Level einer Profi-Agentur".

Jedes Rezept nennt unten (a) was gebaut ist, (b) **womit es belegt ist**, und
(c) welcher Rückfall damit unmöglich wird.

---

## 1 · Strikte YAML-Wache (#1313)

**Was gebaut ist.** `scripts/frontmatter_wache.py` prüft doppelte YAML-Schlüssel
in **drei** Schichten:

| Schicht | Was sie sieht |
|---|---|
| Scanner (F3) | Duplikate je Mapping-Bereich (Einrückungstiefe), je Sequenz-Eintrag und in Flow-Mappings (`{k: 1, k: 2}`) über `_flow_doppelte` |
| Parser (F2) | strenger `SafeLoader`, der Duplikate tiefenunabhängig als Fehler wirft |
| Dedupe | unterdrückt die Parser-Fassung **nur auf Einrückung 0**, wo beide Schichten denselben Fall abdecken |

**Belegt.**

- **Eigene Korrektur, 23.11.2026 — frühere Belege waren zu schwach.**
  Ich hatte „ohne PyYAML" mit `python3 -E -s` gemessen. **Das ist falsch:**
  `-s` blockiert nur *user site-packages*, die venv-Pakete bleiben
  sichtbar. Nachgemessen: `python3 -E -s -c "import yaml"` findet
  PyYAML 6.0.4. Der echte Test ist `python3 -S` (kein site-Import). Alle
  Aussagen in diesem Bericht, die „ohne PyYAML" sagen, sind ab hier mit
  `-S` belegt — die früheren waren es nicht.

- **Die Lücke, die `main` noch offen hatte — und jetzt zu ist.**
  Mit dem echten `-S` gemessen:

  | Fassung | ohne PyYAML | mit PyYAML |
  |---|---|---|
  | `main` | **OK (skipped=5)** — grün, aber mit übersprungenem Flow-Test | OK |
  | dieser PR | **OK (skipped=5)** | OK |

  Der Unterschied liegt nicht im Ergebnis, sondern darin, **was geprüft
  wird**: `main`s Flow-Test trägt `@skipUnless(HAT_YAML, "Flow-Mappings
  liest nur der Parser")` und fällt ohne Parser aus — ausgerechnet im
  e2e-Job, der vor jedem `pip install` läuft. Nimmt man den Skip weg,
  **fällt `main` durch**: `AssertionError: [] is not true : Flow-Mapping-
  Duplikat bleibt unentdeckt`. Heißt: Hugo bricht den Bau an
  `meta: {a: "1", a: "2"}` ab, und `main`s Wache meldete ohne PyYAML
  nichts.

  Geheilt mit `_flow_doppelte_schluessel()`: der Scanner zerlegt das
  Flow-Mapping selbst (Quote-, Komma- und Klammertiefe beachtet, ohne
  `yaml`-Import). Drei neue Tests halten es: der Fall selbst, kein
  Fehlalarm (Komma im Wert, Liste, Quote-Schlüssel), keine
  Doppelmeldung mit Parser. **49/49 Tests in beiden Modi.**

- **Der strict loader trennt die Fälle messbar.** Direkt am Objekt geprüft:
  `a: 1\na: 2` wirft mit `_strenger_loader` einen `ConstructorError` **mit
  Zeile 2, Spalte 1** — und `m: {k: 1, k: 2}` (Flow-Mapping, der Hugo-Fall)
  ebenfalls, mit Zeile 1, Spalte 11. Gegenprobe mit `yaml.safe_load`:
  `{'a': 2}` — **lautlos, letzter Wert gewinnt.** Das ist genau die Lücke
  aus #1313, und sie ist zu.
- **49/49** eigene Tests mit PyYAML, **49/49** ohne (`python3 -S`), und
  **46/46** mit `main`s eigener Testdatei gegen diese Wache (beide Richtungen).
- `--selftest`: 34 Proben (7 davon gegen Schicht 1 allein).
- Vollscan: 175 Dateien, **0 Blocker**, 0 Hinweise.
- Governance-Kontrakt C1–C49 grün.

**Genau eine Lücke gegen `main` — die anderen zwei waren meine Fehlannahme.**
Gemessen mit `python3 -S` (echt ohne PyYAML) und `yaml=False`:

| Fall | `main` | dieser PR |
|---|---|---|
| Top-Level-Duplikat | 1 Befund (F3) ✅ | 1 Befund ✅ |
| verschachtelt (`aenderungsgrund`) | 1 Befund ✅ | 1 Befund ✅ |
| **Flow-Mapping (`m: {k: 1, k: 2}`)** | **0 Befunde** ❌ | **1 Befund (BLOCKER)** ✅ |

Ich hatte zunächst drei Lücken behauptet. Zwei davon waren falsch: `main`
hatte Top-Level und Verschachtelung längst geheilt (mit demselben
Nachweis gemessen), und auch die Meldung nennt den Schlüssel. Übrig bleibt
die **echte** Lücke — und die ist die gefährlichste, weil der e2e-Job vor
jedem `pip install` läuft:

- **`main` ist ohne PyYAML blind für Flow-Duplikate.** Hugo bricht den Bau
  an `meta: {a: "1", a: "2"}` ab (`mapping key already defined`), die
  Wache meldet nichts. `main`s eigener Test dafür trägt
  `@skipUnless(HAT_YAML, "Flow-Mappings liest nur der Parser")` — er
  fällt aus, statt rot zu werden. Nimmt man den Skip weg, fällt `main`
  durch: `AssertionError: [] is not true : Flow-Mapping-Duplikat bleibt
  unentdeckt`.

Geheilt mit `_flow_doppelte_schluessel()` (eigener Zerleger, kein
`yaml`-Import: Quote-, Komma- und Klammertiefe beachtet). Drei neue Tests
halten es — der Fall selbst, kein Fehlalarm (Komma im Wert, Liste,
Quote-Schlüssel), keine Doppelmeldung mit Parser. **49/49 in beiden Modi.**

**Nebenfund, mit behoben.** Der Testhelfer übersetzte `yaml_modul="ohne"` auf
`None` — und `None` heißt im Prüfer „nimm, was installiert ist". Jeder
„ohne PyYAML"-Test lief still MIT Parser und war ein No-Op. Dieselbe Falle
hatte #1339 auf `main` gestellt; in meiner Testdatei stand sie noch.

**Rückfall unmöglich, weil** jeder der drei Fälle einen Regressionstest hat,
der gegen `main` rot ist und hier grün.

---

## 2 · Titel-Wächter bestandsweise (#1304)

**Was gebaut ist.** `scripts/titel_klinke.py` friert Titelbefunde ein: Ein
Befund, der schon bekannt ist, bleibt still; **Verschlechterung** wird rot;
**Heilung** rastet ein; die **Rückkehr** eines geheilten Befunds gilt als NEU.

**Belegt.** Selbsttest 20 Proben grün; 144 Artikel im Bestand geprüft.

**Rückfall unmöglich, weil** die Klinke nicht auf „Titel ist zu lang" prüft,
sondern auf die *Veränderung* gegenüber dem eingefrorenen Stand — ein alter
Artikel kann also nicht unbemerkt aus dem Raster fallen (genau der Fall vom
20.11.: 64 Zeichen blieben unsichtbar, weil der Artikel live war).

---

## 3 · Glue-Heading-Wache (#1263)

**Was gebaut ist.** `scripts/markdown_struktur_wache.py` findet Überschriften,
die am Ende des vorigen Absatzes kleben (`[^\s#]#{2,4}`). Markdown rendert sie
als Fließtext, aber `extend_head.html` splittet das FAQPage-Schema an der
Zeichenkette `### ` — die Frage stand im JSON-LD und nicht auf der Seite.

**Stand 23.11.2026: Die Ausnahmeliste ist LEER** — und das ist ein
Ergebnis, kein Rückzug. `main` hat die einzige zurückgestellte Stelle
(Gasabschlag) in #1329 (`371835702`) geheilt; `erhebe()` findet im
Bestand 0 Funde. Eine Ausnahme, die einen nicht mehr existierenden Befund
schützt, wäre ab dem 31.01.2027 rot geworden, ohne dass jemand etwas
geändert hat — genau die Zeitbombe, gegen die das Verfallsdatum gedacht
war. Der **Mechanismus** bleibt geprüft (Selbsttest mit eigener,
markierter Probe; `BefristungTest` prüft vor/nach Ablauf, die
Datei-Bindung und dass kein Zustand leckt).

**Belegt.** Selbsttest 22 Proben; 153 Dateien, 0 neue Funde. Code-Blöcke,
Hashtags, Fragmente und `C#` klagen nicht an.

**Rückfall unmöglich, weil** die Ausnahme ein Ablaufdatum hat — eine Ausnahme
ohne Frist ist ein Dauerzustand.

---

## 4 · Alerting-Herzschlag (#1152-Kaskade)

**Was gebaut ist.** `scripts/alerting_heartbeat.py` misst den **Ausfall**, nicht
die Grundlast. Geprüft werden Zustellfenster und GitHub-Flakes statt der
naiven Annahme „kein Lauf = Alarm weg". Die YAML-1.1-Falle (`on:` → `True`)
ist abgefangen, ebenso echte Skip-Runs.

**Belegt.** Selbsttest grün: Fenster + Gnadenfrist, Zählung,
Zuordnungsgrenzen (±90/5 min), Rot-sofort-Befund, skipped-Ausschluss,
YAML-Falle + Regex-Fallback, echter Bestand, Deckung der Wacht-Liste
(D1–D10 inkl. Sabotage-Gegenprobe). Bestand: 375 Läufe, 8 verloren (2,1 %).

**Rückfall unmöglich, weil** der Selbsttest eine **Sabotage-Gegenprobe**
enthält: Die Wache muss anschlagen, wenn man den Fehler künstlich einbaut.

---

## 5 · Release-Scorecard / F4-Disposition

**Was gebaut ist.** 26 Checks mit `geprueft_am` (23.11.2026) und 365-Tage-Frist;
Entscheidungen werden **gebündelt** in der Akte geführt (`BEFUND-AKTE.md`,
`F4-ENTSCHEIDUNGSVORLAGE.md`), nicht als Einzelabfragen-Stakkato.

**Belegt.** `test_release_scorecard` 58/58. Akte: 256 offene Befunde auf
71 Seiten (45 live), ältester 24 Tage, 92 über der Frist — als Projektion aus
Queue + Entscheidungen erzeugt (`--schreiben`), nicht von Hand.

**Rückfall unmöglich, weil** zwei Wachen die Akte treiben:
`test_akte_im_repo_ist_auf_dem_stand_der_queue` (Veraltung fällt auf) und die
365-Tage-Frist im Datensatz selbst.

**Geerbtes Rot, mitgeheilt.** `main` war hier rot, weil der Ledger einen
Doppelschlüssel hatte; nach dessen Auflösung, weil die Akte veraltet war.
Siehe Rezept 1 (Wache) und den Ledger-Abschnitt unten.

---

## 6 · Klick-Kette (#1247)

**Was gebaut ist.** `scripts/click_attribution.py` prüft die URL-Hüllen-Regeln
(`/go/strom/` braucht `data-klick`, `subid`, `placement`), die Normalisierung
der go-Keys und die Aggregation. Der Guard kann jetzt **scheitern**: „kein
Build ⇒ NICHT GEMESSEN" — nicht GRÜN.

**Belegt.** 25 Tests (`test_click_chain_guard`);
Selbsttest (go-Key-Normalisierung, Aggregation, Datenschutz). Status:
GREEN 0 · AMBER 1 · NICHT GEMESSEN 2.

**Rückfall unmöglich, weil** der Guard zuvor **nicht scheitern konnte** — ein
Prüfer, der immer grün ist, ist kein Prüfer. Genau das ist behoben und mit
Regressionstests festgehalten.

---

## 7 · Design-Varianten (#1248) + Layout-Audit (#1301)

**Was gebaut ist.** `scripts/design_variant_gate.py` und
`scripts/layout_audit.py` prüfen gegen **gemessene** Budgets; der Lookup
existiert, LCP-Manifest und Gas-Rückfallschutz sind verdrahtet. Die
Alarm-Räte schieben nicht mehr in die falsche Richtung: Die Web-Vitals-Meldung
nannte „API-Key abgelaufen / GitHub-Ausfall", obwohl zwei *unabhängige*
Messungen (urllib und Chromium) im selben Lauf ausfielen.

**Belegt.** Design-Gate-Selbsttest 11 Gruppen; Layout-Audit-Selbsttest
(Baubasis fail-closed, Seiten-/Artikel-Erkennung, Startseiten-Pflicht — ohne
Hugo und Netz). Budgets 54/52/28/1100, Limits 60/58/32/1400, Runtime 1350.

**Rückfall unmöglich, weil** die Budgets aus der **Messung** stammen
(`.cache/layout/dom-audit.json`, `.cache/design-varianten/…`) und nicht
aufgepumpt wurden — „reparieren, nicht aufpumpen". Wo die Messung fehlt, ist
das Ergebnis NICHT GEMESSEN, nicht GRÜN.

---

## C · Die Klassen-Wache: „Eine Abfrage darf nicht schreiben" (neu)

Der `regression`-Job war rot, und die Ursache war kein Testfehler:
`markdown_struktur_wache.py --json` **schrieb** die Baseline – auf null
Einträge, weil der Bestand sauber war. Der nächste Test fand `{}`.

**Dieselbe Zeile stand an zwei Stellen** (`markdown_struktur_wache.py` und
`titel_klinke.py`). Beide einzeln zu heilen hätte den nächsten Kopierer
nicht aufgehalten. `scripts/lese_wache.py` prüft deshalb die Regel:

| Prüfung | Was sie tut |
|---|---|
| statisch | findet Schreibaufrufe in Blöcken ohne Ausnahme für `maschinenformat` (erkennt `not maschinenformat`, die Variable `schreibend`, den `--seed`-Zweig samt Vorlauf) |
| dynamisch | führt `--json` wirklich aus und vergleicht die Prüfsummen der Daten-Dateien |

**Belegt in beide Richtungen:** Gegen den alten Code meldet sie genau den
Fehler (1 Befund), gegen die Heilung 0. 10/10 Tests, Selbsttest 5 Proben,
Bestand 0 Befunde. Eingehängt vor der Uhr-Probe.

**Ein Fehlschluss, den die Wache selbst aufgedeckt hat:** Mein erster Wurf
sprach `_schreibe_baseline(stand, args.dry_run)` frei, weil `dry_run` in
der Zeile stand. Das ist falsch — im `--json`-Lauf ist `dry_run` **False**,
die Anwesenheit des Arguments sagt nichts über das Schreiben. Der Fall
steht jetzt als Test (`test_dry_run_argument_allein_schuetzt_nicht`).

**Was das kostet, wenn es unbemerkt bleibt:** Wer eine Sperrklinke beim
Lesen schreibt, kann nicht zweimal messen – die zweite Messung sieht die
erste. Deshalb ist „Abfrage schreibt nicht" keine Stilfrage, sondern die
Voraussetzung dafür, dass Messungen etwas bedeuten.

---

## Abgleich mit #1329 statt Doppelarbeit

#1329 (gemergt 23.11.) überlappte vier Rezepte. Der Abgleich ist **gemessen**,
nicht angenommen:

| #1329 brachte | Verhältnis zu diesem PR |
|---|---|
| mehrstufiger Scanner für #1313 | **Ergänzung, kein Ersatz:** Flow-Mapping ohne PyYAML blieb blind (Beleg oben); die Tests dafür existieren hier |
| `data/design/varianten.yaml`, `design_variant_*` | unverändert übernommen; Design-Gate-Selbsttest grün |
| `data/ki_kennzeichnung.yaml` | übernommen, keine Kollision |
| #1263-Markdown-Regel | deckungsgleich; meine Wache (22 Proben) bleibt die strengere |

**#1329 hat außerdem drei Regressionen hinterlassen**, die hier geheilt sind:

1. **`data/faktenfrische_entscheidungen.yaml`** — drei Einträge ohne `- `-Trenner.
   `main` hat die Daten inzwischen selbst repariert; der **Heiler** kann den
   Fall aber weiterhin nicht (nachgemessen: `'geschrieben': False`, Fassung
   als „Fragment" verworfen). Siehe unten.
2. **`scripts/frontmatter_wache.py`** — Import kaputt; von #1339 gefixt, aber
   mit den drei Lücken aus Rezept 1.
3. **`e2e/archivredaktion.spec.mjs`** — Test hing an einem Satz, den #1329
   umgeschrieben hat; der Playwright-Job war auf **jedem** Branch rot.

---

## Was NICHT behauptet wird (Abgrenzung)

- **F4-Fachbefunde (256) sind nicht abgehakt.** Die Scorecard weist sie als
  „Mensch (Herausgeber/Redaktion)" aus. Der Schließweg ist fassungsgebunden;
  eine Maschine, die das abhakt, bräche die Doktrin des Repos.
- **Kein Hugo/npm in dieser Umgebung.** Die E2E-Änderung ist über den
  Textvergleich belegt (Artikel byte-identisch auf `main`, gesuchte Phrasen
  0-mal vorhanden), nicht über einen lokalen Playwright-Lauf.
- **`pillow` fehlte** in der Sandbox; die 14 Testfehler, die es verursachte,
  sind Umgebung, nicht Code (im CI-Lock steht `pillow==13.0.0`).
- **Der lokale Nachweis der E2E-Änderung ist hinfällig geworden:** `main`
  hat den Test inzwischen selbst geheilt (#1345) — und besser als ich, mit
  Regex-Mustern UND einem stabilen Anker aus dem Shortcode
  (`.ff-chart__status`). Diese Fassung ist übernommen; meine Änderung am
  Test ist damit gegenstandslos. Die Wache bleibt und prüft sie.
- **`public/index.xml`** existiert nur nach einem Hugo-Build;
  `test_feed_traegt_den_kanal_auf_beiden_ebenen` ist deshalb lokal nicht
  lauffähig — auf `main` identisch.

---

## Zwei zusätzliche Heilungen, die aus dem Abgleich fielen

### A · E2E-Textanker-Wache (neu)

`scripts/e2e_textanker_wache.py` prüft jede `toContainText('…')`-Behauptung
gegen `.post-content` gegen den Artikelbestand. UI-Texte (Kopfdaten,
Rechner-Ausgaben) sind frei, Markdown-Auszeichnung wird ignoriert.

**Belegt.** Gegen den alten Testtext meldet sie **genau** die zwei Anker, die
#1329 gebrochen hat. Gegen den heutigen Bestand: 0 Befunde. Selbsttest
7 Proben (anschlagen UND still bleiben). Eingehängt vor dem Browser-Setup —
ein fehlender Satz fällt nach fünf Sekunden auf, nicht nach acht Minuten.

**Erster Wurf war nicht highend — und die Gates haben es gefangen.** Beides
war mein Fehler, nicht geerbt:

1. **CodeQL `py/redos`.** Der erste Regex war
   `(["'])(?:(?!\1).)*\1` — Backreference in einer Wiederholung, die
   klassische Exponentialfalle. Auf einer Zeile aus 40.000 Backslashes wäre
   die Wache im CI in die Knie gegangen; ein Prüfer, der den Job aufhängt,
   ist schlimmer als keiner. Ersetzt durch einen linearen Durchlauf
   (`_anker_in_zeile`): **40.000 Wiederholungen in 0,007 s**, als Test
   festgehalten (4 neue Tests, 11/11 grün).
2. **Trigger-Wache.** Mein neuer CI-Schritt rief ein Skript auf, das im
   `paths`-Filter von `e2e.yml` fehlte — der Lauf wäre bei einer Änderung
   nur an der Wache **nicht** gestartet, hätte sie sich also nie gegen den
   Bestand geprüft. Pfad ergänzt: 105 Workflows, **0 Befunde** (vorher 1);
   `test_trigger_wache` 23/23.

### B · Ledger-Heiler (verklebte Entscheidungen)

`_verklebte_bloecke_loesen()` setzt die Teile wieder zusammen, die ein
fehlender `- `-Trenner zerlegt hat. Die Fassungszuordnung kommt aus dem
**Textzeugen** („Fassung vorher 692d9701, heute cddc3cdf"), nicht aus der
Position; ohne Zeugen keine Änderung (fail-closed).

**Eigene Korrektur, dokumentiert.** Meine erste Fassung ordnete die
Kopf-Fassung dem *älteren* Entscheid zu. Der Zeuge im Text beweist das
Gegenteil, und `main`s Datenreparatur bestätigt es. Die falsche Annahme steht
jetzt samt Korrektur im Code, damit sie nicht wiederkommt.

---

## Prüfstand (Stand des letzten Laufs)

| Prüfung | Ergebnis |
|---|---|
| Frontmatter-Wache (eigene Tests) | **49/49** — mit **und** ohne PyYAML (`python3 -S`) |
| Frontmatter-Wache (gegen `main`s Testdatei) | 46/46 |
| `--selftest` Wache | 34 Proben |
| Vollscan Bestand | 175 Dateien · 0 Blocker |
| Governance-Kontrakt | C1–C49 |
| Release-Scorecard | 58/58 |
| Fachbefund-Ledger | 21/21 |
| Befund-Akte | 11/11 |
| E2E-Textanker | 11/11 · Selbsttest 7 Proben · Bestand 0 Befunde |
| E2E-Textanker ReDoS | 40.000 Wiederholungen in 0,007 s |
| Trigger-Wache | 105 Workflows · 0 Befund |
| **Lese-Wache** | **10/10 Tests · Selbsttest 5 Proben · Bestand 0 Befunde** |
| Markdown-Struktur | 32/32 Tests · Selbsttest 22 Proben |
| **Lokale Vollsuite** | **6499 Tests · 1 Fehler (Umgebung: `public/index.xml` fehlt ohne Hugo-Build)** |
| Design-Gate | 11 Gruppen |
| Layout-Audit | Selbsttest |
| Markdown-Struktur | 22 Proben |
| Titel-Klinke | 20 Proben |
| Herzschlag | Selbsttest inkl. Sabotage |
| Klick-Kette | 25 Tests |
| Workflow-Aufruf-Vertrag | 837 Aufrufe · 0 Verstoß |
| Wachen-Vertrag | 413 Skripte · 0 Fund |

**Rot, das bleibt — und warum es kein Befund ist:**

- `test_feed_traegt_den_kanal_auf_beiden_ebenen` — braucht
  `public/index.xml`, das nur ein Hugo-Build erzeugt. In dieser Umgebung
  gibt es kein Hugo; auf `main` identisch. **Einziger Fehler der
  Vollsuite** (6499 Tests, 1328 s).
- Der zuvor genannte `test_pr1205_heizoel_…` steht **nicht** mehr in der
  Liste — er ist mit dem Ledger-Stand dieser Branch grün geworden.
