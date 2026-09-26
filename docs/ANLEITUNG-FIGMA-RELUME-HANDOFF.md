# Figma/Relume ↔ Hugo – Premium-Handoff

**Stand:** 26.09.2026 · **Status:** Repository-Seite produktionsbereit

Diese Integration verbindet externe Entwurfsarbeit mit dem bestehenden Hugo-
Designsystem, ohne Figma oder Relume zur zweiten, unkontrollierten Wahrheit zu
machen. Sie veröffentlicht nichts automatisch. Figma und Relume bleiben
Entwurfswerkzeuge; Hugo, `DESIGN.md` und `data/design/regelwerk.yaml` bleiben
die Produktionswahrheit.

## Architektur

```text
Agent Reach          Relume                Figma / Tokens Studio
Design-Signale  →    Sitemap/Wireframe →   Tokens + Komponenten
      │                    │                       │
      └──────────── Hypothese, nie Fakten ────────┘
                               ↓
                    Design-Varianten-Werkbank
                    Hugo → Playwright → Lighthouse
                               ↓
                    Messprotokoll + Mensch-Freigabe
```

| Ebene | Datei/Werkzeug | Vertrag |
|---|---|---|
| Design-SSOT | `data/design/handoff.yaml` | Projektbrief, Tokens, Komponenten, Sitemap |
| Marken-Gate | `data/design/regelwerk.yaml` | Erlaubte Farben, Radien, A11y- und Performance-Budgets |
| Generator | `scripts/design_handoff.py` | validiert und erzeugt deterministische Exporte |
| Figma-Import | `design/handoff/figma-tokens.tokens.json` | Tokens-Studio-kompatible Light-/Dark-Collections |
| Relume-Input | `design/handoff/relume-project-brief.md` | kopierfertiger Prompt, Sitemap und Section-Vertrag |
| Dev-Handoff | `design/handoff/component-inventory.md` | Figma-Name ↔ CSS-Vertrag ↔ Zustände ↔ A11y |
| Nachweis | `design/handoff/handoff-manifest.json` | SHA-256 für Quellen und Exporte |
| Abnahme | Playwright + Lighthouse | Browserregression, A11y, SEO, CWV und Budgets |

## Einmalige Einrichtung in Figma

1. Eine Datei **„FranksFinanzcheck – Design System“** anlegen.
2. Seiten in der Reihenfolge aus `data/design/handoff.yaml → figma.page_order`
   anlegen.
3. Tokens Studio installieren und
   `design/handoff/figma-tokens.tokens.json` als lokale JSON-Quelle importieren.
4. Themes **Light** und **Dark** den gleichnamigen Token-Sets zuordnen.
5. Komponenten exakt nach `component-inventory.md` benennen. Interaktive
   Komponenten benötigen die dort genannten Fokus-, Fehler-, Disabled- und
   Dark-Mode-Zustände.
6. Frames mindestens bei 390, 768 und 1280 px prüfen. Inhalte nicht durch
   Platzhalter-Fakten oder erfundene Sparbeträge ersetzen.

Figma-Zugangsdaten oder Personal Access Tokens gehören **nie** in dieses Repo.
Der Import ist absichtlich manuell: Eine SaaS-Datei darf nicht ungeprüft das
Produktionsdesign überschreiben.

## Einmalige Einrichtung in Relume

1. Neues Projekt in deutscher Sprache anlegen.
2. Den Block **Projekt-Prompt** aus `relume-project-brief.md` einfügen.
3. Sitemap und Section-Reihenfolge gegen den dortigen Vertrag prüfen.
4. Relume nur Struktur und Wireframes vorschlagen lassen. Bestehende deutsche
   Inhalte bleiben verbindlich; Testimonials, Bewertungen, Preise und Siegel
   dürfen nicht generiert werden.
5. Den akzeptierten Entwurf nach Figma exportieren und dort auf die importierten
   Marken-Tokens zurückführen.

## Laufender Workflow

```bash
# Voraussetzung für den Python-Generator
python3 -m venv .venv
.venv/bin/pip install pyyaml

# Nach Änderungen an Brief, Tokens oder Komponenten
.venv/bin/python scripts/design_handoff.py
.venv/bin/python scripts/design_handoff.py --check

# Varianten- und Qualitätskette
npm ci
npm run design:lauf v-meine-variante
npm run design:messen v-meine-variante
npm run design:quality
npm run test:e2e
```

`design:handoff:check` läuft zusätzlich im Workflow **Design-Varianten**. Jede
manuelle Änderung an einem generierten Export erzeugt Drift und stoppt das Gate.
Lighthouse ist direkt und versionsfest als Dev-Dependency installiert; die
Messung läuft über `e2e/variant-metrics.mjs` mobil als maßgebliches Profil und
desktop als Vergleich. Playwright bleibt für Desktop- und Mobile-Regressionen
zuständig.

## Definition of Done für einen Design-Entwurf

- Hypothese und Abbruchkriterium im Varianten-Register dokumentiert.
- Nur Marken-Tokens verwendet; Light und Dark vollständig.
- Mobile 390 px sowie Desktop geprüft; keine horizontalen Überläufe.
- Fokuszustände, Labels, Fehlerzustände und reduzierte Bewegung vorhanden.
- Playwright grün; Lighthouse-Budgets erfüllt; SEO-/Affiliate-Verträge intakt.
- Messung unter `data/design/messungen/` eingefroren.
- Frank Hartung hat im Register ausdrücklich freigegeben.
- Aktivierung und Rückrollweg sind dokumentiert.

## Klare Grenze

Die technische Integration kann im Repository vollständig eingerichtet werden.
Die tatsächliche Anlage eines Figma-/Relume-Projekts und ein möglicher
kostenpflichtiger Account müssen außerhalb des Repositories durch den
Kontoinhaber erfolgen. Ohne diese manuelle SaaS-Aktion sind trotzdem alle
Importdateien, Prompts, Gates und Abnahmetests einsatzbereit.
