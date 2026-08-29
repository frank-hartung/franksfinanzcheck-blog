#!/usr/bin/env python3
# ============================================================
#  UMBRUCH-GUARD – Premium-Zeilenumbruch für lange Komposita
#
#  ANLASS (29.08.2026, Premium-Befund Impressum):
#      „Verbraucherstreitbeilegung / Universalschlichtungsstelle“
#  Deutsche Monster-Komposita (24+ Zeichen) kennen im Deutschen
#  KEINE automatische Silbentrennung (Haus-Regel: hyphens: manual –
#  „Wörter werden nie getrennt“). Ohne Trennstelle bleibt dem
#  Browser nur der Notfall-Umbruch (word-break) – und der bricht
#  MITTEN im Wort: „Universalschlichtungsst“ / „elle“. Das sieht
#  kaputt aus, nicht premium.
#
#  LÖSUNG (deterministisch, keine KI, keine Wortliste nötig):
#    Weiche Trennstellen (U+00AD, soft hyphen) an Morphem-Grenzen
#    setzen – unsichtbar, solange nicht umgebrochen wird. Bricht
#    die Zeile, trennt der Browser dort und setzt einen korrekten
#    Bindestrich („Universal-“ / „schlichtungsstelle“).
#
#  REGELN:
#    U1  Wort >= 24 Zeichen und ohne U+00AD → Trennstellen an
#        Morphem-Grenzen (Kopf-Nomen VOR, Bestimmungswort NACH).
#    U2  Bruchstücke mindestens 5 Zeichen (Premium-Optik; Duden
#        erlaubt 3 – wir wollen keine Splitter).
#    U3  Fugen-s-Falle: kollidiert eine „NACH“-Stelle mit einer
#        „VOR“-Stelle (Abstand <= 3), gewinnt die VOR-Stelle.
#        („Verbraucherschlichtungs|stelle“ statt
#         „Verbraucherschlichtung|sstelle“)
#    U4  ANKER-BEWEIS: In Überschriften wird nur gesetzt, wenn der
#        Goldmark-Anker vorher/nachher IDENTISCH ist (Ankerlogik
#        aus heading_guard.goldmark_slug – U+00AD zählt nicht als
#        Buchstabe, fällt also weg). Externe Links/Pins brechen nie.
#    U5  SCHUTZ: Frontmatter, Code (`` und ```), HTML-Tags,
#        Link-Ziele, URLs, /go/-Pfade, E-Mail-Adressen.
#    U6  IDEMPOTENT: zweiter Lauf findet nichts mehr.
#
#  AUFRUF:
#    python3 scripts/umbruch_guard.py                # Report (Check)
#    python3 scripts/umbruch_guard.py --fix          # heilen
#    python3 scripts/umbruch_guard.py --dry-run      # zeigen
#    python3 scripts/umbruch_guard.py --file X.md    # eine Datei
#    python3 scripts/umbruch_guard.py --selftest     # eingefrorene Fälle
#
#  AUSGABE: UMBRUCH-REPORT.md
#  EXIT: 0 = sauber/geheilt · 1 = Funde ohne --fix · 2 = Selbsttest fehlerhaft
# ============================================================

import datetime
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("GITHUB_WORKSPACE") or Path(__file__).resolve().parent.parent)
CONTENT_DIR = ROOT / "content"
REPORT = ROOT / "UMBRUCH-REPORT.md"
HISTORY = ROOT / "data" / "umbruch_guard_history.jsonl"
SCRIPTS_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(SCRIPTS_DIR))
try:  # Anker-Beweis (U4) – Haus-Logik aus der Überschriften-Wache
    from heading_guard import goldmark_slug
except Exception:  # pragma: no cover – Wache fehlt: dann keine Überschrift-Heilung
    goldmark_slug = None

SHY = "\u00ad"               # U+00AD – weiche Trennstelle
MIN_LEN = 24                 # U1: ab dieser Wortlänge lohnt eine Trennstelle
MIN_PART = 5                 # U2: kürzestes Bruchstück
NEAR = 3                     # U3: Kollisionsabstand (Fugen-s)

DO_FIX = "--fix" in sys.argv
DRY_RUN = "--dry-run" in sys.argv

# ---------------------------------------------------------------- Morpheme
# Kopf-Nomen (typisch hinten) – Trennstelle DAVOR
KOEPFE = [
    "versicherung", "verfahren", "beilegung", "schlichtung", "gebühren",
    "vergleich", "abrechnung", "gesetz", "quote", "klasse", "pflichten",
    "findung", "laufzeit", "kündigung", "erklärung", "tarif", "entgelte",
    "elektronik", "einstellungen", "überweisungen", "verzicht", "verletzung",
    "anbieter", "berechnung", "erstattung", "verbrauch", "kosten", "stelle",
    "rahmen", "vertrag", "konto", "kredit", "schutz", "rechte", "beratung",
]
# Bestimmungswörter (typisch vorn) – Trennstelle DANACH
BESTIMMUNG = [
    "wohngebäude", "privat", "elementar", "unterhaltung", "browser",
    "aufbewahrung", "entscheidungs", "lebenshaltung", "bereitstellungs",
    "echtzeit", "heizkosten", "mindest", "sonder", "grundversorgungs",
    "telekommunikations", "weiterempfehlungs", "schadenfreiheits",
    "verbraucher", "streit", "universal", "schaden", "haftpflicht",
    "versicherungs", "datenschutz", "konto", "führung", "kündigungs",
    "unterversicherungs", "vertrags", "tierhalter", "hausrat", "zahnzusatz",
]

# ---------------------------------------------------------------- Schutz (U5)
PROTECTED = [
    re.compile(r"```.*?```", re.S),                       # Code-Blöcke
    re.compile(r"`[^`\n]*`"),                             # Inline-Code
    re.compile(r"<[^>\n]*>"),                             # HTML-Tags/Attribute
    re.compile(r"\]\([^)\n]*\)"),                         # Markdown-Linkziele
    re.compile(r"\b(?:https?://|www\.)\S+"),              # URLs
    re.compile(r"/go/[A-Za-z0-9\-_/]+"),                  # Affiliate-Gateway
    re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),          # E-Mail
]
WORD_RX = re.compile(r"[A-Za-zÄÖÜäöüß]{%d,}" % MIN_LEN)


def mask_protected(line: str) -> tuple[str, list[tuple[int, int]]]:
    """Ersetzt geschützte Bereiche durch Platzhalter gleicher Länge."""
    spans: list[tuple[int, int]] = []
    for rx in PROTECTED:
        for m in rx.finditer(line):
            spans.append((m.start(), m.end()))
    if not spans:
        return line, []
    spans.sort()
    buf = list(line)
    for a, b in spans:
        for i in range(a, b):
            buf[i] = "\x00"
    return "".join(buf), spans


def trennstellen(word: str) -> list[int]:
    """U1–U3: liefert sortierte Trenn-Positionen (Index = Bruchstelle)."""
    low = word.lower()
    vor: list[int] = []      # U3: VOR einem Kopf-Nomen (bevorzugt)
    nach: list[int] = []     # NACH einem Bestimmungswort

    def ok(i: int) -> bool:
        return MIN_PART <= i <= len(word) - MIN_PART

    for m in KOEPFE:
        start = 0
        while True:
            i = low.find(m, start)
            if i < 0:
                break
            if ok(i):
                vor.append(i)
            start = i + 1
    for m in BESTIMMUNG:
        start = 0
        while True:
            i = low.find(m, start)
            if i < 0:
                break
            j = i + len(m)
            if ok(j):
                nach.append(j)
            start = i + 1

    vor = sorted(set(vor))
    nach = sorted(set(nach))
    # Fugen-s-Falle (U3): NACH-Stellen, die dicht an einer VOR-Stelle
    # liegen, verlieren – sonst entsteht „…schlichtung|sstelle“.
    gewaehlt = sorted(set(vor))
    for j in nach:
        if all(abs(j - v) > NEAR for v in vor):
            gewaehlt.append(j)
    return sorted(set(gewaehlt))


def umbrechen(word: str) -> str:
    """Setzt U+00AD an allen Trennstellen (idempotent, U6)."""
    if SHY in word or len(word) < MIN_LEN:
        return word
    pos = trennstellen(word)
    if not pos:
        return word
    out = word
    for i in sorted(pos, reverse=True):
        if out[i - 1:i] == SHY or out[i:i + 1] == SHY:
            continue
        out = out[:i] + SHY + out[i:]
    return out


def heal_line(line: str, anker_pruefen: bool) -> tuple[str, list[dict], list[dict]]:
    """Heilt eine Zeile. Rückgabe: (neue Zeile, gesetzt[], blockiert[])."""
    masked, _spans = mask_protected(line)
    if "\x00" in masked and not WORD_RX.search(masked.replace("\x00", " ")):
        return line, [], []

    gesetzt, blockiert = [], []
    treffer = [m for m in WORD_RX.finditer(masked) if "\x00" not in m.group(0)]
    if not treffer:
        return line, [], []

    ist_ueberschrift = anker_pruefen and line.lstrip().startswith("#")
    anker_vor = goldmark_slug(line) if (ist_ueberschrift and goldmark_slug) else None

    out = line
    shift = 0
    for m in treffer:
        alt = m.group(0)
        neu = umbrechen(alt)
        if neu == alt:
            continue
        a, b = m.start() + shift, m.end() + shift
        kandidat = out[:a] + neu + out[b:]
        if anker_vor is not None:
            anker_nach = goldmark_slug(kandidat)
            if anker_nach != anker_vor:              # U4
                blockiert.append({"wort": alt, "anker_vor": anker_vor,
                                  "anker_nach": anker_nach})
                continue
        out = kandidat
        shift += len(neu) - len(alt)
        gesetzt.append({"wort": alt, "neu": neu})
    return out, gesetzt, blockiert


def heal_text(text: str) -> tuple[str, list[dict], list[dict]]:
    """Heilt eine Datei (Frontmatter bleibt unangetastet, U5)."""
    lines = text.split("\n")
    gesetzt, blockiert = [], []
    start = 0
    if lines and lines[0].strip() == "---":          # Frontmatter überspringen
        for i in range(1, len(lines)):
            if lines[i].strip() in ("---", "..."):
                start = i + 1
                break
    for i in range(start, len(lines)):
        neu, g, b = heal_line(lines[i], anker_pruefen=True)
        if g or b:
            for e in g:
                e["zeile"] = i + 1
            for e in b:
                e["zeile"] = i + 1
            gesetzt.extend(g)
            blockiert.extend(b)
            lines[i] = neu
    return "\n".join(lines), gesetzt, blockiert


def scan_file(path: Path) -> tuple[list[dict], list[dict]]:
    text = path.read_text(encoding="utf-8")
    _neu, gesetzt, blockiert = heal_text(text)
    for e in gesetzt + blockiert:
        e["file"] = str(path.relative_to(ROOT))
    return gesetzt, blockiert


def protokoll(eintraege: list[dict]) -> None:
    """Audit-Spur: jede Heilung landet in data/umbruch_guard_history.jsonl."""
    if not eintraege:
        return
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with HISTORY.open("a", encoding="utf-8") as fh:
        for e in eintraege:
            fh.write(json.dumps({
                "ts": ts, "file": e.get("file"), "zeile": e.get("zeile"),
                "wort": e.get("wort"), "neu": e.get("neu"),
            }, ensure_ascii=False) + "\n")


def letzte_heilung() -> str:
    if not HISTORY.exists():
        return ""
    lines = [l for l in HISTORY.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not lines:
        return ""
    try:
        erste = json.loads(lines[0])
        letzte = json.loads(lines[-1])
    except Exception:
        return ""
    return (f"**Letzte Heilung (Audit-Spur):** {len(lines)} Trennstelle(n), "
            f"zuletzt {letzte.get('ts', '?')[:16].replace('T', ' ')} UTC "
            f"– Details: `data/umbruch_guard_history.jsonl`")

def write_report(funde: list[dict], blockiert: list[dict], geheilt: int,
                 modus: str) -> None:
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    worte: dict[str, int] = {}
    for e in funde:
        worte[e["neu"]] = worte.get(e["neu"], 0) + 1
    top = sorted(worte.items(), key=lambda kv: (-kv[1], kv[0]))[:25]

    L = [f"# ↔️ UMBRUCH-REPORT (umbruch_guard.py)", "",
         f"**Stand:** {now} · Modus: {modus}", "",
         f"**Trennstellen gefunden:** {len(funde)} in "
         f"{len({e['file'] for e in funde})} Dateien"
         f"{f' · **geheilt:** {geheilt}' if geheilt else ''}", "",
         "## 🔤 Häufigste behandelte Komposita", ""]
    if top:
        for w, c in top:
            L.append(f"- `{w.replace(SHY, '·')}` – {c}×")
    else:
        L.append("_Keine Funde – alle langen Komposita tragen Trennstellen._")
    audit = letzte_heilung()
    if audit:
        L += ["", audit, ""]
    if funde:
        L += ["", "## %s (Detail)" % ("✅ Gesetzt" if geheilt else "🔎 Kandidaten (--fix setzt sie)"), ""]
    for e in funde[:200]:
        L.append(f"- `{e['file']}` Zeile {e['zeile']}: "
                 f"`{e['wort']}` → `{e['neu'].replace(SHY, '·')}`")
    if blockiert:
        L += ["", "## ⛔ Blockiert (Anker-Beweis U4)", ""]
        for e in blockiert:
            L.append(f"- `{e['file']}` Zeile {e['zeile']}: `{e['wort']}` – "
                     f"Anker `{e['anker_vor']}` ≠ `{e['anker_nach']}`")
    L += ["",
          "---",
          "_Deterministisch: weiche Trennstelle (U+00AD) an Morphem-Grenzen, "
          "ab 24 Zeichen, Bruchstücke ab 5 Zeichen. Geschützt: Frontmatter, "
          "Code, HTML, Linkziele, URLs, E-Mails. Überschriften nur mit "
          "Anker-Beweis (U4). Keine automatische Silbentrennung im CSS "
          "(Haus-Regel: hyphens: manual)._", ""]
    REPORT.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L[:14]))


# ------------------------------------------------------------------ Selbsttest
SELFTEST_CASES = [
    ("Verbraucherschlichtungsstelle", "Verbraucher­schlichtungs­stelle"),
    ("Universalschlichtungsstelle", "Universal­schlichtungs­stelle"),
    ("Verbraucherstreitbeilegung", "Verbraucher­streit­beilegung"),
    ("Streitbeilegungsverfahren", "Streit­beilegungs­verfahren"),
    # Unter der Schwelle (23 < 24 Zeichen) → bleibt unangetastet:
    ("Wohngebäudeversicherung", "Wohngebäudeversicherung"),
    ("Privathaftpflichtversicherung", "Privat­haftpflicht­versicherung"),
    ("Elementarschadenversicherung", "Elementar­schaden­versicherung"),
    ("Kurz", "Kurz"),  # zu kurz → unangetastet
]


def selftest() -> int:
    fehler = []
    for alt, erwartet in SELFTEST_CASES:
        got = umbrechen(alt)
        if got != erwartet:
            fehler.append(f"{alt}: erwartet {erwartet.replace(SHY, '·')!r}, "
                          f"bekommen {got.replace(SHY, '·')!r}")
        if umbrechen(got) != got:  # U6 Idempotenz
            fehler.append(f"{alt}: nicht idempotent")
    # Schutzzonen
    if heal_line("Siehe https://example.com/Privathaftpflichtversicherung jetzt",
                 True)[0] != "Siehe https://example.com/Privathaftpflichtversicherung jetzt":
        fehler.append("URL-Schutz (U5) greift nicht")
    if SHY in heal_line("`Privathaftpflichtversicherung`", True)[0]:
        fehler.append("Inline-Code-Schutz (U5) greift nicht")
    if SHY in heal_line("- [x](Privathaftpflichtversicherung)", True)[0]:
        fehler.append("Linkziel-Schutz (U5) greift nicht")
    # Anker-Beweis (U4)
    if goldmark_slug:
        h = "## Verbraucherstreitbeilegung / Universalschlichtungsstelle"
        neu, g, b = heal_line(h, True)
        if not g or b:
            fehler.append("Überschrift-Heilung (U4) blockiert zu Unrecht")
        elif goldmark_slug(neu) != goldmark_slug(h):
            fehler.append("Anker-Beweis (U4) verletzt")
    if fehler:
        print("SELBSTTEST FEHLERHAFT:")
        for f in fehler:
            print("  -", f)
        return 2
    print("Selbsttest OK: %d Fälle, idempotent, Schutzzonen + Anker-Beweis grün."
          % len(SELFTEST_CASES))
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()

    if "--file" in sys.argv:
        idx = sys.argv.index("--file")
        files = [Path(sys.argv[idx + 1]).resolve()]
    else:
        files = sorted(CONTENT_DIR.rglob("*.md"))

    funde: list[dict] = []
    blockiert: list[dict] = []
    geheilt = 0
    for p in files:
        g, b = scan_file(p)
        funde.extend(g)
        blockiert.extend(b)
        if g and DO_FIX and not DRY_RUN:
            text = p.read_text(encoding="utf-8")
            neu, _g, _b = heal_text(text)
            if neu != text:
                p.write_text(neu, encoding="utf-8")
                geheilt += 1
    if geheilt:
        protokoll(funde)

    write_report(funde, blockiert, geheilt,
                 "FIX" if (DO_FIX and not DRY_RUN) else
                 ("DRY-RUN" if DRY_RUN else "CHECK"))
    if funde and not DO_FIX:
        print(f"\n{len(funde)} Trennstellen möglich – mit --fix anwenden.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
