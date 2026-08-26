#!/usr/bin/env python3
"""Zentrale Groq-Konfiguration – Single Source of Truth.

Alle Automations-Skripte (Drafts, Guards, Meta, Spellcheck, …) lesen
URL, Modell, User-Agent und den Chat-Client von hier. Kein hartcodiertes
Modell und keine duplizierte Request-Logik mehr.

WARUM DIESES REFACTOR (26.08.2026):
  Groq hat llama-3.3-70b-versatile und llama-3.1-8b-instant am 16.08.2026
  für Free-/Developer-Tier abgeschaltet
  (https://console.groq.com/docs/deprecations).
  Offizieller Ersatz: openai/gpt-oss-120b bzw. openai/gpt-oss-20b.
  Vorher war das tote Modell in 13 Skripten hart verdrahtet – jeder
  Groq-Call wäre einzeln zu flicken gewesen.

Überschreiben:
  GROQ_API_KEY   Pflicht für echte Calls
  GROQ_MODEL     Default openai/gpt-oss-120b; deprecated IDs werden
                 automatisch auf den offiziellen Ersatz gemappt
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-120b"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

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


def headers() -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key()}",
        "User-Agent": USER_AGENT,
    }


def _payload(messages: list, temperature: float, max_tokens: int) -> dict:
    body = {
        "model": model(),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    # GPT-OSS denkt standardmäßig laut – ohne Flag landet Reasoning im
    # Content und zerlegt Frontmatter-/JSON-Parser der Guards.
    if model().startswith("openai/gpt-oss"):
        body["include_reasoning"] = False
    return body


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
    """Einheitlicher Groq-Chat. Liefert Antworttext oder None (kein Key).

    raise_on_error=True wirft nach ausgeschöpften Retries weiter
    (HTTPError/Timeout) – für Provider-Rotation in generate_drafts.
    """
    if not available():
        return None
    if messages is None:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt or ""})

    data = json.dumps(_payload(messages, temperature, max_tokens)).encode("utf-8")
    last_err: Exception | None = None
    for i in range(max(1, attempts)):
        try:
            req = urllib.request.Request(
                API_URL, data=data, headers=headers(), method="POST"
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            return (payload["choices"][0]["message"]["content"] or "").strip()
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (429, 500, 502, 503, 504) and i + 1 < attempts:
                time.sleep(4 * (i + 1))
                continue
            if raise_on_error:
                raise
            return None
        except (TimeoutError, urllib.error.URLError, ConnectionError, KeyError, IndexError, ValueError) as e:
            last_err = e
            if i + 1 < attempts:
                time.sleep(4 * (i + 1))
                continue
            if raise_on_error:
                raise
            return None
    if raise_on_error and last_err:
        raise last_err
    return None


if __name__ == "__main__":
    resolved = model()
    requested = (os.environ.get("GROQ_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL
    print(f"url:      {API_URL}")
    print(f"model:    {resolved}")
    if requested != resolved:
        print(f"mapped:   {requested} → {resolved} (deprecated)")
    print(f"key-set:  {'ja' if available() else 'nein'}")
    print(f"ua:       {USER_AGENT[:48]}…")
