#!/usr/bin/env python3
"""Read-only quality audit for the GitHub Actions control plane.

The blog has many deliberately separate workflows. This audit does not merge
jobs or change schedules; it makes the operational contracts measurable so a
new workflow cannot quietly bypass the basics of a production pipeline.

Usage:
  python3 scripts/automation_premium_audit.py
  python3 scripts/automation_premium_audit.py --json
  python3 scripts/automation_premium_audit.py --strict
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - CI installs PyYAML
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
SHA = re.compile(r"@[0-9a-f]{40}$", re.IGNORECASE)
USES = re.compile(r"^\s*uses:\s*([^\s#]+)", re.MULTILINE)


def load(path: Path) -> dict:
    if yaml is None:
        raise RuntimeError("PyYAML fehlt: python3 -m pip install pyyaml")
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return value if isinstance(value, dict) else {}


def has_schedule(data: dict) -> bool:
    trigger = data.get("on", data.get(True, {}))
    return isinstance(trigger, dict) and "schedule" in trigger


def audit_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    # PyYAML is optional: the fallback intentionally extracts only the
    # top-level contracts this audit owns, so the command remains useful on a
    # clean runner before dependencies have been installed.
    if yaml is None:
        name_match = re.search(r"^name:\s*(.+?)\s*$", text, re.MULTILINE)
        name = name_match.group(1).strip().strip('"').strip("'") if name_match else path.stem
        jobs_match = re.search(r"^jobs:\s*$([\s\S]*)", text, re.MULTILINE)
        job_names = re.findall(r"^  ([A-Za-z0-9_-]+):\s*$", jobs_match.group(1), re.MULTILINE) if jobs_match else []
        missing_timeout = [job for job in job_names if not re.search(
            rf"^  {re.escape(job)}:[\s\S]*?(?=^  [A-Za-z0-9_-]+:|\Z)", text, re.MULTILINE
        ) or not re.search(
            rf"^  {re.escape(job)}:[\s\S]*?^    timeout-minutes:", text, re.MULTILINE)]
        data = {"name": name, "jobs": job_names,
                "on": {"schedule": True} if re.search(r"^\s+schedule:", text, re.MULTILINE) else {}}
        # Schlüssel nur bei einem echten Top-Level-Vertrag setzen. Zuvor wurde
        # auch bei Abwesenheit `permissions: None` eingetragen; die spätere
        # Schlüsselprüfung meldete dadurch ausgerechnet fehlende Permissions
        # fälschlich als vorhanden.
        if re.search(r"^permissions:\s*(?:#.*)?$", text, re.MULTILINE):
            data["permissions"] = {}
        if re.search(r"^concurrency:\s*(?:#.*)?$", text, re.MULTILINE):
            data["concurrency"] = {}
    else:
        data = load(path)
        jobs = data.get("jobs") if isinstance(data.get("jobs"), dict) else {}
        missing_timeout = [name for name, job in jobs.items()
                           if isinstance(job, dict) and "timeout-minutes" not in job]
    jobs = data.get("jobs") if isinstance(data.get("jobs"), (dict, list)) else {}
    refs = [ref for ref in USES.findall(text) if not ref.startswith("./")]
    floating = [ref for ref in refs if not SHA.search(ref)]
    continue_count = text.count("continue-on-error:")
    return {
        "file": str(path.relative_to(ROOT)),
        "name": data.get("name", path.stem),
        "scheduled": has_schedule(data),
        "jobs": len(jobs),
        # Nur die granulare Mapping-Form ist ein belastbarer Least-Privilege-
        # Vertrag. `permissions: null`, `read-all` und `write-all` zählen nicht.
        "has_permissions": isinstance(data.get("permissions"), dict),
        "has_concurrency": "concurrency" in data,
        "missing_timeout_jobs": missing_timeout,
        "floating_action_refs": floating,
        "continue_on_error_count": continue_count,
    }


def build_report(rows: list[dict]) -> dict:
    names: dict[str, list[str]] = {}
    for row in rows:
        names.setdefault(str(row["name"]), []).append(row["file"])
    duplicates = {name: files for name, files in names.items() if len(files) > 1}
    scheduled = [r for r in rows if r["scheduled"]]
    return {
        "workflow_count": len(rows),
        "scheduled_count": len(scheduled),
        "missing_permissions": [r["file"] for r in rows if not r["has_permissions"]],
        "missing_concurrency": [r["file"] for r in rows if not r["has_concurrency"]],
        "missing_timeout": {r["file"]: r["missing_timeout_jobs"] for r in rows
                            if r["missing_timeout_jobs"]},
        "floating_actions": {r["file"]: r["floating_action_refs"] for r in rows
                             if r["floating_action_refs"]},
        "duplicate_names": duplicates,
        "continue_on_error_total": sum(r["continue_on_error_count"] for r in rows),
        "workflows": rows,
    }


def print_text(report: dict) -> None:
    print("AUTOMATION PREMIUM AUDIT – read-only")
    print(f"Workflows: {report['workflow_count']}  |  geplant: {report['scheduled_count']}")
    print(f"Action-Refs ohne Commit-SHA: {sum(map(len, report['floating_actions'].values()))}")
    print(f"Jobs ohne Timeout: {sum(map(len, report['missing_timeout'].values()))}")
    print(f"Ohne explizite Permissions: {len(report['missing_permissions'])}")
    print(f"Ohne Concurrency-Vertrag: {len(report['missing_concurrency'])}")
    print(f"continue-on-error-Vorkommen: {report['continue_on_error_total']}")
    if report["duplicate_names"]:
        print("DUPLIKATE WORKFLOW-NAMEN:")
        for name, files in report["duplicate_names"].items():
            print(f"  - {name}: {', '.join(files)}")
    print("\nNächste Premium-Priorität:")
    print("  1. kritische Drittanbieter-Actions auf Commit-SHAs pinnen")
    print("  2. fehlende Timeouts und explizite Least-Privilege-Permissions schließen")
    print("  3. continue-on-error nur mit sichtbarem Issue-/Summary-Fallback erlauben")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="maschinenlesbarer Bericht")
    parser.add_argument("--strict", action="store_true",
                        help="nicht erfolgreich bei doppelten Namen, fehlenden Timeouts "
                             "oder fehlenden/ungültigen Permissions")
    args = parser.parse_args(argv)
    rows = [audit_file(path) for path in sorted(WORKFLOWS.glob("*.yml"))]
    report = build_report(rows)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_text(report)
    if args.strict and (report["duplicate_names"] or report["missing_timeout"]
                        or report["missing_permissions"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
