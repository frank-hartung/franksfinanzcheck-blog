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
  python3 scripts/metadaten_wache.py --fix      # heilt M2/M7 (Snippet) an der Quelle
  python3 scripts/metadaten_wache.py --selftest # Sabotage-Proben (Exit 0 = Wache scharf)

Exit: 0 = alles ok (oder geheilt) · 1 = Befunde · 2 = Selbsttest/Setup-Fehler

--fix (WF-7B6B / #925, 29.10.2026): Die Wache wurde am 27.10.2026 an die
SSOT gebunden, die SCHREIBER aber nicht. Einer von ihnen (das Keyword-Gate
im Deploy-Pfad) schrieb am 27.10. eine Description mit 153 Zeichen und
1011 px – innerhalb seines eigenen Limits (160), außerhalb des Marktes
(155/985). Das nächtliche Snippet-Gate fand es 15 Stunden später. Seitdem
heilt diese Wache an der Quelle, BEVOR gebaut und veröffentlicht wird:
  · M2/M7 (Snippet): kürzen an der Wortgrenze, gegen BEIDE Grenzen der
    SSOT (`serp_limits.auf_snippet_kuerzen`). Nur KÜRZEN – Verlängern
    braucht Inhalt, den die Wache nicht erfindet.
  · M3 (lastmod vor date): lastmod auf den Publikationstag heben, damit
    ein live gehender Entwurf kein Änderungsdatum aus der Vergangenheit
    trägt. Genau dieser Befund lag beim Eindrehen der Heilung an.
Nicht heilbar bleibt gemeldet: M1, M4, M5, M6, „zu kurze" Description,
unmessbare Description in der Satzmitte. C34 bleibt gewahrt: Ein Befund
stoppt die Auslieferung nicht; die Heilung läuft im Deploy-Pfad toleriert,
aber laut (Annotation + Report).
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


# ---------------------------------------------------------------------------
#  Heilung der Snippet-Klasse (M2/M7) an der Quelle
# ---------------------------------------------------------------------------
_DESC_ZEILE = re.compile(r"(?m)^description:[ \t]*(.*?)[ \t]*$")


def _yaml_quote(text: str) -> str:
    """Description sicher in eine doppelt gequotete YAML-Zeile schreiben."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _desc_rohwert(text: str) -> str | None:
    """Den ROH-Wert der description-Zeile lesen (ohne YAML-Deutung).

    Hausstil ist `description: "…"` in EINER Zeile. Ein Block- oder
    Foldskalar wird NICHT angefasst – dann bleibt die Datei unverändert
    und die Wache meldet den Befund weiter.
    """
    treffer = list(_DESC_ZEILE.finditer(text))
    if len(treffer) != 1:
        return None
    roh = treffer[0].group(1).strip()
    if len(roh) >= 2 and roh[0] == roh[-1] and roh[0] in "\"'":
        roh = roh[1:-1]
    return roh.replace('\\"', '"').replace("\\\\", "\\")


def heile_snippet(rel: str, text: str) -> tuple[str, list[str]]:
    """Kürzt eine zu lange/zu breite Description deterministisch (M2/M7).

    Rückgabe (neuer_text, geheilt). `geheilt` nennt Regel, altes und neues
    Maß. Bleibt die Datei unverändert, ist `geheilt` leer – die Wache meldet
    den Befund dann unverändert weiter. Nie geheilt wird:
      · M2 „zu kurz\" (Verlängern braucht Inhalt),
      · M7 „unmessbar\" (Zeichen ohne Breitenmaß – Schneiden hilft nicht
        zuverlässig, die Datei bleibt unverändert),
      · alles, was `serp_limits.auf_snippet_kuerzen` nicht ins Fenster
        bringt (Rückgabe `None`).
    """
    befunde = check_document(rel, text)
    if not any(f["rule"] in ("M2", "M7") for f in befunde):
        return text, []
    roh = _desc_rohwert(text)
    if roh is None:
        return text, []
    alt_zeichen, alt_px = serp_limits.masse(roh)
    neu = serp_limits.auf_snippet_kuerzen(roh)
    if neu is None or neu == serp_limits.normalisiere(roh):
        return text, []
    neu_zeichen, neu_px = serp_limits.masse(neu)
    # Nachprüfung VOR dem Schreiben: ein Schnitt, der die Grenzen nicht
    # einhält, wird verworfen – die Datei bleibt unverändert.
    if serp_limits.befunde(neu):
        return text, []
    zeile = f'description: "{_yaml_quote(neu)}"'
    neu_text = _DESC_ZEILE.sub(lambda _m: zeile, text, count=1)
    if neu_text == text:
        return text, []
    masse_alt = f"{alt_zeichen} Zeichen, {alt_px:.0f} px" if alt_px is not None else f"{alt_zeichen} Zeichen"
    masse_neu = f"{neu_zeichen} Zeichen, {neu_px:.0f} px" if neu_px is not None else f"{neu_zeichen} Zeichen"
    return neu_text, [f"M2/M7: Description {masse_alt} → {masse_neu} (Snippet-Fenster der SSOT)"]


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


def run(root=BLOG_DIR, heilen=False):
    findings = []
    geheilt = []
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
        if heilen:
            # Heilung VOR der Prüfung: Der Befund soll verschwinden, nicht
            # nur gemeldet werden. Was nicht heilbar ist, meldet die Prüfung
            # danach unverändert – geheilt wird nur, was wirklich heilt.
            text, meldungen = heile_datei(rel, text)
            if meldungen:
                with open(path, "w", encoding="utf-8") as out:
                    out.write(text)
                geheilt.append((rel, meldungen))
        findings += check_document(rel, text, cover_exists=cover_exists, pill_fn=pill_fn)
        fm, _ = split_frontmatter(text)
        if fm and _is_published(fm):
            docs.append((rel, _norm(fm.get("title")), _norm(fm.get("description"))))
    findings += check_uniqueness(docs)
    return findings, len(files), geheilt


def heile_lastmod(rel: str, text: str) -> tuple[str, list[str]]:
    """M3: `lastmod` vor `date` auf den Publikationstag heben.

    Nur für VERÖFFENTLICHTE Dokumente: Ein Entwurf darf ein älteres
    lastmod tragen (sein letzter Stand), sobald er live geht, darf das
    Änderungsdatum aber nicht VOR dem Veröffentlichungstag liegen – das
    ist widersprüchliches Metadatum, nicht nur ein Schönheitsfehler.
    Die Heilung setzt lastmod auf `date` (den Tag, an dem der Inhalt
    öffentlich wurde), nicht auf heute: kein erfundener Stand.
    """
    if not any(f["rule"] == "M3" for f in check_document(rel, text)):
        return text, []
    fm, _ = split_frontmatter(text)
    if fm is None or not _is_published(fm):
        return text, []
    date = _days(fm.get("date"))
    lastmod = _days(fm.get("lastmod"))
    if not date or not lastmod or lastmod >= date:
        return text, []
    if not re.search(r"(?m)^lastmod:", text):
        return text, []
    neu = re.sub(r"(?m)^lastmod:.*$", f"lastmod: {date.isoformat()}", text, count=1)
    if neu == text:
        return text, []
    return neu, [f"M3: lastmod {lastmod.isoformat()} \u2192 {date.isoformat()} "
                 "(Publikationstag – lastmod davor nicht live gehen lassen)"]


def heile_datei(rel: str, text: str) -> tuple[str, list[str]]:
    """Alle heilbaren Klassen einer Datei: Snippet (M2/M7), dann lastmod (M3).

    Reihenfolge fest: erst die Description, dann das Datum – beide Heilungen
    wirken auf Frontmatter-Zeilen und sollen sich nicht widersprechen.
    """
    text, geheilt = heile_snippet(rel, text)
    text, datum = heile_lastmod(rel, text)
    return text, geheilt + datum


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
    # ------------------------------------------------------------------
    #  Heilungs-Selbsttest (WF-7B6B / #925, 29.10.2026)
    #  Der Vorfall: das Keyword-Gate schrieb eine Description mit 153
    #  Zeichen und 1011 px. Die Wache sah die Grenzen, der SCHREIBER nicht.
    #  Seitdem heilt diese Wache die Snippet-Klasse an der Quelle – diese
    #  Proben halten den Heiler scharf: der Vorfall wird geheilt, und
    #  Gegenproben stellen sicher, dass er NICHT schneidet, was passt.
    # ------------------------------------------------------------------
    vorfall = _GOOD.replace(
        'description: "Strom sparen im Alltag: Stromfresser finden, Tarife vergleichen und Abschl\u00e4ge richtig planen. Mit einfachen Rechenbeispielen f\u00fcr jeden Haushalt."',
        'description: "DSL Hacks: WLAN-Verst\u00e4rker oder Mesh-WLAN? So findest du 2026 heraus, was dein Zuhause wirklich braucht \u2013 mit klaren Kosten und einer Entscheidungshilfe."')
    if not any(f["rule"] in ("M2", "M7") for f in check_document("x.md", vorfall)):
        fails.append("Heilung: die #925-Description wird nicht als Befund erkannt")
    geheilt_text, geheilt_meldungen = heile_snippet("x.md", vorfall)
    if not geheilt_meldungen:
        fails.append("Heilung: #925-Description wurde nicht geheilt")
    elif serp_limits.befunde(serp_limits.normalisiere(_desc_rohwert(geheilt_text))):
        fails.append("Heilung: geheiltes #925-Ergebnis verletzt die SSOT weiter")
    else:
        # Idempotenz: ein zweiter Lauf findet nichts mehr zu heilen.
        if heile_snippet("x.md", geheilt_text)[1]:
            fails.append("Heilung: zweiter Lauf heilt erneut (nicht idempotent)")
        # Der Rest des Dokuments bleibt unberührt: abgesehen von der
        # Description-Zeile müssen beide Fassungen Byte-gleich sein.
        rest_alt = vorfall.replace(_DESC_ZEILE.search(vorfall).group(0), "", 1)
        rest_neu = geheilt_text.replace(_DESC_ZEILE.search(geheilt_text).group(0), "", 1)
        if rest_neu != rest_alt:
            fails.append("Heilung: au\u00dfer der Description wurde etwas ver\u00e4ndert")
    # Gegenprobe: eine passende Description wird NICHT angefasst.
    if heile_snippet("x.md", _GOOD)[1]:
        fails.append("Heilung: eine passende Description wurde ver\u00e4ndert")
    # Zu kurz wird NICHT verl\u00e4ngert (Inhalt kann die Wache nicht erfinden).
    kurz = _GOOD.replace(
        'description: "Strom sparen im Alltag: Stromfresser finden, Tarife vergleichen und Abschl\u00e4ge richtig planen. Mit einfachen Rechenbeispielen f\u00fcr jeden Haushalt."',
        'description: "Zu kurz."')
    if heile_snippet("x.md", kurz)[1]:
        fails.append("Heilung: eine zu kurze Description wurde verl\u00e4ngert")
    # Unmessbar AM RAND (Emoji am Ende): Der Schnitt entfernt genau das
    # Zeichen ohne Breitenma\u00df und landet wieder im Fenster \u2013 geheilt.
    emoji = _GOOD.replace('f\u00fcr jeden Haushalt."', 'f\u00fcr jeden Haushalt. 💡"')
    emoji_geheilt, emoji_meldung = heile_snippet("x.md", emoji)
    if not emoji_meldung:
        fails.append("Heilung: unmessbares Zeichen am Rand wurde nicht entfernt")
    elif serp_limits.befunde(serp_limits.normalisiere(_desc_rohwert(emoji_geheilt))):
        fails.append("Heilung: nach Emoji-Entfernung noch ein Befund")
    # Unmessbar in der MITTE: Kein Pr\u00e4fix erreicht das Fenster (das
    # Zeichen ohne Metrik bleibt in jedem langen Pr\u00e4fix) \u2013 die Datei
    # bleibt unver\u00e4ndert, der Befund wird gemeldet, nicht weggeschnitten.
    mitte = _GOOD.replace(
        'description: "Strom sparen im Alltag: Stromfresser finden, Tarife vergleichen und Abschl\u00e4ge richtig planen. Mit einfachen Rechenbeispielen f\u00fcr jeden Haushalt."',
        'description: "Strom sparen 💡 im Alltag: Stromfresser finden, Tarife vergleichen und Abschl\u00e4ge planen. Mit einfachen Rechenbeispielen f\u00fcr den Haushalt."')
    if heile_snippet("x.md", mitte)[1]:
        fails.append("Heilung: unmessbares Zeichen in der Mitte wurde weggeschnitten")

    # M3-Heilung (WF-7B6B / #925): Ein live gehender Entwurf trug lastmod
    # aus der Vergangenheit – genau dieser Befund lag beim Eindrehen der
    # Heilung an. Geheilt wird auf den PUBLIKATIONSTAG, nicht auf heute.
    m3 = _GOOD.replace("lastmod: 2026-09-02", "lastmod: 2026-08-01")
    m3_geheilt, m3_meldung = heile_lastmod("x.md", m3)
    if not m3_meldung:
        fails.append("Heilung: lastmod vor date wurde nicht geheilt")
    elif "lastmod: 2026-09-01" not in m3_geheilt:
        fails.append("Heilung: lastmod wurde nicht auf den Publikationstag gesetzt")
    elif heile_lastmod("x.md", m3_geheilt)[1]:
        fails.append("Heilung: M3-Heilung ist nicht idempotent")
    # Gegenprobe: Entwurf (draft: true) bleibt unberührt – sein letzter
    # Stand darf älter sein als ein date, das noch nicht gilt.
    entwurf = _GOOD.replace("draft: false", "draft: true").replace(
        "lastmod: 2026-09-02", "lastmod: 2026-08-01")
    if heile_lastmod("x.md", entwurf)[1]:
        fails.append("Heilung: ein Entwurf wurde geheilt (darf nicht)")

    if fails:
        print("🛒🛒 Selbsttest FEHLGESCHLAGEN:")
        for f in fails:
            print("   -", f)
        return 2
    print(f"✅ Selbsttest: {len(cases) + 1} Proben (inkl. M5) + Heiler-Proben bestanden – Wache ist scharf.")
    return 0
def main(argv):
    if "--selftest" in argv:
        return run_selftest()
    heilen = "--fix" in argv
    if run_selftest() != 0:
        return 2
    findings, count, geheilt = run(heilen=heilen)
    if "--json" in argv:
        print(json.dumps({"files": count, "findings": findings,
                          "geheilt": [{"file": rel, "msg": m}
                                      for rel, ms in geheilt for m in ms]},
                         ensure_ascii=False, indent=1))
    else:
        for rel, ms in geheilt:
            for m in ms:
                print(f"  [GEHEILT] {rel}: {m}")
        for f in findings:
            print(f"  [{f['rule']}] {f['file']}: {f['msg']}")
        print(f"Metadaten-Wache: {count} Dateien | Befunde: {len(findings)}"
              f" | Geheilt: {sum(len(ms) for _, ms in geheilt)}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
