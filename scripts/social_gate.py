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
#
#  REPARATUR 02.10.2026 (PR #530, CI „gate“/„regression“ rot sobald der
#  Urlaubskasse-Artikel der jüngste Pool-Eintrag wurde):
#  Die Regel war Flexions-BLIND: exakter Wort-Vorkommnis-Abgleich
#  (`" die " in text`). Echter deutscher Text ohne Liste der bloßen
#  Grundformen – „Du willst deine Urlaubskasse aufbessern?" (deine,
#  ohne, willst) – fiel mit null Treffern durch: FALSCH-NEGATIV in
#  einer fail-closed-Wache, und das sauberste mögliche Beispiel
#  (Titel + Hook des aktuellen Live-Artikels). Die Heuristik bleibt
#  absichtlich schwach (sie erkennt deutsche Funktionswörter, sie
#  beweist keine Grammatik), wird aber robust: Treffer jetzt auch über
#  die häufigsten Flexionsendungen (dein+e/n/r/s/em/en …) und eine
#  ergänzte Funktionswort-Liste (ohne, vom, beim, über …). Gegenprobe
#  bleibt Pflicht: rein englischer Text muss weiterhin blockieren.
#    L7 Shouting / Spam-Muster (!!!!!, ALLES GROSS, Link-Shortener)
#    L8 Duplikat-Schutz (Ähnlichkeit zu früheren Postings desselben Kanals)
#    L9 Fakten-Treue (keine Zahl, die nicht im Artikel steht)
#   L10 Bildpflicht, wo der Kanal sie verlangt
#
#  REPARATUR 12.10.2026 (Meldung #716, Kanal Mastodon 48 h stumm):
#  L9 prüfte den ROHEN Text inklusive Hashtag-Block. Der Texter baut aus dem
#  Keyword „50-30-20-Regel" das Hashtag „#503020Regel" – die Ziffernfolge
#  503020 steht so in keinem Artikel, wohl aber die drei Einzelzahlen
#  50 / 30 / 20. Die Regel meldete „L9 Zahl ohne Beleg im Artikel: 503020"
#  und blockierte den Ratgeber in JEDEM Winkel dauerhaft. Ein Falschurteil
#  in einer fail-closed-Wache ist genauso schwerwiegend wie ein übersehener
#  Verstoß: Es kostet Inhalt, blockiert Slots und lässt den Kanal verhungern.
#  Seither gilt: Der Fließtext wird ohne Hashtag-Block geprüft, und jedes
#  Hashtag einzeln – seine Zahlen müssen belegbar sein, entweder direkt oder
#  als Verkettung belegter Zahlen (50+30+20 → 503020). Erfundene Zahlen
#  blockieren weiterhin, im Text wie im Hashtag. Tausendertrenner zählen
#  als Schreibweise („2.800" belegt „2800").
#
#  REPARATUR 14.10.2026 (#716-Familie, Kanal Instagram – Ratgeber
#  „DNS-Server wechseln“ in KEINEM Winkel sendbar, CI `regression` rot):
#  L7 zählte jede Großbuchstabenfolge als Geschrei. Der Fließtext eines
#  Technik-Ratgebers lebt aber von Fachkürzeln – „DNS over HTTPS“, „DNS over
#  TLS“ – und kippte mit 13 % über die 12-%-Schwelle. Dieselbe Fehlerklasse
#  wie die beiden Reparaturen vom 12.10. (Hashtag-Zahlen in L9, CamelCase-Tags
#  in L7): ein Falschurteil in einer fail-closed-Wache, das ausgerechnet die
#  präzisesten Texte aussperrt. Seither unterscheidet L7 FACHKÜRZEL von
#  GESCHREI – nach demselben Prinzip wie L9 („Zahl mit Beleg“):
#    · Fachkürzel ist, was der Haus-Kanon (`tag_casing`: Akronyme, Marken,
#      Einheiten) in Versalien führt ODER was der Artikel selbst in Versalien
#      schreibt (Titel, Kurzantwort, Beschreibung, Takeaways, Keywords, Tags).
#    · Nie Fachkürzel: Schreiwörter (GRATIS, JETZT, SOFORT … – Kanon in
#      `meta.gate.schrei_woerter`) und gewöhnliche Wörter, die der Artikel
#      selbst klein oder als Nomen schreibt („Jetzt“ im Artikel macht „JETZT“
#      im Beitrag nicht zum Kürzel). Länger als sechs Buchstaben ist kein
#      Kürzel, sondern ein geschrienes Wort – es sei denn, der Kanon führt es.
#  Geschrei bleibt Geschrei: Ein Satz in Versalien blockiert unverändert,
#  auch wenn er ein belegtes Kürzel enthält.
#
#  Ergebnis: (freigabe: bool, verstöße: list[str], kennzahlen: dict)
#  Das Gate ist deterministisch und offline lauffähig – es braucht
#  weder Netz noch Token.
# ============================================================
from __future__ import annotations

import os
import re
import sys
from collections.abc import Iterable

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BLOG_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import social_copywriter as copy  # noqa: E402
import tag_casing  # noqa: E402  – EIN Wortschatz-Kanon für Kürzel und Marken

# Härtung 2026-10 (py/overly-large-range, 2. Runde): Regionale Indikatoren
# (1F1E6–1F1FF) liegen vollständig im Symbol-/Emoji-Block – als EIGENE Range
# neben 1F300–1FAFF meldet der Scanner Überlappungsverdacht. Eine durchgehend
# kanonisierte Klassenliste (Pfeile, Symbole/Dingbats, Sterne/Ornamente,
# geschlossener Emoji-Block inkl. Flaggen) ist semantisch identisch.
EMOJI_RX = re.compile(
    "[" "\u2190-\u21FF" "\u2600-\u27BF" "\u2B00-\u2BFF" "\U0001F000-\U0001FAFF" "]"
)
TAG_RX = re.compile(r"(?<!\w)#([A-Za-z0-9ÄÖÜäöüß_]+)")
NUM_RX = re.compile(r"\d[\d.,]*")
ENUM_RX = re.compile(r"(?m)^\s*(?:\d+[.)]|[-*•])\s+")
URL_RX = re.compile(r"https?://\S+")

GERMAN_MARKERS = ["der", "die", "das", "und", "nicht", "für", "mit", "ein", "eine",
                  "ist", "sind", "du", "dein", "auf", "im", "am", "zum", "wird",
                  "oder", "dass", "so", "mehr", "kann", "kannst", "sparen",
                  # REPARATUR 02.10.2026 (s. Kopfkommentar L6): häufige
                  # Funktionswörter, die in Hooks alltäglich sind, deren
                  # bloßes Fehlen aber fälschlich „nicht deutsch“ meldete.
                  "ohne", "von", "auch", "wenn", "wie", "was", "nur", "noch",
                  "sehr", "jetzt", "hier", "hat", "haben", "sie", "wir",
                  "vom", "beim", "nach", "über"]

# Flexions-Endungen für die robuste L6-Erkennung: Marker als Wortanfang
# plus übliche deutsche Endung gilt als Treffer (dein+e, dein+en,
# dein+er, dein+s, dein+em, kann+en …). Bewusst konservativ: nur Marker
# mit ≥3 Zeichen und eine eng geführte Endungsliste, damit englische
# Wörter (z. B. „diet“ ≉ „die“) weiterhin durchfallen.
_FLEXION_ENDUNGEN = ("e", "en", "er", "es", "em", "n", "s", "st", "est", "ern", "et")
_GERMAN_TOKEN_RX = re.compile(r"[a-zäöüß]+", re.IGNORECASE)


def _german_hit(text: str) -> bool:
    """L6-Trefferheuristik: Grundwort-Abgleich ODER Marker+Flexion."""
    low = (text or "").lower()
    if any(f" {w} " in f" {low} " for w in GERMAN_MARKERS):
        return True
    for tok in _GERMAN_TOKEN_RX.findall(low):
        for w in GERMAN_MARKERS:
            if len(w) >= 3 and tok != w and tok.startswith(w):
                if tok[len(w):] in _FLEXION_ENDUNGEN:
                    return True
    return False

SHORTENER_RX = re.compile(r"(bit\.ly|tinyurl|t\.co|goo\.gl|is\.gd|ow\.ly|buff\.ly)", re.I)


def _strip_enum(text: str) -> str:
    """Entfernt Aufzählungs-Marker, damit „1)" nicht als Zahl gilt."""
    return ENUM_RX.sub("", text or "")


def _norm_zahl(token: str) -> str:
    """Ziffernfolge ohne Trennzeichen: „2.800" → „2800", „1.234,5" → „12345".

    Tausender- und Dezimaltrenner sind Schreibweise, nicht Inhalt. Ohne die
    Normalisierung galt „2800 €" als erfunden, obwohl der Artikel „2.800 €"
    schreibt – ein zweiter Falschurteils-Pfad derselben Regel.
    """
    return re.sub(r"[.,]", "", token or "")


def _zahl_zerlegbar(rest: str, pool: tuple[str, ...], memo: set[str]) -> bool:
    """True, wenn `rest` vollständig aus belegten Zahlen zusammengesetzt ist."""
    if not rest:
        return True
    if rest in memo:
        return False
    memo.add(rest)
    for zahl in pool:
        if rest.startswith(zahl) and _zahl_zerlegbar(rest[len(zahl):], pool, memo):
            return True
    return False


def zahl_belegt(zahl: str, belegte: Iterable[str]) -> bool:
    """Ist diese Zahl durch den Artikel gedeckt?

    Belegt ist eine Zahl, wenn sie wörtlich im Material steht ODER wenn sich
    ihre Ziffernfolge lückenlos aus belegten Zahlen zusammensetzt. Letzteres
    deckt Hashtags wie „#503020Regel" ab, die der Texter aus „50-30-20-Regel"
    bildet (Meldung #716). Die Zerlegung ist bewusst streng: Es bleibt nichts
    übrig, jede Teilzahl muss einzeln belegt sein.
    """
    ziel = _norm_zahl(zahl)
    if not ziel:
        return True
    # Deterministisch sortieren (erst Länge, dann lexikografisch): Die
    # Mengen-Reihenfolge hängt am String-Hash und wäre sonst je Prozess
    # anders – ein Gate muss aber reproduzierbar urteilen.
    pool = sorted({_norm_zahl(z) for z in belegte if _norm_zahl(z)},
                  key=lambda z: (-len(z), z))
    if ziel in pool:
        return True
    return _zahl_zerlegbar(ziel, tuple(pool), set())


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


# Versalien-Folge ab drei Buchstaben – die Einheit, die L7 bewertet.
VERSAL_RX = re.compile(r"[A-ZÄÖÜ]{3,}")
# Längstes Kürzel, das ohne Kanon-Eintrag als Fachbegriff gelten darf
# (DOCSIS, DSGVO, SCHUFA). Alles darüber ist ein geschrienes Wort.
KUERZEL_MAX_LEN = 6
# Werbe-Schreiwörter: in Versalien IMMER Geschrei, auch wenn ein Artikel sie
# so schreibt. Erweiterbar über `meta.gate.schrei_woerter` (channels.yaml).
SCHREI_WOERTER_STANDARD = frozenset({
    "ACHTUNG", "AKTION", "BESTE", "CHANCE", "EXKLUSIV", "GRATIS", "HEUTE",
    "JETZT", "KOSTENLOS", "LETZTE", "MEGA", "NEU", "NUR", "SOFORT", "SPAREN",
    "STOPP", "SUPER", "TOP", "WICHTIG", "WOW",
})


def _kanon_kuerzel() -> frozenset[str]:
    """Versalien-Folgen aus dem Haus-Kanon (Akronyme, Marken, Einheiten).

    Eine Quelle für alle Werkzeuge: Was `tag_casing` als „DNS“, „HTTPS“ oder
    „FRITZ!Box“ kanonisiert, ist per Definition kein Geschrei.
    """
    out: set[str] = set()
    for lexikon in (tag_casing.ACRONYMS, tag_casing.BRANDS, tag_casing.UNITS):
        for kanon in lexikon.values():
            out.update(VERSAL_RX.findall(str(kanon)))
    return frozenset(out)


KANON_KUERZEL = _kanon_kuerzel()


def schrei_woerter(gate_cfg: dict | None = None) -> frozenset[str]:
    extra = ((gate_cfg or {}).get("schrei_woerter") or [])
    return SCHREI_WOERTER_STANDARD | {str(w).strip().upper() for w in extra if str(w).strip()}


def fachkuerzel(material: str, gate_cfg: dict | None = None) -> frozenset[str]:
    """Versalien-Folgen, die in DIESEM Beitrag Fachsprache sind (mit Beleg).

    Belegt ist ein Kürzel, wenn der Haus-Kanon es führt oder wenn der Artikel
    es selbst in Versalien schreibt. Ausgeschlossen bleiben Schreiwörter und
    gewöhnliche Wörter, die der Artikel klein oder als Nomen verwendet – ein
    Artikel, der „Jetzt“ schreibt, belegt kein „JETZT“.
    """
    verboten = schrei_woerter(gate_cfg)
    woerter = set(re.findall(r"[A-Za-zÄÖÜäöüß]+", material or ""))
    belegt = set(KANON_KUERZEL)
    for folge in set(VERSAL_RX.findall(material or "")):
        if len(folge) > KUERZEL_MAX_LEN:
            continue
        if folge.lower() in woerter or folge.capitalize() in woerter:
            continue
        belegt.add(folge)
    return frozenset(belegt - verboten)


def shouting_ratio(text: str, fachkuerzel: Iterable[str] = ()) -> float:
    """Anteil geschriener Wörter am Fließtext.

    REPARATUR 12.10.2026 (Meldung #716, Nebenbefund): Hashtags und URLs
    zählten mit. Hashtags sind aber bewusst CamelCase („#DNSServerWechseln\")
    und Acronym-Tags („#WLAN\", „#DSL\") sind Fachsprache, kein Geschrei. Auf
    Instagram mit 8–11 Tags kippte die Kennzahl dadurch über die Schwelle und
    blockierte ausgerechnet die technikstarken Ratgeber. Seither misst die
    Regel nur den Fließtext – geschrien wird dort weiterhin erkannt.

    REPARATUR 14.10.2026 (#716-Familie, Instagram): Belegte Fachkürzel im
    Fließtext („DNS over HTTPS“) sind ebenfalls kein Geschrei. Ohne Beleg-
    Menge (Altaufrufe) zählt der Kanon des Hauses; Schreiwörter zählen immer.
    """
    prose = URL_RX.sub(" ", TAG_RX.sub(" ", text or ""))
    all_words = re.findall(r"\b\w{3,}\b", prose)
    if not all_words:
        return 0.0
    erlaubt = (frozenset(fachkuerzel) if fachkuerzel
               else KANON_KUERZEL - SCHREI_WOERTER_STANDARD)
    words = [w for w in VERSAL_RX.findall(prose) if w not in erlaubt]
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

    # THREAD-BEWERTUNG (Meldung #716, Nebenbefund): Ein Thread ist EIN
    # Beitrag in mehreren Teilen. Das Gate prüfte nur `text` (= Teil 1) und
    # meldete für jeden Mastodon-Thread „L2 Link fehlt" und „L4 zu wenige
    # Hashtags", weil Link und Tags bewusst im Schlussteil stehen. Damit war
    # der Winkel `thread` auf Mastodon und Bluesky dauerhaft unbenutzbar –
    # ausgerechnet das reichweitenstärkste Format der Fediverse-Kanäle.
    # Seither gilt: Link-, Hashtag-, Sprach- und Faktenprüfung sehen den
    # ganzen Thread; die Längen- und Emoji-Grenze gilt JEDEM Teil, denn die
    # Plattform zählt jeden Teil als eigenen Post.
    teile = [t for t in (pkg.get("thread") or []) if str(t).strip()] or [text]
    gesamt = "\n\n".join(teile)

    max_chars = int(text_cfg.get("max_chars") or 500)
    weight = int(text_cfg.get("link_weight") or 0)
    link_pos = text_cfg.get("link_position") or "end"
    full = "\n".join(p for p in (text, comment, *teile) if p).strip()
    metrics = {
        "chars": max(copy.effective_length(t, url, weight) for t in teile),
        "max_chars": max_chars,
        "hashtags": len(TAG_RX.findall(gesamt)),
        "emoji": max(count_emoji(t) for t in teile),
        "similarity": 0.0,
        "teile": len(teile),
    }

    # -- L1 Länge -----------------------------------------------------------
    if metrics["chars"] > max_chars:
        violations.append(f"L1 zu lang: {metrics['chars']} > {max_chars} Zeichen")
    min_chars = int(gate_cfg.get("min_chars") or 0)
    if len(text.strip()) < min_chars:
        violations.append(f"L1 zu kurz: {len(text.strip())} < {min_chars} Zeichen")
    max_parts = int((text_cfg.get("thread") or {}).get("max_parts") or 0)
    if len(teile) > 1 and max_parts and len(teile) > max_parts:
        violations.append(f"L1 Thread zu lang: {len(teile)} > {max_parts} Teile")

    # -- L2 Link ------------------------------------------------------------
    for pattern in (link_cfg.get("forbid") or []):
        if pattern.lower() in full.lower():
            violations.append(f"L2 unzulässiger Link/Shortener: {pattern}")
    if SHORTENER_RX.search(full):
        violations.append("L2 Link-Shortener unzulässig")
    if text_cfg.get("link_required"):
        # `destination` = der Link reist als Ziel-Link des Beitrags (Pinterest
        # pinzt die Artikel-URL als Pin-Ziel, nicht in die Beschreibung).
        # Ein nacktes „URL fehlt im Text" wäre hier ein Falschurteil – geprüft
        # wird stattdessen, dass überhaupt eine kanonische Ziel-URL gesetzt ist.
        if link_pos == "destination":
            if not url:
                violations.append("L2 kanonischer Artikel-Link fehlt (Ziel-Link)")
        else:
            where = comment if link_pos == "first_comment" else gesamt
            if url and url not in where:
                violations.append("L2 kanonischer Artikel-Link fehlt")
        if url and not url.startswith(str((meta or {}).get("base_url") or "https://").rstrip("/")):
            violations.append("L2 Link ist keine kanonische Blog-URL")
    if link_pos == "none" and "http" in gesamt:
        violations.append("L2 dieser Kanal erlaubt keine Links im Text")

    # -- L3 Recht & Versprechen --------------------------------------------
    for term in (gate_cfg.get("blocked_terms") or []):
        if term.lower() in full.lower():
            violations.append(f"L3 unzulässiges Versprechen: „{term}“")
    for phrase in (gate_cfg.get("forbidden_phrases") or []):
        if phrase.lower() in full.lower():
            violations.append(f"L3 Phrase gesperrt: „{phrase}“")

    # -- L4 Hashtags --------------------------------------------------------
    tags = TAG_RX.findall(gesamt)
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
    # Je Teil, nicht je Thread: Die Plattform zählt jeden Teil als Post.
    emo_max = int(text_cfg.get("emoji_max") or 0)
    emo_spitze = max(count_emoji(t) for t in teile)
    if emo_spitze > emo_max:
        violations.append(f"L5 zu viele Emojis: {emo_spitze} > {emo_max}")

    # -- L6 Sprache ---------------------------------------------------------
    if not _german_hit(gesamt):
        violations.append("L6 Text wirkt nicht deutschsprachig")

    # -- L7 Shouting / Spam -------------------------------------------------
    if "!!!" in gesamt or "???" in gesamt:
        violations.append("L7 Ausrufezeichen-/Fragezeichen-Ketten")
    # Belegmaterial = alles, was der Texter aus dem Artikel übernehmen darf.
    # Die FAQ gehört dazu: Der Winkel `frage` zitiert Frage und Antwort
    # wörtlich aus dem Artikel – ohne sie im Material galt jede Zahl der
    # Antwort („§ 554 BGB“, „50 bis 100 Mbit/s“) als erfunden.
    material = " ".join([
        article.get("kurzantwort") or "", article.get("description") or "",
        article.get("title") or "", " ".join(article.get("takeaways") or []),
        " ".join(article.get("keywords") or []), " ".join(article.get("tags") or []),
        article.get("faq_question") or "", article.get("faq_answer") or "",
    ])
    ratio = shouting_ratio(gesamt, fachkuerzel(material, gate_cfg))
    metrics["shouting"] = round(ratio, 3)
    if ratio > float(gate_cfg.get("max_shouting_ratio") or 0.12):
        violations.append(f"L7 zu viele Großbuchstaben ({ratio:.0%})")
    if len(URL_RX.findall(gesamt)) > 2:
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
    # Dasselbe Material wie die Kürzel-Belege in L7: EINE Belegquelle je Beitrag.
    material_nums = set(NUM_RX.findall(material))
    # Fließtext OHNE Hashtag-Block: Ein Hashtag ist ein Schlagwort, keine
    # Behauptung im Satz. Seine Zahlen werden gleich einzeln geprüft.
    body_nums = set(NUM_RX.findall(TAG_RX.sub(" ", _strip_enum(gesamt))))
    invented = sorted(n for n in body_nums
                      if not zahl_belegt(n, material_nums) and n not in url)
    if invented:
        violations.append(f"L9 Zahl ohne Beleg im Artikel: {', '.join(invented[:4])}")
    for tag in sorted(set(TAG_RX.findall(gesamt))):
        erfunden = sorted(n for n in NUM_RX.findall(tag)
                          if not zahl_belegt(n, material_nums))
        if erfunden:
            violations.append(
                f"L9 Zahl im Hashtag ohne Beleg: #{tag} ({', '.join(erfunden[:3])})")

    # -- L10 Bildpflicht ----------------------------------------------------
    if media_cfg.get("required") and not (pkg.get("media_url") or pkg.get("media_path")):
        violations.append("L10 dieser Kanal verlangt ein Bild, es liegt keines vor")

    return (not violations), violations, metrics
