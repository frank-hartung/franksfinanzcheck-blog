#!/usr/bin/env python3
"""generate_kurzantworten.py – erzeugt pro Artikel eine knackige Kurzantwort
(2–3 Sätze) für Featured Snippets / AI Overviews und speichert sie als
Frontmatter-Feld `kurzantwort:`.

Die Kurzantwort wird als hervorgehobene Box direkt unter der H1 gerendert
(siehe layouts/single.html) – ein klarer, selbstständiger Antwort-Text, den
Google als Snippet/AI-Overview übernehmen kann.

Nutzung:
  python3 scripts/generate_kurzantworten.py            # nur fehlende, alle
  python3 scripts/generate_kurzantworten.py --file X   # einzelner Artikel
  python3 scripts/generate_kurzantworten.py --all      # alle neu generieren
"""
import os
import re
import sys
import glob
import time
import json

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
from post_utils import list_post_paths
import generate_drafts as g

PROMPT = (
    "Beantworte die Kernfrage des folgenden Blog-Artikels in 2-3 kurzen, "
    "klaren deutschen Sätzen als direkte Antwort (wie für ein Google-Featured-"
    "Snippet / AI Overview). Nenne einen konkreten Zahlenwert oder Fakt, wenn "
    "sinnvoll. KEINE Einleitung wie 'In diesem Artikel...', keine Aufzählung, "
    "keine Markdown-Formatierung. Nur die Antwort.\n\n"
    "TITEL: {title}\n"
    "FRAGE/KERN: {desc}\n"
)


def get_meta(path):
    content = open(path, encoding="utf-8").read()
    parts = content.split("---", 2)
    fm = parts[1] if len(parts) >= 2 else ""
    def get(key):
        m = re.search(rf'^{key}:\s*"?(.+?)"?\s*$', fm, re.M)
        return m.group(1).strip() if m else ""
    return get("title"), get("description"), fm


def set_kurzantwort(path, answer):
    content = open(path, encoding="utf-8").read()
    parts = content.split("---", 2)
    fm = parts[1]
    if re.search(r"^kurzantwort:\s*", fm, re.M):
        fm2 = re.sub(r"^kurzantwort:.*$", f'kurzantwort: "{answer}"', fm, count=1, flags=re.M)
    else:
        fm2 = fm.rstrip() + f'\nkurzantwort: "{answer}"\n'
    open(path, "w", encoding="utf-8").write("---".join([parts[0], fm2, parts[2]]))


def main():
    files = []
    if "--file" in sys.argv:
        files = [sys.argv[sys.argv.index("--file") + 1]]
    else:
        files = list_post_paths()
    force = "--all" in sys.argv

    ok, fail = 0, 0
    for path in files:
        title, desc, fm = get_meta(path)
        if not title:
            continue
        if "kurzantwort:" in fm and not force:
            continue
        prompt = PROMPT.format(title=title, desc=desc[:200])
        answer = None
        for fn in (g.call_groq, g.call_gemini):
            try:
                answer = fn(prompt)
                if answer and 60 <= len(answer.strip()) <= 400:
                    break
                answer = None
            except Exception:
                answer = None
        if not answer:
            print(f"  ⚠ übersprungen (kein Provider): {os.path.basename(os.path.dirname(path))}")
            fail += 1
            continue
        answer = answer.strip().replace("\n", " ")
        # BERREINIGUNG (Top-Level): HTML-Entities & bekannte KI-Fehler entfernen.
        # Sonst erscheinen sie im Frontmatter/HTML als sichtbarer Text.
        answer = answer.replace("&nbsp;", " ").replace("&amp;", "&")
        answer = re.sub(r"\bless als\b", "weniger als", answer, flags=re.I)
        answer = re.sub(r"\s+", " ", answer).strip()
        # Validierung: keine Entities, keine offensichtlichen Fehler
        if any(bad in answer for bad in ["&nbsp;", "&amp;", "less als", "  "]):
            print(f"  ⚠ Antwort nach Bereinigung noch fehlerhaft: {os.path.basename(os.path.dirname(path))}")
            fail += 1
            continue
        set_kurzantwort(path, answer)
        ok += 1
        print(f"  ✓ {os.path.basename(os.path.dirname(path))[:50]} → {answer[:60]}…")
        time.sleep(1)  # Rate-Limit-Schonung

    print(f"\nFertig: {ok} Kurzantworten erzeugt, {fail} übersprungen.")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
