# Wartung · Veröffentlichung · Vorgang WF-829B (#922) — Highend-Dauerheilung, 01.11.2026

**Vorgang:** WF-829B · **Issue:** [#922](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/922)
**Auftrag:** dauerhaft auf Highend-Level einer Profi-Agentur beheben
**Stand der Messungen:** 01.11.2026, 09:20–09:45 UTC · alle Werte live abgefragt
**Vorberichte:** `…-2026-10-29.md` (Zugangsdossier) · `…-2026-10-30.md` (Einrichter + Kanal-Probe)

---

## 1. Kurzfassung

Der Vorgang ist an dem Punkt, an dem die beiden Vorberichte ihn verlassen
haben — und das ist eine Nachricht, keine Wiederholung: **Das Repository kann
diesen Schalter nicht stellen.** Heute wurde das zum zweiten Mal gemessen
(HTTP 403, Abschnitt 2.1). Der Inhaber hat deshalb entschieden, das
Environment selbst zu sichern. Damit fällt dem Repository genau eine Aufgabe
zu, und die ist bisher offen:

> Nach dem Setzen der Freigabe hält **jeder** Worker-Deploy an, bis ein Mensch
> ihn freigibt. Ein solcher Lauf wird nicht rot. Er meldet nichts, er altert
> nur — und belegt dabei den Concurrency-Slot `worker-deploy`. Der nächste
> Push reiht sich dahinter ein, der Nachweis für #922 entsteht nie, und
> niemand hat einen Anlass nachzusehen.

Das ist die Lehre vom 24.10.2026 („stiller Nicht-Deploy“) in neuer Form: nicht
der laute Ausfall fehlt, sondern der leise. Diese Heilung macht ihn sichtbar,
mit Schließpfad und mit Lauf-Link.

| Nr. | Befund | Heilung | Stand |
|---|---|---|---|
| **A** | Die Freigabe ist weiterhin nicht gesetzt; ein Schreibversuch scheitert mit **403** | Nicht im Repository heilbar. Gemessen, beziffert, mit exakter Klickfolge (Abschnitt 5) | **Inhaber**, 3 Schalter + 1 Knopf + 1 Freigabe |
| **B** | Nach der Freigabe-Regel wartet jeder Deploy — **unsichtbar**, ohne Meldung, mit blockiertem Concurrency-Slot | `scripts/worker_freigabe_wache.py` + täglicher Schritt „Wartende Deploy-Freigaben“ | **geheilt** (20 Selbsttest-Fälle, 23 Vertragstests) |
| **C** | Der Wartezustand war nirgends dokumentiert — Runbook nannte nur das Einrichten, nicht das Freigeben | Runbook A4 „Die Freigabe ist ein Klick“ + D2-Schritt 3, CLAUDE.md-Abschnitt | **geheilt** |

**Der harte Stopp bleibt unangetastet.** Kein Schritt überspringt den
Deploy-Job, keine Prüfung wird zur Warnung herabgestuft, keine Bedingung des
Gates wird gelockert. Was hinzukommt, ist ausschließlich eine **lesende**
Wache auf einem Zustand, den es nach dem Einrichten zwangsläufig gibt.

---

## 2. Forensischer Ist-Befund (live gemessen, nicht zitiert)

### 2.1 Defekt A · Das Environment ist unverändert — und Schreiben ist ein Rechtebefund

`GET /repos/frank-hartung/franksfinanzcheck-blog/environments/cloudflare-produktion`,
01.11.2026:

```json
{"id":25274969424,"name":"cloudflare-produktion",
 "created_at":"2026-10-25T13:20:15Z","updated_at":"2026-10-25T13:20:15Z",
 "can_admins_bypass":true,"protection_rules":[],"deployment_branch_policy":null}
```

Vier Aussagen in einem Objekt:

1. **Kein Required Reviewer** (`protection_rules: []`).
2. **Keine Branch-Regel** (`deployment_branch_policy: null`) — jeder Branch
   dürfte dieses Environment anfordern.
3. **Admin-Bypass aktiv** (`can_admins_bypass: true`).
4. **`created_at == updated_at` (25.10.2026 13:20:15 UTC)** — seit der
   automatischen Anlage hat niemand dieses Environment konfiguriert. Es ist
   kein verlorener Schutz, es ist ein **nie eingerichteter**.

Der Schreibversuch von hier, am selben Tag erneut ausgeführt:

```text
PUT  /repos/…/environments/wf829b-probe        → 403  "Resource not accessible by integration"
POST /repos/…/actions/workflows/<id>/dispatches → 403  "Resource not accessible by integration"
```

Damit sind **zwei** Grenzen gleichzeitig belegt: Dieses Token darf weder
Environments schreiben noch Workflows auslösen. Beides ist ein
**Rechtebefund**, keine Code-Regression — und beides heißt: Der letzte
Handgriff und der letzte Knopf gehören einem Menschen. Wer hier „Skript
reparieren“ liest, repariert das Falsche.

### 2.2 Defekt B · Die zweite Stufe hat keinen Melder

Die Deploy-Kette besteht aus drei Jobs: `plan` → `production-policy`
(read-only-Gate, `actions: read`, keine Secrets) → `deploy` (Environment,
Cloudflare-Secrets, Wrangler). Mit Required Reviewer und
`can_admins_bypass: false` endet der dritte Job **vor** dem ersten Schritt in
`waiting` — für GitHub ein normaler Vorgang, für den Betrieb ein schwarzes
Loch:

- Der Lauf erscheint **nicht rot**. Kein Alerting greift, weil es nichts zu
  alarmieren gibt.
- Er blockiert den Concurrency-Slot `worker-deploy`
  (`cancel-in-progress: false`) — nachfolgende Deploys warten mit.
- `#922` bleibt offen, weil der Abschluss zwei **grüne** Deploy-Jobs verlangt
  (`scripts/alert_resolve_gate.py`).
- Die Sicherheits-Wache sah bisher nur den **Freigabestand** des Environments
  (Schritt „Produktions-Environment – Freigabestand und Drift“), nicht die
  Läufe, die auf ihn warten.

Genau die Lage, die am 24.10.2026 teuer war: Ein Zustand, der nirgendwo
auffällt, weil er nicht scheitert.

---

## 3. Dauerhafte technische Heilung

### H-A · `scripts/worker_freigabe_wache.py` — der Wartezustand wird ein Befund

```bash
npm run worker:freigabe                        # Standard-Schwelle 120 Minuten
python3 scripts/worker_freigabe_wache.py --check --schwelle 45 --md -
python3 scripts/worker_freigabe_wache.py --selftest   # 20 Fälle, offline
```

Sechs Entscheidungen, jede durch einen Test belegt:

1. **Nur zwei Ketten.** Gelesen werden ausschließlich die Läufe von
   `worker-deploy.yml` und `worker-zugang-pruefen.yml` — genau die, die das
   Environment anfordern. Kein allgemeiner Lauf-Monitor.
2. **Drei Zustände, ein Mensch.** `waiting` (Required Reviewer), `pending`
   (Deployment-Protection) und `action_required` (manueller Eingriff) zählen
   als Warten. `queued`, `in_progress`, `completed` und `cancelled` nicht.
3. **Junge Wartung ist still.** Unter der Schwelle (Standard 120 Minuten) ist
   Warten normal; gemeldet wird erst, was niemand mehr im Blick hat. Ein
   Dauer-Alarm über einen normalen Vorgang wäre die unbezahlte Rechnung aus
   #912.
4. **Nicht belegbar ist nicht in Ordnung (C33).** Unlesbare Antwort, HTTP
   401/403/404/500, kaputtes JSON, Lauf-ID, die keine ist, Zeitstempel in der
   Zukunft: **Exit 2**, nie Grün.
5. **Geheimnisfrei und ohne Fremdlink.** Das Token steht ausschließlich im
   Header; der Lauf-Link wird aus geprüfter Repository-Angabe und geprüfter
   Lauf-ID **selbst gebaut**, nie aus `html_url` der Antwort übernommen. Eine
   präparierte API-Antwort kann damit keinen Link in einen Lauf schmuggeln
   (Selbsttest K5/K9).
6. **Read-only.** Ausschließlich `GET` auf die Läufe-Liste; Weiterleitungen
   werden abgelehnt, der Pfad ist auf `/repos/<repo>/actions/workflows/<name>.yml/runs`
   festgenagelt (`per_page=30`, kein weiterer Parameter). Freigeben und
   Abbrechen bleiben Handlungen eines Menschen.

Ausgabe: eine Warnung mit Alter, Lauf-ID und Link plus Markdown-Abschnitt mit
Tabelle für die Job-Zusammenfassung. Beispiel aus dem Selbsttest:

```text
Lauf 41056313716 (worker-deploy.yml) wartet seit 360 Minuten auf Freigabe
(Schwelle 120): https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/41056313716
```

### H-B · Täglicher Blick in der Sicherheits-Wache

`.github/workflows/sicherheits-wache.yml`, Job **Live-Messung**, neuer Schritt
„Wartende Deploy-Freigaben (täglich)“ direkt nach dem Freigabestand — vor dem
Artefakt-Upload. Der Job hat `permissions: {actions: read, contents: read}`;
mehr braucht diese Wache nicht.

| Exit | Wirkung | Warum |
|---|---|---|
| `0` | grün | nichts wartet über der Schwelle |
| `1` | `::warning` + `exit 0` | offene **Entscheidung**, kein Defekt — der Schließpfad ist „freigeben oder abbrechen“ |
| `2` | `::error` + `exit 1` | Zustand nicht belegbar (Netz, Rechte) — ungeprüft ist nicht sauber |

Der Schritt hängt an `!cancelled()`, damit ein vorheriger Befund die Meldung
nicht verschluckt. Der Pfadfilter nennt Wache und Test, damit eine Änderung an
ihr diesen Lauf auch auslöst (Trigger-Wache W1).

### H-C · Der Rat bleibt am Befund

Beide Meldewege nennen den nächsten Schritt, nicht nur den Zustand: die
Warnung sagt „freigeben (*Review deployments*) oder abbrechen — der Lauf
blockiert den Concurrency-Slot und hält den Nachweis für #922 offen“, die
Zusammenfassung sagt dasselbe mit Lauf-Link.

### H-D · Verträge und Dokumentation

| Ort | Änderung |
|---|---|
| `scripts/governance_contract.py` | `worker_freigabe_wache.py` im vertraglichen Minimum (C6): Eine Wache, die niemand verlangt, führt irgendwann niemand aus |
| `package.json` | `worker:freigabe`, `test:worker:freigabe`; `test:sicherheit` führt Selbsttest und Vertragstests mit |
| `.github/workflows/sicherheits-wache.yml` | Pfadfilter (push + pull_request), Offline-Job (Selbsttest + 23 Vertragstests), täglicher Live-Schritt |
| `docs/SICHERHEIT_BETRIEB-RUNBOOK.md` | **A4** „Die Freigabe ist ein Klick — und der Wartezustand ist bewacht“ (Freigeben per Oberfläche und per API, Abbrechen, Exit-Bedeutung) · **D2** Schritt 3 nennt den Halt und seine Meldung |
| `CLAUDE.md` | Abschnitt „Ein wartender Deploy ist kein grüner Deploy“ (Entscheidung, Preis, Wache, Abschlusskriterium) |

---

## 4. Verifikation

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/worker_freigabe_wache.py --selftest` | **Exit 0** — 20 Fälle (Schwelle minutengenau, drei Wartezustände, Gegenprobe, Fremdziel, Geheimnisfreiheit, Zukunft ⇒ nicht belegbar) |
| `python3 -m unittest scripts.tests.test_worker_freigabe_wache` | **23 Tests OK** |
| `python3 scripts/worker_freigabe_wache.py --check` (live) | **Exit 0** — „Kein Lauf wartet über der Schwelle auf eine Freigabe“ |
| `python3 scripts/worker_environment_guard.py --selftest` | **Exit 0** |
| `python3 scripts/worker_environment_einrichten.py --selftest` | **Exit 0** |
| `python3 scripts/worker_zugang.py --selftest` | **Exit 0** |
| `python3 scripts/worker_ressourcen.py --selftest` | **Exit 0** |
| `python3 scripts/worker_deploy_vorbereiten.py --selftest` | **Exit 0** |
| `python3 scripts/wachen_vertrag.py` | **368 Skripte, 0 Befunde** |
| `python3 scripts/skript_syntax_wache.py --check` | **618 Dateien grün** |
| `python3 scripts/trigger_wache.py --check` | **98 Workflows, 0 Befunde** |
| `python3 scripts/governance_contract.py --quick` | **43 Regeln** prüfen in beide Richtungen |
| `python3 scripts/ki_transportweg.py --selftest` | grün (16 Sabotage- + 2 Driftproben) |
| `npm run manifest:check` | **GRÜN** |
| `npm run test:sicherheit` | **Exit 0** |

Die fünf Selbsttests der Deploy-Kette sind Teil dieses Berichts, weil sie die
Frage beantworten, die nach dem Klick zählt: **Gibt es außer der Freigabe noch
eine zweite Landmine?** Gemessen: nein — Plan, Zugangsdossier, Ressourcen-
Resolver, Vorbereitung und Gate sind offline grün. Was sie nicht beweisen
können, ist der Cloudflare-Zugang selbst; der wird erst im Lauf lesend geprüft
und benennt jedes fehlende Feld in **einem** Durchgang.

---

## 5. Was offen bleibt — drei Schalter, ein Knopf, eine Freigabe

Die Reihenfolge ist so gewählt, dass jeder Schritt den nächsten belegt.

**Schritt 1 — Environment absichern** (Settings → Environments →
[`cloudflare-produktion`](https://github.com/frank-hartung/franksfinanzcheck-blog/settings/environments)):

1. *Required reviewers* → **Frank Hartung**.
2. *Deployment branches and tags* → **Selected branches and tags** → Regel
   `main` (Typ *Branch*), sonst nichts.
3. *Allow administrators to bypass configured protection rules* → **aus**.

Schritt 1 ist der einzige, den keine API stellen kann (`can_admins_bypass`);
die Punkte 1 und 2 nimmt die API an, dieses Token darf sie aber nicht schreiben
(403). Nach dem Klick prüft `npm run worker:environment` den Stand und muss
`0` melden.

**Schritt 2 — Deploy starten:** Actions → **„Cloudflare-Worker deployen“** →
*Run workflow* (`newsletter-worker`, `main`).

**Schritt 3 — Freigeben:** Der Job `deploy` hält an (*Review deployments*).
Freigeben ist die gewollte Handlung, nicht die Ausnahme:

```bash
R=frank-hartung/franksfinanzcheck-blog
gh api "repos/$R/actions/runs/<run_id>/pending_deployments"        # environment_ids lesen
gh api -X POST "repos/$R/actions/runs/<run_id>/pending_deployments" \
  -F environment_ids[]=<id> -f state=approved -f comment="Produktionsdeploy freigegeben"
```

**Abschluss:** zwei grüne Deploy-Jobs, `/healthz` liefert den Build-Stempel
aus `wrangler.toml` (`ff-newsletter-2026-10-24`), und
`scripts/alert_resolve_gate.py` bestätigt es. Erst dann schließt #922 — ein
grüner Plan, ein grüner Zugangs-Check oder dieser Bericht schließen ihn
ausdrücklich **nicht**.

Bis dahin ist der Zustand **bekannt und bewacht**, nicht unbekannt und still:
Der tägliche Lauf meldet den Freigabestand (Warnstufe) und seit heute auch
jeden Deploy, der auf einen Menschen wartet — mit Link.

---

## 6. Grenzen dieser Heilung (bewusst benannt)

- **Der Bypass-Schalter bleibt Handarbeit.** Kein Werkzeug und kein Token in
  diesem Repository kann ihn setzen; die Belege stehen in Abschnitt 2.1. Wer
  etwas anderes behauptet, hat es nicht gemessen.
- **Die Wache prüft den Zustand, nicht die Absicht.** Sie sagt „dieser Lauf
  wartet seit X Minuten“, nicht „diese Freigabe war richtig“. Die Entscheidung
  bleibt beim Menschen — deshalb Warnstufe und Schließpfad statt Automatik.
- **Die Wache gibt nichts frei und bricht nichts ab.** Ein Werkzeug, das seine
  eigene Freigabe erteilt, wäre die Freigabe, die es bewacht.
- **`/healthz` ist aus der Agenten-Sandbox nicht erreichbar** (nur
  github.com/api.github.com sind offen). Die Endabnahme läuft deshalb im
  Workflow, nicht in diesem Bericht — sie ist dort als Schritt hinterlegt und
  nicht als Behauptung.
- **Der Abschluss braucht einen Menschen.** Jeder Deploy nach Schritt 1 hält
  an; das ist die gewollte Wirkung des Schutzes, den dieser Vorgang verlangt.
  Wer sie nicht will, will den Schutz nicht — dann ist die Entscheidung zu
  ändern, nicht die Anzeige.
