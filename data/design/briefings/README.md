# data/design/briefings/ – Design-Signale aus dem Netz

Hier landen die Ergebnisse von `scripts/design_reach_briefing.py`:

| Datei | Inhalt | Erzeuger |
|---|---|---|
| `<datum>-internet-recherche.md` / `.json` | Rohsignale je Kanal | `scripts/agent_reach_research.py` (mit `--plan data/agent_reach/design_themenplan.yaml`) |
| `<datum>-design-hypothesen.md` | Signale → Varianten-Skizzen, je mit den Regeln, an denen sie gemessen würden | `scripts/design_reach_briefing.py` |

Gefüllt wird der Ordner vom Workflow
`.github/workflows/design-varianten.yml` (montags, nach der
Redaktions-Recherche). Lokal:

```bash
python3 scripts/design_reach_briefing.py
```

## Was hier NICHT passiert

Ein Briefing ist ein **Vorschlag**, keine Entscheidung. Agent Reach
läuft ausschließlich lesend; das Skript schreibt weder CSS noch
`data/design/varianten.yaml` noch eine Freigabe. Ob aus einer Skizze
eine Variante wird, entscheidet ein Mensch und trägt sie von Hand ins
Register ein.

Runbook: [`docs/ANLEITUNG-DESIGN-VARIANTEN.md`](../../../docs/ANLEITUNG-DESIGN-VARIANTEN.md)
