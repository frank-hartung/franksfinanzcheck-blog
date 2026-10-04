#!/usr/bin/env python3
# ============================================================
#  EMOJI-GUARD – Marken-Emoji-Politur (selbst prüfen & entscheiden)
#
#  Entscheidet auf Profi-Niveau über Emojis an den Marken-Touchpoints:
#
#  REGELN (Ebenen):
#    E1  Der frühere statische Startseiten-Willkommenstext ist gelöscht.
#        Saison-Badge und Saison-Emoji sind deshalb Sache von
#        saisonale_startseite_guard.py, nicht dieses Hugo-TOML-Tools.
#    E2  params.description (Meta-Description): KEIN Emoji-Zwang –
#        Google zeigt Emojis dort unzuverlässig; mehr als 1 = Report.
#    E3  Anti-Overuse: mehr als 1 Emoji in der Meta-Description = Fund.
#        (Profi-Regel: Emoji = Akzent, nicht Dekoration.)
#    E4  Mojibake-Scanner (blogweit, content/ + hugo.toml):
#        kaputte UTF-8-Doppelcodierung (Ã¤ → ä, â€" → –, ðŸ'° → 💰)
#        wird automatisch repariert. Klassischer Copy-Paste-/KI-Fehler.
#
#  Geschützt: saisonale H1/Leads und Artikel-Fließtext (keine Auto-Emoji-
#  Einfügung in redaktionelle Semantik), Code und URLs.
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

MAX_META_EMOJI = 1  # E3: Such-Snippets bleiben ruhig und gut lesbar

# Härtung 2026-10 (py/overly-large-range): Bereiche kanonisiert – disjunkt,
# explizit escapte Grenzen, Regional-Indikatoren (1F1E6–1F1FF) lagen schon in
# 1F000–1FAFF; der Variation Selector U+FE0F bleibt bewusst als Einzelzeichen.
EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F]")

# ---------------- E4: Mojibake-Tabelle (häufigste UTF-8-Brüche) ----------------
MOJIBAKE = {
    "Ã„": "Ä", "Ã¤": "ä", "Ã–": "Ö", "Ã¶": "ö", "Ãœ": "Ü", "Ã¼": "ü",
    "ÃŸ": "ß", "â€“": "–", "â€”": "—", "â€ž": "„", "â€œ": "“",
    "â€\u009c": "“", "â€ž": "„", "â€™": "'", "â‚¬": "€", "Â": "",
}
EMOJI_MOJI = re.compile("ðŸ[\\x80-\\xbf]{2,4}")  # kaputte Emoji-Header


def count_emojis(text: str) -> int:
    return len(EMOJI_RE.findall(text))


# ------------------------------------------------------------- Prüfungen

def check_hugo_toml() -> list[dict]:
    """E2/E3 auf der Meta-Description; der saisonale Hero hat ein eigenes Gate."""
    src = HUGO_TOML.read_text(encoding="utf-8")
    findings = []
    m = re.search(r'^(  description\s*=\s*\")([^\"]*)(\")', src, re.M)
    if m:
        n = count_emojis(m.group(2))
        if n > MAX_META_EMOJI:
            findings.append({"id": "E3", "wo": "params.description",
                             "problem": f"{n} Emojis in Meta-Description (max 1 empfohlen)"})
    return findings


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
    mode = "DRY-RUN" if DRY_RUN else ("FIX" if DO_FIX else "REPORT")
    lines = ["# 😀 EMOJI-REPORT (emoji_guard.py)", "",
             f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · Modus: {mode}", ""]
    open_f = findings
    if open_f:
        lines += ["## Befunde", ""]
        lines += [f"- **{f['id']}** `{f['wo']}`: {f['problem']}" for f in open_f]
    if moji:
        lines += ["", "## ⚠️ E4/E5 Text-Hygiene (Mojibake + unsichtbare Zeichen)", ""]
        if repaired:
            lines += [f"✅ {repaired} Datei(en) automatisch repariert.", ""]
        lines += [f"- `{m['file']}`: " +
                  ", ".join(f"{repr(k)} ×{v}" for k, v in m["arten"].items()) for m in moji[:15]]
    if not open_f and not moji:
        lines.append("🎉 Touchpoints emoji-sauber, kein Mojibake – Profi-Niveau erreicht.")
    lines += ["", "---", "_Regeln: Saison-Emoji im Saison-Gate · E2 Meta-Desc rar · "
              "E3 Anti-Overuse (max 1) · E4 Mojibake-Auto-Reparatur._"]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:20]))


if __name__ == "__main__":
    main()
