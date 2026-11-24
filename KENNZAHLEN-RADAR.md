# 📡 Kennzahlen-Radar (Frühwarnung)
**Stand:** 2026-11-24 · **Auftrag:** Veränderungen früher erkennen (Konkurrenz-Parität Finanztip, H5)

- 🔴 **P1 – AKTION** (fällig + neues Brief-Signal): **0**
- 🟠 **P2 – FÄLLIG** (Prüfintervall überschritten): **0**
- 🟡 **P3 – SIGNAL** (Brief erwähnt Änderung): **5**
- 🟢 **OK** (im Rhythmus): **3**

---

## 🔴 P1 – sofort prüfen
_Keine_


## 🟠 P2 – fällig
_Keine_


## 🟡 P3 – Signale beobachten
### 🟡 Kfz-Versicherung: Wechselfrist zum 30. November (30.11.2026 Datum)
- **Prüfstand:** 2026-09-17 · **Intervall:** 365 d · **Alter:** 68 d · **YMYL**
- **Quelle:** [Verbraucherzentrale – Kfz-Versicherung wechseln](https://www.verbraucherzentrale.de/wissen/verkehr/auto-kfz/autoversicherung-wechseln-so-gehts-10540)
- 📡 **Brief-Signal:** data/research/artikel/versicherungen.md (2026-10-30) – Treffer: Stichtag

### 🟡 Marktcheck: Kostenlose Girokonten (Konditionen)
- **Prüfstand:** 2026-09-28 · **Intervall:** 90 d · **Alter:** 57 d · **YMYL**
- **Quelle:** [Verbraucherzentrale – Girokonto: Was Sie darüber wissen sollten](https://www.verbraucherzentrale.de/wissen/geld-versicherungen/sparen-und-anlegen/girokonto-was-sie-darueber-wissen-sollten-4990)
- 📡 **Brief-Signal:** data/research/artikel/2026-10-30-kostenloses-girokonto-ohne-gebuehren-finden.md (2026-10-31) – Treffer: Girokonto, Kontoführung

### 🟡 Bundesnetzagentur: Markt- und Preisdaten Strom/Gas
- **Prüfstand:** 2026-10-13 · **Intervall:** 60 d · **Alter:** 42 d · **YMYL**
- **Quelle:** [Bundesnetzagentur – Elektrizität und Gas](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html)
- 📡 **Brief-Signal:** data/research/artikel/2026-09-21-grundversorgung-strom-und-gas-was-sie-leistet.md (2026-11-23) – Treffer: ElektrizitaetundGas
- 📡 **Brief-Signal:** data/research/artikel/2026-09-24-internet-dsl-update-was-sich-jetzt-fuer-dich-aendert.md (2026-11-23) – Treffer: ElektrizitaetundGas
- 📡 **Brief-Signal:** data/research/artikel/2026-11-23-photovoltaik-lohnt-sich-eine-solaranlage-2026.md (2026-11-23) – Treffer: ElektrizitaetundGas

### 🟡 EZB-Einlagenzins (Maßstab für Tagesgeld-Bestzinsen)
- **Prüfstand:** 2026-10-13 · **Intervall:** 42 d · **Alter:** 42 d · **YMYL**
- **Quelle:** [Deutsche Bundesbank – Aktuelle Zinssätze](https://www.bundesbank.de/de/statistiken/geld-und-kapitalmaerkte/aktuelle-zinssaetze)
- 📡 **Brief-Signal:** data/research/2026-10-26-internet-recherche.md (2026-10-26) – Treffer: EZB

### 🟡 Bundesnetzagentur: Breitband-/DSL-Marktdaten
- **Prüfstand:** 2026-10-13 · **Intervall:** 90 d · **Alter:** 42 d · **YMYL**
- **Quelle:** [Bundesnetzagentur – Telekommunikation](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html)
- 📡 **Brief-Signal:** data/research/artikel/2026-09-24-internet-dsl-update-was-sich-jetzt-fuer-dich-aendert.md (2026-11-23) – Treffer: Telekommunikation/start
- 📡 **Brief-Signal:** data/research/artikel/2026-08-31-stoerung-beim-internetanbieter-so-sicherst-du-deine-rechte.md (2026-11-21) – Treffer: Telekommunikation/start
- 📡 **Brief-Signal:** data/research/artikel/2026-08-14-internet-dsl-wechseln-praxis-tipps-fuer-den-anbieterwechsel.md (2026-11-20) – Treffer: Telekommunikation/start



## 🟢 OK – im Rhythmus
### 🟢 Grundfreibetrag (Einkommensteuer)
- **Prüfstand:** 2026-01-02 · **Intervall:** 365 d · **Alter:** 326 d · **YMYL**
- **Quelle:** [Bundesministerium der Finanzen – Steuertarife](https://www.bundesfinanzministerium.de/Web/DE/Themen/Steuern/Steuertarife/steuertarife.html)

### 🟢 BDEW-Strompreisanalyse: Haushaltsstrompreis (37,3 ct/kWh)
- **Prüfstand:** 2026-11-04 · **Intervall:** 30 d · **Alter:** 20 d · **YMYL**
- **Quelle:** [BDEW-Strompreisanalyse (Herbst 2026)](https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/)

### 🟢 BDEW-Gaspreisanalyse: Gaspreis Einfamilienhaus (12,23 ct/kWh)
- **Prüfstand:** 2026-11-04 · **Intervall:** 30 d · **Alter:** 20 d · **YMYL**
- **Quelle:** [BDEW-Gaspreisanalyse (Herbst 2026)](https://www.bdew.de/service/daten-und-grafiken/bdew-gaspreisanalyse/)



---

### Nächste Schritte (Chefredakteur)

1. **P1 zuerst:** Brief-Signal lesen (`data/research/…`), neuen Wert an der
   Quelle prüfen, dann `ist_wert` + `stand` im Register von Hand aktualisieren
   (Register ist menschlich kuratiert – die Maschine schreibt es nie).
2. **Artikel hinterherhängend:** Zahlen im Artikel aktualisieren, danach
   `scripts/set_lastmod.py --git-changed` laufen lassen.
3. **Recherche anstoßen:** `python3 scripts/faktenfrische.py --apply --max 3`
   frischt die Belegketten (`quellen`/`faktencheck`) der betroffenen Artikel auf.

_Automatisch erzeugt von `scripts/kennzahlen_radar.py` am 2026-11-24._
