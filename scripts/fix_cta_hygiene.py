#!/usr/bin/env python3
"""fix_cta_hygiene.py – Deterministische Heilung der kanonischen Partner-CTA.

WARUM (Reserve-Reparatur #5, 11.09.2026, „Stock shortage“ #247):
  Die KI-Schritte (profi_polish, lektor_guard --ai, meta_optimizer --ai)
  verschmelzen in der kanonischen Schnell-Tipp-Zeile wiederholt die Wörter
  „Die besten“ zum Klebewort „Ddiebesten“ (real beobachtet in 3 Artikeln am
  11.09.2026, davon einer bereits LIVE). Die alte Reserve-Reparatur
  (reserve_finisher._canonical_cta_hygiene) heilte die Stelle NUR VOR der
  Heiler-Kette – profi_polish läuft aber als ERSTER Heiler und erzeugte die
  Korruption danach neu; spellcheck --fix kann das Klebewort nicht sicher
  auflösen (unklare Hunspell-Vorschläge) → Rechtschreib-Score 0.00–0.50 in der
  Zertifizierung → „Stock shortage“ an jedem Tag.

  Dieser Heiler ist KI- und netzunabhängig, idempotent und wird MEHRMALS
  gefahren: sofort NACH jedem KI-Schritt, der Fließtext umschreibt, und als
  letzte deterministische Instanz vor der Zertifizierung. Er heilt die
  bekannte Korruptionsklasse auf der markierten CTA-Zeile:

      💡 **Schnell-Tipp von FranksFinanzcheck:** Ddiebesten Tarife …
      → 💡 **Schnell-Tipp von FranksFinanzcheck:** Die besten Tarife …

  Varianten: „Ddiebesten“, „Diebesten“, „ddiebesten“, „Ddie besten“. Der
  Gedankenstrich in „Partner-Vergleich“/„Partner‑Vergleich“ bleibt bytegenau
  erhalten (kein Streit mit dem Dash-Guard).

MODI:
  python3 scripts/fix_cta_hygiene.py                     # Korpus (ohne Entwürfe)
  python3 scripts/fix_cta_hygiene.py --include-drafts    # inkl. Entwürfe
  python3 scripts/fix_cta_hygiene.py --file <pfad>       # eine Datei (Entwürfe erlaubt)
  python3 scripts/fix_cta_hygiene.py --selftest          # Sabotage-Schutz

EXIT: 0 ok (geheilt oder bereits sauber) · 1 unerwarteter Fehler · 2 Selbsttest fehlt
"""
import argparse
import re
import sys
import tempfile
from pathlib import Path

BLOG_DIR = Path(__file__).resolve().parent.parent
POSTS_DIR = BLOG_DIR / "content" / "posts"

# Die Korruption sitzt IMMER auf der fett ausgezeichneten CTA-Zeile
# („…:** <Wort> Tarife findest du über unseren Partner-Vergleich“). Der
# Label-Prefix verhindert, dass ein korrektes „die besten Tarife“ mitten im
# Fließtext ungefragt großgeschrieben wird.
CANONICAL_CTA_RE = re.compile(
    r"(?P<prefix>^[^\n]*\*\*[^*\n]{3,}:\*\*[ \t]+)"
    r"(?P<onset>Ddiebesten|Diebesten|ddiebesten|Ddie[ \t]+besten|diebesten)"
    r"(?P<rest>[ \t]+Tarife[ \t]+findest[ \t]+du[ \t]+"
    r"(?:über|ueber)[ \t]+unseren?[ \t]+Partner[‐-―−-]?Vergleich)",
    re.M,
)


def hygiene_text(text: str) -> tuple[str, int]:
    """Liefert (ggf. geheilten Text, Anzahl Korrekturen). Idempotent."""
    new, n = CANONICAL_CTA_RE.subn(
        lambda m: m.group("prefix") + "Die besten" + m.group("rest"), text)
    return new, n


def hygiene_file(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    new, n = hygiene_text(text)
    if n:
        path.write_text(new, encoding="utf-8")
    return n


def is_draft(text: str) -> bool:
    parts = text.split("---", 2)
    if len(parts) < 3:
        return False
    return bool(re.search(r"(?m)^draft:\s*true\s*$", parts[1]))


def iter_files(include_drafts: bool):
    for p in sorted(POSTS_DIR.glob("*/index.md")):
        text = p.read_text(encoding="utf-8")
        if not include_drafts and is_draft(text):
            continue
        yield p


def run_selftest() -> list:
    fehler = []
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        bad = d / "bad.md"
        bad.write_text(
            "---\ntitle: T\ndraft: true\n---\n\n"
            "💡 **Schnell-Tipp von FranksFinanzcheck:** Ddiebesten Tarife "
            "findest du über unseren Partner-Vergleich: [x](/go/strom/)\n",
            encoding="utf-8")
        fixed, n = hygiene_text(bad.read_text(encoding="utf-8"))
        if n != 1 or "Ddiebesten" in fixed or \
                "** Die besten Tarife findest du über unseren Partner-Vergleich" \
                not in fixed:
            fehler.append(f"Ddiebesten wurde nicht kanonisch repariert (n={n})")
        # Idempotenz
        fixed2, n2 = hygiene_text(fixed)
        if n2 != 0 or fixed2 != fixed:
            fehler.append("Hygiene ist nicht idempotent (churnt)")
        # Variante mit schmalem nicht-trennenden Bindestrich (U+2011)
        variant = ("💡 **Schnell-Tipp von FranksFinanzcheck:** Diebesten Tarife "
                   "findest du über unseren Partner‑Vergleich: [x](/go/gas/)\n")
        out, n3 = hygiene_text(variant)
        if n3 != 1 or "Die besten Tarife" not in out or "Partner‑Vergleich" not in out:
            fehler.append("Variante (Diebesten/U+2011) nicht geheilt oder Dash zerstört")
        # Sauberer Text bleibt unverändert
        clean = "Ein Absatz ohne CTA. Die besten Tarife gibt es woanders.\n"
        out, n4 = hygiene_text(clean)
        if n4 != 0 or out != clean:
            fehler.append("Die Hygiene greift außerhalb der markierten CTA-Zeile")
        # Entwurfs-Filter
        draft = d / "d.md"
        live = d / "l.md"
        body = ("---\ntitle: T\ndraft: {draft}\n---\n\n"
                "💡 **Schnell-Tipp:** Ddiebesten Tarife findest du über "
                "unseren Partner-Vergleich.\n")
        draft.write_text(body.format(draft="true"), encoding="utf-8")
        live.write_text(body.format(draft="false"), encoding="utf-8")
        # Draft-Policy wird im Aufrufer geprüft (is_draft)
        if is_draft(draft.read_text(encoding="utf-8")) is not True:
            fehler.append("is_draft erkennt Entwurf nicht")
        if is_draft(live.read_text(encoding="utf-8")) is not False:
            fehler.append("is_draft erkennt Live-Artikel falsch")
    return fehler


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="Einzelne Datei (inkl. Entwürfe)")
    ap.add_argument("--include-drafts", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        fehler = run_selftest()
        if fehler:
            print("🛑 CTA-HYGIENE-SELFTEST FEHLGESCHLAGEN:")
            for f in fehler:
                print(f"   - {f}")
            return 2
        print("✅ CTA-Hygiene-Selbsttest grün (Kanonic, Idempotenz, Draft-Filter).")
        return 0

    total = 0
    if args.file:
        total += hygiene_file(Path(args.file))
    else:
        for p in iter_files(args.include_drafts):
            total += hygiene_file(p)
    if total:
        print(f"🧹 CTA-Hygiene: {total} kanonische Partner-CTA-Zeile(n) "
              f"repariert.")
    else:
        print("CTA-Hygiene: alle kanonischen CTA-Zeilen sauber.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
