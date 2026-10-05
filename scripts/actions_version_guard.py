#!/usr/bin/env python3
# ============================================================
#  ACTIONS-VERSIONS-WACHE – eine Version je GitHub-Action, dauerhaft
#
#  AUFTRAG (Dependabot-PR #571 „bump actions/setup-python from 5 to 7",
#  04.–05.10.2026): Dependabot hebt die Action-Versionen an, trifft aber
#  nicht immer jede Fundstelle (Rebase-Konflikte, Teil-Merges, von Hand
#  nachgezogene Workflows). Ergebnis war ein Flickenteppich:
#  setup-python@v6 in EINEM Workflow gegen @v7 in 35 anderen,
#  checkout@v4 gegen @v5, setup-node@v4 gegen @v5, upload-artifact@v4
#  gegen @v7. Solche Drift fällt erst auf, wenn ein alter Runner-Node
#  abgekündigt wird und ein einzelner Nacht-Job stirbt.
#
#  Diese Wache macht die Einheitlichkeit zu einem geprüften Vertrag statt
#  zu einer Fleißaufgabe. Sie läuft in integrity-lock.yml bei JEDEM Pull
#  Request – also auch bei jedem Dependabot-PR – und ist damit die
#  dauerhafte Antwort auf #571, nicht nur eine einmalige Korrektur.
#
#  REGELN
#    A1  KANON-KONSISTENZ: Jede fremde Action wird im gesamten Repository
#        mit GENAU EINER Referenz benutzt. Maßgeblich (Kanon) ist die
#        höchste im Repo vorhandene Major-Version – so genügt EIN
#        angenommener Dependabot-PR, der Rest wird hier eingesammelt.
#    A2  KEINE BEWEGLICHEN ZIELE: @main/@master/@latest oder ganz ohne
#        Referenz ist verboten (Lieferketten-Risiko, nicht reproduzierbar).
#    A3  SHA-PINS SIND ABSICHT: Eine 40-stellige Commit-SHA ist eine
#        bewusste Härtung (Supply-Chain-Pin) und wird nie angefasst und
#        nie als Drift gewertet – sie zählt auch nicht in den Kanon.
#    A4  LOKALE ACTIONS (./.github/actions/...) und Docker-Refs sind frei.
#    A5  AUSNAHMEN nur dokumentiert: KANON_FIX erzwingt für einzelne
#        Actions eine abweichende Version (mit Begründung im Code).
#
#  WIRKUNGSKREIS: Report → Auto-Fix (--fix) → Gate (--gate, Exit 1).
#  Der Fix ist rein textuell (nur die Referenz hinter `uses:` wird
#  ersetzt) – Kommentare, Einrückung und Reihenfolge bleiben unberührt,
#  deshalb braucht die Wache kein YAML-Round-Trip und kann nie einen
#  Workflow umformatieren.
#
#  SELBSTTEST (--selftest, Familienstandard): eingefrorene echte Fälle
#  inklusive Negativ-Fällen („darf nie angefasst werden"). Abweichung =
#  Exit 2, es wird keine Datei geschrieben (Sabotage-Schutz).
#
#  Aufruf:
#    python3 scripts/actions_version_guard.py            # Report
#    python3 scripts/actions_version_guard.py --gate     # CI (Exit 1 bei Drift)
#    python3 scripts/actions_version_guard.py --fix      # vereinheitlichen
#    python3 scripts/actions_version_guard.py --dry-run  # Fix simulieren
#    python3 scripts/actions_version_guard.py --json     # Maschinenlesbar
#    python3 scripts/actions_version_guard.py --selftest # Sabotage-Schutz
# ============================================================

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, NamedTuple, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_DIRS = (".github/workflows", ".github/actions")

# A5 – dokumentierte Ausnahmen. Leer heißt: der Kanon ergibt sich allein aus
# dem Bestand (höchste vorhandene Major-Version). Beispiel für einen Eintrag:
#   "peaceiris/actions-gh-pages": "v4",  # v5 verlangt Node 24-Runner
KANON_FIX: Dict[str, str] = {}

# `uses: owner/repo@ref` bzw. `uses: owner/repo/pfad@ref` – mit und ohne
# Anführungszeichen, als Step-Eintrag (`- uses:`) oder als eigene Zeile.
USES_RE = re.compile(
    r"""^(?P<prefix>\s*(?:-\s+)?uses:\s*)(?P<quote>["']?)(?P<action>[^"'@\s]+)(?:@(?P<ref>[^"'\s]+))?(?P<rest>(?P=quote)\s*(?:#.*)?)$"""
)
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
MAJOR_RE = re.compile(r"^v(\d+)(?:\.(\d+))?(?:\.(\d+))?$")
MOVING_REFS = {"main", "master", "latest", "HEAD"}


class Use(NamedTuple):
    path: str
    line: int
    action: str
    ref: Optional[str]


class Finding(NamedTuple):
    rule: str          # A1 | A2
    path: str
    line: int
    action: str
    ist: str
    soll: Optional[str]
    text: str


# ---------------------------------------------------------------- Einlesen

def is_local(action: str) -> bool:
    """A4 – lokale Composite-Action oder Docker-Referenz."""
    return action.startswith("./") or action.startswith("docker://")


def is_pin(ref: Optional[str]) -> bool:
    """A3 – bewusste Commit-SHA-Härtung."""
    return bool(ref) and bool(SHA_RE.match(ref or ""))


def version_key(ref: str) -> Tuple[int, int, int]:
    m = MAJOR_RE.match(ref)
    if not m:
        return (-1, -1, -1)
    return (int(m.group(1)), int(m.group(2) or 0), int(m.group(3) or 0))


def parse_uses(text: str, path: str = "<memory>") -> List[Use]:
    """Alle `uses:`-Fundstellen einer Datei – Kommentarzeilen werden
    ignoriert (die Composite-Actions dokumentieren ihren Aufruf im Kopf)."""
    out: List[Use] = []
    for no, raw in enumerate(text.splitlines(), start=1):
        if raw.lstrip().startswith("#"):
            continue
        m = USES_RE.match(raw.rstrip("\n"))
        if not m:
            continue
        out.append(Use(path, no, m.group("action"), m.group("ref")))
    return out


def collect(root: Path) -> List[Use]:
    uses: List[Use] = []
    for rel in WORKFLOW_DIRS:
        base = root / rel
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*.y*ml")):
            uses.extend(parse_uses(f.read_text(encoding="utf-8"), str(f.relative_to(root))))
    return uses


# ---------------------------------------------------------------- Bewerten

def build_kanon(uses: Iterable[Use]) -> Dict[str, str]:
    """A1 – je Action die höchste vorhandene Major-Version (SHA-Pins zählen
    nicht mit), überschrieben durch dokumentierte Ausnahmen (A5)."""
    kanon: Dict[str, str] = {}
    for u in uses:
        if is_local(u.action) or not u.ref or is_pin(u.ref) or u.ref in MOVING_REFS:
            continue
        if version_key(u.ref) == (-1, -1, -1):
            continue
        best = kanon.get(u.action)
        if best is None or version_key(u.ref) > version_key(best):
            kanon[u.action] = u.ref
    kanon.update(KANON_FIX)
    return kanon


def analyze(uses: List[Use]) -> Tuple[List[Finding], Dict[str, str]]:
    kanon = build_kanon(uses)
    findings: List[Finding] = []
    for u in uses:
        if is_local(u.action):
            continue
        if is_pin(u.ref):
            continue  # A3
        if not u.ref or u.ref in MOVING_REFS:
            soll = kanon.get(u.action)
            findings.append(
                Finding(
                    "A2", u.path, u.line, u.action, u.ref or "(ohne Referenz)", soll,
                    f"bewegliches Ziel – auf {soll or 'eine feste Version'} festnageln",
                )
            )
            continue
        soll = kanon.get(u.action)
        if soll and u.ref != soll:
            findings.append(
                Finding(
                    "A1", u.path, u.line, u.action, u.ref, soll,
                    f"Versions-Drift – Kanon ist {soll}",
                )
            )
    findings.sort(key=lambda f: (f.path, f.line))
    return findings, kanon


# ---------------------------------------------------------------- Heilen

def fix_text(text: str, kanon: Dict[str, str]) -> Tuple[str, int]:
    out: List[str] = []
    changed = 0
    for raw in text.splitlines(keepends=True):
        line = raw.rstrip("\n")
        nl = raw[len(line):]
        if line.lstrip().startswith("#"):
            out.append(raw)
            continue
        m = USES_RE.match(line)
        if not m:
            out.append(raw)
            continue
        action, ref = m.group("action"), m.group("ref")
        soll = kanon.get(action)
        if (
            not soll
            or is_local(action)
            or is_pin(ref)
            or (ref is not None and ref == soll)
            or (ref is not None and ref not in MOVING_REFS and version_key(ref) == (-1, -1, -1))
        ):
            out.append(raw)
            continue
        out.append(f"{m.group('prefix')}{m.group('quote')}{action}@{soll}{m.group('rest')}{nl}")
        changed += 1
    return "".join(out), changed


def apply_fix(root: Path, kanon: Dict[str, str], dry_run: bool = False) -> List[Tuple[str, int]]:
    touched: List[Tuple[str, int]] = []
    for rel in WORKFLOW_DIRS:
        base = root / rel
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*.y*ml")):
            old = f.read_text(encoding="utf-8")
            new, n = fix_text(old, kanon)
            if n:
                touched.append((str(f.relative_to(root)), n))
                if not dry_run:
                    f.write_text(new, encoding="utf-8")
    return touched


# ---------------------------------------------------------------- Selbsttest

SELFTEST_CASES = [
    # (Eingabe, Kanon, erwartete Ausgabe) – echte Zeilen aus diesem Repo.
    ("        uses: actions/setup-python@v6\n", {"actions/setup-python": "v7"},
     "        uses: actions/setup-python@v7\n"),
    ("      - uses: actions/setup-python@v6\n", {"actions/setup-python": "v7"},
     "      - uses: actions/setup-python@v7\n"),
    ('        uses: "actions/checkout@v4"   # Kommentar bleibt\n', {"actions/checkout": "v5"},
     '        uses: "actions/checkout@v5"   # Kommentar bleibt\n'),
    # Negativ-Fälle: niemals anfassen
    ("        uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n",
     {"actions/checkout": "v5"},
     "        uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n"),
    ("        uses: ./.github/actions/install-hugo\n", {"actions/checkout": "v5"},
     "        uses: ./.github/actions/install-hugo\n"),
    ("#       uses: actions/checkout@v4\n", {"actions/checkout": "v5"},
     "#       uses: actions/checkout@v4\n"),
    ("        uses: github/codeql-action/init@v4\n", {"github/codeql-action/init": "v4"},
     "        uses: github/codeql-action/init@v4\n"),
]


def run_selftest() -> List[str]:
    fails: List[str] = []

    for src, kanon, want in SELFTEST_CASES:
        got, _ = fix_text(src, kanon)
        if got != want:
            fails.append(f"fix_text: {src.strip()!r} → {got.strip()!r} statt {want.strip()!r}")

    # Kanon = höchste Major, SHA-Pins zählen nicht mit
    uses = [
        Use("a.yml", 1, "actions/checkout", "v4"),
        Use("b.yml", 2, "actions/checkout", "v5"),
        Use("c.yml", 3, "actions/checkout", "11d5960a326750d5838078e36cf38b85af677262"),
        Use("d.yml", 4, "./.github/actions/hugo-build", None),
    ]
    findings, kanon = analyze(uses)
    if kanon.get("actions/checkout") != "v5":
        fails.append(f"Kanon falsch: {kanon}")
    rules = sorted((f.rule, f.path) for f in findings)
    if rules != [("A1", "a.yml")]:
        fails.append(f"Befunde falsch: {rules}")

    # A2 – bewegliches Ziel
    findings, _ = analyze([
        Use("a.yml", 1, "foo/bar", "main"),
        Use("b.yml", 2, "foo/bar", "v2"),
    ])
    if [f.rule for f in findings] != ["A2"]:
        fails.append(f"A2 nicht erkannt: {findings}")

    # Parser: Kommentarzeilen und Nicht-Treffer
    parsed = parse_uses("#  uses: actions/checkout@v4\n      - uses: actions/checkout@v5\n")
    if [u.ref for u in parsed] != ["v5"]:
        fails.append(f"Parser falsch: {parsed}")

    # Idempotenz: ein zweiter Lauf darf nichts mehr ändern
    once, _ = fix_text("      - uses: actions/setup-python@v6\n", {"actions/setup-python": "v7"})
    twice, n2 = fix_text(once, {"actions/setup-python": "v7"})
    if twice != once or n2 != 0:
        fails.append("Fix ist nicht idempotent")

    return fails


# ---------------------------------------------------------------- Ausgabe

def report(findings: List[Finding], kanon: Dict[str, str]) -> str:
    lines = ["🔧 ACTIONS-VERSIONS-WACHE", ""]
    lines.append("Kanon (höchste im Repo vorhandene Version je Action):")
    for action in sorted(kanon):
        lines.append(f"  · {action}@{kanon[action]}")
    lines.append("")
    if not findings:
        lines.append("✅ Keine Drift – jede Action wird überall mit derselben Version benutzt.")
        return "\n".join(lines)
    lines.append(f"❌ {len(findings)} Fundstelle(n) mit abweichender Version:")
    for f in findings:
        lines.append(f"  [{f.rule}] {f.path}:{f.line}  {f.action}@{f.ist} → {f.soll}  ({f.text})")
    lines.append("")
    lines.append("Heilung: python3 scripts/actions_version_guard.py --fix")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Eine Version je GitHub-Action – Wache & Heilung.")
    ap.add_argument("--fix", action="store_true", help="Drift vereinheitlichen")
    ap.add_argument("--dry-run", action="store_true", help="Fix nur simulieren")
    ap.add_argument("--gate", action="store_true", help="Exit 1 bei Drift (CI)")
    ap.add_argument("--json", action="store_true", help="Maschinenlesbare Ausgabe")
    ap.add_argument("--selftest", action="store_true", help="Sabotage-Schutz")
    ap.add_argument("--root", default=str(ROOT), help="Repo-Wurzel")
    args = ap.parse_args(argv)

    if args.selftest:
        fails = run_selftest()
        if fails:
            print("❌ Selbsttest fehlgeschlagen:")
            for f in fails:
                print(f"   · {f}")
            return 2
        print(f"✅ Selbsttest bestanden ({len(SELFTEST_CASES)} Fix-Fälle + Kanon-, A2-, Parser- und Idempotenz-Probe).")
        return 0

    root = Path(args.root).resolve()
    uses = collect(root)
    findings, kanon = analyze(uses)

    if args.fix or args.dry_run:
        touched = apply_fix(root, kanon, dry_run=args.dry_run)
        total = sum(n for _, n in touched)
        verb = "würde ändern" if args.dry_run else "geändert"
        print(f"🔧 {total} Referenz(en) in {len(touched)} Datei(en) {verb}.")
        for path, n in touched:
            print(f"   · {path}: {n}")
        if not args.dry_run:
            findings, kanon = analyze(collect(root))

    if args.json:
        print(json.dumps({
            "kanon": kanon,
            "fundstellen": [f._asdict() for f in findings],
            "drift": len(findings),
        }, ensure_ascii=False, indent=2))
    else:
        print(report(findings, kanon))

    if findings and args.gate:
        print("::error::Actions-Versions-Drift – heilen mit: python3 scripts/actions_version_guard.py --fix")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
