#!/usr/bin/env python3
"""
Automatischer Internal-Linker für FranksFinanzcheck.

Findet semantisch passende Verlinkungsziele zwischen Artikeln und fügt
kontextuelle Links in den Fließtext ein – auf Profi-Niveau:

  - Max. 2-3 neue Links pro Artikel (SEO: nicht übertreiben)
  - Nur EIN Vorkommen pro Ankertext (keine Link-Wiederholungen)
  - Keine Links in Überschriften, Frontmatter, Code, bestehenden Links
  - Anker = natürliche Keyword-Phrase (1-3 Wörter) aus dem Zielartikel
  - Kein Link auf sich selbst, keine doppelten Ziele im selben Artikel
  - Dry-run (--dry-run) zeigt Vorschläge, --apply fügt sie ein

Nutzung:
    python3 scripts/internal_linker.py --dry-run      # Vorschläge anzeigen
    python3 scripts/internal_linker.py --apply        # Links einfügen
    python3 scripts/internal_linker.py --apply --max 3

Workflow: seo-weekly.yml ruft es mit --apply auf (nach Keyword-Optimierung).
"""
import os
import re
import sys
import yaml

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
MAX_LINKS_PER_ARTICLE = 3  # neue Links pro Artikel pro Lauf
MIN_WORDS = 2              # Ankertext min. Wörter (vermeidet generische Links)
MAX_WORDS = 4              # Ankertext max. Wörter

# Zu ignorierende Anker (generisch/kein SEO-Wert)
STOP_ANCHORS = {
    "hier", "dort", "klick", "mehr", "weiter", "diesen artikel", "diesen beitrag",
    "check24", "lesen", "jetzt", "so geht", "tipp", "tricks",
}


def parse_frontmatter(content):
    """Liest Frontmatter (Titel, Keywords, Tags) + Body."""
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.S)
    if not m:
        return {}, content
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except Exception:
        fm = {}
    return fm, m.group(2)


def strip_markdown(text):
    """Entfernt Markdown-Formatierung, um saubere Anker zu bekommen."""
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)          # Bilder
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)      # Links → Text
    text = re.sub(r"[*_#>`~]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def find_anchor(body, phrase):
    """Findet das erste Vorkommen einer Phrase im Body, außerhalb von
    Überschriften, Links, Code und Frontmatter."""
    # Body ohne Code-Blöcke betrachten (Positionen bleiben erhalten)
    code_ranges = []
    for m in re.finditer(r"(`[^`]*`|```.*?```)", body, re.S):
        code_ranges.append((m.start(), m.end()))
    # Body ohne bestehende Links betrachten
    link_ranges = []
    for m in re.finditer(r"\[[^\]]*\]\([^)]*\)", body):
        link_ranges.append((m.start(), m.end()))

    # Überschriften-Ranges
    head_ranges = []
    for m in re.finditer(r"^#{1,6} .*$", body, re.M):
        head_ranges.append((m.start(), m.end()))

    blocked = code_ranges + link_ranges + head_ranges

    def is_blocked(pos):
        return any(s <= pos < e for s, e in blocked)

    # Suche alle Vorkommen (case-insensitive), nimm das erste nicht blockierte
    for m in re.finditer(re.escape(phrase), body, re.I):
        # Prüfe Wortgrenzen (nicht mitten im Wort)
        before = body[m.start() - 1] if m.start() > 0 else ""
        after = body[m.end()] if m.end() < len(body) else ""
        if before.isalnum() or after.isalnum():
            continue
        if is_blocked(m.start()):
            continue
        return m.start(), m.end()
    return None


def build_anchor_candidates(pages):
    """Baut Kandidaten-Phrasen aus Titel/Keywords aller Artikel."""
    candidates = []  # (phrase, target_path, score)
    for path, info in pages.items():
        title = info["title"]
        # Titel-Phrasen: ganze Wörter (2-4) aus dem Titel
        words = re.findall(r"[A-Za-zÄÖÜäöüß0-9-]+", title.lower())
        if len(words) >= 2:
            for n in (2, 3):
                if len(words) >= n:
                    phrase = " ".join(words[:n])
                    if phrase not in STOP_ANCHORS:
                        candidates.append((phrase, path, info.get("score", 50)))
        # Keywords (1-3 Wörter)
        for kw in info.get("keywords", [])[:5]:
            kw_l = kw.lower().strip()
            if 2 <= len(kw_l.split()) <= MAX_WORDS and kw_l not in STOP_ANCHORS:
                candidates.append((kw_l, path, info.get("score", 60) + 10))
    return candidates


def load_pages():
    """Lädt alle Artikel mit Metadaten."""
    pages = {}
    for fn in sorted(os.listdir(POSTS_DIR)):
        if not fn.endswith(".md"):
            continue
        path = os.path.join(POSTS_DIR, fn)
        content = open(path, encoding="utf-8").read()
        fm, body = parse_frontmatter(content)
        title = fm.get("title", fn[:-3])
        keywords = [k.strip().lower() for k in (fm.get("keywords") or [])]
        tags = [t.strip().lower() for t in (fm.get("tags") or [])]
        pages[fn] = {
            "title": title,
            "keywords": keywords,
            "tags": tags,
            "body": body,
            "score": 50 + 10 * min(len(keywords), 3),
            "path": path,
        }
    return pages


def topic_overlap(a, b):
    """Überlappung der Themen (keywords/tags) zwischen zwei Artikeln."""
    a_set = set(a["keywords"] + a["tags"])
    b_set = set(b["keywords"] + b["tags"])
    if not a_set or not b_set:
        return 0
    return len(a_set & b_set)


def main():
    dry = "--dry-run" in sys.argv
    apply = "--apply" in sys.argv
    max_links = MAX_LINKS_PER_ARTICLE
    if "--max" in sys.argv:
        try:
            max_links = int(sys.argv[sys.argv.index("--max") + 1])
        except (ValueError, IndexError):
            pass

    pages = load_pages()
    candidates = build_anchor_candidates(pages)
    print(f"Artikel: {len(pages)} | Kandidaten-Phrasen: {len(candidates)}\n")

    total_added = 0
    for src_fn, src in sorted(pages.items()):
        added = 0
        used_targets = set()
        used_phrases = set()
        # Sortiere Kandidaten nach Themen-Überlappung mit dem Quellartikel
        scored = []
        for phrase, tgt_fn, base_score in candidates:
            if tgt_fn == src_fn:
                continue
            overlap = topic_overlap(src, pages[tgt_fn])
            if overlap == 0 and base_score < 70:
                continue  # kein thematischer Bezug
            scored.append((overlap * 100 + base_score, phrase, tgt_fn))
        scored.sort(reverse=True)

        for score, phrase, tgt_fn in scored:
            if added >= max_links:
                break
            if tgt_fn in used_targets:
                continue
            if phrase in used_phrases:
                continue  # pro Phrase nur EIN Ziel (keine Anker-Duplikate)
            anchor = find_anchor(src["body"], phrase)
            if not anchor:
                continue
            start, end = anchor
            target = f"/posts/{tgt_fn[:-3]}/"
            rel = pages[tgt_fn]["path"]
            print(f"  {src_fn}: „{src['body'][start:end].strip()}“ → {tgt_fn} (Score {score})")
            if apply:
                # Nur das erste Vorkommen verlinken, Rest unangetastet
                content = open(src["path"], encoding="utf-8").read()
                # Position im Gesamt-Dokument (Frontmatter verschiebt Body)
                fm_match = re.match(r"^---\n.*?\n---\n", content, re.S)
                offset = fm_match.end() if fm_match else 0
                abs_start = offset + start
                abs_end = offset + end
                # Sicherheitscheck: nichts kaputt machen
                if content[abs_start - 1] in "[(" or content[abs_end] in "])":
                    continue
                old = content[abs_start:abs_end]
                new = f"[{old}]({target})"
                content = content[:abs_start] + new + content[abs_end:]
                with open(src["path"], "w", encoding="utf-8") as f:
                    f.write(content)
            added += 1
            used_targets.add(tgt_fn)
            used_phrases.add(phrase)
            total_added += 1

        if added:
            print(f"  → {src_fn}: {added} Link(s) {'eingefügt' if apply else 'vorgeschlagen'}")
    print(f"\nFertig: {total_added} Links {'eingefügt' if apply else 'vorgeschlagen'} "
          f"({len(pages)} Artikel).")


if __name__ == "__main__":
    main()
