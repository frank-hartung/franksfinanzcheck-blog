# Redaktionelle Sprache und die ZEIT-Latte

> Wörtlich aus `CLAUDE.md` übernommen am 01.11.2026 (Skill-Umbau). Kein Satz wurde umformuliert, gekürzt oder erfunden; die Überschriften sind eine Ebene tiefer gehängt. Änderungen hier sind Änderungen am Regelwerk – sie brauchen denselben Nachweis wie vorher: Selbsttest der betroffenen Wache, dann Commit.

### Redaktionelle Sprache (DAUERVORGABE)

Templates und wiederkehrende Formeln erzeugen Gleichförmigkeit. Für alle neuen
und überarbeiteten Texte gilt deshalb: sprachlich mindestens auf dem Niveau von
ZEIT.de, jedoch mit eigenständiger Stimme und ohne Nachahmung. Die Form folgt
dem konkreten Thema; Einstiege, Übergänge, Überschriftenrhythmus und Schlüsse
werden nicht schematisch wiederholt. Jeder Artikel braucht einen eigenen Blick,
eine konkrete Beobachtung oder ein tragfähiges Bild. Anspruch bedeutet Präzision
und gedankliche Beweglichkeit, nicht Ornament oder unnötige Komplexität.

Die ausführliche, maschinenlesbare Leitplanke steht in
`data/schreibstil.yaml` unter `eigenstaendigkeit`; Generierung und manuelle
Lesbarkeitsprüfung müssen sie berücksichtigen.

### ZEIT-Niveau-Rechtschreib-Wache (Dauerbetrieb seit 28.09.2026)

Dauerhafte Premium-Rechtschreibprüfung aller Artikel
(`scripts/zeit_rechtschreibung.py`, SSOT `data/zeit_rechtschreibung.json`).
Faktenlage: zeit.de bietet **keine** öffentliche Rechtschreib-API – die
ZEIT-Latte (s. Abschnitt Sprache) wird über die `/v2/check`-kompatible
Premium-Engine eingelöst. Provider-Kette: **Premium** (ENV `ZR_API_URL`
bzw. `ZR_USERNAME`/`ZR_API_KEY`) → **öffentlich** (nur `--oeffentlich`,
ToS verbieten Automation – im CI hart geblockt) → **offline**
(LT1–LT4-Nachbau, immer verfügbar).

- **Kosten-Regel:** kein Paid-/Netz-Provider als alleiniger Pfad –
  `require_online`/`offline_fallback` in der Config sind verboten
  (Selbsttest ST8, Exit 2).
- **Schreibvertrag:** Auto-Fix nur aus harter Regel-Allowlist mit genau
  einem Vorschlag, nie im Titel, nie in Schutzzonen (längentreue
  Maskierung), immer `sprachkern.write_verified`; Stil/Komma bleiben
  Agentur-Hand (Fund mit `owner=human`).
- **Quota:** `data/zeit_rechtschreibung_cache.json` (versioniert) –
  unveränderte Artikel kosten keine Anfrage; Verlauf in
  `data/zeit_rechtschreibung_history.jsonl`.
- **CI aktiv:** `.github/workflows/zeit-rechtschreibung.yml`
  montags 04:35 UTC (seit 28.09. aktiv; die einstige Vorlagen-Kopie in
  `workflow-ready/` ist am 30.09. entfernt – SSOT ist der aktive Workflow).
- Runbook + Datenschutz + Premium-Aktivierung:
  `docs/ANLEITUNG-ZEIT-RECHTSCHREIBUNG.md`.
