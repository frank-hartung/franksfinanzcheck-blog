# Wartung · Veröffentlichung · Vorgang WF-829B (#922) — Dauerheilung am 10.11.2026

**Vorgang:** WF-829B · **Issue:** [#922](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/922) (weiterhin **OFFEN**, zuletzt nachgeführt 10.11.2026, 17:14:50 UTC)
**Jüngster roter Lauf:** [42862649288](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/42862649288) · 10.11.2026, 17:13:05 UTC (18:13 Uhr Ortszeit) · `production-policy → failure`, `deploy → skipped`
**Auftrag:** „Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben."
**Messzeit:** 10.11.2026, 17:18–17:35 UTC · alle Zahlen am echten Baum, am echten Environment, am echten Artefakt und an der echten GitHub-API gemessen
**Vorberichte:** `…-2026-10-29.md` · `…-2026-10-30.md` · `…-2026-11-01.md` · `…-2026-11-03.md` · `…-SIEGEL-DAUERHEILUNG-2026-11-04.md` · `…-SELBSTHEILUNG-HIGHEND-2026-11-07.md`

---

## 1. Kurzfassung: sechs Berichte haben den richtigen Befund gemeldet und die falsche Stelle repariert

Der Vorgang ist **kein Ausfall**. Das fail-closed-Gate arbeitet seit dem 25.10.2026 korrekt: Das Environment `cloudflare-produktion` ist ungesichert, also bricht der Deploy ab, **bevor** ein Cloudflare-Secret gelesen wird. Genau das war nach dem Vorfall vom 24.10.2026 (Run 40100342025 – übersprungener Deploy, grüner Lauf) gewollt.

Was die sechs Vorberichte übersehen haben, ist die **Auslöser-Logik**: `.github/workflows/worker-deploy.yml` behandelte **jeden `push` nach `main` auf einen Worker-Pfad als Produktions-Deploy-Versuch** – auch jeden Dependabot-Bump an `tools/wrangler/**`. Bei einem Environment, das das Repository nachweislich nicht selbst absichern kann, ist jeder dieser Läufe **garantiert rot**. Seit dem 27.10. sind es acht rote Läufe, bei jedem wurde #922 nachgeführt. Das Runbook A4 sagt an derselben Stelle das Gegenteil: deployt wird, wenn ein Mensch *Run workflow* drückt.

Die zweite, teurere Beobachtung: Der am 07.11. eingeführte „Selbstheilungs"-Workflow ist seitdem **siebenmal mit `success`** gelaufen, davon **viermal mit ausgeführtem Live-Heiljob** (08.11., 09.11., 10.11. 13:47 schedule, 10.11. 17:14 workflow_run) – und `updated_at` des Environments steht weiter auf dem 25.10. Ein grüner Heil-Lauf, der nichts heilt, ist die gleiche Klasse wie #809: ein „Behoben" ohne den Job, der rot war. Der Grund ist kein Codefehler, sondern eine **Rechtegrenze**, die heute erstmals mit dem Antwortkopf belegt wurde (Abschnitt 2).

> Die Dauerheilung dieses Vorgangs besteht nicht aus einem siebten Heiler, sondern aus drei Dingen: den unmöglichen Automatismus abschaffen, den Schutz am **Verhalten** statt an einer Stellvertreter-Einstellung beweisen und den verbleibenden Inhaber-Schritt sichtbar machen, statt ihn grün zu übermalen.

| Nr | Befund (live gemessen) | Heilung | Stand |
|---|---|---|---|
| **A** | `push` löst Produktions-Deploys aus, die garantiert fail-closed rot werden; 8 rote Läufe seit Eröffnung der Meldung, 8× #922 nachgeführt | Deploy nur `workflow_dispatch`; Push/PR nur geheimnisfreie Worker-Tests; `abschluss` beweist die Trennung | **geheilt**, 16 Gegenproben + 18 Vertragstests |
| **B** | Schutz wurde nur als Stellvertreter (Environment-Einstellung) geprüft; ein stiller Skip war indirekt erschlossen | **Verhaltensbeweis** über `needs.*.result`: geplanter Deploy muss `success` sein, Push/PR darf nie deployen | **geheilt**, mit Gegenprobe belegt |
| **C** | Heil-Lauf meldet `success` bei unverändertem Environment (4× live) | **Ampel am Commit**: `action_required` bei `OFFEN`, `success` nur bei Nachmessung `SICHER/GEHEILT`, `failure` bei ungeprüft | **geheilt**, 4 Zustände am echten `run:`-Block nachgefahren |
| **D** | Rechtegrenze wurde behauptet, nicht gemessen | Live-`PUT` → **403** mit `X-Accepted-Github-Permissions: administration=write`; GraphQL-Introspection `UpdateEnvironmentInput` ohne Bypass-Feld | **belegt**, Abschnitt 2 |
| **E** | Trigger, Verdrahtung und Security-Gates konnten still driften | Wachen am echten Workflow-Text; 102 Workflows V1–V7, 102 Trigger, 396 Skripte, 691 Syntaxdateien, 283 Selbsttests | **geprüft**, Abschnitt 5 |
| **F** | Environment `cloudflare-produktion` seit 25.10. ungesichert; kein Admin-Schreibrecht | **Inhaber-Aufgabe**, auf drei exakte Handgriffe verdichtet; Tageslauf übernimmt, sobald das Recht steht | **offen**, Abschnitt 6 |

**#922 ist nicht geschlossen und wurde nicht von Hand kommentiert** (D2). Der Schließpfad bleibt der grüne Job, der rot war (`alert_resolve_gate.py`). Nichts wurde gelockert, um Grün zu erzeugen.

---

## 2. Forensik: Bytes, Köpfe und Läufe statt Zitate

### 2.1 Das Environment, heute live gelesen

```json
{"id": 25274969424, "name": "cloudflare-produktion",
 "created_at": "2026-10-25T13:20:15Z", "updated_at": "2026-10-25T13:20:15Z",
 "can_admins_bypass": true, "protection_rules": [], "deployment_branch_policy": null}
```

`created_at == updated_at`: seit der automatischen Anlage am 25.10. ist dieses Objekt **nie** konfiguriert worden – auch nicht von den fünf grünen Heil-Läufen.

### 2.2 Die Rechtegrenze, heute erstmals mit Antwortkopf gemessen

```text
PUT /repos/frank-hartung/franksfinanzcheck-blog/environments/cloudflare-produktion
→ HTTP/2.0 403 Forbidden
  X-Accepted-Github-Permissions: administration=write
  X-Github-Request-Id: BB24:0E41:36210:5E6D8:6AF35272
  {"message":"Resource not accessible by integration"}
```

Der Schreibversuch war ausschließlich verschärfend (`{"can_admins_bypass": false}`), hat nichts verändert – die Nachmessung liefert weiter `can_admins_bypass: true`, `updated_at` 25.10. Ergänzend, lesend gegen die echte GraphQL-Schema-Introspection:

```text
UpdateEnvironmentInput → clientMutationId, environmentId, waitTimer,
                         reviewers, preventSelfReview
```

Kein Bypass-Feld; `CreateEnvironmentInput` kennt nur `repositoryId` und `name`. Die REST-Körpersperre (`additionalProperties: false`) ist in A4/A4b dokumentiert und wird vom Einrichter-Selbsttest (Fall 6: „kein `can_admins_bypass` im Schreibkörper") bewacht; ein erneuter REST-Schreibtest war wegen desselben 403 nicht möglich und wird hier **nicht** als neue Messung ausgegeben. Die Aussage lautet deshalb bewusst eng: **Dieses Repository kann mit seinem heutigen Token und keiner verfügbaren GitHub-Schreib-API den Zielzustand herstellen.** Alles andere wäre eine Behauptung.

### 2.3 Die Kette, die jeden Morgen von vorn begann

```text
push (auch Dependabot an tools/wrangler/**)
  → „Cloudflare-Worker deployen" startet
  → plan: 1 Worker
  → production-policy: worker_environment_guard.py --check → Exit 1 (3 Befunde)
  → deploy: skipped
  → Fehler-Alerting aktualisiert #922 mit dem neuen Lauf
  → workflow_run startet „Produktions-Schutz · Selbstheilung" → success (OFFEN, Warnstufe)
  → Environment: unverändert
```

Acht rote Deploy-Läufe seit Eröffnung der Meldung am 27.10. (40569123622, 40308260271, 40855503441, 40857308513, 41056313716, 41417750214, 42074601435, 42862649288); insgesamt neun seit dem 25.10. Sieben grüne Läufe des Heil-Workflows (42362691341, 42362956168, 42375156727, 42479296822, 42634439151, 42827831087, 42862890380), davon vier mit ausgeführtem Live-Heiljob – die drei übrigen waren Offline-/PR-Läufe ohne Heiljob. Die Belegkette `data/produktions_schutz_belege.jsonl` enthält zwei ehrliche Einträge mit `vorher == nachher` – das ist der Beweis, dass ein 403 nie als Heilung gebucht wurde. Der Fehler lag **nicht** im Heiler, sondern davor: Es gab gar keinen Anlass, einen Deploy zu versuchen.

---

## 3. Die Heilung — drei Schichten, je mit eigenem Beweis

### S1 · Trigger-Vertrag (`.github/workflows/worker-deploy.yml`)

| Ereignis | Jobs | Geheimnisse |
|---|---|---|
| `workflow_dispatch` auf `refs/heads/main` | `plan` → `production-policy` → `deploy` → `abschluss` | Environment + Cloudflare-Secrets erst **nach** dem Gate |
| `push` / `pull_request` | nur `tests` (alle drei Worker über `scripts/ci_tests.py`), `plan`/`production-policy`/`deploy` `skipped` | keine; kein Environment, kein Wrangler, keine Freigabe |
| immer | `abschluss` mit `if: always()` | keine; liest nur `needs.*.result` |

Die beiden `paths`-Filter sind deckungsgleich und nennen jedes aufgerufene Skript (W1/W3 der Trigger-Wache). Der `push`-Filter bleibt, damit Worker-Änderungen **weiterhin getestet** werden – die Testabdeckung wurde nicht geopfert, sondern vom Deploy getrennt.

### S2 · Verhaltensbeweis (`scripts/worker_deploy_abschluss.py`, neu)

Der Vorfall vom 24.10. war ein *stiller Skip*. Ein Gate, das nur die Environment-Einstellungen liest, erschließt dessen Abwesenheit indirekt. Der neue Abschlussjob misst das Verhalten **dieses Laufs**:

- Bei `workflow_dispatch`: `ref == refs/heads/main`, Plan nicht leer, `plan`/`production-policy`/`deploy` alle `success`. Jedes `skipped`, `failure`, `cancelled` ist **rot und nennt den Job**.
- Bei `push`/`pull_request`: `tests == success` und alle drei Deploy-Jobs `skipped`. Ein ausgeführter Deploy auf Push/PR ist ein **harter Bruch**, kein „war halt nicht nötig".
- Unlesbare Eingaben (leerer/ungültiger Plan, unbekanntes Ereignis, fehlendes Ergebnis) sind **Exit 2**, nie grün.

16 Gegenproben im `--selftest`, 18 Vertragstests am echten Workflow-Text. Das Urteil landet als Markdown in der Job-Zusammenfassung; ein grüner Lauf ohne ausgeführten Deploy ist damit ausgeschlossen.

### S3 · Ampel statt grünem Schein (`.github/workflows/produktions-schutz-selbstheilung.yml`)

C14 verlangt für einen Zustand, den das Repository nicht herstellen kann, die Warnstufe statt Dauer-Rot. Richtig – aber der **Commit** darf deshalb nicht grün aussehen. Der Heil-Lauf schreibt seinen gemessenen Zustand als Check-Run `Produktions-Schutz · Environment (WF-829B)` an `github.sha`:

| Mess-Exit | Conclusion | Bedeutung |
|---|---|---|
| 0 | `success` | Zielzustand mit Nachmessung belegt |
| 1 | **`action_required`** | Inhaberhandlung offen, `details_url` → #922, zwei konkrete Schritte im Text |
| 2 / 3 / Sonstige | `failure` | ungeprüft gilt nicht als sauber |

Das einzige neue Recht ist `checks: write` für diesen Status – **kein** `administration: write`, kein Deploy-Recht, kein Secret, keine Freigabe, keine `pending_deployments`. Der echte `run:`-Block wurde offline gegen alle vier Exit-Codes mit einem `gh`-Stellvertreter nachgefahren; jeder erzeugte gültigen Check-Run-Körper. Die Ampel verschwindet von selbst, sobald die Nachmessung grün ist.

### Dokumentation und Einbindung

`docs/SICHERHEIT-BETRIEB-RUNBOOK.md` § **A4c** (Messwerte, Trigger-Vertrag, Ampel, drei Inhaber-Handgriffe, Nachweisbefehle) · `.github/workflows/alert-on-failure.yml`: der Rat zu WF-829B nennt die neue Auslöser-Logik · `package.json`: `test:worker:abschluss` sowie Aufnahme in `test:sicherheit`.

---

## 4. Geänderte Dateien

| Datei | Änderung |
|---|---|
| `.github/workflows/worker-deploy.yml` | Trigger-Vertrag, `tests`-Job (Push/PR), `if:`-Grenzen an `plan`/`production-policy`/`deploy`, `abschluss`-Job, symmetrische Pfadfilter, begründeter Kopfkommentar. **Gate, Reihenfolge, Resolver und Nachweis unverändert.** |
| `scripts/worker_deploy_abschluss.py` | **neu** – Verhaltensbeweis, 16 Gegenproben, CLI (`--pruefen`, `--selftest`, `--md`, `--json`), Exit 0/1/2 |
| `scripts/tests/test_worker_deploy_abschluss.py` | **neu** – 18 Tests: Entscheidungen, echter Trigger-Vertrag, harter Stopp, Pfadfilter-Symmetrie, Ampel-Verdrahtung, `--wache` grün |
| `.github/workflows/produktions-schutz-selbstheilung.yml` | Ampel-Schritt, `checks: write` nur im Live-Job, drei ehrliche Zustände |
| `.github/workflows/alert-on-failure.yml` | ein Satz im WF-829B-Rat: Deploy nur auf Zuruf, Abschlussjob macht Skips rot |
| `docs/SICHERHEIT-BETRIEB-RUNBOOK.md` | § A4c mit Messprotokoll, Grenze, Schließpfad und Inhaber-Schritten |
| `package.json` | `test:worker:abschluss`; Aufnahme in `test:sicherheit` |
| `WARTUNG-…-2026-11-10.md` | dieser Bericht |

**Nicht angefasst:** `worker_environment_guard.py`, `worker_environment_einrichten.py`, `produktions_schutz_selbstheilung.py`, `data/produktions_schutz_vertrag.json`, `data/produktions_schutz_belege.jsonl`, `data/integrity_lock.json`, alle 55 signierten Kerndateien, alle Abhängigkeits-Pins. Kein Secret gelesen, kein Token ausgegeben, keine Dependency geändert.

---

## 5. Verifikation (10.11.2026, lokal ausgeführt; Live-Werte über `api.github.com`)

| Prüfung | Ergebnis |
|---|---|
| `npm run test:worker:abschluss` | ✅ 16 Gegenproben + **18 Tests OK** |
| `npm run test:sicherheit` | ✅ Exit 0 (inkl. Eichprobe, `--wache`, 38 Vertragstests, neuem Beweis) |
| `npm run test:worker:selbstheilung` | ✅ Exit 0 |
| `python3 scripts/produktions_schutz_selbstheilung.py --wache` | ✅ Vertrag, Verdrahtung, harter Stopp, Kette heil |
| `python3 scripts/workflow_vertrag_wache.py --gate` / `--selftest` | ✅ **102 Workflows**, V1–V7, 0 Befunde |
| `python3 scripts/trigger_wache.py --check` / `--selftest` | ✅ 102 Workflows, **0 Befunde**; `npm run test:trigger` grün |
| `python3 scripts/workflow_js_wache.py --check` / `npm run workflow:js` | ✅ alle `github-script`-Blöcke kompilieren |
| `python3 scripts/skript_syntax_wache.py --check` | ✅ **691 Dateien** grün |
| `python3 scripts/wachen_vertrag.py` / `--selftest` | ✅ **396 Skripte**, 0 Funde |
| `python3 scripts/governance_contract.py` und `--quick` | ✅ 46 Regeln, beide Richtungen |
| `python3 scripts/integrity_guard.py --gate` | ✅ **55 Kerndateien** == signierter Stand (`90aa12b`) |
| `python3 scripts/alert_issue_identity.py --selftest` / `--tabelle` | ✅ 66 Workflows, 66 eindeutige Codes, WF-829B unverändert |
| `python3 scripts/alert_resolve_gate.py --selftest` | ✅ Job-Beweis bleibt die Schließregel |
| `python3 scripts/selftest_runner.py --ohne-uhr-probe` | ✅ **283 Wachen**, 0 rot |
| Ampel-`run:`-Block (aus dem echten YAML extrahiert, `gh` offline nachgebaut) | ✅ vier Exit-Klassen erzeugen gültige Check-Run-Körper (`success` / `action_required` / `failure`) |
| `python3 scripts/worker_environment_guard.py --check` (live) | ✅ Exit 1 — 3 Befunde, fail-closed **unverändert** |
| `python3 scripts/worker_environment_einrichten.py --pruefen` (live) | ✅ MACHBAR / OBERFLAECHE / MACHBAR |
| Live-`PUT` Environment | ✅ **403** `administration=write`; Nachmessung: `updated_at` unverändert 25.10. |
| `alert_resolve_gate.py` mit dem **echten Body von #922** | ✅ grüner Push-Lauf (Gate `skipped`) → **`schliessen: false`**; echter grüner Deploy-Lauf → **`schliessen: true`**. Kein Schlupfloch durch die Trigger-Trennung |
| `worker_deploy_abschluss.py` (3 Lagen simuliert) | ✅ Push-only-Tests → 0 · roter Dispatch (`policy=failure`, `deploy=skipped`) → 1 mit Namensnennung · grüner Dispatch → 0 |

PyYAML 6.0.3 und die übrigen in `requirements-ci.txt` gepinnten Pakete wurden für diese Verifikation in einer **separaten Sandbox-Umgebung** bereitgestellt (`/tmp`, nicht im Repo). Ohne sie meldet der Selbsttest-Runner die bekannte Prüfgrundlagen-Lücke (#1001) fail-closed; am Repository wurde **keine Abhängigkeit geändert**.

**Vorbefund, unverändert, eigener Kanal:** `python3 scripts/artefakt_waechter.py` meldet zwei syntaktisch gebrochene GSC-Artefakte (`data/gsc/top_seiten_28t.json`, `data/gsc/top_suchbegriffe_28t.json`). Beide sind **bereits in `HEAD` ungültig** und wurden von diesem Vorgang nicht berührt. Sie gehören nicht zu WF-829B und werden bewusst **nicht von Hand rekonstruiert** (D7: ein Messartefakt ist eine ganze Messung, kein Text) – die Heilung ist ein neuer Lauf ihres Erzeugers.

**Live-Gegenprobe auf dem PR (Run 42867976651, `pull_request`):** `Worker-Tests (ohne Deployment)` = `success`, `Deploy planen` / `Produktions-Environment absichern …` / `Deploy …` = `skipped`, **`Deploy-Beweis · kein stiller Skip` = `success`**. Damit ist der neue Vertrag nicht nur offline, sondern in der echten CI auf einem Nicht-Deploy-Ereignis belegt. `Verträge, Eichprobe und Verdrahtung (offline)` = `pass`; der Live-Heiljob ist auf PRs planmäßig `skipping`.

**Drei rote PR-Checks sind Vorbefunde des Hauptstands** und liegen ausschließlich in Dateien, die dieser Vorgang nicht berührt hat (alle drei lokal am unveränderten `HEAD` nachgefahren):

| Check | Roter Schritt | Ursache im Bestand |
|---|---|---|
| `Integritäts-Siegel` | Artefakt-Wächter | drei syntaktisch gebrochene GSC-Artefakte (`data/gsc/meta.json`, `top_seiten_28t.json`, `top_suchbegriffe_28t.json`) |
| `ReDoS-Wache` | Sicherheitsvertrag zu Alert Nr. 87 | `test_gsc_abdeckung` liest dieselben gebrochenen GSC-Daten; `redos_guard.py` und `test_redos_security` sind grün |
| `Playwright-Suite` | Metadaten-Wache – Quelle | M4: Artikel vom 05.11.2026 ohne `quellen` im Frontmatter; der Workflow-Kommentar nennt diesen Bestandsbefund ausdrücklich |

Sie gehören nicht zu WF-829B und werden bewusst **nicht von Hand rekonstruiert** (D7: ein Messartefakt ist eine ganze Messung, kein Text; der M4-Befund ist eine Redaktionsentscheidung). Die Heilung ist ein neuer Lauf des jeweiligen Erzeugers – kein Eingriff in diesen Vorgang.

---

## 6. Grenzen und was offen bleibt

- **Der Inhaber-Schritt ist echt und nicht automatisierbar.** Zwei Ziele setzt die API, sobald `UMGEBUNGS_ADMIN_TOKEN` mit `Environments: read/write` steht; der dritte (`can_admins_bypass`) ist ein Dashboard-Schalter. Kein Agent, kein Workflow und kein Token in diesem Repository kann ihn heute setzen. Das ist gemessen, nicht vermutet.
- **Kein Deploy wurde freigegeben, kein Schutz gelockert.** `worker_environment_guard.py --check` steht weiter vor jedem Secret-Zugriff; `--wache` Regel W5 verbietet, dass der Heilweg das Gate ersetzt. Push/PR-Läufe berühren das Environment gar nicht mehr.
- **Ein grüner Push-Lauf ist kein Deploy-Lauf.** Er enthält nur den Testjob und den Abschlussbeweis; `alert_resolve_gate.py` verlangt für #922 den grünen Job „Produktions-Environment absichern …", der auf Push/PR `skipped` ist. Ein solcher Lauf **kann #922 nicht schließen** – genau deshalb ist die Trennung kein Schlupfloch.
- **Die Ampel ist ein Status, keine Freigabe.** `action_required` macht den offenen Zustand am Commit sichtbar; es entscheidet nichts über Deploys und erzeugt keinen zweiten Alarm.
- **Die Eichprobe prüft den Prüfer, nicht die Welt.** Sie beweist, dass der belegte Vorfall erkannt wird, nicht dass jede denkbare Beschädigung erkannt wird.
- **#922 bleibt offen**, bis ein echter grüner Deploy-Lauf existiert. Ein Bericht, ein grüner Plan oder ein grüner Selbsttest schließen ihn ausdrücklich nicht.

### Die drei Inhaber-Handgriffe (einmalig)

1. Secret `UMGEBUNGS_ADMIN_TOKEN` mit `Environments: read/write` hinterlegen. Der Tageslauf (05:48 UTC) setzt Required Reviewer und Branch-Regel `main` danach **selbst** – mit Eichprobe, Nachmessung und Belegkette. Kontrolle ohne Eingriff: `npm run worker:selbstheilung:pruefen` und `npm run worker:selbstheilung:wache`.
2. Im Dashboard *Allow administrators to bypass configured protection rules* **aus**. Kontrolle: `python3 scripts/worker_environment_guard.py --check` muss Exit 0 liefern.
3. Actions → „Cloudflare-Worker deployen" → *Run workflow* (`main`, `newsletter-worker`), bei *Review deployments* freigeben. `/healthz` muss den `bau`-Stempel aus `wrangler.toml` liefern. **Erst dieser grüne Deploy-Lauf schließt #922 automatisch** – mit dem Job-Beweis, den `alert_resolve_gate.py` verlangt.

---

*Geheilt, gemessen und belegt am 10.11.2026. Geändert hat sich nicht das Environment – das kann dieses Repository nicht. Geändert hat sich, dass kein Routine-Push mehr einen unmöglichen Produktions-Deploy versucht, dass ein übersprungener Deploy am Verhalten rot wird und dass ein ungeheilter Zustand nicht mehr grün aussieht.*
