#!/usr/bin/env python3
# ============================================================
#  LLM-CLIENT – Multi-Provider-Zugang der KI-Redaktion
#  ------------------------------------------------------------
#  Einheitlicher Chat-Zugang für die Rollen der Blog-Automatik
#  (Schema: lange Artikel, schnelle News, SEO). Provider:
#
#    groq       → GRATIS, openai/gpt-oss-120b     (GROQ_API_KEY,
#                 nutzt scripts/groq_config.py als SSOT)
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
#  BILDER (seit 08.10.2026): Auch Bildaufrufe gehen durch diesen
#  Client – ein Transportweg bleibt einer, auch für Cover-Alt-Texte.
#  chat(..., bilder=[{"mime": "image/jpeg", "data": <bytes>}]) trägt
#  die Bildteile im jeweiligen Protokoll (Gemini inline_data bzw.
#  OpenAI-kompatible Inhalts-Teile mit data-URL). Der Vertrag T6 des
#  Gates scripts/ki_transportweg.py erzwingt den Weg.
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
    # Die OpenAI-Bahn: dasselbe offene OpenAI-Modell bei drei Hostern.
    "nvidia": os.environ.get("NVIDIA_MODEL") or "openai/gpt-oss-120b",
    "cloudflare": (os.environ.get("CLOUDFLARE_MODEL")
                   or "@cf/openai/gpt-oss-120b"),
}

NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

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
                      temperature, max_tokens, timeout, bild_teile=None):
    """Chat-Completions-PROTOKOLL (nicht der Anbieter OpenAI).

    Groq, NVIDIA NIM und Cloudflare Workers AI sprechen alle dieses
    Format. Der Name beschreibt das Protokoll – es führt kein Pfad zur
    kostenpflichtigen OpenAI-API.
    """
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.extend(_mit_bildern(messages, bild_teile))
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


def _call_openai_kompatibel_frei(provider, messages, system, model,
                                 temperature, max_tokens, timeout,
                                 bild_teile=None):
    """NVIDIA NIM und Cloudflare Workers AI – beide OpenAI-kompatibel."""
    url = NVIDIA_URL if provider == "nvidia" else cloudflare_url()
    roh = _call_openai_like(url, key_for(provider), messages, system, model,
                            temperature, max_tokens, timeout, bild_teile)
    return _ohne_denkspuren(roh or "")


def _call_gemini(messages, system, model, temperature, max_tokens, timeout,
                 bild_teile=None):
    key = key_for("gemini")
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:generateContent?key={key}")
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
         attempts: int = 3,
         bilder: list | None = None) -> str | None:
    """Einheitlicher Chat-Call. Liefert Antworttext oder None.

    None bedeutet: Provider nicht verfügbar (kein Key) oder endgültiger
    Fehler nach allen Retries. Aufrufer entscheiden selbst über den
    Fallback – dieser Client wirft nie in die Pipeline hinein.

    `bilder` nimmt optional [{'mime': 'image/jpeg', 'data': <bytes>}]
    entgegen und trägt die Bildteile über denselben Weg aus (T6: ein
    Transportweg bleibt einer – auch für Bildaufrufe). Ungültige
    Bildangaben wirfen einen ValueError (Aufruferfehler, laut und früh).
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
            if provider in ("nvidia", "cloudflare"):
                return _call_openai_kompatibel_frei(
                    provider, messages, system, model,
                    temperature, max_tokens, timeout, bild_teile)
            if provider == "gemini":
                return _call_gemini(messages, system, model,
                                    temperature, max_tokens, timeout,
                                    bild_teile)
            if provider == "groq" and groq_config:
                msgs = []
                if system:
                    msgs.append({"role": "system", "content": system})
                msgs.extend(_mit_bildern(messages, bild_teile))
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
