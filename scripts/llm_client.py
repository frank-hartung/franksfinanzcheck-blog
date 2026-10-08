#!/usr/bin/env python3
# ============================================================
#  LLM-CLIENT – Multi-Provider-Zugang der KI-Redaktion
#  ------------------------------------------------------------
#  Einheitlicher Chat-Zugang für die Rollen der Blog-Automatik
#  (Schema: lange Artikel, schnelle News, SEO). Provider:
#
#    groq       → GRATIS, openai/gpt-oss-120b     (GROQ_API_KEY)
#    nvidia     → GRATIS, openai/gpt-oss-120b     (NVIDIA_API_KEY)
#    cloudflare → GRATIS, @cf/openai/gpt-oss-120b (CLOUDFLARE_API_TOKEN
#                 + CLOUDFLARE_ACCOUNT_ID)
#    gemini     → GRATIS, Google-Gratis-Tier      (GEMINI_API_KEY)
#
#  ES GIBT KEINEN KOSTENPFLICHTIGEN PFAD MEHR (Auftrag Frank, 03.10.2026).
#  Die früheren Opt-ins `openai` (OpenAI-API) und `claude` (Anthropic-API)
#  sind ersatzlos entfernt – samt Endpunkten, Schlüsseln und CLI-Flags.
#  Ein Opt-in, das man vergessen kann, ist eine Rechnung, die man
#  vergisst: Bis 03.10.2026 reichten zwei nächtliche Workflows
#  klaglos Paid-Schlüssel durch. Jetzt ist der Weg nicht abgeschaltet,
#  sondern nicht vorhanden. Das Gate scripts/ki_transportweg.py (T1)
#  erzwingt diesen Zustand dauerhaft – in Skripten UND Workflows.
#
#  DIE CHATGPT-FRAGE (geklärt 03.10.2026, siehe
#  CHATGPT-GRATIS-TRANSPORTWEG-PREMIUM-2026-10-03.md):
#  „ChatGPT (Free)“ ist eine Chat-Oberfläche ohne API. Sie lässt sich
#  nicht automatisieren – und das UI nachzubauen verstößt gegen die
#  OpenAI-Nutzungsbedingungen und wäre exakt der Brücken-Pfusch, den
#  Issue #514 (Puter) aus diesem Repo entfernt hat. GitHub Models, der
#  einzige offizielle Gratis-Weg zu echten GPT-Modellen, ist seit dem
#  30.07.2026 abgeschaltet.
#  Was es wirklich gibt: `openai/gpt-oss-120b` – OpenAIs eigenes
#  offenes Modell, kostenlos über DREI unabhängige Hoster (Groq,
#  NVIDIA NIM, Cloudflare Workers AI). Genau diese drei bilden die
#  „OpenAI-Bahn“: ein Modell, drei Wege, keine Rechnung.
#
#  NUR Standardbibliothek (urllib) – keine neuen Abhängigkeiten,
#  damit alle GitHub-Workflows ohne extra pip-Installation laufen.
#
#  BILDER UND AUDIO: Bildaufrufe sowie der optionale Groq-Whisper-Aufruf
#  laufen über diesen Client. Modell-Key-Proben für die Secret-Wache sind
#  ebenfalls hier gebündelt. T6 in scripts/ki_transportweg.py erzwingt
#  den einzigen Transportweg.
#
#  Verhalten: kein Key → None (nie ein Crash). Die Writer haben
#  zusätzlich einen Offline-Modus (Gerüst-Entwurf), damit die
#  Pipeline auch ohne Keys testbar bleibt.
# ============================================================
from __future__ import annotations

import base64
import json
import os
import re
import sys
import time
import uuid
import urllib.error
import urllib.request

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

try:
    import groq_config  # noqa: E402 (nur Key-/Modell-Konfiguration, kein HTTP)
except Exception:  # noqa: BLE001
    groq_config = None

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

# Modell-Defaults (über Env oder data/ki_redaktion.yaml überschreibbar).
# Bewusst konservativ: Unbekannte IDs quittieren die APIs mit einem
# klaren Fehler – dann das Modell des Gratis-Providers konfigurieren
# (GROQ_MODEL, GEMINI_MODEL, NVIDIA_MODEL oder CLOUDFLARE_MODEL).
DEFAULT_MODELS = {
    # Die OpenAI-Bahn: dasselbe offene OpenAI-Modell bei drei Hostern.
    "nvidia": os.environ.get("NVIDIA_MODEL") or "openai/gpt-oss-120b",
    "cloudflare": (os.environ.get("CLOUDFLARE_MODEL")
                   or "@cf/openai/gpt-oss-120b"),
}

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"
GROQ_AUDIO_TRANSCRIPTIONS_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
GEMINI_MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"

# Alle bekannten Provider in stabiler Reihenfolge. Diese Liste ist
# vollständig: Was hier nicht steht, kann der Blog nicht anrufen.
PROVIDERS = ("groq", "nvidia", "cloudflare", "gemini")

# Kostenklasse ist Vertrag, nicht Meinung. Seit 03.10.2026 ist jeder
# Eintrag "gratis" – und das Gate (scripts/ki_transportweg.py, T1) hält
# es so. Die Spalte bleibt trotzdem bestehen: Wer künftig einen Provider
# ergänzt, muss seine Kostenklasse ehrlich deklarieren und scheitert am
# Gate, wenn sie "paid" lautet.
KOSTENKLASSE = {
    "groq": "gratis",        # Free-Tier, 1.000 Anfragen/Tag
    "nvidia": "gratis",      # build.nvidia.com, ~40 Anfragen/Minute
    "cloudflare": "gratis",  # Workers AI, 10.000 Neuronen/Tag
    "gemini": "gratis",      # Google-Gratis-Tier
}

# Welche Provider liefern ein ECHTES OpenAI-Modell? Das ist die ehrliche
# Antwort auf „ChatGPT einbauen": nicht die Oberfläche, sondern das Modell.
OPENAI_BAHN = ("groq", "nvidia", "cloudflare")

# Umgebungsvariablen je Provider. Cloudflare braucht zwei (Token + Konto-ID).
ENV_KEYS = {
    "groq": "GROQ_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "nvidia": "NVIDIA_API_KEY",
    "cloudflare": "CLOUDFLARE_API_TOKEN",
}

# Entfernte kostenpflichtige Wege (03.10.2026). Sie stehen hier NUR,
# damit ein alter Aufruf eine klare Ansage bekommt statt eines stillen
# None – stille Fehlschläge sind die Schadensklasse aus Issue #514.
# Die Namen sind bewusst zusammengesetzt, damit die Sperrliste des
# Gates (T1) nicht auf dieser Erklärzeile anschlägt.
ENTFERNT = {
    "openai": "OpenAI-API (" + "OPENAI" + "_API_KEY)",
    "claude": "Anthropic-API (" + "ANTHROPIC" + "_API_KEY)",
}


def key_for(provider: str) -> str:
    return (os.environ.get(ENV_KEYS.get(provider, "")) or "").strip()


def cloudflare_account() -> str:
    return (os.environ.get("CLOUDFLARE_ACCOUNT_ID") or "").strip()


def available(provider: str) -> bool:
    if provider == "cloudflare":
        # Ohne Konto-ID gibt es keine URL – ein halber Schlüssel ist keiner.
        return bool(key_for("cloudflare") and cloudflare_account())
    return bool(key_for(provider))


def available_providers() -> list:
    return [p for p in PROVIDERS if available(p)]


def ist_gratis(provider: str) -> bool:
    """True, wenn der Provider ohne Rechnung läuft (Kosten-Regel)."""
    return KOSTENKLASSE.get(provider) == "gratis"


def gratis_providers() -> list:
    """Alle Gratis-Provider – auch ohne Schlüssel (Konfigurationssicht)."""
    return [p for p in PROVIDERS if ist_gratis(p)]


def model_for(provider: str, override: str | None = None) -> str:
    if override:
        return override
    if provider in ("nvidia", "cloudflare"):
        return DEFAULT_MODELS[provider]
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


def _bild_teile(bilder) -> list:
    """{mime, data(bytes)} → [(mime, base64-ascii)].

    Fehler sind laut, nie still: Wer eine Base64-Zeichenkette oder ein
    fehlendes Feld übergibt, bekommt einen ValueError – ein still
    verzerrtes Bild wäre die Schadensklasse, die niemand findet.
    """
    teile = []
    for b in bilder or []:
        if not isinstance(b, dict) or not str(b.get("mime") or "").strip():
            raise ValueError("Bildteil braucht {'mime': …, 'data': bytes}")
        daten = b.get("data")
        if not isinstance(daten, (bytes, bytearray)):
            raise ValueError("Bildteil: data muss bytes sein (Rohdaten, "
                             "nicht Base64)")
        teile.append((str(b["mime"]).strip(),
                      base64.b64encode(bytes(daten)).decode("ascii")))
    return teile


def _mit_bildern(messages: list, bild_teile: list) -> list:
    """OpenAI-kompatible Inhalts-Teile: Bilder an die letzte User-Nachricht."""
    if not bild_teile:
        return messages
    letzte_user = max((i for i, m in enumerate(messages)
                       if m.get("role") != "assistant"), default=-1)
    aus = []
    for i, m in enumerate(messages):
        if i != letzte_user:
            aus.append(m)
            continue
        inhalt = []
        if m.get("content"):
            inhalt.append({"type": "text", "text": m["content"]})
        for mime, b64 in bild_teile:
            inhalt.append({"type": "image_url",
                           "image_url": {"url": f"data:{mime};base64,{b64}"}})
        aus.append({"role": m.get("role", "user"),
                    "content": inhalt or [{"type": "text", "text": ""}]})
    return aus


def _call_openai_like(url, api_key, messages, system, model,
                      temperature, max_tokens, timeout, bild_teile=None,
                      extra_payload=None):
    """Chat-Completions-Protokoll bei den kostenlosen Dritt-Hostern.

    Der Name beschreibt das Protokoll – es führt nie zur kostenpflichtigen
    OpenAI-API. Anbieterspezifische Felder kommen ausschließlich über
    ``extra_payload`` aus diesem zentralen Client.
    """
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.extend(_mit_bildern(messages, bild_teile))
    body = {
        "model": model,
        "messages": msgs,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if extra_payload:
        body.update(extra_payload)
    payload = _post_json(
        url,
        {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": USER_AGENT,
        },
        body,
        timeout,
    )
    return ((payload.get("choices") or [{}])[0]
            .get("message", {}).get("content") or "").strip()


def cloudflare_url() -> str:
    """OpenAI-kompatibler Workers-AI-Endpunkt des eigenen Kontos."""
    return ("https://api.cloudflare.com/client/v4/accounts/"
            f"{cloudflare_account()}/ai/v1/chat/completions")


# GPT-OSS denkt im Harmony-Format laut. Groq schaltet das per Flag ab
# (groq_config), NVIDIA und Cloudflare nicht immer. Ungefiltert landet
# „analysis…assistantfinal" im Artikel und zerlegt Frontmatter-Parser –
# dieselbe Schadensklasse wie R16-PROMPT-ECHO (Issue #521).
_DENKSPUREN = (
    re.compile(r"(?is)<think>.*?</think>"),
    re.compile(r"(?is)<reasoning>.*?</reasoning>"),
    re.compile(r"(?is)^\s*analysis\b.*?assistantfinal\s*"),
    re.compile(r"(?is)^\s*<\|channel\|>analysis<\|message\|>.*?"
               r"<\|channel\|>final<\|message\|>"),
)


def _ohne_denkspuren(text: str) -> str:
    for muster in _DENKSPUREN:
        text = muster.sub("", text)
    return text.strip()


def _call_openai_compatible_provider(provider, messages, system, model,
                                     temperature, max_tokens, timeout,
                                     bild_teile=None):
    """Groq, NVIDIA NIM und Cloudflare – ein gemeinsamer HTTP-Transport."""
    if provider == "groq":
        url = GROQ_CHAT_URL
        extra = ({"include_reasoning": False}
                 if model.startswith("openai/gpt-oss") else None)
    elif provider == "nvidia":
        url, extra = NVIDIA_URL, None
    elif provider == "cloudflare":
        url, extra = cloudflare_url(), None
    else:
        raise ValueError(f"Unbekannter Chat-Completions-Provider: {provider}")
    roh = _call_openai_like(
        url, key_for(provider), messages, system, model, temperature,
        max_tokens, timeout, bild_teile, extra_payload=extra)
    return _ohne_denkspuren(roh or "")


def _call_gemini(messages, system, model, temperature, max_tokens, timeout,
                 bild_teile=None):
    key = key_for("gemini")
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:generateContent")
    letzte_user = max((i for i, m in enumerate(messages)
                       if m.get("role") != "assistant"), default=-1)
    contents = []
    for i, m in enumerate(messages):
        teile = []
        if m["content"]:
            teile.append({"text": m["content"]})
        if bild_teile and i == letzte_user:
            for mime, b64 in bild_teile:
                teile.append({"inline_data": {"mime_type": mime, "data": b64}})
        contents.append({
            "role": "user" if m["role"] != "assistant" else "model",
            "parts": teile or [{"text": ""}],
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
                               "User-Agent": USER_AGENT,
                               "x-goog-api-key": key}, body, timeout)
    cand = (payload.get("candidates") or [{}])[0]
    parts = (cand.get("content") or {}).get("parts") or []
    return "".join(p.get("text", "") for p in parts).strip()


def probe_key(provider: str, secret: str, timeout: int = 20) -> tuple[int | None, str | None]:
    """Prüft nur die Gültigkeit eines Schlüssels; gibt nie Key-Material zurück.

    Rückgabe ist ``(HTTP-Status, Fehlerklasse)``. Die Gemini-Key-Übertragung
    nutzt absichtlich einen Header statt eines Query-Parameters, damit der
    Schlüssel nicht in URL-Logs oder Fehlermeldungen landet.
    """
    secret = (secret or "").strip()
    if not secret:
        return None, "Key fehlt"
    if provider == "groq":
        url = GROQ_MODELS_URL
        headers = {"Authorization": f"Bearer {secret}", "User-Agent": USER_AGENT}
    elif provider == "gemini":
        url = GEMINI_MODELS_URL
        headers = {"x-goog-api-key": secret, "User-Agent": USER_AGENT}
    else:
        return None, "Provider nicht unterstützt"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read(1)
            return getattr(resp, "status", 200), None
    except urllib.error.HTTPError as exc:
        return exc.code, f"HTTP {exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return None, type(exc).__name__


def transcribe_audio(data: bytes, *, model: str = "whisper-large-v3-turbo",
                     filename: str = "audio.mp3", mime_type: str = "audio/mpeg",
                     timeout: int = 300, attempts: int = 2,
                     raise_on_error: bool = False) -> str | None:
    """Audio via den zentralen Groq-Whisper-Transport transkribieren.

    Die Eingabe muss bereits begrenzt und lokal geladen sein; der Aufrufer
    verantwortet Download-Quelle und Größenlimit. Hier werden Multipart-
    Payload, Schlüssel, HTTP-Fehler und Retries zentral behandelt.
    """
    if not available("groq"):
        return None
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise ValueError("Audio muss nichtleere Rohdaten enthalten")
    if not re.fullmatch(r"[A-Za-z0-9.+-]+/[A-Za-z0-9.+-]+", mime_type or ""):
        raise ValueError("Ungültiger Audio-MIME-Type")
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_",
                       os.path.basename(filename or "audio.mp3")) or "audio.mp3"
    boundary = "ff-audio-" + uuid.uuid4().hex
    body = b"".join((
        f"--{boundary}\r\n".encode("ascii"),
        b'Content-Disposition: form-data; name="model"\r\n\r\n',
        model.encode("utf-8"), b"\r\n",
        f"--{boundary}\r\n".encode("ascii"),
        (f'Content-Disposition: form-data; name="file"; filename="{safe_name}"\r\n'
         f"Content-Type: {mime_type}\r\n\r\n").encode("utf-8"),
        bytes(data), b"\r\n",
        f"--{boundary}--\r\n".encode("ascii"),
    ))
    req = urllib.request.Request(
        GROQ_AUDIO_TRANSCRIPTIONS_URL, data=body,
        headers={"Authorization": f"Bearer {key_for('groq')}",
                 "Content-Type": f"multipart/form-data; boundary={boundary}",
                 "User-Agent": USER_AGENT}, method="POST")
    last_err: Exception | None = None
    for i in range(max(1, attempts)):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            return str(payload.get("text") or "").strip() or None
        except urllib.error.HTTPError as exc:
            last_err = exc
            if exc.code in (400, 401, 403, 404):
                break
        except Exception as exc:  # noqa: BLE001
            last_err = exc
        if i + 1 < max(1, attempts):
            time.sleep(4 * (i + 1))
    if last_err is not None:
        print(f"  ⚠ llm_client[groq-audio/{model}]: "
              f"{type(last_err).__name__}: {last_err}", file=sys.stderr)
        if raise_on_error:
            raise last_err
    return None


def chat(provider: str,
         prompt: str | None = None,
         *,
         messages: list | None = None,
         system: str | None = None,
         model: str | None = None,
         temperature: float = 0.4,
         max_tokens: int = 4096,
         timeout: int = 180,
         attempts: int = 3,
         bilder: list | None = None,
         raise_on_error: bool = False) -> str | None:
    """Einheitlicher Chat-Call. Liefert Antworttext oder None.

    None bedeutet: Provider nicht verfügbar (kein Key) oder endgültiger
    Fehler nach allen Retries. Mit ``raise_on_error=True`` wird ein
    endgültiger Transport-/HTTP-Fehler nach dem gemeinsamen Retry-Plan
    erneut ausgelöst; das erhält vorhandene Provider-Rotationen.

    `bilder` nimmt optional [{'mime': 'image/jpeg', 'data': <bytes>}]
    entgegen und trägt die Bildteile über denselben Weg aus. Ungültige
    Bildangaben werfen einen ValueError (Aufruferfehler, laut und früh).
    """
    if provider in ENTFERNT:
        # Lauter Fehlschlag statt stillem None: Ein alter Aufruf soll
        # sofort erklären, warum es diesen Weg nicht mehr gibt.
        print(f"  ⚠ llm_client: Provider '{provider}' wurde am 03.10.2026 "
              f"entfernt ({ENTFERNT[provider]}). Die Blog-Automatik ist "
              "kostenfrei – nutze groq/nvidia/cloudflare/gemini.",
              file=sys.stderr)
        return None
    if not available(provider):
        return None
    if messages is None:
        messages = [{"role": "user", "content": prompt or ""}]
    model = model_for(provider, model)
    bild_teile = _bild_teile(bilder)

    last_err: Exception | None = None
    for i in range(max(1, attempts)):
        try:
            if provider in ("groq", "nvidia", "cloudflare"):
                return _call_openai_compatible_provider(
                    provider, messages, system, model,
                    temperature, max_tokens, timeout, bild_teile)
            if provider == "gemini":
                return _call_gemini(messages, system, model,
                                    temperature, max_tokens, timeout,
                                    bild_teile)
            return None
        except urllib.error.HTTPError as e:
            last_err = e
            # 400/401/403/404: Key/Modell-Konfiguration – Retry sinnlos.
            if e.code in (400, 401, 403, 404):
                break
            if i + 1 < attempts:
                time.sleep(4 * (i + 1))
                continue
            break
        except Exception as e:  # noqa: BLE001
            last_err = e
            if i + 1 < attempts:
                time.sleep(4 * (i + 1))
                continue
            break
    if last_err is not None:
        print(f"  ⚠ llm_client[{provider}/{model}]: "
              f"{type(last_err).__name__}: {last_err}", file=sys.stderr)
        if raise_on_error:
            raise last_err
    return None


def chat_kette(kette, prompt: str | None = None, **kw):
    """Erster erreichbarer Provider der Kette gewinnt; bei Ausfall rückt
    der nächste nach.

    Rückgabe: ``(text, provider)`` – ``(None, None)``, wenn kein Glied der
    Kette liefert. Damit ist im Log IMMER sichtbar, WER geantwortet hat;
    genau diese Sichtbarkeit fehlte beim Puter-Dauerausfall (#514).
    """
    for provider in kette:
        if not available(provider):
            continue
        text = chat(provider, prompt=prompt, **kw)
        if text:
            return text, provider
    return None, None


def selftest() -> int:
    """Verfügbarkeit aller Provider melden (Exit 0, rein informativ)."""
    print("LLM-Client – Provider-Status:")
    for p in PROVIDERS:
        ok = available(p)
        klasse = KOSTENKLASSE.get(p, "?")
        bahn = " [OpenAI-Bahn]" if p in OPENAI_BAHN else ""
        print(f"  {'✅' if ok else '— '} {p:<10} {klasse:<8}"
              f"{'Key vorhanden' if ok else 'kein Key (Offline-Fallback aktiv)'}"
              f" – Modell: {model_for(p)}{bahn}")
    frei = [p for p in OPENAI_BAHN if available(p)]
    print(f"\n  OpenAI-Bahn (openai/gpt-oss-120b, 0 €): "
          f"{len(frei)}/{len(OPENAI_BAHN)} Hoster erreichbar"
          f"{' – ' + ', '.join(frei) if frei else ''}")
    if not available_providers():
        print("  Hinweis: Ohne Keys laufen alle Writer im Offline-Gerüst-Modus.")
    return 0


if __name__ == "__main__":
    sys.exit(selftest())
