# 🚀 FRANKSFINANZCHECK – MASTER-SYSTEM
### Der komplette Profi-Aufbau für franksfinanzcheck.de
**Stand:** 09.08.2026 · **Status:** Live (Hugo + GitHub Pages + Cloudflare) · **Basis:** 39 Artikel, 6 Pillars, 149 Themen-Pool, 9 Automations-Workflows
**Monetarisierung:** CHECK24-Partnerprogramm (pid=80968&aid=18) + partner-versicherung.de (Tarifcheck) + Tierversicherung

> Dieses Dokument ist die **einzige, vollständige System-Referenz** – Branding, Technik, SEO, Automation, 30 neue Artikel, Monetarisierung, Wartung & Skalierung. Es ersetzt keine bestehende Datei, sondern **bündelt den IST-Stand und schließt die Lücken** (alles, was mit ✅ markiert ist, läuft bereits; alles andere ist neu).

---

# 1. BRANDING & POSITIONIERUNG

## 1.1 Mission, Vision, Werte

| Element | Inhalt |
|---|---|
| **Mission** | Frank macht Finanzentscheidungen so einfach, dass jeder Haushalt in Deutschland jährlich 300–800 € spart – durch klare Anleitungen, echte Tarifvergleiche und ohne Fachchinesisch. |
| **Vision** | Die vertrauenswürdigste deutsche Anlaufstelle für „Geld sparen im Alltag" – gemessen daran, wie viele Leser:innen tatsächlich gewechselt, gespart und vorgesorgt haben (nicht an Klickzahlen). |
| **Werte** | ① **Ehrlichkeit** – Affiliate-Links sind transparent gekennzeichnet, Empfehlungen bleiben unabhängig. ② **Verständlichkeit** – jede Erklärung schafft es in einen 7.-Klasse-Satz. ③ **Sparsamkeit als Haltung** – wir empfehlen nur, was Frank selbst tun würde. ④ **Aktualität** – jeder Artikel trägt ein Prüfdatum (lastmod). ⑤ **Datenschutz** – nur technisch notwendige Cookies (bereits umgesetzt). |

## 1.2 Zielgruppenanalyse – 3 Kern-Avatare

| | **Avatar 1: „Spar-Fuchs Samira"** | **Avatar 2: „Familien-Vater Markus"** | **Avatar 3: „Best-Agerin Ingrid"** |
|---|---|---|---|
| **Alter / Situation** | 27, Single, Berufseinstieg, erste eigene Wohnung, Azubi/Studentin oder Junior | 38, verheiratet, 2 Kinder, Eigenheim oder Mietwohnung, Haushaltseinkommen ~4.500 € | 64, Rentnerin, lebt allein, Eigenheim, festes Budget |
| **Schmerz** | „Am Monatsende ist das Konto leer, ich weiß nicht wohin" | „Strom-, Internet- und Versicherungsrechnungen fressen das Budget, keine Zeit zum Vergleichen" | „Ich traue Online-Vergleichen nicht, habe Angst vor Abzocke und unnötigen Verträgen" |
| **Suchintention** | „budget erstellen vorlage", „nebenjob ideen", „wie viel notgroschen" | „stromanbieter wechseln 2026", „kfz versicherung wechseln", „dsl vergleich" | „privathaftpflicht sinnvoll", „riester lohnt sich", „tagesgeld sicher anlegen" |
| **Unser Angebot** | Fertige Vorlagen + Schritt-für-Schritt-Anleitungen | Vergleichs-Anleitungen mit realistischen Sparpotenzialen („So wechselst du in 20 Minuten") | Beruhigende, unabhängige Erklärungen + „Fallen"-Artikel |
| **CTA-Präferenz** | Checkliste/PDF-Download | Tarifwechsel (CHECK24-Deep-Link) | Telefon/Hilfe-Artikel, Versicherungs-Check |

## 1.3 Unique Value Proposition (UVP)

> **„Finanz-Tipps, die Frank selbst umsetzt – mit echten Zahlen, fertigen Vorlagen und einem Tarifwechsel, der in 20 Minuten klappt."**

Abgrenzung: Kein Finfluencer-Geschrei, kein 0815-Listicle – sondern **eine Person, ein Versprechen, nachvollziehbare Sparbeträge** („Du kannst bis zu 50 € im Monat sparen" – jede Kurzantwort liefert die Zahl gleich mit).

## 1.4 Tonalität & Schreibstil (verbindliche Regeln – bereits in den Generatoren verankert)

| Regel | Vorgabe |
|---|---|
| Anrede | **Du-Form**, persönlich, „Frank" spricht (Ich-Erfahrung, wo passend) |
| Satzbau | Kurze Sätze (max. ~20 Wörter), aktiv, starke Verben, kein Passiv |
| Absätze | 3–4 Sätze, **ein Gedanke pro Absatz**, keine Textwände |
| Verboten | KI-Floskeln („In der heutigen schnelllebigen Welt…", „Zusammenfassend…"), Silbentrennung, Höflichkeitsform („Sie") |
| Zahlen | **Geschütztes Leerzeichen (U+00A0) zwischen Zahl und %/€** – nie umbrechen (seit 5f456ce per Gate abgesichert) |
| Belege | Konkrete Sparbeträge als Spannen („ca. 100–300 €/Jahr"), keine erfundenen Präzisionen |
| Struktur | H1 → Intro (mit Kurz-und-knapp-Antwort) → H2-Abschnitte → FAQ → CTA |

## 1.5 Farbwelt & visuelle Identität

| Element | Wert | Einsatz |
|---|---|---|
| **Primär (Smaragd)** | `#0E5A43` | Überschriften, Buttons, Akzente – „Geld & Wachstum" |
| **Sekundär (Weichgrün)** | `#EAF4EF` / `#F7FBF9` | Hintergründe, Kurz-und-knapp-Box, Pillar-Boxen |
| **Akzent (Warn-Gelb)** | `#F5B800` | Affiliate-CTA-Pills (auch partner-versicherung.de) |
| **Text** | `#222` / Graustufen | Lesefreundlicher Body (Inter) |
| **Schriften** | **Inter** (Fließtext) + **Montserrat** (Headlines) | lokal gehostet, woff2, vorgewärmt (Performance: LCP ~300 ms warm) |
| **Bildsprache** | Echte Fotos von Alltagssituationen (nicht Stock-CGI), Cover 16:9 mit Titel-Overlay, Alt-Texte = Titel | 38 Covers vorhanden, 8 Varianten je Cover |

**Logo-Ideen (sobald Budget/Bock):**
1. **„Frank-Mark"** – stilisiertes „F" als Sparschwein-Umriss in Smaragd (SVG, responsive).
2. **„Sparpfeil"** – aufsteigender Pfeil, der in einen Euro-Haken übergeht (→ „Geld wächst").
3. **Wortmarke** – „franksfinanzcheck" in Montserrat 800, „finanz" in Smaragd, „check" in Gelb (kostengünstigste Variante, sofort umsetzbar als Text-Logo im Header).

---

# 2. TECHNISCHE BLOG-STRUKTUR

## 2.1 Navigationsstruktur (IST, funktionsfähig)

```
FRANKSFINANZCHECK.DE
├── Startseite (Home-Cluster: 6 Pillars + neueste Artikel)
├── Ratgeber (Pillar-Pages = Hauptkategorien)
│   ├── Frugalismus (finanzielle Freiheit)
│   ├── Strom sparen (Energiekosten)
│   ├── Konto & Karten (Banking, Kredit, Depot)
│   ├── Versicherungen (Schutz, aber nicht überversichert)
│   ├── Internet & DSL (Tarife, WLAN, Hardware)
│   └── Mietwagen & Reisen (Urlaub günstig)
├── Affiliate-Disclosure / Datenschutz / Impressum
└── 404-Seite (custom, mit Navigation)
```

## 2.2 Hauptkategorien (6 Pillars) + Unterkategorien (Themen-Cluster)

| # | Pillar (Hauptkategorie) | Unterkategorien / Cluster (4–6 je Pillar) | Artikel heute |
|---|---|---|---|
| 1 | **Frugalismus** | Budget & Haushaltsbuch · Notgroschen & Rücklagen · Spar-Tricks im Alltag · Finanzielle Freiheit & Mindset · Nebenverdienst | 7 |
| 2 | **Strom sparen** | Tarifwechsel & Vergleich · Geräte & Stromfresser · Heizen & Wärme · E-Mobilität zu Hause · Erneuerbare (PV/Balkonkraftwerk) | 7 |
| 3 | **Konto & Karten** | Girokonto & Wechsel · Kreditkarten · Sparen & Tagesgeld · Kredite & Zinsen · Depot & ETF | 6 |
| 4 | **Versicherungen** | Haftpflicht & Unfall · Haus & Eigentum · Gesundheit (Zahn, Reise, Tier) · Kfz · Altersvorsorge (BU, Rente) | 8 |
| 5 | **Internet & DSL** | Tarife & Anbieterwechsel · WLAN & Mesh · DNS & Technik · Router & Hardware · Mobilfunk | 5 |
| 6 | **Mietwagen & Reisen** | Mietwagen buchen · Mietwagen-Fallen · Flüge & Pauschalreisen · Reiseversicherung · Budget-Reisen | 6 |

## 2.3 Interne Linklogik (verbindlich – in `internal_linker.py` automatisiert)

| Regel | Vorgabe |
|---|---|
| **Silo-Prinzip** | Jeder Artikel verlinkt seine **Pillar-Page** (Ratgeber) – Pillar verlinkt zurück auf alle Cluster-Artikel |
| **Anzahl** | 2–5 interne Links pro Artikel (Bot: `--max 5`), **kein** Link-Spam im ersten Absatz |
| **Ankertexte** | Beschreibend & keywordhaltig („so wechselst du den Stromanbieter"), nie „hier klicken" |
| **Semantische Nähe** | Links nur innerhalb des Silos + max. 1 Querverweis in benachbarte Silos |
| **Breadcrumbs / Post-Navigation** | Vorheriger/Nächster Artikel + Pillar-Box am Artikelende (implementiert) |
| **Pillar → Artikel** | Jede Pillar-Seite listet ihre Artikel mit Teasern (implementiert) |

## 2.4 Content-Cluster-Architektur (Silostruktur – SEO-Power)

```
SILO „STROM SPAREN"
   Pillar: /pillar/strom-sparen/  (Hub, interne Links zu allen Artikeln)
   ├── Stromanbieter wechseln 2026 (Kauf-Intent, Affiliate-Deep-Link)
   ├── Stromtarif für Wärmepumpe (Mid-Tail)
   ├── Strom sparen: 20 Tipps (Evergreen, Long-Tail)
   ├── Stromfresser entlarven (Long-Tail)
   ├── E-Auto laden (Long-Tail)
   └── Wärmepumpe vs. Gasheizung (Vergleich, Querverweis-Silo)
```
> **Regel:** Neue Artikel werden IMMER einem der 6 Silos zugeordnet (Frontmatter `pillar:`), nie „freischwebend" veröffentlicht. Themen außerhalb der Silos (z. B. Depot/ETF) hängen am Pillar **Konto & Karten** (dort liegt „Depot 2026" + „ETF-Sparplan").

## 2.5 Technische Basis (IST – alles ✅ verifiziert)

| Baustein | Status |
|---|---|
| Hugo v0.164 (extended), Page-Bundles, `titleCaseStyle = "none"` | ✅ |
| `baseURL = "https://franksfinanzcheck.de/"`, Custom Domain + CNAME, 301 von github.io | ✅ |
| Cloudflare vorgeschaltet (Proxy), Cache-TTL 1 Jahr für Assets, SSL „Full" → „Full (strict)" sobald GitHub-Zertifikat da (Watchdog Check 4 meldet) | ✅/⏳ |
| Sitemap, RSS, Service Worker (SWJS), Canonicals | ✅ |
| Performance: LCP warm ~300 ms, 0 Third-Party, DOM < 500 | ✅ |
| Mobile: Cover über Titel, Reflow-frei (0 forced Layouts) | ✅ |

---

# 3. SEO-MASTERPLAN

## 3.1 Keyword-Strategie (Short-, Mid-, Long-Tail)

| Typ | Beispiele | Einsatz | Ziel |
|---|---|---|---|
| **Short-Tail** (1–2 Wörter, hohe Konkurrenz) | „stromanbieter wechseln", „kreditkarte vergleich" | Nur in Pillar-Hubs + Vergleichsseiten, **nicht** für neue Artikel | Langfristige Autorität, ab Monat 9+ |
| **Mid-Tail** (3–4 Wörter) | „kfz versicherung wechseln wann", „etf sparplan anfänger" | Einzelartikel mit klarer Absicht (je 1 Keyword = Fokus) | Haupt-Traffic-Quelle ab Monat 4–8 |
| **Long-Tail** (5+ Wörter, Fragen) | „wie viel notgroschen brauche ich wirklich", „lohnt sich eine zahnzusatzversicherung" | Täglich neue Artikel, FAQ-Sektion, Kurz-und-knapp-Box | Schnelle Rankings in 2–6 Monaten, Featured Snippets |

> **Grundsatz:** Eine junge Domain (BLOG < 3 Monate) rankt zuerst über **Long-Tail + lokale/konkrete Fragen**. Short-Tail nur als Pillar-Ziel. Suchvolumen in den Tabellen sind **qualitative Schätzungen (H/M/N)**, keine garantierten Zahlen – wir validieren sie über GSC, sobald Daten da sind.

## 3.2 50 hochrelevante Start-Keywords (verteilt auf die 6 Silos)

### Silo 1: Frugalismus (8)
| # | Keyword | Typ | Intent | Priorität |
|---|---|---|---|---|
| 1 | 50-30-20 regel einfach erklärt | Mid-Tail | Informational | 🔥 (existiert) |
| 2 | wie viel geld als notgroschen | Long-Tail | Informational | 🔥 (existiert) |
| 3 | haushaltsbuch führen app oder papier | Long-Tail | Informational | 🔥 neu |
| 4 | sparen im alltag ohne verzicht | Long-Tail | Informational | 🔥 |
| 5 | impulse kaufen vermeiden tipps | Long-Tail | Informational | 🔥 neu |
| 6 | monatsbudget erstellen vorlage | Mid-Tail | Informational | 🔥 neu |
| 7 | nebenjob ideen von zuhause 2026 | Mid-Tail | Informational | Mittel |
| 8 | finanzielle freiheit erreichen schritte | Mid-Tail | Informational | Mittel |

### Silo 2: Strom sparen (9)
| # | Keyword | Typ | Intent | Priorität |
|---|---|---|---|---|
| 9 | stromanbieter wechseln so gehts | Mid-Tail | Transactional | 🔥 (existiert) |
| 10 | strom sparen haushalt 20 tipps | Mid-Tail | Informational | 🔥 (existiert) |
| 11 | stromfresser finden geräte | Long-Tail | Informational | 🔥 (existiert) |
| 12 | wärmepumpe stromkosten senken | Long-Tail | Informational | 🔥 (existiert) |
| 13 | kühlschrank strom sparen einstellung | Long-Tail | Informational | 🔥 neu |
| 14 | heizkosten senken maßnahmen | Mid-Tail | Informational | 🔥 neu |
| 15 | nachtspeicherheizung lohnt sich | Long-Tail | Informational | Mittel neu |
| 16 | balkonkraftwerk lohnt sich 2026 | Mid-Tail | Transactional | Mittel neu |
| 17 | e-auto laden kosten zuhause | Long-Tail | Informational | 🔥 (existiert) |

### Silo 3: Konto & Karten (9)
| # | Keyword | Typ | Intent | Priorität |
|---|---|---|---|---|
| 18 | kostenloses girokonto ohne gebühren | Mid-Tail | Transactional | 🔥 (existiert) |
| 19 | kreditkarte ohne jahresgebuehr | Mid-Tail | Transactional | 🔥 (existiert) |
| 20 | tagesgeld zinsen sicher anlegen | Mid-Tail | Transactional | 🔥 (existiert) |
| 21 | depot eröffnen schritt für schritt | Long-Tail | Transactional | 🔥 (existiert: Depot 2026) |
| 22 | etf sparplan für anfänger starten | Mid-Tail | Transactional | 🔥 (existiert) |
| 23 | kontowechsel service kostenlos | Long-Tail | Transactional | 🔥 neu |
| 24 | dispokredit zinsen vermeiden | Long-Tail | Informational | 🔥 neu |
| 25 | festgeld oder tagesgeld 2026 | Long-Tail | Transactional | 🔥 neu |
| 26 | depot umzug übertrag anleitung | Long-Tail | Informational | Mittel neu |

### Silo 4: Versicherungen (9)
| # | Keyword | Typ | Intent | Priorität |
|---|---|---|---|---|
| 27 | privathaftpflicht warum pflicht kosten | Mid-Tail | Informational | 🔥 (existiert) |
| 28 | kfz versicherung wechseln wann | Long-Tail | Transactional | 🔥 (existiert) |
| 29 | hausratversicherung was zahlt sie | Mid-Tail | Informational | 🔥 (existiert) |
| 30 | zahnzusatzversicherung lohnt sich | Mid-Tail | Transactional | 🔥 (existiert) |
| 31 | berufsunfähigkeitsversicherung lohnt sich | Mid-Tail | Informational | 🔥 neu |
| 32 | tierversicherung hund sinnvoll | Long-Tail | Transactional | 🔥 (existiert) |
| 33 | versicherungen kündigen welche | Long-Tail | Informational | 🔥 neu |
| 34 | elementarschadenversicherung hochwasser | Long-Tail | Informational | Mittel neu |
| 35 | riester rente lohnt sich 2026 | Mid-Tail | Informational | Mittel neu |

### Silo 5: Internet & DSL (8)
| # | Keyword | Typ | Intent | Priorität |
|---|---|---|---|---|
| 36 | dsl internet flat günstig sichern | Mid-Tail | Transactional | 🔥 (existiert) |
| 37 | dns server ändern schnelleres internet | Long-Tail | Informational | 🔥 (existiert) |
| 38 | wlan verstärker oder mesh | Long-Tail | Transactional | 🔥 (existiert) |
| 39 | handytarife vergleichen günstigster | Mid-Tail | Transactional | 🔥 (existiert) |
| 40 | glasfaser vs dsl vs kabel | Mid-Tail | Informational | 🔥 neu |
| 41 | router kaufen oder mieten | Long-Tail | Informational | 🔥 neu |
| 42 | internet anbieter wechseln kündigen | Long-Tail | Transactional | Mittel neu |
| 43 | wlan verbessern tipps ohne kauf | Long-Tail | Informational | Mittel neu |

### Silo 6: Mietwagen & Reisen (7)
| # | Keyword | Typ | Intent | Priorität |
|---|---|---|---|---|
| 44 | mietwagen günstig buchen tricks | Mid-Tail | Transactional | 🔥 (existiert) |
| 45 | mietwagen versicherung fallen vermeiden | Long-Tail | Informational | 🔥 (existiert) |
| 46 | günstige flüge buchen tricks | Mid-Tail | Transactional | 🔥 (existiert) |
| 47 | last minute urlaub buchen | Mid-Tail | Transactional | 🔥 (existiert) |
| 48 | pauschalreise wann buchen zeitpunkt | Long-Tail | Informational | 🔥 neu |
| 49 | reiseversicherung welche sinnvoll | Long-Tail | Transactional | Mittel neu |
| 50 | urlaub mit kindern günstig | Long-Tail | Informational | Mittel neu |

## 3.3 SERP-Analyse der wichtigsten Konkurrenten (Stand 08/2026)

| Konkurrent | Stärken | Schwächen | Was wir übernehmen | Was wir besser machen |
|---|---|---|---|---|
| **Finanztip** (gemeinnützig, ~500k Newsletter) | Extrem hohe Autorität, 8+ Quellen/Artikel, regelmäßige Updates, Transparenz-Score 9/10 | Sehr lange Texte (2.000+ W.), wenig persönlich | Quellen-Dichte, Aktualität, Transparenz | Persönliche „Frank"-Stimme, kürzere Antworten (Kurz-und-knapp-Box) |
| **Finanzfluss** (YouTube 1,5 Mio+) | Didaktisch brillant, Video-first | Blog zweitrangig, selten Updates | Einfache Erklär-Prinzipien | Texte statt Videos, sofortige Antwort |
| **Frugalisten** | Nische Frugalismus, loyaler Kern | Kleine Reichweite, wenig Struktur | Themen-Tiefe Frugalismus | Klare Silos + Vergleichs-CTA |
| **Aktiengram** | Persönlicher Stil, Praxis-Tipps (Depotübertrag!) | Fokus Invest, keine Vergleichs-Monetarisierung | Praxis-Ebene („Depot-Umzug") | CHECK24-Vergleichs-CTA |
| **Gerd Kommer** | Experten-Autorität Nr. 1 | Hochschwellig, für Einsteiger abschreckend | Seriosität, keine Hype-Sprache | Einsteigerfreundlichkeit |
| **Tim Schäfer Media** | Motivation + Anfänger-Niveau | Kaum Transparenz, Werbe-Druck | Motivations-Ton | Fakten + Quellen |
| **Madame Moneypenny** | Female-Finance-Marke | Andere Zielgruppe | – | – (kein eigener Fokus) |

**SERP-Erkenntnisse für uns:**
1. **Featured Snippets** gehen an klare, kurze Antworten → genau dafür ist unsere Kurz-und-knapp-Box gebaut (eigener Absatz nach der H1).
2. **FAQ-Sektionen** (FAQPage-Schema) sind in YMYL-Nischen Standard – wir haben sie, müssen sie mit Schema ausliefern (→ 3.5).
3. **Aktualität** ist ein Ranking-Faktor (lastmod + Update-Commits) – läuft über `set_lastmod.py`.
4. **Quellen & E-E-A-T** trennen die Spreu vom Weizen – jeder neue Artikel braucht ≥2 externe, seriöse Quellen.

## 3.4 Meta-Tag-Vorlagen (verbindlich, werden vom Meta-Gate geprüft – Score 100/100)

| Feld | Formel | Beispiel |
|---|---|---|
| **Title (≤60 Zeichen)** | `[Haupt-Keyword]: [Nutzen/Kontext]` | „Stromanbieter wechseln 2026: So sparst du beim Tarifwechsel" |
| **Meta-Description (≤155 Zeichen, vollständiger Satz mit . ! ?)** | `[Ergebnis] + [Methode] + [Zahl]` | „Du kannst bis zu 50 € im Monat sparen: So wechselst du den Stromanbieter 2026 in 20 Minuten – Schritt für Schritt erklärt." |
| **URL-Slug** | Klein, Bindestriche, Keyword, ohne Stoppwörter | `/posts/stromvergleich-richtig-lesen-tarif-finden/` |
| **H1** | = Title ohne Marken-/Datums-Ballast, mit Schlüsselphrase | „Stromanbieter wechseln 2026" |
| **Alt-Texte** | = Titel des Artikels (automatisiert via fix_cover_alts.py) | ✅ |

## 3.5 Schema-Markup-Plan

| Schema | Status | Umsetzung |
|---|---|---|
| **Article** | ✅ | Von Hugo/Theme generiert, og:image absolut + `?v=`-Buster |
| **WebSite** | ✅ | Im Head (SearchAction) |
| **Person / Author (Frank)** | ✅ | In `extend_head.html` |
| **FAQPage** | ⏳ **TODO** | FAQ aus Frontmatter als JSON-LD ausgeben (nächster SEO-Commit) |
| **BreadcrumbList** | ⏳ **TODO** | Auf Artikel- und Pillar-Seiten ergänzen |
| **HowTo** | 💡 Optional | Für „So wechselst du…"-Artikel (Vorsicht: Google-Änderungen bei HowTo 2023 – nur wo sinnvoll) |
| **Organization + Logo** | 💡 Optional | Sobald Logo existiert |

## 3.6 E-E-A-T-Optimierung

| Baustein | Status | Maßnahme |
|---|---|---|
| **Erfahrung (Experience)** | ✅ | Frank-Ich-Perspektive in Artikeln, persönliche Anekdoten |
| **Expertise** | ⏳ | „Über Frank"-Seite mit Hintergrund (Bereich, Erfahrung im Vergleichen) – nächster Meilenstein |
| **Autorität (Authority)** | ⏳ | Backlink-Strategie (Kapitel 7.4), Finanzblogroll-Eintrag, Gastbeiträge |
| **Vertrauen (Trust)** | ✅ | Impressum + Datenschutz (pflichtbewusst), Affiliate-Disclosure in jedem Artikel, nur notwendige Cookies, HTTPS |
| **Zitierfähigkeit** | ⏳ | ≥2 seriöse externe Quellen pro Artikel (Verbraucherzentrale, Stiftung Warentest, Bundesnetzagentur, GDV, BaFin, Destatis, ADAC …) – in den 30 Blueprints unten bereits hinterlegt |

---

# 4. CONTENT-AUTOMATIONSSYSTEM (läuft bereits – 9 Workflows)

## 4.0 DAUERVORGABEN: Launch, Kadenz, Artikellänge (festgelegt 19.08.2026)

| Vorgabe | Wert | Umsetzung |
|---|---|---|
| **Blog-Launch** | **08.08.2026** – kein Artikel mit Datum davor; vor dem Launch datierter Alt-Bestand (36 Posts) am 19.08.2026 dauerhaft gelöscht | Frontmatter-`date:` ≥ 2026-08-08 |
| **Bestands-Kadenz** | Blog zeigt Artikel **nur an Mo/Mi/Fr**: 38 Off-Kadenz-Posts (08.08. Sa, 08.09. So, 08.11. Di + 32 Evergreen vom 09.08.) am 19.08.2026 vollständig gelöscht – Bestand: 6 Posts (je 2 an Mo 08.10., Mi 08.12., Fr 08.14.) | `CADENCE-REPORT.md` Regel 3 |
| **Veröffentlichungsintervall** | **Nur Mo, Mi, Fr – 2–3 Artikel pro Publikationstag** (≈ 6–9/Woche) · Haupt-Slot 08:10 MESZ, Fallbacks 16:10/19:40 MESZ · harter Wochentags-Guard + 2er-Floor im Skript | `content-engine-v2.yml` (cron `10 6 * * 1,3,5`), `engine_generate.py` (`PUBLICATION_DAYS`, Floor für `MIN/MAX_ARTIKEL_PRO_TAG`), `cadence_guard.py` (harte Wache + Selbstheilung, 26.08.), Definition in `CADENCE-REPORT.md` |
| **Empfohlene Zeichenlänge pro Blogartikel** | **6.000–10.000 Zeichen** Fließtext (≈ 800–1.400 Wörter; Median-Bestand: 9.124 Zeichen) | `check_length.py` (`OPT_CHARS_MIN/MAX`, Env `LENGTH_OPT_CHARS_MIN/MAX`) |
| **Hartes Vor-Veröffentlichungs-Gate (26.08.2026)** | Jeder Publish (Deploy, Engine, `publish.py`) besteht vorher zwingend: Kadenz (Mo/Mi/Fr, 2–3/Tag) + Titel-Integrität (R5: kein unvollständiger Cover-Text) + Cover-Text-Komplettheit (C4). Verstoß → SOFORTIGE SELBSTHEILUNG (Zurückstufung + Re-Queue, Neu-Render, Verwurf nur bei NEUEN Artikeln mit defektem Titel), erst dann Build/Publish. Report: `CADENCE-GATE-REPORT.md` | `cadence_guard.py` (Wache + `--selftest` + `--fix`), `deploy.yml` Gate-Chain, `publish_gate.py` (5. Prüfung R5), `publish.py` (Routine-Block), `check_titles.py`/`check_covers.py` C4, `safe_title_cut()` in `post_utils.py` · Details: `CADENCE-REPORT.md` Regel 5 |
| Pillar-Seiten (keine Blogartikel) | 2.500–4.000 Wörter (≈ 17.500–28.000 Zeichen) | `length_guard.py` (Hoheitskarte `QUALITAETS-REGELWERK.md`) |

## 4.1 Die vollautomatisierte Content-Pipeline (IST)

```
MO/MI/FR 08:10 MESZ (content-engine-v2.yml – Dauervorgabe, s. 4.0)
  2–3 Artikel pro Publikationstag (MIN/MAX_ARTIKEL_PRO_TAG, Default 2–3;
  harter Wochentags-Guard: Di/Do/Sa/So wird nie veröffentlicht)
  Themenfindung (topics.yaml-Pool, 175 Themen, refill bei Leerung)
  → Artikel generieren (generate_drafts.py, KI mit Groq/Gemini, 1.200+ Wörter)
  → Qualitäts-Pipeline:
       Rechtschreibung (spellcheck.py inkl. Check 3b/3c)
       Grammatik (grammar_check.py) · Lesbarkeit (readability_check.py)
       Meta-Titel/-Desc (meta_optimizer.py, Gate 100/100)
       Profi-Polish (profi_polish.py) · Einzigartigkeit (check_uniqueness.py)
       Affiliate-Links (affiliate_link_check.py) · Covers (check_covers.py)
  → Kurzantwort generieren (generate_kurzantworten.py, bereinigt + validiert)
  → Interne Links setzen (internal_linker.py --max 5)
  → Commit + Deploy (GitHub Pages) → IndexNow-Ping
  → BOT-STATUS.md aktualisieren

WÖCHENTLICH (seo-weekly.yml)   Mo 08:40
  → SEO-Audit, lastmod-Updates, interne Verlinkung nachziehen, Report
WÖCHENTLICH (backlink-weekly.yml) Do 08:50 → Backlink-Report + Outreach-Vorbereitung
WÖCHENTLICH (repin-weekly.yml)   → Pinterest-Repins (73-Pin-Plan; AKTIVIERUNG fehlt: PINTEREST_ACCESS_TOKEN)
VIERTELJÄHRLICH (update-quarterly.yml) → Evergreen-Aktualisierung
TÄGLICH 10:30 (bot-watchdog.yml) → Selbstüberwachung (4 Checks, Issue bei Störung)
IMMER (alert-on-failure.yml) → Fehler-Benachrichtigung
WOCHENTLICH (weekly-audit.yml) → Gesamt-Audit
```

## 4.2 Regeln für Themenfindung (verbindlich)

| Regel | Vorgabe |
|---|---|
| Quelle | `data/topics.yaml` (149 Themen, nach Pillar sortiert, mit Affiliate-URL je Thema) |
| Nachschub | `refill_topics()` ergänzt neue Themen, sobald der Pool < 16 wird (KI-Vorschlag + dedupe gegen existierende Titel) |
| Saisonalität | Immer aktuelle Saisonfenster befüllen (August: Heizperiode, Spätsommer-Reisen; September: Kfz-Wechselstichtag, Gas; November: Versicherungen, Weihnachtsbudget …) |
| Priorität | Long-Tail-Fragen mit Kauf-Nähe zu CHECK24-Kategorien zuerst (Strom/Gas/DSL/Handy/Mietwagen/Kredit/Versicherung) |
| Verboten | Themen außerhalb der 6 Silos, doppelte Titel (uniqueness-Gate), KI-Lieblingsthemen ohne Spar-Bezug |

## 4.3 Regeln für Artikelaufbau (in Generatoren verankert)

```
Frontmatter: title, description (Meta), date, slug, pillar, cover, kurzantwort,
             keywords, tags (normalisiert)
Body:
  H1 (Keyword) → Kurz-und-knapp-Box (Antwort in 1–2 Sätzen mit Zahl)
  → Intro (Problem + Versprechen, 3–4 Sätze)
  → 4–7 H2-Abschnitte (je 3–4 Sätze, ein Gedanke)
  → Vergleichstabelle/Tipps, wo sinnvoll
  → FAQ (3 Fragen, Schema-ready)
  → Affiliate-CTA (1× früh, 1× am Ende) + Disclosure
```

## 4.4 Regeln für interne Verlinkung

- 2–5 Links/Artikel, Pillar immer verlinkt, Ankertexte beschreibend (siehe 2.3)
- `internal_linker.py --max 5` läuft täglich + wöchentlich nach
- Cross-Silo max. 1 Link (z. B. Wärmepumpe → Konto-Artikel nur wenn thematisch zwingend)

## 4.5 Regeln für Aktualisierung & Evergreen

- `update-quarterly.yml`: alle 3 Monate prüft die ältesten Artikel (Preise, Tarife, Gesetze)
- `set_lastmod.py` aktualisiert `lastmod` bei jedem echten Update (SEO-Signal)
- **Regel:** Preis-/Tarifangaben immer als Spannen + „Stand: Monat Jahr"; konkrete Zahlen mit Datum versehen

## 4.6 Automatisierte Social-Media-Verteilung (IST + Lücken)

| Kanal | Status | Plan |
|---|---|---|
| **Pinterest** | ⏳ Workflow `repin-weekly.yml` bereit, 73-Pin-Plan (`data/pinterest_plan.yaml`) – **fehlt: PINTEREST_ACCESS_TOKEN** (Du bist dran) + Board-ID-Variable | Aktivieren, sobald Token da |
| **LinkedIn / Instagram / Facebook** | ❌ Noch keine Automation | Ausbaustufe 2 (nach Pinterest): 3 Posts je Artikel (Textbausteine in `generate_social_posts.py`) – als neue Workflow-Idee notiert |
| **Newsletter** | ❌ Noch kein System | Siehe 6.4 (Funnel + Anbieter-Empfehlung) |

---

# 5. 30 SOFORT VERÖFFENTLICHBARE ARTIKEL (Blueprints)

> **So nutzt du sie:** Jeder Blueprint ist eine vollständige Vorlage – der Content-Bot (generate_drafts.py) oder ein manueller Workflow erzeugt daraus den 1.200+-Wörter-Artikel inkl. aller Qualitäts-Gates. **Alle 30 Themen sind garantiert frei** (kein Duplikat der 39 existierenden Artikel) und liegen in den 6 Silos. Externe Quellen sind echte, seriöse Referenzen (E-E-A-T).

## SILO 1 – FRUGALISMUS (5 Artikel)

### 1. Haushaltsbuch führen: App, Excel oder Stift – was wirklich funktioniert
- **SEO-Titel:** Haushaltsbuch führen: Die 3 besten Methoden im Vergleich
- **Meta-Description:** Du verlierst monatlich den Überblick? So führst du ein Haushaltsbuch, das wirklich funktioniert – mit App, Excel oder Stift. Inkl. kostenloser Vorlage.
- **Gliederung (H2):** Warum ein Haushaltsbuch den größten Hebel hat · Methode 1: Die App (Vor- & Nachteile) · Methode 2: Excel-Vorlage · Methode 3: Stift & Papier · So kategorisierst du Ausgaben richtig · Der 30-Tage-Startplan · Häufige Fehler beim Haushaltsbuch
- **FAQ:** Welche App ist am besten? / Wie viel Zeit kostet Führen pro Woche? / Was bringt ein Haushaltsbuch wirklich?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** Verbraucherzentrale (Haushaltsbuch-Vorlage), Finanztip (Budget-Tipps), Stiftung Warentest (Banking-Apps-Test)
- **Affiliate-CTA:** Generisch CHECK24 (Konto-Check) → `deep=c24bank&cat=14`

### 2. Impulskäufe stoppen: 7 psychologische Tricks, die sofort wirken
- **SEO-Titel:** Impulskäufe vermeiden: 7 Tricks, die dein Budget retten
- **Meta-Description:** 60 % aller Käufe sind Impulskäufe. Diese 7 psychologischen Tricks helfen dir, unnötige Ausgaben sofort zu stoppen – ohne Spaßverzicht.
- **Gliederung (H2):** Warum kaufen wir impulsiv? · Trick 1: Die 48-Stunden-Regel · Trick 2: Einkaufsliste & Budget-Cash · Trick 3: Newsletter abbestellen · Trick 4: Warenkorb-Sperre · Trick 5: Kosten pro Nutzung rechnen · Trick 6: Trigger erkennen · Trick 7: Belohnung umlenken · Was das im Jahr bringt
- **FAQ:** Was sind typische Impulskäufe? / Wie überwinde ich Kaufreiz im Laden? / Helfen Kreditkarten-Hacks?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** Verbraucherzentrale (Konsumkompetenz), Destatis (Konsumausgaben), Stiftung Warentest (Geldratgeber)
- **Affiliate-CTA:** Generisch CHECK24

### 3. Monatsbudget erstellen: Schritt-für-Schritt mit fertiger Vorlage
- **SEO-Titel:** Monatsbudget erstellen: Anleitung mit kostenloser Vorlage
- **Meta-Description:** In 6 Schritten zum Monatsbudget: So planst du Fixkosten, Sparen und Spaß realistisch – mit fertiger Vorlage zum Sofort-Download.
- **Gliederung (H2):** Warum ein Budget ohne Plan scheitert · Schritt 1: Einnahmen erfassen · Schritt 2: Fixkosten auflisten · Schritt 3: Variable Kosten ehrlich schätzen · Schritt 4: Sparziel festlegen · Schritt 5: Budget-Kategorien befüllen · Schritt 6: Monatlich nachjustieren · Die 50-30-20-Variante als Startpunkt
- **FAQ:** Wie viel sollte ich monatlich sparen? / Was tun bei Budget-Überschreitung? / Brauche ich eine App dafür?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** Verbraucherzentrale (Haushaltsrechner), Finanztip (Budgetierung), Bundesbank (Geld & Haushalt)
- **Affiliate-CTA:** Generisch CHECK24

### 4. Sparquote berechnen und steigern: Von 5 % auf 30 % in 12 Monaten
- **SEO-Titel:** Sparquote berechnen: So steigerst du sie auf 30 %
- **Meta-Description:** Deine Sparquote verrät, wie schnell du Vermögen aufbaust. So berechnest du sie richtig und steigerst sie Schritt für Schritt auf 30 %.
- **Gliederung (H2):** Was ist die Sparquote und warum zählt sie? · Formel & Rechenbeispiel · Deine aktuelle Quote ermitteln · Die 4 Stellschrauben (Einnahmen, Fixkosten, Variable, Automatisierung) · Gehaltserhöhung = Sparquote? · Sparquote bei niedrigem Einkommen · Der 12-Monats-Plan von 5 % auf 30 %
- **FAQ:** Was ist eine gute Sparquote? / Zählt die Tilgung zur Sparquote? / Wie automatisiere ich Sparen?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** Stiftung Warentest (Sparen & Anlegen), Finanztip (Sparquote), Bundesbank (Geldpolitik & Sparen)
- **Affiliate-CTA:** Generisch CHECK24 (Depot/Tagesgeld)

### 5. Zweites Standbein: 10 realistische Nebenverdienst-Ideen für 2026
- **SEO-Titel:** Nebenverdienst 2026: 10 Ideen für ein zweites Standbein
- **Meta-Description:** Bis zu 300 € monatlich extra: Diese 10 Nebenverdienst-Ideen funktionieren 2026 wirklich – mit Steuer-Regeln und realistischen Verdienst-Spannen.
- **Gliederung (H2):** Lohnt sich ein Nebenjob überhaupt? · Ideen 1–3: Digital (Freelance, Content, Handmade) · Ideen 4–6: Flexibel (Lieferung, Nachhilfe, Umzüge) · Ideen 7–8: Kapitalbasiert (Vermietung, Dividenden) · Ideen 9–10: Skalierbar (Info-Produkte, Coaching) · Steuerfreibetrag & Anmeldung · So vermeidest du den Nebenjob-Trugschluss
- **FAQ:** Wie viel darf ich steuerfrei dazuverdienen? / Brauche ich ein Gewerbe? / Was bringt am schnellsten Geld?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** Finanzamt/BZSt (Freibeträge), Verbraucherzentrale (Nebenjobs), Arbeitsagentur (Minijob-Zentrale)
- **Affiliate-CTA:** Generisch CHECK24

## SILO 2 – STROM SPAREN (5 Artikel)

### 6. Stromvergleich richtig lesen: So findest du den besten Tarif in 20 Minuten
- **SEO-Titel:** Stromtarif-Vergleich: So liest du Angebote richtig
- **Meta-Description:** Arbeitspreis, Bonus, Preisgarantie – ein Stromvergleich verwirrt. So erkennst du den wirklich günstigsten Tarif in 20 Minuten und wechselst sicher.
- **Gliederung (H2):** Warum Vergleichsportale unterschiedliche Preise zeigen · Die 4 wichtigsten Kennzahlen (Arbeitspreis, Grundpreis, Bonus, Garantie) · Versteckte Kosten erkennen · Neukunden-Boni richtig einrechnen · Preisgarantie: sinnvoll oder unnötig? · So wechselst du ohne Risiko (Kündigung übernimmt der neue Anbieter) · Was du bei Ökostrom beachten solltest
- **FAQ:** Ist der Wechsel wirklich kostenlos? / Was passiert mit meiner Kündigung? / Wie lange dauert der Wechsel?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** Bundesnetzagentur (Strompreis-Monitor), Verbraucherzentrale (Tarifwechsel), CHECK24 Ratgeber
- **Affiliate-CTA:** CHECK24 Strom → `deep=stromanbieter-wechseln&cat=1`

### 7. Kühlschrank & Gefriertruhe: So sparst du 80 € Strom im Jahr
- **SEO-Titel:** Kühlschrank Strom sparen: Die richtige Einstellung zählt
- **Meta-Description:** Kühlschrank und Gefriertruhe sind Dauerläufer. Mit 7 Einstellungen und Gewohnheiten sparst du bis zu 80 € Strom im Jahr.
- **Gliederung (H2):** Warum Kühlgeräte bis zu 20 % des Haushaltsstroms fressen · Die richtige Temperatur (7 °C / −18 °C) · Standort & Abstand · Abtauen & Eis vermeiden · Tür-Verhalten & Befüllung · Altgerät vs. Effizienzklasse A · Wann sich ein Neukauf lohnt (Amortisation)
- **FAQ:** Welche Temperatur ist optimal? / Lohnt sich ein neuer Kühlschrank? / Was kostet ein Kühlschrank im Jahr?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** EU-Energielabel (ec.europa.eu), Verbraucherzentrale (Gerätestrom), ÖKO-TEST (Kühlschrank-Test)
- **Affiliate-CTA:** CHECK24 Strom → `deep=stromanbieter-wechseln&cat=1`

### 8. Heizkosten senken: 10 Maßnahmen, die sich in einer Saison amortisieren
- **SEO-Titel:** Heizkosten senken: 10 Maßnahmen mit schneller Amortisation
- **Meta-Description:** Heizen ist der größte Energieposten. Diese 10 Maßnahmen senken deine Heizkosten spürbar – viele amortisieren sich schon in einer Saison.
- **Gliederung (H2):** Wo die Heizkosten wirklich entstehen · Maßnahmen 1–4: Ohne Kosten (Heizkörper frei, richtig lüften, Thermostat, Türen zu) · Maßnahmen 5–7: Kleine Investition (Dichtungen, Thermostat-Tausch, Reflexionsfolie) · Maßnahmen 8–10: Größer denken (Hydraulischer Abgleich, Heizkurve, Dämmung) · Die Amortisations-Tabelle · Förderung durch die BEG
- **FAQ:** Welche Raumtemperatur ist optimal? / Was bringt ein Thermostat-Tausch? / Lohnt sich der Heizungstausch 2026?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** BMWK (Heizen & Energieeffizienz), Verbraucherzentrale (Heizkosten), CO2-online/Heizspiegel
- **Affiliate-CTA:** CHECK24 Gas → `deep=gasanbieter-wechseln&cat=3`

### 9. Nachtspeicherheizung: Lohnt sich der Wechsel 2026 wirklich?
- **SEO-Titel:** Nachtspeicherheizung: Wechseln oder behalten?
- **Meta-Description:** Nachtspeicherheizungen gelten als Stromfresser. Ob sich ein Wechsel 2026 lohnt und welche Alternativen es gibt – mit Rechenbeispiel.
- **Gliederung (H2):** So funktioniert eine Nachtspeicherheizung · Was sie wirklich kostet (Strom vs. Gas vs. Wärmepumpe) · Das Wärmepumpen-Förderprogramm · Der Sanierungsfahrplan in 5 Schritten · Miete vs. Eigentum: Wer zahlt? · Rechenbeispiel: 70 m² Wohnung
- **FAQ:** Ist die Nachtspeicherheizung verboten? / Was kostet der Austausch? / Gibt es Förderung?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** BMWK (BEG-Förderung), Verbraucherzentrale (Heizungswechsel), Stiftung Warentest (Wärmepumpen)
- **Affiliate-CTA:** CHECK24 Gas/Strom → `deep=gasanbieter-wechseln&cat=3`

### 10. Balkonkraftwerk 2026: Lohnt sich das Stecker-Solar wirklich?
- **SEO-Titel:** Balkonkraftwerk 2026: Kosten, Förderung, Amortisation
- **Meta-Description:** Balkonkraftwerke sind günstiger denn je. So prüfst du, ob sich Stecker-Solar bei dir lohnt – inkl. Förderung, Anmeldung und Rechenbeispiel.
- **Gliederung (H2):** Was ein Balkonkraftwerk kann (und was nicht) · Kosten & Leistung 2026 · Amortisationsrechnung mit echtem Ertrag · Förderung von Bund & Ländern · Anmeldung im Marktstammdatenregister · Balkon, Garten oder Garage: Standort-Check · Typische Fehler beim Kauf
- **FAQ:** Brauche ich einen Elektriker? / Was bringt ein 800-Watt-Modul im Jahr? / Ist die Anmeldung Pflicht?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** BMWK (Solarpaket I), Verbraucherzentrale (Balkonkraftwerk), Stiftung Warentest (Stecker-Solar-Test)
- **Affiliate-CTA:** CHECK24 Strom → `deep=stromanbieter-wechseln&cat=1`

## SILO 3 – KONTO & KARTEN (5 Artikel)

### 11. Kontowechsel in 20 Minuten: So funktioniert der kostenlose Wechselservice
- **SEO-Titel:** Kontowechsel: In 20 Minuten zum kostenlosen Girokonto
- **Meta-Description:** Kontowechsel klingt lästig – ist es aber nicht: Der kostenlose Wechselservice erledigt alles. So wechselst du dein Girokonto in 20 Minuten.
- **Gliederung (H2):** Warum ein Kontowechsel bis zu 200 € im Jahr bringt · Was der Wechselservice automatisch erledigt · Schritt 1–5: Der Wechsel in 20 Minuten · Daueraufträge & Lastschriften im Blick · Den alten Kontostand richtig nutzen · Fallen beim Kontowechsel vermeiden
- **FAQ:** Kostet der Wechselservice etwas? / Was mache ich mit meinem alten Konto? / Wie lange dauert der Wechsel?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** Verbraucherzentrale (Kontowechsel), Stiftung Warentest (Girokonto-Vergleich), BaFin (Einlagensicherung)
- **Affiliate-CTA:** CHECK24 C24 Bank → `deep=c24bank&cat=14`

### 12. Dispozinsen verstehen: Was dein Dispo wirklich kostet + 5 Alternativen
- **SEO-Titel:** Dispozins 2026: Was dein Dispo wirklich kostet
- **Meta-Description:** Rund 10–14 % Zinsen zahlt, wer den Dispo nutzt. So vermeidest du Dispozinsen – mit 5 günstigen Alternativen für den Notfall.
- **Gliederung (H2):** So hoch sind die Dispozinsen 2026 (Überblick) · Rechenbeispiel: 1.000 € für 30 Tage · Warum Banken den Dispo lieben · Alternative 1: Dispo senken lassen · Alternative 2: Notgroschen aufbauen · Alternative 3: Ratenkredit (Kostenvergleich!) · Alternative 4: kostenloses Konto mit Rahmen · Alternative 5: Budget-Fix
- **FAQ:** Kann ich meinen Dispo-Zinssatz verhandeln? / Was kostet ein Ratenkredit im Vergleich? / Ist der Dispo eine gute Notlösung?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** Stiftung Warentest (Dispozinsen), Verbraucherzentrale (Girokonto), Bundesbank (Zinsstatistik)
- **Affiliate-CTA:** CHECK24 Kredit → `deep=kreditvergleich`

### 13. Festgeld oder Tagesgeld? Wo dein Geld 2026 richtig liegt
- **SEO-Titel:** Festgeld oder Tagesgeld: Die richtige Wahl 2026
- **Meta-Description:** Tagesgeld flexibel, Festgeld mehr Zins? So entscheidest du, wo dein Geld 2026 am besten liegt – mit aktuellen Zins-Einordnungen und Sicherheits-Regeln.
- **Gliederung (H2):** Der aktuelle Zinsmarkt kurz erklärt · Tagesgeld: Vorteile & Grenzen · Festgeld: Laufzeiten & Zinsstaffel · Der Zinseszinseffekt im Vergleich · Sicherheit: Einlagensicherung verstehen · Zins-Hopping: Legale Strategie oder Aufwand? · Die Entscheidungs-Matrix
- **FAQ:** Ist mein Geld bei Banken sicher? / Was bringt Zins-Hopping? / Wie viel sollte ich auf Tagesgeld halten?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** BaFin (Einlagensicherung), Bundesbank (Zinsen), Stiftung Warentest (Festgeld)
- **Affiliate-CTA:** CHECK24 Tagesgeld → `deep=tagesgeldvergleich`

### 14. Depot-Umzug: So überträgst du dein Depot ohne Steuerchaos
- **SEO-Titel:** Depot-Umzug: Wechsel ohne Steuerfalle – Schritt für Schritt
- **Meta-Description:** Depot wechseln ist einfacher als gedacht: Der Übertrag läuft automatisch, Steuern fallen keine an. So klappt der Depot-Umzug steuersicher.
- **Gliederung (H2):** Warum ein Depotwechsel sich lohnen kann · Was der Übertrag kostet (Überblick) · Schritt 1–6: Der Depotübertrag · Steuern beim Übertrag: Was du wissen musst (Einstandswerte!) · Steuertöpfe & Verlustverrechnung · Was bei ausländischen Brokern anders ist · Die 5 häufigsten Fehler
- **FAQ:** Kostet ein Depotwechsel Geld? / Muss ich Gewinne versteuern? / Was passiert mit meinen Sparplänen?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** BaFin (Depotübertrag), Stiftung Warentest (Depotvergleich), Verbraucherzentrale (Wertpapierübertrag)
- **Affiliate-CTA:** Generisch CHECK24 (Konto)

### 15. Gebührenfallen im Banking: Auslandszahlungen, Überweisungen & Co.
- **SEO-Titel:** Gebührenfallen beim Banking: Diese 7 Kosten killst du
- **Meta-Description:** Konto, Karte, Ausland: Banken verstecken Kosten an vielen Stellen. Diese 7 Gebührenfallen erkennst und umgehst du ab sofort.
- **Gliederung (H2):** Die unsichtbaren Kontogebühren · Falle 1: Auslandseinsatz-Gebühr · Falle 2: Bargeldautomaten-Fremdgebühr · Falle 3: Konto mit „Servicepauschale" · Falle 4: Kreditkarten-Jahresgebühr · Falle 5: Überweisungsgebühren (SEPA) · Falle 6: Post-Versand & Papierkram · Falle 7: Verwahrentgelte (Negativzinsen-Reste)
- **FAQ:** Welche Kreditkarte ist im Ausland kostenlos? / Was kostet Geld abheben in der EU? / Wie finde ich ein wirklich kostenloses Konto?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** Stiftung Warentest (Bankgebühren), Verbraucherzentrale (Kontowechsel), EU-Kommission (SEPA-Gebühren)
- **Affiliate-CTA:** CHECK24 Kreditkarte → `deep=kreditkarte`

## SILO 4 – VERSICHERUNGEN (5 Artikel)

### 16. Berufsunfähigkeitsversicherung: Für wen sie sich 2026 wirklich lohnt
- **SEO-Titel:** Berufsunfähigkeitsversicherung: Lohnt sich der Abschluss?
- **Meta-Description:** Die BU ist die teuerste Police – und für viele unnötig. Für wen sich der Abschluss 2026 wirklich lohnt und wie du Kosten sparst.
- **Gliederung (H2):** Was die BU absichert (und was nicht) · Der Fall, den keiner kommen sieht: Zahlen & Wahrscheinlichkeiten · Für wen die BU ein Muss ist (Fachkräfte, Selbstständige, junge Familien) · Für wen sie sich nicht lohnt (Beamte, Haushalte mit Polster) · Kostencheck: So findest du die günstigste BU · Gesundheitsfragen ehrlich beantworten · Alternative: Grundfähigkeitsversicherung & Co.
- **FAQ:** Wie viel kostet eine BU im Monat? / Wann muss ich die BU abschließen? / Was passiert bei Berufswechsel?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** GDV (BU-Statistik), Stiftung Warentest (BU-Test), Verbraucherzentrale (Berufsunfähigkeit)
- **Affiliate-CTA:** Tarifcheck → `deep=unfallversicherung` (plus Hinweis auf Vergleichsportal)

### 17. Versicherungen aufräumen: Diese 5 Policen kannst du getrost kündigen
- **SEO-Titel:** Versicherungen kündigen: Diese 5 Policen brauchst du nicht
- **Meta-Description:** Viele Haushalte zahlen für überflüssige Policen. Diese 5 Versicherungen kannst du meist kündigen – und bis zu 400 € im Jahr sparen.
- **Gliederung (H2):** Der Versicherungs-Ordner: Erst Bestandsaufnahme · Kündigen: 1. Handy-/Elektronikversicherung · Kündigen: 2. Reisegepäckversicherung · Kündigen: 3. Doppelte Hausrat (Altverträge) · Kündigen: 4. Kleinst-Lebensversicherungen · Kündigen: 5. Zusatzpolice „Kfz-Schutzbrief" · Die 4 Policen, die wirklich bleiben sollten · Kündigungsfristen richtig nutzen
- **FAQ:** Welche Versicherungen sind Pflicht? / Wie kündige ich nach der neuen Frist? / Was bringt ein Versicherungs-Check?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** Verbraucherzentrale (Versicherungs-Check), GDV (Versicherungslexikon), Stiftung Warentest (Versicherungen)
- **Affiliate-CTA:** Tarifcheck (Haftpflicht/Hausrat) → `deep=haftpflichtversicherung|hausratversicherung`

### 18. Elementarschadenversicherung: Hochwasser, Starkregen & Co.
- **SEO-Titel:** Elementarschadenversicherung: Wer sie braucht & was sie kostet
- **Meta-Description:** Starkregen, Hochwasser, Schneedruck: Nur jede zweite Wohnung ist geschützt. So prüfst du, ob sich die Elementarschadenversicherung für dich lohnt.
- **Gliederung (H2):** Was die Elementarschadenversicherung abdeckt · Warum die Hausrat/Kfz allein nicht reicht · Wer ein hohes Risiko hat (Zonierung!) · Kosten & Selbstbeteiligung · Der Staat hilft nur bei versicherten Schäden · So wechselst du in den Tarif · 3 Schritte zur Entscheidung
- **FAQ:** Ist die Elementarschadenversicherung Pflicht? / Was kostet sie im Jahr? / Was mache ich bei bestehender Hausrat?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** GDV (ZÜRS-Zonierung), Verbraucherzentrale (Elementarschäden), Stiftung Warentest (Elementarschaden-Test)
- **Affiliate-CTA:** Tarifcheck → `deep=hausratversicherung`

### 19. Kfz-Versicherung: SF-Klasse, Prozente & Rabatte verständlich erklärt
- **SEO-Titel:** SF-Klasse einfach erklärt: So steigst du in die beste Stufe
- **Meta-Description:** SF-Klasse 1/2, Prozente, Rabattretter: So funktioniert die Kfz-Versicherung wirklich – und so holst du den besten Preis heraus.
- **Gliederung (H2):** Was die SF-Klasse ist und wie sie wächst · Typklasse & Regionalklasse: Die unbekannten Preistreiber · Schadenfreiheit sichern: Rabattretter & Co. · Die 6 größten Rabatte (Werkstattbindung, Telematik, online) · Jährlicher Wechsel: Wann er sich lohnt · So liest du das Vergleichsangebot richtig
- **FAQ:** Wie lange dauert es bis SF-Klasse 35? / Was passiert nach einem Unfall? / Kann ich Prozente von Eltern übernehmen?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** GDV (Typklassen), Stiftung Warentest (Kfz-Versicherung), Verbraucherzentrale (Kfz-Wechsel)
- **Affiliate-CTA:** CHECK24 Kfz → `deep=kfz-versicherung`

### 20. Riester-Rente 2026: Für wen sich der Abschluss noch lohnt
- **SEO-Titel:** Riester-Rente 2026: Weiterfördern oder kündigen?
- **Meta-Description:** Die Riester-Reform kommt – aber was heißt das für deinen Vertrag? So entscheidest du 2026: fördern, stilllegen oder kündigen.
- **Gliederung (H2):** Wie Riester funktioniert (Grundzulage, Kinderzulage, Steuervorteil) · Die Reform 2026: Was sich ändert · Für wen Riester weiterhin lohnt (Familien mit Kindern!) · Für wen sich die Kündigung lohnt · Stilllegen vs. kündigen vs. weiterzahlen · Der Kosten-Check deines Vertrags · Alternativen (ETF-Sparplan, betriebliche Altersvorsorge)
- **FAQ:** Soll ich meinen Riester kündigen? / Was passiert mit den Zulagen bei Kündigung? / Gibt es bessere Alternativen?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** Bundesministerium für Arbeit (Riester), Verbraucherzentrale (Riester-Analyse), Stiftung Warentest (Riester-Test)
- **Affiliate-CTA:** Generisch CHECK24 (Konto) + Tarifcheck

## SILO 5 – INTERNET & DSL (5 Artikel)

### 21. Glasfaser, DSL oder Kabel? Der Anschluss-Vergleich 2026
- **SEO-Titel:** Glasfaser vs. DSL vs. Kabel: Welcher Anschluss passt?
- **Meta-Description:** Glasfaser, DSL oder Kabel – welcher Internetanschluss lohnt sich 2026 für dich? Der Vergleich von Tempo, Preis und Verfügbarkeit.
- **Gliederung (H2):** Die 3 Technologien kurz erklärt · Tempo im Alltag: Was du wirklich brauchst (50/100/250/1000 Mbit) · Preis-Leistungs-Vergleich 2026 · Verfügbarkeit prüfen (Ausbaugebiete) · Glasfaser: Wann der Umstieg Pflicht wird · Kabel: Die Drossel-Falle im Abend · Die Entscheidungs-Tabelle
- **FAQ:** Wie schnell muss Internet wirklich sein? / Was kostet Glasfaser im Monat? / Wann lohnt sich der Wechsel?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** Bundesnetzagentur (Breitbandatlas), Verbraucherzentrale (Internetverträge), CHECK24 Ratgeber
- **Affiliate-CTA:** CHECK24 DSL → `deep=dsl-anbieterwechsel&cat=4`

### 22. Router kaufen oder mieten? Die Rechnung, die dir 120 € spart
- **SEO-Titel:** Router kaufen oder mieten: Was sich wirklich rechnet
- **Meta-Description:** Der Miet-Router kostet dich oft 5 € pro Monat – auf 2 Jahre über 120 €. Wann sich Kaufen lohnt und was du beim Wechsel beachten musst.
- **Gliederung (H2):** Die Miet-Falle: Was Router-Miete wirklich kostet · Wann Mieten sinnvoll ist (Fritzbox-Update, Support) · Die Kauf-Rechnung (Amortisation nach 12–18 Monaten) · Router-Freiheit: Dein Recht auf eigene Hardware · Kompatibilität prüfen (Anschlussart!) · WLAN-Qualität: Worauf du beim Kauf achtest · Die 3 besten Preis-Leistungs-Router (Kategorien)
- **FAQ:** Darf ich den Router selbst kaufen? / Welcher Router ist der beste? / Was passiert mit dem alten Miet-Router?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** Bundesnetzagentur (Router-Freiheit), Stiftung Warentest (Router-Test), Verbraucherzentrale (Internetvertrag)
- **Affiliate-CTA:** CHECK24 DSL → `deep=dsl-anbieterwechsel&cat=4`

### 23. Internet-Anbieter wechseln: Kündigungsfristen & Sonderkündigungsrecht
- **SEO-Titel:** Internetvertrag wechseln: Fristen, Sonderkündigung, Tipps
- **Meta-Description:** Kein Internetvertrag ist eine Lebensbindung: So kündigst du richtig, nutzt Sonderkündigungsrechte und wechselst ohne Stress zum günstigeren Tarif.
- **Gliederung (H2):** Kündigungsfristen 2026: Was gesetzlich gilt · Sonderkündigungsrecht: Wann du sofort rauskommst (Preiserhöhung, Umzug) · Der Wechsel-Ablauf ohne Internet-Lücke · Kündigung per Musterbrief (Vorlage) · Was Anbieter dir „beim Bleiben" bieten · Die besten Wechsel-Zeitpunkte (Neukunden-Boni) · Checkliste: Alle Leistungen im Blick
- **FAQ:** Wann darf ich vorzeitig kündigen? / Wie kündige ich sicher? / Gibt es Wechsel-Boni?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** Verbraucherzentrale (Kündigung & Sonderkündigung), Bundesnetzagentur (Verbraucherservice), CHECK24 Ratgeber
- **Affiliate-CTA:** CHECK24 DSL → `deep=dsl-anbieterwechsel&cat=4`

### 24. WLAN zu Hause verbessern: 12 Tipps ohne neue Hardware
- **SEO-Titel:** WLAN verbessern: 12 Tipps ohne neue Hardware
- **Meta-Description:** Langsames WLAN? Diese 12 Einstellungen und Tricks verbessern dein WLAN sofort – ohne einen Euro für neue Hardware auszugeben.
- **Gliederung (H2):** Der richtige Router-Standort · Frequenzwahl: 2,4 vs. 5 GHz · Kanal-Check & Nachbarn · Firmware-Update & Neustart-Routine · WLAN-Verschlüsselung & versteckte Geräte · DLAN-Optimierung statt Kabelverlegung · Die 12-Tipps-Checkliste
- **FAQ:** Warum ist mein WLAN abends langsam? / Was bringt ein Kanalwechsel? / Wie weit reicht WLAN durch Wände?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** Bundesnetzagentur (Funkfrequenzen), Stiftung Warentest (WLAN-Router), Verbraucherzentrale (Internet)
- **Affiliate-CTA:** CHECK24 DSL → `deep=dsl-anbieterwechsel&cat=4`

### 25. 5G-Home-Router oder DSL? Wann mobiles Internet sich lohnt
- **SEO-Titel:** 5G-Home statt DSL: Für wen sich mobiles Internet lohnt
- **Meta-Description:** Kein Glasfaser, aber 5G-Abdeckung? Der 5G-Home-Router ist für viele eine echte DSL-Alternative. Wann er sich lohnt – und wann nicht.
- **Gliederung (H2):** So funktioniert 5G-Home · Tempo & Latenz im Vergleich zu DSL/Kabel · Die 5G-Abdeckung realistisch prüfen · Kostenvergleich: 5G-Home vs. DSL-Vertrag · Datenvolumen: Die unbekannte Grenze · Für wen sich 5G-Home lohnt (Land, Pendler, Zweitwohnsitz) · Die 3 Fallstricke beim 5G-Vertrag
- **FAQ:** Wie schnell ist 5G-Home wirklich? / Was passiert bei Datenlimit? / Kann ich 5G-Home mitnehmen?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** Bundesnetzagentur (5G-Abdeckung), Verbraucherzentrale (Mobilfunk), CHECK24 Ratgeber
- **Affiliate-CTA:** CHECK24 Handy → `deep=handytarife`

## SILO 6 – MIETWAGEN & REISEN (5 Artikel)

### 26. Mietwagen im Winter: So sicherst du Schnäppchen in der Nebensaison
- **SEO-Titel:** Mietwagen im Winter: Die besten Schnäppchen-Tricks
- **Meta-Description:** Im Winter sind Mietwagen bis zu 60 % günstiger. Mit diesen 7 Tricks sicherst du Schnäppchen für Skireise und Winterurlaub.
- **Gliederung (H2):** Warum Winter-Mietwagen so günstig sind · Trick 1: Abholzeitpunkt clever wählen · Trick 2: Winterreifen-Check (Pflicht!) · Trick 3: Skigebiete: Kleinwagen statt SUV · Trick 4: Voll bis voll & Tankregel · Trick 5: Der richtige Buchungszeitpunkt · Trick 6: Versicherungskombination · Trick 7: Stornobedingungen nutzen
- **FAQ:** Muss ich Winterreifen extra buchen? / Wann bucht man den Winter-Mietwagen? / Was kostet Mietwagen im Winter?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** ADAC (Mietwagen-Tipps), Verbraucherzentrale (Mietwagen), CHECK24 Ratgeber
- **Affiliate-CTA:** CHECK24 Mietwagen → `deep=mietwagen-preisvergleich&cat=10`

### 27. Pauschalreise buchen: Der beste Zeitpunkt + 6 Spartricks
- **SEO-Titel:** Pauschalreise buchen: Wann ist der beste Zeitpunkt?
- **Meta-Description:** Frühbucher oder Last Minute? Der beste Buchungszeitpunkt für Pauschalreisen hängt vom Ziel ab. Mit 6 Spartricks und den besten Zeitfenstern.
- **Gliederung (H2):** Frühbucher vs. Last Minute: Die Wahrheit · Die besten Buchungszeitfenster je Ziel · Der Preisverlauf verstehen (5 Muster) · Spartrick 1: Flexibel beim Abflughafen · Spartrick 2: Mitte der Woche fliegen · Spartrick 3: Zubuchungen geschickt wählen · Der Pauschalreise-Vorteil: Sicherheit & Recht
- **FAQ:** Wann ist die günstigste Buchungszeit? / Ist Last Minute günstiger? / Was schützt die Pauschalreise?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** Verbraucherzentrale (Reiserecht), ADAC (Reise-Tipps), Stiftung Warentest (Reisen)
- **Affiliate-CTA:** CHECK24 Pauschalreisen → `deep=pauschalreisen-vergleich&cat=9`

### 28. Flug buchen: 9 Tricks, die bei jedem Ticket Geld sparen
- **SEO-Titel:** Flug buchen: 9 Tricks für günstige Flugtickets
- **Meta-Description:** Bis zu 40 % sparen beim Flug: Diese 9 bewährten Tricks funktionieren bei jeder Buchung – von Suchfenstern bis Versteckte-Gebühren-Falle.
- **Gliederung (H2):** Der richtige Suchzeitpunkt · Flexible Ziele & Daten nutzen · Abflughafen-Vergleich (Umfeld) · Die 7-Tage-Regel für Inlandsflüge · Handgepäck-Tarife richtig lesen · Versteckte Kosten: Sitzplatz, Priority, Versicherung · Vielfliegerprogramme clever nutzen · Der Buchungs-Check vor dem Klick
- **FAQ:** Wann sind Flüge am günstigsten? / Lohnt sich der Geheimtipp „Dienstag buchen"? / Was kostet Handgepäck extra?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** Verbraucherzentrale (Fluggastrechte), ADAC (Reiserecht), Stiftung Warentest (Reisen)
- **Affiliate-CTA:** CHECK24 Flug → `deep=flugvergleich`

### 29. Reiseversicherung richtig kombinieren: Kranken, Storno, Gepäck
- **SEO-Titel:** Reiseversicherung: Diese Kombination ist die richtige
- **Meta-Description:** Reiserücktritt, Auslandskranken, Gepäck – welche Reiseversicherungen du wirklich brauchst und wie du sie günstig kombinierst.
- **Gliederung (H2):** Die 3 wichtigsten Reiseversicherungen · Auslandskrankenversicherung: Pflicht für jede Reise · Reiserücktrittsversicherung: Wann sie sich lohnt · Gepäckversicherung: Meist überflüssig · Jahresvertrag vs. Einzelreise · Die Kombi-Falle der Reiseportale · So findest du den günstigsten Schutz
- **FAQ:** Was kostet eine Auslandskrankenversicherung? / Wann lohnt Reiserücktritt? / Zahlt die GKV im Ausland?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** Verbraucherzentrale (Reiseversicherung), Stiftung Warentest (Reiseversicherungs-Test), GDV (Reiseversicherung)
- **Affiliate-CTA:** Tarifcheck → `deep=reisekrankenversicherung`

### 30. Urlaub mit Kindern günstig: Familien-Spartricks, die wirklich ziehen
- **SEO-Titel:** Urlaub mit Kindern: So sparst du 300 € pro Familienreise
- **Meta-Description:** Familienurlaub muss nicht teuer sein: Diese 10 Spartricks senken die Reisekosten mit Kindern um bis zu 300 € – ohne Spaßverlust.
- **Gliederung (H2):** Die größten Kostenposten im Familienurlaub · Trick 1: Kinder-Rabatte systematisch nutzen · Trick 2: Verpflegung & Selbstversorgung · Trick 3: Familienzimmer vs. Appartement · Trick 4: Bahn statt Flug (Familien-Bonus) · Trick 5: Mietwagen ohne Kindersitz-Miete · Trick 6: Nebensaison für Familien · Trick 7–10: die restlichen Spartricks · Die Familien-Spar-Checkliste
- **FAQ:** Ab wann ist Urlaub mit Kindern günstiger? / Was kostet ein Kindersitz im Mietwagen? / Lohnt sich die Familienkarte?
- **Interne Links:** *(werden nach dem Mo/Mi/Fr-Aufbau neu verdrahtet – Alt-Bestand am 19.08.2026 gelöscht)*
- **Externe Quellen:** ADAC (Familienreisen), Verbraucherzentrale (Reiserecht), Stiftung Warentest (Reisen)
- **Affiliate-CTA:** CHECK24 Mietwagen/Pauschalreisen → `deep=mietwagen-preisvergleich&cat=10` / `deep=pauschalreisen-vergleich&cat=9`

---

# 6. MONETARISIERUNGSSTRATEGIE

## 6.1 Affiliate-Plan (IST + Ausbau)

| Bereich | Partner | Deep-Link (CHECK24 pid=80968&aid=18) | Status |
|---|---|---|---|
| Strom | CHECK24 | `deep=stromanbieter-wechseln&cat=1` | ✅ live |
| Gas | CHECK24 | `deep=gasanbieter-wechseln&cat=3` | ✅ live |
| DSL/Internet | CHECK24 | `deep=dsl-anbieterwechsel&cat=4` | ✅ live |
| Handy | CHECK24 | `deep=handytarife` | ✅ live |
| Mietwagen | CHECK24 | `deep=mietwagen-preisvergleich&cat=10` | ✅ live |
| Pauschalreisen | CHECK24 | `deep=pauschalreisen-vergleich&cat=9` | ✅ live |
| Flüge | CHECK24 | `deep=flugvergleich` | ✅ live |
| Girokonto (C24) | CHECK24 | `deep=c24bank&cat=14` | ✅ live |
| Kreditkarte | CHECK24 | `deep=kreditkarte` | ✅ live |
| Kredit | CHECK24 | `deep=kreditvergleich` | ✅ live |
| Tagesgeld | CHECK24 | `deep=tagesgeldvergleich` | ✅ live |
| Kfz-Versicherung | CHECK24 | `deep=kfz-versicherung` | ✅ live |
| Haftpflicht/Hausrat/Zahn/Reisekranken/Unfall | partner-versicherung.de (Tarifcheck partner_id=47086&ad_id=15) | `deep=haftpflichtversicherung` etc. | ✅ live |
| Tierversicherung | partner-versicherung.de | `deep=hundeversicherung` (Katzen nicht abgedeckt – Hinweis im Artikel) | ✅ live |

**Ausbaustufe 2 (sobald Traffic > 5.000/Monat):**
- **Broker-Vergleich** (Trade Republic, Scalable, ING – mit eigenen Affiliate-Programmen, hohe Payouts, aber gründlich prüfen!)
- **Festgeld/Tagesgeld-Listing** (Bank-Affiliates z. B. über CHECK24-Banking)
- **Versicherungs-Makler-Portale** (zweites Standbein neben Tarifcheck)

## 6.2 Platzierungslogik für Affiliate-Links (verbindlich)

| Position | Regel |
|---|---|
| **Im Artikel** | Max. **2 CTA-Stellen**: ① nach der Kurz-und-knapp-Box (Kontext: „Jetzt Angebote vergleichen") ② am Artikelende vor der FAQ |
| **Anker-CTA** | Gelbe Pill-Buttons (CSS vorhanden) – auffällig, aber nicht aufdringlich |
| **Disclosure** | Affiliate-Hinweis unter jedem CTA + globale Disclosure-Seite (implementiert) |
| **Kontextpflicht** | Link nur, wenn der Absatz zum Thema passt (Vergleich, Wechsel, Tarif) – nie im ersten Satz |
| **Gate** | `affiliate_link_check.py` prüft täglich: 44 Seiten, 0 Probleme (✅) |
| **Verhältnis** | 1 Affiliate-Link auf ≥ 400 Wörter – keine Link-Häufung |

## 6.3 Lead-Magnet-Ideen (sofort umsetzbar)

| Lead-Magnet | Format | Funnel-Ziel |
|---|---|---|
| **„Haushaltsbuch-Vorlage"** (Excel/PDF) | Download hinter E-Mail | Budget-Artikel (Blueprint #1, #3) |
| **„Wechsel-Checkliste Strom/Gas"** | PDF, 1 Seite | Strom-/Gas-Artikel |
| **„50-30-20-Planer"** | 1 Blatt zum Ausdrucken | 50-30-20-Artikel |
| **„Versicherungs-Ordner-Check"** | Checkliste | Versicherungs-Artikel (#17) |
| **„Mietwagen-Checkliste"** (vor Ort) | PDF | Mietwagen-Artikel |

## 6.4 Newsletter-Funnel (Ausbaustufe 2 – noch nicht gebaut)

```
Stufe 1  Opt-in: Lead-Magnet (s. o.) – Double-Opt-in, DSGVO-konform (Anbieter: Brevo oder MailerLite, kostenlos bis 2.000/5.000 Kontakte)
Stufe 2  Willkommens-Serie (3 Mails): Über Frank → 3 Sofort-Spartipps → Top-3-Artikel mit CTA
Stufe 3  Wöchentlicher „Spar-Ticker" (Fr 08:00): 3 Artikel der Woche + 1 Sparzahl + 1 Affiliate-CTA
Stufe 4  Quartals-„Wechsel-Erinnerung": Kfz-Stichtag (Nov), Strom/Gas (Sep–Nov), Versicherungs-Check (Jan)
Automatisierung: Newsletter-Aufbau-Workflow ergänzt daily-content.yml (Liste der Woche) – neuer GitHub-Workflow newsletter-weekly.yml
```

## 6.5 E-Book- & Kurs-Strategie (ab ~10.000 Besucher/Monat)

**E-Book 1: „Der 30-Tage-Sparplan"** (9,90 €)
- Inhaltsverzeichnis: Tag 1–7 Überblick & Haushaltsbuch · Tag 8–14 Fixkosten-Killer · Tag 15–21 Verzicht ohne Leiden · Tag 22–28 Automatisierung · Tag 29–30 Notgroschen & Ausblick · Bonus: Vorlagen
**E-Book 2: „Tarifwechsel-Radar"** (14,90 €, jährlich aktualisiert)
- Inhaltsverzeichnis: Die 6 wichtigsten Wechseltermine · Strom/Gas/DSL/Handy: Schritt-für-Schritt · Kfz-Stichtag-Planer · Muster-Kündigungsschreiben · Vergleichs-Checklisten
**Kurs: „Finanzen für Einsteiger"** (49 €, 6 Module)
- Modul 1 Budget & Haushaltsbuch · Modul 2 Notgroschen & Tagesgeld · Modul 3 Versicherungen ohne Überversicherung · Modul 4 ETF-Sparplan starten · Modul 5 Tarife optimieren · Modul 6 Der 12-Monats-Plan

---

# 7. AUTOMATISIERTE WARTUNG & SKALIERUNG

## 7.1 Redaktionskalender 12 Monate (Saison-Fokus, rollierend)

| Monat | Saison-Fokus (Silo) | Konkrete Themen | Automation |
|---|---|---|---|
| Aug 2026 | Heizperiode, Spätsommer-Reisen | #7, #8, #26–30, #6, #10 | daily + seo-weekly |
| Sep 2026 | Kfz-Wechsel, Gas, Energie | Kfz-Stichtag (30.11. vorbereiten), Gastarife, Heizungs-Check | daily + backlink |
| Okt 2026 | Versicherungen, Herbst | #17, #18, #16, Kfz-Fokus | daily + repin |
| Nov 2026 | Kfz-Wechsel-Hauptzeit, Weihnachtsbudget | Kfz-Artikel aktualisieren, Weihnachts-Sparartikel (Neu) | daily + seo |
| Dez 2026 | Jahresrückblick, Budget-Planung | #3, #4, Jahres-Rückblick-Artikel (Neu), Steuer-Vorbereitung | update-quarterly |
| Jan 2027 | Neujahrs-Vorsätze, Steuern | #1, #2, Steuer-Artikel (Neu: „Steuererklärung für Anfänger") | daily + newsletter |
| Feb 2027 | Versicherungs-Check, Reise-Buchung | #19, #20, #27, #29 | daily + repin |
| Mär 2027 | Frühjahrs-Check, Depot/ETF | #14, ETF-Fokus, #4, #5 | daily + seo |
| Apr 2027 | Steuern-Frist, Sommer-Buchung | Steuer-Artikel aktualisieren, #28, #30, #26 | daily + backlink |
| Mai 2027 | Sommerreisen, Mietwagen | #26, #27, #30, Mietwagen-Hauptsaison-Tipps (Neu) | daily + repin |
| Jun 2027 | Energie-Vorsorge, Balkonkraftwerk | #10, #9, #13 | daily + update-quarterly |
| Jul 2027 | Sommer-Fokus, Ausblick | #7, #8 (Refresh), Halbjahres-Audit, Plan Q4 | weekly-audit + seo |

## 7.2 Automatisierte Qualitätskontrolle (7 Gates – laufen täglich/wöchentlich, alle ✅)

| Gate | Skript | Ergebnis-Stand |
|---|---|---|
| Rechtschreibung + Satzanfänge + Entity-/NBSP-Checks (3b/3c) | spellcheck.py | 0 Funde |
| Grammatik | grammar_check.py | ✅ |
| Meta-Qualität (Titel/Desc) | meta_report.py / meta_optimizer.py | Ø 100/100 |
| Lesbarkeit | readability_check.py | Top-Level, 0 < 75 |
| Profi-Text / KI-Floskeln | profi_text_check.py | 100/100 |
| Einzigartigkeit | check_uniqueness.py | bestanden |
| Affiliate-Links | affiliate_link_check.py | 44 Seiten, 0 Probleme |
| Covers | check_covers.py | 0 Probleme |
| Bot-Selbstkontrolle | bot-watchdog.yml (4 Checks) | ✅ repariert (6523e5b) |

## 7.3 Automatisierte SEO-Updates

- **Täglich:** Interne Verlinkung nachziehen (internal_linker), IndexNow-Ping bei neuen Artikeln
- **Wöchentlich (seo-weekly.yml):** Meta-Audit, lastmod, neue Chancen (GSC-Daten sobald > 1.000 Klicks)
- **Quartalsweise (update-quarterly.yml):** Evergreen-Refresh (Preise, Tarife, Gesetze, Screenshots)
- **Offen:** FAQPage- & Breadcrumb-Schema (→ 3.5), GSC-Domain-Property einrichten (empfohlen: Property „franksfinanzcheck.de" – dann auch alle Subdomain-Daten)

## 7.4 Automatisierte Backlink-Strategie

| Taktik | Umsetzung | Status |
|---|---|---|
| **Finanzblogroll.net** | Blog eintragen (größtes deutsches Finanzblog-Verzeichnis) | 🔥 nächster Schritt |
| **Gastartikel** | 1×/Monat auf kompatiblen Blogs: Themen „Tarifwechsel-Leitfaden", „Versicherungs-Checkliste" (mit Link zurück) | backlink-weekly.yml bereitet vor |
| **Outreach-Vorlage** | Kurz + persönlich: „Ich habe X geschrieben, das passt zu eurem Artikel Y – gern als Quelle verlinken" | Vorlage in BACKLINK-REPORT.md |
| **Digital PR** | Saisonale Daten-Pressemitteilungen („Kfz-Wechsel-Stichtag: So viel sparen Deutsche 2026") – Zitate für lokale Medien | Ausbaustufe 2 |
| **Nofollow-Disclosure** | Affiliate-Links sauber kennzeichnen → keine Penalty-Risiken | ✅ |

## 7.5 Skalierungsplan 100.000 Besucher/Monat (4 Phasen)

| Phase | Ziel | Maßnahmen | KPI |
|---|---|---|---|
| **1. Fundament** (0–2k/Monat, jetzt) | 100 Artikel, alle Gates grün, Pinterest aktiv | 2 Artikel/Tag → 4 Artikel/Tag (Variable `MAX_ARTIKEL_PRO_TAG=4` setzen!), Pinterest-Token, Newsletter-Start | 39 → 100 Artikel, 73 Pins |
| **2. Autorität** (2–10k, Monat 3–8) | Top-10-Rankings Long-Tail, erste Short-Tail | FAQ-Schema, GSC-Auswertung, Backlinks (Finanzblogroll, 6 Gastartikel), E-Book-Start | 100+ Keywords in Top 20 |
| **3. Wachstum** (10–50k, Monat 9–18) | Featured Snippets, Video/Aufbau | Kurzvideo-Skripte (Social), Newsletter 2.000+, Produktvergleiche, Kooperationen | 1.000+ Rankings |
| **4. Dominanz** (50–100k, Monat 19–30) | Short-Tail, Marke | Kurs-Launch, Podcast-Gäste, PR, zweites Standbein (YouTube) | 5.000+ Rankings, 20 % Direkt-Traffic |

---

# 8. AUSGABEFORMAT (Portierbarkeit – WordPress oder jedes CMS)

## 8.1 Von Hugo zu WordPress / anderem CMS

| Hugo-Element | WordPress-Äquivalent | Mapping |
|---|---|---|
| Page-Bundle (`content/posts/SLUG/index.md`) | Beitrag mit Slug | Slug 1:1 übernehmen (keine Redirects nötig) |
| Frontmatter (`title`, `description`, `pillar`, `kurzantwort`, `cover`) | Yoast/RankMath-Felder + Kategorien + Custom-Fields | `pillar` → Kategorie; `kurzantwort` → Custom-Field oder FAQ-Block |
| Pillar-Pages | Kategorie-Archive oder Landingpages | Kategorie-Seite mit Einleitungstext |
| Kurz-und-knapp-Box | FAQ-Block/Info-Box (Plugin: „Box"-Block) | Inhalt aus `kurzantwort` |
| Qualitäts-Gates | Nicht 1:1 – als Redaktions-Checkliste (editorial workflow plugin) | Checkliste aus 7.2 |
| Automationen | Kein natives Äquivalent → bleiben als GitHub-Workflows bestehen (Content wird generiert, Mensch importiert) | Oder: WordPress-REST-API-Import-Skript (wp-cli `post create`) |
| Affiliate-Links | ThirstyAffiliate / Pretty Links (Link-Management) | URLs 1:1 übernehmen |

## 8.2 Empfehlung

**Bleib bei Hugo + GitHub + Cloudflare** (kostenlos, blitzschnell, versioniert, automatisierbar) – WordPress lohnt erst, wenn du Plugin-Ökosystem (Newsletter, Shop, Kurse) brauchst. Der saubere Migrationspfad steht oben bereit. **Wichtig:** Sollte je umgezogen werden → 301-Redirects von allen Artikel-URLs + Sitemap + Schema übernehmen.

## 8.3 Nächste konkrete Schritte (Prioritätsreihenfolge)

| # | Aktion | Aufwand |
|---|---|---|
| 1 | Pinterest-Token erzeugen → `PINTEREST_ACCESS_TOKEN` + `PINTEREST_BOARD_ID` Secrets → repin-weekly aktivieren (73-Pin-Plan liegt bereit) | 10 min |
| 2 | Variable `MAX_ARTIKEL_PRO_TAG=4` setzen (Zeitfenster stehen bereit) | 2 min |
| 3 | FAQPage- + Breadcrumb-Schema implementieren (nächster SEO-Commit) | 1 h |
| 4 | „Über Frank"-Seite (E-E-A-T) + GSC-Domain-Property | 30 min |
| 5 | Artikel 1–10 aus den 30 Blueprints durch die Pipeline jagen | automatisch |
| 6 | Newsletter-Funnel aufbauen (Brevo, 3 Willkommens-Mails, Spar-Ticker) | 2–3 h |
| 7 | E-Book „Der 30-Tage-Sparplan" schreiben (aus Artikeln destillieren) | 1–2 Tage |

---
*Ende des Master-Systems. Stand 09.08.2026 – alle Angaben zum IST-Stand stammen aus den laufenden Gates/Reports des Repos (BOT-STATUS.md, META-REPORT.md, AFFILIATE-REPORT.md, BLOG-OPTIMIERUNGSPLAN.md).*
