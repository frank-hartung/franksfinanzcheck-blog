# ⚡ Core-Web-Vitals-Wächter (Agentur/Performance)
**Stand:** 2026-09-07 · **Messmethode:** deterministisch (kein Browser)

## 🤖 Gesamt-Ampel: **GREEN**

| Kanal | Befunde |
|---|---|
| Bild-Budget (`static/`) | 0 |
| Build-Hygiene (`public/`) | 0 |

**Build gemessen:** ja

## Befunde

_Alle Soll-Werte eingehalten._

## Kennzahlen (static/)

- Bilder gesamt: **517** (Summe 14.2 MB)
- Cover: **496** · größtes Cover 135 KB

## Kennzahlen (public/)

- HTML-Dateien: **324** · JS-Dateien 4 (245 KB) · CSS 0 (0 KB)
- Inline-<style>: 0 · externe Skripte ohne async/defer: 0 · Inline-JS-Blöcke: 278 · JSON-LD/strukturierte Daten (nicht blockierend): 38 · <img> ohne Größensetzung: 0

## Empfehlungen

1. **LCP:** Größtes Cover als AVIF/WebP ausliefern (`generate_covers.py` erzeugt die
   Varianten bereits; den `<picture>`-Tag via `cover.html` nutzen).
2. **Bild-Budget:** Bilder > 220 KB komprimieren oder per `<picture>` responsive servieren.
3. **INP/JS:** externe Skripte mit `defer` laden, Inline-JS minimieren.
4. **CLS:** jedem `<img>` `width`/`height`/`aspect-ratio` mitgeben.
5. **Mess-Schleife:** diesen Wächter wöchentlich in `seo-weekly.yml` nach dem Hugo-Build.   laufen lassen (siehe Premium-Governance-Workflow).

_Automatisch erzeugt von `scripts/cwv_guard.py` am 2026-09-07._
