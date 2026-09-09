# Reparatur #233 – Wöchentliche SEO-Optimierung

**Datum:** 2026-09-09  
**Workflow:** `Wöchentliche SEO-Optimierung` / `.github/workflows/seo-weekly.yml`  
**Befund:** Der Lauf #23 / Issue #233 brach im Schritt **„Textverständnis-Report und -Fixes committen“** ab. Der typische Auslöser in diesem Repository ist ein langer SEO-Lauf auf einem älteren `main`-Stand, während andere Automationen parallel generierte Reports, Statusdateien oder JSONL-Historien fortschreiben. Beim anschließenden Rebase/Push entsteht dann ein technisch lösbarer Bot-Artefakt-Konflikt und der Workflow wird rot.

## Dauerhafte Härtung

1. **`scripts/git_sync.sh` erweitert**
   - erkennt Rebase-Konflikte in rein generierten Bot-Artefakten,
   - vereinigt append-only `*.jsonl`-Historien dedupliziert,
   - übernimmt bei generierten Reports/Statusdateien deterministisch den gerade erzeugten Bot-Stand,
   - bricht weiterhin hart ab, sobald echte Content-Dateien betroffen sind.

2. **Push-Retry gehärtet**
   - auch Retry-Rebases nutzen jetzt dieselbe Konflikt-Selbstheilung statt still abzubrechen.

3. **JSONL-Merge-Regel eingeführt**
   - `.gitattributes`: `*.jsonl merge=union` verhindert Standard-Konflikte bei parallelen append-only Historien.

4. **SEO-Workflow stabilisiert**
   - Checkout läuft mit `fetch-depth: 0`, damit Rebase/Diagnose auf vollständiger Historie arbeitet.
   - Ein fehlerhaft eingerücktes `exit ${PIPESTATUS[0]}` im Meta-Schritt wurde korrigiert.

## Sicherheitsprinzip

Die Reparatur löst nur maschinell erzeugte Artefakte automatisch. Artikel-/Content-Konflikte werden nicht blind gemergt, sondern bleiben echte Stopps. Damit ist der Workflow robuster, ohne redaktionelle Qualität zu riskieren.

## Validierung

- `bash -n scripts/git_sync.sh`
- synthetischer Rebase-Konflikt-Test mit Report- und JSONL-Datei: erfolgreich automatisch gelöst und gepusht
- YAML-Parse von `.github/workflows/seo-weekly.yml`: erfolgreich
