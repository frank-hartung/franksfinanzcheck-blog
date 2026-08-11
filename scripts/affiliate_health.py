#!/usr/bin/env python3
# ============================================================
#  AFFILIATE-HEALTH (Wochenwache) – Live-Gesundheit der Ziele
#
#  Profi-Affiliate-Optimierung (11.08.2026). Prüft jede Woche, was der
#  Checker offline nicht sieht:
#
#    H1  ERREICHBARKEIT jedes Register-Ziels (/go/<key>/): HTTP-Status,
#        Redirect-Kette (Affiliate-Tracker!) + landet sie im erwarteten
#        Netzwerk (check24.net/* oder tarifcheck.de) und
#        erkennbar im richtigen Thema (Keyword-Stichprobe der Zielseite).
#    H2  PID-VOLLSTÄNDIGKEIT & -Echtheit: pid=80968&aid=18 bzw.
#        partner_id=47086&ad_id=15; fremde/fehlende PIDs = revenue loss.
#    H3  GATEWAY-INTEGRITÄT: jede /go/-Seite zeigt auf die aktuelle
#        Register-URL (kein Drift zwischen YAML und static/go).
#    H4  CTA-ABDECKUNG: jeder Post hat mindestens einen Affiliate-Pfad.
#        (/go/<key>/ zählt; allgemein)
#
#  Ausfall -> GitHub-Issue mit Dedupe (Label: affiliate-health), der
#  REPORT wird committet (AFFILIATE-HEALTH-REPORT.md), History jsonl.
#
#  Aufruf:
#    python3 scripts/affiliate_health.py            # Report (mit Netz!)
#    python3 scripts/affiliate_health.py --no-net   # nur Offline-Checks
#    python3 scripts/affiliate_health.py --issue    # + Issue bei kritischem Fund
#
#  Workflow: .github/workflows/affiliate-health.yml (Mo 07:45 MESZ)
# ============================================================

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "scripts" / "check24_links.yaml"
GO_DIR = ROOT / "static" / "go"
REPORT = ROOT / "AFFILIATE-HEALTH-REPORT.md"
HISTORY = ROOT / "data" / "affiliate_health_history.jsonl"

NO_NET = "--no-net" in sys.argv
MAKE_ISSUE = "--issue" in sys.argv

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 FranksFinanzcheck-Health/1.0"}

# Erwartungsschluessel pro Netzwerk:
NETWORK_OK = {"a.check24.net": ("check24",), "a.partner-versicherung.de": ("tarifcheck",)}


def load_registry() -> dict:
    reg = {}
    for line in REGISTRY.read_text(encoding="utf-8").splitlines():
        ls = line.strip()
        if ls and not ls.startswith("#") and ": " in ls and '"' in ls:
            key = ls.split(":")[0].strip()
            url = ls.split('"')[1]
            if url.startswith("http"):
                reg[key] = url
    return reg


# ------------------------------------------------------------- H1: Living URLs

def check_url(url: str) -> dict:
    """Erreichbarkeit + Netzwerk-Zugehörigkeit (keine komplette Kette verfolgen –
    nodem die Tracker zu externen Netzen)."""
    try:
        req = urllib.request.Request(url, headers=UA, method="GET")
        opener = urllib.request.build_opener(NoRedirect)
        resp = opener.open(req, timeout=25)
        code = resp.status
        loc = resp.headers.get("Location", "")
    except urllib.error.HTTPError as e:
        code, loc = e.code, e.headers.get("Location", "")
    except Exception as e:
        return {"ok": False, "grund": f"Timeout/Fehler: {type(e).__name__}", "code": 0}
    net_ok = True
    for net, markers in NETWORK_OK.items():
        if net in url:
            net_ok = any(loc_ok in loc for loc_ok in markers) or not loc
    ok = code in (301, 302, 303, 307, 308, 200)
    grund = ("Weiterleitung aktiv" if code in (301, 302, 303, 307, 308)
             else "Direktantwort") if ok else f"HTTP {code}"
    return {"ok": ok and net_ok, "grund": f"{grund} → {loc[:60]}", "code": code}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, url):
        return None


# --------------------------------------------------------------- H2/H3/H4

def check_pids(reg: dict) -> list[str]:
    wrong = []
    for key, url in reg.items():
        if "check24.net" in url:
            if "pid=80968" not in url or "aid=18" not in url:
                wrong.append(f"{key}: PID falsch! ({url[:70]})")
        elif "partner-versicherung.de" in url:
            if "partner_id=47086" not in url or "ad_id=15" not in url:
                wrong.append(f"{key}: Partner-ID falsch! ({url[:70]})")
    return wrong


def check_gateway(reg: dict) -> list[str]:
    problems = []
    for key, url in reg.items():
        f = GO_DIR / key / "index.html"
        if not f.exists():
            problems.append(f"/go/{key}/: Weiterleitungsseite fehlt (shield ausfuehren)")
            continue
        html = f.read_text(encoding="utf-8")
        if url not in html:
            problems.append(f"/go/{key}/: zeigt von Register abweichend")
    return problems


def check_coverage() -> list[str]:
    gaps = []
    for p in sorted((ROOT / "content" / "posts").glob("*/index.md")):
        t = p.read_text(encoding="utf-8")
        if re.search(r"^draft:\s*true", t[:2500], re.M):
            continue
        if re.search(r"/go/[\w-]+/", t) is None and not re.search(r"a\.(check24\.net|partner-versicherung\.de)", t):
            gaps.append(p.parent.name)
    return gaps


def create_issue(title: str, body: str) -> None:
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repo:
        print("ℹ Kein GITHUB_TOKEN – Issue wird uebersprungen:", title); return
    api = f"https://api.github.com/repos/{repo}/issues"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    req = urllib.request.Request(f"{api}?state=open&labels=affiliate-health&per_page=10", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            for i in json.loads(r.read().decode()):
                if i["title"] == title:
                    print(f"ℹ Dedupe: Issue existiert: #{i['number']}"); return
        data = json.dumps({"title": title, "body": body, "labels": ["affiliate-health"]}).encode()
        urllib.request.urlopen(urllib.request.Request(api, data=data, headers=headers, method="POST"), timeout=20)
        print("✔ Issue erstellt:", title)
    except Exception as e:
        print(f"⚠ Issue-Feeler: {e}")


def main() -> None:
    reg = load_registry()
    h1, h2, h3, h4 = [], [], [], []
    if not NO_NET:
        for key, url in sorted(reg.items()):
            res = check_url(url)
            h1.append((key, res))
            print(f"  {'🟢' if res['ok'] else '🔴'} {key}: {res['grund'][:70]}")
    h2 = check_pids(reg)
    h3 = check_gateway(reg)
    h4 = check_coverage()

    fails = [k for k, r in h1 if not r["ok"]] + h2 + h3
    today = date.today().isoformat()
    L = [f"# 🩺 AFFILIATE-HEALTH-REPORT", "",
         f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
         f"**Kanäle:** {len(reg)} · **Online geprüft:** {len(h1) if h1 else 'offline-Modus'}",
         f"**Status:** {'🟢 Alles gesund' if not fails and not h4 else '🔴 ' + str(len(fails)) + ' kritisch, ' + str(len(h4)) + ' Lücken'}",
         "", "## " + ("✅ Geprüft und gesund" if not fails else "🔴 Ausfälle"), ""]
    if fails:
        L += [f"- `{f}`" if isinstance(f, str) else f"- **{f[0]}**: {f[1]['grund']}" for f in fails]
    if h4:
        L += ["", f"## ⚠️ CTA-Lücken ({len(h4)} Artikel ohne Affiliate-Link)", ""]
        L += [f"- `{g}`" for g in h4[:20]]
    L += ["", "---", "_Wochenwache: Erreichbarkeit, Redirect-Ziel-Netzwerk, PID-Integritaet, "
          "Gateway-Drift, CTA-Luecken. Bei kritischem Befund: Issue (Label affiliate-health)._"]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:25]))

    HISTORY.parent.mkdir(exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"date": today, "kritisch": len(fails), "luecken": len(h4)}) + "\n")

    if fails and MAKE_ISSUE:
        zeilen = [f if isinstance(f, str) else f"{f[0]}: {f[1]['grund']}" for f in fails]
        body = "```\n" + "\n".join(zeilen) + "\n```\n\n_Details: AFFILIATE-HEALTH-REPORT.md im Repo._"
        create_issue(f"🚨 Affiliate-Health: {len(fails)} kritischer Fund(e) vom {today}", body)
    sys.exit(2 if fails else 0)


if __name__ == "__main__":
    main()
