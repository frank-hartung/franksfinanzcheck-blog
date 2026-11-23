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
    """Liest einen Frontmatter-Skalar – auch ohne Anführungszeichen.

    BEFUND 22.11.2026 (Regression `test_live_wache_ist_gruen`): Diese Funktion
    verlangte doppelte Anführungszeichen (`^key: "(.*)"$`). Der gültige
    YAML-Skalar `pillar: versicherungen` wurde dadurch zu `""`. Folge: Die
    Siegel-Ausnahme in `_has_template_links` fiel STILL aus, und ein
    fassungsgebundener YAML-Artikel (kfz, `inhalt_sha256` gesetzt) wurde als
    „kein Rechner-Link“ gemeldet, obwohl `weiterrechnen_box.html` den Link im
    gerenderten HTML liefert. Ein Parser, der eine gültige Schreibweise nicht
    kennt, erfindet einen Befund – deshalb liest die Wache jetzt alle drei
    YAML-Formen (doppelt, einfach, nackt) und schneidet Kommentare ab.
    """
    m = re.search(rf'^{re.escape(key)}:[ \t]*(.*)$', front, re.M)
    if not m:
        return ""
    roh = m.group(1).strip()
    if not roh:
        return ""
    if roh[0] in ('"', "'"):
        ende = roh.find(roh[0], 1)
        return roh[1:ende] if ende != -1 else ""
    return roh.split(" #", 1)[0].strip()


def _is_live(front):
    return not re.search(r"^draft: true", front, re.M)


def _has_template_links(front):
    """Beiträge mit fassungsgebundenem YMYL-Siegel (inhalt_sha256) oder
    späterer Reserve-Veröffentlichung dürfen im Markdown-Body nicht
    nachträglich verändert werden (C25 / Reserve-Zertifikat). Für sie
    liefern weiterrechnen_box.html und pillar_box.html den Rechner- und
    Pillar-Link im gerenderten HTML, sofern `pillar` gesetzt ist."""
    if not _field(front, "pillar"):
        return False
    w_box = os.path.join(BLOG_DIR, "layouts", "_partials", "weiterrechnen_box.html")
    p_box = os.path.join(BLOG_DIR, "layouts", "_partials", "pillar_box.html")
    if not (os.path.isfile(w_box) and os.path.isfile(p_box)):
        return False
    if re.search(r"^\s*inhalt_sha256:\s*\"?[0-9a-f]{64}\"?\s*$", front, re.M):
        return True
    m = re.search(r"^reserve_published:\s*(\d{4}-\d{2}-\d{2})\s*$", front, re.M)
    return bool(m and m.group(1) > "2026-10-19")


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
            tpl_ok = _has_template_links(front)
            if "](../../werkzeuge/" not in body and "](/werkzeuge/" not in body and not tpl_ok:
                findings.append(f"FF3 {rel}: kein Rechner-Link")
            if "](../../pillar/" not in body and "](/pillar/" not in body and not tpl_ok:
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

    # FELDER LESEN (22.11.2026): Der Parser-Fix in `_field` ist die Ursache
    # eines Fehlbefunds an einem versiegelten Artikel gewesen – `pillar:
    # versicherungen` ohne Anführungszeichen wurde zu `""`, die Siegel-Ausnahme
    # in `_has_template_links` fiel still aus, und FF3 meldete „kein
    # Rechner-Link" gegen einen Beitrag, dessen weiterrechnen_box.html den Link
    # längst renderte. Der Fix selbst steht; was fehlte, ist seine Sicherung:
    # Ohne Probe altert er unbemerkt, und genau das ist die Lehre aus dem
    # Befund. Eine Wache, die gültige Werte nicht liest, ist doppelt falsch –
    # sie meldet Befunde, die keine sind, und übersieht dieselben Felder dort,
    # wo sie wirklich fehlen.
    #
    # Die Proben sind in BEIDE Richtungen scharf: Ein fehlendes oder leeres Feld
    # muss leer bleiben, sonst erfindet die Wache ein `pillar`-Feld und gibt die
    # Siegel-Ausnahme einem Beitrag, dessen Boxen nichts zu verlinken hätten.
    feld_proben = [
        ('pillar: "versicherungen"', "pillar", "versicherungen"),   # doppelt quotiert
        ("pillar: versicherungen", "pillar", "versicherungen"),     # nackt – der Befund
        ("pillar: 'konto-karten'", "pillar", "konto-karten"),       # einfach quotiert
        ('title: "Tagesgeld vergleichen: Was bleibt?"', "title",
         "Tagesgeld vergleichen: Was bleibt?"),                     # Doppelpunkt im Wert
        ("title: Tagesgeld vergleichen", "title", "Tagesgeld vergleichen"),
        ("draft: true", "pillar", ""),                              # Feld fehlt
        ("pillar:", "pillar", ""),                                  # Feld leer
        ('pillar: "wert"  # Kommentar', "pillar", "wert"),          # Inline-Kommentar
        ("pillar: wert # Kommentar", "pillar", "wert"),             # nackt + Kommentar
    ]
    for front, key, expect in feld_proben:
        got = _field(front, key)
        if got != expect:
            bad += 1
            print(f"  ✗ Feld-Probe fehlgeschlagen: {front!r} → {got!r}, erwartet {expect!r}")

    # Der Vertrag hinter dem Befund: Die Siegel-Ausnahme hängt an `_field`.
    sig = 'redaktionelle_pruefung:\n  inhalt_sha256: "' + ("a" * 64) + '"'
    if not _has_template_links("pillar: versicherungen\ndraft: false\n" + sig):
        bad += 1
        print("  ✗ Fassungsgebundener Beitrag mit nacktem pillar-Feld verliert die "
              "Template-Ausnahme – genau der Fehlbefund vom 22.11.2026.")
    if _has_template_links("draft: false\n" + sig):
        bad += 1
        print("  ✗ Beitrag OHNE pillar-Feld bekommt die Template-Ausnahme – "
              "die Boxen hätten nichts zu verlinken.")

    if bad:
        print(f"🛑 Inhalts-Wache-Selbsttest: {bad} Probe(n) falsch")
        return 2
    n_proben = len(cases) + len(feld_proben) + 2
    print(f"✅ Inhalts-Wache-Selbsttest bestanden "
          f"({n_proben} Proben: FF1 + Feldleser + Siegel-Ausnahme scharf)")
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
