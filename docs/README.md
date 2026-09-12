# 📁 docs/ – Dokumentation & Arbeitsmaterialien

Dieser Ordner sammelt **einmalige** Dokumente, Pläne und Arbeitsdateien,
damit der Repo-Root sauber bleibt (Profi-Cleanup 20.08.2026, erweitert
im Premium-Audit 12.09.2026).

**Was hier liegt:**
- `ANLEITUNG-*.md` – alle Betriebsanleitungen an einem Ort
  (12.09.2026 konsolidiert: dazu gekommen sind die fünf, die vorher im
  Root lagen; alle Skript-/Workflow-Verweise zeigen jetzt auf `docs/`)
- `archiv/` – datierte One-Shot-Dokumente (REPARATUR-Logs, Optimierungs-
  Kampagnen, Studio-Dokus, Aktionspläne) – Historie bleibt lesbar,
  liest keine Automatik
- Entscheidungsdokumente, Pläne, Workbooks und Vorschau-Bilder

**Was bewusst NICHT hier liegt (bleibt im Root):**
- `README.md`, `CLAUDE.md`, `DESIGN.md`, `PRODUCT.md` – Kerndokumente
  auf Root-Ebene
- Drei Live-Eingaben des Watchdogs: `PRODUKTIONS-STATUS.md`,
  `AFFILIATE-INTEGRITY-REPORT.md`, `PINTEREST-REPORT.md` –
  `scripts/bot_watchdog.py` liest sie direkt aus dem CI-Checkout
  (mtime-/Inhaltsprüfung); die Workflow-Schreiber halten sie aktuell

**Was nicht mehr versioniert wird (seit 12.09.2026):**
- Alle übrigen Root-Reports (`*-REPORT.md`, `*-STATUS.md`) und die
  `EDITORIAL-SCORECARD.md`: Die Workflows schreiben sie weiterhin
  (sichtbar in den Lauf-Logs), aber sie landen nicht mehr im Git –
  spart ~8 Pushes pro Tag und nimmt der Bot-Flotte die Push-Rennen.
  `report_hygiene.py` überwacht, dass sich im Root nichts ansammelt.
- Dot-Caches (`.grammar_report.json`, `.spellcheck_report.json`,
  `.keyword_suggestions.json`, `.affiliate_report.json`), `patches/`
  (abgearbeitete Patches) und `static/audio/` (Alters-Handwerkstück).
  Einzige Ausnahme: `.indexnow_submitted.json` bleibt versioniert –
  es ist der IndexNow-Dedup-State über Läufe hinweg.

> Hinweis: Edits in `docs/` triggern **keinen** Deploy
> (`deploy.yml` → `paths-ignore: docs/**`).
