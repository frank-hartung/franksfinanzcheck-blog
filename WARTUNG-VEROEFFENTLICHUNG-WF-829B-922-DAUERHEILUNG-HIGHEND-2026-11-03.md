# Wartung · Veröffentlichung · Vorgang WF-829B (#922) — Highend-Dauerheilung, 03.11.2026

**Vorgang:** WF-829B · **Issue:** [#922](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/922)
**Auftrag:** dauerhaft auf Highend-Level einer Profi-Agentur beheben
**Stand der Messungen:** 03.11.2026, 09:00–09:15 UTC · alle Werte live abgefragt
**Vorberichte:** `…-2026-10-29.md` (Zugangsdossier) · `…-2026-10-30.md` (Einrichter + Kanal-Probe) · `…-2026-11-01.md` (Freigabe-Wache)
**Nachtrag 04.11.2026 (PR #1039):** Der Vorgang war blockiert – nicht durch #922, sondern durch ein **zerstörtes Integritäts-Siegel**, das seit dem 02.11.2026 in `main` stand. Ursache, Beweis und die vier Schichten der Heilung: `WARTUNG-VEROEFFENTLICHUNG-WF-829B-922-SIEGEL-DAUERHEILUNG-2026-11-04.md`.

---

## 1. Kurzfassung

Der Vorgang steht exakt dort, wo ihn der Vorbericht verlassen hat — und das ist die saubere Nachricht: **Die Dauerheilung hält.** Seit 25.10.2026 ist das Environment `cloudflare-produktion` unverändert ungesichert; seit 30.10.2026 kann das Repository das selbst beziffern und — soweit eine GitHub-API es zulässt — selbst herstellen; seit 01.11.2026 ist auch der zweite, leise Ausfall sichtbar. Am 03.11.2026 wurde jede dieser Aussagen neu gemessen — kein Zitat, kein Cache.

> Der harte Stopp bleibt unangetastet. Kein Gate wird gelockert, kein Befund zur Warnung herabgestuft, keine Matrix geleert. Was hinzukommt, ist ausschließlich **lesende** Sicht auf Zustände, die es nach der Sicherung zwangsläufig gibt.

| Nr. | Befund | Heilung | Stand 03.11. |
|---|---|---|---|
| **A** | Die Freigabe ist nicht gesetzt; Schreibversuch scheitert mit **403** — Token darf Environments nicht schreiben | Nicht im Repository heilbar. Dreifach gemessen (25.10., 01.11., 03.11.), als Rechtebefund erkannt, mit exakter Klickfolge (Abschnitt 5) | **Inhaber** — 3 Zielfelder (Reviewer MACHBAR, Branch MACHBAR, Bypass OBERFLÄCHE) + 1 Knopf + 1 Freigabe |
| **B** | Nach der Freigabe-Regel wartet jeder Deploy unsichtbar — kein Rot, kein Issue, Concurrency-Slot `worker-deploy` blockiert | `scripts/worker_freigabe_wache.py` + täglicher Schritt „Wartende Deploy-Freigaben“ in `sicherheits-wache.yml` | **geheilt** — 20 Selbsttest-Fälle, 23 Vertragstests, 03.11. live: kein Lauf wartet |
| **C** | Der Wartezustand war nirgends dokumentiert — Runbook nannte nur das Einrichten | Runbook A4 „Die Freigabe ist ein Klick — und der Wartezustand ist bewacht“ + D2-Schritt 3, CLAUDE.md-Abschnitt | **geheilt** — seit 01.11. dokumentiert, heute re-verifiziert |

**Ergebnis heute:** Fail-closed ist seit 25.10. wirksam, die Meldung ist seit 27.10. sachlich richtig, die Heilung ist seit 01.11. vollständig — und sie hat die zwei zusätzlichen Betriebstage ohne Drift überstanden.

---

## 2. Forensischer Ist-Befund (live gemessen, nicht zitiert)

### 2.1 Environment — unverändert seit 25.10.2026, heute erneut gemessen

`GET /repos/frank-hartung/franksfinanzcheck-blog/environments/cloudflare-produktion`, 03.11.2026 09:06 UTC:

```json
{
    "id": 25274969424,
    "name": "cloudflare-produktion",
    "created_at": "2026-10-25T13:20:15Z",
    "updated_at": "2026-10-25T13:20:15Z",
    "can_admins_bypass": true,
    "protection_rules": [],
    "deployment_branch_policy": null
}
```

`GET …/deployment-branch-policies?per_page=100` → `404 {"message":"Not Found"}` — korrekt, weil `deployment_branch_policy == null` (keine Policy-Liste lesbar, nicht etwa leer).

Vier Aussagen in einem Objekt, heute zum dritten Mal identisch:

1. **Kein Required Reviewer** (`protection_rules: []`).
2. **Keine Branch-Regel** (`deployment_branch_policy: null`) — jedes Branch dürfte deployen.
3. **Admin-Bypass aktiv** (`can_admins_bypass: true`).
4. **`created_at == updated_at` (25.10.2026 13:20:15 UTC)** — seit der automatischen Anlage hat niemand das Environment konfiguriert. Es ist kein verlorener Schutz, es ist ein **nie eingerichteter**.

Der letzte relevante Deploy-Lauf ist weiterhin [#41417750214](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/41417750214) (02.11.2026 09:04:46 UTC, Push `339de076`): `plan → success`, `production-policy → failure` („Produktions-Environment absichern (vor Zugriff auf Secrets)“), `deploy → skipped`. Genau der Beweis, dass das Gate **vor** jedem Secret-Zugriff fail-closed hält.

### 2.2 Schreiben ist ein Rechtebefund — heute erneut belegt

Live, 03.11.2026:

```text
GITHUB_REPOSITORY=frank-hartung/franksfinanzcheck-blog GITHUB_TOKEN=<actions-token>
python3 scripts/worker_environment_guard.py --check
→ [error] Cloudflare-Produktionsfreigabe unsicher: Required Reviewer fehlt.
  Administrator-Bypass ist aktiv. Deployment-Branch-Policy fehlt.
  Exit 1 — fail-closed, vor Wrangler, ohne Secrets.

python3 scripts/worker_environment_einrichten.py --pruefen
→ Required Reviewer: MACHBAR · Kein Administrator-Bypass: OBERFLAECHE · Branch-Regel exakt `main`: MACHBAR
  Exit 1 (Warnstufe) / Exit 0 (—warnstufe-Variante für die Tages-Wache: ::warning)

python3 scripts/worker_environment_einrichten.py --anwenden --reviewer frank-hartung
→ [error] GitHub-API verweigert den Zugriff (HTTP 403). Dem Token fehlt das Recht,
  Environments zu schreiben. Das ist ein Rechtebefund, keine Code-Regression.

gh api --method PUT repos/.../environments/cloudflare-produktion → 403 "Resource not accessible by integration"
gh api --method PUT repos/.../environments/wf829b-probe        → 403 (01.11.: zweiter Endpunkt, gleiche Klasse)
POST /repos/.../actions/workflows/<id>/dispatches              → 403 (01.11., Workflow-Dispatch — zweiter Rechtebefund)
```

Damit sind **drei** Grenzen gleichzeitig belegt: Token darf weder Environments schreiben noch Workflows auslösen. Beides ist ein **Rechtebefund** mit `permissions: admin:true` — der Scope fehlt, nicht der Code.

Zwei weitere Grenzen sind dokumentiert und im Werkzeug als Klasse `OBERFLAECHE` festgehalten:

- `can_admins_bypass` ist über **keine** GitHub-API setzbar (`PUT …/environments` → `additionalProperties: false`; GraphQL `updateEnvironment` kennt das Feld nicht). Das Dashboard ist der einzige Schalter.
- Ein Branch-Selbsttest ohne freigegebenen Reviewer würde grün wirken, aber den Deploy nicht freigeben — deshalb bleibt `OBERFLAECHE` in der Tages-Wache als `::warning`, nicht als Dauer-Rot (C14).

### 2.3 Freigabe-Wache — der zweite, leise Ausfall bleibt bewacht

`GITHUB_REPOSITORY=… GITHUB_TOKEN=… python3 scripts/worker_freigabe_wache.py --check`, 03.11.2026 09:08 UTC:

```text
[notice] Wartende Deploy-Freigabe: Kein Worker-Deploy wartet auf eine Freigabe.
→ Exit 0 · Markdown: "Kein Lauf wartet über der Schwelle auf eine Freigabe." (Schwelle 120 Minuten)
```

Die beiden überwachten Ketten (`worker-deploy.yml`, `worker-zugang-pruefen.yml`, je `per_page=30`, ausschließlich `GET`, kein Schreibzugriff) listen heute keinen Lauf in `waiting`/`pending`/`action_required` über der Schwelle. Das ist korrekt: Solange das Gate rot ist, entsteht kein wartender Deploy — die Wache ist dennoch die einzige Stelle, die ihn melden würde, sobald das Environment gesichert ist.

Die Sicherheits-Wache (`sicherheits-wache.yml`, Job **Live-Messung**, täglich 06:05 UTC + auf Zuruf) führt seit 01.11.2026 beide Blicke hintereinander:

- „Produktions-Environment – Freigabestand und Drift“ (`worker_environment_einrichten.py --pruefen --warnstufe` → `::warning` bei 1, `::error` bei 2)
- „Wartende Deploy-Freigaben (täglich)“ (`worker_freigabe_wache.py --check` → `::warning` bei 1, `::error` bei 2)

Beide Schritte hängen an `!cancelled()`, damit ein vorheriger Befund den nächsten nicht verschluckt, und ihr Pfadfilter nennt Wache und Tests — eine Änderung an ihnen löst diesen Lauf aus (Trigger-Wache W1).

Der Alerting-Kanal selbst ist seit 30.10.2026 10:36 UTC wieder gesund: Nach dem Merge von PR #956 (Fix doppelter `const workerZugangFailed`) sind die Meldeläufe grün; #922 wird seitdem mit jedem roten Deploy-Lauf nachgeführt („Mit dem jüngsten Lauf nachgeführt“ — Zeit, Run-Link und rote Schritte sind aktuell: Run 41417750214).

---

## 3. Dauerhafte technische Heilung (seit 01.11. vollständig, heute re-verifiziert)

Keine neue Code-Änderung war nötig — die Heilung hat den dritten Betriebstag ohne Regression überstanden. Die Nachprüfung ist die Heilung.

### H-A · Gate und Einrichter — lesen, beziffern, nur verschärfen

| Baustein | Datei | Aufgabe |
|---|---|---|
| **Gate** | `scripts/worker_environment_guard.py` | Read-only-Prüfer vor jedem Secret-Zugriff. Drei Bedingungen, je eine Annotation, Exit 1 bei Abweichung, Exit 2 bei nicht belegbar (C33). Selbsttest 7 Fälle. |
| **Einrichter** | `scripts/worker_environment_einrichten.py` | Stellt her, was eine API annimmt (Reviewer, Branch-Policy `main`), beziffert den Rest (Admin-Bypass = OBERFLÄCHE). Klassen ERFUELLT / MACHBAR / OBERFLAECHE / ABWEICHUNG / OFFEN, je genau ein nächster Schritt. Nur verschärfend (kein DELETE), idempotent, geheimnisfrei, Endpunkt-grenzfest (`api.github.com`, nur `cloudflare-produktion`), 11 Selbsttest-Fälle + 30 Vertragstests. |
| **Drift-Blick** | `.github/workflows/sicherheits-wache.yml` | Täglicher `—pruefen —warnstufe`-Schritt mit `actions: read`, vor Artefakt-Upload. Warnstufe statt Dauer-Rot, weil der Zustand im Repository nicht herstellbar ist. |

Befehle (identisch zu 30.10./01.11., heute erneut ausgeführt):

```bash
npm run worker:environment                          # --pruefen
python3 scripts/worker_environment_einrichten.py --pruefen --warnstufe --md "$GITHUB_STEP_SUMMARY"
python3 scripts/worker_environment_einrichten.py --anwenden --reviewer frank-hartung  # → 403 Rechtebefund
python3 scripts/worker_environment_einrichten.py --inventur       # alle 5 Environments, hier nur eines relevant
python3 scripts/worker_environment_einrichten.py --selftest       # 11 Fälle, offline
```

### H-B · Zugangs-Dossier — ein Lauf sagt alles

```bash
python3 scripts/worker_zugang.py --pruefen --worker newsletter-worker --md "$GITHUB_STEP_SUMMARY"
python3 scripts/worker_zugang.py --pruefen --worker klick-zaehler  # gleiche Prüfung, zweite Ressource
python3 scripts/worker_ressourcen.py --aufloesen newsletter-worker # lesend, ohne neuen Speicher
```

`worker_zugang.py` sammelt **alle** Befunde in einem Durchgang (Token fehlt/ungültig/zu schwach, Konto-ID fehlt/falsch, Bindung fehlt/mehrdeutig, Netzstörung), schreibt ein Inhaber-Dossier in die Step Summary und meldet je Befund genau eine Annotation. `worker_ressourcen.py` bleibt Autorität für die IDs, bricht bei fehlender/mehrdeutiger Bindung fail-closed rot ab und legt nie einen neuen Speicher an (Vergleich `ff-newsletter` ABO / `klick-zaehler` DB). Ohne diesen Dossier-Schritt kostete jedes Feld eine eigene Freigabe-Runde (Run 40569123622, 27.10.).

Prüfknopf ohne Deploy: Actions → **„Deploy-Zugang prüfen“** → *Run workflow* (`main`, Environment `cloudflare-produktion`). Derselbe Dossier-Lauf, kein Wrangler, kein Deploy, überwacht (steht auf der Wacht-Liste des Fehler-Alertings — ein stiller Kanal wäre die Wiederholung von #922).

### H-C · Freigabe-Wache — der zweite Schritt nach dem Einrichten

```bash
npm run worker:freigabe                            # --check, Schwelle 120 Minuten
python3 scripts/worker_freigabe_wache.py --check --schwelle 45 --md -
python3 scripts/worker_freigabe_wache.py --selftest       # 20 Fälle, offline
python3 -m unittest scripts.tests.test_worker_freigabe_wache  # 23 Verträge
```

Sechs Entscheidungen, jede durch einen Test belegt:

1. **Nur zwei Ketten** (`worker-deploy.yml`, `worker-zugang-pruefen.yml`) — kein allgemeiner Lauf-Monitor.
2. **Drei Wartezustände, ein Mensch** (`waiting`, `pending`, `action_required`) zählen als Warten; `queued`/`in_progress`/`completed`/`cancelled` nicht.
3. **Junge Wartung ist still** — unter der Schwelle (120 min Standard) ist Warten normal; gemeldet wird erst, was niemand mehr im Blick hat.
4. **Nicht belegbar ist nicht in Ordnung** (C33): unlesbare Antwort, HTTP 401/403/404/500, kaputtes JSON, Lauf-ID die keine ist, Zeitstempel in der Zukunft → Exit 2, nie Grün.
5. **Geheimnisfrei und ohne Fremdlink** — Token nur im Header; Lauf-Link wird aus geprüfter Repo-Angabe und geprüfter Lauf-ID selbst gebaut, nie aus `html_url` übernommen (Selbsttest K5/K9).
6. **Read-only** — ausschließlich `GET …/actions/workflows/<name>.yml/runs?per_page=30`, Weiterleitungen abgelehnt, Pfad und Parameter festgenagelt (`per_page=30`). Freigeben/Brechen bleibt Menschenhandlung.

Täglicher Schritt in `sicherheits-wache.yml`: Exit 0 = grün, Exit 1 = `::warning` + `exit 0` (offene Entscheidung, kein Defekt — Link in der Zusammenfassung: „freigeben oder abbrechen — blockiert Concurrency-Slot und hält Nachweis für #922 offen“), Exit 2 = `::error` + `exit 1` (nicht belegbar).

### H-D · Dokumentation und Verträge

| Ort | Inhalt seit 01.11. | Re-verifiziert 03.11. |
|---|---|---|
| `docs/SICHERHEIT-BETRIEB-RUNBOOK.md` A4 | „Die Freigabe ist ein Klick — und der Wartezustand ist bewacht“ (Freigeben per Oberfläche + per `gh api`, Abbrechen, Exit-Bedeutung) | unverändert, Pfad filtert |
| `docs/SICHERHEIT-BETRIEB-RUNBOOK.md` D2 | Schritt 3 nennt den Halt und seine Meldung | ok |
| `package.json` | `worker:environment`, `worker:freigabe`, `test:worker:environment`, `test:worker:freigabe`; `test:sicherheit` führt alle | ok |
| `.github/workflows/sicherheits-wache.yml` | Pfadfilter (push + pull_request) + Offline-Job (Selbsttests + 23 Vertragstests) + 2 tägliche Live-Schritte | 98 Workflows, 0 Befunde (Trigger-Wache) |
| `scripts/governance_contract.py` | `worker_freigabe_wache.py` im vertraglichen Minimum (C6) | 43 Regeln grün |
| `scripts/alert_issue_identity.py --tabelle` | Zuordnung `WF-829B ↔ worker-deploy-zugang` | Teil der Alert-On-Failure-Simulationen |

**Der harte Stopp ist unantastbar:** Kein Schritt überspringt den Deploy-Job, keine Bedingung wird gelockert. Warnstufe betrifft ausschließlich Zustände, die das Repository nicht herstellen kann — Dauer-Rot dort wäre ein Alarm ohne Schließpfad (C14).

---

## 4. Verifikation (03.11.2026, 09:00–09:15 UTC — alle Werte live, alle Selbsttests offline)

| Prüfung | Ergebnis 03.11. |
|---|---|
| `python3 scripts/worker_environment_guard.py --selftest` | ✅ Exit 0 — 7 Fälle (korrekte Policy akzeptiert, 4 unsichere/unklare Zustände fail-closed) |
| `python3 -m unittest scripts.tests.test_worker_environment_guard` | ✅ 17 Tests OK |
| `python3 scripts/worker_environment_einrichten.py --selftest` | ✅ Exit 0 — 11 Fälle (Zuordnung, OFFEN nie grün, Endpunktgrenzen, Nur-Verschärfen, Idempotenz, Rechtebefund, Geheimnisfreiheit) |
| `python3 -m unittest scripts.tests.test_worker_environment_einrichten` | ✅ 30 Tests OK |
| `python3 scripts/worker_zugang.py --selftest` | ✅ Exit 0 — 10 Fälle (Sammelbefund, Klassen, Maskierung, Endpunktgrenzen) |
| `python3 -m unittest scripts.tests.test_worker_zugang` | ✅ 43 Tests OK |
| `python3 scripts/worker_ressourcen.py --selftest` | ✅ Exit 0 — produktive Bindung aufgelöst, kein neuer Speicher |
| `python3 -m unittest scripts.tests.test_worker_ressourcen` | ✅ OK |
| `python3 scripts/worker_deploy_vorbereiten.py --selftest` | ✅ Exit 0 — Variablen, ID-Format, `workers_dev = false`, Plan-Schutz |
| `python3 -m unittest scripts.tests.test_worker_deploy_vorbereiten` | ✅ OK |
| `python3 scripts/worker_freigabe_wache.py --selftest` | ✅ Exit 0 — 20 Fälle (Schwelle minutengenau, 3 Wartezustände, Gegenprobe, Fremdlink, Geheimnisfreiheit, Zukunft ⇒ nicht belegbar) |
| `python3 -m unittest scripts.tests.test_worker_freigabe_wache` | ✅ 23 Tests OK |
| `python3 scripts/alert_resolve_gate.py --selftest` | ✅ Exit 0 — 11 Fälle (Job-Beweis WF-E813 / #809) |
| `python3 -m unittest scripts.tests.test_alert_resolve_gate` | ✅ OK |
| `python3 -m unittest scripts.tests.test_alert_scoping` | ✅ 27 Tests OK (inkl. 3 Zugangsdossier-Simulationen) |
| `GITHUB_TOKEN=… python3 scripts/worker_environment_guard.py --check` | ✅ Exit 1 — fail-closed mit drei Befunden (Reviewer, Branch, Bypass) — **erwartet** solange ungesichert |
| `GITHUB_TOKEN=… python3 scripts/worker_environment_einrichten.py --pruefen` | ✅ Exit 1 — MACHBAR / OBERFLÄCHE / MACHBAR korrekt beziffert |
| `GITHUB_TOKEN=… python3 scripts/worker_freigabe_wache.py --check` | ✅ Exit 0 — kein Lauf wartet über der Schwelle |
| `python3 scripts/wachen_vertrag.py` | ✅ 372 Skripte, 0 Befunde |
| `python3 scripts/trigger_wache.py --check` | ✅ 98 Workflows, 0 Befunde |
| `python3 scripts/skript_syntax_wache.py --check` | ✅ 628 Dateien grün |
| `python3 scripts/governance_contract.py --quick` | ✅ 43 Regeln grün |
| `python3 scripts/governance_contract.py` | ✅ 43 Regeln grün (beide Richtungen) |
| `python3 scripts/worker_betrieb_wache.py --offline` | ✅ Deckel 100/Tag, Bau `ff-newsletter-2026-10-24` |
| `npm run test:sicherheit` | ✅ Exit 0 (13 Selbsttests + 325 Vertragstests + Struktur-Gate) |

Live-Infrastruktur, die aus der Agenten-Sandbox nicht erreichbar ist, wird nicht behauptet: `api.github.com` ist die einzige Netzgrenze dieses Berichts. `/healthz`-Nachweis (`bau == ff-newsletter-2026-10-24`) läuft im Workflow, nicht hier — dort als Schritt hinterlegt, nicht als Behauptung.

---

## 5. Was offen bleibt — Inhaber-Aufgabe, ein Durchgang (unverändert seit 01.11.)

Die Reihenfolge ist so gewählt, dass jeder Schritt den nächsten belegt:

**Schritt 1 — Environment absichern** (Settings → Environments → [`cloudflare-produktion`](https://github.com/frank-hartung/franksfinanzcheck-blog/settings/environments)):

1. *Required reviewers* → **Frank Hartung** (oder ein Team mit Frank).
2. *Deployment branches and tags* → **Selected branches and tags** → Regel `main` (Typ *Branch*), sonst nichts.
3. *Allow administrators to bypass configured protection rules* → **aus** (`can_admins_bypass: false`).

Schritt 1 ist der einzige, den keine API stellen kann — `can_admins_bypass` bleibt Handarbeit (REST: `additionalProperties: false`; GraphQL: Feld unbekannt). Punkte 1 und 2 nimmt die API an, das Agenten-Token darf sie aber nicht schreiben (403). Mit einem Token, das `Environments: read/write` darf, genügt stattdessen:

```bash
export GITHUB_TOKEN=…  # feingranular Environments: read/write, klassisch repo
python3 scripts/worker_environment_einrichten.py --anwenden --reviewer frank-hartung
# → ergänzt Reviewer, setzt Branch-Regel `main`, lässt bestehende Reviewer stehen
npm run worker:environment  # muss danach Exit 0 melden
```

**Schritt 2 — Deploy starten:** Actions → **„Cloudflare-Worker deployen“** → *Run workflow* (`newsletter-worker`, `main`). Der Lauf benötigt eine Freigabe im Environment `cloudflare-produktion`.

**Schritt 3 — Freigeben:** Der Job `deploy` hält an (*Review deployments*). Freigeben ist die gewollte Handlung:

```bash
R=frank-hartung/franksfinanzcheck-blog
gh api "repos/$R/actions/runs/<run_id>/pending_deployments"        # environment_ids lesen
gh api -X POST "repos/$R/actions/runs/<run_id>/pending_deployments" \
  -F environment_ids[]=<id> -f state=approved -f comment="Produktionsdeploy freigegeben"
# Abbrechen ginge mit state=rejected — ebenfalls legitimer Ausgang.
```

**Abschluss:** Zwei grüne Deploy-Jobs, `/healthz` liefert `bau == ff-newsletter-2026-10-24`, und `scripts/alert_resolve_gate.py` bestätigt den Job-Beweis. Erst dann schließt #922 automatisch — ein grüner Plan, ein grüner Zugangs-Check oder dieser Bericht schließen ihn ausdrücklich **nicht**. Ein vorheriger Prüfknopf empfiehlt sich:

```bash
Actions → „Deploy-Zugang prüfen“ → Run workflow (main)  # read-only Dossier, alle Befunde auf einmal
```

Bis dahin ist der Zustand **bekannt und bewacht**, nicht unbekannt und still: Der tägliche Lauf meldet den Freigabestand (Warnstufe) und jeden Deploy, der auf einen Menschen wartet — mit Link.

---

## 6. Grenzen dieser Heilung (bewusst benannt)

- **Der Bypass-Schalter bleibt Handarbeit.** Kein Werkzeug und kein Token in diesem Repository kann ihn setzen; die Belege stehen in Abschnitt 2.2. Wer etwas anderes behauptet, hat es nicht gemessen.
- **Die Wache prüft den Zustand, nicht die Absicht.** Sie sagt „dieser Lauf wartet seit X Minuten“, nicht „diese Freigabe war richtig“. Die Entscheidung bleibt beim Menschen — deshalb Warnstufe und Schließpfad statt Automatik.
- **Die Wache gibt nichts frei und bricht nichts ab.** Ein Werkzeug, das seine eigene Freigabe erteilt, wäre die Freigabe, die es bewacht.
- **`/healthz` ist aus der Agenten-Sandbox nicht erreichbar** (nur `github.com`/`api.github.com` sind offen). Die Endabnahme läuft deshalb im Workflow — dort als Schritt hinterlegt, nicht als Behauptung.
- **Der Abschluss braucht einen Menschen.** Jeder Deploy nach Schritt 1 hält an; das ist die gewollte Wirkung des Schutzes, den dieser Vorgang verlangt. Wer sie nicht will, will den Schutz nicht — dann ist die Entscheidung zu ändern, nicht die Anzeige.
- **Nichts wurde gelockert, um Grün zu erzeugen.** Das Gate steht vor jedem Secret-Zugriff, der Resolver legt nie einen neuen Speicher an, die Wache leitet kein Token weiter und lernt keinen Fremdlink. Ein Skript, das hier „repariert“, repariert das Falsche.

---

*Geheilt, gemessen und dokumentiert am 03.11.2026 — dritte Live-Messung ohne Drift, zweite Bestätigung des Rechtebefunds (403), null Wartende über der Schwelle, alle Selbst- und Vertragstests grün.*
