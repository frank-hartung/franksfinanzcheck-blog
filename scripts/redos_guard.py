#!/usr/bin/env python3
"""ReDoS-Wache – die lokale Rückfallsperre zu Code-Scanning-Alert Nr. 87.

WARUM DIESE WACHE EXISTIERT (26.10.2026)
----------------------------------------
CodeQL meldete in `scripts/gsc_abdeckung.py` einen `py/redos`-Fund:

    ^sitemap:\\s*\\n(?:\\s+.*\\n)*?\\s+disable:\\s*true

Der Ausdruck sollte aus einem mehrzeiligen Hugo-Frontmatter nur die eine
Aussage lesen: „Ist `sitemap.disable` auf `true` gesetzt?“. Stattdessen
konnte dieselbe Eingabe von drei überlappenden, unbegrenzten Quantoren
zerlegt werden: `\\s+`, `.*` und `\\s+` hinter der wiederholten Gruppe.
CodeQL nannte die Pumpe wörtlich: Eingaben, die mit `sitemap:\\n` beginnen
und viele Wiederholungen von `\\t\\n` enthalten.

Die Heilung im Produktivcode ist ein zeilenweiser Parser ohne regulären
Ausdruck. Diese Wache hält die **Struktur der Fundstelle** fest. Sie ist
bewusst kein vollständiger Ersatz für CodeQL: Die allgemeine Suche nach
neuen ReDoS-Klassen bleibt die Aufgabe der `security-extended`-Suite, die
im Security-Gate zusätzlich namentlich hart verdrahtet ist. Was diese
Wache ohne SARIF-Upload, ohne Alert-API und ohne GitHub-Default-Setup
garantiert: Der historische Fehler und seine offensichtlichen Varianten
kommen nicht durch einen Merge zurück in den Bestand.

GEPRÜFTE REGELN
---------------
R0-SYNTAX       Eine Python-Datei ist nicht lesbar. Unlesbar ist nicht
                „sauber“, sondern ein Werkzeugfehler (fail-closed).
R1-NEWLINE-PUMP Ein Regex-Literal in einem `re.*`-Aufruf enthält eine
                unbegrenzte Gruppe, in der ein Whitespace-Quantor und ein
                breiter Zeilen-Quantor ohne Pflichttrennzeichen
                aufeinandertreffen, dazu ein Zeilenumbruch-Literal, und
                hinter der Gruppe folgt ein weiterer unbegrenzter
                Whitespace-Quantor. Genau diese Kombination erzeugt die
                exponentielle Zerlegung aus Alert Nr. 87.

BEWUSSTE GRENZEN
----------------
* Die Wache liest **statisch erkennbare Muster**: Literale, verkettete
  Literale, f-Strings mit Platzhalter und Modul-/Funktionskonstanten, die
  an `re.compile/search/match/fullmatch/sub/subn/findall/finditer/split`
  übergeben werden. Vollständig zur Laufzeit gebaute Muster bleiben
  CodeQLs Datenflussanalyse überlassen.
* Sie urteilt über die **Struktur**, nicht über die Herkunft der Eingabe.
  Ein harmloser const-String mit derselben Pumpe ist trotzdem ein Fund:
  Die nächste Änderung macht ihn vielleicht zu einer Benutzereingabe.
* Keine Ausnahmen, keine Whitelist, keine Inline-Unterdrückung. Ein
  berechtigt anderes Muster wird umgeschrieben, nicht freigesprochen.

AUFRUF
------
    python3 scripts/redos_guard.py                 # gesamten Python-Bestand prüfen
    python3 scripts/redos_guard.py --json         # maschinenlesbarer Bericht
    python3 scripts/redos_guard.py --root /pfad   # anderen Baum prüfen
    python3 scripts/redos_guard.py --selftest     # Schärfe- und Gegenproben

EXIT: 0 = grün · 1 = Fund · 2 = Wache selbst defekt
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

try:  # Python 3.11+ – ohne die veraltete sre_parse-Warnung.
    import re._parser as MUSTER_PARSER
except ImportError:  # pragma: no cover – Rückfall für ältere Laufzeiten.
    import sre_parse as MUSTER_PARSER  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parent.parent
REGEL_SYNTAX = "R0-SYNTAX"
REGEL_PUMPE = "R1-NEWLINE-PUMP"
RE_FUNKTIONEN = frozenset({
    "compile", "search", "match", "fullmatch", "sub", "subn",
    "findall", "finditer", "split",
})
WIEDERHOLUNG = frozenset({"MAX_REPEAT", "MIN_REPEAT"})
# Verzeichnisse, die CodeQL selbst nicht als eigenen Quelltext analysiert.
AUSGESCHLOSSEN = frozenset({
    ".git", "node_modules", ".venv", "venv", "__pycache__", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", "public", "resources", "build", "dist",
})
AUSGESCHLOSSENER_PFAD = ".claude/skills/impeccable/scripts"
# Stichproben für Zeichenklassen. Die historische Fundstelle ist ASCII; die
# zusätzlichen Zeichen verhindern, dass eine Unicode-Klasse still als leer
# gilt. Für die Strukturaussage genügt eine endliche, dokumentierte Menge.
PROBEN = tuple(chr(i) for i in range(128)) + (
    "ä", "ö", "ü", "ß", "–", "—", "€", "\u00a0", "\u200b", "中", "🙂",
)
ALLE_PROBEN = frozenset(PROBEN)
HORIZONTAL = frozenset({" ", "\t", "\f", "\v", "\u00a0"})
PLATZHALTER = "A"


@dataclass(frozen=True)
class Fund:
    regel: str
    pfad: str
    zeile: int
    muster: str
    text: str

    def kurz(self) -> str:
        return f"{self.regel} {self.pfad}:{self.zeile} – {self.text}"


def _name(op: object) -> str:
    return str(op)


def _kategoriezeichen(name: object) -> frozenset[str]:
    """Die von einer `sre_parse`-Kategorie erfassten Stichprobenzeichen."""
    kategorie = str(name).upper()
    out = set()
    for zeichen in PROBEN:
        if "NOT_SPACE" in kategorie:
            trifft = not zeichen.isspace()
        elif "NOT_DIGIT" in kategorie:
            trifft = not zeichen.isdigit()
        elif "NOT_WORD" in kategorie:
            trifft = not (zeichen.isalnum() or zeichen == "_")
        elif "SPACE" in kategorie:
            trifft = zeichen.isspace()
        elif "DIGIT" in kategorie:
            trifft = zeichen.isdigit()
        elif "WORD" in kategorie:
            trifft = zeichen.isalnum() or zeichen == "_"
        else:
            # Unbekannte Kategorie: konservativ „alle Zeichen“ annehmen.
            trifft = True
        if trifft:
            out.add(zeichen)
    return frozenset(out)


def _zeichenmenge(op: object, arg: object) -> frozenset[str]:
    """Stichprobenmenge eines einzelnen Zeichen-Tokens."""
    art = _name(op)
    if art == "LITERAL":
        wert = int(arg)  # type: ignore[arg-type]
        return frozenset({chr(wert)}) if 0 <= wert <= 0x10FFFF else ALLE_PROBEN
    if art == "NOT_LITERAL":
        wert = int(arg)  # type: ignore[arg-type]
        return ALLE_PROBEN - {chr(wert)}
    if art == "ANY":
        return ALLE_PROBEN
    if art == "CATEGORY":
        return _kategoriezeichen(arg)
    if art == "IN":
        eintraege = list(arg)  # type: ignore[arg-type]
        negiert = bool(eintraege and _name(eintraege[0][0]) == "NEGATE")
        if negiert:
            eintraege = eintraege[1:]
        out: set[str] = set()
        for teil_op, teil_arg in eintraege:
            teil_art = _name(teil_op)
            if teil_art == "LITERAL":
                out.add(chr(int(teil_arg)))
            elif teil_art == "RANGE":
                anfang, ende = teil_arg  # type: ignore[misc]
                out.update(chr(wert) for wert in range(max(0, int(anfang)),
                                                       min(0x10FFFF, int(ende)) + 1)
                           if chr(wert) in ALLE_PROBEN)
            elif teil_art == "CATEGORY":
                out.update(_kategoriezeichen(teil_arg))
            else:
                out.update(ALLE_PROBEN)
        menge = frozenset(out)
        return (ALLE_PROBEN - menge) if negiert else menge
    return ALLE_PROBEN


def _unbegrenzt(op: object, arg: object) -> bool:
    if _name(op) not in WIEDERHOLUNG:
        return False
    try:
        minimum, maximum, inhalt = arg  # type: ignore[misc]
    except (TypeError, ValueError):
        return False
    return (maximum is MUSTER_PARSER.MAXREPEAT
            or maximum == MUSTER_PARSER.MAXREPEAT) and minimum < maximum


def _quantor_art(op: object, arg: object) -> str:
    """`raum`, `breit` oder `""` für einen unbegrenzten Einzel-Quantor."""
    if not _unbegrenzt(op, arg):
        return ""
    try:
        _minimum, _maximum, inhalt = arg  # type: ignore[misc]
    except (TypeError, ValueError):
        return ""
    tokens = list(inhalt)
    if len(tokens) != 1:
        return ""
    teil_op, teil_arg = tokens[0]
    art = _name(teil_op)
    if art == "ANY":
        return "breit"
    menge = _zeichenmenge(teil_op, teil_arg)
    hat_horizontal = bool(menge & HORIZONTAL)
    # `\s`, `[ \t]`, `[^\S\n]` sind schmale Raumklassen: Jedes erfasste
    # Zeichen ist selbst Leerraum. `[^\n]` und `.` sind breit: Sie können
    # dieselben Leerzeichen wie die Raumklasse verschlingen, dazu aber
    # beliebige andere Zeichen – genau das erzeugt die mehrdeutige Zerlegung.
    if hat_horizontal and all(zeichen.isspace() for zeichen in menge):
        return "raum"
    if hat_horizontal and art in {"IN", "CATEGORY", "NOT_LITERAL"}:
        return "breit"
    return ""


def _ist_neuZeile(op: object, arg: object) -> bool:
    return _name(op) == "LITERAL" and int(arg) == 10  # type: ignore[arg-type]


def _gruppentokens(arg: object) -> list[tuple[object, object]]:
    """Tokens einer wiederholten Gruppe – eine nicht erfassende Gruppe ist
    im Parsebaum bereits eine flache Sequenz, eine erfassende steht in
    `SUBPATTERN`. Beide Formen müssen dieselbe Pumpe erkennen."""
    try:
        _minimum, _maximum, inhalt = arg  # type: ignore[misc]
    except (TypeError, ValueError):
        return []
    tokens = list(inhalt)
    if len(tokens) == 1 and _name(tokens[0][0]) == "SUBPATTERN":
        try:
            return list(tokens[0][1][-1])  # type: ignore[index]
        except (TypeError, IndexError):
            return tokens
    return tokens


def _pumpe_in_gruppe(tokens: list[tuple[object, object]]) -> bool:
    if not any(_ist_neuZeile(op, arg) for op, arg in tokens):
        return False
    for i, (op, arg) in enumerate(tokens):
        if _quantor_art(op, arg) != "raum":
            continue
        # Zwischen Raum- und Breitquantor darf höchstens ein Zeilenumbruch
        # stehen. Ein anderes Pflichtzeichen wäre ein eindeutiges Trennzeichen
        # und würde die mehrdeutige Zerlegung verhindern.
        for j in range(i + 1, min(i + 4, len(tokens))):
            if _quantor_art(*tokens[j]) == "breit":
                return True
            if not _ist_neuZeile(*tokens[j]):
                break
    return False


def _folgt_raumquantor(tokens: list[tuple[object, object]], start: int) -> bool:
    for op, arg in tokens[start + 1:]:
        art = _name(op)
        if art.startswith("AT") or art in {"ASSERT", "ASSERT_NOT", "SUCCESS"}:
            continue
        return _quantor_art(op, arg) == "raum"
    return False


def _struktur_gefunden(tokens: list[tuple[object, object]]) -> bool:
    for i, (op, arg) in enumerate(tokens):
        art = _name(op)
        # Possessive Quantoren und atomare Gruppen können nicht zurückverfolgen.
        if art == "POSSESSIVE_REPEAT" or art == "ATOMIC_GROUP":
            continue
        if _unbegrenzt(op, arg):
            gruppe = _gruppentokens(arg)
            if _pumpe_in_gruppe(gruppe) and _folgt_raumquantor(tokens, i):
                return True
            if _struktur_gefunden(gruppe):
                return True
        elif art == "SUBPATTERN":
            try:
                if _struktur_gefunden(list(arg[-1])):  # type: ignore[index]
                    return True
            except (TypeError, IndexError):
                continue
        elif art == "BRANCH":
            try:
                for zweig in arg[1]:  # type: ignore[index]
                    if _struktur_gefunden(list(zweig)):
                        return True
            except (TypeError, IndexError):
                continue
        elif art in {"ASSERT", "ASSERT_NOT"}:
            try:
                if _struktur_gefunden(list(arg[1])):  # type: ignore[index]
                    return True
            except (TypeError, IndexError):
                continue
    return False


def muster_gefunden(muster: str) -> bool:
    """Wahr, wenn ein Muster die Alert-Nr.-87-Struktur trägt."""
    try:
        baum = MUSTER_PARSER.parse(muster)
    except (ValueError, TypeError, OverflowError, RecursionError):
        return False
    return _struktur_gefunden(list(baum))


def _literalmuster(knoten: ast.AST, konstanten: dict[str, str]) -> str | None:
    if isinstance(knoten, ast.Constant) and isinstance(knoten.value, str):
        return knoten.value
    if isinstance(knoten, ast.Name):
        return konstanten.get(knoten.id)
    if isinstance(knoten, ast.JoinedStr):
        teile: list[str] = []
        for teil in knoten.values:
            if isinstance(teil, ast.Constant) and isinstance(teil.value, str):
                teile.append(teil.value)
            elif isinstance(teil, ast.FormattedValue):
                teile.append(PLATZHALTER)
            else:
                return None
        return "".join(teile)
    if isinstance(knoten, ast.BinOp) and isinstance(knoten.op, ast.Add):
        links = _literalmuster(knoten.left, konstanten)
        rechts = _literalmuster(knoten.right, konstanten)
        return links + rechts if links is not None and rechts is not None else None
    if isinstance(knoten, ast.Call):
        # `re.escape(...)` liefert Literaltext, keine Quantoren. Für die
        # Strukturanalyse genügt ein Platzhalter.
        func = knoten.func
        if isinstance(func, ast.Attribute) and func.attr == "escape":
            return PLATZHALTER
    return None


def _konstanten(baum: ast.AST) -> dict[str, str]:
    out: dict[str, str] = {}
    for knoten in ast.walk(baum):
        ziele: list[ast.AST] = []
        wert: ast.AST | None = None
        if isinstance(knoten, ast.Assign):
            ziele = list(knoten.targets)
            wert = knoten.value
        elif isinstance(knoten, ast.AnnAssign) and knoten.value is not None:
            ziele = [knoten.target]
            wert = knoten.value
        if wert is None:
            continue
        muster = _literalmuster(wert, out)
        if muster is None:
            continue
        for ziel in ziele:
            if isinstance(ziel, ast.Name):
                out[ziel.id] = muster
    return out


def _aliase(baum: ast.AST) -> tuple[set[str], dict[str, set[str]]]:
    module = {"re"}
    funktionen = {name: {name} for name in RE_FUNKTIONEN}
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Import):
            for eintrag in knoten.names:
                if eintrag.name == "re":
                    module.add(eintrag.asname or eintrag.name)
        elif isinstance(knoten, ast.ImportFrom) and knoten.module == "re":
            for eintrag in knoten.names:
                if eintrag.name in RE_FUNKTIONEN:
                    funktionen[eintrag.name].add(eintrag.asname or eintrag.name)
                elif eintrag.name == "*":
                    for name in RE_FUNKTIONEN:
                        funktionen[name].add(name)
    return module, funktionen


def _verwendet_verbose(aufruf: ast.Call) -> bool:
    muster_knoten: ast.AST | None = None
    if aufruf.args:
        muster_knoten = aufruf.args[0]
    for schluesselwort in aufruf.keywords:
        if schluesselwort.arg == "pattern":
            muster_knoten = schluesselwort.value
    if isinstance(muster_knoten, ast.Constant) and isinstance(muster_knoten.value, str):
        if "(?x" in muster_knoten.value[:8]:
            return True
    for argument in list(aufruf.args)[1:] + [k.value for k in aufruf.keywords]:
        try:
            text = ast.unparse(argument)
        except (AttributeError, ValueError):
            continue
        if "VERBOSE" in text or ".X" in text or "REGEX_X" in text:
            return True
    return False


def analysiere_quelle(quelle: str, pfad: str = "probe.py") -> list[Fund]:
    """Prüft eine Python-Quelle im Speicher. Schreibt nie in den Baum."""
    try:
        baum = ast.parse(quelle, filename=pfad)
    except (SyntaxError, ValueError) as exc:
        return [Fund(REGEL_SYNTAX, pfad, getattr(exc, "lineno", 1) or 1, "",
                     f"Python nicht analysierbar: {exc.__class__.__name__}")]
    konstanten = _konstanten(baum)
    module, funktionen = _aliase(baum)
    alle_funktionsnamen = {alias for mengen in funktionen.values() for alias in mengen}
    funde: list[Fund] = []
    gesehen: set[tuple[str, int, str]] = set()
    for knoten in ast.walk(baum):
        if not isinstance(knoten, ast.Call):
            continue
        func = knoten.func
        getroffen = False
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            getroffen = func.value.id in module and func.attr in RE_FUNKTIONEN
        elif isinstance(func, ast.Name):
            getroffen = func.id in alle_funktionsnamen
        if not getroffen or _verwendet_verbose(knoten):
            continue
        muster_knoten: ast.AST | None = knoten.args[0] if knoten.args else None
        for schluesselwort in knoten.keywords:
            if schluesselwort.arg == "pattern":
                muster_knoten = schluesselwort.value
        if muster_knoten is None:
            continue
        muster = _literalmuster(muster_knoten, konstanten)
        if muster is None or not muster_gefunden(muster):
            continue
        kennung = (pfad, knoten.lineno, muster)
        if kennung in gesehen:
            continue
        gesehen.add(kennung)
        funde.append(Fund(
            REGEL_PUMPE, pfad, knoten.lineno, muster[:240],
            "Mehrzeilige Regex-Pumpe: überlappende Raum- und Breitquantoren "
            "um eine wiederholte Zeilengruppe (Alert Nr. 87).",
        ))
    return funde


def dateien(root: Path = ROOT) -> list[Path]:
    out: list[Path] = []
    for pfad in root.rglob("*.py"):
        if any(teil in AUSGESCHLOSSEN for teil in pfad.parts):
            continue
        try:
            relativ = pfad.relative_to(root).as_posix()
        except ValueError:
            continue
        if relativ.startswith(AUSGESCHLOSSENER_PFAD):
            continue
        out.append(pfad)
    return sorted(out)


def scan(root: Path = ROOT) -> tuple[list[Fund], int]:
    liste = dateien(root)
    funde: list[Fund] = []
    for pfad in liste:
        try:
            quelle = pfad.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            funde.append(Fund(REGEL_SYNTAX, str(pfad.relative_to(root)), 1, "",
                              f"Datei nicht lesbar: {exc.__class__.__name__}"))
            continue
        funde.extend(analysiere_quelle(quelle, str(pfad.relative_to(root))))
    return funde, len(liste)


def _historisch() -> str:
    # Bewusst aus Teilen gebaut: Die Wache darf ihre eigene Rückfallprobe
    # nicht als produktives Regex-Literal in die CodeQL-Analyse tragen.
    return (r"^sitemap:\s*" + r"\n(?:\s+" + r".*\n)*?"
            + r"\s+disable:\s*true")


def _aufruf(muster: str, kopf: str = "import re", funktion: str = "re.search") -> str:
    return f"{kopf}\n\ndef pruefe(fm):\n    return {funktion}({muster!r}, fm)\n"


def selbsttest() -> int:
    ok = 0
    fehler: list[str] = []

    def pruefe(name: str, bedingung: bool, detail: str = "") -> None:
        nonlocal ok
        if bedingung:
            ok += 1
        else:
            fehler.append(f"{name}{': ' + detail if detail else ''}")

    hist = _historisch()
    direkt = analysiere_quelle(_aufruf(hist))
    pruefe("P1 historische Fundstelle wird erkannt",
           len(direkt) == 1 and direkt[0].regel == REGEL_PUMPE, str(direkt))

    konstant = analysiere_quelle(
        f"import re\nMUSTER = {hist!r}\n\ndef pruefe(fm):\n    return re.search(MUSTER, fm)\n")
    pruefe("P2 Musterkonstante wird erkannt",
           any(f.regel == REGEL_PUMPE for f in konstant), str(konstant))

    alias = analysiere_quelle(
        _aufruf(hist, kopf="import re as rx", funktion="rx.match"))
    pruefe("P3 Modulalias wird erkannt",
           any(f.regel == REGEL_PUMPE for f in alias), str(alias))

    direktimport = analysiere_quelle(
        _aufruf(hist, kopf="from re import search", funktion="search"))
    pruefe("P4 Funktionsalias wird erkannt",
           any(f.regel == REGEL_PUMPE for f in direktimport), str(direktimport))

    fstring = analysiere_quelle(
        "import re\n"
        "def pruefe(fm, kopf):\n"
        "    return re.search(rf\"^{kopf}\\s*\\n(?:\\s+.*\\n)*?\\s+disable:\\s*true\", fm)\n")
    pruefe("P5 f-String mit statischem Gerüst wird erkannt",
           any(f.regel == REGEL_PUMPE for f in fstring), str(fstring))

    kaputt = analysiere_quelle("def halb(:\n    pass\n")
    pruefe("P6 nicht lesbarer Quelltext ist fail-closed",
           len(kaputt) == 1 and kaputt[0].regel == REGEL_SYNTAX, str(kaputt))

    sicher_parser = analysiere_quelle(
        "def sitemap_deaktiviert(fm):\n"
        "    for zeile in fm.splitlines():\n"
        "        if zeile.strip() == 'sitemap:':\n"
        "            return True\n"
        "    return False\n")
    pruefe("G1 zeilenweiser Parser bleibt grün", sicher_parser == [], str(sicher_parser))

    ohne_schwanz = analysiere_quelle(
        _aufruf(r"^sitemap:\s*\n(?:\s+.*\n)*?disable:\s*true"))
    pruefe("G2 Pumpe ohne überlappenden Schlussquantor bleibt grün",
           ohne_schwanz == [], str(ohne_schwanz))

    mit_trenner = analysiere_quelle(
        _aufruf(r"^sitemap:[ \t]*\n(?:[ \t]+[^\n]*\n)*disable:\s*true"))
    pruefe("G3 eindeutiger Zeilentrenner bleibt grün",
           mit_trenner == [], str(mit_trenner))

    nur_kommentar = analysiere_quelle(
        f"# historisch: {hist}\n"
        "def pruefe(fm):\n    return 'sitemap:' in fm.splitlines()\n")
    pruefe("G4 ein Kommentar ist kein Aufruf",
           nur_kommentar == [], str(nur_kommentar))

    harmlos = analysiere_quelle(_aufruf(r"^sitemap:\s*disable:\s*true$"))
    pruefe("G5 einzeiliges Muster bleibt grün", harmlos == [], str(harmlos))

    nicht_dynamic = analysiere_quelle(
        "import re\n"
        "def pruefe(fm, muster):\n"
        "    return re.search(muster, fm)\n")
    pruefe("G6 unbekannte Laufzeitmuster erzeugen keinen Fehlalarm",
           nicht_dynamic == [], str(nicht_dynamic))

    if fehler:
        print(f"🛑 REDOS-WACHE SELBSTTEST: {len(fehler)} von {ok + len(fehler)} Fällen rot")
        for name in fehler:
            print(f"   ✗ {name}")
        return 2
    print(f"✅ REDOS-WACHE SELBSTTEST: {ok} Fälle grün")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Rückfallsperre gegen die ReDoS-Struktur aus Code-Scanning-Alert Nr. 87.")
    parser.add_argument("--selftest", action="store_true", help="Schärfe- und Gegenproben")
    parser.add_argument("--json", action="store_true", help="Bericht als JSON")
    parser.add_argument("--root", type=Path, default=ROOT, help="zu prüfendes Verzeichnis")
    args = parser.parse_args(argv)
    if args.selftest:
        return selbsttest()

    root = args.root.resolve()
    if not root.is_dir():
        print(f"🛑 Kein Verzeichnis: {root}")
        return 2
    funde, anzahl = scan(root)
    if anzahl < 20:
        print(f"🛑 Dateiauswahl zu klein ({anzahl}) – die Wache darf keinen "
              "leeren Baum als grün melden.")
        return 2
    bericht = {
        "geprueft": anzahl,
        "funde": [asdict(fund) for fund in funde],
        "regeln": [REGEL_SYNTAX, REGEL_PUMPE],
        "ok": not funde,
    }
    if args.json:
        print(json.dumps(bericht, ensure_ascii=False, indent=2))
    elif funde:
        print(f"🛑 REDOS-WACHE: {len(funde)} Fund(e) in {anzahl} Python-Dateien")
        for fund in funde:
            print(f"   ✗ {fund.kurz()}")
            print(f"::error file={fund.pfad},line={fund.zeile},"
                  f"title={fund.regel}::{fund.text}")
    else:
        print(f"✅ REDOS-WACHE: {anzahl} Python-Dateien, 0 Funde")
    return 1 if funde else 0


if __name__ == "__main__":
    sys.exit(main())
