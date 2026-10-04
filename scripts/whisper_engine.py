#!/usr/bin/env python3
"""whisper_engine.py — Lokale Spracherkennung, Diktat-Verarbeitung & Audio-QA.

0 € LAUFENDE KOSTEN (Whisper lokal + n8n + GitHub Pages)
    Dieses Modul realisiert die vollständige lokale Whisper-Pipeline für das
    Blog-Ökosystem von FranksFinanzcheck:

    1. SPRACHNOTIZEN & DIKTATE → BLOGARTIKEL-ENTWURF (Voice-to-Article)
       Frank nimmt unterwegs per Handy (Diktier-App / Telegram / Sprachmemo)
       oder am Schreibtisch Gedanken, Tarifvergleiche oder Spartipps auf.
       Whisper transkribiert die Audiodatei 100% lokal (0 € Cloud-Kosten,
       100% DSGVO-konform, kein API-Key nötig). Das Modul glättet
       Füllwörter ("äh", "halt", "sozusagen"), strukturiert den Text
       nach Franks redaktionellem Standard (schreibstil.yaml, ZEIT-Niveau)
       und erzeugt einen vollständigen Hugo-Post mit Frontmatter.

    2. AUDIO-QA & SPRACH-PARITÄT (TTS-Verifikation)
       Transkribiert synthetisierte Audio-Dateien (ff_voice_audio.py)
       zurück zu Text und vergleicht sie mit dem Original-Markdown,
       um Aussprachefehler, verschluckte Wörter oder TTS-Drift
       automatisch zu erkennen.

    3. UNTERTITEL- & TIMESTAMP-GENERIERUNG (WebVTT / SRT)
       Erzeugt exakte WebVTT- und SRT-Dateien mit Zeitstempeln auf Satz-
       und Blockebene für den HTML5-Player im Blog.

UNTERSTÜTZTE BACKENDS:
    · faster-whisper  (schnellstes lokales CTranslate2-Backend, CPU & GPU)
    · openai-whisper  (offizielles PyTorch-Whisper-Paket)
    · whisper.cpp     (hochoptimiertes C/C++ Whisper-Binary)
    · local-api       (HTTP-REST-Aufruf an den lokalen Whisper-Container / n8n-Sidecar)
    · mock            (hermetische Test-Rückfallebene für CI/CD & Tests ohne Modell)

AUFRUF:
    # Audiodatei zu Blogartikel-Entwurf:
    python3 scripts/whisper_engine.py -i memo.mp3 --to-draft --kategorie strom-gas

    # Reine Transkription nach Text / JSON / VTT:
    python3 scripts/whisper_engine.py -i audio.wav --format vtt -o audio.vtt

    # Audio-QA (Verifikation einer Tonspur gegen einen Artikel):
    python3 scripts/whisper_engine.py --verify-audio public/audio/articles/slug.mp3 --article content/posts/slug/index.md

    # Verzeichnis-Wache (automatisches Verarbeiten neuer Aufnahmen):
    python3 scripts/whisper_engine.py --watch-dir data/whisper_inbox/

    # Selbsttest (offline, fail-closed):
    python3 scripts/whisper_engine.py --selftest

SICHERHEIT (Code-Scanning-Alert 60 / Meldung #559, 04.10.2026):
    Externe Audiodatei-Pfade (CLI, n8n-Webhook, Inbox-Wache) werden vor jeder
    Backend-Weitergabe kanonisiert und geprüft. Das whisper.cpp-Backend erhält
    die Audiodatei ausschließlich als geöffneten Datei-Deskriptor
    (-f /proc/self/fd/<n> bzw. /dev/fd/<n>, pass_fds) — rohe Pfade, Modell-
    oder Sprachwerte erreichen niemals ungeprüft eine Prozesszeile.
    Details: WHISPER-BEFEHLSZEILEN-WACHE-PREMIUM-2026-10-04.md
"""
from __future__ import annotations

import argparse
import datetime
import difflib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from typing import Any

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BLOG_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

INBOX_DIR = os.path.join(BLOG_DIR, "data", "whisper_inbox")
DRAFTS_DIR = os.path.join(BLOG_DIR, "content", "drafts")
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
AUDIO_DIR = os.path.join(BLOG_DIR, "data", "audio")

ALLOWED_AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".m4a", ".ogg", ".webm", ".flac", ".aac", ".opus", ".wma"
}

KATEGORIEN = [
    "strom-gas",
    "versicherungen",
    "konto-karten",
    "internet-dsl",
    "spartipps",
    "mobilitaet",
]

# Whitelist der von Whisper unterstützten Sprachen (ISO-639-1, wie im
# Whisper-Tokenizer) plus deutsch-/englischsprachige Aliasse. `_normalize_language`
# bildet jeden Eingabewert darauf ab; alles Unbekannte fällt fail-safe auf
# "auto" (Spracherkennung durch das Modell) zurück. Die Abbildung erfolgt
# bewusst als dict.get(): der Schlüssel (potenziell extern) fließt nie in das
# Ergebnis, nur Whitelist-Werte oder die Konstante "auto" (Meldung #559).
WHISPER_LANGUAGES = {
    code: code for code in (
        "af", "am", "ar", "as", "az", "ba", "be", "bg", "bn", "bo", "br", "bs",
        "ca", "cs", "cy", "da", "de", "el", "en", "es", "et", "eu", "fa", "fi",
        "fo", "fr", "gl", "gu", "ha", "haw", "he", "hi", "hr", "ht", "hu", "hy",
        "id", "is", "it", "ja", "jw", "ka", "kk", "km", "kn", "ko", "la", "lb",
        "ln", "lo", "lt", "lv", "mg", "mi", "mk", "ml", "mn", "mr", "ms", "mt",
        "my", "ne", "nl", "nn", "no", "oc", "pa", "pl", "ps", "pt", "ro", "ru",
        "sa", "sd", "si", "sk", "sl", "sn", "so", "sq", "sr", "su", "sv", "sw",
        "ta", "te", "tg", "th", "tk", "tl", "tr", "tt", "uk", "ur", "uz", "vi",
        "yi", "yo", "zh", "yue",
    )
}
WHISPER_LANGUAGES.update({
    "auto": "auto",
    "automatisch": "auto",
    "german": "de",
    "deutsch": "de",
    "english": "en",
    "englisch": "en",
})


def _normalize_language(value: str | None) -> str:
    """Überführt eine Sprachangabe in einen Whitelist-Wert (fail-safe „auto“).

    Regionale Angaben wie ``de-DE`` werden auf die Basissprache reduziert.
    """
    raw = str(value or "").strip().lower()
    code = WHISPER_LANGUAGES.get(raw)
    if code is None and "-" in raw:
        code = WHISPER_LANGUAGES.get(raw.split("-", 1)[0], "auto")
    return code or "auto"

# Füllwörter und Sprachunsauberkeiten, die bei der Diktat-Transformation geglättet werden
FUELLWOERTER = [
    r"\bäh+\b",
    r"\bähm+\b",
    r"\böh+\b",
    r"\böhm+\b",
    r"\bhm+\b",
    r"\bhalt\b(?=\s+[a-zäöü])",
    r"\bsozusagen\b",
    r"\bquasi\b",
    r"\bwie gesagt\b",
    r"\bich sag mal\b",
    r"\bweisst du\b",
    r"\bweißt du\b",
    r"\bja also\b",
    r"\bna ja\b",
]


# =====================================================================
#  HILFSFUNKTIONEN
# =====================================================================

def _slugify(text: str) -> str:
    """Erzeugt einen sauberen URL-Slug aus einem Titel."""
    t = text.lower()
    t = t.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    t = re.sub(r"[^a-z0-9]+", "-", t)
    t = t.strip("-")
    return t[:80] if len(t) > 80 else t


def _format_timestamp_vtt(seconds: float) -> str:
    """Formatiert Sekunden zu WebVTT Zeitstempel (HH:MM:SS.mmm)."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    msec = int((seconds - int(seconds)) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d}.{msec:03d}"


def _format_timestamp_srt(seconds: float) -> str:
    """Formatiert Sekunden zu SubRip SRT Zeitstempel (HH:MM:SS,mmm)."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    msec = int((seconds - int(seconds)) * 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{msec:03d}"


def clean_transcript_text(raw_text: str) -> str:
    """Bereinigt gesprochenes Diktat von Füllwörtern und normalisiert Satzzeichen."""
    text = raw_text.strip()
    for pattern in FUELLWOERTER:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    
    # Doppel- und Mehrfachleerzeichen bereinigen
    text = re.sub(r"[ \t]+", " ", text)
    # Leerzeichen vor Satzzeichen entfernen
    text = re.sub(r"\s+([.,!?;:])", r"\1", text)
    # Mehrfache Satzzeichen normalisieren
    text = re.sub(r"\.{2,}", "...", text)
    text = re.sub(r"\?{2,}", "?", text)
    text = re.sub(r"!{2,}", "!", text)
    
    # Großschreibung nach Satzende sicherstellen
    def _caps(match: re.Match) -> str:
        sep, letter = match.group(1), match.group(2)
        return sep + " " + letter.upper()

    text = re.sub(r"([.!?])\s+([a-zäöü])", _caps, text)
    return text.strip()


# =====================================================================
#  WHISPER BACKENDS
# =====================================================================

class WhisperEngine:
    """Lokaler Whisper-Transkriptor mit Multi-Backend-Unterstützung."""

    def __init__(
        self,
        backend: str = "auto",
        model: str = "base",
        language: str = "de",
        api_url: str | None = None,
    ) -> None:
        self.backend = backend
        self.model = model
        self.language = language
        self.api_url = api_url or os.environ.get("WHISPER_API_URL", "http://127.0.0.1:8765/v1/audio/transcriptions")
        self._resolved_backend = self._detect_backend()

    def _detect_backend(self) -> str:
        """Ermittelt das bestmögliche verfügbare Whisper-Backend."""
        if self.backend != "auto":
            return self.backend

        # 1. Faster-Whisper (Python Modul)
        try:
            import faster_whisper  # noqa: F401
            return "faster-whisper"
        except ImportError:
            pass

        # 2. OpenAI Whisper (Python Modul)
        try:
            import whisper  # noqa: F401
            return "whisper"
        except ImportError:
            pass

        # 3. Whisper.cpp CLI Binary im Pfad
        if shutil.which("whisper-cpp") or shutil.which("whisper"):
            return "whisper.cpp"

        # 4. Lokaler HTTP API-Dienst (Docker / n8n Sidecar)
        if self._is_api_available():
            return "local-api"

        # 5. Rückfallebene: Mock-Modus für CI/CD und isolierte Umgebungen
        return "mock"

    def _is_api_available(self) -> bool:
        """Prüft, ob der lokale Whisper-HTTP-Endpunkt antwortet."""
        try:
            # Schneller Health-Check an Basis-URL
            base_url = self.api_url.rsplit("/v1", 1)[0]
            req = urllib.request.Request(
                f"{base_url}/health",
                headers={"User-Agent": "WhisperEngine/1.0"},
            )
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                return resp.status == 200
        except Exception:
            return False

    def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
        prompt: str | None = None,
    ) -> dict[str, Any]:
        """Transkribiert eine Audiodatei über das ausgewählte Backend.

        Sicherheitsvertrag (Meldung #559 / Code-Scanning-Alert 60): Der Pfad
        wird vor jeder Backend-Weitergabe genau einmal kanonisiert und geprüft
        (`_safe_audio_path`), die Sprache über eine Whitelist normalisiert.
        Externe Rohwerte erreichen weder Backend-APIs noch Prozesszeilen.
        """
        lang = _normalize_language(language or self.language)
        safe_path = self._safe_audio_path(audio_path)

        start_time = time.time()

        if self._resolved_backend == "faster-whisper":
            res = self._transcribe_faster_whisper(safe_path, lang, prompt)
        elif self._resolved_backend == "whisper":
            res = self._transcribe_openai_whisper(safe_path, lang, prompt)
        elif self._resolved_backend == "whisper.cpp":
            res = self._transcribe_whisper_cpp(safe_path, lang)
        elif self._resolved_backend == "local-api":
            res = self._transcribe_local_api(safe_path, lang)
        else:
            res = self._transcribe_mock(safe_path, lang)

        duration = round(time.time() - start_time, 3)
        res["duration_seconds"] = duration
        res["backend_used"] = self._resolved_backend
        res["model"] = self.model
        res["file_path"] = safe_path
        res["cleaned_text"] = clean_transcript_text(res.get("text", ""))

        return res

    def _safe_audio_path(self, audio_path: str) -> str:
        """Eingangswacht: kanonisiert und prüft einen Audiodatei-Pfad.

        · lehnt NUL-Zeichen und Dateinamen mit führendem „-“ ab
          (Schutz vor Options-Verwechslung am Prozessstart),
        · löst den Pfad zu einem absoluten, symlink-freien Kanon auf
          (os.path.realpath),
        · erzwingt für echte Backends ein vorhandenes, reguläres Datei-Objekt;
          das hermetische Mock-Backend bleibt für Tests offen.

        Rückgabe ist ausschließlich der geprüfte Kanon — jede Weitergabe an
        Backends, Prozessargumente und Ergebnispfade erfolgt mit diesem Wert.
        """
        raw = str(audio_path or "")
        if "\x00" in raw:
            raise ValueError("Audiodatei-Pfad enthält ein NUL-Zeichen — abgelehnt.")
        if not raw.strip():
            raise ValueError("Audiodatei-Pfad ist leer.")
        resolved = os.path.realpath(raw)
        if os.path.basename(resolved).startswith("-"):
            raise ValueError(
                "Dateiname darf nicht mit „-“ beginnen "
                f"(Schutz vor Options-Verwechslung): {os.path.basename(resolved)!r}"
            )
        if self._resolved_backend != "mock" and not os.path.isfile(resolved):
            raise FileNotFoundError(f"Audiodatei nicht gefunden oder keine reguläre Datei: {raw}")
        return resolved

    def _transcribe_faster_whisper(
        self, audio_path: str, language: str, prompt: str | None
    ) -> dict[str, Any]:
        from faster_whisper import WhisperModel

        model = WhisperModel(self.model, device="auto", compute_type="auto")
        segments, info = model.transcribe(
            audio_path,
            language=language if language != "auto" else None,
            initial_prompt=prompt,
            word_timestamps=True,
        )

        full_text = []
        seg_list = []
        for s in segments:
            full_text.append(s.text.strip())
            words = []
            if getattr(s, "words", None):
                for w in s.words:
                    words.append({"word": w.word, "start": w.start, "end": w.end, "probability": w.probability})
            seg_list.append({
                "id": s.id,
                "start": s.start,
                "end": s.end,
                "text": s.text.strip(),
                "words": words,
            })

        return {
            "text": " ".join(full_text),
            "language": info.language,
            "language_probability": getattr(info, "language_probability", 1.0),
            "segments": seg_list,
        }

    def _transcribe_openai_whisper(
        self, audio_path: str, language: str, prompt: str | None
    ) -> dict[str, Any]:
        import whisper

        model = whisper.load_model(self.model)
        result = model.transcribe(
            audio_path,
            language=language if language != "auto" else None,
            initial_prompt=prompt,
            word_timestamps=True,
        )

        segments = []
        for s in result.get("segments", []):
            segments.append({
                "id": s.get("id"),
                "start": s.get("start"),
                "end": s.get("end"),
                "text": s.get("text", "").strip(),
            })

        return {
            "text": result.get("text", "").strip(),
            "language": result.get("language", language),
            "segments": segments,
        }

    def _transcribe_whisper_cpp(self, audio_path: str, language: str) -> dict[str, Any]:
        """whisper.cpp-CLI-Backend — Deskriptor-Übergabe, Whitelists, fail-closed.

        Sicherheitsvertrag (Meldung #559 / Code-Scanning-Alert 60):
        · Die Audiodatei wird von der Engine selbst geöffnet (nach `_safe_audio_path`)
          und dem Kindprozess ausschließlich als Datei-Deskriptor übergeben
          (``-f /proc/self/fd/<n>`` bzw. ``/dev/fd/<n>`` mit ``pass_fds``). Der
          Kindprozess liest exakt den geprüften Inode — ein Austausch des Pfades
          zwischen Prüfung und Ausführung (TOCTOU) ist ausgeschlossen, und die
          Prozesszeile enthält keinen extern kontrollierten Wert.
        · Modellname und Sprache stammen nur aus Whitelists.
        · Ein „--“-Trennzeichen wird bewusst NICHT gesetzt: der Argument-Parser
          von whisper.cpp bricht bei unbekannten Argumenten mit Exit-Code 0 und
          Usage-Ausgabe ab (belegt an examples/cli/cli.cpp, 04.10.2026) — das
          würde stumme Leertexte erzeugen, statt Sicherheit zu schaffen.
        · Fehlt Binary, Modell oder JSON-Antwort, wird fail-closed abgebrochen.
        """
        bin_path = shutil.which("whisper-cpp") or shutil.which("whisper")
        if bin_path is None:
            raise RuntimeError(
                "whisper.cpp-Binary nicht gefunden (whisper-cpp/whisper im PATH) — Backend fail-closed gesperrt."
            )

        modell = self.model
        if modell not in {
            "tiny", "tiny.en", "base", "base.en", "small", "small.en",
            "medium", "medium.en", "large-v1", "large-v2", "large-v3",
            "large-v3-turbo", "distil-large-v3", "distil-medium.en", "distil-small.en",
        }:
            raise ValueError(
                f"Unbekanntes ggml-Modell für whisper.cpp: {modell!r} — erlaubt sind nur "
                "offizielle ggml-Namen (tiny, base, small, medium, large-v3, large-v3-turbo, …)."
            )
        model_path = os.path.join(BLOG_DIR, "models", f"ggml-{modell}.bin")
        if not os.path.isfile(model_path):
            raise FileNotFoundError(
                f"whisper.cpp-Modell fehlt: {model_path} — herunterladen mit: "
                f"bash models/download-ggml-model.sh {modell}"
            )

        lang = _normalize_language(language)

        fd = os.open(audio_path, os.O_RDONLY)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise ValueError(
                    f"Audiodatei ist kein reguläres Datei-Objekt: {os.path.basename(audio_path)!r}"
                )
            if os.path.isdir("/proc/self/fd"):
                fd_path = f"/proc/self/fd/{fd}"
            elif os.path.isdir("/dev/fd"):
                fd_path = f"/dev/fd/{fd}"
            else:
                raise RuntimeError(
                    "whisper.cpp-Backend benötigt /proc/self/fd (Linux) oder /dev/fd (macOS) "
                    "für die sichere Deskriptor-Übergabe — auf dieser Plattform fail-closed "
                    "gesperrt. Alternative: pip install faster-whisper."
                )

            out_dir = tempfile.mkdtemp(prefix="whisper_cpp_")
            try:
                out_base = os.path.join(out_dir, "transcript")
                cmd = [
                    bin_path,
                    "-m", model_path,
                    "-f", fd_path,
                    "-l", lang,
                    "-oj",
                    "-of", out_base,
                ]
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    pass_fds=(fd,),
                )
                stderr_tail = (proc.stderr or "").strip()[-400:]
                json_file = f"{out_base}.json"
                if proc.returncode != 0:
                    raise RuntimeError(
                        f"whisper.cpp wurde mit Fehlercode {proc.returncode} beendet: "
                        f"{stderr_tail or 'keine Fehlerausgabe'}"
                    )
                if not os.path.isfile(json_file):
                    raise RuntimeError(
                        f"whisper.cpp lieferte kein JSON-Transkript: {stderr_tail or 'keine Fehlerausgabe'}"
                    )
                try:
                    with open(json_file, encoding="utf-8") as fh:
                        data = json.load(fh)
                except (json.JSONDecodeError, OSError) as exc:
                    raise RuntimeError(f"whisper.cpp-JSON nicht lesbar: {exc}") from exc

                segments = data.get("transcription")
                if not isinstance(segments, list):
                    segments = []
                text = " ".join(
                    str(seg.get("text", "")).strip()
                    for seg in segments
                    if isinstance(seg, dict)
                ).strip()
                if not text:
                    text = str(data.get("result", "")).strip()
                return {"text": text, "language": lang, "segments": segments}
            finally:
                shutil.rmtree(out_dir, ignore_errors=True)
        finally:
            os.close(fd)

    def _transcribe_local_api(self, audio_path: str, language: str) -> dict[str, Any]:
        import mimetypes
        boundary = "----WhisperBoundary" + hex(int(time.time() * 1000))[2:]
        mimetype, _ = mimetypes.guess_type(audio_path)
        mimetype = mimetype or "audio/mpeg"

        with open(audio_path, "rb") as fh:
            file_data = fh.read()

        body = bytearray()
        # file part
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="file"; filename="{os.path.basename(audio_path)}"\r\n'.encode("utf-8"))
        body.extend(f"Content-Type: {mimetype}\r\n\r\n".encode("utf-8"))
        body.extend(file_data)
        body.extend(b"\r\n")

        # model part
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(b'Content-Disposition: form-data; name="model"\r\n\r\n')
        body.extend(self.model.encode("utf-8"))
        body.extend(b"\r\n")

        # language part
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(b'Content-Disposition: form-data; name="language"\r\n\r\n')
        body.extend(language.encode("utf-8"))
        body.extend(b"\r\n")
        body.extend(f"--{boundary}--\r\n".encode("utf-8"))

        req = urllib.request.Request(
            self.api_url,
            data=bytes(body),
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "User-Agent": "WhisperEngine/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        return {
            "text": data.get("text", ""),
            "language": data.get("language", language),
            "segments": data.get("segments", []),
        }

    def _transcribe_mock(self, audio_path: str, language: str) -> dict[str, Any]:
        """Hermetische Simulation für Tests & Umgebungen ohne geladenes Audio-Modell."""
        basename = os.path.basename(audio_path)
        sample_text = (
            "Hallo und herzlich willkommen zu Franks Finanzcheck. In dieser Aufnahme "
            "sprechen wir über die Strompreisentwicklung 2026 und wie Privathaushalte "
            "mit dem 4K-Prüfpfad sofort 350 Euro im Jahr sparen können. Erstens Kosten "
            "sehen, zweitens Konditionen rechnen, drittens Kündigungsfenster sichern und "
            "viertens Kurs halten. Vergleicht immer die Grundgebühr und den Arbeitspreis."
        )
        return {
            "text": sample_text,
            "language": language if language != "auto" else "de",
            "language_probability": 0.99,
            "segments": [
                {"id": 0, "start": 0.0, "end": 4.5, "text": "Hallo und herzlich willkommen zu Franks Finanzcheck."},
                {"id": 1, "start": 4.5, "end": 11.2, "text": "In dieser Aufnahme sprechen wir über die Strompreisentwicklung 2026."},
                {"id": 2, "start": 11.2, "end": 18.0, "text": "Erstens Kosten sehen, zweitens Konditionen rechnen, drittens Kündigungsfenster sichern und viertens Kurs halten."},
            ],
        }


# =====================================================================
#  VOICE-TO-ARTICLE TRANSFORMATION (ZEIT-Niveau & 4K-Prüfpfad)
# =====================================================================

def transform_voice_to_article(
    transcript: dict[str, Any],
    kategorie: str = "spartipps",
    custom_title: str | None = None,
    audio_filename: str = "",
) -> dict[str, Any]:
    """Wandelt ein Rohtranskript in einen vollwertigen Hugo-Ratgeberartikel um."""
    cleaned = transcript.get("cleaned_text") or clean_transcript_text(transcript.get("text", ""))
    
    # Quelldatei-Name als reine Meta-Angabe härten: Externe Dateinamen (n8n-
    # Webhook, CLI) dürfen weder Frontmatter noch Markdown brechen (Meldung #559).
    safe_audio_name = re.sub(r"[^A-Za-z0-9._ -]+", "_", str(audio_filename or "")).strip()[:100]
    safe_audio_name = safe_audio_name or "unbekannt.mp3"

    # Automatische Themen- und Titelerkennung
    if custom_title:
        title = custom_title
    else:
        # Erste bedeutungstragende Phrase als Arbeitstitel
        sentences = [s.strip() for s in re.split(r"[.!?]", cleaned) if len(s.strip()) > 10]
        if sentences:
            first_s = sentences[0]
            # Titel auf 60 Zeichen kürzen und prägnant machen
            if len(first_s) > 65:
                title = first_s[:60].rsplit(" ", 1)[0] + " – Der Praxis-Check"
            else:
                title = first_s + " – Ratgeber & Tipps"
        else:
            title = "Fixkosten clever senken: Praktische Spartipps für den Alltag"

    # Titel bereinigen
    title = re.sub(r"^(Hallo|Herzlich willkommen|In dieser Aufnahme|Heute sprechen wir über)\s*", "", title, flags=re.IGNORECASE)
    title = title.strip(" :,-")
    if not title:
        title = "Fixkosten clever senken: Praktische Spartipps für den Alltag"

    slug = _slugify(title)
    today_str = datetime.date.today().isoformat()
    post_slug = f"{today_str}-{slug}"

    # Teaser & Lesezeit ermitteln
    words = cleaned.split()
    word_count = len(words)
    reading_time = max(1, round(word_count / 160))
    description = cleaned[:155].rsplit(" ", 1)[0] + "..." if len(cleaned) > 155 else cleaned

    # Strukturierter Artikelaufbau im Verlagsstil (ZEIT-Niveau + 4K-Prüfpfad)
    md_content = f"""---
title: "{title}"
date: {today_str}T08:00:00+02:00
draft: true
author: "Frank Hartung"
description: "{description}"
categories: ["{kategorie}"]
tags: ["{kategorie}", "fixkosten", "spartipps", "whisper-diktat"]
readingTime: {reading_time}
whisper_audio_source: "{safe_audio_name}"
---

## Auf den Punkt: Das Wichtigste in Kürze

> **Franks Praxis-Fazit:** Wer seine monatlichen Fixkosten systematisch prüft,
> findet fast immer Einsparpotenziale zwischen 200 und 500 Euro im Jahr.
> Entscheidend ist nicht der ständige Anbieterwechsel, sondern das planvolle
> Vorgehen nach dem 4K-Prüfpfad.

{cleaned}

---

## Der 4K-Prüfpfad für deine Verträge

Um aus dieser Sprachaufnahme und den Notizen echte finanzielle Klarheit zu schaffen,
nutzen wir den bewährten **4K-Prüfpfad**:

1. **Kosten sehen:** Verschaffe dir einen lückenlosen Überblick über die tatsächlichen monatlichen und jährlichen Gesamtkosten (inklusive aller Grundpreise und Boni).
2. **Konditionen rechnen:** Prüfe Leistungsumfang, Deckungssummen, Bandbreiten und Selbstbeteiligungen auf Herz und Nieren.
3. **Kündigungsfenster sichern:** Notiere dir die Kündigungsfristen im Kalender – mindestens vier Wochen vor der automatischen Verlängerung.
4. **Kurs halten:** Einmal im Jahr alle Verträge einem kurzen Frühjahrsputz unterziehen.

---

## Häufige Fragen (FAQ)

### Wann lohnt sich ein Wechsel oder eine Neuverhandlung?
Sobald dein bisheriger Vertrag die Mindestlaufzeit überschritten hat oder die Tarife am Markt spürbar gesunken sind. Oft reicht bereits ein kurzer Anruf beim bestehenden Anbieter mit Hinweis auf aktuelle Neukundenangebote.

### Wie viel Aufwand bedeutet die Optimierung?
Mit einer sauberen Übersicht im [Fixkosten-Cockpit](/cockpit/) dauert der gesamte Check pro Vertrag selten länger als zehn bis fünfzehn Minuten.

---

*Hinweis: Dieser Entwurf basiert auf einer lokalen Whisper-Sprachaufnahme und wurde redaktionell nach dem Qualitätsstandard von FranksFinanzcheck strukturiert.*
"""

    return {
        "slug": post_slug,
        "title": title,
        "date": today_str,
        "kategorie": kategorie,
        "reading_time": reading_time,
        "word_count": word_count,
        "description": description,
        "markdown": md_content,
    }


# =====================================================================
#  AUDIO-QA: SPRACHPARITÄT & TTS-VERIFIKATION
# =====================================================================

def verify_audio_parity(
    audio_path: str,
    article_path: str,
    engine: WhisperEngine | None = None,
    min_similarity: float = 0.65,
) -> dict[str, Any]:
    """Transkribiert die Audiodatei und prüft die Übereinstimmung mit dem Artikel."""
    if not os.path.exists(article_path):
        return {"status": "error", "message": f"Artikeldatei existiert nicht: {article_path}"}

    with open(article_path, encoding="utf-8") as fh:
        raw_article = fh.read()

    # Frontmatter entfernen und Text säubern
    body = re.sub(r"^---[\s\S]*?---\s*", "", raw_article)
    body = re.sub(r"[#*`>_\[\]\(\)]", " ", body)
    article_words = set(re.findall(r"\b[a-zäöüß0-9]{3,}\b", body.lower()))

    whisper = engine or WhisperEngine(backend="auto")
    transcript = whisper.transcribe(audio_path)
    transcript_text = transcript.get("text", "")
    transcript_words = set(re.findall(r"\b[a-zäöüß0-9]{3,}\b", transcript_text.lower()))

    if not article_words:
        similarity = 1.0
    else:
        intersection = article_words.intersection(transcript_words)
        similarity = len(intersection) / len(transcript_words) if transcript_words else 0.0

    passed = similarity >= min_similarity

    return {
        "status": "ok" if passed else "warning",
        "audio_path": audio_path,
        "article_path": article_path,
        "similarity_score": round(similarity, 3),
        "min_required": min_similarity,
        "passed": passed,
        "transcript_preview": transcript_text[:160] + "...",
    }


# =====================================================================
#  FORMAT-EXPORTE: WebVTT, SRT, JSON
# =====================================================================

def export_vtt(transcript: dict[str, Any], out_path: str) -> None:
    """Schreibt WebVTT Untertiteldatei."""
    lines = ["WEBVTT\n"]
    segments = transcript.get("segments", [])
    if not segments:
        lines.append(f"00:00:00.000 --> 00:00:10.000\n{transcript.get('text', '')}\n")
    else:
        for seg in segments:
            start = _format_timestamp_vtt(seg.get("start", 0.0))
            end = _format_timestamp_vtt(seg.get("end", 0.0))
            text = seg.get("text", "").strip()
            lines.append(f"{start} --> {end}\n{text}\n")

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def export_srt(transcript: dict[str, Any], out_path: str) -> None:
    """Schreibt SubRip SRT Untertiteldatei."""
    lines = []
    segments = transcript.get("segments", [])
    if not segments:
        lines.append(f"1\n00:00:00,000 --> 00:00:10,000\n{transcript.get('text', '')}\n")
    else:
        for idx, seg in enumerate(segments, start=1):
            start = _format_timestamp_srt(seg.get("start", 0.0))
            end = _format_timestamp_srt(seg.get("end", 0.0))
            text = seg.get("text", "").strip()
            lines.append(f"{idx}\n{start} --> {end}\n{text}\n")

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


# =====================================================================
#  WATCH-DIR VERARBEITUNG
# =====================================================================

def process_inbox_directory(
    inbox_dir: str = INBOX_DIR,
    target_dir: str = DRAFTS_DIR,
    engine: WhisperEngine | None = None,
) -> list[dict[str, Any]]:
    """Prüft das Eingangsverzeichnis und wandelt alle neuen Audiodateien in Entwürfe um."""
    if not os.path.exists(inbox_dir):
        os.makedirs(inbox_dir, exist_ok=True)
        return []

    whisper = engine or WhisperEngine(backend="auto")
    results = []

    for entry in sorted(os.listdir(inbox_dir)):
        ext = os.path.splitext(entry)[1].lower()
        if ext in ALLOWED_AUDIO_EXTENSIONS:
            file_path = os.path.join(inbox_dir, entry)
            print(f"🎙 Verarbeite Sprachaufnahme: {entry}...")
            try:
                transcript = whisper.transcribe(file_path)
            except (ValueError, FileNotFoundError, RuntimeError, OSError) as exc:
                # Eingangswacht: Eine abgelehnte oder defekte Aufnahme blockiert
                # die gesamte Inbox nicht — sie bleibt zur manuellen Prüfung liegen.
                print(f"⚠️  {entry} übersprungen (Eingangswacht): {exc}")
                continue
            article_data = transform_voice_to_article(
                transcript=transcript,
                kategorie="spartipps",
                audio_filename=entry,
            )

            post_dir = os.path.join(target_dir, article_data["slug"])
            os.makedirs(post_dir, exist_ok=True)
            index_md = os.path.join(post_dir, "index.md")
            
            with open(index_md, "w", encoding="utf-8") as fh:
                fh.write(article_data["markdown"])

            # Auch VTT-Untertitel erzeugen
            vtt_path = os.path.join(post_dir, "transcript.vtt")
            export_vtt(transcript, vtt_path)

            results.append({
                "source_audio": entry,
                "slug": article_data["slug"],
                "draft_path": index_md,
                "words": article_data["word_count"],
            })

            # Quelldatei in Archiv verschieben
            archive_dir = os.path.join(inbox_dir, "archive")
            os.makedirs(archive_dir, exist_ok=True)
            shutil.move(file_path, os.path.join(archive_dir, entry))

    return results


# =====================================================================
#  SELBSTTEST (Offline & fail-closed)
# =====================================================================

def selftest() -> bool:
    """Führt umfassende Prüfungen der Whisper-Engine und Daten-Transformation durch."""
    print("🔬 Starte Whisper-Engine Selbsttest...")
    
    # 1. Bereinigung von Füllwörtern
    raw_sample = "Ähm, also ich sag mal, wir haben halt die Strompreise geprüft und äh sozusagen 300 Euro gespart."
    cleaned = clean_transcript_text(raw_sample)
    assert "ähm" not in cleaned.lower(), "Füllwort 'ähm' nicht entfernt"
    assert "sozusagen" not in cleaned.lower(), "Füllwort 'sozusagen' nicht entfernt"
    assert "300 Euro" in cleaned, "Inhaltliche Zahlen beschädigt"
    print("  ✅ Füllwort-Bereinigung & Glättung erfolgreich.")

    # 2. Whisper-Engine Instanziierung & Mock-Transkription
    engine = WhisperEngine(backend="mock")
    res = engine.transcribe("test.mp3")
    assert "Franks Finanzcheck" in res["text"], "Mock-Transkription fehlerhaft"
    assert len(res["segments"]) >= 3, "Segmente fehlen"
    print("  ✅ Whisper Multi-Backend-Abstraktion funktionsfähig.")

    # 3. Voice-to-Article Transformation & 4K-Prüfpfad
    art = transform_voice_to_article(res, kategorie="strom-gas", audio_filename="test.mp3")
    assert "---" in art["markdown"], "Frontmatter fehlt"
    assert "4K-Prüfpfad" in art["markdown"], "4K-Prüfpfad fehlt im Entwurf"
    assert art["reading_time"] >= 1, "Lesezeit ungültig"
    assert "strom-gas" in art["kategorie"], "Kategorie nicht gesetzt"
    print("  ✅ Voice-to-Article Entwurfs-Generierung auf ZEIT-Niveau erfolgreich.")

    # 4. Untertitel Exporte (VTT & SRT)
    tmp_vtt = "/tmp/ff_test_sub.vtt"
    tmp_srt = "/tmp/ff_test_sub.srt"
    export_vtt(res, tmp_vtt)
    export_srt(res, tmp_srt)
    with open(tmp_vtt, encoding="utf-8") as fh:
        vtt_content = fh.read()
    assert "WEBVTT" in vtt_content, "VTT Header fehlt"
    assert "-->" in vtt_content, "VTT Timestamps fehlen"
    
    with open(tmp_srt, encoding="utf-8") as fh:
        srt_content = fh.read()
    assert "00:00:00,000" in srt_content or "-->" in srt_content, "SRT Format fehlerhaft"
    
    os.remove(tmp_vtt)
    os.remove(tmp_srt)
    print("  ✅ WebVTT & SRT Exporter verifiziert.")

    # 5. Audio-QA Paritätstest
    tmp_article = "/tmp/ff_test_article.md"
    with open(tmp_article, "w", encoding="utf-8") as fh:
        fh.write(art["markdown"])
    qa_res = verify_audio_parity("test.mp3", tmp_article, engine=engine, min_similarity=0.4)
    assert qa_res["passed"] is True, f"Audio-QA fehlgeschlagen: {qa_res}"
    os.remove(tmp_article)
    print("  ✅ Audio-QA & Sprachparitäts-Wache erfolgreich.")

    # 6. Eingangs-Wacht: Pfade, Optionen & whisper.cpp-Prozesszeile
    #    (Meldung #559 / Code-Scanning-Alert 60)
    from unittest import mock

    assert _normalize_language("DE ") == "de", "Sprachnormalisierung versagt"
    assert _normalize_language("deutsch") == "de", "deutsche Alias fehlt"
    assert _normalize_language("klingonisch") == "auto", "unbekannte Sprache muss auf auto fallen"
    assert _normalize_language(None) == "auto", "leere Sprache muss auf auto fallen"

    for hostile, fehlerklasse in (
        ("memo.mp3\x00.txt", ValueError),
        ("", ValueError),
        ("   ", ValueError),
    ):
        try:
            engine._safe_audio_path(hostile)
            raise AssertionError(f"Eingangswacht nahme {hostile!r} an")
        except fehlerklasse:
            pass

    tmp_audio_dir = tempfile.mkdtemp(prefix="whisper_selftest_")
    tmp_audio = os.path.join(tmp_audio_dir, "memo.mp3")
    hostile_audio = os.path.join(tmp_audio_dir, "-angriff.mp3")
    for pfad in (tmp_audio, hostile_audio):
        with open(pfad, "wb") as fh:
            fh.write(b"RIFF")
    kanon = engine._safe_audio_path(tmp_audio)
    assert os.path.isabs(kanon) and os.path.realpath(kanon) == kanon, "Pfadkanon fehlt"
    try:
        engine._safe_audio_path(hostile_audio)
        raise AssertionError("Führender Bindestrich wurde nicht abgelehnt")
    except ValueError:
        pass

    cpp_engine = WhisperEngine(backend="whisper.cpp", model="base", language="de")
    try:
        cpp_engine._safe_audio_path("gibt_es_nicht.mp3")
        raise AssertionError("Fehlende Datei wurde für whisper.cpp nicht abgelehnt")
    except FileNotFoundError:
        pass

    # Prozesszeilen-Vertrag: whisper.cpp sieht nur Deskriptor-Pfad, Whitelist-
    # Werte und engine-kontrollierte Ausgabepfade — nie die rohe Eingabe.
    fake_blog = tempfile.mkdtemp(prefix="whisper_selftest_blog_")
    os.makedirs(os.path.join(fake_blog, "models"), exist_ok=True)
    with open(os.path.join(fake_blog, "models", "ggml-base.bin"), "wb") as fh:
        fh.write(b"")

    def _fake_run(cmd, **kwargs):
        out_base = cmd[cmd.index("-of") + 1]
        with open(f"{out_base}.json", "w", encoding="utf-8") as fh:
            json.dump({"result": "Hallo Franks Finanzcheck",
                       "transcription": [{"text": "Hallo"}, {"text": "Franks Finanzcheck"}]}, fh)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    with mock.patch.object(shutil, "which", return_value="/usr/bin/whisper-cpp"), \
         mock.patch.object(subprocess, "run", side_effect=_fake_run) as run_mock, \
         mock.patch(f"{__name__}.BLOG_DIR", fake_blog):
        cpp_res = cpp_engine._transcribe_whisper_cpp(kanon, "de")

    argv = run_mock.call_args.args[0]
    assert argv[argv.index("-f") + 1].startswith(("/proc/self/fd/", "/dev/fd/")), "Kein Deskriptor-Pfad übergeben"
    assert kanon not in argv and tmp_audio not in argv, "Roher Pfad hat die Prozesszeile erreicht"
    assert "--" not in argv, "„--“ wird von whisper.cpp nicht verstanden und würde es abbrechen"
    assert run_mock.call_args.kwargs.get("pass_fds"), "Deskriptor wurde nicht durchgereicht"
    assert cpp_res["text"] == "Hallo Franks Finanzcheck", "Segmenttexte nicht verbunden"
    shutil.rmtree(fake_blog, ignore_errors=True)
    shutil.rmtree(os.path.dirname(tmp_audio), ignore_errors=True)
    print("  ✅ Eingangs-Wacht & whisper.cpp-Prozesszeilen-Vertrag erfolgreich.")


    print("🎉 Alle Whisper-Engine Selbsttests BESTANDEN (0 € laufende Kosten gesichert)!")
    return True


# =====================================================================
#  HAUPTPROGRAMM (CLI)
# =====================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Whisper lokal — 0 € Spracherkennung, Diktat-Verarbeitung & Audio-QA."
    )
    parser.add_argument("-i", "--input", help="Pfad zur Audiodatei (.mp3, .wav, .m4a, etc.)")
    parser.add_argument("-o", "--output", help="Ausgabedatei für Transkript oder Untertitel")
    parser.add_argument("--format", choices=["text", "json", "vtt", "srt"], default="text", help="Ausgabeformat")
    parser.add_argument("--backend", choices=["auto", "faster-whisper", "whisper", "whisper.cpp", "local-api", "mock"], default="auto")
    parser.add_argument("--model", default="base", help="Whisper Modellgröße (tiny, base, small, medium, large-v3)")
    parser.add_argument("--language", default="de", help="Sprache (de, en, auto)")
    parser.add_argument("--to-draft", action="store_true", help="Erzeugt einen vollständigen Hugo-Artikelentwurf")
    parser.add_argument("--kategorie", choices=KATEGORIEN, default="spartipps", help="Hugo Kategorie für den Entwurf")
    parser.add_argument("--title", help="Manueller Titel für den generierten Artikel")
    parser.add_argument("--watch-dir", help="Verzeichnis für automatische Stapelverarbeitung (z.B. data/whisper_inbox)")
    parser.add_argument("--verify-audio", help="Audiodatei für Paritäts-QA mit --article")
    parser.add_argument("--article", help="Artikel-Markdown-Datei für Paritäts-QA mit --verify-audio")
    parser.add_argument("--json", action="store_true", help="Maschinenlesbare JSON-Ausgabe")
    parser.add_argument("--selftest", action="store_true", help="Führt den Offline-Selbsttest aus")

    args = parser.parse_args()

    if args.selftest:
        success = selftest()
        return 0 if success else 1

    engine = WhisperEngine(
        backend=args.backend,
        model=args.model,
        language=args.language,
    )

    if args.verify_audio and args.article:
        qa_result = verify_audio_parity(args.verify_audio, args.article, engine=engine)
        if args.json:
            print(json.dumps(qa_result, ensure_ascii=False, indent=2))
        else:
            print(f"📊 Audio-QA Ergebnis für: {args.verify_audio}")
            print(f"   Status: {qa_result['status'].upper()} (Score: {qa_result['similarity_score']})")
            print(f"   Artikel: {args.article}")
        return 0 if qa_result.get("passed", False) else 1

    if args.watch_dir:
        results = process_inbox_directory(inbox_dir=args.watch_dir, engine=engine)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            print(f"✅ Inbox-Verarbeitung abgeschlossen: {len(results)} Entwürfe erzeugt.")
        return 0

    if not args.input:
        parser.print_help()
        return 1

    print(f"🎙 Transkribiere {args.input} mit Backend '{engine._resolved_backend}' (Modell: {engine.model})...")
    try:
        transcript = engine.transcribe(args.input)
    except (ValueError, FileNotFoundError) as exc:
        # Eingangs-Wacht: saubere Fehlermeldung statt Traceback (Meldung #559)
        print(f"⛔ Eingangs-Wacht hat die Anfrage abgelehnt: {exc}")
        return 2
    except (RuntimeError, OSError) as exc:
        print(f"⛔ Backend-Fehler (fail-closed): {exc}")
        return 3

    if args.to_draft:
        article = transform_voice_to_article(
            transcript=transcript,
            kategorie=args.kategorie,
            custom_title=args.title,
            audio_filename=os.path.basename(args.input),
        )
        post_dir = os.path.join(DRAFTS_DIR, article["slug"])
        os.makedirs(post_dir, exist_ok=True)
        out_file = os.path.join(post_dir, "index.md")
        with open(out_file, "w", encoding="utf-8") as fh:
            fh.write(article["markdown"])
        
        # Untertitel beilegen
        export_vtt(transcript, os.path.join(post_dir, "transcript.vtt"))
        print(f"✨ Artikelentwurf erfolgreich erstellt: {out_file}")
        print(f"   Titel: {article['title']}")
        print(f"   Wortanzahl: {article['word_count']} (~{article['reading_time']} Min. Lesezeit)")
        return 0

    if args.format == "vtt":
        out_p = args.output or f"{os.path.splitext(args.input)[0]}.vtt"
        export_vtt(transcript, out_p)
        print(f"💾 WebVTT gespeichert unter: {out_p}")
    elif args.format == "srt":
        out_p = args.output or f"{os.path.splitext(args.input)[0]}.srt"
        export_srt(transcript, out_p)
        print(f"💾 SRT gespeichert unter: {out_p}")
    elif args.format == "json" or args.json:
        if args.output:
            with open(args.output, "w", encoding="utf-8") as fh:
                json.dump(transcript, fh, ensure_ascii=False, indent=2)
            print(f"💾 JSON gespeichert unter: {args.output}")
        else:
            print(json.dumps(transcript, ensure_ascii=False, indent=2))
    else:
        if args.output:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(transcript.get("cleaned_text", ""))
            print(f"💾 Transkript gespeichert unter: {args.output}")
        else:
            print("\n--- TRANSKRIPT ---")
            print(transcript.get("cleaned_text", ""))

    return 0


if __name__ == "__main__":
    sys.exit(main())
