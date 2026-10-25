#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
#  SKRIPT-SYNTAX-WACHE – „kompiliert, was auf main liegt?"
#  ------------------------------------------------------------
#  WARUM ES DIESE WACHE GIBT (Bot-Watchdog #864, 25.10.2026)
#
#  Am 25.10.2026 landete `scripts/redaktions_standard.py` mit einem
#  IndentationError auf main (Zeile 424). Er entstand nicht beim
#  Schreiben, sondern beim ZUSAMMENFÜHREN: Der Squash-Merge von
#  PR #869 traf eine zwischenzeitlich gewanderte `main`; Kopf und
#  Rumpf derselben Funktion kamen aus zwei verschiedenen Fassungen.
#  Zurück blieben ein doppelter `if`-Block und zwei verwaiste
#  Fortsetzungszeilen.
#
#  Vier weitere Commits (Scorecard, Social, Governance, Gate) gingen
#  danach ohne Beanstandung über diesen Stand – weil KEINE Stelle im
#  Repo den *liegenden* Stand kompiliert. Die PR-Prüfung sieht den
#  PR-Stand, der Unit-Test sieht die Module, die er importiert, der
#  Hugo-Build sieht Python überhaupt nicht, und `bot_preflight.py`
#  läuft nur in der Content-Engine.
#
#  Genau diese Lücke schließt diese Wache: Sie liest ALLE Skripte,
#  wie sie im Arbeitsbaum liegen, und kompiliert sie – ohne sie
#  auszuführen, ohne Netz, ohne Import, in unter einer Sekunde.
#  Sie ist die EINE Quelle der Wahrheit für „Python im Repo ist
#  gültig"; der Bot-Watchdog, der Push-Lauf und der Syntax-Heiler
#  fragen sie, statt die Regel dreimal zu formulieren.
#
#  WAS SIE BEWUSST NICHT TUT
#  -------------------------
#    · Sie führt nichts aus (kein Import des Prüflings, keine
#      Modell-/Netzaufrufe, kein Schreiben von `__pycache__`).
#    · Sie urteilt NICHT über Namen, Aufrufe oder halbe Fassungen –
#      das ist `wachen_vertrag.py` (W1–W4/W9). Hier geht es nur um
#      die unterste Stufe: Ist der Text überhaupt Python?
#    · Ihr eigener Selbsttest prüft DEN DETEKTOR (erkennt er einen
#      Fehler, schweigt er bei gutem Code, überspringt er `__pycache__`) –
#      nicht den Repo-Stand. Ein Detektor, dessen Selbsttest am
#      kaputten Prüfling scheitert, wäre in genau dem Moment blind,
#      für den er gebaut ist (#864).
#
#  NUTZUNG
#    python3 scripts/skript_syntax_wache.py            # prüfen (Exit 1 bei Fund)
#    python3 scripts/skript_syntax_wache.py --json     # Maschinenausgabe
#    python3 scripts/skript_syntax_wache.py --md       # Markdown für Lauf-Summary
#    python3 scripts/skript_syntax_wache.py --selftest # Sabotage-Schutz (Exit 2 bei Defekt)
#
#  EXIT: 0 = alles kompiliert · 1 = mindestens ein Fund · 2 = Wache defekt
# ============================================================
"""Eine Quelle der Wahrheit: Jedes Python-Skript im Repo kompiliert."""

from __future__ import annotations

import argparse
import json
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path

BLOG_DIR = Path(__file__).resolve().parent.parent

# Wo Skripte liegen. `scripts/tests` gehört dazu: Ein kaputter Test
# blockiert die ganze Suite und damit jeden Nachweis über den Code.
SUCHWURZELN = ("scripts",)

# Verzeichnisse, die kein Quelltext sind. `__pycache__` enthält Bytes,
# `public` den gebauten Stand, `node_modules` fremden Code.
UEBERSPRUNGEN = {"__pycache__", ".git", ".venv", "venv", "node_modules",
                 "public", "build", "dist", "out", "coverage"}

# Für die Ausgabe: eine Zeile, damit Tickets und Logs lesbar bleiben.
MAX_QUELLE = 160


@dataclass(frozen=True)
class Syntaxfehler:
    """Ein belegter Syntaxfehler – Datei, Zeile, Art, Quellzeile."""

    datei: str          # repo-relativ, z. B. "scripts/redaktions_standard.py"
    zeile: int
    art: str            # z. B. "IndentationError: unexpected indent"
    quelle: str = ""    # die betroffene Quellzeile (gekürzt)

    def text(self) -> str:
        ort = f"{self.datei}:{self.zeile}"
        return f"{ort}: {self.art}"

    def as_dict(self) -> dict:
        return {"datei": self.datei, "zeile": self.zeile,
                "art": self.art, "quelle": self.quelle}


def dateien(root: Path | str = BLOG_DIR) -> list[Path]:
    """Alle Python-Skripte, die im Repo liegen – deterministisch sortiert."""
    root = Path(root)
    gefunden: list[Path] = []
    for wurzel in SUCHWURZELN:
        basis = root / wurzel
        if not basis.is_dir():
            continue
        for pfad in basis.rglob("*.py"):
            if any(teil in UEBERSPRUNGEN for teil in pfad.parts):
                continue
            if pfad.is_file():
                gefunden.append(pfad)
    return sorted(set(gefunden))


def quelle_lesen(pfad: Path | str) -> str:
    """Quelltext mit korrekter Kodierung lesen (PEP 263, BOM)."""
    with tokenize.open(str(pfad)) as fh:
        return fh.read()


def pruefe_quelle(text: str, name: str = "<speicher>") -> Syntaxfehler | None:
    """Kompiliert Text im Speicher. Schreibt KEIN `__pycache__`.

    Der Rückgabewert nennt Zeile, Art und Quellzeile – py_compile nannte
    bisher nur „Sorry: IndentationError … (redaktions_standard.py, line 424)"
    und zwang jeden Leser, den Dateinamen selbst zu suchen (#864).
    """
    try:
        compile(text, name, "exec")
    except SyntaxError as exc:
        zeile = int(exc.lineno or 0)
        art = f"{type(exc).__name__}: {exc.msg}"
        quelle = (exc.text or "").strip()[:MAX_QUELLE]
        return Syntaxfehler(datei=name, zeile=zeile, art=art, quelle=quelle)
    except (ValueError, UnicodeError) as exc:      # z. B. Nullbytes
        return Syntaxfehler(datei=name, zeile=0,
                            art=f"{type(exc).__name__}: {exc}"[:MAX_QUELLE])
    return None


def pruefe_datei(pfad: Path | str, root: Path | str = BLOG_DIR) -> Syntaxfehler | None:
    """Prüft eine Datei und meldet den Befund repo-relativ."""
    pfad = Path(pfad)
    root = Path(root)
    try:
        relativ = pfad.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        relativ = pfad.as_posix()
    try:
        text = quelle_lesen(pfad)
    except (OSError, SyntaxError, UnicodeError) as exc:
        return Syntaxfehler(datei=relativ, zeile=0,
                            art=f"{type(exc).__name__}: {exc}"[:MAX_QUELLE])
    return pruefe_quelle(text, relativ)


def finde(root: Path | str = BLOG_DIR) -> list[Syntaxfehler]:
    """Alle Syntaxfehler im Repo (leer = grün)."""
    fehler: list[Syntaxfehler] = []
    for pfad in dateien(root):
        treffer = pruefe_datei(pfad, root)
        if treffer is not None:
            fehler.append(treffer)
    return fehler


def betroffene_dateien(fehler: list[Syntaxfehler]) -> list[str]:
    """Eindeutige Dateipfade in Melde-Reihenfolge."""
    gesehen: list[str] = []
    for f in fehler:
        if f.datei not in gesehen:
            gesehen.append(f.datei)
    return gesehen


def bericht(fehler: list[Syntaxfehler], geprueft: int | None = None) -> str:
    """Menschenlesbare Zusammenfassung (eine Zeile je Fund)."""
    if not fehler:
        zusatz = f" ({geprueft} Dateien)" if geprueft is not None else ""
        return f"✅ Skript-Syntax grün{zusatz}"
    kopf = (f"🛑 Skript-Syntax: {len(fehler)} Fund(e) in "
            f"{len(betroffene_dateien(fehler))} Datei(en)")
    return "\n".join([kopf] + [f"  - {f.text()}" for f in fehler])


def markdown(fehler: list[Syntaxfehler], geprueft: int) -> str:
    """Kurzfassung für `$GITHUB_STEP_SUMMARY`."""
    if not fehler:
        return f"- ✅ **Skript-Syntax grün** – {geprueft} Python-Dateien kompiliert.\n"
    zeilen = [f"- 🛑 **Skript-Syntax: {len(fehler)} Fund(e)** – "
              f"{geprueft} Python-Dateien geprüft.", ""]
    zeilen += [f"  - `{f.datei}:{f.zeile}` – {f.art}" for f in fehler]
    return "\n".join(zeilen) + "\n"


# ------------------------------------------------------------
#  SELBSTTEST – der Detektor, nicht der Prüfling
# ------------------------------------------------------------
def selftest() -> int:
    """Beweist die Wirkung des Detektors an Wegwerf-Dateien.

    Der Repo-Stand wird hier absichtlich NICHT bewertet: Während eines
    Ausfalls ist er rot, und ein roter Selbsttest hätte den Melder in
    genau dem Moment abgeschaltet, in dem er gebraucht wird (#864).
    """
    import tempfile

    fehler: list[str] = []

    def probe(name: str, bedingung: bool, hinweis: str = "") -> None:
        if not bedingung:
            fehler.append(f"{name}{(': ' + hinweis) if hinweis else ''}")

    gute = "def addiere(a, b):\n    return a + b\n"
    kaputte = "def addiere(a, b):\n    return a + b\n        return 0\n"

    probe("guter Code bleibt still", pruefe_quelle(gute) is None,
          "ein fehlerfreier Text wurde als Befund gemeldet")

    fund = pruefe_quelle(kaputte, "probe.py")
    probe("kaputter Code wird erkannt", fund is not None)
    if fund is not None:
        probe("Fehlerzeile stimmt", fund.zeile == 3, f"Zeile {fund.zeile} statt 3")
        probe("Fehlerart ist benannt", "IndentationError" in fund.art, fund.art)
        probe("Quellzeile wird mitgeliefert", "return 0" in fund.quelle,
              "ohne Quellzeile ist der Fund im Log nicht wiederzuerkennen")

    # Doppelpunkt-Fehler (die häufigste Merge-Ruine) trägt eine Zeile.
    colon = pruefe_quelle("def f()\n    pass\n", "probe2.py")
    probe("fehlender Doppelpunkt erkannt", colon is not None and colon.zeile == 1,
          "" if colon else "nicht erkannt")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_pfad = Path(tmp)
        (tmp_pfad / "scripts").mkdir()
        (tmp_pfad / "scripts" / "gut.py").write_text(gute, encoding="utf-8")
        (tmp_pfad / "scripts" / "kaputt.py").write_text(kaputte, encoding="utf-8")
        (tmp_pfad / "scripts" / "__pycache__").mkdir()
        (tmp_pfad / "scripts" / "__pycache__" / "müll.py").write_text(
            "das ist kein python(\n", encoding="utf-8")
        (tmp_pfad / "scripts" / "notiz.txt").write_text("egal", encoding="utf-8")

        gelesen = [p.name for p in dateien(tmp_pfad)]
        probe("nur .py wird gelesen", gelesen == ["gut.py", "kaputt.py"], str(gelesen))
        probe("__pycache__ wird übersprungen", "müll.py" not in gelesen, str(gelesen))

        treffer = finde(tmp_pfad)
        probe("genau ein Fund im Baum", len(treffer) == 1,
              f"{len(treffer)} Funde")
        if treffer:
            probe("Pfad ist repo-relativ", treffer[0].datei == "scripts/kaputt.py",
                  treffer[0].datei)
            probe("Text nennt Datei und Zeile",
                  "scripts/kaputt.py:3" in treffer[0].text(), treffer[0].text())
        probe("Markdown nennt den Fund",
              "scripts/kaputt.py:3" in markdown(treffer, 2), "Markdown ohne Fund")
        probe("JSON ist serialisierbar",
              json.loads(json.dumps([f.as_dict() for f in treffer]))[0]["zeile"] == 3)

        # Beweis, dass die Prüfung nichts schreibt: kein __pycache__ entsteht.
        probe("Prüfung schreibt kein __pycache__",
              not any(Path(tmp_pfad, "scripts", "__pycache__").glob("gut*.pyc")),
              "die Wache hat den Arbeitsbaum verändert")

    probe("grüner Bericht ist grün", bericht([]).startswith("✅"), bericht([]))
    probe("roter Bericht nennt die Zahl", "1 Fund" in bericht(
        [Syntaxfehler("scripts/x.py", 3, "IndentationError: unexpected indent")]),
        bericht([Syntaxfehler("scripts/x.py", 3, "IndentationError: x")]))

    if fehler:
        print("🛑 SKRIPT-SYNTAX-WACHE SELFTEST FEHLGESCHLAGEN:")
        for f in fehler:
            print(f"  - {f}")
        return 2
    print("✅ SKRIPT-SYNTAX-WACHE SELFTEST bestanden "
          "(Erkennung, Zeile, Quellzeile, __pycache__-Schutz, Berichte, kein Schreiben).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prüft, ob jedes Python-Skript im Repo kompiliert.")
    parser.add_argument("--check", action="store_true",
                        help="prüfen (Standard; für Aufrufer, die es aussprechen wollen)")
    parser.add_argument("--selftest", action="store_true",
                        help="Detektor gegen Sabotage absichern")
    parser.add_argument("--json", action="store_true", help="Maschinenausgabe")
    parser.add_argument("--md", action="store_true", help="Markdown für Lauf-Summary")
    parser.add_argument("--wurzel", default=str(BLOG_DIR),
                        help="Repository-Wurzel (Default: dieses Repo)")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    root = Path(args.wurzel)
    alle = dateien(root)
    fehler = finde(root)

    if args.json:
        print(json.dumps({"geprueft": len(alle),
                          "fehler": [f.as_dict() for f in fehler]},
                         ensure_ascii=False, indent=2))
    elif args.md:
        print(markdown(fehler, len(alle)), end="")
    else:
        print(bericht(fehler, len(alle)))
        if fehler:
            print("\nHeilung (Maschinenbesitz): "
                  "python3 scripts/skript_syntax_heiler.py --fix --commit")
    return 0 if not fehler else 1


if __name__ == "__main__":
    sys.exit(main())
