#!/usr/bin/env python3
# ============================================================
#  KI-KENNZEICHNUNGS-GATE – „Mit KI erstellt“ bleibt, wo es hingehört
#
#  Sicherheitsaudit 14.10.2026 (M-17): 17 von 59 live geschalteten
#  Bot-Artikeln trugen `ai_generated: false` – 9 davon durch einen einzigen
#  Commit, der das Feld still umstellte. Das Feld steuert das sichtbare
#  Label „Mit KI erstellt“ (layouts/_partials/ff_pruefzeile.html). Seit dem
#  02.08.2026 verlangt Art. 50 Abs. 4 KI-VO die Kennzeichnung KI-erzeugter
#  Texte zu Angelegenheiten von öffentlichem Interesse, sofern kein Mensch
#  die redaktionelle Verantwortung nach echter Prüfung übernommen hat.
#
#  Regeln (Register: data/ki_kennzeichnung.yaml):
#    K1  Artikel unter `maschinell` haben IMMER ai_generated: true.
#    K2  ai_generated: false nur mit Eintrag unter `menschlich` ODER mit
#        freigegebener `redaktionelle_pruefung` (status: freigegeben).
#    K3  Fehlt das Feld, gilt es als false (→ K2).
#
#  Aufruf:
#    python3 scripts/ki_kennzeichnung_gate.py            # Report
#    python3 scripts/ki_kennzeichnung_gate.py --gate     # Exit 1 bei Fund
#    python3 scripts/ki_kennzeichnung_gate.py --fix      # heilen: ai_generated: true
#    python3 scripts/ki_kennzeichnung_gate.py --selftest
#  Im Deploy läuft --fix; die Heilung committet der Gate-Heilungspfad.
#  Über-Kennzeichnen ist rechtlich unschädlich, Unter-Kennzeichnen nicht.
# ============================================================
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "content" / "posts"
REGISTER = ROOT / "data" / "ki_kennzeichnung.yaml"


def register_lesen(pfad: Path = REGISTER) -> dict[str, set[str]]:
    """Einfacher, abhängigkeitsfreier Leser für das Listenformat."""
    daten: dict[str, set[str]] = {"maschinell": set(), "menschlich": set()}
    aktuell = None
    if not pfad.exists():
        return daten
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        if not zeile.strip() or zeile.lstrip().startswith("#"):
            continue
        m = re.match(r"^([a-z_]+):\s*$", zeile)
        if m:
            aktuell = m.group(1) if m.group(1) in daten else None
            continue
        m = re.match(r"^\s+-\s+([A-Za-z0-9._-]+)\s*$", zeile)
        if m and aktuell:
            daten[aktuell].add(m.group(1))
    return daten


def slug_von(pfad: Path) -> str:
    return pfad.parent.name if pfad.name == "index.md" else pfad.stem


def kopf_von(text: str) -> str:
    if not text.startswith("---"):
        return ""
    ende = text.find("\n---", 3)
    return text[3:ende] if ende > 0 else ""


def ki_wert(kopf: str) -> bool | None:
    m = re.search(r"(?m)^ai_generated:\s*(true|false)\s*$", kopf)
    return None if not m else m.group(1) == "true"


def freigegeben(kopf: str) -> bool:
    m = re.search(r"(?ms)^redaktionelle_pruefung:\s*\n(.*?)(?=^\S|\Z)", kopf)
    if not m:
        return False
    st = re.search(r"(?m)^\s+status:\s*[\"']?([A-Za-z]+)", m.group(1))
    return bool(st and st.group(1).lower() in ("freigegeben", "approved"))


def pruefen(posts: Path = POSTS, register: dict | None = None) -> list[tuple[Path, str]]:
    reg = register if register is not None else register_lesen()
    funde = []
    for p in sorted(posts.rglob("*.md")):
        if p.name == "_index.md":
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        kopf = kopf_von(text)
        if not kopf:
            continue
        slug = slug_von(p)
        wert = ki_wert(kopf)
        if slug in reg["maschinell"] and wert is not True:
            funde.append((p, "K1 maschinell erstellt, aber nicht als KI gekennzeichnet"))
        elif wert is not True and slug not in reg["menschlich"] and not freigegeben(kopf):
            funde.append((p, "K2 ai_generated: false ohne Register-Eintrag „menschlich“ und ohne freigegebene redaktionelle Prüfung"))
    return funde


def heilen(pfad: Path) -> bool:
    text = pfad.read_text(encoding="utf-8")
    kopf = kopf_von(text)
    if not kopf:
        return False
    if re.search(r"(?m)^ai_generated:", kopf):
        neu_kopf = re.sub(r"(?m)^ai_generated:.*$", "ai_generated: true", kopf, count=1)
    else:
        neu_kopf = kopf.rstrip("\n") + "\nai_generated: true\n"
    neu = "---" + neu_kopf + text[3 + len(kopf):]
    if neu != text:
        pfad.write_text(neu, encoding="utf-8")
        return True
    return False


def selbsttest() -> int:
    import tempfile
    fehler = []
    with tempfile.TemporaryDirectory() as tmp:
        posts = Path(tmp) / "posts"
        for slug, kopf in {
            "bot-falsch": "ai_generated: false",
            "bot-gut": "ai_generated: true",
            "mensch": "ai_generated: false",
            "ohne-feld": "title: x",
            "geprueft": "ai_generated: false\nredaktionelle_pruefung:\n  status: freigegeben\n  pruefer:\n    name: X",
            "maschine-als-mensch": "ai_generated: false",
        }.items():
            (posts / slug).mkdir(parents=True)
            (posts / slug / "index.md").write_text(f"---\ntitle: T\n{kopf}\n---\nText\n", encoding="utf-8")
        reg = {"maschinell": {"bot-falsch", "bot-gut", "maschine-als-mensch"}, "menschlich": {"mensch", "maschine-als-mensch"}}
        funde = {slug_von(p): g for p, g in pruefen(posts, reg)}
        erwartet = {"bot-falsch", "ohne-feld", "maschine-als-mensch"}
        if set(funde) != erwartet:
            fehler.append(f"Funde {sorted(funde)} statt {sorted(erwartet)}")
        for p, _ in pruefen(posts, reg):
            heilen(p)
        if pruefen(posts, reg):
            fehler.append("Heilung nicht vollständig")
        if "ai_generated: true" not in (posts / "ohne-feld" / "index.md").read_text(encoding="utf-8"):
            fehler.append("fehlendes Feld nicht ergänzt")
        if "ai_generated: false" not in (posts / "mensch" / "index.md").read_text(encoding="utf-8"):
            fehler.append("menschlicher Artikel wurde verändert")
    reg_echt = register_lesen()
    if not reg_echt["maschinell"]:
        fehler.append("Register data/ki_kennzeichnung.yaml leer oder unlesbar")
    if reg_echt["maschinell"] & reg_echt["menschlich"]:
        fehler.append("Register widersprüchlich: Slug zugleich maschinell und menschlich")
    for f in fehler:
        print(f"❌ {f}")
    if fehler:
        return 2
    print("✅ KI-Kennzeichnungs-Gate-Selbsttest: K1/K2/K3, Heilung und Register korrekt.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="KI-Kennzeichnungs-Gate (Audit M-17)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--gate", action="store_true")
    g.add_argument("--fix", action="store_true")
    g.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selbsttest()
    funde = pruefen()
    for p, grund in funde:
        rel = p.relative_to(ROOT)
        if a.fix and heilen(p):
            print(f"::notice title=KI-Kennzeichnung geheilt::{rel}: {grund} → ai_generated: true")
        else:
            print(f"::error title=KI-Kennzeichnung::{rel}: {grund}")
    if not funde:
        print("✅ KI-Kennzeichnung: alle Artikel korrekt gekennzeichnet.")
    if a.gate and funde:
        return 1
    if a.fix:
        return 1 if pruefen() else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
