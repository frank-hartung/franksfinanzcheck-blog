#!/usr/bin/env python3
"""heading_anchor_guard.py — Wache gegen Ankersymbole in Überschriften.

Befund 10.09.2026 (Frank): In der Kurzfassung stand im ganzen Blog hinter
JEDEM Eintrag ein „§“. Ursache war der Premium-Knopf „Link zu diesem
Abschnitt kopieren“: Er trug das „§“ als TEXTKNOTEN direkt in der
Überschrift. Alles, was Überschriften-Text ausliest, bekam es dadurch
angehängt — Kurzfassung („In diesem Artikel“), Tabellen-Titel,
Klartext-Kopie, Mini-Verzeichnis, die Vorlese-Engine (sprach
„… Paragraph“), der Überschriften-Name für Screenreader und die
Suchmaschinen (Überschriften sind ein Ranking-Signal).

Repariert ist das an der Quelle (Symbol statt Glyphe). Diese Wache sichert
die Reparatur DAUERHAFT ab — fünf Schichten:

  1. QUELLE   ff-premium.js setzt kein Textzeichen in den Anker-Knopf:
              Inline-SVG statt Glyphe, `data-ff-skip-read` für
              Lesemaschinen, `.ff-heading-text` + `aria-labelledby`
              für einen sauberen Überschriften-Namen.
  2. ENGINE   ff-voice.js filtert Bedienelemente, versteckte Knoten und
              Anker aus jedem gelesenen Text (READ_SKIP_SELECTOR) und
              nimmt Überschriften-Texte über `headingTextOf()`.
  3. THEME    der Anker des Themes bleibt für Lesemaschinen unsichtbar
              (`hidden` + `aria-hidden`), nie als nacktes Zeichen.
  4. BAU      im gebauten public/ endet KEINE Überschrift auf ein
              SICHTBARES Ankersymbol und kein sichtbares <a>/<button>
              trägt „§“/„#“ als Text. Der versteckte Theme-Anker ist
              legitim und bleibt ausgenommen (läuft nur, wenn public/
              vorhanden ist; `--selftest` prüft die Logik ohne Hugo).
  5. TEST     die Regressionsgruppe „Abschnitts-Link“ ist vorhanden und
              das Lesehilfen-Gate führt diese Wache aus.

Aufruf: python3 scripts/heading_anchor_guard.py
        python3 scripts/heading_anchor_guard.py --json
        python3 scripts/heading_anchor_guard.py --selftest

Rückgabe: 0 = alles grün, 1 = mindestens ein Befund (Deploy stoppen).
"""

from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PREMIUM = os.path.join(ROOT, "static", "premium", "ff-premium.js")
ENGINE = os.path.join(ROOT, "static", "premium", "ff-voice.js")
SAFETY = os.path.join(ROOT, "static", "premium", "ff-summary-safety.js")
THEME_ANCHOR = os.path.join(ROOT, "themes", "PaperMod", "layouts", "_partials", "anchored_headings.html")
FUNCTIONAL_TEST = os.path.join(ROOT, "scripts", "ff_voice_functional_test.mjs")
GLYPH_GUARD = os.path.join(ROOT, "scripts", "ff_heading_glyph_guard_test.mjs")
GATE = os.path.join(ROOT, ".github", "workflows", "lesehilfen-gate.yml")
PUBLIC = os.path.join(ROOT, "public")

GLYPH = "\u00a7"          # §
TAG_STRIP = re.compile(r"<[^>]*>")
HEADING_RE = re.compile(r"<h([1-6])\b[^>]*>(.*?)</h\1>", re.S | re.I)
INNER_ANCHOR_RE = re.compile(r"<(a|button)\b([^>]*)>\s*(" + GLYPH + r"|#)\s*</\1>", re.I)
# Versteckte Knoten (Theme-Anker) zählen nicht zum sichtbaren Text —
# genau das ist Schicht 3 dieser Wache („der Anker des Themes bleibt für
# Lesemaschinen unsichtbar“). \bhidden\b trifft sowohl das HTML-Attribut
# `hidden` als auch `aria-hidden="true"`.
HIDDEN_TAG_RE = re.compile(
    r"<(?:a|span|button|svg|small)\b[^>]*\bhidden\b[^>]*>.*?</(?:a|span|button|svg|small)>",
    re.S | re.I)

# Prüfsteine der Quelltexte: (Befund-Text, Muster, muss enthalten?)
SOURCE_RULES = [
    ("Knopf trägt ein Inline-SVG statt einer Glyphe", r"ff-heading-copy__ico", True),
    ("Knopf ist für Lesemaschinen markiert", r"data-ff-skip-read", True),
    ("Überschriften-Text in eigenem Etikett", r"ff-heading-text", True),
    ("Überschrift ist sauber beschriftet", r"aria-labelledby", True),
    ("Häkchen als Kopier-Bestätigung", r"CHECK_ICON", True),
    ("Mini-Verzeichnis nutzt den sauberen Text", r"headingText\(heading\)", True),
    ("Kein „§“ als Inhalt eines Elements", r"innerHTML\s*=\s*['\"]\s*" + GLYPH, False),
    ("Kein „§“ als Textknoten", r"textContent\s*=\s*['\"]\s*" + GLYPH, False),
    ("Kein „§“ als Knopf-Beschriftung", r"createTextNode\(\s*['\"]\s*" + GLYPH, False),
]

ENGINE_RULES = [
    ("Lesemaschinen überspringen den Kopierknopf", r"\.ff-heading-copy", True),
    ("Lesemaschinen überspringen Anker", r"\.anchor", True),
    ("Lesemaschinen überspringen versteckte Knoten", r"\[hidden\]", True),
    ("Lesemaschinen überspringen aria-hidden", r"\[aria-hidden=\"true\"\]", True),
    ("Lesemaschinen überspringen Bedienelemente", r"'button'", True),
    ("Lesemaschinen respektieren data-ff-skip-read", r"\[data-ff-skip-read\]", True),
    ("Eigener Überschriften-Text (headingTextOf)", r"function headingTextOf\(", True),
]


def read(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


class Report:
    def __init__(self):
        self.checks = []

    def add(self, layer, label, ok, detail=""):
        self.checks.append({"layer": layer, "label": label, "ok": bool(ok), "detail": detail})

    @property
    def failed(self):
        return [c for c in self.checks if not c["ok"]]

    def __str__(self):
        layers = []
        out = []
        for c in self.checks:
            if c["layer"] not in layers:
                layers.append(c["layer"])
        for layer in layers:
            out.append("")
            out.append("  " + layer)
            for c in self.checks:
                if c["layer"] != layer:
                    continue
                mark = "\u2713" if c["ok"] else "\u2717"
                line = "    {} {}".format(mark, c["label"])
                if not c["ok"] and c["detail"]:
                    line += " \u2014 " + c["detail"]
                out.append(line)
        out.append("")
        out.append("  {}/{} Prüfungen bestanden".format(
            len(self.checks) - len(self.failed), len(self.checks)))
        return "\n".join(out)


def check_source(rep):
    src = read(PREMIUM)
    if src is None:
        rep.add("1) QUELLE · static/premium/ff-premium.js", "Datei vorhanden", False, "fehlt")
        return
    rep.add("1) QUELLE · static/premium/ff-premium.js", "Datei vorhanden", True)
    for label, pattern, must_have in SOURCE_RULES:
        found = re.search(pattern, src) is not None
        rep.add("1) QUELLE · static/premium/ff-premium.js", label, found == must_have,
                "" if found == must_have else "Muster {} {} im Quelltext".format(
                    pattern, "fehlt" if must_have else "ist weiterhin enthalten"))


def check_engine(rep):
    src = read(ENGINE)
    if src is None:
        rep.add("2) ENGINE · static/premium/ff-voice.js", "Datei vorhanden", False, "fehlt")
        return
    rep.add("2) ENGINE · static/premium/ff-voice.js", "Datei vorhanden", True)
    for label, pattern, must_have in ENGINE_RULES:
        found = re.search(pattern, src) is not None
        rep.add("2) ENGINE · static/premium/ff-voice.js", label, found == must_have,
                "" if found == must_have else "Muster {} {}".format(
                    pattern, "fehlt" if must_have else "unerwartet"))
    # Die Kurzfassung muss den sauberen Überschriften-Text verwenden
    rep.add("2) ENGINE · static/premium/ff-voice.js",
            "Inhaltsverzeichnis nutzt headingTextOf", "text: headingTextOf(h)" in src)
    rep.add("2) ENGINE · static/premium/ff-voice.js",
            "Tabellen-Titel nutzen headingTextOf", "stripDecor(headingTextOf(prev))" in src)

    safety = read(SAFETY) or ""
    rep.add("2) ENGINE · static/premium/ff-voice.js",
            "Sicherheitsnetz prüft Ankerreste im Verzeichnis",
            "ff-voice-toc" in safety)
    rep.add("2) ENGINE · static/premium/ff-voice.js",
            "Sicherheitsnetz entfernt reine Ankerrest-Knoten (Härtung #248)",
            "removeChild(last)" in safety)


def check_theme(rep):
    src = read(THEME_ANCHOR)
    layer = "3) THEME · anchored_headings.html"
    if src is None:
        rep.add(layer, "Datei vorhanden", False, "fehlt")
        return
    rep.add(layer, "Datei vorhanden", True)
    rep.add(layer, "Anker ist versteckt", "hidden" in src)
    # Im Template stehen die Anführungszeichen maskiert: aria-hidden=\"true\"
    rep.add(layer, "Anker ist für Lesemaschinen unsichtbar", 'aria-hidden=\\"true\\"' in src)
    rep.add(layer, "Anker trägt kein „§“", GLYPH not in src)


def visible_heading_text(inner_html):
    """Sichtbarer Überschriften-Text: versteckte Knoten (Theme-Anker)
    zuerst entfernen, dann Tags weg. Nur dieser Text wird geprüft —
    sonst würde der legitime, versteckte Theme-Anker („#“) ein
    angeblich angehängtes Ankersymbol vortäuschen."""
    return TAG_STRIP.sub("", HIDDEN_TAG_RE.sub("", inner_html)).strip()


def heading_findings(html, rel):
    """Liefert die Befunde EINER Seite: Liste von Klartext-Funden.
    Ein Fund ist immer ein SICHTBARES Ankersymbol — verstecktes Markup
    (Theme-Anker: `hidden`/`aria-hidden`/Klasse `anchor`) ist legitim."""
    out = []
    for level, inner in HEADING_RE.findall(html):
        visible = visible_heading_text(inner)
        if GLYPH in visible and re.search(r"[\s" + GLYPH + r"#]$", visible):
            out.append(rel + ": " + visible[-48:])
        for m in INNER_ANCHOR_RE.finditer(inner):
            attrs = m.group(2) or ""
            if re.search(r"\bhidden\b", attrs, re.I):
                continue
            if re.search(r"\banchor\b", attrs, re.I):
                continue
            out.append(rel + ": sichtbares Ankersymbol in <{}>".format(m.group(1)))
    return out


def scan_build(public_dir):
    """Prüft alle gebauten Seiten in public_dir. Rückgabe: (Befunde, Anzahl Seiten)."""
    files = []
    for base, _dirs, names in os.walk(public_dir):
        for name in names:
            if name.endswith(".html"):
                files.append(os.path.join(base, name))
        if len(files) > 600:
            break
    bad = []
    for path in files[:600]:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                html = fh.read()
        except OSError:
            continue
        bad.extend(heading_findings(html, os.path.relpath(path, public_dir)))
    return bad, len(files[:600])


def check_build(rep):
    layer = "4) BAU · public/ (gebraute Seiten)"
    if not os.path.isdir(PUBLIC):
        rep.add(layer, "public/ nicht vorhanden \u2014 Bauprüfung übersprungen", True)
        return
    bad, count = scan_build(PUBLIC)
    rep.add(layer, "Keine Überschrift endet auf ein sichtbares Ankersymbol ({} Seiten)".format(count),
            not bad, " | ".join(bad[:4]))


def selftest():
    """Selbsttest der Bau-Prüfung mit einer synthetischen public/-Umgebung.

    Hintergrund (Befund 10.09.2026): Die Bau-Prüfung lief zum ersten Mal
    im ECHTEN Deploy — und scheiterte an jedem Theme-Anker, weil das
    Muster verstecktes Markup nicht ausnahm. Lokal gibt es kein public/
    (kein Hugo), das Lesehilfen-Gate baut nicht — deshalb prüft dieser
    Selbsttest die Bau-Logik gegen ein Mini-public/, das den echten
    Hugo-Output nachbildet (anchored_headings.html). Er läuft im
    Lesehilfen-Gate und im Deploy VOR der echten Wache.
    """
    theme_anchor = '<a hidden class="anchor" aria-hidden="true" href="#x">#</a>'
    cases = []

    # 1 · Saubere Seite, wie Hugo sie baut: Theme-Anker (versteckt) +
    #     legitimes „§“ mitten im Überschriften-Text.
    okay = (
        "<html><body><main><article>"
        '<h2 id="a">Was ist Tagesgeld?' + theme_anchor + "</h2>"
        "<p>Text</p>"
        '<h2 id="b">Rechte aus § 8 EinSiG' + theme_anchor + "</h2>"
        "</article></main></body></html>"
    )
    cases.append(("saubere Seite (Theme-Anker + legitimes §)", okay, False))

    # 2 · Der Original-Bug: sichtbarer „§“-Knopf in der Überschrift.
    button = (
        "<html><body><main><article>"
        '<h2 id="a">Was ist Tagesgeld?<button class="ff-heading-copy" type="button">§</button></h2>'
        "</article></main></body></html>"
    )
    cases.append(("sichtbarer §-Knopf (Original-Bug)", button, True))

    # 3 · Überschriften-TEXT endet sichtbar auf „§“.
    trailing = (
        "<html><body><main><article>"
        '<h2 id="a">Zinsen im Vergleich §</h2>'
        "</article></main></body></html>"
    )
    cases.append(("Text endet sichtbar auf §", trailing, True))

    # 4 · SICHTBARES Anker-„#“ als Elementtext (nicht versteckt).
    visible_anchor = (
        "<html><body><main><article>"
        '<h2 id="a">Zinsen im Vergleich<a class="some-link" href="#a">#</a></h2>'
        "</article></main></body></html>"
    )
    cases.append(("sichtbares Anker-# in <a>", visible_anchor, True))

    import tempfile
    failed = 0
    with tempfile.TemporaryDirectory() as tmp:
        for i, (label, html, expect_bad) in enumerate(cases):
            case_dir = os.path.join(tmp, "fall-{}".format(i))
            os.makedirs(case_dir)
            with open(os.path.join(case_dir, "seite.html"), "w", encoding="utf-8") as fh:
                fh.write(html)
            findings, count = scan_build(case_dir)
            got_bad = bool(findings)
            mark = "\u2713" if got_bad == expect_bad and count == 1 else "\u2717"
            if got_bad != expect_bad or count != 1:
                failed += 1
            detail = "" if got_bad == expect_bad else " \u2014 Befunde: {}".format(findings)
            print("  {} {}{}".format(mark, label, detail))

    print("")
    if failed:
        print("\u274c heading_anchor_guard Selbsttest: {} Fall/F\u00e4lle fehlgeschlagen.".format(failed))
        return 1
    print("\u2705 heading_anchor_guard Selbsttest: gr\u00fcn.")
    return 0


def check_tests(rep):
    layer = "5) TEST · Regressionsgruppe & Verdrahtung"
    src = read(FUNCTIONAL_TEST) or ""
    rep.add(layer, "Gruppe „Abschnitts-Link“ vorhanden", "Abschnitts-Link" in src)
    rep.add(layer, "Prüfung „Verzeichnis: kein einziges „§““", "kein einziges" in src)
    rep.add(layer, "Prüfung „echtes § bleibt erhalten“", "EinSiG" in src)
    guard = read(GLYPH_GUARD) or ""
    rep.add(layer, "„§“-Wache (jsdom, echte Produktions-Dateien) vorhanden",
            "ff-heading-copy" in guard and "Feind-Injektion" in guard)
    rep.add(layer, "„§“-Wache pinnt alle echten Artikel", "listArticles()" in guard)
    gate = read(GATE) or ""
    rep.add(layer, "Gate führt den Funktionstest aus", "ff_voice_functional_test.mjs" in gate)
    rep.add(layer, "Gate führt die „§“-Wache aus", "ff_heading_glyph_guard_test.mjs" in gate)
    rep.add(layer, "Gate führt diese Wache aus", "heading_anchor_guard.py" in gate)
    rep.add(layer, "Gate reagiert auf ff-premium.js", "static/premium/ff-premium.js" in gate)


def main():
    if "--selftest" in sys.argv:
        print("")
        print("  heading_anchor_guard.py \u2014 Selbsttest der Bau-Pr\u00fcfung")
        print("  " + "=" * 52)
        return selftest()

    rep = Report()
    check_source(rep)
    check_engine(rep)
    check_theme(rep)
    check_build(rep)
    check_tests(rep)

    if "--json" in sys.argv:
        print(json.dumps({"checks": rep.checks, "failed": len(rep.failed)}, ensure_ascii=False, indent=2))
    else:
        print("")
        print("  heading_anchor_guard.py \u2014 Wache gegen Ankersymbole in Überschriften")
        print("  " + "=" * 62)
        print(str(rep))
        print("")

    if rep.failed:
        print("\u274c heading_anchor_guard: {} Befund(e).".format(len(rep.failed)))
        return 1
    print("\u2705 heading_anchor_guard: grün.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
