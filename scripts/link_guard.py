#!/usr/bin/env python3
# ============================================================
#  LINK-GUARD – Interne Link-Integrität (relativ & /go/), selbstheilend
#
#  Anlass (11.08. spaet, Fund beim Bug-Sweep): Die Engine schrieb
#  interne Links mit ABGEKNIBBELTEN Slugs (z. B. ../../posts/
#  versicherungen-kuendigen-diese-5-poli/ statt …-policen/) – stille
#  404-Fabrik. Diese Wache verifiziert JEDES interne Linkziel gegen
#  das Verzeichnis-Register und heilt Abknickungen per
#  Praefix-/Fuzzy-Match; Seiten-Stamm-Regel: kein Blind-Versatz,
#  keine Fundstelle ohne Beweis.
#
#    V1  Relative Markdown-Links (../../posts|pillar/<slug>/) ->
#        Ziel muss existieren; sonst Heilung via slug-Match.
#    V2  /go/-Links -> nur bekannte Gateway-Keys (Register-Check).
#
#  SABOTAGE-SCHUTZ: SELFTEST (6 eingefrorene Faelle) vor jedem
#  Einsatz; Abweichung -> Exit 2, nichts wird angefasst.
#
#  Aufruf:
#    python3 scripts/link_guard.py            # Report
#    python3 scripts/link_guard.py --fix      # Auto-Heilung
#    python3 scripts/link_guard.py --new-only # Engine-Modus (heute)
#
#  Ausgabe: LINK-REPORT.md + data/link_history.jsonl
# ============================================================

import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "content" / "posts"
PILLARS = ROOT / "content" / "pillar"
REGISTRY = ROOT / "scripts" / "check24_links.yaml"
REPORT = ROOT / "LINK-REPORT.md"
HISTORY = ROOT / "data" / "link_history.jsonl"

DO_FIX = "--fix" in sys.argv
DRY_RUN = "--dry-run" in sys.argv
NEW_ONLY = "--new-only" in sys.argv

REL_LINK = re.compile(r"\]\((\.\./\.\./(?:posts|pillar)/)([^)\s]+?)(/?)\)")
GO_LINK = re.compile(r"\]\(/go/([\w-]+)/\)")


def slug_register() -> dict:
    """Alle real existierenden Slugs -> Sektion (posts|pillar)."""
    out = {}
    for base, sektion in ((POSTS, "posts"), (PILLARS, "pillar")):
        if base.exists():
            for d in sorted(base.iterdir()):
                if d.is_dir() and (d / "index.md").exists():
                    out[d.name] = sektion
    return out


def known_go_keys() -> set:
    reg = set()
    if REGISTRY.exists():
        for line in REGISTRY.read_text(encoding="utf-8").splitlines():
            ls = line.strip()
            if ls and not ls.startswith("#") and ": " in ls and '"' in ls:
                reg.add(ls.split(":")[0].strip())
    return reg


def heal_slug(broken: str, register: dict) -> str:
    """Praefix-/Fuzzy-Heilung: abgeknickter Slug -> naechster realer."""
    if broken in register:
        return broken
    # 1) Praefix-Match (Abknickung): der kuensteste, eindeutigste Treffer
    cands = [s for s in register if s.startswith(broken)]
    if len(cands) == 1:
        return cands[0]
    if len(cands) > 1:
        return min(cands, key=len)
    # 2) Broken ist zu lang? (umgekehrtes Praefix)
    cands = [s for s in register if broken.startswith(s)]
    if cands:
        return max(cands, key=len)
    # 3) Token-Jaccard (Zurueckhaltung: >= 0.6 sonst kommt nix)
    bt = set(re.split(r"[-_]", broken))
    best, bscore = None, 0.0
    for s in register:
        st = set(re.split(r"[-_]", s))
        j = len(bt & st) / max(1, len(bt | st))
        if j > bscore:
            best, bscore = s, j
    return best if bscore >= 0.6 else ""


# ------------------------------------------------------------
# SABOTAGE-SCHUTZ: Selbsttest (eingefrorene Faelle aus echten Fehlern)
# ------------------------------------------------------------
SELFTEST = [
    # (kaputter_slug, register_simuliert, erwartetes Ziel)
    ("versicherungen-kuendigen-diese-5-poli", {"versicherungen-kuendigen-diese-5-policen": ""}, "versicherungen-kuendigen-diese-5-policen"),
    ("notgroschen-aufbauen-wie-viel-rei", {"notgroschen-aufbauen-wie-viel-reicht": ""}, "notgroschen-aufbauen-wie-viel-reicht"),
    ("strom-sparen-haushalt-20-tipps", {"strom-sparen-haushalt-20-tipps": ""}, "strom-sparen-haushalt-20-tipps"),
    ("2026-08-06-turbo-fuers-n", {"2026-08-06-turbo-fuers-netz": ""}, "2026-08-06-turbo-fuers-netz"),
    ("gibt-es-gar-nicht-xyz", {"tagesgeld-zinsen": "", "dsl-wechsel": ""}, ""),
    ("kfz-versicherung-wechseln-extrailang", {"kfz-versicherung-wechseln": ""}, "kfz-versicherung-wechseln"),
]


def run_selftest() -> list:
    fehler = []
    for i, (broken, reg, want) in enumerate(SELFTEST, 1):
        got = heal_slug(broken, reg)
        if got != want:
            fehler.append(f"  Fall {i}: „{broken}“ → erwartet „{want or '—'}“, bekam „{got or '—'}“")
    return fehler


def scan_file(path: Path, register: dict, gow: set) -> tuple:
    rel = str(path.relative_to(ROOT))
    text = path.read_text(encoding="utf-8")
    fixes, reports = 0, []

    def repl_rel(m):
        nonlocal fixes
        prefix, slug, slash = m.group(1), m.group(2), m.group(3)
        # Sektionsfehler zuerst: exakten Slug in FALSCHER Sektion?
        if slug in register:
            want = "posts" if "posts" in prefix else "pillar"
            if register[slug] != want:
                fixes += 1
                reports.append(("V1-SEKTION", f"{prefix}{slug}/ -> ../../{register[slug]}/{slug}/"))
                return f"](../../{register[slug]}/{slug}{slash})"
            return m.group(0)
        healed = heal_slug(slug, register)
        if healed:
            fixes += 1
            sektion = register[healed]
            reports.append(("V1", f"{slug} -> {healed} ({sektion})"))
            return f"](../../{sektion}/{healed}{slash})"
        reports.append(("V1-TOT", f"kein Ziel fuer {slug} (manuell pruefen!)"))
        return m.group(0)

    text2 = REL_LINK.sub(repl_rel, text)

    for m in GO_LINK.finditer(text2):
        if m.group(1) not in gow:
            reports.append(("V2", f"/go/{m.group(1)}/ unbekannt (Register)"))

    return text2, fixes, reports


def main() -> None:
    fehler = run_selftest()
    if fehler:
        print("🛑 LINK-SELBSTTEST FEHLGESCHLAGEN – Sabotage verhindert. Nichts geschrieben:")
        print("\n".join(fehler))
        sys.exit(2)
    print(f"✅ Link-Selbsttest: {len(SELFTEST)} Faelle gruen.")

    register = slug_register()
    gow = known_go_keys()
    files = sorted(POSTS.rglob("index.md")) + sorted(PILLARS.rglob("index.md"))
    if NEW_ONLY:
        today = date.today().isoformat()
        files = [f for f in files if f.parent.name.startswith(today)]

    tot_fix, tot_dead, tot_reports = 0, 0, []
    for f in files:
        text2, fixes, reports = scan_file(f, register, gow)
        tot_fix += fixes
        tot_reports += [(str(f.relative_to(ROOT)), r) for r in reports]
        tot_dead += sum(1 for r in reports if r[0] == "V1-TOT") + sum(1 for r in reports if r[0] == "V2")
        if fixes and DO_FIX and not DRY_RUN and text2 != f.read_text(encoding="utf-8"):
            f.write_text(text2, encoding="utf-8")

    mode = "DRY-RUN" if DRY_RUN else ("FIX" if DO_FIX else "REPORT")
    L = ["# 🔗 LINK-REPORT (link_guard.py)", "",
         f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · Modus: {mode}",
         f"**Dateien:** {len(files)} · **Geheilte Links:** {tot_fix} · **Unheilbare Funde:** {tot_dead}", ""]
    if tot_reports:
        L += ["## Funde", ""]
        L += [f"- `{f}` | **{tag}** {msg[:80]}" for f, (tag, msg) in tot_reports[:30]]
    else:
        L += ["🎉 Alle internen Links verifiziert – keine Totstellen."]
    L += ["", "---", "_V1: relative Linkziele praefix-geheilt · V2: /go/-Keys gegen Register._"]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:12]))
    HISTORY.parent.mkdir(exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"date": date.today().isoformat(), "modus": mode,
                             "geheilt": tot_fix, "tot": tot_dead}) + "\n")
    sys.exit(1 if tot_dead else 0)


if __name__ == "__main__":
    main()
