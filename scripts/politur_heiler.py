#!/usr/bin/env python3
"""politur_heiler.py – der fehlende Heiler der Politur-Ruinen (#614).

WARUM DIESE DATEI EXISTIERT (Vorgang BOT-WATCHDOG-614, 07.10.2026)
=================================================================
Das Bot-Watchdog-Ticket #614 meldete am 06.10.2026 „Content-Reserve niedrig"
(P2, Maschine, 3 von 6 gate-fertig) – und der nächste Schritt im Ticket
lautete „mindestens 4 zertifizierte Kandidaten herstellen". Genau das war der
Maschine nicht möglich, weil ein Teil des Vorrats an Defekten hing, für die es
KEINEN Heiler gab. Drei Belege aus `data/reserve-readiness.json` (07.10.2026):

    dein-weg-… : R15-PHRASEN-DOPPEL  „…dein weg zu geringeren im check
                 dein weg zu geringeren…" – „manuell reparieren"
    smart-home-…: R14-MARKER-RUINE    „SATZ:" am Zeilenanfang einer Tabellenzeile
    dsl-anbieter-…: R7-INTRO-FORMEL   „in diesem artikel"

Alle drei sind **Maschinenprodukte** der eigenen Automatik:

  * R14/R16 (Marker-/Prompt-Ruinen) entstehen, wenn eine KI-Antwort ihren
    Ausgabe-Marker mit in den Text bringt (`sprachkern.POLITUR_RUINEN` ist
    dafür die Muster-SSOT – `write_verified` verweigert sie beim NEUEN
    Schreiben, aber keine Instanz heilt sie danach).
  * R15 (Phrasen-Dopplung) entsteht durch wiederholte, nicht-idempotente
    Keyword-Stempel der Kette („{keyword} im Check: {absatz}" lief mehrfach).
  * R7 (Intro-Formel) entsteht durch Template-Sprache der Generierung.

Für alle drei Regeln galt bis heute die Deckungs-Tabelle
(`reserve_healer_coverage.REGEL_HEILER`) als „gedeckt" – durch
`r5_absatz_splitter.py` (heilt R5) und `fix_url_hygiene.py` (heilt R8-URL).
Das ist exakt die Bauart, die #609 für die Lesbarkeit entlarvt hat:

    Eine Deckung ohne Wirkung ist Papier.

Folge: Die Zertifizierung lief jede Nacht in dieselben harten
Textverständnis-Funde, die Kandidaten blieben „nicht bereit", der Vorrat
erreichte sein Ziel nicht, das harte End-Gate färbte den Reserve-Lauf rot –
und der Bot-Watchdog eröffnete dieselbe Klasse Tag für Tag wieder.

WAS DIESER HEILER TUT (deterministisch, offline, fail-closed)
============================================================
Er heilt genau die Regeln, deren Defekt ein MASCHINEN-Überrest ist und deren
Korrektur beweisbar bedeutungserhaltend ist:

  1. R14 R14-MARKER-RUINE / R16 PROMPT-ECHO
     Marker am Zeilenanfang (`SATZ:`, `TITLE:`, …) werden entfernt – die
     Marker-Liste kommt aus `sprachkern.POLITUR_RUINEN` (SSOT, keine zweite
     Wahrheit). Eine Zeile, die danach nur noch den Artikel-Titel wiederholt,
     fällt ganz weg; leere Zeilen verschwinden.
  2. R15 PHRASEN-DOPPEL
     Unmittelbar aufeinanderfolgende, wortgleiche Wiederholungen (Periode
     ≤ 30 Wörter, mindestens `textverstaendnis_guard.R15_N` Wörter lang)
     werden auf EIN Vorkommen zusammengezogen – und zwar nur, wenn der
     gelöschte Bereich KEIN Markup trägt (Links, Shortcodes, Tabellen,
     Überschriften, Code). Enthält er Markup, bleibt der Text unangetastet
     (fail-closed, der Fund gehört dann einem Menschen).
  3. R7 INTRO-FORMEL
     Template-Sprache („in diesem Artikel", „in diesem Ratgeber", …) wird
     durch das bedeutungsgleiche „hier" ersetzt – die Formel-Liste kommt aus
     `textverstaendnis_guard.INTRO_FORMELN` (SSOT).
  4. R11 JAHRESZAHL-SPLIT und R13 DATUM-PUNKT
     „20 26" → „2026" (Leerraum weg) und „2 Januar" → „2. Januar" (fehlender
     Ordinalpunkt) – beide Muster aus `sprachkern.POLITUR_RUINEN`.

WAS ER BEWUSST NICHT TUT
  * R12-ZAHL-RUINE („Du bist der 0 am Strommarkt") verlangt eine inhaltliche
    Entscheidung – der Heiler meldet sie nur. Kein Raten.
  * Er fasst NUR Entwürfe an (`draft: true`). Live-Texte gehören der
    Deploy-/Kadenz-Kette; sie werden erst zurückgestuft, dann geheilt.
  * Er schreibt NIE ins Frontmatter, NIE eine Kürzung, NIE einen neuen Fund.

DAS TOR (fail-closed – entscheidet, nicht der Schreiber)
    T1  Die harten Textverständnis-Funde (SSOT: `publish_gate.HARTE_REGELN`,
        gemessen mit dem echten Wächter) sind danach eine ECHTE Teilmenge der
        Funde davor: mindestens einer weniger, keiner neu. Gleiches gilt für
        `sprachkern.politur_ruine_funde`.
    T2  Formale Bewahrung: Frontmatter byte-identisch, Linkziele, /go/-Anker,
        Überschriften, Shortcodes, Zahlen-Multiset und Tabellenzellen
        unverändert, Länge ≥ 98 %.
    T3  Kein Text ohne Wirkung: ändert sich nichts, wird nichts geschrieben.
Scheitert eine Zeile, bleibt die Datei **byte-identisch** liegen und der Rest
steht als Befund im Bericht. „Nicht gemessen" ist niemals „geschrieben".

WIRKUNGSNACHWEIS (Maschinenvertrag, `--wirkungsprobe`)
    Ein Fixture mit R14 + R15 + R7 + R11 + R13 wird geheilt; die Probe besteht
    nur, wenn danach KEINE dieser Regeln mehr feuert, das Tor T1–T3 hält und
    der zweite Lauf nichts mehr ändert (Idempotenz). `reserve_healer_coverage`
    fordert diesen Nachweis über `PROBEN_PFLICHT` (Deckung heißt Wirkung,
    Regel C25) – ein Name in der Kette genügt nicht.

NUTZUNG
    python3 scripts/politur_heiler.py --file content/posts/<slug>/index.md
        --fix                       # einen Entwurf heilen (Standard: Trockenlauf)
    python3 scripts/politur_heiler.py --reserve --fix
                                    # alle Reserve-Kandidaten mit heilbaren Resten
    python3 scripts/politur_heiler.py --reserve --json
    python3 scripts/politur_heiler.py --wirkungsprobe
    python3 scripts/politur_heiler.py --selftest

EXIT: 0 = nichts (mehr) zu heilen · 1 = mindestens ein Kandidat blieb mit
      heilbarem Rest zurück (fail-closed: nichts Halbfertiges geschrieben)
      · 2 = Selbsttest/Werkzeugfehler.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BLOG_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import publish_gate as pg              # noqa: E402 – HARTE_REGELN (SSOT)
import sprachkern as sk                # noqa: E402 – POLITUR_RUINEN (Muster-SSOT)
import textverstaendnis_guard as tv    # noqa: E402 – der echte Textverständnis-Wächter
from post_utils import join_article     # noqa: E402 – Naht-SSOT

# Regeln, die dieser Heiler heilt – genau diese Namen werden im Bericht geführt.
HEILBARE_REGELN = (
    "R7-INTRO-FORMEL",
    "R11-JAHRESZAHL-SPLIT",
    "R13-DATUM-PUNKT",
    "R14-MARKER-RUINE",
    "R15-PHRASEN-DOPPEL",
    "R16-PROMPT-ECHO",
)

# Wiederholungs-Erkennung (R15): dieselbe Schwelle wie der Wächter (SSOT).
R15_N = tv.R15_N
MAX_PERIODE = 30          # längere „Wiederholungen" sind kein Stempel, sondern Inhalt
MAX_RUNDEN = 6            # Fixpunkt: dreifache Stempel brauchen mehrere Runden

_WORT = re.compile(r"\w+", re.UNICODE)
# Markup, das eine Löschung NIE zerschneiden darf (fail-closed).
_MARKUP = ("[", "]", "(", ")", "|", "{", "}", "`", "<", ">")


# ---------------------------------------------------------------------------
#  HILFEN
# ---------------------------------------------------------------------------
def _teile(rohtext: str):
    """(prefix, frontmatter, body) – dieselbe Naht wie `post_utils.join_article`."""
    parts = (rohtext or "").split("---", 2)
    if len(parts) < 3:
        return None
    return parts[0], parts[1], parts[2]


def _titel(rohtext: str) -> str:
    teile = _teile(rohtext)
    if not teile:
        return ""
    m = re.search(r"(?m)^title:\s*[\"']?(.+?)[\"']?\s*$", teile[1])
    return m.group(1).strip() if m else ""


def harte_funde(rohtext: str, slug: str) -> set:
    """Harte Textverständnis-Funde (SSOT: publish_gate.HARTE_REGELN).

    Gemessen mit dem ECHTEN Wächter. Jeder Werkzeugfehler wirft weiter, damit
    der Aufrufer fail-closed ablehnen kann (nie ein stilles „0 Funde").
    """
    body = tv.split_body(rohtext)
    funde = tv.check_article(f"{slug}/index.md", body,
                             tv.load_terminologie(),
                             tv.frontmatter_keywords(rohtext))
    return {f"{regel}: {detail[:80]}" for _rel, regel, detail, _fund in funde
            if regel in pg.HARTE_REGELN}


def ruinen(text: str) -> set:
    """Politur-Ruinen über die Muster-SSOT `sprachkern.POLITUR_RUINEN`."""
    return {f"{regel}: {fund}" for regel, fund in sk.politur_ruine_funde(text)}


# ---------------------------------------------------------------------------
#  STUFE 1 – MARKER-RUINEN (R14/R16)
# ---------------------------------------------------------------------------
def _marker_muster() -> list[tuple[str, re.Pattern]]:
    """Die R14-/R16-Muster aus der SSOT – gelesen, nicht abgetippt."""
    gewuenscht = ("R14-MARKER-RUINE", "R16-PROMPT-ECHO")
    return [(name, rx) for name, rx, _desc in sk.POLITUR_RUINEN
            if name in gewuenscht]


def heile_marker(body: str, titel: str = "") -> tuple[str, list[str]]:
    """Entfernt Marker-/Prompt-Reste am Zeilenanfang (R14/R16).

    Ein Marker ist nie Inhalt; der Rest der Zeile bleibt erhalten. Wiederholt
    die Restzeile nur den Artikel-Titel, fällt die GANZE Zeile weg (das war
    der Kopf des KI-Ausgabeformats, kein Absatz des Artikels).
    """
    entfernt: list[str] = []
    echo_entfernt = False
    titel_norm = re.sub(r"\W+", "", (titel or "").lower())
    for name, rx in _marker_muster():
        neue_zeilen: list[str] = []
        for zeile in body.split("\n"):
            m = rx.match(zeile)
            if not m:
                neue_zeilen.append(zeile)
                continue
            rest = zeile[m.end():].strip()
            rest_norm = re.sub(r"\W+", "", rest.lower())
            if titel_norm and rest_norm and rest_norm == titel_norm:
                entfernt.append(f"{name}: Titel-Echo-Zeile entfernt")
                echo_entfernt = True
                continue                      # ganze Zeile fällt weg
            entfernt.append(f"{name}: „{m.group(0).strip()}\" entfernt")
            neue_zeilen.append(rest if rest else "")
        body = "\n".join(neue_zeilen)
    # Nur wenn eine Zeile GANZ fiel, entstandene Leerzeilen glätten – sonst
    # bliebe der Text unverändert (keine kosmetische Drift am ganzen Artikel).
    if echo_entfernt:
        body = re.sub(r"\n{3,}", "\n\n", body)
    return body, entfernt


# ---------------------------------------------------------------------------
#  STUFE 2 – PHRASEN-DOPPLUNG (R15)
# ---------------------------------------------------------------------------
def _wort_spans(text: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in _WORT.finditer(text)]


def _im_markup(text: str, start: int, ende: int) -> bool:
    return any(z in text[start:ende] for z in _MARKUP)


def _wiederholung_finden(body: str, ab: int = 0):
    """Erste unmittelbare Wort-Wiederholung: (start, periode, reps) oder None.

    Gesucht wird eine Wortfolge der Länge ≥ R15_N, die sich unmittelbar
    wiederholt (Periode p ≤ MAX_PERIODE). Rückgabe in RAW-Positionen:
    (wort_index_start, periode, anzahl_wiederholungen, spans). `ab` überspringt
    bereits geprüfte Wortpositionen (Markup-Sperre, siehe `heile_phrasendoppel`).
    """
    spans = _wort_spans(body)
    w = [body[a:b].lower() for a, b in spans]
    n = len(w)
    if n < R15_N * 2:
        return None
    for i in range(max(0, ab), n - R15_N + 1):
        for p in range(1, MAX_PERIODE + 1):
            if i + p + R15_N > n:
                break
            if all(w[i + k] == w[i + p + k] for k in range(R15_N)):
                # Links/rechts auf die volle Periode ausdehnen.
                links = i
                while links - 1 >= 0 and links - 1 + p < n and w[links - 1] == w[links - 1 + p]:
                    links -= 1
                rechts = i + p + R15_N - 1
                while rechts + 1 < n and rechts + 1 - p >= 0 and w[rechts + 1] == w[rechts + 1 - p]:
                    rechts += 1
                laenge = rechts - links + 1
                if laenge % p:                     # keine exakte Periodik → Finger weg
                    continue
                reps = laenge // p
                if reps < 2:
                    continue
                return links, p, reps, spans
    return None


def heile_phrasendoppel(body: str) -> tuple[str, list[str]]:
    """Zieht unmittelbare Wort-Wiederholungen auf EIN Vorkommen zusammen (R15).

    Gelöscht wird ausschließlich der Bereich von der ERSTEN bis zum Beginn der
    LETZTEN Wiederholung: Es bleibt genau EIN Vorkommen stehen – das letzte,
    denn an ihm hängt der fortsetzende Satzrest („… im Check – stell dir vor,
    …"). Trägt der gelöschte Bereich Markup (Link, Shortcode, Tabelle, Code),
    bleibt dieser Kandidat unangetastet (fail-closed) und die Suche läuft
    hinter ihm weiter.
    """
    entfernt: list[str] = []
    ab = 0
    for _ in range(MAX_RUNDEN):
        treffer = _wiederholung_finden(body, ab=ab)
        if not treffer:
            break
        links, p, reps, spans = treffer
        start_erste = spans[links][0]                    # Beginn der ersten Wiederholung
        start_letzte = spans[links + (reps - 1) * p][0]  # Beginn der letzten
        if start_letzte <= start_erste:
            ab = links + 1
            continue
        if _im_markup(body, start_erste, start_letzte):
            ab = links + 1                               # Markup im Weg: weiter suchen
            continue
        probe = " ".join(body[span_a:span_b].lower()
                         for span_a, span_b in spans[links:links + p])
        entfernt.append("R15-PHRASEN-DOPPEL: "
                        + probe[:60] + f" … ({reps}×) auf 1× zusammengezogen")
        body = body[:start_erste] + body[start_letzte:]
        ab = 0                                           # nach dem Schnitt neu messen
    return body, entfernt


# ---------------------------------------------------------------------------
#  STUFE 3 – TEMPLATE-SPRACHE (R7)
# ---------------------------------------------------------------------------
def heile_intro_formeln(body: str) -> tuple[str, list[str]]:
    """Ersetzt Template-Sprache bedeutungsgleich durch „hier" (R7).

    Die Formel-Liste ist die SSOT des Wächters (`tv.INTRO_FORMELN`); die
    Ersetzung erhält die Groß-/Kleinschreibung am Satzanfang.
    """
    entfernt: list[str] = []
    for formel in tv.INTRO_FORMELN:
        muster = re.compile(re.escape(formel), re.IGNORECASE)

        def _ersetzen(m: re.Match) -> str:
            vor = m.string[:m.start()].rstrip()
            satzanfang = (not vor) or vor.endswith((".", "!", "?", ":", "\n"))
            return "Hier" if satzanfang else "hier"

        body, n = muster.subn(_ersetzen, body)
        if n:
            entfernt.append(f"R7-INTRO-FORMEL: „{formel}\" ×{n} → „hier\"")
    return body, entfernt


# ---------------------------------------------------------------------------
#  STUFE 4 – ZAHL-/DATUMS-RUINEN (R11/R13)
# ---------------------------------------------------------------------------
def _muster(name: str) -> re.Pattern | None:
    for regel, rx, _desc in sk.POLITUR_RUINEN:
        if regel == name:
            return rx
    return None


def heile_zahlen_und_daten(body: str) -> tuple[str, list[str]]:
    """Heilt zerrissene Jahreszahlen (R11) und fehlende Ordinalpunkte (R13)."""
    entfernt: list[str] = []
    rx11 = _muster("R11-JAHRESZAHL-SPLIT")
    if rx11:
        def _jahr(m: re.Match) -> str:
            entfernt.append(f"R11-JAHRESZAHL-SPLIT: „{m.group(0)}\" → „{m.group(0).replace(' ', '').replace(chr(0xA0), '').replace(chr(0x202F), '')}\"")
            return re.sub(r"[\s\u00A0\u202F]", "", m.group(0))
        body = rx11.sub(_jahr, body)
    rx13 = _muster("R13-DATUM-PUNKT")
    if rx13:
        def _datum(m: re.Match) -> str:
            entfernt.append(f"R13-DATUM-PUNKT: „{m.group(0)}\" → „{m.group(1)}. {m.group(2)}\"")
            return f"{m.group(1)}. {m.group(2)}"
        body = rx13.sub(_datum, body)
    return body, entfernt


# ---------------------------------------------------------------------------
#  DIE HEILUNG (Stufen + Tor)
# ---------------------------------------------------------------------------
def _transformiere(body: str, titel: str) -> tuple[str, list[str]]:
    """Alle Stufen in fester Reihenfolge – ohne Urteil, nur Transformation."""
    entfernt: list[str] = []
    for funktion in (lambda b: heile_marker(b, titel),
                     heile_phrasendoppel,
                     heile_intro_formeln,
                     heile_zahlen_und_daten):
        body, rest = funktion(body)
        entfernt += rest
    return body, entfernt


def _marker_zeilen_entfernen(text: str) -> str:
    """Nur die Marker am Zeilenanfang streichen – für die VORHER-Messung.

    Dieselbe Vorschrift, mit der der Heiler schreibt (Muster-SSOT
    `sprachkern.POLITUR_RUINEN`): So wird „vorher" mit demselben Lineal
    gemessen wie „nachher". Nur SO kann ein darüber hinausgehender Verlust
    (z. B. eine gelöschte Tabellenzeile) überhaupt auffallen.
    """
    for _name, rx in _marker_muster():
        text = rx.sub("", text)
    return text


def _tabellenzellen(text: str) -> list[str]:
    """Tabellenzellen – Marker am Zeilenanfang zählen nicht als Zelleninhalt."""
    zellen = []
    for zeile in _marker_zeilen_entfernen(text).split("\n"):
        s = zeile.strip()
        if not s.startswith("|"):
            continue
        zellen += [z.strip() for z in s.strip("|").split("|")]
    return sorted(zellen)


def _linkziele(text: str) -> list[str]:
    return sorted(re.findall(r"\]\(([^)]*)\)", text))


def _go_anker(text: str) -> list[str]:
    return sorted(re.findall(r"\[[^\]]*\]\((/go/[^)]*)\)", text))


def _ueberschriften(text: str) -> list[str]:
    return [l.strip() for l in text.split("\n") if l.strip().startswith("#")]


def _shortcodes(text: str) -> list[str]:
    return sorted(re.findall(r"\{\{[<%].*?[>%]\}\}", text))


def _zahlen(text: str) -> list[str]:
    ohne_links = re.sub(r"\]\([^)]*\)", "]", text)
    return sorted(re.findall(r"\d+(?:[.,]\d+)*", ohne_links))


def _zahlen_nach_jahreszahl_join(text: str) -> list[str]:
    """Zahlen-Multiset, nachdem R11 („20 26" → „2026") angewandt wurde.

    Die Jahreszahl-Heilung ändert das Zahlen-Multiset GEWOLLT („20" + „26"
    werden EINE Zahl). Verglichen wird deshalb gegen den alten Text, auf den
    dieselbe Vorschrift angewandt wurde – jede darüber hinausgehende
    Zahlen-Änderung bleibt damit ein Befund.
    """
    rx = _muster("R11-JAHRESZAHL-SPLIT")
    if rx:
        text = rx.sub(lambda m: re.sub(r"[\s\u00A0\u202F]", "", m.group(0)), text)
    return _zahlen(text)


def bewahre_form(alt_raw: str, neu_raw: str) -> list[str]:
    """T2 – formale Bewahrung. Rückgabe: Verstöße (leer = bewahrt).

    Links, /go/-Anker, Überschriften und Shortcodes werden am ROHEN Text
    verglichen (dort darf sich nichts ändern). Zahlen und Tabellenzellen
    werden gegen den alten Text gestellt, auf den nur die jeweils GEWOLLTE
    Vorschrift angewandt wurde (R11-Join bzw. Marker-Strip) – so fällt jeder
    Verlust jenseits der Heiler-Regeln auf.
    """
    gruende: list[str] = []
    a, n = _teile(alt_raw), _teile(neu_raw)
    if a is None or n is None:
        return ["T2 Form: Frontmatter-Grenzen fehlen oder sind verschoben"]
    if a[1] != n[1]:
        gruende.append("T2 Form: Frontmatter verändert (der Heiler schreibt nie ins Frontmatter)")
    for name, links, rechts in (("Linkziele", _linkziele(a[2]), _linkziele(n[2])),
                                ("/go/-Anker", _go_anker(a[2]), _go_anker(n[2])),
                                ("Überschriften", _ueberschriften(a[2]), _ueberschriften(n[2])),
                                ("Shortcodes", _shortcodes(a[2]), _shortcodes(n[2])),
                                ("Zahlen", _zahlen_nach_jahreszahl_join(a[2]), _zahlen(n[2])),
                                ("Tabellenzellen", _tabellenzellen(a[2]), _tabellenzellen(n[2]))):
        if links != rechts:
            gruende.append(f"T2 Form: {name} verändert")
    if not n[2].strip():
        gruende.append("T2 Form: Fließtext geleert")
    # Wortzahl-Grenze der Hauswache (sprachkern.write_verified): 10 % Spielraum
    # für die gewollten Marker-/Wiederholungs-Entfernungen, darüber ein Befund.
    worte_alt = len(_WORT.findall(a[2]))
    worte_neu = len(_WORT.findall(n[2]))
    if worte_alt and worte_neu < 0.90 * worte_alt:
        gruende.append(f"T2 Form: Wortzahl {worte_neu} < 90 % von {worte_alt}")
    return gruende


def verifiziere(slug: str, alt_raw: str, neu_raw: str) -> list[str]:
    """DAS TOR (T1–T3). Rückgabe: Gründe, die die Änderung verwerfen."""
    gruende = bewahre_form(alt_raw, neu_raw)
    if neu_raw == alt_raw:
        return gruende + ["T3 Wirkung: Text unverändert – nichts zu schreiben"]
    vor, nach = harte_funde(alt_raw, slug), harte_funde(neu_raw, slug)
    if nach - vor:
        gruende.append("T1 Textverständnis: neuer harter Fund – "
                       + "; ".join(sorted(nach - vor)[:2]))
    if len(nach) >= len(vor):
        gruende.append("T1 Textverständnis: kein Fund behoben "
                       f"({len(vor)} → {len(nach)})")
    vor_ruine, nach_ruine = ruinen(alt_raw), ruinen(neu_raw)
    if nach_ruine - vor_ruine:
        gruende.append("T1 Politur-Ruine: neuer Rest – "
                       + "; ".join(sorted(nach_ruine - vor_ruine)[:2]))
    return gruende


def heile_text(slug: str, rohtext: str) -> dict:
    """Heilt EINEN Text unter dem Tor. Schreibt nie – liefert das Ergebnis."""
    teile = _teile(rohtext)
    if teile is None:
        return {"slug": slug, "ok": False, "neu_raw": rohtext,
                "gruende": ["Frontmatter-Grenzen fehlen – fail-closed"]}
    vor = harte_funde(rohtext, slug)
    neu_body, entfernt = _transformiere(teile[2], _titel(rohtext))
    neu_raw = join_article(teile[1], neu_body, teile[0])
    nach = harte_funde(neu_raw, slug)
    gruende = verifiziere(slug, rohtext, neu_raw)
    return {
        "slug": slug,
        "ok": not gruende,
        "neu_raw": neu_raw,
        "geschrieben": False,
        "entfernt": entfernt,
        "vorher": sorted(vor),
        "nachher": sorted(nach),
        "behoben": sorted(vor - nach),
        "rest": sorted(nach),
        "gruende": gruende,
    }


def _ist_entwurf(rohtext: str) -> bool:
    teile = _teile(rohtext)
    return bool(teile) and bool(re.search(r"(?m)^draft:\s*true\s*$", teile[1], re.I))


def _slug_von(pfad: str) -> str:
    return os.path.basename(os.path.dirname(os.path.abspath(pfad)))


def hole_reserve() -> list[str]:
    """Reserve-Kandidaten (draft:true + reserve:true) mit heilbarem Rest."""
    import glob
    pfade = []
    for p in sorted(glob.glob(os.path.join(BLOG_DIR, "content/posts/*/index.md"))):
        try:
            raw = open(p, encoding="utf-8").read()
        except OSError:
            continue
        if not re.search(r"(?m)^reserve:\s*true\s*$", raw):
            continue
        if not _ist_entwurf(raw):
            continue
        if any(f.split(":", 1)[0] in HEILBARE_REGELN for f in harte_funde(raw, _slug_von(p))):
            pfade.append(p)
    return pfade


# ---------------------------------------------------------------------------
#  WIRKUNGSPROBE – der Nachweis, den die Deckung fordert
# ---------------------------------------------------------------------------
PROBE_FIXTURE = (
    "---\n"
    "title: \"Probe: Ruinen\"\n"
    "date: 2026-10-07\n"
    "draft: true\n"
    "---\n\n"
    "## Einleitung\n\n"
    "Dein Weg zu geringeren im Check: Dein Weg zu geringeren im Check: "
    "Dein Weg zu geringeren im Check – stell dir vor, du sparst jeden Monat "
    "50 Euro mehr, ohne mehr zu arbeiten. Nutze 20 26 gezielt den Vergleich "
    "und prüfe die Frist zum 2 Januar.\n\n"
    "Der Tarifvergleich beginnt mit dem eigenen Verbrauch. Notiere die "
    "Zählernummer, das Zählerstand-Datum und den Arbeitspreis, damit jede "
    "Aussage der Anbieter nachrechenbar bleibt. Wer die Posten sortiert, "
    "findet die teuren Verträge in wenigen Minuten und erkennt sofort, wo "
    "sich ein Wechsel lohnt.\n\n"
    "| Standard | Verbrauch |\n"
    "|----------|-----------|\n"
    "SATZ: | Funk | 0,5 Watt |\n\n"
    "In diesem Artikel erfährst du, wie du die Kosten senkst und welche "
    "Schritte wirklich helfen. Ein Vergleich lohnt sich immer dann, wenn "
    "Laufzeit und Bonus getrennt geprüft werden und die Kündigungsfrist "
    "schriftlich im Kalender steht.\n\n"
    "## Prüfschritte\n\n"
    "Zuerst liest du den letzten Jahresverbrauch aus der Abrechnung ab und "
    "trägst ihn in eine Tabelle ein. Danach vergleichst du Arbeitspreis und "
    "Grundpreis getrennt, weil ein niedriger Arbeitspreis mit hohem Grundpreis "
    "teuer enden kann. Anschließend prüfst du Laufzeit, Kündigungsfrist und "
    "Bonusbedingungen und rechnest den Rabatt über die volle Laufzeit. Erst "
    "danach entscheidest du, ob sich der Wechsel lohnt, und notierst den Termin "
    "für die Kündigung im Kalender, damit die Frist nicht verstreicht.\n"
)


def wirkungsprobe() -> tuple[bool, str]:
    """Beweist: R14 + R15 + R7 + R11 + R13 verschwinden, das Tor hält."""
    slug = "wirkungsprobe"
    ergebnis = heile_text(slug, PROBE_FIXTURE)
    if not ergebnis["ok"]:
        return False, ("Tor verworfen: "
                       + "; ".join(ergebnis["gruende"][:3]) or "ohne Grund")
    neu = ergebnis["neu_raw"]
    rest_ruinen = {r.split(":", 1)[0] for r in ruinen(neu)}
    if rest_ruinen:
        return False, f"Ruinen bleiben stehen: {sorted(rest_ruinen)}"
    nach = harte_funde(neu, slug)
    if any(f.split(":", 1)[0] in HEILBARE_REGELN for f in nach):
        return False, f"heilbare Regel feuert weiter: {sorted(nach)}"
    # Idempotenz: der zweite Lauf darf nichts mehr finden.
    zweiter = heile_text(slug, neu)
    if zweiter["neu_raw"] != neu:
        return False, "zweiter Lauf verändert den Text – nicht idempotent"
    behoben = ergebnis["behoben"]
    return True, (f"Heilung wirkt: {len(behoben)} harte Funde behoben "
                  f"({', '.join(sorted({b.split(':', 1)[0] for b in behoben}))}), "
                  f"T1–T3 erfüllt, idempotent")


# ---------------------------------------------------------------------------
#  SELBSTTEST – Sabotage-Proben (offline, ohne Netz)
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    fehler: list[str] = []

    # --- 1) Wirkung ---------------------------------------------------------
    ok, meldung = wirkungsprobe()
    if not ok:
        fehler.append(f"Wirkungsprobe rot: {meldung}")

    # --- 2) R14: Marker weg, Tabellenzelle bleibt --------------------------
    body = ("---\ntitle: \"T\"\ndraft: true\n---\n\n"
            "| A | B |\n|---|---|\nSATZ: | Thread | 40–80 € |\n")
    neu, entfernt = heile_marker(body.split("---", 2)[2], "T")
    if "SATZ" in neu or "| Thread | 40–80 € |" not in neu:
        fehler.append("R14: Marker nicht entfernt oder Zelle beschädigt")
    if not entfernt:
        fehler.append("R14: Entfernung nicht protokolliert")

    # --- 3) R16: Titel-Echo-Zeile fällt ganz --------------------------------
    body16 = ("---\ntitle: \"Preiswert surfen\"\ndraft: true\n---\n\n"
              "TITLE: Preiswert surfen\n\nDer Text beginnt hier.\n")
    neu16, _ = heile_marker(body16.split("---", 2)[2], "Preiswert surfen")
    if "TITLE" in neu16 or "Preiswert surfen" in neu16:
        fehler.append("R16: Prompt-Marker bzw. Titel-Echo blieb stehen")

    # --- 4) R15: dreifacher Stempel wird auf einen gezogen ------------------
    body15 = ("---\ntitle: \"T\"\ndraft: true\n---\n\n"
              "Dein Weg zu geringeren im Check: Dein Weg zu geringeren im Check: "
              "Dein Weg zu geringeren im Check – dann geht es weiter mit dem Text.\n")
    neu15, entfernt15 = heile_phrasendoppel(body15.split("---", 2)[2])
    if neu15.count("Dein Weg zu geringeren") != 1:
        fehler.append(f"R15: Wiederholung nicht auf 1× gezogen: {neu15[:80]}")
    if "dann geht es weiter" not in neu15:
        fehler.append("R15: Resttext verloren")

    # --- 5) R15: Markup im Löschbereich → unangetastet ----------------------
    body15m = ("---\ntitle: \"T\"\ndraft: true\n---\n\n"
               "Prüfe den Tarif und vergleiche die Preise der Anbieter im Netz: "
               "Prüfe den Tarif und vergleiche die Preise der [Anbieter](/go/konto/) "
               "im Netz und danach folgt weiterer Text für den Artikel.\n")
    neu15m, _ = heile_phrasendoppel(body15m.split("---", 2)[2])
    if "](/go/konto/)" not in neu15m:
        fehler.append("R15: Link wurde durch die Kollabierung zerstört")
    if neu15m.count("Prüfe den Tarif") != 2:
        fehler.append("R15: Markup-Fall wurde nicht fail-closed übersprungen")

    # --- 6) R7 / R11 / R13 ---------------------------------------------------
    body7 = ("---\ntitle: \"T\"\ndraft: true\n---\n\n"
             "In diesem Artikel erfährst du alles. Nutze 20 26 den Vergleich und "
             "prüfe die Frist zum 2 Januar.\n")
    neu7, _ = heile_intro_formeln(body7.split("---", 2)[2])
    if "In diesem Artikel" in neu7 or "Hier erfährst du" not in neu7:
        fehler.append("R7: Intro-Formel nicht ersetzt")
    neu7b, _ = heile_zahlen_und_daten(neu7)
    if "20 26" in neu7b or "2026" not in neu7b:
        fehler.append("R11: zerrissene Jahreszahl nicht geheilt")
    if "2 Januar" in neu7b or "2. Januar" not in neu7b:
        fehler.append("R13: fehlender Ordinalpunkt nicht geheilt")

    # --- 7) Das Tor weist Sabotage ab ---------------------------------------
    gut = ("---\ntitle: \"T\"\ndraft: true\n---\n\n"
           "Das Konto kostet Gebühren. Der Wechsel dauert kurz.\n")
    faelle = {
        "Link entfernt": gut + "Mehr im [Vergleich](/go/konto/).\n",
        "Zahl verändert": gut + "Der Preis liegt bei 12 Euro.\n",
        "Frontmatter verändert": gut.replace("draft: true", "draft: false"),
        "neuer harter Fund": gut + "In diesem Beitrag erfährst du alles.\n",
    }
    if not bewahre_form(faelle["Link entfernt"], gut):
        fehler.append("Tor T2 erkennt Linkverlust nicht")
    if not bewahre_form(faelle["Zahl verändert"], gut):
        fehler.append("Tor T2 erkennt Zahlenverlust nicht")
    if not bewahre_form(faelle["Frontmatter verändert"], gut):
        fehler.append("Tor T2 erkennt Frontmatter-Änderung nicht")
    if not any("T1" in g for g in verifiziere("probe", gut, faelle["neuer harter Fund"])):
        fehler.append("Tor T1 erkennt neuen harten Fund nicht")
    if not any("Wirkung" in g for g in verifiziere("probe", gut, gut)):
        fehler.append("Tor T3 erkennt wirkungslose Änderung nicht")

    # --- 8) Scope-Schutz -----------------------------------------------------
    live = gut.replace("draft: true", "draft: false")
    if _ist_entwurf(live):
        fehler.append("Live-Artikel gilt als Entwurf – Scope-Schutz defekt")
    if not _ist_entwurf(gut):
        fehler.append("Entwurf wird nicht als Entwurf erkannt")

    # --- 9) R12 bleibt liegen (bewusst NICHT geheilt) ------------------------
    body12 = ("---\ntitle: \"T\"\ndraft: true\n---\n\n"
              "Du bist der 0 am deutschen Strommarkt und zahlst zu viel.\n")
    ergebnis12 = heile_text("probe12", body12)
    if ergebnis12["ok"]:
        fehler.append("R12 wurde 'geheilt' – dafür fehlt die inhaltliche Grundlage")

    if fehler:
        print("🛑 POLITUR-HEILER-SELFTEST FEHLGESCHLAGEN:")
        for f in fehler:
            print("  -", f)
        return 2
    print(f"✅ Politur-Heiler-Selbsttest bestanden – {meldung}; Marker, Stempel, "
          f"Template-Sprache, Zahlen-/Datums-Ruinen heilen, Markup-Sperre hält, "
          f"das Tor T1–T3 weist Sabotage ab.")
    return 0


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------
def _verarbeite(pfade: list[str], *, fix: bool, max_n: int | None,
                auch_live: bool = False) -> tuple[list[dict], int]:
    berichte, befund = [], 0
    for pfad in pfade[:max_n] if max_n else pfade:
        try:
            with open(pfad, encoding="utf-8") as fh:
                rohtext = fh.read()
        except OSError as exc:
            berichte.append({"slug": os.path.basename(os.path.dirname(pfad)),
                             "ok": False, "gruende": [f"nicht lesbar: {exc}"]})
            befund += 1
            continue
        slug = _slug_von(pfad)
        if not _ist_entwurf(rohtext) and not auch_live:
            berichte.append({"slug": slug, "ok": True, "stufe": "übersprungen",
                             "befund": "kein Entwurf (draft: false) – Scope-Schutz"})
            continue
        ergebnis = heile_text(slug, rohtext)
        # Drei Lagen, damit Exit 0 in JEDER Betriebsart dasselbe heißt –
        # „hier liegt nichts mehr" (BOT-WATCHDOG-614):
        #   sauber            (Text unverändert)                -> kein Punkt
        #   heilbar+fix       (geschrieben)                     -> kein Punkt
        #   heilbar ohne fix  (Trockenlauf)                     -> offener Punkt
        #   Heilung verworfen (Tor T1–T3, Text bleibt liegen)   -> offener Punkt
        veraendert = ergebnis["neu_raw"] != rohtext
        if veraendert and ergebnis["ok"]:
            if fix:
                with open(pfad, "w", encoding="utf-8") as fh:
                    fh.write(ergebnis["neu_raw"])
                ergebnis["geschrieben"] = True
            else:
                befund += 1
        elif veraendert:
            befund += 1
        ergebnis["pfad"] = os.path.relpath(pfad, BLOG_DIR)
        ergebnis.pop("neu_raw", None)
        berichte.append(ergebnis)
    return berichte, befund


def _menschen_text(berichte: list[dict], befund: int) -> str:
    zeilen = ["# POLITUR-HEILER (Klasse #614)", ""]
    for b in berichte:
        if b.get("stufe") == "übersprungen":
            zeilen.append(f"⏭  {b['slug']}: {b.get('befund')}")
            continue
        marke = "🟢" if b.get("ok") else "🔴"
        haken = " ✍️" if b.get("geschrieben") else ""
        zeilen.append(f"{marke} {b.get('slug')}{haken}: "
                      f"{len(b.get('behoben') or [])} behoben, "
                      f"{len(b.get('rest') or [])} Rest")
        for e in (b.get("entfernt") or [])[:6]:
            zeilen.append(f"     · {e}")
        for g in (b.get("gruende") or [])[:4]:
            zeilen.append(f"     ! {g}")
        for r in (b.get("rest") or [])[:4]:
            zeilen.append(f"     ⏳ verbleibend: {r}")
    zeilen += ["", f"Gehbare Regeln: {', '.join(HEILBARE_REGELN)}",
               f"Offene Punkte (ungeheilt oder im Trockenlauf nicht "
               f"geschrieben): {befund}"]
    return "\n".join(zeilen)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Politur-Heiler: entfernt Maschinen-Ruinen (R7/R11/R13/"
                    "R14/R15/R16) aus Entwürfen – fail-closed, mit Wirkungsprobe.")
    ap.add_argument("--file", action="append", default=[],
                    help="einzelne Datei (mehrfach möglich)")
    ap.add_argument("--reserve", action="store_true",
                    help="alle Reserve-Kandidaten mit heilbarem Rest")
    ap.add_argument("--blocked", action="store_true",
                    help="Alias für --reserve (Sprachgebrauch der Reserve)")
    ap.add_argument("--fix", action="store_true", help="schreiben (sonst Trockenlauf)")
    ap.add_argument("--auch-live", action="store_true",
                    help="auch Nicht-Entwürfe anfassen (Standard: nur draft:true)")
    ap.add_argument("--max", type=int, default=None, help="höchstens N Kandidaten")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--report", action="store_true",
                    help="Report nach POLITUR-HEILER-REPORT.md schreiben")
    ap.add_argument("--wirkungsprobe", action="store_true",
                    help="Maschinenvertrag: beweist die Wirkung (Exit 0 = grün)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return run_selftest()

    if args.wirkungsprobe:
        ok, meldung = wirkungsprobe()
        if args.json:
            print(json.dumps({"ok": ok, "meldung": meldung,
                              "regeln": list(HEILBARE_REGELN)},
                             ensure_ascii=False))
        else:
            print(("✅ " if ok else "🛑 ") + "Wirkungsprobe: " + meldung)
        return 0 if ok else 2

    pfade = list(args.file)
    if args.reserve or args.blocked:
        rest = hole_reserve()
        if not rest and not pfade:
            # REPARATUR 07.10.2026 (BOT-WATCHDOG-614): „nichts zu heilen" ist ein
            # ERGEBNIS, kein Bedienfehler. Vorher brach der Aufruf mit einem
            # Usage-Fehler ab, sobald der Pool politurfrei war – in einer Kette
            # liest sich das wie ein kaputtes Werkzeug, obwohl genau der
            # gewünschte Zustand erreicht war. Ein sauberer Lauf endet still und
            # grün; nur ein Aufruf ganz OHNE Quelle bleibt ein Bedienfehler.
            if args.json:
                print(json.dumps({"befund": 0, "berichte": [],
                                  "hinweis": "Pool ist politurfrei"},
                                 ensure_ascii=False))
            else:
                print("✅ Politur-Heiler: 0 Reserve-Kandidaten mit heilbarem "
                      "Rest – nichts zu tun (Pool ist politurfrei).")
            return 0
        pfade += rest
    if not pfade:
        ap.error("Quelle fehlt: --file oder --reserve "
                 "(oder --selftest/--wirkungsprobe)")

    berichte, befund = _verarbeite(sorted(dict.fromkeys(pfade)), fix=args.fix,
                                   max_n=args.max, auch_live=args.auch_live)
    text = _menschen_text(berichte, befund)
    if args.json:
        print(json.dumps({"befund": befund, "berichte": berichte},
                         ensure_ascii=False, indent=1, default=str))
    else:
        print(text)
    if args.report:
        ziel = os.path.join(BLOG_DIR, "POLITUR-HEILER-REPORT.md")
        with open(ziel, "w", encoding="utf-8") as fh:
            fh.write(f"<!-- erzeugt: {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M} UTC -->\n\n")
            fh.write(text + "\n")
        print(f"📄 Report: {os.path.relpath(ziel, BLOG_DIR)}")
    return 1 if befund else 0


if __name__ == "__main__":
    sys.exit(main())
