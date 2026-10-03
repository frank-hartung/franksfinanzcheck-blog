#!/usr/bin/env python3
# ============================================================
#  POPPY-WERKBANK – Einsammeln (Quellen → Insight-Karten)
#  ------------------------------------------------------------
#  Sammelt Quellen ein und legt sie als Karten auf dem Board ab
#  (data/poppy/cards/). Unterstützte Quellen:
#
#    • YouTube-Video        – Transkript (youtube-transcript-api, gratis)
#    • YouTube-Kanal/Feed   – neueste Videos als Einzelkarten
#    • RSS/Atom/Podcast     – Episoden/Beiträge (Shownotes; Audio-Transkription
#                             per Gratis-Whisper auf Groq, opt-in)
#    • Artikel-URL          – Lesetext (trafilatura, sonst eingebauter Extrakt)
#    • PDF (URL/Pfad)       – Text via pypdf
#    • Eigene Notiz         – freier Text
#
#  Jede Karte bekommt Insights (Gratis-KI Groq→Gemini, sonst Heuristik),
#  einen Artikel-Winkel und eine Pillar-Zuordnung. Duplikate (gleiche
#  Quell-URL) werden übersprungen.
#
#  Nutzung:
#    python3 scripts/poppy_ingest.py --quelle "https://youtu.be/XXX"
#    python3 scripts/poppy_ingest.py --quelle "Notiz von Frank: ..." \
#                                    --quelle "https://finanztip.de/feed/"
#    python3 scripts/poppy_ingest.py --watchlist
#    python3 scripts/poppy_ingest.py --offline --quelle "Demo-Notiz"
#    POPPY_QUELLEN="url1
#    url2" python3 scripts/poppy_ingest.py   (Workflow-Variante)
#
#  Veröffentlichung: NIE – Poppy schreibt nur Karten/Entwürfe.
# ============================================================
from __future__ import annotations

import argparse
import os
import sys
import urllib.parse

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import poppy_lib as lib  # noqa: E402


def _max_neu(quelle_cfg: dict, einstellungen: dict, explizit: int | None) -> int:
    if explizit:
        return explizit
    if quelle_cfg.get("max_neu"):
        return int(quelle_cfg["max_neu"])
    return int(einstellungen["max_karten_pro_lauf"])


def sammle_eine(eingabe: str, einstellungen: dict, transkribieren: bool,
                offline: bool, dry_run: bool = False) -> dict | None:
    """Eine Quelle → eine Karte (oder None bei Fehler/Duplikat)."""
    if offline:
        karte = lib.neue_karte(
            "text", titel="Offline-Demokarte der Poppy-Werkbank",
            url="",
            rohtext=("Demotext: Die Strompreise für Neukunden liegen 2026 "
                     "laut Musterquelle rund 12 Prozent unter dem des "
                     "Grundversorgers. Ein Wechsel spart im Modellfall "
                     "etwa 300 Euro im Jahr. Wichtig: Preisgarantie und "
                     "Kündigungsfristen prüfen."),
            methode="offline-demo")
        lib.insights_generieren(karte)
        return karte

    typ, wert = lib.erkenne_typ(eingabe)
    print(f"\n▶ Sammle ein: [{typ}] {lib.kuerze(eingabe, 90)[0]}")

    if typ == "youtube":
        video_id = lib.youtube_video_id(wert)
        titel, autor = lib.hole_oembed(wert)
        transkript, methode = (lib.hole_youtube_transkript(video_id)
                               if video_id else (None, "keine video-id"))
        rohtext = transkript or ""
        hinweis = "" if rohtext else (
            "Kein Transkript verfügbar – Karte nur mit Metadaten; "
            "vor dem Verwerten ggf. manuell ergänzen.")
        karte = lib.neue_karte(
            "youtube", titel=titel or f"YouTube-Video {video_id}",
            url=wert, rohtext=rohtext, autor=autor, methode=methode,
            hinweis=hinweis)
        karte["quelle"]["video_id"] = video_id

    elif typ == "youtube_kanal":
        # Kanal → neueste Videos einzeln einsammeln (keine Karte fürs Board)
        feed_url = lib.youtube_feed_url(wert)
        if "channel_id=" not in feed_url:
            print("  ⚠ Kanal-ID konnte nicht aufgelöst werden – "
                  "bitte videos.xml-URL mit channel_id direkt angeben.")
            return None
        eintraege = lib.hole_feed(feed_url)
        gesammelt = 0
        for e in eintraege[:einstellungen["max_karten_pro_lauf"]]:
            if not e.get("link") or lib.karte_existiert(e["link"]):
                continue
            karte = _karte_aus_feed_eintrag(e, "youtube", einstellungen,
                                            transkribieren)
            if karte:
                _fertigstellen(karte, dry_run)
                gesammelt += 1
        if gesammelt == 0:
            print("  ℹ Keine neuen Videos fürs Board.")
        return None  # Kanal-Ebene erzeugt selbst keine Karte

    elif typ == "feed":
        eintraege = lib.hole_feed(wert)
        if not eintraege:
            print("  ⚠ Feed leer oder nicht erreichbar.")
            return None
        gesammelt = 0
        for e in eintraege[:einstellungen["max_karten_pro_lauf"]]:
            if not e.get("link") or lib.karte_existiert(e["link"]):
                continue
            # YouTube-Feed-Eintrag? Dann Transkript statt Shownotes holen.
            ist_yt = "youtube.com/watch" in e.get("link", "")
            karte = _karte_aus_feed_eintrag(
                e, "youtube" if ist_yt else "podcast", einstellungen,
                transkribieren and not ist_yt)
            if karte:
                _fertigstellen(karte, dry_run)
                gesammelt += 1
        if gesammelt == 0:
            print("  ℹ Keine neuen Einträge fürs Board.")
        return None

    elif typ == "pdf":
        text = lib.hole_pdf(wert)
        if not text:
            print("  ⚠ PDF ohne auswertbaren Text.")
            return None
        karte = lib.neue_karte("pdf",
                               titel=os.path.basename(
                                   urllib.parse.urlparse(wert).path)
                               or "PDF-Dokument",
                               url=wert, rohtext=text, methode="pypdf")

    elif typ == "artikel":
        text, titel = lib.hole_artikel(wert)
        if not text or len(text) < 200:
            print("  ⚠ Artikel-Lesetext zu kurz/leer – übersprungen.")
            return None
        karte = lib.neue_karte("artikel", titel=titel or wert, url=wert,
                               rohtext=text, methode="trafilatura")

    else:  # text
        karte = lib.neue_karte("text",
                               titel=lib.kuerze(eingabe, 60)[0], url="",
                               rohtext=eingabe, methode="notiz")

    if lib.karte_existiert(karte["quelle"]["url"]):
        print("  ℹ Karte existiert bereits (Duplikat) – übersprungen.")
        return None
    return karte


def _karte_aus_feed_eintrag(e: dict, typ: str, einstellungen: dict,
                            transkribieren: bool) -> dict | None:
    """Feed-Eintrag → Karte; YouTube-Videos bekommen ihr Transkript."""
    url = e.get("link") or ""
    rohtext = (e.get("beschreibung") or "").strip()
    methode = "shownotes"
    if typ == "youtube":
        video_id = lib.youtube_video_id(url)
        titel, autor = lib.hole_oembed(url)
        transkript, methode = (lib.hole_youtube_transkript(video_id)
                               if video_id else (None, "keine video-id"))
        rohtext = transkript or rohtext
    else:
        titel = e.get("titel") or url
        autor = ""
        if transkribieren and e.get("audio_url") \
                and einstellungen.get("audio_transkription"):
            text, methode = lib.transkribiere_audio(e["audio_url"])
            if text:
                rohtext = text
            else:
                print(f"  ⚠ Audio-Transkription übersprungen: {methode}")
    if not rohtext and not titel:
        return None
    karte = lib.neue_karte(typ, titel=titel, url=url, rohtext=rohtext,
                           autor=autor, datum=e.get("datum") or "",
                           methode=methode,
                           hinweis="" if len(rohtext) > 400 else
                           "Kurzer Quellentext (Shownotes) – vor dem "
                           "Verwerten ggf. ergänzen.")
    return karte


def _fertigstellen(karte: dict, dry_run: bool) -> None:
    """Insights erzeugen + speichern (mit Offline-Fallback)."""
    lib.insights_generieren(karte)
    if dry_run:
        print(f"  [Dry-Run] Karte {karte['id']} (nicht gespeichert): "
              f"{len(karte['insights'])} Insights, Pillar {karte['pillar'] or '—'}")
        return
    pfad = lib.speichere_karte(karte)
    print(f"  ✅ Karte gespeichert: {os.path.relpath(pfad, BLOG_DIR)}")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Poppy-Werkbank: Quellen einsammeln → Insight-Karten")
    ap.add_argument("--quelle", action="append", default=[],
                    help="Quelle: YouTube-URL, Kanal-URL, Feed-URL, "
                         "Artikel-URL, PDF oder freie Notiz (mehrfach möglich)")
    ap.add_argument("--watchlist", action="store_true",
                    help="Aktive Quellen aus data/poppy/quellen.yaml abrufen")
    ap.add_argument("--max-pro-quelle", type=int, default=None,
                    help="Max. neue Karten pro Quelle (überschreibt quellen.yaml)")
    ap.add_argument("--transkribieren", action="store_true",
                    help="Podcast-Audio per Gratis-Whisper (Groq) transkribieren")
    ap.add_argument("--offline", action="store_true",
                    help="Demo-Karte ohne Netzwerk (Pipeline-Test)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Karten anzeigen, aber nichts speichern")
    ap.add_argument("--selftest", action="store_true",
                    help="Fail-closed-Selbsttest (Exit 2 bei Defekt)")
    args = ap.parse_args()

    if args.selftest:
        return lib.selbsttest()

    einstellungen = lib.lade_einstellungen()
    quellen = list(args.quelle)
    env_quellen = os.environ.get("POPPY_QUELLEN", "")
    if env_quellen:
        quellen += [z for z in
                    (zeile.strip() for zeile in env_quellen.splitlines())
                    if z]

    transkribieren = args.transkribieren or bool(
        einstellungen.get("audio_transkription"))

    gesamt = 0
    report_zeilen: list[str] = []

    # 1) Watchlist (Kanäle/Feeds) – jeder Eintrag sammelt selbst ein
    if args.watchlist:
        watchlist = lib.lade_watchlist()
        if not watchlist:
            print("ℹ Watchlist leer oder alles inaktiv "
                  "(data/poppy/quellen.yaml).")
        for q in watchlist:
            url = (q.get("url") or "").strip()
            if not url:
                continue
            print(f"\n▶ Watchlist: {q.get('id') or url} "
                  f"({q.get('typ', 'auto')})")
            typ, wert = lib.erkenne_typ(url)
            # Kanal-URLs: Feed auflösen, sonst Einträge direkt holen
            if typ == "youtube_kanal":
                feed_url = lib.youtube_feed_url(wert)
                eintraege = lib.hole_feed(feed_url) if "channel_id=" in feed_url else []
                if not eintraege:
                    print("  ⚠ Keine Einträge (Kanal-ID auflösbar?).")
                    continue
                pro_runde = _max_neu(q, einstellungen, args.max_pro_quelle)
                for e in eintraege[:pro_runde]:
                    if not e.get("link") or lib.karte_existiert(e["link"]):
                        continue
                    karte = _karte_aus_feed_eintrag(e, "youtube",
                                                    einstellungen, False)
                    if karte:
                        _fertigstellen(karte, args.dry_run)
                        gesamt += 1
            elif typ == "youtube":
                # Einzelvideo direkt in der Watchlist → wie --quelle behandeln
                karte = sammle_eine(url, einstellungen, transkribieren,
                                    offline=False)
                if karte:
                    _fertigstellen(karte, args.dry_run)
                    gesamt += 1
            elif typ == "feed":
                # Feed/Feed-Podcast: max_neu dieser Quelle respektieren
                eintraege = lib.hole_feed(wert)
                if not eintraege:
                    print("  ⚠ Feed leer oder nicht erreichbar.")
                    continue
                pro_runde = _max_neu(q, einstellungen, args.max_pro_quelle)
                for e in eintraege[:pro_runde]:
                    if not e.get("link") or lib.karte_existiert(e["link"]):
                        continue
                    ist_yt = "youtube.com/watch" in e.get("link", "")
                    karte = _karte_aus_feed_eintrag(
                        e, "youtube" if ist_yt else "podcast", einstellungen,
                        transkribieren and not ist_yt)
                    if karte:
                        _fertigstellen(karte, args.dry_run)
                        gesamt += 1
            else:
                eintraege = lib.hole_feed(wert) if typ == "artikel" else []
                if eintraege:  # hinter einer „normalen“ URL steckt ein Feed
                    pro_runde = _max_neu(q, einstellungen, args.max_pro_quelle)
                    for e in eintraege[:pro_runde]:
                        if not e.get("link") or lib.karte_existiert(e["link"]):
                            continue
                        karte = _karte_aus_feed_eintrag(e, "podcast",
                                                        einstellungen,
                                                        transkribieren)
                        if karte:
                            _fertigstellen(karte, args.dry_run)
                            gesamt += 1
                elif typ == "artikel":
                    karte = sammle_eine(url, einstellungen, transkribieren,
                                        offline=False)
                    if karte:
                        _fertigstellen(karte, args.dry_run)
                        gesamt += 1

    # 2) Einzelquellen von der Kommandozeile/Env
    for eingabe in quellen:
        karte = sammle_eine(eingabe, einstellungen, transkribieren,
                            offline=args.offline)
        if karte:
            _fertigstellen(karte, args.dry_run)
            gesamt += 1

    if not args.dry_run:
        report_zeilen.append(
            f"- **Einsammeln ({lib.heute_iso()}):** {gesamt} neue Karte(n) "
            "auf dem Board. Verwerten mit "
            "`python3 scripts/poppy_repurpose.py --auto`.")
        report_zeilen.append(
            "- Board: `python3 scripts/poppy_board.py` bauen, "
            "`npm run poppy:serve` öffnen.")
        lib.schreibe_report(report_zeilen)

    if gesamt == 0 and quellen and not args.watchlist:
        print("\nℹ Nichts Neues fürs Board (Duplikate/Fehler siehe oben).")
        return 1
    print(f"\n✅ Poppy-Werkbank: {gesamt} neue Karte(n).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
