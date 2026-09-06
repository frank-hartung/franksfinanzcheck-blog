# 🏆 BACKLINK-PREMIUM-STRATEGIE – FranksFinanzcheck

**Stand:** 31.08.2026 · **Rolle:** Agentur + Pinterest + Affiliate · **Nächste Review:** 30.09.2026
**Scout:** `scripts/backlink_automation.py` · **Wochenpack:** `BACKLINK-REPORT.md` · **CRM:** `data/backlink_state.json`

---

## 0. TL;DR – was sich heute ändert

| # | Deliverable | Status |
|---|---|---|
| 1 | **Doktrin 2026:** verdienen statt sammeln. Linktausch, Verzeichnisse, Farmen = raus | ✅ |
| 2 | **7 Kanäle** statt 1 Generic-Mail: Community, Gastbeitrag, Digital PR, Resource, Pinterest-Embed, Podcast, Partnerschaft | ✅ |
| 3 | **Scout neu:** Scoring (Passung × DA × Saison / Aufwand), Live-Artikel-Match, Typ-Templates, Wochenpack à 5 | ✅ |
| 4 | **CRM** in `data/backlink_state.json` – die kuratierte YAML wird nicht mehr zerschrieben | ✅ |
| 5 | **6 Linkable Assets** als Magneten (Kfz-Kalender, Stromfresser-Checkliste, Budget-Vorlage, …) | ✅ `data/backlink_assets.yaml` |
| 6 | **Saison-Kampagnen** Kfz 30.11. / Heizperiode / Black-Friday-DSL – aligned mit Pinterest | ✅ |
| 7 | **Affiliate-safe:** nie `/go/` pitchen, nie Exact-Match „CHECK24“, nie nackte Partner-URLs | ✅ |

**Was du diese Woche tust (15+15+15 Min.):** Abschnitt 8 und das aktuelle Wochenpack in `BACKLINK-REPORT.md`. Der Bot sendet **nichts** – das bleibt dein Qualitäts-Gate.

---

## 1. Audit des alten Systems (warum das kein Premium war)

Der Scout vom 07.08. hat 15 Opportunities und Copy-Paste-Mails geliefert. Alle 15 standen drei Wochen später noch auf `neu`. Das lag nicht an Faulheit – die Texte waren nicht sendbar.

| Schwäche | Beweis | Premium-Fix |
|---|---|---|
| **Ein Template für alles** | Reddit, Verzeichnis, Gastbeitrag, Trustpilot – alle „Hallo X-Team, Gastbeitrag/Vorschlag“ | 8 Renderer, je Typ |
| **Falscher Artikel** | DNS-Artikel an Finanzfluss / Blogger.de | `preferred_slug` + Keyword-Scoring, Drafts ausgeschlossen |
| **`fn`-Bug** | `load_articles()` nutzte undefiniertes `fn[:-3]` | `slug_of()` aus `post_utils` |
| **Linktausch als Taktik** | Sparblog24 in der Prio-Liste | Score = 0, Status `ungeeignet` (Google: *excessive link exchanges*, 2026 domain-level) |
| **Verzeichnis-Spam** | Blogger.de, Geld.de/blog, Sparwelt | retired, Begründung im YAML |
| **Kein CRM** | YAML wurde jede Woche dump’t, Status nie gepflegt | State-Datei, `--mark` / `--note` |
| **Kein Saisonhebel** | Kfz-Stichtag 30.11. kam in keinem Pitch vor | Kampagnen + Seasonal-Boost 1.6 |
| **Pinterest = 0 im Linkgraph** | Pins als Traffic gedacht, nie als Embed-Magnet | Kanal `pinterest` = Infografik-Embeds, nicht Pin-PageRank |
| **Ziele auf `/go/` denkbar** | Affiliate-Seiten sind thin + `rel=sponsored` | Harte Regel: nur Ratgeber-URLs |

**Google 2026 (SpamBrain, kontinuierlich):** Guest-Post-Farmen, bezahlte Platzierungen ohne `rel=sponsored`, Reciprocal-Schemes und KI-Massen-Bylines werden nicht „ein bisschen weniger wert“ – sie können die **ganze Domain** markieren. Ein junger Affiliate-Blog überlebt das nicht.

Deshalb die Doktrin:

> Ein Link zählt nur, wenn ein Mensch ihn auch setzen würde, wenn es Google nicht gäbe.

---

## 2. Die Premium-Doktrin (Agentur, 7 Regeln)

1. **Editorial > Directory.** Eine Byline oder ein Journalisten-Zitat schlägt 30 Katalog-Einträge.
2. **Relevanz > DA.** Ein dofollow von Sparkonto.org (Tagesgeld) ist mehr wert als ein nofollow von einem allgemeinen PR-Verteiler – und beides schlägt einen unthematischen DA-70-Kauf.
3. **Asset first, Pitch second.** Ohne Stromfresser-Checkliste / Kfz-Kalender bleiben PR-Mails Bitstellen. Mit Asset werden sie zur Quelle.
4. **Pinterest verkauft, Google moatet.** Pins bringen Outbound-Klicks (CHECK24). Backlinks halten Rankings, wenn Pinterest-Sessions kommen. Beide Kanäle füttern dieselben Landingpages.
5. **Affiliate-CTA bleibt hinter dem Ratgeber.** Graph: `fremde Seite → /posts/<slug>/ → /go/<kategorie>/`. Nie andersrum.
6. **Anker-Text natürlich.** Marke (`FranksFinanzcheck`), Thema (`Kfz-Versicherung Stichtag 30.11.`), URL, generisch. **Verboten:** Exact-Match „CHECK24 Vergleich“, „günstigster Strom“.
7. **Kapazität 5/Woche.** Mehr Outreach = erkennbares Schema. Weniger = keine Bewegung. 5 ist Agentur-Kadenz für eine Domain dieses Alters.

---

## 3. Die 7 Kanäle (in dieser Reihenfolge skalieren)

### 3.1 Community – Traffic + E-E-A-T (kein PageRank-Wunder)

Finanztip Community, r/Finanzen, r/de_EDV, Gutefrage, Stiftung Warentest Community, LinkedIn.

**Premium-Verhalten:** Profil mit Klarnamen. 10 nützliche Antworten, bevor der erste Link fällt. Link nur, wenn die Frage eine Anleitung verlangt.

**Warum trotz nofollow/ugc:** Referral-Sessions (messbar in Umami), Branded Search, Autor als Entity. Google braucht den Menschen hinter dem KI-Blog – Community ist der billigste E-E-A-T-Beweis.

**Anti-Muster:** Serienkommentare mit identischem Link, „schaut mal meinen Blog an“, Finanztip-Threads mit Affiliate-URLs.

### 3.2 Digital PR – der härteste Hebel 2026

Versicherungsbote, CHIP, COMPUTER BILD, t-online Ratgeber, Pressebox (1× pro Saison), Stretch: FOCUS, heise.

**Premium-Verhalten:** Kein „Darf ich einen Gastbeitrag schreiben?“. Stattdessen **3 fertige Zitate** (Frist / Fehler / Einordnung), 80–120 Wörter, Quellenzeile „Frank Hartung, FranksFinanzcheck“. Journalisten kopieren, sie recherchieren nicht für einen unbekannten Blog.

**Saisonfenster (jetzt):** Kfz-Stichtag 30.11. – Pitch **ab 01.09.**, weil Redaktionen 4–6 Wochen Vorlauf haben. Parallel Heizperiode (Gaspreisgarantie).

**Pressebox/openPR:** Eine sachliche Service-Meldung, dann Schweigen. Dauerfeuer = Pressemitteilungs-Spam, den SpamBrain kennt.

### 3.3 Gastbeitrag – nur exklusiv, nur Nachbar-Nische

Sparkonto.org, MeinGeldBlog, Utopia.de, Smarticular. Finanzfluss **nur** mit Originaldatensatz.

**Premium-Verhalten:** Exklusiver Winkel, den *deren* Leser brauchen und den *du* noch nicht live hast. 1 kontextueller Link + Bio. **Kein Republish** des Live-Artikels (Duplicate Content, Scaled-Content-Risiko).

**Affiliate im Gasttext:** keine `/go/`-Links, keine CHECK24-CTAs. Der Host würde es ablehnen, Google würde es als Link-Schema lesen.

### 3.4 Resource / Roundup – nur kuratierte Listen

Eine Mail an eine redaktionelle „Beste DE-Finanzblogs“-Seite: *euch fehlt die Fixkosten-Nische neben den ETF-Blogs*. Wenn die Seite ein Formular-Katalog ist → skip.

### 3.5 Pinterest – Traffic-Maschine, Backlinks über Embeds

Pinterest-Pins selbst sind **nofollow**. Wer Pins als „Backlinks“ zählt, misst falsch.

**Die drei Premium-Hebel:**

| Hebel | Wirkung | Wer |
|---|---|---|
| **Infografik-Embed** | Anderer Blog bettet die Grafik ein → dofollow + natürlicher Anker | Digital-PR-Empfänger, Haushaltsblogs |
| **Pin → Artikel → `/go/`** | Outbound-Klicks, Rankingsignale durch Engagement | Pinterest-Engine (schon gebaut) |
| **Creator-Collab** | Idea-Pin / Board-Beitrag, jeder verlinkt seinen Guide | 2–3 DE-Creator Haushalt/Sparen |

Regel bleibt: `Pin → eigener Artikel → Affiliate-CTA`. Nie Profil-Sackgasse, nie nacktes check24.de.

Design-System (bereits Premium): 1000×1500, Emerald/Gold, Spar-Zahl als Anker, `*Werbung |` auf TP-Pins. **Neu:** Quellenzeile „Grafik: FranksFinanzcheck“ auf jeder Infografik, die das Haus verlassen darf.

### 3.6 Podcast – Shownotes = editorial dofollow

Pitch-Winkel, den ETF-Podcasts nicht haben: **Fixkosten vor dem Sparplan.** Drei Episoden-Ideen, 90-Sekunden-Bio, drei Soundbites. Shownotes-Link auf den Guide, nicht auf `/go/`.

### 3.7 Partnerschaft – Test der editorialen Unabhängigkeit

CHECK24-Partner (Co-Assets, nicht Forum-Spam). Ein Haushalts-/Familienblog, dem du das Tarif-Kapitel lieferst.

**Test:** Würde der Link auch existieren, wenn der andere nicht zurückverlinkt? Wenn nein → nicht machen. Google 2026 unterscheidet nicht zwischen „nett gemeintem Tausch“ und Schema, sobald Volumen + Timing korrelieren.

---

## 4. Linkable Assets (ohne die bleibt PR Bitstellen)

Quelle: `data/backlink_assets.yaml`. Reihenfolge = Impact × Saison.

| Prio | Asset | Warum jetzt | Aufwand |
|---|---|---|---|
| 1 | **Kfz-Wechselsaison-Kalender 2026** | Stichtag 30.11., Redaktionen brauchen ihn jedes Jahr | 3 h |
| 2 | **Stromfresser-Checkliste (€/Jahr)** | Evergreen-Zitatmagnet für CHIP/Haushaltsblogs | 2 h |
| 3 | **Gaspreisgarantie-Entscheidungsbaum** | Heizperiode läuft | 3 h |
| 4 | **„Was kostet der Haushalt 2026?“-Tabelle** | Originaldaten = härtester Editorial-Link 2026. Nur mit echten Quellen (Destatis, Marktspannen) – **keine erfundenen Preise** | 4 h |
| 5 | **50-30-20-Vorlage** | Januar-Vorsätze + Pinterest-Saves | 2 h |
| 6 | **DSL-Wechsel-Checkliste** | Black Friday / Jahresende | 2 h |

Jedes Asset braucht: Stand-Datum, Quellenzeile, 1000×1500-Pin, 1200×628-Press-Cut, Einbett-Hinweis auf der Artikelseite. Erst dann pitchen.

---

## 5. Pinterest × Backlinks × Affiliate (das Dreieck)

```
          Pinterest-Pin (nofollow, Traffic)
                    │
                    ▼
          Ratgeber /posts/<slug>/     ◄── fremde Seite (dofollow, SEO)
                    │
                    ▼
          CTA /go/<kategorie>/  (rel=sponsored, Conversion)
```

- **Pinterest-Analytics** sagt, welcher Pin Outbound bringt (North Star bleibt Outbound-CTR ≥ 1,5 %).
- **Umami** sagt, welche Referral-Domain Sessions + `affiliate_click` bringt.
- **GSC** sagt, welche Domain als Link zählt.
- Wo alle drei Spitzen zeigen, liegt der Gewinner – den als Asset/Pin/PR verdoppeln.

**Affiliate-Manager-Regeln (Netzwerk + UWG):**

- TP-Pins und Gastbeiträge nie als getarnte Werbung.
- `rel=sponsored` auf bezahlten/partnerischen Links (Gateway tut das bereits).
- Kein Linkkauf „damit die Kfz-Seite rankt“ – ToS von CHECK24/Awin + Google.
- Co-Content mit dem Partnerprogramm: Datencharts mit Quellenangabe, nicht Sitewide-Footer.

---

## 6. Anker-Text- und Ziel-Policy

| Ziel-URL | Wann | Anker |
|---|---|---|
| `franksfinanzcheck.de/` | Marken-Erwähnung, Bio | FranksFinanzcheck |
| `/posts/<slug>/` | 90 % aller Pitches | Thema + Nutzen („Kfz-Versicherung bis 30.11. vergleichen“) |
| `/pillar/<welt>/` | Roundups, „Themenwelt“ | „Ratgeber Strom & Gas“ |
| `/go/<kat>/` | **nie im Outreach** | — |
| check24.de/… | **nie** | — |

Mischung über 90 Tage: ~40 % Marke/URL, ~40 % thematisch-neutral, ~20 % teil-exakt. Kein Cluster identischer Anker von verschiedenen Domains in derselben Woche.

---

## 7. Pipeline & Scout (so arbeitet die Automatik)

```
data/backlink_prospects.yaml     ← kuratiert, Scout schreibt sie NICHT
data/backlink_assets.yaml        ← Magneten
data/backlink_state.json         ← CRM (Status, last_checked, Notizen)
        │
        ▼
scripts/backlink_automation.py   ← Mo 11:00 MESZ (backlink-weekly.yml)
        │
        ├─ Selftest (Exit 2 = Sabotage-Stop)
        ├─ HTTP-Reachability (kein Auto-Submit)
        ├─ Score + Live-Artikel-Match
        └─ BACKLINK-REPORT.md    ← Wochenpack, Copy, Pipeline
```

**Status:** `neu → vorbereitet → kontaktiert → follow-up → gewonnen | abgelehnt | pausiert | ungeeignet`

```bash
python3 scripts/backlink_automation.py --selftest
python3 scripts/backlink_automation.py              # Scout + Report
python3 scripts/backlink_automation.py --no-net     # offline
python3 scripts/backlink_automation.py --mark finanztip-community=kontaktiert
python3 scripts/backlink_automation.py --note finanztip-community="3 Antworten, 1 Link"
```

Follow-up: bei Gastbeitrag/PR nach 7/5 Tagen **eine** 4-Zeilen-Mail, dann Schluss. Dreimal nachfassen ist Spam.

---

## 8. Wochenritual (KW 36 und dauerhaft)

**Gesamt 45 Minuten, verteilt auf Mi/Do/Fr – parallel zur Content-Kadenz Mo/Mi/Fr.**

| Slot | Minuten | Quelle (aktuelles Pack steht im Report) |
|---|---|---|
| Mi | 15 | Community: 2 echte Antworten (Finanztip oder r/Finanzen), Thema der Saison (Kfz/Gas) |
| Do | 15 | 1 Digital-PR-Mail (Versicherungsbote oder t-online) **oder** 1 Gastbeitrag-Pitch (Sparkonto.org) |
| Fr | 15 | Pinterest: 1 Infografik-Fortschritt **oder** 3 manuelle Pins aus der Queue (18–21 Uhr) + Brand-Search auf Unlinked Mentions |

**Diese Woche bewusst nicht:** Verzeichnisse, Linktausch, OpenPR-Dauerfeuer, Finanzfluss ohne Asset, LinkedIn-Token-Baustelle.

---

## 9. 30 / 60 / 90 Tage

**Tage 1–30 (Fundament, Sept)**
- [ ] Kfz-Kalender-Asset bauen und auf den Kfz-Artikel + Pin
- [ ] Finanztip-Profil + 8 hilfreiche Antworten (Ziel: 1 kontextueller Link)
- [ ] 2 PR-Pitches (Versicherungsbote, t-online) mit fertigen Zitaten
- [ ] 1 Gastbeitrag-Pitch Sparkonto.org (exklusiver Tagesgeld-Winkel)
- [ ] CRM pflegen (`--mark`), nicht im Kopf

**Tage 31–60 (Magneten, Okt)**
- [ ] Stromfresser-Checkliste live, CHIP/Computerbild pitchen
- [ ] Gas-Entscheidungsbaum + Heiz-Pins (Pinterest 30 Tage voraus)
- [ ] 1 Podcast-Pitch
- [ ] Unlinked-Mention-Suche zum ersten Mal ernst (10 Min)

**Tage 61–90 (Ernte, Nov = Peak)**
- [ ] Kfz-Kampagne: PR-Zitate recyceln, nicht neu erfinden
- [ ] DSL-Checkliste vor Black Friday
- [ ] Auswertung: welche Domain brachte Umami-Sessions + `affiliate_click`?
- [ ] Nur dort nachlegen. Flops nicht mit mehr Mails zuschütten

---

## 10. KPIs (90 Tage)

| KPI | Ziel | Messpunkt |
|---|---|---|
| Editorial dofollow, thematisch DE | ≥ 4 Referring Domains | manuell + später GSC Links |
| Community-Referral-Sessions | messbare Linie > 0 | Umami Referrer |
| PR-Erwähnungen (auch nofollow) | ≥ 2 | Brand-Search |
| Pinterest Outbound-CTR | ≥ 1,5 % | Pinterest Analytics |
| Affiliate-Klicks aus Referral | Baseline dokumentieren, dann + | Umami Event `affiliate_click` |
| Outreach-Antwortquote | ≥ 15 % auf PR/Gast | CRM-Notizen |
| Spam-Fußabdruck | 0 Verzeichnisse, 0 Tausch, 0 Farmen | YAML `ungeeignet` bleibt ungeeignet |

North Star fürs **Geschäft** bleibt Affiliate-Conversion, nicht Domain-Rating. Ein CHIP-Referral, der 3 Kfz-Abschlüsse bringt, schlägt 20 Directory-Dofollows ohne Klicks.

---

## 11. Anti-Playbook (nie wieder anfassen)

- Linkkauf, PBNs, Guest-Post-Netzwerke, A-B-C-Tausch
- Blog-Verzeichnisse (Blogger.de, Geld.de/blog, Sparwelt-Katalog)
- Automatisches Einreichen, Bot-Kommentare, identische Mails an 30 Blogs
- Exact-Match-Anker auf Affiliate-Landingpages
- Republish eines Live-Artikels als „Gastbeitrag“
- Mehr als eine Presseinfo pro Kampagne auf OpenPR/Pressebox
- Pitches an Finanzfluss/FOCUS ohne Original-Asset
- Trustpilot-Reviews als Linkbuilding
- nackte CHECK24-URLs in Outreach, Pins oder Shownotes

---

## 12. Changelog Repo (31.08.2026)

- `scripts/backlink_automation.py` – Premium-Scout (Templates, Scoring, CRM, Selftest, kein YAML-Dump)
- `data/backlink_prospects.yaml` – 7 Kanäle, Saison-Kampagnen, retired Prospects mit Begründung
- `data/backlink_assets.yaml` – 6 Magneten
- `data/backlink_state.json` – CRM
- `BACKLINK-REPORT.md` – Wochenpack statt 15 identischer Mails
- `.github/workflows/backlink-weekly.yml` – Selftest vor Scout
- `WOCHENPLAN-2026-W36.md` – Hebel 4 an Premium-Doktrin angepasst

*Kompatibilität: `post_utils.slug_of` / Draft-Filter analog Internal-Linker. Kein Auto-Submit. Alerting bleibt auf Workflow „Backlink-Automation“.*

---

_Erstellt als Agentur-Paket „Backlink Premium“ am 31.08.2026. Nächster sinnvoller Auftrag: Asset #1 (Kfz-Kalender) bauen, dann den Versicherungsbote-Pitch aus dem Wochenpack absenden._
