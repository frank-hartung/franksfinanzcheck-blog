# Archivprüfung · 19. November 2026

**Umfang:** Alle 88 veröffentlichten Artikel unter `content/posts`, einzeln mit dem lokalen Build abgeglichen. Die 46 Entwürfe gehören nicht zum veröffentlichten Archiv. Prüfstand ist der Arbeitsbranch, nicht die Produktionswebsite.

## Bearbeitungsstand nach der Bestandsredaktion

Die Tabelle unten bleibt der **Messstand vor dieser Überarbeitung**, nicht eine neue Messung nach den Änderungen. Bearbeitet wurden danach alle 88 veröffentlichten Beiträge und alle 46 Entwürfe:

- Jeder Beitrag hat einen individuell formulierten Teaser. Bei zehn fachlich gesiegelten Fassungen wird dafür Hugos separates Summary verwendet; die attestierten Texte und Prüfdaten bleiben unverändert. Kein Entwurf wurde freigeschaltet.
- Die ungesiegelten Beiträge enthalten konkrete, artikelspezifische Entscheidungshilfen. Die neuen Fassungen zu Handytarifen, Tagesgeld und Vorratsplanung erklären ihre Vergleichsrechnungen direkt am Beispiel. Der DSL-Vergleich rechnet 100 Mbit/s mit und ohne lange Bindung über denselben Zeitraum. Der Vorratsentwurf verzichtet auf die sachfremde Reisewerbung.
- Im Herbstbeitrag sind Frist und Jahresende voneinander abgegrenzt. Die frühere Sammelsumme von 1.440 € entfällt. Beim gesiegelten Kfz-Beitrag sind die Grenzen des Rechenbeispiels und des Novembertermins als Korrektur ausgewiesen und öffentlich protokolliert. Für die fachliche Neuabnahme liegt eine [Redaktionsvorlage mit Ersatztexten](kfz-fachrevision-2026-11-19.md) vor. Eine neue Fachfreigabe ist **offen**.

**Abnahme der überarbeiteten Fassungen:** Hugo-Produktionsbuild und isolierter Entwurfsbuild erfolgreich. Für jeden der 134 Quellartikel wurden die gerenderte Einzelseite und die Sichtbarkeit im richtigen Build kontrolliert: 88 im Produktionsbuild, alle 134 im Prüfbuild. Alle 134 Teaser sind verschieden und erfüllen die Zeichen- und Breitengrenzen aus `scripts/serp_limits.py`. Copy-Editing mit `--include-drafts --strict`: 0 offene Funde, Flesch-Amstad Ø 65,6. Siegelwache, Beweisregister und Ableitungen der 20 bebilderten Beiträge ohne Befund. Die fünf gezielten Browserprüfungen für Startstruktur, Kfz-Hinweis und Tagesgeld-Rechnung waren erfolgreich (Desktop sowie für die beiden Artikelfälle auch mobil).

**Partnerlinks:** Sachfremde Tarifwerbung unter anderem aus Fenster-, Waschmaschinen- und Kaffee-Ratgebern entfernt. Partnerangebote, wo passend, mit dem tatsächlichen Ziel benannt. Die gerenderte Offenlegung und die Integritätsprüfung bestehen; die Intent-Prüfung meldet keinen blockierenden Fund. Ein nicht blockierender Hinweis betrifft den allgemeinen Partnerlink im bereits gesiegelten saisonalen Entwurf vom 15. Oktober. Er wurde nicht stillschweigend geändert.

## Befunde der ursprünglichen Prüfung

1. **Kfz-Vergleich:** Der Einstieg nennt den 30. November als allgemeine Kündigungsfrist; weiter unten nennt derselbe Beitrag unterjährige Laufzeiten. Einstieg und Kurzantwort müssen die Bedingung direkt nennen. Die Spanne von 300–800 Euro ist keine allgemeine Durchschnittsersparnis. Der Beitrag trägt bereits eine Fachfreigabe: Korrektur und erneute Prüfung zusammen behandeln, nicht still das Siegel übernehmen.
2. **Handytarife und Tagesgeld:** Preise „ab 4,99 €“ und Zinsspannen sind zeitabhängig. Vor erneuter Bewerbung Tarif, Datum, Laufzeit und Bedingungen an der Originalquelle nachprüfen. Bei fehlendem Preisbeleg lieber den Vergleichsweg beschreiben als einen Bestpreis versprechen.
3. **Reihenfolge:** Zuerst Artikel mit Frist- oder Preisangaben und offenen Fachfreigaben prüfen. Danach Texte ohne ausgewiesenen Prüfstatus einordnen. Vier Artikel sind als freigegeben, 48 als ausstehend und 36 ohne diesen Status erfasst. Keine Freigabe wurde durch den Sprachtest ersetzt.

**Sprache:** Der strikte Copy-Editing-Lauf über den veröffentlichten Bestand meldete keine offenen kritischen Treffer; Flesch-Amstad Ø 66,1. Die zusätzliche Titelsichtung fand trotzdem Satzfragmente und pauschale Versprechen, die im Branch redigiert wurden. Ein grüner Sprachtest prüft weder die Wahrheit eines Satzes noch die Aktualität seiner Quelle.

## Ladezeit: Was die Messung tatsächlich zeigt

Ein kalter Aufruf pro URL mit Chromium 153.0.8010.0, 390 × 844, neuer Browserkontext, Service Worker deaktiviert, nur lokale Ressourcen, kein Netz- oder CPU-Throttling. Zeit vom Navigationsbeginn bis `loadEventEnd`; Lazy-Load beim Scrollen ist nicht enthalten. Artikel: Median **176 ms**, P75 **186 ms**, P95 **208 ms**. Startseite **163 ms**, Archiv **97 ms**, Cockpit **142 ms**. Perzentile beschreiben die Verteilung über URLs, nicht über Besucher.

Separat drei lokale Lighthouse-Läufe auf der Startseite: keine Verletzung der Projekt-Budgets; letzter Lauf Performance **93**, Accessibility **100**, Best Practices **100**, SEO **100**. Das ist kein Nachweis für Barrierefreiheit, Google-Platzierungen oder Core Web Vitals realer Nutzer. Dafür ist nach Veröffentlichung der bestehende Workflow `web-vitals-woche.yml` zuständig.

## Sichtbarkeit: echte Impressionen statt geschätzter Rankings

Quelle: `data/gsc/top_seiten_28t.json` und `top_suchbegriffe_28t.json`, Domain-Property, 13.10.–09.11.2026, Import 12.11.2026. Die mittlere Position bezieht sich nur auf beobachtete Impressionen. Kein Live-Abruf am 19.11.; keine Aussage über den Effekt der unveröffentlichten Änderungen. Fehlende Zeilen bedeuten **keine Daten in diesem Export**, nicht Position null. Suchbegriffe sind nicht mit einzelnen Seiten verknüpft.

| Suchbegriff (höchste Impressionen) | Impressionen | Klicks | Ø Position |
|---|---:|---:|---:|
| 100 mbit internet monatlich kündbar | 66 | 0 | 45.35 |
| energiekosten senken | 22 | 0 | 39.41 |
| frank dsl | 15 | 0 | 7.07 |
| dauerhafte kostenkontrolle | 11 | 0 | 62.73 |
| internetkosten | 11 | 0 | 57.73 |

**Entscheidung:** Beim DSL-Ratgeber zuerst prüfen, ob die Kosten eines monatlich kündbaren 100-Mbit-Tarifs verständlich mit einer längeren Laufzeit verglichen werden. 66 Impressionen sind ein Hinweis auf Nachfrage, kein Grund für ein Rankingversprechen. Nach Veröffentlichung zwei vollständige 28-Tage-Fenster für dieselbe URL und Suchanfrage vergleichen; saisonale Effekte und kleine Stichproben kenntlich machen.

## Artikelregister

Quellen = Anzahl der hinterlegten Quellen, keine Bestätigung ihrer Richtigkeit. Prüfanlässe = Textsignale in Titel, Beschreibung, Kurzantwort oder Volltext, keine festgestellten Rechts- oder Rechenfehler. Ein Strich ist keine inhaltliche Freigabe.

| Artikel | Quellen | Fachstatus laut Artikel | Prüfanlass | Load (ms) | GSC: Impressionen / Ø Position |
|---|---:|---|---|---:|---:|
| [DSL-Wechselbonus sichern: So sparst du beim Internetvertrag](../content/posts/2026-08-10-dsl-wechselbonus-sichern/index.md) | 3 | nicht ausgewiesen | – | 190 | – |
| [Gaspreisgarantie: Welche Kosten sind geschützt und wie lange?](../content/posts/2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas/index.md) | 4 | nicht ausgewiesen | – | 187 | – |
| [Haus und Hausrat versichern: Welcher Schutz passt zu dir?](../content/posts/2026-08-12-dein-haus-sicher-schuetzen-das-neue-vorsorge-update-2026/index.md) | 3 | freigegeben | – | 170 | 1 / 9.00 |
| [Geld abheben im Ausland: Wo die Gebühren wirklich entstehen](../content/posts/2026-08-12-geld-abheben-im-ausland-gebuehren-vermeiden/index.md) | 3 | ausstehend | – | 169 | – |
| [Preisgarantie Gas: So sicherst du günstige Tarife](../content/posts/2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026/index.md) | 5 | nicht ausgewiesen | – | 190 | 6 / 8.67 |
| [Gasrechnung senken: Welche Fehler lassen sich vor der Heizperiode vermeiden?](../content/posts/2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden/index.md) | 4 | nicht ausgewiesen | – | 183 | 10 / 5.70 |
| [DSL-Anbieterwechsel: Ablauf, Ausfallzeiten und Effektivpreis](../content/posts/2026-08-14-internet-dsl-wechseln-praxis-tipps-fuer-den-anbieterwechsel/index.md) | 3 | nicht ausgewiesen | – | 181 | 3 / 7.67 |
| [Sparen im Herbst: Spartipps für die goldene Jahreszeit](../content/posts/2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit/index.md) | 1 | nicht ausgewiesen | Preisstand, Sparbetrag, Frist | 218 | 2 / 4.00 |
| [WLAN verbessern: So bringst du stabilen Speed in jede Ecke](../content/posts/2026-08-14-wlan-verbessern-so-bringst-du-speed-in-jede-ecke/index.md) | 3 | nicht ausgewiesen | – | 230 | – |
| [Abos und Verträge: Der stille Posten im Haushaltsplan](../content/posts/2026-08-17-abos-und-vertraege-stiller-posten-haushaltsplan/index.md) | 3 | ausstehend | – | 223 | – |
| [Kostenloses Girokonto: Ein Konto ohne Gebühren finden](../content/posts/2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren/index.md) | 6 | nicht ausgewiesen | – | 202 | 29 / 36.55 |
| [Privathaftpflicht: Was schützt sie und was kostet sie?](../content/posts/2026-08-17-privathaftpflicht-warum-sie-so-wichtig-ist-und-was-sie-kostet/index.md) | 3 | freigegeben | – | 186 | – |
| [Wohngebäudeversicherungen vergleichen: Auf diese Leistungen kommt es an](../content/posts/2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst/index.md) | 3 | freigegeben | – | 282 | 7 / 40.29 |
| [DSL-Vergleich: So findest du den günstigsten Internettarif](../content/posts/2026-08-19-dsl-vergleich-so-findest-du-guenstigeres-internet/index.md) | 3 | nicht ausgewiesen | Sparbetrag | 182 | 4 / 65.00 |
| [Energiediebe stoppen: So kannst du Stromfresser finden](../content/posts/2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden/index.md) | 5 | nicht ausgewiesen | – | 165 | – |
| [DSL-Tarif für dein Zuhause: Das passende Angebot finden](../content/posts/2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause/index.md) | 3 | nicht ausgewiesen | – | 182 | – |
| [Haushaltsbuch führen: App, Excel oder Stift im Vergleich](../content/posts/2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier/index.md) | 3 | nicht ausgewiesen | Sparbetrag | 169 | 11 / 6.36 |
| [Mietwagen ohne Kautionsfallen: So sparst du im Urlaub](../content/posts/2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub/index.md) | 1 | nicht ausgewiesen | Preisstand | 173 | 4 / 33.50 |
| [Frugalismus-Tipps: Mehr Freiheit durch klugen Verzicht](../content/posts/2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps/index.md) | 3 | nicht ausgewiesen | Preisstand | 192 | 7 / 9.86 |
| [Preisgarantie Gas: Was bei Preiserhöhung hilft](../content/posts/2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen/index.md) | 5 | nicht ausgewiesen | – | 172 | 4 / 9.50 |
| [DNS-Server wechseln: Datenschutz, Filter und Einrichtung](../content/posts/2026-08-26-dns-server-wechseln-schnelleres-sichereres-internet/index.md) | 8 | nicht ausgewiesen | – | 179 | 1 / 4.00 |
| [Handytarif 2026 vergleichen: Günstige Tarife ab 4,99 €](../content/posts/2026-08-26-handytarif-vergleichen-2026-guenstige-tarife/index.md) | 3 | nicht ausgewiesen | Preisstand, Sparbetrag | 173 | – |
| [Kfz-Versicherung Vergleich 2026: Bis zu 800 € sparen](../content/posts/2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen/index.md) | 5 | freigegeben | Sparbetrag, Frist | 189 | – |
| [Tagesgeld-Zinsen 2026: Die besten Zinssätze im Vergleich](../content/posts/2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich/index.md) | 3 | nicht ausgewiesen | Sparbetrag | 208 | – |
| [Warmwasser sparen: Was kostet dich eine Dusche?](../content/posts/2026-08-26-warmwasser-sparen-rechnung-hinter-dem-hahn/index.md) | 7 | ausstehend | – | 169 | – |
| [Lastschrift und Dauerauftrag: Was du prüfen solltest](../content/posts/2026-08-28-lastschrift-und-dauerauftrag-abbuchungen-pruefen/index.md) | 3 | ausstehend | – | 184 | – |
| [Nachtstrom-Tarife: Wann sich ein Doppeltarifzähler lohnt](../content/posts/2026-08-31-nachtstrom-tarife-wann-sich-ein-doppeltarifzaehler-noch-lohnt/index.md) | 4 | ausstehend | – | 185 | – |
| [Störung beim Internetanbieter: So sicherst du deine Rechte](../content/posts/2026-08-31-stoerung-beim-internetanbieter-so-sicherst-du-deine-rechte/index.md) | 4 | ausstehend | – | 168 | – |
| [September-Roadtrip: Clevere Wege zum Mietwagen-Schnäppchen](../content/posts/2026-09-02-september-roadtrip-clevere-wege-zum-mietwagen-schnaeppchen/index.md) | 2 | nicht ausgewiesen | Sparbetrag | 205 | – |
| [Kreditkarte vergleichen: Kostenlos und sicher zahlen](../content/posts/2026-09-03-kreditkarte-vergleichen-kostenlos-sicher-bezahlen/index.md) | 3 | nicht ausgewiesen | – | 172 | – |
| [DNS-Hack testen: Antwortzeit statt gefühltem Tempo](../content/posts/2026-09-04-digitaler-turbo-warum-der-dns-hack-dein-netz-beschleunigt/index.md) | 4 | nicht ausgewiesen | – | 158 | – |
| [Finanzielle Freiheit: Wie du eine Sparroutine aufbaust](../content/posts/2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich/index.md) | 3 | nicht ausgewiesen | – | 192 | – |
| [Umzug mit Internet: Anschluss und Rufnummer mitnehmen](../content/posts/2026-09-04-umzug-mit-internet-anschluss-und-rufnummer-mitnehmen/index.md) | 4 | ausstehend | – | 184 | – |
| [Frugalismus für Einsteiger: Mit kleinen Schritten sparen](../content/posts/2026-09-07-frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum/index.md) | 3 | nicht ausgewiesen | – | 190 | – |
| [Alltagsfehler vermeiden: 5 Frugalismus-Tipps im Überblick](../content/posts/2026-09-07-frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler/index.md) | 4 | nicht ausgewiesen | – | 188 | – |
| [Heizkosten senken: Welche Maßnahmen passen zu deiner Wohnung?](../content/posts/2026-09-07-heizkosten-senken-mit-diesen-strategien-sparst-du-sofort/index.md) | 3 | nicht ausgewiesen | Pauschalaussage | 175 | – |
| [Notgroschen: Die Wahrheit über das finanzielle Polster](../content/posts/2026-09-09-notgroschen-die-wahrheit-ueber-das-finanzielle-polster/index.md) | 3 | nicht ausgewiesen | – | 171 | – |
| [5 einfache Frugalismus-Tricks für den Alltag: Geld sparen](../content/posts/2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag/index.md) | 5 | nicht ausgewiesen | – | 174 | – |
| [50-30-20-Regel: Beherrsche dein Budget – Fixkosten senken](../content/posts/2026-09-11-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026/index.md) | 4 | nicht ausgewiesen | – | 177 | – |
| [Heizungs-Check vor dem Frost: Probelauf, Thermostate, Druck](../content/posts/2026-09-11-guenstig-durch-den-winter-heizungs-check-im-spaetsommer/index.md) | 3 | nicht ausgewiesen | – | 170 | – |
| [Standby Kosten reduzieren: So entlarvst du Stromfresser](../content/posts/2026-09-11-standby-kosten-reduzieren-so-entlarvst-du-stromfresser/index.md) | 3 | nicht ausgewiesen | – | 176 | – |
| [Finanzieller Puffer: Der Rechenweg in fünf Minuten](../content/posts/2026-09-20-finanzieller-puffer-wie-viel-notgroschen-ist-genug/index.md) | 3 | nicht ausgewiesen | – | 193 | – |
| [Gasrechnung lesen: Zählerstand, kWh und Abschlag einordnen](../content/posts/2026-09-20-gasrechnung-senken-so-bereitest-du-dich-im-spaetsommer-vor/index.md) | 3 | nicht ausgewiesen | – | 180 | – |
| [Gasrechnung in 60 Minuten: Ablauf für Tarif und Heizung](../content/posts/2026-09-20-gasrechnung-senken-spaetsommer-check-spart-hunderte-euro/index.md) | 4 | nicht ausgewiesen | – | 180 | – |
| [Grundversorgung Strom und Gas: Was sie leistet und kostet](../content/posts/2026-09-21-grundversorgung-strom-und-gas-was-sie-leistet/index.md) | 3 | ausstehend | – | 150 | – |
| [Einlagensicherung: Wie viel Guthaben geschützt ist](../content/posts/2026-09-23-einlagensicherung-wie-viel-guthaben-geschuetzt-ist/index.md) | 3 | ausstehend | – | 170 | – |
| [DSL-Tarif prüfen: Effektivpreis statt Lockpreis](../content/posts/2026-09-24-internet-dsl-update-was-sich-jetzt-fuer-dich-aendert/index.md) | 3 | nicht ausgewiesen | – | 183 | – |
| [WLAN-Repeater oder Mesh: Was passt zu deiner Wohnung?](../content/posts/2026-09-27-wlan-verstaerker-vs-mesh-wlan-was-brauchst-du-wirklich/index.md) | 3 | nicht ausgewiesen | Preisstand | 182 | – |
| [Zählerstand ablesen und melden: Schätzwerte vermeiden](../content/posts/2026-09-28-zaehlerstand-ablesen-und-melden-schaetzwerte-vermeiden/index.md) | 3 | ausstehend | – | 169 | – |
| [Großeinkauf und Vorrat: Wann Bevorraten sich rechnet](../content/posts/2026-09-30-grosseinkauf-und-vorrat-wann-bevorraten-sich-rechnet/index.md) | 3 | ausstehend | Pauschalaussage | 161 | – |
| [Last Minute Urlaub: So findest du echte Reiseschnäppchen](../content/posts/2026-09-30-last-minute-urlaub-so-schnappst-du-dir-das-sommer-schnaepp/index.md) | 3 | nicht ausgewiesen | – | 180 | – |
| [Gasabschlag berechnen: So planst du die Heizsaison richtig](../content/posts/2026-10-02-gasabschlag-berechnen-so-planst-du-die-heizsaison-richtig/index.md) | 3 | ausstehend | Sparbetrag | 203 | – |
| [Preiswert surfen: DSL, Kabel oder Glasfaser im Vergleich](../content/posts/2026-10-02-preiswert-surfen-so-findest-du-den-optimalen-dsl-anschluss/index.md) | 3 | ausstehend | Sparbetrag | 192 | – |
| [Weihnachtsbudget planen: Geschenke und Feiertage ohne Schulden](../content/posts/2026-10-02-weihnachten-budget-planen-ohne-schulden-durch-die-feiertage/index.md) | 3 | ausstehend | – | 163 | – |
| [Büroausstattung steuerlich clever absetzen: So geht's](../content/posts/2026-10-05-bueroausstattung-steuerlich-clever-absetzen-so-vermeidest/index.md) | 1 | ausstehend | Preisstand | 179 | – |
| [Der erste eigene Haushalt: Fixkosten von Anfang an ordnen](../content/posts/2026-10-05-erster-eigener-haushalt-fixkosten-richtig-ordnen/index.md) | 4 | ausstehend | – | 164 | – |
| [Sieben Gewohnheiten für den Umgang mit deinem Geld](../content/posts/2026-10-07-7-gewohnheiten-fuer-finanzielle-freiheit/index.md) | 2 | ausstehend | – | 149 | – |
| [Campingurlaub planen: Budget für Platz und Fahrt](../content/posts/2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust/index.md) | 3 | ausstehend | Pauschalaussage | 177 | – |
| [Treue-Falle beim DSL-Vertrag: Wann sich der Wechsel rechnet](../content/posts/2026-10-07-dsl-anbieter-wechseln-warum-treue-dich-bares-geld-kostet/index.md) | 2 | ausstehend | – | 146 | – |
| [Handyvertrag kündigen: Enddatum, Nachweis und Rufnummer](../content/posts/2026-10-07-handyvertrag-kuendigen-raus-aus-der-kostenfalle-verlaengerung/index.md) | 4 | ausstehend | – | 162 | – |
| [Urlaub sparen: Budget, Buchung und Kosten im Blick](../content/posts/2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen/index.md) | 4 | ausstehend | Pauschalaussage | 166 | – |
| [Smart Home: Spart die Automatisierung mehr Strom, als sie verbraucht?](../content/posts/2026-10-07-wie-smart-home-geraete-deine-stromrechnung-wirklich-druecken/index.md) | 2 | ausstehend | – | 168 | – |
| [Balkonkraftwerk Förderung: So holst du dir Geld zurück](../content/posts/2026-10-09-balkonkraftwerk-foerderung-so-holst-du-dir-geld-zurueck/index.md) | 5 | ausstehend | – | 172 | – |
| [Energiekosten senken: Smarte Helfer für den Haushalt](../content/posts/2026-10-09-energiekosten-senken-smarte-helfer-fuer-den-haushalt/index.md) | 1 | ausstehend | – | 173 | – |
| [VPN Zuhause: Schutzschild oder unnötige Fixkosten-Falle?](../content/posts/2026-10-09-vpn-zuhause-schutzschild-oder-unnoetige-fixkosten-falle/index.md) | 2 | ausstehend | – | 172 | 7 / 10.00 |
| [Dein Weg zu geringeren Monatskosten: Schritt für Schritt](../content/posts/2026-10-12-dein-weg-zu-geringeren-monatskosten-schritt-fuer-schritt/index.md) | 1 | ausstehend | – | 186 | 1 / 7.00 |
| [Energieausweis: Was er für deine Fixkosten bedeutet](../content/posts/2026-10-12-energieausweis-was-das-dokument-fuer-deine-fixkosten/index.md) | 1 | ausstehend | – | 163 | – |
| [Haushaltskosten reduzieren: So gewinnst du die Kontrolle](../content/posts/2026-10-12-haushaltskosten-reduzieren-so-gewinnst-du-die-kontrolle/index.md) | 1 | ausstehend | – | 181 | 24 / 45.92 |
| [Energie sparen: Welche kleinen Änderungen sich im Alltag lohnen](../content/posts/2026-10-12-kleine-energiespar-tricks-die-deine-kosten-sofort-senken/index.md) | 1 | ausstehend | – | 171 | 59 / 32.49 |
| [Wärmepumpe vs. Gasheizung 2026: So entscheidest du richtig](../content/posts/2026-10-12-waermepumpe-vs-gasheizung-2026-so-entscheidest-du-richtig/index.md) | 1 | ausstehend | Sparbetrag | 168 | 1 / 9.00 |
| [Stromkosten senken: Clevere Haushaltsgeräte im Überblick](../content/posts/2026-10-23-stromkosten-senken-clevere-haushaltsgeraete-im-ueberblick/index.md) | 1 | ausstehend | – | 165 | 2 / 4.50 |
| [Bankgebühren senken: 7 Schritte zum günstigeren Konto](../content/posts/2026-10-24-bankgebuehren-senken-7-schritte-zum-guenstigeren-konto/index.md) | 1 | ausstehend | – | 167 | – |
| [Energieeffizienz im Haushalt: 5 schnelle Spartricks](../content/posts/2026-10-24-energieeffizienz-im-haushalt-5-schnelle-spartricks/index.md) | 1 | ausstehend | – | 164 | – |
| [ETF-Sparplan starten: Deine Schritt-für-Schritt-Anleitung](../content/posts/2026-10-24-etf-sparplan-starten-schritt-fuer-schritt-zum-monatlichen/index.md) | 1 | ausstehend | – | 152 | 5 / 13.40 |
| [Strategisch sparen: So kannst du deine Reisekasse füllen](../content/posts/2026-10-25-strategisch-sparen-so-kannst-du-deine-reisekasse-fuellen/index.md) | 3 | ausstehend | – | 180 | – |
| [Frugalismus mit Familie: Gemeinsam über Ausgaben entscheiden](../content/posts/2026-10-27-frugalismus-familie-clever-sparen-ohne-verzicht/index.md) | 1 | ausstehend | – | 170 | – |
| [Flugvergleich im Winter: So findest du echte Billigflüge](../content/posts/2026-10-28-flugvergleich-im-winter-so-findest-du-echte-billigfluege/index.md) | 1 | ausstehend | – | 183 | – |
| [Ökostromanbieter wechseln: Tarif, Herkunft und Preis prüfen](../content/posts/2026-10-28-oekostrom-anbieter-wechseln-sicher-gruen-und-bezahlbar/index.md) | 3 | ausstehend | Pauschalaussage | 167 | 23 / 21.17 |
| [Gaspreiserhöhung in der Grundversorgung: Wann kannst du kündigen?](../content/posts/2026-10-30-gaspreiserhoehung-sonderkuendigungsrecht-raus-aus-dem/index.md) | 1 | ausstehend | – | 183 | – |
| [Flugverspätung: Wann kommt eine Entschädigung infrage?](../content/posts/2026-11-01-flugverspaetung-entschaedigung-so-holst-du-dein-geld-zurueck/index.md) | 2 | ausstehend | – | 188 | – |
| [Waschmaschine beladen: Weniger Kosten bei jedem Waschgang](../content/posts/2026-11-05-waschmaschine-beladen-weniger-kosten-bei-jedem-waschgang/index.md) | 8 | ausstehend | – | 187 | 1 / 50.00 |
| [Fenster abdichten: So stoppst du Zugluft an alten Rahmen](../content/posts/2026-11-10-fenster-abdichten-so-stoppst-du-zugluft-an-alten-rahmen/index.md) | 1 | ausstehend | – | 193 | – |
| [Kaffeemaschine: Was kostet eine Tasse wirklich?](../content/posts/2026-11-10-kaffeemaschine-stromverbrauch-was-kostet-die-tasse-kaffee/index.md) | 1 | ausstehend | – | 176 | – |
| [WLAN verbessern: So findest du einen guten Platz für den Router](../content/posts/2026-11-10-wlan-frust-loesen-so-findest-du-den-besten-router-standort/index.md) | 1 | ausstehend | – | 156 | – |
| [Wie viel Bandbreite brauchst du fürs Streaming?](../content/posts/2026-11-12-wie-viel-streaming-bandbreite-du-wirklich-brauchst-dein/index.md) | 1 | ausstehend | – | 161 | – |
| [Geschenkkarte: Was du beim Kauf und Aufladen wissen musst](../content/posts/2026-11-13-geschenkkarte-was-du-beim-kauf-und-aufladen-wissen-musst/index.md) | 1 | ausstehend | – | 176 | – |
| [Mesh-WLAN nachrüsten: Wann lohnt sich die Investition?](../content/posts/2026-11-13-mesh-wlan-nachruesten-schluss-mit-funkloechern-in-der-wohnung/index.md) | 1 | ausstehend | – | 172 | – |
| [Secondhand-Kleidung kaufen: So prüfst du Stoff, Nähte und Passform](../content/posts/2026-11-13-secondhand-kleidung-so-erkennst-du-qualitaet-sparst/index.md) | 1 | ausstehend | – | 175 | – |

## Wiederholen

1. `python3 scripts/copy_editing_gate.py --strict` ausführen; zusätzlich Titel, Teaser, Kurzantwort und Modellannahmen redaktionell prüfen.
2. Mit der gepinnten Hugo-Version `hugo --minify -d /tmp/ffsite` bauen und diesen Ordner lokal auf Port 4173 ausliefern.
3. Nach `npm ci --ignore-scripts`: `node scripts/archiv_ladeprobe.mjs http://127.0.0.1:4173` sowie `node scripts/lighthouse_live.mjs --basis http://127.0.0.1:4173 --url / --laeufe 3 --json`.
4. Rankings aus dem regulären autorisierten `gsc-import.yml` aktualisieren. Niemals lokale Ladezeiten als Produktionswerte oder fehlende GSC-Zeilen als Rankingverlust ausweisen.
