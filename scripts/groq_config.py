#!/usr/bin/env python3
"""Groq-Konfiguration und kompatibler Wrapper für den zentralen LLM-Client.

Alle Schlüssel-, Modell- und Transportlogik liegt in ``llm_client.py``.
Dieses Modul bleibt als Übergangsschicht erhalten, damit ältere Aufrufer
keine zweite HTTP-Implementierung mehr mitbringen müssen.

Überschreiben:
  GROQ_API_KEY   Pflicht für echte Calls
  GROQ_MODEL     Default openai/gpt-oss-120b; alte Modell-IDs werden
                 automatisch auf den offiziellen Ersatz gemappt
"""
from __future__ import annotations

import os

DEFAULT_MODEL = "openai/gpt-oss-120b"

# Abgeschaltete IDs → offizielle Groq-Empfehlung (Stand 16.08.2026).
DEPRECATED_MODELS = {
    "llama-3.3-70b-versatile": "openai/gpt-oss-120b",
    "llama-3.1-8b-instant": "openai/gpt-oss-20b",
    "llama3-70b-8192": "openai/gpt-oss-120b",
    "llama3-8b-8192": "openai/gpt-oss-20b",
    "llama-3.1-70b-versatile": "openai/gpt-oss-120b",
    "mixtral-8x7b-32768": "openai/gpt-oss-120b",
    "qwen/qwen3-32b": "openai/gpt-oss-120b",
    "meta-llama/llama-4-scout-17b-16e-instruct": "openai/gpt-oss-120b",
}


def api_key() -> str:
    return (os.environ.get("GROQ_API_KEY") or "").strip()


def available() -> bool:
    return bool(api_key())


def model() -> str:
    raw = (os.environ.get("GROQ_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL
    return DEPRECATED_MODELS.get(raw, raw)


def chat(
    prompt: str | None = None,
    *,
    messages: list | None = None,
    system: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 1000,
    timeout: int = 90,
    attempts: int = 3,
    raise_on_error: bool = False,
) -> str | None:
    """Abwärtskompatibler Aufruf – delegiert vollständig an llm_client.chat."""
    # Lokaler Import verhindert einen Importzyklus: llm_client benötigt die
    # reinen Key-/Modell-Funktionen dieses Moduls, ruft aber nie diesen Wrapper.
    import llm_client

    return llm_client.chat(
        "groq", prompt=prompt, messages=messages, system=system,
        model=model(), temperature=temperature, max_tokens=max_tokens,
        timeout=timeout, attempts=attempts, raise_on_error=raise_on_error,
    )


if __name__ == "__main__":
    print("transport: scripts/llm_client.py")
    print(f"model:    {model()}")
    print(f"key-set:  {'ja' if available() else 'nein'}")
