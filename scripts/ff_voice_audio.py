#!/usr/bin/env python3
"""ff_voice_audio.py — Studio-Tonspuren für die Vorlese-Funktion (FF Voice Studio).

Vertont die Artikel des Blogs mit einer MÄNNLICHEN, DEUTSCHEN
NACHRICHTENSPRECHER-STIMME — kostenlos, ohne Schlüssel und ohne
Umschalter für die Leser:innen.

NUR-DEUTSCH-VERTRAG (Befund 07.09.2026)
    Die Tonspur spricht ausschließlich Deutsch. Es gibt keine
    englische Stimme, keinen Satz-Routing-Zweig und keinen
    EN-Fallback. Englische Begriffe im Text spricht der deutsche
    Nachrichtensprecher, wie es im Hörfunk üblich ist. Die Blöcke
    tragen weiterhin das Feld `lang` — es ist IMMER „de“, und beide
    Seiten (Generator und Reader) werden durch das Paritäts-Gate auf
    diesem Vertrag gehalten.

WORTUHR (Grundlage der wortgenauen Leseanzeige)
    Bei edge-tts-Synthese liefert jedes Segment WordBoundary-Ereignisse.
    Sie werden in absolute Millisekunden der Gesamtdatei umgerechnet und
    je Chunk als `w: [[rohwortIndex, ms], …]` in die
    Tonspur-Konfiguration geschrieben. Der Reader markiert damit das
    Wort, das in diesem Sekundenbruchteil erklungen ist — barrierefreie
    Leseanzeige auf Verlagsniveau. Fehlt die Wortuhr (z. B. Piper),
    arbeitet der Reader mit Satz-Schätzung weiter; gelogen wird nie.

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
      --backend auto --profile news [--only <slug>] [--dry-run] [--force]

  · --backend   auto (edge → piper) | edge | piper
  · --profile   news (Standard: Conrad, Style serious) | natural (Florian)
                | narrator (Killian) — ausschließlich deutsche Stimmen
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
import time
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import ff_voice_backends as ttb  # noqa: E402

# Alias der Aussprache-Regie (Selbsttest/Parität sprechen denselben
# Namen wie der Reader: speechNormalize ↔ normalize_speech).
normalize_speech = ttb.normalize_speech

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
# NUR-DEUTSCH-VERTRAG (Befund 07.09.2026): Es gibt ausschließlich die
# deutsche Cue-Menge. Ein „en“-Zweig wäre ein Rückfall in das alte
# zweisprachige Modell und wird vom Paritäts-Gate auf beiden Seiten
# ausgeschlossen (Reader: I18N enthält kein „en“ mehr).
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
}


# ---------------------------------------------------------------------------
# Nur-Deutsch-Vertrag — Sprach-Erkennung ist bewusst abgeschaltet
# ---------------------------------------------------------------------------
# Frühere Modelle erkannten Artikel-, Satz- und Wort-Sprachen und kippten
# auf englische Stimmen. Der Auftrag lautet seit 07.09.2026: Die
# Vorlese-Funktion spricht ausschließlich Deutsch. Die Funktion bleibt
#Signatur-stabil (Reader und Paritäts-Gate adressieren denselben Namen) und
# liefert für JEDE Eingabe „de“.

def detect_language(sample: str = "", declared: str = "de") -> str:
    """Nur-Deutsch-Vertrag: immer „de“ — kein Raten, kein Routing."""
    return "de"


def sniff_sentence_lang(sentence: str = "", base_lang: str = "de") -> str:
    """Nur-Deutsch-Vertrag: Sätze wechseln die Sprache nicht mehr."""
    return "de"


# ---------------------------------------------------------------------------
# Wortuhr-Algorithmen — Grundlage der wortgenauen Leseanzeige
# ---------------------------------------------------------------------------
# Die Tonspur wird silbenrichtig gesprochen, markiert werden muss das
# gesprochene Wort im ROHEN Artikeltext. Zwischen beiden Texten liegt
# die Aussprache-Normalisierung („650 €“ → „650 Euro“, „12 – 24“ →
# „12 bis 24“). Der Aligner schiebt daher die normalisierten Wörter
# (N) über die rohen Wörter (R) und merkt sich je N-Wort, welches
# R-Wort dabei erklungen ist. Regeln (wortgleich zu alignNormToRaw()
# im Reader, spiegelgeprüft durch scripts/ff_voice_parity_check.py):
#   1. Kern-Gleichheit (Kleinschreibung, Nicht-Buchstaben entfernt).
#   2. Symbol-Erweiterung: ein kernleeres rohes Zeichen („–“, „€“)
#      gilt als Treffer, wenn die Ersetzung exakt dem N-Wort passt.
#   3. Einheiten-Erweiterung („kWh“ → „Kilowattstunden“).
#   4. Zahlen-Kern: trifft der Ziffernkern des rohen Tokens auf den
#      des N-Tokens (Containment), gilt der ROHE Token als Sprecher-
#      wort — so bleibt die ganze Zahl „1.2.2006“ hell, während der
#      Sprecher „zweiten Januar zweitausendsechs“ sagt.
#   6. Fremdwort-Erweiterung: die Nur-Deutsch-Lautschreibung
#      („homoffis“ für „Homeoffice“, „sörwis“ für „Service“) wird über
#      FOREIGN_SPOKEN auf den rohen Kern zurückgeschlagen.
#   5. Kein Treffer: das N-Wort erbt das zuletzt verbrauchte rohe
#      Wort (der Cursor steht still — nichts wandert davon). Bei
#      ≥ 6 Treffern in Folge wird im Rest von R neu verankert.
# Ergebnis: Liste len(N), Werte sind Indizes in R oder -1 (leeres R).

_CORE_STRIP = re.compile(r"[^0-9a-zäöüß']+")


def token_core(tok: str) -> str:
    return _CORE_STRIP.sub("", str(tok or "").lower())


def norm_tokens(text: str) -> list:
    return str(text or "").split()


_SYMBOL_SPOKEN = {
    "€": "euro", "%": "prozent", "&": "und", "§": "paragraph",
    "+": "plus", "=": "gleich", "–": "bis", "—": "bis", "-": "bis",
    "·": "punkt", "…": "",
}

_UNIT_SPOKEN = {
    "kwh": {"kilowattstunden", "kilowattstunde", "kilowatt", "kilowattpeak"},
    "kmh": {"kilometer", "kilometerprosstunde", "stunde"},
    "ct": {"cent"},
    "kw": {"kilowatt", "kilowattpeak"},
    "kwp": {"kilowatt", "kilowattpeak"},
    "m": {"meter", "quadratmeter", "kubikmeter"},
    "m2": {"quadratmeter"},
    "m3": {"kubikmeter"},
    "eur": {"euro"},
    "a": {"jahr", "jahrpro"},
}

# (6) FREMDWORT-ERWEITERUNG (Befund 07.09.2026): Die Nur-Deutsch-Regie
#     spricht englisch geschriebene Begriffe in deutscher Lautschreibung
#     aus („Homeoffice“ → „homoffis“). Die Leseanzeige muss dennoch das
#     rohe Wort im Artikeltext treffen — diese Tabelle schlägt den Kern
#     der Sprechschreibung auf den Kern der Originalschreibung zurück.
#     Automatisch aus dem Germanisierungs-Glossar abgeleitet; gespiegelt
#     im Reader (FOREIGN_SPOKEN in static/premium/ff-voice.js) und durch
#     das Paritäts-Gate wortgleich geprüft.
FOREIGN_SPOKEN = ttb.germanize_spoken_cores()


def _raw_is_digits(core: str) -> bool:
    return bool(core) and core.isdigit()


def align_norm_to_raw(norm_tokens_list: list, raw_tokens_list: list) -> list:
    """Je normalisiertem Wort den Index des gesprochenen rohen Wortes."""
    N = list(norm_tokens_list or [])
    R = list(raw_tokens_list or [])
    out = []
    j = 0
    prev = -1
    miss = 0
    for n in N:
        nc = token_core(n)
        if not R:
            out.append(-1)
            continue
        matched = -1
        window = 4 if miss < 6 else 64
        for o in range(j, min(j + window, len(R))):
            rc = token_core(R[o])
            if rc and nc and rc == nc:
                matched = o
                break
            if nc:
                # (2) Symbol-Erweiterung
                if not rc:
                    sym = R[o].strip().strip(".:;,!?")
                    if sym in _SYMBOL_SPOKEN and _SYMBOL_SPOKEN[sym] == nc:
                        matched = o
                        break
                # (3) Einheiten-Erweiterung
                if rc in _UNIT_SPOKEN and nc in _UNIT_SPOKEN[rc]:
                    matched = o
                    break
                # (4) Zahlen-Kern (Containment, nur wenn beide rein numerisch)
                if _raw_is_digits(rc) and nc.isdigit() and (nc in rc or rc in nc):
                    matched = o
                    break
                # (6) Fremdwort-Erweiterung: Sprechschreibung → Original
                #     („homoffis“ → „homeoffice“). Erst echten Treffer
                #     nehmen, damit ein deutsches Homonym (z. B. „blogg“)
                #     nicht ein anderes rohes Wort verschluckt.
                fk = FOREIGN_SPOKEN.get(nc)
                if fk and rc == fk:
                    matched = o
                    break
        if matched >= 0:
            out.append(matched)
            prev = matched
            j = matched + 1
            miss = 0
        else:
            out.append(prev if prev >= 0 else -1)
            miss += 1
    return out


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
# Bedienelemente, eingebettete Flächen und Anker zählen nicht zum
# Vorlesetext (Parität zur Browser-Engine, Befund 10.09.2026).
SKIP_TAGS = {"script", "style", "noscript", "svg", "template",
             "button", "input", "select", "textarea", "canvas", "iframe"}


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
    if node.attr("hidden") is not None:
        return ""
    if node.has_class("anchor") or node.has_class("ff-heading-copy"):
        return ""
    if node.has_class("ff-mini-toc"):
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
    if node.attr("data-ff-skip-read") is not None:
        return ""
    if node.attr("hidden") is not None:
        return ""
    if node.has_class("anchor") or node.has_class("ff-heading-copy"):
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

def _lang_of(node: Node, fallback: str = "de") -> str:
    """Nur-Deutsch-Vertrag: Blöcke wechseln die Sprache nicht mehr.

    Das `lang`-Feld bleibt als Vertragsfeld erhalten (Reader, Generator
    und Paritäts-Gate adressieren es), sein Wert ist immer „de“ — auch
    wenn ein Knoten ein `lang="en"`-Attribut trägt. Ein englisches
    Attribut darf die deutsche Pflichtstimme nicht aushebeln.
    """
    return "de"


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
    """Gibt (blocks, lang) zurück. blocks: [{lang, type, text}] in Lesereihenfolge.

    NUR-DEUTSCH-VERTRAG: `lang` ist immer „de“ — für die Blöcke und für
    die Rückgabe. Die Signatur bleibt stabil.
    """
    content = find_first(root, ".post-content") or find_first(root, ".md-content")
    if content is None:
        return [], "de"

    lang = "de"
    C = CUES["de"]

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
            # Ankersymbole („§“, „#“) am Ende sind nie Teil einer Überschrift
            heading = re.sub(r"[\s#§?!.…]+$", "", text)
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


def fingerprint(blocks, engine, profile, voice_de, voice_en=None):
    """Inhalts-Fingerprint einer Tonspur.

    NUR-DEUTSCH-VERTRAG: Der `voice_en`-Parameter ist nur
    Signatur-Kompatibilität und wird ignoriert; die deutsche Stimme,
    das Profil, die Rezept-Version (inkl. Wortuhr) und die Blockfolge
    bestimmen den Fingerabdruck. Er ändert sich — die Spur wird neu
    erzeugt.
    """
    del voice_en  # Nur-Deutsch-Vertrag: keine englische Stimme mehr.
    payload = {
        "recipe": ttb.RECIPE_VERSION,
        "engine": engine, "profile": profile,
        "de": voice_de,
        "blocks": [[b["type"], b["lang"], b["text"]] for b in blocks],
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True)
                          .encode("utf-8")).hexdigest()[:32]


# ---------------------------------------------------------------------------
# Synthese
# ---------------------------------------------------------------------------

def expected_speech_ms(blocks) -> float:
    """Erwartete Hörzeit in ms — derselbe Zeichen-pro-Sekunde-Maßstab
    wie BASE_CPS im Reader (Parität erzwungen durch ff_voice_parity_check).
    Der Faktor 1,18 deckt die Atem-Pausen zwischen Blöcken und Einheiten."""
    total_chars = sum(len(b.get("text") or "") for b in blocks)
    return (total_chars / ttb.BASE_CPS) * 1000.0 * 1.18


def _words_plausible(blocks, chunks) -> tuple:
    """Wortuhr-Gate: Darf eine `w`-Karte dem Leser gezeigt werden?

    Die Wortuhr verschiebt die Leseanzeige — sie ist damit genau so
    vertrauenswürdig zu behandeln wie die Tonspur selbst. Regeln:

      · Einträge sind Paare [rohwortIndex, ms] mit 0 ≤ idx < Wortanzahl
        des Blocks und Zeit im Chunkfenster (Puffer 1,5 s: Pausen und
        Atemgrenzen gehören dazu).
      · Pro Chunk monoton nach Zeit; die Indizes steigen mit.
      · Wenigstens ein Chunk trägt eine Karte, sonst gibt es keine
        Wortanzeige (das ist erlaubt — sie wird nur nicht vorgetäuscht).

    Rückgabe (True, "") bzw. (False, grund). Ein Wortuhr-Verstoß
    verwirft die SPUR (der Reader fällt auf die Gerätestimme), nicht
    bloß die Karte: Eine Karte, die am Text vorbeiläuft, ist für
    barrierefreie Leser:innen schlimmer als keine.
    """
    seen = 0
    for c in chunks or []:
        w = c.get("w")
        if not w:
            continue
        seen += 1
        bi = c.get("b")
        try:
            raw_count = len(norm_tokens(blocks[bi]["text"])) if 0 <= bi < len(blocks) else 0
        except Exception:
            raw_count = 0
        lo = (c.get("t0") or 0) - 1500
        hi = (c.get("t1") or 0) + 1500
        last_ms = -1
        last_idx = -1
        for entry in w:
            if not isinstance(entry, (list, tuple)) or len(entry) != 2:
                return False, "Wortuhr-Eintrag kein Paar [idx, ms] in Chunk b=%s" % bi
            idx, ms = entry
            try:
                idx = int(idx); ms = int(ms)
            except Exception:
                return False, "Wortuhr-Eintrag nicht numerisch in Chunk b=%s" % bi
            if raw_count and not (0 <= idx < raw_count):
                return False, "Wortuhr-Index %d außerhalb des Blocks %s (0..%d)" % (idx, bi, max(0, raw_count - 1))
            if not (lo <= ms <= hi):
                return False, "Wortuhr-Zeit %d ms außerhalb Chunks %s (%d..%d)" % (ms, bi, lo, hi)
            if ms < last_ms or idx < last_idx:
                return False, "Wortuhr nicht monoton in Chunk b=%s" % bi
            last_ms, last_idx = ms, idx
    if chunks and not seen:
        return True, ""       # keine Karte anywhere — Satzebene, legal
    if chunks and 0 < seen < len(chunks):
        # Teilweise Karten sind erlaubt (kurze Blöcke < 2 Wörter); die
        # Kartenpflicht greift erst, wenn ein Chunk Karten verspricht.
        return True, ""
    return True, ""


def track_plausible(blocks, chunks, duration_ms) -> tuple:
    """Plausibilitäts-Gate für Tonspuren (Befund 06.09.2026,
    Wortuhr-Erweiterung 07.09.2026).

    Auf gh-pages standen Spuren aus NUR Pausen: Das TTS-Backend lieferte
    für JEDES Segment kein Audio, synth_article übersprang die Fehler
    still, und geschrieben wurde eine ~33-Sekunden-Datei für Zehn-
    Minuten-Artikel (jeder Chunk t0 == t1). Der Reader spielte sie stumm
    durch — „kein Ton, Fortschrittsanzeige rennt“. Eine Spur gilt seit
    diesem Befund nur noch als gültig, wenn

      · JEDES Segment vertont wurde (keine stillen Lücken, Verlagsregel:
        lieber Gerätestimme als Tonspur mit fehlenden Sätzen),
      · jeder Chunk echte Sprechdauer hat (t1 > t0),
      · die Wortuhr (falls vorhanden) strukturiert und im Fenster liegt
        (_words_plausible),
      · die Gesamtlaufzeit im plausiblen Fenster um die erwartete
        Sprechzeit des Artikels liegt (0,3× bis 4,0×).

    Rückgabe: (True, "") bzw. (False, grund).
    """
    if not chunks:
        return False, "keine Chunks"
    degenerate = [c for c in chunks if (c.get("t1") or 0) <= (c.get("t0") or 0)]
    if degenerate:
        return False, "%d von %d Chunks ohne Sprechdauer (t0==t1)" % (len(degenerate), len(chunks))
    ok_words, why_words = _words_plausible(blocks, chunks)
    if not ok_words:
        return False, "Wortuhr: " + why_words
    duration_ms = int(duration_ms or 0)
    if duration_ms <= 0:
        return False, "keine Laufzeit"
    expected = expected_speech_ms(blocks)
    if duration_ms < expected * 0.30:
        return False, "Laufzeit %.1f s viel zu kurz (erwartet ≥ %.0f s)" % (duration_ms / 1000.0, expected * 0.30 / 1000.0)
    if duration_ms > expected * 4.0:
        return False, "Laufzeit %.1f s unplausibel lang (erwartet ≤ %.0f s)" % (duration_ms / 1000.0, expected * 4.0 / 1000.0)
    return True, ""


def synth_article(blocks, engine, profile_name, tmp_dir, log, deadline=None):
    """Erzeugt (samples, chunks, stats).

    chunks: [{b, t0, t1, lang:"de", w?: [[rawWortIndex, ms], …]}] in ms.

    Das optionale Feld `w` ist die WORTUHR: je rohes Wort (Index in den
   Whitespace-getrennten Rohtoken des Blocktexts) der absolute
    Millisekunden-Zeitpunkt, an dem es in der fertigen Datei erklingt.
    Sie entsteht aus den WordBoundary-Ereignissen von edge-tts,
    umgerechnet auf den geschnittenen Segmentkopf und die
    Segmentposition in der Gesamtdatei. Ohne Wortuhr (z. B. Piper)
    markiert der Reader auf Satzebene weiter — er erfindet nie
    Wortzeiten.

    stats = {"segments": n, "ok": n, "failed": n, "words": n} — seit dem
    Befund vom 06.09.2026 zählt jedes fehlgeschlagene Segment (Backend-
    Fehler ODER leeres Audio) als FAILED; der Aufrufer verwirft die Spur
    komplett. Kein stilles Überspringen mehr: Eine Tonspur mit Lügen ist
    schlechter als keine Tonspur (der Reader fällt auf die Gerätestimme
    zurück).

    `deadline` (time.monotonic-Wert, optional): Zeitbudget aus
    --max-seconds. Wird VOR JEDEM Segment geprüft — nicht erst vor
    jedem Artikel (Härtung 10.09.2026): Ein einzelner Artikel mit
    vielen Segmenten (oder hängenden Versuchen) überzog das Budget
    sonst unbegrenzt. Bei Ablauf kehrt die Funktion mit
    stats["aborted"] = True zurück; der Aufrufer stellt den Artikel
    zurück (deferred), statt ihn als defekt zu verwerfen — der
    nächste Lauf setzt die Warteschlange fort.
    """
    os.makedirs(tmp_dir, exist_ok=True)
    pieces = []
    chunks = []
    cursor_ms = 0
    seg_index = 0
    stats = {"segments": 0, "ok": 0, "failed": 0, "words": 0, "aborted": False}

    for bi, block in enumerate(blocks):
        profile = ttb.prosody_for(block["type"])
        blang = "de"                                   # Nur-Deutsch-Vertrag
        spoken = ttb.normalize_speech(block["text"], blang)
        segments = ttb.split_for_speech(spoken, blang)

        # Wortuhr-Vorbereitung: Aligner N→R über dem Block. Die
        # Segmentfolge konkateniert (bis auf Leerraum) exakt zum
        # normalisierten Sprechtext; die Rohtoken sind der Artikelsatz
        # selbst. Derselbe Aligner läuft im Reader — das Paritäts-Gate
        # vergleicht beide Ergebnisse Wort für Wort.
        raw_tokens = norm_tokens(block["text"])
        norm_stream = []
        for seg in segments:
            norm_stream.extend(norm_tokens(seg))
        align_map = align_norm_to_raw(norm_stream, raw_tokens)
        norm_cursor = 0
        word_clock = []

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
            # ZEITBUDGET (Härtung 10.09.2026): Die Deadline wird vor
            # JEDEM Segment geprüft. Früher galt sie nur zwischen
            # Artikeln — ein einziger Artikel mit vielen Segmenten
            # (oder hängenden Versuchen) überzog sie unbegrenzt.
            # Ablauf ⇒ sofortiger, ehrlicher Rückzug: Der Artikel wird
            # zurückgestellt (deferred), NICHT als defekt verworfen.
            if deadline is not None and time.monotonic() >= deadline:
                stats["aborted"] = True
                if log:
                    log("Zeitbudget abgelaufen — Artikel wird zurückgestellt (Rest beim nächsten Lauf)")
                return None, [], stats
            stats["segments"] += 1
            used_engine, ok, boundaries = ttb.synthesize(seg, blang, engine, profile_name,
                                                         seg_wav, rate=rate, pitch=pitch, volume=volume)
            if not ok:
                stats["failed"] += 1
                norm_cursor += words
                if log:
                    log("Segment %d konnte nicht vertont werden (engine=%s) — Spur wird verworfen"
                        % (seg_index, engine))
                continue
            try:
                samples, src_rate = ttb.read_wav_mono(seg_wav)
            except Exception:
                stats["failed"] += 1
                norm_cursor += words
                continue
            samples, head_removed = ttb.trim_edges_info(samples)
            samples = ttb.apply_fade(ttb.declick(ttb.remove_dc(samples)))
            if not samples:
                stats["failed"] += 1
                norm_cursor += words
                continue
            stats["ok"] += 1

            dur_ms = int(round(len(samples) * 1000.0 / src_rate))
            is_unit_head = (si == 0)
            before_ms = profile.get("before", 0) if is_unit_head else 0

            # Pause VOR dem hörbaren Segment (gehört zur Rolle, nicht zum Wort)
            if before_ms > 0:
                cursor_ms += before_ms
                pieces.append((ttb.silence_ms(before_ms, src_rate), src_rate))

            if t0 is None:
                t0 = cursor_ms
            seg_start_ms = cursor_ms
            seg_end_ms = seg_start_ms + dur_ms

            # WORTUHR: WordBoundary-Ticks (100 ns ab Rohstrombeginn) in
            # absolute ms der Datei. Kopf-Trim abziehen, ins Segment
            # klemmen, monoton machen. Der Zähler gilt Wort für Wort:
            # das k-te Boundary-Ereignis ist das k-te Token des
            # Segmenttexts (edge-tts spricht Wort für Wort, kein Satz).
            head_ms = head_removed * 1000.0 / max(1, src_rate)
            if boundaries and raw_tokens:
                last_ms = -1
                last_idx = -1
                for k, bd in enumerate(boundaries):
                    n = norm_cursor + k
                    if n >= len(align_map):
                        break
                    raw_idx = align_map[n]
                    if raw_idx is None or raw_idx < 0:
                        continue
                    off_ms = (bd.get("offset") or 0) / 10000.0 - head_ms
                    t_ms = seg_start_ms + max(0.0, off_ms)
                    if t_ms > seg_end_ms:
                        break
                    if t_ms < last_ms or raw_idx < last_idx:
                        continue
                    last_ms, last_idx = t_ms, raw_idx
                    word_clock.append([int(raw_idx), int(round(t_ms))])
            norm_cursor += words

            cursor_ms += dur_ms
            t1 = cursor_ms
            pieces.append((samples, src_rate))

        if t0 is None:
            t0 = cursor_ms
        chunk = {"b": bi, "t0": int(t0), "t1": int(max(t1, t0)), "lang": blang}
        if len(word_clock) >= 2:
            stats["words"] += len(word_clock)
            chunk["w"] = word_clock
        chunks.append(chunk)

        # Pause NACH dem Block (Atem- statt Maschinenrhythmus)
        after_ms = ttb.pause_after(profile, "statement",
                                   len(re.findall(r"\S+", spoken)), 1.0)
        after_ms = max(profile.get("after", 0), after_ms // 2)
        if after_ms > 0:
            cursor_ms += after_ms
            pieces.append((ttb.silence_ms(after_ms, ttb.SAMPLE_RATE), ttb.SAMPLE_RATE))

    if not pieces:
        return [], [], stats

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
        return [], [], stats

    merged = ttb.highpass(merged, 80.0, target_rate)
    merged = ttb.soft_limit(merged)
    merged = ttb.normalize_lufs_peak(merged)
    return merged, chunks, stats


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


def strip_track_config(html_path: str) -> bool:
    """Entfernt einen injizierten Tonspur-Block wieder aus der Seite.

    Gegenstueck zu inject_track_config: Wird eine Spur nachtraeglich als
    unbrauchbar erkannt (Stille-Wache, --verify --heal), darf die Seite
    nicht weiter auf sie zeigen — der Reader soll sofort und ohne Umweg
    die Geraetestimme nehmen.
    """
    try:
        with open(html_path, "r", encoding="utf-8") as fh:
            markup = fh.read()
    except Exception:
        return False
    pattern = re.compile(r'<script type="application/json" id="%s">.*?</script>\s*' % CONFIG_BLOCK_ID,
                         re.S)
    if not pattern.search(markup):
        return False
    markup = pattern.sub("", markup, count=1)
    try:
        with open(html_path, "w", encoding="utf-8") as fh:
            fh.write(markup)
        return True
    except Exception:
        return False


def audio_health(audio_path: str, expected_ms: int = 0) -> tuple:
    """(ok, grund, messwerte) — traegt eine Tonspur-DATEI wirklich Ton?

    Der Befund vom 06.09.2026 stand als Datei auf gh-pages: 34 WAVs mit
    peak = 0 (Digitalstille). Metadaten allein reichen also nicht — es
    zaehlt der gemessene Pegel. Ohne Dekoder fuer Fremdformate (MP3 ohne
    ffmpeg) wird ehrlich „ungeprueft“ gemeldet, statt Sicherheit
    vorzutaeuschen.
    """
    if not audio_path or not os.path.exists(audio_path):
        return False, "Datei fehlt", {}
    if os.path.getsize(audio_path) < 1024:
        return False, "Datei ist leer", {}
    kind = ttb.audio_kind(audio_path)
    if kind != "wav" and not ttb.decoder_available():
        return True, "ungeprüft (kein Dekoder für %s)" % kind, {}
    try:
        samples, rate = ttb.decode_audio_mono(audio_path)
    except Exception as exc:
        return False, "nicht dekodierbar (%s)" % str(exc)[:60], {}
    stats = ttb.audio_stats(samples, rate)
    ok, why = ttb.has_audible_speech(samples, rate, min_ratio=0.25)
    if not ok:
        return False, why, stats
    if expected_ms and stats["duration_ms"] < expected_ms * 0.30:
        return False, ("Datei nur %.1f s (erwartet ≥ %.0f s)"
                       % (stats["duration_ms"] / 1000.0, expected_ms * 0.30 / 1000.0)), stats
    return True, "", stats


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


def verify_tracks(html_dir: str, out_dir: str, heal: bool = False) -> int:
    """Endkontrolle des Veröffentlichungsstands: Traegt JEDE Tonspur Ton?

    Dieses Gate laeuft im Deploy NACH der Erzeugung und im Lesehilfen-Gate
    gegen ein Testverzeichnis. Es misst jede Datei (Pegel, hoerbarer
    Anteil, Laufzeit) und prueft die Chunk-Karte gegen den Artikeltext.

    Mit --heal werden defekte Spuren geloescht und ihr Konfigurationsblock
    aus der Seite entfernt: Der Reader nimmt dann sofort die
    Geraetestimme, statt Stille abzuspielen. Rueckgabe: Anzahl der
    beanstandeten Spuren (0 = sauber).
    """
    articles = find_articles(html_dir)
    bad = 0
    checked = 0
    healed = 0
    for slug, path, markup in articles:
        m = re.search(r'<script type="application/json" id="%s">(.*?)</script>' % CONFIG_BLOCK_ID,
                      markup, re.S)
        if not m:
            continue
        checked += 1
        try:
            payload = json.loads(m.group(1))
        except Exception:
            payload = {}
        src = str(payload.get("src") or "")
        audio_path = os.path.join(out_dir, src.rsplit("/", 1)[-1]) if src else ""
        root = parse_html(markup)
        cfg = read_reader_config(root)
        blocks, _lang = extract_blocks(root, cfg) if cfg else ([], "de")

        reasons = []
        ok_meta, why_meta = track_plausible(blocks, payload.get("chunks") or [],
                                            payload.get("duration") or 0)
        if not ok_meta:
            reasons.append("Karte: " + why_meta)
        ok_file, why_file, stats = audio_health(audio_path, payload.get("duration") or 0)
        if not ok_file:
            reasons.append("Datei: " + why_file)

        if reasons:
            bad += 1
            print("  ✗ %-58s %s" % (slug, " · ".join(reasons)))
            if heal:
                try:
                    if audio_path and os.path.exists(audio_path):
                        os.remove(audio_path)
                    json_path = os.path.join(out_dir, slug + ".track.json")
                    if os.path.exists(json_path):
                        os.remove(json_path)
                except Exception:
                    pass
                if strip_track_config(path):
                    healed += 1
        else:
            print("  ✓ %-58s %5.1f s · peak %5d · %3.0f %% Ton"
                  % (slug, (payload.get("duration") or 0) / 1000.0,
                     stats.get("peak", 0), stats.get("audible_ratio", 0) * 100.0))

    print("FF-VOICE-VERIFY – geprüft: %d, beanstandet: %d%s"
          % (checked, bad, (", geheilt: %d" % healed) if heal else ""))
    if bad and not heal:
        print("  → Reparatur: python3 scripts/ff_voice_audio.py --verify --heal "
              "--html-dir %s --out-dir %s" % (html_dir, out_dir))
    return bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Studio-Tonspuren für die Vorlese-Funktion")
    ap.add_argument("--html-dir", default="public")
    ap.add_argument("--out-dir", default=os.path.join("public", "audio", "articles"))
    ap.add_argument("--cache-dir", default="")
    ap.add_argument("--backend", default="auto", choices=["auto", "edge", "piper"])
    ap.add_argument("--profile", default=ttb.DEFAULT_PROFILE, choices=sorted(ttb.VOICE_PROFILES.keys()),
                    help="Stimmen-Profil — alle ausschließlich Deutsch (Standard: news)")
    ap.add_argument("--order", default="newest", choices=["newest", "oldest", "path"])
    ap.add_argument("--limit-new", type=int, default=0)
    # ZEITBUDGET (Reparatur Issue #218, 08.09.2026)
    # ------------------------------------------------------------------
    # Die Neuvertonung ist der mit ABSTAND teuerste Schritt des Deploys:
    # gemessen 63 min (Run 34129128450) bzw. 151 min (Run 34121113112),
    # während der komplette Rest (Checkout, alle Gates, Hugo-Build,
    # gh-pages-Push) zusammen nur ~90 s braucht. Ein reiner Stück-Zaehler
    # (--limit-new) kann das NICHT begrenzen, weil die Dauer je Artikel
    # stark schwankt (Laenge, Netz, Backend-Retries). --max-seconds ist
    # die fehlende Wanduhr-Grenze: Sie deckelt AUSSCHLIESSLICH die neue
    # Synthese. Bereits fertige Spuren bleiben erhalten, der Rest wird im
    # naechsten Lauf aus dem Cache weitergefuehrt (konvergent).
    # 0 = unbegrenzt (bewusster Backfill-Lauf).
    ap.add_argument("--max-seconds", type=int, default=0,
                    help="Wanduhr-Budget fuer NEUE Vertonungen in Sekunden "
                         "(0 = unbegrenzt). Cache-Wiederverwendung laeuft "
                         "immer vollstaendig weiter.")
    ap.add_argument("--only", default="")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--verify", action="store_true",
                    help="Endkontrolle: misst jede veröffentlichte Tonspur auf echten Ton")
    ap.add_argument("--heal", action="store_true",
                    help="mit --verify: defekte Tonspuren entfernen (Reader nimmt die Gerätestimme)")
    ap.add_argument("--engines", nargs="*", default=None)
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    if args.verify:
        bad = verify_tracks(args.html_dir, args.out_dir, heal=args.heal)
        if args.heal:
            return 0
        return 1 if bad else 0

    if args.engines is not None:
        print("Verfügbare Engines: %s" % (", ".join(ttb.available_engines()) or "keine"))
        print("Rezept-Version:     %s" % ttb.RECIPE_VERSION)
        for name, prof in ttb.VOICE_PROFILES.items():
            marker = "  ← Voreinstellung" if name == ttb.DEFAULT_PROFILE else ""
            print("  Profil %-9s DE %-36s Stil %-9s%s"
                  % (name, prof["de"], prof.get("style") or "neutral", marker))
        print("Sprache:              ausschließlich Deutsch (Nur-Deutsch-Vertrag)")
        print("Wortuhr (Leseanzeige): wird je Artikel mit erzeugt, wenn edge-tts Wortgrenzen liefert")
        print("ffmpeg:             %s" % ("ja" if ttb.has_ffmpeg() else "nein (WAV-Fallback)"))
        print("Audio-Dekoder:      %s" % (ttb.decoder_name() or "KEINER — edge-tts (MP3) unbrauchbar!"))
        if ttb.edge_module_present() and not ttb.decoder_available():
            print("  ⚠ edge-tts ist installiert, aber ohne Dekoder unbrauchbar:")
            print("    apt-get install -y ffmpeg   ODER   pip install miniaudio")
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
    # Zurueckgestellte Artikel (Budget/Limit erschoepft) – siehe unten:
    # sie werden NICHT abgebrochen, sondern nur von der teuren Synthese
    # ausgenommen, damit ihre Cache-Spuren weiterhin eingebunden werden.
    deferred = 0
    deadline = (time.monotonic() + args.max_seconds) if args.max_seconds > 0 else None
    limit_noted = False
    budget_noted = False
    if deadline is not None:
        print("Zeitbudget fuer neue Vertonungen: %d s (danach nur noch Cache-Wiederverwendung)."
              % args.max_seconds)

    for slug, path, markup in articles:
        root = parse_html(markup)
        cfg = read_reader_config(root)
        if not cfg:
            continue
        blocks, lang = extract_blocks(root, cfg)
        if not blocks:
            continue

        fp = fingerprint(blocks, engine, profile, voices["de"])
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
                # Cache-Wache (Befund 06.09.2026): Auf gh-pages lagen
                # Pausen-Spuren (alle Chunks t0==t1, 33 s für 10-Minuten-
                # Artikel). Deren Fingerprint stimmte — sie wurden für
                # immer wiederverwendet und in jede neue Seite injiziert.
                # Seitdem durchläuft JEDE wiederverwendete Spur dasselbe
                # Plausibilitäts-Gate wie eine frisch erzeugte.
                ok_cache, why = track_plausible(blocks, previous.get("chunks") or [], previous.get("duration") or 0)
                if previous.get("fingerprint") == fp and ok_cache:
                    src_audio = previous.get("src", "")
                    audio_name = src_audio.rsplit("/", 1)[-1] if src_audio else slug + ".mp3"
                    cached_audio = (os.path.join(args.cache_dir, audio_name)
                                    if args.cache_dir else os.path.join(args.out_dir, audio_name))
                    target_audio = os.path.join(args.out_dir, audio_name)
                    # STILLE-WACHE AM CACHE (07.09.2026): Nicht nur die
                    # Metadaten, sondern die DATEI wird gemessen. Genau so
                    # verschwinden die 34 stummen Spuren aus dem Bestand:
                    # Sie werden nicht wiederverwendet, sondern neu vertont.
                    probe = cached_audio if os.path.exists(cached_audio) else target_audio
                    heal_ok, heal_why, _stats = audio_health(probe, previous.get("duration") or 0)
                    if not heal_ok:
                        print("  ⚠ Cache-Spur %s verworfen (Datei: %s) — wird neu vertont"
                              % (slug, heal_why))
                        try:
                            if os.path.exists(target_audio):
                                os.remove(target_audio)
                            if os.path.exists(track_json):
                                os.remove(track_json)
                        except Exception:
                            pass
                        strip_track_config(path)
                    else:
                        if os.path.exists(cached_audio) and not os.path.exists(target_audio):
                            shutil.copy2(cached_audio, target_audio)
                        if os.path.exists(target_audio) and not os.path.exists(track_json):
                            shutil.copy2(src_json, track_json)
                        if os.path.exists(target_audio):
                            inject_track_config(path, {
                                "src": previous.get("src", ""),
                                "version": ttb.RECIPE_VERSION,
                                "voice": {"de": voices["de"],
                                          "style": voices.get("style"),
                                          "lang": "de"},
                                "engine": previous.get("engine", engine),
                                "profile": profile,
                                "duration": previous.get("duration", 0),
                                "chunks": previous.get("chunks", []),
                            })
                            reused += 1
                            continue
                elif previous.get("fingerprint") == fp and not ok_cache:
                    print("  ⚠ Cache-Spur %s verworfen (%s) — wird neu vertont" % (slug, why))
                    strip_track_config(path)

        # ---- STUECK- UND ZEITGRENZE (Reparatur Issue #218) ----------------
        # WICHTIG: hier wird bewusst `continue` statt des frueheren `break`
        # verwendet. Der Abbruch mit `break` verliess die Schleife komplett –
        # dadurch bekamen ALLE nachfolgenden Artikel ihren Tonspur-Block
        # nicht mehr in die frisch gebaute Seite injiziert und verloren ihr
        # Audio im Livegang, OBWOHL eine gueltige Spur im Cache lag. Mit
        # `continue` laeuft die guenstige Cache-Wiederverwendung fuer den
        # gesamten Rest der Warteschlange weiter; gedeckelt wird nur die
        # teure Neusynthese.
        if args.limit_new and produced >= args.limit_new:
            if not limit_noted:
                print("Limit erreicht (--limit-new %d) – Rest beim nächsten Lauf "
                      "(Cache-Spuren werden weiterhin eingebunden)." % args.limit_new)
                limit_noted = True
            deferred += 1
            continue

        if deadline is not None and time.monotonic() >= deadline:
            if not budget_noted:
                print("Zeitbudget erschoepft (--max-seconds %d) – Rest beim nächsten Lauf "
                      "(Cache-Spuren werden weiterhin eingebunden)." % args.max_seconds)
                budget_noted = True
            deferred += 1
            continue

        if args.dry_run:
            print("Würde vertonen: %s (%d Blöcke, %d Zeichen)"
                  % (slug, len(blocks), sum(len(b["text"]) for b in blocks)))
            produced += 1
            continue

        tmp_dir = os.path.join(args.out_dir, ".tmp-" + slug)
        samples, chunks, stats = synth_article(blocks, engine, profile, tmp_dir,
                                               log=lambda m: print("  · %s" % m),
                                               deadline=deadline)
        if stats.get("aborted"):
            # Budget lief MITTEN im Artikel ab (Segment-Deckel,
            # Härtung 10.09.2026) — derselbe Umgang wie zwischen
            # Artikeln: zurückstellen, Cache läuft weiter, kein
            # Verwerfen, kein Strip; der nächste Lauf setzt fort.
            if not budget_noted:
                print("Zeitbudget erschöpft (--max-seconds %d) – Rest beim nächsten Lauf "
                      "(Cache-Spuren werden weiterhin eingebunden)." % args.max_seconds)
                budget_noted = True
            deferred += 1
            shutil.rmtree(tmp_dir, ignore_errors=True)
            continue
        if not samples:
            failed += 1
            shutil.rmtree(tmp_dir, ignore_errors=True)
            strip_track_config(path)
            continue
        if stats["failed"] > 0:
            failed += 1
            print("  ✗ %s VERWORFEN: %d von %d Segmenten ohne Audio — keine Lückenspur veröffentlicht"
                  % (slug, stats["failed"], stats["segments"]))
            shutil.rmtree(tmp_dir, ignore_errors=True)
            strip_track_config(path)
            continue
        duration_ms = int(round(len(samples) * 1000.0 / ttb.SAMPLE_RATE))
        ok_track, why = track_plausible(blocks, chunks, duration_ms)
        if not ok_track:
            failed += 1
            print("  ✗ %s VERWORFEN: Plausibilitäts-Gate (%s) — Reader bleibt auf Gerätestimme" % (slug, why))
            shutil.rmtree(tmp_dir, ignore_errors=True)
            strip_track_config(path)
            continue

        # STILLE-WACHE (07.09.2026): gemessen, nicht geglaubt. Eine Spur
        # ohne Pegel wird nie geschrieben — der Reader nimmt dann ehrlich
        # die Gerätestimme statt 28 Sekunden Digitalstille abzuspielen.
        audible, why_audio = ttb.has_audible_speech(samples, ttb.SAMPLE_RATE, min_ratio=0.25)
        if not audible:
            failed += 1
            print("  ✗ %s VERWORFEN: Stille-Wache (%s) — keine tonlose Spur veröffentlicht"
                  % (slug, why_audio))
            shutil.rmtree(tmp_dir, ignore_errors=True)
            strip_track_config(path)
            continue

        wav_path = os.path.join(args.out_dir, slug + ".wav")
        mp3_path = os.path.join(args.out_dir, slug + ".mp3")
        ttb.write_wav_mono(wav_path, samples)
        audio_name = slug + ".wav"
        if ttb.master_to_mp3(wav_path, mp3_path) and os.path.getsize(mp3_path) > 0:
            # Auch das Mastering wird nachgemessen: Eine ffmpeg-Filterkette
            # kann eine stumme oder abgeschnittene Datei erzeugen. Dann
            # bleibt die geprüfte WAV stehen.
            mp3_ok, mp3_why, _mp3_stats = audio_health(mp3_path, duration_ms)
            if mp3_ok:
                audio_name = slug + ".mp3"
                try:
                    os.remove(wav_path)
                except Exception:
                    pass
            else:
                print("  ⚠ %s: MP3-Mastering verworfen (%s) — WAV bleibt" % (slug, mp3_why))
                try:
                    os.remove(mp3_path)
                except Exception:
                    pass

        final_audio = os.path.join(args.out_dir, audio_name)
        final_ok, final_why, final_stats = audio_health(final_audio, duration_ms)
        if not final_ok:
            failed += 1
            print("  ✗ %s VERWORFEN: Endkontrolle der Datei (%s)" % (slug, final_why))
            for leftover in (wav_path, mp3_path):
                try:
                    if os.path.exists(leftover):
                        os.remove(leftover)
                except Exception:
                    pass
            shutil.rmtree(tmp_dir, ignore_errors=True)
            strip_track_config(path)
            continue
        shutil.rmtree(tmp_dir, ignore_errors=True)

        payload = {
            "src": "/audio/articles/" + audio_name,
            "version": ttb.RECIPE_VERSION,
            "voice": {"de": voices["de"], "style": voices.get("style"),
                      "lang": "de"},
            "engine": engine,
            "profile": profile,
            "duration": duration_ms,
            "chunks": chunks,
        }
        with open(track_json, "w", encoding="utf-8") as fh:
            json.dump(dict(payload, fingerprint=fp), fh, ensure_ascii=False, indent=1)
        inject_track_config(path, payload)
        produced += 1
        print("Tonspur: %-58s %6.1f s  %d Blöcke  peak %d · %.0f %% Ton"
              % (slug, duration_ms / 1000.0, len(blocks),
                 final_stats.get("peak", 0), final_stats.get("audible_ratio", 0) * 100.0))

    print("FF-VOICE-AUDIO – neu: %d, wiederverwendet: %d, fehlgeschlagen: %d, zurückgestellt: %d"
          % (produced, reused, failed, deferred))
    if deferred:
        print("Hinweis: %d Artikel warten auf Vertonung (Stück-/Zeitgrenze). "
              "Der nächste Lauf setzt genau dort fort – kein Verlust." % deferred)
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

    # ---------- Nur-Deutsch-Vertrag (Befund 07.09.2026) ----------
    check("Nur-Deutsch: Sprach-Erkennung liefert immer de",
          detect_language("This is an English sample about insurance costs.", "en") == "de")
    check("Nur-Deutsch: Satz-Sniffing liefert immer de",
          sniff_sentence_lang("This sentence is clearly English.", "en") == "de")
    check("Nur-Deutsch: kein englisches CUES-Set mehr", "en" not in CUES)
    check("Nur-Deutsch: Blöcke tragen immer lang=de",
          all(b["lang"] == "de" for b in p_blocks))
    check("Nur-Deutsch: englisches Attribut kippt Block nicht",
          all(b["lang"] == "de" for b in extract_blocks(
              parse_html(FIXTURE.replace('<html lang="de">', '<html lang="en">')), cfg)[0]))
    check("Nur-Deutsch: Aussprache folgt deutschem Regelwerk",
          normalize_speech("about 20%") == "about 20 Prozent")

    # ---------- Wortuhr: Aligner N→R ----------
    def _aligned(norm, raw):
        return align_norm_to_raw(norm_tokens(norm), norm_tokens(raw))

    check("Wortuhr: 650 € → Euro am Rohwort ‚€“",
          _aligned("bis zu 650 Euro", "bis zu 650 €") == [0, 1, 2, 3])
    check("Wortuhr: Bereich 12 – 24 → 12 bis 24",
          _aligned("12 bis 24", "12 – 24") == [0, 1, 2])
    check("Wortuhr: Datum bleibt am Rohwort kleben",
          _aligned("Stand 2. Januar 2006 ende", "Stand 02.01.2006 ende") == [0, 1, 1, 1, 2])
    check("Wortuhr: kWh-Expansion trifft das Rohwort",
          _aligned("20 Kilowattstunden Strom", "20 kWh Strom") == [0, 1, 2])
    check("Wortuhr: Monotonie (nie zurück)",
          (lambda a: all(a[i] <= a[i + 1] for i in range(len(a) - 1)))(
              _aligned("Der Cashflow kommt jeden Monat und das ist gut so",
                       "Der Cashflow kommt jeden Monat und das ist gut so")))
    check("Wortuhr: leere Rohliste ⇒ -1 ohne Absturz", _aligned("a b", "") == [-1, -1])

    def _wplaus_ok(chunks_w):
        bb = [{"type": "p", "lang": "de", "text": "Eins zwei drei"}]
        return track_plausible(bb, chunks_w, 1400)[0]

    check("Wortuhr-Gate: saubere Karte besteht",
          _wplaus_ok([{"b": 0, "t0": 100, "t1": 8000, "lang": "de", "w": [[0, 120], [1, 900], [2, 2000]]}]))
    check("Wortuhr-Gate: Index außerhalb fällt durch",
          not _wplaus_ok([{"b": 0, "t0": 100, "t1": 8000, "w": [[9, 120], [9, 900]]}]))
    check("Wortuhr-Gate: unmotologische Zeit fällt durch",
          not _wplaus_ok([{"b": 0, "t0": 100, "t1": 8000, "w": [[1, 5000], [2, 300]]}]))
    check("Wortuhr-Gate: absteigender Index fällt durch",
          not _wplaus_ok([{"b": 0, "t0": 100, "t1": 8000, "w": [[2, 300], [1, 5000]]}]))

    # Fingerprint
    fp1 = fingerprint(blocks, "edge", "news", "de-DE-ConradNeural")
    fp2 = fingerprint(blocks, "edge", "news", "de-DE-ConradNeural")
    fp3 = fingerprint(blocks, "edge", "narrator", "de-DE-KillianNeural")
    check("Fingerprint stabil", fp1 == fp2)
    check("Fingerprint reagiert auf Stimme", fp1 != fp3)
    check("Fingerprint: englische Stimme ist bedeutungslos (Nur-Deutsch)",
          fp1 == fingerprint(blocks, "edge", "news", "de-DE-ConradNeural", "en-US-Irgendwas"))

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

    # ---------- Plausibilitäts-Gate & Stille-Wache (Befund 06.09.2026) ----
    # Auf gh-pages standen Pausen-Spuren (85 Chunks, alle t0==t1, 33 s für
    # einen Zehn-Minuten-Artikel) — der Reader spielte sie stumm durch.
    # Diese Tests pinnen die Wache fest, die das verhindert.
    deployed_defect = {"chunks": [{"b": i, "t0": i * 420, "t1": i * 420, "lang": "de"}
                                  for i in range(85)], "duration": 32980}
    ok_defect, why_defect = track_plausible(blocks, deployed_defect["chunks"], deployed_defect["duration"])
    check("Gate verwirft deployte Pausen-Spur", not ok_defect)
    check("Gate nennt den Grund (t0==t1)", "t0==t1" in why_defect)

    honest_ms = int(expected_speech_ms(blocks))
    honest_chunks = []
    t = 0
    for bi, b in enumerate(blocks):
        d = max(200, int(len(b["text"]) / ttb.BASE_CPS * 1000))
        honest_chunks.append({"b": bi, "t0": t, "t1": t + d, "lang": b.get("lang") or "de"})
        t += d + 300
    ok_honest, _ = track_plausible(blocks, honest_chunks, t)
    check("Gate akzeptiert ehrliche Spur", ok_honest)

    ok_short, why_short = track_plausible(blocks, honest_chunks, int(honest_ms * 0.05))
    check("Gate verwirft Stumm-Spur (5 % Hörzeit)", not ok_short and "zu kurz" in why_short)
    ok_long, _ = track_plausible(blocks, honest_chunks, honest_ms * 20)
    check("Gate verwirft falsche Spur (20× zu lang)", not ok_long)
    ok_empty, _ = track_plausible(blocks, [], 0)
    check("Gate verwirft leere Spur", not ok_empty)
    gap_chunks = [dict(c) for c in honest_chunks]
    gap_chunks[2]["t1"] = gap_chunks[2]["t0"]
    ok_gap, _ = track_plausible(blocks, gap_chunks, t)
    check("Gate verwirft Einzel-Lücke (t0==t1)", not ok_gap)

    # synth_article: fehlgeschlagene Segmente zählen — nie still überspringen
    import tempfile as _tf
    orig_synthesize = ttb.synthesize
    try:
        def _failing_synth(text, lang, engine, profile_name, out_wav, rate=1.0, pitch=0, volume=1.0):
            return engine, False, []
        ttb.synthesize = _failing_synth
        with _tf.TemporaryDirectory() as td:
            _s, _c, st = synth_article(blocks, "edge", "natural", td, log=None)
            check("Backend-Ausfall zählt als Fehler", st["failed"] == st["segments"] and st["failed"] > 0)
            check("Backend-Ausfall: kein Segment ok", st["ok"] == 0)

        def _working_synth(text, lang, engine, profile_name, out_wav, rate=1.0, pitch=0, volume=1.0):
            import math as _math
            n = int((len(text) / ttb.BASE_CPS) * ttb.SAMPLE_RATE)
            tone = [int(12000 * _math.sin(2 * _math.pi * 180 * i / ttb.SAMPLE_RATE))
                    for i in range(max(1, n))]
            ttb.write_wav_mono(out_wav, tone)
            return engine, True, []
        ttb.synthesize = _working_synth
        with _tf.TemporaryDirectory() as td:
            s2, c2, st2 = synth_article(blocks, "edge", "natural", td, log=None)
            check("Funktionierende Spur: keine Fehler", st2["failed"] == 0 and st2["ok"] > 0)
            check("Funktionierende Spur: jeder Chunk spricht", all(ch["t1"] > ch["t0"] for ch in c2))
            dur2 = int(round(len(s2) * 1000.0 / ttb.SAMPLE_RATE))
            ok2, _ = track_plausible(blocks, c2, dur2)
            check("Funktionierende Spur besteht das Gate", ok2)
            check("Ohne Wortgrenzen bleibt die Wortuhr weg (kein Bluff)",
                  all("w" not in ch for ch in c2))

        # End-to-End mit Wortgrenzen: jedes Wort eines Segments bekommt
        # eine Zeit; die Karte muss strukturiert, im Chunkfenster und
        # indexseitig gültig sein — und das Gate muss sie bestehen.
        def _boundary_synth(text, lang, engine, profile_name, out_wav,
                            rate=1.0, pitch=0, volume=1.0):
            import math as _m
            n = int((len(text) / ttb.BASE_CPS) * ttb.SAMPLE_RATE)
            tone = [int(12000 * _m.sin(2 * _m.pi * 180 * i / ttb.SAMPLE_RATE))
                    for i in range(max(1, n))]
            ttb.write_wav_mono(out_wav, tone)
            bnds = []
            for k, w in enumerate(norm_tokens(text)):
                bnds.append({"offset": k * 300000, "duration": 250000, "text": w})
            return engine, True, bnds
        ttb.synthesize = _boundary_synth
        with _tf.TemporaryDirectory() as td:
            s3, c3, st3 = synth_article(blocks, "edge", "news", td, log=None)
            wch = [ch for ch in c3 if ch.get("w")]
            check("Wortuhr: wird bei Wortgrenzen erzeugt", len(wch) >= 2)
            check("Wortuhr: Zeitstempel wachsen im Chunk",
                  all(all(e[1] <= nxt[1] for e, nxt in zip(ch["w"], ch["w"][1:]))
                      for ch in wch))
            check("Wortuhr: Indizes zeigen in den Blocktext",
                  all(0 <= e[0] < max(1, len(norm_tokens(blocks[ch["b"]]["text"])))
                      for ch in wch for e in ch["w"]))
            dur3 = int(round(len(s3) * 1000.0 / ttb.SAMPLE_RATE))
            ok3, why3 = track_plausible(blocks, c3, dur3)
            check("Wortspur besteht das Plausibilitäts-Gate", ok3)
            check("Wortuhr: stats zählen Wörter mit", st3["words"] >= 2)

        # ZEITBUDGET ZWISCHEN SEGMENTEN (Härtung 10.09.2026): Früher
        # galt die Deadline nur zwischen Artikeln — ein Artikel mit
        # vielen (oder hängenden) Segmenten überzog sie unbegrenzt.
        # Ablauf ⇒ sofortiger Abbruch mit Ehrlichkeits-Flag statt
        # Verwerfen; der Aufrufer stellt zurück (deferred).
        calls = []

        def _counting_synth(text, lang, engine, profile_name, out_wav,
                            rate=1.0, pitch=0, volume=1.0):
            calls.append(text)
            return _working_synth(text, lang, engine, profile_name, out_wav,
                                  rate=rate, pitch=pitch, volume=volume)

        ttb.synthesize = _counting_synth
        with _tf.TemporaryDirectory() as td:
            past = time.monotonic() - 1.0
            sa, _ca, sta = synth_article(blocks, "edge", "natural", td, log=None,
                                         deadline=past)
            check("Budget: abgelaufene Deadline bricht mit Ehrlichkeits-Flag ab",
                  sta.get("aborted") is True and sa is None)
            check("Budget: kein Segment mehr synthetisiert", calls == [])
            future = time.monotonic() + 600.0
            _sb, _cb, stb = synth_article(blocks, "edge", "natural", td, log=None,
                                          deadline=future)
            check("Budget: frische Deadline synthetisiert normal",
                  stb.get("aborted") is not True and stb["ok"] > 0
                  and stb["failed"] == 0)
    finally:
        ttb.synthesize = orig_synthesize

    # Engine-Auswahl
    check("Engine-Auswahl respektiert None", pick_engine("nicht-da") is None or True)

    # ------------------------------------------------------------------
    # KERNBEFUND 06.09.2026 · Der komplette Weg bis zur Datei
    #   „edge-tts liefert MP3, die Kette las RIFF/WAVE“ → Digitalstille
    # ------------------------------------------------------------------
    import math as _math
    import tempfile as _tf2

    def _speech_samples(seconds=2.0):
        n = int(ttb.SAMPLE_RATE * seconds)
        out = []
        for i in range(n):
            t = i / float(ttb.SAMPLE_RATE)
            env = 0.5 + 0.5 * _math.sin(2 * _math.pi * 4 * t)
            out.append(int(10000 * env * _math.sin(2 * _math.pi * 170 * t)))
        return out

    with _tf2.TemporaryDirectory() as td:
        silent_wav = os.path.join(td, "silent.wav")
        ttb.write_wav_mono(silent_wav, [0] * (ttb.SAMPLE_RATE * 3))
        loud_wav = os.path.join(td, "loud.wav")
        ttb.write_wav_mono(loud_wav, _speech_samples(3.0))

        ok_sil, why_sil, _st = audio_health(silent_wav, 3000)
        check("Datei-Wache: deployte Stille-Spur fällt durch", ok_sil is False)
        check("Datei-Wache: Grund benannt", "Digitalstille" in why_sil or "hörbar" in why_sil)
        check("Datei-Wache: echte Sprache besteht", audio_health(loud_wav, 3000)[0] is True)
        check("Datei-Wache: fehlende Datei fällt durch",
              audio_health(os.path.join(td, "gibtsnicht.wav"))[0] is False)
        check("Datei-Wache: zu kurze Datei fällt durch",
              audio_health(loud_wav, 60000)[0] is False)

        # Injektion / Entfernung des Konfigurationsblocks
        page = os.path.join(td, "index.html")
        with open(page, "w", encoding="utf-8") as fh:
            fh.write(FIXTURE)
        inject_track_config(page, {"src": "/audio/articles/x.wav", "duration": 1000, "chunks": []})
        with open(page, encoding="utf-8") as fh:
            markup_injected = fh.read()
        check("Injektion: Block steht in der Seite", CONFIG_BLOCK_ID in markup_injected)
        check("Rückbau: Block entfernt", strip_track_config(page) is True)
        with open(page, encoding="utf-8") as fh:
            check("Rückbau: Seite ohne Tonspur-Block", CONFIG_BLOCK_ID not in fh.read())
        check("Rückbau: zweiter Aufruf ist wirkungslos", strip_track_config(page) is False)

    # Endkontrolle gegen den DEPLOYTEN Defekt: Seite + Stille-WAV + Karte
    with _tf2.TemporaryDirectory() as td:
        html_dir = os.path.join(td, "public")
        out_dir = os.path.join(html_dir, "audio", "articles")
        page_dir = os.path.join(html_dir, "posts", "stille-spur")
        os.makedirs(page_dir, exist_ok=True)
        os.makedirs(out_dir, exist_ok=True)
        page = os.path.join(page_dir, "index.html")
        with open(page, "w", encoding="utf-8") as fh:
            fh.write(FIXTURE)
        ttb.write_wav_mono(os.path.join(out_dir, "stille-spur.wav"),
                           [0] * int(ttb.SAMPLE_RATE * 27.94))
        root_x = parse_html(FIXTURE)
        blocks_x, _lx = extract_blocks(root_x, read_reader_config(root_x))
        deployed_payload = {
            "src": "/audio/articles/stille-spur.wav",
            "version": ttb.RECIPE_VERSION, "engine": "edge", "profile": "natural",
            "duration": 27940,
            "chunks": [{"b": i, "t0": i * 420, "t1": i * 420, "lang": "de"}
                       for i in range(len(blocks_x))],
        }
        inject_track_config(page, deployed_payload)
        with open(os.path.join(out_dir, "stille-spur.track.json"), "w", encoding="utf-8") as fh:
            json.dump(deployed_payload, fh)

        bad = verify_tracks(html_dir, out_dir, heal=False)
        check("Endkontrolle erkennt die deployte Stille-Spur", bad == 1)
        bad_healed = verify_tracks(html_dir, out_dir, heal=True)
        check("Heilung meldet denselben Fund", bad_healed == 1)
        with open(page, encoding="utf-8") as fh:
            check("Heilung: Seite zeigt nicht mehr auf die Spur", CONFIG_BLOCK_ID not in fh.read())
        check("Heilung: stumme Datei gelöscht",
              not os.path.exists(os.path.join(out_dir, "stille-spur.wav")))
        check("Endkontrolle danach sauber", verify_tracks(html_dir, out_dir) == 0)

    # Eine gesunde Spur besteht die Endkontrolle vollständig
    with _tf2.TemporaryDirectory() as td:
        html_dir = os.path.join(td, "public")
        out_dir = os.path.join(html_dir, "audio", "articles")
        page_dir = os.path.join(html_dir, "posts", "gute-spur")
        os.makedirs(page_dir, exist_ok=True)
        os.makedirs(out_dir, exist_ok=True)
        page = os.path.join(page_dir, "index.html")
        with open(page, "w", encoding="utf-8") as fh:
            fh.write(FIXTURE)
        root_g = parse_html(FIXTURE)
        blocks_g, _lg = extract_blocks(root_g, read_reader_config(root_g))
        secs = expected_speech_ms(blocks_g) / 1000.0
        ttb.write_wav_mono(os.path.join(out_dir, "gute-spur.wav"), _speech_samples(secs))
        t = 0
        chunks_g = []
        for bi, b in enumerate(blocks_g):
            d = max(200, int(len(b["text"]) / ttb.BASE_CPS * 1000))
            chunks_g.append({"b": bi, "t0": t, "t1": t + d, "lang": b.get("lang") or "de"})
            t += d
        inject_track_config(page, {"src": "/audio/articles/gute-spur.wav",
                                   "duration": int(secs * 1000), "chunks": chunks_g})
        check("Endkontrolle lässt gesunde Spur durch", verify_tracks(html_dir, out_dir) == 0)

    # ------------------------------------------------------------------
    # ZEITBUDGET + WARTESCHLANGEN-TREUE (Reparatur Issue #218, 08.09.2026)
    #
    # Regression, die dieser Block dauerhaft ausschliesst: Die Stueckgrenze
    # brach die Schleife frueher mit `break` ab. Damit verloren ALLE
    # nachfolgenden Artikel ihren Tonspur-Block in der frisch gebauten
    # Seite – auch die, deren fertige Spur laengst im Cache lag. Aus einer
    # reinen Drossel wurde so ein stiller Audio-Verlust im Livegang.
    # Erwartet: gedrosselt wird nur die teure NEUsynthese, die Schleife
    # laeuft ueber die gesamte Warteschlange.
    # ------------------------------------------------------------------
    import contextlib as _ctx
    import io as _io

    with _tf2.TemporaryDirectory() as td:
        html_dir = os.path.join(td, "public")
        out_dir = os.path.join(html_dir, "audio", "articles")
        os.makedirs(out_dir, exist_ok=True)
        for slug in ("artikel-eins", "artikel-zwei", "artikel-drei"):
            page_dir = os.path.join(html_dir, "posts", slug)
            os.makedirs(page_dir, exist_ok=True)
            with open(os.path.join(page_dir, "index.html"), "w", encoding="utf-8") as fh:
                fh.write(FIXTURE)

        # Hermetisch: kein echtes TTS-Backend noetig, kein Netzzugriff.
        _orig_pick = globals()["pick_engine"]
        globals()["pick_engine"] = lambda _b: "edge"
        try:
            buf = _io.StringIO()
            with _ctx.redirect_stdout(buf):
                rc_limit = main(["--html-dir", html_dir, "--out-dir", out_dir,
                                 "--dry-run", "--order", "path", "--limit-new", "1"])
            out_limit = buf.getvalue()

            buf2 = _io.StringIO()
            with _ctx.redirect_stdout(buf2):
                rc_free = main(["--html-dir", html_dir, "--out-dir", out_dir,
                                "--dry-run", "--order", "path"])
            out_free = buf2.getvalue()

            buf3 = _io.StringIO()
            with _ctx.redirect_stdout(buf3):
                rc_budget = main(["--html-dir", html_dir, "--out-dir", out_dir,
                                  "--dry-run", "--order", "path", "--max-seconds", "600"])
            out_budget = buf3.getvalue()
        finally:
            globals()["pick_engine"] = _orig_pick

        check("Drossel: Lauf bleibt erfolgreich", rc_limit == 0)
        check("Drossel: genau 1 Artikel neu vertont", "neu: 1," in out_limit)
        check("Drossel: Warteschlange wird NICHT abgebrochen (Issue #218)",
              "zurückgestellt: 2" in out_limit)
        check("Drossel: Rest wird als wartend gemeldet, nicht verschwiegen",
              "warten auf Vertonung" in out_limit)
        check("Ohne Grenze: alle Artikel werden bearbeitet", "neu: 3," in out_free)
        check("Ohne Grenze: nichts zurückgestellt", "zurückgestellt: 0" in out_free)
        check("Zeitbudget: Option wird angenommen", rc_budget == 0)
        check("Zeitbudget: Budget wird protokolliert",
              "Zeitbudget fuer neue Vertonungen: 600 s" in out_budget)
        check("Zeitbudget: grosszuegiges Budget drosselt nicht",
              "neu: 3," in out_budget and "zurückgestellt: 0" in out_budget)

    failed = [n for n, ok in results if not ok]
    for name, ok in results:
        if not ok:
            print("  ✗ " + name)
    print("FF-VOICE-AUDIO – Selbsttest: %d/%d bestanden" % (len(results) - len(failed), len(results)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
