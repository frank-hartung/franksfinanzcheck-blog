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

``--selftest`` prüft den ADAPTER (Durchreichen, Exit-Code, Umbenennung,
JSON-Unversehrtheit) UND lässt zusätzlich den Selbsttest der Engine laufen.
Bis zum 03.10.2026 tat es das NICHT: Es reichte die Flagge nur weiter und
druckte die grüne Zeile der Engine – nachdem es darin „readability_check"
durch „hemingway_check" ersetzt hatte. Das Häkchen trug also den Namen eines
Moduls, von dem keine einzige Zeile geprüft worden war. Siehe _selftest().
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
    # Eigener Selbsttest statt Weiterreichen: Sonst trüge das grüne Häkchen
    # den Namen dieses Moduls, ohne eine Zeile davon geprüft zu haben.
    if "--selftest" in forwarded:
        return _selftest()
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


# ======================================================================
#  Selbsttest
#  ---------------------------------------------------------------------
#  WARUM ER EIGENSTÄNDIG SEIN MUSS (Befund 03.10.2026):
#  Vorher reichte `--selftest` die Flagge nur an die Engine weiter. Deren
#  grüne Zeile lautet „✅ readability_check --selftest OK …"; der Adapter
#  ersetzte darin den Modulnamen und gab sie als EIGENES Urteil aus:
#
#      ✅ hemingway_check --selftest OK (R6-Schwellen + …)
#
#  Dieses Häkchen war durch Suchen-und-Ersetzen hergestellt. Geprüft war
#  keine einzige Zeile dieses Moduls – und `test_hemingway_check.py`
#  bestätigte genau diese gefälschte Zeichenkette. Ein grünes Signal, das
#  seinen eigenen Namen erfindet, ist schlimmer als ein fehlendes: Es
#  verbraucht Vertrauen, ohne etwas zu leisten.
#
#  Der Adapter hat vier eigene Versprechen, und nur die prüft dieser Test:
#    A1  Argumente kommen unverändert bei der Engine an.
#    A2  Der Exit-Code der Engine wird durchgereicht, nicht geschluckt.
#    A3  Im Textmodus wird die Produktbezeichnung umbenannt.
#    A4  Im JSON-Modus wird NICHT umbenannt – die Ausgabe bleibt parsebar.
#    A5  Eine --report-Datei wird nachgezogen.
#    A6  Ein roter Lauf darf nie als grün erscheinen (Fälschungsprobe).
#    A7  Die Engine hat ein echtes --selftest – sonst wäre Weiterreichen
#        eine Lüge und der Aufruf startete das scharfe Gate (Klasse
#        publish_gate.py, 18.09.2026).
# ======================================================================

def _mit_attrappe(ausgabe: str, code: int = 0):
    """Kontextmanager: ersetzt die Engine durch eine Attrappe.

    Gibt die Liste zurück, in der die Attrappe die gesehenen Argumente
    ablegt – damit „wurde durchgereicht" belegbar ist statt behauptet.
    """
    import contextlib as _ctx

    @_ctx.contextmanager
    def _lauf():
        gesehen: list[str] = []

        def attrappe():
            gesehen.extend(sys.argv[1:])
            print(ausgabe, end="")
            if code:
                raise SystemExit(code)

        echt = _engine.main
        _engine.main = attrappe
        try:
            yield gesehen
        finally:
            _engine.main = echt

    return _lauf()


def _fang(argv: list[str]) -> tuple[int, str]:
    """Führt main(argv) aus und fängt Rückgabewert und Ausgabe ein."""
    puffer = io.StringIO()
    with contextlib.redirect_stdout(puffer):
        status = main(argv)
    return status, puffer.getvalue()


def _selftest() -> int:
    import json as _json
    import tempfile

    fehler: list[str] = []

    # ---- A7: Die Engine muss die Flagge WIRKLICH auswerten --------------
    # Täte sie es nicht, startete jeder --selftest-Aufruf den scharfen
    # Bestands-Gate-Lauf über alle Artikel. Genau diese Verwechslung stufte
    # am 18.09.2026 beinahe einen Live-Artikel auf draft herab.
    quelle = Path(_engine.__file__).read_text(encoding="utf-8")
    if "'--selftest'" not in quelle and '"--selftest"' not in quelle:
        fehler.append("A7: readability_check wertet --selftest nicht aus – das "
                      "Weiterreichen würde den scharfen Gate-Lauf starten.")

    # ---- A1 + A3: Durchreichen und Umbenennen ---------------------------
    with _mit_attrappe("Lesbarkeits-Audit: 3 Artikel\nLesbarkeits-Wache aktiv\n") as gesehen:
        status, text = _fang(["--new-only", "--file", "x.md"])
    if gesehen != ["--new-only", "--file", "x.md"]:
        fehler.append(f"A1: Argumente kamen verändert an: {gesehen}")
    if status != 0:
        fehler.append(f"A1: grüner Lauf endet mit {status}")
    if "Hemingway-Lesbarkeitscheck" not in text or "Hemingway-Wache" not in text:
        fehler.append(f"A3: Umbenennung fehlt: {text!r}")
    if "Lesbarkeits-Audit" in text or "Lesbarkeits-Wache" in text:
        fehler.append("A3: alte Produktbezeichnung steht noch in der Ausgabe")

    # ---- A2: Exit-Codes werden durchgereicht ----------------------------
    for code in (1, 2, 7):
        with _mit_attrappe("egal\n", code=code):
            status, _ = _fang([])
        if status != code:
            fehler.append(f"A2: Exit {code} der Engine kam als {status} an – ein "
                          "Gate, dessen Veto unterwegs verlorengeht, ist kein Gate.")

    # ---- A4: JSON bleibt unangetastet und parsebar ----------------------
    roh = _json.dumps({"werkzeug": "readability_check",
                       "befund": "Lesbarkeits-Wache", "flesch": 61.5})
    with _mit_attrappe(roh):
        status, text = _fang(["--json"])
    try:
        daten = _json.loads(text)
    except ValueError as exc:
        daten = None
        fehler.append(f"A4: JSON-Ausgabe ist nicht mehr parsebar ({exc})")
    if daten is not None and daten.get("werkzeug") != "readability_check":
        fehler.append("A4: Im JSON-Modus wurde umbenannt – maschinenlesbare "
                      "Ausgabe darf nicht kosmetisch verändert werden.")

    # ---- A5: Report-Datei wird nachgezogen ------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        bericht = Path(tmp) / "HEMINGWAY-REPORT.md"
        bericht.write_text("# Lesbarkeits-Wache\nQuelle: readability_check\n",
                           encoding="utf-8")
        with _mit_attrappe("fertig\n"):
            _fang(["--report", str(bericht)])
        inhalt = bericht.read_text(encoding="utf-8")
        if "Lesbarkeits-Wache" in inhalt or "readability_check" in inhalt:
            fehler.append("A5: Report behält die alte Produktbezeichnung")
        if "Hemingway-Wache" not in inhalt:
            fehler.append("A5: Report wurde nicht umbenannt")

    # ---- A6: FÄLSCHUNGSPROBE -------------------------------------------
    # Die Engine meldet rot UND druckt trotzdem ihre Grün-Zeile. Der Adapter
    # darf daraus kein grünes Urteil basteln. Diese Probe ist der Grund für
    # diese ganze Funktion.
    with _mit_attrappe("✅ readability_check --selftest OK (alles bestens)\n", code=1):
        status, text = _fang(["--selftest-weiterreichen-probe"])
    if status == 0:
        fehler.append("A6: Roter Lauf mit grün aussehendem Text wurde als Erfolg "
                      "gewertet – genau die Fälschung vom 03.10.2026.")

    # ---- Die Engine-Prüfung bleibt erhalten, aber unter eigenem Namen ----
    engine_puffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(engine_puffer):
            engine_status = _engine._selftest()
    except Exception as exc:  # pragma: no cover - Engine kaputt
        engine_status = 1
        fehler.append(f"Engine-Selbsttest brach ab: {exc}")
    if engine_status != 0:
        fehler.append("Engine-Selbsttest (readability_check) ist rot: "
                      + engine_puffer.getvalue().strip())

    if fehler:
        for f in fehler:
            print("❌ " + f)
        return 1
    print("✅ hemingway_check --selftest OK (A1–A7: Durchreichen, Exit-Codes, "
          "Umbenennung, JSON unangetastet, Report, Fälschungsprobe) "
          "+ Engine-Selbsttest readability_check grün.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
