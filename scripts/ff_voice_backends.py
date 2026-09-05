#!/usr/bin/env python3
"""ff_voice_backends.py — Stimmen-Kette, Aussprache und Prosodie (FF Voice Studio).

Gegenstück zu `static/premium/ff-voice.js` auf der Serverseite. Beide
sprechen denselben Text mit derselben Regie — die Parität wird durch
`scripts/ff_voice_parity_check.py` erzwungen. Wäre sie nicht erzwungen,
klänge derselbe Artikel je nach Gerät unterschiedlich.

STIMMEN (männlich, Deutsch + Englisch, ohne Umschalter)
    edge   (Voreinstellung)  Microsoft-Edge-Neuralstimmen über das offene
                             Paket `edge-tts`: kein Key, kein Konto, keine
                             Zeichenkosten.
                             Profil „natural“ : de-DE-FlorianMultilingualNeural
                                                en-US-AndrewMultilingualNeural
                             Profil „narrator“: de-DE-ConradNeural
                                                en-GB-RyanNeural
                             Multilingual-v2-Stimmen sprechen englische
                             Fachbegriffe im deutschen Satz in derselben
                             Stimme — kein Timbresprung.
    piper  (Offline-Fallback) Lokale ONNX-Stimmen (de_DE-thorsten-high,
                             en_US-ryan-high): offline, unbegrenzt,
                             lizenzsauber, deterministisch.
    groq   (Notnagel)        Nur Englisch (canopylabs/orpheus-v1-english),
                             braucht GROQ_API_KEY.

Ohne verfügbares Backend wird KEINE Tonspur geschrieben; der Reader
bleibt dann beim lokalen Web-Speech-Pfad — niemals stumm.

AUSSPRACHE-REGIE
    Zahlen, Währungen, Daten, Zeiten, Prozente, Paragraphen, Abkürzungen,
    Einheiten und URLs werden vor der Synthese in gesprochene Sprache
    übersetzt — getrennt für DE und EN, in derselben Reihenfolge wie im
    Reader (siehe `RULES_DE` / `RULES_EN`).

PROSODIE-REGIE
    Jede Rolle (Überschrift, Fließtext, Tabellenzeile, Warnhinweis …)
    bekommt Tempo, Tonlage und Lautstärke. Dieselben Werte stehen in
    `PROSODY` im Reader.

Selbsttest ohne Netzwerk und ohne Schlüssel:
    python3 scripts/ff_voice_backends.py --selftest
"""

from __future__ import annotations

import asyncio
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
    "natural": {
        "de": "de-DE-FlorianMultilingualNeural",
        "en": "en-US-AndrewMultilingualNeural",
        "label": "Multilingual v2 (Florian / Andrew)",
    },
    "narrator": {
        "de": "de-DE-ConradNeural",
        "en": "en-GB-RyanNeural",
        "label": "Sprecher (Conrad / Ryan)",
    },
}

PIPER_VOICES = {
    "de": "de_DE-thorsten-high",
    "en": "en_US-ryan-high",
}

GROQ_MODEL = "canopylabs/orpheus-v1-english"

ENGINE_ORDER = ["edge", "piper", "groq"]

# Backend-Fingerprint: ändert er sich, werden Tonspuren neu erzeugt.
RECIPE_VERSION = "ff-voice-2026.09.05-b"

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
MONTHS_EN = ["January", "February", "March", "April", "May", "June",
             "July", "August", "September", "October", "November", "December"]

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

RULES_EN = [
    (re.compile(r"\be\.\s?g\.", re.I), "for example"),
    (re.compile(r"\bi\.\s?e\.", re.I), "that is"),
    (re.compile(r"\betc\.", re.I), "and so on"),
    (re.compile(r"\bapprox\.", re.I), "approximately"),
    (re.compile(r"\bvs\.", re.I), "versus"),
    (re.compile(r"\bNo\.\s?(\d+)"), r"number \1"),
    (re.compile(r"\bMr\."), "Mister"),
    (re.compile(r"\bMrs\."), "Misses"),
    (re.compile(r"kWh/a"), "kilowatt hours per year"),
    (re.compile(r"kWh", re.I), "kilowatt hours"),
    (re.compile(r"kWp", re.I), "kilowatt peak"),
    (re.compile(r"sq\s?m", re.I), "square meters"),
    (re.compile(r"cu\s?m", re.I), "cubic meters"),
    (re.compile(r"£\s?(\d[\d.,]*)"), r"\1 pounds"),
    (re.compile(r"\$(\d[\d.,]*)"), r"\1 dollars"),
    (re.compile(r"(\d[\d.,]*)\s?\$"), r"\1 dollars"),
    (re.compile(r"(\d)\s?%"), r"\1 percent"),
    (re.compile(r"%"), "percent"),
    (re.compile(r"§\s?(\d+)"), r"section \1"),
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
    """Schreibsprache → Sprechsprache. Deckungsgleich mit speechNormalize()."""
    L = "en" if lang == "en" else "de"
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
        return _hold(store, m.group(0).replace("@", " at ").replace(".", " Punkt " if L == "de" else " dot "))
    out = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", mail_repl, out)

    # Vollständige URLs
    def url_repl(m):
        spoken = re.sub(r"^https?://", "", m.group(0), flags=re.I).rstrip("/")
        spoken = spoken.replace(".", " Punkt " if L == "de" else " dot ").replace("/", " ")
        return _hold(store, spoken)
    out = re.sub(r"\bhttps?://[^\s<>\"')]+", url_repl, out, flags=re.I)

    # Nackte Domains
    def dom_repl(m):
        return _hold(store, m.group(0).replace(".", " Punkt " if L == "de" else " dot "))
    out = re.sub(r"\b([\w-]+\.(?:de|com|org|net|io|eu|info|blog))\b", dom_repl, out, flags=re.I)

    months = MONTHS_EN if L == "en" else MONTHS_DE

    def date_repl(m):
        a, b, c = int(m.group(1)), int(m.group(2)), m.group(3)
        month, day = (a, b) if L == "en" else (b, a)
        if 1 <= month <= 12:
            return _hold(store, "%d. %s %s" % (day, months[month - 1], c))
        return m.group(0)
    out = re.sub(r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b", date_repl, out)

    def short_date_repl(m):
        month = int(m.group(2))
        if 1 <= month <= 12:
            return _hold(store, "%d. %s" % (int(m.group(1)), months[month - 1]))
        return m.group(0)
    out = re.sub(r"\b(\d{1,2})\.(\d{1,2})\.(?!\d)", short_date_repl, out)

    def time_repl(m):
        hh, mm = int(m.group(1)), int(m.group(2))
        if L == "de":
            return _hold(store, "%d Uhr" % hh if mm == 0 else "%d Uhr %d" % (hh, mm))
        return _hold(store, "%d o'clock" % hh if mm == 0 else "%d %s" % (hh, ("oh %d" % mm) if mm < 10 else mm))
    out = re.sub(r"\b(\d{1,2}):(\d{2})\s?(Uhr)?\b", time_repl, out)

    for pattern, repl in (RULES_DE if L == "de" else RULES_EN):
        out = pattern.sub(repl, out)

    # Zahlenbereiche: 12 – 24 / 12-24
    word = " bis " if L == "de" else " to "
    out = re.sub(r"(\d)\s?(?:–|—|-)\s?(\d)", lambda m: m.group(1) + word + m.group(2), out)

    # Tausender-Trennzeichen: sprachrichtig ergänzen statt Leerzeichen schlucken
    sep = "." if L == "de" else ","
    out = re.sub(r"(\d)\s(\d{3})\b", r"\1" + sep + r"\2", out)

    # Symbole
    out = out.replace("&", " und " if L == "de" else " and ")
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
    if not samples:
        return samples
    start = 0
    end = len(samples)
    while start < end and abs(samples[start]) < threshold:
        start += 1
    while end > start and abs(samples[end - 1]) < threshold:
        end -= 1
    start = max(0, start - window)
    end = min(len(samples), end + window)
    return samples[start:end]


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
    try:
        import edge_tts  # noqa: F401
        return True
    except Exception:
        return False


def piper_available() -> bool:
    return shutil.which("piper") is not None


def groq_available() -> bool:
    return bool(os.environ.get("GROQ_API_KEY"))


def available_engines() -> list:
    found = []
    if edge_available():
        found.append("edge")
    if piper_available():
        found.append("piper")
    if groq_available():
        found.append("groq")
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


def synth_edge(text: str, lang: str, voice: str, rate: float, pitch: int, volume: float,
               out_wav: str):
    """Gibt (ok, word_boundaries) zurück. Wortgrenzen in 100-ns-Ticks."""
    import edge_tts
    os.makedirs(os.path.dirname(out_wav) or ".", exist_ok=True)
    comm = edge_tts.Communicate(
        text, voice,
        rate=_rate_to_edge(rate),
        volume=_volume_to_edge(volume),
        pitch=_pitch_to_edge(pitch),
    )
    boundaries = []
    try:
        loop = asyncio.new_event_loop()
    except Exception:
        loop = None

    async def run():
        with open(out_wav, "wb") as fh:
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
        if loop is None:
            asyncio.run(run())
        else:
            try:
                loop.run_until_complete(run())
            finally:
                loop.close()
    except Exception:
        return False, []
    ok = os.path.exists(out_wav) and os.path.getsize(out_wav) > 0
    return ok, boundaries


def synth_piper(text: str, voice: str, out_wav: str):
    if not piper_available():
        return False
    os.makedirs(os.path.dirname(out_wav) or ".", exist_ok=True)
    cmd = ["piper", "--model", voice, "--output_file", out_wav]
    try:
        proc = subprocess.run(cmd, input=text.encode("utf-8"),
                              capture_output=True, timeout=600)
        return proc.returncode == 0 and os.path.exists(out_wav) and os.path.getsize(out_wav) > 0
    except Exception:
        return False


def synth_groq(text: str, out_wav: str):
    """Nur Englisch — Notnagel, wenn edge und piper fehlen."""
    import urllib.request
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return False
    try:
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/audio/speech",
            data=__import__("json").dumps({
                "model": GROQ_MODEL, "input": text[:4000], "voice": "autumn",
                "response_format": "wav",
            }).encode("utf-8"),
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = resp.read()
        os.makedirs(os.path.dirname(out_wav) or ".", exist_ok=True)
        with open(out_wav, "wb") as fh:
            fh.write(data)
        return os.path.getsize(out_wav) > 0
    except Exception:
        return False


def synthesize(text: str, lang: str, engine: str, profile_name: str, out_wav: str,
               rate: float = 1.0, pitch: int = 0, volume: float = 1.0):
    """Ein Segment sprechen. Gibt (engine, ok, word_boundaries) zurück."""
    L = "en" if lang == "en" else "de"
    voice = VOICE_PROFILES.get(profile_name, VOICE_PROFILES["natural"]).get(L)
    if engine == "edge" and edge_available():
        ok, boundaries = synth_edge(text, L, voice, rate, pitch, volume, out_wav)
        if ok:
            return "edge", True, boundaries
    if engine == "piper" and piper_available():
        if synth_piper(text, PIPER_VOICES[L], out_wav):
            return "piper", True, []
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

    # Aussprache EN
    check("EN: $ → dollars", normalize_speech("Save $1,200", "en") == "Save 1,200 dollars")
    check("EN: % → percent", normalize_speech("about 20%", "en") == "about 20 percent")
    check("EN: e.g.", normalize_speech("e.g. gas", "en") == "for example gas")
    check("EN: Datum (MM/TT)", normalize_speech("on 02/01/2006", "en") == "on 1. February 2006")
    check("EN: % ohne Leerzeichen", normalize_speech("about 20%", "en") == "about 20 percent")
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

    # Stimmen
    check("Stimmen: DE männlich gesetzt", "Neural" in VOICE_PROFILES["natural"]["de"])
    check("Stimmen: EN männlich gesetzt", "Neural" in VOICE_PROFILES["natural"]["en"])
    check("Stimmen: beide Profile DE+EN",
          all(set(v.keys()) >= {"de", "en"} for v in VOICE_PROFILES.values()))
    check("Piper: DE+EN gesetzt", set(PIPER_VOICES.keys()) == {"de", "en"})

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
    for profile, voices in VOICE_PROFILES.items():
        print("  Profil %-9s DE %-34s EN %s" % (profile, voices["de"], voices["en"]))
    print("Selbsttest: python3 scripts/ff_voice_backends.py --selftest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
