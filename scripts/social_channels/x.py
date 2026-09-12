#!/usr/bin/env python3
# ============================================================
#  ADAPTER: X (Twitter)
#  ------------------------------------------------------------
#  API: POST /2/tweets, Upload via upload.twitter.com
#  Auth: OAuth 1.0a (User Context) – HMAC-SHA1-Signatur, hier mit
#  Bordmitteln (hmac/hashlib/base64) gebaut, damit keine
#  Drittanbieter-Bibliothek nötig ist.
#  Kanal-Logik: 280 Zeichen, maximal 2 Hashtags, Thread = Reply-Kette.
# ============================================================
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import urllib.parse
import uuid

from . import ChannelAdapter, PublishResult, failed, http_json, http_request, register, skipped

API = "https://api.twitter.com/2"
UPLOAD = "https://upload.twitter.com/1.1/media/upload.json"


def _pct(s: str) -> str:
    return urllib.parse.quote(str(s), safe="~")


def oauth1_header(method: str, url: str, consumer_key: str, consumer_secret: str,
                  token: str, token_secret: str, extra_params: dict | None = None) -> str:
    """Baut einen OAuth-1.0a-Authorization-Header (HMAC-SHA1)."""
    params = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": uuid.uuid4().hex,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": token,
        "oauth_version": "1.0",
    }
    params.update(extra_params or {})
    # Query-Parameter der URL gehören mit in die Signatur
    query = urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query, keep_blank_values=True)
    all_params = [(k, v) for k, v in params.items()] + query
    normalized = "&".join(
        f"{_pct(k)}={_pct(v)}" for k, v in sorted(all_params, key=lambda kv: (kv[0], kv[1]))
    )
    base = "&".join([method.upper(), _pct(url.split("?")[0]), _pct(normalized)])
    key = f"{_pct(consumer_secret)}&{_pct(token_secret)}".encode("utf-8")
    digest = hmac.new(key, base.encode("utf-8"), hashlib.sha1).digest()
    params["oauth_signature"] = base64.b64encode(digest).decode("utf-8")
    header = ", ".join(f'{_pct(k)}="{_pct(v)}"' for k, v in sorted(params.items()))
    return f"OAuth {header}"


@register("x")
class XAdapter(ChannelAdapter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ck = self.env("X_API_KEY")
        self.cs = self.env("X_API_SECRET")
        self.at = self.env("X_ACCESS_TOKEN")
        self.ats = self.env("X_ACCESS_SECRET")

    def configured(self) -> tuple[bool, str]:
        missing = [k for k, v in (("X_API_KEY", self.ck), ("X_API_SECRET", self.cs),
                                  ("X_ACCESS_TOKEN", self.at), ("X_ACCESS_SECRET", self.ats))
                   if not v]
        if missing:
            return False, f"{', '.join(missing)} fehlen"
        return True, ""

    def _auth(self, method: str, url: str, extra: dict | None = None) -> dict:
        return {"Authorization": oauth1_header(method, url, self.ck, self.cs,
                                               self.at, self.ats, extra),
                "Content-Type": "application/json"}

    def _upload_media(self, path: str, alt: str = "") -> tuple[str, str]:
        try:
            with open(path, "rb") as fh:
                blob = fh.read()
        except OSError as exc:
            return "", f"Bild nicht lesbar ({exc})"
        b64 = base64.b64encode(blob).decode("ascii")
        body = urllib.parse.urlencode({"media_data": b64}).encode("ascii")
        status, data, err = http_json(
            UPLOAD, data=body,
            headers={"Authorization": oauth1_header("POST", UPLOAD, self.ck, self.cs,
                                                    self.at, self.ats),
                     "Content-Type": "application/x-www-form-urlencoded"},
            timeout=90, retries=2)
        if err or not isinstance(data, dict):
            return "", err or "Media-Upload ohne Antwort"
        media_id = str(data.get("media_id_string") or data.get("media_id") or "")
        if not media_id:
            return "", "Media-Upload ohne ID"
        if alt:
            meta = json.dumps({"media_id": media_id,
                               "alt_text": {"text": alt[:1000]}}).encode("utf-8")
            http_json("https://upload.twitter.com/1.1/media/metadata/create.json",
                      data=meta,
                      headers={"Authorization": oauth1_header(
                          "POST", "https://upload.twitter.com/1.1/media/metadata/create.json",
                          self.ck, self.cs, self.at, self.ats),
                          "Content-Type": "application/json; charset=UTF-8"},
                      retries=1)
        return media_id, ""

    def _tweet(self, text: str, media_ids: list[str] | None = None,
               reply_to: str = "") -> tuple[dict | None, str]:
        payload: dict = {"text": text}
        if media_ids:
            payload["media"] = {"media_ids": media_ids}
        if reply_to:
            payload["reply"] = {"in_reply_to_tweet_id": reply_to}
        status, data, err = http_json(f"{API}/tweets",
                                      data=json.dumps(payload).encode("utf-8"),
                                      headers=self._auth("POST", f"{API}/tweets"))
        if err:
            return None, err
        if not isinstance(data, dict) or not (data.get("data") or {}).get("id"):
            return None, f"unerwartete Antwort (HTTP {status})"
        return data["data"], ""

    def publish(self, item: dict) -> PublishResult:
        ok, reason = self.configured()
        if not ok:
            return skipped(reason)

        media_ids: list[str] = []
        media_path = item.get("media_path")
        if media_path and os.path.isfile(media_path) and self.media_cfg.get("supported"):
            mid, merr = self._upload_media(media_path, item.get("alt") or "")
            if mid:
                media_ids.append(mid)
            elif merr:
                print(f"    ⚠ X-Bild abgelehnt ({merr}) – poste als Text.")
        elif self.media_cfg.get("required"):
            return failed("Bildpflicht nicht erfüllt (Cover fehlt)")

        parts = item.get("thread") or []
        if parts and self.supports_threads:
            reply_to = ""
            last_id = ""
            for i, part in enumerate(parts[: int((self.text_cfg.get("thread") or {}).get("max_parts", 5))]):
                data, err = self._tweet(part, media_ids if i == 0 else None, reply_to)
                if err:
                    if i == 0:
                        return failed(err)
                    print(f"    ⚠ Thread bei Teil {i + 1} abgebrochen: {err}")
                    break
                last_id = str(data.get("id") or "")
                reply_to = last_id
            if last_id:
                return PublishResult(ok=True, url=f"https://x.com/i/web/status/{last_id}", ref=last_id)
            return failed("Thread ohne bestätigten Tweet")

        data, err = self._tweet(item.get("text", ""), media_ids)
        if err:
            return failed(err)
        tid = str(data.get("id") or "")
        return PublishResult(ok=True, url=f"https://x.com/i/web/status/{tid}", ref=tid)
