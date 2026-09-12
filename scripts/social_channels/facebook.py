#!/usr/bin/env python3
# ============================================================
#  ADAPTER: FACEBOOK (Seite)
#  ------------------------------------------------------------
#  API: graph.facebook.com/v20.0
#    - Textpost + Link-Vorschau: POST /{page_id}/feed
#    - Bildpost:                POST /{page_id}/photos
#  Ein Bildpost mit Link im Text performt in der Regel besser als ein
#  reiner Linkpost – deshalb wird das Cover bevorzugt als Foto gesendet
#  und die URL in den Text geschrieben (Facebook baut daraus eine
#  klickbare Vorschau).
# ============================================================
from __future__ import annotations

import json
import os
import urllib.parse

from . import ChannelAdapter, PublishResult, failed, http_json, register, skipped

GRAPH = "https://graph.facebook.com/v20.0"


@register("facebook")
class FacebookAdapter(ChannelAdapter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = self.env("FACEBOOK_PAGE_TOKEN")
        self.page_id = self.env("FACEBOOK_PAGE_ID")

    def configured(self) -> tuple[bool, str]:
        if not self.token:
            return False, "FACEBOOK_PAGE_TOKEN fehlt"
        if not self.page_id:
            return False, "FACEBOOK_PAGE_ID fehlt"
        return True, ""

    def publish(self, item: dict) -> PublishResult:
        ok, reason = self.configured()
        if not ok:
            return skipped(reason)

        text = (item.get("text") or "")[: int(self.text_cfg.get("max_chars", 1200))]
        link = item.get("url") or ""
        media_url = item.get("media_url") or ""

        if media_url and str(media_url).startswith("http"):
            fields = {"url": media_url, "caption": text, "access_token": self.token}
            status, data, err = http_json(
                f"{GRAPH}/{self.page_id}/photos",
                data=urllib.parse.urlencode(fields).encode("utf-8"),
                headers={"Content-Type": "application/x-www-form-urlencoded"})
            if err:
                # Fallback: reiner Linkpost (kein Bild) statt Abbruch.
                print(f"    ⚠ Facebook-Foto abgelehnt ({err}) – sende Linkpost.")
            elif isinstance(data, dict) and data.get("id"):
                return PublishResult(ok=True, url=_post_url(data.get("post_id") or data["id"]),
                                     ref=str(data["id"]))

        if not link:
            return failed("Weder Bild noch Link übermittelbar")
        fields = {"message": text, "link": link, "access_token": self.token}
        status, data, err = http_json(
            f"{GRAPH}/{self.page_id}/feed",
            data=urllib.parse.urlencode(fields).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        if err:
            return failed(err)
        if not isinstance(data, dict) or not data.get("id"):
            return failed("Facebook ohne Post-ID")
        return PublishResult(ok=True, url=_post_url(data["id"]), ref=str(data["id"]))


def _post_url(post_id: str) -> str:
    pid = str(post_id or "")
    if "_" in pid:
        page, rest = pid.split("_", 1)
        return f"https://www.facebook.com/{page}/posts/{rest}"
    return f"https://www.facebook.com/{pid}" if pid else ""
