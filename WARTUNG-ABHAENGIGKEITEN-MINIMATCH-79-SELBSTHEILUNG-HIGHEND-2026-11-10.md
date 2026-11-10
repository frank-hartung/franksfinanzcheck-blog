# Highend-Beweisbericht · Dependabot-Alert #79 (`minimatch`) & automatische Abhängigkeits-Selbstheilung

**Datum:** 10.11.2026  
**Vorgang:** Dependabot-Alert `#79` (`minimatch has potential denial of service via globparts amplification`, `GHSA-g3hv-75wg-m249` / `CVE-2026-118764`) + Begleitfund `glob@13.0.6` (`GHSA-3g3m-2fjr-6pw4`)  
**Zweig:** `arena/208badaa-franksfinanzcheck-blog`

---

## 1. Forensischer Ursachenbefund (warum `#79` auf `main` landen konnte)

1. **Eintrittsvektor (`90aa12b6`, PR `#1139`, 10.11.2026 17:14 UTC):**  
   Der Bump `lighthouse 13.5.0 -> 13.6.0` zog im Wurzel-`package-lock.json` transitiv `node_modules/@sentry/bundler-plugins@11.10.0` (`glob: ^13.0.6`) -> `glob@13.0.6` (`minimatch: ^10.2.2`) -> `minimatch@10.2.6` herein. Alle übrigen 12 `package*.json`-Dateien im Repository waren nicht betroffen.
2. **Systemlücke 1 — PR-Blindflug im Online-Audit:**  
   In `.github/workflows/sicherheits-wache.yml` lief `abhaengigkeits_wache.py --audit` ausschließlich bei `schedule || workflow_dispatch`. PR `#1139` passierte den Job `Abhängigkeiten (Pins offline · Audit online)` grün, ohne die neuen Lockfile-Versionen gegen die GitHub Advisory Database zu prüfen.
3. **Systemlücke 2 — Mehrzweig-Normalisierung & fehlender Offline-Boden (`A9`):**  
   `_normalisiere()` in `scripts/abhaengigkeits_wache.py` wählte bei mehrzweigigen GHSA-Einträgen den ersten Listeneintrag ohne Abgleich des Versionszweigs (Downgrade-Gefahr z. B. `3.1.3` statt `10.2.3`/`11.0.1`), und `pruefe_struktur()` kannte keine dauerhafte Sicherheits-Untergrenze (`A9`).
4. **Systemlücke 3 — Kein geschlossener Selbstheilungs-Regelkreis:**  
   Bei neu veröffentlichten Advisories fehlte ein H-02-konformer Heiler mit Eichprobe, `--ignore-scripts`-Zwang, Lieferketten-Prüfung, Nachmessung, verketteter SHA-256-Belegkette und automatischer PR-Bereitstellung.

---

## 2. Dauerhafte 5-Schichten-Architektur (Profi-Agentur-Standard)

| Schicht | Artefakt / Modul | Wirkung |
|---|---|---|
| **1 · SSOT-Vertrag & Regel `A9`** | `data/abhaengigkeits_schutz_vertrag.json` + `scripts/abhaengigkeits_wache.py` (`REGEL_UNTERGRENZE = "A9"`) | Verankert jede geheilte `first_patched_version` (`npm:minimatch >= 11.0.1`, `npm:glob >= 14.0.2`) sowie `package.json#overrides` dauerhaft für die deterministische Offline-Prüfung in `< 0,2 s`. |
| **2 · Eichprobe (Exit 3)** | `scripts/abhaengigkeits_selbstheilung.py` (`eichprobe()`) | Spielt Vorfall `#79`, Mehrzweig-Downgrade-Falle und fremden Tarball-Host vor jedem Urteil und Schreibzugriff im Speicher nach. Blindes Messgerät -> Exit 3 (`MESSGERAET`), null Schreibzugriffe. |
| **3 · Sichere Heilung & Nachmessung** | `scripts/abhaengigkeits_selbstheilung.py` (`--heilen`) | Streng aufsteigende Heilung (`--package-lock-only --ignore-scripts`, `overrides` bei Major-Sprüngen/sturen Eltern-Ranges, synchroner pip-Pin+Wheel-Hash-Lock), Lieferketten-Prüfung (`sha512`/`sha256` + `registry.npmjs.org` + `hasInstallScript`-Ausweis) und obligatorische Nachmessung mit atomarem Byte-Rollback bei Verschlechterung (Exit 2). |
| **4 · Verkettete SHA-256-Belegkette** | `data/abhaengigkeits_schutz_belege.jsonl` + `.gitattributes` (`merge=binary`) | Append-only Kette ab `GENESIS` (`seq=1`, `sha256=ce214c9fcca6b2c5…`). Idempotent bei sauberem Bestand (`SICHER` schreibt keine Uhrzeit-Commits). |
| **5 · PR-Eingangstor, Heil-Workflow & Alerting** | `.github/workflows/sicherheits-wache.yml`, `.github/workflows/abhaengigkeits-selbstheilung.yml`, `.github/workflows/alert-on-failure.yml` | PRs/Pushes mit Paket-/Workflow-Diff führen sofort den Online-Audit aus (`--audit-bedarf`). Täglich um 06:18 UTC sowie nach roter `Sicherheits-Wache` auf `main` erstellt der Heil-Workflow H-02-konform einen nachgemessenen Heilungs-PR (`automation/deps-heilung-*` via `scripts/git_sync.sh`). |

---

## 3. Live-Heilungs- und Prüfnachweise

| Prüfung | Ergebnis |
|---|---|
| Live-Heilung `abhaengigkeits_selbstheilung.py --heilen` | ✅ `GEHEILT` (Exit 0): Vormessung `338 geprüft · 2 Treffer` (`GHSA-g3hv-75wg-m249`, `GHSA-3g3m-2fjr-6pw4`) -> Nachmessung **`339 geprüft · 0 Treffer`**, `minimatch@11.0.6`, `glob@14.0.4`, `seq=1` |
| Zweitlauf `abhaengigkeits_selbstheilung.py --heilen` (Idempotenz) | ✅ `SICHER` (Exit 0), 0 geänderte Dateien, kein zusätzlicher Beleg-Eintrag |
| `abhaengigkeits_wache.py --selftest` & `--check` | ✅ 9 Strukturregeln (`A1`–`A9`), 0 Fehler, 0 Warnungen |
| `abhaengigkeits_selbstheilung.py --selftest` & `--wache` | ✅ Alle Sabotageproben & Verdrahtungs-Prüfungen grün |
| `manifest_guard.py --selftest` & Arbeitsbaum + `npm ci --ignore-scripts --dry-run` | ✅ 13 Dateien grün, `npm ci` trocken in 216 ms ohne Skriptausführung |
| `trigger_wache.py --check`, `workflow_vertrag_wache.py --gate`, `workflow_js_wache.py --check` | ✅ 103 Workflows, 0 Befunde |
| `integrity_guard.py --gate` | ✅ Alle 55 signierten Kerndateien unverändert intakt |
