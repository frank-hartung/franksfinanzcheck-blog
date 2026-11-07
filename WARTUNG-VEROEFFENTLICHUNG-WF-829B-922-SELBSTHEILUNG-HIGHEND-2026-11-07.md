# Wartung · Veröffentlichung · Vorgang WF-829B (#922) — automatische Selbstheilung, 07.11.2026

**Vorgang:** WF-829B · **Issue:** [#922](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/922) (weiterhin **OFFEN**)
**Auftrag:** „Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben mit automatischer Selbstheilung."
**Stand der Messungen:** 07.11.2026, 09:50–10:05 UTC · alle Werte am echten Baum, am echten Environment und am echten Artefakt gemessen
**Vorberichte:** `…-2026-10-29.md` · `…-2026-10-30.md` · `…-2026-11-01.md` · `…-2026-11-03.md` · `…-SIEGEL-DAUERHEILUNG-2026-11-04.md`

---

## 1. Kurzfassung: der Befund war die fehlende Verdrahtung

Fünf Berichte haben den Zustand korrekt beschrieben und ihn deshalb für geheilt gehalten: Das Environment ist ungesichert, das Gate hält fail-closed, der Einrichter *könnte* zwei der drei Ziele setzen, und der Rest sei eine Inhaber-Aufgabe. **Was keiner der Berichte geprüft hat: ob der Einrichter überhaupt je automatisch aufgerufen wird.**

Er wird nicht. `worker_environment_einrichten.py --anwenden` existiert seit dem 30.10.2026, steht als Handbefehl in `package.json` und in Prosa in den Berichten — und in **keinem einzigen Workflow-Aufruf**. Die tägliche Sicherheits-Wache ruft ausschließlich `--pruefen --warnstufe` auf. Jeden Morgen wurde derselbe Befund neu gemeldet, jeden Tag blieb er liegen. Das ist keine Wache, sondern eine Warteschlange: dieselbe Klasse wie GSC #1097 am 06.11.2026 (`--apply` ein Handbefehl), nur an der teureren Stelle.

> Ein Heilpfad, den niemand anstößt, ist kein Heilpfad. Die eigentliche Dauerheilung dieses Vorgangs ist nicht das Environment, sondern der **automatische Lauf**, der es herstellt, nachmisst und belegt.

| Nr | Befund (07.11., live gemessen) | Heilung | Stand |
|---|---|---|---|
| **A** | `--anwenden` in keinem Workflow verdrahtet; Tages-Wache meldet nur | Eigener Workflow mit **drei** Auslösern: täglich 05:48 UTC, **nach jedem Worker-Deploy auf `main`**, auf Zuruf; Push/PR am Regelwerk | **geheilt** |
| **B** | Der Prüfer konnte unbemerkt „immer grün" werden | **Eichprobe vor jedem Urteil**: Vorfall im Speicher nachgebaut, Sabotage ⇒ Exit 3, kein Urteil und kein Schreibzugriff | **geheilt**, mit Gegenprobe belegt |
| **C** | Kein Heil-Lauf prüft, was er getan hat | **Pflicht-Nachmessung** nach jedem Eingriff; Verschlechterung ⇒ Exit 2; verbleibender Rest bleibt `OFFEN`, nie `GEHEILT` | **geheilt** |
| **D** | Beweis war Prosa in Berichten | **Append-only Belegkette** mit verketteten SHA-256-Prüfsummen (`seq`, `prev_sha256`, `sha256`), Vorher/Nachher je Ziel, Artefakt 90 Tage | **geheilt**, 2 echte Einträge |
| **E** | Verdrahtung konnte still verrotten (Lehre aus #1097 / #806) | `--wache` in **jedem** Lauf: Heilschritt muss im `run:`-Block stehen (Kommentar zählt nicht), Vertrag, Kette, `main`-Grenze, keine Fremd-Secrets, **harter Stopp im Deploy-Pfad unangetastet** | **geheilt**, 8 Sabotagefälle |
| **F** | Ein still roter Heil-Lauf wäre unsichtbar | `Produktions-Schutz · Selbstheilung (WF-829B)` in die Alerting-Wacht-Liste aufgenommen; 66 Workflows, 66 eindeutige Codes | **geheilt** |
| **G** | Environment `cloudflare-produktion` seit 25.10. ungesichert; Token 403; Bypass nur Dashboard | Automatische Heilung **für alles, was die API zulässt**, sobald `UMGEBUNGS_ADMIN_TOKEN` steht; ein Schalter bleibt Inhaber-Aufgabe | **Inhaber**, Abschnitt 6 |

**Nichts wurde gelockert, um Grün zu erzeugen.** `worker_environment_guard.py --check` steht weiter vor jedem Secret-Zugriff; keine Deploy-Freigabe, keine Cloudflare-Secrets, kein `DELETE`, kein `can_admins_bypass` im Schreibkörper. Heute gemessen: `--gate` grün, 55 signierte Kerndateien unverändert.

---

## 2. Forensischer Befund (Bytes und API, nicht Zitat)

### 2.1 Das Environment — heute erneut live gemessen

`GET /repos/…/environments/cloudflare-produktion`, 07.11.2026 09:58 UTC, **nach** allen Schreibversuchen:

```json
{"id": 25274969424, "name": "cloudflare-produktion",
 "created_at": "2026-10-25T13:20:15Z", "updated_at": "2026-10-25T13:20:15Z",
 "can_admins_bypass": true, "protection_rules": [], "deployment_branch_policy": null}
```

`created_at == updated_at` — seit der automatischen Anlage am 25.10. hat **niemand** dieses Environment konfiguriert. Issue #922 ist offen (zuletzt nachgeführt 06.11. 15:33 UTC mit dem roten Lauf `42074601435` vom 05.11., 18:26 UTC: `production-policy → failure`, `deploy → skipped`).

Drei Messungen am selben Objekt, alle heute:

```text
worker_environment_guard.py --check            → Exit 1 · 3 Befunde (Reviewer, Bypass, Branch-Policy)
worker_environment_einrichten.py --pruefen     → Exit 1 · MACHBAR / OBERFLAECHE / MACHBAR
worker_environment_einrichten.py --anwenden    → HTTP 403 · „Dem Token fehlt das Recht, Environments zu schreiben"
```

### 2.2 Die eigentliche Ursache — ein Befehl ohne Anstoß

```text
.github/workflows/sicherheits-wache.yml  →  --pruefen --warnstufe          (nur lesen)
package.json                             →  worker:environment:anwenden     (Handbefehl)
WARTUNG-…-2026-11-03.md                  →  „python3 … --anwenden"         (Prosa)
.github/workflows/**                     →  --anwenden: 0 Treffer          (kein Lauf)
```

Damit war die Kette „messen → melden → **heilen** → nachmessen → belegen" an der dritten Stelle unterbrochen. Die Meldung war korrekt, die Heilung vorhanden, der Anstoß fehlte. Genau das ist der Unterschied zwischen einem Bericht und einem Betrieb.

### 2.3 Warum „dauerhaft" mehr verlangt als einen Cron-Eintrag

Vier Rückfallklassen sind im selben Vorgang schon dokumentiert: eine zerstörte, **parsebare** Siegel-Datei, die der alte Prüfer als `ok` las (#1039, 04.11.); ein Handbefehl ohne Anstoß (#1097, 06.11.); eine Wache, die in keinem Workflow lief (#806, 19.10.); ein roter Check, den das Ruleset nicht verlangt (C18, PR #1021). Ein Cron-Job ohne Eichprobe, Nachmessung, Beleg und Verdrahtungs-Wache wäre die fünfte. Deshalb fünf Schichten statt einer Zeile YAML.

---

## 3. Die Dauerheilung — fünf Schichten, je mit eigenem Beweis

### S1 · Zielzustand an einer Stelle (`data/produktions_schutz_vertrag.json`)

Environment, Zweig, Reviewer, Ziele, Dashboard-Ziele, `nur_verschaerfen: true` und Ledger-Pfad. Der Vertrag wird **strikt gegen die Konstanten des Einrichters und des Gates** validiert (`ZIELE`, `UMGEBUNG`, `ZWEIG`, `LOGIN_RE`) und als Bytes gelesen: doppelte Schlüssel sind ein Bruch, kein gültiges JSON (Lehre aus #1039). Zwölf Sabotagefälle — `nur_verschaerfen: false`, fremdes Environment, gekürzte Ziele, Bypass als API-Ziel, Ledger außerhalb `data/` — werden abgelehnt.

### S2 · Eichprobe vor jedem Urteil (`eichprobe()`)

Der Vorfall wird **im Speicher** nachgebaut (kein Netz, keine Datei): `planen()` muss `{reviewer: MACHBAR, branch: MACHBAR, bypass: OBERFLAECHE}` liefern, der harte Stopp muss ihn sehen, der sichere Zustand muss leer durchgehen, und der Schreibweg muss genau `PUT` Environment + `POST` Branch-Regel sein — ohne `can_admins_bypass` im Körper. Weicht irgendetwas ab: **Exit 3 „MESSGERÄT NICHT EICHFÄHIG"**, kein Urteil, kein Schreibzugriff, kein Ledger-Eintrag mit einem Messergebnis. Gegenprobe: `planen` auf „immer grün" gepatcht ⇒ Eichprobe rot ⇒ kein einziger Schreibaufruf (Test 8, Selbsttest 1/7).

### S3 · Automatischer Heil-Lauf (`.github/workflows/produktions-schutz-selbstheilung.yml`)

| Auslöser | Wirkung |
|---|---|
| `schedule` 05:48 UTC | täglich **vor** der Sicherheits-Wache (06:05): Drift ist behoben, bevor sie gemeldet wird |
| `workflow_run` → „Cloudflare-Worker deployen", `completed`, `head_branch == 'main'` | **der rote Deploy löst seine eigene Reparatur aus** — Minuten statt nächster Tag |
| `workflow_dispatch` (`heilen`/`pruefen`) | auf Zuruf; `pruefen` ist rein lesend |
| `push` / `pull_request` (6 Pfadfilter, spiegelgleich) | Änderung am Heilwerkzeug löst seine Prüfung aus (Trigger-Wache W1/W3) |

Ablauf: `eichprobe → stand()/planen() → schreiben() (nur verschärfend) → stand()/planen() erneut → Ledger`. Ohne Nachmessung kein `GEHEILT`. Eine Verschlechterung (`ERFUELLT → MACHBAR`) bricht mit Exit 2 ab. Zwei geheilte Ziele bei offenem Bypass ergeben `OFFEN` mit dem Satz „weitere Ziele bleiben offen" — nie ein falsches Grün.

Exit-Klassen folgen C34/C14: **0** `SICHER`/`GEHEILT` · **1** `OFFEN` (Warnung mit Schließpfad, kein Dauer-Rot ohne Handlungsmöglichkeit) · **2** `NICHT_BELEGBAR`/`VERSCHLECHTERUNG` (rot) · **3** `MESSGERAET` (rot). Der Mess-Schritt bleibt neutral; ein eigener Auswerte-Schritt entscheidet.

### S4 · Belegkette (`data/produktions_schutz_belege.jsonl`)

Jede Zeile: `seq`, `prev_sha256`, `sha256` über die kanonische Form aller übrigen Felder, dazu Vorher/Nachher je Ziel, Schritte, Gründe, Lauf, Vertrags-Hash und Eichproben-Status. Kein Token, kein Antworttext, kein Fremdlink; eine Geheimnisspur verhindert das Schreiben. Der Lauf kopiert die Kette in `$RUNNER_TEMP`, hängt seinen Beleg an und bewahrt sie 90 Tage als Artefakt auf. `merge=binary` in `.gitattributes` verhindert, dass `merge=union` zwei Läufe mit gleicher `seq` zu einer gebrochenen Kette vereinigt (D7).

Zwei **echte** Einträge, beide live gemessen:

```text
seq 1 · erste-messung-20261107 · OFFEN · MACHBAR → MACHBAR · sha 1f77d2af2d38…
seq 2 · endmessung-20261107   · OFFEN · MACHBAR → MACHBAR · sha 88c89de3be04…
```

Vorher und Nachher sind identisch — das ist der Beweis, dass ein 403 **nicht** als Heilung gebucht wurde.

### S5 · Die Wache über der Wache (`--wache`)

Läuft in **jedem** Lauf, auch auf PRs, offline, ohne PyYAML. Sie prüft Vertrag, Kette, die sechs Pfadfilter auf Symmetrie und Existenz, `--selftest`/`--wache`/`--heilen`/`--beleg`/Vertragstests in echten `run:`-Blöcken (Einzeiler und Blockskalare; Kommentare zählen nicht), Token-Fallback, `main`-Grenze, Concurrency-Sperre, Abwesenheit von `pending_deployments` und Fremd-Secrets — **und dass `worker_environment_guard.py --check` im Deploy-Pfad noch steht**. Acht Sabotagefälle (Heilschritt nur im Kommentar, entfernt, Tageslauf weg, Ereignis-Heilung weg, asymmetrischer Filter, Selbstfreigabe, Fremd-Secrets, gelöschtes Gate) werden erkannt. Wird die Verdrahtung entfernt, wird sie zum Befund.

### Dokumentation und Einbindung

`docs/SICHERHEIT-BETRIEB-RUNBOOK.md` § **A4b** (Auslöser, vier Stufen, Exit-Tabelle, Beleg, Wache, Befehle, Grenzen) · `package.json`: `worker:selbstheilung`, `:pruefen`, `:wache`, `test:worker:selbstheilung` und Aufnahme in `test:sicherheit` · `.github/workflows/alert-on-failure.yml`: neuer Kanal in der Wacht-Liste.

---

## 4. Verifikation (07.11.2026, lokal ausgeführt; Live-Werte über `api.github.com`)

| Prüfung | Ergebnis |
|---|---|
| `produktions_schutz_selbstheilung.py --selftest` | ✅ 11 Fallgruppen grün, offline, ohne Schreibzugriff |
| `python3 -m unittest scripts.tests.test_produktions_schutz_selbstheilung` | ✅ **38 Tests OK** |
| Uhr-Probe `--trap scripts/…py --offset 97` / `1461` | ✅ beide grün |
| Uhr-Probe `--trap-modul scripts.tests.test_… --offset 97` / `1461` | ✅ beide grün |
| `produktions_schutz_selbstheilung.py --wache` | ✅ Vertrag, Verdrahtung, harter Stopp, Kette heil |
| `--heilen --json` (live, Actions-Token) | ✅ `OFFEN` / Exit 1 · Eichprobe bestanden · `RECHT` + `OBERFLAECHE` · Vorher == Nachher · kein falsches Grün |
| `worker_environment_guard.py --check` (live) | ✅ Exit 1 — 3 Befunde, fail-closed **unverändert** |
| `worker_environment_einrichten.py --pruefen` / `--anwenden` (live) | ✅ MACHBAR/OBERFLAECHE/MACHBAR · **HTTP 403** (Rechtebefund) |
| `gh api …/environments/cloudflare-produktion` nach den Versuchen | ✅ `updated_at` unverändert 25.10. — kein versehentlicher Eingriff |
| `npm run test:sicherheit` | ✅ Exit 0 (inkl. Eichprobe, Wache, 38 neue Vertragstests) |
| `python3 scripts/selftest_runner.py --ohne-uhr-probe` | ✅ **275 Wachen**, 0 rot |
| `python3 scripts/integrity_guard.py --gate` / `--selftest` | ✅ 55 Kerndateien == signierter Stand · 11 Fälle |
| `python3 scripts/governance_contract.py` und `--quick` | ✅ 46 Regeln, beide Richtungen |
| `python3 scripts/workflow_vertrag_wache.py --gate` / `--selftest` | ✅ **101 Workflows**, V1–V6 · Selbsttest grün |
| `python3 scripts/trigger_wache.py --check` / `--selftest` | ✅ 101 Workflows, 0 Befunde |
| `python3 scripts/wachen_vertrag.py` | ✅ 386 Skripte, 0 Funde |
| `python3 scripts/skript_syntax_wache.py --check` | ✅ 667 Dateien grün |
| `python3 scripts/artefakt_waechter.py` | ✅ 593 Artefakte strukturell heil |
| `python3 scripts/alert_issue_identity.py --selftest` / `--tabelle` | ✅ 66 Workflows, 66 eindeutige Codes, markenfreie Titel |

PyYAML 6.0.3 und die übrigen in `requirements-ci.txt` gepinnten Pakete wurden für diese Verifikation in einer separaten Sandbox-Umgebung bereitgestellt (die Basis-Sandbox hat sie nicht); am Repository wurde **keine Abhängigkeit geändert**.

---

## 5. Grenzen dieser Heilung (bewusst benannt)

- **Der automatische Pfad kann heute noch nicht schreiben.** Ihm fehlt `Environments: write`; der Lauf meldet `RECHT` statt zu heilen. Das ist heute zweimal gemessen, nicht vermutet. Ein Werkzeug, das einen 403 als „übersprungen" oder „ok" bucht, wäre die Rückkehr des Vorfalls vom 24.10.2026.
- **`can_admins_bypass` bleibt eine Oberflächen-Entscheidung.** Weder REST (`additionalProperties: false`) noch GraphQL `updateEnvironment` nehmen das Feld an. Kein Token, kein Workflow und kein Agent kann es setzen. Wer etwas anderes behauptet, hat es nicht gemessen.
- **Die Wache prüft die Verdrahtung, nicht die Absicht.** Sie beweist, dass der Heilschritt läuft, nicht dass eine Freigabe richtig war. Freigeben bleibt Menschenhandlung; `pending_deployments` kommt im Heil-Lauf nicht vor und ist als Textbefund gesperrt.
- **Die Eichprobe prüft den Prüfer, nicht die Welt.** Sie beweist, dass der belegte Vorfall noch erkannt wird — nicht, dass jede denkbare Beschädigung erkannt wird.
- **Der Branch-Schutz verlangt den Integritäts-Check weiterhin nicht** (C18, PR #1021 ist der Beleg). Das ist eine Admin-Entscheidung; dieser Bericht nennt sie, statt sie zu umgehen.
- **Ein `workflow_run` läuft im Kontext des Default-Branches** und löst keine weitere `workflow_run`-Kette aus. Der Heil-Lauf berührt nie PR-Code.
- **#922 ist nicht geschlossen.** Ein grüner Plan, ein grüner Selbsttest oder dieser Bericht schließen ihn ausdrücklich nicht — erst der Job-Beweis eines echten grünen Deploys (`alert_resolve_gate.py`).

---

## 6. Was offen bleibt — Inhaber-Aufgabe (von drei Handgriffen auf zwei plus Freigabe reduziert)

**Schritt 1 — Schreibrecht hinterlegen** (Settings → Secrets and variables → Actions → New repository secret):

```
Name:   UMGEBUNGS_ADMIN_TOKEN
Wert:   feingranulares Token mit „Environments: read/write" (klassisch: repo/administration)
```

Danach setzt der **automatische** Lauf (täglich 05:48 UTC bzw. unmittelbar nach dem nächsten Deploy) den Required Reviewer und die Branch-Regel `main` selbst — mit Eichprobe, Nachmessung und Beleg. Prüfen ohne Eingriff:

```bash
npm run worker:selbstheilung:wache        # Verdrahtung und Belegkette
npm run worker:selbstheilung:pruefen      # rein lesend
```

**Schritt 2 — ein Schalter im Dashboard** (Settings → Environments → [`cloudflare-produktion`](https://github.com/frank-hartung/franksfinanzcheck-blog/settings/environments)): *Allow administrators to bypass configured protection rules* → **aus**. Das ist der einzige Zielwert, den keine API herstellen kann.

**Schritt 3 — Deploy starten und freigeben:** Actions → „Cloudflare-Worker deployen" → *Run workflow* (`newsletter-worker`, `main`). Der Job `deploy` hält bei *Review deployments* — das ist die gewollte Wirkung des Schutzes. Freigeben über die Oberfläche oder mit `gh api -X POST …/pending_deployments` (Runbook A4). Ein Lauf, der wartet, wird seit 01.11. von `worker_freigabe_wache.py` mit Link gemeldet.

**Abschluss:** zwei grüne Deploy-Jobs, `/healthz` liefert `bau == ff-newsletter-2026-10-24`, `scripts/alert_resolve_gate.py` bestätigt den Job-Beweis. Erst dann schließt #922 automatisch.

---

## 7. Geänderte Dateien

| Datei | Änderung |
|---|---|
| `scripts/produktions_schutz_selbstheilung.py` | **neu** — Vertrag, Eichprobe, Heilung mit Nachmessung, Belegkette, Verdrahtungs-Wache, Selbsttest (11 Fallgruppen), CLI |
| `scripts/tests/test_produktions_schutz_selbstheilung.py` | **neu** — 38 Vertragstests, offline, inkl. Sabotage am Prüfer und an der Verdrahtung |
| `.github/workflows/produktions-schutz-selbstheilung.yml` | **neu** — 5 Auslöser, Offline-Vertragsjob, Live-Heiljob mit neutralem Mess- und eigenem Auswerte-Schritt, Beleg-Artefakt |
| `data/produktions_schutz_vertrag.json` | **neu** — Zielzustand, strikt gegen Gate/Einrichter validiert |
| `data/produktions_schutz_belege.jsonl` | **neu** — 2 echte, verkettete Messungen vom 07.11.2026 |
| `.gitattributes` | `merge=binary` für die Belegkette (Hash-Kette statt Text-Union) |
| `.github/workflows/alert-on-failure.yml` | Heil-Lauf in die Wacht-Liste (66 Workflows) |
| `package.json` | 4 neue Skripte; `--selftest`, `--wache` und 38 Tests in `test:sicherheit` |
| `docs/SICHERHEIT-BETRIEB-RUNBOOK.md` | § A4b: Auslöser, vier Stufen, Exit-Tabelle, Beleg, Wache, Grenzen, Inhaber-Schritte |
| `WARTUNG-…-2026-11-07.md` | dieser Bericht |

**Nicht angefasst:** `worker_environment_guard.py`, `worker_environment_einrichten.py`, `worker-deploy.yml`, `data/integrity_lock.json`, alle 55 signierten Kerndateien. Der harte Stopp steht unverändert vor jedem Secret-Zugriff.

---

*Geheilt, gemessen und belegt am 07.11.2026. Der Zustand des Environments ist heute unverändert — geändert hat sich, dass die Reparatur ab jetzt von selbst anläuft, sich vor jedem Urteil eicht, nach jedem Eingriff nachmisst, jeden Lauf belegt und es meldet, falls sie selbst nicht mehr läuft.*
