"""Gemeinsame Prüfregel der Befund-Akten: Arbeitsliste ist kein Befund.

Drei Aktentests (#763, #823, #911) prüften bisher, ob ihre Seiten überhaupt
noch in `data/faktenfrische_queue.json` stehen. Das war am Tag der Heilung
wahr und danach falsch: die Queue ist eine **Arbeitsliste**, kein
Befundregister. Sobald die Frist einer Seite in den Vorlauf rückt
(seit 06.11.2026: 14 Tage), steht sie dort wieder – mit dem Grund „frisch
geprüft vor N Tagen“, ohne einen einzigen offenen Befund. Am 07.11.2026
wurden deshalb zwei dieser Prüfungen rot, ohne dass ein Sachfehler
zurückgekehrt wäre (Frist 14.11. minus 14 Tage Vorlauf = 31.10.).

Seit 10.11.2026 (#1126) ist auch die Datei selbst eindeutig: `offen` führt
nur noch ARBEIT (fällig, befundbehaftet, abgebrochen), `vorlauf` die
turnusgemäßen Termine, `arbeitsvorrat` beide. Ein Eintrag in `offen`, der
„frisch geprüft, Frist in 7 Tagen“ sagt, ist damit kein Grenzfall mehr,
sondern ein Strukturfehler (siehe `faktenfrische.queue_invariante`).

Geprüft wird deshalb dreierlei:
  * offene **Befunde** derselben Seiten – über das Befund-Ledger
    (`faktenfrische_befund_ledger`), die Quelle, aus der Ticket und
    Redaktion arbeiten;
  * dass die Seiten nirgends in `offen` stehen (Arbeit ohne Arbeit);
  * dass ein Arbeitsvorrat-Eintrag keinen Befund mitschleppt.

Kein Testmodul: der Dateiname beginnt bewusst nicht mit `test_`.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "data" / "faktenfrische_queue.json"

sys.path.insert(0, str(ROOT / "scripts"))


def kern(slug: object) -> str:
    """Slug ohne Datumspräfix – die Identität, die eine Akte meint."""
    return re.sub(r"^\d{4}-\d{2}-\d{2}-", "", str(slug or ""))


def _queue(queue_path: Path | None = None) -> dict:
    pfad = Path(queue_path) if queue_path is not None else QUEUE
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}
    return daten if isinstance(daten, dict) else {}


def offene_befunde(slugs, queue_path: Path | None = None) -> list[dict]:
    """Offene Befunde zu genau diesen Seiten (leer = Befund geschlossen)."""
    import faktenfrische_befund_ledger as ledger

    gesucht = {kern(s) for s in slugs}
    pfad = Path(queue_path) if queue_path is not None else QUEUE
    return [befund for befund in ledger.offene_befunde(pfad)
            if kern(befund.get("slug")) in gesucht
            or kern(befund.get("ursprungs_slug")) in gesucht]


def eintraege(slugs, queue_path: Path | None = None) -> list[dict]:
    """ALLE Arbeitsvorrat-Einträge dieser Seiten – Arbeit und Vorlauf.

    Schema 2 trennt die beiden Listen; wer eine Seite wiederfinden will,
    liest die Obermenge. Schema 1 (nur `offen`) bleibt lesbar.
    """
    gesucht = {kern(s) for s in slugs}
    queue = _queue(queue_path)
    vorrat = queue.get("arbeitsvorrat")
    if not isinstance(vorrat, list):
        vorrat = list(queue.get("offen") or []) + list(queue.get("vorlauf") or [])
    return [eintrag for eintrag in vorrat
            if isinstance(eintrag, dict)
            and kern(eintrag.get("slug")) in gesucht]


def eintraege_in_offen(slugs, queue_path: Path | None = None) -> list[dict]:
    """Einträge, die als ARBEIT geführt werden (muss für gehealte Seiten leer sein)."""
    gesucht = {kern(s) for s in slugs}
    return [eintrag for eintrag in (_queue(queue_path).get("offen") or [])
            if isinstance(eintrag, dict)
            and kern(eintrag.get("slug")) in gesucht]


def arbeitsliste_traegt_befunde(slugs, queue_path: Path | None = None) -> list[dict]:
    """Einträge, die einen Befund mitschleppen (muss leer sein)."""
    return [eintrag for eintrag in eintraege(slugs, queue_path)
            if eintrag.get("befunde") or eintrag.get("fachbefunde")
            or "id" in eintrag or "text" in eintrag]
