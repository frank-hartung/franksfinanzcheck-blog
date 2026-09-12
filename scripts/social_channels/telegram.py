#!/usr/bin/env python3
# ============================================================
#  ADAPTER: TELEGRAM (Kanal via Bot-API)
#  ------------------------------------------------------------
#  API: api.telegram.org/bot<token>/sendMessage | sendPhoto
#  Kanal-Logik:
#    - HTML-Markup (<b>, <i>, <a href>) – Telegram rendert es direkt
#    - Bis zu 4096 Zeichen, aber gelesen werden 3–5 Zeilen → das Gate
#      arbeitet mit soft_max_chars (700)
#    - Abonnenten sind die treueste Leserschaft: neue Artikel gehen
#      hier zuerst raus (launch_delay_hours = 0)
# ============================================================
from __future__ import annotations

import json
import mimetypes
import os
import urllib.parse
import uuid

from . import ChannelAdapter, PublishResult, failed, http_json, register, skipped


@register("telegram")
class TelegramAdapter(ChannelAdapter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = self.env("TELEGRAM_BOT_TOKEN")
        self.chat_id = self.env("TELEGRAM_CHAT_ID")
        self.base = f"https://api.telegram.org/bot{self.token}" if self.token else ""

    def configured(self) -> tuple[bool, str]:
        if not self.token:
            return False, "TELEGRAM_BOT_TOKEN fehlt"
        if not self.chat_id:
            return False, "TELEGRAM_CHAT_ID fehlt"
        return True, ""

    def _send(self, method: str, fields: dict, files: dict | None = None) -> tuple[dict | None, str]:
        url = f"{self.base}/{method}"
        if files:
            boundary = f"----fftelegram{uuid.uuid4().hex}"
            body = b""
            for key, value in fields.items():
                body += (f"--{boundary}\r\nContent-Disposition: form-data; "
                         f"name=\"{key}\"\r\n\r\n{value}\r\n").encode("utf-8")
            for key, path in files.items():
                ctype = mimetypes.guess_type(path)[0] or "image/jpeg"
                with open(path, "rb") as fh:
                    blob = fh.read()
                body += (f"--{boundary}\r\nContent-Disposition: form-data; "
                         f"name=\"{key}\"; filename=\"{os.path.basename(path)}\"\r\n"
                         f"Content-Type: {ctype}\r\n\r\n").encode("utf-8") + blob + b"\r\n"
            body += f"--{boundary}--\r\n".encode("utf-8")
            status, data, err = http_json(
                url, data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                timeout=90)
        else:
            status, data, err = http_json(
                url, data=urllib.parse.urlencode(fields).encode("utf-8"),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=60)
        if err:
            return None, err
        if not isinstance(data, dict) or not data.get("ok"):
            return None, f"Telegram: {(data or {}).get('description') or 'unbekannte Antwort'}"
        return data.get("result") or {}, ""

    def publish(self, item: dict) -> PublishResult:
        ok, reason = self.configured()
        if not ok:
            return skipped(reason)

        text = (item.get("text") or "")[: int(self.text_cfg.get("max_chars", 4096))]
        media_path = item.get("media_path")
        fields = {"chat_id": self.chat_id, "parse_mode": "HTML",
                  "disable_web_page_preview": "false"}

        if media_path and os.path.isfile(media_path):
            fields["caption"] = text
            result, err = self._send("sendPhoto", fields, files={"photo": media_path})
            if err:
                print(f"    ⚠ Telegram-Foto abgelehnt ({err}) – sende Text.")
                result, err = self._send("sendMessage",
                                         {"chat_id": self.chat_id, "text": text,
                                          "parse_mode": "HTML",
                                          "disable_web_page_preview": "false"})
        else:
            if self.media_cfg.get("required"):
                return failed("Bildpflicht nicht erfüllt (Cover fehlt)")
            fields["text"] = text
            result, err = self._send("sendMessage", fields)

        if err:
            return failed(err)
        msg_id = str((result or {}).get("message_id") or "")
        return PublishResult(ok=True, url=_msg_url(self.chat_id, msg_id), ref=msg_id)


def _msg_url(chat_id: str, msg_id: str) -> str:
    if not msg_id:
        return ""
    if chat_id.startswith("@"):
        return f"https://t.me/{chat_id[1:]}/{msg_id}"
    # Numerische Chat-IDs sind im Web nicht direkt verlinkbar (Privacy).
    return ""
