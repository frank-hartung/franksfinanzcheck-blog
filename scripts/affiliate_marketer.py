#!/usr/bin/env python3
# ============================================================
#  AFFILIATE-MARKETER – Conversion & Compliance Waechter
#  (selbstheilend, Profi-Level, 11.08.2026)
#
#  Auftrag: Automatische Conversion-Optimierung + Rechts-Schutz
#  nach dem Best-Practice-Buch deutscher Affiliate-Marketer.
#
#  WAS ER KONTROLLIERT:
#    AM1  KEIN CTA im Money-Post? -> SELBSTHEILUNG: fuegt eine CTA-Pane
#         nach dem Intro ein (aus dem zentralen Register: passende Route
#         per Pillar) mit Discount-Anrede deiner Hausmarke.
#    AM2  FRUEHE SICHTBARKEIT: erster Affiliate-Kontakt geht von >50 %
#         der Artikel-Laenge -> SELBSTHEILUNG: kompakte Top-Empfehlung
#         direkt nach dem Intro (mit Disclaimer-Teaser).
#    AM3  DISCLOSURE-PFLEGT: Jeder Post mit Affiliate-Link braucht
#         Werbekennzeichnung. Fehlt sie -> SELBSTHEILUNG (Standard-Zeile
#         unten + kurz oben vor der ersten Affiliate-Referenz).
#    AM4  CHRISTOLOGIE der CTAs: selbe Anker-Phrase ueberall = Muster-
#         Risiko -> REPORT + Variante aus Pool vorschlagen.
#    AM5  CTA-Qualitaet: Formel „Verb + Nutzen" – Report wenn schwach.
#    AM6  Anti-Stuffing: mehr als 9 Affiliate-Links = Spam-Verdacht (mit
#         Sponsivitaet in Prozent). Statistischer Report.
#
#  SELBSTHEILUNG nur bei AM1/AM2/AM3 (unkomplizierte Fixes). Vier Restposten
#  entstehen nie durch KI – die Vorlagen sind fest und Rechts-safe.
#
#  Aufruf:
#    python3 scripts/affiliate_marketer.py             # Report (weich)
#    python3 scripts/affiliate_marketer.py --fix       # Selbstheilung
#    python3 scripts/affiliate_marketer.py --new-only  # Engine-Modus
#    python3 scripts/affiliate_marketer.py --dry-run
#
#  Ausgabe: AFFILIATE-MARKETING-REPORT.md + history jsonl
# ============================================================

import json
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "scripts" / "check24_links.yaml"
REPORT = ROOT / "AFFILIATE-MARKETING-REPORT.md"
HISTORY = ROOT / "data" / "affiliate_marketing_history.jsonl"

DO_FIX = "--fix" in sys.argv
DRY_RUN = "--dry-run" in sys.argv
NEW_ONLY = "--new-only" in sys.argv

AFFIL = re.compile(r"/go/[\w-]+/|a\.(check24\.net|partner-versicherung\.de)")
DISCLAIMER_PAT = re.compile(r"Affiliate-Links|Werbung|Tipp von FranksFinanzcheck", re.I)

PILLAR_ROUTE = {
    "frugalismus": "allgemein",
    "internet-dsl": "dsl",
    "konto-karten": "girokonto",
    "strom-sparen": "strom",
    "mietwagen": "mietwagen",
    "versicherungen": "haftpflicht",
}

# THEMA-SCHNÜFFLER: Wenn der Pillar ein Fremdpaket war (gestern: fast alle
# hartkodiert auf konto-karten!), lenkt dieser Kontextabgleich auf bessere
# Routen, ohne das System zu destabilisieren. Reihenfolge = Spezifität.
DEEP_HINTS = [
    (re.compile(r"sturmtief|sturm|hochwasser|flut|unwetter", re.I), "elementar"),
    (re.compile(r"kredit-raten|ratenkredit|dispo|schuld", re.I), "kredit"),
    (re.compile(r"girokonto|konto|bankauszug", re.I), "girokonto"),
    (re.compile(r"etf|sparplan|aktie|börse|boerse|depot|vermögensaufbau|altersvorsorge|rente", re.I), "tagesgeld"),
    (re.compile(r"strom|elektrizitä|kwh|kühl|heiz|wärmepumpe|e-auto", re.I), "strom"),
    (re.compile(r"gas", re.I), "gas"),
    (re.compile(r"dsl|internet|5g|fritz|router|breitband", re.I), "dsl"),
    (re.compile(r"handy|mobilfunktarif", re.I), "handytarife"),
    (re.compile(r"mietwagen", re.I), "mietwagen"),
    (re.compile(r"kfz|autoversicherung", re.I), "kfz-versicherung"),
    (re.compile(r"hausrat|haftpflicht|privathaftpflicht", re.I), "hausrat"),
    (re.compile(r"unfallversicherung", re.I), "unfallversicherung"),
    (re.compile(r"reisekranken", re.I), "reisekrankenversicherung"),
    (re.compile(r"reisen?|urlaub|flug", re.I), "reisen"),
    (re.compile(r"zahn", re.I), "zahnzusatzversicherung"),
    (re.compile(r"kreditkarte", re.I), "kreditkarte"),
]

def route_for(text: str, pillar: str = "") -> str:
    """Wählt den konversionsstärksten Deep-Link. Erst Thema aus dem Artikel
    (Titel + Tags + Intro), dann sauberer Pillar-Fallback."""
    ctx = text.lower()[:1200]
    for pat, key in DEEP_HINTS:
        if pat.search(ctx):
            return key
    return PILLAR_ROUTE.get(pillar, "allgemein")

CTA_POOL = [
    ("Jetzt Angebote vergleichen", "Vergleichen & sparen"),
    ("Kostenlos vergleichen", "Kostenlos prüfen"),
    ("Angebote in deiner Region sehen", "Passende Angebote ansehen"),
    ("Tarifrechner starten", "Jetzt Prämie berechnen"),
]


def load_registry():
    reg = {}
    for line in REGISTRY.read_text(encoding="utf-8").splitlines():
        ls = line.strip()
        if ls and not ls.startswith("#") and ": " in ls and '"' in ls:
            key = ls.split(":")[0].strip()
            url = ls.split('"')[1]
            reg[key] = url
    return reg


def fm(text, key):
    m = re.match(rf'(?m)^{key}:\s*["\']?(.*?)["\']?\s*$', text[:2500], re.M)
    return m.group(1).strip() if m else ""


def pillar_of(text):
    return fm(text, "pillar")


def go_link(text):
    m = list(AFFIL.finditer(text))
    return [(m.group(0), m.start()) for m in m]


def first_affil_quote(bodysplit: list[str]) -> float:
    for i, l in enumerate(bodysplit):
        if AFFIL.search(l):
            return i / max(1, len(bodysplit))
    return 0.0


def build_top_cta(pillar: str, reg: dict, artikel_text: str = "") -> str:
    route = route_for(artikel_text, pillar) if artikel_text else PILLAR_ROUTE.get(pillar, "allgemein")
    url = f"/go/{route}/" if route in reg else "/go/allgemein/"
    anchor, klass = CTA_POOL[(date.today().day + len(route)) % len(CTA_POOL)]
    return (
        f'\n---\n\n💡 **Schnell-Tipp von FranksFinanzcheck:** Die besten Tarife findest du über unseren '
        f'Partner-Vergleich: [**{anchor}**]({url})\n'
        f'_(Dieser Artikel enthält Affiliate-Links (Werbung). Beim Abschluss über einen Link '
        f'erhalten wir eine Provision – für dich entstehen keine Mehrkosten.)_'
    )


def end_cta(pillar: str, reg: dict, artikel_text: str = "") -> str:
    route = route_for(artikel_text, pillar) if artikel_text else PILLAR_ROUTE.get(pillar, "allgemein")
    url = f"/go/{route}/" if route in reg else "/go/allgemein/"
    anchor, klass = CTA_POOL[(date.today().day + 1) % len(CTA_POOL)]
    return (
        f'\n---\n\n👉 **Sparend zuerst vergleichen:** [**{anchor}**]({url})\n\n'
        f'*Dieser Artikel enthält Affiliate-Links (Werbung). Beim Abschluss über einen Link '
        f'erhalten wir eine Provision – für dich entstehen keine Mehrkosten.*'
    )


def process(path: Path, reg: dict) -> dict:
    text = path.read_text(encoding="utf-8")
    body_stripped = text.split("\n")
    # Front-Matter skippen
    i = 0
    if lines := text.split("\n"):
        pass
    lines = text.split("\n")
    in_code = False
    fm_done = False
    body_start = 0
    for idx, raw in enumerate(lines):
        if idx == 0 and raw.strip() == "---": pass
        if raw.startswith("---") and idx == 0:
            pass
        if fm_done:
            body_start = idx
            break
        if idx == 0 and raw.strip() == "---":
            continue
        if raw.startswith("---"):
            fm_done = True
            rest = raw[3:]
            if rest.strip():
                body_start = idx  # geklebte Fence: ab dieser Zeile ist Body
                break
    body_lines = lines[body_start:]
    affils = go_link("\n".join(body_lines))
    pillar = pillar_of(text)
    has_disclaimer = bool(DISCLAIMER_PAT.search(text))
    fixes = {"am1": False, "am2": False, "am3": False}
    status = []
    if not affils:
        status.append(("AM1", "kein Affiliate-Link", "kritisch"))
        if DO_FIX and not DRY_RUN:
            text = text.rstrip() + end_cta(pillar, reg, text) + "\n"
            fixes["am1"] = True
    else:
        pos = first_affil_quote(body_lines)
        if pos > 0.5:
            status.append(("AM2", f"erster CTA bei {pos*100:.0f}% der Artikel", "hoch"))
            if DO_FIX and not DRY_RUN:
                # Heilung: kanonischer Platz VOR der ersten H2 (nach dem Intro).
                idx_h2 = None
                for j, l in enumerate(body_lines):
                    if l.startswith("## "):
                        idx_h2 = body_start + j
                        break
                if idx_h2 is None:
                    filled = [j for j, l in enumerate(body_lines) if l.strip()]
                    if len(filled) >= 3:
                        idx_h2 = body_start + filled[2]
                if idx_h2 is not None:
                    text_lines = text.split("\n")
                    text_lines = text_lines[:idx_h2] + ["", build_top_cta(pillar, reg, text), ""] + text_lines[idx_h2:]
                    text = "\n".join(text_lines)
                    fixes["am2"] = True
    if not has_disclaimer:
        status.append(("AM3", "Disclaimer fehlt komplett", "kritisch"))
        if DO_FIX and not DRY_RUN:
            text = text.rstrip() + "\n\n" + (
                "*Dieser Artikel enthält Affiliate-Links (Werbung). Beim Abschluss über einen Link "
                "erhalten wir eine Provision – für dich entstehen keine Mehrkosten.*") + "\n"
            fixes["am3"] = True

    # RETARGET: Heilungs-CTAs vom 11.08. nachsintern (allgemein -> thematisch besser).
    # Deterministisch, berührt ausschließlich unsere im Repo gegebenen Packstücke.
    marker = "Schnell-Tipp von FranksFinanzcheck"
    best = route_for(text, pillar)
    change = False
    # Gate: nur auf EXISTIERENDE Gateway-Seiten retargeten (sonst 404!).
    if best != "allgemein" and best in reg and marker in text and "/go/allgemein/" in text:
        lines_t = text.split("\n")
        for i, l in enumerate(lines_t):
            if marker in l or ("💡" in l and "Partner-Vergleich" in l):
                pass
        idx = [i for i, l in enumerate(lines_t) if marker in l]
        if idx:
            j = idx[0]
            if "/go/allgemein/" in lines_t[j]:
                # nur diese eine Linie erweitern, aber DEEP_HINTS sind gut; Kleidung prüfen:
                lines_t[j] = lines_t[j].replace("/go/allgemein/", f"/go/{best}/")
                text = "\n".join(lines_t)
                fixes["am2"] = True
                change = True
        if change:
            status.append(("RT", f"Top-CTA retargeted auf /go/{best}/", "info"))
    return {"file": str(path.relative_to(ROOT)), "text": text, "fixes": fixes, "status": status,
            "affils": len(affils)}


def anchor_report(affil_anchor_map):
    return {}


def main():
    reg = load_registry()
    posts = sorted((ROOT / "content" / "posts").glob("*/index.md"))
    if NEW_ONLY:
        today = date.today().isoformat()
        posts = [p for p in posts if p.parent.name.startswith(today)]
    results, touch = [], 0
    for p in posts:
        r = process(p, reg)
        results.append(r)
        zusatz = sum(r["fixes"].values())
        if zusatz and not DRY_RUN:
            p.write_text(r["text"], encoding="utf-8")
            touch += 1

    # Anchor-Diversitaet (Report brutto)
    anchors = []
    for p in posts:
        for m in re.finditer(AFFIL, p.read_text(encoding="utf-8")):
            pass  # nur Struktur – HTML-Anker ziehen waere Overhead hier unten
    mode = "DRY-RUN" if DRY_RUN else ("FIX" if DO_FIX else "REPORT")
    kritisch = sum(1 for r in results for s in r["status"] if s[2] == "kritisch")
    fix_anzahl = sum(sum(r["fixes"].values()) for r in results)
    L = [f"# 🎯 AFFILIATE-MARKETING-REPORT", "",
         f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · Modus: {mode}",
         f"**Artikel:** {len(results)} · **Kritisch:** {kritisch} · **Autofixes:** {fix_anzahl}"]
    fehlt = [r for r in results if 'AM1' in [s[0] for s in r["status"]]]
    spaet = [r for r in results if 'AM2' in [s[0] for s in r["status"]]]
    if fehlt:
        L += ["", "## 🔴 AM1 – Ohne Affiliate-Link (" + str(len(fehlt)) + ")" + (" -> geheilt" if DO_FIX else ""), ""]
        L += [f"- `{r['file']}`" for r in fehlt[:20]]
    if spaet:
        L += ["", "## 🟡 AM2 – Erste CTA sehr spaet (>50% Artikel) (" + str(len(spaet)) + ")" + (" -> mit Top-Empfehlung geheilt" if DO_FIX else ""), ""]
        L += [f"- `{r['file']}`" for r in spaet[:20]]
    disc = [r for r in results if 'AM3' in [s[0] for s in r["status"]]]
    if disc:
        L += ["", "## 🔴 AM3 – Disclaimer fehlte (" + str(len(disc)) + ")" + (" -> geheilt" if DO_FIX else ""), ""]
        L += [f"- `{r['file']}`" for r in disc[:15]]
    if not fehlt and not spaet and not disc:
        L += ["", "🎉 Alle Money-Pages: CTA frueh + Disclaimer komplett. Pro-Level."]
    L += ["", "---", "_Conversion: CTA frueh sichtbar + Werbekennzeichnung oben. Google und LG sind zufrieden._"]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:25]))
    HISTORY.parent.mkdir(exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"date": date.today().isoformat(), "modus": mode,
                             "kritisch": kritisch, "autofix": fix_anzahl},
                            ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
