#!/usr/bin/env python3
"""abgeleitete_register.py – eine Ableitung folgt ihrer Quelle, im SELBEN Commit.

ANLASS (09.11.2026, Regressionsbefund nach #1137)
=================================================
`data/fachpruefung_register.yaml` ist keine Redaktionsdatei, sondern eine
ABLEITUNG aus dem Live-Bestand: Slug, Titel, Risikoklasse, Status und alle
Sätze mit Euro-/Prozentangaben. Die Gates im Deploy heilen laufend Inhalt –
Titel, Links, Formulierungen, Frontmatter. Niemand zog die Ableitung nach.
Ergebnis im Lauf `42609545452`:

    FAIL: test_register_ist_aktuell
    AssertionError: 1 != 0
    🛑 fachpruefung_register.yaml ist veraltet

Der Bestand war zu diesem Zeitpunkt **korrekt**; falsch war allein die Kopie.
Der Befund erreichte die Suite Wochen später – und kostete einen roten
Lieferketten-Job, weil ein abgeleitetes Artefakt als Handarbeit gepflegt wurde.

DIE REGEL
---------
    Eine Ableitung folgt ihrer Quelle – im selben Commit, maschinell.

Deshalb steht genau dort, wo die Gate-Heilungen committet werden, ein
deterministischer Nachzug (deploy.yml, vor „Gate-Heilungen committen“). Der
Schritt ist idempotent, ohne Netz und ohne KI: er ruft die Schreiber auf, die
das Haus für diese Register schon hat. Keine zweite Erzeugungslogik – die
Wahrheit über ein Register bleibt sein eigenes Skript.

WARUM EIN VERZEICHNIS UND KEIN EINZELAUFRUF
-------------------------------------------
Damit die Klasse nicht beim nächsten Register von vorn beginnt. Wer eine neue
Ableitung baut, trägt sie in `REGISTER` ein – dann gilt für sie automatisch:
Selbsttest, Nachzug im Commit-Pfad und ein Test, der die Einhängung prüft
(`scripts/tests/test_abgeleitete_register.py`).

CLI:
  python3 scripts/abgeleitete_register.py --check     # Exit 1, wenn veraltet
  python3 scripts/abgeleitete_register.py --fix       # nachziehen (schreiben)
  python3 scripts/abgeleitete_register.py --selftest  # Sabotage-Schutz
  python3 scripts/abgeleitete_register.py             # Bericht (Trockenlauf)
"""
from __future__ import annotations

import argparse
import importlib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


@dataclass(frozen=True)
class Register:
    """Ein abgeleitetes Artefakt und sein Schreiber."""

    pfad: str          # repo-relativ, wird committet
    skript: str        # repo-relativ, der EINZIGE Schreiber
    modul: str         # Importname des Schreibers (für den Selbsttest)
    zweck: str         # wofür die Ableitung gebraucht wird


REGISTER: Tuple[Register, ...] = (
    Register(
        pfad="data/fachpruefung_register.yaml",
        skript="scripts/fachpruefung_register.py",
        modul="fachpruefung_register",
        zweck="Prüfpfad für YMYL-Beiträge (Zahlenfundstellen, offener Prüfer)",
    ),
)


def _lauf(skript: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(ROOT / skript), *args],
        capture_output=True, text=True, check=False, cwd=str(ROOT),
    )


def _abweichung(erwartet: str, ist: str) -> List[str]:
    """Nennt die abweichenden Zeilen – eine Zahl allein hilft niemandem."""
    e, i = erwartet.splitlines(), ist.splitlines()
    zeilen: List[str] = []
    for nr in range(max(len(e), len(i))):
        links = e[nr] if nr < len(e) else "∅"
        rechts = i[nr] if nr < len(i) else "∅"
        if links != rechts:
            zeilen.append(f"Zeile {nr + 1}: erwartet {links[:110]!r} · gefunden {rechts[:110]!r}")
    return zeilen


def pruefen(register: Register) -> Tuple[bool, str]:
    """Delegiert an den Schreiber: SEIN `--check` ist die Wahrheit."""
    erg = _lauf(register.skript, "--check")
    text = (erg.stdout or erg.stderr or "").strip()
    return erg.returncode == 0, text


def nachziehen(register: Register) -> str:
    erg = _lauf(register.skript)
    return (erg.stdout or erg.stderr or "").strip()


def bericht() -> int:
    for register in REGISTER:
        ok, text = pruefen(register)
        print(f"{'✅' if ok else '🛑'} {register.pfad} – {register.zweck}")
        if text:
            print(f"   {text}")
    return 0


def selftest() -> int:
    """Sabotage-Schutz: Das Verzeichnis muss stimmen UND Drift erkennbar sein."""
    fehler: List[str] = []

    if not REGISTER:
        fehler.append("leeres Verzeichnis – dann prüft der Wächter nichts")
    if len({r.pfad for r in REGISTER}) != len(REGISTER):
        fehler.append("doppelter Register-Pfad im Verzeichnis")

    for register in REGISTER:
        if not (ROOT / register.skript).is_file():
            fehler.append(f"{register.skript}: Schreiber fehlt")
            continue
        if not (ROOT / register.pfad).is_file():
            fehler.append(f"{register.pfad}: Register fehlt (nicht erzeugt?)")
        try:
            modul = importlib.import_module(register.modul)
        except Exception as exc:  # noqa: BLE001 – jeder Importfehler ist ein Befund
            fehler.append(f"{register.modul}: nicht importierbar ({exc})")
            continue
        if not (hasattr(modul, "render") and hasattr(modul, "collect")):
            fehler.append(f"{register.modul}: render/collect fehlen – "
                          "der Nachzug wäre blind")
            continue
        # Drift-Erkennung selbst beweisen: zwei Fassungen, ein Unterschied.
        erwartet = modul.render(modul.collect())
        getampert = erwartet.replace("anzahl:", "anzahl :", 1)
        if getampert == erwartet:
            fehler.append(f"{register.modul}: Sabotage hat nichts geändert (Probe taugt nicht)")
        elif not _abweichung(erwartet, getampert):
            fehler.append(f"{register.modul}: Drift wird nicht erkannt")
        elif _abweichung(erwartet, erwartet):
            fehler.append(f"{register.modul}: identische Fassungen gelten als Drift")

    if fehler:
        for f in fehler:
            print(f"✗ {f}")
        return 1
    print(f"✓ abgeleitete Register – {len(REGISTER)} Eintrag/Einträge, "
          "Schreiber vorhanden, Drift-Erkennung geprüft")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Abgeleitete Register prüfen und nachziehen "
                    "(Ableitung folgt ihrer Quelle, im selben Commit).")
    modus = ap.add_mutually_exclusive_group()
    modus.add_argument("--check", action="store_true",
                       help="Exit 1, wenn ein Register veraltet ist")
    modus.add_argument("--fix", action="store_true",
                       help="Register deterministisch neu erzeugen")
    modus.add_argument("--selftest", action="store_true",
                       help="Sabotage-Schutz für CI")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    if args.fix:
        for register in REGISTER:
            print(nachziehen(register))
        ok = all(pruefen(register)[0] for register in REGISTER)
        if not ok:
            print("::error title=Abgeleitete Register::Nach dem Nachzug ist ein "
                  "Register weiterhin veraltet – der Schreiber ist defekt.")
            return 1
        print(f"✅ {len(REGISTER)} abgeleitete(s) Register nachgezogen und geprüft")
        return 0

    if args.check:
        veraltet = [(register, text) for register in REGISTER
                    for ok, text in [pruefen(register)] if not ok]
        for register, text in veraltet:
            print(f"::error title=Abgeleitete Register::{register.pfad} ist "
                  f"veraltet – python3 {register.skript}%0A{text.replace('%', '%25')}")
        if veraltet:
            return 1
        print(f"✅ Abgeleitete Register aktuell ({len(REGISTER)} geprüft)")
        return 0

    return bericht()


if __name__ == "__main__":
    sys.exit(main())
