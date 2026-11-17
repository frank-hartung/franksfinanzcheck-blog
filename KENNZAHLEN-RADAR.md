# 📡 Kennzahlen-Radar (Frühwarnung)
**Stand:** 2026-11-17 · **Auftrag:** Veränderungen früher erkennen (Konkurrenz-Parität Finanztip, H5)

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
- **Prüfstand:** 2026-09-17 · **Intervall:** 365 d · **Alter:** 61 d · **YMYL**
- **Quelle:** [Verbraucherzentrale – Kfz-Versicherung wechseln](https://www.verbraucherzentrale.de/wissen/verkehr/auto-kfz/autoversicherung-wechseln-so-gehts-10540)
- 📡 **Brief-Signal:** data/research/artikel/versicherungen.md (2026-10-30) – Treffer: Stichtag

### 🟡 Marktcheck: Kostenlose Girokonten (Konditionen)
- **Prüfstand:** 2026-09-28 · **Intervall:** 90 d · **Alter:** 50 d · **YMYL**
- **Quelle:** [Verbraucherzentrale – Girokonto: Was Sie darüber wissen sollten](https://www.verbraucherzentrale.de/wissen/geld-versicherungen/sparen-und-anlegen/girokonto-was-sie-darueber-wissen-sollten-4990)
- 📡 **Brief-Signal:** data/research/artikel/2026-10-30-kostenloses-girokonto-ohne-gebuehren-finden.md (2026-10-31) – Treffer: Girokonto, Kontoführung

### 🟡 Bundesnetzagentur: Markt- und Preisdaten Strom/Gas
- **Prüfstand:** 2026-10-13 · **Intervall:** 60 d · **Alter:** 35 d · **YMYL**
- **Quelle:** [Bundesnetzagentur – Elektrizität und Gas](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html)
- 📡 **Brief-Signal:** data/research/artikel/2026-10-07-wie-smart-home-geraete-deine-stromrechnung-wirklich-druecken.md (2026-11-16) – Treffer: ElektrizitaetundGas
- 📡 **Brief-Signal:** data/research/artikel/2026-10-24-energieeffizienz-im-haushalt-5-schnelle-spartricks.md (2026-11-16) – Treffer: ElektrizitaetundGas
- 📡 **Brief-Signal:** data/research/artikel/2026-11-16-e-auto-laden-so-senkst-du-deine-stromkosten.md (2026-11-16) – Treffer: ElektrizitaetundGas

### 🟡 EZB-Einlagenzins (Maßstab für Tagesgeld-Bestzinsen)
- **Prüfstand:** 2026-10-13 · **Intervall:** 42 d · **Alter:** 35 d · **YMYL**
- **Quelle:** [Deutsche Bundesbank – Aktuelle Zinssätze](https://www.bundesbank.de/de/statistiken/geld-und-kapitalmaerkte/aktuelle-zinssaetze)
- 📡 **Brief-Signal:** data/research/2026-10-26-internet-recherche.md (2026-10-26) – Treffer: EZB

### 🟡 Bundesnetzagentur: Breitband-/DSL-Marktdaten
- **Prüfstand:** 2026-10-13 · **Intervall:** 90 d · **Alter:** 35 d · **YMYL**
- **Quelle:** [Bundesnetzagentur – Telekommunikation](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html)
- 📡 **Brief-Signal:** data/research/artikel/2026-10-07-handyvertrag-kuendigen-raus-aus-der-kostenfalle-verlaengerung.md (2026-11-16) – Treffer: Telekommunikation/start
- 📡 **Brief-Signal:** data/research/artikel/2026-11-16-wlan-verbessern-lohnt-sich-mesh-oder-reicht-ein-repeater.md (2026-11-16) – Treffer: Telekommunikation/start
- 📡 **Brief-Signal:** data/research/artikel/2026-10-07-dsl-anbieter-wechseln-warum-treue-dich-bares-geld-kostet.md (2026-11-15) – Treffer: Telekommunikation/start



## 🟢 OK – im Rhythmus
### 🟢 Grundfreibetrag (Einkommensteuer)
- **Prüfstand:** 2026-01-02 · **Intervall:** 365 d · **Alter:** 319 d · **YMYL**
- **Quelle:** [Bundesministerium der Finanzen – Steuertarife](https://www.bundesfinanzministerium.de/Web/DE/Themen/Steuern/Steuertarife/steuertarife.html)

### 🟢 BDEW-Strompreisanalyse: Haushaltsstrompreis (37,3 ct/kWh)
- **Prüfstand:** 2026-11-04 · **Intervall:** 30 d · **Alter:** 13 d · **YMYL**
- **Quelle:** [BDEW-Strompreisanalyse (Herbst 2026)](https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/)

### 🟢 BDEW-Gaspreisanalyse: Gaspreis Einfamilienhaus (12,23 ct/kWh)
- **Prüfstand:** 2026-11-04 · **Intervall:** 30 d · **Alter:** 13 d · **YMYL**
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

_Automatisch erzeugt von `scripts/kennzahlen_radar.py` am 2026-11-17._
