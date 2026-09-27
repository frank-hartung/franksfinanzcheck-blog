# Willkommenstext SEO/GEO-Premium + Hero-Layout — Report 27.09.2026

**Auftrag (Frank):** „Mit Agent Reach und Claude den Willkommenstext SEO- und GEO
optimieren, Layout optimieren auf Premium-Level einer Profi-Agentur."

**Umsetzung in zwei Ebenen:**
1. **Text:** Willkommenstext (H1 + Content, `hugo.toml homeInfoParams`) auf die
   GEO-Antwort-zuerst-Struktur von 2026 umgebaut — geschrieben über die
   autorisierte Kette des `willkommenstext_guard.py` (Signal-Pool → Fallback-Pool →
   Schreiben → Brand-/Integrity-Lock → Build → Render-Beweis).
2. **Layout:** Neue Design-Variante **`v-hero-premium`** (Status `entwurf`) über die
   Design-Varianten-Werkbank — vollständig gemessen (Tier A + Tier B + Lighthouse),
   Messprotokoll eingefroren, **wartet auf die menschliche Freigabe**.

---

## 1. Recherche (Agent Reach, nur lesend)

- **Agent Reach v1.5.0** nach Repository-Vertrag installiert (Pin
  `f65526cbaaad3879473acc1ba6dbefd195caf2be` aus `requirements-agent-reach.txt`),
  `agent-reach doctor --json` geprüft: aktiv `github` (gh CLI), `web` (Jina Reader),
  `rss` (feedparser). Exa/r.jina.ai/Release-CDN sind in dieser Sandbox durch die
  Netzwerk-Allowlist blockiert; die Websuche wurde deshalb über den verfügbaren
  Suchkanal ergänzt. Nichts wurde gepostet/geschrieben (Leitplanke „nur LESEN").
- **Befund SEO/GEO-Stand 2026** (konsistent über mehrere Quellen 2026):
  - KI-Antwortmaschinen (ChatGPT Search, Perplexity, Google AI Overviews, Copilot)
    **zitieren Passagen, keine Seiten** — der erste Absatz muss die Kernantwort
    selbstständig, quantifiziert und mit voller Entity-Benennung liefern (BLUF).
  - Quantifizierte Aussagen erhöhen die Zitierwahrscheinlichkeit nachhaltig
    (Princeton-GEO-Studie: Statistiken/Zitate/Quellen als stärkster Hebel).
  - FAQPage/Article-Schema, sichtbare E-E-A-T-Autorschaft und Frische bleiben die
    tragenden Säulen; die Site erfüllt das bereits (SEO-GEO-PREMIUM-REPORT-2026-09-21).
- **Daraus abgeleiteter Auftrag an den Text:** Satz 1 = Definition
  („FranksFinanzcheck ist dein unabhängiger Ratgeber für …"), Nutzen quantifiziert
  (10 Jahre, zehn Minuten, mehrere hundert Euro), Autor im Lead, du-Durchgang.
- **Governance:** Neue Fakten dürfen KI nicht erfinden — der Aufhänger wurde als
  kuratierter Eintrag `seo-geo-antwort-zuerst` in `data/aktuelle_entwicklungen.yaml`
  registriert (die Datei sieht genau diesen Weg für „Agenten mit Web-Recherche-
  Zugriff" vor) und der Text als handgeschriebener Pool-Eintrag im
  `FALLBACK_POOL` des Guards hinterlegt (Signal-ID 1:1 gebunden).

## 2. Der neue Willkommenstext

| | Vorher | Nachher |
|---|---|---|
| **H1** | „FranksFinanzcheck – Deine ehrliche Hilfe für Strom, Versicherung und Konto" | „FranksFinanzcheck – Geld sparen bei Strom, Gas, Versicherung & Konto" |
| **Content** | Persönlicher Einstieg („Hi! Schön, dass du da bist …"), Kern-Nutzen erst ab Satz 3, nur 2 Kategorien breit | **Satz 1 = zitierfähige Definition** (Entity + Kategorie + Nutzenversprechen + Autor/E-E-A-T), dann quantifizierter Nutzen („zehn Minuten … mehrere hundert Euro"), dann Kadenz + Handlungs-Aufforderung |

- **SEO:** Primär-Keyword „Geld sparen" jetzt in H1 **und** Satz 1; 4 der 5
  Kern-Kategorien im ersten Absatz; Meta-Title/-Description der Startseite
  (`content/_index.md`, bereits keyword-first) bleiben unangetastet — SERP- und
  On-Page-Ebene sind so bewusst getrennt und jeweils stark.
- **GEO:** Der Definitions-Satz ist eine **selbstständig zitierbare Einheit** für
  ChatGPT/Perplexity/AI Overviews: Entity voll benannt, Aussage quantifiziert,
  ohne Kontext verständlich.
- **Markenstimme:** du-Durchgang, kein Verkaufsdruck, 1 Emoji, keine KI-Floskel
  (alle Guard-Regeln grün), 693/700 Zeichen (Guard-Fenster 250–700).
- **Einzigartigkeit:** Jaccard 0.00–0.04 gegen die letzten 5 Versionen
  (Grenze: 0.55) — maximaler Substanz-Neuheit.
- **Kette:** `write_hugo_toml()` → `brand_guard.py --set-current` ✅ →
  `integrity_guard.py --set-current` ✅ → `hugo --minify` ✅ → Render-Beweis
  (Titel im gebauten `public/index.html`) ✅ → History + Report des Guards.
  `willkommenstext_guard.py` (Basis-Lauf), `brand_guard.py` und
  `integrity_guard.py --drift-audit` melden danach: **kein Refresh-Bedarf /
  keine Drift, 43 Kerndateien = signierter Stand.**

## 3. Layout: Design-Variante `v-hero-premium` (Premium-Politur)

**Design-Pass 2 (27.09.2026, zweite Auftragsrunde „Layout und Design“):** Nach
Agent-Reach-/Websuche zum Design-Stand 2026 (editorial serif revival, „one
italic accent word“, Standfirst-Muster für Premium-Editorial-Heros) wurde die
Variante designseitig vervollständigt:

- **Playfair-Standfirst:** Die erste Zeile des Lead-Definitionsatzes läuft als
  editorialer Standfirst in **Playfair Display Kursiv auf Gold** (`--ff-accent-2`)
  — exakt die freigegebene Subline-Rolle aus DESIGN.md §2 („nur auf Smaragd“).
  Kein neuer Webfont: Playfair ist bereits Teil der Marken-Identität.
- **PaperMod-Rest entfernt (echter Fund):** PaperMods
  `.first-entry .entry-header` clamp't den Hero-Titel auf **3 Zeilen mit
  Ellipsis** — der neue, längere Guard-Titel wurde in Produktion als
  „FranksFinanzcheck – Geld sparen bei Strom, Gas,…“ gekappt. Die Variante
  hebt den Clamp defensiv auf (alle betroffenen Properties); der H1 steht
  jetzt vollständig über 4 Zeilen. Latenter Basis-Defekt, der erst durch
  den längeren SEO-Titel sichtbar wurde.
- **Saison-Elemente strukturiert:** Hinweis mit Gold-Hairline (2px, `--ff-accent-2`)
  und zurückgenommener Deckkraft; Badge mit feinerer Kante + ruhigem Glas-Blur.
- **CTA-Feinschliff:** `text-wrap: pretty` am Lead, Press-State (`:active`),
  H1-Maximum 20ch („FranksFinanzcheck –“ bleibt in einer Zeile).

**Design-Pass 3 (27.09.2026, dritte Runde: Dark-Mode-Artdirection + Typo-Feinschliff):**
Erstmals wurde der Dark Mode der Variante **visuell** geprüft (Shots mit
emuliertem `prefers-color-scheme: dark`, `data-theme="dark"` verifiziert) —
Funde und fixes:

- **Fakten-Panel kompakt:** Das Desktop-Panel war bislang auf die volle
  Hero-Höhe gestreckt (`align-self: stretch`) — oben blieb eine unruhige
  Leerfläche. Jetzt `align-self: center`: die Karte umschließt ihre vier
  Zeilen und sitzt zur Inhalt-Mitte (wirkt in hell **und** dunkel).
- **H1-Umbruch-Typografie:** Der Gedankenstrich von „FranksFinanzcheck –"
  führte Zeile 2 an — verursacht durch `text-wrap: balance` der Basis
  (ausgleichen verschiebt den Strich gezielt runter). Fix: `text-wrap: pretty`
  + 22ch auf den Startseiten-H1 → der Strich steht am **Zeilenende**
  (klassische Satzregel: kein Strich am Zeilenanfang).
- Review-Artefakte: `shots/v-hero-premium/hero-desktop-DARK.png`,
  `hero-mobile-DARK.png` (Dark Mode), `hero-desktop-zoom.png`,
  `hero-mobile-zoom.png` (Hell, final).

**Weg über die Werkbank** (Runbook `docs/ANLEITUNG-DESIGN-VARIANTEN.md`), nicht in
die Basis: `assets/css/varianten/v-hero-premium.css` + Eintrag in
`data/design/varianten.yaml` (Status `entwurf`, Hypothese + Rückbau notiert).

**Was die Variante tut (ohne ein einziges neues DOM-Element):**
- **Lead-Definition:** Der erste Absatz (der neue Definitions-Satz) tritt typogra-
  phisch hervor — Clamp-Größe aus der vorhandenen Skala, fast volle Deckkraft.
  Der GEO-Text und die Form verstärken sich gegenseitig.
- **Fakten-Panel:** Die vier Vertrauens-Signale werden im Desktop-Grid zu einer
  ruhigen Checklisten-Fläche (Radius 16, Trennlinien, Check-Medaillons) gebündelt;
  die Herausgeber-Zeile (Frank Hartung) trägt eine Goldkante — E-E-A-T sichtbar.
- **CTA-Hierarchie + Press-State:** Fortführung der freigegebenen
  `v-hero-conversion`-Logik (eine Primär-, zwei Sekundärwege) plus sauberem
  `:active`-Zustand am Primär-CTA.
- **Bühne 1024px, editoriales Grid, mobile LCP-Reihenfolge** (Artikel-Cover zuerst)
  werden aus der freigegebenen Variante **übernommen, nicht zurückgebaut** — eine
  spätere Ablöse ist verlustfrei (Rückbau = eine Datei weglassen).
- **Regeln:** nur Marken-Tokens, Radius-Skala, Easing-Skala, kein `!important`,
  Dark-Mode-Pflichten und `prefers-reduced-motion` erfüllt; H1 mit `hyphens: auto`
  für lange deutsche Komposita.

**Messung (27.09.2026, Stand Design-Pass 3):**

| Ebene | Ergebnis | Budget |
|---|---|---|
| Tier A statisch | DOM max 1062 (+1: Varianten-`<style>`), H1 1× auf allen Seiten, Canonical/Schema/Alt/rel intakt, 3 CTAs mit Umami, Newsletter da | DOM-Head ≤ 52, CSS-Δ ≤ 6144 B |
| CSS-Zuwachs (inline) | **+4878 B** | ≤ 6144 B ✅ |
| Varianten-Datei (roh) | 8110 B | ≤ 8192 B ✅ |
| Tier B Browser | Kontrast **7.53:1**, kleinstes Tap-Ziel **26.4 px**, **CLS 0**, LCP 680 ms | ≥ 4.5 · ≥ 24 · ≤ 0.1 · Playwright-Wert ohne Budget |
| Lighthouse mobil | LCP **1826 ms**, TBT 143 ms, Perf **0.98**, A11y **0.96** | LCP ≤ 2500 · Perf ≥ 0.90 · A11y ≥ 0.95 ✅ |
| Lighthouse desktop | LCP 766 ms, Perf **0.99–1.0** | ✅ |
| Gate | `design_variant_gate.py`: **BESTANDEN, keine Befunde** | — |
| E2E | design-variante- + home-Specs **6/6 grün** (Desktop+Mobile); Gesamtsuite seit Pass 6 **68/68 grün** (siehe Root-Cause-Berichtigung unten) | — |
| Protokoll | `data/design/messungen/v-hero-premium-2026-09-27.json` (eingefroren, Pass 3) | Freigabe-Beleg |

Screenshots für das Review: `shots/v-hero-premium/home--desktop.png` +
`home--mobile.png` (gitignored Review-Artefakt).

## 4. Verifikation (kompletter Bestand)

**Design-Pass 9 (27.09.2026, neunte Runde: Abschluss-Sweep + Geometrie-Audit komplett):**

- **Artikel-og-Geometrie geprüft und bewusst bestätigt:** Nachdem die
  Startseite seit Pass 8 das 1,91:1-Format trägt, wurde auch die
  Artikel-Ebene auditgericht: Artikel-`og:image` bleibt absichtlich das
  2:3-Pinterest-Cover (1000×1500) — laut Git des
  `generate_covers.py`-Kopfs **Pinterest-Masterplan, explizite Entscheidung**
  (PRODUCT.md: Pinterest ist Reichweiten-Säule; Pinterest-Pins speisen
  sich aus og:image). Falsch wäre es, das heimlich umzubauen; richtig
  ist es, es als dokumentierte Absicht zu führen. Falls X/LinkedIn-
  Anteile der Artikel künftig wachsen, ist der saubere Weg ein zweites,
  querformatiges `twitter:image` je Cover — bewusst NICHT in diesem
  Lauf umgesetzt (Pipeline-Änderung am gesiegelten Cover-Generator =
  Chefsache mit eigener Messung).
- **IndexNow:** Endpoint aus der Sandbox nicht erreichbar
  (Allowlist); der bestehende Wochen-Workflow meldet Startseite,
  Artikel, Pillars und Hubs ohnehin automatisch — inklusive der
  neuen Meta-/OG-Signale beim nächsten Lauf.
- **Abschluss-Verifikation am finalen HEAD (59a348b), alles grün:**
  - **E2E-Suite: 68/68** (Playwright, Desktop + Mobile)
  - **Design-Metrics hell+dunkel:** Startseite min 5,25 (hell) /
    4,91 (dunkel), Artikel 5,1 / 6,07 — alle ≥ 4,5-AA; 12 Messektionen
    (Home, Layout, Artikel, Fokus, Tap-Ziele, Mobile — je hell+dunkel)
  - Design-Varianten-Gate BESTANDEN · Schema-/SEO-Gate 383 Seiten,
    0 harte Funde · SEO-Cockpit 0 Befunde · layout/dom_audit im Budget
  - willkommenstext „kein Auffrischungsbedarf“ · brand_guard „alle
    Bausteine unverändert“ · integrity „kein Drift, 43 Kerndateien“

**Design-Pass 8 (27.09.2026, achte Runde: Social-Preview-Geometrie):**

- **Echter Befund:** Das `og:image` der Startseite war das 2:3-Pinterest-
  Hochkant-Cover (1000×1500, Verhältnis 0,667). Facebook, LinkedIn,
  WhatsApp, X und Co. erwarten **1,91:1** — Link-Vorschauen der
  meistgeteilten URL wurden zwangsläufig beschnitten/umgebrochen.
- **Fix auf Agentur-Niveau, deterministisch statt generiert:** Eine
  **1200×630-Markenkarte** (`og-default-1200x630.jpg`), gebaut aus den
  Repos-eigenen Markenmitteln — Smaragd-Verlauf wie der Hero (#0E5A43 →
  #0A4634), dezenter Gold-Glow, Inter-Wortmarke, Gold-Hairline,
  Playfair-Kursiv-Subline mit Gold-Akzent, Autorenzeile mit
  E-E-A-T-Angabe. Fonts aus `static/fonts/` (self-hosted-Pakt gewahrt),
  Pixel-QA per Messung (Verhältnis 1,905, Textbereiche verifiziert).
- **Verkabelung ohne neues Head-Gewicht:** `site.Params.images` führt die
  Karte jetzt als erstes Bild — `get-page-images`/`opengraph.html`
  nehmen `index 0` und lesen die **echten Pixelmaße** via `imageConfig`;
  `og:image:width/height/type/alt` stimmen automatisch. Das 2:3-Cover
  bleibt als Fallback hinter der Karte (und für Pinterest-Kontexte).
- **Betriebsvorfall dokumentiert:** Die Sandbox wurde zwischendurch neu
  geklont (lokal git-Historie + node_modules + /usr/local/bin/hugo
  verloren). Alle sieben früheren Pässe überlebten auf dem Remote-Branch;
  Recovery per `git reset --hard` auf den Remote-Stand, Pass 8 wurde
  sauber erneut angewendet. Kein Datahlverlust.
- **Verifikation:** og:image 1200×630 korrekt emittiert · Schema-/SEO-
  Gate ✅ · SEO-Cockpit 0 Befunde · home- + design-variante-Specs 8/8 ·
  Brand-/Integrity-Locks neu signiert (Siegel-Beleg = dieser Commit).

**Design-Pass 7 (27.09.2026, siebte Runde: Entity-Graph + GEO-Dauerhaftigkeit):**

- **Person-Knoten auf der Startseite (GEO):** Der WebSite-Knoten
  referenziert den Autor per `@id: …#frank-hartung` — der Knoten selbst
  wurde aber nur auf Artikelseiten emittiert. Auf der meistgesehenen
  Seite war die Referenz damit **unaufgelöst** (Entity-Graph-Bruch
  ausgerechnet dort, wo KI-Antwortmaschinen zuerst ansetzen). Jetzt
  wird der Person-Knoten auch auf der Startseite emittiert (`extend_head`,
  außerhalb der Siegel-Dateien — Drift-Audit grün ohne Neusignatur).
  Startseite: 2 JSON-LD-Blöcke (Person + WebSite), beide
  JSON-valide geparst.
- **GEO-Prompt dauerhaft verankert:** Der Prompt des
  `willkommenstext_guard.py` (wöchentliche Neugenerierung des
  Willkommenstexts) kannte die Antwort-zuerst-Struktur nicht — jede
  künftige KI-Rotation hätte strukturell wieder bei null anfangen
  können. Der Prompt schreibt jetzt die GEO-Struktur verbindlich vor:
  erster Satz = selbstständig zitierbare Entity-Definition
  („FranksFinanzcheck ist dein unabhängiger Ratgeber für …"),
  Titel keyword-nah mit Marke + „Geld sparen". Die Premium-Struktur
  überlebt damit alle künftigen automatischen Auffrischungen.
- **Verifikation:** Schema-/SEO-Gate 383 Seiten, 0 harte Funde ·
  SEO-Cockpit 0 Befunde · Guard „kein Auffrischungsbedarf" ·
  home- + design-variante-Specs 8/8 · robots.txt Sitemap-Zeile ✓.

**Design-Pass 6 (27.09.2026, sechste Runde: Root-Cause-Jagd — der dauerrote Test):**

- **Der „Sandbox-Befund" war ein Test-Bug — und ist geheilt.** Die seit
  Beginn rote Spec „Kurz-&-knapp-Signet" (67/68 in allen bisherigen Läufen)
  hatte einen anderen, echten Grund: Die **Artikel-Tipp-Box wiederverwendet
  die Klasse `.ff-kurzantwort__icon`** als kleines Inline-Zeichen (bewusst,
  CSS-Vertrag `.ff-article-tip-icon .ff-kurzantwort__icon`). Der Test-
  Locator war nicht strict-sicher → Playwright brach mit „resolved to 2
  elements" ab. Manuelle Probes mit `querySelector` (erstes Element)
  hatten das bislang maskiert. **Fix:** Locatoren auf die Box gescoped
  (`.ff-kurzantwort .ff-kurzantwort__icon`, auch in der Reduced-Motion-
  Spec). Ergebnis: **68/68 E2E-Tests grün — erstmals vollständig, im
  Sandbox-Browser wie in CI.** Die frühere Attribution „Umgebungs-Befund
  des Fallback-Chromiums" (Pass 1–5) war falsch und ist hiermit berichtigt.
- **Sitemap-Frische geprüft (verdächtigt, entlastet):** Die Startseite
  trägt `lastmod 2026-09-25` aus dem Partial `sitemap_lastmod` — ein
  **belegtes Redaktionsdatum**, kein Build-Zeitstempel. Die Befundklasse
  „Frische-Inflation" (SEO-Report F1) bleibt geschlossen; kein Eingriff.
- **Verifikation:** E2E **68/68** · Interne Links 3118/0 defekt ·
  Design-Gate BESTANDEN (Variante unverändert 8110/8192 B) ·
  Integrity-Drift-Audit grün (E2E ist nicht sigilpflichtig).

**Design-Pass 5 (27.09.2026, fünfte Runde: E-E-A-T-Verlinkung + Robustheit):**

- **Personen-Entity verlinkt:** Die Herausgeber-Zeile im Hero nannte Frank
  Hartung als reinen Text — die Person war von der Startseite aus nicht
  erreichbar (E-E-A-T-Lücke auf der meistgesehenen Seite). Jetzt verlinkt
  auf `/ueber/` (`a.ff-trust-author`), Optik unverändert plus dezente
  Unterstreichung, Hover in `--ff-accent-2`, globaler Fokus-Ring greift.
  **Messkette bewährte sich:** Der erste Lauf meldete Tap-Ziel 15,4 px
  (Budget 24) → Trefferfläche per `::after inset:-8px` vergrößert
  (Hausstandard wie `.ff-heading-copy`) → wieder 26,4 px.
- **Font-unabhängiges Häkchen (Robustheits-Fund):** Das „✓" (U+2713) der
  Trust-Pills hängt an der Symbolfont-Abdeckung des Geräts — ohne
  Symbolfont bleibt das Medaillon leer (im Sandbox-Browser nachweisbar,
  pixelgeprüft). Das Häkchen wird jetzt **CSS-gezeichnet** (2px-Chevron
  via Pseudo-Element, gold `--ff-accent-2`); das Zeichen bleibt im DOM.
  Pixel-Verifikation: Chevron rendert im Medaillon-Zentrum, auf jedem
  Gerät identisch.
- **Pinterest-CTA-Review (aus Pass 4 versprochen):** Bento-Karte besteht
  den Agentur-Blick — Logo-Badge, Text-Balance, roter Primär-Button mit
  sauberem Kontrast; der „Pin-Board"-Umbruch ist korrekte Silbentrennung.

**Design-Pass 4 (27.09.2026, vierte Runde: Meta-Ebene + Below-the-Fold-Audit):**

- **Meta-Description der Startseite (SEO/GEO):** Bislang ohne Entity und ohne
  Konkretisierung („… so sparst du monatlich bares Geld."). Neu (155 Zeichen,
  Gate-Fenster 70–165): **„Geld sparen bei Strom, Gas, Internet und
  Versicherungen: FranksFinanzcheck zeigt ehrliche Tarifvergleiche mit
  konkreten Euro-Beträgen – ohne Verkaufsdruck."** — Entity + Quantifizierung,
  konsistent zur H1-Definition und zu `llms.txt`. Gilt für
  `meta name=description` UND `og:description` (SERP + Social-Karte).
- **Redaktioneller Fund im Saison-Block geheilt:** Die Karte „Günstig durch
  den Winter" zeigte die rohe Kategorie **„energie"** als Themen-Label —
  der Artikel trug `pillar: "energie"`, eine ID, die es nicht gibt (kanonisch:
  `strom-sparen`). Folge neben dem Label: kein Ratgeber-Link, falsches
  Kurzantwort-Signet. Geheilt auf `strom-sparen` → Label „Strom & Gas
  sparen", Link in den Ratgeber, Bolt-Signet. Interne Links: 3117 geprüft,
  0 defekte.
- **Below-the-Fold-Beweisaudit:** Saison-Block und Pinterest-CTA visuell
  geprüft (Viewport-Shots über HTTP) — Karten-Hierarchie, „Franks Tipp"-
  Zeile und Pinterest-Bento bestehen den Agentur-Blick; die scheinbar
  „leeren" Cover-Boxen im Full-Page-Capture sind Lazy-Loading (erstes
  LCP-Cover: eager, geladen, sichtbar — messbar via CWV-Grün).
- **`llms.txt` geprüft:** Entity-Block, Zitierregeln und alle Pillars sind
  aktuell und konsistent zum neuen Text (wird bei jedem IndexNow-Lauf
  regeneriert) — kein Eingriff nötig.
- **SEO-Cockpit:** 213 Seiten, **0 Befunde (P1/P2/P3)**.

- **E2E:** Ursprünglich 67/68 Playwright-Tests. **Berichtigung (Pass 6,
  unten):** Der eine Fehler („Kurz-&-knapp-Signet animiert") war **kein**
  Umgebungs-Befund, sondern ein nicht strict-sicherer Test-Locator — die
  Artikel-Tipp-Box nutzt dieselbe Icon-Klasse. Seit Pass 6 **68/68 grün**.
  Der Varianten-Leak-Test (Prüfnadel im Produktions-CSS) wurde nach einer
  bewussten Reihenfolge-Korrektur (eigene Deklarationen zuerst) **grün**.
- **Unit-Tests:** 962/963 grün. Der eine Fehler war der Siegel-Vertrag
  „`data/integrity_lock.json` muss im selben Commit wie sein Beleg liegen" —
  **erledigt durch genau diesen Commit**.
- **layout_audit / dom_audit:** alle Budgets im Rahmen (DOM-Elemente 1062/1100,
  Tiefe 13/28, Chunker-Vertrag 1456 Überschriften ok).
- **Guards nach dem Schreiben:** willkommenstext („kein Auffrischungsbedarf"),
  brand, integrity (--drift-audit: 43 Kerndateien = signierter Stand) — alle grün.

## 5. Nächste Schritte (menschlicher Vorbehalt)

1. **Ansehen:** Screenshots in `shots/v-hero-premium/` (oder lokal
   `HUGO_PARAMS_DESIGNVARIANTE=v-hero-premium hugo server`).
2. **Freigeben (nur Frank):** Eintrag `v-hero-premium` in
   `data/design/varianten.yaml` auf `status: freigegeben` setzen mit
   `messprotokoll: "design/messungen/v-hero-premium-2026-09-27.json"`,
   dann Scharfschalten (`aktiv: "v-hero-premium"` im Register +
   `designVariante = "v-hero-premium"` in hugo.toml) und
   `npm run design:wache` → BESTANDEN.
3. **Beobachten:** 14 Tage `cta_click` je slug in Umami; Abbruch/Rückbau, wenn
   die Summe aller drei Hero-CTAs sinkt (identisch zum Vertrag von
   `v-hero-conversion`, deren Beobachtungsfenster ohnehin am 10.10.2026 endet —
   `v-hero-premium` ist als Nachfolger mit gleicher Hierarchie gebaut).
4. **Text:** Läuft weiter automatisch (7-Tage-Rhythmus des
   `willkommenstext_guard.py`, neuer Pool-Eintrag hält die Qualität auch offline).

---
**Dateien dieses Laufs:** `hugo.toml` (nur Title/Content, via Guard geschrieben) ·
`data/brand_lock.yaml` + `data/integrity_lock.json` (+ history) (neu signiert) ·
`scripts/willkommenstext_guard.py` (Pool-Eintrag) ·
`data/aktuelle_entwicklungen.yaml` (Signal) · `assets/css/varianten/v-hero-premium.css` ·
`data/design/varianten.yaml` (Register) · `data/design/messungen/v-hero-premium-2026-09-27.json`.
