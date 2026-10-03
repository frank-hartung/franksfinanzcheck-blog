# Hugo-Build: eine Fehlerausgabe für alle Workflows

**Stand:** 2026-10-03 · **Action:** `.github/actions/hugo-build` · **Wache:** `scripts/hugo_build_vertrag.py` (H1–H8)

---

## Worum es geht

Am 02.10.2026 starb der Build an einer einzigen Zeile:

```
ERROR render of "sitemap" failed: layouts/sitemap.xml:40:29:
      wrong type for value; expected string; got []string
```

Ursache war ein **leeres Verzeichnis** unter `content/`. Die Suche danach dauerte
Stunden — nicht, weil der Fehler schwer war, sondern weil ihn fast jeder
Workflow unsichtbar machte:

| Workflow | Alte Zeile | Wirkung |
|---|---|---|
| `seo-weekly.yml` (2×) | `hugo --minify > /dev/null 2>&1` | Schritt wird rot, Protokoll bleibt **leer** |
| `bot-watchdog.yml` | `hugo --minify \|\| true` | Fehlschlag spurlos verschluckt |
| `e2e.yml` | `hugo --quiet …` | Fehlerzeile unterdrückt |
| `layout-ai.yml` | `hugo --minify --quiet` | Fehlerzeile unterdrückt |
| `visual-data-gate.yml` | `hugo --minify --quiet …` | Fehlerzeile unterdrückt |

Ein Schritt, der rot wird und **nichts sagt**, ist teurer als einer, der grün
durchläuft: Er kostet Zeit und erzieht zum Wegsehen.

---

## Benutzung

```yaml
- name: Hugo installieren (Extended, verifiziert, mehrquellig)
  uses: ./.github/actions/install-hugo
  with:
    version: "0.164.0"

- name: Seite bauen
  uses: ./.github/actions/hugo-build
  with:
    args: "--minify"            # Standard; weitere Flaggen frei
    label: "Qualitäts-Gate"     # erscheint in Annotation + Zusammenfassung
```

### Eingaben

| Eingabe | Standard | Bedeutung |
|---|---|---|
| `args` | `--minify` | Hugo-Argumente. **Ohne `--quiet`** (wird abgelehnt). |
| `label` | `Seite bauen` | Klartext-Name dieses Baus. |
| `log` | `hugo-build.log` | Logdatei; wird **immer** geschrieben, auch im Erfolgsfall. |
| `zeilen` | `40` | Log-Zeilen in der Zusammenfassung bei Fehlschlag. |
| `weiter-bei-fehler` | `false` | `true` = Fehlschlag laut melden, Job trotzdem weiterlaufen lassen. |

### Ausgaben

| Ausgabe | Bedeutung |
|---|---|
| `rc` | Exit-Code von Hugo — auch bei `weiter-bei-fehler: "true"` |
| `log` | Pfad der Logdatei (für Folgeschritte, Artefakt-Upload) |
| `dauer` | Bauzeit in Sekunden |
| `seiten` | Von Hugo gemeldete Seitenzahl |

---

## Was die Action garantiert

1. **`set -o pipefail` + `PIPESTATUS[0]` + `tee`** — der Exit-Code überlebt die
   Pipe. Ohne das meldet *jeder* getee'te Build Erfolg, auch der kaputte.
   Beide Netze sind einzeln bewiesen (Proben `S1a`–`S1c`).
2. **`::error title=…::`** — der Fehler erscheint als Annotation direkt im PR,
   nicht nur im Rohlog. (Rohlogs sind nicht aus jeder Umgebung abrufbar.)
3. **`$GITHUB_STEP_SUMMARY`** — Kommando, Exit-Code, Dauer, erste Fehlerzeile und
   Log-Auszug stehen auf der Übersichtsseite des Laufs.
4. **Selbstdiagnose** — bei Fehlschlag sucht die Action aktiv nach den bekannten
   Ursachen (siehe unten).
5. **`--quiet` wird abgelehnt** (Exit 2). Die Flagge verschluckt die
   entscheidende Zeile sogar bei eingefangener Ausgabe. Ruhe im Protokoll gibt
   es über die Logdatei — nicht durch Wegwerfen der Diagnose.

---

## Die Selbstdiagnose

| Erkannt an | Meldung |
|---|---|
| `find content data -type d -empty` | Liste der leeren Verzeichnisse + Behebung |
| `wrong type for value` im Log | Das Template-Muster, das ihn erzeugt, + Fix |
| `TOCSS` / `libsass` im Log | Hugo ist nicht Extended |

**Warum ausgerechnet leere Verzeichnisse?** Weil `git status` sie
**grundsätzlich nicht** meldet — auch nicht mit `--ignored`. Jede Wache, die
„Arbeitsbaum sauber" nur über `git status` beweist, ist an dieser Stelle blind.
Der Defekt ist zusätzlich **sortierabhängig**: Ein leerer Ordner unter
`content/` tötet den Build nur, wenn er *nach* dem ersten string-liefernden
Eintrag einsortiert (`drafts/` ja, `_0probe/` oder `zz/` nein). Deshalb listet
die Action **alle** leeren Verzeichnisse — Raten hilft hier nicht.

---

## `weiter-bei-fehler` statt `|| true`

```yaml
- uses: ./.github/actions/hugo-build
  with:
    weiter-bei-fehler: "true"
```

Der Unterschied zum alten `|| true`: Der Fehlschlag bleibt **sichtbar**
(Annotation + Zusammenfassung + `rc`-Ausgabe), er stoppt nur den Job nicht.
*Toleriert* und *unbemerkt* sind zwei verschiedene Dinge.

Verwendet in `bot-watchdog.yml` (Watchdog soll auch bei rotem Bau messen) und
`premium-governance.yml` (der Exit-Code ist dort der **Messwert**, den
`governance_gate.py --emit build` bewertet).

---

## Kommandos

```bash
npm run build:vertrag        # H1–H8 prüfen (läuft im Qualitäts-Gate)
npm run build:selftest       # Verhaltens- + Sabotage-Proben
python3 scripts/hugo_build_vertrag.py --json
```

Der Selbsttest führt den **echten Shell-Rumpf** der Action gegen ein
Hugo-Attrappen-Programm aus: grüner Bau, roter Bau, leeres Verzeichnis,
`weiter-bei-fehler`, stummer Abbruch — plus neun Sabotage-Proben. Eine Wache,
die nur Wörter im YAML zählt, lässt sich mit einem Kommentar betrügen.

---

## Eine neue Baustelle hinzufügen

1. `uses: ./.github/actions/hugo-build` statt `run: hugo …`
2. `label` setzen — ein Name, den man in der Lauf-Übersicht wiedererkennt.
3. Braucht der Schritt Umgebungsvariablen (z. B. `HUGO_JSDELIVR_SHA`): auf
   **Job-Ebene** setzen. Ein `env:` am `uses:`-Schritt erreicht die Schritte
   einer Composite-Action nicht zuverlässig.
4. `npm run build:vertrag` — H6 meldet jeden direkten Aufruf.

## Eine Ausnahme eintragen

Nur, wenn die Action die Semantik wirklich nicht abbilden kann. Eintrag in
`AUSNAHMEN` in `scripts/hugo_build_vertrag.py` — **mit Begründung**. Eine
Ausnahme ohne Grund ist eine Ausrede, und die Wache meldet sie als Befund.
Wird die Datei später umgebaut und baut gar kein Hugo mehr, meldet H6 den
Eintrag als *toten Eintrag* — so wächst hier kein Regal voller Altlasten.

**Aktuelle Ausnahme:** `affiliate-integrity-daily.yml` — eigene
3-fach-Wiederholung mit `rm -rf public` bei endgültigem Fehlschlag, damit
`ensure_build()` nicht gegen ein halbfertiges Artefakt „aktuell" beweist. Die
Fehlerausgabe ist dort bereits vollständig.
