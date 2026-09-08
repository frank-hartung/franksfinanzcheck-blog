#!/usr/bin/env python3
"""Preflight the stock on quiet days. Count proven articles, not reserve flags.

Zertifiziert die Reife der Reserve-Pool-Kandidaten mit den ECHTEN
Produktions-Gates (quality_score >= 0.85 + publish_gate STRICT + hugo-Render-
Beweis) und schreibt hash-gesicherte Zertifikate nach
data/reserve-readiness.json. Ein Zertifikat gilt nur für EXAKT diesen
Datei-Inhalt (sha256) – jede spätere Änderung macht den Kandidaten wieder
„offen“ (wird von engine_generate/_reserve_topup und reserve_finisher
respektiert).

Reparatur 08.09.2026 (Issue #224): Diagnose pro Kandidat (Score-Teile bzw.
Gate-Grund) wird im JSON und auf stdout mitgeliefert, damit der tägliche
Lauf bei „Stock shortage“ die konkrete Ursache nennt statt nur 0/6.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import reserve_pool as rp  # noqa: E402
from publication_release import accept_candidate  # noqa: E402


def target() -> int:
    try:
        return int(os.environ.get("RESERVE_TARGET") or "6")
    except ValueError:
        return 6


def score_diagnosis(index) -> dict | None:
    """Lesende Score-Diagnose (weakest parts) – bevor das harte Gate läuft."""
    try:
        import quality_score as qs
        return qs.score_article(str(index))
    except Exception as exc:  # noqa: BLE001 – Diagnose darf nie blockieren
        return {"fehler": str(exc)}


def main():
    rows = []
    for index in rp.reserve_drafts():
        original = index.read_text(encoding="utf-8")
        diag = score_diagnosis(index)
        ready, reason = False, None
        try:
            rp.publish_one(index)
            ready = accept_candidate(index)
            if not ready:
                if diag and diag.get("score") is not None \
                        and diag["score"] < 0.85:
                    schwach = ", ".join(
                        f"{k} {v:.2f}" for k, v in sorted(
                            diag.get("parts", {}).items(),
                            key=lambda kv: kv[1])[:3])
                    reason = (f"quality-score {diag['score']} < 0.85 "
                              f"(schwach: {schwach})")
                else:
                    reason = ("publish_gate/hugo abgelehnt (STRICT dry-run) – "
                              "Details im Workflow-Log")
        except Exception as exc:  # noqa: BLE001 – nie am Gate scheitern
            ready, reason = False, f"Gate-Ausnahme: {exc}"
        finally:
            index.write_text(original, encoding="utf-8")
        row = {"slug": index.parent.name, "ready": ready,
               "sha256": hashlib.sha256(original.encode()).hexdigest()}
        if reason:
            row["reason"] = reason
        if diag:
            row["score"] = diag.get("score")
            row["parts"] = diag.get("parts")
        rows.append(row)

    goal = target()
    ready_count = sum(r["ready"] for r in rows)
    report = {"target": goal, "ready": ready_count, "candidates": rows}
    (ROOT / "data" / "reserve-readiness.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    if ready_count < goal:
        print(f"\n🛑 RESERVE-ENGPAß: {ready_count}/{goal} Kandidaten "
              f"gate-fertig.")
        for r in rows:
            mark = "✅" if r["ready"] else "⛔"
            extra = f" – {r.get('reason', '')}" if r.get("reason") else ""
            score = f" | Score {r.get('score')}" if "score" in r else ""
            print(f"   {mark} {r['slug']}{score}{extra}")
        print("   Nächster Schritt: Heiler-Kette via "
              "`python3 scripts/reserve_finisher.py --finish` (im Workflow "
              "automatisch) und/oder Redaktion prüft die Diagnose.")
    else:
        print(f"\n✅ Reserve-Pool vollständig gate-fertig ({ready_count}/{goal}).")
    return 0 if ready_count >= goal else 1


if __name__ == "__main__":
    raise SystemExit(main())
