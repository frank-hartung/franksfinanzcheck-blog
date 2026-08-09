#!/usr/bin/env python3
"""fix_dash_breaks.py – Dauerhafte Regel: Zeilenumbruch nach Gedankenstrich
vor erläuterndem Nachsatz (PROFI-LEVEL mit Kontext-Erkennung).

WARUM: Auf schmalen Bildschirmen bricht der Browser sonst oft VOR dem
Gedankenstrich um („…verschiedener Reisedauern" / „– die 10-Tage-Variante…").
Damit der Nachsatz sauber auf einer NEUEN Zeile beginnt, wird nach „ – "
ein Markdown-Hard-Break gesetzt (zwei Leerzeichen + Zeilenumbruch =
CommonMark-<br>).

REGEL (Umbruch setzen):
  NUR im normalen Fließtext und NUR, wenn nach dem Gedankenstrich ein
  ERLÄUTERNDER Nachsatz folgt (Artikel/Pronomen/Fragewort/Erläuterungs-Wort:
  die, der, das, ein, wer, was, man, es, das heißt, sprich, konkret, …).

KEIN Umbruch (und bestehende werden ZURÜCKGEBAUT):
  1) FAQ-BEREICHE (ab „## Häufige Fragen" / „## Häufig gestellte Fragen" /
     „## FAQ" bis zur nächsten Überschrift oder Dateiende): Antworten werden
     als Schema-JSON-LD (FAQPage) gerendert – dort sind <br> unschön.
  2) LISTENELEMENTE (Zeilen mit „- " / „* " / „1. "): Ein <li> mit erzwungenem
     Umbruch sieht in Aufzählungen unprofessionell aus.
  3) Tabellenzeilen („|"), Inline-Code („`"), Überschriften („#") – Titel
     werden nie zerrissen.
  4) Fortsetzungen (und, oder, für, mit, z. B., …) – z. B. bleibt die
     Affiliate-Disclosure kompakt.

Idempotent: Bereits korrekt gesetzte Umbrüche im Fließtext bleiben.

Aufruf:  python3 scripts/fix_dash_breaks.py          (alle Dateien)
         python3 scripts/fix_dash_breaks.py --dry-run (nur anzeigen)
"""
import glob
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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

# FAQ-Start: „## Häufige Fragen", „## Häufig gestellte Fragen", „## FAQ", …
RE_FAQ_START = re.compile(
    r"^#{1,6}\s*(Häufige Fragen|Häufig gestellte Fragen|Häufige Fragen \(FAQ\)|FAQ)\s*$",
    re.I)
# Umgebrochene Zeile: endet mit „ – " + mind. 1 Space (Hard-Break-Spur)
RE_BROKEN_END = re.compile(r"\u2013[ \u00a0]+$")
# Listenelement-Anfang
RE_LIST_ITEM = re.compile(r"^\s*(?:[-*]|\d+\.)\s+")


def fix_body(body: str) -> tuple[str, int]:
    """Wendet die Regel an. Liefert (neuer_body, anzahl)."""
    lines = body.split("\n")
    out: list[str] = []
    changed = 0
    in_faq = False
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]

        # Kontext-Tracking: FAQ-Bereich erkennen. Nur Überschriften der
        # Ebenen # und ## beenden ihn; ###-Fragen INNERHALB der FAQ
        # (z. B. "### Ist ein Stromwechsel wirklich kostenlos?") bleiben
        # im FAQ-Kontext – ihre Antworten gehören dazu.
        if re.match(r"^#{1,6}\s+", line):
            if RE_FAQ_START.match(line):
                in_faq = True
            elif re.match(r"^#{1,2}\s+", line):
                in_faq = False

        # KEIN-Umbruch-Kontext? (FAQ, Liste, Tabelle, Code, Überschrift)
        no_break_ctx = (
            in_faq
            or RE_LIST_ITEM.match(line)
            or "|" in line
            or "`" in line
            or line.lstrip().startswith("#")
        )

        if no_break_ctx:
            # Bestehende Umbrüche ZURÜCKBAUEN: Zeile endet mit „ –  " und die
            # nächste Zeile ist die Fortsetzung → zusammenführen.
            if RE_BROKEN_END.search(line) and i + 1 < n:
                nxt = lines[i + 1].strip()
                # Nächste Zeile darf nicht wieder eine umgebrochene Zeile sein
                if nxt and not RE_BROKEN_END.search(nxt):
                    merged = line.rstrip() + " " + nxt
                    out.append(merged)
                    changed += 1
                    i += 2
                    continue
            out.append(line)
            i += 1
            continue

        # Normaler Fließtext:
        # 1) Bereits umgebrochen? (idempotent – nichts tun)
        if RE_BROKEN_END.search(line):
            out.append(line)
            i += 1
            continue
        # 2) Neuer Umbruch-Kandidat?
        m = RE_NACHSATZ.search(line)
        if not m:
            out.append(line)
            i += 1
            continue
        if RE_KEIN.search(line):
            out.append(line)
            i += 1
            continue
        pos = m.start() + 3  # Länge von „ – " (Space, Dash, Space)
        before = line[:pos] + "  "
        after = line[pos:]
        out.append(before)
        out.append(after)
        changed += 1
        i += 1
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
        new_body, n = fix_body(parts[2])
        if n:
            total += n
            print(f"  {f.split('/')[-2]}: {n} Änderung(en)")
            if not dry:
                open(f, "w", encoding="utf-8").write(parts[0] + "---" + parts[1] + "---" + new_body)
    print(f"\n{'DRY-RUN: ' if dry else ''}Fertig: {total} Änderungen in {len(files)} Dateien.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
