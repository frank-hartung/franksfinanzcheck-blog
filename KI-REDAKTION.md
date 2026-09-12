# 🤖 KI-Redaktion – Blog-Automatik nach dem Schema Claude / ChatGPT / Jasper

> **Auftrag (Frank, 08.09.2026):** Eine Blog-Automatik nach dem Schema
> „Claude für lange Artikel + ChatGPT Plus für schnelle News + Jasper für
> SEO" – mit möglichst gleichem Funktionsumfang und **ohne jegliche Kosten**.

---

## 1. Die ehrliche Ausgangslage (wichtig!)

Bevor die Lösung kommt, die Fakten, die jede seriöse Agentur dir sagen würde:

| Dienst | Abo (das du kennst) | API für Automatik |
|---|---|---|
| **Claude** (Anthropic) | Web-/App-Chat | eigene, **kostenpflichtige** API – kein Bestandteil des Abos |
| **ChatGPT Plus** | Web-/App-Chat für 20 €/Monat | **kein API-Zugang enthalten** – die OpenAI-API wird getrennt nach Verbrauch abgerechnet |
| **Jasper** | Web-App (ab ~39 €/Monat) | **keine öffentliche API** (nur Enterprise-Absprachen) |

Das heißt konkret:

1. Ein Abo von Claude/ChatGPT Plus/Jasper lässt sich **nicht** direkt und
   kostenlos automatisieren. Die Chat-Oberflächen per Skript „fern­zusteuern"
   (Scraping) verstößt gegen die Nutzungsbedingungen aller drei Anbieter,
   ist unzuverlässig und ein Kontosperr-Risiko – das bauen wir nicht.
2. Die echten APIs von Anthropic/OpenAI wären **zusätzliche, laufende
   Kosten** (ca. 0,10–0,50 € pro Langartikel je nach Modell) und sind
   deshalb in dieser Lösung **abgeschaltet**.
3. Jasper bietet technisch gar keine API.

**Die Lösung:** Deine KI-Redaktion bildet den **Funktionsumfang der drei
Rollen 1:1 ab** – aber ausschließlich mit den **Gratis-Zugängen, die in
deinem Repo bereits etabliert sind** (Groq: GPT-OSS 120B, Gemini: Gratis-Tier;
genau die Keys, die auch die Content-Engine v2 nutzt). **Kosten: 0 €.**

---

## 2. Feature-Parität: Das Schema → dein Blog

| Schema-Rolle | Original-Funktionsumfang | Umsetzung hier (0 €) | Datei |
|---|---|---|---|
| **Claude** – lange Artikel | Tiefe Long-Form-Texte mit klarer Struktur, Tabellen, Rechenbeispielen, FAQ; Markenstimme | Rolle „Claude": Premium-Ratgeber, 11.000–18.000 Zeichen, AGC-Markenkontext, kuratierte Themen | `scripts/claude_writer.py` |
| **ChatGPT Plus** – schnelle News | Schnelle, aktuelle Kurz-Artikel aus Anlässen | Rolle „ChatGPT": News-Kompakt-Artikel aus dem **kuratierten** Aufhänger-Pool (anti-halluziniert), erfüllt den 10.000-Zeichen-Floor | `scripts/news_writer.py` |
| **Jasper** – SEO | SEO-Mode, Meta-Titel/-Descriptions, Content Improvements, Score | Rolle „Jasper": deterministische SEO-Werkbank – Score 0–100, Keyword-Dichte/-Platzierung, SERP-Längen, Struktur-Checks, sichere Metadaten-Fixes, optionale Gratis-KI-Varianten als Vorschläge | `scripts/jasper_seo.py` |
| _(Alle drei)_ | Redaktionsplan, Freigabe-Workflow | Orchestrator + bewusste Freigabe (`--promote`), Veröffentlichung **nur** über den bestehenden `cadence_guard` | `scripts/ki_redaktion.py` |

**Gemeinsame Leitplanke (wie im restlichen Repo):** Die KI erfindet niemals
Fakten. Themen kommen aus `data/topics.yaml`, News-Anlässe aus
`data/aktuelle_entwicklungen.yaml` – beides von Menschen kuratiert.
Alles Weitere sind als Faustregeln gekennzeichnete, zeitlose Aussagen.

---

## 3. Die Pipeline

```
  ┌────────────────────────────────────────────────────────────┐
  │  KI-REDAKTION (Mo/Mi/Fr bzw. Di/Do, 06:30 MESZ)             │
  │    Rolle Claude  → langer Premium-Artikel   (Groq → Gemini) │
  │    Rolle ChatGPT → News-Kompakt-Artikel     (Groq → Gemini) │
  │    Rolle Jasper  → SEO-Pass + sichere Metadaten-Fixes        │
  │  ERGEBNIS: Entwürfe (draft: true, OHNE cadence_wait)         │
  └──────────────────────────────┬─────────────────────────────┘
                                 ▼
  ┌────────────────────────────────────────────────────────────┐
  │  FREIGABE DURCH FRANK (ein Befehl, bewusst)                  │
  │    python3 scripts/ki_redaktion.py --promote <slug>          │
  └──────────────────────────────┬─────────────────────────────┘
                                 ▼
  ┌────────────────────────────────────────────────────────────┐
  │  BESTEHENDE AUTOMATIK (unverändert!)                         │
  │    cadence_guard: Re-Queue → nächster Slot Mo/Mi/Fr          │
  │    (2–3 Artikel/Tag, alle Gates der Content-Engine v2)       │
  └────────────────────────────────────────────────────────────┘
```

Es gibt **keinen zweiten Veröffentlicher**: Die KI-Redaktion liefert zu,
veröffentlicht wird ausschließlich über die bewährten Gates.

---

## 4. Bedienung

```bash
# Kompletter Selbsttest (Exit 2 = Defekt; prüft auch die Kosten-Regel)
python3 scripts/ki_redaktion.py --selftest

# Produktion starten (alle Rollen)
python3 scripts/ki_redaktion.py --run
python3 scripts/ki_redaktion.py --run --rolle lang     # nur Claude-Rolle
python3 scripts/ki_redaktion.py --run --rolle news     # nur ChatGPT-Rolle
python3 scripts/ki_redaktion.py --run --rolle seo --fix

# Einzelaufrufe der Rollen
python3 scripts/claude_writer.py                        # nächstes freies Thema
python3 scripts/claude_writer.py --topic "Titel" --pillar strom-sparen
python3 scripts/news_writer.py --kategorie energie
python3 scripts/jasper_seo.py --new-only                # SEO-Befund + Report
python3 scripts/jasper_seo.py --new-only --fix          # + Metadaten-Fixes
python3 scripts/jasper_seo.py --new-only --ai           # + Gratis-KI-Varianten

# Ohne KI-Zugang testen (Pipeline-Check, erzeugt Struktur-Gerüste)
python3 scripts/ki_redaktion.py --run --offline

# Übersicht aller KI-Entwürfe
python3 scripts/ki_redaktion.py --status

# Bewusste Freigabe → Re-Queue → Publikation über cadence_guard
python3 scripts/ki_redaktion.py --promote <slug>
```

Berichte: `KI-REDAKTION-REPORT.md` (Status) und `KI-SEO-REPORT.md`
(SEO-Befund je Artikel mit Score).

---

## 5. Einrichtung (einmalig, 2 Minuten)

**Es sind KEINE neuen Secrets nötig.** Der Workflow `.github/workflows/
ki-redaktion.yml` verwendet die vorhandenen `GROQ_API_KEY` und
`GEMINI_API_KEY` (Settings → Secrets and variables → Actions). Fehlt
beides, erzeugt die Automatik trotzdem lauffähige Struktur-Gerüste
(Offline-Modus) – nie einen Fehlerlauf.

Termine (UTC-Cron im Workflow):

| Slot | Rollen |
|---|---|
| Mo/Mi/Fr 06:30 MESZ | Claude-Rolle (Langartikel) + Jasper-Rolle (SEO, mit Fix) |
| Di/Do/So 06:30 MESZ | ChatGPT-Rolle (News) + Jasper-Rolle (SEO) |

Zusätzlich jederzeit manuell über **Actions → KI-Redaktion → Run workflow**
(Rolle wählbar).

---

## 6. Kosten-Regel (dauerhaft abgesichert)

- In `data/ki_redaktion.yaml` stehen die Anbieter-Ketten. **Erlaubt sind
  nur `groq` und `gemini`.** Der Selbsttest bricht mit Exit 2 ab, sobald
  dort ein Paid-Provider alleinige Option wäre.
- Die echten Claude-/ChatGPT-APIs (`claude`/`openai`) sind im Code zwar
  vorhanden, werden aber **niemals automatisch** angerufen: nur mit
  ausdrücklich gesetztem `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` **und**
  manuellem `--provider claude|openai`. Damit bleibt die Option für
  später offen, ohne dass je unbeabsichtigt Kosten entstehen.
- `auto_veroeffentlichen` ist fest `false`; ein `true` wird aktiv
  ignoriert und im Report angemerkt.

---

## 7. Sicherheits- und Qualitäts-Garantien

1. **Nie ein zweiter Veröffentlicher** – Entwürfe ohne `cadence_wait`
   sind für alle Promote-Automatiken unsichtbar (cadence_guard fasst
   sie nie an).
2. **Anti-Halluzination** – keine erfundenen Zahlen/Daten/Zitate;
   Faktenanker ausschließlich aus kuratierten Repo-Dateien.
3. **Floor-konform** – auch News erfüllen die 10.000-Zeichen-Vorgabe
   (`length_policy`); `--promote` verweigert zu kurze Texte.
4. **Compliance** – Werbekennzeichnung und Finanz-Disclaimer sind in
   jeder Rolle fest eingebaut.
5. **Fail-closed** – `--selftest` (Exit 2) läuft im Workflow vor jeder
   Produktion; defekte Bausteine stoppen den Lauf, statt still „grün"
   zu melden.

---

## 8. Dateien (neu)

```
scripts/llm_client.py                Multi-Provider-Client (Gratis-Kette zuerst)
scripts/ki_shared.py                 gemeinsame Helfer (Themen, Frontmatter, Report)
scripts/claude_writer.py             Rolle Claude: lange Premium-Artikel
scripts/news_writer.py               Rolle ChatGPT: schnelle News-Kompakt
scripts/jasper_seo.py                Rolle Jasper: SEO-Analyse, -Fixes, Score
scripts/ki_redaktion.py              Orchestrator, Status, Freigabe, Selbsttest
data/ki_redaktion.yaml               Konfiguration (Anbieter-Ketten, Korridore)
.github/workflows/ki-redaktion.yml   Zeitplan (Mo/Mi/Fr lang, Di/Do/So News)
KI-REDAKTION.md                      diese Doku
```

Kompatibilität: Die Content-Engine v2, der AGC-Autopilot und alle Guards
bleiben unverändert. Die KI-Redaktion nutzt die AGC-Recherche
(Brand Brain + Tagesreport) über `agc_context.py` automatisch mit.

---

## 9. Internet-Recherche (Agent Reach, seit 12.09.2026)

Damit **News-Anlässe** und **Faktenanker** nicht allein aus den kuratierten
Stamm-Dateien kommen, gibt es eine ergänzende, rein **lesende** Recherche-
Schicht über das Open-Source-Tool
[Agent Reach](https://github.com/Panniantong/Agent-Reach) (kostenlos,
ohne API-Keys).

```
  KURATIERTE QUELLEN (Themenplan)        agent-reach (lesend)
  ┌────────────────────────────┐   ┌─────────────────────────────┐
  │ data/agent_reach/          │ → │ Mo 08:15 MESZ (CI) / manuell │
  │ themenplan.yaml            │   │ scripts/agent_reach_research │
  │ (RSS-Feeds, YouTube-,      │   │ → RSS / YouTube / GitHub / Web│
  │  GitHub-, Web-Quellen)     │   │ → data/research/<datum>-*.md  │
  └────────────────────────────┘   └─────────────────────────────┘
                       │
                       ▼  (bewusste, menschliche Übernahme einzelner Signale)
  data/aktuelle_entwicklungen.yaml  /  data/topics.yaml
```

**So bleibt es statuskonform:**

1. Der Recherche-Brief ist eine **Signalsammlung**, kein fertiger Text.
   Die KI-Redaktion zitiert/paraphrasiert weiterhin **nur** aus den
   kuratierten Pools (`aktuelle_entwicklungen.yaml`, `topics.yaml`) –
   niemals direkt aus einem Brief.
2. Ein Signal wird erst dann zum Faktenanker, wenn Frank (oder ein Agent
   mit Quellenprüfung) es **bewusst** in eine kuratierte Datei übernimmt
   (inkl. `id`/`kategorie`/`ab`/`bis`, siehe Kommentarblock der YAML).
3. Agent Reach läuft hier **rein lesend**: kein Posten, kein Kommentieren,
   keine Cookies/Logins in CI (Login-Kanäle nur lokal, siehe
   `ANLEITUNG-AGENT-REACH.md`). Das schützt die Garantie aus Abschnitt 7.

**Bedienung:**

```bash
# Gesundheit der Recherche-Schicht prüfen (Exit 0 = einsatzbereit)
python3 scripts/agent_reach_gate.py

# Recherche-Brief manuell erzeugen → data/research/
python3 scripts/agent_reach_research.py
```

Einzelheiten, Kanalmatrix und Troubleshooting: `ANLEITUNG-AGENT-REACH.md`.
Rollout-Nachweis: `AGENT-REACH-INTEGRATION-2026-09-12.md`.
