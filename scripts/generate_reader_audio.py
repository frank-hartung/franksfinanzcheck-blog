#!/usr/bin/env python3
"""generate_reader_audio.py — Vorab vertonte Artikel (ZEIT-Standard, v8).

Vertont die Artikel des Blogs mit einer MÄNNLICHEN DE- & EN-Stimme –
komplett kostenlos und ohne Umschalter für die Leser:innen.

v8 (04.09.2026) – Warum dieses Update nötig war
  Groq hat `playai-tts` (Fritz-PlayAI / Atlas-PlayAI) am 31.12.2025
  abgeschaltet; der Ersatz `canopylabs/orpheus-v1-english` kann kein
  Deutsch (https://console.groq.com/docs/deprecations). Der Generator
  lief damit seit Januar 2026 ins Leere, und der Reader fiel still auf
  die geräteabhängige Browser-Stimme zurück. Neu ist deshalb eine
  Backend-Kette aus drei kostenlosen Engines (Details, Stimmen, Lizenzen
  und die gesamte Sprach-/Prosodie-Logik stehen in
  `scripts/reader_tts_backends.py`):

    edge   (Voreinstellung)  Microsoft-Edge-Neuralstimmen über das offene
                            Paket `edge-tts`: kein Key, kein Konto, keine
                            Zeichenkosten. Männlich DE
                            `de-DE-FlorianMultilingualNeural`
                            (Multilingual v2 – spricht englische
                            Fachbegriffe im deutschen Satz in derselben
                            Stimme, kein Timbresprung), EN
                            `en-US-AndrewMultilingualNeural`.
                            Profil „narrator": `de-DE-ConradNeural` +
                            `en-GB-RyanNeural`. High-End-Priorität.
    piper  (Offline-Fallback) Lokale ONNX-Stimmen (`de_DE-thorsten-high`,
                            `de_DE-karlsson-low` für DE, `en_US-ryan-high`
                            / `en_GB-alan-medium` für EN): offline,
                            unbegrenzt, lizenzsauber, deterministisch.
    groq                   Nur EN-Notnagel (Orpheus), braucht Key.

  Ohne verfügbares Backend wird keine Tonspur geschrieben; der Reader
  bleibt dann beim lokalen Web-Speech-Pfad (niemals stumm).

Natürlichkeits-Regie (alles kostenlos, alles hier im Repo)
  1. Aussprache-Normalisierung: Zahlen, Währungen, Daten, Zeiten,
     Prozente, Paragraphen, Abkürzungen, Akronyme und URLs werden vor
     der Synthese in gesprochene Sprache übersetzt (DE/EN getrennt).
  2. Satzweises DE/EN-Routing: englische Sätze im deutschen Artikel
     spricht die männliche EN-Stimme – ohne Umschalter.
  3. Rollen-Prosodie: Überschrift, Warnbox, Tabellenzeile und Fließtext
     bekommen eigenes Tempo, eigene Tonlage und eigene Lautstärke.
  4. Echte Pausen: Stille an den Segmenträndern wird abgeschnitten und
     danach rollengerecht neu eingesetzt (Atem- statt Maschinenrhythmus).
  5. Satzgenaue Timeline aus echten Wortgrenzen (edge-tts) statt
     Zeichenschätzung → die Markierung im Reader sitzt.
  6. Klickfreie Equal-Power-Übergänge, Hochpass 70 Hz (korrekte
     Biquad-Implementierung), Peak-Limiter und EBU-R128-Lautheit
     −16 LUFS / −1,5 dBTP über ffmpeg.

Rauschen/Knacken/Hetzen werden automatisch beseitigt (kein Extra-Regler):
Heal-Kette je Segment (Trim, DC, Declick, Auto-Tempo, 10-ms-Fade),
Mastering (Hochpass 80 Hz, Declick, Denoise, Soft-Limit, −16 LUFS),
MP3 64 kbit/s Mono 24 kHz. Stille wird hart an Sprache gesetzt
(kein Equal-Power-Join Stille+Sprache).

Der Reader (static/premium/ff-reader.js) bevorzugt die Tonspur, wenn sie
existiert, und fällt sonst automatisch auf die lokale Browser-Stimme
zurück. Der Vertrag bleibt unverändert:
`cfg.audio = { src, chunks: [{ b, t0, t1, lang }] }`.

Aufruf (lokal oder im Deploy-Workflow NACH `hugo --minify`):
  python3 scripts/generate_reader_audio.py --html-dir public \
      --out-dir public/audio/articles --cache-dir /tmp/ff-audio-cache \
      --backend auto --profile natural [--only <slug>] [--dry-run] [--force]

  · --backend     auto (edge → piper → groq) | edge | piper | groq
  · --profile     natural (Multilingual v2) | narrator (Conrad/Ryan)
  · --voice-de/-en  explizite Stimmen-Override (Redaktionsentscheidung)
  · --out-dir     Zielverzeichnis (Deploy: public/audio/articles; lokal:
                  static/audio/articles). Pro Artikel entstehen
                  <slug>.mp3 (Fallback .wav ohne ffmpeg) + <slug>.audio.json.
  · --cache-dir   Vorherige Tonspuren (z. B. aus dem letzten gh-pages-Stand).
                  Unveränderte Artikel werden 1:1 wiederverwendet
                  (Fingerprint inkl. Backend/Stimme/Rezept-Version), nur
                  neue/geänderte Artikel werden neu vertont → inkrementell.
  · --limit-new   max. Anzahl NEU vertonter Artikel je Lauf (0 = alle);
                  schützt die CI-Laufzeit und die Gratis-Kontingente.
  · Injektion     Der Generator schreibt zusätzlich
                  <script type="application/json" id="ff-reader-audio-config">
                  in jede Artikel-HTML.

Diagnose & Selbsttests (ohne Netzwerk/Key):
  python3 scripts/generate_reader_audio.py --selftest
  python3 scripts/generate_reader_audio.py --engines
  python3 scripts/reader_tts_backends.py --selftest
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
from datetime import datetime
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import groq_config  # noqa: E402  (API-URL-Muster, Key, User-Agent)
import reader_tts_backends as ttb  # noqa: E402  (kostenlose Stimmen-Kette, Aussprache, Prosodie)

# --------------------------------------------------------------------------
# Backend-Konfiguration (kostenlos, männlich, DE + EN ohne Umschalter)
# --------------------------------------------------------------------------
# Das Reader-JS (ff-reader.js) und die Toolbar werden NICHT berührt –
# sie prüfen nur, ob cfg.audio existiert, und spielen es ab.
#
# Die Engine-Logik (Stimmen-Kette, Rollen-Prosodie, Aussprache-
# Normalisierung, Audio-Bausteine) liegt in scripts/reader_tts_backends.py,
# damit Generator, A/B-Hörtest und Selbsttests dieselbe Quelle benutzen.
DEFAULT_BACKEND = os.environ.get("FF_AUDIO_BACKEND", "auto")       # auto|edge|piper|groq
DEFAULT_PROFILE = os.environ.get("FF_AUDIO_PROFILE", "natural")    # natural|narrator
DEFAULT_BITRATE = int(os.environ.get("FF_AUDIO_BITRATE", "64"))    # kbit/s, Mono 24 kHz
DEFAULT_LUFS = float(os.environ.get("FF_AUDIO_LUFS", "-16"))       # EBU R128 Ziellautheit
DEFAULT_PEAK_DB = -1.5                                             # True-Peak-Grenze
MAX_PAUSE_MS = 900          # Obergrenze einer Sprechpause (sonst wirkt es zerrissen)
ESTIMATE_CHARS_PER_SEC = 12.0   # Dry-Run-Schätzung ohne Engine (ruhiges Nachrichtentempo)
# Deploy-Schutz: Fällt der Sprachdienst aus (Netz, Sperre, Kontingent), würde
# sonst jeder Satz jedes Artikels einzeln scheitern – mit Wiederholung und
# Wartezeit. Nach so vielen Fehlern in Folge wird der Artikel abgebrochen.
MAX_CONSECUTIVE_FAILURES = 6

# Legacy-Umgebungsvariablen: nur noch für den Groq-EN-Notnagel relevant.
GROQ_API_URL = ttb.GroqBackend.API_URL
GROQ_TTS_MODEL = ttb.GroqBackend.MODEL
GROQ_VOICE_DE = os.environ.get("FF_AUDIO_VOICE_DE", "")   # Orpheus kann kein Deutsch
GROQ_VOICE_EN = os.environ.get("FF_AUDIO_VOICE_EN", "")

INTRO_DE = "{title}. Ein Beitrag von FranksFinanzcheck. Hördauer etwa {time} Minuten."
INTRO_EN = "{title}. An article by FranksFinanzcheck. Listening time about {time} minutes."
OUTRO_DE = "Ende des Beitrags. Vielen Dank fürs Zuhören bei FranksFinanzcheck."
OUTRO_EN = "End of article. Thank you for listening to FranksFinanzcheck."


# --------------------------------------------------------------------------
# Sprache (DE/EN) & Aussprache – delegiert an reader_tts_backends
# --------------------------------------------------------------------------
def sniff_lang(text: str, base: str) -> str:
    """DE/EN-Erkennung auf Satzebene (Quelle: reader_tts_backends)."""
    return ttb.sniff_lang(text, base)


def normalize_text(text: str, lang: str = "de") -> str:
    """Geschriebener Text → gesprochener Text.

    Zahlen, Währungen, Daten, Zeiten, Prozente, Paragraphen, Abkürzungen,
    Akronyme und URLs werden sprachabhängig aufgelöst. Das ist der größte
    kostenlose Natürlichkeits-Hebel: „1.299,50 €" wird zu
    „eintausendzweihundertneunundneunzig Euro und fünfzig Cent" statt zu
    „eins Punkt zweitausendneunundneunzig Komma fünfzig Euro".
    """
    out = ttb.speech_normalize(text or "", lang or "de")
    out = re.sub(r"\s+", " ", out).strip()
    if out and not re.search(r"[.!?…:,]$", out):
        out += "."
    return out


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
# Synthese: Backend-Kette + WAV-Verarbeitung
# --------------------------------------------------------------------------
def tts_segment_groq(text: str, voice: str, timeout: int = 120, attempts: int = 3) -> bytes:
    """Legacy-Helfer: ein Groq-Segment als WAV (nur noch Englisch nutzbar).

    Groq hat playai-tts am 31.12.2025 abgeschaltet; der Ersatz
    `canopylabs/orpheus-v1-english` kennt kein Deutsch. Der reguläre Pfad
    läuft deshalb über reader_tts_backends.Engine (edge → piper → groq).
    """
    unit = ttb.Unit(block=0, text=text, lang="en", role="p", rate=1.0, pitch=1.0,
                    volume=1.0, before_ms=0, after_ms=0, final=True)
    backend = ttb.GroqBackend(profile=DEFAULT_PROFILE, voice_en=voice or None)
    backend.voice_for("en")
    res = backend.synthesize(unit)
    return ttb.build_wav(res.pcm, res.rate)


def build_wav(data: bytes, bits: int = 16, channels: int = 1, rate: int = 24000) -> bytes:
    """44-Byte-WAV-Header für 16-bit-Mono-PCM-Daten."""
    if bits != 16 or channels != 1:
        raise ValueError("build_wav: nur 16-bit Mono unterstützt.")
    return ttb.build_wav(data, rate)


def wav_info(data: bytes) -> dict:
    """Metadaten eines RIFF/WAVE-Puffers (Kompatibilitäts-Schnitt)."""
    pcm, rate = ttb.wav_pcm(data)
    channels, bits = 1, 16
    return {"audio_format": 1, "channels": channels, "rate": rate,
            "byte_rate": rate * channels * bits // 8,
            "block_align": channels * bits // 8, "bits": bits, "data": pcm}


def _fade_samples(first_payload: bytes, second_payload: bytes, rate: int,
                  bits: int = 16, fade_ms: int = 4) -> bytes:
    """Klickfreie Verbindung zweier PCM-Segmente (Equal-Power-Kreuzfade)."""
    return ttb.equal_power_fade(first_payload, second_payload, rate, fade_ms)


def concat_wavs(segments: list[bytes], fade_ms: int = 4) -> bytes:
    """WAV-Segmente zu einer einzigen Tonspur verketten.

    Ohne Glättung erzeugt der harte Übergang zwischen zwei unabhängig
    synthetisierten Segmenten einen Amplitudensprung – das digitale
    Äquivalent zu Knacken (Clicks/Pops). Die Equal-Power-Kurve hält die
    Energie über den Übergang konstant, eine lineare Kreuzfade würde bei
    Sprache einen hörbaren Pegelknick erzeugen.
    """
    if not segments:
        return b""
    if len(segments) == 1:
        return segments[0]
    pcm, rate = ttb.wav_pcm(segments[0])
    for seg in segments[1:]:
        pcm2, rate2 = ttb.wav_pcm(seg)
        if rate2 != rate:
            raise ValueError(f"concat_wavs: Abtastraten unterscheiden sich ({rate} vs {rate2}).")
        pcm = ttb.equal_power_fade(pcm, pcm2, rate, fade_ms)
    return ttb.build_wav(pcm, rate)


def preprocess_wav_for_clean_playback(data: bytes, bits: int, channels: int, rate: int,
                                      limiter_floor_db: float = -3.0) -> bytes:
    """Segment-Bereinigung: Hochpass 70 Hz + sanfter Peak-Limiter.

    Drei typische Störquellen kosten TTS Natürlichkeit:
      1. Diskontinuitäten an Segmentgrenzen → Equal-Power-Kreuzfade.
      2. Clipping-Spitzen → weicher Limiter ab limiter_floor_db.
      3. Subsonik/Brummen unterhalb der Sprache → Butterworth-Hochpass.

    Hinweis zur Historie: Die frühere Fassung benutzte eine falsche
    Zustandsführung im Filter (z1 = x − y) und erzeugte damit selbst
    Artefakte. Ersetzt durch die geprüfte Biquad-Implementierung in
    reader_tts_backends.highpass_pcm.
    """
    if bits != 16 or channels != 1:
        raise ValueError("preprocess_wav_for_clean_playback: nur 16-bit Mono implementiert.")
    pcm = ttb.highpass_pcm(data, rate, fc=70.0)
    threshold = 32767 * (10 ** (limiter_floor_db / 20))
    samples = ttb.pcm_to_samples(pcm)
    out = []
    for s in samples:
        a = abs(s)
        if a > threshold:
            limited = threshold + (a - threshold) * 0.6
            s = int((1 if s >= 0 else -1) * min(limited, 32767))
        out.append(s)
    return ttb.pcm_from_samples(out)


def duration_ms(wav: bytes) -> int:
    info = wav_info(wav)
    return round(len(info["data"]) * 1000 / info["byte_rate"])


def pcm_duration_ms(pcm: bytes, rate: int) -> int:
    return round(len(pcm) * 1000 / (rate * 2))


# --------------------------------------------------------------------------
# Sprech-Regie: Pausen, Timeline, Verdichtung auf Blockebene
# --------------------------------------------------------------------------
def estimate_ms(text: str, rate: float) -> int:
    """Dauerschätzung für den Dry-Run (ohne Engine, ~13,5 Zeichen/s)."""
    chars = len(re.sub(r"\s+", " ", text or "").strip())
    speed = max(0.5, ESTIMATE_CHARS_PER_SEC * (rate or 1.0))
    return int(chars / speed * 1000)


def pause_before_ms(units: list, i: int) -> int:
    """Atempause vor Einheit i: Nachpause des Vorgängers ODER eigene
    Vorpause – whichever größer, nie die Summe.

    Zwei aufeinanderfolgende Pausen (Absatzende + Überschriftenanfang)
    würden zusammen über eine Sekunde Stille ergeben und klingen wie ein
    Verbindungsfehler, nicht wie ein Sprecher.
    """
    if i <= 0 or not units:
        return min(MAX_PAUSE_MS, int(units[0].before_ms) if units else 0)
    prev = units[i - 1]
    return min(MAX_PAUSE_MS, max(int(prev.after_ms), int(units[i].before_ms)))


def synthesize_track(units: list, engine, dry_run: bool = False,
                     on_progress=None) -> dict:
    """Sprech-Einheiten → eine Tonspur + satzgenaue Timeline.

    Rückgabe: {"pcm", "rate", "chunks", "timeline", "engines", "failures"}.
      chunks   Satzgranularität: {"b","t0","t1","lang","role","text"}
      timeline dito, zusätzlich mit echten Wortgrenzen (edge-tts),
               nur für die Sidecar-JSON – NICHT für die HTML-Injektion
               (sonst bläht sich jede Artikelseite um zig Kilobyte auf).
      Eine fehlgeschlagene Einheit zählt als Failure; der Aufrufer
      entscheidet, ob ein lückenhafter Track geschrieben wird (Voreinstellung:
      nein – lieber die Browser-Stimme als ein Satz, der fehlt).
    """
    rate = ttb.TARGET_RATE
    chunks: list[dict] = []
    timeline: list[dict] = []
    engines: dict[str, str] = {}
    failures: list[dict] = []
    pcm_parts: list[bytes] = []
    consecutive = 0
    t = 0

    for i, u in enumerate(units):
        pause = pause_before_ms(units, i)
        if dry_run:
            dur = estimate_ms(u.text, u.rate)
            t += pause
            t0, t = t, t + dur
            chunks.append({"b": u.block, "t0": t0, "t1": t, "lang": u.lang,
                           "role": u.role, "text": u.text})
            continue

        res = None
        err = None
        # Wiederholung und Wartezeit nur beim ersten Fehler: Ist der Dienst
        # einmal down, kostet jeder weitere Versuch Sekunden ohne Aussicht auf
        # Erfolg – im Deploy summiert sich das sonst auf Minuten.
        for attempt in range(1 if consecutive else 2):
            try:
                res = engine.synthesize(u)
                break
            except Exception as e:  # noqa: BLE001 – Engine-Fehler sind erwartbar
                err = e
                if not consecutive:
                    time.sleep(1.5 * (attempt + 1))
        if res is None:
            consecutive += 1
            failures.append({"b": u.block, "lang": u.lang, "role": u.role,
                             "text": u.text[:80], "error": str(err)[:200]})
            if consecutive >= MAX_CONSECUTIVE_FAILURES:
                failures.append({
                    "b": u.block, "lang": u.lang, "role": "abbruch", "text": "",
                    "error": f"Abbruch: {consecutive} Einheiten in Folge fehlgeschlagen "
                             f"(Sprachdienst nicht erreichbar?) – die restlichen "
                             f"{len(units) - i - 1} Einheiten wurden übersprungen."})
                break
            continue

        if res.rate != rate and not pcm_parts and not chunks:
            # Erstes Segment bestimmt die Spurrate (z. B. Piper 22,05 kHz ohne
            # ffmpeg) – so scheitert ein Artikel nicht an einer Abtastrate.
            rate = res.rate
        if res.rate != rate:
            try:
                res_pcm = ttb.ffmpeg_decode(ttb.build_wav(res.pcm, res.rate), rate)
            except RuntimeError:
                res_pcm = ttb.resample_pcm_linear(res.pcm, res.rate, rate)
        else:
            res_pcm = res.pcm
        # Stille an den Rändern kappen, dann rollengerecht neu einsetzen:
        # Neural-Engines liefern oft 200–500 ms „tote Luft" pro Satz –
        # der Rhythmus wirkt dadurch schleppend und unsicher.
        # Automatische Fehlerbeseitigung + Tempo + Knackschutz, BEVOR
        # die Dauer gemessen wird – sonst läuft die Timeline der
        # gedehnten Tonspur davon. Stille wird hinterher hart an die
        # Sprache gesetzt (kein Equal-Power-Join Stille+Sprache).
        res_pcm = ttb.heal_segment(res_pcm, rate, text=u.text, lang=u.lang)
        if ttb.segment_is_broken(res_pcm, rate):
            recovered = False
            if consecutive == 0:
                try:
                    time.sleep(0.35)
                    res2 = engine.synthesize(u)
                    if res2.rate != rate:
                        try:
                            pcm2 = ttb.ffmpeg_decode(ttb.build_wav(res2.pcm, res2.rate), rate)
                        except RuntimeError:
                            pcm2 = ttb.resample_pcm_linear(res2.pcm, res2.rate, rate)
                    else:
                        pcm2 = res2.pcm
                    pcm2 = ttb.heal_segment(pcm2, rate, text=u.text, lang=u.lang)
                    if not ttb.segment_is_broken(pcm2, rate):
                        res, res_pcm, recovered = res2, pcm2, True
                except Exception:  # noqa: BLE001
                    recovered = False
            if not recovered:
                consecutive += 1
                failures.append({"b": u.block, "lang": u.lang, "role": u.role,
                                 "text": u.text[:80],
                                 "error": "stilles oder abgebrochenes Segment"})
                if consecutive >= MAX_CONSECUTIVE_FAILURES:
                    failures.append({
                        "b": u.block, "lang": u.lang, "role": "abbruch", "text": "",
                        "error": f"Abbruch: {consecutive} Einheiten in Folge fehlgeschlagen "
                                 f"(Sprachdienst nicht erreichbar?) – die restlichen "
                                 f"{len(units) - i - 1} Einheiten wurden übersprungen."})
                    break
                continue
        consecutive = 0
        dur = pcm_duration_ms(res_pcm, rate)

        if pause > 0:
            pcm_parts.append(ttb.pcm_silence(pause, rate))
        pcm_parts.append(res_pcm)
        t += pause
        t0 = t
        t += dur
        engines[u.lang] = f"{res.backend}:{res.voice}"
        chunks.append({"b": u.block, "t0": t0, "t1": t, "lang": u.lang,
                       "role": u.role, "text": u.text})
        entry = {"b": u.block, "t0": t0, "t1": t, "lang": u.lang, "role": u.role,
                 "text": u.text, "engine": engines[u.lang]}
        if res.words:
            entry["words"] = [[max(t0, t0 + int(w.get("offset_ms", 0))),
                               int(w.get("duration_ms", 0)), w.get("text", "")]
                              for w in res.words]
        timeline.append(entry)
        if on_progress:
            on_progress(i, len(units), u, dur)

    return {"pcm": b"".join(pcm_parts), "rate": rate, "chunks": chunks,
            "timeline": timeline, "engines": engines, "failures": failures,
            "duration_ms": t}


def _micro_fade(pcm: bytes, rate: int, fade_ms: int = 10) -> bytes:
    """10 ms Ein-/Ausblendung am Segmentrand (Knackschutz)."""
    return ttb.micro_fade_pcm(pcm, rate, fade_ms=fade_ms)


def block_chunks(chunks: list[dict]) -> list[dict]:
    """Satz-Timeline → Block-Timeline (Reader-Vertrag: ein Chunk je Block).

    Die Blocksprache ist diejenige, die die meiste Sprechzeit abdeckt –
    ein Block mit einem englischen Zitat bleibt damit deutsch markiert.
    """
    out: list[dict] = []
    per_block: dict[int, dict] = {}
    for c in chunks:
        b = c["b"]
        agg = per_block.setdefault(b, {"b": b, "t0": c["t0"], "t1": c["t1"], "ms": {}})
        agg["t0"] = min(agg["t0"], c["t0"])
        agg["t1"] = max(agg["t1"], c["t1"])
        span = max(0, c["t1"] - c["t0"])
        agg["ms"][c["lang"]] = agg["ms"].get(c["lang"], 0) + span
    for b in sorted(per_block):
        agg = per_block[b]
        lang = max(agg["ms"].items(), key=lambda kv: kv[1])[0] if agg["ms"] else "de"
        out.append({"b": b, "t0": agg["t0"], "t1": agg["t1"], "lang": lang})
    return out


def polish_track(pcm: bytes, rate: int, target_lufs: float = DEFAULT_LUFS,
                 peak_db: float = DEFAULT_PEAK_DB) -> bytes:
    """Hochpass + EBU-R128-Lautheit (−16 LUFS) + True-Peak-Grenze.

    Konsistente Lautheit ist ein unterschätzter Natürlichkeits-Faktor:
    Leise Warnboxen neben lauten Überschriften wirken wie ein defekter
    Player, und unterwegs regelt niemand nach. Ohne ffmpeg greift die
    Peak-Normalisierung (immer noch besser als unbearbeitet).
    """
    pcm = ttb.highpass_pcm(pcm, rate, fc=80.0)
    pcm = ttb.declick_pcm(pcm)
    pcm = ttb.soft_limit_pcm(pcm)
    wav = ttb.build_wav(pcm, rate)
    # Automatische Rauschunterdrückung (ffmpeg afftdn) – immer an, kein Regler.
    # Ohne ffmpeg ein No-Op (Hochpass, Declick, Soft-Limit, Lautheit greifen trotzdem).
    wav = ttb.broadband_denoise_wav(wav)
    return ttb.loudness_normalize_wav(wav, target_lufs, peak_db)


# --------------------------------------------------------------------------
# Fingerprint + ffmpeg + Injektion
# --------------------------------------------------------------------------
GEN_VERSION = "ff-audio-v3"

# Das „Rezept" (Backend, Stimmen, Prosodie, Lautheit, Rezept-Versionen) ist
# Teil des Fingerprints: Wer die Stimme oder die Regie ändert, bekommt die
# Artikel neu vertont, statt alte Tracks mit neuem Rezept zu mischen.
RECIPE: dict = {
    "backend": DEFAULT_BACKEND,
    "profile": DEFAULT_PROFILE,
    "voiceDe": GROQ_VOICE_DE or "",
    "voiceEn": GROQ_VOICE_EN or "",
    "prosody": True,
    "bitrate": DEFAULT_BITRATE,
    "lufs": DEFAULT_LUFS,
    "norm": ttb.NORM_VERSION,
    "prosodyVersion": ttb.PROSODY_VERSION,
    "backendsVersion": ttb.BACKENDS_VERSION,
}


def set_recipe(**kw) -> dict:
    RECIPE.update({k: v for k, v in kw.items() if v is not None})
    return RECIPE


def fingerprint_for(blocks: list[tuple[str, str, str]], recipe: dict | None = None) -> str:
    """Inhalts-Fingerprint: ändert sich bei Text-, Stimmen- oder Regiewechsel."""
    r = recipe or RECIPE
    payload = "\n".join([
        GEN_VERSION, json.dumps(r, sort_keys=True, ensure_ascii=False),
        *(f"{lang}|{btype}|{normalize_text(text, lang)}" for lang, btype, text in blocks),
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def find_ffmpeg() -> str | None:
    return ttb.find_ffmpeg()


def encode_mp3(wav_bytes: bytes, mp3_path: str, bitrate: int | None = None) -> None:
    """WAV → Mono-MP3 (24 kHz, einstellbare Bitrate) – Podcast-Qualität.

    64 kbit/s Mono hält Zischlaute und Denoise-Reserve, ohne die
    gh-pages-Größe zu sprengen (≈ 480 kB je Minute).
    """
    exe = find_ffmpeg()
    if not exe:
        raise RuntimeError("ffmpeg nicht gefunden – MP3-Kodierung nicht möglich.")
    kbps = int(bitrate or DEFAULT_BITRATE)
    proc = subprocess.run(
        [exe, "-y", "-loglevel", "error", "-f", "wav", "-i", "pipe:0",
         "-vn", "-ac", "1", "-ar", "24000", "-c:a", "libmp3lame", "-b:a", f"{kbps}k",
         "-ar", "24000", mp3_path],
        input=wav_bytes, capture_output=True, timeout=900)
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
                   reading_time: str = "", engine=None, prosody: bool = True,
                   bitrate: int | None = None, keep_partial: bool = False) -> dict | None:
    """Ein Artikel → eine Tonspur (männliche DE-/EN-Stimme) + Timeline.

    Ablauf: Blöcke extrahieren (Parität zum Reader) → Sprech-Einheiten
    bauen (satzweises DE/EN-Routing + Rollen-Prosodie) → synthetisieren
    (kostenlose Backend-Kette) → Stille kappen, Pausen neu setzen →
    Hochpass + EBU-R128-Lautheit → MP3 → Sidecar-JSON → HTML-Injektion.
    """
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

    units = ttb.build_units(blocks, article_lang, prosody=prosody)
    if not units:
        print(f"  ⚠ {slug}: keine Sprech-Einheiten → übersprungen.")
        return None

    fingerprint = fingerprint_for(blocks)

    # 1) Wiederverwendung aus dem Cache (inkrementell – keine Synthese nötig).
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
            inject_audio_config(html_path, {"audio": {"src": cdata.get("src", ""),
                                                      "chunks": cdata.get("chunks", [])}})
        print(f"  ↺ {slug}: unverändert → wiederverwendet ({ext}).")
        return {"slug": slug, "status": "reuse", "blocks": len(blocks),
                "duration_ms": cdata.get("durationMs", 0)}
    elif existing:
        print(f"  ⏭ {slug}: existiert bereits (--force zum Neuaufbau).")
        return None

    # 2) Neu vertonen (oder im Dry-Run nur planen).
    if dry_run or engine is None:
        track = synthesize_track(units, engine, dry_run=True)
        mins = track["duration_ms"] / 1000 / 60
        print(f"  ⊙ {slug}: {len(blocks)} Blöcke → {len(track['chunks'])} Sprech-Einheiten "
              f"(~{round(track['duration_ms'] / 1000, 1)} s, {mins:.1f} min)")
        return {"slug": slug, "status": "generate", "blocks": len(blocks),
                "chunks": len(track["chunks"]), "duration_ms": track["duration_ms"],
                "fingerprint": fingerprint, "estimated": True}

    need_lang = "en" if str(article_lang).lower().startswith("en") else "de"
    if not engine.can(need_lang):
        print(f"  ⚠ {slug}: kein kostenloses Backend für {need_lang.upper()} verfügbar "
              f"→ keine Tonspur (Reader nutzt die Browser-Stimme).")
        return None

    track = synthesize_track(units, engine, dry_run=False)
    if track["failures"] and not keep_partial:
        # Liegt ein Schutzschalter-Abbruch vor, ist er die eigentliche Ursache
        # (Dienst nicht erreichbar) – die gehört ins Deploy-Log, nicht der
        # erste Einzelfehler.
        first = next((f for f in track["failures"] if f.get("role") == "abbruch"),
                     track["failures"][0])
        print(f"  ⚠ {slug}: {len(track['failures'])} von {len(units)} Einheiten fehlgeschlagen "
              f"(z. B. {first['error']}) → KEIN lückenhafter Track geschrieben. "
              f"Der Reader bleibt beim Browser-Fallback (--keep-partial zum Erzwingen).")
        return None
    if not track["pcm"]:
        print(f"  ⚠ {slug}: keine Audiodaten → übersprungen.")
        return None

    # 3) Mastering: Hochpass, Lautheit, Kodierung.
    final_wav = polish_track(track["pcm"], track["rate"])
    os.makedirs(out_dir, exist_ok=True)

    ext = "wav"
    audio_path = os.path.join(out_dir, f"{slug}.wav")
    if fmt in ("auto", "mp3") and find_ffmpeg():
        mp3_path = os.path.join(out_dir, f"{slug}.mp3")
        try:
            encode_mp3(final_wav, mp3_path, bitrate=bitrate)
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
    injected_chunks = block_chunks(track["chunks"])
    voices = track["engines"]
    data = {
        "src": src,
        # Reader-Vertrag (bleibt unverändert): ein Chunk je Block.
        "chunks": injected_chunks,
        # Sidecar-Debug/QA: Satz-Timeline inkl. echter Wortgrenzen.
        "timeline": track["timeline"],
        "fingerprint": fingerprint,
        "durationMs": track["duration_ms"],
        "blocks": len(blocks),
        "units": len(units),
        "engines": voices,
        "backend": (RECIPE.get("backend") or "auto"),
        "profile": RECIPE.get("profile"),
        "voiceDe": voices.get("de", ""),
        "voiceEn": voices.get("en", ""),
        "recipe": dict(RECIPE),
        "failures": len(track["failures"]),
        "versions": {"gen": GEN_VERSION, "norm": ttb.NORM_VERSION,
                     "prosody": ttb.PROSODY_VERSION, "backends": ttb.BACKENDS_VERSION},
    }
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    if inject:
        inject_audio_config(html_path, {"audio": {"src": src, "chunks": injected_chunks}})
    print(f"  ✅ {slug}: {len(blocks)} Blöcke / {len(units)} Sätze, "
          f"{round(track['duration_ms'] / 1000, 1)} s → {audio_path}"
          + (f" ({len(track['failures'])} Fehler, partiell)" if track["failures"] else ""))
    return {"slug": slug, "status": "generate", "blocks": len(blocks),
            "chunks": len(injected_chunks), "duration_ms": track["duration_ms"],
            "fingerprint": fingerprint, "engines": voices,
            "failures": len(track["failures"])}


def _parse_reader_date(value: str, fallback_path: str = "") -> tuple[int, str]:
    """Datumswert aus ff-reader-config -> Sortierschlüssel.

    Unterstützt Reader-/Hugo-Formate wie 04.09.2026, 2026-09-04 oder
    ISO-Zeitstempel. Fällt robust auf die Dateimtime zurück, damit die
    Backfill-Reihenfolge deterministisch bleibt.
    """
    raw = str(value or "").strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            dt = datetime.strptime(raw, fmt)
            return int(dt.timestamp()), raw
        except ValueError:
            continue
    if raw.endswith("Z"):
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return int(dt.timestamp()), raw
        except ValueError:
            pass
    try:
        return int(os.path.getmtime(fallback_path)), raw
    except OSError:
        return 0, raw


def discover_articles(html_dir: str) -> list[tuple[str, str, str, str, int, str]]:
    """Findet Artikel (Seiten mit ff-reader-config).

    Liefert (Pfad, Titel, Sprache, Lesedauer, sort_ts, raw_date). Die
    zusätzliche Sortier-Info steuert den Audio-Backfill deterministisch:
    standardmäßig zuerst die neuesten Artikel, damit frische Inhalte nicht
    hinter altem Bestand in der Warteschlange hängen bleiben.
    """
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
        raw_date = ""
        # Bevorzugt die echte Reader-Konfiguration (cfg.title/cfg.readingTime) –
        # exakt der Text, den auch der Web-Speech-Pfad als Anmoderation liest.
        m = re.search(r'<script[^>]*id="ff-reader-config"[^>]*>(.*?)</script>', content, re.S)
        if m:
            try:
                cfg = json.loads(m.group(1))
                title = cfg.get("title") or title
                lang = cfg.get("lang") or "de"
                reading_time = str(cfg.get("readingTime") or "")
                raw_date = str(cfg.get("updated") or cfg.get("date") or "")
            except json.JSONDecodeError:
                pass
        if not m or not title or title == os.path.basename(root):
            mt = re.search(r"<title[^>]*>(.*?)</title>", content, re.S | re.I)
            if mt:
                t = html_mod.unescape(re.sub(r"\s+", " ", mt.group(1)).strip())
                if t:
                    title = t
        sort_ts, raw_date = _parse_reader_date(raw_date, path)
        found.append((path, title, lang, reading_time, sort_ts, raw_date))
    return found


def sort_articles(articles: list[tuple[str, str, str, str, int, str]], order: str = "newest") -> list[tuple[str, str, str, str, int, str]]:
    """Sortiert die Audio-Queue deterministisch.

    newest = frische Inhalte zuerst (Backfill-Standard)
    oldest = Altbestand zuerst
    path   = stabile Repository-Reihenfolge
    """
    order = str(order or "newest").lower()
    if order == "oldest":
        return sorted(articles, key=lambda a: (a[4], a[0]))
    if order == "path":
        return sorted(articles, key=lambda a: a[0])
    return sorted(articles, key=lambda a: (-a[4], a[0]))


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

    print("— Selftest: Aussprache-Normalisierung (Natürlichkeits-Kern) —")
    cases = [
        ("Der Tarif kostet 1.299,50 € im Jahr.", "de",
         "eintausendzweihundertneunundneunzig Euro und fünfzig Cent"),
        ("Du sparst 8 % der Stromkosten.", "de", "acht Prozent"),
        ("Gültig ab 12.08.2026.", "de", "zwölfter August zweitausendsechsundzwanzig"),
        ("Das regelt § 5 BGB.", "de", "Paragraph fünf"),
        ("Ein ETF-Sparplan kostet nichts.", "de", "E T F"),
        ("Vergleiche z. B. Check24 und Verivox.", "de", "zum Beispiel"),
        ("The plan costs $1,299.50 per year.", "en",
         "one thousand two hundred ninety-nine dollars and fifty cents"),
        ("You save 8% on fees from 2026.", "en", "twenty twenty-six"),
    ]
    for text, lang, expect in cases:
        out = normalize_text(text, lang)
        check(f"Aussprache: {text[:36]!r} → {expect[:32]!r}", expect in out, out)
    url_out = normalize_text("Mehr auf https://www.check24.de/strom", "de")
    check("Kein URL-Buchstabensalat", "https" not in url_out, url_out)
    check("Keine Markdown-/Emoji-Reste",
          "*" not in normalize_text("**Wichtig:** Strom sparen", "de"))

    print("— Selftest: Sprech-Einheiten, Prosodie & Pausen —")
    blocks_p = [("de", "intro", "Stromkosten senken. Ein Beitrag von FranksFinanzcheck."),
                ("de", "h2", "Die wichtigsten Hebel"),
                ("de", "p", "Vergleichen lohnt sich. The comparison shows lower fees. "
                            "Wer 2026 wechselt, spart oft 300 € pro Jahr."),
                ("de", "warning", "Achtung: Die Preisgarantie endet oft nach 12 Monaten.")]
    units_p = ttb.build_units(blocks_p, "de")
    langs = [u.lang for u in units_p]
    check("Englischer Satz im deutschen Absatz bekommt die EN-Stimme",
          langs.count("en") == 1, str(langs))
    h2_rate = next(u.rate for u in units_p if u.role == "h2")
    p_rate = next(u.rate for u in units_p if u.role == "p" and u.lang == "de")
    check("Überschrift wird ruhiger gelesen als Fließtext", h2_rate < p_rate,
          f"h2={h2_rate:.3f} p={p_rate:.3f}")
    check("Fließtext nicht hetzend (rate ≤ 0.92)", p_rate <= 0.92, f"p={p_rate:.3f}")
    check("Rezept-Version v3 (High-End-Kette)", GEN_VERSION.startswith("ff-audio-v3"), GEN_VERSION)
    check("MP3-Bitrate ≥ 64 kbit/s (weniger Kodier-Rauschen)", DEFAULT_BITRATE >= 64,
          str(DEFAULT_BITRATE))
    warn = next(u for u in units_p if u.role == "warning")
    check("Warnbox bekommt Vor- und Nachpause",
          warn.before_ms >= 400 and warn.after_ms >= 300, f"{warn.before_ms}/{warn.after_ms}")
    finals = [u for u in units_p if u.final]
    check("Letzter Satz je Block als final markiert (Final-Dehnung)",
          len(finals) == len({u.block for u in units_p}), str(len(finals)))
    check("Pausen bleiben unter der Obergrenze",
          all(pause_before_ms(units_p, i) <= MAX_PAUSE_MS for i in range(len(units_p))))
    idx_seq = next(i for i, u in enumerate(units_p) if u.block == 2)
    check("Pausenregel nutzt max(Nachpause, Vorpause) statt Summe",
          pause_before_ms(units_p, idx_seq) <= max(units_p[idx_seq - 1].after_ms,
                                                    units_p[idx_seq].before_ms))
    flat = ttb.build_units(blocks_p, "de", prosody=False)
    check("Ohne Prosodie entfällt die Rollen-Regie (A/B-Schalter wirkt)",
          len({round(u.rate, 3) for u in flat}) < len({round(u.rate, 3) for u in units_p})
          or len({round(u.rate, 3) for u in flat}) == 1,
          str(sorted({round(u.rate, 3) for u in flat})))

    print("— Selftest: Mischsprache wird getrennt vertont —")

    class _ProbeEngine:
        """Nimmt Einheiten entgegen, ohne Audio zu erzeugen (Routing-Prüfung)."""

        def __init__(self):
            self.seen = []

        def synthesize(self, unit):
            import math as _m
            self.seen.append((unit.lang, unit.role))
            tone = [int(6000 * _m.sin(2 * _m.pi * 150 * i / ttb.TARGET_RATE))
                    for i in range(int(ttb.TARGET_RATE * 0.3))]
            return ttb.SynthResult(ttb.pcm_from_samples(tone), ttb.TARGET_RATE, [],
                                   "fake", "de_DE-test-high" if unit.lang == "de" else "en_US-test-high")

    probe = _ProbeEngine()
    mixed_track = synthesize_track(ttb.build_units(blocks_p, "de"), probe, dry_run=False)
    check("DE- und EN-Satz desselben Artikels landen bei unterschiedlichen Stimmen",
          {"de", "en"} <= {lang for lang, _ in probe.seen}, str(probe.seen))
    check("Beide Sprachen stehen in der Engine-Doku des Tracks",
          {"de", "en"} <= set(mixed_track["engines"]), str(mixed_track["engines"]))
    check("Keine Einheit ohne Sprache", all(lang in ("de", "en") for lang, _ in probe.seen))

    print("— Selftest: Timeline (Dry-Run) —")
    dry = synthesize_track(units_p, None, dry_run=True)
    ch = dry["chunks"]
    check("Chunk-Zeiten steigen monoton und überlappen nicht",
          all(ch[i]["t0"] < ch[i]["t1"] and (i == 0 or ch[i]["t0"] >= ch[i - 1]["t1"] - 1)
              for i in range(len(ch))), str(ch[:3]))
    check("Gesamtdauer = Ende des letzten Chunks",
          dry["duration_ms"] == ch[-1]["t1"], f"{dry['duration_ms']} vs {ch[-1]['t1']}")
    check("Alle Blöcke sind in der Timeline",
          {c["b"] for c in ch} == {u.block for u in units_p}, str({c["b"] for c in ch}))
    bc = block_chunks(ch)
    check("Block-Timeline: genau ein Chunk je Block",
          len(bc) == len({c["b"] for c in ch}), str(bc))
    check("Block-Timeline bleibt Reader-vertragskonform",
          all(set(c) == {"b", "t0", "t1", "lang"} for c in bc), str(bc[0] if bc else None))
    mixed = next((c for c in bc if c["b"] == 2), None)
    check("Blocksprache = dominante Sprache (Mischblock bleibt deutsch)",
          mixed is not None and mixed["lang"] == "de", str(mixed))

    print("— Selftest: End-to-End mit Fake-Engine (offline, ohne Netzwerk) —")

    class _FakeEngine(ttb.Engine):
        """Ersetzt edge/piper durch einen Sinuston und prüft den kompletten
        Render-Pfad: Pausen, Mastering, Sidecar, Injektion, Cache.
        Erbt bewusst von Engine, damit der echte Vorab-Test (preflight)
        mitläuft – genau der Code, der auch im Deploy arbeitet."""

        def __init__(self):
            self.calls = []

        def can(self, lang):
            return lang in ("de", "en")

        def usable_langs(self):
            return ["de", "en"]

        def describe(self):
            return "fake:de_DE-test-high"

        def warm(self):
            return None

        def synthesize(self, unit):
            import math as _m
            self.calls.append(unit)
            # Stille vorn/hinten wie bei echten Engines → muss gekappt werden.
            n = int(ttb.TARGET_RATE * min(1.5, 0.2 + len(unit.text) / 400))
            tone = [int(9000 * _m.sin(2 * _m.pi * 180 * i / ttb.TARGET_RATE)) for i in range(n)]
            quiet = [0] * int(ttb.TARGET_RATE * 0.4)
            pcm = ttb.pcm_from_samples(quiet + tone + quiet)
            voice = "en_US-test-high" if unit.lang == "en" else "de_DE-test-high"
            return ttb.SynthResult(pcm, ttb.TARGET_RATE,
                                   [{"text": "x", "offset_ms": 0, "duration_ms": 10}],
                                   "fake", voice)

    with tempfile.TemporaryDirectory() as td:
        art_dir = os.path.join(td, "posts", "strom")
        os.makedirs(art_dir, exist_ok=True)
        html_file = os.path.join(art_dir, "index.html")
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(SELFTEST_HTML)
        fake = _FakeEngine()
        out_dir = os.path.join(td, "out")
        r = render_article(html_file, out_dir, None, "Hausratversicherung: Was sie kostet", "de",
                           dry_run=False, force=False, fmt="wav", inject=True, have_key=False,
                           engine=fake, prosody=True)
        check("End-to-End liefert Status generate", bool(r) and r.get("status") == "generate", str(r))
        check("Jede Sprech-Einheit wurde synthetisiert", len(fake.calls) > 0, str(len(fake.calls)))
        check("Alle Einheiten tragen die Artikel- oder Satzsprache",
              {c.lang for c in fake.calls} <= {"de", "en"} and len(fake.calls) > 0,
              str({c.lang for c in fake.calls}))
        wav_path = os.path.join(out_dir, "strom.wav")
        check("Tonspur geschrieben",
              os.path.exists(wav_path) and os.path.getsize(wav_path) > 1000,
              str(os.path.getsize(wav_path)) if os.path.exists(wav_path) else "fehlt")
        side = os.path.join(out_dir, "strom.audio.json")
        check("Sidecar-JSON geschrieben", os.path.exists(side))
        data = {}
        if os.path.exists(side):
            with open(side, encoding="utf-8") as f:
                data = json.load(f)
            check("Sidecar enthält Block-Chunks (Reader-Vertrag)",
                  bool(data.get("chunks")) and
                  all(set(c) == {"b", "t0", "t1", "lang"} for c in data["chunks"]),
                  str(data.get("chunks", [])[:2]))
            check("Sidecar enthält Satz-Timeline mit Wortgrenzen",
                  bool(data.get("timeline")) and any(e.get("words") for e in data["timeline"]))
            check("Sidecar dokumentiert Engine + Stimmen",
                  bool(data.get("engines")) and bool(data.get("voiceDe")), str(data.get("engines")))
            check("Sidecar enthält das Rezept",
                  (data.get("recipe") or {}).get("profile") in ttb.VOICE_PRESETS,
                  str(data.get("recipe")))
        with open(html_file, encoding="utf-8") as f:
            injected = f.read()
        check("HTML-Injektion vorhanden", 'id="ff-reader-audio-config"' in injected)
        m = re.search(r'id="ff-reader-audio-config">(.*?)</script>', injected, re.S)
        payload = json.loads(m.group(1)) if m else {}
        inj = payload.get("audio", {})
        check("Injizierte Chunks sind Blockebene (kein Satz-Ballast in der HTML)",
              bool(inj.get("chunks")) and not any(("text" in c or "words" in c)
                                                  for c in inj["chunks"]),
              str(inj.get("chunks", [])[:2]))
        if os.path.exists(wav_path):
            with open(wav_path, "rb") as f:
                wav_bytes = f.read()
            real_ms = duration_ms(wav_bytes)
            last = (inj.get("chunks") or [{}])[-1]
            check("Timeline passt zur realen Audiodauer",
                  abs(real_ms - r.get("duration_ms", 0)) <= 150 and last.get("t1", 0) <= real_ms + 5,
                  f"wav={real_ms} track={r.get('duration_ms')} t1={last.get('t1')}")
            pcm_body, _rate = ttb.wav_pcm(wav_bytes)
            check("Tonspur ist nicht still (Mastering wirksam)",
                  ttb.rms_db(pcm_body) > -45.0, f"{ttb.rms_db(pcm_body):.1f} dB")
            check("Kein Clipping in der fertigen Tonspur",
                  max(abs(s) for s in ttb.pcm_to_samples(pcm_body)) <= 32767)
            check("Stille an den Segmenträndern wurde gekappt",
                  real_ms < sum(2 * 400 + 1 for _ in fake.calls),
                  f"wav={real_ms} ms bei {len(fake.calls)} Einheiten")
        cache_dir = os.path.join(td, "cache")
        shutil.copytree(out_dir, cache_dir)
        fake2 = _FakeEngine()
        r2 = render_article(html_file, out_dir, cache_dir, "Hausratversicherung: Was sie kostet", "de",
                            dry_run=False, force=False, fmt="wav", inject=True, have_key=False,
                            engine=fake2, prosody=True)
        check("Zweiter Lauf nutzt den Cache (keine neue Synthese)",
              bool(r2) and r2.get("status") == "reuse" and fake2.calls == [], str(r2))
        fp1 = fingerprint_for(blocks_p)
        fp2 = fingerprint_for(blocks_p, {**RECIPE, "voiceDe": "de-DE-ConradNeural"})
        check("Stimmenwechsel erzwingt Neuvertonung (Fingerprint kippt)",
              fp1 != fp2, f"{fp1}/{fp2}")

    # ------------------------------------------------------------------
    # CLI-Integration: die komplette Befehlszeile offline prüfen
    # (Discovery, Injektion, Cache, Vorab-Test, Fehler-Schutzschalter,
    # Dry-Run). Ohne diese Prüfung fällt erst im Deploy auf, dass z. B.
    # ein ausgefallener Sprachdienst den Lauf minutenlang blockiert.
    # ------------------------------------------------------------------
    print("— Selftest: CLI-Integration (Discovery, Cache, Vorab-Test, Schutzschalter) —")
    import contextlib
    import io as _io
    import tempfile as _tf

    class _KaputteEngine(_FakeEngine):
        """Simuliert einen ausgefallenen Sprachdienst (Sperre/Kontingent)."""

        def synthesize(self, unit):
            self.calls.append(unit)
            raise ttb.BackendError("Selftest: Sprachdienst nicht erreichbar")

    def _run(argv, engine):
        """main() ausführen und die CLI-Ausgabe einsammeln (Log bleibt lesbar)."""
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(argv, engine_factory=lambda **_kw: engine)
        return rc, buf.getvalue()

    with _tf.TemporaryDirectory() as td:
        site_dir = os.path.join(td, "public", "posts", "strom")
        os.makedirs(site_dir)
        page_html = os.path.join(site_dir, "index.html")
        cfg_tag = ('<script type="application/json" id="ff-reader-config">'
                   '{"title":"Stromvergleich 2026","readingTime":"7","wordCount":"1200"}'
                   '</script>')
        with open(page_html, "w", encoding="utf-8") as f:
            f.write(SELFTEST_HTML.replace('<div class="post-content md-content">',
                                          '<div class="post-content md-content">' + cfg_tag, 1))
        out_dir = os.path.join(td, "public", "audio", "articles")
        cache_dir = os.path.join(td, "cache")
        base = ["--html-dir", os.path.join(td, "public"), "--out-dir", out_dir,
                "--cache-dir", cache_dir, "--format", "wav"]

        fake_cli = _FakeEngine()
        rc, log = _run(base, fake_cli)
        with open(page_html, encoding="utf-8") as f:
            injected = f.read()
        check("CLI-Lauf vertont den Artikel (Exit 0, WAV vorhanden)",
              rc == 0 and os.path.exists(os.path.join(out_dir, "strom.wav")), f"rc={rc}")
        check("CLI injiziert die Tonspur in die Artikelseite",
              'id="ff-reader-audio-config"' in injected)
        check("Artikel-Config bleibt unangetastet (nur eigener Audio-Block)",
              '"wordCount":"1200"}' in injected and '"audio"' not in injected.split(
                  'id="ff-reader-audio-config"')[0][-400:])
        probes = [c for c in fake_cli.calls if c.text == "Test."]
        check("Vorab-Test kostet genau zwei Mini-Synthesen (DE/EN)", len(probes) == 2,
              str(len(probes)))
        check("Manifest wird mit echten Ergebnissen geschrieben",
              os.path.exists(os.path.join(out_dir, "manifest.json")))

        shutil.copytree(out_dir, cache_dir, dirs_exist_ok=True)
        fake_cli2 = _FakeEngine()
        rc2, _log2 = _run(base, fake_cli2)
        real_calls = [c for c in fake_cli2.calls if c.text != "Test."]
        check("Zweiter CLI-Lauf nutzt den Cache (keine Neuvertonung)",
              rc2 == 0 and not real_calls, f"{len(real_calls)} Synthesen")

        # Backfill-Reihenfolge: newest/oldest/path müssen deterministisch
        # steuerbar sein, damit neue Artikel im Archiv-Backfill nicht hinten
        # anstehen und man Altbestand bei Bedarf gezielt vorziehen kann.
        order_root = os.path.join(td, "order")
        newer_dir = os.path.join(order_root, "posts", "neuer")
        older_dir = os.path.join(order_root, "posts", "alter")
        os.makedirs(newer_dir, exist_ok=True)
        os.makedirs(older_dir, exist_ok=True)
        with open(os.path.join(newer_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write('<html><body><script type="application/json" id="ff-reader-config">'
                    '{"title":"Neu","lang":"de","date":"04.09.2026","readingTime":"1"}'
                    '</script><div class="post-content md-content"><p>Neu.</p></div></body></html>')
        with open(os.path.join(older_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write('<html><body><script type="application/json" id="ff-reader-config">'
                    '{"title":"Alt","lang":"de","date":"01.09.2026","readingTime":"1"}'
                    '</script><div class="post-content md-content"><p>Alt.</p></div></body></html>')
        discovered = discover_articles(order_root)
        newest = [os.path.basename(os.path.dirname(a[0])) for a in sort_articles(discovered, "newest")]
        oldest = [os.path.basename(os.path.dirname(a[0])) for a in sort_articles(discovered, "oldest")]
        bypath = [os.path.basename(os.path.dirname(a[0])) for a in sort_articles(discovered, "path")]
        check("Backfill-Queue: newest priorisiert frische Artikel", newest == ["neuer", "alter"], str(newest))
        check("Backfill-Queue: oldest priorisiert Altbestand", oldest == ["alter", "neuer"], str(oldest))
        check("Backfill-Queue: path bleibt stabil alphabetisch", bypath == ["alter", "neuer"], str(bypath))

        # CLI-Ebene: Der Vorab-Test muss einen ausgefallenen Dienst erkennen,
        # BEVOR Artikel abgearbeitet werden – sonst wartet der Deploy minutenlang.
        broken = _KaputteEngine()
        rc3, log3 = _run(["--html-dir", os.path.join(td, "public"),
                          "--out-dir", os.path.join(td, "out2"), "--format", "wav", "--force"],
                         broken)
        failed_calls = [c for c in broken.calls if c.text != "Test."]
        check("Ausgefallener Dienst stoppt den Deploy nicht (Exit 0)", rc3 == 0, f"rc={rc3}")
        check("Vorab-Test verhindert jede Satz-Synthese (keine Warteschleife)",
              not failed_calls, f"{len(failed_calls)} Synthesen")
        check("Vorab-Test wird im Deploy-Log begründet",
              "Vorab-Test fehlgeschlagen" in log3, log3[-160:])
        check("Keine lückenhafte Tonspur geschrieben",
              not os.path.exists(os.path.join(td, "out2", "strom.wav")))

        # Unit-Ebene: Fällt der Dienst erst mitten im Artikel aus, muss der
        # Schutzschalter den Artikel abbrechen (nicht jeden Satz probieren).
        track_broken = _KaputteEngine()
        t_start = time.time()
        tr = synthesize_track(ttb.build_units(blocks_p, "de", prosody=True), track_broken)
        elapsed = time.time() - t_start
        aborts = [f for f in tr["failures"] if f.get("role") == "abbruch"]
        check("Schutzschalter bricht den Artikel ab",
              bool(aborts) and len(track_broken.calls) <= MAX_CONSECUTIVE_FAILURES + 1,
              f"{len(track_broken.calls)} Versuche, {len(aborts)} Abbruchmeldungen")
        check("Abbruch nennt die Ursache", bool(aborts) and "nicht erreichbar" in aborts[0]["error"],
              aborts[0]["error"] if aborts else "kein Abbrucheintrag")
        check("Abbruch bleibt schnell (unter 20 s)", elapsed < 20.0, f"{elapsed:.1f} s")

        rc4, _log4 = _run(["--html-dir", os.path.join(td, "public"),
                           "--out-dir", os.path.join(td, "out3"), "--dry-run"], _FakeEngine())
        check("Dry-Run plant ohne Audiodatei", rc4 == 0 and not os.path.exists(os.path.join(td, "out3")))

    print(f"\n=== Selftest: {ok} grün, {fail} rot ===")
    return 0 if not fail else 1


def main(argv: list[str] | None = None, engine_factory=None) -> int:
    """CLI-Einstieg.

    `argv` und `engine_factory` existieren für den Selbsttest: So lässt sich
    die komplette Befehlszeile (Discovery, Limit, Vorab-Test, Cache,
    Manifest, Dry-Run) offline prüfen, ohne einen Sprachdienst zu rufen.
    """
    make_engine = engine_factory or ttb.Engine
    ap = argparse.ArgumentParser(
        description="Vorab vertonte Artikel (ZEIT-Standard). Kostenlose Backend-Kette: "
                    "edge-tts (männliche Neuralstimmen DE/EN, High-End) → Piper (lokal, offline) → "
                    "Groq Orpheus (nur EN). Ohne Backend bleibt der Browser-Fallback aktiv.")
    ap.add_argument("--html-dir", default=os.path.join(ROOT, "public"))
    ap.add_argument("--out-dir", default=os.path.join(ROOT, "static", "audio", "articles"))
    ap.add_argument("--cache-dir", default=None, help="Verzeichnis mit vorherigen Tonspuren (inkrementell)")
    ap.add_argument("--format", choices=["auto", "mp3", "wav"], default="auto",
                    help="Zielformat (auto = mp3 wenn ffmpeg vorhanden, sonst wav)")
    ap.add_argument("--only", help="nur diesen Slug generieren")
    ap.add_argument("--limit", type=int, default=0, help="max. Anzahl Artikel (0 = alle)")
    ap.add_argument("--limit-new", type=int, default=int(os.environ.get("FF_AUDIO_LIMIT_NEW", "25")),
                    help="max. Anzahl NEU vertonter Artikel je Lauf (0 = unbegrenzt). "
                         "Schützt CI-Laufzeit und Gratis-Kontingente; der Rest folgt beim "
                         "nächsten Deploy, Wiederverwendung aus dem Cache bleibt unbegrenzt.")
    ap.add_argument("--force", action="store_true", help="existierende Dateien überschreiben")
    ap.add_argument("--order", choices=["newest", "oldest", "path"], default="newest",
                    help="Reihenfolge für Backfill/Neuvertonung: newest = frische Artikel zuerst (Standard)")
    ap.add_argument("--dry-run", action="store_true", help="nur Planung ohne Synthese")
    ap.add_argument("--no-inject", action="store_true",
                    help="keine <script id=ff-reader-audio-config> in die HTML schreiben")
    ap.add_argument("--selftest", action="store_true", help="Selbsttest ohne Netzwerk/Key")
    ap.add_argument("--engines", action="store_true",
                    help="verfügbare Backends + gewählte männliche Stimmen anzeigen")
    # Stimmen-Regie (alles kostenlos, alles ohne Umschalter für die Leser:innen)
    ap.add_argument("--backend", default=DEFAULT_BACKEND,
                    choices=["auto", "edge", "piper", "groq"],
                    help="auto = edge → piper → groq (Standardpriorität: menschlichste Neuralstimme)")
    ap.add_argument("--profile", default=DEFAULT_PROFILE, choices=sorted(ttb.VOICE_PRESETS),
                    help="natural = Multilingual-v2-Stimmen (ein Sprecher auch für englische "
                         "Fachbegriffe), narrator = Conrad/Ryan (klassischer Erzähler)")
    ap.add_argument("--voice-de", default=os.environ.get("FF_AUDIO_VOICE_DE") or None,
                    help="explizite männliche DE-Stimme (überschreibt das Profil)")
    ap.add_argument("--voice-en", default=os.environ.get("FF_AUDIO_VOICE_EN") or None,
                    help="explizite männliche EN-Stimme (überschreibt das Profil)")
    ap.add_argument("--rate", type=float, default=float(os.environ.get("FF_AUDIO_RATE", "1.0")),
                    help="globales Tempo (0.9 = ruhiger; Neuralstimmen klingen bei ~0.96 natürlicher)")
    ap.add_argument("--pitch", type=float, default=float(os.environ.get("FF_AUDIO_PITCH", "0")),
                    help="globale Tonlagen-Verschiebung in Hz (männliche Zone: -2 … 0)")
    ap.add_argument("--bitrate", type=int, default=DEFAULT_BITRATE,
                    help=f"MP3-Bitrate in kbit/s (Voreinstellung {DEFAULT_BITRATE}, Mono 24 kHz)")
    ap.add_argument("--lufs", type=float, default=DEFAULT_LUFS,
                    help=f"EBU-R128-Ziellautheit (Voreinstellung {DEFAULT_LUFS} LUFS)")
    ap.add_argument("--no-prosody", action="store_true",
                    help="Rollen-Prosodie/Pausenregie abschalten (A/B-Vergleich)")
    ap.add_argument("--keep-partial", action="store_true",
                    help="auch bei Einzelfehlern eine (lückenhafte) Tonspur schreiben")
    ap.add_argument("--piper-dir", default=os.environ.get("FF_PIPER_VOICES"),
                    help="Verzeichnis für lokale Piper-Stimmen (Default: .cache/ff-tts/piper-voices)")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    prosody = not args.no_prosody
    set_recipe(backend=args.backend, profile=args.profile,
               voiceDe=args.voice_de or "", voiceEn=args.voice_en or "",
               prosody=prosody, bitrate=args.bitrate, lufs=args.lufs,
               rate=args.rate, pitch=args.pitch)

    if args.engines:
        print(f"Rezept: {json.dumps(RECIPE, ensure_ascii=False, sort_keys=True)}")
        for name in ttb.BACKEND_ORDER:
            inst = ttb.BACKEND_CLASSES[name](profile=args.profile)
            ok, why = inst.available()
            print(f"  {'✅' if ok else '⊘'} {name:6s} {why}")
        engine = make_engine(backend=args.backend, profile=args.profile,
                             voice_de=args.voice_de, voice_en=args.voice_en,
                             rate_scale=args.rate, pitch_offset_hz=args.pitch,
                             workdir=None, verbose=True)
        print("Auswahl:", engine.describe() or "kein Backend verfügbar → Reader nutzt die Browser-Stimme")
        print("ffmpeg:", find_ffmpeg() or "nicht gefunden (MP3/Lautheit nicht möglich)")
        return 0

    if not os.path.isdir(args.html_dir):
        print(f"❌ HTML-Verzeichnis nicht gefunden: {args.html_dir} (erst `hugo --minify` bauen).")
        return 2

    have_key = groq_config.available()
    engine = None
    if not args.dry_run:
        engine = make_engine(backend=args.backend, profile=args.profile,
                             voice_de=args.voice_de, voice_en=args.voice_en,
                             rate_scale=args.rate, pitch_offset_hz=args.pitch,
                             verbose=True)
        if args.piper_dir:
            os.environ["FF_PIPER_VOICES"] = args.piper_dir
        usable = engine.usable_langs()
        print(f"🔊 Backend-Kette: {args.backend} · Profil {args.profile} · {engine.describe()}")
        if not usable:
            print("⚠ Kein kostenloses TTS-Backend verfügbar. Der Deploy läuft weiter; der Reader "
                  "nutzt die lokale Browser-Stimme. Abhilfe: `pip install edge-tts` "
                  "(+ ffmpeg) oder `pip install piper-tts`.")
        else:
            engine.warm()
            # Vorab-Test (ein Testwörtchen je Sprache), BEVOR Dutzende Artikel
            # abgearbeitet werden. Fällt der Sprachdienst aus, wird die
            # Neuvertonung in diesem Lauf übersprungen – Tonspuren aus dem
            # Cache werden trotzdem weiter injiziert, alles andere bleibt beim
            # Browser-Fallback. Ohne diesen Test würde jeder Satz jedes
            # Artikels einzeln scheitern und den Deploy um Minuten verlängern.
            preflight = engine.preflight()
            working = [lg for lg, (ok, _w) in preflight.items() if ok]
            broken = [(lg, why) for lg, (ok, why) in preflight.items() if not ok]
            if preflight and not working:
                print("⚠ Vorab-Test fehlgeschlagen – in diesem Lauf wird nichts neu vertont:")
                for lg, why in broken:
                    print(f"    {lg.upper()}: {why}")
                print("  Der Deploy läuft weiter: vorhandene Tonspuren aus dem Cache "
                      "werden injiziert, neue Artikel nutzen die Browser-Stimme.")
                engine = None
            elif broken:
                for lg, why in broken:
                    print(f"⚠ Vorab-Test: {lg.upper()} nicht vertonbar ({why}) – Artikel in "
                          f"dieser Sprache bleiben beim Browser-Fallback.")
    else:
        print(f"DRY-RUN: Rezept {args.backend}/{args.profile}, keine Synthese.")

    inject = not args.no_inject
    articles = discover_articles(args.html_dir)
    if args.only:
        articles = [a for a in articles if args.only in a[0]]
    articles = sort_articles(articles, args.order)
    if args.limit:
        articles = articles[: args.limit]

    if not articles:
        print("Keine Artikel mit ff-reader-config gefunden.")
        return 0

    queue_preview = ", ".join(os.path.basename(os.path.dirname(a[0])) for a in articles[:5])
    print(f"{len(articles)} Artikel gefunden. Neuvertonung je Lauf: "
          f"{'unbegrenzt' if args.limit_new <= 0 else args.limit_new} "
          f"(Cache-Wiederverwendung unbegrenzt). Reihenfolge: {args.order}. "
          f"Queue-Start: {queue_preview}")

    results = []
    new_count = 0
    for path, title, lang, reading_time, _sort_ts, _raw_date in articles:
        try:
            will_render = not args.dry_run and engine is not None
            blocked_by_limit = (will_render and args.limit_new > 0 and new_count >= args.limit_new
                                and not _cached(path, args.cache_dir, args.out_dir, title, lang,
                                                reading_time, RECIPE))
            if blocked_by_limit:
                continue
            r = render_article(path, args.out_dir, args.cache_dir, title, lang,
                               args.dry_run, args.force, args.format, inject,
                               have_key, reading_time=reading_time, engine=engine,
                               prosody=prosody, bitrate=args.bitrate,
                               keep_partial=args.keep_partial)
            if r:
                results.append(r)
                if r.get("status") == "generate" and not r.get("estimated"):
                    new_count += 1
        except Exception as e:  # noqa: BLE001
            print(f"  ❌ {path}: {e}")
            continue

    # Manifest (slug → Status/Fingerprint/Dauer) für Inkrementalität & Debug.
    # Nur mit echten Ergebnissen schreiben: reine Schätzungen (kein Backend
    # verfügbar) belegen keine Tonspur und gehören nicht in diese Datei.
    rendered = [r for r in results if not r.get("estimated")]
    if rendered and not args.dry_run:
        os.makedirs(args.out_dir, exist_ok=True)
        manifest = {r["slug"]: {k: v for k, v in r.items() if k != "slug"} for r in rendered}
        with open(os.path.join(args.out_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

    generated = sum(1 for r in results if r.get("status") == "generate")
    reused = sum(1 for r in results if r.get("status") == "reuse")
    print(f"\nFertig: {len(results)} Artikel ({generated} neu vertont, {reused} wiederverwendet). "
          f"Ausgabe: {args.out_dir}")
    return 0


def _cached(html_path: str, cache_dir: str | None, out_dir: str | None, title: str,
            article_lang: str, reading_time: str, recipe: dict) -> bool:
    """Prüft ohne Synthese, ob für diesen Artikel schon eine passende Tonspur
    im Cache liegt (für die --limit-new-Steuerung)."""
    if not cache_dir:
        return False
    slug = os.path.splitext(os.path.basename(html_path))[0]
    if slug == "index":
        slug = os.path.basename(os.path.dirname(html_path))
    cjson = os.path.join(cache_dir, f"{slug}.audio.json")
    if not os.path.exists(cjson):
        return False
    try:
        with open(cjson, encoding="utf-8") as f:
            cdata = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False
    try:
        with open(html_path, encoding="utf-8") as f:
            html = f.read()
    except OSError:
        return False
    parser = DocParser()
    parser.feed(html)
    blocks = collect_blocks(parser.root, title, article_lang, reading_time)
    if not blocks:
        return False
    if cdata.get("fingerprint") != fingerprint_for(blocks, recipe):
        return False
    return any(os.path.exists(os.path.join(cache_dir, f"{slug}.{ext}")) for ext in ("mp3", "wav"))


if __name__ == "__main__":
    raise SystemExit(main())
