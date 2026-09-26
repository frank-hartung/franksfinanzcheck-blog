# assets/css/varianten/ – Varianten-Stylesheets (NICHT ausgeliefert)

Dieses Verzeichnis liegt bewusst **neben** `assets/css/extended/` und nicht
darin.

**Der Grund steht in `layouts/_partials/head.html` Zeile 66:**

```go-html-template
{{- $extended := (resources.Match "css/extended/*.css") | resources.Concat ... }}
```

Alles unter `css/extended/` wird bei **jedem** Build in das eine
ausgelieferte Stylesheet gebündelt. Eine Datei, die dort landet, ist damit
sofort auf jeder Seite in Produktion – genau das soll bei Varianten
unmöglich sein.

Dateien hier werden nur von `layouts/_partials/design_variante.html`
geladen, und auch nur dann, wenn der Hugo-Parameter `designVariante` exakt
auf ihre ID zeigt. Ohne Parameter erzeugt der Build **kein einziges Byte**
aus diesem Verzeichnis.

## Regeln für eine Datei hier

| Regel | Geprüft von |
|---|---|
| Dateiname = Varianten-ID aus `data/design/varianten.yaml` | `design_variant_gate.py` |
| Nur Marken-Tokens (Farben, Radien, Schatten, Easing) | `design_variant_gate.py` |
| Dark-Mode-Entsprechung, sobald Farben gesetzt werden | `design_variant_gate.py` |
| `prefers-reduced-motion`, sobald Bewegung entsteht | `design_variant_gate.py` |
| Kein `!important`, kein `@font-face`, keine externen URLs | `design_variant_gate.py` |
| ≤ 8 KB roh | `design_variant_gate.py` (`marke.css_budget_bytes`) |

Anleitung: [`docs/ANLEITUNG-DESIGN-VARIANTEN.md`](../../../docs/ANLEITUNG-DESIGN-VARIANTEN.md)
