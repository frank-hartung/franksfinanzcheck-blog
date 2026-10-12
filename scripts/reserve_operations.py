#!/usr/bin/env python3
"""Operational safety for the daily reserve, not a second editorial gate.

A real tool preflight precedes content work. All writers share an absolute
work deadline; the job retains time for evidence, Git sync and the end gate.
Healer timeouts stop the complete process group before isolation is restored.
No model, network or production state is used by the selftest.
"""
from __future__ import annotations

import argparse
import contextlib
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
DEADLINE_ENV = "RESERVE_WORK_DEADLINE"


def work_seconds(cap: float, *, env=None, now=None) -> float:
    """Remaining shared work budget, bounded by the caller's own limit.

    No deadline outside CI means only the local limit. A configured but
    malformed deadline means STOP, not unlimited content work. Wall time is
    shared across workflow processes; each child also gets a monotonic timeout.
    """
    env = os.environ if env is None else env
    now = time.time() if now is None else now
    if not math.isfinite(cap) or cap < 0:
        raise ValueError("Arbeitsbudget muss endlich und nicht negativ sein")
    raw = env.get(DEADLINE_ENV)
    if raw is None:
        return cap
    try:
        deadline = float(raw)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(deadline):
        return 0.0
    return min(cap, max(0.0, deadline - now))


class WorkInterrupted(BaseException):
    """Exit via finally, not a swallowed candidate/healer failure."""


@contextlib.contextmanager
def restore_on_termination():
    """Allow temporary publication bytes and isolation snapshots to restore.

    Nested uses are safe: restore the previous handler on exit. SIGKILL is
    still the runner's last resort, never our ordinary timeout mechanism.
    """
    previous = signal.getsignal(signal.SIGTERM)

    def interrupt(_signum, _frame):
        raise WorkInterrupted("Reserve-Arbeit durch SIGTERM unterbrochen")

    signal.signal(signal.SIGTERM, interrupt)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)


def stop_group(proc: subprocess.Popen) -> None:
    """Reap the parent AND terminate surviving descendants, even after exit."""
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=5)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        pass
    finally:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()


def run_healer(cmd, *, cwd=ROOT, env=None, timeout=900):
    """Captured output with a bounded, fully reaped process group."""
    proc = subprocess.Popen(cmd, cwd=cwd, env=env, start_new_session=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True)
    try:
        with restore_on_termination():
            stdout, stderr = proc.communicate(timeout=timeout)
        return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)
    except BaseException:
        stop_group(proc)
        proc.communicate()  # close capture pipes; no writers outlive isolation
        raise




def bounded_command(command, *, cap=900, runner=None) -> int:
    """Bound a workflow stage, including retries inside its Python process."""
    if not command or not math.isfinite(cap) or cap <= 0:
        print("::error::Reserve-Auftrag benötigt Kommando und positives Zeitlimit.")
        return 3
    remaining = work_seconds(cap)
    if remaining <= 0:
        print("::warning::Reserve-Arbeitsbudget erschöpft – kein neuer Prozess.")
        return 124
    runner = run_healer if runner is None else runner
    try:
        result = runner(command, cwd=ROOT, env=dict(os.environ), timeout=remaining)
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        return result.returncode
    except (subprocess.TimeoutExpired, WorkInterrupted) as exc:
        # communicate() exposes the actual partial output even on timeout.
        for output, stream in ((getattr(exc, "output", None), sys.stdout),
                               (getattr(exc, "stderr", None), sys.stderr)):
            if output:
                print(output.decode("utf-8", "replace") if isinstance(output, bytes)
                      else output, end="", file=stream)
        print("::warning::Reserve-Auftrag zeitlich beendet; Prozessgruppe gestoppt.")
        return 124
    except OSError as exc:
        print(f"::error::Reserve-Auftrag nicht ausführbar: {exc}")
        return 3


def start_window(*, minutes=65, env_file=None, now=None) -> int:
    """Anchor the clock only; this is NOT a tool proof or writing permission."""
    if not math.isfinite(minutes) or not 1 <= minutes <= 90:
        print("::error::Reserve-Arbeitsfenster muss zwischen 1 und 90 Minuten liegen.")
        return 3
    current = time.time() if now is None else now
    if env_file:
        with Path(env_file).open("a", encoding="utf-8") as handle:
            handle.write(f"{DEADLINE_ENV}={current + minutes * 60:.6f}\n")
    print(f"⏱ Reserve-Arbeitsfenster verankert ({minutes:g} min); "
          "kein Schreibrecht – Werkzeug- und Wachenprüfung folgen.")
    return 0


def preflight(*, minutes=65, env_file=None, now=None, checker=None) -> int:
    """Only a real tool proof can grant the workflow's writing window."""
    if not math.isfinite(minutes) or not 1 <= minutes <= 90:
        print("::error::Reserve-Arbeitsfenster muss zwischen 1 und 90 Minuten liegen.")
        return 3
    if checker is None:
        from reserve_recert import gate_verfuegbar
        checker = gate_verfuegbar
    ok, reason = checker()
    if not ok:
        print(f"::error::RESERVE-WERKZEUG: {reason}. Kein Schreibauftrag erteilt.")
        return 3
    current = time.time() if now is None else now
    remaining = work_seconds(minutes * 60, now=current)
    if remaining <= 0:
        print("::error::Reserve-Arbeitsbudget erschöpft/ungültig; kein Schreibauftrag.")
        return 124
    if env_file:
        deadline = current + remaining
        with Path(env_file).open("a", encoding="utf-8") as handle:
            handle.write(f"{DEADLINE_ENV}={deadline:.6f}\n")
    print(f"✅ Reserve-Werkzeug geprüft: {reason} · Restbudget {remaining / 60:.1f} min; "
          "Sicherung und End-Gate bleiben außerhalb des Arbeitsbudgets.")
    return 0


def run_selftest() -> int:
    """Own promises: malformed budgets, failed tools and graceful termination."""
    for raw in ("", "x", "nan", "inf", "-inf", "99"):
        assert work_seconds(30, env={DEADLINE_ENV: raw}, now=100) == 0
    assert work_seconds(30, env={}, now=100) == 30
    assert work_seconds(30, env={DEADLINE_ENV: "110"}, now=100) == 10
    assert work_seconds(30, env={DEADLINE_ENV: "999"}, now=100) == 30
    from unittest import mock
    with mock.patch.dict(os.environ, {}, clear=True), \
            tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "env"
        with contextlib.redirect_stdout(__import__("io").StringIO()):
            assert preflight(env_file=path, checker=lambda: (False, "Probe")) == 3
            assert not path.exists()
            assert preflight(minutes=65, env_file=path, now=100,
                             checker=lambda: (True, "Probe")) == 0
        assert path.read_text() == f"{DEADLINE_ENV}=4000.000000\n"
    old = signal.getsignal(signal.SIGTERM)
    try:
        with restore_on_termination():
            handler = signal.getsignal(signal.SIGTERM)
            handler(signal.SIGTERM, None)
    except WorkInterrupted:
        pass
    else:
        raise AssertionError("SIGTERM führt nicht durch finally")
    assert signal.getsignal(signal.SIGTERM) == old
    print("✅ Reserve-Operations-Selbsttest: Budget, Werkzeug-Sperre, "
          "schreibfreier Fehlerpfad und SIGTERM-Restaurierung bestanden.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", action="store_true",
                        help="Arbeitsfenster vor Installation/Selbsttests verankern")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--max-minuten", type=float, default=65)
    parser.add_argument("--timeout-sekunden", type=float, default=900)
    parser.add_argument("--run", nargs=argparse.REMAINDER,
                        help="Auftrag im verbleibenden Arbeitsbudget ausführen")
    args = parser.parse_args(argv)
    if args.selftest:
        return run_selftest()
    if args.run is not None:
        return bounded_command(args.run, cap=args.timeout_sekunden)
    if args.start:
        return start_window(minutes=args.max_minuten,
                            env_file=os.environ.get("GITHUB_ENV"))
    if args.preflight:
        return preflight(minutes=args.max_minuten,
                         env_file=os.environ.get("GITHUB_ENV"))
    parser.error("--start, --preflight, --run oder --selftest erforderlich")


if __name__ == "__main__":
    raise SystemExit(main())
