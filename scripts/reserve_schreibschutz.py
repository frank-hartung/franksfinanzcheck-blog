#!/usr/bin/env python3
"""Bytegebundene Reserve-Entwürfe sind für Hygiene-Heiler schreibgeschützt (#900).

WARUM ES DIESEN SCHUTZ GIBT
---------------------------
`data/reserve-readiness.json` belegt jeden READY-Kandidaten mit der SHA-256
der exakten `index.md`. Der Nachweis ist damit keine Meinung, sondern eine
Byte-Aussage: „genau diese Datei wurde mit Hugo + Hunspell gemessen“.

Jeder Schreiber, der danach noch am Entwurf dreht – eine Transparenz-Zeile
einfügen, Keywords entdoppeln, Pin-Texte glätten –, entwertet diese Aussage.
Beide Vorgänge sehen für sich grün aus; der Widerspruch fällt erst im
nächsten Gate auf (#462 „Zertifikats-Drift“, #634, #900).

DER VORFALL VOM 30.10.2026
--------------------------
Der Pinterest-Watchdog heilte drei zertifizierte Reserve-Entwürfe
(`spam_guard.fix_blog` setzte die Transparenz-Zeile, die Pin-Heiler kürzten
`keywords`) und committete das Ergebnis. Der Nachweis zeigte danach auf
Bytes, die es nicht mehr gab. Die Nachmessung ist Sache der Reserve-Kette
(sie hat Hugo + Hunspell), nicht Sache der Hygiene-Heiler.

DIE REGEL
---------
`draft: true` **und** `reserve: true` im Frontmatter = bytegebunden.
Wer schreiben will, fragt vorher `ist_bytegebunden()`. Der Heiler meldet
den Fund weiter (nichts wird verschwiegen), schreibt aber nicht.

Die Reserve-Kette selbst (Produktion, Veredelung, Zertifizierung) benutzt
diesen Schutz bewusst NICHT: sie darf schreiben, weil sie unmittelbar
danach neu misst.
"""
from __future__ import annotations

import re
from pathlib import Path

# Beide Marken stehen im Frontmatter; eine allein genügt nicht. `draft: true`
# ohne `reserve: true` ist ein normaler Entwurf (Heiler dürfen ihn anfassen),
# `reserve: true` ohne `draft: true` ist bereits ausgeliefert (dann ist der
# Nachweis ohnehin verbraucht).
_BYTE_MARKEN = ("draft", "reserve")


def frontmatter(text: str) -> str:
    """Frontmatter-Block ohne die beiden `---`-Zeilen (rein textuell).

    Bewusst ohne PyYAML: der Schutz muss in jedem Heiler laufen, auch dort,
    wo nur die Standardbibliothek installiert ist. Ein Parser-Ausfall darf
    den Schutz nicht abschalten.
    """
    if not text.startswith("---"):
        return ""
    ende = text.find("\n---", 3)
    return text[3:ende] if ende != -1 else ""


def ist_bytegebunden(text: str) -> bool:
    """True, wenn der Text ein zertifikatsgebundener Reserve-Entwurf ist."""
    block = frontmatter(text.replace("\r\n", "\n"))
    if not block:
        return False
    for marke in _BYTE_MARKEN:
        if not re.search(rf"(?m)^{marke}:\s*true\s*$", block):
            return False
    return True


def geschuetzte_slugs(posts_dir: Path | str) -> set[str]:
    """Alle bytegebundenen Entwürfe im Bestand (für Berichte und Tests)."""
    wurzel = Path(posts_dir)
    treffer: set[str] = set()
    for pfad in sorted(wurzel.glob("*/index.md")):
        try:
            text = pfad.read_text(encoding="utf-8")
        except OSError:
            continue
        if ist_bytegebunden(text):
            treffer.add(pfad.parent.name)
    return treffer


def schutzvermerk(slug: str, quelle: str) -> str:
    """Eine Meldung, die den Fund sichtbar macht, ohne ihn zu verschweigen."""
    return (f"{slug}: unangetastet – bytegebundener Reserve-Entwurf "
            f"(draft + reserve); Nachmessung ist Sache der Reserve-Kette "
            f"(reserve_recert.py --fix), nicht von {quelle}")
