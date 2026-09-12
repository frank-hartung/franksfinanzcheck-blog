#!/usr/bin/env python3
# ============================================================
#  ADAPTER: INSTAGRAM (Graph API, Business/Creator)
#  ------------------------------------------------------------
#  Zwei-Schritt-Verfahren (wie bei Threads, nur strenger):
#    1) Container  POST /{ig_user_id}/media (image_url + caption + alt_text)
#    2) publish    POST /{ig_user_id}/media_publish
#  HARTE KANAL-KRITERIEN, die hier durchgesetzt werden:
#    - OHNE Bild kein Post (Instagram ist ein Bildnetzwerk)
#    - Bild-URL muss ÖFFENTLICH per HTTPS erreichbar sein
#    - Seitenverhältnis 4:5 (1080×1350) bis 1,91:1 – unser Cover ist
#      2:3 und würde abgelehnt, deshalb rendert social_images.py eine
#      4:5-Variante (static/images/social/<slug>-ig.jpg)
#    - Captions dürfen KEINE klickbaren Links enthalten → CTA „Link in Bio"
# ============================================================
from __future__ import annotations

import time
import urllib.parse

from . import ChannelAdapter, PublishResult, failed, http_json, register, skipped

GRAPH = "https://graph.facebook.com/v20.0"


@register("instagram")
class InstagramAdapter(ChannelAdapter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = self.env("INSTAGRAM_ACCESS_TOKEN")
        self.account_id = self.env("INSTAGRAM_ACCOUNT_ID")

    def configured(self) -> tuple[bool, str]:
        if not self.token:
            return False, "INSTAGRAM_ACCESS_TOKEN fehlt"
        if not self.account_id:
            return False, "INSTAGRAM_ACCOUNT_ID fehlt"
        return True, ""

    def publish(self, item: dict) -> PublishResult:
        ok, reason = self.configured()
        if not ok:
            return skipped(reason)

        image_url = item.get("media_url") or ""
        if not str(image_url).startswith("https://"):
            return failed("Instagram braucht eine öffentliche HTTPS-Bild-URL")

        caption = (item.get("text") or "")[: int(self.text_cfg.get("max_chars", 2200))]
        fields = {
            "image_url": image_url,
            "caption": caption,
            "access_token": self.token,
        }
        alt = (item.get("alt") or "").strip()
        if alt:
            fields["alt_text"] = alt[: int(self.media_cfg.get("alt_max_chars", 900) or 900)]

        status, data, err = http_json(
            f"{GRAPH}/{self.account_id}/media",
            data=urllib.parse.urlencode(fields).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        if err or not isinstance(data, dict) or not data.get("id"):
            return failed(err or "Container ohne ID")
        container = str(data["id"])

        # Container kann noch in Verarbeitung sein – kurz warten, dann senden.
        for _ in range(4):
            pid, perr = self._publish(container)
            if pid:
                return PublishResult(ok=True, url=f"https://www.instagram.com/p/{pid}/",
                                     ref=pid)
            if perr and "not finished" in perr.lower():
                time.sleep(6)
                continue
            return failed(perr or "Veröffentlichung ohne ID")
        return failed("Bild-Container wurde nicht rechtzeitig fertig")

    def _publish(self, container: str) -> tuple[str, str]:
        status, data, err = http_json(
            f"{GRAPH}/{self.account_id}/media_publish",
            data=urllib.parse.urlencode({"creation_id": container,
                                         "access_token": self.token}).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        if err or not isinstance(data, dict) or not data.get("id"):
            return "", err or "Veröffentlichung ohne ID"
        return str(data["id"]), ""
