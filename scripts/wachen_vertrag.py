#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
#  WACHEN-VERTRAG – EINE WACHE IST GANZ ODER GAR NICHT
#  ------------------------------------------------------------
#  WARUM ES DIESE WACHE GIBT (Vorgang WF-6F7F / Meldung #783,
#  16.10.2026)
#
#  Am 15.10.2026 um 18:18:59 wurde PR #776 zusammengeführt. Seine
#  Commit-Nachricht nennt den Vorgang offen:
#
#      „Rebased onto origin/main; Faustregel-Konflikte zugunsten der
#       themenspezifischen Varianten aufgelöst.“
#
#  Was dabei entstand, war keine Fassung, sondern ein ZUSAMMENSCHNITT:
#  Der Kopf und die 14 eingefrorenen Selbsttest-Fälle kamen aus der
#  neueren Fassung (#766, Faustregel-POOL + Bestandsmessung), der
#  RS3-Rumpf aus der älteren (`_themen_spezifische_faustregel`). Die
#  Datei war syntaktisch gültig – und in sich widersprüchlich:
#
#    · `main()` rief `faustregel_kontext()`, `_bestand_texte()`,
#      `faustregel_vorrat()`, `_kontext_aktualisieren()` und
#      `ersetze_generische_faustregel()` auf – keine dieser Funktionen
#      existierte noch.
#    · Der Selbsttest las `FAUSTREGEL_POOL`, `FAUSTREGEL_LEGACY`,
#      `FAUSTREGEL_VORRAT_WARNUNG` – alle drei gab es nicht mehr.
#
#  Die Folgen sind belegt: `--selftest` Exit 2 (Lauf 38893209063,
#  Meldung #783), Qualitäts-Gate rot ab 15.10. 18:19 (Lauf
#  38784603892, Schritt „Governance-Selbsttests …“), Regression rot
#  (Lauf 38784546132), und der Heilpfad der Redaktions-Wache war für
#  jeden echten Lauf ein `NameError` – eine tote Wache, die aussah,
#  als wäre sie da.
#
#  Die Lehre ist nicht „der Agent hat sich vertan“, sondern: Diese
#  Klasse von Defekt hatte keine Wache. Alle bestehenden Prüfungen
#  setzen voraus, dass eine DATEI funktioniert (Selbsttest) oder dass
#  ein ARTEFAKT lesbar ist (`artefakt_waechter.py`, A1–A6). Der
#  Zustand „die halbe Fassung“ liegt dazwischen: Die Datei ist
#  syntaktisch gültig, der Selbsttest ist sogar vorhanden – aber er
#  zeigt auf Namen, die es in dieser Datei nicht gibt.
#
#  WAS DIESE WACHE PRÜFT (rein lesend, ohne Ausführung des Prüflings)
#  ------------------------------------------------------------
#    W1  KONFLIKT-MARKER   `<<<<<<<` / `>>>>>>>` in einem Skript
#        (die Mitte `=======` wird nur gewertet, wenn ein Marker-Paar
#        existiert – sonst wäre jede Docstring-Unterstreichung ein
#        Befund).
#    W2  HALBER AUFRUF     ein Name wird aufgerufen (`foo(...)`), ist
#        aber in der Datei NIRGENDS gebunden – weder definiert, noch
#        importiert, noch Parameter, noch eingebaut. Ein solcher
#        Aufruf ist immer ein `NameError`; er kann nur überleben,
#        wenn ihn niemals jemand ausführt (genau der Vorfall).
#    W3  HALBE KONSTANTE   ein Modul-Konstante (GROSSBUCHSTABEN) wird
#        gelesen, ist aber in der Datei nirgends gebunden. Konvention
#        dieses Repos: Schwellen, Pools und Marker stehen als
#        Konstante oben – ihre Lesestelle ist ein Vertrag.
#    W4  AUSNAHME-ALTER     eine Ausnahme in
#        `data/wachen_vertrag_ausnahmen.yaml` ist unbekannt (Datei
#        existiert nicht mehr), unbegründet, undatiert – oder sie
#        deckt keinen Befund mehr zu. Eine Ausnahme, die altert, ohne
#        aufzufallen, ist ein Versteck.
#
#  BEWUSST NICHT GEPRÜFT
#  ---------------------
#    · Keine Vervollständigungs-Analyse (kein Pyflakes-Ersatz): W2/W3
#      melden nur, was BEWEISBAR nirgends gebunden ist. Alles, was
#      irgendwo in der Datei zugewiesen wird (auch in einer anderen
#      Funktion), gilt als gebunden – das ist bewusst zu großzügig,
#      damit diese Wache nie wegen eines Fehlalarms rot wird.
#      Die Prüfung erfolgt ohne Ausführung: keine Importe des
#      Prüflings, keine Netz-, keine Modellaufrufe.
#    · Keine Namensraum-Prüfung für dynamisch erzeugte Namen
#      (`globals()`/`setattr`): Wer so arbeitet, trägt die Begründung
#      in die Ausnahmedatei ein – sichtbar, nicht still.
#
#  NUTZUNG
#    python3 scripts/wachen_vertrag.py                 # prüfen (Exit 1 bei Fund)
#    python3 scripts/wachen_vertrag.py --json          # Maschinenausgabe
#    python3 scripts/wachen_vertrag.py --md            # Markdown für Lauf-Summary
#    python3 scripts/wachen_vertrag.py --selftest      # Sabotage-Schutz (Exit 2 bei Defekt)
#
#  EXIT: 0 = grün · 1 = Fund · 2 = der Vertrag selbst ist defekt
#
#  Report: WACHEN-VERTRAG-REPORT.md · Hintergrund:
#  WF-6F7F-783-DAUERHEILUNG-PREMIUM-2026-10-16.md
# ============================================================
from __future__ import annotations

import argparse
import ast
import builtins
import datetime
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

BLOG_DIR = Path(__file__).resolve().parent.parent
SKRIPTE = BLOG_DIR / "scripts"
AUSNAHMEN_DATEI = BLOG_DIR / "data" / "wachen_vertrag_ausnahmen.yaml"
REPORT = BLOG_DIR / "WACHEN-VERTRAG-REPORT.md"

# Die Klassen sind HART: Eine Wache, deren Namen ins Leere zeigen, ist keine
# Wache. Es gibt hier keine „Warnstufe“ – ein halber Messer ist kein stumpfer
# Messer, sondern ein Messer, das man für scharf hält.
KLASSEN = {
    "W1-KONFLIKT-MARKER": "Git-Konfliktmarker im Skript – eine Konflikt-Auflösung wurde nicht zu Ende geführt.",
    "W2-HALBER-AUFRUF": "Aufgerufener Name ohne Definition in dieser Datei – der Aufruf endet in einem NameError.",
    "W3-HALBE-KONSTANTE": "Gelesene Modul-Konstante ohne Definition in dieser Datei.",
    "W4-AUSNAHME": "Die Ausnahmedatei ist unbekannt, unbegründet, undatiert oder abgelaufen.",
    "W9-SYNTAX": "Die Datei ist kein gültiges Python – dann gilt hier keine Aussage über Namen.",
}

# Marker-Paar-Regel: `<<<<<<<` und `>>>>>>>` sind eindeutig; die Mitte nur
# zusammen mit einem Paar (siehe Kopfkommentar).
KONFLIKT_START = re.compile(r"^<{7}(?: |$)")
KONFLIKT_MITTE = re.compile(r"^={7}$")
KONFLIKT_ENDE = re.compile(r"^>{7}(?: |$)")

# Konvention „Schwelle/Pool/Marker als Konstante“: nur ALL-CAPS-Namen.
KONSTANTE = re.compile(r"^_*[A-Z][A-Z0-9_]{2,}$")

# Namen, die Python selbst in ein Modul legt.
MAGIC = {
    "__file__", "__name__", "__doc__", "__spec__", "__package__",
    "__loader__", "__builtins__", "__debug__", "__annotations__", "__path__",
    "__cached__", "__dict__",
}

BUILTIN_NAMEN = set(dir(builtins))


@dataclass(frozen=True)
class Fund:
    klasse: str
    pfad: str
    stelle: str
    meldung: str

    def kurz(self) -> str:
        return f"{self.klasse} {self.pfad}:{self.stelle} – {self.meldung}"


# ---------------------------------------------------------------------------
#  W1 – Konfliktmarker
# ---------------------------------------------------------------------------

def konfliktmarker(text: str) -> list[int]:
    """Zeilennummern echter Konfliktmarker (Paar-Regel, siehe Kopf)."""
    zeilen = text.splitlines()
    start = [i for i, z in enumerate(zeilen, 1) if KONFLIKT_START.match(z)]
    ende = [i for i, z in enumerate(zeilen, 1) if KONFLIKT_ENDE.match(z)]
    if not (start or ende):
        return []
    mitte = [i for i, z in enumerate(zeilen, 1) if KONFLIKT_MITTE.match(z)]
    return sorted(start + ende + mitte)


# ---------------------------------------------------------------------------
#  W2/W3 – Namens-Vertrag
# ---------------------------------------------------------------------------

def gebundene_namen(baum: ast.AST) -> set[str]:
    """Jeder Name, der in dieser Datei irgendwo gebunden wird.

    Bewusst großzügig (siehe Kopf): Zuweisung, Parameter, `def`/`class`,
    Import, `except … as`, Walrus, `global`, Match-Muster, Schleifen- und
    with-Ziele. Wer irgendwo in der Datei vorkommt, gilt als gebunden – die
    Wache meldet nur den beweisbaren Rest.
    """
    namen: set[str] = set()
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Name) and isinstance(knoten.ctx, (ast.Store, ast.Del)):
            namen.add(knoten.id)
        elif isinstance(knoten, ast.arg):
            namen.add(knoten.arg)
        elif isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            namen.add(knoten.name)
        elif isinstance(knoten, ast.alias):
            namen.add((knoten.asname or knoten.name).split(".")[0])
        elif isinstance(knoten, ast.ExceptHandler) and knoten.name:
            namen.add(knoten.name)
        elif isinstance(knoten, (ast.Global, ast.Nonlocal)):
            namen.update(knoten.names)
        elif isinstance(knoten, (ast.MatchAs, ast.MatchStar)):
            if knoten.name:
                namen.add(knoten.name)
        elif isinstance(knoten, ast.MatchMapping):
            if knoten.rest:
                namen.add(knoten.rest)
    return namen


def namensbefunde(pfad: str, text: str) -> list[Fund]:
    """W2 + W3 für EIN Skript. Ohne Ausführung, ohne Import des Prüflings."""
    try:
        baum = ast.parse(text, filename=pfad)
    except SyntaxError as exc:  # Ein nicht lesbares Skript ist kein Namensproblem.
        return [Fund("W9-SYNTAX", pfad, str(exc.lineno or 0),
                     f"Datei ist kein gültiges Python ({exc.msg}) – "
                     "weder Wache noch Prüfling.")]
    namen = gebundene_namen(baum)
    funde: list[Fund] = []
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Call) and isinstance(knoten.func, ast.Name):
            gerufen = knoten.func.id
            if gerufen not in namen and gerufen not in BUILTIN_NAMEN:
                funde.append(Fund(
                    "W2-HALBER-AUFRUF", pfad, str(knoten.lineno),
                    f"`{gerufen}()` wird aufgerufen, aber nirgends in dieser "
                    "Datei definiert oder importiert – halbe Fassung?"))
        elif isinstance(knoten, ast.Name) and isinstance(knoten.ctx, ast.Load):
            if (KONSTANTE.match(knoten.id) and knoten.id not in namen
                    and knoten.id not in BUILTIN_NAMEN and knoten.id not in MAGIC):
                funde.append(Fund(
                    "W3-HALBE-KONSTANTE", pfad, str(knoten.lineno),
                    f"`{knoten.id}` wird gelesen, aber in dieser Datei nicht "
                    "definiert – vertragslos?"))
    return funde


def skripte(root: Path | str) -> list[Path]:
    root = Path(root)
    return sorted(p for p in (root / "scripts").glob("*.py") if p.is_file())


def pruefe_skript(pfad: Path | str, root: Path | str) -> list[Fund]:
    root = Path(root)
    pfad = Path(pfad)
    try:
        text = pfad.read_text(encoding="utf-8")
    except OSError as exc:
        return [Fund("W9-LESEFEHLER", str(pfad.relative_to(root)), "0",
                     f"nicht lesbar: {exc.__class__.__name__}")]
    try:
        rel = str(pfad.relative_to(root))
    except ValueError:      # Datei außerhalb der Wurzel: trotzdem prüfen
        rel = str(pfad)
    funde = [Fund("W1-KONFLIKT-MARKER", rel, str(z),
                  "Konfliktmarker im Skript – Auflösung unvollständig.")
             for z in konfliktmarker(text)]
    funde += namensbefunde(rel, text)
    return funde


# ---------------------------------------------------------------------------
#  W4 – Ausnahmen (begründet, datiert, nicht still)
# ---------------------------------------------------------------------------

def lade_ausnahmen(datei: Path) -> tuple[dict, str]:
    """→ (Ausnahmen, Fehlertext). Fehlt die Datei, gibt es keine Ausnahmen."""
    if not datei.exists():
        return {}, ""
    try:
        import yaml  # noqa: PLC0415 – nur für die Ausnahmedatei nötig
    except Exception as exc:  # noqa: BLE001
        return {}, (f"`{datei.name}` vorhanden, aber PyYAML fehlt "
                    f"({exc.__class__.__name__}) – Ausnahmen nicht prüfbar.")
    try:
        daten = yaml.safe_load(datei.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001
        return {}, f"`{datei.name}` ist kein gültiges YAML: {exc.__class__.__name__}"
    if not isinstance(daten, dict):
        return {}, f"`{datei.name}` muss ein Mapping (Pfad → Begründung) sein."
    return daten, ""


def ausnahmebefunde(ausnahmen: dict, gedeckt: set, root: Path | str,
                    fehler: str = "") -> list[Fund]:
    """Prüft die Ausnahmen selbst: bekannt, begründet, datiert, nicht abgelaufen.

    `gedeckt` sind die Pfade, für die eine Ausnahme gerade WIRKLICH etwas
    unterdrückt. Eine Ausnahme, die nichts mehr deckt, ist kein stiller
    Freibrief, sondern ein Befund: Sie würde eine künftige halbe Fassung
    desselben Skripts verstecken.
    """
    root = Path(root)
    rel_datei = os.path.relpath(AUSNAHMEN_DATEI, root)
    if fehler:
        return [Fund("W4-AUSNAHME", rel_datei, "-", fehler)]
    befunde: list[Fund] = []
    for pfad, eintrag in sorted(ausnahmen.items()):
        pfad = str(pfad)
        if not (root / pfad).exists():
            befunde.append(Fund("W4-AUSNAHME", rel_datei, pfad,
                                "Ausnahme für eine Datei, die es nicht (mehr) "
                                "gibt – stille Lücke, Eintrag entfernen."))
            continue
        if not isinstance(eintrag, dict) or not str(eintrag.get("grund") or "").strip():
            befunde.append(Fund("W4-AUSNAHME", rel_datei, pfad,
                                "Ausnahme ohne Begründung (`grund`) – eine "
                                "Ausnahme ohne Grund ist ein Versteck."))
            continue
        seit = str(eintrag.get("seit") or "").strip()
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", seit):
            befunde.append(Fund("W4-AUSNAHME", rel_datei, pfad,
                                "Ausnahme ohne Datum (`seit: JJJJ-MM-TT`) – "
                                "eine Ausnahme muss altern können."))
            continue
        if pfad not in (gedeckt or set()):
            befunde.append(Fund("W4-AUSNAHME", rel_datei, pfad,
                                "Ausnahme deckt keinen Befund mehr zu "
                                "(die Datei ist in Ordnung) – Eintrag entfernen, "
                                "sonst wächst hier ein Versteck."))
    return befunde


# ---------------------------------------------------------------------------
#  Gesamtlauf
# ---------------------------------------------------------------------------

def befunde(root: Path | str = BLOG_DIR, ausnahmen: dict | None = None,
            ausnahmen_fehler: str = "", akzeptiert: list | None = None) -> list[Fund]:
    """Alle Funde. Importierbar (Governance-Vertrag C39) – schreibt nichts.

    Reihenfolge (bewusst so, seit dem Vorfall #783): ERST messen, DANN
    Ausnahmen anwenden. Eine Ausnahme kann nur benannte Klassen verdecken
    (W2/W3 – dynamischer Namensraum, Fremd-Einspielung); sie kann NIE einen
    Konfliktmarker (W1) verstecken. Und sie altert sichtbar: deckt sie nichts
    mehr zu, wird sie selbst zum Befund.
    """
    root = Path(root)
    rohe: list[Fund] = []
    for pfad in skripte(root):
        rohe += pruefe_skript(pfad, root)
    if ausnahmen is None:
        ausnahmen, ausnahmen_fehler = lade_ausnahmen(root / "data" /
                                                     AUSNAHMEN_DATEI.name)
    ausnahmen = ausnahmen or {}
    verdeckbar = {"W2-HALBER-AUFRUF", "W3-HALBE-KONSTANTE"}
    verdeckt = [f for f in rohe if f.pfad in ausnahmen and f.klasse in verdeckbar]
    gedeckt = {f.pfad for f in verdeckt}
    if akzeptiert is not None:
        akzeptiert.extend(verdeckt)
    funde = [f for f in rohe if f not in verdeckt]
    funde += ausnahmebefunde(ausnahmen, gedeckt, root, ausnahmen_fehler)
    return funde


def bericht(funde: list[Fund], geprueft: int) -> str:
    stand = datetime.datetime.now(datetime.timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    zeilen = [
        "# WACHEN-VERTRAG – Eine Wache ist ganz oder gar nicht",
        "",
        f"**Stand:** {stand} · **Geprüft:** {geprueft} Skript(e) unter `scripts/`",
        "",
        ("**Ergebnis:** ✅ keine halben Wachen – jeder aufgerufene Name und jede "
         "gelesene Konstante hat eine Definition in ihrer Datei."
         if not funde else
         f"**Ergebnis:** 🛑 {len(funde)} Fund(e) – siehe Tabelle."),
        "",
    ]
    if funde:
        zeilen += ["| Klasse | Datei | Stelle | Befund |", "|---|---|---|---|"]
        for f in funde:
            zeilen.append(f"| `{f.klasse}` | `{f.pfad}` | {f.stelle} | {f.meldung} |")
        zeilen += [
            "",
            "## Was jetzt zu tun ist",
            "",
            "1. **Keine beiden Seiten zusammensetzen.** Die betroffene Datei auf "
            "eine Fassung zurückstellen (`git checkout <rev> -- <pfad>`) und "
            "deren Selbsttest laufen lassen: `python3 scripts/<datei> --selftest`.",
            "2. Erst wenn der Selbsttest grün ist, wird committet. Ein roter "
            "Selbsttest ist der Beweis, dass die Fassung in sich nicht stimmt.",
            "3. Kann ein Name bewusst nicht in der Datei stehen (dynamischer "
            "Namensraum), gehört die Begründung nach "
            "`data/wachen_vertrag_ausnahmen.yaml` – mit `grund` und `seit`.",
        ]
    return "\n".join(zeilen) + "\n"


# ---------------------------------------------------------------------------
#  Selbsttest – eingefrorene Fälle (Vorgang WF-6F7F als Fall, nicht als Text)
# ---------------------------------------------------------------------------
#  Der Vorfall vom 15.10.2026 ist hier als MINIATUR eingefroren: dieselbe
#  Gemengelage (Kopf/Aufruf aus der neuen, Rumpf aus der alten Fassung).
#  Schlägt dieser Selbsttest fehl, ist der Messer stumpf – dann wird nichts
#  bewertet (Exit 2), und keine Aussage dieser Datei gilt.
HALBE_WACHE = '''#!/usr/bin/env python3
"""Miniatur des Vorfalls #783: Selbsttest neu, Rumpf alt."""
SELFTEST = [
    ("Pool-ist-gross", lambda: len(FAUSTREGEL_POOL) >= 12, True),
    ("Wahl-ist-deterministisch", lambda: waehle_faustregel("Strom", set())[0], True),
]


def fix(body):
    return ersetze_generische_faustregel(body, slug="strom")


def main():
    kontext = faustregel_kontext(_bestand_texte())
    if faustregel_vorrat(kontext) < FAUSTREGEL_VORRAT_WARNUNG:
        print("Vorrat fast leer")
    return _messung()


main()
'''

GANZE_WACHE = '''#!/usr/bin/env python3
"""Dieselbe Wache, eine Fassung: alles, was aufgerufen wird, existiert."""
FAUSTREGEL_POOL = (("strom", "Miss den Verbrauch, bevor du wechselst."),)
FAUSTREGEL_VORRAT_WARNUNG = 2


def faustregel_saetze():
    return [satz for _thema, satz in FAUSTREGEL_POOL]


def waehle_faustregel(text, eigene, slug="", kontext=None):
    return faustregel_saetze()[0], "gewaehlt"


def _messung():
    return 7


def ersetze_generische_faustregel(body, slug="", titel="", kontext=None):
    return body, 0, ""


def faustregel_kontext(texte):
    return {"belegung": set(), "index": {}, "vermeiden": set()}


def _bestand_texte():
    return {}


def faustregel_vorrat(kontext):
    return len(faustregel_saetze())


def main():
    kontext = faustregel_kontext(_bestand_texte())
    grenze = FAUSTREGEL_VORRAT_WARNUNG
    if faustregel_vorrat(kontext) < grenze:
        return waehle_faustregel("Strom", set())[1]
    return ersetze_generische_faustregel("", slug="strom")[2]


main()
'''

DOKSTRING_UNTERSTRICH = '''#!/usr/bin/env python3
"""Wache mit Markdown-Unterstreichung im Docstring.

NUTZUNG
=======
    python3 scripts/beispiel.py --selftest
"""
import sys

if "--selftest" in sys.argv:
    print("ok")
'''

# Die Marker werden zusammengesetzt, nicht zitiert: Diese Datei fällt unter
# ihre eigene Prüfung (W1), und ein eingefrorener Konfliktmarker im Quelltext
# einer Wache wäre genau der Fund, den sie melden soll.
_S = "<" * 7
_M = "=" * 7
_E = ">" * 7
KONFLIKT_KAPUTT = (f"#!/usr/bin/env python3\n{_S} HEAD\nGRENZE = 40\n"
                   f"{_M}\nGRENZE = 45\n{_E} origin/main\n\n\n"
                   "def main():\n    return GRENZE\n")

DYNAMISCH = '''#!/usr/bin/env python3
"""Dynamischer Namensraum: bewusst, begründet, ausgenommen."""
INJEKTION = {}


def main():
    globals().update(INJEKTION)
    return NICHT_IN_DER_DATEI
'''


def _fall(root: Path, name: str, inhalt: str) -> Path:
    ziel = root / "scripts" / name
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(inhalt, encoding="utf-8")
    return ziel


def selftest() -> int:
    fehler: list[str] = []
    geprueft = 0
    with tempfile.TemporaryDirectory(prefix="wachen-vertrag-") as tmp:
        wurzel = Path(tmp)

        def pruefe(name: str, bedingung: bool) -> None:
            nonlocal geprueft
            geprueft += 1
            if not bedingung:
                fehler.append(name)

        # --- W2/W3: der Vorfall -------------------------------------------
        _fall(wurzel, "halbe_wache.py", HALBE_WACHE)
        funde = befunde(wurzel, ausnahmen={})
        klassen = {f.klasse for f in funde}
        pruefe("Vorfall-wird-als-halbe-Wache-erkannt",
               "W2-HALBER-AUFRUF" in klassen and "W3-HALBE-KONSTANTE" in klassen)
        pruefe("Vorfall-nennt-den-Aufruf-faustregel_kontext",
               any("faustregel_kontext" in f.meldung for f in funde))
        pruefe("Vorfall-nennt-die-Konstante-FAUSTREGEL_POOL",
               any("FAUSTREGEL_POOL" in f.meldung for f in funde))

        # --- Gegenprobe: dieselbe Wache, eine Fassung ----------------------
        (wurzel / "scripts" / "halbe_wache.py").unlink()
        _fall(wurzel, "ganze_wache.py", GANZE_WACHE)
        pruefe("Ganze-Wache-ist-gruen", befunde(wurzel, ausnahmen={}) == [])

        # --- W1: Marker-Paar wird erkannt, Unterstreichung nicht -----------
        _fall(wurzel, "konflikt.py", KONFLIKT_KAPUTT)
        funde = befunde(wurzel, ausnahmen={})
        pruefe("Konfliktmarker-werden-erkannt",
               sum(1 for f in funde if f.klasse == "W1-KONFLIKT-MARKER") == 3)
        (wurzel / "scripts" / "konflikt.py").unlink()
        _fall(wurzel, "unterstrich.py", DOKSTRING_UNTERSTRICH)
        funde = befunde(wurzel, ausnahmen={})
        pruefe("Docstring-Unterstreichung-ist-kein-Konflikt",
               not any(f.klasse == "W1-KONFLIKT-MARKER" for f in funde))
        pruefe("sys-Import-ist-gebunden",
               not any(f.klasse == "W2-HALBER-AUFRUF" for f in funde))

        # --- Ausnahmen: begründet, datiert, nicht still --------------------
        _fall(wurzel, "dynamisch.py", DYNAMISCH)
        funde = befunde(wurzel, ausnahmen={})
        pruefe("Dynamischer-Name-wird-gemeldet",
               any(f.klasse == "W3-HALBE-KONSTANTE" for f in funde))
        # (a) Ausnahme greift – aber nur für W2/W3, nie für W1.
        unterdrueckt = befunde(wurzel, ausnahmen={
            "scripts/dynamisch.py": {"grund": "dynamischer Namensraum",
                                     "seit": "2026-10-16"}})
        pruefe("Ausnahme-unterdrueckt-den-Befund", unterdrueckt == [])
        (wurzel / "scripts" / "dynamisch.py").write_text(
            DOKSTRING_UNTERSTRICH.replace("beispiel.py", "dynamisch.py"),
            encoding="utf-8")
        funde = befunde(wurzel, ausnahmen={
            "scripts/dynamisch.py": {"grund": "dynamischer Namensraum",
                                     "seit": "2026-10-16"}})
        pruefe("Abgelaufene-Ausnahme-wird-gemeldet",
               any(f.klasse == "W4-AUSNAHME" and "keinen Befund" in f.meldung
                   for f in funde))
        # (b) ohne Grund / ohne Datum / unbekannte Datei
        for fall, stichwort in (
            ({"grund": "", "seit": "2026-10-16"}, "ohne Begründung"),
            ({"grund": "weil", "seit": ""}, "ohne Datum"),
            ("kein-mapping", "ohne Begründung"),
        ):
            _fall(wurzel, "x.py", DOKSTRING_UNTERSTRICH)
            funde = ausnahmebefunde({"scripts/x.py": fall}, set(), wurzel)
            pruefe(f"Ausnahme-{stichwort.replace(' ', '-')}-wird-gemeldet",
                   any(stichwort in f.meldung for f in funde))
            (wurzel / "scripts" / "x.py").unlink()
        funde = ausnahmebefunde({"scripts/gibtsnicht.py":
                                 {"grund": "alt", "seit": "2026-01-01"}}, set(), wurzel)
        pruefe("Ausnahme-fuer-fremde-Datei-wird-gemeldet",
               any("stille Lücke" in f.meldung for f in funde))
        # (c) unlesbare Ausnahmedatei ist ein Befund, kein Schweigen
        funde = ausnahmebefunde({}, set(), wurzel, fehler="PyYAML fehlt")
        pruefe("Nicht-pruefbare-Ausnahmen-sind-ein-Befund",
               any(f.klasse == "W4-AUSNAHME" for f in funde))

        # --- Der Prüfling wird nicht ausgeführt ----------------------------
        _fall(wurzel, "scharf.py",
              "#!/usr/bin/env python3\nprint('ICH WURDE AUSGEFÜHRT')\nraise SystemExit(9)\n")
        (wurzel / "scripts" / "scharf.py").chmod(0o500)
        pruefe("Prüfling-wird-nicht-ausgeführt", befunde(wurzel, ausnahmen={}) == [])

    if fehler:
        print("🛑 SELBSTTEST FEHLGESCHLAGEN – der Wachen-Vertrag ist defekt "
              "(Exit 2, kein Fund wird gemeldet):")
        for f in fehler:
            print("   -", f)
        return 2
    print(f"✅ Wachen-Vertrag: Selbsttest grün ({geprueft} eingefrorene Fälle: "
          "der Vorfall #783 als Miniatur, seine Gegenprobe, Marker-Paar-Regel, "
          "Ausnahme-Lebenszyklus, Nicht-Ausführung des Prüflings).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wachen-Vertrag: eine Wache ist "
                                                 "ganz oder gar nicht (#783)")
    parser.add_argument("--selftest", action="store_true", help="Sabotage-Schutz")
    parser.add_argument("--json", action="store_true", help="Maschinenausgabe")
    parser.add_argument("--md", action="store_true", help="Markdown für Lauf-Summary")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    ausnahmen, ausnahmen_fehler = lade_ausnahmen(AUSNAHMEN_DATEI)
    funde = befunde(BLOG_DIR, ausnahmen=ausnahmen, ausnahmen_fehler=ausnahmen_fehler)
    geprueft = len(skripte(BLOG_DIR))

    if args.json:
        print(json.dumps({"geprueft": geprueft,
                          "funde": [{"klasse": f.klasse, "pfad": f.pfad,
                                     "stelle": f.stelle, "meldung": f.meldung}
                                    for f in funde]}, ensure_ascii=False, indent=2))
    elif args.md:
        print(bericht(funde, geprueft))
    else:
        text = bericht(funde, geprueft)
        REPORT.write_text(text, encoding="utf-8")
        for f in funde:
            print(f"  🛑 {f.kurz()}")
        print(f"Wachen-Vertrag: {geprueft} Skript(e) geprüft, "
              f"{len(funde)} Fund(e) · Report: {REPORT.name}")

    return 1 if funde else 0


if __name__ == "__main__":
    sys.exit(main())
