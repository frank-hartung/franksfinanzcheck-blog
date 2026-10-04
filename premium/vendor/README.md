# Vendor-Dateien

Diese Datei wird first-party ausgeliefert, damit FranksFinanzcheck keine zusätzlichen CDN-/Drittanbieter-Requests für Premium-Motion erzeugt.

- `gsap.min.js` – GSAP 3.13.0

**Kein ScrollTrigger im Runtime-Pfad:** Scroll-Reveals laufen bewusst über IntersectionObserver, damit Lighthouse keine erzwungenen Layout-/Reflow-Messungen aus ScrollTrigger meldet.

Quelle: https://cdn.jsdelivr.net/npm/gsap@3.13.0/dist/

Wenn GSAP aktualisiert werden soll:

```bash
bash tools/update-gsap-vendor.sh
```
