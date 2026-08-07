#!/usr/bin/env python3
"""
TOP-LEVEL-RECHTSCHREIB- UND GROSS-/KLEINSCHREIBUNGS-PRÜFUNG
für FranksFinanzcheck (deutsche Sprache, Hunspell de_DE).

PRÜFT:
  A) Rechtschreibung  – Hunspell de_DE (echtes deutsches Wörterbuch)
  B) Groß-/Kleinschreibung:
       1. Kleingeschriebene Nomen (Hunspell kennt die Großform, nicht die
          Kleinform → "geld" → "Geld", "haushaltsbuch" → "Haushaltsbuch")
       2. Satzanfänge nach . ! ? (kleingeschriebenes Wort nach Satzpunkt)
       3. "zuhause" → "zu Hause" (klassische Standardform; "Zuhause" als
          Nomen bleibt korrekt)
  C) URL-Reste & Markdown-Artefakte (werden ignoriert, nicht "korrigiert")

SICHERHEIT:
  - Es wird NUR der Fließtext (Body) korrigiert.
  - Frontmatter: title/description werden nur gemeldet (KEINE Auto-Änderung
    ohne --fix-frontmatter); tags/keywords bleiben unangetastet (SEO-Klein-
    schreibung ist üblich und gewollt).
  - Links/URLs/Code-Blöcke/HTML werden NIE verändert.
  - Whitelist (data/spellcheck_whitelist.txt) schützt Eigennamen und
    Fachbegriffe (Frugalismus, FritzBox, ETF, …).
  - Korrekturen nur bei EINDEUTIGEN Fällen; Unsicheres wandert in den
    Report (bzw. mit --ai zur KI-Entscheidung).

NUTZUNG:
  python3 scripts/spellcheck.py               # Prüfung + Report (Exit 1 bei Fehlern)
  python3 scripts/spellcheck.py --fix         # Eindeutige Fehler korrigieren
  python3 scripts/spellcheck.py --fix --ai    # + KI-Entscheidung für unsichere Fälle
  python3 scripts/spellcheck.py --file X.md   # einzelner Artikel
  python3 scripts/spellcheck.py --json        # maschinenlesbar (Workflow)
"""
import os
import re
import sys
import json
import glob
import subprocess

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
WHITELIST_FILE = os.path.join(BLOG_DIR, "data", "spellcheck_whitelist.txt")
REPORT_FILE = os.path.join(BLOG_DIR, "RECHTSCHREIB-REPORT.md")
JSON_FILE = os.path.join(BLOG_DIR, ".spellcheck_report.json")

# Abkürzungen, die Hunspell nicht kennt, aber korrekt sind
ABKUERZUNGEN = {
    "z.b", "z.b.", "bzw", "bzw.", "ca", "ca.", "etc", "etc.", "inkl", "inkl.",
    "exkl", "zzgl", "vgl", "usw", "usw.", "d.h", "d.h.", "u.a", "u.a.", "usf",
    "max", "max.", "min", "min.", "nr", "nr.", "tel", "geb", "ggf", "evtl",
    "sog", "bspw", "bzw", "bzw.", "vs", "vs.", "mbit", "kbit", "gbit", "ghz",
    "mhz", "kmh", "kwh", "kw", "mw", "kva", "uhr", "usd", "eur", "gb", "mb",
    "tb", "ssid", "vpn", "dns", "dsl", "lte", "sms", "tan", "pin", "wlan",
    "www", "http", "https", "com", "de", "net", "org",
}

# URL-Erkennung
URL_RE = re.compile(r'https?://[^\s)"\']+|www\.[^\s)"\']+')

# Markdown-Link: [Text](url) → nur Text behalten
LINK_RE = re.compile(r'\[([^\]]*)\]\([^)]*\)')

# Code-Blöcke
CODE_RE = re.compile(r'```.*?```', re.S)

# Satzendepunkte für Satzanfangs-Prüfung
SENTENCE_END_RE = re.compile(r'([.!?])\s+([a-zäöüß])')

# "zuhause" → "zu Hause" (nur kleingeschrieben; "Zuhause" Nomen bleibt)
ZUHAUSE_RE = re.compile(r'\bzuhause\b')

# Bekannte Fehl-Phrasen (Bot-Artefakte: Keywords wörtlich klein im Fließtext)
PHRASEN_FIXES = [
    (re.compile(r'\bdns server wechseln\b'), 'DNS-Server wechseln'),
    (re.compile(r'\bdns server\b'), 'DNS-Server'),
    (re.compile(r'\bdsl tipps\b'), 'DSL-Tipps'),
    (re.compile(r'\bgeld sparen im alltag\b'), 'Geld sparen im Alltag'),
    (re.compile(r'\bmietwagen günstig buchen\b'), 'Mietwagen günstig buchen'),
    (re.compile(r'\bfrugalismus tipps\b'), 'Frugalismus-Tipps'),
]


def load_whitelist():
    wl = set()
    if os.path.exists(WHITELIST_FILE):
        for line in open(WHITELIST_FILE, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#"):
                wl.add(line.lower())
    return wl


def load_articles(files=None):
    arts = []
    paths = files or sorted(glob.glob(os.path.join(POSTS_DIR, "*.md")))
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

        arts.append({
            "file": os.path.basename(path), "path": path,
            "title": get("title"), "description": get("description"),
            "fm": fm, "body": body, "content": content,
        })
    return arts


def extract_words(body, whitelist):
    """Liefert Liste von (wort, start, end) – nur Fließtext, ohne Links/Code/URLs.
    OFFSET-SICHER: Alles, was ignoriert werden soll, wird durch gleich lange
    Leerzeichen maskiert – die start/end-Positionen stimmen exakt mit dem
    Original-Body überein (für sichere Korrekturen)."""
    text = body
    # Code + URLs + komplette Markdown-Links maskieren (gleiche Länge!)
    text = CODE_RE.sub(lambda m: " " * (m.end() - m.start()), text)
    text = URL_RE.sub(lambda m: " " * (m.end() - m.start()), text)
    text = LINK_RE.sub(lambda m: " " * (m.end() - m.start()), text)

    words = []
    # Bindestriche nur in der Wortmitte erlauben (kein "-" am Ende:
    # "Strom-, DSL- und …" → "DSL" statt "DSL-")
    for m in re.finditer(r"[A-Za-zÄÖÜäöüß0-9]+(?:-[A-Za-zÄÖÜäöüß0-9]+)*", text):
        w = m.group(0)
        # Abkürzungen + Whitelist ignorieren
        if w.lower().rstrip(".") in ABKUERZUNGEN or w.lower() in whitelist:
            continue
        # Kurze Kleinschreibung = meist Artefakt/Abkürzung (z. B. "aid", "pid")
        if len(w) <= 3 and w.islower():
            continue
        words.append((w, m.start(), m.end()))
    return words


def batch_hunspell(words):
    """Prüft Wörter per Hunspell-Batch. Liefert Set der fehlerhaften Wörter."""
    if not words:
        return set()
    r = subprocess.run(["hunspell", "-d", "de_DE", "-l"],
                       input="\n".join(words) + "\n",
                       capture_output=True, text=True)
    out = r.stdout.strip()
    return set(out.split("\n")) if out else set()


def is_noun_capitalized(word):
    """Prüft, ob die GROSSGESCHRIEBENE Form ein bekanntes Nomen ist.

    Strengere Logik (verhindert falsche Positives wie 'erreichst'→'Erreichst'):
    - Die KLEINform muss ein Hunspell-FEHLER sein (sonst ist es ein Verb,
      Adjektiv oder Pronomen – z. B. 'erreichst', 'deine', 'finanzielle').
    - Die GROSSform muss ein Hunspell-TREFFER sein.
    Nur dann liegt ein kleingeschriebenes Nomen vor ('geld'→'Geld')."""
    if not word or word[0].isupper():
        return False
    # Kleinform: bekannt → kein Nomen-Fall (Verb/Adjektiv)
    r_small = subprocess.run(["hunspell", "-d", "de_DE", "-l"],
                             input=word + "\n", capture_output=True, text=True)
    if r_small.stdout.strip() == "":
        return False
    # Großform: bekannt → Nomen-Kandidat
    cap = word[0].upper() + word[1:]
    r_cap = subprocess.run(["hunspell", "-d", "de_DE", "-l"],
                           input=cap + "\n", capture_output=True, text=True)
    return r_cap.stdout.strip() == ""


def suggestions(word):
    """Hunspell-Korrekturvorschläge."""
    r = subprocess.run(["hunspell", "-d", "de_DE"],
                       input=word + "\n", capture_output=True, text=True)
    lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
    if lines and lines[0].startswith("&"):
        # Format: & original 0 0: vorschlag1, vorschlag2
        parts = lines[0].split(":")
        if len(parts) > 1:
            return [s.strip() for s in parts[1].split(",") if s.strip()]
    return []


def analyze_article(a, whitelist):
    """Analysiert einen Artikel. Liefert Liste von Problemen."""
    body = a["body"]
    problems = []
    # Phrasen-Fixes zuerst (ganze Fehl-Phrasen → korrekte Schreibweise)
    for regex, fix in PHRASEN_FIXES:
        for m in regex.finditer(body):
            problems.append({
                "type": "phrase", "word": m.group(0), "fix": fix,
                "start": m.start(), "end": m.end(), "conf": 0.97,
                "reason": f"Phrase: „{m.group(0)}“ → „{fix}“",
            })
    words = extract_words(body, whitelist)
    if not words:
        return problems

    word_list = [w for w, _, _ in words]
    bad = batch_hunspell(word_list)

    # Map für schnellen Lookup: Wort → Positionen (erste)
    pos_map = {}
    for w, s, e in words:
        pos_map.setdefault(w, (s, e))

    # 1. Rechtschreibfehler mit Vorschlägen
    for w, s, e in words:
        if w not in bad:
            continue
        # Kleingeschriebenes Nomen? (Großform bekannt) – "zuhause" ausgenommen
        # (wird von der Sonderregel "→ zu Hause" behandelt)
        if w.lower() == "zuhause":
            continue
        # "minute" in "last minute" ist korrekt (etablierter Begriff)
        if w.lower() == "minute" and re.search(r'last\s+minute', body[max(0, s-15):e]):
            continue
        if is_noun_capitalized(w):
            cap = w[0].upper() + w[1:]
            problems.append({
                "type": "noun_case", "word": w, "fix": cap,
                "start": s, "end": e, "conf": 0.95,
                "reason": f"Substantiv klein: „{w}“ → „{cap}“",
            })
            continue
        # Eindeutiger Tippfehler: genau 1 Vorschlag
        sugg = suggestions(w)
        if len(sugg) == 1:
            problems.append({
                "type": "typo", "word": w, "fix": sugg[0],
                "start": s, "end": e, "conf": 0.8,
                "reason": f"Tippfehler: „{w}“ → „{sugg[0]}“",
            })
        else:
            problems.append({
                "type": "unknown", "word": w, "fix": None,
                "start": s, "end": e, "conf": 0.0,
                "reason": f"Unbekanntes Wort: „{w}“ (Vorschläge: {', '.join(sugg[:3]) or '–'})",
            })

    # 2. "zuhause" → "zu Hause" (nur kleingeschrieben, nicht in Links)
    for m in ZUHAUSE_RE.finditer(body):
        problems.append({
            "type": "zuhause", "word": "zuhause", "fix": "zu Hause",
            "start": m.start(), "end": m.end(), "conf": 0.9,
            "reason": "„zuhause“ → „zu Hause“ (Standardform)",
        })

    # 3. Description im Frontmatter mitprüfen (Google-Text!):
    #    Phrasen-Fixes + "zuhause" + kleingeschriebene Substantive –
    #    tags/keywords bleiben bewusst unangetastet (SEO-Kleinschreibung).
    desc = a.get("description", "")
    desc_abs_start = a["content"].find("description:")
    if desc and desc_abs_start >= 0:
        # absolute Position des Description-Inhalts (nach 'description: "')
        quote = a["content"].find('"', desc_abs_start + 12)
        if quote >= 0:
            dstart = quote + 1
            for regex, fix in PHRASEN_FIXES:
                for m in regex.finditer(desc):
                    problems.append({
                        "type": "phrase", "word": m.group(0), "fix": fix,
                        "abs_start": dstart + m.start(), "abs_end": dstart + m.end(),
                        "conf": 0.97,
                        "reason": f"Description-Phrase: „{m.group(0)}“ → „{fix}“",
                    })
            for m in ZUHAUSE_RE.finditer(desc):
                problems.append({
                    "type": "zuhause", "word": "zuhause", "fix": "zu Hause",
                    "abs_start": dstart + m.start(), "abs_end": dstart + m.end(),
                    "conf": 0.9,
                    "reason": "Description: „zuhause“ → „zu Hause“",
                })
            # Kleingeschriebene Substantive in der Description
            for m in re.finditer(r"[A-Za-zÄÖÜäöüß]+(?:-[A-Za-zÄÖÜäöüß]+)*", desc):
                w = m.group(0)
                if w.lower() in whitelist or len(w) <= 3 or w[0].isupper():
                    continue
                if is_noun_capitalized(w) and w.lower() != "zuhause":
                    # Phrasen-Abdeckung prüfen (nicht doppelt)
                    covered = any(regex.search(desc[max(0, m.start()-20):m.end()+20])
                                  for regex, _ in PHRASEN_FIXES)
                    if not covered:
                        cap = w[0].upper() + w[1:]
                        problems.append({
                            "type": "noun_case", "word": w, "fix": cap,
                            "abs_start": dstart + m.start(), "abs_end": dstart + m.end(),
                            "conf": 0.95,
                            "reason": f"Description: Substantive klein „{w}“ → „{cap}“",
                        })

    return problems


def apply_fix(a, problem):
    """Wendet eine Korrektur an. Body-Funde rechnen den Offset nach dem
    Frontmatter hoch; Description-Funde nutzen absolute Offsets."""
    content = a["content"]
    parts = content.split("---", 2)
    body_start = content.index(parts[2]) if len(parts) == 3 else 0
    if "abs_start" in problem:
        abs_start = problem["abs_start"]
        abs_end = problem["abs_end"]
    else:
        abs_start = body_start + problem["start"]
        abs_end = body_start + problem["end"]

    # Sicherheitscheck: nichts im Link/Code verändern
    segment = content[max(0, abs_start - 30):abs_end + 30]
    if "](http" in segment or "[[" in segment:
        return False

    old = content[abs_start:abs_end]
    if old != problem["word"]:
        return False
    content = content[:abs_start] + problem["fix"] + content[abs_end:]
    a["content"] = content
    return True


def ai_decide(article, problems):
    """KI entscheidet für unsichere Fälle (type=unknown). Liefert Liste mit fix."""
    import urllib.request
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    groq_key = os.environ.get("GROQ_API_KEY", "")
    if not (gemini_key or groq_key):
        return problems

    unsure = [p for p in problems if p["type"] == "unknown"]
    if not unsure:
        return problems

    ctx_lines = []
    for i, p in enumerate(unsure):
        ctx = article["body"][max(0, p["start"] - 80):p["end"] + 80].replace("\n", " ")
        ctx_lines.append(f"{i+1}. Wort: {p['word']} | Kontext: …{ctx}…")

    prompt = (
        "Du bist ein deutscher Lektor. Im folgenden Blog-Artikel-Text sind Wörter "
        "markiert, die das Wörterbuch nicht kennt. Entscheide für JEDES Wort, ob es "
        "a) ein korrektes Fachwort/Eigenname ist (dann antworte OK) oder b) ein Fehler, "
        "den du korrigierst (dann nenne das korrekte Wort).\n\n"
        + "\n".join(ctx_lines) +
        "\n\nAntworte im Format: Nummer|OK oder Nummer|korrektesWort – eine Zeile pro Nummer."
    )
    ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"

    text = None
    if gemini_key:
        try:
            body = {"contents": [{"parts": [{"text": prompt}]}]}
            req = urllib.request.Request(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key=" + gemini_key,
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json", "User-Agent": ua})
            resp = json.loads(urllib.request.urlopen(req, timeout=90).read())
            text = resp["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception:
            pass
    if not text and groq_key:
        try:
            body = {"model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}], "max_tokens": 500}
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {groq_key}", "User-Agent": ua})
            resp = json.loads(urllib.request.urlopen(req, timeout=90).read())
            text = resp["choices"][0]["message"]["content"].strip()
        except Exception:
            pass
    if not text:
        return problems

    for line in text.splitlines():
        m = re.match(r"(\d+)\s*\|\s*(.+)", line.strip())
        if not m:
            continue
        idx = int(m.group(1)) - 1
        decision = m.group(2).strip()
        if 0 <= idx < len(unsure) and decision.upper() != "OK":
            unsure[idx]["fix"] = decision
            unsure[idx]["type"] = "ai_fix"
            unsure[idx]["conf"] = 0.7
    return problems


def main():
    fix = "--fix" in sys.argv
    use_ai = "--ai" in sys.argv
    as_json = "--json" in sys.argv
    files = None
    if "--file" in sys.argv:
        files = [sys.argv[sys.argv.index("--file") + 1]]

    whitelist = load_whitelist()
    articles = load_articles(files)
    print(f"Rechtschreib-/Groß-Klein-Prüfung: {len(articles)} Artikel\n")

    all_problems = []
    for a in articles:
        problems = analyze_article(a, whitelist)
        if problems:
            all_problems.append({"file": a["file"], "title": a["title"], "problems": problems})

    # KI-Entscheidung für unsichere Fälle
    if use_ai:
        for entry in all_problems:
            a = next(x for x in articles if x["file"] == entry["file"])
            entry["problems"] = ai_decide(a, entry["problems"])

    # Korrekturen anwenden (Phrasen zuerst, dann Wörter – Overlap-Schutz)
    fixed_count = 0
    remaining = []
    for entry in all_problems:
        a = next(x for x in articles if x["file"] == entry["file"])
        # Anwendung in 2 Phasen (rückwärts, damit Offsets gültig bleiben):
        # 1) PHASEN-Fixes (größere Bereiche) zuerst – sie haben Vorrang
        # 2) Wort-Fixes, die mit einem Phasen-Bereich überlappen, überspringen
        covered = []  # bereits korrigierte Bereiche
        def pstart(p): return p.get("abs_start", p.get("start"))
        def pend(p):   return p.get("abs_end", p.get("end"))
        phases = sorted([p for p in entry["problems"] if p["type"] == "phrase"],
                        key=lambda p: pstart(p), reverse=True)
        words = sorted([p for p in entry["problems"] if p["type"] != "phrase"],
                       key=lambda p: pstart(p), reverse=True)
        for p in phases + words:
            if not (p["fix"] and p["conf"] >= 0.7):
                remaining.append(p)
                continue
            # Overlap-Check gegen bereits korrigierte Bereiche
            ps, pe = pstart(p), pend(p)
            if any(not (pe <= cs or ps >= ce) for cs, ce in covered):
                continue
            if fix and apply_fix(a, p):
                fixed_count += 1
                p["applied"] = True
                covered.append((ps, pe))
            elif fix:
                pass
            else:
                p["applied"] = False

    # Dateien schreiben
    if fix:
        for a in articles:
            if a.get("content") != a["content"]:
                pass  # nur geänderte schreiben
        for a in articles:
            orig = open(a["path"], encoding="utf-8").read()
            if a["content"] != orig:
                open(a["path"], "w", encoding="utf-8").write(a["content"])

    # Report
    total = sum(len(e["problems"]) for e in all_problems)
    still = [p for e in all_problems for p in e["problems"] if not p.get("applied")]
    lines = [
        "# 📝 Rechtschreib-Report", "",
        f"> **Automatisch** erzeugt am … – {len(articles)} Artikel geprüft, "
        f"{total} Funde, {fixed_count} korrigiert, {len(still)} offen.", "",
        "## Offene Punkte", "",
    ]
    if still:
        for p in still[:50]:
            lines.append(f"- `{p['reason']}`")
        if len(still) > 50:
            lines.append(f"- … und {len(still)-50} weitere")
    else:
        lines.append("_Keine offenen Punkte._")
    lines += ["", "---", "*Erzeugt von scripts/spellcheck.py*"]
    open(REPORT_FILE, "w", encoding="utf-8").write("\n".join(lines))

    # JSON
    json.dump({"articles": len(articles), "total": total, "fixed": fixed_count,
               "open": len(still)}, open(JSON_FILE, "w", encoding="utf-8"))

    # Ausgabe
    for entry in all_problems:
        print(f"  {entry['file']}:")
        for p in entry["problems"]:
            mark = "✅" if p.get("applied") else ("⚠️" if p["fix"] and p["conf"] >= 0.7 else "❌")
            print(f"    {mark} {p['reason']}")

    print(f"\nFertig: {total} Funde, {fixed_count} korrigiert, {len(still)} offen.")
    sys.exit(1 if still else 0)


if __name__ == "__main__":
    main()
