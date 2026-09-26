# Premium-Audit: Figma/Relume + KI-Coding-Agent + Lighthouse/Playwright

**Datum:** 26.09.2026

## Kurzurteil vor der Optimierung

| Baustein | Bestand | Befund |
|---|---|---|
| Agent Reach | vorhanden | Gepinnte Recherche-Schicht, Design-Themenplan und wöchentliches Briefing bereits professionell eingerichtet |
| KI-Coding-Agent | vorhanden | Agentenleitfaden, sechs gepinnte Skills, Design-SSOT, Varianten-Governance und menschliche Freigabe vorhanden |
| Playwright | vorhanden | Desktop/Mobile, SEO, A11y, Affiliate-Integrität, Screenshots/Traces und CI vorhanden |
| Lighthouse | weitgehend vorhanden | Mobile/desktop Messung und regelwerksbasierte Budgets vorhanden; das Lighthouse-Paket war jedoch nicht im Projekt fest gepinnt |
| Figma/Relume | nur indirekt | Herkunftsfeld und Relume-Muster waren dokumentiert, aber es fehlten reproduzierbare Tokens, Sitemap-Brief, Komponenten-Mapping und Drift-Gate |

**Antwort:** Der Blog hatte bereits eine ungewöhnlich starke Agent-/Playwright-/
Lighthouse-Basis. Er hatte aber noch keine belastbare Figma-/Relume-
Übergabeschicht. Genau diese Lücke wurde geschlossen.

## Umgesetzte Premium-Erweiterung

1. `data/design/handoff.yaml` ist die maschinenlesbare Quelle für Projektbrief,
   Figma-Tokens, Breakpoints, Typografie, Komponenten und Relume-Sitemap.
2. `scripts/design_handoff.py` validiert Farben und Radien gegen das bestehende
   Marken-Regelwerk, fordert Light/Dark- und Fokuszustände und erzeugt die
   Übergabe deterministisch.
3. `design/handoff/figma-tokens.tokens.json` liefert Light-/Dark-Collections
   für Tokens Studio.
4. `design/handoff/relume-project-brief.md` liefert einen deutschsprachigen,
   markensicheren Prompt sowie einen Section-Vertrag für Startseite,
   Ratgeber-Zentrale und Artikel.
5. `design/handoff/component-inventory.md` verbindet Figma-Komponenten mit den
   realen Hugo/CSS-Verträgen und A11y-Zuständen.
6. `design/handoff/handoff-manifest.json` macht Quellen- und Exportdrift über
   SHA-256 nachvollziehbar.
7. Der Workflow `Design-Varianten` führt Selbsttest und Drift-Check bei jedem
   relevanten PR aus.
8. Lighthouse `13.5.0` ist als exakte Dev-Dependency festgeschrieben;
   `npm audit` meldet 0 bekannte Schwachstellen. Die CI braucht keine
   ungepinnte Ad-hoc-Installation mehr.
9. Neue Befehle: `design:handoff`, `design:handoff:check` und
   `design:quality`.

## Qualitätsmodell

Externe Tools dürfen Vorschläge liefern, aber nicht direkt deployen:

`Agent Reach → Relume → Figma → Variante → Playwright/Lighthouse → Messprotokoll → menschliche Freigabe → Hugo`

Damit sind Designfreiheit, Messbarkeit und Produktionssicherheit getrennt.
Figma/Relume werden nicht zur Schatten-Produktionsumgebung; das vorhandene
Hugo-Designsystem bleibt die verbindliche Quelle.

## Noch manuell außerhalb des Repositories

Ein Figma-/Relume-Projekt kann ohne Zugriff auf die jeweiligen Konten nicht
angelegt werden. Die dafür erforderlichen Importdateien und der genaue Ablauf
liegen in `docs/ANLEITUNG-FIGMA-RELUME-HANDOFF.md`. Es werden bewusst keine
SaaS-Tokens im Repository hinterlegt.
