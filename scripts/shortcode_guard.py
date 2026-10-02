#!/usr/bin/env python3
"""Shortcode-Wache: Hugo-Shortcodes bleiben frei von Markdown-Links.

Root-Cause WF-1F8C (Issue #522, 02.10.2026): Ein Rewrite-Heiler hat das
Wort „notgroschen“ INNERHALB von {{< rechner typ="notgroschen" … >}} zu
einem Markdown-Link umgeschrieben:

    typ="[notgroschen](../../posts/2026-09-09-notgroschen-…/)"

Hugo bricht dann blog-weit ab („rechner: unbekannter typ …“) – kein
Build, kein Deploy, Kadenz-Endkontrolle rot. Der Linker ist seitdem
shortcode-blind (Sperrzonen in internal_linker.find_anchor), aber viele
Heiler schreiben in den Artikeltext. Diese Wache ist das Fangnetz:

  - findet Markdown-Links ([text](ziel)) in {{< … >}} / {{% … %}}
  - --fix entlinkt sie deterministisch (Label bleibt, Link fliegt raus)
  - --selftest beweist Erkennung + Heilung am realen Schadensmuster

Exit-Codes: 0 = sauber/geheilt · 1 = Funde ohne --fix · 2 = Selbsttest rot.

Nutzung:
    python3 scripts/shortcode_guard.py              # nur prüfen
    python3 scripts/shortcode_guard.py --fix        # prüfen + heilen
    python3 scripts/shortcode_guard.py --selftest
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"

SHORTCODE_RX = re.compile(r"\{\{[<%].*?[>%]\}\}", re.S)
MD_LINK_RX = re.compile(r"\[([^\]\n]*)\]\(([^)\n]*)\)")


def heal_shortcode(sc: str):
    """Entlinkt Markdown-Links im Shortcode; Label bleibt stehen."""
    funde = [m.group(0) for m in MD_LINK_RX.finditer(sc)]
    return MD_LINK_RX.sub(r"\1", sc), funde


def scan_file(path: Path, fix: bool):
    text = path.read_text(encoding="utf-8")
    funde = []
    out = []
    last = 0
    for m in SHORTCODE_RX.finditer(text):
        healed, hits = heal_shortcode(m.group(0))
        if hits:
            funde.extend(hits)
            out.append(text[last:m.start()])
            out.append(healed)
            last = m.end()
    if funde and fix:
        out.append(text[last:])
        path.write_text("".join(out), encoding="utf-8")
    return funde


def run(fix: bool) -> int:
    gesamt = 0
    dateien = 0
    for path in sorted(CONTENT.rglob("*.md")):
        funde = scan_file(path, fix)
        if funde:
            dateien += 1
            gesamt += len(funde)
            status = "geheilt" if fix else "FUND"
            rel = path.relative_to(ROOT)
            for f in funde:
                print(f"  {status}: {rel}: {f}")
    if gesamt == 0:
        print("✅ Shortcode-Wache: keine Markdown-Links in Shortcodes – "
              "alle Parameter build-sicher.")
        return 0
    print(f"{'✅' if fix else '❌'} Shortcode-Wache: {gesamt} Link(s) in "
          f"{dateien} Datei(en) {'entlinkt (Label erhalten)' if fix else 'gefunden – mit --fix heilen'}.")
    return 0 if fix else 1


def selftest() -> int:
    kaputt = ('{{< rechner typ="[notgroschen](../../posts/2026-09-09-'
              'notgroschen-die-wahrheit-ueber-das-finanzielle-polster/)" '
              'quelle="Verbraucherzentrale" stand="September 2026" >}}')
    erwartet = ('{{< rechner typ="notgroschen" '
                'quelle="Verbraucherzentrale" stand="September 2026" >}}')
    fails = []
    healed, hits = heal_shortcode(kaputt)
    if healed != erwartet:
        fails.append(f"Heilung falsch: {healed!r}")
    if len(hits) != 1:
        fails.append(f"Erkennung falsch: {hits!r}")
    sauber = '{{< rechner typ="notgroschen" quelle="BDEW" >}}'
    healed2, hits2 = heal_shortcode(sauber)
    if healed2 != sauber or hits2:
        fails.append("False Positive auf sauberem Shortcode")
    # Markdown-Links AUSSERHALB von Shortcodes sind Sache des Linkers,
    # nicht dieser Wache – der Scanner darf sie nicht anfassen.
    text = "Ein [notgroschen](../../posts/x/) im Fließtext.\n" + sauber + "\n"
    if SHORTCODE_RX.findall(text) != [sauber]:
        fails.append("Scanner greift über Shortcode-Grenzen hinaus")
    if fails:
        for f in fails:
            print(f"❌ Shortcode-Wache Selbsttest: {f}")
        return 2
    print("✅ Shortcode-Wache Selbsttest: erkennt und entlinkt das reale "
          "WF-1F8C-Schadensmuster, ohne sauberen Bestand anzufassen.")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    return run("--fix" in sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
