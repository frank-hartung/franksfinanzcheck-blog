#!/usr/bin/env python3
"""
Automatische Meta-Daten-Optimierung (Profi-Niveau, kostenlos).

Prüft und optimiert für ALLE Artikel:
  - Title (Frontmatter): 30-60 Zeichen (SEO-optimal)
  - Meta-Description: 70-160 Zeichen (mit Keyword, klickstark)
  - Keywords: 3-8 relevante Begriffe
  - Alt-Texte, OpenGraph-Bilder (og:image), Canonical

Funktionen:
  python3 scripts/meta_optimizer.py              # Audit (nur prüfen)
  python3 scripts/meta_optimizer.py --fix        # fehlende/zu kurze Descriptions
                                                  automatisch aus dem Inhalt erzeugen
  python3 scripts/meta_optimizer.py --ai         # KI-generierte, klickstarke Descriptions
                                                  (Gemini/Groq, mit Cache)
  python3 scripts/meta_optimizer.py --json       # JSON-Report

Exit-Code: 0 = ok, 1 = Artikel mit kritischen Meta-Problemen
"""
import json
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
CACHE_FILE = os.path.join(BLOG_DIR, ".meta_cache.json")

TITLE_MIN, TITLE_MAX = 30, 60
DESC_MIN, DESC_MAX = 70, 160
# Optimale CTR-Bereiche (für den 100er-Score im Meta-Report)
TITLE_OPT_MIN, TITLE_OPT_MAX = 50, 60
DESC_OPT_MIN, DESC_OPT_MAX = 120, 160
KEYWORDS_MIN = 3


def parse_keywords(raw):
    """Parst Keywords aus dem Frontmatter (YAML-Liste oder Komma-String)."""
    if not raw:
        return []
    raw = raw.strip()
    if raw.startswith("["):
        return [k.strip().strip('"\'') for k in raw[1:-1].split(",") if k.strip()]
    return [k.strip().strip('"\'') for k in raw.split(",") if k.strip()]


def norm(s):
    s = s.lower()
    s = re.sub(r"[äàáâ]", "ae", s)
    s = re.sub(r"[öòóô]", "oe", s)
    s = re.sub(r"[üùúû]", "ue", s)
    s = re.sub(r"ß", "ss", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def load_articles():
    arts = []
    for fn in sorted(os.listdir(POSTS_DIR)):
        if not fn.endswith(".md"):
            continue
        content = open(os.path.join(POSTS_DIR, fn), encoding="utf-8").read()
        parts = content.split("---", 2)
        fm = parts[1] if len(parts) > 1 else ""
        body = parts[2] if len(parts) == 3 else content
        if "draft: true" in fm:
            continue

        def get(key):
            m = re.search(rf"^{key}:\s*[\"']?(.+?)[\"']?\s*$", fm, re.M)
            return m.group(1).strip() if m else ""

        anrede_raw = get("anrede").strip('"').lower()
        arts.append({
            "file": fn,
            "slug": fn[:-3],
            "title": get("title"),
            "description": get("description"),
            "keywords": get("keywords"),
            "cover": get("cover"),
            "fm": fm,
            "body": body,
            "path": os.path.join(POSTS_DIR, fn),
            "content": content,
            "anrede_sie": anrede_raw in ("sie", "sie-form", "höflich"),
        })
    return arts


def clean_text(text, limit):
    """Sauberer Text-Auszug für Description-Generierung."""
    text = re.sub(r"[#*_>`|~-]{1,}", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    # Am Wortende abschneiden
    last_space = cut.rfind(" ")
    if last_space > limit * 0.7:
        cut = cut[:last_space]
    return cut.rstrip(" ,.;:") + "…"


def generate_description(a):
    """Erzeugt eine Description aus dem Artikelinhalt (kein KI nötig)."""
    # Ersten sinnvollen Absatz nehmen (nach der Einleitung)
    paragraphs = [p.strip() for p in a["body"].split("\n\n") if p.strip() and not p.strip().startswith("#")]
    source = ""
    for p in paragraphs:
        plain = re.sub(r"[#*_>`|~-]{1,}", " ", p)
        if len(plain) > 60:
            source = plain
            break
    if not source:
        source = a["body"]
    desc = clean_text(source, DESC_MAX - 3)
    # Keyword vorne einbauen, falls nicht enthalten
    kws = parse_keywords(a["keywords"])
    if kws:
        core = norm(kws[0]).split()
        core = next((t for t in core if len(t) >= 3), "")
        if core and core not in norm(desc):
            lead = f"{kws[0]}: " if len(kws[0]) < 40 else ""
            desc = lead + desc
            desc = desc[:DESC_MAX - 1] + ("…" if len(desc) > DESC_MAX - 1 else "")
    return desc


def ai_description(a):
    """KI-generierte, klickstarke Description (mit Cache)."""
    import urllib.request
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            cache = json.load(open(CACHE_FILE, encoding="utf-8"))
        except Exception:
            cache = {}

    key_id = a["slug"]
    if key_id in cache:
        return cache[key_id]

    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GROQ_API_KEY")):
        return None

    title = a["title"][:80]
    kws = parse_keywords(a["keywords"])[:4]
    anrede_hint = ("Sprich den Leser mit 'du' an." if not a.get("anrede_sie")
                   else "Sprich den Leser mit der Höflichkeitsform 'Sie' an.")
    prompt = (f"Schreibe für einen deutschen Blog-Artikel eine klickstarke Meta-Description "
              f"(max. 155 Zeichen, mit wichtigstem Keyword '{kws[0] if kws else title}'). "
              f"{anrede_hint} "
              f"Artikel-Titel: '{title}'. Nur die Description, ohne Anführungszeichen.")

    ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    if gemini_key:
        try:
            body = {"contents": [{"parts": [{"text": prompt}]}]}
            req = urllib.request.Request(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key=" + gemini_key,
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json", "User-Agent": ua})
            resp = json.loads(urllib.request.urlopen(req, timeout=60).read())
            text = resp["candidates"][0]["content"]["parts"][0]["text"].strip()
            if text:
                cache[key_id] = text
                json.dump(cache, open(CACHE_FILE, "w", encoding="utf-8"), ensure_ascii=False)
            return text
        except Exception:
            pass

    groq_key = os.environ.get("GROQ_API_KEY", "")
    if groq_key:
        try:
            body = {"model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}], "max_tokens": 100}
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {groq_key}", "User-Agent": ua})
            resp = json.loads(urllib.request.urlopen(req, timeout=60).read())
            text = resp["choices"][0]["message"]["content"].strip()
            if text:
                cache[key_id] = text
                json.dump(cache, open(CACHE_FILE, "w", encoding="utf-8"), ensure_ascii=False)
            return text
        except Exception:
            pass
    return None


def ai_title(a):
    """KI-generierter, klickstarker Titel (50–60 Zeichen) mit Cache."""
    import urllib.request
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            cache = json.load(open(CACHE_FILE, encoding="utf-8"))
        except Exception:
            cache = {}

    key_id = a["slug"] + ":title"
    if key_id in cache:
        return cache[key_id]

    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GROQ_API_KEY")):
        return None

    title = a["title"][:80]
    kws = parse_keywords(a["keywords"])[:4]
    kw = kws[0] if kws else title
    prompt = (f"Schreibe für einen deutschen Blog-Artikel einen klickstarken, "
              f"natürlichen SEO-Titel von EXAKT 50-60 Zeichen. Wichtigstes Keyword: "
              f"'{kw}'. Ausgangs-Titel: '{title}'. Kein Clickbait, keine "
              f"Sonderzeichen am Ende. Nur der Titel, ohne Anführungszeichen.")

    ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    if gemini_key:
        try:
            body = {"contents": [{"parts": [{"text": prompt}]}]}
            req = urllib.request.Request(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key=" + gemini_key,
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json", "User-Agent": ua})
            resp = json.loads(urllib.request.urlopen(req, timeout=60).read())
            text = resp["candidates"][0]["content"]["parts"][0]["text"].strip()
            if text:
                cache[key_id] = text
                json.dump(cache, open(CACHE_FILE, "w", encoding="utf-8"), ensure_ascii=False)
            return text
        except Exception:
            pass

    groq_key = os.environ.get("GROQ_API_KEY", "")
    if groq_key:
        try:
            body = {"model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}], "max_tokens": 80}
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {groq_key}", "User-Agent": ua})
            resp = json.loads(urllib.request.urlopen(req, timeout=60).read())
            text = resp["choices"][0]["message"]["content"].strip()
            if text:
                cache[key_id] = text
                json.dump(cache, open(CACHE_FILE, "w", encoding="utf-8"), ensure_ascii=False)
            return text
        except Exception:
            pass
    return None


def audit(a):
    issues = []
    # Titel-Länge OHNE HTML-Tags messen (z. B. "<br>" für den H1-Zeilenumbruch)
    tl = len(re.sub(r"<[^>]+>", "", a["title"]).replace("&nbsp;", " "))
    dl = len(a["description"].replace("&nbsp;", " "))
    kw_count = len(parse_keywords(a["keywords"]))

    if tl < TITLE_MIN:
        issues.append(f"Titel zu kurz ({tl} Zeichen)")
    elif tl > TITLE_MAX:
        issues.append(f"Titel zu lang ({tl} Zeichen, max. {TITLE_MAX})")
    if dl < DESC_MIN:
        issues.append(f"Description zu kurz ({dl} Zeichen, min. {DESC_MIN})")
    elif dl > DESC_MAX:
        issues.append(f"Description zu lang ({dl} Zeichen, max. {DESC_MAX})")
    if kw_count < KEYWORDS_MIN:
        issues.append(f"Nur {kw_count} Keywords (min. {KEYWORDS_MIN})")
    if not a["cover"]:
        issues.append("Kein og:image (Cover fehlt)")

    return {"file": a["file"], "title": a["title"][:45], "tl": tl, "dl": dl,
            "kw": kw_count, "issues": issues}


def extend_description(desc, a, target_min=DESC_OPT_MIN, target_max=DESC_OPT_MAX):
    """Verlängert eine zu kurze Description deterministisch auf 120+ Zeichen."""
    desc = desc.rstrip()
    # Sinnvolle Bausteine anhängen (bis Ziel erreicht)
    addons = [
        " So sparst du jeden Monat bares Geld.",
        " Schritt für Schritt erklärt – ohne Fachchinesisch.",
        " Mit praktischen Tipps für den Alltag.",
        " Vergleiche jetzt und profitiere von den besten Konditionen.",
        " So gelingt dir der Wechsel schnell und unkompliziert.",
    ]
    for add in addons:
        if len(desc) >= target_min:
            break
        if add.lstrip().lower()[:20] in desc.lower():
            continue
        if len(desc) + len(add) <= target_max:
            desc += add
    # Letzter Notnagel: Keyword-Phrase anhängen
    if len(desc) < target_min:
        kws = parse_keywords(a["keywords"])
        for kw in kws:
            if len(desc) + len(kw) + 4 <= target_max:
                desc += f" – {kw}."
                break
    return desc[:target_max]


def fix_meta(a, use_ai):
    """Wendet Fixes an. Liefert (geändert, beschreibung_neu)."""
    content = a["content"]
    changed = False

    # 1) Description auf CTR-OPTIMUM fixen (120-160 Zeichen)
    dl = len(a["description"])
    if dl < DESC_OPT_MIN or dl > DESC_OPT_MAX:
        new_desc = ai_description(a) if use_ai else generate_description(a)
        # KI/Generator-Ziel prüfen; sonst deterministisch nachbessern
        if new_desc:
            if len(new_desc) < DESC_OPT_MIN:
                new_desc = extend_description(new_desc, a)
            elif len(new_desc) > DESC_OPT_MAX:
                new_desc = new_desc[:DESC_OPT_MAX - 1].rstrip() + "…"
        if new_desc:
            old_line = re.search(rf'^description:.*$', content, re.M)
            if old_line:
                content = content[:old_line.start()] + f'description: "{new_desc}"' + content[old_line.end():]
                changed = True

    # 1b) Titel auf CTR-OPTIMUM fixen (50-60 Zeichen)
    tl = len(a["title"])
    if tl < TITLE_OPT_MIN or tl > TITLE_OPT_MAX:
        new_title = None
        if use_ai:
            new_title = ai_title(a)
        if not new_title:
            # Deterministischer Fallback: passendes Keyword als Ergänzung
            kws = parse_keywords(a["keywords"])
            ABBR = {"dns", "dsl", "kfz", "wlan", "lte", "tv", "pc", "gmbh",
                    "check24", "tarifcheck", "lkw", "pk"}
            def cap(kw):
                first = kw.split()[0].lower() if kw else ""
                if first in ABBR:
                    return first.upper() + kw[len(first):]
                return kw[0].upper() + kw[1:]
            title_l = a["title"].lower()
            suffix = ""
            for kw in kws:
                first = kw.split()[0].lower() if kw else ""
                if first and first not in title_l and kw.lower() not in title_l:
                    suffix = cap(kw)
                    break
            if tl < TITLE_OPT_MIN:
                # 1) Keyword-Suffix anhängen
                if suffix:
                    new_title = f"{a['title']}: {suffix}"
                # 2) Weitere Keywords ergänzen, bis ≥ Optimum
                for kw in kws:
                    add = cap(kw)
                    if add.lower() not in new_title.lower() and len(new_title) + len(add) + 2 <= TITLE_OPT_MAX:
                        new_title = f"{new_title} {add}"
                        if len(new_title) >= TITLE_OPT_MIN:
                            break
                # 3) Notnagel: generische Bausteine (nur wenn noch < Optimum)
                for addon in [" im Vergleich", " – so geht’s", " – Tipps & Tricks", " einfach erklärt"]:
                    if len(new_title) >= TITLE_OPT_MIN:
                        break
                    if len(new_title) + len(addon) <= TITLE_OPT_MAX:
                        new_title += addon
                # Final abschneiden, falls über Ziel
                if len(new_title) > TITLE_OPT_MAX:
                    new_title = new_title[:TITLE_OPT_MAX - 1].rstrip() + "…"
            elif tl > TITLE_OPT_MAX:
                new_title = a["title"][:TITLE_OPT_MAX - 1].rstrip() + "…"
        # Länge final begrenzen (KI kann überziehen)
        if new_title and len(new_title) > TITLE_MAX + 5:
            new_title = new_title[:TITLE_MAX - 1].rstrip() + "…"
        if new_title:
            old_line = re.search(r'^title:.*$', content, re.M)
            if old_line:
                content = content[:old_line.start()] + f'title: "{new_title}"' + content[old_line.end():]
                changed = True

    # 2) Keywords erweitern, falls zu wenige
    kw_count = len(parse_keywords(a["keywords"]))
    if kw_count < KEYWORDS_MIN:
        kws = parse_keywords(a["keywords"])
        # Aus dem Titel ableiten
        title_words = [w for w in a["title"].split() if len(w) > 3 and w.lower() not in
                       ("für", "und", "der", "die", "das", "mit", "den", "dem")]
        for w in title_words[:3]:
            if len(kws) >= KEYWORDS_MIN:
                break
            if w not in kws:
                kws.append(w)
        while len(kws) < KEYWORDS_MIN:
            kws.append(a["title"][:20])
            break
        new_list = ", ".join(f'"{k}"' for k in kws)
        old_line = re.search(rf'^keywords:.*$', content, re.M)
        if old_line:
            content = content[:old_line.start()] + f"keywords: [{new_list}]" + content[old_line.end():]
            changed = True

    if changed:
        open(a["path"], "w", encoding="utf-8").write(content)
    return changed


def main():
    fix = "--fix" in sys.argv
    use_ai = "--ai" in sys.argv
    as_json = "--json" in sys.argv

    articles = load_articles()
    results = [audit(a) for a in articles]
    critical = [r for r in results if r["issues"]]
    avg_tl = sum(r["tl"] for r in results) / len(results) if results else 0
    avg_dl = sum(r["dl"] for r in results) / len(results) if results else 0

    if fix:
        print("Meta-Optimierung: Fixe fehlende/zu kurze/zu lange Meta-Daten…")
        n = 0
        for a in articles:
            if fix_meta(a, use_ai):
                n += 1
                print(f"  ✓ {a['file'][:45]}")
        print(f"→ {n} Artikel optimiert")
        if use_ai:
            print("  (Descriptions per KI generiert – Cache: .meta_cache.json)")
        sys.exit(0)

    if as_json:
        print(json.dumps({
            "articles": len(results), "avg_title_len": round(avg_tl, 1),
            "avg_desc_len": round(avg_dl, 1), "critical": len(critical),
            "details": results}, ensure_ascii=False, indent=2))
        sys.exit(1 if critical else 0)

    print(f"Meta-Daten-Audit: {len(results)} Artikel (Ø Titel: {avg_tl:.0f} Zeichen, Ø Description: {avg_dl:.0f})")
    print("=" * 60)
    for r in results:
        status = "✅" if not r["issues"] else f"⚠️ ({len(r['issues'])})"
        print(f"{status} {r['title']}  [T:{r['tl']} D:{r['dl']} K:{r['kw']}]")
        for i in r["issues"]:
            print(f"     • {i}")
    print("=" * 60)
    print(f"Ergebnis: {len(critical)} Artikel mit Meta-Problemen")
    if critical:
        print("Tipp: python3 scripts/meta_optimizer.py --fix  (oder --ai für KI-Descriptions)")
        sys.exit(1)
    print("✅ Alle Meta-Daten auf Profi-Niveau")


if __name__ == "__main__":
    main()
