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

**Messung (27.09.2026, Stand Design-Pass 2):**

| Ebene | Ergebnis | Budget |
|---|---|---|
| Tier A statisch | DOM max 1062 (+1: Varianten-`<style>`), H1 1× auf allen Seiten, Canonical/Schema/Alt/rel intakt, 3 CTAs mit Umami, Newsletter da | DOM-Head ≤ 52, CSS-Δ ≤ 6144 B |
| CSS-Zuwachs (inline) | **+4938 B** | ≤ 6144 B ✅ |
| Varianten-Datei (roh) | 8180 B | ≤ 8192 B ✅ |
| Tier B Browser | Kontrast **7.53:1**, kleinstes Tap-Ziel **26.4 px**, **CLS 0**, LCP 688 ms | ≥ 4.5 · ≥ 24 · ≤ 0.1 · Playwright-Wert ohne Budget |
| Lighthouse mobil | LCP **1845 ms**, TBT 137 ms, Perf **0.98**, A11y **0.96** | LCP ≤ 2500 · Perf ≥ 0.90 · A11y ≥ 0.95 ✅ |
| Lighthouse desktop | LCP 768 ms, Perf **1.0** | ✅ |
| Gate | `design_variant_gate.py`: **BESTANDEN, keine Befunde** | — |
| E2E | design-variante-Spec + home-Spec **8/8 grün**; Gesamtsuite 67/68 (1 Bestandsbefund des Sandbox-Fallback-Chromiums, am Basis-Tree belegt) | — |
| Protokoll | `data/design/messungen/v-hero-premium-2026-09-27.json` (eingefroren, Pass 2) | Freigabe-Beleg |

Screenshots für das Review: `shots/v-hero-premium/home--desktop.png` +
`home--mobile.png` (gitignored Review-Artefakt).

## 4. Verifikation (kompletter Bestand)

- **E2E:** 67/68 Playwright-Tests grün (Desktop+Mobile). Der eine Fehler
  („Kurz-&-knapp-Signet animiert") ist ein **Bestandsbefund der Sandbox**: Das
  Fallback-Chromium (`@sparticuz/chromium`, nötig, weil das Playwright-CDN hier
  blockiert ist) liefert die Signet-Animation nicht — **nachweisbar auch am
  unveraenderten Basis-Tree fehlgeschlagen**, in CI mit vollem Chromium grün.
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
