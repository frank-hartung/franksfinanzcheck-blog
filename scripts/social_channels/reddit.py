#!/usr/bin/env python3
# ============================================================
#  ADAPTER: REDDIT
#  ------------------------------------------------------------
#  API: oauth.reddit.com/api/submit (OAuth2 „script"-App)
#  KOMMUNITÄTS-REGELN (hier technisch abgesichert):
#    - maximal EIN Beitrag pro Tag (cadence.max_per_day = 1)
#    - nie am Erscheinungstag (launch_delay_hours = 72)
#    - Standardziel ist das EIGENE PROFIL (u/<user>) – sicher, weil
#      dort keine Community-Regeln gegen Eigenwerbung verletzt werden.
#      Ein Subreddit darf nur bewusst gesetzt werden (REDDIT_SUBREDDIT)
#      und nur, wenn dessen Regeln Eigenwerbung zulassen.
#    - keine Hashtags, keine Emojis, keine Werbesprache (Gate)
# ============================================================
from __future__ import annotations

import base64
import json
import urllib.parse

from . import ChannelAdapter, PublishResult, failed, http_json, http_request, register, skipped

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API = "https://oauth.reddit.com"


@register("reddit")
class RedditAdapter(ChannelAdapter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client_id = self.env("REDDIT_CLIENT_ID")
        self.client_secret = self.env("REDDIT_CLIENT_SECRET")
        self.username = self.env("REDDIT_USERNAME")
        self.password = self.env("REDDIT_PASSWORD")
        self.subreddit = self.env("REDDIT_SUBREDDIT") or (f"u_{self.username}" if self.username else "")
        self._token = ""

    def configured(self) -> tuple[bool, str]:
        missing = [k for k, v in (("REDDIT_CLIENT_ID", self.client_id),
                                  ("REDDIT_CLIENT_SECRET", self.client_secret),
                                  ("REDDIT_USERNAME", self.username),
                                  ("REDDIT_PASSWORD", self.password)) if not v]
        if missing:
            return False, f"{', '.join(missing)} fehlen"
        return True, ""

    def _login(self) -> str:
        if self._token:
            return self._token
        basic = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        body = urllib.parse.urlencode({
            "grant_type": "password",
            "username": self.username,
            "password": self.password,
        }).encode("utf-8")
        status, data, err = http_json(
            TOKEN_URL, data=body,
            headers={"Authorization": f"Basic {basic}",
                     "Content-Type": "application/x-www-form-urlencoded",
                     "User-Agent": "FranksFinanzcheck-SocialAutopilot/1.0 (by /u/%s)"
                                   % (self.username or "bot")},
            retries=2)
        if err or not isinstance(data, dict) or not data.get("access_token"):
            return ""
        self._token = data["access_token"]
        return self._token

    def publish(self, item: dict) -> PublishResult:
        ok, reason = self.configured()
        if not ok:
            return skipped(reason)
        token = self._login()
        if not token:
            return failed("Reddit-Login fehlgeschlagen (Script-App prüfen)")
        if not self.subreddit:
            return failed("Kein Ziel: REDDIT_SUBREDDIT oder REDDIT_USERNAME setzen")

        title = (item.get("headline") or item.get("title") or "")[: int(
            self.text_cfg.get("title_max_chars", 300))]
        body = (item.get("text") or "")[: int(self.text_cfg.get("max_chars", 40000))]
        link = item.get("url") or ""

        # Selbstpost mit Quellenlink: die ehrlichste Form auf Reddit.
        if link and link not in body:
            body = f"{body.rstrip()}\n\nAlle Details und Quellen: {link}"

        payload = {
            "sr": self.subreddit,
            "kind": "self",
            "title": title,
            "text": body,
            "api_type": "json",
            "resubmit": "true",
        }
        status, data, err = http_json(
            f"{API}/api/submit",
            data=urllib.parse.urlencode(payload).encode("utf-8"),
            headers={"Authorization": f"bearer {token}",
                     "Content-Type": "application/x-www-form-urlencoded",
                     "User-Agent": "FranksFinanzcheck-SocialAutopilot/1.0 (by /u/%s)"
                                   % (self.username or "bot")},
            retries=2)
        if err:
            return failed(err)
        errors = (((data or {}).get("json") or {}).get("errors") or [])
        if errors:
            return failed("Reddit: " + "; ".join(str(e) for e in errors[:2]))
        url = (((data or {}).get("json") or {}).get("data") or {}).get("url") or ""
        return PublishResult(ok=True, url=url, ref=url)
