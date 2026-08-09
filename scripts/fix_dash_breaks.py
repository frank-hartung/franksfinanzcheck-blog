#!/usr/bin/env python3
"""fix_dash_breaks.py – Dauerhafte Regel: Zeilenumbruch nach Gedankenstrich
vor erläuterndem Nachsatz.

WARUM: Auf schmalen Bildschirmen bricht der Browser sonst oft VOR dem
Gedankenstrich um („…verschiedener Reisedauern" / „– die 10-Tage-Variante…").
Damit der Nachsatz sauber auf einer NEUEN Zeile beginnt, wird nach „ – "
ein Markdown-Hard-Break gesetzt (zwei Leerzeichen + Zeilenumbruch =
CommonMark-<br>).

REGEL: Umbruch nur, wenn nach dem Gedankenstrich ein ERLÄUTERNDER
Nachsatz folgt (Artikel/Pronomen/Fragewort/Erläuterungs-Wort wie „die,
der, das, ein, wer, was, man, es, das heißt, sprich, konkret, …").
KEIN Umbruch bei Fortsetzungen (Präpositionen/Konjunktionen wie „und,
oder, für, mit, z. B., …" – z. B. die Affiliate-Disclosure „…Provision –
für dich entstehen keine Mehrkosten." bleibt kompakt).

Ausgenommen: Tabellenzeilen (enthalten „|") und Inline-Code (Backticks).
Idempotent: Bereits umgebrochene Stellen (Zeile endet mit „ –  ") werden
nicht angefasst.

Aufruf:  python3 scripts/fix_dash_breaks.py          (alle Dateien)
         python3 scripts/fix_dash_breaks.py --dry-run (nur anzeigen)
"""
import glob
import re
import sys

BLOG_DIR = __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))

# Nachsatz-Einleiter (→ Umbruch): Artikel, Pronomen, Fragewörter, Erläuterung
NACHSATZ_WORDS = (
    "die der das ein eine einer einem einen wer was wem wen man es "
    "sprich konkret genau wichtig entscheidend dabei außerdem zudem "
    "nämlich deshalb darum deswegen kurz kurzum letztlich letztendlich "
    "so dann damit hier dort alles nichts viel mehr weniger besser "
    "schlechter günstiger teurer schneller langsamer einfacher "
    "schwieriger sinnvoll ratsam empfehlenswert viele einige manche "
).split()
NACHSATZ_PHRASES = ("das heißt", "der Trick", "die Regel", "die Idee", "der Unterschied",
    "der Vorteil", "der Nachteil", "das Ergebnis", "das Fazit", "der Schlüssel",
    "die Antwort", "die Lösung", "die Wahrheit", "die Sache", "das Ganze",
    "die meisten", "die wenigsten", "am Ende", "im Kern")

# KEIN Umbruch (Fortsetzung): Präpositionen, Konjunktionen, Disclosure-Bausteine
KEIN_WORDS = (
    "und oder aber denn doch jedoch sowie auch nicht kein keine keinen "
    "keinem nie immer oft meist manchmal wirklich eigentlich eben ja nein "
    "für mit von bei auf zu um aus nach über unter vor bis an in im zum "
    "zur vom beim gegen ohne durch zwischen wegen als wie wenn weil dass "
    "damit obwohl während seit ab außer trotz laut dank je pro plus minus "
    "mal etwa rund ungefähr fast nur gerade schon noch bereits erst"
).split()
KEIN_PHRASES = ("z. B.", "zum Beispiel", "eine Provision", "ein paar", "ein wenig",
    "ein bisschen", "viele Jahre")

# Sortiert: längere Phrasen zuerst (sonst matcht „die" vor „die meisten")
_NACH = sorted(set(NACHSATZ_WORDS) | set(NACHSATZ_PHRASES), key=len, reverse=True)
_KEIN = sorted(set(KEIN_WORDS) | set(KEIN_PHRASES), key=len, reverse=True)

RE_NACHSATZ = re.compile(r" \u2013 (" + "|".join(re.escape(w) for w in _NACH) + r")(?![a-zäöüß])")
RE_KEIN = re.compile(r" \u2013 (" + "|".join(re.escape(w) for w in _KEIN) + r")(?![a-zäöüß])")

DASH = "\u2013"


def fix_body(body: str) -> tuple[str, int]:
    """Wendet die Regel auf den Body an. Liefert (neuer_body, anzahl)."""
    lines = body.split("\n")
    out: list[str] = []
    changed = 0
    for line in lines:
        # Tabellenzeilen, Inline-Code und ÜBERSCHRIFTEN auslassen
        # (eine Überschrift wie "### … – was ist besser?" darf NICHT
        # umgebrochen werden – der Titel würde zerrissen)
        if "|" in line or "`" in line or line.lstrip().startswith("#"):
            out.append(line)
            continue
        # Bereits umgebrochen (Zeile endet mit „ –  ")?
        if line.rstrip().endswith(DASH + "  ") or line.rstrip().endswith(DASH):
            out.append(line)
            continue
        m = RE_NACHSATZ.search(line)
        if not m:
            out.append(line)
            continue
        # Sicherheitscheck: kein Fortsetzungs-Wort
        if RE_KEIN.search(line):
            out.append(line)
            continue
        # Stelle des Nachsatzes: nach „ – "
        pos = m.start() + 3  # Länge von „ – " (Space, Dash, Space)
        before = line[:pos] + "  "   # 2 Leerzeichen = Markdown-Hard-Break
        after = line[pos:]
        out.append(before)
        out.append(after)
        changed += 1
    return "\n".join(out), changed


def main() -> int:
    dry = "--dry-run" in sys.argv
    files = (sorted(glob.glob(f"{BLOG_DIR}/content/posts/*/index.md"))
             + sorted(glob.glob(f"{BLOG_DIR}/content/pillar/*/index.md")))
    total = 0
    for f in files:
        content = open(f, encoding="utf-8").read()
        parts = content.split("---", 2)
        if len(parts) < 3:
            continue
        body = parts[2]
        new_body, n = fix_body(body)
        if n:
            total += n
            print(f"  {f.split('/')[-2]}: {n} Umbruch/Umbrüche")
            if not dry:
                open(f, "w", encoding="utf-8").write(parts[0] + "---" + parts[1] + "---" + new_body)
    print(f"\n{'DRY-RUN: ' if dry else ''}Fertig: {total} Umbrüche in {len(files)} Dateien.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
