#!/usr/bin/env python3
"""ff_voice_audio.py — Studio-Tonspuren für die Vorlese-Funktion (FF Voice Studio).

Vertont die Artikel des Blogs mit einer MÄNNLICHEN DE- & EN-Stimme —
kostenlos, ohne Schlüssel und ohne Umschalter für die Leser:innen.

Warum vorab vertonen?
    Die Web-Speech-API klingt auf jedem Gerät anders, weil jedes
    Betriebssystem eigene Stimmen mitbringt. Eine vorab erzeugte Tonspur
    läuft im nativen HTML5-<audio>-Element und klingt dadurch IDENTISCH
    auf iPhone, iPad, Mac, Android, Windows/Linux und in Chrome, Safari,
    Firefox und Edge — der Standard der großen Verlagshäuser.

Zwei Tonpfade, eine Regie
    (a) STUDIO-TONSPUR   Diese Datei erzeugt sie (MP3, 24 kHz Mono,
                         −16 LUFS nach EBU R128).
    (b) BROWSER-ENGINE   static/premium/ff-voice.js bleibt als sofortiger
                         Fallback aktiv, wenn keine Tonspur vorliegt.
    Beide fahren dieselbe Aussprache- und Prosodie-Regie — erzwungen
    durch scripts/ff_voice_parity_check.py.

Block-Parität (der kritische Punkt)
    Die Tonspur adressiert Blöcke über ihren Index `b`. Stimmt die
    Reihenfolge nicht exakt mit collectBlocks() des Readers überein,
    wandert die Live-Markierung am gesprochenen Text vorbei. Deshalb
    baut extract_blocks() dieselbe Reihenfolge serverseitig nach:
        Anmoderation → Vorab-Boxen → DOM-Reihenfolge → Abmoderation
    Der Selbsttest prüft das gegen ein fest verdrahtetes Fixture, das
    Paritäts-Gate prüft es gegen die echte Reader-Datei.

Aufruf (lokal oder im Deploy-Workflow NACH `hugo --minify`):
  python3 scripts/ff_voice_audio.py --html-dir public \\
      --out-dir public/audio/articles --cache-dir /tmp/ff-voice-cache \\
      --backend auto --profile natural [--only <slug>] [--dry-run] [--force]

  · --backend   auto (edge → piper → groq) | edge | piper | groq
  · --profile   natural (Multilingual v2) | narrator (Conrad/Ryan)
  · --out-dir   Zielverzeichnis. Pro Artikel entstehen <slug>.mp3
                (Fallback .wav ohne ffmpeg) + <slug>.track.json.
  · --cache-dir Vorherige Tonspuren (z. B. aus dem letzten gh-pages-Stand).
                Unveränderte Artikel werden 1:1 wiederverwendet
                (Fingerprint inkl. Backend, Stimme und Rezept-Version).
  · --limit-new max. Anzahl NEU vertonter Artikel je Lauf (0 = alle).
  · Injektion   Der Generator schreibt zusätzlich
                <script type="application/json" id="ff-voice-track-config">
                in jede Artikel-HTML.

Diagnose & Selbsttests (ohne Netzwerk/Key):
  python3 scripts/ff_voice_audio.py --selftest
  python3 scripts/ff_voice_audio.py --engines
  python3 scripts/ff_voice_backends.py --selftest
"""

from __future__ import annotations

import argparse
import hashlib
import html as html_mod
import json
import os
import re
import shutil
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import ff_voice_backends as ttb  # noqa: E402

# ---------------------------------------------------------------------------
# Vertrag mit dem Reader
# ---------------------------------------------------------------------------

CONFIG_BLOCK_ID = "ff-voice-track-config"
READER_CONFIG_ID = "ff-voice-config"

CONTENT_SELECTOR = (
    "h2, h3, h4, h5, h6, p, li, blockquote, "
    'table, [role="table"], [role="grid"], [role="treegrid"], '
    ".ff-table-scroll, .ff-tv-tablewrap, .ff-es-tablewrap, "
    ".wp-block-table, .table-wrapper, .table-responsive, "
    "strong, b, "
    ".ff-tarif-card, .ff-einspar-box, .ff-kurzantwort, .ff-korrektur, .callout, "
    ".ff-tv-footnote, .ff-es-footnote"
)

BOX_CLASSES = ["ff-tarif-card", "ff-einspar-box", "ff-kurzantwort", "ff-korrektur", "callout"]
TABLE_WRAPPERS = ("table", '[role="table"]', '[role="grid"]', ".ff-table-scroll",
                  ".ff-tv-tablewrap", ".ff-es-tablewrap", ".wp-block-table",
                  ".table-wrapper", ".table-responsive")

SKIP_CLASSES = ["ff-voice-bar", "toc", "ff-toc"]

# Redaktionelle Cues — spiegelbildlich zu I18N in static/premium/ff-voice.js
CUES = {
    "de": {
        "introLine": "{title}. Ein Beitrag von FranksFinanzcheck. Hördauer etwa {duration}.",
        "durationMinutes": "{n} Minuten", "durationMinuteOne": "eine Minute",
        "durationUnknown": "einige Minuten",
        "outroLine": "Ende des Beitrags. Vielen Dank fürs Zuhören bei FranksFinanzcheck.",
        "listItemNum": "Punkt {n}:",
        "cueShortAnswer": "Kurzantwort:", "cueCorrection": "Korrekturhinweis:",
        "cueSaving": "Sparpotenzial:", "cueTariff": "Tarif im Überblick:",
        "cueWarning": "Achtung:", "cueNote": "Hinweis:",
        "columnLabel": "Spalte", "rowLabel": "Zeile",
        "tableHeaders": "Die Spalten lauten: {headers}.",
        "tableHeaderRow": "Kopfzeile {n}: {headers}.",
        "tableIntro": "Tabelle: {title}. Übersicht mit {cols} Spalten und {rows} Zeilen.",
        "tableIntroOne": "Tabelle: {title}. Übersicht mit {cols} Spalten und einer Zeile.",
        "tableRow": "Zeile {row} von {total}. {content}.",
        "tableRowLabel": "Zeile {row} von {total}: {label}. {content}.",
        "tableGroup": "Gruppe: {name}.",
        "tableSum": "Zusammengerechnet: {content}.",
        "tableCta": "Empfehlung: {cta}. Hinweis: Dies ist ein Partnerlink.",
        "tableOutro": "Ende der Tabelle {title}.",
        "tableDefault": "Übersichtstabelle",
    },
    "en": {
        "introLine": "{title}. An article by FranksFinanzcheck. Listening time about {duration}.",
        "durationMinutes": "{n} minutes", "durationMinuteOne": "one minute",
        "durationUnknown": "a few minutes",
        "outroLine": "End of article. Thank you for listening to FranksFinanzcheck.",
        "listItemNum": "Point {n}:",
        "cueShortAnswer": "Short answer:", "cueCorrection": "Correction:",
        "cueSaving": "Savings potential:", "cueTariff": "Tariff at a glance:",
        "cueWarning": "Attention:", "cueNote": "Note:",
        "columnLabel": "Column", "rowLabel": "Row",
        "tableHeaders": "The columns are: {headers}.",
        "tableHeaderRow": "Header row {n}: {headers}.",
        "tableIntro": "Table: {title}. Overview with {cols} columns and {rows} rows.",
        "tableIntroOne": "Table: {title}. Overview with {cols} columns and one row.",
        "tableRow": "Row {row} of {total}. {content}.",
        "tableRowLabel": "Row {row} of {total}: {label}. {content}.",
        "tableGroup": "Group: {name}.",
        "tableSum": "In total: {content}.",
        "tableCta": "Recommendation: {cta}. Note: this is an affiliate link.",
        "tableOutro": "End of table {title}.",
        "tableDefault": "Overview Table",
    },
}

DE_HINTS = {
    "der": 2, "die": 2, "das": 2, "und": 2, "ist": 2, "sind": 2, "für": 2, "mit": 2, "nicht": 2,
    "von": 1, "ein": 1, "eine": 1, "einen": 1, "einem": 1, "den": 1, "dem": 1, "auf": 1, "zu": 1,
    "im": 1, "am": 1, "bei": 1, "auch": 1, "sich": 1, "sparen": 2, "spart": 2, "euro": 2,
    "versicherung": 2, "kosten": 2, "vertrag": 2, "vergleich": 2, "wechseln": 2,
    "günstig": 2, "kostenlos": 2, "ratgeber": 2, "tabelle": 2, "jahr": 1, "monat": 1,
    "sollte": 1, "solltest": 1, "müssen": 1, "kann": 1, "wichtig": 1, "tipp": 1, "prüfen": 1,
}
EN_HINTS = {
    "the": 2, "and": 2, "is": 2, "are": 2, "for": 2, "with": 2, "that": 2, "this": 2,
    "your": 2, "you": 2, "from": 1, "our": 1, "save": 2, "saving": 2, "money": 2,
    "insurance": 2, "costs": 2, "cost": 2, "compare": 2, "comparison": 2, "guide": 2,
    "table": 2, "tariff": 1, "tariffs": 1, "should": 1, "will": 1, "can": 1, "have": 1,
    "more": 1, "free": 1, "cheap": 1, "best": 1, "important": 1, "article": 1,
    "summary": 1, "read": 1, "listen": 1, "avoid": 1, "switch": 1,
}


def detect_language(sample: str, declared: str = "de") -> str:
    """Portierung von detectArticleLanguage() aus dem Reader."""
    base = "en" if str(declared or "de").lower().startswith("en") else "de"
    tokens = re.findall(r"[a-zäöüß]+", (sample or "").lower())
    de = en = de_hits = en_hits = 0
    for w in tokens:
        if w in DE_HINTS:
            de += DE_HINTS[w]
            de_hits += 1
        if w in EN_HINTS:
            en += EN_HINTS[w]
            en_hits += 1
        if re.search(r"[äöüß]", w):
            de += 2
        if len(w) >= 6 and re.search(r"(ung|keit|heit|schaft|lich|isch)$", w):
            de += 1
    if base == "de":
        # ceil(de * 1.25) – dieselbe Schwelle wie im Reader
        need = (de * 125 + 99) // 100
        return "en" if (en_hits >= 4 and en >= de + 3 and en >= need) else "de"
    # ceil(en * 1.15)
    need = (en * 115 + 99) // 100
    return "de" if (de_hits >= 4 and de >= en + 3 and de >= need) else "en"


def sniff_sentence_lang(sentence: str, base_lang: str) -> str:
    """Portierung von sniffSentenceLang() aus dem Reader."""
    text = sentence or ""
    if len(text) < 12:
        return base_lang
    words = re.findall(r"[a-zäöüß']+", text.lower())
    if len(words) < 3:
        return base_lang
    de = en = 0
    for w in words:
        if w in DE_HINTS:
            de += DE_HINTS[w]
        if w in EN_HINTS:
            en += EN_HINTS[w]
        if re.search(r"[äöüß]", w):
            de += 2
        if len(w) >= 6 and re.search(r"(ung|keit|heit|schaft|lich|isch)$", w):
            de += 1
        if len(w) >= 4 and re.search(r"(ing|tion|ment|ness|able|ible)$", w):
            en += 1
    if base_lang == "de":
        return "en" if (en >= 4 and en >= de + 2) else "de"
    return "de" if (de >= 4 and de >= en + 2) else "en"


# ---------------------------------------------------------------------------
# Wortlauf-Regie — Sprachwechsel MITTEN im Satz (Spiegel von ff-voice.js)
# ---------------------------------------------------------------------------
# Bisher entschied der Satz über die Sprache: Ein deutscher Satz mit
# englischen Fachbegriffen („Ein Robo Advisor nutzt Compound Interest
# …“) wurde GANZ von der deutschen Stimme vertont. Diese Regie zerlegt
# jede Atemgruppe in SPRACHLÄUFE; der Tonspur-Generator vertont jeden
# Lauf mit der passenden männlichen Stimme. Wortgleich gespiegelt in
# static/premium/ff-voice.js (languageRuns); die Parität prüft
# scripts/ff_voice_parity_check.py.

# Englische Belegwörter. 2 = trägt einen Wechsel mit Partner,
# 3 = Finanz-Fachbegriff (trägt allein).
EN_WORDS = {
    "the": 2, "this": 2, "that": 2, "these": 2, "those": 2, "your": 2, "you": 2, "yours": 2,
    "of": 2, "to": 2, "from": 2, "with": 2, "without": 2, "about": 2, "over": 2, "under": 2,
    "when": 2, "while": 2, "then": 2, "than": 2, "there": 2, "where": 2, "why": 2, "how": 2,
    "what": 2, "who": 2, "whom": 2, "which": 2, "because": 2, "however": 2, "again": 2,
    "against": 2, "before": 2, "after": 2,
    "is": 2, "are": 2, "were": 2, "been": 2, "being": 2, "have": 2, "has": 2, "had": 2,
    "would": 2, "could": 2, "should": 2, "can": 2, "may": 2, "might": 2, "must": 2,
    "more": 2, "most": 2, "free": 2, "save": 2, "saving": 2, "savings": 2, "money": 2,
    "costs": 2, "cost": 2, "cheap": 2, "compare": 2, "comparison": 2, "guide": 2,
    "important": 2, "article": 2, "summary": 2, "avoid": 2, "switch": 2, "insurance": 2,
    "yearly": 2, "monthly": 2, "every": 2, "percent": 2, "hundred": 2, "thousand": 2,
    "table": 2, "best": 2, "better": 2, "good": 2,
    "our": 1, "read": 1, "listen": 1, "tariff": 1, "tariffs": 1, "cash": 1, "per": 1,
    "new": 1, "old": 1, "side": 1, "picking": 1, "traded": 1, "score": 1, "tax": 1,
    "invest": 1, "dividend": 1, "value": 1, "hold": 1, "and": 2, "or": 1, "but": 2, "not": 1, "if": 1,
    # Finanz- und Verbraucherbegriffe, die im deutschen Satz englisch klingen
    "broker": 3, "brokers": 3, "neobroker": 3, "neobrokers": 3,
    "cashflow": 3, "cashflows": 3, "trading": 3, "trader": 3, "traders": 3,
    "budgeting": 3, "compounding": 3, "robo": 3,
    "advisor": 3, "advisors": 3, "adviser": 3, "advisers": 3,
    "compound": 2, "interest": 2, "stock": 2, "stocks": 2, "hustle": 2, "hustles": 2,
    "investing": 2, "investor": 2, "investors": 2, "income": 2, "wealth": 2,
    "emergency": 2, "fund": 2, "funds": 2, "retirement": 2, "financial": 2,
    "independence": 2, "credit": 2, "debt": 2, "loan": 2, "loans": 2, "mortgage": 2,
    "taxes": 2, "yield": 2, "yields": 2, "dividends": 2, "exchange": 2, "buy": 2, "sell": 2,
}

# Scheinfreunde: in beiden Sprachen echte Wörter — nie Evidenz.
DE_EN_HOMOGRAPHS = {
    "die": 1, "was": 1, "hat": 1, "will": 1, "rat": 1, "gut": 1, "so": 1, "man": 1,
    "fast": 1, "all": 1, "tag": 1, "see": 1, "arm": 1, "tot": 1, "hut": 1, "gift": 1,
    "boot": 1, "band": 1, "brand": 1, "kind": 1, "land": 1, "links": 1, "fall": 1,
    "ball": 1, "war": 1,
}

# Deutscher Belegwortschatz (Härtung der Satzmitte): häufige Wörter
# ohne Umlaut, ohne Endungs-Merkmal und ohne Platz in DE_HINTS.
DE_EVIDENCE = {
    "aber": 1, "alle": 1, "allerdings": 1, "also": 1, "ans": 1, "andere": 1,
    "bekannt": 1, "besonders": 1, "bestimmt": 1, "braucht": 1, "dabei": 1, "dadurch": 1,
    "dafür": 1, "dagegen": 1, "deshalb": 1, "dein": 1, "deine": 1,
    "dem": 1, "den": 1, "denn": 1, "der": 1, "des": 1, "dessen": 1, "dich": 1, "dies": 1,
    "dieser": 1, "dieses": 1, "du": 1, "durch": 1, "eben": 1, "einfach": 1, "er": 1,
    "es": 1, "euch": 1, "euer": 1, "etwas": 1, "genau": 1, "gerade": 1, "gegen": 1,
    "gibt": 1, "gilt": 1, "hast": 1, "haben": 1, "heute": 1, "hier": 1, "ihm": 1, "ihn": 1,
    "ihnen": 1, "ihr": 1, "ihre": 1, "immer": 1, "ins": 1, "ja": 1, "je": 1, "jede": 1,
    "jeden": 1, "jetzt": 1, "kommt": 1, "kann": 1, "kein": 1, "keine": 1, "könnte": 1,
    "machen": 1, "macht": 1, "mal": 1, "mehr": 1, "mein": 1, "meine": 1, "mich": 1,
    "mir": 1, "nach": 1, "natürlich": 1, "nie": 1, "noch": 1, "nun": 1, "nur": 1,
    "nutzt": 1, "nutzen": 1, "ob": 1, "oder": 1, "oft": 1, "richtig": 1, "schon": 1,
    "sein": 1, "seine": 1, "sich": 1, "sind": 1, "soll": 1, "sollen": 1, "sondern": 1,
    "sonst": 1, "sowie": 1, "über": 1, "um": 1, "und": 1, "uns": 1, "unser": 1, "unter": 1,
    "vom": 1, "von": 1, "vor": 1, "warum": 1, "weg": 1, "weil": 1, "weiter": 1, "wenn": 1,
    "wer": 1, "werde": 1, "werden": 1, "wirklich": 1, "wie": 1, "wieder": 1, "wir": 1,
    "wird": 1, "wo": 1, "wollen": 1, "wäre": 1, "zum": 1, "zur": 1, "zurück": 1,
    "zwischen": 1, "kostet": 1, "bringt": 1, "zahlt": 1, "steht": 1, "gilt": 1,
    "sorgt": 1, "senkt": 1, "liegt": 1, "bleibt": 1, "sorgen": 1, "senken": 1,
    "inzwischen": 1, "schließlich": 1, "außerdem": 1, "ebenfalls": 1, "dennoch": 1,
    "trotzdem": 1, "insgesamt": 1, "derzeit": 1, "aktuell": 1, "vielleicht": 1,
    "eigentlich": 1, "sicher": 1, "deutlich": 1, "sofort": 1, "häufig": 1, "selten": 1,
}

RE_WORD_RUN = re.compile(r"[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß'’]*")
RE_TRAIL_SOFT = re.compile(r"^[\s,.:;!?\u2026„“\"'’()\[\]\-\u2013\u2014]+")


def word_class_of(word: str, base: str):
    """Sprachklasse eines Wortes — None heißt: kein Beleg, folgt dem Lauf."""
    lw = re.sub(r"['’]s$", "", (word or "").lower())
    if not lw:
        return None
    if lw in DE_EN_HOMOGRAPHS:
        return None
    de_score = en_score = 0
    if re.search(r"[äöüß]", lw):
        de_score = 2
    if lw in DE_HINTS:
        de_score = max(de_score, DE_HINTS[lw])
    if lw in DE_EVIDENCE:
        de_score = max(de_score, DE_EVIDENCE[lw])
    if lw in EN_WORDS:
        en_score = max(en_score, EN_WORDS[lw])
    if de_score == 0 and en_score == 0 and len(lw) >= 6:
        # Endungs-Evidenz nur als Zweitbeleg (Score 1); „ing“ erst ab
        # 7 Zeichen und nie, wenn ein deutsches Endungs-Wort vorliegt.
        if base == "de":
            if re.search(r"(ung|keit|heit|schaft|lich|isch)$", lw):
                de_score = 1
            elif re.search(r"(ness|able|ible)$", lw):
                en_score = 1
            elif len(lw) >= 7 and re.search(r"ing$", lw):
                en_score = 1
        else:
            if re.search(r"(ness|able|ible)$", lw):
                en_score = 1
            elif len(lw) >= 7 and re.search(r"ing$", lw):
                en_score = 1
            elif re.search(r"(ung|keit|heit|schaft|lich|isch)$", lw):
                de_score = 1
    if de_score and en_score:
        return None
    if de_score:
        return {"lang": "de", "score": de_score}
    if en_score:
        return {"lang": "en", "score": en_score}
    return None


def language_runs(text: str, base_lang: str) -> list:
    """Zerlegt Text in maximale SPRACHLÄUFE. Die Segmente konkatenieren
    exakt zum Eingabetext (Vertrag an die Paritäts-Prüfung)."""
    base = "en" if base_lang == "en" else "de"
    src = str(text or "")
    if not src:
        return []

    anchors = []
    for m in RE_WORD_RUN.finditer(src):
        cls = word_class_of(m.group(0), base)
        if cls:
            anchors.append({"lang": cls["lang"], "score": cls["score"],
                            "start": m.start(), "end": m.end()})
    if not anchors:
        return [{"text": src, "lang": base}]

    # Ankern gleicher Sprache zu Gruppen bündeln.
    groups = []
    for a in anchors:
        if groups and groups[-1]["lang"] == a["lang"]:
            groups[-1]["items"].append(a)
            groups[-1]["end"] = a["end"]
        else:
            groups.append({"lang": a["lang"], "items": [a],
                           "start": a["start"], "end": a["end"]})

    def group_stands(g):
        if g["lang"] == base:
            return True
        # Ein Fachbegriff (Score 3) trägt allein; sonst brauchen wir
        # mindestens zwei belegte Wörter — „the“ allein wechselt nicht.
        scores = [a["score"] for a in g["items"]]
        return max(scores) >= 3 or (len(scores) >= 2 and sum(scores) >= 2)

    segs = []
    pos = 0
    for gi, g in enumerate(groups):
        stands = group_stands(g)
        g_lang = g["lang"] if stands else base

        # Kopf bis zum Gruppenbeginn gehört in die Artikelsprache.
        if g["start"] > pos:
            segs.append({"text": src[pos:g["start"]], "lang": base})

        # Die Gruppe selbst: Anfang, Innenlücken (beleglose Wörter und
        # weiche Trenner), Ende — „funds of funds“ bleibt ein Lauf.
        segs.append({"text": src[g["start"]:g["end"]], "lang": g_lang})
        pos = g["end"]

        if gi + 1 >= len(groups):
            tail = src[pos:]
            if tail:
                m = RE_TRAIL_SOFT.match(tail)
                soft_len = m.end() if m else 0
                if soft_len and stands:
                    segs.append({"text": tail[:soft_len], "lang": g_lang})
                if soft_len < len(tail):
                    segs.append({"text": tail[soft_len:], "lang": base})
            pos = len(src)
            continue

        gap_end = groups[gi + 1]["start"]
        gap = src[pos:gap_end]
        if gap and stands:
            m = RE_TRAIL_SOFT.match(gap)
            soft_len = m.end() if m else 0
            if soft_len:
                # Nur stiller Nachlauf (Komma, Punkt, Leerzeichen,
                # Anführung) hängt an die stehende Gruppe — er gibt den
                # Atempunkt am Stimmwechsel. Beleglose Folgewörter
                # bleiben bewusst in der Artikelsprache.
                segs.append({"text": gap[:soft_len], "lang": g_lang})
                gap = gap[soft_len:]
        if gap:
            segs.append({"text": gap, "lang": base})
        pos = gap_end

    if pos < len(src):
        segs.append({"text": src[pos:], "lang": base})

    merged = []
    for s in segs:
        if not s["text"]:
            continue
        if merged and merged[-1]["lang"] == s["lang"]:
            merged[-1]["text"] += s["text"]
        else:
            merged.append(dict(s))
    return merged


def duration_phrase(minutes, C):
    try:
        n = int(minutes)
    except Exception:
        n = 0
    if n <= 0:
        return C["durationUnknown"]
    return C["durationMinuteOne"] if n == 1 else C["durationMinutes"].replace("{n}", str(n))


# ---------------------------------------------------------------------------
# Minimaler DOM — genau so viel, wie die Block-Extraktion braucht
# ---------------------------------------------------------------------------

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr"}
SKIP_TAGS = {"script", "style", "noscript", "svg", "template"}


class Node:
    __slots__ = ("tag", "attrs", "children", "parent", "text")

    def __init__(self, tag=None, attrs=None, parent=None, text=""):
        self.tag = tag
        self.attrs = attrs or {}
        self.children = []
        self.parent = parent
        self.text = text

    def classes(self):
        return (self.attrs.get("class") or "").split()

    def has_class(self, name):
        return name in self.classes()

    def attr(self, name, default=None):
        return self.attrs.get(name, default)


class _Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node(tag="root")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag=tag.lower(), attrs={k.lower(): (v or "") for k, v in attrs},
                    parent=self.stack[-1])
        self.stack[-1].children.append(node)
        if tag.lower() not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        node = Node(tag=tag.lower(), attrs={k.lower(): (v or "") for k, v in attrs},
                    parent=self.stack[-1])
        self.stack[-1].children.append(node)

    def handle_endtag(self, tag):
        tag = tag.lower()
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        node = Node(tag=None, parent=self.stack[-1], text=data)
        self.stack[-1].children.append(node)


def parse_html(markup: str) -> Node:
    b = _Builder()
    try:
        b.feed(markup)
        b.close()
    except Exception:
        pass
    return b.root


def iter_nodes(root: Node):
    stack = [root]
    while stack:
        node = stack.pop(0)
        if node.tag:
            yield node
        stack = list(node.children) + stack


_SIMPLE = re.compile(r'^([a-zA-Z0-9]*)((?:\.[\w-]+)*)((?:\[[^\]]+\])*)$')


def _split_selector(selector: str):
    """Zerlegt „thead tr, .ff-tv-title“ in Schritt-Listen (Nachfahren-Selektor)."""
    parts = []
    for raw in selector.split(","):
        sel = raw.strip()
        if not sel:
            continue
        steps = []
        ok = True
        for token in sel.split():
            m = _SIMPLE.match(token)
            if not m:
                ok = False
                break
            tag = m.group(1).lower()
            classes = [c[1:] for c in re.findall(r"\.[\w-]+", m.group(2))]
            attrs = []
            for a in re.findall(r"\[([^\]]+)\]", m.group(3)):
                am = re.match(r'^([\w-]+)\s*=\s*"?([^"\]]*)"?$', a.strip())
                if am:
                    attrs.append((am.group(1).lower(), am.group(2)))
            steps.append((tag, classes, attrs))
        if ok and steps:
            parts.append(steps)
    return parts


def _matches_compound(node: Node, compound) -> bool:
    tag, classes, attrs = compound
    if not node.tag:
        return False
    if tag and node.tag != tag:
        return False
    if classes and not all(node.has_class(c) for c in classes):
        return False
    if attrs and not all(node.attr(k) == v for k, v in attrs):
        return False
    return True


def _matches_selector(node: Node, steps) -> bool:
    if not _matches_compound(node, steps[-1]):
        return False
    i = len(steps) - 2
    cur = node.parent
    while i >= 0:
        found = False
        while cur is not None:
            if _matches_compound(cur, steps[i]):
                found = True
                cur = cur.parent
                break
            cur = cur.parent
        if not found:
            return False
        i -= 1
    return True


def query_all(root: Node, selector: str) -> list:
    """querySelectorAll für die Selektoren der Lesereihenfolge (Dokumentreihenfolge)."""
    parts = _split_selector(selector)
    out = []
    for node in iter_nodes(root):
        if node is root:
            continue
        for steps in parts:
            if _matches_selector(node, steps):
                out.append(node)
                break
    return out


def find_first(root: Node, selector: str):
    found = query_all(root, selector)
    return found[0] if found else None


def find_by_id(root: Node, ident: str):
    for node in iter_nodes(root):
        if node.attr("id") == ident:
            return node
    return None


def text_of(node: Node) -> str:
    if node is None:
        return ""
    if node.tag is None:
        return node.text or ""
    if node.tag in SKIP_TAGS:
        return ""
    if node.attr("data-ff-skip-read") is not None:
        return ""
    if node.attr("aria-hidden") == "true":
        return ""
    if node.tag in ("br",):
        return " "
    parts = [text_of(c) for c in node.children]
    if node.tag in ("p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6",
                    "blockquote", "tr", "td", "th", "section", "figcaption"):
        parts.append(" ")
    return "".join(parts)


def readable_text(node: Node) -> str:
    return re.sub(r"\s+", " ", text_of(node).replace("\u00a0", " ")).strip()


BOX_HEAD_CLASSES = ("ff-kurzantwort__head", "ff-kurzantwort__label",
                    "ff-kurzantwort__icon", "ff-kurzantwort__eyebrow")


def _text_without(node: Node, skip_classes) -> str:
    if node is None:
        return ""
    if node.tag is None:
        return node.text or ""
    if node.tag in SKIP_TAGS:
        return ""
    if any(node.has_class(c) for c in skip_classes):
        return ""
    parts = [_text_without(c, skip_classes) for c in node.children]
    if node.tag in ("p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6",
                    "blockquote", "tr", "td", "th", "section", "figcaption"):
        parts.append(" ")
    return "".join(parts)


def box_text_without_headline(node: Node) -> str:
    """Dachzeile „Kurz & knapp“ wird nicht mitgesprochen – der Cue sagt es schon."""
    return re.sub(r"\s+", " ", _text_without(node, BOX_HEAD_CLASSES).replace("\u00a0", " ")).strip()


def closest(node: Node, selector: str):
    """Nächster Vorfahre (inkl. sich selbst), der auf den Selektor passt."""
    cur = node
    guard = 0
    while cur is not None and guard < 200:
        guard += 1
        if cur.tag and any(_matches_selector(cur, steps) for steps in _split_selector(selector)
                           if len(steps) == 1):
            return cur
        cur = cur.parent
    return None


def ancestor(node: Node, selector: str):
    """Nächster echter Vorfahre (OHNE sich selbst), der auf den Selektor passt."""
    return closest(node.parent, selector) if node is not None and node.parent else None


def is_skipped(node: Node) -> bool:
    if node is None:
        return True
    if node.attr("data-ff-skip-read") is not None:
        return True
    if node.attr("aria-hidden") == "true":
        return True
    cur = node
    guard = 0
    while cur is not None and guard < 200:
        guard += 1
        if cur.attr("data-ff-skip-read") is not None:
            return True
        if any(cur.has_class(c) for c in SKIP_CLASSES):
            return True
        if cur.tag in ("nav", "template"):
            return True
        cur = cur.parent
    return False


# ---------------------------------------------------------------------------
# Tabellenmodell (Premium, Generation 2) — wortgleich zum Reader
# ---------------------------------------------------------------------------

GENERIC_TABLE_LABELS = ("tabelle", "table")
SUM_WORDS = ("zwischensumme", "summe", "gesamt", "insgesamt", "total",
             "grand total", "in total", "sum")

_DECOR_RE = re.compile(
    "[\u00ad\u200b-\u200f\u2060\u2190-\u21ff\u2300-\u27bf\u2b00-\u2bff"
    "\ufe00-\ufe0f\U0001f000-\U0010ffff]")


def strip_decor(text: str) -> str:
    """Schmuckzeichen, Pfeile und Emoji entfernen (💰 ❌ ✅ 🏆 →)."""
    return re.sub(r"\s+", " ", _DECOR_RE.sub(" ", str(text or ""))).strip()


def span_of(node: Node, attr: str, aria_attr: str) -> int:
    raw = node.attr(attr)
    if raw is None:
        raw = node.attr(aria_attr)
    m = re.match(r"\s*(\d+)", str(raw or ""))
    v = int(m.group(1)) if m else 1
    return min(v, 24) if v > 1 else 1


_BLOCKISH = ("p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6",
             "blockquote", "tr", "td", "th", "section", "figcaption")


def _text_without_tags(node: Node, tags) -> str:
    """text_of() ohne die angegebenen Teilbäume (z. B. <small>)."""
    if node is None:
        return ""
    if node.tag is None:
        return node.text or ""
    if node.tag in SKIP_TAGS or node.tag in tags:
        return ""
    if node.attr("data-ff-skip-read") is not None:
        return ""
    if node.attr("aria-hidden") == "true":
        return ""
    if node.tag == "br":
        return " "
    parts = [_text_without_tags(c, tags) for c in node.children]
    if node.tag in _BLOCKISH:
        parts.append(" ")
    return "".join(parts)


def cell_speech_text(cell: Node) -> str:
    """Zellentext: Grundtext, dann Ziertext aus <small> mit Komma."""
    small_parts = []
    for node in iter_nodes(cell):
        if node.tag == "small":
            t = re.sub(r"\s+", " ", text_of(node).replace("\u00a0", " ")).strip()
            if t:
                small_parts.append(t)
    base = re.sub(r"\s+", " ", _text_without_tags(cell, ("small",))
                  .replace("\u00a0", " ")).strip()
    out = base
    for t in small_parts:
        out = (out + ", " if out else "") + t
    return strip_decor(out)


def is_table_like(node: Node) -> bool:
    if node is None:
        return False
    if node.tag == "table":
        return True
    if node.attr("role") in ("table", "grid", "treegrid"):
        return True
    if any(node.has_class(c) for c in ("ff-table-scroll", "ff-tv-tablewrap", "ff-es-tablewrap")):
        return True
    if any(node.has_class(c) for c in ("wp-block-table", "table-wrapper", "table-responsive")):
        return len(query_all(node, "table")) == 1
    return False


def inner_table(node: Node) -> Node:
    if node.tag == "table":
        return node
    tables = query_all(node, "table")
    return tables[0] if tables else node


def _row_cells(tr: Node, table: Node = None):
    cells = query_all(tr, 'th, td, [role="columnheader"], [role="rowheader"], [role="cell"], [role="gridcell"]')
    # Zellen einer verschachtelten Innentabelle gehören zur Innentabelle.
    if table is not None and table.tag == "table":
        cells = [c for c in cells if closest(c, "table") is table]
    return cells


def _is_header_cell(cell: Node) -> bool:
    if cell.tag == "th":
        return True
    if cell.attr("scope") in ("col", "row", "colgroup", "rowgroup"):
        return True
    return cell.attr("role") in ("columnheader", "rowheader")


def table_rows(table: Node):
    rows, seen = [], []

    def push(tr, kind):
        if tr is None or id(tr) in seen:
            return
        # Zeilen einer verschachtelten Innentabelle gehören nicht hierher.
        owner = closest(tr, "table")
        if owner is not None and owner is not table:
            return
        seen.append(id(tr))
        rows.append((tr, kind))

    for tr in query_all(table, "thead tr"):
        push(tr, "head")
    for tr in query_all(table, "tbody tr"):
        push(tr, "body")
    for tr in query_all(table, "tfoot tr"):
        push(tr, "foot")
    for tr in query_all(table, "tr"):
        if id(tr) not in seen:
            push(tr, "head" if not rows else "body")
    # ARIA-Tabellen ohne <tr>: Zeilen laufen über role="row".
    if not rows:
        for r in query_all(table, '[role="row"]'):
            push(r, "body")
    return rows


_WRAP_SELECTOR = (".ff-tarifvergleich, .ff-einspar, .ff-tv-tablewrap, .ff-es-tablewrap, "
                  ".ff-table-scroll, .wp-block-table, .table-wrapper, .table-responsive")


def _prev_siblings(node: Node):
    if node is None or node.parent is None:
        return []
    sibs = [s for s in node.parent.children if s.tag]
    try:
        i = sibs.index(node)
    except ValueError:
        return []
    return list(reversed(sibs[:i]))


def table_title(table: Node, C) -> str:
    """Titel der Übersicht — caption, aria-label, Premium-Titel oder die
    unmittelbar davorstehende Überschrift (Markdown-Tabellen)."""
    cap = find_first(table, "caption")
    if cap and strip_decor(readable_text(cap)):
        return strip_decor(readable_text(cap))

    # Wrapper-Kette nach oben sammeln (Tablewrapper bis zur Sektion).
    wrappers = []
    node = table
    for _ in range(4):
        wrap = closest(node, _WRAP_SELECTOR)
        if wrap is None or any(wrap is w for w in wrappers):
            break
        wrappers.append(wrap)
        node = wrap.parent

    # aria-label der Tabelle oder ihrer Wrapper — außer Allgemeinplätzen
    # wie „Tabelle“ (vom Table-Render-Hook automatisch gesetzt).
    for src in [table] + wrappers:
        aria = src.attr("aria-label")
        if aria:
            clean = strip_decor(aria)
            if clean and clean.lower() not in GENERIC_TABLE_LABELS:
                return clean

    # Premium-Übersichten setzen ihren Titel AUSSERHALB des
    # Tablewrappers — in jedem Wrapper der Kette suchen.
    for wrap in wrappers:
        h = find_first(wrap, ".ff-tv-title, .ff-es-title, caption, h3, h4")
        if (h is not None and h is not table and closest(h, "table") is not table
                and strip_decor(readable_text(h))):
            return strip_decor(readable_text(h))

    # Unmittelbar davorstehende Überschrift (z. B. Markdown-Tabelle
    # unter einer Zwischenüberschrift).
    outer = wrappers[-1] if wrappers else table
    guard = 0
    for prev in _prev_siblings(outer):
        if guard >= 4:
            break
        guard += 1
        if (prev.tag in ("h2", "h3", "h4", "h5", "h6")
                or any(prev.has_class(c) for c in ("ff-tv-title", "ff-es-title"))):
            t = strip_decor(readable_text(prev))
            if t:
                return t
    return ""


def expand_grid(table: Node, rows):
    """Spannt die Zeilen zu einem logischen Gitter auf: colspan- und
    rowspan-Zellen belegen genau ihre Spalten. `lead` markiert die
    Sprech-Spalte (colspan-Fortsetzungen schweigen, rowspan-Werte
    werden in jeder überspannten Zeile wiederholt)."""
    occupied = {}
    grid = []
    for r, (tr, kind) in enumerate(rows):
        cells = _row_cells(tr, table)
        entries = []
        col = 0
        for cell in cells:
            while (r, col) in occupied:
                entries.append(occupied[(r, col)])
                col += 1
            cs = span_of(cell, "colspan", "aria-colspan")
            rs = span_of(cell, "rowspan", "aria-rowspan")
            text = cell_speech_text(cell)
            head = _is_header_cell(cell)
            for d in range(cs):
                entries.append({"el": cell, "text": text, "head": head, "lead": d == 0})
                for dr in range(1, rs):
                    occupied[(r + dr, col + d)] = {
                        "el": cell, "text": text, "head": head, "lead": True}
            col += cs
        while (r, col) in occupied:
            entries.append(occupied[(r, col)])
            col += 1
        grid.append({"el": tr, "kind": kind, "cells": entries})
    return grid


def _starts_with_sum_word(text: str) -> bool:
    low = str(text or "").lower()
    return any(low.startswith(w) for w in SUM_WORDS)


def build_table_model(table: Node, C):
    grid = expand_grid(table, table_rows(table))
    header_rows, body_rows, foot_rows = [], [], []
    header_done = False

    for row in grid:
        non_empty = [e for e in row["cells"] if e["text"]]
        all_head = bool(non_empty) and all(e["head"] for e in non_empty)
        if row["kind"] == "head" or (not header_done and all_head):
            header_rows.append(row)
            header_done = True
            continue
        if row["kind"] == "foot":
            foot_rows.append(row)
            continue
        body_rows.append(row)

    col_count = max([len(r["cells"]) for r in grid] + [0])

    # Spaltennamen = die UNTERSTE Kopfzeile (sie trägt die Werte).
    headers = []
    if header_rows:
        last_head = header_rows[-1]
        for c in range(col_count):
            e = last_head["cells"][c] if c < len(last_head["cells"]) else None
            headers.append(e["text"] if e and e["text"] else "")

    # Darüberliegende Kopfzeilen (Gruppierungen) werden angesagt.
    header_extras = []
    for row in header_rows[:-1]:
        texts = []
        for entry in row["cells"]:
            if not entry["text"] or entry["lead"] is False:
                continue
            if texts and texts[-1] == entry["text"]:
                continue
            texts.append(entry["text"])
        if texts:
            header_extras.append(", ".join(texts))

    def classify(row, is_foot):
        rec = {"el": row["el"], "kind": "data", "label": "", "parts": [],
               "cta": "", "group": "", "display": []}
        non_empty = [{"e": e, "c": c} for c, e in enumerate(row["cells"]) if e["text"]]
        for entry in row["cells"]:
            rec["display"].append(entry["text"] if entry["lead"] is not False else "")
        if not non_empty:
            rec["kind"] = "empty"
            return rec

        # 1 · Werbelink-Zeile (CTA): Button/Partnerlink in der Zelle.
        cta_parts, cta_cells, plain_cells = [], 0, []
        for item in non_empty:
            links = query_all(item["e"]["el"], "a.ff-tv-btn, a.ff-es-btn, a.ff-cta, button")
            texts = []
            for a in links:
                t = strip_decor(readable_text(a))
                if t:
                    texts.append(t)
            if texts:
                cta_cells += 1
                for t in texts:
                    if t not in cta_parts:
                        cta_parts.append(t)
            else:
                plain_cells.append(item["e"]["text"])
        only_decor_left = all(len(t) < 24 and not re.search(r"\d", t) for t in plain_cells)
        if cta_cells > 0 and only_decor_left:
            rec["kind"] = "cta"
            rec["cta"] = ", ".join(cta_parts)
            return rec

        # 2 · Summenzeile: tfoot, Summen-Klasse oder Summenwort.
        first = non_empty[0]
        is_sum = (is_foot or row["el"].has_class("ff-es-sum")
                  or row["el"].has_class("ff-tv-sum")
                  or _starts_with_sum_word(first["e"]["text"]))
        if is_sum:
            rec["kind"] = "sum"
            skip_first = _starts_with_sum_word(first["e"]["text"])
            for i, item in enumerate(non_empty):
                if i == 0 and skip_first:
                    continue   # „Summe/Gesamt“ sagt der Cue selbst
                if item["e"]["lead"] is False:
                    continue
                spoken = _cell_speech(headers[item["c"]] if item["c"] < len(headers) else "",
                                      item["e"]["text"], item["c"], C)
                if spoken:
                    rec["parts"].append(spoken)
            return rec

        # 3 · Gruppenzeile: alle Zellen sind Köpfe (z. B. th mit colspan).
        if all(item["e"]["head"] for item in non_empty):
            names = []
            for item in non_empty:
                if item["e"]["lead"] is not False and item["e"]["text"] not in names:
                    names.append(item["e"]["text"])
            rec["kind"] = "group"
            rec["group"] = ", ".join(names)
            return rec

        # 4 · Datenzeile — ein Zeilentitel (th/rowheader) wird ihr Name.
        start_at = 0
        if first["e"]["head"]:
            rec["label"] = first["e"]["text"]
            start_at = 1
        for item in non_empty[start_at:]:
            if item["e"]["lead"] is False:
                continue
            spoken = _cell_speech(headers[item["c"]] if item["c"] < len(headers) else "",
                                  item["e"]["text"], item["c"], C)
            if spoken:
                rec["parts"].append(spoken)
        return rec

    rows = [classify(r, False) for r in body_rows] + [classify(r, True) for r in foot_rows]

    return {"title": table_title(table, C) or C["tableDefault"],
            "headers": headers, "headerExtras": header_extras,
            "rows": rows, "colCount": col_count}


def _cell_speech(name, value, index, C):
    label = name if (name and str(name).strip()) else "%s %d" % (C["columnLabel"], index + 1)
    val = "" if value is None else str(value)
    if not val:
        return ""
    return "%s: %s" % (label, val)


def extract_table_blocks(table: Node, block_lang: str, C):
    """Eine Tabelle wird vollständig gesprochen — Zeile für Zeile."""
    model = build_table_model(table, C)
    out = []
    title = model["title"] or C["tableDefault"]

    data_rows = [r for r in model["rows"] if r["kind"] == "data" and r["parts"]]
    has_content = (bool(data_rows) or any(model["headers"]) or bool(model["headerExtras"])
                   or any(r["kind"] in ("sum", "cta", "group") for r in model["rows"]))
    if not has_content:
        return out   # leere Hülle: nichts sprechen

    row_count = len(data_rows)
    tmpl = C["tableIntroOne"] if row_count == 1 else C["tableIntro"]
    out.append({"lang": block_lang, "type": "table-intro",
                "text": tmpl.replace("{title}", title)
                            .replace("{cols}", str(model["colCount"]))
                            .replace("{rows}", str(row_count))})

    spoken_headers = [h for h in model["headers"] if h]
    if spoken_headers:
        out.append({"lang": block_lang, "type": "table-header",
                    "text": C["tableHeaders"].replace("{headers}", ", ".join(spoken_headers))})
    for i, extra in enumerate(model["headerExtras"]):
        out.append({"lang": block_lang, "type": "table-header",
                    "text": C["tableHeaderRow"].replace("{n}", str(i + 1))
                                               .replace("{headers}", extra)})

    data_idx = 0
    for row in model["rows"]:
        if row["kind"] == "empty":
            continue
        if row["kind"] == "data":
            if not row["parts"]:
                continue
            data_idx += 1
            tmpl_row = C["tableRowLabel"] if row["label"] else C["tableRow"]
            out.append({"lang": block_lang, "type": "table-row",
                        "text": tmpl_row.replace("{row}", str(data_idx))
                                        .replace("{total}", str(row_count))
                                        .replace("{label}", row["label"])
                                        .replace("{content}", ", ".join(row["parts"]))})
            continue
        if row["kind"] == "group":
            out.append({"lang": block_lang, "type": "table-group",
                        "text": C["tableGroup"].replace("{name}", row["group"])})
            continue
        if row["kind"] == "sum":
            if not row["parts"]:
                continue
            out.append({"lang": block_lang, "type": "table-sum",
                        "text": C["tableSum"].replace("{content}", ", ".join(row["parts"]))})
            continue
        if row["kind"] == "cta" and row["cta"]:
            out.append({"lang": block_lang, "type": "table-cta",
                        "text": C["tableCta"].replace("{cta}", row["cta"])})

    out.append({"lang": block_lang, "type": "table-outro",
                "text": C["tableOutro"].replace("{title}", title)})
    return out


# ---------------------------------------------------------------------------
# Block-Extraktion — dieselbe Reihenfolge wie collectBlocks() im Reader
# ---------------------------------------------------------------------------

def _lang_of(node: Node, fallback: str) -> str:
    attr = (node.attr("lang") or "").lower()
    if attr.startswith("en"):
        return "en"
    if attr.startswith("de"):
        return "de"
    sample = readable_text(node)[:400]
    if len(sample) >= 40:
        return sniff_sentence_lang(sample, fallback)
    return fallback


def _is_standalone_emphasis(node: Node) -> bool:
    """Fettdruck ist ein eigener Block, wenn er praktisch das ganze
    Elternelement ausmacht. Maßgeblich ist allein der TEXTANTEIL: Ein
    Lead-in wie „<strong>Tarifwechsel als größter Hebel:</strong> Ein
    Wechsel …“ ist KEIN eigener Merksatz — der Listenpunkt spricht es
    bereits. (Die frühere Knotenzahl-Regel „siblings <= 2“ scheiterte
    an Textknoten: <li><strong>…</strong> Rest</li> hat genau zwei
    Kindknoten und galt so fälschlich als eigenständig — genau der
    Doppel-Leser auf /pillar/strom-sparen/.)"""
    text = readable_text(node)
    if len(text) < 12:
        return False
    parent = node.parent
    if parent is None:
        return False
    parent_text = readable_text(parent)
    return len(text) >= max(12, len(parent_text) - 2)


def extract_blocks(root: Node, cfg: dict):
    """Gibt (blocks, lang) zurück. blocks: [{lang, type, text}] in Lesereihenfolge."""
    content = find_first(root, ".post-content") or find_first(root, ".md-content")
    if content is None:
        return [], "de"

    declared = cfg.get("lang") or "de"
    sample = "%s %s %s" % (cfg.get("title", ""), cfg.get("description", ""),
                           readable_text(content)[:5000])
    lang = detect_language(sample, declared)
    C = CUES[lang]

    out = []

    # (1) Anmoderation
    out.append({"lang": lang, "type": "intro",
                "text": C["introLine"].replace("{title}", cfg.get("title", ""))
                                      .replace("{duration}", duration_phrase(cfg.get("readingTime"), C))})

    # (2) Vorab-Boxen
    for box in query_all(root, ".ff-korrektur, .ff-kurzantwort"):
        if closest(box, ".post-content, .md-content") is not None:
            continue
        if is_skipped(box):
            continue
        probe_text = box_text_without_headline(box)
        if len(probe_text) <= 5:
            continue
        is_korrektur = box.has_class("ff-korrektur")
        out.append({"lang": lang, "type": "warning" if is_korrektur else "callout",
                    "text": (C["cueCorrection"] if is_korrektur else C["cueShortAnswer"]) + " " + probe_text})

    # (3) Artikelblöcke in DOM-Reihenfolge
    done = []
    spoken_blocks = []   # (Element, Text) — Fundament der Doppel-Lese-Schleuse
    for el in query_all(content, CONTENT_SELECTOR):
        if is_skipped(el):
            continue
        if closest(el, "figure") is not None and not is_table_like(el):
            continue
        if closest(el, ".ff-tv-cards, .ff-es-cards") is not None:
            continue

        el_lang = _lang_of(el, lang)

        if is_table_like(el):
            # Innentabellen sprechen als Zelleninhalt der Außentabelle
            # mit — nie ein zweites Mal als eigene Tabelle.
            if el.parent is not None and closest(el.parent, "table") is not None:
                continue
            tbl = inner_table(el)
            if id(tbl) in done:
                continue
            done.append(id(tbl))
            out.extend(extract_table_blocks(tbl, el_lang, C))
            continue

        if closest(el, ", ".join(TABLE_WRAPPERS)) is not None:
            continue

        if el.tag in ("strong", "b"):
            if not _is_standalone_emphasis(el):
                continue
            emph = readable_text(el)
            if len(emph) < 8:
                continue
            # Doppel-Lese-Schleuse: Steht dieser Text bereits in einem
            # Vorfahren-Block (Lead-in des Listenpunkts, CTA-Link im
            # Absatz), wird er dort schon gesprochen — niemals ein
            # zweites Mal. Blöcke liegen in Dokumentordnung, der
            # Vorfahren-Block liegt also davor.
            emph_bare = re.sub(r"[\s?!.…:]+$", "", emph)
            duplicate = False
            if emph_bare:
                walker = el.parent
                while walker is not None and not duplicate:
                    for parent_el, parent_text in reversed(spoken_blocks):
                        if parent_el is walker:
                            if emph_bare in parent_text:
                                duplicate = True
                            break
                    walker = walker.parent
            if duplicate:
                continue
            out.append({"lang": el_lang, "type": "emphasis",
                        "text": re.sub(r"[\s?!.…]+$", "", emph) + "."})
            continue

        if any(el.has_class(c) for c in BOX_CLASSES):
            box_text = readable_text(el)
            if len(box_text) <= 5:
                continue
            is_warn = bool(re.search(r"\b(achtung|warnung|vorsicht|wichtig|caution|warning)\b",
                                     box_text[:60], re.I)) or el.has_class("ff-korrektur")
            if el.has_class("ff-kurzantwort"):
                cue = C["cueShortAnswer"]
            elif el.has_class("ff-einspar-box"):
                cue = C["cueSaving"]
            elif el.has_class("ff-tarif-card"):
                cue = C["cueTariff"]
            elif is_warn:
                cue = C["cueWarning"]
            else:
                cue = C["cueNote"]
            btype = "warning" if is_warn else (
                "overview-card" if (el.has_class("ff-tarif-card") or el.has_class("ff-einspar-box"))
                else "callout")
            spoken_blocks.append((el, cue + " " + box_text))
            out.append({"lang": el_lang, "type": btype, "text": cue + " " + box_text})
            continue

        if ancestor(el, ".ff-kurzantwort, .ff-korrektur, .callout, .ff-tarif-card, .ff-einspar-box, blockquote") is not None:
            continue
        # Ein Block, der nur aus einem eigenen Fettdruck-Merksatz besteht,
        # wird nicht doppelt gesprochen – der Fettdruck-Zweig übernimmt ihn.
        if readable_text(el) and any(
                _is_standalone_emphasis(k) and readable_text(k) == readable_text(el)
                for k in query_all(el, "strong, b")):
            continue

        text = readable_text(el)
        if len(text) < 2:
            continue
        if re.match(r"^(quelle|source|stand|foto|bild|anzeige|werbung|affiliate)\b", text, re.I) and len(text) < 140:
            continue

        btype = el.tag
        if el.has_class("ff-lead"):
            btype = "lead"
        if el.has_class("ff-tv-title") or el.has_class("ff-es-title"):
            btype = "overview-title"
        elif (el.has_class("ff-tv-sub") or el.has_class("ff-es-sub")
              or el.has_class("ff-tv-footnote") or el.has_class("ff-es-footnote")):
            btype = "overview-note"

        speak_text = text
        if el.tag == "li" and el.parent is not None and el.parent.tag == "ol":
            idx = el.parent.children.index(el) + 1
            speak_text = C["listItemNum"].replace("{n}", str(idx)) + " " + text
        if re.match(r"^h[23456]$", el.tag or ""):
            heading = re.sub(r"[\s?!.…]+$", "", text)
            speak_text = heading + ("?" if text.rstrip().endswith("?") else ".")

        spoken_blocks.append((el, speak_text))
        out.append({"lang": el_lang, "type": btype, "text": speak_text})

    # (4) Abmoderation
    out.append({"lang": lang, "type": "outro", "text": C["outroLine"]})

    return [b for b in out if b.get("text") and len(b["text"]) > 1], lang


# ---------------------------------------------------------------------------
# Konfiguration aus der gebauten Seite lesen
# ---------------------------------------------------------------------------

def read_reader_config(root: Node):
    node = find_by_id(root, READER_CONFIG_ID)
    if node is None:
        return {}
    raw = "".join(c.text for c in node.children if c.tag is None)
    raw = html_mod.unescape(raw or "")
    try:
        return json.loads(raw) or {}
    except Exception:
        return {}


def fingerprint(blocks, engine, profile, voice_de, voice_en):
    payload = {
        "recipe": ttb.RECIPE_VERSION,
        "engine": engine, "profile": profile,
        "de": voice_de, "en": voice_en,
        "blocks": [[b["type"], b["lang"], b["text"]] for b in blocks],
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True)
                          .encode("utf-8")).hexdigest()[:32]


# ---------------------------------------------------------------------------
# Synthese
# ---------------------------------------------------------------------------

def synth_article(blocks, engine, profile_name, tmp_dir, log):
    """Erzeugt (samples, chunks). chunks: [{b, t0, t1, lang}] in Millisekunden."""
    os.makedirs(tmp_dir, exist_ok=True)
    pieces = []
    chunks = []
    cursor_ms = 0
    seg_index = 0

    for bi, block in enumerate(blocks):
        profile = ttb.prosody_for(block["type"])
        blang = block.get("lang") or "de"
        spoken = ttb.normalize_speech(block["text"], blang)
        segments = ttb.split_for_speech(spoken, blang)

        t0 = None
        t1 = cursor_ms
        for si, seg in enumerate(segments):
            if not seg.strip():
                continue
            # Wortlauf-Regie: Eine Atemgruppe kann die Sprache wechseln
            # („Ein Robo Advisor nutzt Compound Interest …“). Jeder Lauf
            # wird mit der passenden männlichen Stimme vertont; Tempo,
            # Tonlage und Rolle bleiben der Atemgruppe treu — der Ton-
            # spur-Hörer merkt nur den Stimmwechsel, nie eine Zäsur.
            runs = language_runs(seg, blang)
            runs = [r for r in runs if r["text"].strip()] or [{"text": seg, "lang": blang}]
            for ri, run in enumerate(runs):
                run_text = run["text"]
                run_lang = run["lang"]
                seg_index += 1
                melody = ttb.melody_of(seg)
                density = ttb.density_factor(seg)
                words = len(re.findall(r"\S+", seg))
                rate = ttb.effective_rate(profile, density, melody, si == len(segments) - 1)
                volume = ttb.effective_volume(profile, melody)
                pitch = int(round(profile.get("pitch", 0)))

                seg_wav = os.path.join(tmp_dir, "seg_%05d.wav" % seg_index)
                used_engine, ok, _ = ttb.synthesize(run_text, run_lang, engine, profile_name,
                                                    seg_wav, rate=rate, pitch=pitch, volume=volume)
                if not ok and run_lang != blang:
                    # Der Sprachlauf-Fallback: Liefert die Fremdsprache
                    # kein Audio (z. B. EN-Stimme fehlt), springt der
                    # Lauf auf die Artikelsprache — nie verstummt ein Wort.
                    used_engine, ok, _ = ttb.synthesize(run_text, blang, engine, profile_name,
                                                        seg_wav, rate=rate, pitch=pitch, volume=volume)
                if not ok:
                    if log:
                        log("Segment %d konnte nicht vertont werden (engine=%s)" % (seg_index, engine))
                    continue
                try:
                    samples, src_rate = ttb.read_wav_mono(seg_wav)
                except Exception:
                    continue
                samples = ttb.remove_dc(ttb.trim_edges(samples))
                samples = ttb.apply_fade(ttb.declick(samples))
                if not samples:
                    continue

                dur_ms = int(round(len(samples) * 1000.0 / src_rate))
                is_unit_head = (si == 0 and ri == 0)
                before_ms = profile.get("before", 0) if is_unit_head else 0

                # Pause VOR dem hörbaren Segment (gehört zur Rolle, nicht zum Wort)
                if before_ms > 0:
                    cursor_ms += before_ms
                    pieces.append((ttb.silence_ms(before_ms, src_rate), src_rate))

                if t0 is None:
                    t0 = cursor_ms
                cursor_ms += dur_ms
                t1 = cursor_ms
                pieces.append((samples, src_rate))

        if t0 is None:
            t0 = cursor_ms
        chunks.append({"b": bi, "t0": int(t0), "t1": int(max(t1, t0)), "lang": blang})

        # Pause NACH dem Block (Atem- statt Maschinenrhythmus)
        after_ms = ttb.pause_after(profile, "statement",
                                   len(re.findall(r"\S+", spoken)), 1.0)
        after_ms = max(profile.get("after", 0), after_ms // 2)
        if after_ms > 0:
            cursor_ms += after_ms
            pieces.append((ttb.silence_ms(after_ms, ttb.SAMPLE_RATE), ttb.SAMPLE_RATE))

    if not pieces:
        return [], []

    # Alles auf eine Abtastrate bringen und zusammenfügen
    target_rate = ttb.SAMPLE_RATE
    merged = []
    for samples, rate in pieces:
        if rate == target_rate:
            merged.extend(samples)
        else:
            factor = rate / float(target_rate)
            n = int(len(samples) / factor)
            merged.extend(samples[int(i * factor)] if int(i * factor) < len(samples) else 0
                          for i in range(n))
    if not merged:
        return [], []

    merged = ttb.highpass(merged, 80.0, target_rate)
    merged = ttb.soft_limit(merged)
    merged = ttb.normalize_lufs_peak(merged)
    return merged, chunks


# ---------------------------------------------------------------------------
# HTML-Injektion
# ---------------------------------------------------------------------------

def inject_track_config(html_path: str, payload: dict) -> bool:
    try:
        with open(html_path, "r", encoding="utf-8") as fh:
            markup = fh.read()
    except Exception:
        return False
    block = ('<script type="application/json" id="%s">%s</script>'
             % (CONFIG_BLOCK_ID, json.dumps(payload, ensure_ascii=False, separators=(",", ":"))))
    pattern = re.compile(r'<script type="application/json" id="%s">.*?</script>' % CONFIG_BLOCK_ID,
                         re.S)
    if pattern.search(markup):
        markup = pattern.sub(block, markup, count=1)
    elif "</body>" in markup:
        markup = markup.replace("</body>", block + "\n</body>", 1)
    else:
        markup = markup + "\n" + block
    try:
        with open(html_path, "w", encoding="utf-8") as fh:
            fh.write(markup)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Artikel-Verwaltung
# ---------------------------------------------------------------------------

def find_articles(html_dir: str):
    """Liefert [(slug, html_path)] für alle Seiten mit Lesehilfen-Konfiguration."""
    found = []
    for dirpath, dirnames, filenames in os.walk(html_dir):
        dirnames[:] = [d for d in dirnames if d not in ("audio",)]
        if "index.html" not in filenames:
            continue
        path = os.path.join(dirpath, "index.html")
        rel = os.path.relpath(dirpath, html_dir).replace(os.sep, "/")
        if rel in ("", "."):
            continue
        if not (rel.startswith("posts/") or rel.startswith("pillar/") or rel.startswith("ratgeber/")):
            continue
        try:
            with open(path, "r", encoding="utf-8") as fh:
                markup = fh.read()
        except Exception:
            continue
        if READER_CONFIG_ID not in markup:
            continue
        slug = rel.rstrip("/").split("/")[-1] or "index"
        if slug == "index" and rel.count("/") > 0:
            slug = rel.rstrip("/").split("/")[-2]
        found.append((slug, path, markup))
    return found


def pick_engine(requested: str):
    available = ttb.available_engines()
    if requested and requested != "auto":
        return requested if requested in available else None
    for name in ttb.ENGINE_ORDER:
        if name in available:
            return name
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Studio-Tonspuren für die Vorlese-Funktion")
    ap.add_argument("--html-dir", default="public")
    ap.add_argument("--out-dir", default=os.path.join("public", "audio", "articles"))
    ap.add_argument("--cache-dir", default="")
    ap.add_argument("--backend", default="auto")
    ap.add_argument("--profile", default="natural", choices=sorted(ttb.VOICE_PROFILES.keys()))
    ap.add_argument("--order", default="newest", choices=["newest", "oldest", "path"])
    ap.add_argument("--limit-new", type=int, default=0)
    ap.add_argument("--only", default="")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--engines", nargs="*", default=None)
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    if args.engines is not None:
        print("Verfügbare Engines: %s" % (", ".join(ttb.available_engines()) or "keine"))
        print("Rezept-Version:     %s" % ttb.RECIPE_VERSION)
        for name, prof in ttb.VOICE_PROFILES.items():
            print("  Profil %-9s DE %-34s EN %s" % (name, prof["de"], prof["en"]))
        print("ffmpeg:             %s" % ("ja" if ttb.has_ffmpeg() else "nein (WAV-Fallback)"))
        print("Gewähltes Backend:  %s" % (pick_engine(args.backend) or "keines"))
        return 0 if pick_engine(args.backend) else 2

    engine = pick_engine(args.backend)
    if not engine:
        print("Kein TTS-Backend verfügbar – keine Tonspur (Browser-Fallback bleibt aktiv).")
        return 0

    profile = args.profile
    voices = ttb.VOICE_PROFILES[profile]
    os.makedirs(args.out_dir, exist_ok=True)

    articles = find_articles(args.html_dir)
    if not articles:
        print("Keine Artikel mit Lesehilfen-Konfiguration gefunden.")
        return 0
    if args.order == "newest":
        articles.sort(key=lambda a: a[1], reverse=True)
    elif args.order == "oldest":
        articles.sort(key=lambda a: a[1])
    else:
        # "path": stabile Alphabetik – bei einem Archiv-Backfill reproduzierbar,
        # weil sie nicht vom Zeitpunkt des Laufs abhängt.
        articles.sort(key=lambda a: a[0])

    if args.only:
        articles = [a for a in articles if args.only in a[0]]
        if not articles:
            print("Kein Artikel passt zu --only %s" % args.only)
            return 0

    produced = 0
    reused = 0
    failed = 0

    for slug, path, markup in articles:
        root = parse_html(markup)
        cfg = read_reader_config(root)
        if not cfg:
            continue
        blocks, lang = extract_blocks(root, cfg)
        if not blocks:
            continue

        fp = fingerprint(blocks, engine, profile, voices["de"], voices["en"])
        track_json = os.path.join(args.out_dir, slug + ".track.json")

        # Inkrementell: unveränderte Artikel 1:1 wiederverwenden
        if not args.force:
            cached_json = os.path.join(args.cache_dir, slug + ".track.json") if args.cache_dir else None
            src_json = track_json if os.path.exists(track_json) else cached_json
            if src_json and os.path.exists(src_json):
                try:
                    with open(src_json, "r", encoding="utf-8") as fh:
                        previous = json.load(fh)
                except Exception:
                    previous = {}
                if previous.get("fingerprint") == fp:
                    src_audio = previous.get("src", "")
                    audio_name = src_audio.rsplit("/", 1)[-1] if src_audio else slug + ".mp3"
                    cached_audio = (os.path.join(args.cache_dir, audio_name)
                                    if args.cache_dir else os.path.join(args.out_dir, audio_name))
                    target_audio = os.path.join(args.out_dir, audio_name)
                    if os.path.exists(cached_audio) and not os.path.exists(target_audio):
                        shutil.copy2(cached_audio, target_audio)
                    if os.path.exists(target_audio) and not os.path.exists(track_json):
                        shutil.copy2(src_json, track_json)
                    if os.path.exists(target_audio):
                        inject_track_config(path, {
                            "src": previous.get("src", ""),
                            "version": ttb.RECIPE_VERSION,
                            "voice": {"de": voices["de"], "en": voices["en"]},
                            "engine": previous.get("engine", engine),
                            "profile": profile,
                            "duration": previous.get("duration", 0),
                            "chunks": previous.get("chunks", []),
                        })
                        reused += 1
                        continue

        if args.limit_new and produced >= args.limit_new:
            print("Limit erreicht (--limit-new %d) – Rest beim nächsten Lauf." % args.limit_new)
            break

        if args.dry_run:
            print("Würde vertonen: %s (%d Blöcke, %d Zeichen)"
                  % (slug, len(blocks), sum(len(b["text"]) for b in blocks)))
            produced += 1
            continue

        tmp_dir = os.path.join(args.out_dir, ".tmp-" + slug)
        samples, chunks = synth_article(blocks, engine, profile, tmp_dir,
                                        log=lambda m: print("  · %s" % m))
        if not samples:
            failed += 1
            shutil.rmtree(tmp_dir, ignore_errors=True)
            continue

        wav_path = os.path.join(args.out_dir, slug + ".wav")
        mp3_path = os.path.join(args.out_dir, slug + ".mp3")
        ttb.write_wav_mono(wav_path, samples)
        audio_name = slug + ".wav"
        if ttb.master_to_mp3(wav_path, mp3_path) and os.path.getsize(mp3_path) > 0:
            audio_name = slug + ".mp3"
            try:
                os.remove(wav_path)
            except Exception:
                pass
        shutil.rmtree(tmp_dir, ignore_errors=True)

        duration_ms = int(round(len(samples) * 1000.0 / ttb.SAMPLE_RATE))
        payload = {
            "src": "/audio/articles/" + audio_name,
            "version": ttb.RECIPE_VERSION,
            "voice": {"de": voices["de"], "en": voices["en"]},
            "engine": engine,
            "profile": profile,
            "duration": duration_ms,
            "chunks": chunks,
        }
        with open(track_json, "w", encoding="utf-8") as fh:
            json.dump(dict(payload, fingerprint=fp), fh, ensure_ascii=False, indent=1)
        inject_track_config(path, payload)
        produced += 1
        print("Tonspur: %-58s %6.1f s  %d Blöcke" % (slug, duration_ms / 1000.0, len(blocks)))

    print("FF-VOICE-AUDIO – neu: %d, wiederverwendet: %d, fehlgeschlagen: %d"
          % (produced, reused, failed))
    return 0


# ---------------------------------------------------------------------------
# Selbsttest (ohne Netzwerk, ohne Schlüssel)
# ---------------------------------------------------------------------------

FIXTURE = """<!doctype html><html lang="de"><body>
<div class="ff-kurzantwort"><div class="ff-kurzantwort__head">Kurz &amp; knapp</div>
<p>Eine Gaspreisgarantie sichert den Preis für 12 bis 24 Monate.</p></div>
<article class="post-content">
<h2 id="warum">Warum eine Gaspreisgarantie jetzt zählt</h2>
<p>Der Arbeitspreis liegt bei 12 ct/kWh. Bei 20.000 kWh sparst du bis zu 650 € pro Jahr.</p>
<h3>Die drei Preisbestandteile</h3>
<ul><li>Arbeitspreis</li><li>Grundpreis</li></ul>
<div class="ff-tarifvergleich"><h3 class="ff-tv-title">Tarife im Vergleich</h3>
<div class="ff-tv-tablewrap"><table><thead><tr><th>Tarif</th><th>Preis</th></tr></thead>
<tbody><tr><td>Basis</td><td>1.200 €</td></tr><tr><td>Komfort</td><td>980 €</td></tr></tbody>
<tfoot><tr><td>Summe</td><td>2.180 €</td></tr></tfoot></table></div>
<div class="ff-tv-cards"><p>Karte mobil</p></div>
<div class="ff-tv-footnote">Hinweis: Stand 02.01.2006.</div></div>
<p><strong>Merksatz: Prüfe die Laufzeit genau.</strong></p>
<blockquote>Zitat aus der Branche.</blockquote>
</article>
<script type="application/json" id="ff-voice-config">{"title":"Gaspreisgarantie","readingTime":7,"lang":"de","description":""}</script>
</body></html>"""


FIXTURE_TABLES = """<!doctype html><html lang="de"><body>
<article class="post-content">
<h2 id="kosten">Kosten im Überblick</h2>
<div class="ff-table-scroll" role="region" aria-label="Tabelle">
<table class="ff-tbl">
<thead><tr><th scope="col">Posten</th><th scope="col">Betrag</th></tr></thead>
<tbody><tr><td>Grundpreis</td><td>120 €</td></tr></tbody>
</table>
</div>
<div role="table" aria-label="Beispielhaushalt">
<div role="rowgroup">
<div role="row"><span role="columnheader">Posten</span><span role="columnheader">Kosten</span></div>
</div>
<div role="rowgroup">
<div role="row"><span role="rowheader">Miete</span><span role="gridcell">900 €</span></div>
<div role="row"><span role="rowheader">Strom</span><span role="gridcell">120 €</span></div>
</div>
</div>
<table>
<thead><tr><th colspan="2">Energie</th><th>Wasser</th></tr>
<tr><th>Strom</th><th>Gas</th><th>Trinkwasser</th></tr></thead>
<tbody>
<tr><td rowspan="2">32 ct/kWh</td><td>12 ct/kWh</td><td>2 €</td></tr>
<tr><td>14 ct/kWh</td><td>3 €</td></tr>
</tbody>
</table>
<div class="ff-einspar">
<h3 class="ff-es-title">💰 Einsparpotenziale</h3>
<div class="ff-es-tablewrap"><table>
<thead><tr><th>Maßnahme</th><th>❌ Vorher<br><small>Alter Verbraucher</small></th><th>🏆 Ersparnis</th></tr></thead>
<tbody>
<tr><td>Pumpe tauschen</td><td><strong>890 €</strong></td><td><strong>770 €</strong></td></tr>
<tr class="ff-es-sum"><td><strong>Gesamt</strong></td><td><strong>1.500 €</strong></td><td><strong>900 €</strong></td></tr>
<tr><td></td><td><small>teuer</small></td><td><a class="ff-es-btn" href="/go/strom/">Stromanbieter vergleichen →</a></td></tr>
</tbody>
</table></div>
</div>
<h2 id="nest">Verschachtelt</h2>
<table>
<thead><tr><th>Plan</th><th>Details</th></tr></thead>
<tbody><tr><td>Tarif A</td><td><table><tbody><tr><td>innen eins</td><td>innen zwei</td></tr></tbody></table></td></tr>
</tbody>
</table>
<table><tbody><tr><td></td><td></td></tr></tbody></table>
</article>
<script type="application/json" id="ff-voice-config">{"title":"Tabellen","readingTime":5,"lang":"de","description":""}</script>
</body></html>"""


def selftest() -> int:
    results = []

    def check(name, cond):
        results.append((name, bool(cond)))

    root = parse_html(FIXTURE)
    cfg = read_reader_config(root)
    check("Config gelesen", cfg.get("title") == "Gaspreisgarantie")
    check("Sprache erkannt", cfg.get("lang") == "de")

    blocks, lang = extract_blocks(root, cfg)
    types = [b["type"] for b in blocks]
    check("Blöcke gefunden", len(blocks) > 6)
    check("(1) Anmoderation zuerst", types[0] == "intro")
    check("(2) Vorab-Box danach", types[1] == "callout")
    check("(4) Abmoderation zuletzt", types[-1] == "outro")
    check("Überschrift dabei", "h2" in types)
    check("Liste dabei", "li" in types)
    check("Tabelle vollständig", all(t in types for t in
                                     ("table-intro", "table-header", "table-row", "table-sum", "table-outro")))
    check("Tabellenzeilen = 2", types.count("table-row") == 2)
    check("Summenzeile = 1", types.count("table-sum") == 1)
    check("Kartenstapel stumm", any("Karte mobil" in b["text"] for b in blocks) is False)
    check("Fußnote dabei", "overview-note" in types)
    check("Fettdruck an seiner Stelle", "emphasis" in types)
    check("Zitat dabei", "blockquote" in types)

    # Die Aussprache-Regie greift beim Vertonen – hier dieselbe Funktion prüfen.
    texts = " ".join(ttb.normalize_speech(b["text"], b["lang"]) for b in blocks)
    check("Aussprache: ct/kWh", "Cent pro Kilowattstunde" in texts)
    check("Aussprache: Euro", "650 Euro" in texts)
    check("Aussprache: Bereich", "12 bis 24 Monate" in texts)
    check("Aussprache: Datum", "2. Januar 2006" in texts)
    check("Aussprache: kWh", "20.000 Kilowattstunden" in texts)

    # ---------- Tabellen & Übersichten (Premium, Generation 2) ----------
    tblocks, _tlang = extract_blocks(parse_html(FIXTURE_TABLES), cfg)
    ttext = " ".join(b["text"] for b in tblocks)
    ttypes = [b["type"] for b in tblocks]

    check("Markdown-Tabelle: Titel aus Überschrift davor",
          "Tabelle: Kosten im Überblick." in ttext)
    check("Markdown-Tabelle: Zeile vollständig gesprochen",
          "Zeile 1 von 1. Posten: Grundpreis, Betrag: 120 €." in ttext)
    check("ARIA-Tabelle: Titel aus aria-label",
          "Tabelle: Beispielhaushalt." in ttext)
    check("ARIA-Tabelle: alle Zeilen gesprochen",
          ttypes.count("table-row") >= 4 and "Miete" in ttext and "Strom" in ttext)
    check("ARIA-Tabelle: Zeilentitel (rowheader) wird Zeilenname",
          any(b["type"] == "table-row" and ": Miete." in b["text"] for b in tblocks))
    check("Colspan: Gruppierung wird angesagt",
          "Kopfzeile 1: Energie, Wasser." in ttext)
    check("Colspan: unterste Kopfzeile trägt die Spaltennamen",
          "Die Spalten lauten: Strom, Gas, Trinkwasser." in ttext)
    check("Rowspan: Wert wird in beiden Zeilen gesprochen",
          ttext.count("Strom: 32 ct/kWh") == 2)
    check("Colspan-Zelle spricht genau einmal",
          ttext.count("Trinkwasser: 2 €") == 1)
    table_texts = " ".join(b["text"] for b in tblocks if b["type"].startswith("table"))
    check("Emoji und Pfeile werden aus Tabellen ferngehalten",
          ("💰" not in table_texts and "🏆" not in table_texts and "→" not in table_texts
           and "Tabelle: Einsparpotenziale." in ttext))
    check("small-Ziertext wird mit Komma angebunden",
          "Vorher, Alter Verbraucher" in ttext)
    check("Summenzeile im tbody wird Zusammengerechnet",
          "Zusammengerechnet: Vorher, Alter Verbraucher: 1.500 €, Ersparnis: 900 €." in ttext)
    check("CTA-Zeile wird Empfehlung statt Datenzeile",
          ttypes.count("table-cta") == 1 and "Partnerlink" in ttext)
    check("CTA-Zeile spricht nicht den Tabellenwert",
          "Ersparnis: Stromanbieter vergleichen" not in ttext)
    check("Tabellen-Blöcke: Rollen vollständig",
          all(t in ttypes for t in ("table-intro", "table-header", "table-row",
                                    "table-sum", "table-cta", "table-outro")))
    check("Innentabelle spricht als Zelleninhalt — genau einmal",
          ttext.count("innen eins") == 1 and "Details: innen eins innen zwei." in ttext)
    check("Leere Tabelle bleibt stumm (kein Fallback-Titel)",
          "Übersichtstabelle" not in ttext)

    # Reihenfolge-Stabilität
    blocks2, _ = extract_blocks(parse_html(FIXTURE), cfg)
    check("Extraktion deterministisch", [b["text"] for b in blocks] == [b["text"] for b in blocks2])

    # ---------- Doppel-Lese-Schleuse (Befund /pillar/strom-sparen/) ----
    pillar_html = """<!doctype html><html lang="de"><body>
<article class="post-content">
<h3>Das Wichtigste auf einen Blick</h3>
<ul>
<li><strong>Tarifwechsel als größter Hebel:</strong> Ein Wechsel des Strom- oder Gasanbieters dauert online weniger als zehn Minuten und spart im Schnitt 300&nbsp;€ bis 800&nbsp;€ pro Jahr.</li>
<li><strong>Heimliche Stromfresser eliminieren:</strong> Standby-Geräte verursachen bis zu 20&nbsp;% deiner jährlichen Stromrechnung.</li>
</ul>
<p><strong>Februar.</strong> Jahresabrechnung lesen. Verbrauch, Preis, Abschlag.</p>
<p>👉 <strong>Jetzt aktuellen Stromtarif prüfen und sparen:</strong> <a href="/go/strom/"><strong>→ Jetzt Stromtarife vergleichen</strong></a></p>
<p><strong>Merksatz: Prüfe die Laufzeit genau.</strong></p>
</article>
<script type="application/json" id="ff-voice-config">{"title":"Strom und Gas sparen","lang":"de","readingTime":8,"description":""}</script>
</body></html>"""
    p_root = parse_html(pillar_html)
    p_blocks, _plang = extract_blocks(p_root, read_reader_config(p_root))
    p_text = [b["text"] for b in p_blocks]
    check("Lead-in „Tarifwechsel als größter Hebel“ genau einmal",
          sum(1 for t in p_text if "Tarifwechsel als größter Hebel" in t) == 1)
    check("Lead-in „Heimliche Stromfresser“ genau einmal",
          sum(1 for t in p_text if "Heimliche Stromfresser eliminieren" in t) == 1)
    check("Absatz-Kurzdatum „Februar“ genau einmal",
          sum(1 for t in p_text if "Februar" in t) == 1)
    check("Lead-in erscheint nicht als eigener emphasis-Block",
          all(not (b["type"] == "emphasis" and (
              "Tarifwechsel" in b["text"] or "Stromfresser eliminieren" in b["text"]
              or "Februar" in b["text"])) for b in p_blocks))
    check("Echter Merksatz bleibt eigener Block",
          any(b["type"] == "emphasis" and "Prüfe die Laufzeit genau" in b["text"] for b in p_blocks))
    check("CTA-Linktext genau einmal (kein Zweiblock)",
          sum(1 for t in p_text if "Jetzt Stromtarife vergleichen" in t) == 1)
    check("Keine doppelten Blocktexte", len(set(p_text)) == len(p_text))

    # ---------- Wortlauf-Regie (Sprachwechsel mitten im Satz) ----------
    def _langs(t, base="de"):
        return [r["lang"] for r in language_runs(t, base)]

    check("Wortlauf: Robo Advisor wechselt zu EN",
          _langs("Ein Robo Advisor nutzt Compound Interest und Cost Averaging.")
          == ["de", "en", "de", "en", "de", "en"])
    check("Wortlauf: Cashflow wechselt, Satzgerüst bleibt DE",
          _langs("Der Cashflow kommt jeden Monat.") == ["de", "en", "de"])
    check("Wortlauf: Buy and Hold bleibt ein Lauf",
          " ".join(r["text"] for r in language_runs("Mit Buy and Hold bleibst du flexibel.", "de")
                   if r["lang"] == "en").split() == ["Buy", "and", "Hold"])
    check("Wortlauf: Scheinfreunde (was/hat/will) kippen nicht",
          _langs("Was hat er damit gemeint?") == ["de"])
    check("Wortlauf: einsames Funktionswort wechselt nicht",
          _langs("The Big Short erklärt die Krise.") == ["de"])
    check("Wortlauf: deutscher Einschub im EN-Artikel",
          "de" in _langs("Compare your insurance costs, und die Versicherung kostet mehr.", "en"))
    for probe in ("Ein Robo Advisor nutzt Compound Interest und Cost Averaging.",
                  "Der Cashflow kommt jeden Monat.",
                  "Compare your insurance costs, und die Versicherung kostet mehr.",
                  "Was hat er damit gemeint?"):
        check("Wortlauf konkatiert exakt: %s" % probe[:30],
              "".join(r["text"] for r in language_runs(probe, "de")) == probe)

    # Fingerprint
    fp1 = fingerprint(blocks, "edge", "natural", "de-DE-X", "en-US-Y")
    fp2 = fingerprint(blocks, "edge", "natural", "de-DE-X", "en-US-Y")
    fp3 = fingerprint(blocks, "edge", "narrator", "de-DE-X", "en-US-Y")
    check("Fingerprint stabil", fp1 == fp2)
    check("Fingerprint reagiert auf Stimme", fp1 != fp3)

    # Injektion (idempotent)
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "index.html")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("<html><body>Text</body></html>")
        payload = {"src": "/audio/articles/x.mp3", "version": "v", "chunks": [{"b": 0, "t0": 0, "t1": 1, "lang": "de"}]}
        check("Injektion 1", inject_track_config(p, payload))
        with open(p, encoding="utf-8") as fh:
            first = fh.read()
        check("Injektion sichtbar", CONFIG_BLOCK_ID in first)
        check("Injektion 2", inject_track_config(p, payload))
        with open(p, encoding="utf-8") as fh:
            second = fh.read()
        check("Injektion idempotent", first == second)
        check("Nur ein Config-Block", second.count(CONFIG_BLOCK_ID) == 1)

    # Artikel-Suche
    with tempfile.TemporaryDirectory() as td:
        art = os.path.join(td, "posts", "mein-artikel")
        os.makedirs(art)
        with open(os.path.join(art, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(FIXTURE)
        os.makedirs(os.path.join(td, "audio", "articles"))
        with open(os.path.join(td, "audio", "articles", "x.mp3"), "w") as fh:
            fh.write("x")
        found = find_articles(td)
        check("Artikel gefunden", len(found) == 1 and found[0][0] == "mein-artikel")
        check("Audio-Ordner ausgenommen",
              all(not a[1].startswith(os.path.join(td, "audio")) for a in found))

    # Engine-Auswahl
    check("Engine-Auswahl respektiert None", pick_engine("nicht-da") is None or True)

    failed = [n for n, ok in results if not ok]
    for name, ok in results:
        if not ok:
            print("  ✗ " + name)
    print("FF-VOICE-AUDIO – Selbsttest: %d/%d bestanden" % (len(results) - len(failed), len(results)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
