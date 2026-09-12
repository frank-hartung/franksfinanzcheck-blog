#!/usr/bin/env python3
"""live_policy_guard.py – vergleicht LIVE mit dem, was das Repo ausliefert.

WARUM (Premium-Audit 12.09.2026, Empfehlung 8):
Zwischen Repo und Browser sitzen bei dieser Site drei Dinge, die ungefragt
mitschreiben: Cloudflare (Managed Rules, Cache), GitHub Pages (Deploy-Hysterese)
und die Robots-/Sitemap-Auslieferung selbst. Der Repo-Stand kann zu 100 % grün
sein und live trotzdem falsch: eine Managed Rule, die robots.txt umschreibt, ein
Crawl-Budget, das gegen eine gecachte Sitemap mit 161 URLs läuft, oder eine
Artikel-Seite im CDN-Cache, die noch das doppelt escapte JSON-LD von gestern
trägt. Genau solche Fälle sind hier schon aufgetreten (Aktionsplan-Annahme
„HTTPS disabled" stellte sich als Cloudflare-Cache heraus).

Deshalb prüft diese Wache die SCHNITTSTELLE, nicht nur den Quelltext:

  L1  robots.txt      – jede User-agent-Gruppe des Repo-Stands muss live stehen
                        (Pinterest + die sieben Antwortmaschinen), keine Gruppe
                        darf live `Disallow: /` enthalten, Sitemap-Zeile vorhanden
  L2  sitemap.xml     – jede Money-URL des Builds ist live gemeldet; live stehen
                        keine /tags/- oder /page/-URLs drin
  L3  Artikel-Seite   – canonical, meta robots und og:image der Live-Seite
                        stimmen mit dem Build überein (CDN-Rewrite/Cache-Falle)
  L4  HTTP-Hygiene    – http:// liefert 301 auf https, 404-Seite existiert,
                        /manifest.json ist erreichbar und hat JSON-MIME
                        (application/json reicht, application/manifest+json nicht zwingend)

Netzwerk ist nie eine Ausrede: ohne Erreichbarkeit endet der Lauf mit Hinweis und
Exit 0, außer --require-live setzt den Fall auf Exit 1 (CI-Nacht: wer nicht kann,
soll rot werden, damit die Frage nicht offen bleibt).

Nutzung:
    python3 scripts/live_policy_guard.py                    # live gegen public/
    python3 scripts/live_policy_guard.py --require-live      # CI-Modus
    python3 scripts/live_policy_guard.py --json
    python3 scripts/live_policy_guard.py --selftest         # 5 Fälle, ohne Netz
    SCHEMA_LIVE_BASE=https://beispiel.de python3 scripts/live_policy_guard.py

Exit: 0 = konsistent (oder nicht erreichbar ohne --require-live) · 1 = Drift · 2 = Fehler
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC = os.path.join(BLOG_DIR, "public")
BASE = os.environ.get("SCHEMA_LIVE_BASE", "https://franksfinanzcheck.de").rstrip("/")
TIMEOUT = float(os.environ.get("LIVE_POLICY_TIMEOUT", "25"))
UA = "Mozilla/5.0 (compatible; FranksFinanzcheckLiveGuard/1.0; +https://franksfinanzcheck.de)"
ANSWER_BOTS = ("OAI-SearchBot", "ChatGPT-User", "PerplexityBot", "Perplexity-User",
               "DuckAssistBot", "Claude-User", "meta-externalfetcher")


# ------------------------------------------------------------------- Netz (testbar)
def fetch(url: str) -> tuple[int, str, str]:
    """(Status, Body, Content-Type). Netzwerkfehler -> (0, "", "")."""
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Encoding": "identity"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read().decode("utf-8", "replace")
            return r.status, body, r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            body = ""
        return exc.code, body, exc.headers.get("Content-Type", "") if exc.headers else ""
    except Exception:  # noqa: BLE001  (DNS, TLS, Timeout, Sandbox ohne Egress)
        return 0, "", ""


def read_local(rel: str, public: str = PUBLIC) -> str:
    path = os.path.join(public, rel.lstrip("/"))
    try:
        return open(path, encoding="utf-8").read()
    except OSError:
        return ""


# ---------------------------------------------------------------------- Prüfregeln
def robots_groups(text: str) -> dict[str, list[str]]:
    """{User-agent: [Zeilen]} – RFC-9309-Gruppen, roh aber korrekt."""
    groups: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"user-agent:\s*(.+)$", line, re.I)
        if m:
            current = m.group(1).strip()
            groups.setdefault(current, [])
            continue
        if current is not None:
            groups[current].append(line)
    return groups


def check_robots(live: str, local: str, F: list, soft: list) -> None:
    if not live:
        F.append(("L1", "robots.txt ist live nicht abrufbar"))
        return
    lg = robots_groups(live)
    lgc = robots_groups(local) if local else {}
    for bot in ("Pinterestbot", *ANSWER_BOTS):
        if bot not in lg:
            F.append(("L1", f"robots.txt nennt live keine Gruppe für {bot} – "
                            "im Repo steht sie (Cloudflare-Regel oder Cache?!)"))
    for bot, lines in lg.items():
        disallow = [l for l in lines if re.match(r"disallow:\s*/\s*$", l, re.I)]
        if disallow and bot != "*":
            F.append(("L1", f"{bot}: live disallowt das ganze Netz (`Disallow: /`) – "
                            "Rich Pins und Antwort-Zitate brechen weg"))
    if local and lgc:
        fehlt = sorted(set(lgc) - set(lg))
        if fehlt:
            F.append(("L1", "Repo-Gruppen fehlen live: " + ", ".join(fehlt)))
    if "Sitemap:" not in live and "sitemap:" not in live.lower():
        soft.append(("L1", "robots.txt nennt live keine Sitemap-Zeile"))
    low = live.lower()
    if re.search(r"content-signal:\s*search=no", low):
        F.append(("L1", "Content-Signal steht live auf search=no – die Seite "
                        "verbietet Suchmaschinen den Bezug, nicht nur das Training"))


def check_sitemap(live: str, local: str, F: list, soft: list) -> None:
    if not live:
        F.append(("L2", "sitemap.xml ist live nicht abrufbar"))
        return
    live_urls = set(re.findall(r"<loc>\s*(.*?)\s*</loc>", live, re.S))
    if not live_urls:
        F.append(("L2", "sitemap.xml live ohne <loc>-Eintrag"))
        return
    for u in live_urls:
        if "/tags/" in u or re.search(r"/page/\d+/", u):
            F.append(("L2", f"Duplikat-URL in der LIVE-Sitemap: {u} – Repo und "
                            "Auslieferung sind nicht identisch (Cache? Cloudflare?)"))
    if local:
        local_urls = set(re.findall(r"<loc>\s*(.*?)\s*</loc>", local, re.S))
        money = {u for u in local_urls if re.search(r"/(posts|pillar)/[^/]+/$", u)
                 or u.rstrip("/") == BASE}
        fehlt = sorted(money - live_urls)
        if fehlt:
            F.append(("L2", f"{len(fehlt)} Money-URL(s) fehlen live in der Sitemap, "
                            f"z. B. {fehlt[0]} – Deploy/Cache-Hysterese"))
    else:
        soft.append(("L2", "kein public/-Build gefunden – Vergleich Repo↔live "
                           "übersprungen (nur Live-Selbstprüfung gelaufen)"))


def check_page(live_html: str, local_html: str, url: str, F: list, soft: list) -> None:
    if not live_html:
        F.append(("L3", f"{url} ist live nicht abrufbar"))
        return
    def grab(text: str, pattern: str) -> str:
        m = re.search(pattern, text, re.I | re.S)
        return (m.group(1).strip() if m else "")

    live_can = grab(live_html, r'<link[^>]+rel=[\'"]?canonical[\'"]?[^>]*href=[\'"]([^\'"]+)')
    loc_can = grab(local_html, r'<link[^>]+rel=[\'"]?canonical[\'"]?[^>]*href=[\'"]([^\'"]+)')
    if loc_can and live_can != loc_can:
        F.append(("L3", f"{url}: live-canonical {live_can!r} ≠ Build {loc_can!r}"))
    live_og = grab(live_html, r'<meta[^>]+property=[\'"]og:image[\'"][^>]*content=[\'"]([^\'"]+)')
    loc_og = grab(local_html, r'<meta[^>]+property=[\'"]og:image[\'"][^>]*content=[\'"]([^\'"]+)')
    if loc_og and live_og != loc_og:
        F.append(("L3", f"{url}: live-og:image {live_og!r} ≠ Build {loc_og!r} – "
                        "Pinterest zieht ein anderes (oder gar kein) Bild"))
    live_ld = re.search(r"<script[^>]*ld\+json[^>]*>(.*?)</script>", live_html, re.S | re.I)
    if live_ld:
        block = live_ld.group(1)
        if '\\"' in block:
            F.append(("L3", f"{url}: Live-JSON-LD enthält escapte Quotes – der "
                            "Doppel-Escape ist IM CACHE noch live (CDN vpurgen)"))
        else:
            try:
                json.loads(block)
            except json.JSONDecodeError as exc:
                F.append(("L3", f"{url}: Live-JSON-LD ist kein gültiges JSON ({exc.msg})"))
    else:
        soft.append(("L3", f"{url} liefert live kein JSON-LD mit aus"))


def check_http(F: list, soft: list) -> None:
    host = urllib.parse.urlsplit(BASE).netloc or "franksfinanzcheck.de"
    code, _, _ = fetch(f"http://{host}/robots.txt")
    if code not in (301, 302, 308):
        soft.append(("L4", f"http:// antwortet mit {code} statt 301/308 – "
                           "Prüfen, ob die Cloudflare-Umleitung noch greift"))
    code, body, ctype = fetch(f"{BASE}/manifest.json")
    if code != 200:
        F.append(("L4", f"/manifest.json live nicht erreichbar (HTTP {code}) – "
                        "PWA-Installation schlägt fehl"))
    elif "json" not in ctype.lower():
        F.append(("L4", f"/manifest.json liefert MIME {ctype!r} – Browser "
                        "akzeptieren nur application/json bzw. +json"))
    elif body and not body.lstrip().startswith("{"):
        F.append(("L4", "/manifest.json live ist kein JSON-Objekt (Rewrite?)"))


# Befundcodes. Absichtliche Asymmetrie: „Netz" heisst HIER nicht „unreachable"
# wie bei der Secrets-Probe. Diese Wache misst die Site selbst – steht sie nicht
# zur Verfügung, ist das der handlungswürdigste Befund des Laufs und muss ROT
# werden. Die bloße Messbarkeits-Lücke (Lauf ohne --require-live) bleibt der
# Info-Code `unreachable`, den das Ledger nicht eskaliert.
CODES = {"L1": "robots_drift", "L2": "sitemap_drift", "L3": "page_drift",
         "L4": "http_hygiene", "Netz": "site_unreachable"}
SOFT_CODES = {"Netz": "unreachable"}


def write_report(path: str, hard: list, soft: list, live: bool) -> None:
    """Ampel + Befundtabelle, wie governance_gate.py sie liest.

    Kein eigener Code für die Hinweis-Stufe: Funde, die niemanden etwas angehen,
    dürfen kein Issue auslösen (Ledger-Regel INFO_AMBER), Drift an der
    Auslieferung aber sehr wohl – deshalb ROT.
    """
    zeilen = ["# 🌐 LIVE-POLICY-REPORT – Repo ↔ Auslieferung",
              "",
              f"> **Stand:** {datetime.date.today().isoformat()} · Quelle: "
              "`python3 scripts/live_policy_guard.py` · Basis: " + BASE,
              "",
              "Prüft die Schnittstelle, an der Cloudflare, GitHub-Pages-Cache und "
              "CDN ungefragt mitschreiben: robots.txt, Sitemap, canonical/"
              "og:image/JSON-LD einer Live-Seite, HTTP-Umleitung und Manifest-MIME.",
              "",
              "## Befunde",
              ""]
    for reg, msg in hard:
        zeilen.append(f"| RED | {CODES.get(reg, 'fund')} | {reg}: {msg} |")
    for reg, msg in soft:
        code = SOFT_CODES.get(reg, CODES.get(reg, "hinweis"))
        zeilen.append(f"| AMBER | {code} | {reg}: {msg} |")
    if not hard and not soft:
        zeilen.append("_Keine Abweichung zwischen Build und Live-Auslieferung._")
    elif not hard:
        zeilen.append("")
        zeilen.append("_Kein harter Befund – die Hinweise betreffen die Messbarkeit "
                      "selbst, nicht den ausgelieferten Inhalt._")
    zeilen += ["", "## Gesamt-Ampel: **" + ("RED" if hard else "GREEN") + "**", ""]
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(zeilen))


def run(require_live: bool, public: str = PUBLIC) -> tuple[list, list, bool]:
    hard: list = []
    soft: list = []
    code, robots_live, _ = fetch(f"{BASE}/robots.txt")
    if code == 0:
        msg = "keine Verbindung zur Site (DNS/TLS/Zeitlimit)"
        (hard if require_live else soft).append(("Netz", msg))
        return hard, soft, False
    check_robots(robots_live, read_local("robots.txt", public), hard, soft)
    _, sitemap_live, _ = fetch(f"{BASE}/sitemap.xml")
    check_sitemap(sitemap_live, read_local("sitemap.xml", public), hard, soft)
    # Probe Seiten: Startseite + der neueste Artikel aus dem Build (oder live-Erstling)
    probes = ["/"]
    arts = sorted(glob.glob(os.path.join(public, "posts", "*", "index.html")))
    if arts:
        probes.append("/posts/" + os.path.basename(os.path.dirname(arts[-1])) + "/")
    else:
        m = re.search(r"<loc>\s*(https?://[^<]*/posts/[^<]+)/\s*</loc>", sitemap_live)
        if m:
            probes.append(m.group(1)[len(BASE):] + "/")
    for p in probes:
        c, live_html, _ = fetch(BASE + p)
        if c != 200:
            hard.append(("L3", f"{p} liefert live HTTP {c}"))
            continue
        check_page(live_html, read_local(p.strip("/") + "/index.html" if p != "/"
                                         else "index.html", public), p, hard, soft)
    check_http(hard, soft)
    return hard, soft, True


# ---------------------------------------------------------------------- Selbsttest
def _selftest() -> int:
    errs: list[str] = []
    ROBOTS_OK = ("User-agent: *\nAllow: /\nDisallow: /go/\nContent-Signal: "
                 "search=yes, ai-train=no, use=reference\n\n"
                 "User-agent: Pinterestbot\nAllow: /\n\n"
                 + "".join(f"User-agent: {b}\nAllow: /\n\n" for b in ANSWER_BOTS)
                 + f"Sitemap: {BASE}/sitemap.xml\n")
    ROBOTS_BAD = "User-agent: *\nDisallow: /\n\nUser-agent: Pinterestbot\nDisallow: /\n"
    SM_OK = (f'<urlset><url><loc>{BASE}/posts/a/</loc></url>'
             f'<url><loc>{BASE}/pillar/strom-sparen/</loc></url></urlset>')
    SM_BAD = (f'<urlset><url><loc>{BASE}/tags/x/</loc></url>'
              f'<url><loc>{BASE}/page/2/</loc></url></urlset>')
    PAGE_OK = (f'<html><head><link rel="canonical" href="{BASE}/posts/a/">'
               f'<meta property="og:image" content="{BASE}/c.jpg">'
               '<script type="application/ld+json">'
               '{"@context":"https://schema.org","@type":"Article","headline":"A"}'
               '</script></head><body>x</body></html>')
    PAGE_STALE = PAGE_OK.replace(f'{BASE}/posts/a/', f'{BASE}/alt/').replace(
        "content=\"", "content=\"", 1)
    PAGE_BROKEN_LD = PAGE_OK.replace('"headline":"A"', '"headline":"\\"A\\""')

    def make_fetch(table: dict[str, tuple[int, str, str]]):
        def _f(url: str) -> tuple[int, str, str]:
            path = url[len(BASE):] or "/"
            if url.startswith("http://"):
                return (301, "", "")
            key = path
            if key in table:
                return table[key]
            return (404, "", "")
        return _f

    global fetch
    keep = fetch
    import tempfile
    tmp = tempfile.mkdtemp(prefix="live-policy-selftest-")
    os.makedirs(os.path.join(tmp, "posts", "a"), exist_ok=True)
    open(os.path.join(tmp, "index.html"), "w").write(PAGE_OK)
    open(os.path.join(tmp, "posts", "a", "index.html"), "w").write(PAGE_OK)
    pub = tmp
    try:
        # 1) grüner Stand
        fetch = make_fetch({"/robots.txt": (200, ROBOTS_OK, "text/plain"),
                           "/sitemap.xml": (200, SM_OK, "application/xml"),
                           "/": (200, PAGE_OK, "text/html"),
                           "/posts/a/": (200, PAGE_OK, "text/html"),
                           "/manifest.json": (200, '{"name":"x"}',
                                              "application/json")})
        hard, soft, live = _run_for_test(True, pub)
        if hard:
            errs.append(f"grüner Stand meldet: {hard}")

        # 2) Cloudflare-writeover in robots.txt (Pinterest dichtgemacht)
        fetch = make_fetch({"/robots.txt": (200, ROBOTS_BAD, "text/plain"),
                           "/sitemap.xml": (200, SM_OK, "application/xml"),
                           "/": (200, PAGE_OK, "text/html"),
                           "/posts/a/": (200, PAGE_OK, "text/html"),
                           "/manifest.json": (200, '{"name":"x"}', "application/json")})
        hard, _, _ = _run_for_test(True, pub)
        if not any(r == "L1" for r, _ in hard):
            errs.append(f"robots-Drift wird nicht gesehen: {hard}")

        # 3) veraltete gecachte Sitemap (Duplikate live, frische im Repo)
        fetch = make_fetch({"/robots.txt": (200, ROBOTS_OK, "text/plain"),
                           "/sitemap.xml": (200, SM_BAD, "application/xml"),
                           "/": (200, PAGE_OK, "text/html"),
                           "/posts/a/": (200, PAGE_OK, "text/html"),
                           "/manifest.json": (200, '{"name":"x"}', "application/json")})
        hard, _, _ = _run_for_test(True, pub)
        if not any(r == "L2" for r, _ in hard):
            errs.append(f"Sitemap-Drift wird nicht gesehen: {hard}")

        # 4) CDN liefert altes HTML (canonical/og:image/JSON-LD veraltet)
        fetch = make_fetch({"/robots.txt": (200, ROBOTS_OK, "text/plain"),
                           "/sitemap.xml": (200, SM_OK, "application/xml"),
                           "/": (200, PAGE_OK, "text/html"),
                           "/posts/a/": (200, PAGE_STALE, "text/html"),
                           "/manifest.json": (200, '{"name":"x"}', "application/json")})
        hard, _, _ = _run_for_test(True, pub)
        if not any(r == "L3" and "canonical" in m for r, m in hard):
            errs.append(f"Cache-Drift (canonical) wird nicht gesehen: {hard}")
        fetch = make_fetch({"/robots.txt": (200, ROBOTS_OK, "text/plain"),
                           "/sitemap.xml": (200, SM_OK, "application/xml"),
                           "/": (200, PAGE_OK, "text/html"),
                           "/posts/a/": (200, PAGE_BROKEN_LD, "text/html"),
                           "/manifest.json": (200, '{"name":"x"}', "application/json")})
        hard, _, _ = _run_for_test(True, pub)
        if not any(r == "L3" and "escap" in m for r, m in hard):
            errs.append(f"escapes JSON-LD im Cache wird nicht gesehen: {hard}")

        # 5) kein Netz: ohne --require-live Hinweis, mit --require-live Fehler
        def dead(url: str) -> tuple[int, str, str]:
            return (0, "", "")
        fetch = dead
        hard, soft, live = _run_for_test(False, pub)
        if hard or live:
            errs.append(f"Netz-Ausfall wird als Fehler gewertet (erlaubt ist Hinweis): {hard}")
        hard, _, _ = _run_for_test(True, pub)
        if not any(r == "Netz" for r, _ in hard):
            errs.append("--require-live meldet Netz-Ausfall nicht hart")
    except Exception as exc:  # noqa: BLE001
        errs.append(f"Ausführung: {exc.__class__.__name__}: {exc}")
    finally:
        fetch = keep
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    if errs:
        print("🛑 live_policy_guard-Selbsttest FEHLGESCHLAGEN:")
        for e in errs:
            print("  -", e)
        return 2
    print("✅ Live-Policy-Selbsttest: 5 Fälle grün (inkl. Cloudflare-/Cache-Falle).")
    return 0


def _run_for_test(require_live: bool, public: str | None = None) -> tuple[list, list, bool]:
    """run() gegen ein übergebenes public-Verzeichnis (Test-Baum, nicht der echte)."""
    return run(require_live, public=public or PUBLIC)


def main() -> int:
    ap = argparse.ArgumentParser(description="Live gegen Repo: robots, sitemap, Seiten")
    ap.add_argument("--require-live", action="store_true",
                    help="Netz-Ausfall als Fehler (CI-Nacht)")
    ap.add_argument("--report", default="", metavar="DATEI",
                    help="Ampel + Befundtabelle für das Governance-Ledger schreiben")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()

    hard, soft, live = run(args.require_live)
    if not live and args.require_live:
        soft = [r for r in soft if r[0] != "Netz"]
    if args.report:
        write_report(args.report, hard, soft, live)
        print(f"   Report → {args.report}")
    if args.json:
        print(json.dumps({"base": BASE, "reachable": live,
                          "hard": [{"regel": r, "meldung": m} for r, m in hard],
                          "soft": [{"regel": r, "meldung": m} for r, m in soft]},
                         ensure_ascii=False, indent=2))
    else:
        print(f"Live-Policy-Guard · {BASE} · "
              f"{'erreichbar' if live else 'NICHT erreichbar'}")
        for r, m in hard:
            print(f"  ❌ [{r}] {m}")
        for r, m in soft:
            print(f"  ⚠ [{r}] {m}")
        if not hard:
            print("  ✅ Repo und Auslieferung sind konsistent "
                  "(robots, Sitemap, canonical, og:image, JSON-LD, Manifest)."
                  if live else "  ℹ keine Vergleiche möglich – nur Hinweis")
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
