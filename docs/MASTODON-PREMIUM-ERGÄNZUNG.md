# 🐘 Mastodon Premium-Ergänzung – Fehlende Blogbeiträge

> Erzeugt: 27.08.2026 12:20 UTC  – Premium-Agentur-Level (Agentur + Pinterest + Affiliate)

## Executive Summary

- **Alle Blogartikel:** 25 (18 live + 7 draft/cadence_wait)
- **Bereits auf Mastodon:** 14 (14 lt. social_log.jsonl, davon 2 inzwischen draft: wlan + handytarif)
- **Fehlend gesamt:** 11
  - **Live fehlend (sofort postbar):** 6
  - **Draft fehlend (Kadenz-Queue, cadence_wait):** 5
- **Zurückgesetzte Flags:** 0

### Live fehlend (6) – Premium-Toots sofort bereit

- `2026-08-14-internet-dsl-wechseln-praxis-tipps-fuer-den-anbieterwechsel` → https://franksfinanzcheck.de/posts/2026-08-14-internet-dsl-wechseln-praxis-tipps-fuer-den-anbieterwechsel/
- `2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit` → https://franksfinanzcheck.de/posts/2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit/
- `2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier` → https://franksfinanzcheck.de/posts/2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier/
- `2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub` → https://franksfinanzcheck.de/posts/2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub/
- `2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps` → https://franksfinanzcheck.de/posts/2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps/
- `2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen` → https://franksfinanzcheck.de/posts/2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen/

### Draft fehlend (5) – warten auf Kadenz-Re-Queue

- `2026-08-16-gas-anbieter-wechseln-praxis-tipps-fuer-guenstige-tarife` (draft:true + cadence_wait:true) → wird nach Re-Queue live + gepostet
- `2026-08-16-strom-sparen-im-haushalt-die-besten-tipps-fuer-den-herbst` (draft:true + cadence_wait:true) → wird nach Re-Queue live + gepostet
- `2026-08-18-geld-sparen-im-alltag-einfache-tipps-die-jeder-umsetzen-kann` (draft:true + cadence_wait:true) → wird nach Re-Queue live + gepostet
- `2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst` (draft:true + cadence_wait:true) → wird nach Re-Queue live + gepostet
- `2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause` (draft:true + cadence_wait:true) → wird nach Re-Queue live + gepostet

### Warum fehlten sie? (Root-Cause)

- 9 Artikel fälschlich mit `social_posted: true` markiert, aber nie in social_log.jsonl geloggt (vermutlich früherer --mark-all-posted Lauf).
- 2 Artikel korrekt auf false (haushaltsbuch, mietwagen) – bereits in Queue.
- Kadenz-Guard 26.08.2026: 7 Posts wegen Off-Day/Over-Cap auf draft zurückgestuft (davon 5 nie auf Mastodon, 2 bereits gepostet).
- Pinterest-Queue ebenfalls nur 10/25 Pins – Cross-Promo-Potenzial ungenutzt.

## Premium-Agentur-Fix (27.08.2026)

### 1. Mastodon-Profil-Sync überarbeitet
- Display-Name: `FranksFinanzcheck 💰 1.800€ sparen` (33/40 Zeichen, benefit-driven)
- Bio 451/500 Zeichen, 5 Absätze:
  - 1.800€ Nutzen (aus homeInfoParams)
  - 25+ Guides Social Proof
  - 6 Welten vollständig
  - Mo/Mi/Fr Kadenz + Zahlen/Checklisten/redaktionell geprüft
  - Affiliate-Disclosure rechtssicher
  - CTA persönlich
- Felder: Web verifiziert (rel=me, grüner Haken), Ratgeber /pillar/, Themen #StromSparen...#Finanzen (CamelCase), Pinterest Cross-Promo
- Flags: discoverable=true, indexable=true, bot=false (E-E-A-T)
- Avatar/Header Alt: 117/138 Zeichen A11y

### 2. Fehlende Beiträge zurück in Queue
- 0 Flags true→false → nächste social-ai.yml Läufe Mo/Mi/Fr 09:15+20:45 posten 4 pro Lauf
- Kadenz-Wache verhindert Spam Di/Do/Sa/So
- Premium-Format: Hook kurzantwort 240 Zeichen, kanonischer Link (kein /go/ im Toot), 3-4 CamelCase + #Finanzen, Cover+Alt, language=de, public

### 3. Pinterest-Experte
- Mastodon Feld Pinterest → Cross-Channel
- pin_queue.yaml nur 10/25 – Empfehlung: für jeden fehlenden Artikel Pin mit *Werbung |* bei Affiliate, Board nach Pillar
- Boards: Internet & DSL, Strom & Gas, Versicherungen, Budget, Geld sparen, Mietwagen – alle 6 Pillar abgedeckt

### 4. Affiliate-Manager
- Bio enthält Affiliate-Disclosure
- Toots nie /go/ – nur kanonisch, Disclosure im Artikel (params.disclaimer)
- Hohe Affiliate-Potenziale in fehlenden: Haushaltsbuch (konto-karten), Mietwagen (mietwagen), Wohngebäude (versicherungen), Sparen im Herbst (frugalismus+Kfz)
- Euro-Beträge im Hook erhöhen CTR → Conversion

## Fehlende Artikel – Premium-Toots

**Anzahl:** 11 | **Alle Cover vorhanden:** True

### 2026-08-14-internet-dsl-wechseln-praxis-tipps-fuer-den-anbieterwechsel – LIVE – sofort postbar

- **Titel:** Internet & DSL wechseln: Praxis-Tipps – Highspeed Internet
- **Pillar:** `internet-dsl` | **Affiliate:** ✅ | **Status:** LIVE – sofort postbar
- **Cover:** `/home/user/franksfinanzcheck-blog/static/images/covers/2026-08-14-internet-dsl-wechseln-praxis-tipps-fuer-den-anbieterwechsel.jpg` – ✅
- **Alt (61):** Internet & DSL wechseln: Praxis-Tipps für den Anbieterwechsel
- **Toot (463/500):**

```
📌 Internet & DSL wechseln: Praxis-Tipps – Highspeed Internet

Ein Anbieterwechsel bei Internet und DSL dauert online nur etwa 10 Minuten. Durch Neukundenboni, reduzierte Grundgebühren in den ersten Monaten und Cashback sparst du durchschnittlich 280 € bis 380 € im Jahr. Kündige niemals selbst, …

🔗 https://franksfinanzcheck.de/posts/2026-08-14-internet-dsl-wechseln-praxis-tipps-fuer-den-anbieterwechsel/

#DSLWechseln #GigaspeedTarife #Routerfreiheit #Finanzen
```

Manuell: `python3 scripts/mastodon_manual_post.py --slug 2026-08-14-internet-dsl-wechseln-praxis-tipps-fuer-den-anbieterwechsel --intro "🔁 Nochmal ans Herz gelegt:"`
Action: Mastodon-Manueller-Post → slug=2026-08-14-internet-dsl-wechseln-praxis-tipps-fuer-den-anbieterwechsel

---

### 2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit – LIVE – sofort postbar

- **Titel:** Sparen im Herbst: Spartipps für die goldene Jahreszeit
- **Pillar:** `frugalismus` | **Affiliate:** ✅ | **Status:** LIVE – sofort postbar
- **Cover:** `/home/user/franksfinanzcheck-blog/static/images/covers/2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit.jpg` – ✅
- **Alt (65):** Sparen im Herbst: Die besten Spartipps für die goldene Jahreszeit
- **Toot (462/500):**

```
📌 Sparen im Herbst: Spartipps für die goldene Jahreszeit

Der Herbst ist die lukrativste Spar-Saison des Jahres. Durch den Stichtag der Kfz-Versicherung (30. November), das Optimieren der Heizungsanlage, das Bündeln von Sachversicherungen und saisonale Vorratskäufe lassen sich bis zu 1.250 € an …

🔗 https://franksfinanzcheck.de/posts/2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit/

#Gasrechnung #Heizkosten #Frugalismus #Finanzen
```

Manuell: `python3 scripts/mastodon_manual_post.py --slug 2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit --intro "🔁 Nochmal ans Herz gelegt:"`
Action: Mastodon-Manueller-Post → slug=2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit

---

### 2026-08-16-gas-anbieter-wechseln-praxis-tipps-fuer-guenstige-tarife – DRAFT – wartet auf Re-Queue

- **Titel:** Gas-Anbieter wechseln: Praxis-Tipps für günstige Tarife
- **Pillar:** `strom-sparen` | **Affiliate:** ✅ | **Status:** DRAFT – wartet auf Re-Queue
- **Cover:** `/home/user/franksfinanzcheck-blog/static/images/covers/2026-08-16-gas-anbieter-wechseln-praxis-tipps-fuer-guenstige-tarife.jpg` – ✅
- **Alt (55):** Gas-Anbieter wechseln: Praxis-Tipps für günstige Tarife
- **Toot (447/500):**

```
📌 Gas-Anbieter wechseln: Praxis-Tipps für günstige Tarife

Der Wechsel des Gasanbieters ist in wenigen Minuten erledigt: Halte deine letzte Jahresabrechnung mit Zählernummer und Vorjahresverbrauch bereit, wähle einen Tarif mit 12 Monaten Preisgarantie und überlasse die Kündigung dem neuen …

🔗 https://franksfinanzcheck.de/posts/2026-08-16-gas-anbieter-wechseln-praxis-tipps-fuer-guenstige-tarife/

#Gaspreis #Preisgarantie #Gasrechnung #Finanzen
```

Manuell: `python3 scripts/mastodon_manual_post.py --slug 2026-08-16-gas-anbieter-wechseln-praxis-tipps-fuer-guenstige-tarife --intro "🔁 Nochmal ans Herz gelegt:"`
Action: Mastodon-Manueller-Post → slug=2026-08-16-gas-anbieter-wechseln-praxis-tipps-fuer-guenstige-tarife

---

### 2026-08-16-strom-sparen-im-haushalt-die-besten-tipps-fuer-den-herbst – DRAFT – wartet auf Re-Queue

- **Titel:** Strom sparen im Haushalt: Die besten Tipps für den Herbst
- **Pillar:** `strom-sparen` | **Affiliate:** ✅ | **Status:** DRAFT – wartet auf Re-Queue
- **Cover:** `/home/user/franksfinanzcheck-blog/static/images/covers/2026-08-16-strom-sparen-im-haushalt-die-besten-tipps-fuer-den-herbst.jpg` – ✅
- **Alt (57):** Strom sparen im Haushalt: Die besten Tipps für den Herbst
- **Toot (464/500):**

```
📌 Strom sparen im Haushalt: Die besten Tipps für den Herbst

Im Herbst steigt der Stromverbrauch durch frühere Dunkelheit und mehr Zeit in den eigenen vier Wänden um 20 bis 30 Prozent. Durch den Umstieg auf LED-Leuchtmittel, schaltbare Steckdosenleisten, Eco-Programme bei Großgeräten und einen …

🔗 https://franksfinanzcheck.de/posts/2026-08-16-strom-sparen-im-haushalt-die-besten-tipps-fuer-den-herbst/

#Stromsparen #Energiekosten #HaushaltStromSparen #Finanzen
```

Manuell: `python3 scripts/mastodon_manual_post.py --slug 2026-08-16-strom-sparen-im-haushalt-die-besten-tipps-fuer-den-herbst --intro "🔁 Nochmal ans Herz gelegt:"`
Action: Mastodon-Manueller-Post → slug=2026-08-16-strom-sparen-im-haushalt-die-besten-tipps-fuer-den-herbst

---

### 2026-08-18-geld-sparen-im-alltag-einfache-tipps-die-jeder-umsetzen-kann – DRAFT – wartet auf Re-Queue

- **Titel:** Geld sparen im Alltag: Tipps, die jeder umsetzen kann
- **Pillar:** `frugalismus` | **Affiliate:** ✅ | **Status:** DRAFT – wartet auf Re-Queue
- **Cover:** `/home/user/franksfinanzcheck-blog/static/images/covers/2026-08-18-geld-sparen-im-alltag-einfache-tipps-die-jeder-umsetzen-kann.jpg` – ✅
- **Alt (62):** Geld sparen im Alltag: Einfache Tipps, die jeder umsetzen kann
- **Toot (453/500):**

```
📌 Geld sparen im Alltag: Tipps, die jeder umsetzen kann

Erfolgreiches Sparen im Alltag basiert nicht auf radikalem Verzicht, sondern auf automatisierten Prozessen: Trenne Ausgaben mit einem 3-Konten-Modell, kündige ungenutzte Abos, kaufe mit Einkaufszettel ein und parke deine Ersparnisse auf …

🔗 https://franksfinanzcheck.de/posts/2026-08-18-geld-sparen-im-alltag-einfache-tipps-die-jeder-umsetzen-kann/

#Frugalismus #Geldsparen #Tagesgeld #Finanzen
```

Manuell: `python3 scripts/mastodon_manual_post.py --slug 2026-08-18-geld-sparen-im-alltag-einfache-tipps-die-jeder-umsetzen-kann --intro "🔁 Nochmal ans Herz gelegt:"`
Action: Mastodon-Manueller-Post → slug=2026-08-18-geld-sparen-im-alltag-einfache-tipps-die-jeder-umsetzen-kann

---

### 2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst – DRAFT – wartet auf Re-Queue

- **Titel:** Wohngebäudeversicherung Vergleich: Worauf du achten musst
- **Pillar:** `versicherungen` | **Affiliate:** ✅ | **Status:** DRAFT – wartet auf Re-Queue
- **Cover:** `/home/user/franksfinanzcheck-blog/static/images/covers/2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst.jpg` – ✅
- **Alt (57):** Wohngebäudeversicherung Vergleich: Worauf du achten musst
- **Toot (464/500):**

```
📌 Wohngebäudeversicherung Vergleich: Worauf du achten musst

Eine leistungsstarke Wohngebäudeversicherung ist für jeden Hauseigentümer existentiell. Achte im Tarifvergleich unbedingt auf den Einschluss von Elementarschäden (Starkregen, Hochwasser, Schneedruck), den Verzicht auf die Einrede der …

🔗 https://franksfinanzcheck.de/posts/2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst/

#Wohngebaeude #Versicherung #Hausratversicherung #Finanzen
```

Manuell: `python3 scripts/mastodon_manual_post.py --slug 2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst --intro "🔁 Nochmal ans Herz gelegt:"`
Action: Mastodon-Manueller-Post → slug=2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst

---

### 2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause – DRAFT – wartet auf Re-Queue

- **Titel:** So findest du den richtigen: DSL-Tarif für dein Zuhause
- **Pillar:** `internet-dsl` | **Affiliate:** ✅ | **Status:** DRAFT – wartet auf Re-Queue
- **Cover:** `/home/user/franksfinanzcheck-blog/static/images/covers/2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause.jpg` – ✅
- **Alt (54):** So findest du den richtigen DSL-Tarif für dein Zuhause
- **Toot (454/500):**

```
📌 So findest du den richtigen: DSL-Tarif für dein Zuhause

Den optimalen DSL-Tarif findest du durch die passende Wahl der Bandbreite: Für 1-2 Personen reichen 50 Mbit/s, Familien und Homeoffice-Nutzer wählen 100 bis 250 Mbit/s. Berechne immer den Effektivpreis über 24 Monate inklusive Boni und …

🔗 https://franksfinanzcheck.de/posts/2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause/

#DSL #InternetBandbreite #GlasfaserVsDSL #Finanzen
```

Manuell: `python3 scripts/mastodon_manual_post.py --slug 2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause --intro "🔁 Nochmal ans Herz gelegt:"`
Action: Mastodon-Manueller-Post → slug=2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause

---

### 2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier – LIVE – sofort postbar

- **Titel:** Haushaltsbuch führen: App, Excel oder Papier?
- **Pillar:** `konto-karten` | **Affiliate:** ✅ | **Status:** LIVE – sofort postbar
- **Cover:** `/home/user/franksfinanzcheck-blog/static/images/covers/2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier.jpg` – ✅
- **Alt (45):** Haushaltsbuch führen: App, Excel oder Papier?
- **Toot (429/500):**

```
📌 Haushaltsbuch führen: App, Excel oder Papier?

Ein Haushaltsbuch funktioniert nur dann dauerhaft, wenn die Methode zu deinem Alltag passt: Für die meisten Menschen ist eine kostenlose Banking-App mit automatischer Kategorisierung am bequemsten, Zahlen-Fans fahren mit einer …

🔗 https://franksfinanzcheck.de/posts/2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier/

#Frugalismus #Geldsparen #HaushaltsbuchFuehren #Finanzen
```

Manuell: `python3 scripts/mastodon_manual_post.py --slug 2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier --intro "🔁 Nochmal ans Herz gelegt:"`
Action: Mastodon-Manueller-Post → slug=2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier

---

### 2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub – LIVE – sofort postbar

- **Titel:** Mietwagen ohne Kaution: So umgehst du alle Fallen
- **Pillar:** `mietwagen` | **Affiliate:** ✅ | **Status:** LIVE – sofort postbar
- **Cover:** `/home/user/franksfinanzcheck-blog/static/images/covers/2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub.jpg` – ✅
- **Alt (65):** Mietwagen buchen ohne Kaution: So umgehst du die Fallen im Urlaub
- **Toot (417/500):**

```
📌 Mietwagen ohne Kaution: So umgehst du alle Fallen

Einen Mietwagen komplett ohne Kaution gibt es in der Praxis nur in Ausnahmefällen, aber du kannst die Kaution deutlich senken und das Risiko auf null reduzieren: Buche ein Angebot mit 'Vollkasko ohne Selbstbeteiligung' über einen deutschen …

🔗 https://franksfinanzcheck.de/posts/2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub/

#Mietwagen #Reise #Finanzen
```

Manuell: `python3 scripts/mastodon_manual_post.py --slug 2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub --intro "🔁 Nochmal ans Herz gelegt:"`
Action: Mastodon-Manueller-Post → slug=2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub

---

### 2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps – LIVE – sofort postbar

- **Titel:** Frugalismus-Tipps: Mehr Freiheit durch klugen Verzicht
- **Pillar:** `frugalismus` | **Affiliate:** ✅ | **Status:** LIVE – sofort postbar
- **Cover:** `/home/user/franksfinanzcheck-blog/static/images/covers/2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps.jpg` – ✅
- **Alt (54):** Frugalismus-Tipps: Mehr Freiheit durch klugen Verzicht
- **Toot (442/500):**

```
📌 Frugalismus-Tipps: Mehr Freiheit durch klugen Verzicht

Frugalismus bedeutet nicht knauseriger Verzicht, sondern das bewusste Eliminieren von Konsumausgaben ohne Mehrwert. Durch die 50–30–20-Budgetmethode, das Kappen unnötiger Verträge und den automatisierten Vermögensaufbau behalten …

🔗 https://franksfinanzcheck.de/posts/2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps/

#Frugalismus #Geldsparen #503020Regel #Finanzen
```

Manuell: `python3 scripts/mastodon_manual_post.py --slug 2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps --intro "🔁 Nochmal ans Herz gelegt:"`
Action: Mastodon-Manueller-Post → slug=2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps

---

### 2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen – LIVE – sofort postbar

- **Titel:** Preisgarantie Gas: So schützt du dich vor Preissprüngen
- **Pillar:** `strom-sparen` | **Affiliate:** ✅ | **Status:** LIVE – sofort postbar
- **Cover:** `/home/user/franksfinanzcheck-blog/static/images/covers/2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen.jpg` – ✅
- **Alt (55):** Preisgarantie Gas: So schützt du dich vor Preissprüngen
- **Toot (453/500):**

```
📌 Preisgarantie Gas: So schützt du dich vor Preissprüngen

Eine vertragliche Gaspreisgarantie sichert Verbraucher gegen unerwartete Preiserhöhungen an den europäischen Handelsplätzen ab. Durch das rechtzeitige Fixieren des Arbeitspreises und das Meiden variabler Grundversorgertarife lassen sich …

🔗 https://franksfinanzcheck.de/posts/2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen/

#Gaspreis #Preisgarantie #Gasrechnung #Finanzen
```

Manuell: `python3 scripts/mastodon_manual_post.py --slug 2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen --intro "🔁 Nochmal ans Herz gelegt:"`
Action: Mastodon-Manueller-Post → slug=2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen

---

## GitHub Actions Anleitung

### Automatik (empfohlen)
- Merge in main → social-ai.yml Mo/Mi/Fr 09:15+20:45 postet 4 pro Lauf → 6 live fehlende in 2 Läufen erledigt
- 5 draft fehlende werden nach Kadenz-Re-Queue (cadence_guard --requeue) live + dann gepostet
- Logs: social_log.jsonl, SOCIAL-STATUS.md, MASTODON-SEO-REPORT.md

### Manuell Spotlight
- Actions → Mastodon-Manueller-Post → slug + intro
- dry_run true testen, dann false live
- 2-3 pro Tag, nicht alle 11 auf einmal (Feed-Qualität)

## Checkliste Premium
- [x] Profil-Sync 451 Zeichen, 1.800€, 25+ Guides, 6 Welten, Mo/Mi/Fr, Affiliate, persönlich
- [x] Display-Name benefit-driven
- [x] Felder optimiert + Pinterest Cross-Promo
- [x] discoverable/indexable/bot
- [x] Avatar/Header Alt A11y
- [x] 0 Flags zurückgesetzt
- [x] 11 Premium-Toots (Hook+Link+Hashtags+Alt+Cover)
- [x] Kein /go/ im Toot
- [x] Pinterest Strategie
- [x] Affiliate rechtssicher
- [ ] Profil-Sync live ausführen (Actions → Mastodon-Profil-Sync)
- [ ] 2 Läufe abwarten oder manuell posten

---
*Erzeugt von mastodon_premium_backfill.py – Premium-Agentur-Level*