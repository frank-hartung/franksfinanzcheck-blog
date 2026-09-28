# Konkurrenzanalyse: ZEIT ONLINE vs. FranksFinanzcheck

> **Auftrag:** Wie lassen sich Blog- und Ratgeberbeiträge dauerhaft auf das Niveau der Online-Redaktion von ZEIT ONLINE heben – und in der Finanzratgeber-Nische übertreffen?
>
> **Stand:** 28.09.2026 · **Wettbewerber:** zeit.de / ZEIT ONLINE · **Eigene Basis:** 56 veröffentlichte Artikel (zuzüglich `_index.md`)
>
> **Rechercheweg:** Agent Reach v1.5.0, Skill `.claude/skills/agent-reach/`, Kanäle `web` (Jina Reader) und `rss` (feedparser), vorheriger Gesundheitscheck mit `agent-reach doctor --json`. Der Doctor meldete Web/Jina und RSS als einsatzbereit. Der konkrete Jina-/RSS-Abruf von zeit.de scheiterte in der Laufumgebung an einer TLS-Verbindung. Zur Ausfallsicherheit wurden die öffentlich indexierten ZEIT-Seiten danach über die verfügbare Websuche gelesen. Das ist im Sinne der Agent-Reach-Leitplanke transparent ausgewiesen; es werden keine nicht erhobenen Agent-Reach-Treffer behauptet.

---

## 1. Management Summary

**ZEIT ONLINE gewinnt nicht durch eine einzelne Textformel.** Das Niveau entsteht aus einem System: spezialisierten Ressorts, mindestens einer zweiten redigierenden Person, Korrektorat, Quellen- und Wahrhaftigkeitsregeln, pointierter Autorensprache, Formatentwicklung, Daten/Visualisierung, SEO, Community sowie einer sichtbaren Korrekturpraxis.

FranksFinanzcheck besitzt bereits eine ungewöhnlich starke technische Qualitätsbasis: Agent-Reach-Recherche, Faktenfrische, Quellenfelder, Lesbarkeitsprüfung, Audio, strukturierte Daten und Automations-Gates. Der Abstand zu ZEIT ONLINE liegt deshalb **weniger bei Automatisierung und elementarer Verständlichkeit**, sondern vor allem bei:

1. **originärer Recherche** statt bloßer Sekundärquellen-Synthese,
2. **menschlicher Zweitredaktion und fachlicher Gegenprüfung**,
3. **sprachlicher Eigenständigkeit und Dramaturgie**,
4. **Datenprodukten, Grafiken und eigenen Berechnungen**,
5. **sichtbarer Korrektur-, Update- und Quellenhistorie**,
6. **klarer Trennung von Nachricht, Analyse, Ratgeber und Meinung**,
7. **Autorität durch mehrere benannte Fachleute und Gesprächspartner**.

**Realistisches Ziel:** ZEIT ONLINE nicht als Universalmedium kopieren. In der engen Domäne „alltagstaugliche private Finanzen, Verträge und Sparen“ kann FranksFinanzcheck ZEIT übertreffen, wenn jeder Ratgeber zugleich (a) journalistisch sauber, (b) individuell berechenbar, (c) handlungsorientiert, (d) versions- und quellentransparent und (e) nachweislich aktuell ist.

---

## 2. Methodik und belastbare Quellenbasis

### 2.1 Analysierte ZEIT-Standards

- [Leitlinien der Redaktionen von ZEIT und ZEIT ONLINE](https://www.zeit.de/fragen-der-zeit/2018/09/leitlinien-der-zeit-redaktionen): Genauigkeit, in der Regel zwei unabhängige Quellen für nicht selbst überprüfbare Nachrichten, Gründlichkeit vor Schnelligkeit, gewissenhaftes Redigieren, transparente Korrekturen, Recherche/Analyse/Argument, lebendige Sprache und anspruchsvolle Gestaltung.
- [Wie wir mit unseren Fehlern umgehen](https://blog.zeit.de/glashaus/2017/02/24/fehler-korrektur-journalismus-sprache-inhalt-ablaeufe-zeit-online/): Jeder Beitrag wird mindestens von einer zweiten Person gelesen und redigiert; wichtige Beiträge durchlaufen zusätzliche Schleifen; viele Texte gehen ins Korrektorat; inhaltliche Korrekturen werden unter dem Artikel offengelegt.
- [Standards und Regeln für journalistische Beiträge](https://www.zeit.de/glashaus/archiv/2019-05/was-ist-in-unseren-journalistischen-beitraegen-erlaubt-was-nicht): keine vorgetäuschte Augenzeugenschaft, Herkunft von Zitaten und Erlebnissen kenntlich machen, sachliche Richtigkeit und Quellen nachprüfbar halten.
- [KI-Standards der ZEIT-Redaktion](https://www.zeit.de/administratives/2026-08/ki-standards-zeit-redaktion): nur freigegebene Werkzeuge, KI-Antwort nie als vertrauenswürdige Quelle, menschliche Verantwortung für Endfassungen, Nachvollziehbarkeit des Entstehungsprozesses, Kennzeichnung eigenständiger KI-Zusatzangebote.
- [Impressum](https://www.zeit.de/impressum/index): sichtbare Spezialisierung u. a. für Investigative Recherche/Daten, Daten und Visualisierung, Formatentwicklung, SEO/Abosteuerung und Community.
- [ZEIT-App und Audiofunktionen](https://www.zeit.de/administratives/2024-05/zeit-online-app-audio-update): fast alle Artikel als Hörangebot, Warteschlange, Abspielgeschwindigkeit, Schriftgröße, Merkliste und nutzerzentrierte Bedienung.

### 2.2 Stichprobe aus dem Finanzangebot

Die Stichprobe umfasst unterschiedliche Formen statt nur eines einzelnen Texttyps:

- [Tagesgeld: Diese Banken zahlen Ihnen vier Prozent](https://www.zeit.de/wirtschaft/geldanlage/2026-09/tagesgeld-einlagen-sparer-revolut-chase) – aktueller erklärender Nutzwertartikel mit Angebotsbedingungen, Einordnung und Beispielrechnung.
- [Faktor-ETFs: Ist das die ultimative Alternative zum MSCI World?](https://www.zeit.de/geld/2026-09/faktor-etf-sparer-investieren-msci-world-geldverbesserer) – Expertenkolumne, Produktvergleich, Mehrjahreswerte, Risikoabwägung und klares Fazit.
- [ETF-Fallen](https://www.zeit.de/geld/2026-05/etf-fallen-investieren-fehler-finanztipps-geldverbesserer) – problemorientierter Listenratgeber mit konkreten Fehlerbildern.
- [Sie investieren immer noch nicht in ETFs?](https://www.zeit.de/geld/2025-01/geld-anlegen-investieren-finanzen-etfs-tipps) – motivierender Einstieg mit starker Metapher und niedrigschwelliger Leserführung.
- [26 Finanzfehler](https://www.zeit.de/geld/2025-12/geld-sparen-finanzen-tipps-2026) – saisonaler Service, psychologische Erklärung und breite Handlungsagenda.
- [Riester-Rente: So geht Riestern ohne Risiko](https://www.zeit.de/wirtschaft/geldanlage/2024-06/private-altersvorsorge-riester-rente-rentenluecke-faq) – FAQ-Struktur, Zielgruppenabgrenzung und externe Weiterleitung zu vertiefender Anleitung.

### 2.3 Eigene Messbasis

Lokaler Bestandscheck am 28.09.2026:

- 56 redaktionelle Artikel plus `_index.md`
- Median: **1.717 Wörter**
- Median: **14 H2-Überschriften**
- Median sichtbarer externer Markdown-Links im Fließtext: **0** (Quellen können zusätzlich im Frontmatter geführt werden; die Kennzahl misst nur sichtbare Inline-Belege)
- internes Lesbarkeits-Audit: **Ø 94/100**, **Ø Flesch 63,6**
- 14 Beiträge lagen im Audit unter dem Zielwert Flesch 62; fünf davon unter 52

Die Zahlen zeigen: Umfang und formale Lesbarkeit sind grundsätzlich konkurrenzfähig. Mehr Länge oder noch mehr Zwischenüberschriften lösen die Qualitätslücke nicht.

---

## 3. Was das ZEIT-Niveau tatsächlich ausmacht

### 3.1 Redaktionelle Organisation statt Einzelautor-Optimierung

ZEIT behandelt Qualität als arbeitsteiligen Prozess. Autor, redigierende Person, gegebenenfalls Korrektorat, Daten-/Visualisierungsteam und Formatentwicklung erfüllen unterschiedliche Funktionen. Das ist der wichtigste strukturelle Vorsprung.

**Konsequenz:** Eine KI, die denselben Entwurf mehrfach „poliert“, ersetzt keine unabhängige Zweitprüfung. Der zweite Durchgang braucht eine andere Rolle, andere Prüffragen und idealerweise einen anderen Menschen.

### 3.2 Originärer Erkenntniswert

Starke ZEIT-Beiträge erklären nicht nur Bekanntes. Sie kombinieren aktuelle Anlässe, konkrete Zahlen, Expertenaussagen, Gegenpositionen, Erfahrungsbeispiele und eine redaktionelle These. Leser erhalten eine begründete Einordnung, nicht nur eine suchmaschinenfreundliche Zusammenfassung.

### 3.3 Stimme und Dramaturgie

ZEIT-Texte dürfen pointiert, überraschend und bildhaft sein. Die Beispiele reichen von „Reichmachmaschine“ bis zu „ETF-Fallen“. Diese Einstiege erfüllen eine Funktion: Sie übersetzen Abstraktion in ein Problem, erzeugen Spannung und führen anschließend in belegte Erklärung.

**Nicht nachahmen:** bloßer ZEIT-Ton oder ähnliche Überschriften. Zu übernehmen ist das Prinzip: Jeder Text benötigt einen eigenständigen Gedanken und einen erkennbaren dramaturgischen Bogen.

### 3.4 Evidenz plus Unsicherheit

Die Finanztexte nennen Zahlen und Produkte, begrenzen Empfehlungen aber nach Zielgruppe, Zeitraum, Kosten und Risiko. Gute Beratung enthält nicht nur „Was tun?“, sondern ebenso „Für wen nicht?“, „Unter welchen Annahmen?“ und „Was kann schiefgehen?“

### 3.5 Formatvielfalt

ZEIT nutzt Nachricht, FAQ, Kolumne, Analyse, Gespräch, Datenvisualisierung, Audio und interaktive Elemente. Derselbe Gegenstand wird nicht immer in dasselbe Ratgebertemplate gepresst.

### 3.6 Öffentliche Verantwortlichkeit

Die sichtbare Korrekturpraxis ist selbst ein Qualitätsmerkmal. Ein aktualisiertes Datum ohne Änderungsnotiz wirkt schwächer als eine nachvollziehbare Historie: Was wurde geändert, warum, durch wen und anhand welcher Quelle?

---

## 4. Direkter Wettbewerbsvergleich

Bewertungsskala: 1 = schwach, 3 = solide, 5 = führend. ZEIT-Werte sind eine qualitative Bewertung der veröffentlichten Standards und Stichprobe; FF-Werte beruhen zusätzlich auf dem Repository-Audit.

| Dimension | ZEIT | FF heute | Befund |
|---|---:|---:|---|
| Fakten-/Wahrhaftigkeitsstandard | 5 | 4 | FF hat starke technische Quellen-Gates; ZEIT zusätzlich institutionalisierte menschliche Prüfung und Zwei-Quellen-Prinzip. |
| Menschliche Zweitredaktion | 5 | 2 | Größte Prozesslücke. Automatisierte Rollen sind nicht unabhängig genug. |
| Originäre Recherche/Interviews | 5 | 2 | FF synthetisiert überwiegend öffentliche Quellen; eigene Stimmen und Datenerhebung fehlen sichtbar. |
| Verständlichkeit | 4 | 4 | FF Ø Flesch 63,6 und klare Handlungsstruktur; Ausreißer müssen konsequenter blockiert werden. |
| Eigenständige Sprache | 5 | 3 | FF ist klar, aber Templates und wiederkehrende Formeln bergen Gleichförmigkeit. |
| Nutzwert/Schrittfolge | 4 | 5 | Hier kann FF führen: Checklisten, Rechner und konkrete Umsetzung sind Kernkompetenz. |
| Daten/Visualisierung | 5 | 2 | ZEIT besitzt ein eigenes Team; FF braucht fokussierte Datenprodukte statt dekorativer Charts. |
| Aktualität | 5 | 4 | FF hat Faktenfrische und Agent Reach; Ereignis-Trigger und sichtbare Änderungsverläufe fehlen noch. |
| Korrekturtransparenz | 5 | 2 | ZEIT dokumentiert wesentliche Korrekturen öffentlich; FF braucht ein standardisiertes Änderungsprotokoll. |
| Formatvielfalt | 5 | 3 | Audio ist stark; Interviews, Pro/Contra, Fallstudien, Datenstories und echte Kolumnen fehlen. |
| Autorität/Expertise | 5 | 3 | ZEIT hat spezialisierte Teams; FF kann mit einem kleinen, sichtbaren Expertennetzwerk aufholen. |
| Unabhängigkeit/Kommerz | 5 | 4 | FF hat Affiliate-Governance; Offenlegung sollte artikelgenau und noch sichtbarer sein. |
| UX/Barrierearmut | 5 | 4 | FF Audio und Lesefunktionen sind stark; Personalisierung/Merkliste und hochwertige Grafiken bleiben Lücken. |
| SEO/GEO-Maschinenlesbarkeit | 4 | 5 | FF hat hier durch strukturierte Quellen, Schema und feste Gates einen realistischen Vorsprung. |

**Gesamturteil:** FranksFinanzcheck ist technisch-redaktionell weiter als ein typischer Einzelblog. Für ZEIT-Niveau fehlen jedoch echte redaktionelle Unabhängigkeit im Prüfprozess und eigener Erkenntnisgewinn. Genau diese beiden Lücken kann keine zusätzliche Text-KI allein schließen.

---

## 5. Zielstandard: „FF Editorial Standard 100“

Jeder neue Ratgeber muss vor Veröffentlichung 100 Pflichtpunkte erreichen. Ein Durchschnittswert darf kein kritisches Defizit verdecken.

### A. Auftrag und Eigenwert – 15 Punkte

- 5: eine präzise Leserfrage und ein konkreter Entscheidungsfall
- 5: mindestens **eine originäre Leistung** (eigene Rechnung, Datenauswertung, Interview, Dokumentenanalyse, Test oder belastbare Fallstudie)
- 5: ein Satz im Briefing: „Nach diesem Artikel kann der Leser …“

### B. Recherche und Belege – 20 Punkte

- 5: mindestens zwei voneinander unabhängige belastbare Quellen bei zentralen veränderlichen Tatsachen
- 5: Primärquelle vor Sekundärquelle (Gesetz, Behörde, Preisblatt, Geschäftsbedingungen, Statistik)
- 5: jede Zahl mit Quelle, Bezugszeitpunkt, Einheit und Kontext
- 5: Gegenbeleg-/Widerspruchssuche dokumentiert

### C. Fachliche Fairness – 15 Punkte

- 5: „Geeignet für / nicht geeignet für“
- 5: Risiken, Kosten, Ausnahmen und Unsicherheiten gleich sichtbar wie Vorteile
- 5: Interessenkonflikt und Affiliate-Bezug artikelgenau offengelegt

### D. Text und Dramaturgie – 15 Punkte

- 5: eigenständiger Einstieg statt generischer Frage oder SEO-Floskel
- 5: roter Faden Problem → Evidenz → Optionen → Entscheidung → Umsetzung
- 5: konkrete Szenen, Beispiele oder Rechnungen ohne erfundene Personen/Zitate

### E. Nutzwert – 15 Punkte

- 5: Kurzantwort mit Bedingungen, nicht als pauschales Versprechen
- 5: ausführbare Schrittfolge oder Entscheidungsmatrix
- 5: mindestens ein eigenes Werkzeug: Rechner, Download, Tabelle, Vorlage oder Checkliste

### F. Redaktionelle Prüfung – 15 Punkte

- 5: unabhängige Fachprüfung (Vier-Augen-Prinzip)
- 5: separates Sprach-/Strukturlektorat
- 5: Link-, Rechen-, Zitat- und Claims-Check bestanden

### G. Lebenszyklus – 5 Punkte

- 2: verantwortliche Person und nächster Prüfanlass
- 2: Ereignis-Trigger statt nur Kalenderdatum
- 1: öffentliches Änderungsprotokoll

**Harte Stopper – unabhängig vom Punktestand:** unbelegte Kernzahl; erfundenes Zitat/Erlebnis; unklarer kommerzieller Einfluss; fehlende Gegenanzeige bei YMYL-Empfehlung; nur KI-basierte fachliche Freigabe; keine Primärquelle trotz verfügbarer Primärquelle.

---

## 6. Dauerhafter Redaktionsprozess

### Stufe 1 – Themenentscheidung

Nur produzieren, wenn mindestens eines gilt:

1. hoher Entscheidungsdruck für Leser,
2. erhebliche finanzielle Wirkung,
3. aktuelle Regel-/Marktänderung,
4. bestehender Artikel ist belegbar veraltet,
5. FF kann einen eigenen Erkenntnisbeitrag leisten.

**Nicht produzieren:** bloße Keyword-Variation eines vorhandenen Beitrags. Das reduziert Kannibalisierung und redaktionelle Gleichförmigkeit.

### Stufe 2 – Recherchebrief mit Agent Reach

Agent Reach sammelt nur Signale und Quellenkandidaten. Der Brief enthält:

- Fragestellung und Hypothese,
- Primärquellen,
- mindestens eine Gegenposition,
- offene Widersprüche,
- Zahlen mit Stichtag,
- mögliche Gesprächspartner,
- Änderungsereignisse, die später einen Refresh auslösen.

**Regel:** Agent Reach oder ein Chatbot ist nie die zitierte Quelle. Zitiert wird die Originalquelle.

### Stufe 3 – Eigenrecherche

Für jeden Premium-Ratgeber mindestens eines:

- Mini-Interview mit Verbraucherzentrale, Wissenschaft, Behörde oder Fachpraxis,
- eigene Stichprobe von mindestens fünf relevanten Tarifen/Preisblättern,
- reproduzierbare Modellrechnung mit Annahmen,
- Auswertung eines offenen Datensatzes,
- dokumentierter Produkttest ohne verdeckte Gegenleistung,
- echte Leserfrage als anonymisierter Fall mit Einwilligung.

### Stufe 4 – Schreibbriefing

Vor dem Schreiben festhalten:

- Kernthese in einem Satz,
- stärkster Beleg,
- stärkster Einwand,
- Zielgruppe und Nicht-Zielgruppe,
- gewünschte Handlung,
- Formatentscheidung (FAQ, Analyse, Test, Datenstory, Interview, Schrittfolge),
- was an diesem Beitrag unverwechselbar ist.

### Stufe 5 – Entwurf

Die KI darf strukturieren, Varianten vorschlagen, Verständlichkeit prüfen und Lücken markieren. Der verantwortliche Mensch entscheidet über These, Auswahl, Gewichtung, endgültige Formulierung und Veröffentlichung.

### Stufe 6 – „Roter“ Gegencheck

Eine getrennte Rolle versucht, den Beitrag zu widerlegen:

- Welche Zahl ist falsch oder veraltet?
- Welche Zielgruppe wird durch die Empfehlung benachteiligt?
- Welche Annahme ist versteckt?
- Welche Quelle hängt von derselben Ursprungsquelle ab?
- Ist der Titel stärker als die Evidenz?
- Wird Affiliate-Conversion mit Empfehlung verwechselt?

### Stufe 7 – Zweitredaktion

Eine zweite Person prüft nicht nur Rechtschreibung, sondern Auftrag, Logik, Gewichtung, Belege, Ton und potenziellen Schaden. Für Versicherungen, Steuern, Geldanlage und Kredite zusätzlich fachkundige Freigabe.

### Stufe 8 – Veröffentlichung

Jeder Beitrag zeigt:

- Autor und konkrete Kompetenz,
- „fachlich geprüft von“ (wenn vorhanden),
- Recherche-/Datenstand,
- wichtigste Primärquellen,
- Methodik/Annahmen bei Rechnungen,
- Affiliate-/Interessenkonflikthinweis,
- letzte wesentliche Änderungen,
- Feedback-/Fehler-melden-Funktion.

### Stufe 9 – Lebenszyklus

Nicht nur „alle 45/90 Tage prüfen“, sondern Ereignisse beobachten:

- EZB-/Bundesbank-Entscheidungen,
- Gesetzesverkündung und Inkrafttreten,
- Preisblatt-/AGB-Änderungen,
- neue BaFin-/BNetzA-/Destatis-Daten,
- Produktkündigung oder Konditionswechsel,
- überdurchschnittlich viele Leserhinweise,
- Ranking-/Traffic-Sprung bei sinkender Zufriedenheit.

Jede wesentliche Änderung erzeugt einen öffentlichen Changelog-Eintrag. Reine Typokorrekturen müssen nicht einzeln protokolliert werden.

---

## 7. Wie FranksFinanzcheck ZEIT in der Nische übertreffen kann

### 7.1 Vom Artikel zum überprüfbaren Entscheidungsprodukt

ZEIT erklärt hervorragend. FF sollte zusätzlich **rechnen und ausführen lassen**:

- individualisierbare Rechner,
- herunterladbare Entscheidungsvorlagen,
- Kosten über 1/5/10/20 Jahre,
- Break-even-Punkte,
- Sensitivitätsanalyse („Was ändert sich bei ±1 Prozentpunkt?“),
- Ergebnis inklusive Annahmen und Export.

### 7.2 Reproduzierbare Daten statt einzelner Beispielzahlen

Für Kernfelder eigene, versionierte Datenreihen bauen:

- Tages-/Festgeld-Konditionsindex,
- DSL-Gesamtkosten über 24 Monate,
- Versicherungs-Selbstbehalt-Szenarien,
- Haushaltskosten-/Sparpotenzial-Index,
- Kündigungs- und Wechselkalender.

Jede Tabelle bekommt Datenstand, Stichprobe, Methodik und maschinenlesbaren Download. Damit entsteht ein zitierbarer Primärwert – ein Vorsprung gegenüber einem reinen Erklärartikel.

### 7.3 Regionale und lebensnahe Tiefe

ZEIT adressiert ein breites Publikum. FF kann näher am Alltag sein:

- Beispielhaushalte mit klaren Annahmen,
- Ost-/West-, Stadt-/Land- oder Mieter-/Eigentümer-Szenarien, sofern Daten dies tragen,
- konkrete Briefe, Checklisten und Gesprächsskripte,
- „in 10 Minuten“, „an einem Abend“, „vor Vertragsabschluss“.

### 7.4 Offenstes Update-System der Nische

Öffentliche Versionshistorie pro Artikel:

```text
28.09.2026 – Zinssätze und Beispielrechnung aktualisiert; Revolut-Preisblatt geprüft.
14.09.2026 – Abschnitt Einlagensicherung ergänzt; fachlich geprüft von …
02.07.2026 – Erstveröffentlichung; Datensatz v1.0.
```

Zusätzlich: Link zur archivierten/reproduzierbaren Datengrundlage und Hinweis, was **nicht** erneut geprüft wurde.

### 7.5 Kleines Expertennetzwerk statt Vollredaktion imitieren

Ein realistisch finanzierbares Modell:

- 1 verantwortlicher Herausgeber,
- 1 freie Schlussredaktion für alle Premiumtexte,
- Pool aus 3–5 Fachprüfern (Versicherung, Steuer, Geldanlage, Energie/Telekom, Verbraucherrecht),
- vierteljährlicher Methodenbeirat oder Peer Review für Datenprodukte.

Bezahlung und mögliche Interessenkonflikte transparent ausweisen. Anbieter dürfen keine Empfehlung freigeben.

### 7.6 Leser als Qualitätsnetz

Unter jedem Beitrag:

- „War die Antwort hilfreich?“
- „Welche Stelle blieb unklar?“
- „Hat sich eine Kondition geändert?“
- öffentlich sichtbare Korrekturquote/Antwortzeit erst nach ausreichender Datenbasis,
- redaktionelles SLA: substanzielle Hinweise binnen zwei Werktagen prüfen.

---

## 8. Priorisierter 90-Tage-Plan

### Tage 1–30: Qualitätssystem schließen

1. Editorial Standard 100 verbindlich machen.
2. Pflichtfeld für zweite redigierende/fachprüfende Person einführen.
3. öffentliches Änderungsprotokoll im Artikeltemplate ergänzen.
4. „Primärquelle / Gegenquelle / Annahme / Stand“-Schema in Briefings ergänzen.
5. die 14 Lesbarkeits-Ausreißer manuell überarbeiten; Score nicht durch kurze Sätze allein optimieren.
6. zehn umsatz- oder risikoreichste YMYL-Artikel auf unbelegte Kernzahlen auditieren.

**Erfolgskriterien:** 100 % der neuen YMYL-Texte mit Zweitprüfung; 100 % Kernzahlen belegt; keine Veröffentlichung mit hartem Stopper.

### Tage 31–60: Eigenleistung sichtbar machen

1. zwei Kernartikel als Datenprodukte neu entwickeln.
2. ersten unabhängigen Fachprüfer vertraglich gewinnen.
3. fünf echte Experten-/Verbrauchergespräche führen.
4. standardisierte Modellrechnung mit Rechentest und Annahmenbox bauen.
5. Leser-Feedback und Fehler-melden-Kanal artikelbezogen einführen.

**Erfolgskriterien:** zwei reproduzierbare Datensätze; mindestens fünf originäre Stimmen; Feedbackroute mit dokumentierter Bearbeitungszeit.

### Tage 61–90: Nischenführerschaft testen

1. drei „Signature Guides“ veröffentlichen: je ein Thema aus Geldanlage, Versicherung und laufenden Verträgen.
2. jedes Stück mit Originalrecherche, Fachprüfung, Rechner/Download und Changelog.
3. Ereignis-Trigger für fünf Primärquellen automatisieren.
4. Verständnistest mit fünf Zielgruppenlesern pro Signature Guide.
5. Ergebnisse und Korrekturen öffentlich in einem Quartalsbericht zusammenfassen.

**Erfolgskriterien:** ≥80 % Aufgabenlösung im Nutzertest; keine ungeklärte fachliche Beanstandung älter als zwei Werktage; mindestens ein externer organischer Verweis auf Daten/Werkzeug statt nur auf Text.

---

## 9. Dauerhafte Kennzahlen – Qualität statt Content-Menge

| Kennzahl | Ziel |
|---|---:|
| neue YMYL-Beiträge mit menschlicher Zweitprüfung | 100 % |
| zentrale veränderliche Fakten mit zwei unabhängigen Quellen | ≥95 % |
| zentrale Zahlen mit Primärquelle und Stichtag | 100 % |
| Beiträge mit originärer Eigenleistung | 100 % Premium / ≥50 % Standard |
| wesentliche Updates mit öffentlichem Changelog | 100 % |
| substanzielle Leserhinweise innerhalb 2 Werktagen geprüft | ≥90 % |
| Artikel, bei denen Testleser die Kernaufgabe lösen | ≥80 % |
| harte Fehler nach Veröffentlichung | <1 je 50 Artikel; 100 % transparent korrigiert |
| Artikel mit klarer Nicht-Zielgruppe/Gegenanzeige | 100 % YMYL |
| aktualitätskritische Artikel mit Ereignis-Trigger | zunächst Top 20, danach 100 % |

**Nicht als Haupt-KPI verwenden:** Wortzahl, Artikelzahl pro Woche, Flesch allein, KI-Score allein oder organischer Traffic allein. Diese Werte können Qualität unterstützen, aber auch Fehlanreize erzeugen.

---

## 10. Konkrete Do/Don’t-Regeln

### Do

- Primärquellen lesen und im Text präzise referenzieren.
- eine Empfehlung stets an Bedingungen knüpfen.
- Zahlen nachrechnen und Rechenweg testbar halten.
- echte Ungewissheit benennen.
- einen überraschenden, aber belegbaren Eigenwert schaffen.
- Überschriften erst nach dem belastbaren Fazit finalisieren.
- wesentliche Korrekturen sichtbar lassen.
- KI als Assistenz und Prüfer, niemals als Quelle oder alleinige Freigabe nutzen.

### Don’t

- ZEIT-Stil imitieren oder Formulierungen übernehmen.
- generische „Alles, was du wissen musst“-Texte veröffentlichen.
- fünf Sekundärartikel als fünf unabhängige Quellen zählen.
- Aktualität nur über ein neues Datum simulieren.
- Fachautorität durch ein KI-generiertes Autorenprofil vortäuschen.
- Affiliate-Ziel und redaktionelle Empfehlung vermischen.
- komplexe Themen allein durch Kürzen „verständlich“ machen.
- jede Leserfrage in dasselbe Template pressen.

---

## 11. Schlussfolgerung

Das ZEIT-Niveau ist vor allem ein **institutioneller Qualitätsprozess**. FranksFinanzcheck kann ihn nicht durch längere Beiträge oder ein weiteres Sprachmodell erreichen. Notwendig sind unabhängige Zweitredaktion, originäre Recherche, fachliche Gegenprüfung, Daten-/Rechenprodukte und öffentliche Korrekturhistorien.

Der Blog kann ZEIT ONLINE in seiner Nische dennoch übertreffen: nicht bei redaktioneller Größe oder Themenbreite, wohl aber bei **konkreter Entscheidungshilfe, Reproduzierbarkeit, Aktualitätsautomatisierung, Quellenoffenheit und individueller Berechnung**. Die wirksamste Positionierung lautet daher:

> **So sorgfältig geprüft wie ein Qualitätsmedium – aber konkreter, berechenbarer und nachvollziehbarer für die persönliche Finanzentscheidung.**

Der erste Hebel ist nicht mehr Content. Der erste Hebel ist ein verbindliches Vier-Augen-System für die wichtigsten 20 Artikel, ergänzt um ein öffentliches Changelog und mindestens eine originäre Leistung pro Beitrag.
