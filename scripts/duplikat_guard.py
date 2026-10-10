#!/usr/bin/env python3
"""
DUPLIKAT-GUARD (R1) – Duplikat- & Redundanz-Wächter für FranksFinanzcheck.

Erkennt die Verständnis-Killer, die KEIN bestehendes Gate misst:

  D1  Exakte Absatz-Duplikate INNERHALB eines Artikels (SHA-256, >= 80 Zeichen)
  D2  Near-Duplikate INNERHALB eines Artikels (difflib-Ratio >= 0.85, >= 120 Zeichen)
      -> fängt auch die "Premium-Length"-Falle ab: angehängte Blöcke, die
         wortnah einen vorhandenen Abschnitt wiederholen (DNS-Artikel 08/2026).
  D3  Exakte Absatz-Duplikate ÜBER Artikel hinweg (>= 80 Zeichen)
  D4  Near-Duplikate ÜBER Artikel hinweg (Ratio >= 0.85, >= 150 Zeichen)
  D5  Sektions-Duplikate: zwei H2-Kapitel eines Artikels fast identisch
      (Ratio >= 0.85, Kapitel >= 150 Zeichen) – "Wann X spürbar ist / Wann Y
      spürbar ist"-Doppelstrukturen.
  D6  Premium-Length-Anhänge: Blöcke NACH dem Marker '<!-- premium-length -->'
      werden gegen den Rest des Artikels geprüft (Shingle-Überlappung >= 5).

MODI:
  python3 scripts/duplikat_guard.py             # Report (alle Artikel)
  python3 scripts/duplikat_guard.py --json      # maschinenlesbar
  python3 scripts/duplikat_guard.py --fix       # exakte + fast-exakte Duplikate
                                                # (Ratio >= 0.92, Längendiff < 25 %)
                                                # im SELBEN Artikel entfernen (spätere Version)
  python3 scripts/duplikat_guard.py --new-only  # Engine-Modus: nur Artikel von heute;
                                                # Funde -> Exit 1 (Gate blockierend)
  python3 scripts/duplikat_guard.py --selftest  # Sabotage-Schutz (eingefrorene Fälle)

Ausgabe: DUPLIKAT-REPORT.md + data/duplikat_history.jsonl
Sicherheit: Cross-Artikel-Funde werden NIE auto-gefixed, nur gemeldet.
"""

import ast
import difflib
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "content" / "posts"
REPORT = ROOT / "DUPLIKAT-REPORT.md"
HISTORY = ROOT / "data" / "duplikat_history.jsonl"

# Die CTA-SSOT liegt als Schwestermodul in scripts/. Beim Aufruf über
# `python3 -m unittest scripts.tests.…` ist scripts/ nicht auf sys.path –
# ohne diesen Eintrag fiele die Haus-CTA-Erkennung still auf die lokale
# Fallback-Normalform zurück (#676: eine stille Ausnahme ist ein Scheingrün).
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

DO_FIX = "--fix" in sys.argv
AS_JSON = "--json" in sys.argv
NEW_ONLY = "--new-only" in sys.argv
SELFTEST_ONLY = "--selftest" in sys.argv

MIN_EXACT = 80          # Mindestlänge für exakte Duplikate (Zeichen)
MIN_NEAR = 120          # Mindestlänge für Near-Duplikate (Zeichen)
MIN_NEAR_X = 150        # Mindestlänge für Near-Duplikate über Artikel hinweg
RATIO_NEAR = 0.85       # Near-Duplikat-Schwelle
RATIO_FIX = 0.92        # Auto-Fix-Schwelle (innerhalb Artikel)
FIX_LEN_DIFF = 0.25     # max. relative Längendifferenz für Auto-Fix
PREMIUM_MARKER = "premium-length"
SHINGLE = 5             # N-Gramm-Größe für D6

# Boilerplate-Blöcke (sind absichtlich mehrfach im Artikel: Disclaimer, CTA,
# Weiterlesen-Boxen) – werden von der Duplikat-Messung ausgenommen.
#
# DAUERHEILUNG #676 (09.10.2026): Diese Liste wird gegen die VERGLEICHSFORM
# `_vergleichsform()` geprüft, nicht mehr gegen `text.lower()`. Zwei Gründe:
#   1. Unicode-Bindestriche: Der Bestand schreibt „Affiliate‑Links" mit
#      U+2011 (weicher Bindestrich, aus der KI-Erzeugung). `lower()` erhielt
#      ihn, das Muster „affiliate-links" traf nie – die Transparenz-Zeile
#      galt als redaktioneller Text und wurde als D3/D4-Duplikat gemeldet.
#   2. Markdown-Schmuck: `**Jetzt …:**` und `> 💶 …` verschoben den Anfang
#      des Vergleichstextes, Muster mit führendem Wort trafen nicht.
# `affiliate_intent_contract.norm()` ist dafür die SSOT – dieselbe Normalform,
# mit der die Intent-Wache CTA-Sätze im Bestand wiederfindet. Eine zweite
# Normalform wäre eine zweite Messregel (Lektion #521).
BOILERPLATE_RE = [
    r"dieser artikel enthält affiliate-links",
    r"jetzt vergleichen und sparen",
    r"weiterlesen:",
    r"das wichtigste in kürze",
    r"schnell-tipp von franksfinanzcheck",
    r"lesetipps zum weitersparen",
    r"dieser beitrag enthält affiliate",
    r"beim abschluss über einen link",
    # Haus-Templates, die absichtlich in vielen Artikeln stehen (Befund
    # 12.09.2026, D3/D4-Einführung): In-Text-CTA aus affiliate_marketer.py
    # und die Fazit-Formel aus fazit_schmiede.py. Nichts zu heilen – aber
    # ohne Whitelist blendet jede Cross-Artikel-Messung sie als Duplikat.
    r"spar-tipp zwischendurch",
    r"sich gezielt mit dem thema",
    # Rechtlicher Standard-Hinweis (YMYL-Disclaimer), wortgleich in jedem
    # Finanz-Artikel vorgeschrieben. Kein redaktioneller Inhalt, also kein
    # Duplikat – aber vor #676 nicht erfasst (D3-X über 5 Artikel).
    r"dieser artikel dient ausschließlich der allgemeinen information",
]

# ============================================================
#  HAUS-CTA AUS DER VERTRAGS-SSOT (Dauerheilung #676, 09.10.2026)
#  ------------------------------------------------------------
#  Root Cause von Issue #676 waren ZWEI WACHTEN MIT WIDERSPRÜCHLICHEN
#  VERTRÄGEN:
#
#    · scripts/affiliate_intent_contract.py ist die SSOT für CTA-Wortlaut.
#      Sie schreibt je Route EINEN ehrlichen Satz fest (`saetze["end"]` =
#      „Jetzt das Tagesgeld-Angebot der C24 Bank ansehen") und verlangt,
#      dass der Anker das Ziel nennt. `Ziel.satz_ehrlich()` sagt ausdrücklich:
#      „Ein Marker darf nicht umgeschrieben werden." Die Intent-Wache
#      (IW0–IW9) und die Affiliate-Integritäts-Wache PRÜFEN diesen Wortlaut.
#    · duplikat_guard maß denselben Wortlaut über Artikel hinweg und meldete
#      D3-X „Absatz wortgleich in 2 Artikeln" – für einen Block, den der
#      Vertrag absichtlich identisch vorgibt.
#
#  Die Folge war eine Blockade ohne Heiler: RD1-duplikate ist in der
#  Release-Scorecard `wirkung: blockiert`, `entscheidung: auto`, Cross-
#  Artikel-Funde werden aber NIE auto-gefixed („der Heilweg läuft über die
#  Redaktion"). Der Deploy starb 13× in Folge amselben Befund, kein
#  `--fix`-Lauf konnte ihn je heilen, die komplette öffentliche
#  Auslieferung fror ein – der neueste Artikel lieferte HTTP 404.
#
#  Die Reparatur ist keine weitere handgepflegte Zeichenkette, sondern die
#  ABLEITUNG aus der SSOT: Was der CTA-Vertrag als Haus-Wortlaut registriert,
#  ist Struktur und kein Inhalt. `ist_haus_cta()` erkennt einen Block nur
#  dann als Template, wenn er (a) ein internes Affiliate-Gateway `/go/…`
#  trägt und (b) sein gesamter Prosatext lückenlos aus registrierten
#  Vertrags-Bausteinen besteht. Ein einziger eigener Redaktionssatz im Block
#  hebt die Ausnahme auf – gemessen wird dann wieder alles.
# ============================================================

# Haus-Marker, die der Vertrag bewusst nicht umbenennt sieht (Kommentar in
# affiliate_intent_contract.CTA_SAETZE_DEFAULT): Sie sind Stil, kein Inhalt.
HAUS_MARKER = (
    "jetzt vergleichen und sparen",
    "spar-tipp zwischendurch",
    "schnell-tipp von franksfinanzcheck",
    "passendes angebot finden",
    "jetzt angebote ansehen",
    "jetzt angebote vergleichen",
    "transparenz",
    "werbung",
)

# Nur interne Affiliate-Gateways zählen als CTA-Beweis. Ein externer Link
# macht aus einem Absatz keinen Haus-Block.
GO_LINK_RE = re.compile(r"\]\(\s*/go/[a-z0-9_\-/]+/?\s*\)")

# Alles, was nach dem Herausnehmen der Vertrags-Bausteine übrig bleiben darf:
# Satzzeichen, Aufzählungs-/Pfeil-Schmuck und die CTA-Emoji-Marker des
# Bestands (👉 78×, 💡 51×, 💶 44× – siehe Kommentar in affiliate_intent_guard).
REST_SCHMUCK_RE = re.compile(
    "[\\s:·\\-–—.,;!?()\\[\\]{}\"'„“»«*_`>#|/→←👉💡💶✅📌🔗💰📊]+"
)

_HAUS_CTA_REGISTER: list | None = None
_HAUS_FORMELN: list | None = None

# Klartext-Hausformeln anderer SSOTs: (modul, attribut). Auch hier gilt:
# abgeleitet, nicht abgeschrieben. Steht die Formel im erzeugenden Modul,
# kennt die Duplikat-Messung sie – ohne zweite Zeichenkette, die verrotten
# kann (die Whitelist-Falle, die zu #676 führte).
HAUS_TEXT_QUELLEN = (
    ("ki_shared", "DISCLAIMER"),          # rechtlicher Standard-Hinweis (YMYL)
    ("cta_builder", "END_DISCLOSURE"),    # Werbe-Offenlegung am Artikelende
    ("cta_builder", "_END_SATZ_FALLBACK"),
    ("news_writer", "STAND_INTRO"),       # News-Kompakt-Dateline (mit Platzhalter)
)

# Ein Platzhalter in einer Haus-Formel wird zu genau EINEM Token – nie zu
# „beliebigem Text". Sonst wäre die Formel ein Freibrief für alles.
_PLATZHALTER_RE = re.compile(r"\{[^{}]*\}")


def _ssot_wert(modul: str, attribut: str):
    """Modulkonstante aus der QUELLDATEI lesen (AST) – nie per Import.

    Warum nicht `__import__`: `ki_shared`, `cta_builder` und `news_writer`
    ziehen PyYAML (und damit eine ganze Kette) nach. In jeder Umgebung ohne
    PyYAML – PR-Pfad, C6-Selbsttest, lokale Probe – wäre die Haus-Template-
    Erkennung damit STILL ausgefallen: Die Ausnahme verschwindet, die Wache
    misst vertraglich vorgeschriebene CTA-Blöcke wieder als Plagiat, und
    Issue #676 kehrt als Dauer-Fehlalarm zurück, der den Deploy einfriert.

    Fail-open ist hier teurer als ein Fehler. Ein AST-Lesezugriff auf eine
    Modulkonstante hat keine Import-Nebenwirkungen, braucht keine
    Abhängigkeit des Produzenten und liest trotzdem DIESELBE Quelle – keine
    zweite, abschreibbare Zeichenkette.

    Rückgabe: (wert, lücke). `lücke` ist leer, wenn gelesen wurde; sonst der
    Grund. Eine Lücke wird von `haus_template_luecken()` laut gemeldet und
    stoppt den Gate-Lauf (Exit 2) – eine blinde Wache ist kein Grün."""
    pfad = Path(__file__).resolve().parent / f"{modul}.py"
    try:
        baum = ast.parse(pfad.read_text(encoding="utf-8"))
    except OSError as exc:
        return None, f"{pfad.name} nicht lesbar: {exc}"
    except SyntaxError as exc:
        return None, f"{pfad.name} ist kein gültiges Python (Z. {exc.lineno})"
    for knoten in baum.body:
        if not isinstance(knoten, ast.Assign):
            continue
        for ziel in knoten.targets:
            if isinstance(ziel, ast.Name) and ziel.id == attribut:
                try:
                    return ast.literal_eval(knoten.value), ""
                except (ValueError, SyntaxError):
                    return None, (f"{modul}.{attribut} ist keine "
                                  "literal auswertbare Konstante")
    return None, f"{modul}.{attribut} nicht gefunden"


def haus_template_luecken() -> list:
    """Deklarierte SSOT-Quellen, die nicht gelesen werden konnten.

    Eine Lücke heißt: Die Ausnahme für diese Haus-Formel fehlt, die Wache
    misst sie wieder als Duplikat. Das ist kein Zustand, den man verschweigt
    (C33: eine fehlgeschlagene Messung ist kein leerer Vorrat)."""
    luecken = []
    for modul, attribut in HAUS_TEXT_QUELLEN:
        _wert, grund = _ssot_wert(modul, attribut)
        if grund:
            luecken.append(f"{modul}.{attribut}: {grund}")
    return luecken


def haus_formeln() -> list:
    """Vergleichsmuster für Haus-Formeln MIT Platzhalter (SSOT-abgeleitet).

    `news_writer.STAND_INTRO` trägt `{today}`: Dieselbe Zeile steht in jedem
    News-Kompakt-Artikel, nur das Datum wechselt. Vor #676 maß D4-X sie als
    Fast-Duplikat (Ratio 0.98) zwischen `markt-update` und `energie-update` –
    ein Format wurde als Inhaltsklau gewertet."""
    global _HAUS_FORMELN
    if _HAUS_FORMELN is not None:
        return _HAUS_FORMELN
    formeln = []
    for modul, attribut in HAUS_TEXT_QUELLEN:
        wert, _luecke = _ssot_wert(modul, attribut)
        if not isinstance(wert, str) or not _PLATZHALTER_RE.search(wert):
            continue
        # Auch kurze Fragmente zählen (die Dateline beginnt mit „Stand:“ –
        # sechs Zeichen). Wegfiltern würde die Formel hier unsichtbar machen;
        # die Sicherheit kommt aus der Längenprüfung der GESAMTformel unten.
        teile = [_vergleichsform(t) for t in _PLATZHALTER_RE.split(wert)]
        teile = [t for t in teile if len(t) >= 3]
        if len(teile) < 2 or sum(len(t) for t in teile) < 60:
            continue
        # `\s*\S+\s*` statt `\S+`: `normalize()` strippt die Leerzeichen um
        # den Platzhalter weg („**Stand: “ → „stand:“), im Artikel steht das
        # Datum aber mit Abstand. Ohne die flexiblen Ränder träfe die Formel
        # ihren eigenen Text nie – die Ausnahme wäre tot, nicht zu weit.
        formeln.append((f"{modul}.{attribut}",
                        re.compile(r"\s*\S+\s*".join(re.escape(t) for t in teile))))
    _HAUS_FORMELN = formeln
    return _HAUS_FORMELN


def haus_texte() -> list:
    """Klartext-Hausformeln ohne Platzhalter, in Vergleichsform (SSOT)."""
    texte = []
    for modul, attribut in HAUS_TEXT_QUELLEN:
        wert, _luecke = _ssot_wert(modul, attribut)
        if not isinstance(wert, str) or _PLATZHALTER_RE.search(wert):
            continue
        form = _vergleichsform(wert)
        if len(form) >= 40:          # nur echte Formeln, keine Marker-Wörter
            texte.append((f"{modul}.{attribut}", form))
    return texte


def _vergleichsform(text: str) -> str:
    """Normalform für den Template-Vergleich (SSOT: affiliate_intent_contract).

    Entfernt Unicode-Bindestriche, geschützte Leerzeichen und Markdown-
    Schmuck – genau wie die Intent-Wache, damit beide Wachen denselben Text
    sehen. Fällt auf eine lokale, gleichwertige Normalisierung zurück, wenn
    das Vertragsmodul nicht importierbar ist (die Wache bleibt lauffähig)."""
    try:
        import affiliate_intent_contract as aic  # noqa: PLC0415
        return aic.norm(normalize(text))
    except Exception:  # noqa: BLE001 – Fallback, nie still grün
        s = normalize(text).lower()
        s = s.replace("\u00ad", "").replace("\u00a0", " ").replace("\u202f", " ")
        for z in ("\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2015",
                  "\u2212", "\u02d7"):
            s = s.replace(z, "-")
        s = re.sub(r"[*_`>]", " ", s)
        return re.sub(r"\s+", " ", s).strip()


def haus_cta_register() -> list:
    """Alle CTA-Bausteine der Vertrags-SSOT in Vergleichsform (längster zuerst).

    Abgeleitet, nicht abgeschrieben: Ein neuer Partner, eine neue Route oder
    eine neue Anker-Variante in `affiliate_intent_contract.ZIELE` ist ab dem
    nächsten Lauf automatisch erfasst. Genau das fehlte der Whitelist – sie
    verrottete mit jeder neuen CTA-Variante und machte den Vertragstreuesten
    Block zum Plagiat.
    """
    global _HAUS_CTA_REGISTER
    if _HAUS_CTA_REGISTER is not None:
        return _HAUS_CTA_REGISTER
    bausteine: set = set()
    try:
        import affiliate_intent_contract as aic  # noqa: PLC0415
        for z in getattr(aic, "ZIELE", {}).values():
            for satz in (getattr(z, "saetze", {}) or {}).values():
                if satz:
                    bausteine.add(_vergleichsform(satz))
            for varianten in (getattr(z, "anker", {}) or {}).values():
                for anker in varianten or ():
                    if anker:
                        bausteine.add(_vergleichsform(anker))
            for feld in ("produkt", "weiter_zu"):
                wert = getattr(z, feld, "") or ""
                if wert:
                    bausteine.add(_vergleichsform(wert))
        for satz in (getattr(aic, "CTA_SAETZE_DEFAULT", {}) or {}).values():
            if satz:
                bausteine.add(_vergleichsform(satz))
    except Exception:  # noqa: BLE001 – ohne Vertrag nur Haus-Marker
        pass
    bausteine.update(_vergleichsform(m) for m in HAUS_MARKER)
    _HAUS_CTA_REGISTER = sorted((b for b in bausteine if len(b) >= 8),
                                key=len, reverse=True)
    return _HAUS_CTA_REGISTER


def ist_haus_cta(text: str) -> bool:
    """True, wenn der Block NUR aus Haus-CTA-Bausteinen des Vertrags besteht.

    Bewusst streng (kein Inhalts-Freibrief):
      1. ohne internes `/go/`-Gateway kein CTA-Block,
      2. jeder Prosarest außerhalb der Vertrags-Bausteine hebt die Ausnahme
         auf – ein Redaktionssatz neben der CTA wird wieder gemessen.
    """
    if not GO_LINK_RE.search(text or ""):
        return False
    rest = _vergleichsform(GO_LINK_RE.sub(" ", text))
    rest = rest.replace("[", " ").replace("]", " ")
    for baustein in haus_cta_register():
        if baustein and baustein in rest:
            rest = rest.replace(baustein, " ")
    return REST_SCHMUCK_RE.sub("", rest) == ""


def haus_template_grund(text: str) -> str:
    """Warum ein Block ausgenommen ist – Ausnahmen müssen sichtbar sein.

    Eine stille Ausnahme ist ein Scheingrün (Lektion #521, C19). Der Report
    zählt deshalb je Familie mit, und `--json` nennt den Grund am Fund.
    Reihenfolge ist bewusst: erst die SSOT-abgeleiteten Familien (sie sind
    die Wahrheit), dann die handfesten Haus-Formeln der Whitelist."""
    if not text:
        return ""
    t = _vergleichsform(text)
    for quelle, muster in haus_formeln():
        if muster.search(t):
            return f"Haus-Formel mit Platzhalter (`{quelle}`)"
    for quelle, form in haus_texte():
        if form in t:
            return f"Haus-Text (`{quelle}`)"
    if ist_haus_cta(text):
        return "Haus-CTA (Bausteine aus affiliate_intent_contract)"
    for muster in BOILERPLATE_RE:
        if re.search(muster, t):
            return f"Haus-Formel `{muster}`"
    return ""


def is_boilerplate(text: str) -> bool:
    """Haus-Template? (Disclaimer, CTA, Dateline, Weiterlesen-Boxen).

    Einziger Einstieg in die Ausnahme – damit Messung und Begründung nie
    auseinanderlaufen können (ein Block ist genau dann ausgenommen, wenn
    `haus_template_grund()` einen Grund nennt)."""
    return bool(haus_template_grund(text))


def split_body(frontmatter_body: str) -> str:
    parts = frontmatter_body.split("---", 2)
    return parts[2] if len(parts) >= 3 else frontmatter_body


def normalize(text: str) -> str:
    t = re.sub(r"\s+", " ", text).strip()
    # Angeklebte Trennlinie (Korruptions-Muster: wiederholte Intro-Blöcke
    # stehen als "---\n<Einleitung>" im Text): das "---" darf NICHT Teil
    # des Fingerabdrucks sein, sonst verfehlt D1/D2 die ERSTE Kopie und
    # der Rest ist selbst im --fix-Modus nicht heilbar (Befund 12.09.2026:
    # 7 Artikel mit je 2–4 eingefügten Intro-Kopien, Dauersignal im Report).
    t = re.sub(r"^[-=]{3,}\s+", "", t)
    return t


def blocks_of(body: str) -> list:
    """Liste von (block_text_normalized, start_zeichen, ist_premium)."""
    out = []
    premium = False
    pos = 0
    for chunk in body.split("\n\n"):
        chunk_n = normalize(re.sub(r"```.*?```", " ", chunk, flags=re.S))
        if not chunk_n:
            pos += len(chunk) + 2
            continue
        if PREMIUM_MARKER in chunk_n:
            premium = True
        if len(chunk_n) >= MIN_EXACT:
            out.append((chunk_n, pos, premium))
        pos += len(chunk) + 2
    return out


def sections_of(body: str) -> list:
    """H2-Kapitel (Text zwischen ##-Überschriften) für D5."""
    lines = body.split("\n")
    heads = [i for i, l in enumerate(lines) if re.match(r"^##\s+", l)]
    heads.append(len(lines))
    out = []
    for a, b in zip(heads[:-1], heads[1:]):
        sec = "\n".join(lines[a:b])
        sec_n = normalize(re.sub(r"```.*?```", " ", sec, flags=re.S))
        if len(sec_n) >= MIN_NEAR:
            out.append(sec_n)
    return out


def near_candidates(blocks: list, min_len: int):
    """Bucket-Strategie: vergleiche nur Blöcke ähnlicher Länge (Fenster ±1 Bucket)
    und gleichen Anfangsbuchstabens – vermeidet O(n²) über die ganze Flotte."""
    buckets = {}
    for b in blocks:
        key = (b[0][:1].lower(), len(b[0]) // 40)
        buckets.setdefault(key, []).append(b)
    for b in blocks:
        key = (b[0][:1].lower(), len(b[0]) // 40)
        for dk in (key[1] - 1, key[1], key[1] + 1):
            for o in buckets.get((key[0], dk), []):
                if o[0] < b[0]:
                    yield b, o


def check_article(path: Path, articles: list, *, root: Path = ROOT) -> list:
    """Gibt Liste von (artikel, regel, detail, pos) zurück.

    ``root`` ist für isolierte Vor-Publish-Prüfungen injizierbar. Die
    Produktionswache bleibt mit dem Standardwert unverändert, während das
    Publish-Gate denselben Collector auch in einer Test-Sandbox nutzen kann.
    """
    rel = str(path.relative_to(root))
    raw = path.read_text(encoding="utf-8")
    body = split_body(raw)
    blocks = blocks_of(body)
    finds = []

    # D1 + D2 (innerhalb Artikel)
    seen = {}
    for text, pos, premium in blocks:
        if is_boilerplate(text):
            continue
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if h in seen:
            finds.append((rel, "D1-EXAKT", f"Absatz doppelt (Z.{pos} ≈ Z.{seen[h]}): {text[:100]}…", pos))
            continue
        seen[h] = pos
    for a, b in near_candidates([bl for bl in blocks if not is_boilerplate(bl[0])], MIN_NEAR):
        ta, tb = a[0], b[0]
        if len(ta) < MIN_NEAR or len(tb) < MIN_NEAR:
            continue
        # Ratio-Obergrenze prüfen, bevor difflib läuft (schneller Filter)
        if min(len(ta), len(tb)) / max(len(ta), len(tb)) < RATIO_NEAR:
            continue
        if ta[:6] != tb[:6]:
            continue
        r = difflib.SequenceMatcher(None, ta, tb).ratio()
        if r >= RATIO_NEAR:
            finds.append((rel, "D2-NEAR",
                          f"Fast-Duplikat (Ratio {r:.2f}, Z.{a[1]} ≈ Z.{b[1]}): {ta[:90]}…", b[1]))

    # D5 (Sektions-Duplikate)
    secs = sections_of(body)
    for i in range(len(secs)):
        for j in range(i + 1, len(secs)):
            s1, s2 = secs[i], secs[j]
            if min(len(s1), len(s2)) / max(len(s1), len(s2)) < RATIO_NEAR:
                continue
            if s1[:10] == s2[:10]:
                r = difflib.SequenceMatcher(None, s1, s2).ratio()
                if r >= RATIO_NEAR:
                    finds.append((rel, "D5-SEKTION",
                                  f"Kapitel fast identisch (Ratio {r:.2f}): {s1[:80]}…", 0))

    # D6 (Premium-Anhänge): Blöcke nach dem Marker gegen frühere Blöcke
    premium_blocks = [b for b in blocks if b[2] and not is_boilerplate(b[0])]
    early_blocks = [b for b in blocks if not b[2] and not is_boilerplate(b[0])]
    if premium_blocks and early_blocks:
        early_ng = {ng for b in early_blocks for ng in ngrams(b[0], SHINGLE)}
        for text, pos, _ in premium_blocks:
            ng = ngrams(text, SHINGLE)
            hit = sum(1 for g in ng if g in early_ng)
            total = max(1, len(set(ng)))
            if hit >= 5 and hit / total >= 0.4:
                finds.append((rel, "D6-PREMIUM",
                              f"Premium-Anhang wiederholt früheren Text (Shingles {hit}/{total}): {text[:90]}…", pos))
    return finds


def ngrams(text: str, n: int) -> set:
    words = re.findall(r"[a-zäöüß0-9]+", text.lower())
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)} if len(words) >= n else set()


def load_blocks(paths: list, *, root: Path = ROOT) -> dict:
    """{rel: [(block_text, pos), ...]} – Boilerplate aussortiert."""
    per: dict[str, list] = {}
    for p in paths:
        try:
            raw = p.read_text(encoding="utf-8")
        except OSError:
            continue
        per[str(p.relative_to(root))] = [(t, pos)
                                         for t, pos, _ in blocks_of(split_body(raw))
                                         if not is_boilerplate(t)]
    return per


def check_cross(paths: list, *, root: Path = ROOT) -> list:
    """D3 (exakt) + D4 (near) ÜBER Artikel hinweg – NUR Report, nie Auto-Fix.

    (Befund 12.09.2026: D3/D4 standen im Docstring, wurden aber nie
    implementiert – der `articles`-Parameter von check_article war tot.
    Zwei Artikel DÜRFEN sich legitime Formulierungen teilen, deshalb bleibt
    die Gegenprüfung hier bewusst report-only; der Heilweg läuft über die
    Redaktion. Rückgabe: (rel_a, regel, detail, pos, rel_b)."""
    per = load_blocks(paths, root=root)
    finds: list = []

    # D3: exakte Übereinstimmung (SHA-256) in ≥ 2 Artikeln
    by_hash: dict = {}
    for rel, blocks in per.items():
        for t, pos in blocks:
            if len(t) < MIN_EXACT:
                continue
            by_hash.setdefault(hashlib.sha256(t.encode()).hexdigest(),
                               []).append((rel, pos, t))
    for hits in by_hash.values():
        articles = sorted({rel for rel, _, _ in hits})
        if len(articles) >= 2:
            rel_a, rel_b = articles[0], articles[1]
            pos = next(pos for rel, pos, _ in hits if rel == rel_b)
            finds.append((rel_a, "D3-X",
                          f"Absatz wortgleich in {len(articles)} Artikeln "
                          f"({rel_a} ≈ {rel_b}): {hits[0][2][:90]}…", pos, rel_b))

    # D4: Near-Duplikate über Artikel hinweg (Bucket-Strategie wie D2)
    buckets: dict = {}
    for rel, blocks in per.items():
        for t, pos in blocks:
            if len(t) < MIN_NEAR_X:
                continue
            buckets.setdefault((t[:1].lower(), len(t) // 40), []).append((rel, t, pos))
    seen_pairs = set()
    for rel_a, blocks in per.items():
        for t, pos in blocks:
            if len(t) < MIN_NEAR_X:
                continue
            key = (t[:1].lower(), len(t) // 40)
            for dk in (key[1] - 1, key[1], key[1] + 1):
                for rel_b, tb, posb in buckets.get((key[0], dk), []):
                    if rel_a == rel_b or tb < t:
                        continue
                    if min(len(t), len(tb)) / max(len(t), len(tb)) < RATIO_NEAR:
                        continue
                    if t[:6] != tb[:6]:
                        continue
                    r = difflib.SequenceMatcher(None, t, tb).ratio()
                    if r < RATIO_NEAR:
                        continue
                    pair = (min(rel_a, rel_b), max(rel_a, rel_b))
                    if pair in seen_pairs:
                        continue
                    seen_pairs.add(pair)
                    finds.append((rel_a, "D4-X",
                                  f"Fast-Duplikat über Artikel (Ratio {r:.2f}, "
                                  f"{rel_a} ≈ {rel_b}): {t[:80]}…", posb, rel_b))
    return finds


def fix_sections(body: str) -> tuple:
    """D5-Auto-Fix: fast identische H2-Kapitel (Ratio >= 0.92) – die spätere
    Version wird komplett entfernt (inkl. Überschrift). Nur Kapitel ohne
    Boilerplate und ohne Frontmatter-Bereich."""
    lines = body.split("\n")
    heads = [i for i, l in enumerate(lines) if re.match(r"^##\s+", l)]
    heads.append(len(lines))
    drop_ranges = set()
    removed = []
    for a in range(len(heads) - 1):
        for b in range(a + 1, len(heads) - 1):
            sec_a = "\n".join(lines[heads[a]:heads[a + 1]])
            sec_b = "\n".join(lines[heads[b]:heads[b + 1]])
            na = normalize(re.sub(r"```.*?```", " ", sec_a, flags=re.S))
            nb = normalize(re.sub(r"```.*?```", " ", sec_b, flags=re.S))
            if len(na) < MIN_NEAR or len(nb) < MIN_NEAR:
                continue
            if is_boilerplate(na) or is_boilerplate(nb):
                continue
            if min(len(na), len(nb)) / max(len(na), len(nb)) < RATIO_FIX - 0.1:
                continue
            r = difflib.SequenceMatcher(None, na, nb).ratio()
            if r >= RATIO_FIX:
                drop_ranges.add((heads[b], heads[b + 1]))
                removed.append(("D5-FIX", f"Kapitel {b + 1} entfernt (Ratio {r:.2f}): {na[:70]}…"))
                break
    if not drop_ranges:
        return body, 0, []
    keep = []
    prev = 0
    for start, end in sorted(drop_ranges):
        keep.append("\n".join(lines[prev:start]))
        prev = end
    keep.append("\n".join(lines[prev:]))
    return "\n".join(keep), len(removed), removed


def auto_fix(rel: str, body: str) -> tuple:
    """Entfernt exakte + fast-exakte Duplikate (spätere Version) im selben Artikel.
    Zwei Ebenen: Absätze (D1/D2) und H2-Kapitel (D5)."""
    blocks = blocks_of(body)
    if not blocks:
        return body, 0, []
    removed = []

    # Exakte Duplikate (D1)
    seen = {}
    keep_lines = []
    chunks = body.split("\n\n")
    for i, chunk in enumerate(chunks):
        c_n = normalize(re.sub(r"```.*?```", " ", chunk, flags=re.S))
        if not c_n:
            keep_lines.append(i)
            continue
        h = hashlib.sha256(c_n.encode("utf-8")).hexdigest()
        if len(c_n) >= MIN_EXACT and h in seen and "premium-length" not in c_n:
            removed.append(("D1-FIX", f"Z.{i}: {c_n[:70]}…"))
            continue
        seen[h] = i
        keep_lines.append(i)

    # Near-Duplikate (D2) mit hoher Schwelle (RATIO_FIX)
    keep = [chunks[i] for i in keep_lines]
    drop = set()
    cand = []
    for k, text in enumerate(keep):
        c_n = normalize(re.sub(r"```.*?```", " ", text, flags=re.S))
        if len(c_n) >= MIN_NEAR:
            cand.append((k, c_n))
    for i in range(len(cand)):
        for j in range(i + 1, len(cand)):
            ti, tj = cand[i][1], cand[j][1]
            if min(len(ti), len(tj)) / max(len(ti), len(tj)) < RATIO_FIX - 0.1:
                continue
            if ti[:6] != tj[:6]:
                continue
            r = difflib.SequenceMatcher(None, ti, tj).ratio()
            len_diff = abs(len(ti) - len(tj)) / max(len(ti), len(tj))
            if r >= RATIO_FIX and len_diff <= FIX_LEN_DIFF:
                # spätere Version entfernen (größerer Index).
                # ACHTUNG (Befund 12.09.2026): i/j sind Indizes in `cand`
                # (nur Blöcke >= MIN_NEAR), `drop` adressiert aber `keep`
                # (ALLE Blöcke). Ohne Rückübersetzung per cand[..][0] würde
                # bei kürzeren Blöcken dazwischen der FALSCHER Absatz
                # entfernt (Index-Drift) – hier der Hebel, der den
                # Near-Duplikat-Fix über unvollständige cand-Listen rettet.
                later = cand[max(i, j)][0]
                if later not in drop:
                    drop.add(later)
                    removed.append(("D2-FIX", f"Absatz {later}: {ti[:70]}…"))

    out = "\n\n".join(ch for k, ch in enumerate(keep) if k not in drop)

    # Zweite Ebene: H2-Kapitel-Duplikate (D5)
    out2, n5, rem5 = fix_sections(out)
    removed.extend(rem5)
    return out2, len(removed), removed


def run_selftest() -> list:
    fehler = []
    # Fall 1: exaktes Duplikat wird erkannt (D1-Logik direkt geprüft)
    b1 = ("Einleitung.\n\n"
          "Das ist ein längerer Beispielabsatz mit mehreren Wörtern, der exakt doppelt vorkommt und "
          "deshalb als Duplikat gelten muss, weil er wortgleich wiederholt wird.\n\n"
          "Das ist ein längerer Beispielabsatz mit mehreren Wörtern, der exakt doppelt vorkommt und "
          "deshalb als Duplikat gelten muss, weil er wortgleich wiederholt wird.")
    blocks = blocks_of(b1)
    hashes = [hashlib.sha256(t.encode()).hexdigest() for t, _, _ in blocks]
    if len(hashes) == len(set(hashes)):
        fehler.append("Fall 1 (D1-Erkennung): exaktes Duplikat nicht erkannt")
    # Fall 2: Auto-Fix entfernt exaktes Duplikat
    out, n, _ = auto_fix("t", b1)
    if n != 1 or out.count("Beispielabsatz") != 1:
        fehler.append(f"Fall 2 (D1-Fix): erwartet 1 Entfernung/1 Treffer, bekam {n}/{out.count('Beispielabsatz')}")
    # Fall 3: verschiedene Absätze werden NICHT gefixt (kein False-Positive)
    b2 = "Absatz eins über Stromsparen und ganz andere Inhalte.\n\nAbsatz zwei über Versicherungen mit völlig anderen Themen."
    _, n2, _ = auto_fix("t", b2)
    if n2 != 0:
        fehler.append(f"Fall 3 (False-Positive): unabhängige Absätze gefixt ({n2})")
    # Fall 4: D6-Marker-Erkennung (Premium-Anhänge werden als solche markiert)
    b3 = ("Erster Teil des Artikels mit ausreichend langem Inhalt, der über achtzig Zeichen "
          "hinausgeht und deshalb als Block zählt.\n\n<!-- premium-length-2026 -->\n\n"
          "Zweiter Teil des Artikels, ebenfalls lang genug, mit dem Premium-Marker davor "
          "und Inhalt, der als Anhang markiert werden muss.")
    early = [b for b in blocks_of(b3) if not b[2]]
    late = [b for b in blocks_of(b3) if b[2]]
    if not (early and late and late[0][2]):
        fehler.append("Fall 4 (D6-Marker): Premium-Marker-Erkennung fehlgeschlagen")
    # Fall 5: Near-Duplikat-Erkennung (D2) über blocks_of + buckets
    b5 = ("Kurz.\n\n"
          "Der DNS-Server ist wie ein Telefonbuch des Internets und übersetzt Namen in Adressen, "
          "damit dein Browser die richtige Seite findet und lädt.\n\n"
          "Der DNS-Server ist wie ein Telefonbuch des Internets und übersetzt Namen in Adressen, "
          "damit dein Browser die richtige Seite findet und lädt – fast wortgleich wiederholt.")
    b5_blocks = blocks_of(b5)
    pairs = list(near_candidates(b5_blocks, MIN_NEAR))
    hit = any(difflib.SequenceMatcher(None, a[0], b[0]).ratio() >= RATIO_NEAR
              for a, b in pairs)
    if not hit:
        fehler.append("Fall 5 (D2-Near): Fast-Duplikat nicht erkannt")
    # Fall 6: Korruptions-Muster der 7 Alt-Artikel (12.09.2026): wiederholte
    # Intro-Blöcke, die als "---\n<Einleitung>" vorliegen. Die ERSTE Kopie
    # muss erkannt UND im --fix-Modus entfernt werden (davor: Fingerprint-
    # Mismatch, Kopie blieb für immer).
    intro = ("Warum zahlen Millionen Haushalte Monat für Monat zu viel für ihren "
             "Anschluss? Weil Treue im Markt leider nicht belohnt wird, im Gegenteil.")
    b6 = (intro + "\n\n"
          "---\n" + intro + "\n\n"
          "---\n\n"
          "💡 **Schnell-Tipp von FranksFinanzcheck:** Vergleiche jetzt deine Optionen.")
    b6_hashes = {hashlib.sha256(t.encode()).hexdigest()
                 for t, _, _ in blocks_of(b6) if len(t) >= MIN_EXACT}
    if len(b6_hashes) != 1:
        fehler.append("Fall 6 (Trennlinie): trennliniengeklebte Kopie nicht als "
                      "Duplikat erkannt")
    out6, n6, _ = auto_fix("t", b6)
    if n6 != 1 or out6.count("Warum zahlen") != 1:
        fehler.append(f"Fall 6 (Trennlinie-Fix): erwartet 1/1, bekam {n6}/{out6.count('Warum zahlen')}")
    if "\n---\n\n" not in out6:
        fehler.append("Fall 6 (Trennlinie-Fix): Trennlinie vor CTA-Box wurde mitgelöscht")
    # Fall 7: D2-Near mit kurzen Absätzen ZWISCHEN den Kandidaten – der Fix
    # darf die spätere (nahe) Version entfernen, nicht das Original
    # (Regression: cand/keep-Index-Drift in auto_fix).
    a7 = ("Der Gaspreis je Kilowattstunde liegt aktuell etwa bei neun Cent, und wer früh "
          "vergleicht, sichert sich den günstigeren Tarif für ein ganzes Jahr vorab.")
    a7b = ("Der Gaspreis je Kilowattstunde liegt aktuell etwa bei neun Cent, und wer früh "
           "vergleicht, sichert sich den günstigeren Tarif für ein ganzes Jahr im Voraus.")
    b7 = "Kurzer Absatz hier.\n\nKurz zwei.\n\n" + a7 + "\n\n" + a7b + "\n\nKurz drei."
    out7, n7, _ = auto_fix("t", b7)
    if n7 != 1 or "im Voraus" in out7:
        fehler.append(f"Fall 7 (D2-Index-Drift): falscher Absatz entfernt ({n7})")
    if a7 not in out7:
        fehler.append("Fall 7 (D2-Index-Drift): Original entfernt statt der Kopie")

    # ------------------------------------------------------------
    # Fälle 8–11: HAUS-TEMPLATES (Dauerheilung Issue #676, 09.10.2026)
    # ------------------------------------------------------------
    # Eingefrorener Originalbefund: Der End-CTA stand wortgleich in zwei
    # Artikeln vom 07.10. und wurde als D3-X gemeldet, obwohl
    # affiliate_intent_contract genau diesen Wortlaut vorschreibt. RD1 ist
    # blockierend, Cross-Artikel-Funde sind nie auto-heilbar → der Deploy
    # starb 13× in Folge, die komplette Auslieferung fror ein, der neueste
    # Artikel lieferte 404. Diese vier Fälle sind der Sabotage-Schutz: Wer
    # die SSOT-Ableitung wieder durch eine Whitelist ersetzt, wird rot.
    cta_676 = ("👉 **Jetzt das Tagesgeld-Angebot der C24 Bank ansehen:** "
               "[**→ Jetzt C24 Bank Tagesgeld ansehen**](/go/tagesgeld/)")
    if not is_boilerplate(cta_676):
        fehler.append("Fall 8 (#676 Haus-CTA): vertraglich vorgeschriebener "
                      "End-CTA wird wieder als Duplikat gemessen")
    grund8 = haus_template_grund(cta_676)
    if "affiliate_intent_contract" not in grund8:
        fehler.append(f"Fall 8 (#676 Begründung): Ausnahme nennt nicht die "
                      f"Vertrags-SSOT („{grund8}“) – eine stille Ausnahme ist "
                      "ein Scheingrün")

    # Fall 9: Die Ausnahme ist KEIN Freibrief. Derselbe CTA-Block mit einem
    # eigenen Redaktionssatz muss wieder gemessen werden – sonst könnte
    # beliebiger Inhalt hinter einer CTA verschwinden.
    cta_redaktionell = (cta_676 + " Beachte aber, dass eine lange Zinsbindung "
                        "deiner Anlagestrategie widersprechen kann, wenn du "
                        "kurzfristig Liquidität brauchst und deshalb einen "
                        "Vergleich der Angebote lieber verschieben möchtest.")
    if is_boilerplate(cta_redaktionell):
        fehler.append("Fall 9 (Kein Freibrief): CTA-Block mit eigenem "
                      "Redaktionssatz wurde als Haus-Template ausgenommen")

    # Fall 10: Unicode-Bindestriche. Der Bestand schreibt „Affiliate‑Links"
    # mit U+2011; gegen `text.lower()` traf das Muster „affiliate-links"
    # nie, die Offenlegung galt als Inhalt und wurde als D3/D4 gemeldet.
    offenlegung_u2011 = ("***Transparenz:** Dieser Artikel enthält "
                         "Affiliate\u2011Links (Werbung). Beim Abschluss über "
                         "einen Link erhalten wir eine Provision – für dich "
                         "entstehen keine Mehrkosten.*")
    if not is_boilerplate(offenlegung_u2011):
        fehler.append("Fall 10 (U+2011): Offenlegung mit weichem Bindestrich "
                      "wird wieder als Duplikat gemessen")

    # Fall 11: Haus-Formel MIT Platzhalter (News-Kompakt-Dateline). Dieselbe
    # Zeile steht in jedem News-Artikel, nur das Datum wechselt – D4-X maß
    # sie als Fast-Duplikat (Ratio 0.98) zwischen markt- und energie-update.
    dateline = ("**Stand: 06.10.2026.** Dieser News\u2011Kompakt\u2011Artikel "
                "ordnet eine aktuelle Entwicklung ein. Konditionen und Regeln "
                "können sich ändern – prüfe Details immer beim jeweiligen "
                "Anbieter.")
    if not is_boilerplate(dateline):
        fehler.append("Fall 11 (News-Dateline): Haus-Formel mit Datum wird "
                      "wieder als Fast-Duplikat gemessen")
    # … aber nur, solange sie die Formel ist. Ein eigener Satz danach hebt
    # die Ausnahme auf (derselbe Grundsatz wie Fall 9).
    dateline_eigenbau = ("**Stand: 06.10.2026.** Dieser News-Kompakt-Artikel "
                         "ordnet eine aktuelle Entwicklung ein, die vor allem "
                         "Haushalte mit Wärmepumpe betrifft, weil der "
                         "Netzbetreiber die Einspeisevergütung gesenkt hat und "
                         "deshalb viele Verträge neu gerechnet werden müssen.")
    if is_boilerplate(dateline_eigenbau):
        fehler.append("Fall 11b (News-Dateline): eigenständig ausformulierter "
                      "Artikelanfang wurde als Haus-Formel ausgenommen")

    # Fall 12: Echter redaktioneller Inhalt bleibt messbar – die Ausnahme
    # darf die Wache nicht blind machen (Gegenprobe zu 8–11).
    redaktion = ("Der Gaspreis je Kilowattstunde liegt aktuell etwa bei neun "
                 "Cent, und wer früh vergleicht, sichert sich den günstigeren "
                 "Tarif für ein ganzes Jahr im Voraus und spart damit deutlich "
                 "mehr als mit einer verspäteten Entscheidung im Herbst.")
    if is_boilerplate(redaktion):
        fehler.append("Fall 12 (Gegenprobe): redaktioneller Absatz wurde als "
                      "Haus-Template ausgenommen – die Wache wäre blind")

    # Fall 13: Die SSOT-Quellen sind ohne Import-Kette lesbar. `ki_shared`,
    # `cta_builder` und `news_writer` ziehen PyYAML nach; würde die Ableitung
    # importieren statt zu lesen, fiele die Ausnahme in jeder pyyaml-freien
    # Umgebung STILL aus – und #676 kehrte als Dauer-Fehlalarm zurück.
    luecken = haus_template_luecken()
    if luecken:
        fehler.append(f"Fall 13 (SSOT-Lücke): Haus-Template-Quellen nicht "
                      f"lesbar – {luecken[0][:120]}")
    if not haus_formeln():
        fehler.append("Fall 13b (SSOT-Ableitung): keine Haus-Formel mit "
                      "Platzhalter abgeleitet – die News-Dateline wäre blind")
    if not haus_texte():
        fehler.append("Fall 13c (SSOT-Ableitung): kein Haus-Text abgeleitet – "
                      "Disclaimer/Offenlegung wären blind")

    # Fall 14: Eine umbenannte Konstante ist eine LÜCKE, kein stiller
    # Verzicht. Wer die SSOT verschiebt, muss rot sehen (fail-closed).
    _wert, grund = _ssot_wert("news_writer", "STAND_INTRO_GIBT_ES_NICHT")
    if not grund:
        fehler.append("Fall 14 (Lücken-Meldung): eine fehlende SSOT-Konstante "
                      "wurde nicht als Lücke gemeldet")
    return fehler


def main() -> int:
    fehler = run_selftest()
    if fehler or SELFTEST_ONLY:
        for f in fehler:
            print("🛑 " + f)
        if fehler:
            print("SELFTEST FEHLGESCHLAGEN – nichts geschrieben.")
            return 2
        print("✅ Duplikat-Selbsttest: 14 Fälle grün (Trennlinien-Muster, "
              "Index-Drift, Haus-Templates aus der CTA-/News-SSOT #676, "
              "kein Freibrief für Redaktionssätze, SSOT ohne Import-Kette).")
        return 0

    # FAIL-CLOSED VOR JEDER MESSUNG (#676): Die Haus-Template-Ausnahme wird
    # aus den erzeugenden Modulen abgeleitet. Ist eine dieser Quellen nicht
    # lesbar, fehlt genau ihre Ausnahme – die Wache würde vertraglich
    # vorgeschriebene CTA-/Disclaimer-Blöcke wieder als Plagiat messen und
    # den Deploy einfrieren. Das ist keine Warnung, sondern ein
    # Werkzeugfehler: Eine blinde Messung darf nie als Grün durchgehen.
    luecken = haus_template_luecken()
    if luecken:
        print("🛑 Haus-Template-SSOT unvollständig (Exit 2, fail-closed):")
        for luecke in luecken:
            print(f"   ❔ {luecke}")
        print("   Ohne diese Quellen fehlt die Ausnahme für Haus-CTA/-Formeln –")
        print("   die Messung würde Format als Inhaltsklau werten (Klasse #676).")
        return 2

    today = date.today().isoformat()
    paths = sorted(POSTS.glob("*/index.md"))
    paths = [p for p in paths if p.name != "_index.md"]
    if NEW_ONLY:
        paths = [p for p in paths
                 if re.search(rf"^date:\s*\"?{today}", p.read_text(encoding="utf-8"), re.M)
                 and "draft: false" in p.read_text(encoding="utf-8")]
        if not paths:
            print("Duplikat-Gate: keine neuen Artikel heute – OK.")
            return 0

    all_finds, fixed_any = [], False
    for p in paths:
        raw = p.read_text(encoding="utf-8")
        body = split_body(raw)
        if DO_FIX:
            new_body, n, removed = auto_fix(str(p.relative_to(ROOT)), body)
            if n:
                p.write_text(raw.replace(body, new_body), encoding="utf-8")
                fixed_any = True
                for _, d in removed:
                    all_finds.append((str(p.relative_to(ROOT)), "FIX", d, 0))
                print(f"  ✂ {p.relative_to(ROOT)}: {n} Duplikat(e) entfernt")
        all_finds += check_article(p, paths)

    # D3/D4 über Artikel hinweg (einmalig, report-only; Sicherheit:
    # Cross-Artikel-Funde werden NIEMALS auto-gefixed). Im Engine-Modus
    # (--new-only) zählt nur, was HEUTIGE Artikel berührt – ein Fund
    # zwischen zwei Alt-Artikeln darf den Publikationstag nicht blockieren.
    focus = ({str(p.relative_to(ROOT)) for p in paths}
             if NEW_ONLY else None)
    for rel_a, rule, detail, pos, rel_b in check_cross(paths):
        if focus is not None and not ({rel_a, rel_b} & focus):
            continue
        all_finds.append((rel_a, rule, detail, pos))

    # deduplizieren (Fix + Check desselben Fundes)
    uniq, seen = [], set()
    for f in all_finds:
        k = (f[0], f[1], f[2][:60])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(f)

    d1 = [f for f in uniq if f[1] == "D1-EXAKT"]
    d2 = [f for f in uniq if f[1] == "D2-NEAR"]
    d3 = [f for f in uniq if f[1] == "D3-X"]
    d4 = [f for f in uniq if f[1] == "D4-X"]
    d5 = [f for f in uniq if f[1] == "D5-SEKTION"]
    d6 = [f for f in uniq if f[1] == "D6-PREMIUM"]
    fx = [f for f in uniq if f[1] == "FIX"]

    # Report
    lines = [f"# 🔁 DUPLIKAT-REPORT (duplikat_guard.py)",
             f"**Stand:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · Modus: {'FIX' if DO_FIX else 'REPORT'}" +
             (" · Engine (nur heute)" if NEW_ONLY else ""),
             "",
             f"| Regel | Anzahl |",
             f"|---|---|",
             f"| D1 Exakt (im Artikel) | {len(d1)} |",
             f"| D2 Near (im Artikel) | {len(d2)} |",
             f"| D3 Exakt (über Artikel) | {len(d3)} |",
             f"| D4 Near (über Artikel) | {len(d4)} |",
             f"| D5 Sektion (im Artikel) | {len(d5)} |",
             f"| D6 Premium-Anhang | {len(d6)} |",
             f"| Auto-Fixes | {len(fx)} |",
             ""]
    if uniq:
        lines.append("## Fundstellen (Auswahl)")
        for rel, regel, detail, pos in uniq[:40]:
            lines.append(f"- `{rel}` **{regel}**: {detail}")
    lines.append("")
    lines.append("_Kein Duplikat darf den Leser zweimal dieselbe Information lesen lassen._")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    with HISTORY.open("a", encoding="utf-8") as h:
        h.write(json.dumps({"date": today, "d1": len(d1), "d2": len(d2),
                            "d3": len(d3), "d4": len(d4), "d5": len(d5),
                            "d6": len(d6), "fix": len(fx)}, ensure_ascii=False) + "\n")

    if AS_JSON:
        print(json.dumps({"duplicates": [{"file": f[0], "rule": f[1], "detail": f[2]} for f in uniq]},
                         ensure_ascii=False, indent=2))
        return 1 if (d1 or d2 or d3 or d4 or d5 or d6) and NEW_ONLY else 0

    print(f"Duplikat-Audit: {len(paths)} Artikel | D1 {len(d1)} · D2 {len(d2)} · D3 {len(d3)} · D4 {len(d4)} · D5 {len(d5)} · D6 {len(d6)} · Fixes {len(fx)}")
    for rel, regel, detail, pos in uniq[:25]:
        print(f"  {'❌' if regel.startswith('D') else '✂'} [{regel:>10}] {rel} Z.{pos}: {detail[:110]}")
    if NEW_ONLY and (d1 or d2 or d3 or d4 or d5 or d6):
        print("❌ Duplikat-Gate nicht bestanden – neue Artikel enthalten Redundanz!")
        return 1
    if not uniq:
        print("✅ Keine Duplikate gefunden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
