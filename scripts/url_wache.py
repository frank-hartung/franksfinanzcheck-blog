#!/usr/bin/env python3
"""url_wache.py – Wache für verschwindende URLs.

WARUM (19.10.2026): Ein Beitrag wurde umbenannt oder gelöscht, und niemand hat es gemerkt. Dadurch
entstanden 117 Alt-URLs ohne Weiterleitung. Diese Wache vergleicht die Live-URLs mit einem Snapshot.
Verschwindet eine URL, muss sie einen Eintrag haben: in data/weiterleitungen.yaml (Ziel) oder in
data/url_entfallen.yaml (bewusst 404). Sonst ist das ein Befund.

Umbenennungen schlägt die Wache über den datumsbereinigten Slug vor. Die Entscheidung trifft ein Mensch.

Befunde haben owner (auto|human), severity (P1–P3) und channel (CLAUDE.md).

Nutzung:
    python3 scripts/url_wache.py              Vergleich gegen data/url_snapshot.json (exit 1 bei Befund)
    python3 scripts/url_wache.py --snapshot   Snapshot neu schreiben (nur nach bewusster Änderung)
    python3 scripts/url_wache.py --selftest   Selbsttest

Exit: 0 = grün · 1 = Befund · 2 = Fehler
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BLOG_DIR)

from scripts import weiterleitungen as wl  # noqa: E402

SNAPSHOT = os.path.join(BLOG_DIR, "data", "url_snapshot.json")
CHANNEL = "seo-technik"


def befund(url: str, text: str, owner: str, severity: str) -> dict:
    return {"url": url, "befund": text, "owner": owner, "severity": severity, "channel": CHANNEL}


def vorschlag(verschwunden: str, live: set[str]) -> str:
    """Nur Vorschlag: gleicher datumsbereinigter Slug unter einer live Beitrags-URL."""
    rest = wl.slug_rest(verschwunden)
    if not rest:
        return "kein Vorschlag"
    treffer = sorted(u for u in live if u.startswith("/posts/") and wl.slug_rest(u) == rest)
    if treffer:
        return "Vorschlag (datumsbereinigt, manuell prüfen): " + ", ".join(treffer)
    return "kein Vorschlag (kein Beitrag mit gleichem Slug-Rest live)"


def vergleiche(snapshot: set[str], live: set[str], eintraege: list[dict], entfallen: list[dict]) -> tuple[list[dict], list[str]]:
    """Gibt (Befunde, Hinweise) zurück. Hinweise sind keine Befunde."""
    befunde: list[dict] = []
    hinweise: list[str] = []
    ziel_von = {e["von"] for e in eintraege}
    bewusst_404 = {e["von"] for e in entfallen}

    for u in sorted(snapshot - live):
        if u in ziel_von or u in bewusst_404:
            continue  # bereits entschieden
        if u.startswith("/tags/"):
            befunde.append(befund(u, "Tag-Archiv verschwunden, nicht in url_entfallen.yaml eingetragen", "human", "P3"))
        else:
            befunde.append(befund(u, "Live-URL verschwunden ohne Weiterleitung oder bewusst-404-Eintrag. " + vorschlag(u, live), "human", "P1"))

    for e in eintraege:
        if e["von"] in live:
            befunde.append(befund(e["von"], "Weiterleitungsquelle ist wieder live – Eintrag in weiterleitungen.yaml entfernen", "human", "P1"))
        if e["nach"] not in live:
            befunde.append(befund(e["von"], f"Ziel {e['nach']} ist nicht mehr live", "human", "P1"))

    neu = sorted(live - snapshot)
    if neu:
        hinweise.append(f"{len(neu)} neue Live-URL(n) seit Snapshot (kein Befund): " + ", ".join(neu[:5]) + (" …" if len(neu) > 5 else ""))
    return befunde, hinweise


def lade_snapshot(pfad: str = SNAPSHOT) -> set[str]:
    with open(pfad, encoding="utf-8") as fh:
        return set(json.load(fh)["urls"])


def schreibe_snapshot(live: set[str], pfad: str = SNAPSHOT) -> None:
    daten = {
        "stand": "2026-10-19",
        "hinweis": "Generiert von scripts/url_wache.py --snapshot. Nur nach bewusster Änderung neu schreiben.",
        "anzahl": len(live),
        "urls": sorted(live),
    }
    with open(pfad, "w", encoding="utf-8") as fh:
        json.dump(daten, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


def selftest() -> int:
    fehler: list[str] = []

    def check(name: str, ok: bool) -> None:
        if not ok:
            fehler.append(name)

    live = {"/posts/2026-10-07-neu/", "/pillar/konto-karten/"}
    snap = live | {"/posts/2026-09-21-alt/", "/posts/2026-08-10-x/"}
    eint = [{"von": "/posts/2026-08-10-x/", "nach": "/pillar/konto-karten/", "regel": "C", "grund": "Pillar-Fallback Test"}]
    ent: list[dict] = []
    b, h = vergleiche(snap, live, eint, ent)
    check("unbelegte verschwundene URL ist Befund", any(x["url"] == "/posts/2026-09-21-alt/" for x in b))
    check("Befund hat owner/severity/channel", all(x["owner"] in ("auto", "human") and x["severity"] in ("P1", "P2", "P3") and x["channel"] for x in b))
    check("Weiterleitung schließt Befund", not any(x["url"] == "/posts/2026-08-10-x/" for x in b))
    check("Vorschlag nennt gleichen Slug-Rest",
          "/posts/2026-10-01-alt/" in vorschlag("/posts/2026-09-21-alt/", live | {"/posts/2026-10-01-alt/"}))
    b2, _ = vergleiche({"/posts/a/"}, {"/posts/a/"}, [], [])
    check("unverändert ist grün", b2 == [])
    ent2 = [{"von": "/posts/2026-09-21-alt/", "regel": "D", "grund": "bewusst 404 Test"}]
    b3, _ = vergleiche(snap, live, eint, ent2)
    check("bewusst 404 schließt Befund", not any(x["url"] == "/posts/2026-09-21-alt/" for x in b3))
    b4, _ = vergleiche({"/tags/x/"}, set(), [], [])
    check("Tag-Verschwinden ist P3", any(x["severity"] == "P3" for x in b4))
    b5, _ = vergleiche(set(), {"/posts/2026-08-10-x/"}, eint, [])
    check("Quelle live erkannt", any("wieder live" in x["befund"] for x in b5))
    with tempfile.TemporaryDirectory() as tmp:
        pf = os.path.join(tmp, "s.json")
        schreibe_snapshot(live, pf)
        check("Snapshot Roundtrip", lade_snapshot(pf) == live)
    if fehler:
        print("SELBSTTEST FEHLGESCHLAGEN:")
        for x in fehler:
            print("  -", x)
        return 2
    print("url_wache.py Selbsttest ok (8 Fälle)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--snapshot", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    live = wl.live_urls(BLOG_DIR)
    if a.snapshot:
        schreibe_snapshot(live)
        print(f"Snapshot geschrieben: {len(live)} URLs → {SNAPSHOT}")
        return 0
    if not os.path.exists(SNAPSHOT):
        print("Kein Snapshot – zuerst --snapshot ausführen", file=sys.stderr)
        return 2
    eintraege, entfallen = wl.lade_quelle(BLOG_DIR)
    b, h = vergleiche(lade_snapshot(), live, eintraege, entfallen)
    for x in h:
        print("Hinweis:", x)
    for x in b:
        print(f"BEFUND [{x['severity']} · owner={x['owner']} · channel={x['channel']}] {x['url']}: {x['befund']}")
    if b:
        print(f"{len(b)} Befund(e) – Entscheidung nötig (Weiterleitung in data/weiterleitungen.yaml oder bewusst 404 in data/url_entfallen.yaml)")
        return 1
    print(f"url_wache: grün ({len(live)} Live-URLs, Snapshot {len(lade_snapshot())})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
