# BEFUND-AKTE – offene Fachbefunde der Faktenfrische

_Stand 2026-11-05 · erzeugt von `scripts/faktenfrische_befund_akte.py` · Quelle: `data/faktenfrische_queue.json` + `data/faktenfrische_entscheidungen.yaml` (eine Regel, zwei Leser)._

**47 offene Befunde auf 11 Seiten · davon 4 Live-Seiten mit 13 Befunden · ältester 6 Tage · Frist 14 Tage.**

| Kennzahl | Wert |
|---|---|
| Offene Befunde | 47 |
| Seiten betroffen | 11 (davon live: 4) |
| Text seit dem Befund geändert | 13 |
| Altbestand ohne Fassungs-Hash | 15 |
| Nicht entscheidbar (Seite fehlt) | 5 |
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

> **Wichtig – betrifft 28 von 47 Befunden** (in der Tabelle als Fassung markiert): Der Text ist seit dem Befund bereits geändert worden (Heilung) oder stammt aus dem Altbestand. Die Entscheidung bezieht sich ausdrücklich auf den HEUTIGEN Text – bitte diesen lesen, nicht den alten Befund abnicken. Diese Prüfung kann dir die Maschine nicht abnehmen – sie darf sie aber auch nicht verhindern.

## Seiten

### `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026` · **LIVE** (blockiert) · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `30caa57be394afb62947` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Für den angeführten BDEW-Durchschnittspreis von 11,93 Cent/kWh fehlt in den Recherche-Fundstellen ein entsprechender Beleg. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `32a3ea879f2cf126b3a7` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Der Artikel lässt den in der Quelle explizit genannten Regulierungsrahmen der 'Unternehmenspflichten' unerwähnt, der für den Schutz der Verbraucher beim Anbieterwechsel zentral ist. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `c583efe1ce02df3ca2d7` | luecke | 4 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die im Artikel genannte Ersparnis-Berechnung der Bundesnetzagentur für Januar 2026 (360 €) wird durch die allgemeine Übersichtsseite der Behörde nicht gestützt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 30caa57be394afb62947 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 32a3ea879f2cf126b3a7 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden c583efe1ce02df3ca2d7 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit` · **LIVE** (blockiert) · Risikoklasse standard · 5 Befund(e)

Datei: `content/posts/2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `47f855cb4f0fe1e5c65f` | luecke | 6 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Angaben zu möglichen Einsparungen beim Kfz‑Versicherungswechsel (150 €‑400 € bzw. 180 €‑350 €) sind ohne Quellenangabe; keine der genannten Zahlen findet sich in den bereitgestellten Statistiken. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `6b0aa3429d97e8c74ed8` | luecke | 6 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Behauptung, technische Maßnahmen beim Heizen senken den Energieverbrauch um 8 %‑12 %, wird nicht belegt; die bereitgestellten Daten enthalten lediglich die allgemeine Preisentwicklung von Energie (+14,9 %). | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `7f66ec82ee1a3f095b0c` | praezision | 6 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Aussage, der Herbst sei die „lukrativste Spar‑Saison des Jahres“, ist nicht durch messbare Daten gestützt; ein Vergleich mit anderen Jahreszeiten fehlt. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `84c991c5d152b14a2675` | luecke | 6 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Gesamteinsparungen von 500 €‑1.300 € pro Haushalt werden als Modellrechnung präsentiert, jedoch ohne Kennzeichnung als Modell und ohne Quellenangabe. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `a70e7adc97c58317ccc1` | luecke | 6 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Das angegebene Sparpotenzial von 50 €‑80 € durch saisonale Lebensmittel‑ und Vorratshaltung ist nicht mit einer Quelle untermauert. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 47f855cb4f0fe1e5c65f --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6b0aa3429d97e8c74ed8 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7f66ec82ee1a3f095b0c --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 84c991c5d152b14a2675 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a70e7adc97c58317ccc1 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich` · **LIVE** · Risikoklasse standard · 2 Befund(e)

Datei: `content/posts/2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `20c08cb650ef6e24af64` | luecke | 0 T | Text unverändert seit dem Befund | Der Ratgeber vernachlässigt bei der Kalkulation der Sparfähigkeit die massive Preissteigerung bei Energie (+14,9 %), die das Budget für monatliche Sparraten erheblich belastet. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `6aafb23c0c6dbb06ce3b` | veraltet | 0 T | Text unverändert seit dem Befund | Die im Rechenbeispiel zur Realrendite genutzte Inflationsrate von 2 % ist veraltet; die vorläufige Rate für Oktober 2026 beträgt laut Statistischem Bundesamt 2,8 %. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 20c08cb650ef6e24af64 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 6aafb23c0c6dbb06ce3b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-09-07-frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum` · **LIVE** · Risikoklasse standard · 3 Befund(e)

Datei: `content/posts/2026-09-07-frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum/index.md`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `24f05ddc03ffdd50118f` | praezision | 0 T | Text unverändert seit dem Befund | Die Kalkulation der Fixkostenersparnis bei Energie (Strom/Gas) ist unpräzise, da sie den aktuellen Preisanstieg von +14,9 % bei Energieprodukten nicht einbezieht. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `4816322f061dfdc03bcd` | luecke | 0 T | Text unverändert seit dem Befund | Bei den Einsparpotenzialen für Lebensmittel fehlt der Bezug zur aktuellen Preissteigerung von +0,4 % bei Nahrungsmitteln. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `7017065ee7c74c7ae452` | veraltet | 0 T | Text unverändert seit dem Befund | Der Artikel nutzt Kostenszenarien für 2024/2025, während aktuelle Daten für Oktober 2026 eine Inflationsrate von +2,8 % ausweisen. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 24f05ddc03ffdd50118f --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 4816322f061dfdc03bcd --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7017065ee7c74c7ae452 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-10-30-kostenloses-girokonto-ohne-gebuehren-finden` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-10-30-kostenloses-girokonto-ohne-gebuehren-finden`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `176642ea8acfa44f1152` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Behauptung, dass Inlands‑Überweisungen in der Regel kostenlos sind, fehlt eine entsprechende Quelle. | – |
| `2520f45d441ef87614e3` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Behauptung, dass ein kostenloses Girokonto keine reguläre Kontoführungsgebühr erhebt, wird nicht durch die bereitgestellten Quellen belegt. | – |
| `33bda5941052d9334598` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Quantitative Aussage, dass ein kostenloses Girokonto mindestens ein Drittel der bisherigen Kontokosten einsparen kann, ist unbelegt. | – |
| `7406eaba3aa749c46f4b` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Zeitangabe, dass die Kontoeröffnung meist innerhalb weniger Werktage abgeschlossen ist, wird nicht durch die genannten Quellen gestützt. | – |
| `9f47e6d2aa8cf2a8ff91` | luecke | 5 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Angabe, dass die meisten Banken ein Mindestguthaben von ein paar hundert Euro verlangen, fehlt eine fundierte Quelle. | – |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 176642ea8acfa44f1152 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 2520f45d441ef87614e3 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 33bda5941052d9334598 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 7406eaba3aa749c46f4b --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 9f47e6d2aa8cf2a8ff91 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-02-last-minute-urlaubsangebote-sichern` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-11-02-last-minute-urlaubsangebote-sichern`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `0a2bec9dc02e16c057ee` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die 50‑30‑20‑Regel für die Urlaubsbudget‑Aufteilung wird ohne Quellenangabe präsentiert. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `274c32d1a16e9dffcf1a` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Angabe, dass das Weglassen der Vollkasko‑Selbstbeteiligung die Kosten um 10 % bis 20 % senken kann, ist nicht mit einer Quelle belegt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `5c572a933edece129bba` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Aussage, dass Stornogebühren häufig einem Tagespreis entsprechen, ist unbelegt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `9d9d4afc8d6c421a0d14` | luecke | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Behauptung, dass Last‑Minute‑Deals wegen Restkapazitäten zu niedrigeren Preisen führen, fehlt eine fundierte Quelle. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `fb50388539a0e8b4461c` | praezision | 2 T | Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen | Die Empfehlung, ausschließlich CHECK24 für den Mietwagenvergleich zu nutzen, ist ein unqualifiziertes Superlativ ohne Messgrundlage. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

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
| `05be346e82c80b2a8664` | luecke | 6 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Wechselboni von 50 € bis 100 € werden genannt, jedoch fehlt jede belegbare Angabe zu deren Höhe oder Häufigkeit. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `d0a5cf7bb64eb0cd46c8` | luecke | 6 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Der Artikel erwähnt keinen regulatorischen Rahmen (z. B. Informations‑ und Preisbindungspflichten der Bundesnetzagentur) obwohl die Fundstelle darauf hinweist, dass solche Vorgaben existieren. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `ec53e181336df8dc61ac` | luecke | 6 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Der Artikel behauptet, dass DSL‑Verträge häufig eine Laufzeit von 24 Monaten haben und danach eine Kündigungsfrist von einem Monat gilt, ohne dafür eine Quelle anzugeben. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `f3f9184bfca9b097f68e` | luecke | 6 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die 50‑30‑20‑Regel wird als allgemein gültige Budget‑Methode dargestellt, ohne Hinweis, dass es sich um ein Modell handelt oder Quelle dafür zu nennen. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |
| `fb4d2260f4fa291c35ae` | praezision | 6 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Angabe, dass für zwei HD‑Streams gleichzeitig etwa 30 Mbit/s benötigt werden, ist nicht durch Daten belegt und lässt Spielraum für Fehlinterpretationen. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html) |

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
| `360dbd44c71db04f43e0` | luecke | 6 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Preisangaben für die Privathaftpflicht (35 – 65 € jährlich) werden ohne Quellenangabe genannt. | [Quelle](https://www.gdv.de/gdv/medien/medieninformationen) |
| `a4f736ca6f8f1a70fe60` | praezision | 6 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Der Hinweis, dass ein jährlicher Kfz‑Wechsel‑Check zum Stichtag 30. November „fast immer“ zu Einsparungen führt, ist pauschal und nicht durch konkrete Daten gestützt. | – |
| `c2de49121dea2b8b7cc6` | luecke | 6 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Empfehlung einer Mindestdeckungssumme von 50 Millionen Euro für Personen‑, Sach‑ und Vermögensschäden in der Privathaftpflicht wird nicht durch eine Quelle belegt. | [Quelle](https://www.gdv.de/gdv/medien/medieninformationen) |
| `de9bc512fad04e99c1da` | praezision | 6 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Aussage, dass Elementarschäden bei Wohn‑ und Hausratversicherung „unverzichtbar“ seien, ist ein unqualifiziertes Superlativ ohne messbare Grundlage. | – |
| `e7ab68c9e3b2f443c904` | luecke | 6 T | Altbestand ohne Fassungs-Hash – am heutigen Text prüfen | Die Behauptung, dass ein Kfz‑Wechsel zum 30. November jährlich 100 – 300 € spart, fehlt jede belegbare Marktinformation. | [Quelle](https://www.gdv.de/gdv/medien/medieninformationen) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 360dbd44c71db04f43e0 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a4f736ca6f8f1a70fe60 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden c2de49121dea2b8b7cc6 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden de9bc512fad04e99c1da --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e7ab68c9e3b2f443c904 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-04-guenstigen-mietwagen-fuer-den-urlaub-buchen` · nicht im Live-Bestand · 4 Befund(e)

Seite: `2026-11-04-guenstigen-mietwagen-fuer-den-urlaub-buchen`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `785eee76d888bb05ad96` | luecke | 0 T | Text unverändert seit dem Befund | Die im Rechenbeispiel genutzte Kilometerpauschale von 0,20 €/km wird als Referenzwert ohne Quellenangabe (z. B. Branchenverband) angeführt. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `843ec148e23841b7bf35` | luecke | 0 T | Text unverändert seit dem Befund | Der als Handlungsschritt empfohlene '4K-Prüfpfad' wird im Text nicht erläutert und ist in der genannten Quelle nicht enthalten. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `def43a04853be4c35f7f` | luecke | 0 T | Text unverändert seit dem Befund | Die Preisprognose (Anstieg in den letzten 3 Wochen) und der empfohlene Buchungsvorlauf (3-4 Wochen) sind Marktdaten ohne Beleg durch die Fachquelle. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |
| `f064ea49ccefde26aef9` | praezision | 0 T | Text unverändert seit dem Befund | Das Versprechen, CHECK24 vergleiche 'alle großen Anbieter', ist ein Vollständigkeitsversprechen ohne Nennung von Auswahlkriterien oder der Marktabdeckung. | [Quelle](https://www.verbraucherzentrale.de/wissen/reise-mobilitaet) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 785eee76d888bb05ad96 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 843ec148e23841b7bf35 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden def43a04853be4c35f7f --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f064ea49ccefde26aef9 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-05-waschmaschine-beladen-weniger-kosten-bei-jedem-waschgang` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-11-05-waschmaschine-beladen-weniger-kosten-bei-jedem-waschgang`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `4284fd2d9c9005e7af8f` | praezision | 0 T | Text unverändert seit dem Befund | Behauptung, dass Überladung der Maschine zu schnellerem Verschleiß und teuren Reparaturen führt, wird ohne konkrete Daten oder Messgröße angegeben. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `84e247f17354e224c973` | praezision | 0 T | Text unverändert seit dem Befund | Aussage, dass das richtige Beladen allein die Fixkosten senkt, ohne weitere Maßnahmen, ist ein pauschales Leistungsversprechen ohne Nennung von Mechanismen oder Grenzen. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `a2a7dc69f10393af6531` | luecke | 0 T | Text unverändert seit dem Befund | Die Modellrechnung (0,9 kWh/50 L bei vollem Waschgang, 0,6 kWh/35 L bei halbem Waschgang, Strompreis 0,40 €/kWh, Wasserpreis 0,005 €/L) und die daraus resultierende Jahresersparnis von 22 € fehlen einer fundierten Quelle. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `cb794331f1cc0c715a55` | luecke | 0 T | Text unverändert seit dem Befund | Die Aussage, dass bei 4 Waschgängen pro Woche ein durchschnittlicher Haushalt rund 5 € jährlich an Strom‑ und Wasserkosten spart, ist nicht mit einer Quelle belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `e6729081522126e972c2` | luecke | 0 T | Text unverändert seit dem Befund | Angabe, dass ein optimal beladener Trommel (ca. 80 % Kapazität) bis zu 15 % weniger Wasser und Energie verbraucht, wird nicht durch eine Quelle belegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 4284fd2d9c9005e7af8f --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 84e247f17354e224c973 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden a2a7dc69f10393af6531 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden cb794331f1cc0c715a55 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden e6729081522126e972c2 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

### `2026-11-01-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu` · nicht im Live-Bestand · 5 Befund(e)

Seite: `2026-11-01-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `0b564f460c41218244bd` | luecke | 2 T | Seite nicht lesbar – nicht entscheidbar | Der Artikel behauptet, dass Heizöl‑Preise ihr Tief meist in den Monaten Januar und Februar erreichen, ohne dafür eine Quelle anzugeben. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `3ad2eefed314eb172c26` | luecke | 2 T | Seite nicht lesbar – nicht entscheidbar | Die Aussage, dass durch frühzeitige Bestellung Kosten um 10 % bis 20 % im Herbst eingespart werden können, ist unbelegt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `43788c2cdcdfda52e753` | luecke | 2 T | Seite nicht lesbar – nicht entscheidbar | Die Modellrechnung verwendet einen Tiefpreis von 0,80 €/Liter, ohne dass diese Preisangabe belegt wird. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `5eedec8afbdef6a4ca49` | luecke | 2 T | Seite nicht lesbar – nicht entscheidbar | Es wird angegeben, dass typische Fehler beim Heizölkauf bis zu 15 % Mehrkosten verursachen können, jedoch fehlt ein Nachweis für diese Zahl. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |
| `81881c5bc61824d25f5a` | praezision | 2 T | Seite nicht lesbar – nicht entscheidbar | Die Faustregel, dass man bestellen sollte, wenn Preise vier Wochen unter dem Schnitt der letzten 12 Monate liegen, wird ohne Messgrundlage oder Quelle genannt. | [Quelle](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 0b564f460c41218244bd --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 3ad2eefed314eb172c26 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 43788c2cdcdfda52e753 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 5eedec8afbdef6a4ca49 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 81881c5bc61824d25f5a --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

---

_Diese Akte entscheidet nichts und schließt nichts. Sie macht sichtbar, was zu entscheiden ist, wer es entscheiden muss (Herausgeber/Redaktion) und wie der Schließweg lautet. Regel: `scripts/faktenfrische_befund_ledger.py`, Governance C46._
