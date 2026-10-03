#!/usr/bin/env python3
"""whisper_server.py — Lokaler FastAPI-Server für Whisper (OpenAI-kompatibel).

Stellt einen 100% lokalen, kostenlosen Endpunkt für n8n und Skripte bereit:
  - GET  /health                      → Health-Check
  - POST /v1/audio/transcriptions     → OpenAI Audio API Standard (für n8n OpenAI Audio Node)
  - POST /transcribe                  → Direkter Upload-Endpunkt
"""
from __future__ import annotations

import os
import shutil
import tempfile
import time
from typing import Any

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel

app = FastAPI(
    title="FranksFinanzcheck Local Whisper Service",
    description="Lokale Spracherkennung ohne laufende Kosten für n8n & Blogautomatik.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_SIZE = os.environ.get("WHISPER_MODEL", "base")
DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")
COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")
PORT = int(os.environ.get("PORT", "8765"))

# Lazy-loaded Modell-Instanz
_model_instance: WhisperModel | None = None


def get_model() -> WhisperModel:
    global _model_instance
    if _model_instance is None:
        print(f"📦 Lade Whisper Modell: {MODEL_SIZE} (Device: {DEVICE}, Compute: {COMPUTE_TYPE})...")
        _model_instance = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
        print("✅ Whisper Modell erfolgreich initialisiert.")
    return _model_instance


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "whisper-api",
        "model": MODEL_SIZE,
        "device": DEVICE,
        "compute_type": COMPUTE_TYPE,
        "timestamp": time.time(),
    }


@app.post("/v1/audio/transcriptions")
async def transcribe_openai_compatible(
    file: UploadFile = File(...),
    model: str = Form(default="base"),
    language: str | None = Form(default=None),
    prompt: str | None = Form(default=None),
    response_format: str = Form(default="json"),
    temperature: float = Form(default=0.0),
) -> dict[str, Any]:
    """OpenAI-kompatibler Endpunkt – direkt nutzbar mit dem n8n 'OpenAI' Audio Node."""
    try:
        suffix = os.path.splitext(file.filename or "audio.mp3")[1] or ".mp3"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        whisper = get_model()
        segments, info = whisper.transcribe(
            tmp_path,
            language=language if language and language != "auto" else None,
            initial_prompt=prompt,
            temperature=temperature,
            word_timestamps=True,
        )

        full_text = []
        seg_list = []
        for s in segments:
            full_text.append(s.text.strip())
            seg_list.append({
                "id": s.id,
                "start": s.start,
                "end": s.end,
                "text": s.text.strip(),
            })

        os.remove(tmp_path)
        combined_text = " ".join(full_text).strip()

        if response_format == "text":
            return {"text": combined_text}

        return {
            "text": combined_text,
            "language": info.language,
            "duration": info.duration,
            "segments": seg_list,
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/transcribe")
async def transcribe_direct(
    file: UploadFile = File(...),
    language: str = Form(default="de"),
) -> dict[str, Any]:
    return await transcribe_openai_compatible(file=file, language=language)


if __name__ == "__main__":
    uvicorn.run("whisper_server:app", host="0.0.0.0", port=PORT, log_level="info")
