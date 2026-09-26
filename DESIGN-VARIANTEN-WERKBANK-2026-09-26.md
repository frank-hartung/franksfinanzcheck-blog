# 🎛️ Design-Varianten-Werkbank – Einbau-Bericht

**Datum:** 26.09.2026 · **Auftrag:** Figma/Relume + KI-Coding-Agent +
Lighthouse/Playwright so einbauen, dass eine KI Layoutvarianten erzeugt und
Daten auswertet, **ohne** eigenmächtig das Blogdesign auszutauschen –
Brand Guidelines, Accessibility, SEO, Performance und Conversion-Ziele
vorgegeben, finale Freigabe beim Menschen.
**Runbook:** [`docs/ANLEITUNG-DESIGN-VARIANTEN.md`](docs/ANLEITUNG-DESIGN-VARIANTEN.md)

---

## 1. Was jetzt da ist

Eine Werkbank, die den Auftrag in drei technisch getrennte Rollen zerlegt:

| Rolle | Wer darf das | Umsetzung |
|---|---|---|
| **Vorschlagen** | Maschine | `scripts/design_reach_briefing.py` – Agent-Reach-Signale (web.dev, Chrome Developers, Smashing, NN/g, GitHub) werden einem kuratierten Hypothesen-Raster zugeordnet und als Varianten-Skizze vorgelegt. Schreibt **kein** CSS. |
| **Bauen & Messen** | Maschine | `scripts/design_variant_lab.py` (Tier A: HTML/DOM/SEO/Conversion/Bytes) und `e2e/variant-metrics.mjs` (Tier B: Playwright-Kontraste/Tap/Fokus/CLS/LCP + Lighthouse-Scores/TBT). |
| **Bewerten** | Maschine | `scripts/design_variant_gate.py` – prüft gegen `data/design/regelwerk.yaml`: Marke, Barrierefreiheit, SEO, Performance, Conversion, Freigabe-Kontrakt. |
| **Entscheiden** | **Nur Mensch** | Unterschrift in `data/design/varianten.yaml`. Drei Wächter setzen das technisch durch (siehe §3). |

Die Kette in einem Befehl je Schritt:

```bash
npm run design:briefing        # Signale → Hypothesen (Vorschlag)
npm run design:lauf <id>       # Basis + Variante bauen, Tier A messen
npm run design:messen <id>     # Tier B: Browser + Lighthouse
npm run design:gate            # Bewertung gegen das Regelwerk
#   … Mensch unterschreibt im Register …
npm run design:wache           # Produktionswache (läuft im Deploy)
```

---

## 2. Die Regeln sind jetzt Zahlen, keine Absicht

`data/design/regelwerk.yaml` spiegelt DESIGN.md maschinenlesbar:

* **Marke** – 15 erlaubte Hex-Tokens, Radius-Skala `[0, 8, 12, 16, 999]`,
  Easing- und Dauer-Skala, erlaubte `rgba()`-Basen, sieben benannte Verbote
  (`@font-face`, externe URLs, `outline: none`, `!important`,
  Layout-Animation, Gelb als Textfarbe) und zwei Pflichten (Dark-Mode-Block,
  `prefers-reduced-motion`).
* **Barrierefreiheit** – Kontrast ≥ 4.5 / 3.0, Tap ≥ 24 px (Soll 44),
  sichtbarer Fokusring, Lighthouse-A11y ≥ 0.95.
* **SEO** – genau ein `<h1>`, Canonical-Pflicht, Pflicht-Schema, interne
  Links ≥ 95 % der Basis, null Bilder ohne `width`/`height`, Lighthouse-SEO = 1.0.
* **Performance** – DOM-Budgets identisch zu `scripts/dom_audit.py`
  (keine zweite Wahrheit), LCP ≤ 2500 ms, CLS ≤ 0.1, TBT ≤ 200 ms,
  CSS-Zuwachs ≤ 6 KB gegenüber der Basis.
* **Conversion** – kein CTA darf verschwinden, **jedes**
  `data-umami-event` bleibt erhalten, Affiliate-`rel` intakt,
  Pflicht-Bausteine vorhanden, Primär-CTA über dem Falz (390 × 844).

Damit keine Regel zur Attrappe wird: Das Gate kennt jeden Schlüssel
namentlich und **meldet unbekannte Schlüssel als Fehler**. Eine Regel, die
niemand prüft, ist keine Regel.

---

## 3. Die drei Wächter gegen den eigenmächtigen Designwechsel

1. **Der Schalter existiert nur als Parameter.**
   `layouts/_partials/design_variante.html` lädt ein Varianten-Stylesheet
   ausschließlich bei gesetztem `designVariante`. Ohne Parameter erzeugt der
   Build **kein Byte** – nachgewiesen: Basis-Bau enthält 0 Treffer für
   `data-ff-variante`. Varianten-CSS liegt bewusst in
   `assets/css/varianten/` und **nicht** in `assets/css/extended/`, weil
   Letzteres per `resources.Match` bei jedem Build komplett ausgeliefert wird.

2. **Die Produktionswache läuft vor dem Build.**
   Neuer Schritt in `.github/workflows/deploy.yml` (nach den
   Py-Abhängigkeiten): `design_variant_gate.py --produktionswache`.
   Sie verweigert eine Variante ohne Freigabe, eine unbekannte ID und jede
   Abweichung zwischen `hugo.toml` und Register. Fail-closed.

3. **Der Freigabe-Kontrakt ist prüfbar.**
   Status `freigegeben`/`live` verlangt: `mensch: true`, Name aus
   `freigabe.berechtigte`, gültiges Datum (nicht in der Zukunft, nicht älter
   als 30 Tage) **und** drei vorliegende Messebenen (statisch, gerendert,
   lighthouse). Fehlt eine, ist die Freigabe ungültig.

**Gegenprobe gefahren** (regelwidrige Testvariante, danach zurückgesetzt):
**22 Befunde, davon 8 × P1** – fehlende Unterschrift, unbekannter
Unterzeichner, Zukunftsdatum, drei fehlende Messungen, Produktionswache;
dazu Fremdfarbe, Webfont, externe URL, `!important`, `outline: none`,
Layout-Animation, Gelb als Textfarbe, fehlender Dark-Mode-Block.
Ergebnis: **DURCHGEFALLEN**, Exit 1 → Deploy gestoppt.

---

## 4. Nachweise aus dem echten Lauf

Beispielvariante `v-hero-conversion` (Hero: eine Primärhandlung statt drei
gleichlauter CTAs, Status **entwurf**, bewusst nicht freigegeben):

| Kennzahl | Basis | Variante | Δ |
|---|---:|---:|---:|
| Seiten gebaut | 221 | 221 | — |
| DOM-Elemente (max) | 1034 | 1035 | +1 |
| Head-Kinder (max) | 49 | 50 | +1 |
| Inline-CSS Startseite | 129 881 B | 131 173 B | +1 292 B |
| Seitengewicht (max) | 212 774 B | 214 152 B | +1 378 B |
| CTAs / ohne Umami-Event | 3 / 0 | 3 / 0 | — |
| Affiliate-Links ohne `rel` | 0 | 0 | — |

Bauzeit beider Varianten zusammen inkl. Messung: **6,7 s**.

**Tier B nachgeholt** (26.09.2026, über den Repo-Fallback
`@sparticuz/chromium`, weil `cdn.playwright.dev` gesperrt ist):

| Kennzahl | Basis | Variante | Budget |
|---|---:|---:|---:|
| Kontrast (Minimum, hell + dunkel) | 7,53 | 7,53 | ≥ 4,5 ✅ |
| Kleinstes Tap-Ziel | 26,4 px | 26,4 px | ≥ 24 px ✅ |
| CLS | 0 | 0 | ≤ 0,1 ✅ |
| Lighthouse Performance (mobil) | 0,99 | 0,99 | ≥ 0,90 ✅ |
| Lighthouse Accessibility | 0,96 | 0,96 | ≥ 0,95 ✅ |
| Lighthouse SEO | 1,00 | 1,00 | = 1,00 ✅ |
| Lighthouse Best Practices | 0,96 | 0,96 | ≥ 0,95 ✅ |
| Total Blocking Time | 39 ms | 63 ms | ≤ 200 ms ✅ |
| Lighthouse LCP (mobil, nach Korrektur) | 1760 ms | 1809 ms | ≤ 2500 ms ✅ |
| Lighthouse LCP (desktop) | 573 ms | 558 ms | ≤ 2500 ms ✅ |

Damit sind für beide Seiten alle drei Messebenen vollständig – die
Variante ist **freigabefähig**, aber weiterhin `entwurf` und
**nicht unterschrieben**. Das ist der vorgesehene Zustand: Die Maschine
hat geliefert, die Entscheidung steht aus.

**Testabdeckung:** 35 neue Regressionstests
(`scripts/tests/test_design_varianten.py`), 4 neue Playwright-Specs
(`e2e/design-variante.spec.mjs`), drei `--selftest`-Suiten.
Die bestehende Suite bleibt grün: **910 Tests, OK (17 übersprungen)**.

---

## 5. Was dabei gefunden wurde

Vier echte Funde, alle behoben oder sauber zugeordnet:

1. **`site.Data` hätte den Varianten-Build getötet.**
   Erste Fassung las das Register über `site.Data`. Hugo parst dann den
   ganzen `data/`-Baum und stirbt an den `*.jsonl`-Protokollen in
   `data/audit/`. Symptom: Build läuft 300 s bei 0 % CPU. Behoben über
   `design_varianten_data.html` (`os.ReadFile` + `transform.Unmarshal`) –
   dasselbe Muster wie `saisons_data.html`. Die Landmine ist damit zum
   dritten Mal im Repo dokumentiert.

2. **`partial` statt `partialCached` kostete 90 s Bauzeit.**
   Der Registerabgleich lief auf jeder der 221 Seiten. Jetzt 1,35 s.

3. **Das Gate hätte einen Bestandszustand der Variante angelastet.**
   Die Basis reißt bereits das DOM-Kinder-Budget (58 > Frühwarnung 54,
   Lighthouse-Grenze 60 eingehalten). Ohne Basis-Vergleich hätte jede
   Variante diesen Befund geerbt – die Fehlalarm-Klasse aus
   [Vorfall #343](docs/INCIDENT-2026-09-21-layout-ai-fehlalarm-343.md).
   Behoben: Budgets werden gegen die Basis gerechnet, Bestandsbefunde
   laufen als **P3 auf `basis`** und blockieren nichts.

4. **Das Briefing belegte eine A11y-Hypothese mit einem Token-Repository.**
   Substring-Treffer: „aria" in „Design-Tokens-CSS-Vari**ables**".
   Behoben durch Wortgrenzen; Testfall festgehalten. Falsche Belege sind
   schlimmer als keine – sie sehen aus wie Evidenz.

5. **Playwright-LCP und Lighthouse-LCP sind nicht dieselbe Zahl.**
   Playwright misst ungedrosselt auf localhost (184 ms), Lighthouse mit
   simulierter Drosselung (3110 ms) – für dieselbe Seite. Beide gegen die
   Google-Schwelle von 2500 ms zu prüfen, hätte garantiertes Falsch-Grün
   erzeugt. Die Schwelle gilt jetzt nur für Lighthouse; der
   Playwright-Wert bleibt als Basis/Variante-Delta im Report.

6. **Ein gerissenes Basis-Budget wäre unsichtbar geblieben.**
   Die Variante wird für Bestandszustände nicht angeklagt (Fund 3) – aber
   `pruefe_bestand()` sah nur die statische Ebene. Der LCP-Befund der
   Basis hätte damit *niemanden* erreicht. Jetzt laufen alle drei Ebenen
   plus die Lighthouse-Kategorien durch die Bestandsprüfung.

**Zwei Bestandsbefunde – inzwischen behoben.**
Vollständige Ursachenanalyse, Belege und Nachmessung:
[`BESTANDSBEFUNDE-2026-09-26.md`](BESTANDSBEFUNDE-2026-09-26.md)

* **DOM-Kinder 58 → 49.** Die 58 Kinder waren 58 leere
  `div.ff-content-chunk`-Hüllen. Die flache Teilung an H2 *und* H3 hatte
  „ein Chunk mit vielen Kindern" gegen „viele Chunks" getauscht – die Zahl
  der Chunks war selbst die neue Obergrenze. Jetzt zweistufig
  (`ff-content-section` je H2, `ff-content-chunk` je H2/H3-Block), beide
  Ebenen `display: contents`. Pixelgleichheit belegt: 4832 verglichene
  Element-Geometrien, 0 Abweichungen > 1 px.
* **Lighthouse-LCP mobil 3179 → 1760 ms** (Performance 0,93 → 0,99).
  Ursache war weder die Seite noch die Sandbox: `e2e/server.mjs` lieferte
  Text unkomprimiert aus, GitHub Pages liefert gzip/brotli (190 KB statt
  31 KB). Auf simuliertem Mobilfunk waren das ~0,7 s Phantom-Ladezeit.
  Nebenbei aufgedeckt: Die Lighthouse-Node-API ignoriert
  `settings: { preset: 'desktop' }` stillschweigend – gemessen wurde mobil,
  während `lighthouserc.cjs` desktop deklarierte. Beides behoben, beide
  Profile werden jetzt gemessen und schreiben ihre Bedingungen mit.

## 6. Was noch zu tun ist

| Was | Warum | Wie |
|---|---|---|
| **Chromium + Lighthouse in CI** | Tier B ist Freigabe-Pflicht und läuft nur mit Browser | Im Workflow verdrahtet; lokal über den Repo-Fallback verifiziert (`npm i --no-save @sparticuz/chromium lighthouse` – beide in EINEM Befehl) |
| **Inline-CSS nach Seitentyp trennen** | ~94 KiB der 129 KB sind auf der Startseite ungenutzt (Artikel-CSS) | Sitzt in `layouts/_partials/head.html` – **KRITISCH-versiegelt**, also menschliche Entscheidung mit Neusignatur. Nach der Kompressionskorrektur kein Druck (LCP mobil 1760 ms bei Budget 2500 ms) |
| **Erste echte Freigabe** | `v-hero-conversion` ist Entwurf und soll es bleiben, bis gemessen wurde | `npm run design:lauf v-hero-conversion` → `npm run design:messen …` → Zahlen lesen → unterschreiben oder verwerfen |
| **Umami-Auswertung nach 14 Tagen** | Das Labor sagt „darf ausgeliefert werden", nicht „ist besser" | `cta_click` je `slug` vergleichen; Abbruch, wenn die CTA-Summe sinkt |
| **Figma/Relume-Anbindung** | Entwürfe kommen heute als Text-Hypothese herein | Feld `herkunft` im Register nimmt die Quelle auf; ein Figma-Export ändert am Ablauf nichts – er ersetzt nur Schritt 2 |

---

## 7. Geänderte und neue Dateien

**Neu**

```
data/design/regelwerk.yaml            Die Regeln (Marke/A11y/SEO/Perf/Conversion/Freigabe)
data/design/varianten.yaml            Das Register (Basis + v-hero-conversion)
data/design/briefings/README.md       Ablage der Agent-Reach-Briefings
data/agent_reach/design_themenplan.yaml  Design-Quellen + Hypothesen-Raster
assets/css/varianten/README.md        Warum nicht in extended/
assets/css/varianten/v-hero-conversion.css
layouts/_partials/design_variante.html       Der Schalter (fail-closed)
layouts/_partials/design_varianten_data.html Register lesen ohne site.Data
scripts/design_variant_gate.py        Gate + Produktionswache + LHCI-Export
scripts/design_variant_lab.py         Werkbank (bauen, Tier A, Vergleich)
scripts/design_reach_briefing.py      Agent-Reach → Hypothesen
scripts/tests/test_design_varianten.py  35 Regressionstests
e2e/variant-metrics.mjs               Tier B (Playwright + Lighthouse)
e2e/design-variante.spec.mjs          4 Produktions-Sicherungen
lighthouserc.cjs                      LHCI-Konfiguration
lighthouse/assertions.json            ERZEUGT aus dem Regelwerk
docs/ANLEITUNG-DESIGN-VARIANTEN.md    Runbook
.github/workflows/design-varianten.yml
```

**Geändert**

```
.github/workflows/deploy.yml   + Produktionswache vor dem Build
layouts/_partials/extend_head.html  + partialCached-Aufruf (letzter Head-Block)
e2e/server.mjs                 + E2E_ROOT (Varianten-Builds ausliefern)
package.json                   + 8 npm-Skripte (design:*, test:design)
DESIGN.md                      + §9 Varianten-Governance
CLAUDE.md                      + Varianten-Pflicht bei Layout-Umbauten
```

Lauf-Artefakte (`DESIGN-VARIANTEN-REPORT.md`, `.cache/design-varianten/`)
sind über die bestehenden `.gitignore`-Regeln ausgeschlossen.
