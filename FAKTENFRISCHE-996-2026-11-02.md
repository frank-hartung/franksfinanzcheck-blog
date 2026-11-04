# Faktenfrische #996: Gasartikel und Prüfpfad

Stand 2. November 2026. Der Issue-Lauf meldete 16 neue Befunde für vier
Artikel. Die allgemeine BNetzA-Themenübersicht im automatischen Dossier ist
kein Beleg für konkrete Preise, Heizsparwerte oder Kündigungsfristen. Eine
fehlende Angabe dort widerlegt umgekehrt nicht automatisch eine Aussage.
Die Änderungen unten sind redaktionelle Korrekturvorschläge, keine menschliche
fachliche Freigabe und kein neuer vollständiger Faktencheck.

## Belege und Entscheidung

- [BNetzA: Preise und Abschläge](https://www.bundesnetzagentur.de/DE/Vportal/Energie/PreiseAbschlaege/start.html): grundsätzlich ein Monat Vorankündigung für Haushaltskunden, Inhalt der Mitteilung, Sonderkündigung und relevante Ausnahmen; zusätzliche Anforderungen in der Grundversorgung.
- [BNetzA: Arten der Energiebelieferung](https://www.bundesnetzagentur.de/DE/Vportal/Energie/Vertragsarten/start.html): unterschiedliche Zuordnung zur Grund- oder Ersatzversorgung je nach Situation; kurze Wechselverzögerung als Beispiel für Ersatzversorgung.
- [Verbraucherzentrale: Heizung – 10 Tipps](https://www.verbraucherzentrale.de/wissen/energie/heizen-und-warmwasser/heizung-10-einfache-tipps-zum-heizkosten-sparen-13892): ungefähr 6 % Heizenergie je Grad und 10–15 % für eine richtig eingestellte Heizungsanlage. Letzteres ist kein pauschaler Wert für alle Sparmaßnahmen oder die gesamte Gasrechnung.

Die Zahlen 11,93 ct/kWh und 360 € waren nicht durch die im Issue genannte
Quelle belegt; statt sie als unbestimmten Marktdurchschnitt weiterzugeben,
wurden sie entfernt. Ebenso entfernt: behauptete aktuelle Preisspannen und
eine saisonale Preisprognose. Rechenbeispiele bleiben als Annahmen und ohne
Marktbehauptung erhalten. 18.000 kWh ist keine Aussage über den typischen
Verbrauch; der persönliche Rechnungswert ist maßgeblich.

## Alle 16 Befunde aus dem Lauf

| Artikel vom | Befund-ID | Behandlung |
|---|---|---|
| 10.08. | `7bdec96c0329769bebe6` | Unbelegte aktuelle Preisbereiche entfernt; Tarifbeispiel als Rechnung erhalten. |
| 10.08. | `a56734aa032e0ed9e0c4` | Mitteilungspflicht, Sonderkündigung, Ausnahmen und BNetzA-Beleg ergänzt. |
| 10.08. | `124ff2c3cd3917c274aa` | „Die besten Tarife“ durch neutrale Partnerbeschreibung ersetzt. |
| 12.08. | `c583efe1ce02df3ca2d7` | Unbelegte BNetzA-Ersparnis entfernt. |
| 12.08. | `30caa57be394afb62947` | Unbelegten BDEW-Durchschnitt entfernt. |
| 12.08. | `32a3ea879f2cf126b3a7` | Pflichten bei Preisänderung und Zuordnung bei Lieferlücke mit konkreten BNetzA-Quellen ergänzt. |
| 14.08. | `db8a69f08dc0020adebd` | Behauptung besserer Oktoberpreise und saisonales Werbeversprechen entfernt. |
| 14.08. | `e834f4702e87194affe7` | 18.000 kWh ausdrücklich als Annahme statt als typischen Hausverbrauch gekennzeichnet. |
| 14.08. | `9fbacd9942c2dfa1447f` | 6-%-Faustwert an der Aussage verlinkt und eingeschränkt. |
| 14.08. | `da30cbb5fbc8c801daf0` | Pauschale 10–15 % Gaskostensenkung entfernt; belegten Wert auf Einstellung der Anlage begrenzt. |
| 14.08. | `437b809ffbf41e5af434` | BNetzA-Quelle ergänzt und Grund-/Ersatzversorgung fallbezogen unterschieden. |
| 24.08. | `252413dcc16cea146beb` | Monatsfrist und Informationspflichten mit konkretem BNetzA-Beleg präzisiert. |
| 24.08. | `ab4d084fd367c8e4d518` | Unbelegten BDEW-Durchschnitt entfernt. |
| 24.08. | `d215addd22dea72c44df` | 6-%-Faustwert direkt mit Verbraucherzentrale verlinkt. |
| 24.08. | `9326152f4d788cff56bd` | Kündigung zum Zeitpunkt der Änderung, Vertragsende am Vortag und Ausnahmen konkretisiert. |
| 24.08. | `48a0a962046c8315270e` | Garantie auf vertraglich geschützte Bestandteile begrenzt; Aufpreis nicht als üblich behauptet. |

Zusätzlich wurden ähnliche Werbe-Superlative, unzutreffende pauschale
Kündigungs- und Versorgungsbehauptungen sowie ein Rechenfehler im ersten
Artikel korrigiert: 0,4–0,8 ct × 18.000 kWh = 72–144 €, nicht durchweg
über 100 €. Die Pin-Texte wurden mitbereinigt.

## Dauerhafter Betrieb und offener Freigabeschritt

`scripts/tests/test_faktenfrische_996.py` schützt die vier Seiten vor den
konkreten Rückfällen, prüft Beleglinks und Rechenwege und läuft sowohl mit
`npm run test:faktenfrische` als auch im Deploy vor dem Publish-Gate. Das ist
ein Rückfallschutz, kein Ersatz für Quellenprüfung, Rechtsberatung oder eine
vollständige Faktenprüfung. Bei einer späteren, tatsächlich belegten neuen
Zahl sind Artikel und Test gemeinsam fachlich zu überprüfen.

`lastmod` wurde für die wesentlichen Textänderungen gesetzt; `faktencheck`
bleibt auf dem bisherigen Datum des automatischen Laufs. Die Queue und
`data/faktenfrische_entscheidungen.yaml` wurden bewusst nicht verändert:
das Ledger verlangt eine dokumentierte **menschliche** Entscheidung und
bindet diese an den Fassungs-Hash des Ledger-Eintrags. Die 16 Befunde bleiben
daher bis zu einem passenden erneuten Prüf-/Ledgerstand und einer manuellen,
fassungsgebundenen Entscheidung offen. Keine Freigabe oder Schließung wurde
vorgegeben. Die übrigen älteren Befunde im Issue sind nicht Gegenstand dieser
16er-Bearbeitung und bleiben ebenfalls offen.

## Nachtrag 03.11.2026 – Pin-Sync-Rückfall

Im Checkout waren die zwei Pin-Beschreibungen der Artikel 14.08. und 24.08.
und ihre Einträge im Pinterest-Plan erneut mit unbelegten saisonalen Preis-
und Ersparnisversprechen belegt. Auch zwei weitere Pins zum Artikel vom 14.08.
trugen unbelegte Zahlen bzw. pauschale Sparversprechen. Frontmatter und alle
vier Planeinträge wurden neutralisiert; der bestehende Rückfallschutz prüft
jetzt zusätzlich die Planquelle, aus der der tägliche Sync schreibt. Die
lokale Testsuite ist grün; das ist keine Bestätigung eines neuen Deployments.

## Einordnung 04.11.2026

Bei der Übernahme von #1051 wurden die inzwischen auf dem Ausgangsstand
redaktionell überarbeiteten Texte und die Synchronisationssperre beibehalten.
Die Planeinträge dürfen deshalb vom Frontmatter abweichen; der Test prüft
Sperre und unzulässige Aussagen statt Textidentität.
