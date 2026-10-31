#!/usr/bin/env python3
"""URL-Wache – lokale Reproduktion der CodeQL-Abfragen zur URL-Substring-Prüfung.

WARUM ES DIESE WACHE GIBT (Code-Scanning-Alert #83, 10.10.2026)
---------------------------------------------------------------
Am 04.10.2026 wurden elf Fundstellen dieser Regelklasse geheilt – zwei blieben
als begründete Inline-Ausnahme stehen (`# codeql[py/incomplete-url-substring-
sanitization]`). Genau diese zwei standen sechs Tage später wieder als offener
Alert in der Security-Tab. Der Grund ist derselbe wie bei Alert #80:

* Eine Inline-Unterdrückung wirkt nur in der **Advanced-Konfiguration** dieses
  Repositories. GitHubs parallel laufendes **Default-Setup** kennt weder
  `paths-ignore` noch `# codeql[...]`-Kommentare.
* Solange das Default-Setup aktiv ist, lehnt GitHub zusätzlich den
  SARIF-Upload der Advanced-Konfiguration ab. Die Alert-Nummern in der
  Security-Tab stammen dann vollständig vom Default-Setup.
* Ergebnis: Das Gate meldete „0 Funde", die Security-Tab zeigte offene Alerts.
  Eine Unterdrückung ist also **keine Heilung**, sondern nur eine andere Sicht.

Konsequenz und Vertrag dieser Wache:

1. **Unterdrückung ist selbst ein Befund.** Ein `# codeql[...]`- oder
   `# lgtm[...]`-Kommentar für eine der beiden Regeln wird rot – auch ohne
   Fundstelle darunter.
2. **Kein toter Winkel.** Geprüft werden Python, JavaScript (.js/.mjs/.cjs)
   und eingebettete `<script>`-Blöcke in HTML – auch Dateien, die
   `.github/codeql/codeql-config.yml` für die Advanced-Analyse ausblendet.
3. **Vor dem Scanner, nicht nach ihm.** Die Prüfung läuft offline in Sekunden
   (`python3 scripts/url_substring_guard.py`) und im CI als eigenständiges,
   von CodeQL und dessen Upload unabhängiges Gate.

WAS GEPRÜFT WIRD
----------------
Nachbau beider Abfragen der CodeQL-Standard-Suite – Muster und Ausnahmen
1:1 aus den Query-Quellen übersetzt (Stand 10/2026):

* `py/incomplete-url-substring-sanitization`
  python/ql/src/Security/CWE-020/IncompleteUrlSubstringSanitization.ql
      looksLikeUrl(s)  : "(?i)([a-z]*:?//)?\\.?([a-z0-9-]+\\.)+(com|org|edu|gov|
                          uk|net|io)(:[0-9]+)?/?"  ODER
                         "(?i)https?://([a-z0-9-]+\\.)+([a-z]+)(:[0-9]+)?/?"
      Fundstelle       : `"<url>" in x`, `x.startswith("<url>")`,
                         `x.endswith("<url>")`
      Ausnahmen        : startswith mit vollständigem Pfad
                         ("(?i)https?://[\\.a-z0-9-]+/.*"),
                         endswith mit führendem Punkt
                         ("(?i)\\.([a-z0-9-]+)(\\.[a-z0-9-]+)+")

* `js/incomplete-url-substring-sanitization`
  javascript/ql/src/Security/CWE-020/IncompleteUrlSubstringSanitization.qll
      Fundstelle       : StartsWith / EndsWith / Includes auf einer Zeichenkette
      zusätzlich       : Includes auch bei URL MIT Pfad
                         ("(?i)https?://([a-z0-9-]+\\.)+([a-z]+)(:[0-9]+)?/[a-z0-9/_-]+")
      Ausnahmen        : endsWith mit führendem Punkt; startsWith mit
                         abschließendem Port oder Schrägstrich (".*(:[0-9]+|/)")

BEWUSSTE ABWEICHUNG (strenger als CodeQL – jede einzeln begründet)
------------------------------------------------------------------
* Unterdrückungs-Kommentare zählen als Befund (siehe oben).
* Python `"<url>" not in x`: CodeQL kennt nur den `In`-Operator. Eine
  Negativ-Prüfung ist exakt so umgehbar wie die Positiv-Prüfung.
* Python `x.startswith(("<url>", …))`: CodeQL sieht nur `getArg(0)` als
  Zeichenkette. Ein Tupel ist dieselbe Prüfung, nur mehrfach.
* JavaScript `indexOf` / `lastIndexOf` / `search` mit URL-Literal: CodeQL
  verlangt zusätzlich den Vergleich (`=== 0`, `!== -1`, …). Ein solcher
  Aufruf OHNE Vergleich ist toter Code; mit Vergleich ist er die Lücke.

Die Heilung ist in allen Fällen dieselbe und steht in `scripts/url_host.py`:
URL parsen, Host exakt vergleichen (`ist_host`), Subdomains über die
Punkt-Grenze (`ist_host_oder_subdomain`), Text-/Codesuche mit Namensgrenzen
(`nennt_host`).

AUFRUF
------
    python3 scripts/url_substring_guard.py              # ganzes Repository
    python3 scripts/url_substring_guard.py --json       # maschinenlesbar
    python3 scripts/url_substring_guard.py --selftest   # Eigenprüfung
    python3 scripts/url_substring_guard.py pfad/a.py …  # einzelne Dateien

Exit-Code 0 = sauber, 1 = Befunde, 2 = Datei nicht analysierbar (fail-closed).
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
import tokenize
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REGEL_PY = "py/incomplete-url-substring-sanitization"
REGEL_JS = "js/incomplete-url-substring-sanitization"
REGELN = (REGEL_PY, REGEL_JS)

# --------------------------------------------------------------------------- #
#  1 · Muster – wörtlich aus den Query-Quellen
# --------------------------------------------------------------------------- #
_TLD = "com|org|edu|gov|uk|net|io"

# „Domain auf gängiger TLD, eventuell mit weiteren URL-Bestandteilen"
MUSTER_DOMAIN = re.compile(r"(?i)([a-z]*:?//)?\.?([a-z0-9-]+\.)+(" + _TLD + r")(:[0-9]+)?/?")
# „http(s)-URL auf eine Domain mit beliebiger TLD"
MUSTER_HTTP = re.compile(r"(?i)https?://([a-z0-9-]+\.)+([a-z]+)(:[0-9]+)?/?")
# nur JavaScript/Includes: dieselbe URL mit Pfadanteil
MUSTER_HTTP_PFAD = re.compile(r"(?i)https?://([a-z0-9-]+\.)+([a-z]+)(:[0-9]+)?/[a-z0-9/_-]+")

# Ausnahmen
SICHER_PRAEFIX_PY = re.compile(r"(?i)https?://[\.a-z0-9-]+/.*", re.DOTALL)
SICHER_SUFFIX = re.compile(r"(?i)\.([a-z0-9-]+)(\.[a-z0-9-]+)+")
SICHER_PRAEFIX_JS = re.compile(r".*(:[0-9]+|/)", re.DOTALL)

# Unterdrückungsmarker: echte Kommentare, nicht Zeichenketten.
MARKER = re.compile(r"\b(?:codeql|lgtm)\s*\[\s*[^\]]*incomplete-url-substring-sanitization[^\]]*\]",
                    re.IGNORECASE)

# Dateien, die nie eigener Quelltext sind.
AUSGESCHLOSSENE_TEILE = {".git", "node_modules", "__pycache__", ".venv", "venv",
                         "public", "resources", ".hugo_build.lock"}


def _voll(muster: re.Pattern[str], text: str) -> bool:
    """QLs `regexpMatch` verlangt den VOLLSTÄNDIGEN Treffer."""
    return muster.fullmatch(text) is not None


def sieht_aus_wie_url(text: str, *, includes: bool = False) -> bool:
    """`looksLikeUrl` der Python-Query bzw. die Zielmuster der JS-Query."""
    if _voll(MUSTER_DOMAIN, text) or _voll(MUSTER_HTTP, text):
        return True
    return includes and _voll(MUSTER_HTTP_PFAD, text)


def praefix_ist_sicher(text: str, *, sprache: str) -> bool:
    """Darf ein Präfix-Vergleich mit diesem Ziel als vollständig gelten?"""
    if sprache == "python":
        return _voll(SICHER_PRAEFIX_PY, text)
    return _voll(SICHER_PRAEFIX_JS, text)


def suffix_ist_sicher(text: str) -> bool:
    """Führender Punkt macht den Suffix-Vergleich auf dem Host eindeutig."""
    return _voll(SICHER_SUFFIX, text)


# --------------------------------------------------------------------------- #
#  2 · Befund
# --------------------------------------------------------------------------- #
@dataclass
class Befund:
    datei: str
    zeile: int
    regel: str
    art: str      # "pruefung" | "unterdrueckung"
    form: str     # "in", "startswith", "includes", …
    ziel: str     # die geprüfte Zeichenkette (ein Hostname, kein Geheimnis)

    def als_text(self) -> str:
        if self.art == "unterdrueckung":
            return (f"{self.datei}:{self.zeile} [{self.regel}] Unterdrückung statt Heilung "
                    f"({self.form})")
        return (f"{self.datei}:{self.zeile} [{self.regel}] {self.form} „{self.ziel}“ – "
                "die Zeichenkette darf an beliebiger Stelle der URL stehen")


def _rel(pfad: Path, wurzel: Path) -> str:
    try:
        return str(Path(pfad).resolve().relative_to(Path(wurzel).resolve()))
    except ValueError:
        return str(pfad)


# --------------------------------------------------------------------------- #
#  3 · Python-Analyse (AST – exakt die Query-Logik)
# --------------------------------------------------------------------------- #
def _py_literale(knoten: ast.AST) -> list[str]:
    """Zeichenketten-Literale eines Arguments (auch Tupel – strenger als CodeQL)."""
    if isinstance(knoten, ast.Constant) and isinstance(knoten.value, str):
        return [knoten.value]
    if isinstance(knoten, (ast.Tuple, ast.List, ast.Set)):
        werte: list[str] = []
        for teil in knoten.elts:
            if isinstance(teil, ast.Constant) and isinstance(teil.value, str):
                werte.append(teil.value)
        return werte
    return []


def pruefe_python(pfad: Path, quelltext: str, wurzel: Path) -> list[Befund]:
    rel = _rel(pfad, wurzel)
    baum = ast.parse(quelltext, filename=str(pfad))
    befunde: list[Befund] = []

    def melde(zeile: int, form: str, ziel: str) -> None:
        befunde.append(Befund(datei=rel, zeile=zeile, regel=REGEL_PY,
                              art="pruefung", form=form, ziel=ziel))

    for knoten in ast.walk(baum):
        # a) `"<url>" in x` – CodeQL: Compare.compares(url, In, _)
        if isinstance(knoten, ast.Compare):
            links = knoten.left
            for op, rechts in zip(knoten.ops, knoten.comparators):
                if isinstance(op, (ast.In, ast.NotIn)):
                    for wert in _py_literale(links):
                        if sieht_aus_wie_url(wert):
                            form = "in" if isinstance(op, ast.In) else "not in"
                            melde(getattr(links, "lineno", knoten.lineno), form, wert)
                links = rechts
        # b) `x.startswith("<url>")` / `x.endswith("<url>")`
        elif isinstance(knoten, ast.Call) and isinstance(knoten.func, ast.Attribute) \
                and knoten.args and knoten.func.attr in ("startswith", "endswith"):
            for wert in _py_literale(knoten.args[0]):
                if not sieht_aus_wie_url(wert):
                    continue
                if knoten.func.attr == "startswith":
                    if not praefix_ist_sicher(wert, sprache="python"):
                        melde(knoten.lineno, "startswith", wert)
                elif not suffix_ist_sicher(wert):
                    melde(knoten.lineno, "endswith", wert)
    return befunde


def unterdrueckungen_python(pfad: Path, quelltext: str, wurzel: Path) -> list[Befund]:
    """Marker in ECHTEN Kommentaren – ein Marker in einem String ist Lehrstoff."""
    rel = _rel(pfad, wurzel)
    befunde: list[Befund] = []
    try:
        for tok in tokenize.generate_tokens(iter(quelltext.splitlines(keepends=True)).__next__):
            if tok.type == tokenize.COMMENT and MARKER.search(tok.string):
                befunde.append(Befund(datei=rel, zeile=tok.start[0], regel=REGEL_PY,
                                      art="unterdrueckung", form="codeql-kommentar",
                                      ziel=tok.string.strip()[:120]))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # Der AST-Lauf meldet denselben Defekt als Analysefehler (fail-closed).
        pass
    return befunde


# --------------------------------------------------------------------------- #
#  4 · JavaScript – eigener Lexer (Kommentare und Zeichenketten sind kein Code)
# --------------------------------------------------------------------------- #
class LexFehler(Exception):
    """Quelltext ist nicht zerlegbar – fail-closed statt stillem Grün."""


@dataclass
class Tok:
    art: str              # name | zahl | string | regex | punkt | kommentar
    text: str             # Rohtext
    zeile: int
    wert: str | None = None   # konstanter Zeichenkettenwert (nur bei art == "string")


_JS_NAME_START = re.compile(r"[A-Za-z_$]")
_JS_NAME = re.compile(r"[A-Za-z0-9_$]")
_JS_ZAHL = re.compile(r"[0-9]")
_OPERATOREN = ("===", "!==", "==", "!=", ">=", "<=", "&&", "||", "??", "=>", "++", "--",
               "**", "+=", "-=", "*=", "/=", "<", ">", "=", "+", "-", "*", "/", "%",
               "(", ")", "[", "]", "{", "}", ",", ".", ":", ";", "?", "!", "&", "|",
               "~", "^", "@", "#")
# Nach diesen Token steht ein `/` für eine Division, sonst für ein Regex-Literal.
_KEIN_REGEX_DAVOR = {"name", "zahl", "string", "regex"}
_SCHLUESSELWORT = {"return", "typeof", "instanceof", "in", "of", "new", "delete", "void",
                   "throw", "case", "do", "else", "yield", "await"}

_JS_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v",
               "0": "\0", "\\": "\\", "'": "'", '"': '"', "`": "`"}


def _string_wert(roh: str) -> str:
    """Escapes auflösen – `"https://a\\u002ecom"` ist derselbe Wert wie ohne Escape."""
    out: list[str] = []
    i = 0
    while i < len(roh):
        z = roh[i]
        if z != "\\":
            out.append(z)
            i += 1
            continue
        i += 1
        if i >= len(roh):
            break
        n = roh[i]
        if n == "u":
            if i + 1 < len(roh) and roh[i + 1] == "{":
                ende = roh.find("}", i)
                if ende > 0:
                    try:
                        out.append(chr(int(roh[i + 2:ende], 16)))
                    except ValueError:
                        pass
                    i = ende + 1
                    continue
            try:
                out.append(chr(int(roh[i + 1:i + 5], 16)))
                i += 5
                continue
            except ValueError:
                pass
        elif n == "x":
            try:
                out.append(chr(int(roh[i + 1:i + 3], 16)))
                i += 3
                continue
            except ValueError:
                pass
        elif n == "\n":
            i += 1
            continue
        out.append(_JS_ESCAPES.get(n, n))
        i += 1
    return "".join(out)


_STATEMENT_KOEPFE = {"if", "while", "for", "with"}


def _klammer_leitet_statement_ein(toks: list[Tok]) -> bool:
    """Endet die letzte schließende Klammer eine `if (…)`-Bedingung?

    Der Lexer läuft rückwärts über die Token, zählt Klammern und prüft, ob
    vor der passenden öffnenden Klammer ein Statement-Kopf steht. Das ist
    die einzige Stelle, an der JavaScripts berühmte `/`-Mehrdeutigkeit
    tatsächlich entschieden werden kann, ohne einen Parser zu bauen.
    """
    tiefe = 0
    for index in range(len(toks) - 1, -1, -1):
        tok = toks[index]
        if tok.art != "punkt":
            if tiefe == 0:
                return tok.art == "name" and tok.text in _STATEMENT_KOEPFE
            continue
        if tok.text in (")", "]", "}"):
            tiefe += 1
        elif tok.text in ("(", "[", "{"):
            tiefe -= 1
            if tiefe == 0:
                davor = toks[index - 1] if index > 0 else None
                return bool(davor and davor.art == "name" and davor.text in _STATEMENT_KOEPFE)
    return False


def js_lexen(quelltext: str, startzeile: int = 1) -> list[Tok]:
    """Zerlegt JavaScript in Token. Wirft LexFehler, wenn das nicht geht."""
    toks: list[Tok] = []
    i = 0
    zeile = startzeile
    n = len(quelltext)
    letzte_bedeutung: Tok | None = None

    def anhaengen(t: Tok) -> None:
        nonlocal letzte_bedeutung
        toks.append(t)
        if t.art != "kommentar":
            letzte_bedeutung = t

    while i < n:
        z = quelltext[i]
        if z == "\n":
            zeile += 1
            i += 1
            continue
        if z in " \t\r\f\v\u00a0\ufeff":
            i += 1
            continue
        # Kommentare
        if z == "/" and i + 1 < n and quelltext[i + 1] == "/":
            ende = quelltext.find("\n", i)
            ende = n if ende < 0 else ende
            anhaengen(Tok("kommentar", quelltext[i:ende], zeile))
            i = ende
            continue
        if z == "/" and i + 1 < n and quelltext[i + 1] == "*":
            ende = quelltext.find("*/", i + 2)
            if ende < 0:
                raise LexFehler(f"Zeile {zeile}: Blockkommentar ohne Ende")
            text = quelltext[i:ende + 2]
            anhaengen(Tok("kommentar", text, zeile))
            zeile += text.count("\n")
            i = ende + 2
            continue
        # Zeichenketten
        if z in "'\"":
            j = i + 1
            while j < n:
                if quelltext[j] == "\\":
                    j += 2
                    continue
                if quelltext[j] == z:
                    break
                if quelltext[j] == "\n":
                    raise LexFehler(f"Zeile {zeile}: Zeichenkette ohne Ende")
                j += 1
            if j >= n:
                raise LexFehler(f"Zeile {zeile}: Zeichenkette ohne Ende")
            roh = quelltext[i + 1:j]
            anhaengen(Tok("string", quelltext[i:j + 1], zeile, _string_wert(roh)))
            i = j + 1
            continue
        # Template-Literale (konstant nur ohne ${…})
        if z == "`":
            j = i + 1
            tiefe = 0
            konstant = True
            while j < n:
                c = quelltext[j]
                if c == "\\":
                    j += 2
                    continue
                if c == "\n":
                    zeile += 1
                elif tiefe == 0 and c == "$" and j + 1 < n and quelltext[j + 1] == "{":
                    konstant = False
                    tiefe = 1
                    j += 2
                    continue
                elif tiefe > 0:
                    if c == "{":
                        tiefe += 1
                    elif c == "}":
                        tiefe -= 1
                elif c == "`":
                    break
                j += 1
            if j >= n:
                raise LexFehler(f"Zeile {zeile}: Template-Literal ohne Ende")
            roh = quelltext[i + 1:j]
            anhaengen(Tok("string", quelltext[i:j + 1], zeile,
                          _string_wert(roh) if konstant else None))
            i = j + 1
            continue
        # Regex-Literal oder Division
        if z == "/":
            # Wann beginnt nach einem `/` ein Regex-Literal, wann ist es
            # Division? Das ist die einzige echte Mehrdeutigkeit im
            # JavaScript-Lexer und sie muss KONJUNKTIV entschieden werden.
            #
            # BEFUND 31.10.2026: Hier stand eine ODER-Kette, in der der
            # Regex-Fall bereits durch das erste Glied wahr wurde. Folge:
            # `/` nach `)` galt IMMER als Regex-Start. Ein Ausdruck wie
            # `Math.round((x / W) * 1000) / 10` verschluckte damit den Rest
            # der Zeile bis zum nächsten `/` – und die Wache meldete an
            # fremden Dateien einen Lexfehler statt eines Befunds. Genau die
            # Sorte blinder Fleck, die Alert #83 sichtbar gemacht hat:
            # Was eine Analyse nicht liest, hält sie für in Ordnung.
            if letzte_bedeutung is None:
                regex_moeglich = True
            elif letzte_bedeutung.art == "name":
                # Nach einem Bezeichner nur, wenn er ein Statement einleitet
                # (`return /x/`), sonst ist es Division (`a / b`).
                regex_moeglich = letzte_bedeutung.text in _SCHLUESSELWORT
            elif letzte_bedeutung.art == "punkt":
                if letzte_bedeutung.text in (")", "]", "}"):
                    # `)` schließt meist einen Ausdruck (Division), kann aber
                    # eine `if (…)`-Bedingung beenden (Regex).
                    regex_moeglich = _klammer_leitet_statement_ein(toks)
                else:
                    regex_moeglich = True
            else:
                # Nach Zahl, Zeichenkette oder Regex folgt immer Division.
                regex_moeglich = False
            if regex_moeglich:
                j = i + 1
                klasse = False
                ok = False
                while j < n:
                    c = quelltext[j]
                    if c == "\\":
                        j += 2
                        continue
                    if c == "\n":
                        break           # Regex-Literale sind einzeilig → war Division
                    if c == "[":
                        klasse = True
                    elif c == "]":
                        klasse = False
                    elif c == "/" and not klasse:
                        ok = True
                        break
                    j += 1
                if ok:
                    j += 1
                    while j < n and _JS_NAME.match(quelltext[j]):
                        j += 1
                    anhaengen(Tok("regex", quelltext[i:j], zeile))
                    i = j
                    continue
            anhaengen(Tok("punkt", "/", zeile))
            i += 1
            continue
        # Namen
        if _JS_NAME_START.match(z):
            j = i
            while j < n and _JS_NAME.match(quelltext[j]):
                j += 1
            anhaengen(Tok("name", quelltext[i:j], zeile))
            i = j
            continue
        # Zahlen
        if _JS_ZAHL.match(z) or (z == "." and i + 1 < n and _JS_ZAHL.match(quelltext[i + 1])):
            j = i
            while j < n and (_JS_NAME.match(quelltext[j]) or quelltext[j] == "."
                             or (quelltext[j] in "+-" and quelltext[j - 1] in "eE")):
                j += 1
            anhaengen(Tok("zahl", quelltext[i:j], zeile))
            i = j
            continue
        # Operatoren
        for op in _OPERATOREN:
            if quelltext.startswith(op, i):
                anhaengen(Tok("punkt", op, zeile))
                i += len(op)
                break
        else:
            anhaengen(Tok("punkt", z, zeile))
            i += 1
    return toks


def _argumente(toks: list[Tok], klammer: int) -> list[list[Tok]] | None:
    """Argumentliste eines Aufrufs ab Index der `(`; None bei fehlender `)`."""
    tiefe = 0
    aktuell: list[Tok] = []
    args: list[list[Tok]] = []
    i = klammer
    while i < len(toks):
        t = toks[i]
        if t.art == "punkt":
            if t.text in "([{":
                tiefe += 1
                if tiefe == 1:
                    i += 1
                    continue
            elif t.text in ")]}":
                tiefe -= 1
                if tiefe == 0:
                    if aktuell or args:
                        args.append(aktuell)
                    return args
            elif t.text == "," and tiefe == 1:
                args.append(aktuell)
                aktuell = []
                i += 1
                continue
        aktuell.append(t)
        i += 1
    return None


_JS_SUBSTRING = {"startsWith": "startsWith", "endsWith": "endsWith", "includes": "includes"}
_JS_INDEX = {"indexOf", "lastIndexOf", "search"}
_JS_SCHNITT = {"slice", "substring", "substr"}
_VERGLEICH = {"===", "==", "!==", "!="}


def pruefe_js_tokens(toks: list[Tok], rel: str) -> list[Befund]:
    """Findet Substring-Prüfungen auf URL-Literalen im Token-Strom."""
    befunde: list[Befund] = []
    code = [t for t in toks if t.art != "kommentar"]

    def melde(zeile: int, form: str, ziel: str) -> None:
        befunde.append(Befund(datei=rel, zeile=zeile, regel=REGEL_JS,
                              art="pruefung", form=form, ziel=ziel))

    def literal(arg: list[Tok]) -> str | None:
        if len(arg) == 1 and arg[0].art == "string" and arg[0].wert is not None:
            return arg[0].wert
        return None

    for i, t in enumerate(code):
        # a) x.startsWith("…") / x.endsWith("…") / x.includes("…")  (+ lodash `_`)
        if t.art == "punkt" and t.text == "." and i + 2 < len(code) \
                and code[i + 1].art == "name" and code[i + 2].art == "punkt" \
                and code[i + 2].text == "(":
            name = code[i + 1].text
            args = _argumente(code, i + 2)
            if args is None:
                continue
            lodash = i > 0 and code[i - 1].art == "name" and code[i - 1].text == "_"
            if name in _JS_SUBSTRING:
                index = 1 if lodash and len(args) > 1 else 0
                wert = literal(args[index]) if len(args) > index else None
                if wert is not None and sieht_aus_wie_url(wert, includes=(name == "includes")):
                    if name == "startsWith" and praefix_ist_sicher(wert, sprache="js"):
                        continue
                    if name == "endsWith" and suffix_ist_sicher(wert):
                        continue
                    melde(code[i + 1].zeile, name, wert)
            elif name in _JS_INDEX:
                wert = literal(args[0]) if args else None
                if wert is not None and sieht_aus_wie_url(wert, includes=True):
                    melde(code[i + 1].zeile, name, wert)
        # b) x.slice(0, n) === "…"  /  "…" === x.slice(0, n)
        if t.art == "punkt" and t.text in _VERGLEICH:
            links = code[i - 1] if i > 0 else None
            rechts = code[i + 1] if i + 1 < len(code) else None
            if rechts is not None and rechts.art == "string" and rechts.wert is not None \
                    and links is not None and links.art == "punkt" and links.text == ")":
                if _schnitt_davor(code, i - 1) and sieht_aus_wie_url(rechts.wert) \
                        and not praefix_ist_sicher(rechts.wert, sprache="js"):
                    melde(rechts.zeile, "slice-vergleich", rechts.wert)
            if links is not None and links.art == "string" and links.wert is not None \
                    and rechts is not None and rechts.art == "name":
                if _schnitt_dahinter(code, i + 1) and sieht_aus_wie_url(links.wert) \
                        and not praefix_ist_sicher(links.wert, sprache="js"):
                    melde(links.zeile, "slice-vergleich", links.wert)
    return befunde


def _schnitt_davor(code: list[Tok], zu: int) -> bool:
    """Gehört die `)` bei Index `zu` zu einem slice/substring/substr-Aufruf?"""
    tiefe = 0
    i = zu
    while i >= 0:
        t = code[i]
        if t.art == "punkt":
            if t.text in ")]}":
                tiefe += 1
            elif t.text in "([{":
                tiefe -= 1
                if tiefe == 0:
                    return (i >= 2 and code[i - 1].art == "name"
                            and code[i - 1].text in _JS_SCHNITT
                            and code[i - 2].art == "punkt" and code[i - 2].text == ".")
        i -= 1
    return False


def _schnitt_dahinter(code: list[Tok], ab: int) -> bool:
    """Folgt ab Index `ab` ein `… .slice(`-Aufruf?"""
    for i in range(ab, min(ab + 8, len(code) - 2)):
        if code[i].art == "punkt" and code[i].text == "." \
                and code[i + 1].art == "name" and code[i + 1].text in _JS_SCHNITT \
                and code[i + 2].art == "punkt" and code[i + 2].text == "(":
            return True
    return False


def unterdrueckungen_js(toks: list[Tok], rel: str) -> list[Befund]:
    return [Befund(datei=rel, zeile=t.zeile, regel=REGEL_JS, art="unterdrueckung",
                   form="codeql-kommentar", ziel=t.text.strip()[:120])
            for t in toks if t.art == "kommentar" and MARKER.search(t.text)]


# --------------------------------------------------------------------------- #
#  5 · HTML – eingebettete <script>-Blöcke (CodeQL analysiert sie mit)
# --------------------------------------------------------------------------- #
# HEILUNG 10.10.2026 (py/bad-tag-filter, gefunden von CodeQL AN DIESER WACHE):
# Das Endtag hieß hier `</script\s*>` und übersah damit, was Browser sehr wohl
# als Ende lesen – `</script foo="bar">`, `</script\t\n bar>`, `</script/>`.
# Folge wäre ein Fail-OPEN gewesen: Der Skriptblock hätte nicht geendet, der
# Lexer hätte Markup als JavaScript gelesen oder den Block ganz verfehlt. Ein
# `\b` nach dem Namen hält `</scriptfoo>` weiterhin draußen.
_SCRIPT = re.compile(r"<script\b([^>]*)>(.*?)</script\b[^>]*>", re.IGNORECASE | re.DOTALL)
_ATTR_SRC = re.compile(r"\bsrc\s*=", re.IGNORECASE)
_ATTR_TYPE = re.compile(r"""\btype\s*=\s*["']?([^"'\s>]+)""", re.IGNORECASE)
_JS_TYPEN = {"", "text/javascript", "application/javascript", "module",
             "text/ecmascript", "application/ecmascript"}
# Hugo-/Go-Template-Aktionen sind kein JavaScript. Sie werden durch einen
# neutralen Namen ersetzt, damit der Lexer den umgebenden echten Code sieht
# (in einer Zeichenkette bleibt daraus schlicht ein Wort).
_TEMPLATE_AKTION = re.compile(r"\{\{.*?\}\}", re.DOTALL)
# Hugo-Kommentare zuerst: Sie dürfen ihrerseits `}}` enthalten (Beispielcode in
# der Erklärung), und genau dort steht in diesem Repo ein erwähntes `<script>`.
_HUGO_KOMMENTAR = re.compile(r"\{\{-?\s*/\*.*?\*/\s*-?\}\}", re.DOTALL)
# HTML-Kommentare können ein `<script>` erwähnen, ohne eines zu öffnen.
_HTML_KOMMENTAR = re.compile(r"<!--.*?-->", re.DOTALL)


def _neutral(m: re.Match[str]) -> str:
    """Ersetzt einen Bereich durch einen harmlosen Namen – Zeilen bleiben erhalten."""
    return "__HUGO__" + "\n" * m.group(0).count("\n")


def _ohne_template(text: str) -> str:
    """Hugo-Aktionen und HTML-Kommentare neutralisieren (zeilentreu).

    Beides ist kein JavaScript – und beides kann ein `<script>` enthalten, das
    gar keines ist (`layouts/_partials/schema_article.html` dokumentiert in
    einem Hugo-Kommentar das Auto-Escaping in „`<script>`-Blöcken").
    """
    ohne = _HUGO_KOMMENTAR.sub(_neutral, text)
    return _TEMPLATE_AKTION.sub(_neutral, _HTML_KOMMENTAR.sub(_neutral, ohne))


def html_skripte(quelltext: str) -> list[tuple[int, str]]:
    """(Startzeile, JavaScript) aller inline-Skripte – ohne src und ohne JSON."""
    out: list[tuple[int, str]] = []
    for m in _SCRIPT.finditer(quelltext):
        attribute, inhalt = m.group(1), m.group(2)
        if _ATTR_SRC.search(attribute):
            continue
        typ = _ATTR_TYPE.search(attribute)
        if typ and typ.group(1).strip().lower() not in _JS_TYPEN:
            continue
        startzeile = quelltext.count("\n", 0, m.start(2)) + 1
        out.append((startzeile, inhalt))
    return out


# --------------------------------------------------------------------------- #
#  6 · Dateiauswahl und Lauf
# --------------------------------------------------------------------------- #
PY_ENDUNGEN = {".py", ".pyw"}
# TypeScript wird mitgeprüft: Der Lexer unten braucht nur Zeichenketten,
# Kommentare, Regex-Literale und Bezeichner – Typannotationen stören ihn
# nicht. CodeQLs JavaScript-Extraktor liest .ts/.tsx/.mts/.cts ohnehin als
# JavaScript, also darf diese Wache dort keinen blinden Fleck haben.
JS_ENDUNGEN = {".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".mts", ".cts"}
HTML_ENDUNGEN = {".html", ".htm", ".xhtml"}
ALLE_ENDUNGEN = PY_ENDUNGEN | JS_ENDUNGEN | HTML_ENDUNGEN

# Endungen, die CodeQL analysiert, für die hier aber (noch) kein Leser
# existiert. Taucht eine davon im Repository auf, ist das KEIN „sauber“,
# sondern eine Lücke: `scopeluecken()` meldet sie, der Sicherheitsvertrag
# macht sie rot. So erzwingt der erste `.vue`-Baustein die Erweiterung der
# Wache, statt still an ihr vorbeizulaufen (Lehre aus Alert #83: Was eine
# Analyse nicht liest, hält sie für in Ordnung).
UNGELESENE_ENDUNGEN = {".vue", ".hbs", ".ejs", ".njk", ".svelte", ".astro"}


def scopeluecken(wurzel: Path = None) -> list[str]:
    """Dateien, die CodeQL liest und diese Wache (noch) nicht.

    Rückgabe ist die (hoffentlich leere) Liste der Pfade. Nicht leer heißt:
    Wache erweitern, bevor der Baustein nach `main` geht.
    """
    wurzel = Path(wurzel or ROOT)
    muster = [f"*{e}" for e in sorted(UNGELESENE_ENDUNGEN)]
    try:
        roh = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", *muster],
            cwd=wurzel, capture_output=True, text=True, timeout=120, check=True).stdout
        kandidaten = [wurzel / p for p in roh.split("\0") if p.strip()]
    except (OSError, subprocess.SubprocessError):
        kandidaten = [p for e in UNGELESENE_ENDUNGEN for p in wurzel.rglob(f"*{e}")]
    return sorted(
        str(p.relative_to(wurzel)) for p in kandidaten
        if not any(teil in AUSGESCHLOSSENE_TEILE for teil in p.parts))



def quelldateien(wurzel: Path) -> list[Path]:
    """Versionierte plus neue, nicht ignorierte Quelldateien.

    Eine neue Datei muss schon vor ihrem ersten Commit sichtbar sein; nur
    `git ls-files` zu verwenden wäre lokal ein Blindflug.
    """
    muster = [f"*{e}" for e in sorted(ALLE_ENDUNGEN)]
    try:
        roh = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", *muster],
            cwd=wurzel, capture_output=True, text=True, timeout=120, check=True).stdout
        dateien = [wurzel / p for p in roh.split("\0") if p.strip()]
        if dateien:
            return sorted({d for d in dateien if _relevant(d)})
    except (OSError, subprocess.SubprocessError):
        pass
    return sorted({p for e in ALLE_ENDUNGEN for p in wurzel.rglob(f"*{e}") if _relevant(p)})


def _relevant(pfad: Path) -> bool:
    if any(teil in AUSGESCHLOSSENE_TEILE for teil in pfad.parts):
        return False
    # Minifizierte Vendor-Bündel sind generierte Artefakte; ihr Quelltext liegt
    # upstream. Sie werden geprüft, aber ihre Lexfehler sind keine Befunde
    # (siehe pruefe()).
    return pfad.suffix.lower() in ALLE_ENDUNGEN


def _minifiziert(pfad: Path) -> bool:
    name = pfad.name.lower()
    return name.endswith(".min.js") or name.endswith(".umd.js") or name.endswith(".min.mjs")


def pruefe(pfade, wurzel: Path = ROOT) -> tuple[list[Befund], list[str]]:
    befunde: list[Befund] = []
    fehler: list[str] = []
    for roh in pfade:
        pfad = Path(roh)
        rel = _rel(pfad, wurzel)
        try:
            quelltext = pfad.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            fehler.append(f"{rel}: nicht lesbar ({exc.__class__.__name__})")
            continue
        endung = pfad.suffix.lower()
        try:
            if endung in PY_ENDUNGEN:
                befunde.extend(pruefe_python(pfad, quelltext, wurzel))
                befunde.extend(unterdrueckungen_python(pfad, quelltext, wurzel))
            elif endung in JS_ENDUNGEN:
                toks = js_lexen(quelltext)
                befunde.extend(pruefe_js_tokens(toks, rel))
                befunde.extend(unterdrueckungen_js(toks, rel))
            elif endung in HTML_ENDUNGEN:
                # Zuerst Hugo-Aktionen/HTML-Kommentare neutralisieren, DANN die
                # Skriptblöcke suchen: sonst öffnet ein `<script>` aus einem
                # Kommentar einen Block, den es nie gab.
                for startzeile, js in html_skripte(_ohne_template(quelltext)):
                    toks = js_lexen(js, startzeile)
                    befunde.extend(pruefe_js_tokens(toks, rel))
                    befunde.extend(unterdrueckungen_js(toks, rel))
        except SyntaxError as exc:
            fehler.append(f"{rel}:{exc.lineno}: Syntaxfehler – nicht analysierbar")
        except LexFehler as exc:
            if _minifiziert(pfad):
                continue
            fehler.append(f"{rel}: {exc}")
        except RecursionError:
            fehler.append(f"{rel}: zu tief verschachtelt – nicht analysierbar")
    return befunde, fehler


# --------------------------------------------------------------------------- #
#  7 · Eigenprüfung (Positiv-, Gegen- und Musterproben)
# --------------------------------------------------------------------------- #
POSITIV: dict[str, tuple[str, str]] = {
    "py_in": (".py", '''
def ist_blog(url):
    return "https://franksfinanzcheck.de" in url
'''),
    "py_not_in": (".py", '''
def fremd(url):
    return "api.pinterest.com" not in url
'''),
    "py_startswith": (".py", '''
def ist_api(url):
    return url.startswith("https://api.resend.com")
'''),
    "py_endswith": (".py", '''
def eigener_host(host):
    return host.endswith("api.resend.com")
'''),
    "py_tupel": (".py", '''
def erlaubt(url):
    return url.startswith(("https://api.resend.com", "/go/"))
'''),
    "py_kette": (".py", '''
def pruefe(url, liste):
    return url and "api.pinterest.com" in url in liste
'''),
    "py_unterdrueckung": (".py", '''
def harmlos(text):
    # codeql[py/incomplete-url-substring-sanitization] war mal eine Ausnahme
    return len(text)
'''),
    "js_includes": (".mjs", '''
export function istBlog(url) {
  return url.includes("https://franksfinanzcheck.de");
}
'''),
    "js_includes_mit_pfad": (".mjs", '''
export const treffer = (url) => url.includes("https://franksfinanzcheck.de/go/gas");
'''),
    "js_startswith": (".js", '''
function istApi(url) {
  return url.startsWith("https://api.resend.com");
}
'''),
    "js_endswith": (".js", '''
function eigen(host) {
  return host.endsWith("api.pinterest.com");
}
'''),
    "js_indexof": (".js", '''
const treffer = url.indexOf("https://api.pinterest.com") !== -1;
'''),
    "js_lodash": (".js", '''
const ok = _.startsWith(url, "https://api.resend.com");
'''),
    "js_slice": (".js", '''
const ok = url.slice(0, 28) === "https://api.resend.com";
'''),
    "js_template": (".mjs", '''
export const ok = (url) => url.includes(`https://franksfinanzcheck.de`);
'''),
    "js_unterdrueckung": (".js", '''
// codeql[js/incomplete-url-substring-sanitization] war mal eine Ausnahme
export const laenge = (t) => t.length;
'''),
    "html_inline": (".html", '''<!doctype html>
<html><body>
<script>
  if (location.href.includes("https://franksfinanzcheck.de")) { ok(); }
</script>
</body></html>
'''),
    # TypeScript: CodeQLs JS-Extraktor liest .ts/.tsx wie JavaScript, also
    # muss diese Wache es auch tun (Scope-Vertrag seit 10.10.2026).
    "ts_includes": (".ts", '''
export function istBlog(url: string): boolean {
  const liste: Array<string> = [];
  return liste.length === 0 && url.includes("https://franksfinanzcheck.de/go/");
}
'''),
    "tsx_indexof": (".tsx", '''
export const trefferAt = (u: string): number => u.indexOf("https://api.resend.com/emails");
'''),
    # Endtag mit Müll: Browser lesen `</script\t\n bar>` als Ende, eine naive
    # Regex nicht (py/bad-tag-filter, 10.10.2026 von CodeQL an dieser Wache
    # selbst gefunden). Wird der Block nicht beendet, verfehlt die Wache den
    # Code darin – ein Fail-OPEN, das hier dauerhaft ausgeschlossen bleibt.
    "html_endtag_mit_muell": (".html", '''<!doctype html>
<html><body>
<script>
  const treffer = url.includes("https://api.resend.com/emails");
</script\t
 bar>
</body></html>
'''),
}

NEGATIV: dict[str, tuple[str, str]] = {
    "py_host_exakt": (".py", '''
from urllib.parse import urlsplit

def ist_api(url):
    teile = urlsplit(url)
    return teile.scheme == "https" and teile.hostname == "api.resend.com"
'''),
    "py_endswith_mit_punkt": (".py", '''
def subdomain(host):
    return host.endswith(".franksfinanzcheck.de")
'''),
    "py_startswith_mit_pfad": (".py", '''
def gateway(url):
    return url.startswith("https://franksfinanzcheck.de/go/")
'''),
    "py_kein_url_literal": (".py", '''
def enthaelt(text):
    return "Girokonto" in text
'''),
    "py_marker_im_string": (".py", '''
LEHRSTOFF = "# codeql[py/incomplete-url-substring-sanitization]"

def lauf():
    return len(LEHRSTOFF)
'''),
    "py_literal_rechts": (".py", '''
def lauf(hosts):
    return hosts in ("api.resend.com",)
'''),
    "js_origin_exakt": (".mjs", '''
export function istBlog(url) {
  return new URL(url).origin === "https://franksfinanzcheck.de";
}
'''),
    "js_endswith_mit_punkt": (".js", '''
const vorschau = (host) => host.endsWith(".pages.dev");
'''),
    "js_startswith_mit_slash": (".js", '''
const gateway = (url) => url.startsWith("https://franksfinanzcheck.de/");
'''),
    "js_url_in_kommentar": (".js", '''
// Beispiel: url.includes("https://franksfinanzcheck.de") wäre falsch
export const ok = (u) => new URL(u).hostname === "franksfinanzcheck.de";
'''),
    "js_url_in_string": (".js", '''
const hinweis = 'url.includes("https://franksfinanzcheck.de")';
export const zeige = () => hinweis;
'''),
    "js_division_kein_regex": (".js", '''
const quote = treffer / gesamt / 2;
export const ok = (u) => new URL(u).hostname === "franksfinanzcheck.de";
'''),
    "js_regex_mit_host": (".js", '''
const muster = /franksfinanzcheck\\.de/;
export const ok = (u) => muster.test(new URL(u).hostname);
'''),
    "html_json_ld": (".html", '''<!doctype html>
<html><head>
<script type="application/ld+json">{"@context": "https://schema.org"}</script>
</head><body>
<script>
  const ok = new URL(location.href).origin === "https://franksfinanzcheck.de";
</script>
</body></html>
'''),
    "html_hugo_template": (".html", '''<!doctype html>
<html><body>
<script>
  const basis = "{{ .Site.BaseURL }}";
  {{ if .Params.x }}
  const ok = new URL(basis).hostname === "franksfinanzcheck.de";
  {{ end }}
</script>
</body></html>
'''),
    # TypeScript-Syntax darf den Lexer nicht aus dem Tritt bringen: Generics,
    # `as`-Zusicherung, Division (kein Regex-Literal) und ein echtes Regex.
    "ts_host_exakt": (".ts", '''
export function erlaubt(origin: string): boolean {
  let url: URL;
  try { url = new URL(origin); } catch { return false; }
  const teile = origin.split("/") as string[];
  const quote = teile.length / 2 / 2;
  const muster = /https?:\\/\\/[a-z.]+/i;
  return url.protocol === "https:" && muster.test(origin) && quote >= 0
    && url.hostname.toLowerCase() === "franksfinanzcheck.de";
}
'''),
}

# Mustervergleich gegen die Query-Regeln: (Text, als URL erkannt?)
MUSTERPROBEN: tuple[tuple[str, bool], ...] = (
    ("https://franksfinanzcheck.de", True),
    ("api.pinterest.com", True),
    ("www.example.com", True),
    ("example.io:8080", True),
    (".example.org", True),
    ("//example.net", True),
    ("franksfinanzcheck.de", False),          # TLD nicht in der Query-Liste
    ("example.network", False),               # TLD nur als Präfix – kein Treffer
    ("Girokonto vergleichen", False),
    ("/go/gas/", False),
    ("api.pinterest.com/v5/pins", False),     # Pfad: nur über die Includes-Regel
)

MUSTERPROBEN_INCLUDES: tuple[tuple[str, bool], ...] = (
    ("https://franksfinanzcheck.de/go/gas", True),
    ("https://api.beispiel.com/v5/pins", True),
    ("https://franksfinanzcheck.de/go/gas?a=1", False),   # Query ist nicht abgedeckt
)

AUSNAHMEPROBEN: tuple[tuple[str, str, bool], ...] = (
    # (Zielwert, Sprache, gilt der Präfix-Vergleich als sicher?)
    ("https://franksfinanzcheck.de/go/", "python", True),
    ("https://franksfinanzcheck.de", "python", False),
    ("https://franksfinanzcheck.de/", "js", True),
    ("https://franksfinanzcheck.de:8080", "js", True),
    ("https://franksfinanzcheck.de", "js", False),
)

SUFFIXPROBEN: tuple[tuple[str, bool], ...] = (
    (".franksfinanzcheck.de", True),
    (".pages.dev", True),
    ("franksfinanzcheck.de", False),
    (".de", False),
)


def selftest() -> int:
    import tempfile

    fehler: list[str] = []

    # a) Musterlage – die Query-Regeln selbst
    for text, soll in MUSTERPROBEN:
        if sieht_aus_wie_url(text) != soll:
            fehler.append(f"Muster: „{text}“ müsste {'' if soll else 'KEIN '}URL-Ziel sein")
    for text, soll in MUSTERPROBEN_INCLUDES:
        if sieht_aus_wie_url(text, includes=True) != soll:
            fehler.append(f"Muster (includes): „{text}“ müsste "
                          f"{'' if soll else 'KEIN '}URL-Ziel sein")
    for text, sprache, soll in AUSNAHMEPROBEN:
        if praefix_ist_sicher(text, sprache=sprache) != soll:
            fehler.append(f"Ausnahme ({sprache}): Präfix „{text}“ falsch bewertet")
    for text, soll in SUFFIXPROBEN:
        if suffix_ist_sicher(text) != soll:
            fehler.append(f"Ausnahme: Suffix „{text}“ falsch bewertet")

    # b) Positiv- und Gegenproben auf echten Dateien
    with tempfile.TemporaryDirectory() as tmp:
        wurzel = Path(tmp)
        for name, (endung, code) in POSITIV.items():
            pfad = wurzel / f"pos_{name}{endung}"
            pfad.write_text(code, encoding="utf-8")
            befunde, lauffehler = pruefe([pfad], wurzel)
            if lauffehler:
                fehler.append(f"Positivprobe `{name}`: Analysefehler {lauffehler}")
            if not befunde:
                fehler.append(f"Positivprobe `{name}`: Fundstelle wurde NICHT erkannt")
        for name, (endung, code) in NEGATIV.items():
            pfad = wurzel / f"neg_{name}{endung}"
            pfad.write_text(code, encoding="utf-8")
            befunde, lauffehler = pruefe([pfad], wurzel)
            if lauffehler:
                fehler.append(f"Gegenprobe `{name}`: Analysefehler {lauffehler}")
            if befunde:
                fehler.append(f"Gegenprobe `{name}`: Fehlalarm {befunde[0].als_text()}")

        # c) Fail-closed: kaputter Quelltext ist niemals „sauber"
        for endung, inhalt in ((".py", "def kaputt(:\n"), (".js", "const s = 'offen\n")):
            pfad = wurzel / f"kaputt{endung}"
            pfad.write_text(inhalt, encoding="utf-8")
            _, lauffehler = pruefe([pfad], wurzel)
            if not lauffehler:
                fehler.append(f"Fail-closed: {endung}-Datei ohne Analysefehler durchgelassen")

        # d) Scope-Lücke: eine Endung, die CodeQL liest und diese Wache nicht,
        #    muss auffallen – sonst wächst der blinde Fleck still mit dem Repo.
        #    Geprüft wird in einem eigenen Verzeichnis OHNE Git, damit der
        #    Rückfall-Pfad (rglob) mitgeprüft wird und das echte Repository
        #    unberührt bleibt.
        luecke = wurzel / "komponente.vue"
        luecke.write_text("<template><div/></template>\n", encoding="utf-8")
        gemeldet = scopeluecken(wurzel)
        if "komponente.vue" not in gemeldet:
            fehler.append("Scope-Lücke: .vue-Datei wurde nicht als ungelesene Endung gemeldet")
        luecke.unlink()
        if scopeluecken(wurzel):
            fehler.append("Scope-Lücke: Fehlalarm auf einem Baum ohne ungelesene Endungen")

    if fehler:
        print("❌ URL-WACHE SELBSTTEST FEHLGESCHLAGEN:")
        for f in fehler:
            print(f"   - {f}")
        return 1
    print(f"✅ URL-Wache Selbsttest bestanden ({len(POSITIV)} Positivproben, "
          f"{len(NEGATIV)} Gegenproben, "
          f"{len(MUSTERPROBEN) + len(MUSTERPROBEN_INCLUDES) + len(AUSNAHMEPROBEN) + len(SUFFIXPROBEN)}"
          f" Musterproben, 2 Fail-closed-Proben, 2 Scope-Proben).")
    return 0


# --------------------------------------------------------------------------- #
#  8 · CLI
# --------------------------------------------------------------------------- #
HEILUNG = (
    "   Heilung: URL parsen und den HOST vergleichen – scripts/url_host.py\n"
    "   (`ist_host`, `ist_host_oder_subdomain`) bzw. in JavaScript\n"
    "   `new URL(x).hostname`. Für reine Text-/Codesuche: `nennt_host`.\n"
    "   Unterdrücken gilt nicht – siehe CODE-SCANNING-ALERT-83-DAUERHEILUNG-"
    "PREMIUM-2026-10-10.md."
)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="URL-Wache: findet unvollständige URL-Substring-Prüfungen "
                    "(Python, JavaScript/TypeScript, HTML).")
    p.add_argument("pfade", nargs="*", help="zu prüfende Dateien (Standard: ganzes Repository)")
    p.add_argument("--json", action="store_true", help="Befunde als JSON ausgeben")
    p.add_argument("--selftest", action="store_true", help="Eigenprüfung der Wache")
    p.add_argument("--quiet", action="store_true", help="nur Befunde, kein Erfolgs-Text")
    a = p.parse_args(argv)

    if a.selftest:
        return selftest()

    eigener_lauf = not a.pfade
    pfade = [Path(x) for x in a.pfade] if a.pfade else quelldateien(ROOT)
    befunde, fehler = pruefe(pfade, ROOT)
    befunde.sort(key=lambda b: (b.datei, b.zeile, b.form))

    # Eine Endung, die CodeQL liest und diese Wache nicht, ist eine Lücke –
    # und zwar eine, die sich wie „grün“ anfühlt. Sie zählt als Fehler
    # (Exit 2), nicht als Befund: Es ist kein Fund, sondern Blindheit.
    luecken = scopeluecken(ROOT) if eigener_lauf else []
    fehler = fehler + [
        f"{pfad}: Endung wird von CodeQL analysiert, von dieser Wache aber nicht "
        f"gelesen – Leser in url_substring_guard.py ergänzen (Scope-Lücke)"
        for pfad in luecken]

    if a.json:
        print(json.dumps({"befunde": [asdict(b) for b in befunde], "fehler": fehler,
                          "geprueft": len(pfade), "regeln": list(REGELN),
                          "scopeluecken": luecken},
                         ensure_ascii=False, indent=2))
        if fehler:
            return 2
        return 1 if befunde else 0

    for f in fehler:
        print(f"⚠ {f}")
    if befunde:
        unterdrueckt = [b for b in befunde if b.art == "unterdrueckung"]
        print(f"❌ URL-WACHE: {len(befunde)} Befund(e) in {len(pfade)} Dateien "
              f"({len(unterdrueckt)} davon nur per Kommentar unterdrückt – "
              f"das Default-Setup sieht sie trotzdem).")
        for b in befunde:
            marke = "UNTERDRÜCKT" if b.art == "unterdrueckung" else "PRÜFUNG"
            print(f"   [{marke}] {b.als_text()}")
        print()
        print(HEILUNG)
        return 2 if fehler else 1
    if not a.quiet:
        print(f"✅ URL-Wache: {len(pfade)} Dateien (Python, JavaScript/TypeScript, HTML), keine "
              f"unvollständige URL-Prüfung (Regeln: {REGEL_PY}, {REGEL_JS}).")
    return 0 if not fehler else 2


if __name__ == "__main__":
    sys.exit(main())
