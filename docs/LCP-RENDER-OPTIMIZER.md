# LCP Render-Delay Optimizer

Stand: 24.08.2026

## Problem

Lighthouse zeigt in der LCP-Aufschlüsselung eine sehr hohe:

```txt
Verzögerung beim Rendering des Elements
```

Das bedeutet: Die Bilddatei ist bereits geladen, wird aber spät gemalt. Bei FranksFinanzcheck kann das passieren, wenn ein Above-the-fold-Cover durch Scroll-Reveal-Logik zuerst `opacity: 0` oder `transform` bekommt und erst nach einem JavaScript-/IntersectionObserver-Callback sichtbar wird.

## Lösung

Der LCP-Kandidat darf niemals durch Reveal-Animationen versteckt werden.

Eingebaut wurde:

- LCP-Karten (`.lcp-card`) werden aus `ff-will-reveal` ausgeschlossen.
- Bilder mit `data-ff-lcp="candidate"` werden aus Reveal-Hiding ausgeschlossen.
- Ein defensiver CSS-Guard erzwingt für LCP-Kandidaten:

```css
opacity: 1;
transform: none;
content-visibility: visible;
```

## Neues Tool

```bash
python3 scripts/lcp_render_optimizer.py --fix
```

Das schreibt:

```txt
data/lcp_render_optimizer_manifest.json
```

Prüfung nach einem Hugo-Build:

```bash
hugo --minify
python3 scripts/lcp_render_optimizer.py --check
```

JSON-Report:

```bash
python3 scripts/lcp_render_optimizer.py --check --json
```

## Quality-Gates

Das Tool prüft:

- LCP-Kandidaten werden nicht mit `ff-will-reveal` versteckt,
- genau ein LCP-Kandidat pro Seite,
- LCP-Bild ist `loading="eager"`,
- LCP-Bild ist `fetchpriority="high"`,
- LCP-Bild hat feste Dimensionen,
- `ff-premium.js` enthält den LCP-Filter,
- CSS enthält den defensiven LCP-Guard.

## Erwartetes Ergebnis

Nach Deploy sollte die LCP-Aufschlüsselung weniger Zeit bei:

```txt
Verzögerung beim Rendering des Elements
```

zeigen. Die LCP-Zeit sollte stärker vom eigentlichen Ressourcenladen abhängen, nicht davon, dass JavaScript das Bild erst später sichtbar macht.
