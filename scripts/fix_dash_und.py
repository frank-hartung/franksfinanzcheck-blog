#!/usr/bin/env python3
"""Gedankenstrich-vor-'und'-Korrektur (deterministisch, konservativ)
für FranksFinanzcheck.

Hintergrund (User-Meldung Riester-Artikel): Der Gedankenstrich (Halbgeviert-
strich '–' oder Geviertstrich '—') VOR 'und' ist oft redundant, weil 'und'
die Verknüpfung bereits leistet. Zwei sichere, deterministische Regeln:

  R1  „ – und <Jahreszahl>"   →  „. <Jahreszahl>"
      (nach 'und' beginnt ein NEUER Hauptsatz mit einer Jahreszahl;
       der Gedankenstrich ist hier ein Stilfehler – Punkt setzen)

  R2  „ – und <Präposition>"  →  „ und <Präposition>"
      (nach 'und' folgt ein Präpositional-Nachtrag; 'und' + Präposition
       markieren die Ergänzung bereits, der Strich ist überflüssig –
       glatt verbinden)

KONSERVATIV: Alle anderen „ – und"-Vorkommen bleiben unangetastet
(„und dass/wer/die/versteuert/sparst/zwar/danach…" – dort ist der
Gedankenstrich oft legitim, z. B. als betonter Nachtrag oder in
Checklisten-Fragen). Keine KI nötig – deterministisch und selbstheilend.

Nutzung:
  python3 scripts/fix_dash_und.py            # nur melden (Exit 0/1)
  python3 scripts/fix_dash_und.py --fix      # korrigieren
  python3 scripts/fix_dash_und.py --json     # JSON-Output

Exit: 0 = ok · 1 = offene Funde
"""
import os
import re
import sys
import json
import glob

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Gedankenstrich: Halbgeviertstrich oder Geviertstrich, von Leerzeichen umgeben.
# Das optionale Leerzeichen VOR dem Strich wird mit-konsumiert, damit keine
# doppelten Leerzeichen entstehen.
DASH = "[\u2013\u2014]"

# R1: Jahreszahl direkt nach „und" → NEUER Hauptsatz → Punkt.
#     „…Altersvorsorge – und 2026 steht…" → „…Altersvorsorge. 2026 steht…"
R1 = re.compile(r"[ \t]*" + DASH + r"\s+und\s+(20\d\d)(?![\d])")

# Präposition direkt nach „und"
PRAEP = (
    r"ab|an|auf|aus|bei|dank|durch|für|fuer|gegen|hinter|in|mit|nach|neben|"
    r"ohne|seit|trotz|über|ueber|um|unter|von|vor|wegen|zu|zwischen|außer|"
    r"ausser|binnen|entlang|gegenüber|gegenueber|gemäß|gemass|laut|mitsamt|"
    r"samt|zwecks"
)

# R2: NUR kurze Nachträge glätten. Nach „und <Präposition>" dürfen höchstens
#     4 weitere Wörter folgen, bis ein Satzzeichen oder Zeilenende kommt.
#     Kurze Phrasen sind fast immer Nachträge/Ellipsen („– und von einer
#     ehrlichen Rechnung."); lange Fortsetzungen sind Hauptsätze mit Subjekt
#     und Verb („– und mit der kostenlosen Stornierung kannst du nachbuchen…")
#     und bleiben bewusst unangetastet.
R2 = re.compile(
    r"[ \t]*" + DASH + r"\s+und\s+(" + PRAEP + r")((?:\s+\S+){0,4})"
    r"(?=[.!?,;:]|$)"
)


def iter_content_files():
    for pattern in ("content/posts/*/index.md", "content/posts/*.md",
                    "content/pillar/*/index.md"):
        for f in glob.glob(os.path.join(BLOG_DIR, pattern)):
            yield f


def fix_text(text):
    """Wendet R1/R2 an. Rückgabe (neuer_text, anzahl)."""
    n = 0

    def repl_r1(m):
        nonlocal n
        n += 1
        return ". " + m.group(1)

    def repl_r2(m):
        nonlocal n
        n += 1
        return " und " + m.group(1) + (m.group(2) or "")

    # R1 zuerst (Jahreszahl), dann R2 (kurze Präpositional-Nachträge)
    text = R1.sub(repl_r1, text)
    text = R2.sub(repl_r2, text)
    return text, n


def scan_file(path, fix=False):
    """Scannt eine Datei, optional mit Korrektur. Rückgabe Dict."""
    with open(path, encoding="utf-8") as f:
        content = f.read()
    in_code = False
    # Pro Zeile arbeiten, um Code-Blöcke (```) auszusparen
    out_lines = []
    findings = []
    for line in content.split("\n"):
        if line.strip().startswith("```"):
            in_code = not in_code
            out_lines.append(line)
            continue
        if in_code:
            out_lines.append(line)
            continue
        # Funde für Report (R1/R2 getrennt zählen)
        if R1.search(line):
            for m in R1.finditer(line):
                findings.append({"rule": "R1", "line": line.strip()[:100]})
        if R2.search(line):
            for m in R2.finditer(line):
                findings.append({"rule": "R2", "line": line.strip()[:100]})
        new_line, n = fix_text(line)
        out_lines.append(new_line)
    new_content = "\n".join(out_lines)
    if fix and findings and new_content != content:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
    return {"file": path, "findings": findings, "changed": new_content != content}


def main():
    fix = "--fix" in sys.argv
    as_json = "--json" in sys.argv
    total = 0
    results = []
    for path in iter_content_files():
        r = scan_file(path, fix=fix)
        if r["findings"]:
            total += len(r["findings"])
            results.append(r)
            for f in r["findings"]:
                print(f"  {'✅' if fix else '❌'} [{f['rule']}] "
                      f"{os.path.basename(os.path.dirname(path))}: {f['line']}")
    print(f"Gedankenstrich-Check: {total} Funde"
          + (f" – korrigiert" if fix else "") + " (R1: Jahreszahl→Punkt, "
          f"R2: Präposition→glatt)")
    if fix and total:
        try:
            from audit_log import log_event
            log_event(module="fix_dash_und", action="apply",
                      input={"files": len(results)}, output={"changes": total},
                      status="ok")
        except Exception:
            pass
    if as_json:
        print(json.dumps({"total": total, "fixed": fix,
                          "items": results}, ensure_ascii=False))
    return 1 if (total and not fix) else 0


if __name__ == "__main__":
    sys.exit(main())
