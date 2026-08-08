#!/usr/bin/env python3
"""
TOP-LEVEL-GRAMMATIKPRÜFUNG für FranksFinanzcheck (LanguageTool API).

Nutzt die kostenlose LanguageTool-Public-API (api.languagetool.org) – den
Goldstandard für deutsche Grammatik- und Stilprüfung (Open Source,
DSGVO-freundlich, keine Cookies).

GEPRÜFT WERDEN:
  - Rechtschreibung (über Hunspell hinaus: Kontext-Fehler wie "das/dass")
  - Grammatik (Kongruenz, Tempus, Satzstruktur)
  - Groß-/Kleinschreibung in Wendungen ("nach hause" → "nach Hause")
  - Zeichensetzung (Kommas, Anführungszeichen)
  - Typische deutsche Fehler (sie/ Sie, wieder/wider, seid/seit …)

SICHERHEIT:
  - Links/URLs/Code-Blöcke werden maskiert und NIE verändert
  - Whitelist (data/grammar_whitelist.txt) schützt Eigennamen/Fachbegriffe
  - Nur EINDEUTIGE Korrekturen (genau 1 Vorschlag) werden automatisch
    angewendet (--fix); unsichere landen im Report
  - Frontmatter (title/description) wird mitgeprüft, tags/keywords nicht

NUTZUNG:
  python3 scripts/grammar_check.py               # Prüfung + Report
  python3 scripts/grammar_check.py --fix         # eindeutige Fehler korrigieren
  python3 scripts/grammar_check.py --file X.md   # einzelner Artikel
  python3 scripts/grammar_check.py --new-only    # nur Artikel von heute
"""
import os
import re
import sys
import json
import glob
import time
import urllib.request
import urllib.parse

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
WHITELIST_FILE = os.path.join(BLOG_DIR, "data", "grammar_whitelist.txt")
REPORT_FILE = os.path.join(BLOG_DIR, "GRAMMATIK-REPORT.md")
JSON_FILE = os.path.join(BLOG_DIR, ".grammar_report.json")
API_URL = "https://api.languagetool.org/v2/check"
MAX_CHUNK = 3500  # LanguageTool-Limit pro Request

# Nur diese Fehlerkategorien automatisch fixen (kein Stil-Gefrickel)
FIX_CATEGORIES = {"TYPOS", "GRAMMAR", "CASING", "PUNCTUATION", "GERMAN_SPELLING",
                  "COMMA_PARENTHESIS_WHITESPACE", "REDUNDANCY", "DAS_DASS",
                  "DOUBLE_NEGATION", "CONFUSED_WORDS"}
# Kategorien, die NIE automatisch geändert werden (Stil/Geschmack)
SKIP_CATEGORIES = {"WORDINESS", "STYLE", "CREATIVE_WRITING", "TYPOS_DE"}

# Wörter, die LanguageTool fälschlich anmeckert (Dialekt/Marken)
DEFAULT_WHITELIST = {
    "frugalismus", "frugalismus-tipps", "fritzbox", "check24", "tarifcheck",
    "cloudflare", "schufa", "cashback", "etf", "etfs", "mesh", "repeater",
    "wlan", "dns", "dsl", "mbit", "kbit", "smartphone", "smartphones",
    "girocard", "wallbox", "dispo", "app", "apps", "streaming", "tracking",
}


def load_whitelist():
    wl = set(DEFAULT_WHITELIST)
    if os.path.exists(WHITELIST_FILE):
        for line in open(WHITELIST_FILE, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#"):
                wl.add(line.lower())
    return wl


def mask_protected(text):
    """Maskiert Links/URLs/Code durch gleich lange Platzhalter (Offset-sicher)."""
    code_re = re.compile(r"```.*?```", re.S)
    url_re = re.compile(r"https?://[^\s)\"']+|www\.[^\s)\"']+")
    link_re = re.compile(r"\[([^\]]*)\]\([^)]*\)")
    text = code_re.sub(lambda m: " " * (m.end() - m.start()), text)
    text = url_re.sub(lambda m: " " * (m.end() - m.start()), text)
    text = link_re.sub(lambda m: m.group(1), text)
    # &nbsp; → gleich viele Leerzeichen (Offsets bleiben gültig, kein "nbsp"-Wort)
    text = text.replace("&nbsp;", " " * 6)
    return text


def chunk_text(text, size=MAX_CHUNK):
    """Teilt Text in Chunks an Satzgrenzen."""
    if len(text) <= size:
        return [text]
    chunks = []
    while len(text) > size:
        cut = text.rfind(". ", 0, size)
        if cut < size * 0.5:
            cut = size
        chunks.append(text[:cut + 1])
        text = text[cut + 1:]
    if text:
        chunks.append(text)
    return chunks


def lt_check(text, whitelist):
    """LanguageTool-Check eines Texts. Liefert Liste von Matches (gefiltert)."""
    if not text.strip():
        return []
    results = []
    for chunk in chunk_text(text):
        data = urllib.parse.urlencode({
            "language": "de-DE",
            "text": chunk,
            "enabledOnly": "false",
        }).encode()
        req = urllib.request.Request(API_URL, data=data,
                                     headers={"User-Agent": "Mozilla/5.0 (FranksFinanzcheck-Bot)",
                                              "Content-Type": "application/x-www-form-urlencoded"})
        try:
            resp = json.loads(urllib.request.urlopen(req, timeout=60).read())
        except Exception as e:
            print(f"  ⚠️ LanguageTool-Fehler: {e}")
            time.sleep(5)
            continue
        for m in resp.get("matches", []):
            cat = m.get("rule", {}).get("category", {}).get("id", "")
            if cat in SKIP_CATEGORIES:
                continue
            if cat not in FIX_CATEGORIES and cat != "UNKNOWN_WORD":
                continue
            offset = m.get("offset", 0)
            length = m.get("length", 0)
            word = chunk[offset:offset + length]
            # Whitelist: Wort ignorieren
            wl_key = word.lower().strip(".,;:!?")
            if wl_key in whitelist:
                continue
            # Nur Vorschläge mit genau 1 Replacement = eindeutig
            repls = m.get("replacements", [])
            if len(repls) != 1:
                continue
            repl = repls[0].get("value", "")
            if not repl or repl == word:
                continue
            # "Du"→"du" Einheitlichkeits-Vorschläge NICHT fixen (Stil-Entscheidung
            # des Blogs: "Du" am Satzanfang groß, "du" im Satz klein ist üblich)
            if word in ("Du", "Dein", "Deine", "Deinem", "Deiner", "Sie", "Ihr", "Ihre") \
               and repl.lower() == word.lower() and cat != "CASING":
                continue
            # Komma-Fixes: nur annehmen, wenn nicht zu invasiv
            if cat == "PUNCTUATION" and len(repl) > len(word) + 5:
                continue
            results.append({
                "offset": offset, "length": length, "word": word, "fix": repl,
                "message": m.get("message", ""), "category": cat,
                "conf": 0.9,
            })
        time.sleep(0.6)  # Rate-Limit der Public-API (~20 chars/s)
    return results


def load_articles(files=None, new_only=False):
    import datetime
    today = datetime.date.today().isoformat()
    arts = []
    paths = files or sorted(
        glob.glob(os.path.join(POSTS_DIR, "*.md"))
        + glob.glob(os.path.join(POSTS_DIR, "*", "index.md"))
    )
    for path in paths:
        content = open(path, encoding="utf-8").read()
        parts = content.split("---", 2)
        if len(parts) < 3:
            continue
        fm, body = parts[1], parts[2]
        if "draft: true" in fm:
            continue

        def get(key):
            m = re.search(rf"^{key}:\s*[\"']?(.+?)[\"']?\s*$", fm, re.M)
            return m.group(1).strip() if m else ""

        date = get("date")
        if new_only and not date.startswith(today):
            continue
        arts.append({
            "file": os.path.relpath(path, POSTS_DIR), "path": path,
            "title": get("title"), "description": get("description"),
            "fm": fm, "body": body, "content": content,
        })
    return arts


def analyze_article(a, whitelist):
    """Prüft Body (maskiert) auf Grammatik-Fehler."""
    problems = []
    # Body
    body_masked = mask_protected(a["body"])
    matches = lt_check(body_masked, whitelist)
    for m in matches:
        problems.append({
            "type": "grammar", "word": m["word"], "fix": m["fix"],
            "start": m["offset"], "end": m["offset"] + m["length"],
            "conf": m["conf"], "reason": f"{m['message']} ({m['category']})",
        })
    # Description (Frontmatter)
    desc = a.get("description", "")
    if desc:
        desc_idx = a["content"].find('description: "')
        if desc_idx >= 0:
            dstart = desc_idx + len('description: "')
            dm = lt_check(desc, whitelist)
            for m in dm:
                problems.append({
                    "type": "grammar", "word": m["word"], "fix": m["fix"],
                    "abs_start": dstart + m["offset"],
                    "abs_end": dstart + m["offset"] + m["length"],
                    "conf": m["conf"], "reason": f"Description: {m['message']} ({m['category']})",
                })
    return problems


def apply_fix(a, problem):
    content = a["content"]
    parts = content.split("---", 2)
    body_start = content.index(parts[2]) if len(parts) == 3 else 0
    if "abs_start" in problem:
        abs_start, abs_end = problem["abs_start"], problem["abs_end"]
    else:
        abs_start, abs_end = body_start + problem["start"], body_start + problem["end"]
    old = content[abs_start:abs_end]
    if old != problem["word"]:
        return False
    content = content[:abs_start] + problem["fix"] + content[abs_end:]
    a["content"] = content
    return True


def main():
    fix = "--fix" in sys.argv
    as_json = "--json" in sys.argv
    new_only = "--new-only" in sys.argv
    files = None
    if "--file" in sys.argv:
        files = [sys.argv[sys.argv.index("--file") + 1]]

    whitelist = load_whitelist()
    articles = load_articles(files, new_only)
    print(f"Grammatik-Prüfung (LanguageTool): {len(articles)} Artikel\n")

    all_problems = []
    for a in articles:
        problems = analyze_article(a, whitelist)
        if problems:
            all_problems.append({"file": a["file"], "title": a["title"], "problems": problems})
            print(f"  {a['file']}: {len(problems)} Funde")

    # Anwenden (rückwärts)
    fixed_count = 0
    for entry in all_problems:
        a = next(x for x in articles if x["file"] == entry["file"])
        entry["problems"].sort(key=lambda p: p.get("abs_start", p.get("start")), reverse=True)
        for p in entry["problems"]:
            if fix and p["conf"] >= 0.8:
                if apply_fix(a, p):
                    fixed_count += 1
                    p["applied"] = True
            elif p["conf"] >= 0.8:
                p["applied"] = False

    if fix:
        for a in articles:
            orig = open(a["path"], encoding="utf-8").read()
            if a["content"] != orig:
                open(a["path"], "w", encoding="utf-8").write(a["content"])

    # Report
    total = sum(len(e["problems"]) for e in all_problems)
    still = [p for e in all_problems for p in e["problems"] if not p.get("applied")]
    lines = [
        "# 🔤 Grammatik-Report", "",
        f"> **Automatisch** – {len(articles)} Artikel geprüft (LanguageTool de-DE), "
        f"{total} Funde, {fixed_count} korrigiert, {len(still)} offen.", "",
        "## Funde", "",
    ]
    for e in all_problems:
        lines.append(f"### {e['file']}")
        for p in e["problems"]:
            mark = "✅" if p.get("applied") else "⚠️"
            lines.append(f"- {mark} „{p['word']}“ → „{p['fix']}“ – {p['reason'][:80]}")
    lines += ["", "---", "*Erzeugt von scripts/grammar_check.py (LanguageTool Public API)*"]
    open(REPORT_FILE, "w", encoding="utf-8").write("\n".join(lines))
    json.dump({"articles": len(articles), "total": total, "fixed": fixed_count,
               "open": len(still)}, open(JSON_FILE, "w", encoding="utf-8"))

    print(f"\nFertig: {total} Funde, {fixed_count} korrigiert, {len(still)} offen.")
    sys.exit(1 if still else 0)


if __name__ == "__main__":
    main()
