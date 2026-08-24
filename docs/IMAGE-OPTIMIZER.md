# Image Optimizer für FranksFinanzcheck

Stand: 24.08.2026

## Ziel

Dieses Tool automatisiert die Bildauslieferung auf Mobile und Desktop nach Performance-/Agentur-Standard:

- passende Bildbreiten statt übergroßer Originale,
- AVIF zuerst, WebP als Fallback, JPEG als letzter Fallback,
- sichere Prüfung gegen Fake-AVIF/Fake-WebP,
- Manifest für Audits und Lighthouse-Kontrolle,
- Integration in die Hugo-Templates für Cover, Related Cards und Pillar Cards.

## Zentrales Tool

```bash
python3 scripts/image_optimizer.py --fix
```

Das Tool scannt die Original-Cover unter:

```txt
static/images/covers/*.jpg
```

und erzeugt automatisch:

```txt
static/images/covers/360/*.jpg
static/images/covers/480/*.jpg
static/images/covers/620/*.jpg
static/images/covers/720/*.jpg

static/images/covers/webp/360/*.webp
static/images/covers/webp/480/*.webp
static/images/covers/webp/620/*.webp
static/images/covers/webp/720/*.webp
static/images/covers/webp/*.webp

static/images/covers/avif/360/*.avif
static/images/covers/avif/480/*.avif
static/images/covers/avif/620/*.avif
static/images/covers/avif/720/*.avif
static/images/covers/avif/*.avif
```

## Warum diese Breiten?

```txt
360 px  → kleine Smartphones
480 px  → große Smartphones / kleine DPR-Spielräume
620 px  → Bloglisten / Karten
720 px  → Single-Artikel / größere Desktop-Ansicht
1000 px → nur als WebP/AVIF-Fallback/OG-Reserve, nicht im normalen srcset
```

Die 1000px-Datei wird bewusst nicht mehr im normalen `srcset` angeboten, damit Chrome/Lighthouse bei kleinen Layoutbreiten nicht unnötig die große Originaldatei lädt.

## Befehle

### Varianten erzeugen oder ergänzen

```bash
python3 scripts/image_optimizer.py --fix
```

### Alles neu encodieren

```bash
python3 scripts/image_optimizer.py --force
```

### Prüfen

```bash
python3 scripts/image_optimizer.py --check
```

### JSON-Report

```bash
python3 scripts/image_optimizer.py --json
```

## Manifest

Bei `--fix` oder `--force` wird geschrieben:

```txt
data/image_optimizer_manifest.json
```

Darin stehen Quelle, Varianten, Breiten, Höhen und Dateigrößen. Das ist nützlich für Audits und Regressionen.

## Template-Integration

Die folgenden Templates nutzen die Varianten automatisch:

```txt
layouts/_partials/cover.html
layouts/_partials/head.html
layouts/_partials/extend_post_content.html
layouts/pillar/single.html
```

## Qualitätswerte

```txt
JPEG: 82, progressive + optimize
WebP: 78, method 6
AVIF: 45, speed 6
```

Diese Werte sind für die grafischen FranksFinanzcheck-Cover bewusst gewählt: sehr kleine Dateien, aber ausreichend scharfe Typografie.

## Installation lokal/CI

Falls die Pakete fehlen:

```bash
python3 -m pip install pillow pillow-avif-plugin
```

Die bestehenden Workflows installieren Pillow bereits. `generate_covers.py` nutzt jetzt dieselbe Optimierungslogik wie `image_optimizer.py`, damit neue Artikel automatisch die gleichen Mobile-/Desktop-Varianten erhalten.
