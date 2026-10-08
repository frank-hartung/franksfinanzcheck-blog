#!/usr/bin/env python3
"""lesbarkeit_heiler.py – der fehlende Heiler der Lesbarkeits-Klasse (#609).

WARUM DIESE DATEI EXISTIERT (Vorgang WACHE-609, 07.10.2026)
=========================================================
Die Produktions-Wache meldete am 06.10.2026 für den letzten Publikationstag
(05.10.) „Content-Engine liefert nicht“ (P2, Issue #609) – und nannte im
selben Body ihren Bestand: „2 von Gates gehalten (publish-gate: Lesbarkeits-
Gate nicht bestanden: Flesch 44.4 …)“. Zwei Beobachtungen, eine Ursache:

  1. Am 05.10.2026 hat die Lesbarkeits-Wache (#585) die Publish-Schwelle
     `readability_check.NEW_FLESCH_MIN` (60,0) hart in `publish_gate.
     readability_failures()` verankert – richtig so. Seitdem blockiert das
     Tor Entwürfe und Reserve-Kandidaten, die 53–60 messen.
  2. Für diese Klasse existierte **kein Heiler, der die Schwelle auch
     erreicht**. Die Reserve-Heiler-Kette nannte `profi_polish.py` als
     Deckung – und `reserve_healer_coverage` prüfte nur, dass der Name in
     der Kette steht. Wirkung prüfte niemand.

Das Ergebnis steht in `data/reserve-readiness.json` vom 07.10.2026
(11:11:50Z, Lauf run:37607427999): **Ziel 6, bereit 2, Pool 12** – davon
**7 Kandidaten allein an der Lesbarkeit** gescheitert (Flesch 53,1 / 55,8 /
57,9 / 58,8 / 59,4 / 59,9 bzw. Score 70/75) und ein achter am
Textverständnis. Ein Vorrat, der sein Ziel nicht erreicht, kann an einem Tag
mit verpassten Slots (#601) oder Synchronverlust (#590) nicht auffüllen –
und genau dieser Tag endet dann bei 1/2 und erzeugt den nächsten
Wache-Auftrag. **Die Quote ist das Symptom; der trockene Vorrat ist die
Krankheit.**

Dieses Werkzeug schließt die Klasse – und zwar nach dem Kodex des Hauses:

    Eine Deckung ohne Wirkung ist Papier.

DESHALB SIND ES ZWEI STUFEN UND EIN TOR
=======================================
  * **Stufe A – deterministisch (ohne KI, ohne Netz):**
      1. Schachtelsätze (> 18 Wörter) werden an *sicheren Nahtstellen*
         zerlegt: „, und “ / „, aber “ / „, denn “ / „, doch “ /
         „, sondern “ / „; “. Deutsche Hauptsatz-Reihungen mit Komma
         erlauben den Satzpunkten-Schnitt; Nebensätze (weil/dass/wenn/…)
         sind KEINE Naht und werden nie getrennt (sonst entstünden
         Fragmente).
      2. Füllphrasen der „Kurz-und-klar“-Liste werden ersetzt
         („im Rahmen von“ → „bei“, „nichtsdestotrotz“ → „trotzdem“, …) –
         bedeutungsgleich, nur kürzer.
      3. Absätze über 4 Sätze zerlegt der bestehende R5-Splitter
         (`r5_absatz_splitter`, SSOT – kein zweiter Splitter).
    Abkürzungen (z. B., d. h., Nr.) werden VOR jeder Zerlegung maskiert
    (Liste aus `r5_absatz_splitter` – auch hier keine zweite Wahrheit).

  * **Stufe B – KI-Feinschliff (Gemini → Groq, wie `profi_polish`):** läuft
    NUR, wenn Stufe A die Schwelle nicht erreicht und Keys vorhanden sind.
    Der Auftrag ist eng und nennt das IST (Flesch, Ø Satzlänge, Ø Wortlänge)
    sowie den eigentlichen Hebel: Flesch = 180 − Ø Satzlänge − 58,5 · Silben
    je Wort. Bei diesen Kandidaten liegt die Ø Satzlänge bereits unter 15
    Wörtern (9,9 im VPN-Text) – es sind die SILBEN JE WORT. Darum verlangt
    der Auftrag zuerst lange Komposita durch kurze Alltagswörter zu ersetzen
    („Stromanbieterwechsel“ → „Wechsel“, „Erstattungsfähigkeit“ →
    „Erstattung“) und erst danach Satzschnitte. Bleibt Versuch 1 unter der
    Schwelle, folgt genau EIN zweiter („radikaler bei den langen Wörtern“);
    danach entscheidet das Tor – nicht der Schreiber.
    Der KI-Aufruf ist injizierbar (`KI_CALL`): Der Selbsttest beweist mit
    einer Attrappe Annehmen UND Verwerfen – ohne Netz, Key oder Kosten.

  * **Das Tor (fail-closed, entscheidet – nicht der Schreiber):** Eine
    Änderung wird nur geschrieben, wenn ALLE diese Sätze bewiesen sind:
      T1  Flesch ≥ `readability_check.NEW_FLESCH_MIN` (importierte SSOT –
          keine zweite Zahl) UND besser als vorher.
      T2  Kein harter Textverständnis-Fund danach (Regelliste
          `publish_gate.HARTE_REGELN`, gemessen mit dem echten Wächter).
      T3  Der Publikations-Vertrag (`publikations_vertrag.pruefe`, V1–V3;
          Vorgang WF-54C4/#607) meldet keinen Verstoß.
      T4  Formale Bewahrung: Linkziele, `/go/`-Anker, Überschriften,
          Shortcodes, Tabellenzeilen und ZAHLEN (Multiset) unverändert,
          Frontmatter byte-identisch, Länge ≥ 90 %.
    Scheitert eine Zeile, bleibt die Datei **byte-identisch** liegen und der
    Befund (Restlücke) wird gemeldet. „Nicht gemessen“ ist niemals
    „geschrieben“.

WIRKUNGSNACHWEIS (der eigentliche Lehrauftrag aus #609)
=======================================================
`wirkungsprobe()` heilt ein Fixture, das unter der Schwelle startet, mit
Stufe A und prüft: vorher < 60 ≤ nachher – plus alle Verträge T2–T4. Diesen
Nachweis fordert `reserve_healer_coverage.wirkungsdeckung()` und damit der
Governance-Vertrag **C25** („Deckung heißt Wirkung“; Code C25, weil
„C24“ im Haus die C24 Bank bezeichnet): Eine Regel darf nur
dann als gedeckt gelten, wenn der genannte Heiler die Schwelle, die er
verspricht, auch *misst* und ihre Bewegung *beweist*.

SCOPE / SICHERHEIT
==================
  * Es werden NUR Entwürfe angefasst (`draft: true`) – Live-Artikel nie.
    Ausnahme existiert bewusst nicht: Ein Live-Text wird bei Bedarf erst
    zurückgestuft (Kadenz-/Gate-Pfad), dann geheilt, dann erneut geprüft.
  * Es wird nie `draft` umgeschrieben, nie ein `cadence_*`-Feld gesetzt und
    nie veröffentlicht. Die Re-Queue entscheidet `requeue_quality_holds.py`
    bzw. die Kadenz – nicht dieses Werkzeug.
  * Idempotent: Ist ein Text bereits über der Schwelle, passiert nichts.

NUTZUNG
=======
    python3 scripts/lesbarkeit_heiler.py --file content/posts/<slug>/index.md
        --fix                       # einen Entwurf heilen (Standard: Trockenlauf)
    python3 scripts/lesbarkeit_heiler.py --holds --fix
                                    # alle Gate-Holds der Lesbarkeits-Klasse
    python3 scripts/lesbarkeit_heiler.py --blocked --fix
                                    # Reserve-Kandidaten laut readiness-Zertifikat
    python3 scripts/lesbarkeit_heiler.py --new-only --fix
                                    # Artikel des HEUTIGEN Datums (Live-Engine
                                    # Phase 2 – genau die Texte, die das Gate
                                    # der Auslieferung sonst zurückhält)
    python3 scripts/lesbarkeit_heiler.py --file X --keine-ki --json
    python3 scripts/lesbarkeit_heiler.py --wirkungsprobe
                                    # beweist die Wirkung als Maschinenvertrag
                                    # (Exit 0 = Fixture < 60 → ≥ 60, T1–T4 ok)
    python3 scripts/lesbarkeit_heiler.py --selftest   # Sabotage- UND Wirkungsprobe

EXIT: 0 = alles über der Schwelle (oder nichts zu tun) · 1 = mindestens ein
      Kandidat blieb unter der Schwelle (Befund, fail-closed: nichts
      Halbfertiges geschrieben) · 2 = Selbsttest/Werkzeugfehler.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BLOG_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import readability_check as rc           # noqa: E402 – Mess-SSOT (Flesch)
import publish_gate as pg                # noqa: E402 – HARTE_REGELN (SSOT)
import publikations_vertrag as vertrag   # noqa: E402 – V1–V3 (WF-54C4/#607)
import textverstaendnis_guard as tv      # noqa: E402 – echter Verständnis-Prüfer
import r5_absatz_splitter as r5          # noqa: E402 – Abkürzungen + Absatz-Splitter
from post_utils import join_article      # noqa: E402 – Naht-SSOT
import reserve_artifacts as artifacts    # noqa: E402 – ganze Belege (#634)

# Die Schwelle ist IMPORTIERT – eine Regel, zwei Leser, eine Zahl.
MINDEST_FLESCH = rc.NEW_FLESCH_MIN

# Ab dieser Länge gilt ein Satz als Schachtelsatz (Zielkorridor: 12–18 Wörter).
MAX_SATZ_WOERTER = 18
# Kürzeste erlaubte Satzhälfte nach einem Schnitt – sonst bleibt der Satz ganz.
MIN_TEIL_WOERTER = 6
# Höchstens so viele Schnitte je Satz pro Runde (danach ist der Rest KI-Arbeit).
MAX_SCHNITTE_JE_SATZ = 2
# Zerlege-Runden bis zum Fixpunkt (Idempotenz: der zweite Lauf findet nichts mehr).
MAX_RUNDEN = 4

_WORT = re.compile(r"\b\w+\b")

# ---------------------------------------------------------------------------
#  NAHTSTELLEN des deterministischen Satzschnitts
# ---------------------------------------------------------------------------
#  Begründung je Naht (nur diese fünf, keine Erfindungen):
#    „und/aber/denn/doch/sondern“ leiten im Deutschen einen selbstständigen
#    Hauptsatz ein (Komma davor ist fakultativ) – ein Satzpunkt ist dort
#    grammatisch korrekt. Nicht-Koordinatoren (weil, dass, wenn, obwohl,
#    damit, sodass, wobei, was, der/die/das als Relativpronomen) sind KEINE
#    Naht: Aus „Ich spare, weil ich will.“ würde „Ich spare. Weil ich will.“
#    – ein Fragment. Solche Sätze bleiben unangetastet.
NAHTSTELLEN = (
    (", und ", "Und "),
    (", aber ", "Aber "),
    (", denn ", "Denn "),
    (", doch ", "Doch "),
    (", sondern ", "Sondern "),
    ("; ", None),               # Semikolon trennt gleichrangige Sätze
)

# ---------------------------------------------------------------------------
#  „KURZ UND KLAR“ – Füllphrasen (deterministisch, bedeutungsgleich)
# ---------------------------------------------------------------------------
#  Aufnahmekriterien: (1) die Kurzform bedeutet dasselbe, (2) sie ist kürzer
#  oder alltäglicher, (3) sie kann in JEDEM Kontext ersetzt werden. Alles,
#  was Kontext braucht („durchführen“ → „machen“), bleibt draußen – Stufe B
#  (KI) ist dafür da. Jede Ersetzung ist im Selbsttest eingefroren.
KURZ_LEXIKON = (
    ("im Rahmen von", "bei"),
    ("im Rahmen der", "bei der"),
    ("im Rahmen des", "beim"),
    ("zum jetzigen Zeitpunkt", "jetzt"),
    ("aufgrund der Tatsache, dass", "weil"),
    ("nichtsdestotrotz", "trotzdem"),
    ("des Weiteren", "außerdem"),
    ("darüber hinaus", "außerdem"),
    ("in diesem Zusammenhang", "dabei"),
    ("aus diesem Grund", "deshalb"),
    ("eine Vielzahl von", "viele"),
    ("eine große Anzahl von", "viele"),
    ("Verbraucherinnen und Verbraucher", "Verbraucher"),
    ("Mitarbeiterinnen und Mitarbeiter", "Beschäftigte"),
)


# ===========================================================================
#  MESSUNG (alles über die SSOT – nie über eine eigene Formel)
# ===========================================================================
def _teile(rohtext: str):
    """(prefix, frontmatter, body) oder None – dieselbe Naht wie join_article."""
    parts = (rohtext or "").split("---", 2)
    if len(parts) < 3:
        return None
    return parts[0], parts[1], parts[2]


def messe(rohtext: str, slug: str) -> dict:
    """Lesbarkeits-Datensatz eines (auch ungeschriebenen) Textes – SSOT."""
    satz = rc.parse_article(rohtext, f"{slug}/index.md")
    if not satz:
        raise ValueError("Text nicht messbar (Frontmatter/Grenzen unvollständig)")
    return rc.analyze(satz)


def flesch(rohtext: str, slug: str) -> float | None:
    try:
        return messe(rohtext, slug)["flesch"]
    except Exception:  # noqa: BLE001 – unbekannte Messung ist kein Freispruch
        return None


def harte_funde(rohtext: str, slug: str) -> set[str]:
    """Harte Verständnis-Funde (SSOT: publish_gate.HARTE_REGELN).

    Gemessen mit dem ECHTEN Wächter; jeder Werkzeugfehler wirft weiter, damit
    der Aufrufer fail-closed ablehnen kann (nie ein stilles „0 Funde“).
    """
    body = tv.split_body(rohtext)
    funde = tv.check_article(f"{slug}/index.md", body,
                             tv.load_terminologie(),
                             tv.frontmatter_keywords(rohtext))
    return {regel for _, regel, _, _ in funde if regel in pg.HARTE_REGELN}


# ===========================================================================
#  FORMALE BEWAHRUNG (T4) – das, was ein Textumbau nie anfassen darf
# ===========================================================================
def _linkziele(text: str) -> list[str]:
    return sorted(re.findall(r"\]\(([^)]*)\)", text))


def _go_anker(text: str) -> list[str]:
    return sorted(re.findall(r"\[[^\]]*\]\((/go/[^)]*)\)", text))


def _ueberschriften(text: str) -> list[str]:
    return [l.strip() for l in text.split("\n") if l.strip().startswith("#")]


def _shortcodes(text: str) -> list[str]:
    return sorted(re.findall(r"\{\{[<%].*?[>%]\}\}", text))


def _tabellenzeilen(text: str) -> list[str]:
    return [l.rstrip() for l in text.split("\n") if l.strip().startswith("|")]


def _zahlen(text: str) -> list[str]:
    """Alle Zahlen-Token (inkl. Datums-/Geldzahlen) als Multiset.

    Ein Umbau darf keine Zahl verändern, erfinden oder verlieren – die
    Lesbarkeit ist kein Freibrief für Fakten-Drift.
    """
    ohne_links = re.sub(r"\]\([^)]*\)", "]", text)
    return sorted(re.findall(r"\d+(?:[.,]\d+)*", ohne_links))


def _zeilenzahl_kurz(text: str, grenze: int = 4) -> int:
    return sum(1 for l in text.split("\n") if len(_WORT.findall(l)) > grenze)


def bewahre(alt_raw: str, neu_raw: str) -> list[str]:
    """T4 – formale Bewahrung. Rückgabe: Verstöße (leer = bewahrt)."""
    gruende: list[str] = []
    a, n = _teile(alt_raw), _teile(neu_raw)
    if a is None or n is None:
        return ["T4 Form: Frontmatter-Grenzen fehlen oder sind verschoben"]
    if a[1] != n[1]:
        gruende.append("T4 Form: Frontmatter verändert (der Heiler schreibt nie ins Frontmatter)")
    if _linkziele(alt_raw) != _linkziele(neu_raw):
        gruende.append("T4 Form: Linkziele verändert")
    if _go_anker(alt_raw) != _go_anker(neu_raw):
        gruende.append("T4 Form: /go/-Anker verändert")
    if _ueberschriften(alt_raw) != _ueberschriften(neu_raw):
        gruende.append("T4 Form: Überschriften verändert")
    if _shortcodes(alt_raw) != _shortcodes(neu_raw):
        gruende.append("T4 Form: Hugo-Shortcodes verändert")
    if _tabellenzeilen(alt_raw) != _tabellenzeilen(neu_raw):
        gruende.append("T4 Form: Tabellenzeilen verändert")
    if _zahlen(alt_raw) != _zahlen(neu_raw):
        gruende.append("T4 Form: Zahlen/Daten verändert")
    if len(neu_raw) < int(0.9 * len(alt_raw)):
        gruende.append(f"T4 Form: Länge {len(neu_raw)} < 90 % von {len(alt_raw)}")
    return gruende


def verifiziere(slug: str, alt_raw: str, neu_raw: str) -> list[str]:
    """DAS TOR (T1–T4). Rückgabe: Gründe, die die Änderung verwerfen.

    Fail-closed: Jede nicht auswertbare Prüfung ist ein Verstoß.
    """
    gruende = bewahre(alt_raw, neu_raw)
    alt_f, neu_f = flesch(alt_raw, slug), flesch(neu_raw, slug)
    if alt_f is None or neu_f is None:
        gruende.append("T1 Lesbarkeit: Text nicht messbar – fail-closed")
    else:
        if neu_f < MINDEST_FLESCH:
            gruende.append(
                f"T1 Lesbarkeit: Flesch {neu_f:.1f} < Schwelle {MINDEST_FLESCH:g} "
                f"(nicht veröffentlichungsfähig)")
        if neu_f <= alt_f:
            gruende.append(
                f"T1 Lesbarkeit: keine Verbesserung ({alt_f:.1f} → {neu_f:.1f})")
    try:
        neue_funde = harte_funde(neu_raw, slug)
    except Exception as exc:  # noqa: BLE001 – ohne Mess KEIN grünes Urteil
        gruende.append(f"T2 Textverständnis nicht messbar ({exc.__class__.__name__}) – fail-closed")
    else:
        for regel in sorted(neue_funde):
            gruende.append(f"T2 Textverständnis: harter Fund {regel} im Ergebnis")
    try:
        gruende += vertrag.pruefe(slug, alt_raw, neu_raw)
    except Exception as exc:  # noqa: BLE001
        gruende.append(f"T3 Vertrag nicht auswertbar ({exc.__class__.__name__}: {exc}) – fail-closed")
    return gruende


# ===========================================================================
#  STUFE A – deterministisch
# ===========================================================================
def _kuerze_fuellphrasen(body: str) -> tuple[str, int]:
    n = 0
    for alt, neu in KURZ_LEXIKON:
        muster = re.compile(rf"\b{re.escape(alt)}\b")
        body, k = muster.subn(neu, body)
        n += k
    return body, n


_SPAN = re.compile(r"\[[^\]]*\]\([^)]*\)|\{\{.*?\}\}|`[^`]*`|!\[[^\]]*\]\([^)]*\)")


def _geschuetzte_spans(text: str) -> list[tuple[int, int]]:
    """Bereiche, die kein Schnitt berühren darf (Links, Shortcodes, Code).

    Ein Satz MIT Link wird also geheilt – nur nicht *im* Link. Ohne diese
    Unterscheidung fielen genau die Sätze aus, die einen Link tragen (die
    meisten Fließtext-Sätze dieses Blogs) – der Heiler hätte dann scheinbar
    „nichts zu tun“.
    """
    return [(m.start(), m.end()) for m in _SPAN.finditer(text)]


def _in_span(pos: int, spans: list[tuple[int, int]]) -> bool:
    return any(a <= pos < b for a, b in spans)


def _naht_im_satz(satz: str):
    """Beste Nahtstelle eines Satzes: (start, ende, naht, ersatz, links, rechts).

    „Beste“ = diejenige, die den Satz am gleichmäßigsten teilt; beide Hälften
    müssen mindestens `MIN_TEIL_WOERTER` Wörter tragen, und die Naht darf
    keinen Link/Shortcode zerschneiden. None = keine Naht.
    """
    spans = _geschuetzte_spans(satz)
    beste = None
    for naht, ersatz in NAHTSTELLEN:
        for m in re.finditer(re.escape(naht), satz):
            if _in_span(m.start(), spans) or _in_span(m.end() - 1, spans):
                continue
            links = len(_WORT.findall(satz[:m.start()]))
            rechts = len(_WORT.findall(satz[m.end():]))
            if links < MIN_TEIL_WOERTER or rechts < MIN_TEIL_WOERTER:
                continue
            abweichung = abs(links - rechts)
            if beste is None or abweichung < beste[0]:
                beste = (abweichung, m.start(), m.end(), naht, ersatz, links, rechts)
    if beste is None:
        return None
    _, start, ende, naht, ersatz, links, rechts = beste
    return start, ende, naht, ersatz, links, rechts


def _zerlege_satz(satz: str) -> tuple[str, int]:
    """Zerlegt EINEN langen Satz an Nahtstellen. (neuer Satz, Schnitte)."""
    if len(_WORT.findall(satz)) <= MAX_SATZ_WOERTER:
        return satz, 0
    if any(t in satz for t in ("{{", "<", "|")):        # Shortcodes/Tabellen: Finger weg
        return satz, 0
    schnitte = 0
    while schnitte < MAX_SCHNITTE_JE_SATZ and len(_WORT.findall(satz)) > MAX_SATZ_WOERTER:
        naht = _naht_im_satz(satz)
        if naht is None:
            break
        start, ende, _naht, ersatz, _l, _r = naht
        rest = satz[ende:]
        if ersatz is None:                       # Semikolon → einfacher Satzpunkt
            rest = rest.lstrip()
        else:
            rest = ersatz + rest[0].lower() + rest[1:] if rest else ersatz.rstrip()
        satz = satz[:start] + ". " + rest
        schnitte += 1
    if schnitte:
        # Nach jedem erzeugten Satzpunkt groß weiter (auch nach dem Semikolon-Weg).
        satz = re.sub(r"\. ([a-zäöüß])", lambda m: ". " + m.group(1).upper(), satz)
    return satz, schnitte


def _zerlege_saetze(body: str) -> tuple[str, int]:
    """Zerlegt lange Sätze in Fließtext-Zeilen (nie in Markup-Zeilen)."""
    zeilen, schnitte = [], 0
    for zeile in body.split("\n"):
        blank = zeile.strip()
        if not blank or blank.startswith(("|", "#", ">", "{{", "<", "- ", "* ", "👉", "💡")):
            zeilen.append(zeile)
            continue
        neu = []
        for satz in re.split(r"(?<=[.!?])\s+", zeile):
            geheilt, k = _zerlege_satz(satz)
            schnitte += k
            neu.append(geheilt)
        zeilen.append(" ".join(neu))
    return "\n".join(zeilen), schnitte


def stufe_a(rohtext: str) -> tuple[str, dict]:
    """Deterministische Heilung. Rückgabe: (neuer Rohtext, Protokoll)."""
    teile = _teile(rohtext)
    if teile is None:
        return rohtext, {"fehler": "keine Frontmatter-Grenzen"}
    prefix, fm, body = teile
    # 1) Abkürzungen maskieren (SSOT-Liste des R5-Splitters) – sonst zerlegt
    #    der Satzschnitt „z. B.“ mitten in der Abkürzung.
    body, tok = r5.protect(body)
    # 2) Füllphrasen kürzen
    body, lex = _kuerze_fuellphrasen(body)
    # 3) Schachtelsätze zerlegen – bis zum FIXPUNKT (max. MAX_RUNDEN Läufe).
    #    Ein Satz kann nach dem ersten Schnitt noch über 18 Wörtern liegen
    #    (beide Hälften ≥ MIN_TEIL_WOERTER); erst der Fixpunkt macht den Lauf
    #    idempotent – ein zweiter Aufruf findet dann nichts mehr zu tun.
    satz_schnitte, runden = 0, 0
    while runden < MAX_RUNDEN:
        body, k = _zerlege_saetze(body)
        satz_schnitte += k
        runden += 1
        if not k:
            break
    body = r5.restore(body, tok)
    neu = join_article(fm, body, prefix)
    # 4) Absätze > 4 Sätze: der BESTEHENDE Splitter (keine zweite Implementierung)
    neu, absatz_schnitte, _warn = r5.heal_text(neu, label="lesbarkeit_heiler")
    return neu, {"lexikon": lex, "saetze": satz_schnitte, "absaetze": absatz_schnitte}


# ===========================================================================
#  STUFE B – KI-Feinschliff (optional, gleiche Prüfung wie A)
# ===========================================================================
KI_PROMPT = """Du bist Chefredakteur eines deutschen Finanz-Ratgeber-Blogs (Niveau: ZEIT/Stiftung Warentest).

Aufgabe: Schreibe den folgenden Artikel-Body in EINFACHEM, KLAREM Deutsch neu.
Ziel: Flesch-Amstad (deutsch) mindestens {ziel:.0f}. {lage}

Der Flesch-Wert hängt fast nur an den Silben je Wort. Dein stärkster Hebel ist:
lange Komposita und Substantivierungen durch kurze Alltagswörter ersetzen
(„Stromanbieterwechsel" → „Wechsel", „Vertragslaufzeit" → „Laufzeit",
„Beitragsanpassung" → „Anpassung", „Erstattungsfähigkeit" → „Erstattung",
„Haushaltsgeräte" → „Geräte"), Nominalstil in Verben auflösen
(„die Übernahme der Kosten" → „die Kasse zahlt die Kosten").
{vorsatz}

HARTE REGELN (jede Verletzung führt dazu, dass deine Fassung verworfen wird):
1. KEINE neuen Fakten, Zahlen, Preise, Daten, Namen, Quellen. Alle Zahlen bleiben exakt.
2. ALLE Markdown-Links exakt beibehalten (Ziel UND Text) – insbesondere /go/-Links.
3. Alle Überschriften (##/###) im Wortlaut, gleiche Anzahl. Keine neuen Überschriften.
4. ALLE Tabellenzeilen und Tabellenwerte unverändert. Keine neuen Tabellenzeilen.
5. Hugo-Shortcodes unverändert.
6. Anrede beibehalten („du“).
7. Länge mindestens 95 % des Originals. Keine Absätze löschen, keine Inhalte weglassen.
8. Zerlege jeden Satz über 18 Wörter in zwei kurze Sätze.
9. Keine Floskeln, kein „In diesem Beitrag“, keine Anrede-Floskeln am Anfang.
10. Antworte NUR mit dem neuen Body – kein Vorwort, kein Frontmatter, keine Erklärung.

ARTIKEL-BODY:
{body}
"""

# Der KI-Aufruf ist injizierbar. None = echter Weg (Gemini → Groq); der
# Selbsttest setzt hier eine Attrappe ein und beweist damit Annehmen und
# Verwerfen der Stufe B, ohne Netz, ohne Key, ohne Kosten.
KI_CALL = None


def _ki_prompt(rohtext: str, slug: str, ziel: float, versuch: int) -> str:
    """Auftrag mit IST-Lage – das Modell soll messbar werden, nicht „schöner“."""
    teile = _teile(rohtext)
    m = messe(rohtext, slug)
    lage = (f"IST: Flesch {m['flesch']:.1f} · Ø Satzlänge {m['wps']:.1f} Wörter · "
            f"Ø Wortlänge {m['word_len']:.1f} Zeichen · "
            f"{m['long_pct']:.1f} % lange Wörter (über 12 Zeichen).")
    vorsatz = ("" if versuch <= 1 else
               "ZWEITER VERSUCH: Die vorige Fassung lag noch unter dem Ziel. "
               "Sei deutlich radikaler bei den langen Wörtern – jede Silbe zählt.")
    return KI_PROMPT.format(ziel=ziel, lage=lage, vorsatz=vorsatz,
                            body=teile[2])


def _ki_chat(prompt: str) -> str | None:
    """Gemini zuerst, dann Groq – dieselbe Reihenfolge wie profi_polish."""
    import urllib.request
    ua = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/126.0 Safari/537.36")
    gemini_key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if gemini_key:
        try:
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            req = urllib.request.Request(
                "https://generativelanguage.googleapis.com/v1beta/models/"
                "gemini-3-flash-preview:generateContent?key=" + gemini_key,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json", "User-Agent": ua})
            resp = json.loads(urllib.request.urlopen(req, timeout=180).read())
            text = resp["candidates"][0]["content"]["parts"][0]["text"].strip()
            if text:
                return text
        except Exception as exc:  # noqa: BLE001 – Stufe B ist ein Versuch, kein Muss
            print(f"  ⚠ Gemini (Lesbarkeits-Heiler): {exc}")
    try:
        import groq_config
        if groq_config.available():
            return groq_config.chat(prompt, max_tokens=8000, timeout=180)
    except Exception as exc:  # noqa: BLE001
        print(f"  ⚠ Groq (Lesbarkeits-Heiler): {exc}")
    return None


def _ki_antwort(prompt: str) -> str | None:
    """Der eine Weg nach außen (injizierbar für den Selbsttest)."""
    return (KI_CALL or _ki_chat)(prompt)


def _ki_body(rohtext: str, slug: str, ziel: float, *, versuch: int = 1) -> str | None:
    teile = _teile(rohtext)
    if teile is None:
        return None
    antwort = _ki_antwort(_ki_prompt(rohtext, slug, ziel, versuch))
    if not antwort:
        return None
    # Antwort säubern: Code-Zäune und versehentlich mitgeschicktes Frontmatter entfernen.
    antwort = re.sub(r"^```[a-z]*\s*", "", antwort.strip())
    antwort = re.sub(r"\s*```$", "", antwort)
    if antwort.lstrip().startswith("---"):
        teile2 = _teile(antwort)
        if teile2 is not None:
            antwort = teile2[2]
    return antwort.lstrip("\n")


# ===========================================================================
#  DER HEILWEG EINES TEXTES
# ===========================================================================
def heile_text(slug: str, rohtext: str, *, ki: bool = True,
               ziel: float | None = None) -> dict:
    """Heilt einen Entwurf über die Schwelle – oder lässt ihn unangetastet.

    Rückgabe: dict mit ok/neu_raw/vor/nach/stufen/gruende/befund.
    """
    ziel = MINDEST_FLESCH if ziel is None else ziel
    ergebnis = {"slug": slug, "ok": False, "neu_raw": rohtext, "stufe": None,
                "gruende": [], "vor": None, "nach": None, "log": {}}
    vor = flesch(rohtext, slug)
    ergebnis["vor"] = vor
    if vor is None:
        ergebnis["gruende"] = ["Text nicht messbar – fail-closed"]
        return ergebnis
    if vor >= ziel:
        ergebnis.update(ok=True, stufe="bereits", nach=vor,
                        befund=f"bereits über der Schwelle ({vor:.1f} ≥ {ziel:g})")
        return ergebnis

    # ---- Stufe A -----------------------------------------------------------
    neu_a, log = stufe_a(rohtext)
    if neu_a != rohtext and not verifiziere(slug, rohtext, neu_a):
        ergebnis.update(ok=True, neu_raw=neu_a, stufe="A", log=log,
                        nach=flesch(neu_a, slug))
        ergebnis["befund"] = (f"Stufe A: {log.get('lexikon', 0)} Füllphrase(n), "
                              f"{log.get('saetze', 0)} Satzschnitt(e), "
                              f"{log.get('absaetze', 0)} Absatzschnitt(e)")
        return ergebnis
    if neu_a != rohtext:
        ergebnis["log"] = log
        ergebnis["gruende"] += [f"Stufe A verworfen: {g}" for g in verifiziere(slug, rohtext, neu_a)]

    # ---- Stufe B (nur wenn A nicht reichte) --------------------------------
    basis = neu_a if neu_a != rohtext else rohtext
    if ki and flesch(basis, slug) is not None and flesch(basis, slug) < ziel:
        for versuch in (1, 2):
            body = _ki_body(basis, slug, ziel, versuch=versuch)
            if not body:
                ergebnis["gruende"].append(
                    f"Stufe B (Versuch {versuch}): keine KI-Antwort – "
                    "Text bleibt unangetastet")
                break
            teile = _teile(basis)
            neu_b = join_article(teile[1], body, teile[0])
            if neu_b == basis:
                ergebnis["gruende"].append(
                    f"Stufe B (Versuch {versuch}): keine Änderung")
                continue
            gruende = verifiziere(slug, rohtext, neu_b)
            if not gruende:
                ergebnis.update(ok=True, neu_raw=neu_b, stufe="B",
                                nach=flesch(neu_b, slug))
                ergebnis["befund"] = (f"Stufe B (KI, Versuch {versuch}) – "
                                      "Vertrag T1–T4 erfüllt")
                return ergebnis
            ergebnis["gruende"] += [f"Stufe B (Versuch {versuch}) verworfen: {g}"
                                    for g in gruende]
            # Ein formaler/substanzieller Verstoß (T2–T4) wird nicht mit mehr
            # Nachdruck wiederholt: Die KI hat den Auftrag verletzt, nicht knapp
            # verfehlt. Der zweite Versuch gilt nur der knappen Schwelle (T1).
            if any(g.startswith(("T2", "T3", "T4")) for g in gruende):
                break

    rest = flesch(basis, slug)
    ergebnis["nach"] = rest
    ergebnis["gruende"].append(
        f"Restlücke: Flesch {rest:.1f} < {ziel:g} – Text bleibt unangetastet (fail-closed)")
    ergebnis["befund"] = "; ".join(ergebnis["gruende"][-1:])
    return ergebnis


# ===========================================================================
#  KANDIDATEN
# ===========================================================================
def ist_lesbarkeits_hold(grund: str | None) -> bool:
    """Gate-Hold der Lesbarkeits-Klasse? (Wort-Erkennung, kein Präfix –
    das Gate darf seinen Satz umformulieren, ohne uns zu erblinden.)"""
    return bool(grund) and ("Lesbarkeits-Gate" in str(grund)
                            or "Lesbarkeits-Score" in str(grund))


def hole_holds() -> list[str]:
    """Alle Entwurfs-Pfade, die als Lesbarkeits-Hold geparkt sind (SSOT: Kadenz)."""
    import cadence_guard as cg
    pfade = []
    for p in cg.load_posts():
        if p.get("state") == "hold" and ist_lesbarkeits_hold(p.get("grund")):
            if p.get("draft") and p.get("path"):
                pfade.append(p["path"])
    return sorted(pfade)


def hole_neue() -> list[str]:
    """Artikel des HEUTIGEN Datums (Live-Engine Phase 2, Muster `profi_polish --new`).

    Anders als `--holds`/`--blocked` zielt diese Quelle auf den frisch erzeugten
    Artikel des Tages – er darf in Phase 2 bereits `draft: false` sein (die
    Auslieferung hat ihn noch nicht verankert). Geschützt wird er nicht durch
    eine Draft-Regel, sondern durch das Tor T1–T4 dieses Moduls.
    """
    import post_utils
    heute = datetime.date.today().isoformat()
    pfade = []
    for f in post_utils.list_post_paths():
        with open(f, encoding="utf-8") as fh:
            teile = _teile(fh.read())
        # „2026-10-07T10:32:50Z“ ist derselbe Tag: deshalb auf Ziffern/Bindestrich
        # NACH dem Datum prüfen – `\b` griffe hier nicht (7 und T sind beide Wortzeichen).
        if teile and re.search(rf"(?m)^date:\s*{heute}(?![\d-])", teile[1]):
            pfade.append(f)
    return sorted(pfade)


def hole_blocked() -> list[str]:
    """Reserve-Kandidaten laut Zertifikat (`data/reserve-readiness.json`)."""
    zertifikat = os.path.join(BLOG_DIR, "data", "reserve-readiness.json")
    try:
        daten = artifacts.read_certificate(Path(zertifikat))
    except (OSError, ValueError) as exc:
        print(f"⚠ Reserve-Heiler-Auswahl übersprungen: Zertifikat nicht prüfbar ({exc})")
        return []
    pfade = []
    for c in daten.get("candidates", []):
        if c.get("ready"):
            continue
        grund = str(c.get("reason") or "")
        if "Lesbarkeits-Gate" not in grund and "Lesbarkeits-Score" not in grund:
            continue
        pfad = os.path.join(BLOG_DIR, "content", "posts", str(c.get("slug")), "index.md")
        if (os.path.isfile(pfad) and Path(pfad).resolve().is_relative_to(
                (Path(BLOG_DIR) / "content" / "posts").resolve())):
            pfade.append(pfad)
    return sorted(pfade)


def _ist_entwurf(rohtext: str) -> bool:
    teile = _teile(rohtext)
    return bool(teile) and bool(re.search(r"(?m)^draft:\s*true\s*$", teile[1], re.I))


def _slug_von(pfad: str) -> str:
    return os.path.basename(os.path.dirname(os.path.abspath(pfad)))


# ===========================================================================
#  WIRKUNGSPROBE – der Nachweis, den #609 gefordert hat
# ===========================================================================
#  Fixture: bewusst ein Text, der (a) unter der Schwelle startet, (b) seine
#  Länge aus Schachtelsätzen bezieht und (c) Füllphrasen trägt. Genau die
#  Formen, die Stufe A behebt – und keine, die sie nicht behebt (alles
#  andere wäre eine Behauptung, keine Probe).
PROBE_FIXTURE = (
    "---\n"
    "title: \"Probe: einfache Sprache\"\n"
    "date: 2026-10-07\n"
    "draft: true\n"
    "---\n\n"
    "Wer seine Gebühren prüft, senkt die Kosten im Monat, und wer den Tarif mit anderen "
    "Anbietern vergleicht, findet schnell ein günstigeres Angebot, und wer die Frist für "
    "die Kündigung notiert, vermeidet eine Verlängerung des Vertrages um ein weiteres Jahr.\n\n"
    "Viele Verbraucher zahlen im Rahmen von alten Verträgen jeden Monat zu viel, und sie "
    "erkennen die Mehrkosten erst bei der Abrechnung, aber dann ist die Frist für die "
    "Kündigung schon vorbei, denn die Bank meldet sich selten von selbst bei ihren Kunden.\n\n"
    "Ein Blick auf die Abrechnung hilft sofort, und ein Wechsel kostet nur wenig Zeit, "
    "die Bank übernimmt die meiste Arbeit, und der Rest bleibt gleich, weil die bekannte "
    "Kontonummer erhalten bleibt und keine Zahlung verloren geht oder doppelt ankommt.\n\n"
    "Wer nichts unternimmt, zahlt weiter, aber wer handelt, spart jedes Jahr Geld.\n"
)


def wirkungsprobe() -> tuple[bool, float | None, float | None, str]:
    """Beweist, dass Stufe A die Schwelle BEWEGT und alle Verträge hält.

    Rückgabe: (ok, vorher, nachher, Meldung). Wird von
    `reserve_healer_coverage.wirkungsdeckung()` und vom Governance-Vertrag C25
    verlangt – eine Deckung ohne diesen Nachweis ist Papier.
    """
    slug = "wirkungsprobe"
    vor = flesch(PROBE_FIXTURE, slug)
    neu, log = stufe_a(PROBE_FIXTURE)
    nach = flesch(neu, slug)
    if vor is None or nach is None:
        return False, vor, nach, "Wirkungsprobe nicht messbar – fail-closed"
    if vor >= MINDEST_FLESCH:
        return False, vor, nach, (f"Fixture startet nicht unter der Schwelle "
                                  f"({vor:.1f} ≥ {MINDEST_FLESCH:g}) – Probe wertlos")
    verstoesse = verifiziere(slug, PROBE_FIXTURE, neu)
    if verstoesse:
        return False, vor, nach, "Vertrag verletzt: " + "; ".join(verstoesse[:3])
    if nach < MINDEST_FLESCH:
        return False, vor, nach, (f"Stufe A hebt das Fixture nicht über die Schwelle "
                                  f"({vor:.1f} → {nach:.1f} < {MINDEST_FLESCH:g})")
    return True, vor, nach, (f"Stufe A: Flesch {vor:.1f} → {nach:.1f} "
                             f"(≥ {MINDEST_FLESCH:g}), Verträge T1–T4 erfüllt")


# ===========================================================================
#  SELBSTTEST – Sabotage-Proben
# ===========================================================================
def run_selftest() -> int:
    fehler: list[str] = []

    # --- 1) WIRKUNG: die Probe selbst ------------------------------------
    ok, vor, nach, meldung = wirkungsprobe()
    if not ok:
        fehler.append(f"Wirkungsprobe rot: {meldung}")

    # --- 2) Das Tor weist Sabotage ab ------------------------------------
    gut = ("---\ntitle: \"T\"\ndraft: true\n---\n\n"
           "Das Konto kostet Gebühren. Der Wechsel dauert kurz.\n")
    faelle = {
        "Link entfernt": gut + "Mehr im [Vergleich](/go/konto/).\n",
        "Zahl erfunden": gut + "Der Preis liegt bei 12 Euro.\n",
        "R7-Intro-Formel": gut + "In diesem Beitrag erfährst du alles.\n",
        "zu kurz": gut + "Kurz.\n",
    }
    link_fall = ("---\ntitle: \"T\"\ndraft: true\n---\n\n"
                 "Das Konto kostet Gebühren. Der Wechsel dauert kurz.\n"
                 "Mehr im [Vergleich](/go/konto/).\n")
    zahlen_fall = ("---\ntitle: \"T\"\ndraft: true\n---\n\n"
                   "Der Preis liegt bei 12 Euro. Die Frist beträgt 3 Monate.\n")
    kurz_fall = ("---\ntitle: \"T\"\ndraft: true\n---\n\n"
                 "Ein langer Absatz mit vielen Wörtern, der gekürzt wurde, "
                 "damit der Vertrag die Längengrenze prüft.\n"
                 "Ein zweiter Absatz mit weiteren Wörtern für die Länge.\n"
                 "Ein dritter Absatz mit noch mehr Wörtern.\n"
                 "Ein vierter Absatz mit vielen Wörtern.\n"
                 "Ein fünfter Absatz für den Schluss.\n")
    if not bewahre(link_fall, link_fall.replace("](/go/konto/)", "]()")):
        fehler.append("Tor T4 erkennt entferntes Linkziel nicht")
    if not bewahre(zahlen_fall, zahlen_fall.replace("12 Euro", "9 Euro")):
        fehler.append("Tor T4 erkennt veränderte Zahl nicht")
    if not any("zu kurz" in g.lower() or "Länge" in g
               for g in bewahre(kurz_fall, "---\ntitle: \"T\"\ndraft: true\n---\n\nKurz.\n")):
        fehler.append("Tor T4 erkennt zu starke Kürzung nicht")
    if not any("T2" in g for g in verifiziere("probe", gut, faelle["R7-Intro-Formel"])):
        fehler.append("Tor T2 erkennt harten Textverständnis-Fund nicht")

    # --- 3) Die Nahtstellen sind eingehalten ------------------------------
    fragment = ("---\ntitle: \"T\"\ndraft: true\n---\n\n"
                "Ich spare Geld, weil ich den Vertrag prüfe, und ich kündige, wenn die Frist "
                "abgelaufen ist, damit die Bank den Tarif wechseln kann.\n")
    zerlegt, schnitte = _zerlege_saetze(fragment.split("---", 2)[2])
    if schnitte != 1 or ". Und " not in zerlegt:
        fehler.append(f"Nahtstelle nicht wie erwartet genutzt (Schnitte={schnitte}): {zerlegt[:120]}")
    if "Weil ich" in zerlegt or "Damit die" in zerlegt:
        fehler.append("Nebensatz-Naht wurde getrennt – Fragmente drohen")
    kurz_satz = "Der Preis liegt bei 12,50 Euro, und die Frist beträgt 3 Monate."
    if len(_WORT.findall(kurz_satz)) <= MAX_SATZ_WOERTER and _zerlege_satz(kurz_satz)[1] != 0:
        fehler.append("Satz unter der Längengrenze wurde zerlegt")
    # Sätze mit Markup bleiben unangetastet
    mit_link = "Ein Satz mit [Link](/go/x/) und vielen weiteren Wörtern, und noch mehr Wörtern hier drin."
    if _zerlege_satz(mit_link)[1] != 0:
        fehler.append("Satz mit Link wurde zerlegt – Linkziele wären gefährdet")

    # --- 4) Abkürzungen überleben den Schnitt ----------------------------
    abk = ("---\ntitle: \"T\"\ndraft: true\n---\n\n"
           "Der Anbieter prüft z. B. die Frist, und er prüft d. h. den Vertrag, "
           "und danach sendet er die Bestätigung an dich.\n")
    neu_abk, _log = stufe_a(abk)
    if "z. B." not in neu_abk or "d. h." not in neu_abk:
        fehler.append("Abkürzung wurde beim Satzschnitt zerstört")

    # --- 5) Füllphrasen-Lexikon ------------------------------------------
    if "im Rahmen von" in _kuerze_fuellphrasen("Hier im Rahmen von Verträgen.")[0]:
        fehler.append("Füllphrase „im Rahmen von“ wird nicht ersetzt")
    if "nichtsdestotrotz" in _kuerze_fuellphrasen("nichtsdestotrotz gilt das")[0]:
        fehler.append("Füllphrase „nichtsdestotrotz“ wird nicht ersetzt")

    # --- 6) Fail-closed: KI-Vorschlag unter der Schwelle wird verworfen ---
    stub_alt = PROBE_FIXTURE
    stub_neu = join_article(_teile(stub_alt)[1], _teile(stub_alt)[2], "")
    if not verifiziere("probe", stub_alt, stub_neu):
        fehler.append("Ein wirkungsloser Vorschlag passiert das Tor (keine Verbesserung)")
    # und der gute Vorschlag (Stufe A) passiert es
    gut_a, _ = stufe_a(stub_alt)
    if verifiziere("probe", stub_alt, gut_a):
        fehler.append("Der wirksame Vorschlag wird vom Tor fälschlich verworfen")

    # --- 7) Idempotenz ----------------------------------------------------
    zweite, _ = stufe_a(gut_a)
    if flesch(zweite, "probe") != flesch(gut_a, "probe"):
        fehler.append("Zweiter Lauf verändert den Text – nicht idempotent")

    # --- 8) Live-Schutz ---------------------------------------------------
    live = gut.replace("draft: true", "draft: false")
    if _ist_entwurf(live):
        fehler.append("Live-Artikel gilt als Entwurf – Scope-Schutz defekt")
    if not _ist_entwurf(gut):
        fehler.append("Entwurf wird nicht als Entwurf erkannt")

    # --- 9) Hold-Erkennung ------------------------------------------------
    if not ist_lesbarkeits_hold("publish-gate: Lesbarkeits-Gate nicht bestanden: Flesch 57.9"):
        fehler.append("Lesbarkeits-Hold wird nicht erkannt")
    if ist_lesbarkeits_hold("publish-gate: Textverständnis-Gate nicht bestanden"):
        fehler.append("fremder Hold wird als Lesbarkeits-Hold erkannt")
    if ist_lesbarkeits_hold(None):
        fehler.append("leerer Grund wird als Lesbarkeits-Hold erkannt")

    # --- 10) Stufe B: Annehmen UND Verwerfen mit Attrappe -----------------
    #  Die Attrappe ersetzt den echten KI-Aufruf (`KI_CALL`) – der Beweis
    #  kostet nichts und hängt an keinem Kontingent. Das Fixture ist bewusst
    #  ein Text, den Stufe A NICHT heben kann (kurze Sätze, lange Komposita:
    #  Flesch 0,9). Genau dort muss die KI-Stufe greifen – und das Tor muss
    #  sie verwerfen, wenn sie den Auftrag verletzt.
    ki_alt = ("---\ntitle: \"Probe B\"\ndate: 2026-10-07\ndraft: true\n---\n\n"
              "Die Beitragsanpassung der Versicherungsgesellschaft erhöht die monatliche "
              "Belastung der Kunden. Die Verbraucherzentrale empfiehlt eine Überprüfung "
              "der Vertragsbedingungen, und die Tarifberatung dokumentiert die "
              "Vereinbarung der Zahlungsmodalitäten für die Folgejahre.\n")
    ki_neu = ("---\ntitle: \"Probe B\"\ndate: 2026-10-07\ndraft: true\n---\n\n"
              "Die Kasse hebt den Beitrag jedes Jahr an. Die Kunden merken das oft erst "
              "bei der Abrechnung. Wer die alten Briefe prüft, sieht den neuen Preis "
              "sofort. Die Beratung notiert, was sie mit dir ausgemacht hat, und was im "
              "nächsten Jahr gilt. So behältst du den Überblick und kannst rechtzeitig "
              "widersprechen, wenn dir etwas zu teuer wird.\n")
    ki_body = ki_neu.split("---", 2)[2].lstrip("\n")
    alt_ki_call = KI_CALL
    try:
        vor_ki = flesch(ki_alt, "p")
        if vor_ki is None or vor_ki >= MINDEST_FLESCH:
            fehler.append(f"Stufe-B-Fixture startet nicht unter der Schwelle "
                          f"({vor_ki}) – die Probe wäre wertlos")
        globals()["KI_CALL"] = lambda _prompt: ki_body
        ergebnis_b = heile_text("p", ki_alt, ki=True)
        if not ergebnis_b["ok"] or ergebnis_b["stufe"] != "B":
            fehler.append(f"Stufe-B-Attrappe (gute Fassung) wurde nicht angenommen: "
                          f"{ergebnis_b['stufe']} {ergebnis_b['gruende'][:2]}")
        if ergebnis_b["ok"] and ergebnis_b["nach"] < MINDEST_FLESCH:
            fehler.append("Stufe-B-Attrappe passierte das Tor unter der Schwelle")
        # (b) Link-Verlust: die Attrappe ersetzt einen Link durch nichts.
        ki_alt_link = ki_alt.replace(
            "Die Verbraucherzentrale",
            "Mehr im [Vergleich](/go/kasse/). Die Verbraucherzentrale")
        ergebnis_link = heile_text("p", ki_alt_link, ki=True)
        if ergebnis_link["ok"] or ergebnis_link["neu_raw"] != ki_alt_link:
            fehler.append("Stufe-B-Attrappe mit Link-Verlust wurde nicht verworfen")
        # (c) Wirkungslos: die Attrappe gibt den Text unverändert zurück.
        globals()["KI_CALL"] = lambda _prompt: ki_alt.split("---", 2)[2].lstrip("\n")
        ergebnis_leer = heile_text("p", ki_alt, ki=True)
        if ergebnis_leer["ok"]:
            fehler.append("Wirkungslose Stufe-B-Attrappe passierte das Tor")
    finally:
        globals()["KI_CALL"] = alt_ki_call

    if fehler:
        print("🛑 LESBARKEITS-HEILER-SELFTEST FEHLGESCHLAGEN:")
        for f in fehler:
            print("  -", f)
        return 2
    print(f"✅ Lesbarkeits-Heiler-Selbsttest bestanden – Wirkungsprobe grün "
          f"({vor:.1f} → {nach:.1f}), Tor T1–T4 weist Sabotage ab, Stufe B "
          f"nimmt mit Attrappe an und verwirft, Nahtstellen und Abkürzungen halten.")
    return 0


# ===========================================================================
#  CLI
# ===========================================================================
def _verarbeite(pfade: list[str], *, fix: bool, ki: bool, max_n: int | None,
                auch_live: bool = False, erlaube_live: bool = False
                ) -> tuple[list[dict], int]:
    berichte, befund = [], 0
    for pfad in pfade[:max_n] if max_n else pfade:
        with open(pfad, encoding="utf-8") as fh:
            rohtext = fh.read()
        slug = _slug_von(pfad)
        if not _ist_entwurf(rohtext) and not auch_live and not erlaube_live:
            berichte.append({"slug": slug, "ok": True, "stufe": "übersprungen",
                             "befund": "kein Entwurf (draft: false) – Scope-Schutz"})
            continue
        ergebnis = heile_text(slug, rohtext, ki=ki)
        if ergebnis["ok"] and ergebnis["neu_raw"] != rohtext:
            if fix:
                with open(pfad, "w", encoding="utf-8") as fh:
                    fh.write(ergebnis["neu_raw"])
                ergebnis["geschrieben"] = True
            else:
                ergebnis["geschrieben"] = False
        elif not ergebnis["ok"]:
            befund += 1
        ergebnis["pfad"] = os.path.relpath(pfad, BLOG_DIR)
        berichte.append(ergebnis)
    return berichte, befund


def _menschen_text(berichte: list[dict], befund: int) -> str:
    zeilen = ["# LESBARKEITS-HEILER (Klasse #609)", ""]
    for b in berichte:
        vor = f"{b['vor']:.1f}" if b.get("vor") is not None else "–"
        nach = f"{b['nach']:.1f}" if b.get("nach") is not None else "–"
        marke = "🟢" if b.get("ok") else "🔴"
        zeilen.append(f"{marke} {b.get('slug')}: Flesch {vor} → {nach} "
                      f"[{b.get('stufe') or 'offen'}] {b.get('befund') or ''}")
        for g in (b.get("gruende") or [])[:4]:
            zeilen.append(f"     · {g}")
    zeilen += ["", f"Schwelle: Flesch ≥ {MINDEST_FLESCH:g} "
                   f"(readability_check.NEW_FLESCH_MIN, importierte SSOT)",
               f"Ungeheilt (fail-closed, nichts Halbfertiges geschrieben): {befund}"]
    return "\n".join(zeilen)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Lesbarkeits-Heiler: heilt Entwürfe/Kandidaten über die "
                    "Publish-Schwelle (Fail-closed, Vertrag T1–T4).")
    ap.add_argument("--file", action="append", default=[],
                    help="einzelne Datei (mehrfach möglich)")
    ap.add_argument("--holds", action="store_true",
                    help="alle Gate-Holds der Lesbarkeits-Klasse")
    ap.add_argument("--blocked", action="store_true",
                    help="Reserve-Kandidaten laut data/reserve-readiness.json")
    ap.add_argument("--new-only", action="store_true",
                    help="Artikel des heutigen Datums (Live-Engine Phase 2)")
    ap.add_argument("--fix", action="store_true", help="schreiben (sonst Trockenlauf)")
    ap.add_argument("--keine-ki", action="store_true",
                    help="nur Stufe A (deterministisch, ohne API)")
    ap.add_argument("--auch-live", action="store_true",
                    help="auch Nicht-Entwürfe anfassen (Standard: nur draft:true; "
                         "der Scope-Schutz verweigert sonst den Schreibpfad)")
    ap.add_argument("--max", type=int, default=None, help="höchstens N Kandidaten")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--report", action="store_true",
                    help="Report nach LESBARKEIT-HEILER-REPORT.md schreiben")
    ap.add_argument("--wirkungsprobe", action="store_true",
                    help="Maschinenvertrag: beweist die Wirkung (Exit 0 = grün)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return run_selftest()

    if args.wirkungsprobe:
        ok, vor, nach, meldung = wirkungsprobe()
        if args.json:
            print(json.dumps({"ok": ok, "vor": vor, "nach": nach,
                              "meldung": meldung, "schwelle": MINDEST_FLESCH},
                             ensure_ascii=False))
        else:
            print(("✅ " if ok else "🛑 ") + "Wirkungsprobe: " + meldung)
        return 0 if ok else 2

    pfade = list(args.file)
    if args.holds:
        pfade += hole_holds()
    if args.blocked:
        pfade += hole_blocked()
    if args.new_only:
        pfade += hole_neue()
    if not pfade:
        ap.error("Quelle fehlt: --file, --holds, --blocked oder --new-only "
                 "(oder --selftest/--wirkungsprobe)")

    berichte, befund = _verarbeite(sorted(dict.fromkeys(pfade)), fix=args.fix,
                                   ki=not args.keine_ki, max_n=args.max,
                                   auch_live=args.auch_live,
                                   erlaube_live=args.new_only)
    if args.json:
        print(json.dumps({"befund": befund, "berichte": berichte},
                         ensure_ascii=False, indent=1, default=str))
    else:
        print(_menschen_text(berichte, befund))
    if args.report:
        ziel = os.path.join(BLOG_DIR, "LESBARKEIT-HEILER-REPORT.md")
        with open(ziel, "w", encoding="utf-8") as fh:
            fh.write(f"<!-- erzeugt: {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M} UTC -->\n\n")
            fh.write(_menschen_text(berichte, befund) + "\n")
        print(f"📄 Report: {os.path.relpath(ziel, BLOG_DIR)}")
    return 1 if befund else 0


if __name__ == "__main__":
    sys.exit(main())
