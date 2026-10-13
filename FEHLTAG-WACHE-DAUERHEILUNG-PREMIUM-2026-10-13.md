# Fehltag-Wache: Dauerheilung der Kadenz-Lücke (#725)

**Auftrag (Frank, 13.10.2026):** „Kadenz: 12 Nachlieferungen für 11 Mo/Mi/Fr-Fehltage (inkl. 05.10.) – #725. Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben.“

**Vorgeschichte:** Die Nachlieferung selbst ist mit PR #725 gemergt (Bericht `FEHLTAGE-NACHHILFE-KADENZ-PREMIUM-2026-10-13.md`). Dieser Vorgang behandelt die **Ursache**: Warum konnten elf Fehltage und ein leerer Montag unbemerkt bleiben, und wie verhindern wir, dass es wieder passiert?

**Prüfmaßstab:** `docs/CADENCE-REPORT.md` Regel 2 (nur Mo/Mi/Fr, 2–3 Artikel je Publikationstag), durchgesetzt von `scripts/cadence_guard.py`.

---

## Kurzfassung

Die Nachlieferung hat den Bestand geheilt. Die **Wache dahinter** hatte zwei blinde Stellen, die den Fehler erst möglich machten:

1. **Ein Publikationstag ohne jeden Post war unsichtbar.** Die Zählung (`find_violations`) lief über die Tage, an denen überhaupt ein Post liegt. Der Montag 31.08. mit 0/2 kam deshalb in keiner Warnung vor.
2. **Ein Defizit blieb folgenlos.** `--check` endete mit Exit 0, sobald nur Mindestziel-Defizite vorlagen. Der Hinweis „Fallback-Slots heilen nach“ galt für vergangene Tage nicht mehr, und niemand wurde gerufen.

Beides ist behoben. Der Guard bewertet jetzt den **Kalender** seit Launch und lässt `--check` bei einem Defizit im jüngsten Prüffenster scheitern.

| Kennzahl | vorher | nachher |
|---|---|---|
| Publikationstage, die der Guard sieht | nur Tage mit ≥1 Post | **alle Mo/Mi/Fr seit 08.08.2026** (28 Tage) |
| Leerer Publikationstag | unsichtbar | erkannt, Zählung `0` |
| `--check` bei Defizit im Prüffenster | Exit 0 | **Exit 1** |
| `--check` bei Altbefund | Exit 0 | Exit 0 (Altbefund im Report) |
| `--fix` | Heiler | Heiler, weiterhin **nie** Exit 1 wegen Fehltagen |
| Bestand heute | 56 live, 28/28 Tage mit 2 | unverändert: 56 live, 28/28 Tage mit 2, kein Defizit |

---

## Ursachenanalyse

### Ursache 1: Kalenderlücke in `find_violations`

Vorher:

```python
for day in sorted(by_day):          # by_day enthält nur Tage MIT Posts
    if is_publication_day(day) and day <= today:
        ...
```

Ein Tag ohne Post existiert in `by_day` nicht und wird nie bewertet. Das war strukturell, nicht Zufall: Der Mo 31.08. hatte null Live-Artikel und stand deshalb in keiner der elf ⚠️-Zeilen. Gefunden wurde er nur durch den manuellen Abgleich des Publikationskalenders gegen die Artikelordner.

### Ursache 2: Defizit ohne Folge

`find_violations` lieferte Defizite als `under_days`, aber `main()` gab bei `total == 0` immer Exit 0 zurück, nur mit dem Satz „Fallback-Slots heilen nach“. Diese Aussage gilt nur für den laufenden Tag. Für vergangene Tage kann kein Fallback-Slot mehr etwas nachfüllen. Ein Defizit, das nie geheilt wird, bleibt dauerhaft stehen und fällt in keinem Gate auf.

### Warum das mit „Ruhetag“ und Engine nicht zusammenhing

`engine_issue.py` und `publication_check.py` messen den **jüngsten Publikationstag** über `published_on()` und zählen damit einen leeren Tag korrekt mit 0. Die Lücke lag also allein in der Historien-Sicht der Kadenz-Wache, nicht im Tagesdefizit-Kanal.

---

## Fix

Geändert: `scripts/cadence_guard.py` (Code, Selbsttest, Report) und `docs/CADENCE-REPORT.md` (Regel 7).

- **`BLOG_LAUNCH = 2026-08-08`**: Startdatum laut Regel 1. Davor zählt kein Tag.
- **`publikationstage_im_intervall()`**: alle Mo/Mi/Fr im Intervall, Grundlage des Kalenders.
- **`find_violations(..., heute=None)`**: bewertet **jeden** Publikationstag seit Launch, auch mit 0 Posts. Der laufende Tag bleibt ausgenommen (er läuft bis 19:40 MESZ). `heute` ist injizierbar, damit der Selbsttest deterministisch ist.
- **`DEFIZIT_FENSTER_PUBLIKATIONSTAGE = 6`** und **`defizit_im_fenster()`**: Prüffenster = die letzten sechs Publikationstage strikt vor heute (rund zwei Wochen).
- **`main()` / `--check`**: Exit 1, wenn ein Defizit im Prüffenster liegt. Altbefund bleibt Exit 0, wird aber benannt.
- **`--fix`**: bleibt Heiler. Historische Fehltage führen dort **nie** zu Exit 1. Deploy, Endkontrolle und Blog-Health bleiben also stabil.
- **Report** (`CADENCE-GATE-REPORT.md`): Tagesliste zeigt Null-Tage mit 0; Defizite unterscheiden „im Prüffenster“ und „Altbefund“.
- **Selbsttest**: neuer Block mit eigenem Bestand (Mo 08-10 mit 1 Live, Mi 08-12 mit 1 Live und 1 Entwurf, Fr 08-14 ohne Post, Mo 08-17 mit 2, Mi 08-19 mit 3, Fr 08-07 vor Launch). Geprüft werden: Null-Tag wird erkannt, Entwurf zählt nicht, Launch-Grenze, laufender Tag ausgenommen, Fenster vs. Altbefund, Fensterstart, Null-Tag im Report.

---

## Belege

```
cadence_guard.py --selftest   → ✅ bestanden (inkl. Fehltage/Prüffenster)
cadence_guard.py --check      → ✅ exit 0 · kein Mindestziel-Defizit seit 2026-08-08
cadence_guard.py --fix        → ✅ exit 0
Bestand: 28 Publikationstage seit Launch · 28 mit 2 Live · 56 Live gesamt · 0 Off-Day · 0 Over-Cap
```

**Simulation an einer Kopie des Bestands** (Posts gezielt entfernt, Repo unberührt):

| Fall | Ergebnis | Erwartet |
|---|---|---|
| A: Mo 10.05. und die Posts dieses Ordners entfernt | `--check` **exit 1**, Fehltage 10.05. und 10.07. im Prüffenster benannt | ✅ |
| B: Mo 09.28. ohne Post (außerhalb des Prüffensters) | `--check` **exit 0**, „Altbefund“ | ✅ |
| C: wie A, aber `--fix` | **exit 0**, Fehltage im Log und im Report | ✅ |

Fall A zeigt 10.07. mit, weil ein Post mit Frontmatter-Datum 10.07. in einem Ordner `2026-10-05-…` lag. Der Guard zählt nach Frontmatter-Datum, wie es die SSOT verlangt.

**Unit-Suite** (`python3 -m unittest discover -s scripts/tests`): Ohne und mit Änderung dieselben Fehler außer vier Fällen, die in der Vergleichskopie ohne `.git` fehlschlagen. Keine neuen Fehler. Die zwei kadenznahen Fehler in `test_publication_reliability` existierten vorher. Die Sandbox hat weitere, nicht kadenzbezogene Fehler, etwa Scorecard, Schaltwerk und Kostensperre; sie sind nicht Teil dieser Änderung.

**Angrenzende Selbsttests:** `publication_check.py --selftest` ✅, `engine_issue.py --selftest` ✅.

---

## Entscheidungen (bewusst gesetzt, änderbar)

1. **Prüffenster = 6 Publikationstage** (`DEFIZIT_FENSTER_PUBLIKATIONSTAGE`). Kürzer = schneller alarmiert, länger = mehr Zeit zum Nachliefern. Die Konstante ist die einzige Stelle.
2. **Exit 1 nur in `--check`, nicht in `--fix`.** Ein Heiler, der Deploy oder Endkontrolle wegen Vergangenheit rot macht, würde den Live-Betrieb blockieren, ohne dass heute etwas zu heilen wäre.
3. **Altbefunde bleiben Exit 0.** Sonst wäre `--check` dauerhaft rot wegen Tagen, die nicht mehr heilbar sind. Die Altbefunde stehen trotzdem sichtbar im Report.

---

## Offen (Entscheidung des Betreibers)

- **CI-Verdrahtung des harten Gates.** Derzeit ruft **kein** Workflow `cadence_guard.py --check` auf. Die Workflows nutzen `--fix`, und dort greift das neue Gate bewusst nicht. Damit die Regel *automatisch* alarmiert, wäre ein `--check`-Schritt nötig, etwa in `blog-health-daily.yml` nach `--fix`. Das würde den Gesundheits-Job bei Fehltagen im Prüffenster rot schalten; welche Folgeprozesse daran hängen, sollte vorab geprüft werden. Ich habe das nicht eigenmächtig eingebaut.
- **Governance-Wortlaut.** `docs/GOVERNANCE-KONTRAKT.md` (C23) sagt: „Ein Fehltag wird NICHT nachgeholt.“ Die Nachlieferung von #725 war eine ausdrückliche Entscheidung Franks. Die Regel „Nachlieferung bei Fehltag“ ist im Kontrakt nicht formuliert und sollte dort ergänzt werden, falls sie gelten soll.

## Nicht getan

- Keine Artikel, Entwürfe oder Cover angefasst.
- Kein Gate-Workflow geändert.
- Kein Merge.
