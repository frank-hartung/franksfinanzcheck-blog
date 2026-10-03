#!/usr/bin/env python3
# ============================================================
#  POPPY-WERKBANK – Board bauen (Dashboard der Insight-Karten)
#  ------------------------------------------------------------
#  Baut aus data/poppy/cards/*.json das „Poppy-Board“: eine lokale,
#  offline-fähige Übersicht aller Quellkarten mit Status, Insights
#  und Erzeugnissen (Blog-Entwurf, Newsletter, Mastodon, Pinterest).
#
#  Muster wie beim SEO-Cockpit: Vorlage + Assets liegen in
#  tools/poppy-board/, die generierte Ausgabe in .cache/poppy-board/
#  (gitignored). Keine externen Abhängigkeiten, keine Netzwerk-
#  requests, keine Datenübertragung.
#
#  Nutzung:
#    python3 scripts/poppy_board.py            # Board bauen
#    python3 scripts/poppy_board.py --json     # nur board.json schreiben
#    npm run poppy:serve                       # lokal öffnen (http.server)
#    python3 scripts/poppy_board.py --selftest # fail-closed Selbsttest
# ============================================================
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import poppy_lib as lib  # noqa: E402

PLACEHOLDER = "/*BOARD_DATA*/"


def board_payload(karten: list | None = None) -> dict:
    """Karten → Board-Payload (nur Felder, die das Dashboard braucht)."""
    karten = karten if karten is not None else lib.lade_karten()
    typ_icons = {"youtube": "▶", "podcast": "🎙", "artikel": "📰",
                 "pdf": "📄", "text": "✎"}
    eintraege = []
    for k in karten:
        quelle = k.get("quelle", {})
        erg = k.get("erzeugnisse") or {}
        blog = erg.get("blog") or {}
        eintraege.append({
            "id": k.get("id", ""),
            "status": k.get("status", lib.STATUS_NEU),
            "typ": quelle.get("typ", "text"),
            "typ_icon": typ_icons.get(quelle.get("typ", ""), "✎"),
            "titel": quelle.get("titel", "(ohne Titel)"),
            "url": quelle.get("url", ""),
            "autor": quelle.get("autor", ""),
            "datum": quelle.get("veroeffentlicht", ""),
            "inhalt_zeichen": (k.get("inhalt") or {}).get("zeichen", 0),
            "inhalt_methode": (k.get("inhalt") or {}).get("methode", ""),
            "hinweis": (k.get("inhalt") or {}).get("hinweis", ""),
            "insights": k.get("insights") or [],
            "winkel": k.get("winkel", ""),
            "pillar": k.get("pillar", ""),
            "schlagworte": k.get("schlagworte") or [],
            "artikel_titel": k.get("artikel_titel", ""),
            "erzeugnisse": {
                "blog_slug": blog.get("slug", ""),
                "blog_zeichen": blog.get("zeichen", 0),
                "blog_provider": blog.get("provider", ""),
                "freigabe": blog.get("freigabe", ""),
                "kurzantwort": erg.get("kurzantwort", ""),
                "newsletter": erg.get("newsletter") or {},
                "mastodon": erg.get("mastodon", ""),
                "pinterest": erg.get("pinterest") or {},
                "artikel_url": erg.get("artikel_url", ""),
                "sozial_provider": erg.get("sozial_provider", ""),
            },
            "angelegt": (k.get("historie") or [{}])[0].get("zeit", ""),
        })
    neu = sum(1 for e in eintraege if e["status"] == lib.STATUS_NEU)
    verwertet = len(eintraege) - neu
    return {
        "stand": lib.now_utc_iso(),
        "gesamt": len(eintraege),
        "neu": neu,
        "verwertet": verwertet,
        "karten": eintraege,
    }


def board_bauen(payload: dict | None = None,
                ausgabe: str | None = None) -> str:
    """Payload → .cache/poppy-board/index.html + board.json."""
    payload = payload or board_payload()
    ausgabe = ausgabe or lib.BOARD_OUTPUT
    os.makedirs(ausgabe, exist_ok=True)
    template_pfad = os.path.join(lib.BOARD_ASSETS, "index.html")
    if not os.path.exists(template_pfad):
        print(f"⚠ Vorlage fehlt: {template_pfad}")
        return ""
    with open(template_pfad, encoding="utf-8") as fh:
        template = fh.read()
    if PLACEHOLDER not in template:
        raise RuntimeError("Vorlage ohne /*BOARD_DATA*/-Platzhalter")
    daten = (json.dumps(payload, ensure_ascii=False)
             .replace("<", "\\u003c").replace(">", "\\u003e")
             .replace("&", "\\u0026"))
    index_pfad = os.path.join(ausgabe, "index.html")
    with open(index_pfad, "w", encoding="utf-8") as fh:
        fh.write(template.replace(PLACEHOLDER, daten))
    for name in ("app.js", "style.css"):
        quelle = os.path.join(lib.BOARD_ASSETS, name)
        if os.path.exists(quelle):
            shutil.copyfile(quelle, os.path.join(ausgabe, name))
    with open(os.path.join(ausgabe, "board.json"), "w",
              encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return index_pfad


def _selbsttest() -> int:
    print("Poppy-Board – Selbsttest (offline)")
    fehler = []
    karte = lib.neue_karte(
        "youtube", titel="Selbsttest: Strompreis-Video", url="https://youtu.be/x",
        rohtext="x" * 100, methode="selbsttest")
    karte["insights"] = ["Strompreis sinkt um 12 Prozent."]
    karte["pillar"] = "strom-sparen"
    payload = board_payload([karte])
    if payload["gesamt"] != 1 or payload["neu"] != 1 \
            or payload["karten"][0]["typ"] != "youtube":
        fehler.append("Payload-Kennzahlen falsch")
    if payload["karten"][0]["typ_icon"] != "▶":
        fehler.append("Typ-Icon fehlt")
    verwertet = dict(karte)
    verwertet["status"] = lib.STATUS_VERWERTET
    if board_payload([verwertet])["verwertet"] != 1:
        fehler.append("Status-Zählung verwertet falsch")
    template = os.path.join(lib.BOARD_ASSETS, "index.html")
    if not os.path.exists(template):
        fehler.append(f"Vorlage fehlt: {template}")
    elif PLACEHOLDER not in open(template, encoding="utf-8").read():
        fehler.append("Vorlage ohne /*BOARD_DATA*/-Platzhalter")
    for name in ("app.js", "style.css"):
        if not os.path.exists(os.path.join(lib.BOARD_ASSETS, name)):
            fehler.append(f"Asset fehlt: {name}")
    if fehler:
        print("  ✗ " + "\n  ✗ ".join(fehler))
        return 2
    print("  ✓ Payload, Status-Zählung, Vorlage und Assets: in Ordnung.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Poppy-Werkbank: Board-Dashboard bauen")
    ap.add_argument("--json", action="store_true",
                    help="nur board.json schreiben (ohne HTML)")
    ap.add_argument("--ausgabe", default=None,
                    help="Ausgabeverzeichnis (Default .cache/poppy-board)")
    ap.add_argument("--selftest", action="store_true",
                    help="Fail-closed-Selbsttest (Exit 2 bei Defekt)")
    args = ap.parse_args()

    if args.selftest:
        return _selbsttest()

    payload = board_payload()
    if args.json:
        os.makedirs(args.ausgabe or lib.BOARD_OUTPUT, exist_ok=True)
        ziel = os.path.join(args.ausgabe or lib.BOARD_OUTPUT, "board.json")
        with open(ziel, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        print(f"✅ board.json: {ziel}")
        return 0
    pfad = board_bauen(payload, args.ausgabe)
    if not pfad:
        return 2
    print(f"✅ Board: {pfad}")
    print(f"   Karten: {payload['gesamt']} "
          f"({payload['neu']} neu, {payload['verwertet']} verwertet)")
    print("   Öffnen: npm run poppy:serve")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
