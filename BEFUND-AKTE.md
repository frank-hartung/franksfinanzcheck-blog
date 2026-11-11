# BEFUND-AKTE – offene Fachbefunde der Faktenfrische

_Stand 2026-11-11 · erzeugt von `scripts/faktenfrische_befund_akte.py` · Quelle: `data/faktenfrische_queue.json` + `data/faktenfrische_entscheidungen.yaml` (eine Regel, zwei Leser)._

**153 offene Befunde auf 37 Seiten · davon 22 Live-Seiten mit 90 Befunden · ältester 12 Tage · Frist 14 Tage.**

| Kennzahl | Wert |
|---|---|
| Offene Befunde | 153 |
| Seiten betroffen | 37 (davon live: 22) |
| Text seit dem Befund geändert | 117 |
| Altbestand ohne Fassungs-Hash | 5 |
| Nicht entscheidbar (Seite fehlt) | 0 |
| Über der Frist (14 Tage) | 0 |
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

> **Wichtig – betrifft 122 von 153 Befunden** (in der Tabelle als Fassung markiert): Der Text ist seit dem Befund bereits geändert worden (Heilung) oder stammt aus dem Altbestand. Die Entscheidung bezieht sich ausdrücklich auf den HEUTIGEN Text – bitte diesen lesen, nicht den alten Befund abnicken. Diese Prüfung kann dir die Maschine nicht abnehmen – sie darf sie aber auch nicht verhindern.

## Seiten

### `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `30caa57be394afb62947` | luecke | 10 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Für den angeführten BDEW-Durchschnittspreis von 11,93 Cent/kWh fehlt in den Recherche-Fundstellen ein entsprechender Beleg. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `32a3ea879f2cf126b3a7` | luecke | 10 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel lässt den in der Quelle explizit genannten Regulierungsrahmen der 'Unternehmenspflichten' unerwähnt, der für den Schutz der Verbraucher beim Anbieterwechsel zentral ist. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `c583efe1ce02df3ca2d7` | luecke | 10 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die im Artikel genannte Ersparnis-Berechnung der Bundesnetzagentur für Januar 2026 (360 €) wird durch die allgemeine Übersichtsseite der Behörde nicht gestützt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 30caa57be394afb62947 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 32a3ea879f2cf126b3a7 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden c583efe1ce02df3ca2d7 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden` · **LIVE** (blockiert) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `437b809ffbf41e5af434` | luecke | 10 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Keine Quelle für die Aussage, dass das Gesetz bei einem Tarifwechsel die Grundversorgung garantiert – regulatorischer Rahmen fehlt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `9fbacd9942c2dfa1447f` | luecke | 10 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Keine Quelle für die Behauptung, dass ein Grad weniger Raumtemperatur rund 6 % Energie einspart – Prozent‑Angabe fehlt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `da30cbb5fbc8c801daf0` | luecke | 10 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Keine Quelle für die Angabe, dass durch Optimierungsmaßnahmen 10‑15 % Einsparungen realistisch sind – Prozent‑Wert unbelegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `db8a69f08dc0020adebd` | luecke | 10 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Keine Quelle für die Aussage, dass im Oktober 2026 bessere Gaspreise gelten – Preis‑Trend‑Behauptung fehlt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `e834f4702e87194affe7` | luecke | 10 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Keine Quelle für die Angabe, dass ein Einfamilienhaus typischerweise 18.000 kWh/Jahr verbraucht – Verbrauchszahl ist unbelegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 437b809ffbf41e5af434 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 9fbacd9942c2dfa1447f --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden da30cbb5fbc8c801daf0 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden db8a69f08dc0020adebd --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e834f4702e87194affe7 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen` · **LIVE** (blockiert) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `252413dcc16cea146beb` | luecke | 10 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel behauptet, dass eine Preisänderung meist einen Monat vorher angekündigt werden muss, ohne dafür eine Quelle anzugeben. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `48a0a962046c8315270e` | praezision | 10 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Behauptung, dass eine Preisgarantie einen Teil des Risikos auf den Anbieter überträgt und dafür ein höherer Startpreis üblich ist, fehlt eine konkrete Quelle und bleibt vage. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `9326152f4d788cff56bd` | praezision | 10 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass man „in der Regel“ zum Zeitpunkt der Preisänderung Sonderkündigungsrecht hat, ist unpräzise und wird nicht durch eine konkrete Regelung belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `ab4d084fd367c8e4d518` | luecke | 10 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der angegebene durchschnittliche Gaspreis von 11,93 Cent/kWh für 2026 (laut BDEW) wird nicht durch eine Quelle belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `d215addd22dea72c44df` | luecke | 10 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Angabe, dass die Verbraucherzentrale etwa 6 % weniger Heizenergie pro Grad niedrigerer Raumtemperatur nennt, fehlt eine Quellenangabe. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

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
| `0aa915539d57841e5014` | luecke | 9 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass die Verbraucherzentrale empfiehlt, Boni im ersten Vergleich auszublenden, fehlt eine Quellenangabe. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `5e1be48085014a836807` | luecke | 9 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der angegebene BDEW‑Durchschnittspreis von 11,93 Cent/kWh für 2026 wird nicht belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `6fdf31c3b68b6122bd0d` | praezision | 9 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die pauschale Formulierung, dass bei zentraler Heizung der Vermieter oder die Eigentümergemeinschaft den Anbieter wählt, ist zu ungenau und nicht belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `c27c182c615bd7ca3b78` | luecke | 9 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel behauptet, dass laut Bundesnetzagentur Preisänderungen klar angekündigt und begründet sein müssen, liefert jedoch keinen Beleg dafür. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `e1e40e9bbbdd109df86e` | luecke | 9 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Es wird angegeben, dass bei einer Preisänderung in der Regel ein Sonderkündigungsrecht besteht, ohne dafür eine Quelle zu nennen. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

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
| `334751e6f61ad0033fe4` | luecke | 9 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Angabe, dass ein Gaslieferantenwechsel bei 20.000 kWh im Januar 2026 im Schnitt etwa 360 € spart, fehlt jede Quellenangabe. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `36759a5efe5e8e5163d0` | luecke | 9 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Faustregel der Verbraucherzentrale, dass pro Grad weniger Raumtemperatur der Heizbedarf um etwa 6 % sinkt, wird ohne Quelle angegeben. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `942922d1afd7844618e9` | luecke | 9 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Rechnung „1 Cent pro kWh bei 18.000 kWh Jahresverbrauch ergibt rund 180 € im Jahr“ wird nicht belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `d41f0d5ce8798df0211b` | praezision | 9 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage „Die besten Tarife findest du über unseren Partner‑Vergleich“ ist ein Superlativ ohne messbare Daten oder Vergleichskriterien. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `e139d0769faadd04392a` | luecke | 9 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der BDEW‑Durchschnittspreis von 11,93 Cent/kWh für 2026 wird ohne Quellenangabe genannt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

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
| `58f03a64adaaf8125959` | praezision | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Während der Artikel vor hohen Kosten für Festmenüs warnt, liegt die Preissteigerung bei Nahrungsmitteln laut Destatis im Oktober 2026 bei lediglich +0,4 % und damit deutlich unter der allgemeinen Inflation. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `a7f5f01ef15a38839a0d` | praezision | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Pauschale für 'Anreise und Mobilität' (10 % des Budgets) berücksichtigt nicht die überdurchschnittliche Preissteigerung bei Energie von +14,9 %, die Fahrtkosten im Vergleich zum Vorjahr massiv verteuern kann. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `bcc2bdf06220d5097133` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Modellrechnung für das Weihnachtsbudget (600 €) lässt die aktuelle Teuerungsrate unberücksichtigt. Laut Statistischen Bundesamt liegt die Inflationsrate im Oktober 2026 bei +2,8 %, was als Referenzwert für die Budgetplanung zum Vorjahr fehlt. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 58f03a64adaaf8125959 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a7f5f01ef15a38839a0d --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden bcc2bdf06220d5097133 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `089b89138417e63a3dcf` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Es fehlt der für Campingbuchungen relevante Regulierungsrahmen (Unterscheidung Mietrecht bei Stellplätzen vs. Reiserecht), den die Fundstelle für den Bereich Reise nur allgemein andeutet. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `1158934e7a18c7b2099b` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Preisangabe von 20 bis 45 € pro Nacht wird als realistischer Wert positioniert, ist jedoch nicht durch Marktdaten oder eine Referenzstelle in den Fundstellen belegt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `3716cfd3ab5aec6d774b` | praezision | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Verweis auf die Verbraucherzentrale zur Prüfung von Buchungsangaben führt auf eine allgemeine Übersichtsseite ohne konkrete Checklisten für Camping-Angebote. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 089b89138417e63a3dcf --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 1158934e7a18c7b2099b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 3716cfd3ab5aec6d774b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen` · **LIVE** (blockiert) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `7067eabb89a917ae67a4` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Verbraucherzentrale sammelt Hinweise zu Reisebuchungen, auch zu unklaren Angeboten und Problemen mit Online-Buchungen. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `af2ccb4222eeb195222f` | praezision | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Ein Mietwagenvergleich kann Angebote sichtbar machen, prüft aber nicht automatisch, ob das Auto zum individuellen Urlaub passt – ohne Messgröße bleibt die Aussage ungenau. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `d9c8b522bf1dcaed0340` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Verbraucherzentrale beschreibt, dass sich eine Pauschalreise unter bestimmten Bedingungen auf eine andere Person übertragen lässt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `e2975509f3f130de0755` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Verbraucherzentrale empfiehlt, größere Ausgaben vorauszuplanen und das eigene Budget im Blick zu behalten. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `f1704e45e970a8f4b078` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Bei einer Pauschalreise gilt die Mitteilung als rechtzeitig, wenn sie dem Veranstalter spätestens sieben Tage vor Reisebeginn zugeht (§ 651e BGB). | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7067eabb89a917ae67a4 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden af2ccb4222eeb195222f --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d9c8b522bf1dcaed0340 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e2975509f3f130de0755 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f1704e45e970a8f4b078 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren` · **LIVE** (blockiert) · Risikoklasse erhoeht · 5 Befund(e)

Datei: `content/posts/2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `1dbeb2f8c51e78d11d49` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Behauptung, dass klassische Filialbanken jährlich 150 € bis 250 € an reinen Gebühren kosten, ist unbelegt. | – |
| `33e736ac6afe996b491a` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Behauptung, dass Echtzeit‑Überweisungen bei kostenlosen Konten generell gebührenfrei sind, fehlt jede Quelle. | – |
| `96b7b7768d402884810c` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Aussage, dass Einlagen bis 100.000 € durch die deutsche Einlagensicherung geschützt sind, wird nicht belegt. | – |
| `a25bb6bbcb25ba8b0e22` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Angabe von Dispozinsen von 8 % bis 11 % ohne Quellenangabe. | – |
| `f94f8ba1e4342e67e45a` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Angabe, dass ein Kontowechsel 120 € bis 180 € im Jahr spart, fehlt jede Quelle. | – |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 1dbeb2f8c51e78d11d49 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 33e736ac6afe996b491a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 96b7b7768d402884810c --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a25bb6bbcb25ba8b0e22 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f94f8ba1e4342e67e45a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier` · **LIVE** (blockiert) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `4afb8daed73677ee6224` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Angabe, dass 58 % der Nutzer ihr Haushaltsbuch digital führen, beruft sich angeblich auf Statista 2025, jedoch wird keine Quelle genannt. | – |
| `9eb9a90899cc8ca66020` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Sparpotenzial‑Beispiele (z. B. DSL‑Tarifwechsel von 44 € auf 24 €) enthalten konkrete Zahlen ohne Quellenangabe. | – |
| `b4bd085bc84a6131b644` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Behauptung, dass 60 % der Haushalte in Deutschland ihr Geld nicht nachverfolgen, wird mit einer Auswertung der Stiftung Warentest angegeben, jedoch fehlt ein entsprechender Nachweis. | – |
| `baed76dc211bd15dd46f` | praezision | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Versprechen, dass ein Haushaltsbuch „schnell“ zeigt, welche Posten sich lohnen, ist nicht quantifiziert und fehlt an konkreten Evidenzangaben. | – |
| `d7c3cfb422310cf26ca6` | praezision | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass die 50‑30‑20‑Regel für ein Nettoeinkommen von 2.500 € realistisch sei, wird ohne Hinweis auf regionale Unterschiede oder empirische Daten präsentiert. | – |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 4afb8daed73677ee6224 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 9eb9a90899cc8ca66020 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden b4bd085bc84a6131b644 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden baed76dc211bd15dd46f --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d7c3cfb422310cf26ca6 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-03-kreditkarte-vergleichen-kostenlos-sicher-bezahlen` · **LIVE** (blockiert) · Risikoklasse erhoeht · 5 Befund(e)

Datei: `content/posts/2026-09-03-kreditkarte-vergleichen-kostenlos-sicher-bezahlen/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `16b3b8584ff802803aa9` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Angaben zum Fremdwährungsentgelt von „fast zwei Prozent“ bei Zahlungen in fremder Währung fehlen jede belegbare Referenz. | – |
| `7ff042b6fe804cdf101b` | praezision | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Formulierungen wie „einige Anbieter ohne Auslandsgebühr gehören zu den besten Karten für Reisen“ sind pauschal und ohne messbare Daten unpräzise. | – |
| `bec83c4b814183fa1086` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass die kostenlose Sperr‑Notrufnummer 116 für alle Karten in Deutschland gilt, wird nicht durch eine Quelle gestützt. | – |
| `f9aff86b6eba71b153a6` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Angabe, dass Sollzinsen bei Teilzahlung zwischen 12 % und 20 % liegen, ist nicht mit einer Quelle belegt. | – |
| `fed9215b770ea4879eda` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Behauptung, dass eine gute Kreditkarte im Jahr nichts kostet (keine Jahres‑ und keine Fremdwährungsgebühr), wird ohne jegliche Quelle angegeben. | – |

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
| `20c08cb650ef6e24af64` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Ratgeber vernachlässigt bei der Kalkulation der Sparfähigkeit die massive Preissteigerung bei Energie (+14,9 %), die das Budget für monatliche Sparraten erheblich belastet. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `6aafb23c0c6dbb06ce3b` | veraltet | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die im Rechenbeispiel zur Realrendite genutzte Inflationsrate von 2 % ist veraltet; die vorläufige Rate für Oktober 2026 beträgt laut Statistischem Bundesamt 2,8 %. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 20c08cb650ef6e24af64 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6aafb23c0c6dbb06ce3b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-07-frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-09-07-frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `24f05ddc03ffdd50118f` | praezision | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Kalkulation der Fixkostenersparnis bei Energie (Strom/Gas) ist unpräzise, da sie den aktuellen Preisanstieg von +14,9 % bei Energieprodukten nicht einbezieht. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `4816322f061dfdc03bcd` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Bei den Einsparpotenzialen für Lebensmittel fehlt der Bezug zur aktuellen Preissteigerung von +0,4 % bei Nahrungsmitteln. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `7017065ee7c74c7ae452` | veraltet | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel nutzt Kostenszenarien für 2024/2025, während aktuelle Daten für Oktober 2026 eine Inflationsrate von +2,8 % ausweisen. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 24f05ddc03ffdd50118f --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 4816322f061dfdc03bcd --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7017065ee7c74c7ae452 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-05-waschmaschine-beladen-weniger-kosten-bei-jedem-waschgang` · **LIVE** (blockiert) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-11-05-waschmaschine-beladen-weniger-kosten-bei-jedem-waschgang/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `4284fd2d9c9005e7af8f` | praezision | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Behauptung, dass Überladung der Maschine zu schnellerem Verschleiß und teuren Reparaturen führt, wird ohne konkrete Daten oder Messgröße angegeben. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `84e247f17354e224c973` | praezision | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Aussage, dass das richtige Beladen allein die Fixkosten senkt, ohne weitere Maßnahmen, ist ein pauschales Leistungsversprechen ohne Nennung von Mechanismen oder Grenzen. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `a2a7dc69f10393af6531` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Modellrechnung (0,9 kWh/50 L bei vollem Waschgang, 0,6 kWh/35 L bei halbem Waschgang, Strompreis 0,40 €/kWh, Wasserpreis 0,005 €/L) und die daraus resultierende Jahresersparnis von 22 € fehlen einer fundierten Quelle. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `cb794331f1cc0c715a55` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass bei 4 Waschgängen pro Woche ein durchschnittlicher Haushalt rund 5 € jährlich an Strom‑ und Wasserkosten spart, ist nicht mit einer Quelle belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `e6729081522126e972c2` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Angabe, dass ein optimal beladener Trommel (ca. 80 % Kapazität) bis zu 15 % weniger Wasser und Energie verbraucht, wird nicht durch eine Quelle belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

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
| `1e06a96f6f71e104ce0b` | praezision | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Während Meal Prep als großer Sparhebel betont wird, zeigt die Marktlage für Nahrungsmittel eine moderate Teuerung von nur 0,4 %, was die Priorisierung der Sparbemühungen relativiert. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `81c6a707139046b83ccd` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Ratgeber empfiehlt die Revision von Fixkosten, lässt aber die drastische Preissteigerung bei Energie von +14,9 % unerwähnt, die ein wesentlicher Treiber der Haushaltsausgaben ist. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `8cc00288af8a1f2b02d8` | veraltet | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Budget-Tipps berücksichtigen nicht die aktuelle Inflationsrate von 2,8 % (Stand Oktober 2026), was die Kaufkraft-Annahmen im Haushaltsbuch beeinflusst. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 1e06a96f6f71e104ce0b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 81c6a707139046b83ccd --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 8cc00288af8a1f2b02d8 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `5a1bf10697f58e5fe14a` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Ratgeber nennt Sparbeispiele für Heizkosten, lässt aber die aktuelle Preissteigerung bei Energie von +14,9 % (Stand Oktober 2026) unerwähnt, die den finanziellen Druck auf Haushalte massiv erhöht. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `e48f9237cff6397c49a6` | praezision | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die in Aussicht gestellten Ersparnisse von bis zu 200 € werden nicht ins Verhältnis zur aktuellen Inflationsrate von +2,8 % gesetzt, welche die reale Kaufkraft des gesparten Geldes mindert. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `f6de6b078d49f9d42e0e` | praezision | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Beim Fokus auf Lebensmittelplanung fehlt der Hinweis auf die vergleichsweise moderate Preissteigerung von +0,4 % bei Nahrungsmitteln, was diesen Hebel gegenüber den stark steigenden Energiekosten relativiert. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 5a1bf10697f58e5fe14a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e48f9237cff6397c49a6 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f6de6b078d49f9d42e0e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-11-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026` · **LIVE** (blockiert) · Risikoklasse standard · 2 Befund(e)

Datei: `content/posts/2026-09-11-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `6cb2229c5eb83b02da23` | veraltet | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Kalkulation der Fixkosten (Energie 140 €) und die Empfehlung zur Senkung der Kosten ignorieren den aktuellen Markttrend massiv steigender Energiepreise (+14,9 %), was die 50-Prozent-Quote für notwendige Ausgaben gefährdet. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `f00055a1cb65ee22165f` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Ratgeber verspricht eine 'planbare' Budgetierung, lässt aber die aktuelle Inflationsrate von 2,8 % unerwähnt, die insbesondere den Block der notwendigen Ausgaben (Nahrungsmittel +0,4 %) dynamisch belastet. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6cb2229c5eb83b02da23 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f00055a1cb65ee22165f --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden` · **LIVE** (blockiert) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `43470330b3b48c9cee49` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel empfiehlt, Kühl- und Gefriergeräte mindestens 24 Stunden, besser mehrere Tage zu messen, liefert jedoch keine Quelle für diese Messdauer. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `8ddc1025e45be176ad3a` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Es wird kein regulatorischer Rahmen (z. B. Aufgaben der Bundesnetzagentur) genannt, obwohl das Thema Stromversorgung berührt wird; entsprechende Vorgaben fehlen im Text. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `95d6d2877620e5a056ce` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass Verbraucherzentralen oder Bibliotheken Messgeräte verleihen, wird ohne Beleg gemacht. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `ab16029999747466a638` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Berechnung mit einem Arbeitspreis von 0,37 €/kWh wird angegeben, ohne dass ein aktueller Preis‑ oder Marktwert belegt wird. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `b057dee3603e09f494b5` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Das Amortisationsbeispiel (Kaufpreis 650 €, Amortisationszeit 10,3 Jahre) enthält keine Quelle für die zugrunde liegenden Annahmen oder Preise. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 43470330b3b48c9cee49 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 8ddc1025e45be176ad3a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 95d6d2877620e5a056ce --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ab16029999747466a638 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden b057dee3603e09f494b5 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-26-warmwasser-sparen-rechnung-hinter-dem-hahn` · **LIVE** (blockiert) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-08-26-warmwasser-sparen-rechnung-hinter-dem-hahn/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `278d89267d9122a1e9d8` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Angaben zu gesetzlichen Vorgaben für Warmwassertemperaturen zur Vermeidung von Legionellen werden nicht durch die bereitgestellten Quellen gestützt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `450c3aa629342062825e` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass Warmwasser der zweitgrößte Kostenposten im Haushalt ist, wird nicht durch eine der bereitgestellten Quellen belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `7601167c9f3560093fb0` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Behauptung, dass Warmwasser in der Heizkostenabrechnung üblicherweise als eigener Block ausgewiesen wird, fehlt eine Quellenangabe. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `7efbcd7a4275fe1577bb` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Verweise auf die Verbraucherzentrale (Tipps zum Heizkosten sparen, Heizung optimieren) können nicht mit den angegebenen Fundstellen belegt werden. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `971a719f94ca492f640e` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Preis von 0,30 € pro Kilowattstunde in der Modellrechnung ist nicht mit einer Quelle belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 278d89267d9122a1e9d8 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 450c3aa629342062825e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7601167c9f3560093fb0 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7efbcd7a4275fe1577bb --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 971a719f94ca492f640e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-30-last-minute-urlaub-so-schnappst-du-dir-das-sommer-schnaepp` · **LIVE** (blockiert) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-09-30-last-minute-urlaub-so-schnappst-du-dir-das-sommer-schnaepp/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `33278b9e7942ebfdbbac` | luecke | 0 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Definition des Begriffs „Last Minute“ (maximal 14 Tage zwischen Buchung und Abreise) wird mit dem Deutschen Reiseverband angegeben, jedoch fehlt ein Nachweis. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `6ad7358a9afcfef3babb` | praezision | 0 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Angabe, dass Preisalarme keinen Tiefstpreis garantieren, wird nicht durch konkrete Zahlen oder Vergleichsstudien belegt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `7c375a3e1a9bfab1468c` | luecke | 0 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Hinweis auf § 651r BGB (Insolvenzsicherung bei Pauschalreisen) enthält keinen Verweis auf eine Rechtsquelle oder Verbraucherzentrale‑Information. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `ea11d36614fa115503b4` | luecke | 0 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Behauptung, dass Nachlässe von bis zu 50 % nur Einzelfälle sind, wird ohne Quellenangabe präsentiert. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `f7b1c869dd8e442eaf16` | praezision | 0 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Aussage, dass der „beste Zeitpunkt zum Buchen“ ein Modellwert sei, bleibt vage und ohne messbare Daten oder Studien untermauert. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 33278b9e7942ebfdbbac --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6ad7358a9afcfef3babb --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7c375a3e1a9bfab1468c --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ea11d36614fa115503b4 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f7b1c869dd8e442eaf16 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-11-standby-kosten-reduzieren-so-entlarvst-du-stromfresser` · **LIVE** (blockiert) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-09-11-standby-kosten-reduzieren-so-entlarvst-du-stromfresser/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `7a87eaaa2b863ba8cc46` | luecke | 1 T | Text unverändert seit dem Befund | Ein relevanter regulatorischer Rahmen (z. B. Vorgaben der Bundesnetzagentur oder BDEW) wird nicht genannt, obwohl die Fundstelle darauf hinweist, dass solche Vorgaben existieren. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `9d67a5e6bd11212c7c1e` | praezision | 1 T | Text unverändert seit dem Befund | Die Aussage, dass bestimmte Gerätegruppen (TV‑Ecke, Homeoffice, alte Audio‑Technik) zuerst zu senken „lohnt“, wird ohne messbare Daten oder Vergleichskriterien gemacht. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `a54abc1cad73d20fb689` | luecke | 1 T | Text unverändert seit dem Befund | Die konkreten Jahreskosten (z. B. 32 € für 10 W Standby) beruhen auf dem nicht belegten Strompreis und werden nicht als Modellrechnung gekennzeichnet. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `a7d1cf6485921e117919` | luecke | 1 T | Text unverändert seit dem Befund | Der angegebene durchschnittliche Strompreis von 37,3 Cent/kWh (BDEW‑Schnitt) wird ohne Quellenangabe genannt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `a7f69a854430d62a4a3e` | luecke | 1 T | Text unverändert seit dem Befund | Die Empfehlung, dass ein günstigerer Arbeitspreis der zweite wichtigste Hebel sei, fehlt jede Quelle oder regulatorische Einordnung. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7a87eaaa2b863ba8cc46 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 9d67a5e6bd11212c7c1e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a54abc1cad73d20fb689 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a7d1cf6485921e117919 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a7f69a854430d62a4a3e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-25-strategisch-sparen-so-kannst-du-deine-reisekasse-fuellen` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-10-25-strategisch-sparen-so-kannst-du-deine-reisekasse-fuellen/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `98eb45f772ad7a0aac7b` | luecke | 0 T | Text unverändert seit dem Befund | Das Sparversprechen von '500 € mehr' in der PIN-Beschreibung nutzt im Text Referenzwerte (120 € Strom, 80 € Kfz), für die in der Quelle keine Marktdaten oder Durchschnittswerte als Beleg vorliegen. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `b7f0d52968d89cdf8c5b` | praezision | 0 T | Text unverändert seit dem Befund | Die Einschätzung zur Datensicherheit von Cashback-Apps bleibt ohne Nennung konkreter rechtlicher Grundlagen (DSGVO) unpräzise, während die Quelle explizit auf rechtliche Verbraucherthemen fokussiert. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `be911855d67f998be662` | luecke | 0 T | Text unverändert seit dem Befund | Der Ratgeber nennt keinen Regulierungsrahmen für Reisebuchungen (z. B. Fluggastrechte oder Stornierungsregeln), obwohl die Quelle diese als zentrale Informationsbereiche ausweist. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 98eb45f772ad7a0aac7b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden b7f0d52968d89cdf8c5b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden be911855d67f998be662 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-02-last-minute-urlaubsangebote-sichern` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-11-02-last-minute-urlaubsangebote-sichern`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `0a2bec9dc02e16c057ee` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die 50‑30‑20‑Regel für die Urlaubsbudget‑Aufteilung wird ohne Quellenangabe präsentiert. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `274c32d1a16e9dffcf1a` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Angabe, dass das Weglassen der Vollkasko‑Selbstbeteiligung die Kosten um 10 % bis 20 % senken kann, ist nicht mit einer Quelle belegt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `5c572a933edece129bba` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass Stornogebühren häufig einem Tagespreis entsprechen, ist unbelegt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `9d9d4afc8d6c421a0d14` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Behauptung, dass Last‑Minute‑Deals wegen Restkapazitäten zu niedrigeren Preisen führen, fehlt eine fundierte Quelle. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `fb50388539a0e8b4461c` | praezision | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Empfehlung, ausschließlich CHECK24 für den Mietwagenvergleich zu nutzen, ist ein unqualifiziertes Superlativ ohne Messgrundlage. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 0a2bec9dc02e16c057ee --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 274c32d1a16e9dffcf1a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 5c572a933edece129bba --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 9d9d4afc8d6c421a0d14 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden fb50388539a0e8b4461c --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-10-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-11-10-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu`

Herkunft nach Datums-Lift: `2026-11-01-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu` → `2026-11-10-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu`. Befund-ID und Fassungsanker bleiben unverändert; das Re-Dating ist keine fachliche Entscheidung.

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `0b564f460c41218244bd` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel behauptet, dass Heizöl‑Preise ihr Tief meist in den Monaten Januar und Februar erreichen, ohne dafür eine Quelle anzugeben. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `3ad2eefed314eb172c26` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass durch frühzeitige Bestellung Kosten um 10 % bis 20 % im Herbst eingespart werden können, ist unbelegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `43788c2cdcdfda52e753` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Modellrechnung verwendet einen Tiefpreis von 0,80 €/Liter, ohne dass diese Preisangabe belegt wird. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `5eedec8afbdef6a4ca49` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Es wird angegeben, dass typische Fehler beim Heizölkauf bis zu 15 % Mehrkosten verursachen können, jedoch fehlt ein Nachweis für diese Zahl. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `81881c5bc61824d25f5a` | praezision | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Faustregel, dass man bestellen sollte, wenn Preise vier Wochen unter dem Schnitt der letzten 12 Monate liegen, wird ohne Messgrundlage oder Quelle genannt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 0b564f460c41218244bd --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 3ad2eefed314eb172c26 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 43788c2cdcdfda52e753 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 5eedec8afbdef6a4ca49 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 81881c5bc61824d25f5a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-04-guenstigen-mietwagen-fuer-den-urlaub-buchen` · nicht im Live-Bestand · 4 Befund(e)

Seite: `2026-11-04-guenstigen-mietwagen-fuer-den-urlaub-buchen`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `785eee76d888bb05ad96` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die im Rechenbeispiel genutzte Kilometerpauschale von 0,20 €/km wird als Referenzwert ohne Quellenangabe (z. B. Branchenverband) angeführt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `843ec148e23841b7bf35` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der als Handlungsschritt empfohlene '4K-Prüfpfad' wird im Text nicht erläutert und ist in der genannten Quelle nicht enthalten. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `def43a04853be4c35f7f` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Preisprognose (Anstieg in den letzten 3 Wochen) und der empfohlene Buchungsvorlauf (3-4 Wochen) sind Marktdaten ohne Beleg durch die Fachquelle. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `f064ea49ccefde26aef9` | praezision | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Das Versprechen, CHECK24 vergleiche 'alle großen Anbieter', ist ein Vollständigkeitsversprechen ohne Nennung von Auswahlkriterien oder der Marktabdeckung. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

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
| `82cc87314e0d4fcb21e9` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die kalkulierte Ersparnis bei Energiekosten (15 €/Monat) berücksichtigt nicht den aktuellen Markttrend massiv steigender Preise (+14,9 % bei Energie). | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `bd5ee70c85ec7db78f26` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die pauschalen Jahressparwerte von 300 € bis 1.000 € werden in Marktfakten-Positur ohne Nennung einer Referenzquelle oder eines Absenders (z. B. Destatis) aufgeführt. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `f83f21c1f2e2012f672e` | praezision | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Sparversprechen im Bereich Lebensmittel vernachlässigen die Inflationsrate bei Nahrungsmitteln (+0,4 %), was Modellrechnungen ohne Inflationsbereinigung ungenau macht. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 82cc87314e0d4fcb21e9 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden bd5ee70c85ec7db78f26 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f83f21c1f2e2012f672e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-06-guenstige-fluege-fuer-den-spaetsommer-finden` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-11-06-guenstige-fluege-fuer-den-spaetsommer-finden`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `0e68294e193918d5b5b0` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Text nennt eine angeblich gängige Faustregel von 20 % Rabatt im Spätsommer (Beispiel 300 € → 240 €) ohne Quellenangabe. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `4d91ef71fa76febdb769` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Es wird angegeben, dass Flüge an Dienstagen und Mittwochen günstiger seien und an Freitagen bzw. Sonntagen teurer, ohne Beleg. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `5b427fb4f05b475d9a89` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Empfehlung, Flüge vier bis acht Wochen im Voraus zu buchen, weil die Preise dann am niedrigsten seien, wird nicht belegt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `e933e34672f0b6464d1e` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel behauptet, dass im Spätsommer die Nachfrage nach Flügen sinkt und dadurch die Preise fallen, ohne dafür eine Quelle anzugeben. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `eb6a47df5535fa267a82` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Behauptet wird, dass Kombi‑Deals für Flug + Mietwagen typischerweise 5–15 % Einsparungen bringen, ohne Nachweis. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

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
| `0f248aaad2d2b8d87d0d` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die im Marktradar angegebenen Durchschnittspreise für Strom (37,3 ct/kWh) und Gas (12,23 ct/kWh) werden ohne Quellenangabe genannt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `3a69bd57886154a18b8e` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass bei Preiserhöhungen ein gesetzliches 14‑tägiges Sonderkündigungsrecht besteht, fehlt eine rechtliche Quellenangabe. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `4f777954306ac7b21e03` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Behauptung, dass ein Lieferantenwechsel und ein technischer Anschlusswechsel nicht dasselbe seien, wird nicht durch eine Quelle belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 0f248aaad2d2b8d87d0d --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 3a69bd57886154a18b8e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 4f777954306ac7b21e03 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-09-reisekasse-fuellen-7-wege-zu-mehr-budget-fuer-den-urlaub` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-11-09-reisekasse-fuellen-7-wege-zu-mehr-budget-fuer-den-urlaub`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `11a92bff688ccbb5a485` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Behauptung, dass bis zum Sommer 500 € mehr im Urlaubsbudget verfügbar sind, fehlt eine Quellenangabe. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `1d4896d8ed60f5b6921f` | praezision | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass Cashback‑Portale „seit vielen Jahren am Markt etabliert“ sind, ist ein unpräzises Superlativ ohne messbare Daten. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `4d2bc6c3e60fb9b4a719` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass eine 5 %ige Reduktion der Fixkosten bei 800 € Aufwand 40 € im Monat bzw. 480 € im Jahr spart, wird nicht durch die angeführte Quelle belegt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `76b5cdfda85516962cf8` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Angaben zu typischen Kündigungsfristen von ein bis drei Monaten werden von der Quelle nicht bestätigt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `b292db236a31ea0a1629` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der genannte durchschnittliche Cashback‑Satz von 2 % der Ausgaben ist nicht durch die Quelle gestützt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 11a92bff688ccbb5a485 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 1d4896d8ed60f5b6921f --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 4d2bc6c3e60fb9b4a719 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 76b5cdfda85516962cf8 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden b292db236a31ea0a1629 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-10-strompreis-2026-herbst-check-fuer-deine-stromkosten` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-11-10-strompreis-2026-herbst-check-fuer-deine-stromkosten`

Herkunft nach Datums-Lift: `2026-11-09-strompreis-2026-herbst-check-fuer-deine-stromkosten` → `2026-11-10-strompreis-2026-herbst-check-fuer-deine-stromkosten`. Befund-ID und Fassungsanker bleiben unverändert; das Re-Dating ist keine fachliche Entscheidung.

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `1c6e4d2f12da24ec4081` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Hinweis, dass ein Anbieterwechsel im Durchschnitt 3‑6 Wochen dauert, fehlt eine nachweisbare Quelle. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `5b539daf371f7362a3ef` | praezision | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Empfehlung, dynamische Tarife erforderten zwingend einen Smart Meter, wird ohne Angabe von Voraussetzungen, Kosten oder Verfügbarkeit präzisiert. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `77d809de9e06d1d6910d` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Es wird eine Prognose für den Strompreis 2026 angegeben („Trends erkennen“, „Netzentgelte steigen“), ohne dass dafür aktuelle Marktdaten oder offizielle Prognosen genannt werden. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `ad7c0a90ef52ff35130e` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel behauptet, dass Preisgarantien vor Preissteigerungen schützen, liefert jedoch keine Quelle für diese Aussage. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `f227178fbda2cc59c350` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass Ökostrom‑Tarife häufig günstiger als die Grundversorgung seien, wird nicht durch eine Quelle belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 1c6e4d2f12da24ec4081 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 5b539daf371f7362a3ef --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 77d809de9e06d1d6910d --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ad7c0a90ef52ff35130e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f227178fbda2cc59c350 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-28-dsl-und-internet-flat-guenstig-sichern` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-10-28-dsl-und-internet-flat-guenstig-sichern`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `05be346e82c80b2a8664` | luecke | 12 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Wechselboni von 50 € bis 100 € werden genannt, jedoch fehlt jede belegbare Angabe zu deren Höhe oder Häufigkeit. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `d0a5cf7bb64eb0cd46c8` | luecke | 12 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Der Artikel erwähnt keinen regulatorischen Rahmen (z. B. Informations‑ und Preisbindungspflichten der Bundesnetzagentur) obwohl die Fundstelle darauf hinweist, dass solche Vorgaben existieren. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `ec53e181336df8dc61ac` | luecke | 12 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Der Artikel behauptet, dass DSL‑Verträge häufig eine Laufzeit von 24 Monaten haben und danach eine Kündigungsfrist von einem Monat gilt, ohne dafür eine Quelle anzugeben. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `f3f9184bfca9b097f68e` | luecke | 12 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die 50‑30‑20‑Regel wird als allgemein gültige Budget‑Methode dargestellt, ohne Hinweis, dass es sich um ein Modell handelt oder Quelle dafür zu nennen. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `fb4d2260f4fa291c35ae` | praezision | 12 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Angabe, dass für zwei HD‑Streams gleichzeitig etwa 30 Mbit/s benötigt werden, ist nicht durch Daten belegt und lässt Spielraum für Fehlinterpretationen. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 05be346e82c80b2a8664 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d0a5cf7bb64eb0cd46c8 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ec53e181336df8dc61ac --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f3f9184bfca9b097f68e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden fb4d2260f4fa291c35ae --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-08-energie-update-was-sich-jetzt-fuer-dich-aendert` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-10-08-energie-update-was-sich-jetzt-fuer-dich-aendert`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `1d448c9cdc2618ef9bdf` | luecke | 1 T | Text unverändert seit dem Befund | Der Hinweis, dass Festpreis‑Tarife in der Regel einen Aufschlag enthalten, fehlt jede Beleggrundlage. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `2188f6b0006eb0607871` | luecke | 1 T | Text unverändert seit dem Befund | Die Behauptung, die Bundesnetzagentur fordere die getrennte Angabe von Grund‑ und Arbeitspreis, wird nicht durch die verlinkte Quelle belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `33917254a91a1c551389` | praezision | 1 T | Text unverändert seit dem Befund | Die Aussage, dass variable Tarife mit Preisgarantie oder Deckel im Vergleich „selten ganz oben“ stehen, ist ein untermauertes Superlativ ohne Messgröße. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `82badcfa80493134c12a` | luecke | 1 T | Text unverändert seit dem Befund | Die Aussage, dass variable Tarife das Marktpreisrisiko vollständig auf den Kunden übertragen, wird ohne Quellenangabe gemacht. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `b44fd9621fb708f45c90` | luecke | 1 T | Text unverändert seit dem Befund | Die Behauptung, dass sich die Energiemärkte 2026 wieder stärker bewegen, wird ohne aktuelle Marktdaten belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 1d448c9cdc2618ef9bdf --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 2188f6b0006eb0607871 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 33917254a91a1c551389 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 82badcfa80493134c12a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden b44fd9621fb708f45c90 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-09-handytarife-vergleichen-so-findest-du-den-guenstigsten-tarif` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-11-09-handytarife-vergleichen-so-findest-du-den-guenstigsten-tarif`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `3efe31a371440636f465` | luecke | 1 T | Text unverändert seit dem Befund | Empfehlung, den Handytarif einmal jährlich bzw. vierteljährlich zu prüfen, fehlt eine Quellenangabe. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `49c1a762c2df16c52b7a` | luecke | 1 T | Text unverändert seit dem Befund | Der Artikel behauptet, dass Verträge nach sechs Monaten die Preise erhöhen, ohne dafür eine Quelle anzugeben. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `56c5b1f92a70c6ebeb0b` | praezision | 1 T | Text unverändert seit dem Befund | Die Aussage, dass CHECK24 alle aktuellen Angebote liefert, ist ein Vollständigkeitsversprechen ohne Messgröße. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `c6d20c93f94cee2ae5ae` | praezision | 1 T | Text unverändert seit dem Befund | Die Regel „Datenvolumen halbieren, das du wirklich brauchst“ wird als allgemeine Faustregel präsentiert, ohne Messdaten oder Quelle. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `f6a30c4191c47f5cdf0a` | luecke | 1 T | Text unverändert seit dem Befund | Die Faustregel, dass zusätzliche Gebühren mindestens 5 % der Grundgebühr betragen müssen, wird nicht belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |

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
| `6d89862b38c33c827817` | praezision | 1 T | Text unverändert seit dem Befund | Die pauschale Behauptung, Hardware bleibe stets Eigentum des Nutzers, ist unpräzise, da die Bundesnetzagentur die Kupfer-Glas-Migration begleitet, die oft providerseitige Technikwechsel und neue Netzabschlusspunkte erfordert. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `72bbf29e4ef70a71ad06` | luecke | 1 T | Text unverändert seit dem Befund | Aussagen zu Markttrends wie hohen Neukundenrabatten und Wechselprämien werden als Marktfakten ohne Bezug zu offiziellen Referenzwerten oder Berichten der Aufsichtsbehörde dargestellt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `f0103f4c6a777aaa4845` | luecke | 1 T | Text unverändert seit dem Befund | Der Ratgeber thematisiert den Anbieterwechsel und Bandbreiten, lässt aber den regulatorischen Rahmen der Bundesnetzagentur zur Breitbandversorgung und zum Verbraucherschutz bei Minderleistung unerwähnt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6d89862b38c33c827817 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 72bbf29e4ef70a71ad06 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f0103f4c6a777aaa4845 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-29-konto-karten-update-was-sich-jetzt-fuer-dich-aendert` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-09-29-konto-karten-update-was-sich-jetzt-fuer-dich-aendert`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `2140cb752c4069ae86a0` | luecke | 0 T | Text unverändert seit dem Befund | Für die herkömmliche Girocard werden häufig Gebühren von etwa 0,99 Euro monatlich erhoben – Angabe fehlt in den bereitgestellten Quellen. | [Quelle](https://www.verbraucherzentrale.de/aktuelle-meldungen) |
| `766e3df5f10bb91ff03b` | luecke | 0 T | Text unverändert seit dem Befund | Ein schneller Kontowechsel sei jederzeit kostenlos und sichere dauerhaft die besten Zinsen – diese Aussage fehlt in den bereitgestellten Quellen. | [Quelle](https://www.tagesschau.de/wirtschaft/unternehmen/faq-nvidia-spionage-100.html) |
| `d11731ee598db94f14c0` | luecke | 0 T | Text unverändert seit dem Befund | Die Maestro‑Funktion soll seit Juli 2023 schrittweise eingestellt werden – keine Quelle dafür vorhanden. | [Quelle](https://www.verbraucherzentrale.de/aktuelle-meldungen) |
| `ef34d0d6243902be1bc9` | luecke | 0 T | Text unverändert seit dem Befund | Befristete Sonderzinsen bei Tagesgeldkonten und deren starke Absenkung nach der Aktionsphase werden behauptet, ohne dass die angegebenen Quellen dies belegen. | [Quelle](https://www.tagesschau.de/wirtschaft/unternehmen/faq-nvidia-spionage-100.html) |
| `f48dd250f165f647c90a` | luecke | 0 T | Text unverändert seit dem Befund | Viele Banken stellen ihre Standardkarten auf kostenlose Debit‑Visas oder Mastercards um – ohne aktuelle Quelle belegt. | [Quelle](https://www.verbraucherzentrale.de/aktuelle-meldungen) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 2140cb752c4069ae86a0 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 766e3df5f10bb91ff03b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d11731ee598db94f14c0 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ef34d0d6243902be1bc9 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f48dd250f165f647c90a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-14-heizperiode-vorbereiten-im-spaetsommer` · nicht im Live-Bestand · 2 Befund(e)

Seite: `2026-10-14-heizperiode-vorbereiten-im-spaetsommer`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `61ed9d03642fa5afa89e` | praezision | 0 T | Text unverändert seit dem Befund | Die pauschale Einordnung der Behördenseite als 'kein Beleg für Tipps' greift zu kurz; die Fundstelle ist das zentrale Aufsichtsportal für den regulierten Energiemarkt (Strom/Gas). | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `bbd476563a6a52c57957` | luecke | 0 T | Text unverändert seit dem Befund | Der Artikel verweist für Informationen zum Stromverbrauch von Routern auf die Bundesnetzagentur, verlinkt jedoch die Fachabteilung für Energie statt die zuständige Abteilung für Telekommunikation. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 61ed9d03642fa5afa89e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden bbd476563a6a52c57957 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `frugalismus` · nicht im Live-Bestand · 3 Befund(e)

Seite: `frugalismus`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `760cdea8544be9d1c7c0` | luecke | 0 T | Text unverändert seit dem Befund | Die im 'Zins-Marktradar Q4 2026' genannten Benchmark-Daten für Tagesgeld (3,10–3,45 %) und Dispozinsen (11,5–13,8 %) werden der Bundesbank und BaFin zugeschrieben, sind jedoch in den Recherche-Fundstellen nicht belegt. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `cacd65ac080f79a719ae` | praezision | 0 T | Text unverändert seit dem Befund | Der Ratgeber thematisiert Fixkosten-Senkungen allgemein, lässt aber die laut Destatis signifikante Preissteigerung bei Energie (+12,2 %) unerwähnt, die den Spielraum für die angestrebte 50-Prozent-Quote prägt. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `d2bfec8aa9b7a0807f0e` | luecke | 0 T | Text unverändert seit dem Befund | Die 50–30–20-Budgetformel wird als Destatis-Standardmodell ausgewiesen; die angegebene Quelle des Statistischen Bundesamtes enthält jedoch nur Daten zum Verbraucherpreisindex, keine Budget-Verteilungsschlüssel. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 760cdea8544be9d1c7c0 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden cacd65ac080f79a719ae --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d2bfec8aa9b7a0807f0e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

---

_Diese Akte entscheidet nichts und schließt nichts. Sie macht sichtbar, was zu entscheiden ist, wer es entscheiden muss (Herausgeber/Redaktion) und wie der Schließweg lautet. Regel: `scripts/faktenfrische_befund_ledger.py`, Governance C46._
