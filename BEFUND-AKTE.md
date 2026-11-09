# BEFUND-AKTE – offene Fachbefunde der Faktenfrische

_Stand 2026-11-09 · erzeugt von `scripts/faktenfrische_befund_akte.py` · Quelle: `data/faktenfrische_queue.json` + `data/faktenfrische_entscheidungen.yaml` (eine Regel, zwei Leser)._

**107 offene Befunde auf 26 Seiten · davon 19 Live-Seiten mit 77 Befunden · ältester 10 Tage · Frist 14 Tage.**

| Kennzahl | Wert |
|---|---|
| Offene Befunde | 107 |
| Seiten betroffen | 26 (davon live: 19) |
| Text seit dem Befund geändert | 92 |
| Altbestand ohne Fassungs-Hash | 15 |
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

> **Wichtig – betrifft 107 von 107 Befunden** (in der Tabelle als Fassung markiert): Der Text ist seit dem Befund bereits geändert worden (Heilung) oder stammt aus dem Altbestand. Die Entscheidung bezieht sich ausdrücklich auf den HEUTIGEN Text – bitte diesen lesen, nicht den alten Befund abnicken. Diese Prüfung kann dir die Maschine nicht abnehmen – sie darf sie aber auch nicht verhindern.

## Seiten

### `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026` · **LIVE** (nicht beweisbar) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `30caa57be394afb62947` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Für den angeführten BDEW-Durchschnittspreis von 11,93 Cent/kWh fehlt in den Recherche-Fundstellen ein entsprechender Beleg. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `32a3ea879f2cf126b3a7` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel lässt den in der Quelle explizit genannten Regulierungsrahmen der 'Unternehmenspflichten' unerwähnt, der für den Schutz der Verbraucher beim Anbieterwechsel zentral ist. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `c583efe1ce02df3ca2d7` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die im Artikel genannte Ersparnis-Berechnung der Bundesnetzagentur für Januar 2026 (360 €) wird durch die allgemeine Übersichtsseite der Behörde nicht gestützt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 30caa57be394afb62947 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 32a3ea879f2cf126b3a7 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden c583efe1ce02df3ca2d7 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden` · **LIVE** (nicht beweisbar) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `437b809ffbf41e5af434` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Keine Quelle für die Aussage, dass das Gesetz bei einem Tarifwechsel die Grundversorgung garantiert – regulatorischer Rahmen fehlt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `9fbacd9942c2dfa1447f` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Keine Quelle für die Behauptung, dass ein Grad weniger Raumtemperatur rund 6 % Energie einspart – Prozent‑Angabe fehlt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `da30cbb5fbc8c801daf0` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Keine Quelle für die Angabe, dass durch Optimierungsmaßnahmen 10‑15 % Einsparungen realistisch sind – Prozent‑Wert unbelegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `db8a69f08dc0020adebd` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Keine Quelle für die Aussage, dass im Oktober 2026 bessere Gaspreise gelten – Preis‑Trend‑Behauptung fehlt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `e834f4702e87194affe7` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Keine Quelle für die Angabe, dass ein Einfamilienhaus typischerweise 18.000 kWh/Jahr verbraucht – Verbrauchszahl ist unbelegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 437b809ffbf41e5af434 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 9fbacd9942c2dfa1447f --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden da30cbb5fbc8c801daf0 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden db8a69f08dc0020adebd --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e834f4702e87194affe7 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen` · **LIVE** (nicht beweisbar) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `252413dcc16cea146beb` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel behauptet, dass eine Preisänderung meist einen Monat vorher angekündigt werden muss, ohne dafür eine Quelle anzugeben. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `48a0a962046c8315270e` | praezision | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Behauptung, dass eine Preisgarantie einen Teil des Risikos auf den Anbieter überträgt und dafür ein höherer Startpreis üblich ist, fehlt eine konkrete Quelle und bleibt vage. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `9326152f4d788cff56bd` | praezision | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass man „in der Regel“ zum Zeitpunkt der Preisänderung Sonderkündigungsrecht hat, ist unpräzise und wird nicht durch eine konkrete Regelung belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `ab4d084fd367c8e4d518` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der angegebene durchschnittliche Gaspreis von 11,93 Cent/kWh für 2026 (laut BDEW) wird nicht durch eine Quelle belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `d215addd22dea72c44df` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Angabe, dass die Verbraucherzentrale etwa 6 % weniger Heizenergie pro Grad niedrigerer Raumtemperatur nennt, fehlt eine Quellenangabe. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 252413dcc16cea146beb --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 48a0a962046c8315270e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 9326152f4d788cff56bd --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ab4d084fd367c8e4d518 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d215addd22dea72c44df --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-20-gasrechnung-senken-so-bereitest-du-dich-im-spaetsommer-vor` · **LIVE** (nicht beweisbar) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-09-20-gasrechnung-senken-so-bereitest-du-dich-im-spaetsommer-vor/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `0aa915539d57841e5014` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass die Verbraucherzentrale empfiehlt, Boni im ersten Vergleich auszublenden, fehlt eine Quellenangabe. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `5e1be48085014a836807` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der angegebene BDEW‑Durchschnittspreis von 11,93 Cent/kWh für 2026 wird nicht belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `6fdf31c3b68b6122bd0d` | praezision | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die pauschale Formulierung, dass bei zentraler Heizung der Vermieter oder die Eigentümergemeinschaft den Anbieter wählt, ist zu ungenau und nicht belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `c27c182c615bd7ca3b78` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel behauptet, dass laut Bundesnetzagentur Preisänderungen klar angekündigt und begründet sein müssen, liefert jedoch keinen Beleg dafür. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `e1e40e9bbbdd109df86e` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Es wird angegeben, dass bei einer Preisänderung in der Regel ein Sonderkündigungsrecht besteht, ohne dafür eine Quelle zu nennen. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 0aa915539d57841e5014 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 5e1be48085014a836807 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6fdf31c3b68b6122bd0d --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden c27c182c615bd7ca3b78 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e1e40e9bbbdd109df86e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-20-gasrechnung-senken-spaetsommer-check-spart-hunderte-euro` · **LIVE** (nicht beweisbar) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-09-20-gasrechnung-senken-spaetsommer-check-spart-hunderte-euro/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `334751e6f61ad0033fe4` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Angabe, dass ein Gaslieferantenwechsel bei 20.000 kWh im Januar 2026 im Schnitt etwa 360 € spart, fehlt jede Quellenangabe. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `36759a5efe5e8e5163d0` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Faustregel der Verbraucherzentrale, dass pro Grad weniger Raumtemperatur der Heizbedarf um etwa 6 % sinkt, wird ohne Quelle angegeben. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `942922d1afd7844618e9` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Rechnung „1 Cent pro kWh bei 18.000 kWh Jahresverbrauch ergibt rund 180 € im Jahr“ wird nicht belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `d41f0d5ce8798df0211b` | praezision | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage „Die besten Tarife findest du über unseren Partner‑Vergleich“ ist ein Superlativ ohne messbare Daten oder Vergleichskriterien. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `e139d0769faadd04392a` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der BDEW‑Durchschnittspreis von 11,93 Cent/kWh für 2026 wird ohne Quellenangabe genannt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 334751e6f61ad0033fe4 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 36759a5efe5e8e5163d0 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 942922d1afd7844618e9 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d41f0d5ce8798df0211b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e139d0769faadd04392a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-02-weihnachten-budget-planen-ohne-schulden-durch-die-feiertage` · **LIVE** (nicht beweisbar) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-10-02-weihnachten-budget-planen-ohne-schulden-durch-die-feiertage/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `58f03a64adaaf8125959` | praezision | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Während der Artikel vor hohen Kosten für Festmenüs warnt, liegt die Preissteigerung bei Nahrungsmitteln laut Destatis im Oktober 2026 bei lediglich +0,4 % und damit deutlich unter der allgemeinen Inflation. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `a7f5f01ef15a38839a0d` | praezision | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Pauschale für 'Anreise und Mobilität' (10 % des Budgets) berücksichtigt nicht die überdurchschnittliche Preissteigerung bei Energie von +14,9 %, die Fahrtkosten im Vergleich zum Vorjahr massiv verteuern kann. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `bcc2bdf06220d5097133` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Modellrechnung für das Weihnachtsbudget (600 €) lässt die aktuelle Teuerungsrate unberücksichtigt. Laut Statistischen Bundesamt liegt die Inflationsrate im Oktober 2026 bei +2,8 %, was als Referenzwert für die Budgetplanung zum Vorjahr fehlt. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 58f03a64adaaf8125959 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a7f5f01ef15a38839a0d --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden bcc2bdf06220d5097133 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust` · **LIVE** (nicht beweisbar) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `089b89138417e63a3dcf` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Es fehlt der für Campingbuchungen relevante Regulierungsrahmen (Unterscheidung Mietrecht bei Stellplätzen vs. Reiserecht), den die Fundstelle für den Bereich Reise nur allgemein andeutet. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `1158934e7a18c7b2099b` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Preisangabe von 20 bis 45 € pro Nacht wird als realistischer Wert positioniert, ist jedoch nicht durch Marktdaten oder eine Referenzstelle in den Fundstellen belegt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `3716cfd3ab5aec6d774b` | praezision | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Verweis auf die Verbraucherzentrale zur Prüfung von Buchungsangaben führt auf eine allgemeine Übersichtsseite ohne konkrete Checklisten für Camping-Angebote. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 089b89138417e63a3dcf --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 1158934e7a18c7b2099b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 3716cfd3ab5aec6d774b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen` · **LIVE** (nicht beweisbar) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `7067eabb89a917ae67a4` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Verbraucherzentrale sammelt Hinweise zu Reisebuchungen, auch zu unklaren Angeboten und Problemen mit Online-Buchungen. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `af2ccb4222eeb195222f` | praezision | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Ein Mietwagenvergleich kann Angebote sichtbar machen, prüft aber nicht automatisch, ob das Auto zum individuellen Urlaub passt – ohne Messgröße bleibt die Aussage ungenau. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `d9c8b522bf1dcaed0340` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Verbraucherzentrale beschreibt, dass sich eine Pauschalreise unter bestimmten Bedingungen auf eine andere Person übertragen lässt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `e2975509f3f130de0755` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Verbraucherzentrale empfiehlt, größere Ausgaben vorauszuplanen und das eigene Budget im Blick zu behalten. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `f1704e45e970a8f4b078` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Bei einer Pauschalreise gilt die Mitteilung als rechtzeitig, wenn sie dem Veranstalter spätestens sieben Tage vor Reisebeginn zugeht (§ 651e BGB). | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7067eabb89a917ae67a4 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden af2ccb4222eeb195222f --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d9c8b522bf1dcaed0340 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e2975509f3f130de0755 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f1704e45e970a8f4b078 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren` · **LIVE** (nicht beweisbar) · Risikoklasse erhoeht · 5 Befund(e)

Datei: `content/posts/2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `1dbeb2f8c51e78d11d49` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Behauptung, dass klassische Filialbanken jährlich 150 € bis 250 € an reinen Gebühren kosten, ist unbelegt. | – |
| `33e736ac6afe996b491a` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Behauptung, dass Echtzeit‑Überweisungen bei kostenlosen Konten generell gebührenfrei sind, fehlt jede Quelle. | – |
| `96b7b7768d402884810c` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Aussage, dass Einlagen bis 100.000 € durch die deutsche Einlagensicherung geschützt sind, wird nicht belegt. | – |
| `a25bb6bbcb25ba8b0e22` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Angabe von Dispozinsen von 8 % bis 11 % ohne Quellenangabe. | – |
| `f94f8ba1e4342e67e45a` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Angabe, dass ein Kontowechsel 120 € bis 180 € im Jahr spart, fehlt jede Quelle. | – |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 1dbeb2f8c51e78d11d49 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 33e736ac6afe996b491a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 96b7b7768d402884810c --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a25bb6bbcb25ba8b0e22 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f94f8ba1e4342e67e45a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier` · **LIVE** (nicht beweisbar) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `4afb8daed73677ee6224` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Angabe, dass 58 % der Nutzer ihr Haushaltsbuch digital führen, beruft sich angeblich auf Statista 2025, jedoch wird keine Quelle genannt. | – |
| `9eb9a90899cc8ca66020` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Sparpotenzial‑Beispiele (z. B. DSL‑Tarifwechsel von 44 € auf 24 €) enthalten konkrete Zahlen ohne Quellenangabe. | – |
| `b4bd085bc84a6131b644` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Behauptung, dass 60 % der Haushalte in Deutschland ihr Geld nicht nachverfolgen, wird mit einer Auswertung der Stiftung Warentest angegeben, jedoch fehlt ein entsprechender Nachweis. | – |
| `baed76dc211bd15dd46f` | praezision | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Versprechen, dass ein Haushaltsbuch „schnell“ zeigt, welche Posten sich lohnen, ist nicht quantifiziert und fehlt an konkreten Evidenzangaben. | – |
| `d7c3cfb422310cf26ca6` | praezision | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass die 50‑30‑20‑Regel für ein Nettoeinkommen von 2.500 € realistisch sei, wird ohne Hinweis auf regionale Unterschiede oder empirische Daten präsentiert. | – |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 4afb8daed73677ee6224 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 9eb9a90899cc8ca66020 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden b4bd085bc84a6131b644 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden baed76dc211bd15dd46f --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d7c3cfb422310cf26ca6 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-03-kreditkarte-vergleichen-kostenlos-sicher-bezahlen` · **LIVE** (nicht beweisbar) · Risikoklasse erhoeht · 5 Befund(e)

Datei: `content/posts/2026-09-03-kreditkarte-vergleichen-kostenlos-sicher-bezahlen/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `16b3b8584ff802803aa9` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Angaben zum Fremdwährungsentgelt von „fast zwei Prozent“ bei Zahlungen in fremder Währung fehlen jede belegbare Referenz. | – |
| `7ff042b6fe804cdf101b` | praezision | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Formulierungen wie „einige Anbieter ohne Auslandsgebühr gehören zu den besten Karten für Reisen“ sind pauschal und ohne messbare Daten unpräzise. | – |
| `bec83c4b814183fa1086` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass die kostenlose Sperr‑Notrufnummer 116 für alle Karten in Deutschland gilt, wird nicht durch eine Quelle gestützt. | – |
| `f9aff86b6eba71b153a6` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Angabe, dass Sollzinsen bei Teilzahlung zwischen 12 % und 20 % liegen, ist nicht mit einer Quelle belegt. | – |
| `fed9215b770ea4879eda` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Behauptung, dass eine gute Kreditkarte im Jahr nichts kostet (keine Jahres‑ und keine Fremdwährungsgebühr), wird ohne jegliche Quelle angegeben. | – |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 16b3b8584ff802803aa9 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7ff042b6fe804cdf101b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden bec83c4b814183fa1086 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f9aff86b6eba71b153a6 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden fed9215b770ea4879eda --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich` · **LIVE** (nicht beweisbar) · Risikoklasse standard · 2 Befund(e)

Datei: `content/posts/2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `20c08cb650ef6e24af64` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Ratgeber vernachlässigt bei der Kalkulation der Sparfähigkeit die massive Preissteigerung bei Energie (+14,9 %), die das Budget für monatliche Sparraten erheblich belastet. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `6aafb23c0c6dbb06ce3b` | veraltet | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die im Rechenbeispiel zur Realrendite genutzte Inflationsrate von 2 % ist veraltet; die vorläufige Rate für Oktober 2026 beträgt laut Statistischem Bundesamt 2,8 %. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 20c08cb650ef6e24af64 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6aafb23c0c6dbb06ce3b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-07-frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum` · **LIVE** (nicht beweisbar) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-09-07-frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `24f05ddc03ffdd50118f` | praezision | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Kalkulation der Fixkostenersparnis bei Energie (Strom/Gas) ist unpräzise, da sie den aktuellen Preisanstieg von +14,9 % bei Energieprodukten nicht einbezieht. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `4816322f061dfdc03bcd` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Bei den Einsparpotenzialen für Lebensmittel fehlt der Bezug zur aktuellen Preissteigerung von +0,4 % bei Nahrungsmitteln. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `7017065ee7c74c7ae452` | veraltet | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel nutzt Kostenszenarien für 2024/2025, während aktuelle Daten für Oktober 2026 eine Inflationsrate von +2,8 % ausweisen. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 24f05ddc03ffdd50118f --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 4816322f061dfdc03bcd --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7017065ee7c74c7ae452 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-07-frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler` · **LIVE** (nicht beweisbar) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-09-07-frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `1e06a96f6f71e104ce0b` | praezision | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Während Meal Prep als großer Sparhebel betont wird, zeigt die Marktlage für Nahrungsmittel eine moderate Teuerung von nur 0,4 %, was die Priorisierung der Sparbemühungen relativiert. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `81c6a707139046b83ccd` | luecke | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Ratgeber empfiehlt die Revision von Fixkosten, lässt aber die drastische Preissteigerung bei Energie von +14,9 % unerwähnt, die ein wesentlicher Treiber der Haushaltsausgaben ist. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `8cc00288af8a1f2b02d8` | veraltet | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Budget-Tipps berücksichtigen nicht die aktuelle Inflationsrate von 2,8 % (Stand Oktober 2026), was die Kaufkraft-Annahmen im Haushaltsbuch beeinflusst. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 1e06a96f6f71e104ce0b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 81c6a707139046b83ccd --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 8cc00288af8a1f2b02d8 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag` · **LIVE** (nicht beweisbar) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `5a1bf10697f58e5fe14a` | luecke | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Ratgeber nennt Sparbeispiele für Heizkosten, lässt aber die aktuelle Preissteigerung bei Energie von +14,9 % (Stand Oktober 2026) unerwähnt, die den finanziellen Druck auf Haushalte massiv erhöht. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `e48f9237cff6397c49a6` | praezision | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die in Aussicht gestellten Ersparnisse von bis zu 200 € werden nicht ins Verhältnis zur aktuellen Inflationsrate von +2,8 % gesetzt, welche die reale Kaufkraft des gesparten Geldes mindert. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `f6de6b078d49f9d42e0e` | praezision | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Beim Fokus auf Lebensmittelplanung fehlt der Hinweis auf die vergleichsweise moderate Preissteigerung von +0,4 % bei Nahrungsmitteln, was diesen Hebel gegenüber den stark steigenden Energiekosten relativiert. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 5a1bf10697f58e5fe14a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e48f9237cff6397c49a6 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f6de6b078d49f9d42e0e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-11-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026` · **LIVE** (nicht beweisbar) · Risikoklasse standard · 2 Befund(e)

Datei: `content/posts/2026-09-11-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `6cb2229c5eb83b02da23` | veraltet | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Kalkulation der Fixkosten (Energie 140 €) und die Empfehlung zur Senkung der Kosten ignorieren den aktuellen Markttrend massiv steigender Energiepreise (+14,9 %), was die 50-Prozent-Quote für notwendige Ausgaben gefährdet. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `f00055a1cb65ee22165f` | luecke | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Ratgeber verspricht eine 'planbare' Budgetierung, lässt aber die aktuelle Inflationsrate von 2,8 % unerwähnt, die insbesondere den Block der notwendigen Ausgaben (Nahrungsmittel +0,4 %) dynamisch belastet. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6cb2229c5eb83b02da23 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f00055a1cb65ee22165f --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden` · **LIVE** (nicht beweisbar) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `43470330b3b48c9cee49` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel empfiehlt, Kühl- und Gefriergeräte mindestens 24 Stunden, besser mehrere Tage zu messen, liefert jedoch keine Quelle für diese Messdauer. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `8ddc1025e45be176ad3a` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Es wird kein regulatorischer Rahmen (z. B. Aufgaben der Bundesnetzagentur) genannt, obwohl das Thema Stromversorgung berührt wird; entsprechende Vorgaben fehlen im Text. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `95d6d2877620e5a056ce` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass Verbraucherzentralen oder Bibliotheken Messgeräte verleihen, wird ohne Beleg gemacht. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `ab16029999747466a638` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Berechnung mit einem Arbeitspreis von 0,37 €/kWh wird angegeben, ohne dass ein aktueller Preis‑ oder Marktwert belegt wird. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `b057dee3603e09f494b5` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Das Amortisationsbeispiel (Kaufpreis 650 €, Amortisationszeit 10,3 Jahre) enthält keine Quelle für die zugrunde liegenden Annahmen oder Preise. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 43470330b3b48c9cee49 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 8ddc1025e45be176ad3a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 95d6d2877620e5a056ce --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ab16029999747466a638 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden b057dee3603e09f494b5 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit` · **LIVE** (nicht beweisbar) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `47f855cb4f0fe1e5c65f` | luecke | 10 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Angaben zu möglichen Einsparungen beim Kfz‑Versicherungswechsel (150 €‑400 € bzw. 180 €‑350 €) sind ohne Quellenangabe; keine der genannten Zahlen findet sich in den bereitgestellten Statistiken. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `6b0aa3429d97e8c74ed8` | luecke | 10 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Behauptung, technische Maßnahmen beim Heizen senken den Energieverbrauch um 8 %‑12 %, wird nicht belegt; die bereitgestellten Daten enthalten lediglich die allgemeine Preisentwicklung von Energie (+14,9 %). | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `7f66ec82ee1a3f095b0c` | praezision | 10 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Aussage, der Herbst sei die „lukrativste Spar‑Saison des Jahres“, ist nicht durch messbare Daten gestützt; ein Vergleich mit anderen Jahreszeiten fehlt. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `84c991c5d152b14a2675` | luecke | 10 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Gesamteinsparungen von 500 €‑1.300 € pro Haushalt werden als Modellrechnung präsentiert, jedoch ohne Kennzeichnung als Modell und ohne Quellenangabe. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `a70e7adc97c58317ccc1` | luecke | 10 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Das angegebene Sparpotenzial von 50 €‑80 € durch saisonale Lebensmittel‑ und Vorratshaltung ist nicht mit einer Quelle untermauert. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 47f855cb4f0fe1e5c65f --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6b0aa3429d97e8c74ed8 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7f66ec82ee1a3f095b0c --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 84c991c5d152b14a2675 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a70e7adc97c58317ccc1 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub` · **LIVE** (nicht beweisbar) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `0051151e6c46f4c2bdb3` | luecke | 10 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Der Artikel nennt eine Kautionshöhe von 900 € bis 2.500 €, ohne dass die Verbraucherzentrale diese Spanne angibt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `0790f52160dfaa819917` | luecke | 10 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die angegebene Ersparnis von 145 € bei einer einwöchigen Anmietung ist nicht durch Zahlen der Verbraucherzentrale gedeckt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `53c3fde8e986e6560890` | luecke | 10 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Behauptung, dass Flughafen‑Mietstationen 15 %‑25 % teurer sind, wird von der Verbraucherzentrale nicht bestätigt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `89adecebaae75c147402` | luecke | 10 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Aussage, dass eine „Zero‑Excess“-Option die Kaution komplett auf 0 € senkt und dafür 5 €‑12 € pro Tag kostet, wird von der Verbraucherzentrale nicht belegt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `a1a269b73a1b9c2dfc88` | luecke | 10 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Der Hinweis, dass eine Vollkasko ohne Selbstbeteiligung nur 3 €‑8 € pro Tag mehr kostet, fehlt in den Angaben der Verbraucherzentrale. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 0051151e6c46f4c2bdb3 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 0790f52160dfaa819917 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 53c3fde8e986e6560890 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 89adecebaae75c147402 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a1a269b73a1b9c2dfc88 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-02-last-minute-urlaubsangebote-sichern` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-11-02-last-minute-urlaubsangebote-sichern`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `0a2bec9dc02e16c057ee` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die 50‑30‑20‑Regel für die Urlaubsbudget‑Aufteilung wird ohne Quellenangabe präsentiert. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `274c32d1a16e9dffcf1a` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Angabe, dass das Weglassen der Vollkasko‑Selbstbeteiligung die Kosten um 10 % bis 20 % senken kann, ist nicht mit einer Quelle belegt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `5c572a933edece129bba` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass Stornogebühren häufig einem Tagespreis entsprechen, ist unbelegt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `9d9d4afc8d6c421a0d14` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Behauptung, dass Last‑Minute‑Deals wegen Restkapazitäten zu niedrigeren Preisen führen, fehlt eine fundierte Quelle. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `fb50388539a0e8b4461c` | praezision | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Empfehlung, ausschließlich CHECK24 für den Mietwagenvergleich zu nutzen, ist ein unqualifiziertes Superlativ ohne Messgrundlage. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 0a2bec9dc02e16c057ee --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 274c32d1a16e9dffcf1a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 5c572a933edece129bba --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 9d9d4afc8d6c421a0d14 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden fb50388539a0e8b4461c --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-05-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-11-05-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu`

Herkunft nach Datums-Lift: `2026-11-01-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu` → `2026-11-05-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu`. Befund-ID und Fassungsanker bleiben unverändert; das Re-Dating ist keine fachliche Entscheidung.

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `0b564f460c41218244bd` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel behauptet, dass Heizöl‑Preise ihr Tief meist in den Monaten Januar und Februar erreichen, ohne dafür eine Quelle anzugeben. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `3ad2eefed314eb172c26` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass durch frühzeitige Bestellung Kosten um 10 % bis 20 % im Herbst eingespart werden können, ist unbelegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `43788c2cdcdfda52e753` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Modellrechnung verwendet einen Tiefpreis von 0,80 €/Liter, ohne dass diese Preisangabe belegt wird. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `5eedec8afbdef6a4ca49` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Es wird angegeben, dass typische Fehler beim Heizölkauf bis zu 15 % Mehrkosten verursachen können, jedoch fehlt ein Nachweis für diese Zahl. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `81881c5bc61824d25f5a` | praezision | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Faustregel, dass man bestellen sollte, wenn Preise vier Wochen unter dem Schnitt der letzten 12 Monate liegen, wird ohne Messgrundlage oder Quelle genannt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

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
| `785eee76d888bb05ad96` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die im Rechenbeispiel genutzte Kilometerpauschale von 0,20 €/km wird als Referenzwert ohne Quellenangabe (z. B. Branchenverband) angeführt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `843ec148e23841b7bf35` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der als Handlungsschritt empfohlene '4K-Prüfpfad' wird im Text nicht erläutert und ist in der genannten Quelle nicht enthalten. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `def43a04853be4c35f7f` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Preisprognose (Anstieg in den letzten 3 Wochen) und der empfohlene Buchungsvorlauf (3-4 Wochen) sind Marktdaten ohne Beleg durch die Fachquelle. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `f064ea49ccefde26aef9` | praezision | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Das Versprechen, CHECK24 vergleiche 'alle großen Anbieter', ist ein Vollständigkeitsversprechen ohne Nennung von Auswahlkriterien oder der Marktabdeckung. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

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
| `82cc87314e0d4fcb21e9` | luecke | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die kalkulierte Ersparnis bei Energiekosten (15 €/Monat) berücksichtigt nicht den aktuellen Markttrend massiv steigender Preise (+14,9 % bei Energie). | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `bd5ee70c85ec7db78f26` | luecke | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die pauschalen Jahressparwerte von 300 € bis 1.000 € werden in Marktfakten-Positur ohne Nennung einer Referenzquelle oder eines Absenders (z. B. Destatis) aufgeführt. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `f83f21c1f2e2012f672e` | praezision | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Sparversprechen im Bereich Lebensmittel vernachlässigen die Inflationsrate bei Nahrungsmitteln (+0,4 %), was Modellrechnungen ohne Inflationsbereinigung ungenau macht. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 82cc87314e0d4fcb21e9 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden bd5ee70c85ec7db78f26 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f83f21c1f2e2012f672e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-06-guenstige-fluege-fuer-den-spaetsommer-finden` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-11-06-guenstige-fluege-fuer-den-spaetsommer-finden`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `0e68294e193918d5b5b0` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Text nennt eine angeblich gängige Faustregel von 20 % Rabatt im Spätsommer (Beispiel 300 € → 240 €) ohne Quellenangabe. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `4d91ef71fa76febdb769` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Es wird angegeben, dass Flüge an Dienstagen und Mittwochen günstiger seien und an Freitagen bzw. Sonntagen teurer, ohne Beleg. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `5b427fb4f05b475d9a89` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Empfehlung, Flüge vier bis acht Wochen im Voraus zu buchen, weil die Preise dann am niedrigsten seien, wird nicht belegt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `e933e34672f0b6464d1e` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel behauptet, dass im Spätsommer die Nachfrage nach Flügen sinkt und dadurch die Preise fallen, ohne dafür eine Quelle anzugeben. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `eb6a47df5535fa267a82` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Behauptet wird, dass Kombi‑Deals für Flug + Mietwagen typischerweise 5–15 % Einsparungen bringen, ohne Nachweis. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

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
| `0f248aaad2d2b8d87d0d` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die im Marktradar angegebenen Durchschnittspreise für Strom (37,3 ct/kWh) und Gas (12,23 ct/kWh) werden ohne Quellenangabe genannt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `3a69bd57886154a18b8e` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass bei Preiserhöhungen ein gesetzliches 14‑tägiges Sonderkündigungsrecht besteht, fehlt eine rechtliche Quellenangabe. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `4f777954306ac7b21e03` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Behauptung, dass ein Lieferantenwechsel und ein technischer Anschlusswechsel nicht dasselbe seien, wird nicht durch eine Quelle belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 0f248aaad2d2b8d87d0d --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 3a69bd57886154a18b8e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 4f777954306ac7b21e03 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-28-dsl-und-internet-flat-guenstig-sichern` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-10-28-dsl-und-internet-flat-guenstig-sichern`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `05be346e82c80b2a8664` | luecke | 10 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Wechselboni von 50 € bis 100 € werden genannt, jedoch fehlt jede belegbare Angabe zu deren Höhe oder Häufigkeit. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `d0a5cf7bb64eb0cd46c8` | luecke | 10 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Der Artikel erwähnt keinen regulatorischen Rahmen (z. B. Informations‑ und Preisbindungspflichten der Bundesnetzagentur) obwohl die Fundstelle darauf hinweist, dass solche Vorgaben existieren. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `ec53e181336df8dc61ac` | luecke | 10 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Der Artikel behauptet, dass DSL‑Verträge häufig eine Laufzeit von 24 Monaten haben und danach eine Kündigungsfrist von einem Monat gilt, ohne dafür eine Quelle anzugeben. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `f3f9184bfca9b097f68e` | luecke | 10 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die 50‑30‑20‑Regel wird als allgemein gültige Budget‑Methode dargestellt, ohne Hinweis, dass es sich um ein Modell handelt oder Quelle dafür zu nennen. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `fb4d2260f4fa291c35ae` | praezision | 10 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Angabe, dass für zwei HD‑Streams gleichzeitig etwa 30 Mbit/s benötigt werden, ist nicht durch Daten belegt und lässt Spielraum für Fehlinterpretationen. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 05be346e82c80b2a8664 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d0a5cf7bb64eb0cd46c8 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ec53e181336df8dc61ac --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f3f9184bfca9b097f68e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden fb4d2260f4fa291c35ae --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

---

_Diese Akte entscheidet nichts und schließt nichts. Sie macht sichtbar, was zu entscheiden ist, wer es entscheiden muss (Herausgeber/Redaktion) und wie der Schließweg lautet. Regel: `scripts/faktenfrische_befund_ledger.py`, Governance C46._
