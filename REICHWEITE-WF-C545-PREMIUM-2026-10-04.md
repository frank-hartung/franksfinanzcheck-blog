# Reichweite WF-C545 – dauerhaft auf Premium-Level behoben

**Datum:** 2026-10-04
**Auslöser:** Issue #547 „🔧 Wartung · Reichweite · Vorgang WF-C545“ –
Shorts-Schmiede (Video & Reels) rot (Run 37116487089, 03.10.2026, 12:27 UTC),
Schritt „Stand sichern“.
**Sichtbares Symptom:** `git_sync.sh: Rebase-Konflikt gegen origin/main (ein
paralleler Workflow hat dieselben Zeilen geändert). Kein Push – Arbeitsstand
bleibt lokal sauber.`

---

## 1) Was wirklich kaputt war

Der rote Schritt war nur der Melder. Die echte Ursache: ein Scheduling-Kollateralschaden.

1. `social-video.yml` (Shorts-Schmiede) läuft Di + Sa um `20 5 * * 2,6`
   (05:20 UTC) und schreibt am Ende jedes Laufs
   `scripts/social_calendar.py --build`, der **jeden** Kanal-Kalender unter
   `data/social/kalender/*.md` + `*.ics` sowie dessen öffentliche Kopie
   `static/kalender/*.ics` + `index.html` komplett neu erzeugt.
2. `social-autopilot.yml` läuft **im selben Takt** `20 5,7,9,11,13,15,17,19 * * *`
   – also alle 2 Stunden, unter anderem exakt um 05:20 UTC – und ruft am Ende
   jedes Laufs denselben `social_calendar.py --build` auf, bevor er
   `git add data/social/ … static/kalender/` committet und pusht.
3. An Di/Sa starten beide Workflows also in derselben Taktminute, schreiben
   dieselben generierten Kalenderdateien und wollen beide pushen. Der zweite
   Push muss rebasen – und landet exakt auf diesen Dateien im Konflikt.
4. `scripts/git_sync.sh` heilt solche Konflikte bereits automatisch für
   andere rein generierte Artefakte (`data/reserve-readiness.json`,
   `*-REPORT.md`, …, siehe Issues #233/#295/#329/#387/#497) – die
   Kalenderdateien standen aber **nicht** auf dieser Liste und fielen damit
   in den harten „echter Konflikt“-Pfad: kein Push, roter Run, Auto-Alert
   WF-C545.

Fachlich steckt in den Kalenderdateien nichts, das verloren gehen könnte:
Sie sind eine reine Ableitung aus den versionierten Quellen
(`data/social/schedule.yaml`, `state.yaml`, `channels.yaml`,
`video_state.yaml`) und werden bei **jedem** `--build`-Lauf vollständig neu
geschrieben – der jeweils nächste Lauf (spätestens 2 Stunden später)
überschreibt sie ohnehin wieder komplett.

## 2) Die Reparatur (Ursache, nicht nur Symptom)

### A. Automatische Heilung in `scripts/git_sync.sh` (Root-Cause-Fix)

Neuer Fall in `auto_resolve_generated_rebase_conflicts()`:

```
data/social/kalender/*|static/kalender/*)
  git checkout --theirs -- "$f"
  git add -- "$f"
  ;;
```

Analog zum bestehenden Muster für `data/reserve-readiness.json` /
`data/covers_manifest.json`: der frische Lauf gewinnt deterministisch
(„letzter Schreiber gewinnt“), weil beide Seiten denselben Stand ohnehin aus
denselben Quellen regenerieren würden. Die Quelldateien selbst
(`schedule.yaml`, `state.yaml`, `video_state.yaml`) sind **nicht** Teil
dieses Musters und bleiben bei echten Konflikten weiter ein harter Stopp –
hier steckt redaktionelle/Zustands-Information, die nicht blind gemerget
werden darf.

### B. Entzerrung der Taktung (Defense in Depth)

`social-video.yml`: Cron von `20 5 * * 2,6` auf `26 5 * * 2,6` verschoben
(05:26 statt 05:20 UTC). Damit startet Shorts-Schmiede nicht mehr in
derselben Taktminute wie Social-Autopilot (und auch nicht mehr zeitgleich
mit der YMYL-Prüfung, die an Dienstagen ebenfalls auf `20 5 * * 1-5` liegt).
Das senkt die Kollisionshäufigkeit zusätzlich, ersetzt aber nicht die
Heilung unter A – zwei GitHub-Actions-Scheduler können trotz unterschiedlicher
Minute durch Lauf-Jitter weiterhin überlappen.

## 3) Beweisläufe (lokal, deterministisch)

| Prüfung | Ergebnis |
|---|---|
| Neuer Regressionstest `test_social_kalender_konflikt_heilt_frischer_lauf_gewinnt` (synthetisches Konflikt-Szenario: Autopilot schreibt `mastodon.md`/`mastodon.ics`, Shorts-Schmiede kollidiert beim Push) | ✅ heilt automatisch, frischer Lauf gewinnt |
| `python3 -m unittest scripts.tests.test_git_sync -v` (29 Tests) | ✅ alle grün, keine Regression auf den bestehenden Konfliktklassen |
| `scripts/social_calendar.py --selftest` | ✅ Kalender & ICS weiterhin korrekt erzeugt |
| `scripts/social_video.py --selftest` | ✅ unverändert grün |
| `scripts/integrity_guard.py` | ✅ Kern exakt im signierten Zustand (geänderte Dateien sind nicht Teil des Kernbestands) |
| Workflow-YAML (`social-video.yml`) | ✅ parsebar |

## 4) Warum das dauerhaft ist

- **Ursache beseitigt, nicht nur das Symptom:** Der Konflikt heilt jetzt
  automatisch, unabhängig davon, ob künftig noch ein dritter oder vierter
  Workflow denselben Kalender schreibt – die Regel greift auf den ganzen
  Verzeichnisbaum (`data/social/kalender/*`, `static/kalender/*`), nicht nur
  auf die heute betroffenen Dateien.
- **Zwei unabhängige Schichten:** Die Taktentzerrung senkt, wie oft es
  überhaupt zum Konflikt kommt; die Selbstheilung in `git_sync.sh` sorgt
  dafür, dass ein verbleibender Konflikt nie wieder einen roten Run und
  einen WF-Alert erzeugt.
- **Regressionstest als Wächter:** Der neue Test beweist das Verhalten an
  einem synthetischen Repo (nie am Live-Repo) und läuft als Teil derselben
  Suite, die bereits #233/#295/#329/#387/#497 offen hält.
- **Keine Datenverlust-Gefahr:** Die geheilten Dateien sind nachweislich
  reine, deterministische Ableitungen aus versionierten Quellen – ein
  „letzter Schreiber gewinnt“ verliert keine Information, die nicht der
  nächste Lauf ohnehin neu schreibt.

## 5) Nächster Schritt

Issue #547 wird mit Verweis auf diesen Fix geschlossen. Tritt WF-C545 erneut
auf, ist das ein Hinweis auf eine NEUE Ursache (z. B. ein echter Fehler in
`social_video.py`/`social_calendar.py`) – die hier behobene Konfliktklasse
ist durch den Regressionstest dauerhaft abgedeckt.
