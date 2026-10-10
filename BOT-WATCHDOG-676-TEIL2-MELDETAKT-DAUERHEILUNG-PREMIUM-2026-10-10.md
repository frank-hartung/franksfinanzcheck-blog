# Bot-Watchdog · Meldetakt · Vorgang #676 (Teil 2)
# DAUERHEILUNG (Premium-Level) – 10.10.2026

**Vorgang:** Bot-Watchdog #676, Teil 2
**Bereich:** Alarm-Wache (`bot-watchdog.yml`) · Alarm-Router (`scripts/alert_router.py`) · Governance-Vertrag
**Klasse:** DAUERHEILUNG (kein manueller Eingriff mehr nötig)
**Ziel:** Der Meldetakt ist an den **Ausfall** gebunden, nicht an den Kalender –
ein Ausfall ist spätestens eine Stunde nach Beginn sichtbar und bleibt sichtbar,
solange er steht.

---

## 📋 Zusammenfassung des Vorfalls

| Feld | Wert |
|---|---|
| **Issue** | [#676](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/676) – „Bot-Watchdog: Automatisierung braucht Eingriff“ |
| **Teil 1** | PR #686 (`7dea07c` → Merge `892dddd`, 10.10.2026 09:37 UTC) – Auslieferung vor Siegel, Befund `deploy-blockade` |
| **Was Teil 1 ließ** | Die **Latenz**: Der Watchdog lief einmal täglich um 08:30 UTC |
| **Erkennungslücke** | bis zu **23,5 h** zwischen Ausfall-Beginn und Entdeckung |
| **Ausfall vom 09.10.2026** | 19 h 38 min ohne öffentliche Auslieferung – **komplett zwischen zwei Watchdog-Läufen** |
| **Meldetakt im Ticket** | Eskalationsleiter in **Tagen** (0/3/7/14), Mindestabstand 72 h → während der 19 h **kein einziger Kommentar** |
| **Ticket-Stand bei Arbeitsbeginn** | 10.10.2026 10:52 UTC offen → 10:54:50 UTC `completed` geschlossen (PR #684) |

### Belegte Ausgangslage (über die GitHub-API erhoben)

| Prüfung | Ergebnis |
|---|---|
| `gh auth status` | ✅ angemeldet als `frank-hartung` (`GH_TOKEN`) – die Annahme „jeder `gh`-Aufruf schlägt fehl“ traf in dieser Umgebung **nicht** zu |
| PR #686 | ✅ `MERGED` 10.10.2026 09:37:54 UTC, Merge-Commit `892dddd`, ist Vorfahr von `main` |
| PR #684 | ✅ `MERGED` 10.10.2026 10:54:48 UTC, Merge-Commit `7c7668f` |
| Commit `7dea07c` | ✅ vorhanden („fix(publication): Auslieferung vor Siegel …“) |
| Commit `dc761e6` / `967a3b2` | ❌ existieren auf GitHub **nicht** (HTTP 422) |
| Branch `arena/76491cfe-franksfinanzcheck-blog` | ❌ nach dem Merge gelöscht – „übernehmen“ war nicht möglich |
| Patch `/home/user/0676-…-bin.patch` | ❌ in dieser Umgebung **nicht vorhanden** (`/home/user` enthält nur das Repo) |

**Folge:** Der übertragbare Patch war nicht auffindbar, die referenzierten
Commits nie gepusht. Teil 2 ist deshalb **neu gebaut**, nicht eingespielt –
gegen die im Ticket und im Abschlussbericht zu Teil 1 dokumentierte Absicht
(„Meldetakt an den Ausfall binden“, Kanal läuft ab dem nächsten `:05`
stündlich).

---

## 🔍 Wurzelursache – und warum sie strukturell ist

Teil 1 hat den Befund gebaut. Gesehen hat ihn trotzdem niemand.

```
08:30 UTC   Watchdog-Lauf   → alles grün
09:00 UTC   deploy.yml bricht am Scorecard-Schritt ab
            … 19 h 38 min ohne öffentliche Auslieferung …
            (kein Lauf misst, niemand meldet)
08:30 UTC   Watchdog-Lauf   → jetzt erst sichtbar, wenn ein Artikel 404 läuft
```

Drei Fehler, die zusammengehören:

1. **Mess-Takt = Kalender.** Ein täglicher Cron macht aus jeder Störung einen
   Ausfall von bis zu 23,5 h. Die Ausfall-Erkennung war selbst ein
   Tagesgeschäft.
2. **Meldetakt = Kalender.** Die Eskalationsleiter rechnet in Tagen, der
   Mindestabstand zwischen zwei Kommentaren beträgt 72 h. Für einen chronischen
   Befund ist das richtig (#272: „ein offenes Ticket ist kein tägliches
   Rauschen“). Für einen laufenden Ausfall bedeutet es: **Schweigen während des
   gesamten Ausfalls.**
3. **Blockade ohne 404 war kein Befund.** `CHECK3B` maß
   `FAIL (Schritt: …)`, erzeugt hat das nichts. Solange der letzte Artikel
   noch live war, sah die Wache grün – die eingefrorene Auslieferung wurde erst
   durch den *nächsten* Artikel sichtbar (Klasse #537).

---

## ✅ DAUERHEILUNG

### 1. `bot-watchdog.yml` – zwei Takte in einem Workflow

| Takt | Cron | Umfang |
|---|---|---|
| **Ausfall-Takt** | `5 * * * *` (stündlich :05 UTC) | read-only: 1a Produktions-Wache, 2 Skript-Syntax, 3 Live-Site, 3b Auslieferungs-Kette + Live-Site-Selbstheilung + Nachmessung + Routing |
| **Voll-Lauf** | `30 8 * * *` (10:30 MESZ) | unverändert alle Checks inkl. Hugo, Reserve-Nachzertifizierung, Pinterest-Report |

* Der **Takt-Umschalter** (`id: takt`) ist die einzige Wahrheit: Er liest
  `github.event.schedule` und setzt `modus=triage|voll`; per
  `workflow_dispatch` ist der Takt wählbar (`auto|triage|voll`).
* Jeder teure und jeder schreibende Schritt prüft
  `steps.takt.outputs.modus == 'voll'`: Hugo-Installation,
  Reserve-Zertifikat, Pinterest-Report, Content-Reserve-Dispatch und der
  Commit des Routing-Zustands. **Ein Ausfall-Takt kann damit per Konstruktion
  weder bauen noch produzieren noch nach main committen.**
* Die `:05` ist bewusst nicht mit dem Deploy-Catchup (`:20`) kollidiert, den
  sie bei Befund selbst auslöst.
* `concurrency: bot-watchdog` bleibt unverändert: Ein Ausfall-Takt, der in
  einen Voll-Lauf fällt, wartet – kein Doppel-Dispatch der Heilung.

### 2. `scripts/bot_watchdog.py --triage` – die Ausfall-Klasse

* `run_all(triage=True)` misst nur 1a/2/3/3b und meldet die Blockade.
* Nicht gemessene Checks stehen als `ÜBERSPRUNGEN (Ausfall-Takt – Voll-Lauf
  08:30 UTC)` in der Env – **niemals als `OK`** (Vertrag C2: eine nicht
  ausgeführte Messung ist kein Grün). Der Wortlaut ist Vertragsbestandteil:
  Er darf weder `OK` noch `WARN`/`FAIL` enthalten, sonst läse ein
  Workflow-Schritt eine Nicht-Messung als Grün oder als Befund.
* Report und Konsole sagen im Ausfall-Takt „AUSFALL-TAKT GRÜN (nur
  Ausfall-Klasse gemessen)“, nicht „ALLES OK“.

### 3. Blockade ohne 404 wird zum Befund

`CHECK3B == blockiert` erzeugt jetzt immer `deploy-blockade` – unabhängig vom
HTTP-Status des neuesten Artikels. Ein Bauplan (`deploy_blockade_finding`),
zwei Wege: zusammen mit einer 404 und allein. Der Befund nennt Ursache,
blockierenden Schritt, die Fehlschlag-Serie **und** den maschinellen
Heilungsweg – bei Besitzer `auto` ist eine Arbeitsanweisung an einen Menschen
eine Sackgasse (C34).

### 4. `scripts/alert_router.py` – akuter Meldetakt

Befunde der Ausfall-Klasse tragen `akut=True`. Für sie rechnet die Leiter in
**Stunden**:

| Alter des Tickets | Stufe |
|---|---|
| 0 h | Meldung (Ticket-Eröffnung) |
| 1 h | Stand nach 1 h |
| 6 h | Stand nach 6 h |
| 24 h | Stand nach 24 h |
| danach | alle 24 h, bis der Befund geheilt ist |

* Gerechnet wird ab dem **letzten Stand**, nicht ab der Stufen-Schwelle –
  sonst würde der stündliche Takt ab Stunde 48 jede Runde feuern (Taktfeuer
  statt Meldetakt).
* Mindestabstand 1 h, ein Stand pro Stufe, Endstufe wiederholt.
* **Grenze zu #272:** Chronische Befunde behalten ihre 72-h-Kadenz
  unverändert. Ein akuter Takt für alles wäre Taktfeuer und würde #272 kippen.
* Der Stand nennt Ausfalldauer („19 h 38 min“), offene Befunde, was die
  Maschine bereits versucht hat, und wann der nächste Stand kommt.
* Das Ticket schließt sich selbst, sobald die Nachmessung grün ist.

**Voraussetzung, die Teil 2 erst möglich macht:** Weil der Ausfall-Takt
stündlich misst, ist das Ticket-Alter ein brauchbares Maß für die
Ausfalldauer (Abweichung höchstens eine Takt-Runde). Bei einem täglichen Lauf
dürfte die Leiter gar nicht in Stunden rechnen.

### 5. Governance-Vertrag **C35 „Meldetakt an den Ausfall“**

`scripts/governance_contract.py` prüft in beide Richtungen (Fehler **und**
Schein-Sicherheit) und läuft im PR-Pfad:

| Prüfung | Sabotage, die der Selftest einspielt |
|---|---|
| Stündlicher Ausfall-Takt vorhanden | Cron `5 * * * *` entfernt |
| Voll-Lauf bleibt | Cron `30 8 * * *` entfernt |
| Takt-Umschalter vorhanden | `id: takt` entfernt |
| `--triage` verdrahtet | — |
| Ausfall-Takt ist read-only | Takt-Sperre am `Routing-Zustand sichern` entfernt |
| Nicht-Messung ist kein Grün | `TRIAGE_SKIP = "OK (…)"` |
| Router nutzt den akuten Takt | `akuter_takt(machine)` → `False` |
| Chronisch bleibt bei 72 h | `MIN_COMMENT_INTERVAL_HOURS = 72` → `1` |
| Ausfall-Befund ist akut | `akut=True` aus `deploy_blockade_finding` entfernt |
| Blockade nennt Heilungsweg | `watchdog_recovery.py` aus dem Befund entfernt |
| Regressionstest vorhanden | Testdatei fehlt |

---

## 🔧 Mitgeheilt: vier Defekte aus PR #684

PR #684 (Merge `7c7668f`, 10.10.2026 10:54 UTC) ging mit vier Fehlern in
`main`. Der erste versteckte die anderen drei: Solange
`governance_contract.py` nicht importierbar war, prüfte niemand etwas.

| # | Defekt | Folge | Reparatur |
|---|---|---|---|
| 1 | `LABEL`-Dict in `scripts/governance_contract.py` mit `}` **zu früh geschlossen**, zwei Einträge dahinter | `IndentationError` – die Datei war nicht importierbar, das Qualitäts-Gate `link-check.yml` auf main **rot** (Lauf `38046561281`, 10:54:52 UTC, `failure`) | Klammer entfernt; beide C34-Verträge stehen in **einem** Eintrag (zwei gleiche Schlüssel in einem Dict-Literal machen einen unsichtbar) – ebenso in `RULE_TEXT` |
| 2 | Schritt `Release-Scorecard` in `deploy.yml` mit **zwei `run:`-Blöcken** (#684 vor #686 geschoben) | Doppelter YAML-Schlüssel: der erste Block ist toter Code, `test_workflow_yaml` (UniqueKeyLoader) rot, `deploy.yml`-Läufe `failure` (`38046560460`, `38046490439`) | Ein Block mit beiden Absichten: Exit-Auswertung aus #686 (C34) + benannte Befund-Annotation aus #684. Verhalten gemessen: Exit 0 → grün · Exit 1 → harter Stopp, laut · Exit 2 → Auslieferung läuft weiter, `werkzeugfehler=true`, laut |
| 3 | Anker der Blustradius-Klausel war der blanke Schritt-Text | `find` fand den **Kommentar** am Kopf von `deploy.yml` (Zeile ~324, seit #686) statt des Schritts (Zeile ~834) und meldete „die Isolation steht NACH der finalen Release-Scorecard“ – auf einem Baum, in dem sie 130 Zeilen **vor** ihr steht. Derselbe Anker-Fehler saß in `test_release_isolation.py` | Anker auf `- name: Release-Scorecard (Produktionswahrheit versiegeln` (Vertrag **und** Test) |
| 4 | `live-site`-Befund doppelt gebaut (inline in `run_all` + `live_site_findings`) | Dieselbe 404 stand **zweimal** im Ticket, einmal ohne Heilungsweg und ohne Ausfall-Klasse | Ein Befund, zwei Beleg-Quellen: `classify_deploy_jobs` (Schritt) + `deploy_ausfall_spur` (Serie, Run-Id) |

Ein Melder, der am Melden scheitert, ist der teuerste Fehler (Lehre aus
#209/#227). Alle vier Klassen sind jetzt festgenagelt: `AnkerDisziplinTestCase`
(1, 3), `test_workflow_yaml`/UniqueKeyLoader (2),
`test_eine_404_ist_ein_befund_nicht_zwei` (4).

---

## 🧪 Nachweis

| Prüfung | Befehl | Ergebnis |
|---|---|---|
| **Gesamtsuite (130 Module)** | `python3 -m unittest <alle scripts/tests/test_*.py>` | ✅ **2611 Tests, OK** (25 übersprungen, 0 Fehler) |
| Neue Meldetakt-Tests | `python3 -m unittest scripts.tests.test_bot_watchdog_meldetakt` | **47 Tests, OK** |
| Bestehende Watchdog-Tests | `… test_bot_watchdog_live_site test_bot_watchdog_routing test_alert_router` | **119 Tests, OK** (zusammen mit obigen) |
| Deploy-Vertrag + Isolation + Workflow-YAML | `… test_deploy_publication_priority test_release_isolation test_workflow_yaml` | **49 Tests, OK** |
| Governance-Vertrag Selftest | `python3 scripts/governance_contract.py --selftest` | ✅ **C1–C35**, alle Sabotagen erkannt, echter Baum still |
| Governance-Vertrag real | `python3 scripts/governance_contract.py --quick` | ✅ **33 Regeln** erfüllt |
| Watchdog-Selbsttest | `python3 scripts/bot_watchdog.py --selftest` | ✅ inkl. neuer #676-Ausfall-Klassen-Prüfung |
| Router-Selbsttest | `python3 scripts/alert_router.py --selftest` | ✅ inkl. 24-h-Simulation (3 Stände, nicht 24) |
| Heiler-Selbsttest | `python3 scripts/watchdog_recovery.py --selftest` | ✅ |
| YAML beider Workflows | `yaml.safe_load` (+ UniqueKeyLoader für `deploy.yml`) | ✅ Wache: 2 Crons, 19 Schritte, Dispatch-Eingang `takt` · Deploy: keine doppelten Schlüssel |
| Shell der Wache | `bash -n` je `run:`-Block | ✅ **14/14** Blöcke |
| Verhalten des Takt-Umschalters | echter `run:`-Block mit 6 Lagen ausgeführt | ✅ `5 * * * *`→triage · `30 8 * * *`→voll · Wunsch überschreibt Cron · ohne Angabe→voll |
| Verhalten des Scorecard-Schritts | echter `run:`-Block aus `deploy.yml` mit 3 Exit-Lagen ausgeführt | ✅ `0`→grün · `1`→rc 1, laut · `2`→rc 0, `werkzeugfehler=true`, laut |
| Ausfall-Takt live | `python3 scripts/bot_watchdog.py --triage` (echte GitHub-API) | ✅ misst 1a/2/3/3b, 11 Checks `ÜBERSPRUNGEN`, Exit 0 |
| Mutationsprobe | `akuter_takt(machine)` → `False` / Cron entfernt / `akut=True` entfernt | ✅ je 1 Test rot, danach wieder grün |

**Vorbestehende Fehler:** keine. Die drei Fehler in `test_reserve_pipeline`
(2) und `test_offenlegung_gate` (1), die auf dem Ausgangsstand `c1b9d80` rot
waren (per `git stash` gegengeprüft), sind auf dem aktuellen `main`-Stand
(`cfcb865`, mit PR #684) grün.

**Nicht prüfbar aus dieser Umgebung:** der öffentliche HTTP-Status von
`https://franksfinanzcheck.de/…` (nur `github.com`, `npmjs.org` und `pypi.org`
sind erreichbar). `check_live_site` liefert hier `offline` und damit `WARN` –
bewusst kein Befund (Offline ist kein Ausfall).

---

## 📌 Was sich für den Betrieb ändert

| Vorher | Nachher |
|---|---|
| Ausfall bleibt bis zu 23,5 h unbemerkt | Ausfall ist spätestens **1 h** nach Beginn sichtbar |
| 19-h-Ausfall: kein Kommentar im Ticket | Meldung, Stand nach 1 h, Stand nach 6 h, dann alle 24 h |
| Blockade ohne 404 ist unsichtbar | `deploy-blockade` meldet die eingefrorene Auslieferung sofort |
| Chronische Befunde im 72-h-Takt | **unverändert** 72 h – #272 bleibt gültig |
| Reihenfolge per Konvention | Reihenfolge per Vertrag **C35** (PR-Gate) + 47 Unit-Tests |
| Stündlicher Lauf könnte Hugo bauen | Kann er per Konstruktion nicht – jeder teure Schritt prüft den Takt |

**Kosten:** Der Ausfall-Takt ist read-only und misst vier Checks; er braucht
weder Hugo noch die Reserve-Produktion. Der tägliche Voll-Lauf bleibt der Ort
für alles Übrige.

**Runbook:** `docs/ANLEITUNG-RELEASE-SCORECARD.md` (Scorecard),
`docs/ANLEITUNG-HUGO-BUILD.md` (Deploy-Kette),
`docs/ALARMROUTING-2026-09-12.md` (Besitz, Kadenz, Schließpfad).
