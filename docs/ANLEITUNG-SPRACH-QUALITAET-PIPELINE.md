# Sprach-Qualitäts-Pipeline (GitHub Actions, Highend)

> **Datei:** `.github/workflows/sprach-qualitaet-pipeline.yml`
> **Rollout:** Highend · **Zeitplan:** täglich 04:30 UTC · **Manuell auslösbar** über Actions

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
| 1 | Offene kritische Funde (nur strict) | ⚠️ Workflow rot, Issue wird eröffnet |
| 2 | Selbsttest rot (Sabotage) | 🛑 Abbruch, keine Datei angefasst, kein Commit |

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

## 6. Automatische Issue-Eröffnung

Im `strict`-Modus bei Qualitätsverstoß (offene kritische Funde) wird automatisch ein GitHub Issue eröffnet:

- Titel: „🚨 Sprach-Qualität: offene kritische Funde (Copy-Editing-Gate)“
- Inhalt: der aktuelle `COPY-EDITING-REPORT.md`
- Labels: `qualitaet`, `sprach-qualitaet`, `automatisiert`

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
