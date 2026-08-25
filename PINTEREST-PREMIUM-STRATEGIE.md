# 🏆 PINTEREST-PREMIUM-STRATEGIE – FranksFinanzcheck

**Profil:** [de.pinterest.com/franksfinanzcheck](https://de.pinterest.com/franksfinanzcheck/) · **Stand:** 25.08.2026
**Erstellt als:** Agentur-Paket „Pinterest Premium" (Profil + Pins + System) · **Nächste Review:** 25.09.2026

---

## 0. TL;DR – was du heute bekommen hast

| # | Deliverable | Status |
|---|---|---|
| 1 | **Masterplan `data/pinterest_plan.yaml` komplett überarbeitet** – 62 Pins auf Premium-Level | ✅ im Repo |
| 2 | **Dieses Strategie-Dokument** mit Copy-Paste-Paketen für Profil & Boards | ✅ im Repo |
| 3 | **3 Premium-Pin-Vorlagen** (1000×1500px, Marken-CD) als Design-Referenz | ✅ `static/images/pins/` |
| 4 | Live-Profil umgestellt (Bio, Boards, Cover) | ⏳ Job für dich (Copy-Paste-Pakete unten, ~20 Min.) |

**Warum 4 nicht automatisiert geht:** Pinterest sperrt jeden Dritt-Zugriff auf Profil-Einstellungen ohne OAuth-Token – Bio, Board-Namen und Board-Beschreibungen änderst du in deinem Dashboard in Minuten (Texte liegen unten fertig). Sobald dein API-Token aktiv ist (`ANLEITUNG-PINTEREST-API.md`), erledigt die Engine das Pin-Posting.

---

## 1. Audit-Befund (25.08.2026)

### 1.1 Was bereits stark ist (weiter so!)

- ✅ **Business-Account + verifizierte Website** (`static/pinterest-e238f.html` liegt im Root – Claim steht)
- ✅ **RSS-Auto-Publish** eingerichtet (Pinterest-freundlicher Feed, 2:3-Cover) – `ANLEITUNG-PINTEREST-RSS.md`
- ✅ **Eigenes Marken-CD** auf allen Covern: Smaragd `#0E5A43` / Gold `#FFB300`, Inter Bold, 1000×1500px (2:3)
- ✅ **Pin-Engine mit Auto-Refresh** (`pinterest_engine.py`, Rotation 60 Tage) + Token-Auto-Refresh
- ✅ **Werbekennzeichnung als Standard** definiert (`*Werbung | …`, max. 3 Hashtags – PINTEREST-SEO-HEALER)

### 1.2 Gefundene Schwächen (alle behoben im neuen Masterplan)

| # | Problem im alten Plan | Beispiel | Fix |
|---|---|---|---|
| S1 | **Massenduplikate** – 62 Pins, aber nur ~15 echte Themen | „5 einfache Frugalismus-Tricks" wortgleich an Tag 1, 7, 13, 19, 26 | 62/62 Pins jetzt individuell (Fresh-Pin-Varianten) |
| S2 | **Mitten im Wort abgeschnittene Beschreibungen** | „…wie Du Standby-" | Vollständige Texte, ≤ 500 Zeichen |
| S3 | **Tippfehler in Keywords & URLs** | „50 30 20 reget", „Internet-Fiat", `pinterest.denrankstinanzcheck` (2× kaputt!) | Alle korrigiert |
| S4 | **4 Pins ohne Typ** (EP/TP leer) | Tag 3, 9, 13, 22 | Alle typisiert: 50 EP / 12 TP |
| S5 | **TP-Pins ohne Werbekennzeichnung** | alle 12 CHECK24-Pins | Alle TP starten mit `*Werbung \|` |
| S6 | **Board-Namen mit Versions-Suffix** | „Günstige Strom- & Gastarife **1**", einmal sogar mit Doppel-Leerzeichen | 6 saubere SEO-Boards (s. Schritt 2) |
| S7 | **Beschreibungen ohne CTA**, Keywords teils generisch | „…Alle Fakten zum" (Abbruch statt CTA) | Jedes Pin: Hook → Nutzen mit Zahl → CTA |

**Auswirkung (warum das Geld kostet):** Pinterest wertet doppelte Bilder + identische Texte als „Re-Pin-Spam" und drosselt die Reichweite des gesamten Kontos. Die kaputten Profil-URLs (S3) hätten Pins mit toten Zielen erzeugt – schlimmstes Signal für den Quality-Score eines jungen Accounts.

---

## 2. SCHRITT 1: Profil auf Premium-Level (Copy-Paste, ~10 Min.)

> **Wo:** de.pinterest.com → Profil → **Einstellungen → Öffentliches Profil bearbeiten**

### 2.1 Anzeigename (max. 65 Zeichen, keyword-besetzt)

```
FranksFinanzcheck | Geld sparen & Tarife clever wechseln
```
*(57 Zeichen – „Geld sparen" und „Tarife wechseln" sind Suchbegriffe; dein Name wird dadurch auch für Nicht-Follower in der Suche auffindbar)*

**Alternative (persönlicher, Marke + Gesicht):**
```
FranksFinanzcheck – Frank Hartung | Geld sparen leicht gemacht
```

### 2.2 Bio (max. 500 Zeichen, zum Kopieren)

```
Dein Praxis-Ratgeber für weniger Fixkosten & mehr vom Leben 💡 Ehrliche Spartipps zu Strom, Gas, DSL, Versicherungen & Budget – verständlich erklärt, mit konkreten Euro-Beträgen. Über 10 Jahre Erfahrung im Tarif-Dschungel. 📌 Jede Woche neue Finanz-Hacks & Checklisten zum Speichern. 👉 Alle Guides: franksfinanzcheck.de (enthält Affiliate-Links)
```

**Warum so:** Keyword-Dichte (Strom, Gas, DSL, Versicherungen, Budget, Spartipps) + Vertrauensanker (10 Jahre) + Posting-Versprechen („jede Woche" = Follow-Grund) + CTA-Link + **proaktive Affiliate-Offenlegung** (Vertrauenssignal für Pinterest-Moderation & Nutzer).

### 2.3 Profil-Checkliste (Einstellungen)

| Punkt | Premium-Standard | Wo |
|---|---|---|
| Account-Typ | **Business-Account** (nicht privat) | Einstellungen → Konto |
| Website-Anpruch | ✅ erledigt (`pinterest-e238f.html`) | Einstellungen → Beanspruchte Konten |
| Profilbild | **Frank-Foto** (nicht nur Logo) – Gesichter schaffen im Finanz-Bereich Vertrauen; Logo als Fallback. ✅ **Fertige Premium-Dateien in `static/images/social/`:** `pinterest-profilbild-marke-1000.png` (Foto + Gold-Ring + Check-Badge, empfohlen) oder `pinterest-profilbild-1000.png` (cleane Studio-Variante); je auch als 400px-Version | Profil bearbeiten → Foto |
| ~~Titelbild~~ | Entfällt – Pinterest bietet KEIN Profil-Titelbild (das ist YouTube/Facebook). Premium-Ersatz: **Board-Cover gezielt setzen** (s. Schritt 3.3) – sie wirken auf dem Profil wie ein Header | — |
| Rich Pins | Aktiviert (Artikel-Pins) – PaperMod liefert OG/JSON-LD bereits; 1× validieren | developers.pinterest.com/tools/url-debugger |

---

## 3. SCHRITT 2: Board-Architektur Premium (Copy-Paste, ~10 Min.)

**Warum umbenennen?** Board-Namen sind Pinterest-SEO-Echtmeat: Der Algorithmus klassifiziert dein gesamtes Konto über Board-Titel + Board-Beschreibungen. „… 1"-Suffixe sehen nach Baustelle aus und verschenken Keyword-Platz.

### 3.1 Mapping alt → neu (Boards einfach umbenennen, Pins bleiben erhalten)

| Alter Board-Name | Neuer Premium-Name |
|---|---|
| Geld sparen & Frugalismus (1) | `Geld sparen im Alltag \| Frugalismus-Tipps` |
| Haushaltskasse & Budgetplanung (1) | `Budget & Haushaltskasse: clever planen` |
| Günstige Strom- & Gastarife 1 (inkl. Doppel-Leerzeichen-Variante) | `Strom & Gas sparen \| Tarife clever wechseln` |
| Internet- & DSL-Hacks 1 | `Internet & DSL \| WLAN-Tipps & Tarife` |
| Reisebudget & Mietwagen 1 | `Günstig reisen \| Reisebudget & Mietwagen` |
| — (NEU anlegen) | `Versicherungen clever wechseln & sparen` |

> Das 6. Board lohnt sich: Dein Blog wächst im Versicherungs-Silo (Privathaftpflicht, Wohngebäude, Kfz-Wechselsaison bis 30.11.). Ein eigenes Board bündelt diese Pins thematisch sauber, statt sie unter „Frugalismus" zu verstecken.

### 3.2 Board-Beschreibungen (max. 500 Zeichen – zum Kopieren)

**Geld sparen im Alltag | Frugalismus-Tipps**
```
Geld sparen im Alltag leicht gemacht: Frugalismus-Tipps, Sparmethoden & Finanz-Hacks, die wirklich funktionieren – von der 24-Stunden-Regel bis zum No-Spend-Weekend. Ehrlich, verständlich, mit konkreten Euro-Beträgen. Ideal für alle, die ohne Verzichtsgefühl jeden Monat 100 € und mehr freischaufeln wollen.
```

**Budget & Haushaltskasse: clever planen**
```
Budgetierung ohne Stress: Hier dreht sich alles um die 50-30-20-Regel, Haushaltsbuch, Notgroschen & cleveres Planen mit dem Gehalt. Mit Beispielrechnungen, Checklisten und Schritt-für-Schritt-Anleitungen für dein Budget – egal ob 1.500 € oder 3.500 € netto. So hast du am Monatsende endlich Geld übrig.
```

**Strom & Gas sparen | Tarife clever wechseln**
```
Stromkosten & Heizkosten senken: Stromfresser finden, Energiefresser stoppen, Strom- und Gastarife clever wechseln – mit Preisgarantie, Wechselbonus und Checklisten zum Abhaken. Dazu verständliche Guides rund um Gasrechnung, Abschlag und Heizperiode. Spartipps mit echten Euro-Beträgen statt leerer Versprechen.
```

**Internet & DSL | WLAN-Tipps & Tarife**
```
Schnelleres Internet ohne mehr zu zahlen: WLAN verbessern, Mesh vs. Repeater, DNS-Tricks und die besten DSL-Tarife mit Wechselbonus. Verständliche Anleitungen für jedes Gerät – von der Fritzbox bis zum Smartphone. Für ein Zuhause ohne Funklöcher und ohne zu teure Verträge.
```

**Günstig reisen | Reisebudget & Mietwagen**
```
Günstig reisen ohne Abstriche: Reisebudget clever planen, Urlaubskasse aufbessern, Mietwagen-Fallen vermeiden und Last-Minute-Schnäppchen sichern. Mit Checklisten für Buchung, Abholung und Rückgabe des Mietwagens plus Spartaktiken für Flüge und Unterkünfte. Mehr Urlaub fürs Geld – jedes Jahr.
```

**Versicherungen clever wechseln & sparen** (NEU)
```
Versicherungen verstehen & wechseln: Kfz-Versicherung zum Stichtag 30.11., Privathaftpflicht, Wohngebäudeversicherung & Co. – was du wirklich brauchst und was du kündigen kannst. Vergleichen, Hunderte Euro sparen und typische Vertragsfallen vermeiden. Ehrlich erklärt, ohne Fachchinesisch.
```

### 3.3 Board-Cover & Reihenfolge

- **Board-Cover:** Feste Cover setzen (Board → „…" → Bearbeiten → Cover). **Fertiges 6er-Set liegt bereit** (25.08.): `static/images/boards/cover-<slug>.png` (1000×1000, quadratisch – Pinterest beschneidet Board-Cover seitlich zum Rechteck, die Vorlagen sind deshalb zentriert-safe designt). Hochladen je Board: Board-Seite → Stift-Symbol/Bearbeiten → „Cover ändern" → Bild hochladen.

  | Board | Datei | Claim auf dem Cover |
  |---|---|---|
  | Geld sparen & Frugalismus | `cover-geld-sparen.png` | „Weniger Fixkosten, mehr vom **Leben**." |
  | Strom & Gas sparen | `cover-strom-gas.png` | „Kleine Rechnung, **warme Wohnung**." |
  | Budget & Haushaltskasse | `cover-budget.png` | „Dein Gehalt. **Dein Plan**." |
  | Internet & DSL | `cover-internet-dsl.png` | „Volles Tempo, **halbe Rechnung**." |
  | Günstig reisen | `cover-reisen.png` | „Mehr Urlaub fürs selbe **Geld**." |
  | Versicherungen | `cover-versicherungen.png` | „Voller Schutz, **faire Preise**." |

  **Design-System:** einheitliches Erscheinungsbild = stärkste Profil-Wirkung – Emerald-Gradient (CD), Gold-Pill-Badge (Boardname), 2-zeiliger Benefit-Claim mit Gold-Akzent im letzten Wort, kreisförmiges Autoren-Medaillon (aus dem Premium-Profilbild, § 2.3) mit Gold-Ring + Check-Badge, Brand-Zeile „✓ FranksFinanzcheck". Dein Gesicht auf jedem Board-Cover = persönliche Marke statt anonymer Sammelboards.
- **Reihenfolge auf dem Profil:** Mit Pins sortieren = größte+stärkste Boards zuerst (Strom & Gas, Geld sparen). Saisonal rotieren: ab September Strom/Gas + Versicherungen nach vorn, ab Januar Reisen.
- **Absolutes No-Go:** Keine leeren Boards (unter 5 Pins) und keine „Gemischt"-Boards – beides verwässert deine Topical Authority.

---

## 4. SCHRITT 3: Pin-Design-System Premium

### 4.1 Spezifikationen

| Element | Premium-Standard | Begründung |
|---|---|---|
| Format | **1000×1500 px, 2:3** (nie breiter als hoch, nie über 1000×2100) | Feed-Optimierung, kein Abschneiden |
| Safe-Zone | 90 px Rand oben/unten frei von Text | UI-Overlays von Pinterest |
| Farben | Emerald `#0E5A43` · Dark `#083A2B` · Gold `#FFB300` · Cream `#F0F5F2` | Bestehendes CD – hohe Wiedererkennbarkeit im Feed |
| Font | Inter Bold (vorhanden), Headline ≥ 72 px, Subline ≥ 40 px | Lesbarkeit auf Smartphone im Feed |
| Marke | Brand-Band unten: ✓ FranksFinanzcheck (wie bisher) | Anti-Diebstahl + Wiedererkennung |
| Dateiformat | JPEG, Qualität 85, < 2 MB | Schnelle Auslieferung |

### 4.2 Die drei Premium-Upgrade-Hebel (gegenüber dem Ist)

Der Ist-Stand (grüne Fläche + Badge + Headline + Brand-Band) ist sauber, aber **austauschbar**. Die drei Hebel, die Premium-Accounts von Amateur-Pins trennen:

1. **Die Spar-Zahl als Design-Anker.** Nichts zieht im Finanz-Feed stärker als eine konkrete Euro-Zahl in Gold: „**−300 €/Jahr**", „**abuso 9,99 €/Monat**" (TP-Pins), „**50 / 30 / 20**" (Erklär-Pins). Die Zahl bekommt die größte visuelle Ebene nach der Headline.
2. **Emotion über Bild-Ebene.** Oberes Drittel: stilisierte Fotomotive/Illustrationen zum Thema (Steckdose, Heizung, Smartphone mit WLAN-Wellen, Auto am Strand). Menschen/Situationen schlagen reine Farbflächen bei Outbound-CTR spürbar – besonders bei „Mietwagen-Fallen" & „Urlaubskasse".
3. **Klarer Pin-Typ pro Template.** Drei Template-Familien reichen für das gesamte Jahr – Konsistenz = Markenwirkung:
   - **T1 „Ersparnis-Pin" (TP):** Pillar-Badge → Headline → **Gold-Pille mit Euro-Betrag** → Brand-Band → dezenter `*Werbung`-Hinweis unten
   - **T2 „Listen-Pin" (EP):** Pillar-Badge → große Zahl („5", „7") → Headline → Mini-Icons der Listenpunkte
   - **T3 „Erklär-Pin" (EP):** einfache Infografik-Ebene (Kreisdiagramm, Pfeile, 3er-Segmente) → Headline

→ Die drei Referenz-Designs liegen in `static/images/pins/` als visuelle Vorlage für `scripts/generate_covers.py` oder deinen Designer/Canva.

### 4.3 Design-Do's & Don'ts

- ✅ Ein Kern-Keyword **auf dem Bild** (Pinterest liest Text-Overlay mit)
- ✅ Kontrast Gold-auf-Emerald nur für Akzente (Badge, Zahlen) – nie für Flächen
- ✅ 3–5 Wörter Hauptzeile ideal, max. 3 Zeilen
- ❌ Keine Clickbait-Irritationen („Du wirst nicht glauben …") – Pinterest drosselt
- ❌ Keine Telefonnummern/QR-Codes/Wasserzeichen-Fremdlogos (CHECK24-Logo NICHT aufs Pin-Bild!)
- ❌ Keine Screenshots aus dem CHECK24-Portal (Markenrecht; TP-Pin bleibt im eigenen CD)

---

## 5. SCHRITT 4: Pin-Copy-System Premium (schon im Masterplan eingebaut)

### 5.1 Titel-Formeln (≤ 100 Z., Feed-sichtbar ~40 Z.)

```
[Keyword zuerst]: [Zahl] [konkreter Nutzen]        → "Stromfresser im Haushalt entlarven: Die 5 größten Energiediebe"
[Keyword] + [Saison/Dringlichkeit]                  → "Kfz-Versicherung wechseln bis 30.11.: Jetzt vergleichen & sparen"
[Ergebnis-Frage]                                    → "3 Monatsgehälter? So groß sollte dein Notgroschen wirklich sein"
[Versprechen mit Zahl]                              → "Mit diesen 5 Frugalismus-Tricks sparst du jeden Monat dreistellig"
```

### 5.2 Description-Formel (≤ 500 Z.)

**Educational-Pin (EP → Blog):**
```
[Hook-Frage oder Schmerz-Aussage] + [1–2 Kern-Keywords natürlich eingebaut] + [konkreter Nutzen mit Zahl/Format] + [CTA]
→ "Welche Geräte treiben deine Stromrechnung wirklich in die Höhe? … inklusive Euro-Beträgen pro Jahr … Jetzt checken und bis zu 300 € im Jahr sparen."
```

**Transactional-Pin (TP → CHECK24, *zwingend mit Kennzeichnung*):**
```
*Werbung | [Dringlichkeit/Saison-Hook] + [Ersparnis in €] + [Risiko-Abbau: kostenlos / Kündigung-Service / Dauer] + [CTA]
→ "*Werbung | Stichtag 30.11. nicht verpassen: Bis dahin kannst du deine Kfz-Versicherung wechseln … Jetzt Tarife durchrechnen …"
```

### 5.3 Hashtag-Regel

Max. **3 Hashtags, ASCII-only** (Umlaute killen die Hashtag-Indexierung: `#sparen` statt `#günstig-reisen`). Herleitung aus dem `keywords`-Feld des Masterplans – die Engine hängt sie automatisch an.

---

## 6. SCHRITT 5: Affiliate-Compliance (Pinterest × deutsches Recht)

| Regel | Umsetzung bei FranksFinanzcheck |
|---|---|
| Pinterest erlaubt Affiliate-Links, **verbietet aber Tarnung** | TP-Pins verlinken direkt auf `check24.de/...` – KEINE URL-Shortener, keine mehrstufigen Redirects |
| Offenlegung der Affiliate-Natur | Jedes TP-Pin startet mit `*Werbung |` (im Masterplan eingebaut) + Bio enthält „(enthält Affiliate-Links)" |
| Kein Spam-Verhalten | Max. 10 Pins/Tag, keine Duplikat-Flut → dank 62 einzigartiger Pins erledigt; Fresh-Pins statt Repins derselben URL am selben Tag |
| Ausgewogenheit | 50 EP : 12 TP ≈ **80 % Mehrwert / 20 % Monetarisierung** – genau das Mischungsverhältnis, das Affiliate-Accounts vor Drosselung schützt |
| Keine irreführenden Sparversprechen | Euro-Angaben immer als „bis zu" / „mehrere hundert Euro möglich" (im Masterplan durchgängig so gelöst) |
| Blog-Seite | Disclaimer bereits brand-gelockt ✅ |

---

## 7. SCHRITT 6: Posting-System & Saisonkalender

### 7.1 Kadenz (ab Aktivierung des API-Tokens)

| Parameter | Premium-Vorgabe |
|---|---|
| Pins/Tag | **2 frische Pins** (1 EP + im Wechsel EP/TP), nie mehr als 5 |
| Posting-Tage | Mo/Mi/Fr – synchron zur Content-Engine (frischer Blog-Artikel = frischer Pin = maximale Fresh-Signale) |
| Uhrzeit | 18–21 Uhr (deutsche Pinterest-Primetime), Sonntag Nachmittag für Reise-Pins |
| Refresh | Pins > 60 Tage mit NEUEM Bild + neuer Description neu pinnen (Engine markiert Kandidaten automatisch) |
| RSS-Auto-Publish | bleibt AN – liefert organisch die Artikel-Pins; API-Pins setzen die optimierten Masterplan-Texte obendrauf |

### 7.2 Saisonkalender (Pinterest läuft 30–45 Tage VORAUS – diese Pins brauchen Vorlauf!)

| Zeitraum | Prio-Pins | Warum jetzt |
|---|---|---|
| **Sep 2026** | Heizperiode (EP), Gas-Preisgarantie (TP), goldenen-September-Mietwagen (TP) | Heizsaison-Suche startet; Reise-Nebensaison |
| **Okt 2026** | Kfz-Wechsel (TP) Aufbau, Stromfresser/Heizkosten (EP), DSL-Bonus (TP) | Kfz-Stichtag 30.11. – Pinterest-Vorlauf! |
| **Nov 2026** | **Kfz-Stichtag 30.11. (TP, Hauptkampagne)**, Black-Friday-DSL (TP), Budget-Herbst (EP) | Absoluter Konversions-Peak des Jahres |
| **Dez 2026** | Gasrechnung/Abschlag (EP), Jahresbudget (EP), Notgroschen (EP) | „Neues Jahr, neue Finanzen"-Suchen starten |
| **Jan/Feb 2027** | 50-30-20 (EP), Girokonto (TP), Urlaubsplanung/Flüge (TP) | Vorsätze + Buchungssaison – Reise-Pins 45 Tage vor Osterferien |

---

## 8. SCHRITT 7: Analytics & KPI-System

**North Star = Outbound-Clicks** (nicht Impressions!). Impressions sind Eitelkeit, Outbound-Clicks sind CHECK24-Provision.

| KPI | Zielwert (90 Tage) | Messpunkt |
|---|---|---|
| Outbound-CTR | ≥ 1,5 % (Finanz-Nische: gut 1–3 %) | Pinterest Analytics → Pins |
| Saves/Outbound-Verhältnis | ≤ 10:1 | Analytics → Übersicht |
| Top-10-Pins-Anteil | monatlich identifizieren & in neuem Design re-pinnen | Analytics |
| TP-Anteil an Outbound-Clicks | ≥ 30 % | UTM: Links in `scripts/check24_links.yaml` um `?utm_source=pinterest&utm_medium=social&utm_campaign=<pin-slug>` ergänzen |

**Monatsritual (letzter Werktag):** Analytics exportieren → 3 Top-Pins analysieren (Warum? Bild? Titel?) → 3 Flop-Pins mit neuem Titel+Bild refresh-pinnen → Masterplan ergänzen. Pinterest-Trends (trends.pinterest.com) 45 Tage vor jeder Saison gegen den Plan prüfen.

---

## 9. 30/60/90-Tage-Roadmap

**Tage 1–30 (Fundament):**
- [ ] Profil: Name, Bio, Foto, Cover (Schritt 2, 20 Min.)
- [ ] Boards umbenennen + Beschreibungen einsetzen (Schritt 3, 20 Min.)
- [ ] API-Token aktivieren (`ANLEITUNG-PINTEREST-API.md`) → Engine postet Masterplan-Pins automatisch
- [ ] Baseline: Impressions/Outbound-Clicks notieren

**Tage 31–60 (Design-Hebel):**
- [ ] Cover-Generator auf T1–T3-Templates erweitern (Referenz: `static/images/pins/`)
- [ ] Erste Refresh-Runde Top-5-Pins mit Premium-Design
- [ ] Kfz-Kampagne (TP + 3 EP) für Stichtag 30.11. ausrollen

**Tage 61–90 (Skalieren):**
- [ ] Flop-Pins systematisch neu pinnen (neues Bild + neuer Titel – niemals identisch)
- [ ] UTM-Auswertung: Welche Board/Template-Kombination bringt CHECK24-Klicks?
- [ ] Masterplan-Zyklus 2 planen (Winter-Themen: Stromsparen im Winter, Staubsauger-Roboter-Strom, Sofort-Kfz-Wechsel-Sonderkündigung)

---

## 10. Changelog Repo (25.08.2026)

- `data/pinterest_plan.yaml` – 62 Pins Premium-überarbeitet (s. Tabelle 1.2, S1–S7)
- `PINTEREST-PREMIUM-STRATEGIE.md` – dieses Dokument
- `static/images/pins/premium-pin-stromfresser.png` – Template-Referenz T2 (Listen-Pin, EP)
- `static/images/pins/premium-pin-50-30-20.png` – Template-Referenz T3 (Erklär-Pin, EP)
- `static/images/pins/premium-pin-stromwechsel.png` – Template-Referenz T1 (Ersparnis-Pin, TP)
- `scripts/generate_covers.py` – **Premium-Upgrade (DESIGN_VERSION 3)**
  - **Pillar-Badges** statt generischem „GELD SPAREN"-Badge: aus Frontmatter `pillar:` (Fallback: Keyword-Scan) → „STROM & GAS SPAREN", „INTERNET & DSL", „VERSICHERUNGEN", „GÜNSTIG REISEN", „KONTO & FINANZEN", „GELD SPAREN & FRUGALISMUS" *(behebt den Audit-Fund: das DSL-Cover trug fälschlich ein Frugalismus-Badge)*
  - **Gold-Spar-Pille** unter dem Titel: automatisch aus `description`/`title` erkannt („bis zu 800 € …" nur mit Spar-Kontext; Zeitraum „im Jahr/im Monat" präzise; **Dedupe:** steht der Betrag schon golden im Titel, entfällt die Pille) – überschreibbar per Frontmatter `savings: "bis zu 300 € im Jahr sparen"`
  - **Gold-Zahlen im Titel** (Listen- und Betrags-Akzente), Trust-Line „UNABHÄNGIG · VERSTÄNDLICH · MIT ECHTEN ZAHLEN", dezente Vignette
  - **Design-Drift-Erkennung** (`data/covers_manifest.json`): Ändern sich Badge/Pille/Version, rendert der nächste Lauf automatisch neu
  - Rollout 25.08.: **alle 25 Bestands-Cover neu gerendert** (17 mit Spar-Pille), `check_covers.py`: 0 Probleme, 0 Stale, 0 Brand-Verstöße
- **UTM-Attribution (Zwei-Ebenen-Modell, Details §11):**
  - `scripts/check24_links.yaml` – alle 19 Affiliate-Links mit kanalneutraler Kategorie-Kampagne (`utm_campaign=<kategorie>`)
  - `static/go/*/index.html` – alle 19 Gateway-Weiterleitungen via `affiliate_shield.py --fix` neu generiert (0 Artikel angetastet, idempotent)
  - `scripts/pinterest_engine.py` + `scripts/generate_pins.py` – gepinnte Artikel-Links mit `PIN_UTM` (`utm_source=pinterest`)
  - `layouts/_default/rss.xml` – Item-Links mit RSS-Kampagnen-UTM (GUID bleibt reine Permalink = stabile Pin-Identität)
  - Geprüft: `link_guard.py` ✅ alle internen Links OK · Offline-Gates ✅
- **Premium-Profilbild angelegt (25.08.):** Aus `static/images/frank-hartung.jpg` (800×800-Passfoto) wurde ein Studio-Porträt auf Marken-Emerald mit Kopffreiheit fürs Kreis-Format gebaut → `static/images/social/pinterest-profilbild-1000.png` / `-400.png` (clean) und `pinterest-profilbild-marke-1000.png` / `-400.png` (mit Gold-Ring + Check-Badge, CD-verzahnt mit dem Mastodon-Avatar). Upload: Pinterest → Einstellungen → Öffentliches Profil bearbeiten → Foto ändern.
- **Premium-Board-Cover-Set mit Autoren-Foto angelegt (25.08.):** 6 einheitliche Board-Cover 1000×1000 in `static/images/boards/` (`cover-geld-sparen`, `cover-strom-gas`, `cover-budget`, `cover-internet-dsl`, `cover-reisen`, `cover-versicherungen`) – Emerald-Gradient, Gold-Pill-Badge (Boardname), 2-zeiliger Benefit-Claim mit Gold-Akzent, kreisförmiges Foto-Medaillon aus `pinterest-profilbild-1000.png` (Gold-Ring + Check-Badge, nahtlos in den Pad-Gradient eingebettet), Brand-Zeile. Font-PACT eingehalten (nur Inter-Bold), flächenfrei ohne Overlay-Muster, zentriert-safe für Pinterest' Cover-Beschnitt. Details + Claims: § 3.3.

*Kompatibilität geprüft: `category_from_pin()` in `scripts/generate_drafts.py` mappt alle neuen Board-Namen korrekt (strom/gas → strom, internet/dsl → dsl, reisebudget/mietwagen → mietwagen); `check_uniqueness.py` läuft unverändert; Brand-Gate C2/C2b unverletzt (Band, Gold-Linie, Häckchen, Wortmarke an geheiligten Positionen); ROUTE_CONTRACT/Tracker-Checks sind substring-tolerant, PID/aid/deep stehen unverändert vorn in der Query.*

---

## 11. ANHANG: UTM-Konvention & „Welcher Pin bringt Provision?"

Attribution läuft bewusst in **zwei getrennten Ebenen** (Industrie-Standard — Netzwerk-Ebene vs. Analytics-Ebene), damit keine falsche Kanal-Zuordnung entsteht:

### Ebene 1: Kategorie im Netzwerk (CHECK24/Tarifcheck-Dashboard)

Alle Affiliate-Links tragen kanalneutral:
```
utm_source=franksfinanzcheck · utm_medium=affiliate · utm_campaign=<kategorie>
```
→ Im Partner-Dashboard wertest du Klicks/Abschlüsse **je Kategorie** aus (`utm_campaign=strom`, `…=kfz-versicherung`, `…=dsl` …). So siehst du, ob z. B. die Kfz-Herbstkampagne die Conversion liefert.

### Ebene 2: Kanal & Pin in Umami (Analytics)

- Pinterest-Engine & RSS pinnen Artikel-Links mit `?utm_source=pinterest&utm_medium=social&utm_campaign=pins` bzw. `…=rss-autopublish`.
- **Auswertung in Umami:** Reports → **UTM** → `utm_source=pinterest` zeigt Sessions, Engagement und Top-Seiten pro Pin. Da jeder Pin genau einen Artikel verlinkt, identifiziert die Landingpage im Seiten-Report den Pin eindeutig.
- **Pin → Provision lesen:** Umami sagt dir *welcher Pin Besucher brachte* (Seite + Event `affiliate_click` mit Thema, A5 im Shield), das Partner-Dashboard sagt dir *welche Kategorie Geld brachte*. Wo beide Spitzen zeigen, steckt dein Gewinner-Pin.

### ⚠️ Regeln (wichtig)

1. **TP-Pins NIEMALS nackt auf `check24.de` pinnen** — ohne Tracker keine Provision! Für manuelle Transactional-Pins immer die eigene Gateway-URL nutzen: `https://franksfinanzcheck.de/go/<kategorie>/` (eigene Domain, kein Shortener → Pinterest-Konform + PID sicher).
2. **Fail-safe aktiv:** Der Wochen-Wächter (`affiliate_health.py`, ROUTE_CONTRACT) prüft die Tracker weiterhin wöchentlich E2E. Sollte ein Netzwerk die UTM-Parameter je ablehnen, „heilt" der Wächter auf den bekannten Zustand zurück — PID/aid/deep stehen unverändert am Anfang der Query, Tracking kann nicht brechen. *(Hinweis 25.08.: Sandbox-Netz blockierte Live-E2E per TLS – die nächste reguläre Wochenwache verifiziert die UTM-Links live; bei Problemen greift der Fallback automatisch.)*
3. **GUID im RSS bleibt UTM-frei** — sonst denkt Pinterest, alte Artikel seien neu und wirft dein Pin-Archiv durcheinander.
