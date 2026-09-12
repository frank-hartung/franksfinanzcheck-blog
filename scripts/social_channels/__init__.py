#!/usr/bin/env python3
# ============================================================
#  SOCIAL-CHANNELS – Adapter-Paket des Social-Autopiloten
#  ------------------------------------------------------------
#  Ein Adapter pro Netzwerk. Alle Adapter teilen dieselbe Basis:
#
#    configured()  → (True, "") oder (False, "MASTODON_ACCESS_TOKEN fehlt")
#    publish(item) → PublishResult   (NIE eine Exception nach außen)
#    comment(...)  → Zweitpost (z. B. LinkedIn-Link im ersten Kommentar)
#
#  WICHTIG (Betriebsruhe, Dauervorgabe): Ein fehlendes Token ist KEIN
#  Fehler. Der Kanal meldet „Standby", der Lauf bleibt grün. Nur ein
#  konfigurierter Kanal, der beim Senden scheitert, erzeugt einen
#  Fehler – dann übernimmt die Selbstheilung (Replan, späterer Versuch).
#
#  Alle Adapter nutzen ausschließlich die Python-Standardbibliothek
#  (urllib) – damit jeder GitHub-Workflow ohne pip-Installation läuft.
# ============================================================
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS_DIR = os.path.join(BLOG_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

CONFIG_PATH = os.path.join(BLOG_DIR, "data", "social", "channels.yaml")

USER_AGENT = "FranksFinanzcheck-SocialAutopilot/1.0 (+https://franksfinanzcheck.de)"


# --------------------------------------------------------------- Konfiguration
def load_config(path: str | None = None) -> dict:
    """Lädt data/social/channels.yaml (SSOT). Fehler → leeres Gerüst."""
    import yaml

    path = path or CONFIG_PATH
    try:
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except FileNotFoundError:
        return {}
    except Exception as exc:  # noqa: BLE001 – Konfiguration darf nie den Lauf killen
        print(f"⚠ channels.yaml nicht lesbar ({exc}) – Autopilot läuft im Leerlauf.")
        return {}


def channel_map(cfg: dict) -> dict:
    return (cfg.get("channels") or {}) if isinstance(cfg, dict) else {}


def meta_of(cfg: dict) -> dict:
    return (cfg.get("meta") or {}) if isinstance(cfg, dict) else {}


def enabled_channels(cfg: dict) -> list[str]:
    return [cid for cid, c in channel_map(cfg).items() if (c or {}).get("enabled", False)]


def missing_env(channel: dict) -> list[str]:
    """Welche Secrets/Variablen für diesen Kanal fehlen (leer = einsatzbereit)."""
    missing = []
    for key in (channel or {}).get("secrets") or []:
        if not (os.environ.get(key) or "").strip():
            missing.append(key)
    return missing


# -------------------------------------------------------------- Ergebnis-Typ
class PublishResult:
    """Ergebnis eines Sendevorgangs – immer gefüllt, nie eine Exception."""

    __slots__ = ("ok", "url", "ref", "error", "skipped", "raw")

    def __init__(self, ok: bool = False, url: str = "", ref: str = "",
                 error: str = "", skipped: bool = False, raw: dict | None = None):
        self.ok = ok
        self.url = url
        self.ref = ref
        self.error = error
        self.skipped = skipped
        self.raw = raw or {}

    def __repr__(self) -> str:  # pragma: no cover – Debug-Hilfe
        state = "skip" if self.skipped else ("ok" if self.ok else "fail")
        return f"<PublishResult {state} url={self.url!r} err={self.error!r}>"

    def as_dict(self) -> dict:
        return {"ok": self.ok, "url": self.url, "ref": self.ref,
                "error": self.error, "skipped": self.skipped}


def skipped(reason: str) -> PublishResult:
    return PublishResult(ok=False, skipped=True, error=reason)


def failed(reason: str) -> PublishResult:
    return PublishResult(ok=False, error=reason)


# ------------------------------------------------------------------- HTTP
def http_request(url: str, data: bytes | None = None, headers: dict | None = None,
                 method: str | None = None, timeout: int = 45,
                 retries: int = 3, backoff: float = 3.0):
    """Robuster HTTP-Call. Rückgabe: (status, body_bytes|None, error|None).

    Retries nur bei Netzwerkfehlern und 5xx; 4xx gehen sofort zurück
    (Konfigurationsfehler wiederholt man nicht – das kostet nur Zeit).
    """
    headers = dict(headers or {})
    headers.setdefault("User-Agent", USER_AGENT)
    last_err = None
    for attempt in range(max(1, retries)):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read(), None
        except urllib.error.HTTPError as exc:
            body = b""
            try:
                body = exc.read()
            except Exception:  # noqa: BLE001
                pass
            if exc.code in (429,) or 500 <= exc.code < 600:
                last_err = f"HTTP {exc.code}: {body[:200].decode('utf-8', 'ignore')}"
                if attempt + 1 < max(1, retries):
                    time.sleep(backoff * (attempt + 1))
                    continue
            return exc.code, body, f"HTTP {exc.code}: {body[:240].decode('utf-8', 'ignore')}"
        except Exception as exc:  # noqa: BLE001
            last_err = str(exc)[:240]
            if attempt + 1 < max(1, retries):
                time.sleep(backoff * (attempt + 1))
                continue
            return 0, None, last_err
    return 0, None, last_err or "unbekannter Netzwerkfehler"


def http_json(url: str, data: bytes | None = None, headers: dict | None = None,
              method: str | None = None, timeout: int = 45, retries: int = 3):
    """Wie http_request, gibt (status, json|None, error|None) zurück."""
    status, body, err = http_request(url, data=data, headers=headers, method=method,
                                     timeout=timeout, retries=retries)
    if body is None:
        return status, None, err
    try:
        return status, json.loads(body.decode("utf-8")), (err if status >= 400 else None)
    except Exception as exc:  # noqa: BLE001
        return status, None, f"Antwort kein JSON ({exc})"


def form_encode(fields: dict) -> bytes:
    return "&".join(
        f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in fields.items()
    ).encode("utf-8")


# ------------------------------------------------------------- Basis-Adapter
class ChannelAdapter:
    """Gemeinsame Basis: Konfiguration, Grenzwerte, Sende-Rahmen."""

    channel_id = ""
    #: Endpunkt-Template ggf. überschreiben
    def __init__(self, channel: dict, meta: dict, channel_id: str = ""):
        self.cfg = channel or {}
        self.meta = meta or {}
        self.channel_id = channel_id or self.channel_id
        self.text_cfg = self.cfg.get("text") or {}
        self.media_cfg = self.cfg.get("media") or {}
        self.cadence = self.cfg.get("cadence") or {}

    # -- Grenzwerte ---------------------------------------------------------
    @property
    def max_chars(self) -> int:
        return int(self.text_cfg.get("max_chars") or 500)

    @property
    def soft_max_chars(self) -> int:
        return int(self.text_cfg.get("soft_max_chars") or self.max_chars)

    @property
    def emoji_max(self) -> int:
        return int(self.text_cfg.get("emoji_max") or 0)

    @property
    def link_position(self) -> str:
        return self.text_cfg.get("link_position") or "end"

    @property
    def supports_threads(self) -> bool:
        return bool((self.text_cfg.get("thread") or {}).get("supported"))

    @property
    def label(self) -> str:
        return self.cfg.get("label") or self.channel_id

    # -- Konfiguration ------------------------------------------------------
    def configured(self) -> tuple[bool, str]:
        missing = missing_env(self.cfg)
        if missing:
            return False, f"{', '.join(missing)} fehlt"
        return True, ""

    def env(self, key: str, default: str = "") -> str:
        return (os.environ.get(key) or default).strip()

    # -- Senden -------------------------------------------------------------
    def publish(self, item: dict) -> PublishResult:  # pragma: no cover – Interface
        raise NotImplementedError

    def comment(self, target: str, text: str) -> PublishResult:
        """Zweitpost (Standard: nicht unterstützt)."""
        return skipped("Kommentar-Funktion von diesem Kanal nicht unterstützt")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{type(self).__name__} {self.channel_id}>"


# ----------------------------------------------------------------- Registry
_REGISTRY: dict[str, type] = {}


def register(channel_id: str):
    def _wrap(cls):
        _REGISTRY[channel_id] = cls
        cls.channel_id = channel_id
        return cls

    return _wrap


def adapter_class(channel_id: str):
    if channel_id in _REGISTRY:
        return _REGISTRY[channel_id]
    mod_name = f"social_channels.{channel_id}"
    try:
        mod = __import__(mod_name, fromlist=["*"])
    except Exception as exc:  # noqa: BLE001
        print(f"⚠ Adapter {channel_id} nicht ladbar: {exc}")
        return None
    return _REGISTRY.get(channel_id)


def get_adapter(channel_id: str, cfg: dict | None = None) -> ChannelAdapter | None:
    """Baut einen Adapter. Unbekannter Kanal → None (nie eine Exception)."""
    cfg = cfg if cfg is not None else load_config()
    channel = channel_map(cfg).get(channel_id)
    if not channel:
        return None
    cls = adapter_class(channel_id)
    if not cls:
        return None
    try:
        return cls(channel, meta_of(cfg), channel_id=channel_id)
    except Exception as exc:  # noqa: BLE001
        print(f"⚠ Adapter {channel_id} nicht initialisierbar: {exc}")
        return None


def available_adapters(cfg: dict | None = None) -> dict[str, ChannelAdapter]:
    cfg = cfg if cfg is not None else load_config()
    out = {}
    for cid in enabled_channels(cfg):
        ad = get_adapter(cid, cfg)
        if ad:
            out[cid] = ad
    return out
