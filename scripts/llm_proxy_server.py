#!/usr/bin/env python3
# ============================================================
#  LLM-PROXY-SERVER – Einheitliche Transportschicht
#  für Cloudflare Worker + Frontend-Backend-Split
#  ============================================================
#
#  Architektur:
#    Cloudflare Worker (Edge)
#         ↓ HTTPS POST
#    LLM-Proxy-Server (Backend)
#         ↓ Validierung + Audit-Log
#    scripts/llm_client.py (Python)
#         ↓ Provider-Routing
#    Groq / NVIDIA / Cloudflare / Gemini
#
#  Dies ist das zentrale Verteilzentrum. Jeder LLM-Call vom Worker
#  wird hier protokolliert, validiert und an den Python-Client
#  weitergeleitet. So bleibt der Transportweg T6 (ki_transportweg.py)
#  durchgehend nachvollziehbar.
#
#  Betrieb:
#    python3 scripts/llm_proxy_server.py --listen 127.0.0.1:8080
#    (Production: hinter einem HTTPS-Reverse-Proxy wie nginx/Caddy)
#
#  ENV-Variablen:
#    LLM_PROXY_LISTEN  = "127.0.0.1:8080" (default)
#    LLM_PROXY_LOG_DIR = "data/llm-proxy" (default; wird erstellt)
#    LLM_PROXY_SECRET  = "" (optional: HMAC-X-Signature zum Worker)
# ============================================================
from __future__ import annotations

import argparse
import asyncio
import base64
import datetime
import functools
import hashlib
import hmac
import inspect
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

BLOG_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BLOG_DIR / "scripts"))

try:
    import llm_client
except ImportError:
    llm_client = None

# ---- Logging ----
LOG_DIR = Path(os.environ.get("LLM_PROXY_LOG_DIR", BLOG_DIR / "data" / "llm-proxy"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / f"proxy-{datetime.date.today()}.log"),
        logging.StreamHandler(sys.stderr),
    ],
)
logger = logging.getLogger(__name__)

ALLOWED_PROVIDERS = frozenset(("groq", "nvidia", "cloudflare", "gemini"))


def log_request(method: str, path: str, status: int, provider: str | None = None,
                duration_ms: float = 0, error: str | None = None, ip: str = "?") -> None:
    """Audit-Trail: Jeder Call wird protokolliert."""
    msg = (f"{ip:15} {method:4} {path:30} {status:3} "
           f"{duration_ms:6.1f}ms")
    if provider:
        msg += f" [{provider}]"
    if error:
        msg += f" ERROR: {error}"
    logger.info(msg)


async def read_json_body(scope: dict, receive: Any) -> dict:
    """ASGI-Body-Decoder: liest die vollständige POST-Payload."""
    body_parts = []
    while True:
        msg = await receive()
        if msg["type"] == "http.request":
            body_parts.append(msg.get("body", b""))
            if not msg.get("more_body", False):
                break
    return json.loads(b"".join(body_parts).decode("utf-8"))


def validate_signature(body_str: str, signature_header: str | None,
                       secret: str | None) -> bool:
    """Optional: HMAC-X-Signature validieren (wenn secret gesetzt)."""
    if not secret or not signature_header:
        return True
    try:
        expected = base64.b64encode(
            hmac.new(secret.encode(), body_str.encode(), hashlib.sha256).digest()
        ).decode("ascii")
        return hmac.compare_digest(expected, signature_header)
    except Exception:
        return False


async def handle_chat(scope: dict, receive: Any, send: Any, secret: str | None) -> None:
    """POST /proxy/{provider}/chat – Forwarding zu llm_client.chat()."""
    start_time = time.time()
    status = 400
    provider = None
    error_msg = None
    ip = (
        dict(scope.get("headers", [])).get(b"x-forwarded-for", b"?").decode("utf-8", errors="ignore")
        or "?"
    )

    try:
        # Body lesen
        body_str = (b"".join([
            msg.get("body", b"")
            async for msg in iter_request_body(receive)
        ])).decode("utf-8")
        body = json.loads(body_str)

        # Signature validieren
        if not validate_signature(body_str, body.get("_signature"), secret):
            status = 401
            error_msg = "Invalid signature"
            response_data = {"error": "Signature validation failed"}
            await send_json_response(send, status, response_data)
            return

        # Provider extrahieren + validieren
        provider = (body.get("provider") or "").lower().strip()
        if provider not in ALLOWED_PROVIDERS:
            status = 400
            error_msg = f"Unknown provider: {provider}"
            response_data = {"error": f"Provider '{provider}' not supported"}
            await send_json_response(send, status, response_data)
            return

        if not llm_client:
            status = 503
            error_msg = "llm_client module not available"
            response_data = {"error": "Service unavailable"}
            await send_json_response(send, status, response_data)
            return

        # Payload vorbereiten
        messages = body.get("messages", [])
        system_prompt = body.get("systemPrompt", "")
        max_tokens = min(int(body.get("maxTokens", 1500)), 4096)

        # llm_client.chat() aufrufen
        answer = await run_sync(
            llm_client.chat,
            provider=provider,
            messages=messages,
            system=system_prompt,
            max_tokens=max_tokens,
            timeout=30,
            attempts=2,
        )

        if answer:
            status = 200
            response_data = {"answer": answer, "provider": provider}
        else:
            status = 503
            error_msg = f"Provider {provider} unavailable or failed"
            response_data = {
                "error": "Service temporarily unavailable",
                "offline": True,
            }

        await send_json_response(send, status, response_data)

    except json.JSONDecodeError:
        status = 400
        error_msg = "Invalid JSON"
        await send_json_response(send, status, {"error": "Invalid JSON in request body"})
    except KeyError as e:
        status = 400
        error_msg = f"Missing field: {e}"
        await send_json_response(send, status, {"error": f"Missing required field: {e}"})
    except Exception as e:
        status = 500
        error_msg = f"{type(e).__name__}: {e}"
        await send_json_response(send, status, {"error": "Internal server error"})

    finally:
        duration_ms = (time.time() - start_time) * 1000
        path = f"/proxy/{provider}/chat" if provider else "/proxy/unknown/chat"
        log_request("POST", path, status, provider, duration_ms, error_msg, ip)


async def iter_request_body(receive: Any):
    """Async-Iterator über ASGI-Request-Body-Chunks."""
    while True:
        msg = await receive()
        if msg["type"] == "http.request":
            yield msg.get("body", b"")
            if not msg.get("more_body"):
                break


async def send_json_response(send: Any, status: int, data: dict) -> None:
    """ASGI-JSON-Response versenden."""
    body = json.dumps(data).encode("utf-8")
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [
            (b"content-type", b"application/json"),
            (b"access-control-allow-origin", b"*"),
            (b"cache-control", b"no-store"),
        ],
    })
    await send({
        "type": "http.response.body",
        "body": body,
    })


def run_sync(func, *args, **kwargs):
    """Synchrone Python-Funktion in async-Kontext aufrufen."""
    loop = asyncio.get_event_loop()
    if inspect.iscoroutinefunction(func):
        return loop.create_task(func(*args, **kwargs))
    else:
        return loop.run_in_executor(None, functools.partial(func, *args, **kwargs))


async def app(scope: dict, receive: Any, send: Any) -> None:
    """ASGI-Hauptanwendung."""
    secret = os.environ.get("LLM_PROXY_SECRET", "").strip() or None

    if scope["type"] == "http":
        path = scope.get("path", "")

        # CORS Preflight
        if scope["method"] == "OPTIONS":
            await send({
                "type": "http.response.start",
                "status": 204,
                "headers": [
                    (b"access-control-allow-origin", b"*"),
                    (b"access-control-allow-methods", b"POST, OPTIONS"),
                    (b"access-control-allow-headers", b"Content-Type, X-Signature"),
                ],
            })
            await send({"type": "http.response.body", "body": b""})
            return

        # Health Check
        if path == "/health":
            await send_json_response(send, 200, {"status": "ok", "llm_client": llm_client is not None})
            return

        # LLM-Proxy-Routen
        if re.match(r"^/proxy/(groq|nvidia|cloudflare|gemini)/chat$", path):
            await handle_chat(scope, receive, send, secret)
            return

        # 404
        await send_json_response(send, 404, {"error": "Not found"})


# ---- CLI + Server ----
async def main_async(host: str, port: int) -> None:
    """Starten mit uvicorn/hypercorn (Production)."""
    try:
        from hypercorn.asyncio import serve
        from hypercorn.config import Config

        config = Config()
        config.bind = [f"{host}:{port}"]
        config.accesslog = str(LOG_DIR / "access.log")
        await serve(app, config)
    except ImportError:
        logger.error("hypercorn nicht installiert. Installiere: pip install hypercorn")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="LLM Proxy Server – Backend für Cloudflare Worker"
    )
    parser.add_argument(
        "--listen",
        default=os.environ.get("LLM_PROXY_LISTEN", "127.0.0.1:8080"),
        help="Listen address (host:port)",
    )
    parser.add_argument(
        "--log-dir",
        default=str(LOG_DIR),
        help="Log directory",
    )
    args = parser.parse_args()

    # Parse host:port
    try:
        host, port_str = args.listen.rsplit(":", 1)
        port = int(port_str)
    except ValueError:
        logger.error(f"Invalid listen format: {args.listen}. Use host:port")
        sys.exit(1)

    logger.info(f"LLM Proxy Server starting on {host}:{port}")
    logger.info(f"Log directory: {args.log_dir}")

    if llm_client:
        logger.info("llm_client.py loaded – forwarding enabled")
    else:
        logger.warning("llm_client.py NOT loaded – /proxy/* will return 503")

    # Starten
    asyncio.run(main_async(host, port))


if __name__ == "__main__":
    main()
