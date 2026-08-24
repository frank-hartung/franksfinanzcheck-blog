# Automatischer LCP-Optimierer für Bilder

Stand: 24.08.2026

## Ziel

Der LCP-Optimierer sorgt dafür, dass das wahrscheinlich größte Above-the-fold-Bild jeder wichtigen Seite automatisch im kritischen Ladepfad landet:

- richtiges Bild erkennen,
- nur passende Mobile-/Desktop-Breiten preladen,
- AVIF bevorzugen,
- `imagesizes` synchron zum späteren `<picture>` halten,
- `fetchpriority="high"` und `loading="eager"` für echte LCP-Kandidaten setzen,
- keine 1000px-Übergröße im Preload anbieten.

## Neues Tool

```bash
python3 scripts/lcp_image_optimizer.py --fix
```

Das Tool schreibt:

```txt
data/lcp_images.json
```

Dieses Hugo-Datenmanifest wird in `layouts/_partials/head.html` gelesen und erzeugt den passenden Preload pro Seite.

## Strategie

### Artikel-Seiten

Für einzelne Artikel ist das Artikel-Cover der LCP-Kandidat:

```txt
/posts/<slug>/ → cover.image
sizes: (min-width: 768px) 720px, 100vw
```

### Startseite und Blogliste

Für Startseite und `/posts/` ist das erste sichtbare Listen-Cover der Bild-LCP-Kandidat:

```txt
/        → erstes sichtbares Post-Cover
/posts/  → erstes sichtbares Post-Cover
sizes: (min-width: 768px) 620px, 100vw
```

## Preload-Breiten

```txt
360w
480w
620w
720w
```

Bewusst nicht im Preload:

```txt
1000w
```

Die 1000px-Datei bleibt als Social-/Fallback-Reserve erhalten, wird aber nicht als LCP-Kandidat angeboten. Das verhindert, dass Chrome auf HiDPI-Geräten unnötig große Dateien lädt.

## Integration

Geänderte/gekoppelte Dateien:

```txt
scripts/lcp_image_optimizer.py
scripts/image_optimizer.py
scripts/generate_covers.py
layouts/_partials/head.html
layouts/_partials/cover.html
data/lcp_images.json
```

`image_optimizer.py --fix` aktualisiert das LCP-Manifest automatisch mit. `generate_covers.py` aktualisiert es ebenfalls, wenn neue Covers erzeugt werden.

## Befehle

### Manifest erzeugen/aktualisieren

```bash
python3 scripts/lcp_image_optimizer.py --fix
```

### Prüfen

```bash
python3 scripts/lcp_image_optimizer.py --check
```

### JSON-Report

```bash
python3 scripts/lcp_image_optimizer.py --json
```

## Qualitäts-Gates

Das Tool prüft:

- Originalbild existiert,
- alle AVIF-LCP-Varianten existieren,
- keine LCP-AVIF-Variante ist ungewöhnlich groß,
- mindestens ein LCP-Preload existiert.

## Ergebnis im HTML

Im `<head>` erscheint ein Preload wie:

```html
<link rel="preload" as="image" type="image/avif" fetchpriority="high"
  data-ff-lcp-optimizer="true"
  imagesrcset="... 360w, ... 480w, ... 620w, ... 720w"
  imagesizes="(min-width: 768px) 620px, 100vw">
```

Das tatsächliche LCP-`img` erhält zusätzlich:

```html
data-ff-lcp="candidate"
```

Damit lässt sich später im HTML oder per Browser-Test schnell prüfen, welches Bild vom Optimierer priorisiert wurde.
