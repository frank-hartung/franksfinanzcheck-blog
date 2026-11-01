# Werkbank und Internet-Recherche

> Wörtlich aus `CLAUDE.md` übernommen am 01.11.2026 (Skill-Umbau). Kein Satz wurde umformuliert, gekürzt oder erfunden; die Überschriften sind eine Ebene tiefer gehängt. Änderungen hier sind Änderungen am Regelwerk – sie brauchen denselben Nachweis wie vorher: Selbsttest der betroffenen Wache, dann Commit.

### Werkbank: die eigene Antwortmaschine statt Perplexity (seit 03.10.2026)

`scripts/antwortwerk.py` beantwortet Recherchefragen **mit Belegen** und
ersetzt damit die Rolle, für die sonst ein Perplexity-Abo nötig wäre.
Kette: SearXNG sucht → Allowlist filtert → Crawl4AI liest → Playwright
beweist → Synthese zitiert. SSOT `data/werkbank.yaml`, Vertrag
`scripts/werkbank_gate.py` (B1–B9, fail-closed, `--selftest` mit zehn
Sabotage-Proben).

- **Perplexity nicht einbauen.** Bewusste Entscheidung, nicht aus Sparzwang:
  Volltext statt Snippet, Quellenrang statt Anbieterrelevanz, Affiliate-Sperre,
  Zitatprüfung im echten Browser, 0 €. Begründung in
  `WERKBANK-PREMIUM-2026-10-03.md`, Abschnitt 2. Das Dossier-Format folgt der
  Perplexity-Agent-API, damit ein späterer Anschluss ein Adapter bleibt.
- **Die vier Gewerke:** Antwortwerk (Faktenfrische + GEO-Check), Crawl4AI
  (Markdown-Lesen, löst Jina ab), Playwright (Browser-Beweis), Composio
  (Konnektor fürs Schaltwerk).
- **Ohne Beleg kein Satz.** Ohne `GROQ_API_KEY`/`GEMINI_API_KEY` arbeitet das
  Antwortwerk **extraktiv** – wörtliche Passagen mit `[1]`-Belegen, kein
  Sprachmodell, keine erfundene Zahl. Secret hinterlegen schaltet Synthese
  scharf, die Belegpflicht bleibt. Exit 3 = keine Quelle belegfähig (Warnung,
  kein Abbruch).
- **B9 ist nicht verhandelbar:** eigene Domain und alle aus
  `scripts/check24_links.yaml` abgeleiteten Partnerdomains sind als Quelle
  gesperrt. `domain_von()` entfernt dabei Port, Zugangsdaten und `www.` –
  sonst läuft `check24.de:443` an der Liste vorbei (war ein echter Bug).
- **Standby ist grün.** Fehlendes Secret oder fehlendes Modul = ⏸, Exit 0. Nur
  `--strict` (für CI) verlangt alle Gewerke aktiv.
- **Additiv:** `sammle_web()` in `agent_reach_research.py` versucht Crawl4AI
  zuerst und fällt auf Jina zurück. Ohne Crawl4AI ist das Verhalten
  unverändert. `faktenfrische.py` und `schaltwerk.py` sind unberührt – die
  Werkbank liefert Signale, nicht Freigaben.
- **Vor jedem Umbau:** `npm run test:werkbank`, danach
  `python3 scripts/werkbank_gate.py --selftest`.
- Cockpit: `WERKBANK-STATUS.md` · Anleitung: `docs/ANLEITUNG-WERKBANK.md`.

### Internet-Recherche (Agent Reach, seit 12.09.2026)

- **Ad-hoc-Recherche/Suche/URL-Lektüre:** immer über den Skill
  `.claude/skills/agent-reach/` (Routing-Tabelle + `references/` beachten;
  vor Login-/Multi-Backend-Plattformen `agent-reach doctor --json` prüfen).
  Nichts „aus dem Gedächtnis" erfinden, wenn das Netz die Antwort hat.
- **Geplante Signalsammlung:** `scripts/agent_reach_research.py` liest den
  kuratierten Themenplan (`data/agent_reach/themenplan.yaml`) und legt
  Briefs unter `data/research/` ab (CI: `.github/workflows/agent-reach-research.yml`,
  Mo 08:15 MESZ). Gesundheitscheck: `scripts/agent_reach_gate.py`.
- **Leitplanken:** nur LESEN (nie posten/schreiben), keine Cookies/Logins in
  CI, Facts aus Briefs erst nach menschlicher Prüfung in kuratierte Pools
  (`data/aktuelle_entwicklungen.yaml`, `data/topics.yaml`) übernehmen.
- Installations- und Betriebsdetails: `docs/ANLEITUNG-AGENT-REACH.md`.
