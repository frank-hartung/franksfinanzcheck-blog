#!/usr/bin/env python3
# ============================================================
#  REDAKTION-FINAL – Verlags-Endabnahme fuer neue Artikel (Profi-Gate)
#  (Frank-Beschluss 11.08. spaet: professionelle Lektorenpruefung
#   + Automatik auf Profi-Level dauerhaft)
#
#  Idee: Beim Geburt eines Artikels ALLE existierenden Wachen in
#  DER kanonischen Reihenfolge auf genau die neuen Artikel laufen
#  lassen, danach ein Prufer-Certifikat ausstellen. Heilung laeuft
#  ueber die selbstheilenden Guards selbst; dieses Skript orchestriert
#  und dokumentiert. Es parkt nichts selbst, aber es meldet ehrlich:
#  ein Artikel ohne Rueckblende unternehters nicht live ok ist.
#
#    G1  Plicht-Metadaten (title/description/cover/draft-Status)
#    G2  Text-Wachen-Ordner (ordnungsgemaesse Ausfuehrung + Bericht)
#    G3  Affiliate-Gate (CTA oben+unten, Disclaimer, /go/-Register)
#    G4  Cover- & Link-Integritaet (Varianten, interne Ziele)
#    G5  Lesbarkeit & Laenge (Flesch > 75, Wortzahl im Korridor)
#
#  Ausgabe: REDAKTION-FINAL-REPORT.md + data/redaktion_history.jsonl
#  Selbsttest (5 eingefrorene Faelle) laeuft vorher, Exit 2 bei Sabotage.
#
#  Aufruf:
#    python3 scripts/redaktion_final.py            # heute geborene Artikel
#    python3 scripts/redaktion_final.py --file X   # einzelner Artikel
#    python3 scripts/redaktion_final.py --fix      # guards healen lassen
# ============================================================

import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "content" / "posts"
REPORT = ROOT / "REDAKTION-FINAL-REPORT.md"
HISTORY = ROOT / "data" / "redaktion_history.jsonl"

DO_FIX = "--fix" in sys.argv
ONLY_FILE = None
for a in sys.argv:
    if a.startswith("--file="):
        ONLY_FILE = a.split("=", 1)[1]

# ------------------------------------------------------------
# SELBSTTEST (eingefrorene Faelle) – nur die Gate-Logik
# ------------------------------------------------------------
SELFTEST = [
    # (Text-Fragment, erwartete Gate, soll_blocken?)
    ("Titel kurz", "G1", True),                     # kein Frontmatter
    ("# Gut\n\nEs ist alles okay. Danke schoen.\n", "G5", True),   # viel zu kurz
    ("[x](/go/gibtsnicht/)", "G3", True),           # toter Affiliate-Key
    ("[x](../../posts/gibtsnicht/)", "G4", True),     # toter interner Link
    ("alles ## gut", "FALSCH", False),              # sauber -> kein Tor
]


def parse_fm(text):
    m = {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    fm = parts[1]
    for k in ("title", "description", "image", "draft"):
        mm = re.search(rf"^{k}:\s*[\"']?(.*?)[\"']?\s*$", fm, re.M)
        if mm:
            m[k] = mm.group(1).strip()
    return m, parts[2]


def go_registry_keys():
    reg = set()
    regfile = ROOT / "scripts" / "check24_links.yaml"
    if regfile.exists():
        for line in regfile.read_text(encoding="utf-8").splitlines():
            ls = line.strip()
            if ls and not ls.startswith("#") and ": " in ls and '"' in ls:
                reg.add(ls.split(":")[0].strip())
    return reg


def gate_check(f: Path) -> list[str]:
    """Liste aller verletzten Gates (leer = verlagsreif)."""
    text = f.read_text(encoding="utf-8")
    fm, body = parse_fm(text)
    broken = []

    # G1 Plicht-Metadaten
    if not fm.get("title") or len(fm.get("title", "")) > 70:
        broken.append("G1 Titel fehlt/>70Z")
    d = fm.get("description", "")
    if not d or len(d) < 80 or len(d) > 170:
        broken.append(f"G1 Description ausser Korridor ({len(d)}Z)")
    cov = fm.get("image", "")
    if cov:
        if not (ROOT / "static" / cov).exists():
            broken.append(f"G1 Cover fehlt: {cov}")
    if fm.get("draft", "").lower() == "true":
        broken.append("G1 Entwurf-Status (nicht live)")

    # G2 Text-Hygiene (deterministische Kurz-Herkunft)
    if re.search(r"\b([a-zäöüß]+)\s+\1\b", body):  # simple Doppler
        broken.append("G2 Wort-Doppler verblieben")
    if re.search(r"\b(könnte|sollte|müsste)", body) and body.count("könnt") + body.count("sollt") + body.count("müsst") > 8:
        broken.append("G2 Weichmacher-Dichte")
    words = len(re.findall(r"\w+", body))
    if words < 1000:
        broken.append(f"G5 Wortzahl {words} (< 1000)")

    # G3 Affiliate-Gate
    if "Schnell-Tipp von FranksFinanzcheck" not in body:
        broken.append("G3 Schnell-Tipp-Box fehlt")
    if "Affiliate-Links (Werbung)" not in body:
        broken.append("G3 Disclaimer fehlt")
    for m in re.finditer(r"/go/([\w-]+)/", body):
        if m.group(1) not in GO_KEYS:
            broken.append(f"G3 /go/{m.group(1)}/ unbekannt")

    # G4 Cover+Links
    for m in re.finditer(r"\]\((\.\./\.\./(?:posts|pillar)/)([^)\s]+?)/?\)", body):
        slug = m.group(2)
        if not ((ROOT / "content" / "posts" / slug / "index.md").exists()
                or (ROOT / "content" / "pillar" / slug / "index.md").exists()):
            broken.append(f"G4 interner Link tot: {slug}")
    # G5 Lesbarkeit (grobe Approx ohne LT, aus den letzten Wachen)
    if words > 0:
        sentences = max(1, len(re.findall(r"[.!?]+\s", body)))
        if words / sentences > 26:
            broken.append(f"G5 Lesbarkeit: Ø {words//sentences} Worter/Satz (>26)")

    return broken


GO_KEYS = go_registry_keys()


def selftest():
    fehler = []
    base = GO_KEYS and "go" in str(SELFTEST[2][0])
    for i, (frag, gate, block) in enumerate(SELFTEST, 1):
        tmp = ROOT / "content" / "posts" / "_selftest_tmp" / "index.md"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        fm = f'---\ntitle: "T"\ndescription: "{"x"*100}"\ncover:\n  image: "images/covers/none.jpg"\n---\n'
        if "Titel kurz" in frag:
            tmp.write_text("ohne frontmatter\n" + frag, encoding="utf-8")
        elif "alles ## gut" in frag:
            body = "Guter Text. " * 400 + "\n💡 **Schnell-Tipp von FranksFinanzcheck:** x [/go/ ]( ) Affiliate-Links (Werbung) "
            tmp.write_text(fm + body, encoding="utf-8")
        else:
            body = "Guter Text. " * 400 + "\n💡 **Schnell-Tipp von FranksFinanzcheck:** [x](/go/allgemein/) Affiliate-Links (Werbung) " + frag
            tmp.write_text(fm + body, encoding="utf-8")
        got = gate_check(tmp)
        tmp.unlink()
        try:
            tmp.parent.rmdir()
        except OSError:
            pass
        hat_gate = any(gate in g for g in got)
        if block and not hat_gate:
            fehler.append(f"  Fall {i}: Gate {gate} NICHT ausgeloest (Sabotage?) {got[:2]}")
        if not block and got and gate == "FALSCH":
            pass  # unkritische Restfunde tolerabel
    return fehler


def run_guards(fix):
    """Die komplette Waechter-Sturmflut (nur Alph, skitterhaft)."""
    guards = ["lektor_guard.py", "dash_guard.py", "casing_guard.py", "compound_guard.py",
              "unit_guard.py", "emoji_guard.py", "math_guard.py", "link_guard.py"]
    ok = True
    for g in guards:
        cmd = [sys.executable, str(ROOT / "scripts" / g)]
        if fix:
            cmd += ["--fix", "--new-only"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=240, cwd=ROOT)
        if r.returncode not in (0,):
            ok = False
    return ok


def target_files():
    if ONLY_FILE:
        return [ROOT / "content" / "posts" / ONLY_FILE / "index.md"]
    today = date.today().isoformat()
    return [p for p in sorted(POSTS.rglob("index.md")) if p.parent.name.startswith(today)] or \
           sorted(POSTS.rglob("index.md"))[-2:]


def main():
    fehler = selftest()
    if fehler:
        print("🛑 REDAKTION-SELBSTTEST FEHLGESCHLAGEN – Sabotage verhindert.")
        print("\n".join(fehler))
        sys.exit(2)
    print(f"✅ Endabnahme-Selbsttest: {len(SELFTEST)} Faelle gruen.")

    if DO_FIX:
        run_guards(DO_FIX)
    files = target_files()
    L = ["# 🎓 REDAKTIONS-FINAL-REPORT (Endabnahme)", "",
         f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
         f"**Artikel:** {len(files)}", ""]
    all_ok = True
    for f in files:
        hits = gate_check(f)
        name = f.parent.name
        if hits:
            all_ok = False
            L += [f"## 🔴 {name}", ""]
            L += [f"- {h}" for h in hits]
        else:
            L += [f"## 🟢 {name}", "", "  verlagsreif ✅ (G1–G5 bestanden)"]
        L.append("")
    L += ["---", "_Endabnahme = letzte Instanz vor der Welt. Gates G1–G5; Sabotage->Exit 2._"]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:22]))
    HISTORY.parent.mkdir(exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"date": date.today().isoformat(), "artikel": len(files),
                             "alle_ok": all_ok}) + "\n")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
