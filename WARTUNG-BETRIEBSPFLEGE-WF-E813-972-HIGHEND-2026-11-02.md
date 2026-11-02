# Wartung · Betriebspflege · Vorgang WF-E813 (#972) — Highend-Dauerheilung, 02.11.2026

**Auftrag:** `Wartung · Betriebspflege · Vorgang WF-E813 #972 Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben.`
**Datum:** 02.11.2026 · **Branch:** `arena/92a0e9f2-franksfinanzcheck-blog` · **Basis:** `876ea5a` (`main`)
**Vorgänger:** `WARTUNG-BETRIEBSPFLEGE-WF-E813-815-HIGHEND-2026-10-29.md` (Stufe 5, #815) · `WARTUNG-VEROEFFENTLICHUNG-WF-829B-922-DAUERHEILUNG-HIGHEND-2026-11-01.md` (#922, Freigabe-Wache)

---

## 1. Kurzfassung

#972 ist die tägliche Sicherheits-Wache. Sie ist rot, weil **zwei unabhängige
Live-Prüfungen** scheitern: die Header der Seite (F-01) und das
authentifizierte Betriebsbild des Workers (F-02/F-03/F-08). Beide Ursachen
sind **Inhaber-Aufgaben**, keine Code-Regression:

| Befund | Gemessen | Ursache | Heilung |
|---|---|---|---|
| **F-01** | Auf `/` und `/methodik/` fehlen fünf Pflicht-Header (CSP, Referrer-Policy, X-Frame-Options, X-Content-Type-Options, HSTS). Die Messung war erfolgreich, der Proxy ist aktiv. | Die Transform Rule `FF Sicherheits-Header` ist nicht aktiv. | A1: `npm run edge:freigabe:apply` mit Zonen-Token, danach B7. |
| **Worker** | `/healthz` liefert keinen `bau`-Stempel; das authentifizierte Betriebsbild ist unvollständig (`budget`, `turnstile`, `schluesselrollen`, `exporte`). | Der letzte Worker-Deploy liegt vor dem Repo-Stand `ff-newsletter-2026-10-24`; der Deploy ist seit 25.10.2026 durch das ungesicherte Environment `cloudflare-produktion` blockiert. | Environment absichern (Reviewer, `main`, Bypass aus), Zugang hinterlegen, deployen, Freigabe erteilen. |

**Das Repository kann diese beiden Schritte nicht stellvertretend ausführen.**
Der verfügbare GitHub-Token ist ein Integrations-Token ohne
`Environments: write`; ein Schreibversuch wird mit **HTTP 403**
„Resource not accessible by integration“ beantwortet. Der Cloudflare-Zonen-
Token und der Worker-Deploy-Zugang existieren in dieser Umgebung nicht. Ein
„grüner“ Behelf wäre eine Fälschung des Live-Nachweises. **#972 bleibt
offen.**

Was diese Stufe liefert, ist der **Schließpfad für den Menschen**: Die Meldung
nennt jetzt den Schritt, der den Deploy tatsächlich blockiert
(`Produktions-Environment absichern`), und das Runbook hat eine
Reihenfolge, die jeden Schritt mit dem nächsten belegt. Der harte Stopp
bleibt unangetastet.

---

## 2. Forensischer Ist-Befund (live gemessen, nicht zitiert)

### 2.1 Der letzte Live-Lauf: `41308995375`

Sicherheits-Wache, Event `schedule`, 01.11.2026 12:58:33 UTC, Commit
`c854f594`. Job „Quellseite“ grün, Job „Abhängigkeiten“ grün, Job
**„Live-Messung“ rot**:

- **F-01 BEFUND (10 Annotationen):** Auf `https://franksfinanzcheck.de/` und
  `/methodik/` fehlen `content-security-policy`, `referrer-policy`,
  `x-frame-options`, `x-content-type-options` und
  `strict-transport-security`. Die Wache klassifiziert „gemessen, und etwas
  fehlt“ — nicht „nicht messbar“. Die Diagnose ist damit eindeutig: Die Zone
  liegt hinter dem Proxy, die Regel wirkt nicht.
- **Worker STOERUNG (3 Annotationen):** `bau` fehlt in `/healthz`; das
  authentifizierte Betriebsbild ist unvollständig. Die Annotation nennt den
  veralteten Deploy und verweist auf den Workflow „Cloudflare-Worker
  deployen“.
- **Environment-Warnung:** „3 Ziel(e) nicht erreicht“ — Required Reviewer
  fehlt, Administrator-Bypass aktiv, Deployment-Branch-Policy fehlt. Der
  Deploy bleibt fail-closed gesperrt.
- **Gesamturteil:** `header: BEFUND, worker: STOERUNG – kein vollständiger
  Live-Nachweis.`

### 2.2 Der letzte Worker-Deploy: `41417750214`

Push-Lauf vom 02.11.2026 09:04:46 UTC, Commit `339de076`
(`chore(deps): bump wrangler (#1015)`). Der Planungsjob war grün, der Job
**„Produktions-Environment absichern“** rot, der Secret-tragende Deploy-Job
**übersprungen**:

```text
Environment `cloudflare-produktion` ist nicht deploy-sicher:
Required Reviewer fehlt.
Administrator-Bypass ist aktiv oder nicht belegbar; auf `false` setzen.
Deployment-Branch-Policy fehlt; aktuell ist kein Branch eingeschränkt.
```

Das ist die exakte Ursache des Worker-Befunds: Der Deploy kommt gar nicht bis
Wrangler. Der letzte erfolgreiche Worker-Deploy war `40113538658` am
24.10.2026 16:52:15 UTC; seitdem ist jeder Lauf an dieser Policy
gescheitert.

### 2.3 Das Environment: seit der automatischen Anlage unberührt

`GET /repos/frank-hartung/franksfinanzcheck-blog/environments/cloudflare-produktion`,
02.11.2026:

```json
{"can_admins_bypass": true, "created_at": "2026-10-25T13:20:15Z",
 "deployment_branch_policy": null, "name": "cloudflare-produktion",
 "protection_rules": [], "updated_at": "2026-10-25T13:20:15Z"}
```

`created_at == updated_at`: Seit GitHub das Environment beim ersten Verweis
automatisch angelegt hat, hat es niemand konfiguriert. Es ist kein
verlorener Schutz, es ist ein **nie eingerichteter**.

### 2.4 Die Rechtegrenze ist erneut belegt

Ein Schreibversuch mit dem verfügbaren Token, 02.11.2026:

```text
PUT /repos/…/environments/cloudflare-produktion  → 403
"Resource not accessible by integration"
```

`python3 scripts/worker_environment_einrichten.py --anwenden --reviewer
frank-hartung` übersetzt denselben Befund:

```text
[error] Produktions-Environment nicht einrichtbar: GitHub-API verweigert den
Zugriff (HTTP 403). Dem Token fehlt das Recht, Environments zu schreiben
(feingranular: `Environments: read/write`, klassisch: `repo`/`administration`).
Das ist ein Rechtebefund, keine Code-Regression – die Einrichtung bleibt eine
Inhaber-Aufgabe.
```

Das Environment ist unverändert (`updated_at` bleibt 25.10.2026 13:20:15 UTC).
Die Sandbox erreicht `franksfinanzcheck.de` und `abos.franksfinanzcheck.de`
nicht (nur `github.com`, `api.github.com`, npm und PyPI sind offen). Die
Live-Messung läuft deshalb im Workflow, nicht in diesem Bericht.

### 2.5 Warum die grünen Push-Läufe kein Abschluss sind

Die Push-/PR-Läufe der Sicherheits-Wache auf `main` sind grün, weil der
Live-Job nur bei `schedule` und `workflow_dispatch` läuft
(`if: github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'`).
Sie beweisen die Offline-Wachen, nicht die Edge. Der letzte Live-Lauf bleibt
`41308995375` (rot). Genau diese Unterscheidung ist der Grund, warum
`sicherheits_nachweis.py` den Abschluss an den Live-Job bindet und nicht an
den Push-Lauf.

---

## 3. Dauerhafte technische Heilung

### H-A · Die Meldung nennt den Blocker, nicht nur das Symptom

`.github/workflows/alert-on-failure.yml`, Klasse `sicherheit-live`:

- **F-01:** Der Rat behauptet nicht mehr pauschal „ohne aktiven Proxy kann
  die Regel nicht wirken“. Er verweist auf die Diagnose der Header-Annotation:
  Proxy aktiv → Regel fehlt/ist unvollständig; Proxy fehlt → DNS/Proxy
  zuerst. Das ist der Unterschied zwischen „die Regel ist falsch“ und „die
  Regel kann nicht wirken“ — zwei Befunde mit zwei verschiedenen nächsten
  Schritten.
- **Worker:** Der Rat nennt jetzt den Schritt, der den Deploy blockiert:
  `Produktions-Environment absichern`. Fehlt `bau` und ist der letzte Deploy
  dort gescheitert, zuerst Reviewer + exakt `main` + Admin-Bypass aus, dann
  deployen. Read-only prüfbar mit
  `python3 scripts/worker_environment_guard.py --check`; einrichtbar mit
  `python3 scripts/worker_environment_einrichten.py --anwenden --reviewer
  frank-hartung` (Reviewer + Branch), Bypass im Dashboard.
- **Abschluss:** `npm run worker:environment` (Exit 0) und
  `npm run edge:freigabe` (Exit 0) vor dem Live-Lauf; nur der vollständige
  Live-Nachweis schließt.

Der Vertragstest `test_972_live_rat_nennt_den_environment_blocker` nagelt
diese drei Sätze fest. Die Verhaltens-Simulation (74 Szenarien) bleibt grün;
die bestehende #809-Gegenprobe verlangt weiterhin `**Worker:**`, `A3/A4 und
D2`, `KV_NAMESPACE_ID_ABO`, `edge:freigabe:apply` und `edge:b7:apply` — der
neue Rat hat diese Elemente nicht verdrängt, sondern ergänzt.

### H-B · Die Reihenfolge im Runbook

`docs/SICHERHEIT-BETRIEB-RUNBOOK.md`, neuer Abschnitt **A1b · Live-Abschluss
#972 — die Reihenfolge**:

1. Environment absichern (A4) — Reviewer, `main`, Bypass aus; Verify
   `npm run worker:environment`.
2. Zugang hinterlegen (A4) — `CF_WORKERS_DEPLOY_TOKEN`,
   `CLOUDFLARE_ACCOUNT_ID`; „Deploy-Zugang prüfen“ ohne Deploy.
3. Worker deployen (D2) — Workflow, Freigabe erteilen, `/healthz` mit
   `bau == ff-newsletter-2026-10-24`.
4. Edge-Regel anwenden (A1) — `edge:freigabe`, `edge:freigabe:apply`,
   `edge:b7`, Datenschutztext committen.
5. Live-Nachweis — `gh workflow run sicherheits-wache.yml --ref main`; nur
   der vollständige Erfolg schließt #972.

Die Reihenfolge ist so gewählt, dass jeder Schritt den nächsten belegt: Ohne
Environment-Policy kein Deploy, ohne Deploy kein `bau`, ohne Edge-Regel keine
Header, ohne beides kein Live-Nachweis.

### H-C · Keine Lockerung des Gates

Der Guard bleibt fail-closed. `can_admins_bypass` ist weiterhin ein
Dashboard-Schalter, weil die GitHub-API ihn nicht annimmt (REST
`additionalProperties: false`; GraphQL `updateEnvironment` kennt nur
`waitTimer`, `reviewers`, `preventSelfReview`). Der Bypass ist keine
Formalie: Ein Administrator, der ihn umgehen darf, umgeht auch den Required
Reviewer. Ihn durch eine „Warnung“ zu ersetzen, wäre keine Heilung, sondern
die Abschaffung des Schutzes.

---

## 4. Verifikation

| Prüfung | Ergebnis |
|---|---|
| `python3 -m unittest scripts.tests.test_alert_scoping` | ✅ **31 Tests** (1 skipped), inkl. neuer Environment-Blocker-Test |
| `node scripts/tests/sim/alert_scoping_sim.mjs` (74 Szenarien) | ✅ **74/74** über den Vertragstest |
| `python3 scripts/workflow_js_wache.py --check` | ✅ alle `github-script`-Blöcke kompilieren |
| `python3 -m unittest scripts.tests.test_workflow_yaml` | ✅ 7 Tests (7 skipped, YAML-Modul nicht installiert) |
| `python3 scripts/worker_environment_einrichten.py --pruefen` (live) | ❌ **3 Ziele nicht erreicht** — Environment weiterhin ungesichert (erwartet) |
| `python3 scripts/worker_environment_guard.py --check` (live) | ❌ **Exit 1** — Required Reviewer, Bypass, Branch-Policy (erwartet) |
| `PUT …/environments/cloudflare-produktion` (live) | ❌ **HTTP 403** — Rechtebefund, Environment unverändert |
| `python3 scripts/worker_environment_einrichten.py --anwenden` (live) | ❌ **HTTP 403** — Rechtebefund, keine Änderung |
| `python3 scripts/blog_header_gate.py --offline` | ✅ Repo-Stand (Vorlage + Meta-CSP) grün |
| `python3 scripts/cloudflare_edge_freigabe.py --selftest` | ✅ 7 Fälle (Vorlage, SSL-Downgrade-Sperre, Regel-Vollprüfung, B7) |
| `python3 scripts/worker_betrieb_wache.py --selftest` | ✅ |
| `python3 scripts/sicherheits_nachweis.py --selftest` | ✅ Live-Abschluss, übersprungene Schritte, widersprüchliche Messnachweise |
| `python3 scripts/worker_freigabe_wache.py --selftest` | ✅ 20 Fälle |
| `python3 -m unittest scripts.tests.test_worker_freigabe_wache` | ✅ 23 Tests |

Die Live-Prüfungen (Header, Worker, Cloudflare-Regel) sind aus der Sandbox
nicht erreichbar. Sie sind im Workflow hinterlegt und werden dort gemessen;
dieser Bericht behauptet kein Grün, das er nicht gemessen hat.

---

## 5. Was offen bleibt — fünf Schritte, ein Beweis

**Schritt 1 — Environment absichern** (Settings → Environments →
[`cloudflare-produktion`](https://github.com/frank-hartung/franksfinanzcheck-blog/settings/environments)):

1. *Required reviewers* → **Frank Hartung**.
2. *Deployment branches and tags* → **Selected branches and tags** → Regel
   `main` (Typ *Branch*), sonst nichts.
3. *Allow administrators to bypass configured protection rules* → **aus**.

Reviewer und Branch-Regel kann alternativ ein Token mit
`Environments: read/write` setzen:

```bash
GITHUB_TOKEN=<PAT> GITHUB_REPOSITORY=frank-hartung/franksfinanzcheck-blog \
  python3 scripts/worker_environment_einrichten.py --anwenden --reviewer frank-hartung
```

Den Bypass-Schalter stellt nur das Dashboard. Danach:

```bash
npm run worker:environment     # muss Exit 0 melden
```

**Schritt 2 — Zugang hinterlegen:** `CF_WORKERS_DEPLOY_TOKEN` (Workers
Scripts: Read + Deploy) und `CLOUDFLARE_ACCOUNT_ID` im Environment. Prüfen
ohne Deploy: Actions → „Deploy-Zugang prüfen“ → *Run workflow* (`main`).

**Schritt 3 — Worker deployen:** Actions → „Cloudflare-Worker deployen“ →
`newsletter-worker` von `main`. Der Secret-Job hält auf Freigabe; den Lauf
freigeben oder abbrechen. Der Lauf muss `/healthz` mit
`bau == ff-newsletter-2026-10-24` belegen.

**Schritt 4 — Edge-Regel anwenden:**

```bash
npm run edge:freigabe          # Exit 0
npm run edge:freigabe:apply    # Regel → SSL → DNS → Gegenmessung → B7
npm run edge:b7                # Datenschutztext geprüft
```

Token: `CLOUDFLARE_API_TOKEN` mit `Zone.DNS:Edit`, `Zone.Settings:Edit`,
`Zone.Transform Rules:Edit` für diese Zone. Den geänderten Datenschutztext
committen.

**Schritt 5 — Live-Nachweis:**

```bash
gh workflow run sicherheits-wache.yml --ref main
```

Nur der vollständige erfolgreiche Live-Job schließt #972. Die Warnung
„Produktions-Environment“ bleibt danach als #922-Nachweis bestehen, bis der
Bypass-Schalter im Dashboard steht; sie ist keine Live-Sicherheits-
Abweichung, sondern die Vorbedingung für den nächsten Deploy.

---

## 6. Grenzen dieser Heilung (bewusst benannt)

- **Der Bypass-Schalter bleibt Handarbeit.** Kein Werkzeug und kein Token in
  diesem Repository kann ihn setzen; die Belege stehen in Abschnitt 2.3/2.4.
- **Der Zonen-Token und der Deploy-Zugang fehlen in dieser Umgebung.** Der
  Apply und der Deploy sind Inhaber-Aufgaben; ein „grüner“ Behelf wäre eine
  Fälschung des Nachweises.
- **Die Sandbox erreicht die Live-Hosts nicht.** Die Endabnahme läuft im
  Workflow; dieser Bericht ist die Vorbereitung, nicht der Beweis.
- **Der Abschluss braucht einen Menschen.** Jeder Deploy nach Schritt 1 hält
  an; das ist die gewollte Wirkung des Schutzes, den dieser Vorgang verlangt.
  Wer sie nicht will, will den Schutz nicht — dann ist die Entscheidung zu
  ändern, nicht die Anzeige.
