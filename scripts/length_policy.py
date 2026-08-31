#!/usr/bin/env python3
# ============================================================
#  LENGTH-POLICY – Single Source of Truth (Premium 31.08.2026)
#
#  Google (YMYL-Finance 2026): Top-10-Seiten in Vergleichs-/Ratgeber-
#  Queries liegen typisch bei 1.500–2.500 Wörtern. Wortzahl ist KEIN
#  Rankingfaktor – Tiefe ist es. Unter ~10.000 Zeichen Fließtext gilt
#  ein Check24-/Tarif-Artikel gegen Portale als dünn (Thin/Affiliate-
#  Filter, Scaled-Content-Risiko).
#
#  Pinterest: Pin-Ranking läuft über Titel (≤100, opt. 40–60) und
#  Description (≤500, opt. 220–480). Die LANDINGPAGE entscheidet über
#  Dwell-Time/Outbound-Qualität – deshalb derselbe Body-Korridor.
#
#  Hoheit:
#    posts  → check_length.py + length_guard.py (dieser Korridor)
#    pillar → length_guard.py --scope pillar
# ============================================================
from __future__ import annotations

import os
import re
from pathlib import Path

# --- Body (Artikel / Pillar) --------------------------------
POSTS = {
    "target_min_chars": int(os.environ.get("LENGTH_MIN_CHARS") or 10000),
    "opt_min_chars": int(os.environ.get("LENGTH_OPT_CHARS_MIN") or 12000),
    "opt_max_chars": int(os.environ.get("LENGTH_OPT_CHARS_MAX") or 18000),
    "target_max_chars": int(os.environ.get("LENGTH_MAX_CHARS") or 18000),
    "warn_chars": int(os.environ.get("LENGTH_WARN_CHARS") or 10000),
    "heal_chars": int(os.environ.get("LENGTH_HEAL_CHARS") or 10000),
    "fat_chars": int(os.environ.get("LENGTH_FAT_CHARS") or 22000),
}

PILLAR = {
    "target_min_chars": int(os.environ.get("PILLAR_MIN_CHARS") or 12000),
    "opt_min_chars": int(os.environ.get("PILLAR_OPT_CHARS_MIN") or 15000),
    "opt_max_chars": int(os.environ.get("PILLAR_OPT_CHARS_MAX") or 32000),
    "target_max_chars": int(os.environ.get("PILLAR_MAX_CHARS") or 32000),
    "warn_chars": int(os.environ.get("PILLAR_WARN_CHARS") or 15000),
    "heal_chars": int(os.environ.get("PILLAR_HEAL_CHARS") or 12000),
    "fat_chars": int(os.environ.get("PILLAR_FAT_CHARS") or 38000),
}

POLICY = {"posts": POSTS, "pillar": PILLAR}

# Deutsche Faustregel: ~7 Zeichen/Wort (Bestand Median 6,96)
CHARS_PER_WORD = 7.0

# --- Pinterest Pin-Felder -----------------------------------
PIN_TITLE_MIN, PIN_TITLE_OPT, PIN_TITLE_MAX = 40, 60, 100
PIN_DESC_MIN, PIN_DESC_OPT_MIN, PIN_DESC_OPT_MAX, PIN_DESC_MAX = 220, 280, 480, 500

# --- Google SERP --------------------------------------------
TITLE_MIN, TITLE_MAX = 30, 60
META_DESC_OPT_MIN, META_DESC_OPT_MAX = 120, 160

MARKER = "<!-- premium-length-2026 -->"


def classify(path: Path | str) -> str:
    parts = Path(path).parts
    return "pillar" if "pillar" in parts else "posts"


def policy_for(path: Path | str) -> dict:
    return POLICY[classify(path)]


def measure(text: str) -> tuple[int, int]:
    """Wörter & Zeichen des Artikels (ohne Front-Matter/Code/Tabellen-Sep)."""
    t = text
    if t.startswith("---"):
        parts = t.split("---", 2)
        if len(parts) >= 3:
            t = parts[2]
    t = re.sub(r"```.*?```", "", t, flags=re.S)
    t = re.sub(r"^[-| :]+$", "", t, flags=re.M)
    chars = len(re.sub(r"\s+", " ", t).strip())
    words = len(re.sub(r"[|#*>\[\]()]", " ", t).split())
    return words, chars


def status_of(chars: int, typ: str = "posts") -> str:
    pol = POLICY[typ]
    if chars < pol["heal_chars"]:
        return "heilen"
    if chars < pol["warn_chars"] or chars < pol["opt_min_chars"]:
        return "kurz"
    if chars > pol["fat_chars"]:
        return "lang"
    if chars > pol["opt_max_chars"]:
        return "ok-lang"
    return "ok"


def corridor_label(typ: str = "posts") -> str:
    p = POLICY[typ]
    def de(n: int) -> str:
        return f"{n:,}".replace(",", ".")
    return (
        f"{de(p['opt_min_chars'])}–{de(p['opt_max_chars'])} Zeichen "
        f"(Floor {de(p['target_min_chars'])}, heil < {de(p['heal_chars'])})"
    )
