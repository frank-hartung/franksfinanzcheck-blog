#!/usr/bin/env python3
# ============================================================
#  SOCIAL-COPYWRITER – kanalnative Beitrags-Erstellung
#  ------------------------------------------------------------
#  AUFTRAG: Für JEDEN Artikel × JEDEN Kanal × JEDEN Winkel eine
#  eigene, kanalgerechte Fassung – nicht ein Text für alle Netze.
#
#  ARBEITSWEISE (Hybrid, Dauervorgabe):
#    1. MATERIAL: Aus dem Artikel werden belastbare Bausteine
#       gezogen – Kurzantwort (der beste Hook), die „Das Wichtigste in
#       Kürze"-Punkte, konkrete Euro-/Prozent-Zahlen, die FAQ-Frage,
#       Titel und Pillar. Nichts wird erfunden.
#    2. ENTWURF: Eine deterministische, budgetbewusste Vorlage je
#       Kanal-Typ (microblog · business · visual · messenger ·
#       community · pin). Sie respektiert Zeichenlimit, Hashtag-Zahl,
#       Link-Position und Emoji-Budget – IMMER.
#    3. POLITUR (optional): Mit Gratis-LLM-Key (Groq/Gemini) wird die
#       Vorlage kanalgerecht geschliffen. Der Entwurf bleibt
#       Rückfallebene: Ohne Key, bei Timeout oder wenn die KI gegen
#       eine Kanalregel verstößt (Länge, fehlender Link, erfundene
#       Zahlen), gilt automatisch die Vorlage.
#
#  Kosten-Regel des Blogs bleibt unangetastet: ausschließlich
#  Gratis-Provider (Groq/Gemini) – nie Paid-APIs.
# ============================================================
from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timezone

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BLOG_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
DEFAULT_BASE = "https://franksfinanzcheck.de"

# ---------------------------------------------------------------- Pillar-Wissen
PILLAR_TAGS = {
    "internet-dsl": ["DSL", "Internet"],
    "strom-sparen": ["Stromsparen", "Energiekosten"],
    "versicherungen": ["Versicherung", "Vorsorge"],
    "konto-karten": ["Girokonto", "Sparen"],
    "mietwagen": ["Mietwagen", "Reise"],
    "frugalismus": ["Frugalismus", "Geldsparen"],
}
ACRONYMS = {"dsl", "etf", "kfz", "sepa", "wlan", "dns", "vpn", "gez", "agb",
            "eeg", "kwh", "iban", "bic", "seo", "ai", "pkv", "ok", "eu", "tls"}
KEYWORD_HINTS = [
    (r"wechselbonus", ["DSL", "Wechselbonus"]),
    (r"preisgarantie|gaspreisgarantie|gaspreis", ["Gaspreis", "Preisgarantie"]),
    (r"gasrechnung|heizkosten|heizen|heizung", ["Gasrechnung", "Heizkosten"]),
    (r"\bwlan\b", ["WLAN", "Internet"]),
    (r"dsl.?vergleich|internet.?vergleich", ["DSL", "DSLVergleich"]),
    (r"girokonto|kontoführungs|kontofuehrungs", ["Girokonto", "Konto"]),
    (r"haftpflicht", ["Privathaftpflicht", "Versicherung"]),
    (r"wohngebäude|wohngebaeude|elementar|hausversicherung", ["Wohngebaeude", "Versicherung"]),
    (r"stromfresser|energiedieb|standby", ["Stromsparen", "Energiekosten"]),
    (r"mietwagen|leihwagen|kaution", ["Mietwagen", "Reise"]),
    (r"frugalismus|konsumverzicht|haushaltsbuch|50.?30.?20", ["Frugalismus", "Geldsparen"]),
    (r"handytarif|mobilfunk|sim.?karte", ["Handytarif", "Mobilfunk"]),
    (r"tagesgeld|zinssatz|festgeld|zinsen", ["Tagesgeld", "Zinsen"]),
    (r"photovoltaik|solar|balkonkraftwerk", ["Photovoltaik", "Energiekosten"]),
]
WEAK_TAG_RX = re.compile(r"gebuehren|fuehrungs|vergleich$|zuhause|vorbereitung|hacks$", re.I)

# Schlusslicht-Pool: Reichen Titel, Keywords und Pillar nicht aus, um das
# Hashtag-MINIMUM eines Kanals zu erfüllen (Instagram: 5, LinkedIn: 3),
# wird aus dieser Liste aufgefüllt – thematisch nah, suchbar, markenkonform.
# Ohne diesen Pool lief die alte Auffüll-Zeile `add("Finanzen")` ins Leere,
# weil `add()` genau dieses Token ausschließt: LinkedIn war dadurch zu 100 %
# vom Gate blockiert (Meldung #716, Nebenbefund).
FALLBACK_TAGS = ["Finanzen", "Fixkosten", "Spartipps", "Geldsparen", "Haushaltsbudget",
                 "Vorsorgen", "Tarifvergleich", "Alltagskosten", "BudgetPlanen",
                 "Verbrauchertipps", "Finanzwissen"]

# Gleiche Klassen wie social_gate.EMOJI_RX – bewusst doppelt gehalten, weil
# das Gate den Texter nicht importieren darf (Zirkelschluss). Die Parität
# bewacht scripts/tests/test_social_autopilot.py (TestKanaltreue).
EMOJI_RX = re.compile(
    "[" "\u2190-\u21FF" "\u2600-\u27BF" "\u2B00-\u2BFF" "\U0001F000-\U0001FAFF" "]"
)
PFEIL_RX = re.compile("[\u2190-\u21FF\u2794\u279C\u27A1]")

# Kuratierte Mythen je Pillar (für den Winkel „mythos").
# Bewusst allgemeingültig formuliert – der Fakt daneben kommt immer
# aus dem Artikel selbst, nie aus dieser Liste.
MYTHS = {
    "internet-dsl": "Ein teurerer Tarif ist automatisch der schnellere.",
    "strom-sparen": "Standby-Geräte kosten nur ein paar Cent im Jahr.",
    "versicherungen": "Die alte Versicherung ist immer die günstigere.",
    "konto-karten": "Kontoführungsgebühren sind unvermeidbar.",
    "mietwagen": "Wer früh bucht, bekommt immer den besten Preis.",
    "frugalismus": "Sparen heißt, auf alles zu verzichten.",
}
GENERIC_MYTH = "Ohne großen Aufwand lässt sich an Fixkosten nichts drehen."

QUESTIONS = {
    "internet-dsl": "Welcher Tarif läuft bei dir wirklich stabil?",
    "strom-sparen": "Welcher Stromfresser ist bei dir der größte Posten?",
    "versicherungen": "Wann hast du deine Policen zuletzt geprüft?",
    "konto-karten": "Was zahlst du heute noch für dein Konto?",
    "mietwagen": "Welcher Mietwagen-Fehler hat dich am meisten geärgert?",
    "frugalismus": "Welche Sparregel hält bei dir im Alltag stand?",
}
GENERIC_QUESTION = "Was ist dein stärkster Hebel beim Sparen?"


# ------------------------------------------------------------- Artikel-Material
def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def _frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return ""
    m = re.search(r"(?m)^---", text[4:])
    return text[4:4 + m.start()] if m else ""


# ------------------------------------------------- Grammatik der Copy-Quelle
# Befund 30.10.2026: Der Artikel 2026-10-24-etf-sparplan-… stand mit
# „Dein Schritt-für-Schritt-Anleitung“ im Frontmatter. Jeder Kanal baut seine
# Überschrift aus genau diesem Feld – der Fehler wanderte also ungeprüft auf
# Pinterest, X, Bluesky, Instagram, Facebook, Threads und LinkedIn. Eine
# Quell-Heilung allein genügt nicht: Die Copy wird TÄGLICH neu erzeugt, und
# jedes spätere Redaktionsversehen im Titel stünde sofort in sieben Kanälen.
# Deshalb heilt die Copy-Quelle sich selbst – mit demselben Beweis wie der
# Blogtext (LT5/LT6 aus `grammar_check.py`, eindeutiges Ziel oder nichts).
def _kongruenz_heilen(text: str) -> str:
    """Heilt eindeutige Kongruenz-Fehler in einem Copy-Baustein (sonst unverändert)."""
    if not text:
        return text
    try:
        import grammar_check
        funde = grammar_check.kongruenz_funde(text, grammar_check.lade_genus_lexikon())
    except Exception:  # eine kaputte Wache darf die Copy nicht blockieren
        return text
    for f in sorted(funde, key=lambda x: x["start"], reverse=True):
        if not f.get("fix"):
            continue
        text = text[:f["start"]] + f["fix"] + text[f["end"]:]
    return text


def _fm_field(fm: str, name: str) -> str:
    m = re.search(rf'^{name}:\s*["\']?(.*?)["\']?\s*$', fm, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _fm_list(fm: str, name: str) -> list[str]:
    m = re.search(rf"^{name}:\s*\[(.*?)\]", fm, re.MULTILINE)
    if not m:
        return []
    return [t.strip().strip('"').strip("'") for t in m.group(1).split(",") if t.strip()]


# Punkte, die KEIN Satzende sind: Ordnungszahlen vor Monat oder kleinem Wort
# („vom 1. Januar bis 31. Dezember“, „der 3. und letzte“) und gängige
# Abkürzungen („z. B.“, „ca.“, „bzw.“). Ohne diesen Schutz riss der Texter
# Sätze mitten im Datum ab und baute daraus Beiträge wie „… laufen vom 1.“.
_MONATE = (r"(?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|"
           r"Oktober|November|Dezember|Jan|Feb|Mär|Apr|Jun|Jul|Aug|Sep|Sept|"
           r"Okt|Nov|Dez)\b")
_KEIN_SATZENDE_RX = re.compile(
    r"(?:\b\d{1,2}\.(?=\s+(?:" + _MONATE + r"|[a-zäöüß]))"
    r"|\b(?:z|d|u|o|s|v)\.\s?[a-zA-Z]\."
    r"|\b(?:ca|bzw|ggf|inkl|zzgl|evtl|usw|etc|vgl|Nr|Abs|Art|Mio|Mrd|Tsd|max|min|bspw|sog)\.)")
_PUNKT_PLATZHALTER = "\u2024"   # ONE DOT LEADER – unsichtbar für den Splitter


def sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return []
    geschuetzt = _KEIN_SATZENDE_RX.sub(
        lambda m: m.group(0).replace(".", _PUNKT_PLATZHALTER), text)
    parts = re.split(r"(?<=[.!?])\s+", geschuetzt)
    return [p.replace(_PUNKT_PLATZHALTER, ".").strip() for p in parts if p.strip()]


def clean_md(line: str) -> str:
    """Entfernt Markdown-Reste aus Aufzählungspunkten."""
    line = re.sub(r"\*\*(.+?)\*\*", r"\1", line or "")
    line = re.sub(r"\*(.+?)\*", r"\1", line)
    line = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1", line)
    line = re.sub(r"\s+", " ", line).strip(" •-*\t")
    return line.strip()


def extract_takeaways(body: str, limit: int = 4) -> list[str]:
    """Liest die „Das Wichtigste in Kürze"-Punkte eines Artikels."""
    if not body:
        return []
    # Zwei Bauarten kommen im Blog vor: echte Überschrift (## …) und
    # ein fetter Fließtext-Kopf (**Das Wichtigste in Kürze**).
    m = re.search(
        r"(?ims)^(?:#{2,4}\s*|\**\s*)(?:das wichtigste in kürze|auf einen blick|kernpunkte)"
        r"\s*[:\-–—]?\s*\**\s*$\s*(.{0,2200})", body)
    block = m.group(1) if m else ""
    out: list[str] = []
    if block:
        for line in block.splitlines():
            line = line.strip()
            if not line:
                if out:
                    break
                continue
            if re.match(r"^([-*•]|\d+\.)\s+", line):
                item = clean_md(re.sub(r"^([-*•]|\d+\.)\s+", "", line))
                if 12 <= len(item) <= 220:
                    out.append(item)
            elif out:
                break
            if len(out) >= limit:
                break
    return out[:limit]


def extract_numbers(text: str, limit: int = 4) -> list[str]:
    """Konkrete Euro-/Prozent-Angaben – das Kapital dieses Blogs."""
    found: list[str] = []
    rx = re.compile(r"(?:bis zu\s+)?\d[\d.,]*\s?(?:€|Euro|Prozent|%|Grad|kWh|Stunden|"
                    r"Minuten|Monate|Jahre|Tage|Cent)", re.I)
    for m in rx.finditer(text or ""):
        val = re.sub(r"\s+", " ", m.group(0)).strip()
        low = val.lower()
        if "bis zu" not in low:
            val = val
        if val not in found:
            found.append(val)
        if len(found) >= limit:
            break
    return found


def extract_faq(body: str) -> tuple[str, str]:
    """Erste FAQ-Frage + Antwort (für den Winkel „frage")."""
    if not body:
        return "", ""
    # REPARATUR 14.10.2026: Ohne DOTALL fing `(.{0,2500})` nur den Rest der
    # Überschriftenzeile – also nichts. Der Winkel `frage` lief dadurch auf
    # JEDEM Kanal in den Titel-Rückfall, obwohl fast jeder Ratgeber einen
    # FAQ-Block hat. Der Block ist jetzt das, was nach der Überschrift folgt.
    m = re.search(r"(?im)^#{2,4}\s*(?:faq|häufige fragen|haeufige fragen)\b.*$", body)
    if not m:
        return "", ""
    block = body[m.end():m.end() + 2500]
    q = re.search(r"(?m)^#{3,4}\s*(.+?\?)\s*$", block)
    if not q:
        return "", ""
    zeilen = []
    for line in block[q.end():].splitlines():
        if line.lstrip().startswith("#"):
            break    # nächste Frage/Überschrift – nie in die Antwort ziehen
        if clean_md(line):
            zeilen.append(clean_md(line))
        if len(zeilen) >= 6:
            break
    saetze = sentences(" ".join(zeilen))
    # Eine Antwort wie „Nicht zwingend.“ ist ein Auftakt, keine Antwort: Sie
    # bekommt den folgenden Satz dazu, der die Begründung trägt.
    antwort = saetze[0] if saetze else ""
    if antwort and len(antwort) < 60 and len(saetze) > 1:
        antwort = f"{antwort} {saetze[1]}"
    return clean_md(q.group(1)), antwort


def load_article(path: str, base_url: str = DEFAULT_BASE) -> dict:
    """Baut das Material-Bündel eines Artikels (nie eine Exception)."""
    text = _read(path)
    fm = _frontmatter(text)
    body = text[4 + len(fm):] if text.startswith("---\n") else text
    body = re.sub(r"(?m)^\-\-\-\s*$", "", body, count=1)

    slug = os.path.basename(os.path.dirname(path)) if os.path.basename(path) == "index.md" \
        else os.path.basename(path)[:-3]
    title = _fm_field(fm, "title") or slug.replace("-", " ").title()
    kurzantwort = _fm_field(fm, "kurzantwort")
    description = _fm_field(fm, "description")
    # Copy-Quelle selbstheilend: Was hier falsch bleibt, steht später in jedem
    # Kanal. Nur eindeutige Funde werden geschrieben, der Rest bleibt sichtbar.
    title = _kongruenz_heilen(title)
    kurzantwort = _kongruenz_heilen(kurzantwort)
    description = _kongruenz_heilen(description)
    cover = ""
    m_cover = re.search(r"image:\s*[\"']?(.*?)[\"']?\s*$", fm, re.MULTILINE)
    if m_cover:
        cover = m_cover.group(1).strip()
    alt = ""
    m_alt = re.search(r"^\s+alt:\s*[\"']?(.*?)[\"']?\s*$", fm, re.MULTILINE)
    if m_alt:
        alt = m_alt.group(1).strip()

    hook_src = kurzantwort or description
    hook_parts = sentences(hook_src)
    takeaways = extract_takeaways(body)
    numbers = extract_numbers(f"{kurzantwort} {description} {title}")
    faq_q, faq_a = extract_faq(body)

    date_raw = _fm_field(fm, "date")
    published = ""
    if date_raw:
        try:
            published = datetime.fromisoformat(date_raw.replace("Z", "+00:00")).isoformat()
        except ValueError:
            published = date_raw

    return {
        "slug": slug,
        "path": path,
        "title": title,
        "description": description,
        "kurzantwort": kurzantwort,
        "hook": hook_parts[0] if hook_parts else "",
        "hook_sentences": hook_parts,
        "takeaways": takeaways,
        "numbers": numbers,
        "faq_question": faq_q,
        "faq_answer": faq_a,
        "tags": _fm_list(fm, "tags"),
        "keywords": _fm_list(fm, "keywords"),
        "pillar": _fm_field(fm, "pillar"),
        "pin_title": _kongruenz_heilen(_fm_field(fm, "pin_title")),
        "cover": cover,
        "cover_alt": alt,
        "draft": _fm_field(fm, "draft").lower() == "true",
        "reserve": _fm_field(fm, "reserve").lower() == "true",
        "published": published,
        "url": f"{base_url.rstrip('/')}/posts/{slug}/",
        "raw_fm": fm,
    }


def article_pool(base_url: str = DEFAULT_BASE) -> list[dict]:
    """Alle veröffentlichten Artikel (keine Entwürfe, keine Reserve)."""
    import post_utils

    out = []
    for path in post_utils.list_post_paths():
        art = load_article(path, base_url=base_url)
        if art["draft"] or art["reserve"] or not art["title"]:
            continue
        out.append(art)
    return out


# ------------------------------------------------------------------ Hashtags
def umlaut_free(s: str) -> str:
    return (s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
             .replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue").replace("ß", "ss"))


def _kanon_kuerzel_tags() -> dict[str, str]:
    """Kürzel-Kanon des Hauses (`tag_casing`) für Hashtags: „https“ → „HTTPS“.

    Die lokale Liste `ACRONYMS` bleibt vorrangig (bestehende Tags ändern sich
    nicht); der Kanon schließt nur ihre Lücken. Vorher wurde aus „DNS over
    HTTPS“ das Tag „#DNSOverHttps“ – auf dem Kanal, der Fachkompetenz zeigen
    soll, eine sichtbar falsche Schreibweise.
    """
    try:
        import tag_casing
    except Exception:  # noqa: BLE001 – ohne Kanon gilt die lokale Liste
        return {}
    out = {}
    for key, kanon in tag_casing.ACRONYMS.items():
        token = re.sub(r"[^A-Za-z0-9]", "", str(kanon))
        if token and token.lower() == key:
            out[key] = token
    return out


KANON_TAG_KUERZEL = _kanon_kuerzel_tags()


def _tag_token(word: str) -> str:
    core = re.sub(r"[^A-Za-z0-9]", "", umlaut_free(word or ""))
    if not core:
        return ""
    if core.lower() in ACRONYMS:
        return core.upper()
    return KANON_TAG_KUERZEL.get(core.lower()) or core.capitalize()


def to_hashtag(phrase: str) -> str:
    return "".join(_tag_token(w) for w in re.split(r"[\s\-/]+", phrase or "") if w)


def emoji_budget_halten(text: str, budget: int) -> str:
    """Hält das Emoji-/Symbol-Budget des Kanals ein (L5 im Gate).

    Artikel übernehmen Symbole aus dem Bestand (z. B. „Kosten sehen →
    Konditionen rechnen"). Auf Reddit (Budget 0) oder Telegram (2) machte das
    den Beitrag unsendbar. Pfeile werden zu Gedankenstrichen – sie tragen
    Bedeutung –, übrige Symbole entfallen ersatzlos.
    """
    budget = max(0, int(budget or 0))
    behalten = 0

    def ersetze(m: "re.Match[str]") -> str:
        nonlocal behalten
        if behalten < budget:
            behalten += 1
            return m.group(0)
        return "–" if PFEIL_RX.match(m.group(0)) else ""

    out = EMOJI_RX.sub(ersetze, text or "")
    return re.sub(r"[ \t]{2,}", " ", out)


def pick_hashtags(article: dict, channel_cfg: dict) -> list[str]:
    """Suchbare, kurze CamelCase-Tags – kanalweise begrenzt UND minimumssicher.

    Das Gate verlangt je Kanal eine Mindestzahl (Instagram 5, LinkedIn 3).
    Reichen Artikel-Tags nicht, füllt `FALLBACK_TAGS` auf – sonst blockiert
    L4 den Kanal vollständig, obwohl Text und Bild einwandfrei sind.
    """
    ht = ((channel_cfg or {}).get("text") or {}).get("hashtags") or {}
    maximum = int(ht.get("max") or 3)
    minimum = min(int(ht.get("min") or 0), maximum)
    max_len = int(ht.get("max_len") or 20)
    corpus = " ".join([
        article.get("title") or "", article.get("kurzantwort") or "",
        article.get("description") or "", " ".join(article.get("tags") or []),
        " ".join(article.get("keywords") or []), article.get("pillar") or "",
    ])
    picked: list[str] = []
    seen: set[str] = set()

    def add(token: str) -> None:
        token = (token or "").strip()
        if not token or token.lower() in seen or token.lower() == "finanzen":
            return
        if len(token) > max_len or len(picked) >= maximum:
            return
        if any(token.lower().startswith(p.lower()) or p.lower().startswith(token.lower())
               for p in picked):
            return
        seen.add(token.lower())
        picked.append(token)

    for rx, hints in KEYWORD_HINTS:
        if re.search(rx, corpus, re.I):
            for h in hints:
                add(h)
        if len(picked) >= maximum:
            break
    for raw in (article.get("tags") or []) + (article.get("keywords") or []):
        token = to_hashtag(raw)
        if token and not WEAK_TAG_RX.search(token):
            add(token)
        if len(picked) >= maximum:
            break
    if len(picked) < 2:
        for h in PILLAR_TAGS.get(article.get("pillar") or "", []):
            add(h)

    # Minimums-Garantie: Der Schlusslicht-Pool darf auch „Finanzen" setzen,
    # das `add()` aus dem Artikel-Korpus bewusst fernhält.
    for token in FALLBACK_TAGS:
        if len(picked) >= max(minimum, 1) or len(picked) >= maximum:
            break
        if len(token) > max_len:
            continue
        low = token.lower()
        if low in seen or any(low.startswith(p.lower()) or p.lower().startswith(low)
                              for p in picked):
            continue
        seen.add(low)
        picked.append(token)
    return picked[:maximum]


def tag_string(tags: list[str]) -> str:
    return " ".join(f"#{t}" for t in tags if t)


# -------------------------------------------------------------- Budget-Helfer
def trim(text: str, max_len: int) -> str:
    """Kürzt an Wortgrenzen – und ERHÄLT Zeilenumbrüche (Listen!).

    Ein Aufzählungsblock darf beim Kürzen nicht zu einer Zeile
    zusammenfallen: Mastodon-, LinkedIn- und Telegram-Beiträge leben von
    der Struktur. Darum wird zeilenweise gekürzt, nie der ganze Block
    flachgewalzt.
    """
    if not text:
        return ""
    text = re.sub(r"[ \t]+", " ", text.strip())
    if len(text) <= max_len or max_len <= 0:
        return text
    if "\n" in text:
        lines = [ln for ln in text.split("\n") if ln.strip()]
        out: list[str] = []
        used = 0
        for line in lines:
            rest = max_len - used - (2 if out else 0)
            if len(line) <= rest:
                out.append(line)
                used += len(line) + 2
                continue
            # Passt die Zeile nicht, wird sie selbst gekürzt – aber erst,
            # wenn dafür noch sinnvoll Platz ist (sonst weglassen).
            if rest >= 24:
                out.append(_trim_flat(line, rest))
            break
        return "\n".join(out)
    return _trim_flat(text, max_len)


def _trim_flat(text: str, max_len: int) -> str:
    cut = text[:max_len]
    sp = cut.rfind(" ")
    if sp > max_len * 0.5:
        cut = cut[:sp]
    return cut.rstrip(" ,;:-–—") + " …"


def bullets_of(article: dict, limit: int = 3, max_len: int = 130) -> list[str]:
    """Aufzählungspunkte eines Artikels.

    Erste Wahl sind die „Das Wichtigste in Kürze"-Punkte. Ältere Artikel
    haben diesen Block nicht – dort übernehmen die Folgesätze der
    Kurzantwort die Rolle der Aufzählung (strukturiert statt flach).
    """
    items = list(article.get("takeaways") or [])
    if not items:
        items = [s for s in (article.get("hook_sentences") or [])[1:]]
    out = [trim(t, max_len) for t in items if t and len(t.strip()) > 12]
    return out[:limit]


def effective_length(text: str, url: str, link_weight: int = 0) -> int:
    """Länge, wie die PLATTFORM sie zählt.

    X zählt jeden Link pauschal mit 23 Zeichen (t.co-Kürzung) – ein
    140-Zeichen-Link kostet dort also nur 23. Wer das ignoriert, verschenkt
    auf dem kürzesten Kanal im Portfolio ein Drittel des Budgets.
    """
    if link_weight and url and url in (text or ""):
        return len(text) - len(url) + int(link_weight)
    return len(text or "")


def _hard_fit(text: str, max_chars: int, keep: list[str]) -> str:
    """Letzte Instanz vor dem Senden: Text auf das Limit bringen, Link und
    Hashtags retten. Schneidet nie mitten in den Link."""
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    protected = [k for k in keep if k and k in text]
    rest = text
    for k in protected:
        rest = rest.replace(k, "")
    room = max_chars - sum(len(k) + 2 for k in protected)
    rest = trim(rest, max(30, room - 2))
    out = ([rest] if rest else []) + protected
    res = "\n\n".join(x for x in out if x)
    if len(res) <= max_chars:
        return res
    if protected:
        # Notfall: Kopf kappen, der Link überlebt als letztes Element.
        tail = "\n\n" + protected[-1]
        head = res[: max_chars - len(tail)].rstrip(" ,;:-–—")
        if len(head) + len(tail) <= max_chars:
            return head + tail
    return res[:max_chars]


def _fit_limit(text: str, url: str, tags_txt: str, cfg: dict) -> str:
    """Bringt einen Beitrag sicher unter das Kanal-Limit."""
    text_cfg = (cfg or {}).get("text") or {}
    max_chars = int(text_cfg.get("max_chars") or 500)
    weight = int(text_cfg.get("link_weight") or 0)
    if effective_length(text, url, weight) <= max_chars:
        return text
    # Plattform-Zählung in echtes Zeichenbudget zurückrechnen
    budget = max_chars + (len(url) - weight if (weight and url and url in text) else 0)
    return _hard_fit(text, max(budget, 60), [url if url in text else "", tags_txt])


def build_url(article: dict, channel_id: str, meta: dict) -> str:
    """Kanonische Artikel-URL mit UTM-Kanalmarkierung (nie /go/)."""
    utm = (meta or {}).get("utm") or {}
    url = article["url"]
    sep = "&" if "?" in url else "?"
    return (f"{url}{sep}utm_source={channel_id}"
            f"&utm_medium={utm.get('medium', 'social')}"
            f"&utm_campaign={utm.get('campaign', 'autopilot')}")


def _budget(channel_cfg: dict, reserved: int) -> int:
    return max(60, int(((channel_cfg or {}).get("text") or {}).get("max_chars") or 500) - reserved)


def _emoji(channel_cfg: dict, allowed: list[str]) -> str:
    """Liefert ein Emoji, wenn das Kanal-Budget es zulässt (sonst leer)."""
    n = int(((channel_cfg or {}).get("text") or {}).get("emoji_max") or 0)
    return allowed[0] if (n > 0 and allowed) else ""


# ------------------------------------------------------------------ Komponist
def compose(article: dict, channel_id: str, channel_cfg: dict, angle: str,
            meta: dict, use_llm: bool = True) -> dict:
    """Baut die kanalnative Fassung. Ergebnis ist IMMER gültig."""
    kind = (channel_cfg or {}).get("kind") or "microblog"
    url = build_url(article, channel_id, meta)
    tags = pick_hashtags(article, channel_cfg)
    tags_txt = tag_string(tags)
    link_pos = ((channel_cfg or {}).get("text") or {}).get("link_position") or "end"

    builders = {
        "microblog": _compose_microblog,
        "business": _compose_business,
        "visual": _compose_visual,
        "messenger": _compose_messenger,
        "community": _compose_community,
        "pin": _compose_pin,
    }
    builder = builders.get(kind, _compose_microblog)
    pkg = builder(article, channel_cfg, angle, url, tags, tags_txt, link_pos)

    # Sicherheitsnetz: kein Beitrag verlässt dieses Modul über dem Limit.
    pkg["text"] = _fit_limit(pkg.get("text") or "", url, tags_txt, channel_cfg)
    if pkg.get("thread"):
        pkg["thread"] = [_fit_limit(t, url, tags_txt, channel_cfg) for t in pkg["thread"]]

    # Kanaltreue: Das Emoji-/Symbol-Budget des Kanals gilt JEDEM Teil.
    # Symbole aus dem Artikelbestand (Pfeile, Häkchen) dürfen einen Beitrag
    # nicht unsendbar machen – sie werden kanalgerecht zurückgebaut.
    budget = int(((channel_cfg or {}).get("text") or {}).get("emoji_max") or 0)
    pkg["text"] = emoji_budget_halten(pkg.get("text") or "", budget)
    if pkg.get("thread"):
        pkg["thread"] = [emoji_budget_halten(t, budget) for t in pkg["thread"]]
    if pkg.get("comment"):
        pkg["comment"] = emoji_budget_halten(pkg["comment"], budget)

    pkg.update({
        "channel": channel_id,
        "slug": article["slug"],
        "angle": angle,
        "hashtags": tags,
        "url": url,
        "article": article,
        "alt": _alt_text(article),
        "headline": pkg.get("headline") or _headline(article, channel_cfg),
    })

    if use_llm:
        polished = polish(pkg, channel_cfg, meta)
        if polished:
            pkg["text"] = polished
            pkg["ai_polished"] = True
        else:
            pkg["ai_polished"] = False
    return pkg


def _headline(article: dict, channel_cfg: dict) -> str:
    limit = int(((channel_cfg or {}).get("text") or {}).get("title_max_chars") or 100)
    base = article.get("pin_title") or article.get("title") or ""
    return trim(base, limit)


def _alt_text(article: dict) -> str:
    alt = (article.get("cover_alt") or "").strip()
    if alt and len(alt) >= 24 and not re.match(r"^(cover|bild|image|foto)\.?$", alt, re.I):
        return alt[:400]
    return f"{article.get('title', '')} – unabhängiger Spar-Tipp von FranksFinanzcheck"[:400]


# --- microblog (Mastodon, Bluesky, X, Threads) ------------------------------
def _compose_microblog(article, cfg, angle, url, tags, tags_txt, link_pos):
    max_chars = int((cfg.get("text") or {}).get("max_chars") or 500)
    title = article["title"]
    hook = article["hook"] or article["description"] or ""
    second = article["hook_sentences"][1] if len(article["hook_sentences"]) > 1 else ""
    takeaways = article["takeaways"]
    numbers = article["numbers"]
    emo = _emoji(cfg, ["💶", "📌", "🔍"])
    link_line = f"{url}" if link_pos != "none" else ""
    reserve = len(link_line) + len(tags_txt) + 8

    if angle == "thread" and ((cfg.get("text") or {}).get("thread") or {}).get("supported"):
        return _compose_thread(article, cfg, url, tags_txt, max_chars)

    if angle == "zahl" and numbers:
        head = f"{numbers[0]} – {trim(hook, _budget(cfg, reserve + len(numbers[0]) + 40))}"
        body = trim(second, _budget(cfg, reserve + len(head) + 20)) if second else ""
    elif angle == "takeaway" and (takeaways or len(article["hook_sentences"]) > 1):
        head = title
        items = [trim(t, 96) for t in bullets_of(article, 3, 96)]
        body = "\n".join(f"{i + 1}️⃣ {t}" if cfg.get("text", {}).get("emoji_max", 0) >= 3
                         else f"{i + 1}) {t}" for i, t in enumerate(items))
    elif angle == "frage":
        q = article["faq_question"] or f"{_head_core(article)}?"
        a = article["faq_answer"] or trim(hook, 170)
        head = f"{q}"
        body = trim(a, _budget(cfg, reserve + len(head) + 10))
    elif angle == "mythos":
        myth = MYTHS.get(article["pillar"] or "", GENERIC_MYTH)
        fact = trim(hook, _budget(cfg, reserve + len(myth) + 60))
        head = f"Mythos: „{myth}“"
        body = f"Fakt: {fact}"
    elif angle == "zitat":
        claim = trim(hook, _budget(cfg, reserve + 30))
        head = f"„{claim}“"
        body = trim(second, _budget(cfg, reserve + len(head) + 10)) if second else ""
    elif angle == "vergleich" and (" oder " in title.lower() or ":" in title):
        pair = _pair_of(title)
        head = f"{pair[0]} oder {pair[1]}?"
        body = trim(second or hook, _budget(cfg, reserve + len(head) + 10))
    else:  # nutzen (Default)
        head = f"{emo} {title}".strip()
        body = trim(hook, _budget(cfg, reserve + len(head) + 10))

    parts = [p for p in [head, body, link_line] if p]
    if tags_txt:
        parts.append(tags_txt)
    text = "\n\n".join(parts)
    if len(text) > max_chars:
        text = _shrink(parts, max_chars, keep=(link_line, tags_txt))
    return {"text": text, "headline": title}


def _compose_thread(article, cfg, url, tags_txt, max_chars):
    """4–6 Teile: Aufhänger → 2–4 Punkte → Abschluss mit Link."""
    hook_parts = article["hook_sentences"] or [article["hook"]]
    takeaways = bullets_of(article, 3, 200) or hook_parts[1:]
    head = f"{article['title']}\n\n{trim(hook_parts[0], 200)}"
    parts = [trim(head, max_chars - 20)]
    for t in takeaways[:3]:
        parts.append(trim(clean_md(t), max_chars - 20))
    tail = f"Alle Rechenwege, Fristen und Fallen im Artikel:\n{url}"
    if tags_txt:
        tail = f"{tail}\n\n{tags_txt}"
    parts.append(trim(tail, max_chars - 10))
    limit = int(((cfg.get("text") or {}).get("thread") or {}).get("max_parts") or 5)
    return {"text": parts[0], "thread": parts[:limit], "headline": article["title"]}


def _pair_of(title: str) -> tuple[str, str]:
    low = title.lower()
    if " oder " in low:
        a, b = re.split(r"(?i)\s+oder\s+", title, maxsplit=1)
        return a.strip(" :"), b.strip(" :.?")
    if ":" in title:
        a, b = title.split(":", 1)
        return a.strip(), b.strip(" .?")
    return title.strip(), "die Alternative"


def _head_core(article: dict) -> str:
    title = article["title"]
    if ":" in title:
        return title.split(":", 1)[0].strip()
    return trim(title, 60).rstrip(" .")


def _shrink(parts: list[str], max_chars: int, keep: tuple) -> str:
    """Schrumpft einen Beitrag, ohne Link und Hashtags anzutasten.

    Struktur bleibt erhalten: es wird immer der längste frei kürzbare
    Teil gestaucht, bis das Budget passt – Aufzählungen überleben.
    """
    protected = [p for p in keep if p]
    flexible = [p for p in parts if p and p not in protected]
    protected_len = sum(len(p) + 2 for p in protected)
    room = max_chars - protected_len

    def joined(flex: list[str]) -> str:
        return "\n\n".join(x for x in flex if x)

    text = joined(flexible)
    guard = 0
    while len(text) > room and flexible and guard < 24:
        guard += 1
        idx = max(range(len(flexible)), key=lambda i: len(flexible[i]))
        part = flexible[idx]
        target = max(40, len(part) - max(20, len(text) - room + 2))
        if target >= len(part):
            target = max(40, len(part) - 20)
        if target < 40:
            flexible.pop(idx)
        else:
            flexible[idx] = trim(part, target)
        text = joined(flexible)
    out = flexible + protected
    return "\n\n".join(p for p in out if p)


# --- business (LinkedIn, Facebook) ------------------------------------------
def _compose_business(article, cfg, angle, url, tags, tags_txt, link_pos):
    max_chars = int((cfg.get("text") or {}).get("max_chars") or 2900)
    soft = int((cfg.get("text") or {}).get("soft_max_chars") or max_chars)
    title = article["title"]
    hook = article["hook"] or article["description"] or ""
    sentences_ = article["hook_sentences"]
    takeaways = article["takeaways"]

    if angle == "zahl" and article["numbers"]:
        if re.search(r"\d", article["hook"] or ""):
            opener = trim(article["hook"], 150)      # die Zahl steht schon drin
        else:
            opener = (f"{article['numbers'][0]} – darum geht es bei "
                      f"„{_head_core(article)}“.")
    elif angle == "frage":
        opener = (article["faq_question"] or f"{_head_core(article)}?").rstrip()
    elif angle == "vergleich":
        a, b = _pair_of(title)
        opener = f"{a} oder {b}? Die Antwort hängt an einer Zahl."
    else:
        opener = trim(hook, 150)

    body_parts = sentences_[1:3] or sentences_[:1]
    body = " ".join(body_parts)
    body = trim(body, max(240, int(soft * 0.45)))

    block = ""
    bullets = bullets_of(article, 3, 130)
    if bullets:
        block = "Was wirklich zählt:\n" + "\n".join(f"• {t}" for t in bullets)

    question = QUESTIONS.get(article["pillar"] or "", GENERIC_QUESTION)
    closer = f"Frage an dich: {question}"

    link_line = url if link_pos == "end" else ""
    parts = [opener, "", body, "", block, "", closer]
    if link_line:
        parts.append(link_line)
    # Hashtags bleiben IMMER im Beitrag: Bei `first_comment` wandert nur der
    # LINK in den Kommentar (LinkedIn-Reichweitenstandard), die Tags gehören
    # ans Textende. Vor der Reparatur #716 fielen sie dort ersatzlos weg –
    # L4 „zu wenige Hashtags" blockierte damit jeden LinkedIn-Beitrag.
    if tags_txt:
        parts.append(tags_txt)
    text = "\n".join(p for p in parts if p is not None).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)

    if len(text) > soft:
        # Zuerst den Body kürzen, dann den Takeaway-Block – der Hook bleibt.
        body = trim(body, max(120, len(body) - (len(text) - soft) - 3))
        parts = [opener, "", body, "", block, "", closer]
        if link_line:
            parts.append(link_line)
        if tags_txt:
            parts.append(tags_txt)
        text = re.sub(r"\n{3,}", "\n\n", "\n".join(p for p in parts if p is not None).strip())
    if len(text) > max_chars:
        text = text[:max_chars].rstrip()

    return {
        "text": text,
        "headline": title,
        "comment": f"Alle Details, Rechenbeispiele und Quellen: {url}" if link_pos == "first_comment" else "",
    }


# --- visual (Instagram) ------------------------------------------------------
# Satz, in dem der Artikel selbst eine verbreitete Annahme korrigiert
# („erhöht weder … noch …“, „nicht automatisch“). Daraus entsteht der Winkel
# `mythos` aus dem Artikel – statt einer Pillar-Behauptung, die zum konkreten
# Thema gar nicht passen muss.
KORREKTUR_RX = re.compile(
    r"\b(?:weder|nicht automatisch|kein\w* automatisch|irrtum|mythos|"
    r"entgegen|anders als (?:viele|oft))\b", re.I)
VISUAL_OPENER_MAX = 125    # Instagram zeigt ~125 Zeichen vor „mehr“
VISUAL_BODY_MAX = 380      # Caption bleibt unter dem soft_max des Kanals
VISUAL_PUNKT_MAX = 180     # ganze Takeaway-Sätze statt abgerissener „…“


def _visual_winkel(article: dict, angle: str) -> tuple[str, str]:
    """(Erste Zeile, Körper) der Instagram-Caption – je Winkel eigenständig.

    REPARATUR 14.10.2026 (#716-Familie): Die Caption war winkelBLIND – alle
    sechs Instagram-Winkel lieferten Wort für Wort denselben Text, nur die
    (nirgends gesendeten) Folien unterschieden sich. Ein einziges Falschurteil
    des Gates sperrte damit den Artikel in JEDEM Winkel; das Nachrücken auf
    einen anderen Winkel, das den Kanal vor dem Verhungern schützt, lief ins
    Leere. Jetzt trägt jeder Winkel einen eigenen Zugang zum Thema – und nur
    Material, das im Artikel steht (Kurzantwort, Takeaways, FAQ, Zahlen aus
    Kurzantwort/Beschreibung/Titel). Fehlt einem Winkel sein Material, fällt
    er ehrlich auf den Nutzen-Zugang zurück, statt etwas zu erfinden.
    """
    hook = article.get("hook") or article.get("description") or ""
    saetze = list(article.get("hook_sentences") or ([hook] if hook else []))
    numbers = article.get("numbers") or []

    def koerper(teile: list[str]) -> str:
        return trim(" ".join(t for t in teile if t), VISUAL_BODY_MAX)

    if angle == "zahl" and numbers:
        # Steht die Zahl in einem Folgesatz, rückt dieser Satz nach vorn. Steht
        # sie schon im Aufhänger, wäre das der Nutzen-Text – dann führt die
        # Zahl selbst (sie stammt aus Kurzantwort/Beschreibung/Titel, L9-belegt).
        mit_zahl = next((x for x in saetze[1:] if re.search(r"\d", x)), "")
        if mit_zahl:
            rest = [x for x in saetze if x != mit_zahl][:2]
            return trim(mit_zahl, VISUAL_OPENER_MAX), koerper(rest)
        return (trim(f"{numbers[0]} – darum geht es bei „{_head_core(article)}“.",
                     VISUAL_OPENER_MAX), koerper(saetze[:2]))

    if angle in ("takeaway", "karussell"):
        # `karussell` sendet (Stand Adapter) ein Einzelbild – die Caption
        # verspricht deshalb keine Folien, sondern liefert die Merkliste, die
        # man speichert. Ohne echte Takeaways gibt es keine Merkliste.
        limit = 4 if angle == "karussell" else 3
        punkte = bullets_of(article, limit, VISUAL_PUNKT_MAX)
        if angle == "karussell" and not article.get("takeaways"):
            punkte = []
        if punkte:
            if angle == "karussell":
                liste = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(punkte))
                return trim(hook, VISUAL_OPENER_MAX), f"Zum Speichern:\n{liste}"
            liste = "\n".join(f"• {t}" for t in punkte)
            return trim(hook, VISUAL_OPENER_MAX), f"Das Wichtigste in Kürze:\n{liste}"

    if angle == "frage":
        frage = (article.get("faq_question") or f"{_head_core(article)}?").strip()
        antwort = article.get("faq_answer") or ""
        return (trim(frage, VISUAL_OPENER_MAX),
                koerper([antwort] if antwort else saetze[:2]))

    if angle == "mythos":
        idx = next((i for i, x in enumerate(saetze) if KORREKTUR_RX.search(x)), -1)
        if idx >= 0:
            korrektur = saetze[idx]
            weiter = saetze[idx + 1:idx + 2]    # der Satz, der die Korrektur fortführt
            return (trim(f"Was bei „{_head_core(article)}“ oft falsch eingeschätzt wird:",
                         VISUAL_OPENER_MAX), koerper([korrektur, *weiter]))
        myth = MYTHS.get(article.get("pillar") or "", GENERIC_MYTH)
        return (trim(f"Mythos: „{myth}“", VISUAL_OPENER_MAX),
                koerper([f"Fakt: {hook}"]) if hook else "")

    # nutzen (Default) – und ehrlicher Rückfall jedes Winkels ohne Material.
    return trim(hook, VISUAL_OPENER_MAX), koerper(saetze[1:3])


def _compose_visual(article, cfg, angle, url, tags, tags_txt, link_pos):
    hook = article["hook"] or article["description"] or ""
    takeaways = article["takeaways"]
    numbers = article["numbers"]
    # Die Rechenwege-Formel nur, wo der Artikel tatsächlich rechnet – ein
    # Technik-Ratgeber ohne eine einzige Zahl verspricht sonst etwas, das er
    # nicht hält.
    cta = ("Mehr Rechenwege findest du über den Link in der Bio." if numbers
           else "Den ganzen Ratgeber findest du über den Link in der Bio.")
    slides: list[str] = [article["title"]]

    if angle == "karussell" and takeaways:
        slides += bullets_of(article, 4, 120)
        slides.append("Link in der Bio")
    elif numbers:
        slides += bullets_of(article, 3, 120) or [trim(hook, 120)]
        slides.append(f"{numbers[0]} Sparpotenzial")
    else:
        slides += bullets_of(article, 3, 120) or [trim(hook, 120)]
        slides.append("Link in der Bio")

    opener, body = _visual_winkel(article, angle)
    parts = [opener, "", body, "", cta]
    if tags_txt:
        parts.append(tags_txt)
    text = "\n\n".join(p for p in parts if p)
    max_chars = int((cfg.get("text") or {}).get("max_chars") or 2200)
    if len(text) > max_chars:
        text = _shrink(parts, max_chars, keep=(tags_txt,))
    return {"text": text, "headline": article["title"], "slides": slides}


# --- messenger (Telegram) ----------------------------------------------------
def _compose_messenger(article, cfg, angle, url, tags, tags_txt, link_pos):
    hook = article["hook"] or article["description"] or ""
    takeaways = article["takeaways"]
    head = f"<b>{article['title']}</b>"
    body = trim(" ".join(article["hook_sentences"][:2]), 420)
    block = "\n".join(f"• {t}" for t in bullets_of(article, 3, 120))
    link_line = f'<a href="{url}">Ganzen Artikel lesen</a>' if link_pos != "none" else ""
    parts = [head, "", body]
    if block:
        parts += ["", block]
    if link_line:
        parts += ["", link_line]
    if tags_txt:
        parts += ["", tags_txt]
    text = "\n".join(parts)
    max_chars = int((cfg.get("text") or {}).get("max_chars") or 4096)
    if len(text) > max_chars:
        text = _shrink(parts, max_chars, keep=(link_line, tags_txt))
    return {"text": text, "headline": article["title"]}


# --- community (Reddit) ------------------------------------------------------
def _compose_community(article, cfg, angle, url, tags, tags_txt, link_pos):
    """Reddit: Erfahrungsbericht, keine Werbesprache, kein Hashtag."""
    hook = article["hook"] or article["description"] or ""
    takeaways = article["takeaways"]
    title = f"{_head_core(article)} – meine Erfahrung mit echten Zahlen"
    body_parts = [trim(hook, 600)]
    reddit_bullets = bullets_of(article, 4, 200)
    if reddit_bullets:
        body_parts.append("\n".join(f"* {t}" for t in reddit_bullets))
    body_parts.append(
        "Ich schreibe die Ratgeber dazu selbst und habe die Zahlen nachgerechnet – "
        "wenn ihr andere Werte aus der Praxis habt, korrigiert mich gern. "
        f"Zusammengefasst hier: {url}")
    text = "\n\n".join(p for p in body_parts if p)
    max_chars = int((cfg.get("text") or {}).get("max_chars") or 40000)
    return {"text": text[:max_chars], "headline": trim(title, int(
        (cfg.get("text") or {}).get("title_max_chars") or 300))}


# --- pin (Pinterest) ---------------------------------------------------------
def _compose_pin(article, cfg, angle, url, tags, tags_txt, link_pos):
    """Pinterest denkt wie eine Suchmaschine: Keyword vorn, Nutzen, CTA."""
    title = article.get("pin_title") or article["title"]
    title = trim(title, int((cfg.get("text") or {}).get("title_max_chars") or 100))
    hook = article["hook"] or article["description"] or ""
    numbers = article["numbers"]
    lead = f"{numbers[0]} – " if numbers and angle == "zahl" else ""
    body = trim(f"{lead}{hook}", 260)
    cta = "Jetzt die Spartipps auf FranksFinanzcheck lesen!"
    parts = [body, cta]
    # `destination` (Playbook-Standard für Pinterest): Die Artikel-URL reist
    # als Ziel-Link des Pins, nicht durch die Beschreibung. Nur bei
    # `end`/`first_comment` steht sie zusätzlich im Text.
    if link_pos == "end" and url:
        parts.append(url)
    if tags_txt:
        parts.append(tags_txt)
    text = " ".join(parts)
    max_chars = int((cfg.get("text") or {}).get("max_chars") or 500)
    if len(text) > max_chars:
        text = _shrink(parts, max_chars, keep=(tags_txt, url if link_pos == "end" else ""))
    return {"text": text, "headline": title}


# ----------------------------------------------------------------- KI-Politur
SYSTEM_PROMPT = (
    "Du bist Social-Media-Redakteur der Premium-Agentur für die Marke FranksFinanzcheck "
    "(unabhängige Spar-Ratgeber für Privathaushalte in Deutschland). Du schreibst auf "
    "Deutsch, in der Du-Form, psychologisch stark, ehrlich und zahlengetrieben – ohne "
    "platten Verkaufsdruck, aber mit klarem Fokus auf Conversion (BOFU). "
    "Zeige dem Leser das Problem auf (Kostenfalle, Deadline), liefere ein konkretes Detail "
    "und rufe dann zur Lösung (dem Link) auf."
)


def polish(pkg: dict, channel_cfg: dict, meta: dict) -> str:
    """Poliert den Entwurf mit einem Gratis-LLM. Scheitert irgendetwas,
    wird '' zurückgegeben – dann gilt der deterministische Entwurf."""
    llm_cfg = (meta or {}).get("llm") or {}
    mode = (os.environ.get("SOCIAL_COPY_MODE") or llm_cfg.get("mode") or "auto").lower()
    if mode == "off":
        return ""
    try:
        import llm_client
    except Exception:  # noqa: BLE001
        return ""

    providers = [p for p in (llm_cfg.get("providers") or ["groq", "gemini"])
                 if llm_client.available(p)]
    if not providers:
        return ""

    text_cfg = channel_cfg.get("text") or {}
    hashtags = pkg.get("hashtags") or []
    rules = "\n".join([
        f"- Kanal: {channel_cfg.get('label')} ({channel_cfg.get('kind')})",
        f"- maximal {text_cfg.get('max_chars')} Zeichen (hart)",
        f"- {len(hashtags)} Hashtags, die du übernimmst: {' '.join('#' + h for h in hashtags)}",
        f"- maximal {text_cfg.get('emoji_max', 0)} Emojis",
        f"- Ton: {str(channel_cfg.get('tone') or '').strip()}",
        f"- Winkel: {pkg.get('angle')}",
    ])
    link_rule = ("- Der Link muss UNVERÄNDERT enthalten bleiben: " + pkg.get("url", "")
                 if (text_cfg.get("link_position") or "end") != "none"
                 else "- Kein Link im Text (dieser Kanal klickt nicht).")
    draft = pkg.get("text") or ""
    prompt = (
        "Schreibe den folgenden Entwurf für den genannten Kanal neu. "
        "Erfinde KEINE neuen Zahlen, Fakten oder Versprechen – alle Zahlen "
        "und der Link kommen unverändert aus dem Entwurf.\n\n"
        f"KANAL-REGELN:\n{rules}\n{link_rule}\n"
        "- Keine Hashtags erfinden, keine Emojis häufen, keine Werbeversprechen.\n"
        "- Antworte AUSSCHLIESSLICH mit dem fertigen Beitragstext – ohne "
        "Anführungszeichen, ohne Erklärung, ohne Markdown-Codeblock.\n\n"
        f"ENTWURF:\n{draft}\n\n"
        f"ARTIKEL-MATERIAL (Kontext, nur verwenden, was im Entwurf steht):\n"
        f"Titel: {(pkg.get('article') or {}).get('title', '')}\n"
        f"Kernpunkte: {' | '.join((pkg.get('article') or {}).get('takeaways', [])[:4])}"
    )
    for provider in providers:
        try:
            out = llm_client.chat(
                provider,
                prompt,
                system=SYSTEM_PROMPT,
                temperature=float(llm_cfg.get("temperature") or 0.5),
                max_tokens=int(llm_cfg.get("max_tokens") or 900),
                timeout=90,
                attempts=2,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"    ⚠ KI-Politur ({provider}) fehlgeschlagen: {exc}")
            continue
        cleaned = _clean_llm_output(out or "")
        if _polish_is_valid(cleaned, pkg, channel_cfg):
            return cleaned
        print(f"    ⚠ KI-Fassung verworfen (Regelverstoß) – Entwurf bleibt.")
    return ""


def _clean_llm_output(raw: str) -> str:
    text = (raw or "").strip()
    text = re.sub(r"^```(?:[a-zA-Z]*)\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    text = text.strip().strip('"').strip("'").strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _polish_is_valid(text: str, pkg: dict, channel_cfg: dict) -> bool:
    """Harte Abnahme der KI-Fassung – sonst gilt der Entwurf."""
    text_cfg = channel_cfg.get("text") or {}
    if not text or len(text) < int(((pkg.get("meta") or {}).get("min_chars")) or 60) and len(text) < 60:
        return False
    if len(text) > int(text_cfg.get("max_chars") or 500):
        return False
    link_pos = text_cfg.get("link_position") or "end"
    if link_pos != "none" and (pkg.get("url") or "") not in text:
        return False
    if link_pos == "none" and "http" in text:
        return False
    # Keine erfundenen Zahlen: jede Zahl der KI muss im Material vorkommen.
    material = " ".join([
        (pkg.get("article") or {}).get("kurzantwort") or "",
        (pkg.get("article") or {}).get("description") or "",
        (pkg.get("article") or {}).get("title") or "",
        " ".join((pkg.get("article") or {}).get("takeaways") or []),
        (pkg.get("text") or ""),
    ])
    allowed = set(re.findall(r"\d[\d.,]*", material))
    for num in re.findall(r"\d[\d.,]*", text):
        if num not in allowed and num not in material:
            return False
    # Hashtags müssen erhalten bleiben
    for tag in pkg.get("hashtags") or []:
        if f"#{tag}".lower() not in text.lower():
            return False
    return True


# ---------------------------------------------------------------------- CLI
if __name__ == "__main__":  # pragma: no cover – Handwerkzeug
    import json as _json

    argv = sys.argv[1:]
    slug = next((a for a in argv if not a.startswith("-")), "")
    channel = "mastodon"
    if "--channel" in argv:
        channel = argv[argv.index("--channel") + 1]
    angle = "nutzen"
    if "--angle" in argv:
        angle = argv[argv.index("--angle") + 1]
    import social_channels

    cfg = social_channels.load_config()
    meta = social_channels.meta_of(cfg)
    pool = article_pool()
    art = next((a for a in pool if a["slug"] == slug), None) or (pool[-1] if pool else None)
    if not art:
        sys.exit("Kein Artikel gefunden.")
    for ang in ([angle] if "--angle" in argv else ["nutzen", "zahl", "takeaway", "frage",
                                                   "mythos", "zitat", "vergleich", "thread"]):
        for cid in ([channel] if "--channel" in argv else list(social_channels.channel_map(cfg))):
            ch = social_channels.channel_map(cfg).get(cid) or {}
            package = compose(art, cid, ch, ang, meta, use_llm=False)
            print("=" * 72)
            print(f"{cid} · {ang} · {len(package['text'])} Zeichen "
                  f"(Limit {((ch.get('text') or {}).get('max_chars'))})")
            print("-" * 72)
            print(package["text"])
