# Automatischer FCP-Optimierer für Bilder

Stand: 24.08.2026

## Ziel

FCP misst, wann der erste sichtbare Inhalt gerendert wird. Bilder sind dabei oft nicht direkt render-blocking, können aber den frühen kritischen Pfad verschlechtern, wenn sie:

- mit dem LCP-Cover um Bandbreite konkurrieren,
- ohne feste Dimensionen Layout-Arbeit verursachen,
- synchron decodiert werden,
- unnötig früh oder mit hoher Priorität geladen werden,
- als riesiges inline-SVG den DOM aufblähen.

Der FCP-Bildoptimierer setzt deshalb eine klare Prioritäts-Strategie für alle Bildrollen.

## Neues Tool

```bash
python3 scripts/fcp_image_optimizer.py --fix
```

Das schreibt:

```txt
data/fcp_images.json
```

Prüfung nach einem Hugo-Build:

```bash
hugo --minify
python3 scripts/fcp_image_optimizer.py --check
```

JSON-Report:

```bash
python3 scripts/fcp_image_optimizer.py --check --json
```

## Bildrollen

### 1. Logo

```html
<img data-ff-fcp-image="logo" fetchpriority="low" decoding="async" loading="eager">
```

Das Logo ist klein und dimensioniert, darf aber nicht mit dem LCP-Cover konkurrieren. Es wird deshalb extern als SVG-Bild geladen statt als inline-SVG-DOM-Baum.

### 2. LCP-Bild

```html
<img data-ff-lcp="candidate" data-ff-fcp-image="lcp" fetchpriority="high" loading="eager" decoding="async">
```

Nur der echte LCP-Kandidat bekommt hohe Priorität.

### 3. Nicht-kritische Bilder

```html
<img data-ff-fcp-image="deferred" loading="lazy" decoding="async" fetchpriority="low">
```

Alle übrigen Bilder werden bewusst vom FCP-Pfad ferngehalten.

## Qualitätsregeln

Das Tool prüft den gebauten HTML-Output auf:

- nicht mehr als ein High-Priority-Bild pro Seite,
- nicht mehr als ein `data-ff-lcp="candidate"` pro Seite,
- `width` und `height` für alle Inhaltsbilder,
- `decoding="async"` für alle Inhaltsbilder,
- Nicht-LCP-Bilder sind `loading="lazy"`,
- Nicht-LCP-Bilder haben keine konkurrierende hohe Priorität,
- Logo ist `fetchpriority="low"`.

## Kopplung mit anderen Optimierern

`image_optimizer.py --fix` aktualisiert automatisch:

```txt
data/image_optimizer_manifest.json
data/lcp_images.json
data/fcp_images.json
```

`generate_covers.py` aktualisiert ebenfalls LCP- und FCP-Manifeste, sobald neue Cover entstehen.

## Geänderte Templates

```txt
layouts/_partials/header.html
layouts/_partials/cover.html
layouts/_partials/extend_post_content.html
layouts/pillar/single.html
layouts/_partials/trust_box.html
layouts/shortcodes/autor-foto.html
```

## Ergebnis

Der Browser lädt weiterhin das wichtige LCP-Bild früh, während Logo, Related Cards, Autorenbilder und andere nicht-kritische Bilder keine unnötige Konkurrenz im FCP-/LCP-Zeitfenster erzeugen.
