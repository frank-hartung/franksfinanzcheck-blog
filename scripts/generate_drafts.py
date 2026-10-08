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
    AI_PROVIDER=gemini python3 scripts/...            # Provider erzwingen
"""

import datetime
import json
import os
import random
import re
import sys
import time
import urllib.error

import yaml

# ---------------------------------------------------------------- Konfiguration
BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
from post_utils import list_post_paths, slug_of, join_article  # Naht-SSOT
import llm_client
# AGC-AUTOPILOT (08.09.2026): optionaler Kontext aus der Blog-Automatik
# (Brand Brain + geroutete Tages-Recherche + Kampagnen-CTA). Der Import DARF
# NIE brechen: fehlt das Modul, schreibt der Bot exakt wie bisher.
try:
    import agc_context
except Exception:  # noqa: BLE001
    agc_context = None
TOPICS_FILE = os.path.join(BLOG_DIR, "data", "topics.yaml")

PINTEREST_PLAN = os.path.join(BLOG_DIR, "data", "pinterest_plan.yaml")

MAX_ARTICLES = int(os.environ.get("MAX_ARTIKEL_PRO_LAUF", "1"))
AUTHOR = os.environ.get("BLOG_AUTHOR") or "Frank Hartung"
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
    ("analyse", "Beginne mit einer konkreten Entscheidungssituation und analysiere sie ohne erfundene Eigenerfahrung"),
    ("neutral", "Schreibe sachlich-neutral wie eine unabhängige Redaktion, ohne Test- oder Beratungsleistung zu behaupten"),
    ("modellfall", "Eröffne mit einem ausdrücklich als Modellfall markierten Beispiel, niemals mit einer erfundenen realen Person"),
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
    "PROFI-NIVEAU – sprachlich mindestens auf dem Niveau von ZEIT.de, ohne dessen "
    "Texte oder Formeln nachzuahmen. Du schreibst eigenständig, gedanklich präzise, "
    "variantenreich und sachlich. Wiederkehrende Templates, identische Einstiege, "
    "Übergänge und Schlussformeln sind verboten: Die Form folgt dem konkreten Thema. "
    "Jeder Artikel braucht einen eigenen Blick, ein konkretes Bild oder eine präzise "
    "Beobachtung. Du schreibst sachlich korrekte Artikel. "
    "Du erfindest keine Preise, Spannen, Zinssätze, Statistiken, Studien, Umfragen, "
    "Personen, Kundengeschichten, eigenen Tests oder Experten-Zitate. Ein \"ca.\" "
    "macht eine unbelegte Zahl nicht belastbar. Jede externe Zahlen- oder Rechtsaussage "
    "braucht einen klickbaren Quellenlink direkt im selben Satz; ein Quellenverzeichnis "
    "allein reicht nicht. Gesetzesparagraphen brauchen immer einen Primärquellen-Link. "
    "Modellrechnungen kennzeichnest du im Satz als Modellrechnung und nennst Annahmen, "
    "Formel, Rechenschritte und Ergebnis; sie sind kein Marktwert. Du schreibst in AKTIVER, lebendiger Sprache: kurze Sätze "
    "(max. ~20 Wörter), starke Verben. " + SYSTEM_ANREDE + " Kein Passiv, keine Füllphrasen, kein Werbesprech. "
    "Du verzichtest auf typische KI-Floskeln wie \"In der heutigen schnelllebigen Welt\", "
    "\"Es ist wichtig zu beachten\", \"Zusammenfassend lässt sich sagen\", \"Des Weiteren\", "
    "\"Es gibt viele Möglichkeiten\", \"heutzutage\", \"Tauchen wir ein\". "
    "Du arbeitest mit den Struktur-Methoden der großen Wirtschaftsredaktionen: "
    "eine klare, dem Thema angemessene Orientierung, direkte Antworten und "
    "konkrete Beispiele. Bausteine wie Kurzfazit, Faustregel, Schrittfolge oder "
    "FAQ sind nur dort einzusetzen, wo sie dem Leser wirklich helfen – nicht als "
    "automatische Schablone. "
    "Deine Texte sind journalistisch, konkret, praxisnah und vermitteln echten Nutzen. "
    "Jeder Absatz ist 3–4 Sätze lang, behandelt genau EINEN Gedanken und endet an einer "
    "sinnvollen Stelle – keine Textwände, kein Aneinanderreihen von Ein-Satz-Absätzen. "
    "Schreibe Wörter NIE mit Silbentrennung (kein Wort wird getrennt). Zwischen einer "
    "Zahl und ihrer Einheit steht IMMER ein geschütztes Leerzeichen (U+00A0, "
    "Non-Breaking Space), damit Zahl und Einheit nie in verschiedene Zeilen brechen: "
    "z. B. 20 %, 50 €, 100 EUR mit geschütztem Leerzeichen – niemals mit normalem "
    "Leerzeichen und niemals als HTML-Entity (&nbsp;). Leitet ein Gedankenstrich "
    "einen erläuternden Nachsatz ein (Muster: 'Satz – Nachsatz', z. B. '…Reisedauern – "
    "die 10-Tage-Variante…'), beginnt der Nachsatz auf einer NEUEN Zeile "
    "(Markdown-Hard-Break: zwei Leerzeichen am Zeilenende). Deutsche Rechtschreibung ist fehlerfrei."
)

# ---------------------------------------------------------------- Hilfsfunktionen


def fix_number_units(body):
    """Top-Level-Darstellung: Zahl + Einheit (% / € / EUR) mit geschütztem
    Leerzeichen (U+00A0) verbinden, damit nie getrennt umbrochen wird.
    HTML-Entities (&nbsp;) werden dabei normalisiert. Markdown-Links werden
    maskiert, damit URLs unangetastet bleiben."""
    link_re = re.compile(r"\[[^\]]*\]\([^)]*\)")
    num_unit_re = re.compile(r"(\d[\d.,]*)\s+(%|€|EUR)(?!\w)")
    body = re.sub(r"&nbsp;", "\u00a0", body)
    masked = link_re.sub(lambda m: " " * (m.end() - m.start()), body)
    out, last = [], 0
    for m in num_unit_re.finditer(masked):
        out.append(body[last:m.start()])
        out.append(m.group(1) + "\u00a0" + m.group(2))
        last = m.end()
    out.append(body[last:])
    return "".join(out)


def load_topics():
    """Lädt data/topics.yaml als echtes YAML (13.08.2026 – vorher ein sehr
    fragiler, zeilenbasierter Mini-Parser, der bei jeder Formatierungs-
    Abweichung (z. B. durch andere Automatisierungs-Skripte) still falsche
    Themen/Pillars zusammengewürfelt statt einen Fehler geworfen hat – siehe
    Commit-Historie zu data/topics.yaml. Ein echter YAML-Parser bricht bei
    kaputtem Format stattdessen laut mit einer klaren Fehlermeldung ab,
    statt die Themen falsch zuzuordnen."""
    try:
        with open(TOPICS_FILE, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        sys.exit(f"FEHLER: data/topics.yaml ist kein gültiges YAML mehr – "
                 f"bitte reparieren, bevor der Bot weiterläuft:\n{exc}")
    raw_topics = (data or {}).get("topics") or []
    topics = []
    with open(TOPICS_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("- title:"):
                t = line.split(":", 1)[1].strip().strip("\"'")
                topics.append({"title": t, "keywords": [], "affiliate_url": None, "pillar": None})
            elif line.startswith("keywords:") and topics:
                raw = line.split(":", 1)[1].strip()
                topics[-1]["keywords"] = [k.strip().strip("\"'") for k in raw.strip("[]").split(",")]
            elif line.startswith("affiliate_url:") and topics:
                topics[-1]["affiliate_url"] = line.split(":", 1)[1].strip().strip("\"'")
            elif line.startswith("pillar:") and topics:
                topics[-1]["pillar"] = line.split(":", 1)[1].strip().strip("\"'")
    if not topics:
        sys.exit("FEHLER: Keine Themen in data/topics.yaml gefunden.")
    return topics


def refill_topics(topics, used_titles, target=16):
    """Lässt die KI neue Themenvorschläge generieren, wenn der Pool leer läuft.
    Neue Themen werden auf Duplikate (gegen Pool + bestehende Artikel) geprüft
    und an data/topics.yaml angehängt. Liefert Anzahl der neuen Themen."""
    PILLARS = ["strom-sparen", "versicherungen", "mietwagen", "frugalismus",
               "internet-dsl", "konto-karten"]
    existing_lines = "\n".join(f"- {t['title']}" for t in topics)
    prompt = (
        f"Generiere {target} NEUE, konkrete deutsche Blog-Artikel-Titel für einen "
        "Finanz-Ratgeber-Blog (Frugalismus, Strom/Gas sparen, Versicherungen, "
        "Mietwagen/Reisen, Internet/DSL, Konto/Karten). Anforderungen: "
        "spezifisch und praxisnah (keine Allgemeinplätze), für 2026/2027 relevant, "
        "jeder Titel 5-12 Wörter mit konkretem Nutzenversprechen. "
        "Diese Themen existieren BEREITS – erfinde KEINE ähnlichen:\n"
        f"{existing_lines}\n\n"
        "Antworte NUR in diesem Format (genau 1 Leerzeile zwischen Blöcken):\n"
        "TITLE: <Titel>\n"
        "KEYWORDS: <Keyword1>, <Keyword2>, <Keyword3>\n"
        f"PILLAR: <einer von: {', '.join(PILLARS)}>\n"
    )
    raw = None
    for fn in (call_groq, call_gemini):
        try:
            raw = fn(prompt)
            if raw and len(raw.strip()) > 200:
                break
        except Exception:
            continue
    if not raw:
        print("    ✗ KI-Themen-Generierung fehlgeschlagen (kein Provider erreichbar).")
        return 0

    # Blöcke parsen
    blocks = re.split(r"\n\s*\n", raw.strip())
    neue = 0
    with open(TOPICS_FILE, "a", encoding="utf-8") as f:
        for b in blocks:
            t = re.search(r"^TITLE:\s*(.+)$", b, re.M)
            k = re.search(r"^KEYWORDS:\s*(.+)$", b, re.M)
            p = re.search(r"^PILLAR:\s*(.+)$", b, re.M)
            if not t:
                continue
            title = t.group(1).strip().strip('"')
            if not title or len(title) > 90:
                continue
            # Duplikat-Checks
            if topic_already_covered(title, used_titles):
                continue
            if any(topic_already_covered(title, {x["title"]}) for x in topics):
                continue
            keywords = [kw.strip() for kw in (k.group(1).split(",") if k else [])][:4]
            if not keywords:
                keywords = [title]
            pillar = (p.group(1).strip() if p else "frugalismus")
            if pillar not in PILLARS:
                pillar = "frugalismus"
            f.write(f'\n  - title: "{title}"\n    keywords: {json.dumps(keywords, ensure_ascii=False)}\n    pillar: "{pillar}"\n')
            topics.append({"title": title, "keywords": keywords, "affiliate_url": None, "pillar": pillar})
            neue += 1
    print(f"    ✓ {neue} neue Themen in topics.yaml gespeichert.")
    return neue


def demo_files():
    """Findet Demo-Artikel (mit Marker 'demo-artikel' im Inhalt) – NUR diese
    dürfen vom Aufräum-Prozess gelöscht werden. Schützt echte Bot-Artikel."""
    demos = []
    if not os.path.isdir(POSTS_DIR):
        return demos
    for path in list_post_paths():
        with open(path, encoding="utf-8") as f:
            if "demo-artikel" in f.read():
                demos.append(path)
    return demos


def existing_titles():
    """Listet bereits vorhandene Artikel-Titel (für Duplikat-Schutz)."""
    titles = set()
    if not os.path.isdir(POSTS_DIR):
        return titles
    for path in list_post_paths():
        with open(path, encoding="utf-8") as f:
            content = f.read()
        m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.M)
        if m:
            titles.add(m.group(1).strip().lower())
    return titles


def topic_already_covered(topic_title, used_titles):
    """Prüft, ob ein Thema bereits durch einen vorhandenen Artikel abgedeckt ist.
    Mehrstufig:
      1) Exakte/normalisierte Übereinstimmung (Titel in Titel)
      2) Präfix-Abgleich der ersten 4 Wörter
      3) TOKEN-ÜBERSCHNEIDUNG: Teilt beide Titel in inhaltstragende Wörter
         (ohne Stoppwörter) und prüft, ob ≥ 60 % der Themen-Tokens in einem
         bestehenden Titel vorkommen → verhindert Themen-Kannibalisierung
         (z. B. „5 einfache Frugalismus-Tricks" vs. „5 Frugalismus-Tricks:
         So sparst du 200 €" – gleiches Kern-Thema).
    """
    STOP = {"der", "die", "das", "und", "oder", "fur", "fuer", "mit", "von", "im",
            "in", "den", "dem", "ein", "eine", "einer", "eines", "auf", "bei",
            "zum", "zur", "sich", "nicht", "auch", "als", "wie", "was", "dich",
            "dein", "deine", "ihr", "ihre", "so", "du", "sie", "is", "sind",
            "fur", "gegen", "nach", "uber", "aus", "für", "über"}

    def norm(s):
        s = s.lower()
        s = re.sub(r"[äàáâ]", "ae", s)
        s = re.sub(r"[öòóô]", "oe", s)
        s = re.sub(r"[üùúû]", "ue", s)
        s = re.sub(r"ß", "ss", s)
        return re.sub(r"[^a-z0-9]+", " ", s).strip()

    def tokens(s):
        return [w for w in norm(s).split() if w not in STOP and len(w) > 2]

    t = norm(topic_title)
    if not t:
        return False
    t_tokens = t.split()[:4]  # erste 4 Wörter als Kern des Themas
    topic_tokens = tokens(topic_title)
    core_tokens = topic_tokens[:3]  # erste 3 inhaltstragende Wörter (Kern)

    for title in used_titles:
        nt = norm(title)
        if t in nt or nt in t:
            return True
        # Präfix-Abgleich: gleiche ersten 4 Wörter = gleiches Thema
        if t_tokens and nt.split()[:4] == t_tokens:
            return True
        # Token-Überschneidung: ≥ 60 % der Themen-Tokens stecken im Titel
        if topic_tokens:
            nt_tokens = tokens(title)
            if nt_tokens:
                overlap = sum(1 for w in topic_tokens if w in nt_tokens)
                if overlap / len(topic_tokens) >= 0.6:
                    return True
                # Kern-Token-Regel: ≥ 2 der ersten 3 Kern-Wörter im Titel
                # (fängt Fälle wie „5 einfache Frugalismus-Tricks" vs.
                #  „5 Frugalismus-Tricks: So sparst du 200 €" – 50 %-Overlap,
                #  aber identischer Themen-Kern)
                if len(core_tokens) >= 2:
                    core_hits = sum(1 for w in core_tokens if w in nt_tokens)
                    if core_hits >= 2:
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


def lesbarkeits_befund(body: str):
    """Flesch-Amstad des Rohtexts gegen die IMPORTIERTE Schwelle (#585).

    Rückgabe: Befund-Text oder None (über der Schwelle). Jeder Messfehler ist
    ein Befund – „nicht gemessen“ ist niemals „freigegeben“ (V3, #607).

    WARUM HIER (WF-D4E0, #612): Das Geburts-Gate („Profi-Gate“) prüfte Länge,
    Module, Keywords und Struktur – aber nicht die Regel, die über die
    Veröffentlichung entscheidet. Genau diese Lücke erzeugte die Dauer-Engpässe
    der Reserve: Kandidaten wurden mit Flesch 52–60 GEBOREN, die Zertifizierung
    (hartes Gate, `readability_check.NEW_FLESCH_MIN`) wies sie danach
    geschlossen zurück, und der Vorrat fiel unter das Ziel – der harte
    End-Gate „Stock shortage must not look successful“ wurde Nacht für Nacht
    rot (Issues #513, #609, #612). Verhindern statt protokollieren: Was die
    Zertifizierung ablehnt, darf gar nicht erst als Rohtext entstehen.
    """
    try:
        import readability_check as rc      # Import HIER: Modul bleibt leicht
        satz = rc.parse_article('---\ntitle: "geburts-messung"\n---\n\n'
                                + (body or ""), "geburts-gate/index.md")
        if not satz:
            return ("Lesbarkeit nicht messbar (Rohtext ohne Grenzen) – "
                    "fail-closed (V3)")
        wert = rc.analyze(satz).get("flesch")
    except Exception as exc:  # noqa: BLE001 – Messfehler ist ein Befund
        return (f"Lesbarkeit nicht messbar ({type(exc).__name__}) – "
                f"fail-closed (V3)")
    if wert is None or wert < rc.NEW_FLESCH_MIN:
        zahl = f"{wert:.1f}" if isinstance(wert, (int, float)) else "nicht messbar"
        return (f"Lesbarkeit: Flesch {zahl} < {rc.NEW_FLESCH_MIN:g} "
                f"(hartes Publish-Kriterium R6/#585) – kürzere Sätze und "
                f"alltägliche Wörter statt langer Komposita")
    return None


def profi_quality_ok(body, keywords=None):
    """Prüft einen frisch generierten Artikel auf Profi-Niveau.
    Liefert (ok, probleme). Wird in der Regenerierungs-Schleife genutzt."""
    problems = []
    text = re.sub(r"[#*_>`|~\[\]()-]", " ", body)
    text = re.sub(r"\s+", " ", text).lower()
    words = len(re.findall(r"\w+", text))

    chars = len(re.sub(r"\s+", " ", body).strip())
    if words < 1400 or chars < 10000:
        problems.append(f"nur {words} Wörter / {chars} Zeichen (Premium: ≥1.400 Wörter und ≥10.000 Zeichen)")
    h2 = len(re.findall(r"^##\s", body, re.M))
    if h2 < 5:
        problems.append(f"nur {h2} H2-Abschnitte (Premium: ≥5)")
    faq = len(re.findall(r"^###\s.*\?", body, re.M))
    if faq < 4:
        problems.append(f"nur {faq} FAQ-Fragen (Premium: ≥4)")
    if "das wichtigste in kürze" not in text:
        problems.append("kein „Das Wichtigste in Kürze“-Modul (RS1)")
    if "faustregel" not in text:
        problems.append("keine Faustregel markiert (RS3)")
    floskeln = [f for f in PROFI_FLOSKELN if f in text]
    if floskeln:
        problems.append(f"KI-Floskeln: {', '.join(floskeln[:2])}")
    # WF-D4E0 (#612): Die Lesbarkeit ist ein HARTES Publish-Kriterium (#585)
    # und fehlte bis hier – Texte wurden unter der Schwelle geboren und
    # mussten nachgelagert geheilt werden (oder blieben liegen). Die Messung
    # nutzt ausschließlich die importierte SSOT-Schwelle, keine zweite Zahl.
    lesbarkeit = lesbarkeits_befund(body)
    if lesbarkeit:
        problems.append(lesbarkeit)
    # Reserve-Qualitätsvertrag: Faktenbeleg/RS5, Phantomquellen/RS6,
    # H2-Redundanz und redaktioneller Mindestumfang blockieren schon bei Geburt.
    try:
        from redaktions_standard import reserve_quality_findings
        problems.extend(reserve_quality_findings(body, author=AUTHOR))
    except Exception as exc:  # fail-closed: Messausfall ist kein Freispruch
        problems.append(f"Reserve-Qualitäts-Gate nicht prüfbar: {exc}")
    if keywords:
        kws = [k.strip().strip('"').lower() for k in keywords if k.strip()]
        if kws and kws[0] not in text:
            problems.append(f"Keyword „{kws[0]}“ fehlt")
        # PREMIUM #303: Keyword muss in Titel/Description/erster Absatz/H2 – hier prüfen wir
        # ersten Absatz (erste 350 Zeichen) und H2/H3, damit die Engine sofort neu würfelt
        # statt erst in Phase 2 zu heilen. Das ist die Geburts-Gate-Härtung für Keywords.
        if kws:
            main_kw = kws[0]
            # Norm für Keyword-Check (wie in keyword_optimizer)
            def _norm(s):
                s = s.lower()
                s = re.sub(r"[äàáâ]", "ae", s)
                s = re.sub(r"[öòóô]", "oe", s)
                s = re.sub(r"[üùúû]", "ue", s)
                s = re.sub(r"ß", "ss", s)
                return re.sub(r"[^a-z0-9]+", " ", s).strip()
            nk = _norm(main_kw)
            core = next((t for t in nk.split() if len(t) >= 3), nk)
            def _has_kw(txt):
                txt_n = _norm(txt)
                if nk in txt_n:
                    return True
                for w in txt_n.split():
                    if w == core or w.startswith(core):
                        return True
                    if len(w) >= 4 and core.startswith(w):
                        return True
                return False
            first_350 = body[:400]
            if not _has_kw(first_350):
                problems.append(f"Keyword „{main_kw}“ fehlt im ersten Absatz (Premium #303)")
            # H2/H3 Check
            h2_texts = re.findall(r"^#{2,3}\s+(.+)$", body, re.M)
            if h2_texts and not any(_has_kw(h) for h in h2_texts):
                problems.append(f"Keyword „{main_kw}“ fehlt in H2/H3 (Premium #303)")
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




def _retry(fn, attempts=4, base_delay=5):
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
    return llm_client.chat(
        "groq", prompt=prompt, system=SYSTEM_PROMPT,
        temperature=0.9, max_tokens=6000, timeout=180,
        raise_on_error=True,
    )


def call_gemini(prompt):
    if not llm_client.available("gemini"):
        return None
    model = os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")
    # Explizites Ausgabelimit hält den 1.500–2.200-Wörter-Auftrag unabhängig
    # vom impliziten Modell-Default; der gemeinsame Client liest alle Antwort-Parts.
    def _call():
        return llm_client.chat(
            "gemini", prompt=prompt, model=model, temperature=0.8,
            max_tokens=8192, timeout=90, attempts=1, raise_on_error=True,
        )
    return _retry(_call)



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
]


def generate_article_text(topic, angle, perspective=None, pin=None, keywords=None, pillar=None, hinweise=None):
    """Baut den Prompt und ruft die KI auf. Liefert (rohtext, provider).

    - angle:      Schreibstil (Ratgeber, Vergleich, FAQ …)
    - perspective: Erzählperspektive (direkt, Erfahrung, neutral …)
    - pin:        der zugehörige Pinterest-Pin – NUR als Inspiration,
                  der Artikel muss eigenständig formuliert sein.
    - keywords:   Ziel-Keywords – der Artikel soll sie natürlich einbauen
                  (automatische Keyword-Optimierung neuer Artikel).
    - hinweise:   konkrete Befunde des VORHERIGEN Versuchs (z. B. gemessene
                  Lesbarkeit, fehlende Module). Sie gehen als Korrektur-Auftrag
                  in den Prompt, statt denselben Fehler blind neu zu würfeln
                  (WF-D4E0, #612). `None` = erster Versuch.
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
    pillar_hint = ""
    if pillar:
        pillar_hint = (
            "CLUSTER-VERLINKUNG: Dieser Artikel gehört zu einer Ratgeber-Übersicht "
            "(Pillar-Page) auf FranksFinanzcheck. Baue an genau EINER passenden "
            "Stelle im Fließtext einen natürlichen, kontextuellen Link auf die "
            "Ratgeber-Übersicht ein – Markdown-Link mit RELATIVEM Pfad "
            "(kein führender Slash): "
            f"[Ratgeber: ...](../../pillar/{pillar}/) – "
            "z. B. „Mehr dazu im Ratgeber …“ mit aussagekräftigem Ankertext.\n"
        )
    # AGC-AUTOPILOT: Brand Brain + geroutete Recherche + Kampagnen-CTA als
    # Kontext an den Schreiber übergeben. Fehlt ein Baustein → leerer Block,
    # der Prompt bleibt identisch zum bisherigen Verhalten.
    agc_block = ""
    if agc_context is not None:
        try:
            agc_block = agc_context.build_context_block(
                topic, pillar=pillar, keywords=keywords, pin=pin)
        except Exception:  # noqa: BLE001
            agc_block = ""

    # YMYL wird VOR dem Schreiben klassifiziert. Ein Modell darf bei
    # Baufinanzierung, Rente, Kredit und Versicherung keinen glatten
    # Veröffentlichungsersatz simulieren; es liefert einen prüfpflichtigen
    # Arbeitsentwurf ohne Scheinquellen oder erfundene Eigenerfahrung.
    try:
        import editorial_review_gate as _erg
        risk = _erg.classify_text(" ".join([topic] + list(keywords or [])[:2]), pillar or "")
    except Exception:  # noqa: BLE001 - Publish-Gate klassifiziert erneut
        risk = "standard"
    current_year = datetime.date.today().year
    if risk == "hoch":
        risk_instructions = (
            "YMYL-RISIKOKLASSE HOCH – ARBEITSENTWURF, KEINE FREIGABE:\n"
            "- Behaupte weder fachliche Prüfung noch Beratung, eigene Kundenfälle oder eigene Tests.\n"
            "- Nenne keine Marktwerte, Zinsspannen, Sparsummen, Fristen oder pauschalen Bankregeln, "
            "wenn sie nicht im gelieferten Recherchekontext mit konkreter Quelle belegt sind.\n"
            "- Eine Modellrechnung ist nur erlaubt, wenn alle Annahmen frei gewählt und als solche "
            "markiert sind; zeige Formel und jeden Rechenschritt.\n"
            "- Pauschalaussagen zu Zinsbindung, Eigenkapital, Bonität, Bankverhalten und "
            "Versicherungsschutz sind verboten; nenne Bedingungen und Gegenfälle.\n"
            "- Verwende keinen Artikelstand vor dem aktuellen Jahr " + str(current_year) + ".\n"
            "- Kein Affiliate-Aufruf im Fachtext. Die Pipeline setzt einen CTA erst am Artikelende; "
            "vorher müssen Kriterien, Risiken und Alternativen vollständig erklärt sein.\n"
        )
    else:
        risk_instructions = (
            "RISIKOKLASSE " + risk.upper() + ": Zahlen nur mit gelieferter Quelle oder als "
            "transparent hergeleitete Modellannahme verwenden. Verwende keinen als aktuell "
            "bezeichneten Artikelstand vor " + str(current_year) + ".\n"
        )
    # KORREKTUR-AUFTRAG (WF-D4E0, #612): Der vorherige Versuch wurde vom
    # Geburts-Gate mit KONKRETEN Befunden abgelehnt. Blind neu zu würfeln
    # verschwendet Kontingent und trifft dieselbe Regel mit derselben
    # Wahrscheinlichkeit wieder; dieser Block macht aus dem Retry einen
    # Auftrag. Leer (None/[]), wenn es der erste Versuch ist.
    korrektur_block = ""
    befunde = [str(h).strip() for h in (hinweise or []) if str(h).strip()]
    if befunde:
        korrektur_block = (
            "\nKORREKTUR-AUFTRAG – der vorige Versuch wurde ABGELEHNT. Behebe "
            "GENAU diese Punkte und ändere dabei nichts, was schon gut war:\n"
            + "\n".join(f"- {b}" for b in befunde[:6]) + "\n")
    prompt = f"""Schreibe einen EINZIGARTIGEN, hilfreichen deutschen Blog-Artikel zum Thema:
"{topic}"

{pillar_hint}{inspiration}{keyword_hint}Stil des Artikels: {angle_desc}.
Erzählperspektive: {persp_desc}.

{agc_block}
{risk_instructions}
FORMAT – halte dich GENAU daran (wichtig für die Weiterverarbeitung):
Zeile 1: TITLE: Ein prägnanter, klickstarker Titel (max. 60 Zeichen). Wähle einen FRISCHEN Blickwinkel – verwende NICHT den Pin-Titel und nicht wörtlich das Thema.
Zeile 2: DESCRIPTION: Eine Meta-Beschreibung (max. 155 Zeichen, mit wichtigstem Keyword)
Ab Zeile 3: Der Artikel in Markdown:
- Keine Überschrift für den Titel am Anfang (Titel steht schon in Zeile 1)
- Einleitung mit starkem HAKEN: Nutzenversprechen, konkrete Frage oder überraschende Zahl –
  KEIN generischer Einstieg ("In der heutigen Zeit…", "Geld sparen ist wichtig…")
- VERBOTEN: die Schablone „In diesem Ratgeber zeige/erfährst/erkläre ich dir …“ am
  Einleitungsende. Entwickle stattdessen einen frischen Einstieg aus dem konkreten
  Gegenstand. Kein Rotationsschema, keine vorgegebene Liste von Öffnungsformeln.
- 5 bis 8 Abschnitte mit H2-Überschriften (##) – strukturiere sie ANDERS als die Pin-Vorlage
- Pflicht-Module (kein Fülltext): eine Tabelle ODER Checkliste und ein Abschnitt „Typische Fehler“. Eine Modellrechnung nur, wenn sie fachlich hilft; dann mit offen gelegten Annahmen, Formel, Rechenschritten und Rechenprobe – nie mit einem künstlichen Jahreslabel.
- REDAKTIONS-STANDARD (Capital/WirtschaftsWoche/ZEIT, Pflicht für alle Module):
  1) „Das Wichtigste in Kürze“: Direkt NACH der Einleitung (vor der ersten H2) ein Block
     mit fettem Label + 3–4 Bullet-Punkten mit den Kernaussagen (Zahlen nur als Spannen).
  2) Mindestens 2 deiner H2-Überschriften sind FRAGEN („Warum lohnt sich X?“, „Was kostet X?“,
     „Welche Fehler kosten dich Geld?“) – jede Frage wird direkt und konkret beantwortet.
  3) Mindestens EINE markierte Faustregel als eigener Absatz: „**Faustregel:** …“.
  4) Mindestens EINE nummerierte Schrittfolge mit 3–6 Schritten („So gehst du vor:“ + 1. 2. 3.).
  5) Zahlen-Ehrlichkeit (WiWo-Standard): Harte Zahlen nur mit Einordnung – „ca. 20–40 €“,
     „in der Regel“, „je nach Anbieter“, „rund“. NIE erfundene Studien/Umfragen/Experten
     (keine Sätze wie „Laut einer Studie…“) – unbelegbare Aussagen als Allgemeinwissen
     formulieren. Rechenbeispiele klar als solche kennzeichnen.
- Mindestens EINE Liste oder Tabelle (Mehrwert, Scannability)
- Am Ende ein FAQ-Bereich: "## Häufige Fragen" mit 5 Fragen als H3 und Antworten
- 1.500 bis 2.200 Wörter insgesamt (mindestens 1.400 Wörter / 10.000 Zeichen – darunter gilt der Artikel als zu kurz und wird abgelehnt). Zielkorridor Premium: 12.000–18.000 Zeichen Fließtext. Substanz, keine Floskeln.
- Absätze max. 3–4 Sätze (eine Idee pro Absatz), aktive Sprache ("du"),
  kurze Sätze (max. ~20 Wörter); nach einem langen Satz folgen 1–2 kurze (Satzrhythmus)
- LESBARKEIT ist ein MESSBARES, hartes Kriterium (Flesch-Amstad nach Amstad-Formel,
  Publish-Schwelle – an ihr wird der Artikel gemessen, bevor er erscheint):
  Ø Satzlänge höchstens 12 Wörter, Ø höchstens ~1,9 Silben je Wort. Konkret:
  ersetzt lange Komposita durch Alltagswörter („Wohngebäudeversicherung“ → „Hausrat“;
  „Verbraucherverhalten“ → „Verhalten“), zerlegt Bandwurmsätze an „und/aber/denn/doch/
  sondern“ in zwei Sätze und streicht Füllphrasen („im Rahmen von“, „zum jetzigen
  Zeitpunkt“). Deutsche Alltagssprache schlägt Amtsdeutsch: „nutzen“ statt „Verwendung
  finden“, „Kosten“ statt „Kostenaufwendungen“.
- KEINE Komma-Listen: nie mehr als 15 Begriffe in einer Aufzählung hintereinander;
  stattdessen Tabellen oder Listen mit je einem erklärenden Satz
- TERMINOLOGIE: pro Artikel EINEN Leitbegriff für das Hauptkonzept wählen und
  durchgehend verwenden; Synonyme höchstens einmal als Erklärung bei Ersterwähnung
  (z. B. „DNS-Server (auch Namensauflösung oder Resolver genannt)“)
- ANREDE: {anrede_var} – konsistent durchgehend verwenden
- PRAXISBEZUG (E-E-A-T): konkrete Entscheidungssituationen als ausdrücklich benannte
  Modellfälle. NIEMALS „Ich habe …“, „meine Klienten …“ oder reale Tests/Beratungen
  behaupten, wenn kein dokumentierter Eigenbeleg im Recherchekontext steht. Auch
  Preisspannen mit „ca.“ oder „in der Regel“ brauchen eine konkrete Quelle.
- KEINE KI-Floskeln: verboten sind u.a. "In der heutigen schnelllebigen Welt", "Es ist
  wichtig zu beachten", "Zusammenfassend lässt sich sagen", "Des Weiteren", "Es gibt viele
  Möglichkeiten", "heutzutage", "Tauchen wir ein", "Der Schlüssel zum Erfolg"
- KEINE Links einfügen, KEINE konkreten Zahlen erfinden
- Deutsche Orthografie: korrekte Groß-/Kleinschreibung, korrekte Anführungszeichen ("…")
- Originalität ist Pflicht: eigener Wortlaut, eigene Beispiele, eigene Abschnittsfolge
{korrektur_block}"""
    forced = (os.environ.get("AI_PROVIDER") or "").strip().lower()
    if forced and forced not in {"groq", "gemini"}:
        print(f"  ✗ Unbekannter AI_PROVIDER={forced!r}; erlaubt sind groq und gemini.")
        return None, None
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
            if e.code in (429, 500, 502, 503, 504):
                # Rate-Limit/Server-Probleme: kurz warten, bevor der nächste
                # Provider gefragt wird (verhindert Ketten-Ausfälle)
                time.sleep(8)
        except Exception as e:
            print(f"    Provider-Fehler ({type(e).__name__}: {e}), nächster Provider …")
    return None, None


# ---------------------------------------------------------------- Artikel bauen


# Marker des Prompt-Ausgabeformats. Bewusst großzügiger als die zwei
# Marker, die der Prompt selbst verlangt: Modelle erfinden regelmäßig
# „META:“, „SLUG:“ oder „OUTPUT:“ dazu.
_MARKER_RX = re.compile(
    r"(?im)^\s{0,3}(TITLE|TITEL|DESCRIPTION|BESCHREIBUNG|BODY|ARTIKEL|"
    r"ARTICLE|KEYWORDS|META|METADESCRIPTION|SLUG|H1|OUTPUT|AUSGABE|"
    r"ANTWORT|PROMPT|SYSTEM|ASSISTANT|USER|PILLAR)\s*:\s*(?P<wert>.*)$")
# Wie weit vorne im Output darf ein Kopf-Marker stehen? Großzügig genug
# für Leerzeilen, Code-Fences und ein vorangestelltes „---“, eng genug,
# dass eine Zeile mitten im Artikel nicht als Kopfzeile missverstanden wird.
_MARKER_FENSTER = 8


def parse_article(raw, topic, angle_name):
    """Extrahiert Titel, Beschreibung und Body aus dem KI-Output.

    ISSUE #521 (02.10.2026) – warum diese Funktion gehärtet wurde:
    Die alte Fassung verlangte „TITLE:“ auf Zeile 0 UND „DESCRIPTION:“ auf
    Zeile 1. Beides war positionsgebunden, und die zweite Bedingung war
    zusätzlich die einzige Stelle, an der der Body überhaupt vom Kopf
    getrennt wurde. Setzte das Modell eine Leerzeile zwischen die beiden
    Marker – am 02.10.2026 real geschehen –, griff:

      * `title`  … noch korrekt (Zeile 0 passte),
      * `desc`   … NICHT, Fallback nahm die erste Body-Zeile …
      * `body`   … NICHT, blieb der komplette Rohtext INKLUSIVE Kopf.

    Ergebnis: `description: "TITLE: Preiswert surfen: …"`,
    `pin_description: "*Werbung | TITLE: …"`, und der Artikel begann mit
    „TITLE:“. Dass der Entwurf nicht live ging, war Zufall (Zeichenlänge).

    Die neue Fassung ist positionsunabhängig, entfernt JEDEN Kopf-Marker
    aus dem Body und lässt nie einen Marker in die Beschreibung.
    """
    title, desc = None, None
    lines = raw.split("\n")

    # 1) Kopfzone: Marker einsammeln, egal in welcher Reihenfolge und mit
    #    wie vielen Leerzeilen dazwischen.
    kopf_bis = 0
    for i, line in enumerate(lines[:_MARKER_FENSTER]):
        s = line.strip()
        if not s or s in ("---", "```") or s.startswith("```"):
            continue
        m = _MARKER_RX.match(line)
        if not m:
            break           # erste echte Inhaltszeile -> Kopfzone zu Ende
        schluessel = m.group(1).upper()
        wert = m.group("wert").strip()
        if schluessel in ("TITLE", "TITEL") and not title:
            title = wert
        elif schluessel in ("DESCRIPTION", "BESCHREIBUNG",
                            "META", "METADESCRIPTION") and not desc:
            desc = wert
        kopf_bis = i + 1
    body = "\n".join(lines[kopf_bis:]).strip()

    # 2) Rest-Marker im gesamten Body entfernen. Ein Modell, das den Kopf
    #    wiederholt oder mitten im Text „KEYWORDS:“ setzt, darf das nicht
    #    in den Artikel schreiben. R16-PROMPT-ECHO blockt es sonst später
    #    hart – hier ist die Stelle, an der es gar nicht erst entsteht.
    body = _MARKER_RX.sub("", body).strip()
    # 3) Trenner, den Modelle gern zwischen Kopf und Text setzen. Ein „---“
    #    als erste Body-Zeile ist nach dem Frontmatter kein Gestaltungs-
    #    element, sondern ein Rest des Ausgabeformats (Realfall 02.10.2026).
    body = re.sub(r"\A(?:\s*(?:-{3,}|\*{3,}|_{3,})\s*\n)+", "", body).strip()

    if not title:
        m = re.search(r"^#\s+(.+)$", raw, re.M)
        title = m.group(1).strip() if m else topic
    if not desc:
        # Erste Zeile, die weder leer noch Marker noch Überschrift ist.
        for line in body.split("\n"):
            s = line.strip()
            if s and not _MARKER_RX.match(line) and not s.startswith("#"):
                desc = s
                break
        desc = desc or topic
    # Letzte Sicherung: Was hier durchrutscht, geht als Google-Snippet und
    # Pinterest-Pin nach außen. Ein Marker darf dort nie landen.
    title = _MARKER_RX.sub("", title).strip() or topic
    # KI-Ausgaben enthalten gelegentlich abgeschnittene oder doppelte
    # Satzzeichen. Normalisieren, bevor Frontmatter, Slug und Cover-Alttext
    # daraus entstehen und die Qualitäts-Gates den Fehler übernehmen.
    title = re.sub(r"\s*[:：]\s*", ": ", title)
    # Strich-Normalisierung (Fix 04.10.2026, prä-existierender Defekt aus
    # 01d6508): Gedankenstriche (– —) werden immer auf „ – “ gebracht; ein
    # Bindestrich wird NUR mit umgebenden Leerzeichen zum Gedankenstrich.
    # Komposita wie „DSL-Anschluss“ oder „Corona-Impfung“ bleiben unberührt –
    # die alte Regel \s*[–—-]\s* zog den Bindestrich auseinander und machte
    # aus „DSL-Anschluss“ das kaputte „DSL – Anschluss“ (Schadensfall-Titel
    # vom 02.10.2026, siehe test_prompt_echo).
    title = re.sub(r"\s*[–—]\s*", " – ", title)
    title = re.sub(r"\s+-\s+", " – ", title)
    title = re.sub(r"\s*:\s*–\s*|\s*–\s*:\s*", ": ", title)
    title = re.sub(r"\s+", " ", title).strip(" :-–—") or topic
    desc = _MARKER_RX.sub("", desc).strip() or topic
    desc = desc[:155]
    # Code-Fences entfernen, falls die KI welche setzt
    body = re.sub(r"^```[a-zA-Z]*\s*$", "", body, flags=re.M).strip()
    # Kein zweites H1: Layout rendert den Titel bereits.
    body = re.sub(r"^# [^\n]+\n+", "", body, count=1).strip()
    return title, desc, body


def validate_frontmatter(path):
    """Prüft Pflichtfelder im Frontmatter eines frisch erstellten Artikels.
    Fehlende/kaputte Felder werden repariert. Wirft Exception bei nicht
    reparierbaren Zuständen (z. B. leere Datei)."""
    content = open(path, encoding="utf-8").read()
    if "---" not in content:
        raise ValueError("Kein Frontmatter vorhanden")
    parts = content.split("---", 2)
    fm = parts[1]
    required = ["title:", "description:", "date:", "draft:", "categories:", "keywords:", "author:"]
    fixes = []
    for field in required:
        if field not in fm:
            fixes.append(field)
    if fixes:
        # Minimal-Reparatur: fehlende Felder mit sinnvollen Defaults ergänzen
        import datetime as _dt
        add = ""
        for f in fixes:
            if f == "date:":
                add += f"date: {_dt.date.today().isoformat()}\n"
            elif f == "draft:":
                add += "draft: false\n"
            elif f == "categories:":
                add += 'categories: ["Ratgeber"]\n'
            elif f == "keywords:":
                add += "keywords: []\n"
            elif f == "author:":
                add += "author: \"Frank Hartung\"\n"
            elif f == "title:":
                add += 'title: "Artikel"\n'
            elif f == "description:":
                add += 'description: "Tipps und Einordnung zu diesem Thema."\n'
        parts[1] = fm.rstrip() + "\n" + add
        open(path, "w", encoding="utf-8").write(
            join_article(parts[1], parts[2], parts[0]))
        print(f"    ✓ Frontmatter repariert: {', '.join(fixes)} ergänzt")


def _register_tags(keywords, pillar=None, titel=""):
    """Kanonische Tags aus data/seo/tag_register.yaml (Index-Hygiene 29.09.2026).

    Vorher stand im Frontmatter `normalize_tags(keywords[:4])` – die ersten vier
    SEO-Keywords wurden also direkt zu Tags. Keywords sind aber long-tail und pro
    Artikel einmalig: jeder Entwurf hat damit bis zu vier neue Tag-Archive plus
    vier /page/1/-Weiterleitungen erzeugt. Zusammen mit engine_generate.py war das
    die Ursache der 237 „nicht indexiert"-Meldungen in der Search Console.

    Tags kommen jetzt ausschließlich aus dem kuratierten Register; erfunden wird
    keiner mehr. Die Keywords bleiben unverändert im `keywords`-Feld.
    Fail-closed: ist das Register nicht ladbar oder findet sich kein kanonischer
    Tag, bricht dieser Entwurf mit einem klaren Fehler ab. Die alte
    Schreibweisen-Normalisierung darf niemals wieder Keywords zu URL-erzeugenden
    Tags machen.
    """
    from tag_governance import kanonische_tags
    return kanonische_tags(keywords, pillar=pillar or "", titel=titel or "")


def normalize_tags(keywords):
    """Kompatibilitäts-API mit derselben fail-closed Registergrenze.

    Der frühere Fallback hat beliebige Keywords als Tags ausgegeben und damit
    genau die behobene Crawl-Flächen-Leckage wieder öffnen können. Der Name
    bleibt für externe Aufrufer erhalten, delegiert aber ausschließlich an
    das kuratierte Register.
    """
    from tag_governance import kanonische_tags
    return kanonische_tags(keywords)


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

    raw, provider_name = generate_article_text(topic, angle, perspective=None, pin=pin, keywords=keywords, pillar=topic_entry.get("pillar"))
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
        letzte_befunde = []
        if not reason:
            ok_profi, prob = profi_quality_ok(body, keywords)
            if not ok_profi:
                reason = "Profi-Qualität nicht erreicht: " + "; ".join(prob)
                letzte_befunde = list(prob)
        if reason:
            print(f"  ⚠ {reason} (Versuch {attempt}/3)")
            print(f"  ↻ Generiere mit anderem Stil neu …")
            other_angles = [a for a in ANGLES if a[0] != angle[0]]
            new_angle = random.choice(other_angles) if other_angles else angle
            raw, provider_name = generate_article_text(topic, new_angle,
                                                       perspective=random.choice(PERSPECTIVES),
                                                       pin=pin, keywords=keywords,
                                                       hinweise=letzte_befunde or None)
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
    bundle_dir = os.path.join(POSTS_DIR, f"{date}-{slug}")
    # Duplikat-Schutz: Existiert der Ordner bereits (z. B. durch einen früheren
    # Lauf mit gleichem Titel), wird ein Zähler angehängt – nie überschreiben.
    if os.path.exists(bundle_dir):
        i = 2
        while os.path.exists(f"{bundle_dir}-{i}"):
            i += 1
        bundle_dir = f"{bundle_dir}-{i}"
    os.makedirs(bundle_dir, exist_ok=True)
    filename = os.path.join(bundle_dir, "index.md")

    try:
        # REPARATUR 02.10.2026 (WF-D4E0, Issue #513): Auch hier stand die
        # rohe Partner-URL mit dem generischen Anker „Jetzt Angebote
        # vergleichen“ – Link-Integrität, IW8 und IW3 verwarfen jeden so
        # erzeugten Reserve-Kandidaten bei der Zertifizierung. Ab jetzt
        # kommt der End-CTA aus scripts/cta_builder.py (Kontrakt-Wahrheit,
        # immer /go/-Übergabeseite). Route-Erkennung: erst Themensignale
        # des Topics, dann die URL-Abbildung aus check24_links.yaml.
        import cta_builder
        import affiliate_intent_contract as aic
        route = aic.route_fuer_text(
            "\n".join([topic or "", " ".join(keywords or [])]),
            titel=topic or "", pillar=str(topic_entry.get("pillar") or "")) or ""
        cta = cta_builder.cta_end_block(
            affiliate_url=affiliate_url, route=route, slug=slug)
    except Exception as _cta_err:                       # noqa: BLE001
        print(f"  ⚠ Kontrakt-CTA nicht verfügbar ({_cta_err}) – Portal-Fallback")
        import cta_builder
        cta = cta_builder.cta_end_block(affiliate_url=affiliate_url, slug=slug)
    def _yq(value):
        """YAML-sicher quoten (Doppelpunkte/Sonderzeichen)."""
        v = str(value)
        if ":" in v or "#" in v or v != v.strip():
            return '"' + v.replace('"', '\\"') + '"'
        return v

    inspiration_line = ""
    if pin:
        inspiration_line = (
            f"inspiration: {_yq('Pin ' + str(pin.get('tag')) + ' – „' + str(pin.get('titel', '')) + '“')} "
            "(nur Themen-Grundlage, eigenständig formuliert)\n"
        )
    draft_flag = "false" if auto_publish else "true"
    try:
        import editorial_review_gate as _erg
        review_risk = _erg.classify_text(
            " ".join([title, topic] + list(keywords or [])[:2]),
            topic_entry.get("pillar") or "")
        review_block = _erg.review_scaffold_yaml(review_risk)
    except Exception as exc:  # noqa: BLE001 - Gate klassifiziert später fail-closed
        print(f"  ⚠ Risikoklasse nicht vormerkbar: {exc}")
        review_block = ""
    frontmatter = (
        "---\n"
        f"title: {yaml_str(title)}\n"
        f"description: {yaml_str(desc)}\n"
        f"date: {date}\n"
        f"draft: {draft_flag}\n"
        f'tags: {json.dumps(_register_tags(keywords, topic_entry.get("pillar"), title), ensure_ascii=False)}\n'
        f'categories: ["Ratgeber"]\n'
        + (f'pillar: "{topic_entry.get("pillar")}"\n' if topic_entry.get("pillar") else "")
        + f"keywords: {json.dumps(keywords, ensure_ascii=False)}\n"
        f"author: {yaml_str(AUTHOR)}\n"
        f"ai_generated: true\n"
        f"ai_provider: {yaml_str(provider_name)}\n"
        f"{review_block}"
        f"{inspiration_line}"
        "---\n\n"
    )
    with open(filename, "w", encoding="utf-8") as f:
        f.write(frontmatter + fix_number_units(body) + "\n" + cta)
    # FRONTMATTER-VALIDIERUNG: Pflichtfelder müssen gesetzt sein – sonst
    # wird die Datei repariert (fehlende Felder ergänzt). Verhindert, dass
    # ein Artikel ohne Title/Description/Date/draft live geht.
    try:
        validate_frontmatter(filename)
    except Exception as e:
        print(f"  ⚠ Frontmatter-Validierung: {e}")
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


def pillar_from_pinwand(pinwand):
    """Pillar aus Board-Name – Single Source of Truth: data/pinterest_boards.yaml.
    Damit tragen Plan-Artikel die KORREKTE Pillar (Cluster-Linking + Board-Routing)
    statt des Defaults 'konto-karten'."""
    try:
        import yaml as _yaml
        cfg = _yaml.safe_load(open(
            os.path.join(BLOG_DIR, "data", "pinterest_boards.yaml"), encoding="utf-8")) or {}
    except Exception:
        return None
    pw = re.sub(r"\s+", " ", (pinwand or "").strip().lower())
    for b in cfg.get("boards", []):
        if re.sub(r"\s+", " ", (b.get("name") or "").strip().lower()) == pw:
            pillars = b.get("pillars") or []
            return pillars[0] if pillars else None
    return None


def load_pin_topics():
    """Lädt Themen direkt aus dem Pinterest-Plan (data/pinterest_plan.yaml).
    Jeder Pin wird zu einem Themen-Eintrag – die Pins sind damit die
    Grundlage für die Artikel (nur als Inspiration, nie 1:1 kopiert).

    WICHTIG: Jeder Pin bekommt den PASSENDEN Affiliate-Link aus
    scripts/check24_links.yaml zugewiesen (basierend auf Ziel-URL/Pinwand).
    Ändern sich die Links, genügt ein Update der check24_links.yaml –
    neue Artikel nutzen dann automatisch die neuen Links.

    Premium (25.08.2026): Themen tragen zusätzlich pinwand + pillar
    (Board-Routing) und die kuratierten Pin-Texte (pin_titel/pin_
    beschreibung) – die Engine schreibt sie in das Artikel-Frontmatter,
    damit PINs mit Premium-Text auf dem richtigen Board landen."""
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
        pinwand = (p.get("pinwand") or "").strip()
        topics.append({
            "title": titel,
            "keywords": kws[:5] or ["Geld sparen", "Ratgeber"],
            "affiliate_url": affiliate,
            "pin_category": cat,
            "pinwand": pinwand,
            "pillar": pillar_from_pinwand(pinwand),
            "pin_typ": (p.get("typ") or "EP").strip(),
            "pin_titel": titel,
            "pin_beschreibung": (p.get("beschreibung") or "").strip(),
        })
    return topics


def main():
    if not os.path.isdir(POSTS_DIR):
        os.makedirs(POSTS_DIR, exist_ok=True)
    auto_publish = os.environ.get("AUTO_PUBLISH", "0") == "1"

    # KADENZ-HARD-GATE (26.08.2026, Defense-in-Depth): Auch ein direkter
    # Aufruf dieses Legacy-Skripts mit AUTO_PUBLISH=1 veröffentlicht NUR
    # an Mo/Mi/Fr (Dauervorgabe, CADENCE-REPORT.md Regel 2). Die Engine
    # (engine_generate.py) hat denselben Guard; hier schützt er den
    # Fall "Skript wird direkt mit AUTO_PUBLISH=1 ausgeführt".
    # Entwürfe (AUTO_PUBLISH ungesetzt/0) sind davon unberührt.
    if auto_publish and os.environ.get("FORCE_PUBLISH_ANY_DAY") != "1":
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import cadence_guard
        today = datetime.date.today()
        if not cadence_guard.is_publication_day(today):
            print(f"🛑 KADENZ-GATE: Heute ist {cadence_guard.DAYS_DE[today.weekday()]} "
                  f"– automatische Veröffentlichung nur Mo/Mi/Fr (Dauervorgabe).")
            print("   Notfall-Override: FORCE_PUBLISH_ANY_DAY=1 (bewusst, bleibt im Log).")
            return

    pin_topics = os.environ.get("PIN_TOPICS", "0") == "1"
    # Tages-Limit: Wie viele Artikel dürfen pro Tag veröffentlicht werden?
    # (Guard gegen mehrere Workflow-Läufe pro Tag – GitHub-Crons können
    #  verzögert laufen oder doppelt ausgelöst werden.)
    max_per_day = int(os.environ.get("MAX_ARTIKEL_PRO_TAG", "2"))

    # Heute bereits veröffentlichte Artikel zählen
    today = datetime.date.today().isoformat()
    published_today = 0
    if os.path.isdir(POSTS_DIR):
        for path in list_post_paths():
            slug = slug_of(path)
            if slug.startswith(today):
                with open(path, encoding="utf-8") as f:
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

    # SELBSTHEILENDER THEMENPOOL: Wenn nur noch wenige Themen frei sind,
    # lässt die KI neue Themenvorschläge generieren und ergänzt topics.yaml.
    # So läuft der Generator nie leer (dauerhafte Vollautomatik).
    freie_vorher = [t for t in topics if not topic_already_covered(t["title"], used_titles)]
    if len(freie_vorher) < 8:  # Schwelle für 4 Posts/Tag (früher nachfüllen)
        print(f"  – Themenpool fast leer ({len(freie_vorher)} frei) → KI generiert Nachschub …")
        neu = refill_topics(topics, used_titles)
        if neu:
            topics = load_topics()  # neu laden (Datei wurde ergänzt)
            quelle += " + KI-Nachschub"
            print(f"  – Themenpool aufgefrischt: jetzt {len(topics)} Themen")

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
        try:
            if write_draft(topic_entry, angle, provider=None, used_titles=used_titles,
                           auto_publish=auto_publish):
                created += 1
        except Exception as e:
            # FEHLER-ISOLATION: Ein fehlerhaftes Thema (z. B. API-Format-Wechsel,
            # unerwarteter Datentyp) stoppt NICHT den gesamten Lauf. Der Fehler
            # wird protokolliert, der nächste Versuch startet.
            import traceback
            print(f"  ⚠ Fehler bei Thema „{topic_entry['title'][:50]}…“: {type(e).__name__}: {e}")
            traceback.print_exc()
            print("  → Thema übersprungen, nächster Versuch …")
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
