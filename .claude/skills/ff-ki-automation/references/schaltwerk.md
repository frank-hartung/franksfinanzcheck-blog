# Schaltwerk: Automationen statt Zapier

> Wörtlich aus `CLAUDE.md` übernommen am 01.11.2026 (Skill-Umbau). Kein Satz wurde umformuliert, gekürzt oder erfunden; die Überschriften sind eine Ebene tiefer gehängt. Änderungen hier sind Änderungen am Regelwerk – sie brauchen denselben Nachweis wie vorher: Selbsttest der betroffenen Wache, dann Commit.

### Schaltwerk: Automationen statt Zapier (seit 01.10.2026)

`scripts/schaltwerk.py` ist der repo-eigene Zapier-Ersatz: **Trigger → Filter
→ Aktion**, deklariert in `data/automationen.yaml`, getaktet von
`.github/workflows/schaltwerk.yml` (alle 30 min, dazu `workflow_dispatch` und
`repository_dispatch` als kostenloser Webhook). Kein Fremddienst, keine
Task-Limits, keine Kosten.

- **Arbeitsteilung:** Der Social-Autopilot bleibt der Sender für neue Artikel
  und Evergreen-Recycling. Das Schaltwerk dirigiert und füllt Lücken
  (Update-Wellen, Reach-Kuratierung, Wachhunde, Planerneuerung, Ad-hoc-Posts).
  Jede sendende Regel braucht `dedupe_key` und `throttle` – sonst Doppelposts.
- **Leitplanken (durch Selbsttest + Unit-Tests erzwungen):** Agent-Reach-Signale
  nie direkt posten (nur `themen_vorschlag`); kostenpflichtige Kanäle (X) nicht
  fest verdrahten; Standby ist kein Fehler; `--dry-run` schreibt nichts;
  gescheiterte Ketten gelten nicht als erledigt.
- **Vor jedem Umbau am Regelwerk:** `npm run test:schaltwerk`, danach
  `python3 scripts/schaltwerk.py --dry-run`.
- Cockpit: `SCHALTWERK-STATUS.md` · Anleitung: `docs/ANLEITUNG-SCHALTWERK.md`.
