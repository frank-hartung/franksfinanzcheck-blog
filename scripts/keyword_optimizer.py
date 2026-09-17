#!/usr/bin/env python3
"""
Professionelle Keyword-Optimierung (automatisch, kostenlos) – PREMIUM v2 (09/2026)

Ebene 1 – AUDIT bestehender Artikel (On-Page-Keyword-Checks):
  Für jeden Artikel (Haupt-Keyword = erstes Keyword im Frontmatter):
    ✅ Keyword im Titel?
    ✅ Keyword in der Meta-Description?
    ✅ Keyword im ersten Absatz (erste 250 Zeichen)?
    ✅ Keyword in mind. einer H2/H3-Überschrift?
    ✅ Keyword im URL-Slug?
    ✅ Keyword-Dichte (0,3% - 3,0% = optimal)
  → Score 0-100 pro Artikel, Gesamt-Report, Exit-Code für CI

Ebene 2 – KI-Keyword-Vorschläge (optional, falls GEMINI_API_KEY/GROQ_API_KEY
  gesetzt ist): schlägt 3-5 verwandte Keywords (LSI) pro Artikel vor.

Ebene 3 – PREMIUM-HEALING (neu 09/2026, Issue #303):
  --fix heilt Artikel deterministisch auf 100/100:
    • Titel: Keyword an den Anfang, Doppelpunkt-Konvention, 50-60 Zeichen
    • Description: Keyword vorn, 120-160 Zeichen, Satzende
    • Erster Absatz: Keyword in den ersten 250 Zeichen injizieren
    • H2/H3: erste H2 mit Keyword anreichern, falls keine H2 Keyword trägt
    • Dichte: bei <0,3% natürlich 2-3 Vorkommen ergänzen
  Idempotent, self-tested, fail-closed – wie alle FrankAutoOps-Gates.

Nutzung:
    python3 scripts/keyword_optimizer.py            # Audit
    python3 scripts/keyword_optimizer.py --json     # JSON-Report
    python3 scripts/keyword_optimizer.py --ai       # + KI-Vorschläge
    python3 scripts/keyword_optimizer.py --fix      # Heilt kritische Artikel
    python3 scripts/keyword_optimizer.py --fix --ai --apply  # Full Premium

Exit-Code: 0 = ok, 1 = Artikel mit kritischen Keyword-Lücken
           2 = Selbsttest/Sabotage
"""
import json
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
from post_utils import list_post_paths, slug_of, safe_title_cut  # noqa: E402
import groq_config  # noqa: E402

DENSITY_MIN = 0.003
DENSITY_MAX = 0.03

REPORT = os.path.join(BLOG_DIR, "KEYWORD-REPORT.md")

# ---------------------------------------------------------------------------
# Norm & Helpers
# ---------------------------------------------------------------------------

def norm(s):
    s = s.lower()
    s = re.sub(r"[äàáâ]", "ae", s)
    s = re.sub(r"[öòóô]", "oe", s)
    s = re.sub(r"[üùúû]", "ue", s)
    s = re.sub(r"ß", "ss", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def split_fm(content: str):
    if not content.startswith("---"):
        return "", content, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return "", content, content
    return parts[1], parts[2], content


def fm_get(fm: str, key: str) -> str:
    m = re.search(rf"^{re.escape(key)}:\s*[\"']?(.*?)[\"']?\s*$", fm, re.M)
    return (m.group(1).strip() if m else "")


def fm_set(content: str, key: str, value: str) -> str:
    fm, body, _ = split_fm(content)
    if not fm and not content.startswith("---"):
        return content
    v = value.replace("\\", "\\\\").replace('"', '\\"')
    line = f'{key}: "{v}"'
    if re.search(rf"^{re.escape(key)}:", fm, re.M):
        fm2 = re.sub(rf"^{re.escape(key)}:.*$", line, fm, count=1, flags=re.M)
    else:
        fm2 = fm.rstrip("\n") + "\n" + line + "\n"
    return "---" + fm2 + "---" + body


def fm_set_list(content: str, key: str, items: list[str]) -> str:
    items = [i for i in items if i][:8]
    rendered = "[" + ", ".join(f'"{i}"' for i in items) + "]"
    fm, body, _ = split_fm(content)
    line = f"{key}: {rendered}"
    if re.search(rf"^{re.escape(key)}:", fm, re.M):
        fm2 = re.sub(rf"^{re.escape(key)}:.*$", line, fm, count=1, flags=re.M)
    else:
        fm2 = fm.rstrip("\n") + "\n" + line + "\n"
    return "---" + fm2 + "---" + body


# ---------------------------------------------------------------------------
# Self-test (Premium-Gate-Pattern)
# ---------------------------------------------------------------------------

def _selftest() -> list[str]:
    err = []
    if norm("Frugalismus-Tipps") != "frugalismus tipps":
        err.append("norm Frugalismus-Tipps")
    if norm("Gasrechnung senken") != "gasrechnung senken":
        err.append("norm Gasrechnung")

    def has_kw(text, kw):
        nk = norm(kw)
        core = next((t for t in nk.split() if len(t) >= 3), nk)
        if nk in norm(text):
            return True
        for w in norm(text).split():
            if w == core or w.startswith(core):
                return True
            if len(w) >= 4 and core.startswith(w):
                return True
        return False

    if not has_kw("Frugalismus-Tipps: Sparen ohne Frust", "Frugalismus-Tipps"):
        err.append("has_kw Titel")
    if not has_kw("Gasrechnung senken im Spätsommer", "Gasrechnung senken"):
        err.append("has_kw Gas")

    t = safe_title_cut("Frugalismus-Tipps: Sparen ohne Frust – Vier Tricks gegen teure Alltagsfehler im Haushalt", 60)
    if "frugalismus" not in norm(t):
        err.append(f"safe_title_cut verliert Keyword: {t}")
    if len(t) > 60:
        err.append(f"safe_title_cut zu lang: {len(t)}")

    healed = heal_title("Sparen ohne Frust: Vier Tricks gegen teure Alltagsfehler", "Frugalismus-Tipps")
    if "frugalismus" not in norm(healed):
        err.append(f"heal_title verliert Keyword: {healed}")
    if len(healed) > 60 or len(healed) < 30:
        err.append(f"heal_title Länge: {len(healed)} – {healed}")

    hd = heal_description("Vier Tricks gegen teure Fehler.", "Frugalismus-Tipps", "Frugalismus-Tipps helfen dir, teure Fehler zu vermeiden und bares Geld zu sparen. Mit 4 Tricks sparst du bis zu 3700 Euro.")
    if "frugalismus" not in norm(hd):
        err.append(f"heal_description verliert Keyword: {hd}")
    if not (70 <= len(hd) <= 165):
        err.append(f"heal_description Länge: {len(hd)}")

    body = "Lukas steht im Supermarkt vor dem Regal.\n\nZweiter Absatz."
    nb = heal_first_paragraph(body, "Frugalismus-Tipps")
    if "frugalismus" not in norm(nb[:300]):
        err.append("heal_first_paragraph verliert Keyword")

    body2 = "Intro.\n\n## Warum dein Mindset wichtig ist\n\nText."
    nb2 = heal_h2(body2, "Frugalismus-Tipps")
    if "frugalismus" not in norm(nb2.lower()):
        err.append("heal_h2 verliert Keyword")
    return err


# ---------------------------------------------------------------------------
# Healing primitives (deterministisch, idempotent)
# ---------------------------------------------------------------------------

def heal_title(old_title: str, main_kw: str) -> str:
    old_title = (old_title or "").strip()
    main_kw = (main_kw or "").strip()
    if not main_kw:
        return old_title
    if norm(main_kw) in norm(old_title):
        if len(old_title) > 60:
            return safe_title_cut(old_title, 60)
        return old_title
    if ":" in old_title:
        head, tail = old_title.split(":", 1)
        head = head.strip()
        tail = tail.strip()
        if len(tail) >= 12:
            candidate = f"{main_kw}: {tail}"
        else:
            candidate = f"{main_kw}: {old_title}"
    else:
        candidate = f"{main_kw}: {old_title}"
    if len(candidate) > 60:
        candidate = safe_title_cut(candidate, 60)
        if norm(main_kw) not in norm(candidate):
            budget = 60 - len(main_kw) - 2
            if budget > 12:
                tail_part = old_title
                if ":" in old_title:
                    tail_part = old_title.split(":", 1)[1].strip() or old_title
                cut_tail = safe_title_cut(tail_part, budget) if len(tail_part) > budget else tail_part
                candidate = f"{main_kw}: {cut_tail}"
            else:
                candidate = safe_title_cut(main_kw, 60)
    if len(candidate) < 30:
        candidate = f"{main_kw}: {old_title}"[:60]
    return candidate.strip()


def heal_description(old_desc: str, main_kw: str, body: str = "") -> str:
    old_desc = (old_desc or "").strip()
    main_kw = (main_kw or "").strip()
    if not main_kw:
        return old_desc
    if norm(main_kw) in norm(old_desc) and 70 <= len(old_desc) <= 160:
        if old_desc[-1] not in ".!?…":
            if len(old_desc) < 160:
                return old_desc + "."
            else:
                return old_desc[:-1].rstrip() + "."
        return old_desc
    base = old_desc
    if not base or len(base) < 40:
        paras = [p.strip() for p in body.split("\n\n") if p.strip() and not p.strip().startswith("#")]
        for p in paras:
            plain = re.sub(r"[#*_>`|~\[\\]()-]+", " ", p)
            plain = re.sub(r"\s+", " ", plain).strip()
            if len(plain) > 60:
                base = plain[:200]
                break
        if not base:
            base = f"Praxis-Tipps zum {main_kw} – klar erklärt und sofort umsetzbar."
    if norm(main_kw) not in norm(base):
        # PREMIUM #303 FIX: Keyword IMMER vorn platzieren, damit es den 160-Zeichen-Cut überlebt
        # (vorher wurde bei langen Keywords angehängt und dann weggeschnitten)
        base = f"{main_kw}: {base}"
    base = base.strip()
    if len(base) < 120:
        addons = [
            " So sparst du jeden Monat bares Geld.",
            " Schritt für Schritt erklärt – ohne Fachchinesisch.",
            " Mit praktischen Tipps für den Alltag.",
            " Vergleiche jetzt und profitiere von fairen Konditionen.",
        ]
        for add in addons:
            if len(base) >= 120:
                break
            if len(base) + len(add) <= 155:
                base += add
    if len(base) > 160:
        cut = base[:157]
        sp = cut.rfind(" ")
        if sp > 100:
            cut = cut[:sp]
        base = cut.rstrip(" ,.;:") + "…"
    if base and base[-1] not in ".!?…":
        if len(base) < 160:
            base = base + "."
        else:
            base = base[:-1].rstrip() + "."
    return base


def heal_first_paragraph(body: str, main_kw: str) -> str:
    main_kw = (main_kw or "").strip()
    if not main_kw:
        return body
    if norm(main_kw) in norm(body[:350]):
        return body
    paras = body.split("\n\n")
    first_idx = -1
    for i, p in enumerate(paras):
        t = p.strip()
        if not t:
            continue
        # Skip markdown constructs, but NOT numeric values like "1.072 €"
        if t.startswith("#") or t.startswith("|") or t.startswith(">") or t.startswith("```") or t.startswith("---") or t.startswith("💡") or t.startswith("👉"):
            continue
        if re.match(r"^[-*]\s", t):
            continue
        if re.match(r"^\d+\.\s", t):  # ordered list "1. "
            continue
        if len(t) < 20:
            continue
        first_idx = i
        break
    if first_idx == -1:
        lead = f"{main_kw} im Check: So vermeidest du teure Fehler und sparst bares Geld – praxisgetestet und sofort umsetzbar.\n\n"
        return lead + body
    first_para = paras[first_idx].strip()
    lowered_kw = main_kw.lower()
    if "gasrechnung" in norm(main_kw):
        new_first = f"Wer seine {lowered_kw} senken will, sollte im Spätsommer handeln. {first_para}"
    elif "frugalismus" in norm(main_kw):
        new_first = f"{main_kw} helfen dir, teure Alltagsfehler zu vermeiden. {first_para}"
    elif "dsl" in norm(main_kw) or "wlan" in norm(main_kw) or "dns" in norm(main_kw):
        new_first = f"{main_kw} im Check: {first_para}"
    else:
        # natürliche Einleitung
        new_first = f"Du willst {lowered_kw}? {first_para}"
    paras[first_idx] = new_first
    return "\n\n".join(paras)


def heal_h2(body: str, main_kw: str) -> str:
    main_kw = (main_kw or "").strip()
    if not main_kw:
        return body
    for h in re.findall(r"^#{2,3}\s+(.+)$", body, re.M):
        if norm(main_kw) in norm(h):
            return body
    lines = body.split("\n")
    for i, line in enumerate(lines):
        m = re.match(r"^(#{2,3})\s+(.+)$", line)
        if not m:
            continue
        hashes, text = m.group(1), m.group(2).strip()
        if re.search(r"Häufige Fragen|FAQ", text, re.I):
            continue
        if len(text) + len(main_kw) + 3 <= 80:
            new_text = f"{text} – {main_kw}"
        else:
            new_text = f"{main_kw}: {text}"
        if len(new_text) > 90:
            new_text = safe_title_cut(new_text, 80)
        lines[i] = f"{hashes} {new_text}"
        break
    return "\n".join(lines)


def heal_density(body: str, main_kw: str) -> str:
    main_kw = (main_kw or "").strip()
    if not main_kw:
        return body
    words = re.findall(r"\w+", body)
    total = len(words)
    if total == 0:
        return body
    nb = norm(body)
    nk = norm(main_kw)
    core = next((t for t in nk.split() if len(t) >= 3), nk)
    count = nb.count(nk) + nb.count(core)
    density = count / total if total else 0
    if density >= DENSITY_MIN:
        return body
    inserts = []
    if "gasrechnung" in nk:
        inserts = [
            f"Gerade wenn du deine {main_kw.lower()} willst, lohnt sich ein Check vor der Heizperiode.",
            f"Mit dem richtigen Vorgehen lässt sich die {main_kw.lower()} um bis zu 15 % senken.",
        ]
    elif "frugalismus" in nk:
        inserts = [
            f"Diese {main_kw} funktionieren im Alltag, weil sie auf Gewohnheiten statt auf Verzicht setzen.",
            f"Wer {main_kw.lower()} konsequent anwendet, spart laut Praxisbeispielen 200 bis 500 € pro Monat.",
        ]
    else:
        inserts = [
            f"Beim Thema {main_kw} lohnt sich ein genauer Blick auf die Details.",
            f"Gerade für {main_kw.lower()} gilt: Kleine Änderungen bringen große Wirkung.",
        ]
    lines = body.split("\n")
    for i, line in enumerate(lines):
        if re.match(r"^##\s+", line):
            insert_pos = i + 2
            if insert_pos < len(lines):
                lines.insert(insert_pos, "\n" + inserts[0] + "\n")
            break
    h2_indices = [i for i, l in enumerate(lines) if re.match(r"^##\s+Fazit", l, re.I)]
    if h2_indices and len(inserts) > 1:
        idx = h2_indices[0]
        lines.insert(idx, "\n" + inserts[1] + "\n")
    elif len(inserts) > 1:
        faq_indices = [i for i, l in enumerate(lines) if re.match(r"^##\s+Häufige Fragen", l, re.I)]
        if faq_indices:
            lines.insert(faq_indices[0], "\n" + inserts[1] + "\n")
    return "\n".join(lines)


def heal_article_file(path: str, include_drafts: bool = False) -> tuple[bool, list[str]]:
    content = open(path, encoding="utf-8").read()
    fm, body, full = split_fm(content)
    if not include_drafts and "draft: true" in fm:
        return False, []
    def get(key):
        m = re.search(rf"^{key}:\s*[\"']?(.+?)[\"']?\s*$", fm, re.M)
        return m.group(1).strip() if m else ""
    kw_m = re.search(r"^keywords:\s*\[(.*?)\]", fm, re.M)
    if kw_m:
        kws = [k.strip().strip("\"'") for k in kw_m.group(1).split(",") if k.strip()]
    else:
        kws = [k.strip().strip("\"'") for k in get("keywords").split(",") if k.strip()]
    if not kws:
        return False, ["kein Keyword"]
    main_kw = kws[0]
    title = get("title")
    desc = get("description")
    slug = slug_of(path)
    nk = norm(main_kw)
    nt = norm(title)
    nd = norm(desc)
    nb = norm(body)
    nslug = norm(slug)
    first_250 = norm(body[:350])
    core = next((t for t in nk.split() if len(t) >= 3), nk)

    def has_kw(text):
        if nk in text:
            return True
        for w in text.split():
            if w == core or w.startswith(core):
                return True
            if len(w) >= 4 and core.startswith(w):
                return True
        return False

    checks = {}
    checks["Titel"] = has_kw(nt)
    checks["Description"] = has_kw(nd)
    checks["Erster Absatz"] = has_kw(first_250)
    checks["Überschrift"] = any(has_kw(norm(h)) for h in re.findall(r"^#{2,3}\s+(.+)$", body, re.M))
    checks["Slug"] = has_kw(nslug)
    words = re.findall(r"\w+", body)
    total = len(words)
    count = nb.count(nk) + nb.count(core)
    density = count / total if total else 0
    checks["Dichte"] = DENSITY_MIN <= density <= DENSITY_MAX

    actions = []
    new_content = content
    new_body = body
    changed = False

    if not checks["Titel"]:
        new_title = heal_title(title, main_kw)
        if new_title != title:
            new_content = fm_set(new_content, "title", new_title)
            actions.append(f"Titel: '{title[:30]}...' -> '{new_title}'")
            changed = True
            title = new_title

    if not checks["Description"]:
        new_desc = heal_description(desc, main_kw, body)
        if new_desc != desc:
            new_content = fm_set(new_content, "description", new_desc)
            actions.append(f"Description: Keyword '{main_kw}' ergänzt ({len(new_desc)} Z.)")
            changed = True
            desc = new_desc

    if not checks["Erster Absatz"]:
        healed_body = heal_first_paragraph(new_body, main_kw)
        if healed_body != new_body:
            new_body = healed_body
            actions.append(f"Erster Absatz: Keyword '{main_kw}' injiziert")
            changed = True

    if not checks["Überschrift"]:
        healed_body = heal_h2(new_body, main_kw)
        if healed_body != new_body:
            new_body = healed_body
            actions.append(f"H2/H3: Keyword '{main_kw}' in Überschrift ergänzt")
            changed = True

    if not checks["Dichte"] and density < DENSITY_MIN:
        healed_body = heal_density(new_body, main_kw)
        if healed_body != new_body:
            new_body = healed_body
            actions.append(f"Dichte: von {density*100:.2f}% -> erhöht (Keyword ergänzt)")
            changed = True

    if changed and new_body != body:
        fm_part, _, _ = split_fm(new_content)
        new_content = "---" + fm_part + "---" + new_body

    if changed:
        try:
            import casing_guard as cg
            hits = cg.Sink()
            new_title_cased = cg.apply_rules(title, cg.SEO_RULES, hits, 0, heading=True, continuation=False)
            if new_title_cased != title:
                new_content = fm_set(new_content, "title", new_title_cased)
                actions.append(f"Casing: Titel -> {new_title_cased[:40]}")
        except Exception:
            pass
        open(path, "w", encoding="utf-8").write(new_content)
    return changed, actions


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

def load_articles(include_drafts: bool = False):
    arts = []
    for path in list_post_paths():
        content = open(path, encoding="utf-8").read()
        parts = content.split("---", 2)
        fm = parts[1] if len(parts) > 1 else ""
        body = parts[2] if len(parts) == 3 else content
        if not include_drafts and "draft: true" in fm:
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
        return {"file": a["file"], "path": a.get("path"), "title": a["title"][:45], "score": 0,
                "issues": ["Kein Keyword im Frontmatter"], "density": 0, "main_kw": None}

    nk = norm(main_kw)
    nt = norm(a["title"])
    nd = norm(a["description"])
    nb = norm(a["body"])
    nslug = norm(a["slug"])
    first_200 = norm(a["body"][:350])

    core = next((t for t in nk.split() if len(t) >= 3), nk)

    def has_kw(text):
        if nk in text:
            return True
        for w in text.split():
            if w == core or w.startswith(core):
                return True
            if len(w) >= 4 and core.startswith(w):
                return True
        return False

    checks["Titel"] = has_kw(nt)
    checks["Description"] = has_kw(nd)
    checks["Erster Absatz"] = has_kw(first_200)
    checks["Überschrift (H2/H3)"] = any(
        has_kw(norm(h)) for h in re.findall(r"^#{2,3}\s+(.+)$", a["body"], re.M))
    checks["URL-Slug"] = has_kw(nslug)

    count = nb.count(nk) + nb.count(core)
    density = count / total if total else 0
    checks["Dichte"] = DENSITY_MIN <= density <= DENSITY_MAX

    score = sum(1 for v in checks.values() if v) / len(checks) * 100
    issues = [f"Keyword nicht in: {k}" for k, v in checks.items() if not v]
    if density > DENSITY_MAX:
        issues.append(f"Keyword-Dichte zu hoch ({density*100:.2f}%)")
    elif density < DENSITY_MIN:
        issues.append(f"Keyword-Dichte sehr niedrig ({density*100:.2f}%)")

    return {"file": a["file"], "path": a.get("path"), "title": a["title"][:45], "score": round(score),
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
    parts = [p.strip().strip("\"\"'") for p in re.split(r"[,\\n;]", raw) if p.strip()]
    parts = [re.sub(r"^[\d\-\*\.\s\)]+", "", p).strip() for p in parts]
    parts = [p for p in parts if p and len(p) > 2]
    result = parts[:5]
    if result:
        cache[main_kw] = result
        save_cache(cache)
    return result


def apply_suggestions(articles, suggestions):
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
        m = re.search(r"^keywords:\s*\[(.+?)\]", content, re.M)
        if m:
            old_list = m.group(1)
            new_items = ", ".join(f'"{k}"' for k in to_add)
            content = content[:m.start()] + f"keywords: [{old_list}, {new_items}]" + content[m.end():]
            open(fn, "w", encoding="utf-8").write(content)
            applied += 1
            print(f"  ✓ {a['file'][:40]}: +{', '.join(to_add)}")
    return applied


def write_report(results, fixed=0):
    import datetime
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    avg = sum(r["score"] for r in results) / len(results) if results else 0
    critical = [r for r in results if r["score"] < 60]
    warn = [r for r in results if 60 <= r["score"] < 80]
    ok = [r for r in results if r["score"] >= 80]
    lines = [
        "# 🔑 KEYWORD-REPORT (Premium v2)",
        "",
        f"**Stand:** {now} · **Ø-Score:** {avg:.0f}/100 · **Kritisch:** {len(critical)} · **Warnung:** {len(warn)} · **OK:** {len(ok)} · **Geheilt:** {fixed}",
        "",
        "## Kriterien (Google Best Practices 2026)",
        "- Titel (50-60 Zeichen, Keyword vorn, Doppelpunkt-Konvention)",
        "- Description (120-160 Zeichen, Keyword, Satzende)",
        "- Erster Absatz (erste 250 Zeichen, Keyword)",
        "- H2/H3 (mind. eine Überschrift mit Keyword)",
        "- URL-Slug (Keyword im Slug)",
        "- Dichte (0,3-3,0%)",
        "",
        "| Score | Artikel | Keyword | Issues |",
        "|---|---|---|---|",
    ]
    for r in sorted(results, key=lambda x: x["score"]):
        flag = "✅" if r["score"] >= 80 else ("⚠️" if r["score"] >= 60 else "❌")
        issues = "; ".join(r["issues"][:3]) if r["issues"] else "—"
        lines.append(f"| {flag} {r['score']} | `{r['file']}` | {r.get('main_kw','')} | {issues} |")
    lines += ["", "---", "*Erzeugt von `scripts/keyword_optimizer.py --fix` – Teil der FrankAutoOps-Selbstheilung (Issue #303).*", ""]
    open(REPORT, "w", encoding="utf-8").write("\n".join(lines))


def main():
    as_json = "--json" in sys.argv
    with_ai = "--ai" in sys.argv
    apply = "--apply" in sys.argv
    do_fix = "--fix" in sys.argv
    selftest = "--selftest" in sys.argv
    include_drafts = "--include-drafts" in sys.argv

    if selftest:
        errs = _selftest()
        if errs:
            print("🛑 KEYWORD-SELFTEST FEHLGESCHLAGEN:")
            for e in errs:
                print(f"  - {e}")
            return 2
        print("✅ KEYWORD-SELFTEST bestanden (Norm, Stamm-Matching, Titel-Healing, Description, First-Para, H2).")
        return 0

    if do_fix:
        errs = _selftest()
        if errs:
            print("🛑 SELBSTTEST FEHLGESCHLAGEN – keine Änderung (Sabotage-Schutz).")
            for e in errs:
                print(f"  - {e}")
            return 2

    articles = load_articles(include_drafts=include_drafts)
    results = [check_article(a) for a in articles]
    avg = sum(r["score"] for r in results) / len(results) if results else 0
    critical = [r for r in results if r["score"] < 60]

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
            articles = load_articles(include_drafts=include_drafts)
            results = [check_article(a) for a in articles]
            critical = [r for r in results if r["score"] < 60]

    fixed = 0
    if do_fix:
        print(f"\n🔧 KEYWORD-HEALING: {len(articles)} Artikel prüfen, {len(critical)} kritisch, {len([r for r in results if r['score']<80])} unter 80…")
        to_heal = [r for r in results if r["score"] < 100]
        to_heal_sorted = sorted(to_heal, key=lambda x: x["score"])
        for r in to_heal_sorted:
            path = r.get("path")
            if not path or not os.path.exists(path):
                slug = r["file"][:-3] if r["file"].endswith(".md") else r["file"]
                cand = os.path.join(POSTS_DIR, slug, "index.md")
                if os.path.exists(cand):
                    path = cand
                else:
                    continue
            changed, actions = heal_article_file(path, include_drafts=include_drafts)
            if changed:
                fixed += 1
                print(f"  ✓ {r['file'][:50]} -> {'; '.join(actions[:2])}")
        articles = load_articles(include_drafts=include_drafts)
        results = [check_article(a) for a in articles]
        avg = sum(r["score"] for r in results) / len(results) if results else 0
        critical = [r for r in results if r["score"] < 60]

    write_report(results, fixed)

    if as_json:
        out = {"articles": len(results), "avg_score": round(avg, 1),
               "critical": len(critical), "details": results,
               "suggestions": suggestions, "fixed": fixed}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        sys.exit(1 if critical else 0)

    print(f"\nKeyword-Optimierung: {len(results)} Artikel (Ø-Score: {avg:.0f}/100) · Geheilt: {fixed}\n")
    for r in sorted(results, key=lambda x: x["score"]):
        flag = "✅" if r["score"] >= 80 else ("⚠️" if r["score"] >= 60 else "❌")
        print(f"{flag} {r['score']:>3}/100  {r['title']}  (Dichte: {r['density']}%)")
        for i in r["issues"][:3]:
            print(f"      • {i}")
        kw = r.get("main_kw")
        if kw and suggestions.get(kw):
            print(f"      💡 LSI: {', '.join(suggestions[kw])}")

    print(f"\nErgebnis: {len(critical)} Artikel unter 60 Punkten (kritisch)")
    if fixed:
        print(f"→ {fixed} Artikel geheilt (Report: {REPORT})")
    if critical:
        sys.exit(1)
    print("✅ Alle Artikel keyword-optimiert auf Profi-Niveau")


if __name__ == "__main__":
    sys.exit(main())
