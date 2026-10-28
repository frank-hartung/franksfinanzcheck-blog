# Profi-Affiliate-Umsetzung: vom Content-System zum messbaren Geschäft

**Arbeitsstand:** 28.10.2026 · **Geltungsbereich:** franksfinanzcheck.de · **Status:** Umsetzung auf dem Arbeits-Branch; Produktion, DNS und Partnerkonten wurden nicht verändert.

Dieses Dokument ist der operative Vertrag für die sechs priorisierten Wachstumsschritte. Es trennt belegte Repository-Fakten von Arbeit, die zwingend den Betreiber, einen realen Partnerdatensatz oder eine fachliche Freigabe braucht. Kein Zielwert in diesem Dokument ist ein bereits erzieltes Ergebnis.

## Entscheidung für die nächsten 90 Tage

**Primärcluster: Strom- und Gaskosten im Haushalt – vom Verbrauch bis zum Vertragsvergleich.**

Begründung: Der vorhandene Search-Console-Prioritätsstand führt den Artikel `2026-10-12-kleine-energiespar-tricks-die-deine-kosten-sofort-senken` mit 54 Impressionen und Position 33,15; der Energie-Pillar hat bereits passende Rechner, einen Tarifwechsel-Entscheidungsbaum und unterstützende Inhalte. Das ist ein **Testsignal, kein Nachweis von Umsatz oder dauerhaftem Suchvolumen**. Die Datenbasis ist klein und es gibt noch keine belastbare Affiliate-Klick- oder Provisionsmessung.

Der Cluster wird als Verbraucherentscheidung aufgebaut, nicht als weiterer „Spartipps“-Strom:

1. **Kosten sehen:** letzte Abrechnung, Zählerstand und tatsächliche Jahresmenge.
2. **Konditionen rechnen:** Strom und Gas getrennt; Vollkosten über dieselbe Laufzeit.
3. **Fristen sichern:** nur die Frist des konkreten Vertrags verwenden.
4. **Kurs halten:** nächster Prüftermin aus dem echten Vertragsdatum.

Andere Themen bleiben erreichbar. Für 90 Tage wird jedoch **keine Publikationsmenge erhöht**, bevor die Kernseiten, Beleglage, Nutzungsdaten und CTA-Relevanz geprüft sind.

## 1. Messbarkeit: Status quo und Abnahme

### Repository-Status

- Affiliate-Routen und deren Darstellung sind technisch prüfbar; die Partnerabrechnung hat eine datensparsame Offline-Importstrecke.
- `npm run mess:status` zeigt derzeit: keine lokale Provisionsdatei, kein Import und keinen Klickzähler-Lauf.
- Der Klick-Worker ist laut `docs/ANLEITUNG-KLICKMESSUNG-OHNE-COOKIES.md` **nicht produktiv eingerichtet**. `data/klickmessung.yaml` steht auf `aktiv: false`.
- Deshalb bleiben Klicks, Anträge, Abschlüsse, Provision und EPC **unbekannt**. Unbekannt ist niemals 0 € Umsatz.

### Umgesetzte Verbesserung

Der Revenue-Funnel unterscheidet jetzt ausdrücklich:

- **Pipeline-Ampel:** technischer Zustand der eingeschalteten Messwege;
- **Geschäftsmessbarkeit:** unbekannt, teilweise, veraltet oder vollständig gemessen.

Eine grüne Pipeline-Ampel ist kein Umsatz- oder Erfolgssignal. Der maschinenlesbare Funnel enthält `geschaeftsmessbarkeit` mit Quellenabdeckung; Tests sichern die Unterscheidung.

### In dieser Arbeitskopie noch nicht ausführbare Schritte

1. Die Betreiberin/der Betreiber richtet Worker, D1 und `stats.franksfinanzcheck.de` gemäß dem Runbook ein und bestätigt `/healthz`.
2. Die Datenschutzprüfung des konkreten Cloudflare-Betriebs wird abgeschlossen; erst danach wird `aktiv: true` gesetzt und die `/go/`-Seiten neu erzeugt.
3. Partnerabrechnungen werden monatlich **aggregiert** in der lokalen, gitignored CSV eingetragen und validiert. Keine Personen- oder Kundendaten gehören in Git.
4. Erst nach realen Importen wird ein Funnel-Wert interpretiert. Partnerabschlüsse und Monatsprovisionen werden nicht künstlich auf einzelne Artikel verteilt.

**Abnahme:** zwei frische Quellen (Klicks und Abrechnung), dokumentierte Herkunft, keine Rohdaten im öffentlichen Repository und zwei aufeinanderfolgende Wochen mit verständlicher Auswertung. Ein technischer Selftest allein erfüllt die Abnahme nicht.

## 2. Cluster- und Inhaltsfokus

Der Strom-/Gas-Pillar ist die zentrale Einstiegsseite. Priorität haben:

1. `/pillar/strom-sparen/` – Methodik, Angebote, Rechner und Weiterleitungen;
2. aktuelle Strom-/Gas-Wechsel- und Kostenbeiträge mit konkretem Nutzerproblem;
3. `/werkzeuge/` und die drei passenden Rechner – als vollständig nutzbare Werkzeuge, nicht als Lead-Gates;
4. interne Verlinkung zwischen Hub, Ratgebern und Werkzeugen nach Suchabsicht.

**Stop-Regel:** keine neuen saisonalen Varianten derselben Suchabsicht veröffentlichen, wenn das bestehende Stück die Frage bereits beantwortet. Entwürfe mit generischem CHECK24-Portal-CTA, ungeprüften Beträgen oder offener redaktioneller Prüfung bleiben Entwürfe.

## 3. Bestand optimieren, nicht blind erweitern

In dieser Runde wurden konkrete, belegte Probleme behoben:

- Der Strom-/Gas-Pillar verspricht keine pauschalen Einsparbeträge mehr. Die verifizierbaren Abrechnungs- und Angebotsdaten des Lesers stehen im Mittelpunkt.
- Unbelegte „Praxis-Fallstudien“ mit nicht dokumentierten Haushalten und rechnerisch widersprüchlichen Summen wurden entfernt. An ihre Stelle trat ein nachrechenbarer Vollkosten-Rechenweg ohne erfundene Marktwerte.
- Feste Monats-, Prozent- und Temperaturregeln wurden dort, wo sie keine belastbare Grundlage hatten, durch die Prüfung des konkreten Vertrags bzw. der Hersteller- und Anlagenhinweise ersetzt.
- Der Gaszähler-Artikel führt nicht mehr auf einen Stromtarif. Der Mietwagen-CTA im Camping-Beitrag nennt jetzt den konkreten Nutzungskontext.
- Der Heizöl-Beitrag mit unbelegten saisonalen Preis- und Einsparbehauptungen wurde zurückgestellt. Seine unpassenden Stromtarif-CTAs wurden entfernt; eine sachlich passende Heizöl-Partnerroute wird nicht erfunden. Die alte URL erhält eine nachvollziehbar begründete Weiterleitung zum Energie-Einstieg.

**Vor weiterer Aktualisierung:** Preis- und Rechtsaussagen nur mit Primärquelle, Abruf-/Standdatum und konkretem Anker aktualisieren. Das BDEW-Marktradar trägt einen sichtbaren Quellenstand; bundesweite Werte werden ausdrücklich nicht als persönliches Angebot ausgegeben.

**Abnahme je Kernseite:** Suchabsicht eindeutig, zentrale Frage früh beantwortet, Zahlen mit Quellen-/Rechenweg, Angebot passend und ehrlich, interne Weiterleitung sinnvoll, mobile und barrierefreie Darstellung geprüft.

## 4. Eigene Erfahrung und Beweisführung

Es wird **keine Fallstudie, Messung oder Lesermeinung erfunden**. Das öffentliche Beweisregister (`data/beweise/register.yaml`) enthält bereits:

- ein dokumentiertes Modellbeispiel zum DSL-Effektivpreis;
- einen ausdrücklich als Modellfall markierten DSL-Fall;
- ein DSL-Wechselprotokoll in Erhebung;
- eine Standby-Messreihe mit geplantem Messaufbau und Fälligkeit 30.11.2026;
- eine geplante anonymisierte Kfz-Leserfallstudie mit Einwilligungs- und Vier-Augen-Anforderungen.

**Nächster echter Beleg für den gewählten Cluster:** die bereits registrierte Standby-Messreihe. Das präzisierte [Erhebungsprotokoll](PROTOKOLL-STANDBY-MESSREIHE.md) beschreibt Messaufbau, Rohdaten, Hochrechnungsgrenzen und Freigabe. Erst nach tatsächlicher Erhebung, Gegenprüfung der Rohwerte, Rechenweg und Strompreisquelle darf sie als eigene Messung veröffentlicht werden. Bis dahin bleibt sie als „in Erhebung“ kenntlich; kein Artikel darf das Vorhaben als Testergebnis ausgeben.

Eine reale Leser-Fallstudie setzt echte Unterlagen und schriftliche Einwilligung voraus. Ohne Einwilligung werden nur klar als Modell gekennzeichnete Rechnungen veröffentlicht.

## 5. Distribution und verdiente Autorität

Der bestehende Backlink-Scout, das CRM und Link-Assets sind Vorbereitung; sie sind kein Outreach-Ergebnis. Der dokumentierte CRM-Stand enthält Prospects, aber keine belegten Kontaktaufnahmen oder gewonnenen redaktionellen Links.

### Menschlich ausgeführte Wochenkadenz

- **1. Slot:** eine hilfreiche, fachlich passende Community-Antwort ohne Link, sofern kein Link zur Lösung nötig ist.
- **2. Slot:** ein individueller Digital-PR-Pitch mit einem konkreten, zitierbaren Befund und direkter Quellen-/Methodikseite.
- **3. Slot:** ein Folgekontakt oder eine redaktionelle Kooperation nur bei echter Passung.
- **CRM-Pflege:** Status und Datum unmittelbar nach der Handlung aktualisieren; Absenden bleibt manuell.

Die Kapazitätsgrenze des bestehenden Backlink-Plans bleibt bei fünf Aktionen pro Woche. Kein Linkkauf, Linktausch, Massenkommentar oder automatisches Versenden. Ein Prospect, ein vorbereitetes Pitch-Paket oder ein wöchentlicher Bot-Lauf zählt nicht als gewonnener Link.

**Erfolgsmessung:** tatsächlich versandte individuelle Kontakte, Antworten, redaktionelle Erwähnungen/Links, Referral-Sitzungen (sobald zulässige Reichweitenmessung besteht) und resultierende Markensuchen. Keine DA-Zielwerte als Ersatz für Leserwirkung.

## 6. Publikationskadenz und Skalierung

**Kurzfristig gilt Bestandsoptimierung vor Mengenwachstum.** Die Content-Engine darf nicht als Erfolg gezählt werden, nur weil sie Entwürfe produziert.

Vor einer Erhöhung des Publikationstempos müssen alle Bedingungen erfüllt sein:

1. Zwei vollständige, frische Messzyklen; Business-Messbarkeit ist nicht mehr `unbekannt`.
2. Kernseiten des priorisierten Clusters sind redaktionell und fachlich geprüft; unbelegte Fallstudien und Zahlen sind entfernt.
3. Die passenden CTAs sind im Intent-Report sauber; abweichendes Cross-Selling ist mit sichtbarem Kontext begründet.
4. Für die Veröffentlichung neuer Artikel liegt eine konkrete Suchabsicht vor, die kein vorhandener Artikel ausreichend abdeckt.
5. Distribution wird pro Woche tatsächlich ausgeführt und im CRM protokolliert.
6. Ein neuer Artikel wird mindestens vier Wochen beobachtet, bevor die Kadenz erhöht wird. Bewertet werden organische Impressionen/Klicks, qualifizierte Affiliate-Klicks und bestätigte Partnerergebnisse – getrennt, mit Quellen und Zeiträumen.

**Takt für die ersten vier Wochen:** ein fokussierter Bestandsartikel pro Woche überarbeiten, eine reale Mess-/Belegaufgabe bearbeiten und Distribution manuell ausführen. Keine automatische Erhöhung der Artikelzahl. Erst danach entscheidet ein gemeinsamer Review anhand der tatsächlichen Daten.

## Offene Betreiberaktionen (nicht durch Code vortäuschen)

- [ ] Cloudflare-Worker/D1 produktiv einrichten und eigene Domain verifizieren.
- [ ] Datenschutzprüfung und Freigabe der Messung vor `aktiv: true`.
- [ ] Lokale Provisions-CSV aus echten Partner-Abrechnungen befüllen; `provisionen_check.py` und Offline-Import ausführen.
- [ ] Standby-Messreihe real durchführen; Messgerät, Zeitraum und Rohwerte dokumentieren.
- [ ] Erste Outreach-Kontakte persönlich prüfen, versenden und CRM danach aktualisieren.

## Gate-Snapshot (28.10.2026)

- Hugo Extended 0.168.0: Build erfolgreich (110 Seiten, 17 Paginator-Seiten); ausschließlich lokaler Prüfbuild, kein Deploy.
- Metadaten-Wache: 107 Dateien, 0 Befunde. Offenlegung O1–O7: 76 Seiten geprüft, 75 mit Partnerlinks, 20 Ziele offengelegt.
- Affiliate-Integrität: 69 Live-Artikel, 0 Struktur- und 0 Render-Funde. Intent-Wache: 107 Artikel / 248 Gateway-Links, 0 blockierend; 10 IW2-Hinweise zu generischen End-CTAs bleiben manuell zu prüfen.
- Redirects: 251 Seiten stimmen mit der Quelle überein; 7 bewusst 404, 104 Live-URLs.
- Bestands-Gate im nichtdestruktiven Dry-Run: 69 Live-Artikel, 0 Befunde, 0 Auswertungsfehler. Die strengere Release-Scorecard ist **nicht vollständig grün**: 56/69 freigabe-reif, 10 durch saisonal fällige Faktenprüfung blockiert, 3 mit nicht-blockierender Zeichenlängenwarnung. Diese Faktenchecks brauchen aktuelle Belege; nicht per Datum oder Code „auffrischen“.
- Redaktion: veröffentlichter Bestand 69 Artikel, 0 Hochrisiko-Funde. Gesamtprüfung: 100 Artikel, davon 10 Hochrisiko; 3 freigegeben und 7 Entwürfe weiterhin blockiert. Diese Entwürfe bleiben unveröffentlicht.
- Der Revenue-Funnel bleibt **UNBEKANNT – KEINE GESCHÄFTSMESSUNG** (0/2 Quellen). Kein Produktiv-Worker, keine Abrechnungsdaten.

Im QA-Lauf wurden außerdem fehlerhafte relative SVG-Pfade (`abbildung-merkkarte. svg` / `abbildung-ablauf. svg`) in 20 Bestandsartikeln korrigiert; jedes Ziel wurde vor Änderung gegen die jeweilige lokale SVG-Datei geprüft. Das senkte die technischen Release-Blocker, ersetzt aber keine der noch offenen Quellenprüfungen.

**Referenzläufe:** `npm run mess:status` · `python3 scripts/revenue_funnel.py --print` · `python3 scripts/affiliate_intent_guard.py --dry-run --json` · `python3 scripts/backlink_automation.py --selftest` · `python3 scripts/editorial_review_gate.py --published --strict`. 
