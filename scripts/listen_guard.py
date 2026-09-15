#!/usr/bin/env python3
# ============================================================
#  LISTEN-GUARD – L1 geleimte Listenpunkte, L2 Marker-Stil im Block
#  (neu am Regelwerk 15.09.2026, Fund beim Nacharbeiten der Hold-Artikel)
#
#  ANLASS: Im Bestand stehen Listen, deren Punkte in EINER Zeile stehen –
#  „* Punkt eins. * Punkt zwei“ oder „1. **Schritt** (… ). 2. **Schritt** …“.
#  Markdown macht daraus einen einzigen Absatz: die Leser sehen Sterne und
#  Zahlen im Fließtext statt einer Aufzählung. Nachgemessen 41 solche Punkte in
#  11 Artikeln (8 live), erzeugt von früheren Generator-Generationen. Der Fund
#  fiel beim redaktionellen Nacharbeiten von `finanzielle-freiheit` auf – dort
#  waren es 7.
#
#  AUFTRAG:
#    L1 GELEIMTER PUNKT (heilbar): steht in einer Zeile, die mit einem
#        Listenmarker beginnt, nach einem Satzzeichen [.!?] ein weiterer Marker
#        („* “, „- “ oder „3. “), wird dort umgebrochen. Der Splitter schneidet
#        NUR vor dem Marker ab – der Marker bleibt in seinem Stück stehen. Ein
#        Heiler, der Marker selbst vorsetzen muss, war der Fehler, den dieses
#        Skript nicht wiederholen darf (15.09. real passiert: zwei Punkte ihres
#        Sterns beraubt).
#    L2 MARKER-STIL IM BLOCK (heilbar): mischt ein zusammenhängender Block auf
#        EINER Einrückungsstufe die Kugel-Marker („- “ und „* “), gilt die
#        Mehrheit der Stufe; nummerierte Listen je Familie („.“ gegen „)“)
#        normalisiert, nie Familie-übergreifend. Gemischte STUFEN sind kein
#        Befund – „* außen / - darin“ ist korrektes Markdown.
#
#  WAS DIE WACHE NICHT TUT:
#    * keine Mathe-Zeile zerlegen: „- 40 Watt * 24 Stunden = 960 Wh“ enthält ein
#      „*“, aber kein Satzzeichen davor – und „ab 1. - 5 %“ bleibt in Ruhe, weil
#      nach dem Marker ein nackter Wert steht, kein listenüblicher Anfang.
#    * nichts innerhalb ```-Blöcken und in Tabellen.
#    * kein Heilen ohne Wortbeweis: nach der Heilung muss die Folge der Wörter
#      unverändert sein (L1) bzw. nur in den Marker-Anfängen abweichen (L2).
#      Sonst wird der Fund gemeldet und die Datei nicht angefasst.
#
#  SABOTAGE-SCHUTZ: eingefrorener Selbsttest, Abweichung -> Exit 2.
#
#  Aufruf:
#    python3 scripts/listen_guard.py                # Bericht (schreibt nicht)
#    python3 scripts/listen_guard.py --fix          # heilt im Korpus
#    python3 scripts/listen_guard.py --fix --file content/posts/<slug>/index.md
#    python3 scripts/listen_guard.py --selftest     # Sabotage-Schutz
#    python3 scripts/listen_guard.py --json         # Report als JSON
#    --dry-run / --new-only: vom Doktor durchgereicht, Bericht wie ohne Flag
#
#  Eingehängt: scripts/blog_doctor.py (Phase A-Text, --fix im scharfen Lauf)
# ============================================================

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "content" / "posts"

RAUM = r"[ \t\u00a0\u202f]"
# Ein Zeilenanfang, der eine Aufzählung eröffnet (auch Task-Listen „- [ ] “).
LISTEN_ANFANG = re.compile(rf"^{RAUM}*(?:[-*+]|\d+[.)]){RAUM}+")
# Der geleimte Punkt: Satzzeichen, Leerraum, einzelner Marker, Leerraum,
# listenüblicher Anfang (fett, Kursiv-Anführungszeichen, Task-Kästchen,
# Großbuchstabe oder eine neue nummerierte Zeile).
GLUEICH = re.compile(
    rf"(?<=[.!?]){RAUM}+(?:(?<!\*)([-*+])(?!\*)|(\d+)[.)]){RAUM}+"
    rf"(?=(?:\*\*|„|\[[ xX]\]|[A-ZÄÖÜß]|\d{{1,5}}[.)]))"
)
EINZUG = re.compile(rf"^({RAUM}*)")
CODE_ZAEUN = re.compile(r"^\s*(```|~~~)")
TABELLE = re.compile(r"^\s*\|")
KUGEL = re.compile(rf"^{RAUM}*([-*+]){RAUM}")
NUMMER_STIL = re.compile(rf"^{RAUM}*\d+([.)]){RAUM}")
WORT = re.compile(r"\S+")
MARKER_CHARS = "-*+"


def zeilen_arten(text: str):
    """(index, zeile, gespuetzt) – Code- und Tabellenzeilen sind gesperrt."""
    code = False
    for i, line in enumerate(text.split("\n")):
        if CODE_ZAEUN.match(line):
            code = not code
            yield i, line, True
            continue
        yield i, line, code or bool(TABELLE.match(line))


def funde_zeile(line: str) -> list:
    """Startpositionen der geleimten Punkte in einer Listenzeile (leer = sauber)."""
    if not LISTEN_ANFANG.match(line):
        return []
    return [m.start() for m in GLUEICH.finditer(line)]


def teile_zeile(line: str) -> list:
    """Zeile an den Geleimtheiten aufschneiden; der Marker bleibt im Folgestück."""
    pos = funde_zeile(line)
    if not pos:
        return [line]
    einzug = EINZUG.match(line).group(1)
    stuecke, vorher = [], 0
    for p in pos + [len(line)]:
        brocken = line[vorher:p]
        stuecke.append(brocken if not stuecke else einzug + brocken.strip())
        vorher = p
    return stuecke


def bloecke(text: str) -> list:
    """Nummernblöcke zusammenhängender Listenzeilen (Listenanfänge, >1 Zeile)."""
    block, out = [], []
    for i, line, gesperrt in zeilen_arten(text):
        if not gesperrt and LISTEN_ANFANG.match(line):
            block.append(i)
            continue
        if len(block) > 1:
            out.append(block)
        block = []
    if len(block) > 1:
        out.append(block)
    return out


def stil_funde(zeilen: list, block: list) -> list:
    """L2: gemischter Marker-Stil -> [(zeilen, alt, ziel)].

    Verglichen wird NUR innerhalb derselben Einrückungsstufe und derselben
    Familie: „* außen / - darin“ ist korrektes Markdown-Nesting und kein
    Befund (15.09. erster Entwurf der Regel hätte ihn geheilt). Der Ziel-Marker
    ist die Mehrheit der Stufe, bei Gleichstand der Marker des ersten Eintrags
    – Autorenwille vor Haus-Kanon, weil der Bestand beide Kugeln gleichwertig
    führt (320 „-“ gegen 240 „*“ auf erster Ebene)."""
    gruppen = {}
    for i in block:
        line = zeilen[i]
        ebene = len(EINZUG.match(line).group(1))
        m = KUGEL.match(line)
        familie = "kugel"
        if not m:
            m = NUMMER_STIL.match(line)
            familie = "nummer"
        if not m:
            continue
        gruppen.setdefault((familie, ebene), {}).setdefault(m.group(1), []).append(i)
    out = []
    for (_familie, _ebene), stile in gruppen.items():
        if len(stile) < 2:
            continue
        ziel = sorted(stile.items(), key=lambda kv: (-len(kv[1]), kv[1][0]))[0][0]
        for stil, idx in stile.items():
            if stil != ziel:
                out.append((idx, stil, ziel))
    return out


def heilen(text: str):
    """(neuer Text, Befunde). Befund = (zeile, regel, meldung)."""
    zeilen = text.split("\n")
    meldungen = []

    # L1 – geleimte Punkte ausgeleimt
    neu = []
    for _i, line, gesperrt in zeilen_arten(text):
        stuecke = [line] if gesperrt else teile_zeile(line)
        if len(stuecke) > 1:
            meldungen.append((_i + 1, "L1", f"{len(stuecke) - 1} Punkt/Punkte ausgeleimt"))
        neu.extend(stuecke)

    # L2 – Marker-Stil im Block, auf dem bereits geleimten Text
    for block in bloecke("\n".join(neu)):
        for idx, alt, ziel in stil_funde(neu, block):
            for i in idx:
                alt_text = neu[i]
                neu[i] = re.sub(rf"^({RAUM}*)[{MARKER_CHARS}]", rf"\g<1>{ziel}",
                                alt_text, count=1)
                meldungen.append((i + 1, "L2", f"Marker {alt!r} → {ziel!r} "
                                               f"(Mehrheit auf dieser Ebene)"))
    if not meldungen:
        return text, []

    # Wortbeweis: L1 darf kein Wort bewegen, L2 höchstens die Marker-Anfänge.
    vor = WORT.findall(text)
    nach = WORT.findall("\n".join(neu))
    if len(vor) != len(nach):
        return text, [(0, "BELEG", f"Heilung verworfen – Wortbeweis: {len(vor)} Wörter "
                                  f"vorher, {len(nach)} nachher")]
    for a, b in zip(vor, nach):
        gleich = a == b or (len(a) == len(b) == 1 and a in MARKER_CHARS and b in MARKER_CHARS)
        if not gleich:
            return text, [(0, "BELEG", f"Heilung verworfen – Wortbeweis: „{a[:24]}“ "
                                      f"wurde „{b[:24]}“, das war kein Marker")]
    return "\n".join(neu), meldungen


# ------------------------------------------------------------
# SELBSTTEST (eingefroren): Abweichung -> Exit 2
# ------------------------------------------------------------
FELLEN = [
    # name, text, erwartete Befunde, erwartete Zeilen, Pflichtfragment (None = unverändert)
    ("sauber", "Ein normaler Absatz.\n\n* Punkt eins\n* Punkt zwei\n", 0, 4, None),
    ("nesten-ruhe", "* außen\n  - darin\n  - darin zwei\n* außen zwei\n", 0, 4, None),
    ("kugel-geleimt", "* Punkt eins. * Punkt zwei\n", 1, 2, "* Punkt zwei"),
    ("nummeriert-geleimt", "1. **Schritt** (alpha). 2. **Schritt** (beta).\n",
     1, 2, "2. **Schritt** (beta)."),
    ("taskliste-geleimt", "- [ ] **Prüfen:** Wert notieren. - [ ] **Quittieren:** abheften.\n",
     1, 2, "- [ ] **Quittieren:** abheften."),
    ("mathe-ruhe", "- 40 Watt * 24 Stunden = 960 Wattstunden pro Tag.\n", 0, 1, None),
    ("abkuerzung-ruhe", "- Der Wert gilt ab 1. - 5 % steigen später nicht.\n", 0, 1, None),
    ("code-ruhe", "```\n* a. * b\n```\n", 0, 3, None),
    ("tabelle-ruhe", "| Spalte | 1. eins. 2. zwei |\n", 0, 1, None),
    ("marker-stil", "- eins\n* zwei\n- drei\n", 1, 3, "- zwei"),
    ("einzug-erhaelt", "  * eins\n  * zwei\n", 0, 2, None),
    ("doppel-punkt-ruft-nicht", "* Preis: 3 € - 5 € je nach Region\n", 0, 1, None),
]


def selbsttest() -> list:
    fehler = []
    for name, text, exp_funde, exp_zeilen, pflicht in FELLEN:
        neu, meld = heilen(text)
        if len(meld) != exp_funde:
            fehler.append(f"  Fall '{name}': erwartet {exp_funde} Befund(e), bekam "
                          f"{len(meld)} ({meld[:1]})")
            continue
        got = len(neu.rstrip("\n").split("\n"))
        if got != exp_zeilen:
            fehler.append(f"  Fall '{name}': erwartet {exp_zeilen} Zeilen, bekam {got}")
        if pflicht and pflicht not in neu:
            fehler.append(f"  Fall '{name}': „{pflicht}“ fehlt in der Heilung – Marker "
                          f"oder Text verloren:\n    {neu!r}")
        if pflicht is None and neu.rstrip("\n") != text.rstrip("\n"):
            fehler.append(f"  Fall '{name}': unbeteiligter Text verändert")
    # Idempotenz: zweites Heilen findet nichts mehr
    text = "* eins. * zwei\n\n1. **A.** a). 2. **B.** b)\n"
    einmal, _ = heilen(text)
    zweimal, meld = heilen(einmal)
    if meld or zweimal != einmal:
        fehler.append("  Idempotenz kaputt: zweiter Lauf heilt nochmal")
    return fehler


def report_zeile(slug: str, meld: list, geheilt: bool) -> str:
    zeilen = "\n".join(f"      {r} Zeile {z}: {t}" for z, r, t in meld if z)
    return f"  {'🔧' if geheilt else '🟡'} {slug}: {len(meld)} Befund(e)" + (f"\n{zeilen}" if zeilen else "")


def main() -> int:
    arg = sys.argv[1:]
    if "--selftest" in arg:
        f = selbsttest()
        if f:
            print("🛑 LISTEN-GUARD-SELBSTTEST FEHLGESCHLAGEN – Wache geschützt.")
            print("\n".join(f))
            return 2
        print(f"✅ Listen-Guard-Selbsttest: {len(FELLEN) + 1} Fälle grün "
              f"(Heilung, Ruhe, Idempotenz).")
        return 0

    do_fix = "--fix" in arg
    as_json = "--json" in arg
    if "--file" in arg:
        dateien = [Path(arg[arg.index("--file") + 1])]
    else:
        dateien = sorted(POSTS.glob("*/index.md"))

    details, blockiert, geheilte_dateien = [], [], 0
    for pfad in dateien:
        try:
            text = pfad.read_text(encoding="utf-8")
        except OSError as exc:
            blockiert.append(f"{pfad.parent.name}: nicht lesbar ({exc})")
            continue
        neu, meld = heilen(text)
        if not meld:
            continue
        slug = pfad.parent.name
        verwurf = [t for _z, _r, t in meld if "verworfen" in t]
        if verwurf:
            blockiert.extend(f"{slug}: {v}" for v in verwurf)
        elif do_fix:
            nach, nach_meld = heilen(neu)
            if nach_meld:
                blockiert.append(f"{slug}: Nachkontrolle meldet nach dem Schreiben noch "
                                 f"{len(nach_meld)} Befund(e) – Heilung nicht abgeschlossen")
                continue
            pfad.write_text(neu, encoding="utf-8")
            geheilte_dateien += 1
        for z, r, t in meld:
            details.append({"slug": slug, "zeile": z, "regel": r, "meldung": t})
        if not as_json:
            print(report_zeile(slug, meld, bool(do_fix and not verwurf)))

    if as_json:
        print(json.dumps({"befunde": len(details),
                          "artikel": len({d["slug"] for d in details}),
                          "geheilt": geheilte_dateien, "blockiert": blockiert,
                          "details": details}, ensure_ascii=False, indent=1))
    if blockiert:
        print("🛑 Listen-Guard: Heilung zurückgehalten (Wortbeweis oder Lesefehler):")
        for b in blockiert:
            print("   -", b)
        return 2
    if not as_json:
        print(f"🧾 Listen-Guard: {len(details)} Befund(e) in "
              f"{len({d['slug'] for d in details})} Artikel(n)"
              + (f", {geheilte_dateien} Datei(en) geheilt, nachgeprüft: 0 Befunde."
                 if do_fix else " – Bericht, nichts geschrieben."))
    if do_fix and geheilte_dateien:
        return 0
    return 1 if details else 0


if __name__ == "__main__":
    sys.exit(main())
