# Automatischer DOM-Größe-Optimierer für Layouts

Stand: 24.08.2026

## Ziel

Der DOM-Optimizer verhindert, dass Hugo-Layouts mit der Zeit unnötig viele Elemente, tiefe Verschachtelungen oder dekorative Inline-SVGs aufbauen. Das verbessert:

- Style-Recalculation,
- Layout-/Reflow-Kosten,
- Memory-Nutzung,
- Responsiveness,
- Lighthouse-Hinweise zur DOM-Größe.

## Neues Tool

```bash
python3 scripts/dom_size_optimizer.py --fix
```

Das Tool analysiert den gebauten Hugo-Output unter `public/` und schreibt:

```txt
data/dom_optimizer_manifest.json
```

Prüfung:

```bash
hugo --minify
python3 scripts/dom_size_optimizer.py --check
```

JSON-Report:

```bash
python3 scripts/dom_size_optimizer.py --check --json
```

## Budgets

```txt
maxElements:        700
maxDepth:            15
maxDirectChildren:  120
maxInlineSvg:         4
maxInlineSvgPaths:    8
```

Diese Budgets sind bewusst strenger als Lighthouse-Warnschwellen, aber realistisch für FranksFinanzcheck.

## Eingebaute Layout-Optimierungen

### 1. Header-Logo bleibt extern

Das Logo wird nicht als großer Inline-SVG-Pfadbaum in den DOM injiziert, sondern als externes SVG-Bild geladen. Dadurch sinken DOM-Tiefe und HTML-Gewicht.

### 2. Redundanter Screenreader-Span entfernt

Der Header-Link hat bereits ein klares `aria-label`. Der zusätzliche versteckte Textknoten wurde entfernt.

### 3. Dekorative Pinterest-SVGs ersetzt

Wiederholte dekorative Inline-SVGs wurden durch ein kleines, barrierefrei verstecktes Emoji/Icon-Element ersetzt:

```html
<span class="ff-icon-pinterest" aria-hidden="true">📌</span>
```

Das spart SVG-/Path-Knoten in Footer und Artikel-CTA.

## Manifest-Inhalt

Das Manifest enthält:

- Gesamtzahl der geprüften Seiten,
- maximale Elementanzahl,
- maximale DOM-Tiefe,
- maximale Anzahl direkter Kinder,
- Anzahl Inline-SVGs und SVG-Pfade,
- Worst-Case-Seiten nach Elementen, Tiefe und Kindern.

## Empfohlener Workflow

```bash
hugo --minify
python3 scripts/dom_size_optimizer.py --fix
python3 scripts/dom_size_optimizer.py --check
```

Wenn der Check fehlschlägt, sollte zuerst geprüft werden:

1. Werden dekorative Icons inline als SVG wiederholt?
2. Gibt es unnötige Wrapper-`div`/`span`?
3. Gibt es große wiederholte Komponenten auf Listen- oder Artikelseiten?
4. Ist ein komplexes SVG versehentlich inline statt extern eingebunden?

## Warum kein aggressives HTML-Flattening?

Der Optimierer entfernt nicht blind Wrapper, weil das Layout, Barrierefreiheit oder CSS-Selektoren beschädigen könnte. Stattdessen kombiniert er sichere Layout-Verbesserungen mit einem automatischen DOM-Budget-Gate.
