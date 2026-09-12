#!/usr/bin/env python3
"""audio_coverage_check.py – wie viele Live-Artikel haben eine Studio-Tonspur?

WARUM (Premium-Audit 12.09.2026, Empfehlung 4 – mit Korrektur des Befunds):
Das Audit zählte „1 von 31 Artikeln mit Audio". Gezählt wurde aber im Quell-Repo
(`static/audio/`) – dort liegt nur das eine per Hand erzeugte Paar aus der
Anfangszeit. Die fertigen Tonspuren leben seit dem Härtungs-Deploy (10.09.2026)
auf dem **gh-pages-Zweig** unter `audio/articles/`: `deploy.yml` holt sie dort
pro Lauf als Cache zurück, vertont maximal `audio_limit_new` (Voreinstellung 25)
fehlende Artikel neu und veröffentlicht alles auf Pages. Im Quell-Repo zu zählen
ist also nicht falsch, aber unvollständig – und wer daraus „nichts passiert"
ableitet, repariert an der richtigen Stelle vorbei.

Diese Wache stellt die Zahl, die stimmt: Sie vergleicht die Live-Artikel des
Bestands mit den Tonspuren, die in einem Ort liegen, den man angeben kann:

    python3 scripts/audio_coverage_check.py                      # Fundorte der Reihe nach
    python3 scripts/audio_coverage_check.py --ref origin/gh-pages
    python3 scripts/audio_coverage_check.py --dir public/audio/articles
    python3 scripts/audio_coverage_check.py --strict             # Exit 1 bei Lücken
    python3 scripts/audio_coverage_check.py --json
    python3 scripts/audio_coverage_check.py --selftest           # 5 Fälle, ohne Netz

Exit: 0 = vollständig oder ohne Nachweis (Hinweis) · 1 = Lücke (--strict) · 2 = Fehler
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KANDIDATEN = ("public/audio/articles", "audio/articles")


def _git(root: str, *args: str) -> tuple[int, str]:
    try:
        p = subprocess.run(("git", "-C", root) + args, capture_output=True,
                           text=True, timeout=40)
        return p.returncode, (p.stdout or "")
    except Exception as exc:  # noqa: BLE001
        return 2, f"{exc.__class__.__name__}"


def assert_worktree(root: str) -> None:
    """Lesend harmless, aber die Sperre bleibt: kein Write, kein Seiteneffekt."""
    rc, top = _git(root, "rev-parse", "--show-toplevel")
    if rc != 0 or os.path.realpath(top.strip() or "") != os.path.realpath(root):
        raise SystemExit(f"❌ audio_coverage_check: {root} ist kein Git-Worktree.")


def live_artikel(root: str) -> list[str]:
    """Slugs der Artikel, die Hugo wirklich baut (draft:false, nicht in Zukunft)."""
    import datetime
    heute = datetime.date.today()
    out = []
    for idx in sorted(glob.glob(os.path.join(root, "content", "posts", "*", "index.md"))):
        with open(idx, encoding="utf-8") as fh:
            text = fh.read(4096)
        m = re.search(r"(?m)^draft:\s*(\S+)\s*$", text)
        if m and m.group(1).lower() in ("true", '"true"'):
            continue
        d = re.search(r"(?m)^date:\s*[\"']?(\d{4}-\d{2}-\d{2})", text)
        if d and datetime.date.fromisoformat(d.group(1)) > heute:
            continue
        out.append(os.path.basename(os.path.dirname(idx)))
    return out


def spuren_von_dir(pfad: str) -> set[str]:
    if not os.path.isdir(pfad):
        return set()
    return {os.path.splitext(os.path.basename(p))[0]
            for p in glob.glob(os.path.join(pfad, "*.mp3"))}


def _liste(root: str, ref: str, vorpfad: str) -> tuple[set[str], str]:
    rc, listing = _git(root, "ls-tree", "-r", "--name-only", ref, "--", vorpfad)
    if rc != 0:
        return set(), f"ls-tree auf {ref} fehlgeschlagen"
    return ({os.path.splitext(os.path.basename(l))[0] for l in listing.splitlines()
             if l.endswith(".mp3")}, ref)


def spuren_von_ref(root: str, ref: str, vorpfad: str = "audio/articles") -> tuple[set[str], str]:
    """(Slugs, Quelle).

    Der gh-pages-Zweig ist im Quell-Checkout normalerweise gar nicht gemappt –
    ohne diesen Nachhol-Pfad würde die Wache „0 %“ melden, wo in Wirklichkeit
    18 Tonspuren auf Pages liegen (der Fehler, den das Audit 12.09.2026 hatte).
    Gholt wird blob-frei und flach: nur Bäume, keine Audiodaten.
    """
    rc, _ = _git(root, "rev-parse", "--verify", "--quiet", ref)
    if rc == 0:
        return _liste(root, ref, vorpfad)
    branche = ref.split("/", 1)[1] if ref.startswith("origin/") else ref
    rc2, err = _git(root, "fetch", "--quiet", "--depth=1", "--filter=blob:none",
                    "origin", f"+{branche}:refs/remotes/{ref}")
    if rc2 != 0:
        return set(), (f"Ref {ref} nicht verfügbar "
                       f"({(err or '').strip()[:60] or 'kein Fetch-Zugriff'})")
    return _liste(root, ref, vorpfad)


def auswerten(root: str, ref: str, dire: str) -> dict:
    """→ {"artikel": [...], "spuren": set, "quelle": str, "fehlend": [...]}"""
    artikel = live_artikel(root)
    if dire:
        spuren, quelle = spuren_von_dir(os.path.join(root, dire)), dire
    elif ref:
        spuren, quelle = spuren_von_ref(root, ref)
    else:
        spuren, quelle = set(), ""
        for k in KANDIDATEN:
            s = spuren_von_dir(os.path.join(root, k))
            if s:
                spuren, quelle = s, k
                break
        if not quelle:
            s, q = spuren_von_ref(root, "origin/gh-pages")
            spuren, quelle = s, q
    return {"artikel": artikel, "spuren": spuren, "quelle": quelle,
            "fehlend": sorted(set(artikel) - spuren)}


def tabelle(res: dict) -> str:
    a, f = len(res["artikel"]), len(res["fehlend"])
    zeilen = [f"Studio-Audio-Abdeckung · {a - f}/{a} Live-Artikel mit Tonspur · "
              f"Nachweis: {res['quelle'] or 'kein Fundort'}"]
    if not res["spuren"]:
        zeilen.append("  ⚠ Kein Tonspur-Nachweis gefunden – die Zahl ist „unbekannt“, "
                      "nicht „null“. Quelle prüfen (--ref / --dir).")
    elif f:
        zeilen.append(f"  ⚠ {f} Artikel ohne eigene Tonspur (Gerätestimme springt ein; "
                      "Deploy mit audio_backfill=true schließt die Lücke):")
        for s in res["fehlend"][:40]:
            zeilen.append(f"     – {s}")
    else:
        zeilen.append("  ✅ Jeder Live-Artikel hat eine Studio-Tonspur.")
    return "\n".join(zeilen)


# ---------------------------------------------------------------------- Selbsttest
def _selftest() -> int:
    import shutil
    import tempfile
    errs: list[str] = []
    tmp = tempfile.mkdtemp(prefix="audio-cov-selftest-")
    try:
        root = os.path.join(tmp, "repo")
        os.makedirs(os.path.join(root, "content", "posts", "2026-08-01-a", "audio"),
                    exist_ok=True)
        os.makedirs(os.path.join(root, "content", "posts", "2026-08-02-b"), exist_ok=True)
        os.makedirs(os.path.join(root, "content", "posts", "2026-12-24-c"), exist_ok=True)
        os.makedirs(os.path.join(root, "content", "posts", "2026-08-03-d"), exist_ok=True)
        for slug, draft, datum in (("2026-08-01-a", "false", "2026-08-01"),
                                   ("2026-08-02-b", "false", "2026-08-02"),
                                   ("2026-12-24-c", "false", "2026-12-24"),
                                   ("2026-08-03-d", "true", "2026-08-03")):
            with open(os.path.join(root, "content", "posts", slug, "index.md"),
                      "w", encoding="utf-8") as fh:
                fh.write(f"---\ntitle: {slug}\ndate: {datum}T09:00:00Z\ndraft: {draft}\n---\nText\n")
        d = os.path.join(root, "public", "audio", "articles")
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "2026-08-01-a.mp3"), "w").write("x")
        open(os.path.join(d, "2026-08-01-a.timemap.json"), "w").write("{}")

        # 1) Fundort im Build: 1 von 2 (Zukunfts-C zählt nicht, Draft-D auch nicht)
        res = auswerten(root, "", "public/audio/articles")
        if res["artikel"] != ["2026-08-01-a", "2026-08-02-b"]:
            errs.append(f"Live-Artikel falsch: {res['artikel']}")
        if res["fehlend"] != ["2026-08-02-b"]:
            errs.append(f"Lücke nicht erkannt: {res['fehlend']}")
        if "1/2 Live-Artikel" not in tabelle(res):
            errs.append("Tabelle meldet die falsche Quote")

        # 2) keine Nachweisquelle => Hinweis, nicht „0 %“-Behauptung
        res2 = {"artikel": res["artikel"], "spuren": set(), "quelle": "",
                "fehlend": res["artikel"]}
        if "unbekannt" not in tabelle(res2):
            errs.append("fehlender Nachweis wird als Lücke verkauft")

        # 3) vollständig => friedlich
        open(os.path.join(d, "2026-08-02-b.mp3"), "w").write("x")
        res3 = auswerten(root, "", "public/audio/articles")
        if res3["fehlend"]:
            errs.append(f"nach dem Ziehen immer noch Lücke: {res3['fehlend']}")
        if "✅" not in tabelle(res3):
            errs.append("grüne Abdeckung nicht als grün gemeldet")

        # 4) Ref-Modus: Tonspuren liegen auf dem Pages-Zweig, nicht im Quellbaum
        spuren_dir = os.path.join(root, "audio", "articles")
        os.makedirs(spuren_dir, exist_ok=True)
        with open(os.path.join(spuren_dir, "2026-08-01-a.mp3"), "w") as fh:
            fh.write("x")
        for cmd in (("init", "-q", "."), ("config", "user.email", "t@x"),
                    ("config", "user.name", "t"), ("add", "-A"),
                    ("commit", "-q", "-m", "basis"),
                    ("checkout", "-q", "--orphan", "gh-pages"),
                    ("add", "-f", "audio/articles/2026-08-01-a.mp3"),
                    ("commit", "-q", "-m", "audio")):
            _git(root, *cmd)
        spuren, quelle = spuren_von_ref(root, "gh-pages")
        if spuren != {"2026-08-01-a"}:
            errs.append(f"Ref-Auslese liefert {spuren} (Quelle {quelle})")
        res4 = auswerten(root, "gh-pages", "")
        if res4["fehlend"] != ["2026-08-02-b"]:
            errs.append(f"Ref-Modus rechnet falsch: {res4}")

        # 5) Worktree-Sperre: fremdes Verzeichnis wird abgewiesen (Fall 7)
        assert_worktree(root)  # hier darf es durchgehen
        try:
            assert_worktree(tmp)
            errs.append("Sperre greift nicht außerhalb eines Worktrees")
        except SystemExit:
            pass
    except Exception as exc:  # noqa: BLE001
        errs.append(f"Ausführung: {exc.__class__.__name__}: {exc}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if errs:
        print("🛑 audio_coverage_check-Selbsttest FEHLGESCHLAGEN:")
        for e in errs:
            print("  -", e)
        return 2
    print("✅ Audio-Abdeckungs-Selbsttest: 5 Fälle grün (Build, Ref, Hinweis, Sperre).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Studio-Tonspuren vs. Live-Bestand")
    ap.add_argument("--root", default=BLOG_DIR)
    ap.add_argument("--dir", default="", help="Verzeichnis mit <slug>.mp3 (z. B. public/audio/articles)")
    ap.add_argument("--ref", default="", help="Git-Ref, z. B. origin/gh-pages")
    ap.add_argument("--vorpfad", default="audio/articles")
    ap.add_argument("--strict", action="store_true", help="Exit 1 bei Lücken")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    root = os.path.abspath(args.root)
    assert_worktree(root)
    res = auswerten(root, args.ref, args.dir)
    res_out = dict(res)
    res_out["spuren"] = sorted(res["spuren"])
    if args.json:
        print(json.dumps(res_out, ensure_ascii=False, indent=2))
    else:
        print(tabelle(res))
    return 1 if (args.strict and res["spuren"] and res["fehlend"]) else 0


if __name__ == "__main__":
    sys.exit(main())
