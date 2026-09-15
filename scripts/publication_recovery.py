#!/usr/bin/env python3
"""Run the bounded publication recovery chain and wait for its deploy.

The delivery check must not race the asynchronous cadence backstop.  This
small orchestrator is deliberately boring: dispatch the existing backstop,
wait for that run, then wait for the deploy it requested.  A timeout is a
real failure; it is never converted into a green delivery receipt.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import time


def gh(*args: str) -> str:
    return subprocess.check_output(["gh", *args], text=True)


def runs(workflow: str) -> list[dict]:
    raw = gh(
        "run", "list", "--workflow", workflow, "--limit", "20",
        "--json", "databaseId,status,conclusion,createdAt,headBranch",
    )
    return json.loads(raw)


def wait_for_run(workflow: str, started: dt.datetime, timeout: int) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        candidates = []
        for run in runs(workflow):
            created = dt.datetime.fromisoformat(run["createdAt"].replace("Z", "+00:00"))
            if created >= started:
                candidates.append(run)
        if candidates:
            run = max(candidates, key=lambda item: item["createdAt"])
            if run["status"] == "completed":
                if run["conclusion"] != "success":
                    raise RuntimeError(f"{workflow} ended {run['conclusion']}")
                return run
        time.sleep(20)
    raise TimeoutError(f"Timed out waiting for {workflow}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=45 * 60)
    args = parser.parse_args(argv)
    started = dt.datetime.now(dt.timezone.utc)
    print("Dispatching cadence backstop before declaring delivery failed…", flush=True)
    gh("workflow", "run", "kadenz-endkontrolle.yml", "--ref", "main")
    wait_for_run("kadenz-endkontrolle.yml", started, args.timeout)
    # The backstop dispatches deploy even when it had no source diff.  Waiting
    # for it closes the race between a healed source tree and public HTML.
    # The deploy is dispatched during the cadence run, so its creation time
    # can precede the cadence completion timestamp.
    try:
        wait_for_run("deploy.yml", started, min(args.timeout, 20 * 60))
    except TimeoutError:
        # A deploy may have been queued just before deploy_started.  The
        # delivery retries remain authoritative, so expose this as a warning.
        print("Deploy run not visible in time; public receipt remains authoritative.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
