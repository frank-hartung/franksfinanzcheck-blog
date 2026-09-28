# 📡 Kennzahlen-Radar (Frühwarnung)
**Stand:** 2026-09-28 · **Auftrag:** Veränderungen früher erkennen (Konkurrenz-Parität Finanztip, H5)

- 🔴 **P1 – AKTION** (fällig + neues Brief-Signal): **4**
- 🟠 **P2 – FÄLLIG** (Prüfintervall überschritten): **0**
- 🟡 **P3 – SIGNAL** (Brief erwähnt Änderung): **1**
- 🟢 **OK** (im Rhythmus): **3**

---

## 🔴 P1 – sofort prüfen
### 🔴 Marktcheck: Kostenlose Girokonten (Konditionen)
- **Prüfstand:** 2026-02-14 · **Intervall:** 90 d · **Alter:** 226 d · **YMYL**
- **Quelle:** [Verbraucherzentrale – Kostenlose Girokonten](https://www.verbraucherzentrale.de/wissen/geld-versicherungen/sparen-und-anlegen/kostenlose-girokonten-worauf-sie-achten-sollten-10702)
- 📡 **Brief-Signal:** data/research/artikel/konto-karten.md (2026-09-27) – Treffer: Girokonto

### 🔴 Bundesnetzagentur: Markt- und Preisdaten Strom/Gas
- **Prüfstand:** 2026-07-10 · **Intervall:** 60 d · **Alter:** 80 d · **YMYL**
- **Quelle:** [Bundesnetzagentur – Elektrizität und Gas](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html)
- 📡 **Brief-Signal:** data/research/2026-09-12-internet-recherche.md (2026-09-12) – Treffer: Bundesnetzagentur, Energiepreis

### 🔴 BDEW-Strompreisanalyse: Haushaltsstrompreis (37,0 ct/kWh)
- **Prüfstand:** 2026-08-21 · **Intervall:** 30 d · **Alter:** 38 d · **YMYL**
- **Quelle:** [BDEW-Strompreisanalyse](https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/)
- 📡 **Brief-Signal:** data/research/2026-09-21-internet-recherche.md (2026-09-21) – Treffer: Strompreis
- 📡 **Brief-Signal:** data/research/2026-09-14-internet-recherche.md (2026-09-14) – Treffer: Stromkosten, Strompreis
- 📡 **Brief-Signal:** data/research/2026-09-12-internet-recherche.md (2026-09-12) – Treffer: Stromkosten, Strompreis

### 🔴 BDEW-Gaspreisanalyse: Gaspreis Einfamilienhaus (11,93 ct/kWh)
- **Prüfstand:** 2026-08-24 · **Intervall:** 30 d · **Alter:** 35 d · **YMYL**
- **Quelle:** [BDEW-Gaspreisanalyse](https://www.bdew.de/service/daten-und-grafiken/bdew-gaspreisanalyse/)
- 📡 **Brief-Signal:** data/research/2026-09-12-internet-recherche.md (2026-09-12) – Treffer: Gaspreis



## 🟠 P2 – fällig
_Keine_


## 🟡 P3 – Signale beobachten
### 🟡 Bundesnetzagentur: Breitband-/DSL-Marktdaten
- **Prüfstand:** 2026-07-10 · **Intervall:** 90 d · **Alter:** 80 d · **YMYL**
- **Quelle:** [Bundesnetzagentur – Telekommunikation](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html)
- 📡 **Brief-Signal:** data/research/artikel/internet-dsl.md (2026-09-27) – Treffer: Breitband, DSL, Glasfaser, Mobilfunk



---

### Nächste Schritte (Chefredakteur)

1. **P1 zuerst:** Brief-Signal lesen (`data/research/…`), neuen Wert an der
   Quelle prüfen, dann `ist_wert` + `stand` im Register von Hand aktualisieren
   (Register ist menschlich kuratiert – die Maschine schreibt es nie).
2. **Artikel hinterherhängend:** Zahlen im Artikel aktualisieren, danach
   `scripts/set_lastmod.py --git-changed` laufen lassen.
3. **Recherche anstoßen:** `python3 scripts/faktenfrische.py --apply --max 3`
   frischt die Belegketten (`quellen`/`faktencheck`) der betroffenen Artikel auf.

_Automatisch erzeugt von `scripts/kennzahlen_radar.py` am 2026-09-28._
