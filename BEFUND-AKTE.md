# BEFUND-AKTE – offene Fachbefunde der Faktenfrische

_Stand 2026-11-18 · erzeugt von `scripts/faktenfrische_befund_akte.py` · Quelle: `data/faktenfrische_queue.json` + `data/faktenfrische_entscheidungen.yaml` (eine Regel, zwei Leser)._

**213 offene Befunde auf 56 Seiten · davon 35 Live-Seiten mit 129 Befunden · ältester 19 Tage · Frist 14 Tage.**

| Kennzahl | Wert |
|---|---|
| Offene Befunde | 213 |
| Seiten betroffen | 56 (davon live: 35) |
| Text seit dem Befund geändert | 161 |
| Altbestand ohne Fassungs-Hash | 11 |
| Nicht entscheidbar (Seite fehlt) | 0 |
| Über der Frist (14 Tage) | 48 |
| In Eskalation (21 Tage) | 0 |

## So schließt du einen Befund

1. **Text und Beleg prüfen.** Mangel korrigieren (Zahl belegen oder entfernen, Aussage präzisieren) oder den Befund fachlich begründet zurückweisen. Der Text ist redaktionell – die Maschine schreibt ihn nie.
2. **Entscheidung dokumentieren** (eine Zeile, bindet an den heutigen Text und an genau diesen Befund):

   ```bash
   python3 scripts/faktenfrische_befund_ledger.py --entscheiden <BEFUND-ID> --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
   ```

3. **Akte und Messung nachziehen:**

   ```bash
   python3 scripts/faktenfrische_befund_akte.py --schreiben
   python3 scripts/release_scorecard.py --live --streng
   ```

Ein neues `faktencheck`-Datum schließt **keinen** Befund (F4 ≠ F1). Und: Ein Befund ist an den **Text** gebunden, nicht an die Quellen – eine automatische Quellenpflege öffnet keine erledigte Entscheidung, eine Textänderung dagegen schon.

> **Wichtig – betrifft 172 von 213 Befunden** (in der Tabelle als Fassung markiert): Der Text ist seit dem Befund bereits geändert worden (Heilung) oder stammt aus dem Altbestand. Die Entscheidung bezieht sich ausdrücklich auf den HEUTIGEN Text – bitte diesen lesen, nicht den alten Befund abnicken. Diese Prüfung kann dir die Maschine nicht abnehmen – sie darf sie aber auch nicht verhindern.

## Seiten

### `2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `124ff2c3cd3917c274aa` | praezision | 17 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Bewerbung des Vergleichsportals mit dem Superlativ 'Die besten Tarife' erfolgt ohne messbare Daten oder Auswahlkriterien in der Recherchegrundlage. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `7bdec96c0329769bebe6` | luecke | 17 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die im Artikel als Fakten genannten Gaspreise für Oktober 2026 (11 bis 13 Cent/kWh) sind nicht durch die Fundstelle belegt, die lediglich eine allgemeine Themenübersicht darstellt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `a56734aa032e0ed9e0c4` | luecke | 17 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der für den Verbraucherschutz zentrale Regulierungsrahmen (Sonderkündigungsrecht, Informationspflichten der Versorger) wird in der Fundstelle nicht inhaltlich bestätigt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 124ff2c3cd3917c274aa --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7bdec96c0329769bebe6 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a56734aa032e0ed9e0c4 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `30caa57be394afb62947` | luecke | 17 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Für den angeführten BDEW-Durchschnittspreis von 11,93 Cent/kWh fehlt in den Recherche-Fundstellen ein entsprechender Beleg. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `32a3ea879f2cf126b3a7` | luecke | 17 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel lässt den in der Quelle explizit genannten Regulierungsrahmen der 'Unternehmenspflichten' unerwähnt, der für den Schutz der Verbraucher beim Anbieterwechsel zentral ist. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `c583efe1ce02df3ca2d7` | luecke | 17 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die im Artikel genannte Ersparnis-Berechnung der Bundesnetzagentur für Januar 2026 (360 €) wird durch die allgemeine Übersichtsseite der Behörde nicht gestützt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 30caa57be394afb62947 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 32a3ea879f2cf126b3a7 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden c583efe1ce02df3ca2d7 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen` · **LIVE** (blockiert) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `252413dcc16cea146beb` | luecke | 17 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel behauptet, dass eine Preisänderung meist einen Monat vorher angekündigt werden muss, ohne dafür eine Quelle anzugeben. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `48a0a962046c8315270e` | praezision | 17 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Behauptung, dass eine Preisgarantie einen Teil des Risikos auf den Anbieter überträgt und dafür ein höherer Startpreis üblich ist, fehlt eine konkrete Quelle und bleibt vage. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `9326152f4d788cff56bd` | praezision | 17 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass man „in der Regel“ zum Zeitpunkt der Preisänderung Sonderkündigungsrecht hat, ist unpräzise und wird nicht durch eine konkrete Regelung belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `ab4d084fd367c8e4d518` | luecke | 17 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der angegebene durchschnittliche Gaspreis von 11,93 Cent/kWh für 2026 (laut BDEW) wird nicht durch eine Quelle belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `d215addd22dea72c44df` | luecke | 17 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Angabe, dass die Verbraucherzentrale etwa 6 % weniger Heizenergie pro Grad niedrigerer Raumtemperatur nennt, fehlt eine Quellenangabe. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 252413dcc16cea146beb --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 48a0a962046c8315270e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 9326152f4d788cff56bd --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ab4d084fd367c8e4d518 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d215addd22dea72c44df --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-20-gasrechnung-senken-so-bereitest-du-dich-im-spaetsommer-vor` · **LIVE** (blockiert) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-09-20-gasrechnung-senken-so-bereitest-du-dich-im-spaetsommer-vor/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `0aa915539d57841e5014` | luecke | 16 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass die Verbraucherzentrale empfiehlt, Boni im ersten Vergleich auszublenden, fehlt eine Quellenangabe. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `5e1be48085014a836807` | luecke | 16 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der angegebene BDEW‑Durchschnittspreis von 11,93 Cent/kWh für 2026 wird nicht belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `6fdf31c3b68b6122bd0d` | praezision | 16 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die pauschale Formulierung, dass bei zentraler Heizung der Vermieter oder die Eigentümergemeinschaft den Anbieter wählt, ist zu ungenau und nicht belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `c27c182c615bd7ca3b78` | luecke | 16 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel behauptet, dass laut Bundesnetzagentur Preisänderungen klar angekündigt und begründet sein müssen, liefert jedoch keinen Beleg dafür. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `e1e40e9bbbdd109df86e` | luecke | 16 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Es wird angegeben, dass bei einer Preisänderung in der Regel ein Sonderkündigungsrecht besteht, ohne dafür eine Quelle zu nennen. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 0aa915539d57841e5014 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 5e1be48085014a836807 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6fdf31c3b68b6122bd0d --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden c27c182c615bd7ca3b78 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e1e40e9bbbdd109df86e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-20-gasrechnung-senken-spaetsommer-check-spart-hunderte-euro` · **LIVE** (blockiert) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-09-20-gasrechnung-senken-spaetsommer-check-spart-hunderte-euro/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `334751e6f61ad0033fe4` | luecke | 16 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Angabe, dass ein Gaslieferantenwechsel bei 20.000 kWh im Januar 2026 im Schnitt etwa 360 € spart, fehlt jede Quellenangabe. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `36759a5efe5e8e5163d0` | luecke | 16 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Faustregel der Verbraucherzentrale, dass pro Grad weniger Raumtemperatur der Heizbedarf um etwa 6 % sinkt, wird ohne Quelle angegeben. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `942922d1afd7844618e9` | luecke | 16 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Rechnung „1 Cent pro kWh bei 18.000 kWh Jahresverbrauch ergibt rund 180 € im Jahr“ wird nicht belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `d41f0d5ce8798df0211b` | praezision | 16 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage „Die besten Tarife findest du über unseren Partner‑Vergleich“ ist ein Superlativ ohne messbare Daten oder Vergleichskriterien. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `e139d0769faadd04392a` | luecke | 16 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der BDEW‑Durchschnittspreis von 11,93 Cent/kWh für 2026 wird ohne Quellenangabe genannt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 334751e6f61ad0033fe4 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 36759a5efe5e8e5163d0 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 942922d1afd7844618e9 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d41f0d5ce8798df0211b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e139d0769faadd04392a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-02-weihnachten-budget-planen-ohne-schulden-durch-die-feiertage` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-10-02-weihnachten-budget-planen-ohne-schulden-durch-die-feiertage/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `58f03a64adaaf8125959` | praezision | 15 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Während der Artikel vor hohen Kosten für Festmenüs warnt, liegt die Preissteigerung bei Nahrungsmitteln laut Destatis im Oktober 2026 bei lediglich +0,4 % und damit deutlich unter der allgemeinen Inflation. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `a7f5f01ef15a38839a0d` | praezision | 15 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Pauschale für 'Anreise und Mobilität' (10 % des Budgets) berücksichtigt nicht die überdurchschnittliche Preissteigerung bei Energie von +14,9 %, die Fahrtkosten im Vergleich zum Vorjahr massiv verteuern kann. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `bcc2bdf06220d5097133` | luecke | 15 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Modellrechnung für das Weihnachtsbudget (600 €) lässt die aktuelle Teuerungsrate unberücksichtigt. Laut Statistischen Bundesamt liegt die Inflationsrate im Oktober 2026 bei +2,8 %, was als Referenzwert für die Budgetplanung zum Vorjahr fehlt. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 58f03a64adaaf8125959 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a7f5f01ef15a38839a0d --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden bcc2bdf06220d5097133 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `089b89138417e63a3dcf` | luecke | 15 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Es fehlt der für Campingbuchungen relevante Regulierungsrahmen (Unterscheidung Mietrecht bei Stellplätzen vs. Reiserecht), den die Fundstelle für den Bereich Reise nur allgemein andeutet. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `1158934e7a18c7b2099b` | luecke | 15 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Preisangabe von 20 bis 45 € pro Nacht wird als realistischer Wert positioniert, ist jedoch nicht durch Marktdaten oder eine Referenzstelle in den Fundstellen belegt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `3716cfd3ab5aec6d774b` | praezision | 15 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Verweis auf die Verbraucherzentrale zur Prüfung von Buchungsangaben führt auf eine allgemeine Übersichtsseite ohne konkrete Checklisten für Camping-Angebote. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 089b89138417e63a3dcf --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 1158934e7a18c7b2099b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 3716cfd3ab5aec6d774b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen` · **LIVE** (blockiert) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `7067eabb89a917ae67a4` | luecke | 15 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Verbraucherzentrale sammelt Hinweise zu Reisebuchungen, auch zu unklaren Angeboten und Problemen mit Online-Buchungen. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `af2ccb4222eeb195222f` | praezision | 15 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Ein Mietwagenvergleich kann Angebote sichtbar machen, prüft aber nicht automatisch, ob das Auto zum individuellen Urlaub passt – ohne Messgröße bleibt die Aussage ungenau. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `d9c8b522bf1dcaed0340` | luecke | 15 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Verbraucherzentrale beschreibt, dass sich eine Pauschalreise unter bestimmten Bedingungen auf eine andere Person übertragen lässt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `e2975509f3f130de0755` | luecke | 15 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Verbraucherzentrale empfiehlt, größere Ausgaben vorauszuplanen und das eigene Budget im Blick zu behalten. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `f1704e45e970a8f4b078` | luecke | 15 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Bei einer Pauschalreise gilt die Mitteilung als rechtzeitig, wenn sie dem Veranstalter spätestens sieben Tage vor Reisebeginn zugeht (§ 651e BGB). | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7067eabb89a917ae67a4 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden af2ccb4222eeb195222f --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d9c8b522bf1dcaed0340 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e2975509f3f130de0755 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f1704e45e970a8f4b078 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `3fe383f6d452737f66f2` | praezision | 14 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die im Teaser und Text genannten monatlichen Ersparnisse von 350 € bis 600 € werden als Marktfakten ohne Quellenbeleg oder methodische Herleitung (z. B. Referenzhaushalt des Statistischen Bundesamtes) angeführt. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `7bba759bbb4ca14c7f35` | luecke | 14 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Ratgeber empfiehlt Tarifwechsel bei Energie zur Kostensenkung, verschweigt aber den aktuellen Markttrend massiv steigender Energiepreise (+14,9 %), was die Kalkulation der 50-Prozent-Fixkostenquote gefährdet. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `e8e32a383b6f803cc8d4` | veraltet | 14 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Einschätzung zur Inflation ist unpräzise: Die aktuelle Inflationsrate liegt laut Destatis bei +2,8 % (Oktober 2026), wodurch die genannten Tagesgeldzinsen von 0,5 % bis 1,5 % den Wertverlust deutlich weniger ausgleichen als suggeriert. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 3fe383f6d452737f66f2 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7bba759bbb4ca14c7f35 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e8e32a383b6f803cc8d4 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-03-kreditkarte-vergleichen-kostenlos-sicher-bezahlen` · **LIVE** (blockiert) · Risikoklasse erhoeht · 5 Befund(e)

Datei: `content/posts/2026-09-03-kreditkarte-vergleichen-kostenlos-sicher-bezahlen/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `16b3b8584ff802803aa9` | luecke | 14 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Angaben zum Fremdwährungsentgelt von „fast zwei Prozent“ bei Zahlungen in fremder Währung fehlen jede belegbare Referenz. | – |
| `7ff042b6fe804cdf101b` | praezision | 14 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Formulierungen wie „einige Anbieter ohne Auslandsgebühr gehören zu den besten Karten für Reisen“ sind pauschal und ohne messbare Daten unpräzise. | – |
| `bec83c4b814183fa1086` | luecke | 14 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass die kostenlose Sperr‑Notrufnummer 116 für alle Karten in Deutschland gilt, wird nicht durch eine Quelle gestützt. | – |
| `f9aff86b6eba71b153a6` | luecke | 14 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Angabe, dass Sollzinsen bei Teilzahlung zwischen 12 % und 20 % liegen, ist nicht mit einer Quelle belegt. | – |
| `fed9215b770ea4879eda` | luecke | 14 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Behauptung, dass eine gute Kreditkarte im Jahr nichts kostet (keine Jahres‑ und keine Fremdwährungsgebühr), wird ohne jegliche Quelle angegeben. | – |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 16b3b8584ff802803aa9 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7ff042b6fe804cdf101b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden bec83c4b814183fa1086 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f9aff86b6eba71b153a6 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden fed9215b770ea4879eda --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich` · **LIVE** (blockiert) · Risikoklasse standard · 2 Befund(e)

Datei: `content/posts/2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `20c08cb650ef6e24af64` | luecke | 13 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Ratgeber vernachlässigt bei der Kalkulation der Sparfähigkeit die massive Preissteigerung bei Energie (+14,9 %), die das Budget für monatliche Sparraten erheblich belastet. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `6aafb23c0c6dbb06ce3b` | veraltet | 13 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die im Rechenbeispiel zur Realrendite genutzte Inflationsrate von 2 % ist veraltet; die vorläufige Rate für Oktober 2026 beträgt laut Statistischem Bundesamt 2,8 %. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 20c08cb650ef6e24af64 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6aafb23c0c6dbb06ce3b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-07-frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-09-07-frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `24f05ddc03ffdd50118f` | praezision | 13 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Kalkulation der Fixkostenersparnis bei Energie (Strom/Gas) ist unpräzise, da sie den aktuellen Preisanstieg von +14,9 % bei Energieprodukten nicht einbezieht. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `4816322f061dfdc03bcd` | luecke | 13 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Bei den Einsparpotenzialen für Lebensmittel fehlt der Bezug zur aktuellen Preissteigerung von +0,4 % bei Nahrungsmitteln. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `7017065ee7c74c7ae452` | veraltet | 13 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel nutzt Kostenszenarien für 2024/2025, während aktuelle Daten für Oktober 2026 eine Inflationsrate von +2,8 % ausweisen. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 24f05ddc03ffdd50118f --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 4816322f061dfdc03bcd --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7017065ee7c74c7ae452 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-05-waschmaschine-beladen-weniger-kosten-bei-jedem-waschgang` · **LIVE** (blockiert) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-11-05-waschmaschine-beladen-weniger-kosten-bei-jedem-waschgang/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `4284fd2d9c9005e7af8f` | praezision | 13 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Behauptung, dass Überladung der Maschine zu schnellerem Verschleiß und teuren Reparaturen führt, wird ohne konkrete Daten oder Messgröße angegeben. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `84e247f17354e224c973` | praezision | 13 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Aussage, dass das richtige Beladen allein die Fixkosten senkt, ohne weitere Maßnahmen, ist ein pauschales Leistungsversprechen ohne Nennung von Mechanismen oder Grenzen. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `a2a7dc69f10393af6531` | luecke | 13 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Modellrechnung (0,9 kWh/50 L bei vollem Waschgang, 0,6 kWh/35 L bei halbem Waschgang, Strompreis 0,40 €/kWh, Wasserpreis 0,005 €/L) und die daraus resultierende Jahresersparnis von 22 € fehlen einer fundierten Quelle. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `cb794331f1cc0c715a55` | luecke | 13 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass bei 4 Waschgängen pro Woche ein durchschnittlicher Haushalt rund 5 € jährlich an Strom‑ und Wasserkosten spart, ist nicht mit einer Quelle belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `e6729081522126e972c2` | luecke | 13 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Angabe, dass ein optimal beladener Trommel (ca. 80 % Kapazität) bis zu 15 % weniger Wasser und Energie verbraucht, wird nicht durch eine Quelle belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 4284fd2d9c9005e7af8f --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 84e247f17354e224c973 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a2a7dc69f10393af6531 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden cb794331f1cc0c715a55 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e6729081522126e972c2 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-07-frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-09-07-frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `1e06a96f6f71e104ce0b` | praezision | 12 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Während Meal Prep als großer Sparhebel betont wird, zeigt die Marktlage für Nahrungsmittel eine moderate Teuerung von nur 0,4 %, was die Priorisierung der Sparbemühungen relativiert. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `81c6a707139046b83ccd` | luecke | 12 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Ratgeber empfiehlt die Revision von Fixkosten, lässt aber die drastische Preissteigerung bei Energie von +14,9 % unerwähnt, die ein wesentlicher Treiber der Haushaltsausgaben ist. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `8cc00288af8a1f2b02d8` | veraltet | 12 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Budget-Tipps berücksichtigen nicht die aktuelle Inflationsrate von 2,8 % (Stand Oktober 2026), was die Kaufkraft-Annahmen im Haushaltsbuch beeinflusst. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 1e06a96f6f71e104ce0b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 81c6a707139046b83ccd --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 8cc00288af8a1f2b02d8 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `5a1bf10697f58e5fe14a` | luecke | 12 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Ratgeber nennt Sparbeispiele für Heizkosten, lässt aber die aktuelle Preissteigerung bei Energie von +14,9 % (Stand Oktober 2026) unerwähnt, die den finanziellen Druck auf Haushalte massiv erhöht. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `e48f9237cff6397c49a6` | praezision | 12 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die in Aussicht gestellten Ersparnisse von bis zu 200 € werden nicht ins Verhältnis zur aktuellen Inflationsrate von +2,8 % gesetzt, welche die reale Kaufkraft des gesparten Geldes mindert. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `f6de6b078d49f9d42e0e` | praezision | 12 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Beim Fokus auf Lebensmittelplanung fehlt der Hinweis auf die vergleichsweise moderate Preissteigerung von +0,4 % bei Nahrungsmitteln, was diesen Hebel gegenüber den stark steigenden Energiekosten relativiert. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 5a1bf10697f58e5fe14a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e48f9237cff6397c49a6 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f6de6b078d49f9d42e0e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-11-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026` · **LIVE** (blockiert) · Risikoklasse standard · 2 Befund(e)

Datei: `content/posts/2026-09-11-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `6cb2229c5eb83b02da23` | veraltet | 12 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Kalkulation der Fixkosten (Energie 140 €) und die Empfehlung zur Senkung der Kosten ignorieren den aktuellen Markttrend massiv steigender Energiepreise (+14,9 %), was die 50-Prozent-Quote für notwendige Ausgaben gefährdet. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `f00055a1cb65ee22165f` | luecke | 12 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Ratgeber verspricht eine 'planbare' Budgetierung, lässt aber die aktuelle Inflationsrate von 2,8 % unerwähnt, die insbesondere den Block der notwendigen Ausgaben (Nahrungsmittel +0,4 %) dynamisch belastet. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6cb2229c5eb83b02da23 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f00055a1cb65ee22165f --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden` · **LIVE** (blockiert) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `43470330b3b48c9cee49` | luecke | 11 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel empfiehlt, Kühl- und Gefriergeräte mindestens 24 Stunden, besser mehrere Tage zu messen, liefert jedoch keine Quelle für diese Messdauer. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `8ddc1025e45be176ad3a` | luecke | 11 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Es wird kein regulatorischer Rahmen (z. B. Aufgaben der Bundesnetzagentur) genannt, obwohl das Thema Stromversorgung berührt wird; entsprechende Vorgaben fehlen im Text. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `95d6d2877620e5a056ce` | luecke | 11 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass Verbraucherzentralen oder Bibliotheken Messgeräte verleihen, wird ohne Beleg gemacht. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `ab16029999747466a638` | luecke | 11 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Berechnung mit einem Arbeitspreis von 0,37 €/kWh wird angegeben, ohne dass ein aktueller Preis‑ oder Marktwert belegt wird. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `b057dee3603e09f494b5` | luecke | 11 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Das Amortisationsbeispiel (Kaufpreis 650 €, Amortisationszeit 10,3 Jahre) enthält keine Quelle für die zugrunde liegenden Annahmen oder Preise. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 43470330b3b48c9cee49 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 8ddc1025e45be176ad3a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 95d6d2877620e5a056ce --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ab16029999747466a638 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden b057dee3603e09f494b5 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-26-warmwasser-sparen-rechnung-hinter-dem-hahn` · **LIVE** (blockiert) · Risikoklasse erhoeht · 5 Befund(e)

Datei: `content/posts/2026-08-26-warmwasser-sparen-rechnung-hinter-dem-hahn/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `278d89267d9122a1e9d8` | luecke | 11 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Angaben zu gesetzlichen Vorgaben für Warmwassertemperaturen zur Vermeidung von Legionellen werden nicht durch die bereitgestellten Quellen gestützt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `450c3aa629342062825e` | luecke | 11 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass Warmwasser der zweitgrößte Kostenposten im Haushalt ist, wird nicht durch eine der bereitgestellten Quellen belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `7601167c9f3560093fb0` | luecke | 11 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Behauptung, dass Warmwasser in der Heizkostenabrechnung üblicherweise als eigener Block ausgewiesen wird, fehlt eine Quellenangabe. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `7efbcd7a4275fe1577bb` | luecke | 11 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Verweise auf die Verbraucherzentrale (Tipps zum Heizkosten sparen, Heizung optimieren) können nicht mit den angegebenen Fundstellen belegt werden. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `971a719f94ca492f640e` | luecke | 11 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Preis von 0,30 € pro Kilowattstunde in der Modellrechnung ist nicht mit einer Quelle belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 278d89267d9122a1e9d8 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 450c3aa629342062825e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7601167c9f3560093fb0 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7efbcd7a4275fe1577bb --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 971a719f94ca492f640e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-11-standby-kosten-reduzieren-so-entlarvst-du-stromfresser` · **LIVE** (blockiert) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-09-11-standby-kosten-reduzieren-so-entlarvst-du-stromfresser/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `7a87eaaa2b863ba8cc46` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Ein relevanter regulatorischer Rahmen (z. B. Vorgaben der Bundesnetzagentur oder BDEW) wird nicht genannt, obwohl die Fundstelle darauf hinweist, dass solche Vorgaben existieren. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `9d67a5e6bd11212c7c1e` | praezision | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass bestimmte Gerätegruppen (TV‑Ecke, Homeoffice, alte Audio‑Technik) zuerst zu senken „lohnt“, wird ohne messbare Daten oder Vergleichskriterien gemacht. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `a54abc1cad73d20fb689` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die konkreten Jahreskosten (z. B. 32 € für 10 W Standby) beruhen auf dem nicht belegten Strompreis und werden nicht als Modellrechnung gekennzeichnet. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `a7d1cf6485921e117919` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der angegebene durchschnittliche Strompreis von 37,3 Cent/kWh (BDEW‑Schnitt) wird ohne Quellenangabe genannt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `a7f69a854430d62a4a3e` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Empfehlung, dass ein günstigerer Arbeitspreis der zweite wichtigste Hebel sei, fehlt jede Quelle oder regulatorische Einordnung. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7a87eaaa2b863ba8cc46 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 9d67a5e6bd11212c7c1e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a54abc1cad73d20fb689 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a7d1cf6485921e117919 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a7f69a854430d62a4a3e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-30-last-minute-urlaub-so-schnappst-du-dir-das-sommer-schnaepp` · **LIVE** (blockiert) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-09-30-last-minute-urlaub-so-schnappst-du-dir-das-sommer-schnaepp/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `33278b9e7942ebfdbbac` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Definition des Begriffs „Last Minute“ (maximal 14 Tage zwischen Buchung und Abreise) wird mit dem Deutschen Reiseverband angegeben, jedoch fehlt ein Nachweis. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `6ad7358a9afcfef3babb` | praezision | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Angabe, dass Preisalarme keinen Tiefstpreis garantieren, wird nicht durch konkrete Zahlen oder Vergleichsstudien belegt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `7c375a3e1a9bfab1468c` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Hinweis auf § 651r BGB (Insolvenzsicherung bei Pauschalreisen) enthält keinen Verweis auf eine Rechtsquelle oder Verbraucherzentrale‑Information. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `ea11d36614fa115503b4` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Behauptung, dass Nachlässe von bis zu 50 % nur Einzelfälle sind, wird ohne Quellenangabe präsentiert. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `f7b1c869dd8e442eaf16` | praezision | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Aussage, dass der „beste Zeitpunkt zum Buchen“ ein Modellwert sei, bleibt vage und ohne messbare Daten oder Studien untermauert. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 33278b9e7942ebfdbbac --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6ad7358a9afcfef3babb --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7c375a3e1a9bfab1468c --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ea11d36614fa115503b4 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f7b1c869dd8e442eaf16 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-25-strategisch-sparen-so-kannst-du-deine-reisekasse-fuellen` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-10-25-strategisch-sparen-so-kannst-du-deine-reisekasse-fuellen/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `98eb45f772ad7a0aac7b` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Das Sparversprechen von '500 € mehr' in der PIN-Beschreibung nutzt im Text Referenzwerte (120 € Strom, 80 € Kfz), für die in der Quelle keine Marktdaten oder Durchschnittswerte als Beleg vorliegen. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `b7f0d52968d89cdf8c5b` | praezision | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Einschätzung zur Datensicherheit von Cashback-Apps bleibt ohne Nennung konkreter rechtlicher Grundlagen (DSGVO) unpräzise, während die Quelle explizit auf rechtliche Verbraucherthemen fokussiert. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `be911855d67f998be662` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Ratgeber nennt keinen Regulierungsrahmen für Reisebuchungen (z. B. Fluggastrechte oder Stornierungsregeln), obwohl die Quelle diese als zentrale Informationsbereiche ausweist. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 98eb45f772ad7a0aac7b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden b7f0d52968d89cdf8c5b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden be911855d67f998be662 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-02-preiswert-surfen-so-findest-du-den-optimalen-dsl-anschluss` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-10-02-preiswert-surfen-so-findest-du-den-optimalen-dsl-anschluss/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `6b5921bdc76490587167` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Seit 2026 nutzen die großen Anbieter die Technik mit dem Namen Vectoring; das ist ein Modellwert. Sie senkt das Rauschen auf der Leitung. In der Stadt sind damit bis zu 250 Mbps stabil drin. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `8436b91bdb63a6316979` | praezision | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Preisgarantie über mindestens 12 Monate; ohne Garantie darf der Anbieter bald erhöhen, oft um bis zu 10 %. | – |
| `a4ff01e649b789f19e6a` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Für 50 Mbps zahlst du heute meist ca. 20–40 € im Monat; das ist ein Beispielwert. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6b5921bdc76490587167 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 8436b91bdb63a6316979 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a4ff01e649b789f19e6a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-12-energieausweis-was-das-dokument-fuer-deine-fixkosten` · **LIVE** (blockiert) · Risikoklasse standard · 4 Befund(e)

Datei: `content/posts/2026-10-12-energieausweis-was-das-dokument-fuer-deine-fixkosten/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `1dc0f20f9ab3a6b783bc` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Behauptung, dass ein fehlender Ausweis zu empfindlichen Bußgeldern führt, fehlt eine belegbare Quelle. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `7b94ca07b36c0b7cb1cc` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Aussage, dass Baudenkmäler von der Ausweispflicht befreit sind, wird nicht durch die angegebene Quelle gestützt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `985f506ee04087bf7253` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Angabe, dass ein Wechsel von Energieeffizienzklasse F zu C über 2.000 € Jahresersparnis bringt, ist unbelegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `ee321fa37210590f7e9b` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Keine Quelle für die Angabe, dass ein Energieausweis ein volles Jahrzehnt gültig ist, sofern keine größeren Umbauten erfolgen. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 1dc0f20f9ab3a6b783bc --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7b94ca07b36c0b7cb1cc --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 985f506ee04087bf7253 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ee321fa37210590f7e9b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-24-bankgebuehren-senken-7-schritte-zum-guenstigeren-konto` · **LIVE** (blockiert) · Risikoklasse standard · 4 Befund(e)

Datei: `content/posts/2026-10-24-bankgebuehren-senken-7-schritte-zum-guenstigeren-konto/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `04ae33652c1c5eb4e2b8` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Ein kurzer Check spart dir oft mehrere hundert Euro im Jahr. | – |
| `5223a3c7287ff81939cd` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Faustregel: ... mehr als 5 % deines Nettoeinkommens ... Meist sinken diese Kosten um über 80 % | – |
| `9800545ae945ec280b34` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Ein Wechsel ist für dich in der Regel komplett kostenlos als Beispielwert. | – |
| `bc0e4f2eb357a682c674` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Bei einem normalen Einkommen sollten die Gebühren fast Null sein. | – |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 04ae33652c1c5eb4e2b8 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 5223a3c7287ff81939cd --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 9800545ae945ec280b34 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden bc0e4f2eb357a682c674 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-07-7-gewohnheiten-fuer-finanzielle-freiheit` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-10-07-7-gewohnheiten-fuer-finanzielle-freiheit/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `25d6b9a720f981e8e9df` | praezision | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Bei der Bewertung flexibler Kosten sollte die moderate Preisentwicklung bei Nahrungsmitteln (+0,4 %) den stark steigenden Energiekosten gegenübergestellt werden, um Sparpotenziale zu priorisieren. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `3693b612533c24dcd1ea` | luecke | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Ratgeber empfiehlt die Prüfung von Stromverträgen, vernachlässigt aber den massiven Preistrend bei Energie von +12,2 %, der die Kalkulation der Fixkosten aktuell dominiert. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `c877eeff8842942c0071` | praezision | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die allgemeine Budget-Transparenz ist ohne Einbezug der Inflationsrate von 2,8 % unvollständig, da Preissteigerungen die Planungssicherheit der 'festen Kosten' kontinuierlich untergraben. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 25d6b9a720f981e8e9df --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 3693b612533c24dcd1ea --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden c877eeff8842942c0071 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-07-handyvertrag-kuendigen-raus-aus-der-kostenfalle-verlaengerung` · **LIVE** (blockiert) · Risikoklasse erhoeht · 2 Befund(e)

Datei: `content/posts/2026-10-07-handyvertrag-kuendigen-raus-aus-der-kostenfalle-verlaengerung/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `26b1c694d76bcc7af50f` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Ratgeber versäumt es, den für den Verbraucherschutz zentralen Regulierungsrahmen der 'Unternehmenspflichten' zu nennen, den die Bundesnetzagentur explizit als Fachthema führt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `9593e535bce55f4283e6` | praezision | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Empfehlung zum Preisvergleich lässt den aktuellen Marktdruck (sinkende Umsätze bei O2) außer Acht, der für die Verhandlung von Rückholangeboten bei Kündigung entscheidend sein kann. | [Quelle](https://www.heise.de/news/O2-mit-maessigen-Geschaeftszahlen-11525319.html?wt_mc=rss.red.ho.ho.atom.beitrag.beitrag) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 26b1c694d76bcc7af50f --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 9593e535bce55f4283e6 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-07-wie-smart-home-geraete-deine-stromrechnung-wirklich-druecken` · **LIVE** (blockiert) · Risikoklasse standard · 1 Befund(e)

Datei: `content/posts/2026-10-07-wie-smart-home-geraete-deine-stromrechnung-wirklich-druecken/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `a10511ed618384aa7b88` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel nennt keine regulatorischen Vorgaben oder Zertifizierungen (z. B. CE‑Kennzeichnung, Sicherheitsanforderungen) für Smart‑Home‑Geräte, obwohl solche Vorgaben von der Bundesnetzagentur beschrieben werden. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a10511ed618384aa7b88 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-24-energieeffizienz-im-haushalt-5-schnelle-spartricks` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-10-24-energieeffizienz-im-haushalt-5-schnelle-spartricks/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `0d1977a0b6a7b59136f2` | praezision | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Bezeichnung als 'beste Tarife' ist ein Superlativ ohne messbare Daten oder eigene Vergleichsmetrik. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `228ef205074fdc3fb4b3` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Heiz-Faustwert (6 % Ersparnis pro Grad) fehlt in der angegebenen Quelle und ist nicht am Satz belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `d7c301604b02d49e8d65` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der behauptete Budgetanteil von 30 % für Energie ist ein spezifischer Marktwert, der in der angegebenen Quelle nicht vorkommt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 0d1977a0b6a7b59136f2 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 228ef205074fdc3fb4b3 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d7c301604b02d49e8d65 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit` · **LIVE** (blockiert) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `47f855cb4f0fe1e5c65f` | luecke | 19 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Angaben zu möglichen Einsparungen beim Kfz‑Versicherungswechsel (150 €‑400 € bzw. 180 €‑350 €) sind ohne Quellenangabe; keine der genannten Zahlen findet sich in den bereitgestellten Statistiken. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `6b0aa3429d97e8c74ed8` | luecke | 19 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Behauptung, technische Maßnahmen beim Heizen senken den Energieverbrauch um 8 %‑12 %, wird nicht belegt; die bereitgestellten Daten enthalten lediglich die allgemeine Preisentwicklung von Energie (+14,9 %). | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `7f66ec82ee1a3f095b0c` | praezision | 19 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Aussage, der Herbst sei die „lukrativste Spar‑Saison des Jahres“, ist nicht durch messbare Daten gestützt; ein Vergleich mit anderen Jahreszeiten fehlt. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `84c991c5d152b14a2675` | luecke | 19 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Gesamteinsparungen von 500 €‑1.300 € pro Haushalt werden als Modellrechnung präsentiert, jedoch ohne Kennzeichnung als Modell und ohne Quellenangabe. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `a70e7adc97c58317ccc1` | luecke | 19 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Das angegebene Sparpotenzial von 50 €‑80 € durch saisonale Lebensmittel‑ und Vorratshaltung ist nicht mit einer Quelle untermauert. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 47f855cb4f0fe1e5c65f --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6b0aa3429d97e8c74ed8 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7f66ec82ee1a3f095b0c --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 84c991c5d152b14a2675 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a70e7adc97c58317ccc1 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub` · **LIVE** (blockiert) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `0051151e6c46f4c2bdb3` | luecke | 19 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Der Artikel nennt eine Kautionshöhe von 900 € bis 2.500 €, ohne dass die Verbraucherzentrale diese Spanne angibt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `0790f52160dfaa819917` | luecke | 19 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die angegebene Ersparnis von 145 € bei einer einwöchigen Anmietung ist nicht durch Zahlen der Verbraucherzentrale gedeckt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `53c3fde8e986e6560890` | luecke | 19 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Behauptung, dass Flughafen‑Mietstationen 15 %‑25 % teurer sind, wird von der Verbraucherzentrale nicht bestätigt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `89adecebaae75c147402` | luecke | 19 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Aussage, dass eine „Zero‑Excess“-Option die Kaution komplett auf 0 € senkt und dafür 5 €‑12 € pro Tag kostet, wird von der Verbraucherzentrale nicht belegt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `a1a269b73a1b9c2dfc88` | luecke | 19 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Der Hinweis, dass eine Vollkasko ohne Selbstbeteiligung nur 3 €‑8 € pro Tag mehr kostet, fehlt in den Angaben der Verbraucherzentrale. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 0051151e6c46f4c2bdb3 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 0790f52160dfaa819917 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 53c3fde8e986e6560890 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 89adecebaae75c147402 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a1a269b73a1b9c2dfc88 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-09-energiekosten-senken-smarte-helfer-fuer-den-haushalt` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-10-09-energiekosten-senken-smarte-helfer-fuer-den-haushalt/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `4d0125136c5b940946e4` | luecke | 5 T | Text unverändert seit dem Befund | Lichtsteuerung: Bedarfssteuerung – 2 bis 5 % des Stromverbrauchs. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `7aeb2098034d16a46885` | luecke | 5 T | Text unverändert seit dem Befund | Anbieter locken mit Neukundenboni, die nach der üblichen Erstlaufzeit entfallen; danach steigt der Arbeitspreis massiv an. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `ea97b5dd6695de127fd2` | luecke | 5 T | Text unverändert seit dem Befund | Heizungssteuerung: Smarte Thermostate können Heizkosten einsparen. Die Spanne von 10 bis 25 % ist ein Beispielwert aus der Rechnung unten. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 4d0125136c5b940946e4 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7aeb2098034d16a46885 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ea97b5dd6695de127fd2 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-12-kleine-energiespar-tricks-die-deine-kosten-sofort-senken` · **LIVE** (blockiert) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-10-12-kleine-energiespar-tricks-die-deine-kosten-sofort-senken/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `19ab248b17415c73edfb` | luecke | 5 T | Text unverändert seit dem Befund | Thermostat um 1 °C senken \| 4 % – 6 % der Heizkosten | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `372bb51051e8bd7c5f71` | luecke | 5 T | Text unverändert seit dem Befund | Viele Anbieter belohnen einen niedrigen Verbrauch mit besseren Konditionen | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `6aaff85e3a7591d0c5b2` | luecke | 5 T | Text unverändert seit dem Befund | für dich entstehen keine Mehrkosten | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `7e6087a4117a857a92c8` | luecke | 5 T | Text unverändert seit dem Befund | Durch diese zwei Maßnahmen sparst du in dieser Beispielrechnung jährlich rund 140 € | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `e28b4ad1f6d608d2ec77` | luecke | 5 T | Text unverändert seit dem Befund | Strom (LED‑Umrüstung) \| 100 € – 140 € \| etwa 8 % | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 19ab248b17415c73edfb --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 372bb51051e8bd7c5f71 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6aaff85e3a7591d0c5b2 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7e6087a4117a857a92c8 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e28b4ad1f6d608d2ec77 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-23-stromkosten-senken-clevere-haushaltsgeraete-im-ueberblick` · **LIVE** (blockiert) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-10-23-stromkosten-senken-clevere-haushaltsgeraete-im-ueberblick/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `1eae5c7e2bbd95a3362c` | luecke | 1 T | Text unverändert seit dem Befund | Tabelle mit konkreten kWh‑Werten und Euro‑Ersparnissen für neue vs. alte Geräte. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `8547ce3daa75aabb30d4` | luecke | 1 T | Text unverändert seit dem Befund | Annahme von 40 ct/kWh und daraus resultierende Jahres‑Ersparnis von 52 € für einen Kühlschrank‑Tausch. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `c8b197692bd0023c87bf` | luecke | 1 T | Text unverändert seit dem Befund | Behauptung, dass ein neuer Wärmepumpentrockner „sogar noch schneller“ die Anschaffungskosten amortisiert. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `e40a2ee5c7baa5f8567b` | luecke | 1 T | Text unverändert seit dem Befund | Sparsame Geräte senken deinen Verbrauch in der Beispielrechnung unten um bis zu 40 %. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `feb71513c6fb7064dc92` | luecke | 1 T | Text unverändert seit dem Befund | Der Stromverbrauch von Kühlschrank und Waschmaschine macht in der Modellrechnung rund 30 % der Kosten im Haushalt aus. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 1eae5c7e2bbd95a3362c --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 8547ce3daa75aabb30d4 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden c8b197692bd0023c87bf --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e40a2ee5c7baa5f8567b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden feb71513c6fb7064dc92 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-24-etf-sparplan-starten-schritt-fuer-schritt-zum-monatlichen` · **LIVE** (blockiert) · Risikoklasse erhoeht · 3 Befund(e)

Datei: `content/posts/2026-10-24-etf-sparplan-starten-schritt-fuer-schritt-zum-monatlichen/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `3bfeb0118af92a780a47` | luecke | 1 T | Text unverändert seit dem Befund | Bei 5 % Rendite im Jahr entstehen rund 30.000 € – keine Quelle für die angenommene Rendite angegeben. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `ed2161154dcee85da1ee` | luecke | 1 T | Text unverändert seit dem Befund | Angabe, dass die Einrichtung eines Sparplans meist weniger als 15 Minuten dauert, fehlt belegt. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `f593fe21275bd9dcefef` | luecke | 1 T | Text unverändert seit dem Befund | Behauptung, dass einige Broker bereits ab 1 € monatlich starten, ohne Quelle. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 3bfeb0118af92a780a47 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ed2161154dcee85da1ee --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f593fe21275bd9dcefef --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-09-balkonkraftwerk-foerderung-so-holst-du-dir-geld-zurueck` · **LIVE** · Risikoklasse standard · 2 Befund(e)

Datei: `content/posts/2026-10-09-balkonkraftwerk-foerderung-so-holst-du-dir-geld-zurueck/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `a74029dd4e284794d697` | luecke | 0 T | Text unverändert seit dem Befund | Eine separate Meldung beim Netzbetreiber ist im Standardfall nicht mehr nötig. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `c45ea4bb1a6f2330679a` | luecke | 0 T | Text unverändert seit dem Befund | Keine bundesweite Zuschusspflicht: Zuschüsse kommen, wenn überhaupt, von Städten, Gemeinden oder Ländern. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a74029dd4e284794d697 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden c45ea4bb1a6f2330679a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-30-kostenloses-girokonto-ohne-gebuehren-finden` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-10-30-kostenloses-girokonto-ohne-gebuehren-finden`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `176642ea8acfa44f1152` | luecke | 18 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Behauptung, dass Inlands‑Überweisungen in der Regel kostenlos sind, fehlt eine entsprechende Quelle. | – |
| `2520f45d441ef87614e3` | luecke | 18 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Behauptung, dass ein kostenloses Girokonto keine reguläre Kontoführungsgebühr erhebt, wird nicht durch die bereitgestellten Quellen belegt. | – |
| `33bda5941052d9334598` | luecke | 18 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Quantitative Aussage, dass ein kostenloses Girokonto mindestens ein Drittel der bisherigen Kontokosten einsparen kann, ist unbelegt. | – |
| `7406eaba3aa749c46f4b` | luecke | 18 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Zeitangabe, dass die Kontoeröffnung meist innerhalb weniger Werktage abgeschlossen ist, wird nicht durch die genannten Quellen gestützt. | – |
| `9f47e6d2aa8cf2a8ff91` | luecke | 18 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Angabe, dass die meisten Banken ein Mindestguthaben von ein paar hundert Euro verlangen, fehlt eine fundierte Quelle. | – |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 176642ea8acfa44f1152 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 2520f45d441ef87614e3 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 33bda5941052d9334598 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7406eaba3aa749c46f4b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 9f47e6d2aa8cf2a8ff91 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-04-guenstigen-mietwagen-fuer-den-urlaub-buchen` · nicht im Live-Bestand · 4 Befund(e)

Seite: `2026-11-04-guenstigen-mietwagen-fuer-den-urlaub-buchen`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `785eee76d888bb05ad96` | luecke | 13 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die im Rechenbeispiel genutzte Kilometerpauschale von 0,20 €/km wird als Referenzwert ohne Quellenangabe (z. B. Branchenverband) angeführt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `843ec148e23841b7bf35` | luecke | 13 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der als Handlungsschritt empfohlene '4K-Prüfpfad' wird im Text nicht erläutert und ist in der genannten Quelle nicht enthalten. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `def43a04853be4c35f7f` | luecke | 13 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Preisprognose (Anstieg in den letzten 3 Wochen) und der empfohlene Buchungsvorlauf (3-4 Wochen) sind Marktdaten ohne Beleg durch die Fachquelle. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `f064ea49ccefde26aef9` | praezision | 13 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Das Versprechen, CHECK24 vergleiche 'alle großen Anbieter', ist ein Vollständigkeitsversprechen ohne Nennung von Auswahlkriterien oder der Marktabdeckung. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 785eee76d888bb05ad96 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 843ec148e23841b7bf35 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden def43a04853be4c35f7f --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f064ea49ccefde26aef9 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag` · nicht im Live-Bestand · 3 Befund(e)

Seite: `2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `82cc87314e0d4fcb21e9` | luecke | 12 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die kalkulierte Ersparnis bei Energiekosten (15 €/Monat) berücksichtigt nicht den aktuellen Markttrend massiv steigender Preise (+14,9 % bei Energie). | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `bd5ee70c85ec7db78f26` | luecke | 12 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die pauschalen Jahressparwerte von 300 € bis 1.000 € werden in Marktfakten-Positur ohne Nennung einer Referenzquelle oder eines Absenders (z. B. Destatis) aufgeführt. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `f83f21c1f2e2012f672e` | praezision | 12 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Sparversprechen im Bereich Lebensmittel vernachlässigen die Inflationsrate bei Nahrungsmitteln (+0,4 %), was Modellrechnungen ohne Inflationsbereinigung ungenau macht. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 82cc87314e0d4fcb21e9 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden bd5ee70c85ec7db78f26 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f83f21c1f2e2012f672e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-06-guenstige-fluege-fuer-den-spaetsommer-finden` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-11-06-guenstige-fluege-fuer-den-spaetsommer-finden`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `0e68294e193918d5b5b0` | luecke | 11 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Text nennt eine angeblich gängige Faustregel von 20 % Rabatt im Spätsommer (Beispiel 300 € → 240 €) ohne Quellenangabe. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `4d91ef71fa76febdb769` | luecke | 11 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Es wird angegeben, dass Flüge an Dienstagen und Mittwochen günstiger seien und an Freitagen bzw. Sonntagen teurer, ohne Beleg. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `5b427fb4f05b475d9a89` | luecke | 11 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Empfehlung, Flüge vier bis acht Wochen im Voraus zu buchen, weil die Preise dann am niedrigsten seien, wird nicht belegt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `e933e34672f0b6464d1e` | luecke | 11 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel behauptet, dass im Spätsommer die Nachfrage nach Flügen sinkt und dadurch die Preise fallen, ohne dafür eine Quelle anzugeben. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `eb6a47df5535fa267a82` | luecke | 11 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Behauptet wird, dass Kombi‑Deals für Flug + Mietwagen typischerweise 5–15 % Einsparungen bringen, ohne Nachweis. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 0e68294e193918d5b5b0 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 4d91ef71fa76febdb769 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 5b427fb4f05b475d9a89 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e933e34672f0b6464d1e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden eb6a47df5535fa267a82 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `strom-sparen` · nicht im Live-Bestand · 3 Befund(e)

Seite: `strom-sparen`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `0f248aaad2d2b8d87d0d` | luecke | 11 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die im Marktradar angegebenen Durchschnittspreise für Strom (37,3 ct/kWh) und Gas (12,23 ct/kWh) werden ohne Quellenangabe genannt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `3a69bd57886154a18b8e` | luecke | 11 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass bei Preiserhöhungen ein gesetzliches 14‑tägiges Sonderkündigungsrecht besteht, fehlt eine rechtliche Quellenangabe. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `4f777954306ac7b21e03` | luecke | 11 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Behauptung, dass ein Lieferantenwechsel und ein technischer Anschlusswechsel nicht dasselbe seien, wird nicht durch eine Quelle belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 0f248aaad2d2b8d87d0d --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 3a69bd57886154a18b8e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 4f777954306ac7b21e03 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-18-strompreis-2026-herbst-check-fuer-deine-stromkosten` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-11-18-strompreis-2026-herbst-check-fuer-deine-stromkosten`

Herkunft nach Datums-Lift: `2026-11-09-strompreis-2026-herbst-check-fuer-deine-stromkosten` → `2026-11-18-strompreis-2026-herbst-check-fuer-deine-stromkosten`. Befund-ID und Fassungsanker bleiben unverändert; das Re-Dating ist keine fachliche Entscheidung.

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `1c6e4d2f12da24ec4081` | luecke | 9 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Hinweis, dass ein Anbieterwechsel im Durchschnitt 3‑6 Wochen dauert, fehlt eine nachweisbare Quelle. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `5b539daf371f7362a3ef` | praezision | 9 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Empfehlung, dynamische Tarife erforderten zwingend einen Smart Meter, wird ohne Angabe von Voraussetzungen, Kosten oder Verfügbarkeit präzisiert. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `77d809de9e06d1d6910d` | luecke | 9 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Es wird eine Prognose für den Strompreis 2026 angegeben („Trends erkennen“, „Netzentgelte steigen“), ohne dass dafür aktuelle Marktdaten oder offizielle Prognosen genannt werden. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `ad7c0a90ef52ff35130e` | luecke | 9 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel behauptet, dass Preisgarantien vor Preissteigerungen schützen, liefert jedoch keine Quelle für diese Aussage. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `f227178fbda2cc59c350` | luecke | 9 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass Ökostrom‑Tarife häufig günstiger als die Grundversorgung seien, wird nicht durch eine Quelle belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 1c6e4d2f12da24ec4081 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 5b539daf371f7362a3ef --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 77d809de9e06d1d6910d --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ad7c0a90ef52ff35130e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f227178fbda2cc59c350 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-09-handytarife-vergleichen-so-findest-du-den-guenstigsten-tarif` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-11-09-handytarife-vergleichen-so-findest-du-den-guenstigsten-tarif`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `3efe31a371440636f465` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Empfehlung, den Handytarif einmal jährlich bzw. vierteljährlich zu prüfen, fehlt eine Quellenangabe. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `49c1a762c2df16c52b7a` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel behauptet, dass Verträge nach sechs Monaten die Preise erhöhen, ohne dafür eine Quelle anzugeben. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `56c5b1f92a70c6ebeb0b` | praezision | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass CHECK24 alle aktuellen Angebote liefert, ist ein Vollständigkeitsversprechen ohne Messgröße. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `c6d20c93f94cee2ae5ae` | praezision | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Regel „Datenvolumen halbieren, das du wirklich brauchst“ wird als allgemeine Faustregel präsentiert, ohne Messdaten oder Quelle. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `f6a30c4191c47f5cdf0a` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Faustregel, dass zusätzliche Gebühren mindestens 5 % der Grundgebühr betragen müssen, wird nicht belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 3efe31a371440636f465 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 49c1a762c2df16c52b7a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 56c5b1f92a70c6ebeb0b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden c6d20c93f94cee2ae5ae --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f6a30c4191c47f5cdf0a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-09-wlan-verbessern-mesh-system-oder-repeater-im-check` · nicht im Live-Bestand · 3 Befund(e)

Seite: `2026-11-09-wlan-verbessern-mesh-system-oder-repeater-im-check`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `6d89862b38c33c827817` | praezision | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die pauschale Behauptung, Hardware bleibe stets Eigentum des Nutzers, ist unpräzise, da die Bundesnetzagentur die Kupfer-Glas-Migration begleitet, die oft providerseitige Technikwechsel und neue Netzabschlusspunkte erfordert. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `72bbf29e4ef70a71ad06` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Aussagen zu Markttrends wie hohen Neukundenrabatten und Wechselprämien werden als Marktfakten ohne Bezug zu offiziellen Referenzwerten oder Berichten der Aufsichtsbehörde dargestellt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `f0103f4c6a777aaa4845` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Ratgeber thematisiert den Anbieterwechsel und Bandbreiten, lässt aber den regulatorischen Rahmen der Bundesnetzagentur zur Breitbandversorgung und zum Verbraucherschutz bei Minderleistung unerwähnt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6d89862b38c33c827817 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 72bbf29e4ef70a71ad06 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f0103f4c6a777aaa4845 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `frugalismus` · nicht im Live-Bestand · 3 Befund(e)

Seite: `frugalismus`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `760cdea8544be9d1c7c0` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die im 'Zins-Marktradar Q4 2026' genannten Benchmark-Daten für Tagesgeld (3,10–3,45 %) und Dispozinsen (11,5–13,8 %) werden der Bundesbank und BaFin zugeschrieben, sind jedoch in den Recherche-Fundstellen nicht belegt. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `cacd65ac080f79a719ae` | praezision | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Ratgeber thematisiert Fixkosten-Senkungen allgemein, lässt aber die laut Destatis signifikante Preissteigerung bei Energie (+12,2 %) unerwähnt, die den Spielraum für die angestrebte 50-Prozent-Quote prägt. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `d2bfec8aa9b7a0807f0e` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die 50–30–20-Budgetformel wird als Destatis-Standardmodell ausgewiesen; die angegebene Quelle des Statistischen Bundesamtes enthält jedoch nur Daten zum Verbraucherpreisindex, keine Budget-Verteilungsschlüssel. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 760cdea8544be9d1c7c0 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden cacd65ac080f79a719ae --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d2bfec8aa9b7a0807f0e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-19-urlaubskasse-clever-aufbessern` · nicht im Live-Bestand · 3 Befund(e)

Seite: `2026-10-19-urlaubskasse-clever-aufbessern`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `17cddd994cefcdc30f31` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Ein Mietwagen ist oft ein teurer Posten. Er kostet meistens fast so viel wie der Flug oder das Hotel. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `676fdb5ff70228b06bdc` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Geld sollte innerhalb von 48 Stunden zurück sein. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `88051266499d4040f7f3` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Preise werden dort fair und offen gezeigt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 17cddd994cefcdc30f31 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 676fdb5ff70228b06bdc --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 88051266499d4040f7f3 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-11-kreditkarte-ohne-jahresgebuehr-die-besten-kostenlosen-karten` · nicht im Live-Bestand · 4 Befund(e)

Seite: `2026-11-11-kreditkarte-ohne-jahresgebuehr-die-besten-kostenlosen-karten`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `228c9da3c42ee90e34bf` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Eine typische Auslandseinsatzgebühr liegt bei 1 % des Umsatzes. | – |
| `7728690d5c2f7c141d8d` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Du hast eine Jahresgebühr von 60 € und kündigst erst 30 Tage nach Ablauf der Frist. | – |
| `cc0de46a82ad90851506` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Du investierst 15 Minuten in den CHECK24‑Filter und sparst im Schnitt 5 Minuten pro Anbieter. | – |
| `d553d0d6c7706a69ad13` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Keine versteckten Kosten, wenn die Karte „keine Jahres‑ und keine Auslandseinsatzgebühr“ nennt. | – |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 228c9da3c42ee90e34bf --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7728690d5c2f7c141d8d --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden cc0de46a82ad90851506 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d553d0d6c7706a69ad13 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-13-tagesgeld-und-zinsen-so-parkst-du-dein-geld-sicher` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-11-13-tagesgeld-und-zinsen-so-parkst-du-dein-geld-sicher`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `32467bdd3433317393b9` | luecke | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Auszahlungsgebühr – selten, aber bei manchen Anbietern möglich. | [Quelle](https://www.bundesbank.de/de/presse/pressenotizen) |
| `ad932db898c534874507` | luecke | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Durch die gesetzliche Einlagensicherung ist dein Geld bis zu einem hohen Betrag geschützt. | [Quelle](https://www.bundesbank.de/de/presse/pressenotizen) |
| `ccf8977f44f05ea2de0a` | luecke | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Mindesteinlage – manchmal 1 000 €, häufig aber keine Mindestgrenze. | [Quelle](https://www.bundesbank.de/de/presse/pressenotizen) |
| `d561837e6b7d7ee02a8e` | luecke | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Neukunden‑Zins – Oft 6‑12 Monate, danach Rückkehr zum Basissatz. | [Quelle](https://www.bundesbank.de/de/presse/pressenotizen) |
| `fc0e4ba836f5e544d957` | luecke | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Kündigungsfrist – in der Regel sofort, bei Sonderkonditionen kann es Einschränkungen geben. | [Quelle](https://www.bundesbank.de/de/presse/pressenotizen) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 32467bdd3433317393b9 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ad932db898c534874507 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ccf8977f44f05ea2de0a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d561837e6b7d7ee02a8e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden fc0e4ba836f5e544d957 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-16-die-50-30-20-regel-bringt-ordnung-wohin-mit-dem-gehalt` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-11-16-die-50-30-20-regel-bringt-ordnung-wohin-mit-dem-gehalt`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `30d4af7eef58e74bd3b6` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | 20 % des Einkommens für Sparen/Vorsorge | – |
| `676ef4593c35f53c18f1` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Faustregel: Fixkosten > 60 % erfordern Handlungsbedarf | – |
| `7fe714402ea2428ccea8` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | 50 % des Einkommens in lebensnotwendige Ausgaben | – |
| `9051f78fea0408adbe70` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Vertragschecks senken die Fixlast | – |
| `b11782f36d73e5a16b7a` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | 30 % des Einkommens für Wünsche | – |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 30d4af7eef58e74bd3b6 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 676ef4593c35f53c18f1 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7fe714402ea2428ccea8 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 9051f78fea0408adbe70 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden b11782f36d73e5a16b7a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-16-stabile-gaskosten-lohnt-sich-eine-preisgarantie-fuer-dich` · nicht im Live-Bestand · 4 Befund(e)

Seite: `2026-11-16-stabile-gaskosten-lohnt-sich-eine-preisgarantie-fuer-dich`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `05ae2eeee6a578aac17b` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Keine Datenbasis für die Angabe, dass 24‑Monats‑Garantie üblich sei. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `2980f6b227953c5ac8af` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Keine Quelle für die Aussage, dass die eingeschränkte Preisgarantie von den meisten Kunden bevorzugt wird. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `c32c41bdd629ae4646c1` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Keine Quelle für die Aussage, welche Kosten von einer Preisgarantie tatsächlich abgedeckt werden. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `d557c9fcb4562042612b` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Unbelegte Behauptung zur Ersatzversorgung bei Anbieterinsolvenz. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 05ae2eeee6a578aac17b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 2980f6b227953c5ac8af --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden c32c41bdd629ae4646c1 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d557c9fcb4562042612b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-18-wertvolle-gebrauchte-moebel-finden-so-pruefst-du-qualitaet` · nicht im Live-Bestand · 3 Befund(e)

Seite: `2026-11-18-wertvolle-gebrauchte-moebel-finden-so-pruefst-du-qualitaet`

Herkunft nach Datums-Lift: `2026-11-17-wertvolle-gebrauchte-moebel-finden-so-pruefst-du-qualitaet` → `2026-11-18-wertvolle-gebrauchte-moebel-finden-so-pruefst-du-qualitaet`. Befund-ID und Fassungsanker bleiben unverändert; das Re-Dating ist keine fachliche Entscheidung.

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `842ddd33d3dd6b0b97f7` | luecke | 1 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Muffiger Geruch deutet oft auf tiefliegenden Schimmel oder Feuchtigkeit hin. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `d3e210fb738bd77ef594` | luecke | 1 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Neue Möbel verlieren oft sofort nach dem Kauf massiv an Wert. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `da84fa452f879ea8f2da` | luecke | 1 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Eigenleistung lohnt sich finanziell, wenn die Ersparnis den Zeitaufwand rechtfertigt. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 842ddd33d3dd6b0b97f7 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d3e210fb738bd77ef594 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden da84fa452f879ea8f2da --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-28-dsl-und-internet-flat-guenstig-sichern` · nicht im Live-Bestand · 1 Befund(e)

Seite: `2026-10-28-dsl-und-internet-flat-guenstig-sichern`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `fb4d2260f4fa291c35ae` | praezision | 19 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Angabe, dass für zwei HD‑Streams gleichzeitig etwa 30 Mbit/s benötigt werden, ist nicht durch Daten belegt und lässt Spielraum für Fehlinterpretationen. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden fb4d2260f4fa291c35ae --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-08-energie-update-was-sich-jetzt-fuer-dich-aendert` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-10-08-energie-update-was-sich-jetzt-fuer-dich-aendert`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `1d448c9cdc2618ef9bdf` | luecke | 8 T | Text unverändert seit dem Befund | Der Hinweis, dass Festpreis‑Tarife in der Regel einen Aufschlag enthalten, fehlt jede Beleggrundlage. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `2188f6b0006eb0607871` | luecke | 8 T | Text unverändert seit dem Befund | Die Behauptung, die Bundesnetzagentur fordere die getrennte Angabe von Grund‑ und Arbeitspreis, wird nicht durch die verlinkte Quelle belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `33917254a91a1c551389` | praezision | 8 T | Text unverändert seit dem Befund | Die Aussage, dass variable Tarife mit Preisgarantie oder Deckel im Vergleich „selten ganz oben“ stehen, ist ein untermauertes Superlativ ohne Messgröße. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `82badcfa80493134c12a` | luecke | 8 T | Text unverändert seit dem Befund | Die Aussage, dass variable Tarife das Marktpreisrisiko vollständig auf den Kunden übertragen, wird ohne Quellenangabe gemacht. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `b44fd9621fb708f45c90` | luecke | 8 T | Text unverändert seit dem Befund | Die Behauptung, dass sich die Energiemärkte 2026 wieder stärker bewegen, wird ohne aktuelle Marktdaten belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 1d448c9cdc2618ef9bdf --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 2188f6b0006eb0607871 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 33917254a91a1c551389 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 82badcfa80493134c12a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden b44fd9621fb708f45c90 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-29-konto-karten-update-was-sich-jetzt-fuer-dich-aendert` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-09-29-konto-karten-update-was-sich-jetzt-fuer-dich-aendert`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `2140cb752c4069ae86a0` | luecke | 7 T | Text unverändert seit dem Befund | Für die herkömmliche Girocard werden häufig Gebühren von etwa 0,99 Euro monatlich erhoben – Angabe fehlt in den bereitgestellten Quellen. | [Quelle](https://www.verbraucherzentrale.de/aktuelle-meldungen) |
| `766e3df5f10bb91ff03b` | luecke | 7 T | Text unverändert seit dem Befund | Ein schneller Kontowechsel sei jederzeit kostenlos und sichere dauerhaft die besten Zinsen – diese Aussage fehlt in den bereitgestellten Quellen. | [Quelle](https://www.tagesschau.de/wirtschaft/unternehmen/faq-nvidia-spionage-100.html) |
| `d11731ee598db94f14c0` | luecke | 7 T | Text unverändert seit dem Befund | Die Maestro‑Funktion soll seit Juli 2023 schrittweise eingestellt werden – keine Quelle dafür vorhanden. | [Quelle](https://www.verbraucherzentrale.de/aktuelle-meldungen) |
| `ef34d0d6243902be1bc9` | luecke | 7 T | Text unverändert seit dem Befund | Befristete Sonderzinsen bei Tagesgeldkonten und deren starke Absenkung nach der Aktionsphase werden behauptet, ohne dass die angegebenen Quellen dies belegen. | [Quelle](https://www.tagesschau.de/wirtschaft/unternehmen/faq-nvidia-spionage-100.html) |
| `f48dd250f165f647c90a` | luecke | 7 T | Text unverändert seit dem Befund | Viele Banken stellen ihre Standardkarten auf kostenlose Debit‑Visas oder Mastercards um – ohne aktuelle Quelle belegt. | [Quelle](https://www.verbraucherzentrale.de/aktuelle-meldungen) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 2140cb752c4069ae86a0 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 766e3df5f10bb91ff03b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d11731ee598db94f14c0 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ef34d0d6243902be1bc9 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f48dd250f165f647c90a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-21-mietwagen-fallen-im-urlaub-vermeiden` · nicht im Live-Bestand · 4 Befund(e)

Seite: `2026-10-21-mietwagen-fallen-im-urlaub-vermeiden`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `4246118449c91859654d` | praezision | 1 T | Text unverändert seit dem Befund | Die Faustregel lautet: Jede Zusatzoption sollte höchstens ein Drittel der Miete kosten. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `4f62641b3af8d53ba65d` | praezision | 1 T | Text unverändert seit dem Befund | Ein Navi kostet oft zehn Euro oder mehr pro Tag. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `5f76a2f9b3a57de72e73` | praezision | 1 T | Text unverändert seit dem Befund | Ein Schutz ohne Eigenanteil ist meist teurer pro Tag. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `6df8b77e2840e62c5711` | luecke | 1 T | Text unverändert seit dem Befund | Frühbucherrabatte gelten meist nur bis zu einer bestimmten Anzahl Tage vor Mietbeginn. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 4246118449c91859654d --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 4f62641b3af8d53ba65d --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 5f76a2f9b3a57de72e73 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6df8b77e2840e62c5711 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-07-notgroschen-aufbauen-wie-viel-reicht-wirklich` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-10-07-notgroschen-aufbauen-wie-viel-reicht-wirklich`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `7312c88fd0b751847ccf` | praezision | 0 T | Text unverändert seit dem Befund | Ein Konto für Tagesgeld ist die beste Wahl für dich. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `a8ddfb1310192fb9c280` | luecke | 0 T | Text unverändert seit dem Befund | Die 50–30–20-Regel hilft dir bei der Ordnung deines Geldes. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `c6ab40eeb8dea1d1c3da` | luecke | 0 T | Text unverändert seit dem Befund | Als sicherer Rahmen gilt seit langer Zeit eine einfache Faustregel. Spare etwa drei bis sechs Netto-Monatslöhne an. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `c858896722ed308b0271` | praezision | 0 T | Text unverändert seit dem Befund | Dein Sparbetrag steigt dadurch leicht um fünf bis zehn Prozent an. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `cd38bc25c828bedd7b72` | luecke | 0 T | Text unverändert seit dem Befund | Viele Experten raten zu 10 % des Nettolohns. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7312c88fd0b751847ccf --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a8ddfb1310192fb9c280 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden c6ab40eeb8dea1d1c3da --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden c858896722ed308b0271 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden cd38bc25c828bedd7b72 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-15-saison-update-was-sich-jetzt-fuer-dich-aendert` · nicht im Live-Bestand · 4 Befund(e)

Seite: `2026-10-15-saison-update-was-sich-jetzt-fuer-dich-aendert`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `108c4ad3f4adcb4d2a1b` | veraltet | 0 T | Text unverändert seit dem Befund | Die Steigerung der Energiepreise wird mit 14,9 % angegeben, die aktuelle Destatis-Statistik weist jedoch nur +12,7 % aus. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `211613734bc20a8603e5` | luecke | 0 T | Text unverändert seit dem Befund | Bei der Erwähnung von Konten "ohne Grundgebühr" fehlt die notwendige Eingrenzung auf die Zielgruppe (Verbraucher) und der regulatorische Rahmen des Zahlungskontengesetzes. | – |
| `2bbbd4141968a4365ab6` | luecke | 0 T | Text unverändert seit dem Befund | Beim Versicherungscheck fehlt der Hinweis auf die Prüfung der Notwendigkeit (existenzielle Risiken), wie sie die Verbraucherzentrale als ersten Schritt priorisiert. | – |
| `b28c1e2fb42f8f2ba34c` | praezision | 0 T | Text unverändert seit dem Befund | Das Versprechen, Portale zeigten die "besten Tarife auf einen Blick", ist unpräzise, da sie nur Marktausschnitte abbilden und staatlich zertifizierte Vergleiche ignorieren. | – |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 108c4ad3f4adcb4d2a1b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 211613734bc20a8603e5 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 2bbbd4141968a4365ab6 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden b28c1e2fb42f8f2ba34c --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

---

_Diese Akte entscheidet nichts und schließt nichts. Sie macht sichtbar, was zu entscheiden ist, wer es entscheiden muss (Herausgeber/Redaktion) und wie der Schließweg lautet. Regel: `scripts/faktenfrische_befund_ledger.py`, Governance C46._
