#!/usr/bin/env python3
# ============================================================
#  FONT-GUARD – Schriften unter Vertrag, selbstheilend
#  (Inter-Edition, 11.08.2026 spaet, Frank-Wahl)
#
#  Anlass: Drei woff2-Dateien hieBen Montserrat-500/600/700 –
#  innen waren alle dieselbe Montserrat-THIN-Datei. Regel:
#  nie dem Dateinamen trauen; Familie + Gewicht lesen wir AUS
#  dem Font-Koerper.
#
#    F1  Alle Vertrags-Dateien existieren
#    F2  Name + weightClass aus der Datei == Versprechen
#    F3  CSS-Vertrag: Headings laufen mit 'Inter' 700
#
#  SELBSTHEILUNG: fehlerhafte Datei -> bake_fonts.py baut sie aus
#  den gelockten Variable-Fonts in static/fonts/_src/ neu.
#
#  SABOTAGE-SCHUTZ: Selbsttest (Proben aus Inter-var in temp),
#  Abweichung -> Exit 2, nichts geschrieben.
#
#  Aufruf:
#    python3 scripts/font_guard.py            # Report (Exit 1 bei Fund)
#    python3 scripts/font_guard.py --fix      # Auto-Heilung
# ============================================================

import json
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "static" / "fonts"
SRC_DIR = FONTS / "_src"
CSS = ROOT / "assets" / "css" / "extended" / "custom.css"
REPORT = ROOT / "FONT-REPORT.md"
HISTORY = ROOT / "data" / "font_history.jsonl"

DO_FIX = "--fix" in sys.argv

# Der Vertrag: Datei -> (Familie, weightClass, kursiv?)
FONT_CONTRACT = {
    "inter-variable.woff2":             ("Inter", None, False),  # Variable: beliebiges Gewicht erlaubt
    "Inter-Bold.ttf":                   ("Inter", 700, False),   # Cover-Font (gebacken)
    "playfairdisplay-normal-500.woff2": ("Playfair Display", 500, False),
    "playfairdisplay-normal-600.woff2": ("Playfair Display", 600, False),
    "playfairdisplay-italic-500.woff2": ("Playfair Display", 500, True),
}

CSS_HEADING_PROOF = "font-family: 'Inter'"  # headings muessen Inter bleiben
INTER_CSS_BLOCK = ("\n/* FONT-PACT (font_guard, Frank 11.08.): Headings = Inter Bold */\n"
                   "h1, h2, h3, h4, h5, h6, .post-title, .entry-title, .home-info h1,\n"
                   ".logo a, .nav a, .archive .group-title {\n"
                   "    font-family: 'Inter', -apple-system, sans-serif;\n"
                   "    font-weight: 700;\n"
                   "    letter-spacing: -0.01em;\n}\n")


def inspect_font(path: Path):
    """Wahrheit aus dem Datei-Koerper (nie dem Namen trauen)."""
    try:
        from fontTools.ttLib import TTFont
        f = TTFont(str(path))
        name = f["name"]
        fam = name.getDebugName(16) or name.getDebugName(1) or "?"
        wc = f["OS/2"].usWeightClass if "OS/2" in f else None
        return fam, wc
    except Exception as e:
        return f"ERROR:{type(e).__name__}", None


# ------------------------------------------------------------
# SABOTAGE-SCHUTZ: Selbsttest NUR gegen die Waechter-Logik
# (im Temp gebackene Proben aus dem gelockten Variable-Font),
# Produktivdateien bleiben dabei unberuehrt.
# ------------------------------------------------------------
SELFTEST_PINS = [
    # (Quelle in _src, Pin-Gewicht, erwartete Familie, erwarteter WC, soll ok sein?)
    ("Inter-var.ttf", 700, "Inter", 700, True),
    ("Inter-var.ttf", 100, "Inter", 700, False),   # Thin als Bold: MUSS fliegen
    (None, "kaputt", "Inter", 700, False),          # korrupte Datei: muss als Fehler fliegen
]


def _probe(weight, src_name):
    import tempfile
    if weight == "kaputt" or src_name is None:
        with tempfile.NamedTemporaryFile(suffix=".woff2", delete=False) as f:
            f.write(b"KEIN FONT")
            return f.name
    from fontTools import ttLib
    from fontTools.varLib.instancer import instantiateVariableFont
    ff = ttLib.TTFont(str(SRC_DIR / src_name))
    instantiateVariableFont(ff, {"wght": weight}, inplace=True)
    ff.flavor = "woff2"
    with tempfile.NamedTemporaryFile(suffix=".woff2", delete=False) as f:
        p = f.name
    ff.save(p)
    return p


def selftest() -> list:
    fehler = []
    for i, (src_name, pin, fam, wc, expect_ok) in enumerate(SELFTEST_PINS, 1):
        try:
            p = Path(_probe(pin, src_name))
            got_fam, got_wc = inspect_font(p)
            p.unlink(missing_ok=True)
        except Exception as e:
            fehler.append(f"  Fall {i}: Ausnahme {type(e).__name__}: {str(e)[:70]}")
            continue
        korrekt = (got_fam == fam and got_wc == wc)
        if expect_ok != korrekt:
            fehler.append(f"  Fall {i}: pin={pin} -> {got_fam}/{got_wc} (erwartet „ok={expect_ok}“)")
    if len(FONT_CONTRACT) != len(set(FONT_CONTRACT)):
        fehler.append("  FONT_CONTRACT enthaelt Dubletten")
    return fehler


def heal(fname: str) -> bool:
    """Neubacken aus gelockten _src-Variable-Fonts via bake_fonts.py."""
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "bake_fonts.py"),
                        "--file", fname],
                       capture_output=True, text=True, timeout=240)
    return r.returncode == 0


def main() -> None:
    fehler = selftest()
    if fehler:
        print("🛑 FONT-SELBSTTEST FEHLGESCHLAGEN – Sabotage verhindert. Nichts geschrieben:")
        print("\n".join(fehler))
        sys.exit(2)
    print(f"✅ Font-Selbsttest: {len(SELFTEST_PINS)} Pins gruen.")

    funde, geheilt = [], []
    for fname, (want_fam, want_wc, _it) in FONT_CONTRACT.items():
        p = FONTS / fname
        if not p.exists():
            funde.append(f"F1 fehlt: {fname}")
            if DO_FIX and heal(fname):
                geheilt.append(f"F1 {fname} neu gebacken")
            continue
        fam, wc = inspect_font(p)
        if fam.startswith("ERROR"):
            funde.append(f"F2 unlesbar: {fname} ({fam})")
            if DO_FIX and heal(fname):
                geheilt.append(f"F2 {fname} neu gebacken")
            continue
        if want_wc is not None and wc != want_wc:
            funde.append(f"F2 Gewichts-Luege: {fname} verspricht {want_wc}, ist {wc}")
            if DO_FIX and heal(fname):
                geheilt.append(f"F2 {fname} neu gebacken ({wc}->{want_wc})")
        elif want_fam not in fam:
            funde.append(f"F2 Familien-Luege: {fname} ist „{fam}“ statt {want_fam}")

    css = CSS.read_text(encoding="utf-8") if CSS.exists() else ""
    if CSS_HEADING_PROOF not in css:
        funde.append("F3 Ueberschriften ohne Inter-Vertrag (custom.css)")
        if DO_FIX:
            with CSS.open("a", encoding="utf-8") as fh:
                fh.write(INTER_CSS_BLOCK)
            geheilt.append("F3 Inter-Heading-Block nachgesetzt")

    today = date.today().isoformat()
    mode = "FIX" if DO_FIX else "REPORT"
    L = ["# 🔤 FONT-REPORT", "",
         f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · Modus: {mode}",
         f"**Vertrag:** {len(FONT_CONTRACT)} Fonts · **Funde:** {len(funde)} · **Geheilt:** {len(geheilt)}",
         ""]
    if funde or geheilt:
        L += [f"- ✅ {g}" for g in geheilt] + [f"- 🔴 {f}" for f in funde]
    else:
        L += ["🎉 Alle Fonts erfuellen ihr Versprechen (Name + Gewicht aus dem Datei-Koerper bewiesen)."]
    L += ["", "---", "_Font-Pakt: Headings Inter Bold 700, Cover Inter Bold – aus der Datei bewiesen._"]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:14]))
    HISTORY.parent.mkdir(exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"date": today, "funde": len(funde), "geheilt": len(geheilt)}) + "\n")
    sys.exit(1 if funde else 0)


if __name__ == "__main__":
    main()
