#!/usr/bin/env python3
# ============================================================
#  LLM-CLIENT – Multi-Provider-Zugang der KI-Redaktion
#  ------------------------------------------------------------
#  Einheitlicher Chat-Zugang für die drei Rollen der Blog-Automatik
#  (Schema: Claude = lange Artikel, ChatGPT = schnelle News,
#  Jasper = SEO). Provider:
#
#    claude   → Anthropic Messages API   (ANTHROPIC_API_KEY)
#    openai   → OpenAI Chat Completions  (OPENAI_API_KEY)
#    groq     → vorhandener Gratis-Fallback (GROQ_API_KEY,
#               nutzt scripts/groq_config.py als SSOT)
#    gemini   → vorhandener Gratis-Fallback (GEMINI_API_KEY)
#
#  NUR Standardbibliothek (urllib) – keine neuen Abhängigkeiten,
#  damit alle GitHub-Workflows ohne extra pip-Installation laufen.
#
#  Verhalten: kein Key → None (nie ein Crash). Die Writer haben
#  zusätzlich einen Offline-Modus (Gerüst-Entwurf), damit die
#  Pipeline auch ohne Keys testbar bleibt.
# ============================================================
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

try:
    import groq_config  # noqa: E402  (SSOT für den Gratis-Fallback)
except Exception:  # noqa: BLE001
    groq_config = None

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

# Modell-Defaults (über Env oder data/ki_redaktion.yaml überschreibbar).
# Bewusst konservativ: unbekannte IDs quittieren die APIs mit einem
# klaren Fehler – dann einfach CLAUDE_MODEL / OPENAI_MODEL setzen.
DEFAULT_MODELS = {
    "claude": os.environ.get("CLAUDE_MODEL") or "claude-sonnet-4-5",
    "openai": os.environ.get("OPENAI_MODEL") or "gpt-4o",
}

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"


def key_for(provider: str) -> str:
    env = {
        "claude": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "groq": "GROQ_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }
    return (os.environ.get(env.get(provider, "")) or "").strip()


def available(provider: str) -> bool:
    return bool(key_for(provider))


def available_providers() -> list:
    return [p for p in ("claude", "openai", "groq", "gemini") if available(p)]


def model_for(provider: str, override: str | None = None) -> str:
    if override:
        return override
    if provider == "claude":
        return DEFAULT_MODELS["claude"]
    if provider == "openai":
        return DEFAULT_MODELS["openai"]
    if provider == "groq" and groq_config:
        return groq_config.model()
    if provider == "gemini":
        return os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")
    return ""


def _post_json(url: str, headers: dict, payload: dict, timeout: int) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _call_anthropic(messages, system, model, temperature, max_tokens, timeout):
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
    }
    if system:
        body["system"] = system
    payload = _post_json(
        ANTHROPIC_URL,
        {
            "x-api-key": key_for("claude"),
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
            "user-agent": USER_AGENT,
        },
        body,
        timeout,
    )
    parts = payload.get("content") or []
    text = "".join(p.get("text", "") for p in parts if p.get("type") == "text")
    return text.strip()


def _call_openai_like(url, api_key, messages, system, model,
                      temperature, max_tokens, timeout):
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.extend(messages)
    payload = _post_json(
        url,
        {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": USER_AGENT,
        },
        {
            "model": model,
            "messages": msgs,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout,
    )
    return ((payload.get("choices") or [{}])[0]
            .get("message", {}).get("content") or "").strip()


def _call_gemini(messages, system, model, temperature, max_tokens, timeout):
    key = key_for("gemini")
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:generateContent?key={key}")
    contents = []
    for m in messages:
        contents.append({
            "role": "user" if m["role"] != "assistant" else "model",
            "parts": [{"text": m["content"]}],
        })
    body = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    payload = _post_json(url, {"Content-Type": "application/json",
                               "User-Agent": USER_AGENT}, body, timeout)
    cand = (payload.get("candidates") or [{}])[0]
    parts = (cand.get("content") or {}).get("parts") or []
    return "".join(p.get("text", "") for p in parts).strip()


def chat(provider: str,
         prompt: str | None = None,
         *,
         messages: list | None = None,
         system: str | None = None,
         model: str | None = None,
         temperature: float = 0.4,
         max_tokens: int = 4096,
         timeout: int = 180,
         attempts: int = 3) -> str | None:
    """Einheitlicher Chat-Call. Liefert Antworttext oder None.

    None bedeutet: Provider nicht verfügbar (kein Key) oder endgültiger
    Fehler nach allen Retries. Aufrufer entscheiden selbst über den
    Fallback – dieser Client wirft nie in die Pipeline hinein.
    """
    if not available(provider):
        return None
    if messages is None:
        messages = [{"role": "user", "content": prompt or ""}]
    model = model_for(provider, model)

    last_err: Exception | None = None
    for i in range(max(1, attempts)):
        try:
            if provider == "claude":
                return _call_anthropic(messages, system, model,
                                       temperature, max_tokens, timeout)
            if provider == "openai":
                return _call_openai_like(OPENAI_URL, key_for("openai"),
                                         messages, system, model,
                                         temperature, max_tokens, timeout)
            if provider == "gemini":
                return _call_gemini(messages, system, model,
                                    temperature, max_tokens, timeout)
            if provider == "groq" and groq_config:
                msgs = []
                if system:
                    msgs.append({"role": "system", "content": system})
                msgs.extend(messages)
                return groq_config.chat(messages=msgs,
                                        temperature=temperature,
                                        max_tokens=max_tokens,
                                        timeout=timeout)
            return None
        except urllib.error.HTTPError as e:
            last_err = e
            # 400/401/403/404: Key/Modell-Konfiguration – Retry sinnlos.
            if e.code in (400, 401, 403, 404):
                break
            if i + 1 < attempts:
                time.sleep(4 * (i + 1))
                continue
            return None
        except Exception as e:  # noqa: BLE001
            last_err = e
            if i + 1 < attempts:
                time.sleep(4 * (i + 1))
                continue
            return None
    if last_err is not None:
        print(f"  ⚠ llm_client[{provider}/{model}]: {last_err}",
              file=sys.stderr)
    return None


def selftest() -> int:
    """Verfügbarkeit aller Provider melden (Exit 0, rein informativ)."""
    print("LLM-Client – Provider-Status:")
    for p in ("claude", "openai", "groq", "gemini"):
        ok = available(p)
        print(f"  {'✅' if ok else '— '} {p:<7} "
              f"({'Key vorhanden' if ok else 'kein Key (Offline-Fallback aktiv)'})"
              f" – Modell: {model_for(p)}")
    if not available_providers():
        print("  Hinweis: Ohne Keys laufen alle Writer im Offline-Gerüst-Modus.")
    return 0


if __name__ == "__main__":
    sys.exit(selftest())
