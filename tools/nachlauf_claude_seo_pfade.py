#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""nachlauf_claude_seo_pfade.py – die zwei Eingriffe am vendorten claude-seo
wiederherstellen, die `npx skills update` nicht kennt.

WARUM (01.11.2026)
------------------
Die 26 Skills aus `AgriciDaniel/claude-seo` rufen ihre Werkzeuge als
`"${CLAUDE_PLUGIN_ROOT}/scripts/claude-seo" run <script.py>` auf. Diese Variable
setzt nur ein Plugin; in diesem Checkout liegt die Runtime deshalb im Hub-Ordner
`.claude/skills/seo/` und der Token ist auf den Repo-Pfad umgeschrieben (genau
wie es das Upstream-`install.sh` für Handinstallationen mit `$HOME` tut).

Der Skills-CLI weiß davon nichts: `npx skills update` kopiert wieder den
Upstream-Stand, also die Plugin-Variable zurück. Danach zeigen 32 Dokumente auf
einen Pfad, den es nicht gibt – der Fehler ist stumm, weil kein Gate die
Markdown-Dateien fremder Skills prüft.

Dieses Skript ist der Nachlauf: es schreibt den Repo-Pfad erneut, ist idempotent
(zweiter Lauf ändert nichts) und meldet mit `--check`, ob ein Update dazwischen
lag. Aufruf nach jedem `update`:

    python3 tools/nachlauf_claude_seo_pfade.py           # schreiben
    python3 tools/nachlauf_claude_seo_pfade.py --check   # nur melden (Exit 1)

Die Lizenzdateien (`LICENSE.txt` = unveränderter MIT-Volltext) setzt der
Nachlauf mit, weil der CLI dort wieder die 143-Byte-Zeiger des Upstreams
ablegt. Quelle für beides ist ein flacher Klon des Upstreams.

Exit: 0 = sauber bzw. geschrieben · 1 = --check fand Plugin-Token · 2 = Quelle
fehlt oder Ziel fehlt.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BLOG_DIR = Path(__file__).resolve().parent.parent
SKILL_ORDNER = BLOG_DIR / ".claude" / "skills"
HUB = "seo"
UPSTREAM = "https://github.com/AgriciDaniel/claude-seo.git"

# Reihenfolge: längste Form zuerst, sonst frisst die kurze Präfix-Form die
# spezifischere und der Launcher landet unter dem falschen Wurzelpfad.
ERSETZUNGEN = (
    ("${CLAUDE_PLUGIN_ROOT}/scripts/claude-seo", ".claude/skills/seo/scripts/claude-seo"),
    ("${CLAUDE_PLUGIN_ROOT}/skills/", ".claude/skills/"),
    ("${CLAUDE_PLUGIN_ROOT}/hooks/", ".claude/skills/seo/hooks/"),
    ("${CLAUDE_PLUGIN_ROOT}/schema/", ".claude/skills/seo/schema/"),
    ("${CLAUDE_PLUGIN_ROOT}/data/", ".claude/skills/seo/data/"),
)
RUNTIME_TEILE = ("scripts", "schema", "data", "hooks")
TOKEN = "${CLAUDE_PLUGIN_ROOT}"


def skill_ordner() -> list[Path]:
    """Der Hub und seine 25 Geschwister – nichts anderes unter .claude/skills."""
    if not SKILL_ORDNER.is_dir():
        return []
    return sorted(p for p in SKILL_ORDNER.iterdir()
                  if p.is_dir() and (p.name == HUB or p.name.startswith(f"{HUB}-")))


def token_funde() -> list[tuple[Path, int]]:
    funde: list[tuple[Path, int]] = []
    for d in skill_ordner():
        for f in sorted(d.rglob("*.md")):
            for nr, zeile in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if TOKEN in zeile:
                    funde.append((f.relative_to(BLOG_DIR), nr))
    return funde


def schreibe_pfade() -> int:
    geaendert = 0
    for d in skill_ordner():
        for f in sorted(d.rglob("*.md")):
            alt = f.read_text(encoding="utf-8")
            neu = alt
            for muster, ziel in ERSETZUNGEN:
                neu = neu.replace(muster, ziel)
            if neu != alt:
                f.write_text(neu, encoding="utf-8")
                geaendert += 1
    return geaendert


def hole_upstream() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="claude-seo-"))
    subprocess.run(["git", "clone", "--depth", "1", "-q", UPSTREAM, str(tmp / "repo")],
                   check=True, capture_output=True)
    return tmp / "repo"


def schreibe_runtime(quelle: Path) -> None:
    ziel = SKILL_ORDNER / HUB
    if not ziel.is_dir():
        raise FileNotFoundError(f"{ziel.relative_to(BLOG_DIR)} fehlt – erst `npx skills add` laufen lassen")
    # dirs_exist_ok: der zweite Lauf legt NICHT `scripts/scripts` an – genau den
    # Fehler würde ein `cp -r quelle/scripts ziel/scripts` bei vorhandenem Ziel machen.
    for teil in RUNTIME_TEILE:
        src = quelle / teil
        if src.is_dir():
            shutil.copytree(src, ziel / teil, dirs_exist_ok=True)
    req = quelle / "requirements.txt"
    if req.is_file():
        shutil.copy2(req, ziel / "requirements.txt")
    launcher = ziel / "scripts" / "claude-seo"
    if launcher.is_file():
        launcher.chmod(0o755)


def schreibe_lizenzen(quelle: Path) -> int:
    text = (quelle / "LICENSE").read_bytes()
    if not text.startswith(b"MIT License"):
        raise ValueError("Upstream-Lizenz ist nicht MIT – Nachlauf prüfen")
    geschrieben = 0
    for d in skill_ordner():
        ziel = d / "LICENSE.txt"
        if not ziel.is_file() or ziel.read_bytes() != text:
            ziel.write_bytes(text)
            geschrieben += 1
    return geschrieben


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--check", action="store_true", help="nur melden, nichts schreiben")
    args = p.parse_args()

    ordner = skill_ordner()
    if not ordner:
        print("✗ keine claude-seo-Skills unter .claude/skills – nichts nachzulaufen", file=sys.stderr)
        return 2

    if args.check:
        funde = token_funde()
        if funde:
            print(f"🛑 {len(funde)} Plugin-Token in {len({f for f, _ in funde})} Datei(en) – "
                  "ein `npx skills update` lag dazwischen:")
            for f, nr in funde[:10]:
                print(f"   {f}:{nr}")
            print("Heilung: python3 tools/nachlauf_claude_seo_pfade.py")
            return 1
        print(f"✅ {len(ordner)} Skill-Ordner, kein Plugin-Token – Pfade zeigen auf den Repo-Pfad")
        return 0

    geaendert = schreibe_pfade()
    quelle = hole_upstream()
    schreibe_runtime(quelle)
    lizenzen = schreibe_lizenzen(quelle)
    print(f"✅ {len(ordner)} Skill-Ordner · {geaendert} Dokument(e) umgeschrieben · "
          f"{lizenzen} Lizenztext(e) gesetzt · Runtime aus {quelle.name}")
    rest = token_funde()
    if rest:
        print(f"🛑 danach noch {len(rest)} Token – Muster in ERSETZUNGEN ergänzen", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
