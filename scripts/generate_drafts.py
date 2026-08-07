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
AUTHOR = os.environ.get("BLOG_AUTHOR") or "Frank"
# E-E-A-T: Autor immer setzen – kein leerer Author (Google braucht die
# Autoren-Zuordnung für die E-E-A-T-Bewertung)
AFFILIATE_URL = os.environ.get("AFFILIATE_URL") or "https://a.check24.net/misc/click.php?pid=80968&aid=18"

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

# Anrede: Standard "du" – per Umgebungsvariable BLOG_ANREDE=sie auf Sie-Form umstellbar
ANREDE = os.environ.get("BLOG_ANREDE", "du").lower()
if ANREDE == "sie":
    SYSTEM_ANREDE = (
        "Du sprichst den Leser mit der HOEFLICHKEITSFORM an (Sie, Ihre, Ihnen) - "
        "konsistent durchgehend, kein Wechsel zu du."
    )
    ANREDE_PRON = "Sie/Ihnen/Ihre"
    ANREDE_VERB = "Sie"
else:
    SYSTEM_ANREDE = (
        "Du sprichst den Leser durchgehend mit du an (du, dein, dich) - "
        "konsistent, kein Wechsel zur Hoeflichkeitsform."
    )
    ANREDE_PRON = "du/dein/dich"
    ANREDE_VERB = "du"

SYSTEM_PROMPT = (
    "Du bist ein deutschsprachiger, seriöser Finanz- und Verbraucher-Ratgeber-Autor auf "
    "PROFI-NIVEAU – vergleichbar mit den besten unabhängigen Finanzblogs im DACH-Raum. "
    "Du schreibst ehrliche, hilfreiche und sachlich korrekte Artikel. "
    "Du erfindest keine konkreten Preise oder Anbieterbewertungen – Preise nennst du nur "
    "als vorsichtige Spannen (\"ca. X–Y €\") oder mit \"in der Regel\". "
    "Du schreibst in AKTIVER, lebendiger Sprache: kurze Sätze (max. ~20 Wörter), starke "
    "Verben. " + SYSTEM_ANREDE + " Kein Passiv, keine Füllphrasen, kein Werbesprech. "
    "Du verzichtest auf typische KI-Floskeln wie \"In der heutigen schnelllebigen Welt\", "
    "\"Es ist wichtig zu beachten\", \"Zusammenfassend lässt sich sagen\", \"Des Weiteren\", "
    "\"Es gibt viele Möglichkeiten\", \"heutzutage\", \"Tauchen wir ein\". "
    "Deine Texte sind journalistisch, konkret, praxisnah und vermitteln echten Nutzen. "
    "Jeder Absatz ist 3–4 Sätze lang. Deutsche Rechtschreibung ist fehlerfrei."
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


def demo_files():
    """Findet Demo-Artikel (mit Marker 'demo-artikel' im Inhalt) – NUR diese
    dürfen vom Aufräum-Prozess gelöscht werden. Schützt echte Bot-Artikel."""
    demos = []
    if not os.path.isdir(POSTS_DIR):
        return demos
    for fn in os.listdir(POSTS_DIR):
        if not fn.endswith(".md"):
            continue
        with open(os.path.join(POSTS_DIR, fn), encoding="utf-8") as f:
            if "demo-artikel" in f.read():
                demos.append(fn)
    return demos


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
    """HTTP-Helfer (nur Standardbibliothek).
    WICHTIG: Browser-User-Agent setzen – Cloudflare blockt Requests ohne
    User-Agent (Error 1010/403), wie es im GitHub-Runner passiert ist."""
    hdrs = dict(headers or {})
    hdrs.setdefault("User-Agent",
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
    req = urllib.request.Request(url, data=data, headers=hdrs)
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


# KI-Floskeln, die in Profi-Texten nie vorkommen dürfen
PROFI_FLOSKELN = [
    "in der heutigen schnelllebigen welt", "in der heutigen zeit",
    "es ist wichtig zu beachten", "zusammenfassend lässt sich sagen",
    "zusammenfassend kann man sagen", "des weiteren", "in diesem artikel werden wir",
    "in diesem artikel erfahren sie", "es gibt viele möglichkeiten",
    "es gibt zahlreiche", "wenn es darum geht", "heutzutage",
    "in der modernen welt", "tauchen wir ein", "lassen sie uns",
    "der schlüssel zum erfolg", "ein muss für jeden", "unverzichtbar für",
    "das a und o", "die welt der", "in einer welt, in der",
]


def profi_quality_ok(body, keywords=None):
    """Prüft einen frisch generierten Artikel auf Profi-Niveau.
    Liefert (ok, probleme). Wird in der Regenerierungs-Schleife genutzt."""
    problems = []
    text = re.sub(r"[#*_>`|~\[\]()-]", " ", body)
    text = re.sub(r"\s+", " ", text).lower()
    words = len(re.findall(r"\w+", text))

    if words < 400:
        problems.append(f"nur {words} Wörter (Profi: 400+)")
    h2 = len(re.findall(r"^##\s", body, re.M))
    if h2 < 4:
        problems.append(f"nur {h2} H2-Abschnitte")
    faq = len(re.findall(r"^###\s.*\?", body, re.M))
    if faq < 2:
        problems.append(f"nur {faq} FAQ-Fragen")
    floskeln = [f for f in PROFI_FLOSKELN if f in text]
    if floskeln:
        problems.append(f"KI-Floskeln: {', '.join(floskeln[:2])}")
    if keywords:
        kws = [k.strip().strip('"').lower() for k in keywords if k.strip()]
        if kws and kws[0] not in text:
            problems.append(f"Keyword „{kws[0]}“ fehlt")
    if not re.search(r"(^|\n)[-*]\s", body, re.M) and "|" not in body:
        problems.append("keine Liste/Tabelle")

    return len(problems) == 0, problems


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




def _retry(fn, attempts=3, base_delay=3):
    """Führt fn mit Wiederholungen aus (Timeout/5xx-robust)."""
    last_err = None
    for i in range(attempts):
        try:
            return fn()
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(base_delay * (i + 1))
                continue
            raise
        except (TimeoutError, urllib.error.URLError, ConnectionError):
            last_err = None
            time.sleep(base_delay * (i + 1))
    if last_err:
        raise last_err
    raise TimeoutError("API nach mehreren Versuchen nicht erreichbar")


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

    def _call():
        resp = http_json(
            "https://api.groq.com/openai/v1/chat/completions",
            data=data,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        )
        return resp["choices"][0]["message"]["content"]

    return _retry(_call)


def call_gemini(prompt):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    model = os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    data = json.dumps(body).encode("utf-8")

    def _call():
        resp = http_json(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        return resp["candidates"][0]["content"]["parts"][0]["text"]

    return _retry(_call)


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


def generate_article_text(topic, angle, perspective=None, pin=None, keywords=None):
    """Baut den Prompt und ruft die KI auf. Liefert (rohtext, provider).

    - angle:      Schreibstil (Ratgeber, Vergleich, FAQ …)
    - perspective: Erzählperspektive (direkt, Erfahrung, neutral …)
    - pin:        der zugehörige Pinterest-Pin – NUR als Inspiration,
                  der Artikel muss eigenständig formuliert sein.
    - keywords:   Ziel-Keywords – der Artikel soll sie natürlich einbauen
                  (automatische Keyword-Optimierung neuer Artikel).
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

    # Automatische Keyword-Optimierung: Ziel-Keywords in den Prompt einbauen
    keyword_hint = ""
    if keywords:
        kw_list = ", ".join(keywords[:5])
        keyword_hint = (
            f"SEO-KEYWORDS (natürlich und ungezwungen in den Text einbauen): {kw_list}\n"
            "Anforderungen: Das Haupt-Keyword (das erste) MUSS vorkommen in: "
            "Titel (TITLE-Zeile), Meta-Beschreibung (DESCRIPTION-Zeile), "
            "dem ersten Absatz und mindestens einer H2-Überschrift. "
            "Die Keywords insgesamt 3-6 Mal natürlich verteilen – "
            "KEIN Keyword-Stuffing, KEINE künstliche Aufzählung.\n"
        )

    anrede_var = "Du-Form (du/dein/dich)" if os.environ.get("BLOG_ANREDE", "du").lower() != "sie" else "Sie-Form (Sie/Ihnen/Ihre)"
    prompt = f"""Schreibe einen EINZIGARTIGEN, hilfreichen deutschen Blog-Artikel zum Thema:
"{topic}"

{inspiration}{keyword_hint}
Stil des Artikels: {angle_desc}.
Erzählperspektive: {persp_desc}.

FORMAT – halte dich GENAU daran (wichtig für die Weiterverarbeitung):
Zeile 1: TITLE: Ein prägnanter, klickstarker Titel (max. 60 Zeichen). Wähle einen FRISCHEN Blickwinkel – verwende NICHT den Pin-Titel und nicht wörtlich das Thema.
Zeile 2: DESCRIPTION: Eine Meta-Beschreibung (max. 155 Zeichen, mit wichtigstem Keyword)
Ab Zeile 3: Der Artikel in Markdown:
- Keine Überschrift für den Titel am Anfang (Titel steht schon in Zeile 1)
- Einleitung mit starkem HAKEN: Nutzenversprechen, konkrete Frage oder überraschende Zahl –
  KEIN generischer Einstieg ("In der heutigen Zeit…", "Geld sparen ist wichtig…")
- 4 bis 6 Abschnitte mit H2-Überschriften (##) – strukturiere sie ANDERS als die Pin-Vorlage
- Mindestens EINE Liste oder Tabelle (Mehrwert, Scannability)
- Am Ende ein FAQ-Bereich: "## Häufige Fragen" mit 3 Fragen als H3 und Antworten
- 500 bis 800 Wörter insgesamt – substanziell, aber ohne Blabla
- Absätze max. 3–4 Sätze, aktive Sprache ("du"), kurze Sätze (max. ~20 Wörter)
- ANREDE: {anrede_var} – konsistent durchgehend verwenden
- PRAXISBEZUG (E-E-A-T): konkrete, plausible Alltagsbeispiele; eigene Erfahrung als
  Formulierung erlaubt ("Ich habe…", "In der Praxis…") – aber KEINE erfundenen Fakten,
  KEINE konkreten Preise; Preisspannen nur mit "ca." oder "in der Regel"
- KEINE KI-Floskeln: verboten sind u.a. "In der heutigen schnelllebigen Welt", "Es ist
  wichtig zu beachten", "Zusammenfassend lässt sich sagen", "Des Weiteren", "Es gibt viele
  Möglichkeiten", "heutzutage", "Tauchen wir ein", "Der Schlüssel zum Erfolg"
- KEINE Links einfügen, KEINE konkreten Zahlen erfinden
- Deutsche Orthografie: korrekte Groß-/Kleinschreibung, korrekte Anführungszeichen ("…")
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


def write_draft(topic_entry, angle, provider, used_titles, auto_publish=False):
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

    raw, provider_name = generate_article_text(topic, angle, perspective=None, pin=pin, keywords=keywords)
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

    # Qualitäts-Schleife (Profi-Niveau): Pin-Ähnlichkeit ODER Text unter
    # Profi-Schwelle → mit anderem Stil neu generieren (max. 3 Versuche)
    for attempt in range(1, 4):
        title, desc, body = parse_article(raw, topic, angle[0])
        if title.lower() in used_titles:
            print(f"  ✗ Titel existiert bereits ({title[:50]}…) – Duplikat-Schutz.")
            return False
        reason = None
        if pin:
            ok, hits, examples = uniqueness_check(body, pin)
            if not ok:
                reason = f"zu ähnlich zum Pinterest-Pin ({hits} gleiche Phrasen)"
                for ex in examples:
                    print(f"    → „{ex}…“")
        if not reason:
            ok_profi, prob = profi_quality_ok(body, keywords)
            if not ok_profi:
                reason = "Profi-Qualität nicht erreicht: " + "; ".join(prob)
        if reason:
            print(f"  ⚠ {reason} (Versuch {attempt}/3)")
            print(f"  ↻ Generiere mit anderem Stil neu …")
            other_angles = [a for a in ANGLES if a[0] != angle[0]]
            new_angle = random.choice(other_angles) if other_angles else angle
            raw, provider_name = generate_article_text(topic, new_angle,
                                                       perspective=random.choice(PERSPECTIVES),
                                                       pin=pin, keywords=keywords)
            if not raw:
                return False
            angle = new_angle
            continue
        break
    else:
        print("  ✗ 3 Versuche ohne Profi-Niveau – Artikel wird übersprungen.")
        return False

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
    draft_flag = "false" if auto_publish else "true"
    frontmatter = (
        "---\n"
        f"title: {yaml_str(title)}\n"
        f"description: {yaml_str(desc)}\n"
        f"date: {date}\n"
        f"draft: {draft_flag}\n"
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


def load_affiliate_links():
    """Lädt die zentralen Affiliate-Links aus scripts/check24_links.yaml.
    Wenn sich die Links ändern, genügt es, DIESE Datei zu aktualisieren –
    der Bot verwendet automatisch die neuen Links für alle neuen Artikel."""
    links = {}
    path = os.path.join(BLOG_DIR, "scripts", "check24_links.yaml")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"^\s*([a-z-]+):\s*[\"'](.+?)[\"']\s*(?:#.*)?$", line)
                if m:
                    cat, url = m.group(1), m.group(2)
                    if url and not url.startswith("DEIN-LINK"):
                        links[cat] = url
    return links


def category_from_pin(pin):
    """Leitet die Affiliate-Kategorie aus der Pin-Ziel-URL bzw. Pinwand ab.
    Liefert den Kategorie-Schlüssel (z. B. 'strom') oder None."""
    url = (pin.get("url") or "").lower()
    pinwand = (pin.get("pinwand") or "").lower()

    # 1) Direkt aus der Ziel-URL (check24.de/<kategorie>/)
    m = re.search(r"check24\.de/([a-z0-9-]+)", url)
    if m:
        path = m.group(1)
        mapping = {
            "strom": "strom", "stromanbieter-wechseln": "strom",
            "gas": "gas", "gasanbieter-wechseln": "gas",
            "dsl": "dsl", "dsl-anbieterwechsel": "dsl",
            "mietwagen": "mietwagen", "mietwagen-preisvergleich": "mietwagen",
            "reisen": "reisen", "pauschalreisen-vergleich": "reisen",
            "fluege": "fluege", "flugvergleich": "fluege",
            "girokonto": "girokonto", "c24bank": "girokonto",
            "kredit": "kredit", "kreditvergleich": "kredit",
            "kfz-versicherung": "kfz-versicherung",
            "handytarife": "handytarife",
            "kreditkarte": "kreditkarte",
            "tagesgeld": "tagesgeld", "tagesgeldvergleich": "tagesgeld",
        }
        if path in mapping:
            return mapping[path]

    # 2) Fallback über die Pinwand (bei Educational-Pins ohne Ziel-URL)
    if "strom" in pinwand or "gas" in pinwand:
        return "strom"
    if "internet" in pinwand or "dsl" in pinwand:
        return "dsl"
    if "reisebudget" in pinwand or "mietwagen" in pinwand:
        return "mietwagen"
    # Geld sparen / Haushaltskasse / Budgetplanung → generischer Link (None)
    return None


def load_pin_topics():
    """Lädt Themen direkt aus dem Pinterest-Plan (data/pinterest_plan.yaml).
    Jeder Pin wird zu einem Themen-Eintrag – die Pins sind damit die
    Grundlage für die Artikel (nur als Inspiration, nie 1:1 kopiert).

    WICHTIG: Jeder Pin bekommt den PASSENDEN Affiliate-Link aus
    scripts/check24_links.yaml zugewiesen (basierend auf Ziel-URL/Pinwand).
    Ändern sich die Links, genügt ein Update der check24_links.yaml –
    neue Artikel nutzen dann automatisch die neuen Links."""
    pins = load_pinterest_plan()
    aff_links = load_affiliate_links()
    topics = []
    for p in pins:
        titel = (p.get("titel") or "").strip()
        if not titel:
            continue
        kws = [k.strip() for k in (p.get("keywords") or "").split(",") if k.strip()]
        cat = category_from_pin(p)
        affiliate = aff_links.get(cat) or aff_links.get("allgemein")
        topics.append({
            "title": titel,
            "keywords": kws[:5] or ["Geld sparen", "Ratgeber"],
            "affiliate_url": affiliate,
            "pin_category": cat,
        })
    return topics


def main():
    if not os.path.isdir(POSTS_DIR):
        os.makedirs(POSTS_DIR, exist_ok=True)
    auto_publish = os.environ.get("AUTO_PUBLISH", "0") == "1"
    pin_topics = os.environ.get("PIN_TOPICS", "0") == "1"
    # Tages-Limit: Wie viele Artikel dürfen pro Tag veröffentlicht werden?
    # (Guard gegen mehrere Workflow-Läufe pro Tag – GitHub-Crons können
    #  verzögert laufen oder doppelt ausgelöst werden.)
    max_per_day = int(os.environ.get("MAX_ARTIKEL_PRO_TAG", "2"))

    # Heute bereits veröffentlichte Artikel zählen
    today = datetime.date.today().isoformat()
    published_today = 0
    if os.path.isdir(POSTS_DIR):
        for fn in os.listdir(POSTS_DIR):
            if fn.startswith(today) and fn.endswith(".md"):
                with open(os.path.join(POSTS_DIR, fn), encoding="utf-8") as f:
                    content = f.read()
                if "draft: false" in content:
                    published_today += 1

    if auto_publish and published_today >= max_per_day:
        print(f"Bereits {published_today} Artikel heute veröffentlicht "
              f"(Limit: {max_per_day}) – nichts zu tun.")
        return

    used_titles = existing_titles()

    if pin_topics:
        topics = load_pin_topics()
        quelle = "Pinterest-Plan (62 Pins)"
        # Fallback: Sind alle Pin-Themen bereits abgedeckt, wird automatisch
        # auf den erweiterten Themenpool zurückgegriffen (nie leerlaufen).
        freie = [t for t in topics if not topic_already_covered(t["title"], used_titles)]
        if not freie:
            print("  – Alle Pin-Themen bereits behandelt → Fallback auf Themenpool (topics.yaml)")
            topics = load_topics()
            quelle = "Themenpool (Fallback)"
    else:
        topics = load_topics()
        quelle = "Themenpool (topics.yaml)"

    print(f"Content-Bot gestartet – Quelle: {quelle} ({len(topics)} Themen), "
          f"{MAX_ARTICLES} Artikel geplant, "
          f"{len(used_titles)} bestehende Artikel erkannt.")
    print(f"Modus: {'AUTO-VERÖFFENTLICHUNG (draft: false)' if auto_publish else 'Entwürfe (draft: true)'}")

    created = 0
    attempts = 0
    random.shuffle(topics)
    while created < MAX_ARTICLES and attempts < MAX_ARTICLES * 15:
        attempts += 1
        topic_entry = topics[(attempts - 1) % len(topics)]
        if topic_already_covered(topic_entry["title"], used_titles):
            print(f"  – Thema bereits behandelt, übersprungen: {topic_entry['title'][:60]}…")
            continue
        angle = ANGLES[(attempts - 1) % len(ANGLES)]
        if write_draft(topic_entry, angle, provider=None, used_titles=used_titles,
                       auto_publish=auto_publish):
            created += 1
        time.sleep(2)

    if auto_publish:
        print(f"\nFertig: {created} neue Artikel AUTOMATISCH VERÖFFENTLICHT (draft: false).")
        if created == 0:
            print("⚠ WICHTIG: Es wurde KEIN Artikel erzeugt. Mögliche Ursachen:")
            print("  - API-Key fehlt oder abgelaufen (GROQ_API_KEY / GEMINI_API_KEY)")
            print("  - API-Kontingent erschöpft (Rate Limit)")
            print("  → Bitte Workflow-Log prüfen und Keys aktualisieren.")
            sys.exit(1)  # Workflow als fehlgeschlagen markieren
    else:
        print(f"\nFertig: {created} neue Entwürfe (draft: true). "
              "Zum Veröffentlichen draft auf 'false' setzen (siehe README).")


if __name__ == "__main__":
    main()
