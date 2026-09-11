#!/usr/bin/env python3
"""
reserve_gate.py – Hartes End-Gate der Content-Reserve-Produktionslinie.

Liest das von reserve_readiness.py geschriebene, hash-gesicherte
Zertifikat (data/reserve-readiness.json) und beantwortet EINE Frage:

    Sind mindestens RESERVE_TARGET Kandidaten am echten
    Produktions-Gate zertifiziert (ready=true)?

Grundregel „Stock shortage must not look successful": Bei Engpass
darf der Workflow NICHT grün werden. Exit-Code 0 nur bei vollem Ziel.

Verwendung:
    python3 scripts/reserve_gate.py                 # Workflow-End-Gate
    python3 scripts/reserve_gate.py --selftest      # Sabotageschutz
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CERT = ROOT / "data" / "reserve-readiness.json"


def evaluate(cert_path: Path) -> tuple[int, int, list[dict]]:
    """Liefert (ready, target, candidates). Fehlt das Zertifikat,
    gilt der Pool als leer (0/target) – ein abgestürzter Lauf darf
    nicht als erfolgreich aussehen."""
    if not cert_path.exists():
        return 0, int(os.environ.get("RESERVE_TARGET", "6")), []
    data = json.loads(cert_path.read_text(encoding="utf-8"))
    target = int(data.get("target", os.environ.get("RESERVE_TARGET", "6")))
    candidates = data.get("candidates", [])
    ready = sum(1 for r in candidates if r.get("ready"))
    return ready, target, candidates


def report(ready: int, target: int, candidates: list[dict]) -> None:
    if ready >= target:
        print(f"\u2705 Reserve-Pool gate-fertig: {ready}/{target} Kandidaten zertifiziert.")
        return
    print(f"\U0001f6d1 RESERVE-ENGPA\u00df: nur {ready}/{target} Kandidaten gate-fertig.")
    for r in candidates:
        mark = "\u2705" if r.get("ready") else "\u26d4"
        score = f" | Score {r.get('score')}" if r.get("score") is not None else ""
        reason = f" \u2013 {r.get('reason', '')}" if r.get("reason") else ""
        print(f"   {mark} {r.get('slug', '<ohne-slug>')}{score}{reason}")
    if ready > 0 and not candidates:
        print("   (Zertifikat ohne Kandidatenliste)")
    print("   Diagnose: RESERVE-FINISH-REPORT.md (Score-Teile je Kandidat/Heiler).")


def run_selftest() -> int:
    cert_cases = []
    with tempfile.TemporaryDirectory() as tmp:
        cert = Path(tmp) / "reserve-readiness.json"

        # Fall 1: kein Zertifikat -> wie leerer Pool behandeln
        ready, target, candidates = evaluate(cert)
        assert (ready, target, candidates) == (0, 6, []), "fehlendes Zertifikat muss leer zählen"

        # Fall 2: 5/6 -> Engpass
        cert.write_text(json.dumps({
            "target": 6, "ready": 5,
            "candidates": [{"slug": f"k{i}", "ready": i < 5,
                            "score": 0.9 if i < 5 else None,
                            "reason": None if i < 5 else "R5"} for i in range(6)],
        }, ensure_ascii=False), encoding="utf-8")
        ready, target, candidates = evaluate(cert)
        assert (ready, target) == (5, 6), f"5/6 erwartet, {ready}/{target}"
        assert len(candidates) == 6

        # Fall 3: 6/6 -> voll
        cert.write_text(json.dumps({
            "target": 6, "ready": 6,
            "candidates": [{"slug": f"k{i}", "ready": True, "score": 0.95} for i in range(6)],
        }, ensure_ascii=False), encoding="utf-8")
        ready, target, _ = evaluate(cert)
        assert (ready, target) == (6, 6), f"6/6 erwartet, {ready}/{target}"

        # Fall 4: überfüllt 7/6 -> ebenfalls grün
        cert.write_text(json.dumps({
            "target": 6, "ready": 7,
            "candidates": [{"slug": f"k{i}", "ready": True} for i in range(7)],
        }, ensure_ascii=False), encoding="utf-8")
        ready, target, _ = evaluate(cert)
        assert ready >= target, "7/6 muss grün sein"

        cert_cases.append("ok")
    print(f"\u2705 Selbsttest reserve_gate: {len(cert_cases)} Fälle bestanden.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Harter End-Gate der Content-Reserve")
    ap.add_argument("--selftest", action="store_true", help="interne Tests ausführen")
    ap.add_argument("--cert", default=str(CERT), help="Pfad zum Zertifikat (für Tests)")
    args = ap.parse_args()
    if args.selftest:
        return run_selftest()
    ready, target, candidates = evaluate(Path(args.cert))
    report(ready, target, candidates)
    return 0 if ready >= target else 1


if __name__ == "__main__":
    sys.exit(main())
