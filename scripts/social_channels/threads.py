#!/usr/bin/env python3
# ============================================================
#  ADAPTER: THREADS (Meta)
#  ------------------------------------------------------------
#  API: graph.threads.net/v1.0 – ZWEI Schritte sind Pflicht:
#    1) Container anlegen  POST /{user_id}/threads
#    2) veröffentlichen    POST /{user_id}/threads_publish
#  Bei Bildern muss der Container erst den Status FINISHED haben –
#  darum wird kurz pollingweise geprüft (max. 6 × 5 s).
#  Threads-Reihen: `reply_to_id` verweist auf den Vorgänger-Container.
# ============================================================
from __future__ import annotations

import json
import os
import time
import urllib.parse

from . import ChannelAdapter, PublishResult, failed, http_json, register, skipped

API = "https://graph.threads.net/v1.0"


@register("threads")
class ThreadsAdapter(ChannelAdapter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = self.env("THREADS_ACCESS_TOKEN")
        self.user_id = self.env("THREADS_USER_ID")

    def configured(self) -> tuple[bool, str]:
        if not self.token:
            return False, "THREADS_ACCESS_TOKEN fehlt"
        if not self.user_id:
            return False, "THREADS_USER_ID fehlt"
        return True, ""

    def _create(self, text: str, image_url: str = "", reply_to: str = "") -> tuple[str, str]:
        fields = {
            "media_type": "IMAGE" if image_url else "TEXT",
            "text": text,
            "access_token": self.token,
        }
        if image_url:
            fields["image_url"] = image_url
        if reply_to:
            fields["reply_to_id"] = reply_to
        status, data, err = http_json(
            f"{API}/{self.user_id}/threads",
            data=urllib.parse.urlencode(fields).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        if err or not isinstance(data, dict) or not data.get("id"):
            return "", err or "Container ohne ID"
        return str(data["id"]), ""

    def _wait_finished(self, cid: str) -> bool:
        for _ in range(6):
            status, data, err = http_json(
                f"{API}/{cid}?fields=status&access_token={urllib.parse.quote(self.token)}",
                method="GET")
            if not err and isinstance(data, dict):
                st = (data.get("status") or "").upper()
                if st in ("FINISHED", "PUBLISHED"):
                    return True
                if st in ("ERROR", "EXPIRED"):
                    return False
            time.sleep(5)
        return False  # lieber ohne Bild posten als endlos warten

    def _publish_container(self, cid: str) -> tuple[str, str]:
        status, data, err = http_json(
            f"{API}/{self.user_id}/threads_publish",
            data=urllib.parse.urlencode({"creation_id": cid,
                                         "access_token": self.token}).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        if err or not isinstance(data, dict) or not data.get("id"):
            return "", err or "Veröffentlichung ohne ID"
        return str(data["id"]), ""

    def publish(self, item: dict) -> PublishResult:
        ok, reason = self.configured()
        if not ok:
            return skipped(reason)

        image_url = item.get("media_url") or ""
        if not image_url and self.media_cfg.get("required"):
            return failed("Bildpflicht nicht erfüllt (Cover-URL fehlt)")
        if image_url and not str(image_url).startswith("http"):
            image_url = ""

        parts = item.get("thread") or []
        if parts and self.supports_threads:
            last_id, last_container = "", ""
            for i, part in enumerate(parts[: int((self.text_cfg.get("thread") or {}).get("max_parts", 4))]):
                cid, err = self._create(part, image_url if i == 0 else "", last_container)
                if err:
                    if i == 0:
                        return failed(err)
                    print(f"    ⚠ Thread bei Teil {i + 1} abgebrochen: {err}")
                    break
                if i == 0 and image_url:
                    self._wait_finished(cid)
                pid, perr = self._publish_container(cid)
                if perr:
                    if i == 0:
                        return failed(perr)
                    break
                last_id, last_container = pid, cid
            if last_id:
                return PublishResult(ok=True, url=_permalink(last_id), ref=last_id)
            return failed("Thread ohne bestätigten Post")

        cid, err = self._create(item.get("text", ""), image_url)
        if err:
            return failed(err)
        if image_url and not self._wait_finished(cid):
            print("    ⚠ Bild-Container nicht rechtzeitig fertig – poste als Text.")
            cid2, err2 = self._create(item.get("text", ""))
            if err2:
                return failed(err2)
            cid = cid2
        pid, perr = self._publish_container(cid)
        if perr:
            return failed(perr)
        return PublishResult(ok=True, url=_permalink(pid), ref=pid)


def _permalink(post_id: str) -> str:
    return f"https://www.threads.net/post/{post_id}" if post_id else ""
