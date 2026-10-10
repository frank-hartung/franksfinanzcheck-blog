# 🎯 MARKETING-AKTIONSPLAN – erste Provisionen ohne Pinterest

**Stand:** 10.10.2026 · **Auftrag:** „Welche Maßnahmen bringen am sichersten bald die ersten Provisionen, wenn Pinterest wegen Spam gesperrt ist? Was würde ein Affiliate-Profi tun?"
**Grundlagen (geprüft, nicht geschätzt):** `data/revenue_funnel.json`, `RELEASE-SCORECARD.md`, `AFFILIATE-INTEGRITY-REPORT.md`, `AFFILIATE-INTENT-REPORT.md`, `AUTHORITY-RADAR.md`, `data/pinterest_domain_block.json`, `data/social/performance.yaml`, `data/seo/tag_register.yaml`, `docs/BACKLINK-PREMIUM-STRATEGIE.md`, `docs/UMSATZ-MESSUNG-PREMIUM.md`

> **Verbindlichkeit:** Dieser Plan ersetzt keine Gates. Jede CTA-Änderung läuft durch `affiliate_integrity_gate` + `affiliate_intent_guard` (IW1–IW9) und die Kennzeichnungspflicht (`offenlegung_guard`). Nichts hier rechtfertigt Linkkauf, Eigenabschlüsse oder Pin-Bursts.

---

## 0. Diagnose: Pinterest ist nicht das Problem

Pinterest war Reichweite, nie Provision. Die Sperre hat einen Kanal entfernt – drei Dinge fehlen aber für die **erste Provision** viel grundlegender:

| Nr. | Was fehlt | Beweis im Repo | Wirkung |
|---|---|---|---|
| **B1** | **Der Trichter ist nicht verbunden** | `revenue_funnel.json`: alle Felder `null` seit Anbeginn; `data/monetization.yaml`: `awin_enabled: false`, `umami_api_import_enabled: false`; `data/provisionen/` enthält nur die Vorlage | Du optimierst blind. Du weißt nicht, welche Seite klickt, welcher Klick führt zu einem Antrag, welche Route Geld bringt |
| **B2** | **Zu wenig indexierter Bestand, um Kaufabsicht einzufangen** | 42 Live-Artikel, ~8 Wochen alte Domain; GSC meldete 237 nicht indexierte Seiten; 2 Artikel von Gates gehalten; 1 Draft wartet auf Freigabe | Bei 0–2 k Klicks/Monat und einer CTA-CTR von 3–4 % sind **300–800 /go/-Klicks** realistisch – bei 1–3 % Antragsrate auf Strom/Gas also **3–24 Anträge/Monat**, wenn alles stimmt. Wenn die Seiten aber nicht indexiert sind, ist der Ausgangswert 0 |
| **B3** | **Kein vertrauensbildendes Außensignal** | `AUTHORITY-RADAR.md`: 0 Editorial-Links, 0 Mediennennungen, 0 Interviews, 0 Kooperationen; `data/social/engagement_cache.json`: alle 11 Mastodon-Posts bei 0 Reaktionen | Auf YMYL gewinnt nicht der beste Text, sondern der glaubwürdigste Absender. Ohne Außensignale konvertiert auch Platz 2 schlechter |

**Konsequenz für die Priorität:** Ein Affiliate-Profi würde in Monat 1 **nicht** primär Content produzieren (die Pipeline liefert bereits 2/Tag), sondern **Messen verbinden, Kaufen ermöglichen, Vertrauen ausleihen**.

---

## 1. Die Doktrin in einem Satz

> **Geld gibt es dort, wo Wechselangst auf einen Rechner trifft – nicht dort, wo Spartipps wohnen.**

Das bedeutet programmatisch: **Kategorien auf 3–4 zusammenstreichen** und jede Maßnahme an *einer* Zahl ausrichten (Anträge je 100 Besuche je Route), nicht an Reichweite.

### Provisionstreppen (CHECK24-Inhouse, dein aktives Programm `pid=80968`)

| Produkt | Vergütung je… | Besonderheit | Konsequenz |
|---|---|---|---|
| Strom / Gas | **16,50–20,00 € je Antrag, stornofrei** | Antrag zählt, max. 25 Tage bis Gutschrift | **Schnellstes Geld.** Kein Storno-Risiko, keine Wartezeit bis zur Provision → ideal für die *ersten* Abschlüsse |
| DSL / Internet | **40,00–72,50 € je Abschluss** | Abschluss, nicht Antrag; härtere Keyword-Landschaft | Höchster Einzelwert – aber du musst gegen Finanztip/Check24-eigene Landingpages ranken |
| Kfz-Versicherung | je Abschluss (Tarifcheck) | **Stichtag 30.11.** | Zeitfenster öffnet jetzt. Vorlauf 4–6 Wochen = Oktober/November |
| Mietwagen / Pauschalreise | 5,50 % der Buchungssumme | Saisonal, im Oktober tot | Auf Januar (Frühbucher) parken, kein Ressourcenkampf jetzt |
| Hausrat / Haftpflicht / Zahnzusatz / Wohngebäude | Abschlussprovision (Tarifcheck) | Lange Laufzeiten, hohe Vertrauenshürde | Nur mit echtem Erfahrungsbeleg (Polizze, Beitrag, Selbstbehalt) |

### Was daraus folgt (radikale Fokussierung, 6 Wochen)

- **Rang 1: Strom + Gas** (Volumen + Antrag-Vergütung + Heizsaison = perfektes Timing; Kampagne `herbst-energiewechsel-2026` läuft bereits bis 31.10., `winter-energie-2026-27` ab 01.11.).
- **Rang 2: Kfz-Versicherung 30.11.** – der einzige Termin im deutschen Affiliate, an dem Nachfrage *kalenderfest* ist. Asset (`kuendigungsfristen-kalender`) existiert schon.
- **Rang 3: DSL** auf deinen stärksten 3 bestehenden Seiten (Bestand heben statt neu schreiben).
- **Pause (Sichtbarkeit auf den 3 Kernen, keine neuen Artikel):** Frugalismus, 50-30-20, „7 Gewohnheiten", WLAN-Ratgeber, Mietwagen/Reisen, Girokonto/Tagesgeld. *Grund:* Intent passt nicht zur Provision – „Notgroschen" kauft keinen Stromtarif. Genau diese Streuung ist auch der Grund für die drei IW2-Hinweise im Intent-Report (fremde End-CTAs).

---

## 2. Prioritätenliste: Was ein Affiliate-Profi in dieser Reihenfolge tun würde

Jede Maßnahme mit **Aufwand**, **Zeit bis zum Effekt** und **Beweis, dass sie wirkt**.

### P0 – Messen verbinden (Woche 1, 2–4 h) · *Grundlage für alles Weitere*

> **Stand 10.10.2026 – Weg 0.1/0.3 ist gebaut:** `scripts/offline_import.py`
> zieht Dashboard-Exporte (`data/offline/messstand.json`) **und** die
> Abrechnungstabelle in die versionierten Aggregate; `scripts/revenue_funnel.py`
> rechnet daraus einen Trichter mit ausgewiesener Messbrücke. Ablauf:
> `npm run mess:vorlage` → ausfüllen → `npm run mess:import`; Kontrolle:
> `npm run mess:status`. Runbook: `docs/UMSATZ-MESSUNG-PREMIUM.md`, Abschnitt 5a.
> 0.2 (Zweitnetz-API) bleibt der bevorzugte Weg, sobald Token vorhanden –
> `data/monetization.yaml` ist und bleibt die einzige Entscheidung darüber.

| # | Maßnahme | Aufwand | Effekt |
|---|---|---|---|
| 0.1 | **Partner-Dashboard zur einzigen täglichen Wahrheit machen:** `a.check24.net` Statistiken nach `pid`/`aid`/`deep` auswerten – die sind bei dir schon kategoriegenau getrennt. Täglich 1 Zeile manuell in `data/provisionen/provisionen.csv` (Vorlage existiert, `provisionen_check.py` validiert) | 15 Min/Tag → später 10 Min/Woche | Klicks ↔ Anträge ↔ Provision zum ersten Mal **im selben Bild** |
| 0.2 | **Zweitnetz zur Kreuzprüfung anmelden** (CHECK24 läuft u. a. über Awin; dort `AWIN_API_TOKEN` + `AWIN_PUBLISHER_ID` setzen) – *nur* als Kontrollkanal mit SubID, Hauptlinks bleiben unverändert auf Inhouse (höhere Vergütung, stornofrei) | 1–2 h | Deine vorhandene `revenue-import`-Pipeline füllt sich, der Funnel hört auf, `null` zu melden. Ohne Netz-Backup hast du keine unabhängige Zahl |
| 0.3 | **Umami-Zahlen in den Trichter holen (Export-Schleife) oder aus dem Free-Plan raus.** Stand: `hugo.toml → [params.umami]` zeigt auf `cloud.umami.is` (Cloud Free, seit 31.08.2026, cookieless, `consentRequired = false`), deshalb ist `umami_api_import_enabled: false` – die Views liegen nur im Dashboard und sind für die Automatik unsichtbar. Zwei Wege: (a) Export-Schleife (wöchentlich CSV je Seite + Event `affiliate_click` einlesen), (b) **self-hosted** auf VPS/Container mit Postgres (die `hostUrl`-Zeile ist dafür schon vorbereitet) | 2–4 h | Kanal-Zerlegung (Google / Newsletter / Community / Discover) wird erst messbar – und zwar ohne UTM-Parameter am Affiliate-Link zu verbiegen (deine bewusste Regel von 25.08.2026) |
| 0.4 | **Ein Testklick, kein Testkauf:** `click_chain_guard.py --test-page` – eigene Adresse über /go/ klicken, Klick im Dashboard wiederfinden. **Niemals** selbst einen Vertrag über den eigenen Link abschließen | 10 Min | Kette bewiesen, Programm-Status nicht gefährdet |

> Ehrliche Erwartung: P0 bringt 0 €. Es ist der Grund, warum P1–P4 überhaupt bewertet werden können. Ein Profi beginnt hier, weil „nach Gefühl optimieren" die einzige Art ist, ein Jahr zu verlieren.

### P1 – Kaufen ermöglichen: die 82 kaufnahen Seiten scharf stellen (Woche 1–2, 1–2 Tage)

| # | Maßnahme | Warum es schnell wirkt |
|---|---|---|
| 1.1 | **Rechner in die Kaufstrecke einbetten – nicht umgekehrt.** Nachprüfung 10.10. (Korrektur dieses Punktes): Die 8 Werkzeuge sind **vollständig abgekoppelt** – 0 interne Links aus `content/` auf `/werkzeuge/`, `{{< werkzeug >}}` in keinem Artikel, und `kaufnahe_paths()` zählt **0** Werkzeugseiten. Ein CTA **auf** der Werkzeugseite ist verboten: `werkzeuge_gate.py` W3 (WERBEFREI) bricht den Deploy ab und der Vertrauenssatz W1 ist Markenversprechen. Der ehrliche Hebel ist deshalb der Gegenweg: Werkzeug als **Beweisstück in die 6–8 strongest kaufnahen Artikel/Pillar** (`{{< werkzeug id="abschlag-nachzahlung" >}}` ist dafür gebaut, „Einbettung anderswo“) – Rechenleistung gehört vor den Abgang, nicht in die Werbung. Optional zweite Stellschraube: `werkzeuge/` in die kaufnahe Menge aufnehmen, damit der Trichter diese Seiten endlich misst (Regel in `revenue_funnel.py`, kein Content-Bruch) | Kein neuer Traffic nötig, kein Gate-Bruch, und der einzige Punkt, an dem deine acht fertigen Werkzeuge überhaupt Geld sehen können |
| 1.2 | **Die 3 meistbesuchten Seiten auf Top-CTA + konkrete Zahl trimmen** (Ersparnis in €, 24-Monats-Rechnung, Kündigungsfrist). Vorbild: dein eigenes Effektivpreis-Rechner-Muster | Ein CTA mit Euro-Betrag schlägt einen CTA mit Versprechen |
| 1.3 | **Heizöl-Artikel sendet Strom-CTAs:** `2026-10-07-heizoel-preise-…` hat drei Mal `/go/strom/` (top/mid/end) – für einen Artikel über Heizöl-Kaufzeitpunkte. Es gibt keine Heizöl-Route im `check24_links`-Register, also ist der ehrliche Fix: Strom-CTA **runter** und den Heizöl-Rechner/C24-Budget-Hinweis setzen **oder** eine themenexakte Route ergänzen – nie einen fremden Rechner als Ersatz-CTA stehen lassen (Intent-Wache IW4, offen seit 19.09.) | 20–40 Min; beseitigt ein dokumentiertes Conversion-Leck auf einer Kaufseite und schützt die Intent-Regel „Anker = Ziel" |
| 1.4 | **Cross-Selling-End-CTAs entwirren** (IW2: Pauschalreise-Artikel → Mietwagen-CTA; Strom-Artikel → Portal-CTA). Entweder Kontextsatz ergänzen oder Route wechseln | Ein Klick, der beim Thema bleibt, konvertiert; einer, der in einer Portal-Startseite landet, verpufft |
| 1.5 | **/go/-Gateway-Seiten von der Übergabe zur Zwischenseite machen:** Top-3-Angebote der Kategorie, 3 Vertrauenszeilen, ein Satz Datenschutz, dann der Abgang | Senkt die „warum bin ich hier"-Absprungrate. Gate `IW5` beachtet: echtes Ziel benennen, `noindex`, keine Werbung ohne Kennzeichnung |

### P2 – Käufer ohne Google besorgen (Woche 1–6, der eigentliche Provisionstreiber)

| # | Maßnahme | Konkrete Umsetzung | realistische Zahl |
|---|---|---|---|
| 2.1 | **Newsletter zum Verkaufsapparat machen** (Infrastruktur ist schon dein Eigenbau: Worker + KV + Resend, Di/Fr 06:30) | **Lead-Magnet:** eine Mini-Seite „Kündigungs-Fenster-Check" – Ergebnis kommt per Mail (kein PII in Git, passt zu deiner bestehenden Hash-Politik). **Welcome-Strecke** 4 Mails/8 Tage: 1) Was du jetzt (Oktober) tun solltest · 2) Rechenbeispiel Strom-Abschlag · 3) Mein eigener Wechsel, mit Screenshots und der Nachzahlung, die ich bekommen habe · 4) Vergleichslink + Fristen. Im Format der Normalausgabe „1 Zahl + 1 Link" | 500 Abos, 45 % Öffnung, 12 % Klick auf den Newsletter-CTA, davon 5 % auf /go/ ≈ **14 Klicks pro Ausgabe** (Di + Fr ≈ 115/Monat). Bei 2 % Antragsrate auf Gas = **2–3 Anträge/Monat ≈ 40–60 €**, und zwar stornofrei. Die Rechnung ist absichtlich konservativ: Unter 300 Abos reicht der Newsletter noch nicht für die erste Provision – dann ist 2.2 der Hebel |
| 2.2 | **Community statt Autopilot** | 2–3 wirklich gute Antworten/Woche: r/Finanzen, Finanztip-Foren-Threads zu Strom-/Gas-/Kfz-Fragen, Gutefrage, lokale Facebook-Haushaltsgruppen. Profil mit Klarnamen Frank + „10 Jahre Praxis". Link **nur**, wenn die Frage eine Anleitung verlangt. Keine Serien, keine identischen Sätze | Kein Traffic-Versprechen, aber: Referral-Sessions, Markensuche, und der günstigste E-E-A-T-Beweis, den es für einen KI-gesteuerten Blog gibt |
| 2.3 | **Mastodon-Autopilot umstellen oder aus** | 11 Posts, 60 Tage, **0** Zustimmungen, 0 Reposts, 0 Antworten. Fortsetzung bedeutet: 2×/Tag ins Leere senden **und** ein Spam-Muster auf einem Kanal, den du gerade verloren hast. Entscheidung: (a) Autopilot auf „Gespräch" umstellen (Reply-Modus, 3×/Woche, `social-dialog`-Pfad nutzen) oder (b) Kanal auf Standby | Nichts verlieren außer Lärm. Ein toter Vollautomat ist teurer als ein leiser manueller Kanal |
| 2.4 | **Digitale PR auf das einzige Asset, das schon live ist:** `fixkosten-index-2026-q4` (live seit 02.10.) | Presseformat, Methodik und CSV sind laut `AUTORITAET-DISTRIBUTION-RUNBOOK.md` Pflicht – vorhanden? Dann 5 Pitches/Woche – das ist exakt deine eigene Kapazitätsregel: Lokalzeitungen („Strompreis in Ihrer Stadt"), Verbraucherblogs, Finanz-Podcasts, Hörfunk-Verbrauchersendungen. **Nie** `/go/` pitchen, nie Exact-Match-Anker | Links + Nennungen = Ranking- und Conversion-Booster. Wirkt in 6–10 Wochen, wirkt aber lange |
| 2.5 | **News-Reaktivität als zweiter Traffic-Motor** | Es existieren bereits „Update, was sich jetzt ändert"-Artikel pro Themenwelt (Energie, Konto & Karten, Internet & DSL). Das ist genau das Format, das 2026 funktioniert (Discover + KI-Zitate). Also: Preis-/Gebühren-Radar (BDEW, Bundesnetzagentur, Netzbetreiber-Betriebsstunden, Provider-Erhöhungen) → **innerhalb von 24 h** Update + Aussendung über Newsletter, Mastodon und Frage-Antwort-Plattformen | Ein einziges getimtes Update kann mehr Provision bringen als 20 Evergreens. Und es ist der Grund, warum das Kennzahlen-Radar überhaupt existiert |
| 2.6 | **Bing/Ecosia/DuckDuckGo** – IndexNow + Sitemap sind da, Verifizierung vorhanden | Für junge Domains nachweislich zugänglicher; Ecosia (Bing-Index) hat in DE spürbaren Anteil bei „grün + sparen"-Publikum | 5–10 % zusätzliche organische Klicks, ohne Zusatzaufwand |

### P3 – Sichtbarkeit auf Bestand statt Breite (Woche 2–8)

| # | Maßnahme | Detail |
|---|---|---|
| 3.1 | **Indexierung ist das Nadelöhr, nicht „mehr Artikel"** | GSC-Prüfung je Live-Artikel: Abdeckung → „Gefunden – aktuell nicht indexiert" ist dein Hauptfehlerbild. Freigabe-Queue abarbeiten (2 Artikel von Gates gehalten, 1 Draft „Vorsorge-Update 2026" wartet), `set_lastmod.py --git-changed` danach. Tag-Archive sind bereits abgeschafft – gut, das war Crawl-Budget-Diebstahl |
| 3.2 | **Long-Tail statt Kopfzeile** | Nicht „Stromanbieter vergleichen", sondern: „Strompreis **München** Oktober 2026", „**Stadtwerke** X Kündigung Frist", „Wie rechne ich meinen **Gasabschlag** bei 130 m²", „**Sonderkündigungsrecht** bei Preiserhöhung", „**Vorkasse**-Stromanbieter ausgefallen – was tun". Diese Seiten sind kauend, wenig umkämpft und AI Overviews nehmen sie seltener vorweg |
| 3.3 | **KI-Antwortmaschinen füttern (GEO/AEO)** | `static/llms.txt` existiert bereits. Was fehlt: **zitiierbare Einzahl-Sätze mit Datum und Methode** je Money-Page („FranksFinanzcheck-Fixkosten-Index, Q4 2026, n=…, Stand 02.10.2026"), FAQ-Block als Antwort-Einheit, durchgehender Autor-Block. CTR aus AI Overviews liegt in DE bei ~1 % – ein **Zitat mit Markenname** bringt Markensuche, und die konvertiert überdurchschnittlich |
| 3.4 | **Discover-Rahmen** | `max-image-preview:large` ist schon gesetzt (gut). Discover heißt 2026 aber: lokale Relevanz, kein Clickbait, Tiefgang (Februar-Update). Also Bilder ≥ 1200 px / 16:9 mit echtem Befund im Titel, keine Neugier-Lücken („…das erstaunt dich" verliert) |
| 3.5 | **Menge deckeln** | `MAX_ARTIKEL_PRO_TAG = 4` steht als Option im Optimierungsplan – **nicht** aktivieren. Bei 0 Außen-signalen erhöht 4×/Tag nur das Risiko dünner, thematisch streuender Seiten (und Topical Authority ist genau das, was der Insurance-/Energie-Content braucht). 2/Tag mit klarem Kern-Fokus schlägt 4/Tag diffus |

### P4 – Pinterest: reparieren, aber nie wieder als Income-Kanal bauen

1. **Appeal sauber stellen** (Help-Center-Kontaktformular → *Appeals*; die Phasen mit Formularfehlern sind behoben – dort gehören die Domain-URL und ein sachlicher „kein Link-Spam"-Nachweis hinein). Vorlage liegt in `docs/PINTEREST-SPIELBUCH.md`, Status in Issue #448.
2. **Erst nach schriftlicher Freigabe:** `python3 scripts/spam_guard.py --domain-unblock` → dann `pinterest-restart.yml` (geführt, `bestaetigt`-Haken, Token-Neuautorisierung, **Trockenlauf statt Pin-Burst**). Dieser Workflow ist genau dafür gebaut worden – nutzen, nicht im Runbook hantieren.
3. **Neue Grundregel, damit es nicht nochmal passiert:** Das Risiko war nicht „Pinterest", sondern **Vollautomaten-Pinning aus RSS bei 2 Publikationen/Tag**. Deshalb dauerhaft: RSS-Autopublish **aus**, stattdessen max. 2 Pins/Tag, Pin erst ≥ 48 h nach Livegang (Qualitätssignal statt Massenabwurf), pro Artikel 1 Pin, und Pins, die auf echten Traffic konvertieren (Rechner/Infografik statt Cover-Motiv).
4. **Erwartung:** Pinterest verlängert Reichweite, nicht Provision. Wenn der Rest steht, ist der Kanal nettes Extra – und falls die Sperre bleibt, ist dein Jahr trotzdem gelaufen.

---

## 3. Zeitachsen – ehrlich gerechnet

| Horizont | Was „Erfolg" heißt | Wovon es abhängt |
|---|---|---|
| **7 Tage** | Funnel zeigt echte Zahlen statt `null`; alle 42 Artikel indexiert oder mit begründetem Status; alle kaufnahen Seiten mit themenexakter Route; 1. Ausgabe mit Fristen-Magnet | P0 + P1 + 3.1 |
| **30 Tage** | **1.–5. Antrag aus Strom/Gas** (16,50–20 € stornofrei) – primär aus Newsletter + Community + Long-Tail, nicht aus Rankings; ≥ 15 neue Newsletter-Abos/Woche; 5 versendete PR-Pitches | P1.1 + P2.1 + P2.4 |
| **60 Tage** | 5–15 Anträge/Monat, erste DSL-Abschlüsse (je 40–72,50 €), EPC je Route sichtbar → damit entscheiden, welche 10 Seiten Investment verdienen | P2 + P3.2 |
| **90 Tage** | 15–40 Abschlüsse/Monat, ≥ 3 verdiente Editorial-Links im Evidenzregister, Kategorie-Verteilung nach Daten statt Bauch | P2.4 + P3 |
| **6–12 Monate** | Kfz-Stichtag 30.11. als eigener Saison-Umsatz; Fixkosten-Index als zitierte Quelle; mehrkanalfähige Distribution, die keinen einzigen Kanal-Sperrtag überlebt | Asset-Programm |

Wer nach 30 Tagen 500 € erwartet, hat sich verrechnet. Wer nach 30 Tagen **null** provisionierte Anträge hat **und** einen funktionierenden Trichter, hat ein Verteilungsproblem – und weiß es dann auch.

---

## 4. Was du NICHT tun solltest (die teuren Fehler)

1. **Ersatz-Kanal-Hopping** (Instagram/TikTok/X/Pinterest-Backup-Account). Kurzfristig Reichweite, null Kaufkraft, hohes Sperre-Risiko durch Automaten-Muster – der identische Fehler, der Pinterest gekostet hat.
2. **Noch mehr Artikel, noch breiter.** Die Engine liefert bereits. Dein Mangel ist Vertrauen, Verbindung und Intent-Fokus, nicht Zeichen.
3. **Gekaufte Links, Verzeichnisse, Tauschringe, KI-Bylines in Massen.** 2026 bestraft SpamBrain auf Domain-Ebene – eine junge Domain überlebt das nicht. Deine eigene Doktrin („Ein Link zählt nur, wenn ein Mensch ihn auch ohne Google setzen würde") ist richtig – danach handeln.
4. **Eigenabschlüsse, um das Dashboard zu füllen.** Ein Antrag wird storniert, im besten Fall nichts, im schlechtesten das Partnerverhältnis.
5. **Klick- und Impressionstaktiken auf /go/.** Kein „Klick hier, sonst zahlst du 300 €" – die Marke (und der Google-Qualitätsscore) lebt von Ruhe.
6. **Auto-Post-Serien mit identischem Muster auf jeder Plattform.** Genau das hat Pinterest gemeldet. Jeder neue Kanal braucht eine eigene Frequenz-Obergrenze (dein `spam_guard`-Muster ist die richtige Bauform – auch für neue Kanäle).

---

## 5. Die 12 Griffe für diese Woche (Checkliste)

- [ ] `a.check24.net` Dashboard öffnen, letzte 30 Tage je `deep` notieren → `data/provisionen/provisionen.csv` anlegen (`cp provisionen-vorlage.csv …`)
- [ ] Zweitnetz (Awin) beantragen, Secrets setzen, `awin_enabled: true` – erst dann meldet der Funnel echte Transaktionen
- [ ] `click_chain_guard.py --test-page` einmal durchlaufen (Klick-Kette beweisen)
- [ ] Heizöl-Artikel `2026-10-07-heizoel-…`: drei Strom-CTAs durch ein ehrliches Ziel ersetzen (Route ergänzen **oder** CTA entfernen – nicht auf `gas` umbiegen, wenn das Angebot nicht passt); `affiliate_intent_guard.py --fix` meldet danach `IW4: 0`
- [ ] 3× IW2-Hinweise auflösen: Kontextsatz an der End-CTA **oder** Route themenexakt
- [ ] Rechner-Einbettung als begutachtungsfähiger Entwurf: 6–8 kaufnahe Artikel × 1 × `{{< werkzeug id=… >}}` + End-CTA auf die passende Route (`rel="sponsored nofollow noopener"` + SubID, Kennzeichnung nach `offenlegung_guard`). **Kein** Partnerlink unter `/werkzeuge/` (W3-Wache); Entscheidung „werkzeuge in kaufnahe Menge?“ als separater, begründeter Eingriff
- [ ] 2 gehaltene Artikel + 1 Draft fachlich freigeben (Scorecard wird grün, Bestand wächst messbar)
- [ ] Newsletter: „Fristen-Check" als Lead-Magnet definieren + Welcome-Strecke (4 Mails) in `data/campaigns.yaml` als `type: promo`, Status `paused` bis Freigabe
- [ ] Kfz-Kampagne „30.11." aktivieren (Asset vorhanden: Kündigungsfristen-Kalender)
- [ ] Pinterest-Appeal über Help-Center → *Appeals* absenden, Beleg in Issue #448 vermerken
- [ ] Mastodon-Autopilot: Entscheidung „Gespräch oder Standby" und dokumentieren (kein dritter Zustand)
- [ ] GSC: Liste „nicht indexiert" je Live-Artikel abarbeiten, Ergebnis in `INDEX-HYGIENE`-Report schreiben

---

## 6. Messgröße des Monats (eine einzige, verbindlich)

**Anträge je 100 Besuche, je Route, je Kanal.**
Alles andere (Views, Follower, Pins, Rankings) ist Vorlauf. Diese eine Zahl steht ab P0 wöchentlich im Scorecard-Kontext und entscheidet, was ausgebaut wird.
