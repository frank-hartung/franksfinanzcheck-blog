# Wartung · Sicherung · WF-9E5A #923 — Highend-Dauerheilung (07.11.2026)

**Auftrag:** `Wartung · Sicherung · Vorgang WF-9E5A #923 — dauerhaft auf Highend-Level einer Profi-Agentur beheben, mit automatischer Selbstheilung.`
**Branch:** `arena/41cd7103-franksfinanzcheck-blog` · **Basis:** `4d60e220` (`main`, 07.11.2026, 08:40 UTC)
**Bearbeiter:** Arena Agent · **Vorgänger:** `WARTUNG-BACKUP-WF-9E5A-HIGHEND-2026-11-03.md`

---

## 1. Was heute anders ist als in den fünf Berichten davor

Die Vorgängerberichte haben die Signalkette um den Vorgang herum geheilt — richtige
Klasse, richtiger Rat, richtiger Schlie&szlig;pfad. Das war nötig und ist belegt. Heute
ging der Blick auf die **Gegenprobe der Selbstheilung selbst**: Wo behauptet das
System Erfolg, ohne geprüft zu haben — und wo wartet es auf einen Menschen, obwohl
die Reparatur **ohne jeden Zugang** möglich wäre?

Zwei Antworten, beide live belegt, beide heute geschlossen:

1. **Der grüne Leerlauf.** Der Job „backup" meldet `success`, während weder
   `BACKUP_REPO` noch `BACKUP_PASSPHRASE` gesetzt sind. Er sichert dann nichts
   Dauerhaftes — nur eine 7-Tage-Kurzzeitkopie im **selben** Konto. Diese Wahrheit
   stand bis heute ausschließlich im Lauf-Log. Kein Alarm, keine Klasse, kein Rat.
2. **Der übersprungene Nachweis.** Der Rückweg-Nachweis („Kurzprüfung
   Wiederherstellbarkeit") stand in **sechs aufeinanderfolgenden** Frischwache-Läufen
   als `skipped` im Lauf — nicht als Fehler, nicht als Erfolg, sondern als **Lücke**.
   Ursache: GitHubs Standardbedingung `success()`.

Und für den dritten Befund gibt es jetzt zum ersten Mal echte **Selbstheilung** —
mit Beweis, nicht mit Zusage:

3. **Der fehlende Lauf.** Seit dem 15.10. startet der nächtliche Lauf nicht um
   03:00 UTC, sondern zwischen **07:37 und 10:28 UTC** (24 Läufe gemessen). Die
   Workflow-Datei ist in Ordnung; es fehlt der Lauf. Ein Dispatch holt ihn nach —
   und der **Beweis** ist ein neuer Lauf in der Läufe-Liste. Das „HTTP 204" der API
   zählt ausdrücklich nicht.

## 2. Live-Befund (07.11.2026, gegen die echte GitHub-API)

| Prüfung | Ergebnis |
|---|---|
| Offsite-Lauf `42359904795` (07.11., 09:28 UTC) | Job `KV-/D1-Backup` **failure** in „Voraussetzungen prüfen" (gewollt, Einrichtung fehlt) · Job `backup` **success** |
| Annotationen des **grünen** Jobs | „Kein dauerhaftes Offsite-Ziel gesetzt" + „Kein BACKUP_PASSPHRASE" — **beide** aus dem Lauf gelesen (`check-runs/…/annotations`) |
| Einrichtungsprüfung (live, `--pruefen`) | E1, E2, E3, E4, E5, E6 offen · E7 optional · E8 offen (`protection_rules: []`, `deployment_branch_policy: null`) |
| 24 Läufe 15.10.–07.11. | **alle** `failure`; Startzeiten 07:37–10:28 UTC (Soll 03:00 UTC) |
| Frischwache: 6 Läufe 03.–06.11. | **alle** `failure`; „Kurzpruefung Wiederherstellbarkeit" **jeweils `skipped`** |
| Schreib-Endpunkte (Variable/Secret/Environment) | `403 Resource not accessible by integration` — erneut geprüft, nichts erfunden, nichts gesetzt |
| Ziel-Repository `frank-hartung/franksfinanzcheck-backup` | **404** — existiert nicht |

Damit ist die Grenze sauber gezogen: **Die Inhaber-Einrichtung (E1–E8) ist und
bleibt der einzige funktionale Blocker** — und *alles andere* ist heute heilbar
gewesen.

## 3. Der Selbstfund in meiner eigenen ersten Fassung

Das gehört in diesen Bericht, weil er die Klasse zeigt, gegen die hier gebaut wird.

Die erste Fassung von `pruefe_leerlauf()` maß `workflow_runs[].conclusion` — also
den **Gesamtlauf**. Am Lauf `42359904795` ist der Gesamtlauf `failure` (der KV-Job
ist rot), der Job „backup" darin aber `success`. Eine Messung auf Lauf-Ebene hätte
den Befund „grün, aber nichts gesichert" **ausgerechnet an dem Tag verschluckt, an
dem er zutraf**.

Gefunden hat das nicht die Review, sondern der **erste Live-Lauf des Moduls**: Der
Plan meldete „einrichtung, scheinbeweis" — ohne `leerlauf`, obwohl ich den Befund
Minuten vorher aus den Annotationen zitiert hatte. Die Korrektur ist die Regel:

> **Miss die Höhe, auf der die Aussage steht.** „Wurde gesichert?" ist eine
> Job-Aussage, keine Lauf-Aussage.

Die Verträge halten jetzt beide Richtungen fest (`test_leerlauf_wird_auf_job_ebene_gemessen`),
inklusive der Gegenprobe, dass der KV-Job **nicht** als Zeuge taugt (er legt nach
Audit M-11 bewusst nie ein Artefakt an).

## 4. Die Heilungen

### H-01 · Selbstheilung als eigener Baustein — `scripts/backup_selbstheilung.py` (neu)

Drei Regeln, im Kopf der Datei und im Vertrag:

| Regel | Inhalt |
|---|---|
| **H1** Nur reparieren, was **beweisbar** kaputt ist | Ein Befund ohne `beleg` ist nie heilbar (F12) |
| **H2** Nur reparieren, was **ohne Zugang** reparierbar ist | Heilbare Klassen: **genau** `scheduler`. E1–E8 ausdrücklich nicht (F19/Vertrag) |
| **H3** Heilung ist eine **Aktion mit Beweis** | Dispatch + Erfolgsprüfung über die Läufe-Liste; „angenommen" ≠ bewiesen (F13–F15) |

Klassen: `scheduler` (heilbar, Dispatch), `leerlauf`, `scheinbeweis`, `einrichtung`
(nicht heilbar — beraten, nicht „lösen"). Exit-Codes: 0 nichts zu tun · 1 heilbar,
Beweis ausgeblieben (rot) · 3 Inhaber-Schritt · 4 Leerlauf.

**Wichtige Ehrlichkeit im Code:** Ist die Einrichtung offen, hat **sie** Vorrang
(Exit 3). Der Leerlauf ist dann die *Folge*, nicht die Ursache — zwei Rot-Stellen für
eine Ursache wären Lärm. Erst bei vollständiger Einrichtung wird der Leerlauf zur
Spitze (Exit 4), weil er dann eine Sicherung vortäuscht, die es nicht gibt.

### H-02 · Der übersprungene Nachweis wird ausgeführt — `backup-frischwache.yml`

Der Schritt „Kurzpruefung Wiederherstellbarkeit" läuft jetzt mit `if: ${{ !cancelled() }}`
statt unter der impliziten `success()`-Bedingung, und er sagt ehrlich, was er nicht
kann:

```
::warning title=Wiederherstellbarkeit nicht belegbar::Ohne Ziel, Zugang und
Passphrase existiert keine Sicherung, deren Rückweg prüfbar wäre. Geprüft wird
deshalb nur die STRUKTUR …
```

Strukturell prüfbar (Syntax, Selbsttests, Schein-Grün-Gegenprobe) wird geprüft;
nicht Prüfbares wird **benannt** statt verschwiegen. Kein `continue-on-error`, kein
`|| true` — der Rückweg-Nachweis verliert nichts von seiner Schärfe.

### H-03 · Leerlauf wird gemessen und bekommt einen eigenen Rat

- `backup_selbstheilung.py` misst auf **Job-Ebene** (Exit 4, Klasse `leerlauf`).
- `alert-on-failure.yml`: neue Runbook-Klasse **`backup-leerlauf`** mit eigenem
  Drei-Schritt-Rat („Ein Lauf ist grün – und trotzdem ist nichts gesichert"), in der
  Klassenkette **vor** dem allgemeinen Backup-Rat, damit „Datei-Befunde unten" die
  einzige zutreffende Aussage nicht verschluckt.
- Erkennung gebunden an den Schrittnamen `Selbstheilung` und **nicht** an
  „Voraussetzungen prüfen" — sonst wäre der Rat bei offener Einrichtung doppelt
  (dort bleibt `backup-einrichtung` die erste Antwort; Gegenprobe in der Simulation).

### H-04 · Verdrahtung, Rechte, Beweisbarkeit

- Neuer Workflow-Schritt „Selbstheilung (nur Beweisbares – Dispatch mit Lauf-Nachweis)"
  mit `if: ${{ !cancelled() }}` und **ausschließlich** dem Lauf-Token (`github.token`).
- Job-Rechte: `contents: read` + `actions: write` — Letzteres nur zum Starten eines
  Laufs im **eigenen** Repo. Der Vertrag prüft, dass kein weiteres Recht dazukommt
  und dass weder `ZIEL_TOKEN` noch `CF_API_TOKEN` in der Heilung landen.
- Trigger-Pfad `scripts/backup_selbstheilung.py` ergänzt (Trigger-Wache W1: der Lauf
  muss auslösen, was er prüft) — `trigger_wache.py --check`: 100 Workflows, 0 Befunde.
- `governance_contract.GUARDS`: die Heilung steht im vertraglichen Minimum (C6) —
  eine Wache **mit Folgen** braucht einen Selbsttest, der in jedem Gate läuft.
- `npm run backup:heilung` / `backup:heilung:anwenden`.

## 5. Regressionsschutz — beide Richtungen, wie es die Hausdisziplin verlangt

Neu in `scripts/tests/test_backup_einrichtung.py`:
`SelbstheilungVertrag` (7 Tests) und `LeerlaufAlarmVertrag` (2 Tests).

| Vertrag | Inhalt |
|---|---|
| `test_selbsttest_und_vertrag_gruen` | Selbsttest grün **und** ohne eine einzige geleakte `::error::`/`::warning::`-Zeile |
| `test_heilung_laeuft_im_workflow_und_wird_geprueft` | `--heilen` im Workflow, `--selftest` im Selbsttest-Schritt, Pfad im Trigger, Exit-1-Pfad vorhanden |
| `test_rueckweg_nachweis_wird_nicht_mehr_stillschweigend_uebersprungen` | `!cancelled()` statt `success()`, „Nicht prüfbar (ehrlich benannt)" im Rumpf |
| `test_kein_secret_zugriff_fuer_die_heilung` | nur `github.token`; keine Backup-Zugänge im Schritt |
| `test_heilbare_klassen_sind_ausdruecklich_begrenzt` | heilbare Menge **exakt** `{scheduler}`; Inhaber-Klassen mit Begründung |
| `test_einrichtung_wird_nie_erfunden` | kein `gh secret set` / `gh variable set` / `--input -` im Modul |
| `test_leerlauf_wird_auf_job_ebene_gemessen` | grüner `backup`-Job **muss** gemeldet werden; KV-Job taugt nicht als Zeuge |
| `test_eigene_klasse_und_eigener_rat` | `backup-leerlauf` in der Klassenkette, **vor** `backup`, **nach** `backup-einrichtung` |
| `test_verhalten_positiv_und_gegenprobe` | Simulation mit positivem Szenario **und** Gegenprobe |

**Sabotageproben ausgeführt** (jede Heilung einzeln zurückgenommen):

| Sabotage | Ergebnis |
|---|---|
| `einrichtung` auf `heilbar: True` gesetzt | ❌ 2 Fehlschläge (`test_heilbare_klassen_…`, `test_selbsttest_und_vertrag_gruen`) |
| `!cancelled()` vom Rückweg-Nachweis entfernt (= alter `skipped`-Zustand) | ❌ 2 Fehlschläge |
| `--selftest`/`--vertrag` der Heilung aus dem Workflow entfernt | ❌ 2 Fehlschläge |
| `pruefe_leerlauf` auf Lauf-Ebene zurückgedreht | ❌ `test_leerlauf_wird_auf_job_ebene_gemessen` |

## 6. Abnahme (alle Befehle in diesem Stand ausgeführt)

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/backup_selbstheilung.py --selftest` | ✅ 21 Fallgruppen |
| `python3 scripts/backup_selbstheilung.py --vertrag` | ✅ verdrahtet, selbstgeprüft, Grenze dokumentiert |
| `GITHUB_REPOSITORY=… python3 scripts/backup_selbstheilung.py --plan` (live) | ✅ 3 Befunde korrekt: `leerlauf` (aus Job-API), `scheinbeweis` (`skipped`), `einrichtung` (E1–E6) |
| `python3 scripts/kv_backup.py --selftest` | ✅ |
| `python3 scripts/backup_einrichtung.py --selftest` | ✅ 18 Fallgruppen |
| `python3 scripts/backup_freshness_guard.py --selftest` | ✅ 13 Fallgruppen |
| `python3 -m unittest scripts.tests.test_backup_einrichtung` (venv, PyYAML 6.0.3) | ✅ **74 Tests** (64 Bestand + 10 neu) |
| `python3 -m unittest scripts.tests.test_alert_scoping test_alerting_heartbeat` | ✅ **52 Tests** (inkl. Verhaltenssimulation mit 2 neuen Szenarien) |
| `python3 -m unittest discover -s scripts/tests` (volle Suite) | ✅ **5429 Tests**, 22 Skips |
| `python3 scripts/selftest_runner.py` (voller Stack) | ✅ **275 Wachen, 550 Uhr-Proben** |
| `python3 scripts/governance_contract.py` (voll) | ✅ alle 46 Regeln, beide Richtungen |
| `python3 scripts/trigger_wache.py --check` | ✅ 100 Workflows, 0 Befunde |
| `python3 scripts/workflow_js_wache.py --check` | ✅ alle `github-script`-Blöcke kompilieren |
| `python3 scripts/skript_syntax_wache.py --check` | ✅ 665 Dateien |
| YAML-Parse beider Backup-Workflows + `alert-on-failure.yml` | ✅ |
| `node scripts/tests/sim/alert_scoping_sim.mjs` | ✅ inkl. `#923: Selbstheilung rot → eigener Leerlauf-Rat` und Gegenprobe |

## 7. Was der Inhaber weiterhin tun muss (unverändert)

Kein Agent kommt an Secrets, PAT-Formular, Cloudflare-Konto oder
Environment-Regeln — die Schreib-Endpunkte antworten heute erneut mit `403`.
Das ist keine Bequemlichkeit, sondern die Grenze, die den Vorgang überhaupt
vertrauenswürdig macht.

```bash
npm run backup:einrichten     # E8 zuerst, dann E1–E7; Geheimnisse verdeckt
npm run backup:status         # Stand prüfen, ohne etwas zu ändern
npm run backup:heilung        # was das System selbst reparieren darf
```

Danach Actions → „Offsite-Backup" → „Run workflow" (`main`), anschließend
`npm run backup:probe`. **Abnahmekriterien für #923:**

1. grüner `KV-/D1-Backup`-Job auf `main`,
2. privates Entwurfs-Release `kv-backup-*` mit Größen-/Draft-Nachweis,
3. bestandener Restore-Drill,
4. die Frischwache wird grün (reflexiver Beweis, dass beide Wachen dieselbe Wahrheit sehen),
5. **neu:** Es existiert **kein** grüner `backup`-Job mehr ohne dauerhaftes Ziel —
   der Leerlauf ist messbar, alarmiert und benannt.

Bis dahin bleiben #923 und #1030 offen und rot — der korrekte, auditierbare Zustand.

## 8. Bewusste Grenzen

- **Keine erfundenen Werte.** Kein Secret, kein Token, keine Variable, kein
  Environment-Recht wurde gesetzt oder behauptet. Der Prüfer-Selbsttest fährt
  weiterhin den vergifteten-Werte-Gegencheck.
- **Kein Absenken einer Prüfung.** Kein `continue-on-error`, kein `|| true` in den
  Backup-Workflows. Die neue `!cancelled()`-Bedingung macht den Rückweg-Nachweis
  **häufiger** ausführbar, nicht schwächer — und was er nicht kann, sagt er.
- **Keine Heilung über die Grenze.** Automatisch reparierbar ist genau eine Klasse
  (`scheduler`), und das ist per Vertrag fixiert. „Einrichtung heilen" wäre
  Selbstbetrug mit gutem Namen.
- **Fremde Vorgänge unberührt**: `#1030` (Frischwache-Alarm), `#1098`
  (Release-Scorecard), `#1096`/`#1107` (Lesbarkeit/Fristen) — kein Handeingriff,
  keine Umschrift. Offene Alarm-Issues bleiben Sache ihres eigenen Schlie&szlig;pfads.
- **Keine Doku-Drift.** Der Live-Status der Anleitung trägt das Datum 07.11.2026 mit
  den heute gelesenen Werten; die Vorgängerstände sind als *Archiv* markiert, nicht
  gelöscht.
