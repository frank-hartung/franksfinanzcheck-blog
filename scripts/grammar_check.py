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


SHY = "\u00ad"   # weiche Trennstelle aus scripts/umbruch_guard.py


def strip_shy(text):
    """Entfernt weiche Trennstellen (U+00AD) für den LanguageTool-Check.

    LanguageTool würde „Verbraucher\u00adschlichtungsstelle“ sonst als zwei
    Wörter lesen („schlichtungs“ = unbekannt) und falsch „korrigieren“.
    Rückgabe: (sauberer Text, Offset-Tabelle zurück in den Originaltext).
    Ist keine Trennstelle enthalten, bleibt der Text unverändert (table=None).
    """
    if SHY not in text:
        return text, None
    chars, table = [], []
    for i, ch in enumerate(text):
        if ch == SHY:
            continue
        chars.append(ch)
        table.append(i)
    table.append(len(text))
    return "".join(chars), table


# FALSCH-POSITIV-SCHUTZ (02.09.2026, Wöchentliche SEO-Optimierung #20):
# LanguageTools Satzanfangs-Regel (Kategorie CASING) hält kompakte Datums-/
# Ordnungspunkte („Kündigung bis 30.11. bei …“, „30.11. in den Kalender“) für
# Satzenden und „korrigiert“ das Folgewort groß: „Bei manchen“, „Anfängt“,
# „Kennen und nutzen“, „Zum 31.12. Des Jahres“ – 6 echte Schäden, eingespielt
# am 01.09. (e230ada2) via Auto-Apply und heute live repariert.
# Dauerhafte Regel: CASING-Korrekturen direkt NACH einem Datumspunkt-Muster
# werden NIE automatisch übernommen (auch nicht gemeldet) – ein verpasster
# True-Positive ist billiger als ein falsch kapitalisiertes Verb.
DATE_DOT_TRAP = re.compile(r"(?:\d{1,2}\.){1,3}\s*$")


def accept_lt_match(m, chunk_lt, table, whitelist):
    """Filtert ein einzelnes LanguageTool-Match (alle deterministischen
    Regeln, offline testbar). Liefert Ergebnis-Dict oder None (= verworfen).
    `table` ist die Offset-Tabelle aus strip_shy() (oder None)."""
    cat = m.get("rule", {}).get("category", {}).get("id", "")
    if cat in SKIP_CATEGORIES:
        return None
    if cat not in FIX_CATEGORIES and cat != "UNKNOWN_WORD":
        return None
    offset = m.get("offset", 0)
    length = m.get("length", 0)
    word = chunk_lt[offset:offset + length]
    # Whitelist: Wort ignorieren
    wl_key = word.lower().strip(".,;:!?")
    if wl_key in whitelist:
        return None
    # Nur Vorschläge mit genau 1 Replacement = eindeutig
    repls = m.get("replacements", [])
    if len(repls) != 1:
        return None
    repl = repls[0].get("value", "")
    if not repl or repl == word:
        return None
    # "Du"→"du" Einheitlichkeits-Vorschläge NICHT fixen (Stil-Entscheidung
    # des Blogs: "Du" am Satzanfang groß, "du" im Satz klein ist üblich)
    if word in ("Du", "Dein", "Deine", "Deinem", "Deiner", "Sie", "Ihr", "Ihre") \
       and repl.lower() == word.lower() and cat != "CASING":
        return None
    # Komma-Fixes: nur annehmen, wenn nicht zu invasiv
    if cat == "PUNCTUATION" and len(repl) > len(word) + 5:
        return None
    # Großschreib-Falle NACH Datums-/Ordnungspunkt („30.11. bei“ ≠ Satzende)
    if cat == "CASING" and word[:1].islower() and repl[:1].isupper() \
            and DATE_DOT_TRAP.search(chunk_lt[max(0, offset - 14):offset]):
        return None
    off, ln = offset, length
    if table:  # Offsets zurück in den Originaltext rechnen
        end = min(off + ln, len(chunk_lt))
        off, ln = table[off], max(table[end] - table[off], ln)
    return {
        "offset": off, "length": ln, "word": word, "fix": repl,
        "message": m.get("message", ""), "category": cat,
        "conf": 0.9,
    }


API_FAILURES = 0   # hochgezählt bei nicht erreichbarer LanguageTool-API


def lt_check(text, whitelist):
    """LanguageTool-Check eines Texts. Liefert Liste von Matches (gefiltert)."""
    global API_FAILURES
    if not text.strip():
        return []
    results = []
    for chunk in chunk_text(text):
        chunk_lt, table = strip_shy(chunk)   # U+00AD raus, Offsets gerettet
        data = urllib.parse.urlencode({
            "language": "de-DE",
            "text": chunk_lt,
            "enabledOnly": "false",
        }).encode()
        req = urllib.request.Request(API_URL, data=data,
                                     headers={"User-Agent": "Mozilla/5.0 (FranksFinanzcheck-Bot)",
                                              "Content-Type": "application/x-www-form-urlencoded"})
        try:
            resp = json.loads(urllib.request.urlopen(req, timeout=60).read())
        except Exception as e:
            # Toter-Gate-Schutz (01.09.2026, Audit): API-Fehler wurden bisher
            # still geschluckt -> Report meldete dauerhaft „0 Funde“.
            API_FAILURES += 1
            print(f"  ⚠️ LanguageTool-Fehler: {e}")
            time.sleep(5)
            continue
        for m in resp.get("matches", []):
            accepted = accept_lt_match(m, chunk_lt, table, whitelist)
            if accepted:
                results.append(accepted)
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


def run_selftest():
    """Offline-Selbsttest der Match-Filter (keine API nötig), eingefrorene
    Schadensfälle vom 01./02.09.2026. Exit 2 bei Versagen."""
    wl = set(w.lower() for w in DEFAULT_WHITELIST)

    def m(rule_cat, off, ln, repl, msg="LT-Meldung"):
        return {"rule": {"category": {"id": rule_cat}}, "offset": off,
                "length": ln, "message": msg,
                "replacements": ([{"value": repl}] if repl is not None else [])}

    cases = []

    # 1) Datumspunkt-Falle: „…bis 30.09. bei…“ → CASING „Bei“ wird verworfen
    text = "Kündigung meist bis 30.11., 30.09. bei manchen. Wer im Oktober vergleicht."
    pos = text.index("bei")
    res = accept_lt_match(m("CASING", pos, 3, "Bei"), text, None, wl)
    cases.append(("FALSCH-POSITIV gehärtet: CASING nach Datumspunkt verworfen", res is None))

    # 2) Kompaktdatum „…am 29.11. anfängt…“ → „Anfängt“ wird verworfen
    text2 = "stichtag. Wer am 29.11. anfängt, unterschreibt Fehler."
    pos2 = text2.index("anfängt")
    res2 = accept_lt_match(m("CASING", pos2, len("anfängt"), "Anfängt"), text2, None, wl)
    cases.append(("Kompaktdatum X.Y. geschützt („anfängt“ bleibt klein)", res2 is None))

    # 3) Ordinalpunkt „…der 30. zum…“ → „Zum“ wird verworfen
    text3 = "Der reguläre Kündigungstermin ist der 30.11. zum 31.12. des Jahres."
    pos3 = text3.index("zum")
    res3 = accept_lt_match(m("CASING", pos3, 3, "Zum"), text3, None, wl)
    pos3b = text3.index("des Jahres")
    cases.append(("Ordinal-&Folgedatum geschützt („zum“/„des“)", res3 is None
                  and accept_lt_match(m("CASING", pos3b, 3, "Des"), text3, None, wl) is None))

    # 4) ECHTER Satzanfang bleibt heilbar: „Fehler gemacht. dann …“ → „Dann“
    text4 = "Viele machen Fehler. dann ärgern sie sich."
    pos4 = text4.index("dann")
    res4 = accept_lt_match(m("CASING", pos4, 4, "Dann"), text4, None, wl)
    cases.append(("True-Positive bleibt: CASING am echten Satzanfang",
                  res4 is not None and res4["fix"] == "Dann"))

    # 5) TYPOS eindeutig → angenommen
    text5 = "Der Ferstärker ist kaputt."
    res5 = accept_lt_match(m("TYPOS", text5.index("Ferstärker"), 10, "Verstärker"), text5, None, wl)
    cases.append(("TYPOS-Fix wird angenommen", res5 is not None))

    # 6) STYLE → nie automatisiert
    res6 = accept_lt_match(m("STYLE", 0, 4, "egal"), "Irgendein Satz.", None, wl)
    cases.append(("STYLE-Kategorie verworfen", res6 is None))

    # 7) Whitelist geschützt (Marken/Fachbegriffe)
    text7 = "Bei check24 vergleichen lohnt sich."
    res7 = accept_lt_match(m("TYPOS", text7.index("check24"), 7, "Check24"), text7, None, wl)
    cases.append(("Whitelist-Wort verworfen", res7 is None))

    # 8) „Du“→„du“ Stil-Vorschlag (nicht CASING) → verworfen
    text8 = "Hier kannst Du sparen."
    res8 = accept_lt_match(m("TYPOS", text8.index("Du"), 2, "du"), text8, None, wl)
    cases.append(("Du→du Stil-Vorschlag verworfen", res8 is None))

    # 9) Zu invasive PUNCTUATION-Veränderung → verworfen
    text9 = "Das ist ein Test."
    res9 = accept_lt_match(m("PUNCTUATION", 0, 3, "Dasssssssss"), text9, None, wl)
    cases.append(("Invasiver PUNCTUATION-Fix verworfen", res9 is None))

    # 10) PUNCTUATION moderat → angenommen
    res10 = accept_lt_match(m("PUNCTUATION", 0, 3, "Das,"), text9, None, wl)
    cases.append(("Moderater PUNCTUATION-Fix angenommen", res10 is not None))

    # 11) SHY-Offsets: Trennstelle vor dem Fund verschiebt nichts
    lyric = "Verbraucher\u00adstreitbeilegung ist 30.11. fällig"
    plain, tbl = strip_shy(lyric)
    cases.append(("strip_shy entfernt U+00AD", "\u00ad" not in plain))
    ok_off = tbl is not None and tbl[plain.index("streit")] == lyric.index("streit")
    cases.append(("Offset-Tabelle rechnet korrekt zurück", ok_off))

    fails = [name for name, ok in cases if not ok]
    for name, ok in cases:
        print(("\u2705 " if ok else "\u274c ") + name)
    if fails:
        print(f"\n\U0001f6d1 GRAMMAR-SELFTEST FEHLGESCHLAGEN: {len(fails)} Fall/Fälle")
        return 2
    print(f"\n\u2705 GRAMMAR-SELFTEST bestanden ({len(cases)} Fälle, offline, 0 API).")
    return 0


def main():
    if "--selftest" in sys.argv:
        sys.exit(run_selftest())
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
        if API_FAILURES > 3:
            print("🛑 Circuit-Breaker: LanguageTool-API mehrfach nicht erreichbar – "
                  "Abbruch, der Report markiert den Gate als nicht auswertbar.")
            break

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
    api_down = API_FAILURES > 0 and total == 0
    lines = [
        "# 🔤 Grammatik-Report", "",
        f"> **Automatisch** – {len(articles)} Artikel geprüft (LanguageTool de-DE), "
        f"{total} Funde, {fixed_count} korrigiert, {len(still)} offen.", "",
    ]
    if api_down:
        lines += [f"🛑 **LanguageTool-API NICHT erreichbar** ({API_FAILURES} fehlgeschlagene "
                  "Requests) – dieser Gate ist aktuell NICHT auswertbar. Bitte API-Erreichbarkeit "
                  "prüfen (api.languagetool.org); sonst liefert der Report dauerhaft 0 Funde.",
                  "",
                  "## Funde", "", "_(keine – API down)_"]
    else:
        lines.append("## Funde")
        for e in all_problems:
            lines.append(f"### {e['file']}")
            for p in e["problems"]:
                mark = "✅" if p.get("applied") else "⚠️"
                lines.append(f"- {mark} „{p['word']}“ → „{p['fix']}“ – {p['reason'][:80]}")
    lines += ["", "---", "*Erzeugt von scripts/grammar_check.py (LanguageTool Public API)*"]
    open(REPORT_FILE, "w", encoding="utf-8").write("\n".join(lines))
    json.dump({"articles": len(articles), "total": total, "fixed": fixed_count,
               "open": len(still), "api_failures": API_FAILURES},
              open(JSON_FILE, "w", encoding="utf-8"))

    print(f"\nFertig: {total} Funde, {fixed_count} korrigiert, {len(still)} offen "
          f"(API-Fehler: {API_FAILURES}).")
    sys.exit(2 if api_down else (1 if still else 0))


if __name__ == "__main__":
    main()
