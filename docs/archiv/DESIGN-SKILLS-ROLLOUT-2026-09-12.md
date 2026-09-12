# DESIGN-SKILLS-ROLLOUT – 12.09.2026 (Premium-Integration)

> **Auftrag:** Impeccable, Guidelines (web-design-guidelines), Awesome Design
> (frontend-design), Taste Skill (design-taste-frontend) und Playwright auf
> Premium-Niveau einer Profi-Agentur integrieren – inkl. Design-Audit und
> Design-Politur.
> **Status:** ✅ Umgesetzt, verifiziert, 25/25 E2E-Tests grün.

---

## 1. Was installiert/eingerichtet wurde

### 1.1 Agent-Skills (`.claude/skills/`, via `npx skills add --copy`)

| Skill | Quelle | Zweck |
|---|---|---|
| `impeccable` v4.3.1 | pbakaus/impeccable | Design-Disziplin: polish/critique/audit/layout/typeset…, Craft-Floor mit harten Bans |
| `web-design-guidelines` | vercel-labs/agent-skills | UI-Review gegen Web Interface Guidelines |
| `frontend-design` | anthropics/skills („Awesome Design") | Eigenständige visuelle Identität statt AI-Slop-Defaults |
| `design-taste-frontend` | Leonxlnx/taste-skill | Anti-Slop-Regeln (Typo, Dichte, Varianz) |
| `webapp-testing` | anthropics/skills | Playwright-Wissen für Agenten (Server-Lifecycle, waits, Selektoren) |

Pinning/Updates über `skills-lock.json` (`npx skills update`).
Kontext-Dateien neu angelegt: **PRODUCT.md** (Produkt/Marke/Gates) und
**DESIGN.md** (Design-System, aus dem echten CSS generiert) – beide liest
Impeccable vor jeder Design-Arbeit. **CLAUDE.md** verdrahtet Agenten,
Skills, Tests und Konventionen.

### 1.2 Playwright-Komplett-Setup (Root)

| Datei | Rolle |
|---|---|
| `package.json` / `package-lock.json` | `@playwright/test` 1.63, Scripts (`test:e2e`, `test:e2e:report` …) |
| `playwright.config.mjs` | 2 Projekte (Desktop + iPhone-14-Emulation), Service-Worker blockiert (Determinismus), Traces bei Fehlern |
| `e2e/server.mjs` | zero-dependency Static-Server für `public/` (404 + Statuscode korrekt, `/healthz`) |
| `e2e/fixtures.mjs` | Hermetik: Produktions-URLs (`https://franksfinanzcheck.de/**`) werden auf den lokalen Server geroutet – Tests laufen NIE gegen Live |
| `e2e/browser.mjs` | Chromium-Resolver: Standard-Playwright-Download; Fallback `@sparticuz/chromium` für CDN-blockierte Umgebungen |
| `e2e/helpers.mjs` | Fehler-Sammler (pageerror vs. Drittanbieter-Console), smooth-scroll-resistentes Durchscrollen, Bild-Settle-Warten |
| `e2e/home.spec.mjs` | Startseite: Struktur, H1, Teaser, Impressum/Datenschutz, 0 JS-Fehler, 0 defekte Same-Origin-Requests, Bilder geladen+alt |
| `e2e/article.spec.mjs` | Neuester Artikel (dynamisch ermittelt): H1/Meta/Breadcrumbs, Description/Canonical/OG/Twitter, JSON-LD (Article+BreadcrumbList), Bilder (alt+width/height=CLS), Voice-Toolbar-A11y |
| `e2e/navigation.spec.mjs` | Header/Footer-Links 200, /posts/, Pillar, Pagination, 404-Status + -Seite |
| `e2e/affiliate-guard.spec.mjs` | **E2E-Affiliate-Wache:** /go/-Links → sponsored+nofollow+noopener+_blank+subid; Redirect-Stümpfe 200+noindex; Tabnabbing-Schutz |
| `e2e/seo-a11y.spec.mjs` | Eindeutige Titel, 1×H1, lang=de, Landmarks, Skip-Link, robots/sitemap/manifest/favicon, RSS |
| `e2e/mobile.spec.mjs` | iPhone 14: kein Overflow (Home+Artikel), Header nutzbar, Tap-Ziele ≥ 40px |
| `e2e/design-metrics.mjs` | **Messbarer Design-Audit** (neu): Kontraste (WCAG, hell+dunkel), Typo-Skala, Messweite ch, Heading-Rhythmus, Fokus-Sichtbarkeit, Tap-Ziele mit echtem Hit-Test |
| `e2e/design-shots.mjs` | Screenshot-Runner (Desktop+Mobile) als Playwright-Ablösung von `_design_shots.js` |
| `.github/workflows/e2e.yml` | CI: PRs auf main (pfadgefiltert) + dienstags 07:00 MESZ; HTML-Report + Metriken als Artifact |

Dependabot um npm (`/`) erweitert; `.gitignore` um `shots/`,
`test-results/`, `playwright-report/` ergänzt.

**Gefundene und behobene Fußangeln (dokumentiert, damit sie niemand
wieder durchlaufen muss):**
1. `devices['iPhone 14']` trägt `defaultBrowserType: 'webkit'` – ohne
   explizites `browserName: 'chromium'` startet der Runner den WebKit-Treiber
   gegen den Chromium-Binary (still hängend). Fix in playwright.config.mjs.
2. `route.continue()` erlaubt keinen Protokollwechsel (https→http) –
   Hermetik-Fixture nutzt `route.fetch()` + `route.fulfill()`.
3. `scroll-behavior: smooth` (z-premium-blog.css) macht jede synchrone
   Scroll-Logik unzuverlässig (lazy images, elementFromPoint) – Helper
   schaltet temporär auf `auto`, Hit-Tests auf `behavior:'instant'`.
4. CDN-blockierte Umgebungen: `npx playwright install` fällt – Resolver
   mit @sparticuz/chromium-Fallback (inkl. manuelles Entpacken der
   AL2023-Kompat-Libs bei Bedarf).

## 2. Design-Audit (messbar, gegen die Skill-Standards)

Maßstäbe: Impeccable craft-floor (Kontrast, Tiefe, Abstände, Typo, Motion,
Browser-Flächen), frontend-design-Anti-Tells, taste-skill-Typo-/Layout-
Disziplin, Web Interface Guidelines. **Gemessen, nicht geschätzt** –
`e2e/design-metrics.mjs` berechnet WCAG-Kontraste im gerenderten Zustand
hell+dunkel und prüft Tap-Ziele per echtem Hit-Test.

### 2.1 Was bereits Agentur-Niveau hatte (Bestätigt)

| Prüfung | Messwert | Urteil |
|---|---|---|
| Fließtext-Kontrast hell / dunkel | 16:1 / 9.6:1 | ✓ |
| Links | 7.5:1 | ✓ |
| Messweite | **65ch** (Soll 65–75) | ✓ |
| Typo-Skala H1→H2→H3 | 56→24→16.8px, Inter 700 | ✓ |
| Heading-Rhythmus | h3: 44px über / 16px unter | ✓ |
| Fokus-Sichtbarkeit | 3px solid #FFB300, beide Modi | ✓ |
| Übergangs-Disziplin | nur 0.16s/0.3s, cubic-bezier, keine bounce/elastic | ✓ |
| reduced-motion | 5 Blöcke + Lifts deaktiviert | ✓ |
| tabular-nums | 25 Verwendungen | ✓ |
| text-wrap: balance | 6 Verwendungen | ✓ |

### 2.2 Befunde und Behobenes (Vorher → Nachher)

| # | Befund | Vorher | Nachher | Fix |
|---|---|---|---|---|
| A1 | **Dark Mode: H1–H3 Smaragd #0E5A43 auf #1D1E20** (defaultTheme:auto → betrifft jeden dunklen OS-Nutzer!) | **2.04:1** ✗ | **9.28:1** ✓ | `--ff-emerald-bright: #7FD1B4` via `:root[data-theme="dark"]` (zzz-agency-polish.css §2) |
| A2 | Home-Info-Links Signalgelb auf Smaragd-Verlauf | 4.49:1 (Grenzfall) | **5.8:1** ✓ | `--ff-accent-2` #FFD15A (§3) |
| A3 | Kopier-Buttons an Überschriften 28×28px | <44px | **44px Trefferfläche** ✓ | `::after inset:-8px` (§4) – per elementFromPoint verifiziert (19 Buttons) |
| A4 | Tap-Ziele < 24px (WCAG 2.5.8 AA): Consent-Link 22px, Footer 21px, TOC 21px, Trust-Box 18px | **12 AA-Verstöße** | **0** ✓ | inline-block+Padding (§4), Klasse `.ff-consent-reopen` in extend_footer.html |
| A5 | `::selection` unthematisiert (`--selection` war toter Token) | Browser-Blau | Marken-Signalgelb (hell+dunkel) | §5 |
| A6 | Skip-Link (z 100000) unter Progress-Bar (z 999998) | überdeckt | Skip-Link z 1000001 | §6 |
| A7 | Radius-Ausreißer 18px ×5, Spacing 11px ×1 | außerhalb Skala | 16px / 12px | direkt normalisiert (ff-voice/z-premium/zz-themenwelten), dokumentiert |
| A8 | Pillar-Seiten: Inline-Farben ohne Dark-Varianten | #0E5A43/#555/#666 inline | semantische `.ff-pc-*`-Klassen, Light-Parität 1:1 (vermessen), voller Dark-Support | Template-Refactoring + §7 |

**Bewusst NICHT geändert** (Entscheidungen, keine Versäumnisse – in
PRODUCT.md/DESIGN.md verankert):
- `width`-Transition am Voice-Progress-Balken (kontinuierliche Wertanzeige,
  kein Layout-Thrash – Impeccable-Ban zielt auf Entrance/Hover).
- 31× `!important` (historisch; Abbau = eigenes Refactoring mit Gate-Risiko).
- Weiße Flächen im Consent-Banner auch im Dark Mode (lesbar 16:1, bewusstes
  Signalflächen-Design).
- Meta-Zeile mit Mittel-Punkten (Verlags-Konvention, kein AI-Tell).

## 3. Politur-Layer

`assets/css/extended/zzz-agency-polish.css` – lädt als letztes, jede Regel
mit Audit-Herleitung im Kopf. Enthält: Dark-Kontraste, Home-Info-Link-
Farbe, Tap-Ziel-Erweiterungen, ::selection/caret, Z-Ordnung, die kompletten
`.ff-pc-*`-Pillar-Komponenten (Light+Dark) und reduced-motion-Absicherung.
Template-Änderungen: `layouts/pillar/single.html` (Klassen statt Inline),
`layouts/_partials/extend_footer.html` (eine Klasse).

## 4. Verifikation

- **Playwright: 25/25 grün** nach allen Änderungen (Desktop + Mobile),
  inkl. Affiliate-Guard, SEO, A11y, 404, Mobile-Overflow.
- **Kontrast-Nachmessung:** artikel-dark h2 9.28:1, home-info-Links 5.8:1,
  meta 4.9–6.1:1 – alles ≥ AA.
- **Tap-Ziele:** 0 AA-Verstöße (hell+dunkel), 19 Buttons hit-test-verifiziert
  auf 44px erweitert.
- **Pillar-Parität:** computed styles vor/nach identisch (h1 #0E5A43/36px/800,
  Cluster #F7FBF9, Karte #fff/12px, Chip #EAF4EF) – Dark-Werte neu
  (#7FD1B4, #2E2E33-Flächen).
- Statisches Gate `scripts/layout_audit.py` weiterhin grün.

## 5. Betrieb

```bash
npm run test:e2e              # Build + Suite (lokale Vorbedingung: Hugo Extended)
node e2e/design-metrics.mjs   # Design-Audit als JSON (vor jedem Design-PR)
node e2e/design-shots.mjs     # Screenshots → shots/ (gitignoriert)
npx skills update             # Skills aktuell halten
```

CI läuft automatisch: PRs auf main (pfadgefiltert) + dienstags 07:00 MESZ.
Failures erzeugen einen HTML-Report als Artifact (7 Tage).
