# BEFUND-AKTE – offene Fachbefunde der Faktenfrische

_Stand 2026-11-11 · erzeugt von `scripts/faktenfrische_befund_akte.py` · Quelle: `data/faktenfrische_queue.json` + `data/faktenfrische_entscheidungen.yaml` (eine Regel, zwei Leser)._

**63 offene Befunde auf 15 Seiten · davon 0 Live-Seiten mit 0 Befunden · ältester 12 Tage · Frist 14 Tage.**

| Kennzahl | Wert |
|---|---|
| Offene Befunde | 63 |
| Seiten betroffen | 15 (davon live: 0) |
| Text seit dem Befund geändert | 35 |
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

> **Wichtig – betrifft 40 von 63 Befunden** (in der Tabelle als Fassung markiert): Der Text ist seit dem Befund bereits geändert worden (Heilung) oder stammt aus dem Altbestand. Die Entscheidung bezieht sich ausdrücklich auf den HEUTIGEN Text – bitte diesen lesen, nicht den alten Befund abnicken. Diese Prüfung kann dir die Maschine nicht abnehmen – sie darf sie aber auch nicht verhindern.

## Seiten

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
