# Vorfall-Bericht: „Content-Engine v2" rot — das Siegel selbst war zerbrochen

**Datum:** 22.09.2026 · **Status:** behoben (Reparatur belegt, Ursache geschlossen)
· **Schweregrad:** hoch (zwei Produktions-Slots fielen aus, **kein** Schaden an
Artikeln, Links oder Builds)
**Vorgänger:** [Vorfall 19.09.2026 — der Integritäts-Lock stoppte die Produktion](INCIDENT-2026-09-19-integritaets-lock.md)

## Kurzfassung

Zwei Läufe der Content-Engine starben am Abend des 21.09.2026 im **ersten
Schritt**, vor jeder Artikelarbeit. Zum dritten Mal in vier Tagen stand der
HARD STOP — aber diesmal war **keine einzige Kerndatei verändert**. Zerstört
war das Siegel selbst: Ein Merge hat zwei Fassungen von
`data/integrity_lock.json` wie Quelltext zusammengesetzt. Das Ergebnis (7.185
Bytes) ist kein gültiges JSON mehr — die Bruchstelle liegt bei **Byte 7.171**,
dahinter steht der Rest einer anderen Fassung. Beide Mergeseiten waren für
sich einwandfrei.

Der eigentliche Defekt war nicht der Merge, sondern die blinde Stelle danach:
Das Siegel konnte sich **selbst nicht prüfen**. `load_lock()` verschluckte den
Syntaxfehler zu „0 Dateien gelockt", der Guard meldete daraufhin das *Symptom*
(„6 kritische Knoten neu ohne Signatur"), und der Alarm schickte den Menschen
zu API-Keys. Es gab **keinen Weg zurück** außer einer menschlichen Signatur —
obwohl der Kern nachweislich unversehrt war: Alle 43 gesperrten Dateien
stimmten Byte für Byte mit der letzten gültigen Signatur überein (`da493edf`,
`sha256 721c5659…`).

Behoben ist jetzt beides: die **Ursache** (Maschinen-Artefakte werden nicht
mehr gemergt — `.gitattributes: merge=binary`) und die **Wirkung** (das Siegel
ist prüfbar, verkettet, atomar geschrieben und belegt reparierbar). Die Engine
heilt ein beschädigtes Siegel künftig selbst, statt daran zu sterben.

## Was gemeldet wurde

| Lauf | Auslöser | Commit | Ergebnis |
|---|---|---|---|
| [35644553718](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/35644553718) | schedule 19:23 UTC | `661a878f` | ❌ „Integritäts-Lock prüfen & belegten Drift signieren (HARD STOP bei Sabotage)" |
| [35655896206](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/35655896206) | schedule 21:13 UTC | `f9df9ae2` | ❌ derselbe Schritt |

Der Fehler-Alarm [Issue #346](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/346)
öffnete sich 19:24:17 UTC automatisch. Das Alerting hat funktioniert — die
Zuordnung wieder nicht: Die Meldung riet zu abgelaufenen API-Keys, GitHub-Ausfall
oder einem transienten Fehler. Das Log wusste es besser, sagte es aber nicht:
Es nannte sechs „neu ohne Signatur"-Knoten.

**Beide Gates waren auf genau diesem PR rot — und der Merge ging trotzdem
durch.** Für den Kopf `d364e039` (den Merge-Commit mit dem kaputten Siegel)
wurden zwei Läufe erzeugt:

| Lauf | Gate | Roter Schritt | Ergebnis |
|---|---|---|---|
| [35643686499](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/35643686499) | Integritäts-Lock (PR-Gate) | 4. „Integritäts-Siegel prüfen (HARD STOP – Sabotage-Schutz)" | ❌ failure |
| [35643686448](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/35643686448) | Publication reliability regression tests | 5. `unittest discover -s scripts/tests` | ❌ failure |

Der Unittest-Lauf fiel über genau dieses Siegel: `RepoSealTests`
(`test_ausgelieferter_baum_passt_zum_siegel`, `test_siegel_kennt_jeden_kritischen_knoten`,
`test_akte_bleibt_gebunden_und_bennbar`) — die **Erkennung funktionierte also**.
Was fehlte, war die **Wirkung**: Kein Ruleset verlangt diese Checks
(`Integritäts-Siegel` ist der dokumentierte Dauerzustand, `docs/PFLICHT-CHECK-RUNBOOK.md`,
Governance C18/C15), also hielt das rote Kreuz niemanden auf.

Genau daraus folgt die Bauart dieser Reparatur: Der Schutz muss im **Artefakt
selbst** liegen (Kette, Prüfsummen, `merge=binary`, Selbstheilung) und nicht
allein in einem Check, den niemand verlangt.

## Was tatsächlich passiert ist

| Zeit (UTC) | Ereignis |
|---|---|
| 21.09. 18:44:42 | `da493edf` (nach Merge identisch mit `fe97f39f`) — **letzte gültige Signatur**, 7.339 Bytes, `sha256 721c5659…`, Stand `14c1a89`, 43 Dateien |
| 21.09. 19:01:20 | `da493edf` „fix(alerting): #343 … + Lock-Neusignatur (#345)" — gültig |
| 21.09. 19:15:30 | `d364e039` „Merge branch 'main' into arena/01a0c4dc-franksfinanzcheck-blog" — **erzeugt das kaputte Siegel** (7.185 Bytes) |
| 21.09. 19:23:55 | Content-Engine v2 stirbt im ersten Schritt; Issue #346 |
| 21.09. 21:13:32 | zweiter Lauf stirbt im selben Schritt |
| 22.09. | Reparatur + dauerhafte Schließung der Ursache (dieses Dokument) |

### Der Beweis, Byte für Byte

Die beiden Eltern des Merges waren **für sich gültig**:

| Fassung | Bytes | SHA-256 (Anfang) | Zustand |
|---|---|---|---|
| `2b726664` (Zweig-Seite) | 7.983 | `e97fe3ba…` | gültiges Siegel, 12 Akteneinträge bis `d192a90` |
| `fe97f39f` (main-Seite) | 7.339 | `721c5659…` | gültiges Siegel, 12 Akteneinträge bis `14c1a89` |
| `d364e039` (**Merge-Ergebnis**) | 7.185 | `22426dfd…` | **JSONDecodeError: line 158 column 7 (char 7171)** |
| HEAD `e64cdac` (bis zur Reparatur) | 7.185 | `22426dfd…` | identisch — der Schaden lag seit dem 21.09. 19:15 UTC in `main` |

Gelesen mit dem neuen Guard:

```
$ python3 scripts/integrity_guard.py --drift-audit
🧨 SIEGEL NICHT GESUND – die Drift-Aufstellung unten ist darum zweitrangig:
  **Siegel ZERSTÖRT (kein gültiges JSON)** · 7185 Bytes · Bruchstelle Byte 7171 · Verdacht: zusammenschnitt
  JSON nicht lesbar: Expecting property name enclosed in double quotes: line 158 column 7 (char 7171)
  Bruchstelle: Byte 7171 von 7185 (Zeile 158)
  Hinter der Bruchstelle steht der Rest einer ANDEREN Fassung – Muster:
  zwei Stände wurden zusammengesetzt (Merge-Konflikt in einer Maschinendatei).
```

Die letzten Bytes des Artefakts (`]\n    }\n  ]\n}\n`) sind genau das Ende
einer der beiden gültigen Fassungen — vorne steht der eine Stand, hinten der
Falz des anderen. Genau das erzeugt ein Text-Merge in einer Datei, die kein
Text ist.

### Warum das die Produktion traf

1. `load_lock()` fing den Syntaxfehler mit `except Exception` und lieferte
   `{"signed_at": "beschaedigt", "files": {}}` — formal korrekt, praktisch
   fatal: „0 Dateien gelockt" ist **kein** Zustand, es ist Blindheit.
2. `verify_files()` sah daraufhin jeden kritischen Knoten als „neu ohne
   Signatur" → `exit_fuer` → **Exit 3, HARD STOP**.
3. Der HARD STOP steht als **erster Schritt** der Content-Engine → kein
   Artikel, kein Slot, Defizit-Alarm (und die Folgeschritte wurden von der
   roten Phase überlagert).
4. `--heal` durfte nicht: Ohne lesbares Siegel gibt es nichts zu belegen. Es
   blieb nur `--set-current` — die **menschliche** Signatur. Ein Betrieb, der
   bei jedem Artefakt-Schaden auf einen Menschen wartet, ist kein Betrieb.

## Die Reparatur (was der Lauf jetzt tut)

**Sofort (dieser Vorfall):** Das Siegel wurde aus dem beschädigten Artefakt
**geborgen** — vorne war es vollständig. Übernommen wurden die 43 Datei-Hashes
und die 11 lesbaren Akteneinträge; **keine Datei wurde neu gezeichnet**. Die
Bergung war nur zulässig, weil die geborgene Map den Baum exakt und
vollständig deckt (43/43, alle Klassen, keine fremden Pfade).

```
$ python3 scripts/integrity_guard.py --repair-lock
🛠️  INTEGRITÄTS-SIEGEL BESCHÄDIGT – Diagnose: … Bruchstelle Byte 7171 …
   Quelle: Bergung aus dem beschädigten Artefakt (11 lesbare Akteneinträge, Map deckt den Baum exakt)
   - git-head: verworfen (Siegel ZERSTÖRT)
   - git-historie: keine gültige Fassung in der lokalen Historie (flacher Klon?)
🔧 SIEGEL REPARIERT (bergung): 43 Kerndateien entsprechen wieder exakt dem signierten Stand.
   Keine Datei wurde neu gezeichnet – nur die zerstörte Akte ersetzt.
   Kontrolle: 43 Dateien, Fassung 2, Kette + Map-Prüfsumme
```

**Dauerhaft (vier Lagen, alle mit Test):**

| Lage | Was | Wo |
|---|---|---|
| **Ursache** | Maschinen-Artefakt wird nicht mehr als Text gemergt: `merge=binary` → sichtbarer Konflikt statt stiller Zusammenschnitt. Zusätzlich die Hausregel in CLAUDE.md. | `.gitattributes`, `CLAUDE.md` |
| **Schreiben** | Temp-Datei + `os.replace` + `fsync`, davor Serialisierungsprüfung, danach **Rück-Leseprobe von der Platte**. Ein abgebrochener Lauf (Kill/Timeout) hinterlässt die vorige Fassung — nie ein halbes Siegel. | `integrity_guard.lock_schreiben` |
| **Erkennen** | Siegel-Zustand ist eine **eigene erste Frage**: `ok` / `ok-legacy` / `beschaedigt` / `chimäre` / `fremdformat` / `fehlt`, mit Bruchstelle, Byte-Größe und Muster (Abbruch vs. Zusammenschnitt). Neu im Artefakt: `schema`, `files_sha256` (Map-Prüfsumme), `prev_sha256` (Kette über die Akte), `audit_start_sha256` (Anker des ältesten Eintrags). Ein **syntaktisch gültiger** Zusammenschnitt fällt damit ebenfalls auf. | `lock_zustand`, `_kette_pruefen` |
| **Heilen** | `--repair-lock` mit Beweisleiter: **1.** committeter Stand (HEAD) → **2.** jüngste gültige Fassung der lokalen Historie → **3.** Bergung aus dem beschädigten Artefakt (nur wenn committet und Map = Baum). Sonst **Exit 3 ohne Schreiben**. `--heal` (erster Engine-Schritt) fährt das automatisch. `--gate` bleibt read-only und fail-closed, nennt aber jetzt Ursache und Reparaturzeile. | `lock_reparatur`, `heilen`, `gate` |

Der HARD STOP für echten Kern-Drift ist **unverändert hart**: KRITISCH und
Laufzeit-Mutationen bleiben menschliche Entscheidungen. Neu ist nur, dass ein
kaputtes *Siegel* nicht mehr wie Sabotage am *Kern* aussieht.

## Nachweis

- **Beweis im Guard selbst** (`--selftest`, läuft in jedem PR und jedem
  Engine-Lauf, schreibt nichts): 9 eingefrorene Fälle + Kern-Beweis mit
  Siegel-Diagnose, Reparatur aus der Historie und Abbruchsicherheit.
  `python3 scripts/integrity_guard.py --selftest` → Exit 0.
- **Regressionstests** (`scripts/tests/test_integrity_guard.py`): 23 neue
  Tests — `SiegelZustandTests` (8: Bruchstelle, Muster, Chimäre, Kettenbruch,
  Kappung, Legacy, kein stilles Verschlucken), `ReparaturTests` (9:
  Quellenleiter, Bergung im flachen Klon, Ablehnung bei Drift, keine Quelle =
  Exit 3, `--heal` heilt das Siegel, Gate bleibt read-only),
  `SchreibsicherheitTests` (4: Abbruch, ungesundes Siegel, Rückleseprobe,
  lautes Scheitern) und zwei neue Siegel-Prüfungen im ausgelieferten Baum
  (`RepoSealTests`), inklusive „das Siegel ist mit seinem Beleg committet".
  Die Datei läuft von 24 auf 47 Tests; `python3 -m unittest discover -s
  scripts/tests` ist damit grün (die vier Import-Fehler des Gesamtlaufs sind
  Umgebungs-Abhängigkeiten — `yaml`/`playwright` — und bestehen unabhängig
  von diesem Vorfall).
- **Kein Inhalts-Eingriff:** Der Kern steht seit der Reparatur wieder exakt
  auf der Signatur `files_sha256 224bec94…`; die Reparatur hat **null** Dateien
  neu gezeichnet (Akte: `"geaendert": []`, `"art": "repair"`).

## Selbst prüfen

```bash
python3 scripts/integrity_guard.py --selftest          # Beweis des Wächters (schreibt nichts)
python3 scripts/integrity_guard.py --drift-audit       # Siegel-Zustand + Herkunft (read-only)
python3 scripts/integrity_guard.py --gate              # PR-Gate, fail-closed
python3 scripts/integrity_guard.py --repair-lock --dry-run   # würde es heilen? (schreibt nichts)
python3 -m unittest discover -s scripts/tests          # Regressionstests
```

## Produktivbetrieb

- Läuft die Engine als erster Schritt in `--heal`, ist ein beschädigtes Siegel
  **kein Produktionsstopp mehr**: Es wird belegt geheilt, protokolliert
  (`::warning::` + `INTEGRITY-REPORT.md` + `data/integrity_history.jsonl`,
  `modus: repair`) und der Lauf arbeitet weiter. Bleibt daneben echter Drift,
  gilt die gewohnte Regel (FEST = Sichtung, KRITISCH = HARD STOP).
- Offen bleibt der bekannte **Dauerzustand**: Die PR-Checks
  `Integritäts-Siegel` und `unittest` sind weiterhin **nicht** als
  Pflicht-Checks im Ruleset hinterlegt (`docs/PFLICHT-CHECK-RUNBOOK.md`,
  Governance C18). Ein rotes Kreuz hält also keinen Merge auf — belegt durch
  diesen Vorfall (beide Checks rot, Merge trotzdem). Deshalb liegt die
  Schließung im Artefakt selbst (Kette + `merge=binary` + Selbstheilung) und
  nicht allein im Gate.
- Ehrliche Grenze: Das Siegel ist ein **Sabotage-Melder**, keine
  Signatur-Autorität mit Schlüssel. Wer Push-Rechte hat, kann neu signieren —
  das war vorher so und bleibt so. Was sich ändert: Ein *unbeabsichtigter*
  Schaden ist jetzt laut, benannt und innerhalb eines Schrittes geheilt.
