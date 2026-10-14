#!/usr/bin/env python3
"""whisper_server.py — Lokaler FastAPI-Server für Whisper (OpenAI-kompatibel).

Stellt einen 100% lokalen, kostenlosen Endpunkt für n8n und Skripte bereit:
  - GET  /health                      → Health-Check
  - POST /v1/audio/transcriptions     → OpenAI Audio API Standard (für n8n OpenAI Audio Node)
  - POST /transcribe                  → Direkter Upload-Endpunkt

SICHERHEIT (Sicherheitsaudit 14.10.2026, N-11):
  · Kein CORS mehr: Vorher durfte JEDE Website im Browser des Betreibers den
    lokalen Dienst ansprechen (allow_origins=* mit Credentials). Der Dienst ist
    für Server-zu-Server-Aufrufe (n8n, Skripte) gedacht – Browser bleiben draußen.
  · Bindung standardmäßig an 127.0.0.1 (HOST). Im Container setzt die
    docker-compose.yml HOST=0.0.0.0; nach außen veröffentlicht sie den Port nur
    auf 127.0.0.1.
  · Optionaler Zugangsschlüssel: Ist WHISPER_TOKEN gesetzt, braucht jede
    Anfrage „Authorization: Bearer <token>“.
  · Upload-Grenze (MAX_UPLOAD_MB, Standard 50) und Endungs-Allowlist.
  · Temporärdateien werden IMMER gelöscht; Fehlertexte gehen nur ins Log,
    nach außen eine neutrale Meldung.
  · /transcribe war defekt (FastAPI-Form-Objekte als Werte übergeben) und
    nutzt jetzt denselben Kern mit echten Werten.
"""
from __future__ import annotations

import hmac
import logging
import os
import tempfile
import time
from typing import Any

import uvicorn
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from faster_whisper import WhisperModel

LOG = logging.getLogger("whisper-api")

app = FastAPI(
    title="FranksFinanzcheck Local Whisper Service",
    description="Lokale Spracherkennung ohne laufende Kosten für n8n & Blogautomatik.",
    version="1.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

MODEL_SIZE = os.environ.get("WHISPER_MODEL", "base")
DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")
COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")
PORT = int(os.environ.get("PORT", "8765"))
HOST = os.environ.get("HOST", "127.0.0.1")
MAX_UPLOAD_BYTES = int(float(os.environ.get("MAX_UPLOAD_MB", "50")) * 1024 * 1024)
TOKEN = os.environ.get("WHISPER_TOKEN", "").strip()
ERLAUBTE_ENDUNGEN = {".mp3", ".mpga", ".mpeg", ".m4a", ".mp4", ".wav", ".ogg", ".oga",
                     ".opus", ".webm", ".flac"}
ERLAUBTE_FORMATE = {"json", "text", "verbose_json"}

# Lazy-loaded Modell-Instanz
_model_instance: WhisperModel | None = None


def get_model() -> WhisperModel:
    global _model_instance
    if _model_instance is None:
        LOG.info("Lade Whisper-Modell %s (Device %s, Compute %s)", MODEL_SIZE, DEVICE, COMPUTE_TYPE)
        _model_instance = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
    return _model_instance


def zugang_pruefen(authorization: str | None = Header(default=None)) -> None:
    """Zugangsschlüssel prüfen – fail closed.

    Sicherheitsaudit 15.10.2026 (F-04): Vorher kehrte diese Funktion SOFORT
    zurück, wenn WHISPER_TOKEN leer war – der Dienst war dann offen. Genau
    das war der Standardfall: docker-compose setzte `${WHISPER_TOKEN:-}`, die
    Vorlage ließ den Wert leer. Da der Port auf 127.0.0.1 veröffentlicht ist,
    konnte JEDE Webseite, die der Betreiber besucht, Transkriptionen auslösen
    (ein `POST` mit FormData ist ein „simple request" ohne Preflight; die
    Antwort ist für den Angreifer nicht lesbar, die Arbeit aber passiert).
    Jetzt gilt: ohne konfigurierten Schlüssel wird nicht gearbeitet – außer
    der Betreiber schaltet es für eine lokale Probe ausdrücklich frei
    (WHISPER_OHNE_TOKEN_OK=1).
    """
    if not TOKEN:
        if os.environ.get("WHISPER_OHNE_TOKEN_OK") == "1":
            return
        raise HTTPException(
            status_code=503,
            detail="Dienst ohne Zugangsschlüssel gesperrt. WHISPER_TOKEN setzen "
                   "(openssl rand -hex 32 in tools/n8n/.env); nur für lokale Proben: "
                   "WHISPER_OHNE_TOKEN_OK=1",
        )
    erwartet = f"Bearer {TOKEN}"
    if not authorization or not hmac.compare_digest(authorization.encode(), erwartet.encode()):
        raise HTTPException(status_code=401, detail="Nicht autorisiert.")


@app.get("/health")
def health() -> dict[str, Any]:
    # Bewusst ohne Modell-/Gerätedetails (keine Betriebsinterna nach außen).
    return {"status": "ok", "service": "whisper-api", "timestamp": time.time()}


async def _speichern(file: UploadFile) -> str:
    endung = os.path.splitext(file.filename or "")[1].lower() or ".mp3"
    if endung not in ERLAUBTE_ENDUNGEN:
        raise HTTPException(status_code=415, detail="Dateityp nicht unterstützt.")
    gelesen = 0
    fd, pfad = tempfile.mkstemp(suffix=endung, prefix="whisper-")
    try:
        with os.fdopen(fd, "wb") as ziel:
            while True:
                block = await file.read(1024 * 1024)
                if not block:
                    break
                gelesen += len(block)
                if gelesen > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="Datei zu groß.")
                ziel.write(block)
    except BaseException:
        try:
            os.remove(pfad)
        except OSError:
            pass
        raise
    if gelesen == 0:
        os.remove(pfad)
        raise HTTPException(status_code=400, detail="Leere Datei.")
    return pfad


async def _transkribiere(file: UploadFile, language: str | None, prompt: str | None,
                         response_format: str, temperature: float) -> dict[str, Any]:
    if response_format not in ERLAUBTE_FORMATE:
        raise HTTPException(status_code=400, detail="Unbekanntes response_format.")
    if not 0.0 <= float(temperature) <= 1.0:
        raise HTTPException(status_code=400, detail="temperature muss zwischen 0 und 1 liegen.")
    sprache = (language or "").strip().lower()
    if sprache in ("", "auto"):
        sprache = None
    elif not (2 <= len(sprache) <= 5 and sprache.replace("-", "").isalpha()):
        raise HTTPException(status_code=400, detail="Ungültige Sprache.")
    pfad = await _speichern(file)
    try:
        segments, info = get_model().transcribe(
            pfad,
            language=sprache,
            initial_prompt=(prompt or None) and str(prompt)[:500],
            temperature=float(temperature),
            word_timestamps=True,
        )
        texte, liste = [], []
        for s in segments:
            texte.append(s.text.strip())
            liste.append({"id": s.id, "start": s.start, "end": s.end, "text": s.text.strip()})
        text = " ".join(texte).strip()
        if response_format == "text":
            return {"text": text}
        return {"text": text, "language": info.language, "duration": info.duration, "segments": liste}
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001 – Details nur ins Log
        LOG.exception("Transkription fehlgeschlagen")
        raise HTTPException(status_code=500, detail="Transkription fehlgeschlagen.") from None
    finally:
        try:
            os.remove(pfad)
        except OSError:
            pass


@app.post("/v1/audio/transcriptions", dependencies=[Depends(zugang_pruefen)])
async def transcribe_openai_compatible(
    file: UploadFile = File(...),
    model: str = Form(default="base"),
    language: str | None = Form(default=None),
    prompt: str | None = Form(default=None),
    response_format: str = Form(default="json"),
    temperature: float = Form(default=0.0),
) -> dict[str, Any]:
    """OpenAI-kompatibler Endpunkt – direkt nutzbar mit dem n8n 'OpenAI' Audio Node."""
    return await _transkribiere(file, language, prompt, response_format, temperature)


@app.post("/transcribe", dependencies=[Depends(zugang_pruefen)])
async def transcribe_direct(
    file: UploadFile = File(...),
    language: str = Form(default="de"),
) -> dict[str, Any]:
    return await _transkribiere(file, language, None, "json", 0.0)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run("whisper_server:app", host=HOST, port=PORT, log_level="info",
                limit_concurrency=4, timeout_keep_alive=5)
