#!/usr/bin/env python3
"""Close the loop for machine-healable watchdog findings.

The watchdog is a detector, not a dead-end ticket generator. A reserve
shortage must start the reserve production line immediately; waiting for the
next scheduled run leaves an open issue and makes the automation depend on a
human. This small broker keeps that hand-off explicit, idempotent and
fail-safe: an already running reserve workflow is never duplicated.

A dispatch is asynchronous. Therefore a *successfully proven* reserve repair
must also remeasure the complete watchdog picture and route it immediately.
Otherwise a resolved generic alarm survives until tomorrow's watchdog run and
looks like an unfinished incident. The reconciliation deliberately uses the
existing ``bot_watchdog.py`` and ``alert_router.py`` SSOTs; it never closes an
issue merely because one producer believes it is healthy. Other machine-owned
findings keep the ticket open or update it.

The same applies to the live site. "Newest article not live" (issue #676)
was reported as machine-healable, yet nothing healed it: the watchdog wrote
the ticket and the next scheduled run measured the same 404 again. Since the
repair for #676 the broker also closes that loop -- but only when a dispatch
can actually help. If the deploy chain itself is blocked (a step aborted the
``deploy`` job before the Pages artifact was uploaded), re-triggering the
catch-up would fail identically; the honest answer is then the name of the
blocking step, not another red run.

Usage (GitHub Actions):
    python3 scripts/watchdog_recovery.py --reserve
    python3 scripts/watchdog_recovery.py --live-site
    python3 scripts/watchdog_recovery.py --reconcile
    python3 scripts/watchdog_recovery.py --selftest

Exit codes: 0 = geheilt/nicht nötig · 2 = Umgebung fehlt (gh/Token) ·
3 = nicht durch Dispatch heilbar (Auslieferung blockiert).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

WORKFLOW = "content-reserve.yml"
DEPLOY_CATCHUP_WORKFLOW = "deploy-catchup.yml"
DEPLOY_WORKFLOW = "deploy.yml"
REF = "main"
# Der Reserve-Workflow unterscheidet seinen regulären Nachtlauf bewusst von
# einer vom Watchdog ausgelösten Reparatur. Nur letztere führt nach dem harten
# Gate sofort den vollständigen Alarm-Abgleich aus; damit erzeugt ein normaler
# Vorratslauf keine vorgezogene, möglicherweise noch transiente Lagebewertung.
RECOVERY_INPUT = "watchdog_recovery"
ROOT = Path(__file__).resolve().parent.parent
WATCHDOG = ROOT / "scripts" / "bot_watchdog.py"


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
    result = _run([
        "gh", "workflow", "run", WORKFLOW, "--ref", REF,
        "--field", f"{RECOVERY_INPUT}=true",
    ])
    if result.returncode:
        print(f"::warning::Content-Reserve konnte nicht gestartet werden: "
              f"{result.stderr.strip() or result.stdout.strip()}")
        return result.returncode
    print("🚑 Content-Reserve wegen niedrigem Bestand gestartet (workflow_dispatch).")
    return 0


def deploy_in_flight() -> bool:
    """Return whether a deploy or catch-up run is already active.

    Both workflows share the ``pages-deploy`` concurrency group, so a second
    dispatch would only be queued (or displace a waiting run, issue #218).
    """
    active = {"queued", "in_progress", "waiting", "requested"}
    for workflow in (DEPLOY_WORKFLOW, DEPLOY_CATCHUP_WORKFLOW):
        result = _run([
            "gh", "run", "list", "--workflow", workflow, "--branch", REF,
            "--limit", "10", "--json", "status",
        ])
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f"gh run list {workflow} fehlgeschlagen")
        try:
            runs = json.loads(result.stdout or "[]")
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"gh run list {workflow} lieferte ungültiges JSON: {exc}") from exc
        for row in runs:
            if isinstance(row, dict) and str(row.get("status", "")).lower() in active:
                return True
    return False


def deploy_chain_blocked() -> tuple[bool, str]:
    """Ask the watchdog SSOT whether the deploy chain is blocked.

    Returns ``(blocked, evidence)``. Anything the watchdog cannot decide
    (offline, no completed run) is reported as *not* blocked: a recovery
    dispatch is cheap and idempotent, while a wrong "blocked" verdict would
    silently skip the only repair path.
    """
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import bot_watchdog
    except Exception as exc:  # pragma: no cover - defensiv
        print(f"::warning::Watchdog-Klassifikation nicht verfügbar ({exc}); "
              f"Catchup wird ausgelöst")
        return False, "Klassifikation nicht verfügbar"
    try:
        lage, schritt, beleg = bot_watchdog.deploy_blockade()
    except Exception as exc:  # pragma: no cover - defensiv
        print(f"::warning::Deploy-Kette nicht messbar ({exc}); Catchup wird ausgelöst")
        return False, f"nicht messbar: {exc}"
    if lage == "blockiert":
        return True, f"Schritt „{schritt}“ – {beleg}"
    return False, beleg


def trigger_deploy_catchup() -> int:
    """Heal a missing live article by dispatching the deploy catch-up.

    Order matters (lesson from #661): first check whether a dispatch can heal
    at all, then avoid duplicate runs, then dispatch.
    """
    if not os.environ.get("GH_TOKEN") and not os.environ.get("GITHUB_TOKEN"):
        print("::warning::Keine GitHub-Authentifizierung – Deploy-Catchup nicht ausgelöst")
        return 2
    if shutil.which("gh") is None:
        print("::warning::gh CLI fehlt – Deploy-Catchup nicht ausgelöst")
        return 2

    blocked, evidence = deploy_chain_blocked()
    if blocked:
        # Ein erneuter Dispatch würde exakt denselben Schritt treffen.
        print(f"::error::Auslieferung blockiert: {evidence}")
        print("🛑 Deploy-Catchup NICHT ausgelöst – er würde am selben Schritt "
              "scheitern. Der blockierende Schritt in deploy.yml muss zuerst "
              "weg (Dauerheilung #676: erst liefern, dann siegeln).")
        return 3

    try:
        if deploy_in_flight():
            print("✅ Deploy oder Catchup läuft bereits; kein Doppel-Dispatch.")
            return 0
    except RuntimeError as exc:
        print(f"::warning::{exc}; starte einmalig neu")

    result = _run(["gh", "workflow", "run", DEPLOY_CATCHUP_WORKFLOW, "--ref", REF])
    if result.returncode:
        print(f"::warning::Deploy-Catchup konnte nicht gestartet werden: "
              f"{result.stderr.strip() or result.stdout.strip()}")
        return result.returncode
    print("🚑 Deploy-Catchup ausgelöst – der fehlende Artikel wird nachgeliefert "
          "(Nachmessung im selben Watchdog-Lauf).")
    return 0


def reconcile_after_reserve() -> int:
    """Re-measure and route after a *successful* reserve end gate.

    A recovery dispatch cannot know whether the child workflow later produced
    enough hash-verified candidates. This function is therefore called only
    after ``reserve_gate.py`` succeeded. It still measures the *entire*
    watchdog state before the router decides whether the generic ticket may be
    closed: a green reserve must never hide a simultaneous deployment,
    cadence, syntax or affiliate problem.

    The function deliberately returns a non-zero code on a routing failure so
    callers can expose the missing acknowledgement. The workflow treats that
    acknowledgement as best effort: the proven reserve repair remains valid
    and the scheduled watchdog will retry the routing path.
    """
    if not os.environ.get("GH_TOKEN") and not os.environ.get("GITHUB_TOKEN"):
        print("::warning::Keine GitHub-Authentifizierung – Watchdog-Abgleich nicht möglich")
        return 2
    if not os.environ.get("GITHUB_REPOSITORY"):
        print("::warning::GITHUB_REPOSITORY fehlt – Watchdog-Abgleich nicht möglich")
        return 2
    if shutil.which("gh") is None:
        print("::warning::gh CLI fehlt – Watchdog-Abgleich nicht möglich")
        return 2
    if not WATCHDOG.is_file():
        print(f"::warning::Watchdog-Skript fehlt: {WATCHDOG}")
        return 2

    measure = _run([sys.executable, str(WATCHDOG), "--emit-env"])
    if measure.returncode:
        print("::warning::Watchdog-Nachmessung fehlgeschlagen: "
              f"{measure.stderr.strip() or measure.stdout.strip()}")
        return measure.returncode

    route = _run([sys.executable, str(WATCHDOG), "--route"])
    if route.returncode:
        print("::warning::Watchdog-Alarmrouting fehlgeschlagen: "
              f"{route.stderr.strip() or route.stdout.strip()}")
        return route.returncode

    print("✅ Watchdog nach erfolgreicher Reserve-Reparatur vollständig nachgemessen und geroutet.")
    return 0


def selftest() -> int:
    """Static contract test usable before the broker is deployed."""
    errors = []
    if not WORKFLOW.endswith(".yml"):
        errors.append("workflow muss YAML sein")
    if not DEPLOY_CATCHUP_WORKFLOW.endswith(".yml"):
        errors.append("deploy-catchup muss YAML sein")
    if DEPLOY_WORKFLOW != "deploy.yml":
        errors.append("Deploy-Kette muss über deploy.yml gemessen werden")
    if not (ROOT / ".github" / "workflows" / DEPLOY_CATCHUP_WORKFLOW).is_file():
        errors.append("deploy-catchup.yml fehlt – der Selbstheilungsweg wäre tot")
    if not callable(globals().get("deploy_chain_blocked")):
        errors.append("Blockade-Prüfung fehlt")
    if REF != "main":
        errors.append("Reparatur darf nur main bearbeiten")
    if RECOVERY_INPUT != "watchdog_recovery":
        errors.append("Recovery-Dispatch braucht den erwarteten Workflow-Input")
    if WATCHDOG.name != "bot_watchdog.py" or not WATCHDOG.is_file():
        errors.append("Nachmessung braucht scripts/bot_watchdog.py als SSOT")
    if errors:
        for error in errors:
            print(f"🛑 {error}")
        return 1
    print("✅ watchdog_recovery Selbsttest: Reserve-Dispatch und Nachmessung fail-safe.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reserve", action="store_true")
    parser.add_argument("--live-site", action="store_true")
    parser.add_argument("--reconcile", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    if args.reserve:
        return trigger_reserve()
    if args.live_site:
        return trigger_deploy_catchup()
    if args.reconcile:
        return reconcile_after_reserve()
    parser.error("--reserve, --live-site, --reconcile oder --selftest erforderlich")
    return 2


if __name__ == "__main__":
    sys.exit(main())
