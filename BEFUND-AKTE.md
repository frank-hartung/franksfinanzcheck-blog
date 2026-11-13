# BEFUND-AKTE – offene Fachbefunde der Faktenfrische

_Stand 2026-11-13 · erzeugt von `scripts/faktenfrische_befund_akte.py` · Quelle: `data/faktenfrische_queue.json` + `data/faktenfrische_entscheidungen.yaml` (eine Regel, zwei Leser)._

**155 offene Befunde auf 39 Seiten · davon 24 Live-Seiten mit 94 Befunden · ältester 14 Tage · Frist 14 Tage.**

| Kennzahl | Wert |
|---|---|
| Offene Befunde | 155 |
| Seiten betroffen | 39 (davon live: 24) |
| Text seit dem Befund geändert | 96 |
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

> **Wichtig – betrifft 111 von 155 Befunden** (in der Tabelle als Fassung markiert): Der Text ist seit dem Befund bereits geändert worden (Heilung) oder stammt aus dem Altbestand. Die Entscheidung bezieht sich ausdrücklich auf den HEUTIGEN Text – bitte diesen lesen, nicht den alten Befund abnicken. Diese Prüfung kann dir die Maschine nicht abnehmen – sie darf sie aber auch nicht verhindern.

## Seiten

### `2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `124ff2c3cd3917c274aa` | praezision | 12 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Bewerbung des Vergleichsportals mit dem Superlativ 'Die besten Tarife' erfolgt ohne messbare Daten oder Auswahlkriterien in der Recherchegrundlage. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `7bdec96c0329769bebe6` | luecke | 12 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die im Artikel als Fakten genannten Gaspreise für Oktober 2026 (11 bis 13 Cent/kWh) sind nicht durch die Fundstelle belegt, die lediglich eine allgemeine Themenübersicht darstellt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `a56734aa032e0ed9e0c4` | luecke | 12 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der für den Verbraucherschutz zentrale Regulierungsrahmen (Sonderkündigungsrecht, Informationspflichten der Versorger) wird in der Fundstelle nicht inhaltlich bestätigt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 124ff2c3cd3917c274aa --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7bdec96c0329769bebe6 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a56734aa032e0ed9e0c4 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `30caa57be394afb62947` | luecke | 12 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Für den angeführten BDEW-Durchschnittspreis von 11,93 Cent/kWh fehlt in den Recherche-Fundstellen ein entsprechender Beleg. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `32a3ea879f2cf126b3a7` | luecke | 12 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel lässt den in der Quelle explizit genannten Regulierungsrahmen der 'Unternehmenspflichten' unerwähnt, der für den Schutz der Verbraucher beim Anbieterwechsel zentral ist. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `c583efe1ce02df3ca2d7` | luecke | 12 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die im Artikel genannte Ersparnis-Berechnung der Bundesnetzagentur für Januar 2026 (360 €) wird durch die allgemeine Übersichtsseite der Behörde nicht gestützt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 30caa57be394afb62947 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 32a3ea879f2cf126b3a7 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden c583efe1ce02df3ca2d7 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen` · **LIVE** (blockiert) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `252413dcc16cea146beb` | luecke | 12 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel behauptet, dass eine Preisänderung meist einen Monat vorher angekündigt werden muss, ohne dafür eine Quelle anzugeben. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `48a0a962046c8315270e` | praezision | 12 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Behauptung, dass eine Preisgarantie einen Teil des Risikos auf den Anbieter überträgt und dafür ein höherer Startpreis üblich ist, fehlt eine konkrete Quelle und bleibt vage. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `9326152f4d788cff56bd` | praezision | 12 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass man „in der Regel“ zum Zeitpunkt der Preisänderung Sonderkündigungsrecht hat, ist unpräzise und wird nicht durch eine konkrete Regelung belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `ab4d084fd367c8e4d518` | luecke | 12 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der angegebene durchschnittliche Gaspreis von 11,93 Cent/kWh für 2026 (laut BDEW) wird nicht durch eine Quelle belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `d215addd22dea72c44df` | luecke | 12 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Angabe, dass die Verbraucherzentrale etwa 6 % weniger Heizenergie pro Grad niedrigerer Raumtemperatur nennt, fehlt eine Quellenangabe. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

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
| `0aa915539d57841e5014` | luecke | 11 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass die Verbraucherzentrale empfiehlt, Boni im ersten Vergleich auszublenden, fehlt eine Quellenangabe. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `5e1be48085014a836807` | luecke | 11 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der angegebene BDEW‑Durchschnittspreis von 11,93 Cent/kWh für 2026 wird nicht belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `6fdf31c3b68b6122bd0d` | praezision | 11 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die pauschale Formulierung, dass bei zentraler Heizung der Vermieter oder die Eigentümergemeinschaft den Anbieter wählt, ist zu ungenau und nicht belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `c27c182c615bd7ca3b78` | luecke | 11 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel behauptet, dass laut Bundesnetzagentur Preisänderungen klar angekündigt und begründet sein müssen, liefert jedoch keinen Beleg dafür. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `e1e40e9bbbdd109df86e` | luecke | 11 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Es wird angegeben, dass bei einer Preisänderung in der Regel ein Sonderkündigungsrecht besteht, ohne dafür eine Quelle zu nennen. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 0aa915539d57841e5014 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 5e1be48085014a836807 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6fdf31c3b68b6122bd0d --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden c27c182c615bd7ca3b78 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e1e40e9bbbdd109df86e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `089b89138417e63a3dcf` | luecke | 10 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Es fehlt der für Campingbuchungen relevante Regulierungsrahmen (Unterscheidung Mietrecht bei Stellplätzen vs. Reiserecht), den die Fundstelle für den Bereich Reise nur allgemein andeutet. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `1158934e7a18c7b2099b` | luecke | 10 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Preisangabe von 20 bis 45 € pro Nacht wird als realistischer Wert positioniert, ist jedoch nicht durch Marktdaten oder eine Referenzstelle in den Fundstellen belegt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `3716cfd3ab5aec6d774b` | praezision | 10 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Verweis auf die Verbraucherzentrale zur Prüfung von Buchungsangaben führt auf eine allgemeine Übersichtsseite ohne konkrete Checklisten für Camping-Angebote. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 089b89138417e63a3dcf --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 1158934e7a18c7b2099b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 3716cfd3ab5aec6d774b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren` · **LIVE** (blockiert) · Risikoklasse erhoeht · 5 Befund(e)

Datei: `content/posts/2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `1dbeb2f8c51e78d11d49` | luecke | 9 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Behauptung, dass klassische Filialbanken jährlich 150 € bis 250 € an reinen Gebühren kosten, ist unbelegt. | – |
| `33e736ac6afe996b491a` | luecke | 9 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Behauptung, dass Echtzeit‑Überweisungen bei kostenlosen Konten generell gebührenfrei sind, fehlt jede Quelle. | – |
| `96b7b7768d402884810c` | luecke | 9 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Aussage, dass Einlagen bis 100.000 € durch die deutsche Einlagensicherung geschützt sind, wird nicht belegt. | – |
| `a25bb6bbcb25ba8b0e22` | luecke | 9 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Angabe von Dispozinsen von 8 % bis 11 % ohne Quellenangabe. | – |
| `f94f8ba1e4342e67e45a` | luecke | 9 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Angabe, dass ein Kontowechsel 120 € bis 180 € im Jahr spart, fehlt jede Quelle. | – |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 1dbeb2f8c51e78d11d49 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 33e736ac6afe996b491a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 96b7b7768d402884810c --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a25bb6bbcb25ba8b0e22 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f94f8ba1e4342e67e45a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `3fe383f6d452737f66f2` | praezision | 9 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die im Teaser und Text genannten monatlichen Ersparnisse von 350 € bis 600 € werden als Marktfakten ohne Quellenbeleg oder methodische Herleitung (z. B. Referenzhaushalt des Statistischen Bundesamtes) angeführt. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `7bba759bbb4ca14c7f35` | luecke | 9 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Ratgeber empfiehlt Tarifwechsel bei Energie zur Kostensenkung, verschweigt aber den aktuellen Markttrend massiv steigender Energiepreise (+14,9 %), was die Kalkulation der 50-Prozent-Fixkostenquote gefährdet. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `e8e32a383b6f803cc8d4` | veraltet | 9 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Einschätzung zur Inflation ist unpräzise: Die aktuelle Inflationsrate liegt laut Destatis bei +2,8 % (Oktober 2026), wodurch die genannten Tagesgeldzinsen von 0,5 % bis 1,5 % den Wertverlust deutlich weniger ausgleichen als suggeriert. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 3fe383f6d452737f66f2 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7bba759bbb4ca14c7f35 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e8e32a383b6f803cc8d4 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-03-kreditkarte-vergleichen-kostenlos-sicher-bezahlen` · **LIVE** (blockiert) · Risikoklasse erhoeht · 5 Befund(e)

Datei: `content/posts/2026-09-03-kreditkarte-vergleichen-kostenlos-sicher-bezahlen/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `16b3b8584ff802803aa9` | luecke | 9 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Angaben zum Fremdwährungsentgelt von „fast zwei Prozent“ bei Zahlungen in fremder Währung fehlen jede belegbare Referenz. | – |
| `7ff042b6fe804cdf101b` | praezision | 9 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Formulierungen wie „einige Anbieter ohne Auslandsgebühr gehören zu den besten Karten für Reisen“ sind pauschal und ohne messbare Daten unpräzise. | – |
| `bec83c4b814183fa1086` | luecke | 9 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass die kostenlose Sperr‑Notrufnummer 116 für alle Karten in Deutschland gilt, wird nicht durch eine Quelle gestützt. | – |
| `f9aff86b6eba71b153a6` | luecke | 9 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Angabe, dass Sollzinsen bei Teilzahlung zwischen 12 % und 20 % liegen, ist nicht mit einer Quelle belegt. | – |
| `fed9215b770ea4879eda` | luecke | 9 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Behauptung, dass eine gute Kreditkarte im Jahr nichts kostet (keine Jahres‑ und keine Fremdwährungsgebühr), wird ohne jegliche Quelle angegeben. | – |

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
| `20c08cb650ef6e24af64` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Ratgeber vernachlässigt bei der Kalkulation der Sparfähigkeit die massive Preissteigerung bei Energie (+14,9 %), die das Budget für monatliche Sparraten erheblich belastet. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `6aafb23c0c6dbb06ce3b` | veraltet | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die im Rechenbeispiel zur Realrendite genutzte Inflationsrate von 2 % ist veraltet; die vorläufige Rate für Oktober 2026 beträgt laut Statistischem Bundesamt 2,8 %. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 20c08cb650ef6e24af64 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6aafb23c0c6dbb06ce3b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-07-frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-09-07-frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `24f05ddc03ffdd50118f` | praezision | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Kalkulation der Fixkostenersparnis bei Energie (Strom/Gas) ist unpräzise, da sie den aktuellen Preisanstieg von +14,9 % bei Energieprodukten nicht einbezieht. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `4816322f061dfdc03bcd` | luecke | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Bei den Einsparpotenzialen für Lebensmittel fehlt der Bezug zur aktuellen Preissteigerung von +0,4 % bei Nahrungsmitteln. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `7017065ee7c74c7ae452` | veraltet | 8 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel nutzt Kostenszenarien für 2024/2025, während aktuelle Daten für Oktober 2026 eine Inflationsrate von +2,8 % ausweisen. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 24f05ddc03ffdd50118f --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 4816322f061dfdc03bcd --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7017065ee7c74c7ae452 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-07-frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-09-07-frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `1e06a96f6f71e104ce0b` | praezision | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Während Meal Prep als großer Sparhebel betont wird, zeigt die Marktlage für Nahrungsmittel eine moderate Teuerung von nur 0,4 %, was die Priorisierung der Sparbemühungen relativiert. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `81c6a707139046b83ccd` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Ratgeber empfiehlt die Revision von Fixkosten, lässt aber die drastische Preissteigerung bei Energie von +14,9 % unerwähnt, die ein wesentlicher Treiber der Haushaltsausgaben ist. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `8cc00288af8a1f2b02d8` | veraltet | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Budget-Tipps berücksichtigen nicht die aktuelle Inflationsrate von 2,8 % (Stand Oktober 2026), was die Kaufkraft-Annahmen im Haushaltsbuch beeinflusst. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 1e06a96f6f71e104ce0b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 81c6a707139046b83ccd --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 8cc00288af8a1f2b02d8 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `5a1bf10697f58e5fe14a` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Ratgeber nennt Sparbeispiele für Heizkosten, lässt aber die aktuelle Preissteigerung bei Energie von +14,9 % (Stand Oktober 2026) unerwähnt, die den finanziellen Druck auf Haushalte massiv erhöht. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `e48f9237cff6397c49a6` | praezision | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die in Aussicht gestellten Ersparnisse von bis zu 200 € werden nicht ins Verhältnis zur aktuellen Inflationsrate von +2,8 % gesetzt, welche die reale Kaufkraft des gesparten Geldes mindert. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `f6de6b078d49f9d42e0e` | praezision | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Beim Fokus auf Lebensmittelplanung fehlt der Hinweis auf die vergleichsweise moderate Preissteigerung von +0,4 % bei Nahrungsmitteln, was diesen Hebel gegenüber den stark steigenden Energiekosten relativiert. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 5a1bf10697f58e5fe14a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e48f9237cff6397c49a6 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f6de6b078d49f9d42e0e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-11-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026` · **LIVE** (blockiert) · Risikoklasse standard · 2 Befund(e)

Datei: `content/posts/2026-09-11-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `6cb2229c5eb83b02da23` | veraltet | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Kalkulation der Fixkosten (Energie 140 €) und die Empfehlung zur Senkung der Kosten ignorieren den aktuellen Markttrend massiv steigender Energiepreise (+14,9 %), was die 50-Prozent-Quote für notwendige Ausgaben gefährdet. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `f00055a1cb65ee22165f` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Ratgeber verspricht eine 'planbare' Budgetierung, lässt aber die aktuelle Inflationsrate von 2,8 % unerwähnt, die insbesondere den Block der notwendigen Ausgaben (Nahrungsmittel +0,4 %) dynamisch belastet. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6cb2229c5eb83b02da23 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f00055a1cb65ee22165f --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden` · **LIVE** (blockiert) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `43470330b3b48c9cee49` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel empfiehlt, Kühl- und Gefriergeräte mindestens 24 Stunden, besser mehrere Tage zu messen, liefert jedoch keine Quelle für diese Messdauer. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `8ddc1025e45be176ad3a` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Es wird kein regulatorischer Rahmen (z. B. Aufgaben der Bundesnetzagentur) genannt, obwohl das Thema Stromversorgung berührt wird; entsprechende Vorgaben fehlen im Text. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `95d6d2877620e5a056ce` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass Verbraucherzentralen oder Bibliotheken Messgeräte verleihen, wird ohne Beleg gemacht. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `ab16029999747466a638` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Berechnung mit einem Arbeitspreis von 0,37 €/kWh wird angegeben, ohne dass ein aktueller Preis‑ oder Marktwert belegt wird. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `b057dee3603e09f494b5` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Das Amortisationsbeispiel (Kaufpreis 650 €, Amortisationszeit 10,3 Jahre) enthält keine Quelle für die zugrunde liegenden Annahmen oder Preise. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

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
| `278d89267d9122a1e9d8` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Angaben zu gesetzlichen Vorgaben für Warmwassertemperaturen zur Vermeidung von Legionellen werden nicht durch die bereitgestellten Quellen gestützt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `450c3aa629342062825e` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass Warmwasser der zweitgrößte Kostenposten im Haushalt ist, wird nicht durch eine der bereitgestellten Quellen belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `7601167c9f3560093fb0` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Behauptung, dass Warmwasser in der Heizkostenabrechnung üblicherweise als eigener Block ausgewiesen wird, fehlt eine Quellenangabe. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `7efbcd7a4275fe1577bb` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Verweise auf die Verbraucherzentrale (Tipps zum Heizkosten sparen, Heizung optimieren) können nicht mit den angegebenen Fundstellen belegt werden. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `971a719f94ca492f640e` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Preis von 0,30 € pro Kilowattstunde in der Modellrechnung ist nicht mit einer Quelle belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

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
| `7a87eaaa2b863ba8cc46` | luecke | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Ein relevanter regulatorischer Rahmen (z. B. Vorgaben der Bundesnetzagentur oder BDEW) wird nicht genannt, obwohl die Fundstelle darauf hinweist, dass solche Vorgaben existieren. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `9d67a5e6bd11212c7c1e` | praezision | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass bestimmte Gerätegruppen (TV‑Ecke, Homeoffice, alte Audio‑Technik) zuerst zu senken „lohnt“, wird ohne messbare Daten oder Vergleichskriterien gemacht. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `a54abc1cad73d20fb689` | luecke | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die konkreten Jahreskosten (z. B. 32 € für 10 W Standby) beruhen auf dem nicht belegten Strompreis und werden nicht als Modellrechnung gekennzeichnet. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `a7d1cf6485921e117919` | luecke | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der angegebene durchschnittliche Strompreis von 37,3 Cent/kWh (BDEW‑Schnitt) wird ohne Quellenangabe genannt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `a7f69a854430d62a4a3e` | luecke | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Empfehlung, dass ein günstigerer Arbeitspreis der zweite wichtigste Hebel sei, fehlt jede Quelle oder regulatorische Einordnung. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

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
| `33278b9e7942ebfdbbac` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Definition des Begriffs „Last Minute“ (maximal 14 Tage zwischen Buchung und Abreise) wird mit dem Deutschen Reiseverband angegeben, jedoch fehlt ein Nachweis. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `6ad7358a9afcfef3babb` | praezision | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Angabe, dass Preisalarme keinen Tiefstpreis garantieren, wird nicht durch konkrete Zahlen oder Vergleichsstudien belegt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `7c375a3e1a9bfab1468c` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Hinweis auf § 651r BGB (Insolvenzsicherung bei Pauschalreisen) enthält keinen Verweis auf eine Rechtsquelle oder Verbraucherzentrale‑Information. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `ea11d36614fa115503b4` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Behauptung, dass Nachlässe von bis zu 50 % nur Einzelfälle sind, wird ohne Quellenangabe präsentiert. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `f7b1c869dd8e442eaf16` | praezision | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Aussage, dass der „beste Zeitpunkt zum Buchen“ ein Modellwert sei, bleibt vage und ohne messbare Daten oder Studien untermauert. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 33278b9e7942ebfdbbac --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6ad7358a9afcfef3babb --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7c375a3e1a9bfab1468c --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ea11d36614fa115503b4 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f7b1c869dd8e442eaf16 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit` · **LIVE** (blockiert) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `47f855cb4f0fe1e5c65f` | luecke | 14 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Angaben zu möglichen Einsparungen beim Kfz‑Versicherungswechsel (150 €‑400 € bzw. 180 €‑350 €) sind ohne Quellenangabe; keine der genannten Zahlen findet sich in den bereitgestellten Statistiken. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `6b0aa3429d97e8c74ed8` | luecke | 14 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Behauptung, technische Maßnahmen beim Heizen senken den Energieverbrauch um 8 %‑12 %, wird nicht belegt; die bereitgestellten Daten enthalten lediglich die allgemeine Preisentwicklung von Energie (+14,9 %). | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `7f66ec82ee1a3f095b0c` | praezision | 14 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Aussage, der Herbst sei die „lukrativste Spar‑Saison des Jahres“, ist nicht durch messbare Daten gestützt; ein Vergleich mit anderen Jahreszeiten fehlt. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `84c991c5d152b14a2675` | luecke | 14 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Gesamteinsparungen von 500 €‑1.300 € pro Haushalt werden als Modellrechnung präsentiert, jedoch ohne Kennzeichnung als Modell und ohne Quellenangabe. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `a70e7adc97c58317ccc1` | luecke | 14 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Das angegebene Sparpotenzial von 50 €‑80 € durch saisonale Lebensmittel‑ und Vorratshaltung ist nicht mit einer Quelle untermauert. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

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
| `0051151e6c46f4c2bdb3` | luecke | 14 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Der Artikel nennt eine Kautionshöhe von 900 € bis 2.500 €, ohne dass die Verbraucherzentrale diese Spanne angibt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `0790f52160dfaa819917` | luecke | 14 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die angegebene Ersparnis von 145 € bei einer einwöchigen Anmietung ist nicht durch Zahlen der Verbraucherzentrale gedeckt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `53c3fde8e986e6560890` | luecke | 14 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Behauptung, dass Flughafen‑Mietstationen 15 %‑25 % teurer sind, wird von der Verbraucherzentrale nicht bestätigt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `89adecebaae75c147402` | luecke | 14 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Aussage, dass eine „Zero‑Excess“-Option die Kaution komplett auf 0 € senkt und dafür 5 €‑12 € pro Tag kostet, wird von der Verbraucherzentrale nicht belegt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `a1a269b73a1b9c2dfc88` | luecke | 14 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Der Hinweis, dass eine Vollkasko ohne Selbstbeteiligung nur 3 €‑8 € pro Tag mehr kostet, fehlt in den Angaben der Verbraucherzentrale. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 0051151e6c46f4c2bdb3 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 0790f52160dfaa819917 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 53c3fde8e986e6560890 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 89adecebaae75c147402 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a1a269b73a1b9c2dfc88 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-02-preiswert-surfen-so-findest-du-den-optimalen-dsl-anschluss` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-10-02-preiswert-surfen-so-findest-du-den-optimalen-dsl-anschluss/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `6b5921bdc76490587167` | luecke | 1 T | Text unverändert seit dem Befund | Seit 2026 nutzen die großen Anbieter die Technik mit dem Namen Vectoring; das ist ein Modellwert. Sie senkt das Rauschen auf der Leitung. In der Stadt sind damit bis zu 250 Mbps stabil drin. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `8436b91bdb63a6316979` | praezision | 1 T | Text unverändert seit dem Befund | Preisgarantie über mindestens 12 Monate; ohne Garantie darf der Anbieter bald erhöhen, oft um bis zu 10 %. | – |
| `a4ff01e649b789f19e6a` | luecke | 1 T | Text unverändert seit dem Befund | Für 50 Mbps zahlst du heute meist ca. 20–40 € im Monat; das ist ein Beispielwert. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6b5921bdc76490587167 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 8436b91bdb63a6316979 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a4ff01e649b789f19e6a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-09-energiekosten-senken-smarte-helfer-fuer-den-haushalt` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-10-09-energiekosten-senken-smarte-helfer-fuer-den-haushalt/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `4d0125136c5b940946e4` | luecke | 0 T | Text unverändert seit dem Befund | Lichtsteuerung: Bedarfssteuerung – 2 bis 5 % des Stromverbrauchs. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `7aeb2098034d16a46885` | luecke | 0 T | Text unverändert seit dem Befund | Anbieter locken mit Neukundenboni, die nach der üblichen Erstlaufzeit entfallen; danach steigt der Arbeitspreis massiv an. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `ea97b5dd6695de127fd2` | luecke | 0 T | Text unverändert seit dem Befund | Heizungssteuerung: Smarte Thermostate können Heizkosten einsparen. Die Spanne von 10 bis 25 % ist ein Beispielwert aus der Rechnung unten. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 4d0125136c5b940946e4 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7aeb2098034d16a46885 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ea97b5dd6695de127fd2 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-12-energieausweis-was-das-dokument-fuer-deine-fixkosten` · **LIVE** (blockiert) · Risikoklasse standard · 4 Befund(e)

Datei: `content/posts/2026-10-12-energieausweis-was-das-dokument-fuer-deine-fixkosten/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `1dc0f20f9ab3a6b783bc` | luecke | 0 T | Text unverändert seit dem Befund | Behauptung, dass ein fehlender Ausweis zu empfindlichen Bußgeldern führt, fehlt eine belegbare Quelle. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `7b94ca07b36c0b7cb1cc` | luecke | 0 T | Text unverändert seit dem Befund | Aussage, dass Baudenkmäler von der Ausweispflicht befreit sind, wird nicht durch die angegebene Quelle gestützt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `985f506ee04087bf7253` | luecke | 0 T | Text unverändert seit dem Befund | Angabe, dass ein Wechsel von Energieeffizienzklasse F zu C über 2.000 € Jahresersparnis bringt, ist unbelegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `ee321fa37210590f7e9b` | luecke | 0 T | Text unverändert seit dem Befund | Keine Quelle für die Angabe, dass ein Energieausweis ein volles Jahrzehnt gültig ist, sofern keine größeren Umbauten erfolgen. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 1dc0f20f9ab3a6b783bc --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7b94ca07b36c0b7cb1cc --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 985f506ee04087bf7253 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden ee321fa37210590f7e9b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-12-kleine-energiespar-tricks-die-deine-kosten-sofort-senken` · **LIVE** (blockiert) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-10-12-kleine-energiespar-tricks-die-deine-kosten-sofort-senken/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `19ab248b17415c73edfb` | luecke | 0 T | Text unverändert seit dem Befund | Thermostat um 1 °C senken \| 4 % – 6 % der Heizkosten | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `372bb51051e8bd7c5f71` | luecke | 0 T | Text unverändert seit dem Befund | Viele Anbieter belohnen einen niedrigen Verbrauch mit besseren Konditionen | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `6aaff85e3a7591d0c5b2` | luecke | 0 T | Text unverändert seit dem Befund | für dich entstehen keine Mehrkosten | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `7e6087a4117a857a92c8` | luecke | 0 T | Text unverändert seit dem Befund | Durch diese zwei Maßnahmen sparst du in dieser Beispielrechnung jährlich rund 140 € | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `e28b4ad1f6d608d2ec77` | luecke | 0 T | Text unverändert seit dem Befund | Strom (LED‑Umrüstung) \| 100 € – 140 € \| etwa 8 % | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 19ab248b17415c73edfb --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 372bb51051e8bd7c5f71 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6aaff85e3a7591d0c5b2 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7e6087a4117a857a92c8 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e28b4ad1f6d608d2ec77 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-24-bankgebuehren-senken-7-schritte-zum-guenstigeren-konto` · **LIVE** (blockiert) · Risikoklasse standard · 4 Befund(e)

Datei: `content/posts/2026-10-24-bankgebuehren-senken-7-schritte-zum-guenstigeren-konto/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `04ae33652c1c5eb4e2b8` | luecke | 0 T | Text unverändert seit dem Befund | Ein kurzer Check spart dir oft mehrere hundert Euro im Jahr. | – |
| `5223a3c7287ff81939cd` | luecke | 0 T | Text unverändert seit dem Befund | Faustregel: ... mehr als 5 % deines Nettoeinkommens ... Meist sinken diese Kosten um über 80 % | – |
| `9800545ae945ec280b34` | luecke | 0 T | Text unverändert seit dem Befund | Ein Wechsel ist für dich in der Regel komplett kostenlos als Beispielwert. | – |
| `bc0e4f2eb357a682c674` | luecke | 0 T | Text unverändert seit dem Befund | Bei einem normalen Einkommen sollten die Gebühren fast Null sein. | – |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 04ae33652c1c5eb4e2b8 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 5223a3c7287ff81939cd --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 9800545ae945ec280b34 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden bc0e4f2eb357a682c674 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-13-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-11-13-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu`

Herkunft nach Datums-Lift: `2026-11-01-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu` → `2026-11-13-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu`. Befund-ID und Fassungsanker bleiben unverändert; das Re-Dating ist keine fachliche Entscheidung.

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `0b564f460c41218244bd` | luecke | 10 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel behauptet, dass Heizöl‑Preise ihr Tief meist in den Monaten Januar und Februar erreichen, ohne dafür eine Quelle anzugeben. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `3ad2eefed314eb172c26` | luecke | 10 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass durch frühzeitige Bestellung Kosten um 10 % bis 20 % im Herbst eingespart werden können, ist unbelegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `43788c2cdcdfda52e753` | luecke | 10 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Modellrechnung verwendet einen Tiefpreis von 0,80 €/Liter, ohne dass diese Preisangabe belegt wird. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `5eedec8afbdef6a4ca49` | luecke | 10 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Es wird angegeben, dass typische Fehler beim Heizölkauf bis zu 15 % Mehrkosten verursachen können, jedoch fehlt ein Nachweis für diese Zahl. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `81881c5bc61824d25f5a` | praezision | 10 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Faustregel, dass man bestellen sollte, wenn Preise vier Wochen unter dem Schnitt der letzten 12 Monate liegen, wird ohne Messgrundlage oder Quelle genannt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 0b564f460c41218244bd --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 3ad2eefed314eb172c26 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 43788c2cdcdfda52e753 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 5eedec8afbdef6a4ca49 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 81881c5bc61824d25f5a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag` · nicht im Live-Bestand · 3 Befund(e)

Seite: `2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `82cc87314e0d4fcb21e9` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die kalkulierte Ersparnis bei Energiekosten (15 €/Monat) berücksichtigt nicht den aktuellen Markttrend massiv steigender Preise (+14,9 % bei Energie). | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `bd5ee70c85ec7db78f26` | luecke | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die pauschalen Jahressparwerte von 300 € bis 1.000 € werden in Marktfakten-Positur ohne Nennung einer Referenzquelle oder eines Absenders (z. B. Destatis) aufgeführt. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `f83f21c1f2e2012f672e` | praezision | 7 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Sparversprechen im Bereich Lebensmittel vernachlässigen die Inflationsrate bei Nahrungsmitteln (+0,4 %), was Modellrechnungen ohne Inflationsbereinigung ungenau macht. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 82cc87314e0d4fcb21e9 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden bd5ee70c85ec7db78f26 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f83f21c1f2e2012f672e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-06-guenstige-fluege-fuer-den-spaetsommer-finden` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-11-06-guenstige-fluege-fuer-den-spaetsommer-finden`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `0e68294e193918d5b5b0` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Text nennt eine angeblich gängige Faustregel von 20 % Rabatt im Spätsommer (Beispiel 300 € → 240 €) ohne Quellenangabe. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `4d91ef71fa76febdb769` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Es wird angegeben, dass Flüge an Dienstagen und Mittwochen günstiger seien und an Freitagen bzw. Sonntagen teurer, ohne Beleg. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `5b427fb4f05b475d9a89` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Empfehlung, Flüge vier bis acht Wochen im Voraus zu buchen, weil die Preise dann am niedrigsten seien, wird nicht belegt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `e933e34672f0b6464d1e` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel behauptet, dass im Spätsommer die Nachfrage nach Flügen sinkt und dadurch die Preise fallen, ohne dafür eine Quelle anzugeben. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `eb6a47df5535fa267a82` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Behauptet wird, dass Kombi‑Deals für Flug + Mietwagen typischerweise 5–15 % Einsparungen bringen, ohne Nachweis. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

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
| `0f248aaad2d2b8d87d0d` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die im Marktradar angegebenen Durchschnittspreise für Strom (37,3 ct/kWh) und Gas (12,23 ct/kWh) werden ohne Quellenangabe genannt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `3a69bd57886154a18b8e` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass bei Preiserhöhungen ein gesetzliches 14‑tägiges Sonderkündigungsrecht besteht, fehlt eine rechtliche Quellenangabe. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `4f777954306ac7b21e03` | luecke | 6 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Behauptung, dass ein Lieferantenwechsel und ein technischer Anschlusswechsel nicht dasselbe seien, wird nicht durch eine Quelle belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 0f248aaad2d2b8d87d0d --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 3a69bd57886154a18b8e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 4f777954306ac7b21e03 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-09-reisekasse-fuellen-7-wege-zu-mehr-budget-fuer-den-urlaub` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-11-09-reisekasse-fuellen-7-wege-zu-mehr-budget-fuer-den-urlaub`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `11a92bff688ccbb5a485` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Behauptung, dass bis zum Sommer 500 € mehr im Urlaubsbudget verfügbar sind, fehlt eine Quellenangabe. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `1d4896d8ed60f5b6921f` | praezision | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass Cashback‑Portale „seit vielen Jahren am Markt etabliert“ sind, ist ein unpräzises Superlativ ohne messbare Daten. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `4d2bc6c3e60fb9b4a719` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass eine 5 %ige Reduktion der Fixkosten bei 800 € Aufwand 40 € im Monat bzw. 480 € im Jahr spart, wird nicht durch die angeführte Quelle belegt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `76b5cdfda85516962cf8` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Angaben zu typischen Kündigungsfristen von ein bis drei Monaten werden von der Quelle nicht bestätigt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `b292db236a31ea0a1629` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der genannte durchschnittliche Cashback‑Satz von 2 % der Ausgaben ist nicht durch die Quelle gestützt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 11a92bff688ccbb5a485 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 1d4896d8ed60f5b6921f --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 4d2bc6c3e60fb9b4a719 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 76b5cdfda85516962cf8 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden b292db236a31ea0a1629 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-13-strompreis-2026-herbst-check-fuer-deine-stromkosten` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-11-13-strompreis-2026-herbst-check-fuer-deine-stromkosten`

Herkunft nach Datums-Lift: `2026-11-09-strompreis-2026-herbst-check-fuer-deine-stromkosten` → `2026-11-13-strompreis-2026-herbst-check-fuer-deine-stromkosten`. Befund-ID und Fassungsanker bleiben unverändert; das Re-Dating ist keine fachliche Entscheidung.

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `1c6e4d2f12da24ec4081` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Hinweis, dass ein Anbieterwechsel im Durchschnitt 3‑6 Wochen dauert, fehlt eine nachweisbare Quelle. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `5b539daf371f7362a3ef` | praezision | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Empfehlung, dynamische Tarife erforderten zwingend einen Smart Meter, wird ohne Angabe von Voraussetzungen, Kosten oder Verfügbarkeit präzisiert. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `77d809de9e06d1d6910d` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Es wird eine Prognose für den Strompreis 2026 angegeben („Trends erkennen“, „Netzentgelte steigen“), ohne dass dafür aktuelle Marktdaten oder offizielle Prognosen genannt werden. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `ad7c0a90ef52ff35130e` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel behauptet, dass Preisgarantien vor Preissteigerungen schützen, liefert jedoch keine Quelle für diese Aussage. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `f227178fbda2cc59c350` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass Ökostrom‑Tarife häufig günstiger als die Grundversorgung seien, wird nicht durch eine Quelle belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

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
| `3efe31a371440636f465` | luecke | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Empfehlung, den Handytarif einmal jährlich bzw. vierteljährlich zu prüfen, fehlt eine Quellenangabe. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `49c1a762c2df16c52b7a` | luecke | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel behauptet, dass Verträge nach sechs Monaten die Preise erhöhen, ohne dafür eine Quelle anzugeben. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `56c5b1f92a70c6ebeb0b` | praezision | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass CHECK24 alle aktuellen Angebote liefert, ist ein Vollständigkeitsversprechen ohne Messgröße. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `c6d20c93f94cee2ae5ae` | praezision | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Regel „Datenvolumen halbieren, das du wirklich brauchst“ wird als allgemeine Faustregel präsentiert, ohne Messdaten oder Quelle. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `f6a30c4191c47f5cdf0a` | luecke | 3 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Faustregel, dass zusätzliche Gebühren mindestens 5 % der Grundgebühr betragen müssen, wird nicht belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 3efe31a371440636f465 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 49c1a762c2df16c52b7a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 56c5b1f92a70c6ebeb0b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden c6d20c93f94cee2ae5ae --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f6a30c4191c47f5cdf0a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-28-dsl-und-internet-flat-guenstig-sichern` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-10-28-dsl-und-internet-flat-guenstig-sichern`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `05be346e82c80b2a8664` | luecke | 14 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Wechselboni von 50 € bis 100 € werden genannt, jedoch fehlt jede belegbare Angabe zu deren Höhe oder Häufigkeit. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `d0a5cf7bb64eb0cd46c8` | luecke | 14 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Der Artikel erwähnt keinen regulatorischen Rahmen (z. B. Informations‑ und Preisbindungspflichten der Bundesnetzagentur) obwohl die Fundstelle darauf hinweist, dass solche Vorgaben existieren. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `ec53e181336df8dc61ac` | luecke | 14 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Der Artikel behauptet, dass DSL‑Verträge häufig eine Laufzeit von 24 Monaten haben und danach eine Kündigungsfrist von einem Monat gilt, ohne dafür eine Quelle anzugeben. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `f3f9184bfca9b097f68e` | luecke | 14 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die 50‑30‑20‑Regel wird als allgemein gültige Budget‑Methode dargestellt, ohne Hinweis, dass es sich um ein Modell handelt oder Quelle dafür zu nennen. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `fb4d2260f4fa291c35ae` | praezision | 14 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Angabe, dass für zwei HD‑Streams gleichzeitig etwa 30 Mbit/s benötigt werden, ist nicht durch Daten belegt und lässt Spielraum für Fehlinterpretationen. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |

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
| `1d448c9cdc2618ef9bdf` | luecke | 3 T | Text unverändert seit dem Befund | Der Hinweis, dass Festpreis‑Tarife in der Regel einen Aufschlag enthalten, fehlt jede Beleggrundlage. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `2188f6b0006eb0607871` | luecke | 3 T | Text unverändert seit dem Befund | Die Behauptung, die Bundesnetzagentur fordere die getrennte Angabe von Grund‑ und Arbeitspreis, wird nicht durch die verlinkte Quelle belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `33917254a91a1c551389` | praezision | 3 T | Text unverändert seit dem Befund | Die Aussage, dass variable Tarife mit Preisgarantie oder Deckel im Vergleich „selten ganz oben“ stehen, ist ein untermauertes Superlativ ohne Messgröße. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `82badcfa80493134c12a` | luecke | 3 T | Text unverändert seit dem Befund | Die Aussage, dass variable Tarife das Marktpreisrisiko vollständig auf den Kunden übertragen, wird ohne Quellenangabe gemacht. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `b44fd9621fb708f45c90` | luecke | 3 T | Text unverändert seit dem Befund | Die Behauptung, dass sich die Energiemärkte 2026 wieder stärker bewegen, wird ohne aktuelle Marktdaten belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 1d448c9cdc2618ef9bdf --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 2188f6b0006eb0607871 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 33917254a91a1c551389 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 82badcfa80493134c12a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden b44fd9621fb708f45c90 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-09-wlan-verbessern-mesh-system-oder-repeater-im-check` · nicht im Live-Bestand · 3 Befund(e)

Seite: `2026-11-09-wlan-verbessern-mesh-system-oder-repeater-im-check`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `6d89862b38c33c827817` | praezision | 3 T | Text unverändert seit dem Befund | Die pauschale Behauptung, Hardware bleibe stets Eigentum des Nutzers, ist unpräzise, da die Bundesnetzagentur die Kupfer-Glas-Migration begleitet, die oft providerseitige Technikwechsel und neue Netzabschlusspunkte erfordert. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `72bbf29e4ef70a71ad06` | luecke | 3 T | Text unverändert seit dem Befund | Aussagen zu Markttrends wie hohen Neukundenrabatten und Wechselprämien werden als Marktfakten ohne Bezug zu offiziellen Referenzwerten oder Berichten der Aufsichtsbehörde dargestellt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `f0103f4c6a777aaa4845` | luecke | 3 T | Text unverändert seit dem Befund | Der Ratgeber thematisiert den Anbieterwechsel und Bandbreiten, lässt aber den regulatorischen Rahmen der Bundesnetzagentur zur Breitbandversorgung und zum Verbraucherschutz bei Minderleistung unerwähnt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6d89862b38c33c827817 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 72bbf29e4ef70a71ad06 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f0103f4c6a777aaa4845 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-29-konto-karten-update-was-sich-jetzt-fuer-dich-aendert` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-09-29-konto-karten-update-was-sich-jetzt-fuer-dich-aendert`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `2140cb752c4069ae86a0` | luecke | 2 T | Text unverändert seit dem Befund | Für die herkömmliche Girocard werden häufig Gebühren von etwa 0,99 Euro monatlich erhoben – Angabe fehlt in den bereitgestellten Quellen. | [Quelle](https://www.verbraucherzentrale.de/aktuelle-meldungen) |
| `766e3df5f10bb91ff03b` | luecke | 2 T | Text unverändert seit dem Befund | Ein schneller Kontowechsel sei jederzeit kostenlos und sichere dauerhaft die besten Zinsen – diese Aussage fehlt in den bereitgestellten Quellen. | [Quelle](https://www.tagesschau.de/wirtschaft/unternehmen/faq-nvidia-spionage-100.html) |
| `d11731ee598db94f14c0` | luecke | 2 T | Text unverändert seit dem Befund | Die Maestro‑Funktion soll seit Juli 2023 schrittweise eingestellt werden – keine Quelle dafür vorhanden. | [Quelle](https://www.verbraucherzentrale.de/aktuelle-meldungen) |
| `ef34d0d6243902be1bc9` | luecke | 2 T | Text unverändert seit dem Befund | Befristete Sonderzinsen bei Tagesgeldkonten und deren starke Absenkung nach der Aktionsphase werden behauptet, ohne dass die angegebenen Quellen dies belegen. | [Quelle](https://www.tagesschau.de/wirtschaft/unternehmen/faq-nvidia-spionage-100.html) |
| `f48dd250f165f647c90a` | luecke | 2 T | Text unverändert seit dem Befund | Viele Banken stellen ihre Standardkarten auf kostenlose Debit‑Visas oder Mastercards um – ohne aktuelle Quelle belegt. | [Quelle](https://www.verbraucherzentrale.de/aktuelle-meldungen) |

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
| `61ed9d03642fa5afa89e` | praezision | 2 T | Text unverändert seit dem Befund | Die pauschale Einordnung der Behördenseite als 'kein Beleg für Tipps' greift zu kurz; die Fundstelle ist das zentrale Aufsichtsportal für den regulierten Energiemarkt (Strom/Gas). | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `bbd476563a6a52c57957` | luecke | 2 T | Text unverändert seit dem Befund | Der Artikel verweist für Informationen zum Stromverbrauch von Routern auf die Bundesnetzagentur, verlinkt jedoch die Fachabteilung für Energie statt die zuständige Abteilung für Telekommunikation. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 61ed9d03642fa5afa89e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden bbd476563a6a52c57957 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `frugalismus` · nicht im Live-Bestand · 3 Befund(e)

Seite: `frugalismus`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `760cdea8544be9d1c7c0` | luecke | 2 T | Text unverändert seit dem Befund | Die im 'Zins-Marktradar Q4 2026' genannten Benchmark-Daten für Tagesgeld (3,10–3,45 %) und Dispozinsen (11,5–13,8 %) werden der Bundesbank und BaFin zugeschrieben, sind jedoch in den Recherche-Fundstellen nicht belegt. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `cacd65ac080f79a719ae` | praezision | 2 T | Text unverändert seit dem Befund | Der Ratgeber thematisiert Fixkosten-Senkungen allgemein, lässt aber die laut Destatis signifikante Preissteigerung bei Energie (+12,2 %) unerwähnt, die den Spielraum für die angestrebte 50-Prozent-Quote prägt. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `d2bfec8aa9b7a0807f0e` | luecke | 2 T | Text unverändert seit dem Befund | Die 50–30–20-Budgetformel wird als Destatis-Standardmodell ausgewiesen; die angegebene Quelle des Statistischen Bundesamtes enthält jedoch nur Daten zum Verbraucherpreisindex, keine Budget-Verteilungsschlüssel. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 760cdea8544be9d1c7c0 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden cacd65ac080f79a719ae --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d2bfec8aa9b7a0807f0e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-19-urlaubskasse-clever-aufbessern` · nicht im Live-Bestand · 3 Befund(e)

Seite: `2026-10-19-urlaubskasse-clever-aufbessern`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `17cddd994cefcdc30f31` | luecke | 1 T | Text unverändert seit dem Befund | Ein Mietwagen ist oft ein teurer Posten. Er kostet meistens fast so viel wie der Flug oder das Hotel. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `676fdb5ff70228b06bdc` | luecke | 1 T | Text unverändert seit dem Befund | Geld sollte innerhalb von 48 Stunden zurück sein. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `88051266499d4040f7f3` | luecke | 1 T | Text unverändert seit dem Befund | Die Preise werden dort fair und offen gezeigt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 17cddd994cefcdc30f31 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 676fdb5ff70228b06bdc --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 88051266499d4040f7f3 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-11-kreditkarte-ohne-jahresgebuehr-die-besten-kostenlosen-karten` · nicht im Live-Bestand · 4 Befund(e)

Seite: `2026-11-11-kreditkarte-ohne-jahresgebuehr-die-besten-kostenlosen-karten`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `228c9da3c42ee90e34bf` | luecke | 1 T | Text unverändert seit dem Befund | Eine typische Auslandseinsatzgebühr liegt bei 1 % des Umsatzes. | – |
| `7728690d5c2f7c141d8d` | luecke | 1 T | Text unverändert seit dem Befund | Du hast eine Jahresgebühr von 60 € und kündigst erst 30 Tage nach Ablauf der Frist. | – |
| `cc0de46a82ad90851506` | luecke | 1 T | Text unverändert seit dem Befund | Du investierst 15 Minuten in den CHECK24‑Filter und sparst im Schnitt 5 Minuten pro Anbieter. | – |
| `d553d0d6c7706a69ad13` | luecke | 1 T | Text unverändert seit dem Befund | Keine versteckten Kosten, wenn die Karte „keine Jahres‑ und keine Auslandseinsatzgebühr“ nennt. | – |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 228c9da3c42ee90e34bf --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7728690d5c2f7c141d8d --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden cc0de46a82ad90851506 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden d553d0d6c7706a69ad13 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

---

_Diese Akte entscheidet nichts und schließt nichts. Sie macht sichtbar, was zu entscheiden ist, wer es entscheiden muss (Herausgeber/Redaktion) und wie der Schließweg lautet. Regel: `scripts/faktenfrische_befund_ledger.py`, Governance C46._
