# BEFUND-AKTE – offene Fachbefunde der Faktenfrische

_Stand 2026-11-03 · erzeugt von `scripts/faktenfrische_befund_akte.py` · Quelle: `data/faktenfrische_queue.json` + `data/faktenfrische_entscheidungen.yaml` (eine Regel, zwei Leser)._

**57 offene Befunde auf 13 Seiten · davon 10 Live-Seiten mit 42 Befunden · ältester 4 Tage · Frist 14 Tage.**

| Kennzahl | Wert |
|---|---|
| Offene Befunde | 57 |
| Seiten betroffen | 13 (davon live: 10) |
| Text seit dem Befund geändert | 21 |
| Altbestand ohne Fassungs-Hash | 20 |
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

> **Wichtig – betrifft 41 von 57 Befunden** (in der Tabelle als Fassung markiert): Der Text ist seit dem Befund bereits geändert worden (Heilung) oder stammt aus dem Altbestand. Die Entscheidung bezieht sich ausdrücklich auf den HEUTIGEN Text – bitte diesen lesen, nicht den alten Befund abnicken. Diese Prüfung kann dir die Maschine nicht abnehmen – sie darf sie aber auch nicht verhindern.

## Seiten

### `2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `124ff2c3cd3917c274aa` | praezision | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Bewerbung des Vergleichsportals mit dem Superlativ 'Die besten Tarife' erfolgt ohne messbare Daten oder Auswahlkriterien in der Recherchegrundlage. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `7bdec96c0329769bebe6` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die im Artikel als Fakten genannten Gaspreise für Oktober 2026 (11 bis 13 Cent/kWh) sind nicht durch die Fundstelle belegt, die lediglich eine allgemeine Themenübersicht darstellt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `a56734aa032e0ed9e0c4` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der für den Verbraucherschutz zentrale Regulierungsrahmen (Sonderkündigungsrecht, Informationspflichten der Versorger) wird in der Fundstelle nicht inhaltlich bestätigt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 124ff2c3cd3917c274aa --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7bdec96c0329769bebe6 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a56734aa032e0ed9e0c4 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `30caa57be394afb62947` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Für den angeführten BDEW-Durchschnittspreis von 11,93 Cent/kWh fehlt in den Recherche-Fundstellen ein entsprechender Beleg. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `32a3ea879f2cf126b3a7` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel lässt den in der Quelle explizit genannten Regulierungsrahmen der 'Unternehmenspflichten' unerwähnt, der für den Schutz der Verbraucher beim Anbieterwechsel zentral ist. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `c583efe1ce02df3ca2d7` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die im Artikel genannte Ersparnis-Berechnung der Bundesnetzagentur für Januar 2026 (360 €) wird durch die allgemeine Übersichtsseite der Behörde nicht gestützt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 30caa57be394afb62947 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 32a3ea879f2cf126b3a7 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden c583efe1ce02df3ca2d7 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden` · **LIVE** (blockiert) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `437b809ffbf41e5af434` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Keine Quelle für die Aussage, dass das Gesetz bei einem Tarifwechsel die Grundversorgung garantiert – regulatorischer Rahmen fehlt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `9fbacd9942c2dfa1447f` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Keine Quelle für die Behauptung, dass ein Grad weniger Raumtemperatur rund 6 % Energie einspart – Prozent‑Angabe fehlt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `da30cbb5fbc8c801daf0` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Keine Quelle für die Angabe, dass durch Optimierungsmaßnahmen 10‑15 % Einsparungen realistisch sind – Prozent‑Wert unbelegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `db8a69f08dc0020adebd` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Keine Quelle für die Aussage, dass im Oktober 2026 bessere Gaspreise gelten – Preis‑Trend‑Behauptung fehlt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `e834f4702e87194affe7` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Keine Quelle für die Angabe, dass ein Einfamilienhaus typischerweise 18.000 kWh/Jahr verbraucht – Verbrauchszahl ist unbelegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

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
| `252413dcc16cea146beb` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel behauptet, dass eine Preisänderung meist einen Monat vorher angekündigt werden muss, ohne dafür eine Quelle anzugeben. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `48a0a962046c8315270e` | praezision | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Behauptung, dass eine Preisgarantie einen Teil des Risikos auf den Anbieter überträgt und dafür ein höherer Startpreis üblich ist, fehlt eine konkrete Quelle und bleibt vage. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `9326152f4d788cff56bd` | praezision | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass man „in der Regel“ zum Zeitpunkt der Preisänderung Sonderkündigungsrecht hat, ist unpräzise und wird nicht durch eine konkrete Regelung belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `ab4d084fd367c8e4d518` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der angegebene durchschnittliche Gaspreis von 11,93 Cent/kWh für 2026 (laut BDEW) wird nicht durch eine Quelle belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `d215addd22dea72c44df` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Angabe, dass die Verbraucherzentrale etwa 6 % weniger Heizenergie pro Grad niedrigerer Raumtemperatur nennt, fehlt eine Quellenangabe. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 252413dcc16cea146beb --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 48a0a962046c8315270e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 9326152f4d788cff56bd --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ab4d084fd367c8e4d518 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d215addd22dea72c44df --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit` · **LIVE** (blockiert) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `47f855cb4f0fe1e5c65f` | luecke | 4 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Angaben zu möglichen Einsparungen beim Kfz‑Versicherungswechsel (150 €‑400 € bzw. 180 €‑350 €) sind ohne Quellenangabe; keine der genannten Zahlen findet sich in den bereitgestellten Statistiken. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `6b0aa3429d97e8c74ed8` | luecke | 4 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Behauptung, technische Maßnahmen beim Heizen senken den Energieverbrauch um 8 %‑12 %, wird nicht belegt; die bereitgestellten Daten enthalten lediglich die allgemeine Preisentwicklung von Energie (+14,9 %). | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `7f66ec82ee1a3f095b0c` | praezision | 4 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Aussage, der Herbst sei die „lukrativste Spar‑Saison des Jahres“, ist nicht durch messbare Daten gestützt; ein Vergleich mit anderen Jahreszeiten fehlt. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `84c991c5d152b14a2675` | luecke | 4 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Gesamteinsparungen von 500 €‑1.300 € pro Haushalt werden als Modellrechnung präsentiert, jedoch ohne Kennzeichnung als Modell und ohne Quellenangabe. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `a70e7adc97c58317ccc1` | luecke | 4 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Das angegebene Sparpotenzial von 50 €‑80 € durch saisonale Lebensmittel‑ und Vorratshaltung ist nicht mit einer Quelle untermauert. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

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
| `0051151e6c46f4c2bdb3` | luecke | 4 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Der Artikel nennt eine Kautionshöhe von 900 € bis 2.500 €, ohne dass die Verbraucherzentrale diese Spanne angibt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `0790f52160dfaa819917` | luecke | 4 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die angegebene Ersparnis von 145 € bei einer einwöchigen Anmietung ist nicht durch Zahlen der Verbraucherzentrale gedeckt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `53c3fde8e986e6560890` | luecke | 4 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Behauptung, dass Flughafen‑Mietstationen 15 %‑25 % teurer sind, wird von der Verbraucherzentrale nicht bestätigt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `89adecebaae75c147402` | luecke | 4 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Aussage, dass eine „Zero‑Excess“-Option die Kaution komplett auf 0 € senkt und dafür 5 €‑12 € pro Tag kostet, wird von der Verbraucherzentrale nicht belegt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `a1a269b73a1b9c2dfc88` | luecke | 4 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Der Hinweis, dass eine Vollkasko ohne Selbstbeteiligung nur 3 €‑8 € pro Tag mehr kostet, fehlt in den Angaben der Verbraucherzentrale. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 0051151e6c46f4c2bdb3 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 0790f52160dfaa819917 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 53c3fde8e986e6560890 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 89adecebaae75c147402 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a1a269b73a1b9c2dfc88 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-07-heizkosten-senken-mit-diesen-strategien-sparst-du-sofort` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-09-07-heizkosten-senken-mit-diesen-strategien-sparst-du-sofort/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `3f0a88ede9d44ee910cb` | luecke | 1 T | Text unverändert seit dem Befund | Es fehlt der Hinweis auf das offizielle Beschwerdeportal der Bundesnetzagentur, über das Verbraucher Probleme mit Anbietern direkt melden können. | – |
| `51e259fd2d8582e774f7` | luecke | 1 T | Text unverändert seit dem Befund | Der Ratgeber versäumt es, bei der Tarifprüfung auf die behördlichen Schlichtungsverfahren hinzuweisen, die Verbrauchern bei Streitigkeiten mit Energieversorgern zur Verfügung stehen. | – |
| `55f8eeedc587cf0895ee` | luecke | 1 T | Text unverändert seit dem Befund | Der Artikel erwähnt keine behördlichen Informationsquellen wie das Verbraucher-Radar, das Transparenz über den Energiemarkt und Verbraucherschutzthemen bietet. | – |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 3f0a88ede9d44ee910cb --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 51e259fd2d8582e774f7 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 55f8eeedc587cf0895ee --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-11-guenstig-durch-den-winter-heizungs-check-im-spaetsommer` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-09-11-guenstig-durch-den-winter-heizungs-check-im-spaetsommer/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `045ff990e44a7035e9a0` | luecke | 1 T | Text unverändert seit dem Befund | Es fehlt der Hinweis auf die behördliche Anlaufstelle für Anfragen und Beschwerden im Bereich Energie, die über die rein zivilrechtliche Meldung beim Vermieter hinausgeht. | – |
| `8919c2d1145af782d17a` | luecke | 1 T | Text unverändert seit dem Befund | Der Ratgeber empfiehlt Tarifvergleiche und Mängelmeldungen, lässt aber den für den Energiemarkt relevanten Regulierungsrahmen für den Verbraucherschutz (Schlichtungsverfahren) unerwähnt. | – |
| `c39938841291b1e9e140` | praezision | 1 T | Text unverändert seit dem Befund | Die Markttransparenz und der Verbraucherschutz im Energiesektor werden durch das 'Verbraucher-Radar' der Bundesnetzagentur statistisch erfasst; dieser Kontext fehlt bei der Einordnung von Marktdaten. | – |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 045ff990e44a7035e9a0 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 8919c2d1145af782d17a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden c39938841291b1e9e140 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-20-gasrechnung-senken-so-bereitest-du-dich-im-spaetsommer-vor` · **LIVE** (blockiert) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-09-20-gasrechnung-senken-so-bereitest-du-dich-im-spaetsommer-vor/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `0aa915539d57841e5014` | luecke | 1 T | Text unverändert seit dem Befund | Die Aussage, dass die Verbraucherzentrale empfiehlt, Boni im ersten Vergleich auszublenden, fehlt eine Quellenangabe. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `5e1be48085014a836807` | luecke | 1 T | Text unverändert seit dem Befund | Der angegebene BDEW‑Durchschnittspreis von 11,93 Cent/kWh für 2026 wird nicht belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `6fdf31c3b68b6122bd0d` | praezision | 1 T | Text unverändert seit dem Befund | Die pauschale Formulierung, dass bei zentraler Heizung der Vermieter oder die Eigentümergemeinschaft den Anbieter wählt, ist zu ungenau und nicht belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `c27c182c615bd7ca3b78` | luecke | 1 T | Text unverändert seit dem Befund | Der Artikel behauptet, dass laut Bundesnetzagentur Preisänderungen klar angekündigt und begründet sein müssen, liefert jedoch keinen Beleg dafür. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `e1e40e9bbbdd109df86e` | luecke | 1 T | Text unverändert seit dem Befund | Es wird angegeben, dass bei einer Preisänderung in der Regel ein Sonderkündigungsrecht besteht, ohne dafür eine Quelle zu nennen. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

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
| `334751e6f61ad0033fe4` | luecke | 1 T | Text unverändert seit dem Befund | Die Angabe, dass ein Gaslieferantenwechsel bei 20.000 kWh im Januar 2026 im Schnitt etwa 360 € spart, fehlt jede Quellenangabe. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `36759a5efe5e8e5163d0` | luecke | 1 T | Text unverändert seit dem Befund | Die Faustregel der Verbraucherzentrale, dass pro Grad weniger Raumtemperatur der Heizbedarf um etwa 6 % sinkt, wird ohne Quelle angegeben. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `942922d1afd7844618e9` | luecke | 1 T | Text unverändert seit dem Befund | Die Rechnung „1 Cent pro kWh bei 18.000 kWh Jahresverbrauch ergibt rund 180 € im Jahr“ wird nicht belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `d41f0d5ce8798df0211b` | praezision | 1 T | Text unverändert seit dem Befund | Die Aussage „Die besten Tarife findest du über unseren Partner‑Vergleich“ ist ein Superlativ ohne messbare Daten oder Vergleichskriterien. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `e139d0769faadd04392a` | luecke | 1 T | Text unverändert seit dem Befund | Der BDEW‑Durchschnittspreis von 11,93 Cent/kWh für 2026 wird ohne Quellenangabe genannt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 334751e6f61ad0033fe4 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 36759a5efe5e8e5163d0 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 942922d1afd7844618e9 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d41f0d5ce8798df0211b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e139d0769faadd04392a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-30-kostenloses-girokonto-ohne-gebuehren-finden` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-10-30-kostenloses-girokonto-ohne-gebuehren-finden`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `176642ea8acfa44f1152` | luecke | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Behauptung, dass Inlands‑Überweisungen in der Regel kostenlos sind, fehlt eine entsprechende Quelle. | – |
| `2520f45d441ef87614e3` | luecke | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Behauptung, dass ein kostenloses Girokonto keine reguläre Kontoführungsgebühr erhebt, wird nicht durch die bereitgestellten Quellen belegt. | – |
| `33bda5941052d9334598` | luecke | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Quantitative Aussage, dass ein kostenloses Girokonto mindestens ein Drittel der bisherigen Kontokosten einsparen kann, ist unbelegt. | – |
| `7406eaba3aa749c46f4b` | luecke | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Zeitangabe, dass die Kontoeröffnung meist innerhalb weniger Werktage abgeschlossen ist, wird nicht durch die genannten Quellen gestützt. | – |
| `9f47e6d2aa8cf2a8ff91` | luecke | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Angabe, dass die meisten Banken ein Mindestguthaben von ein paar hundert Euro verlangen, fehlt eine fundierte Quelle. | – |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 176642ea8acfa44f1152 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 2520f45d441ef87614e3 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 33bda5941052d9334598 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7406eaba3aa749c46f4b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 9f47e6d2aa8cf2a8ff91 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-28-dsl-und-internet-flat-guenstig-sichern` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-10-28-dsl-und-internet-flat-guenstig-sichern`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `05be346e82c80b2a8664` | luecke | 4 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Wechselboni von 50 € bis 100 € werden genannt, jedoch fehlt jede belegbare Angabe zu deren Höhe oder Häufigkeit. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `d0a5cf7bb64eb0cd46c8` | luecke | 4 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Der Artikel erwähnt keinen regulatorischen Rahmen (z. B. Informations‑ und Preisbindungspflichten der Bundesnetzagentur) obwohl die Fundstelle darauf hinweist, dass solche Vorgaben existieren. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `ec53e181336df8dc61ac` | luecke | 4 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Der Artikel behauptet, dass DSL‑Verträge häufig eine Laufzeit von 24 Monaten haben und danach eine Kündigungsfrist von einem Monat gilt, ohne dafür eine Quelle anzugeben. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `f3f9184bfca9b097f68e` | luecke | 4 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die 50‑30‑20‑Regel wird als allgemein gültige Budget‑Methode dargestellt, ohne Hinweis, dass es sich um ein Modell handelt oder Quelle dafür zu nennen. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `fb4d2260f4fa291c35ae` | praezision | 4 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Angabe, dass für zwei HD‑Streams gleichzeitig etwa 30 Mbit/s benötigt werden, ist nicht durch Daten belegt und lässt Spielraum für Fehlinterpretationen. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 05be346e82c80b2a8664 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d0a5cf7bb64eb0cd46c8 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ec53e181336df8dc61ac --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f3f9184bfca9b097f68e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden fb4d2260f4fa291c35ae --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `versicherungen` · nicht im Live-Bestand · 5 Befund(e)

Seite: `versicherungen`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `360dbd44c71db04f43e0` | luecke | 4 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Preisangaben für die Privathaftpflicht (35 – 65 € jährlich) werden ohne Quellenangabe genannt. | [Quelle](https://www.gdv.de/gdv/medien/medieninformationen) |
| `a4f736ca6f8f1a70fe60` | praezision | 4 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Der Hinweis, dass ein jährlicher Kfz‑Wechsel‑Check zum Stichtag 30. November „fast immer“ zu Einsparungen führt, ist pauschal und nicht durch konkrete Daten gestützt. | – |
| `c2de49121dea2b8b7cc6` | luecke | 4 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Empfehlung einer Mindestdeckungssumme von 50 Millionen Euro für Personen‑, Sach‑ und Vermögensschäden in der Privathaftpflicht wird nicht durch eine Quelle belegt. | [Quelle](https://www.gdv.de/gdv/medien/medieninformationen) |
| `de9bc512fad04e99c1da` | praezision | 4 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Aussage, dass Elementarschäden bei Wohn‑ und Hausratversicherung „unverzichtbar“ seien, ist ein unqualifiziertes Superlativ ohne messbare Grundlage. | – |
| `e7ab68c9e3b2f443c904` | luecke | 4 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Behauptung, dass ein Kfz‑Wechsel zum 30. November jährlich 100 – 300 € spart, fehlt jede belegbare Marktinformation. | [Quelle](https://www.gdv.de/gdv/medien/medieninformationen) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 360dbd44c71db04f43e0 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a4f736ca6f8f1a70fe60 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden c2de49121dea2b8b7cc6 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden de9bc512fad04e99c1da --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e7ab68c9e3b2f443c904 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

---

_Diese Akte entscheidet nichts und schließt nichts. Sie macht sichtbar, was zu entscheiden ist, wer es entscheiden muss (Herausgeber/Redaktion) und wie der Schließweg lautet. Regel: `scripts/faktenfrische_befund_ledger.py`, Governance C46._
