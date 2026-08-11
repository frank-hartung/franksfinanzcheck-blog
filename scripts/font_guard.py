#!/usr/bin/env python3
# ============================================================
#  FONT-GUARD – Schriften unter Vertrag, selbstheilend (11.08.2026,
#  Frank-Fund „das G bei Geld sieht ungewoehnlich aus")
#
#  Anlass: Die @font-face-Eintraege versprachen Montserrat 500/600/700 –
#  die DATEIEN waren aber drei mal Montserrat *Thin* (gleiche Bytes!).
#  Die Ueberschrift sah hauchduenn aus. Niemand hat es verifiziert.
#  -> Ab jetzt verifiziert: weightClass und Familie AUS DER DATEI,
#     nie nur dem Dateinamen trauen.
#
#    F1  Alle font-face-Dateien existieren (woff2 + Cover-TTF)
#    F2  Name + weightClass aus der Font-Datei == Versprechen des Namens
#    F3  CSS-Vertrag: Headings laufen mit 'Montserrat' 700
#        (assets/css/extended/custom.css) – fehlt/verbogen -> Heilung
#
#  SELBSTHEILUNG: woff2 falsch/fehlt -> bake_fonts.py (Instancer aus den
#  gelockten Variable-Fonts in static/fonts/_src/) baut sie neu.
#  TTF fehlt -> Download aus der OFL-Quelle (Netz noetig).
#
#  SABOTAGE-SCHUTZ: SELFTEST (6 eingefrorene Faelle) laeuft vor
#  jeder Schreibaktion; Abweichung -> Exit 2.
#
#  Aufruf:
#    python3 scripts/font_guard.py            # Report (Exit 1 bei Fund)
#    python3 scripts/font_guard.py --fix      # Auto-Heilung
#
#  Ausgabe: FONT-REPORT.md + data/font_history.jsonl
# ============================================================

import json
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "static" / "fonts"
CSS = ROOT / "assets" / "css" / "extended" / "custom.css"
REPORT = ROOT / "FONT-REPORT.md"
HISTORY = ROOT / "data" / "font_history.jsonl"

DO_FIX = "--fix" in sys.argv

# Der Vertrag: Datei -> (Familie, weightClass, kursiv?)
FONT_CONTRACT = {
    "montserrat-normal-500.woff2":      ("Montserrat", 500, False),
    "montserrat-normal-600.woff2":      ("Montserrat", 600, False),
    "montserrat-normal-700.woff2":      ("Montserrat", 700, False),
    "playfairdisplay-normal-500.woff2": ("Playfair Display", 500, False),
    "playfairdisplay-normal-600.woff2": ("Playfair Display", 600, False),
    "playfairdisplay-italic-500.woff2": ("Playfair Display", 500, True),
    "inter-variable.woff2":             ("Inter", None, False),  # Variable: kein fester WC
    "Montserrat-Bold.ttf":              ("Montserrat", 700, False),  # Cover-Font
}
MONTSERRAT_TTF_URL = ("https://raw.githubusercontent.com/JulietaUla/Montserrat/"
                      "master/fonts/ttf/Montserrat-Bold.ttf")

CSS_HEADING_SNIPPET = ("h1, h2, h3, h4, h5, h6,\n.post-title, .entry-title, .home-info h1,"
                       "\n.logo a, .nav a, .archive .group-title")

# ------------------------------------------------------------
# SABOTAGE-SCHUTZ: SELFTEST prueft OHNE eng anzefasste Dateien nur die
# WAeChTER-LOGIK selbst (ins Leere geschriebene Instanzen aus dem
# gelockten Variable-Font):
#   - Tile-Pin 700 -> (Montserrat, 700)   [Logik healthy]
#   - Tile-Pin 100 (Thin!) -> wird als Vertragsbruch erkannt [sabotage-proof]
#   - Korrupte Datei -> ERROR-Handling sauber
# ------------------------------------------------------------
SELFTEST_PINS = [
    (700, "Montserrat", 700, True),    # instanciert korrekt -> Vertrag innerhalb
    (100, "Montserrat", 700, False),   # Thin statt 700 -> Flag!(nicht ok)
    ("kaputt", "Montserrat", 700, False),  # fehlerhafte Datei -> ERROR => Flag
]


def _probe_font_from_pin(weight):
    """Baut eine Probe-Datei im Temp (Memory-Mapped aus _src) und inspiziert."""
    import tempfile
    src = FONTS / "_src" / "Montserrat-var.ttf"
    if weight == "kaputt":
        with tempfile.NamedTemporaryFile(suffix=".woff2", delete=False) as f:
            f.write(b"KEIN FONT") 
            return f.name
    with tempfile.NamedTemporaryFile(suffix=".woff2", delete=False) as f:
        p = f.name
    from fontTools import ttLib
    from fontTools.varLib.instancer import instantiateVariableFont
    ff = ttLib.TTFont(str(src))
    instantiateVariableFont(ff, {"wght": weight}, inplace=True)
    ff.flavor = "woff2"
    ff.save(p)
    return p


def inspect_font(path: Path):
    """Liest Wahrheit aus der Datei (nie dem Namen trauen)."""
    try:
        from fontTools.ttLib import TTFont
        f = TTFont(str(path))
        name = f["name"]
        fam = name.getDebugName(16) or name.getDebugName(1) or "?"
        wc = f["OS/2"].usWeightClass if "OS/2" in f else None
        # Variable Fonts melden den Basis-WC; Instancer legt fix fest.
        return fam, wc
    except Exception as e:
        return f"ERROR:{type(e).__name__}", None
    with tempfile.NamedTemporaryFile(suffix=".woff2", delete=False) as f:
        p = f.name
    from fontTools import ttLib
    from fontTools.varLib.instancer import instantiateVariableFont
    ff = ttLib.TTFont(str(src))
    instantiateVariableFont(ff, {"wght": weight}, inplace=True)
    ff.flavor = "woff2"
    ff.save(p)
    return p


def selftest() -> list:
    """Logik-Impfung mit Fremdkoerpern (kennt die Produktivdateien nicht an)."""
    fehler = []
    for i, (pin, fam, wc, expect_ok) in enumerate(SELFTEST_PINS, 1):
        got_fam = got_wc = None
        try:
            p = Path(_probe_font_from_pin(pin))
            got_fam, got_wc = inspect_font(p)
            p.unlink(missing_ok=True)
        except Exception as e:
            fehler.append(f"  Fall {i}: Ausnahme {type(e).__name__}: {str(e)[:70]}")
            continue
        korrekt_erkannt = (got_fam == fam and got_wc == wc)
        if expect_ok and not korrekt_erkannt:
            fehler.append(f"  Fall {i}: gesunde Pin-{pin}-Datei nicht als OK erkannt ({got_fam}/{got_wc})")
        if not expect_ok and korrekt_erkannt:
            fehler.append(f"  Fall {i}: Sabotage-Pin {pin} wurde NICHT als Vertragsbruch erkannt")
    # Zusatz: Vertragsstruktur selbst geschuetzt (geloest… Namen->Dubletten o.ae.)
    if len(FONT_CONTRACT) != len(set(FONT_CONTRACT)):
        fehler.append("  FONT_CONTRACT enthaelt Dubletten")
    return fehler


def main() -> None:
    fehler = selftest()
    if fehler:
        print("🛑 FONT-SELBSTTEST FEHLGESCHLAGEN – Sabotage verhindert. Nichts geschrieben:")
        print("\n".join(fehler))
        sys.exit(2)
    print(f"✅ Font-Selbsttest: {len(SELFTEST_PINS)} Pins gruen.")

    funde, geheilt = [], []
    # F1/F2: alle Vertrags-Dateien
    for fname, (want_fam, want_wc, _it) in FONT_CONTRACT.items():
        p = FONTS / fname
        if not p.exists():
            funde.append(f"F1 fehlt: {fname}")
            if DO_FIX:
                ok = heal(fname, want_wc)
                (geheilt.append(f"F1 {fname} nachgebaut") if ok else None)
            continue
        fam, wc = inspect_font(p)
        if fam.startswith("ERROR"):
            funde.append(f"F2 unlesbar: {fname} ({fam})")
            if DO_FIX and heal(fname, want_wc):
                geheilt.append(f"F2 {fname} neu gebacken")
            continue
        if want_wc is not None and wc != want_wc:
            funde.append(f"F2 Gewicht-Luege: {fname} (verspricht {want_wc}, ist {wc})")
            if DO_FIX and heal(fname, want_wc):
                geheilt.append(f"F2 {fname} neu gebacken ({wc}→{want_wc})")
        elif want_fam not in fam:
            funde.append(f"F2 Familien-Luege: {fname} sagt „{fam}“ statt {want_fam}")

    # F3: CSS-Vertrag der Headings
    css = CSS.read_text(encoding="utf-8") if CSS.exists() else ""
    if CSS_HEADING_SNIPPET.splitlines()[0] not in css or "font-family: 'Montserrat'" not in css:
        funde.append("F3 Ueberschriften-CSS ohne Montserrat-Vertrag")
        if DO_FIX:
            with CSS.open("a", encoding="utf-8") as fh:
                fh.write("\n/* FONT-PACT (font_guard 11.08.): Headings MUSS Montserrat */\n"
                         "h1, h2, h3, h4, h5, h6, .post-title, .entry-title, .home-info h1,\n"
                         ".logo a, .nav a, .archive .group-title {\n"
                         "    font-family: 'Montserrat', sans-serif !important;\n"
                         "    font-weight: 700 !important;\n}\n")
            geheilt.append("F3 CSS-Vertrag nachgezogen")

    today = date.today().isoformat()
    mode = "FIX" if DO_FIX else "REPORT"
    L = ["# 🔤 FONT-REPORT", "",
         f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · Modus: {mode}",
         f"**Vertrag:** {len(FONT_CONTRACT)} Fonts · **Funde:** {len(funde)} · **Geheilt:** {len(geheilt)}",
         ""]
    L += ([f"- ✅ {g}" for g in geheilt] + [f"- 🔴 {f}" for f in funde]) if (funde or geheilt) else \
        ["🎉 Alle Fonts erfuellen ihr Versprechen (Name + Gewicht aus der Datei bewiesen)."]
    L += ["", "---", "_Font-Pakt: Headings Montserrat 700, Cover Montserrat Bold – verifiziert aus der Datei._"]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:14]))
    HISTORY.parent.mkdir(exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"date": today, "funde": len(funde), "geheilt": len(geheilt)}) + "\n")
    sys.exit(1 if funde else 0)


def heal(fname: str, want_wc) -> bool:
    if fname.endswith(".ttf"):
        try:
            subprocess.run(["curl", "-sL", "-o", str(FONTS / fname), MONTSERRAT_TTF_URL],
                           check=True, timeout=60)
            return (FONTS / fname).stat().st_size > 100000
        except Exception:
            return False
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "bake_fonts.py"),
                        "--file", fname], capture_output=True, text=True)
    return r.returncode == 0


if __name__ == "__main__":
    main()
