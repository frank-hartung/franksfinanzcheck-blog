#!/usr/bin/env python3
"""ops_report.py – Täglicher FrankAutoOps-Report (maschinenlesbar + Kurzfassung)

Standard-Output-Format:
{
  "audit": {...},      # Audit-Statistik + letzte Events
  "playbooks": [...],  # aktive Automatisierungen (Workflows) + Status
  "commands": [...],   # vom System ausgeführte Aktionen (heute)
  "reports": {...},    # Qualitäts-Scores, Gates, Kennzahlen
  "next_steps": [...]  # priorisierte nächste Schritte
}

CLI:
  python3 scripts/ops_report.py            # JSON (maschinenlesbar)
  python3 scripts/ops_report.py --summary  # menschliche Kurzfassung
"""
import datetime
import glob
import json
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import audit_log  # noqa: E402


def _count_posts() -> int:
    return len(glob.glob(f"{BLOG_DIR}/content/posts/*/index.md"))


def _quality_summary() -> dict:
    try:
        import quality_score as qs
        files = sorted(glob.glob(f"{BLOG_DIR}/content/posts/*/index.md"))
        results = [qs.score_article(f) for f in files]
        avg = sum(r["score"] for r in results) / len(results) if results else 0
        return {
            "articles": len(results),
            "avg_score": round(avg, 3),
            "publish": sum(1 for r in results if r["verdict"] == "publish"),
            "draft_autofix": sum(1 for r in results if r["verdict"] == "draft+autofix"),
            "human_review": [r["slug"] for r in results if r["verdict"] == "human-review"],
        }
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


def _playbooks() -> list[dict]:
    """Aktive Automatisierungen aus .github/workflows (Name + Trigger)."""
    playbooks = []
    for f in sorted(glob.glob(f"{BLOG_DIR}/.github/workflows/*.yml")):
        name = os.path.basename(f).replace(".yml", "")
        triggers = []
        try:
            import yaml
            data = yaml.safe_load(open(f, encoding="utf-8"))
            on = data.get("on", {})
            if isinstance(on, dict):
                triggers = list(on.keys())
            elif isinstance(on, str):
                triggers = [on]
        except Exception:  # noqa: BLE001
            triggers = ["?"]
        playbooks.append({"name": name, "triggers": triggers})
    return playbooks


def _today_events() -> list[dict]:
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    path = os.path.join(audit_log.AUDIT_DIR, f"{today}.jsonl")
    events = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return events


def build_report() -> dict:
    events = _today_events()
    audit_stats = audit_log.report()
    q = _quality_summary()

    report = {
        "audit": {
            "today_events": len(events),
            "total_events": audit_stats.get("total", 0),
            "errors": audit_stats.get("error", 0),
            "critical": audit_stats.get("critical", 0),
            "last_events": events[-5:],
        },
        "playbooks": _playbooks(),
        "commands": [
            {"ts": e.get("ts"), "module": e.get("module"),
             "action": e.get("action"), "status": e.get("status")}
            for e in events
        ],
        "reports": {
            "content": {"posts": _count_posts()},
            "quality": q,
        },
        "next_steps": _next_steps(q, audit_stats),
    }
    return report


def _next_steps(q: dict, audit_stats: dict) -> list[dict]:
    steps = []
    if q.get("human_review"):
        steps.append({"priority": 1, "action": "human-review",
                      "detail": f"Artikel unter 0.80: {', '.join(q['human_review'][:5])}"})
    if audit_stats.get("error", 0) > 0:
        steps.append({"priority": 1, "action": "investigate-errors",
                      "detail": f"{audit_stats['error']} Audit-Fehler – Logs prüfen"})
    if audit_stats.get("critical", 0) > 0:
        steps.append({"priority": 1, "action": "critical-incident",
                      "detail": "Kritische Vorfälle vorhanden – sofort prüfen"})
    steps.append({"priority": 2, "action": "run-content-engine",
                  "detail": "Content-Engine v2 läuft automatisch (Crons 08:10–19:40 MESZ)"})
    steps.append({"priority": 3, "action": "monitor-tls-cert",
                  "detail": "GitHub-TLS-Zertifikat: Watchdog Check 4 meldet, sobald da → Full (strict)"})
    steps.append({"priority": 3, "action": "pinterest-token",
                  "detail": "PINTEREST_ACCESS_TOKEN fehlt → Pinterest-AI postet noch nicht"})
    return steps


def main() -> int:
    report = build_report()
    if "--summary" in sys.argv:
        q = report["reports"]["quality"]
        lines = [
            f"FrankAutoOps-Report {datetime.date.today().isoformat()}",
            f"  Artikel: {q.get('articles', '?')} | Ø-Score: {q.get('avg_score', '?')} "
            f"(publish {q.get('publish', '?')} / draft {q.get('draft_autofix', '?')} "
            f"/ review {len(q.get('human_review', []))})",
            f"  Audit heute: {report['audit']['today_events']} Events | Fehler: {report['audit']['errors']}",
            f"  Playbooks aktiv: {len(report['playbooks'])}",
            "  Nächste Schritte:",
        ]
        for s in report["next_steps"][:4]:
            lines.append(f"    P{s['priority']} {s['action']}: {s['detail']}")
        print("\n".join(lines))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
