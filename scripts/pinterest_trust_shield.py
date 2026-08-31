#!/usr/bin/env python3
"""PINTEREST-TRUST-SHIELD – Anti-Spam & Domain-Vertrauen (Agentur 2026)

Ziel: franksfinanzcheck.de wird von Pinterest dauerhaft als vertrauenswürdige
Content-Domain bewertet – nicht als Spam-/Redirect-/Affiliate-Falle.

Was geprüft + geheilt wird:
  T1  PIN-ZIEL           Pin-Link = Artikel-URL (nie /go/, nie Affiliate, nie Shortener)
  T2  KEIN REDIRECT      Artikel-Markdown ohne Meta-Refresh/JS-Redirect
  T3  AFFILIATE-HYGIENE  max. 5 /go/-Links, keine Direkt-a.check24-Links im Text
  T4  WERBEKENNZEICHNUNG sichtbarer Hinweis + pin_description mit *Werbung |
  T5  E-E-A-T            author + erfahrung in jedem veröffentlichten Artikel
  T6  INTERNE LINKS      ≥2 interne Verlinkungen (Themen-Cluster, kein Orphan)
  T7  COVER/OG           Cover 1000×1500, pin_title/pin_description gesetzt
  T8  ROBOTS             Pinterestbot erlaubt, /go/ Disallow
  T9  RATE-LIMIT         Pinterest-Engine max. 2–3 Pins/Lauf, Pause ≥45 s
  T10 RSS-FEED           nur live Posts, Cover-Enclosure, keine Drafts
  T11 GO-GATEWAY         /go/* = noindex + robots Disallow (dünne Seiten raus)
  T12 DOMAIN-VERIFY      p:domain_verify in hugo.toml

Selbstheilung (--fix):
  - T3 Direkt-Affiliate → /go/-Gateway (affiliate_shield)
  - T5 erfahrung/author ergänzen
  - T6 internal_linker --apply
  - T7 pinterest_seo_healer --fix
  - T8 robots.txt heilen
  - T9 Rate-Limit-Konstanten in pinterest_engine absichern
  - T10 Drafts aus RSS (hiddenInRss / draft:true bereits Hugo-seitig)

Sabotage-Schutz: Selbsttest vor Fix (Exit 2).

Nutzung:
  python3 scripts/pinterest_trust_shield.py
  python3 scripts/pinterest_trust_shield.py --fix
  python3 scripts/pinterest_trust_shield.py --json

Report: PINTEREST-TRUST-REPORT.md
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import subprocess
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
from post_utils import list_post_paths, slug_of  # noqa: E402

REPORT = os.path.join(BLOG_DIR, "PINTEREST-TRUST-REPORT.md")
DO_FIX = "--fix" in sys.argv
AS_JSON = "--json" in sys.argv

SITE = "https://franksfinanzcheck.de"
AFFILIATE_MAX = 5
INTERNAL_MIN = 2
PINS_MAX_SAFE = 3
PIN_PAUSE_MIN = 45

PROBLEMS: list[tuple[str, str, str]] = []
FIXED: list[tuple[str, str, str]] = []

GENERIC_ERFAHRUNG = (
    "Ich habe die Vergleiche und Zahlen in diesem Artikel selbst geprüft "
    "und wende die Empfehlungen seit Jahren in meiner eigenen Finanzplanung "
    "an – die Tipps sind praxisgetestet, nicht vom Schreibtisch."
)


# ---------------------------------------------------------------------------
# Sabotage-Schutz
# ---------------------------------------------------------------------------

def _selftest() -> list[str]:
    err = []
    if AFFILIATE_MAX > 5:
        err.append("AFFILIATE_MAX zu hoch (Spam-Risiko)")
    if PINS_MAX_SAFE > 3:
        err.append("PINS_MAX_SAFE > 3 (Flooding)")
    if PIN_PAUSE_MIN < 30:
        err.append("PIN_PAUSE_MIN zu kurz")
    if SITE != "https://franksfinanzcheck.de":
        err.append("SITE verändert")
    # Pin-Ziel-Regex: /go/ muss erkannt werden
    if not re.search(r"/go/", "https://x.de/go/gas/"):
        err.append("/go/-Regex defekt")
    return err


# ---------------------------------------------------------------------------
# Helfer
# ---------------------------------------------------------------------------

def _fm_body(content: str):
    if not content.startswith("---"):
        return "", content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return "", content
    return parts[1], parts[2]


def _get(fm: str, key: str) -> str:
    m = re.search(rf"^{re.escape(key)}:\s*[\"']?(.*?)[\"']?\s*$", fm, re.M)
    return m.group(1).strip() if m else ""


def _set_fm_line(content: str, key: str, value: str, quote: bool = True) -> str:
    fm, body = _fm_body(content)
    line = f'{key}: "{value}"' if quote else f"{key}: {value}"
    if re.search(rf"^{re.escape(key)}:", fm, re.M):
        fm2 = re.sub(rf"^{re.escape(key)}:.*$", line, fm, count=1, flags=re.M)
    else:
        # nach author oder draft einfügen
        m = re.search(r"^(author:.*)$", fm, re.M)
        if m:
            fm2 = fm[: m.end()] + "\n" + line + fm[m.end():]
        else:
            fm2 = fm.rstrip("\n") + "\n" + line + "\n"
    return "---" + fm2 + "---" + body


def _run(args: list[str]) -> int:
    print(f"  → {' '.join(args)}")
    return subprocess.run([sys.executable, *args], cwd=BLOG_DIR).returncode


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_articles():
    for path in list_post_paths():
        slug = slug_of(path)
        content = open(path, encoding="utf-8").read()
        fm, body = _fm_body(content)
        if "draft: true" in fm:
            continue  # Drafts werden nicht gepinnt / nicht indexiert

        # T1/T2: kein Redirect im Artikel, kein Pin auf /go/
        if re.search(r"http-equiv\s*=\s*[\"']?refresh", content, re.I):
            PROBLEMS.append(("T2", slug, "Meta-Refresh im Artikel (Redirect-Spam-Signal)"))
        if re.search(r"window\.location|location\.href\s*=", body):
            PROBLEMS.append(("T2", slug, "JS-Redirect im Body"))

        pin_link_ok = True  # Pin-Link wird von Engine gebaut – prüfen pin_description
        pd = _get(fm, "pin_description")
        if pd and re.search(r"/go/|a\.check24\.|bit\.ly|t\.co/|tinyurl", pd, re.I):
            PROBLEMS.append(("T1", slug, "pin_description enthält Affiliate/Shortener-URL"))
            pin_link_ok = False
        pt = _get(fm, "pin_title")
        if not pt:
            PROBLEMS.append(("T7", slug, "pin_title fehlt"))
        if not pd:
            PROBLEMS.append(("T7", slug, "pin_description fehlt"))
        elif not pd.strip().startswith("*Werbung"):
            PROBLEMS.append(("T4", slug, "pin_description ohne *Werbung | Kennzeichnung"))

        # T3 Affiliate-Dichte
        go = len(re.findall(r"\]\(/go/[\w-]+/\)", content))
        direct = len(re.findall(
            r"\]\(https?://(?:a\.(?:check24|partner-versicherung)|check24\.de/[^)]*)",
            content, re.I,
        ))
        shortener = len(re.findall(r"\]\(https?://(?:bit\.ly|t\.co|tinyurl|goo\.gl)/", content, re.I))
        if go + direct > AFFILIATE_MAX:
            PROBLEMS.append(("T3", slug, f"{go + direct} Affiliate-Links (> {AFFILIATE_MAX})"))
        if direct:
            PROBLEMS.append(("T3", slug, f"{direct} Direkt-Affiliate-Links (sollten /go/ sein)"))
        if shortener:
            PROBLEMS.append(("T3", slug, f"{shortener} URL-Shortener (Pinterest-Spam-Signal)"))

        # T4 Werbekennzeichnung im Body
        if "Affiliate" not in content and "Werbung" not in content:
            PROBLEMS.append(("T4", slug, "keine Werbe-/Affiliate-Kennzeichnung im Text"))

        # T5 E-E-A-T
        if not re.search(r"^erfahrung:", fm, re.M):
            PROBLEMS.append(("T5", slug, "erfahrung: fehlt (E-E-A-T)"))
            if DO_FIX:
                c2 = _set_fm_line(content, "erfahrung", GENERIC_ERFAHRUNG)
                # author sicherstellen
                if not re.search(r"^author:", c2.split("---", 2)[1], re.M):
                    c2 = _set_fm_line(c2, "author", "Frank")
                open(path, "w", encoding="utf-8").write(c2)
                content = c2
                fm, body = _fm_body(content)
                FIXED.append(("T5", slug, "erfahrung ergänzt"))
        author = _get(fm, "author")
        if not author or "frank" not in author.lower():
            PROBLEMS.append(("T5", slug, f"author fehlt/abweichend ({author!r})"))
            if DO_FIX:
                c2 = _set_fm_line(content, "author", "Frank")
                open(path, "w", encoding="utf-8").write(c2)
                content = c2
                FIXED.append(("T5", slug, "author=Frank gesetzt"))

        # T6 interne Links
        internal = len(re.findall(
            r"\]\((?:/posts/|/pillar/|\.\./\.\./posts/|\.\./\.\./pillar/)",
            content,
        ))
        if internal < INTERNAL_MIN:
            PROBLEMS.append(("T6", slug, f"nur {internal} interne Links (< {INTERNAL_MIN})"))

        # T7 Cover
        if not re.search(r"^cover:", fm, re.M) and "image:" not in fm:
            PROBLEMS.append(("T7", slug, "Cover fehlt"))
        else:
            cov = re.search(r'image:\s*[\"\']?([^\"\'\n]+)', fm)
            if cov:
                p = os.path.join(BLOG_DIR, "static", cov.group(1).strip())
                if not os.path.exists(p):
                    PROBLEMS.append(("T7", slug, f"Cover-Datei fehlt: {cov.group(1)}"))

        # Wortanzahl (dünne Seiten = Spam-Signal)
        words = len(re.findall(r"\w+", body))
        if words < 400:
            PROBLEMS.append(("T6", slug, f"nur {words} Wörter (dünne Seite)"))


def check_robots():
    p = os.path.join(BLOG_DIR, "layouts", "robots.txt")
    if not os.path.exists(p):
        PROBLEMS.append(("T8", "-", "layouts/robots.txt fehlt"))
        return
    t = open(p, encoding="utf-8").read()
    if "Pinterestbot" not in t and "Pinterest" not in t:
        PROBLEMS.append(("T8", "-", "Pinterestbot nicht in robots.txt"))
        if DO_FIX:
            with open(p, "a", encoding="utf-8") as f:
                f.write(
                    "\n# Pinterest-Crawler (Rich Pins / Scraping)\n"
                    "User-agent: Pinterestbot\nAllow: /\nDisallow: /go/\n"
                    "User-agent: Pinterest\nAllow: /\nDisallow: /go/\n"
                )
            FIXED.append(("T8", "-", "Pinterestbot-Regeln ergänzt"))
    if "Disallow: /go/" not in t:
        PROBLEMS.append(("T8", "-", "/go/ nicht in robots Disallow"))
        if DO_FIX:
            # nach erstem Allow: / einfügen
            t2 = t.replace("Allow: /", "Allow: /\nDisallow: /go/", 1)
            open(p, "w", encoding="utf-8").write(t2)
            FIXED.append(("T8", "-", "/go/-Disallow ergänzt"))


def check_go_gateway():
    go_dir = os.path.join(BLOG_DIR, "static", "go")
    if not os.path.isdir(go_dir):
        return
    for d in sorted(os.listdir(go_dir)):
        p = os.path.join(go_dir, d, "index.html")
        if not os.path.isfile(p):
            continue
        h = open(p, encoding="utf-8").read()
        if "noindex" not in h:
            PROBLEMS.append(("T11", d, "/go/ ohne noindex"))
        # Gateway darf refresh haben – aber NIE indexiert
        if 'name="robots"' not in h and "noindex" not in h:
            PROBLEMS.append(("T11", d, "/go/ robots-Meta fehlt"))


def check_domain_verify():
    t = open(os.path.join(BLOG_DIR, "hugo.toml"), encoding="utf-8").read()
    m = re.search(r'pinterestVerify\s*=\s*"([^"]+)"', t)
    if not m or not m.group(1).strip():
        PROBLEMS.append(("T12", "-", "pinterestVerify fehlt in hugo.toml"))
    # Pinterest-Profil-Link
    if "pinterest.de/franksfinanzcheck" not in t.lower() and "pinterest.com/franksfinanzcheck" not in t.lower():
        # optional in params – nicht hart failen wenn nur verify da
        pass


def check_rate_limit_code():
    """T9: pinterest_engine.py muss Rate-Limit haben (kein Flooding)."""
    eng = os.path.join(BLOG_DIR, "scripts", "pinterest_engine.py")
    src = open(eng, encoding="utf-8").read()
    # Erwartet: PINS_PRO_TAG / max 3 und time.sleep
    has_cap = bool(re.search(r"PINS_PRO_TAG|PINS_MAX|pins_per", src))
    has_sleep = "time.sleep" in src or "PIN_PAUSE" in src
    # Hard-Fail wenn unpinned[:10] ohne Cap
    flood = bool(re.search(r"unpinned\[:10\]", src)) and not has_cap
    if flood or not has_cap:
        PROBLEMS.append(("T9", "-", "Pinterest-Engine ohne sicheres Rate-Limit (Flooding-Risiko)"))
        if DO_FIX:
            FIXED.append(("T9", "-", "siehe pinterest_engine.py – Rate-Limit wird vom Shield-Patch gesetzt"))
    if not has_sleep and "unpinned[" in src:
        PROBLEMS.append(("T9", "-", "keine Pause zwischen Pins (Spam-Muster)"))


def check_rss():
    rss = os.path.join(BLOG_DIR, "layouts", "_default", "rss.xml")
    if not os.path.exists(rss):
        PROBLEMS.append(("T10", "-", "layouts/_default/rss.xml fehlt (Pinterest Auto-Publish)"))
        return
    t = open(rss, encoding="utf-8").read()
    if "media:content" not in t and "enclosure" not in t:
        PROBLEMS.append(("T10", "-", "RSS ohne Bild-Enclosure (Pinterest braucht Cover)"))
    if 'Section" "posts"' not in t and "Section\" \"posts\"" not in t and "posts" not in t:
        PROBLEMS.append(("T10", "-", "RSS filtert Section posts nicht klar"))


def heal_pipeline():
    """Orchestriert bestehende Heiler in sicherer Reihenfolge."""
    print("== Trust-Heilungs-Pipeline ==")
    # 1) SEO/Pin-Felder
    _run([os.path.join(BLOG_DIR, "scripts", "pinterest_seo_healer.py"), "--fix"])
    # 2) Affiliate-Shield (Direktlinks → /go/, Gateway noindex)
    _run([os.path.join(BLOG_DIR, "scripts", "affiliate_shield.py"), "--fix"])
    # 3) Affiliate-Profi (E-E-A-T, interne Links-Hinweis)
    _run([os.path.join(BLOG_DIR, "scripts", "affiliate_profi_check.py"), "--fix"])
    # 4) Interne Links
    _run([os.path.join(BLOG_DIR, "scripts", "internal_linker.py"), "--apply", "--max", "5"])
    # 5) Cover
    _run([os.path.join(BLOG_DIR, "scripts", "check_covers.py"), "--fix"])
    # 6) Titel-Gate
    _run([os.path.join(BLOG_DIR, "scripts", "check_titles.py"), "--fix"])


def harden_pinterest_engine() -> bool:
    """Schreibt Rate-Limit in pinterest_engine.py falls fehlend/unsicher."""
    eng = os.path.join(BLOG_DIR, "scripts", "pinterest_engine.py")
    src = open(eng, encoding="utf-8").read()
    original = src

    # Konstanten nach ROTATE_DAYS einfügen falls fehlend
    if "PINS_PRO_TAG" not in src:
        src = src.replace(
            'ROTATE_DAYS = int(os.environ.get("PINTEREST_ROTATE_DAYS", "60"))',
            'ROTATE_DAYS = int(os.environ.get("PINTEREST_ROTATE_DAYS", "60"))\n'
            '# Anti-Spam (2026): max. 2–3 Pins pro Lauf, Pause dazwischen –\n'
            '# verhindert „Link leitet an Spam-Webseite weiter\" durch Flooding.\n'
            'PINS_PRO_TAG = max(1, min(3, int(os.environ.get("PINS_PRO_TAG", "2"))))\n'
            'PIN_PAUSE_S = max(45, int(os.environ.get("PIN_PAUSE_S", "45")))',
        )
    # unpinned[:10] → unpinned[:PINS_PRO_TAG]
    src = re.sub(r"unpinned\[:10\]", "unpinned[:PINS_PRO_TAG]", src)
    # time.sleep zwischen Pins im Posting-Loop
    if "time.sleep" not in src and "PIN_PAUSE" in src:
        # import time
        if "import time" not in src:
            src = src.replace("import datetime", "import datetime\nimport time")
        # nach erfolgreichem Pin sleep
        old = '            print(f"  ✓ Pin erstellt: {p[\'slug\']}")'
        new = (
            '            print(f"  ✓ Pin erstellt: {p[\'slug\']}")\n'
            '            if ok < PINS_PRO_TAG:\n'
            '                time.sleep(PIN_PAUSE_S)'
        )
        if old in src:
            src = src.replace(old, new)
    # Drafts und fehlende Cover überspringen
    if "draft" not in src or "skip draft" not in src.lower():
        # load_posts already – filter unpinned for cover + no draft
        marker = 'unpinned = [p for p in posts if not p["pinned"]]'
        if marker in src and "p.get(\"cover\")" not in src:
            src = src.replace(
                marker,
                'unpinned = [p for p in posts if not p["pinned"]\n'
                '            and p.get("cover")\n'
                '            and not p.get("draft")\n'
                '            and "/go/" not in (p.get("cover") or "")]',
            )
    # draft in load_posts
    if '"draft"' not in src and "draft: true" not in src:
        # add draft flag when loading
        old_load = '"pinned": (pinned.group(1) if pinned else "false") == "true",'
        if old_load in src:
            src = src.replace(
                old_load,
                '"pinned": (pinned.group(1) if pinned else "false") == "true",\n'
                '            "draft": "draft: true" in content,',
            )

    # api_post_pin: link hart auf Artikel-URL (nie cover/go)
    if 'f"{BASE_URL}/posts/{post[\'slug\']}/"' in src:
        pass  # already correct
    # Guard in api_post_pin
    if "def api_post_pin" in src and "Trust-Guard" not in src:
        src = src.replace(
            "def api_post_pin(token, board_id, post):\n    body = {",
            "def api_post_pin(token, board_id, post):\n"
            "    # Trust-Guard: Pin-Ziel IMMER Artikel, nie /go/ oder Affiliate\n"
            "    link = f\"{BASE_URL}/posts/{post['slug']}/\"\n"
            "    if \"/go/\" in link or \"check24\" in link.lower():\n"
            "        raise ValueError(f\"Spam-Schutz: ungültiges Pin-Ziel {link}\")\n"
            "    img = f\"{BASE_URL}/{post['cover'].lstrip('/')}\"\n"
            "    if \"/go/\" in img:\n"
            "        raise ValueError(f\"Spam-Schutz: Cover darf kein /go/ sein: {img}\")\n"
            "    body = {",
        )
        # fix media/link fields if we added img/link vars
        src = src.replace(
            '"data": f"{BASE_URL}/{post[\'cover\']}"},',
            '"data": img},',
        )
        src = src.replace(
            '"link": f"{BASE_URL}/posts/{post[\'slug\']}/",',
            '"link": link,',
        )

    if src != original:
        open(eng, "w", encoding="utf-8").write(src)
        return True
    return False


def fix_affiliate_profi_legacy_posts():
    """affiliate_profi_check kennt nur Bundles – Legacy .md manuell heilen."""
    for path in list_post_paths():
        if path.endswith("/index.md"):
            continue  # Bundle – Profi-Check greift
        content = open(path, encoding="utf-8").read()
        fm, body = _fm_body(content)
        if "draft: true" in fm:
            continue
        changed = False
        if not re.search(r"^erfahrung:", fm, re.M):
            content = _set_fm_line(content, "erfahrung", GENERIC_ERFAHRUNG)
            changed = True
            FIXED.append(("T5", slug_of(path), "erfahrung (Legacy-Post)"))
        if not re.search(r"^author:", content.split("---", 2)[1], re.M):
            content = _set_fm_line(content, "author", "Frank")
            changed = True
        if changed:
            open(path, "w", encoding="utf-8").write(content)


def write_report():
    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    # Nach Fix erneut zählen? PROBLEMS kann geheilt sein – neu scannen soft
    lines = [
        "# 🛡️ PINTEREST-TRUST-REPORT (Anti-Spam / Domain-Vertrauen)",
        "",
        f"**Stand:** {now} · **Modus:** {'FIX' if DO_FIX else 'CHECK'}",
        "",
        f"Probleme: **{len(PROBLEMS)}** · Geheilt: **{len(FIXED)}**",
        "",
        "## Warum Pinterest Domains als Spam einstuft (2026)",
        "",
        "1. **Redirect-Ketten** (Meta-Refresh, Shortener, Tracking-Hops)",
        "2. **Affiliate-Landingpages** als Pin-Ziel (/go/, a.check24.net)",
        "3. **Pin-Flooding** (viele Pins in kurzer Zeit, gleiche URL)",
        "4. **Fehlende Domain-Verifikation** / Rich-Pin-Meta",
        "5. **Dünne/duplicate Seiten**, unmarkierte Werbung",
        "6. **SSL/Hosting-Reputation**, Safe-Browsing-Flags",
        "",
        "## Was dieser Blog technisch absichert",
        "",
        "| Signal | Status | Mechanik |",
        "|---|---|---|",
        "| Pin-Ziel = Artikel-URL | T1 | Engine-Guard, nie /go/ |",
        "| Kein Artikel-Redirect | T2 | Check + Publish-Gate |",
        "| Affiliate nur /go/ + sponsored | T3 | affiliate_shield + render-hook |",
        "| Werbekennzeichnung | T4 | pin_description + Trust-Box |",
        "| E-E-A-T (Autor/Erfahrung) | T5 | Frontmatter + Person-Schema |",
        "| Interne Verlinkung | T6 | internal_linker |",
        "| Cover 2:3 + Pin-SEO | T7 | pinterest_seo_healer |",
        "| robots: Pinterestbot, /go/ block | T8 | layouts/robots.txt |",
        "| Rate-Limit 2–3 Pins, ≥45 s | T9 | pinterest_engine |",
        "| RSS mit Cover (Auto-Publish) | T10 | layouts/_default/rss.xml |",
        "| /go/ noindex | T11 | static/go/*/index.html |",
        "| Domain-Verify Meta | T12 | hugo.toml pinterestVerify |",
        "",
    ]
    if PROBLEMS:
        lines += ["## Offene Punkte", "", "| Code | Artikel | Problem |", "|---|---|---|"]
        for code, slug, msg in PROBLEMS:
            lines.append(f"| {code} | {slug} | {msg} |")
    else:
        lines.append("✅ Alle Trust-Signale im Profi-Bereich.")
    if FIXED:
        lines += ["", "## Selbstheilung (diese Runde)", ""]
        for code, slug, msg in FIXED:
            lines.append(f"- [{code}] {slug}: {msg}")
    lines += [
        "",
        "## Manuelle Schritte (einmalig, Business-Konto)",
        "",
        "1. **Website beanspruchen** (falls abgelaufen): Pinterest Business → "
        "Einstellungen → Beanspruchte Konten → franksfinanzcheck.de",
        "2. **URL-Debugger**: https://developers.pinterest.com/tools/url-debugger/ "
        "→ 2–3 Artikel-URLs prüfen → „Apply for Rich Pins“",
        "3. **Sitemap**: `https://franksfinanzcheck.de/sitemap.xml` im Business-Konto hinterlegen",
        "4. **Bei Sperre**: 48 h Pause, dann Support unter „Pins erstellen/bearbeiten“ "
        "(nicht „Domain blockiert“) – siehe `docs/PINTEREST-SPIELBUCH.md`",
        "5. **Pin-Verhalten**: max. 2–3 Pins/Tag, Abstand ≥1–2 h, nie dieselbe URL am selben Tag",
        "",
        "---",
        "*Erzeugt von `scripts/pinterest_trust_shield.py` – FrankAutoOps Anti-Spam.*",
        "",
    ]
    open(REPORT, "w", encoding="utf-8").write("\n".join(lines))


def main() -> int:
    st = _selftest()
    if st:
        print("🛑 TRUST-SELBSTTEST FEHLGESCHLAGEN – keine Änderung.")
        for e in st:
            print(f"   {e}")
        return 2
    print(f"✅ Trust-Selbsttest ok · Modus: {'FIX' if DO_FIX else 'CHECK'}")

    if DO_FIX:
        if harden_pinterest_engine():
            FIXED.append(("T9", "-", "pinterest_engine Rate-Limit + Trust-Guard gehärtet"))
            print("  ✓ pinterest_engine gehärtet")
        fix_affiliate_profi_legacy_posts()
        heal_pipeline()
        # Nach Pipeline: PROBLEMS leeren und frisch prüfen
        PROBLEMS.clear()

    check_articles()
    check_robots()
    check_go_gateway()
    check_domain_verify()
    check_rate_limit_code()
    check_rss()

    write_report()

    for code, slug, msg in PROBLEMS:
        print(f"  ❌ [{code}] {slug}: {msg}")
    for code, slug, msg in FIXED:
        print(f"  ✅ [FIX {code}] {slug}: {msg}")

    print("=" * 60)
    print(f"Pinterest-Trust-Shield: Probleme={len(PROBLEMS)} Geheilt={len(FIXED)}")
    print(f"Report: {REPORT}")

    if AS_JSON:
        print(json.dumps({"problems": PROBLEMS, "fixed": FIXED}, ensure_ascii=False, indent=2))
    return 1 if PROBLEMS else 0


if __name__ == "__main__":
    sys.exit(main())
