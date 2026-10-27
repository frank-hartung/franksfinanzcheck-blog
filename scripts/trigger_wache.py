#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TRIGGER-WACHE – eine Wache, die nicht anspringt, ist keine Wache.

WARUM ES DIESE WACHE GIBT (WF-E813 / #815, 27.10.2026)
------------------------------------------------------
Die Dauerheilung von WF-E813 besteht aus Wachen: Header-Wache, Worker-Wache,
Abhängigkeits-Wache, Edge-Freigabe, Deploy-Vorbereitung. Jede dieser Wachen
ist ein Skript, das ein Workflow aufruft. **Wann** er aufgerufen wird,
entscheidet allein der `paths:`-Filter im Trigger – eine Liste, die von Hand
gepflegt wird, und zwar zweimal (für `push` und für `pull_request`).

Genau darin liegt eine stille Ausfallklasse, die zu diesem Vorgang passt:

    · Der Workflow prüft `scripts/manifest_guard.py`.
    · `manifest_guard.py` wird geändert.
    · Der Workflow startet **nicht**, weil sein Filter die Datei nicht nennt.
    · Ergebnis: Grün, ohne geprüft zu haben.

Am 27.10.2026 hat diese Wache den Bestand zum ersten Mal gemessen. Sie fand
**36 Befunde in neun Workflows**:

    · W1 – 21 Aufrufe ohne Trigger in acht Workflows, verteilt auf elf
      Dateien: `manifest_guard.py` (in fünf Gates benutzt, in vier Filtern
      nicht genannt), `alert_issue_identity.py` (Markenflächen-Wache),
      `audio_coverage_check.py`, `ff_voice_parity_check.py` und
      `ff_voice_toolbar_check.py` (Lesehilfen-Gate), `selftest_clock.py`
      (Robustheits-Wache), `backup_einrichtung.py`/`kv_backup.py`
      (Backup-Frischwache), `tabellen_lesbarkeit_guard.py` (E2E),
      `agent_reach_gate.py` und `test_design_varianten.py` (Design-Varianten).
    · W3 – 15 Einträge, die nur in EINER der beiden Listen standen
      (14 davon im Lesehilfen-Gate, 1 in der Sicherheits-Wache).
    · W2 – 0: Kein Filter zeigte ins Leere.

Keine dieser Lücken war „kaputt“ – alle waren unsichtbar. Das ist dieselbe
Bauweise, die den Worker-Deploy (#829B) und das CodeQL-Gate (26.10.2026)
tagelang still rot stehen ließ: Das Signal existiert, aber es kommt nicht an.

DIE REGELN
----------
    W1  REFERENZ    Ein Skript/test, das ein Workflow in einem `run:`-Block
                    aufruft, muss von dessen `paths`-Filter gedeckt sein –
                    für `push` und für `pull_request`, sofern der Filter
                    existiert. Workflows ohne `paths` laufen immer: nichts
                    zu prüfen.
    W2  WAISE       Ein Filtereintrag ohne Platzhalter, der auf keine Datei
                    mehr zeigt, ist ein toter Trigger: Er lädt zu einer
                    Prüfung ein, die es nicht mehr gibt.
    W3  SYMMETRIE   `push` und `pull_request` müssen dieselbe Liste tragen.
                    Zwei handgepflegte Kopien driften; eine Prüfung, die nur
                    auf dem einen Weg läuft, ist ein halbes Gate.

WAS SIE AUSDRÜCKLICH NICHT PRÜFT
--------------------------------
Ob die Prüfung *sinnvoll* ist, ob der Schritt im richtigen Job steht, oder
ob ein Filter zu breit ist. Sie prüft nur: **Was der Lauf anfasst, löst ihn
auch aus.** Diese Grenze ist bewusst – eine Wache, die über Geschmack
urteilt, wird ignoriert.

BENUTZUNG
---------
    python3 scripts/trigger_wache.py --check      # Exit 0/1/2
    python3 scripts/trigger_wache.py --md         # Bericht für die Summary
    python3 scripts/trigger_wache.py --selftest   # Sabotage- und Gegenproben

Der Parser liest nur den Ausschnitt von YAML, den Trigger brauchen
(`on:` → Ereignis → `paths`/`paths-ignore`), absichtlich ohne PyYAML: Diese
Wache läuft in einem Lauf, der keine Abhängigkeiten installiert. Dass der
Ausschnitt-Parser nicht anders liest als ein vollständiger YAML-Parser,
beweist `scripts/tests/test_trigger_wache.py` gegen PyYAML (wenn vorhanden).
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Sequence

HIER = Path(__file__).resolve().parent
BLOG_DIR = HIER.parent
WORKFLOW_DIR = Path(".github") / "workflows"

REGEL_REFERENZ = "W1"
REGEL_WAISE = "W2"
REGEL_SYMMETRIE = "W3"

# Ereignisse, deren Pfadfilter dieselbe Menge prüfen MUSS (W3).
GESPIEGELT = ("push", "pull_request")

# Was ein Lauf aufrufen kann. Die Endung ist Pflicht – sonst würde jedes
# erwähnte Verzeichnis (tools/wrangler, e2e) zu einem Befund.
AUFRUF = re.compile(
    r"(?:python3?|node|bash|sh)\s+(?:-m\s+\S+\s+)?"
    r"((?:scripts|e2e|tools)/[A-Za-z0-9_./*-]+\.(?:py|mjs|cjs|js|sh))"
)
# `python3 -m unittest scripts.tests.test_x` → scripts/tests/test_x.py
MODULTEST = re.compile(r"-m\s+unittest\s+(?:-v\s+|--verbose\s+)?"
                       r"((?:scripts|tools)\.[A-Za-z0-9_.]+)")

EIGENSCHAFT = re.compile(r"^(\s+)([A-Za-z0-9_-]+):\s*(.*)$")


@dataclass(frozen=True)
class Befund:
    regel: str
    workflow: str
    ereignis: str
    text: str


# --------------------------------------------------------------------------- #
#  YAML-Ausschnitt (nur Trigger)
# --------------------------------------------------------------------------- #
def _ohne_kommentar(wert: str) -> str:
    """Schneidet einen YAML-Kommentar ab – ohne `#` in Anführungszeichen."""
    in_einfach = in_doppelt = False
    for stelle, zeichen in enumerate(wert):
        if zeichen == "'" and not in_doppelt:
            in_einfach = not in_einfach
        elif zeichen == '"' and not in_einfach:
            in_doppelt = not in_doppelt
        elif zeichen == "#" and not in_einfach and not in_doppelt:
            if stelle == 0 or wert[stelle - 1] in " \t":
                return wert[:stelle].rstrip()
    return wert.rstrip()


def _wert(roh: str) -> str:
    wert = _ohne_kommentar(roh).strip()
    if len(wert) >= 2 and wert[0] == wert[-1] and wert[0] in "\"'":
        return wert[1:-1]
    return wert


def trigger(text: str) -> dict[str, dict[str, list[str]]]:
    """Liest `on:` → Ereignis → `paths`/`paths-ignore` aus dem Workflow-Text.

    Gibt je Ereignis ein Dict mit den Schlüsseln ``paths`` und
    ``paths-ignore`` zurück (leer, wenn der Ereignis-Block keine Pfade hat).
    """
    zeilen = text.splitlines()
    ergebnis: dict[str, dict[str, list[str]]] = {}
    i = 0
    while i < len(zeilen):
        if re.match(r"^on:\s*(#.*)?$", zeilen[i]):
            break
        i += 1
    else:
        return ergebnis
    i += 1
    ereignis: str | None = None
    unter: str | None = None
    while i < len(zeilen):
        zeile = zeilen[i]
        i += 1
        if not zeile.strip() or zeile.lstrip().startswith("#"):
            continue
        einrueckung = len(zeile) - len(zeile.lstrip())
        if einrueckung == 0:
            break  # nächster Top-Level-Schlüssel (jobs:, permissions:, …)
        treffer = EIGENSCHAFT.match(zeile)
        if einrueckung == 2:
            if not treffer:
                continue
            ereignis = treffer.group(2)
            ergebnis.setdefault(ereignis, {"paths": [], "paths-ignore": []})
            unter = None
            # Fließform `push: [paths]` gibt es im Bestand nicht; ein nicht
            # leerer Wert an dieser Stelle wäre eine ungeprüfte Form.
            continue
        if not ereignis:
            continue
        if treffer:
            unter = treffer.group(2)
            if unter in ("paths", "paths-ignore"):
                ergebnis[ereignis].setdefault(unter, [])
                rest = _wert(treffer.group(3))
                if rest.startswith("["):
                    raise ValueError(
                        f"Fließform in {ereignis}.{unter} wird nicht gelesen: {rest}")
            continue
        gestrichen = zeile.lstrip()
        if gestrichen.startswith("- ") and unter in ("paths", "paths-ignore"):
            wert = _wert(gestrichen[2:])
            if wert:
                ergebnis[ereignis][unter].append(wert)
    return ergebnis


# --------------------------------------------------------------------------- #
#  Aufrufe im Workflow
# --------------------------------------------------------------------------- #
def _run_bloecke(text: str) -> list[str]:
    """Alle `run:`-Inhalte – Blockform (`run: |`) und einzeilig."""
    zeilen = text.splitlines()
    bloecke: list[str] = []
    i = 0
    while i < len(zeilen):
        treffer = re.match(r"^(\s*)(?:-\s+)?run:\s*(.*)$", zeilen[i])
        if not treffer:
            i += 1
            continue
        einrueckung = len(treffer.group(1))
        rest = treffer.group(2).strip()
        i += 1
        if rest in ("|", ">", "|-", ">-", "|+", ">+", ""):
            rumpf: list[str] = []
            while i < len(zeilen):
                zeile = zeilen[i]
                if not zeile.strip():
                    rumpf.append("")
                    i += 1
                    continue
                if len(zeile) - len(zeile.lstrip()) <= einrueckung:
                    break
                rumpf.append(zeile)
                i += 1
            bloecke.append("\n".join(rumpf))
        else:
            bloecke.append(rest)
    return bloecke


def aufrufe(text: str, root: Path) -> set[str]:
    """Repo-Pfade, die dieser Workflow in `run:`-Blöcken wirklich aufruft.

    Nur existierende Dateien zählen: Eine Zeile über eine Datei, die es nicht
    (mehr) gibt, ist kein Aufruf, sondern Altlast.
    """
    gefunden: set[str] = set()
    for block in _run_bloecke(text):
        for zeile in block.splitlines():
            if zeile.lstrip().startswith("#"):
                continue
            for pfad in AUFRUF.findall(zeile):
                if (root / pfad).is_file():
                    gefunden.add(pfad)
            for modul in MODULTEST.findall(zeile):
                pfad = modul.replace(".", "/") + ".py"
                if (root / pfad).is_file():
                    gefunden.add(pfad)
    return gefunden


def _glob_muster(muster: str) -> "re.Pattern[str]":
    """Übersetzt einen GitHub-`paths`-Glob in einen regulären Ausdruck.

    WARUM NICHT `fnmatch` (Befund der eigenen Gegenprobe, 27.10.2026): In
    `fnmatch` trifft `*` AUCH den Schrägstrich. Damit hätte
    `scripts/*.py` den Pfad `scripts/tests/foo.py` „gedeckt“ – die Wache
    hätte eine Lücke als Deckung gemeldet und wäre selbst die stille Wache
    gewesen, gegen die sie antritt. GitHubs Filter kennen diese Bedeutung
    nicht:

        *     beliebige Zeichen AUSSER `/`      (eine Ebene)
        **    beliebige Zeichen MIT `/`         (über Ebenen)
        **/   null oder mehr Verzeichnisse
        ?     ein Zeichen außer `/`
    """
    i = 0
    aus: list[str] = []
    while i < len(muster):
        zeichen = muster[i]
        if muster.startswith("**/", i):
            aus.append("(?:[^/]+/)*")
            i += 3
            continue
        if muster.startswith("**", i):
            aus.append(".*")
            i += 2
            continue
        if zeichen == "*":
            aus.append("[^/]*")
        elif zeichen == "?":
            aus.append("[^/]")
        elif zeichen == "[" and "]" in muster[i + 1:]:
            ende = muster.index("]", i + 1)
            klasse = muster[i + 1:ende]
            if klasse.startswith("!"):
                klasse = "^" + klasse[1:]
            aus.append("[" + klasse + "]")
            i = ende
        else:
            aus.append(re.escape(zeichen))
        i += 1
    return re.compile("^" + "".join(aus) + "$")


@lru_cache(maxsize=512)
def _muster_regex(muster: str) -> "re.Pattern[str]":
    return _glob_muster(muster)


def gedeckt(pfad: str, muster: Iterable[str]) -> bool:
    """Deckt einer der `paths`-Einträge den Pfad – mit GitHubs Glob-Regeln?"""
    return any(_muster_regex(eintrag).match(pfad) for eintrag in muster)


# --------------------------------------------------------------------------- #
#  Prüfung
# --------------------------------------------------------------------------- #
def workflow_dateien(root: Path) -> list[Path]:
    ordner = root / WORKFLOW_DIR
    if not ordner.is_dir():
        return []
    return sorted([*ordner.glob("*.yml"), *ordner.glob("*.yaml")])


def pruefe(root: Path = BLOG_DIR) -> list[Befund]:
    befunde: list[Befund] = []
    for datei in workflow_dateien(root):
        name = datei.relative_to(root / WORKFLOW_DIR).as_posix()
        text = datei.read_text(encoding="utf-8")
        ereignisse = trigger(text)
        if not ereignisse:
            continue
        refs = aufrufe(text, root)

        for ereignis, conf in ereignisse.items():
            muster = conf.get("paths") or []
            if not muster or ereignis not in GESPIEGELT:
                continue
            ignoriert = conf.get("paths-ignore") or []
            for pfad in sorted(refs):
                if gedeckt(pfad, muster) or (ignoriert and gedeckt(pfad, ignoriert)):
                    continue
                befunde.append(Befund(
                    REGEL_REFERENZ, name, ereignis,
                    f"`{pfad}` wird aufgerufen, aber der `{ereignis}`-Filter nennt "
                    f"die Datei nicht – eine Änderung daran löst diesen Lauf nicht aus.",
                ))

        # W2 · Waise (Platzhalter sind keine Datei-Aussage)
        for ereignis, conf in ereignisse.items():
            for art in ("paths", "paths-ignore"):
                for eintrag in conf.get(art) or []:
                    if any(zeichen in eintrag for zeichen in "*?["):
                        continue
                    if (root / eintrag).exists():
                        continue
                    befunde.append(Befund(
                        REGEL_WAISE, name, ereignis,
                        f"`{art}` nennt `{eintrag}` – diese Datei gibt es nicht (mehr) "
                        f"im Repository.",
                    ))

        # W3 · Symmetrie der beiden handgepflegten Kopien
        if all(ereignis in ereignisse for ereignis in GESPIEGELT):
            links = set(ereignisse["push"].get("paths") or [])
            rechts = set(ereignisse["pull_request"].get("paths") or [])
            for nur, seite in ((links - rechts, "pull_request"), (rechts - links, "push")):
                for eintrag in sorted(nur):
                    befunde.append(Befund(
                        REGEL_SYMMETRIE, name, "push/pull_request",
                        f"`{eintrag}` steht nur in einer der beiden Listen; fehlt bei "
                        f"`{seite}` – die Prüfung läuft dort nicht.",
                    ))
    return befunde


def bericht(befunde: Sequence[Befund], geprueft: int) -> str:
    zeilen = ["# Trigger-Wache – was ein Lauf prüft, muss ihn auch auslösen", ""]
    zeilen.append(f"Workflows geprüft: **{geprueft}** · Befunde: **{len(befunde)}**")
    zeilen.append("")
    if not befunde:
        zeilen.append("Keine Befunde: Jeder aufgerufene Prüfer löst seinen Lauf aus.")
        return "\n".join(zeilen) + "\n"
    for befund in befunde:
        zeilen.append(f"- **{befund.regel}** · `{befund.workflow}` ({befund.ereignis}) "
                      f"– {befund.text}")
    return "\n".join(zeilen) + "\n"


# --------------------------------------------------------------------------- #
#  Sabotage- und Gegenproben
# --------------------------------------------------------------------------- #
def _kleiner_workflow(pfade: list[str], *, ereignis: str = "push",
                      zweite: list[str] | None = None) -> str:
    def block(name: str, liste: list[str]) -> list[str]:
        return [f"  {name}:", "    paths:"] + [f'      - "{p}"' for p in liste]

    zeilen = ["name: Probe", "on:"]
    zeilen += block(ereignis, pfade)
    if zweite is not None:
        zeilen += block("pull_request", zweite)
    zeilen += ["", "jobs:", "  pruefen:", "    runs-on: ubuntu-24.04", "    steps:",
               "      - name: Prüfen", "        run: |", "          set -euo pipefail",
               "          python3 scripts/probe.py --selftest"]
    return "\n".join(zeilen) + "\n"


def selftest() -> int:
    import tempfile

    fehler: list[str] = []

    def probe(name: str, bedingung: bool, detail: object = "") -> None:
        if not bedingung:
            fehler.append(f"{name}: {detail}" if detail else name)

    # --- 1 · Parser: kommentierte Werte, Anführungszeichen, Ignorierliste --
    text = """
name: Probe
on:
  push:
    branches: [main]
    paths:
      - "content/**"
      - 'layouts/x.html'   # Kommentar
  pull_request:
    paths-ignore:
      - "docs/**"
  schedule:
    - cron: "0 6 * * *"
jobs:
  a:
    runs-on: ubuntu-24.04
    steps:
      - run: python3 scripts/a.py
        name: inline
      - name: Block
        run: |
          # python3 scripts/kommentar.py
          python3 scripts/b.py --x
"""
    conf = trigger(text)
    probe("Parser/push-pfade", conf["push"]["paths"] == ["content/**", "layouts/x.html"],
           conf["push"]["paths"])
    probe("Parser/pull_request-ignore", conf["pull_request"]["paths-ignore"] == ["docs/**"],
           conf["pull_request"])
    probe("Parser/schedule-ohne-pfade", conf["schedule"]["paths"] == [])

    # --- 2 · Aufrufe: Datei muss existieren, Kommentar zählt nicht --------
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "scripts").mkdir()
        for name in ("probe.py", "a.py", "b.py"):
            (root / "scripts" / name).write_text("", encoding="utf-8")
        (root / "scripts" / "tests").mkdir()
        (root / "scripts" / "tests" / "test_c.py").write_text("", encoding="utf-8")
        test_text = (
            "on:\n  push:\n    paths:\n      - scripts/**\n"
            "jobs:\n  a:\n    steps:\n"
            "      - name: X\n        run: |\n"
            "          python3 scripts/a.py\n"
            "          # python3 scripts/erfunden.py\n"
            "          python3 scripts/fehlt.py\n"
            "          python3 -m unittest scripts.tests.test_c\n"
        )
        gefunden = aufrufe(test_text, root)
        probe("Aufrufe/echte_datei", gefunden == {"scripts/a.py", "scripts/tests/test_c.py"},
               gefunden)

        # --- 3 · W1 feuert und schweigt im Gegenfall ----------------------
        (root / ".github" / "workflows").mkdir(parents=True)
        (root / ".github" / "workflows" / "gruen.yml").write_text(
            _kleiner_workflow(["scripts/probe.py"]) + "\n# zweiter Trigger\n",
            encoding="utf-8")
        (root / ".github" / "workflows" / "rot.yml").write_text(
            _kleiner_workflow(["scripts/anders.py"], zweite=["scripts/probe.py"]),
            encoding="utf-8")
        befunde = pruefe(root)
        regeln = {(b.regel, b.workflow, b.ereignis) for b in befunde}
        probe("W1/fehlt_im_push", (REGEL_REFERENZ, "rot.yml", "push") in regeln, regeln)
        probe("W1/kein_befund_im_pull_request",
               (REGEL_REFERENZ, "rot.yml", "pull_request") not in regeln, regeln)
        probe("W1/gruener_workflow_ohne_befund",
               not any(b.workflow == "gruen.yml" for b in befunde),
               [b for b in befunde if b.workflow == "gruen.yml"])

        # --- 4 · W2 Waise -------------------------------------------------
        (root / ".github" / "workflows" / "waise.yml").write_text(
            _kleiner_workflow(["scripts/probe.py", "docs/gibt-es-nicht.md"]),
            encoding="utf-8")
        befunde = pruefe(root)
        waisen = [b for b in befunde if b.regel == REGEL_WAISE and b.workflow == "waise.yml"]
        probe("W2/waise_erkannt", len(waisen) == 1, waisen)

        # --- 5 · W3 Symmetrie ---------------------------------------------
        (root / ".github" / "workflows" / "schief.yml").write_text(
            _kleiner_workflow(["scripts/probe.py"], zweite=["scripts/probe.py", "scripts/a.py"]),
            encoding="utf-8")
        befunde = pruefe(root)
        schief = [b for b in befunde if b.regel == REGEL_SYMMETRIE and b.workflow == "schief.yml"]
        probe("W3/asymmetrie_erkannt", len(schief) == 1 and "scripts/a.py" in schief[0].text,
               schief)

        # --- 6 · Fließform wird nicht geraten, sondern gemeldet -----------
        try:
            trigger("on:\n  push:\n    paths: [a, b]\n")
        except ValueError:
            pass
        else:
            fehler.append("Fließform: ungeprüfte Form wurde stillschweigend akzeptiert")

    # --- 7 · Der echte Bestand: Selbsttest darf eigene Befunde melden ---
    if fehler:
        print("❌ Trigger-Wache-Selbsttest fehlgeschlagen:", file=sys.stderr)
        for eintrag in fehler:
            print(f"   · {eintrag}", file=sys.stderr)
        return 2
    print("✅ Trigger-Wache-Selbsttest bestanden (Parser, W1, W2, W3, Fließform-Sperre).")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modus = parser.add_mutually_exclusive_group(required=True)
    modus.add_argument("--check", action="store_true", help="Bestand prüfen")
    modus.add_argument("--md", action="store_true", help="Markdown-Bericht ausgeben")
    modus.add_argument("--selftest", action="store_true", help="Sabotage- und Gegenproben")
    parser.add_argument("--root", default=str(BLOG_DIR), help="Wurzel (Tests)")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    root = Path(args.root).resolve()
    try:
        befunde = pruefe(root)
    except (OSError, UnicodeError, ValueError) as fehler:
        print(f"❌ Trigger-Wache nicht durchführbar: {fehler}", file=sys.stderr)
        return 2
    geprueft = len(workflow_dateien(root))

    if args.md:
        print(bericht(befunde, geprueft))
        return 1 if befunde else 0

    print(bericht(befunde, geprueft))
    if not befunde:
        print(f"✅ Trigger-Wache: {geprueft} Workflows, keine Befunde.")
        return 0
    print(f"❌ Trigger-Wache: {len(befunde)} Befund(e).", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
