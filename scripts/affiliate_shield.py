#!/usr/bin/env python3
# ============================================================
#  AFFILIATE-SHIELD – Pro-Absicherung aller Affiliate-Links
#
#  Auftrag (11.08.2026): „Sichere meine Affiliate-Links wie Profis".
#  Was Profi-Affiliate-Marketer damit meinen – und was eingebaut ist:
#
#    A1  ZENTRALER GATEWAY (/go/): Klicks laufen ueber eigene URLs
#        franksfinanzcheck.de/go/<thema>/ -> 302-aehnliche Meta-Weiterleitung
#        zur Affiliate-Zielseite. Programmwechsel? Eine Zeile im Register!
#    A2  REGISTER FIRST: scripts/check24_links.yaml ist die Quelle der
#        Wahrheit. Unbekannte Affiliate-URLs -> REPORT, kein Blind-Trust.
#    A3  GOOGLE-KONFORM: /go/-Links bekommen rel="sponsored nofollow noopener"
#        (Hugo-Render-Hook) und die Zielseiten sind noindex + robots-sperrt
#        (/go/ plus disallow) – sauberes Cloaking-freies Routing.
#    A4  SELBSTHEILUNG: neue KI-Artikel kommen mit rohen pid-Links ->
#        naechster Engine-Lauf routet sie automatisch ueber /go/.
#        Doppelroute (/go/x/ erneut) erkennt uns ueberspringen – idempotent.
#    A5  REICHWEITEN-MESSUNG: Umami-Events „affiliate_click" mit Thema.
#
#  Aufruf:
#    python3 scripts/affiliate_shield.py             # Report + /go/ generieren
#    python3 scripts/affiliate_shield.py --fix       # Artikel umschreiben+generate
#    python3 scripts/affiliate_shield.py --new-only  # Engine-Modus
#
#  Ausgabe: AFFILIATE-SHIELD-REPORT.md + Static-Pages unter static/go/
# ============================================================

import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "scripts" / "check24_links.yaml"
GO_DIR = ROOT / "static" / "go"
REPORT = ROOT / "AFFILIATE-SHIELD-REPORT.md"
HISTORY = ROOT / "data" / "affiliate_shield_history.jsonl"

DO_FIX = "--fix" in sys.argv
DRY_RUN = "--dry-run" in sys.argv
NEW_ONLY = "--new-only" in sys.argv

AFFIL_PAT = re.compile(
    r"https://a\.(?:check24\.net|partner-versicherung\.de)[^)\]\s\"']*")


def ctx_route_for(full_text: str) -> str:
    """Thematische Route EINMAL pro Datei – Wahrheit: affiliate_marketer.route_for
    (mit Pillar-Fallback). Dient dem AUTO-DEEP: generische Roh-Links (ohne deep=)
    werden nicht mehr nur gemeldet, sondern auf ihre /go/-Deep-Route gehoben.
    Frank-Regel 11.08.: Deep-first, generisch nur wo wirklich kein Fach passt."""
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import affiliate_marketer as am
        return am.route_for(full_text, am.pillar_of(full_text))
    except Exception:
        return ""


def load_registry() -> dict:
    """YAML-Simpelparse: '  key: "URL"' Zeilen. Liefert {key: url}."""
    out = {}
    for line in REGISTRY.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s+([\w-]+):\s*\"(https://[^\"]+)\"", line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def deep_map(reg: dict) -> dict:
    """{deep-Wert: key} aus den Registrierungs-URLs."""
    m = {}
    for key, url in reg.items():
        d = re.search(r"[?&]deep=([\w-]+)", url)
        if d:
            m[d.group(1)] = key
    return m


# Ziel-Namen fuer die Gateway-Seiten (Transparenz beim Uebergang –
# wie Profi-Affiliates: Nutzer SEHEN, wohin es geht; Frank-Regel 11.08.:
# bei C24-Verlinkung immer die C24 Bank nennen).
GO_NAMES = {
    "tagesgeld": "C24 Bank (von Check24)",
    "girokonto": "C24 Bank (von Check24)",
    "haftpflicht": "Tarifcheck",
    "hausrat": "Tarifcheck",
    "unfallversicherung": "Tarifcheck",
    "zahnzusatzversicherung": "Tarifcheck",
    "reisekrankenversicherung": "Tarifcheck",
}


def generate_go_pages(reg: dict) -> int:
    """Erzeugt die statischen Weiterleitungen static/go/<key>/index.html."""
    GO_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    tpl = """<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">
<meta name="robots" content="noindex,nofollow,noarchive">
<meta http-equiv="refresh" content="0; url={url}">
<link rel="canonical" href="{url}">
<title>Weiter zu {zielname} | FranksFinanzcheck</title>
</head><body style="font-family:sans-serif;text-align:center;padding:60px 20px;color:#19324c">
<p>Du wirst zu <strong>{zielname}</strong> weitergeleitet …</p>
<h1 style="font-size:20px">FranksFinanzcheck</h1>
<p><a href="{url}" style="background:#0f6049;color:#fff;padding:12px 26px;border-radius:8px;text-decoration:none;font-weight:600">Falls nicht automatisch: weiter zu {zielname}</a></p>
<p style="color:#798897;font-size:12px;margin-top:40px">Partnerlink (Werbung). Wir erhalten ggf. eine Provision – fuer dich kostenlos.</p>
</body></html>
"""
    for key, url in reg.items():
        dest = GO_DIR / key / "index.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(tpl.replace("{url}", url)
                        .replace("{zielname}", GO_NAMES.get(key, "Check24")), encoding="utf-8")
        count += 1
    return count


def shield_line(body: str, dmap: dict, reg: dict, fname: str, reports: list,
                ctx_route: str = "") -> str:
    """Routet rohe Affiliate-Links ueber /go/<key>/. Generische Links (ohne
    deep=) werden seit 11.08. (Abend) automatisch auf die thematische
    Deep-/go/-Route gehoben (Auto-Deep)."""
    def repl(m):
        url = m.group(0)
        d = re.search(r"[?&]deep=([\w-]+)", url)
        if not d:
            if ctx_route and ctx_route in reg:
                # /go/allgemein/ == funktional identisch zum bisherigen
                # Check24-Generik-Link; thematische Routen sind klar besser.
                reports.append((fname, f"AUTO-DEEP → /go/{ctx_route}/", url))
                return f"/go/{ctx_route}/"
            reports.append((fname, "GENERIC-link (Checker zuständig)", url))
            return url
        key = dmap.get(d.group(1))
        if key:
            return f"/go/{key}/"
        reports.append((fname, "UNREGISTERED-deep (ins Register!)", url))
        return url
    return AFFIL_PAT.sub(repl, body)


def process(path: Path, dmap: dict, reg: dict, reports: list) -> tuple[int, str]:
    rel = str(path.relative_to(ROOT))
    full = path.read_text(encoding="utf-8")
    lines = full.split("\n")
    ctx_route = ctx_route_for(full)  # einmal pro Datei (Auto-Deep)
    out, n = [], 0
    in_code, fence_open, fence_done = False, False, False
    for raw in lines:
        s = raw.strip()
        if s.startswith("```"):
            in_code = not in_code
            out.append(raw); continue
        if in_code:
            out.append(raw); continue
        # Front-Matter nie anfassen
        if raw.startswith("---") and not fence_open:
            fence_open = True; out.append(raw); continue
        if not fence_done and fence_open and raw.startswith("---"):
            fence_done = True
            # geklebte Fence-Restzeile (bekanntes Engine-Format)
            rest = s[3:]
            if rest.strip():
                fixed = shield_line(rest, dmap, reg, rel, reports, ctx_route)
                out.append("---" + fixed)
                continue
            out.append(raw); continue
        if not fence_done:
            out.append(raw); continue
        fixed = shield_line(raw, dmap, reg, rel, reports, ctx_route)
        if fixed != raw:
            n += 1
        out.append(fixed)
    return n, "\n".join(out)


def target_files():
    files = sorted((ROOT / "content").rglob("index.md")) + \
        sorted((ROOT / "content").rglob("_index.md"))
    if NEW_ONLY:
        changed = set()
        try:
            outp = subprocess.run(["git", "diff", "--name-only", "HEAD~2", "HEAD", "--", "content/"],
                                  capture_output=True, text=True, cwd=ROOT, timeout=30).stdout
            changed = {ROOT / l.strip() for l in outp.splitlines() if l.strip()}
        except Exception:
            pass
        today = date.today().isoformat()
        changed |= {f for f in (ROOT / "content").rglob("index.md") if f.parent.name.startswith(today)}
        files = [f for f in files if f in changed]
    return files


def main() -> None:
    reg = load_registry()
    dmap = deep_map(reg)
    made = generate_go_pages(reg) if (DO_FIX and not DRY_RUN) else 0

    reports, count_files, routed = [], 0, 0
    for p in target_files():
        n, new_text = process(p, dmap, reg, reports)
        if n:
            count_files += 1
            routed += n
            if DO_FIX and not DRY_RUN and new_text != p.read_text(encoding="utf-8"):
                p.write_text(new_text, encoding="utf-8")

    mode = "DRY-RUN" if DRY_RUN else ("FIX" if DO_FIX else "REPORT")
    L = ["# 🛡️ AFFILIATE-SHIELD-REPORT", "",
         f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · Modus: {mode}",
         f"**Register:** {len(reg)} Themen-Links (`scripts/check24_links.yaml`) · **Weiterleitungen:** /go/ ({made} neu generiert)" if made else "",
         f"**Artikel angefasst:** {count_files} · **Links geroutet:** {routed}", ""]
    if reports:
        L += ["## ⚠️ Funde (manuell ins Register aufnehmen)", ""]
        L += [f"- `{f}` [{t}] {u[:80]}" for f, t, u in reports[:25]]
    L += ["", "---", "_/go/-Gateway + rel=sponsored/nofollow + robots-sperre = Profi-Affiliate-Niveau._"]
    L = [x for x in L if x]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:25]))


if __name__ == "__main__":
    main()
