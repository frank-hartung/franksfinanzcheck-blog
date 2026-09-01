#!/usr/bin/env python3
"""
ABSORB-WHITELIST – Rechtschreib-Rauschen senken (Audit 01.09.2026).

Hunspell kennt viele korrekte deutsche Komposita nicht („Spontankäufen“,
„Dispokredite“, „SIM-Only-Tarife“) -> der Report sammelt dauerhaft hunderte
offene „Unbekanntes Wort“-Funde, die nie ein echter Tippfehler sind.

Konservative Absorption: Ein Wort wird NUR dann in die Whitelist übernommen,
wenn es als „unbekannt“ in MINDESTENS 3 verschiedenen Artikeln vorkommt.
Ein echter Tippfehler wiederholt sich praktisch nie identisch in 3 Artikeln;
ein korrektes Fachkompositum dagegen fast immer.

  python3 scripts/absorb_whitelist.py            # Report (was würde absorbiert)
  python3 scripts/absorb_whitelist.py --apply    # Whitelist tatsächlich erweitern
"""

import re
import sys
import os
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spellcheck as sc

MIN_ARTICLES = 3      # Wort muss in so vielen Artikeln auftauchen
MIN_LEN = 4

APPLY = "--apply" in sys.argv


def main() -> int:
    whitelist = sc.load_whitelist()
    articles = sc.load_articles()
    counter = Counter()
    for a in articles:
        problems = sc.analyze_article(a, whitelist)
        words = {p["word"] for p in problems if p.get("type") == "unknown"}
        for w in words:
            counter[w] += 1

    candidates = sorted(
        w for w, n in counter.items()
        if n >= MIN_ARTICLES and len(w) >= MIN_LEN
        and re.search(r"[a-zäöüß]", w, re.I)
    )
    print(f"Absorption: {len(counter)} unterschiedliche unbekannte Wörter "
          f"in {len(articles)} Artikeln; Kandidaten (≥ {MIN_ARTICLES} Artikel): {len(candidates)}")

    for w in candidates:
        print(f"  {w:<40} ×{counter[w]}")

    if APPLY and candidates:
        path = Path(sc.WHITELIST_FILE)
        existing = set()
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                ls = line.strip()
                if ls and not ls.startswith("#"):
                    existing.add(ls.lower())
        neu = [w for w in candidates if w.lower() not in existing]
        if not neu:
            print("Alles bereits whitelisted.")
            return 0
        with path.open("a", encoding="utf-8") as f:
            f.write("\n# Automatisch absorbiert (absorb_whitelist.py, 01.09.2026)\n"
                    "# Korrekte Komposita, die Hunspell nicht kennt, aber in ≥ 3 Artikeln vorkommen.\n")
            for w in neu:
                f.write(w + "\n")
        print(f"\n✅ {len(neu)} Wörter in {path} aufgenommen.")
    elif not APPLY:
        print("\n(--apply zum tatsächlichen Eintragen)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
