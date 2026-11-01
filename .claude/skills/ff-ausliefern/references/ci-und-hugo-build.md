# CI, Pflicht-Check und der eine Hugo-Bau

> Wörtlich aus `CLAUDE.md` übernommen am 01.11.2026 (Skill-Umbau). Kein Satz wurde umformuliert, gekürzt oder erfunden; die Überschriften sind eine Ebene tiefer gehängt. Änderungen hier sind Änderungen am Regelwerk – sie brauchen denselben Nachweis wie vorher: Selbsttest der betroffenen Wache, dann Commit.

### CI

- `.github/workflows/e2e.yml` – Playwright bei PRs auf main + dienstags
  07:00 MESZ; HTML-Report als Artifact.
- `.github/workflows/integrity-lock.yml` – PR-Gate, Pflicht-Check
  **`Integritäts-Siegel`**. Der Job-Anzeigename ist ein Vertrag mit dem
  Ruleset (Governance-Regel C18, Konstante `PFLICHT_CHECK_NAME`): **nie
  umbenennen, keinen `paths`-Filter, kein `if:` am Job** – sonst friert `main`
  ein oder das Gate wird Scheingrün. Umbenennen nur nach
  `docs/PFLICHT-CHECK-RUNBOOK.md`.
  Der Meta-Schritt `pflichtcheck_guard.py` meldet den auf diesem Repo **nicht
  erfüllbaren** Teil (kein Ruleset verlangt den Check; Rulesets ändern ist
  Admin-Aufgabe, C15) als **bekannten Dauerzustand**: Exit 0 mit `::warning::`,
  das 🛑 bleibt in Log und Summary – Erklärung `PFLICHT_CHECK_DAUERZUSTAND`,
  Prüffrist bis 31.12.2026, harter Ausweg `--strict`. Nicht „reparieren“, nicht
  grün waschen, nicht im Workflow auf `--strict` umstellen; Rückbau und Ablauf
  stehen im Runbook-Abschnitt „Dauerzustand“.
- Agenten-Tokens haben KEINE `workflows`-Permission: Workflow-Dateien nur
  per Patch/PR mit vollwertigem Token ändern (siehe README, Known Issue).

### Hugo-Build: eine Fehlerausgabe für alle Workflows (seit 03.10.2026)

**Jeder Hugo-Bau läuft über `./.github/actions/hugo-build`.** Direkte
`run: hugo …`-Zeilen sind ein Befund (H6).

```yaml
- name: Seite bauen
  uses: ./.github/actions/hugo-build
  with:
    args: "--minify"
    label: "Qualitäts-Gate"
```

**Warum.** Am 02.10.2026 starb der Build an einem leeren Verzeichnis unter
`content/`. Die Suche dauerte Stunden, weil fünf Workflows die Fehlerzeile
vernichteten: `> /dev/null 2>&1` (seo-weekly, 2×), `|| true` (bot-watchdog),
`--quiet` (e2e, layout-ai, visual-data-gate). Ein Schritt, der rot wird und
nichts sagt, ist teurer als einer, der grün durchläuft.

Die Action garantiert ohne Zutun des Aufrufers: `pipefail` + `PIPESTATUS[0]` +
`tee`, eine `::error title=…::`-Annotation, einen Block in
`$GITHUB_STEP_SUMMARY` und eine **Selbstdiagnose**, die aktiv nach leeren
Verzeichnissen sucht — die sieht `git status` grundsätzlich nicht.

**`--quiet` wird abgelehnt** (Exit 2). Ruhe gibt es über die Logdatei, nicht
durch Wegwerfen der Diagnose.

**Darf ein Bau scheitern?** Dann `weiter-bei-fehler: "true"` statt `|| true`.
Der Fehlschlag bleibt sichtbar, er stoppt nur den Job nicht. *Toleriert* und
*unbemerkt* sind zwei verschiedene Dinge.

Wache `scripts/hugo_build_vertrag.py` (H1–H8) läuft im Qualitäts-Gate.
Ausnahmen nur mit Begründung in `AUSNAHMEN` — ein toter Eintrag ist selbst ein
Befund. Runbook: `docs/ANLEITUNG-HUGO-BUILD.md`.
