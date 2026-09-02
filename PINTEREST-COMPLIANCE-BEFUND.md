# 📌 Pinterest-Compliance-Befund (FranksFinanzcheck)

**Stand:** 2026-09-02 · **Anlass:** Spam-Sperre der Domain
`franksfinanzcheck.de` · **Zweck:** Ursachenanalyse und Nachweis der Behebung

---

## 1. Festgestellte Ursache

Die Pin-Planung verteilte **73 Pins auf nur 29 Ziel-URLs**. Ein Artikel
erhielt 9 Pins; vier Ziele bekamen zwei Pins **am selben Tag**. Dieses
Verhältnis erzeugt ein Repeat-Pin-/Link-Spam-Signal.

Das war ein Planungsfehler, kein Täuschungsversuch: Die Absicht war,
verschiedene inhaltliche Blickwinkel eines Artikels zu zeigen. Uns ist klar,
dass mehrere Pins auf dieselbe URL unabhängig von der Absicht als Spam
gewertet werden.

## 2. Was NICHT die Ursache war (geprüft und belegt)

| Prüfpunkt | Befund |
|---|---|
| Werbekennzeichnung | **25/25** Pin-Texte mit `*Werbung`-Präfix |
| Doppelte Pin-Texte | **0** Near-Duplicates (6-Wort-Shingle, Jaccard ≥ 0,25) |
| Doppelte Pin-Bilder | **0** exakte Cover-Duplikate bei 26 Bildern |
| Publikations-Kadenz | nur Fri, Mon, Wed, max. 3 Artikel/Tag |
| Affiliate-Weiterleitungen | `/go/`-Gateway mit `noindex,nofollow,noarchive`, in `robots.txt` gesperrt |
| Cloaking | keins – Pins verlinken **Artikelseiten**, nie Affiliate-URLs |
| API-Nutzung | **0** Pins je über die API erstellt (Registry leer, Rate 0/40 Tag) |

## 3. Umgesetzte Maßnahmen

**Technisches Gate (nicht umgehbar):** Zwei neue Regeln im Plan-Guard, die
vor **jedem** Pin-Lauf greifen:

- **P6 – max. 3 Pins pro Ziel-URL** (vorher: bis zu 9)
- **P7 – min. 7 Tage Abstand** zwischen zwei Pins auf dieselbe URL
  (vorher: bis zu 0 Tage, also gleicher Tag)

UTM-Parameter zählen dabei nicht als neues Ziel.

**Ergebnis der Bereinigung:**

| Kennzahl | vorher | nachher |
|---|---|---|
| Pins im Plan | 73 | **48** |
| Ziel-URLs | 29 | 29 |
| Max. Pins pro Ziel | 9 | **3** |
| Kleinster Abstand | 0 Tage | **7 Tage** |
| Zurückgestellte Pins | – | 25 |

**Mengenvorgaben korrigiert:** Die interne Zielmenge (≥60 Pins) war nur durch
Mehrfach-Pins erreichbar und setzte damit einen Fehlanreiz. Sie wurde auf ≥40
gesenkt. Zusätzliche Pins entstehen künftig durch neue Artikel.

**Absicherung:** 5 eingefrorene Testfälle verhindern, dass die Regel je
wieder aufgeweicht wird. Das Gate läuft automatisch vor jedem Pin-Lauf.

## 4. Laufender Betrieb

Die automatische Pin-Erstellung ist bis zur Klärung ausgesetzt. Wir bitten um
Prüfung und stehen für Rückfragen bereit.

_Erzeugt aus dem Repository-Stand; alle Zahlen sind reproduzierbar über
`scripts/pinterest_plan_guard.py` und `scripts/spam_guard.py`._
