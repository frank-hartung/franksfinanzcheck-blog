# Suchradar – Serp-Erfassung ohne API

> Wörtlich aus `CLAUDE.md` übernommen am 01.11.2026 (Skill-Umbau). Kein Satz wurde umformuliert, gekürzt oder erfunden; die Überschriften sind eine Ebene tiefer gehängt. Änderungen hier sind Änderungen am Regelwerk – sie brauchen denselben Nachweis wie vorher: Selbsttest der betroffenen Wache, dann Commit.

### Suchradar: Suchergebnis-Erfassung ohne API (seit 12.10.2026)

`scripts/suchradar.py` ist der blogeigene Nachbau des Apify-Actors
`apify/google-search-scraper` – **ohne API-Anbindung**, ohne Schlüssel, ohne
Kosten. Getaktet von `.github/workflows/suchradar.yml` (täglich 07:52 MESZ).

- **Warum nicht google.com direkt:** Nutzungsvertrag, Rechenzentrums-IP mit
  CAPTCHA-Antwort, verzerrte Treffer. Stattdessen Metasuche und offene
  Indizes: `searxng` → `duckduckgo` → `duckduckgo_lite` → `mojeek` → `wikipedia`,
  alle schlüssellos. Die Begründung im Einzelnen steht in
  `scripts/serp_anbieter.py` (Modulkopf).
- **Drei Schichten über dem Abruf:** Rang-Verfolgung (Delta gegen den
  letzten Stand *derselben Anfrage*), Wettbewerbs-Radar (Häufigkeit und
  Rangtiefe getrennt), Merkmal-Erkennung (Sonderflächen).
- **Leitplanken (durch Selbsttest + 68 Unit-Tests erzwungen):** Tagesbudget
  wird *vor* dem Abruf geprüft; kein Treffer → Exit 3 statt grünes
  Schweigen; `--dry-run` schreibt nichts; Anzeigen zählen nicht;
  DuckDuckGo-Umleitungen werden entpackt; bezahlte Anbieter (Apify,
  SerpApi, serper.dev) brauchen Schlüssel **und** die Freigabe der
  Kostensperre (Fläche `serp_premium`).
- **Vor jedem Umbau an den Providern:** `npm run test:suchradar`. Die
  Parser-Tests laufen gegen echte HTML-Proben in
  `scripts/tests/serp_proben/` – fällt einer, ist die Probe veraltet.
- Cockpit: `SUCHRADAR-RADAR.md` (versioniert) · Anleitung: `docs/ANLEITUNG-SUCHRADAR.md` ·
  Bericht: `SUCHRADAR-GOOGLE-SERP-NACHBAU-PREMIUM-2026-10-12.md`.
