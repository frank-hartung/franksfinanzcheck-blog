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

- 48/48 eigene Tests **und** 45/45 gegen die `main`-Testdatei (beide Richtungen).
- `--selftest`: 28 Proben.
- Vollscan: 175 Dateien, **0 Blocker**, 0 Hinweise.
- Governance-Kontrakt C1–C49 grün.

**Drei Lücken gegen `main` nachgemessen** (nicht behauptet — mit `python3 -E -s`
und blockiertem `yaml`-Import bzw. fremder Testdatei):

1. **Flow-Mapping ohne PyYAML:** `main` ist **blind**. Der e2e-Job
   („Frontmatter-Vertrag — Quelle (vor jedem Bau)") läuft VOR jedem
   `pip install`; dort gibt es kein PyYAML, und `main` hatte die
   Flow-Erkennung nur im Parser.
2. **Meldung nennt den Block nicht:** `main` sagt „steht doppelt (zuerst Zeile
   6)" — bei `redaktionelle_pruefung`, `cover` und `seo` ist das die halbe
   Auskunft. Der Rahmen trägt jetzt den Schlüsselnamen.
3. **Dedupe hing am Wortlaut:** Nach einer Umformulierung griff sie nicht mehr
   und meldete Top-Level-Duplikate doppelt. `_ist_duplikat()` prüft den Inhalt.

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

Eine zurückgestellte Stelle steht **befristet** in der Sperrklinke
(bis 31.01.2027), danach entsteht automatisch ein neuer Befund.

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
| Frontmatter-Wache (eigene Tests) | 48/48 |
| Frontmatter-Wache (gegen `main`s Testdatei) | 45/45 |
| `--selftest` Wache | 28 Proben |
| Vollscan Bestand | 175 Dateien · 0 Blocker |
| Governance-Kontrakt | C1–C49 |
| Release-Scorecard | 58/58 |
| Fachbefund-Ledger | 21/21 |
| Befund-Akte | 11/11 |
| E2E-Textanker | 7/7 · Bestand 0 Befunde |
| Design-Gate | 11 Gruppen |
| Layout-Audit | Selbsttest |
| Markdown-Struktur | 22 Proben |
| Titel-Klinke | 20 Proben |
| Herzschlag | Selbsttest inkl. Sabotage |
| Klick-Kette | 25 Tests |
| Workflow-Aufruf-Vertrag | 837 Aufrufe · 0 Verstoß |
| Wachen-Vertrag | 413 Skripte · 0 Fund |

**Geerbtes Rot, das bleibt** (auf `main` identisch, nicht von diesem PR):
`test_pr1205_heizoel_folgeentscheidungen_sind_belegt_wiederhergestellt` —
ein eigener Doppelschlüssel in einer Test-Fixture; `test_feed_traegt_den_kanal_…`
— braucht einen Hugo-Build.
