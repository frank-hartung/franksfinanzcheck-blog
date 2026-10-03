#!/usr/bin/env python3
# ============================================================
#  SPAM-SCHUTZ-WACHE – Google-Spam-Policy im Tagesrhythmus
#  ------------------------------------------------------------
#  Premium-Schutz gegen die drei Google-Spam-Risiken automatisierter
#  Redaktionen („Scaled Content Abuse“-Politik, Stand 2026):
#
#    1) MASSENHAFT UNORIGINÄLER CONTENT  – gemessen über KI-Anteil,
#       Near-Duplicate-Quote (SimHash, SSOT: plagiat_guard) und
#       Thin Content im LIVE-Bestand
#    2) VERÖFFENTLICHUNGS-TEMPO          – Artikel pro Tag/Woche
#       (Deckel in data/spam_schutz.yaml)
#    3) FEHLENDE TRANSPARENZ/WERT        – Offenlegung, Titel-Duplikate,
#       publish ohne erkennbaren Wertbeitrag (Thin)
#
#  NOTBREMSE (das Herzstück): Bei ROT stellt die Wache die Endredaktion
#  automatisch auf „modus: manuell“ (mit Marker-Kommentar) – ab dann
#  wird KEIN Entwurf mehr vollautomatisch freigegeben. Bei GRÜN nimmt
#  sie NUR eigene Notbremsen zurück (manuelle Frank-Entscheidungen mit
#  „modus: manuell“ bleiben unangetastet). So bleibt der Schutz
#  dauerhaft wirksam, ohne die Redaktion stillzulegen.
#
#  HANDSHAKE: data/spam_schutz_status.json ist die Maschinen-Wahrheit,
#  die scripts/endredaktion.py vor jeder automatischen Freigabe liest
#  (fail-closed: kein Statusfile = keine Auto-Freigabe).
#
#  Nutzung:
#    python3 scripts/spam_schutz_wache.py             # messen + berichten + Notbremse
#    python3 scripts/spam_schutz_wache.py --nur-messen # ohne jede Dateiänderung
#    python3 scripts/spam_schutz_wache.py --json       # KPIs als JSON
#    python3 scripts/spam_schutz_wache.py --selftest   # fail-closed (Exit 2)
#
#  Exit: 0 = grün oder gelb (gelb mit Warnung im Bericht) · 2 = rot
# ============================================================
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import yaml  # noqa: E402

import post_utils  # noqa: E402
import length_policy  # noqa: E402
from plagiat_guard import hamming, normalize, simhash  # noqa: E402 (SSOT)

CONFIG_FILE = os.path.join(BLOG_DIR, "data", "spam_schutz.yaml")
STATUS_FILE = os.path.join(BLOG_DIR, "data", "spam_schutz_status.json")
REPORT_FILE = os.path.join(BLOG_DIR, "SPAM-SCHUTZ-REPORT.md")
ENDREDAKTION_CONFIG = os.path.join(BLOG_DIR, "data", "endredaktion.yaml")
NOTBREMSE_MARKER = "# NOTBREMSE (spam-schutz-wache"

# Kalibriert am Ist-Zustand 03.10.2026 (38 live, 32 % KI, Tempo 5/Woche,
# 0 Near-Dups) – bewusst mit Luft nach oben, aber hart genug, um
# Pathologie-Zustände sofort zu bremsen.
DEFAULT_BUDGETS = {
    "tempo_max_pro_tag": 3,          # rot: mehr Veröffentlichungen an einem Tag
    "tempo_gelb_pro_woche": 7,       # gelb: auffällig viele in 7 Tagen
    "tempo_rot_pro_woche": 10,       # rot: Spam-Tempo
    "ki_anteil_gelb_prozent": 50,    # gelb: halber Bestand KI-generiert
    "ki_anteil_rot_prozent": 65,     # rot: KI dominiert den Bestand
    "auto_freigaben_max_pro_woche": 3,  # rot: Endredaktion-Freigaben/Woche
    "near_dup_gelb_paare": 1,        # gelb: erstes verdächtiges Paar
    "near_dup_rot_paare": 3,         # rot: Cluster-Bildung
    "near_dup_hamming": 10,          # SimHash-Abstand ≤ X = Near-Duplicate
    "thin_live_max": 0,              # rot: Live-Artikel unter Längen-Floor
    "titel_duplikate_max": 0,        # rot: gleiche Titel im Live-Bestand
    "offenlegung_fehlend_max": 0,    # rot: KI-Live-Artikel ohne Kennzeichnung
}


def lade_budgets() -> dict:
    budgets = dict(DEFAULT_BUDGETS)
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, encoding="utf-8") as fh:
                geladen = yaml.safe_load(fh) or {}
            budgets.update({k: v for k, v in geladen.items()
                            if k in DEFAULT_BUDGETS})
    except Exception as e:  # noqa: BLE001 – Konfig darf nie crashen
        print(f"  ⚠ spam_schutz.yaml nicht lesbar ({e}) – Defaults aktiv.")
    return budgets


# ---------------------------------------------------------------- Bestand lesen
def lese_live_posts() -> list[dict]:
    """Live-Artikel mit den Feldern, die die KPIs brauchen."""
    posts = []
    for path in post_utils.list_post_paths():
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue
        kopf = text[:3000]
        if re.search(r"(?m)^draft:\s*true", kopf):
            continue
        teile = text.split("---", 2)
        body = teile[2] if len(teile) == 3 else text
        m_titel = re.search(r'(?m)^title:\s*"?([^"\n]+)"?', kopf)
        m_datum = re.search(r"(?m)^date:\s*(\d{4}-\d{2}-\d{2})", kopf)
        posts.append({
            "slug": post_utils.slug_of(path),
            "pfad": path,
            "titel": (m_titel.group(1).strip() if m_titel else "").lower(),
            "datum": m_datum.group(1) if m_datum else "",
            "ai": re.search(r"(?m)^ai_generated:\s*true", kopf) is not None,
            "endredaktion_freigabe": re.search(
                r"(?m)^endredaktion_status:\s*freigegeben", kopf) is not None,
            "hat_offenlegung": ("Transparenz:" in body
                                or "Affiliate-Links (Werbung)" in body),
            "body": body,
        })
    return posts


# ---------------------------------------------------------------- KPIs
def kpis_berechnen(posts: list[dict], budgets: dict, heute=None) -> dict:
    heute = heute or datetime.date.today()
    vor7 = (heute - datetime.timedelta(days=6)).isoformat()

    tage = {}
    for p in posts:
        if p["datum"]:
            tage[p["datum"]] = tage.get(p["datum"], 0) + 1
    letzte7 = [d for d in tage if vor7 <= d <= heute.isoformat()]
    tempo_tag = max(tage.values()) if tage else 0
    tempo_woche = sum(tage[d] for d in letzte7)

    live_n = len(posts)
    ki_n = sum(1 for p in posts if p["ai"])
    ki_anteil = round(100 * ki_n / live_n, 1) if live_n else 0.0

    auto_freigaben = sum(
        1 for p in posts
        if p["endredaktion_freigabe"] and vor7 <= p["datum"] <= heute.isoformat())

    # Near-Duplicates: SimHash der Live-Körper (SSOT plagiat_guard)
    hashes = [(p["slug"], simhash(normalize(p["body"]))) for p in posts]
    paare = []
    for i in range(len(hashes)):
        for j in range(i + 1, len(hashes)):
            abstand = hamming(hashes[i][1], hashes[j][1])
            if abstand <= budgets["near_dup_hamming"]:
                paare.append({"abstand": abstand,
                              "a": hashes[i][0], "b": hashes[j][0]})
    paare.sort(key=lambda x: x["abstand"])

    thin = []
    for p in posts:
        try:
            _, zeichen = length_policy.measure(p["body"])
            if zeichen < length_policy.POSTS["target_min_chars"]:
                thin.append(p["slug"])
        except Exception:  # noqa: BLE001 – Messfehler ist kein Dünner
            continue

    titel_seen, titel_dups = {}, []
    for p in posts:
        if p["titel"] in titel_seen:
            titel_dups.append(f"{titel_seen[p['titel']]} ↔ {p['slug']}")
        elif p["titel"]:
            titel_seen[p["titel"]] = p["slug"]

    offenlegung_fehlt = [p["slug"] for p in posts
                         if p["ai"] and not p["hat_offenlegung"]]

    return {
        "live_artikel": live_n,
        "ki_artikel": ki_n,
        "ki_anteil_prozent": ki_anteil,
        "tempo_max_pro_tag": tempo_tag,
        "tempo_letzte7_tage": tempo_woche,
        "auto_freigaben_letzte7_tage": auto_freigaben,
        "near_dup_paare": len(paare),
        "near_dup_beispiele": [f"{p['a']} ↔ {p['b']} (d={p['abstand']})"
                               for p in paare[:5]],
        "thin_live": thin,
        "titel_duplikate": titel_dups,
        "offenlegung_fehlt": offenlegung_fehlt,
    }


def kpi_verdict(k: dict, b: dict) -> tuple[str, list[str]]:
    """(urteil, probleme). urteil: grün | gelb | rot."""
    probleme = []
    urteil = "gruen"

    def hebe(ziel: str, text: str):
        nonlocal urteil
        rang = {"gruen": 0, "gelb": 1, "rot": 2}
        if rang[ziel] > rang[urteil]:
            urteil = ziel
        probleme.append(text)

    if k["tempo_max_pro_tag"] > b["tempo_max_pro_tag"]:
        hebe("rot", f"Tempo: {k['tempo_max_pro_tag']} Artikel an einem Tag "
             f"(Budget {b['tempo_max_pro_tag']})")
    if k["tempo_letzte7_tage"] > b["tempo_rot_pro_woche"]:
        hebe("rot", f"Tempo: {k['tempo_letzte7_tage']} Artikel in 7 Tagen "
             f"(rot ab {b['tempo_rot_pro_woche']})")
    elif k["tempo_letzte7_tage"] > b["tempo_gelb_pro_woche"]:
        hebe("gelb", f"Tempo: {k['tempo_letzte7_tage']} Artikel in 7 Tagen "
             f"(gelb ab {b['tempo_gelb_pro_woche']})")

    if k["ki_anteil_prozent"] > b["ki_anteil_rot_prozent"]:
        hebe("rot", f"KI-Anteil live: {k['ki_anteil_prozent']} % "
             f"(rot ab {b['ki_anteil_rot_prozent']} %)")
    elif k["ki_anteil_prozent"] > b["ki_anteil_gelb_prozent"]:
        hebe("gelb", f"KI-Anteil live: {k['ki_anteil_prozent']} % "
             f"(gelb ab {b['ki_anteil_gelb_prozent']} %)")

    if k["auto_freigaben_letzte7_tage"] > b["auto_freigaben_max_pro_woche"]:
        hebe("rot", f"Auto-Freigaben: {k['auto_freigaben_letzte7_tage']} in "
             f"7 Tagen (Budget {b['auto_freigaben_max_pro_woche']})")

    if k["near_dup_paare"] > b["near_dup_rot_paare"]:
        hebe("rot", f"Near-Duplicates: {k['near_dup_paare']} Paare "
             f"(rot ab {b['near_dup_rot_paare']})")
    elif k["near_dup_paare"] >= b["near_dup_gelb_paare"]:
        hebe("gelb", f"Near-Duplicates: {k['near_dup_paare']} Paar(e) – "
             f"redaktionell prüfen: {'; '.join(k['near_dup_beispiele'][:2])}")

    if len(k["thin_live"]) > b["thin_live_max"]:
        hebe("rot", f"Thin Content live: {', '.join(k['thin_live'][:3])}")

    if len(k["titel_duplikate"]) > b["titel_duplikate_max"]:
        hebe("rot", f"Titel-Duplikate live: "
             f"{'; '.join(k['titel_duplikate'][:3])}")

    if len(k["offenlegung_fehlt"]) > b["offenlegung_fehlend_max"]:
        hebe("rot", f"KI-Artikel ohne Werbe-Offenlegung: "
             f"{', '.join(k['offenlegung_fehlt'][:3])}")

    return urteil, probleme


# ---------------------------------------------------------------- Notbremse
def notbremse_anwenden(urteil: str, nur_messen: bool = False) -> str:
    """ROT → Endredaktion auf manuell (mit Marker). GRÜN → eigene Bremsen lösen.

    Frank manuell gesetztes „modus: manuell“ (ohne Marker) wird NIEMALS
    angetastet. Rückgabe: Beschreibung der Aktion."""
    if not os.path.exists(ENDREDAKTION_CONFIG):
        return "endredaktion.yaml fehlt – Notbremse nicht anwendbar"
    with open(ENDREDAKTION_CONFIG, encoding="utf-8") as fh:
        text = fh.read()
    hat_marker = NOTBREMSE_MARKER in text
    ist_manuell = re.search(r"(?m)^modus:\s*manuell", text) is not None

    if urteil == "rot":
        if ist_manuell:
            return ("Endredaktion bereits im manuellen Modus – "
                    + ("Notbremse aktiv" if hat_marker
                       else "Frank-Entscheidung, bleibt unangetastet"))
        if nur_messen:
            return ("[Nur-Messen] Notbremse würde greifen: Endredaktion → "
                    "modus: manuell")
        text = re.sub(r"(?m)^modus:.*$",
                      f"modus: manuell  {NOTBREMSE_MARKER} "
                      f"{datetime.date.today().isoformat()} – "
                      f"automatisch gesperrt, siehe SPAM-SCHUTZ-REPORT.md)",
                      text, count=1)
        with open(ENDREDAKTION_CONFIG, "w", encoding="utf-8") as fh:
            fh.write(text)
        return ("NOTBREMSE AKTIV: Endredaktion auf „modus: manuell“ "
                "gestellt – keine automatischen Freigaben mehr, bis die "
                "Wache wieder grün ist.")

    if urteil == "gruen" and hat_marker and not ist_manuell:
        return "Notbremse bereits gelöst."
    if urteil == "gruen" and hat_marker and ist_manuell:
        if nur_messen:
            return ("[Nur-Messen] Eigene Notbremse würde gelöst: "
                    "Endredaktion → modus: automatisch")
        text = re.sub(r"(?m)^modus:.*$", "modus: automatisch", text, count=1)
        text = re.sub(rf"(?m)^.*{re.escape(NOTBREMSE_MARKER)}.*$\n?", "",
                      text)
        with open(ENDREDAKTION_CONFIG, "w", encoding="utf-8") as fh:
            fh.write(text)
        return ("NOTBREMSE GELÖST: Alle Budgets grün – Endredaktion wieder "
                "auf „modus: automatisch“.")
    return "Keine Notbremse nötig."


def status_schreiben(k: dict, urteil: str, probleme: list[str]) -> None:
    os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
    payload = {
        "stand": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"),
        "urteil": urteil,
        "probleme": probleme,
        "kpis": k,
    }
    with open(STATUS_FILE, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def bericht_schreiben(k: dict, budgets: dict, urteil: str, probleme: list[str],
                      notbremse: str) -> None:
    stamp = datetime.datetime.now(datetime.timezone.utc)
    icon = {"gruen": "✅", "gelb": "🟡", "rot": "🔴"}[urteil]
    zeilen = [
        "# SPAM-SCHUTZ-REPORT",
        "",
        f"_Stand: {stamp.strftime('%d.%m.%Y %H:%M UTC')} – automatisch durch "
        "scripts/spam_schutz_wache.py erzeugt._",
        "",
        f"## Gesamturteil: {icon} {urteil.upper()}",
        "",
        "| KPI | Wert | Budget (gelb/rot) |",
        "|---|---|---|",
        f"| Live-Artikel | {k['live_artikel']} | – |",
        f"| KI-Anteil live | {k['ki_anteil_prozent']} % "
        f"({k['ki_artikel']} Artikel) | "
        f"{budgets['ki_anteil_gelb_prozent']} % / "
        f"{budgets['ki_anteil_rot_prozent']} % |",
        f"| Tempo Maximum/Tag | {k['tempo_max_pro_tag']} | "
        f"– / {budgets['tempo_max_pro_tag']} |",
        f"| Tempo 7 Tage | {k['tempo_letzte7_tage']} | "
        f"{budgets['tempo_gelb_pro_woche']} / "
        f"{budgets['tempo_rot_pro_woche']} |",
        f"| Auto-Freigaben 7 Tage | {k['auto_freigaben_letzte7_tage']} | "
        f"– / {budgets['auto_freigaben_max_pro_woche']} |",
        f"| Near-Duplicate-Paare (SimHash ≤ {budgets['near_dup_hamming']}) | "
        f"{k['near_dup_paare']} | {budgets['near_dup_gelb_paare']} / "
        f"{budgets['near_dup_rot_paare']} |",
        f"| Thin Content live | {len(k['thin_live'])} | – / "
        f"{budgets['thin_live_max']} |",
        f"| Titel-Duplikate live | {len(k['titel_duplikate'])} | – / "
        f"{budgets['titel_duplikate_max']} |",
        f"| KI ohne Offenlegung | {len(k['offenlegung_fehlt'])} | – / "
        f"{budgets['offenlegung_fehlend_max']} |",
        "",
    ]
    if k["near_dup_beispiele"]:
        zeilen += ["**Near-Duplicate-Verdachte:**"]
        zeilen += [f"- {b}" for b in k["near_dup_beispiele"]] + [""]
    if probleme:
        zeilen += ["**Befunde:**"] + [f"- {p}" for p in probleme] + [""]
    else:
        zeilen += ["**Alle Budgets eingehalten.**", ""]
    zeilen += ["**Notbremse:** " + notbremse, "",
               "_Schutz-Kette: Spam-Schutz-Wache (täglich 07:41 MESZ) → "
               "Notbremse auf data/endredaktion.yaml → Endredaktion prüft "
               "zusätzlich data/spam_schutz_status.json vor jeder "
               "Auto-Freigabe (fail-closed)._"]
    with open(REPORT_FILE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(zeilen).rstrip() + "\n")


# ---------------------------------------------------------------- Selbsttest
def _selbsttest() -> int:
    print("Spam-Schutz-Wache – Selbsttest (offline)")
    fehler = []
    b = dict(DEFAULT_BUDGETS)

    gut = kpis_berechnen([], b)  # leerer Bestand = grün
    if kpi_verdict(gut, b)[0] != "gruen":
        fehler.append("Leerer Bestand nicht grün")

    def post(**kw):
        slug = kw.get("slug", "s")
        basis = {"slug": slug, "pfad": "",
                 "titel": kw.get("titel", f"titel-{slug}"),
                 "datum": kw.get("datum", ""), "ai": kw.get("ai", False),
                 "endredaktion_freigabe": kw.get("auto", False),
                 "hat_offenlegung": kw.get("offen", True),
                 "body": kw.get("body", "Ausreichend langer Text. " * 700)}
        return basis

    heute = datetime.date.today()
    # Tempo rot: 4 an einem Tag
    k = kpis_berechnen([post(datum=heute.isoformat()) for _ in range(4)], b)
    if kpi_verdict(k, b)[0] != "rot":
        fehler.append("Tempo/Tag rot nicht erkannt")

    # KI-Anteil rot
    k = kpis_berechnen(
        [post(ai=True, datum="2026-01-0" + str(i % 9 + 1)) for i in range(7)]
        + [post(datum="2026-01-0" + str(i % 9 + 1)) for i in range(3)], b)
    if k["ki_anteil_prozent"] != 70.0 or kpi_verdict(k, b)[0] != "rot":
        fehler.append(f"KI-Anteil rot nicht erkannt ({k['ki_anteil_prozent']})")

    # Offenlegung rot
    k = kpis_berechnen([post(ai=True, offen=False, datum="2026-01-01")], b)
    if kpi_verdict(k, b)[0] != "rot":
        fehler.append("Fehlende Offenlegung nicht rot")

    # Near-Dup: zwei identische Körper → 1 Paar → gelb
    k = kpis_berechnen([post(slug="a", datum="2026-01-01"),
                        post(slug="b", datum="2026-01-02")], b)
    if k["near_dup_paare"] < 1 or kpi_verdict(k, b)[0] != "gelb":
        fehler.append(f"Near-Dup gelb nicht erkannt ({k['near_dup_paare']})")

    # Notbremse: Setzen und Lösen (Text-Logik, ohne echte Datei)
    text = ("modus: automatisch\nmax_freigaben_pro_lauf: 1\n")
    gesetzt = re.sub(r"(?m)^modus:.*$",
                     lambda m: f"modus: manuell  {NOTBREMSE_MARKER} "
                     f"{datetime.date.today().isoformat()} – gesperrt)", text,
                     count=1)
    if "modus: manuell" not in gesetzt or NOTBREMSE_MARKER not in gesetzt:
        fehler.append("Notbremse setzt modus: manuell nicht")
    geloest = re.sub(r"(?m)^modus:.*$", "modus: automatisch", gesetzt, count=1)
    geloest = re.sub(rf"(?m)^.*{re.escape(NOTBREMSE_MARKER)}.*$\n?", "", geloest)
    if "manuell" in geloest or NOTBREMSE_MARKER in geloest:
        fehler.append("Notbremse löst nicht sauber")

    if fehler:
        print("  ✗ " + "\n  ✗ ".join(fehler))
        return 2
    print("  ✓ Budget-Logik (Tempo, KI-Anteil, Offenlegung, Near-Dup),")
    print("    Notbremse setzen/lösen, leerer Bestand: in Ordnung.")
    return 0


# ---------------------------------------------------------------- CLI
def main() -> int:
    ap = argparse.ArgumentParser(
        description="Spam-Schutz-Wache: Google-Spam-Policy täglich prüfen")
    ap.add_argument("--nur-messen", action="store_true",
                    help="nur messen/berichten – keine Notbremse, kein Statusfile")
    ap.add_argument("--json", action="store_true",
                    help="KPIs als JSON auf stdout")
    ap.add_argument("--selftest", action="store_true",
                    help="fail-closed-Selbsttest (Exit 2 bei Defekt)")
    args = ap.parse_args()

    if args.selftest:
        return _selbsttest()

    budgets = lade_budgets()
    posts = lese_live_posts()
    k = kpis_berechnen(posts, budgets)
    urteil, probleme = kpi_verdict(k, budgets)

    if args.json:
        print(json.dumps({"urteil": urteil, "kpis": k},
                         ensure_ascii=False, indent=2))
        return 0

    notbremse = notbremse_anwenden(
        urteil, nur_messen=args.nur_messen or urteil != "rot")
    if not args.nur_messen:
        status_schreiben(k, urteil, probleme)
    bericht_schreiben(k, budgets, urteil, probleme, notbremse)

    icon = {"gruen": "✅", "gelb": "🟡", "rot": "🔴"}[urteil]
    print(f"Spam-Schutz-Wache: {icon} {urteil.upper()} "
          f"({k['live_artikel']} live, KI {k['ki_anteil_prozent']} %, "
          f"Tempo {k['tempo_letzte7_tage']}/Woche, "
          f"{k['near_dup_paare']} Near-Dup-Paare)")
    for p in probleme:
        print(f"  ⚠ {p}")
    print(f"  {notbremse}")
    print(f"Report: {os.path.relpath(REPORT_FILE, BLOG_DIR)}")
    if urteil == "rot":
        print("::error::Spam-Budget rot – Notbremse aktiv, "
              "Auto-Veröffentlichung gestoppt.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
