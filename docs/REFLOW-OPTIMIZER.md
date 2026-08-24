# Forced-Reflow Optimizer

Stand: 24.08.2026

## Problem

Lighthouse meldete erzwungene dynamische Umbrüche aus:

```txt
premium/vendor/ScrollTrigger.min.js
```

Ursache: ScrollTrigger muss für Scroll-Start-/Endpunkte Layout-Geometrie messen. Das ist für Showreel-/Landingpages oft akzeptabel, für einen schnellen Finanzblog aber unnötig.

## Lösung

Die Premium-Effekte bleiben erhalten, aber Scroll-Effekte laufen jetzt ohne ScrollTrigger:

- Hero-Motion: GSAP-Timeline, zeitbasiert, keine Layoutmessung
- Scroll-Reveals: IntersectionObserver + CSS-Klassen
- Fortschrittsbalken: Scroll-Höhe wird außerhalb des Scroll-Hotpaths gecacht
- Karten-Glow: `getBoundingClientRect()` wird auf `pointerenter` gecacht, nicht auf jedem `pointermove`
- ScrollTrigger wird nicht mehr im Footer geladen

## Neues Tool

```bash
python3 scripts/reflow_optimizer.py --fix
```

Das schreibt:

```txt
data/reflow_optimizer_manifest.json
```

Prüfung nach einem Hugo-Build:

```bash
hugo --minify
python3 scripts/reflow_optimizer.py --check
```

JSON-Report:

```bash
python3 scripts/reflow_optimizer.py --check --json
```

## Budgets

```txt
maxScrollTriggerScripts: 0
maxScrollTriggerUsages: 0
maxHotPathGeometryReads: 0
```

## Geänderte Dateien

```txt
static/premium/ff-premium.js
layouts/_partials/extend_footer.html
scripts/reflow_optimizer.py
data/reflow_optimizer_manifest.json
docs/REFLOW-OPTIMIZER.md
```

## Erwartetes Lighthouse-Ergebnis

Die Quelle

```txt
premium/vendor/ScrollTrigger.min.js
```

soll nach Deploy nicht mehr im Bericht „Erzwungener dynamischer Umbruch“ auftauchen, weil die Datei nicht mehr geladen wird.

Falls Lighthouse weiterhin Reflow-Hinweise zeigt, sollten sie nicht mehr von ScrollTrigger stammen. Dann kann `scripts/reflow_optimizer.py --check` als Quality-Gate genutzt werden, um neue Hotpath-Geometrie-Lesezugriffe zu finden.
