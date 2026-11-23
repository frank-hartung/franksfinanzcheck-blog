# F4-Entscheidungsvorlage — offene Live-Befunde (Vorschlag)

**Status: VORSCHLAG – nichts entschieden.** Die Artikel bleiben in der
Scorecard blockiert, bis der Herausgeber die heutigen Fassungen bestätigt.
Dieses Dokument schreibt nichts in den Ledger und erzeugt keine Entscheidung.

**Bezugsstand: 2026-11-23** – der Stand der Befundakte (`erzeugt` aus `data/faktenfrische_befunde_state.json`), nicht die Wanduhr. So ist die Vorlage reproduzierbar und `--check` uhrfest.

**Keine Prüfsummen im Dokument.** Maßgeblich ist, welche Befunde offen sind und ob die beanstandeten Werte heute noch im Text stehen; die Fassungsbindung führt der Ledger (`geprueft_fassung`). So altert die Vorlage nicht an fremden Commits.

**173 offene Live-Befunde auf 51 Artikeln.** Für **86** gibt es frühere Entscheidungen zu diesem Befund;
die heutige Fassung ist erneut zu prüfen – ein Rückfall ist möglich. **87** Befunde haben keine frühere aktive Entscheidung.

Erzeugt von `scripts/f4_entscheidungsvorlage.py` aus `data/faktenfrische_befunde_state.json`,
`data/faktenfrische_entscheidungen.yaml`, dem Scorecard-Siegel und den heutigen Artikeln.
Regel: F4 ist per SSOT **menschlich** – die Maschine schließt hier nichts.

## Neu ohne frühere Entscheidung

- `1b7c9b9cac0290f71242` · `2026-08-10-dsl-wechselbonus-sichern` · Aktuelle Wechselangebote ermöglichen oft Einsparungen von ca. 10 € bis 25 € pro Monat im Vergleich zu veralteten Bestandskundentarifen.
- `ee260c27a6bfdd60fa04` · `2026-08-10-dsl-wechselbonus-sichern` · Ein Tarif mit ca. 200 € bis 300 € Bonus wirkt auf den ersten Blick unschlagbar; das ist ein Modellwert.
- `1d4095501e717fb30d7b` · `2026-08-12-geld-abheben-im-ausland-gebuehren-vermeiden` · Der Hinweis auf einen „Wochenend‑Effekt“ bei Devisenkursen wird ohne Quellenangabe gemacht.
- `77520584b5afd8ebd7f7` · `2026-08-12-geld-abheben-im-ausland-gebuehren-vermeiden` · Es wird angegeben, dass der Kurs am Automaten häufig über dem Referenzkurs der Bank liegt, jedoch fehlt ein Beleg dafür.
- `a3be3d50280d4fe0a1d8` · `2026-08-12-geld-abheben-im-ausland-gebuehren-vermeiden` · Der Artikel behauptet, dass der Betreiber des Automaten ein eigenes Entgelt verlangt, ohne dafür eine Quelle anzugeben.
- `d6cc7bae16dead3e610b` · `2026-08-12-geld-abheben-im-ausland-gebuehren-vermeiden` · Die Empfehlung, nur Automaten von Banken und nicht von Aufstellern in Touristenzonen zu nutzen, ist unspezifisch und nicht durch Daten belegt.
- `29eea3c457afaba3d7bd` · `2026-08-14-wlan-verbessern-so-bringst-du-speed-in-jede-ecke` · Ein Wechsel zum modernen Provider bringt oft über 350 € in 24 Monaten; das ist eine Modellannahme.
- `8a0df5531569ec042ec4` · `2026-08-14-wlan-verbessern-so-bringst-du-speed-in-jede-ecke` · Ein freier Standplatz steigert den Empfang um bis zu 40 %.
- `bda1b543db068b3e00ff` · `2026-08-14-wlan-verbessern-so-bringst-du-speed-in-jede-ecke` · Im Check: Du zahlst jeden Monat rund 45 € für einen schnellen Anschluss; das ist ein Modellwert.
- `3a3269aa4a2e95d780ad` · `2026-08-17-abos-und-vertraege-stiller-posten-haushaltsplan` · Ein Jahresabo ohne Abbuchung im letzten Monat ist im Haushalt trotzdem eine laufende Verpflichtung
- `c3ff13d7ca048da95112` · `2026-08-17-abos-und-vertraege-stiller-posten-haushaltsplan` · Bei einer Lastschrift kannst du die Abbuchung über deine Bank zurückgeben lassen
- `ec052a0155f98740a3b5` · `2026-08-17-abos-und-vertraege-stiller-posten-haushaltsplan` · Ein Dienst, der gegen Gebühr kündigt, ändert nichts an den Fristen
- `ee3a722844f4b84b84b8` · `2026-08-17-abos-und-vertraege-stiller-posten-haushaltsplan` · Die häufigste Panne ist die Kündigung zum falschen Zeitpunkt
- `991bda7b2298b751f4e6` · `2026-08-19-dsl-vergleich-so-findest-du-guenstigeres-internet` · Die Behauptung einer garantierten Versorgung ist rechtlich zu weitgehend; die Bundesnetzagentur führt lediglich Unternehmenspflichten und die Grundversorgung als Aufsichtsthemen auf.
- `ae71596724d7a243217b` · `2026-08-19-dsl-vergleich-so-findest-du-guenstigeres-internet` · Der Artikel ignoriert die regulatorisch und technisch relevante Kupfer-Glas-Migration, welche die langfristige Verfügbarkeit und den Wechselzwang von DSL-Anschlüssen maßgeblich beeinflusst.
- `91894b9b1535765acdca` · `2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause` · Der Artikel versäumt es, den gesetzlichen Regulierungsrahmen (z. B. Entschädigung bei Wechselproblemen) zu nennen, obwohl die Fachseite der Aufsichtsbehörde als Beleg angeführt wird.
- `f7b9c93c6a9be1368b06` · `2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause` · Die Einstufung von Glasfaser als teure 'Premium-Variante' ist überholt, da neue Schnäppchentarife den Markt preislich verändern.
- `0b4755213f0c38321710` · `2026-08-26-handytarif-vergleichen-2026-guenstige-tarife` · Behauptung 'kein üblicher Wechselgewinn' ohne Daten
- `3e0c5fa74179e97866b8` · `2026-08-26-handytarif-vergleichen-2026-guenstige-tarife` · Preisangabe 9,99 € monatlich ohne Quelle
- `ae90ebae2842ff9f97f1` · `2026-08-26-handytarif-vergleichen-2026-guenstige-tarife` · Aussage über Downloadwert vs Gesprächsqualität ohne Beleg
- `b2611d9120121d0ad785` · `2026-08-26-handytarif-vergleichen-2026-guenstige-tarife` · Empfehlung, nicht den günstigsten Tarif zu wählen, fehlt Beleg
- `fcb8168c18bd423c5180` · `2026-08-26-handytarif-vergleichen-2026-guenstige-tarife` · Unterschiedliche Aufgaben von 2‑Jahres‑ vs monatlich kündbarem Vertrag ohne Beleg
- `3ad12cdcf94bd8459bd8` · `2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich` · Bei der Erläuterung von Vermittlungsportalen fehlt die Einordnung als 'Kreditdienstleistungsinstitute', die die Bundesbank als spezifischen Aspekt der Finanzaufsicht führt.
- `1cc830a25d3ae505dd0e` · `2026-08-28-lastschrift-und-dauerauftrag-abbuchungen-pruefen` · Die Frist von acht Wochen gilt für autorisierte Lastschriften (ohne Angabe von Gründen). Bei unautorisierten Lastschriften (ohne Mandat) beträgt die gesetzliche Frist zur Rückgabe 13 Monate.
- `32f827af8f4695488e97` · `2026-08-28-lastschrift-und-dauerauftrag-abbuchungen-pruefen` · Banken dürfen vom Zahler (Kontoinhaber) in der Regel kein Entgelt für eine Rücklastschrift verlangen, die mangels Deckung oder wegen eines berechtigten Widerspruchs erfolgt.
- `642d9c53e557ff642257` · `2026-08-28-lastschrift-und-dauerauftrag-abbuchungen-pruefen` · Es fehlt der Hinweis auf die gesetzliche 13-Monats-Frist gemäß Zahlungsdiensterecht (PSD2) für die Meldung nicht autorisierter oder fehlerhafter Kartenzahlungen.
- `8230373c2c33722d66d8` · `2026-08-28-lastschrift-und-dauerauftrag-abbuchungen-pruefen` · Die Bezeichnung als 'wirksamste Maßnahme' ist ein Superlativ ohne messbare Datenbasis oder Vergleich mit anderen Sicherheitsmechanismen.
- `efee7b0cefffa501cc57` · `2026-08-28-lastschrift-und-dauerauftrag-abbuchungen-pruefen` · Stromabschläge sind untypisch für Daueraufträge, da sich die Beträge nach Jahresabrechnungen meist ändern; hier ist die Lastschrift der Standard, um Zahlungsfehler zu vermeiden.
- `dc1e5d50a58f50e0ade1` · `2026-08-31-nachtstrom-tarife-wann-sich-ein-doppeltarifzaehler-noch-lohnt` · Die verlinkte Seite der Bundesnetzagentur ist eine reine Navigations-Übersicht und enthält keine der im Text versprochenen Beschreibungen zu Tarifbestandteilen oder Preisregelungen.
- `def8ad23c34566c795fe` · `2026-08-31-nachtstrom-tarife-wann-sich-ein-doppeltarifzaehler-noch-lohnt` · Die Verknüpfung der HT/NT-Definition mit der Bundesnetzagentur ist unpräzise, da die verlinkte Seite lediglich eine Themenübersicht ohne fachliche Definitionen darstellt.
- `19a724ba20628f34cd01` · `2026-08-31-stoerung-beim-internetanbieter-so-sicherst-du-deine-rechte` · Eine feste Frist für die Entstörung nennt das Gesetz nicht.
- `4126d33a9dd92716b286` · `2026-08-31-stoerung-beim-internetanbieter-so-sicherst-du-deine-rechte` · Ein unentschuldigter no-show zählt nur, wenn du ihn zeitnah meldest.
- `67fbe0b49bb4e6bb48b7` · `2026-08-31-stoerung-beim-internetanbieter-so-sicherst-du-deine-rechte` · Die Pflichten aus dem TKG gelten für alle Zugangsarten.
- `cb5f849bfd26ad8121eb` · `2026-08-31-stoerung-beim-internetanbieter-so-sicherst-du-deine-rechte` · Der Anbieter muss die Störung beheben; eine pauschale Wartezeit gibt es nicht, aber eine Pflicht zur zeitnahen Entstörung.
- `f108d554ff8861370b64` · `2026-08-31-stoerung-beim-internetanbieter-so-sicherst-du-deine-rechte` · Bei einem längeren Ausfall hast du zwei Hebel: die Gutschrift für die ausgefallene Leistung und bei einigen Verzögerungen die Entschädigung.
- `009906e47bcc8265b36a` · `2026-09-09-notgroschen-die-wahrheit-ueber-das-finanzielle-polster` · Angestellte reichen oft drei bis sechs Monatsausgaben als Sicherheit
- `e0293a43782c64955b27` · `2026-09-09-notgroschen-die-wahrheit-ueber-das-finanzielle-polster` · Selbstständige sollten sechs‑ bis zwölf‑Monats‑Ausgaben als Reserve planen
- `3eab428a91b1b16b7df8` · `2026-09-20-finanzieller-puffer-wie-viel-notgroschen-ist-genug` · Die aktuelle Inflationsrate von +2,8 % wird nicht genannt, obwohl sie für die empfohlene regelmäßige Prüfung der Pufferhöhe die zentrale Rechengröße darstellt.
- `7da9383cbc6a45e1a3ac` · `2026-09-20-finanzieller-puffer-wie-viel-notgroschen-ist-genug` · Der Modellwert für Lebensmittel (320 €) wird nicht mit der aktuellen Preissteigerung von +0,4 % abgeglichen, um die Validität der Kalkulationsbasis zu stützen.
- `da7852bcca291061c39b` · `2026-09-20-finanzieller-puffer-wie-viel-notgroschen-ist-genug` · Die Modellrechnung für Fixkosten berücksichtigt nicht die spezifische Teuerung bei Energie (+12,7 %), was bei der Kalkulation von Strom und Gas zu einer Unterdeckung führen kann.
- `68afba3e6a16a364ce45` · `2026-09-21-grundversorgung-strom-und-gas-was-sie-leistet` · Die Kündigungsfrist in der Grundversorgung ist gesetzlich exakt auf zwei Wochen festgelegt, was für den Leser eine wichtigere Information ist als die vage Bezeichnung 'kurze Fristen'.
- `dc5ff05c5dda79d01373` · `2026-09-21-grundversorgung-strom-und-gas-was-sie-leistet` · Es fehlt der Hinweis auf die gesetzliche Befristung der Ersatzversorgung auf maximal drei Monate, nach denen sie automatisch endet.
- `5c096f87730532352820` · `2026-09-23-einlagensicherung-wie-viel-guthaben-geschuetzt-ist` · Gesetze nennen konkrete Auszahlungsfristen im Einlagensicherungsfall.
- `6b5921bdc76490587167` · `2026-10-02-preiswert-surfen-so-findest-du-den-optimalen-dsl-anschluss` · Seit 2026 nutzen die großen Anbieter die Technik mit dem Namen Vectoring; das ist ein Modellwert. Sie senkt das Rauschen auf der Leitung. In der Stadt sind damit bis zu 250 Mbps stabil drin.
- `8436b91bdb63a6316979` · `2026-10-02-preiswert-surfen-so-findest-du-den-optimalen-dsl-anschluss` · Preisgarantie über mindestens 12 Monate; ohne Garantie darf der Anbieter bald erhöhen, oft um bis zu 10 %.
- `a4ff01e649b789f19e6a` · `2026-10-02-preiswert-surfen-so-findest-du-den-optimalen-dsl-anschluss` · Für 50 Mbps zahlst du heute meist ca. 20–40 € im Monat; das ist ein Beispielwert.
- `25d6b9a720f981e8e9df` · `2026-10-07-7-gewohnheiten-fuer-finanzielle-freiheit` · Bei der Bewertung flexibler Kosten sollte die moderate Preisentwicklung bei Nahrungsmitteln (+0,4 %) den stark steigenden Energiekosten gegenübergestellt werden, um Sparpotenziale zu priorisieren.
- `3693b612533c24dcd1ea` · `2026-10-07-7-gewohnheiten-fuer-finanzielle-freiheit` · Der Ratgeber empfiehlt die Prüfung von Stromverträgen, vernachlässigt aber den massiven Preistrend bei Energie von +12,2 %, der die Kalkulation der Fixkosten aktuell dominiert.
- `c877eeff8842942c0071` · `2026-10-07-7-gewohnheiten-fuer-finanzielle-freiheit` · Die allgemeine Budget-Transparenz ist ohne Einbezug der Inflationsrate von 2,8 % unvollständig, da Preissteigerungen die Planungssicherheit der 'festen Kosten' kontinuierlich untergraben.
- `26b1c694d76bcc7af50f` · `2026-10-07-handyvertrag-kuendigen-raus-aus-der-kostenfalle-verlaengerung` · Der Ratgeber versäumt es, den für den Verbraucherschutz zentralen Regulierungsrahmen der 'Unternehmenspflichten' zu nennen, den die Bundesnetzagentur explizit als Fachthema führt.
- `9593e535bce55f4283e6` · `2026-10-07-handyvertrag-kuendigen-raus-aus-der-kostenfalle-verlaengerung` · Die Empfehlung zum Preisvergleich lässt den aktuellen Marktdruck (sinkende Umsätze bei O2) außer Acht, der für die Verhandlung von Rückholangeboten bei Kündigung entscheidend sein kann.
- `a10511ed618384aa7b88` · `2026-10-07-wie-smart-home-geraete-deine-stromrechnung-wirklich-druecken` · Der Artikel nennt keine regulatorischen Vorgaben oder Zertifizierungen (z. B. CE‑Kennzeichnung, Sicherheitsanforderungen) für Smart‑Home‑Geräte, obwohl solche Vorgaben von der Bundesnetzagentur beschrieben werden.
- `a74029dd4e284794d697` · `2026-10-09-balkonkraftwerk-foerderung-so-holst-du-dir-geld-zurueck` · Eine separate Meldung beim Netzbetreiber ist im Standardfall nicht mehr nötig.
- `c45ea4bb1a6f2330679a` · `2026-10-09-balkonkraftwerk-foerderung-so-holst-du-dir-geld-zurueck` · Keine bundesweite Zuschusspflicht: Zuschüsse kommen, wenn überhaupt, von Städten, Gemeinden oder Ländern.
- `4d0125136c5b940946e4` · `2026-10-09-energiekosten-senken-smarte-helfer-fuer-den-haushalt` · Lichtsteuerung: Bedarfssteuerung – 2 bis 5 % des Stromverbrauchs.
- `7aeb2098034d16a46885` · `2026-10-09-energiekosten-senken-smarte-helfer-fuer-den-haushalt` · Anbieter locken mit Neukundenboni, die nach der üblichen Erstlaufzeit entfallen; danach steigt der Arbeitspreis massiv an.
- `ea97b5dd6695de127fd2` · `2026-10-09-energiekosten-senken-smarte-helfer-fuer-den-haushalt` · Heizungssteuerung: Smarte Thermostate können Heizkosten einsparen. Die Spanne von 10 bis 25 % ist ein Beispielwert aus der Rechnung unten.
- `7c2624072c861d136c96` · `2026-10-12-dein-weg-zu-geringeren-monatskosten-schritt-fuer-schritt` · Die pauschale Behauptung zu Preisunterschieden zwischen Standardtarifen und Angeboten ist ein Marktdatum ohne Beleg oder eigene Messung (Regel 9a/9e).
- `d9d3004fbc05895c3f79` · `2026-10-12-dein-weg-zu-geringeren-monatskosten-schritt-fuer-schritt` · Die Aussage zum steigenden Strompreis ist unpräzise; die Quelle belegt einen konkreten Anstieg der Energiepreise um +12,7 %.
- `1dc0f20f9ab3a6b783bc` · `2026-10-12-energieausweis-was-das-dokument-fuer-deine-fixkosten` · Behauptung, dass ein fehlender Ausweis zu empfindlichen Bußgeldern führt, fehlt eine belegbare Quelle.
- `7b94ca07b36c0b7cb1cc` · `2026-10-12-energieausweis-was-das-dokument-fuer-deine-fixkosten` · Aussage, dass Baudenkmäler von der Ausweispflicht befreit sind, wird nicht durch die angegebene Quelle gestützt.
- `985f506ee04087bf7253` · `2026-10-12-energieausweis-was-das-dokument-fuer-deine-fixkosten` · Angabe, dass ein Wechsel von Energieeffizienzklasse F zu C über 2.000 € Jahresersparnis bringt, ist unbelegt.
- `ee321fa37210590f7e9b` · `2026-10-12-energieausweis-was-das-dokument-fuer-deine-fixkosten` · Keine Quelle für die Angabe, dass ein Energieausweis ein volles Jahrzehnt gültig ist, sofern keine größeren Umbauten erfolgen.
- `19ab248b17415c73edfb` · `2026-10-12-kleine-energiespar-tricks-die-deine-kosten-sofort-senken` · Thermostat um 1 °C senken | 4 % – 6 % der Heizkosten
- `372bb51051e8bd7c5f71` · `2026-10-12-kleine-energiespar-tricks-die-deine-kosten-sofort-senken` · Viele Anbieter belohnen einen niedrigen Verbrauch mit besseren Konditionen
- `6aaff85e3a7591d0c5b2` · `2026-10-12-kleine-energiespar-tricks-die-deine-kosten-sofort-senken` · für dich entstehen keine Mehrkosten
- `7e6087a4117a857a92c8` · `2026-10-12-kleine-energiespar-tricks-die-deine-kosten-sofort-senken` · Durch diese zwei Maßnahmen sparst du in dieser Beispielrechnung jährlich rund 140 €
- `e28b4ad1f6d608d2ec77` · `2026-10-12-kleine-energiespar-tricks-die-deine-kosten-sofort-senken` · Strom (LED‑Umrüstung) | 100 € – 140 € | etwa 8 %
- `1eae5c7e2bbd95a3362c` · `2026-10-23-stromkosten-senken-clevere-haushaltsgeraete-im-ueberblick` · Tabelle mit konkreten kWh‑Werten und Euro‑Ersparnissen für neue vs. alte Geräte.
- `8547ce3daa75aabb30d4` · `2026-10-23-stromkosten-senken-clevere-haushaltsgeraete-im-ueberblick` · Annahme von 40 ct/kWh und daraus resultierende Jahres‑Ersparnis von 52 € für einen Kühlschrank‑Tausch.
- `c8b197692bd0023c87bf` · `2026-10-23-stromkosten-senken-clevere-haushaltsgeraete-im-ueberblick` · Behauptung, dass ein neuer Wärmepumpentrockner „sogar noch schneller“ die Anschaffungskosten amortisiert.
- `e40a2ee5c7baa5f8567b` · `2026-10-23-stromkosten-senken-clevere-haushaltsgeraete-im-ueberblick` · Sparsame Geräte senken deinen Verbrauch in der Beispielrechnung unten um bis zu 40 %.
- `feb71513c6fb7064dc92` · `2026-10-23-stromkosten-senken-clevere-haushaltsgeraete-im-ueberblick` · Der Stromverbrauch von Kühlschrank und Waschmaschine macht in der Modellrechnung rund 30 % der Kosten im Haushalt aus.
- `04ae33652c1c5eb4e2b8` · `2026-10-24-bankgebuehren-senken-7-schritte-zum-guenstigeren-konto` · Ein kurzer Check spart dir oft mehrere hundert Euro im Jahr.
- `5223a3c7287ff81939cd` · `2026-10-24-bankgebuehren-senken-7-schritte-zum-guenstigeren-konto` · Faustregel: ... mehr als 5 % deines Nettoeinkommens ... Meist sinken diese Kosten um über 80 %
- `9800545ae945ec280b34` · `2026-10-24-bankgebuehren-senken-7-schritte-zum-guenstigeren-konto` · Ein Wechsel ist für dich in der Regel komplett kostenlos als Beispielwert.
- `bc0e4f2eb357a682c674` · `2026-10-24-bankgebuehren-senken-7-schritte-zum-guenstigeren-konto` · Bei einem normalen Einkommen sollten die Gebühren fast Null sein.
- `0d1977a0b6a7b59136f2` · `2026-10-24-energieeffizienz-im-haushalt-5-schnelle-spartricks` · Die Bezeichnung als 'beste Tarife' ist ein Superlativ ohne messbare Daten oder eigene Vergleichsmetrik.
- `228ef205074fdc3fb4b3` · `2026-10-24-energieeffizienz-im-haushalt-5-schnelle-spartricks` · Der Heiz-Faustwert (6 % Ersparnis pro Grad) fehlt in der angegebenen Quelle und ist nicht am Satz belegt.
- `d7c301604b02d49e8d65` · `2026-10-24-energieeffizienz-im-haushalt-5-schnelle-spartricks` · Der behauptete Budgetanteil von 30 % für Energie ist ein spezifischer Marktwert, der in der angegebenen Quelle nicht vorkommt.
- `3bfeb0118af92a780a47` · `2026-10-24-etf-sparplan-starten-schritt-fuer-schritt-zum-monatlichen` · Bei 5 % Rendite im Jahr entstehen rund 30.000 € – keine Quelle für die angenommene Rendite angegeben.
- `ed2161154dcee85da1ee` · `2026-10-24-etf-sparplan-starten-schritt-fuer-schritt-zum-monatlichen` · Angabe, dass die Einrichtung eines Sparplans meist weniger als 15 Minuten dauert, fehlt belegt.
- `f593fe21275bd9dcefef` · `2026-10-24-etf-sparplan-starten-schritt-fuer-schritt-zum-monatlichen` · Behauptung, dass einige Broker bereits ab 1 € monatlich starten, ohne Quelle.
- `381dd90113dd1ee72f39` · `2026-10-28-flugvergleich-im-winter-so-findest-du-echte-billigfluege` · Das Versprechen, 'alle Gebühren' auf Portalen zu sehen, ist ohne Messgröße unpräzise, da Portale systembedingt nur eine Marktauswahl zeigen.
- `4483a81dd1c292034cd0` · `2026-10-28-flugvergleich-im-winter-so-findest-du-echte-billigfluege` · Die Warnung vor einer 'sehr hohen Strafgebühr' am Gate ist ein Superlativ ohne messbare Daten oder konkrete Preisbeispiele.
- `6f4b591e9cadb27adf49` · `2026-10-28-flugvergleich-im-winter-so-findest-du-echte-billigfluege` · Bei der Erwähnung von Stornierungen durch Airlines fehlt der Hinweis auf den rechtlichen Rahmen (z. B. EU-Fluggastrechte).
- `cf60024b74a5e86b50c0` · `2026-10-28-flugvergleich-im-winter-so-findest-du-echte-billigfluege` · Die statistische Aussage zur Preisgünstigkeit von Dienstag und Mittwoch ist eine Marktprognose ohne Beleg in der genannten Quelle.

## `2026-08-10-dsl-wechselbonus-sichern`

- Offene Live-Befunde: **2**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `1b7c9b9cac0290f71242` | luecke | **neu** | 10 € in Zeile 19 ohne Kennzeichnung · 25 € in Zeile 19 ohne Kennzeichnung | Aktuelle Wechselangebote ermöglichen oft Einsparungen von ca. 10 € bis 25 € pro Monat im Vergleich zu veralteten Best… |
| `ee260c27a6bfdd60fa04` | luecke | **neu** | 200 € in Zeile 45 gekennzeichnet · 300 € in Zeile 45 gekennzeichnet | Ein Tarif mit ca. 200 € bis 300 € Bonus wirkt auf den ersten Blick unschlagbar; das ist ein Modellwert. |

### `1b7c9b9cac0290f71242`

**Befund:** Aktuelle Wechselangebote ermöglichen oft Einsparungen von ca. 10 € bis 25 € pro Monat im Vergleich zu veralteten Bestandskundentarifen.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Heute in Zeile 19: 10 € – **ohne** Kennzeichnung
- Heute in Zeile 19: 25 € – **ohne** Kennzeichnung

### `ee260c27a6bfdd60fa04`

**Befund:** Ein Tarif mit ca. 200 € bis 300 € Bonus wirkt auf den ersten Blick unschlagbar; das ist ein Modellwert.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Heute in Zeile 45: 200 € – gekennzeichnet („modellwert“)
- Heute in Zeile 45: 300 € – gekennzeichnet („modellwert“)

## `2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas`

- Offene Live-Befunde: **3**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `124ff2c3cd3917c274aa` | praezision | 2026-11-23 · 2. Entscheidung | kein Wert genannt (Aussage/Präzision) | Die Bewerbung des Vergleichsportals mit dem Superlativ 'Die besten Tarife' erfolgt ohne messbare Daten oder Auswahlkr… |
| `7bdec96c0329769bebe6` | luecke | 2026-11-23 · 2. Entscheidung | 13 Cent in Zeile 98 ohne Kennzeichnung | Die im Artikel als Fakten genannten Gaspreise für Oktober 2026 (11 bis 13 Cent/kWh) sind nicht durch die Fundstelle b… |
| `a56734aa032e0ed9e0c4` | luecke | 2026-11-23 · 2. Entscheidung | kein Wert genannt (Aussage/Präzision) | Der für den Verbraucherschutz zentrale Regulierungsrahmen (Sonderkündigungsrecht, Informationspflichten der Versorger… |

### `124ff2c3cd3917c274aa`

**Befund:** Die Bewerbung des Vergleichsportals mit dem Superlativ 'Die besten Tarife' erfolgt ohne messbare Daten oder Auswahlkriterien in der Recherchegrundlage.

**Frühere Entscheidung (2026-11-23):** Frank Hartung (Betreiber-Freigabe über Arena-Session, 23.11.2026)

> Volltext am 23.11.2026 geprüft (Welle 1): Der beanstandete Superlativ 'Die besten Tarife' steht nicht mehr im Artikel; Vergleichshinweise sind sachlich ohne Superlativ formuliert.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `7bdec96c0329769bebe6`

**Befund:** Die im Artikel als Fakten genannten Gaspreise für Oktober 2026 (11 bis 13 Cent/kWh) sind nicht durch die Fundstelle belegt, die lediglich eine allgemeine Themenübersicht darstellt.

**Frühere Entscheidung (2026-11-23):** Frank Hartung (Betreiber-Freigabe über Arena-Session, 23.11.2026)

> Volltext am 23.11.2026 geprüft (Welle 1): Unbelegte Oktober-2026-Gaspreisspannen (11 bis 13 Cent/kWh) stehen nicht mehr im Artikel; Zahlen sind offen als Modellannahmen oder mit Quellenbezug markiert.

- Heute in Zeile 98: 13 Cent – **ohne** Kennzeichnung

### `a56734aa032e0ed9e0c4`

**Befund:** Der für den Verbraucherschutz zentrale Regulierungsrahmen (Sonderkündigungsrecht, Informationspflichten der Versorger) wird in der Fundstelle nicht inhaltlich bestätigt.

**Frühere Entscheidung (2026-11-23):** Frank Hartung (Betreiber-Freigabe über Arena-Session, 23.11.2026)

> Volltext am 23.11.2026 geprüft (Welle 1): Regulierungsrahmen (Sonderkündigungsrecht, Ausnahmen und Informationspflichten) ist im heutigen Text explizit mit Verweis auf die Bundesnetzagentur dargestellt.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

## `2026-08-12-geld-abheben-im-ausland-gebuehren-vermeiden`

- Offene Live-Befunde: **4**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `1d4095501e717fb30d7b` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Der Hinweis auf einen „Wochenend‑Effekt“ bei Devisenkursen wird ohne Quellenangabe gemacht. |
| `77520584b5afd8ebd7f7` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Es wird angegeben, dass der Kurs am Automaten häufig über dem Referenzkurs der Bank liegt, jedoch fehlt ein Beleg dafür. |
| `a3be3d50280d4fe0a1d8` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Der Artikel behauptet, dass der Betreiber des Automaten ein eigenes Entgelt verlangt, ohne dafür eine Quelle anzugeben. |
| `d6cc7bae16dead3e610b` | praezision | **neu** | kein Wert genannt (Aussage/Präzision) | Die Empfehlung, nur Automaten von Banken und nicht von Aufstellern in Touristenzonen zu nutzen, ist unspezifisch und… |

### `1d4095501e717fb30d7b`

**Befund:** Der Hinweis auf einen „Wochenend‑Effekt“ bei Devisenkursen wird ohne Quellenangabe gemacht.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `77520584b5afd8ebd7f7`

**Befund:** Es wird angegeben, dass der Kurs am Automaten häufig über dem Referenzkurs der Bank liegt, jedoch fehlt ein Beleg dafür.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `a3be3d50280d4fe0a1d8`

**Befund:** Der Artikel behauptet, dass der Betreiber des Automaten ein eigenes Entgelt verlangt, ohne dafür eine Quelle anzugeben.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `d6cc7bae16dead3e610b`

**Befund:** Die Empfehlung, nur Automaten von Banken und nicht von Aufstellern in Touristenzonen zu nutzen, ist unspezifisch und nicht durch Daten belegt.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

## `2026-08-14-wlan-verbessern-so-bringst-du-speed-in-jede-ecke`

- Offene Live-Befunde: **3**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `29eea3c457afaba3d7bd` | luecke | **neu** | 350 € in Zeile 58 gekennzeichnet · 24 Monate in Zeile 58 gekennzeichnet | Ein Wechsel zum modernen Provider bringt oft über 350 € in 24 Monaten; das ist eine Modellannahme. |
| `8a0df5531569ec042ec4` | praezision | **neu** | 40 % in Zeile 23 gekennzeichnet | Ein freier Standplatz steigert den Empfang um bis zu 40 %. |
| `bda1b543db068b3e00ff` | luecke | **neu** | 45 € in Zeile 3 gekennzeichnet | Im Check: Du zahlst jeden Monat rund 45 € für einen schnellen Anschluss; das ist ein Modellwert. |

### `29eea3c457afaba3d7bd`

**Befund:** Ein Wechsel zum modernen Provider bringt oft über 350 € in 24 Monaten; das ist eine Modellannahme.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Heute in Zeile 58: 350 € – gekennzeichnet („annahme“)
- Heute in Zeile 58: 24 Monate – gekennzeichnet („annahme“)

### `8a0df5531569ec042ec4`

**Befund:** Ein freier Standplatz steigert den Empfang um bis zu 40 %.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Heute in Zeile 23: 40 % – gekennzeichnet („modellwert“)

### `bda1b543db068b3e00ff`

**Befund:** Im Check: Du zahlst jeden Monat rund 45 € für einen schnellen Anschluss; das ist ein Modellwert.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Heute in Zeile 3: 45 € – gekennzeichnet („modellwert“)

## `2026-08-17-abos-und-vertraege-stiller-posten-haushaltsplan`

- Offene Live-Befunde: **4**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `3a3269aa4a2e95d780ad` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Ein Jahresabo ohne Abbuchung im letzten Monat ist im Haushalt trotzdem eine laufende Verpflichtung |
| `c3ff13d7ca048da95112` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Bei einer Lastschrift kannst du die Abbuchung über deine Bank zurückgeben lassen |
| `ec052a0155f98740a3b5` | praezision | **neu** | kein Wert genannt (Aussage/Präzision) | Ein Dienst, der gegen Gebühr kündigt, ändert nichts an den Fristen |
| `ee3a722844f4b84b84b8` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Die häufigste Panne ist die Kündigung zum falschen Zeitpunkt |

### `3a3269aa4a2e95d780ad`

**Befund:** Ein Jahresabo ohne Abbuchung im letzten Monat ist im Haushalt trotzdem eine laufende Verpflichtung

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `c3ff13d7ca048da95112`

**Befund:** Bei einer Lastschrift kannst du die Abbuchung über deine Bank zurückgeben lassen

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `ec052a0155f98740a3b5`

**Befund:** Ein Dienst, der gegen Gebühr kündigt, ändert nichts an den Fristen

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `ee3a722844f4b84b84b8`

**Befund:** Die häufigste Panne ist die Kündigung zum falschen Zeitpunkt

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

## `2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren`

- Offene Live-Befunde: **5**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `1dbeb2f8c51e78d11d49` | luecke | 2026-11-17 · 3. Entscheidung | nicht mehr im Text: 150 €, 250 € | Behauptung, dass klassische Filialbanken jährlich 150 € bis 250 € an reinen Gebühren kosten, ist unbelegt. |
| `33e736ac6afe996b491a` | luecke | 2026-11-17 · 3. Entscheidung | kein Wert genannt (Aussage/Präzision) | Behauptung, dass Echtzeit‑Überweisungen bei kostenlosen Konten generell gebührenfrei sind, fehlt jede Quelle. |
| `96b7b7768d402884810c` | luecke | 2026-11-17 · 3. Entscheidung | 100.000 € in Zeile 219 gekennzeichnet | Aussage, dass Einlagen bis 100.000 € durch die deutsche Einlagensicherung geschützt sind, wird nicht belegt. |
| `a25bb6bbcb25ba8b0e22` | luecke | 2026-11-17 · 3. Entscheidung | 8 % in Zeile 5 gekennzeichnet · 11 % in Zeile 78 gekennzeichnet | Angabe von Dispozinsen von 8 % bis 11 % ohne Quellenangabe. |
| `f94f8ba1e4342e67e45a` | luecke | 2026-11-17 · 3. Entscheidung | nicht mehr im Text: 180 € · 120 € in Zeile 90 gekennzeichnet | Angabe, dass ein Kontowechsel 120 € bis 180 € im Jahr spart, fehlt jede Quelle. |

### `1dbeb2f8c51e78d11d49`

**Befund:** Behauptung, dass klassische Filialbanken jährlich 150 € bis 250 € an reinen Gebühren kosten, ist unbelegt.

**Frühere Entscheidung (2026-11-17):** Arena-Redaktion (Auftrag: Frank Hartung), 17.11.2026

> Beleglos entschieden, weil es keinen zulässigen Beleg gibt: In der Quellen-Allowlist (data/agent_reach/faktenfrische.yaml) findet sich keine amtliche oder verbraucherschützerische Erhebung zu durchschnittlichen Jahresgebühren von Filialbanken, und Vergleichsportale außerhalb der Allowlist dürfen als Beleg nicht herhalten. Die unbelegte Marktbehauptung 'ca. 140 Euro bis 240 Euro' ist deshalb aus dem Artikel entfernt. Die Tabelle rechnet jetzt offen mit zwei benannten Modellannahmen (10,00 Euro Kontoführung im Monat und 15,00 Euro Karte im Jahr, zusammen 135,00 Euro im Jahr), ist als Modellrechnung gekennzeichnet, und der Text verweist Leser auf beide Preis- und Leistungsverzeichnisse, statt eine Marktzahl zu behaupten.

- Im heutigen Text nicht mehr vorhanden: 150 €, 250 €

### `33e736ac6afe996b491a`

**Befund:** Behauptung, dass Echtzeit‑Überweisungen bei kostenlosen Konten generell gebührenfrei sind, fehlt jede Quelle.

**Frühere Entscheidung (2026-11-17):** Arena-Redaktion (Auftrag: Frank Hartung), 17.11.2026

> Der Befund ist berechtigt, und die Aussage war sachlich falsch: Eine generelle Gebührenfreiheit von Echtzeit-Überweisungen gibt es nicht. Die Bundesbank (Fragen und Antworten zu Echtzeitüberweisungen und Empfängerüberprüfung, geprüft am 17.11.2026) formuliert die Rechtslage so: Die Kosten für Echtzeitüberweisungen dürfen nicht höher sein als die Kosten für herkömmliche Überweisungen gleicher Art - Preisparität also, nicht Kostenlosigkeit. Der Artikel nennt deshalb in Kurzantwort, Wichtigstes in Kürze, Kostenfaktoren, Extras, 10-Minuten-Check und in der Vergleichstabelle nur noch diese Preisparität, mit den Stichtagen 09.01.2025 (Empfangspflicht) und 09.10.2025 (Sendepflicht). Die unbelegte Gratis-Aussage ist entfernt.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `96b7b7768d402884810c`

**Befund:** Aussage, dass Einlagen bis 100.000 € durch die deutsche Einlagensicherung geschützt sind, wird nicht belegt.

**Frühere Entscheidung (2026-11-17):** Arena-Redaktion (Auftrag: Frank Hartung), 17.11.2026

> Am 17.11.2026 gegen die Primärquelle geprüft. Die früher verlinkte Bundesbank-Seite .../bankenaufsicht/einlagensicherung/einlagensicherung-602936 ist tot (läuft ins Leere); im FAQ-Antworttext und im Frontmatter-Block quellen steht jetzt die geprüfte Seite 'Einlagensicherung' (.../finanzaufsicht/einzelaspekte/einlagensicherung-597886). Inhaltlich übernommen: gesetzlicher Anspruch bis 100.000 Euro je Einleger und je Bank einschließlich Zinsansprüchen, Auszahlung spätestens sieben Arbeitstage nach Feststellung des Entschädigungsfalls, erhöhter Schutz von 500.000 Euro für bis zu sechs Monate bei besonders schutzwürdigen Einlagen. Ergänzt wurde außerdem der fehlende Punkt vor 'Moderne Apps sind zudem sicher'. Die Aussage ist damit belegt statt nur behauptet.

- Heute in Zeile 219: 100.000 € – gekennzeichnet („beispielwert“)

### `a25bb6bbcb25ba8b0e22`

**Befund:** Angabe von Dispozinsen von 8 % bis 11 % ohne Quellenangabe.

**Frühere Entscheidung (2026-11-17):** Arena-Redaktion (Auftrag: Frank Hartung), 17.11.2026

> Die Spanne 'ca. 8 % bis 11 %' hatte keine Quelle und ist aus der Vergleichstabelle entfernt. An ihre Stelle tritt der amtliche Messwert: Bundesbank MFI-Zinsstatistik, Bestände, Zeitreihe BBIM1.M.DE.B.A2Z1.A.R.A.2250.EUR.N - revolvierende Kredite und Überziehungskredite an private Haushalte, September 2026: 9,59 % p.a. effektiv bei 28.552 Mio Euro Volumen; die acht Vormonate lagen zwischen 9,19 % und 9,46 % (Statistikstand laut Seitenstempel 02.11.2026, geprüft am 17.11.2026). Der Artikel benennt den Wert ausdrücklich als Durchschnitt über alle Banken und verweist für den eigenen Satz auf das Preisverzeichnis des Kontomodells.

- Heute in Zeile 5: 8 % – gekennzeichnet („modellwert“)
- Heute in Zeile 78: 11 % – gekennzeichnet („modellwert“)

### `f94f8ba1e4342e67e45a`

**Befund:** Angabe, dass ein Kontowechsel 120 € bis 180 € im Jahr spart, fehlt jede Quelle.

**Frühere Entscheidung (2026-11-17):** Arena-Redaktion (Auftrag: Frank Hartung), 17.11.2026

> Die Sparspanne von 120 Euro bis 180 Euro im Jahr war unbelegt und steht nirgends mehr im Artikel; auch pin_description wirbt nicht länger mit 'bis zu 120 Euro im Jahr sparen'. Der Artikel sagt stattdessen, dass die Ersparnis den Gebühren im eigenen alten Preisverzeichnis entspricht. Belegt wird nur noch, was gesetzlich feststeht: der Kontowechselservice nach Paragraf 21 ff. ZKG - die neue Bank muss die alte Bank innerhalb von zwei Geschäftstagen nach der Ermächtigung beauftragen (Paragraf 22 ZKG) und erhält dafür die Daueraufträge, die Lastschriftmandate und die Buchungen der letzten 13 Monate; die Ermächtigung ist auch im Online-Banking möglich (Paragraf 21 Absatz 4 ZKG). Dieselbe Quelle trägt jetzt auch die FAQ-Antwort zum Lastschriftumzug. Deshalb der ZKG-Beleg statt einer erfundenen Sparzahl.

- Im heutigen Text nicht mehr vorhanden: 180 €
- Heute in Zeile 90: 120 € – gekennzeichnet („annahme“)

## `2026-08-19-dsl-vergleich-so-findest-du-guenstigeres-internet`

- Offene Live-Befunde: **2**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `991bda7b2298b751f4e6` | praezision | **neu** | kein Wert genannt (Aussage/Präzision) | Die Behauptung einer garantierten Versorgung ist rechtlich zu weitgehend; die Bundesnetzagentur führt lediglich Unter… |
| `ae71596724d7a243217b` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Der Artikel ignoriert die regulatorisch und technisch relevante Kupfer-Glas-Migration, welche die langfristige Verfüg… |

### `991bda7b2298b751f4e6`

**Befund:** Die Behauptung einer garantierten Versorgung ist rechtlich zu weitgehend; die Bundesnetzagentur führt lediglich Unternehmenspflichten und die Grundversorgung als Aufsichtsthemen auf.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `ae71596724d7a243217b`

**Befund:** Der Artikel ignoriert die regulatorisch und technisch relevante Kupfer-Glas-Migration, welche die langfristige Verfügbarkeit und den Wechselzwang von DSL-Anschlüssen maßgeblich beeinflusst.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

## `2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden`

- Offene Live-Befunde: **5**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `43470330b3b48c9cee49` | luecke | 2026-11-11 · 2. Entscheidung | 24 Stunden in Zeile 96 ohne Kennzeichnung | Der Artikel empfiehlt, Kühl- und Gefriergeräte mindestens 24 Stunden, besser mehrere Tage zu messen, liefert jedoch k… |
| `8ddc1025e45be176ad3a` | luecke | 2026-11-11 · 2. Entscheidung | kein Wert genannt (Aussage/Präzision) | Es wird kein regulatorischer Rahmen (z. B. Aufgaben der Bundesnetzagentur) genannt, obwohl das Thema Stromversorgung… |
| `95d6d2877620e5a056ce` | luecke | 2026-11-11 · 2. Entscheidung | kein Wert genannt (Aussage/Präzision) | Die Aussage, dass Verbraucherzentralen oder Bibliotheken Messgeräte verleihen, wird ohne Beleg gemacht. |
| `ab16029999747466a638` | luecke | 2026-11-11 · 2. Entscheidung | 0,37 € in Zeile 98 gekennzeichnet | Die Berechnung mit einem Arbeitspreis von 0,37 €/kWh wird angegeben, ohne dass ein aktueller Preis‑ oder Marktwert be… |
| `b057dee3603e09f494b5` | luecke | 2026-11-11 · 2. Entscheidung | 650 € in Zeile 121 ohne Kennzeichnung · 10,3 Jahre in Zeile 122 ohne Kennzeichnung | Das Amortisationsbeispiel (Kaufpreis 650 €, Amortisationszeit 10,3 Jahre) enthält keine Quelle für die zugrunde liege… |

### `43470330b3b48c9cee49`

**Befund:** Der Artikel empfiehlt, Kühl- und Gefriergeräte mindestens 24 Stunden, besser mehrere Tage zu messen, liefert jedoch keine Quelle für diese Messdauer.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Am heutigen Text geprüft (SHA-256 01a0b2abe713): Die verlangte Quelle steht im Abschnitt „Das Wichtigste in Kürze“ inline – „Diese Messdauer empfiehlt die [Verbraucherzentrale](https://www.verbraucherzentrale.de/wissen/energie/strom-sparen/so-finden-sie-den-passenden-kuehlschrank-10573).“. Der Befund trifft die heutige Fassung damit nicht mehr.

- Heute in Zeile 96: 24 Stunden – **ohne** Kennzeichnung

### `8ddc1025e45be176ad3a`

**Befund:** Es wird kein regulatorischer Rahmen (z. B. Aufgaben der Bundesnetzagentur) genannt, obwohl das Thema Stromversorgung berührt wird; entsprechende Vorgaben fehlen im Text.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Am heutigen Text geprüft (SHA-256 01a0b2abe713): Die verlangte Quelle steht im Abschnitt „So misst du sauber statt nur kurz draufzuschauen“ inline – „Die [Bundesnetzagentur](https://www.bundesnetzagentur.de/DE/Vportal/Energie/Metering/artikel.html) erklärt dazu die Rechte der Anschlussnutzer: Bei Zweifeln an der messtechnischen “. Der Befund trifft die heutige Fassung damit nicht mehr.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `95d6d2877620e5a056ce`

**Befund:** Die Aussage, dass Verbraucherzentralen oder Bibliotheken Messgeräte verleihen, wird ohne Beleg gemacht.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Am heutigen Text geprüft (SHA-256 01a0b2abe713): Die verlangte Quelle steht im Abschnitt „Das Wichtigste in Kürze“ inline – „Diese Messdauer empfiehlt die [Verbraucherzentrale](https://www.verbraucherzentrale.de/wissen/energie/strom-sparen/so-finden-sie-den-passenden-kuehlschrank-10573).“. Der Befund trifft die heutige Fassung damit nicht mehr.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `ab16029999747466a638`

**Befund:** Die Berechnung mit einem Arbeitspreis von 0,37 €/kWh wird angegeben, ohne dass ein aktueller Preis‑ oder Marktwert belegt wird.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Am heutigen Text geprüft (SHA-256 01a0b2abe713): Die verlangte Quelle steht im Abschnitt „Die Kostenformel, die du wirklich brauchst“ inline – „Der [BDEW](https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/) nennt für Haushalte im Oktober 2026 einen Durchschnittspreis von 37,3 Cent je kWh.“. Der Befund trifft die heutige Fassung damit nicht mehr.

- Heute in Zeile 98: 0,37 € – gekennzeichnet („modellwert“)

### `b057dee3603e09f494b5`

**Befund:** Das Amortisationsbeispiel (Kaufpreis 650 €, Amortisationszeit 10,3 Jahre) enthält keine Quelle für die zugrunde liegenden Annahmen oder Preise.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Am heutigen Text geprüft (SHA-256 01a0b2abe713): Die verlangte Quelle steht im Abschnitt „Die Kostenformel, die du wirklich brauchst“ inline – „Der [BDEW](https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/) nennt für Haushalte im Oktober 2026 einen Durchschnittspreis von 37,3 Cent je kWh.“. Der Befund trifft die heutige Fassung damit nicht mehr.

- Heute in Zeile 121: 650 € – **ohne** Kennzeichnung
- Heute in Zeile 122: 10,3 Jahre – **ohne** Kennzeichnung

## `2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause`

- Offene Live-Befunde: **2**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `91894b9b1535765acdca` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Der Artikel versäumt es, den gesetzlichen Regulierungsrahmen (z. B. Entschädigung bei Wechselproblemen) zu nennen, ob… |
| `f7b9c93c6a9be1368b06` | veraltet | **neu** | kein Wert genannt (Aussage/Präzision) | Die Einstufung von Glasfaser als teure 'Premium-Variante' ist überholt, da neue Schnäppchentarife den Markt preislich… |

### `91894b9b1535765acdca`

**Befund:** Der Artikel versäumt es, den gesetzlichen Regulierungsrahmen (z. B. Entschädigung bei Wechselproblemen) zu nennen, obwohl die Fachseite der Aufsichtsbehörde als Beleg angeführt wird.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `f7b9c93c6a9be1368b06`

**Befund:** Die Einstufung von Glasfaser als teure 'Premium-Variante' ist überholt, da neue Schnäppchentarife den Markt preislich verändern.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

## `2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier`

- Offene Live-Befunde: **5**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `4afb8daed73677ee6224` | luecke | 2026-11-11 · 2. Entscheidung | nicht mehr im Text: 58 % | Angabe, dass 58 % der Nutzer ihr Haushaltsbuch digital führen, beruft sich angeblich auf Statista 2025, jedoch wird k… |
| `9eb9a90899cc8ca66020` | luecke | 2026-11-11 · 2. Entscheidung | 44 € in Zeile 119 ohne Kennzeichnung · 24 € in Zeile 14 ohne Kennzeichnung | Sparpotenzial‑Beispiele (z. B. DSL‑Tarifwechsel von 44 € auf 24 €) enthalten konkrete Zahlen ohne Quellenangabe. |
| `b4bd085bc84a6131b644` | luecke | 2026-11-11 · 2. Entscheidung | 60 % in Zeile 122 ohne Kennzeichnung | Behauptung, dass 60 % der Haushalte in Deutschland ihr Geld nicht nachverfolgen, wird mit einer Auswertung der Stiftu… |
| `baed76dc211bd15dd46f` | praezision | 2026-11-11 · 2. Entscheidung | kein Wert genannt (Aussage/Präzision) | Versprechen, dass ein Haushaltsbuch „schnell“ zeigt, welche Posten sich lohnen, ist nicht quantifiziert und fehlt an… |
| `d7c3cfb422310cf26ca6` | praezision | 2026-11-11 · 2. Entscheidung | 2.500 € in Zeile 100 gekennzeichnet | Die Aussage, dass die 50‑30‑20‑Regel für ein Nettoeinkommen von 2.500 € realistisch sei, wird ohne Hinweis auf region… |

### `4afb8daed73677ee6224`

**Befund:** Angabe, dass 58 % der Nutzer ihr Haushaltsbuch digital führen, beruft sich angeblich auf Statista 2025, jedoch wird keine Quelle genannt.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Die 58-%-Statista-Angabe steht nicht mehr im Artikel; die Vorentscheidung hat sie entfernt. Die Sparbeträge stehen nur noch in der Tabelle „Modell-Monatsersparnis“ mit dem Hinweis „Summe der Annahmen oben“.

- Im heutigen Text nicht mehr vorhanden: 58 %

### `9eb9a90899cc8ca66020`

**Befund:** Sparpotenzial‑Beispiele (z. B. DSL‑Tarifwechsel von 44 € auf 24 €) enthalten konkrete Zahlen ohne Quellenangabe.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Das DSL-Beispiel (44 € → 24 €) steht ausschließlich in der Tabelle „Modell-Monatsersparnis“; Überschrift und Summenzeile kennzeichnen die Werte als Annahmen. Eine Marktbehauptung ist nicht mehr enthalten.

- Heute in Zeile 119: 44 € – **ohne** Kennzeichnung
- Heute in Zeile 14: 24 € – **ohne** Kennzeichnung

### `b4bd085bc84a6131b644`

**Befund:** Behauptung, dass 60 % der Haushalte in Deutschland ihr Geld nicht nachverfolgen, wird mit einer Auswertung der Stiftung Warentest angegeben, jedoch fehlt ein entsprechender Nachweis.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Die 60-%-Angabe ist nicht mehr im Text; die unbelegte Stiftung-Warentest-Zuordnung wurde in der Vorentscheidung entfernt. Übrig bleiben die als Modell gekennzeichneten Beispielbeträge.

- Heute in Zeile 122: 60 % – **ohne** Kennzeichnung

### `baed76dc211bd15dd46f`

**Befund:** Versprechen, dass ein Haushaltsbuch „schnell“ zeigt, welche Posten sich lohnen, ist nicht quantifiziert und fehlt an konkreten Evidenzangaben.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Die Geschwindigkeitszusage ist quantifiziert und markiert: „Oft reicht schon ein gemeinsamer Monatscheck von 15 Minuten; das ist ein Rechenbeispiel.“ Ein pauschales „schnell“ ohne Maß trägt die Passage nicht mehr.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `d7c3cfb422310cf26ca6`

**Befund:** Die Aussage, dass die 50‑30‑20‑Regel für ein Nettoeinkommen von 2.500 € realistisch sei, wird ohne Hinweis auf regionale Unterschiede oder empirische Daten präsentiert.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Am heutigen Text geprüft (SHA-256 905288727fca): Die Zahl steht weiterhin im Artikel, ist aber ausdrücklich als Modell-/Beispielwert gekennzeichnet: „Bei 2.500 € netto heißt das: 1.250 € Fixkosten, 750 € Freizeit, 500 € Sparrate; das ist ein Beispielwert.“. Beanstandet war die Zahl OHNE Kennzeichnung; das trifft nicht mehr zu.

- Heute in Zeile 100: 2.500 € – gekennzeichnet („beispielwert“)

## `2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps`

- Offene Live-Befunde: **3**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `3fe383f6d452737f66f2` | praezision | 2026-11-04 · 1. Entscheidung | nicht mehr im Text: 350 € · 600 € in Zeile 143 gekennzeichnet | Die im Teaser und Text genannten monatlichen Ersparnisse von 350 € bis 600 € werden als Marktfakten ohne Quellenbeleg… |
| `7bba759bbb4ca14c7f35` | luecke | 2026-11-04 · 1. Entscheidung | 14,9 % in Zeile 200 ohne Kennzeichnung | Der Ratgeber empfiehlt Tarifwechsel bei Energie zur Kostensenkung, verschweigt aber den aktuellen Markttrend massiv s… |
| `e8e32a383b6f803cc8d4` | veraltet | 2026-11-04 · 1. Entscheidung | 2,8 % in Zeile 115 ohne Kennzeichnung · 0,5 % in Zeile 108 ohne Kennzeichnung · 1,5 % in Zeile 23 gekennzeichnet | Die Einschätzung zur Inflation ist unpräzise: Die aktuelle Inflationsrate liegt laut Destatis bei +2,8 % (Oktober 202… |

### `3fe383f6d452737f66f2`

**Befund:** Die im Teaser und Text genannten monatlichen Ersparnisse von 350 € bis 600 € werden als Marktfakten ohne Quellenbeleg oder methodische Herleitung (z. B. Referenzhaushalt des Statistischen Bundesamtes) angeführt.

**Frühere Entscheidung (2026-11-04):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 04.11.2026)

> Ersparnis-Spanne 350–600 € als Beispielhaushalt-Rechnung gekennzeichnet; Energiepreis-Kontext ergänzt; Inflations-/Tagesgeld-Einordnung auf Destatis Oktober 2026 (+2,8 %) aktualisiert.

- Im heutigen Text nicht mehr vorhanden: 350 €
- Heute in Zeile 143: 600 € – gekennzeichnet („beispielwert“)

### `7bba759bbb4ca14c7f35`

**Befund:** Der Ratgeber empfiehlt Tarifwechsel bei Energie zur Kostensenkung, verschweigt aber den aktuellen Markttrend massiv steigender Energiepreise (+14,9 %), was die Kalkulation der 50-Prozent-Fixkostenquote gefährdet.

**Frühere Entscheidung (2026-11-04):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 04.11.2026)

> Ersparnis-Spanne 350–600 € als Beispielhaushalt-Rechnung gekennzeichnet; Energiepreis-Kontext ergänzt; Inflations-/Tagesgeld-Einordnung auf Destatis Oktober 2026 (+2,8 %) aktualisiert.

- Heute in Zeile 200: 14,9 % – **ohne** Kennzeichnung

### `e8e32a383b6f803cc8d4`

**Befund:** Die Einschätzung zur Inflation ist unpräzise: Die aktuelle Inflationsrate liegt laut Destatis bei +2,8 % (Oktober 2026), wodurch die genannten Tagesgeldzinsen von 0,5 % bis 1,5 % den Wertverlust deutlich weniger ausgleichen als suggeriert.

**Frühere Entscheidung (2026-11-04):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 04.11.2026)

> Ersparnis-Spanne 350–600 € als Beispielhaushalt-Rechnung gekennzeichnet; Energiepreis-Kontext ergänzt; Inflations-/Tagesgeld-Einordnung auf Destatis Oktober 2026 (+2,8 %) aktualisiert.

- Heute in Zeile 115: 2,8 % – **ohne** Kennzeichnung
- Heute in Zeile 108: 0,5 % – **ohne** Kennzeichnung
- Heute in Zeile 23: 1,5 % – gekennzeichnet („beispielwert“)

## `2026-08-26-handytarif-vergleichen-2026-guenstige-tarife`

- Offene Live-Befunde: **5**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `0b4755213f0c38321710` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Behauptung 'kein üblicher Wechselgewinn' ohne Daten |
| `3e0c5fa74179e97866b8` | luecke | **neu** | 9,99 € in Zeile 32 gekennzeichnet | Preisangabe 9,99 € monatlich ohne Quelle |
| `ae90ebae2842ff9f97f1` | praezision | **neu** | kein Wert genannt (Aussage/Präzision) | Aussage über Downloadwert vs Gesprächsqualität ohne Beleg |
| `b2611d9120121d0ad785` | praezision | **neu** | kein Wert genannt (Aussage/Präzision) | Empfehlung, nicht den günstigsten Tarif zu wählen, fehlt Beleg |
| `fcb8168c18bd423c5180` | praezision | **neu** | kein Wert genannt (Aussage/Präzision) | Unterschiedliche Aufgaben von 2‑Jahres‑ vs monatlich kündbarem Vertrag ohne Beleg |

### `0b4755213f0c38321710`

**Befund:** Behauptung 'kein üblicher Wechselgewinn' ohne Daten

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `3e0c5fa74179e97866b8`

**Befund:** Preisangabe 9,99 € monatlich ohne Quelle

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Heute in Zeile 32: 9,99 € – gekennzeichnet („modellrechnung“)

### `ae90ebae2842ff9f97f1`

**Befund:** Aussage über Downloadwert vs Gesprächsqualität ohne Beleg

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `b2611d9120121d0ad785`

**Befund:** Empfehlung, nicht den günstigsten Tarif zu wählen, fehlt Beleg

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `fcb8168c18bd423c5180`

**Befund:** Unterschiedliche Aufgaben von 2‑Jahres‑ vs monatlich kündbarem Vertrag ohne Beleg

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

## `2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich`

- Offene Live-Befunde: **1**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `3ad12cdcf94bd8459bd8` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Bei der Erläuterung von Vermittlungsportalen fehlt die Einordnung als 'Kreditdienstleistungsinstitute', die die Bunde… |

### `3ad12cdcf94bd8459bd8`

**Befund:** Bei der Erläuterung von Vermittlungsportalen fehlt die Einordnung als 'Kreditdienstleistungsinstitute', die die Bundesbank als spezifischen Aspekt der Finanzaufsicht führt.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

## `2026-08-26-warmwasser-sparen-rechnung-hinter-dem-hahn`

- Offene Live-Befunde: **5**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `278d89267d9122a1e9d8` | luecke | 2026-11-11 · 2. Entscheidung | kein Wert genannt (Aussage/Präzision) | Angaben zu gesetzlichen Vorgaben für Warmwassertemperaturen zur Vermeidung von Legionellen werden nicht durch die ber… |
| `450c3aa629342062825e` | luecke | 2026-11-11 · 2. Entscheidung | kein Wert genannt (Aussage/Präzision) | Die Aussage, dass Warmwasser der zweitgrößte Kostenposten im Haushalt ist, wird nicht durch eine der bereitgestellten… |
| `7601167c9f3560093fb0` | luecke | 2026-11-11 · 2. Entscheidung | kein Wert genannt (Aussage/Präzision) | Die Behauptung, dass Warmwasser in der Heizkostenabrechnung üblicherweise als eigener Block ausgewiesen wird, fehlt e… |
| `7efbcd7a4275fe1577bb` | luecke | 2026-11-11 · 2. Entscheidung | kein Wert genannt (Aussage/Präzision) | Verweise auf die Verbraucherzentrale (Tipps zum Heizkosten sparen, Heizung optimieren) können nicht mit den angegeben… |
| `971a719f94ca492f640e` | luecke | 2026-11-11 · 2. Entscheidung | 0,30 € in Zeile 53 gekennzeichnet | Der Preis von 0,30 € pro Kilowattstunde in der Modellrechnung ist nicht mit einer Quelle belegt. |

### `278d89267d9122a1e9d8`

**Befund:** Angaben zu gesetzlichen Vorgaben für Warmwassertemperaturen zur Vermeidung von Legionellen werden nicht durch die bereitgestellten Quellen gestützt.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Die gesetzlichen Werte stehen heute mit Quelle im Abschnitt „Was Legionellen mit der Temperatur machen“: „Die Verbraucherzentrale nennt in ihrem Ratgeber Kosten für Warmwasser senken die maßgeblichen Werte: Im gesamten Warmwasser-Leitungssystem sollen mindestens 55 °C herrschen … In Speichern mit mehr als 400 Litern muss das Wasser am Speicherausgang gemäß Trinkwasserverordnung immer mindestens 60 °C erreichen … Prüfe die Einstellung deshalb alle drei Monate.“

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `450c3aa629342062825e`

**Befund:** Die Aussage, dass Warmwasser der zweitgrößte Kostenposten im Haushalt ist, wird nicht durch eine der bereitgestellten Quellen belegt.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Am heutigen Text geprüft (SHA-256 e30b40915c72): Die verlangte Quelle steht im Abschnitt „(Einleitung)“ inline – „Über das Jahr kommt viel zusammen: [co2online](https://www.co2online.de/energie-sparen/) beziffert die Wassererwärmung auf rund 16 Prozent des gesamten Haushalts-Energieverbrauchs,“. Der Befund trifft die heutige Fassung damit nicht mehr.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `7601167c9f3560093fb0`

**Befund:** Die Behauptung, dass Warmwasser in der Heizkostenabrechnung üblicherweise als eigener Block ausgewiesen wird, fehlt eine Quellenangabe.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Die Pflicht zur Kostentrennung ist mit der Verordnung belegt: „Bei zentraler Versorgung ist diese Trennung vorgeschrieben: [§ 9 Heizkostenverordnung] verlangt, die gemeinsam entstandenen Kosten einer verbundenen Anlage zu trennen“; § 9 Heizkostenverordnung steht zusätzlich in den Quellen.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `7efbcd7a4275fe1577bb`

**Befund:** Verweise auf die Verbraucherzentrale (Tipps zum Heizkosten sparen, Heizung optimieren) können nicht mit den angegebenen Fundstellen belegt werden.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Am heutigen Text geprüft (SHA-256 e30b40915c72): Die verlangte Quelle steht im Abschnitt „Warum die Abrechnung oft eine eigene Zeile braucht?“ inline – „Was du selbst steuern kannst und was Sache der Anlagentechnik bleibt, beschreibt die Verbraucherzentrale im Ratgeber [Kosten für Warmwasser senken](https://www.verbraucherzentrale.“. Der Befund trifft die heutige Fassung damit nicht mehr.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `971a719f94ca492f640e`

**Befund:** Der Preis von 0,30 € pro Kilowattstunde in der Modellrechnung ist nicht mit einer Quelle belegt.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Am heutigen Text geprüft (SHA-256 e30b40915c72): Die verlangte Quelle steht im Abschnitt „Modellrechnung: vier Personen, ein Jahr“ inline – „Zum Vergleich: Der [BDEW](https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/) nennt für Haushaltsstrom im Oktober 2026 durchschnittlich 37,3 Cent je kWh.“. Der Befund trifft die heutige Fassung damit nicht mehr.

- Heute in Zeile 53: 0,30 € – gekennzeichnet („rechenannahme“)

## `2026-08-28-lastschrift-und-dauerauftrag-abbuchungen-pruefen`

- Offene Live-Befunde: **5**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `1cc830a25d3ae505dd0e` | praezision | **neu** | 13 Monate in Zeile 177 ohne Kennzeichnung | Die Frist von acht Wochen gilt für autorisierte Lastschriften (ohne Angabe von Gründen). Bei unautorisierten Lastschr… |
| `32f827af8f4695488e97` | praezision | **neu** | kein Wert genannt (Aussage/Präzision) | Banken dürfen vom Zahler (Kontoinhaber) in der Regel kein Entgelt für eine Rücklastschrift verlangen, die mangels Dec… |
| `642d9c53e557ff642257` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Es fehlt der Hinweis auf die gesetzliche 13-Monats-Frist gemäß Zahlungsdiensterecht (PSD2) für die Meldung nicht auto… |
| `8230373c2c33722d66d8` | praezision | **neu** | kein Wert genannt (Aussage/Präzision) | Die Bezeichnung als 'wirksamste Maßnahme' ist ein Superlativ ohne messbare Datenbasis oder Vergleich mit anderen Sich… |
| `efee7b0cefffa501cc57` | praezision | **neu** | kein Wert genannt (Aussage/Präzision) | Stromabschläge sind untypisch für Daueraufträge, da sich die Beträge nach Jahresabrechnungen meist ändern; hier ist d… |

### `1cc830a25d3ae505dd0e`

**Befund:** Die Frist von acht Wochen gilt für autorisierte Lastschriften (ohne Angabe von Gründen). Bei unautorisierten Lastschriften (ohne Mandat) beträgt die gesetzliche Frist zur Rückgabe 13 Monate.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Heute in Zeile 177: 13 Monate – **ohne** Kennzeichnung

### `32f827af8f4695488e97`

**Befund:** Banken dürfen vom Zahler (Kontoinhaber) in der Regel kein Entgelt für eine Rücklastschrift verlangen, die mangels Deckung oder wegen eines berechtigten Widerspruchs erfolgt.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `642d9c53e557ff642257`

**Befund:** Es fehlt der Hinweis auf die gesetzliche 13-Monats-Frist gemäß Zahlungsdiensterecht (PSD2) für die Meldung nicht autorisierter oder fehlerhafter Kartenzahlungen.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `8230373c2c33722d66d8`

**Befund:** Die Bezeichnung als 'wirksamste Maßnahme' ist ein Superlativ ohne messbare Datenbasis oder Vergleich mit anderen Sicherheitsmechanismen.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `efee7b0cefffa501cc57`

**Befund:** Stromabschläge sind untypisch für Daueraufträge, da sich die Beträge nach Jahresabrechnungen meist ändern; hier ist die Lastschrift der Standard, um Zahlungsfehler zu vermeiden.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

## `2026-08-31-nachtstrom-tarife-wann-sich-ein-doppeltarifzaehler-noch-lohnt`

- Offene Live-Befunde: **2**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `dc1e5d50a58f50e0ade1` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Die verlinkte Seite der Bundesnetzagentur ist eine reine Navigations-Übersicht und enthält keine der im Text versproc… |
| `def8ad23c34566c795fe` | praezision | **neu** | kein Wert genannt (Aussage/Präzision) | Die Verknüpfung der HT/NT-Definition mit der Bundesnetzagentur ist unpräzise, da die verlinkte Seite lediglich eine T… |

### `dc1e5d50a58f50e0ade1`

**Befund:** Die verlinkte Seite der Bundesnetzagentur ist eine reine Navigations-Übersicht und enthält keine der im Text versprochenen Beschreibungen zu Tarifbestandteilen oder Preisregelungen.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `def8ad23c34566c795fe`

**Befund:** Die Verknüpfung der HT/NT-Definition mit der Bundesnetzagentur ist unpräzise, da die verlinkte Seite lediglich eine Themenübersicht ohne fachliche Definitionen darstellt.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

## `2026-08-31-stoerung-beim-internetanbieter-so-sicherst-du-deine-rechte`

- Offene Live-Befunde: **5**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `19a724ba20628f34cd01` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Eine feste Frist für die Entstörung nennt das Gesetz nicht. |
| `4126d33a9dd92716b286` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Ein unentschuldigter no-show zählt nur, wenn du ihn zeitnah meldest. |
| `67fbe0b49bb4e6bb48b7` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Die Pflichten aus dem TKG gelten für alle Zugangsarten. |
| `cb5f849bfd26ad8121eb` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Der Anbieter muss die Störung beheben; eine pauschale Wartezeit gibt es nicht, aber eine Pflicht zur zeitnahen Entstö… |
| `f108d554ff8861370b64` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Bei einem längeren Ausfall hast du zwei Hebel: die Gutschrift für die ausgefallene Leistung und bei einigen Verzögeru… |

### `19a724ba20628f34cd01`

**Befund:** Eine feste Frist für die Entstörung nennt das Gesetz nicht.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `4126d33a9dd92716b286`

**Befund:** Ein unentschuldigter no-show zählt nur, wenn du ihn zeitnah meldest.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `67fbe0b49bb4e6bb48b7`

**Befund:** Die Pflichten aus dem TKG gelten für alle Zugangsarten.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `cb5f849bfd26ad8121eb`

**Befund:** Der Anbieter muss die Störung beheben; eine pauschale Wartezeit gibt es nicht, aber eine Pflicht zur zeitnahen Entstörung.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `f108d554ff8861370b64`

**Befund:** Bei einem längeren Ausfall hast du zwei Hebel: die Gutschrift für die ausgefallene Leistung und bei einigen Verzögerungen die Entschädigung.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

## `2026-09-03-kreditkarte-vergleichen-kostenlos-sicher-bezahlen`

- Offene Live-Befunde: **5**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `16b3b8584ff802803aa9` | luecke | 2026-11-11 · 2. Entscheidung | kein Wert genannt (Aussage/Präzision) | Angaben zum Fremdwährungsentgelt von „fast zwei Prozent“ bei Zahlungen in fremder Währung fehlen jede belegbare Refer… |
| `7ff042b6fe804cdf101b` | praezision | 2026-11-11 · 2. Entscheidung | kein Wert genannt (Aussage/Präzision) | Formulierungen wie „einige Anbieter ohne Auslandsgebühr gehören zu den besten Karten für Reisen“ sind pauschal und oh… |
| `bec83c4b814183fa1086` | luecke | 2026-11-11 · 2. Entscheidung | kein Wert genannt (Aussage/Präzision) | Die Aussage, dass die kostenlose Sperr‑Notrufnummer 116 für alle Karten in Deutschland gilt, wird nicht durch eine Qu… |
| `f9aff86b6eba71b153a6` | luecke | 2026-11-11 · 2. Entscheidung | 12 % in Zeile 147 ohne Kennzeichnung · 20 % in Zeile 9 ohne Kennzeichnung | Die Angabe, dass Sollzinsen bei Teilzahlung zwischen 12 % und 20 % liegen, ist nicht mit einer Quelle belegt. |
| `fed9215b770ea4879eda` | luecke | 2026-11-11 · 2. Entscheidung | kein Wert genannt (Aussage/Präzision) | Die Behauptung, dass eine gute Kreditkarte im Jahr nichts kostet (keine Jahres‑ und keine Fremdwährungsgebühr), wird… |

### `16b3b8584ff802803aa9`

**Befund:** Angaben zum Fremdwährungsentgelt von „fast zwei Prozent“ bei Zahlungen in fremder Währung fehlen jede belegbare Referenz.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Die unbelegte Spanne „fast zwei Prozent“ ist weg. Der Einstieg nennt sie nur noch als Größe im gekennzeichneten Modellfall („Für viele ist die Kreditkarte eine unsichtbare Gebührenquelle im Modellfall. Zwölf Euro im Jahr hier, zwei Prozent im Ausland dort.“); die Entscheidungskriterien stehen ohne Prozentsatz in der Liste.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `7ff042b6fe804cdf101b`

**Befund:** Formulierungen wie „einige Anbieter ohne Auslandsgebühr gehören zu den besten Karten für Reisen“ sind pauschal und ohne messbare Daten unpräzise.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Der Superlativ ist abgeschwächt: „Anbieter ohne Auslandsgebühr gibt es einige. Für Reisende sind sie deshalb einen genauen Blick wert.“ Eine Rangfolge behauptet der Text nicht mehr.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `bec83c4b814183fa1086`

**Befund:** Die Aussage, dass die kostenlose Sperr‑Notrufnummer 116 für alle Karten in Deutschland gilt, wird nicht durch eine Quelle gestützt.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Am heutigen Text geprüft (SHA-256 a24a9546d5e8): Die Zahl steht weiterhin im Artikel, ist aber ausdrücklich als Modell-/Beispielwert gekennzeichnet: „Die Sperr-Notrufnummer [116 116](https://www.sperr-notruf.de/) sperrt Karten rund um die Uhr; aus dem deutschen Festnetz ist der Anruf kostenlos.“. Beanstandet war die Zahl OHNE Kennzeichnung; das trifft nicht mehr zu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `f9aff86b6eba71b153a6`

**Befund:** Die Angabe, dass Sollzinsen bei Teilzahlung zwischen 12 % und 20 % liegen, ist nicht mit einer Quelle belegt.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Die Spanne „12 % bis 20 %“ steht nicht mehr im Artikel; die Passage sagt jetzt „Die Sollzinsen stehen im Preisverzeichnis und sind in der Regel hoch“ und verweist damit auf die individuelle Vertragsunterlage statt auf eine unbelegte Marktspanne.

- Heute in Zeile 147: 12 % – **ohne** Kennzeichnung
- Heute in Zeile 9: 20 % – **ohne** Kennzeichnung

### `fed9215b770ea4879eda`

**Befund:** Die Behauptung, dass eine gute Kreditkarte im Jahr nichts kostet (keine Jahres‑ und keine Fremdwährungsgebühr), wird ohne jegliche Quelle angegeben.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Die Pauschalaussage ist entschärft: „Eine gute Kreditkarte kann im Jahr ohne Jahresgebühr auskommen und außerhalb Europas ohne Zusatzentgelt funktionieren – der Preis sitzt im Fremdwährungsentgelt und in der Teilzahlung.“ Die Kurzantwort sagt „kann dich im Jahr nichts kosten: Es gibt Karten ohne …“.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

## `2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich`

- Offene Live-Befunde: **2**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `20c08cb650ef6e24af64` | luecke | 2026-11-11 · 2. Entscheidung | 14,9 % in Zeile 116 gekennzeichnet | Der Ratgeber vernachlässigt bei der Kalkulation der Sparfähigkeit die massive Preissteigerung bei Energie (+14,9 %),… |
| `6aafb23c0c6dbb06ce3b` | veraltet | 2026-11-11 · 2. Entscheidung | 2 % in Zeile 5 ohne Kennzeichnung · 2,8 % in Zeile 116 gekennzeichnet | Die im Rechenbeispiel zur Realrendite genutzte Inflationsrate von 2 % ist veraltet; die vorläufige Rate für Oktober 2… |

### `20c08cb650ef6e24af64`

**Befund:** Der Ratgeber vernachlässigt bei der Kalkulation der Sparfähigkeit die massive Preissteigerung bei Energie (+14,9 %), die das Budget für monatliche Sparraten erheblich belastet.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Der Befund ist am heutigen Text erledigt. Der Abschnitt „Energiepreise in der Kalkulation nicht vergessen“ nennt die Preissteigerung mit Quelle: „Energie ist dabei ein wesentlicher Posten: Energieprodukte kosteten laut Statistischem Bundesamt (Verbraucherpreisindex) im Oktober 2026 vorläufig 2,8 % mehr als ein Jahr zuvor“, ergänzt um die Quellenzeile (Destatis, Verbraucherpreisindex). Die frühere Feststellung „keine Energiepreise im Text“ ist durch diese spätere Ergänzung überholt.

- Heute in Zeile 116: 14,9 % – gekennzeichnet („modellwert“)

### `6aafb23c0c6dbb06ce3b`

**Befund:** Die im Rechenbeispiel zur Realrendite genutzte Inflationsrate von 2 % ist veraltet; die vorläufige Rate für Oktober 2026 beträgt laut Statistischem Bundesamt 2,8 %.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Die veraltete 2-%-Rate ist ersetzt: „Bei der vorläufigen Inflationsrate für Oktober 2026 von 2,8 % (Statistisches Bundesamt, Verbraucherpreisindex) verliert das Geld jedes Jahr knapp 3 % seiner Kaufkraft; das ist ein Beispielwert.“

- Heute in Zeile 5: 2 % – **ohne** Kennzeichnung
- Heute in Zeile 116: 2,8 % – gekennzeichnet („modellwert“)

## `2026-09-07-frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum`

- Offene Live-Befunde: **3**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `24f05ddc03ffdd50118f` | praezision | 2026-11-11 · 4. Entscheidung | 14,9 % in Zeile 111 gekennzeichnet | Die Kalkulation der Fixkostenersparnis bei Energie (Strom/Gas) ist unpräzise, da sie den aktuellen Preisanstieg von +… |
| `4816322f061dfdc03bcd` | luecke | 2026-11-11 · 4. Entscheidung | 0,4 % in Zeile 151 gekennzeichnet | Bei den Einsparpotenzialen für Lebensmittel fehlt der Bezug zur aktuellen Preissteigerung von +0,4 % bei Nahrungsmitt… |
| `7017065ee7c74c7ae452` | veraltet | 2026-11-11 · 4. Entscheidung | 2,8 % in Zeile 174 ohne Kennzeichnung | Der Artikel nutzt Kostenszenarien für 2024/2025, während aktuelle Daten für Oktober 2026 eine Inflationsrate von +2,8… |

### `24f05ddc03ffdd50118f`

**Befund:** Die Kalkulation der Fixkostenersparnis bei Energie (Strom/Gas) ist unpräzise, da sie den aktuellen Preisanstieg von +14,9 % bei Energieprodukten nicht einbezieht.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Der Preisanstieg steht mit Quelle im Artikel: „Laut vorläufigem Verbraucherpreisindex des Statistischen Bundesamts lagen die Energieprodukte im Oktober 2026 um +14,9 % über dem Vorjahreswert.“ Die Fixkostenrechnung ist damit auf dem aktuellen Stand.

- Heute in Zeile 111: 14,9 % – gekennzeichnet („annahme“)

### `4816322f061dfdc03bcd`

**Befund:** Bei den Einsparpotenzialen für Lebensmittel fehlt der Bezug zur aktuellen Preissteigerung von +0,4 % bei Nahrungsmitteln.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Der Bezug zu Nahrungsmitteln steht mit Quelle: „Nach dem Indexstand des Statistischen Bundesamts lagen Nahrungsmittel im Oktober 2026 um +0,4 % über dem Niveau des Vorjahresmonats.“ Die Einsparpotenziale sind damit eingeordnet.

- Heute in Zeile 151: 0,4 % – gekennzeichnet („orientierungswert“)

### `7017065ee7c74c7ae452`

**Befund:** Der Artikel nutzt Kostenszenarien für 2024/2025, während aktuelle Daten für Oktober 2026 eine Inflationsrate von +2,8 % ausweisen.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Am heutigen Text geprüft (SHA-256 5bd6779ecdc7): Die Zahl steht weiterhin im Artikel, ist aber ausdrücklich als Modell-/Beispielwert gekennzeichnet: „## Ein Rechenbeispiel: Die Macht kleiner Beträge Nehmen wir ein bewusst vereinfachtes Beispielszenario zum Preisstand Oktober 2026 (Inflationsrate vorläufig 2,8 %, Statistisches Bundesamt, V“. Beanstandet war die Zahl OHNE Kennzeichnung; das trifft nicht mehr zu.

- Heute in Zeile 174: 2,8 % – **ohne** Kennzeichnung

## `2026-09-07-frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler`

- Offene Live-Befunde: **3**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `1e06a96f6f71e104ce0b` | praezision | 2026-11-11 · 3. Entscheidung | 0,4 % in Zeile 34 ohne Kennzeichnung | Während Meal Prep als großer Sparhebel betont wird, zeigt die Marktlage für Nahrungsmittel eine moderate Teuerung von… |
| `81c6a707139046b83ccd` | luecke | 2026-11-11 · 3. Entscheidung | 14,9 % in Zeile 34 ohne Kennzeichnung | Der Ratgeber empfiehlt die Revision von Fixkosten, lässt aber die drastische Preissteigerung bei Energie von +14,9 %… |
| `8cc00288af8a1f2b02d8` | veraltet | 2026-11-11 · 3. Entscheidung | 2,8 % in Zeile 34 ohne Kennzeichnung | Die Budget-Tipps berücksichtigen nicht die aktuelle Inflationsrate von 2,8 % (Stand Oktober 2026), was die Kaufkraft-… |

### `1e06a96f6f71e104ce0b`

**Befund:** Während Meal Prep als großer Sparhebel betont wird, zeigt die Marktlage für Nahrungsmittel eine moderate Teuerung von nur 0,4 %, was die Priorisierung der Sparbemühungen relativiert.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Die Priorisierung ist relativiert: „Hinweis zum Stand der Preise: Nach dem Indexstand des Statistischen Bundesamts lagen Nahrungsmittel im Oktober 2026 um +0,4 % über dem Niveau des Vorjahresmonats. Die Beispiele sind Orientierungswerte“ – mit eigener Quellenzeile darunter. Die Meal-Prep-Empfehlung steht damit neben dem belegten Preisfeld.

- Heute in Zeile 34: 0,4 % – **ohne** Kennzeichnung

### `81c6a707139046b83ccd`

**Befund:** Der Ratgeber empfiehlt die Revision von Fixkosten, lässt aber die drastische Preissteigerung bei Energie von +14,9 % unerwähnt, die ein wesentlicher Treiber der Haushaltsausgaben ist.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Am heutigen Text geprüft (SHA-256 5708f03841d4): Die verlangte Quelle steht im Abschnitt „Warum diese Frugalismus-Tipps dein Mindset verändern“ inline – „**Hinweis zum Stand der Preise:** Im Oktober 2026 lagen die Verbraucherpreise um **+2,8 %** über dem Vorjahr, Energie um **+14,9 %** und Nahrungsmittel um **+0,4 %** ([Statistische“. Der Befund trifft die heutige Fassung damit nicht mehr.

- Heute in Zeile 34: 14,9 % – **ohne** Kennzeichnung

### `8cc00288af8a1f2b02d8`

**Befund:** Die Budget-Tipps berücksichtigen nicht die aktuelle Inflationsrate von 2,8 % (Stand Oktober 2026), was die Kaufkraft-Annahmen im Haushaltsbuch beeinflusst.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Am heutigen Text geprüft (SHA-256 5708f03841d4): Die verlangte Quelle steht im Abschnitt „Warum diese Frugalismus-Tipps dein Mindset verändern“ inline – „**Hinweis zum Stand der Preise:** Im Oktober 2026 lagen die Verbraucherpreise um **+2,8 %** über dem Vorjahr, Energie um **+14,9 %** und Nahrungsmittel um **+0,4 %** ([Statistische“. Der Befund trifft die heutige Fassung damit nicht mehr.

- Heute in Zeile 34: 2,8 % – **ohne** Kennzeichnung

## `2026-09-07-heizkosten-senken-mit-diesen-strategien-sparst-du-sofort`

- Offene Live-Befunde: **3**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `3f0a88ede9d44ee910cb` | luecke | 2026-11-23 · 2. Entscheidung | kein Wert genannt (Aussage/Präzision) | Es fehlt der Hinweis auf das offizielle Beschwerdeportal der Bundesnetzagentur, über das Verbraucher Probleme mit Anb… |
| `51e259fd2d8582e774f7` | luecke | 2026-11-23 · 2. Entscheidung | kein Wert genannt (Aussage/Präzision) | Der Ratgeber versäumt es, bei der Tarifprüfung auf die behördlichen Schlichtungsverfahren hinzuweisen, die Verbrauche… |
| `55f8eeedc587cf0895ee` | luecke | 2026-11-23 · 2. Entscheidung | kein Wert genannt (Aussage/Präzision) | Der Artikel erwähnt keine behördlichen Informationsquellen wie das Verbraucher-Radar, das Transparenz über den Energi… |

### `3f0a88ede9d44ee910cb`

**Befund:** Es fehlt der Hinweis auf das offizielle Beschwerdeportal der Bundesnetzagentur, über das Verbraucher Probleme mit Anbietern direkt melden können.

**Frühere Entscheidung (2026-11-23):** Frank Hartung (Betreiber-Freigabe über Arena-Session, 23.11.2026)

> Volltext am 23.11.2026 geprüft & ergänzt (Welle 1): Der Verbraucherservice Energie der Bundesnetzagentur für Anfragen und Beschwerden ist im Artikel explizit genannt.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `51e259fd2d8582e774f7`

**Befund:** Der Ratgeber versäumt es, bei der Tarifprüfung auf die behördlichen Schlichtungsverfahren hinzuweisen, die Verbrauchern bei Streitigkeiten mit Energieversorgern zur Verfügung stehen.

**Frühere Entscheidung (2026-11-23):** Frank Hartung (Betreiber-Freigabe über Arena-Session, 23.11.2026)

> Volltext am 23.11.2026 geprüft (Welle 1): Die kostenfreie Schlichtungsstelle Energie ist im heutigen Text direkt verlinkt.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `55f8eeedc587cf0895ee`

**Befund:** Der Artikel erwähnt keine behördlichen Informationsquellen wie das Verbraucher-Radar, das Transparenz über den Energiemarkt und Verbraucherschutzthemen bietet.

**Frühere Entscheidung (2026-11-23):** Frank Hartung (Betreiber-Freigabe über Arena-Session, 23.11.2026)

> Volltext am 23.11.2026 geprüft (Welle 1): Behördliche Markttransparenzquellen der Bundesnetzagentur (Preisübersichten für Haushaltskunden und SMARD) sind direkt verlinkt.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

## `2026-09-09-notgroschen-die-wahrheit-ueber-das-finanzielle-polster`

- Offene Live-Befunde: **2**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `009906e47bcc8265b36a` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Angestellte reichen oft drei bis sechs Monatsausgaben als Sicherheit |
| `e0293a43782c64955b27` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Selbstständige sollten sechs‑ bis zwölf‑Monats‑Ausgaben als Reserve planen |

### `009906e47bcc8265b36a`

**Befund:** Angestellte reichen oft drei bis sechs Monatsausgaben als Sicherheit

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `e0293a43782c64955b27`

**Befund:** Selbstständige sollten sechs‑ bis zwölf‑Monats‑Ausgaben als Reserve planen

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

## `2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag`

- Offene Live-Befunde: **3**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `5a1bf10697f58e5fe14a` | luecke | 2026-11-11 · 3. Entscheidung | 14,9 % in Zeile 36 ohne Kennzeichnung | Der Ratgeber nennt Sparbeispiele für Heizkosten, lässt aber die aktuelle Preissteigerung bei Energie von +14,9 % (Sta… |
| `e48f9237cff6397c49a6` | praezision | 2026-11-11 · 3. Entscheidung | 200 € in Zeile 7 gekennzeichnet · 2,8 % in Zeile 9 gekennzeichnet | Die in Aussicht gestellten Ersparnisse von bis zu 200 € werden nicht ins Verhältnis zur aktuellen Inflationsrate von… |
| `f6de6b078d49f9d42e0e` | praezision | 2026-11-11 · 3. Entscheidung | 0,4 % in Zeile 38 ohne Kennzeichnung | Beim Fokus auf Lebensmittelplanung fehlt der Hinweis auf die vergleichsweise moderate Preissteigerung von +0,4 % bei… |

### `5a1bf10697f58e5fe14a`

**Befund:** Der Ratgeber nennt Sparbeispiele für Heizkosten, lässt aber die aktuelle Preissteigerung bei Energie von +14,9 % (Stand Oktober 2026) unerwähnt, die den finanziellen Druck auf Haushalte massiv erhöht.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Am heutigen Text geprüft (SHA-256 86d47ae20559): Die verlangte Quelle steht im Abschnitt „(Einleitung)“ inline – „**Damit du die Summe richtig einordnest:** Die Inflationsrate lag im Oktober 2026 bei **+2,8 %** ([Statistisches Bundesamt](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verb“. Der Befund trifft die heutige Fassung damit nicht mehr.

- Heute in Zeile 36: 14,9 % – **ohne** Kennzeichnung

### `e48f9237cff6397c49a6`

**Befund:** Die in Aussicht gestellten Ersparnisse von bis zu 200 € werden nicht ins Verhältnis zur aktuellen Inflationsrate von +2,8 % gesetzt, welche die reale Kaufkraft des gesparten Geldes mindert.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Am heutigen Text geprüft (SHA-256 86d47ae20559): Die verlangte Quelle steht inline: „**Damit du die Summe richtig einordnest:** Die Inflationsrate lag im Oktober 2026 bei **+2,8 %** ([Statistisches Bundesamt](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpre“. Die Aussage ist an der Fundstelle belegt; der Befund trifft die heutige Fassung nicht mehr.

- Heute in Zeile 7: 200 € – gekennzeichnet („modellwert“)
- Heute in Zeile 9: 2,8 % – gekennzeichnet („modellrechnung“)

### `f6de6b078d49f9d42e0e`

**Befund:** Beim Fokus auf Lebensmittelplanung fehlt der Hinweis auf die vergleichsweise moderate Preissteigerung von +0,4 % bei Nahrungsmitteln, was diesen Hebel gegenüber den stark steigenden Energiekosten relativiert.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Am heutigen Text geprüft (SHA-256 86d47ae20559): Die verlangte Quelle steht im Abschnitt „(Einleitung)“ inline – „**Damit du die Summe richtig einordnest:** Die Inflationsrate lag im Oktober 2026 bei **+2,8 %** ([Statistisches Bundesamt](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verb“. Der Befund trifft die heutige Fassung damit nicht mehr.

- Heute in Zeile 38: 0,4 % – **ohne** Kennzeichnung

## `2026-09-11-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026`

- Offene Live-Befunde: **2**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `6cb2229c5eb83b02da23` | veraltet | 2026-11-11 · 4. Entscheidung | 140 € in Zeile 104 gekennzeichnet · 14,9 % in Zeile 96 ohne Kennzeichnung | Die Kalkulation der Fixkosten (Energie 140 €) und die Empfehlung zur Senkung der Kosten ignorieren den aktuellen Mark… |
| `f00055a1cb65ee22165f` | luecke | 2026-11-11 · 4. Entscheidung | 2,8 % in Zeile 82 ohne Kennzeichnung · 0,4 % in Zeile 98 ohne Kennzeichnung | Der Ratgeber verspricht eine 'planbare' Budgetierung, lässt aber die aktuelle Inflationsrate von 2,8 % unerwähnt, die… |

### `6cb2229c5eb83b02da23`

**Befund:** Die Kalkulation der Fixkosten (Energie 140 €) und die Empfehlung zur Senkung der Kosten ignorieren den aktuellen Markttrend massiv steigender Energiepreise (+14,9 %), was die 50-Prozent-Quote für notwendige Ausgaben gefährdet.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Am heutigen Text geprüft (SHA-256 b085bf3a0f5a): Die verlangte Quelle steht im Abschnitt „Preisänderungen im Budget berücksichtigen“ inline – „Die Oktober-Schätzung von [Destatis](https://www.destatis.de/DE/Presse/Pressemitteilungen/2026/10/PD26_382_611.html) vom 30.10.2026 zeigt 2,8 Prozent Inflation.“. Der Befund trifft die heutige Fassung damit nicht mehr.

- Heute in Zeile 104: 140 € – gekennzeichnet („modellrechnung“)
- Heute in Zeile 96: 14,9 % – **ohne** Kennzeichnung

### `f00055a1cb65ee22165f`

**Befund:** Der Ratgeber verspricht eine 'planbare' Budgetierung, lässt aber die aktuelle Inflationsrate von 2,8 % unerwähnt, die insbesondere den Block der notwendigen Ausgaben (Nahrungsmittel +0,4 %) dynamisch belastet.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Am heutigen Text geprüft (SHA-256 b085bf3a0f5a): Die verlangte Quelle steht im Abschnitt „Preisänderungen im Budget berücksichtigen“ inline – „Die Oktober-Schätzung von [Destatis](https://www.destatis.de/DE/Presse/Pressemitteilungen/2026/10/PD26_382_611.html) vom 30.10.2026 zeigt 2,8 Prozent Inflation.“. Der Befund trifft die heutige Fassung damit nicht mehr.

- Heute in Zeile 82: 2,8 % – **ohne** Kennzeichnung
- Heute in Zeile 98: 0,4 % – **ohne** Kennzeichnung

## `2026-09-11-standby-kosten-reduzieren-so-entlarvst-du-stromfresser`

- Offene Live-Befunde: **5**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `7a87eaaa2b863ba8cc46` | luecke | 2026-11-11 · 1. Entscheidung | kein Wert genannt (Aussage/Präzision) | Ein relevanter regulatorischer Rahmen (z. B. Vorgaben der Bundesnetzagentur oder BDEW) wird nicht genannt, obwohl die… |
| `9d67a5e6bd11212c7c1e` | praezision | 2026-11-11 · 1. Entscheidung | kein Wert genannt (Aussage/Präzision) | Die Aussage, dass bestimmte Gerätegruppen (TV‑Ecke, Homeoffice, alte Audio‑Technik) zuerst zu senken „lohnt“, wird oh… |
| `a54abc1cad73d20fb689` | luecke | 2026-11-11 · 1. Entscheidung | 32 € in Zeile 22 ohne Kennzeichnung | Die konkreten Jahreskosten (z. B. 32 € für 10 W Standby) beruhen auf dem nicht belegten Strompreis und werden nicht a… |
| `a7d1cf6485921e117919` | luecke | 2026-11-11 · 1. Entscheidung | 37,3 Cent in Zeile 44 gekennzeichnet | Der angegebene durchschnittliche Strompreis von 37,3 Cent/kWh (BDEW‑Schnitt) wird ohne Quellenangabe genannt. |
| `a7f69a854430d62a4a3e` | luecke | 2026-11-11 · 1. Entscheidung | kein Wert genannt (Aussage/Präzision) | Die Empfehlung, dass ein günstigerer Arbeitspreis der zweite wichtigste Hebel sei, fehlt jede Quelle oder regulatoris… |

### `7a87eaaa2b863ba8cc46`

**Befund:** Ein relevanter regulatorischer Rahmen (z. B. Vorgaben der Bundesnetzagentur oder BDEW) wird nicht genannt, obwohl die Fundstelle darauf hinweist, dass solche Vorgaben existieren.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Der Rahmen ist jetzt benannt: „Für viele Standby-Zustände gelten strenge Grenzwerte der EU-Ökodesign-Verordnung. Netzwerk-Bereitschaft und aktive Komfortfunktionen können trotzdem mehr Strom ziehen.“ Preisgrundlage bleibt der inline belegte BDEW-Wert.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `9d67a5e6bd11212c7c1e`

**Befund:** Die Aussage, dass bestimmte Gerätegruppen (TV‑Ecke, Homeoffice, alte Audio‑Technik) zuerst zu senken „lohnt“, wird ohne messbare Daten oder Vergleichskriterien gemacht.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Die Reihenfolge ist keine Behauptung mehr, sondern folgt der Rechentabelle (1/5/10/20/30 Watt mit Jahresverbrauch und Kosten bei 0,37 €/kWh), samt Einordnung „Ein Ladegerät mit 0,1 Watt Leerlauf lohnt keine Mühe“. Der Leser kann die Gruppen selbst nachrechnen.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `a54abc1cad73d20fb689`

**Befund:** Die konkreten Jahreskosten (z. B. 32 € für 10 W Standby) beruhen auf dem nicht belegten Strompreis und werden nicht als Modellrechnung gekennzeichnet.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Die Rechnung ist als Modell gekennzeichnet: „10 Watt rund um die Uhr entsprechen 87,6 kWh und bei 0,37 €/kWh rund 32 € im Jahr (Rechenbeispiel)“, dazu die Tabelle mit dem Rechenweg. Der Preis ist Rechenwert mit BDEW-Beleg.

- Heute in Zeile 22: 32 € – **ohne** Kennzeichnung

### `a7d1cf6485921e117919`

**Befund:** Der angegebene durchschnittliche Strompreis von 37,3 Cent/kWh (BDEW‑Schnitt) wird ohne Quellenangabe genannt.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Am heutigen Text geprüft (SHA-256 0964b3927ad1): Die verlangte Quelle steht im Abschnitt „So rechnest du wenige Watt in Jahreskosten um“ inline – „Der BDEW-Schnitt von 37,3 Cent pro kWh{{< beleg kennzahl="bdew-haushaltsstrompreis" kurz="BDEW" >}} dient hier nur als Rechenwert.“. Der Befund trifft die heutige Fassung damit nicht mehr.

- Heute in Zeile 44: 37,3 Cent – gekennzeichnet („beispielwert“)

### `a7f69a854430d62a4a3e`

**Befund:** Die Empfehlung, dass ein günstigerer Arbeitspreis der zweite wichtigste Hebel sei, fehlt jede Quelle oder regulatorische Einordnung.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Beanstandet war eine Empfehlung, keine Tatsachenbehauptung: „Ein günstigerer Arbeitspreis ist der zweite: [Stromanbieter vergleichen & wechseln]“. Ein Beleg ist dafür nicht zu führen; die Passage bleibt Handlungsempfehlung ohne Zahlenanspruch. Befund abgelehnt.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

## `2026-09-20-finanzieller-puffer-wie-viel-notgroschen-ist-genug`

- Offene Live-Befunde: **3**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `3eab428a91b1b16b7df8` | luecke | **neu** | nicht mehr im Text: 2,8 % | Die aktuelle Inflationsrate von +2,8 % wird nicht genannt, obwohl sie für die empfohlene regelmäßige Prüfung der Puff… |
| `7da9383cbc6a45e1a3ac` | praezision | **neu** | nicht mehr im Text: 0,4 % · 320 € in Zeile 74 ohne Kennzeichnung | Der Modellwert für Lebensmittel (320 €) wird nicht mit der aktuellen Preissteigerung von +0,4 % abgeglichen, um die V… |
| `da7852bcca291061c39b` | praezision | **neu** | nicht mehr im Text: 12,7 % | Die Modellrechnung für Fixkosten berücksichtigt nicht die spezifische Teuerung bei Energie (+12,7 %), was bei der Kal… |

### `3eab428a91b1b16b7df8`

**Befund:** Die aktuelle Inflationsrate von +2,8 % wird nicht genannt, obwohl sie für die empfohlene regelmäßige Prüfung der Pufferhöhe die zentrale Rechengröße darstellt.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Im heutigen Text nicht mehr vorhanden: 2,8 %

### `7da9383cbc6a45e1a3ac`

**Befund:** Der Modellwert für Lebensmittel (320 €) wird nicht mit der aktuellen Preissteigerung von +0,4 % abgeglichen, um die Validität der Kalkulationsbasis zu stützen.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Im heutigen Text nicht mehr vorhanden: 0,4 %
- Heute in Zeile 74: 320 € – **ohne** Kennzeichnung

### `da7852bcca291061c39b`

**Befund:** Die Modellrechnung für Fixkosten berücksichtigt nicht die spezifische Teuerung bei Energie (+12,7 %), was bei der Kalkulation von Strom und Gas zu einer Unterdeckung führen kann.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Im heutigen Text nicht mehr vorhanden: 12,7 %

## `2026-09-20-gasrechnung-senken-spaetsommer-check-spart-hunderte-euro`

- Offene Live-Befunde: **5**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `334751e6f61ad0033fe4` | luecke | 2026-11-23 · 3. Entscheidung | 20.000 kWh in Zeile 164 ohne Kennzeichnung · 360 € in Zeile 164 ohne Kennzeichnung | Die Angabe, dass ein Gaslieferantenwechsel bei 20.000 kWh im Januar 2026 im Schnitt etwa 360 € spart, fehlt jede Quel… |
| `36759a5efe5e8e5163d0` | luecke | 2026-11-23 · 3. Entscheidung | 6 % in Zeile 5 ohne Kennzeichnung | Die Faustregel der Verbraucherzentrale, dass pro Grad weniger Raumtemperatur der Heizbedarf um etwa 6 % sinkt, wird o… |
| `942922d1afd7844618e9` | luecke | 2026-11-23 · 3. Entscheidung | 1 Cent in Zeile 5 ohne Kennzeichnung · 18.000 kWh in Zeile 9 ohne Kennzeichnung · 180 € in Zeile 9 ohne Kennzeichnung | Die Rechnung „1 Cent pro kWh bei 18.000 kWh Jahresverbrauch ergibt rund 180 € im Jahr“ wird nicht belegt. |
| `d41f0d5ce8798df0211b` | praezision | 2026-11-23 · 3. Entscheidung | kein Wert genannt (Aussage/Präzision) | Die Aussage „Die besten Tarife findest du über unseren Partner‑Vergleich“ ist ein Superlativ ohne messbare Daten oder… |
| `e139d0769faadd04392a` | luecke | 2026-11-23 · 3. Entscheidung | nicht mehr im Text: 11,93 Cent | Der BDEW‑Durchschnittspreis von 11,93 Cent/kWh für 2026 wird ohne Quellenangabe genannt. |

### `334751e6f61ad0033fe4`

**Befund:** Die Angabe, dass ein Gaslieferantenwechsel bei 20.000 kWh im Januar 2026 im Schnitt etwa 360 € spart, fehlt jede Quellenangabe.

**Frühere Entscheidung (2026-11-23):** Frank Hartung (Betreiber-Freigabe über Arena-Session, 23.11.2026)

> Volltext am 23.11.2026 geprüft & präzisiert (Welle 1): Die 360 € bei 20.000 kWh und 1,8 Cent/kWh Differenz stehen ausdrücklich als 'Rechenbeispiel ohne Marktversprechen' ohne Behauptung eines Januar-2026-Durchschnitts.

- Heute in Zeile 164: 20.000 kWh – **ohne** Kennzeichnung
- Heute in Zeile 164: 360 € – **ohne** Kennzeichnung

### `36759a5efe5e8e5163d0`

**Befund:** Die Faustregel der Verbraucherzentrale, dass pro Grad weniger Raumtemperatur der Heizbedarf um etwa 6 % sinkt, wird ohne Quelle angegeben.

**Frühere Entscheidung (2026-11-23):** Frank Hartung (Betreiber-Freigabe über Arena-Session, 23.11.2026)

> Volltext am 23.11.2026 geprüft (Welle 1): Die 6-%-Faustregel je Grad Raumtemperatur verlinkt direkt auf den Ratgeber der Verbraucherzentrale.

- Heute in Zeile 5: 6 % – **ohne** Kennzeichnung

### `942922d1afd7844618e9`

**Befund:** Die Rechnung „1 Cent pro kWh bei 18.000 kWh Jahresverbrauch ergibt rund 180 € im Jahr“ wird nicht belegt.

**Frühere Entscheidung (2026-11-23):** Frank Hartung (Betreiber-Freigabe über Arena-Session, 23.11.2026)

> Volltext am 23.11.2026 geprüft (Welle 1): 1 Cent × 18.000 kWh = 180 € ist eine rein arithmetische Beispielrechnung im ausdrücklich gekennzeichneten Modellfall.

- Heute in Zeile 5: 1 Cent – **ohne** Kennzeichnung
- Heute in Zeile 9: 18.000 kWh – **ohne** Kennzeichnung
- Heute in Zeile 9: 180 € – **ohne** Kennzeichnung

### `d41f0d5ce8798df0211b`

**Befund:** Die Aussage „Die besten Tarife findest du über unseren Partner‑Vergleich“ ist ein Superlativ ohne messbare Daten oder Vergleichskriterien.

**Frühere Entscheidung (2026-11-23):** Frank Hartung (Betreiber-Freigabe über Arena-Session, 23.11.2026)

> Volltext am 23.11.2026 geprüft (Welle 1): Der Superlativ 'Die besten Tarife' steht nicht mehr im Artikel.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `e139d0769faadd04392a`

**Befund:** Der BDEW‑Durchschnittspreis von 11,93 Cent/kWh für 2026 wird ohne Quellenangabe genannt.

**Frühere Entscheidung (2026-11-23):** Frank Hartung (Betreiber-Freigabe über Arena-Session, 23.11.2026)

> Volltext am 23.11.2026 geprüft (Welle 1): Der alte Wert 11,93 Cent/kWh wurde entfernt; stattdessen verlinkt der Artikel auf die BDEW-Gaspreisanalyse Herbst 2026 (12,23 Cent/kWh) als grobe Orientierung.

- Im heutigen Text nicht mehr vorhanden: 11,93 Cent

## `2026-09-21-grundversorgung-strom-und-gas-was-sie-leistet`

- Offene Live-Befunde: **2**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `68afba3e6a16a364ce45` | praezision | **neu** | kein Wert genannt (Aussage/Präzision) | Die Kündigungsfrist in der Grundversorgung ist gesetzlich exakt auf zwei Wochen festgelegt, was für den Leser eine wi… |
| `dc5ff05c5dda79d01373` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Es fehlt der Hinweis auf die gesetzliche Befristung der Ersatzversorgung auf maximal drei Monate, nach denen sie auto… |

### `68afba3e6a16a364ce45`

**Befund:** Die Kündigungsfrist in der Grundversorgung ist gesetzlich exakt auf zwei Wochen festgelegt, was für den Leser eine wichtigere Information ist als die vage Bezeichnung 'kurze Fristen'.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `dc5ff05c5dda79d01373`

**Befund:** Es fehlt der Hinweis auf die gesetzliche Befristung der Ersatzversorgung auf maximal drei Monate, nach denen sie automatisch endet.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

## `2026-09-23-einlagensicherung-wie-viel-guthaben-geschuetzt-ist`

- Offene Live-Befunde: **1**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `5c096f87730532352820` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Gesetze nennen konkrete Auszahlungsfristen im Einlagensicherungsfall. |

### `5c096f87730532352820`

**Befund:** Gesetze nennen konkrete Auszahlungsfristen im Einlagensicherungsfall.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

## `2026-09-30-last-minute-urlaub-so-schnappst-du-dir-das-sommer-schnaepp`

- Offene Live-Befunde: **5**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `33278b9e7942ebfdbbac` | luecke | 2026-11-11 · 1. Entscheidung | 14 Tage in Zeile 16 gekennzeichnet | Definition des Begriffs „Last Minute“ (maximal 14 Tage zwischen Buchung und Abreise) wird mit dem Deutschen Reiseverb… |
| `6ad7358a9afcfef3babb` | praezision | 2026-11-11 · 1. Entscheidung | kein Wert genannt (Aussage/Präzision) | Angabe, dass Preisalarme keinen Tiefstpreis garantieren, wird nicht durch konkrete Zahlen oder Vergleichsstudien belegt. |
| `7c375a3e1a9bfab1468c` | luecke | 2026-11-11 · 1. Entscheidung | kein Wert genannt (Aussage/Präzision) | Hinweis auf § 651r BGB (Insolvenzsicherung bei Pauschalreisen) enthält keinen Verweis auf eine Rechtsquelle oder Verb… |
| `ea11d36614fa115503b4` | luecke | 2026-11-11 · 1. Entscheidung | 50 % in Zeile 12 ohne Kennzeichnung | Behauptung, dass Nachlässe von bis zu 50 % nur Einzelfälle sind, wird ohne Quellenangabe präsentiert. |
| `f7b1c869dd8e442eaf16` | praezision | 2026-11-11 · 1. Entscheidung | kein Wert genannt (Aussage/Präzision) | Aussage, dass der „beste Zeitpunkt zum Buchen“ ein Modellwert sei, bleibt vage und ohne messbare Daten oder Studien u… |

### `33278b9e7942ebfdbbac`

**Befund:** Definition des Begriffs „Last Minute“ (maximal 14 Tage zwischen Buchung und Abreise) wird mit dem Deutschen Reiseverband angegeben, jedoch fehlt ein Nachweis.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Die Definition ist an die Fundstelle gebunden: „Der Deutsche Reiseverband nennt höchstens 14 Tage zwischen Buchung und Abreise als Grenze. Das ZDF gibt diese Definition wieder“ – mit Link auf den ZDF-Ratgeber im selben Absatz; der frühere Zusatz „das ist ein Beispielwert“ ist entfernt.

- Heute in Zeile 16: 14 Tage – gekennzeichnet („modellwert“)

### `6ad7358a9afcfef3babb`

**Befund:** Angabe, dass Preisalarme keinen Tiefstpreis garantieren, wird nicht durch konkrete Zahlen oder Vergleichsstudien belegt.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Der Befund verlangt Messdaten für eine Einschränkung. Der Text behauptet keine Wirkung, er begrenzt sie: „Ein Preisalarm ist ein Hinweis, aber kein Beleg für den niedrigsten verfügbaren Preis“, in der Werkzeug-Tabelle „versprechen keinen Tiefstpreis“. Eine Wirkungsstudie ist für diese Grenze nicht zu führen; Befund abgelehnt.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `7c375a3e1a9bfab1468c`

**Befund:** Hinweis auf § 651r BGB (Insolvenzsicherung bei Pauschalreisen) enthält keinen Verweis auf eine Rechtsquelle oder Verbraucherzentrale‑Information.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Trifft nicht zu: Der Artikel verlinkt den Gesetzestext direkt am Satz – „§ 651r BGB regelt den Sicherungsschein … ([Gesetzestext](https://www.gesetze-im-internet.de/bgb/__651r.html))“ – und führt dieselbe URL in den Quellen.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `ea11d36614fa115503b4`

**Befund:** Behauptung, dass Nachlässe von bis zu 50 % nur Einzelfälle sind, wird ohne Quellenangabe präsentiert.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Die Passage ist an die Fundstelle gebunden und ohne Zahlenversprechen: „Nachlässe von bis zu 50 % sind Einzelfälle, keine verlässliche Erwartung“ mit Link auf die Einordnung zu Last-Minute-Angeboten. Die frühere Modellwert-Formulierung ist entfernt; der Befund trifft die heutige Fassung nicht mehr.

- Heute in Zeile 12: 50 % – **ohne** Kennzeichnung

### `f7b1c869dd8e442eaf16`

**Befund:** Aussage, dass der „beste Zeitpunkt zum Buchen“ ein Modellwert sei, bleibt vage und ohne messbare Daten oder Studien untermauert.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Die Aussage behauptet keinen Modellwert mehr: „Einen Termin, der für alle Reisen der günstigste ist, gibt es nicht – auch nicht drei Monate im Voraus.“ Die vage Prognose ist durch eine Negation ohne Zahlenanspruch ersetzt.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

## `2026-10-02-preiswert-surfen-so-findest-du-den-optimalen-dsl-anschluss`

- Offene Live-Befunde: **3**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `6b5921bdc76490587167` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Seit 2026 nutzen die großen Anbieter die Technik mit dem Namen Vectoring; das ist ein Modellwert. Sie senkt das Rausc… |
| `8436b91bdb63a6316979` | praezision | **neu** | 12 Monate in Zeile 12 ohne Kennzeichnung · 10 % in Zeile 41 ohne Kennzeichnung | Preisgarantie über mindestens 12 Monate; ohne Garantie darf der Anbieter bald erhöhen, oft um bis zu 10 %. |
| `a4ff01e649b789f19e6a` | luecke | **neu** | 40 € in Zeile 60 gekennzeichnet | Für 50 Mbps zahlst du heute meist ca. 20–40 € im Monat; das ist ein Beispielwert. |

### `6b5921bdc76490587167`

**Befund:** Seit 2026 nutzen die großen Anbieter die Technik mit dem Namen Vectoring; das ist ein Modellwert. Sie senkt das Rauschen auf der Leitung. In der Stadt sind damit bis zu 250 Mbps stabil drin.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `8436b91bdb63a6316979`

**Befund:** Preisgarantie über mindestens 12 Monate; ohne Garantie darf der Anbieter bald erhöhen, oft um bis zu 10 %.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Heute in Zeile 12: 12 Monate – **ohne** Kennzeichnung
- Heute in Zeile 41: 10 % – **ohne** Kennzeichnung

### `a4ff01e649b789f19e6a`

**Befund:** Für 50 Mbps zahlst du heute meist ca. 20–40 € im Monat; das ist ein Beispielwert.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Heute in Zeile 60: 40 € – gekennzeichnet („beispielwert“)

## `2026-10-02-weihnachten-budget-planen-ohne-schulden-durch-die-feiertage`

- Offene Live-Befunde: **3**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `58f03a64adaaf8125959` | praezision | 2026-11-11 · 2. Entscheidung | 0,4 % in Zeile 61 gekennzeichnet | Während der Artikel vor hohen Kosten für Festmenüs warnt, liegt die Preissteigerung bei Nahrungsmitteln laut Destatis… |
| `a7f5f01ef15a38839a0d` | praezision | 2026-11-11 · 2. Entscheidung | 10 % in Zeile 28 ohne Kennzeichnung · 14,9 % in Zeile 61 gekennzeichnet | Die Pauschale für 'Anreise und Mobilität' (10 % des Budgets) berücksichtigt nicht die überdurchschnittliche Preisstei… |
| `bcc2bdf06220d5097133` | luecke | 2026-11-11 · 2. Entscheidung | 600 € in Zeile 61 gekennzeichnet · 2,8 % in Zeile 61 gekennzeichnet | Die Modellrechnung für das Weihnachtsbudget (600 €) lässt die aktuelle Teuerungsrate unberücksichtigt. Laut Statistis… |

### `58f03a64adaaf8125959`

**Befund:** Während der Artikel vor hohen Kosten für Festmenüs warnt, liegt die Preissteigerung bei Nahrungsmitteln laut Destatis im Oktober 2026 bei lediglich +0,4 % und damit deutlich unter der allgemeinen Inflation.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Am heutigen Text geprüft (SHA-256 7f8e2a19d909): Die verlangte Quelle steht im Abschnitt „Welche Modellrechnung zeigt dir die passende Wochenrate?“ inline – „Zur Einordnung der Preise: Die Inflation lag im Oktober 2026 bei +2,8 %, Nahrungsmittel verteuerten sich mit +0,4 % deutlich schwächer, Energie dagegen mit +14,9 % stark ([Destatis“. Der Befund trifft die heutige Fassung damit nicht mehr.

- Heute in Zeile 61: 0,4 % – gekennzeichnet („modellrechnung“)

### `a7f5f01ef15a38839a0d`

**Befund:** Die Pauschale für 'Anreise und Mobilität' (10 % des Budgets) berücksichtigt nicht die überdurchschnittliche Preissteigerung bei Energie von +14,9 %, die Fahrtkosten im Vergleich zum Vorjahr massiv verteuern kann.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Am heutigen Text geprüft (SHA-256 7f8e2a19d909): Die verlangte Quelle steht im Abschnitt „Welche Modellrechnung zeigt dir die passende Wochenrate?“ inline – „Zur Einordnung der Preise: Die Inflation lag im Oktober 2026 bei +2,8 %, Nahrungsmittel verteuerten sich mit +0,4 % deutlich schwächer, Energie dagegen mit +14,9 % stark ([Destatis“. Der Befund trifft die heutige Fassung damit nicht mehr.

- Heute in Zeile 28: 10 % – **ohne** Kennzeichnung
- Heute in Zeile 61: 14,9 % – gekennzeichnet („modellrechnung“)

### `bcc2bdf06220d5097133`

**Befund:** Die Modellrechnung für das Weihnachtsbudget (600 €) lässt die aktuelle Teuerungsrate unberücksichtigt. Laut Statistischen Bundesamt liegt die Inflationsrate im Oktober 2026 bei +2,8 %, was als Referenzwert für die Budgetplanung zum Vorjahr fehlt.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Am heutigen Text geprüft (SHA-256 7f8e2a19d909): Die verlangte Quelle steht im Abschnitt „Welche Modellrechnung zeigt dir die passende Wochenrate?“ inline – „Zur Einordnung der Preise: Die Inflation lag im Oktober 2026 bei +2,8 %, Nahrungsmittel verteuerten sich mit +0,4 % deutlich schwächer, Energie dagegen mit +14,9 % stark ([Destatis“. Der Befund trifft die heutige Fassung damit nicht mehr.

- Heute in Zeile 61: 600 € – gekennzeichnet („modellrechnung“)
- Heute in Zeile 61: 2,8 % – gekennzeichnet („modellrechnung“)

## `2026-10-07-7-gewohnheiten-fuer-finanzielle-freiheit`

- Offene Live-Befunde: **3**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `25d6b9a720f981e8e9df` | praezision | **neu** | nicht mehr im Text: 0,4 % | Bei der Bewertung flexibler Kosten sollte die moderate Preisentwicklung bei Nahrungsmitteln (+0,4 %) den stark steige… |
| `3693b612533c24dcd1ea` | luecke | **neu** | nicht mehr im Text: 12,2 % | Der Ratgeber empfiehlt die Prüfung von Stromverträgen, vernachlässigt aber den massiven Preistrend bei Energie von +1… |
| `c877eeff8842942c0071` | praezision | **neu** | 2,8 % in Zeile 108 ohne Kennzeichnung | Die allgemeine Budget-Transparenz ist ohne Einbezug der Inflationsrate von 2,8 % unvollständig, da Preissteigerungen… |

### `25d6b9a720f981e8e9df`

**Befund:** Bei der Bewertung flexibler Kosten sollte die moderate Preisentwicklung bei Nahrungsmitteln (+0,4 %) den stark steigenden Energiekosten gegenübergestellt werden, um Sparpotenziale zu priorisieren.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Im heutigen Text nicht mehr vorhanden: 0,4 %

### `3693b612533c24dcd1ea`

**Befund:** Der Ratgeber empfiehlt die Prüfung von Stromverträgen, vernachlässigt aber den massiven Preistrend bei Energie von +12,2 %, der die Kalkulation der Fixkosten aktuell dominiert.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Im heutigen Text nicht mehr vorhanden: 12,2 %

### `c877eeff8842942c0071`

**Befund:** Die allgemeine Budget-Transparenz ist ohne Einbezug der Inflationsrate von 2,8 % unvollständig, da Preissteigerungen die Planungssicherheit der 'festen Kosten' kontinuierlich untergraben.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Heute in Zeile 108: 2,8 % – **ohne** Kennzeichnung

## `2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust`

- Offene Live-Befunde: **3**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `089b89138417e63a3dcf` | luecke | 2026-11-11 · 4. Entscheidung | kein Wert genannt (Aussage/Präzision) | Es fehlt der für Campingbuchungen relevante Regulierungsrahmen (Unterscheidung Mietrecht bei Stellplätzen vs. Reisere… |
| `1158934e7a18c7b2099b` | luecke | 2026-11-11 · 4. Entscheidung | nicht mehr im Text: 45 € | Die Preisangabe von 20 bis 45 € pro Nacht wird als realistischer Wert positioniert, ist jedoch nicht durch Marktdaten… |
| `3716cfd3ab5aec6d774b` | praezision | 2026-11-11 · 4. Entscheidung | kein Wert genannt (Aussage/Präzision) | Der Verweis auf die Verbraucherzentrale zur Prüfung von Buchungsangaben führt auf eine allgemeine Übersichtsseite ohn… |

### `089b89138417e63a3dcf`

**Befund:** Es fehlt der für Campingbuchungen relevante Regulierungsrahmen (Unterscheidung Mietrecht bei Stellplätzen vs. Reiserecht), den die Fundstelle für den Bereich Reise nur allgemein andeutet.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Der Rahmen ist unterschieden: „Eine einzelne Stellplatzbuchung ist nicht automatisch eine Pauschalreise. Ob Mietrecht, ein anderer Vertrag oder Pauschalreiserecht relevant ist, hängt von den konkret gebuchten Leistungen und dem Vertrag ab.“ Die pauschale Mietrechtszuordnung ist weg.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `1158934e7a18c7b2099b`

**Befund:** Die Preisangabe von 20 bis 45 € pro Nacht wird als realistischer Wert positioniert, ist jedoch nicht durch Marktdaten oder eine Referenzstelle in den Fundstellen belegt.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Die Spanne 20–45 € pro Nacht steht nicht mehr im Artikel. Der Platzpreis ist heute eine offene Modellrechnung: „Angenommen, ein Stellplatz kostet 31 € je Nacht … Der Betrag ist frei gewählt und kein Durchschnittspreis.“

- Im heutigen Text nicht mehr vorhanden: 45 €

### `3716cfd3ab5aec6d774b`

**Befund:** Der Verweis auf die Verbraucherzentrale zur Prüfung von Buchungsangaben führt auf eine allgemeine Übersichtsseite ohne konkrete Checklisten für Camping-Angebote.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Am heutigen Text geprüft (SHA-256 aaf1b8fc6568): Die verlangte Quelle steht im Abschnitt „Welche Kosten gehören in ein Campingbudget?“ inline – „Die Verbraucherzentrale erklärt in ihrem Ratgeber [Online-Reisebüros](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet/urlaub-buchen/onlinereisebueros-so-vermeiden-sie-pr“. Der Befund trifft die heutige Fassung damit nicht mehr.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

## `2026-10-07-handyvertrag-kuendigen-raus-aus-der-kostenfalle-verlaengerung`

- Offene Live-Befunde: **2**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `26b1c694d76bcc7af50f` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Der Ratgeber versäumt es, den für den Verbraucherschutz zentralen Regulierungsrahmen der 'Unternehmenspflichten' zu n… |
| `9593e535bce55f4283e6` | praezision | **neu** | kein Wert genannt (Aussage/Präzision) | Die Empfehlung zum Preisvergleich lässt den aktuellen Marktdruck (sinkende Umsätze bei O2) außer Acht, der für die Ve… |

### `26b1c694d76bcc7af50f`

**Befund:** Der Ratgeber versäumt es, den für den Verbraucherschutz zentralen Regulierungsrahmen der 'Unternehmenspflichten' zu nennen, den die Bundesnetzagentur explizit als Fachthema führt.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `9593e535bce55f4283e6`

**Befund:** Die Empfehlung zum Preisvergleich lässt den aktuellen Marktdruck (sinkende Umsätze bei O2) außer Acht, der für die Verhandlung von Rückholangeboten bei Kündigung entscheidend sein kann.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

## `2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen`

- Offene Live-Befunde: **5**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `7067eabb89a917ae67a4` | luecke | 2026-11-11 · 2. Entscheidung | kein Wert genannt (Aussage/Präzision) | Die Verbraucherzentrale sammelt Hinweise zu Reisebuchungen, auch zu unklaren Angeboten und Problemen mit Online-Buchu… |
| `af2ccb4222eeb195222f` | praezision | 2026-11-11 · 2. Entscheidung | kein Wert genannt (Aussage/Präzision) | Ein Mietwagenvergleich kann Angebote sichtbar machen, prüft aber nicht automatisch, ob das Auto zum individuellen Url… |
| `d9c8b522bf1dcaed0340` | luecke | 2026-11-11 · 2. Entscheidung | kein Wert genannt (Aussage/Präzision) | Die Verbraucherzentrale beschreibt, dass sich eine Pauschalreise unter bestimmten Bedingungen auf eine andere Person… |
| `e2975509f3f130de0755` | luecke | 2026-11-11 · 2. Entscheidung | kein Wert genannt (Aussage/Präzision) | Die Verbraucherzentrale empfiehlt, größere Ausgaben vorauszuplanen und das eigene Budget im Blick zu behalten. |
| `f1704e45e970a8f4b078` | luecke | 2026-11-11 · 2. Entscheidung | kein Wert genannt (Aussage/Präzision) | Bei einer Pauschalreise gilt die Mitteilung als rechtzeitig, wenn sie dem Veranstalter spätestens sieben Tage vor Rei… |

### `7067eabb89a917ae67a4`

**Befund:** Die Verbraucherzentrale sammelt Hinweise zu Reisebuchungen, auch zu unklaren Angeboten und Problemen mit Online-Buchungen.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Am heutigen Text geprüft (SHA-256 de2780e91953): Die verlangte Quelle steht im Abschnitt „Wie setzt du ein realistisches Reisebudget?“ inline – „Die Verbraucherzentrale sammelt [Hinweise zu Reisebuchungen und Problemen mit Online-Buchungen](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet/urlaub-buchen), wenn ein “. Der Befund trifft die heutige Fassung damit nicht mehr.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `af2ccb4222eeb195222f`

**Befund:** Ein Mietwagenvergleich kann Angebote sichtbar machen, prüft aber nicht automatisch, ob das Auto zum individuellen Urlaub passt – ohne Messgröße bleibt die Aussage ungenau.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Am heutigen Text geprüft (SHA-256 de2780e91953): Die verlangte Quelle steht im Abschnitt „Wie setzt du ein realistisches Reisebudget?“ inline – „Die Verbraucherzentrale sammelt [Hinweise zu Reisebuchungen und Problemen mit Online-Buchungen](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet/urlaub-buchen), wenn ein “. Der Befund trifft die heutige Fassung damit nicht mehr.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `d9c8b522bf1dcaed0340`

**Befund:** Die Verbraucherzentrale beschreibt, dass sich eine Pauschalreise unter bestimmten Bedingungen auf eine andere Person übertragen lässt.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Am heutigen Text geprüft (SHA-256 de2780e91953): Die verlangte Quelle steht im Abschnitt „Wie setzt du ein realistisches Reisebudget?“ inline – „Die Verbraucherzentrale sammelt [Hinweise zu Reisebuchungen und Problemen mit Online-Buchungen](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet/urlaub-buchen), wenn ein “. Der Befund trifft die heutige Fassung damit nicht mehr.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `e2975509f3f130de0755`

**Befund:** Die Verbraucherzentrale empfiehlt, größere Ausgaben vorauszuplanen und das eigene Budget im Blick zu behalten.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Am heutigen Text geprüft (SHA-256 de2780e91953): Die verlangte Quelle steht im Abschnitt „Wie setzt du ein realistisches Reisebudget?“ inline – „Die Verbraucherzentrale sammelt [Hinweise zu Reisebuchungen und Problemen mit Online-Buchungen](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet/urlaub-buchen), wenn ein “. Der Befund trifft die heutige Fassung damit nicht mehr.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `f1704e45e970a8f4b078`

**Befund:** Bei einer Pauschalreise gilt die Mitteilung als rechtzeitig, wenn sie dem Veranstalter spätestens sieben Tage vor Reisebeginn zugeht (§ 651e BGB).

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Am heutigen Text geprüft (SHA-256 de2780e91953): Die verlangte Quelle steht im Abschnitt „Wie setzt du ein realistisches Reisebudget?“ inline – „Die Verbraucherzentrale sammelt [Hinweise zu Reisebuchungen und Problemen mit Online-Buchungen](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet/urlaub-buchen), wenn ein “. Der Befund trifft die heutige Fassung damit nicht mehr.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

## `2026-10-07-wie-smart-home-geraete-deine-stromrechnung-wirklich-druecken`

- Offene Live-Befunde: **1**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `a10511ed618384aa7b88` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Der Artikel nennt keine regulatorischen Vorgaben oder Zertifizierungen (z. B. CE‑Kennzeichnung, Sicherheitsanforderun… |

### `a10511ed618384aa7b88`

**Befund:** Der Artikel nennt keine regulatorischen Vorgaben oder Zertifizierungen (z. B. CE‑Kennzeichnung, Sicherheitsanforderungen) für Smart‑Home‑Geräte, obwohl solche Vorgaben von der Bundesnetzagentur beschrieben werden.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

## `2026-10-09-balkonkraftwerk-foerderung-so-holst-du-dir-geld-zurueck`

- Offene Live-Befunde: **2**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `a74029dd4e284794d697` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Eine separate Meldung beim Netzbetreiber ist im Standardfall nicht mehr nötig. |
| `c45ea4bb1a6f2330679a` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Keine bundesweite Zuschusspflicht: Zuschüsse kommen, wenn überhaupt, von Städten, Gemeinden oder Ländern. |

### `a74029dd4e284794d697`

**Befund:** Eine separate Meldung beim Netzbetreiber ist im Standardfall nicht mehr nötig.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `c45ea4bb1a6f2330679a`

**Befund:** Keine bundesweite Zuschusspflicht: Zuschüsse kommen, wenn überhaupt, von Städten, Gemeinden oder Ländern.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

## `2026-10-09-energiekosten-senken-smarte-helfer-fuer-den-haushalt`

- Offene Live-Befunde: **3**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `4d0125136c5b940946e4` | luecke | **neu** | 5 % in Zeile 12 gekennzeichnet | Lichtsteuerung: Bedarfssteuerung – 2 bis 5 % des Stromverbrauchs. |
| `7aeb2098034d16a46885` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Anbieter locken mit Neukundenboni, die nach der üblichen Erstlaufzeit entfallen; danach steigt der Arbeitspreis massi… |
| `ea97b5dd6695de127fd2` | luecke | **neu** | 25 % in Zeile 12 gekennzeichnet | Heizungssteuerung: Smarte Thermostate können Heizkosten einsparen. Die Spanne von 10 bis 25 % ist ein Beispielwert au… |

### `4d0125136c5b940946e4`

**Befund:** Lichtsteuerung: Bedarfssteuerung – 2 bis 5 % des Stromverbrauchs.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Heute in Zeile 12: 5 % – gekennzeichnet („beispielwert“)

### `7aeb2098034d16a46885`

**Befund:** Anbieter locken mit Neukundenboni, die nach der üblichen Erstlaufzeit entfallen; danach steigt der Arbeitspreis massiv an.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `ea97b5dd6695de127fd2`

**Befund:** Heizungssteuerung: Smarte Thermostate können Heizkosten einsparen. Die Spanne von 10 bis 25 % ist ein Beispielwert aus der Rechnung unten.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Heute in Zeile 12: 25 % – gekennzeichnet („beispielwert“)

## `2026-10-12-dein-weg-zu-geringeren-monatskosten-schritt-fuer-schritt`

- Offene Live-Befunde: **2**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `7c2624072c861d136c96` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Die pauschale Behauptung zu Preisunterschieden zwischen Standardtarifen und Angeboten ist ein Marktdatum ohne Beleg o… |
| `d9d3004fbc05895c3f79` | praezision | **neu** | nicht mehr im Text: 12,7 % | Die Aussage zum steigenden Strompreis ist unpräzise; die Quelle belegt einen konkreten Anstieg der Energiepreise um +… |

### `7c2624072c861d136c96`

**Befund:** Die pauschale Behauptung zu Preisunterschieden zwischen Standardtarifen und Angeboten ist ein Marktdatum ohne Beleg oder eigene Messung (Regel 9a/9e).

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `d9d3004fbc05895c3f79`

**Befund:** Die Aussage zum steigenden Strompreis ist unpräzise; die Quelle belegt einen konkreten Anstieg der Energiepreise um +12,7 %.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Im heutigen Text nicht mehr vorhanden: 12,7 %

## `2026-10-12-energieausweis-was-das-dokument-fuer-deine-fixkosten`

- Offene Live-Befunde: **4**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `1dc0f20f9ab3a6b783bc` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Behauptung, dass ein fehlender Ausweis zu empfindlichen Bußgeldern führt, fehlt eine belegbare Quelle. |
| `7b94ca07b36c0b7cb1cc` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Aussage, dass Baudenkmäler von der Ausweispflicht befreit sind, wird nicht durch die angegebene Quelle gestützt. |
| `985f506ee04087bf7253` | luecke | **neu** | nicht mehr im Text: 2.000 € | Angabe, dass ein Wechsel von Energieeffizienzklasse F zu C über 2.000 € Jahresersparnis bringt, ist unbelegt. |
| `ee321fa37210590f7e9b` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Keine Quelle für die Angabe, dass ein Energieausweis ein volles Jahrzehnt gültig ist, sofern keine größeren Umbauten… |

### `1dc0f20f9ab3a6b783bc`

**Befund:** Behauptung, dass ein fehlender Ausweis zu empfindlichen Bußgeldern führt, fehlt eine belegbare Quelle.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `7b94ca07b36c0b7cb1cc`

**Befund:** Aussage, dass Baudenkmäler von der Ausweispflicht befreit sind, wird nicht durch die angegebene Quelle gestützt.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `985f506ee04087bf7253`

**Befund:** Angabe, dass ein Wechsel von Energieeffizienzklasse F zu C über 2.000 € Jahresersparnis bringt, ist unbelegt.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Im heutigen Text nicht mehr vorhanden: 2.000 €

### `ee321fa37210590f7e9b`

**Befund:** Keine Quelle für die Angabe, dass ein Energieausweis ein volles Jahrzehnt gültig ist, sofern keine größeren Umbauten erfolgen.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

## `2026-10-12-kleine-energiespar-tricks-die-deine-kosten-sofort-senken`

- Offene Live-Befunde: **5**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `19ab248b17415c73edfb` | luecke | **neu** | 4 % in Zeile 9 ohne Kennzeichnung · 6 % in Zeile 5 ohne Kennzeichnung | Thermostat um 1 °C senken \| 4 % – 6 % der Heizkosten |
| `372bb51051e8bd7c5f71` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Viele Anbieter belohnen einen niedrigen Verbrauch mit besseren Konditionen |
| `6aaff85e3a7591d0c5b2` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | für dich entstehen keine Mehrkosten |
| `7e6087a4117a857a92c8` | luecke | **neu** | 140 € in Zeile 34 ohne Kennzeichnung | Durch diese zwei Maßnahmen sparst du in dieser Beispielrechnung jährlich rund 140 € |
| `e28b4ad1f6d608d2ec77` | luecke | **neu** | 100 € in Zeile 34 ohne Kennzeichnung · 140 € in Zeile 34 ohne Kennzeichnung · 8 % in Zeile 34 ohne Kennzeichnung | Strom (LED‑Umrüstung) \| 100 € – 140 € \| etwa 8 % |

### `19ab248b17415c73edfb`

**Befund:** Thermostat um 1 °C senken | 4 % – 6 % der Heizkosten

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Heute in Zeile 9: 4 % – **ohne** Kennzeichnung
- Heute in Zeile 5: 6 % – **ohne** Kennzeichnung

### `372bb51051e8bd7c5f71`

**Befund:** Viele Anbieter belohnen einen niedrigen Verbrauch mit besseren Konditionen

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `6aaff85e3a7591d0c5b2`

**Befund:** für dich entstehen keine Mehrkosten

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `7e6087a4117a857a92c8`

**Befund:** Durch diese zwei Maßnahmen sparst du in dieser Beispielrechnung jährlich rund 140 €

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Heute in Zeile 34: 140 € – **ohne** Kennzeichnung

### `e28b4ad1f6d608d2ec77`

**Befund:** Strom (LED‑Umrüstung) | 100 € – 140 € | etwa 8 %

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Heute in Zeile 34: 100 € – **ohne** Kennzeichnung
- Heute in Zeile 34: 140 € – **ohne** Kennzeichnung
- Heute in Zeile 34: 8 % – **ohne** Kennzeichnung

## `2026-10-12-waermepumpe-vs-gasheizung-2026-so-entscheidest-du-richtig`

- Offene Live-Befunde: **5**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `34e4bb2acfa235699da5` | luecke | 2026-11-04 · 1. Entscheidung | kein Wert genannt (Aussage/Präzision) | Der Artikel erwähnt keinen regulatorischen Rahmen (z. B. Bundesnetzagentur) obwohl diese Institution für Strom‑ und G… |
| `42b9d842341d892d42d0` | luecke | 2026-11-04 · 1. Entscheidung | 70 % in Zeile 11 gekennzeichnet | Angaben zu staatlichen Zuschüssen (bis zu 70 %) und deren Auswirkung auf den Eigenanteil fehlen eine Quellenangabe. |
| `866d8b711dc2de369444` | luecke | 2026-11-04 · 1. Entscheidung | kein Wert genannt (Aussage/Präzision) | Hinweis, dass ein spezieller Stromtarif für Wärmepumpen die Kosten senkt, wird nicht durch eine Quelle belegt. |
| `bd4c46a336f33a639f05` | luecke | 2026-11-04 · 1. Entscheidung | kein Wert genannt (Aussage/Präzision) | Preisannahmen für Strom (30 ¢/kWh), Gas (10 ¢/kWh) und CO₂‑Aufschlag (5 ¢/kWh) werden ohne belegbare Daten präsentiert. |
| `e76768fdef3ef5afa026` | luecke | 2026-11-04 · 1. Entscheidung | 12 Jahre in Zeile 12 ohne Kennzeichnung | Die behauptete Amortisationsdauer von 10‑12 Jahren für eine Wärmepumpe basiert auf einer Modellrechnung ohne nachweis… |

### `34e4bb2acfa235699da5`

**Befund:** Der Artikel erwähnt keinen regulatorischen Rahmen (z. B. Bundesnetzagentur) obwohl diese Institution für Strom‑ und Gasmärkte zuständig ist.

**Frühere Entscheidung (2026-11-04):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 04.11.2026)

> Preisannahmen als Modellrechnung mit Annahmen gekennzeichnet; Förderhinweis (bis 70 %) mit Quellenangabe versehen; Wärmepumpen-Tarif relativiert; Regulierungsrahmen Bundesnetzagentur erwähnt.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `42b9d842341d892d42d0`

**Befund:** Angaben zu staatlichen Zuschüssen (bis zu 70 %) und deren Auswirkung auf den Eigenanteil fehlen eine Quellenangabe.

**Frühere Entscheidung (2026-11-04):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 04.11.2026)

> Preisannahmen als Modellrechnung mit Annahmen gekennzeichnet; Förderhinweis (bis 70 %) mit Quellenangabe versehen; Wärmepumpen-Tarif relativiert; Regulierungsrahmen Bundesnetzagentur erwähnt.

- Heute in Zeile 11: 70 % – gekennzeichnet („beispielrechnung“)

### `866d8b711dc2de369444`

**Befund:** Hinweis, dass ein spezieller Stromtarif für Wärmepumpen die Kosten senkt, wird nicht durch eine Quelle belegt.

**Frühere Entscheidung (2026-11-04):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 04.11.2026)

> Preisannahmen als Modellrechnung mit Annahmen gekennzeichnet; Förderhinweis (bis 70 %) mit Quellenangabe versehen; Wärmepumpen-Tarif relativiert; Regulierungsrahmen Bundesnetzagentur erwähnt.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `bd4c46a336f33a639f05`

**Befund:** Preisannahmen für Strom (30 ¢/kWh), Gas (10 ¢/kWh) und CO₂‑Aufschlag (5 ¢/kWh) werden ohne belegbare Daten präsentiert.

**Frühere Entscheidung (2026-11-04):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 04.11.2026)

> Preisannahmen als Modellrechnung mit Annahmen gekennzeichnet; Förderhinweis (bis 70 %) mit Quellenangabe versehen; Wärmepumpen-Tarif relativiert; Regulierungsrahmen Bundesnetzagentur erwähnt.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `e76768fdef3ef5afa026`

**Befund:** Die behauptete Amortisationsdauer von 10‑12 Jahren für eine Wärmepumpe basiert auf einer Modellrechnung ohne nachweisbare Quelle.

**Frühere Entscheidung (2026-11-04):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 04.11.2026)

> Preisannahmen als Modellrechnung mit Annahmen gekennzeichnet; Förderhinweis (bis 70 %) mit Quellenangabe versehen; Wärmepumpen-Tarif relativiert; Regulierungsrahmen Bundesnetzagentur erwähnt.

- Heute in Zeile 12: 12 Jahre – **ohne** Kennzeichnung

## `2026-10-23-stromkosten-senken-clevere-haushaltsgeraete-im-ueberblick`

- Offene Live-Befunde: **5**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `1eae5c7e2bbd95a3362c` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Tabelle mit konkreten kWh‑Werten und Euro‑Ersparnissen für neue vs. alte Geräte. |
| `8547ce3daa75aabb30d4` | luecke | **neu** | 40 ct in Zeile 9 gekennzeichnet · 52 € in Zeile 74 gekennzeichnet | Annahme von 40 ct/kWh und daraus resultierende Jahres‑Ersparnis von 52 € für einen Kühlschrank‑Tausch. |
| `c8b197692bd0023c87bf` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Behauptung, dass ein neuer Wärmepumpentrockner „sogar noch schneller“ die Anschaffungskosten amortisiert. |
| `e40a2ee5c7baa5f8567b` | luecke | **neu** | 40 % in Zeile 9 gekennzeichnet | Sparsame Geräte senken deinen Verbrauch in der Beispielrechnung unten um bis zu 40 %. |
| `feb71513c6fb7064dc92` | luecke | **neu** | 30 % in Zeile 10 gekennzeichnet | Der Stromverbrauch von Kühlschrank und Waschmaschine macht in der Modellrechnung rund 30 % der Kosten im Haushalt aus. |

### `1eae5c7e2bbd95a3362c`

**Befund:** Tabelle mit konkreten kWh‑Werten und Euro‑Ersparnissen für neue vs. alte Geräte.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `8547ce3daa75aabb30d4`

**Befund:** Annahme von 40 ct/kWh und daraus resultierende Jahres‑Ersparnis von 52 € für einen Kühlschrank‑Tausch.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Heute in Zeile 9: 40 ct – gekennzeichnet („beispielrechnung“)
- Heute in Zeile 74: 52 € – gekennzeichnet („modellrechnung“)

### `c8b197692bd0023c87bf`

**Befund:** Behauptung, dass ein neuer Wärmepumpentrockner „sogar noch schneller“ die Anschaffungskosten amortisiert.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `e40a2ee5c7baa5f8567b`

**Befund:** Sparsame Geräte senken deinen Verbrauch in der Beispielrechnung unten um bis zu 40 %.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Heute in Zeile 9: 40 % – gekennzeichnet („beispielrechnung“)

### `feb71513c6fb7064dc92`

**Befund:** Der Stromverbrauch von Kühlschrank und Waschmaschine macht in der Modellrechnung rund 30 % der Kosten im Haushalt aus.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Heute in Zeile 10: 30 % – gekennzeichnet („modellrechnung“)

## `2026-10-24-bankgebuehren-senken-7-schritte-zum-guenstigeren-konto`

- Offene Live-Befunde: **4**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `04ae33652c1c5eb4e2b8` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Ein kurzer Check spart dir oft mehrere hundert Euro im Jahr. |
| `5223a3c7287ff81939cd` | luecke | **neu** | 5 % in Zeile 57 ohne Kennzeichnung · 80 % in Zeile 79 ohne Kennzeichnung | Faustregel: ... mehr als 5 % deines Nettoeinkommens ... Meist sinken diese Kosten um über 80 % |
| `9800545ae945ec280b34` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Ein Wechsel ist für dich in der Regel komplett kostenlos als Beispielwert. |
| `bc0e4f2eb357a682c674` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Bei einem normalen Einkommen sollten die Gebühren fast Null sein. |

### `04ae33652c1c5eb4e2b8`

**Befund:** Ein kurzer Check spart dir oft mehrere hundert Euro im Jahr.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `5223a3c7287ff81939cd`

**Befund:** Faustregel: ... mehr als 5 % deines Nettoeinkommens ... Meist sinken diese Kosten um über 80 %

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Heute in Zeile 57: 5 % – **ohne** Kennzeichnung
- Heute in Zeile 79: 80 % – **ohne** Kennzeichnung

### `9800545ae945ec280b34`

**Befund:** Ein Wechsel ist für dich in der Regel komplett kostenlos als Beispielwert.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `bc0e4f2eb357a682c674`

**Befund:** Bei einem normalen Einkommen sollten die Gebühren fast Null sein.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

## `2026-10-24-energieeffizienz-im-haushalt-5-schnelle-spartricks`

- Offene Live-Befunde: **3**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `0d1977a0b6a7b59136f2` | praezision | **neu** | kein Wert genannt (Aussage/Präzision) | Die Bezeichnung als 'beste Tarife' ist ein Superlativ ohne messbare Daten oder eigene Vergleichsmetrik. |
| `228ef205074fdc3fb4b3` | luecke | **neu** | 6 % in Zeile 21 ohne Kennzeichnung | Der Heiz-Faustwert (6 % Ersparnis pro Grad) fehlt in der angegebenen Quelle und ist nicht am Satz belegt. |
| `d7c301604b02d49e8d65` | luecke | **neu** | 30 % in Zeile 7 gekennzeichnet | Der behauptete Budgetanteil von 30 % für Energie ist ein spezifischer Marktwert, der in der angegebenen Quelle nicht… |

### `0d1977a0b6a7b59136f2`

**Befund:** Die Bezeichnung als 'beste Tarife' ist ein Superlativ ohne messbare Daten oder eigene Vergleichsmetrik.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `228ef205074fdc3fb4b3`

**Befund:** Der Heiz-Faustwert (6 % Ersparnis pro Grad) fehlt in der angegebenen Quelle und ist nicht am Satz belegt.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Heute in Zeile 21: 6 % – **ohne** Kennzeichnung

### `d7c301604b02d49e8d65`

**Befund:** Der behauptete Budgetanteil von 30 % für Energie ist ein spezifischer Marktwert, der in der angegebenen Quelle nicht vorkommt.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Heute in Zeile 7: 30 % – gekennzeichnet („beispielwert“)

## `2026-10-24-etf-sparplan-starten-schritt-fuer-schritt-zum-monatlichen`

- Offene Live-Befunde: **3**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `3bfeb0118af92a780a47` | luecke | **neu** | 5 % in Zeile 12 gekennzeichnet · 30.000 € in Zeile 12 gekennzeichnet | Bei 5 % Rendite im Jahr entstehen rund 30.000 € – keine Quelle für die angenommene Rendite angegeben. |
| `ed2161154dcee85da1ee` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Angabe, dass die Einrichtung eines Sparplans meist weniger als 15 Minuten dauert, fehlt belegt. |
| `f593fe21275bd9dcefef` | luecke | **neu** | 1 € in Zeile 13 ohne Kennzeichnung | Behauptung, dass einige Broker bereits ab 1 € monatlich starten, ohne Quelle. |

### `3bfeb0118af92a780a47`

**Befund:** Bei 5 % Rendite im Jahr entstehen rund 30.000 € – keine Quelle für die angenommene Rendite angegeben.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Heute in Zeile 12: 5 % – gekennzeichnet („beispielwert“)
- Heute in Zeile 12: 30.000 € – gekennzeichnet („beispielwert“)

### `ed2161154dcee85da1ee`

**Befund:** Angabe, dass die Einrichtung eines Sparplans meist weniger als 15 Minuten dauert, fehlt belegt.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `f593fe21275bd9dcefef`

**Befund:** Behauptung, dass einige Broker bereits ab 1 € monatlich starten, ohne Quelle.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

- Heute in Zeile 13: 1 € – **ohne** Kennzeichnung

## `2026-10-25-strategisch-sparen-so-kannst-du-deine-reisekasse-fuellen`

- Offene Live-Befunde: **3**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `98eb45f772ad7a0aac7b` | luecke | 2026-11-11 · 1. Entscheidung | 500 € in Zeile 69 gekennzeichnet · 120 € in Zeile 28 gekennzeichnet · 80 € in Zeile 27 gekennzeichnet | Das Sparversprechen von '500 € mehr' in der PIN-Beschreibung nutzt im Text Referenzwerte (120 € Strom, 80 € Kfz), für… |
| `b7f0d52968d89cdf8c5b` | praezision | 2026-11-11 · 1. Entscheidung | kein Wert genannt (Aussage/Präzision) | Die Einschätzung zur Datensicherheit von Cashback-Apps bleibt ohne Nennung konkreter rechtlicher Grundlagen (DSGVO) u… |
| `be911855d67f998be662` | luecke | 2026-11-11 · 1. Entscheidung | kein Wert genannt (Aussage/Präzision) | Der Ratgeber nennt keinen Regulierungsrahmen für Reisebuchungen (z. B. Fluggastrechte oder Stornierungsregeln), obwoh… |

### `98eb45f772ad7a0aac7b`

**Befund:** Das Sparversprechen von '500 € mehr' in der PIN-Beschreibung nutzt im Text Referenzwerte (120 € Strom, 80 € Kfz), für die in der Quelle keine Marktdaten oder Durchschnittswerte als Beleg vorliegen.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Am heutigen Text geprüft (SHA-256 f5cf5ca16db6): Die Zahl steht weiterhin im Artikel, ist aber ausdrücklich als Modell-/Beispielwert gekennzeichnet: „**Beispielrechnung:** Die angenommenen Einsparungen betragen 120 € im Jahr für Strom, 25 € pro Monat für ungenutzte Abos und 80 € im Jahr für die Kfz‑Versicherung, insgesamt 500 € nach zwölf“. Beanstandet war die Zahl OHNE Kennzeichnung; das trifft nicht mehr zu.

- Heute in Zeile 69: 500 € – gekennzeichnet („modellrechnung“)
- Heute in Zeile 28: 120 € – gekennzeichnet („modellrechnung“)
- Heute in Zeile 27: 80 € – gekennzeichnet („modellrechnung“)

### `b7f0d52968d89cdf8c5b`

**Befund:** Die Einschätzung zur Datensicherheit von Cashback-Apps bleibt ohne Nennung konkreter rechtlicher Grundlagen (DSGVO) unpräzise, während die Quelle explizit auf rechtliche Verbraucherthemen fokussiert.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Die rechtliche Grundlage ist jetzt benannt: „Nach der DSGVO muss der Anbieter Zweck und Rechtsgrundlage der Verarbeitung nennen und dir Auskunft und Löschung deiner Daten ermöglichen.“ Der Befund (kein rechtlicher Rahmen) ist damit erledigt.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `be911855d67f998be662`

**Befund:** Der Ratgeber nennt keinen Regulierungsrahmen für Reisebuchungen (z. B. Fluggastrechte oder Stornierungsregeln), obwohl die Quelle diese als zentrale Informationsbereiche ausweist.

**Frühere Entscheidung (2026-11-11):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 11.11.2026)

> Der Rahmen steht jetzt im Artikel: „Bei Pauschalreisen gilt das Pauschalreiserecht mit Storno- und Insolvenzregeln (§§ 651a ff. BGB), bei Flügen die EU-Fluggastrechte-Verordnung 261/2004.“

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

## `2026-10-28-flugvergleich-im-winter-so-findest-du-echte-billigfluege`

- Offene Live-Befunde: **4**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `381dd90113dd1ee72f39` | praezision | **neu** | kein Wert genannt (Aussage/Präzision) | Das Versprechen, 'alle Gebühren' auf Portalen zu sehen, ist ohne Messgröße unpräzise, da Portale systembedingt nur ei… |
| `4483a81dd1c292034cd0` | praezision | **neu** | kein Wert genannt (Aussage/Präzision) | Die Warnung vor einer 'sehr hohen Strafgebühr' am Gate ist ein Superlativ ohne messbare Daten oder konkrete Preisbeis… |
| `6f4b591e9cadb27adf49` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Bei der Erwähnung von Stornierungen durch Airlines fehlt der Hinweis auf den rechtlichen Rahmen (z. B. EU-Fluggastrec… |
| `cf60024b74a5e86b50c0` | luecke | **neu** | kein Wert genannt (Aussage/Präzision) | Die statistische Aussage zur Preisgünstigkeit von Dienstag und Mittwoch ist eine Marktprognose ohne Beleg in der gena… |

### `381dd90113dd1ee72f39`

**Befund:** Das Versprechen, 'alle Gebühren' auf Portalen zu sehen, ist ohne Messgröße unpräzise, da Portale systembedingt nur eine Marktauswahl zeigen.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `4483a81dd1c292034cd0`

**Befund:** Die Warnung vor einer 'sehr hohen Strafgebühr' am Gate ist ein Superlativ ohne messbare Daten oder konkrete Preisbeispiele.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `6f4b591e9cadb27adf49`

**Befund:** Bei der Erwähnung von Stornierungen durch Airlines fehlt der Hinweis auf den rechtlichen Rahmen (z. B. EU-Fluggastrechte).

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `cf60024b74a5e86b50c0`

**Befund:** Die statistische Aussage zur Preisgünstigkeit von Dienstag und Mittwoch ist eine Marktprognose ohne Beleg in der genannten Quelle.

**Frühere Entscheidung:** keine – dieser Befund ist neu.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

## `2026-11-05-waschmaschine-beladen-weniger-kosten-bei-jedem-waschgang`

- Offene Live-Befunde: **5**

| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |
|---|---|---|---|---|
| `4284fd2d9c9005e7af8f` | praezision | 2026-11-12 · 3. Entscheidung | kein Wert genannt (Aussage/Präzision) | Behauptung, dass Überladung der Maschine zu schnellerem Verschleiß und teuren Reparaturen führt, wird ohne konkrete D… |
| `84e247f17354e224c973` | praezision | 2026-11-12 · 3. Entscheidung | kein Wert genannt (Aussage/Präzision) | Aussage, dass das richtige Beladen allein die Fixkosten senkt, ohne weitere Maßnahmen, ist ein pauschales Leistungsve… |
| `a2a7dc69f10393af6531` | luecke | 2026-11-12 · 3. Entscheidung | nicht mehr im Text: 0,40 €, 0,005 € · 0,9 kWh in Zeile 20 gekennzeichnet · 0,6 kWh in Zeile 121 ohne Kennzeichnung · 22 € in Zeile 118 ohne Kennzeichnung | Die Modellrechnung (0,9 kWh/50 L bei vollem Waschgang, 0,6 kWh/35 L bei halbem Waschgang, Strompreis 0,40 €/kWh, Wass… |
| `cb794331f1cc0c715a55` | luecke | 2026-11-12 · 3. Entscheidung | 5 € in Zeile 20 gekennzeichnet | Die Aussage, dass bei 4 Waschgängen pro Woche ein durchschnittlicher Haushalt rund 5 € jährlich an Strom‑ und Wasserk… |
| `e6729081522126e972c2` | luecke | 2026-11-12 · 3. Entscheidung | nicht mehr im Text: 15 % · 80 % in Zeile 131 gekennzeichnet | Angabe, dass ein optimal beladener Trommel (ca. 80 % Kapazität) bis zu 15 % weniger Wasser und Energie verbraucht, wi… |

### `4284fd2d9c9005e7af8f`

**Befund:** Behauptung, dass Überladung der Maschine zu schnellerem Verschleiß und teuren Reparaturen führt, wird ohne konkrete Daten oder Messgröße angegeben.

**Frühere Entscheidung (2026-11-12):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 12.11.2026)

> Paket C, entschieden am 12.11.2026: Die Folgebehauptung „Überladung führt zu Verschleiß und teuren Reparaturen“ ist gestrichen. Sie stützte sich allein auf FORUM WASCHEN (ikw.org) – keine Domain der Allowlist, und die Kausalaussage war im Quellentext nicht belegt. Geblieben sind zwei belegbare Sätze: die Empfehlung, die Nennbeladung nicht zu überschreiten (im Text der Quelle Q4 zugeordnet), und die Kostenfolge eines wiederholten Waschgangs, die der Artikel selbst herleitet. Beleglosigkeit wird als Streichung geführt, nicht als Beleg.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `84e247f17354e224c973`

**Befund:** Aussage, dass das richtige Beladen allein die Fixkosten senkt, ohne weitere Maßnahmen, ist ein pauschales Leistungsversprechen ohne Nennung von Mechanismen oder Grenzen.

**Frühere Entscheidung (2026-11-12):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 12.11.2026)

> Paket B, entschieden am 12.11.2026: Der Rückfall saß in den Meta-Flächen – `description` und `pin_description` behaupteten weiter „senkt deine Fixkosten“, der Body „senkt die Betriebskosten … nachhaltig“. Alle drei Stellen stehen wieder in der Möglichkeitsform, der Body nennt den Effekt als kleinen Baustein und nicht als Alleinursache. Die Prüfung deckte bis dahin nur den Body ab; deshalb prüft der Regressionstest jetzt auch Titel, Beschreibung, Kurzantwort und Pin-Text. Beleg: BDEW-Strompreisanalyse (Q3 im Artikel) trägt den Strompreis der Rechnung.

Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.

### `a2a7dc69f10393af6531`

**Befund:** Die Modellrechnung (0,9 kWh/50 L bei vollem Waschgang, 0,6 kWh/35 L bei halbem Waschgang, Strompreis 0,40 €/kWh, Wasserpreis 0,005 €/L) und die daraus resultierende Jahresersparnis von 22 € fehlen einer fundierten Quelle.

**Frühere Entscheidung (2026-11-12):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 12.11.2026)

> Paket A, entschieden am 12.11.2026: Die Modellrechnung ist heute vollständig offengelegt (Annahmen, Rechenwege, „Ergebnis der Modellrechnung“). Der frühere Beleg (Bundesnetzagentur-Startseite) trug keinen der Werte; er ist durch die BDEW-Strompreisanalyse ersetzt, die im Artikel als Q3 zitiert ist und den Strompreis von 0,373 €/kWh trägt. Die Wasser- und Verbrauchswerte bleiben als Szenario gekennzeichnet.

- Im heutigen Text nicht mehr vorhanden: 0,40 €, 0,005 €
- Heute in Zeile 20: 0,9 kWh – gekennzeichnet („modellrechnung“)
- Heute in Zeile 121: 0,6 kWh – **ohne** Kennzeichnung
- Heute in Zeile 118: 22 € – **ohne** Kennzeichnung

### `cb794331f1cc0c715a55`

**Befund:** Die Aussage, dass bei 4 Waschgängen pro Woche ein durchschnittlicher Haushalt rund 5 € jährlich an Strom‑ und Wasserkosten spart, ist nicht mit einer Quelle belegt.

**Frühere Entscheidung (2026-11-12):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 12.11.2026)

> Paket A, entschieden am 12.11.2026: Die alte „rund 5 € im Modelljahr“-Aussage existiert nicht mehr; der Artikel rechnet 100 volle gegen 200 halbe Ladungen und kommt auf 28 bis 42 € pro Jahr – ausgewiesen als Ergebnis der Modellrechnung. Beleg für den Preisanteil ist die BDEW-Strompreisanalyse (Q3 im Artikel).

- Heute in Zeile 20: 5 € – gekennzeichnet („modellrechnung“)

### `e6729081522126e972c2`

**Befund:** Angabe, dass ein optimal beladener Trommel (ca. 80 % Kapazität) bis zu 15 % weniger Wasser und Energie verbraucht, wird nicht durch eine Quelle belegt.

**Frühere Entscheidung (2026-11-12):** Frank Hartung (Herausgeber-Auftrag über Arena-Session, 12.11.2026)

> Paket A, entschieden am 12.11.2026: Die „bis zu 15 %“-Angabe ist entfallen. Der Artikel nennt seine Annahmen und sagt in der Kurzantwort ausdrücklich, dass es eine Rechnung mit Quellenwerten und keine Messung im Haushalt ist. Beleg: BDEW-Strompreisanalyse (Q3); Verbrauchswerte sind als Quelle bzw. Szenario benannt.

- Im heutigen Text nicht mehr vorhanden: 15 %
- Heute in Zeile 131: 80 % – gekennzeichnet („modellrechnung“)

---

## Schließweg (eine Zeile je Befund)

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 1b7c9b9cac0290f71242 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ee260c27a6bfdd60fa04 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 124ff2c3cd3917c274aa --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7bdec96c0329769bebe6 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a56734aa032e0ed9e0c4 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 1d4095501e717fb30d7b --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 77520584b5afd8ebd7f7 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a3be3d50280d4fe0a1d8 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d6cc7bae16dead3e610b --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 29eea3c457afaba3d7bd --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 8a0df5531569ec042ec4 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden bda1b543db068b3e00ff --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 3a3269aa4a2e95d780ad --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden c3ff13d7ca048da95112 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ec052a0155f98740a3b5 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ee3a722844f4b84b84b8 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 1dbeb2f8c51e78d11d49 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 33e736ac6afe996b491a --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 96b7b7768d402884810c --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a25bb6bbcb25ba8b0e22 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f94f8ba1e4342e67e45a --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 991bda7b2298b751f4e6 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ae71596724d7a243217b --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 43470330b3b48c9cee49 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 8ddc1025e45be176ad3a --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 95d6d2877620e5a056ce --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ab16029999747466a638 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden b057dee3603e09f494b5 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 91894b9b1535765acdca --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f7b9c93c6a9be1368b06 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 4afb8daed73677ee6224 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 9eb9a90899cc8ca66020 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden b4bd085bc84a6131b644 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden baed76dc211bd15dd46f --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d7c3cfb422310cf26ca6 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 3fe383f6d452737f66f2 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7bba759bbb4ca14c7f35 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e8e32a383b6f803cc8d4 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 0b4755213f0c38321710 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 3e0c5fa74179e97866b8 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ae90ebae2842ff9f97f1 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden b2611d9120121d0ad785 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden fcb8168c18bd423c5180 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 3ad12cdcf94bd8459bd8 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 278d89267d9122a1e9d8 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 450c3aa629342062825e --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7601167c9f3560093fb0 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7efbcd7a4275fe1577bb --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 971a719f94ca492f640e --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 1cc830a25d3ae505dd0e --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 32f827af8f4695488e97 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 642d9c53e557ff642257 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 8230373c2c33722d66d8 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden efee7b0cefffa501cc57 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden dc1e5d50a58f50e0ade1 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden def8ad23c34566c795fe --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 19a724ba20628f34cd01 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 4126d33a9dd92716b286 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 67fbe0b49bb4e6bb48b7 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden cb5f849bfd26ad8121eb --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f108d554ff8861370b64 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 16b3b8584ff802803aa9 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7ff042b6fe804cdf101b --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden bec83c4b814183fa1086 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f9aff86b6eba71b153a6 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden fed9215b770ea4879eda --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 20c08cb650ef6e24af64 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6aafb23c0c6dbb06ce3b --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 24f05ddc03ffdd50118f --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 4816322f061dfdc03bcd --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7017065ee7c74c7ae452 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 1e06a96f6f71e104ce0b --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 81c6a707139046b83ccd --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 8cc00288af8a1f2b02d8 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 3f0a88ede9d44ee910cb --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 51e259fd2d8582e774f7 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 55f8eeedc587cf0895ee --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 009906e47bcc8265b36a --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e0293a43782c64955b27 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 5a1bf10697f58e5fe14a --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e48f9237cff6397c49a6 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f6de6b078d49f9d42e0e --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6cb2229c5eb83b02da23 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f00055a1cb65ee22165f --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7a87eaaa2b863ba8cc46 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 9d67a5e6bd11212c7c1e --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a54abc1cad73d20fb689 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a7d1cf6485921e117919 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a7f69a854430d62a4a3e --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 3eab428a91b1b16b7df8 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7da9383cbc6a45e1a3ac --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden da7852bcca291061c39b --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 334751e6f61ad0033fe4 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 36759a5efe5e8e5163d0 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 942922d1afd7844618e9 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d41f0d5ce8798df0211b --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e139d0769faadd04392a --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 68afba3e6a16a364ce45 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden dc5ff05c5dda79d01373 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 5c096f87730532352820 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 33278b9e7942ebfdbbac --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6ad7358a9afcfef3babb --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7c375a3e1a9bfab1468c --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ea11d36614fa115503b4 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f7b1c869dd8e442eaf16 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6b5921bdc76490587167 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 8436b91bdb63a6316979 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a4ff01e649b789f19e6a --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 58f03a64adaaf8125959 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a7f5f01ef15a38839a0d --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden bcc2bdf06220d5097133 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 25d6b9a720f981e8e9df --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 3693b612533c24dcd1ea --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden c877eeff8842942c0071 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 089b89138417e63a3dcf --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 1158934e7a18c7b2099b --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 3716cfd3ab5aec6d774b --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 26b1c694d76bcc7af50f --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 9593e535bce55f4283e6 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7067eabb89a917ae67a4 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden af2ccb4222eeb195222f --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d9c8b522bf1dcaed0340 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e2975509f3f130de0755 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f1704e45e970a8f4b078 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a10511ed618384aa7b88 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a74029dd4e284794d697 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden c45ea4bb1a6f2330679a --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 4d0125136c5b940946e4 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7aeb2098034d16a46885 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ea97b5dd6695de127fd2 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7c2624072c861d136c96 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d9d3004fbc05895c3f79 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 1dc0f20f9ab3a6b783bc --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7b94ca07b36c0b7cb1cc --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 985f506ee04087bf7253 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ee321fa37210590f7e9b --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 19ab248b17415c73edfb --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 372bb51051e8bd7c5f71 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6aaff85e3a7591d0c5b2 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7e6087a4117a857a92c8 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e28b4ad1f6d608d2ec77 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 34e4bb2acfa235699da5 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 42b9d842341d892d42d0 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 866d8b711dc2de369444 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden bd4c46a336f33a639f05 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e76768fdef3ef5afa026 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 1eae5c7e2bbd95a3362c --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 8547ce3daa75aabb30d4 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden c8b197692bd0023c87bf --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e40a2ee5c7baa5f8567b --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden feb71513c6fb7064dc92 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 04ae33652c1c5eb4e2b8 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 5223a3c7287ff81939cd --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 9800545ae945ec280b34 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden bc0e4f2eb357a682c674 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 0d1977a0b6a7b59136f2 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 228ef205074fdc3fb4b3 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d7c301604b02d49e8d65 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 3bfeb0118af92a780a47 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ed2161154dcee85da1ee --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f593fe21275bd9dcefef --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 98eb45f772ad7a0aac7b --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden b7f0d52968d89cdf8c5b --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden be911855d67f998be662 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 381dd90113dd1ee72f39 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 4483a81dd1c292034cd0 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6f4b591e9cadb27adf49 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden cf60024b74a5e86b50c0 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 4284fd2d9c9005e7af8f --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 84e247f17354e224c973 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a2a7dc69f10393af6531 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden cb794331f1cc0c715a55 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e6729081522126e972c2 --von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"
python3 scripts/faktenfrische_befund_akte.py --schreiben
python3 scripts/release_scorecard.py --live --streng
```

_Jede Entscheidung ist fassungsgebunden: Sie gilt für den heute geprüften
Text (Projektion `betrieb-v4`). Ändert sich ein Satz, öffnet der Befund
erneut – das ist gewollt. Abgeleitete Blöcke und Leerzeilen öffnen nichts._
