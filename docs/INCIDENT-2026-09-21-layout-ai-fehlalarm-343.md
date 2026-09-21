# Vorfall-Bericht: „Workflow fehlgeschlagen: Layout-AI" (#343) — ein Fehlalarm aus dem Entwicklungszweig

**Datum:** 21.09.2026 · **Status:** behoben (dieser PR) · **Schweregrad:** niedrig für die
Website (**kein** Produktionsschaden — `main` war durchgehend grün), mittel für den Betrieb
(Betreiber-Alarm ohne Produktionsbezug + zeitweise **Blindstelle für echte main-Fehler**)
**Verwandt:** [Vorfall 19.09.2026 — Content-Engine/Integritäts-Lock](INCIDENT-2026-09-19-integritaets-lock.md)
(dort dieselbe Alerting-Schwäche: „die Meldung riet, das Log hätte es gewusst") ·
[Issue #343](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/343) ·
[Issue #338](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/338)

## Kurzfassung

Am 21.09.2026 um 17:18 UTC weckte das Fehler-Alerting den Betreiber mit
[Issue #343](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/343):
„⚠️ Workflow fehlgeschlagen: Layout-AI (failure)". Der gemeldete Lauf war jedoch
**kein Produktions-Lauf**: Es war ein `pull_request`-Lauf des Arbeitszweigs
`arena/01a0c4dc-franksfinanzcheck-blog` (PR #342), der mitten in einer
Entwicklungs-Iteration rot war — ein Zwischenstand, sichtbar als Check am PR.
57 Minuten später war derselbe Zweig aus sich heraus grün, und der resolve-Job
des Alertings schloss #343 automatisch.

Die Website selbst war zu keinem Zeitpunkt betroffen. Der eigentliche, reale
Befund des Tages — [Issue #338](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/338)
(ein fehlender Alt-Text, `<head>`-Kinder 59 > Budget 58) — stammte aus dem
**grünen** planmäßigen Layout-AI-Lauf auf `main` und war um 17:54 UTC über
[PR #344](https://github.com/frank-hartung/franksfinanzcheck-blog/pull/344)
dauerhaft behoben.

Der Fehler war strukturell, nicht individuell: Das Alerting kannte die Dimension
„Produktion oder Entwicklung?" nicht. **Jeder** rote Lauf jedes beobachteten
Workflows wurde zum Betreiber-Vorfall — egal auf welchem Zweig, egal aus welchem
Event. Daraus folgten drei konkrete Störbilder, die jetzt alle drei durch eine
einzige Regel beseitigt sind (**PROD-SCOPING**: Alarm nur bei
`head_branch == default_branch` und niemals bei `pull_request`-Events):

1. **Fehlalarm-Lärm** (#343 selbst): Dev-Iteration weckt den Betreiber.
2. **Dedupe-Vergiftung** (latente Blindstelle): Solange ein Dev-Issue wie #343
   offen stand, hätte ein **echter** `main`-Fehler desselben Workflows kein
   eigenes Issue bekommen — der Dedupe-Filter („offenes Issue desselben
   Workflows vorhanden → kein Duplikat") unterdrückt ihn. Genau diese Klasse
   ist seit Issue #218 dokumentiert und gefürchtet; #343 hat sie erneut scharf
   gemacht, ohne dass es jemand merkte.
3. **Falsch-Grün-Schluss**: Der resolve-Job schloss Alarme bei **irgendeinem**
   grünen Lauf des Workflows. #343 wurde von einem grünen Lauf des Zweigs
   `arena/01a0c4dc-…` geschlossen — ohne jeden Beweis über den Produktionsstand.
   Umgekehrt hätte ein echter main-Alarm so „geheilt" werden können, während
   main weiter rot ist. resolve gilt deshalb symmetrisch: geschlossen wird nur
   bei Grün **auf dem Default-Branch**.

Zusätzlich trägt ein Alarm jetzt die **Diagnose direkt im Issue**: die Namen der
fehlgeschlagenen Jobs und Schritte mit Log-Links, plus Event und Versuch-Nummer.
Das ist die überfällige Einlösung der Lehre aus dem
[Integritäts-Lock-Vorfall](INCIDENT-2026-09-19-integritaets-lock.md): Eine
Meldung, die „API-Key? GitHub-Ausfall?" rät, obwohl der Run den toten Schritt
kennt, schickt den Menschen auf Ratesuche.

Bei der Verifikation dieses Vorfalls wurde ein **zweiter, scharfer Befund**
sichtbar: PR #344 hatte mit `layouts/_partials/head.html` eine **gelockte
KRITISCH-Datei** geändert und den Integritäts-Lock **nicht mit-signiert**
(letzte Signatur 15:48 UTC @ `598acdf`, Merge 17:54 UTC @ `ea509c1`). Damit
stand `main` seit 17:54 UTC rot am `integrity_guard --gate` (Exit 3) — dieselbe
Zeitbombe wie am 18.09.2026: Der nächste Content-Engine-Lauf (Mi 06:10 UTC)
wäre im ersten Schritt in den HARD STOP gelaufen (Produktions-Slots verloren),
und **jeder neue PR** wäre am Pflicht-Check „Integritäts-Siegel" gescheitert
(der Check hängt im Ruleset; PR #342 war nur grün, weil er den Lock auf seinem
eigenen Zweig selbst neu gezeichnet hatte). Der Drift war vom Gate als
`VERSIEGELBAR` klassifiziert (Herkunft: `ea509c1`, bytegleich zum committeten
Stand, kein Laufzeit-Mutant). Nach dokumentierter Sichtung des Diffs (zwei
Inline-`<style>`-Blöcke zu einem vereint, `@font-face` ins neue Partial
`ff_fontfaces.html` ausgelagert — funktionsneutral, vom eigenen Build + Audits
verifiziert) wurde der Lock in diesem PR neu signiert
(`integrity_guard.py --set-current`, Akte im Lock: 21.09.2026,
`geaendert: [layouts/_partials/head.html]`).

## Was gemeldet wurde

| Feld | Wert |
|---|---|
| Issue | [#343](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/343) „⚠️ Workflow fehlgeschlagen: Layout-AI (failure)", Label `auto-report` |
| Eröffnet | 21.09.2026, 17:18:20 UTC (vom Workflow „Fehler-Alerting") |
| Gemeldeter Lauf | [35631056798](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/35631056798) — Layout-AI Run #13 |
| Branch / Commit | `arena/01a0c4dc-franksfinanzcheck-blog` · `41e56bd7` — **nicht main** |
| Event | `pull_request` (PR #342) — **kein Produktions-Trigger** |
| Roter Schritt | „Lauf rot stellen, wenn Befunde offen sind" — ein Hard-Fail-Gate, das PR #342 experimentell in seine Zweig-Version von `layout-ai.yml` eingebaut hatte |
| Geschlossen | 21.09.2026, 18:15:16 UTC — automatisch durch den resolve-Job, nachdem Run [#20 (35637093358)](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/35637093358) desselben Zweigs grün wurde |

## Was tatsächlich passiert ist

| Zeit (UTC) | Ereignis |
|---|---|
| 13:49 | Layout-AI-Planlauf [#11 (35608083144)](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/35608083144) auf `main`: **Lauf grün**, aber Befunde → Issue [#338](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/338) (13:50): Alt-Text fehlt bei `2026-09-21-7-gewohnheiten-fuer-finanzielle-freiheit`; `head`-Kinder 59 > 58 auf zwei Artikeln (Desktop + Mobile) |
| ~15:00–17:10 | Zwei Arbeitszweige nehmen #338 unabhängig auf: `arena/01a0c4dc-…` (PR #342, inkl. Umbau von `layout-ai.yml` mit `pull_request`-Triggern und Hard-Fail-Gate) und `arena/01a0c50b-…` (PR #344, reine Befund-Heilung) |
| 17:12 | Layout-AI Run #12 (`push` auf den Zweig) schlägt fehl — erster roter Dev-Lauf der Serie |
| 17:17 | Run #13 (`pull_request`, PR-Head `41e56bd7`) schlägt fehl: das neue Hard-Fail-Gate des Zweigs findet offene Befunde → **Absichtliches Rot als Entwicklungssignal** |
| 17:18 | Fehler-Alerting eröffnet Issue #343 — ohne zu wissen, dass es ein Dev-Lauf war |
| 17:17–17:54 | Runs #14–#19 desselben Zweigs rot (jede PR-Iteration); der Dedupe-Filter unterdrückt Folge-Issues — #343 bleibt das einzige (und blockiert damit latent echte main-Alarme für „Layout-AI") |
| 17:54:31 | [PR #344](https://github.com/frank-hartung/franksfinanzcheck-blog/pull/344) merged als `ea509c1` auf `main`: Cover + descriptiver Alt-Text nachgezogen; zwei Inline-`<style>`-Blöcke im `<head>` zu einem vereint, `@font-face` nach `ff_fontfaces.html` ausgelagert; „Max. Kinder"-Metrik in `layout_browser_check.js` korrekt auf `<body>`-Knoten gescopet (`head`-Kinder bleiben als `headChildren` transparent, zählen aber nicht mehr als Budget-Verstoß) |
| 18:05 | Issue #338 geschlossen — der Realbefund ist dauerhaft geheilt |
| 18:14 | Layout-AI Run #20 auf dem Zweig `arena/01a0c4dc-…` **grün** (die Iteration war fertig) |
| 18:15 | resolve-Job schließt #343 („läuft wieder fehlerfrei") — ausgelöst von einem Zweig-Lauf, nicht von Produktion |

**Bilanz:** Die Website war durchgehend gesund. Der Alarm betraf einen
Entwicklungs-Zwischenstand. Von den 8 roten Layout-AI-Läufen des Tages fand
**kein einziger** auf `main` statt — `main` selbst lief grün (Run #11) und hatte
seinen echten Befund (#338) bereits korrekt als Issue gemeldet und geheilt
bekommen.

## Ursache

`alert-on-failure.yml` entschied nur über `conclusion` (`failure`/`cancelled`),
nie über den **Kontext** des Laufs. `workflow_run`-Ereignisse tragen beides:
`head_branch` und `event`. Ohne diese Dimension ist jeder rote Check einer
Agent-Iteration (dieses Repo entwickelt über kurzlebige `arena/*`-Zweige mit
PR-Checks) ein Betreiber-Vorfall — und das Dedupe-/Resolve-Design (ein Issue je
Workflow, schließen bei irgend-einem Grün) verstärkt den Fehler in beide
Richtungen (Unterdrückung echter Alarme, Scheinheilung falscher).

## Dauerhafte Reparatur (dieser PR)

1. **PROD-SCOPING im alarm-Job** — früher `return` vor jeder Issue-Erzeugung:
   gemeldet wird nur `head_branch == repository.default_branch` **und**
   `event != 'pull_request'`. Da `workflow_run`-Workflows immer in der
   `main`-Version dieser Datei laufen, gilt die Regel repo-weit für alle Zweige.
   Rote Dev-Läufe bleiben sichtbar, wo sie hingehören: als Checks am PR/Zweig.
2. **Symmetrisches PROD-SCOPING im resolve-Job** — Auto-Close nur noch bei
   `success` **auf dem Default-Branch** (und nie für `pull_request`-Läufe).
   Ein grüner Zweig-Lauf ist kein Produktionsbeweis mehr.
3. **Diagnose statt Raten** — das Alarm-Issue trägt jetzt die rot beendeten
   Jobs und Schritte mit direkten Log-Links (`actions: read` war für den
   Phantom-Filter ohnehin vergeben; die Job-Abfrage wird einmal geholt und
   zweimal genutzt), plus Event und Versuch-Nummer.
4. **Dedupe paginiert** — die Offene-Issues-Suche liest alle Seiten statt nur
   der ersten 100 (kleine blinde Stelle, große Wirkung im Störungsfall).
5. **Regressions-Tests** `scripts/tests/test_alert_scoping.py` (13 Tests, läuft
   in „Publication reliability regression tests" auf jeden PR, der `scripts/**`
   oder `.github/workflows/**` anfasst): Scoping-Vergleich vorhanden und VOR der
   Issue-Erzeugung, `pull_request` ausgeschlossen, resolve-Bedingung symmetrisch,
   Titel-/Label-Vertrag byte-stabil (resolve + Aufräum-Workflow parsen darauf),
   Wacht-Liste weiter per `alerting_heartbeat.gelistete_workflows` lesbar
   (SSOT des Herzschlags, ≥ 35 Namen, keine Selbstbeobachtung),
   `types: [completed]` intakt. Dazu die **Verhaltens-Simulation**
   `scripts/tests/sim/alert_scoping_sim.mjs`: Sie führt das Inline-Skript mit
   gestubbtem `github-script`-Kontext wirklich aus und beweist neun Szenarien —
   exakte #343-Reproduktion (roter PR-Lauf eines Zweigs → kein Alarm), rote
   `push`-Läufe auf Zweigen (stumm), echter `main`-Fehler (Alarm **mit**
   Schritt-Diagnose, Titel-/Label-Vertrag), Phantom-Filter #218 (verdrängter
   Wartelauf stumm, echter Abbruch Alarm), Dedupe (kein Duplikat) und Fail-open
   (Job-API tot → Alarm trotzdem). Struktur-Tests allein wären eine Leihgabe —
   hier wird das Verhalten selbst bewacht.
6. **Unangetastet** (bewusst): `name: Fehler-Alerting`, die Wacht-Liste der 39
   Workflows, der Phantom-Filter für verdrängte Warteläufe (#218), die
   Label-Garantie (`auto-report` + `createLabel`-Fallback, C12-Klasse) und der
   Issue-Titel — alles Verträge, die Herzschlag, Aufräum-Workflow und
   Bestands-Tests lesen.
7. **Integritäts-Lock neu signiert** (zweiter Befund, s. o.):
   `data/integrity_lock.json` trägt jetzt den Ist-Stand von `main` inkl.
   `head.html` aus `ea509c1`; die Herkunft steht in der Akte des Locks und in
   diesem Bericht. Ohne diesen Schritt wäre dieser PR selbst nicht mergebar
   gewesen (Pflicht-Check „Integritäts-Siegel") und die Content-Engine wäre am
   Mittwoch in den HARD STOP gelaufen. Die Regel aus dem 19.09.-Vorfall bleibt
   bestehen: Wer eine gelockte Kerndatei ändert, signiert im SELBEN Commit —
   PR #344 hatte genau das versäumt, das Gate hatte es korrekt angezeigt, und
   die Reparatur folgt hier dem vorgeschriebenen Pfad (`--set-current` nach
   Sichtung, nicht `--heal` — KRITISCH-Drift ist und bleibt Chefsache).
8. **`layout-ai.yml` selbst wurde in diesem PR bewusst NICHT angefasst**:
   Der Workflow auf `main` war nie der Verursacher (er lief grün und meldete
   #338 korrekt als weiches Issue). PR #342 (offen, Layout-AI-Checks seit
   18:14 UTC grün) enthält bereits den fachlichen Ausbau des Workflows
   (Annotationen, Job-Summary, Marker-Dedupe mit Issue-Schließpfad, DOM-Budget
   pro Seite) — zwei parallele Umbauten derselben Datei wären Merge-Konflikt
   und Doppelarbeit. Dieser PR repariert die Alerting-Klasse + den Lock-Stand,
   PR #342 die Layout-AI-Tiefe; beide überschneiden sich nur in
   `data/integrity_lock.json` (dort gewinnt der Zweitgemergte per erneuter
   Signatur — der dafür vorgesehene Pfad).

## Verifikation (21.09.2026, reproduzierter Workflow-Stand von `main` @ `14c1a89`)

| Prüfung | Ergebnis |
|---|---|
| `hugo` Extended 0.164.0 (PyPI-Quelle der `install-hugo`-Action), `hugo --quiet` | ✅ exit 0, 371 HTML-Seiten |
| `python3 scripts/layout_audit.py` (statischer Teil des Workflows) | ✅ exit 0 — 0 kritisch, 0 Warnungen: 2140 interne Links geprüft/0 kaputt, alle Cover + WebP/AVIF-Varianten, **alle Alt-Texte gesetzt und aussagekräftig** (Befund #338 geheilt), Article-JSON-LD auf 39 Artikeln, og:image/Meta/H1 überall |
| DOM-Budgets der Browser-Audit-Seiten (Startseite + 3 neueste Artikel, Metrik-Logik 1:1 aus `layout_browser_check.js` nachgebildet) | ✅ alle im Budget: max. `<body>`-Kinder 13–17 (Budget 58), DOM-Knoten 410–740 (Budget 1400); `headChildren` 49–57 (reine Transparenz, seit #344 kein Budget mehr) |
| `python3 -m unittest discover -s scripts/tests` | ✅ 508 Tests OK (inkl. der 13 neuen Scoping-Tests; 18 Bestandsskips) |
| Verhaltens-Simulation `scripts/tests/sim/alert_scoping_sim.mjs` (node) | ✅ alle 9 Szenarien korrekt — #343-Konstellation bleibt stumm, echte main-Fehler alarmieren mit Diagnose |
| `python3 scripts/integrity_guard.py --gate` (nach Neu-Signatur) | ✅ exit 0 — 43 Dateien gelockt, HEAD `14c1a89`, neu gezeichnet: `layouts/_partials/head.html` |
| `python3 scripts/integrity_guard.py --selftest` | ✅ 5 Fälle eingefroren + Kern-Beweis grün |
| `python3 scripts/history_guard.py` | ✅ 56/56 Historien sauber, 0 harte Fehler |
| Layout-AI auf `main` | ✅ letzter Planlauf Run #11 grün; Befund-Pfad (#338 → Issue → PR #344 → geschlossen) funktionierte exakt wie entworfen |

## Was bleibt zu beobachten

- **PR #342** entscheidet, ob Layout-AI auf `main` zusätzlich das Hard-Fail-Gate
  bekommt. Falls es merged: Mit dem PROD-SCOPING dieses PRs bleibt auch ein
  absichtlich roter Gate-Lauf auf `main` ein **echter** Alarm (korrekt — dann
  ist die Produktion betroffen), während Zweig-Iterationen stumm bleiben.
- Der **Alerting-Herzschlag** zählt weiterhin die `workflow_run`-Zustellung
  (nicht die erstellten Issues) — das PROD-SCOPING ändert an seiner Messgröße
  nichts, die Zustellquote bleibt überwachbar.
