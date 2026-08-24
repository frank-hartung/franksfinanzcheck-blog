# Premium Blog Enhancements: GSAP + kostenlose UX-Tools

Stand: 24.08.2026

## Ziel

FranksFinanzcheck soll moderner wirken, ohne wie eine laute Agentur-Demo auszusehen. Für einen Finanz-/Verbraucherblog ist die passende Premium-Richtung:

- vertrauenswürdig,
- schnell,
- lesefreundlich,
- DSGVO-schonend,
- mit subtiler Bewegung statt Effekthascherei.

Deshalb wurden GSAP-Effekte als **progressive enhancement** eingebaut: Die Seite funktioniert vollständig ohne JavaScript, bei reduzierter Bewegung und bei fehlendem GSAP.

## Eingebaute Dateien

```txt
assets/css/extended/z-premium-blog.css
static/premium/ff-premium.js
static/premium/vendor/gsap.min.js
static/premium/vendor/README.md
tools/update-gsap-vendor.sh
```

Außerdem wurde `layouts/_partials/extend_footer.html` erweitert, damit die JavaScript-Dateien first-party/self-hosted geladen werden.

## Features

### 1. GSAP ohne ScrollTrigger-Reflow

- Hero-Intro auf der Startseite per GSAP-Timeline.
- Sanfte Scroll-Reveals für Artikelkarten und Artikelabschnitte per IntersectionObserver.
- Kein ScrollTrigger im Runtime-Pfad, damit Lighthouse keine erzwungenen Layout-/Reflow-Messungen aus ScrollTrigger meldet.
- Animiertes Geld-Highlight, z. B. `1.800 €` im Startseiten-Hero.

### 2. Premium-Look

- Sticky Glass-Header.
- Fortschrittsbalken am oberen Rand.
- Hochwertiger grüner Hero mit Brand-Akzent `#ffb300`.
- Modernere Blogkarten mit Hover-Lift, Bild-Microanimation und Pointer-Glow.
- Bessere Artikel-Überschriften, Tabellen und Zitate.

### 3. Artikel-UX

- Mini-Inhaltsverzeichnis auf Desktop bei längeren Artikeln.
- Copy-Link-Buttons an `h2`/`h3`-Überschriften.
- Interne Links werden bei Hover/Fokus/Touch per `prefetch` vorbereitet.

### 4. Datenschutz & Performance

- Keine Cookies.
- Kein Tracking.
- Keine externen Runtime-CDN-Aufrufe, weil GSAP lokal unter `static/premium/vendor/` liegt.
- `prefers-reduced-motion` wird respektiert.
- `navigator.connection.saveData` wird beim Prefetch respektiert.

## GSAP aktualisieren

```bash
bash tools/update-gsap-vendor.sh
```

Optional mit Versionsnummer:

```bash
bash tools/update-gsap-vendor.sh 3.13.0
```

## Rollback

1. In `layouts/_partials/extend_footer.html` den Block `Premium Blog Enhancements` entfernen.
2. Diese Dateien löschen:

```txt
assets/css/extended/z-premium-blog.css
static/premium/ff-premium.js
static/premium/vendor/gsap.min.js
static/premium/vendor/README.md
tools/update-gsap-vendor.sh
```

Danach baut der Blog wieder ohne die Premium-Erweiterungen.
