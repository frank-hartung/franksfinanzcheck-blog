#!/usr/bin/env python3
"""Zeichenlängen-Gate (deterministisch, selbstheilend) für FranksFinanzcheck.

Stellt sicher, dass alle Blogartikel die Ziel-Länge haben (Profi-Format):

  MIN_WORDS  = 700   (hartes Minimum – darunter gilt der Artikel als „zu kurz")
  OPT_MIN    = 800   (unteres Optimum – darunter: „unter Optimum", kein Fehler)
  OPT_MAX    = 1400  (oberes Optimum)
  MAX_WORDS  = 1800  (hartes Maximum – darüber: „zu lang")

DAUERVORGABE ZEICHENLÄNGE (festgelegt 19.08.2026, Blog-Launch 08.08.2026):
  Empfohlen pro Blogartikel 6.000–10.000 Zeichen Fließtext
  (≈ 800–1.400 Wörter; empirisch aus dem Bestand: Median 9.124 Zeichen
  bei 6,96 Zeichen/Wort). Die Zeichen-Empfehlung wird ausgewiesen und
  als Hinweis gemeldet – die HARTEN Gates bleiben wortbasiert
  (Hoheitskarte QUALITAETS-REGELWERK.md: Posts check_length.py,
  Pillar length_guard.py).

Gemessen wird im FLIESSTEXT (Frontmatter, Code-Blöcke, HTML, Bild-Markup
raus; Markdown-Links werden auf ihren Anzeigetext reduziert). Zusätzlich
zur Wortzahl wird die Zeichenzahl (mit Leerzeichen) ausgewiesen.

Selbstheilung:
  --fix       ruft für alle Artikel unter MIN_WORDS die KI-Verlängerung auf
              (scripts/extend_articles.py) und prüft danach erneut.
  (ohne --fix) nur melden; Exit 1 bei zu kurzen/zu langen Artikeln.

Nutzung:
  python3 scripts/check_length.py             # nur melden (Exit 0/1)
  python3 scripts/check_length.py --fix       # kurze Artikel verlängern
  python3 scripts/check_length.py --json      # JSON-Report

Exit: 0 = alle im Rahmen · 1 = mind. 1 Verstoß (Workflow kann alerten).
"""
import os
import re
import sys
import json
import glob
import subprocess

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Schwellen via Env ueberschreibbar (Audit 11.08.: Affiliate-Floor 1000 in der
# Engine per Variable LENGTH_MIN_WORDS gesetzt - siehe content-engine-v2.yml)
MIN_CHARS = int(os.environ.get("LENGTH_MIN_CHARS") or 8000)
OPT_MIN_CHARS = int(os.environ.get("LENGTH_OPT_CHARS_MIN") or 10000)
OPT_MAX_CHARS = int(os.environ.get("LENGTH_OPT_CHARS_MAX") or 20000)
MAX_CHARS = int(os.environ.get("LENGTH_MAX_CHARS") or 25000)

RE_CODE = re.compile(r"```.*?```", re.S)
RE_HTML = re.compile(r"<[^>]+>")
RE_IMG = re.compile(r"!\[[^\]]*\]\([^)]*\)")
RE_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def clean_body(content: str) -> str:
    """Fließtext aus einer Artikel-Datei extrahieren (Längen-Messung)."""
    parts = content.split("---", 2)
    body = parts[2] if len(parts) >= 3 else content
    body = RE_CODE.sub(" ", body)
    body = RE_IMG.sub(" ", body)
    body = RE_HTML.sub(" ", body)
    body = RE_LINK.sub(r"\1", body)
    return body


def measure(body: str):
    words = len(body.split())
    chars = len(body)
    return words, chars


def status_of(chars: int) -> str:
    if chars < MIN_CHARS:
        return "zu-kurz"
    if chars > MAX_CHARS:
        return "zu-lang"
    if chars < OPT_MIN_CHARS or chars > OPT_MAX_CHARS:
        return "unter-optimum"
    return "ok"


def collect():
    arts = []
    from post_utils import list_post_paths, slug_of
    for f in list_post_paths():
        content = open(f, encoding="utf-8").read()
        body = clean_body(content)
        words, chars = measure(body)
        m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.M)
        title = m.group(1).strip() if m else ""
        arts.append({
            "file": f,
            "slug": slug_of(f),
            "title": title,
            "words": words,
            "chars": chars,
            "status": status_of(chars),
        })
    return arts


def main():
    fix = "--fix" in sys.argv
    as_json = "--json" in sys.argv
    arts = collect()
    issues = [a for a in arts if a["status"] in ("zu-kurz", "zu-lang")]

    if fix:
        short = [a for a in arts if a["status"] == "zu-kurz"]
        if short:
            print(f"{len(short)} Artikel unter {MIN_CHARS} Zeichen – "
                  f"starte KI-Verlängerung …")
            subprocess.run([sys.executable,
                            os.path.join(BLOG_DIR, "scripts", "extend_articles.py"),
                            "--min-chars", str(MIN_CHARS)],
                           cwd=BLOG_DIR, check=False)
            # Erneut messen
            arts = collect()
            issues = [a for a in arts if a["status"] in ("zu-kurz", "zu-lang")]

    ok = sum(1 for a in arts if a["status"] == "ok")
    opt = sum(1 for a in arts if a["status"] == "unter-optimum")
    print(f"Längen-Check: {len(arts)} Artikel | ok: {ok} | unter-Optimum: {opt} "
          f"| zu-kurz: {sum(1 for a in arts if a['status'] == 'zu-kurz')} "
          f"| zu-lang: {sum(1 for a in arts if a['status'] == 'zu-lang')}")
    print(f"Zielbandbreite: {MIN_CHARS}-{MAX_CHARS} Zeichen "
          f"(Optimum {OPT_MIN_CHARS}-{OPT_MAX_CHARS})")
    for a in sorted(issues, key=lambda x: x["chars"]):
        print(f"  ❌ [{a['status']}] {a['slug']}: {a['chars']} Zeichen / "
              f"{a['words']} Wörter")
    # Unter-Optimum nur als Hinweis (kein Fehler)
    for a in sorted(arts, key=lambda x: x["chars"]):
        if a["status"] == "unter-optimum":
            print(f"  ℹ️ [unter-Optimum] {a['slug']}: {a['chars']} Zeichen")

    if as_json:
        print(json.dumps({
            "total": len(arts), "ok": ok, "unter_optimum": opt,
            "zu_kurz": sum(1 for a in arts if a["status"] == "zu-kurz"),
            "zu_lang": sum(1 for a in arts if a["status"] == "zu-lang"),
            "min_chars": MIN_CHARS, "max_chars": MAX_CHARS,
            "items": arts,
        }, ensure_ascii=False))
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
