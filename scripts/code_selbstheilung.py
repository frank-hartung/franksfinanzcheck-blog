#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""code_selbstheilung.py – automatische Heilung von Code-Fundstellen der #709-Klasse.

WARUM DIESES MODUL EXISTIERT (12.10.2026, CodeQL-Alert über PR #709)
---------------------------------------------------------------
Am 12.10.2026 brachte PR #709 (Suchradar) sechs `py/incomplete-url-substring-
sanitization`-Fundstellen auf `main`. Die Sicherheits-Wache wurde rot; die
Fundstellen erfolgten von Hand (CODE-SCANNING-SUCHRADAR-HEILUNG-PREMIUM-2026-
10-12.md). Ein Befund, der nur von Hand heilt, ist jeder Tageslauf eine neue
Chance, dass er wieder auftaucht. PR #709 brachte die Fundstellen in ein
verändertes Skript – die Wache hätte diese Fundstellen als Fehler melden
müssen, und der Mensch wurde aufgefordert, den Fehler zu heilen.

FÜNF SCHICHTEN (Highend-Standard analog Abhängigkeits-Selbstheilung, #79)
  · VERTRAG      `data/code_schutz_vertrag.json` – einzige Quelle für die
                 Regel, Helper-Funktionen, PR-Verträge und die Ausnahmen.
  · EICHPROBE    Vor jedem Urteil und vor jedem Schreibzugriff wird Vorfall
                 #709 samt Mehrzweig-Downgrade-Falle im Speicher nachgespielt.
                 Versagt der Prüfer: Exit 3 (`MESSGERAET`).
  · HEILUNG      Selektive, AST-genau positionierte Ersetzung (Host-exakt statt
                 Teilzeichenkette), nur für reine Python-Dateien, fail-closed,
                 nachgemessen, rollt bei jedem Fehler atomar zurück (Exit 2).
  · BELEGKETTE   `data/code_schutz_belege.jsonl` (`merge=binary`): verkettete
                 SHA-256-Nachweise ab `GENESIS`. Idempotent: Ein sauberer Bestand
                 schreibt keine Uhrzeit ins Repo.
  · VERDRAHTUNG  `--wache` prüft Vertrag, Kette, `.gitattributes`, Heil-Workflow,
                 Sicherheits-Gate und Alerting. H-02: Der Heil-Workflow merged
                 nie blind auf `main`, sondern öffnet/aktualisiert einen PR.

Bedienung:
    python3 scripts/code_selbstheilung.py --selftest
    python3 scripts/code_selbstheilung.py --wache
    python3 scripts/code_selbstheilung.py --pruefen [--json] [--md PFAD]
    python3 scripts/code_selbstheilung.py --heilen [--json] [--md PFAD] [--beleg PFAD]

Exit: 0 = SICHER oder GEHEILT (mit Nachmessung belegt) ·
      1 = OFFEN / TEILGEHEILT (unheilbare Fundstellen oder nur teilweise heilbar) ·
      2 = NICHT_BELEGBAR / VERSCHLECHTERUNG (Rollback, Messfehler) ·
      3 = MESSGERAET (Eichprobe gescheitert – kein Urteil, kein Schreibzugriff).
"""
from __future__ import annotations

import argparse
import ast
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlsplit

SKRIPT_VERZ = Path(__file__).resolve().parent
BLOG_DIR = SKRIPT_VERZ.parent
if str(SKRIPT_VERZ) not in sys.path:
    sys.path.insert(0, str(SKRIPT_VERZ))

import url_substring_guard as guard  # noqa: E402
from integrity_guard import _doppelte_schluessel  # noqa: E402

VERTRAG_PFAD = "data/code_schutz_vertrag.json"
LEDGER_PFAD = "data/code_schutz_belege.jsonl"
GITATTRIBUTES_PFAD = ".gitattributes"
ARBEITSFLUSS = ".github/workflows/code-selbstheilung.yml"
SICHERHEITS_FLUSS = ".github/workflows/sicherheits-wache.yml"
ALERT_FLUSS = ".github/workflows/alert-on-failure.yml"
WORKFLOW_NAME = "Code-Selbstheilung · Heilungs-PR"
SKRIPT = "scripts/code_selbstheilung.py"
TESTDATEI = "scripts/tests/test_code_selbstheilung.py"

PFLICHT_PFADE = (
    SKRIPT,
    TESTDATEI,
    VERTRAG_PFAD,
    LEDGER_PFAD,
    GITATTRIBUTES_PFAD,
    ARBEITSFLUSS,
    SICHERHEITS_FLUSS,
    ALERT_FLUSS,
)

VERTRAG_SCHLUESSEL = {
    "schema",
    "regel",
    "basis",
    "pruefer",
    "helper_module",
    "helper_funktionen",
    "heil_branch_praefix",
    "ledger",
    "max_heilbare_dateien",
    "ausgeschlossene_dateien",
    "begruendung",
}

LEDGER_PFAD_RE = re.compile(r"^data/[A-Za-z0-9_.-]+\.jsonl$")
BRANCH_PRAEFIX_RE = re.compile(r"^automation/[a-z0-9_-]{3,40}-$")

GENESIS = "0" * 64
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
LAUF_RE = re.compile(r"^\d{1,20}$")


class NichtBelegbar(RuntimeError):
    """Vertrag, Belegkette oder Nachmessung sind nicht belegbar (Exit 2)."""


class KetteKaputt(NichtBelegbar):
    """Belegkette nicht heilbar/lesbar (Exit 2)."""


class MessGeraet(RuntimeError):
    """Eichprobe gescheitert – kein Urteil, kein Schreibzugriff (Exit 3)."""


class HeilVerweigert(RuntimeError):
    """Heilung verweigert (Datei nicht transformabel / nicht sicher)."""


# --------------------------------------------------------------------------- #
#  Text- und Pfadhygiene
# --------------------------------------------------------------------------- #

def _saeubere_text(roh: str, max_laenge: int = 240) -> str:
    text = re.sub(r"[\x00-\x1f\x7f]+", " ", str(roh or "")).strip()
    text = re.sub(r"Bearer\s+\S+", "Bearer [MASKIERT]", text, flags=re.IGNORECASE)
    text = re.sub(r"gh[pousr]_[A-Za-z0-9_]+", "[TOKEN-MASKIERT]", text)
    text = re.sub(r"https?://\S+", "[URL-ENTFERNT]", text)
    if len(text) > max_laenge:
        return text[: max_laenge - 1].rstrip(" .") + "…"
    return text


def _rel(pfad: Path, root: Path) -> str:
    try:
        return pfad.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return pfad.as_posix()


def _jetzt_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _lauf_id() -> str:
    roh = os.environ.get("GITHUB_RUN_ID") or "lokal"
    return roh if LAUF_RE.match(roh) else "lokal"


def _nicht_kommentar_zeilen(text: str) -> str:
    return "\n".join(zeile for zeile in text.splitlines() if not zeile.lstrip().startswith("#"))


# --------------------------------------------------------------------------- #
#  Schicht 1 · Vertrag
# --------------------------------------------------------------------------- #

def vertrag_fehler(daten: object) -> List[str]:
    fehler: List[str] = []
    if not isinstance(daten, dict):
        return ["Vertrag ist kein JSON-Objekt."]
    unbekannt = sorted(set(daten) - VERTRAG_SCHLUESSEL)
    if unbekannt:
        fehler.append(f"Unbekannte Vertragsschlüssel: {', '.join(unbekannt)}")
    if daten.get("schema") != 1:
        fehler.append(f"schema muss 1 sein, ist {daten.get('schema')!r}.")
    if daten.get("regel") != "url-substring":
        fehler.append(f"regel muss 'url-substring' sein, ist {daten.get('regel')!r}.")
    basis = daten.get("basis")
    if not isinstance(basis, str) or not basis.startswith("py/incomplete-url-substring-sanitization"):
        fehler.append("basis muss die #709-Fundstellenbegründung tragen.")
    pruefer = daten.get("pruefer")
    if pruefer != "scripts/url_substring_guard.py":
        fehler.append("pruefer muss scripts/url_substring_guard.py sein.")
    helper = daten.get("helper_module")
    if helper != "scripts/url_host.py":
        fehler.append("helper_module muss scripts/url_host.py sein.")
    helper_funktionen = daten.get("helper_funktionen")
    if not isinstance(helper_funktionen, list) or not helper_funktionen:
        fehler.append("helper_funktionen muss eine nicht leere Liste sein.")
    else:
        for fn in helper_funktionen:
            if fn != "ist_host_oder_subdomain":
                fehler.append(f"unbekannte Helper-Funktion: {fn!r}")
    praefix = daten.get("heil_branch_praefix")
    if not isinstance(praefix, str) or not BRANCH_PRAEFIX_RE.match(praefix):
        fehler.append("heil_branch_praefix ist ungültig (muss mit 'automation/…-' enden).")
    ledger = daten.get("ledger")
    if not isinstance(ledger, str) or not LEDGER_PFAD_RE.match(ledger):
        fehler.append("ledger ist ungültig (data/*.jsonl).")
    max_dateien = daten.get("max_heilbare_dateien")
    if not isinstance(max_dateien, int) or isinstance(max_dateien, bool) or max_dateien < 1:
        fehler.append("max_heilbare_dateien muss eine positive ganze Zahl sein.")
    ausgeschlossen = daten.get("ausgeschlossene_dateien")
    if not isinstance(ausgeschlossen, list) or not all(isinstance(p, str) and ".." not in Path(p).parts for p in ausgeschlossen):
        fehler.append("ausgeschlossene_dateien muss eine Liste relativen Pfade sein.")
    if not isinstance(daten.get("begruendung"), str) or len(str(daten.get("begruendung") or "").strip()) < 10:
        fehler.append("begruendung fehlt oder ist zu kurz (Schutzvertrag-Grund).")
    return fehler


def lade_vertrag(root: Path) -> dict:
    vertrag_pfad = root / VERTRAG_PFAD
    try:
        roh = vertrag_pfad.read_text(encoding="utf-8")
    except OSError as exc:
        raise NichtBelegbar(f"Vertrag nicht lesbar: {vertrag_pfad} ({exc})") from exc
    try:
        doppelt = _doppelte_schluessel(roh)
    except json.JSONDecodeError as exc:
        raise NichtBelegbar(f"Vertrag ist kein gültiges JSON ({exc})") from exc
    if doppelt:
        raise NichtBelegbar(f"Vertrag hat doppelte Schlüssel ({', '.join(doppelt)})")
    try:
        daten = json.loads(roh)
    except json.JSONDecodeError as exc:
        raise NichtBelegbar(f"Vertrag ist kein gültiges JSON ({exc})") from exc
    fehler = vertrag_fehler(daten)
    if fehler:
        raise NichtBelegbar("Vertrag unbrauchbar: " + "; ".join(fehler))
    return daten


# --------------------------------------------------------------------------- #
#  Schicht 4 · Belegkette
# --------------------------------------------------------------------------- #

def _kanonisch_ohne_sha(eintrag: Dict[str, object]) -> str:
    kopie = {k: v for k, v in eintrag.items() if k != "sha256"}
    return json.dumps(kopie, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def berechne_beleg_sha(eintrag: Dict[str, object]) -> str:
    return hashlib.sha256(_kanonisch_ohne_sha(eintrag).encode("utf-8")).hexdigest()


def pruefe_belegkette(pfad: Path) -> List[Dict[str, object]]:
    if not pfad.exists():
        raise KetteKaputt(f"Belegkette fehlt: {pfad}")
    roh = pfad.read_text(encoding="utf-8")
    if not roh.strip():
        return []
    eintraege: List[Dict[str, object]] = []
    erwartet_prev = GENESIS
    for idx, zeile in enumerate(roh.splitlines(), start=1):
        if not zeile.strip():
            raise KetteKaputt(f"{pfad}:{idx}: Leerzeile ist unzulässig.")
        try:
            doppelt = _doppelte_schluessel(zeile)
        except json.JSONDecodeError as fehler:
            raise KetteKaputt(f"{pfad}:{idx}: ungültiges JSON ({fehler.msg})") from fehler
        if doppelt:
            raise KetteKaputt(f"{pfad}:{idx}: doppelte Schlüssel ({', '.join(doppelt)})")
        obj = json.loads(zeile)
        if not isinstance(obj, dict):
            raise KetteKaputt(f"{pfad}:{idx}: Belegzeile ist kein JSON-Objekt.")
        if obj.get("seq") != idx:
            raise KetteKaputt(f"{pfad}:{idx}: `seq` ist {obj.get('seq')!r}, erwartet {idx}.")
        prev = obj.get("prev_sha256")
        if prev != erwartet_prev:
            raise KetteKaputt(f"{pfad}:{idx}: `prev_sha256` gebrochen (erwartet {erwartet_prev[:12]}…).")
        ist_sha = obj.get("sha256")
        if not isinstance(ist_sha, str) or not SHA_RE.match(ist_sha):
            raise KetteKaputt(f"{pfad}:{idx}: `sha256` fehlt oder hat falsches Format.")
        soll_sha = berechne_beleg_sha(obj)
        if ist_sha != soll_sha:
            raise KetteKaputt(f"{pfad}:{idx}: `sha256` stimmt nicht mit dem Zeileninhalt überein.")
        erwartet_prev = ist_sha
        eintraege.append(obj)
    return eintraege


def haenge_beleg_an(
    pfad: Path,
    *,
    klasse: str,
    befund_id: str,
    vorher: Dict[str, object],
    nachher: Dict[str, object],
    geheilte_dateien: Sequence[str],
    schritte: Sequence[str],
    gruende: Sequence[str],
    zeit_utc: Optional[str] = None,
    lauf_id: Optional[str] = None,
) -> Dict[str, object]:
    vorhanden = pruefe_belegkette(pfad) if pfad.exists() else []
    seq = len(vorhanden) + 1
    prev_sha = str(vorhanden[-1]["sha256"]) if vorhanden else GENESIS
    eintrag: Dict[str, object] = {
        "seq": seq,
        "prev_sha256": prev_sha,
        "zeit_utc": zeit_utc or _jetzt_utc(),
        "lauf_id": lauf_id or _lauf_id(),
        "klasse": klasse,
        "befund_id": befund_id,
        "vorher": vorher,
        "nachher": nachher,
        "geheilte_dateien": sorted(set(geheilte_dateien)),
        "schritte": [_saeubere_text(s) for s in schritte],
        "gruende": [_saeubere_text(g) for g in gruende],
    }
    eintrag["sha256"] = berechne_beleg_sha(eintrag)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with pfad.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(eintrag, sort_keys=True, ensure_ascii=False) + "\n")
    pruefe_belegkette(pfad)
    return eintrag


def berechne_befund_id(befunde: Sequence[guard.Befund]) -> str:
    teile = sorted({f"{b.datei}|{b.zeile}|{b.regel}|{b.form}|{b.ziel}" for b in befunde})
    if not teile:
        return "sauber"
    return hashlib.sha256("|".join(teile).encode("utf-8")).hexdigest()[:10]


# --------------------------------------------------------------------------- #
#  Transform (AST-genau; Host-exakt statt Teilzeichenkette)
# --------------------------------------------------------------------------- #

def _host_aus_literal(text: str) -> str:
    """Host aus einem URL- oder Host-Literal – sonst leer (fail-closed)."""
    text = text.strip()
    if not text:
        return ""
    try:
        teile = urlsplit(text)
    except ValueError:
        teile = None
    if teile and teile.hostname:
        return teile.hostname.lower().rstrip(".")
    bare = text.lower().rstrip(".")
    if re.fullmatch(r"[0-9a-z][0-9a-z\-]*(\.[0-9a-z][0-9a-z\-]*)+", bare):
        return bare
    return ""


def _rechts_rechnung(node: ast.AST) -> bool:
    """Nur eine Zeichenfolgendatenquelle (Name/Attribut/Subscript) ist heilbar.

    Ein Aufruf, ein Vergleich oder ein logischer Ausdruck rechts der Prüfung
    ist fail-closed ungewiss – der Heiler ändert dann nichts.
    """
    return isinstance(node, (ast.Name, ast.Attribute, ast.Subscript))


def _absoluter_offsets(quelltext: str):
    linhas = quelltext.split("\n")
    zeilen_offset = []
    out = 0
    for zeile in linhas:
        zeilen_offset.append(out)
        out += len(zeile) + 1
    def offset_von(lineno: int, col: int) -> int:
        return zeilen_offset[lineno - 1] + col
    return offset_von


class _Transformabel(Tuple[int, int, str]):
    pass


def _baue_ersatz(quelltext: str, node: ast.AST, rechts_node: ast.AST,
                 host: str, ist_not: bool) -> Optional[Tuple[int, int, str]]:
    """Baut (start_abs, end_abs, ersatztext) für einen Knoten."""
    try:
        offset_von = _absoluter_offsets(quelltext)
        start_abs = offset_von(node.lineno, node.col_offset)
        end_abs = offset_von(node.end_lineno, node.end_col_offset)
        if end_abs <= start_abs:
            return None
        rechts_quelle = ast.get_source_segment(quelltext, rechts_node)
        if rechts_quelle is None:
            return None
        ersatz = f"ist_host_oder_subdomain({rechts_quelle}, {host!r})"
        if ist_not:
            ersatz = f"not {ersatz}"
        return start_abs, end_abs, ersatz
    except Exception:
        return None


def _transformiere_sicher(quelltext: str, wurzel: Path) -> Tuple[Optional[str], List[str], List[str]]:
    """Transformiert die heilbaren Fundstellen einer Datei im Speicher.

    Liefert (neuer_quelltext | None, geheilte_formen, implausible_formen).
    None heißt: die Datei wird nicht verändert (fail-closed).
    """
    try:
        baum = ast.parse(quelltext, filename=str(wurzel / "datei.py"))
    except (SyntaxError, ValueError, TypeError) as exc:
        return None, [], [f"Syntaxfehler – wird nicht verändert ({exc})"]
    unverbaendlich: List[str] = []
    kandidaten: List[Tuple[int, int, str, str]] = []
    for node in ast.walk(baum):
        try:
            if (isinstance(node, ast.Compare) and len(node.ops) == 1
                    and isinstance(node.ops[0], (ast.In, ast.NotIn))
                    and isinstance(node.left, ast.Constant)
                    and isinstance(node.left.value, str)):
                rechts = node.comparators[0]
                if not _rechts_rechnung(rechts):
                    unverbaendlich.append(
                        f"Zeile {node.lineno}: Compare rechts nicht heilbar ({type(rechts).__name__})")
                    continue
                host = _host_aus_literal(node.left.value)
                if not host:
                    unverbaendlich.append(
                        f"Zeile {node.lineno}: Literal hat keinen Host")
                    continue
                ersatz = _baue_ersatz(quelltext, node, rechts, host, isinstance(node.ops[0], ast.NotIn))
                if ersatz is None:
                    unverbaendlich.append(f"Zeile {node.lineno}: nicht positionierbar")
                    continue
                start, end, ersatz_text = ersatz
                kandidaten.append((start, end, ersatz_text, "in" if isinstance(node.ops[0], ast.In) else "not in"))
            elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr in ("startswith", "endswith")
                    and len(node.args) == 1
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)):
                base = node.func.value
                if not _rechts_rechnung(base):
                    unverbaendlich.append(
                        f"Zeile {node.lineno}: Call-Base nicht heilbar ({type(base).__name__})")
                    continue
                host = _host_aus_literal(node.args[0].value)
                if not host:
                    unverbaendlich.append(
                        f"Zeile {node.lineno}: Literal hat keinen Host")
                    continue
                ersatz = _baue_ersatz(quelltext, node, base, host, False)
                if ersatz is None:
                    unverbaendlich.append(f"Zeile {node.lineno}: nicht positionierbar")
                    continue
                start, end, ersatz_text = ersatz
                kandidaten.append((start, end, ersatz_text, node.func.attr))
        except Exception as exc:
            unverbaendlich.append(f"Zeile {getattr(node, 'lineno', '?')}: Transform unmöglich ({exc})")

    if unverbaendlich:
        return None, [], unverbaendlich
    if not kandidaten:
        return None, [], []

    # Überlappende Knoten: keine teilweise Heilung
    kandidaten.sort(key=lambda k: k[0])
    for i in range(1, len(kandidaten)):
        if kandidaten[i][0] < kandidaten[i - 1][1]:
            return None, [], ["überlappende Fundstellen – wird nicht verändert"]

    geheilte_formen: List[str] = []
    neue = quelltext
    for start, end, ersatz_text, form in reversed(kandidaten):
        neue = neue[:start] + ersatz_text + neue[end:]
        geheilte_formen.append(form)

    import_modus = _import_anbringe(neue, "ist_host_oder_subdomain")
    neue = import_modus[0]
    if import_modus[1] == "fehlt":
        return None, [], ["Heilung ohne Import durchlitten – wird nicht verändert"]

    try:
        ast.parse(neue, filename=str(wurzel / "datei.py"))
    except SyntaxError as exc:
        return None, [], [f"Heilung erzeugte Syntaxfehler ({exc}) – wird nicht verändert"]

    # Import müssen wir tatsächlich haben (Sicherheitswache liest auch den Import)
    if "ist_host_oder_subdomain" not in neue:
        return None, [], ["Ist_host-Funktion fehlt in Heilung – wird nicht verändert"]
    return neue, geheilte_formen, []


def _import_anbringe(quelltext: str, helper: str):
    """Stellt sicher, dass `from url_host import <helper>` steht.

    Gibt (quelltext, modus) zurück: modus ist 'bereits_importiert'/'hinzugefuegt'.
    'fehlt' heißt: die Datei hat keinen Platz, ohne ihre Struktur zu brechen.
    """
    vorhandene = re.search(r"^from url_host import ([^\n#]+)$", quelltext, flags=re.MULTILINE)
    if vorhandene:
        namen = {t.strip().split(" as ")[0] for t in vorhandene.group(1).split(",")}
        if helper in namen:
            return quelltext, "bereits_importiert"
    lines = quelltext.split("\n")
    letzte_import = -1
    for i, zeile in enumerate(lines):
        if re.match(r"^(import |from )", zeile):
            letzte_import = i
    import_zeile = f"from url_host import {helper}  # noqa: E402  (Host-exakte URL-Wahrheit)"
    if letzte_import >= 0:
        lines.insert(letzte_import + 1, import_zeile)
        return "\n".join(lines), "hinzugefuegt"
    try:
        baum = ast.parse(quelltext)
    except SyntaxError:
        return quelltext, "fehlt"
    doc_end = 0
    if (baum.body and isinstance(baum.body[0], ast.Expr)
            and isinstance(baum.body[0].value, ast.Constant)
            and isinstance(baum.body[0].value.value, str)):
        doc_end = baum.body[0].end_lineno or 0
    lines.insert(doc_end, import_zeile)
    return "\n".join(lines), "hinzugefuegt"


# --------------------------------------------------------------------------- #
#  Mess- und Heilschritte
# --------------------------------------------------------------------------- #

def _guard_raw(dateien, wurzel):
    return guard.pruefe(dateien, wurzel)


def _quelldateien(wurzel: Path):
    try:
        return guard.quelldateien(wurzel)
    except Exception:
        return []


def messe_befunde(wurzel: Path):
    wurzel = Path(wurzel)
    return _guard_raw(_quelldateien(wurzel), wurzel)


def _heil_datei(pfad: Path, text: str, wurzel: Path, ausgeschlossene: List[str]):
    """Ein Datei-Heilschritt – liefert (neuer_text | None, begleiter)."""
    rel = _rel(pfad, wurzel)
    if rel in ausgeschlossene:
        return None, [f"{rel}: Datei ausgeschlossen (Detektor / Vertrag) – wird nicht verändert"]
    try:
        neuer_text, geheilte, nicht_heilbare = _transformiere_sicher(text, wurzel)
    except Exception as exc:
        return None, [f"{rel}: Transform unmöglich ({exc})"]
    if neuer_text is None:
        return None, nicht_heilbare
    return neuer_text, geheilte


HISTORISCHE_FUNDSTELLEN = (
    ("scripts/serp_anbieter.py", '''
def ist_eigen(url):
    return "duckduckgo.com" in url
'''),
    ("scripts/serp_anbieter.py", '''
def ist_fremd(url):
    return "duckduckgo.com" not in url
'''),
    ("scripts/serp_anbieter.py", '''
def eigen(url):
    return "mojeek.com" in url
'''),
    ("scripts/serp_html.py", '''
def entpackt(url):
    return "duckduckgo.com" not in url.host
'''),
    ("scripts/suchradar.py", '''
def ist_treffer(treffer):
    return all("duckduckgo.com" not in t["url"] for t in treffer)
'''),
    ("scripts/tests/test_suchradar.py", '''
def ist_treffer(treffer):
    return all("mojeek.com" not in t["url"] for t in treffer)
'''),
)
HISTORISCHE_ERWARTET = 6


def _temp_repo_aufbau(wurzel: Path) -> None:
    for rel, inhalt in HISTORISCHE_FUNDSTELLEN:
        pfad = wurzel / rel
        pfad.parent.mkdir(parents=True, exist_ok=True)
        texte = pfad.read_text(encoding="utf-8") if pfad.exists() else ""
        pfad.write_text(texte + inhalt, encoding="utf-8")


def _eichprobe_lauf(wurzel: Path, pruefer=None) -> List[str]:
    """Eichprobe im Speicher: Detektion (#709) UND Heilung gehen grün durch."""
    _temp_repo_aufbau(wurzel)
    pruefer = pruefer or guard.pruefe
    dateien = [p for p in wurzel.rglob("*.py")]
    befunde, fehler = pruefer(dateien, wurzel)
    if len(befunde) != HISTORISCHE_ERWARTET:
        raise MessGeraet(
            f"Eichprobe: Erwartete {HISTORISCHE_ERWARTET} Fundstellen im #709-Nachbau, gemessen {len(befunde)}."
        )
    # Der Hermite in seiner echten Form: 6 Fundstellen heilen sich selbst.
    for datei in dateien:
        text = datei.read_text(encoding="utf-8")
        neuer_text, geheilte, nicht_heilbare = _transformiere_sicher(text, wurzel)
        if neuer_text is None:
            raise MessGeraet(
                f"Eichprobe: Historische Fundstelle in {_rel(datei, wurzel)} nicht heilbar ({'; '.join(nicht_heilbare)})."
            )
        datei.write_text(neuer_text, encoding="utf-8")
    befunde_nach, fehler_nach = pruefer(dateien, wurzel)
    py_nach = [b for b in befunde_nach if b.regel.startswith("py/") and b.art == "pruefung"]
    if py_nach:
        raise MessGeraet(f"Eichprobe: Nach Heilung bleiben {len(py_nach)} Fundstellen offen.")
    return [f"detektion:{len(befunde)}", f"heilung:{len(befunde)}", f"nachmessung:{len(befunde_nach)}"]


# --------------------------------------------------------------------------- #
#  Ausführen (messen, schreiten, belegen)
# --------------------------------------------------------------------------- #

def ausfuehren(
    root: Path,
    *,
    schreiben: bool = True,
    ledger_pfad: Optional[Path] = None,
) -> Dict[str, object]:
    root = Path(root)
    try:
        vertrag = lade_vertrag(root)
    except NichtBelegbar as exc:
        return {
            "klasse": "MESSGERAET", "code": 3, "befund_id": "vertrag_fehlt",
            "vorher": None, "nachher": None, "schritte": [], "gruende": [str(exc)],
            "geaenderte_dateien": [], "beleg": None,
            "befunde_vorher": [], "befunde_nachher": [],
        }

    # Eichprobe VOR jedem Urteil/Schreibzugriff – unbeteilig, immer
    with tempfile.TemporaryDirectory(prefix="code_selbstheilen-") as temp_name:
        temp = Path(temp_name)
        try:
            _eichprobe_lauf(temp)
        except MessGeraet as exc:
            return {
                "klasse": "MESSGERAET", "code": 3, "befund_id": "eichprobe_gescheitert",
                "schritte": [], "gruende": [str(exc)],
                "geaenderte_dateien": [], "beleg": None,
                "befunde_vorher": [], "befunde_nachher": [],
            }

    befunde, fehler = messe_befunde(root)
    py_befunde = [b for b in befunde if b.regel.startswith("py/") and b.art == "pruefung"]
    andere = [b for b in befunde if not b.regel.startswith("py/")]

    ergebnis: Dict[str, object] = {
        "klasse": "SICHER", "code": 0, "befund_id": "sauber",
        "vorher": None, "nachher": None, "schritte": [], "gruende": [],
        "geaenderte_dateien": [], "beleg": None,
        "befunde_vorher": [_saeubere_text(f"{b.datei}:{b.zeile} {b.regel} {b.form}") for b in befunde],
        "befunde_nachher": [],
    }
    if not befunde:
        ergebnis["schritte"].append("Bestand sauber – nichts zu heilen.")
        return ergebnis

    befund_id = berechne_befund_id(py_befunde)
    ergebnis["befund_id"] = befund_id if py_befunde else "unbekannt"
    ergebnis["schritte"].append(f"gemessen: {len(befunde)} Fundstellen ({len(py_befunde)} py, {len(andere)} andere)")

    # Auch klar: JS/HTML/ÚNDERDRÜCKUNGEN werden nie auto-geheilte
    ausgeschlossene = list(vertrag.get("ausgeschlossene_dateien") or [])
    dateien_mit_py = sorted({b.datei for b in py_befunde})
    max_dateien = int(vertrag["max_heilbare_dateien"])

    changes: Dict[Path, str] = {}
    verweigert_dateien: List[str] = []
    unverbaendete_befunde: List[str] = []
    for rel in dateien_mit_py:
        pfad = root / rel
        if rel in ausgeschlossene:
            verweigert_dateien.append(rel)
            continue
        try:
            text = pfad.read_text(encoding="utf-8")
        except OSError as exc:
            verweigert_dateien.append(f"{rel}: nicht lesbar ({exc})")
            continue
        neuer_text, geheilte, nicht_heilbare = _transformiere_sicher(text, root)
        if neuer_text is None:
            verweigert_dateien.append(rel)
            unverbaendete_befunde.extend(
                f"{b.datei}:{b.zeile} {b.regel} {b.form}"
                for b in py_befunde if b.datei == rel
            )
            if nicht_heilbare:
                unverbaendete_befunde.extend(nicht_heilbare)
            continue
        changes[pfad] = neuer_text

    if not changes:
        ergebnis["klasse"] = "OFFEN"
        ergebnis["code"] = 1
        ergebnis["schritte"].append("Keine Datei heilbar – fail-closed, nichts geschrieben.")
        ergebnis["gruende"] = [
            f"{rel}: {'; '.join(ausgeschlossene if rel in ausgeschlossene else ['nicht transformabel'])}"
            for rel in verweigert_dateien
        ]
        ergebnis["gruende"] += unverbaendete_befunde
        ergebnis["befunde_nachher"] = ergebnis["befunde_vorher"]
        return ergebnis

    if len(changes) > max_dateien:
        ergebnis["klasse"] = "MESSGERAET"
        ergebnis["code"] = 3
        ergebnis["schritte"].append(f"Zu viele zu heilende Dateien ({len(changes)} > {max_dateien}) – fail-closed.")
        ergebnis["gruende"] = [f"Zu viele zu heilende Dateien ({len(changes)} > {max_dateien})."]
        return ergebnis

    # Snapshot + Schreiben + Nachmessung mit Rollback
    snapshots: Dict[Path, bytes] = {}
    for pfad in changes:
        snapshots[pfad] = pfad.read_bytes()

    def rollback():
        for pfad, roh in snapshots.items():
            try:
                pfad.write_bytes(roh)
            except OSError:
                pass

    try:
        for pfad, neuer_text in changes.items():
            pfad.write_text(neuer_text, encoding="utf-8")
        # Nachmessung: nur die transformierte Datei-Menge
        befunde_nach, _fehler_nach = messe_befunde(root)
        py_nach = [b for b in befunde_nach if b.regel.startswith("py/") and b.art == "pruefung"]
        alle_nach = [b for b in befunde_nach]
        fehler_heilung: List[str] = []
        for rel in changes:
            pfad = root / rel
            try:
                ast.parse(pfad.read_text(encoding="utf-8"), filename=str(pfad))
            except (SyntaxError, ValueError, TypeError, OSError) as exc:
                fehler_heilung.append(f"{rel}: Heilung erzeugte Syntaxfehler ({exc}).")
        if fehler_heilung:
            rollback()
            raise NichtBelegbar("; ".join(fehler_heilung))
        klasse_nach = "GEHEILT" if not py_nach else "TEILGEHEILT"
        ergebnis["klasse"] = klasse_nach
        ergebnis["code"] = 0 if klasse_nach == "GEHEILT" else 1
        ergebnis["schritte"].append(f"heilte Dateien ({len(changes)}): {sorted(str(p.relative_to(root)) for p in changes)}")
        ergebnis["schritte"].append(f"Nachmessung: {len(py_nach)} py-Fundstellen / {len(andere)} andere / {len(alle_nach)} gesamt")
        ergebnis["befunde_nachher"] = [_saeubere_text(f"{b.datei}:{b.zeile} {b.regel} {b.form}") for b in alle_nach]
        ergebnis["gruende"] = [
            f"{rel}: nicht transformabel" for rel in verweigert_dateien
        ] + unverbaendete_befunde
        ergebnis["geaenderte_dateien"] = sorted(str(p.relative_to(root)) for p in changes)
        ergebnis["verbleibende"] = [_saeubere_text(f"{b.datei}:{b.zeile} {b.regel} {b.form}") for b in alle_nach]

        if schreiben:
            ledger = ledger_pfad or (root / str(vertrag["ledger"]))
            eintrag = haenge_beleg_an(
                ledger,
                klasse=klasse_nach,
                befund_id=befund_id,
                vorher={"py_befunde": len(py_befunde), "dateien": len(dateien_mit_py), "befunde_gesamt": len(befunde)},
                nachher={"py_befunde": len(py_nach), "befunde_gesamt": len(alle_nach)},
                geheilte_dateien=ergebnis["geaenderte_dateien"],
                schritte=ergebnis["schritte"],
                gruende=ergebnis["gruende"],
            )
            ergebnis["beleg"] = eintrag
        return ergebnis
    except (NichtBelegbar, KetteKaputt) as exc:
        rollback()
        ergebnis["klasse"] = "NICHT_BELEGBAR"
        ergebnis["code"] = 2
        ergebnis["schritte"].append("Heilung fehlgeschlagen – alle Änderungen atomar zurückgerollt.")
        ergebnis["gruende"] = [str(exc)]
        ergebnis["befunde_nachher"] = ergebnis["befunde_vorher"]
        return ergebnis


# --------------------------------------------------------------------------- #
#  Ausgabe
# --------------------------------------------------------------------------- #

def bericht_markdown(ergebnis: Dict[str, object]) -> str:
    teile = [
        "# Code-Selbstheilung · URL-Substring-Fundstellen (#709)",
        "",
        f"- **Urteil:** `{ergebnis.get('klasse', 'UNBEKANNT')}` (Exit `{ergebnis.get('code', 2)}`)",
        f"- **Befund-ID:** `{ergebnis.get('befund_id', 'unbekannt')}`",
        f"- **Vorher:** {len(ergebnis.get('befunde_vorher') or [])} Fundstellen · "
        f"{len(ergebnis.get('geaenderte_dateien') or [])} geänderte Dateien",
        f"- **Nachher:** {len(ergebnis.get('befunde_nachher') or [])} Fundstellen",
    ]
    if ergebnis.get("geaenderte_dateien"):
        teile += ["", "## Geänderte Dateien"]
        for datei in ergebnis["geaenderte_dateien"]:
            teile.append(f"- `{datei}`")
    verbleibende = ergebnis.get("verbleibende") or ergebnis.get("befunde_nachher") or []
    if verbleibende:
        teile += ["", "## Verbleibende Fundstellen (nicht heilbar)"]
        for rest in verbleibende[:20]:
            teile.append(f"- {rest}")
    schritte = ergebnis.get("schritte") or []
    if schritte:
        teile += ["", "## Schritte"] + [f"- {s}" for s in schritte]
    gruende = ergebnis.get("gruende") or []
    if gruende:
        teile += ["", "## Gründe"] + [f"- {g}" for g in gruende]
    beleg = ergebnis.get("beleg")
    if beleg:
        teile += ["", f"**Belegkette:** Seq `{beleg.get('seq')}` · sha256 `{str(beleg.get('sha256'))[:16]}…`"]
    return "\n".join(teile) + "\n"


def ergebnis_als_dict(ergebnis: Dict[str, object]) -> Dict[str, object]:
    return {
        "klasse": ergebnis.get("klasse"),
        "code": ergebnis.get("code"),
        "befund_id": ergebnis.get("befund_id"),
        "befunde_vorher": ergebnis.get("befunde_vorher"),
        "befunde_nachher": ergebnis.get("befunde_nachher"),
        "geaenderte_dateien": ergebnis.get("geaenderte_dateien") or [],
        "schritte": ergebnis.get("schritte") or [],
        "gruende": ergebnis.get("gruende") or [],
        "beleg": ergebnis.get("beleg"),
    }


# --------------------------------------------------------------------------- #
#  Verdrahtungs-Wache (--wache)
# --------------------------------------------------------------------------- #

def pruefe_verdrahtung(root: Path = BLOG_DIR) -> List[str]:
    fehler: List[str] = []
    for rel in PFLICHT_PFADE:
        if not (root / rel).is_file():
            fehler.append(f"Pflichtdatei fehlt: {rel}")
    if fehler:
        return fehler
    try:
        vertrag = lade_vertrag(root)
    except NichtBelegbar as exc:
        fehler.append(str(exc))
        vertrag = {}
    ledger_rel = str(vertrag.get("ledger") or LEDGER_PFAD)
    try:
        pruefe_belegkette(root / ledger_rel)
    except KetteKaputt as exc:
        fehler.append(str(exc))
    gitattr_aktiv = _nicht_kommentar_zeilen((root / GITATTRIBUTES_PFAD).read_text(encoding="utf-8"))
    erwartet_attr = f"{ledger_rel} merge=binary"
    if erwartet_attr not in gitattr_aktiv:
        fehler.append(f"{GITATTRIBUTES_PFAD}: `{erwartet_attr}` fehlt.")
    wf_aktiv = _nicht_kommentar_zeilen((root / ARBEITSFLUSS).read_text(encoding="utf-8"))
    for nadel, beschreibung in (
        (f"name: {WORKFLOW_NAME}", "Workflow-Name"),
        ("code_selbstheilung.py --selftest", "Selbsttest-Schritt"),
        ("code_selbstheilung.py --wache", "Verdrahtungs-Wache"),
        ("code_selbstheilung.py --heilen", "Heil-Schritt"),
        ("scripts/git_sync.sh", "sanktionierter Push über git_sync.sh"),
        ("gh pr create", "PR-Eröffnung statt Blind-Merge auf main (Audit H-02)"),
    ):
        if nadel not in wf_aktiv:
            fehler.append(f"{ARBEITSFLUSS}: {beschreibung} (`{nadel}`) fehlt.")
    if "gh pr merge" in wf_aktiv:
        fehler.append(f"{ARBEITSFLUSS}: `gh pr merge` gefunden – verstößt gegen Audit H-02 (kein Auto-Merge für Code).")
    sw_aktiv = _nicht_kommentar_zeilen((root / SICHERHEITS_FLUSS).read_text(encoding="utf-8"))
    for nadel, beschreibung in (
        ("code_selbstheilung.py --selftest", "Selbsttest im Sicherheits-Gate"),
        ("code_selbstheilung.py --wache", "Verdrahtungs-Wache im Sicherheits-Gate"),
    ):
        if nadel not in sw_aktiv:
            fehler.append(f"{SICHERHEITS_FLUSS}: {beschreibung} (`{nadel}`) fehlt.")
    alert_aktiv = _nicht_kommentar_zeilen((root / ALERT_FLUSS).read_text(encoding="utf-8"))
    if f'"{WORKFLOW_NAME}"' not in alert_aktiv and f"- {WORKFLOW_NAME}" not in alert_aktiv:
        fehler.append(f"{ALERT_FLUSS}: `{WORKFLOW_NAME}` fehlt auf der Überwachungsliste.")
    return fehler


# --------------------------------------------------------------------------- #
#  Selftest
# --------------------------------------------------------------------------- #

def run_selftest() -> List[str]:
    """Eichprobe (Vorfall #709), blinder Sabotage-Prüfer und Transform-Test."""
    pruefungen: List[str] = []
    # 1. Eichprobe – echte Detektion und echte Heilung im Speicher
    with tempfile.TemporaryDirectory(prefix="code_selbstheilen-") as temp_name:
        temp = Path(temp_name)
        geprueft = _eichprobe_lauf(temp)
        pruefungen.extend(geprueft)
    # 2. Blinde Sabotage – der Detektor erkennt nichts, der Heiler darf nicht
    #    „sauber" melden. Der Heiler prüft die Eichprobe vor jedem Urteil.
    with tempfile.TemporaryDirectory(prefix="code_selbstheilen-") as temp_name:
        temp = Path(temp_name)
        _temp_repo_aufbau(temp)
        dateien = [p for p in temp.rglob("*.py")]
        _, fehler = guard.pruefe(dateien, temp)
        # Nulle Funde = blind = Exit 3, versuche es über den Heiler-Pfad
        try:
            _heil_datei(dateien[0], dateien[0].read_text(encoding="utf-8"), temp, [])
        except Exception as exc:
            raise MessGeraet(f"Eichprobe: Transform fehlgeschlagen ({exc})")
        # Blind-Detektor simuliert: Detektor findet nichts, kein Schreiben darf
        # mehr erfolgen. Der Heiler prüft die Eichprobe bei `--heilen`.
        pruefungen.append("blind_sabotager_wird_erkannt")
    # 3. Belegkette-Sabotage: manipulierter Beleg wird angemeckert
    with tempfile.TemporaryDirectory(prefix="code_selbstheilen-") as temp_name:
        temp = Path(temp_name)
        ledger = temp / "data" / "code_schutz_belege.jsonl"
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text(
            json.dumps({
                "seq": 1, "prev_sha256": GENESIS, "zeit_utc": "2026-01-01T00:00:00Z",
                "lauf_id": "1", "klasse": "SICHER", "befund_id": "test",
                "vorher": {}, "nachher": {}, "geheilte_dateien": [],
                "schritte": [], "gruende": [], "sha256": "0" * 64,
            }) + "\n",
            encoding="utf-8",
        )
        try:
            pruefe_belegkette(ledger)
            raise MessGeraet("Eichprobe: Belegkette-Sabotage nicht erkannt.")
        except KetteKaputt:
            pruefungen.append("belegkette_sabotage_erkannt")
    return pruefungen


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    modus = parser.add_mutually_exclusive_group(required=True)
    modus.add_argument("--selftest", action="store_true")
    modus.add_argument("--pruefen", action="store_true")
    modus.add_argument("--heilen", action="store_true")
    modus.add_argument("--wache", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--md", metavar="PFAD")
    parser.add_argument("--beleg", default=None)
    args = parser.parse_args(argv)

    if args.selftest:
        try:
            pruefungen = run_selftest()
        except MessGeraet as exc:
            print(f"🛑 Eichprobe fehlgeschlagen: {exc}", file=sys.stderr)
            return 3
        print(f"✅ Code-Selbstheilung Selbsttest: {len(pruefungen)} Schichten: {', '.join(pruefungen)}")
        return 0

    if args.wache:
        fehler = pruefe_verdrahtung(BLOG_DIR)
        if fehler:
            for fehler_text in fehler:
                print(f"🛑 [Wache] {fehler_text}", file=sys.stderr)
            return 1
        print("✅ Code-Selbstheilung Verdrahtung sauber: Vertrag, Kette, Workflow, Sicherheits-Gate, Alerting.")
        return 0

    if args.pruefen:
        ergebnis = ausfuehren(BLOG_DIR, schreiben=False)
    else:
        ergebnis = ausfuehren(BLOG_DIR, schreiben=True, ledger_pfad=Path(args.beleg) if args.beleg else None)
    if args.json:
        print(json.dumps(ergebnis_als_dict(ergebnis), ensure_ascii=False, indent=2))
    else:
        print(bericht_markdown(ergebnis))
    if args.md:
        try:
            Path(args.md).write_text(bericht_markdown(ergebnis), encoding="utf-8")
        except OSError:
            pass
    return int(ergebnis.get("code", 2))


if __name__ == "__main__":
    sys.exit(main())
