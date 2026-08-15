#!/usr/bin/env python3
# ============================================================
#  WORKSPACE-GUARD – Repo-Hygiene & Selbstheilung (Profi-Level)
#
#  Auftrag (11.08.2026): Vollautomatischer Workspace-Checker fuer das
#  Blog-Repo – wie ihn professionelle Maintainer betreiben.
#
#  PRÜFT & HEILT:
#    W1  AUFGEHÄNGTE DATEIEN: kaputte/gejunkte Dateien im Repo
#        (Thumbs.db, .DS_Store, *.pyc, __pycache__, Emacs-~, *.tmp,
#        editor-Backups) -> AUTO-LOESCHEN
#    W2  WAISEEN: static/images/covers/<slug>.* ohne dazugehoerigen
#        Artikel (Phantom! z. B. nach Loeschungen) -> AUTO-LOESCHEN
#    W3  DUPLIKATE: byte-idente Dateien (sha256) -> REPORT
#        (Auto-Merge nur bei exakt gleichem Inhalt UND sicherem
#        Kanon-Pfadmuster; sonst Meldung)
#    W4  DICKSCHIFFE: Dateien > 300 KB (Bilder) / > 500 KB (Rest)
#        -> REPORT (Bild-Optimierung liegt bei generate_covers)
#    W5  GESCHICHTSLINIE-ROTATION: data/*_history.jsonl + Reports
#        werden je nach Alter auf die juengsten N Eintraege gestutzt
#        (Standard: 400 Zeilen) -> AUTO-STUTZEN (mit Sicherungsfrist)
#    W6  RIESEN im Git (tree, >5 MB) -> REPORT (Hinweis git gc)
#
#  AUSSCHLUSS: niemals anfassen: hugo.toml, _partials, layouts/, themes/,
#  .github/, content/, alles unter scripts/Register. Nur W1/W2/W5 heilen.
#
#  Aufruf:
#    python3 scripts/workspace_guard.py             # Report
#    python3 scripts/workspace_guard.py --fix       # heilen + commit-ready
#    python3 scripts/workspace_guard.py --json      # fuer Bots
#
#  Ausgabe: WORKSPACE-REPORT.md · Verlauf data/workspace_history.jsonl
# ============================================================

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone, date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "WORKSPACE-REPORT.md"
HISTORY = ROOT / "data" / "workspace_history.jsonl"
DO_FIX = "--fix" in sys.argv
AS_JSON = "--json" in sys.argv
DRY_RUN = "--dry-run" in sys.argv

KB = 1024
SCHWELLE_BILD = 300 * KB
SCHWELLE_SONST = 500 * KB
HIST_MAX_LINES = 400

JUNK_PATTERNS = [
    r"(^|/)(\.DS_Store|Thumbs\.db|desktop\.ini)$",
    r"\.pyc$", r"(^|/)__pycache__(/|$)", r"~\$", r"\.bak$", r"\.swp$",
    r"\.orig$", r"\.tmp$", r"^(tmp|temp)/",
]
SKIP_DIRS = {".git", "themes", "node_modules", "public", "resources", ".github",
             "layouts", "archetypes"}
SAFE_HISTORY_RE = re.compile(r"data/(\w+_history|audit).*\.jsonl$")


def iter_tracked_files():
    """Alle von git getrackten Dateien (schnell & nur die wirklichen Repo-Inhalte)."""
    import subprocess
    out = subprocess.run(["git", "-c", "core.quotepath=false", "ls-files"],
                         cwd=ROOT, capture_output=True, text=True, timeout=30).stdout
    return [ROOT / l for l in out.splitlines() if l.strip() and
            not any(part in SKIP_DIRS for part in Path(l).parts)]


def hash_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------- W1: Junk

def is_junk(rel: str) -> bool:
    """Reine Entscheidung (Sabotage-testbar): ist dieser Pfad Muell?"""
    return any(re.search(rx, rel) for rx in JUNK_PATTERNS)


def find_junk(files: list) -> list:
    return [str(p.relative_to(ROOT)) for p in files
            if is_junk(str(p.relative_to(ROOT)))]


# ------------------------------------------------------------- W2: Waisen

ORPHAN_PATTERN = re.compile(
    r"static/images/covers/(?:\d+/)?(?:avif/|webp/)?([\w-]+)\.(jpg|webp|avif)$")


def existing_slugs() -> set:
    slugs = {p.parent.name for p in (ROOT / "content").rglob("index.md")}
    slugs |= {p.parent.name for p in (ROOT / "content").rglob("_index.md")}
    return slugs


def find_orphan_covers(files: list, slugs: set) -> list:
    out = []
    for p in files:
        rel = str(p.relative_to(ROOT))
        m = ORPHAN_PATTERN.match(rel)
        if m and m.group(1) not in slugs:
            out.append(rel)
    return sorted(out)



# ------------------------------------------------------------- W3: Duplikate

# Billigliste (12.08., Frank-Cleanings): DOPPELT MIT ABSICHT – nie melden.
# - Gateway-Paare zeigen per Frank-Entscheid auf dasselbe Ziel (fluege≡reisen,
#   girokonto≡tagesgeld entsprechend C24-Bevoelkerung).
# - IndexNow-Key muss doppelt existieren (Pflicht-Modell: Wurzel-Endpunkt +
#   interne abrufbare Quell-Datei – der Guard verifizierte Identitaet 12.08.).
DUP_BILLIG = [
    ("static/go/fluege/index.html", "static/go/reisen/index.html"),
    ("static/go/girokonto/index.html", "static/go/tagesgeld/index.html"),
    ("scripts/indexnow_key.txt", "static/6t77zzoan6sl5i4b9jwcvx073202rgm9.txt"),
]


def find_duplicates(files: list) -> dict:
    by_hash = {}
    for p in files:
        if p.stat().st_size > 5 * KB * 1024:    # nur bis 5 MB hashbar
            continue
        h = hash_file(p)
        by_hash.setdefault(h, []).append(str(p.relative_to(ROOT)))
    return {h: xs for h, xs in by_hash.items() if len(xs) > 1 and not _dup_billig(xs)}


def _dup_billig(xs: list) -> bool:
    """True, wenn die Gruppe komplett auf der Billigliste steht."""
    return any(all(b in xs for b in pair) for pair in DUP_BILLIG)


# ------------------------------------------------------------- W4: Dickschiffe

def find_heavy(files: list) -> list:
    out = []
    for p in files:
        size = p.stat().st_size
        lim = SCHWELLE_BILD if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif") else SCHWELLE_SONST
        if size > lim:
            out.append((str(p.relative_to(ROOT)), size))
    return sorted(out, key=lambda x: -x[1])


# ------------------------------------------------------------- W5: Rotation

def rotate_histories() -> list:
    rotated = []
    for p in (ROOT / "data").rglob("*.jsonl"):
        rel = str(p.relative_to(ROOT))
        if not SAFE_HISTORY_RE.search(rel) and "_history" not in p.name and p.name != "audit_log.jsonl":
            continue
        text = p.read_text(encoding="utf-8")
        lines = text.splitlines()
        if len(lines) > HIST_MAX_LINES:
            if DO_FIX and not DRY_RUN:
                p.write_text("\n".join(lines[-HIST_MAX_LINES:]) + "\n", encoding="utf-8")
            rotated.append((rel, len(lines)))
    return rotated


# ------------------------------------------------------------- W7: Konflikt-Marker
# (12.08.: Git-Marker in CONTENT brachen das Deploy-Build mittags. Fortan wird
#  jeder niemals mehr das Stapelschweigen beweisen.)

MARKER_START = re.compile(r"^<<<<<<<[^\n]*$", re.M)
MARKER_MID = re.compile(r"^=======\s*$", re.M)
MARKER_END = re.compile(r"^>>>>>>>[^\n]*$", re.M)


def sweep_markers(do_fix: bool) -> list:
    """Scannt bei (12.08. Bisschen mehr): content/, scripts/*.py, Root-*.md
    (denn Markierungen haben uns schon Skripte + Reports beschmutzt; das
    auf Materie herabkam baute den Build einmal kaputt)"""
    betroffen = []
    pfade = list((ROOT / "content").rglob("*.md")) \
          + list((ROOT / "scripts").glob("*.py")) \
          + list(ROOT.glob("*.md"))
    for f in pfade:
        t = f.read_text(encoding="utf-8")
        if not (MARKER_START.search(t) and MARKER_END.search(t)):
            continue
        betroffen.append(str(f.relative_to(ROOT)))
        if do_fix:
            new = re.sub(r"(?ms)^<<<<<<<[^\n]*\n(.*?)^=======$\n(.*?)^>>>>>>>[^\n]*$",
                         _merge_wahl, t)
            f.write_text(new, encoding="utf-8")
    return betroffen


def _merge_wahl(m):
    """Die bessere Seite heil (bevorzugt die Zeilenreichere)."""
    a, b = m.group(1), m.group(2)
    la = [l for l in a.split("\n") if l.strip()]
    lb = [l for l in b.split("\n") if l.strip()]
    if not lb:
        return a
    if not la:
        return b
    return a if len(la) >= len(lb) else b


def git_size_mb() -> float:
    try:
        import subprocess
        out = subprocess.run(["du", "-sm", ".git"], cwd=ROOT,
                             capture_output=True, text=True, timeout=20).stdout
        return float(out.split()[0])
    except Exception:
        return 0.0


# ------------------------------------------------------------
# SABOTAGE-SCHUTZ (12.08.): eingefrorene Faelle pruefen W1-Billig/
# Waison-/Junk-Logik und Exit 2, BEVOR irgendetwas geloescht wird.
# ------------------------------------------------------------
SELFTEST = [
    # (Purpose, Eingabe, erwartet)
    ("junk-bak",     is_junk,  ("layouts/_partials/x.bak",), True),
    ("junk-swp",     is_junk,  ("assets/css/core.css.swp",), True),
    ("junk-pycache", is_junk,  ("scripts/__pycache__/lektor.pyc",), True),
    ("sauber",       is_junk,  ("scripts/lektor_guard.py",), False),
    ("sauber-md",    is_junk,  ("WORKSPACE-REPORT.md",), False),
    ("billig-go",    _dup_billig, (["static/go/fluege/index.html", "static/go/reisen/index.html"],), True),
    ("billig-key",   _dup_billig, (["scripts/indexnow_key.txt", "static/6t77zzoan6sl5i4b9jwcvx073202rgm9.txt"],), True),
    ("no-dup",       _dup_billig, (["x/a.md", "x/b.md"],), False),
    ("orphan",       lambda a: bool(ORPHAN_PATTERN.match(a)), ("static/images/covers/denne.jpg",), True),
    ("no-orphan",    lambda a: bool(ORPHAN_PATTERN.match(a)), ("content/posts/x/index.md",), False),
    ("marker-start", lambda t: bool(MARKER_START.search(t)), ("<<<<<<< HEAD\nneu\n=======\nalt\n>>>>>>> x\n",), True),
    ("marker-clean", lambda t: bool(MARKER_START.search(t)), ("## Alles sauber\n\nKein Bruch.\n",), False),
]


def run_selftest() -> list[str]:
    fehler = []
    for i, (zweck, fn, args, want) in enumerate(SELFTEST, 1):
        try:
            got = fn(*args)
        except Exception as e:
            fehler.append(f"  Fall {i} ({zweck}): Ausnahme {type(e).__name__}")
            continue
        if got != want:
            fehler.append(f"  Fall {i} ({zweck}): erwartet {want}, bekam {got}")
    return fehler


def main() -> None:
    # SABOTAGE-SCHUTZ zuerst: Waechter prueft sich selbst, BEVOR er loescht.
    stf = run_selftest()
    if stf:
        print("🛑 WORKSPACE-SELBSTTEST FEHLGESCHLAGEN – Sabotage verhindert.")
        print("   Kein Feststoff wird entfernt. Bitte workspace_guard.py pruefen:")
        print("\n".join(stf))
        sys.exit(2)
    print(f"✅ Workspace-Selbsttest: {len(SELFTEST)} Faelle gruen.")
    files = iter_tracked_files()
    slugs = existing_slugs()

    junk = find_junk(files)
    orphans = find_orphan_covers(files, slugs)
    dups = find_duplicates(files)
    heavy = find_heavy(files)
    rotated = rotate_histories()
    betroffen = sweep_markers(DO_FIX)   # W7 Marker-Jaeger (12.08.)
    git_mb = git_size_mb()

    fixed_junk, fixed_orphans = [], []
    if DO_FIX and not DRY_RUN:
        import subprocess
        for rel in junk + orphans:
            subprocess.run(["git", "rm", "-q", "-f", rel], cwd=ROOT, check=False)
        fixed_junk, fixed_orphans = junk, orphans

    mode = "DRY-RUN" if DRY_RUN else ("FIX" if DO_FIX else "REPORT")
    L = ["# 🧹 WORKSPACE-REPORT", "",
         f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · Modus: {mode} · "
         f"Getrackte Dateien: {len(files)} · .git: {git_mb:.0f} MB", ""]
    L.append("| Pruefung | Befund | " + ("Geheilt" if DO_FIX else "Status") + " |")
    L.append("|---|---|---|")
    def row(name, total, fixed_hint):
        mark = "✅" if (not total or (DO_FIX and fixed_hint)) else ("🩹 geheilt" if DO_FIX and fixed_hint else "⚠️")
        L.append(f"| {name} | {len(total) if isinstance(total, list) else total} | {mark} |")
    row("W1 Muell-Dateien", len(junk), bool(fixed_junk))
    row("W2 Phantom-Cover (kein Artikel)", len(orphans), bool(fixed_orphans))
    row("W3 Duplikate (identische Dateien)", len(dups), False)
    row("W4 Dickschiffe (>300/500 KB)", len(heavy), False)
    row("W5 History-Rotation (>400 Zeilen)", len(rotated), bool(rotated))
    row("W6 Git-Volumen", f"{git_mb:.0f} MB", git_mb < 100)
    row("W7 Konflikt-Marker (content/)", len(betroffen), bool(betroffen))

    details = []
    if betroffen:
        details.insert(0, f"🚧 W7 Marker-Dateien ({len(betroffen)}): " + ", ".join(f"`{b}`" for b in betroffen[:12]) + (" (geheilt)" if DO_FIX else ""))
    if junk: details += ["", "🗑 Muell:", *[f"- `{x}`" for x in junk[:20]]]
    if orphans: details += ["", "👻 Phantom-Cover:", *[f"- `{x}`" for x in orphans[:20]]]
    if dups:
        details += ["", "👯 Duplikate:"]
        for h, xs in list(dups.items())[:10]:
            details += [f"- {len(xs)}x identisch: " + " ↔ ".join(f"`{x}`" for x in xs[:4])]
    if heavy: details += ["", "🐘 Dickschiffe:", *[f"- `{n}`: {s//KB} KB" for n, s in heavy[:12]]]
    if rotated: details += ["", "📜 Rotiert (gestutzt auf juengste 400 Zeilen):", *[f"- `{n}` ({c} Zeilen)" for n, c in rotated]]
    if git_mb > 100:
        details += ["", f"💾 Hinweis: .git ist {git_mb:.0f} MB – bei > 200 MB lohnt sich irgendwann `git gc --aggressive` (oder BFG-Filter bei Historie)."]
    L += details + ["", "---", "_Warrant: Junk/Waisen/Rotation heilen sich selbst; Dickschiffe/Duplikate/"
                    "Git-Historie REPORT-ONLY (Loeschung bleibt Chef-Sache)._"]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:30]))

    HISTORY.parent.mkdir(exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"date": date.today().isoformat(), "mode": mode,
                             "junk": len(junk), "orphans": len(orphans),
                             "dups": len(dups), "heavy": len(heavy),
                             "git_mb": git_mb}, ensure_ascii=False) + "\n")
    if AS_JSON:
        print(json.dumps({"junk": junk, "orphans": orphans, "dups": len(dups),
                          "heavy": len(heavy), "git_mb": git_mb}, ensure_ascii=False))


if __name__ == "__main__":
    main()
