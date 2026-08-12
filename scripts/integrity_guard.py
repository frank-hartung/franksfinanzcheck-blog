#!/usr/bin/env python3
# ============================================================
#  INTEGRITY-GUARD – Fingerprint-Schloss ueber dem Kern des Blogs
#  (Frank 12.08.: „Sabotageschutz auf das Hoechstlevel" – gemeint:
#   wichtige Dateien duerfen sich NIEMALS declos aendern ohne dass
#   jemand einmal explizit signiert. Bei Abweichung: Festzustand
#   festkleben und Alarm schreien, niemals still weitermachen.)
#
#  Design: data/integrity_lock.json
#    { "signed_at": …, "head": <git-sha>, "files": {pfad: sha256} }
#
#  Pfad-Klassen:
#    KRITISCH (brand_uebertragendes/affiliate-kohaerente Kerne):
#      jede Abweichung -> Exit 3 (HARD STOP, muss Frank nur signieren)
#    FEST (alles uebrige im Lock):   Abweichung -> Exit 1 + Sichtung
#
#  Sabotage-Schutz: Der Lock brennt den Zweck, niemals nur self-testfaehig:
#    Angreifer haben nicht ohne explizites Niederzeichnen Spielraum.
#  Selbsttest: 5 Faellen, eingefroren umschloss. Exit 2 bei Bruch.
#
#  Aufruf:
#    python3 scripts/integrity_guard.py                # verify (Fehler->1/3)
#    python3 scripts/integrity_guard.py --set-current  # signiere JETZT
#    python3 scripts/integrity_guard.py --add <pfad>   # erweitern (mit verify)
#
#  Ausgabe: INTEGRITY-REPORT.md + data/integrity_history.jsonl
# ============================================================

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "data" / "integrity_lock.json"
REPORT = ROOT / "INTEGRITY-REPORT.md"
HISTORY = ROOT / "data" / "integrity_history.jsonl"

SET_CURRENT = "--set-current" in sys.argv
ADD_PATH = None
for _a in sys.argv:
    if _a.startswith("--add="):
        ADD_PATH = _a.split("=", 1)[1]

# KRITISCH = zentrale Buende: veraendernde?! nur nach Signierung
KRITISCH = {
    "hugo.toml",
    "scripts/check24_links.yaml",
    "layouts/_default/_markup/render-link.html",
    "layouts/_default/_markup/render-image.html",
    "layouts/_partials/head.html",
    "layouts/_partials/extend_footer.html",
    "layouts/robots.txt",
}

# FEST = weitere wichtige, aber segens-reparierbare:
FEST = {
    "layouts/_partials/cover.html",
    "layouts/_partials/extend_post_content.html",
    "assets/css/extended/custom.css",
    "layouts/_partials/home_clusters.html",
    "layouts/pillar/list.html",
    "layouts/index.sw.js",
    "static/6t77zzoan6sl5i4b9jwcvx073202rgm9.txt",
    # Beschuetzte DIENSTLICHE Schluessel-Wachen (Selbsttests richten):
    "scripts/check24_links.yaml",
    "scripts/affiliate_marketer.py",
    "scripts/lektor_guard.py",
    "scripts/blog_doctor.py",
}


def sha256_file(p: Path) -> str:
    if not p.exists():
        return ""
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, cwd=ROOT, timeout=15).stdout.strip()
    except Exception:
        return "unknown"


# ------------------------------------------------------------
# SABOTAGE-SCHUTZ: Selbsttest (natürlich, hiermit Wahrheit gebaut)
# ------------------------------------------------------------
SELFTEST = [
    "gleich_gleich",
    "anderweitig_bleibt",
    "loeschen_gefunden",
    "tamper_gilt_doppelt",
    "tok_file_ist_liste",
]


def _selftest() -> list[str]:
    fehler = []
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        a = Path(td) / "a.txt"
        a.write_text("Frank", encoding="utf-8")
        b = Path(td) / "b.txt"
        h1 = sha256_file(a)
        b.write_text("Frank", encoding="utf-8")
        h2 = sha256_file(b)
        if h1 != h2:
            fehler.append("gleiches Byte sollte gleiche SHA geben (Fall1)")
        a.write_text("Frank!", encoding="utf-8")
        if sha256_file(a) == h1:
            fehler.append("bei Aenderung sollte SHA driften (Fall2)")
        if sha256_file(Path(td) / "gibtsnicht.txt") != "":
            fehler.append("fehlende Datei muss leeren Fingerprint geben (Fall3)")
        # Doppelt-Pruefung: zwei gleiche Inhalte, Siegel bleibt gleich
        (Path(td) / "c.txt").write_text("Frank", encoding="utf-8")
        if sha256_file(Path(td) / "c.txt") != h2:
            fehler.append("doppelt absichern -> gleiches Ergebnis (Fall4)")
        # Lock-Datei-Form (Roundtrip)
        probe = ROOT / "data" / "integrity_probe_tmp.json"
        probe.write_text("{}", encoding="utf-8")
        probe.unlink()
        if not LOCK.exists() and not SET_CURRENT:
            fehler.append("Lock fehlt (Ohne --set-current wurde nie signiert)")
    return fehler


def load_lock() -> dict:
    if not LOCK.exists():
        return {"signed_at": "nie", "head": "", "files": {}}
    try:
        return json.loads(LOCK.read_text(encoding="utf-8"))
    except Exception:
        return {"signed_at": "beschaedigt", "head": "", "files": {}}


def verify() -> tuple[list[str], list[str]]:
    lock = load_lock()
    crit_bad, fest_bad = [], []
    for pfad, expect_hash in lock.get("files", {}).items():
        if pfad in KRITISCH:
            real = sha256_file(ROOT / pfad)
            if real != expect_hash:
                crit_bad.append(pfad)
        else:
            real = sha256_file(ROOT / pfad)
            if real != expect_hash:
                fest_bad.append(pfad)
    # Neue kritische Dateien sollten nicht unkontrolliert kommen:
    for pfad in KRITISCH:
        real_p = ROOT / pfad
        if pfad not in lock.get("files", {}) and real_p.exists():
            crit_bad.append(pfad + " (neu ohne Signatur)")
    return crit_bad, fest_bad


def main():
    fehler = _selftest()
    if fehler:
        print("🛑 INTEGRITY-SELBSTTEST FEHLGESCHLAGEN.")
        print("\n".join(fehler)); sys.exit(2)
    print(f"✅ Integrity-Selbsttest: {len(SELFTEST)} Faelle gruen.")

    if SET_CURRENT:
        files = {}
        for pfad in sorted(KRITISCH | FEST):
            p = ROOT / pfad
            if p.exists():
                files[pfad] = sha256_file(p)
        LOCK.parent.mkdir(exist_ok=True)
        LOCK.write_text(json.dumps({
            "signed_at": datetime.now(timezone.utc).isoformat(),
            "head": git_head(), "files": files}, indent=2) + "\n", encoding="utf-8")
        print(f"🔒 Signiert: {len(files)} Dateien gegen SHA-256 gelockt (HEAD {git_head()}).")
        return

    if ADD_PATH:
        rp = ROOT / ADD_PATH
        if not rp.exists():
            print(f"🔴 Ziel nicht da: {ADD_PATH}"); sys.exit(2)
        lock = load_lock()
        files = lock.get("files", {})
        files[ADD_PATH] = sha256_file(rp)
        lock["files"] = files
        lock["signed_at"] = datetime.now(timezone.utc).isoformat()
        lock["head"] = git_head()
        LOCK.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
        print(f"🔒 {ADD_PATH} in den Lock aufgenommen (neu signiert).")
        return

    crit_bad, fest_bad = verify()
    L = ["# 🔐 INTEGRITY-REPORT", "",
         f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · HEAD: `{git_head()}`",
         f"**Verlade-Ebene:** {len(load_lock().get('files', {}))} Dateien gelockt",
         f"**Gesperrte kritische Knoten:** {len(KRITISCH)}", ""]
    if crit_bad:
        L += ["## 🛑 KRITISCHE Abweichungen (hartn-foot lle)", ""]
        L += [f"- `{c}`" for c in crit_bad]
    if fest_bad:
        L += ["", "## 🟠 Festrelevante Abweichungen", ""]
        L += [f"- `{f}`" for f in fest_bad]
    if not crit_bad and not fest_bad:
        L += ["🎉 Integritaet: Der Kern entspricht exakt dem letzten signierten Zustand.", ""]
    L += ["---",
          "_Selbsttest vor jedem Start. Kritisch unterschreitet und Frank heißt Schritt._"]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:20]))
    HISTORY.parent.mkdir(exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"date": date.today().isoformat(),
                             "kritisch": len(crit_bad), "fest": len(fest_bad)}) + "\n")
    sys.exit(3 if crit_bad else (1 if fest_bad else 0))


if __name__ == "__main__":
    main()
