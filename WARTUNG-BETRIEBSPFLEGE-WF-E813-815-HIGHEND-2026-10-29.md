# Wartung · Betriebspflege · WF-E813 (#815) — Stufe 5: Produktionsfreigabe beweisen, bevor Secrets fließen

**Auftrag:** `Wartung · Betriebspflege · Vorgang WF-E813 #815 Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben.`

**Datum:** 29.10.2026 · **Branch:** `arena/8d7842b6-franksfinanzcheck-blog` · **Basis:** `2e4c7ae` (`main`)
**Vorgänger:** Stufen 1–4 vom 24.–27.10.2026 (`WARTUNG-BETRIEBSPFLEGE-WF-E813-815-HIGHEND-2026-10-24.md`, `…-2026-10-26.md`, `…-2026-10-27.md`)

---

## 1. Forensischer Befund

### 1.1 Der Live-Vorgang bleibt tatsächlich rot

Der aktuelle Beleg in #815 ist Sicherheits-Wache, Run **`40688195171`** (28.10.2026, 12:29 UTC, `schedule`, Commit `ff14b6b4`):

- **F-01 — BEFUND:** Auf `/` und `/methodik/` fehlen die fünf vorgeschriebenen Antwort-Header (10 konkrete Annotationen). Die Live-Wache misst; sie meldet keinen Netzfehler.
- **Worker — STOERUNG:** `/healthz` bestätigt keinen `bau`-Buildstempel; das authentifizierte Bild ist unvollständig (`budget`, `turnstile`, `schluesselrollen`, `exporte`). Der erwartete Repo-Stempel ist `ff-newsletter-2026-10-24`, aber der Live-Stand weist ihn nicht nach.
- **Gesamturteil:** `header: BEFUND, worker: STOERUNG – kein vollständiger Live-Nachweis.` Ein Offline-Grün kann #815 weiterhin nicht schließen.

### 1.2 Die Deploy-Ursache ist belegt, nicht mehr geraten

Worker-Deploy **`40569123622`** (27.10.2026, 19:26 UTC, Push auf `main`) plante `newsletter-worker` und `klick-zaehler` korrekt ein. Beide Deploy-Jobs brachen vor Wrangler im Schritt „Produktive Ressource auflösen“ fail-closed ab. Die Annotation belegt: **`CF_WORKERS_DEPLOY_TOKEN` fehlt im Environment `cloudflare-produktion`**. Der Worker kann daher nicht den im Repo erwarteten Buildstempel ausliefern.

### 1.3 Zusätzlich entdeckte GitHub-Environment-Drift

Ein read-only-Aufruf der GitHub-Environment-Metadaten zeigt für `cloudflare-produktion`:

- `protection_rules: []` — kein Required Reviewer nachgewiesen;
- `deployment_branch_policy: null` — keine Beschränkung auf `main` nachgewiesen;
- `can_admins_bypass: true` — Administrator-Bypass nicht gesperrt.

Das widerspricht der bisherigen Annahme in Runbook und Workflow-Kommentar, das Environment sei bereits freigabepflichtig und nur für `main` zugelassen. GitHub kann ein in YAML referenziertes Environment beim ersten Zugriff ohne Schutzregeln anlegen. **`environment: cloudflare-produktion` allein ist keine Zugriffsschranke.**

---

## 2. Dauerhafte technische Heilung in dieser Stufe

### H-A — Read-only-Policy-Wache: `scripts/worker_environment_guard.py`

Vor einem produktiven Deploy werden jetzt drei Eigenschaften des *tatsächlich konfigurierten* GitHub-Environments geprüft:

1. Mindestens ein gültiger User-/Team-Reviewer ist als Required Reviewer eingetragen.
2. Die paginierte Branch-Policy erlaubt **genau** `main` vom Typ `branch` — keine Tags, Wildcards oder zusätzlichen Branches.
3. `can_admins_bypass` ist ausdrücklich `false`.

Die Wache ist read-only, folgt keinen fremden Redirects, liest keine Secret-Werte und gibt keine API-Rohantworten aus. Nicht prüfbar zählt als nicht nachgewiesen und blockiert den Deploy. Selbsttest und 17 Unit-Tests decken sichere Konfiguration, fehlende/mehrdeutige Regeln, Pagination samt `total_count`-Vollständigkeit, fremde Link-Ziele, API-Ausfall und Secret-Hygiene ab.

### H-B — Secret-freie Vorprüfung vor dem Environment-Deploy

`.github/workflows/worker-deploy.yml` hat einen separaten Job `production-policy` vor dem Deploy-Job:

- besitzt **kein** `environment:` und erhält **keine Cloudflare-Secrets**;
- hat nur `actions: read` und `contents: read`;
- prüft die GitHub-Policy, bevor der Secret-tragende `deploy`-Job freigegeben wird;
- der Deploy-Job hat zusätzlich eine Job-Bedingung auf `refs/heads/main`.

Manuelle Deploys werden schon im zugangslosen Planungsjob auf `refs/heads/main` beschränkt. So fordern nicht-main Läufe das Produktions-Environment nicht versehentlich an.

### H-C — Alarmierung und Runbook an die echte Ursache angepasst

Der Alert-Kanal für „Cloudflare-Worker deployen“ erkennt jetzt sowohl eine unsichere/unlesbare Environment-Policy als auch fehlende Cloudflare-Zugänge als dieselbe gezielte Einrichtungs-Klasse. Der Rat unterscheidet zuerst Policy (Reviewer, exakt `main`, kein Admin-Bypass) und danach Deploy-Zugang (`CF_WORKERS_DEPLOY_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, bestehende Bindungen). Die Verhaltenssimulation prüft beide Wege.

Runbook A4/D2 und `cloudflare/edge-schutz.md` nennen jetzt den realen GitHub-Policy-Vertrag. Der Backup-Environment-Eintrag wurde außerdem auf „kein Required Reviewer“ präzisiert, weil nächtliche, unbeaufsichtigte Backup-Läufe andernfalls auf eine manuelle Freigabe warten würden.

---

## 3. Verifikation

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/worker_environment_guard.py --selftest` | ✅ sichere Policy akzeptiert; 7 unsichere/unklare Zustände fail-closed erkannt |
| `python3 -m unittest scripts.tests.test_worker_environment_guard -v` | ✅ **17/17** |
| `python3 scripts/worker_deploy_vorbereiten.py --selftest` + `test_worker_deploy_vorbereiten` | ✅ **14/14**; manueller Nicht-`main`-Lauf scheitert vor dem Environment |
| `test_worker_ressourcen` | ✅ **23/23** |
| `test_alert_scoping.VerhaltensSimulation.test_kern_szenarien` | ✅ **62 Szenarien**, einschließlich neuer Environment-Policy-Triage |
| `PYTHONPATH=/tmp/arena-pyyaml npm run test:sicherheit` (PyYAML 6.0.3, nur temporär installiert) | ✅ **225 Sicherheits-Tests + 33 Abhängigkeits-Tests** bestanden. ⚠ Der separate vollständige Abhängigkeits-API-Audit blieb mangels `GITHUB_TOKEN`/`GH_TOKEN` ausdrücklich **ungeprüft**; daraus wird keine Aussage „Abhängigkeiten sauber“ abgeleitet. |
| `ki_transportweg.py --selftest` + `test_ki_transportweg` | ✅ T6-Ausnahme eng begrenzt; **36/36** Tests |
| YAML-Parserprüfung (`worker-deploy`, `sicherheits-wache`, `alert-on-failure`) | ✅ alle drei Dateien valide; Policy-Job secret-frei und vor Deploy verdrahtet |
| `py_compile`, `package.json`, `git diff --check` | ✅ fehlerfrei |

**Separater, nicht WF-E813-bedingter Bestandshinweis:** `scripts.tests.test_wachen_vertrag` läuft bis auf den vorhandenen Test `test_selbsttest_der_redaktions_wache_laeuft`; auch der direkte Aufruf `python3 scripts/redaktions_standard.py --selftest` scheitert aktuell mit `Vertrag-gute-aenderung-still: False, erwartet True`. An dieser fachfremden Redaktions-Wache wurde in dieser Stufe nichts geändert.

---

## 4. Grenze der Behebung — #815 bleibt ehrlich offen

Der Code kann weder GitHub-Environment-Secrets setzen noch Cloudflare DNS/Transform Rules ohne einen produktiven Token ändern. Daher wurde **kein** produktiver Deploy oder Edge-Schreibzugriff versucht und #815 nicht manuell geschlossen. Nach dieser Stufe wird das aktuelle Environment den Deploy nun ausdrücklich blockieren, bis sein Schutz nachgewiesen ist — statt die im Runbook versprochene Freigabe nur anzunehmen.

### Inhaber-Schritte zum echten Live-Abschluss

1. **GitHub → Settings → Environments → `cloudflare-produktion`:** mindestens einen Required Reviewer hinzufügen; Deployment branches and tags → Selected → ausschließlich `main`; Administrator-Bypass deaktivieren. Das neue Gate prüft genau diese Policy vor Secrets.
2. **Secrets im selben Environment** sicher hinterlegen: `CF_WORKERS_DEPLOY_TOKEN` mit Workers Scripts: Read + Deploy sowie `CLOUDFLARE_ACCOUNT_ID`. Werte nicht in Issues, Reports oder Chat schreiben.
3. **Deploy auf `main` ausführen/freigeben:** Actions → „Cloudflare-Worker deployen“ → `newsletter-worker`. Der Lauf muss den echten Deploy und den `/healthz`-Nachweis `bau == ff-newsletter-2026-10-24` zeigen.
4. **Edge A1 + Datenschutz B7 herstellen:** mit dem dafür berechtigten Cloudflare-Zonentoken `npm run edge:freigabe:apply`, danach `npm run edge:b7:apply`; B7-Änderung auf `main` übernehmen.
5. **Sicherheits-Wache live starten:** `gh workflow run sicherheits-wache.yml --ref main`. Nur F-01 vollständig OK, authentifiziert vollständiger Worker-Status und ein vollständiger Abschlussnachweis schließen #815 automatisch.

**Status am 29.10.2026:** #815 ist weiterhin offen. Nach Umsetzung der Inhaber-Schritte muss der neue Policy-Guard grün sein, bevor Cloudflare-Zugangsdaten in einem Deploy-Job verwendet werden.
