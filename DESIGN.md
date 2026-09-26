# DESIGN.md – Design-System von FranksFinanzcheck

> Technische Design-System-Dokumentation. Wird von KI-Agenten (Impeccable,
> frontend-design, taste-skill, web-design-guidelines) gemeinsam mit
> PRODUCT.md vor jeder UI-Arbeit gelesen. Stand: 12.09.2026
> (Design-Skills-Rollout). Generiert aus dem echten CSS-Bestand
> (assets/css/extended/) und mit `e2e/design-metrics.mjs` verifiziert.

## 1. Farb-Tokens

```css
/* Hell-Modus (custom.css :root) */
--ff-emerald:        #0E5A43;  /* Marke, H1–H3, Links (8.2:1 auf Weiß) */
--ff-emerald-dark:   #0A4634;  /* Link-Hover (10.5:1) */
--ff-emerald-soft:   #EAF4EF;  /* Soft-Flächen, Badges, Chips */
--ff-emerald-bright: #7FD1B4;  /* H-Überschriften Dark Mode (10.3:1 auf #1D1E20) */
--ff-anthracite:     #2E2E33;  /* Fließtext (13.1:1 auf --theme) */
--ff-yellow:         #FFB300;  /* CTA-Flächen, Fokus-Ring, Progress (NIE Text auf hell!) */
--ff-yellow-dark:    #E6A100;  /* CTA-Hover-Fläche */
--ff-accent-2:       #FFD15A;  /* Text-Links auf Smaragd-Flächen (5.8:1) */
--ff-ink:            #17211D;  /* dunkelste Textstufe */
--selection:         rgba(255, 179, 0, 0.38); /* ::selection thematisiert */

/* Flächen (PaperMod-Variablen, überschrieben) */
--theme:  #FAFCFB (Seite hell) / #1D1E20 (Dark via data-theme="dark")
--entry:  #FFFFFF (Karte hell) / #2E2E33 (Dark)
--border: #DCE6E1 (hell) / #333 (Dark, PaperMod)
```

Regeln:
- Sekundärtext nie neutral-grau auf farbigen Flächen – vom Farbton der
  Fläche abtönen (Dark Mode: `--secondary` #9B9C9D, 6.0:1).
- Signalgelb nur als Fläche/Akzent oder Text auf Smaragd (dann `--ff-accent-2`).
- Kontrast-Soll: Fließtext ≥ 4.5:1, große Typo ≥ 3:1 – pflichtweise messen:
  `node e2e/design-metrics.mjs`.

## 2. Typografie

| Stufe | Größe | Gewicht | Familie | Messwert |
|---|---|---|---|---|
| H1 Startseite | 56px (clamp) | 700 | Inter | – |
| H1 Artikel (.post-title) | ~36px | 700 | Inter | – |
| H2 | 24px | 700 | Inter + 2px Signalgelb-Unterstreichung | 7.95:1 hell / 9.28:1 dunkel |
| H3 | 16.8px | 700 | Inter | – |
| Fließtext | 18px-Basis | 400 | System-UI | Messweite 65ch, 16:1 hell / 9.6:1 dunkel |
| Meta | .88em | 400–600 | System-UI | 5.1–6.1:1 |
| Subline-Akzent | – | italic | Playfair Display | nur auf Smaragd |

- Body bewusst OHNE Webfont (Performance/Fokus auf LCP-Cover).
- `text-wrap: balance` auf Überschriften; `tabular-nums` in Zahlen/Tabellen
  (25 Verwendungen).
- Dark Mode: H1–H3 in `--ff-emerald-bright`.

## 3. Abstände & Raster

- Arbeitsskala: 8 / 10 / 12 / 14 / 16 / 18 / 20 / 22 / 24 / 32 px
  (14/18/22 sind bewusste Feinstufen des Blogs, dokumentiert in
  z-premium-blog.css).
- Rhythmus-Regel: mehr Abstand ÜBER einer Überschrift als darunter
  (gemessen: h3 44px über / 16px unter ✓).
- Content-Breite: `--main-width: 720px`, Nav 1024px, 4er-Spalten-Grid der
  Teaser auf Desktop, 1er mobil.

## 4. Elevation & Flächen

```css
/* Ebenen-Skala (alle mit Versatz + weichem Blur) */
Stufe 1 (Karte):     0 2px 6px rgba(0,0,0,.05)
Stufe 2 (Hover):     0 6px 20px rgba(14,90,67,.14)
Stufe 3 (Schwebend): 0 8px 24px rgba(15,52,43,.06–.08)
CTA-Glow (einziger zulässiger Akzent-Schatten):
                     0 3px 10px rgba(255,179,0,.4)
```

- Radius-Skala: `--ff-radius-sm: 8px` (Bilder) · `--ff-radius-md: 12px`
  (Karten) · `--ff-radius-lg: 16px` (Boxen) · `999px` (Pills/kleine Controls).
  Karten bleiben bei 12–16px (Impeccable-Floor). 18px-Ausreißer wurden am
  12.09.2026 auf 16px normalisiert.
- Schatten ODER Border pro Fläche, nicht beides hart übereinander.
- Z-Ordnung: Progress-Shell 999998 · Consent-Banner 999999 ·
  Skip-Link 1000001 (immer oben).

## 5. Komponenten-Standards

| Komponente | Klasse(n) | Regeln |
|---|---|---|
| Teaser-Karte | `.post-entry` | Hover-Lift −2…−5px + Ebenen-2-Schatten, reduced-motion → aus |
| Hero-Section | `.first-entry.home-info`, `.ff-home-ctas`, `.ff-btn-*`, `.ff-trust-row`, `.ff-trust-pill` | Gradient-Mesh, 8.2:1 Kontrast, weiche Schatten |
| Pinterest-CTA | `.ff-pinterest-cta`, `.ff-pinterest-cta-btn` | Modernes Bento-Card-Layout mit Pinterest-Rot (#E60023) |
| Pillar-Cluster | `.ff-pc-cluster/-head/-title/-count`, `.ff-pc-grid`, `.ff-pc-card/__body/__title/__desc/__cta` | Light+Dark definiert (zzz-agency-polish.css §7) |
| Ratgeber-Zentrale | `.ff-pillar-hero`, `.ff-pillar-grid`, `.ff-pillar-card`, `.ff-spar-matrix-section`, `.ff-method-grid`, `.ff-faq-list` | Volles Agentur-Layout (/pillar/) mit Dark-Mode-Unterstützung |
| Vertrauens-Box | `.ff-trust-box`, `.ff-trust-box__avatar-wrap`, `.ff-trust-box__img`, `.ff-trust-box__badge` | E-E-A-T-Autorbox am Artikelende mit Verifizierungs-Badge |
| Praxis-Marker | `.ff-experience-box`, `.ff-experience-box__tag`, `.ff-experience-box__text` | Bernstein-Akzent, persönlicher Testbericht-Marker |
| Ratgeber-Link | `.ff-pillar-box`, `.ff-pillar-box__inner`, `.ff-pillar-box__btn` | Vernetzt Artikel bidirektional mit übergeordnetem Ratgeber |
| Verwandte Artikel | `.ff-related-section`, `.ff-related-grid`, `.ff-related-card` | 3er-Grid mit Cover-Bilder, Kategorie-Pill & Datumszeile |
| Callout-Boxen | `.ff-callout`, `.ff-callout--tip`, `.ff-callout--warning`, `.ff-callout--info` | Semantische Hinweisboxen für Markdown-Artikel |
| 404-Fehlerseite | `.ff-404-page`, `.ff-404-badge`, `.ff-404-actions`, `.ff-404-pills` | Großes Gradient-Badge, Themen-Schnellzugriff & Startseiten-CTA |
| Chips | `.ff-pc-chip` | Pill, Smaragd-Soft hell / 12% Smaragd-Bright dunkel |
| Kopier-Button | `.ff-heading-copy` | Optik 28px, Trefferfläche 44px via `::after inset:-8px` (hit-test-verifiziert) |
| Vorlese-Toolbar | `.ff-voice-slot` | Slot reserviert Höhe (kein CLS), WCAG 2.2 AA+ Zustände |
| Consent-Banner | `#ff-consent-banner`, `.ff-consent-banner__*` | fixe Leiste, Dark-Mode-fähig, Links inline-block ≥ 24px |
| Skip-Link | `.skip-link` | 3px-Fokusring Signalgelb, z 1000001 |

## 6. Interaktion & Motion

- Übergänge: 0.16s (Micro) / 0.3s (Flächen), cubic-bezier(.2,.7,.2,1) /
  ease-out. Kein bounce/elastic, keine Layout-Properties (einzig dokumentierte
  Ausnahme: Voice-Progress-Balken width .18s linear – kontinuierliche
  Wertanzeige).
- `@media (prefers-reduced-motion: reduce)`: alle Lifts/Transitionen aus
  (custom.css + zzz-agency-polish.css §8).
- Fokus: `:focus-visible` mit 3px solid #FFB300 – sichtbar in beiden Modi
  (verifiziert). Nicht per outline:none entfernen.

## 7. Do's & Don'ts

**Do**
- Kontraste messen (design-metrics), nicht schätzen
- Dark-Variante mitliefern (`:root[data-theme="dark"]`)
- Tap-Ziele ≥ 24px AA / 44px via Pseudo-Fläche
- Bilder immer width/height (CLS-Gate)
- Neue Flächen aus der Radius-/Schatten-Skala, neue Farben aus den Tokens

**Don't**
- Gelb als Textfarbe auf hellen Flächen
- Neue Webfonts im Body / externe CDNs
- 0-Offset-Halo-Schatten als Deko
- Layout-Properties animieren (width/height/top/left/margin)
- Inline-Styles mit Farben in Templates (Beispiel-Refactoring:
  pillar/single.html → .ff-pc-*-Klassen)

## 8. Verifikation

```bash
npm run test:e2e            # Build + komplette Playwright-Suite (25 Tests)
node e2e/design-metrics.mjs # JSON: Kontraste/Typo/Rhythmus/Tap/Fokus, hell+dunkel
node e2e/design-shots.mjs   # Screenshots Desktop+Mobile für Reviews
```

CI: `.github/workflows/e2e.yml` (PRs + dienstags 07:00 MESZ), Report als
Artifact.

## 9. Varianten-Governance (seit 26.09.2026)

Dieses Design-System wird **nicht** durch Varianten ersetzt – es wird
durch sie erprobt. Eine KI darf Layoutvarianten entwerfen und Messdaten
auswerten; austauschen darf sie nichts. Der Rahmen dafür ist die
Design-Varianten-Werkbank.

**Die Regeln dieser Datei sind dort maschinenlesbar gespiegelt:**
`data/design/regelwerk.yaml` enthält die Token-Listen aus §1, die
Radius-/Schatten-/Easing-Skalen aus §4/§6, die Kontrast- und
Tap-Schwellen aus §1/§5 sowie die Verbote aus §7 als geprüfte Muster.
Ändert sich hier eine Farbe, gehört sie dort hinein – sonst weist das
Gate sie als „nicht in den Marken-Tokens" zurück.

| Was | Wo |
|---|---|
| Varianten-Stylesheet | `assets/css/varianten/<id>.css` (**nicht** in `extended/` – das wird immer ausgeliefert) |
| Register mit Hypothese & Freigabe | `data/design/varianten.yaml` |
| Schalter | `HUGO_PARAMS_DESIGNVARIANTE=<id>` → `layouts/_partials/design_variante.html` |
| Bewertung | `python3 scripts/design_variant_gate.py` |

**Harte Zusagen (getestet in `scripts/tests/test_design_varianten.py`):**

- Ohne Parameter erzeugt der Produktionsbau **kein Byte** aus
  `assets/css/varianten/` – geprüft von `e2e/design-variante.spec.mjs`.
- Eine Variante geht nur live mit **menschlicher Unterschrift** plus
  **drei** vorliegenden Messebenen (statisch, gerendert, Lighthouse).
- Was schon die Basis reißt, wird der Variante **nicht** angelastet
  (Bestandsbefunde sind P3 auf `basis`).
- Varianten-CSS ohne `!important`: Es liegt ohnehin nach der Basis im
  `<head>` und bleibt so durch Weglassen rückabwickelbar.

Runbook mit dem vollständigen Ablauf:
[`docs/ANLEITUNG-DESIGN-VARIANTEN.md`](docs/ANLEITUNG-DESIGN-VARIANTEN.md)
