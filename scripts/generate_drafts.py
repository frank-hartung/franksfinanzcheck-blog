#!/usr/bin/env python3
"""
Automatische Blog-Entwurfs-Generierung für Hugo (PaperMod).

- Liest Themen aus data/topics.yaml
- Erzeugt pro Lauf einen frischen Artikel-ENTWURF (draft: true) mit:
  SEO-Titel, Meta-Beschreibung, Keywords, strukturiertem Markdown, FAQ,
  Affiliate-CTA und Werbekennzeichnung
- Nutzt KOSTENLOSE KI-APIs in dieser Reihenfolge:
    1. GROQ_API_KEY  (Gratis-Key in 2 Min.: console.groq.com)
    2. GEMINI_API_KEY (Gratis-Key in 2 Min.: aistudio.google.com)
  (Die früher key-lose Pollinations-API wurde 2026 eingestellt.)
- DEMO_MODE=1 erzeugt einen Test-Entwurf komplett ohne API-Key,
  um die Pipeline lokal zu prüfen.

Warum Entwürfe statt sofort veröffentlichter Artikel?
Google wertet massenhaft automatisch veröffentlichten KI-Content als
Spam (Scaled Content Abuse). Daher: Der Bot schreibt Entwürfe,
DU prüfst und veröffentlichst mit einem Klick. So bleibt der Blog
einzigartig, wertvoll und google-sicher.

Nutzung:
    python3 scripts/generate_drafts.py                # 1 Entwurf
    MAX_ARTIKEL_PRO_LAUF=2 python3 scripts/...        # 2 Entwürfe
    AI_PROVIDER=pollinations python3 scripts/...      # Provider erzwingen
"""

import datetime
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# ---------------------------------------------------------------- Konfiguration
BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
TOPICS_FILE = os.path.join(BLOG_DIR, "data", "topics.yaml")

PINTEREST_PLAN = os.path.join(BLOG_DIR, "data", "pinterest_plan.yaml")

MAX_ARTICLES = int(os.environ.get("MAX_ARTIKEL_PRO_LAUF", "1"))
AUTHOR = os.environ.get("BLOG_AUTHOR", "Redaktion")
AFFILIATE_URL = os.environ.get(
    "AFFILIATE_URL",
    "https://a.check24.net/misc/click.php?pid=80968&aid=18",
)

# Schreib-Stile, die rotieren – so wird jeder Artikel einzigartig
ANGLES = [
    ("ratgeber", "Schritt-für-Schritt-Ratgeber mit klarer Anleitung und Zwischenüberschriften"),
    ("vergleich", "sachlicher Vergleichs-Artikel: worauf man achten muss, Vor- und Nachteile"),
    ("fehler", "Artikel über die häufigsten Fehler und wie man sie vermeidet"),
    ("faq", "FAQ-lastiger Artikel: alle wichtigen Fragen und klare Antworten"),
    ("checkliste", "kompakter Artikel mit Checklisten und Praxistipps"),
    ("hintergrund", "Hintergrund-Artikel: wie es funktioniert, was sich 2026 geändert hat"),
]

# Zusätzliche Variation: Erzählperspektive (wird zufällig zum Stil kombiniert,
# damit zwei Artikel zum selben Thema nie gleich klingen)
PERSPECTIVES = [
    ("direkt", "Sprich den Leser direkt mit 'du' an und gib ihm konkrete Handlungsanweisungen"),
    ("erfahrung", "Schreibe aus der Ich-Perspektive, als hättest du es selbst ausprobiert (mit Beispielen aus dem Alltag)"),
    ("neutral", "Schreibe sachlich-neutral wie ein unabhängiger Tester, ohne Ich-Form"),
    ("story", "Eröffne mit einer kurzen Alltagsgeschichte/Beispielsituation, dann die Erklärung"),
    ("fragen", "Stelle zu Beginn 2-3 Leitfragen, die der Artikel beantwortet"),
]

# Einzigartigkeits-Schutz: Wie viele übereinstimmende 7-Wort-Phrasen mit der
# Pin-Beschreibung sind maximal erlaubt, bevor der Artikel als "zu ähnlich"
# gilt und neu generiert wird.
MAX_SIMILAR_PHRASES = 1
PHRASE_LEN = 7

SYSTEM_PROMPT = (
    "Du bist ein deutschsprachiger, seriöser Finanz- und Verbraucher-Ratgeber-Autor. "
    "Du schreibst ehrliche, hilfreiche und sachlich korrekte Artikel. "
    "Du erfindest keine konkreten Preise oder Anbieterbewertungen. "
    "Du schreibst im Dativ-Stil neutral und ohne Werbesprech."
)

# ---------------------------------------------------------------- Hilfsfunktionen


def load_topics():
    """Lädt data/topics.yaml (minimalistischer YAML-Parser, nur unser Format)."""
    topics = []
    with open(TOPICS_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("- title:"):
                t = line.split(":", 1)[1].strip().strip("\"'")
                topics.append({"title": t, "keywords": [], "affiliate_url": None})
            elif line.startswith("keywords:") and topics:
                raw = line.split(":", 1)[1].strip()
                topics[-1]["keywords"] = [k.strip().strip("\"'") for k in raw.strip("[]").split(",")]
            elif line.startswith("affiliate_url:") and topics:
                topics[-1]["affiliate_url"] = line.split(":", 1)[1].strip().strip("\"'")
    if not topics:
        sys.exit("FEHLER: Keine Themen in data/topics.yaml gefunden.")
    return topics


def existing_titles():
    """Listet bereits vorhandene Artikel-Titel (für Duplikat-Schutz)."""
    titles = set()
    if not os.path.isdir(POSTS_DIR):
        return titles
    for fn in os.listdir(POSTS_DIR):
        if not fn.endswith(".md"):
            continue
        with open(os.path.join(POSTS_DIR, fn), encoding="utf-8") as f:
            content = f.read()
        m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.M)
        if m:
            titles.add(m.group(1).strip().lower())
    return titles


def topic_already_covered(topic_title, used_titles):
    """Prüft, ob ein Thema bereits durch einen vorhandenen Artikel abgedeckt ist.
    Vergleicht normalisierte Titel: Wenn der Themen-Titel (normalisiert) in einem
    vorhandenen Artikel-Titel steckt (oder umgekehrt), gilt das Thema als erledigt."""
    def norm(s):
        s = s.lower()
        s = re.sub(r"[äàáâ]", "ae", s)
        s = re.sub(r"[öòóô]", "oe", s)
        s = re.sub(r"[üùúû]", "ue", s)
        s = re.sub(r"ß", "ss", s)
        return re.sub(r"[^a-z0-9]+", " ", s).strip()

    t = norm(topic_title)
    if not t:
        return False
    t_tokens = t.split()[:4]  # erste 4 Wörter als Kern des Themas
    for title in used_titles:
        nt = norm(title)
        if t in nt or nt in t:
            return True
        # Präfix-Abgleich: gleiche ersten 4 Wörter = gleiches Thema
        if t_tokens and nt.split()[:4] == t_tokens:
            return True
    return False


def slugify(text):
    """Erzeugt einen URL-freundlichen Slug aus deutschem Text."""
    text = text.lower()
    text = re.sub(r"[äàáâ]", "ae", text)
    text = re.sub(r"[öòóô]", "oe", text)
    text = re.sub(r"[üùúû]", "ue", text)
    text = re.sub(r"ß", "ss", text)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:80].strip("-")


def yaml_str(s):
    """Sicheres Quoting für YAML-Frontmatter."""
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


def http_json(url, data=None, headers=None, timeout=90):
    """HTTP-Helfer (nur Standardbibliothek)."""
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_text(url, timeout=90):
    req = urllib.request.Request(url, headers={"User-Agent": "hugo-blog-bot/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


# ---------------------------------------------------------------- Pinterest-Inspiration


def load_pinterest_plan():
    """Lädt data/pinterest_plan.yaml (62 Pins als INSPIRATIONSQUELLE)."""
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
    """Findet den thematisch passenden Pin (für Inspiration + Einzigartigkeits-Check)."""
    def norm(s):
        s = s.lower()
        s = re.sub(r"[äàáâ]", "ae", s)
        s = re.sub(r"[öòóô]", "oe", s)
        s = re.sub(r"[üùúû]", "ue", s)
        s = re.sub(r"ß", "ss", s)
        return re.sub(r"[^a-z0-9]+", " ", s).strip()

    t = norm(topic_title)
    best, best_score = None, 0
    for p in pins:
        ref = norm((p.get("titel") or "") + " " + (p.get("pinwand") or ""))
        # Überlappung der ersten Wörter
        score = 0
        t_tokens = t.split()
        for i in range(min(len(t_tokens), 6)):
            if i < len(ref.split()) and t_tokens[i] == ref.split()[i]:
                score += 1
        if score > best_score:
            best, best_score = p, score
    return best if best_score >= 2 else None


def uniqueness_check(text, pin, max_similar=MAX_SIMILAR_PHRASES, n=PHRASE_LEN):
    """Prüft, ob der generierte Text zu viele 7-Wort-Phrasen mit der Pin-Beschreibung
    gemeinsam hat. Liefert (ok, anzahl_treffer, beispiele)."""
    ref_text = " ".join(filter(None, [
        pin.get("titel", ""), pin.get("beschreibung", ""), pin.get("keywords", "")
    ])).lower()
    if len(ref_text.split()) < n:
        return True, 0, []

    words = re.findall(r"\w+", text.lower())
    if len(words) < n:
        return True, 0, []

    ref_words = re.findall(r"\w+", ref_text)
    ref_grams = set()
    for i in range(len(ref_words) - n + 1):
        ref_grams.add(" ".join(ref_words[i:i + n]))

    hits, examples = 0, []
    for i in range(len(words) - n + 1):
        gram = " ".join(words[i:i + n])
        if gram in ref_grams:
            hits += 1
            if len(examples) < 3:
                examples.append(gram)
    return hits <= max_similar, hits, examples




def call_groq(prompt):
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    body = {
        "model": os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.9,
        "max_tokens": 1800,
    }
    data = json.dumps(body).encode("utf-8")
    resp = http_json(
        "https://api.groq.com/openai/v1/chat/completions",
        data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    return resp["choices"][0]["message"]["content"]


def call_gemini(prompt):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    data = json.dumps(body).encode("utf-8")
    resp = http_json(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    return resp["candidates"][0]["content"]["parts"][0]["text"]


def call_pollinations(prompt):
    """Key-lose Fallback-API – 2026 weitgehend abgekündigt (meist 402)."""
    url = "https://text.pollinations.ai/" + urllib.parse.quote(prompt)
    return http_text(url, timeout=120)


def demo_article(topic, angle):
    """Erzeugt einen lokalen Test-Entwurf OHNE API-Key (DEMO_MODE=1)."""
    _, angle_desc = angle
    date = datetime.date.today().isoformat()
    return (
        f"TITLE: {topic} – der kompakte Ratgeber\n"
        f"DESCRIPTION: Alles Wichtige zu {topic}: Vor- und Nachteile, Tipps und häufige Fragen – kompakt und verständlich erklärt.\n"
        f"\n"
        f"Wer sich mit {topic.lower()} beschäftigt, steht schnell vor vielen Fragen. Dieser Artikel gibt dir eine klare, ehrliche Übersicht – ohne Fachchinesisch und ohne versteckte Kosten.\n"
        f"\n"
        f"## Warum sich das Thema lohnt\n"
        f"Gerade 2026 gibt es einige Neuerungen und Angebote, die du kennen solltest. Wer sich früh informiert und vergleicht, kann spürbar profitieren. Wichtig ist, dass du nicht nur auf den ersten Blick günstige Angebote nimmst, sondern auf die Konditionen im Detail achtest.\n"
        f"\n"
        f"## Das Wichtigste in Kürze\n"
        f"\n"
        f"- Vergleiche immer mehrere Angebote, bevor du dich entscheidest\n"
        f"- Achte auf Laufzeiten, Kündigungsfristen und versteckte Gebühren\n"
        f"- Boni sind nur dann ein Vorteil, wenn du die Bedingungen erfüllst\n"
        f"- Prüfe deinen Vertrag einmal im Jahr – automatische Verlängerungen sind teuer\n"
        f"\n"
        f"## So gehst du am besten vor\n"
        f"{angle_desc}.[DEMO-ENTWURF] Beschreibe hier in 2–3 Absätzen die konkreten Schritte: 1. Ausgangslage prüfen, 2. Angebote vergleichen, 3. Antrag stellen, 4. Bestätigung prüfen.\n"
        f"\n"
        f"## Häufige Fehler, die dich Geld kosten\n"
        f"Der größte Fehler ist, nie zu vergleichen und im teuren Standardtarif zu bleiben. Ebenso problematisch: nur auf den Preis zu schauen und Leistungen zu ignorieren. Und: Einmal abgeschlossen, nie wieder angeschaut – so verlierst du jedes Jahr Geld.\n"
        f"\n"
        f"## Häufige Fragen\n"
        f"\n"
        f"### Ist ein Wechsel wirklich kostenlos?\n"
        f"In den meisten Fällen ja. Der neue Anbieter übernimmt in der Regel die Kündigung des alten Vertrags für dich.\n"
        f"\n"
        f"### Wie lange dauert der Wechsel?\n"
        f"Meist zwei bis sechs Wochen. Es gibt in der Regel keine Versorgungslücke.\n"
        f"\n"
        f"### Wie oft sollte ich vergleichen?\n"
        f"Einmal pro Jahr reicht in den meisten Fällen – idealerweise kurz vor Ablauf der Vertragslaufzeit.\n"
        f"\n"
        f"---\n"
        f"\n"
        f"[DEMO-ENTWURF – Dieser Artikel wurde im Demo-Modus ohne KI erzeugt, um die Pipeline zu testen.]"
    )


PROVIDERS = [
    ("Groq (Gratis-Key: console.groq.com)", call_groq),
    ("Gemini (Gratis-Key: aistudio.google.com)", call_gemini),
    ("Pollinations (legacy, meist deaktiviert)", call_pollinations),
]


def generate_article_text(topic, angle, perspective=None, pin=None):
    """Baut den Prompt und ruft die KI auf. Liefert (rohtext, provider).

    - angle:      Schreibstil (Ratgeber, Vergleich, FAQ …)
    - perspective: Erzählperspektive (direkt, Erfahrung, neutral …)
    - pin:        der zugehörige Pinterest-Pin – NUR als Inspiration,
                  der Artikel muss eigenständig formuliert sein.
    """
    if os.environ.get("DEMO_MODE") == "1":
        return demo_article(topic, angle), "Demo (ohne API-Key)"

    angle_name, angle_desc = angle
    if perspective is None:
        perspective = random.choice(PERSPECTIVES)
    _, persp_desc = perspective

    # Pin nur als Inspiration einbetten (Thema/Keywords), NIEMALS als Kopiervorlage
    inspiration = ""
    if pin:
        inspiration = (
            "INSPIRATION (nur zur Orientierung, NICHT übernehmen):\n"
            f"- Ursprünglicher Pin-Titel: {pin.get('titel', '')}\n"
            f"- Pinwand: {pin.get('pinwand', '')}\n"
            f"- Stichwörter: {pin.get('keywords', '')}\n"
            "WICHTIG: Der Pin-Text ist nur eine Anregung. Schreibe den Artikel "
            "KOMPLETT NEU in deinen eigenen Worten. Übernimm KEINE Sätze, "
            "KEINE Formulierungen und KEINE Satzstrukturen aus dem Pin. "
            "Wähle eine eigene Überschrift und eine eigene Struktur.\n"
        )

    prompt = f"""Schreibe einen EINZIGARTIGEN, hilfreichen deutschen Blog-Artikel zum Thema:
"{topic}"

{inspiration}
Stil des Artikels: {angle_desc}.
Erzählperspektive: {persp_desc}.

FORMAT – halte dich GENAU daran (wichtig für die Weiterverarbeitung):
Zeile 1: TITLE: Ein prägnanter, klickstarker Titel (max. 60 Zeichen). Wähle einen FRISCHEN Blickwinkel – verwende NICHT den Pin-Titel und nicht wörtlich das Thema.
Zeile 2: DESCRIPTION: Eine Meta-Beschreibung (max. 155 Zeichen, mit wichtigstem Keyword)
Ab Zeile 3: Der Artikel in Markdown:
- Keine Überschrift für den Titel am Anfang (Titel steht schon in Zeile 1)
- Beginne mit einem einleitenden Absatz (erst bei der Perspektive "story"/"fragen" mit einer Geschichte/Frage)
- 4 bis 6 Abschnitte mit H2-Überschriften (##) – strukturiere sie ANDERS als die Pin-Vorlage
- Optional kurze Listen oder eine Tabelle
- Am Ende ein FAQ-Bereich: "## Häufige Fragen" mit 3 Fragen als H3 und Antworten
- 400 bis 700 Wörter insgesamt
- KEINE Links einfügen, KEINE konkreten Preise oder Zahlen erfinden
- Schreibe so, dass der Artikel echtes Wissen vermittelt und jemandem hilft
- Originalität ist Pflicht: eigener Wortlaut, eigene Beispiele, eigene Abschnittsfolge
"""
    forced = os.environ.get("AI_PROVIDER")
    for name, fn in PROVIDERS:
        if forced and forced.lower() not in name.lower():
            continue
        try:
            print(f"  → Versuche Provider: {name}")
            text = fn(prompt)
            if text and len(text.strip()) > 200:
                return text.strip(), name
            print("    Antwort zu kurz oder leer, nächster Provider …")
        except urllib.error.HTTPError as e:
            print(f"    Provider-Fehler ({e.code}), nächster Provider …")
        except Exception as e:
            print(f"    Provider-Fehler ({type(e).__name__}: {e}), nächster Provider …")
    return None, None


# ---------------------------------------------------------------- Artikel bauen


def parse_article(raw, topic, angle_name):
    """Extrahiert Titel, Beschreibung und Body aus dem KI-Output."""
    title, desc, body = None, None, raw
    lines = raw.split("\n")
    if lines and lines[0].startswith("TITLE:"):
        title = lines[0][6:].strip()
    if len(lines) > 1 and lines[1].startswith("DESCRIPTION:"):
        desc = lines[1][12:].strip()
        body = "\n".join(lines[2:]).strip()
    if not title:
        m = re.search(r"^#\s+(.+)$", raw, re.M)
        title = m.group(1).strip() if m else topic
    if not desc:
        m = re.search(r"^(.+)$", body, re.M)
        desc = (m.group(1).strip() if m else topic)[:155]
    desc = desc[:155]
    # Code-Fences entfernen, falls die KI welche setzt
    body = re.sub(r"^```[a-zA-Z]*\s*$", "", body, flags=re.M).strip()
    return title, desc, body


def write_draft(topic_entry, angle, provider, used_titles):
    """Erzeugt eine Draft-Datei. Gibt True zurück, wenn etwas geschrieben wurde.

    Der Artikel wird gegen die passende Pin-Beschreibung geprüft
    (Einzigartigkeits-Check). Ist er zu ähnlich, wird bis zu 2× mit
    anderem Stil/Perspektive neu generiert.
    """
    topic = topic_entry["title"]
    keywords = topic_entry["keywords"]
    affiliate_url = topic_entry.get("affiliate_url") or AFFILIATE_URL
    pins = load_pinterest_plan()
    pin = find_pin_for_topic(topic, pins)
    print(f"\n=== Thema: {topic} | Stil: {angle[0]} ===")
    if pin:
        print(f"    Inspiration: Pinterest-Pin (Tag {pin.get('tag')}) – wird nur als Grundlage genutzt")

    raw, provider_name = generate_article_text(topic, angle, perspective=None, pin=pin)
    if not raw:
        has_key = bool(os.environ.get("GROQ_API_KEY") or os.environ.get("GEMINI_API_KEY"))
        if not has_key:
            print("  ✗ KEIN API-KEY gefunden. So aktivierst du die Automatisierung:")
            print("    1) Gratis-Key holen (2 Min., ohne Zahlungsdaten):")
            print("       Groq   → https://console.groq.com")
            print("       Gemini → https://aistudio.google.com")
            print("    2) Im GitHub-Repo: Settings → Secrets and variables → Actions")
            print("       → New repository secret → GROQ_API_KEY (oder GEMINI_API_KEY)")
            print("    Alternativ lokal testen: DEMO_MODE=1 python3 scripts/generate_drafts.py")
        else:
            print("  ✗ Provider haben geantwortet, aber mit Fehlern – Logs oben prüfen.")
        return False

    # Einzigartigkeits-Check: zu ähnlich zum Pin? → neu generieren (max. 2 Versuche)
    for attempt in range(1, 3):
        title, desc, body = parse_article(raw, topic, angle[0])
        if title.lower() in used_titles:
            print(f"  ✗ Titel existiert bereits ({title[:50]}…) – Duplikat-Schutz.")
            return False
        if pin:
            ok, hits, examples = uniqueness_check(body, pin)
            if not ok:
                print(f"  ⚠ Zu ähnlich zum Pinterest-Pin ({hits} gleiche Phrasen, Versuch {attempt})")
                for ex in examples:
                    print(f"    → „{ex}…“")
                print(f"  ↻ Generiere mit anderem Stil neu …")
                other_angles = [a for a in ANGLES if a[0] != angle[0]]
                other_persp = [p for p in PERSPECTIVES if p[0] != (getattr(angle, 'persp', None) or '')]
                new_angle = random.choice(other_angles)
                raw, provider_name = generate_article_text(topic, new_angle,
                                                           perspective=random.choice(PERSPECTIVES),
                                                           pin=pin)
                if not raw:
                    return False
                angle = new_angle
                continue
        break

    title, desc, body = parse_article(raw, topic, angle[0])
    used_titles.add(title.lower())
    date = datetime.date.today().isoformat()
    slug = slugify(title)
    filename = os.path.join(POSTS_DIR, f"{date}-{slug}.md")

    cta = (
        "\n---\n\n"
        f"👉 **Jetzt vergleichen und sparen:** [**→ Jetzt Angebote vergleichen**]({affiliate_url})\n\n"
        "*Dieser Artikel enthält Affiliate-Links (Werbung). Beim Abschluss über einen Link "
        "erhalten wir eine Provision – für dich entstehen keine Mehrkosten.*\n"
    )
    inspiration_line = ""
    if pin:
        inspiration_line = (
            f"inspiration: Pin {pin.get('tag')} – „{pin.get('titel', '')}“ "
            "(nur Themen-Grundlage, eigenständig formuliert)\n"
        )
    frontmatter = (
        "---\n"
        f"title: {yaml_str(title)}\n"
        f"description: {yaml_str(desc)}\n"
        f"date: {date}\n"
        "draft: true\n"
        f'tags: {json.dumps(keywords[:4], ensure_ascii=False)}\n'
        f'categories: ["Ratgeber"]\n'
        f"keywords: {json.dumps(keywords, ensure_ascii=False)}\n"
        f"author: {yaml_str(AUTHOR)}\n"
        f"ai_generated: true\n"
        f"ai_provider: {yaml_str(provider_name)}\n"
        f"{inspiration_line}"
        "---\n\n"
    )
    with open(filename, "w", encoding="utf-8") as f:
        f.write(frontmatter + body + "\n" + cta)
    print(f"  ✓ Entwurf erstellt: {os.path.relpath(filename, BLOG_DIR)}")
    print(f"    Titel: {title}")
    print(f"    Beschreibung: {desc}")
    print(f"    Provider: {provider_name}")
    return True


# ---------------------------------------------------------------- Hauptprogramm


def main():
    if not os.path.isdir(POSTS_DIR):
        os.makedirs(POSTS_DIR, exist_ok=True)
    topics = load_topics()
    used_titles = existing_titles()
    print(f"Content-Bot gestartet – {len(topics)} Themen verfügbar, "
          f"{MAX_ARTICLES} Entwurf/Entwürfe geplant, "
          f"{len(used_titles)} bestehende Artikel erkannt.")

    created = 0
    attempts = 0
    random.shuffle(topics)
    while created < MAX_ARTICLES and attempts < MAX_ARTICLES * 3:
        attempts += 1
        topic_entry = topics[(attempts - 1) % len(topics)]
        if topic_already_covered(topic_entry["title"], used_titles):
            print(f"  – Thema bereits behandelt, übersprungen: {topic_entry['title'][:60]}…")
            continue
        angle = ANGLES[(attempts - 1) % len(ANGLES)]
        if write_draft(topic_entry, angle, provider=None, used_titles=used_titles):
            created += 1
        time.sleep(2)

    print(f"\nFertig: {created} neue Entwürfe (draft: true). "
          "Zum Veröffentlichen draft auf 'false' setzen (siehe README).")


if __name__ == "__main__":
    main()
