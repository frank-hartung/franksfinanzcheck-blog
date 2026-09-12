#!/usr/bin/env python3
# ============================================================
#  SOCIAL-GATE – hartes Freigabe-Gate (fail-closed)
#  ------------------------------------------------------------
#  Kein Beitrag geht raus, der hier durchfällt. Das Gate prüft für
#  JEDEN Kanal dessen eigene Kriterien plus die redaktionellen und
#  rechtlichen Mindeststandards des Blogs:
#
#    L1 Zeichenlänge (Plattform-Zählung, inkl. Link-Gewichtung)
#    L2 Link-Pflicht & Link-Hygiene (kanonisch, NIE ein Affiliate-/go/-Link)
#    L3 Recht & Werbekennzeichnung (keine unzulässigen Versprechen)
#    L4 Hashtags (Anzahl, Länge, Schreibweise)
#    L5 Emoji-Budget des Kanals
#    L6 Sprach-Check (deutsch – keine englischen Satzleichen)
#    L7 Shouting / Spam-Muster (!!!!!, ALLES GROSS, Link-Shortener)
#    L8 Duplikat-Schutz (Ähnlichkeit zu früheren Postings desselben Kanals)
#    L9 Fakten-Treue (keine Zahl, die nicht im Artikel steht)
#   L10 Bildpflicht, wo der Kanal sie verlangt
#
#  Ergebnis: (freigabe: bool, verstöße: list[str], kennzahlen: dict)
#  Das Gate ist deterministisch und offline lauffähig – es braucht
#  weder Netz noch Token.
# ============================================================
from __future__ import annotations

import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BLOG_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import social_copywriter as copy  # noqa: E402

EMOJI_RX = re.compile(
    "[" "\U0001F300-\U0001FAFF" "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF" "\U00002190-\U000021FF" "\U00002B00-\U00002BFF" "]"
)
TAG_RX = re.compile(r"(?<!\w)#([A-Za-z0-9ÄÖÜäöüß_]+)")
NUM_RX = re.compile(r"\d[\d.,]*")
ENUM_RX = re.compile(r"(?m)^\s*(?:\d+[.)]|[-*•])\s+")
URL_RX = re.compile(r"https?://\S+")

GERMAN_MARKERS = ["der", "die", "das", "und", "nicht", "für", "mit", "ein", "eine",
                  "ist", "sind", "du", "dein", "auf", "im", "am", "zum", "wird",
                  "oder", "dass", "so", "mehr", "kann", "kannst", "sparen"]

SHORTENER_RX = re.compile(r"(bit\.ly|tinyurl|t\.co|goo\.gl|is\.gd|ow\.ly|buff\.ly)", re.I)


def _strip_enum(text: str) -> str:
    """Entfernt Aufzählungs-Marker, damit „1)" nicht als Zahl gilt."""
    return ENUM_RX.sub("", text or "")


def _words(text: str) -> set[str]:
    clean = URL_RX.sub(" ", (text or "").lower())
    clean = TAG_RX.sub(" ", clean)
    return {w for w in re.findall(r"[a-zäöüßA-ZÄÖÜ]{3,}", clean)}


def similarity(a: str, b: str) -> float:
    """Jaccard-Ähnlichkeit der Wortmengen (0–1)."""
    wa, wb = _words(a), _words(b)
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def count_emoji(text: str) -> int:
    return len(EMOJI_RX.findall(text or ""))


def shouting_ratio(text: str) -> float:
    words = re.findall(r"[A-ZÄÖÜ]{3,}", text or "")
    all_words = re.findall(r"\b\w{3,}\b", text or "")
    if not all_words:
        return 0.0
    return len(words) / max(1, len(all_words))


def check(pkg: dict, channel_cfg: dict, meta: dict,
          history: list[dict] | None = None) -> tuple[bool, list[str], dict]:
    """Prüft ein Beitrags-Paket. (freigabe, verstöße, kennzahlen)."""
    history = history or []
    violations: list[str] = []
    text = pkg.get("text") or ""
    comment = pkg.get("comment") or ""
    url = pkg.get("url") or ""
    article = pkg.get("article") or {}
    text_cfg = (channel_cfg or {}).get("text") or {}
    media_cfg = (channel_cfg or {}).get("media") or {}
    gate_cfg = (meta or {}).get("gate") or {}
    link_cfg = (meta or {}).get("link") or {}

    max_chars = int(text_cfg.get("max_chars") or 500)
    weight = int(text_cfg.get("link_weight") or 0)
    link_pos = text_cfg.get("link_position") or "end"
    full = f"{text}\n{comment}".strip()
    metrics = {
        "chars": copy.effective_length(text, url, weight),
        "max_chars": max_chars,
        "hashtags": len(TAG_RX.findall(text)),
        "emoji": count_emoji(text),
        "similarity": 0.0,
    }

    # -- L1 Länge -----------------------------------------------------------
    if metrics["chars"] > max_chars:
        violations.append(f"L1 zu lang: {metrics['chars']} > {max_chars} Zeichen")
    min_chars = int(gate_cfg.get("min_chars") or 0)
    if len(text.strip()) < min_chars:
        violations.append(f"L1 zu kurz: {len(text.strip())} < {min_chars} Zeichen")

    # -- L2 Link ------------------------------------------------------------
    for pattern in (link_cfg.get("forbid") or []):
        if pattern.lower() in full.lower():
            violations.append(f"L2 unzulässiger Link/Shortener: {pattern}")
    if SHORTENER_RX.search(full):
        violations.append("L2 Link-Shortener unzulässig")
    if text_cfg.get("link_required"):
        where = comment if link_pos == "first_comment" else text
        if url and url not in where:
            violations.append("L2 kanonischer Artikel-Link fehlt")
        if url and not url.startswith(str((meta or {}).get("base_url") or "https://").rstrip("/")):
            violations.append("L2 Link ist keine kanonische Blog-URL")
    if link_pos == "none" and "http" in text:
        violations.append("L2 dieser Kanal erlaubt keine Links im Text")

    # -- L3 Recht & Versprechen --------------------------------------------
    for term in (gate_cfg.get("blocked_terms") or []):
        if term.lower() in full.lower():
            violations.append(f"L3 unzulässiges Versprechen: „{term}“")
    for phrase in (gate_cfg.get("forbidden_phrases") or []):
        if phrase.lower() in full.lower():
            violations.append(f"L3 Phrase gesperrt: „{phrase}“")

    # -- L4 Hashtags --------------------------------------------------------
    tags = TAG_RX.findall(text)
    ht_cfg = text_cfg.get("hashtags") or {}
    ht_max = int(ht_cfg.get("max") or 0)
    ht_min = int(ht_cfg.get("min") or 0)
    ht_len = int(ht_cfg.get("max_len") or 24)
    if ht_max and len(tags) > ht_max:
        violations.append(f"L4 zu viele Hashtags: {len(tags)} > {ht_max}")
    if ht_min and len(tags) < ht_min:
        violations.append(f"L4 zu wenige Hashtags: {len(tags)} < {ht_min}")
    for tag in tags:
        if len(tag) > ht_len:
            violations.append(f"L4 Hashtag zu lang: #{tag} ({len(tag)} > {ht_len})")

    # -- L5 Emoji -----------------------------------------------------------
    emo_max = int(text_cfg.get("emoji_max") or 0)
    if count_emoji(text) > emo_max:
        violations.append(f"L5 zu viele Emojis: {count_emoji(text)} > {emo_max}")

    # -- L6 Sprache ---------------------------------------------------------
    low = text.lower()
    if not any(f" {w} " in f" {low} " for w in GERMAN_MARKERS):
        violations.append("L6 Text wirkt nicht deutschsprachig")

    # -- L7 Shouting / Spam -------------------------------------------------
    if "!!!" in text or "???" in text:
        violations.append("L7 Ausrufezeichen-/Fragezeichen-Ketten")
    ratio = shouting_ratio(text)
    if ratio > float(gate_cfg.get("max_shouting_ratio") or 0.12):
        violations.append(f"L7 zu viele Großbuchstaben ({ratio:.0%})")
    if len(URL_RX.findall(text)) > 2:
        violations.append("L7 mehr als zwei Links im Beitrag")

    # -- L8 Duplikat-Schutz -------------------------------------------------
    threshold = float((meta or {}).get("similarity_threshold") or 0.72)
    worst = 0.0
    for entry in history:
        if (entry or {}).get("channel") != pkg.get("channel"):
            continue
        sim = similarity(text, (entry or {}).get("text") or "")
        worst = max(worst, sim)
        if sim >= threshold:
            violations.append(
                f"L8 Duplikat-Verdacht: {sim:.0%} Ähnlichkeit zu einem Posting "
                f"vom {(entry or {}).get('posted_at', '?')[:10]}")
            break
    metrics["similarity"] = round(worst, 3)

    # -- L9 Fakten-Treue ----------------------------------------------------
    material = " ".join([
        article.get("kurzantwort") or "", article.get("description") or "",
        article.get("title") or "", " ".join(article.get("takeaways") or []),
        " ".join(article.get("keywords") or []), " ".join(article.get("tags") or []),
    ])
    material_nums = set(NUM_RX.findall(material))
    body_nums = set(NUM_RX.findall(_strip_enum(text)))
    invented = [n for n in body_nums if n not in material_nums and n not in url]
    if invented:
        violations.append(f"L9 Zahl ohne Beleg im Artikel: {', '.join(sorted(invented)[:4])}")

    # -- L10 Bildpflicht ----------------------------------------------------
    if media_cfg.get("required") and not (pkg.get("media_url") or pkg.get("media_path")):
        violations.append("L10 dieser Kanal verlangt ein Bild, es liegt keines vor")

    return (not violations), violations, metrics
