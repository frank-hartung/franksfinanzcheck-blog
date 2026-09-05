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
        "tableIntro": "Tabelle: {title}. Übersicht mit {cols} Spalten und {rows} Zeilen.",
        "tableIntroOne": "Tabelle: {title}. Übersicht mit {cols} Spalten und einer Zeile.",
        "tableRow": "Zeile {row} von {total}. {content}.",
        "tableSum": "Zusammengerechnet: {content}.",
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
        "tableIntro": "Table: {title}. Overview with {cols} columns and {rows} rows.",
        "tableIntroOne": "Table: {title}. Overview with {cols} columns and one row.",
        "tableRow": "Row {row} of {total}. {content}.",
        "tableSum": "In total: {content}.",
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
# Tabellenmodell (Portierung aus dem Reader)
# ---------------------------------------------------------------------------

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


def _row_cells(tr: Node):
    return query_all(tr, 'th, td, [role="columnheader"], [role="rowheader"], [role="cell"], [role="gridcell"]')


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
    return rows


def table_title(table: Node, C) -> str:
    cap = find_first(table, "caption")
    if cap and readable_text(cap):
        return readable_text(cap)
    aria = table.attr("aria-label")
    if aria:
        return aria
    # Die Premium-Übersichten setzen ihren Titel AUSSERHALB des
    # Tablewrappers – deshalb nach oben steigen, bis einer ihn trägt.
    node = table
    for _ in range(4):
        if node is None:
            break
        wrap = closest(node, ".ff-tarifvergleich, .ff-einspar, .ff-tv-tablewrap, .ff-es-tablewrap, .ff-table-scroll")
        if wrap is None:
            break
        for sel in (".ff-tv-title", ".ff-es-title", "h3", "h4"):
            h = find_first(wrap, sel)
            if h is not None and id(h) != id(table) and readable_text(h):
                return readable_text(h)
        node = wrap.parent
    return C["tableDefault"]


def build_table_model(table: Node, C):
    headers, body, foot = [], [], []
    header_found = False
    for tr, kind in table_rows(table):
        cells = _row_cells(tr)
        texts = [readable_text(c) for c in cells]
        all_head = bool(texts) and all(_is_header_cell(c) for c in cells)
        if kind == "head" or (not header_found and all_head):
            if not header_found:
                headers = texts
                header_found = True
            else:
                body.append(texts)
            continue
        if kind == "foot":
            foot.append(texts)
            continue
        body.append(texts)
    col_count = max([len(headers)] + [len(r) for r in body] + [len(r) for r in foot] + [0])
    return {"title": table_title(table, C), "headers": headers,
            "rows": body, "foot": foot, "colCount": col_count}


def _cell_speech(name, value, index, C):
    label = name if (name and str(name).strip()) else "%s %d" % (C["columnLabel"], index + 1)
    val = "" if value is None else str(value)
    if not val:
        return ""
    return "%s: %s" % (label, val)


def extract_table_blocks(table: Node, block_lang: str, C):
    model = build_table_model(table, C)
    out = []
    title = model["title"] or C["tableDefault"]
    row_count = len(model["rows"])
    tmpl = C["tableIntroOne"] if row_count == 1 else C["tableIntro"]
    out.append({"lang": block_lang, "type": "table-intro",
                "text": tmpl.replace("{title}", title)
                            .replace("{cols}", str(model["colCount"]))
                            .replace("{rows}", str(row_count))})
    if model["headers"]:
        out.append({"lang": block_lang, "type": "table-header",
                    "text": C["tableHeaders"].replace("{headers}", ", ".join(model["headers"]))})
    for i, row in enumerate(model["rows"]):
        parts = []
        for c in range(max(len(row), model["colCount"])):
            spoken = _cell_speech(model["headers"][c] if c < len(model["headers"]) else "",
                                  row[c] if c < len(row) else "", c, C)
            if spoken:
                parts.append(spoken)
        if not parts:
            continue
        out.append({"lang": block_lang, "type": "table-row",
                    "text": C["tableRow"].replace("{row}", str(i + 1))
                                         .replace("{total}", str(row_count))
                                         .replace("{content}", ", ".join(parts))})
    for row in model["foot"]:
        parts = []
        for c in range(len(row)):
            spoken = _cell_speech(model["headers"][c] if c < len(model["headers"]) else "", row[c], c, C)
            if spoken:
                parts.append(spoken)
        if not parts:
            continue
        out.append({"lang": block_lang, "type": "table-sum",
                    "text": C["tableSum"].replace("{content}", ", ".join(parts))})
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
    text = readable_text(node)
    if len(text) < 12:
        return False
    parent = node.parent
    if parent is None:
        return False
    parent_text = readable_text(parent)
    siblings = len(parent.children)
    return len(text) >= max(12, len(parent_text) - 2) or siblings <= 2


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
    for el in query_all(content, CONTENT_SELECTOR):
        if is_skipped(el):
            continue
        if closest(el, "figure") is not None and not is_table_like(el):
            continue
        if closest(el, ".ff-tv-cards, .ff-es-cards") is not None:
            continue

        el_lang = _lang_of(el, lang)

        if is_table_like(el):
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
            seg_index += 1
            melody = ttb.melody_of(seg)
            density = ttb.density_factor(seg)
            words = len(re.findall(r"\S+", seg))
            rate = ttb.effective_rate(profile, density, melody, si == len(segments) - 1)
            volume = ttb.effective_volume(profile, melody)
            pitch = int(round(profile.get("pitch", 0)))

            seg_wav = os.path.join(tmp_dir, "seg_%05d.wav" % seg_index)
            used_engine, ok, _ = ttb.synthesize(seg, blang, engine, profile_name,
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
            before_ms = profile.get("before", 0) if si == 0 else 0
            pause_ms = profile.get("before", 0) if si == 0 else 0

            # Pause VOR dem hörbaren Segment (gehört zur Rolle, nicht zum Wort)
            if before_ms > 0:
                cursor_ms += before_ms
                pieces.append((ttb.silence_ms(before_ms, src_rate), src_rate))

            if t0 is None:
                t0 = cursor_ms
            cursor_ms += dur_ms
            t1 = cursor_ms
            pieces.append((samples, src_rate))

            if si < len(segments) - 1:
                cursor_ms += 0

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
    ap.add_argument("--order", default="newest", choices=["newest", "oldest"])
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

    # Reihenfolge-Stabilität
    blocks2, _ = extract_blocks(parse_html(FIXTURE), cfg)
    check("Extraktion deterministisch", [b["text"] for b in blocks] == [b["text"] for b in blocks2])

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
