#!/usr/bin/env python3
"""Zeichenlängen-Gate (deterministisch, selbstheilend) für FranksFinanzcheck.

Premium-Korridor (Google YMYL + Pinterest-Landing, SSOT length_policy.py):

  Posts Floor   10.000 Zeichen  (hartes Minimum)
  Posts Optimum 12.000–18.000 Zeichen
  Posts Maximum 22.000 Zeichen  (darüber: „zu lang“)

Gemessen wird im FLIESSTEXT (Frontmatter, Code-Blöcke, HTML, Bild-Markup
raus; Markdown-Links auf Anzeigetext reduziert).

Selbstheilung:
  --fix  ruft scripts/extend_articles.py für alle Artikel unter dem Floor
         und prüft danach erneut.

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
import subprocess

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
import length_policy as lp  # noqa: E402

MIN_CHARS = lp.POSTS["target_min_chars"]
OPT_MIN_CHARS = lp.POSTS["opt_min_chars"]
OPT_MAX_CHARS = lp.POSTS["opt_max_chars"]
MAX_CHARS = lp.POSTS["fat_chars"]

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


def measure_file(content: str):
    """SSOT: dieselbe Messung wie length_guard / length_policy."""
    return lp.measure(content)


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
        if re.search(r"^draft:\s*true\s*$", content[:2500], re.M):
            continue
        words, chars = measure_file(content)
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
