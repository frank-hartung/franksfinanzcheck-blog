#!/usr/bin/env python3
# ============================================================
#  AGC-CONTEXT – Brücke zwischen Autopilot und Schreiber (Stufe 4)
#  ------------------------------------------------------------
#  Sammelt den kompletten AGC-Kontext für einen Artikel und liefert
#  ihn als Prompt-Block an generate_drafts.py:
#
#    1) MARKEN-HIRN      (Brand Brain: Stimme, Zielgruppe, Regeln)
#    2) KAMPAGNEN-CTA    (aktive Kampagne → CTA-Override)
#    3) TAGES-RECHERCHE  (geroutete Signale aus dem Research-Report)
#
#  WICHTIG: Diese Datei DARF NIE werfen. Fehlt ein Baustein (kein
#  Research-Report, keine Kampagne), wird der Block einfach kleiner –
#  die Pipeline läuft weiter wie bisher (Rückwärtskompatibilität).
#
#  Aufruf (Test/Preview):
#    python3 scripts/agc_context.py "Stromanbieter wechseln" \
#        --pillar strom-sparen --keywords "Stromvergleich,Stromkosten"
# ============================================================
import os
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import yaml  # noqa: E402


def _load_yaml(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except Exception:
        return {}


def _brand_block():
    try:
        import brand_brain as bb
        return bb.compact_context(bb.load_brand_brain())
    except Exception:
        return ""


def _campaign_block(pillar=None):
    try:
        import campaign_manager as cm
        campaigns = cm.active_campaigns()
        camp = cm.campaign_for(campaigns, pillar) if pillar else None
        if not camp or not camp.get("cta"):
            return ""
        return (f"AKTIVE KAMPAGNE: {camp.get('name')} "
                f"({camp.get('goal', '')}).\n"
                f"KAMPAGNEN-CTA (für die Affiliate-CTA-Zeile verwenden): "
                f"{camp.get('cta')}")
    except Exception:
        return ""


def _research_block(topic, pillar=None, keywords=None):
    try:
        import research_engine as re_
        report = _load_yaml(re_.LATEST_FILE)
        if not report or "teams" not in report:
            return ""
        return re_.build_brief(report, topic, pillar=pillar, keywords=keywords)
    except Exception:
        return ""


def build_context_block(topic, pillar=None, keywords=None, pin=None):
    """Liefert den AGC-Prompt-Block (nie eine Exception)."""
    blocks = []
    brand = _brand_block()
    if brand:
        blocks.append(brand)
    research = _research_block(topic, pillar, keywords)
    if research:
        blocks.append(research)
    campaign = _campaign_block(pillar)
    if campaign:
        blocks.append(campaign)
    if not blocks:
        return ""
    return ("\n\nAGC-KONTEXT (von der Blog-Automatik bereitgestellt – "
            "übernehmen, ohne eigene Fakten zu erfinden):\n"
            + "\n\n".join(blocks))


def main():
    if len(sys.argv) < 2:
        print("Aufruf: agc_context.py <Thema> [--pillar X] [--keywords a,b]")
        return 1
    topic = sys.argv[1]
    pillar = None
    keywords = None
    if "--pillar" in sys.argv:
        p = sys.argv.index("--pillar")
        if len(sys.argv) > p + 1:
            pillar = sys.argv[p + 1]
    if "--keywords" in sys.argv:
        k = sys.argv.index("--keywords")
        if len(sys.argv) > k + 1:
            keywords = [x.strip() for x in sys.argv[k + 1].split(",") if x.strip()]
    print(build_context_block(topic, pillar=pillar, keywords=keywords))
    return 0


if __name__ == "__main__":
    sys.exit(main())
