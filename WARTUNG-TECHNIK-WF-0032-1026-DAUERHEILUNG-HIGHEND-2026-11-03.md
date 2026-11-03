# Dauerheilung WF-0032 (#1026) – Web-Vitals-Feldmessung (wöchentlich)

- **Vorgang:** `WF-0032` · GitHub-Issue `#1026` (`🔧 Wartung · Technik · Vorgang WF-0032`)
- **Auslösender Lauf:** `41456548199` (`run_number: 1`, `2026-11-02T13:51:05Z`, Branch `main` @ `375b1cc3`)
- **Workflow / Job:** `.github/workflows/web-vitals-woche.yml` · Job `Felddaten (CrUX) + Labor (Lighthouse)` (`125314557857`)
- **Datum der Dauerheilung:** `2026-11-03`

---

## 1. Forensischer Befund (Run `41456548199`)

Der erste planmäßige Wochenlauf starb in Schritt 5 (`Selbsttests der Messungen (ohne Netz)`) nach wenigen Millisekunden mit Exit `1`; die Schritte 6–12 sowie 14 wurden als `skipped` übersprungen:

```text
Error [ERR_MODULE_NOT_FOUND]: Cannot find package 'lighthouse'
imported from .../scripts/lighthouse_live.mjs
```

Die Tiefenprüfung des gesamten Kanals (`web-vitals-woche.yml`, `lighthouse_live.mjs`, `cwv_feld_wache.py`, `alert-on-failure.yml`, `publication-reliability-tests.yml`) legte **elf zusammenhängende Ursachen und latente Folgefehler** frei:

| # | Schicht | Befund vor der Heilung | Dauerhafte Lösung |
|---|---|---|---|
| 1 | `scripts/lighthouse_live.mjs` | Statische Top-Level-Imports auf `'lighthouse'`, `'playwright-core'` und `'../e2e/browser.mjs'` (importiert ebenfalls statisch `'playwright-core'`) verhinderten jeden Import ohne `node_modules`. | Top-Level ausschließlich Node-Bordmittel (`node:fs`, `node:path`, `node:url`); Laufzeitpakete werden erst beim Live-Lauf über `ladeLaufzeit()` dynamisch geladen. |
| 2 | `scripts/lighthouse_live.mjs` | Kein eigener `--selftest`-Modus analog zu den Python-Wachen. | Deterministischer Offline-Selbsttest (`--selftest`) ohne Netz, ohne Browser, ohne `node_modules` und ohne Dateischreiben. |
| 3 | `scripts/lighthouse_live.mjs` | Leere Schwellen (`assertions: {}`) oder leere Ziellisten lieferten Scheingrün; fehlende CLI-Optionswerte (`--url` ohne Wert) warfen `TypeError`; Fremdschemata (`file://`, `javascript:`) wurden nicht abgewiesen. | Harte Scheingrün-Sperren in `ladeAssertions()`, `pruefeAssertions()` und `zieleAusDatei()`, strikte CLI-Wert- und `http(s)`-Prüfung in `argumente()`, injizierbare Messfunktion in `messeUrl()`. |
| 4 | `scripts/lighthouse_live.mjs` | Im `--json`-Modus schrieb `haupt()` Fortschrittszeilen (`Labor (1 Läufe/Seite): …`) auf `stdout` vor das JSON-Dokument, sodass nachgelagerte `JSON.parse()`-Aufrufer scheiterten. | Im `--json`-Modus geht Fortschritt auf `stderr`; `stdout` enthält ausschließlich reines, direkt parsbare JSON (live verifiziert gegen Chromium 153 + Lighthouse 13). |
| 5 | `.github/workflows/web-vitals-woche.yml` | `node --test` lief **vor** `actions/setup-node` auf einer ungepinnten Runner-Node-Version. | `Node einrichten` (Node 22, gepinnt auf Commit-SHA) steht vor jedem Node-Aufruf; `cache: npm` füllt nur `~/.npm`, legt kein `node_modules` an. |
| 6 | `.github/workflows/web-vitals-woche.yml` | Der Selbsttest des unverbindlichen Diagnose-Werkzeugs (`lighthouse_live`) lief vor der verbindlichen CrUX-Feldmessung und konnte diese komplett überspringen. | Strikte Pfadtrennung: erst `Selbsttest der Feldmessung` + `Felddaten messen` + `Feldbericht`, danach `Selbsttest der Labormessung` (`test ! -d node_modules`) + `npm ci` + `Chromium` + `Laborwerte messen`. |
| 7 | `.github/workflows/web-vitals-woche.yml` | `continue-on-error: true` + `set -uo pipefail` unter GitHubs Standard-Shell `bash -eo pipefail`: `-e` blieb aktiv, sodass Nicht-Null-Exits (`1`/`2`) vor `echo "exit=$?" >> "$GITHUB_OUTPUT"` und vor `cat *-bericht.md` abbrachen (`Exit '—'`). | `continue-on-error` entfernt; explizites `rc=0; ... || rc=$?` unter `set -euo pipefail` schreibt immer `exit` und `grund` in `$GITHUB_OUTPUT`, gibt Bericht + Stderr aus und speichert `feld-fehler.txt` im Artefakt. |
| 8 | `scripts/cwv_feld_wache.py` | Kein Retry/Backoff bei transienten PSI-Antworten (`429`/`5xx`/Timeout); `HTTPError` verlor den Statuscode, trug aber in `exc.url` `&key=<PSI_API_KEY>`; kein Unterschied zwischen „API tot" und „0 Seiten mit CrUX-Daten". | Begrenzter Backoff in `hole()` (`408`/`429`/`500`/`502`/`503`/`504`, `Retry-After` bis `30s`, sofortiger Abbruch bei `400`/`401`/`403`/`404`), Ziel-Taktung (`1.5s`), `schwaerze_geheimnis()` + `klassifiziere_stoerung()` und `stoerung_grund` (`keine_crux_daten` vs. `teilabruf_fehlgeschlagen` / `abruf_fehlgeschlagen`). |
| 9 | PR-CI (`publication-reliability-tests.yml`) | Kein PR-Gate führte `lighthouse_live.mjs --selftest` oder `lighthouse_live.test.mjs` ohne `node_modules` aus. | `scripts/tests/test_web_vitals_workflow.py` führt beide Aufrufe in einem nackten `TemporaryDirectory` ohne `node_modules` sowie die echten Workflow-Shell-Blöcke unter `bash -eo pipefail` aus (auch unter `+97` Tagen Uhr-Versatz); zusätzlich direkter Lauf in `publication-reliability-tests.yml`. |
| 10 | Trigger-Abdeckung (`publication-reliability-tests.yml`) | Änderungen an `data/cwv/**`, `lighthouse/**`, `e2e/**` oder `package*.json` allein lösten die PR-Regressionssuite nicht aus. | Pfade in `pull_request.paths` von `publication-reliability-tests.yml` aufgenommen. |
| 11 | Zentrales Alerting (`alert-on-failure.yml`) | `Web-Vitals-Feldmessung (wöchentlich)` hatte keine eigenen Fachklassen; Nicht-Selbsttest-Ausfälle wären in `allgemein` („API-Key abgelaufen (GROQ/GEMINI)") gelandet. | Zwei eigene Klassen (`web-vitals-befund`, `web-vitals-stoerung`) ergänzt, `selbsttest`-Rat um Node-Selbsttests/`npm run test:webvitals` erweitert, Verhaltenssimulation für alle `WF-0032`-Fälle inkl. Nachführung von `#1026` ergänzt. |

---

## 2. Vertragstreue: Auto-Close (`#1026`) & Hausregel C2 (CrUX)

1. **Job-Beweis für `#1026` (`scripts/alert_resolve_gate.py`):**
   Issue `#1026` trägt den Marker `<!-- alert-jobs: ["Felddaten (CrUX) + Labor (Lighthouse)"] -->`. Workflow-Name (`Web-Vitals-Feldmessung (wöchentlich)`) und Job-Anzeigename (`Felddaten (CrUX) + Labor (Lighthouse)`) bleiben exakt erhalten; `test_web_vitals_workflow.py` prüft `alert_resolve_gate.entscheiden()` direkt gegen den Marker von `#1026`.
2. **Kein Scheingrün bei fehlenden CrUX-Daten (C2):**
   Antwortet PageSpeed Insights für alle Ziele ohne 28-Tage-CrUX-Daten (`UNGEPRUEFT`), bleibt das Urteil vertragstreu `STOERUNG` (`Exit 2`) – niemals ein erfundenes Grün. Gleichzeitig benennen Bericht, JSON (`"stoerung_grund": "keine_crux_daten"`), Workflow-Annotation und Alerting-Runbook (`web-vitals-stoerung`) unmissverständlich, dass die API erreichbar ist und lediglich das Besucheraufkommen noch unter Googles CrUX-Schwelle liegt.

---

## 3. Nachweis & Prüfprotokoll

Alle Nachweise liefen lokal reproduzierbar grün:

- Paketfreie Vorab-Probe (vor `npm ci`, ohne `node_modules`) & Live-Chromium-Probe:
  - `node scripts/lighthouse_live.mjs --selftest` → Exit `0`
  - `node --test scripts/tests/lighthouse_live.test.mjs` → `18/18` grün
  - Live-Lauf gegen Chromium 153 + Lighthouse 13 (`--json`) → Exit `0`, reines JSON auf `stdout`
- Web-Vitals-Gesamtnachweis (`npm run test:webvitals`):
  - `cwv_feld_wache.py --selftest`, `lighthouse_live.mjs --selftest`, `lighthouse_live.test.mjs` (`18/18`), `test_cwv_feld_wache` (`24/24`), `test_web_vitals_workflow` (`6/6`) → grün
- Uhr-Probe (`+97` Tage) & KI-/Netz-Probe:
  - `selftest_clock.py --trap scripts/cwv_feld_wache.py --offset 97` → grün
  - `selftest_clock.py --trap-modul scripts.tests.test_cwv_feld_wache --offset 97` → grün
  - `selftest_clock.py --trap-modul scripts.tests.test_web_vitals_workflow --offset 97` → grün
  - `selftest_ki.py --trap scripts/cwv_feld_wache.py` → grün
- Hausweite Wachen & Verträge:
  - `unittest scripts.tests.test_alert_scoping` (`32/32` inkl. Node-Verhaltenssimulation aller Runbooks & Markenflächen-Prüfung) → grün
  - `integrity_guard.py --check`, `manifest_guard.py`, `trigger_wache.py --check`, `actions_version_guard.py`, `workflow_vertrag_wache.py --gate`, `automation_premium_audit.py --strict`, `workflow_js_wache.py --check`, `skript_syntax_wache.py --check`, `wachen_vertrag.py`, `skills_vertrag.py`, `report_hygiene.py --check`, `brand_surface_guard.py`, `governance_contract.py --quick` → sämtlich grün
