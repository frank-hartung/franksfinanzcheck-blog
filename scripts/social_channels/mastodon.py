#!/usr/bin/env python3
# ============================================================
#  ADAPTER: MASTODON (Fediverse)
#  ------------------------------------------------------------
#  API: /api/v1/statuses, /api/v2/media
#  Besonderheiten:
#    - 500 Zeichen (Instanzen können abweichen – Konfiguration ist SSOT)
#    - Bilder MIT Alt-Text (A11y + Fediverse-Suche)
#    - Threads = Antwort-Kette auf den eigenen Status
#    - Token läuft nie ab → stabilster Kanal des Autopiloten
# ============================================================
from __future__ import annotations

import json
import mimetypes
import os
import urllib.parse
import uuid

from . import ChannelAdapter, PublishResult, failed, http_json, register, skipped

DEFAULT_INSTANCE = "https://mastodon.social"


@register("mastodon")
class MastodonAdapter(ChannelAdapter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = (os.environ.get("MASTODON_INSTANCE") or DEFAULT_INSTANCE).strip().rstrip("/")
        self.token = (os.environ.get("MASTODON_ACCESS_TOKEN") or "").strip()

    def configured(self) -> tuple[bool, str]:
        if not self.token:
            return False, "MASTODON_ACCESS_TOKEN fehlt"
        return True, ""

    def _headers(self, json_body: bool = False) -> dict:
        h = {"Authorization": f"Bearer {self.token}"}
        if json_body:
            h["Content-Type"] = "application/json"
        return h

    def upload_media(self, path: str, alt: str = "") -> tuple[str, str]:
        """Lädt ein Bild hoch (multipart) und liefert (media_id, fehler)."""
        try:
            with open(path, "rb") as fh:
                blob = fh.read()
        except OSError as exc:
            return "", f"Bild nicht lesbar ({exc})"

        boundary = f"----ffsocial{uuid.uuid4().hex}"
        ctype = mimetypes.guess_type(path)[0] or "image/jpeg"
        name = os.path.basename(path)
        parts = b""
        if alt:
            parts += (
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"description\""
                f"\r\n\r\n{alt}\r\n"
            ).encode("utf-8")
        parts += (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
            f"filename=\"{name}\"\r\nContent-Type: {ctype}\r\n\r\n"
        ).encode("utf-8") + blob + f"\r\n--{boundary}--\r\n".encode("utf-8")

        status, payload, err = http_json(
            f"{self.instance}/api/v2/media",
            data=parts,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
        )
        if err or not isinstance(payload, dict):
            return "", err or "Medien-Upload ohne Antwort"
        return str(payload.get("id") or ""), ""

    def _post_status(self, text: str, media_ids: list[str] | None = None,
                     reply_to: str = "") -> tuple[dict | None, str]:
        payload = {"status": text, "visibility": "public", "language": "de"}
        if media_ids:
            payload["media_ids[]"] = media_ids
        if reply_to:
            payload["in_reply_to_id"] = reply_to
        body = urllib.parse.urlencode(payload, doseq=True).encode("utf-8")
        status, data, err = http_json(
            f"{self.instance}/api/v1/statuses",
            data=body,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        if err:
            return None, err
        if not isinstance(data, dict):
            return None, f"unerwartete Antwort (HTTP {status})"
        return data, ""

    def publish(self, item: dict) -> PublishResult:
        ok, reason = self.configured()
        if not ok:
            return skipped(reason)

        media_ids: list[str] = []
        media_path = item.get("media_path")
        if media_path and os.path.isfile(media_path):
            mid, merr = self.upload_media(media_path, (item.get("alt") or "")[:1400])
            if mid:
                media_ids.append(mid)
            elif merr:
                print(f"    ⚠ Mastodon-Bild abgelehnt ({merr}) – poste als Text.")
        elif self.media_cfg.get("required"):
            return failed("Bildpflicht nicht erfüllt (Cover fehlt)")

        parts = item.get("thread") or []
        if parts and self.supports_threads:
            parent_id = ""
            last_url = ""
            for i, part in enumerate(parts[: int((self.text_cfg.get("thread") or {}).get("max_parts", 5))]):
                data, err = self._post_status(part, media_ids if i == 0 else None, parent_id)
                if err:
                    if i == 0:
                        return failed(err)
                    print(f"    ⚠ Thread bei Teil {i + 1} abgebrochen: {err}")
                    break
                parent_id = str(data.get("id") or "")
                last_url = data.get("url") or last_url
            if last_url:
                return PublishResult(ok=True, url=last_url, ref=parent_id)
            return failed("Thread ohne bestätigten Status")

        data, err = self._post_status(item.get("text", ""), media_ids)
        if err:
            return failed(err)
        return PublishResult(ok=True, url=data.get("url") or "", ref=str(data.get("id") or ""))

    def comment(self, target: str, text: str) -> PublishResult:
        ok, reason = self.configured()
        if not ok:
            return skipped(reason)
        if not target:
            return failed("Keine Status-ID für den Zweitpost")
        data, err = self._post_status(text, None, target)
        if err:
            return failed(err)
        return PublishResult(ok=True, url=data.get("url") or "", ref=str(data.get("id") or ""))
