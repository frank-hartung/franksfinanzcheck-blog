# 🗄️ _archiv – nicht mehr verdrahtete Werkzeuge

Diese Skripte werden von keinem Workflow mehr aufgerufen (Audit 10.08.2026).
Sie bleiben als Referenz/nur für manuelle Nutzung erhalten.

- `add_affiliate_urls.py` – einmaliges Setzen von Affiliate-URLs
- `fix_cover_alts.py` – Alt-Text-Einmal-Korrektur (erledigt)
- `fix_nbsp.py` – NBSP-Einmal-Bereinigung (erledigt)
- `make_workbook_pdf.py` – PDF-Erzeugung für das Pinterest-Workbook
- `update_docs.py` – Docs-Synchronisation (ersetzt durch manuelle Pflege)

**Reaktivieren:** Datei zurück nach `scripts/` verschieben und im Workflow
verdrahten. Nicht aktiv verwaist: `post_utils.py`, `pinterest_auth.py`,
`generate_drafts.py`, `quality_score.py` (werden von anderen Skripten
importiert), sowie die Dokumentations-Tools `publish.py` und
`set_check24_links.py` (in README/ANLEITUNG referenziert).
