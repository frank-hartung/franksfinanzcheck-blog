# ANLEITUNG: Agent Reach – Internet-Recherche für den Blog

> Premium-Integration vom 12.09.2026 · Rollout-Report: `AGENT-REACH-INTEGRATION-2026-09-12.md`
> Upstream: [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach) (MIT, ~80k Stars)

**Agent Reach** gibt KI-Agenten „Augen für das ganze Internet": lesen &
suchen auf 15 Plattformen über **ein** CLI, ohne API-Gebühren. Es ist kein
Scraper-Monolith, sondern ein **Selektor/Installer/Doctor/Router**: Es wählt
für jede Plattform das beste freie Backend-Tool aus (yt-dlp, gh, feedparser,
Jina Reader, …), installiert es auf Wunsch, prüft die Gesundheit
(`agent-reach doctor`) und routet die Skill-Kommandos dorthin.

In diesem Repository ist Agent Reach die **Recherche-Schicht der
KI-Redaktion**: kuratierte Themenpläne → automatische Signalsammlung →
menschliche Prüfung → erst dann Übernahme in Artikel/Willkommenstext.
Kosten: 0 € (nur Zero-Config-Kanäle).

---

## 1. Was installiert ist (Inventar)

| Bestandteil | Ort | Zweck |
|---|---|---|
| Skill (verdrahtet über `skills-lock.json`) | `.claude/skills/agent-reach/` | Routing-Wissen für alle Agenten (Claude Code u. a.): welche Plattform über welches Backend |
| Python-Paket v1.5.0 (Tag-Pin) | via `requirements-agent-reach.txt` | CLI `agent-reach` (doctor/setup/skill/…) |
| Gate | `scripts/agent_reach_gate.py` | Beantwortet: „Kann das Repo gerade im Internet lesen?" |
| Recherche-Läufer | `scripts/agent_reach_research.py` | Erzeugt den wöchentlichen Recherche-Brief |
| Kuratierter Themenplan | `data/agent_reach/themenplan.yaml` | RSS-Feeds, YouTube-/GitHub-Suchen, Referenzseiten |
| Ergebnisablage | `data/research/` | Briefs (`JJJJ-MM-TT-internet-recherche.md` + JSON) |
| Workflow | `.github/workflows/agent-reach-research.yml` | Montags 08:15 MESZ + manuell (`workflow_dispatch`) |

## 2. Lokal installieren (Einmalig, ~2 Minuten)

```bash
python3 -m venv .venv && source .venv/bin/activate   # .venv/ ist git-ignoriert
pip install -r requirements-agent-reach.txt          # gepinnt auf Tag v1.5.0
python3 scripts/agent_reach_gate.py                  # → „EINSATZBEREIT"
```

> ⚠️ **Supply-Chain-Hinweis:** Auf PyPI existiert ein *anderes*, namensgleiches
> Paket `agent-reach` (Autor jgalea, v0.1.0). **Niemals** `pip install agent-reach`
> ohne Quelle ausführen – die Installation erfolgt ausschließlich über die
> GitHub-URL in `requirements-agent-reach.txt` (Commit-gepinnt, prüfbar).

Skill-Aktualisierung (Agent-Routing-Wissen): `npx skills update` – Quellen
stehen in `skills-lock.json`. Paket-Aktualisierung: neuen Tag-Commit in
`requirements-agent-reach.txt` eintragen, Gate laufen lassen, Bericht ergänzen.

## 3. Bedienung

```bash
# Gesundheitsprüfung (Exit 0 = einsatzbereit)
python3 scripts/agent_reach_gate.py            # --json für Maschinen

# Recherche-Brief manuell erzeugen
python3 scripts/agent_reach_research.py        # schreibt data/research/<heute>-internet-recherche.md
python3 scripts/agent_reach_research.py --dry-run
python3 scripts/agent_reach_research.py --selftest   # offline

# Agent-Reach-Originalkommandos (Aktivierung: source .venv/bin/activate)
agent-reach doctor                 # Kanalmatrix (Menschen-Version)
agent-reach doctor --json          # Kanalmatrix (Maschinen-Version)
agent-reach check-update           # neue Upstream-Version?
```

## 4. Kanalmatrix – was wo läuft

| Kanal | Backend | CI (GitHub Actions) | Franks Rechner (optional) |
|---|---|---|---|
| RSS | feedparser | ✅ (Feeds im Themenplan) | ✅ |
| Web | Jina Reader (`r.jina.ai`, kostenlos, ratenbegrenzt) | ✅ | ✅ |
| YouTube | yt-dlp | ✅ (Suche + Untertitel) | ✅ |
| GitHub | gh CLI | ✅ (Runner-Token reicht) | ✅ (`gh auth login`) |
| V2EX | HTTP-API | ⚠️ nur bei Bedarf | ⚠️ |
| Twitter/X, Reddit, XiaoHongShu, Bilibili, Facebook, Instagram, Xueqiu, LinkedIn | div. (Cookies/CLI) | ❌ **bewusst nie** | auf Wunsch lokal |

**Regel:** Login-/Cookie-Kanäle gehören **ausschließlich auf den lokalen
Rechner** und werden dort über `agent-reach setup` bzw. `agent-reach
configure` aktiviert. In CI laufen nur Zero-Config-Kanäle – sonst lägen
bald Session-Cookies in Secrets, und das wollen wir nicht.

## 5. Redaktions-Integration (der eigentliche Nutzen)

```
Themenplan (kuratiert)          Agent Reach (lesend)              Redaktion
──────────────────────   ──────────────────────────────   ─────────────────────
data/agent_reach/        scripts/agent_reach_research.py    Kurz prüfen, dann:
themenplan.yaml    ───►  Mo 08:15 MESZ (CI) + manuell ───►  data/aktuelle_entwicklungen.yaml
(RSS/YT/GH/Web)          data/research/<datum>-*.md          data/topics.yaml → Artikel
```

1. Der Brief ist eine **Signalsammlung**, kein fertiger Inhalt.
2. Signale mit Relevanz (z. B. „Gaspreise +20 % erwartet") werden **von
   einem Menschen (oder einem Agenten mit Quellenprüfung)** in
   `data/aktuelle_entwicklungen.yaml` bzw. `data/topics.yaml` übernommen –
   exakt nach dem dort dokumentierten Kuratierungs-Prinzip.
3. Die KI-Redaktion (`scripts/ki_redaktion.py`) zitiert anschließend nur
   aus diesen kuratierten Pools – niemals direkt aus dem Brief.

Für Agenten gilt zusätzlich (steht in `CLAUDE.md`): Ad-hoc-Recherchen zu
einzelnen Themen/URLs laufen über den Skill `.claude/skills/agent-reach/`
(Routing-Tabelle + `references/` beachten, vorher `agent-reach doctor`).

## 6. Sicherheit & Compliance

- **Nur lesen.** Agent Reach wird hier nie für Schreiboperationen
  (Posten/Kommentieren/Liken) verwendet – der Skill deklariert das selbst
  als Ausschluss, wir setzen es betrieblich durch.
- **Keine Secrets im Repo/CI.** Zero-Config-Kanäle brauchen keine Keys;
  Cookies/Logins bleiben lokal bei Frank (`~/.agent-reach/`, nie im Git).
- **DSGVO:** Briefs enthalten nur öffentlich zugängliche Meldungstitel/-
  auszügen mit Quelllink; es werden keine personenbezogenen Profile
  gespeichert. Kommentare/Klarnamen werden nicht gesammelt.
- **ToS:** Die Backends (RSS, YouTube-Untertitel via yt-dlp, GitHub-API,
  Jina Reader) bewegen sich im Rahmen der jeweiligen Nutzungsbedingungen;
  Abrufmengen sind bewusst klein (Brief 1×/Woche, je Quelle ≤ 5 Treffer).
- **Recht am Inhalt:** Briefs sind intern. Titel/Teaser dürfen nicht 1:1
  als Artikeltext übernommen werden (Urheberrecht) – sie sind Anlässe,
  keine Texte.

## 7. Troubleshooting

| Symptom | Ursache & Lösung |
|---|---|
| Gate: „agent-reach-Binary nicht gefunden" | `pip install -r requirements-agent-reach.txt` (ggf. venv aktivieren) |
| Gate: „Versionsdrift" | Jemand hat eine andere Version installiert – gepinnte Version wiederherstellen oder Pin bewusst anheben |
| RSS „bozo, keine Einträge" | Feed-URL tot oder Netzblockade – URL im Browser testen, Themenplan anpassen |
| YouTube: Bot-Prüfung/leere Antwort | Retry-Kette im Skill (`references/video.md`): yt-dlp → OpenCLI → `agent-reach transcribe` |
| Jina Reader 401/429 | Ratenlimit des Gratis-Tiers – `web:`-Einträge im Themenplan reduzieren |
| „doctor zeigt alles off" in CI | Runner-Netzproblem; Logs prüfen. Im Zweifel Issue-Text des Workflows beachten |
| Neues Agent-Reach-Release | `agent-reach check-update`; Pin in `requirements-agent-reach.txt` anheben, Gate + Selftest laufen lassen |

## 8. Bewusst NICHT getan (und warum)

- **Kein MCP-Server** (`agent_reach/integrations/mcp_server.py`) – dieser
  Betrieb läuft über Skills + CLI; MCP würde eine weitere dauerhafte
  Prozess-Abhängigkeit bringen. Bei Bedarf nachrüstbar.
- **Keine Cookie-Kanäle in CI** – siehe Kapitel 4.
- **Kein automatisches Veröffentlichen** von Recherche-Ergebnissen –
  verstößt gegen das Anti-Halluzinations-Statut der KI-Redaktion.
