#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ci_tests.py – ein Testlauf, der seinen roten Test beim Namen nennt.

WARUM (08.11.2026, #1137 / #1129):
----------------------------------
Der Deploy starb am Schritt „KI-Transparenz – Text, Bild und Provenienz
testen“. Die einzige Auskunft, die der Lauf noch hergab, war

    Process completed with exit code 1.

Damit war die Ursache aus dem Lauf NICHT lesbar: Welcher der sechs
Testmodule rot war, stand nur im Schritt-Log – und ein Log ist flüchtig
(Aufbewahrungsfrist, Sandbox ohne Log-Zugriff, abgebrochener Download).
Die Annotation an der Prüfung bleibt erhalten; sie ist der einzige Kanal,
der die Ursache mit dem Befund zusammen ausliefert.

Dieselbe Lücke war vorher schon zweimal da (Code-Regression, Uhr-Probe).
Dort stand die Auswertung als kopierter Python-Block IN der Workflow-Datei –
dreimal derselbe Code, dreimal die Chance, ihn unterschiedlich zu reparieren.
Hier ist es EINE Umsetzung, die jeder Schritt aufruft:

    python3 scripts/ci_tests.py --titel "KI-Transparenz" -- \
        python3 -m unittest scripts.tests.test_ki_transparenz_render -v

Der Wächter `workflow_vertrag_wache.py` (Regel V7) prüft, dass in den
Lieferketten-Workflows kein Testlauf mehr an dieser Auswertung vorbeiläuft.

VERHALTEN
---------
* Der Befehl läuft mit geerbter Umgebung (`PATH` mit Hugo bleibt also
  gültig), Ausgabe wird mitgeschrieben und angezeigt.
* Exit-Code des Befehls wird unverändert durchgereicht – die Auswertung
  macht ein rotes Gate niemals grün.
* Jeder `FAIL:`/`ERROR:`-Block wird als `::error`-Annotation ausgegeben
  (Name, Ort, Behauptung) – höchstens `--max` Stück, damit die
  Kontrollfläche lesbar bleibt.
* Gibt es einen Fehlschlag OHNE unittest-Format (Absturz im Setup,
  Import-Fehler, fehlendes Binary), wird die Log-Spitze als Annotation
  ausgegeben. „Exit 1 ohne Namen“ darf nicht mehr vorkommen.

Aufruf:
  python3 scripts/ci_tests.py --titel X --log /tmp/x.log -- python3 -m unittest …
  python3 scripts/ci_tests.py --selftest
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Sequence

# unittest schreibt Fehlschläge als Block:
#   FAIL: test_name (modul.Klasse.test_name)
#   ----------------------------------------------------------------------
#   Traceback … / AssertionError: …
# Der Block endet an der nächsten Trennlinie oder an „Ran N tests“.
MUSTER = re.compile(
    r"^(FAIL|ERROR): (\S+) \((.*?)\)\n-+\n(.*?)"
    r"(?=\n(?:={20,}|-{20,}|\Z|Ran \d+ tests))",
    re.S | re.M,
)

MAX_ZEICHEN = 1500


def ent(text: str, grenze: int = MAX_ZEICHEN) -> str:
    """GitHub-Annotationen maskieren `%`, Zeilenumbrüche und CR."""
    return (text.replace("%", "%25").replace("\r", "").replace("\n", "%0A"))[:grenze]


def annotationen(log: str, titel: str, hoechstens: int = 10) -> List[str]:
    """Eine `::error`-Zeile je rotem Test (Name, Ort, Behauptung)."""
    zeilen: List[str] = []
    for _art, name, ort, rumpf in list(MUSTER.findall(log))[:hoechstens]:
        zeilen.append(
            f"::error title={titel}::{ent(name)} ({ent(ort, 300)})"
            f"%0A{ent(rumpf)}"
        )
    return zeilen


def notfall_annotation(log: str, titel: str, rc: int) -> str:
    """Fehlschlag ohne unittest-Format: die Log-Spitze ist die Diagnose."""
    rest = log.strip().splitlines()
    rumpf = "\n".join(rest[-20:]) if rest else "(keine Ausgabe)"
    return f"::error title={titel}::Exit {rc} ohne Testnamen%0A{ent(rumpf)}"


def laufen(befehl: Sequence[str]) -> subprocess.CompletedProcess:
    """Befehl mit geerbter Umgebung, stderr in stdout, kein Pufferverlust."""
    return subprocess.run(  # noqa: S603 – Befehl kommt aus dem Workflow, nicht aus Nutzereingabe
        list(befehl),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        env=os.environ.copy(),
        check=False,
    )


def auswerten(ergebnis: subprocess.CompletedProcess, titel: str,
              logdatei: Path, zeigen: int, hoechstens: int) -> int:
    log = ergebnis.stdout or ""
    try:
        logdatei.write_text(log, encoding="utf-8")
    except OSError as fehler:  # Logdatei ist Komfort, nicht Bedingung
        print(f"⚠ Logdatei {logdatei} nicht schreibbar: {fehler}")

    rest = log.splitlines()
    if rest:
        print(f"… ({max(0, len(rest) - zeigen)} frühere Zeilen) " + str(logdatei))
        print("\n".join(rest[-zeigen:]))

    rc = ergebnis.returncode
    if rc == 0:
        return 0

    zeilen = annotationen(log, titel, hoechstens)
    if not zeilen:
        zeilen = [notfall_annotation(log, titel, rc)]
    for zeile in zeilen:
        print(zeile)
    print(f"🛑 {titel}: {len(zeilen)} Annotation(en), Exit {rc}")
    return rc


def selftest() -> int:
    """Prüft Maskierung, Namensfindung und den Notfallpfad – ohne echtes Netz."""
    fehler: List[str] = []
    probe = (
        "FAIL: test_alpha (pkg.mod.Klasse.test_alpha)\n"
        "----------------------------------------------------------------------\n"
        "Traceback (most recent call last):\n"
        '  File "x.py", line 1\n'
        "AssertionError: 49 not greater than or equal to 50 – 100% rot\n"
        "\n"
        "======================================================================\n"
        "ERROR: setUpClass (pkg.mod.Andere)\n"
        "----------------------------------------------------------------------\n"
        "OSError: hugo fehlt\n"
        "\n"
        "----------------------------------------------------------------------\n"
        "Ran 2 tests\n"
    )
    zeilen = annotationen(probe, "Probe")
    if len(zeilen) != 2:
        fehler.append(f"erwartet 2 Annotationen, erhalten {len(zeilen)}")
    if not any("Probe::test_alpha" in z for z in zeilen):
        fehler.append("der rote Test wird nicht namentlich genannt")
    if not any("setUpClass" in z for z in zeilen):
        fehler.append("ERROR:-Block (Setup-Absturz) fehlt")
    if not any("100%25 rot" in z for z in zeilen):
        fehler.append("Prozentzeichen wird nicht maskiert")
    if any("\n" in z for z in zeilen):
        fehler.append("Annotation enthält echten Zeilenumbruch (bricht die Zeile)")
    if len(annotationen(probe, "Probe", hoechstens=1)) != 1:
        fehler.append("--max wird nicht eingehalten")

    notfall = notfall_annotation("Traceback\nModuleNotFoundError: x\n", "Probe2", 7)
    if "Exit 7" not in notfall or "ModuleNotFoundError" not in notfall:
        fehler.append("Notfallpfad nennt weder Exit-Code noch Log-Spitze")

    if len(ent("a" * (MAX_ZEICHEN + 50))) != MAX_ZEICHEN:
        fehler.append("Annotation wird nicht auf die GitHub-Grenze gekürzt")

    if fehler:
        for f in fehler:
            print(f"✗ {f}")
        return 1
    print(f"✓ ci_tests – {len(zeilen)} Annotationen aus 2 Fehlschlägen, Maskierung ok")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return selftest()

    if "--" in argv:
        trenner = argv.index("--")
        eigen, befehl = argv[:trenner], argv[trenner + 1:]
    else:
        eigen, befehl = argv, []

    p = argparse.ArgumentParser(
        prog="ci_tests.py",
        description="Testlauf mit Annotation je rotem Test (Exit-Code bleibt).")
    p.add_argument("--titel", required=True,
                   help="Präfix der Annotation, z. B. der Schrittname")
    p.add_argument("--log", default=None, help="Logdatei (Standard: temporär)")
    p.add_argument("--zeigen", type=int, default=120,
                   help="wie viele Schlusszeilen im Schritt-Log erscheinen")
    p.add_argument("--max", type=int, default=10, dest="hoechstens",
                   help="höchstens so viele Annotationen")
    args = p.parse_args(eigen)

    if not befehl:
        p.error("kein Befehl – Aufruf: … -- python3 -m unittest …")

    logdatei = Path(args.log) if args.log else Path(tempfile.gettempdir()) / "ci-tests.log"
    return auswerten(laufen(befehl), args.titel, logdatei, args.zeigen, args.hoechstens)


if __name__ == "__main__":
    sys.exit(main())
