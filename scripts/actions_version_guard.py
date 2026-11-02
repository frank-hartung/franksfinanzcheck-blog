#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Actions-Pin-Wache: ein Commit und eine Version je Anbieter-Repository.

Die ursprüngliche Wache aus #571 verglich nur Tags. Seit der SHA-Pflicht
(M-09) übersprang sie damit den gesamten Bestand: 59 setup-python-Aufrufe
hätten auseinanderlaufen können, ohne dass A1 anschlug. PR #1014 machte
diese Lücke sichtbar. Diese Fassung prüft deshalb gerade die SHA-Pins.

Vertrag (offline, ohne Netz und ohne Schreibzugriff im Gate):
  A1  Alle Aufrufe eines Anbieter-Repos benutzen denselben SHA und dieselbe
      Version. Unteraktionen wie codeql-action/init und /analyze gehören
      zusammen. Workflows und Composite-Actions gehören zusammen.
  A2  Fremde Actions brauchen eine vollständige, kleingeschriebene Commit-SHA.
      Tags, Branches und fehlende Referenzen sind keine Supply-Chain-Pins.
  A3  Jeder Pin trägt genau einen Versionskommentar ``# vX.Y.Z``. Ein SHA
      darf nicht unter zwei Versionen geführt werden.
  A4  Lokale Actions (./.github/actions/...) und docker:// sind ausgenommen.

Mehrere gültige SHA/Version-Paare sind ein Befund, aber KEIN automatischer
Kandidat: die lexikalisch größere SHA ist nicht das neuere Release, und ein
Kommentar beweist keine Herkunft. ``--fix`` ergänzt bzw. berichtigt deshalb
nur den Kommentar eines bereits eindeutig feststehenden SHAs. Es wählt nie
zwischen Releases. Teil-Bumps werden über Dependabot vollständig aktualisiert.

Die Anbieter-Existenz und Eingabe-Verträge prüft zusätzlich
``workflow_vertrag_wache.py --online`` im selben PR-Gate.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, NamedTuple, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_DIRS = (".github/workflows", ".github/actions")

USES_RE = re.compile(
    r"""^(?P<prefix>\s*(?:-\s+)?uses:\s*)(?P<quote>["']?)(?P<action>[^"'@\s]+)(?:@(?P<ref>[^"'\s]+))?(?P<tail>(?P=quote)\s*(?:#.*)?)$"""
)
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
VERSION_RE = re.compile(r"v\d+\.\d+\.\d+")
COMMENT_RE = re.compile(r"^(?P<space>\s*)#(?P<comment>.*)$")


class Pin(NamedTuple):
    ref: str
    version: str


class Use(NamedTuple):
    path: str
    line: int
    action: str
    ref: Optional[str]
    version: Optional[str] = None


class Finding(NamedTuple):
    rule: str
    path: str
    line: int
    action: str
    ist: str
    soll: Optional[str]
    text: str


def is_local(action: str) -> bool:
    return action.startswith("./") or action.startswith("docker://")


def is_pin(ref: Optional[str]) -> bool:
    return bool(ref and SHA_RE.fullmatch(ref))


def repository(action: str) -> str:
    """CodeQL-Unteraktionen teilen Release, Runner und Lieferkette."""
    return "/".join(action.split("/")[:2])


def _comment_version(tail: str, quote: str) -> Optional[str]:
    body = tail[1:] if quote else tail
    match = COMMENT_RE.match(body)
    if not match:
        return None
    version = match.group("comment").strip()
    return version if VERSION_RE.fullmatch(version) else None


def parse_uses(text: str, path: str = "<memory>") -> List[Use]:
    out: List[Use] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        if raw.lstrip().startswith("#"):
            continue
        match = USES_RE.match(raw)
        if match:
            out.append(Use(
                path, number, match.group("action"), match.group("ref"),
                _comment_version(match.group("tail"), match.group("quote")),
            ))
    return out


def collect(root: Path) -> List[Use]:
    out: List[Use] = []
    for directory in WORKFLOW_DIRS:
        for path in sorted((root / directory).rglob("*.y*ml")):
            out.extend(parse_uses(path.read_text(encoding="utf-8"),
                                  path.relative_to(root).as_posix()))
    return out


def _candidates(uses: Iterable[Use]) -> Dict[str, set[Pin]]:
    candidates: Dict[str, set[Pin]] = defaultdict(set)
    for use in uses:
        if not is_local(use.action) and is_pin(use.ref) and use.version:
            candidates[repository(use.action)].add(Pin(use.ref, use.version))
    return candidates


def build_kanon(uses: Iterable[Use]) -> Dict[str, Pin]:
    """Nur ein eindeutiges Paar ist kanonisch; niemals SHA-lexikalik raten."""
    return {repo: next(iter(pins))
            for repo, pins in _candidates(uses).items() if len(pins) == 1}


def analyze(uses: List[Use]) -> Tuple[List[Finding], Dict[str, Pin]]:
    candidates = _candidates(uses)
    kanon = build_kanon(uses)
    sha_versions: Dict[str, set[str]] = defaultdict(set)
    for pins in candidates.values():
        for pin in pins:
            sha_versions[pin.ref].add(pin.version)

    findings: List[Finding] = []
    for use in uses:
        if is_local(use.action):
            continue
        repo = repository(use.action)
        target = kanon.get(repo)
        soll = f"{target.ref} # {target.version}" if target else None
        current = f"{use.ref or '(ohne Referenz)'} # {use.version or '(ohne Version)'}"
        rule = message = None
        if not is_pin(use.ref) or len(use.action.split("/")) < 2:
            rule = "A2"
            message = "fremde Action braucht owner/repo@vollständige-Commit-SHA"
        elif not use.version:
            rule = "A3"
            message = "Versionskommentar # vX.Y.Z fehlt oder ist ungültig"
        elif len(sha_versions[use.ref]) > 1:
            rule = "A3"
            message = "derselbe SHA trägt widersprüchliche Versionskommentare"
        elif len(candidates[repo]) > 1:
            rule = "A1"
            message = "SHA/Version-Drift – alle Aufrufe vollständig auf EIN Release aktualisieren"
        elif target and Pin(use.ref, use.version) != target:
            rule = "A1"
            message = "abweichender Action-Pin"
        if rule:
            findings.append(Finding(rule, use.path, use.line, use.action,
                                    current, soll, message))
    findings.sort(key=lambda finding: (finding.path, finding.line))
    return findings, kanon


def fix_text(text: str, kanon: Dict[str, Pin]) -> Tuple[str, int]:
    """Nur eindeutige Kommentardrift heilen; niemals einen SHA erfinden."""
    out: List[str] = []
    changed = 0
    for raw in text.splitlines(keepends=True):
        line = raw.rstrip("\r\n")
        ending = raw[len(line):]
        match = USES_RE.match(line)
        if not match or line.lstrip().startswith("#"):
            out.append(raw)
            continue
        action, ref = match.group("action"), match.group("ref")
        target = kanon.get(repository(action))
        if (is_local(action) or not is_pin(ref) or target is None
                or ref != target.ref
                or _comment_version(match.group("tail"), match.group("quote")) == target.version):
            out.append(raw)
            continue
        quote, tail = match.group("quote"), match.group("tail")
        body = tail[1:] if quote else tail
        comment = COMMENT_RE.match(body)
        space = comment.group("space") if comment else " "
        out.append(f"{match.group('prefix')}{quote}{action}@{ref}{quote}"
                   f"{space}# {target.version}{ending}")
        changed += 1
    return "".join(out), changed


def apply_fix(root: Path, kanon: Dict[str, Pin], dry_run: bool = False) -> List[Tuple[str, int]]:
    touched: List[Tuple[str, int]] = []
    for directory in WORKFLOW_DIRS:
        for path in sorted((root / directory).rglob("*.y*ml")):
            old = path.read_text(encoding="utf-8")
            new, count = fix_text(old, kanon)
            if count:
                touched.append((path.relative_to(root).as_posix(), count))
                if not dry_run:
                    path.write_text(new, encoding="utf-8")
    return touched


SELFTEST_CASES = [
    ("        uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97\n",
     "        uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0\n"),
    ('      - uses: "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97"  # v6.0.0\n',
     '      - uses: "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97"  # v7.0.0\n'),
    ("        uses: actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0 # v7.1.0\n", None),
    ("        uses: actions/setup-python@v7\n", None),
    ("        uses: ./.github/actions/install-hugo\n", None),
    ("#       uses: actions/checkout@v4\n", None),
]


def run_selftest() -> List[str]:
    fails: List[str] = []
    old = Pin("5fda3b95a4ea91299a34e894583c3862153e4b97", "v7.0.0")
    new = Pin("6d4fd22b20465ccc0f7354476588e8df7c9ca0e0", "v7.1.0")
    kanon = {"actions/setup-python": old}
    for source, expected in SELFTEST_CASES:
        actual, _ = fix_text(source, kanon)
        if actual != (expected if expected is not None else source):
            fails.append(f"Fix falsch: {source.strip()!r} → {actual.strip()!r}")

    partial = [Use("a.yml", 1, "actions/setup-python", old.ref, old.version),
               Use("b.yml", 2, "actions/setup-python", new.ref, new.version)]
    findings, target = analyze(partial)
    if [f.rule for f in findings] != ["A1", "A1"] or target:
        fails.append("Teil-Bump wurde nicht fail-closed erkannt")
    if fix_text(f"uses: actions/setup-python@{old.ref} # {old.version}\n", target)[1]:
        fails.append("Mehrdeutiger Bestand wurde automatisch umgeschrieben")

    same_sha = [Use("a.yml", 1, "actions/checkout", old.ref, "v7.0.0"),
                Use("b.yml", 2, "actions/checkout", old.ref, "v7.1.0")]
    if [f.rule for f in analyze(same_sha)[0]] != ["A3", "A3"]:
        fails.append("Widersprüchliche Version am selben SHA nicht erkannt")

    codeql = [Use("a.yml", 1, "github/codeql-action/init", old.ref, old.version),
              Use("a.yml", 2, "github/codeql-action/analyze", new.ref, new.version)]
    if [f.rule for f in analyze(codeql)[0]] != ["A1", "A1"]:
        fails.append("CodeQL-Unteraktionen wurden nicht zusammen geprüft")

    for ref in ("v7", "main", "master", "latest", "HEAD", None, old.ref.upper(), old.ref[:39]):
        if [f.rule for f in analyze([Use("a.yml", 1, "actions/setup-python", ref, "v7.0.0")])[0]] != ["A2"]:
            fails.append(f"Ungepinnte Referenz nicht erkannt: {ref}")
    if [f.rule for f in analyze([Use("a.yml", 1, "actions/setup-python", old.ref, None)])[0]] != ["A3"]:
        fails.append("Fehlender Versionskommentar nicht erkannt")
    if analyze([Use("a.yml", 1, "./.github/actions/hugo-build", None)])[0]:
        fails.append("Lokale Action fälschlich beanstandet")

    once, _ = fix_text(SELFTEST_CASES[0][0], kanon)
    twice, count = fix_text(once, kanon)
    if twice != once or count:
        fails.append("Fix ist nicht idempotent")
    return fails


def report(findings: List[Finding], kanon: Dict[str, Pin]) -> str:
    lines = ["🔧 ACTIONS-PIN-WACHE", "", "Eindeutige Pins je Anbieter-Repository:"]
    lines.extend(f"  · {repo}@{pin.ref} # {pin.version}"
                 for repo, pin in sorted(kanon.items()))
    lines.append("")
    if not findings:
        lines.append("✅ Keine Drift – SHA und Version sind im gesamten Bestand einheitlich.")
    else:
        lines.append(f"❌ {len(findings)} Befund(e):")
        lines.extend(f"  [{f.rule}] {f.path}:{f.line} {f.action}@{f.ist} → "
                     f"{f.soll or 'kein eindeutiger Kandidat'} ({f.text})" for f in findings)
        lines.extend(["", "Heilung: Dependabot-Update vollständig übernehmen. --fix ergänzt nur",
                      "Versionskommentare zu einem eindeutigen SHA; es wählt kein Release."])
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Ein SHA und eine Version je GitHub-Action.")
    parser.add_argument("--fix", action="store_true", help="eindeutige Versionskommentare ergänzen")
    parser.add_argument("--dry-run", action="store_true", help="Kommentar-Fix nur simulieren")
    parser.add_argument("--gate", action="store_true", help="Exit 1 bei Befund (CI)")
    parser.add_argument("--json", action="store_true", help="maschinenlesbarer Bericht")
    parser.add_argument("--selftest", action="store_true", help="Sabotage-Schutz")
    parser.add_argument("--root", default=str(ROOT), help="Repo-Wurzel")
    args = parser.parse_args(argv)

    if args.selftest:
        fails = run_selftest()
        for failure in fails:
            print(f"❌ {failure}")
        if fails:
            return 2
        print(f"✅ Selbsttest bestanden ({len(SELFTEST_CASES)} Fix-Fälle, Teil-Bump, "
              "Unteraktionen, SHA/Version, A2/A3, lokale Actions, Idempotenz).")
        return 0

    root = Path(args.root).resolve()
    uses = collect(root)
    if not uses:
        print("::error::Keine Actions gefunden – Prüfling fehlt, nicht grün melden.", file=sys.stderr)
        return 1
    findings, kanon = analyze(uses)
    if args.fix or args.dry_run:
        touched = apply_fix(root, kanon, dry_run=args.dry_run)
        total = sum(count for _, count in touched)
        print(f"🔧 {total} Versionskommentar(e) in {len(touched)} Datei(en) "
              f"{'würden geändert' if args.dry_run else 'geändert'}.")
        if not args.dry_run:
            findings, kanon = analyze(collect(root))

    if args.json:
        print(json.dumps({"kanon": {repo: pin._asdict() for repo, pin in kanon.items()},
                          "fundstellen": [f._asdict() for f in findings],
                          "drift": len(findings)}, ensure_ascii=False, indent=2))
    else:
        print(report(findings, kanon))
    if findings and (args.gate or args.fix):
        print("::error::Actions-Pin-Drift – Update vollständig übernehmen; keine SHA erraten.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
