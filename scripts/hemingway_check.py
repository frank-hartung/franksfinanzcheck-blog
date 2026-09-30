#!/usr/bin/env python3
"""Kostenloser Hemingway-Editor-Begleiter für die Redaktion.

Der kostenlose Hemingway Editor ist ein browserbasiertes Lektoratstool und
bietet keine offizielle CI-API. Dieser dünne Adapter macht deshalb dieselben
redaktionellen Signale auch im Repository und in GitHub Actions nutzbar:
Satzlänge, Flesch-Amstad, lange Wörter, Schachtelsätze, Absätze und Passiv.

Die eigentliche Auswertung bleibt in ``readability_check.py`` die gemeinsame
SSOT für bestehende Publish-Gates. Dieser Einstieg ist bewusst frei von
Accounts, API-Keys, Netzaufrufen und automatischen Textumschreibungen.

Für die manuelle Schlussrunde:
https://hemingwayapp.com/

Nutzung:
  python3 scripts/hemingway_check.py
  python3 scripts/hemingway_check.py --file content/posts/.../index.md
  python3 scripts/hemingway_check.py --new-only
  python3 scripts/hemingway_check.py --gate-bestand --report HEMINGWAY-REPORT.md
  python3 scripts/hemingway_check.py --json
  python3 scripts/hemingway_check.py --selftest
"""
from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

# Beim direkten Aufruf liegt scripts/ bereits in sys.path. Der Fallback macht
# den Adapter auch bei ``python -m`` und aus Test-Runnern heraus robust.
try:
    import readability_check as _engine
except ImportError:  # pragma: no cover - nur für ungewöhnliche Aufrufer
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import readability_check as _engine

TOOL_NAME = "Hemingway Editor"
TOOL_URL = "https://hemingwayapp.com/"


def main(argv: list[str] | None = None) -> int:
    """Führt die bestehende, deterministische Lesbarkeits-SSOT aus.

    Der Adapter hält die vorhandenen CLI-Optionen und Exit-Codes kompatibel,
    kennzeichnet die Ausgabe aber eindeutig als Hemingway-Lauf. Report-Dateien
    werden ebenfalls umbenannt, damit im Workflow keine alte Produktbezeich-
    nung stehen bleibt.
    """
    forwarded = list(sys.argv[1:] if argv is None else argv)
    old_argv = sys.argv
    output = io.StringIO()
    status = 0
    sys.argv = [str(Path(__file__))] + forwarded
    try:
        with contextlib.redirect_stdout(output):
            _engine.main()
    except SystemExit as exc:
        status = int(exc.code or 0)
    finally:
        sys.argv = old_argv

    text = output.getvalue()
    # Der JSON-Modus bleibt maschinenlesbar; nur freie Status-/Hilfstexte
    # erhalten die neue Werkzeugbezeichnung.
    if "--json" not in forwarded:
        text = (text.replace("readability_check", "hemingway_check")
                    .replace("Lesbarkeits-Wache", "Hemingway-Wache")
                    .replace("Lesbarkeits-Gate", "Hemingway-Gate")
                    .replace("Lesbarkeits-Audit", "Hemingway-Lesbarkeitscheck"))
    print(text, end="")

    report_arg = None
    if "--report" in forwarded:
        index = forwarded.index("--report") + 1
        if index < len(forwarded):
            report_arg = Path(forwarded[index])
    if report_arg and report_arg.exists():
        report = report_arg.read_text(encoding="utf-8")
        report = (report.replace("Lesbarkeits-Wache", "Hemingway-Wache")
                        .replace("readability_check", "hemingway_check"))
        report_arg.write_text(report, encoding="utf-8")

    return status


if __name__ == "__main__":
    raise SystemExit(main())
