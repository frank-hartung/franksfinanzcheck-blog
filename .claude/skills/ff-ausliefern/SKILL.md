---
name: ff-ausliefern
description: "Benutzen bei allem, was die Live-Site erreicht oder blockiert: GitHub-Workflow, Action, Deploy, Pages, Cloudflare-Worker, Hugo-Build-Fehler, Pflicht-Check / Integritäts-Siegel, Ruleset, Concurrency, ein roter Lauf ohne Ursache, Alarm-Issue, Backup/Restore, Restore-Drill, Rebase und Merge einer PR, 'die Seite ist 404', 'der Deploy hängt'. Dieser Skill enthält CI-Verträge, die eine Hugo-Bau-Action, Blustradius und Siegel-Reihenfolge, Alarm-Routing, Release-Scorecard, Backup-Einrichtung und die Merge-Disziplin. Auslöser auch bei: 'welcher Schritt blockiert?', 'lauf gelb/wartend', 'kann ich mergen?'. Nicht für Content-Regeln (ff-produzieren) und nicht für Gate-Baukunst (ff-pruefen)."
metadata:
  version: 1.0.0
  besitz: repo-eigen – kein Eintrag in skills-lock.json, nie von `npx skills update` anfassen
  quelltext: CLAUDE.md-Kernregeln, wörtliche Details in references/
---

# Ausliefern, ohne etwas zu geiseln

Zwei Fehlerklassen trennen diesen Skill: **die lauten** (Build bricht, Gate rot)
und **die teuren stillen** (ein Mess-Schritt hält die Auslieferung an, ein
wartender Lauf meldet nichts, ein Alarm hat keinen Schließpfad). Alles hier ist
wörtlich aus `CLAUDE.md` übernommen – inklusive der Vorgänge (#676, #740, #922,
#654, #912), aus denen die Regeln entstanden sind.

## Wann dieser Skill zählt

- Du änderst `.github/workflows/**`, `.github/actions/**` oder eine Action.
- Ein Deploy wird rot, bleibt liegen, oder wird grün, obwohl etwas fehlt.
- Ein Alarm-Issue ist offen und lässt sich nicht schließen.
- Du willst mergen, reben oder einen Konflikt auflösen.
- Backup, Restore-Drill, Environment oder Secrets sind das Thema.

## Die harten Kernregeln

1. **Auslieferung vor Siegel.** Nach dem Auslieferungs-Beleg
   (`id: artefakt`) folgt im `deploy`-Job nichts mehr. Beweisläufe siegeln im
   Job `release-seal` (`if: always()`) – **erst liefern, dann siegeln**.
2. **Jeder Schritt kennt seinen Blustradius**
   (`data/blustradius-deploy.yml`: `infra` · `inhalt` · `gate-selbsttest` ·
   `werkzeug`). Ein `werkzeug`-Schritt darf die Live-Site nie anhalten; ein
   neuer Schritt ohne Register-Eintrag ist ein Befund, kein Zufall.
3. **Exit 2 ist kein Inhaltsbefund.** `0` weiter · `1` echter Befund, harter
   Stopp · `2` Werkzeugfehler: `::error::` + Job-Output, Auslieferung läuft
   weiter. Kein `continue-on-error`, kein `|| true`.
4. **Jeder Hugo-Bau läuft über `./.github/actions/hugo-build`.** Direkte
   `run: hugo …`-Zeilen sind ein Befund (H6); `--quiet` wird abgelehnt.
   Tolerieren heißt `weiter-bei-fehler: "true"`, nicht verschwinden lassen.
5. **Kein Merge vor dem grünen Abschluss DIESES Commits** –
   `gh pr checks <nr> --watch --fail-fast`. Ein Rebase ist ein neuer Stand.
6. **Ein Alarm braucht Besitzer und Schließpfad** (`owner`, `severity`,
   `channel`); chronische Befunde melden alle 72 h, akute nach `AKUT_TAKT`
   (0/1/6/24 h). Ein Dauer-Alarm ist keine Warnung, sondern eine Rechnung.
7. **Der `Integritäts-Siegel`-Jobname ist ein Vertrag** – nie umbenennen, kein
   `paths`-Filter, kein `if:` am Job. Sein nicht erfüllbarer Teil ist ein
   dokumentierter Dauerzustand, kein Schaden.
8. **Workflow-Dateien sind sicherheitsrelevant** (Kern-Regel 3): Agenten-Tokens
   haben keine `workflows`-Permission; Änderungen nur mit ausdrücklichem
   Auftrag des Inhabers.

## Katalog

| Deine Frage | Antwort im Detail |
|---|---|
| Welche CI-Verträge gelten, wie baue ich richtig, warum eine Action? | `references/ci-und-hugo-build.md` |
| Wer blockiert die Auslieferung, wie sitzt das Siegel, was gehört in die Messkette? | `references/deploy-blockaden.md` (C34, C38, #740, #922) |
| Wer bekommt den Alarm, wie rechnet die Scorecard, wie schließt ein Ticket? | `references/alarme-und-scorecard.md` (C14, C28, C35, C45) |
| Konflikt mit einem fremden Artikelstand, Backup rot, Rebase, eine Heilung überschrieben? | `references/bestand-backup-merge.md` (#590, #761, #780) |

## Kommando-Notausgang

```bash
npm run release:isolation            # blockierte Kandidaten isolieren (Trockenlauf)
npm run release:scorecard            # Produktionswahrheit über die heutigen Kandidaten
python3 scripts/blustradius_register.py --check
python3 scripts/worker_freigabe_wache.py      # wartende Deploy-Freigaben
npm run backup:frische                       # Frische der Offsite-Sicherung
gh pr checks <nr> --watch --fail-fast
```

## Nicht zuständig für

- **Ob ein Artikel veröffentlichbar ist** → `ff-produzieren`
- **Wie ein Gate gebaut und getestet wird** → `ff-pruefen`
- **Modelle, Recherche, Automationen und Geldflächen** → `ff-ki-automation`
