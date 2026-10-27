#!/usr/bin/env python3
"""Metadaten-Wache für Artikel und Pillar-Ratgeber (offline, deterministisch).

Hintergrund (Audit #743, Nachschärfung 14.10.2026): Die bisherigen Gates
prüften Titel und Cover-Existenz, aber nicht die Metadaten-Konsistenz und
nicht, ob ein Zahlenversprechen auf Cover, in der Description oder im
Frontmatter im Text belegt ist. Dieses Gate schließt diese Lücken.

Regeln (jede Regel hat einen Selbsttest-Fall):
  M1  Titel 1–60 Zeichen (SERP kürzt darüber den Titel)
  M2  Description 100–155 Zeichen (SERP-Snippet-Fenster)
  M3  lastmod darf nicht vor dem Veröffentlichungstag (date) liegen
  M4  Veröffentlichte Inhalte: Quelle(n) vorhanden; Artikel zusätzlich
      Kurzantwort, Faktencheck-Datum und ein existierendes Cover-Bild
  M5  Titel und Description sind unter veröffentlichten Inhalten eindeutig
  M6  Zahlenversprechen (Spar-Pille aus savings/Description) müssen im
      Fließtext als Zahl belegt sein – „Zahlen statt Behauptungen“.
      Kein Beleg → FAIL (Korrektur: Zahl belegen oder Versprechen streichen).
  M7  Description passt auch in der BREITE ins Snippet (≤ 985 px in
      Arial 14 px). Die Zeichenzahl allein reicht nicht: 150 Zeichen
      aus breiten Wörtern laufen über, 155 schmale Zeichen nicht.
      Grenzen und Breitenmaß: scripts/serp_limits.py (eine Quelle).

Grenzen sind Markt-Grenzen (seit 27.10.2026): Ein fremder Crawl
(Screaming Frog) meldete die Startseite mit „über 155 Zeichen“ und
„über 985 Pixel“, während M2 hier 160 erlaubte. Zwei Maßstäbe, ein
Befund – seitdem liest diese Wache die Grenzen aus `serp_limits`,
dieselbe Zahl, die das SEO-Cockpit am gebauten HTML prüft.

Nutzung:
  python3 scripts/metadaten_wache.py            # Prüfung, Exit 0/1
  python3 scripts/metadaten_wache.py --json     # Befunde als JSON
  python3 scripts/metadaten_wache.py --selftest # Sabotage-Proben (Exit 0 = Wache scharf)

Exit: 0 = alles ok · 1 = Befunde · 2 = Selbsttest/Setup-Fehler
"""
import datetime as _dt
import glob
import json
import os
import re
import sys

try:
    import yaml
except ImportError:  # fail-closed: ohne PyYAML keine Aussage
    yaml = None

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import serp_limits  # noqa: E402  (SSOT: Grenzen + Breitenmaß, keine zweite Zahl)

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TITLE_MAX = 60
# Keine eigenen Zahlen: die Grenzen gehören der SSOT (serp_limits.py) und
# werden hier nur benannt, damit Berichte und Tests lesbar bleiben.
DESC_MIN, DESC_MAX = serp_limits.DESC_MIN_ZEICHEN, serp_limits.DESC_MAX_ZEICHEN
CONTENT_GLOBS = [
    "content/posts/*.md",
    "content/posts/*/index.md",
    "content/pillar/*/index.md",
]
SKIP_BASENAMES = {"_index.md"}


# ---------------------------------------------------------------------------
#  Frontmatter-Parsing
# ---------------------------------------------------------------------------
def split_frontmatter(text):
    """Liefert (frontmatter_dict, body) oder (None, text) ohne gültiges Frontmatter."""
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m or yaml is None:
        return None, text
    try:
        data = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None, text
    return (data if isinstance(data, dict) else None), m.group(2)


def _norm(s):
    return re.sub(r"\s+", " ", str(s or "").replace("\u00a0", " ").replace("&nbsp;", " ")).strip()


def _days(value):
    """Datum aus YAML (date/datetime/str) auf ein date-Objekt normieren."""
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(value or ""))
    if not m:
        return None
    return _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def _is_published(fm):
    return fm.get("draft") is not True


def _amounts(text):
    """Zahlen wie 430, 1.250, 2.000, 80, 100 aus einem Pillen-Text."""
    return [n.rstrip(".,") for n in re.findall(r"\d[\d\.,]*\d|\d", text or "")]


_UNIT = re.compile(r"€|Euro|%|Prozent")


def _claim_in_body(number, pill, body):
    """Ein Zahlenversprechen gilt nur als belegt, wenn die Zahl MIT ihrer
    Einheit (€/Euro/%/Prozent) im Fließtext steht. Die blanke Zahl reicht
    nicht: „ab ca. 5 € im Monat“ wäre sonst durch „Schritt 5“ belegt."""
    text = body.replace("\u00a0", " ").replace("&nbsp;", " ").replace("*", "")
    unit = r"\s*(?:€|Euro|%|Prozent)" if _UNIT.search(pill) else ""
    rx = r"(?<![\d.,])" + re.escape(number) + r"(?![\d])" + unit
    return re.search(rx, text) is not None


# ---------------------------------------------------------------------------
#  Prüfung einer Datei (pure Funktion – testbar ohne Dateisystem-Glob)
# ---------------------------------------------------------------------------
def check_document(rel, text, cover_exists=None, pill_fn=None):
    """Prüft ein Dokument. Gibt Befunde als Liste von dicts zurück.

    cover_exists: Callable(str)->bool für cover.image (None = nicht prüfen).
    pill_fn: Callable(title, description, explicit)->str|None (Spar-Pille).
    """
    findings = []

    def add(rule, msg):
        findings.append({"file": rel, "rule": rule, "msg": msg})

    fm, body = split_frontmatter(text)
    if fm is None:
        add("M0", "Frontmatter fehlt oder ist nicht lesbar")
        return findings

    title = _norm(fm.get("title"))
    if not title:
        add("M1", "Titel fehlt")
    elif len(title) > TITLE_MAX:
        add("M1", f"Titel {len(title)} Zeichen (max. {TITLE_MAX}): {title!r}")

    desc = _norm(fm.get("description"))
    if not desc:
        add("M2", "Description fehlt")
    else:
        if not (DESC_MIN <= len(desc) <= DESC_MAX):
            add("M2", f"Description {len(desc)} Zeichen (erwartet {DESC_MIN}–{DESC_MAX})")
        # M7: Breite. Ein Snippet kann bei 150 Zeichen überlaufen, wenn die
        # Wörter breit sind – und bei 155 Zeichen passen, wenn sie schmal
        # sind. Deshalb misst die Wache, was Google abschneidet.
        breite = serp_limits.breite_px(desc)
        if breite is None:
            zeichen = ", ".join(repr(z) for z in serp_limits.unbekannte_zeichen(desc)[:5])
            add("M7", f"Description enthält Zeichen ohne Breitenmaß ({zeichen}) – "
                      "Snippet-Breite nicht prüfbar")
        elif breite > serp_limits.DESC_MAX_PX:
            add("M7", f"Description {breite:.0f} px in {serp_limits.SCHRIFT_NAME} "
                      f"(max. {serp_limits.DESC_MAX_PX} px)")

    date = _days(fm.get("date"))
    lastmod = _days(fm.get("lastmod"))
    if date and lastmod and lastmod < date:
        add("M3", f"lastmod {lastmod} liegt vor date {date}")

    if _is_published(fm):
        quellen = fm.get("quellen") or []
        if not quellen:
            add("M4", "Keine Quelle im Frontmatter (quellen)")
        is_article = "/posts/" in rel
        if is_article:
            if not _norm(fm.get("kurzantwort")):
                add("M4", "Kurzantwort fehlt")
            if not fm.get("faktencheck"):
                add("M4", "Faktencheck-Datum fehlt")
        cover = fm.get("cover") or {}
        image = cover.get("image") if isinstance(cover, dict) else None
        if is_article and not image:
            add("M4", "Cover-Bild fehlt (cover.image)")
        if image and cover_exists is not None and not cover_exists(image):
            add("M4", f"Cover-Datei nicht gefunden: {image}")
        if is_article and isinstance(cover, dict) and not _norm(cover.get("alt")):
            add("M4", "Cover-Alt-Text fehlt")

        # M6: Zahlenversprechen müssen im Fließtext belegt sein.
        if pill_fn is not None and title:
            savings = fm.get("savings")
            pill = pill_fn(title, desc, _norm(savings) if savings else None)
            if pill:
                missing = [n for n in _amounts(pill) if not _claim_in_body(n, pill, body)]
                if missing:
                    add("M6", f"Spar-Pille {pill!r}: Zahl {missing[0]} steht nicht mit Einheit im Fließtext")
    return findings


def check_uniqueness(docs):
    """M5 über alle veröffentlichten Dokumente. docs: [(rel, title, desc)]."""
    findings = []
    for field, idx in (("Titel", 1), ("Description", 2)):
        seen = {}
        for doc in docs:
            value = doc[idx]
            if not value:
                continue
            seen.setdefault(value, []).append(doc[0])
        for value, files in seen.items():
            if len(files) > 1:
                for f in files:
                    findings.append({"file": f, "rule": "M5",
                                     "msg": f"{field} doppelt: {value[:60]!r}"})
    return findings


# ---------------------------------------------------------------------------
#  Repo-Lauf
# ---------------------------------------------------------------------------
def _pill_fn():
    """Spar-Pillen-Logik aus dem Cover-Generator (SSOT). None = nicht verfügbar."""
    try:
        sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
        import generate_covers as gc  # noqa: WPS433 (bewusster Lazy-Import)
        return gc.extract_savings
    except Exception:  # fail-closed: der Aufrufer meldet das als Befund
        return None


def run(root=BLOG_DIR):
    findings = []
    pill_fn = _pill_fn()
    if pill_fn is None:
        findings.append({"file": "scripts/generate_covers.py", "rule": "M6",
                         "msg": "Spar-Pillen-Logik nicht ladbar (Pillow fehlt?) – fail-closed"})
    static_dir = os.path.join(root, "static")

    def cover_exists(img):
        return os.path.exists(os.path.join(static_dir, img.lstrip("/")))

    docs = []
    files = []
    for pattern in CONTENT_GLOBS:
        files += glob.glob(os.path.join(root, pattern))
    for path in sorted(set(files)):
        if os.path.basename(path) in SKIP_BASENAMES:
            continue
        rel = os.path.relpath(path, root)
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        findings += check_document(rel, text, cover_exists=cover_exists, pill_fn=pill_fn)
        fm, _ = split_frontmatter(text)
        if fm and _is_published(fm):
            docs.append((rel, _norm(fm.get("title")), _norm(fm.get("description"))))
    findings += check_uniqueness(docs)
    return findings, len(files)


# ---------------------------------------------------------------------------
#  Selbsttest: Sabotage-Proben + Gegenprobe
# ---------------------------------------------------------------------------
_GOOD = """---
title: "Strom sparen: Ratgeber für den Alltag"
description: "Strom sparen im Alltag: Stromfresser finden, Tarife vergleichen und Abschläge richtig planen. Mit einfachen Rechenbeispielen für jeden Haushalt."
date: 2026-09-01T06:00:00Z
lastmod: 2026-09-02
draft: false
quellen:
  - titel: "Quelle"
    url: "https://example.org"
kurzantwort: "Kurze, belastbare Antwort auf die Frage."
faktencheck: "2026-10-01"
cover:
  image: "images/covers/gut.jpg"
  alt: "Titelbild Strom sparen"
savings: "bis zu 360 € im Jahr sparen"
---

Im Text stehen 360 Euro als Beleg: 360 € im Jahr.
"""


def _selftest_pill(title, desc, explicit):
    """Selbsttest-Ersatz für die Spar-Pille (ohne Pillow): gleiche Regel wie
    der Cover-Generator für die Fälle, die der Test braucht."""
    if explicit:
        return explicit
    m = re.search(r"bis\s+zu\s+(\d[\d\.,]*)\s*€", desc or "")
    return f"bis zu {m.group(1)} € sparen" if m else None


def run_selftest():
    if yaml is None:
        print("🛑 Selbsttest: PyYAML fehlt – Wache nicht scharf.")
        return 2
    cases = [
        ("Gegenprobe: sauberer Artikel", _GOOD, None, _selftest_pill, []),
        ("M1: Titel über 60 Zeichen", _GOOD.replace(
            'title: "Strom sparen: Ratgeber für den Alltag"',
            'title: "Strom sparen: Der sehr große Ratgeber für niedrige Energiekosten im Haushalt"'), None, _selftest_pill, ["M1"]),
        ("M2: Description zu kurz", _GOOD.replace(
            'description: "Strom sparen im Alltag: Stromfresser finden, Tarife vergleichen und Abschläge richtig planen. Mit einfachen Rechenbeispielen für jeden Haushalt."',
            'description: "Zu kurz."'), None, _selftest_pill, ["M2"]),
        ("M3: lastmod vor date", _GOOD.replace("lastmod: 2026-09-02", "lastmod: 2026-08-01"), None, _selftest_pill, ["M3"]),
        ("M4: Quelle fehlt", _GOOD.replace('quellen:\n  - titel: "Quelle"\n    url: "https://example.org"\n', 'quellen: []\n'), None, _selftest_pill, ["M4"]),
        ("M4: Cover-Datei fehlt", _GOOD, lambda p: False, _selftest_pill, ["M4"]),
        ("M6: Zahlenversprechen ohne Beleg", _GOOD.replace("Im Text stehen 360 Euro als Beleg: 360 € im Jahr.", "Ohne Zahl im Text."), None, _selftest_pill, ["M6"]),
        ("M6: Zahl nur im Versprechen, Pille aus Description", _GOOD.replace('savings: "bis zu 360 € im Jahr sparen"\n', "").replace(
            'description: "Strom sparen im Alltag: Stromfresser finden, Tarife vergleichen und Abschläge richtig planen. Mit einfachen Rechenbeispielen für jeden Haushalt."',
            'description: "Strom sparen: bis zu 987 € sichern. Stromfresser finden, Tarife vergleichen und Abschläge planen – mit einfachen Rechenbeispielen."'), None, _selftest_pill, ["M6"]),
        # M7-Sabotage (27.10.2026): 135 Zeichen – also innerhalb von M2 –
        # laufen in Arial 14 px über 985 px. Genau diese Lücke zwischen
        # Zeichenzahl und Sichtbarkeit meldete der fremde Crawl.
        ("M7: Description zu breit bei 135 Zeichen", _GOOD.replace(
            'description: "Strom sparen im Alltag: Stromfresser finden, Tarife vergleichen und Abschläge richtig planen. Mit einfachen Rechenbeispielen für jeden Haushalt."',
            'description: "Wohngebäude und Wärmewende: Warum Wärmeverlust, Wärmepumpe und Wartung zusammengehören. Wer Wohnraum warm hält, spart mit Wärmedämmung."'),
         None, _selftest_pill, ["M7"]),
        # Ein Emoji ist messbar breit, aber nicht in der Kernschrift enthalten:
        # Die Wache schätzt NICHT, sie meldet „nicht prüfbar".
        ("M7: Zeichen ohne Breitenmaß (Emoji)", _GOOD.replace(
            'für jeden Haushalt."', 'für jeden Haushalt. 💡"'), None, _selftest_pill, ["M7"]),
        ("M6: Zahl nur als Nummer im Text, Versprechen mit Euro", _GOOD.replace(
            'savings: "bis zu 360 € im Jahr sparen"', 'savings: "ab ca. 5 € im Monat"').replace(
            "Im Text stehen 360 Euro als Beleg: 360 € im Jahr.", "Schritt 5 erklärt den Ablauf."), None, _selftest_pill, ["M6"]),
        ("Draft wird nicht als veröffentlicht bewertet", _GOOD.replace("draft: false", "draft: true").replace("kurzantwort: \"Kurze, belastbare Antwort auf die Frage.\"", ""), None, _selftest_pill, []),
    ]
    fails = []
    for name, text, exists, pf, expect in cases:
        got = sorted({f["rule"] for f in check_document("content/posts/x/index.md", text,
                                                       cover_exists=exists or (lambda p: True),
                                                       pill_fn=pf)})
        if got != sorted(expect):
            fails.append(f"{name}: erwartet {expect}, bekommen {got}")
    # M5-Sabotage: zwei Dokumente mit gleichem Titel
    dup = check_uniqueness([("a.md", "Gleich", "d1"), ("b.md", "Gleich", "d2")])
    if sorted({f["rule"] for f in dup}) != ["M5"] or len(dup) != 2:
        fails.append("M5: doppelter Titel nicht erkannt")
    if fails:
        print("🛑 Selbsttest FEHLGESCHLAGEN:")
        for f in fails:
            print("   -", f)
        return 2
    print(f"✅ Selbsttest: {len(cases) + 1} Proben (inkl. M5) bestanden – Wache ist scharf.")
    return 0


def main(argv):
    if "--selftest" in argv:
        return run_selftest()
    if run_selftest() != 0:
        return 2
    findings, count = run()
    if "--json" in argv:
        print(json.dumps({"files": count, "findings": findings}, ensure_ascii=False, indent=1))
    else:
        for f in findings:
            print(f"  [{f['rule']}] {f['file']}: {f['msg']}")
        print(f"Metadaten-Wache: {count} Dateien | Befunde: {len(findings)}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
