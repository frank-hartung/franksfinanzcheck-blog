#!/usr/bin/env python3
# ============================================================
#  WORKSPACE-GUARD – Frühwarnsystem + Repo-Hygiene (Profi-Level)
#
#  Auftrag (12.08.2026): „Installiere Frühwarnsystem-Automatik
#  mit sofortiger Fehleroptimierung."
#
#  ZWEI SÄULEN (vereinigt aus zwei parallelen Implementierungen):
#
#  A) SANDBOX-BUDGET-FRÜHWARNUNG (Workspace over budget):
#     misst /home/user gegen die harten Snapshot-Limits
#     (128 MB / 10.000 Dateien) und OPTIMIERT SOFORT:
#       GRÜN    < 80 MB / 6.000  → nur Status
#       GELB    ≥ 80 MB / 6.000  → Warnung + Audit-Log
#       ROT     ≥ 95 MB / 8.000  → Stufe 1: public/, __pycache__,
#                                  Caches, Audit-Retention, git gc
#       KRITISCH ≥ 115 MB / 9.500 → Stufe 2: zusätzlich /tmp-Artefakte
#                                  + Snapshot-exkludierte Ordner
#
#  B) REPO-HYGIENE (git-tracked, nur wirkliche Repo-Inhalte):
#     W1  Junk-Dateien (Thumbs.db, .DS_Store, *.pyc, __pycache__…)
#         → AUTO-LÖSCHEN (--fix)
#     W2  Phantom-Cover (Bild ohne Artikel) → AUTO-LÖSCHEN (--fix)
#     W3  Byte-idente Duplikate → REPORT (mit Billigliste-Ausnahme)
#     W4  Dickschiffe (>300 KB Bild / >500 KB Rest) → REPORT
#     W5  History-Rotation (>400 Zeilen jsonl) → AUTO-STUTZEN (--fix)
#     W6  Git-Volumen → REPORT (Hinweis gc)
#     W7  Konflikt-Marker (<<<<<<< in content/scripts/root) → AUTO-HEILEN
#
#  SABOTAGE-SCHUTZ: Selbsttest läuft VOR jeder Löschung (Exit 2 bei
#  Fehlschlag – nichts wird entfernt).
#
#  Aufruf:
#    python3 scripts/workspace_guard.py              # Report beider Säulen
#    python3 scripts/workspace_guard.py --fix        # Repo-Hygiene heilen
#    python3 scripts/workspace_guard.py --force      # Budget-Cleanup erzwingen
#    python3 scripts/workspace_guard.py --json       # JSON für Bots
#
#  Ausgabe: WORKSPACE-REPORT.md · data/workspace_guard.json ·
#           data/workspace_history.jsonl · Audit-Log
# ============================================================

import hashlib
import json
import os
import re
import sys
import glob
import shutil
import subprocess
from datetime import datetime, timezone, date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "WORKSPACE-REPORT.md"
HISTORY = ROOT / "data" / "workspace_history.jsonl"
STATE_FILE = ROOT / "data" / "workspace_guard.json"

DO_FIX = "--fix" in sys.argv
AS_JSON = "--json" in sys.argv
DRY_RUN = "--dry-run" in sys.argv
FORCE = "--force" in sys.argv

HOME = os.path.expanduser("~")
BLOG_DIR = str(ROOT)

KB = 1024
SCHWELLE_BILD = 300 * KB
SCHWELLE_SONST = 500 * KB
HIST_MAX_LINES = 400

# ---- Säule A: Schwellwerte (MB / Dateien) ----
WARN_MB, CLEAN_MB, CRIT_MB, LIMIT_MB = 80, 95, 115, 128
WARN_FILES, CLEAN_FILES, CRIT_FILES, LIMIT_FILES = 6000, 8000, 9500, 10000

EXCLUDED_DIRS = {
    ".arena", ".cache", ".mypy_cache", ".next", ".nox", ".npm", ".nuxt",
    ".output", ".parcel-cache", ".pytest_cache", ".ruff_cache", ".svelte-kit",
    ".tox", ".turbo", ".venv", ".vite", "__pycache__", "build", "coverage",
    "dist", "node_modules", "out", "target",
}

JUNK_PATTERNS = [
    r"(^|/)(\.DS_Store|Thumbs\.db|desktop\.ini)$",
    r"\.pyc$", r"(^|/)__pycache__(/|$)", r"~\$", r"\.bak$", r"\.swp$",
    r"\.orig$", r"\.tmp$", r"^(tmp|temp)/",
]
SKIP_DIRS = {".git", "themes", "node_modules", "public", "resources", ".github",
             "layouts", "archetypes"}
SAFE_HISTORY_RE = re.compile(r"data/(\w+_history|audit).*\.jsonl$")

ORPHAN_PATTERN = re.compile(
    r"static/images/covers/(?:\d+/)?(?:avif/|webp/)?([\w-]+)\.(jpg|webp|avif)$")

DUP_BILLIG = [
    ("static/go/fluege/index.html", "static/go/reisen/index.html"),
    ("static/go/girokonto/index.html", "static/go/tagesgeld/index.html"),
    ("scripts/indexnow_key.txt", "static/6t77zzoan6sl5i4b9jwcvx073202rgm9.txt"),
]

MARKER_START = re.compile(r"^<<<<<<<[^\n]*$", re.M)
MARKER_MID = re.compile(r"^=======\s*$", re.M)
MARKER_END = re.compile(r"^>>>>>>>[^\n]*$", re.M)


# ================================================================
#  SÄULE A – SANDBOX-BUDGET
# ================================================================

def dir_size_mb(path):
    try:
        out = subprocess.run(["du", "-sm", path], capture_output=True,
                             text=True, timeout=60).stdout
        return int(out.split("\t")[0])
    except Exception:
        return 0


def count_files(path):
    try:
        out = subprocess.run(["find", path, "-type", "f"], capture_output=True,
                             text=True, timeout=120).stdout
        return len(out.splitlines())
    except Exception:
        return 0


def cleanup_stage1():
    """Sichere, sofortige Optimierung. Rückgabe: Liste der Aktionen."""
    actions = []
    pub = os.path.join(BLOG_DIR, "public")
    if os.path.isdir(pub):
        mb = dir_size_mb(pub)
        if not DRY_RUN:
            shutil.rmtree(pub, ignore_errors=True)
        actions.append(f"public/ gelöscht (−{mb} MB)")

    n = 0
    for root, dirs, files in os.walk(BLOG_DIR):
        dirs[:] = [d for d in dirs if d not in ("static", "themes", ".git")]
        if "__pycache__" in dirs:
            if not DRY_RUN:
                shutil.rmtree(os.path.join(root, "__pycache__"), ignore_errors=True)
            n += 1
    for pyc in glob.glob(os.path.join(BLOG_DIR, "**", "*.pyc"), recursive=True):
        if not DRY_RUN:
            try:
                os.remove(pyc)
                n += 1
            except OSError:
                pass
    if n:
        actions.append(f"{n} Python-Cache-Einträge gelöscht")

    for c in (".pytest_cache", ".mypy_cache", ".ruff_cache", ".cache"):
        p = os.path.join(BLOG_DIR, c)
        if os.path.isdir(p):
            if not DRY_RUN:
                shutil.rmtree(p, ignore_errors=True)
            actions.append(f"{c}/ gelöscht")

    try:
        if not DRY_RUN:
            subprocess.run([sys.executable,
                            os.path.join(BLOG_DIR, "scripts", "audit_log.py"),
                            "--cleanup"], cwd=BLOG_DIR, capture_output=True,
                           timeout=60)
        actions.append("Audit-Retention angewendet")
    except Exception:
        pass

    git_dir = os.path.join(BLOG_DIR, ".git")
    if os.path.isdir(git_dir) and dir_size_mb(git_dir) > 25:
        if not DRY_RUN:
            subprocess.run(["git", "gc", "--prune=now", "--aggressive"],
                           cwd=BLOG_DIR, capture_output=True, timeout=300)
        actions.append("git gc --aggressive")
    return actions


def cleanup_stage2():
    actions = []
    for pat in ("/tmp/hugo.tar.gz", "/tmp/hugo", "/tmp/serve*",
                "/tmp/chrome-headless-shell*", "/tmp/oc*.png", "/tmp/*.html"):
        for f in glob.glob(pat):
            try:
                if not DRY_RUN:
                    if os.path.isdir(f):
                        shutil.rmtree(f, ignore_errors=True)
                    else:
                        os.remove(f)
                actions.append(f"{f} gelöscht")
            except OSError:
                pass
    for d in sorted(os.listdir(HOME)):
        p = os.path.join(HOME, d)
        if os.path.isdir(p) and d in EXCLUDED_DIRS:
            mb = dir_size_mb(p)
            if not DRY_RUN:
                shutil.rmtree(p, ignore_errors=True)
            actions.append(f"{d}/ gelöscht (−{mb} MB)")
    return actions


def budget_check():
    """Säule A: misst /home/user, optimiert sofort. Rückgabe Dict."""
    mb = dir_size_mb(HOME)
    files = count_files(HOME)
    actions = []

    if mb >= CRIT_MB or files >= CRIT_FILES:
        level = "kritisch"
        actions += cleanup_stage2()
        actions += cleanup_stage1()
    elif mb >= CLEAN_MB or files >= CLEAN_FILES or FORCE:
        level = "rot" if (mb >= CLEAN_MB or files >= CLEAN_FILES) else "erzwungen"
        actions += cleanup_stage1()
    elif mb >= WARN_MB or files >= WARN_FILES:
        level = "gelb"
    else:
        level = "gruen"

    if actions:
        mb = dir_size_mb(HOME)
        files = count_files(HOME)

    state = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "size_mb": mb, "files": files,
        "limit_mb": LIMIT_MB, "limit_files": LIMIT_FILES,
        "level": level, "actions": actions,
    }
    try:
        STATE_FILE.parent.mkdir(exist_ok=True)
        json.dump(state, open(STATE_FILE, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    except Exception:
        pass
    return state


# ================================================================
#  SÄULE B – REPO-HYGIENE
# ================================================================

def iter_tracked_files():
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


def is_junk(rel: str) -> bool:
    return any(re.search(rx, rel) for rx in JUNK_PATTERNS)


def find_junk(files: list) -> list:
    return [str(p.relative_to(ROOT)) for p in files
            if is_junk(str(p.relative_to(ROOT)))]


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


def find_duplicates(files: list) -> dict:
    by_hash = {}
    for p in files:
        if p.stat().st_size > 5 * KB * 1024:
            continue
        h = hash_file(p)
        by_hash.setdefault(h, []).append(str(p.relative_to(ROOT)))
    return {h: xs for h, xs in by_hash.items() if len(xs) > 1 and not _dup_billig(xs)}


def _dup_billig(xs: list) -> bool:
    return any(all(b in xs for b in pair) for pair in DUP_BILLIG)


def find_heavy(files: list) -> list:
    out = []
    for p in files:
        size = p.stat().st_size
        lim = (SCHWELLE_BILD if p.suffix.lower() in
               (".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif")
               else SCHWELLE_SONST)
        if size > lim:
            out.append((str(p.relative_to(ROOT)), size))
    return sorted(out, key=lambda x: -x[1])


def rotate_histories() -> list:
    rotated = []
    for p in (ROOT / "data").rglob("*.jsonl"):
        rel = str(p.relative_to(ROOT))
        if not SAFE_HISTORY_RE.search(rel) and "_history" not in p.name \
                and p.name != "audit_log.jsonl":
            continue
        text = p.read_text(encoding="utf-8")
        lines = text.splitlines()
        if len(lines) > HIST_MAX_LINES:
            if DO_FIX and not DRY_RUN:
                p.write_text("\n".join(lines[-HIST_MAX_LINES:]) + "\n",
                             encoding="utf-8")
            rotated.append((rel, len(lines)))
    return rotated


def sweep_markers(do_fix: bool) -> list:
    betroffen = []
    pfade = (list((ROOT / "content").rglob("*.md"))
             + list((ROOT / "scripts").glob("*.py"))
             + list(ROOT.glob("*.md")))
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
    a, b = m.group(1), m.group(2)
    la = [l for l in a.split("\n") if l.strip()]
    lb = [l for l in b.split("\n") if l.strip()]
    if not lb:
        return a
    if not la:
        return b
    return a if len(la) >= len(lb) else b


def git_size_mb() -> float:
    """Größe des .git in MB (fixiert: war in früherer Version als toter
    Code in _merge_wahl verloren gegangen → NameError zur Laufzeit)."""
    try:
        out = subprocess.run(["du", "-sm", ".git"], cwd=ROOT,
                             capture_output=True, text=True, timeout=20).stdout
        return float(out.split()[0])
    except Exception:
        return 0.0


# ---- Sabotage-Schutz: Selbsttest VOR jeder Löschung ----
SELFTEST = [
    ("junk-bak",     is_junk,  ("layouts/_partials/x.bak",), True),
    ("junk-swp",     is_junk,  ("assets/css/core.css.swp",), True),
    ("junk-pycache", is_junk,  ("scripts/__pycache__/lektor.pyc",), True),
    ("sauber",       is_junk,  ("scripts/lektor_guard.py",), False),
    ("sauber-md",    is_junk,  ("WORKSPACE-REPORT.md",), False),
    ("billig-go",    _dup_billig, (["static/go/fluege/index.html",
                                    "static/go/reisen/index.html"],), True),
    ("billig-key",   _dup_billig, (["scripts/indexnow_key.txt",
                                    "static/6t77zzoan6sl5i4b9jwcvx073202rgm9.txt"],), True),
    ("no-dup",       _dup_billig, (["x/a.md", "x/b.md"],), False),
    ("orphan",       lambda a: bool(ORPHAN_PATTERN.match(a)),
     ("static/images/covers/denne.jpg",), True),
    ("no-orphan",    lambda a: bool(ORPHAN_PATTERN.match(a)),
     ("content/posts/x/index.md",), False),
    ("marker-start", lambda t: bool(MARKER_START.search(t)),
     ("<<<<<<< HEAD\nneu\n=======\nalt\n>>>>>>> x\n",), True),
    ("marker-clean", lambda t: bool(MARKER_START.search(t)),
     ("## Alles sauber\n\nKein Bruch.\n",), False),
    ("git-mb",       git_size_mb, (), float),
]


def run_selftest() -> list[str]:
    fehler = []
    for i, (zweck, fn, args, want) in enumerate(SELFTEST, 1):
        try:
            got = fn(*args)
        except Exception as e:
            fehler.append(f"  Fall {i} ({zweck}): Ausnahme {type(e).__name__}")
            continue
        if want is float:
            if not isinstance(got, float):
                fehler.append(f"  Fall {i} ({zweck}): erwartet float, bekam {type(got).__name__}")
        elif got != want:
            fehler.append(f"  Fall {i} ({zweck}): erwartet {want}, bekam {got}")
    return fehler


def log_audit(event, details):
    try:
        sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
        from audit_log import log_event
        log_event(module="workspace_guard", action=event,
                  input={}, output=details, status="ok")
    except Exception:
        pass


def main() -> None:
    # SABOTAGE-SCHUTZ zuerst: Wächter prüft sich selbst, BEVOR er löscht.
    stf = run_selftest()
    if stf:
        print("🛑 WORKSPACE-SELBSTTEST FEHLGESCHLAGEN – Sabotage verhindert.")
        print("   Kein Feststoff wird entfernt. Bitte workspace_guard.py prüfen:")
        print("\n".join(stf))
        sys.exit(2)
    print(f"✅ Workspace-Selbsttest: {len(SELFTEST)} Fälle grün.")

    # ---- Säule A: Budget-Frühwarnung mit sofortiger Optimierung ----
    budget = budget_check()
    print(f"\n📦 SANDBOX-BUDGET: {budget['size_mb']} MB / {budget['files']} Dateien "
          f"(Limit {LIMIT_MB} MB / {LIMIT_FILES}) – Level: {budget['level'].upper()}")
    for a in budget["actions"]:
        print(f"   ✅ {a}")

    # ---- Säule B: Repo-Hygiene ----
    files = iter_tracked_files()
    slugs = existing_slugs()
    junk = find_junk(files)
    orphans = find_orphan_covers(files, slugs)
    dups = find_duplicates(files)
    heavy = find_heavy(files)
    rotated = rotate_histories()
    betroffen = sweep_markers(DO_FIX)
    git_mb = git_size_mb()

    fixed_junk, fixed_orphans = [], []
    if DO_FIX and not DRY_RUN:
        for rel in junk + orphans:
            subprocess.run(["git", "rm", "-q", "-f", rel], cwd=ROOT, check=False)
        fixed_junk, fixed_orphans = junk, orphans

    mode = "DRY-RUN" if DRY_RUN else ("FIX" if DO_FIX else "REPORT")
    L = ["# 🧹 WORKSPACE-REPORT", "",
         f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · Modus: {mode} · "
         f"Getrackte Dateien: {len(files)} · .git: {git_mb:.0f} MB", "",
         f"**Budget (Säule A):** {budget['size_mb']} MB / {budget['files']} Dateien "
         f"– Level {budget['level'].upper()}", ""]
    L.append("| Prüfung | Befund | " + ("Geheilt" if DO_FIX else "Status") + " |")
    L.append("|---|---|---|")

    def row(name, total, fixed_hint):
        mark = ("✅" if (not total or (DO_FIX and fixed_hint))
                else ("🩹 geheilt" if DO_FIX and fixed_hint else "⚠️"))
        L.append(f"| {name} | {len(total) if isinstance(total, list) else total} | {mark} |")

    row("W1 Müll-Dateien", len(junk), bool(fixed_junk))
    row("W2 Phantom-Cover (kein Artikel)", len(orphans), bool(fixed_orphans))
    row("W3 Duplikate (identische Dateien)", len(dups), False)
    row("W4 Dickschiffe (>300/500 KB)", len(heavy), False)
    row("W5 History-Rotation (>400 Zeilen)", len(rotated), bool(rotated))
    row("W6 Git-Volumen", f"{git_mb:.0f} MB", git_mb < 100)
    row("W7 Konflikt-Marker (content/)", len(betroffen), bool(betroffen))

    details = []
    if budget["actions"]:
        details += ["", "💾 Budget-Optimierung (Sofort):", *[f"- {a}" for a in budget["actions"]]]
    if betroffen:
        details.insert(0, f"🚧 W7 Marker-Dateien ({len(betroffen)}): " +
                       ", ".join(f"`{b}`" for b in betroffen[:12]) +
                       (" (geheilt)" if DO_FIX else ""))
    if junk:
        details += ["", "🗑 Müll:", *[f"- `{x}`" for x in junk[:20]]]
    if orphans:
        details += ["", "👻 Phantom-Cover:", *[f"- `{x}`" for x in orphans[:20]]]
    if dups:
        details += ["", "👯 Duplikate:"]
        for h, xs in list(dups.items())[:10]:
            details += [f"- {len(xs)}x identisch: " + " ↔ ".join(f"`{x}`" for x in xs[:4])]
    if heavy:
        details += ["", "🐘 Dickschiffe:", *[f"- `{n}`: {s//KB} KB" for n, s in heavy[:12]]]
    if rotated:
        details += ["", "📜 Rotiert (gestutzt auf jüngste 400 Zeilen):",
                    *[f"- `{n}` ({c} Zeilen)" for n, c in rotated]]
    if git_mb > 100:
        details += ["", f"💾 Hinweis: .git ist {git_mb:.0f} MB – bei > 200 MB lohnt "
                        "sich `git gc --aggressive` (oder BFG-Filter bei Historie)."]
    L += details + ["", "---",
                    "_Warrant: Junk/Waisen/Rotation/Budget heilen sich selbst; "
                    "Dickschiffe/Duplikate/Git-Historie REPORT-ONLY._"]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:24]))

    HISTORY.parent.mkdir(exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"date": date.today().isoformat(), "mode": mode,
                             "junk": len(junk), "orphans": len(orphans),
                             "dups": len(dups), "heavy": len(heavy),
                             "git_mb": git_mb,
                             "budget_mb": budget["size_mb"],
                             "budget_level": budget["level"]},
                            ensure_ascii=False) + "\n")

    if budget["level"] in ("gelb", "rot", "kritisch") or budget["actions"]:
        log_audit("guard", {k: budget[k] for k in
                            ("level", "size_mb", "files", "actions")})

    if AS_JSON:
        print(json.dumps({"budget": budget, "junk": junk, "orphans": orphans,
                          "dups": len(dups), "heavy": len(heavy),
                          "git_mb": git_mb, "markers": len(betroffen)},
                         ensure_ascii=False))


if __name__ == "__main__":
    main()
