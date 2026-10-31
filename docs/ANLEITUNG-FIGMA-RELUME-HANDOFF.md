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
| Muster | `design/handoff/patterns.md` | Seitenrhythmus, Typo-Einsatz, Tiefe, Verbote |
| A11y-Notizen | `design/handoff/ANNOTATIONEN.md` | gerechnete Kontrast-Matrix, Pflichtzustände |
| Aufbau | `figma/design-system-builder/` | Figma-Plugin: Variablen, Stile, Komponenten-Sets, Cover |
| Qualität | `scripts/figma_quality_gate.py` | 33 Kriterien über SSOT, Exporte, Plugin, Skills, Doku |
| Abnahme | Playwright + Lighthouse | Browserregression, A11y, SEO, CWV und Budgets |

## Einmalige Einrichtung in Figma

Es gibt zwei Wege. **Weg A** ist der schnelle, empfohlene: Ein Plugin baut die
Datei aus der SSOT auf. **Weg B** ist der manuelle Weg über Tokens Studio, für
den Fall, dass jemand die Struktur von Hand nachvollziehen will.

### Weg A – Plugin „FranksFinanzcheck – Design System“ (empfohlen)

> **Schritt für Schritt mit Screenshots-Pfaden, Fehlerliste und Prüfschritten:**
> [`ANLEITUNG-FIGMA-EINRICHTUNG.md`](ANLEITUNG-FIGMA-EINRICHTUNG.md).
> Dieses Kapitel ist die Kurzfassung.

1. Eine leere Datei **„FranksFinanzcheck – Design System“** anlegen.
2. In Figma auf **Plugins → Development → Import plugin from manifest …**
   klicken und `figma/design-system-builder/manifest.json` auswählen.
3. Das Plugin **einmal** ausführen (Plugins → Development → FranksFinanzcheck).
   Es legt an:
   - die Seiten aus `figma.page_order`,
   - die Variablen-Sammlungen *Primitives*, *Semantik* (Hell/Dunkel mit
     echten Aliassen), *Abstand* und *Radius*,
   - Dev-Mode-Code-Syntax `var(--ff-…)` je Variable,
   - Textstile (Desktop **und** Mobil), Farb- und Schattenstile,
   - ein Komponenten-Set je Komponente mit den Achsen **Zustand × Modus**,
   - ein Cover mit Stand, Zahlen und Herkunft.
4. Das Protokoll im Plugin nennt, was **neu** war und was **bereits vorhanden**
   ist. Das Plugin ist idempotent: ein zweiter Lauf legt nichts doppelt an.
5. Nach dem Import die vergebene Plugin-ID in `data/design/handoff.yaml` unter
   `figma.plugin_id` eintragen. Damit wird das Warn-Kriterium **P8** erfüllt
   und die Datei bleibt über Läufe hinweg eindeutig zugeordnet.

> Das Plugin läuft **ohne Netzverbindung** (`networkAccess.allowedDomains:
> ["none"]`), veröffentlicht nichts und ist aus `source.js` + Datenblock
> generiert. `code.js` niemals von Hand bearbeiten – sonst stoppt
> `npm run design:handoff:check`.

### Weg B – manuell über Tokens Studio

1. Tokens Studio installieren und `design/handoff/figma-tokens.tokens.json`
   als lokale JSON-Quelle importieren.
2. Themes **Light** und **Dark** den gleichnamigen Token-Sets zuordnen.
3. Komponenten exakt nach `component-inventory.md` benennen. Interaktive
   Komponenten benötigen die dort genannten Fokus-, Fehler-, Disabled- und
   Dark-Mode-Zustände.
4. Muster und Verbote aus `patterns.md` übernehmen; die Kontrastwerte aus
   `ANNOTATIONEN.md` sind die Abnahmegrenze, nicht ein Vorschlag.
5. Frames mindestens bei 390, 768 und 1280 px prüfen. Inhalte nicht durch
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

# Figma-Handoff: erzeugen, prüfen, Selbsttest
npm run figma:bauen
npm run design:handoff:check
npm run figma:gate
npm run figma:selftest

# Varianten- und Qualitätskette
npm ci
npm run design:lauf v-meine-variante
npm run design:messen v-meine-variante
npm run design:quality
npm run test:e2e
```

`figma:gate` prüft 33 Kriterien in fünf Ebenen – SSOT, Exporte, Plugin, Skills,
Doku. Ein Kriterium ist entweder erfüllt oder es nennt mit einer Zeile, was
fehlt. `--streng` behandelt Warnungen wie Fehler.

`design:handoff:check` läuft zusätzlich im Workflow **Design-Varianten**. Jede
manuelle Änderung an einem generierten Export erzeugt Drift und stoppt das Gate.
Lighthouse ist direkt und versionsfest als Dev-Dependency installiert; die
Messung läuft über `e2e/variant-metrics.mjs` mobil als maßgebliches Profil und
desktop als Vergleich. Playwright bleibt für Desktop- und Mobile-Regressionen
zuständig.

## Definition of Done für den Handoff selbst

- `npm run figma:selftest` grün (Generator **und** Gate, inklusive Sabotage-Proben).
- `npm run design:handoff:check` ohne Drift.
- `npm run figma:gate` ohne Fehler; Warnungen sind benannt und begründet.
- Jede Komponente im Inventar existiert im CSS; jede Rolle in beiden Modi.
- Kontrast-Matrix vollständig und rechnerisch ≥ 4,5:1.
- Plugin-Manifest ohne Netzzugriff; `code.js` aus `source.js` erzeugt.

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
