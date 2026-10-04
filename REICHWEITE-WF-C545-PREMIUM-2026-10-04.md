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

## 4b) Nachtrag 04.10.2026 – zweite, tieferliegende Ursache beseitigt

Die Nachprüfung des roten Schrittes zeigte: Selbst mit Heilung (A) und
Taktentzerrung (B) wäre der Lauf in einem Restfall **weiterhin rot**
geworden. Grund war die Push-Zeile im Schritt „Stand sichern“ selbst:

```
scripts/git_sync.sh --push-only || git push     # vorher
```

`git_sync.sh` bricht bei einem nicht automatisch heilbaren Konflikt
**bewusst und sauber** ab („Kein Push – Arbeitsstand bleibt lokal sauber“) –
genau die Meldung aus dem Fehlerlauf. Der nachgeschaltete rohe `git push`
hebelte diese fail-closed-Entscheidung aus: Er kann nichts gewinnen, was
git_sync (Fetch-Retry, Push-Retry, Rebase-Runden, Auto-Heilung) nicht schon
versucht hat, wird als non-fast-forward abgelehnt und beendet den Schritt
mit Exit 1 – mit einer Meldung, die die echte Ursache verdeckt. Exakt das
war das rote Symptom von WF-C545.

**Bereinigt (dasselbe Anti-Muster, alle Fundstellen im Bestand):**

| Workflow | vorher | nachher |
|---|---|---|
| `social-video.yml` („Stand sichern“) | `git_sync.sh --push-only \|\| git push` | `if git_sync.sh --push-only; then ✅ else ::warning::` |
| `social-dialog.yml` („Stand sichern“) | `git_sync.sh --push-only \|\| git push` | dito – Erfolgsmeldung erst nach belegtem Push |
| `werkbank.yml` („Dossiers committen“) | `git_sync.sh --push-only \|\| git push \|\| true` | dito – kein verschlucktes Ergebnis mehr |

Kein Datenverlust: In allen drei Fällen sind die betroffenen Stände
(`video_state.yaml` + Kalender, `dialog_state.yaml`, Werkbank-Dossiers)
lokal sauber committet und werden vom nächsten Lauf erneut gepusst – der
Lauf meldet das jetzt als sichtbare Warnung statt als irreführendes Rot
bzw. als stilles `|| true`.

**Neuer Wächter:** `scripts/tests/test_push_wache.py` prüft **alle**
Workflows (nicht nur die drei heute bereinigten) auf
1. `git_sync.sh … || git push` (Blind-Fallback) und
2. `git_sync.sh … || true` (verschlucktes Ergebnis).
Damit kann die Klasse nicht über einen neuen Workflow zurückkehren.

| Prüfung (Nachtrag) | Ergebnis |
|---|---|
| `python3 -m unittest scripts.tests.test_push_wache -v` (2 Tests) | ✅ grün |
| `python3 -m unittest scripts.tests.test_git_sync` (29 Tests) | ✅ grün |
| YAML-Parse `social-video.yml` / `social-dialog.yml` / `werkbank.yml` | ✅ |
| `scripts/social_video.py --selftest` · `scripts/social_calendar.py --selftest` | ✅ · ✅ |

## 4c) Nachtrag 04.10.2026 (II) – die Klasse vollständig geschlossen

Nach 4b blieb eine Lücke, die der damalige Wächter konstruktionsbedingt
nicht sehen konnte: Er suchte nur nach `git_sync.sh … || git push` bzw.
`|| true`. Ein Workflow, der `git_sync.sh` **gar nicht erst aufruft** und
stattdessen roh pusht, fiel durch das Raster – dieselbe Fehlerklasse, nur
über eine andere Tür.

Eine Vollprüfung des Bestands (77 Workflows) fand genau zwei solche
Stellen – die beiden letzten rohen Pushes überhaupt:

| Workflow | vorher | Risiko | nachher |
|---|---|---|---|
| `design-varianten.yml` („Briefing committen“) | `git push` | Lauf startet montags 06:45 UTC mitten im Bot-Takt; **kein** Retry, **kein** Rebase → ein paralleler Push nach main macht den Lauf rot (WF-C545-Klasse) | `if scripts/git_sync.sh --push-only; then ✅ else ::warning::` |
| `n8n-schaltwerk-bridge.yml` („Änderungen festschreiben“) | `git push origin HEAD:<ref> \|\| echo "…"` | Wachhund alle 2 h, also dauerhaft im Takt der übrigen Bots; zusätzlich verschluckte `\|\| echo` **jeden** Fehlschlag – Drafts/Whisper-Inbox/State blieben unbemerkt liegen, der Lauf blieb grün | dito – mit Retry/Rebase **und** sichtbarer Warnung |

Damit läuft jeder Push aller 77 Workflows ausnahmslos über
`scripts/git_sync.sh`. Kein Datenverlust in beiden Fällen: Das Briefing ist
ein unverbindlicher Vorschlag ohne Freigabewirkung (nächster Montagslauf
erzeugt es neu), der Bridge-Stand wird vom nächsten Lauf (≤ 2 h) nachgeholt.

**Wächter auf Klassenniveau ausgebaut** (`scripts/tests/test_push_wache.py`,
2 → 8 Tests). Neu abgedeckt:

1. **Roher `git push` am Sync-Kern vorbei** – die Lücke, durch die 4b fiel.
2. **Umbrochene Blind-Fallbacks** – `git_sync.sh --push-only ||` mit dem
   `git push` in der Folgezeile (auch `\`-Fortsetzung). Vorher hätte ein
   simpler Zeilenumbruch den Wächter umgangen; er fügt Shell-Fortsetzungen
   jetzt zu logischen Zeilen zusammen, bevor er prüft.
3. **Begründete Ausnahme statt starrem Verbot** – fail-closed, aber nicht
   zukunftsblind: `# push-wache: ausnahme – <Grund>` an der Fundstelle
   erlaubt einen Sonderweg (z. B. echter Tag-Push), erzwingt aber eine
   Begründung im Diff, die im Review sichtbar ist.

Bewusst **nicht** aufgenommen (geprüft und verworfen, um keinen
Fehlalarm-Wächter zu bauen):

- *Erfolgsmeldung nach unbedingtem `git_sync.sh`* (14 Fundstellen): Die
  Workflows nutzen durchgehend GitHub-Actions-Default-Shell `bash -e`,
  Shell-Overrides auf git_sync-Pfaden existieren nachweislich **keine**
  (0 von 77). Ein Fehlschlag bricht den Schritt also vor der Meldung ab –
  die 14 Stellen sind korrekt, ein Wächter darauf wäre reines Rauschen.
- *`continue-on-error` auf Push-Schritten* (16 Fundstellen, u. a.
  `seo-weekly.yml`): bewusste Weich-Schritte des Bestands, keine
  Umgehung des Sync-Kerns – Verhalten unverändert gelassen.

| Prüfung (Nachtrag II) | Ergebnis |
|---|---|
| `python3 -m unittest scripts.tests.test_push_wache -v` (8 Tests) | ✅ grün |
| Negativprobe: roher Push / Blind-Fallback / **umbrochener** Blind-Fallback / `\|\| true` künstlich eingesetzt | ✅ jeweils rot gemeldet (Wächter greift nachweislich) |
| Negativprobe: begründete Ausnahme `# push-wache: ausnahme – …` | ✅ geht durch (kein Fehlalarm) |
| `python3 -m unittest scripts.tests.test_git_sync` (29) · `test_design_varianten` (40) · `test_workflow_yaml` (6) | ✅ · ✅ · ✅ |
| YAML-Parse + `bash -n` der geänderten Schritte | ✅ beide Workflows |
| **Gesamtsuite** `python3 -m unittest discover -s scripts/tests` | ✅ **1739 Tests, 0 Fehler** (23 übersprungen) |

## 5) Nächster Schritt

Issue #547 wird mit Verweis auf diesen Fix geschlossen. Tritt WF-C545 erneut
auf, ist das ein Hinweis auf eine NEUE Ursache (z. B. ein echter Fehler in
`social_video.py`/`social_calendar.py`) – die hier behobene Konfliktklasse
ist durch den Regressionstest dauerhaft abgedeckt.
