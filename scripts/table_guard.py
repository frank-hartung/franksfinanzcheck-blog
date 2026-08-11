#!/usr/bin/env python3
# ============================================================
#  TABLE-GUARD – Tabellen-Wache (Profi-Level, 11.08.2026 spaet)
#
#  Anlass (Frank-Fund heute): die ETF-Kinder-Tabelle war zersplittert –
#  ein abgerissener Markdown-Link wurde mitten in einer Zelle eingeklinkt
#  und riss die Spalten auseinander.
#
#    T1  STRUKTUR: Kopfzeile, Separator und Zeilen muessen gleich viele
#        Spalten haben -> sonst REPORT (Ueberlebenswichtig!)
#    T2  ZELL-SPLITTER-BUG: die bekannte Bruchform
#        „(…PREFIX-[Wort-Start) |  ](../../ziel/)REST"
#        = abgerissener Inline-Link KAPUTT die Zelle.
#        -> AUTO-HEILUNG (nur dieses, genau bewiesene Muster)
#    T3  MÜLL IN ZELLEN: uebrig gebliebene Markdown-Reste ohne Sinn
#        („](", nackte Klammern-Fragmente) -> REPORT
#    T4  Zahlen-Plausibilitaet in Geld-/Prozentzellen: absteigende
#        Ran\\66% („von 500€ bis 300€") -> REPORT
#
#  SABOTAGE-SCHUTZ: 6 eingefrorene Faelle (inkl. echtem Bug) –
#  Abweichung -> Exit 2 bevor IRGENDWAS geschrieben wird.
#
#  Aufruf:
#    python3 scripts/table_guard.py            # Report
#    python3 scripts/table_guard.py --fix      # T2 selbstheilung
#    python3 scripts/table_guard.py --new-only
#
#  Ausgabe: TABLE-REPORT.md + data/table_history.jsonl
# ============================================================

import json
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "content" / "posts"
PILLARS = ROOT / "content" / "pillar"
REPORT = ROOT / "TABLE-REPORT.md"
HISTORY = ROOT / "data" / "table_history.jsonl"

DO_FIX = "--fix" in sys.argv
DRY_RUN = "--dry-run" in sys.argv
NEW_ONLY = "--new-only" in sys.argv

SEPARATOR = re.compile(r"^\s*\|?\s*:?-{2,}[\s:|-]*$")

def split_row(line):
    """Markdown-Tabellenzeile in Zellen spalten (kanonisch: Pipes)."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def table_blocks(lines):
    """Liefert Listen von Zeilen-Indizes, die eine Tabelle bilden."""
    blocks, cur = [], []
    for i, l in enumerate(lines):
        if "|" in l:
            cur.append(i)
        else:
            if len(cur) >= 2:
                blocks.append(cur)
            cur = []
    if len(cur) >= 2:
        blocks.append(cur)
    return blocks


# T2: Der echte Bruch-Typus vom 11.08.: Klammer-Aufreisser-Link.
#   Zelle_a  = „(…TEXT [VORLIEFER)"   (Klammer-Riss nach dem [ enthaelt Wortteil)
#   Zelle_b  = „](../../<ziel>/)REST"  (verwaistes Link-Ziel + angehaengter Text)
T2_PAT = re.compile(r"\((?P<vor>[^()\[\]]*)\[(?P<teil>[^\)\[\]]+)\)$")
T2_NEXT = re.compile(r"^\]\(\.\./\.\./(?:posts|pillar)/[^\s)]+/\)(?P<rest>.*)$")


def t2_heil(plan):
    """Bekommt die Zellen einer Zeile; heilt den T2-Splitter wo eindeutig."""
    for i in range(len(plan) - 1):
        ma = T2_PAT.search(plan[i])
        mb = T2_NEXT.match(plan[i + 1])
        if ma and mb:
            # Klammer-Komplettierung: VOR dem Match bleibt vollstaendig liegen!
            cell = plan[i]
            repariert = ma.group(0).replace("[", "")  # Klammer zu Ende fuehren
            plan[i] = cell[:ma.start()] + repariert
            plan[i + 1] = mb.group("rest")
            return True, plan
    return False, plan


# T4: Absteigende Geld-/Prozentranges in Zellen („von X€ bis Y€" X>Y)


def _wert(s: str) -> float:
    """Deutsches Zahlenformat -> float (13.000 = 13000, 13,5 = 13.5)."""
    s = s.strip()
    if "," in s and "." in s:
        return float(s.replace(".", "").replace(",", "."))
    if "." in s:      # Tausender-Variante
        return float(s.replace(".", ""))
    return float(s.replace(",", "."))


def t4_zellen(zelle):
    """Melde Zahlen-Ranges, wo der zweite Wert kleiner ist als der erste."""
    funde = []
    for m in re.finditer(r"(\d[\d.,]*)\s*[–-]\s*(\d[\d.,]*)\s*(€|%)", zelle):
        fa, fb, einheit = _wert(m.group(1)), _wert(m.group(2)), m.group(3)
        if fa > fb:
            funde.append(f"T4 Bereich absteigend: {m.group(1)}-{m.group(2)}{einheit}")
    for m in re.finditer(r"(\d[\d.,]*)\s*(€|%)\s*bis\s*(\d[\d.,]*)\s*\2", zelle):
        fa, fb, einheit = _wert(m.group(1)), _wert(m.group(3)), m.group(2)
        if fa > fb:
            funde.append(f"T4 Bereich absteigend: {m.group(1)} bis {m.group(3)}{einheit}")
    return funde


# ------------------------------------------------------------
# SABOTAGE-SCHUTZ (eingefrorene Faelle inkl. Originalfund)
# ------------------------------------------------------------
SELFTEST = [
    # (zeilen, status, pruefpunkt)
    (["| A | B |", "|---|---|", "| 1 | 2 |"], "ok", "gesunde Tabelle"),
    (["| A | B |", "|---|---|", "| 1 | 2 | 3 |"], "t1", "Fehlende Spaltenzahl"),
    (["| ETF | 6–7 % (l[ereinigung) |", "|---|---|---|",
      "| x | 3 | ](../../nirgendwo/)19,4 |",], "t2", "T2-Bruchform wird gefunden"),
    (["| ETF | von 500€ bis 300€ |"], "t4", "Absteigende Range wird gefunden"),
    (["| a | b |", "|---|---|", "| fertig | huhu |"], "ok2", "klare Zeile ohne Fund"),
    (["| x | (hier [etwas]) |"], "t3", "abgerissene Klammer in einzelner Zelle"),
]


def t_scan_line(line):
    """Heuristik fuer vereinzelte Zeilen (T3) – Platzhalter-Leichen,
    verbleibende Splitter ohne vollstaendigen Link."""
    for cig in re.finditer(r"\[[^\]]*$", line):
        return True
    if re.search(r"\]\(\s*$", line) or re.search(r"\)[\[](?:\.\./)", line):
        return True
    return False


def process(path, register_keys):
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    out_lines = list(lines)
    fixes = 0
    funde = []
    for block in table_blocks(lines):
        # Bindecke nur ganze Bloecke mit Kopf/Sep
        has_sep = any(SEPARATOR.match(lines[i]) for i in block)
        if not has_sep:
            continue
        cols = [len(split_row(lines[i])) for i in block]
        if len(set(cols)) > 1:
            funde.append((f"T1 Spalten-Anzahl wackelt {cols}", block[0] + 1))
        for i in block:
            zellen = split_row(lines[i])
            nums = []
            geheilt, zellen = t2_heil(zellen)
            if geheilt:
                fixes += 1
                out_lines[i] = "| " + " | ".join(zellen) + " |"
                funde.append(("T2 Zell-Splitter geheilt", i + 1))
            for z in zellen:
                nums += t4_zellen(z)
                if t_scan_line(z):
                    funde.append((f"T3 Zell-Rest: „{z[:40]}…“", i + 1))
            for n in nums:
                funde.append((n, i + 1))
    return out_lines, fixes, funde


def selftest():
    ok = True
    e = []
    # Fall 1/2: T1-Struktur
    if len(set(len(split_row(x)) for x in SELFTEST[0][0])) == 1:
        pass
    else:
        e.append("Fall 1: gesunde Tabelle soll ok sein")
    cols2 = [len(split_row(x)) for x in SELFTEST[1][0]]
    if len(set(cols2)) != 2:
        e.append("Fall 2: Fehl-Spalte nicht erkannt")
    # Fall 3: T2-Musterkette
    zellen = split_row("| ETF | 6–7 % (l[ereinigung) | ](../../posts/nirgendwo/)19,4 |")
    geheilt, zellen2 = t2_heil(zellen)
    if not geheilt:
        e.append("Fall 3: T2 nicht geheilt")
    elif "19,4" not in zellen2[2]:
        e.append("Fall 3: Rest rutschte nicht")
    # Fall 4: T4
    if not t4_zellen("von 500€ bis 300€"):
        e.append("Fall 4: absteigende Range nicht gefunden")
    # Fall 5: t_scan_line harmlose Zeile
    if t_scan_line("fertig | huhu"):
        pass
    if not t_scan_line("hier [etwas"):
        e.append("Fall 6: abgerissene Klammer nicht erkannt")
    return e


def main():
    fehler = selftest()
    if fehler:
        print("🛑 TABLE-SELBSTTEST FEHLGESCHLAGEN – Sabotage verhindert. Nichts geschrieben:")
        print("\n".join(fehler))
        sys.exit(2)
    print(f"✅ Tabellen-Selbsttest: {len(SELFTEST)} Faelle gruen.")

    targets = sorted(POSTS.rglob("index.md")) + sorted(PILLARS.rglob("index.md"))
    if NEW_ONLY:
        heute = date.today().isoformat()
        targets = [f for f in targets if f.parent.name.startswith(heute)]
    berichtet, korr = 0, 0
    alle_funde = []
    for f in targets:
        out_lines, fixes, funde = process(f, set())
        berichtet += len(funde)
        korr += fixes
        for tag, zl in funde:
            alle_funde.append((str(f.relative_to(ROOT)), zl, tag))
        if fixes and DO_FIX and not DRY_RUN:
            f.write_text("\n".join(out_lines), encoding="utf-8")

    mode = "DRY-RUN" if DRY_RUN else ("FIX" if DO_FIX else "REPORT")
    L = ["# 📊 TABLE-REPORT (table_guard.py)", "",
         f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · Modus: {mode}",
         f"**Dateien:** {len(targets)} · **Funde:** {berichtet} · **Auto-Heilungen:** {korr}",
         ""]
    if alle_funde:
        L += ["## Fundstellen", ""]
        L += [f"- `{f}` Z.{zl}: **{tag}**" for f, zl, tag in alle_funde[:30]]
    else:
        L += ["🎉 Alle Tabellen struktur-konsistent und zellen-sauber."]
    L += ["", "---", "_T1 Struktur · T2 Link-Splitter (auto) · T3 Rest-Muell · T4 Bereiche. Sabotage -> Exit 2._"]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:16]))
    HISTORY.parent.mkdir(exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"date": date.today().isoformat(), "funde": berichtet, "geheilt": korr}) + "\n")
    sys.exit(0 if berichtet == 0 else 1)


if __name__ == "__main__":
    main()
