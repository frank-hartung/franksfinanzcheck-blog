# Sprach-Pipeline: Reparatur der fünf roten Vertragsverletzungen

**Datum:** 31.10.2026 · **Auftrag (Frank):** „Bitte vollständig umsetzen auf
Highend-Level einer Profi-Agentur.“ · **Vorgänger:** PR #977 (Grammar/LT5–LT6,
gemergt als `6a9c05e`) · **Ausgangsstand:** `eb67232` (main)

---

## 1. Der Befund in einem Satz

Fünf Tests des Bestands waren rot – und keiner davon war ein Testfehler:
Die Sprach-Qualitäts-Pipeline konnte nicht pushen, konnte ihren Strict-Modus
nicht auslösen, konnte kein Issue mit Labels eröffnen, interpolierte Eingaben
unmittelbar in die Shell, und der Selbsttest des Copy-Editing-Gates schrieb
während der Beweisführung in `data/lektor_history.jsonl`. Alle fünf sind
**Zusagen ohne Beweis** – die Form, die dieses Repo in C12/C15 verbietet.

| Test | Befund am Ausgangsstand | Klasse |
|---|---|---|
| `test_actions_version_guard.test_setup_python_is_uniform` | 2 verschiedene `actions/setup-python`-Pins (v5.1.1 gegen 58× v7.0.0) | Drift |
| `test_push_wache` | `git push \|\| true` in `sprach-qualitaet-pipeline.yml:134` | C12/Push-Wache |
| `test_unabhaengiger_tiefencheck` | `${{ … }}` in vier `run:`-Blöcken | Template-Injection |
| `test_bot_watchdog_meldetakt` (Governance) | C12: Issue-Labels werden nie angelegt | C12 |
| `test_versicherungs_cluster_verlinkung` | Kfz-Artikel live, im Pillar nicht verlinkt | Wiedervorlage |

---

## 2. Warum der Selftest schrieb (C15) – die eigentliche Wurzel

`copy_editing_gate.py --selftest` ruft alle sechs Engines mit `--selftest` auf.
Fünf davon beenden den Lauf nach den eingefrorenen Fällen – `lektor_guard.py`
nicht. Dort lief `run_selftest()` und **danach** der volle Bestandslauf, der
eine Zeile an `data/lektor_history.jsonl` anhängt:

```
{"date": "2026-10-31", "mode": "REPORT", "L3": 325, "L5echo": 330, …}
```

Der Beweis war damit selbst der Vorgang, den er ausschließen soll: Die
Messgröße war verändert, bevor gemessen wurde. Wer das mit einem Commit der
History-Zeile „repariert“, hat den Fehler in die Dauer übernommen.

**Reparatur:** `lektor_guard.py` hat jetzt einen reinen Beweispfad
(`--selftest` → 17 Fälle, Exit-Code, kein Report, keine History, kein Artikel).
Zusätzlich prüft der Gate **jeden** Lauf gegen einen Fingerabdruck des
Arbeitsbaums (Status + SHA-256 je Pfad): Ändert die Beweisphase eine Datei,
endet der Lauf mit Exit 2 – unabhängig davon, welche Engine schreibt. Eine
künftige Engine mit demselben Fehler fällt beim ersten Lauf auf, nicht nach
Monaten.

---

## 3. Die zweite stille Lüge: Schalter ohne Wirkung

Der Gate baute **eine** Argumentliste und gab sie an alle sechs Engines weiter.
Realität war:

| Engine | `--file` | `--include-drafts` | `--json` | `--strict` |
|---|---|---|---|---|
| `grammar_check` | ✅ | ✅ | ✅ | ✅ |
| `zeit_rechtschreibung` | ✅ | ✅ | ✅ | ✅ |
| `sprachglatt` | ✅ | ✅ | ✅ | ✅ |
| `hardcases_guard` | **ignoriert** | **ignoriert** | **ignoriert** | **ignoriert** |
| `lektor_guard` | **ignoriert** | **ignoriert** | **ignoriert** | **ignoriert** |
| `readability_check` | ✅ | **ignoriert** | ✅ | **ignoriert** |

Ein Lauf `--file X.md` versprach „ein Artikel“, prüfte in Wahrheit drei
Engines auf dem ganzen Bestand und drei auf dem Artikel – und protokollierte
das als einen Lauf. `--strict` konnte für die Hälfte der Kette nie greifen.

**Reparatur (Highend, nicht kosmetisch):**

1. `hardcases_guard.py` und `lektor_guard.py` haben einen echten
   Einzeldatei-Modus (`--file`), inklusive Reichweiten-Schutz: Pfade außerhalb
   des Repos oder ohne Existenz enden mit Exit 2 statt in einem stillen Lauf.
2. Der Gate baut die Argumente pro Engine aus `ENGINE_FAEHIGKEITEN` – nur was
   die Engine auswertet, wird übergeben.
3. Die Tabelle wird gegen den Quelltext geprüft (`_faehigkeiten_pruefen`), in
   **beide** Richtungen: Engine kann mehr als die Tabelle sagt, oder die
   Tabelle verspricht, was die Engine ignoriert. Beides ist Exit 2.
4. `--file` bei einer Engine ohne diesen Modus bricht ab – kein stiller
   Wechsel des Prüfumfangs.

---

## 4. Was am Workflow repariert wurde

| # | Vorher | Wirkung | Nachher |
|---|---|---|---|
| 1 | `${{ inputs.* }}` in vier `run:`-Blöcken | Eingaben wurden ungeprüft in die Shell interpoliert (Template-Injection) | Eingaben über `env:` (`EINGABE_MODUS`, `EINGABE_SCOPE`, `EINGABE_DATEI`), Ausgaben über `$GITHUB_OUTPUT` |
| 2 | `… \|\| true` + `echo $?` | `$?` las den Exit von `true` (immer 0) – Strict war wirkungslos | `set +e` → `RC=$?` → `gate_exit_code`; unbekannter/fehlender Code = `sabotage` (fail-closed) |
| 3 | `git push \|\| true` bei `permissions: contents: read` | Push technisch unmöglich, Fehler verschluckt, History verfiel im Runner | `scripts/git_sync.sh --push-only` + `contents: write` |
| 4 | Labels nie angelegt | Issue-Erstellung wäre mit HTTP 422 gescheitert (#209) | Schritt „Labels sicherstellen (C12)“ mit `--force`, **vor** dem Issue |
| 5 | `setup-python` v5.1.1 | Repo-Pin-Drift | `5fda3b95…` (v7.0.0) |
| 6 | Strict-Verstoß blieb grün | „Verstoß“ ohne Folge | Neuer letzter Schritt wertet den Verstoß rot – **nach** Issue, Artefakten und History |

Punkt 6 ist eine Präzisierung, die beim Lesen auffiel: Die Dokumentation
versprach „Exit 1 → Workflow rot“, die Implementierung öffnete nur ein Issue.
Jetzt gilt beides in der richtigen Reihenfolge – der rote Exit steht am Ende,
weil ein fehlgeschlagener Schritt alle folgenden ohne `always()` überspringt.

---

## 5. Der Pillar-Link (Wiedervorlage eingelöst)

`2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen` ist live, der
Versicherungs-Pillar verlinkte ihn nicht. Im Kfz-Abschnitt steht jetzt ein
kontextueller Link; die drei weiterhin als Entwurf geführten Artikel bleiben
bewusst unverlinkt (W11: tote Linkziele). `lastmod` wurde auf `2026-10-31`
gezogen.

---

## 6. Beweise (gemessen, nicht behauptet)

| Beweis | Ergebnis |
|---|---|
| `test_copy_editing_gate_schnittstelle` | 12 Tests grün (inkl. 4 Negativfälle) |
| `test_workflow_push_rechte` | 6 Tests grün (Rechte-Klasse für **alle** Workflows) |
| Uhr-Probe (`selftest_clock.py --trap-modul`, +97 Tage) | beide Module grün an fremdem Datum |
| `governance_contract.run_all(quick=True)` | **0 Befunde** |
| `lektor_guard.py --selftest` | 17 Fälle grün, `data/lektor_history.jsonl` bytegleich |
| `copy_editing_gate.py --selftest` | 6 Engines grün, „🔒 Schreibschutz-Beweis“ bestätigt |
| `git status` nach beiden Beweisläufen | unverändert |
| Volle Suite | siehe Abschnitt 8 |

Die Rechte-Klasse ist als **Regel** formuliert, nicht als Datei-Fall: Jeder
Workflow, dessen Schritt committet und `git_sync.sh --push-only` aufruft, muss
`contents: write` haben (Job- oder Workflow-Ebene). `deploy.yml` und
`design-varianten.yml` erfüllen das über Job-Rechte und bleiben unverändert.

---

## 7. Grenzen (ehrlich)

- Der Arbeitsbaum-Fingerabdruck vergleicht nur, was `git status` sieht.
  Ignorierte Reports (`*-REPORT.md`) sind bewusst ausgenommen – sie werden bei
  jedem Lauf neu geschrieben. Wer wissen will, ob ein Beweislauf **irgendwo**
  schreibt, braucht `strace`; für den Repo-Zustand ist die Probe scharf.
- Die Fähigkeitstabelle prüft Literale im Quelltext, nicht die Argumentanalyse.
  Sie ist eine Veraltungs-Wache, kein Parser. Ein Schalter, der nur im Docstring
  steht, ist trotzdem ein Befund – dann ist der Docstring falsch.
- Ohne `git` (z. B. Tarball) entfällt der Schreibschutz-Beweis sichtbar mit
  Warnung; die Engine-Selbsttests bleiben scharf.

---

## 8. Betrieb

```bash
# Beweis (schreibt nichts)
python3 scripts/copy_editing_gate.py --selftest

# Ein Artikel, nur melden
python3 scripts/copy_editing_gate.py --file content/posts/<slug>/index.md --report COPY-EDITING-REPORT.md

# Vertragstests
python3 -m unittest scripts.tests.test_copy_editing_gate_schnittstelle \
                   scripts.tests.test_workflow_push_rechte -v
```

Dokumentation: `docs/ANLEITUNG-COPY-EDITING-HIGHEND.md` (Abschnitte 3.1 und 10)
und `docs/ANLEITUNG-SPRACH-QUALITAET-PIPELINE.md` (Abschnitt 11).
