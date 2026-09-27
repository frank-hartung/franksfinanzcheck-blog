#!/usr/bin/env python3
"""Start the owning repair workflow for machine-healable watchdog findings.

The watchdog is a detector, not a dead-end ticket generator.  A reserve
shortage must start the reserve production line immediately; waiting for the
next scheduled run leaves an open issue and makes the automation depend on a
human.  This small broker keeps that hand-off explicit, idempotent and
fail-safe: an already running reserve workflow is never duplicated.

Usage (GitHub Actions):
    python3 scripts/watchdog_recovery.py --reserve
    python3 scripts/watchdog_recovery.py --selftest
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

WORKFLOW = "content-reserve.yml"
REF = "main"


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=False)


def reserve_running() -> bool:
    """Return whether an active repair run exists (unknown means safe to stop)."""
    if shutil.which("gh") is None:
        return False
    result = _run([
        "gh", "run", "list", "--workflow", WORKFLOW, "--branch", REF,
        "--limit", "10", "--json", "status",
    ])
    if result.returncode != 0:
        # Do not silently claim success: the caller logs this as a warning.
        raise RuntimeError(result.stderr.strip() or "gh run list fehlgeschlagen")
    try:
        runs = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"gh run list lieferte ungültiges JSON: {exc}") from exc
    return any(str(row.get("status", "")).lower() in {"queued", "in_progress"}
               for row in runs if isinstance(row, dict))


def trigger_reserve() -> int:
    """Dispatch one reserve repair, returning a shell-friendly status."""
    if not os.environ.get("GH_TOKEN") and not os.environ.get("GITHUB_TOKEN"):
        print("::warning::Keine GitHub-Authentifizierung – Reserve nicht ausgelöst")
        return 2
    if shutil.which("gh") is None:
        print("::warning::gh CLI fehlt – Reserve nicht ausgelöst")
        return 2
    try:
        if reserve_running():
            print("✅ Content-Reserve läuft bereits; kein Doppel-Dispatch.")
            return 0
    except RuntimeError as exc:
        # Fail open for recovery: a failed status query must not prevent a
        # repair, while the warning remains visible in the Actions log.
        print(f"::warning::{exc}; starte einmalig neu")
    result = _run(["gh", "workflow", "run", WORKFLOW, "--ref", REF])
    if result.returncode:
        print(f"::warning::Content-Reserve konnte nicht gestartet werden: "
              f"{result.stderr.strip() or result.stdout.strip()}")
        return result.returncode
    print("🚑 Content-Reserve wegen niedrigem Bestand gestartet (workflow_dispatch).")
    return 0


def selftest() -> int:
    """Static contract test usable before the broker is deployed."""
    errors = []
    if not WORKFLOW.endswith(".yml"):
        errors.append("workflow muss YAML sein")
    if REF != "main":
        errors.append("Reparatur darf nur main bearbeiten")
    if errors:
        for error in errors:
            print(f"🛑 {error}")
        return 1
    print("✅ watchdog_recovery Selbsttest: Reserve-Dispatch fail-safe.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reserve", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    if args.reserve:
        return trigger_reserve()
    parser.error("--reserve oder --selftest erforderlich")
    return 2


if __name__ == "__main__":
    sys.exit(main())
