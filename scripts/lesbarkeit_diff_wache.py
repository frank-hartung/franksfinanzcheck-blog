#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LESBARKEITS-DIFF-WACHE – kein Live-Artikel fällt durch eine Überarbeitung.

WARUM ES DIESE WACHE GIBT (22.11.2026, Befund aus #1247)
--------------------------------------------------------
Das Publish-Gate prüft die Lesbarkeit von **Neuveröffentlichungen**
(`publish_gate.todays_live_candidates()`: Ordner-Präfix heute oder
`date` = heute). Es prüft NICHT, was mit einem bereits veröffentlichten
Artikel passiert, wenn ihn später jemand überarbeitet.

Genau diese Lücke ist real geworden: Drei Live-Artikel wurden am
19.11.2026 neu gefasst (Faktenfrische/Redaktion) und liegen seither
unter dem Haus-Boden Flesch 60:

    2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen   51,5
    2026-08-26-handytarif-vergleichen-2026-guenstige-tarife        53,8
    2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze         54,0

Kein Lauf hat das verhindert – die Wochen-Wache meldet es erst danach,
und ein Bestands-Gate darf nicht rückwirkend veröffentlichen. Diese Wache
setzt am richtigen Ort an: **vor** dem Merge einer Änderung.

WAS SIE PRÜFT (und was nicht)
-----------------------------
* Neu angelegte, bereits `draft: false` gesetzte Artikel: Flesch ≥ 60.
* Geänderte Live-Artikel: nur eine **Verschlechterung** unter den Boden
  ist ein Befund. Ein Alt-Artikel, der schon vorher bei 54 lag, blockiert
  damit nicht jede Routinemeldung – aber er darf auch nicht weiter fallen.
* Entwürfe (`draft: true`) sind frei: sie sind nicht live.

Die Schwelle wird aus `readability_check` importiert (R6) – es gibt keine
zweite Zahl im Haus. Die Messung ist dieselbe Funktion wie im Gate.

AUFRUF
------
  python3 scripts/lesbarkeit_diff_wache.py <basis-ref>
  python3 scripts/lesbarkeit_diff_wache.py --basis origin/main
  python3 scripts/lesbarkeit_diff_wache.py --selbsttest

Exit: 0 = keine Verschlechterung · 1 = Befund · 2 = Werkzeug-/Gitfehler
"""

from __future__ import annotations

import os
import subprocess
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import readability_check as rc  # noqa: E402 – Mess-SSOT (Flesch, R6)

POSTS = os.path.join(BLOG_DIR, "content", "posts")
# Toleranz gegen Messrauschen: Wortstellung ändert den Flesch um Zehntel,
# ohne dass der Text schlechter wird. Erst darunter ist es ein Befund.
RAUSCHEN = 0.05


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", BLOG_DIR, *args],
                          capture_output=True, text=True, check=False)


def geaenderte_artikel(basis: str) -> tuple[list[tuple[str, str]], str | None]:
    """→ ([(status, pfad)], fehler). status = A (neu) oder M (geändert)."""
    pruefung = _git("rev-parse", "--verify", f"{basis}^{{commit}}")
    if pruefung.returncode != 0:
        return [], (f"Basis-Ref '{basis}' ist nicht auflösbar "
                    f"(git rev-parse: {pruefung.stderr.strip()[:200]}).")
    diff = _git("diff", "--name-status", "--diff-filter=AM", f"{basis}...HEAD",
                "--", "content/posts")
    if diff.returncode != 0:
        return [], f"git diff fehlgeschlagen: {diff.stderr.strip()[:200]}"
    dateien = []
    for zeile in diff.stdout.splitlines():
        teile = zeile.split("\t")
        if len(teile) < 2:
            continue
        status, pfad = teile[0].strip(), teile[-1].strip()
        if not pfad.endswith("/index.md"):
            continue
        dateien.append((status[:1], pfad))
    return dateien, None


def _flesch_text(text: str, pfad: str) -> float | None:
    try:
        artikel = rc.parse_article(text, pfad)
        return rc.analyze(artikel)["flesch"]
    except Exception:  # noqa: BLE001 – ein kaputter Text ist ein Befund, kein Absturz
        return None


def bewerte(neu: float | None, alt: float | None, ist_neu: bool) -> str | None:
    """Reine Urteilsfunktion (testbar, ohne Git und ohne Dateien)."""
    if neu is None:
        return "Flesch nicht messbar – ungeprüft ist nicht veröffentlichungsfähig"
    if neu >= rc.FLOOR_MIN:
        return None
    if ist_neu:
        return (f"neuer Live-Artikel mit Flesch {neu:.1f} unter dem "
                f"Boden {rc.FLOOR_MIN:g}")
    if alt is None:
        return (f"frühere Fassung nicht messbar, neue Fassung Flesch {neu:.1f} "
                f"unter dem Boden {rc.FLOOR_MIN:g}")
    if neu < alt - RAUSCHEN:
        return (f"Flesch fällt von {alt:.1f} auf {neu:.1f} und liegt damit "
                f"unter dem Boden {rc.FLOOR_MIN:g}")
    return None


def pruefe(basis: str) -> tuple[list[str], list[str]]:
    """→ (befunde, hinweise)."""
    dateien, fehler = geaenderte_artikel(basis)
    if fehler:
        raise RuntimeError(fehler)
    befunde: list[str] = []
    hinweise: list[str] = []
    for status, pfad in dateien:
        voll = os.path.join(BLOG_DIR, pfad)
        if not os.path.isfile(voll):
            continue  # gelöscht/zurückgezogen – nichts zu bewerten
        with open(voll, encoding="utf-8") as f:
            neu_text = f.read()
        artikel = rc.parse_article(neu_text, pfad)
        if artikel.get("draft"):
            hinweise.append(f"{pfad}: Entwurf (nicht live) – nicht blockierend")
            continue
        neu = _flesch_text(neu_text, pfad)
        alt_text = _git("show", f"{basis}:{pfad}")
        alt = (_flesch_text(alt_text.stdout, pfad)
               if alt_text.returncode == 0 and alt_text.stdout else None)
        grund = bewerte(neu, alt, ist_neu=(status == "A" or alt is None))
        if grund:
            befunde.append(f"{pfad}: {grund}")
        elif neu is not None:
            hinweise.append(f"{pfad}: Flesch {neu:.1f} – in Ordnung")
    return befunde, hinweise


def selftest() -> int:
    fails: list[str] = []
    boden = rc.FLOOR_MIN

    def muss(bedingung: bool, text: str) -> None:
        if not bedingung:
            fails.append(text)

    muss(bewerte(boden + 1, None, True) is None, "guter neuer Artikel wird gemeldet")
    muss(bewerte(boden - 1, None, True) is not None, "schlechter neuer Artikel bleibt unerkannt")
    muss(bewerte(boden - 2, boden + 1, False) is not None,
         "Verschlechterung unter den Boden bleibt unerkannt")
    muss(bewerte(boden - 2, boden - 3, False) is None,
         "Altbestand unter dem Boden wird bei Verbesserung blockiert (Fehlalarm)")
    muss(bewerte(boden - 3, boden - 2, False) is not None,
         "weitere Verschlechterung unter dem Boden bleibt unerkannt")
    muss(bewerte(boden - 2, boden - 2, False) is None,
         "unveränderter Altbestand wird blockiert (Fehlalarm)")
    muss(bewerte(None, 70.0, False) is not None, "nicht messbarer Text gilt als grün")
    if rc.FLOOR_MIN != rc.NEW_FLESCH_MIN:
        fails.append("Boden und Publish-Schwelle sind auseinandergelaufen (R6)")
    if fails:
        print("🛑 LESBARKEITS-DIFF-WACHE – SELBSTTEST FEHLGESCHLAGEN:")
        for f in fails:
            print("  ·", f)
        return 2
    print("✅ Lesbarkeits-Diff-Wache: Selbsttest grün "
          f"(Schwelle {boden:g}, Regression vs. Altbestand, Entwürfe frei).")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selbsttest" in argv:
        return selftest()
    basis = "origin/main"
    rest = [a for a in argv if a != "--basis"]
    if "--basis" in argv:
        i = argv.index("--basis")
        if i + 1 < len(argv):
            basis = argv[i + 1]
    elif rest and not rest[0].startswith("-"):
        basis = rest[0]
    elif os.environ.get("GITHUB_BASE_REF"):
        basis = f"origin/{os.environ['GITHUB_BASE_REF']}"

    try:
        befunde, hinweise = pruefe(basis)
    except RuntimeError as exc:
        print(f"🛑 Lesbarkeits-Diff-Wache nicht durchführbar: {exc}", file=sys.stderr)
        return 2

    for h in hinweise:
        print(f"  · {h}")
    if befunde:
        print(f"\n❌ {len(befunde)} Live-Artikel würde unter dem Flesch-Boden "
              f"{rc.FLOOR_MIN:g} landen:")
        for b in befunde:
            print(f"  - {b}")
        print("\nHebel: kurze Sätze, aktive Verben, gebräuchliche Wörter "
              "(2–3 Silben). Vor dem Speichern messen:\n"
              "  python3 scripts/readability_check.py --file <pfad>")
        return 1
    print(f"✅ Keine neue Lesbarkeits-Regression unter Flesch {rc.FLOOR_MIN:g}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
