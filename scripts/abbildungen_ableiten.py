#!/usr/bin/env python3
"""Eigene Abbildungen für die Top-20-Beiträge (SEO-Punkt 4), reproduzierbar.

Quelle der Auswahl: data/top20_abbildungen.yaml (Regel steht dort).
Je Beitrag entstehen zwei SVG-Dateien im Beitragsordner, abgeleitet nur aus dem
eigenen Text des Beitrags (keine neuen Fakten):
  - abbildung-merkkarte.svg  Kernaussagen aus der Kurzantwort (max. 3 Sätze)
  - abbildung-ablauf.svg     Gliederung aus den Zwischenüberschriften

Modi:
  python3 scripts/abbildungen_ableiten.py            # erzeugen + einbinden (idempotent)
  python3 scripts/abbildungen_ableiten.py --check    # Exit 1, wenn eine Abbildung fehlt
  python3 scripts/abbildungen_ableiten.py --selftest # Regelprüfung ohne Dateischreiben
"""
import glob
import html
import os
import re
import sys
import textwrap

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIST_PATH = os.path.join(BLOG_DIR, "data", "top20_abbildungen.yaml")
SKIP = re.compile(
    r"Wichtigste|FAQ|Häufige|Fazit|Weiterrechnen|Passende|Quellen|Fragen|Ausblick|"
    r"Rechner|Themenseite|Affiliate|Transparenz",
    re.I,
)
MERK = "abbildung-merkkarte.svg"
ABLAUF = "abbildung-ablauf.svg"


def load_slugs():
    """Liest die Liste ohne PyYAML: Zeilen der Form  - slug: "<verzeichnis>"."""
    with open(LIST_PATH, encoding="utf-8") as fh:
        slugs = re.findall(r'^\s*-\s*slug:\s*"([^"]+)"', fh.read(), re.M)
    if not slugs:
        raise SystemExit(f"🛑 keine Beiträge in {LIST_PATH}")
    return slugs


def find_post(slug):
    hits = glob.glob(os.path.join(BLOG_DIR, "content", "posts", slug + "*", "index.md"))
    if len(hits) != 1:
        raise SystemExit(f"🛑 Beitrag nicht eindeutig: {slug} ({len(hits)} Treffer)")
    return hits[0]


def clean(text):
    text = re.sub(r"\*\*|__|\*|`", "", text)
    text = text.replace("‑", "-").replace("&nbsp;", " ").replace("\xa0", " ")
    text = text.replace("&quot;", '"').replace("&amp;", "&")
    return re.sub(r"\s+", " ", text).strip()


def split_sentences(text):
    return [
        s.strip()
        for s in re.split(r'(?<!\d)(?<=[.!?])\s+(?=[A-ZÄÖÜ„"])', text)
        if s.strip()
    ]


def merkkarte_svg(title, sentences):
    width, pad, y = 800, 40, 40
    parts = [f'<text x="{pad}" y="{y + 26}" font-size="26" font-weight="700" fill="#1f3a5f">Auf einen Blick</text>']
    y += 50
    parts.append(f'<line x1="{pad}" y1="{y}" x2="{width - pad}" y2="{y}" stroke="#d7e0ea" stroke-width="2"/>')
    y += 28
    for sentence in sentences:
        for i, line in enumerate(textwrap.wrap(sentence, width=62)):
            prefix = "•  " if i == 0 else "    "
            parts.append(f'<text x="{pad}" y="{y + 22}" font-size="21" fill="#222">{html.escape(prefix + line)}</text>')
            y += 32
        y += 12
    height = y + 60
    parts.append(f'<text x="{pad}" y="{height - 24}" font-size="16" fill="#6b7a8c">FranksFinanzcheck · Zusammenfassung des Beitrags</text>')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="{html.escape("Merkkarte: " + title)}">'
        '<rect width="100%" height="100%" fill="#f6f9fc"/>' + "".join(parts) + "</svg>"
    )


def ablauf_svg(title, steps):
    width, row = 800, 78
    height = 80 + row * len(steps) + 50
    parts = ['<text x="40" y="52" font-size="26" font-weight="700" fill="#1f3a5f">Gliederung des Beitrags</text>']
    for i, step in enumerate(steps):
        top = 90 + i * row
        parts.append(f'<circle cx="70" cy="{top + 22}" r="22" fill="#1f6f5c"/>')
        parts.append(f'<text x="70" y="{top + 29}" font-size="20" font-weight="700" fill="#fff" text-anchor="middle">{i + 1}</text>')
        for j, line in enumerate(textwrap.wrap(step, width=52)[:2]):
            parts.append(f'<text x="110" y="{top + 18 + j * 26}" font-size="21" fill="#222">{html.escape(line)}</text>')
        if i < len(steps) - 1:
            parts.append(f'<line x1="70" y1="{top + 44}" x2="70" y2="{top + row - 2}" stroke="#9fb8cc" stroke-width="3"/>')
    parts.append(f'<text x="40" y="{height - 20}" font-size="16" fill="#6b7a8c">FranksFinanzcheck · Zwischenüberschriften des Beitrags in Reihenfolge</text>')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="{html.escape("Gliederung: " + title)}">'
        '<rect width="100%" height="100%" fill="#ffffff"/>' + "".join(parts) + "</svg>"
    )


def build(post_path):
    with open(post_path, encoding="utf-8") as fh:
        text = fh.read()
    front, body = text.split("\n---\n", 1)
    title = clean(re.search(r'^title: "(.*)"', front, re.M).group(1))
    summary = clean(re.search(r'^kurzantwort: "(.*)"', front, re.M).group(1))
    sentences = split_sentences(summary)[:3]
    steps = [clean(m.group(1)) for m in re.finditer(r"^## (.+)$", body, re.M) if not SKIP.search(m.group(1))][:5]
    return title, sentences, steps, front, body


def render(post_path, write):
    title, sentences, steps, front, body = build(post_path)
    folder = os.path.dirname(post_path)
    if write:
        with open(os.path.join(folder, MERK), "w", encoding="utf-8") as fh:
            fh.write(merkkarte_svg(title, sentences))
        with open(os.path.join(folder, ABLAUF), "w", encoding="utf-8") as fh:
            fh.write(ablauf_svg(title, steps))
        if MERK not in body:  # idempotent: nur einmal einbinden
            lines = body.split("\n")
            h2 = [i for i, line in enumerate(lines) if line.startswith("## ")]
            if len(h2) < 2:
                raise SystemExit(f"🛑 zu wenige Abschnitte für Abbildungen: {post_path}")
            mid = h2[len(h2) // 2]
            lines[mid:mid] = [
                f"![Gliederung des Beitrags: {title}]({ABLAUF})", "",
                "*Abbildung: Gliederung des Beitrags in seinen Zwischenüberschriften (eigene Darstellung).*", "",
            ]
            first = h2[0]
            lines[first:first] = [
                f"![Merkkarte: Kernaussagen zu {title}]({MERK})", "",
                "*Abbildung: Merkkarte mit den Kernaussagen (eigene Darstellung aus diesem Beitrag).*", "",
            ]
            with open(post_path, "w", encoding="utf-8") as fh:
                fh.write(front + "\n---\n" + "\n".join(lines))
    return len(sentences), len(steps)


def check(slugs):
    problems = []
    for slug in slugs:
        path = find_post(slug)
        folder = os.path.dirname(path)
        with open(path, encoding="utf-8") as fh:
            body = fh.read()
        for name in (MERK, ABLAUF):
            if not os.path.isfile(os.path.join(folder, name)):
                problems.append(f"{slug}: Datei fehlt {name}")
            if name not in body:
                problems.append(f"{slug}: nicht eingebunden {name}")
    return problems


def selftest():
    sample = "Erster Satz. Zweiter Satz mit 3.5 Prozent. Dritter Satz!"
    parts = split_sentences(sample)
    assert parts == ["Erster Satz.", "Zweiter Satz mit 3.5 Prozent.", "Dritter Satz!"], parts
    assert clean("**fett** &quot;x&quot;") == 'fett "x"'
    assert "<svg" in merkkarte_svg("T", ["A."]) and "<svg" in ablauf_svg("T", ["Schritt"])
    print("✅ Abbildungen-Selbsttest bestanden")
    return 0


def main(argv):
    if "--selftest" in argv:
        return selftest()
    slugs = load_slugs()
    if "--check" in argv:
        problems = check(slugs)
        for p in problems:
            print("  -", p)
        print(f"Abbildungen-Check: {len(slugs)} Beiträge | Befunde: {len(problems)}")
        return 1 if problems else 0
    for slug in slugs:
        sentences, steps = render(find_post(slug), write=True)
        print(f"  ✔ {slug[:60]}: {sentences} Kernsätze, {steps} Gliederungspunkte")
    print(f"Abbildungen erzeugt für {len(slugs)} Beiträge.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
