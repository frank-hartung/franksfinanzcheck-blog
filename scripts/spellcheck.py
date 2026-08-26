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

import groq_config

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

# Markdown-Tabellen-Trennzeile (Spalten-Ausrichtung): „| :--- | :---: |“
TABLE_SEP_RE = re.compile(r'^\s*\|?\s*:?-{2,}:?\s*(?:\|\s*:?-{2,}:?\s*)*\|?\s*$', re.M)

# Satzendepunkte für Satzanfangs-Prüfung
SENTENCE_END_RE = re.compile(r'([.!?])\s+([a-zäöüß])')

# "zuhause" → "zu Hause" (nur kleingeschrieben; "Zuhause" Nomen bleibt)
ZUHAUSE_RE = re.compile(r'\bzuhause\b')

# Satzanfang NACH einer Markdown-Überschrift muss groß sein:
#   "## Die Grundlagen des Frugalismus\ndu brauchst…" → "Du brauchst…"
HEADING_START_RE = re.compile(r'^(#{1,6}\s+[^\n]+\n)([a-zäöüß])', re.M)

# Falsche Großschreibung NACH KOMMA (kein Nomen/Eigenname):
#   ", Wer Vermögen aufbauen will" → ", wer Vermögen…"
#   Ausnahme: Zeile beginnt mit "#" (zusammengeführte Überschrift+Text)
COMMA_CAP_RE = re.compile(r',\s+([A-ZÄÖÜ][a-zäöüß]+)')

# Höflichkeitsformen, die nach Komma korrekt groß bleiben
POLITE_FORMS = {"sie", "ihr", "ihre", "ihnen", "sie", "ihnen"}

# SATZZEICHEN-REGELN (deterministisch, sicher):
# 1) Abkürzungen ohne Leerzeichen: "Z.B." → "z. B.", "z.B." → "z. B." …
ABKUERZUNG_FIXES = [
    (re.compile(r'\bZ\.B\.'), 'z. B.'),
    (re.compile(r'\bz\.B\.'), 'z. B.'),
    (re.compile(r'\bU\.A\.'), 'u. a.'),
    (re.compile(r'\bu\.A\.'), 'u. a.'),
    (re.compile(r'\bD\.H\.'), 'd. h.'),
    (re.compile(r'\bd\.H\.'), 'd. h.'),
    (re.compile(r'\bU\.S\.W\.'), 'usw.'),
    (re.compile(r'\bu\.S\.W\.'), 'usw.'),
    (re.compile(r'\bE\.T\.C\.'), 'etc.'),
    (re.compile(r'\be\.T\.C\.'), 'etc.'),
]
# 2) Leerzeichen VOR Satzzeichen (", . ; : ! ?") – NICHT bei "z. B."-Abkürzungen
#    und nicht bei Dezimalzahlen ("4, 5" → "4,5" ist ok, aber selten – wir
#    fixen nur eindeutige Fälle wie "Hallo ," → "Hallo,")
SPACE_BEFORE_PUNCT_RE = re.compile(r' +([,;:!?])')

# 3) Doppelte Satzzeichen: "..", ",,", ";;", "::", "!!", "??" → einfach
DOUBLE_PUNCT_RE = re.compile(r'(?<![.\d])\.\.(?![.\d])|,,|;;|::|!!|\?\?')

# 4) Großbuchstabe NACH Abkürzung mitten im Satz ("z. B. Wenn" → "z. B. wenn"):
#    nur wenn davor KEIN Satzendepunkt steht (dann wäre es ein neuer Satz)
AFTER_ABBR_CAP_RE = re.compile(r'(?:[zZ]\.\s?[bB]\.|[uU]\.\s?[aA]\.|[dD]\.\s?[hH]\.|usw\.|etc\.|bzw\.)\s+([A-ZÄÖÜ][a-zäöüß]+)')

# ANREDE-KONSISTENZ: Der Blog spricht Leser durchgehend mit "du" an.
# Echte Höflichkeitsformen (Sie/Ihre/Ihnen) in Descriptions sind ein
# Stilbruch. Diese Muster werden deterministisch auf du-Form umgestellt.
ANREDE_IMPERATIVE = [
    (re.compile(r'Erfahren Sie, wie Sie'), 'Erfahre, wie du'),
    (re.compile(r'Erfahren Sie, wie'), 'Erfahre, wie'),
    (re.compile(r'Erfahren Sie'), 'Erfahre'),
    (re.compile(r'Entdecken Sie'), 'Entdecke'),
    (re.compile(r'Nutzen Sie'), 'Nutze'),
    (re.compile(r'Vergleichen Sie'), 'Vergleiche'),
    (re.compile(r'Informieren Sie sich'), 'Informiere dich'),
    (re.compile(r'Melden Sie'), 'Melde'),
    (re.compile(r'Buchen Sie'), 'Buche'),
    (re.compile(r'Sparen Sie'), 'Spare'),
    (re.compile(r'Prüfen Sie'), 'Prüfe'),
    (re.compile(r'Sichern Sie'), 'Sichere'),
    (re.compile(r'Beachten Sie'), 'Beachte'),
]
ANREDE_PRONOUN = [
    (re.compile(r'\bIhre\b'), 'deine'),
    (re.compile(r'\bIhren\b'), 'deinen'),
    (re.compile(r'\bIhrem\b'), 'deinem'),
    (re.compile(r'\bIhnen\b'), 'dir'),
    (re.compile(r'\bSie\b'), 'du'),
]

def anrede_to_du(text):
    """Konvertiert echte Höflichkeitsformen in du-Form (deterministisch).
    Nur für Descriptions geeignet (kein Nomen-Verweis-Kontext)."""
    orig = text
    for regex, repl in ANREDE_IMPERATIVE:
        text = regex.sub(repl, text)
    for regex, repl in ANREDE_PRONOUN:
        text = regex.sub(repl, text)
    return text if text != orig else None

# Bekannte Fehl-Phrasen (Bot-Artefakte: Keywords wörtlich klein im Fließtext)
PHRASEN_FIXES = [
    (re.compile(r'\bdns server wechseln\b'), 'DNS-Server wechseln'),
    (re.compile(r'\bdns server\b'), 'DNS-Server'),
    (re.compile(r'\bdsl tipps\b'), 'DSL-Tipps'),
    (re.compile(r'\bgeld sparen im alltag\b'), 'Geld sparen im Alltag'),
    (re.compile(r'\bmietwagen günstig buchen\b'), 'Mietwagen günstig buchen'),
    (re.compile(r'\bfrugalismus tipps\b'), 'Frugalismus-Tipps'),
    (re.compile(r'Jjetzt([A-Za-zÄÖÜäöüß]+)'), r'Jetzt \1'),  # Polish-Artefakt
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
    paths = files or sorted(
        glob.glob(os.path.join(POSTS_DIR, "*.md"))
        + glob.glob(os.path.join(POSTS_DIR, "*", "index.md"))
        + glob.glob(os.path.join(BLOG_DIR, "content", "pillar", "*", "index.md"))
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

        # Optionales Frontmatter-Flag für Sie-Artikel:
        #   anrede: "Sie" → dieser Artikel siezt bewusst (z. B. Senioren-
        #   Zielgruppe) – die automatische du-Konvertierung wird übersprungen.
        anrede_raw = get("anrede").strip('"').lower()
        arts.append({
            "file": os.path.relpath(path, POSTS_DIR), "path": path,
            "title": get("title"), "description": get("description"), "kurzantwort": get("kurzantwort"),
            "fm": fm, "body": body, "content": content,
            "anrede_sie": anrede_raw in ("sie", "sie-form", "höflich"),
        })
    return arts


def extract_words(body, whitelist):
    """Liefert Liste von (wort, start, end) – nur Fließtext, ohne Links/Code/URLs.
    OFFSET-SICHER: Alles, was ignoriert werden soll, wird durch gleich lange
    Leerzeichen maskiert – die start/end-Positionen stimmen exakt mit dem
    Original-Body überein (für sichere Korrekturen)."""
    text = body
    # HTML-Entity &nbsp; durch gleich viele Leerzeichen ersetzen (6 Zeichen →
    # 6 Leerzeichen): Offsets bleiben exakt, "nbsp" wird kein gefundenes Wort
    text = text.replace("&nbsp;", " " * 6)
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

    # 2b. Satzanfang nach Überschrift groß schreiben
    for m in HEADING_START_RE.finditer(body):
        problems.append({
            "type": "heading_start", "word": m.group(2), "fix": m.group(2).upper(),
            "start": m.start(2), "end": m.end(2), "conf": 0.95,
            "reason": f"Satzanfang nach Überschrift: „{m.group(2)}“ → „{m.group(2).upper()}“",
        })

    # MASKED Text (Links/URLs/Code ausgeblendet → keine falschen Treffer durch
    # "../../posts/" o. Ä.; Offsets bleiben gültig, weil die Maskierung gleich
    # lang ist). Wird von den Satzanfangs- und Satzzeichen-Checks genutzt.
    # mask_intervals sammelt die Positionen der Maskierungen, damit der
    # Satzzeichen-Check (2c3) KEINE False Positives bei „…](…),“ meldet
    # (Komma direkt nach einem Markdown-Link ist korrektes Deutsch).
    mask_intervals = []

    def _mask_span(m):
        mask_intervals.append((m.start(), m.end()))
        return " " * (m.end() - m.start())

    body_masked = CODE_RE.sub(_mask_span, body)
    body_masked = URL_RE.sub(_mask_span, body_masked)
    body_masked = LINK_RE.sub(_mask_span, body_masked)
    # &nbsp; (6 Zeichen) → 6 Leerzeichen: gleiche Länge, Offsets bleiben gültig
    body_masked = body_masked.replace("&nbsp;", " " * 6)

    # Markdown-Tabellen-TRENNZEILEN („| :--- | :--- |“ – Spalten-Ausrichtung)
    # sind gültige Syntax; das „Leerzeichen vor :“ wäre ein False Positive.
    # → als maskierte Intervalle markieren (gleiche Länge, Offsets gültig).
    for m in TABLE_SEP_RE.finditer(body_masked):
        mask_intervals.append((m.start(), m.end()))
    body_masked = TABLE_SEP_RE.sub(lambda m: " " * (m.end() - m.start()), body_masked)

    # 2b2. SATZANFANG großschreiben (TOP-LEVEL, deterministisch & robust):
    #      a) Am ABSATZANFANG: erste Zeile eines Blocks (nach Leerzeile oder
    #         Textbeginn), die nicht mit Markdown-Syntax beginnt → erstes Wort groß
    #      b) Nach SATZENDE (. ! ? …): nächstes Wort groß
    #      Schützt: Abkürzungen (z. B., usw., bzw. – danach bleibt klein korrekt),
    #      Markennamen mit CamelCase (iCloud, eBay …), Zeilen, die mit einem
    #      Link beginnen (maskiert), nummerierte Listen, Bullets, Tabellen, Code.
    SATZANFANG_MARKEN = {"icloud", "ebay", "ipad", "iphone", "ipod", "macos", "ios",
                         "mbit", "kbit", "gbit", "mbits", "kbits"}

    def _abk_norm(w):
        # ALLE Nicht-Buchstaben entfernen (Punkte, Spaces, Klammern …),
        # damit "(z. B." und "z. B." gleich normalisiert werden
        return re.sub(r"[^a-zäöüß]", "", w.lower())

    _abk_set = {_abk_norm(a) for a in ABKUERZUNGEN}

    def _ist_abkuerzungsende(text):
        worte = text.split()
        if not worte:
            return False
        # Nummerierung/Datum: "1.", "2.", "30." – der Punkt ist KEIN Satzende
        if worte[-1].rstrip(".").isdigit():
            return True
        if _abk_norm(worte[-1]) in _abk_set:
            return True
        if len(worte) >= 2 and _abk_norm(worte[-2] + worte[-1]) in _abk_set:
            return True
        return False

    def _satzanfang_wort(pos):
        m = re.match(r"[a-zäöüß][a-zäöüßA-ZÄÖÜ0-9\-]*", body_masked[pos:])
        return m.group(0) if m else ""

    def _ist_abkuerzung_wort(pos):
        # Volles Wort bis Whitespace (inkl. Punkt, z. B. "usw." oder "z."):
        # wenn es mit Punkt endet oder eine bekannte Abkürzung ist → Abkürzung
        m = re.match(r"[a-zäöüß][^ \t\n]*", body_masked[pos:])
        if not m:
            return False
        w = m.group(0)
        if w.endswith("."):
            return True
        return _abk_norm(w) in _abk_set

    def _endet_mit_link(orig_text, pos):
        seg = orig_text[max(0, pos - 80):pos]
        letzte_zeile = seg.split("\n")[-1]
        return bool(re.search(r"\[[^\]]*\]\([^)]*\)\s*$", letzte_zeile))

    # a) Absatzanfang großschreiben
    for m in re.finditer(r"(?:^|\n\n)[ \t]*(?:[„“])?([a-zäöüß])", body_masked):
        pos = m.start(1)
        wort = _satzanfang_wort(pos)
        if not wort or wort.lower() in SATZANFANG_MARKEN:
            continue
        if _ist_abkuerzung_wort(pos):
            continue  # "z. B. …" oder "usw. …" am Absatzanfang bleibt klein
        if _endet_mit_link(body, pos):
            continue
        problems.append({
            "type": "satzanfang", "word": m.group(1), "fix": m.group(1).upper(),
            "start": pos, "end": pos + 1, "conf": 0.95,
            "reason": f"Satzanfang: „{m.group(1)}“ → „{m.group(1).upper()}“ (Absatzbeginn)",
        })

    # b) Nach Satzende großschreiben (mit Abkürzungs-Schutz)
    for m in re.finditer(r"([.!?…])\s+([a-zäöüß])", body_masked):
        if _ist_abkuerzungsende(body_masked[max(0, m.start() - 40):m.start(1)]):
            continue
        pos = m.start(2)
        # Beginnt der Satz mit einem Markdown-Link (Link zwischen Satzende und
        # Wort maskiert)? Dann ist der Ankertext der Satzanfang (in der Regel
        # groß geschrieben) → kein Fehler, sonst False Positive wie
        # „…Rechnung. [Eigene Router](../../posts/…) gibt es ab 150 Euro…“
        if any(s > m.start(1) and s < pos for s, e in mask_intervals):
            continue
        wort = _satzanfang_wort(pos)
        if not wort or wort.lower() in SATZANFANG_MARKEN:
            continue
        if _ist_abkuerzung_wort(pos):
            continue  # "…bleibt. usw. das…" – usw. bleibt klein
        problems.append({
            "type": "satzanfang", "word": m.group(2), "fix": m.group(2).upper(),
            "start": pos, "end": pos + 1, "conf": 0.95,
            "reason": f"Satzanfang nach „{m.group(1)}“: „{m.group(2)}“ → „{m.group(2).upper()}“",
        })



    # 2c2. SATZZEICHEN: Abkürzungen mit fehlendem Leerzeichen (Z.B. → z. B.)
    for regex, fix in ABKUERZUNG_FIXES:
        for m in regex.finditer(body_masked):
            problems.append({
                "type": "punctuation", "word": m.group(0), "fix": fix,
                "start": m.start(), "end": m.end(), "conf": 0.95,
                "reason": f"Satzzeichen: „{m.group(0)}“ → „{fix}“",
            })

    # 2c3. SATZZEICHEN: Leerzeichen VOR Satzzeichen entfernen ("Hallo ," → "Hallo,")
    for m in SPACE_BEFORE_PUNCT_RE.finditer(body_masked):
        # Kein False Positive: Leerzeichen stammt aus einer Link-/URL-/Code-Maske
        # (z. B. „…](…),“ – Komma NACH einem Link ist korrekt).
        if any(s <= m.start(1) - 1 < e for s, e in mask_intervals):
            continue
        # Nicht in Links/Code (maskierte Bereiche sind Leerzeichen → kein Treffer)
        problems.append({
            "type": "punctuation", "word": m.group(0), "fix": m.group(1),
            "start": m.start(), "end": m.end(), "conf": 0.95,
            "reason": f"Satzzeichen: Leerzeichen vor „{m.group(1)}“ entfernen",
        })

    # 2c4. SATZZEICHEN: Doppelte Satzzeichen zusammenfassen (".." → ".")
    for m in DOUBLE_PUNCT_RE.finditer(body_masked):
        fix = m.group(0)[0]
        problems.append({
            "type": "punctuation", "word": m.group(0), "fix": fix,
            "start": m.start(), "end": m.end(), "conf": 0.9,
            "reason": f"Satzzeichen: „{m.group(0)}“ → „{fix}“",
        })

    # 2c5. Großbuchstabe nach Abkürzung mitten im Satz → klein
    #      ("z. B. Wenn" → "z. B. wenn"), außer nach Satzende (. ! ?)
    for m in AFTER_ABBR_CAP_RE.finditer(body_masked):
        before = body_masked[max(0, m.start() - 4):m.start()]
        if re.search(r'[.!?]\s*$', before):
            continue  # neuer Satz nach Satzendepunkt – groß korrekt
        w = m.group(1)
        # Whitelist/ambig: Wenn die Kleinform unbekannt ist (Nomen), groß lassen
        r = subprocess.run(["hunspell", "-d", "de_DE", "-l"],
                           input=w.lower() + "\n", capture_output=True, text=True)
        if r.stdout.strip() != "":
            continue  # Nomen/Eigenname – groß korrekt
        abbr = m.group(0).split(w)[0].strip()
        problems.append({
            "type": "punctuation", "word": w, "fix": w.lower(),
            "start": m.start(1), "end": m.end(1), "conf": 0.85,
            "reason": f"Satzzeichen: nach „{abbr}“ klein – „{w}“ → „{w.lower()}“",
        })

    # 2c. Falsche Großschreibung nach Komma (Nicht-Nomen) korrigieren
    for m in COMMA_CAP_RE.finditer(body):
        w = m.group(1)
        # Zeile beginnt mit "#"? → zusammengeführte Überschrift+Text, überspringen
        line_start = body.rfind("\n", 0, m.start()) + 1
        if body[line_start:line_start + 1] == "#":
            continue
        # Höflichkeitsformen groß lassen
        if w.lower() in POLITE_FORMS:
            continue
        # Whitelist
        if w.lower() in whitelist:
            continue
        # Teil eines Kompositums? ("Online-Bonus", "Last-Minute") → nie fixen
        if m.end(1) < len(body) and body[m.end(1):m.end(1) + 1] == "-":
            continue
        # Wenn die KLEINFORM ein Hunspell-FEHLER ist → Nomen (nur groß korrekt,
        # z. B. "gas", "strom") → groß lassen, nicht als Fehler markieren.
        r = subprocess.run(["hunspell", "-d", "de_DE", "-l"],
                           input=w.lower() + "\n", capture_output=True, text=True)
        if r.stdout.strip() != "":
            continue  # Kleinform unbekannt = Nomen/Eigenname → groß korrekt
        # AMBIG: Existiert die GROSSform auch als eigenständiges Wort (Nomen)?
        # ("Steuern" = Abgaben, "Gerät" = Gegenstand, "Decken" = Decke)
        # Dann ist die Großschreibung kontextabhängig → NICHT automatisch fixen.
        r2 = subprocess.run(["hunspell", "-d", "de_DE", "-l"],
                            input=w + "\n", capture_output=True, text=True)
        if r2.stdout.strip() == "":
            continue  # Großform bekannt → ambig → lassen
        problems.append({
            "type": "comma_cap", "word": w, "fix": w.lower(),
            "start": m.start(1), "end": m.end(1), "conf": 0.85,
            "reason": f"Nach Komma klein: „{w}“ → „{w.lower()}“",
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
            # Description beginnt mit Kleinbuchstabe? → Satzanfang groß
            if desc and desc[0].islower():
                problems.append({
                    "type": "heading_start", "word": desc[0], "fix": desc[0].upper(),
                    "abs_start": dstart, "abs_end": dstart + 1, "conf": 0.95,
                    "reason": "Description beginnt klein – Satzanfang groß schreiben",
                })
            # ANREDE-KONSISTENZ: Höflichkeitsform (Sie/Ihre…) in Description
            # → du-Form (Blog-Stil). Wird übersprungen, wenn der Artikel
            # bewusst in Sie-Form geschrieben ist (Frontmatter anrede: "Sie").
            if a.get("anrede_sie"):
                pass  # bewusste Sie-Form – nicht konvertieren
            elif re.search(r'(?<![a-zäöüß])(Sie|Ihre|Ihren|Ihrem|Ihnen)(?![a-zäöüß])', desc) \
               or re.search(r'\b(Erfahren|Entdecken|Nutzen|Vergleichen|Informieren|Melden|Buchen|Sparen|Prüfen|Sichern|Beachten) Sie\b', desc):
                converted = anrede_to_du(desc)
                if converted and converted != desc:
                    problems.append({
                        "type": "anrede", "word": desc, "fix": converted,
                        "abs_start": dstart, "abs_end": dstart + len(desc),
                        "conf": 0.9,
                        "reason": "Description nutzt Höflichkeitsform – Blog-Stil ist du-Ansprache",
                    })
            # DESCRIPTION-ENDPUNKT: Meta-Description muss mit . ! ? enden
            # (vollständiger Satz – Google zeigt sie so in den SERPs).
            # Nur anhängen, wenn der letzte Char kein Satzzeichen ist.
            if desc and desc[-1] not in ".!?…":
                punct_desc = desc.rstrip() + "."
                # Länge im Rahmen halten (max. 160 – ggf. 1 Zeichen kürzen)
                if len(punct_desc) > 160:
                    punct_desc = desc.rstrip()[:159].rstrip() + "."
                problems.append({
                    "type": "desc_punkt", "word": desc, "fix": punct_desc,
                    "abs_start": dstart, "abs_end": dstart + len(desc),
                    "conf": 0.98,
                    "reason": "Description endet ohne Satzzeichen – Punkt ergänzen",
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

    # 3b. KURZANTWORT im Frontmatter mitprüfen (Featured-Snippet-Text!):
    #     Entities (&nbsp;, &amp;) dürfen NICHT als sichtbarer Text erscheinen,
    #     typische KI-Fehler ("less als") werden gefunden.
    kurz = a.get("kurzantwort", "")
    if kurz:
        kstart = a["content"].find("kurzantwort:")
        if kstart >= 0:
            q = a["content"].find('"', kstart + 12)
            if q >= 0:
                kabs = q + 1
                if "&nbsp;" in kurz:
                    problems.append({"type": "entity", "word": "&nbsp;", "fix": "\u00a0",
                                     "abs_start": kabs + kurz.find("&nbsp;"),
                                     "abs_end": kabs + kurz.find("&nbsp;") + 6,
                                     "conf": 1.0, "reason": "Kurzantwort: &nbsp; als sichtbarer Text → geschütztes Leerzeichen (U+00A0)"})
                if "&amp;" in kurz:
                    problems.append({"type": "entity", "word": "&amp;", "fix": "&",
                                     "abs_start": kabs + kurz.find("&amp;"),
                                     "abs_end": kabs + kurz.find("&amp;") + 5,
                                     "conf": 1.0, "reason": "Kurzantwort: &amp; als sichtbarer Text → &"})
                for mm in re.finditer(r"\bless als\b", kurz, re.I):
                    problems.append({"type": "phrase", "word": mm.group(0), "fix": "weniger als",
                                     "abs_start": kabs + mm.start(), "abs_end": kabs + mm.end(),
                                     "conf": 1.0, "reason": "Kurzantwort: „less als“ → „weniger als“"})

    # 3c. ZAHL + EINHEIT: Zwischen Ziffer und %/€ MUSS ein geschütztes Leerzeichen
    #     (U+00A0, Non-Breaking Space) stehen. Mit normalem Leerzeichen bricht der
    #     Browser zwischen Zahl und Einheit um („10 %“ am Zeilenende) – im Body
    #     UND in der Kurzantwort. (Auch Restfälle mit mehreren/doppelten Spaces.)
    def _nbsp_problem(m, base=None):
        word = m.group(0)
        fix = word[0] + "\u00a0" + word[-1]  # Ziffer + NBSP + Einheit
        if base is None:
            return {"type": "nbsp", "word": word, "fix": fix,
                    "start": m.start(), "end": m.end(), "conf": 1.0,
                    "reason": "Zahl+Einheit: normales Leerzeichen → geschütztes (U+00A0), kein Umbruch zwischen Zahl und %/€"}
        return {"type": "nbsp", "word": word, "fix": fix,
                "abs_start": base + m.start(), "abs_end": base + m.end(),
                "conf": 1.0,
                "reason": "Kurzantwort: Zahl+Einheit → geschütztes Leerzeichen (U+00A0), kein Umbruch"}
    for m in re.finditer(r"\d[ \u00a0]+[%€]", body):
        if " " in m.group(0):
            problems.append(_nbsp_problem(m))
    if kurz:
        for m in re.finditer(r"\d[ \u00a0]+[%€]", kurz):
            if " " in m.group(0):
                problems.append(_nbsp_problem(m, kabs))

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
            text = groq_config.chat(prompt, max_tokens=500, timeout=90)
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
