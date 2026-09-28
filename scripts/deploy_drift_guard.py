#!/usr/bin/env python3
"""
DEPLOY-DRIFT-WACHE – Profi-Agentur-Level Deploy- & Drift-Absicherung
===================================================================

Schließt die Deploy-Drift-Lücke (Befund Issue #433, 28.09.2026):
Wenn ein gemergter Site-PR (z. B. #431 Pillar-Cluster-CSS) in der
`pages-deploy`-Warteschlange von einem nachfolgenden reinen Workflow-/
State-Push verdrängt und abgebrochen wird, durfte das Relevanz-Gate
des Folge-Pushes nicht nur `before...after` vergleichen – und der
Deploy-Catchup durfte einen Lauf mit übersprungenem Deploy-Job nicht
als „letzten erfolgreichen Deploy" zählen.

DIESES MODUL IST DIE SINGLE SOURCE OF TRUTH (SSOT) FÜR:
  1. `STATE_ONLY`-Negativliste: Welche Dateien sind reine Zustands-,
     Doku- oder CI-Pfade ohne Wirkung auf die gebaute Live-Site.
  2. Live-Stand-Ermittlung (`gh-pages` Commit-Message `deploy: <SHA>`).
  3. Paritäts- & Drift-Prüfung zwischen main-HEAD und dem Live-Stand.

Drift-Zustände:
  • IN_SYNC          – main-HEAD ist byte-identisch mit dem Live-Stand.
  • STATE_ONLY_DIFF  – main-HEAD ist neuer, enthält aber NUR State-/Doku-
                       Änderungen. Kein Deploy nötig (Actions-Entlastung).
  • SITE_DRIFT       – Mindestens eine site-relevante Datei (Content, CSS,
                       Layout, Config, Data) ist auf main, aber nicht live!
                       -> SOFORTIGER HANDLUNGSBEDARF (Deploy auslösen).
  • UNKNOWN_BASE     – Der Live-Stand konnte nicht ermittelt werden
                       (Erst-Deploy, Netzwerkfehler) -> Fehlsicherheit: Deploy.

Nutzung:
  python3 scripts/deploy_drift_guard.py --check
  python3 scripts/deploy_drift_guard.py --json
  python3 scripts/deploy_drift_guard.py --report DEPLOY-DRIFT-REPORT.md
  python3 scripts/deploy_drift_guard.py --selftest
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ============================================================
#  STATE_ONLY NEGATIVLISTE (SSOT)
#  ------------------------------------------------------------
#  NUR bekannte reine Zustands-, Protokoll- und Doku-Pfade sind
#  deploy-irrelevant.
#  ALLES ANDERE (content/, layouts/, assets/, static/, hugo.toml,
#  data/themenwelten.json, data/saisons.yaml, data/affiliate_ziele.yaml, ...)
#  ist per Default RELEVANT – Fail-safe-Architektur.
# ============================================================
STATE_ONLY_PATTERN = (
    r"^(\.github/.*|"
    r"docs/.*|"
    r"scripts/.*|"
    r"e2e/.*|"
    r"data/social/.*|"
    r"data/research/.*|"
    r"data/audit/.*|"
    r"data/[^/]*_state\.json|"
    r"data/[^/]*_history\.jsonl|"
    r"data/[^/]*\.meta\.json|"
    r"data/social_log\.jsonl|"
    r"data/secrets_state\.json|"
    r"data/pinterest_token_state\.json|"
    r"data/integrity_lock\.json|"
    r"data/governance_status\.json|"
    r"data/governance_history\.jsonl|"
    r"data/alerting_heartbeat\.json|"
    r"data/revenue_funnel\.json|"
    r"static/images/social/.*|"
    r"\.[^/]*_state\.json|"
    r"\.casing_report\.json|"
    r"\.indexnow_submitted\.json|"
    r"\.meta_cache\.json|"
    r"\.affiliate_integrity_state\.json|"
    r"\.gitignore|"
    r"package\.json|"
    r"package-lock\.json|"
    r"[A-Za-z0-9._-]+\.md)$"
)

RE_STATE_ONLY = re.compile(STATE_ONLY_PATTERN)
RE_DEPLOY_COMMIT = re.compile(r"deploy:\s*([0-9a-fA-F]{40})", re.IGNORECASE)


def is_state_only(path: str) -> bool:
    """Gibt True zurück, wenn der Pfad ein reiner Zustands-/Doku-Pfad ist."""
    norm = path.strip().replace("\\", "/")
    return bool(RE_STATE_ONLY.match(norm))


def is_site_relevant(path: str) -> bool:
    """Gibt True zurück, wenn der Pfad die Live-Site beeinflusst."""
    return not is_state_only(path)


def parse_deployed_sha(commit_message: str) -> str | None:
    """Extrahiert die 40-Zeichen Git-SHA aus der Deploy-Commit-Message von actions-gh-pages."""
    if not commit_message:
        return None
    match = RE_DEPLOY_COMMIT.search(commit_message)
    if match:
        return match.group(1).lower()
    return None


def get_live_deployed_sha_local(root_dir: Path | str = ROOT) -> str | None:
    """Versucht, den deployed SHA aus dem lokalen origin/gh-pages Branch zu lesen."""
    root = Path(root_dir)
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "log", "-n", "1", "--format=%B", "origin/gh-pages"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if proc.returncode == 0 and proc.stdout:
            sha = parse_deployed_sha(proc.stdout)
            if sha:
                return sha
    except Exception:
        pass

    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "log", "-n", "1", "--format=%B", "gh-pages"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if proc.returncode == 0 and proc.stdout:
            sha = parse_deployed_sha(proc.stdout)
            if sha:
                return sha
    except Exception:
        pass

    return None


def get_live_deployed_sha_gh_cli(repo: str | None = None) -> str | None:
    """Versucht, den deployed SHA über die GitHub CLI (gh api) abzufragen."""
    try:
        cmd = ["gh", "api"]
        if repo:
            cmd.append(f"repos/{repo}/commits/gh-pages")
        else:
            cmd.append("repos/:owner/:repo/commits/gh-pages")
        cmd.extend(["--jq", ".commit.message"])

        proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=10)
        if proc.returncode == 0 and proc.stdout:
            sha = parse_deployed_sha(proc.stdout)
            if sha:
                return sha
    except Exception:
        pass
    return None


def get_live_deployed_sha(root_dir: Path | str = ROOT, repo: str | None = None) -> str | None:
    """Ermittelt den deployed SHA (primär lokal via Git-Ref, sekundär via gh CLI)."""
    sha = get_live_deployed_sha_local(root_dir)
    if sha:
        return sha
    return get_live_deployed_sha_gh_cli(repo)


def get_head_sha(root_dir: Path | str = ROOT, ref: str = "main") -> str | None:
    """Ermittelt die HEAD-SHA des Ziel-Branches."""
    root = Path(root_dir)
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", ref],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip().lower()
    except Exception:
        pass
    return None


def get_changed_files_between_shas(
    base_sha: str, head_sha: str, root_dir: Path | str = ROOT, repo: str | None = None
) -> list[str]:
    """Liefert die Liste aller geänderten Dateien zwischen base_sha und head_sha."""
    root = Path(root_dir)
    # 1. Lokaler Git-Diff
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "diff", "--name-only", f"{base_sha}...{head_sha}"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        if proc.returncode == 0:
            return [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    except Exception:
        pass

    # 2. Fallback: gh api compare
    try:
        target = f"repos/{repo}/compare/{base_sha}...{head_sha}" if repo else f"repos/:owner/:repo/compare/{base_sha}...{head_sha}"
        proc = subprocess.run(
            ["gh", "api", target, "--paginate", "--jq", ".files[].filename"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        if proc.returncode == 0:
            return [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    except Exception:
        pass

    return []


def analyze_drift(
    base_sha: str | None,
    head_sha: str | None,
    changed_files: list[str] | None = None,
    root_dir: Path | str = ROOT,
    repo: str | None = None,
    auto_detect: bool = True,
) -> dict:
    """Führt die vollständige Drift-Analyse durch."""
    if head_sha is None and auto_detect:
        head_sha = get_head_sha(root_dir)

    if base_sha is None and auto_detect:
        base_sha = get_live_deployed_sha(root_dir, repo)

    if not base_sha:
        return {
            "status": "UNKNOWN_BASE",
            "is_drift": True,
            "needs_deploy": True,
            "reason": "Live-Stand auf gh-pages konnte nicht ermittelt werden (Erst-Deploy oder Ref fehlt)",
            "base_sha": None,
            "head_sha": head_sha,
            "changed_files_count": 0,
            "relevant_files": [],
            "state_files": [],
        }

    if head_sha and base_sha.lower() == head_sha.lower():
        return {
            "status": "IN_SYNC",
            "is_drift": False,
            "needs_deploy": False,
            "reason": f"main-HEAD ({head_sha[:7]}) ist exakt identisch mit gh-pages ({base_sha[:7]})",
            "base_sha": base_sha,
            "head_sha": head_sha,
            "changed_files_count": 0,
            "relevant_files": [],
            "state_files": [],
        }

    if changed_files is None and head_sha:
        changed_files = get_changed_files_between_shas(base_sha, head_sha, root_dir, repo)

    changed_files = changed_files or []
    relevant_files = [f for f in changed_files if is_site_relevant(f)]
    state_files = [f for f in changed_files if is_state_only(f)]

    if not relevant_files and changed_files:
        return {
            "status": "STATE_ONLY_DIFF",
            "is_drift": False,
            "needs_deploy": False,
            "reason": f"main ({head_sha[:7] if head_sha else 'HEAD'}) weicht von gh-pages ({base_sha[:7]}) ab, enthält aber nur {len(state_files)} State-/Doku-Dateien",
            "base_sha": base_sha,
            "head_sha": head_sha,
            "changed_files_count": len(changed_files),
            "relevant_files": [],
            "state_files": state_files,
        }

    if relevant_files:
        return {
            "status": "SITE_DRIFT",
            "is_drift": True,
            "needs_deploy": True,
            "reason": f"Deploy-Drift: {len(relevant_files)} site-relevante Datei(en) auf main ({head_sha[:7] if head_sha else 'HEAD'}), aber nicht live auf gh-pages ({base_sha[:7]})!",
            "base_sha": base_sha,
            "head_sha": head_sha,
            "changed_files_count": len(changed_files),
            "relevant_files": relevant_files,
            "state_files": state_files,
        }

    # Keine Dateien gefunden oder compare fehlgeschlagen -> Fail-safe
    return {
        "status": "UNKNOWN_DIFF",
        "is_drift": True,
        "needs_deploy": True,
        "reason": f"SHAs weichen ab ({base_sha[:7]} != {head_sha[:7] if head_sha else 'HEAD'}), aber Dateiliste ist leer/unvollständig (Fehlsicherheit)",
        "base_sha": base_sha,
        "head_sha": head_sha,
        "changed_files_count": 0,
        "relevant_files": [],
        "state_files": [],
    }


def generate_markdown_report(result: dict) -> str:
    """Erzeugt einen sauberen Markdown-Report über den Drift-Zustand."""
    lines = [
        "# 🚀 DEPLOY-DRIFT-BERICHT (Profi-Agentur-Level)",
        "",
        f"**Status:** `{result['status']}` · **Bedarf:** {'🚨 DEPLOY ERFORDERLICH' if result['needs_deploy'] else '✅ LIVE-STAND AKTUELL'}",
        "",
        "## Übersicht",
        "",
        f"- **Live auf `gh-pages`:** `{result.get('base_sha') or 'unbekannt'}`",
        f"- **Ziel `main` HEAD:** `{result.get('head_sha') or 'unbekannt'}`",
        f"- **Gesamt veränderte Dateien:** {result.get('changed_files_count', 0)}",
        f"- **Site-relevante Dateien:** {len(result.get('relevant_files', []))}",
        f"- **Reine Zustands-/Doku-Dateien:** {len(result.get('state_files', []))}",
        "",
        f"**Diagnose:** {result['reason']}",
        "",
    ]

    if result.get("relevant_files"):
        lines.extend([
            "### 🚨 Site-relevante Dateien (nicht deployt):",
            "",
            *[f"- `{f}`" for f in result["relevant_files"][:25]],
            *(["- … (weitere gekürzt)"] if len(result["relevant_files"]) > 25 else []),
            "",
        ])

    if result.get("state_files"):
        lines.extend([
            "### ℹ️ Zustands- / Doku-Dateien (Deploy-irrelevant):",
            "",
            *[f"- `{f}`" for f in result["state_files"][:15]],
            *(["- … (weitere gekürzt)"] if len(result["state_files"]) > 15 else []),
            "",
        ])

    return "\n".join(lines)


# ============================================================
#  SELBSTTEST (Sabotage- & Regressionsschutz)
# ============================================================
def run_selftest() -> list[str]:
    """Prüft alle Logikpfade, Negativliste und Regressions-Szenarien deterministisch."""
    failures: list[str] = []

    # 1. Test: STATE_ONLY Negativliste
    site_paths = [
        "content/posts/2026-09-15-test/index.md",
        "layouts/_default/baseof.html",
        "layouts/pillar/single.html",
        "assets/css/extended/custom.css",
        "assets/css/extended/zzz-agency-polish.css",
        "static/images/cover.jpg",
        "hugo.toml",
        "data/themenwelten.json",
        "data/saisons.yaml",
        "data/affiliate_ziele.yaml",
        "data/design/varianten.yaml",
        "data/aktuelle_entwicklungen.yaml",
        "data/korrekturen.yaml",
        "data/newsletter_studio.json",
        "data/newsletter_kadenz.json",
    ]
    for p in site_paths:
        if is_state_only(p):
            failures.append(f"ST1: Site-Pfad `{p}` fälschlicherweise als state-only eingestuft!")
        if not is_site_relevant(p):
            failures.append(f"ST1: Site-Pfad `{p}` nicht als site-relevant erkannt!")

    state_paths = [
        ".affiliate_integrity_state.json",
        ".affiliate_intent_state.json",
        ".bestand_gate_state.json",
        ".casing_report.json",
        ".indexnow_submitted.json",
        ".meta_cache.json",
        "AFFILIATE-INTEGRITY-REPORT.md",
        "PRODUKTIONS-STATUS.md",
        "BOT-WATCHDOG-REPORT.md",
        "PILLAR-CLUSTER-CSS-REPARATUR-PREMIUM-2026-09-28.md",
        "README.md",
        "docs/README.md",
        "scripts/affiliate_integrity_gate.py",
        "scripts/deploy_drift_guard.py",
        ".github/workflows/deploy.yml",
        ".github/workflows/deploy-catchup.yml",
        "e2e/newsletter.spec.mjs",
        "package.json",
        "package-lock.json",
        ".gitignore",
        "static/images/social/pin.jpg",
        "data/alert_router_state.json",
        "data/integrity_history.jsonl",
        "data/integrity_lock.json",
        "data/spam_history.jsonl",
        "data/social_log.jsonl",
        "data/secrets_state.json",
        "data/pinterest_token_state.json",
        "data/governance_status.json",
        "data/governance_history.jsonl",
        "data/alerting_heartbeat.json",
        "data/revenue_funnel.json",
        "data/revenue_funnel_history.jsonl",
        "data/cwv_history.jsonl",
        "data/cwv_state.json",
        "data/awin_fetch.meta.json",
        "data/umami_clicks.meta.json",
        "data/social/plan.json",
        "data/research/brief.md",
        "data/audit/2026-09-15.jsonl",
    ]
    for p in state_paths:
        if not is_state_only(p):
            failures.append(f"ST2: State-Pfad `{p}` nicht als state-only erkannt!")
        if is_site_relevant(p):
            failures.append(f"ST2: State-Pfad `{p}` fälschlicherweise als site-relevant markiert!")

    # 2. Test: Commit-Message-Parsing
    test_msg = "deploy: a263bcb3d67d08a81ce8407b4768dad5a2808979"
    parsed = parse_deployed_sha(test_msg)
    if parsed != "a263bcb3d67d08a81ce8407b4768dad5a2808979":
        failures.append(f"ST3: Commit-Message SHA Parsing fehlerhaft: {parsed}")

    multiline_msg = "deploy: 1d3a0b0d00000000000000000000000000000000\n\nAutomated GitHub Pages deployment"
    if parse_deployed_sha(multiline_msg) != "1d3a0b0d00000000000000000000000000000000":
        failures.append("ST3: Multiline Commit-Message SHA Parsing fehlerhaft")

    if parse_deployed_sha("chore: initial commit") is not None:
        failures.append("ST3: Nicht-Deploy Commit durfte keine SHA parsen")

    # 3. Test: Drift-Szenarien
    sha1 = "a263bcb3d67d08a81ce8407b4768dad5a2808979"
    sha2 = "1d3a0b0d00000000000000000000000000000000"

    # Szenario A: In Sync
    r_sync = analyze_drift(sha1, sha1, [], auto_detect=False)
    if r_sync["status"] != "IN_SYNC" or r_sync["needs_deploy"]:
        failures.append(f"ST4: In-Sync Erkennung fehlgeschlagen: {r_sync}")

    # Szenario B: Reiner State-Diff (#432 Dependabot / State)
    r_state = analyze_drift(sha1, sha2, [".github/workflows/deploy.yml", "data/alert_router_state.json"], auto_detect=False)
    if r_state["status"] != "STATE_ONLY_DIFF" or r_state["needs_deploy"]:
        failures.append(f"ST5: State-Only Diff durfte keinen Deploy anfordern: {r_state}")

    # Szenario C: Site-Drift (#431 Pillar-Cluster-CSS verpasst!)
    r_drift = analyze_drift(
        sha1,
        sha2,
        [
            ".github/workflows/deploy.yml",
            "assets/css/extended/zzz-agency-polish.css",
            "layouts/pillar/single.html",
        ],
        auto_detect=False,
    )
    if r_drift["status"] != "SITE_DRIFT" or not r_drift["needs_deploy"] or not r_drift["is_drift"]:
        failures.append(f"ST6: Site-Drift (#431) nicht erkannt: {r_drift}")

    # Szenario D: Unbekannte Basis
    r_unk = analyze_drift("", sha1, [], auto_detect=False)
    if r_unk["status"] != "UNKNOWN_BASE" or not r_unk["needs_deploy"]:
        failures.append(f"ST7: Unbekannte Basis muss Fehlsicherheit (Deploy) auslösen: {r_unk}")

    # 4. Test: Markdown Report Generator
    rep = generate_markdown_report(r_drift)
    if "DEPLOY-DRIFT-BERICHT" not in rep or "zzz-agency-polish.css" not in rep:
        failures.append("ST8: Markdown-Report unvollständig")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy-Drift-Wache (SSOT für Deploy-Relevanz und Drift)")
    parser.add_argument("--check", action="store_true", help="Drift prüfen und lesbaren Bericht ausgeben")
    parser.add_argument("--json", action="store_true", help="Drift als JSON ausgeben")
    parser.add_argument("--report", type=str, default="", help="Pfad für Markdown-Bericht")
    parser.add_argument("--selftest", action="store_true", help="Selbsttest ausführen")
    parser.add_argument("--base", type=str, default="", help="Explizite Basis-SHA (Default: gh-pages)")
    parser.add_argument("--head", type=str, default="", help="Explizite Ziel-SHA (Default: main)")
    parser.add_argument("--repo", type=str, default="", help="GitHub Repository (owner/repo)")

    args = parser.parse_args()

    if args.selftest:
        failures = run_selftest()
        if failures:
            for f in failures:
                print(f"❌ {f}", file=sys.stderr)
            return 2
        print("✅ DEPLOY-DRIFT-WACHE-SELFTEST bestanden (Negativliste, SHA-Parsing, 4 Drift-Szenarien).")
        return 0

    base_sha = args.base or None
    head_sha = args.head or None
    result = analyze_drift(base_sha, head_sha, root_dir=ROOT, repo=args.repo or None)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"=== DEPLOY-DRIFT-WACHE ===")
        print(f"Status      : {result['status']}")
        print(f"Bedarf      : {'🚨 DEPLOY NÖTIG' if result['needs_deploy'] else '✅ KEIN DEPLOY NÖTIG'}")
        print(f"Live-SHA    : {result.get('base_sha') or 'unbekannt'}")
        print(f"Ziel-SHA    : {result.get('head_sha') or 'unbekannt'}")
        print(f"Begründung  : {result['reason']}")
        if result.get("relevant_files"):
            print("Site-relevante Dateien:")
            for rf in result["relevant_files"][:10]:
                print(f"  • {rf}")

    if args.report:
        rep_content = generate_markdown_report(result)
        Path(args.report).write_text(rep_content, encoding="utf-8")
        print(f"📄 Bericht geschrieben nach: {args.report}")

    return 1 if result["status"] == "SITE_DRIFT" else 0


if __name__ == "__main__":
    sys.exit(main())
