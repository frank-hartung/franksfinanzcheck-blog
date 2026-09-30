#!/usr/bin/env python3
"""Vertrag für den Zustand der Affiliate-Integritäts-Wache.

Der Zustand wird vom Gate geschrieben und von mehreren Automationen gelesen.
Historische Funde (``content_problems``) und aktuell offene Restfunde dürfen
nicht verwechselt werden: Ein erfolgreich geheilter Fund gehört in die
Historie, aber niemals in ein Alarm-Ticket.

Dieses kleine, nebenwirkungsfreie Modul ist absichtlich die einzige Stelle für
Migration und Validierung. So können Gate, Watchdog und GitHub-Workflow nicht
wieder unterschiedliche Bedeutungen desselben JSON-Felds entwickeln.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

STATE_SCHEMA_VERSION = 2
EXIT_OK = 0
EXIT_CONTENT = 1
EXIT_TOOL = 2
VALID_EXIT_CODES = (EXIT_OK, EXIT_CONTENT, EXIT_TOOL)


def unresolved_problems(state: Mapping[str, Any]) -> list[Any]:
    """Gibt ausschließlich die noch offenen Affiliate-Funde zurück.

    Version-2-Zustände führen dafür zwingend ``unresolved_problems``. Die
    Liste enthält auch bei einem teilweise geheilten Lauf nur die nach der
    Heilung verbliebenen Artikel – nie die vollständige Fundhistorie. Für
    bereits versionierte Altzustände ohne dieses Feld gilt eine sichere,
    dokumentierte Migration:

    * grüner Alt-Lauf (``exit_code == 0``): ``content_problems`` ist eine
      Laufhistorie und daher keine Restmenge;
    * roter Alt-Lauf: ``content_problems`` bleibt die bestmögliche Restmenge.

    Eine ungültige v2-Form wird hier nicht stillschweigend als leer bewertet;
    ``state_contract_error`` macht sie für den Aufrufer fail-closed sichtbar.
    """
    explicit = state.get("unresolved_problems")
    if isinstance(explicit, list):
        return explicit
    if "unresolved_problems" in state:
        return []
    if state.get("exit_code") == EXIT_OK:
        return []
    legacy = state.get("content_problems")
    return legacy if isinstance(legacy, list) else []


def state_contract_error(state: Mapping[str, Any]) -> str | None:
    """Prüft die semantischen Invarianten eines v2-Zustands.

    Altzustände bleiben lesbar. Neue Zustände sind dagegen streng: ein
    widersprüchlicher oder beschädigter Beweis darf nie einen grünen Zustand
    vortäuschen.
    """
    version = state.get("state_schema_version")
    if version is None:
        # Vor v2 gab es kein kanonisches Restmengen-Feld. Die Migration in
        # ``unresolved_problems`` entscheidet bewusst anhand des Exit-Codes.
        return None
    if version != STATE_SCHEMA_VERSION:
        return (f"unbekannte state_schema_version {version!r} "
                f"(erwartet {STATE_SCHEMA_VERSION})")

    unresolved = state.get("unresolved_problems")
    if not isinstance(unresolved, list):
        return "unresolved_problems fehlt oder ist keine Liste"
    content = state.get("content_problems")
    if not isinstance(content, list):
        return "content_problems ist keine Liste"
    if any(not isinstance(problem, str) or not problem for problem in content):
        return "content_problems enthält keinen gültigen Artikel-Schlüssel"
    if any(not isinstance(problem, str) or not problem for problem in unresolved):
        return "unresolved_problems enthält keinen gültigen Artikel-Schlüssel"
    if len(set(content)) != len(content):
        return "content_problems enthält doppelte Artikel-Schlüssel"
    if len(set(unresolved)) != len(unresolved):
        return "unresolved_problems enthält doppelte Artikel-Schlüssel"
    exit_code = state.get("exit_code")
    if not isinstance(exit_code, int) or isinstance(exit_code, bool):
        return "exit_code ist keine Ganzzahl"
    if exit_code not in VALID_EXIT_CODES:
        return f"unbekannter exit_code {exit_code!r}"
    if exit_code == EXIT_OK and unresolved:
        return "grüner Lauf enthält trotzdem offene Restfunde"
    if exit_code == EXIT_CONTENT and not unresolved:
        return "roter Inhaltslauf enthält keine offene Restmenge"
    if exit_code == EXIT_TOOL and unresolved:
        return "Werkzeuglauf enthält trotzdem eine offene Content-Restmenge"
    # Die offene Restmenge kann nur aus der Audit-Spur dieses Laufs stammen.
    # Fehlt dieser Einschluss, könnte ein Fremd-/Tippfehler im State einen
    # Phantom-Alarm öffnen – die Klasse, die #446 dauerhaft ausschließt.
    foreign = sorted(set(unresolved) - set(content))
    if foreign:
        return ("unresolved_problems enthält keinen Fund der Laufhistorie: "
                + ", ".join(foreign[:3]))
    return None
