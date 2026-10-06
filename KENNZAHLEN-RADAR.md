# 📡 Kennzahlen-Radar (Frühwarnung)
**Stand:** 2026-10-06 · **Auftrag:** Veränderungen früher erkennen (Konkurrenz-Parität Finanztip, H5)

- 🔴 **P1 – AKTION** (fällig + neues Brief-Signal): **0**
- 🟠 **P2 – FÄLLIG** (Prüfintervall überschritten): **0**
- 🟡 **P3 – SIGNAL** (Brief erwähnt Änderung): **3**
- 🟢 **OK** (im Rhythmus): **5**

---

## 🔴 P1 – sofort prüfen
_Keine_


## 🟠 P2 – fällig
_Keine_


## 🟡 P3 – Signale beobachten
### 🟡 Bundesnetzagentur: Breitband-/DSL-Marktdaten
- **Prüfstand:** 2026-07-10 · **Intervall:** 90 d · **Alter:** 88 d · **YMYL**
- **Quelle:** [Bundesnetzagentur – Telekommunikation](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/start.html)
- 📡 **Brief-Signal:** data/research/artikel/internet-dsl.md (2026-09-27) – Treffer: Breitband, DSL, Glasfaser, Mobilfunk

### 🟡 BDEW-Strompreisanalyse: Haushaltsstrompreis (37,0 ct/kWh)
- **Prüfstand:** 2026-09-28 · **Intervall:** 30 d · **Alter:** 8 d · **YMYL**
- **Quelle:** [BDEW-Strompreisanalyse (Herbst 2026)](https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/)
- 📡 **Brief-Signal:** data/research/2026-10-05-internet-recherche.md (2026-10-05) – Treffer: Stromkosten, Strompreis
- ⚠️ `2026-09-10-energie-update-was-sich-jetzt-fuer-dich-aendert`: Slug nicht gefunden

### 🟡 Marktcheck: Kostenlose Girokonten (Konditionen)
- **Prüfstand:** 2026-09-28 · **Intervall:** 90 d · **Alter:** 8 d · **YMYL**
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

_Automatisch erzeugt von `scripts/kennzahlen_radar.py` am 2026-10-06._
