#!/usr/bin/env python3
"""report_hygiene.py – Root-Aufräumen, ohne die CI-Dashboards zu zerstören.

WARUM (12.09.2026, Auftrag „REPORT-Dateien aus dem Repo nehmen"):
Im Root liegen ~70 versionierte `*-REPORT.md` / `*-STATUS.md`. Pauschal aus dem
Git nehmen wäre fatal – es gibt vier völlig verschiedene Sorten, und nur eine
davon ist wirklicher Müll:

  1. ci-dashboard – ein Workflow staged die Datei explizit (`git add …`) oder ein
     Skript / eine Workflow-Zeile liest sie (z. B. governance_contract C7 gegen
     CWV-REPORT.md). Bewusst so gewollt: Frank liest diese Dateien in der
     GitHub-Oberfläche, und ein `git add` auf eine ignorierte, UNVERSIONIERTE
     Datei bricht den Lauf hart ab (siehe frankautoops-report.yml). Bleibt im Root.
  2. doku         – von README/docs referenziert (z. B. VORLESEN-HIGHEND-REPORT.md).
     Steht falsch im Root, hängt aber an Referenzen: Verschieben ist opt-in
     (`--move-doku`), weil Links aus Issues auf die Root-Pfade zeigen können.
  3. maschinen-muell – ein Skript/Workflow SCHREIBT die Datei, aber niemand liest
     oder staged sie: reproduzierbarer Nebenbefund, im Repo nur History-Churn
     → `git rm --cached`. Die Datei bleibt auf der Platte; `/*-REPORT.md` und
     `/*-STATUS.md` in .gitignore verhindern den Rückfall.
  4. verwaist     – kein Schreiber, kein Leser, keine Referenz: meist ein manuell
     geschriebener Projektbericht. Der darf NICHT ent-versioniert werden (kein
     Skript brächte ihn zurück) → nach docs/ verschoben, Inhalt bleibt erhalten.

`--check` ist die dauerhafte Regel: maschinen-muell und verwaiste Berichte im Root
sind ein Fehler. Damit sammelt sich nichts wieder an, und die erlaubten Sorten
(Dashboard, referenzierte Doku) bleiben unangetastet.

SPERRE (dokumentierter Unfall vom 12.09.2026, damit er nie wieder passiert): Der
erste Entwurf löste Klassen gegen das Temp-Verzeichnis auf, ließ aber `_git()` und
die Workflow-/Skript-Korpora auf dem Modul-Root laufen – der Selbsttest
ent-versionierte daraufhin 68 echte Dateien und verschob eine per `git mv`. Seitdem
wird `root` durch JEDE Hilfsfunktion durchgereicht, und jede schreibende
Git-Operation ist an die Worktree-Sperre gebunden: sie erlaubt Schreiben nur, wenn
`git rev-parse --show-toplevel` exakt das übergebene root ist.

Nutzung:
    python3 scripts/report_hygiene.py                       # Klassifikation
    python3 scripts/report_hygiene.py --check               # CI-Modus (Exit 1)
    python3 scripts/report_hygiene.py --apply               # Müll + Verwaistes heilen
    python3 scripts/report_hygiene.py --apply --dry-run     # zeigen, nicht tun
    python3 scripts/report_hygiene.py --apply --move-doku   # + referenzierte Doku
    python3 scripts/report_hygiene.py --selftest

Exit: 0 = Ordnung · 1 = Funde (--check) · 2 = Ausführungsfehler/Sperre
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import subprocess
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = "docs"
ROOT_REPORT_RE = re.compile(r"^[^/]+-(?:REPORT|STATUS)\.md$")
# Dateiname mit Endung, Großbuchstaben-Konvention der Reports; bewusst ohne
# Quote-Klassen drumherum – die umgebenden Zeichen sind im Suchfenster egal.
FILE_LITERAL_RE = re.compile(r"([A-Z][A-Z0-9_\-]{3,}[.](?:md|json|jsonl|csv))")
# Nur echte Schreibsignale. Ein zu weites Muster (z. B. „REPORT" oder „open(")
# würde auch reine Leser als Schreiber melden – und ein als „maschinen-muell"
# fehlklassifizierter von-Hand-geschriebener Bericht würde ent-versioniert, also
# aus dem Repo verschwinden. Lieber zu eng: dann bleibt die Datei liegen.
WRITE_SIGNALS = ("> ", "tee ", "write_text", "--out", "out_path", "f.write",
                 ', "w")', ", 'w')", "mode=\"w\"")
# Lese-Signale. WICHTIG: das blanke Zitat eines Report-Namens ist noch kein Leser –
# derselbe String steht auch im Schreibaufruf. Ohne diese Unterscheidung wären alle
# von den Wachen geschriebenen Reports „gelesen", die Müll-Kategorie leer und die
# --check-Regel taub wäre. Ein Literal mit Schreibsignal in der Nähe zählt als Leser NUR,
# wenn es KEIN Schreibsignal hat.
READ_SIGNALS = ("open(", ".read()", "readFile", "os.path.isfile", "exists",
                "cat ", "test -f", "read_text", "grep")


# ----------------------------------------------------------------------- Git-Zugriff
def git(*args: str, root: str) -> str:
    """Alle Git-Aufrufe hier, mit ausdrücklichem root (kein Modul-Default)."""
    try:
        r = subprocess.run(["git", "-C", root, *args], capture_output=True,
                           text=True, timeout=120)
        return r.stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def assert_worktree(root: str) -> str | None:
    """Sperre: schreiben darf nur, wer selbst der Worktree-Root ist."""
    top = git("rev-parse", "--show-toplevel", root=root).strip()
    if not top:
        return f"{root}: kein Git-Worktree gefunden"
    if os.path.realpath(top) != os.path.realpath(root):
        return (f"Sperre: {root} liegt im Worktree von {top} – schreibende "
                "Git-Befehle würden das Eltern-Repo ändern")
    return None


# ------------------------------------------------------------------ Bestandsaufnahme
def tracked_root_reports(root: str) -> list[str]:
    return sorted(f for f in git("ls-files", root=root).splitlines()
                  if ROOT_REPORT_RE.match(f))


def _scan_corpus(root: str) -> list[str]:
    files = (sorted(glob.glob(os.path.join(root, "scripts", "*.py")))
             + sorted(glob.glob(os.path.join(root, "scripts", "tests", "*.py")))
             + sorted(glob.glob(os.path.join(root, "scripts", "*.sh")))
             + sorted(glob.glob(os.path.join(root, "scripts", "*.mjs")))
             + sorted(glob.glob(os.path.join(root, ".github", "workflows", "*.yml"))))
    texts = []
    for path in files:
        try:
            texts.append(open(path, encoding="utf-8", errors="ignore").read())
        except OSError:
            continue
    return texts


def workflow_staged(root: str) -> set[str]:
    """Markdown-Dateinamen, die ein Workflow in einem `git add` nennt.

    Mehrzeilige `git add a \\` / `  b` werden zu einem Block zusammengezogen:
    die Report-Namen stehen fast immer in den Fortsetzungszeilen, ein
    zeilenweiser Blick würde genau die verlieren.
    """
    blob: list[str] = []
    for text in _scan_corpus(root):
        for m in re.finditer(r"git add([^\n]*(?:\\\n[^\n]*)*)", text):
            blob.append(m.group(1))
    joined = re.sub(r"\\\s*\n\s*", " ", " ".join(blob))
    return {t.strip("`'\"") for t in joined.split()
            if t.strip("`'\"").endswith(".md")}


def script_readers(root: str) -> set[str]:
    """Namen, die ein Skript/Workflow LIEST (nicht bloß erwähnt).

    Ein zitiertes `\"LAYOUT-REPORT.md\"` steht genauso im Schreibaufruf – wer das
    für einen Leser hält, bekommt eine Wache, die niemals Müll meldet. Deshalb:
    Lese-Signal required, Schreib-Signal schließt aus (writers() übernimmt die).
    """
    names: set[str] = set()
    for text in _scan_corpus(root):
        for m in re.finditer(r"""["']([A-Z][A-Z0-9_\-]{3,}\.md)["']""", text):
            window = text[max(0, m.start() - 420):m.end() + 420]
            if any(sig in window for sig in WRITE_SIGNALS):
                continue
            if any(sig in window for sig in READ_SIGNALS):
                names.add(m.group(1))
    return names


def writers(root: str) -> set[str]:
    """Reports, die im Umkreis von 140 Zeichen ein Schreibsignal haben.

    Entscheidend nur für die Frage: wiederkaufbar (darf aus dem Index) oder von
    Hand geschrieben (darf das nicht). Bewusst Klartext-Signale statt Regex-
    Akrobatik – ein gequetschter Escape-Regex in einem Shell-Heredoy ist genau
    die Fehlerklasse, die dieses Skript vermeiden will.
    """
    out: set[str] = set()
    for text in _scan_corpus(root):
        for m in FILE_LITERAL_RE.finditer(text):
            name = m.group(1)
            if not name.endswith(".md"):
                continue
            window = text[max(0, m.start() - 420):m.end() + 420]
            if any(sig in window for sig in WRITE_SIGNALS):
                out.add(name)
    return out


def markdown_files(root: str) -> list[str]:
    return ([os.path.join(root, "README.md")]
            + sorted(glob.glob(os.path.join(root, "docs", "*.md")))
            + sorted(glob.glob(os.path.join(root, "*.md"))))


def doc_referenced(name: str, root: str) -> list[str]:
    hits = []
    for path in markdown_files(root):
        if os.path.basename(path) == name:
            continue
        try:
            text = open(path, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        if name in text:
            hits.append(os.path.relpath(path, root))
    return hits


# ------------------------------------------------------------------------ Klassen
def classify(root: str) -> dict[str, list[tuple[str, str]]]:
    staged = workflow_staged(root)
    read = script_readers(root)
    made = writers(root)
    buckets: dict[str, list[tuple[str, str]]] = {"ci-dashboard": [], "doku": [],
                                                  "maschinen-muell": [], "verwaist": []}
    for name in tracked_root_reports(root):
        why = []
        if name in staged:
            why.append("Workflow staged sie")
        if name in read:
            why.append("Skript/Workflow liest sie")
        if why:
            buckets["ci-dashboard"].append((name, " + ".join(why)))
            continue
        refs = doc_referenced(name, root)
        if refs:
            buckets["doku"].append((name, "referenziert in " + ", ".join(refs[:3])))
            continue
        # Keine Referenz, kein Leser: entweder Nachbefund einer Wache (weg aus dem
        # Index – er wird bei jedem Lauf neu geschrieben) oder ein Handtext
        # (in docs/ – der Inhalt ist sonst verloren).
        if name in made or looks_generated(os.path.join(root, name)):
            buckets["maschinen-muell"].append(
                (name, "generierter Nachbefund, den niemand liest"))
        else:
            buckets["verwaist"].append(
                (name, "kein Schreiber, kein Leser, keine Referenz"))
    return buckets


def check(buckets: dict) -> list[str]:
    """CI-Regel: Dashboard und referenzierte Doku sind erlaubt, der Rest nicht."""
    problems = [f"{n}: {w} → python3 scripts/report_hygiene.py --apply"
                for n, w in buckets["maschinen-muell"]]
    problems += [f"{n}: {w} → gehört in docs/: python3 scripts/report_hygiene.py --apply"
                 for n, w in buckets["verwaist"]]
    return problems


# -------------------------------------------------------------------------- Heilung
def looks_generated(path: str) -> bool:
    """Maschinen-Header erkennen: diese Reports schreiben `**Stand:** … UTC`.

    Warum das entscheidet: ent-versionieren darf nur, was ein Skript jederzeit
    zurückbringt. Die Repo-Konvention trennt das sauber – generierte Reports
    tragen den Zeitstempel-Header, von Hand geschriebene Projektberichte
    (`**Datum:**`, Issue-Schreibweise) nicht. Für die gilt: verschieben statt
    ent-versionieren, sonst wäre der Text weg.
    """
    try:
        head = "".join(open(path, encoding="utf-8", errors="ignore").readlines()[:6])
    except OSError:
        return False
    return bool(re.search(r"\*\*Stand:\*\*|erzeugt|Erzeugt|\bModus:\b|\bReport\b.*\bStand\b", head))


def untrack(name: str, root: str) -> bool:
    return name in git("rm", "--cached", "--", name, root=root)


def move_to_docs(name: str, root: str) -> bool:
    if os.path.exists(os.path.join(root, DOCS_DIR, name)):
        return False
    git("mv", name, f"{DOCS_DIR}/{name}", root=root)
    if os.path.exists(os.path.join(root, name)) or \
            not os.path.exists(os.path.join(root, DOCS_DIR, name)):
        return False
    for path in markdown_files(root):
        try:
            text = open(path, encoding="utf-8").read()
        except (OSError, UnicodeDecodeError):
            continue
        new = re.sub(r"\]\((?:\./)?" + re.escape(name) + r"\)",
                     "](" + DOCS_DIR + "/" + name + ")", text)
        if new != text:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)
    return True


def apply_fixes(buckets: dict, root: str, move_doku: bool, dry: bool) -> tuple[int, int]:
    blocked = assert_worktree(root)
    if blocked:
        print(f"🛑 {blocked}")
        return 0, 0
    moved = untracked = 0
    todo = list(buckets["verwaist"])
    if move_doku:
        todo += list(buckets["doku"])
    elif buckets["doku"]:
        print(f"  ℹ {len(buckets['doku'])} referenzierte Doku-Dateien bleiben im Root "
              "(Verschiebung nur mit --apply --move-doku)")
    for name, _why in todo:
        if dry:
            print(f"  würde verschieben: {name} → {DOCS_DIR}/{name}")
            continue
        if move_to_docs(name, root):
            print(f"  ✓ nach {DOCS_DIR}/ verschoben: {name}")
            moved += 1
    for name, _why in buckets["maschinen-muell"]:
        if dry:
            print(f"  würde ent-versionieren: {name} (bleibt auf der Platte)")
            continue
        if untrack(name, root):
            print(f"  ✓ aus dem Index genommen: {name}")
            untracked += 1
    return moved, untracked


# ------------------------------------------------------------------------ Selbsttest
def _selftest() -> int:
    import shutil
    import tempfile

    errs: list[str] = []
    tmp = tempfile.mkdtemp(prefix="report-hygiene-")
    try:
        os.makedirs(os.path.join(tmp, ".github", "workflows"), exist_ok=True)
        os.makedirs(os.path.join(tmp, "scripts"), exist_ok=True)
        os.makedirs(os.path.join(tmp, "docs"), exist_ok=True)
        for name in ("DASH-REPORT.md", "VORLESEN-HIGHEND-REPORT.md",
                     "VERALTET-REPORT.md", "HANDNOTIZ-REPORT.md"):
            with open(os.path.join(tmp, name), "w", encoding="utf-8") as f:
                # Zwei Konventionen, die die Wache unterscheiden muss: generierte
                # Reports schreiben „**Stand:**", von Hand getippte „**Datum:**".
                header = "**Datum:** Test" if name == "HANDNOTIZ-REPORT.md" else "**Stand:** Test"
                f.write(f"# {name}\n\n{header}\n")
        with open(os.path.join(tmp, "docs", "REFERENZ.md"), "w", encoding="utf-8") as f:
            f.write("[Vorlesen-Kurzfassung](VORLESEN-HIGHEND-REPORT.md)\n")
        # Fortsetzungszeile – der Klassiker, den ein zeilenweiser Parser verliert
        with open(os.path.join(tmp, ".github", "workflows", "x.yml"), "w",
                  encoding="utf-8") as f:
            f.write("      - run: |\n          git add DASH-REPORT.md \\\n"
                    "            data/x.jsonl\n")
        with open(os.path.join(tmp, "scripts", "reader.py"), "w", encoding="utf-8") as f:
            f.write("data = open(\"DASH-REPORT.md\").read()\n")
        with open(os.path.join(tmp, "scripts", "writer.py"), "w", encoding="utf-8") as f:
            f.write('with open("VERALTET-REPORT.md", "w") as fh:\n    fh.write(out)\n')
        for cmd in (["init", "-q"], ["add", "-A"],
                    ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "i"]):
            r = subprocess.run(["git", "-C", tmp, *cmd], capture_output=True,
                               text=True, timeout=120)
            if r.returncode:
                raise RuntimeError(f"git {cmd[0]}: {r.stderr[:140]}")

        buckets = classify(tmp)
        names = {k: [n for n, _ in v] for k, v in buckets.items()}
        if "DASH-REPORT.md" not in names["ci-dashboard"]:
            errs.append("CI-Dashboard über Fortsetzungszeile verkannt")
        if "VORLESEN-HIGHEND-REPORT.md" not in names["doku"]:
            errs.append("Doku (nur in docs/ referenziert) nicht erkannt")
        if "VERALTET-REPORT.md" not in names["maschinen-muell"]:
            errs.append("Maschinen-Müll nicht erkannt (Schreiber: scripts/writer.py)")
        if "HANDNOTIZ-REPORT.md" not in names["verwaist"]:
            errs.append("Von Hand geschriebener Bericht nicht als verwaist erkannt")
        probs = check(buckets)
        if not any("VERALTET-REPORT.md" in m for m in probs):
            errs.append("--check benennt den Maschinen-Müll nicht")
        if not any("HANDNOTIZ-REPORT.md" in m for m in probs):
            errs.append("--check benennt den verwaisten Bericht nicht")

        # 2) Sperre: aus einem Unterordner darf das Eltern-Repo nicht geändert werden
        if assert_worktree(os.path.join(tmp, "docs")) is None:
            errs.append("Worktree-Sperre greift nicht bei Unterordner als root")

        # 3) Heilung: Verwaistes bleibt versioniert (nur verschoben), Müll raus
        moved, untracked = apply_fixes(buckets, tmp, move_doku=False, dry=False)
        if moved != 1 or untracked != 1:
            errs.append(f"apply: {moved} verschoben / {untracked} ent-versioniert "
                        "(erwartet 1/1)")
        if not os.path.exists(os.path.join(tmp, "VERALTET-REPORT.md")):
            errs.append("Maschinen-Müll von der Platte gelöscht – darf nicht sein")
        listed = git("ls-files", root=tmp).split()
        if "VERALTET-REPORT.md" in listed:
            errs.append("Maschinen-Müll weiterhin im Index")
        if "HANDNOTIZ-REPORT.md" in listed:
            errs.append("Verwaister Bericht liegt noch im Root statt in docs/")
        if "docs/HANDNOTIZ-REPORT.md" not in listed:
            errs.append("Verwaister Bericht nicht in docs/ versioniert – Inhalt wäre weg")

        # 4) Idempotenz + Opt-in für referenzierte Doku
        again = classify(tmp)
        if again["maschinen-muell"] or again["verwaist"]:
            errs.append("Zweiter Lauf meldet weiter Root-Müll")
        moved2, _ = apply_fixes(again, tmp, move_doku=True, dry=False)
        if moved2 != 1:
            errs.append(f"--move-doku verschob {moved2} (erwartet 1)")
        if not os.path.exists(os.path.join(tmp, "docs", "VORLESEN-HIGHEND-REPORT.md")):
            errs.append("Referenzierte Doku liegt nicht in docs/")
        ref = open(os.path.join(tmp, "docs", "REFERENZ.md"), encoding="utf-8").read()
        if "docs/VORLESEN-HIGHEND-REPORT.md" not in ref:
            errs.append("Referenz nicht mitgezogen")
    except Exception as exc:  # noqa: BLE001
        errs.append(f"Ausführung: {exc.__class__.__name__}: {exc}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if errs:
        print("🛑 report_hygiene-Selbsttest FEHLGESCHLAGEN:")
        for e in errs:
            print("  -", e)
        return 2
    print("✅ Report-Hygiene-Selbsttest: 4 Fälle grün (Klassifikation, Sperre, "
          "Heilung, Idempotenz).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Report-Hygiene im Root")
    ap.add_argument("--root", default=BLOG_DIR)
    ap.add_argument("--check", action="store_true", help="CI-Modus: Exit 1 bei Müll")
    ap.add_argument("--apply", action="store_true",
                    help="verwaiste Berichte nach docs/, Maschinen-Muell aus dem Index")
    ap.add_argument("--move-doku", action="store_true",
                    help="zusaetzlich referenzierte Doku-Dateien nach docs/ verschieben")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()

    root = os.path.realpath(args.root)
    buckets = classify(root)
    if args.json:
        import json
        print(json.dumps({"buckets": {k: [n for n, _ in v] for k, v in buckets.items()},
                          "problems": check(buckets)}, ensure_ascii=False, indent=2))
        return 1 if (args.check and check(buckets)) else 0
    if not args.check and not args.apply:
        total = sum(len(v) for v in buckets.values())
        print(f"Report-Hygiene: {total} versionierte Reports/Status-Dateien im Root "
              f"({os.path.basename(root)})")
        for key in ("ci-dashboard", "doku", "maschinen-muell", "verwaist"):
            print(f"\n### {key}: {len(buckets[key])}")
            for name, why in buckets[key]:
                print(f"  · {name}  ← {why}")

    if args.apply:
        print("\n## Anwenden" + (" (Dry-Run)" if args.dry_run else ""))
        moved, untracked = apply_fixes(buckets, root, args.move_doku, args.dry_run)
        print(f"→ {moved} nach {DOCS_DIR}/ verschoben, {untracked} ent-versioniert "
              "(Dateien bleiben auf der Platte)")
        return 0

    if args.check:
        problems = check(buckets)
        if problems:
            print("\n⚠️ Root-Müll (kein Dashboard, keine referenzierte Doku):")
            for p in problems:
                print("  ❌", p)
            return 1
        print("\n✅ Root sortenrein: jede versionierte Report-/Status-Datei ist "
              "CI-Dashboard oder dokumentierte Doku.")
        return 0

        print("Hinweis: --apply heilt (Verwaistes nach docs/, Generiertes aus dem Index); "
              "--check ist der CI-Modus; --move-doku ist opt-in, weil Issues auf "
              "Root-Pfade verlinken.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
