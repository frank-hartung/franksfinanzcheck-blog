#!/usr/bin/env python3
"""
Professionelle Keyword-Optimierung (automatisch, kostenlos).

Ebene 1 – AUDIT bestehender Artikel (On-Page-Keyword-Checks):
  Für jeden Artikel (Haupt-Keyword = erstes Keyword im Frontmatter):
    ✅ Keyword im Titel?
    ✅ Keyword in der Meta-Description?
    ✅ Keyword im ersten Absatz (erste 150 Zeichen)?
    ✅ Keyword in mind. einer H2/H3-Überschrift?
    ✅ Keyword im URL-Slug?
    ✅ Keyword-Dichte (0,3% - 3,0% = optimal)
  → Score 0-100 pro Artikel, Gesamt-Report, Exit-Code für CI

Ebene 2 – KI-Keyword-Vorschläge (optional, falls GEMINI_API_KEY/GROQ_API_KEY
  gesetzt ist): schlägt 3-5 verwandte Keywords (LSI) pro Artikel vor.

Nutzung:
    python3 scripts/keyword_optimizer.py            # Audit
    python3 scripts/keyword_optimizer.py --json     # JSON-Report
    python3 scripts/keyword_optimizer.py --ai       # + KI-Vorschläge

Exit-Code: 0 = ok, 1 = Artikel mit kritischen Keyword-Lücken
"""
import json
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
from post_utils import list_post_paths, slug_of  # noqa: E402
import groq_config  # noqa: E402

DENSITY_MIN = 0.003
DENSITY_MAX = 0.03


def norm(s):
    s = s.lower()
    s = re.sub(r"[äàáâ]", "ae", s)
    s = re.sub(r"[öòóô]", "oe", s)
    s = re.sub(r"[üùúû]", "ue", s)
    s = re.sub(r"ß", "ss", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def load_articles():
    """Page-Bundles + Legacy – alle veröffentlichten Artikel."""
    arts = []
    for path in list_post_paths():
        content = open(path, encoding="utf-8").read()
        parts = content.split("---", 2)
        fm = parts[1] if len(parts) > 1 else ""
        body = parts[2] if len(parts) == 3 else content
        if "draft: true" in fm:
            continue

        def get(key):
            m = re.search(rf"^{key}:\s*[\"']?(.+?)[\"']?\s*$", fm, re.M)
            return m.group(1).strip() if m else ""

        title = get("title")
        desc = get("description")
        kw_m = re.search(r"^keywords:\s*\[(.*?)\]", fm, re.M)
        if kw_m:
            kws = [k.strip().strip("\"'") for k in kw_m.group(1).split(",") if k.strip()]
        else:
            kws = [k.strip().strip("\"'") for k in get("keywords").split(",") if k.strip()]
        slug = slug_of(path)
        arts.append({
            "file": slug + ".md",
            "path": path,
            "slug": slug,
            "title": title,
            "description": desc,
            "keywords": kws,
            "body": body,
        })
    return arts


def check_article(a):
    checks = {}
    main_kw = a["keywords"][0] if a["keywords"] else None
    words = re.findall(r"\w+", a["body"])
    total = len(words)

    if not main_kw:
        return {"file": a["file"], "title": a["title"][:45], "score": 0,
                "issues": ["Kein Keyword im Frontmatter"], "density": 0}

    nk = norm(main_kw)
    nt = norm(a["title"])
    nd = norm(a["description"])
    nb = norm(a["body"])
    nslug = norm(a["slug"])
    first_200 = norm(a["body"][:250])

    # Kern-Token des Keywords (erstes aussagekräftiges Wort, min. 3 Buchstaben)
    core = next((t for t in nk.split() if len(t) >= 3), nk)

    def has_kw(text):
        """Stamm-Matching: 'günstig' erkennt auch 'günstige', 'günstiger'."""
        if nk in text:
            return True
        for w in text.split():
            if w == core or w.startswith(core):
                return True
            # Auch umgekehrt: Kern "günstige" erkennt "günstig" (min. 4 Buchst.)
            if len(w) >= 4 and core.startswith(w):
                return True
        return False

    checks["Titel"] = has_kw(nt)
    checks["Description"] = has_kw(nd)
    checks["Erster Absatz"] = has_kw(first_200)
    checks["Überschrift (H2/H3)"] = any(
        has_kw(norm(h)) for h in re.findall(r"^#{2,3}\s+(.+)$", a["body"], re.M))
    checks["URL-Slug"] = has_kw(nslug)

    # Dichte: ganze Keyword-Phrase + Kern-Token zählen (realistisch)
    count = nb.count(nk) + nb.count(core)
    density = count / total if total else 0
    checks["Dichte"] = DENSITY_MIN <= density <= DENSITY_MAX

    score = sum(1 for v in checks.values() if v) / len(checks) * 100
    issues = [f"Keyword nicht in: {k}" for k, v in checks.items() if not v]
    if density > DENSITY_MAX:
        issues.append(f"Keyword-Dichte zu hoch ({density*100:.2f}%)")
    elif density < DENSITY_MIN:
        issues.append(f"Keyword-Dichte sehr niedrig ({density*100:.2f}%)")

    return {"file": a["file"], "title": a["title"][:45], "score": round(score),
            "issues": issues, "density": round(density * 100, 2),
            "main_kw": main_kw, "keywords": a["keywords"]}


CACHE_FILE = os.path.join(BLOG_DIR, ".keyword_suggestions.json")


def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1)


def _call_ai(prompt):
    """Ruft Gemini (bevorzugt) oder Groq auf. Liefert Antworttext oder None."""
    import urllib.request

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
            return resp["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            pass

    if groq_config.available():
        try:
            return groq_config.chat(prompt, max_tokens=200, timeout=60)
        except Exception:
            pass
    return None


def ai_suggest(main_kw):
    """Liefert 5 verwandte LSI-Keywords per KI (mit Cache)."""
    cache = load_cache()
    if main_kw in cache:
        return cache[main_kw]

    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GROQ_API_KEY")):
        return None

    prompt = (f"Für das Haupt-Keyword '{main_kw}' eines deutschen Finanz-/Spar-Blogs: "
              f"nenne genau 5 verwandte Suchbegriffe (LSI-Keywords), die Nutzer zusätzlich "
              f"googeln. Antwort: NUR die 5 Begriffe, durch Komma getrennt, "
              f"ohne Nummerierung und ohne Einleitung.")

    raw = _call_ai(prompt)
    if not raw:
        return None

    # Bereinigen: nur die Begriffe extrahieren
    import re as _re
    parts = [p.strip().strip("\"\"'") for p in _re.split(r"[,\n;]", raw) if p.strip()]
    # Nummerierungen entfernen ("1. ", "1)", "- ")
    parts = [_re.sub(r"^[\d\-\*\.\s\)]+", "", p).strip() for p in parts]
    parts = [p for p in parts if p and len(p) > 2]
    result = parts[:5]

    if result:
        cache[main_kw] = result
        save_cache(cache)
    return result


def apply_suggestions(articles, suggestions):
    """Fügt bis zu 2 neue LSI-Keywords ins Frontmatter ein (echte Optimierung)."""
    applied = 0
    for a in articles:
        kw = a.get("main_kw")
        if not kw or kw not in suggestions:
            continue
        existing = [norm(k) for k in a["keywords"]]
        new_kws = [k for k in suggestions[kw] if norm(k) not in existing and norm(k) != norm(kw)]
        to_add = new_kws[:2]
        if not to_add:
            continue
        fn = a.get("path") or os.path.join(POSTS_DIR, a["file"])
        content = open(fn, encoding="utf-8").read()
        # Keywords-Liste im Frontmatter erweitern
        import re as _re
        m = _re.search(r"^keywords:\s*\[(.+?)\]", content, _re.M)
        if m:
            old_list = m.group(1)
            new_items = ", ".join(f'"{k}"' for k in to_add)
            content = content[:m.start()] + f"keywords: [{old_list}, {new_items}]" + content[m.end():]
            open(fn, "w", encoding="utf-8").write(content)
            applied += 1
            print(f"  ✓ {a['file'][:40]}: +{', '.join(to_add)}")
    return applied


def main():
    as_json = "--json" in sys.argv
    with_ai = "--ai" in sys.argv
    apply = "--apply" in sys.argv

    articles = load_articles()
    results = [check_article(a) for a in articles]
    avg = sum(r["score"] for r in results) / len(results) if results else 0
    critical = [r for r in results if r["score"] < 60]

    # KI-Vorschläge einmal sammeln (mit Cache, nur fehlende werden angefragt)
    suggestions = {}
    if with_ai:
        print("⏳ KI-Keyword-Vorschläge werden generiert (einmalig pro Keyword, gecacht)…")
        for r in results:
            kw = r.get("main_kw")
            if kw:
                suggestions[kw] = ai_suggest(kw)
        generated = sum(1 for v in suggestions.values() if v)
        print(f"   → {generated} Keyword-Vorschläge generiert/geladen")
        if apply:
            print("\n📝 Wende LSI-Keywords auf Artikel an:")
            n = apply_suggestions(results, suggestions)
            print(f"   → {n} Artikel um LSI-Keywords erweitert\n")

    if as_json:
        out = {"articles": len(results), "avg_score": round(avg, 1),
               "critical": len(critical), "details": results,
               "suggestions": suggestions}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        sys.exit(1 if critical else 0)

    print(f"Keyword-Optimierung: {len(results)} Artikel (Ø-Score: {avg:.0f}/100)\n")
    for r in sorted(results, key=lambda x: x["score"]):
        flag = "✅" if r["score"] >= 80 else ("⚠️" if r["score"] >= 60 else "❌")
        print(f"{flag} {r['score']:>3}/100  {r['title']}  (Dichte: {r['density']}%)")
        for i in r["issues"][:3]:
            print(f"      • {i}")
        kw = r.get("main_kw")
        if kw and suggestions.get(kw):
            print(f"      💡 LSI: {', '.join(suggestions[kw])}")

    print(f"\nErgebnis: {len(critical)} Artikel unter 60 Punkten (kritisch)")
    if critical:
        sys.exit(1)
    print("✅ Alle Artikel keyword-optimiert auf Profi-Niveau")


if __name__ == "__main__":
    main()
