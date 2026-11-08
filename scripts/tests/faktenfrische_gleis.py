"""Gemeinsame Prüfregel der Befund-Akten: Arbeitsliste ist kein Befund.

Drei Aktentests (#763, #823, #911) prüften bisher, ob ihre Seiten überhaupt
noch in `data/faktenfrische_queue.json` stehen. Das war am Tag der Heilung
wahr und danach falsch: die Queue ist eine **Arbeitsliste**, kein
Befundregister. Sobald die Frist einer Seite in den Vorlauf rückt
(seit 06.11.2026: 14 Tage), steht sie dort wieder – mit dem Grund „frisch
geprüft vor N Tagen“, ohne einen einzigen offenen Befund. Am 07.11.2026
wurden deshalb zwei dieser Prüfungen rot, ohne dass ein Sachfehler
zurückgekehrt wäre (Frist 14.11. minus 14 Tage Vorlauf = 31.10.).

Geprüft wird jetzt, was gemeint war: **offene Befunde** derselben Seiten,
ermittelt über das Befund-Ledger (`faktenfrische_befund_ledger`) – dieselbe
Quelle, aus der Ticket und Redaktion arbeiten. Ein Lauf, der die Fehler
erneut meldet, schreibt sie in `fachbefunde` und macht die Akte weiter rot.

Kein Testmodul: der Dateiname beginnt bewusst nicht mit `test_`.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "data" / "faktenfrische_queue.json"

sys.path.insert(0, str(ROOT / "scripts"))


def kern(slug: object) -> str:
    """Slug ohne Datumspräfix – die Identität, die eine Akte meint."""
    return re.sub(r"^\d{4}-\d{2}-\d{2}-", "", str(slug or ""))


def offene_befunde(slugs, queue_path: Path | None = None) -> list[dict]:
    """Offene Befunde zu genau diesen Seiten (leer = Befund geschlossen)."""
    import faktenfrische_befund_ledger as ledger

    gesucht = {kern(s) for s in slugs}
    pfad = Path(queue_path) if queue_path is not None else QUEUE
    return [befund for befund in ledger.offene_befunde(pfad)
            if kern(befund.get("slug")) in gesucht]


def eintraege(slugs, queue_path: Path | None = None) -> list[dict]:
    """Arbeitslisten-Einträge dieser Seiten – erlaubt, aber nur als Termin."""
    import json

    gesucht = {kern(s) for s in slugs}
    pfad = Path(queue_path) if queue_path is not None else QUEUE
    try:
        queue = json.loads(pfad.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    return [eintrag for eintrag in queue.get("offen", [])
            if kern(eintrag.get("slug")) in gesucht]


def arbeitsliste_traegt_befunde(slugs, queue_path: Path | None = None) -> list[dict]:
    """Einträge, die einen Befund mitschleppen (muss leer sein)."""
    return [eintrag for eintrag in eintraege(slugs, queue_path)
            if eintrag.get("befunde") or eintrag.get("fachbefunde")]
