#!/usr/bin/env python3
"""ff_voice_backends.py — Stimmen-Kette, Aussprache und Prosodie (FF Voice Studio).

Gegenstück zu `static/premium/ff-voice.js` auf der Serverseite. Beide
sprechen denselben Text mit derselben Regie — die Parität wird durch
`scripts/ff_voice_parity_check.py` erzwungen. Wäre sie nicht erzwungen,
klänge derselbe Artikel je nach Gerät unterschiedlich.

NUR-DEUTSCH-VERTRAG (Befund 07.09.2026, Auftrag: „Deutsch als einzige
Sprache“)
    Die Vorlese-Funktion spricht AUSSCHLIESSLICH Deutsch. Es gibt keine
    englische Stimme, kein englisches Profil, keinen Sprachwechsel im
    Satz und keinen EN-Fallback mehr. Englische Fachbegriffe im
    deutschen Text („Cashflow“, „Robo Advisor“) spricht die deutsche
    Nachrichtensprecher-Stimme so aus, wie es im deutschen Hörfunk
    üblich ist — das ist gewollt und kein Fehler. Ein Backend, das nur
    Englisch kann (z. B. der ehemalige Groq-Notnagel), ist aus der
    Kette ENTFERNT; er kehrte nie zurück, solange die Gate-Prüfung
    „Stimmen: kein EN-Profil mehr“ grün ist.

STIMMEN (männlicher Nachrichtensprecher, nur Deutsch, ohne Umschalter)
    edge   (Voreinstellung)  Microsoft-Edge-Neuralstimmen über das offene
                             Paket `edge-tts`: kein Key, kein Konto, keine
                             Zeichenkosten.
                             Profil „news“     : de-DE-ConradNeural
                                               (Vortragsstil „serious“ —
                                               Nachrichtensprecher; wird
                                               nur gesetzt, wenn das
                                               installierte edge-tts
                                               Styles unterstützt)
                             Profil „natural“: de-DE-FlorianMultilingualNeural
                             Profil „narrator“: de-DE-KillianNeural
                             „news“ ist die Voreinstellung.
    piper  (Offline-Fallback) Lokale ONNX-Stimme de_DE-thorsten-high:
                             offline, unbegrenzt, lizenzsauber,
                             deterministisch — ebenfalls ausschließlich
                             Deutsch.

Ohne verfügbares Backend wird KEINE Tonspur geschrieben; der Reader
bleibt dann beim lokalen Web-Speech-Pfad — niemals stumm.

WORTGRENZEN (Grundlage der wortgenauen Leseanzeige)
    `synth_edge` liefert zu jedem Segment die WordBoundary-Ereignisse
    von edge-tts (100-ns-Ticks ab Segmentbeginn). Der Generator
    (ff_voice_audio.synth_article) rechnet sie in absolute
    Millisekunden um und schreibt sie als Wortuhr `w` in die
    Tonspur-Konfiguration — der Reader markiert damit jedes gesprochene
    Wort auf die Millisekunde genau.

AUSSPRACHE-REGIE
    Zahlen, Währungen, Daten, Zeiten, Prozente, Paragraphen, Abkürzungen,
    Einheiten und URLs werden vor der Synthese in gesprochene Sprache
    übersetzt — in derselben Reihenfolge wie im Reader (siehe
    `RULES_DE`). Die Funktion nimmt nach wie vor einen `lang`-Parameter
    an; er wird ignoriert (Nur-Deutsch-Vertrag) und dient nur der
    Signaturen-Stabilität gegenüber dem Reader.

PROSODIE-REGIE
    Jede Rolle (Überschrift, Fließtext, Tabellenzeile, Warnhinweis …)
    bekommt Tempo, Tonlage und Lautstärke. Dieselben Werte stehen in
    `PROSODY` im Reader.

Selbsttest ohne Netzwerk und ohne Schlüssel:
    python3 scripts/ff_voice_backends.py --selftest
"""

from __future__ import annotations

import asyncio
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import wave

# ---------------------------------------------------------------------------
# Stimmen-Kette
# ---------------------------------------------------------------------------

VOICE_PROFILES = {
    # Nachrichtensprecher-Preset: Conrad ist die deutsche
    # Newsroom-Stimme von Microsoft (Kategorie „News & Announcement“).
    # Der Style „serious“ wird gereicht, wenn das installierte edge-tts
    # Styles unterstützt (ältere Pakete ignorieren ihn sauber).
    "news": {
        "de": "de-DE-ConradNeural",
        "style": "serious",
        "label": "Nachrichtensprecher (Conrad · Style serious)",
    },
    "natural": {
        "de": "de-DE-FlorianMultilingualNeural",
        "style": None,
        "label": "Sachlicher Erzählton (Florian)",
    },
    "narrator": {
        "de": "de-DE-KillianNeural",
        "style": None,
        "label": "Nachrichtenlesung (Killian)",
    },
}

# Voreinstellung der Kette — „news“ ist der Auftrag: professioneller
# Nachrichtensprecher, ausschließlich Deutsch.
DEFAULT_PROFILE = "news"


def profile_voice(profile_name: str) -> str:
    """Deutsche Stimme eines Profils — unbekannte Profile fallen auf „news“."""
    profile = VOICE_PROFILES.get(profile_name) or VOICE_PROFILES[DEFAULT_PROFILE]
    return profile["de"]


def profile_style(profile_name: str):
    """Gewünschter Vortragsstil des Profils (kann None sein)."""
    profile = VOICE_PROFILES.get(profile_name) or VOICE_PROFILES[DEFAULT_PROFILE]
    return profile.get("style")

PIPER_VOICES = {
    "de": "de_DE-thorsten-high",
}

ENGINE_ORDER = ["edge", "piper"]

# Backend-Fingerprint: ändert er sich, werden Tonspuren neu erzeugt.
# 06.09.2026: Bump nach dem Pausen-Spur-Befund — alle bestehenden (defekten)
# Caches werden invalidiert und beim nächsten Lauf neu vertont bzw. vom
# Reader-Klienten bis dahin sicher abgewiesen (Plausibilitäts-Gate).
# 07.09.2026: Bump nach der KERNREPARATUR (edge-tts liefert MP3, die Kette
# las RIFF/WAVE → jedes Segment scheiterte, 34 Spuren waren Digitalstille).
# Damit wird JEDE Spur aus der Stille-Ära zwingend neu vertont.
# 10.09.2026: Bump nach dem Nur-Deutsch-Umbau: Profil „news“
# (männlicher Nachrichtensprecher Conrad, Style serious), kein EN-Zweig
# mehr, zusätzlich Wortuhr (WordBoundary-Timings) pro Chunk in der
# Tonspur-Konfiguration. Alle Spuren der DE+EN-Ära werden neu vertont.
RECIPE_VERSION = "ff-voice-2026.09.10"

# ---------------------------------------------------------------------------
# Prosodie-Regie — spiegelbildlich zu PROSODY in static/premium/ff-voice.js
#   rate   0.6 … 1.4 (1.0 = neutral)
#   pitch  Tonlagenversatz in Hz (edge-tts: "±XHz")
#   volume 0.0 … 1.0
#   before / after  Pausen in Millisekunden
# ---------------------------------------------------------------------------

PROSODY = {
    "intro":            {"rate": 0.99, "pitch": 0,   "volume": 1.00, "before": 0,   "after": 520},
    "outro":            {"rate": 0.94, "pitch": -3,  "volume": 0.96, "before": 420, "after": 0},
    "h2":               {"rate": 0.90, "pitch": -4,  "volume": 1.00, "before": 620, "after": 420},
    "h3":               {"rate": 0.92, "pitch": -3,  "volume": 1.00, "before": 520, "after": 340},
    "h4":               {"rate": 0.94, "pitch": -2,  "volume": 1.00, "before": 440, "after": 280},
    "h5":               {"rate": 0.96, "pitch": -1,  "volume": 1.00, "before": 380, "after": 240},
    "h6":               {"rate": 0.97, "pitch": -1,  "volume": 1.00, "before": 340, "after": 220},
    "lead":             {"rate": 0.96, "pitch": 0,   "volume": 1.00, "before": 420, "after": 460},
    "p":                {"rate": 1.00, "pitch": 0,   "volume": 1.00, "before": 180, "after": 420},
    "li":               {"rate": 1.01, "pitch": 0,   "volume": 1.00, "before": 120, "after": 320},
    "blockquote":       {"rate": 0.95, "pitch": -2,  "volume": 0.98, "before": 380, "after": 460},
    "callout":          {"rate": 0.97, "pitch": 0,   "volume": 1.00, "before": 380, "after": 460},
    "warning":          {"rate": 0.93, "pitch": -3,  "volume": 1.02, "before": 460, "after": 520},
    "emphasis":         {"rate": 0.96, "pitch": 1,   "volume": 1.02, "before": 320, "after": 420},
    "overview-title":   {"rate": 0.90, "pitch": -4,  "volume": 1.00, "before": 560, "after": 320},
    "overview-note":    {"rate": 0.98, "pitch": -1,  "volume": 0.96, "before": 220, "after": 380},
    "overview-card":    {"rate": 0.97, "pitch": 0,   "volume": 1.00, "before": 320, "after": 420},
    "table-intro":      {"rate": 0.92, "pitch": -3,  "volume": 1.00, "before": 520, "after": 320},
    "table-header":     {"rate": 0.95, "pitch": -2,  "volume": 1.00, "before": 160, "after": 300},
    "table-row":        {"rate": 0.93, "pitch": -2,  "volume": 0.99, "before": 120, "after": 340},
    "table-group":      {"rate": 0.93, "pitch": -3,  "volume": 1.00, "before": 360, "after": 300},
    "table-sum":        {"rate": 0.92, "pitch": -2,  "volume": 1.01, "before": 260, "after": 400},
    "table-cta":        {"rate": 0.97, "pitch": 0,   "volume": 1.00, "before": 300, "after": 460},
    "table-outro":      {"rate": 0.96, "pitch": -1,  "volume": 0.98, "before": 300, "after": 520},
}

DEFAULT_PROSODY = PROSODY["p"]

MELODY_AFTER_MS = {"question": 240, "exclaim": 200, "trailing": 380, "open": 60, "statement": 0}
MELODY_RATE = {"question": 0.98, "exclaim": 1.02, "trailing": 0.94, "open": 0.99, "statement": 1.0}

BASE_CPS = 15.2          # Zeichen pro Sekunde bei rate 1.0
HARD_CHUNK = 220         # identisch zum Reader
SAMPLE_RATE = 24000
TARGET_LUFS = -16.0
TARGET_TP = -1.5


def prosody_for(block_type: str) -> dict:
    return PROSODY.get(block_type, DEFAULT_PROSODY)


# ---------------------------------------------------------------------------
# Aussprache-Regie — spiegelbildlich zu speechNormalize() im Reader
# ---------------------------------------------------------------------------

MONTHS_DE = ["Januar", "Februar", "März", "April", "Mai", "Juni",
             "Juli", "August", "September", "Oktober", "November", "Dezember"]

# (Muster, Ersetzung) — dieselbe Reihenfolge wie ABBREV im Reader.
RULES_DE = [
    (re.compile(r"bzw\.", re.I), "beziehungsweise"),
    (re.compile(r"zzgl\.", re.I), "zuzüglich"),
    (re.compile(r"inkl\.", re.I), "inklusive"),
    (re.compile(r"exkl\.", re.I), "exklusiv"),
    (re.compile(r"ca\.", re.I), "circa"),
    (re.compile(r"usw\.", re.I), "und so weiter"),
    (re.compile(r"usf\.", re.I), "und so fort"),
    (re.compile(r"vgl\.", re.I), "vergleiche"),
    (re.compile(r"sog\.", re.I), "sogenannt"),
    (re.compile(r"geb\.", re.I), "geboren"),
    (re.compile(r"MwSt\."), "Mehrwertsteuer"),
    (re.compile(r"Abs\.\s?(\d+)"), r"Absatz \1"),
    (re.compile(r"Nr\.\s?(\d+)"), r"Nummer \1"),
    (re.compile(r"Nr\."), "Nummer"),
    (re.compile(r"Art\.\s?(\d+)"), r"Artikel \1"),
    (re.compile(r"S\.\s?(\d+)"), r"Seite \1"),
    (re.compile(r"Abb\.\s?(\d+)"), r"Abbildung \1"),
    (re.compile(r"Tab\.\s?(\d+)"), r"Tabelle \1"),
    (re.compile(r"\bz\.\s?B\.", re.I), "zum Beispiel"),
    (re.compile(r"\bu\.\s?a\.", re.I), "unter anderem"),
    (re.compile(r"\bd\.\s?h\.", re.I), "das heißt"),
    (re.compile(r"\bi\.\s?d\.\s?R\.", re.I), "in der Regel"),
    (re.compile(r"\bo\.\s?g\.", re.I), "oben genannt"),
    (re.compile(r"€\s?/\s?(Monat|Jahr|kWh|Person)", re.I), r"Euro pro \1"),
    (re.compile(r"ct/\s?kWh", re.I), "Cent pro Kilowattstunde"),
    (re.compile(r"kWh/a"), "Kilowattstunden pro Jahr"),
    (re.compile(r"kWh"), "Kilowattstunden"),
    (re.compile(r"kWp"), "Kilowatt Peak"),
    (re.compile(r"m²"), "Quadratmeter"),
    (re.compile(r"m³"), "Kubikmeter"),
    (re.compile(r"km/h"), "Kilometer pro Stunde"),
    (re.compile(r"Mio\.\s?€"), "Millionen Euro"),
    (re.compile(r"Mrd\.\s?€"), "Milliarden Euro"),
    (re.compile(r"\bMio\."), "Millionen"),
    (re.compile(r"\bMrd\."), "Milliarden"),
    (re.compile(r"\bTsd\."), "Tausend"),
    (re.compile(r"§\s?(\d+)"), r"Paragraph \1"),
    (re.compile(r"€"), "Euro"),
    (re.compile(r"(\d)\s?%"), r"\1 Prozent"),
    (re.compile(r"%"), "Prozent"),
]

_ENTITIES = [
    (re.compile(r"&nbsp;"), " "), (re.compile(r"&amp;"), "&"),
    (re.compile(r"&szlig;"), "ß"), (re.compile(r"&uuml;"), "ü"),
    (re.compile(r"&ouml;"), "ö"), (re.compile(r"&auml;"), "ä"),
    (re.compile(r"&euro;"), "€"), (re.compile(r"&[a-zA-Z]+;"), " "),
]


def _hold(store: list, value: str) -> str:
    store.append(str(value))
    return "\u0000%d\u0001" % (len(store) - 1)


def _unhold(text: str, store: list) -> str:
    def repl(m):
        idx = int(m.group(1))
        return store[idx] if 0 <= idx < len(store) else ""
    return re.sub(r"\u0000(\d+)\u0001", repl, text)


def normalize_speech(text: str, lang: str = "de") -> str:
    """Schreibsprache → Sprechsprache. Deckungsgleich mit speechNormalize().

    NUR-DEUTSCH-VERTRAG: Der Parameter `lang` wird ignoriert; geregelt
    wird ausschließlich nach deutschen Lautregeln. Die Signatur bleibt
    stabil, damit Reader, Generator und Paritäts-Gate dieselbe Funktion
    adressieren können.
    """
    del lang  # Nur-Deutsch-Vertrag — siehe Docstring.
    out = text or ""
    if not out:
        return ""
    store: list[str] = []

    for pattern, repl in _ENTITIES:
        out = pattern.sub(repl, out)
    out = re.sub(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f]", " ", out)
    out = out.replace("–", "-").replace("—", "-")
    # Schmuckzeichen, Pfeile und Emoji sind keine Wörter — wortgleich
    # zur Browser-Engine in static/premium/ff-voice.js.
    out = re.sub(r"[\u00ad\u200b-\u200f\u2060\u2190-\u21ff\u2300-\u27bf"
                 r"\u2b00-\u2bff\ufe00-\ufe0f\U0001f000-\U0010ffff]", " ", out)

    # E-Mail-Adressen
    def mail_repl(m):
        return _hold(store, m.group(0).replace("@", " at ").replace(".", " Punkt "))
    out = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", mail_repl, out)

    # Vollständige URLs
    def url_repl(m):
        spoken = re.sub(r"^https?://", "", m.group(0), flags=re.I).rstrip("/")
        spoken = spoken.replace(".", " Punkt ").replace("/", " ")
        return _hold(store, spoken)
    out = re.sub(r"\bhttps?://[^\s<>\"')]+", url_repl, out, flags=re.I)

    # Nackte Domains
    def dom_repl(m):
        return _hold(store, m.group(0).replace(".", " Punkt "))
    out = re.sub(r"\b([\w-]+\.(?:de|com|org|net|io|eu|info|blog))\b", dom_repl, out, flags=re.I)

    def date_repl(m):
        a, b, c = int(m.group(1)), int(m.group(2)), m.group(3)
        month, day = b, a
        if 1 <= month <= 12:
            return _hold(store, "%d. %s %s" % (day, MONTHS_DE[month - 1], c))
        return m.group(0)
    out = re.sub(r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b", date_repl, out)

    def short_date_repl(m):
        month = int(m.group(2))
        if 1 <= month <= 12:
            return _hold(store, "%d. %s" % (int(m.group(1)), MONTHS_DE[month - 1]))
        return m.group(0)
    out = re.sub(r"\b(\d{1,2})\.(\d{1,2})\.(?!\d)", short_date_repl, out)

    def time_repl(m):
        hh, mm = int(m.group(1)), int(m.group(2))
        return _hold(store, "%d Uhr" % hh if mm == 0 else "%d Uhr %d" % (hh, mm))
    out = re.sub(r"\b(\d{1,2}):(\d{2})\s?(Uhr)?\b", time_repl, out)

    for pattern, repl in RULES_DE:
        out = pattern.sub(repl, out)

    # Zahlenbereiche: 12 – 24 / 12-24
    word = " bis "
    out = re.sub(r"(\d)\s?(?:–|—|-)\s?(\d)", lambda m: m.group(1) + word + m.group(2), out)

    # Tausender-Trennzeichen: sprachrichtig ergänzen statt Leerzeichen schlucken
    sep = "."
    out = re.sub(r"(\d)\s(\d{3})\b", r"\1" + sep + r"\2", out)

    # Symbole
    out = out.replace("&", " und ")
    out = re.sub(r"\sx\s(?=\d)", " mal ", out)
    out = out.replace("+", " plus ").replace("=", " gleich ")
    out = out.replace("“", '"').replace("”", '"').replace("„", '"')
    out = out.replace("‘", "'").replace("’", "'").replace("‚", "'")

    out = re.sub(r"\s+", " ", out).strip()
    out = re.sub(r"\.{2,}(?!\.)", ".", out)
    out = re.sub(r"\s+([.,;:!?])", r"\1", out)

    return re.sub(r"\s+", " ", _unhold(out, store)).strip()


# ---------------------------------------------------------------------------
# Satzzerlegung & Atemgruppen (spiegelbildlich zum Reader)
# ---------------------------------------------------------------------------

_ABBREV_DOT = re.compile(
    r"\b(Abs|Art|Nr|S|Abb|Tab|Mio|Mrd|Tsd|bzw|ca|vgl|usw|usf|zzgl|inkl|exkl|sog|geb|MwSt)"
)
MASK = "\u0002"


def mask_sentence_dots(text: str) -> str:
    out = re.sub(r"(\d)\.(\d)", r"\1" + MASK + r"\2", text)
    out = re.sub(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b",
                 lambda m: m.group(0).replace(".", MASK), out)
    out = _ABBREV_DOT.sub(lambda m: m.group(0).replace(".", MASK), out)
    # Getrennt geschriebene Abkürzungen: „z. B.“, „u. a.“, „d. h.“, „e. g.“
    out = re.sub(r"\b([a-z])\.\s+([a-zA-Z])\.",
                 lambda m: m.group(1) + MASK + " " + m.group(2) + MASK, out)
    return out


def split_sentences(text: str) -> list:
    masked = mask_sentence_dots(text)
    parts = re.split(r"(?<=[.!?…])\s+(?=[\"'“„]?[A-ZÄÖÜ0-9(])", masked)
    if len(parts) <= 1:
        parts = re.split(r"(?<=[.!?…])\s+", masked)
    return [p.replace(MASK, ".").strip() for p in parts if p.strip()]


CONNECTIVES = re.compile(
    r"\b(und|oder|aber|denn|weil|da|wenn|falls|obwohl|während|damit|sodass|als|wie|"
    r"nachdem|bevor|seit|sowie|jedoch|allerdings|dennoch|trotzdem|deshalb|daher|"
    r"außerdem|zudem|and|or|but|because|although|however|while|whereas|since|if|"
    r"unless|therefore|moreover|furthermore|nevertheless)\b", re.I)


def density_factor(text: str) -> float:
    words = max(1, len(re.findall(r"\S+", text)))
    numbers = len(re.findall(r"\d", text))
    long_words = len(re.findall(r"\b\w{14,}\b", text))
    clauses = len(re.findall(r"[,;:]", text))
    score = (numbers / words) * 2.2 + (long_words / words) * 2.4 + (clauses / words) * 0.9
    return max(0.90, min(1.06, 1.02 - score))


def melody_of(text: str) -> str:
    if re.search(r"\?\s*$", text):
        return "question"
    if re.search(r"!\s*$", text):
        return "exclaim"
    if re.search(r"…\s*$", text):
        return "trailing"
    if re.search(r"[:,;]\s*$", text):
        return "open"
    return "statement"


def effective_rate(profile: dict, density: float, melody: str, final_chunk: bool) -> float:
    rate = profile["rate"] * density * MELODY_RATE.get(melody, 1.0) * (0.97 if final_chunk else 1.0)
    return max(0.75, min(1.22, rate))


def effective_volume(profile: dict, melody: str) -> float:
    return max(0.55, min(1.0, profile["volume"] + (0.04 if melody == "exclaim" else 0.0)))


def pause_after(profile: dict, melody: str, words: int, eff_rate: float) -> int:
    base = profile.get("after", 0) + MELODY_AFTER_MS.get(melody, 0)
    by_length = 120 if words > 28 else (60 if words > 16 else 0)
    return int(round((base + by_length) / max(0.8, eff_rate)))


def cut_at_connectives(text: str) -> list:
    out, rest, guard = [], text, 0
    while len(rest) > HARD_CHUNK and guard < 12:
        guard += 1
        cut = -1
        for m in CONNECTIVES.finditer(rest):
            at = m.start()
            if HARD_CHUNK * 0.4 < at < len(rest) - 40:
                cut = at
            if at > HARD_CHUNK:
                break
        if cut < 0:
            slice_ = rest[:HARD_CHUNK]
            last_stop = max(slice_.rfind(", "), slice_.rfind("; "), slice_.rfind(": "), slice_.rfind(" - "))
            cut = last_stop + 1 if last_stop > HARD_CHUNK * 0.35 else HARD_CHUNK
        out.append(rest[:cut].strip())
        rest = rest[cut:].strip()
    if rest:
        out.append(rest)
    return out


def split_for_speech(text: str, lang: str = "de") -> list:
    """Zerlegt einen Block in Atemgruppen – identisch zum Reader."""
    out = []
    for sentence in split_sentences(text):
        if len(sentence) <= HARD_CHUNK:
            out.append(sentence)
            continue
        for piece in cut_at_connectives(sentence):
            if len(piece) <= HARD_CHUNK:
                out.append(piece)
                continue
            buf = ""
            for word in piece.split():
                cand = buf + " " + word if buf else word
                if buf and len(cand) > HARD_CHUNK - 12:
                    out.append(buf.strip())
                    buf = word
                else:
                    buf = cand
            if buf.strip():
                out.append(buf.strip())
    return [s for s in out if s.strip()]


# ---------------------------------------------------------------------------
# WAV-Werkzeuge (reine Python-Standardbibliothek)
# ---------------------------------------------------------------------------

def read_wav_mono(path: str):
    """Liest eine WAV-Datei als (samples: list[int], sample_rate: int)."""
    with wave.open(path, "rb") as wf:
        channels = wf.getnchannels()
        width = wf.getsampwidth()
        rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
    if width == 2:
        data = struct.unpack("<%dh" % (len(frames) // 2), frames)
    elif width == 1:
        raw = struct.unpack("<%dB" % len(frames), frames)
        data = [(v - 128) * 256 for v in raw]
    elif width == 4:
        data = struct.unpack("<%di" % (len(frames) // 4), frames)
        data = [max(-32768, min(32767, v >> 16)) for v in data]
    else:
        raise ValueError("Unsupported sample width: %d" % width)
    if channels > 1:
        mono = []
        for i in range(0, len(data) - channels + 1, channels):
            chunk = data[i:i + channels]
            mono.append(int(sum(chunk) / channels))
        data = mono
    return list(data), rate


def _write_bytes(path: str, data: bytes) -> str:
    """Kleine Testhilfe: Bytes schreiben und den Pfad zurueckgeben."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)
    return path


def is_riff_wav(path: str) -> bool:
    """Erkennt echte RIFF/WAVE-Dateien am Kopf (nicht an der Endung)."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(12)
    except Exception:
        return False
    return len(head) >= 12 and head[0:4] == b"RIFF" and head[8:12] == b"WAVE"


def audio_kind(path: str) -> str:
    """'wav' | 'mp3' | 'ogg' | 'unknown' — nach Dateikopf, nie nach Endung.

    KERNBEFUND 06.09.2026: `edge-tts` liefert IMMER MP3
    (audio-24khz-48kbitrate-mono-mp3). Die Kette schrieb diesen Strom in
    eine Datei mit der Endung `.wav` und las sie danach mit dem
    `wave`-Modul — das scheiterte bei JEDEM Segment („file does not start
    with RIFF id“). Ergebnis: Tonspuren aus reinen Pausen (Digitalstille),
    34 Artikel live ohne einen Ton. Seitdem entscheidet der Dateikopf.
    """
    try:
        with open(path, "rb") as fh:
            head = fh.read(16)
    except Exception:
        return "unknown"
    if len(head) >= 12 and head[0:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "wav"
    if head[0:3] == b"ID3":
        return "mp3"
    if len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0:
        return "mp3"
    if head[0:4] == b"OggS":
        return "ogg"
    return "unknown"


# --- Dekoder-Kette (ffmpeg → miniaudio → soundfile) -------------------------

def _decode_ffmpeg(path: str, target_rate: int):
    if not has_ffmpeg():
        return None
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-f", "s16le",
           "-acodec", "pcm_s16le", "-ac", "1", "-ar", str(target_rate), "-"]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=900)
    except Exception:
        return None
    if proc.returncode != 0 or not proc.stdout:
        return None
    raw = proc.stdout
    n = len(raw) // 2
    if n <= 0:
        return None
    return list(struct.unpack("<%dh" % n, raw[: n * 2])), target_rate


def _decode_miniaudio(path: str, target_rate: int):
    try:
        import miniaudio  # type: ignore
    except Exception:
        return None
    try:
        decoded = miniaudio.decode_file(
            path, output_format=miniaudio.SampleFormat.SIGNED16,
            nchannels=1, sample_rate=target_rate)
    except Exception:
        return None
    samples = list(decoded.samples)
    if not samples:
        return None
    return samples, target_rate


def _decode_soundfile(path: str, target_rate: int):
    try:
        import soundfile as sf  # type: ignore
    except Exception:
        return None
    try:
        data, rate = sf.read(path, dtype="int16", always_2d=True)
    except Exception:
        return None
    try:
        mono = [int(sum(frame) / len(frame)) for frame in data]
    except Exception:
        return None
    if not mono:
        return None
    return mono, int(rate)


DECODERS = (
    ("ffmpeg", _decode_ffmpeg),
    ("miniaudio", _decode_miniaudio),
    ("soundfile", _decode_soundfile),
)


def decoder_name() -> str:
    """Name des ersten verfügbaren Fremdformat-Dekoders ('' = keiner)."""
    if has_ffmpeg():
        return "ffmpeg"
    try:
        import miniaudio  # noqa: F401
        return "miniaudio"
    except Exception:
        pass
    try:
        import soundfile  # noqa: F401
        return "soundfile"
    except Exception:
        pass
    return ""


def decoder_available() -> bool:
    return bool(decoder_name())


def decode_audio_mono(path: str, target_rate: int = SAMPLE_RATE):
    """Liest JEDES gelieferte Audioformat als (samples, rate).

    WAV geht ohne Fremdwerkzeug (Standardbibliothek), MP3/OGG über die
    Dekoder-Kette. Wirft, wenn nichts dekodieren kann — der Aufrufer
    zählt das Segment dann als fehlgeschlagen und die Spur wird
    verworfen, statt Stille zu veröffentlichen.
    """
    kind = audio_kind(path)
    if kind == "wav":
        return read_wav_mono(path)
    for name, fn in DECODERS:
        got = fn(path, target_rate)
        if got and got[0]:
            return got
    raise ValueError(
        "Audio-Format '%s' nicht dekodierbar (kein ffmpeg/miniaudio/soundfile): %s"
        % (kind, os.path.basename(path)))


# --- Hörbarkeit messen ------------------------------------------------------

SILENCE_FLOOR = 300        # |Amplitude| unter diesem Wert gilt als Stille
AUDIBLE_MIN_RATIO = 0.12   # mind. 12 % hörbare Rahmen = echte Sprache
AUDIBLE_MIN_RMS = 60       # digitale Stille hat RMS 0


def audio_stats(samples, sample_rate: int = SAMPLE_RATE) -> dict:
    """Messwerte einer Tonspur: Spitze, RMS und hörbarer Zeitanteil.

    Die Digitalstille-Spuren auf gh-pages hatten peak = 0 und rms = 0 —
    messbar, bevor sie jemand veröffentlicht. Der hörbare Anteil zählt
    20-ms-Rahmen über dem Stille-Boden; er entlarvt auch Spuren, die nur
    aus einem kurzen Knacken plus Stille bestehen.

    Zehn-Minuten-Artikel haben ~14 Mio. Abtastwerte. Gemessen wird
    deshalb mit Schrittweite (jeder n-te Wert je Rahmen) — für die
    Stille-Erkennung exakt genug und um Größenordnungen schneller.
    """
    n = len(samples)
    if not n:
        return {"peak": 0, "rms": 0.0, "audible_ratio": 0.0, "duration_ms": 0}
    frame = max(1, int(sample_rate * 0.02))          # 20-ms-Rahmen
    step = max(1, frame // 24)                        # ~24 Messpunkte je Rahmen
    peak = 0
    energy = 0.0
    counted = 0
    audible_frames = 0
    total_frames = 0
    for start in range(0, n, frame):
        stop = min(start + frame, n)
        total_frames += 1
        local_peak = 0
        for i in range(start, stop, step):
            v = samples[i]
            av = v if v >= 0 else -v
            if av > local_peak:
                local_peak = av
            energy += float(v) * float(v)
            counted += 1
        if local_peak > peak:
            peak = local_peak
        if local_peak >= SILENCE_FLOOR:
            audible_frames += 1
    rms = (energy / counted) ** 0.5 if counted else 0.0
    return {
        "peak": int(peak),
        "rms": round(rms, 2),
        "audible_ratio": round(audible_frames / float(total_frames or 1), 4),
        "duration_ms": int(round(n * 1000.0 / sample_rate)),
    }


def has_audible_speech(samples, sample_rate: int = SAMPLE_RATE,
                       min_ratio: float = AUDIBLE_MIN_RATIO) -> tuple:
    """(ok, grund) — trägt die Spur echten Ton? Stille wird NIE gedruckt."""
    st = audio_stats(samples, sample_rate)
    if st["peak"] <= 0 or st["rms"] < AUDIBLE_MIN_RMS:
        return False, "Digitalstille (peak=%d, rms=%.1f)" % (st["peak"], st["rms"])
    if st["audible_ratio"] < min_ratio:
        return False, "nur %.1f %% hörbarer Anteil" % (st["audible_ratio"] * 100.0)
    return True, ""


def write_wav_mono(path: str, samples, sample_rate: int = SAMPLE_RATE) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    packed = struct.pack("<%dh" % len(samples), *[max(-32768, min(32767, int(v))) for v in samples])
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(packed)


def silence_ms(ms: int, sample_rate: int = SAMPLE_RATE):
    return [0] * int(sample_rate * ms / 1000.0)


def trim_edges(samples, threshold: int = 220, window: int = 240):
    """Entfernt führende und trailing Stille (Atem statt Maschinenrhythmus)."""
    return trim_edges_info(samples, threshold, window)[0]


def trim_edges_info(samples, threshold: int = 220, window: int = 240):
    """Wie trim_edges, meldet aber zusätzlich die vorn entfernte Länge
    in SAMPLES. (Der Aufrufer rechnet sie bei bekannter Samplingrate in ms
    um — die Wortuhr der Studio-Tonspur zieht diesen Kopf-Versatz von den
    WordBoundary-Ticks ab, damit kein Wort zu früh markiert wird.)
    """
    if not samples:
        return samples, 0
    start = 0
    end = len(samples)
    while start < end and abs(samples[start]) < threshold:
        start += 1
    while end > start and abs(samples[end - 1]) < threshold:
        end -= 1
    start = max(0, start - window)
    end = min(len(samples), end + window)
    return samples[start:end], start


def apply_fade(samples, fade_ms: int = 10, sample_rate: int = SAMPLE_RATE):
    n = len(samples)
    if n == 0:
        return samples
    fade = max(1, int(sample_rate * fade_ms / 1000.0))
    fade = min(fade, n // 2)
    out = list(samples)
    for i in range(fade):
        g = i / float(fade)
        out[i] = int(out[i] * g)
        out[n - 1 - i] = int(out[n - 1 - i] * g)
    return out


def remove_dc(samples):
    if not samples:
        return samples
    mean = sum(samples) / float(len(samples))
    return [int(max(-32768, min(32767, v - mean))) for v in samples]


def declick(samples, threshold: int = 9000):
    """Glättet einzelne Ausreißer-Samples (Klicks an Segmenträndern)."""
    out = list(samples)
    for i in range(1, len(out) - 1):
        prev_v, cur, nxt = out[i - 1], out[i], out[i + 1]
        if abs(cur - prev_v) > threshold and abs(cur - nxt) > threshold:
            out[i] = int((prev_v + nxt) / 2)
    return out


def soft_limit(samples, ceiling: int = 31000):
    out = []
    for v in samples:
        if v > ceiling:
            v = ceiling + int((v - ceiling) * 0.25)
        elif v < -ceiling:
            v = -ceiling + int((v + ceiling) * 0.25)
        out.append(max(-32768, min(32767, int(v))))
    return out


def highpass(samples, cutoff_hz: float = 80.0, sample_rate: int = SAMPLE_RATE):
    """1-Pol-Hochpass gegen Grummeln und Windgeräusche (Korrekte RC-Form)."""
    if not samples:
        return samples
    rc = 1.0 / (2.0 * 3.141592653589793 * cutoff_hz)
    alpha = rc / (rc + 1.0 / sample_rate)
    out = []
    prev_in = float(samples[0])
    prev_out = 0.0
    for v in samples:
        x = float(v)
        y = alpha * (prev_out + x - prev_in)
        out.append(int(max(-32768, min(32767, y))))
        prev_in = x
        prev_out = y
    return out


def normalize_lufs_peak(samples, target_peak: float = 0.87):
    """Annäherung an EBU R128: RMS-basierte Angleichung + harter Peak-Schutz."""
    if not samples:
        return samples
    rms = (sum(v * v for v in samples) / float(len(samples))) ** 0.5
    if rms < 1e-6:
        return samples
    # −16 LUFS entspricht bei Sprache etwa diesem RMS-Zielbereich
    target_rms = 4200.0
    gain = target_rms / rms
    gain = max(0.15, min(6.0, gain))
    out = [int(max(-32768, min(32767, v * gain))) for v in samples]
    peak = max(abs(v) for v in out) or 1
    ceiling = int(32767 * target_peak)
    if peak > ceiling:
        g = ceiling / float(peak)
        out = [int(v * g) for v in out]
    return out


def concat_with_pauses(segments, sample_rate: int = SAMPLE_RATE):
    """segments: [(samples, pause_before_ms)] → eine durchgehende Spur."""
    out = []
    for samples, pause_ms in segments:
        if pause_ms > 0:
            out.extend(silence_ms(pause_ms, sample_rate))
        out.extend(samples)
    return out


def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def master_to_mp3(wav_path: str, mp3_path: str, sample_rate: int = SAMPLE_RATE) -> bool:
    """EBU-R128-Mastering über ffmpeg. Fällt ohne ffmpeg auf die WAV zurück."""
    if not has_ffmpeg():
        return False
    os.makedirs(os.path.dirname(mp3_path) or ".", exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", wav_path,
        "-af", "highpass=f=80,adeclick,afftdn=nf=-25,alimiter=limit=0.85,"
               "loudnorm=I=%.1f:TP=%.1f:LRA=11" % (TARGET_LUFS, TARGET_TP),
        "-ar", str(sample_rate), "-ac", "1",
        "-c:a", "libmp3lame", "-b:a", "64k",
        mp3_path,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=900)
        return os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 0
    except Exception:
        # Strengere Filterketten scheitern auf alten ffmpeg-Builds –
        # dann der einfache Weg mit Lautheits-Normalisierung.
        try:
            fallback = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", wav_path,
                "-af", "highpass=f=80,loudnorm=I=%.1f:TP=%.1f:LRA=11" % (TARGET_LUFS, TARGET_TP),
                "-ar", str(sample_rate), "-ac", "1",
                "-c:a", "libmp3lame", "-b:a", "64k", mp3_path,
            ]
            subprocess.run(fallback, check=True, capture_output=True, timeout=900)
            return os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 0
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------

def edge_available() -> bool:
    """Edge-Neuralstimmen nutzbar?

    Seit dem 06.09.2026 gehoert der MP3-Dekoder zur Verfuegbarkeit: Ohne
    ffmpeg/miniaudio/soundfile kann der MP3-Strom von edge-tts nicht in
    Ton verwandelt werden — genau daran sind 34 Tonspuren stumm
    geworden. Fehlt der Dekoder, gilt die Engine als NICHT verfuegbar,
    die Kette geht auf Piper und der Reader bleibt notfalls ehrlich auf
    der Geraetestimme.
    """
    try:
        import edge_tts  # noqa: F401
    except Exception:
        return False
    return decoder_available()


def edge_module_present() -> bool:
    try:
        import edge_tts  # noqa: F401
        return True
    except Exception:
        return False


def piper_available() -> bool:
    return shutil.which("piper") is not None


def available_engines() -> list:
    # NUR-DEUTSCH-VERTRAG: Der ehemalige englische Groq-Notnagel ist aus
    # der Kette entfernt — ein rein englisches Modell darf in einer
    # deutschpflichtigen Tonspurkette nicht mehr auftauchen.
    found = []
    if edge_available():
        found.append("edge")
    if piper_available():
        found.append("piper")
    return found


def _rate_to_edge(rate: float) -> str:
    pct = int(round((rate - 1.0) * 100))
    pct = max(-50, min(50, pct))
    return "%+d%%" % pct


def _pitch_to_edge(pitch_hz: int) -> str:
    return "%+dHz" % max(-50, min(50, int(pitch_hz)))


def _volume_to_edge(volume: float) -> str:
    pct = int(round((volume - 1.0) * 100))
    pct = max(-50, min(50, pct))
    return "%+d%%" % pct


def _cleanup(path: str) -> None:
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def synth_edge(text: str, lang: str, voice: str, rate: float, pitch: int, volume: float,
               out_wav: str):
    """Ein Segment mit einer Edge-Neuralstimme sprechen.

    KERNREPARATUR 06.09.2026: `edge-tts` liefert einen **MP3-Strom**
    (audio-24khz-48kbitrate-mono-mp3). Bisher wurde dieser Strom
    unveraendert in `out_wav` geschrieben und danach mit dem
    `wave`-Modul gelesen — das scheiterte bei JEDEM Segment
    („file does not start with RIFF id“). Die Folge: 34 live stehende
    Tonspuren aus reiner Digitalstille (peak = 0), „kein Ton, die
    Fortschrittsanzeige rennt durch“.

    Jetzt wird der Strom als MP3 abgelegt, ueber die Dekoder-Kette
    (ffmpeg / miniaudio / soundfile) geoeffnet, auf Hoerbarkeit geprueft
    und als echte 24-kHz-Mono-WAV geschrieben. Kein Ton = kein Segment.

    Nachrichtensprecher-Profil (Befund 07.09.2026): Unterstuetzt das
    installierte edge-tts den optionalen `style`-Parameter (Vortragsstil
    wie „serious“), wird er gereicht. Aeltere Pakete oder unbekannte
    Styles fuehren zu einem sauberen Retry OHNE Style — der Ton darf nie
    an einem Komfort-Merkmal scheitern.

    Rueckgabe: (ok, word_boundaries) — Wortgrenzen in 100-ns-Ticks;
    Grundlage der wortgenauen Leseanzeige (Wortuhr in der
    Tonspur-Konfiguration).

    `lang` wird ignoriert (Nur-Deutsch-Vertrag); die Signatur bleibt
    gegenueber Reader, Generator und Tests stabil.
    """
    import edge_tts
    del lang  # Nur-Deutsch-Vertrag — die Stimme entscheidet Deutsch.
    os.makedirs(os.path.dirname(out_wav) or ".", exist_ok=True)

    def _make(style=None):
        kwargs = dict(rate=_rate_to_edge(rate), volume=_volume_to_edge(volume),
                      pitch=_pitch_to_edge(pitch))
        if style:
            try:
                return edge_tts.Communicate(text, voice, style=style, **kwargs)
            except TypeError:
                pass  # Dieses edge-tts kennt keine Styles — neutral sprechen.
        return edge_tts.Communicate(text, voice, **kwargs)

    src_path = out_wav + ".edge.src"

    # Erster Versuch mit dem Profil-Style, bei Bedarf einer ohne —
    # ein Newsroom-Stil ist Komfort, Ton ist Pflicht.
    style_tries = [style, None] if style else [None]

    for attempt_style in style_tries:
        comm = _make(attempt_style)
        boundaries = []

        async def run(comm=comm, boundaries=boundaries):
            with open(src_path, "wb") as fh:
                async for chunk in comm.stream():
                    if chunk["type"] == "audio":
                        fh.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        boundaries.append({
                            "offset": chunk.get("offset", 0),
                            "duration": chunk.get("duration", 0),
                            "text": chunk.get("text", ""),
                        })

        try:
            try:
                loop = asyncio.new_event_loop()
            except Exception:
                loop = None
            if loop is None:
                asyncio.run(run())
            else:
                try:
                    loop.run_until_complete(run())
                finally:
                    loop.close()
        except Exception:
            _cleanup(src_path)
            continue

        if not os.path.exists(src_path) or os.path.getsize(src_path) == 0:
            _cleanup(src_path)
            continue

        try:
            samples, src_rate = decode_audio_mono(src_path, SAMPLE_RATE)
        except Exception:
            _cleanup(src_path)
            continue
        _cleanup(src_path)

        audible, _why = has_audible_speech(samples, src_rate)
        if not audible:
            continue
        write_wav_mono(out_wav, samples, src_rate)
        return True, boundaries

    return False, []


def synth_piper(text: str, voice: str, out_wav: str):
    """Lokale ONNX-Stimme. Liefert nur True, wenn die Datei echten Ton traegt."""
    if not piper_available():
        return False
    os.makedirs(os.path.dirname(out_wav) or ".", exist_ok=True)
    cmd = ["piper", "--model", voice, "--output_file", out_wav]
    try:
        proc = subprocess.run(cmd, input=text.encode("utf-8"),
                              capture_output=True, timeout=600)
    except Exception:
        return False
    if proc.returncode != 0 or not os.path.exists(out_wav) or os.path.getsize(out_wav) == 0:
        return False
    return True


# ---------------------------------------------------------------------------
# Segment-Synthese mit Wiederholungen, Engine-Kette und Hoerbarkeits-Pruefung
# ---------------------------------------------------------------------------
# Der fruehere dritte Zweig „groq“ (canopylabs/orpheus-v1-english) war eine
# AUSSCHLIESSLICH englische Stimme und steht damit im Widerspruch zum
# Nur-Deutsch-Vertrag. Er ist ersatzlos entfernt; die Kette lautet
# edge -> piper -> ehrliche Browser-/Gerätestimme im Reader.

SYNTH_ATTEMPTS = 3          # Versuche je Engine (Netz-Aussetzer sind normal)
SYNTH_BACKOFF = (0.8, 2.0)  # Wartezeit vor Versuch 2 und 3 in Sekunden


def _retry_sleep(seconds: float) -> None:
    """Wartezeit zwischen zwei Versuchen (im Selbsttest abschaltbar)."""
    try:
        factor = float(os.environ.get("FF_VOICE_RETRY_SLEEP", "1"))
    except Exception:
        factor = 1.0
    if factor <= 0:
        return
    try:
        import time
        time.sleep(seconds * factor)
    except Exception:
        pass


def verify_segment(out_wav: str) -> tuple:
    """(ok, grund) — traegt die geschriebene Segmentdatei echten Ton?

    Ein Backend kann „erfolgreich“ eine leere, unlesbare oder stumme
    Datei liefern (Befund 06.09.2026). Erst diese Pruefung entscheidet,
    ob ein Segment als gesprochen gilt.
    """
    if not out_wav or not os.path.exists(out_wav) or os.path.getsize(out_wav) == 0:
        return False, "keine Datei"
    try:
        samples, rate = decode_audio_mono(out_wav, SAMPLE_RATE)
    except Exception as exc:
        return False, "nicht dekodierbar (%s)" % (str(exc).split("(")[0].strip() or "unbekannt")
    if not samples:
        return False, "leeres Audio"
    ok, why = has_audible_speech(samples, rate)
    if not ok:
        return False, why
    if audio_kind(out_wav) != "wav":
        # Fremdformat in eine echte WAV ueberfuehren, damit die
        # Weiterverarbeitung ohne Dekoder auskommt.
        write_wav_mono(out_wav, samples, rate)
    return True, ""


def synthesize(text: str, lang: str, engine: str, profile_name: str, out_wav: str,
               rate: float = 1.0, pitch: int = 0, volume: float = 1.0,
               attempts: int = SYNTH_ATTEMPTS, allow_engine_fallback: bool = True):
    """Ein Segment sprechen. Gibt (engine, ok, word_boundaries) zurueck.

    NUR-DEUTSCH-VERTRAG: `lang` wird ignoriert — gesprochen wird
    ausschliesslich mit der deutschen Nachrichtensprecher-Stimme des
    Profils. Die Signatur bleibt gegenueber Generator und Tests stabil.

    ROBUSTHEIT (07.09.2026):
      1. Jede Engine wird bis zu `attempts` Mal versucht — ein einzelner
         Netz-Aussetzer beim Edge-Dienst darf nicht die Tonspur eines
         ganzen Artikels kosten (Verlagsregel seit dem 06.09.: ein
         fehlendes Segment verwirft die komplette Spur).
      2. Danach uebernimmt die naechste verfuegbare Engine der Kette
         (edge -> piper), sofern erlaubt.
      3. JEDES Ergebnis wird gemessen: dekodierbar, nicht stumm. Nur
         hoerbare Segmente gelten als Erfolg.
    """
    del lang  # Nur-Deutsch-Vertrag — immer die deutsche Stimme.
    profile = VOICE_PROFILES.get(profile_name) or VOICE_PROFILES[DEFAULT_PROFILE]
    voice = profile["de"]
    style = profile.get("style")

    chain = [engine]
    if allow_engine_fallback:
        for name in ENGINE_ORDER:
            if name not in chain:
                chain.append(name)

    for eng in chain:
        if eng == "edge" and not edge_available():
            continue
        if eng == "piper" and not piper_available():
            continue
        if eng not in ("edge", "piper"):
            continue   # keine dritte, fremdsprachige Stufe mehr
        for attempt in range(max(1, attempts)):
            if attempt:
                _retry_sleep(SYNTH_BACKOFF[min(attempt - 1, len(SYNTH_BACKOFF) - 1)])
            ok = False
            boundaries = []
            try:
                if eng == "edge":
                    ok, boundaries = synth_edge(text, "de", voice, rate, pitch, volume,
                                                 out_wav, style=style)
                elif eng == "piper":
                    ok = synth_piper(text, PIPER_VOICES["de"], out_wav)
            except Exception:
                ok = False
            if not ok:
                continue
            good, _why = verify_segment(out_wav)
            if good:
                return eng, True, boundaries
        # Engine erschoepft — naechste Kettenstufe
    return engine, False, []


# ---------------------------------------------------------------------------
# Selbsttest (ohne Netzwerk, ohne Schlüssel)
# ---------------------------------------------------------------------------

def _selftest() -> int:
    results = []

    def check(name, cond):
        results.append((name, bool(cond)))

    # Aussprache DE
    check("DE: 650 € → Euro", normalize_speech("bis zu 650 €", "de") == "bis zu 650 Euro")
    check("DE: 12 – 24 → bis", normalize_speech("12 – 24 Monate", "de") == "12 bis 24 Monate")
    check("DE: 12-24 → bis", normalize_speech("12-24 Monate", "de") == "12 bis 24 Monate")
    check("DE: % → Prozent", normalize_speech("ca. 3,5 %", "de") == "circa 3,5 Prozent")
    check("DE: § → Paragraph", normalize_speech("§ 12", "de") == "Paragraph 12")
    check("DE: kWh", normalize_speech("20.000 kWh", "de") == "20.000 Kilowattstunden")
    check("DE: m²", normalize_speech("80 m²", "de") == "80 Quadratmeter")
    check("DE: z. B.", normalize_speech("z. B. Strom", "de") == "zum Beispiel Strom")
    check("DE: Datum", normalize_speech("Stand 02.01.2006", "de") == "Stand 2. Januar 2006")
    check("DE: Uhrzeit", normalize_speech("14:30 Uhr", "de") == "14 Uhr 30")
    check("DE: ct/kWh", normalize_speech("12 ct/kWh", "de") == "12 Cent pro Kilowattstunde")
    check("DE: Mio.", normalize_speech("1,5 Mio. €", "de") == "1,5 Millionen Euro")
    check("DE: Zahlen mit Punkt bleiben", normalize_speech("1.234,56 Euro", "de") == "1.234,56 Euro")

    # NUR-DEUTSCH-VERTRAG (Befund 07.09.2026): Auch englisch deklarierte
    # Eingaben werden ausschließlich nach deutschen Regeln geregelt —
    # eine englische Aussprachekette existiert nicht mehr.
    check("Nur-Deutsch: 'en'-Angabe ⇒ deutsche Regeln",
          normalize_speech("about 20%", "en") == "about 20 Prozent")
    check("Nur-Deutsch: Dollar-Regel ist ersatzlos entfallen",
          normalize_speech("Save $1,200", "en") == "Save $1,200")
    check("Nur-Deutsch: Datum bleibt deutsch (TT.MM.JJJJ)",
          normalize_speech("on 02/01/2006", "en") == "on 2. Januar 2006")
    check("DE: % ohne Leerzeichen", normalize_speech("rund 30%", "de") == "rund 30 Prozent")

    # Satzzerlegung
    check("Satz: Abkürzung trennt nicht",
          len(split_sentences("Das gilt z. B. für Gas. Danach kommt Strom.")) == 2)
    check("Satz: Dezimalzahl trennt nicht",
          len(split_sentences("Der Wert liegt bei 1.234,56 Euro. Punkt.")) == 2)
    check("Satz: Frage erhalten", split_sentences("Geht das?")[0].endswith("?"))

    # Atemgruppen
    long_text = "Und " + "weil der Arbeitspreis in diesem Tarif über die gesamte Laufzeit " * 6
    pieces = split_for_speech(long_text, "de")
    check("Chunk: harte Grenze eingehalten", all(len(p) <= HARD_CHUNK for p in pieces))
    check("Chunk: eigentlich gesplittet", len(pieces) >= 2)

    # Prosodie
    check("Prosodie: Überschrift ruhiger als Fließtext",
          PROSODY["h2"]["rate"] < PROSODY["p"]["rate"])
    check("Prosodie: Warnung lauter als Fließtext",
          PROSODY["warning"]["volume"] >= PROSODY["p"]["volume"])
    check("Prosodie: Tabellenzeile ruhiger", PROSODY["table-row"]["rate"] < PROSODY["p"]["rate"])
    check("Dichte: Zahlen verlangsamen", density_factor("20.000 kWh kosten 1.234,56 Euro") < 1.0)
    check("Dichte: einfacher Satz beschleunigt", density_factor("Das ist gut.") > 1.0)
    check("Melodie: Frage erkannt", melody_of("Geht das?") == "question")
    check("Melodie: Ausruf erkannt", melody_of("Achtung!") == "exclaim")
    check("Rate: Grenzen eingehalten", 0.75 <= effective_rate(PROSODY["p"], 1.0, "statement", False) <= 1.22)

    # Stimmen — NUR-DEUTSCH-VERTRAG (Profi-Agentur, 07.09.2026)
    check("Stimmen: news = deutscher Nachrichtensprecher",
          VOICE_PROFILES[DEFAULT_PROFILE]["de"] == "de-DE-ConradNeural")
    check("Stimmen: news führt News-Stil serious",
          VOICE_PROFILES[DEFAULT_PROFILE].get("style") == "serious")
    check("Stimmen: Voreinstellung der Kette ist news", DEFAULT_PROFILE == "news")
    check("Stimmen: alle Profile männlich-deutsche Neuralstimme",
          all("de-DE-" in v["de"] and v["de"].endswith("Neural") for v in VOICE_PROFILES.values()))
    check("Stimmen: kein EN-Profil mehr",
          all("en" not in v for v in VOICE_PROFILES.values()))
    check("Stimmen: kein en-Schlüssel in PIPER_VOICES", "en" not in PIPER_VOICES)
    check("Piper: nur DE gesetzt", set(PIPER_VOICES.keys()) == {"de"})
    check("Kette: groq ist entfernt", "groq" not in ENGINE_ORDER and len(ENGINE_ORDER) == 2)
    check("Kette: Engine-Reihenfolge edge → piper", ENGINE_ORDER == ["edge", "piper"])
    check("profile_voice: unbekannte Profile fallen auf news",
          profile_voice("unbekannt") == VOICE_PROFILES["news"]["de"])

    # Audio-Werkzeuge
    tone = [int(9000 * (1 if (i // 40) % 2 == 0 else -1)) for i in range(2400)]
    padded = [0] * 500 + tone + [0] * 500
    trimmed = trim_edges(padded)
    check("Audio: Stille abgeschnitten", len(trimmed) < len(padded))
    check("Audio: DC entfernt", abs(sum(remove_dc([1000] * 500)) / 500.0) < 1.0)
    clicky = [0] * 100 + [32000] + [0] * 100
    check("Audio: Klick geglättet", abs(declick(clicky)[100]) < 20000)
    faded = apply_fade([10000] * 1000, 10)
    check("Audio: Fade beginnt leise", abs(faded[0]) < abs(faded[500]))
    limited = soft_limit([40000] * 100)
    check("Audio: Limiter greift", max(limited) < 40000)
    check("Audio: Hochpass dämpft DC", abs(sum(highpass([5000] * 4000))) < sum([5000] * 4000))
    norm = normalize_lufs_peak([300] * 4000)
    check("Audio: Lautheit angehoben", max(abs(v) for v in norm) > 300)
    joined = concat_with_pauses([([1, 2, 3], 100), ([4, 5], 0)], 24000)
    check("Audio: Pausen eingesetzt", len(joined) > 5)

    # ------------------------------------------------------------------
    # KERNBEFUND 06.09.2026 — MP3 in einer .wav-Datei, Digitalstille live
    # ------------------------------------------------------------------
    import tempfile

    tmp = tempfile.mkdtemp(prefix="ff-voice-selftest-")

    mp3_like = os.path.join(tmp, "seg.wav")          # edge-tts schreibt MP3!
    with open(mp3_like, "wb") as fh:
        fh.write(b"ID3\x03\x00\x00\x00\x00\x00\x00" + b"\xff\xfb\x90\x00" + b"\x00" * 2048)
    check("Format: MP3 trotz .wav-Endung erkannt", audio_kind(mp3_like) == "mp3")
    check("Format: MP3 ohne ID3-Kopf erkannt (Frame-Sync)", audio_kind(
        _write_bytes(os.path.join(tmp, "raw.bin"), b"\xff\xfb\x90\x00" + b"\x00" * 64)) == "mp3")

    speech_like = []
    for i in range(SAMPLE_RATE * 2):
        t = i / float(SAMPLE_RATE)
        env = 0.5 + 0.5 * math.sin(2 * math.pi * 4 * t)
        speech_like.append(int(9000 * env * math.sin(2 * math.pi * 170 * t)))
    wav_real = os.path.join(tmp, "real.wav")
    write_wav_mono(wav_real, speech_like)
    check("Format: echte WAV erkannt", audio_kind(wav_real) == "wav")
    check("Dekoder: WAV ohne Fremdwerkzeug lesbar", len(decode_audio_mono(wav_real)[0]) > 0)

    silence = [0] * (SAMPLE_RATE * 3)
    wav_silent = os.path.join(tmp, "silent.wav")
    write_wav_mono(wav_silent, silence)

    st_silence = audio_stats(silence)
    st_speech = audio_stats(speech_like)
    check("Messung: Digitalstille hat peak 0", st_silence["peak"] == 0)
    check("Messung: Digitalstille hat rms 0", st_silence["rms"] == 0)
    check("Messung: Sprache hat Pegel", st_speech["peak"] > 1000 and st_speech["rms"] > 100)
    check("Messung: hörbarer Anteil bei Sprache hoch", st_speech["audible_ratio"] > 0.5)
    check("Messung: hörbarer Anteil bei Stille null", st_silence["audible_ratio"] == 0)
    check("Messung: Laufzeit stimmt", abs(st_silence["duration_ms"] - 3000) <= 2)

    check("Wache: Stille wird abgewiesen", has_audible_speech(silence)[0] is False)
    check("Wache: Sprache wird angenommen", has_audible_speech(speech_like)[0] is True)
    check("Wache: Grund wird benannt", "Digitalstille" in has_audible_speech(silence)[1])

    ok_seg, why_seg = verify_segment(wav_silent)
    check("Segment: stumme Datei fällt durch", ok_seg is False and bool(why_seg))
    check("Segment: sprechende Datei besteht", verify_segment(wav_real)[0] is True)
    check("Segment: leere Datei fällt durch",
          verify_segment(_write_bytes(os.path.join(tmp, "empty.wav"), b""))[0] is False)
    if not decoder_available():
        check("Segment: MP3 ohne Dekoder fällt ehrlich durch", verify_segment(mp3_like)[0] is False)
    else:
        check("Segment: MP3-Attrappe ohne Ton fällt durch", verify_segment(mp3_like)[0] is False)

    # Engine-Verfügbarkeit hängt am Dekoder (sonst wieder Stille-Spuren)
    check("Engine: edge ohne Dekoder nicht verfügbar",
          (not edge_module_present()) or decoder_available() or (edge_available() is False))

    # ------------------------------------------------------------------
    # Wiederholungen + Engine-Kette (offline, monkeygepatcht)
    # ------------------------------------------------------------------
    globals_ = globals()
    orig = {k: globals_[k] for k in ("synth_edge", "synth_piper", "edge_available",
                                     "piper_available")}
    os.environ["FF_VOICE_RETRY_SLEEP"] = "0"
    try:
        calls = {"edge": 0, "piper": 0}

        def flaky_edge(text, lang, voice, rate, pitch, volume, out_wav, style=None):
            calls["edge"] += 1
            if calls["edge"] < 3:
                return False, []                     # zwei Netz-Aussetzer
            write_wav_mono(out_wav, speech_like)
            return True, [{"offset": 0, "duration": 10, "text": "x"}]

        globals_["synth_edge"] = flaky_edge
        globals_["edge_available"] = lambda: True
        globals_["piper_available"] = lambda: False
        eng, ok, _b = synthesize("Test", "de", "edge", "natural", os.path.join(tmp, "s1.wav"))
        check("Kette: Wiederholung rettet das Segment", ok is True and eng == "edge")
        check("Kette: genau drei Versuche", calls["edge"] == 3)

        calls["edge"] = 0

        def dead_edge(text, lang, voice, rate, pitch, volume, out_wav, style=None):
            calls["edge"] += 1
            return False, []

        def good_piper(text, voice, out_wav):
            calls["piper"] += 1
            write_wav_mono(out_wav, speech_like)
            return True

        globals_["synth_edge"] = dead_edge
        globals_["synth_piper"] = good_piper
        globals_["piper_available"] = lambda: True
        eng, ok, _b = synthesize("Test", "de", "edge", "natural", os.path.join(tmp, "s2.wav"))
        check("Kette: Piper übernimmt nach Edge-Ausfall", ok is True and eng == "piper")
        check("Kette: Edge vorher ausgereizt", calls["edge"] == SYNTH_ATTEMPTS)

        def silent_piper(text, voice, out_wav):
            write_wav_mono(out_wav, silence)         # „Erfolg“ ohne Ton
            return True

        globals_["synth_piper"] = silent_piper
        eng, ok, _b = synthesize("Test", "de", "edge", "natural", os.path.join(tmp, "s3.wav"))
        check("Kette: stummer „Erfolg“ zählt als Fehlschlag", ok is False)
    finally:
        for k, v in orig.items():
            globals_[k] = v
        os.environ.pop("FF_VOICE_RETRY_SLEEP", None)
        shutil.rmtree(tmp, ignore_errors=True)

    failed = [n for n, ok in results if not ok]
    for name, ok in results:
        if not ok:
            print("  ✗ " + name)
    print("FF-VOICE-BACKENDS – Selbsttest: %d/%d bestanden" % (len(results) - len(failed), len(results)))
    return 1 if failed else 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _selftest()
    print("Verfügbare Engines: %s" % (", ".join(available_engines()) or "keine"))
    for name, prof in VOICE_PROFILES.items():
        marker = "  ← Voreinstellung (Nur-Deutsch)" if name == DEFAULT_PROFILE else ""
        print("  Profil %-9s DE %-36s Stil %-9s%s"
              % (name, prof["de"], prof.get("style") or "neutral", marker))
    print("Selbsttest: python3 scripts/ff_voice_backends.py --selftest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
