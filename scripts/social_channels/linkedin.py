#!/usr/bin/env python3
# ============================================================
#  ADAPTER: LINKEDIN
#  ------------------------------------------------------------
#  API: /v2/ugcPosts (Text + Bild), /v2/socialActions/{urn}/comments
#  Agentur-Regeln, die hier technisch umgesetzt sind:
#    - Link in den ERSTEN KOMMENTAR (LinkedIn bestraft externe Links
#      im Hauptpost mit Reichweitenverlust) – konfigurierbar über
#      text.link_position = "first_comment"
#    - Keine Emojis, Whitespace-reiche Absätze (Gate setzt das durch)
#    - Bild-Upload über das 3-Schritt-Register-Upload-Verfahren;
#      schlägt der Upload fehl, wird als reiner Textpost gesendet
#      (besser gesendet als gar nicht – der Lauf bleibt heil)
# ============================================================
from __future__ import annotations

import json
import os
import urllib.parse

from . import ChannelAdapter, PublishResult, failed, http_json, http_request, register, skipped

API = "https://api.linkedin.com/v2"


@register("linkedin")
class LinkedInAdapter(ChannelAdapter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = self.env("LINKEDIN_ACCESS_TOKEN")
        self.person = self.env("LINKEDIN_PERSON_URN")
        self.org = self.env("LINKEDIN_ORG_URN")
        self.author = self.org or self.person

    def configured(self) -> tuple[bool, str]:
        if not self.token:
            return False, "LINKEDIN_ACCESS_TOKEN fehlt"
        if not self.author:
            return False, "LINKEDIN_PERSON_URN oder LINKEDIN_ORG_URN fehlt"
        return True, ""

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0"}

    # -- Bild ---------------------------------------------------------------
    def _register_upload(self) -> tuple[str, str, str]:
        """Meldet ein Bild an → (asset_urn, upload_url, fehler)."""
        payload = json.dumps({
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": self.author,
                "serviceRelationships": [
                    {"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}
                ],
            }
        }).encode("utf-8")
        status, data, err = http_json(f"{API}/assets?action=registerUpload",
                                      data=payload, headers=self._headers(), retries=2)
        if err or not isinstance(data, dict):
            return "", "", err or "registerUpload ohne Antwort"
        value = data.get("value") or {}
        asset = value.get("asset") or ""
        mech = (value.get("uploadMechanism") or {}).get(
            "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest") or {}
        upload_url = mech.get("uploadUrl") or ""
        if not asset or not upload_url:
            return "", "", "registerUpload unvollständig"
        return asset, upload_url, ""

    def _upload_image(self, path: str) -> tuple[str, str]:
        asset, upload_url, err = self._register_upload()
        if err:
            return "", err
        try:
            with open(path, "rb") as fh:
                blob = fh.read()
        except OSError as exc:
            return "", f"Bild nicht lesbar ({exc})"
        status, _, err2 = http_request(upload_url, data=blob, method="PUT",
                                       headers={"Authorization": f"Bearer {self.token}"},
                                       timeout=90, retries=2)
        if err2 or status >= 400:
            return "", err2 or f"Bild-Upload HTTP {status}"
        return asset, ""

    # -- Senden -------------------------------------------------------------
    def publish(self, item: dict) -> PublishResult:
        ok, reason = self.configured()
        if not ok:
            return skipped(reason)

        link = item.get("url") or ""
        text = item.get("text") or ""
        media_asset = ""

        media_path = item.get("media_path")
        if media_path and os.path.isfile(media_path) and self.media_cfg.get("supported", True):
            media_asset, merr = self._upload_image(media_path)
            if merr:
                print(f"    ⚠ LinkedIn-Bild abgelehnt ({merr}) – sende Textpost.")

        if media_asset:
            content = {
                "shareMediaCategory": "IMAGE",
                "media": [{"status": "READY", "media": media_asset,
                           "title": {"text": (item.get("headline") or "")[:200]}}],
            }
        elif link and self.link_position != "first_comment":
            content = {
                "shareMediaCategory": "ARTICLE",
                "media": [{"status": "READY", "originalUrl": link,
                           "title": {"text": (item.get("headline") or "")[:200]}}],
            }
        else:
            content = {"shareMediaCategory": "NONE"}

        payload = {
            "author": self.author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {"com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text[: int(self.text_cfg.get("max_chars", 2900))]},
                "shareMediaCategory": content["shareMediaCategory"],
            }},
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }
        payload["specificContent"]["com.linkedin.ugc.ShareContent"].update(content)

        status, data, err = http_json(f"{API}/ugcPosts",
                                      data=json.dumps(payload).encode("utf-8"),
                                      headers=self._headers())
        if err:
            return failed(err)
        share_id = (data or {}).get("id") or ""
        if not share_id:
            return failed("LinkedIn ohne Post-ID (unerwartete Antwort)")
        url = f"https://www.linkedin.com/feed/update/{share_id}"

        # Link in den ersten Kommentar (Reichweiten-Standard)
        if self.link_position == "first_comment" and link:
            c_text = (item.get("comment") or f"Alle Details und Rechenbeispiele: {link}")
            cres = self.comment(share_id, c_text)
            if not cres.ok:
                print(f"    ⚠ Erstkommentar fehlgeschlagen ({cres.error}) – Post steht.")

        return PublishResult(ok=True, url=url, ref=share_id)

    def comment(self, target: str, text: str) -> PublishResult:
        ok, reason = self.configured()
        if not ok:
            return skipped(reason)
        urn = urllib.parse.quote(target, safe="")
        payload = json.dumps({
            "actor": self.author,
            "message": {"text": text[:1250]},
        }).encode("utf-8")
        status, data, err = http_json(
            f"{API}/socialActions/{urn}/comments",
            data=payload, headers=self._headers())
        if err:
            # Auch ein misslungener Kommentar darf den Hauptpost nicht entwerten.
            return failed(err)
        return PublishResult(ok=True, ref=(data or {}).get("id") or "", url="")
