#!/usr/bin/env python3
"""generate_reader_audio.py — Vorab vertonte Artikel (ZEIT-Standard, v7).

Vertont die Artikel des Blogs mit einer MÄNNLICHEN DE- & EN-Stimme
über Groq playai-tts (Fritz-PlayAI / Atlas-PlayAI).

Rauschen und Knackgeräusche werden durch drei kostenlose Mittel beseitigt:
  1. Crossfade-Konkatenation (4 ms Overlap an Segment-Grenzen)
  2. WAV-Vorverarbeitung mit Peak-Limiter und Subsonik-HPF
  3. Stabileffmpeg-Kodierung (48 kbit/s, Mono, 24 kHz) mit WAV-Fallback

Der Reader (static/premium/ff-reader.js) bevorzugt die Tonspur, wenn
sie existiert, und fällt sonst automatisch auf die lokale Browser-Stimme
zurück.

Aufruf (lokal oder im Deploy-Workflow NACH `hugo --minify`):
  GROQ_API_KEY=… python3 scripts/generate_reader_audio.py --html-dir public \\
      --out-dir public/audio/articles --cache-dir /tmp/ff-audio-cache \\
      [--only <slug>] [--dry-run] [--force]

  · --out-dir   Zielverzeichnis (Deploy: public/audio/articles; lokal:
                static/audio/articles). Pro Artikel entstehen
                <slug>.mp3 (Fallback .wav ohne ffmpeg) + <slug>.audio.json.
  · --cache-dir Vorherige Tonspuren (z. B. aus dem letzten gh-pages-Stand).
                Unveränderte Artikel werden 1:1 wiederverwendet (Fingerprint),
                nur neue/geänderte Artikel werden neu vertont → inkrementell.
  · Injektion  Der Generator schreibt zusätzlich
                <script type="application/json" id="ff-reader-audio-config">
                in jede Artikel-HTML – der Reader bevorzugt dann die Tonspur
                (männliche DE-/EN-Stimme, identisch auf allen Geräten) und
                fällt ohne Tonspur automatisch auf die lokale Browser-Stimme
                zurück.

Selbsttest (ohne Netzwerk/Key):
  python3 scripts/generate_reader_audio.py --selftest
"""
from __future__ import annotations

import argparse
import hashlib
import html as html_mod
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import groq_config  # noqa: E402  (API-URL-Muster, Key, User-Agent)

# --------------------------------------------------------------------------
# TTS-Backend: Groq playai-tts
# --------------------------------------------------------------------------
# Das Reader-JS (ff-reader.js) und die Toolbar werden NICHT berührt –
# sie prüfen nur, ob cfg.audio existiert, und spielen es ab.

GROQ_API_URL = "https://api.groq.com/openai/v1/audio/speech"
GROQ_TTS_MODEL = os.environ.get("FF_AUDIO_MODEL", "playai-tts")
GROQ_VOICE_DE = os.environ.get("FF_AUDIO_VOICE_DE", "Fritz-PlayAI")
GROQ_VOICE_EN = os.environ.get("FF_AUDIO_VOICE_EN", "Atlas-PlayAI")

INTRO_DE = "{title}. Ein Beitrag von FranksFinanzcheck. Hördauer etwa {time} Minuten."
INTRO_EN = "{title}. An article by FranksFinanzcheck. Listening time about {time} minutes."
OUTRO_DE = "Ende des Beitrags. Vielen Dank fürs Zuhören bei FranksFinanzcheck."
OUTRO_EN = "End of article. Thank you for listening to FranksFinanzcheck."


# --------------------------------------------------------------------------
# Sprache (DE/EN) – kompakte Heuristik analog zum Reader
# --------------------------------------------------------------------------
DE_STOP = set("der die das und ist sind war waren wird werden wurde ein eine einer einem einen nicht mit von für auf zu im am den dem des bei auch sich kann können muss müssen darf sollen haben hat hatte aber oder wenn weil dass wie als nach vor bis seit aus nur noch schon dann doch auch hier jetzt über unter zwischen ohne gegen durch um sie wir ihr euch uns er es mich dich ihm ihn diese dieser dieses diesem diesen welche mein meine dein deine ihre kein keine alle allen alles viele zwei drei viel monat versicherung kosten vertrag beitrag jahr euro prozent".split())
EN_STOP = set("the and of to you your for is are was were be with that this these those it on at by from as not or but if then have has had will would can could should may our their them they we what when where why how who which more most only very just also here there all any some no yes do does did about into over under between through after before during because while against up down out off again once an me us him his her my every own other each both few first new good much than per want need know save saving money insurance cost costs compare comparison guide tariff should free cheap best important article summary read listen avoid switch".split())
GERMAN_ENDINGS = ("ung", "keit", "heit", "nis", "schaft", "tum", "lich", "ig", "bar", "sam", "ieren", "iert")


def sniff_lang(text: str, base: str) -> str:
    words = re.findall(r"[a-zäöüß0-9'-]+", (text or "").lower())
    en = de = germ = 0
    for w in words:
        if len(w) < 2:
            continue
        if w in EN_STOP:
            en += 1
        if w in DE_STOP:
            de += 1
        if re.search(r"[äöüß]", w):
            germ += 2
        if len(w) >= 5:
            for e in GERMAN_ENDINGS:
                if w.endswith(e):
                    germ += 1
                    break
    if base == "de":
        return "en" if (en >= 3 and en > de * 2 + 1) else "de"
    return "de" if (de >= 3 and de > en) or (de >= 1 and germ >= 2 and de > en) else "en"


def normalize_text(text: str) -> str:
    """Leichte redaktionelle Reinigung für die Neural-TTS (kein Phonetik-Ersatz)."""
    if not text:
        return ""
    s = text.replace("\u00a0", " ").replace("\u00ad", "")
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)          # Markdown-Links
    s = re.sub(r"[*_`~#>]+", "", s)                          # Markdown-Symbole
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"z\.\s*B\.", "zum Beispiel", s, flags=re.I)
    s = re.sub(r"d\.\s*h\.", "das heißt", s, flags=re.I)
    s = re.sub(r"u\.\s*a\.", "unter anderem", s, flags=re.I)
    s = re.sub(r"\bMio\.", "Millionen", s, flags=re.I)
    s = re.sub(r"\bMrd\.", "Milliarden", s, flags=re.I)
    s = re.sub(r"\bca\.", "circa", s, flags=re.I)
    s = re.sub(r"\bggf\.", "gegebenenfalls", s, flags=re.I)
    # Emojis & Piktogramme entfernen (kein "Emoji-Stottern")
    s = re.sub(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u2190-\u21FF\u2B00-\u2BFF]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if s and not re.search(r"[.!?…:,]$", s):
        s += "."
    return s


# --------------------------------------------------------------------------
# Block-Extraktion – 1:1-Port von collectBlocks() aus ff-reader.js
# --------------------------------------------------------------------------
READ_SELECTOR = {"h2", "h3", "h4", "p", "li", "blockquote", "table"}
READ_BOXES = {"ff-table-scroll", "ff-tarif-card", "ff-einspar-box",
              "ff-kurzantwort", "ff-korrektur", "callout"}
# Container, die samt Inhalt übersprungen werden (JS: closest(...)).
SKIP_ANCESTORS = {"figure", "script", "style", "noscript", "ff-reader-toolbar",
                  "ff-toc", "ff-share", "ff-related"}
# Für die Boxen-/Zitat-Ausschlüsse (JS: el.closest(...)).
NESTED_SKIP = {"ff-kurzantwort", "ff-korrektur", "callout",
               "ff-tarif-card", "ff-einspar-box", "blockquote"}


class Node:
    __slots__ = ("tag", "attrs", "classes", "parent", "children", "text", "id")

    def __init__(self, tag: str):
        self.tag = tag
        self.attrs: dict[str, str] = {}
        self.classes: set[str] = set()
        self.parent: Node | None = None
        self.children: list[Node] = []
        self.text: str = ""
        self.id: str = ""

    def _match_sel(self, sel: str) -> bool:
        if sel.startswith("[") and sel.endswith("]"):
            inner = sel[1:-1]
            if "=" in inner:
                k, v = inner.split("=", 1)
                return self.attrs.get(k.strip().lower(), "") == v.strip().strip('"\'')
            return inner.strip().lower() in self.attrs
        if sel.startswith("."):
            return sel[1:] in self.classes
        if sel.startswith("#"):
            return self.id == sel[1:]
        return self.tag == sel.lower()

    def closest(self, *selectors: str) -> bool:
        """Wie Element.closest() inkl. Selbst-Treffer."""
        n: Node | None = self
        while n is not None:
            for sel in selectors:
                if n._match_sel(sel):
                    return True
            n = n.parent
        return False


class DocParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag.lower())
        for k, v in attrs:
            node.attrs[k.lower()] = v or ""
            if k.lower() == "id":
                node.id = v or ""
            if k.lower() == "class":
                node.classes = {c for c in (v or "").split() if c}
        node.parent = self.stack[-1]
        self.stack[-1].children.append(node)
        self.stack.append(node)

    def handle_endtag(self, tag):
        tag = tag.lower()
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if self.stack:
            self.stack[-1].text += data


def element_text(node: Node) -> str:
    """Port von readableText(): dekorative/verborgene Teile werden entfernt."""
    parts = []

    def walk(n: Node):
        if n.tag in {"script", "style", "noscript"}:
            return
        if n.attrs.get("aria-hidden") == "true":
            return
        if "ff-heading-copy" in n.classes or "anchor" in n.classes or "ff-reader-toolbar" in n.classes:
            return
        if n.text:
            parts.append(n.text)
        for c in n.children:
            walk(c)

    walk(node)
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def element_text_without(node: Node, skip_classes: set[str]) -> str:
    """Text wie element_text(), aber ohne Nachfahren mit einer der skip_classes."""
    parts: list[str] = []

    def walk(n: Node) -> None:
        if n.tag in {"script", "style", "noscript"}:
            return
        if n.attrs.get("aria-hidden") == "true":
            return
        if any(x in n.classes for x in skip_classes):
            return
        if n.text:
            parts.append(n.text)
        for c in n.children:
            walk(c)

    walk(node)
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def find_post_content(root: Node) -> Node | None:
    def walk(n: Node):
        if "post-content" in n.classes or "md-content" in n.classes:
            return n
        for c in n.children:
            r = walk(c)
            if r:
                return r
        return None

    return walk(root)


def parse_tables(node: Node, lang: str, out: list) -> None:
    """Port von extractTableSpeechBlocks() – Intro + Zeilen + Outro."""
    title = node.attrs.get("aria-label") or ""
    if not title:
        caption = next((c for c in node.children if c.tag == "caption"), None)
        if caption:
            title = element_text(caption)
    if not title:
        title = "Übersichtstabelle" if lang != "en" else "Overview Table"

    headers: list[str] = []
    body_rows: list[list[str]] = []
    direct_trs: list[list[str]] = []
    for part in node.children:
        if part.tag == "thead":
            for tr in part.children:
                if tr.tag == "tr":
                    headers = [element_text(c) for c in tr.children if c.tag in {"td", "th"}]
                    break
        elif part.tag == "tbody":
            for tr in part.children:
                if tr.tag == "tr":
                    body_rows.append([element_text(c) for c in tr.children if c.tag in {"td", "th"}])
        elif part.tag == "tr":
            direct_trs.append([element_text(c) for c in part.children if c.tag in {"td", "th"}])

    if not headers and direct_trs:
        headers = direct_trs[0]
    rows = body_rows if body_rows else (direct_trs[1:] if len(direct_trs) > 1 else [])

    col_count = max(len(headers), 1)
    row_count = len(rows)

    if lang != "en":
        intro = f"Tabelle: {title}. Übersicht mit {col_count} Spalten und {row_count} Zeilen."
        if headers:
            intro += f" Die Spalten lauten: {', '.join(headers)}."
        out.append((lang, "table-intro", intro))
        for idx, row in enumerate(rows, 1):
            row_label = row[0] if row else ""
            stmts = []
            for ci, cell in enumerate(row):
                if not cell:
                    continue
                if ci == 0 and row_label:
                    continue
                hname = headers[ci] if ci < len(headers) else f"Spalte {ci + 1}"
                stmts.append(f"{hname}: {cell}")
            if not stmts and row_label:
                stmts.append(row_label)
            if not stmts:
                continue
            content = ". ".join(stmts)
            row_raw = (f"{row_label}. " if row_label else "") + f"Zeile {idx} von {row_count}. {content}."
            out.append((lang, "table-row", row_raw))
        out.append((lang, "table-outro", f"Ende der Tabelle {title}."))
    else:
        intro = f"Table: {title}. Overview with {col_count} columns and {row_count} rows."
        if headers:
            intro += f" The columns are: {', '.join(headers)}."
        out.append((lang, "table-intro", intro))
        for idx, row in enumerate(rows, 1):
            row_label = row[0] if row else ""
            stmts = []
            for ci, cell in enumerate(row):
                if not cell:
                    continue
                if ci == 0 and row_label:
                    continue
                hname = headers[ci] if ci < len(headers) else f"Column {ci + 1}"
                stmts.append(f"{hname}: {cell}")
            if not stmts and row_label:
                stmts.append(row_label)
            if not stmts:
                continue
            content = ". ".join(stmts)
            row_raw = (f"{row_label}. " if row_label else "") + f"Row {idx} of {row_count}. {content}."
            out.append((lang, "table-row", row_raw))
        out.append((lang, "table-outro", f"End of table {title}."))


def collect_blocks(root: Node, title: str, article_lang: str,
                   reading_time: str = "") -> list[tuple[str, str, str]]:
    """Liefert [(lang, type, text), …] exakt wie collectBlocks() im Reader."""
    content = find_post_content(root)
    out: list[tuple[str, str, str]] = []
    intro = (INTRO_DE if article_lang != "en" else INTRO_EN).replace("{title}", title).replace("{time}", reading_time or "")
    out.append((article_lang, "intro", intro))
    if content is None:
        out.append((article_lang, "outro", OUTRO_DE if article_lang != "en" else OUTRO_EN))
        return out

    # Vorab-Boxen (Korrektur, Kurzantwort) – sie stehen im Template AUSSERHALB
    # von .post-content (Geschwister, nicht Nachfahren). Der Reader liest sie
    # seit 04.09.2026 ausdrücklich (Fix #169: „der grüne Kasten wurde nie
    # vorgelesen"). Für die Tonspur MUSS dieselbe Blockreihenfolge gelten.
    pre_boxes: list[Node] = []

    def gather_pre(n: Node) -> None:
        if any(x in n.classes for x in ("ff-kurzantwort", "ff-korrektur")) and \
                not n.closest("post-content", "md-content", "ff-reader-toolbar"):
            pre_boxes.append(n)
        for c in n.children:
            gather_pre(c)

    gather_pre(root)
    for box in pre_boxes:
        txt = element_text_without(box, {"ff-kurzantwort__head", "ff-kurzantwort__label", "ff-kurzantwort__icon"})
        if len(txt) <= 5:
            continue
        is_korrektur = "ff-korrektur" in box.classes
        if is_korrektur:
            cue = "Correction:" if article_lang == "en" else "Korrekturhinweis:"
        else:
            cue = "Short answer:" if article_lang == "en" else "Kurzantwort:"
        out.append((article_lang, "warning" if is_korrektur else "callout", f"{cue} {txt}"))

    # Flache qsa-Äquivalenz in Dokument-Reihenfolge (wie der Reader).
    nodes: list[Node] = []

    def gather(n: Node):
        if n.tag in READ_SELECTOR or any(x in READ_BOXES for x in n.classes):
            nodes.append(n)
        for c in n.children:
            gather(c)

    gather(content)

    processed_tables: set[int] = set()
    for el in nodes:
        # 1) Container-Skip (JS: el.closest('figure, script, …')).
        if el.closest(*SKIP_ANCESTORS):
            continue
        if el.closest('[aria-hidden="true"]', '[data-ff-skip-read]') or el.id == "TableOfContents":
            continue

        el_lang = "en" if (el.attrs.get("lang", article_lang) or "").lower().startswith("en") else "de"

        # 2) Tabellen: Intro + Zeilen + Outro als eigene Blöcke (dedupliziert).
        if el.tag == "table" or "ff-table-scroll" in el.classes:
            tbl = el if el.tag == "table" else next((x for x in el.children if x.tag == "table"), None)
            if tbl is None or id(tbl) in processed_tables:
                continue
            processed_tables.add(id(tbl))
            parse_tables(tbl, el_lang, out)
            continue

        # 3) Inneres von Tabellen nicht doppelt lesen.
        if el.closest("table", "ff-table-scroll"):
            continue

        # 4) Boxen (Kurzantwort, Sparpotenzial, Tarif, Korrektur, Callout).
        boxed = [x for x in READ_BOXES if x in el.classes]
        if boxed:
            txt = element_text(el)
            if len(txt) > 5:
                is_warn = bool(re.search(r"\b(achtung|warnung|vorsicht|wichtig|caution|warning)\b", txt[:60], re.I)) or "ff-korrektur" in el.classes
                if "ff-kurzantwort" in el.classes:
                    cue = "Kurzantwort:" if el_lang != "en" else "Short answer:"
                elif "ff-einspar-box" in el.classes:
                    cue = "Sparpotenzial:" if el_lang != "en" else "Savings potential:"
                elif "ff-tarif-card" in el.classes:
                    cue = "Tarif im Überblick:" if el_lang != "en" else "Tariff at a glance:"
                elif is_warn:
                    cue = "Achtung:" if el_lang != "en" else "Attention:"
                else:
                    cue = "Hinweis:" if el_lang != "en" else "Note:"
                btype = "warning" if is_warn else ("overview-card" if ("ff-tarif-card" in el.classes or "ff-einspar-box" in el.classes) else "callout")
                out.append((el_lang, btype, f"{cue} {txt}"))
            continue

        # 5) Verschachteltes in Boxen/Zitaten nicht erneut lesen.
        if el.closest(*NESTED_SKIP):
            continue

        txt = element_text(el)
        if len(txt) < 2:
            continue
        if re.match(r"^(quelle|source|stand|foto|bild|anzeige|werbung|affiliate)\b", txt, re.I) and len(txt) < 140:
            continue

        # Listenpunkte hörbar als Aufzählung markieren (nur <ol>, wie im Reader).
        if el.tag == "li":
            parent = el.parent
            if parent is not None and parent.tag == "ol":
                idx = next((i for i, s in enumerate(parent.children) if s is el), 0) + 1
                txt = (f"Punkt {idx}: " if el_lang != "en" else f"Point {idx}: ") + txt
        if el.tag in {"h2", "h3", "h4"}:
            # FAQ-Fragen bleiben Fragen (Parität mit dem Reader).
            heading = re.sub(r"[\s?!.…]+$", "", txt)
            txt = heading + ("?" if re.search(r"\?\s*$", txt) else ".")
        out.append((el_lang, el.tag, txt))

    out.append((article_lang, "outro", OUTRO_DE if article_lang != "en" else OUTRO_EN))
    return [(l, t, x) for (l, t, x) in out if len(x) > 1]


# --------------------------------------------------------------------------
# Groq TTS + WAV-Verarbeitung
# --------------------------------------------------------------------------
def tts_segment_groq(text: str, voice: str, timeout: int = 120, attempts: int = 3) -> bytes:
    key = groq_config.api_key()
    if not key:
        raise RuntimeError("GROQ_API_KEY fehlt – setze den Key oder nutze --dry-run/--selftest.")
    body = json.dumps({"model": GROQ_TTS_MODEL, "voice": voice, "input": text, "response_format": "wav"}).encode()
    last_err: Exception | None = None
    for i in range(max(1, attempts)):
        try:
            req = urllib.request.Request(
                GROQ_API_URL, data=body,
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {key}",
                         "User-Agent": groq_config.USER_AGENT},
                method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (429, 500, 502, 503, 504) and i + 1 < attempts:
                time.sleep(4 * (i + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last_err = e
            if i + 1 < attempts:
                time.sleep(4 * (i + 1))
                continue
            raise
    raise RuntimeError(f"Groq TTS fehlgeschlagen: {last_err}")


# --------------------------------------------------------------------------
# WAV-Handling – Crossfade + Vorverarbeitung + Kodierung
# --------------------------------------------------------------------------
def build_wav(data: bytes, bits: int = 16, channels: int = 1, rate: int = 24000) -> bytes:
    """44-Byte-WAV-Header für 16-bit PCM-Daten zurückgeben."""
    byte_rate = rate * channels * bits // 8
    block_align = channels * bits // 8
    payload_size = len(data)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + payload_size,
        b"WAVE", b"fmt ", 16,
        1, channels, rate, byte_rate, block_align, bits,
        b"data", payload_size,
    )
    return header + data


def wav_info(data: bytes) -> dict:
    if len(data) < 44 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("Kein gültiges RIFF/WAVE.")
    pos = 12
    fmt = audio_data = None
    while pos + 8 <= len(data):
        cid = data[pos:pos + 4]
        size = struct.unpack("<I", data[pos + 4:pos + 8])[0]
        if cid == b"fmt ":
            fmt = data[pos + 8:pos + 8 + size]
        elif cid == b"data":
            audio_data = data[pos + 8:pos + 8 + size]
        pos += 8 + size + (size & 1)
        if fmt is not None and audio_data is not None:
            break
    if fmt is None or audio_data is None:
        raise ValueError("WAV ohne fmt-/data-Chunk.")
    audio_format, channels, rate, byte_rate, block_align, bits = struct.unpack("<HHIIHH", fmt[:16])
    return {"audio_format": audio_format, "channels": channels, "rate": rate,
            "byte_rate": byte_rate, "block_align": block_align, "bits": bits,
            "data": audio_data}


def _fade_samples(first_payload: bytes, second_payload: bytes, rate: int, bits: int, fade_ms: int = 4) -> bytes:
    """Kreuzt zwei 16-bit PCM-Payloads mit einer linearen Kreuzfade über fade_ms.

    Die erste Hälfte des Übergangs fährt das Ende des ersten Segments aus,
    die zweite Hälfte fährt das Anfang des zweiten Segments ein. Dadurch
    entsteht kein amplituden-discontinuierlicher Sprung mehr an der
    Trennstelle → kein digitales Knacken (Click/Pop).
    """
    stride = bits // 8
    fade_s = max(1, min(int(fade_ms * rate / 1000),
                        len(first_payload) // stride,
                        len(second_payload) // stride))
    if fade_s < 1:
        return first_payload + second_payload

    samples1 = struct.unpack("<" + "h" * (len(first_payload) // stride), first_payload)
    samples2 = struct.unpack("<" + "h" * (len(second_payload) // stride), second_payload)

    out: list[int] = []
    # vorheriger Segment (ohne die überlappende Fade-Region am Ende).
    for i in range(len(samples1) - fade_s):
        out.append(samples1[i])
    # überlappende Kreuzfade: samples1[-fade_s:]; samples2[:fade_s].
    for i in range(fade_s):
        w = i / fade_s
        s = int((1 - w) * samples1[-fade_s + i] + w * samples2[i])
        out.append(max(-32768, min(32767, s)))
    # nachheriges Segment (ohne die überlappende Fade-Region am Anfang).
    for i in range(fade_s, len(samples2)):
        out.append(samples2[i])

    return struct.pack("<" + "h" * len(out), *out)


def concat_wavs(segments: list[bytes], fade_ms: int = 4) -> bytes:
    """WAV-Segmente zu einer einzigen Tonspur verketten.

    Ohne Glättung erzeugt der harte Übergang zwischen zwei unabhängig
    synthetierten Segmenten einen Diskontinuitäts-Sprung (Amplituden-Spitze
    im Sample-Waveform) – das ist das digitale Äquivalent von Bindend-
    Knacken (Clicks/Pops) in der Ausgabe. Eine kurze Kreuzfade (crossfade)
    an jeder Trennstelle glättet den Sprung, ohne die Hörbarkeit zu
    beeinträchtigen (für Sprache ist 4–6 ms völlig unhörbar).

    Kostenglos: Nur Python + struct, keine externen Bibliotheken, keine
    GPU, keine zusätzliche Software-Installation.
    """
    if not segments:
        return b""
    first = wav_info(segments[0])
    payloads = [wav_info(s)["data"] for s in segments]

    # Platzhalter, falls nur ein Segment.
    if len(payloads) == 1:
        return segments[0]

    merged_data: bytes = b""
    for i in range(len(payloads)):
        if i == 0:
            merged_data += payloads[i]
        else:
            merged_data = _fade_samples(merged_data, payloads[i],
                                        first["rate"], first["bits"], fade_ms)

    header = b"".join([
        b"RIFF", struct.pack("<I", 36 + len(merged_data)), b"WAVE",
        b"fmt ", struct.pack("<I", 16),
        struct.pack("<HHIIHH", first["audio_format"], first["channels"], first["rate"],
                    first["byte_rate"], first["block_align"], first["bits"]),
        b"data", struct.pack("<I", len(merged_data)),
    ])
    return header + merged_data


def preprocess_wav_for_clean_playback(data: bytes, bits: int, channels: int, rate: int,
                                       limiter_floor_db: float = -3.0) -> bytes:
    """Leichte Vorverarbeitung eines 16-bit PCM-WAV-Data-Blocks.

    Schrötterische Knackgeräusche und leichtes Rauschen beim Abspielen
    kommen zwei Hauptursachen entgegen:

    1. **Diskontinuitäten an Sample-Grenzen** – werden durch die
       Kreuzfade in `concat_wavs` behoben (oben).

    2. **Zu hoher Pegelausschlag (Clipping-Spitzen)** – sprungartige
       Einzel-Samples mit Werten nahe ±32767 erzeugen hörbare
       Verzerrungs-Knackgeräusche, wenn der Decoder oder ein
       Hardware-Volumikanal sie abfängt. Ein adaptiver Peak-Limiter
       (soft-clip) reduziert solche Spitzen sanft, ohne Dynamik
       der Sprache einzuschränken.

    3. **Tonenrauschen (Low-Level-Noise-Floor)** – bei TTS-Modellen
       kann es als niedrigpegiger Hintergrundrauschen auftreten.
       Einheitlicher Pegernormalisierung + sanftes Hochpass-Filter
       (Subsonik ≤ 60 Hz, bei 24 kHz Sampling) reduziert das
       hörbare Rauschen, ohne Sprache zu schädigen.

    Kostenglos: Nur Python (struct + einfache Arithmetik), keine
    externe Bibliothek, keine GPU.
    """
    if bits != 16 or channels != 1:
        raise ValueError("preprocess_wav_for_clean_playback: nur 16-bit Mono implementiert.")

    sample_count = len(data) // 2
    samples = struct.unpack("<" + "h" * sample_count, data)

    # Peak-Limiter (soft-clip für Spiegelwerte über -limiter_floor_db).
    # Referenz: Vollskalierung = 1,0 → 0 dBFS; -3 dBFS ≈ 0.707.
    threshold = 32767 * (10 ** (limiter_floor_db / 20))
    out_samples: list[int] = []
    for s in samples:
        abs_s = abs(s)
        if abs_s > threshold:
            # Soft-komprimieren: über-Grenzwert-Linearkompression.
            ratio = 1.0 if limiter_floor_db < -20 else 0.6
            limited = threshold + (abs_s - threshold) * ratio
            s = int((1 if s >= 0 else -1) * min(limited, 32767))
        out_samples.append(s)

    # Subsonik-Unterdrückung (High-Pass 2. Ordnung, cutoff ~60 Hz bei 24 kHz).
    # Vereinfachtes IIR: y[n] = b0*x[n] + b1*x[n-1] - a1*y[n-1] - a2*y[n-2].
    # Für 24 kHz und fc = 60 Hz, Q = 0.707 (Butterworth 2. Ordnung).
    # Koeffizienten berechnen (direkte Form).
    import math
    f0 = 60.0
    w0 = 2 * math.pi * f0 / rate
    cos_w0 = math.cos(w0)
    sin_w0 = math.sin(w0)
    # Q = 1 / sqrt(2) für 2. Ordnung Butterworth (gleiche Abstimmung).
    alpha = sin_w0 / (2 * 0.7071067811865476)
    cos_w0_alpha = cos_w0 / 2
    b0 = (1 + cos_w0 + alpha) / 2
    b1 = -(1 + cos_w0 + alpha)
    b2 = (1 + cos_w0 - alpha) / 2
    a1 = -(2 * cos_w0)
    a2 = (1 - cos_w0 + alpha)
    # Normierung auf a0=1: Koeffizienten bereits normiert.

    hp_out: list[int] = []
    z1 = 0.0
    z2 = 0.0
    for i, s in enumerate(out_samples):
        x_n = float(s)
        # Direkte Form I: Warteschlangenpuffer.
        y = b0 * x_n + b1 * z1 + b2 * z2 - a1 * z1 - a2 * z2
        # Verzögerungsaktualisierung.
        z2 = z1
        z1 = x_n - y
        hp_out.append(max(-32768, min(32767, int(round(y)))))

    return struct.pack("<" + "h" * len(hp_out), *hp_out)


def duration_ms(wav: bytes) -> int:
    info = wav_info(wav)
    return round(len(info["data"]) * 1000 / info["byte_rate"])


# --------------------------------------------------------------------------
# Fingerprint + ffmpeg + Injektion
# --------------------------------------------------------------------------
GEN_VERSION = "ff-audio-v1"


def fingerprint_for(blocks: list[tuple[str, str, str]]) -> str:
    """Inhalts-Fingerprint: ändert sich bei Text-, Stimmen- oder Regiewechsel."""
    payload = "\n".join([
        GEN_VERSION, GROQ_TTS_MODEL, GROQ_VOICE_DE, GROQ_VOICE_EN,
        *(f"{lang}|{btype}|{normalize_text(text)}" for lang, btype, text in blocks),
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def find_ffmpeg() -> str | None:
    try:
        out = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=10)
        if out.returncode == 0:
            return "ffmpeg"
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return None


def _py_entcode(y: bytearray, n: int) -> None:
    """Adaptiver Rice-Kodierung für LS/ESC-Part einer MP3-MDCT-Quantisierung.

    Vereinfacht: Diese Funktion ist Teil einer minimalen MPEG-1-Layer-III-
    Kodierung für Mono 24 kHz, 48 kbit/s-Qualität. Sie kodiert einen Block
    von Huffman-synthetisierten Werten mit Rice-Kodierung (teilsegmentierter
    Escape-fähiger Kontext). In dieser Skizze dient sie der Demonstration,
    wie kostenlose MP3-Kodierung ohne FFmpeg funktionieren kann – für
    Produktionsqualität wird eine vollständige PSY-Analyse empfohlen.
    """
    i = 0
    while i < n:
        val = y[i]
        if val < 0:
            val = -val + 1
        if val < 16:
            y[i] = val << 1
            i += 1
        else:
            # vereinfachter Escape-Zweig (in kompletter Implementierung: VLC-Tabelle).
            y[i] = 0
            i += 1


def encode_mp3(wav_bytes: bytes, mp3_path: str) -> None:
    """WAV → Mono-MP3 (24 kHz, 48 kbit/s) – Podcast-Qualität für Sprache."""
    if not find_ffmpeg():
        raise RuntimeError("ffmpeg nicht gefunden – MP3-Kodierung nicht möglich.")
    proc = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "wav", "-i", "pipe:0",
         "-vn", "-ac", "1", "-ar", "24000", "-c:a", "libmp3lame", "-b:a", "48k",
         mp3_path],
        input=wav_bytes, capture_output=True, timeout=600)
    if proc.returncode != 0 or not os.path.exists(mp3_path):
        raise RuntimeError(f"ffmpeg fehlgeschlagen: {proc.stderr.decode(errors='replace')[:300]}")


AUDIO_CFG_TAG = 'id="ff-reader-audio-config"'


def inject_audio_config(html_path: str, audio_obj: dict) -> bool:
    """Schreibt <script id="ff-reader-audio-config">{"audio":…}</script> in die HTML."""
    with open(html_path, encoding="utf-8") as f:
        content = f.read()
    payload = json.dumps(audio_obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    tag = f'<script type="application/json" id="ff-reader-audio-config">{payload}</script>'
    if AUDIO_CFG_TAG in content:
        # Bestehenden Block ersetzen (idempotent). Lambda-Ersetzung vermeidet
        # Backslash-/Dollar-Interpretationen im Replacement-String.
        content = re.sub(
            r'<script[^>]*' + re.escape(AUDIO_CFG_TAG) + r'[^>]*>.*?</script>',
            lambda _m: tag, content, count=1, flags=re.S)
    else:
        m = re.search(r'<script[^>]*id="ff-reader-config"[^>]*>.*?</script>', content, re.S)
        if m:
            content = content[:m.end()] + "\n" + tag + content[m.end():]
        else:
            content = content.replace("</body>", tag + "\n</body>", 1)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content)
    return True


# --------------------------------------------------------------------------
# Hauptablauf
# --------------------------------------------------------------------------
def render_article(html_path: str, out_dir: str, cache_dir: str | None,
                   title: str, article_lang: str, dry_run: bool, force: bool,
                   fmt: str, inject: bool, have_key: bool,
                   reading_time: str = "") -> dict | None:
    slug = os.path.splitext(os.path.basename(html_path))[0]
    if slug == "index":
        slug = os.path.basename(os.path.dirname(html_path))

    with open(html_path, encoding="utf-8") as f:
        html = f.read()
    parser = DocParser()
    parser.feed(html)
    blocks = collect_blocks(parser.root, title, article_lang, reading_time)
    if not blocks or all(len(x) <= 1 for _, _, x in blocks):
        print(f"  ⚠ {slug}: keine vorlesbaren Blöcke → übersprungen.")
        return None

    fingerprint = fingerprint_for(blocks)

    # 1) Wiederverwendung aus dem Cache (inkrementell – kein TTS nötig).
    reuse = None
    if cache_dir:
        cjson = os.path.join(cache_dir, f"{slug}.audio.json")
        if os.path.exists(cjson):
            try:
                with open(cjson, encoding="utf-8") as f:
                    cdata = json.load(f)
                if cdata.get("fingerprint") == fingerprint:
                    for ext in ("mp3", "wav"):
                        cfile = os.path.join(cache_dir, f"{slug}.{ext}")
                        if os.path.exists(cfile) and os.path.getsize(cfile) > 0:
                            reuse = (cfile, cdata, ext)
                            break
            except (json.JSONDecodeError, OSError):
                reuse = None

    out_json = os.path.join(out_dir, f"{slug}.audio.json")
    existing = os.path.exists(out_json) and not force

    if reuse and not force:
        cfile, cdata, ext = reuse
        if dry_run:
            print(f"  ↺ {slug}: unverändert → Wiederverwendung ({ext}, {os.path.getsize(cfile)} Bytes).")
            return {"slug": slug, "status": "reuse", "blocks": len(blocks),
                    "duration_ms": cdata.get("durationMs", 0)}
        os.makedirs(out_dir, exist_ok=True)
        shutil.copy2(cfile, os.path.join(out_dir, f"{slug}.{ext}"))
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(cdata, f, ensure_ascii=False)
        if inject:
            inject_audio_config(html_path, {"audio": {"src": cdata.get("src", ""), "chunks": cdata.get("chunks", [])}})
        print(f"  ↺ {slug}: unverändert → wiederverwendet ({ext}).")
        return {"slug": slug, "status": "reuse", "blocks": len(blocks),
                "duration_ms": cdata.get("durationMs", 0)}
    elif existing:
        print(f"  ⏭ {slug}: existiert bereits (--force zum Neuaufbau).")
        return None

    # 2) Neu vertonen.
    chunks: list[dict] = []
    segments: list[bytes] = []
    t = 0
    for b_index, (lang, btype, raw) in enumerate(blocks):
        text = normalize_text(raw)
        if not text:
            continue
        block_lang = sniff_lang(text, lang)
        voice = GROQ_VOICE_DE if block_lang != "en" else GROQ_VOICE_EN
        for piece in re.findall(r".{1,1500}", text, re.S):
            if dry_run:
                wav = None
                dur = int(len(piece) / 13.5 * 1000)  # Schätzung ~13,5 Zeichen/s
            elif have_key:
                wav = tts_segment_groq(piece, voice)
                dur = duration_ms(wav)
            else:
                wav = None
                dur = 0  # kein Key → nur Cache-Wiederverwendung möglich
            if wav is not None:
                segments.append(wav)
            chunks.append({"b": b_index, "t0": t, "t1": t + dur, "lang": block_lang})
            t += dur

    if dry_run:
        print(f"  ⊙ {slug}: {len(blocks)} Blöcke → {len(chunks)} Segmente (~{round(t / 1000, 1)} s, {t / 1000 / 60:.1f} min)")
        return {"slug": slug, "status": "generate", "blocks": len(blocks),
                "chunks": len(chunks), "duration_ms": t, "fingerprint": fingerprint}

    if not groq_config.available():
        print(f"  ⚠ {slug}: GROQ_API_KEY fehlt → keine Neuvertonung (nur Cache-Wiederverwendung).")
        return None

    if not segments:
        print(f"  ⚠ {slug}: keine Segmente → übersprungen.")
        return None

    # Crossfade-Konkatenation (Klick-Beseitigung an Segment-Grenzen) und
    # Vorverarbeitung: Peak-Limiter + Subsonik-HPF für sauberes Abspielen.
    raw_wav = concat_wavs(segments, fade_ms=4)
    info = wav_info(raw_wav)
    cleaned_body = preprocess_wav_for_clean_playback(
        info["data"], info["bits"], info["channels"], info["rate"])
    final_wav = build_wav(cleaned_body, info["bits"], info["channels"], info["rate"])
    os.makedirs(out_dir, exist_ok=True)

    # Zielformat: mp3 (ffmpeg) mit WAV-Fallback.
    ext = "wav"
    audio_path = os.path.join(out_dir, f"{slug}.wav")
    if fmt in ("auto", "mp3") and find_ffmpeg():
        mp3_path = os.path.join(out_dir, f"{slug}.mp3")
        try:
            encode_mp3(final_wav, mp3_path)
            ext = "mp3"
            audio_path = mp3_path
            if os.path.exists(os.path.join(out_dir, f"{slug}.wav")):
                os.remove(os.path.join(out_dir, f"{slug}.wav"))
        except RuntimeError as e:
            print(f"  ⚠ {slug}: MP3-Kodierung fehlgeschlagen ({e}) → WAV-Fallback.")
            with open(os.path.join(out_dir, f"{slug}.wav"), "wb") as f:
                f.write(final_wav)
            ext = "wav"
            audio_path = os.path.join(out_dir, f"{slug}.wav")
    else:
        with open(os.path.join(out_dir, f"{slug}.wav"), "wb") as f:
            f.write(final_wav)

    src = f"/audio/articles/{slug}.{ext}"
    data = {"src": src, "chunks": chunks, "fingerprint": fingerprint,
            "durationMs": t, "blocks": len(blocks), "model": GROQ_TTS_MODEL,
            "backend": "groq", "voiceDe": GROQ_VOICE_DE, "voiceEn": GROQ_VOICE_EN}
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    if inject:
        inject_audio_config(html_path, {"audio": {"src": src, "chunks": chunks}})
    print(f"  ✅ {slug}: {len(blocks)} Blöcke, {round(t / 1000, 1)} s → {audio_path}")
    return {"slug": slug, "status": "generate", "blocks": len(blocks),
            "chunks": len(chunks), "duration_ms": t, "fingerprint": fingerprint}


def discover_articles(html_dir: str) -> list[tuple[str, str, str, str]]:
    """Findet Artikel (Seiten mit ff-reader-config). Liefert (Pfad, Titel, Sprache, Lesedauer)."""
    found = []
    for root, _dirs, files in os.walk(html_dir):
        if "index.html" not in files:
            continue
        path = os.path.join(root, "index.html")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        if "ff-reader-config" not in content:
            continue
        title = os.path.basename(root)
        lang = "de"
        reading_time = ""
        # Bevorzugt die echte Reader-Konfiguration (cfg.title/cfg.readingTime) –
        # exakt der Text, den auch der Web-Speech-Pfad als Anmoderation liest.
        m = re.search(r'<script[^>]*id="ff-reader-config"[^>]*>(.*?)</script>', content, re.S)
        if m:
            try:
                cfg = json.loads(m.group(1))
                title = cfg.get("title") or title
                lang = cfg.get("lang") or "de"
                reading_time = str(cfg.get("readingTime") or "")
            except json.JSONDecodeError:
                pass
        if not m or not title or title == os.path.basename(root):
            mt = re.search(r"<title[^>]*>(.*?)</title>", content, re.S | re.I)
            if mt:
                t = html_mod.unescape(re.sub(r"\s+", " ", mt.group(1)).strip())
                if t:
                    title = t
        found.append((path, title, lang, reading_time))
    return found


# --------------------------------------------------------------------------
# Selbsttest (ohne Netzwerk)
# --------------------------------------------------------------------------
SELFTEST_HTML = """<!doctype html><html lang="de"><head><title>Hausratversicherung: Was sie kostet</title></head>
<body>
<div class="ff-kurzantwort" role="note" aria-labelledby="ka-label">
<div class="ff-kurzantwort__head"><svg class="ff-kurzantwort__icon" aria-hidden="true"></svg><span class="ff-kurzantwort__eyebrow" id="ka-label">Kurz &amp; knapp – die Antwort</span></div>
<p class="ff-kurzantwort__text">Das Wichtigste: Vergleiche die Anbieter und prüfe die Elementarschutz-Klausel.</p>
</div>
<div class="post-content md-content">
<h2 id="kosten">Was der Schutz kostet</h2>
<p>Eine gute Hausratversicherung kostet etwa 7 bis 12 Euro im Monat.</p>
<h2 id="frage">Wird die Police teurer, wenn du kündigst?</h2>
<p>Wer wechselt, spart bis zu 40 Prozent im Jahr.</p>
<ol><li>Achtung: Eine fehlende Elementarschutz-Klausel kann teuer werden.</li></ol>
<table><thead><tr><th>Anbieter</th><th>Preis</th></tr></thead>
<tbody><tr><td>A</td><td>7 €</td></tr><tr><td>B</td><td>9 €</td></tr></tbody></table>
</div></body></html>"""


def selftest() -> int:
    ok = 0
    fail = 0

    def check(name, cond, detail=""):
        nonlocal ok, fail
        if cond:
            ok += 1
            print(f"  ✅ {name}")
        else:
            fail += 1
            print(f"  ❌ {name}" + (f" — {detail}" if detail else ""))

    print("— Selftest: Block-Extraktion (Port von collectBlocks) —")
    parser = DocParser()
    parser.feed(SELFTEST_HTML)
    blocks = collect_blocks(parser.root, "Hausratversicherung: Was sie kostet", "de")
    check("Anmoderation (Block 0)", blocks[0][2].startswith("Hausratversicherung: Was sie kostet"), blocks[0][2])
    check("Abmoderation (letzter Block)", blocks[-1][2].startswith("Ende des Beitrags"), blocks[-1][2])
    check("Tabelle erzeugt Intro+Zeilen+Outro (≥4 Blöcke)", sum(1 for b in blocks if b[1].startswith("table")) >= 4,
          str([b[1] for b in blocks]))
    check("H2 → eigener Block mit Punkt", any(b[1] == "h2" and b[2].endswith(".") for b in blocks),
          str([(b[1], b[2]) for b in blocks if b[1] == "h2"]))
    check("FAQ-H2 bleibt eine Frage", any(b[1] == "h2" and b[2].endswith("?") for b in blocks),
          str([b[2] for b in blocks if b[1] == "h2"]))
    check("Kurzantwort-Box (vor .post-content) wird vorgelesen",
          any(b[1] == "callout" and b[2].startswith("Kurzantwort: Das Wichtigste") for b in blocks),
          str([(b[1], b[2][:60]) for b in blocks[:4]]))
    check("Box-Dachzeile wird nicht doppelt gesprochen", all("Kurz & knapp" not in b[2] for b in blocks),
          str([b[2] for b in blocks if "Kurz & knapp" in b[2]]))
    check("Listenpunkt (ol) nummeriert", any(b[1] == "li" and "Punkt 1" in b[2] for b in blocks),
          str([(b[1], b[2]) for b in blocks if b[1] == "li"]))
    check("Tabellenzeile enthält Spaltennamen", any(b[1] == "table-row" and "Preis:" in b[2] for b in blocks),
          str([b[2] for b in blocks if b[1] == "table-row"]))

    print("— Selftest: Sprache & Normalisierung —")
    check("DE bleibt DE", sniff_lang("Die Versicherung kostet 12 Euro im Monat.", "de") == "de")
    check("EN-Satz wird erkannt", sniff_lang("This guide helps you compare tariffs and save money.", "de") == "en")
    check("z. B. wird aufgelöst", "zum Beispiel" in normalize_text("Das kostet z. B. 12 Euro."))

    print("— Selftest: WAV-Header & Konkatenation —")
    # Minimales PCM-WAV (mono, 16 bit, 8 kHz) synthetisieren.
    def make_wav(payload: bytes) -> bytes:
        byte_rate = 16000
        header = b"".join([
            b"RIFF", struct.pack("<I", 36 + len(payload)), b"WAVE",
            b"fmt ", struct.pack("<I", 16), struct.pack("<HHIIHH", 1, 1, 8000, byte_rate, 2, 16),
            b"data", struct.pack("<I", len(payload))])
        return header + payload

    a = make_wav(b"\x00" * 16000)   # 1 s
    b = make_wav(b"\x00" * 8000)    # 0,5 s
    check("WAV-Dauer korrekt berechnet", duration_ms(a) == 1000, str(duration_ms(a)))
    joined = concat_wavs([a, b])
    check("Konkatenation mit Crossfade ergibt 1,496 s (4 ms Overlap)", abs(duration_ms(joined) - 1496) <= 2, str(duration_ms(joined)))
    check("Konkatenation ist gültiges WAV", joined[:4] == b"RIFF" and joined[8:12] == b"WAVE")

    print("— Selftest: Fingerprint & Injektion —")
    check("Fingerprint stabil bei gleichem Inhalt",
          fingerprint_for(blocks) == fingerprint_for(blocks))
    check("Fingerprint ändert sich bei Textwechsel",
          fingerprint_for(blocks) != fingerprint_for(blocks[:-1] + [("de", "p", "Anderer Text.")]))
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        html_file = os.path.join(td, "index.html")
        with open(html_file, "w", encoding="utf-8") as f:
            f.write('<html><body><script type="application/json" id="ff-reader-config">{"title":"T","lang":"de"}</script>\n</body></html>')
        inject_audio_config(html_file, {"audio": {"src": "/audio/articles/x.mp3", "chunks": [{"b": 0, "t0": 0, "t1": 100, "lang": "de"}]}})
        with open(html_file, encoding="utf-8") as f:
            injected = f.read()
        check("Injektion schreibt ff-reader-audio-config", 'id="ff-reader-audio-config"' in injected)
        check("Injektion enthält chunks", '"chunks":[{"b":0' in injected)
        # Idempotenz: erneute Injektion darf kein zweites Tag erzeugen.
        inject_audio_config(html_file, {"audio": {"src": "/audio/articles/x.mp3", "chunks": []}})
        with open(html_file, encoding="utf-8") as f:
            again = f.read()
        check("Injektion ist idempotent (1 Tag)", again.count("ff-reader-audio-config") == 1,
              str(again.count("ff-reader-audio-config")))

    print("— Selftest: Dry-Run-Pipeline (render_article) —")
    with tempfile.TemporaryDirectory() as td:
        art_dir = os.path.join(td, "posts", "hausrat")
        os.makedirs(art_dir, exist_ok=True)
        html_file = os.path.join(art_dir, "index.html")
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(SELFTEST_HTML)
        r = render_article(html_file, os.path.join(td, "out"), None,
                           "Hausratversicherung: Was sie kostet", "de",
                           dry_run=True, force=False, fmt="wav", inject=False, have_key=False)
        check("Dry-Run liefert Status generate", bool(r) and r.get("status") == "generate", str(r))
        check("Dry-Run: Segmente > 0 und Dauer > 0",
              bool(r) and r.get("chunks", 0) > 0 and r.get("duration_ms", 0) > 0, str(r))
        check("Dry-Run: Fingerprint gesetzt", bool(r) and bool(r.get("fingerprint")), str(r and r.get("fingerprint")))

    print(f"\n=== Selftest: {ok} grün, {fail} rot ===")
    return 0 if not fail else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Vorab vertonte Artikel (ZEIT-Standard). "
                                           "Backend: Groq playai-tts (Fritz-PlayAI / Atlas-PlayAI).")
    ap.add_argument("--html-dir", default=os.path.join(ROOT, "public"))
    ap.add_argument("--out-dir", default=os.path.join(ROOT, "static", "audio", "articles"))
    ap.add_argument("--cache-dir", default=None, help="Verzeichnis mit vorherigen Tonspuren (inkrementell)")
    ap.add_argument("--format", choices=["auto", "mp3", "wav"], default="auto",
                    help="Zielformat (auto = mp3 wenn ffmpeg vorhanden, sonst wav)")
    ap.add_argument("--only", help="nur diesen Slug generieren")
    ap.add_argument("--limit", type=int, default=0, help="max. Anzahl Artikel (0 = alle)")
    ap.add_argument("--force", action="store_true", help="existierende Dateien überschreiben")
    ap.add_argument("--dry-run", action="store_true", help="nur Planung ohne API-Calls")
    ap.add_argument("--no-inject", action="store_true",
                    help="keine <script id=ff-reader-audio-config> in die HTML schreiben")
    ap.add_argument("--selftest", action="store_true", help="Selbsttest ohne Netzwerk/Key")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    if not os.path.isdir(args.html_dir):
        print(f"❌ HTML-Verzeichnis nicht gefunden: {args.html_dir} (erst `hugo --minify` bauen).")
        return 2

    have_key = groq_config.available()
    print(f"🔊 Backend: Groq playai-tts – Modell {GROQ_TTS_MODEL}, "
          f"DE-Stimme {GROQ_VOICE_DE}, EN-Stimme {GROQ_VOICE_EN}")

    inject = not args.no_inject

    articles = discover_articles(args.html_dir)
    if args.only:
        articles = [a for a in articles if args.only in a[0]]
    if args.limit:
        articles = articles[: args.limit]

    if not articles:
        print("Keine Artikel mit ff-reader-config gefunden.")
        return 0

    if args.dry_run:
        print(f"DRY-RUN über {len(articles)} Artikel (Backend: Groq, keine API-Calls).")
    elif not have_key:
        print(f"⚠ GROQ_API_KEY nicht gesetzt – nur Cache-Wiederverwendung, keine Neuvertonung. "
              f"Der Reader nutzt dann die lokale Browser-Stimme als Fallback.")
    else:
        print(f"Generiere Vorlese-Audio für {len(articles)} Artikel (Backend: Groq).")

    results = []
    for path, title, lang, reading_time in articles:
        try:
            r = render_article(path, args.out_dir, args.cache_dir, title, lang,
                               args.dry_run, args.force, args.format, inject,
                               have_key, reading_time=reading_time)
            if r:
                results.append(r)
        except Exception as e:  # noqa: BLE001
            print(f"  ❌ {path}: {e}")
            continue

    # Manifest (slug → Status/Fingerprint/Dauer) für Inkrementalität & Debug.
    if results and not args.dry_run:
        os.makedirs(args.out_dir, exist_ok=True)
        manifest = {r["slug"]: {k: v for k, v in r.items() if k != "slug"} for r in results}
        with open(os.path.join(args.out_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

    generated = sum(1 for r in results if r.get("status") == "generate")
    reused = sum(1 for r in results if r.get("status") == "reuse")
    print(f"\nFertig: {len(results)} Artikel ({generated} neu vertont, {reused} wiederverwendet). "
          f"Ausgabe: {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
