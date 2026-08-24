# CLS Optimizer

Stand: 24.08.2026

## Problem

Lighthouse zeigte einen sehr kleinen Layout Shift:

```txt
Gesamt: 0,001
Culprit: Hero-Absatz „Beim Internet-Tarif zahlen viele Haushalte …“
```

Der Wert ist bereits sehr gut, aber die Ursache lässt sich weiter absichern:

1. Der Hero-Absatz wurde mit `y/transform` eingeblendet.
2. Der Euro-Betrag im Hero konnte per JS numerisch animiert werden, was die Inline-Breite verändert.

Beides kann in Lighthouse als kleiner Layout-/Render-Shift auftauchen.

## Lösung

### 1. Hero-Reveal nur noch per Opacity

Statt:

```js
y: 24
```

wird der Hero nur noch über `opacity/visibility` eingeblendet. Das vermeidet sichtbare Positionsänderungen im Above-the-fold-Bereich.

### 2. Kein Umschreiben des Euro-Betrags

Der Betrag `1.800 €` bleibt ab First Paint als finaler Text im HTML. Es gibt keine Animation mehr von `0 €` auf `1.800 €`, weil das die Zeilenbreite verändern kann.

### 3. Breite des Hero-Betrags reserviert

```css
.first-entry.home-info .entry-content strong {
  display: inline-block;
  min-width: 7ch;
  text-align: right;
  font-variant-numeric: tabular-nums;
}
```

## Neues Tool

```bash
python3 scripts/cls_optimizer.py --fix
```

Das schreibt:

```txt
data/cls_optimizer_manifest.json
```

Prüfung nach Hugo-Build:

```bash
hugo --minify
python3 scripts/cls_optimizer.py --check
```

JSON-Report:

```bash
python3 scripts/cls_optimizer.py --check --json
```

## Quality-Gates

Das Tool prüft:

- Hero-Animation ist opacity-only,
- kein JS-Rewrite des Geldbetrags,
- Hero-Geldbetrag reserviert Breite,
- Bilder haben `width` und `height`,
- maximal ein LCP-Kandidat pro Seite.

## Erwartetes Ergebnis

Der gemeldete CLS-Culprit im Hero-Absatz sollte nach Deploy verschwinden oder bei 0 bleiben. Der aktuelle Ausgangswert `0,001` ist zwar unkritisch, aber diese Änderung stabilisiert den Above-the-fold-Bereich zusätzlich.
