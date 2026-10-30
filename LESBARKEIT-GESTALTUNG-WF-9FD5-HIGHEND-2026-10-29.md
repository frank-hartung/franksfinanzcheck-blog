# Lesbarkeit & Gestaltung · WF-9FD5 · Dauerheilung (HIGHEND, 29.10.2026)

**Vorgang:** WF-9FD5 · **Meldung:** [#901](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/901)
· **Workflow:** Layout-AI · **Roter Lauf:** [40336062251](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/40336062251) vom 26.10.2026, 15:03 UTC, Commit `2427f499`
· **Bereich:** Lesbarkeit & Gestaltung

---

## 1. Was gemeldet wurde — und was wirklich war

Die Meldung sagte:

> **Layout-AI ist fehlgeschlagen (failure)**
> Job „layout-audit“ – „Website bauen (identisch zur Produktion, minifiziert)“
> *Häufigste Ursachen: API-Key abgelaufen (GROQ/GEMINI), GitHub-Ausfall, transienter Fehler.*

Alle drei Ratschläge waren falsch. Der Lauf ist am **Bau** gestorben, an genau
einer Zeile Content:

```
content/posts/2026-10-09-balkonkraftwerk-foerderung-so-holst-du-dir-geld-zurueck/index.md:2
description: Stromkosten senken: Balkonkraftwerk-Förderung regional – Antrag und Anmeldung
```

Ein Doppelpunkt **innerhalb** eines unquotierten YAML-Werts. Ab da liest jeder
YAML-Parser `description: Stromkosten senken` und danach eine Verschachtelung.
Hugo bricht ab:

```
ERROR error building site: assemble: failed to create page from pageMetaSource
  …/index.md:2:14: [2:14] mapping value is not allowed in this context
```

**Reproduziert, nicht vermutet:** Der Baum von `2427f499` wurde ausgecheckt und
mit demselben Hugo (`v0.168.0+extended`) gebaut – der Bau stirbt an derselben
Zeile. Der heutige Stand baut grün, weil die Datei am 26.10. in #898 repariert
wurde.

**Fünf, nicht eine:** Die Wache meldet auf diesem Stand **5 Dateien** mit
derselben Klasse. Hugo nennt immer nur die erste; die anderen vier hätten den
nächsten Lauf getötet.

| Datei (Stand 26.10.2026) | Zeile |
|---|---|
| `posts/2026-10-09-balkonkraftwerk-foerderung-…/index.md` | 3 |
| `posts/2026-10-09-energiekosten-senken-smarte-helfer-…/index.md` | 3 |
| `posts/2026-10-12-energieausweis-was-das-dokument-…/index.md` | 3 |
| `posts/2026-10-12-haushaltskosten-reduzieren-…/index.md` | 3 |
| `posts/2026-10-12-kleine-energiespar-tricks-…/index.md` | 3 |

---

## 1b. Beim Aufsetzen gefunden: `main` ist am 29.10.2026 erneut rot — dieselbe Klasse

Beim Zusammenführen des aktuellen `main` (Stand `76efccb`, Commit aus #941
„WF-D0C9 #897 – Phase 1: Erste 9 Artikel bearbeitet") schlug die neue Wache
sofort an:

```
content/posts/2026-10-12-dein-weg-zu-geringeren-monatskosten-schritt-fuer-schritt/index.md:7
reserve_reaktiviert: "… Klasse „heilbar" ist heilbar, …"
```

Das deutsche Schlusszeichen **“** wurde durch das ASCII-Zeichen **"** ersetzt.
In einem doppelt gequoteten YAML-Wert beendet dieses Zeichen den Wert zu früh –
Hugo brach ab:

```
ERROR … expected <block end>, but found '<scalar>'
```

**Der Baum von `main` ließ sich in diesem Zustand nicht bauen** – nachgeprüft:
`hugo --minify` auf `76efccb` endet mit Exit 1. Also genau derselbe Ausfall wie
am 26.10., drei Tage später, an einer anderen Zeile.

Zwei Dinge daran sind lehrreich:

1. **Die Wache hat es gefunden, bevor ein Mensch es tat.** Der erste Lauf des
   neuen E2E-Gates auf diesem PR war rot – nicht wegen des PR, sondern wegen
   `main`. Genau dafür ist sie da.
2. **Der Scanner brauchte eine Lücke weniger.** Vorher hätte nur der Parser
   (PyYAML) die Stelle gesehen; die Build-Action läuft aber ohne PyYAML. Die
   Regel **F3 „Text hinter dem schließenden Anführungszeichen“** schließt die
   Lücke: Steht hinter dem ersten `"` noch Text, ist der Wert zu früh beendet.

Geheilt im selben PR (`--fix`, ein Zeichen, Text unverändert):

```diff
-reserve_reaktiviert: "… Klasse „heilbar" ist heilbar, …"
+reserve_reaktiviert: "… Klasse „heilbar“ ist heilbar, …"
```

Danach: 111 Seiten, `hugo --minify` **grün**, 136 Inhaltsdateien ohne Blocker.

---

## 1c. Beim Rebase gefunden: 10 Metadaten-Befunde auf `main` (mechanisch geheilt)

Der E2E-Lauf des PRs lief nach der Frontmatter-Heilung in das **Snippet-Gate**:
eine Description mit 160 Zeichen / 1018 px (Grenze 155 / 985). Die
`metadaten_wache` zeigte den ganzen Stand: **10 Befunde in 6 Artikeln**
(M2 Länge, M7 Breite, M3 `lastmod` vor `date`), alle aus dem Redaktionslauf
#941.

Geheilt wurden ausschließlich die Metadaten – Bedeutung, Kernaussage und
Keywords bleiben, die Kürzungen liegen zwischen 2 und 22 Zeichen:

| Artikel | vorher | nachher |
|---|---|---|
| `2026-08-12-dein-haus-sicher-schuetzen-…` | 1033 px (mit `…` abgeschnitten) | 972 px |
| `2026-08-17-privathaftpflicht-…` | 158 Z · 989 px | 152 Z · 950 px |
| `2026-09-21-zahnzusatzversicherung-…` | 1021 px (mit `…`) | 973 px |
| `2026-10-23-stromanbieter-wechseln-…` | 158 Z · 991 px | 134 Z · 850 px |
| `2026-10-28-dsl-und-internet-flat-…` | 160 Z · 988 px | 138 Z · 869 px |
| `2026-10-25-strategisch-sparen-…` | `lastmod` 25.10. vor `date` 28.10. | `lastmod: 2026-10-28` |

Beleg: `metadaten_wache` **0 Befunde**, `seo_cockpit --fail-on
description-length,description-breite,heading-order` **grün** (P2: 0).

## 1d. Beim Rebase gefunden: Siegel-Drift (nach Repo-Regel geheilt)

Das **Integritäts-Siegel** war auf `main` ebenfalls rot: `scripts/internal_linker.py`
ist nach #940 (`9bb3e86c1`, „restore sealed versions") festrelevant abgewichen
und stand als `VERSIEGELBAR` in der Akte. Nach der Repo-Regel („ein Fix, der
eine versiegelte Kerndatei berührt, ist erst fertig, wenn der Lock im selben
Commit mit-signiert ist") wurde `python3 scripts/integrity_guard.py --heal`
ausgeführt – nur diese eine Datei, mit Herkunft im Lock und Eintrag in
`data/integrity_history.jsonl`. `--check` ist danach grün.

---

## 2. Warum der Alarm so danebenlag (drei Ursachen, nicht eine)

| # | Ursache | Beleg |
|---|---|---|
| 1 | **Keine Prüfung vor dem Bau.** Alle Layout-/Inhaltswachen stehen *hinter* dem Build. Stirbt der Build, kann keine von ihnen etwas sagen. | Job-Liste: Schritt 4 `failure`, Schritt 5 `skipped` |
| 2 | **Erfundene Zahl im Meldungsskript.** `Number(process.env.STATIC_EXIT ?? '1')` machte aus „nicht gelaufen“ eine **1** – also „kritische Befunde“. Der Bericht war leer (`_Kein Report erzeugt._`). | `layout-ai.yml`, Issue-Schritt vor dieser Änderung |
| 3 | **Falscher Rat.** Der Alarm-Workflow kannte für „Layout-AI“ nur die Klasse `allgemein` → API-Key, GitHub-Ausfall, Neustart. Ein Neustart hätte denselben Bau wieder getötet. | Body von #901: `alert-runbook: allgemein` |

Der eigentliche Schaden war nicht der rote Lauf, sondern die Diagnose: Drei
Stunden Fehlersuche in die falsche Richtung, während die Ursache in Zeile 3
einer Datei stand.

---

## 3. Was repariert wurde (fünf Ebenen)

### Ebene 1 — Vorbeugen: `scripts/frontmatter_wache.py` (neu)

Prüft das Frontmatter **jeder** Inhaltsdatei vor dem Bau und nennt Datei, Zeile
und Spalte. Regeln F1–F6 (Gerüst, Parser, Plain-Skalar, Typvertrag,
YAML-1.1-Falle, Kommentar-Abschneidung) – inklusive der zweiten live
gefundenen Klasse „Text hinter dem schließenden Anführungszeichen“ (§1b).

* **Zwei Schichten, ehrlich benannt.** Die kritische Schicht (F1, F3–F6) ist
  **stdlib-only** und läuft auch im nackten Runner der Build-Action. Ist PyYAML
  vorhanden, parst zusätzlich der echte Parser (F2/F4). Der Bericht sagt, welche
  Schicht aktiv war – stille Degradierung wäre derselbe Fehler wie `--quiet`.
* **`--fix` beweist statt zu behaupten.** Es zitiert genau den Plain-Skalar und
  sonst nichts. Test: der geparste Wert ist vor und nach der Heilung identisch;
  Fließtext wird nie angefasst (Regression der Generalprobe: `Annahme: …` im
  Body war kurz davor, zitiert zu werden).
* **22 Selbsttest-Fälle**, u. a. der Originalzustand vom 26.10.2026.

### Ebene 2 — Verhindern, dass es wieder bis zum Bau kommt

Die Vorprüfung ist **Teil des Bauens** (`.github/actions/hugo-build`, neuer
Schritt `id: frontmatter`, **vor** dem Bau, fail-closed). Damit gilt sie an
*jeder* Baustelle des Repos: Deploy, E2E, Layout-AI, Publication-Reliability.
Zusätzlich als Quelle-Gate in `e2e.yml` (Fehler nach 5 Sekunden statt nach 8
Minuten).

### Ebene 3 — Diagnose: der Layout-AI-Lauf sagt jetzt die Wahrheit

| Vorher | Nachher |
|---|---|
| `STATIC_EXIT` fehlte → stillschweigend `1` | fehlt = „nicht gelaufen“ (eigener Zustand) |
| Statisches Audit lief gegen ein leeres `public/` | läuft nur nach grünem Bau |
| Browser-Audit „übersprungen“ = sieht grün aus | läuft nur nach grünem Bau, sonst fail-closed |
| Bericht: „Exit 1 / kritische Befunde“ | Bericht: „**Bau gescheitert**, erste Fehlerzeile: …“ |
| Summary leer | Summary: „⛔ Kein Bau – keine Messung“ + Ursache + Heilweg |
| finale Meldung ohne Ursache | `erste-fehlerzeile` ist eine **Ausgabe** der Action und steht im Text |

Beweis: die Wahrheitstabelle des Schluss-Schritts wird **ausgeführt** (8
Kombinationen, `scripts/tests/test_layout_ai_bauausfall.py`), nicht gelesen.

### Ebene 4 — Der Alarm-Rat passt zum Kanal

`alert-on-failure.yml` bekommt zwei eigene Runbook-Klassen:

* `layout-bau` – „Der BAU ist gescheitert, es fand KEINE Prüfung statt“, mit
  Frontmatter-Heilweg und Runbook-Verweis. Kein API-Key, kein Neustart.
* `layout-audit` – echte Layout-Befunde, mit `LAYOUT-REPORT.md` und
  `scripts/dom_audit.py`.

Die Klassen stehen **hinter** `selbsttest` (ein roter Selbsttest bleibt eine
Code-Regression) und **vor** `allgemein`.

### Ebene 5 — Der Vertrag hält es fest

`scripts/hugo_build_vertrag.py` bekommt **H9**: Vorprüfung vorhanden, **vor**
dem Bau, fail-closed, mit `erste-fehlerzeile` — und zwar **verhaltensgeprüft**:
Der echte Shell-Rumpf des neuen Schritts läuft gegen eine kaputte und eine
saubere Vorlage. Ein `|| true` im Kommentar ist kein Befund; ein `|| true` in
der Wirkung schon. Zwei neue Sabotage-Proben (S8, S9).

---

## 4. Belege (Befehle und ihre Ausgabe)

```text
$ python3 scripts/frontmatter_wache.py --selftest
✅ Selbsttest: 22 Proben bestanden – Wache ist scharf (Tiefenprüfung: YAML-Parser).
# ohne PyYAML (simuliert, wie im nackten Runner):
✅ Selbsttest: 21 Proben bestanden – Wache ist scharf (Tiefenprüfung: Scanner).

$ python3 scripts/frontmatter_wache.py --pfad <Baum von 2427f499> --kurzbefund
F3 …/index.md:3:32 – Doppelpunkt im unquotierten Wert von `description` …
Exit 1

$ python3 scripts/frontmatter_wache.py --pfad <Baum von 2427f499> --fix
Frontmatter-Heilung: 5 Wert(e) zitiert.
# danach: 5 Dateien · 5 Zeilen geändert, KEINE Body-Zeile.

$ python3 scripts/frontmatter_wache.py            # heutiger Bestand
Frontmatter-Wache: 136 Dateien | Blocker: 0 | Hinweise: 0 | Tiefenprüfung: YAML-Parser

$ python3 scripts/hugo_build_vertrag.py --selftest
✅ … (H1–H9, 9 Verhaltensproben am echten Shell-Rumpf, 11 Sabotage-Proben)

$ python3 -m unittest scripts.tests.test_frontmatter_wache
Ran 24 tests … OK

$ python3 -m unittest scripts.tests.test_layout_ai_bauausfall
Ran 8 tests … OK        # inkl. 8-gliedriger Wahrheitstabelle des Schluss-Schritts

$ python3 -m unittest scripts.tests.test_alert_scoping
Ran 27 tests … OK       # Simulation: „alle 62 Szenarien korrekt“,
                        # darunter die WF-9FD5-Reproduktion → runbook „layout-bau“

$ python3 scripts/trigger_wache.py --check     # 95 Workflows, 0 Befunde
$ python3 scripts/wachen_vertrag.py            # 352 Skripte, 0 Funde
$ python3 scripts/skript_syntax_wache.py --check   # 573 Dateien grün
$ python3 scripts/manifest_guard.py            # GRÜN, 0 Warnungen
```

Gegenprobe am echten Bau: Der Shell-Rumpf des neuen Schritts wurde mit
`GITHUB_OUTPUT`/`GITHUB_STEP_SUMMARY` gegen den gesunden Bestand (Exit 0) und
gegen eine Kopie mit der Zeile vom 26.10. ausgeführt (Exit 1, `::error`-Annotation
mit `content/posts/x/index.md:3:32`).

---

## 5. Was bewusst **nicht** getan wurde

* **Kein Abschalter für die Vorprüfung.** Keine Eingabe `frontmatter: "false"`.
  Ein Schalter „Prüfung aus“ ist ein Schalter „Blindflug“ – und der hat am
  26.10. einen Tag gekostet. Wenn die Wache falsch liegt, wird die Wache
  repariert.
* **Keine automatische Heilung im Bau.** `--fix` existiert, wird aber nicht
  automatisch ausgeführt: Ein Skript, das während des Deploys Inhalte
  umschreibt, wäre genau die stille Nebenwirkung, die dieses Repo ausschließt.
  Der Operateur sieht den Befund, heilt, prüft.
* **Keine zweite Wache für dieselbe Frage.** Die Längen- und Snippet-Regeln
  bleiben in `metadaten_wache.py` (M1–M7). Die neue Wache prüft nur, ob Hugo
  die Datei überhaupt lesen kann.
* **Keine Ausnahme eingetragen.** Der Bestand ist blockerfrei – es brauchte
  keine.

---

## 6. Betrieb (für den nächsten roten Lauf)

```bash
npm run frontmatter:check        # prüfen (Exit 1 = Bau-Blocker)
npm run frontmatter:fix          # die Doppelpunkt-Klasse heilen
npm run test:frontmatter         # Selbsttest + Unit- und Workflow-Vertragstests
npm run build:vertrag            # H1–H9 (inkl. Verhaltensprobe der Vorprüfung)
```

Wenn Layout-AI rot ist:

1. **Bau oder Befund?** Die Meldung sagt es jetzt im ersten Satz (`**Bau:**`).
2. **Bau rot** → `layout-bau`: erste Fehlerzeile in der Meldung, sonst
   `python3 scripts/frontmatter_wache.py`. Runbook:
   `docs/ANLEITUNG-HUGO-BUILD.md`.
3. **Befund** → `layout-audit`: `LAYOUT-REPORT.md` in der Job-Zusammenfassung,
   Zahlen in `.cache/layout/dom-audit.json`. Runbook:
   `docs/LAYOUT-AUTOMATISIERUNG.md`.

---

## 7. Restrisiko (offen und benannt)

* **Die obere Schicht braucht PyYAML.** Im nackten Build-Runner ist nur der
  Scanner aktiv. Er deckt die Klasse, die den Ausfall verursacht hat, beweisbar
  ab (Test ohne PyYAML) – exotischere YAML-Fehler sieht erst der Parser in E2E
  und Publication-Reliability. Das steht so im Bericht jedes Laufs, statt still
  zu degradieren.
* **Menschen schreiben weiterhin Content.** Die Wache verhindert, dass ein
  kaputtes Frontmatter den *Bau* erreicht. Sie verhindert nicht, dass jemand
  ein sauberes, aber falsches Frontmatter schreibt – das bleibt Aufgabe von
  `metadaten_wache.py` und der Redaktionsgates.
* **Der historische Lauf bleibt rot.** Er wird nicht nachträglich grün; die
  Meldung #901 wird mit diesem Vorgang geschlossen, der nächste geplante Lauf
  auf `main` ist der Beweis am lebenden Objekt.
