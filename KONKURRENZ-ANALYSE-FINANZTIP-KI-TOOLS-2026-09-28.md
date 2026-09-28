# Konkurrenz-Analyse Finanztip: KI-Tools für Aktualität & Lesbarkeit

> **Auftrag:** Herausfinden, welche KI-Tools der Hauptwettbewerber (finanztip.de) einsetzt,
> um Onlinebeiträge **inhaltlich**, **rechnerisch** und **redaktionell** aktuell zu halten
> und die **Lesbarkeit** zu verbessern – und ableiten, wo FranksFinanzcheck nachsetzen
> bzw. die Qualität erreichen/übertreffen kann.
>
> **Recherche-Stand:** 28.09.2026 · **Bearbeitung:** Arena-Agent (Branch `arena/01a0e548`)
> **Recherche-Quellen:** finanztip.de (Über uns, Redaktionskodex, Ratgeber-Artikel, Pressebereich),
> Stellenanzeigen (Personio-Jobportal, Indeed, Stepstone-Aggregate), Branchenpresse
> (IT Boltwise, Wirtschaftsjournalist:in), Artikel-Fußnoten und Seitenquelltext.

---

## 1. Kernaussagen (TL;DR)

1. **Finanztip nennt auf der Website keine konkreten KI-Produkte** (kein ChatGPT, kein
   Jasper, kein LanguageTool o. Ä. wird öffentlich benannt). Was öffentlich ist: das
   *System* – KI-gestützte Vorarbeit + harte redaktionelle Prüfung + Datenpipelines.
2. Die KI-Nutzung ist **drittklassig belegbar über Stellenanzeigen**: Eine eigene Rolle
   „(Senior) Product Data & AI Automation Manager“ baut mit dem „Test & Analyse“-Team
   einen **weitgehend automatisierten, KI-gestützten Prozess für Produkttests** –
   Änderungserkennung bei Anbieter-/Konditionsdaten, schnellere und häufigere
   Test-Updates, KPIs + Stichproben als Qualitätssicherung.
3. **„Rechnerisch aktuell“ ist bei Finanztip kein Tool, sondern eine Datenpipeline:**
   wöchentliches Zinsbarometer (inkl. EZB-Referenz), monatlich neu berechnete
   Konditionstabellen („Top-3-Häufigkeit der letzten 12 Monate“), je Tabelle eine
   Quellen- und Stand-Zeile („Quelle: Finanztip-Berechnung, Stand: September 2026“).
4. **„Redaktionell“ = Doppelprüfung durch Organisation:** Redaktionskodex + Pressekodex,
   wissenschaftlicher Leiter prüft Ergebnisse und Berechnungen mit, Empfehlung entsteht
   *vor* jeglichem Affiliate-Abschluss, Artikel tragen mehrere namentliche Autoren/Experten.
5. **Lesbarkeit ist redaktioneller Auftrag, kein公开es Tool:** „Unsere Texte sollen einfach
   sein“ (Redaktionskodex), Du-Anrede, kurze Absätze, Inhaltsverzeichnis, FAQ,
   Feedback-Widget mit Antwort-Quote. Ein konkretes Lesbarkeits-Tool wird nicht offengelegt.
6. **Frank ist in mehreren Disziplinen bereits vorne** (gemessene Lesbarkeits-Gates,
   Vorlese-Funktion, Belegketten-Box, Methodik-Seite, KI-Offenlegung nach EU-KI-VO).
   Die echten Lücken: **interaktive Rechner, öffentliche Datenreihen („Barometer“),
   event-getriebene Änderungserkennung, sichtbare Feedback-/Vertrauenssignale,
   Autoritäts-Stack jenseits einer Einzelperson.**

---

## 2. Recherche-Ansatz und Grenzen

Geprüft wurden die Stellen, an denen Verlagssysteme ihr Werkzeug normalerweise verraten:

| Kanal | Ergebnis |
|---|---|
| `finanztip.de/ueber-uns/`, `/redaktionskodex/`, Methodik-Blöcke je Artikel | Prozess beschrieben, **keine Tool-Namen** |
| Artikel-Quelltext (Tagesgeld-Ratgeber, Daily-Artikel) | Infrastruktur sichtbar: TYPO3, eigenes Affiliate-Tracking (`tools.finanztip.de/track/?linkcode=…`), eigenes Page-View-Zählpixel (`toolsut.finanztip.de`), VG-Wort-Zählpixel, Google „Bevorzugte Quelle“, dynamische Bildpipeline (`cdn.finanztip.de/_generate/…`) |
| Stellenanzeigen (Personio, Indeed) | ** Ergiebigster Kanal:** AI-Automation-Manager, Data Scientist, „Redaktion – Analyse, Research & KI“ |
| Branchenpresse | IT Boltwise beschreibt Finanztip als datengetriebenes Portal mit KI-gestützter Erstellung + redaktioneller Prüfung; Redakteurs-Beförderung mit KI-Statement |
| Pressebereich | KI-bezogene Studien/Tests (Content), keine internen Tools |

**Grenze:** Finanztip veröffentlicht keine Tool-Liste. Alle Aussagen unten sind mit
Quellen belegt; wo geschlussfolgert wird, steht es dabei. Genannte Produkte wie
„ChatGPT Enterprise“ oder „Jasper“ tauchen **nicht** in Finanztip-Quellen auf –
solche Zuordnungen wären spekulativ.

---

## 3. Befund A – Was finanztip.de über den KI-Einsatz verrät

### 3.1 Inhaltlich aktuell (Content-Frische)

- **Artikel-Kennzeichnung:** Drittwahrnehmung (IT Boltwise, Juni 2026) beschreibt
  Finanztip-Inhalte als **„a.i.-gestützt erstellt und redaktionell geprüft“** – die
  Kennzeichnung der KI-Beteiligung am Artikel ist Teil des Publikationsprozesses.
- **Lebenszyklus- statt Publikationslogik:** Finanztip pflegt Ratgeber als
  „laufende Wissensdatenbank“: systematische Aktualisierung von Kennzahlen und
  rechtlichen Schwellenwerten, Themencluster mit klaren Landingpages, interne
  Verlinkung (IT Boltwise, Juni 2026).
- **Sichtbares Frische-Signal im Titel:** „Tagesgeld Vergleich **09/26**“ – der Monat
  rotiert automatisch mit; dazu „Stand: 25. September 2026“ über dem Artikel.
- **Ziel laut Stellenanzeige (AI-Automation-Manager):** „Veränderungen **früher
  erkennen**, Daten effizienter verarbeiten und unsere Tests **häufiger
  aktualisieren** können – ohne Kompromisse bei Qualität und Nachvollziehbarkeit.“

### 3.2 Rechnerisch aktuell (Zahlen, Konditionen, Berechnungen)

- **Wöchentliches Datenprodukt „Finanztip-Zinsbarometer“:** Entwicklung der Top-Zinsen
  der eigenen Empfehlungen über 12 Monate, abgeglichen mit dem **EZB-Einlagenzins**
  (Quelle je Chart: „Finanztip, Europäische Zentralbank, Stand 23.09.2026“).
  Verteilkanal ist der Freitag-Newsletter – die Datenpipeline speist also Artikel
  *und* Newsletter gleichzeitig.
- **Monatliche Neuberechnung:** Tabelle „dauerhaft gute Zinsen“ = Auswertung, welche
  Banken in den letzten 12 Monaten am häufigsten in den Top 3 des Newsletter-Vergleichs
  standen (monatlicher Takt), mit Anzahl der Platzierungen als nachvollziehbare Metrik.
- **Rechner-Cluster** (`/rechner/`): individuelle Eingaben statt statischer Beispiele
  (Tagesgeld, Rentenlücke, Kaufen vs. Mieten …) – Nutzer rechnet mit *seinen* Zahlen.
- **Organisatorische Rechen-Prüfung:** „Zusammen mit unserem **wissenschaftlichen
  Leiter** werden die Ergebnisse geprüft: Ist das, was unsere Experten erarbeitet
  haben, objektiv? **Stimmen die Berechnungen?**“ (Über-uns-Seite) – eine
  menschliche Second-Opinion-Instanz über der Redaktion.
- **Methodik-Block je Artikel:** „So hat Finanztip XY analysiert“ + „So haben wir
  gerechnet“ – Annahmen, Kategorien und Datenbasis offen gelegt.

### 3.3 Redaktionell aktuell (Prozesse, Rollen, Prüfkette)

- **Redaktionskodex** (Unabhängigkeit, keine wirtschaftlichen Interessen, Pressekodex)
  + **Trennung von Empfehlung und Vermarktung:** Affiliate-Abteilung kontaktiert
  Anbieter erst *nach* Veröffentlichung der Empfehlung.
- **Rollen aus Stellenanzeigen (Stand Sept. 2026):**
  - **(Senior) Product Data & AI Automation Manager** (Test-&-Analyse-Team):
    „Von der **Änderungserkennung** bis zur Aufbereitung konzipierst und erstellst Du
    einen **KI-gestützten Prozess für unsere Produkttests** … etablierst KPIs,
    Qualitätskontrollen, **Stichproben** und belastbare Dokumentation.“
  - **Data Scientist:** „Empfehlungssysteme … KI und Machine Learning … für
    **automatisierte Analyseprozesse oder die Kategorisierung von Inhalten**.“
  - **Werkstudent:in „Redaktion – Analyse, Research & KI“** (bis mind. Juni 2026
    ausgeschrieben): Recherche zu Verbraucher-/Finanzthemen, verständliche
    Aufbereitung, „sauberes Fact-Checking“.
  - **News-Redakteur:in Community-Aufbau** – Community/Forum als Redaktions-Ressource.
- **Personelle Größe:** >100 Mitarbeitende, Redaktion mit 20+ Experten, >1.000
  Ratgeber, >1 Mio. Newsletter-Abonnenten, eigene Studios (Video/Audio).
- **Führung zu KI:** Der neue Leiter des Hauptstadtbüros, Jan Scharpenberg, sieht KI
  als Chance, „Verbraucherinnen und Verbraucher künftig noch besser, **verständlicher
  und relevanter** zu informieren“ (Wirtschaftsjournalist:in, 30.07.2026).

### 3.4 Lesbarkeit

- **Auftrag statt Tool:** Redaktionskodex: „Unsere Texte sollen **einfach** sein und
  unsere Ergebnisse **verständlich**.“ Kein Lesbarkeits-Tool öffentlich benannt.
- **Umsetzung im Produkt:** Du-Anrede, sehr kurze Absätze, Inhaltsverzeichnis je
  Artikel, „Das Wichtigste in Kürze“, FAQ-Abschnitte, Tabellen mit harten Zahlen,
  konkrete Euro-Beispielrechnungen („10.000 € zu 2,5 % = 250 €“).
- **Messung über Nutzer:** Feedback-Widget „War dieser Ratgeber hilfreich?“ mit
  öffentlich aggregierter Quote („81 % fanden diesen Ratgeber hilfreich“, „5.262
  Personen“) + Sicht-Zähler („15,6 Mio. mal angesehen“) – Lesbarkeit wird am
  Nutzerverhalten gespiegelt, nicht an einer Formel.
- **Eigenes KI-Forschungsthema:** Finanztip testet selbst KI-Antworten auf
  Finanzfragen („ChatGPT vs. Finanztip“, „Warum KI nicht Deine Finanzen regeln
  sollte“) – KI-Kompetenz ist Teil der Marken-/Vertrauensstrategie.

### 3.5 Technik-Stack, sichtbar im Quelltext (Kontext, kein KI-Tool)

| Beobachtung | Bedeutung |
|---|---|
| `typo3_pages`-Zählpixel (`toolsut.finanztip.de`) | CMS: **TYPO3** (Enterprise-Publishing, Workflows/Preview-Stufen) |
| `tools.finanztip.de/track/?linkcode=…&pos=…&path=…` | Eigenes **Affiliate-Tracking mit Positionsattribution** je Link |
| `cdn.finanztip.de/_generate/…` | Automatisierte **Bildpipeline** (Größen/Varianten generiert) |
| Google „Bevorzugte Quelle“ (`google.com/preferences/source`) | Teilnahme am Google-Programm **Preferred Source** (Sichtbarkeit in KI-Antworten) |
| VG-Wort-Pixel | Formelle Erfassung texterschlossener Inhalte |
| PHP/Symfony + React/React-Native (Jobanzeige) | App- und Tool-Entwicklung im Haus |

---

## 4. Befund B – Was das für die eigene Strategie bedeutet

**Der Wettbewerbsvorteil von Finanztip ist kein geheimes KI-Werkzeug, sondern drei Dinge:**

1. **Datenpipeline vor Text:** Zahlen (Zinsen, Konditionen) entstehen als *laufend
   gepflegte Datenreihe*; Artikel sind nur die Anzeige dieser Daten. Dadurch sind sie
   automatisch „rechnerisch aktuell“, sobald die Datenquelle taktgenau aktualisiert wird.
2. **Änderungserkennung als Frühwarnsystem:** Statt Artikel nach Kalender
   (45/90/30 Tage) zu prüfen, wird *das Ereignis* (Preisänderung, Gesetzesänderung)
   erkannt und triggert das Update.
3. **Vertrauens-Stack:** 20+ namentliche Experten, Stiftung, Auszeichnungen,
   Feedback-Zahlen, Präsenz in KI-Antworten. Die Leserschaft glaubt der *Organisation*,
   nicht einem Tool.

---

## 5. Vergleich: Finanztip vs. FranksFinanzcheck (Ist-Zustand 28.09.2026)

| Dimension | Finanztip | FranksFinanzcheck | Bewertung |
|---|---|---|---|
| KI-Textproduktion | KI-gestützte Vorarbeit, redaktionelle Prüfung, Kennzeichnung | KI-Redaktion (Claude/Jasper/ChatGPT-Rollen via Groq+Gemini), Entwurfs-Pipeline mit Freigabezwang, menschliche Freigabe | **Parität – Frank disziplinierter (Draft-only-Gate)** |
| KI-Transparenz | Artikel-Hinweis „KI-gestützt + geprüft“ | Impressum-Hinweis EU-KI-VO Art. 50, Methodik-Seite mit 4-Stufen-Diagramm | **Parität; Frank global dokumentierter, Finanztip artikelbezogener** |
| Fakten-/Quellenkette | Quellen-/Stand-Zeile je Tabelle, Methodik-Block je Artikel | `faktencheck`+`quellen` im Frontmatter, Anti-Halluzinations-Allowlist, „Quellen & Faktenstand“-Box, `schema.org/citation` | **Frank führt (GEO/Zitierbarkeit)** |
| Recherche-Rhythmus | Ereignisorientiert (Ziel: „Veränderungen früher erkennen“) | Intervall-basiert (YMYL 45 / Standard 90 / Saison 30 Tage) + wöchentlicher Reach-Brief | **Lücke: Ereignis-Trigger** |
| Rechnerische Aktualität | Wöchentliche Datenreihe (Zinsbarometer), monatlich neu berechnete Tabellen, interaktive Rechner | Statische Werte im Artikeltext/Tabellen, Refresh über Faktenfrische | **Größte Lücke** |
| Lesbarkeits-Sicherung | Redaktionssatz + Nutzerfeedback-Quote | `readability_check.py` (Flesch-Amstad Ø ≥ 62, Floor 55, harte Publish-Gates) + Stil-Guards | **Frank führt (gemessen statt behauptet)** |
| Vorlesen/Barrierefreiheit | – | FF Voice (Studio-Tonspur + Browser-Engine), Kurzfassung | **Frank führt** |
| Nutzerfeedback | Widget mit öffentlicher Quote + Millionen-Sichtzähler | – (nur indirekt via Analytics) | **Lücke** |
| Autorität/E-E-A-T | 20+ Experten, Stiftung, Auszeichnungen, Pressepartner | Einzelperson mit 10+ Jahren Praxis, `erfahrung`-Feld, Backlink-Kampagnen geplant | **Lücke (strukturbedingt) – mit Netzwerk-Modell adressierbar** |
| Community/Dialog | Forum, 1-Mio-Newsletter, App, YouTube, Podcasts | Newsletter (Di/Fr), Mastodon, Pinterest, Audio | **Teil-Lücke: kein Leser-Dialog-Format** |

---

## 6. Handlungsplan – Qualität erreichen und übertreffen

### Horizont 1 – Sofort (≤ 1 Woche, kleine Patches)

**H1 · Per-Artikel-KI-Prüfzeile rendern.**
Finanztip kennzeichnet pro Artikel; Frank weist es derzeit nur global im Impressum aus. Die Daten
liegen bereits im Frontmatter (`ai_generated`, `erfahrung`, `lastmod`): eine Zeile unter
der Meta-Zeile, z. B. *„Mit KI-Unterstützung recherchiert · Zahlen geprüft von Frank
Hartung (Stand: {lastmod})“*. Erweitert `ff_quellen_box.html` bzw. `extend_post_content.html`.
→ E-E-A-T + EU-KI-VO-konform + schlägt Finanztip mit *benannter* Prüfperson.

**H2 · Stand-Zeile je Tabelle (`stand=` / `quelle=`).**
Die Shortcodes `einspartabelle`, `tarifvergleich`, `summe` um optionale Parameter
ergänzen, gerendert als Caption: „Quelle: Bundesnetzagentur · Stand: Sept. 2026“.
Finanztip zeigt das je Tabelle – bei Frank entsteht es automatisch aus `quellen`.

**H3 · Google Preferred Source beantragen.**
Finanztip nutzt aktiv „Bevorzugte Quelle auf Google“. Registrierung im Google
Publisher Center / Search Console; passt zur bestehenden GEO-Strategie
(`schema.org/citation`).

**H4 · Feedback-Badge statt Mio.-Zähler.**
Kleines „War das hilfreich? 👍/👎“ am Artikelende. Ohne neue Infrastruktur machbar über
den bestehenden **newsletter-worker** (Cloudflare Worker nimmt `POST /feedback` auf,
speichert aggregiert, CMS-loses Statik bleibt erhalten). Anzeige optional erst ab
n Stückzahlen (Ehrlichkeit vor Sozialbeweis).

### Horizont 2 – 2 bis 6 Wochen (Systembausteine)

**H5 · Kennzahlen-Register + Frühwarn-Radar (die „Veränderungen früher erkennen“-Maschine).**
Neue SSOT `data/kennzahlen_register.yaml`:

```yaml
- kennzahl: "Grundversorgung Strom Ø ct/kWh"
  quelle: "bundesnetzagentur"
  url: "…"
  rythmus: "monatlich"
  betroffene_slugs: ["2026-…-strom…", "pillar/strom-sparen"]
- kennzahl: "EZB-Einlagenzins"
  quelle: "ezb"
  rythmus: "sitzungsgetriggert (6 Wochen)"
  betroffene_slugs: ["…-tagesgeld-zinsen…"]
```

Ein GitHub-Workflow (Erweiterung von `agent-reach-research.yml`) vergleicht Soll-/Ist-Wert,
öffnet bei Abweichung automatisch ein Issue via `alert_router.py` (Owner: `human`,
Severity nach YMYL-Klasse) und verlinkt die betroffenen Artikel aus `decay_radar`-Queue.
Damit ist Frank **ereignisgetrieben** statt nur intervallgetrieben – exakt das, was
Finanztip mit der AI-Automation-Manager-Rolle baut, bei 0 € Personalkosten.

**H6 · Zwei bis drei interaktive Rechner („Finanztip hat /rechner/ – Frank hat keins“).**
Kandidaten nach Bestandsrelevanz:
1. **Notgroschen-Rechner** (Einkommen → 3–6 Monatsgehälter, Sparplan-Rate bis Ziel)
2. **Strom-Abschlag-Rechner** (Verbrauch → fairer Abschlag, Warnung Nachzahlung)
3. **DSL-Effektivpreis-Rechner** (Bonus + Grundgebühr + Anschlusskosten → €/Monat)

Umsetzung: reines Self-Hosted-HTML/JS (keine externen Assets, keine Cookies –
erfüllt die harten Qualitätsgates automatisch), je mit Methodik-Block
**„So rechnet dieser Rechner“** (Formel + Quelle + Stand) – das übertrifft Finanztips
Transparenz-Niveau. Rechner sind zusätzlich GEO-/KI-Antworten-Magnete.

**H7 · Leserfrage-Format (Community ohne Forum).**
Aus Newsletter-Antworten (bestehen bereits) 1× pro Woche eine beantwortete
„Leserfrage“ als Kurzformat – nutzt `news_writer.py`-Kompakt-Schiene. Schafft Dialog,
E-E-A-T (echte Fragen echter Leser) und Content ohne neue Recherche-Last.

### Horizont 3 – 1 bis 3 Monate (Differenzierung)

**H8 · Öffentliche Datenreihe „FF-Barometer“.**
Äquivalent zum Zinsbarometer, aber in Franks Kern-Nische: z. B. **„FF
Strompreis-Barometer“** (Ø Grundversorgung/arbeitspreis, Quelle BNetzA/Verivox-Spannen)
als selbst-gehostetes SVG-Chart, monatlich automatisch aus `kennzahlen_register`
gespeist, eingebettet in den Strom-Pillar-Hub + Newsletter-Rubrik „Zahlen der Woche“.
→ Dauerhaftes Frische-Signal, Backlink-Asset (passt zu `backlink_assets.yaml`:
„Tabelle mit Quellen + Stand-Datum“), Alleinstellung gegenüber reinen Text-Blogs.

**H9 · Autoritäts-Stack gegen die 20-Experten-Redaktion.**
Frank kann und soll keine 20 Experten einstellen – aber ein **Netzwerk-Modell** bauen:
- 2–3 namentliche **Gast-Prüfer** je Themenwelt (z. B. Versicherungsmakler prüft
  Versicherungs-Pillar quartalsweise; Disclosure-Zeile im Artikel).
- **Zitiert-in-Rubrik** (Presse-/Blogger-Zitationen sammeln und zeigen).
- Presse-Seite mit fertigen PR-Zitaten (Kampagnen existieren bereits in
  `backlink_prospects.yaml`).
- Die Einzelperson als *Marke* betonen: „Jede Zahl von einem Menschen geprüft“ –
  das Anti-Portal-Argument, das Finanztip strukturell nicht kopieren kann.

**H10 · Was NICHT tun (Anti-Pattern).**
- Kein Tool-Kauf als Strategie-Ersatz: Lesbarkeits- und Qualitäts-Gates sind bereits
  besser als das, was Finanztip öffentlich zeigt.
- Keine Titel-Churn-Robotik („09/26“ im Titel) kopieren – bei ~180 Artikeln riskiert
  das CTR-/Ranking-Schwankungen; der Datenstand-Badge (H2) liefert dasselbe Signal
  ehrlicher.
- Kein Forum aufsetzen (Pflegeaufwand, Spam) – H7 deckt den Dialog-Bedarf ab.

---

## 7. Priorisierung nach Wirkung/Aufwand

| # | Maßnahme | Wirkung | Aufwand | Priorität |
|---|---|---|---|---|
| H1 | Per-Artikel-KI-Prüfzeile | Hoch (Vertrauen, AI-VO) | XS | 🔴 sofort |
| H2 | Tabellen-Stand-Zeile | Mittel-Hoch | XS | 🔴 sofort |
| H5 | Kennzahlen-Register + Frühwarn-Radar | Sehr hoch (Kernlücke) | M | 🔴 sofort starten |
| H6 | Interaktive Rechner | Sehr hoch (GEO, Verweildauer) | M | 🟠 Woche 2–4 |
| H4 | Feedback-Widget | Mittel | S | 🟠 Woche 2–4 |
| H8 | FF-Barometer-Datenreihe | Hoch (Backlinks, Frische) | M-L | 🟡 Monat 1–3 |
| H7 | Leserfrage-Format | Mittel | S | 🟡 Monat 1–2 |
| H9 | Autoritäts-Netzwerk | Hoch, langfristig | L (Prozesse) | 🟡 laufend |
| H3 | Google Preferred Source | Mittel | XS | 🔴 sofort |

---

## 8. Quellen

**finanztip.de (primär):**
- Über uns: https://www.finanztip.de/ueber-uns/ (Finanzierungs-/Prüfprozess, „wissenschaftlicher Leiter“, Zähle)
- Redaktionskodex: https://www.finanztip.de/redaktionskodex/
- Tagesgeld-Ratgeber (Beispiel-Artikel): https://www.finanztip.de/tagesgeld/ (Zinsbarometer + „So haben wir gerechnet“ + Tabellen-Stände + Feedback-Widget)
- Daily-Artikel KI: https://www.finanztip.de/daily/warum-ki-nicht-deine-finanzen-regeln-sollte/
- Pressebereich: https://www.finanztip.de/presse/

**Stellenanzeigen (KI-Stack-Belege):**
- (Senior) Product Data & AI Automation Manager: https://finanztip.jobs.personio.de/job/2753169
- Data Scientist: https://finanztip.jobs.personio.de/job/2791500
- Werkstudent:in Redaktion – Analyse, Research & KI (Indeed-Spiegel, Juni 2026): https://de.indeed.com/q-finanztip-jobs.html

**Branchenpresse:**
- IT Boltwise: „FinanzTip im Portrait – Creator-Logik“ („a.i.-gestützt erstellt und redaktionell geprüft“): https://www.it-boltwise.de/finanztip-im-portrait-wie-creator-logik-finanzwissen-planbar-macht.html
- IT Boltwise: „FinanzTip und die Award-Bilanz“ (Content-Lebenszyklus-/Update-Logik): https://www.it-boltwise.de/finanztip-und-die-award-bilanz-wie-ein-seo-finanzportal-seine-relevanz-im-markt-haelt.html
- Wirtschaftsjournalist:in: Scharpenberg/KI-Statement: https://www.wirtschaftsjournalistin.com/singlenews/uid-979200/jan-scharpenberg-rueckt-bei-finanztip-auf/

**Interne Referenzen (eigenes System):**
- `CLAUDE.md` (KI-Statut, Agent-Reach-Leitplanken), `content/methodik/index.md`
- `data/agent_reach/faktenfrische.yaml` (Intervall-Logik), `scripts/readability_check.py`,
  `scripts/decay_radar.py`, `scripts/editorial_scorecard.py`,
  `layouts/_partials/ff_quellen_box.html`, `.github/workflows/ki-redaktion.yml`
