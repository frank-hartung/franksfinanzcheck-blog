#!/usr/bin/env python3
"""Read-only quality audit for the GitHub Actions control plane.

The blog has many deliberately separate workflows. This audit does not merge
jobs or change schedules; it makes the operational contracts measurable so a
new workflow cannot quietly bypass the basics of a production pipeline.

Usage:
  python3 scripts/automation_premium_audit.py
  python3 scripts/automation_premium_audit.py --json
  python3 scripts/automation_premium_audit.py --strict

Strict mode requires explicit least-privilege permissions, job timeouts, and a
well-formed concurrency contract (workflow-level or job-level), with no
duplicate workflow names. Best-effort step semantics are measured separately;
they are not made blocking without their event-specific recovery contract.
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


def valid_concurrency(value: object) -> bool:
    """A concurrency contract must name its group and cancellation policy."""
    if not isinstance(value, dict):
        return False
    group = value.get("group")
    cancellation = value.get("cancel-in-progress")
    cancel_is_boolean_or_expression = (
        isinstance(cancellation, bool)
        or isinstance(cancellation, str)
        and re.fullmatch(r"\$\{\{\s*.+?\s*\}\}", cancellation.strip()) is not None
    )
    return isinstance(group, str) and bool(group.strip()) and cancel_is_boolean_or_expression


def workflow_has_concurrency(data: dict) -> bool:
    if data.get("_fallback_has_concurrency") is True:
        return True
    if valid_concurrency(data.get("concurrency")):
        return True
    jobs = data.get("jobs") if isinstance(data.get("jobs"), dict) else {}
    return any(isinstance(job, dict) and valid_concurrency(job.get("concurrency"))
               for job in jobs.values())


def fallback_has_concurrency(text: str) -> bool:
    """Dependency-free, indentation-aware extraction of workflow/job blocks."""
    matches = list(re.finditer(r"^(?P<indent> *)concurrency:\s*(?:#.*)?$", text,
                               re.MULTILINE))
    lines = text.splitlines(keepends=True)
    offsets = []
    total = 0
    for line in lines:
        offsets.append(total)
        total += len(line)
    for match in matches:
        start_line = text.count("\n", 0, match.start())
        indent = len(match.group("indent"))
        start = offsets[start_line]
        end = len(text)
        for line_no in range(start_line + 1, len(lines)):
            line = lines[line_no]
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            current_indent = len(line) - len(line.lstrip(" "))
            if current_indent <= indent:
                end = offsets[line_no]
                break
        block = text[start:end]
        if (re.search(r"^\s+group:\s*\S", block, re.MULTILINE)
                and re.search(r"^\s+cancel-in-progress:\s*(?:true|false|\$\{\{.+\}\})",
                              block, re.MULTILINE)):
            return True
    return False


FALLBACK_MARKERS = re.compile(
    r"GITHUB_STEP_SUMMARY|::(?:warning|error|notice)::|"
    r"issues\.(?:create|update|comment|close)|gh issue|upload-artifact|"
    r"--report(?:\s|=)|report\.(?:json|md|txt)|\btee\s+",
    re.IGNORECASE,
)


def continue_on_error_evidence(data: dict, text: str) -> list[dict]:
    """Inventory observable recovery/reporting signals for each YAML step.

    This is a structural safeguard, not a proof that the fallback's business
    meaning is correct. The audit retains the signal and requires at least one
    explicit result/output consumer, in-step diagnostic, or downstream report marker.
    """
    jobs = data.get("jobs") if isinstance(data.get("jobs"), dict) else None
    if jobs is None:
        # The dependency-free fallback cannot prove step/job boundaries. Keep
        # the counted keys visible, but fail strict mode rather than claiming
        # an empty inventory is fully classified.
        count = len(re.findall(r"^\s+continue-on-error:\s*[^#\n]+", text, re.MULTILINE))
        return [{"job": "unknown", "step": f"unparsed-step-{index + 1}",
                 "signal": "unclassified"} for index in range(count)]
    evidence = []
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps") if isinstance(job.get("steps"), list) else []
        for index, step in enumerate(steps):
            if not isinstance(step, dict) or "continue-on-error" not in step:
                continue
            step_id = step.get("id")
            following = "\n".join(str(item) for item in steps[index + 1:]
                                    if isinstance(item, dict))
            if (step_id and re.search(
                    rf"steps\.{re.escape(str(step_id))}\.(?:outcome|conclusion|outputs\.[A-Za-z0-9_-]+)",
                    text)):
                signal = "step-result-consumer"
            elif FALLBACK_MARKERS.search(str(step)):
                signal = "in-step-diagnostic"
            elif FALLBACK_MARKERS.search(following):
                signal = "downstream-report-marker"
            else:
                signal = "unclassified"
            evidence.append({
                "job": str(job_name),
                "step": str(step.get("name", step_id or f"step-{index + 1}")),
                "signal": signal,
            })
    return evidence


def count_continue_on_error(data: dict, text: str) -> int:
    jobs = data.get("jobs") if isinstance(data.get("jobs"), dict) else None
    if jobs is not None:
        total = 0
        for job in jobs.values():
            if not isinstance(job, dict):
                continue
            total += int("continue-on-error" in job)
            total += sum(1 for step in job.get("steps", [])
                         if isinstance(step, dict) and "continue-on-error" in step)
        return total
    # Only actual YAML keys, not comments or prose mentions.
    return len(re.findall(r"^\s+continue-on-error:\s*[^#\n]+", text, re.MULTILINE))


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
        data["_fallback_has_concurrency"] = fallback_has_concurrency(text)
    else:
        data = load(path)
        jobs = data.get("jobs") if isinstance(data.get("jobs"), dict) else {}
        missing_timeout = [name for name, job in jobs.items()
                           if isinstance(job, dict) and "timeout-minutes" not in job]
    jobs = data.get("jobs") if isinstance(data.get("jobs"), (dict, list)) else {}
    refs = [ref for ref in USES.findall(text) if not ref.startswith("./")]
    floating = [ref for ref in refs if not SHA.search(ref)]
    continue_count = count_continue_on_error(data, text)
    fallback_evidence = continue_on_error_evidence(data, text)
    return {
        "file": str(path.relative_to(ROOT)),
        "name": data.get("name", path.stem),
        "scheduled": has_schedule(data),
        "jobs": len(jobs),
        # Nur die granulare Mapping-Form ist ein belastbarer Least-Privilege-
        # Vertrag. `permissions: null`, `read-all` und `write-all` zählen nicht.
        "has_permissions": isinstance(data.get("permissions"), dict),
        "has_concurrency": workflow_has_concurrency(data),
        "missing_timeout_jobs": missing_timeout,
        "floating_action_refs": floating,
        "continue_on_error_count": continue_count,
        "continue_on_error_source_mentions": len(re.findall(r"continue-on-error:", text)),
        "continue_on_error_fallback_evidence": fallback_evidence,
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
        "continue_on_error_source_mentions": sum(
            r.get("continue_on_error_source_mentions", r["continue_on_error_count"])
            for r in rows),
        "continue_on_error_unclassified": [
            {"file": r["file"], **item}
            for r in rows for item in r.get("continue_on_error_fallback_evidence", [])
            if item["signal"] == "unclassified"],
        "continue_on_error_fallback_signal_counts": {
            signal: sum(item["signal"] == signal
                        for r in rows for item in r.get("continue_on_error_fallback_evidence", []))
            for signal in ("step-result-consumer", "in-step-diagnostic",
                           "downstream-report-marker", "unclassified")
        },
        "workflows": rows,
    }


def print_text(report: dict) -> None:
    print("AUTOMATION PREMIUM AUDIT – read-only")
    print(f"Workflows: {report['workflow_count']}  |  geplant: {report['scheduled_count']}")
    print(f"Action-Refs ohne Commit-SHA: {sum(map(len, report['floating_actions'].values()))}")
    print(f"Jobs ohne Timeout: {sum(map(len, report['missing_timeout'].values()))}")
    print(f"Ohne explizite Permissions: {len(report['missing_permissions'])}")
    print(f"Ohne Concurrency-Vertrag: {len(report['missing_concurrency'])}")
    print(f"continue-on-error-Schritte (geparst): {report['continue_on_error_total']}"
          f"  | Texttreffer inkl. Kommentare: {report['continue_on_error_source_mentions']}")
    print("Fallback-Signale (strukturell, keine semantische Erfolgsgarantie): "
          + ", ".join(f"{key}={value}" for key, value in
                       report["continue_on_error_fallback_signal_counts"].items()))
    print(f"Ohne sichtbares Fallback-Signal: {len(report['continue_on_error_unclassified'])}")
    if report["duplicate_names"]:
        print("DUPLIKATE WORKFLOW-NAMEN:")
        for name, files in report["duplicate_names"].items():
            print(f"  - {name}: {', '.join(files)}")
    print("\nNächste Premium-Priorität:")
    if report["floating_actions"]:
        print("  1. ungepinnte Drittanbieter-Actions auf Commit-SHAs pinnen")
    else:
        print("  1. ✅ Drittanbieter-Actions sind auf Commit-SHAs gepinnt")
    if report["missing_timeout"] or report["missing_permissions"]:
        print("  2. fehlende Timeouts und explizite Least-Privilege-Permissions schließen")
    else:
        print("  2. ✅ alle Jobs haben Timeouts und alle Workflows explizite Permissions")
    if report["missing_concurrency"]:
        print("  3. Concurrency-Lücken der %d betroffenen Workflows prüfen; "
              "Event-Verluste durch pauschales Serialisieren vermeiden" %
              len(report["missing_concurrency"]))
    else:
        print("  3. ✅ alle Workflows haben einen Concurrency-Vertrag")
    if report["continue_on_error_unclassified"]:
        print("  4. %d continue-on-error-Schritte ohne erkennbares Fallback-Signal nachprüfen" %
              len(report["continue_on_error_unclassified"]))
    else:
        print("  4. ✅ alle %d continue-on-error-Schritte haben ein klassifiziertes Fallback-Signal"
              % report["continue_on_error_total"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="maschinenlesbarer Bericht")
    parser.add_argument("--strict", action="store_true",
                        help="nicht erfolgreich bei doppelten Namen, fehlenden Timeouts/Permissions "
                             "fehlenden/ungültigen Concurrency-Verträgen oder unklassifizierten "
                             "continue-on-error-Schritten")
    args = parser.parse_args(argv)
    rows = [audit_file(path) for path in sorted(WORKFLOWS.glob("*.yml"))]
    report = build_report(rows)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_text(report)
    if args.strict and (report["duplicate_names"] or report["missing_timeout"]
                        or report["missing_permissions"] or report["missing_concurrency"]
                        or report["continue_on_error_unclassified"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
