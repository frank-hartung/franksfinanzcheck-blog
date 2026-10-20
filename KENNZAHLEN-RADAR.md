# 📡 Kennzahlen-Radar (Frühwarnung)
**Stand:** 2026-10-20 · **Auftrag:** Veränderungen früher erkennen (Konkurrenz-Parität Finanztip, H5)

- 🔴 **P1 – AKTION** (fällig + neues Brief-Signal): **0**
- 🟠 **P2 – FÄLLIG** (Prüfintervall überschritten): **0**
- 🟡 **P3 – SIGNAL** (Brief erwähnt Änderung): **1**
- 🟢 **OK** (im Rhythmus): **7**

---

## 🔴 P1 – sofort prüfen
_Keine_


## 🟠 P2 – fällig
_Keine_


## 🟡 P3 – Signale beobachten
### 🟡 Bundesnetzagentur: Markt- und Preisdaten Strom/Gas
- **Prüfstand:** 2026-10-13 · **Intervall:** 60 d · **Alter:** 7 d · **YMYL**
- **Quelle:** [Bundesnetzagentur – Elektrizität und Gas](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html)
- 📡 **Brief-Signal:** data/research/artikel/2026-10-14-heizperiode-vorbereiten-im-spaetsommer.md (2026-10-15) – Treffer: ElektrizitaetundGas



## 🟢 OK – im Rhythmus
### 🟢 Grundfreibetrag (Einkommensteuer)
- **Prüfstand:** 2026-01-02 · **Intervall:** 365 d · **Alter:** 291 d · **YMYL**
- **Quelle:** [Bundesministerium der Finanzen – Steuertarife](https://www.bundesfinanzministerium.de/Web/DE/Themen/Steuern/Steuertarife/steuertarife.html)

### 🟢 Kfz-Versicherung: Wechselfrist zum 30. November (30.11.2026 Datum)
- **Prüfstand:** 2026-09-17 · **Intervall:** 365 d · **Alter:** 33 d · **YMYL**
- **Quelle:** [Verbraucherzentrale – Kfz-Versicherung wechseln](https://www.verbraucherzentrale.de/wissen/verkehr/auto-kfz/autoversicherung-wechseln-so-gehts-10540)

### 🟢 BDEW-Strompreisanalyse: Haushaltsstrompreis (37,0 ct/kWh)
- **Prüfstand:** 2026-09-28 · **Intervall:** 30 d · **Alter:** 22 d · **YMYL**
- **Quelle:** [BDEW-Strompreisanalyse (Herbst 2026)](https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/)

### 🟢 BDEW-Gaspreisanalyse: Gaspreis Einfamilienhaus (11,93 ct/kWh)
- **Prüfstand:** 2026-09-28 · **Intervall:** 30 d · **Alter:** 22 d · **YMYL**
- **Quelle:** [BDEW-Gaspreisanalyse (August 2026)](https://www.bdew.de/service/daten-und-grafiken/bdew-gaspreisanalyse/)

### 🟢 Marktcheck: Kostenlose Girokonten (Konditionen)
- **Prüfstand:** 2026-09-28 · **Intervall:** 90 d · **Alter:** 22 d · **YMYL**
- **Quelle:** [Verbraucherzentrale – Girokonto: Was Sie darüber wissen sollten](https://www.verbraucherzentrale.de/wissen/geld-versicherungen/sparen-und-anlegen/girokonto-was-sie-darueber-wissen-sollten-4990)

### 🟢 EZB-Einlagenzins (Maßstab für Tagesgeld-Bestzinsen)
- **Prüfstand:** 2026-10-13 · **Intervall:** 42 d · **Alter:** 7 d · **YMYL**
- **Quelle:** [Deutsche Bundesbank – Aktuelle Zinssätze](https://www.bundesbank.de/de/statistiken/geld-und-kapitalmaerkte/aktuelle-zinssaetze)

### 🟢 Bundesnetzagentur: Breitband-/DSL-Marktdaten
- **Prüfstand:** 2026-10-13 · **Intervall:** 90 d · **Alter:** 7 d · **YMYL**
- **Quelle:** [Bundesnetzagentur – Telekommunikation](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html)



---

### Nächste Schritte (Chefredakteur)

1. **P1 zuerst:** Brief-Signal lesen (`data/research/…`), neuen Wert an der
   Quelle prüfen, dann `ist_wert` + `stand` im Register von Hand aktualisieren
   (Register ist menschlich kuratiert – die Maschine schreibt es nie).
2. **Artikel hinterherhängend:** Zahlen im Artikel aktualisieren, danach
   `scripts/set_lastmod.py --git-changed` laufen lassen.
3. **Recherche anstoßen:** `python3 scripts/faktenfrische.py --apply --max 3`
   frischt die Belegketten (`quellen`/`faktencheck`) der betroffenen Artikel auf.

_Automatisch erzeugt von `scripts/kennzahlen_radar.py` am 2026-10-20._
