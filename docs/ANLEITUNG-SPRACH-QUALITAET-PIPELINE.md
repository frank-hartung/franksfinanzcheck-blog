# Sprach-Qualitäts-Pipeline (GitHub Actions, Highend)

> **Datei:** `.github/workflows/sprach-qualitaet-pipeline.yml`
> **Rollout:** Highend · **Zeitplan:** täglich 04:30 UTC · **Manuell auslösbar** über Actions
> **Stand:** 31.10.2026 – Reparatur nach #977 (siehe Abschnitt 11)

## 1. Was die Pipeline tut

Die Pipeline führt den vollständigen Copy-Editing-Highend-Durchlauf über den gesamten Blogbestand aus:

1. **Selbsttests aller 6 Engines** (Sabotage-Schutz, fail-closed). Bei Rot: Abbruch, Exit 2, keine Datei wird angefasst.
2. **grammar_check** (LT1–LT4, offline Grammatik)
3. **hardcases_guard** (H1–H9, deutsche Fest-Fehler)
4. **zeit_rechtschreibung** (ZEIT-Niveau, LanguageTool-kompatibel)
5. **sprachglatt** (DW1–DW9 Glättung + V1 Vorschläge)
6. **lektor_guard** (L1–L12 Verlags-Lektorat)
7. **readability_check** (Flesch-Amstad, Satzlänge, Schachtelsätze, Absätze, Passiv)

Alle Engines laufen 100 % offline, ohne API, ohne externen Dienst, ohne Datenabfluss (DSGVO-konform).

## 2. Modi (workflow_dispatch)

| Modus | Verhalten |
|---|---|
| `report` (Default) | Prüft und meldet. Schreibt Reports + Artefakte. Kein Schreiben in Artikel. |
| `fix` | Heilt eindeutige Fälle (harte Allowlist, verifiziert durch `sprachkern.write_verified`). |
| `strict` | Wie `report`, aber Exit 1 bei offenen kritischen Funden → Workflow rot + automatische Issue-Eröffnung. |

## 3. Scope (workflow_dispatch)

| Scope | Verhalten |
|---|---|
| `bestand` (Default) | Alle Artikel prüfen. |
| `new-only` | Nur Artikel von heute (Publish-Gate). |
| `file` | Einzelner Artikel (Pfad über `file_pfad` angeben). |

## 4. Exit-Codes & Verhalten

| Exit-Code | Bedeutung | Pipeline-Aktion |
|---|---|---|
| 0 | Sauber / gelaufen | ✅ Grün, Artefakte gesichert |
| 1 | Offene kritische Funde (nur strict) | ⚠️ Issue + Artefakte + History, **dann** roter Lauf (Schritt 10) |
| 2 | Selbsttest rot (Sabotage) | 🛑 Abbruch, keine Datei angefasst, **kein** History-Commit |

Der Gate-Exit wird echt erfasst (`set +e` → `RC=$?` → `gate_exit_code`), nicht
über `|| true` verschluckt. Fehlt der Code oder ist er unbekannt, wertet die
Pipeline den Lauf als `sabotage` (fail-closed) – geraten wird nicht.

## 5. Artefakte & Reports

Nach jedem Lauf werden als Workflow-Artefakte (30 Tage Aufbewahrung) gesichert:

- `COPY-EDITING-REPORT.md` – zusammengefasster Highend-Report
- `.copy_editing_report.json` – maschinenlesbar
- `GRAMMATIK-REPORT.md` + `.grammar_report.json`
- `HARDCASES-REPORT.md`
- `ZEIT-RECHTSCHREIBUNG-REPORT.md` + `.zeit_rechtschreibung_report.json`
- `SPRACHGLATT-REPORT.md` + `.sprachglatt_report.json`
- `LEKTOR-REPORT.md`

History-Files (versioniert, dedupliziert pro Tag) werden automatisch committed:

- `data/copy_editing_history.jsonl`
- `data/hardcases_history.jsonl`
- `data/sprachglatt_history.jsonl`
- `data/zeit_rechtschreibung_history.jsonl`
- `data/lektor_history.jsonl`
- `data/grammar_whitelist.txt`

Der Commit geht ausschließlich über `scripts/git_sync.sh --push-only`
(Push-Wache: Retries, Rebase gegen Parallel-Bots; roher `git push` ist im
Bestand verboten). Dafür braucht der Workflow `permissions: contents: write` –
ohne dieses Recht ist der Push technisch unmöglich, und ein verschluckter
Fehler würde die History still im Runner verfallen lassen.
## 6. Automatische Issue-Eröffnung

Im `strict`-Modus bei Qualitätsverstoß (offene kritische Funde) wird automatisch ein GitHub Issue eröffnet:

- Titel: „🚨 Sprach-Qualität: offene kritische Funde (Copy-Editing-Gate)“
- Inhalt: der aktuelle `COPY-EDITING-REPORT.md`
- Labels: `qualitaet`, `sprach-qualitaet`, `automatisiert`

Vor dem Issue legt der Schritt „Labels sicherstellen (C12)“ alle drei Labels
mit `gh label create … --force` an. Ein fehlendes Label lässt `gh issue`
mit HTTP 422 scheitern – dann gäbe es einen Qualitätsverstoß ohne Meldung
(#209).

## 7. Lokale Nutzung (ohne GitHub)

```bash
# Voller Highend-Lauf auf einem Artikel
python3 scripts/copy_editing_gate.py --file content/posts/<artikel>/index.md --report COPY-EDITING-REPORT.md

# Mit Auto-Fix (nur sichere Allowlist-Fixes)
python3 scripts/copy_editing_gate.py --file content/posts/<artikel>/index.md --fix --strict

# Selbsttest (Sabotage-Schutz vor jedem Deploy/Change)
python3 scripts/copy_editing_gate.py --selftest
```

## 8. Beziehung zu bestehenden Workflows

Die neue Pipeline **ersetzt nicht** die bestehenden Einzel-Workflows, sondern orchestriert sie auf Highend-Niveau:

| Bestehender Workflow | Rolle in der Highend-Pipeline |
|---|---|
| `.github/workflows/zeit-rechtschreibung.yml` | ZEIT-Niveau (Schritt 4 der Pipeline) |
| `.github/workflows/hemingway-check.yml` | Lesbarkeit (Schritt 7, über `readability_check`) |
| `.github/workflows/redaktions-politur.yml` | Offline-Glättung (manueller Notlauf, bleibt erhalten) |
| `.github/workflows/endredaktion.yml` | Finale menschliche Freigabe (nach der Pipeline) |

Die Einzel-Workflows bleiben als unabhängige, manuell startbare Wachen bestehen. Die Pipeline bündelt sie zu einem reproduzierbaren Highend-Prozess.

## 9. Voraussetzungen

- Python 3.11 (GitHub Actions: `setup-python`)
- `requirements-ci.txt` (gepinnt, `--require-hashes`, CLAUDE.md Regel A1)
- Keine externen API-Keys, keine Netzwerkdienste (100 % offline)

## 10. Änderungshistorie

- Highend-Rollout: Kombination aller sprachlichen Engines zu einer Pipeline, definierte Schwellen, automatische Issue-Eröffnung, Artefakt-Sicherung, versionierte History.
- 31.10.2026: Reparatur der fünf roten Vertragsverletzungen (Abschnitt 11).

## 11. Reparatur 31.10.2026 (Highend-Audit nach #977)

Der Workflow stand auf rot, obwohl die Engines grün waren – fünf unabhängige
Vertragsbrüche mit derselben Wurzel: **Eine Zusage ohne Beweis ist keine
Zusage.**

| Befund | Wirkung | Reparatur |
|---|---|---|
| `${{ inputs.* }}` in vier `run:`-Blöcken | Template-Injection-Risiko; Eingaben wurden ungeprüft in die Shell interpoliert | Eingaben nur über `env:` (`EINGABE_MODUS`, `EINGABE_SCOPE`, `EINGABE_DATEI`), Ausgaben über `$GITHUB_OUTPUT` |
| `... || true` und `echo $?` | `$?` las den Exit von `true` (immer 0) – der Strict-Modus konnte nie greifen | `set +e`, `RC=$?`, Bewertung in eigenem Schritt, unbekannte Codes = `sabotage` |
| `git push || true` bei `contents: read` | Push technisch unmöglich, Fehler verschluckt, History verfiel im Runner | `scripts/git_sync.sh --push-only` + `permissions: contents: write` |
| Issuelabels nie angelegt | HTTP 422 beim Melden (Klasse #209) | Schritt „Labels sicherstellen (C12)“ mit `--force` |
| `setup-python` v5.1.1 | repo-weit einheitlicher Pin verletzt | `5fda3b95…` (v7.0.0) |

Beweis statt Behauptung: `scripts/tests/test_workflow_push_rechte.py` prüft die
Rechte-Klasse für **alle** Workflows, die committen und pushen, sowie
Exit-Erfassung und Label-Reihenfolge in dieser Datei. Die Schalter- und
Beweisseite des Gates prüft
`scripts/tests/test_copy_editing_gate_schnittstelle.py`.
