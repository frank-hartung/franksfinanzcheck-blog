# Erhebungsprotokoll: Standby-Verbrauch im Haushalt

**Beweisregister-ID:** `ms-standby-haushalt-2026`  
**Status:** geplant / in Erhebung – **keine Ergebnisse liegen diesem Dokument zugrunde**.  
**Geplante Veröffentlichung:** erst nach Messung, Gegenprüfung und Datensatz-Review.

## Forschungsfrage

Welche elektrische Wirkleistung nehmen die vorab festgelegten Gerätegruppen im definierten Bereitschafts- bzw. Aus-Zustand in einem dokumentierten Haushalt auf – und welche Modellkosten ergeben sich daraus bei einem klar benannten Strompreis?

Die Erhebung beschreibt ausschließlich die gemessenen Geräte und Bedingungen. Ein einzelner Haushalt ist keine repräsentative Stichprobe und erlaubt keine Verallgemeinerung auf „deutsche Haushalte“.

## Vorab festgelegter Messumfang

Gerätegruppen laut Beweisregister: Router, Fernseher, Spielekonsole, Kaffeevollautomat, Mikrowelle, PC mit Monitor, Soundbar, Drucker, Ladegeräte und Smart-Home-Hub.

Je Gruppe werden Gerätemodell/-generation, Anschlusskonfiguration, Zustand (Standby/Aus), Messgerät und Messzeitraum vor der Erhebung protokolliert. Seriennummern, WLAN-Namen, Nutzernamen und andere personenbezogene Kennungen werden nicht veröffentlicht.

## Messablauf

1. **Messgerät dokumentieren:** Hersteller, Modell, Messbereich, ausgewiesene Genauigkeit, Prüf-/Kalibrierhinweis und Auflösung festhalten. Die Herstellerangabe ist keine unabhängige Kalibrierung.
2. **Aufbau dokumentieren:** Gerät direkt oder über Mehrfachsteckdose? Welche weiteren Verbraucher hängen mit daran? Netzteile und Ladegeräte werden eindeutig zugeordnet.
3. **Messzeit festlegen:** bis zu 14 vollständige Tage pro Gerätegruppe; Start und Ende mit Datum/Uhrzeit aufzeichnen. Bei wechselnder Nutzung zusätzlich Nutzungszustände notieren.
4. **Ablesungen sichern:** mindestens drei vorab terminierte Leistungsablesungen je Gerätegruppe und Zustand; Originalanzeige fotografieren, wenn keine Personen-/Wohnungsdaten sichtbar sind. Rohwert und Einheit unverändert übernehmen.
5. **Ausreißer nicht still löschen:** Abweichungen, Unterbrechungen, Reset, Messbereichsüberschreitung und Gerätewechsel mit Zeitstempel protokollieren. Ausschluss nur mit dokumentiertem Grund.
6. **Rechnung unabhängig nachprüfen:** Zweitperson kontrolliert Datensatz, Einheiten, Hochrechnung und Veröffentlichungstext gegen die Rohbelege.

## Auswertungsregeln

- Keine Rundung vor der letzten Darstellungsstufe.
- Die Umrechnung `kWh = Watt × Stunden ÷ 1.000` wird mit den tatsächlich erfassten Stunden berechnet.
- Eine Jahreshochrechnung ist eine **Modellhochrechnung**, keine Messung eines ganzen Jahres. Für eine lineare Hochrechnung muss der beobachtete Zustand als repräsentativ für die angesetzten Stunden begründet werden; andernfalls keine Jahreszahl veröffentlichen.
- Kosten werden getrennt ausgewiesen: gemessene Energie/Leistung einerseits, angenommener Preis andererseits. Der Preis bekommt Quelle, Standdatum und Einheit; Grundpreis wird nicht als variabler Preis pro kWh ausgegeben.
- Ein Eurobetrag wird nur als Szenario bei dieser Preisannahme bezeichnet. Kein Betrag wird als „garantierte Ersparnis“ oder Einsparversprechen formuliert.
- Standby- und Aus-Zustand bleiben getrennte Zeilen. Die Differenz ist keine automatische Verbrauchsreduktion: tatsächliche Nutzungsdauer und Folgen des vollständigen Trennens sind individuell.

## Rohdaten-Schema

Vor der Veröffentlichung ist ein versionierter, maschinenlesbarer Datensatz mit mindestens diesen Feldern anzulegen:

| Feld | Inhalt |
|---|---|
| `mess_id` | stabile, nicht personenbezogene Kennung |
| `geraetegruppe` | vorab festgelegte Kategorie |
| `geraet_modell` | öffentliches Modell oder „nicht veröffentlicht“ mit Grund |
| `zustand` | `standby` oder `aus` |
| `messgeraet` | Hersteller/Modell und technische Angaben |
| `start_utc`, `ende_utc` | Messfenster in ISO-8601 |
| `ablesung_utc` | Zeitpunkt der Rohablesung |
| `leistung_w` | angezeigter Rohwert in Watt, Dezimalpunkt |
| `messdauer_h` | dokumentierte Dauer, falls Energiemenge statt Momentanleistung gemessen wird |
| `qualitaetshinweis` | Messbereich, Abbruch oder dokumentierte Besonderheit; leer, wenn keine |
| `strompreis_eur_kwh` | separat versionierter Preisannahmewert, nicht Bestandteil der Geräte-Rohmessung |
| `strompreis_quelle`, `strompreis_stand` | Quelle und Abrufdatum |

Rohbelege bleiben intern, wenn sie Seriennummern, Standortdaten oder sonstige identifizierende Informationen enthalten. Veröffentlicht werden nur bereinigte Messwerte und Methodik. Die Lizenz der öffentlichen Tabelle wird im Datensatz ausdrücklich festgelegt.

## Freigabe vor Veröffentlichung

- [ ] Mindestmessdauer und drei Ablesungen erfüllt oder jede Abweichung begründet.
- [ ] Rechenweg, Einheiten, Summen und Rundungen von einer zweiten Person nachgerechnet.
- [ ] Kein Rohbeleg enthält persönliche oder sicherheitsrelevante Informationen.
- [ ] Text bezeichnet Szenarioannahmen als Annahmen und Einzelfall als Einzelfall.
- [ ] `data/beweise/register.yaml` bleibt bis zur vollständigen Prüfung auf `in-erhebung`.
- [ ] Datensatz, Artikel, Quelle und Beweisregister werden gemeinsam aktualisiert.
- [ ] Fassungssiegel und Änderungsprotokoll folgen dem bestehenden Beweis-Gate.

**Wichtig:** Dieses Protokoll dokumentiert ein geplantes Vorgehen. Es ist selbst kein Nachweis dafür, dass eine Messung stattgefunden hat.
