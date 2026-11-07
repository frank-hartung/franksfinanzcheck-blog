# BEFUND-AKTE – offene Fachbefunde der Faktenfrische

_Stand 2026-11-07 · erzeugt von `scripts/faktenfrische_befund_akte.py` · Quelle: `data/faktenfrische_queue.json` + `data/faktenfrische_entscheidungen.yaml` (eine Regel, zwei Leser)._

**3 offene Befunde auf 1 Seiten · davon 0 Live-Seiten mit 0 Befunden · ältester 1 Tage · Frist 14 Tage.**

| Kennzahl | Wert |
|---|---|
| Offene Befunde | 3 |
| Seiten betroffen | 1 (davon live: 0) |
| Text seit dem Befund geändert | 0 |
| Altbestand ohne Fassungs-Hash | 0 |
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

## Seiten

### `2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag` · nicht im Live-Bestand · 3 Befund(e)

Seite: `2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag`

| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |
|---|---|---|---|---|---|
| `82cc87314e0d4fcb21e9` | luecke | 1 T | Text unverändert seit dem Befund | Die kalkulierte Ersparnis bei Energiekosten (15 €/Monat) berücksichtigt nicht den aktuellen Markttrend massiv steigender Preise (+14,9 % bei Energie). | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `bd5ee70c85ec7db78f26` | luecke | 1 T | Text unverändert seit dem Befund | Die pauschalen Jahressparwerte von 300 € bis 1.000 € werden in Marktfakten-Positur ohne Nennung einer Referenzquelle oder eines Absenders (z. B. Destatis) aufgeführt. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |
| `f83f21c1f2e2012f672e` | praezision | 1 T | Text unverändert seit dem Befund | Die Sparversprechen im Bereich Lebensmittel vernachlässigen die Inflationsrate bei Nahrungsmitteln (+0,4 %), was Modellrechnungen ohne Inflationsbereinigung ungenau macht. | [Quelle](https://www.destatis.de/DE/Themen/Wirtschaft/Preise/Verbraucherpreisindex/_inhalt.html) |

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden 82cc87314e0d4fcb21e9 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden bd5ee70c85ec7db78f26 --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
python3 scripts/faktenfrische_befund_ledger.py --entscheiden f83f21c1f2e2012f672e --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

---

_Diese Akte entscheidet nichts und schließt nichts. Sie macht sichtbar, was zu entscheiden ist, wer es entscheiden muss (Herausgeber/Redaktion) und wie der Schließweg lautet. Regel: `scripts/faktenfrische_befund_ledger.py`, Governance C46._
