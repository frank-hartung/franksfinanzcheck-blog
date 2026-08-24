# Vendor-Dateien

Diese Dateien werden first-party ausgeliefert, damit FranksFinanzcheck keine zusätzlichen CDN-/Drittanbieter-Requests für Animationen erzeugt.

- `gsap.min.js` – GSAP 3.13.0
- `ScrollTrigger.min.js` – GSAP ScrollTrigger 3.13.0

Quelle: https://cdn.jsdelivr.net/npm/gsap@3.13.0/dist/

Wenn GSAP aktualisiert werden soll:

```bash
bash tools/update-gsap-vendor.sh
```
