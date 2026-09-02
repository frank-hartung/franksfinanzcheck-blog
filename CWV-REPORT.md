# ⚡ Core-Web-Vitals-Wächter (Agentur/Performance)
**Stand:** 2026-09-02 · **Messmethode:** deterministisch (kein Browser)

## 🤖 Gesamt-Ampel: **AMBER**

| Kanal | Befunde |
|---|---|
| Bild-Budget (`static/`) | 0 |
| Build-Hygiene (`public/`) | 1 |

## Befunde

| Ebene | Code | Details |
|---|---|---|
| AMBER | render_block_js | 675 Skripte ohne async/defer (INP-Risiko) |

## Kennzahlen (static/)

- Bilder gesamt: **427** (Summe 11.9 MB)
- Cover: **406** · größtes Cover 135 KB

## Kennzahlen (public/)

- HTML-Dateien: **283** · JS-Dateien 3 (84 KB) · CSS 0 (0 KB)
- Inline-<style>: 0 · Skripte ohne async/defer: 675 · <img> ohne Größensetzung: 0

## Empfehlungen

1. **LCP:** Größtes Cover als AVIF/WebP ausliefern (`generate_covers.py` erzeugt die
   Varianten bereits; den `<picture>`-Tag via `cover.html` nutzen).
2. **Bild-Budget:** Bilder > 220 KB komprimieren oder per `<picture>` responsive servieren.
3. **INP/JS:** externe Skripte mit `defer` laden, Inline-JS minimieren.
4. **CLS:** jedem `<img>` `width`/`height`/`aspect-ratio` mitgeben.
5. **Mess-Schleife:** diesen Wächter wöchentlich in `seo-weekly.yml` nach dem Hugo-Build.   laufen lassen (siehe Premium-Governance-Workflow).

_Automatisch erzeugt von `scripts/cwv_guard.py` am 2026-09-02._
