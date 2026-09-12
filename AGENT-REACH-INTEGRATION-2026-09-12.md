# AGENT-REACH-INTEGRATION – Rollout-Report (12.09.2026)

> Premium-Integration von [Agent Reach](https://github.com/Panniantong/Agent-Reach)
> in den Redaktionsbetrieb von franksfinanzcheck.de.
> Betriebsanleitung: `ANLEITUNG-AGENT-REACH.md`

## Auftrag

Der Blog sollte eine professionelle, kostenfreie **Internet-Recherche-Fähigkeit**
erhalten: Agenten und CI sollen Signale (Nachrichten, YouTube-Diskussionen,
GitHub-Projekte, Referenzseiten) sammeln können – ohne API-Gebühren, ohne
Secrets in CI, ohne Schreiboperationen, und ohne das Anti-Halluzinations-
Statut der KI-Redaktion zu verletzen.

## Warum Agent Reach

| Kriterium | Befund |
|---|---|
| Lizenz | MIT ✅ |
| Reife | v1.5.0, ~80k Stars, 375+ Commits, aktive Pflege (Stand 12.09.2026) |
| Kosten | 0 € für die hier genutzten Kanäle (RSS, Web/Jina, YouTube, GitHub) |
| Architektur | Kein Monolith: Selektor/Installer/Doctor/Router über bewährte Einzel-Tools (yt-dlp, gh, feedparser) |
| Agent-Anschluss | Offizieller Skill (SKILL.md + 7 Themen-Referenzen), via `npx skills` versioniert |

**Sicherheitsbefund vor Installation (Due Diligence):** Auf PyPI existiert
ein andersartiges, namensgleiches Paket `agent-reach` 0.1.0 (jgalea). Die
Installation wurde deshalb ausschließlich aus dem offiziellen GitHub-Repository
vorgenommen, gepinnt auf den Commit des Tags v1.5.0
(`f65526cbaaad3879473acc1ba6dbefd195caf2be`).

## Gelieferte Bausteine

1. **Skill** `.claude/skills/agent-reach/` – offiziell via `npx skills add`
   installiert (nachvollziehbar in `skills-lock.json`, inkl. Prüf-Hash).
2. **Pinning** `requirements-agent-reach.txt` – Paket + yt-dlp + feedparser.
3. **Gate** `scripts/agent_reach_gate.py` – Installation, Version, Kanalmatrix,
   Mindestkanäle; Exit-Codes für CI-Anschluss.
4. **Recherche-Läufer** `scripts/agent_reach_research.py` – liest den
   kuratierten Themenplan, sammelt lesend RSS/YouTube/GitHub/Web, schreibt
   einen deutschen Recherche-Brief inkl. Kanalmatrix und Fehlerbilanz.
5. **Kuratierte Quellen** `data/agent_reach/themenplan.yaml` – am 12.09.2026
   live verifizierte Feeds (Tagesschau-Atom, Spiegel Wirtschaft, heise online)
   plus YouTube-/GitHub-Suchen mit Leser-Relevanz.
6. **Workflow** `.github/workflows/agent-reach-research.yml` – montags
   08:15 MESZ (entzerrter Slot) + manuell; commitet Briefs, meldet
   Totalausfälle als Issue.
7. **Dokumentation** – diese Datei + `ANLEITUNG-AGENT-REACH.md` +
   Ergänzungen in `CLAUDE.md` und `KI-REDAKTION.md`.

## Verifikations-Ergebnisse (12.09.2026, Arbeitsumgebung)

**Gate:** `EINSATZBEREIT` (Exit 0), Version 1.5.0, Kanalmatrix:

```
github   ok (gh CLI)        rss   ok (feedparser)
youtube  warn (yt-dlp)*     web   ok (Jina Reader)
v2ex/twitter warn            reddit/bilibili/xhs u. a. off (bewusst nicht installiert)
```
\* „warn" = Backend vorhanden, aber keine Live-Probe (by design, schützt vor
unbeabsichtigten Zugriffen).

**Quell-Verifikation:** Die drei RSS-Feeds des Themenplans wurden am
Integrationstag live geprüft und lieferten frische, blogrelevante Meldungen
(u. a. Gasspeicher-Füllstände, Gaspreis-Prognosen, Pflege- und Rentenreformen).

**Erster Lauf:** `scripts/agent_reach_research.py` erzeugte
`data/research/2026-09-12-internet-recherche.md`. In der Sandbox-Arbeitsumgebung
sind ausgehende Verbindungen zu Fremddomänen eingeschränkt; der Brief
dokumentiert daher ehrlich: GitHub-Suche ✅ (Treffer geliefert), RSS/YouTube/Web
als „nicht erreichbar aus dieser Umgebung" ausgewiesen. In GitHub Actions
(normales Netz) liefern diese Kanäle – der Workflow committet den vollen Brief.

**Tests:** `--selftest` des Recherche-Läufers grün (Slug-Erzeugung,
Brief-Rendering, Bilanz-Logik). Gate-Exit-Code-Pfad verifiziert.

## Betriebliche Leitplanken

- **Nur lesen, nie posten** (Skill-Deklaration + betriebliche Regel).
- **Keine Cookies/Logins in CI** – Login-Kanäle nur lokal bei Frank.
- **Kuratierung bleibt menschlich:** Der Brief ist ein Signal-Pool; Fakten
  gehen erst nach Prüfung in `data/aktuelle_entwicklungen.yaml` / `data/topics.yaml`.
- **Versionierung:** Paket commit-gepinnt, Skill mit Prüf-Hash im Lockfile;
  Updates laufen über bewusste Pin-Anhebung + Gate, nicht stillschweigend.

## Nächste Schritte (optional, Entscheidung bei Frank)

1. **Erster CI-Lauf beobachten** (Workflow nach Merge einmal manuell via
   `workflow_dispatch` starten, Artefakt-Brief prüfen).
2. **Themenplan schärfen:** 1–2 Feeds je Themenwelt ergänzen
   (z. B. Versicherung, Konto), nachdem die Montagläufe Routine sind.
3. **Lokaloptionen bei Bedarf:** Twitter-/Reddit-Kanäle auf Franks Rechner
   via `agent-reach setup` aktivieren (dediziertes Zweitkonto empfohlen,
   siehe Agent-Reach-Sicherheitshinweise) – niemals in CI.

## Geänderte/neue Dateien (Übersicht)

```
NEU  .claude/skills/agent-reach/          (Skill + 7 Referenzen)
NEU  .github/workflows/agent-reach-research.yml
NEU  ANLEITUNG-AGENT-REACH.md
NEU  AGENT-REACH-INTEGRATION-2026-09-12.md
NEU  requirements-agent-reach.txt
NEU  scripts/agent_reach_gate.py
NEU  scripts/agent_reach_research.py
NEU  data/agent_reach/themenplan.yaml
NEU  data/research/README.md
NEU  data/research/2026-09-12-internet-recherche.{md,json}   (erster Lauf)
MOD  skills-lock.json      (Skill-Eintrag mit Prüf-Hash)
MOD  CLAUDE.md             (Skill-Tabelle + Recherche-Regeln)
MOD  KI-REDAKTION.md       (Modul Internet-Recherche)
```
