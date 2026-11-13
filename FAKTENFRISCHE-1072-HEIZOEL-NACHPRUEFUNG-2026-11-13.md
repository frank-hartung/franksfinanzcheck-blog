# Faktenfrische #1072 – Heizöl-Nachprüfung und Rückfallkorrektur

**Stand:** 13.11.2026 · **Umfang dieser Runde:** 5 Heizöl-Fachbefunde auf einem
zurückgestellten Entwurf · **Ergebnis:** 5 erneut am aktuellen Text entschieden;
**150 andere offene Befunde bleiben offen.**

## Warum eine weitere Runde nötig war

Die Erstentscheidungen vom 05.11. und Folgeentscheidungen vom 07.11. hatten die
fünf Heizöl-Befunde als behoben dokumentiert. Die Begründungen behaupteten,
dass die Saisonbehauptung, die Ersparnisspanne, 0,80 €/Liter, die 15-%-Mehrkosten
und die 4-Wochen-Regel entfernt oder sauber als Modell gekennzeichnet seien.
Der am 13.11. vorliegende Entwurf widerlegte diese Begründungen: Er enthielt
die beanstandeten Werte und Saisonratschläge weiterhin. Ein
Bundesnetzagentur-Überblick war dafür kein fachlicher Beleg.

Die Redaktionsakte erkannte die neue Textfassung und öffnete die Befunde
ordnungsgemäß erneut. Die Schwachstelle lag nicht im Öffnungsmechanismus,
sondern in der falschen früheren redaktionellen Entscheidung. Dieser Lauf
korrigiert den Text und die Entscheidungskette, nicht den Alarm.

## Was geändert und wie entschieden wurde

| Befund | Korrektur im heutigen Entwurf | Entscheidung |
|---|---|---|
| `0b564f460c41218244bd` | Empfehlung eines Januar-/Februar-Tiefpunkts entfernt | Streichung; keine passende, datierte Preisreihe im Bestand |
| `3ad2eefed314eb172c26` | 10–20-%-Ersparnisspanne und Herbst-/Frühbestellversprechen entfernt | Streichung; keine pauschale Ersparnis behauptet |
| `43788c2cdcdfda52e753` | 0,80-€/Liter-Tiefpreis und daraus abgeleitete Beispielrechnung entfernt | Streichung; nur noch eine Formel mit konkreten, individuellen Angebotswerten |
| `5eedec8afbdef6a4ca49` | pauschale „bis zu 15 % Mehrkosten“ entfernt | Streichung; Fehler sind qualitative Prüfschritte, keine bezifferten Folgen |
| `81881c5bc61824d25f5a` | 4-Wochen-/12-Monatsregel und Tiefpunkt-Prognose entfernt | Streichung; Erinnerungsroutine ist ausdrücklich keine Marktregel |

Die Quelle wurde **nicht** durch einen anderen, ebenfalls unpassenden Link
ersetzt. Im aktuellen Entwurf gibt es keine Marktpreis- oder Saisonbehauptung,
die einen externen Beleg vortäuscht. Die fünf Folgeentscheidungen sind mit
`belegtyp: streichung` und `beleg_url: null` im Register dokumentiert und im
Ledger an den Text-Hash `ce7dd8c5ef0a596abbc4628c7be2878fc8ef9ded0c9acbbf3ff7cb29bc1ed602`
gebunden. Die Erstfassungen und ihre Entscheidungen bleiben in der Historie
erhalten.

## Veröffentlichungsschutz

Der Artikel bleibt `draft: true`, `reserve: true`, mit redaktionellem Status
`ausstehend`. Der Text sagt ausdrücklich, dass Quellenprüfung und
redaktionelle Abnahme vor einer Veröffentlichung noch ausstehen. Es gibt weder
einen sachfremden `/go/`-CTA noch eine erfundene Heizöl-Partnerroute.

Das ist eine Textkorrektur und eine fassungsgebundene Redaktionsentscheidung,
**keine** fachliche Freigabe des Artikels oder eine Veröffentlichungserlaubnis.

## Dauerhafter Rückfallschutz

`scripts/tests/test_faktenfrische_1072_heizoel.py` schützt die Korrektur auf
drei Ebenen: die beanstandeten Marktwerte und Saisonregeln dürfen nicht
zurückkehren; der Entwurf muss im Draft-/Reserve-Hold ohne sachfremde Affiliate-
Route bleiben; alle fünf Befund-IDs müssen durch die aktuellen, fassungsgebundenen
Entscheidungen geschlossen sein. Der bestehende #1072-Registertest prüft zudem
Anker, verbotene Behauptungen, Streichungs-Belegparität und die Bindung des
Register-Hashes an den aktuellen Text.

## Nachweis

- `python3 -m unittest scripts.tests.test_faktenfrische_1072 scripts.tests.test_faktenfrische_1072_heizoel` — **15 Tests grün**.
- `python3 scripts/faktenfrische_befund_ledger.py --selftest` — grün.
- `python3 scripts/faktenfrische_befund_ledger.py --struktur-pruefen` — **296 Einträge, 0 doppelte Schlüssel**.
- `python3 scripts/faktenfrische_befund_akte.py --schreiben` — **150 offene Befunde auf 38 Seiten**, davon 24 live; vor dieser Runde waren es 155 auf 39 Seiten. Der Rückgang um fünf entspricht genau den fünf hier bearbeiteten Befunden.

## Grenze dieser Runde

Die 150 übrigen Befunde wurden weder geprüft noch geschlossen. Insbesondere
sind „Text seit dem Befund geändert“ und „Altbestand ohne Fassungs-Hash“ keine
Belege dafür, dass der heutige Text fachlich korrekt ist. Eine weitere
Redaktionsrunde muss die betroffenen aktuellen Texte samt jeweils passender
Quelle prüfen oder unbelegte Aussagen konkret streichen. Issue #1072 bleibt
deshalb offen; ein grüner Teilbereich wird nicht als vollständige Erledigung
ausgegeben.
