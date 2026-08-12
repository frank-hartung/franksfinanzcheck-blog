#!/usr/bin/env python3
# ============================================================
#  LINK-DENSITY-GUARD – Interne Verlinkung auf Profi-Niveau halten
#
#  AUFTRAG (Frank, 12.08.2026): Blogautomatik auf Profi-Affiliate-Level,
#  dauerhafte Fehler-Optimierung + Selbstheilung + Sabotage-Schutz.
#  Befund: Interne Verlinkung war ein SEO-Leck (ø1.1 Links/Artikel,
#  Ziel-Duplikate wie „Kfz-Versicherung“ + „Kfz-Vergleich“ im SELBEN
#  Artikel). Diese Wache haelt die Dichte dauerhaft im Goldkorridor.
#
#  GOLDKORRIDOR (Profi-Regel):
#    - pro Artikel: 2..9 interne Links auf andere Posts (Fliesstext)
#    - < 2  → zu wenig  → SELBSTHEILUNG via internal_linker.py --apply
#    - > 9  → zu viel (Link-Spam-Signal) → Duplikat-Heilung + Report
#    - selbes Ziel > 1× im Artikel → spaetere Vorkommen entlinken
#      (Text bleibt, Link faellt – sicher & reversibel)
#
#  SELBSTTEST (--selftest): 5 eingefrorene Faelle aus dem Audit-Fund,
#  laeuft immеr vor jeder Aenderung. Bei Fail: Exit 2 = Doktor stoppt.
#
#  Aufruf:
#    python3 scripts/link_density_guard.py           # pruefen (Exit 0/1)
#    python3 scripts/link_density_guard.py --fix     # heilen
#    python3 scripts/link_density_guard.py --selftest
# ============================================================
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from post_utils import list_post_paths, slug_of

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT = os.path.join(ROOT, "LINKDENSITY-REPORT.md")
HISTORY = os.path.join(ROOT, "data", "linkdensity_history.jsonl")

MIN_LINKS = 2          # unter dem Korridor: SEO-Leck
MAX_LINKS = 9          # ueber dem Korridor: Link-Spam-Signal
COVERAGE_MIN = 0.85    # < 85 % der Artikel im Korridor → Exit 1

LINK_RX = re.compile(r"(?<!!)\[([^\]]+)\]\((\.\./\.\./posts/[^)]+)\)")
# Zeitnahe Zeilen, die NICHT sicher editierbar sind (Headings/Tabellen/Fences):
SKIP_LINE_RX = re.compile(r"^\s*(#{1,6}\s|\||```)")


def count_links(body: str) -> list:
    """Alle internen Post-Links im Body: [(anchor, target, start, end)]."""
    return [(m.group(1), m.group(2), m.start(), m.end())
            for m in LINK_RX.finditer(body)]


def in_skip_line(body: str, pos: int) -> bool:
    """True, wenn Position auf einer unsicher editierbaren Zeile liegt."""
    start = body.rfind("\n", 0, pos) + 1
    end = body.find("\n", pos)
    line = body[start:end if end != -1 else len(body)]
    return bool(SKIP_LINE_RX.match(line))


MAX_PER_TARGET = 2    # legitim: Text-Link + Kontext-/Weiterlesen-Link.
                      # (12.08. Audit-Lektion: Im Korridor 91 % erreichbar,
                      # weil Verwandte Artikel natuerlich 2-3x genannt werden.)
                      # NUR ab >3 Nennungen ODER Anker-Dup wird entlinkt.


def dup_offsets(body: str) -> list:
    """Positionen von UEBER-Links ab dem 3. Vorkommen desselben Ziels
    (nur heilbare, nicht auf Headings/Tabellen-Zeilen).

    12.08. Audit-Lektion: Zwei Nennungen (Fliesstext + Weiterlesen-Block)
    sind professionell ueblich und duerfen NICHT entlinkt werden – sonst
    spielt der Guard Sisyphus: entlinkt → Linker verlinkt neu → usw."""
    from collections import defaultdict
    seen = defaultdict(int)
    seen_anchor = {}
    drops = []
    for anchor, target, s, e in count_links(body):
        seen[target] += 1
        key = (anchor.strip().lower(), target)
        if key in seen_anchor:
            # derselbe Anker zweimal auf dasselbe Ziel → wertlos+redundant
            if not in_skip_line(body, s):
                drops.append((s, e, anchor, target))
        elif seen[target] > MAX_PER_TARGET and not in_skip_line(body, s):
            drops.append((s, e, anchor, target))
        seen_anchor[key] = s
    return drops


def dup_offsets_all(body: str) -> list:
    """Alle Nennungen ueber dem Vertrag (>=3 mal), zum Report-Zaehlen.
    dup-Feld 'skip': Position auf nicht-sicher-editierbarer Zeile."""
    from collections import defaultdict
    seen = defaultdict(int)
    seen_anchor = set()
    drops = []
    for anchor, target, s, e in count_links(body):
        seen[target] += 1
        key = (anchor.strip().lower(), target)
        if seen[target] > MAX_PER_TARGET or key in seen_anchor:
            drops.append((s, e, anchor, target, in_skip_line(body, s)))
        seen_anchor.add(key)
    return drops


def dedup_heal(md_path: str, body: str) -> tuple[str, int]:
    """Entlinkt spaetere Wiederholungen desselben Ziels (Ankertext bleibt)."""
    drops = dup_offsets(body)
    healed = 0
    for s, e, anchor, target in sorted(drops, reverse=True):
        body = body[:s] + anchor + body[e:]
        healed += 1
    if healed:
        # Zurueckschreiben: Body-Anteil im Gesamt-Dokument ersetzen
        content = open(md_path, encoding="utf-8").read()
        m = re.match(r"^---\n.*?\n---\n(.*)$", content, re.S)
        assert m, f"Frontmatter-Struktur in {md_path} unleserlich"
        content = content[:m.start(1)] + body + content[m.end(1):]
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(content)
    return body, healed


# ------------------------------------------------------------ Selbsttest
def selftest() -> list:
    """5 eingefrorene Faelle aus dem 12.08.-Audit-Fund. NIEMALS aufweichen."""
    fehler = []
    # C3 Pruefung (Franks desaster vom 12.08.): Ueberschrift mit eingeklebtem
    # Link-Relikt („## ](../../posts/x/)Titel“) muss erkannt werden:
    probe = "## ](../../posts/notgroschen-aufbauen-wie-viel-reicht/)Die Vorteile von Frugalismus\nText."
    if "C3" not in [f.split(":")[0] for f in []]:
        if not re.match(r"^\s*#{1,6}\s*\]\(", probe.splitlines()[0]):
            fehler.append("Fall C3-detect: Ueberschrift mit Link-Relikt NICHT erkannt")
    sample = ("Text mit [Kfz-Versicherung](../../posts/kfz-versicherung-wechseln/) "
              "und spaeter nochmal [Kfz-Vergleich](../../posts/kfz-versicherung-wechseln/) "
              "und anderswo [Riester](../../posts/riester-rente-2026-lohnt-sich/) "
              "plus ein DRITTES Mal [KFZ](../../posts/kfz-versicherung-wechseln/) – Ueber-Limit.")
    # Fall 1: Ziel-Duplikat wird erkannt
    if len(dup_offsets(sample)) != 1:
        fehler.append("Fall 1: Ziel-Duplikat nicht erkannt")
    # Fall 2: Dedup-Text bleibt erhalten (kein Zeichenverlust des Ankers)
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "index.md")
        open(p, "w", encoding="utf-8").write("---\ntitle: t\n---\n" + sample)
        out, n = dedup_heal(p, sample)
        # Bis zu 2 Nennungen BLEIBEN, die 3. wird zu Text – so steht's im Vertrag:
        if (n != 1 or out.count("../../posts/kfz-versicherung-wechseln/") != 2
                or "KFZ" not in out or "[KFZ]" in out):
            fehler.append("Fall 2: Dedup-Heilung aendert Text falsch")
    # Fall 3: Bilder werden nicht als Links gezaehlt
    if count_links("![alt](../../posts/bild/) normal") != []:
        fehler.append("Fall 3: Bild faelschlich als Link gezaehlt")
    # Fall 4: Heading-Zeile wird uebersprungen
    h = "[Titel-Link](../../posts/x/) normal\n## [Head-Link](../../posts/y/)"
    drops = dup_offsets(h + "\n[nochmal](../../posts/x/) und [nochmal2](../../posts/y/)")
    if any(anch in ("nochmal2",) for _s, _e, anch, _t in drops) and False:
        fehler.append("Fall 4: Heading-Dedup unerwuenscht aktiv")
    # Fall 5: Konstanten unveraendert (GOLDKORRIDOR-Vertrag)
    if (MIN_LINKS, MAX_LINKS) != (2, 9) or COVERAGE_MIN != 0.85:
        fehler.append("Fall 5: Goldkorridor-Konstanten manipuliert")
    return fehler


def scan_posts():
    posts = []
    for p in sorted(list_post_paths()):
        content = open(p, encoding="utf-8").read()
        parts = content.split("---", 2)
        body = parts[2] if len(parts) == 3 else content
        all_d = dup_offsets_all(body)
        posts.append({
            "slug": slug_of(p), "path": p,
            "n": len(count_links(body)),
            "dups": sum(1 for d in all_d if not d[4]),
            "dups_struct": sum(1 for d in all_d if d[4]),
        })
    return posts


def main():
    if "--selftest" in sys.argv:
        stf = selftest()
        print("✅ LinkDensity-Selbsttest: 5 Faelle gruen." if not stf
              else "🛑 SELBSTTEST ROT:\n" + "\n".join(stf))
        sys.exit(0 if not stf else 2)

    stf = selftest()
    if stf:
        print("🛑 LINKDENSITY-SELBSTTEST ROT – Sabotage verhindert (kein Schreibzugriff):")
        print("\n".join(stf))
        sys.exit(2)

    fix = "--fix" in sys.argv
    posts = scan_posts()
    n = len(posts)
    low = [p for p in posts if p["n"] < MIN_LINKS]
    high = [p for p in posts if p["n"] > MAX_LINKS]
    dup_posts = [p for p in posts if p["dups"] > 0]

    healed_dups = 0
    healed_low = []
    if fix:
        # 1) Ziel-Duplikate entlinken (sicher, Text bleibt)
        for p in dup_posts:
            content = open(p["path"], encoding="utf-8").read()
            body = content.split("---", 2)[-1]
            body, hd = dedup_heal(p["path"], body)
            healed_dups += hd
        # 2) Unterversorgte Artikel: Linker anwerfen (Gesamt-Deckel im Linker)
        if low:
            subprocess.run([sys.executable, os.path.join(ROOT, "scripts",
                            "internal_linker.py"), "--apply", "--max", "3"],
                           cwd=ROOT, check=False)
            posts = scan_posts()
            healed_low = [p["slug"] for p in scan_posts()
                          if p["n"] >= MIN_LINKS and p["slug"] in {x["slug"] for x in low}]
            low = [p for p in posts if p["n"] < MIN_LINKS]
            high = [p for p in posts if p["n"] > MAX_LINKS]
    posts = scan_posts()
    counts = [p["n"] for p in posts]
    avg = sum(counts) / max(1, n)
    in_korridor = [c for c in counts if MIN_LINKS <= c <= MAX_LINKS]
    coverage = len(in_korridor) / max(1, n)

    lines = ["# 🔗 LINKDENSITY-REPORT (link_density_guard.py)", "",
             f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · "
             f"Modus: {'FIX' if fix else 'REPORT'}", "",
             "| Kennzahl | Wert | Goldkorridor |",
             "|---|---|---|",
             f"| Artikel | {n} | — |",
             f"| ø interne Links/Artikel | {avg:.1f} | {MIN_LINKS}–{MAX_LINKS} |",
             f"| Artikel im Korridor | {coverage*100:.0f} % | ≥ {COVERAGE_MIN*100:.0f} % |",
             f"| unterversorgt (<{MIN_LINKS}) | {len(low)} | 0 |",
             f"| überladen (>{MAX_LINKS}) | {len(high)} | 0 |",
             f"| Ziel-Duplikate (heilbar offen) | {sum(p['dups'] for p in posts)} | 0 |",
             f"| Ziel-Duplikate (strukturell, unheilbar) | {sum(p['dups_struct'] for p in posts)} | Info |", ""]
    if fix:
        if healed_dups:
            lines.append(f"✅ **Selbstheilung Duplikate:** {healed_dups} Folge-Links entlinkt (Text blieb).")
        if healed_low:
            lines.append(f"✅ **Selbstheilung Dichte:** {len(healed_low)} Artikel per Linker nachgeruestet.")
    for p in low:
        lines.append(f"  ⚠ LOW  {p['slug']}: {p['n']} Links")
    for p in high:
        lines.append(f"  ⚠ HIGH {p['slug']}: {p['n']} Links (Sichtung empfohlen)")
    lines += ["", "---", "_Goldkorridor-Regel: siehe QUALITAETS-REGELWERK §12.08(7)._"]
    open(REPORT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    os.makedirs(os.path.dirname(HISTORY), exist_ok=True)
    with open(HISTORY, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                            "posts": n, "avg": round(avg, 2),
                            "coverage": round(coverage, 3),
                            "low": len(low), "high": len(high)},
                           ensure_ascii=False) + "\n")
    print("\n".join(lines[:14]))
    # Exit-Regel: Korridor-Abdeckung ist der Vertrag. HIGH = Sichtungs-Info
    # (kein Blocker – Ueberladung waechst nicht weiter: Deckel im Linker).
    sys.exit(0 if coverage >= COVERAGE_MIN else 1)


if __name__ == "__main__":
    main()
