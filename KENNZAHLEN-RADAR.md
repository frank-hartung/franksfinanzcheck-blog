# 📡 Kennzahlen-Radar (Frühwarnung)
**Stand:** 2026-10-13 · **Auftrag:** Veränderungen früher erkennen (Konkurrenz-Parität Finanztip, H5)

- 🔴 **P1 – AKTION** (fällig + neues Brief-Signal): **1**
- 🟠 **P2 – FÄLLIG** (Prüfintervall überschritten): **0**
- 🟡 **P3 – SIGNAL** (Brief erwähnt Änderung): **4**
- 🟢 **OK** (im Rhythmus): **3**

---

## 🔴 P1 – sofort prüfen
### 🔴 Bundesnetzagentur: Breitband-/DSL-Marktdaten
- **Prüfstand:** 2026-07-10 · **Intervall:** 90 d · **Alter:** 95 d · **YMYL**
- **Quelle:** [Bundesnetzagentur – Telekommunikation](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html)
- 📡 **Brief-Signal:** data/research/artikel/internet-dsl.md (2026-09-27) – Treffer: Breitband, DSL, Glasfaser, Mobilfunk



## 🟠 P2 – fällig
_Keine_


## 🟡 P3 – Signale beobachten
### 🟡 BDEW-Strompreisanalyse: Haushaltsstrompreis (37,0 ct/kWh)
- **Prüfstand:** 2026-09-28 · **Intervall:** 30 d · **Alter:** 15 d · **YMYL**
- **Quelle:** [BDEW-Strompreisanalyse (Herbst 2026)](https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/)
- 📡 **Brief-Signal:** data/research/2026-10-12-internet-recherche.md (2026-10-12) – Treffer: Strompreis
- 📡 **Brief-Signal:** data/research/artikel/2026-10-12-stromfresser-im-haushalt-entlarven.md (2026-10-12) – Treffer: Strompreis
- 📡 **Brief-Signal:** data/research/artikel/2026-10-08-energie-update-was-sich-jetzt-fuer-dich-aendert.md (2026-10-08) – Treffer: Strompreis
- ⚠️ `2026-09-10-energie-update-was-sich-jetzt-fuer-dich-aendert`: Slug nicht gefunden

### 🟡 BDEW-Gaspreisanalyse: Gaspreis Einfamilienhaus (11,93 ct/kWh)
- **Prüfstand:** 2026-09-28 · **Intervall:** 30 d · **Alter:** 15 d · **YMYL**
- **Quelle:** [BDEW-Gaspreisanalyse (August 2026)](https://www.bdew.de/service/daten-und-grafiken/bdew-gaspreisanalyse/)
- 📡 **Brief-Signal:** data/research/artikel/2026-10-12-stromfresser-im-haushalt-entlarven.md (2026-10-12) – Treffer: Gaspreis, Heizkosten
- 📡 **Brief-Signal:** data/research/artikel/2026-10-08-energie-update-was-sich-jetzt-fuer-dich-aendert.md (2026-10-08) – Treffer: Gaspreis, Heizkosten

### 🟡 Bundesnetzagentur: Markt- und Preisdaten Strom/Gas
- **Prüfstand:** 2026-09-28 · **Intervall:** 60 d · **Alter:** 15 d · **YMYL**
- **Quelle:** [Bundesnetzagentur – Elektrizität und Gas](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/start.html)
- 📡 **Brief-Signal:** data/research/artikel/2026-10-12-stromfresser-im-haushalt-entlarven.md (2026-10-12) – Treffer: Grundversorgung
- 📡 **Brief-Signal:** data/research/artikel/2026-10-08-energie-update-was-sich-jetzt-fuer-dich-aendert.md (2026-10-08) – Treffer: Grundversorgung

### 🟡 Marktcheck: Kostenlose Girokonten (Konditionen)
- **Prüfstand:** 2026-09-28 · **Intervall:** 90 d · **Alter:** 15 d · **YMYL**
- **Quelle:** [Verbraucherzentrale – Girokonto: Was Sie darüber wissen sollten](https://www.verbraucherzentrale.de/wissen/geld-versicherungen/sparen-und-anlegen/girokonto-was-sie-darueber-wissen-sollten-4990)
- 📡 **Brief-Signal:** data/research/artikel/2026-09-29-konto-karten-update-was-sich-jetzt-fuer-dich-aendert.md (2026-09-29) – Treffer: Girokonto
- ⚠️ `2026-09-22-konto-karten-update-was-sich-jetzt-fuer-dich-aendert`: Slug nicht gefunden
- 🕰️ `pillar/konto-karten`: Artikel-Stand 2026-08-31 liegt VOR dem Kennzahlenstand 2026-09-28 – Zahlen ggf. veraltet



---

### Nächste Schritte (Chefredakteur)

1. **P1 zuerst:** Brief-Signal lesen (`data/research/…`), neuen Wert an der
   Quelle prüfen, dann `ist_wert` + `stand` im Register von Hand aktualisieren
   (Register ist menschlich kuratiert – die Maschine schreibt es nie).
2. **Artikel hinterherhängend:** Zahlen im Artikel aktualisieren, danach
   `scripts/set_lastmod.py --git-changed` laufen lassen.
3. **Recherche anstoßen:** `python3 scripts/faktenfrische.py --apply --max 3`
   frischt die Belegketten (`quellen`/`faktencheck`) der betroffenen Artikel auf.

_Automatisch erzeugt von `scripts/kennzahlen_radar.py` am 2026-10-13._
