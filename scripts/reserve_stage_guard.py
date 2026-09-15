#!/usr/bin/env python3
"""
reserve_stage_guard.py – Staging-Politik der Content-Reserve (Premium #295)

WARUM (Root-Cause 15.09.2026, Run 34949097389):
  Der Sicherungs-Schritt des nächtlichen Reserve-Laufs staggte mit `git add -A`
  ALLES, was im Arbeitsbaum lag. Die Veredelungs-Kette enthält aber korpusweite
  Heiler (Live-Engine-Kodex): Sie heilen Live-Posts, regenerieren Live-Cover und
  schreiben Manifeste. Diese Fremd-Änderungen landeten dadurch im Reserve-Commit
  und kollidierten beim Rebase mit dem parallel laufenden Deploy-/
  Auslieferungslauf -> „Rebase-Konflikt … Kein Push“ -> roter Lauf, obwohl der
  Pool gesund war. Zusätzlich verletzte es das Besitzverhältnis: Live-Content
  gehört der Engine-/Deploy-Kette, nicht dem Reservisten.

  Zwei Lagen sichern das jetzt ab:
    1. reserve_finisher.py (Isolation-Wächter): stellt jede Änderung außerhalb
       der Pool-Kandidaten bytegenau zurück bzw. legt neue Fremd-Dateien in
       Quarantäne.
    2. DIESES Skript (Staging-Politik): stagt nur Pool-Pfade, prüft jede
       gestagte Content-Datei auf die `reserve: true`-Kennzeichnung, nimmt
       Fremd-Dateien wieder aus dem Index und meldet, was liegen bleibt.
  Beide sind unabhängig voneinander – fällt eine Lage aus, greift die andere.

MODI:
  python3 scripts/reserve_stage_guard.py            # stagen + Kontrolle
  python3 scripts/reserve_stage_guard.py --dry-run  # nur melden, nichts ändern
  python3 scripts/reserve_stage_guard.py --selftest # Sabotageschutz

EXIT: immer 0 – die Staging-Politik darf den Lauf nicht rot machen; über den
      Commit entscheidet der Workflow (`git diff --cached --quiet`), über den
      Lauf-Status der harte End-Gate.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Pfade, die der Reserve-Lauf BESITZT (maschinengeneriert bzw. Pool-Inhalt).
ALLOWED_PREFIXES = ("content/posts/", "static/images/covers/")
ALLOWED_FILES = ("data/reserve-readiness.json", "data/covers_manifest.json")
STAGE_PATHS = ("content/posts", "static/images/covers",
               "data/reserve-readiness.json", "data/covers_manifest.json",
               "data/audit")

RE_RESERVE = re.compile(r"(?m)^reserve:\s*(true|yes|1)\s*$")


def git(root: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=str(root), timeout=120,
                          capture_output=True, text=True)
    return proc.stdout


def frontmatter(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    parts = text.split("---", 2)
    return parts[1] if len(parts) == 3 and parts[0] == "" else ""


def is_pool_file(path: Path) -> bool:
    """Pool-Content = Reserve-Entwurf (`reserve: true`).

    Live gewordene Reserve-Artikel tragen `reserve_published` – sie gehören
    dann der Engine-/Deploy-Kette und werden hier bewusst NICHT mehr gestagt.
    """
    return bool(RE_RESERVE.search(frontmatter(path)))


def staged_paths(root: Path) -> list:
    return [p for p in git(root, "diff", "--cached", "--name-only")
            .splitlines() if p]


def is_allowed(path: str) -> bool:
    """Pool-Pfade, Zertifikate/Manifeste und Append-only-Historien
    (data/**/*.jsonl – Audit-Gedächtnis, wird beim Rebase dedupliziert
    zusammengeführt, siehe git_sync.sh)."""
    return (path.startswith(ALLOWED_PREFIXES) or path in ALLOWED_FILES
            or (path.startswith("data/") and path.endswith(".jsonl")))


def stage(root: Path = ROOT, dry_run: bool = False) -> dict:
    """Stagt die Pool-Pfade und nimmt Fremd-Content wieder aus dem Index."""
    bericht = {"gestagt": 0, "entfernt": [], "fremd": []}
    if not dry_run:
        for target in STAGE_PATHS:
            subprocess.run(["git", "add", "-A", "--", target], cwd=str(root),
                           capture_output=True, text=True)
    staged = staged_paths(root)
    bericht["gestagt"] = len(staged)

    # Kontrolle: Jede gestagte Content-Datei muss ein Pool-Entwurf sein.
    fremd_content = []
    for path in staged:
        if not path.startswith("content/posts/"):
            continue
        full = root / path
        if full.exists() and not is_pool_file(full):
            fremd_content.append(path)
    if fremd_content and not dry_run:
        subprocess.run(["git", "restore", "--staged", *fremd_content],
                       cwd=str(root), capture_output=True, text=True)
        # Getrackte Fremd-Dateien zusätzlich bytegenau auf HEAD zurücksetzen –
        # sonst bliebe eine Live-Änderung im Arbeitsbaum liegen.
        tracked = set(git(root, "ls-files", "--", *fremd_content).splitlines())
        restore = [p for p in fremd_content if p in tracked]
        if restore:
            subprocess.run(["git", "checkout", "--", *restore],
                           cwd=str(root), capture_output=True, text=True)
        bericht["entfernt"] = fremd_content
        print("::warning::Nicht-Pool-Content wurde gestagt und wieder "
              "entfernt (Live-Content gehört der Engine-/Deploy-Kette):")
        for p in fremd_content:
            print(f"   - {p}")

    # Transparenz: Was bleibt uncommittet liegen?
    dirty = [l for l in git(root, "status", "--porcelain=v1", "-uall")
             .splitlines() if l.strip()]
    bericht["fremd"] = dirty
    if dirty:
        print(f"Hinweis: {len(dirty)} Änderung(en) bleiben bewusst "
              f"uncommittet (außerhalb des Reserve-Pools):")
        for line in dirty[:15]:
            print(f"   {line}")
    return bericht


# ---------------------------------------------------------------------------
#  Sabotage-Schutz: Staging-Politik gegen ein Wegwerf-Repo (nie Live-Repo).
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    from unittest import mock
    fehler = []
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        (repo / "content" / "posts").mkdir(parents=True)
        (repo / "data").mkdir()
        (repo / "static" / "images" / "covers").mkdir(parents=True)

        def write(rel, text):
            p = repo / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")

        def env(cmd, cwd=None, **kw):
            return subprocess.run(cmd, cwd=str(cwd), **kw)

        env(["git", "init", "-q"], cwd=repo)
        env(["git", "config", "user.email", "t@example.com"], cwd=repo)
        env(["git", "config", "user.name", "T"], cwd=repo)
        write("content/posts/2026-09-01-live/index.md",
              "---\ntitle: Live\ndate: 2026-09-01T06:00:00Z\ndraft: false\n---\nBody\n")
        write("content/posts/2026-09-15-pool/index.md",
              "---\ntitle: Pool\ndate: 2026-09-15T06:00:00Z\ndraft: true\n"
              "reserve: true\n---\nBody\n")
        write("data/reserve-readiness.json", '{"target": 1, "candidates": []}')
        env(["git", "add", "-A"], cwd=repo)
        env(["git", "commit", "-qm", "init"], cwd=repo)

        # Sabotage: ein korpusweiter Heiler „heilt“ den LIVE-Post,
        # der Reserve-Finisher veredelt den Pool-Kandidaten.
        write("content/posts/2026-09-01-live/index.md",
              "---\ntitle: Live\ndate: 2026-09-01T06:00:00Z\ndraft: false\n---\nHeilung\n")
        write("content/posts/2026-09-15-pool/index.md",
              "---\ntitle: Pool\ndate: 2026-09-15T06:00:00Z\ndraft: true\n"
              "reserve: true\n---\nVeredelt\n")
        write("data/reserve-readiness.json", '{"target": 1, "candidates": []}')

        with mock.patch("sys.stdout"):
            bericht = stage(root=repo)
        staged = staged_paths(repo)
        if "content/posts/2026-09-15-pool/index.md" not in staged:
            fehler.append(f"Pool-Kandidat wurde nicht gestagt: {staged}")
        if "content/posts/2026-09-01-live/index.md" in staged:
            fehler.append(f"LIVE-Post wurde gestagt (Vertragsbruch): {staged}")
        if bericht["entfernt"] != ["content/posts/2026-09-01-live/index.md"]:
            fehler.append(f"Fremd-Content nicht erkannt: {bericht['entfernt']}")
        # Der Live-Post muss bytegenau auf HEAD zurückgesetzt sein.
        head = env(["git", "show", "HEAD:content/posts/2026-09-01-live/index.md"],
                   cwd=repo, capture_output=True, text=True).stdout
        ist = (repo / "content/posts/2026-09-01-live/index.md").read_text(
            encoding="utf-8")
        if head != ist:
            fehler.append("Live-Post nicht bytegenau zurückgesetzt")

        # Live gewordene Reserve (reserve_published) gilt NICHT als Pool-Datei.
        write("content/posts/2026-09-02-frueher-pool/index.md",
              "---\ntitle: Ehemals Pool\ndate: 2026-09-02T06:00:00Z\n"
              "draft: false\nreserve_published: 2026-09-02\n---\nBody\n")
        env(["git", "add", "-A"], cwd=repo)
        env(["git", "commit", "-qm", "published"], cwd=repo)
        write("content/posts/2026-09-02-frueher-pool/index.md",
              "---\ntitle: Ehemals Pool\ndate: 2026-09-02T06:00:00Z\n"
              "draft: false\nreserve_published: 2026-09-02\n---\nFremd\n")
        with mock.patch("sys.stdout"):
            stage(root=repo)
        staged = staged_paths(repo)
        if "content/posts/2026-09-02-frueher-pool/index.md" in staged:
            fehler.append("Veröffentlichter Reserve-Post wurde gestagt")

    if fehler:
        print("🛑 RESERVE-STAGE-GUARD-SELFTEST FEHLGESCHLAGEN:")
        for f in fehler:
            print(f"   - {f}")
        return 2
    print("✅ Reserve-Stage-Guard-Selbsttest grün (Pool gestagt, Live-Content "
          "nicht gestagt und bytegenau zurückgesetzt).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Staging-Politik der "
                                            "Content-Reserve")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return run_selftest()
    stage(dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
