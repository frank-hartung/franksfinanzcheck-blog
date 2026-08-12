#!/usr/bin/env python3
# ============================================================
#  BRAND-GUARD – Marken-Konfiguration unter Verschluss (mit Selbstheilung)
#
#  AUFTRAG (10.08.2026): Willkommenstext und Emojis dürfen sich NIEMALS
#  ungewollt ändern – egal wer/schwas (Content-Bot, KI-Polish, menschlicher
#  Klick-Fehler). brand_guard prüft die geschützten Werte in hugo.toml
#  und STELLT sie bei Abweichung automatisch WIEDER HER.
#
#  SINGLE SOURCE OF TRUTH: data/brand_lock.yaml
#    - Dort steht der „kanonische" Ist-Zustand pro geschütztem Eintrag.
#    - Absichtliche Änderung gewünscht? → hugo.toml ändern und einmal
#      `python3 scripts/brand_guard.py --set-current` ausführen:
#      der aktuelle Zustand wird zum NEUEN Lock (das dokumentieren wir
#      im BRAND-REPORT.md mit Datum).
#
#  SELBSTHEILUNG:
#    - Jeder Engine-Lauf (Phase 2) und das Wochen-Audit rufen --fix auf.
#    - Abweichung -> Originalwert in hugo.toml zurückschreiben (vor dem
#      Commit-Schritt der Kette) + Fund im BRAND-REPORT.md.
#    - hugo.toml KOMPLETT fehlerhaft/gelöscht? -> hartes Stop-Signal:
#      Exit 1 mit klarer Meldung (Fehler-Alerting greift dann zu).
#
#  Aufruf:
#    python3 scripts/brand_guard.py --fix          # prüfen & heilen
#    python3 scripts/brand_guard.py                # nur prüfen/report
#    python3 scripts/brand_guard.py --set-current  # jetziger Stand = neuer Lock
# ============================================================

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HUGO_TOML = ROOT / "hugo.toml"
LOCK_FILE = ROOT / "data" / "brand_lock.yaml"
REPORT = ROOT / "BRAND-REPORT.md"

DO_FIX = "--fix" in sys.argv
SET_CURRENT = "--set-current" in sys.argv

# Geschützte Schlüssel (Regex auf „Key = \"…\""-Zeilen in hugo.toml):
#   name = Anzeigename · pattern = Option zur Adressierung
PROTECTED = [
    ("homeInfoParams.Title",   re.compile(r'^(    Title\s*=\s*)"(.*)"\s*$', re.M), "Willkommens-Titel"),
    ("homeInfoParams.Content", re.compile(r'^(    Content\s*=\s*)"(.*)"\s*$', re.M), "Startseiten-Tagline"),
    ("params.description",     re.compile(r'^(  description\s*=\s*)"(.*)"\s*$', re.M), "Meta-Description"),
    ("params.disclaimer",      re.compile(r'^(  disclaimer\s*=\s*)"(.*)"\s*$', re.M), "Affiliate-Disclaimer"),
]

# ------------------------------------------------------------ Marken-ASSETS (12.08. Runde 2)
# Frank-Auftrag: Logo (Header/Favicon) + Covers unter DAUER-Sabotage-Schutz.
# Kanonisch = was scripts/bake_brand.py deterministisch backt. Der Hash-Lock
# (data/brand_lock.yaml, Sektion "asset:<pfad>") sichert gegen:
#   - heimliche Manipulation (Fremd-Logo, Farbdreher) -> Hash-Mismatch
#   - Verlust/Loeschung -> Datei fehlt
# SELBSTHEILUNG: bake_brand.py --check regeneriert bei Drift NICHT selbst;
# hier rufen wir bake_brand.py auf (backt bytegleich kanonisch, Font-Pact!),
# danach stimmen Hashes wieder. --set-current versiegelt den Ist-Stand.
ASSET_RELPATHS = [
    "static/images/brand/logo.svg",
    "static/images/brand/logo-light.svg",
    "static/favicon.svg",
    "static/apple-touch-icon.png",
]
HEADER_LOCKUP = ROOT / "layouts" / "_partials" / "header.html"
LOCKUP_MARKERS = ("static/images/brand/logo.svg", "ff-brand")


def _asset_hashes() -> dict:
    import hashlib
    out = {}
    for rel in ASSET_RELPATHS:
        p = ROOT / rel
        out[rel] = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
    return out


# ------------------------------------------------------------ Lock lesen/schreiben

def _yaml_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _yaml_unescape(s: str) -> str:
    return s.replace('\\"', '"').replace("\\\\", "\\")


def load_lock() -> dict:
    """Format: schlüssel: \"wert\" (raw, mit TOML-Escapes wie \\n).

    Zwei Sektionen: hugo.toml-Schluessel UND asset:<pfad> (SHA-256 der
    Marken-Artefakte; Unterscheidung am key-Praefix "asset:")."""
    if not LOCK_FILE.exists():
        return {}
    out = {}
    for line in LOCK_FILE.read_text(encoding="utf-8").splitlines():
        m = re.match(r'^\s*-\s*key:\s*(\S+)\s*$', line)
        if m:
            out[m.group(1)] = None  # Platzhalter
        m2 = re.match(r'^\s*expected:\s*"(.*)"\s*$', line)
        if m2:
            # letzten Key per Reihenfolge zuordnen
            k = list(out)[-1]
            out[k] = _yaml_unescape(m2.group(1))
    return {k: v for k, v in out.items() if v is not None}


def save_locks(values: dict) -> None:
    lines = ["# 🔒 BRAND-LOCK – geschützte Marken-Bausteine (Single Source of Truth)",
             "# Geändert/ausgeweitet wird NUR über: python3 scripts/brand_guard.py --set-current",
             "# (Autowiederherstellung bei Abweichung: siehe scripts/brand_guard.py)",
             "# Sektion asset:<pfad> = SHA-256 der kanonischen Marken-Artefakte (bake_brand.py)", ""]
    for key, val in values.items():
        lines.append(f"- key: {key}")
        lines.append(f'  expected: "{_yaml_escape(val)}"')
    LOCK_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- Prüf-/Heilung

def current_values(src: str) -> dict:
    got = {}
    for key, rx, _label in PROTECTED:
        m = rx.search(src)
        got[key] = m.group(2) if m else None
    return got


def heal(src: str, lock: dict) -> tuple[str, list[str]]:
    differ = []
    for key, rx, label in PROTECTED:
        if key not in lock:
            continue
        m = rx.search(src)
        if m and m.group(2) == lock[key]:
            continue
        if m is None:
            differ.append(f"{label} ({key}): Schlüssel fehlt komplett – NICHT auto-heilbar")
            continue
        old = m.group(2)
        differ.append(f"{label} ({key}): geändert → zurückgesetzt "
                      f"(alt: {str(old)[:40]!r}… → kanonisch)")
        src = src[:m.start(2)] + lock[key] + src[m.end(2):]
    return src, differ


# ---------------------------------------------------- Asset-Wache (12.08. Runde 2)

def check_assets(lock: dict) -> list[str]:
    """Vergleicht Ist-Hashe der Marken-Artefakte mit dem Lock.

    Liefert Liste von Befund-Strings (leer = alles kanonisch)."""
    findings = []
    ist = _asset_hashes()
    for rel in ASSET_RELPATHS:
        want = lock.get(f"asset:{rel}")
        have = ist[rel]
        if want is None:
            findings.append(f"ASSET {rel}: noch nicht im Lock (→ --set-current)")
        elif have is None:
            findings.append(f"ASSET {rel}: DATEI FEHLT (→ Heilung via bake_brand.py)")
        elif have != want:
            findings.append(f"ASSET {rel}: Hash-Mismatch – manipuliert/fremd "
                            f"(ist {have[:12]}… ≠ lock {want[:12]}…)")
    # Header-Lockup-Marker: Template muss das kanonische Logo einbinden
    if not HEADER_LOCKUP.exists():
        findings.append(f"MARKUP {HEADER_LOCKUP.relative_to(ROOT)}: fehlt komplett "
                        f"(Theme-Fallback wuerde Markenfarben verlieren)")
    else:
        src = HEADER_LOCKUP.read_text(encoding="utf-8")
        missing = [m for m in LOCKUP_MARKERS if m not in src]
        if missing:
            findings.append(f"MARKUP header.html: Lockup-Marker verloren {missing} "
                            f"– Logo-Einbindung sabotiert/ausgebaut!")
    return findings


def heal_assets() -> None:
    """Selbstheilung: bake_brand.py backt die kanonischen Artefakte bytegleich
    neu (Determinismus = Sabotageschutz). header.html selbst heilt der
    integrity_guard/blog_doctor-Kontext nicht – das ist ein manueller Fall."""
    import subprocess
    subprocess.run([sys.executable, str(ROOT / "scripts" / "bake_brand.py")],
                   cwd=ROOT, check=True)


# ------------------------------------------------------------------------ Main

def main() -> None:
    if not HUGO_TOML.exists():
        sys.exit("🔴 FEHLER: hugo.toml fehlt komplett – manuelle Prüfung nötig!")
    src = HUGO_TOML.read_text(encoding="utf-8")
    lock = load_lock()

    if SET_CURRENT:
        values = current_values(src)
        values.update({f"asset:{k}": v for k, v in _asset_hashes().items() if v})
        save_locks(values)
        print(f"🔒 Neuer Brand-Lock gespeichert ({len(values)} Einträge):")
        for k, v in values.items():
            n_emojis = len(re.findall(r"[😀-🙏🌀-🛿☀-➿]", v or ""))
            print(f"   {k}: {str(v)[:70]!r}  (Emojis: {n_emojis})")
        return

    if not lock:
        print("ℹ️  Noch kein data/brand_lock.yaml – erstelle initiale Sicherung …")
        values = current_values(src)
        save_locks(values)
        lock = values
        print(f"🔒 Lock initialisiert mit {len(lock)} Einträgen.")

    healed_src, differ = heal(src, lock)
    if differ and DO_FIX:
        HUGO_TOML.write_text(healed_src, encoding="utf-8")

    # Asset-Wache: Logo/Favicon/Header-Lockup (12.08. Runde 2)
    asset_findings = check_assets(lock)
    healed_assets = False
    if asset_findings and DO_FIX:
        if any(f.startswith("ASSET") and "noch nicht im Lock" not in f
               for f in asset_findings):
            heal_assets()            # bake_brand.py: bytegleich kanonisch neu
            healed_assets = True
            asset_findings = check_assets(lock)   # ehrlich neu bewerten

    mode = "FIX" if DO_FIX else "REPORT"
    lines = ["# 🔒 BRAND-REPORT (brand_guard.py)", "",
             f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · Modus: {mode}",
             f"**Lock:** {len(lock)} geschützte Einträge (`data/brand_lock.yaml`) "
             f"· Marken-Assets: {len(ASSET_RELPATHS)} unter SHA-256-Wache", ""]
    if differ:
        lines += ["## ⚠️ Abweichungen" + (" – SELBST GEHEILT ✅" if DO_FIX else " (→ --fix)"), ""]
        lines += [f"- {d}" for d in differ]
    if asset_findings:
        lines += ["## ⚠️ Marken-Asset-Befunde" + (" – Assets SELBST GEHEILT ✅" if healed_assets else ""), ""]
        lines += [f"- {f}" for f in asset_findings]
    if not differ and not asset_findings:
        lines.append("🎉 Alle geschützten Marken-Bausteine unverändert (Willkommenstext, Tagline, "
                     "Meta-Description, Disclaimer) – Logo-Lockup & Artefakte bytegleich kanonisch.")
    lines += ["", "---",
              "_Absichtlich ändern: hugo.toml editieren bzw. `bake_brand.py` anpassen + "
              "`python3 scripts/brand_guard.py --set-current` → Lock übernimmt den neuen Stand._"]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:26]))
    # Exit-Klarheit: ungeheilte (nicht auto-heilbare) Befunde = Exit 1
    if sys.argv[1:] and SET_CURRENT:
        return
    if not DO_FIX and (differ or asset_findings):
        sys.exit(1)
    if DO_FIX and asset_findings:
        sys.exit(1)   # gebliebene MARKUP-Befunde brauchen Menschenhand


if __name__ == "__main__":
    main()
