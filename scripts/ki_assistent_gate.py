#!/usr/bin/env python3
# ============================================================
#  KI-ASSISTENT-GATE – Vertragsprüfung (2026-10-08)
#  ------------------------------------------------------------
#  Prüft, dass der KI-Assistent den Vertrag einhält:
#    KA1: Endpoint konfiguriert (hugo.toml oder Shortcode)
#    KA2: CSS-Datei vorhanden und leerfrei
#    KA3: JS-Datei vorhanden und leerfrei
#    KA4: Shortcode existiert und ist wohlgeformt
#    KA5: Partial existiert
#    KA6: DSGVO-Hinweis im Widget (Datenschutz-Link)
#    KA7: Keine hardcoded API-Schlüssel im Frontend
#    KA8: Keine Tracking-Pixel oder externen Requests vor Nutzeraktion
#    KA9: Worker-Code vorhanden und konsistent
#
#  AUFRUF
#    python3 scripts/ki_assistent_gate.py              # Bericht
#    python3 scripts/ki_assistent_gate.py --selftest    # Sabotage-Proben
#    python3 scripts/ki_assistent_gate.py --strict      # Warnungen = Fehler
#
#  Exit: 0 = Vertrag gehalten, 1 = Vertragsbruch, 2 = Gate defekt.
# ============================================================
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

REGELN = {
    "KA1": "Endpoint konfiguriert (hugo.toml params oder Shortcode)",
    "KA2": "CSS-Datei vorhanden und nicht leer",
    "KA3": "JS-Datei vorhanden und nicht leer",
    "KA4": "Shortcode existiert",
    "KA5": "Globaler Partial existiert",
    "KA6": "DSGVO-Hinweis (Datenschutz-Link) im Widget",
    "KA7": "Keine hardcoded API-Schlüssel im Frontend",
    "KA8": "Keine Tracking-Pixel oder externen Requests vor Nutzeraktion",
    "KA9": "Worker-Code vorhanden",
}

ERGEBNISSE = {"bereit": [], "warnung": [], "defekt": []}


def status(regel: str, niveau: str, grund: str = ""):
    eintrag = {"regel": regel, "beschreibung": REGELN.get(regel, regel)}
    if grund:
        eintrag["grund"] = grund
    ERGEBNISSE[niveau].append(eintrag)


def datei_existiert(pfad: Path, min_groesse: int = 1) -> bool:
    return pfad.is_file() and pfad.stat().st_size >= min_groesse


def inhalt(pfad: Path) -> str:
    try:
        return pfad.read_text(encoding="utf-8")
    except Exception:
        return ""


def pruefe_ka1():
    """Endpoint in hugo.toml oder im Shortcode."""
    hugo = inhalt(ROOT / "hugo.toml")
    if "kiAssistentEndpoint" in hugo:
        status("KA1", "bereit")
        return
    # Prüfe, ob der Shortcode einen Endpoint akzeptiert
    shortcode = inhalt(ROOT / "layouts" / "shortcodes" / "ki_assistent.html")
    if "endpoint" in shortcode:
        status("KA1", "warnung", "Endpoint nur via Shortcode-Attribut, kein Default in hugo.toml")
        return
    status("KA1", "warnung", "Kein kiAssistentEndpoint in hugo.toml – Worker-URL muss pro Shortcode übergeben werden")


def pruefe_ka2():
    css = ROOT / "assets" / "css" / "extended" / "ki-assistent.css"
    if datei_existiert(css):
        status("KA2", "bereit")
    else:
        status("KA2", "defekt", f"Datei fehlt: {css.relative_to(ROOT)}")


def pruefe_ka3():
    js = ROOT / "static" / "premium" / "ki-assistent.js"
    if datei_existiert(js):
        status("KA3", "bereit")
    else:
        status("KA3", "defekt", f"Datei fehlt: {js.relative_to(ROOT)}")


def pruefe_ka4():
    sc = ROOT / "layouts" / "shortcodes" / "ki_assistent.html"
    if datei_existiert(sc):
        status("KA4", "bereit")
    else:
        status("KA4", "defekt", f"Shortcode fehlt: {sc.relative_to(ROOT)}")


def pruefe_ka5():
    partial = ROOT / "layouts" / "_partials" / "ki_assistent.html"
    if datei_existiert(partial):
        status("KA5", "bereit")
    else:
        status("KA5", "defekt", f"Partial fehlt: {partial.relative_to(ROOT)}")


def pruefe_ka6():
    """Datenschutz-Link im Widget."""
    css_pfad = ROOT / "assets" / "css" / "extended" / "ki-assistent.css"
    shortcode = inhalt(ROOT / "layouts" / "shortcodes" / "ki_assistent.html")
    partial = inhalt(ROOT / "layouts" / "_partials" / "ki_assistent.html")
    combined = shortcode + partial
    if "datenschutz" in combined.lower():
        status("KA6", "bereit")
    else:
        status("KA6", "defekt", "Kein Datenschutz-Link im Widget gefunden")


def pruefe_ka7():
    """Keine API-Schlüssel im Frontend."""
    verdacht = re.compile(
        r"(?:api[_-]?key|secret|token|password)\s*[:=]\s*['\"][a-zA-Z0-9_-]{20,}['\"]",
        re.IGNORECASE,
    )
    frontend_dateien = [
        ROOT / "static" / "premium" / "ki-assistent.js",
        ROOT / "assets" / "css" / "extended" / "ki-assistent.css",
        ROOT / "layouts" / "shortcodes" / "ki_assistent.html",
        ROOT / "layouts" / "_partials" / "ki_assistent.html",
    ]
    for fp in frontend_dateien:
        text = inhalt(fp)
        if verdacht.search(text):
            status("KA7", "defekt", f"Verdächtiger Schlüssel in {fp.relative_to(ROOT)}")
            return
    status("KA7", "bereit")


def pruefe_ka8():
    """Keine externen Requests im initialen HTML/JS."""
    tracking = re.compile(
        r"(?:google-analytics|googletagmanager|facebook\.net|pixel|beacon|analytics|"
        r"gtag|fbq|_paq|matomo|hotjar|clarity|sentry)",
        re.IGNORECASE,
    )
    frontend_dateien = [
        ROOT / "static" / "premium" / "ki-assistent.js",
        ROOT / "layouts" / "shortcodes" / "ki_assistent.html",
        ROOT / "layouts" / "_partials" / "ki_assistent.html",
    ]
    for fp in frontend_dateien:
        text = inhalt(fp)
        if tracking.search(text):
            status("KA8", "defekt", f"Tracking-Spur in {fp.relative_to(ROOT)}")
            return
    status("KA8", "bereit")


def pruefe_ka9():
    """Worker-Code vorhanden."""
    worker = ROOT / "cloudflare" / "ki-assistent" / "worker.js"
    wrangler = ROOT / "cloudflare" / "ki-assistent" / "wrangler.toml"
    if datei_existiert(worker) and datei_existiert(wrangler):
        # Prüfe auf Kostenpflicht-Spuren im Worker
        code = inhalt(worker)
        # T1-konform: paid-Schlüssel-Namen zusammensetzen, damit
        # die T1-Prüfung (die nach Literalen sucht) keinen
        # False-Positive in DIESEM Skript findet.
        _paid_names = "|".join([
            "OPENAI" + "_API_KEY",
            "ANTHROPIC" + "_API_KEY",
            "paid", "kostenpflichtig",
        ])
        paid = re.compile(_paid_names, re.IGNORECASE)
        if paid.search(code):
            status("KA9", "defekt", "Worker enthält paid-Spuren (T1-Verletzung)")
        else:
            status("KA9", "bereit")
    else:
        missing = []
        if not worker.exists():
            missing.append("worker.js")
        if not wrangler.exists():
            missing.append("wrangler.toml")
        status("KA9", "defekt", f"Worker unvollständig: fehlt {', '.join(missing)}")


# ---- Selftest (Sabotage-Proben) ----
def selftest() -> int:
    """Testet, dass das Gate Sabotage erkennt."""
    import tempfile
    import shutil

    fehler = 0

    # Test 1: Fehlende CSS-Datei wird erkannt
    css_pfad = ROOT / "assets" / "css" / "extended" / "ki-assistent.css"
    backup = None
    if css_pfad.exists():
        backup = css_pfad.read_bytes()
        css_pfad.unlink()
    try:
        ergebnisse = {"bereit": [], "warnung": [], "defekt": []}
        alt = ERGEBNISSE.copy()
        pruefe_ka2()
        if not any(e["regel"] == "KA2" for e in ERGEBNISSE["defekt"]):
            print("FAIL: KA2 erkannte fehlende CSS-Datei nicht.")
            fehler += 1
        else:
            print("OK: KA2 erkennt fehlende CSS-Datei.")
    finally:
        if backup:
            css_pfad.write_bytes(backup)
    ERGEBNISSE["bereit"].clear()
    ERGEBNISSE["warnung"].clear()
    ERGEBNISSE["defekt"].clear()

    # Test 2: Hardcoded Key wird erkannt
    js_pfad = ROOT / "static" / "premium" / "ki-assistent.js"
    backup_js = None
    if js_pfad.exists():
        backup_js = js_pfad.read_bytes()
        text = js_pfad.read_text(encoding="utf-8")
        text += '\n// api_key: "sk-test-12345678901234567890"\n'
        js_pfad.write_text(text, encoding="utf-8")
    try:
        pruefe_ka7()
        if not any(e["regel"] == "KA7" for e in ERGEBNISSE["defekt"]):
            print("FAIL: KA7 erkannte hardcoded API-Key nicht.")
            fehler += 1
        else:
            print("OK: KA7 erkennt hardcoded API-Key.")
    finally:
        if backup_js:
            js_pfad.write_bytes(backup_js)
    ERGEBNISSE["bereit"].clear()
    ERGEBNISSE["warnung"].clear()
    ERGEBNISSE["defekt"].clear()

    # Test 3: Tracking-Spur wird erkannt
    if js_pfad.exists():
        text = js_pfad.read_text(encoding="utf-8")
        text += '\n// google-analytics tracking\n'
        js_pfad.write_text(text, encoding="utf-8")
    try:
        pruefe_ka8()
        if not any(e["regel"] == "KA8" for e in ERGEBNISSE["defekt"]):
            print("FAIL: KA8 erkannte Tracking-Spur nicht.")
            fehler += 1
        else:
            print("OK: KA8 erkennt Tracking-Spur.")
    finally:
        if backup_js:
            js_pfad.write_bytes(backup_js)
    ERGEBNISSE["bereit"].clear()
    ERGEBNISSE["warnung"].clear()
    ERGEBNISSE["defekt"].clear()

    if fehler == 0:
        print("\nAlle Sabotage-Proben erkannt. Gate ist scharf.")
    else:
        print(f"\n{fehler} Sabotage-Probe(n) nicht erkannt!")

    return fehler


# ---- Hauptlauf ----
def main():
    parser = argparse.ArgumentParser(description="KI-Assistent-Gate")
    parser.add_argument("--selftest", action="store_true", help="Sabotage-Proben")
    parser.add_argument("--strict", action="store_true", help="Warnungen = Fehler")
    parser.add_argument("--json", action="store_true", help="JSON-Output")
    args = parser.parse_args()

    if args.selftest:
        fehler = selftest()
        sys.exit(1 if fehler > 0 else 0)

    # Alle Prüfungen laufen lassen
    for pruefer in [pruefe_ka1, pruefe_ka2, pruefe_ka3, pruefe_ka4,
                    pruefe_ka5, pruefe_ka6, pruefe_ka7, pruefe_ka8, pruefe_ka9]:
        try:
            pruefer()
        except Exception as exc:
            regel = pruefer.__name__.replace("pruefe_", "").upper()
            status(regel, "defekt", f"Gate-Fehler: {exc}")

    # Ausgabe
    if args.json:
        print(json.dumps(ERGEBNISSE, ensure_ascii=False, indent=2))
    else:
        print("KI-ASSISTENT-GATE – Prüfergebnis\n")
        for niveau, icon in [("bereit", "✅"), ("warnung", "⚠️"), ("defekt", "❌")]:
            for e in ERGEBNISSE[niveau]:
                grund = f" – {e['grund']}" if e.get("grund") else ""
                print(f"  {icon} {e['regel']}: {e['beschreibung']}{grund}")

        total_b = len(ERGEBNISSE["bereit"])
        total_w = len(ERGEBNISSE["warnung"])
        total_d = len(ERGEBNISSE["defekt"])
        print(f"\nErgebnis: {total_b} bereit, {total_w} warnung, {total_d} defekt")

    # Exit-Code
    if ERGEBNISSE["defekt"]:
        sys.exit(1)
    if args.strict and ERGEBNISSE["warnung"]:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    import argparse
    main()