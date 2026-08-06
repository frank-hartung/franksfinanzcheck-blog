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

        title = get("title")
        desc = get("description")
        kw_raw = get("keywords")
        kws = [k.strip() for k in kw_raw.split(",") if k.strip()]
        arts.append({
            "file": fn,
            "slug": fn[:-3],
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
            "issues": issues, "density": round(density * 100, 2)}


def ai_suggest(main_kw):
    """Optional: verwandte Keywords per Gemini/Groq vorschlagen."""
    import urllib.request

    prompt = (f"Gib für das Haupt-Keyword '{main_kw}' eines deutschen Finanz-/Spar-Blogs "
              f"genau 5 verwandte Suchbegriffe (LSI-Keywords) zurück – nur die Begriffe, "
              f"durch Komma getrennt, ohne Einleitung.")

    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    if gemini_key:
        try:
            body = {"contents": [{"parts": [{"text": prompt}]}]}
            req = urllib.request.Request(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key=" + gemini_key,
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json",
                         "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/126.0"})
            resp = json.loads(urllib.request.urlopen(req, timeout=60).read())
            return resp["candidates"][0]["content"]["parts"][0]["text"]
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
                         "Authorization": f"Bearer {groq_key}",
                         "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/126.0"})
            resp = json.loads(urllib.request.urlopen(req, timeout=60).read())
            return resp["choices"][0]["message"]["content"]
        except Exception:
            pass
    return None


def main():
    as_json = "--json" in sys.argv
    with_ai = "--ai" in sys.argv

    articles = load_articles()
    results = [check_article(a) for a in articles]
    avg = sum(r["score"] for r in results) / len(results) if results else 0
    critical = [r for r in results if r["score"] < 60]

    if as_json:
        out = {"articles": len(results), "avg_score": round(avg, 1),
               "critical": len(critical), "details": results}
        if with_ai:
            for r in results:
                r["ai_keywords"] = ai_suggest(r.get("main_kw", ""))
        print(json.dumps(out, ensure_ascii=False, indent=2))
        sys.exit(1 if critical else 0)

    print(f"Keyword-Optimierung: {len(results)} Artikel (Ø-Score: {avg:.0f}/100)\n")
    for r in sorted(results, key=lambda x: x["score"]):
        flag = "✅" if r["score"] >= 80 else ("⚠️" if r["score"] >= 60 else "❌")
        print(f"{flag} {r['score']:>3}/100  {r['title']}  (Dichte: {r['density']}%)")
        for i in r["issues"][:3]:
            print(f"      • {i}")
        if with_ai:
            sug = ai_suggest(r.get("main_kw", ""))
            if sug:
                print(f"      💡 LSI: {sug[:120]}")

    print(f"\nErgebnis: {len(critical)} Artikel unter 60 Punkten (kritisch)")
    if critical:
        sys.exit(1)
    print("✅ Alle Artikel keyword-optimiert auf Profi-Niveau")


if __name__ == "__main__":
    main()
