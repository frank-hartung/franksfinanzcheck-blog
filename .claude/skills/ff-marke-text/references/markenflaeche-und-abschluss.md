# Markenfläche README und Abschlüsse mit Nachweis

> Wörtlich aus `CLAUDE.md` übernommen am 01.11.2026 (Skill-Umbau). Kein Satz wurde umformuliert, gekürzt oder erfunden; die Überschriften sind eine Ebene tiefer gehängt. Änderungen hier sind Änderungen am Regelwerk – sie brauchen denselben Nachweis wie vorher: Selbsttest der betroffenen Wache, dann Commit.

### README ist Markenfläche (DAUERVORGABE)

Das `README.md` wird indexiert und steht bei einer Markensuche neben dem
Ratgeber. **Dort steht nichts über die Maschine.** Keine Automatik, keine
Abläufe, keine Gates, keine Werkzeugnamen, keine Dateipfade, kein „0 € Stack" –
auch nicht als Stolz-Abschnitt über eine frische Integration (genau so entstand
Vorgang WF-A4E0 / Meldung #552 am 03.10.2026, nach demselben Fall am 01.10.).

- **Technisches gehört nach `docs/ENTWICKLER-WERKZEUGE.md`**, im README höchstens
  der Verweis darauf. Projektberichte bleiben im Root (`*-PREMIUM-*.md`).
- **Ausnahme nur mit Begründung** in `data/brand_surface_allowlist.txt`.
- **Vor jedem README-Commit:** `npm run marke:check`
- **Die Commit-Sperre stellt sich selbst scharf.** `scripts/haken_wache.py`
  hängt `.githooks/pre-commit` bei `npm install` (prepare) und bei jedem
  Marken-Lauf ein – vorhandene Haken bleiben dabei aktiv (`pre-commit.lokal`).
  Kontrolle: `npm run hooks:status`, von Hand: `npm run hooks:install`.
  **Niemals `core.hooksPath` von Hand setzen** – das legt alle anderen Haken
  still; der Wächter zieht solche Arbeitskopien um und begründet es.
- Regressionstest: `npm run test:marke` (Wache + Wächter) · Hintergrund:
  `MARKENFLAECHE-README-PREMIUM-2026-10-04.md` und
  `LEITPLANKEN-SELBSTSCHARF-PREMIUM-2026-10-04.md`, Runbook:
  `docs/MARKEN-OBERFLAECHE-RUNBOOK.md`.

### Vorgänge werden mit Nachweis geschlossen (DAUERVORGABE)

Eine behobene Meldung bekommt einen **Abschlussvermerk**, und zwar nicht von
Hand: Das persönliche Zugangsrecht darf keine Kommentare schreiben (HTTP 403,
belegt am 04.10.2026 an Meldung #552). Zuständig ist
`.github/workflows/vorgangs-abschluss.yml` – sofort beim Zusammenführen und
täglich als Nachlauf.

- **Im Vorschlag immer `Closes #<Nummer>`** schreiben; daraus leitet sich der
  Vermerk ab.
- Nie von Hand nachkommentieren; fehlt ein Vermerk, nachtragen lassen:
  `npm run vorgang:abschluss -- --pr <Nummer> --apply` (oder `vorgang:nachtrag`).
- **Issue-Kommentare sind Markenfläche.** Der Text läuft vor dem Absenden durch
  die Marken-Wache; Betriebssprache wird zurückgenommen, nicht veröffentlicht.
- Regressionstest: `npm run test:vorgang` · Doku:
  `docs/ENTWICKLER-WERKZEUGE.md`, Abschnitt „Abschlussvermerk an die Meldung".
