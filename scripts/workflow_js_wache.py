#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
#  WORKFLOW-JS-WACHE – auch das Skript IM Workflow muss kompilieren
#  ------------------------------------------------------------
#  WARUM ES DIESE WACHE GIBT (Vorgang WF-829B / #922, 29.10.2026)
#
#  Am 29.10.2026 wurde PR #943 (Zugangs-Diagnose des Worker-Deploys)
#  zusammengeführt. Der Squash-Merge traf eine zwischenzeitlich
#  gewanderte `main` (Environment-Gate aus #935). Ergebnis in
#  `.github/workflows/alert-on-failure.yml` – dem Herzen des gesamten
#  Fehler-Alertings:
#
#      '4. Runbook: … lokal ohne Netz prüfbar mit `… --pruefen`.'
#      '1. **Fail-closed – gewollt, kein Betriebsausfall.** Lies den …'
#
#  Zwei Zeichenketten ohne Komma: `SyntaxError: Unexpected string`.
#  Dazu eine verwaiste `failedStepNames.some(…)`-Zeile, die den
#  Environment-Gate aus #935 aus der Erkennung herauswarf. Der Runner
#  führt den `script:`-Block von `actions/github-script` als Funktion
#  aus – ein Syntaxfehler lässt JEDEN Lauf dieses Workflows sterben.
#  Konkret: Das Fehler-Alerting war auf `main` tot, und niemand hätte
#  davon erfahren, weil genau der Kanal fehlte, der solche Ausfälle
#  meldet. Aufgefallen ist es nur, weil ein Python-Test das Skript
#  über `new Function` nachbaut – in einem Schritt, dessen Name nach
#  etwas ganz anderem klingt.
#
#  Das ist exakt die Klasse, für die „Skript-Syntax (liegender Stand)"
#  existiert (#864, ein halb zusammengeführter `redaktions_standard.py`).
#  Damals ging es nur um Python. Der Block IN einem Workflow ist
#  JavaScript, lebt in YAML und wird von keiner Python-Prüfung berührt.
#
#  WAS DIESE WACHE PRÜFT
#  ---------------------
#    J1  Ein `uses: actions/github-script@…`-Schritt, der einen
#        `script:`-Block trägt, wird extrahiert (Einrückung, nicht
#        Regex-Raten) und mit `node --check` kompiliert.
#    J2  Ein `github-script`-Schritt OHNE `script:`-Block ist ein
#        Befund – der Lauf würde nichts tun und trotzdem grün melden.
#    J3  Ein extrahierter Block, der leer ist, ist ein Befund.
#
#  Fail-closed auch für den Prüfer selbst: Fehlt `node`, ist die
#  Prüfung NICHT durchgeführt (Exit 2), nicht bestanden. Eine
#  ausgefallene Messung ist kein Grün (Vertrag C33 dieses Repos).
#
#  NUTZUNG
#    python3 scripts/workflow_js_wache.py --check
#    python3 scripts/workflow_js_wache.py --md      # Markdown für die Summary
#    python3 scripts/workflow_js_wache.py --selftest
#
#  EXIT: 0 = alles kompiliert · 1 = Befund · 2 = Prüfung nicht möglich
#  (Selbsttest: 2 = Wache defekt.)
# ============================================================
"""Kompiliert die Inline-JavaScript-Blöcke aller Workflows (node --check)."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_DIR = ROOT / ".github" / "workflows"

GITHUB_SCRIPT = re.compile(r"uses:\s*actions/github-script@")
SCRIPT_KEY = re.compile(r"^(\s*)script:\s*(\||>)?\s*$")
SCHLUESSEL = re.compile(r"^(\s*)([A-Za-z0-9_.-]+):")


@dataclass(frozen=True)
class Block:
    datei: str
    zeile: int          # 1-basiert, Zeile von `script:`
    code: str


def _einrueckung(zeile: str) -> int:
    return len(zeile) - len(zeile.lstrip(" "))


def bloecke(text: str, dateiname: str) -> tuple[list[Block], list[str]]:
    """Sammelt alle github-script-Blöcke; meldet J2 (Schritt ohne Skript)."""
    zeilen = text.splitlines()
    gefunden: list[Block] = []
    befunde: list[str] = []
    for nummer, zeile in enumerate(zeilen):
        if not GITHUB_SCRIPT.search(zeile):
            continue
        # Der Block gehört zum Schritt: alles bis zur nächsten Zeile mit
        # gleicher oder kleinerer Einrückung und einem Schlüssel davor.
        schritt_einrueckung = _einrueckung(zeile)
        # Grenze des Schritts: die nächste Zeile, die WENIGER eingerückt ist
        # oder auf derselben Ebene mit einem Listeneintrag beginnt. Ein
        # `with:`/`env:`/`script:` desselben Schritts ist +2 eingerückt und
        # beendet ihn deshalb NICHT (sonst wären 13 echte Blöcke „leer“).
        ende = nummer + 1
        while ende < len(zeilen):
            folge = zeilen[ende]
            if folge.strip():
                einzug = _einrueckung(folge)
                if einzug < schritt_einrueckung:
                    break
                if einzug == schritt_einrueckung and folge.lstrip().startswith("- "):
                    break
            ende += 1
        kopf = zeile
        for index in range(nummer + 1, ende):
            if SCRIPT_KEY.match(zeilen[index]):
                kopf = zeilen[index]
                start = index + 1
                einrueckung = len(SCRIPT_KEY.match(zeilen[index]).group(1)) + 2
                code: list[str] = []
                while start < len(zeilen):
                    kandidat = zeilen[start]
                    if kandidat.strip() and _einrueckung(kandidat) < einrueckung:
                        break
                    code.append(kandidat[einrueckung:] if len(kandidat) >= einrueckung else "")
                    start += 1
                koerper = "\n".join(code).strip("\n")
                if not koerper.strip():
                    befunde.append(f"J3 {dateiname}:{index + 1}: leerer github-script-Block – "
                                   "der Lauf würde nichts tun und grün melden.")
                else:
                    gefunden.append(Block(dateiname, index + 1, koerper))
                break
        else:
            befunde.append(f"J2 {dateiname}:{nummer + 1}: github-script-Schritt ohne "
                           "`script:`-Block – der Schritt hätte nichts auszuführen.")
        _ = kopf
    return gefunden, befunde


def sammeln(wurzel: Path | None = None) -> tuple[list[Block], list[str]]:
    wurzel = ROOT if wurzel is None else wurzel
    verzeichnis = wurzel / ".github" / "workflows"
    if not verzeichnis.is_dir():
        raise FileNotFoundError(f"{verzeichnis} fehlt")
    bloecke_alle: list[Block] = []
    befunde: list[str] = []
    for pfad in sorted(verzeichnis.glob("*.yml")) + sorted(verzeichnis.glob("*.yaml")):
        relativ = pfad.relative_to(wurzel).as_posix()
        gefunden, eigene = bloecke(pfad.read_text(encoding="utf-8"), relativ)
        bloecke_alle.extend(gefunden)
        befunde.extend(eigene)
    return bloecke_alle, befunde


def node_pruefen(code: str, node: str, timeout: float = 60.0) -> tuple[bool, str]:
    """(ok, meldung). Schreibt den Block in eine temporäre Datei."""
    # github-script führt den Block als RUMPF einer async-Funktion aus.
    # Genau so wird er geprüft – sonst wären `await` und `return` auf
    # oberster Ebene „Fehler“, die es in Wahrheit nicht sind (fünf
    # Fehlalarme im Bestand: affiliate-integrity-daily, alert-on-failure,
    # bot-watchdog, deploy-catchup, layout-ai).
    umhuellt = "(async () => {\n" + code + "\n})();\n"
    with tempfile.TemporaryDirectory(prefix="workflow-js-") as ordner:
        pfad = Path(ordner) / "block.js"
        pfad.write_text(umhuellt, encoding="utf-8")
        try:
            lauf = subprocess.run([node, "--check", str(pfad)], capture_output=True,
                                  text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return False, "Prüfung hat das Zeitlimit überschritten"
    if lauf.returncode == 0:
        return True, ""
    meldung = (lauf.stderr or lauf.stdout or "").strip().splitlines()
    kurz = meldung[0] if meldung else f"node --check Exit {lauf.returncode}"
    # Der temporäre Pfad ist für den Leser wertlos.
    return False, kurz.replace(str(pfad), "block.js")


_AUTO = object()  # „nicht angegeben“ – sonst wäre node=None die Autosuche


def _stelle(block: Block, meldung: str) -> str:
    """Übersetzt `block.js:567` in die Zeile der Workflow-Datei.

    Zeile 1 des geprüften Textes ist die Umhüllung; `script:` steht in
    Zeile `block.zeile`, der Block beginnt in der Zeile danach.
    """
    treffer = re.search(r"block\.js:(\d+)", meldung)
    if not treffer:
        return f"Block ab Workflow-Zeile {block.zeile}"
    return f"Workflow-Zeile {block.zeile + int(treffer.group(1)) - 2}"


def pruefen(wurzel: Path | None = None, *, node=_AUTO,
            prüfer=None) -> tuple[int, list[str], str]:
    """(exit_code, befunde, markdown). Fail-closed, wenn node fehlt."""
    node = shutil.which("node") if node is _AUTO else node
    prüfer = prüfer or node_pruefen
    bloecke_alle, befunde = sammeln(wurzel)
    if node is None and prüfer is node_pruefen:
        return 2, ["J0 Prüfung nicht möglich: `node` fehlt im Lauf. Ohne Kompilierung "
                   "ist kein Block bestätigt (ausgefallene Messung ist kein Grün)."], ""
    for block in bloecke_alle:
        ok, meldung = prüfer(block.code, node)
        if not ok:
            befunde.append(f"J1 {block.datei}:{block.zeile}: github-script-Block "
                           f"kompiliert nicht – {meldung} ({_stelle(block, meldung)})")
    status = 0 if not befunde else 1
    zeilen = ["## Workflow-JS-Wache", "",
              f"- github-script-Blöcke geprüft: **{len(bloecke_alle)}**",
              f"- Befunde: **{len(befunde)}**"]
    if befunde:
        zeilen += ["", "```"] + befunde + ["```"]
    return status, befunde, "\n".join(zeilen)


def _selftest() -> int:
    fehler: list[str] = []

    gueltig = """name: Probe
jobs:
  a:
    steps:
      - uses: actions/github-script@1111111111111111111111111111111111111111 # v7
        with:
          script: |
            const x = 1;
            console.log(x);
"""
    kaputt = """name: Probe
jobs:
  a:
    steps:
      - uses: actions/github-script@1111111111111111111111111111111111111111 # v7
        with:
          script: |
            const teile = ['4. Runbook …'
            '1. Fail-closed …'];
"""
    ohne_skript = """name: Probe
jobs:
  a:
    steps:
      - uses: actions/github-script@1111111111111111111111111111111111111111 # v7
        id: leer
"""
    leer = """name: Probe
jobs:
  a:
    steps:
      - uses: actions/github-script@1111111111111111111111111111111111111111 # v7
        with:
          script: |

      - name: danach
        run: echo ok
"""
    # J1: gültiger Block wird gefunden und als genau ein Block erkannt
    gefunden, befunde = bloecke(gueltig, "probe.yml")
    if len(gefunden) != 1 or befunde:
        fehler.append(f"J1: gültiger Block nicht sauber erkannt ({len(gefunden)} Blöcke, {befunde})")
    elif "const x = 1;" not in gefunden[0].code or "console.log(x);" not in gefunden[0].code:
        fehler.append("J1: Blockinhalt unvollständig extrahiert")
    # Der Block muss den Schritt verlassen, ohne die nächste Aktion zu fressen.
    zwei = gueltig + """      - name: danach
        run: echo fertig
"""
    gefunden2, _ = bloecke(zwei, "probe.yml")
    if len(gefunden2) != 1 or "danach" in gefunden2[0].code:
        fehler.append("J1: Extraktion läuft über den Schritt hinaus")

    # J2: Schritt ohne script-Block
    _, befunde2 = bloecke(ohne_skript, "probe.yml")
    if not any(b.startswith("J2") for b in befunde2):
        fehler.append("J2: github-script ohne script-Block nicht erkannt")

    # J3: leerer Block
    _, befunde3 = bloecke(leer, "probe.yml")
    if not any(b.startswith("J3") for b in befunde3):
        fehler.append("J3: leerer Block nicht erkannt")

    # J1 im Verbund: der kaputte Block wird vom Prüfer als Fehler gemeldet.
    def immer_kaputt(code: str, _node):
        return ("'1." not in code), "SyntaxError: Unexpected string"

    with tempfile.TemporaryDirectory(prefix="workflow-js-selbst-") as ordner:
        ziel = Path(ordner) / ".github" / "workflows"
        ziel.mkdir(parents=True)
        (ziel / "gut.yml").write_text(gueltig, encoding="utf-8")
        (ziel / "kaputt.yml").write_text(kaputt, encoding="utf-8")
        status, gefunden, _ = pruefen(Path(ordner), node="node", prüfer=immer_kaputt)
        if status != 1 or not any(b.startswith("J1") and "kaputt.yml" in b for b in gefunden):
            fehler.append("J1: kaputter Block ergab keinen Befund (oder falschen Exit)")

        # Kein github-script im Baum → nichts zu prüfen, aber auch kein Fehler.
        (ziel / "kaputt.yml").unlink()
        status_ok, befunde_ok, _ = pruefen(Path(ordner), node="node", prüfer=node_pruefen)
        if status_ok != 0 or befunde_ok:
            fehler.append(f"gültiger Bestand ergab Befunde: {befunde_ok}")

    # Fail-closed: ohne node wird NICHT grün gemeldet.
    with tempfile.TemporaryDirectory(prefix="workflow-js-node-") as ordner:
        ziel = Path(ordner) / ".github" / "workflows"
        ziel.mkdir(parents=True)
        (ziel / "gut.yml").write_text(gueltig, encoding="utf-8")
        status, befunde, _ = pruefen(Path(ordner), node=None)
        if status != 2 or not any(b.startswith("J0") for b in befunde):
            fehler.append("J0: fehlendes node wurde nicht als nicht-prüfbar gemeldet")

    if fehler:
        for eintrag in fehler:
            print(f"❌ {eintrag}")
        print(f"❌ SELBSTTEST FEHLGESCHLAGEN ({len(fehler)} Fälle)")
        return 2
    print("✅ SELBSTTEST OK — Extraktion, J1/J2/J3 und fail-closed ohne node belegt.")
    return 0


def main(argv: list[str] | None = None) -> int:
    zerleger = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    gruppe = zerleger.add_mutually_exclusive_group(required=True)
    gruppe.add_argument("--check", action="store_true", help="alle Workflows prüfen")
    gruppe.add_argument("--md", action="store_true", help="Markdown für die Lauf-Summary")
    gruppe.add_argument("--json", action="store_true", help="Maschinenausgabe")
    gruppe.add_argument("--selftest", action="store_true", help="Wache selbst prüfen")
    args = zerleger.parse_args(argv)

    if args.selftest:
        return _selftest()
    status, befunde, markdown = pruefen()
    if args.md:
        print(markdown)
    elif args.json:
        print(json.dumps({"status": status, "befunde": befunde, "bloecke": markdown.count("-")}, ensure_ascii=False))
    else:
        if befunde:
            for befund in befunde:
                print(befund)
            print(f"❌ Workflow-JS: {len(befunde)} Befund(e)")
        else:
            print("✅ Workflow-JS: alle github-script-Blöcke kompilieren.")
    return status


if __name__ == "__main__":
    sys.exit(main())
