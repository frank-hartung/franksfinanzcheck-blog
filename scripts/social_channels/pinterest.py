#!/usr/bin/env python3
# ============================================================
#  ADAPTER: PINTEREST (Refresh-Pins)
#  ------------------------------------------------------------
#  ARBEITSTEILUNG (bewusst – die Erstverpinnung ist hart erprobt):
#    · NEUE Artikel pinnt weiterhin pinterest_engine.py
#      (pinterest-ai.yml) – inkl. Anti-Spam-Taktung, Link-Heiler und
#      Board-Routing. Dort sitzt die Erfahrung aus der Spam-Sperre.
#    · Dieser Adapter übernimmt die REFRESH-Pins: Artikel, die älter
#      als `min_article_age_days` (Default 45) sind, bekommen einen
#      neuen Pin mit NEUEM Text und NEUEM Winkel – genau der Job,
#      den pinterest_engine.py bisher nur als Vorschlag meldete.
#
#  API: api.pinterest.com/v5/pins (Token über den Broker
#  scripts/pinterest_token.py, erneuert sich selbst).
#  Board: PINTEREST_BOARD_ID oder Live-Auflösung über die
#  Pillar-Zuordnung aus data/pinterest_boards.yaml (gecacht).
# ============================================================
from __future__ import annotations

import json
import os
import urllib.parse

from . import (ChannelAdapter, PublishResult, failed, http_json, register,
               skipped)

API = "https://api.pinterest.com/v5"
BOARD_CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data", "social", "pinterest_boards_cache.json")


@register("pinterest")
class PinterestAdapter(ChannelAdapter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = ""
        self.board_id = self.env("PINTEREST_BOARD_ID")

    def configured(self) -> tuple[bool, str]:
        token = self._token()
        if not token:
            return False, "kein lebender Pinterest-Token (pinterest_token.py)"
        return True, ""

    def _token(self) -> str:
        if self.token:
            return self.token
        try:
            import pinterest_token
            self.token = pinterest_token.get_token() or ""
        except Exception as exc:  # noqa: BLE001
            print(f"  ⚠ Pinterest-Token-Broker nicht verfügbar: {exc}")
            self.token = ""
        return self.token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"}

    # -- Board --------------------------------------------------------------
    def _load_cache(self) -> dict:
        try:
            with open(BOARD_CACHE, encoding="utf-8") as fh:
                return json.load(fh) or {}
        except Exception:  # noqa: BLE001
            return {}

    def _save_cache(self, data: dict) -> None:
        try:
            os.makedirs(os.path.dirname(BOARD_CACHE), exist_ok=True)
            with open(BOARD_CACHE, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def _live_boards(self) -> dict:
        status, data, err = http_json(f"{API}/boards?page_size=100",
                                      headers=self._headers(), method="GET")
        boards = {}
        if isinstance(data, dict):
            for b in data.get("items") or []:
                name = (b.get("name") or "").strip().lower()
                if name and b.get("id"):
                    boards[name] = b["id"]
        if boards:
            self._save_cache(boards)
        return boards

    def resolve_board(self, pillar: str) -> str:
        if self.board_id:
            return self.board_id
        boards = self._load_cache() or self._live_boards()
        target = _board_name_for_pillar(pillar)
        if target and target.strip().lower() in boards:
            return boards[target.strip().lower()]
        if boards:
            return list(boards.values())[0]
        return ""

    # -- Senden -------------------------------------------------------------
    def publish(self, item: dict) -> PublishResult:
        ok, reason = self.configured()
        if not ok:
            return skipped(reason)

        board = self.resolve_board((item.get("article") or {}).get("pillar") or "")
        if not board:
            return failed("Kein Pinterest-Board auflösbar (PINTEREST_BOARD_ID setzen)")

        media_url = item.get("media_url") or ""
        if not str(media_url).startswith("https://"):
            return failed("Pinterest braucht eine öffentliche HTTPS-Bild-URL")

        title = (item.get("headline") or "")[: int(self.text_cfg.get("title_max_chars", 100))]
        payload = {
            "board_id": board,
            "title": title,
            "description": (item.get("text") or "")[: int(self.text_cfg.get("max_chars", 500))],
            "link": item.get("url") or "",
            "media_source": {"source_type": "image_url", "url": media_url},
        }
        status, data, err = http_json(f"{API}/pins",
                                      data=json.dumps(payload).encode("utf-8"),
                                      headers=self._headers())
        if err:
            return failed(err)
        pin_id = (data or {}).get("id") or ""
        if not pin_id:
            return failed("Pinterest ohne Pin-ID")
        return PublishResult(ok=True, url=f"https://www.pinterest.de/pin/{pin_id}/", ref=pin_id)


def _board_name_for_pillar(pillar: str) -> str:
    """Pillar → Board-Name aus data/pinterest_boards.yaml."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "data", "pinterest_boards.yaml")
    if not (pillar and os.path.isfile(path)):
        return ""
    try:
        import yaml

        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        for board in (data.get("boards") or []):
            if pillar in (board.get("pillars") or []):
                return board.get("name") or ""
    except Exception:  # noqa: BLE001
        return ""
    return ""
