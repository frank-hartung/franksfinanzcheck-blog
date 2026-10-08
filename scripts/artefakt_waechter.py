#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
artefakt_waechter.py – Der Artefakt-Wächter
===========================================

WARUM ES DIESE WACHE GIBT (08.10.2026, WF-D4E0 #653)
----------------------------------------------------
Sechs Nächte hintereinander wurde `content-reserve.yml` am harten End-Gate
„Stock shortage must not look successful“ rot – mit derselben Meldung:

    🛑 RESERVE-ENGPAß: nur 0/6 Kandidaten gate-fertig.

Der Vorrat war in keiner dieser Nächte leer. Der Lauf war rot, weil EIN
Artefakt kaputt war und keine Wache der Kette das geprüft hat:

  * `data/reserve-readiness.json`  – zwei Zertifikatsstände durch einen
    Merge zu EINER Datei verschmolzen (doppelte Schlüssel, kein gültiges
    JSON mehr). Der End-Gate las sie, fing den Parse-Fehler still und
    zählte „0 bereit“: **Ein Artefakt-Defekt sah aus wie ein leeres Lager.**
  * `data/reserve-quarantine.json` – dieselbe Klasse: ein Block wurde
    mitten in einen nicht geschlossenen Eintrag geklebt, die äußere
    Klammer fehlt. Das Quarantäne-Gedächtnis war unlesbar.
  * `data/reserve-custody.json`    – sechs Einträge mit doppeltem
    Schlüssel `zuletzt_im_pool` (zwei Werte für dieselbe Aussage).

Drei Artefakte, eine Ursache, null Wachen: `history_guard.py` deckt
ausschließlich `data/*_history.jsonl` ab, `bot_watchdog.py` prüft
Python-Syntax. Die strukturierte Wahrheit in `data/**/*.json` – genau
dort, wo Zertifikat, Quarantäne und Bestands-Gedächtnis liegen – prüfte
niemand. Ein Merge-Artefakt reiste also durch `main`, bis ein fachlich
völlig unbeteiligtes Tor es als Vorrats-Engpass meldete.

WAS DIE WACHE TUT (im Standardbetrieb rein lesend)
--------------------------------------------------
    A1  JSON-SYNTAX       data/**/*.json ist kein gültiges JSON
    A2  JSON-DOPPELT      doppelter Objektschlüssel in data/**/*.json
    A3  JSONL-ZEILE       Zeile in data/**/*.jsonl ist kein JSON-Objekt
    A4  KONFLIKT-MARKER   Git-Konfliktmarker in einem Artefakt
    A5  YAML              data/**/*.yaml|yml: Syntaxfehler oder doppelter
                          Schlüssel
    A6  FRONTMATTER       content/**/index.md: Frontmatter-Syntaxfehler
                          oder doppelter Schlüssel (Hugo stirbt daran mit
                          „mapping key … already defined“, #645)

Alle sechs Klassen sind HART: Ein Artefakt, das kein Werkzeug der Kette
lesen kann, ist kein „Hinweis“. Wer es liest, entscheidet über Zertifikate,
Quarantäne, Fahnen und Builds.

HEILUNG (ausschließlich beweisbar, sonst keine)
-----------------------------------------------
`--heal` repariert NUR A2 (doppelte JSON-Schlüssel):

    Regel: der LETZTE Eintrag gewinnt – exakt das, was `json.loads()`
    beim Lesen ohnehin tut. Die Wache macht die stille Annahme sichtbar
    und schreibt sie fest. Beweis: nach der Heilung ergibt
    `json.loads(neu) == json.loads(alt)` – die Aussage der Datei ändert
    sich für KEINEN Leser.

A1, A3, A4, A5, A6 werden NICHT geheilt: Ein nicht mehr parsfähiges
Artefakt zu rekonstruieren hieße, Inhalt zu erfinden. Die Wache nennt
stattdessen den Reparaturweg inklusive des letzten nachweislich gültigen
Stands im Git (`git show <rev>:<pfad>` – gelesen, nie geschrieben).

Der Selbsttest und die Wirkungsprobe arbeiten ausschließlich in einem
eigenen temporären Baum (C15): Ein Prüf-Aufruf heilt nicht – schon gar
nicht am echten Repo.

NUTZUNG
    python3 scripts/artefakt_waechter.py                 # prüfen (hart)
    python3 scripts/artefakt_waechter.py --heal          # A2 beweisbar heilen
    python3 scripts/artefakt_waechter.py --md            # Markdown für Lauf-Summary
    python3 scripts/artefakt_waechter.py --json          # maschinenlesbar
    python3 scripts/artefakt_waechter.py --wirkungsprobe # Sabotage → heilen → grün
    python3 scripts/artefakt_waechter.py --selftest      # Sabotageschutz

EXIT: 0 = grün · 1 = Fund · 2 = Selbsttest rot (Wache geschützt)
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Nur versionierte Maschinen-Artefakte – kein Quelltext (den prüft der
# bot_watchdog), keine Reports (die sind absichtlich Prosa).
JSON_GLOBS = ("data/**/*.json",)
JSONL_GLOBS = ("data/**/*.jsonl",)
YAML_GLOBS = ("data/**/*.yaml", "data/**/*.yml")
CONTENT_GLOBS = ("content/**/index.md",)

# Artefakte, die aus einer Quelle NEU erzeugbar sind – die Wache nennt für
# sie den erzeugenden Befehl statt eines blinden „bitte reparieren“.
ERZEUGER = {
    "data/reserve-readiness.json": "python3 scripts/reserve_readiness.py",
    "data/reserve-quarantine.json":
        "python3 scripts/reserve_readiness.py (schreibt Zertifikat und "
        "Quarantäne-Gedächtnis im selben Lauf neu)",
    "data/reserve-custody.json": "python3 scripts/reserve_custody.py --heal",
    "data/reserve-topic-ledger.json": "python3 scripts/reserve_topics.py --status",
    "data/covers_manifest.json": "python3 scripts/check_covers.py",
}

KONFLIKT = re.compile(r"^(<{7} |={7}$|>{7} |\|{7})")
RE_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---[ \t]*\n", re.S)
RE_YAML_KEY = re.compile(
    r"^(?P<indent>[ \t]*)(?P<item>- )?(?P<key>(?:\"[^\"]*\"|'[^']*'|[^:#][^:]*)):")


# ---------------------------------------------------------------------------
#  Fund-Datensatz
# ---------------------------------------------------------------------------
class Fund:
    __slots__ = ("klasse", "pfad", "ort", "meldung", "heilbar", "reparatur")

    def __init__(self, klasse, pfad, ort, meldung, heilbar=False, reparatur=""):
        self.klasse = klasse
        self.pfad = pfad
        self.ort = ort
        self.meldung = meldung
        self.heilbar = heilbar
        self.reparatur = reparatur

    def als_dict(self) -> dict:
        return {"klasse": self.klasse, "pfad": self.pfad, "ort": self.ort,
                "meldung": self.meldung, "heilbar": self.heilbar,
                "reparatur": self.reparatur}

    def __repr__(self) -> str:  # pragma: no cover – Debug-Hilfe
        return f"<Fund {self.klasse} {self.pfad}:{self.ort}>"


# ---------------------------------------------------------------------------
#  Git-Hinweis: letzter nachweislich gültiger Stand (rein lesend)
# ---------------------------------------------------------------------------
def letzter_gueltiger_stand(rel: str, pruefer, wurzel: Path | None = None) -> str | None:
    """Hinweis auf den letzten Commit, in dem das Artefakt noch gültig war.

    LIEST NUR. Die Wache schreibt nichts aus der Historie zurück – sie
    nennt dem Menschen den belegbaren Stand und überlässt ihm die
    Entscheidung (Rekonstruktion wäre eine Fälschung).
    """
    wurzel = wurzel or ROOT
    try:
        revs = subprocess.run(["git", "log", "--format=%H", "--", rel],
                              cwd=str(wurzel), capture_output=True, text=True,
                              timeout=60).stdout.split()
    except (OSError, subprocess.SubprocessError):
        return None
    for rev in revs[:40]:
        try:
            stand = subprocess.run(["git", "show", f"{rev}:{rel}"],
                                   cwd=str(wurzel), capture_output=True,
                                   text=True, timeout=60).stdout
        except (OSError, subprocess.SubprocessError):
            continue
        if stand and not pruefer(stand):
            return f"git show {rev[:12]}:{rel}"
    return None


def parse_json_text(text: str) -> list[Fund]:
    """Prüfer für einen Text im Speicher (Git-Historie, Tests)."""
    try:
        json.loads(text)
    except ValueError:
        return [Fund("A1-JSON-SYNTAX", "-", "-", "kein gültiges JSON")]
    return []


# ---------------------------------------------------------------------------
#  Prüfer je Artefakt-Klasse
# ---------------------------------------------------------------------------
def _doppelte_schluessel(text: str) -> list[str]:
    """Doppelte Objektschlüssel (A2). Leer = sauber."""
    doppelt: list[str] = []

    def waechter(paare):
        gesehen: set = set()
        for schluessel, _ in paare:
            if schluessel in gesehen:
                doppelt.append(str(schluessel))
            gesehen.add(schluessel)
        return dict(paare)

    try:
        json.loads(text, object_pairs_hook=waechter)
    except (ValueError, UnicodeDecodeError):
        return []
    return doppelt


def _text(pfad: Path) -> tuple[str | None, Fund | None]:
    try:
        return pfad.read_text(encoding="utf-8"), None
    except (OSError, UnicodeDecodeError) as exc:
        return None, Fund("A1-JSON-SYNTAX", str(pfad), "-",
                          f"Datei nicht lesbar: {exc.__class__.__name__}")


def _konflikt_fund(rohtext: str, rel: str) -> Fund | None:
    treffer = [i for i, zeile in enumerate(rohtext.splitlines(), 1)
               if KONFLIKT.match(zeile)]
    if not treffer:
        return None
    return Fund("A4-KONFLIKT-MARKER", rel, f"Zeile {treffer[0]}",
                "Git-Konfliktmarker im Artefakt – ein Merge wurde "
                "aufgelöst, indem beide Seiten stehen blieben.",
                reparatur="Konflikt bewusst auflösen, danach neu erzeugen")


def pruefe_json(pfad: Path, rel: str | None = None) -> list[Fund]:
    rel = rel or str(pfad)
    rohtext, fund = _text(pfad)
    if rohtext is None:
        return [fund]
    konflikt = _konflikt_fund(rohtext, rel)
    if konflikt:
        return [konflikt]
    try:
        json.loads(rohtext)
    except ValueError as exc:
        return [Fund("A1-JSON-SYNTAX", rel,
                     f"Zeile {getattr(exc, 'lineno', '?')}",
                     str(exc).splitlines()[0][:180],
                     reparatur=ERZEUGER.get(rel)
                     or "Erzeuger-Skript erneut laufen lassen")]
    doppelt = _doppelte_schluessel(rohtext)
    if doppelt:
        return [Fund("A2-JSON-DOPPELT", rel,
                     ", ".join(sorted(set(doppelt))[:4]),
                     f"{len(doppelt)} doppelte(r) Objektschlüssel – zwei "
                     "Werte für dieselbe Aussage (Merge-Artefakt). "
                     "`json.loads()` nimmt still den letzten; jedes andere "
                     "Werkzeug könnte anders entscheiden.",
                     heilbar=True,
                     reparatur="python3 scripts/artefakt_waechter.py --heal "
                               "(letzter Eintrag gewinnt)")]
    return []


def pruefe_jsonl(pfad: Path, rel: str | None = None) -> list[Fund]:
    rel = rel or str(pfad)
    try:
        zeilen = pfad.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        return [Fund("A3-JSONL-ZEILE", rel, "-", f"Datei nicht lesbar: {exc}")]
    funde: list[Fund] = []
    for nr, zeile in enumerate(zeilen, 1):
        if KONFLIKT.match(zeile):
            funde.append(Fund("A4-KONFLIKT-MARKER", rel, f"Zeile {nr}",
                              "Git-Konfliktmarker in einer Append-only-Historie."))
            continue
        if not zeile.strip():
            continue
        try:
            wert = json.loads(zeile)
        except ValueError as exc:
            funde.append(Fund("A3-JSONL-ZEILE", rel, f"Zeile {nr}",
                              f"kein gültiges JSON: {str(exc).splitlines()[0][:120]}"))
            continue
        if not isinstance(wert, dict):
            funde.append(Fund("A3-JSONL-ZEILE", rel, f"Zeile {nr}",
                              f"JSON, aber kein Objekt ({type(wert).__name__})"))
    return funde


def _yaml_doppelte_schluessel(text: str) -> list[str]:
    """Doppelte Schlüssel je EBENE, ohne ein drittes YAML-Werkzeug.

    Kleiner, eigener Scanner statt eines Custom-Loaders: Die Wache darf an
    einem kaputten Artefakt nicht selbst scheitern, und sie muss auch dort
    noch doppelte Schlüssel finden, wo `yaml.safe_load` längst abbricht.

    Einträge derselben Ebene teilen sich EINE Schlüsselmenge; ein neues
    Sequenz-Element (`- `) beginnt ein NEUES Objekt und setzt die Menge
    zurück. Ein Schlüsselname darf in verschiedenen Ebenen oder in
    verschiedenen Listenelementen beliebig oft vorkommen.
    """
    stapel: list[tuple[int, set]] = []
    funde: list[str] = []
    for zeile in text.splitlines():
        if not zeile.strip() or zeile.lstrip().startswith("#"):
            continue
        treffer = RE_YAML_KEY.match(zeile)
        if not treffer:
            continue
        ebene = len(treffer.group("indent").replace("\t", "  ")) // 2
        while stapel and stapel[-1][0] > ebene:
            stapel.pop()
        if not stapel or stapel[-1][0] < ebene:
            stapel.append((ebene, set()))
        elif treffer.group("item") and stapel[-1][0] == ebene:
            stapel[-1] = (ebene, set())       # neues Listenelement
        schluessel = treffer.group("key").strip().strip('"\'')
        if schluessel in stapel[-1][1]:
            funde.append(schluessel)
        stapel[-1][1].add(schluessel)
    return funde


def _yaml_laden(text: str) -> tuple[list[str], list[str]]:
    """(syntaxfehler, doppelte_schluessel)."""
    try:
        import yaml  # noqa: WPS433 – optionale Abhängigkeit
    except ImportError:
        return [], []
    fehler: list[str] = []
    try:
        for _ in yaml.safe_load_all(text):
            pass
    except Exception as exc:  # noqa: BLE001 – yaml wirft viele Klassen
        meldung = str(getattr(exc, "problem", exc) or exc)
        marke = getattr(exc, "problem_mark", None)
        zeile = getattr(marke, "line", None)
        fehler.append(f"Zeile {zeile}: {meldung}" if zeile else meldung[:180])
    return fehler, _yaml_doppelte_schluessel(text)


def pruefe_yaml(pfad: Path, rel: str | None = None) -> list[Fund]:
    rel = rel or str(pfad)
    try:
        text = pfad.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [Fund("A5-YAML", rel, "-", f"Datei nicht lesbar: {exc}")]
    konflikt = _konflikt_fund(text, rel)
    if konflikt:
        return [konflikt]
    fehler, doppelt = _yaml_laden(text)
    funde = [Fund("A5-YAML", rel, "-", f) for f in fehler]
    if doppelt:
        funde.append(Fund("A5-YAML", rel, ", ".join(sorted(set(doppelt))[:4]),
                          f"{len(doppelt)} doppelte(r) Schlüssel – zwei "
                          "Werte für dieselbe Aussage.",
                          reparatur="doppelten Schlüssel von Hand auflösen"))
    return funde


def pruefe_frontmatter(pfad: Path, rel: str | None = None) -> list[Fund]:
    rel = rel or str(pfad)
    try:
        text = pfad.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [Fund("A6-FRONTMATTER", rel, "-", f"Datei nicht lesbar: {exc}")]
    treffer = RE_FRONTMATTER.match(text)
    if not treffer:
        return []
    fm = treffer.group(1)
    konflikt = [i for i, zeile in enumerate(fm.splitlines(), 2)
                if KONFLIKT.match(zeile)]
    if konflikt:
        return [Fund("A4-KONFLIKT-MARKER", rel,
                     f"Frontmatter-Zeile {konflikt[0]}",
                     "Git-Konfliktmarker im Frontmatter.")]
    fehler, doppelt = _yaml_laden(fm)
    funde = [Fund("A6-FRONTMATTER", rel, "-", f) for f in fehler]
    if doppelt:
        funde.append(Fund("A6-FRONTMATTER", rel,
                          ", ".join(sorted(set(doppelt))[:4]),
                          f"{len(doppelt)} doppelte(r) Frontmatter-Schlüssel "
                          "– Hugo bricht den Build daran ab "
                          "(„mapping key … already defined“).",
                          reparatur="doppelten Schlüssel entfernen "
                                    "(python3 scripts/fm_boundary_guard.py)"))
    return funde


# ---------------------------------------------------------------------------
#  Sammlung
# ---------------------------------------------------------------------------
def dateien(wurzel: Path | None = None) -> list[tuple[Path, str, str]]:
    """(pfad, rel, art) aller zu prüfenden Artefakte."""
    wurzel = Path(wurzel or ROOT)
    out: list[tuple[Path, str, str]] = []
    gesehen: set[Path] = set()
    for art, globs in (("json", JSON_GLOBS), ("jsonl", JSONL_GLOBS),
                       ("yaml", YAML_GLOBS), ("content", CONTENT_GLOBS)):
        for muster in globs:
            for pfad in sorted(wurzel.glob(muster)):
                if pfad.is_dir() or pfad in gesehen:
                    continue
                gesehen.add(pfad)
                out.append((pfad, str(pfad.relative_to(wurzel)), art))
    return out


def pruefe_alle(wurzel: Path | None = None) -> list[Fund]:
    funde: list[Fund] = []
    for pfad, rel, art in dateien(wurzel):
        if art == "json":
            funde += pruefe_json(pfad, rel)
        elif art == "jsonl":
            funde += pruefe_jsonl(pfad, rel)
        elif art == "yaml":
            funde += pruefe_yaml(pfad, rel)
        else:
            funde += pruefe_frontmatter(pfad, rel)
    return funde


# ---------------------------------------------------------------------------
#  Heilung – nur A2, nur beweisbar
# ---------------------------------------------------------------------------
def heile_json_doppelt(pfad: Path) -> tuple[bool, str]:
    """Entfernt doppelte Schlüssel (letzter gewinnt). Beweis: gleicher Inhalt.

    Die Heilung ist BEWEISBAR, weil `json.loads()` beim Lesen ohnehin den
    letzten Eintrag nimmt: Vorher- und Nachher-Objekt sind identisch.
    Genau dieser Gleichheitstest ist die Abnahme – ohne ihn schreibt die
    Wache kein Byte.
    """
    try:
        rohtext = pfad.read_text(encoding="utf-8")
        vorher = json.loads(rohtext)
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        return False, f"nicht heilbar (unlesbar: {exc.__class__.__name__})"
    if not isinstance(vorher, dict):
        return False, "nicht heilbar (Wurzel ist kein Objekt)"
    try:
        bereinigt = json.loads(rohtext, object_pairs_hook=dict)
    except ValueError as exc:
        return False, f"nicht heilbar ({exc})"
    if bereinigt != vorher:
        return False, "nicht heilbar (Ergebnis wiche vom Lesestand ab)"
    # Format des Bestands erhalten: Einzug WIE GELESEN, Sortierung wie gelesen.
    # Warum aus dem Text gelesen und nicht „2“ angenommen: Eine Heilung, die
    # eine vierfach eingerückte Datei auf eine Zeile eindampft, ist zwar
    # aussagengleich, aber ein Diff-Schock – und genau ein solcher Diff wird
    # beim nächsten Merge wieder zum Konfliktmaterial (#653). Wer heilt, muss
    # so schreiben, wie der Bestand schon schreibt.
    treffer = re.search(r"\n([ \t]+)\"", rohtext)
    einzugsstufe: int | str | None = None
    if treffer:
        einzugsstufe = "\t" if "\t" in treffer.group(1) else len(treffer.group(1))
    try:
        oberstes = json.loads(rohtext, object_pairs_hook=lambda p: p)
        sortiert = (isinstance(oberstes, dict)
                    and list(oberstes) == sorted(oberstes))
    except ValueError:
        sortiert = False
    try:
        neu = json.dumps(bereinigt, ensure_ascii=False, indent=einzugsstufe,
                         sort_keys=sortiert) + "\n"
    except (TypeError, ValueError) as exc:
        return False, f"nicht heilbar (nicht serialisierbar: {exc})"
    if neu == rohtext:
        # Idempotenz ist beweisbar: MELDEN heißt „nichts geändert“. Eine
        # Heilung, die „True“ meldet, ohne ein Byte geschrieben zu haben,
        # macht jeden zweiten Lauf zum stummen Alias des ersten (#653).
        return False, "bereits sauber – nichts zu tun"
    try:
        if json.loads(neu) != vorher:
            return False, "nicht heilbar (Gegenprobe ungleich)"
    except ValueError:
        return False, "nicht heilbar (Gegenprobe unlesbar)"
    pfad.write_text(neu, encoding="utf-8")
    return True, "geheilt (letzter Eintrag gewinnt, Gegenprobe gleich)"


def heile(funde: list[Fund], wurzel: Path | None = None) -> list[str]:
    """Heilt ausschließlich A2. Alles andere bleibt unangetastet."""
    wurzel = Path(wurzel or ROOT)
    protokoll: list[str] = []
    for fund in funde:
        if fund.klasse != "A2-JSON-DOPPELT":
            continue
        ok, meldung = heile_json_doppelt(wurzel / fund.pfad)
        zeichen = "✅" if (ok and "geheilt" in meldung) else "⏭️ "
        protokoll.append(f"{zeichen} {fund.pfad}: {meldung}")
    return protokoll


# ---------------------------------------------------------------------------
#  Ausgabe
# ---------------------------------------------------------------------------
def als_markdown(funde: list[Fund], geprueft: int) -> str:
    if not funde:
        return (f"## 🧱 Artefakt-Wächter – {geprueft} Artefakte strukturell heil\n\n"
                "Alle versionierten Maschinen-Artefakte (`data/**/*.json`, "
                "`*.jsonl`, `*.yaml`, Frontmatter von `content/**/index.md`) "
                "sind parsebar und frei von doppelten Schlüsseln.\n")
    zeilen = [f"## 🧱 Artefakt-Wächter – {len(funde)} Fund(e) in "
              f"{geprueft} Artefakten\n"]
    for klasse in sorted({f.klasse for f in funde}):
        gruppe = [f for f in funde if f.klasse == klasse]
        zeilen.append(f"### {klasse} ({len(gruppe)})")
        for fund in gruppe:
            zeilen.append(f"- **{fund.pfad}** ({fund.ort}): {fund.meldung}")
            if fund.reparatur:
                zeilen.append(f"  - Reparatur: `{fund.reparatur}`")
    return "\n".join(zeilen) + "\n"


# ---------------------------------------------------------------------------
#  Sabotageschutz
# ---------------------------------------------------------------------------
# Ein ECHTER Syntaxfehler (fehlendes Komma) – kein doppelter Schlüssel.
_SABOTAGE_JSON_KAPUTT = '{\n  "a": 1,\n  "b": 2\n  "c": 3\n}\n'
_SABOTAGE_JSON_DOPPELT = '{\n  "a": 1,\n  "x": "alt",\n  "x": "neu"\n}\n'
_SABOTAGE_JSONL = '{"ok": 1}\n{kein json}\n'
_SABOTAGE_YAML = "a: 1\nb: 2\nb: 3\n"
_SABOTAGE_KONFLIKT = ('{\n<<<<<<< HEAD\n  "a": 1\n=======\n  "a": 2\n'
                      '>>>>>>> other\n}\n')


def _schreib(wurzel: Path, rel: str, text: str) -> Path:
    ziel = wurzel / rel
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(text, encoding="utf-8")
    return ziel


def run_selftest() -> int:
    fehler: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        wurzel = Path(tmp)

        # --- A1: kaputtes JSON wird erkannt, sauberes nicht ---
        kaputt = _schreib(wurzel, "data/kaputt.json", _SABOTAGE_JSON_KAPUTT)
        if not any(f.klasse == "A1-JSON-SYNTAX"
                   for f in pruefe_json(kaputt, "data/kaputt.json")):
            fehler.append("A1: kaputtes JSON wurde nicht erkannt")
        sauber = _schreib(wurzel, "data/sauber.json", '{\n  "a": 1,\n  "b": 2\n}\n')
        if pruefe_json(sauber, "data/sauber.json"):
            fehler.append("A1: sauberes JSON wurde fälschlich als Fund gemeldet")

        # --- A2: doppelter Schlüssel erkannt + beweisbar geheilt ---
        doppelt = _schreib(wurzel, "data/doppelt.json", _SABOTAGE_JSON_DOPPELT)
        funde = pruefe_json(doppelt, "data/doppelt.json")
        if not any(f.klasse == "A2-JSON-DOPPELT" for f in funde):
            fehler.append("A2: doppelter Schlüssel wurde nicht erkannt")
        elif not any(f.heilbar for f in funde):
            fehler.append("A2: Fund ist nicht als heilbar markiert")
        vorher = json.loads(doppelt.read_text(encoding="utf-8"))
        ok, _ = heile_json_doppelt(doppelt)
        if not ok:
            fehler.append("A2: Heilung schlug fehl")
        else:
            nachher = json.loads(doppelt.read_text(encoding="utf-8"))
            if nachher != vorher or nachher.get("x") != "neu":
                fehler.append("A2: Heilung änderte die Aussage der Datei")
            if pruefe_json(doppelt, "data/doppelt.json"):
                fehler.append("A2: nach der Heilung blieb ein Fund stehen")
            stand = doppelt.read_text(encoding="utf-8")
            heile_json_doppelt(doppelt)
            if doppelt.read_text(encoding="utf-8") != stand:
                fehler.append("A2: Heilung ist nicht idempotent")

        # --- Die Heilung darf NIE rekonstruieren ---
        unheilbar = _schreib(wurzel, "data/zu_kaputt.json", _SABOTAGE_JSON_KAPUTT)
        ok, meldung = heile_json_doppelt(unheilbar)
        if ok or "nicht heilbar" not in meldung:
            fehler.append("A1 wurde geheilt – Rekonstruktion ist verboten")

        # --- A3: JSONL-Zeilen ---
        zl = _schreib(wurzel, "data/kaputt.jsonl", _SABOTAGE_JSONL)
        if not any(f.klasse == "A3-JSONL-ZEILE"
                   for f in pruefe_jsonl(zl, "data/kaputt.jsonl")):
            fehler.append("A3: kaputte JSONL-Zeile wurde nicht erkannt")
        zg = _schreib(wurzel, "data/gut.jsonl", '{"a": 1}\n{"b": 2}\n')
        if pruefe_jsonl(zg, "data/gut.jsonl"):
            fehler.append("A3: saubere JSONL wurde fälschlich als Fund gemeldet")
        zo = _schreib(wurzel, "data/objekt.jsonl", '[1, 2]\n')
        if not any(f.klasse == "A3-JSONL-ZEILE"
                   for f in pruefe_jsonl(zo, "data/objekt.jsonl")):
            fehler.append("A3: JSON-Array-Zeile (kein Objekt) wurde nicht erkannt")

        # --- A4: Konfliktmarker ---
        konf = _schreib(wurzel, "data/konflikt.json", _SABOTAGE_KONFLIKT)
        if not any(f.klasse == "A4-KONFLIKT-MARKER"
                   for f in pruefe_json(konf, "data/konflikt.json")):
            fehler.append("A4: Konfliktmarker wurden nicht erkannt")

        # --- A5/A6: YAML + Frontmatter ---
        yml = _schreib(wurzel, "data/kaputt.yaml", _SABOTAGE_YAML)
        if not any(f.klasse == "A5-YAML"
                   for f in pruefe_yaml(yml, "data/kaputt.yaml")):
            fehler.append("A5: doppelter YAML-Schlüssel wurde nicht erkannt")
        yml_ok = _schreib(wurzel, "data/gut.yaml", "a: 1\nb: 2\n")
        if pruefe_yaml(yml_ok, "data/gut.yaml"):
            fehler.append("A5: sauberes YAML wurde fälschlich als Fund gemeldet")
        liste = _schreib(wurzel, "data/liste.yaml",
                         "items:\n  - name: a\n    value: 1\n"
                         "  - name: b\n    value: 2\n")
        if pruefe_yaml(liste, "data/liste.yaml"):
            fehler.append("A5: gleiche Schlüssel in verschiedenen "
                          "Listenelementen wurden fälschlich gemeldet")
        fm = _schreib(wurzel, "content/posts/beispiel/index.md",
                      "---\ntitle: X\ntitle: Y\ndraft: true\n---\n\nText\n")
        if not any(f.klasse == "A6-FRONTMATTER"
                   for f in pruefe_frontmatter(fm,
                                               "content/posts/beispiel/index.md")):
            fehler.append("A6: doppelter Frontmatter-Schlüssel wurde nicht erkannt")
        fm_ok = _schreib(wurzel, "content/posts/gut/index.md",
                         "---\ntitle: X\ndraft: true\n---\n\nText\n")
        if pruefe_frontmatter(fm_ok, "content/posts/gut/index.md"):
            fehler.append("A6: sauberes Frontmatter wurde fälschlich gemeldet")

        # --- YAML-Scanner: Ebenen dürfen denselben Schlüssel tragen ---
        if _yaml_doppelte_schluessel("a:\n  x: 1\nb:\n  x: 2\n"):
            fehler.append("A5: gleicher Schlüssel auf verschiedenen Ebenen "
                          "wurde fälschlich als Duplikat gemeldet")

        # --- Das echte Repo bleibt unberührt (C15) ---
        if heile([Fund("A1-JSON-SYNTAX", "data/kaputt.json", "-", "x")], wurzel):
            fehler.append("Nicht-heilbare Klasse wurde doch geheilt")

    if fehler:
        print("🛑 ARTEFAKT-WÄCHTER SELBSTTEST ROT:")
        for zeile in fehler:
            print("   - " + zeile)
        return 2
    print("✅ Artefakt-Wächter-Selbsttest grün (A1–A6 erkannt, "
          "A2 beweisbar geheilt, Falschmeldungen ausgeschlossen, "
          "Rekonstruktion verboten, idempotent).")
    return 0


def run_wirkungsprobe() -> int:
    """Sabotage → heilen → grün. Der Maschinenvertrag hinter der Heilung."""
    fehler: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        wurzel = Path(tmp)
        ziel = _schreib(wurzel, "data/reserve-custody.json",
                        '{\n  "eintrag": {\n    "slug": "a",\n'
                        '    "zuletzt_im_pool": "2026-10-07",\n'
                        '    "zuletzt_im_pool": "2026-10-08",\n'
                        '    "zustand": "pool"\n  }\n}\n')
        alt = json.loads(ziel.read_text(encoding="utf-8"))
        funde = pruefe_json(ziel, "data/reserve-custody.json")
        if len(funde) != 1 or funde[0].klasse != "A2-JSON-DOPPELT":
            fehler.append("Sabotage wurde nicht als A2 erkannt")
        else:
            protokoll = heile(funde, wurzel)
            if not any("geheilt" in p for p in protokoll):
                fehler.append("Heilung hat die Sabotage nicht beseitigt: "
                              + "; ".join(protokoll))
            if pruefe_json(ziel, "data/reserve-custody.json"):
                fehler.append("nach der Heilung blieb ein Fund stehen")
            neu = json.loads(ziel.read_text(encoding="utf-8"))
            if neu != alt:
                fehler.append("Heilung hat die Aussage verändert")
            elif neu["eintrag"]["zuletzt_im_pool"] != "2026-10-08":
                fehler.append("Heilung hat nicht den jüngeren Wert gewählt")
            stand = ziel.read_text(encoding="utf-8")
            heile(pruefe_json(ziel, "data/reserve-custody.json"), wurzel)
            if ziel.read_text(encoding="utf-8") != stand:
                fehler.append("Heilung ist nicht idempotent")
    if fehler:
        print("🛑 WIRKUNGSPROBE ROT:")
        for zeile in fehler:
            print("   - " + zeile)
        return 1
    print("✅ Wirkungsprobe grün: A2-Sabotage erkannt, beweisbar geheilt "
          "(jüngerer Wert, Aussage unverändert), danach grün und idempotent.")
    return 0


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Artefakt-Wächter: strukturelle Integrität der "
                    "versionierten Maschinen-Artefakte")
    ap.add_argument("--selftest", action="store_true", help="Sabotageschutz")
    ap.add_argument("--wirkungsprobe", action="store_true",
                    help="Sabotage → heilen → grün (Maschinenvertrag C25)")
    ap.add_argument("--heal", action="store_true",
                    help="A2 (doppelte JSON-Schlüssel) beweisbar heilen")
    ap.add_argument("--md", action="store_true", help="Markdown-Ausgabe")
    ap.add_argument("--json", action="store_true", help="JSON-Ausgabe")
    ap.add_argument("--root", default=None, help="Wurzel (Tests/Sondierung)")
    args = ap.parse_args(argv)

    if args.selftest:
        return run_selftest()
    if args.wirkungsprobe:
        return run_wirkungsprobe()

    wurzel = Path(args.root).resolve() if args.root else ROOT
    funde = pruefe_alle(wurzel)

    if args.heal:
        for zeile in heile(funde, wurzel):
            print("   " + zeile)
        funde = [f for f in pruefe_alle(wurzel) if f.klasse != "A2-JSON-DOPPELT"]

    geprueft = len(dateien(wurzel))
    if args.json:
        print(json.dumps({"geprueft": geprueft,
                          "funde": [f.als_dict() for f in funde]},
                         ensure_ascii=False, indent=2))
        return 1 if funde else 0
    if args.md:
        print(als_markdown(funde, geprueft))
        return 1 if funde else 0

    if not funde:
        print(f"✅ ARTEFAKT-WÄCHTER: {geprueft} Artefakte strukturell heil "
              "(JSON, JSONL, YAML, Frontmatter – parsebar, keine doppelten "
              "Schlüssel, keine Konfliktmarker).")
        return 0

    print(f"🛑 ARTEFAKT-WÄCHTER: {len(funde)} Fund(e) in {geprueft} Artefakten.")
    for fund in funde:
        print(f"   [{fund.klasse}] {fund.pfad} ({fund.ort})")
        print(f"        {fund.meldung}")
        if fund.reparatur:
            print(f"        → {fund.reparatur}")
        if fund.klasse == "A1-JSON-SYNTAX":
            hinweis = letzter_gueltiger_stand(fund.pfad, parse_json_text, wurzel)
            if hinweis:
                print(f"        letzter nachweislich gültiger Stand: {hinweis}")
    print("\n   Ein Artefakt, das kein Werkzeug der Kette lesen kann, ist kein "
          "Hinweis, sondern ein Fund: Die Zertifizierung urteilt damit über "
          "einen Pool, den sie gar nicht gemessen hat.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
