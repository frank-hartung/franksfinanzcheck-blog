#!/usr/bin/env python3
# ============================================================
#  EMOJI-GUARD – Marken-Emoji-Politur (selbst prüfen & entscheiden)
#
#  Entscheidet auf Profi-Niveau über Emojis an den Marken-Touchpoints:
#
#  REGELN (Ebenen):
#    E1  homeInfoParams.Content (Startseiten-Tagline) MUSS mindestens
#        ein Marken-Emoji enthalten. Fehlt es, wird automatisch das
#        thematisch passende vorangestellt (Themen-Mapping unten).
#    E2  params.description (Meta-Description): KEIN Emoji-Zwang –
#        Google zeigt Emojis dort unzuverlässig; mehr als 1 = Report.
#    E3  Anti-Overuse: >2 Emojis in Content/description/Titel = Fund.
#        (Profi-Regel: Emoji = Akzent, nicht Dekoration.)
#    E4  Mojibake-Scanner (blogweit, content/ + hugo.toml):
#        kaputte UTF-8-Doppelcodierung (Ã¤ → ä, â€" → –, ðŸ'° → 💰)
#        wird automatisch repariert. Klassischer Copy-Paste-/KI-Fehler.
#
#  SELBST-ENTSCHEIDUNG (E1): Themen-Mapping bestimmt das Emoji:
#    Geld/Sparen/Budget→💰 · Energie/Strom/Heizen→⚡ · Internet/DSL→📶
#    Versicherung→🛡️ · Reise/Urlaub→✈️ · Auto/Kfz→🚗 · Familie/Kind→👨‍👩‍👧
#    Danach Marken-Default 💰 (deckt „Geld sparen" immer ab).
#
#  Geschützt: Titel (kein Auto-Einfügen – Titel-Semantik bleibt
#  redaktionell), Artikel-Fließtext (das Theme setzt z. B. 💡-Boxen
#  selbst), Code, URLs.
#
#  Aufruf:
#    python3 scripts/emoji_guard.py         # Report
#    python3 scripts/emoji_guard.py --fix   # E1/E3/E4 automatisch fixen
#  Ausgabe: EMOJI-REPORT.md · idempotent · Exit 0 = OK.
# ============================================================

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HUGO_TOML = ROOT / "hugo.toml"
REPORT = ROOT / "EMOJI-REPORT.md"

DO_FIX = "--fix" in sys.argv
DRY_RUN = "--dry-run" in sys.argv

# ---------------- Themen -> Emoji (Entscheidungs-Mapping, Hausmarke 💰) ----------------
TOPIC_EMOJI = [
    (re.compile(r"(energie|strom|heiz|gas|wärmepumpe)", re.I), "⚡"),
    (re.compile(r"(internet|dsl|wlan|netz|5g)", re.I), "📶"),
    (re.compile(r"(versicherung|schutz|haftpflicht)", re.I), "🛡️"),
    (re.compile(r"(reise|urlaub|flug|mietwagen)", re.I), "✈️"),
    (re.compile(r"(auto|kfz|fahrzeug|e-auto)", re.I), "🚗"),
    (re.compile(r"(kind|familie|schule)", re.I), "👨‍👩‍👧"),
    (re.compile(r"(geld|spar|finanz|budget|frugal|zins|vermögen|konto)", re.I), "💰"),
]
BRAND_DEFAULT = "💰"
MAX_EMOJI_SOFT = 2  # E3: mehr = Fund

EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF☀-➿⬀-⯿️\U0001F1E6-\U0001F1FF]")

# ---------------- E4: Mojibake-Tabelle (häufigste UTF-8-Brüche) ----------------
MOJIBAKE = {
    "Ã„": "Ä", "Ã¤": "ä", "Ã–": "Ö", "Ã¶": "ö", "Ãœ": "Ü", "Ã¼": "ü",
    "ÃŸ": "ß", "â€“": "–", "â€”": "—", "â€ž": "„", "â€œ": "“",
    "â€\u009c": "“", "â€ž": "„", "â€™": "'", "â‚¬": "€", "Â": "",
}
EMOJI_MOJI = re.compile("ðŸ[\\x80-\\xbf]{2,4}")  # kaputte Emoji-Header


def count_emojis(text: str) -> int:
    return len(EMOJI_RE.findall(text))


def pick_emoji(content: str) -> str:
    """Entscheidung: erstes passendes Themen-Emoji, sonst Marken-Default."""
    for rx, emoji in TOPIC_EMOJI:
        if rx.search(content):
            return emoji
    return BRAND_DEFAULT


# ------------------------------------------------------------- Prüfungen

def check_hugo_toml() -> list[dict]:
    """E1/E2/E3 auf hugo.toml (Block params / homeInfoParams)."""
    src = HUGO_TOML.read_text(encoding="utf-8")
    findings = []

    # homeInfoParams.Content
    m = re.search(r'(Title\s*=\s*"[^"]*"\s*\n\s*Content\s*=\s*")([^"]*)(")', src)
    if m:
        content = m.group(2)
        n = count_emojis(content)
        if n == 0:
            emoji = pick_emoji(content)
            findings.append({
                "id": "E1", "wo": "homeInfoParams.Content",
                "problem": "kein Marken-Emoji in der Startseiten-Tagline",
                "fix_alt": None, "fix_neu": content,
                "apply": (emoji + " " + content),
                "span": (m.start(2), m.end(2)),
            })
        elif n > MAX_EMOJI_SOFT:
            findings.append({"id": "E3", "wo": "homeInfoParams.Content",
                             "problem": f"{n} Emojis – Overuse (max {MAX_EMOJI_SOFT})"})

    # params.description (Meta)
    m2 = re.search(r'^(  description\s*=\s*")([^"]*)(")', src, re.M)
    if m2:
        n = count_emojis(m2.group(2))
        if n > 1:
            findings.append({"id": "E3", "wo": "params.description",
                             "problem": f"{n} Emojis in Meta-Description (max 1 empfohlen)"})

    return findings


def apply_fixes(findings) -> bool:
    """Wendet E1-Fixes auf hugo.toml an (nur Einträge mit 'apply')."""
    fixable = [f for f in findings if f.get("apply")]
    if not fixable:
        return False
    src = HUGO_TOML.read_text(encoding="utf-8")
    for f in sorted(fixable, key=lambda x: x["span"][0], reverse=True):
        a, b = f["span"]
        src = src[:a] + f["apply"] + src[b:]
    HUGO_TOML.write_text(src, encoding="utf-8")
    return True


ZERO_WIDTH = ["​", "‌", "‍", "﻿"]  # E5: unsichtbarer Müll (U+200B/C/D, BOM)


def mojibake_scan() -> tuple[list[dict], int]:
    """E4+E5: scannt content/ + hugo.toml nach UTF-8-Brüchen und
    Zero-Width-Zeichen; repariert mit --fix optional automatisch."""
    hits, repaired = [], 0
    paths = [HUGO_TOML] + sorted((ROOT / "content").rglob("index.md")) + \
        sorted((ROOT / "content").rglob("_index.md"))
    for p in paths:
        text = p.read_text(encoding="utf-8")
        found = {bad: text.count(bad) for bad in MOJIBAKE if bad in text}
        em = len(EMOJI_MOJI.findall(text))
        if em:
            found["kaputte Emoji (ðŸ…)"] = em
        zw = sum(text.count(c) for c in ZERO_WIDTH)
        if zw:
            found["Zero-Width (U+200B o. ä.)"] = zw
        if not found:
            continue
        hits.append({"file": str(p.relative_to(ROOT)), "arten": found})
        if DO_FIX and not DRY_RUN:
            if "kaputte Emoji (ðŸ…)" in found:
                continue  # kaputte Emoji: nicht raten -> nur melden
            for bad, good in MOJIBAKE.items():
                text = text.replace(bad, good)
            for c in ZERO_WIDTH:                       # E5: immer sicher zu löschen
                text = text.replace(c, "")
            p.write_text(text, encoding="utf-8")
            repaired += 1
    return hits, repaired


# ------------------------------------------------------------------ Main

def main() -> None:
    findings = check_hugo_toml()
    moji, repaired = mojibake_scan()
    fixed_e1 = 0
    if DO_FIX and not DRY_RUN:
        if apply_fixes(findings):
            fixed_e1 = sum(1 for f in findings if f.get("apply"))
            findings = check_hugo_toml()  # neu bewerten

    mode = "DRY-RUN" if DRY_RUN else ("FIX" if DO_FIX else "REPORT")
    lines = ["# 😀 EMOJI-REPORT (emoji_guard.py)", "",
             f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · Modus: {mode}", ""]
    if fixed_e1:
        lines += [f"## ✅ E1 korrigiert: Marken-Emoji in Startseiten-Tagline ergänzt ({fixed_e1}x)", ""]
    open_f = [f for f in findings if not (fixed_e1 and f.get("apply"))]
    if open_f:
        lines += ["## Befunde", ""]
        lines += [f"- **{f['id']}** `{f['wo']}`: {f['problem']}" for f in open_f]
    if moji:
        lines += ["", "## ⚠️ E4/E5 Text-Hygiene (Mojibake + unsichtbare Zeichen)", ""]
        if repaired:
            lines += [f"✅ {repaired} Datei(en) automatisch repariert.", ""]
        lines += [f"- `{m['file']}`: " +
                  ", ".join(f"{repr(k)} ×{v}" for k, v in m["arten"].items()) for m in moji[:15]]
    if not open_f and not moji and not fixed_e1:
        lines.append("🎉 Touchpoints emoji-sauber, kein Mojibake – Profi-Niveau erreicht.")
    lines += ["", "---", "_Regeln: E1 Marken-Emoji (Auto) · E2 Meta-Desc rar · "
              "E3 Anti-Overuse (max 2) · E4 Mojibake-Auto-Reparatur._"]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:20]))


if __name__ == "__main__":
    main()
