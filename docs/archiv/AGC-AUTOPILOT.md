# 🤖 AGC-Autopilot – Blog-Automatik nach dem Funktionsumfang von AGC Studio

> **Auftrag (Frank, 08.09.2026):** Die Blog-Automatik soll den Funktionsumfang
> von [agcstudio.ai](https://agcstudio.ai) möglichst vollständig nachbilden –
> angepasst an einen Hugo-Affiliate-Blog (CHECK24/Pinterest), **ohne** die
> bestehenden harten Qualitäts- und Kadenz-Gates zu verletzen.

**Kernprinzip:** Der Autopilot *denkt, recherchiert und plant*. Veröffentlicht
wird weiterhin **ausschließlich** über die Content-Engine v2 + ihre Gates
(`cadence_guard`, `publish_gate`, `quality_score`). Damit bleibt die
DAUERVORGABE (Mo/Mi/Fr, 2–3 Artikel/Tag) unangetastet – genau wie gewünscht.

---

## 1. Feature-Parität: AGC Studio → dein Blog

| AGC Studio | Umsetzung hier | Datei/Skript |
|---|---|---|
| **Brand Brain** (Marke, Stimme, Zielgruppe, Produkte, Avatar – einmal konfigurieren) | Zentrale Single-Source-of-Truth, wird von allen Agenten gelesen; Drift-Wächter gegen `brand_lock.yaml` | `data/brand_brain.yaml` · `scripts/brand_brain.py` |
| **6 Research-Teams** (tägliche strategische Reports) | Trending, News-Hooks, Evergreen, Pain Points, Viral Outliers, Nischen-Hooks + optional Live-Web | `scripts/research_engine.py` |
| **Research→Agent-Routing** (Reports automatisch an den richtigen Agent) | `route_topic()` ordnet jedem Thema die relevantesten Signale zu und baut einen Recherche-Brief | `scripts/research_engine.py` |
| **Blog Writing Team** (9 Spezial-Agenten) | Bestand an ~40 Wächter-/Qualitäts-Skripten (Polish, Lektorat, Rechtschreibung, Affiliate, Cover …) – unverändert aktiv | `scripts/*.py` + `.github/workflows/content-engine-v2.yml` |
| **Campaign Management System** (Promo + Researched, Kampagnen-CTA, Kalender) | Kampagnen-Datei + CTA-Override + Kampagnen-Zuordnung im Kalender | `data/campaigns.yaml` · `scripts/campaign_manager.py` |
| **Visual/Editorial Calendar** (Wochen/Monate voraus planen) | Deterministischer Redaktionskalender über die nächsten Mo/Mi/Fr-Slots | `data/editorial_calendar.yaml` |
| **Auto-Publishing** (nativ formatiert, mit Review oder Autopilot) | Bestand (Engine v2, 3-Ebenen-Fallback, Profi-Gate, Auto-Publish) – unverändert | `.github/workflows/content-engine-v2.yml` |
| **Cockpit/Übersicht** | Autopilot-Status + lesbarer Tagesreport | `AGC-AUTOPILOT-STATUS.md` · `AGC-FORSCHUNG-BERICHT.md` |

**Bewusst NICHT nachgebaut** (nicht blog-relevant / andere Produkte): Avatar-Videos,
AI-Szenen, TikTok/Instagram/YouTube-Posting. Dafür existiert die bestehende
Pinterest-/Mastodon-Pipeline (`pinterest_engine.py`, `social_poster.py`), die als
„11-Plattformen-Ersatz" für deinen Kanal-Mix dient.

---

## 2. Die Pipeline im Überblick

```
  ┌─────────────────────────────────────────────────────────────────┐
  │ AGC-AUTOPILOT (täglich 05:45 MESZ)                                │
  │   1) Brand Brain validieren      (fail-closed gegen brand_lock)  │
  │   2) Recherche-Report erzeugen   (6 Teams, hybrid/deterministisch)│
  │   3) Redaktionskalender planen   (Mo/Mi/Fr, 4 Wochen Vorlauf)     │
  │   4) Autopilot-Status schreiben                                   │
  └───────────────────────────────┬─────────────────────────────────┘
                                  │  schreibt data/research/ + Kalender
                                  ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │ CONTENT-ENGINE v2 (Mo/Mi/Fr 08:10/16:10/19:40)                    │
  │   Schreiber liest über scripts/agc_context.py:                    │
  │     · MARKEN-HIRN (Brand Brain)                                   │
  │     · TAGES-RECHERCHE (geroutete Signale)                         │
  │     · KAMPAGNEN-CTA (aktive Kampagne)                             │
  │   → Profi-Gate → Kadenz-Gate → Qualitäts-Kette → LIVE              │
  └─────────────────────────────────────────────────────────────────┘
```

Wichtig: Fällt der Autopilot-Workflow einmal aus, schreibt die Engine einfach mit
dem letzten Report weiter (graceful degradation) – nie ein Ausfalltag.

---

## 3. Bedienung

### 3.1 Alles auf einmal (Orchestrator)
```bash
python3 scripts/autopilot.py --run          # Recherche + Kalender + Status
python3 scripts/autopilot.py --status       # Cockpit ausgeben
python3 scripts/autopilot.py --selftest     # alle Bausteine prüfen (Exit 2 = fail)
```

### 3.2 Einzelne Bausteine
```bash
# Brand Brain
python3 scripts/brand_brain.py              # validieren + Drift-Check
python3 scripts/brand_brain.py --fix        # Drift aus brand_lock.yaml heilen
python3 scripts/brand_brain.py --context    # Marken-Hirn-Block anzeigen

# Recherche
python3 scripts/research_engine.py --run    # Tagesreport erzeugen
python3 scripts/research_engine.py --status # Report-Übersicht
python3 scripts/research_engine.py --route "Stromanbieter wechseln" --pillar strom-sparen

# Kampagnen + Kalender
python3 scripts/campaign_manager.py --calendar --weeks 4
python3 scripts/campaign_manager.py --status
```

### 3.3 Live-Web-Recherche einschalten (hybrid)
Standard ist der deterministische Modus (keine API, null Halluzinationsrisiko).
Für AGC-ähnliche Trend-Snippets setzt du in **GitHub → Settings → Secrets and
variables → Actions**:

- Secret `SEARCH_API_KEY` (z. B. [Serper.dev](https://serper.dev) oder
  [Brave Search API](https://brave.com/search/api/))
- Variable `SEARCH_API_PROVIDER` = `serper` (Default) oder `brave`

Die Live-Einträge werden im Report klar als **unverifizierte Winkel** markiert und
fließen nie als Fakt in einen Artikel ein (Haftungsschutz).

### 3.4 Kampagne aktivieren
In `data/campaigns.yaml` bei einer Kampagne `status: paused` → `status: active`
setzen. Ab dann gilt automatisch:
- der **Kampagnen-CTA** für Artikel des passenden Pillars (überschreibt `default_cta`),
- die Kampagnen-Themen werden im **Redaktionskalender** bevorzugt.

Neue Kampagnen starten immer als `paused` – es wird nie etwas ungewollt publiziert.

---

## 4. Wo die Intelligenz herkommt (Anti-Halluzination)

| Team | Quelle | Halluzinationsschutz |
|---|---|---|
| Trending | `data/aktuelle_entwicklungen.yaml` (kuratiert) | nur geprüfte Hooks, Gültigkeitsfenster `ab`/`bis` |
| News-Hooks | dito, saisonal gewichtet | keine erfundenen Meldungen – nur „heiße" Saison-Hooks |
| Evergreen | `data/topics.yaml` | Themen aus dem kuratierten Pool |
| Pain Points | `data/research/pain_points.yaml` (kuratiert) | nur allgemeingültige, sichere Beobachtungen |
| Viral Outliers | `data/pinterest_perf.yaml` → Fallback `pinterest_plan.yaml` (Link-Score) | echte in-Repo-Zahlen |
| Nischen-Hooks | `.keyword_suggestions.json` + ungenutzte Themen | Long-Tail aus vorhandenen Daten |
| Live-Web | nur mit `SEARCH_API_KEY` | explizit `unverified`, nur als Winkel |

Der lesbare Tagesreport `AGC-FORSCHUNG-BERICHT.md` dokumentiert Quelle und Modus
jedes Signals – nachvollziehbar und wiederholbar.

---

## 5. Sicherheit & Rückwärtskompatibilität

- **Kein zweiter Veröffentlicher:** Der Autopilot committet nur
  `data/research/` und `data/editorial_calendar.yaml`. Artikel entstehen
  ausschließlich in der Engine v2 mit allen Gates.
- **Fail-closed:** `--selftest` bricht Workflows ab (Exit 2), wenn Brand Brain,
  Research oder Kalender defekt sind – nie still „grün".
- **Nie ein Crash:** `agc_context.py` und `brand_brain.py` werfen nie; fehlt ein
  Baustein, wird der Prompt-Block einfach kleiner und der Bot schreibt wie bisher.
- **Kadenz unangetastet:** Der Kalender plant nur Mo/Mi/Fr (aus
  `cadence_guard.PUBLICATION_DAYS` importiert – keine Duplikation der Vorgabe).

---

## 6. Dateien (neu)

```
data/brand_brain.yaml                 Brand Brain (Single Source of Truth)
data/research/pain_points.yaml        kuratierter Schmerzpunkt-Pool
data/research/latest.yaml             letzter Tagesreport (strukturiert)
data/research/archive/<datum>.yaml    Report-Archiv (30 Tage)
data/campaigns.yaml                   Kampagnen (promo/researched)
data/editorial_calendar.yaml          Redaktionskalender (Mo/Mi/Fr)
scripts/brand_brain.py                Lader + Validator + Drift-Wächter
scripts/research_engine.py            6 Research-Teams + Routing + Live-Web
scripts/campaign_manager.py           Kampagnen + Kalender + CTA-Auflösung
scripts/agc_context.py                Brücke: Kontext in den Schreiber-Prompt
scripts/autopilot.py                  Orchestrator + Cockpit
.github/workflows/agc-autopilot.yml   täglicher Lauf (05:45 MESZ)
AGC-AUTOPILOT.md                      diese Doku
```

Geändert: `scripts/generate_drafts.py` (optionale AGC-Kontext-Injektion, mit
Fallback – verhält sich ohne Autopilot exakt wie vorher).
