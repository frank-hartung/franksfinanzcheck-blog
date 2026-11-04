# BEFUND-AKTE – offene Fachbefunde der Faktenfrische

_Stand 2026-11-04 · erzeugt von `scripts/faktenfrische_befund_akte.py` · Quelle: `data/faktenfrische_queue.json` + `data/faktenfrische_entscheidungen.yaml` (eine Regel, zwei Leser)._

**25 offene Befunde auf 5 Seiten · davon 0 Live-Seiten mit 0 Befunden · ältester 5 Tage · Frist 14 Tage.**

| Kennzahl | Wert |
|---|---|
| Offene Befunde | 25 |
| Seiten betroffen | 5 (davon live: 0) |
| Text seit dem Befund geändert | 15 |
| Altbestand ohne Fassungs-Hash | 10 |
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

> **Wichtig – betrifft 25 von 25 Befunden** (in der Tabelle als Fassung markiert): Der Text ist seit dem Befund bereits geändert worden (Heilung) oder stammt aus dem Altbestand. Die Entscheidung bezieht sich ausdrücklich auf den HEUTIGEN Text – bitte diesen lesen, nicht den alten Befund abnicken. Diese Prüfung kann dir die Maschine nicht abnehmen – sie darf sie aber auch nicht verhindern.

## Seiten

### `2026-10-30-kostenloses-girokonto-ohne-gebuehren-finden` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-10-30-kostenloses-girokonto-ohne-gebuehren-finden`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `176642ea8acfa44f1152` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Behauptung, dass Inlands‑Überweisungen in der Regel kostenlos sind, fehlt eine entsprechende Quelle. | – |
| `2520f45d441ef87614e3` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Behauptung, dass ein kostenloses Girokonto keine reguläre Kontoführungsgebühr erhebt, wird nicht durch die bereitgestellten Quellen belegt. | – |
| `33bda5941052d9334598` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Quantitative Aussage, dass ein kostenloses Girokonto mindestens ein Drittel der bisherigen Kontokosten einsparen kann, ist unbelegt. | – |
| `7406eaba3aa749c46f4b` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Zeitangabe, dass die Kontoeröffnung meist innerhalb weniger Werktage abgeschlossen ist, wird nicht durch die genannten Quellen gestützt. | – |
| `9f47e6d2aa8cf2a8ff91` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Angabe, dass die meisten Banken ein Mindestguthaben von ein paar hundert Euro verlangen, fehlt eine fundierte Quelle. | – |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 176642ea8acfa44f1152 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 2520f45d441ef87614e3 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 33bda5941052d9334598 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7406eaba3aa749c46f4b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 9f47e6d2aa8cf2a8ff91 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-01-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-11-01-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `0b564f460c41218244bd` | luecke | 1 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel behauptet, dass Heizöl‑Preise ihr Tief meist in den Monaten Januar und Februar erreichen, ohne dafür eine Quelle anzugeben. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `3ad2eefed314eb172c26` | luecke | 1 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass durch frühzeitige Bestellung Kosten um 10 % bis 20 % im Herbst eingespart werden können, ist unbelegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `43788c2cdcdfda52e753` | luecke | 1 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Modellrechnung verwendet einen Tiefpreis von 0,80 €/Liter, ohne dass diese Preisangabe belegt wird. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `5eedec8afbdef6a4ca49` | luecke | 1 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Es wird angegeben, dass typische Fehler beim Heizölkauf bis zu 15 % Mehrkosten verursachen können, jedoch fehlt ein Nachweis für diese Zahl. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `81881c5bc61824d25f5a` | praezision | 1 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Faustregel, dass man bestellen sollte, wenn Preise vier Wochen unter dem Schnitt der letzten 12 Monate liegen, wird ohne Messgrundlage oder Quelle genannt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 0b564f460c41218244bd --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 3ad2eefed314eb172c26 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 43788c2cdcdfda52e753 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 5eedec8afbdef6a4ca49 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 81881c5bc61824d25f5a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-02-last-minute-urlaubsangebote-sichern` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-11-02-last-minute-urlaubsangebote-sichern`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `0a2bec9dc02e16c057ee` | luecke | 1 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die 50‑30‑20‑Regel für die Urlaubsbudget‑Aufteilung wird ohne Quellenangabe präsentiert. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `274c32d1a16e9dffcf1a` | luecke | 1 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Angabe, dass das Weglassen der Vollkasko‑Selbstbeteiligung die Kosten um 10 % bis 20 % senken kann, ist nicht mit einer Quelle belegt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `5c572a933edece129bba` | luecke | 1 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass Stornogebühren häufig einem Tagespreis entsprechen, ist unbelegt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `9d9d4afc8d6c421a0d14` | luecke | 1 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Behauptung, dass Last‑Minute‑Deals wegen Restkapazitäten zu niedrigeren Preisen führen, fehlt eine fundierte Quelle. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `fb50388539a0e8b4461c` | praezision | 1 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Empfehlung, ausschließlich CHECK24 für den Mietwagenvergleich zu nutzen, ist ein unqualifiziertes Superlativ ohne Messgrundlage. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 0a2bec9dc02e16c057ee --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 274c32d1a16e9dffcf1a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 5c572a933edece129bba --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 9d9d4afc8d6c421a0d14 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden fb50388539a0e8b4461c --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-28-dsl-und-internet-flat-guenstig-sichern` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-10-28-dsl-und-internet-flat-guenstig-sichern`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `05be346e82c80b2a8664` | luecke | 5 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Wechselboni von 50 € bis 100 € werden genannt, jedoch fehlt jede belegbare Angabe zu deren Höhe oder Häufigkeit. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `d0a5cf7bb64eb0cd46c8` | luecke | 5 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Der Artikel erwähnt keinen regulatorischen Rahmen (z. B. Informations‑ und Preisbindungspflichten der Bundesnetzagentur) obwohl die Fundstelle darauf hinweist, dass solche Vorgaben existieren. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `ec53e181336df8dc61ac` | luecke | 5 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Der Artikel behauptet, dass DSL‑Verträge häufig eine Laufzeit von 24 Monaten haben und danach eine Kündigungsfrist von einem Monat gilt, ohne dafür eine Quelle anzugeben. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `f3f9184bfca9b097f68e` | luecke | 5 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die 50‑30‑20‑Regel wird als allgemein gültige Budget‑Methode dargestellt, ohne Hinweis, dass es sich um ein Modell handelt oder Quelle dafür zu nennen. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `fb4d2260f4fa291c35ae` | praezision | 5 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Angabe, dass für zwei HD‑Streams gleichzeitig etwa 30 Mbit/s benötigt werden, ist nicht durch Daten belegt und lässt Spielraum für Fehlinterpretationen. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |

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
| `360dbd44c71db04f43e0` | luecke | 5 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Preisangaben für die Privathaftpflicht (35 – 65 € jährlich) werden ohne Quellenangabe genannt. | [Quelle](https://www.gdv.de/gdv/medien/medieninformationen) |
| `a4f736ca6f8f1a70fe60` | praezision | 5 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Der Hinweis, dass ein jährlicher Kfz‑Wechsel‑Check zum Stichtag 30. November „fast immer“ zu Einsparungen führt, ist pauschal und nicht durch konkrete Daten gestützt. | – |
| `c2de49121dea2b8b7cc6` | luecke | 5 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Empfehlung einer Mindestdeckungssumme von 50 Millionen Euro für Personen‑, Sach‑ und Vermögensschäden in der Privathaftpflicht wird nicht durch eine Quelle belegt. | [Quelle](https://www.gdv.de/gdv/medien/medieninformationen) |
| `de9bc512fad04e99c1da` | praezision | 5 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Aussage, dass Elementarschäden bei Wohn‑ und Hausratversicherung „unverzichtbar“ seien, ist ein unqualifiziertes Superlativ ohne messbare Grundlage. | – |
| `e7ab68c9e3b2f443c904` | luecke | 5 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Behauptung, dass ein Kfz‑Wechsel zum 30. November jährlich 100 – 300 € spart, fehlt jede belegbare Marktinformation. | [Quelle](https://www.gdv.de/gdv/medien/medieninformationen) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 360dbd44c71db04f43e0 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a4f736ca6f8f1a70fe60 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden c2de49121dea2b8b7cc6 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden de9bc512fad04e99c1da --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e7ab68c9e3b2f443c904 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

---

_Diese Akte entscheidet nichts und schließt nichts. Sie macht sichtbar, was zu entscheiden ist, wer es entscheiden muss (Herausgeber/Redaktion) und wie der Schließweg lautet. Regel: `scripts/faktenfrische_befund_ledger.py`, Governance C46._
