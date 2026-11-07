# F4-Entscheidungsvorlage – Runde 2 zu #1098

**Stand:** 07.11.2026 · **Entscheider:** Frank Hartung (Herausgeber) · **Branch:** `arena/9e00ce3a-franksfinanzcheck-blog`

## Warum es diese Runde gibt

Der erste Dispatch der Release-Scorecard auf `main` (Lauf [42384831745](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/42384831745)) ist durchgelaufen und hat ehrlich **rot** gemeldet: Siegel `d1e1c4a`, 15:11:47 UTC, `tool_fehler: {}`, blockiert sind genau drei Live-Seiten mit zwölf Fachbefunden.

* zehn **neue** Befunde auf „Energiediebe stoppen“ und „Warmwasser sparen“ – unten inhaltlich behoben,
* zwei **wieder eröffnete** Befunde auf „50-30-20-Regel“: Der Textpflege-Bot hat in `d1e1c4a` nur die automatisch abgeleitete Zeile `*Abbildung: Gliederung …*` neu geschrieben. Dadurch änderte sich der Text-Hash und die Fassungsbindung der ersten Entscheidung lief aus. Der geprüfte Inhalt ist unverändert → Folgeentscheidung, **keine** Aufweichung der Hash-Bindung.

Die beiden Artikel sind bereits überarbeitet (Commit `330e628`). Einzelnachweis nach der Änderung: `technik ✅ · quellen ✅ · affiliate ✅ · redundanz ✅`, offen allein der jeweilige F4-Befund, der auf diese Freigabe wartet.

**Entscheidungsweg:** Für jeden Befund wird nach deiner Zustimmung `faktenfrische_befund_ledger.py --entscheiden <ID> --von "Frank Hartung (Herausgeber-Auftrag über Arena-Session, 07.11.2026)"` mit der untenstehenden Begründung und dem Beleg geschrieben, danach Befund-Akte, Live-Nachmessung und Siegel.

## Energiediebe stoppen: So kannst du Stromfresser finden

`2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden` · heutige Fassung `5fbc5cefce29…`

### 1. Messdauer für Kühl- und Gefriergeräte

* **Befund-ID:** `43470330b3b48c9cee49` (luecke)
* **Beanstandung:** Der Artikel empfiehlt, Kühl- und Gefriergeräte mindestens 24 Stunden, besser mehrere Tage zu messen, liefert jedoch keine Quelle für diese Messdauer.
* **Neue Fassung / Erledigung:** Alle sieben Textstellen (Kurzantwort, Schnellstart, Tipps, Messdauer-Liste, Messwoche, Fazit, FAQ) sagen jetzt einheitlich **sieben Tage messen, dann auf ein Jahr hochrechnen**, mit Inline-Link auf die Verbraucherzentrale. Wortlaut Messdauer-Liste: „**Kühl- und Gefriergerät:** sieben vollständige Tage, dann auf ein Jahr hochrechnen. So empfiehlt es die Verbraucherzentrale, weil sich Kühl- und Abtauzyklen erst über eine Woche ausmitteln.“ Die Tabellenzeile „kWh pro 24 Stunden“ ist durch eine echte Messwoche (Dienstag Start → Dienstag darauf Ablesung) ersetzt.
* **Beleg:** https://www.verbraucherzentrale.de/wissen/energie/strom-sparen/so-finden-sie-den-passenden-kuehlschrank-10573
* **Vorgesehene Entscheidung:** Befund behoben, Entscheidung bindet an die heutige Fassung – Begründung: Beanstandung inhaltlich behoben: Die bisher unbelegte 24-Stunden-Angabe ist durch die quellengedeckte Sieben-Tage-Messung der Verbraucherzentrale ersetzt; jede Nennstelle im Artikel fuehrt die Quelle inline.

### 2. Ausleihe von Energiekostenmessgeräten

* **Befund-ID:** `95d6d2877620e5a056ce` (luecke)
* **Beanstandung:** Die Aussage, dass Verbraucherzentralen oder Bibliotheken Messgeräte verleihen, wird ohne Beleg gemacht.
* **Neue Fassung / Erledigung:** Statt „Viele Verbraucherzentralen und Büchereien leihen solche Geräte aus“ jetzt: „Die Verbraucherzentrale weist darauf hin, dass du solche Geräte in ihren Beratungsstellen ausleihen kannst. Verfügbarkeit und Pfand regelt jede Stelle selbst, also frag vorher nach.“ Die unbelegte Behauptung zu Büchereien ist ersatzlos gestrichen.
* **Beleg:** https://www.verbraucherzentrale.de/wissen/energie/strom-sparen/so-finden-sie-den-passenden-kuehlschrank-10573
* **Vorgesehene Entscheidung:** Befund behoben, Entscheidung bindet an die heutige Fassung – Begründung: Beanstandung inhaltlich behoben: Aussage auf die belegte Ausleihe in VZ-Beratungsstellen verengt, regionale Unterschiede ausdruecklich benannt, unbelegter Bibliotheks-Hinweis entfernt.

### 3. Strompreis 0,37 €/kWh

* **Befund-ID:** `ab16029999747466a638` (luecke)
* **Beanstandung:** Die Berechnung mit einem Arbeitspreis von 0,37 €/kWh wird angegeben, ohne dass ein aktueller Preis‑ oder Marktwert belegt wird.
* **Neue Fassung / Erledigung:** Erste Nennstelle trägt jetzt Quelle, Stand und Durchschnitts-Charakter: „Der BDEW nennt für Haushalte im Oktober 2026 einen Durchschnittspreis von 37,3 Cent je kWh. Mit diesen 0,37 € pro kWh kostet die Gruppe rund 58 € jährlich. Dein eigener Arbeitspreis steht im Vertrag und kann deutlich abweichen.“ Quellenliste auf die geprüfte Herbst-Ausgabe (28.10.2026) datiert.
* **Beleg:** https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/
* **Vorgesehene Entscheidung:** Befund behoben, Entscheidung bindet an die heutige Fassung – Begründung: Beanstandung inhaltlich behoben: Rechenwert 0,37 EUR/kWh entspricht dem BDEW-Haushaltsdurchschnitt Oktober 2026 (37,3 ct/kWh, Stand 28.10.2026), inline verlinkt und als Durchschnitt mit Vorrang des eigenen Tarifs gekennzeichnet.

### 4. Amortisationsbeispiel 650 € / 10,3 Jahre

* **Befund-ID:** `b057dee3603e09f494b5` (luecke)
* **Beanstandung:** Das Amortisationsbeispiel (Kaufpreis 650 €, Amortisationszeit 10,3 Jahre) enthält keine Quelle für die zugrunde liegenden Annahmen oder Preise.
* **Neue Fassung / Erledigung:** Rahmen jetzt explizit: „**Rechenbeispiel mit frei gewählten Werten, keine Marktangaben:** Angenommen, dein altes Gerät verbraucht 310 kWh im Jahr und ein passendes Neugerät ist mit 140 kWh angegeben. Ersetze beide Werte durch deine Messung und das EU-Energielabel des Wunschgeräts.“ Listenzeile: „Angenommener Kaufpreis: **650 €** (frei gewählt, kein Marktpreis)“. Die Rechenwerte 170 kWh Differenz, 62,90 € und 10,3 Jahre bleiben unverändert und korrekt nachrechenbar.
* **Beleg:** https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/
* **Vorgesehene Entscheidung:** Befund behoben, Entscheidung bindet an die heutige Fassung – Begründung: Beanstandung inhaltlich behoben: Kaufpreis und Verbrauchswerte sind als frei gewaehlte Modellannahmen ohne Marktbezug gekennzeichnet; der Leser wird auf eigene Messung und EU-Energielabel verwiesen, der Preisfaktor ist auf BDEW belegt.

### 5. Regulatorischer Rahmen / fest verbaute Geräte

* **Befund-ID:** `8ddc1025e45be176ad3a` (luecke)
* **Beanstandung:** Es wird kein regulatorischer Rahmen (z. B. Aufgaben der Bundesnetzagentur) genannt, obwohl das Thema Stromversorgung berührt wird; entsprechende Vorgaben fehlen im Text.
* **Neue Fassung / Erledigung:** Neuer Absatz an der Messstellen-Stelle: „Für fest verbaute Geräte brauchst du einen Fachbetrieb. Dein Haushaltszähler erfasst nur die Summe aller Geräte, nicht den einzelnen Verbrauch. Zuständig für Einbau, Betrieb und Prüfung dieses Zählers ist der Messstellenbetreiber. Die Bundesnetzagentur erklärt dazu die Rechte der Anschlussnutzer: Bei Zweifeln an der messtechnischen Richtigkeit kannst du eine Befundprüfung des Zählers beantragen.“
* **Beleg:** https://www.bundesnetzagentur.de/DE/Vportal/Energie/Metering/artikel.html
* **Vorgesehene Entscheidung:** Befund behoben, Entscheidung bindet an die heutige Fassung – Begründung: Beanstandung inhaltlich behoben: Zustaendigkeit des Messstellenbetreibers und das Recht auf Befundpruefung sind mit dem Verbraucherportal der Bundesnetzagentur belegt und im Artikel inline verlinkt.

## Warmwasser sparen: Die Rechnung hinter dem Hahn

`2026-08-26-warmwasser-sparen-rechnung-hinter-dem-hahn` · heutige Fassung `96b35a43a8a5…`

### 1. Legionellen / gesetzliche Temperaturvorgaben

* **Befund-ID:** `278d89267d9122a1e9d8` (luecke)
* **Beanstandung:** Angaben zu gesetzlichen Vorgaben für Warmwassertemperaturen zur Vermeidung von Legionellen werden nicht durch die bereitgestellten Quellen gestützt.
* **Neue Fassung / Erledigung:** Aus dem unbelegten „Fachbetriebe empfehlen üblicherweise …“ ist eine belegte Aussage geworden: „Im gesamten Warmwasser-Leitungssystem sollen mindestens 55 °C herrschen. Für größere Anlagen schreibt das die Trinkwasserverordnung vor.“ – zweiter Absatz: „In Speichern mit mehr als 400 Litern muss das Wasser am Speicherausgang gemäß Trinkwasserverordnung immer mindestens 60 °C erreichen. Dasselbe gilt für Leitungen, in denen mehr als drei Liter warmes Wasser stehen. Prüfe die Einstellung deshalb alle drei Monate.“ Jeweils mit Inline-Link auf den VZ-Ratgeber (Stand 21.07.2026).
* **Beleg:** https://www.verbraucherzentrale.de/wissen/energie/heizen-und-warmwasser/kosten-fuer-warmwasser-senken-das-koennen-sie-als-hausbesitzer-tun-17755
* **Vorgesehene Entscheidung:** Befund behoben, Entscheidung bindet an die heutige Fassung – Begründung: Beanstandung inhaltlich behoben: 55 Grad im Leitungssystem, 60 Grad am Speicherausgang bei ueber 400 Litern bzw. ueber 3 Litern Leitungsinhalt und die Dreimonatspruefung sind mit dem VZ-Ratgeber vom 21.07.2026 samt Bezug zur Trinkwasserverordnung belegt.

### 2. „Zweitgrößter Kostenposten“ (Text, Description, Pinterest)

* **Befund-ID:** `450c3aa629342062825e` (luecke)
* **Beanstandung:** Die Aussage, dass Warmwasser der zweitgrößte Kostenposten im Haushalt ist, wird nicht durch eine der bereitgestellten Quellen belegt.
* **Neue Fassung / Erledigung:** Die nicht belegbare Rangbehauptung ist überall entfernt. Neu: „co2online beziffert die Wassererwärmung auf rund 16 Prozent des gesamten Haushalts-Energieverbrauchs, die Raumwärme auf rund zwei Drittel. Warmwasser ist damit – neben dem Haushaltsstrom – einer der beiden großen Blöcke hinter der Heizung. Das sind Durchschnittswerte; wie viel Euro daraus werden, hängt an deinem Tarif und deiner Nutzung.“ Description und pin_description sagen jetzt „Warmwasser braucht rund 16 Prozent der Haushaltsenergie“. Die FAQ nennt die 16 Prozent als Faustgröße mit Quelle.
* **Beleg:** https://www.co2online.de/energie-sparen/
* **Vorgesehene Entscheidung:** Befund behoben, Entscheidung bindet an die heutige Fassung – Begründung: Beanstandung inhaltlich behoben: Die Rangbehauptung zum Kostenposten ist gestrichen und durch den belegten Energieanteil von rund 16 Prozent (co2online, Grafik Stand 10/2025) ersetzt; Kostenbezug ausdruecklich als tarifabhaengig gekennzeichnet, auch in Description und pin_description.

### 3. Eigener Warmwasserblock auf der Abrechnung

* **Befund-ID:** `7601167c9f3560093fb0` (luecke)
* **Beanstandung:** Die Behauptung, dass Warmwasser in der Heizkostenabrechnung üblicherweise als eigener Block ausgewiesen wird, fehlt eine Quellenangabe.
* **Neue Fassung / Erledigung:** Aus „üblicherweise“ wurde eine Rechtsgrundlage: „Bei zentraler Versorgung ist diese Trennung vorgeschrieben: § 9 Heizkostenverordnung verlangt, die gemeinsam entstandenen Kosten einer verbundenen Anlage in einen Heiz- und einen Warmwasseranteil aufzuteilen. Die Warmwassermenge soll dafür mit einem Wärmezähler gemessen werden; Ersatzformeln sind nur bei unzumutbarem Aufwand zulässig. Verteilt werden beide Anteile getrennt – Wärme nach § 7, Warmwasser nach § 8.“ Der Dezentral-Fall (Durchlauferhitzer/Boiler → Stromrechnung) bleibt ausdrücklich getrennt beschrieben.
* **Beleg:** https://www.gesetze-im-internet.de/heizkostenv/__9.html
* **Vorgesehene Entscheidung:** Befund behoben, Entscheidung bindet an die heutige Fassung – Begründung: Beanstandung inhaltlich behoben: Die Pflicht zur Kostentrennung bei verbundenen Anlagen ist mit Paragraph 9 Absatz 1, 2 und 4 Heizkostenverordnung im amtlichen Wortlaut belegt und inline verlinkt.

### 4. Verbraucherzentrale-Fundstellen passen nicht zur Aussage

* **Befund-ID:** `7efbcd7a4275fe1577bb` (luecke)
* **Beanstandung:** Verweise auf die Verbraucherzentrale (Tipps zum Heizkosten sparen, Heizung optimieren) können nicht mit den angegebenen Fundstellen belegt werden.
* **Neue Fassung / Erledigung:** Die Verweise zeigen jetzt auf die Seiten, die die jeweilige Aussage wirklich tragen: Speicher-/Temperaturverluste und Hygiene → „Kosten für Warmwasser senken“ (17755); lückenlose Rohrdämmung → „Heizung optimieren … so geht’s“ (30096, kanonische URL, Stand 08.10.2026); Auslitern des Duschkopfs und Schwelle unter 9 l/min → „Warmwasser im Alltag sparen“ (17752). Der inhaltsleere Verweis auf 13892 ist aus Text und Quellenliste entfernt; Q1 ist jetzt 17752.
* **Beleg:** https://www.verbraucherzentrale.de/wissen/energie/heizen-und-warmwasser/kosten-fuer-warmwasser-senken-das-koennen-sie-als-hausbesitzer-tun-17755 · https://www.verbraucherzentrale.de/wissen/energie/heizen-und-warmwasser/heizung-optimieren-und-heizkosten-sparen-so-gehts-30096 · https://www.verbraucherzentrale.de/wissen/energie/heizen-und-warmwasser/warmwasser-im-alltag-sparen-so-gehts-17752
* **Vorgesehene Entscheidung:** Befund behoben, Entscheidung bindet an die heutige Fassung – Begründung: Beanstandung inhaltlich behoben: Jeder VZ-Verweis fuehrt auf die Fundstelle, die die behauptete Aussage tatsaechlich enthaelt; der unpassende Verweis 13892 ist entfernt und die Quellenliste entsprechend korrigiert.

### 5. Modellpreis 0,30 €/kWh

* **Befund-ID:** `971a719f94ca492f640e` (luecke)
* **Beanstandung:** Der Preis von 0,30 € pro Kilowattstunde in der Modellrechnung ist nicht mit einer Quelle belegt.
* **Neue Fassung / Erledigung:** Tabelleneinleitung jetzt: „Die Euro-Werte rechnen mit frei gewählten 0,30 € je Kilowattstunde – kein Marktpreis, sondern eine Rechenannahme. Zum Vergleich: Der BDEW nennt für Haushaltsstrom im Oktober 2026 durchschnittlich 37,3 Cent je kWh. Bei zentraler Heizung gilt ohnehin dein Gas- oder Wärmepreis, nicht der Strompreis. Setze deshalb deinen eigenen Tarif ein.“ Die Tabellenwerte (840/561/279 €) bleiben als reine Modellrechnung bestehen.
* **Beleg:** https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/
* **Vorgesehene Entscheidung:** Befund behoben, Entscheidung bindet an die heutige Fassung – Begründung: Beanstandung inhaltlich behoben: 0,30 EUR/kWh ist als frei gewaehlte Rechenannahme ohne Marktpreisanspruch gekennzeichnet, dem belegten BDEW-Durchschnitt gegenuebergestellt und um den Hinweis auf Gas- bzw. Waermepreis bei zentraler Versorgung ergaenzt.

## 50-30-20-Regel: Beherrsche dein Budget im Jahr 2026

`2026-09-11-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026` · heutige Fassung `88d3a800cafc…`

### 1. Energiepreistrend (Folgeentscheidung nach Bot-Textpflege)

* **Befund-ID:** `6cb2229c5eb83b02da23` (veraltet)
* **Beanstandung:** Die Kalkulation der Fixkosten (Energie 140 €) und die Empfehlung zur Senkung der Kosten ignorieren den aktuellen Markttrend massiv steigender Energiepreise (+14,9 %), was die 50-Prozent-Quote für notwendige Ausgaben gefährdet.
* **Neue Fassung / Erledigung:** Keine inhaltliche Änderung nötig: Der Absatz „Preisänderungen im Budget berücksichtigen“ enthält bereits die geprüfte Oktober-Schätzung von Destatis (PM 382 vom 30.10.2026): 2,8 Prozent Inflation, Energie +12,2 Prozent, Septemberwert 14,9 Prozent ausdrücklich als Vormonat ausgewiesen. Geändert hat sich seit der ersten Entscheidung ausschließlich die automatisch abgeleitete Bildzeile („*Abbildung: Gliederung …*“) durch Bot-Commit d1e1c4a – der geprüfte Inhalt ist wortgleich.
* **Beleg:** https://www.destatis.de/DE/Presse/Pressemitteilungen/2026/10/PD26_382_611.html
* **Vorgesehene Entscheidung:** Befund behoben, Entscheidung bindet an die heutige Fassung – Begründung: Folgeentscheidung auf der heutigen Fassung: Der Befund ist durch den Destatis-Absatz (PM 382, 30.10.2026: Energie +12,2 Prozent, September 14,9 Prozent als Vormonat) bereits behoben. Seit der Erstentscheidung hat nur der Textpflege-Bot die abgeleitete Abbildungszeile neu erzeugt; der gepruefte Inhalt ist unveraendert.

### 2. Inflationsbezug im Budget (Folgeentscheidung nach Bot-Textpflege)

* **Befund-ID:** `f00055a1cb65ee22165f` (luecke)
* **Beanstandung:** Der Ratgeber verspricht eine 'planbare' Budgetierung, lässt aber die aktuelle Inflationsrate von 2,8 % unerwähnt, die insbesondere den Block der notwendigen Ausgaben (Nahrungsmittel +0,4 %) dynamisch belastet.
* **Neue Fassung / Erledigung:** Ebenfalls keine inhaltliche Änderung nötig: 2,8 Prozent Inflation und +0,4 Prozent Nahrungsmittel stehen mit Datum und Primärquelle im Artikel, samt Handlungsanweisung („Nutze diese Zahlen als Hinweis, nicht als pauschalen Aufschlag“) und Konsequenz für die 50-Prozent-Grenze. Auch hier hat nur die abgeleitete Bildzeile den Text-Hash verändert.
* **Beleg:** https://www.destatis.de/DE/Presse/Pressemitteilungen/2026/10/PD26_382_611.html
* **Vorgesehene Entscheidung:** Befund behoben, Entscheidung bindet an die heutige Fassung – Begründung: Folgeentscheidung auf der heutigen Fassung: Die Inflationsluecke ist mit Destatis PM 382 vom 30.10.2026 (2,8 Prozent Gesamt, 0,4 Prozent Nahrungsmittel) samt Datum, Primarquelle und budgetbezogener Handlungsanweisung geschlossen; seither nur abgeleitete Bildzeile geaendert.

## Anschlussarbeit (separat, nicht Teil dieser Freigabe)

Die Wiedereröffnung durch abgeleitete Bildzeilen ist ein Konstruktionsproblem: `abbildungen_ableiten.py` ändert Text, der in die Fassungsbindung eingeht. Sauberer Weg ist, abgeleitete Bildzeilen aus dem Fassungs-Hash herauszurechnen **und** die Entscheidung an den inhaltlichen Kern zu binden – nicht, die Bindung pauschal zu lockern. Das gehört als eigener Befund in #1098, damit die Runde hier ohne Regeländerung entscheidbar bleibt.

