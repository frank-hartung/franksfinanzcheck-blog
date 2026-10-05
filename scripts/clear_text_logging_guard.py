#!/usr/bin/env python3
"""Klartext-Wache – lokale Reproduktion der CodeQL-Abfragen zu Klartext-Geheimnissen.

WARUM ES DIESE WACHE GIBT (Code-Scanning-Alert #80, 05.10.2026)
---------------------------------------------------------------
Die `CodeQL-Sicherheitswache` (`.github/workflows/codeql.yml`) meldete auf `main`
„0 Funde" – und trotzdem standen in der Security-Tab offene Alerts. Grund: Der
Workflow filtert Fundstellen mit `# codeql[regel-id]`-Kommentar vor dem Upload,
und der Upload scheitert ohnehin, solange GitHubs **Default-Setup** aktiv ist
(„CodeQL analyses from advanced configurations cannot be processed when the
default setup is enabled"). Die Security-Tab zeigt also die Funde des
Default-Setups – und das kennt **weder** die `paths-ignore`-Liste **noch** die
Inline-Unterdrückungen. Jede unterdrückte Fundstelle blieb dort als offener
Alert stehen.

Konsequenz und Vertrag dieser Wache:

1. **Unterdrückung ist keine Heilung.** Eine Fundstelle mit
   `# codeql[py/clear-text-logging-sensitive-data]` gilt dieser Wache als
   eigenständiger Befund („unterdrückt statt geheilt") – genau so, wie das
   Default-Setup sie sieht.
2. **Kein toter Winkel.** Geprüft wird jede Python-Datei im Repository,
   auch die, die `.github/codeql/codeql-config.yml` für die Wache ausblendet.
3. **Vor dem Scanner, nicht nach ihm.** Die Prüfung läuft lokal in Sekunden
   (`python3 scripts/clear_text_logging_guard.py`) und im CI als eigenständiges,
   von CodeQL und dessen Upload unabhängiges Gate.

WAS GEPRÜFT WIRD
----------------
Nachbau von zwei Abfragen der CodeQL-Standard-Suite:

* `py/clear-text-logging-sensitive-data` – sensible Daten fließen in eine
  Log-/Druck-Senke (`print`, `logging.*`, `sys.stdout/stderr.write`).
* `py/clear-text-storage-sensitive-data` – sensible Daten fließen in eine
  unverschlüsselte Ablage (`f.write`, `json.dump`, `Path.write_text`).

Quellen, Senken und Namens-Heuristik folgen den Original-Definitionen:
  python/ql/lib/semmle/python/dataflow/new/SensitiveDataSources.qll
  python/ql/lib/semmle/python/security/dataflow/CleartextLoggingCustomizations.qll
  shared/concepts/codeql/concepts/internal/SensitiveDataHeuristics.qll

Die Heuristik ist rein **namensbasiert**: Es genügt, dass eine Variable, ein
Dict-Schlüssel, ein Parameter oder ein Funktionsname `secret`, `oauth`,
`api_key`, `password`, … heißt – der tatsächliche Inhalt spielt keine Rolle.
Deshalb ist die saubere Heilung fast immer ein **ehrlicher Name**: Wer nur
Variablen-NAMEN transportiert, nennt das Feld `pflicht_env` und nicht
`secrets`.

BEWUSSTE ABWEICHUNG (strenger bzw. milder als CodeQL)
-----------------------------------------------------
* strenger: Unterdrückungs-Kommentare zählen als Befund (s. o.).
* milder:  Aufrufe erklärter Entschärfer (`_redact`, `hash16`, `fingerprint`,
           `mask`, `digest`, …) brechen den Fluss. Das ist der Zweck dieser
           Funktionen; CodeQL erkennt sie über die `*args`-Verpackung ohnehin
           nicht als Fluss. Die Liste steht in `ENTSCHAERFER` – wer sie
           erweitert, muss die Funktion auch wirklich entschärfen lassen.

AUFRUF
------
    python3 scripts/clear_text_logging_guard.py              # ganzes Repo
    python3 scripts/clear_text_logging_guard.py --json       # maschinenlesbar
    python3 scripts/clear_text_logging_guard.py --selftest   # Eigenprüfung
    python3 scripts/clear_text_logging_guard.py pfad/a.py …  # einzelne Dateien

Exit-Code 0 = sauber, 1 = Befunde, 2 = Aufrufe/Parse-Fehler.
"""
from __future__ import annotations

import argparse
import ast
import io
import json
import re
import subprocess
import sys
import tokenize
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REGEL_LOGGING = "py/clear-text-logging-sensitive-data"
REGEL_STORAGE = "py/clear-text-storage-sensitive-data"

# --------------------------------------------------------------------------- #
#  1 · Namens-Heuristik – 1:1 aus SensitiveDataHeuristics.qll übersetzt
# --------------------------------------------------------------------------- #
# Python-`re` kennt keine Lookbehinds variabler Länge; die QL-Alternativen
# (?<!is|is_) werden deshalb als Kette fixer Lookbehinds geschrieben. Das ist
# semantisch identisch.

_SECRET = r"(?s).*((?<!is)(?<!is_)secret|(?<!un)(?<!un_)(?<!is)(?<!is_)trusted(?!_iter)|confidential).*"
_ACCOUNT_A = r"(?s).*(acc(ou)?nt|puid|user.?(name|id)|session.?(id|key)).*"
_ACCOUNT_B = r"(?s).*([uU]|^|_|[a-z](?=U))([uU][iI][dD]).*"
_PASSWORD = (
    r"(?s).*(pass(wd|word|code|.?phrase)(?!.*question)|(auth(entication|ori[sz]ation)?).?key|"
    r"oauth|api.?(key|tok)|([_-]|\b)mfa([_-]|\b)).*"
)
_CERT = r"(?s).*(cert)(?!.*(format|name|ification)).*"
_PRIVATE = (
    r"(?s).*("
    r"social.?security|employer.?identification|national.?insurance|resident.?id|"
    r"passport.?(num|no)|([_-]|\b)ssn([_-]|\b)|"
    r"post.?code|zip.?code|home.?addr|"
    r"(mob(ile)?|home).?(num|no|tel|phone)|(tel|fax|phone).?(num|no)|telephone|"
    r"emergency.?contact|"
    r"latitude|longitude|nationality|"
    r"(credit|debit|bank|visa).?(card|num|no|acc(ou)?nt)|(card|acc(ou)?nt).?(no|num|credit)|"
    r"routing.?num|"
    r"salary|billing|beneficiary|credit.?(rating|score)|([_-]|\b)(ccn|cvv|iban)([_-]|\b)|"
    r"security.?code|"
    r"birth.?da(te|y)|da(te|y).?(of.?)?birth|gender|([_-]|\b)sex([_-]|\b)|"
    r"medical|(health|care).?plan|healthkit|appointment|prescription|patient.?(id|record)|"
    r"blood.?(type|alcohol|glucose|pressure)|heart.?(rate|rhythm)|body.?(mass|fat)|"
    r"menstrua|pregnan|insulin|inhaler|"
    r"employ(er|ee)|spouse|maiden.?name|"
    r"mac.?addr"
    r").*"
)
_NICHT_SENSIBEL = (
    r"(?s).*([^\w$.-]|redact|censor|obfuscate|hash|md5|sha|random|(?<!unen)crypt|(?<!un)encode|"
    r"certain|concert|secretar|wildcard|coauthor|account(ant|ab|ing|ed)|(?<!pro)file|path|"
    r"([_-]|\b)url).*"
)

_FLAGS = re.IGNORECASE | re.DOTALL
_KLASSEN = (
    ("secret", re.compile(_SECRET, _FLAGS)),
    ("id", re.compile(_ACCOUNT_A, _FLAGS)),
    ("id", re.compile(_ACCOUNT_B, re.DOTALL)),
    ("password", re.compile(_PASSWORD, _FLAGS)),
    ("certificate", re.compile(_CERT, _FLAGS)),
    ("private", re.compile(_PRIVATE, _FLAGS)),
)
_NICHT = re.compile(_NICHT_SENSIBEL, _FLAGS)

# CleartextLogging nimmt `id` und `certificate` ausdrücklich NICHT als Quelle
# (siehe CleartextLoggingCustomizations.qll, SensitiveDataSourceAsSource).
_QUELL_KLASSEN = ("secret", "password", "private")


def klassifiziere(name: str) -> set[str]:
    """Alle Sensibilitätsklassen eines Namens (CodeQL `nameIndicatesSensitiveData`)."""
    if not isinstance(name, str) or not name or _NICHT.fullmatch(name):
        return set()
    return {klasse for klasse, rx in _KLASSEN if rx.fullmatch(name)}


def quellklassen(name: str) -> set[str]:
    """Nur die Klassen, die „Clear-text logging/storage" als Quelle wertet."""
    return klassifiziere(name) & set(_QUELL_KLASSEN)


# --------------------------------------------------------------------------- #
#  2 · Entschärfer, Senken, Fluss-Schritte
# --------------------------------------------------------------------------- #
# Funktionen, deren Rückgabe per Konstruktion KEIN Geheimnis mehr enthält.
ENTSCHAERFER = re.compile(
    r"(?i)^_?(redact|mask|maskiere|anonym\w*|pseudonym\w*|hash\w*|sha\d*|md5|blake\w*|hmac|"
    r"digest|hexdigest|fingerprint|fingerabdruck|kuerze\w*|truncate\w*|len|bool|int|float|"
    r"count|isinstance|hasattr)$"
)

# Reine Nicht-Träger: ihr Ergebnis ist ein Urteil, kein Inhalt.
URTEILS_FUNKTIONEN = {"len", "bool", "int", "float", "isinstance", "hasattr", "any", "all"}

STRING_METHODEN = {
    "format", "format_map", "join", "strip", "lstrip", "rstrip", "replace", "lower", "upper",
    "title", "capitalize", "casefold", "split", "rsplit", "splitlines", "encode", "decode",
    "removeprefix", "removesuffix", "zfill", "ljust", "rjust", "center", "partition",
    "rpartition", "expandtabs", "get", "pop", "copy", "values", "items", "setdefault",
    "append", "extend", "update", "add", "insert",
}

LOG_METHODEN = {"debug", "info", "warning", "warn", "error", "critical", "exception", "log"}
LOGGER_BASEN = {"logging", "log", "logger", "_log", "_logger", "LOG", "LOGGER"}

SCHREIB_METHODEN = {"write", "writelines", "write_text", "write_bytes"}


def attr_kette(node: ast.AST) -> str | None:
    """`sys.stdout.write` → "sys.stdout.write" (nur reine Namensketten)."""
    teile: list[str] = []
    while isinstance(node, ast.Attribute):
        teile.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        teile.append(node.id)
        return ".".join(reversed(teile))
    return None


def funktionsname(call: ast.Call) -> str | None:
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


@dataclass
class Befund:
    datei: str
    zeile: int
    regel: str
    art: str          # "fluss" | "unterdrueckung"
    senke: str
    quelle: str

    def als_text(self) -> str:
        # Absichtlich kein Quelltext-Auszug: Eine Sicherheitswache darf nicht
        # selbst einen auf der Fundzeile stehenden Klartextwert ins CI-Log kopieren.
        return f"{self.datei}:{self.zeile}: [{self.regel}] {self.senke} ← {self.quelle}"


# --------------------------------------------------------------------------- #
#  3 · Datei-Analyse
# --------------------------------------------------------------------------- #
class DateiAnalyse:
    """Fluss-Analyse einer Datei: Quellen → (Schritte) → Senken.

    Inhaltsmodell (bewusst nah an CodeQLs Datenfluss, siehe Modulkopf):

    * Der Taint einer Variablen ist eine Abbildung `Schlüssel → Begründung`.
      `"*"` steht für „das Objekt als Ganzes trägt sensible Daten" – wer es an
      eine Senke gibt (``print(obj)``, ``json.dumps(obj)``), leckt sie.
    * Ein Lesezugriff mit **bekanntem** Schlüssel (``d["token"]``) liefert nur
      den Taint genau dieses Schlüssels. Deshalb ist die Positiv-Whitelist
      (`public = {"state": health["state"], …}`) eine echte Entschärfung –
      und nicht bloß Kosmetik.
    * Ein Lesezugriff mit **unbekanntem** Schlüssel (``d[var]``, ``.items()``)
      liefert nichts: Der Inhalt ist statisch nicht bestimmbar, und CodeQL
      verfolgt ihn ebenfalls nicht. Wer so liest, muss die Ausgabe selbst
      kuratieren.
    * Tupel werden gliedweise behandelt (``a, b = f()``), damit ein sensibler
      Rückgabewert nicht seine harmlosen Geschwister vergiftet.
    """

    GANZ = "*"

    def __init__(self, pfad: Path, quelltext: str, wurzel: Path | None = None):
        self.pfad = pfad
        try:
            self.rel = str(pfad.relative_to(wurzel)) if wurzel else str(pfad)
        except ValueError:
            self.rel = str(pfad)
        self.baum = ast.parse(quelltext, filename=str(pfad))
        # Nur echte Python-Kommentare zählen. Marker in Docstrings, Test-Fixtures
        # oder Dokumentations-Strings sind Lehrstoff, keine Unterdrückung.
        self.unterdrueckungen = self._finde_unterdrueckungen(quelltext)
        self.funktionen: dict[str, ast.AST] = {}
        self.funktion_von_knoten: dict[ast.AST, str] = {}
        self.taint: dict[tuple[str, str], dict[str, str]] = {}
        self.rueckgabe: dict[str, dict[str, str]] = {}
        self.str_konstanten: dict[tuple[str, str], str] = {}
        self.dateiobjekte: set[tuple[str, str]] = set()
        self.loggerobjekte: set[tuple[str, str]] = set()
        self.befunde: list[Befund] = []
        self._indiziere()

    @staticmethod
    def _finde_unterdrueckungen(quelltext: str) -> dict[int, str]:
        """Verbotene Clear-Text-Marker als Zeile → Regel, stringsicher."""
        gefunden: dict[int, str] = {}
        try:
            tokens = tokenize.generate_tokens(io.StringIO(quelltext).readline)
            for token in tokens:
                if token.type != tokenize.COMMENT:
                    continue
                for regel in (REGEL_LOGGING, REGEL_STORAGE):
                    if f"codeql[{regel}]" in token.string:
                        gefunden[token.start[0]] = regel
        except (IndentationError, tokenize.TokenError):
            # ast.parse() liefert für syntaktisch defekte Dateien anschließend
            # den fail-closed Parse-Fehler; hier wird nichts weichgezeichnet.
            pass
        return gefunden

    # -- Gerüst ------------------------------------------------------------ #
    def _indiziere(self) -> None:
        def lauf(knoten: ast.AST, scope: str) -> None:
            for kind in ast.iter_child_nodes(knoten):
                if isinstance(kind, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    q = f"{scope}.{kind.name}"
                    self.funktionen[q] = kind
                    self.funktion_von_knoten[kind] = q
                    lauf(kind, q)
                elif isinstance(kind, ast.ClassDef):
                    lauf(kind, f"{scope}.{kind.name}")
                else:
                    lauf(kind, scope)

        lauf(self.baum, "")

    def _knoten(self):
        def lauf(knoten: ast.AST, scope: str):
            for kind in ast.iter_child_nodes(knoten):
                if isinstance(kind, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    yield from lauf(kind, self.funktion_von_knoten[kind])
                elif isinstance(kind, ast.ClassDef):
                    yield from lauf(kind, f"{scope}.{kind.name}")
                else:
                    yield scope, kind
                    yield from lauf(kind, scope)

        yield from lauf(self.baum, "")

    def _kandidaten(self, name: str | None) -> list[str]:
        if not name:
            return []
        return [q for q in self.funktionen if q.rsplit(".", 1)[-1] == name]

    # -- Hilfen für das Inhaltsmodell --------------------------------------- #
    @staticmethod
    def _ganz(taint: dict[str, str]) -> dict[str, str]:
        """Flacht einen Taint ein: jede Spur macht das Ergebnis als Ganzes heiß."""
        if not taint:
            return {}
        grund = taint.get(DateiAnalyse.GANZ) or next(iter(taint.values()))
        return {DateiAnalyse.GANZ: grund}

    @staticmethod
    def _misch(ziel: dict[str, str], quelle: dict[str, str]) -> dict[str, str]:
        for k, v in quelle.items():
            ziel.setdefault(k, v)
        return ziel

    def _var_taint(self, scope: str, name: str) -> dict[str, str]:
        return self.taint.get((scope, name)) or self.taint.get(("", name)) or {}

    def _setze(self, scope: str, name: str, taint: dict[str, str]) -> None:
        if not taint:
            return
        self._misch(self.taint.setdefault((scope, name), {}), taint)

    def _konst_str(self, knoten: ast.AST | None, scope: str) -> str | None:
        if isinstance(knoten, ast.Constant) and isinstance(knoten.value, str):
            return knoten.value
        if isinstance(knoten, ast.Name):
            return self.str_konstanten.get((scope, knoten.id))
        return None

    # -- Quellen ------------------------------------------------------------ #
    def quelle(self, knoten: ast.AST, scope: str) -> str | None:
        """Beschreibung, falls `knoten` selbst eine sensible Quelle ist."""
        if isinstance(knoten, ast.Attribute):
            if quellklassen(knoten.attr):
                return f"Attribut `.{knoten.attr}`"
            return None
        if isinstance(knoten, ast.Subscript):
            schluessel = self._konst_str(knoten.slice, scope)
            if schluessel and quellklassen(schluessel):
                return f'Schlüssel `["{schluessel}"]`'
            return None
        if isinstance(knoten, ast.Call):
            if isinstance(knoten.func, ast.Attribute) and knoten.func.attr == "get" and knoten.args:
                schluessel = self._konst_str(knoten.args[0], scope)
                if schluessel and quellklassen(schluessel):
                    return f'Lookup `.get("{schluessel}")`'
            if attr_kette(knoten.func) == "getpass.getpass":
                return "getpass.getpass()"
            name = funktionsname(knoten)
            if name and not ENTSCHAERFER.match(name) and quellklassen(name):
                return f"Aufruf `{name}()`"
        return None

    # -- Fluss --------------------------------------------------------------- #
    def expr_taint(self, knoten: ast.AST | None, scope: str) -> dict[str, str]:
        if knoten is None:
            return {}
        direkt = self.quelle(knoten, scope)
        if direkt:
            return {self.GANZ: direkt}

        if isinstance(knoten, ast.Name):
            return dict(self._var_taint(scope, knoten.id))

        if isinstance(knoten, (ast.JoinedStr, ast.FormattedValue, ast.BinOp, ast.BoolOp,
                               ast.Starred, ast.Await)):
            for kind in ast.iter_child_nodes(knoten):
                if isinstance(kind, ast.expr):
                    treffer = self.expr_taint(kind, scope)
                    if treffer:
                        return self._ganz(treffer)
            return {}

        if isinstance(knoten, ast.IfExp):
            # Die Bedingung ist ein Urteil, kein Inhalt – nur die Zweige zählen.
            return self._ganz(self.expr_taint(knoten.body, scope)
                              or self.expr_taint(knoten.orelse, scope))

        if isinstance(knoten, (ast.Tuple, ast.List, ast.Set)):
            ergebnis: dict[str, str] = {}
            for i, teil in enumerate(knoten.elts):
                treffer = self.expr_taint(teil, scope)
                if treffer:
                    grund = self._ganz(treffer)[self.GANZ]
                    ergebnis.setdefault(str(i), grund)
                    ergebnis.setdefault(self.GANZ, grund)
            return ergebnis

        if isinstance(knoten, ast.Dict):
            ergebnis = {}
            for schluessel, wert in zip(knoten.keys, knoten.values):
                treffer = self.expr_taint(wert, scope) if wert is not None else {}
                if schluessel is None and wert is not None:      # {**anderes}
                    treffer = self.expr_taint(wert, scope)
                if not treffer:
                    continue
                grund = self._ganz(treffer)[self.GANZ]
                name = self._konst_str(schluessel, scope) if schluessel is not None else None
                if name:
                    ergebnis.setdefault(name, grund)
                ergebnis.setdefault(self.GANZ, grund)
            return ergebnis

        if isinstance(knoten, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            for teil in [knoten.elt] + [g.iter for g in knoten.generators]:
                treffer = self.expr_taint(teil, scope)
                if treffer:
                    return self._ganz(treffer)
            return {}

        if isinstance(knoten, ast.DictComp):
            for teil in [knoten.key, knoten.value] + [g.iter for g in knoten.generators]:
                treffer = self.expr_taint(teil, scope)
                if treffer:
                    return self._ganz(treffer)
            return {}

        if isinstance(knoten, ast.Subscript):
            basis = self.expr_taint(knoten.value, scope)
            if not basis:
                return {}
            schluessel = self._konst_str(knoten.slice, scope)
            if schluessel is None and isinstance(knoten.slice, ast.Constant) \
                    and isinstance(knoten.slice.value, int):
                schluessel = str(knoten.slice.value)
            if schluessel is not None:
                return {self.GANZ: basis[schluessel]} if schluessel in basis else {}
            if isinstance(knoten.slice, ast.Slice):
                return self._ganz(basis)
            # Unbekannter Schlüssel: statisch nicht bestimmbar → kein Fluss.
            return {}

        if isinstance(knoten, ast.Attribute):
            return {}

        if isinstance(knoten, ast.Call):
            return self._aufruf_taint(knoten, scope)

        return {}

    def _aufruf_taint(self, knoten: ast.Call, scope: str) -> dict[str, str]:
        name = funktionsname(knoten)
        if name and (ENTSCHAERFER.match(name) or name in URTEILS_FUNKTIONEN):
            return {}
        kette = attr_kette(knoten.func)

        if kette in ("json.dumps", "json.loads", "pprint.pformat", "yaml.safe_dump",
                     "yaml.dump", "textwrap.dedent", "textwrap.shorten"):
            for arg in knoten.args:
                treffer = self.expr_taint(arg, scope)
                if treffer:
                    return self._ganz(treffer)
            return {}

        if kette in ("copy.copy", "copy.deepcopy") or name in ("dict", "list", "tuple", "set"):
            for arg in knoten.args:
                treffer = self.expr_taint(arg, scope)
                if treffer:
                    return dict(treffer)
            for kw in knoten.keywords:
                treffer = self.expr_taint(kw.value, scope)
                if treffer:
                    return dict(treffer) if kw.arg is None else {self.GANZ: self._ganz(treffer)[self.GANZ]}
            return {}

        if name in ("str", "repr", "format", "sorted", "reversed"):
            for arg in knoten.args:
                treffer = self.expr_taint(arg, scope)
                if treffer:
                    return self._ganz(treffer)
            return {}

        if isinstance(knoten.func, ast.Attribute):
            methode = knoten.func.attr
            if methode == "get" and knoten.args:
                basis = self.expr_taint(knoten.func.value, scope)
                if not basis:
                    return {}
                schluessel = self._konst_str(knoten.args[0], scope)
                if schluessel is not None:
                    return {self.GANZ: basis[schluessel]} if schluessel in basis else {}
                return {}
            if methode in ("items", "keys", "values", "pop", "popitem"):
                # Inhalt unbekannter Schlüssel – siehe Inhaltsmodell im Klassenkopf.
                return {}
            if methode in STRING_METHODEN:
                for teil in [knoten.func.value] + list(knoten.args) + [kw.value for kw in knoten.keywords]:
                    treffer = self.expr_taint(teil, scope)
                    if treffer:
                        return self._ganz(treffer)
                return {}

        for q in self._kandidaten(name):
            if q in self.rueckgabe:
                return dict(self.rueckgabe[q])
        return {}

    # -- Senken ---------------------------------------------------------------- #
    def log_senke(self, knoten: ast.Call,
                  scope: str) -> tuple[str, list[ast.expr]] | None:
        f = knoten.func
        if isinstance(f, ast.Name) and f.id == "print":
            return "print()", list(knoten.args)
        kette = attr_kette(f)
        if kette in ("sys.stdout.write", "sys.stderr.write"):
            return f"{kette}()", knoten.args[:1]
        if isinstance(f, ast.Attribute) and f.attr in LOG_METHODEN:
            basis = attr_kette(f.value) or ""
            kurz = basis.rsplit(".", 1)[-1]
            ist_logger = (kurz in LOGGER_BASEN or kurz.lower().endswith("logger")
                          or (scope, kurz) in self.loggerobjekte
                          or ("", kurz) in self.loggerobjekte)
            if ist_logger:
                return f"{basis}.{f.attr}()", list(knoten.args)
        return None

    def speicher_senke(self, knoten: ast.Call, scope: str) -> tuple[str, list[ast.expr]] | None:
        f = knoten.func
        kette = attr_kette(f)
        if kette in ("json.dump", "yaml.safe_dump", "yaml.dump", "pickle.dump") and knoten.args:
            return f"{kette}()", knoten.args[:1]
        if isinstance(f, ast.Attribute) and f.attr in SCHREIB_METHODEN and knoten.args:
            if f.attr in ("write_text", "write_bytes"):
                return f".{f.attr}()", knoten.args[:1]
            basis = f.value
            if isinstance(basis, ast.Name) and (scope, basis.id) in self.dateiobjekte:
                return f"{basis.id}.{f.attr}()", knoten.args[:1]
            if isinstance(basis, ast.Call) and funktionsname(basis) == "open":
                return f"open().{f.attr}()", knoten.args[:1]
        return None

    # -- Unterdrückungen -------------------------------------------------------- #
    def _unterdrueckungsbefunde(self) -> list[Befund]:
        """Jeder echte Marker ist selbst ein Befund – auch ohne Taint-Fluss."""
        return [Befund(
            datei=self.rel,
            zeile=zeile,
            regel=regel,
            art="unterdrueckung",
            senke="CodeQL-Unterdrückung",
            quelle="verbotener Inline-Kommentar",
        ) for zeile, regel in sorted(self.unterdrueckungen.items())]

    # -- Lauf -------------------------------------------------------------------- #
    def lauf(self) -> list[Befund]:
        for scope, knoten in self._knoten():
            if isinstance(knoten, ast.Assign) and isinstance(knoten.value, ast.Constant) \
                    and isinstance(knoten.value.value, str):
                for ziel in knoten.targets:
                    if isinstance(ziel, ast.Name):
                        self.str_konstanten[(scope, ziel.id)] = knoten.value.value
            if isinstance(knoten, ast.Assign) and isinstance(knoten.value, ast.Call) \
                    and funktionsname(knoten.value) == "open":
                for ziel in knoten.targets:
                    if isinstance(ziel, ast.Name):
                        self.dateiobjekte.add((scope, ziel.id))
            if isinstance(knoten, ast.Assign) and isinstance(knoten.value, ast.Call) \
                    and funktionsname(knoten.value) in ("getLogger", "Logger"):
                for ziel in knoten.targets:
                    if isinstance(ziel, ast.Name):
                        self.loggerobjekte.add((scope, ziel.id))
            if isinstance(knoten, ast.AnnAssign) and isinstance(knoten.target, ast.Name) \
                    and isinstance(knoten.annotation, (ast.Name, ast.Attribute)) \
                    and (attr_kette(knoten.annotation) or getattr(
                        knoten.annotation, "id", "")).rsplit(".", 1)[-1] == "Logger":
                self.loggerobjekte.add((scope, knoten.target.id))
            if isinstance(knoten, ast.withitem) and isinstance(knoten.context_expr, ast.Call) \
                    and funktionsname(knoten.context_expr) == "open" \
                    and isinstance(knoten.optional_vars, ast.Name):
                self.dateiobjekte.add((scope, knoten.optional_vars.id))

        # Sensible Parameter sind laut CodeQL selbst Quellen.
        for q, fn in self.funktionen.items():
            args = fn.args
            alle = (list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs)
                    + ([args.vararg] if args.vararg else [])
                    + ([args.kwarg] if args.kwarg else []))
            for a in alle:
                if a and quellklassen(a.arg):
                    self._setze(q, a.arg, {self.GANZ: f"Parameter `{a.arg}`"})

        # Monotone Fixpunkt-Iteration statt einer willkürlichen Tiefengrenze:
        # Auch ein neuer Fluss durch mehr als acht lokale Helfer bleibt sichtbar.
        while True:
            vorher = self._zustandsgroesse()
            self._durchlauf(melden=False)
            if self._zustandsgroesse() == vorher:
                break
        self.befunde = self._unterdrueckungsbefunde()
        self._durchlauf(melden=True)
        return self.befunde

    def _zustandsgroesse(self) -> int:
        return (sum(len(v) for v in self.taint.values())
                + sum(len(v) for v in self.rueckgabe.values()))

    def _zuweisung(self, scope: str, ziel: ast.AST, taint: dict[str, str]) -> None:
        """Weist `taint` einem Ziel zu – Tupel gliedweise."""
        if isinstance(ziel, ast.Name):
            self._setze(scope, ziel.id, taint)
            return
        if isinstance(ziel, (ast.Tuple, ast.List)):
            for i, teil in enumerate(ziel.elts):
                anteil = {}
                if str(i) in taint:
                    anteil = {self.GANZ: taint[str(i)]}
                elif self.GANZ in taint and not any(k.isdigit() for k in taint):
                    anteil = {self.GANZ: taint[self.GANZ]}
                self._zuweisung(scope, teil, anteil)
            return
        if isinstance(ziel, ast.Starred):
            self._zuweisung(scope, ziel.value, taint)
            return
        if isinstance(ziel, ast.Subscript) and isinstance(ziel.value, ast.Name) and taint:
            grund = self._ganz(taint)[self.GANZ]
            schluessel = self._konst_str(ziel.slice, scope)
            eintrag = {self.GANZ: grund}
            if schluessel:
                eintrag[schluessel] = grund
            self._setze(scope, ziel.value.id, eintrag)
            return
        if isinstance(ziel, ast.Attribute):
            return

    def _durchlauf(self, melden: bool) -> None:
        for scope, knoten in self._knoten():
            if isinstance(knoten, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.NamedExpr)):
                ziele = knoten.targets if isinstance(knoten, ast.Assign) else [knoten.target]
                wert = knoten.value
                if wert is None or isinstance(wert, ast.Lambda):
                    continue
                taint = self.expr_taint(wert, scope)
                for ziel in ziele:
                    namen = [n.id for n in ast.walk(ziel) if isinstance(n, ast.Name)]
                    sensibel = next((n for n in namen if quellklassen(n)), None)
                    if sensibel and isinstance(ziel, ast.Name):
                        # CodeQL: die Zuweisung an einen sensiblen Namen IST die Quelle.
                        self._setze(scope, ziel.id, {self.GANZ: f"Zuweisung an `{sensibel}`"})
                    elif sensibel and isinstance(ziel, (ast.Tuple, ast.List)):
                        for teil in ziel.elts:
                            if isinstance(teil, ast.Name) and quellklassen(teil.id):
                                self._setze(scope, teil.id,
                                            {self.GANZ: f"Zuweisung an `{teil.id}`"})
                        self._zuweisung(scope, ziel, taint)
                    else:
                        self._zuweisung(scope, ziel, taint)
            elif isinstance(knoten, (ast.For, ast.AsyncFor)):
                namen = [n.id for n in ast.walk(knoten.target) if isinstance(n, ast.Name)]
                sensibel = next((n for n in namen if quellklassen(n)), None)
                if sensibel:
                    for n in namen:
                        if quellklassen(n):
                            self._setze(scope, n, {self.GANZ: f"Schleifenziel `{n}`"})
                taint = self.expr_taint(knoten.iter, scope)
                if taint:
                    # Eine Liste von Tupeln mit konstanter Struktur lässt sich
                    # gliedweise auflösen (`for name, key in (("a", K1), …)`).
                    # Sonst gilt: Wer über heiße Daten iteriert, hält Heißes in
                    # der Hand – genau diesen Fluss meldet CodeQL bei
                    # `for code, msg in checks:`.
                    if isinstance(knoten.iter, (ast.Tuple, ast.List)) \
                            and isinstance(knoten.target, (ast.Tuple, ast.List)):
                        for element in knoten.iter.elts:
                            self._zuweisung(scope, knoten.target,
                                            self.expr_taint(element, scope))
                    else:
                        for n in ast.walk(knoten.target):
                            if isinstance(n, ast.Name):
                                self._setze(scope, n.id, self._ganz(taint))
            elif isinstance(knoten, ast.withitem) and knoten.optional_vars is not None:
                namen = [n.id for n in ast.walk(knoten.optional_vars) if isinstance(n, ast.Name)]
                sensibel = next((n for n in namen if quellklassen(n)), None)
                if sensibel:
                    self._setze(scope, sensibel, {self.GANZ: f"with-Ziel `{sensibel}`"})
                else:
                    self._zuweisung(scope, knoten.optional_vars,
                                    self.expr_taint(knoten.context_expr, scope))
            elif isinstance(knoten, ast.Return):
                if knoten.value is not None and scope:
                    taint = self.expr_taint(knoten.value, scope)
                    if taint:
                        self._misch(self.rueckgabe.setdefault(scope, {}), taint)
            elif isinstance(knoten, ast.Call):
                self._aufruf(knoten, scope, melden)

    def _aufruf(self, knoten: ast.Call, scope: str, melden: bool) -> None:
        name = funktionsname(knoten)
        for q in self._kandidaten(name):
            fn = self.funktionen[q]
            params = [p.arg for p in (list(fn.args.posonlyargs) + list(fn.args.args)
                                      + list(fn.args.kwonlyargs))]
            if params and params[0] in ("self", "cls"):
                params = params[1:]
            for i, arg in enumerate(knoten.args):
                if i < len(params):
                    self._setze(q, params[i], self.expr_taint(arg, scope))
            for kw in knoten.keywords:
                if kw.arg:
                    self._setze(q, kw.arg, self.expr_taint(kw.value, scope))
        # Mutierende Container-Aufrufe: d.update(x) / liste.append(x)
        if isinstance(knoten.func, ast.Attribute) and isinstance(knoten.func.value, ast.Name) \
                and knoten.func.attr in ("update", "append", "extend", "add", "insert",
                                         "setdefault"):
            for arg in knoten.args:
                taint = self.expr_taint(arg, scope)
                if taint:
                    self._setze(scope, knoten.func.value.id, self._ganz(taint))
        if not melden:
            return
        for regel, treffer_senke in ((REGEL_LOGGING, self.log_senke(knoten, scope)),
                                     (REGEL_STORAGE, self.speicher_senke(knoten, scope))):
            if not treffer_senke:
                continue
            senke, argumente = treffer_senke
            for arg in argumente:
                taint = self.expr_taint(arg, scope)
                if not taint:
                    continue
                self.befunde.append(Befund(
                    datei=self.rel,
                    zeile=knoten.lineno,
                    regel=regel,
                    # Ein naher Marker wird bereits als eigenständiger Befund
                    # erfasst; der gefährliche Datenfluss bleibt zusätzlich sichtbar.
                    art="fluss",
                    senke=senke,
                    quelle=self._ganz(taint)[self.GANZ],
                ))
                break


# --------------------------------------------------------------------------- #
#  4 · Repository-Lauf
# --------------------------------------------------------------------------- #
def python_dateien(wurzel: Path) -> list[Path]:
    """Alle relevanten Python-Dateien – versioniert plus neue, nicht ignorierte.

    Neue Dateien müssen schon vor ihrem ersten Commit sichtbar sein; nur
    `git ls-files '*.py'` zu verwenden wäre lokal ein gefährlicher Blindflug.
    """
    try:
        roh = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others",
             "--exclude-standard", "--", "*.py"],
            cwd=wurzel, capture_output=True, text=True, timeout=120,
            check=True).stdout
        dateien = [wurzel / p for p in roh.split("\0") if p.strip()]
        if dateien:
            return sorted(set(dateien))
    except (OSError, subprocess.SubprocessError):
        pass
    return sorted(p for p in wurzel.rglob("*.py")
                  if not any(teil in {".git", "node_modules", "__pycache__", ".venv"}
                             for teil in p.parts))


def pruefe(pfade, wurzel: Path = ROOT) -> tuple[list[Befund], list[str]]:
    befunde: list[Befund] = []
    fehler: list[str] = []
    for pfad in pfade:
        pfad = Path(pfad)
        try:
            quelltext = pfad.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            fehler.append(f"{pfad}: nicht lesbar ({exc.__class__.__name__})")
            continue
        try:
            befunde.extend(DateiAnalyse(pfad, quelltext, wurzel).lauf())
        except SyntaxError as exc:
            fehler.append(f"{pfad}:{exc.lineno}: Syntaxfehler – nicht analysierbar")
    return befunde, fehler


# --------------------------------------------------------------------------- #
#  5 · Eigenprüfung (Positiv- UND Gegenprobe)
# --------------------------------------------------------------------------- #
DIAGNOSE_GIFT = "DARF-NIE-IN-DER-WACHEN-DIAGNOSE-STEHEN-8E7C"

POSITIV = {
    "quelle_lookup": '''
import json
def bericht(kanal):
    eintrag = {"secrets": list(kanal.get("secrets") or [])}
    print(json.dumps(eintrag))
''',
    "quelle_funktionsname": '''
def c9_secret_leak(texte):
    return [("C9", f"{name}: Befund") for name in texte]

def main(texte):
    for code, msg in c9_secret_leak(texte):
        print(f"{code} {msg}")
''',
    "quelle_zuweisung": '''
import os
def lauf():
    api_key = os.environ.get("GROQ_KEY", "")
    print(f"Key: {api_key}")
''',
    "quelle_parameter": '''
def sende(client_secret):
    print("Zugang: " + client_secret)
''',
    "senke_logging": '''
import logging
def lauf(cfg):
    logging.info("Zugang %s", cfg["app_secret"])
''',
    "senke_speicher": '''
import json
def schreibe(cfg, pfad):
    with open(pfad, "w", encoding="utf-8") as fh:
        json.dump({"wert": cfg.get("client_secret")}, fh)
''',
    "unterdrueckung_zaehlt_auch_ohne_fluss": '''
def lauf():
    # codeql[py/clear-text-logging-sensitive-data]
    print("harmlos, aber der verbotene Marker muss trotzdem rot werden")
''',
    "logger_alias": '''
import logging
audit = logging.getLogger(__name__)
def lauf(cfg):
    audit.info("Zugang %s", cfg.get("app_secret"))
''',
    "tiefe_helferkette": '''
def f0(x): return f1(x)
def f1(x): return f2(x)
def f2(x): return f3(x)
def f3(x): return f4(x)
def f4(x): return f5(x)
def f5(x): return f6(x)
def f6(x): return f7(x)
def f7(x): return f8(x)
def f8(x): return f9(x)
def f9(x): return x
def lauf(cfg):
    print(f0(cfg.get("app_secret")))
''',
    "diagnose_bleibt_wertfrei": f'''
api_key = "{DIAGNOSE_GIFT}"
print(api_key)
''',
}

NEGATIV = {
    "nur_namen": '''
import json
def bericht(kanal):
    eintrag = {"pflicht_env": list(kanal.get("pflicht_env") or [])}
    print(json.dumps(eintrag))
''',
    "entschaerft": '''
def hash16(wert):
    import hashlib
    return hashlib.sha256(wert.encode()).hexdigest()[:16]

def lauf(cfg):
    print(f"Empfänger {hash16(cfg['app_secret'])}")
''',
    "nur_vorhandensein": '''
def api_token():
    import os
    return os.environ.get("AWIN_API_TOKEN", "")

def status():
    print(f"Token: {'gesetzt' if api_token() else 'fehlt'}")
''',
    "klassifikation_id_ist_keine_quelle": '''
def lauf(sitzung):
    print(sitzung.get("session_id"))
''',
    "hash_name_ist_nicht_sensibel": '''
def lauf(cfg):
    print(cfg.get("secret_hash"))
''',
    "marker_in_string_ist_keine_unterdrueckung": '''
LEHRSTOFF = "# codeql[py/clear-text-logging-sensitive-data]"
def lauf():
    print("harmlos")
''',
}


def selftest() -> int:
    import tempfile

    fehler: list[str] = []

    # a) Namens-Heuristik
    muss_sensibel = ["secrets", "fehlende_secrets", "app_secret", "GROQ_API_KEY", "client_secret",
                     "oauth_token", "password", "c9_secret_leak", "api_key", "passphrase"]
    darf_nicht = ["pflicht_env", "fehlende_env", "token", "GITHUB_TOKEN", "access_token",
                  "secret_hash", "zugangsalter_rot", "session_id", "secret path"]
    for name in muss_sensibel:
        if not quellklassen(name):
            fehler.append(f"Heuristik stumpf: `{name}` müsste sensibel sein")
    for name in darf_nicht:
        if quellklassen(name) and name != "session_id":
            fehler.append(f"Heuristik überempfindlich: `{name}` ist keine Quelle")
    if quellklassen("session_id"):
        fehler.append("Klassifikation `id` darf keine Quelle sein (CleartextLogging)")

    # b) Positiv- und Gegenprobe der Fluss-Analyse
    with tempfile.TemporaryDirectory() as tmp:
        for name, code in POSITIV.items():
            pfad = Path(tmp) / f"pos_{name}.py"
            pfad.write_text(code, encoding="utf-8")
            befunde, _ = pruefe([pfad], Path(tmp))
            if not befunde:
                fehler.append(f"Positivprobe `{name}`: Fluss wurde NICHT erkannt")
            diagnose = json.dumps([asdict(b) for b in befunde], ensure_ascii=False)
            if DIAGNOSE_GIFT in diagnose:
                fehler.append(f"Positivprobe `{name}`: Diagnose gibt den Klartextwert aus")
        for name, code in NEGATIV.items():
            pfad = Path(tmp) / f"neg_{name}.py"
            pfad.write_text(code, encoding="utf-8")
            befunde, _ = pruefe([pfad], Path(tmp))
            if befunde:
                fehler.append(f"Gegenprobe `{name}`: Fehlalarm {befunde[0].als_text()}")

    if fehler:
        print("❌ KLARTEXT-WACHE SELBSTTEST FEHLGESCHLAGEN:")
        for f in fehler:
            print(f"   - {f}")
        return 1
    print(f"✅ Klartext-Wache Selbsttest bestanden "
          f"({len(POSITIV)} Positivproben, {len(NEGATIV)} Gegenproben, "
          f"{len(muss_sensibel) + len(darf_nicht)} Namensproben).")
    return 0


# --------------------------------------------------------------------------- #
#  6 · CLI
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Klartext-Wache: findet Klartext-Logging/-Speicherung sensibler Daten.")
    p.add_argument("pfade", nargs="*", help="zu prüfende Dateien (Standard: alle versionierten .py)")
    p.add_argument("--json", action="store_true", help="Befunde als JSON ausgeben")
    p.add_argument("--selftest", action="store_true", help="Eigenprüfung der Wache")
    p.add_argument("--quiet", action="store_true", help="nur Befunde, kein Erfolgs-Text")
    a = p.parse_args(argv)

    if a.selftest:
        return selftest()

    pfade = [Path(x) for x in a.pfade] if a.pfade else python_dateien(ROOT)
    befunde, fehler = pruefe(pfade, ROOT)

    if a.json:
        print(json.dumps({"befunde": [asdict(b) for b in befunde], "fehler": fehler,
                          "geprueft": len(pfade)}, ensure_ascii=False, indent=2))
        if fehler:
            return 2
        return 1 if befunde else 0

    for f in fehler:
        print(f"⚠ {f}")
    if befunde:
        unterdrueckt = [b for b in befunde if b.art == "unterdrueckung"]
        print(f"❌ KLARTEXT-WACHE: {len(befunde)} Befund(e) in {len(pfade)} Dateien "
              f"({len(unterdrueckt)} davon nur per Kommentar unterdrückt – "
              f"das Default-Setup sieht sie trotzdem).")
        for b in befunde:
            marke = "UNTERDRÜCKT" if b.art == "unterdrueckung" else "FLUSS"
            print(f"   [{marke}] {b.als_text()}")
        print("\n   Heilung: den NAMEN ehrlich machen (z. B. `pflicht_env` statt `secrets`),")
        print("   den Wert entschärfen (Hash/Fingerabdruck) oder die Ausgabe weglassen.")
        print("   Unterdrücken gilt nicht – siehe CODE-SCANNING-ALERT-80-PREMIUM-2026-10-05.md.")
        return 2 if fehler else 1
    if not a.quiet:
        print(f"✅ Klartext-Wache: {len(pfade)} Python-Dateien, keine Klartext-Fundstelle "
              f"(Regeln: {REGEL_LOGGING}, {REGEL_STORAGE}).")
    return 0 if not fehler else 2


if __name__ == "__main__":
    sys.exit(main())
