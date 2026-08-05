#!/usr/bin/env python3
"""
Einzigartigkeits-Audit für alle Blog-Artikel.

Prüft:
  1) Jeden Artikel gegen die Pinterest-Pin-Texte (Quelle: data/pinterest_plan.yaml)
  2) Jeden Artikel gegen alle anderen Artikel (interne Duplikate)

WICHTIG: Template-Bausteine (Werbekennzeichnung, Affiliate-CTA, FAQ-Rahmen)
werden VOR dem Vergleich entfernt – nur der echte Fließtext zählt.

Nutzung:
    python3 scripts/check_uniqueness.py            # alle Artikel prüfen
    python3 scripts/check_uniqueness.py --strict   # strengere Schwelle (5-Wort-Phrasen)
"""
import os
import re
import sys
from itertools import combinations

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
PINTEREST_PLAN = os.path.join(BLOG_DIR, "data", "pinterest_plan.yaml")

PHRASE_LEN = int(os.environ.get("PHRASE_LEN", "7"))
MAX_SIMILAR = int(os.environ.get("MAX_SIMILAR", "1"))


def norm(s):
    s = s.lower()
    s = re.sub(r"[äàáâ]", "ae", s)
    s = re.sub(r"[öòóô]", "oe", s)
    s = re.sub(r"[üùúû]", "ue", s)
    s = re.sub(r"ß", "ss", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def clean_body(content):
    """Entfernt Frontmatter und alle Template-Bausteine → nur Fließtext."""
    parts = content.split("---", 2)
    body = parts[2] if len(parts) == 3 else content
    # Werbekennzeichnung (variiert in Zeilenumbrüchen)
    body = re.sub(r"\*?Dieser Artikel enthält Affiliate-Links.*?(Mehrkosten|Mehrkosten\.)\*?", " ", body, flags=re.S)
    # Affiliate-CTA-Blöcke (👉 ... Link ...)
    body = re.sub(r"👉.*?\)", " ", body, flags=re.S)
    # FAQ-Intro-Standardsätze
    body = re.sub(r"## Häufige Fragen", " ", body)
    # Übrige Markdown-Syntax
    body = re.sub(r"[*_#>`|~-]{1,}", " ", body)
    return body


def ngrams(text, n):
    words = re.findall(r"\w+", norm(text))
    return set(" ".join(words[i:i + n]) for i in range(len(words) - n + 1))


def load_pinterest_plan():
    pins = []
    if not os.path.exists(PINTEREST_PLAN):
        return pins
    current = None
    with open(PINTEREST_PLAN, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("- tag:"):
                current = {"tag": line.split(":", 1)[1].strip()}
                pins.append(current)
            elif current and ":" in line:
                key, val = line.split(":", 1)
                current[key.strip()] = val.strip().strip("\"'")
    return pins


def find_pin_for_topic(topic_title, pins):
    t = norm(topic_title)
    best, best_score = None, 0
    for p in pins:
        ref = norm((p.get("titel") or "") + " " + (p.get("pinwand") or ""))
        score = 0
        t_tokens = t.split()
        ref_tokens = ref.split()
        for i in range(min(len(t_tokens), 6)):
            if i < len(ref_tokens) and t_tokens[i] == ref_tokens[i]:
                score += 1
        if score > best_score:
            best, best_score = p, score
    return best if best_score >= 2 else None


def main():
    strict = "--strict" in sys.argv
    n = 5 if strict else PHRASE_LEN
    max_sim = 1 if strict else MAX_SIMILAR

    articles = {}
    titles = {}
    for fn in sorted(os.listdir(POSTS_DIR)):
        if not fn.endswith(".md"):
            continue
        content = open(os.path.join(POSTS_DIR, fn), encoding="utf-8").read()
        m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.M)
        titles[fn] = m.group(1) if m else fn
        articles[fn] = clean_body(content)

    print(f"Prüfe {len(articles)} Artikel (Phrasenlänge: {n}, max. ähnlich: {max_sim})\n")

    # 1) Gegen Pinterest-Pins
    pins = load_pinterest_plan()
    print("=== 1) Vergleich mit Pinterest-Pins ===")
    pin_problems = 0
    for fn in sorted(articles):
        pin = find_pin_for_topic(titles[fn], pins)
        if not pin:
            continue
        ref = norm((pin.get("titel") or "") + " " + (pin.get("beschreibung") or "") + " " + (pin.get("keywords") or ""))
        ref_words = ref.split()
        if len(ref_words) < n:
            continue
        ref_grams = set(" ".join(ref_words[i:i + n]) for i in range(len(ref_words) - n + 1))
        my_grams = ngrams(articles[fn], n)
        hits = len(my_grams & ref_grams)
        if hits > max_sim:
            pin_problems += 1
            print(f"  ⚠️ {fn[:45]}: {hits} gleiche Phrasen mit Pin (Tag {pin.get('tag')})")
    if not pin_problems:
        print("  ✅ Alle Artikel einzigartig gegenüber den Pin-Texten")

    # 2) Interne Duplikate
    print("\n=== 2) Interne Duplikate (Artikel untereinander) ===")
    names = sorted(articles.keys())
    grams = {fn: ngrams(articles[fn], n) for fn in names}
    internal = 0
    critical = 0
    for a, b in combinations(names, 2):
        overlap = len(grams[a] & grams[b])
        if overlap > max_sim:
            internal += 1
            if overlap >= 5:
                critical += 1
                print(f"  🚨 KRITISCH {a[:32]} ↔ {b[:32]}: {overlap} gleiche Phrasen")
            else:
                print(f"  ℹ️ unkritisch {a[:32]} ↔ {b[:32]}: {overlap} Phrasen (Standard-Formulierungen)")
    if not internal:
        print("  ✅ Keine internen Duplikate")
    else:
        print(f"  (davon kritisch: {critical} – unter 5 Phrasen ist normal und kein Duplicate Content)")

    print(f"\nErgebnis: Pin-Konflikte: {pin_problems} | Interne Überlappungen: {internal}")


if __name__ == "__main__":
    main()
