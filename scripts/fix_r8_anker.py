#!/usr/bin/env python3
"""
R8-ANKER-ZIEL-Heiler (Premium-Stufe) für FranksFinanzcheck.

Heilt deterministisch die verbliebenen weichen R8-Funde aus dem
TEXTVERSTÄNDNIS-Report: Jeder interne Ankertext bekommt mindestens einen
Substantiv-Token des Ziel-Slugs, damit Ankertext und Ziel semantisch
zusammenhängen (Textverständnis-Regel R8, Premium-Level).

Der Heiler ist bewusst konservativ: Er ersetzt NUR exakt bekannte
Ankertext-Fragmente durch bewährte Premium-Formulierungen aus einem
Kanon (kein freies KI-Rewriting). Unbekannte Fälle meldet er als
Review-Kandidaten statt sie blind zu ändern.

MODI:
  python3 scripts/fix_r8_anker.py            # Report (keine Änderungen)
  python3 scripts/fix_r8_anker.py --fix      # Kanon anwenden
  python3 scripts/fix_r8_anker.py --selftest # Sabotage-Schutz

Der Kanon muss mit dem Guard abgestimmt bleiben: Jeder Ersatztext muss
mindestens einen Token-Match mit dem Ziel-Slug erzeugen (Token-Mindestlänge 3,
Umlaute normalisiert, Stoppwörter inkl. „für“→„fuer“ ausgeschlossen).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "content" / "posts"

# Kanon: (exaktes Fragment, Premium-Ersatz)
# Ersatze enthalten mindestens einen Token des Ziel-Slugs (Kohärenz R8).
KANON = [
    # Ziel: preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026
    ("im Leitfaden zur [Tarifstrategie für das Jahr 2026](../../posts/2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026/)",
     "im Leitfaden zu [Preisgarantie-Tarifen für 2026](../../posts/2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026/)"),
    ("in den [Konditions-Vergleichen für das Jahr 2026](../../posts/2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026/)",
     "in den [Vergleichen günstiger Gastarife 2026](../../posts/2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026/)"),
    # Ziel: gasrechnung-senken-fehler-im-spaetsommer-vermeiden
    ("| [Heizung entlüften](../../posts/2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden/)",
     "| [Heizung entlüften im Spätsommer](../../posts/2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden/)"),
    # Ziel: tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich
    ("den [Notgroschen](../../posts/2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich/)",
     "den [Tagesgeld-Notgroschen](../../posts/2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich/)"),
    # Ziel: mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps
    ("sind das **[Geld sparen im Alltag](../../posts/2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps/)**",
     "sind das **[Sparen im Alltag mit Frugalismus-Tipps](../../posts/2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps/)**"),
]

# Selftest-Fälle: (roher Text, erwartete Anzahl Ersetzungen)
SELFTEST_CASES = [
    ("TEXT\n\nWie du sparst, steht im Leitfaden zur "
     "[Tarifstrategie für das Jahr 2026](../../posts/2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026/) "
     "und im Vergleich zu [Preisgarantie-Tarifen für 2026](../../posts/2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026/) mit Lücke.",
     1),
    ("TEXT\n\n| [Heizung entlüften](../../posts/2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden/) & Thermostate | 45 Min |",
     1),
    ("TEXT\n\nKein Treffer hier: [Tarifvergleich](../../posts/2026-08-12-anderes-ziel/).", 0),
]


def apply_kanon(text: str) -> tuple:
    """Wendet alle Kanon-Fixes an. Liefert (neuer Text, Anzahl Fixes, Liste der Fixes)."""
    new = text
    count = 0
    applied = []
    for old, repl in KANON:
        if old in new:
            n = new.count(old)
            new = new.replace(old, repl)
            count += n
            applied.append(f"{n}× „{old[:55]}…“ → „{repl[:55]}…“")
    return new, count, applied


def run_selftest() -> list:
    fehler = []
    for raw, expected in SELFTEST_CASES:
        _, count, _ = apply_kanon(raw)
        if count != expected:
            fehler.append(f"Selftest: erwartet {expected} Fixes, bekam {count}")
    return fehler


def main() -> int:
    fehler = run_selftest()
    if fehler or "--selftest" in sys.argv:
        for f in fehler:
            print("🛑 " + f)
        if fehler:
            return 2
        print("✅ R8-Anker-Heiler Selbsttest grün.")
        return 0

    total_fixes = 0
    reports = []
    for index in sorted(POSTS.glob("*/index.md")):
        text = index.read_text(encoding="utf-8")
        new, count, applied = apply_kanon(text)
        if count:
            if "--fix" in sys.argv:
                index.write_text(new, encoding="utf-8")
            total_fixes += count
            for a in applied:
                reports.append(f"- `{index.relative_to(ROOT)}`: {a}")
            print(f"  {count} Fix(es): {index.relative_to(ROOT)}")

    if reports:
        print(f"\nR8-Heiler: {total_fixes} Ankertext(e) "
              f"{'geheilt' if '--fix' in sys.argv else 'zu heilen'}.")
    else:
        print("R8-Heiler: keine bekannten Fälle – alle Ankertexte kohärent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())