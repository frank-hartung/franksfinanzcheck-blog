# DESIGN.md – Design-System von FranksFinanzcheck

> Technische Design-System-Dokumentation. Wird von KI-Agenten (Impeccable,
> frontend-design, taste-skill) gemeinsam mit PRODUCT.md vor jeder UI-Arbeit
> gelesen; der Review des fertigen Codes läuft über die hauseigene Prüfliste
> `.claude/skills/ff-oberflaeche/references/web-richtlinien.md` (seit 01.11.2026
> statt des Fremd-Skills `web-design-guidelines`, dessen Herkunft ungeklärt war).
> Stand: 12.09.2026 (Design-Skills-Rollout), Kopf nachgezogen 01.11.2026. Generiert aus dem echten CSS-Bestand
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
| Pillar-Cluster | `.ff-pc-cluster/-head/-title/-count`, `.ff-pc-grid`, `.ff-pc-card/__body/__title/__desc/__cta` | Light+Dark definiert (zzz-agency-polish.css §10; nachgeliefert 28.09.2026 – Kopf-Meta/Brotkrumen/Badge, Karten-Raster & Chips komplett) |
| Ratgeber-Zentrale | `.ff-pillar-hero`, `.ff-pillar-grid`, `.ff-pillar-card`, `.ff-spar-matrix-section`, `.ff-faq-list` | Volles Agentur-Layout (/pillar/) mit Dark-Mode-Unterstützung |
| Fixkosten-Kompass | `.ff-kompass`, `__head`, `__steps`, `__step`, `__cta` | Der wiedererkennbare 4K-Prüfpfad (Kosten sehen, Konditionen rechnen, Kündigungsfenster sichern, Kurs halten); Datenquelle `data/fixkosten_kompass.yaml`, Startseite + /pillar/ + /cockpit/ |
| Fixkosten-Cockpit | `.ff-cockpit`, `__row`, `__result`, `__totals`, `__plan` | Lokales, formularbasiertes Tool auf `/cockpit/`; Light/Dark, 44px Controls, sichtbarer Fokus, keine Übertragung der Eingaben; Speicherung nur per Opt-in im Browser |
| Tabellen (überall) | `.ff-table-scroll`, `.ff-tbl`, `.ff-tbl-corner/-num/-nowrap/-a-*` | Basis-Schicht OHNE `.post-content`-Bindung (zzz-agency-polish.css §11, nachgeliefert 30.09.2026): Zellpolster 12/14 px, Sticky-Kopf Smaragd/Weiß, Zebra, Zeilentrenner, Scroll-Container mit Fokusring |
| Spar-Matrix | `.ff-spar-matrix-scroll`, `.ff-spar-matrix-table`, `.ff-spar-matrix-caption`, `.ff-spar-matrix-thema/-aktion`, `.ff-highlight-cell`, `.ff-table-btn` | Fünf Spalten mit `<colgroup>`-Maß; **unter 760 px stapelt jede Zeile zu einer Karte** (Feldnamen aus `data-label`, kein zweites Markup). Wache: `scripts/tabellen_lesbarkeit_guard.py` |
| Vertrauens-Box | `.ff-trust-box`, `.ff-trust-box__avatar-wrap`, `.ff-trust-box__img`, `.ff-trust-box__badge` | E-E-A-T-Autorbox am Artikelende mit Verifizierungs-Badge |
| Praxis-Marker | `.ff-experience-box`, `.ff-experience-box__tag`, `.ff-experience-box__text` | Bernstein-Akzent, persönlicher Testbericht-Marker |
| Ratgeber-Link | `.ff-pillar-box`, `.ff-pillar-box__inner`, `.ff-pillar-box__btn` | Vernetzt Artikel bidirektional mit übergeordnetem Ratgeber |
| Verwandte Artikel | `.ff-related-section`, `.ff-related-grid`, `.ff-related-card` | 3er-Grid mit Cover-Bilder, Kategorie-Pill & Datumszeile |
| Callout-Boxen | `.ff-callout`, `.ff-callout--tip`, `.ff-callout--warning`, `.ff-callout--info` | Semantische Hinweisboxen für Markdown-Artikel |
| Antwort-Box („Kurz & knapp – die Antwort“) | `.ff-kurzantwort`, `__head`, `__medallion`, `__icon`, `__eyebrow`, `__text` | Antwort-Karte oben im Artikel (Light+Dark+Print); Signet-Medaillon mit themenbezogener CSS-Animation je `pillar` (Klassen `.ff-kz-*`; reduced-motion → ruhig) |
| 404-Fehlerseite | `.ff-404-page`, `.ff-404-badge`, `.ff-404-actions`, `.ff-404-pills` | Großes Gradient-Badge, Themen-Schnellzugriff & Startseiten-CTA |
| Chips | `.ff-pc-chip` | Pill, Smaragd-Soft hell / 12% Smaragd-Bright dunkel |
| Kopier-Button | `.ff-heading-copy` | Optik 28px, Trefferfläche 44px via `::after inset:-8px` (hit-test-verifiziert) |
| Vorlese-Toolbar | `.ff-voice-slot` | Slot reserviert Höhe (kein CLS), WCAG 2.2 AA+ Zustände |
| Consent-Banner | `#ff-consent-banner`, `.ff-consent-banner__*` | fixe Leiste, Dark-Mode-fähig, Links inline-block ≥ 24px |
| Skip-Link | `.skip-link` | 3px-Fokusring Signalgelb, z 1000001 |

## 6. Interaktion & Motion

### 6.1 Die Skala (erweitert 01.11.2026, gemessen statt geschätzt)

Bis 31.10.2026 nannte dieser Abschnitt zwei Dauern (0,16 s / 0,3 s). Die
Messung vom 01.11.2026 (`scripts/bewegungs_wache.py`, Vorgang
`BEWEGUNG-AUDIT-HIGHEND-2026-11-01.md`) fand im ausgelieferten CSS zehn
verschiedene Werte. Das war kein Zufall, sondern eine Skala, die nie
aufgeschrieben wurde: Jede Stufe hat eine Aufgabe, und die Zuordnung war über
19 Dateien hinweg konsistent. Sie steht jetzt hier – und nur hier; das
maschinenlesbare Spiegelbild ist `data/design/regelwerk.yaml`, geprüft von der
Bewegungs-Wache (B1/B2) **und** vom Varianten-Gate.

| Stufe | Dauer | Wofür | Belegt in |
|---|---|---|---|
| Sofort | 0,10 s | Rückmeldung auf einer Textzeile (Link in einer Liste) – kürzer als ein Blinzeln, damit Klicken nicht bremst | `.terms-index a` |
| Sofort+ | 0,12 s | Zwei Flächen, die im Verbund umschalten (Wortmarke + Lautstärkebalken im Vorleser); 0,16 s wirkte dort träge | `.ff-voice-w--now` |
| Micro | 0,15 s | Chip, Pille, kleiner Button: Farb- und Rahmenwechsel unter dem Finger | `.ff-pillar-nav__chip`, `.ff-table-btn`, `.ff-teilen__aktion`, `.ff-beleg__link` |
| Micro+ | 0,16 s | Standard-Innenwechsel (Fläche, Text, Klammer) – die Haus-Stufe | `zz-newsletter.css`, `zz-werkzeuge.css` |
| Takt | 0,18 s | Lift, der als Bewegung gelesen wird (Karte, CTA, Kachel) – hier lohnt die Haus-Kurve | `.ff-btn`, `.ff-saison-card`, `.ff-kompass__cta` |
| Zustand | 0,20 s | Ein Zustand schaltet sichtbar um (Badge live, Kopfleiste verdichtet) | `.header`, `.ff-kurzantwort__badge` |
| Panel | 0,22 s | Overlay/Panel öffnet und schließt; länger als Micro, weil eine Fläche kommt und geht | `.ff-ki-panel`, `.ff-home-ctas a` |
| Aufklappen | 0,25 s | Inhalt wird aufgeschlagen (Pfeil, Kurzantwort im Vorlesemodus) | `.ff-offenlegung__pfeil`, `.ff-kurzantwort` |
| Aufdecken | 0,28 s | Ein Element taucht beim Scrollen auf | `.post-entry` (Reveal), `.ff-mini-toc` |
| Fläche | 0,30 s | Größerer Flächenwechsel; alles darüber wirkt zäh | (Bestand) |
| Bildfläche | 0,40 s | Zoom/Hover auf einem Bild – Bildbewegung darf ruhiger sein als UI | `.ff-related-card__img`, `.ff-pc-card__img` |
| Reveal | 0,65 s | Einmalige Enthüllung beim Scrollen (kein Hover, kein Klick) | `.ff-in-view`, `.ff-home-ctas a::after` |
| Bildruhe | 0,70 s | Cover-Zoom im Teaser: langsam, damit das Auge nicht springt | `.post-entry .entry-cover img` |

**Warum das keine Beliebigkeit ist:** 0,10/0,15/0,16 (Text und kleine
Kontrolle) liegen unter der Schwelle, ab der eine Bewegung als Bewegung
wahrgenommen wird – sie sollen nur den Übergang verstecken. Ab 0,18 s wird
Bewegung *gemeint*; dort greift die Haus-Kurve
`cubic-bezier(.2,.7,.2,1)`. Über 0,4 s steht nur noch, was einmalig oder
Bild ist.

**Easing:** `cubic-bezier(.2,.7,.2,1)` für alles, was sich bewegt (Lift,
Panel, Reveal), `ease-out` für Farb-/Rahmenwechsel, `linear` ausschließlich
für kontinuierliche Wertanzeige. Der generische Wert `ease` ist **kein
Verstoß**, aber ein Hinweis: Er trifft die Absicht selten (67 Stellen,
B2 im Audit).

**Layout-Properties:** keine (width/height/top/left/margin/padding).
Dokumentierte Ausnahmen, jede mit Grund:
1. **Voice-Progress** – `.ff-voice-progress { width … linear }`: Die Breite
   *ist* der Wert; ein `scaleX` würde die Rundung an den Enden verzerren.
2. **Kurzantwort-Progress** – `.ff-kurzantwort__progress`: gleiche Bauart,
   gleicher Grund.
3. **Werkzeug-Rangbalken** – `.ff-wz__balken-fuellung { width .3s }`: Der
   Balken wird beim Aufbau *einmal* gesetzt (nicht pro Frame). Das ist kein
   Dauer-Reflow, sondern ein einzelner Layout-Schritt; `transform: scaleX`
   wäre hier gleichwertig, aber der Balken hat einen `border-radius: 999px`,
   den `scaleX` ungleichmäßig staucht.

### 6.2 Pflicht bei Bewegung

- `@media (prefers-reduced-motion: reduce)`: alle Lifts/Transitionen aus
  (custom.css + zzz-agency-polish.css §8).
- **Lift braucht Druck:** Wer bei `:hover`/`:focus-visible` einen
  `transform`-Lift setzt, setzt für dieselbe Fläche ein `:active`
  (`transform: scale(.97)` oder `translateY(0)`). Heute fehlt das an 38
  Flächen – B5 im Audit, Heilung dort geplant.
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

## 10. Figma-/Relume-Handoff

Figma und Relume sind Entwurfswerkzeuge, keine zweite Produktionswahrheit.
Der versionierte Vertrag liegt in `data/design/handoff.yaml`; daraus erzeugt
`scripts/design_handoff.py` reproduzierbar:

- Tokens-Studio-JSON mit Light-/Dark-Collections,
- Relume-Projektprompt, Sitemap und Section-Vertrag,
- Figma↔Hugo-Komponenten-Inventar mit Zuständen und A11y-Abnahme,
- SHA-256-Manifest für Quellen und Exporte.

Die Farben und Radien werden gegen `data/design/regelwerk.yaml` validiert.
Generierte Dateien unter `design/handoff/` werden nicht von Hand bearbeitet;
`python3 scripts/design_handoff.py --check` stoppt Drift im CI-Gate. Ein
externer Entwurf gelangt ausschließlich als registrierte Variante durch
Playwright, Lighthouse, Messprotokoll und menschliche Freigabe in Produktion.

Runbook:
[`docs/ANLEITUNG-FIGMA-RELUME-HANDOFF.md`](docs/ANLEITUNG-FIGMA-RELUME-HANDOFF.md)

## 11. Kanonische Markenobjekte (seit 03.10.2026)

Die Produktionsbasis trägt die Markenidee selbst; eine Hero-Variante ist nicht
mehr aktiv (`designVariante = ""`). Neue Kampagnen dürfen diese Ebene nicht mit
einer parallelen Bildsprache überschreiben.

### FF Kostenprofil

Das **Kostenprofil** ist das wiedererkennbare FranksFinanzcheck-Objekt über
Startseite und Ratgeber hinweg. Es visualisiert immer denselben 4K-Prüfpfad:

1. Kosten sehen
2. Konditionen rechnen
3. Frist sichern
4. Kurs halten

Vertrag: `layouts/_partials/kostenprofil.html`, Gestaltung in Abschnitt 18 von
`zzz-agency-polish.css`, DOM-Marker `[data-ff-kostenprofil]`. Das Objekt darf
**keine errechneten Scores vortäuschen**. Artikel unterscheiden sich über das
redaktionelle Prüffeld (Energie, Internet, Versicherung, Konto, Reise oder
Budget), nie über willkürliche Prozentwerte. Auf der Startseite verbindet es
den Prüfpfad mit dem echten Autorenfoto und der Herausgeberseite.

### FF Datenblatt

Individuelle Diagramme tragen die Kennung `FF—DATENBLATT`, eine cremefarbene
Papierfläche, die dunkle Kopfregel und Smaragd als Datenfarbe. Die zugängliche
SVG-Grafik, Datentabelle, Quelle, Stand und Methodik bleiben Pflicht. Vertrag:
`layouts/shortcodes/chart.html` und `assets/css/extended/zz-visual-data.css`;
die markentypische Art Direction liegt ebenfalls in Abschnitt 18 der
kanonischen Agenturdatei.

### Oberflächenregeln

- Dunkles Redaktionsgrün, Papiercreme und Signalgelb bilden die feste Trias.
- Eckige Drucksachen-Kanten sind den Markenobjekten vorbehalten; normale
  Produktkarten verwenden weiter die dokumentierte Radius-Skala.
- Echte Personenbilder werden nicht durch KI-Porträts ersetzt. Das kanonische
  Autorenbild ist `static/images/frank-hartung.jpg`.
- Website, Newsletter, Pinterest und Social übernehmen Kennung, Farbreihenfolge
  und 4K-Achse; zusätzliche Cover-Varianten schaffen keine neue Designsprache.
- Ein neues Visual-Format wird nur ergänzt, wenn es Information transportiert,
  nicht um eine weitere dekorative Variante zu erzeugen.
