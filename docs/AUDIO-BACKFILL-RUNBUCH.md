# Runbook · Audio-Backfill (`deploy.yml` mit `audio_backfill=true`)

**Wofür:** Das Vorlese-Audio liegt als echte Studiospur pro Artikel auf dem
`gh-pages`-Zweig (`audio/articles/<slug>.mp3`). Fehlt einem Artikel die Spur,
liest der Browser des Lesers mit der Gerätestimme vor — hörbar, aber nicht das
Niveau, das die Seite sonst hat. Der Backfill vertont **alle** fehlenden
Artikel in **einem** Lauf statt häppchenweise.

Stand 12.09.2026: **18 von 31** Live-Artikeln mit Studiospur, **13** ohne.

---

## 1. Kurzfassung

```bash
# Auslösen (Produktiv-Deploy — bewusst von Hand):
gh workflow run deploy.yml -f audio_backfill=true

# Fortschritt ansehen (ID aus der Ausgabe des Befehls oben):
gh run watch <run-id>

# Nachher prüfen:
python3 scripts/audio_coverage_check.py --ref origin/gh-pages
#   Ziel: „31/31 Live-Artikel mit Tonspur · ✅ Jeder Live-Artikel hat …"
```

Dauer: **rund 60–90 Minuten** (Vertonung), plus ~5 Minuten für Checkout,
Gates, Hugo-Build und Veröffentlichung.

Der Lauf veröffentlicht am Ende die Seite — er ist ein **vollwertiger Deploy**,
nur mit größerem Ton-Budget. Deshalb gehört das Auslösen in deine Hand,
nicht in einen Zeitplan.

---

## 2. Brauche ich das überhaupt?

Ein **normaler** Deploy (jeder Push auf `main`) vertont ebenfalls, nur
gedeckelt: maximal `audio_limit_new` (25) neue Spuren **und** höchstens
20 Minuten Vertonung je Lauf, newest-first. Die Warteschlange ist konvergent:
fertige Spuren bleiben, der nächste Lauf macht dort weiter. 13 Lücken
schließen sich so von selbst in etwa 2–3 regulären Deploys (ein bis zwei Tage).

**Backfill lohnt sich, wenn** die Lücke heute zu hören ist und nicht erst
übermorgen verschwinden soll — oder nach einem größeren Bestandszuwachs
(z. B. viele neue Artikel auf einmal).

**Backfill ist unnötig, wenn** gerade ein Deploy lief, der schon fast alles
nachgezogen hat. Vorher kurz messen:

```bash
python3 scripts/audio_coverage_check.py --ref origin/gh-pages
```

Kein Nachweis („unbekannt") ist **kein** „0 %" — dann ist nur `gh-pages`
gerade nicht erreichbar.

---

## 3. Vor dem Auslösen: 30 Sekunden Queue-Check

```bash
gh run list --workflow deploy.yml --limit 3
```

Ist der oberste Lauf `in_progress`, wartet dein Backfill, bis er dran ist.
**Wichtig:** GitHub hält je Warteschlangen-Gruppe (`pages-deploy`) genau
**einen** wartenden Lauf vor. Kommt in der Wartezeit ein neuer Push auf `main`
(die Content-Engine committet täglich), wird der **wartende** Lauf mit
`cancelled` verdrängt — er hat dann keine einzige Zeile ausgeführt.

So erkennst du das: Dauer unter einer Minute, im Log steht nichts, keine Jobs.
**Das ist kein Fehler und nichts ist verloren** — einfach erneut auslösen.
Ein **laufender** Backfill wird dagegen nie abgeschossen
(`cancel-in-progress: false`).

Tipp: möglichst in ein ruhiges Fenster legen (abends, wenn die
Tages-Workflows durch sind).

---

## 4. Was der Lauf tut

| Schritt | Wirkung |
|---|---|
| Audio-Cache holen | Vorhandene Spuren werden von `gh-pages` zurückgeholt — es wird **nichts neu vertont, was schon existiert** |
| `ff_voice_audio.py --limit-new 0 --max-seconds 5400` | Backfill hebt die Stückgrenze auf (`audio_limit_new` wird ignoriert); die **Wanduhr** ist die Grenze: 90 Minuten |
| Nachmessen (`--verify --heal`) | Jede Spur wird gemessen (Pegel, hörbarer Anteil, Laufzeit, Chunk-Karte). Fällt eine durch, wird sie **gelöscht** — dann liest die Gerätestimme vor. Lieber ehrliche Browserstimme als eine stumme Studiospur |
| Abdeckung in die Lauf-Zusammenfassung | Zwei Zahlen: **Vorher** (`gh-pages`) und **Nachher** (dieser Build) |
| Deploy auf `gh-pages` | Veröffentlichung wie bei jedem Deploy |

Feinjustieren (optional, nur mitgeben wenn nötig):

```bash
gh workflow run deploy.yml \
  -f audio_backfill=true \
  -f audio_profile=news \      # news | natural | narrator
  -f audio_backend=auto \      # auto | edge | piper
  -f audio_order=newest \      # newest | oldest | path
  -f audio_max_minutes=90      # leer = Automatik (90 bei Backfill, 20 sonst)
```

Zeitdeckel: der Vertonungsschritt bricht bei **120 Minuten** hart ab
(`continue-on-error`), der Job bei 150. Bei 90 Minuten Budget plus Anlauf ist
da Luft — der Lauf endet also regulär, nicht mit dem Hammer.

---

## 5. Nach dem Lauf

```bash
# Zahl (Quelle: gh-pages, also das, was live ausgeliefert wird):
python3 scripts/audio_coverage_check.py --ref origin/gh-pages

# Zusammenfassung des Laufs (Vorher/Nachher-Zeile):
gh run view <run-id>

# Vertonungs-Log:
gh run view <run-id> --log | grep -iE "Tonspuren|Zeitbudget|Limit erreicht"
```

Erwartung: **31/31**. Bleiben Artikel übrig (z. B. weil der 90-Minuten-Deckel
zuschlug), ist das kein Rückschlag — der nächste reguläre Deploy macht dort
weiter. Ein erneuter Backfill ist dann nur schneller, nicht notwendig.

---

## 6. Abbrechen

```bash
gh run list --workflow deploy.yml --limit 1   # ID holen
gh run cancel <run-id>
```

Abbrechen ist gefahrlos: bereits erzeugte Spuren bleiben im nächsten Lauf
erhalten (Cache), die Seite behält den alten Stand, bis wieder ein Deploy
durchläuft. Der Vertonungsschritt selbst ist mit `continue-on-error`
eingehängt — selbst ein Hänger kann den Livegang nicht verhindern, nur
verzögern.

---

## 7. Referenz

| Datei | Rolle |
|---|---|
| `.github/workflows/deploy.yml` | Eingaben (`audio_backfill`, `audio_limit_new`, `audio_max_minutes`, …) und der Vertonungsschritt |
| `scripts/ff_voice_audio.py` | Synthese, Nachmessung, Zeitbudget (`--limit-new`, `--max-seconds`, `--verify --heal`) |
| `scripts/audio_coverage_check.py` | Abdeckung messen (`--ref`, `--dir`, `--strict`, `--json`), Tagesschritt in `lesehilfen-gate.yml` |
| `docs/PREMIUM-AUDIT-2026-09-11.md` | Herkunft der Zahl „18 von 31" (Empfehlung 4) |
| `DEPLOY-218-REPARATUR-2026-09-08.md` | Warum die Wanduhr die Stückgrenze ersetzt hat |
