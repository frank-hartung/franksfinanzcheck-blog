#!/usr/bin/env python3
"""Inhalts-Wache FF1–FF5: verhindert die Fehler, die im SEO-Umbau aufgefallen sind.

FF1  Erfahrungsbehauptung ohne Kennzeichnung („Ich habe …“, „Meine Erfahrung“,
     „Mein eigener …“, „Fallstudie“ ohne „fiktiv“/„Beispiel“). Zitierte
     Vorlagentexte („…“) und Checklisten-Zeilen („- [ ]“) zählen nicht.
FF2  Formel-Titel „… Was sich jetzt für dich ändert“ in Titel, Keywords, Pin.
FF3  Live-Beitrag ohne Rechner-Link (/werkzeuge/) oder ohne Pillar-Link.
FF4  Doppelte Live-Titel (Kannibalisierung über identischen Titel).
FF5  Top-20-Abbildungen fehlen oder sind nicht eingebunden
     (delegiert an scripts/abbildungen_ableiten.py --check).

Modi:
  python3 scripts/ff_inhalts_wache.py             # Exit 1 bei Befund
  python3 scripts/ff_inhalts_wache.py --selftest  # Sabotage-Proben
"""
import glob
import os
import re
import subprocess
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXPERIENCE = re.compile(
    r"\b(?:[Ii]ch habe|[Mm]eine Erfahrung|[Mm]ein eigener|[Mm]ein eigenes|[Mm]ein Erfahrungswert|"
    r"[Mm]ein Sparbeispiel|[Mm]ein Wechsel|bei mir|[Ii]ch habe getestet)\b"
)
FALLSTUDIE = re.compile(r"Fallstudie")
FICTION_MARK = re.compile(r"fiktiv|Beispiel|Modellrechnung|Rechenbeispiel", re.I)
FORMULA = re.compile(r"Was sich jetzt für dich ändert")
QUOTED = re.compile(r'„[^“”"]*["“”]|"[^"]*"|“[^“”]*”')


def _front_and_body(text):
    if not text.startswith("---\n"):
        return "", text
    front, body = text[4:].split("\n---\n", 1)
    return front, body


def _field(front, key):
    m = re.search(rf'^{key}: "(.*)"$', front, re.M)
    return m.group(1) if m else ""


def _is_live(front):
    return not re.search(r"^draft: true", front, re.M)


def find_experience(body):
    findings = []
    for lineno, line in enumerate(body.split("\n"), 1):
        if line.lstrip().startswith("- [ ]"):
            continue
        stripped = QUOTED.sub("", line)  # Vorlagen in Anführungszeichen sind Zitat, keine Aussage
        if EXPERIENCE.search(stripped):
            findings.append(f"Zeile {lineno}: Erfahrungsbehauptung: „{line.strip()[:90]}“")
        for m in FALLSTUDIE.finditer(stripped):
            if not FICTION_MARK.search(line):
                findings.append(f"Zeile {lineno}: „Fallstudie“ ohne Kennzeichnung als fiktiv/Beispiel")
    return findings


def run_checks():
    posts = sorted(glob.glob(os.path.join(BLOG_DIR, "content", "posts", "*", "index.md")))
    findings = []
    live_titles = {}
    for path in posts:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        front, body = _front_and_body(text)
        rel = os.path.relpath(path, BLOG_DIR)
        live = _is_live(front)
        for key in ("title", "pin_title"):
            if FORMULA.search(_field(front, key)):
                findings.append(f"FF2 {rel}: Formel-Titel in {key}")
        if FORMULA.search(front) and re.search(r"^keywords:.*Was sich jetzt", front, re.M):
            findings.append(f"FF2 {rel}: Formel-Titel in keywords")
        for f in find_experience(body):
            findings.append(f"FF1 {rel}: {f}")
        if live:
            title = _field(front, "title")
            live_titles.setdefault(title, []).append(rel)
            if "](../../werkzeuge/" not in body and "](/werkzeuge/" not in body:
                findings.append(f"FF3 {rel}: kein Rechner-Link")
            if "](../../pillar/" not in body and "](/pillar/" not in body:
                findings.append(f"FF3 {rel}: kein Pillar-Link")
    for title, paths in live_titles.items():
        if len(paths) > 1:
            findings.append(f"FF4 gleicher Live-Titel „{title}“: {', '.join(paths)}")
    result = subprocess.run(
        [sys.executable, os.path.join(BLOG_DIR, "scripts", "abbildungen_ableiten.py"), "--check"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        for line in result.stdout.splitlines():
            if line.strip().startswith("-"):
                findings.append(f"FF5 {line.strip()[2:]}")
        if not any(f.startswith("FF5") for f in findings):
            findings.append("FF5 Abbildungen-Check nicht lesbar (PyYAML fehlt?)")
    return findings


def selftest():
    cases = [
        ("Ich habe alle drei Methoden getestet.", True),
        ("Meine Erfahrung: Wer antizyklisch sucht, gewinnt.", True),
        ("Fallstudie: Max, 28, Software-Entwickler", True),
        ("Rechenbeispiel mit einer fiktiven Person: Max, 28", False),
        ('Vorlage: „Ich habe am 18.40 Uhr eine Störung gemeldet“', False),
        ("- [ ] Ich habe ein separates Konto für die Reserve", False),
        ("Im Beispiel werden Tarifmerkmale angepasst.", False),
    ]
    bad = 0
    for sample, expect in cases:
        got = bool(find_experience(sample))
        if got != expect:
            bad += 1
            print(f"  ✗ Probe fehlgeschlagen (erwartet {expect}): {sample}")
    if bad:
        print(f"🛑 Inhalts-Wache-Selbsttest: {bad} Probe(n) falsch")
        return 2
    print("✅ Inhalts-Wache-Selbsttest bestanden (FF1-Proben scharf)")
    return 0


def main(argv):
    if "--selftest" in argv:
        return selftest()
    findings = run_checks()
    for f in findings:
        print("  -", f)
    print(f"Inhalts-Wache FF1–FF5: {len(findings)} Befund(e)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
