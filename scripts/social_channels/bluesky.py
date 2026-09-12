#!/usr/bin/env python3
# ============================================================
#  ADAPTER: BLUESKY (AT-Protokoll)
#  ------------------------------------------------------------
#  API: com.atproto.server.createSession → com.atproto.repo.createRecord
#  Besonderheiten:
#    - 300 Graphem (URL zählt voll mit) → härteste Kürze im Portfolio
#    - Links und Hashtags werden als FACETS übertragen (Byte-Offsets!) –
#      nur so werden sie klickbar bzw. suchbar gerendert
#    - Bilder über uploadBlob + embed, Alt-Text ist Pflicht (A11y)
#    - Threads = Reply-Kette mit root/parent-Referenz
# ============================================================
from __future__ import annotations

import json
import mimetypes
import os
import re

from . import ChannelAdapter, PublishResult, failed, http_json, register, skipped

DEFAULT_PDS = "https://bsky.social"


def _byte_offsets(text: str, needle: str) -> tuple[int, int]:
    """Byte-Offsets eines Teilstrings (Bluesky zählt UTF-8-Bytes)."""
    start = text.find(needle)
    if start < 0:
        return -1, -1
    b_start = len(text[:start].encode("utf-8"))
    return b_start, b_start + len(needle.encode("utf-8"))


def build_facets(text: str) -> list[dict]:
    """Erzeugt Link- und Tag-Facets für einen Text."""
    facets: list[dict] = []
    for m in re.finditer(r"https?://[^\s]+", text):
        b0, b1 = _byte_offsets(text, m.group(0))
        if b0 >= 0:
            facets.append({"index": {"byteStart": b0, "byteEnd": b1},
                           "features": [{"$type": "app.bsky.richtext.facet#link",
                                         "uri": m.group(0)}]})
    for m in re.finditer(r"(?<!\w)#([A-Za-z0-9ÄÖÜäöüß_]+)", text):
        b0, b1 = _byte_offsets(text, m.group(0))
        if b0 >= 0:
            facets.append({"index": {"byteStart": b0, "byteEnd": b1},
                           "features": [{"$type": "app.bsky.richtext.facet#tag",
                                         "tag": m.group(1)}]})
    return facets


@register("bluesky")
class BlueskyAdapter(ChannelAdapter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pds = (os.environ.get("BLUESKY_PDS") or DEFAULT_PDS).strip().rstrip("/")
        self.identifier = (os.environ.get("BLUESKY_IDENTIFIER") or "").strip()
        self.password = (os.environ.get("BLUESKY_APP_PASSWORD") or "").strip()
        self._session: dict | None = None

    def configured(self) -> tuple[bool, str]:
        if not self.identifier or not self.password:
            return False, "BLUESKY_IDENTIFIER / BLUESKY_APP_PASSWORD fehlen"
        return True, ""

    def _login(self) -> tuple[dict | None, str]:
        if self._session:
            return self._session, ""
        payload = json.dumps({"identifier": self.identifier,
                              "password": self.password}).encode("utf-8")
        status, data, err = http_json(f"{self.pds}/xrpc/com.atproto.server.createSession",
                                      data=payload,
                                      headers={"Content-Type": "application/json"},
                                      retries=2)
        if err or not isinstance(data, dict) or not data.get("accessJwt"):
            return None, err or f"Login fehlgeschlagen (HTTP {status})"
        self._session = data
        return data, ""

    def _auth(self, session: dict) -> dict:
        return {"Authorization": f"Bearer {session['accessJwt']}",
                "Content-Type": "application/json"}

    def _upload_blob(self, session: dict, path: str) -> tuple[dict | None, str]:
        try:
            with open(path, "rb") as fh:
                blob = fh.read()
        except OSError as exc:
            return None, f"Bild nicht lesbar ({exc})"
        ctype = mimetypes.guess_type(path)[0] or "image/jpeg"
        status, data, err = http_json(
            f"{self.pds}/xrpc/com.atproto.repo.uploadBlob",
            data=blob,
            headers={"Authorization": f"Bearer {session['accessJwt']}",
                     "Content-Type": ctype},
            retries=2)
        if err or not isinstance(data, dict) or not (data.get("blob") or {}).get("$type"):
            return None, err or "Blob-Upload ohne Antwort"
        return data["blob"], ""

    def _create_post(self, session: dict, text: str, embed: dict | None = None,
                     reply: dict | None = None) -> tuple[dict | None, str]:
        did = session.get("did")
        record = {
            "$type": "app.bsky.feed.post",
            "text": text,
            "createdAt": _now_iso(),
            "langs": ["de"],
        }
        facets = build_facets(text)
        if facets:
            record["facets"] = facets
        if embed:
            record["embed"] = embed
        if reply:
            record["reply"] = reply
        payload = json.dumps({"repo": did, "collection": "app.bsky.feed.post",
                              "record": record}).encode("utf-8")
        status, data, err = http_json(
            f"{self.pds}/xrpc/com.atproto.repo.createRecord",
            data=payload, headers=self._auth(session))
        if err or not isinstance(data, dict):
            return None, err or f"Post fehlgeschlagen (HTTP {status})"
        return data, ""

    def publish(self, item: dict) -> PublishResult:
        ok, reason = self.configured()
        if not ok:
            return skipped(reason)
        session, err = self._login()
        if not session:
            return failed(err or "Bluesky-Login fehlgeschlagen")

        embed = None
        media_path = item.get("media_path")
        if media_path and os.path.isfile(media_path):
            blob, berr = self._upload_blob(session, media_path)
            if blob:
                embed = {"$type": "app.bsky.embed.images",
                         "images": [{"alt": (item.get("alt") or "")[:900], "image": blob}]}
            elif berr:
                print(f"    ⚠ Bluesky-Bild abgelehnt ({berr}) – poste als Text.")
        elif self.media_cfg.get("required"):
            return failed("Bildpflicht nicht erfüllt (Cover fehlt)")

        parts = item.get("thread") or []
        if parts and self.supports_threads:
            root = parent = None
            last_uri = ""
            for i, part in enumerate(parts[: int((self.text_cfg.get("thread") or {}).get("max_parts", 4))]):
                reply = None
                if root:
                    reply = {"root": root, "parent": parent}
                data, cerr = self._create_post(session, part, embed if i == 0 else None, reply)
                if cerr:
                    if i == 0:
                        return failed(cerr)
                    print(f"    ⚠ Thread bei Teil {i + 1} abgebrochen: {cerr}")
                    break
                uri = data.get("uri") or ""
                cid = data.get("cid") or ""
                if not root:
                    root = {"uri": uri, "cid": cid}
                parent = {"uri": uri, "cid": cid}
                last_uri = uri
            if last_uri:
                return PublishResult(ok=True, url=_permalink(session, last_uri), ref=last_uri)
            return failed("Thread ohne bestätigten Post")

        data, err = self._create_post(session, item.get("text", ""), embed)
        if err:
            return failed(err)
        uri = data.get("uri") or ""
        return PublishResult(ok=True, url=_permalink(session, uri), ref=uri)

    def comment(self, target: str, text: str) -> PublishResult:
        ok, reason = self.configured()
        if not ok:
            return skipped(reason)
        session, err = self._login()
        if not session:
            return failed(err or "Bluesky-Login fehlgeschlagen")
        if not (target or "").startswith("at://"):
            return failed("Keine gültige Post-URI für den Zweitpost")
        root = parent = {"uri": target, "cid": ""}
        data, err = self._create_post(session, text, None, {"root": root, "parent": parent})
        if err:
            return failed(err)
        return PublishResult(ok=True, url=_permalink(session, data.get("uri") or ""),
                             ref=data.get("uri") or "")


def _permalink(session: dict, uri: str) -> str:
    """at://did:plc:…/app.bsky.feed.post/xyz → https://bsky.app/profile/…/post/xyz"""
    if not uri:
        return ""
    try:
        did = uri.split("/")[2]
        rkey = uri.rsplit("/", 1)[-1]
        handle = (session or {}).get("handle") or did
        return f"https://bsky.app/profile/{handle}/post/{rkey}"
    except Exception:  # noqa: BLE001
        return ""


def _now_iso() -> str:
    import datetime

    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
