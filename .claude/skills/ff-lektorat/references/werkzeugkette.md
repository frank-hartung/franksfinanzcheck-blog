# Werkzeugkette & Prozesse – Copy Editing Highend

> **Hausgemacht, nicht übernommen** – deutschsprachige Ausgabe des Hauses,
> bis 01.11.2026 im Fremd-Ordner `copy-editing` (dort `references/werkzeugkette-de.md`), seither hier.
> Kein Upstream-Text: wer sie ändert, ändert Hausregeln.

Diese Skill orchestriert die bereits installierte Offline-Engine-Kette des Repos in einem festen, wiederholbaren Highend-Prozess. Keine Engine wird ersetzt – sie werden in der richtigen Reihenfolge mit definierten Schwellen und Rückschleifen betrieben.

## Die Engine-Kette (SSOT)

| Schritt | Skript | Modus | Exit-Code bei Rot |
|---|---|---|---|
| 1 | `scripts/grammar_check.py --selftest` | Sabotage-Schutz (offline) | 2 |
| 2 | `scripts/grammar_check.py` | Grammatik LT1–LT4 | 1 (--strict) |
| 3 | `scripts/hardcases_guard.py --selftest` | Sabotage-Schutz | 2 |
| 4 | `scripts/hardcases_guard.py` | Fest-Fehler H1–H9 | 1 (--strict) |
| 5 | `scripts/zeit_rechtschreibung.py --selftest` | Sabotage-Schutz | 2 |
| 6 | `scripts/zeit_rechtschreibung.py` | ZEIT-Niveau Rechtschreibung | 1 (--strict) |
| 7 | `scripts/sprachglatt.py --selftest` | Sabotage-Schutz | 2 |
| 8 | `scripts/sprachglatt.py` | Glättung DW1–DW9 + V1 | 1 (--strict) |
| 9 | `scripts/lektor_guard.py` | Verlags-Lektorat L1–L12 | 1 (--strict) |
| 10 | `scripts/readability_check.py --new-only` | Lesbarkeit Flesch-Amstad | 1 (--strict) |

## Prozessablauf (Pro Artikel)

```
1. Selbsttests aller Engines laufen (Sabotage-Schutz)
   └─ Rot (Exit 2) → Abbruch, keine Datei wird angefasst
2. grammar_check → hardcases_guard → zeit_rechtschreibung
   └─ Auto-Fix nur bei harter Allowlist (einmaliger, unzweideutiger Ersatz)
   └─ Grauzonen → Report, nie blinder Auto-Fix
3. sprachglatt → lektor_guard
   └─ DW1–DW9 Auto-Fix (sichere Glättfälle)
   └─ V1/L1–L12 Vorschläge → menschliche Entscheidung
4. readability_check
   └─ Flesch-Amstad ≥ 60 (neue Artikel), Ø ≥ 62 (Bestand)
   └─ Ø Satz ≤ 16 Wörter, lange Wörter < 15 %, Schachtelsätze < 10 %
5. Menschliche Endredaktion (Seven Sweeps + AI-Tell-Check + YMYL-Panel)
   └─ scripts/endredaktion.py für finale Prüfung + Freigabe
6. Report + History-Commit (versioniert, dedupliziert)
```

## Reports & History (versioniert)

| Datei | Inhalt |
|---|---|
| `GRAMMATIK-REPORT.md` + `.grammar_report.json` | LT1–LT4 Funde + geheilt |
| `HARDCASES-REPORT.md` + `data/hardcases_history.jsonl` | H1–H9 Fest-Fehler |
| `ZEIT-RECHTSCHREIBUNG-REPORT.md` + `data/zeit_rechtschreibung_history.jsonl` | ZEIT-Niveau |
| `SPRACHGLATT-REPORT.md` + `data/sprachglatt_history.jsonl` | DW1–DW9 + V1 |
| `LEKTOR-REPORT.md` + `data/lektor_history.jsonl` | L1–L12 Verlags-Lektorat |
| `HEMINGWAY-REPORT.md` / `LESBARKEIT-REPORT.md` | Lesbarkeit |

Alle Reports sind `gitignored` (bleiben im Lauf-Log), die History-Files werden versioniert und dedupliziert (Quoten-Schutz, kein Doppel-Commit am selben Tag).

## Schwellen (Highend-Profi-Agentur)

| Kennzahl | Schwelle neu | Schwelle Bestand | Quelle |
|---|---|---|---|
| Flesch-Amstad | ≥ 60 | ≥ 62 (Ø), Floor ≥ 55 | readability_check |
| Ø Satzlänge | ≤ 16 Wörter | ≤ 16 Wörter | readability_check |
| Lange Wörter (>12 Buchst.) | < 15 % | < 15 % | readability_check |
| Schachtelsätze (>25 Wörter) | < 10 % | < 10 % | readability_check |
| Absätze > 4 Sätze | 0 | 0 | readability_check |
| Passiv-Anteil | niedrig | niedrig | stil_guard / readability |
| Offene Grammatik-Funde (LT1–LT4) | 0 | 0 | grammar_check --strict |
| Offene Fest-Fehler (H1–H9) | 0 | 0 | hardcases_guard --strict |
