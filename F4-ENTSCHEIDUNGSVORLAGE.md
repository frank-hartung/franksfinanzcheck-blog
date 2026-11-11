# F4-Entscheidungsvorlage — offene Live-Befunde (Vorschlag)

**Status: VORSCHLAG – nichts entschieden.** Die Artikel bleiben in der
Scorecard blockiert, bis der Herausgeber die heutigen Fassungen bestätigt.
Dieses Dokument schreibt nichts in den Ledger und erzeugt keine Entscheidung.

**Bezugsstand: 2026-11-11** – der Stand der Befundakte (`erzeugt` aus `data/faktenfrische_befunde_state.json`), nicht die Wanduhr. So ist die Vorlage reproduzierbar und `--check` uhrfest.

**0 offene Live-Befunde auf 0 Artikeln.** Davon sind **0** bereits früher entschieden und durch eine spätere Textänderung
wieder geöffnet worden (fassungsgebundene Bindung, kein Rückfall). **0** Befunde sind neu.

Erzeugt von `scripts/f4_entscheidungsvorlage.py` aus `data/faktenfrische_befunde_state.json`,
`data/faktenfrische_entscheidungen.yaml`, dem Scorecard-Siegel und den heutigen Artikeln.
Regel: F4 ist per SSOT **menschlich** – die Maschine schließt hier nichts.

## Neu ohne frühere Entscheidung

_Keine – jeder offene Live-Befund hat eine frühere Entscheidung._

---

## Schließweg (eine Zeile je Befund)

```bash
python3 scripts/faktenfrische_befund_akte.py --schreiben
python3 scripts/release_scorecard.py --live --streng
```

_Jede Entscheidung ist fassungsgebunden: Sie gilt für den heute geprüften
Text (Projektion `betrieb-v3`). Ändert sich ein Satz, öffnet der Befund
erneut – das ist gewollt. Abgeleitete Blöcke und Leerzeilen öffnen nichts._
