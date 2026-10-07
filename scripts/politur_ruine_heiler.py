#!/usr/bin/env python3
# ============================================================
#  POLITUR-RUINEN-HEILER (R11/R13/R14) – WF-D4E0 / #612, 07.10.2026
#
#  WARUM DIESER HEILER
#  -------------------
#  Die Reserve-Stufe 3 zertifiziert mit dem ECHTEN Publish-Gate. Dort
#  blockiert seit #482 die Politur-Ruinen-Familie R9–R15 (SSOT:
#  `sprachkern.POLITUR_RUINEN`) – Reste automatisierter Politur-Läufe, die
#  im deutschen Satz nie korrekt sind. In der Heiler-Kette der Reserve war
#  die Familie NICHT vertreten: `textverstaendnis_failures` galt über
#  R5-Absatz-Splitter und URL-Hygiene als „gedeckt“, für R11/R13/R14 gab es
#  aber keinen Schreiber.
#
#  Reale Folge am 07.10.2026 (Vorgang WF-D4E0, Issue #612): Der Kandidat
#  `2026-10-07-wie-smart-home-geraete-…` stand mit EINER Ruine im Pool –
#
#      SATZ: | Thread | 2,4 GHz | 10–20 m (Mesh) | 0,05–0,2 W | 40–80 € |
#
#  – einem Tablettenschaden aus einem Politur-Lauf („SATZ: “ vor einer
#  vollständig intakten Tabellenzeile). Zertifikat: Qualität 0,95, alle
#  übrigen Tore grün – der Kandidat war fertig und wurde trotzdem nie
#  veröffentlicht. Kein Werkzeug der Kette durfte den Marker entfernen, die
#  Zertifizierung läuft fail-closed (STRICT-DRY-RUN), und die Quarantäne
#  nahm ihn als `reserve_blocked` aus dem Spiel (Lauf 37607427999). Der
#  Vorrat fiel unter das Ziel, der harte End-Gate wurde rot.
#
#  Ein Blocker ohne Heiler ist ein unerreichbares Ziel (Lehre #594, #349).
#  Dieses Skript ist der fehlende Heiler der Klasse. Es heilt ausschließlich,
#  was es BEWEISEN kann, und lässt alles andere liegen:
#
#    R11-JAHRESZAHL-SPLIT  „20 26“  → „2026“   (Ziffern wieder verbinden)
#    R13-DATUM-PUNKT       „2 Januar“ → „2. Januar“ (fehlenden Punkt setzen)
#    R14-MARKER-RUINE      „SATZ: | … |“ → „| … |“ (Marker-Präfix entfernen)
#
#  BEWUSST NICHT GEHEILT (fail-closed, nur gemeldet):
#    R12-ZAHL-RUINE   „der 0 am deutschen Strommarkt“ – die fehlende Zahl ist
#                     nicht rekonstruierbar; ein Ratespiel wäre eine Fälschung.
#    R16-PROMPT-ECHO  Prompt-Sprache im Fließtext/Meta – inhaltliche
#                     Umschreibung, kein deterministischer Schnitt.
#  Beide bleiben als Befund stehen; die Zertifizierung entscheidet wie bisher.
#
#  DAS TOR (T1–T4) – geschrieben wird nur, was alle vier erfüllt:
#    T1 WIRKUNG   Jede heilbare Ruine der Datei ist danach verschwunden und
#                 KEINE neue Ruine (irgendeiner Klasse) entstanden.
#    T2 REGELN    Kein neuer harter Fund aus `publish_gate.HARTE_REGELN`
#                 (gemessen mit `textverstaendnis_guard.check_article`).
#    T3 GESTALT   Links, Shortcodes, Überschriften und Frontmatter byte-identisch,
#                 Wortzahl ≥ 97 % des Originals (R14 entfernt nur Marker).
#    T4 BEWEIS    Ein zweiter Lauf findet nichts mehr (Idempotenz) und die
#                 SSOT-Muster `sprachkern.POLITUR_RUINEN` bestätigen den Erfolg.
#
#  NUTZUNG
#  -------
#    python3 scripts/politur_ruine_heiler.py --file content/posts/<slug>/index.md
#    python3 scripts/politur_ruine_heiler.py --file … --fix      # schreiben
#    python3 scripts/politur_ruine_heiler.py --new-only --fix    # heutige Artikel
#    python3 scripts/politur_ruine_heiler.py --auch-live --fix   # Live-Bestand
#    python3 scripts/politur_ruine_heiler.py --selftest          # Sabotage-Proben
#    python3 scripts/politur_ruine_heiler.py --wirkungsprobe     # Maschinenvertrag
# ============================================================
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import sprachkern  # noqa: E402 – Muster-SSOT der Politur-Ruinen
from post_utils import join_article  # noqa: E402 – Naht-SSOT
from textverstaendnis_guard import (  # noqa: E402
    check_article, frontmatter_keywords, load_terminologie, split_body,
)

# ---------------------------------------------------------------------------
#  HEILBARE KLASSEN – namentlich, nicht per Musterkopie
# ---------------------------------------------------------------------------
#  Die Muster kommen ausschließlich aus `sprachkern.POLITUR_RUINEN`. Wird dort
#  eine neue Klasse ergänzt, meldet der Selbsttest sie als „ungeprüft“ und
#  dieser Heiler heilt sie NICHT (fail-closed) – eine zweite Musterliste wäre
#  genau die zweite Wahrheit, die dieses Repo sich mehrfach verboten hat.
HEILBAR: dict[str, str] = {
    "R11-JAHRESZAHL-SPLIT": "Ziffern der zerrissenen Jahreszahl verbinden",
    "R13-DATUM-PUNKT": "fehlenden Punkt des Ordinal-Datums setzen",
    "R14-MARKER-RUINE": "Marker-Präfix am Zeilenanfang entfernen",
}
NICHT_HEILBAR: dict[str, str] = {
    "R12-ZAHL-RUINE": "die fehlende Zahl ist nicht rekonstruierbar (Raten "
                      "wäre eine Fälschung) – redaktioneller Fall",
    "R16-PROMPT-ECHO": "Prompt-Sprache im Text/Meta – braucht Umschreibung, "
                       "keinen Schnitt",
}
# Marker-Wörter für R14 (SSOT-Liste der Klasse, sichtbar für den Selbsttest).
MARKER_WOERTER = ("SATZ", "TOKEN", "MARKER", "PLACEHOLDER", "TODO", "FIXME",
                  "XXX", "DEBUG", "ROW", "ZEILE", "NL", "REST")
_MARKER_ZEILE = re.compile(
    r"^(?P<einzug>\s*)(?P<marker>SATZ|TOKEN|MARKER|PLACEHOLDER|TODO|FIXME|"
    r"XXX|DEBUG|ROW|ZEILE|NL|REST)\s*[:\|]\s?(?P<rest>.*)$")

_WORT = re.compile(r"\b\w+\b")


def _muster_der(regel: str):
    """Muster einer Ruinen-Klasse aus der SSOT (None = Klasse unbekannt)."""
    for name, rx, _desc in sprachkern.POLITUR_RUINEN:
        if name == regel:
            return rx
    return None


def _ruinen(text: str) -> list[tuple[str, str]]:
    """Alle Ruinen im Text (SSOT-Muster) – auch die nicht heilbaren."""
    return list(sprachkern.politur_ruine_funde(text))


def _heile_muster(text: str, regel: str) -> tuple[str, int]:
    """Heilt EINE musterbasierte Klasse (R11/R13). Rückgabe: (Text, Anzahl)."""
    rx = _muster_der(regel)
    if rx is None:
        return text, 0
    if regel == "R11-JAHRESZAHL-SPLIT":
        def _ersatz(m):
            return re.sub(r"\s+", "", m.group(0))
    elif regel == "R13-DATUM-PUNKT":
        def _ersatz(m):
            return re.sub(r"^(\d{1,2})\s+", r"\1. ", m.group(0))
    else:                                           # pragma: no cover – Tor
        return text, 0
    neu, n = rx.subn(_ersatz, text)
    return neu, n


def _heilbare_zeile(rest: str) -> bool:
    """Steht der Rest einer Marker-Zeile für sich? (fail-closed)

    Nur Konstrukte, die auch ohne den Marker vollständig sind: Tabellenzeile,
    Listenpunkt, Überschrift, Zitat – oder ein ganzer Satz mit mindestens vier
    Wörtern und Satzende. Alles andere bleibt liegen (ein halber Satz wäre
    schlimmer als der Marker).
    """
    r = rest.strip()
    if not r:
        return True                       # nackter Marker: die Zeile entfällt
    if r[0] in "|#>":
        return True
    if re.match(r"^([-*+]|\d+\.)\s+\S", r):
        return True
    worte = len(_WORT.findall(r))
    return worte >= 4 and r.endswith((".", "!", "?", ":"))


def _heile_marker(text: str) -> tuple[str, int, list[str]]:
    """Heilt R14: Marker-Präfix am Zeilenanfang entfernen.

    Rückgabe: (Text, Anzahl, offene Zeilen). Eine Zeile, deren Rest nicht für
    sich stehen kann, bleibt UNVERÄNDERT und wird als offen gemeldet – der
    Aufrufer schreibt dann nichts (das Tor ist Alles-oder-Nichts je Datei).
    """
    zeilen = text.split("\n")
    neu, n, offen = [], 0, []
    for zeile in zeilen:
        m = _MARKER_ZEILE.match(zeile)
        if not m:
            neu.append(zeile)
            continue
        rest = m.group("rest")
        if not _heilbare_zeile(rest):
            offen.append(zeile.strip()[:120])
            neu.append(zeile)
            continue
        neu.append(m.group("einzug") + rest.strip() if rest.strip() else "")
        n += 1
    return "\n".join(neu), n, offen


# ---------------------------------------------------------------------------
#  DAS TOR (T1–T4)
# ---------------------------------------------------------------------------
def _link_zahl(text: str) -> int:
    return len(re.findall(r"!?\[[^\]]*\]\([^)]*\)", text))


def _shortcode_zahl(text: str) -> int:
    return len(re.findall(r"\{\{[<%].*?[>%]\}\}", text, re.S))


def _ueberschriften(text: str) -> list[str]:
    return re.findall(r"(?m)^#{1,6}\s.*$", text)


def _harte_funde(rohtext: str, slug: str) -> list[str]:
    """Harte Publish-Gate-Funde einer Fassung (SSOT-Liste, keine zweite)."""
    import publish_gate as gate
    body = split_body(rohtext)
    finds = check_article(f"content/posts/{slug}/index.md", body,
                          load_terminologie(), frontmatter_keywords(rohtext))
    return sorted({f[1] for f in finds if f[1] in gate.HARTE_REGELN})


def verifiziere(slug: str, alt_raw: str, neu_raw: str,
                verlust_erklärt: int = 0) -> list[str]:
    """T1–T4. Leere Liste = geschrieben werden darf. Jeder Grund blockiert.

    `verlust_erklärt`: Wortzahl-Verluste, die die Heilung selbst erklärt (eine
    entfernte Marker-Ruine ist ein Wort, eine verbundene Jahreszahl eines) –
    ohne diesen Nachlass wäre die 97-%-Regel in kurzen Fixtures unerfüllbar,
    obwohl der Eingriff nachweislich nur den Defekt entfernt.
    """
    gruende: list[str] = []
    alt_teile = alt_raw.split("---", 2)
    neu_teile = neu_raw.split("---", 2)
    if len(neu_teile) != 3:
        return ["T0: neue Fassung ohne Frontmatter-Grenzen"]

    # T1 – Wirkung: keine heilbare Ruine mehr, keine neue Ruine irgendeiner Klasse
    alt_funde = _ruinen(alt_raw)
    neu_funde = _ruinen(neu_raw)
    rest = [f for f in neu_funde if f[0] in HEILBAR]
    if rest:
        gruende.append("T1: Ruinen der heilbaren Klasse(n) stehen noch im Text "
                       f"({', '.join(sorted({f[0] for f in rest}))})")
    neu_dazu = [f for f in neu_funde if f not in alt_funde]
    if neu_dazu:
        gruende.append(f"T1: neue Ruine eingeführt ({neu_dazu[0][0]}: "
                       f"„{neu_dazu[0][1][:40]}“)")

    # T2 – Regeln: kein neuer harter Fund
    alt_hart, neu_hart = set(_harte_funde(alt_raw, slug)), set(_harte_funde(neu_raw, slug))
    if neu_hart - alt_hart:
        gruende.append("T2: neuer harter Fund "
                       f"({', '.join(sorted(neu_hart - alt_hart))})")

    # T3 – Gestalt: Struktur und Frontmatter byte-identisch
    if alt_teile[1] != neu_teile[1]:
        gruende.append("T3: Frontmatter verändert (der Heiler fasst ihn nie an)")
    for name, alt_wert, neu_wert in (
            ("Links", _link_zahl(alt_raw), _link_zahl(neu_raw)),
            ("Shortcodes", _shortcode_zahl(alt_raw), _shortcode_zahl(neu_raw)),
            ("Überschriften", _ueberschriften(alt_raw), _ueberschriften(neu_raw))):
        if alt_wert != neu_wert:
            gruende.append(f"T3: {name} verändert ({alt_wert} → {neu_wert})")
    alt_w = len(_WORT.findall(alt_raw.split("---", 2)[2]))
    neu_w = len(_WORT.findall(neu_teile[2]))
    if neu_w < 0.97 * alt_w - verlust_erklärt:
        gruende.append(f"T3: Wortzahl eingebrochen ({alt_w} → {neu_w})")

    # T4 – Beweis: Idempotenz (ein zweiter Lauf findet nichts mehr)
    zweit, k, _offen = heile(slug, neu_raw)
    if k:
        gruende.append(f"T4: nicht idempotent – ein zweiter Lauf fände {k} Stelle(n)")
    return gruende


# ---------------------------------------------------------------------------
#  DER HEILWEG EINES TEXTES
# ---------------------------------------------------------------------------
def heile(slug: str, rohtext: str) -> tuple[str, int, list[str]]:
    """Deterministische Heilung OHNE Tor. Rückgabe: (neu, Anzahl, offene Zeilen)."""
    teile = rohtext.split("---", 2)
    if len(teile) != 3:
        return rohtext, 0, []
    # Dieselbe Naht wie join_article/lesbarkeit_heiler: Präfix (z. B. BOM)
    # bleibt erhalten, `fm` und `body` sind die rohen Teilstücke.
    prefix, fm, body = teile[0], teile[1], teile[2]
    n = 0
    for regel in ("R11-JAHRESZAHL-SPLIT", "R13-DATUM-PUNKT"):
        body, k = _heile_muster(body, regel)
        n += k
    body, k, offen = _heile_marker(body)
    n += k
    return join_article(fm, body, prefix), n, offen


def heile_text(slug: str, rohtext: str) -> dict:
    """Ein Text durch den Heiler inklusive Tor. Nie eine halbe Heilung."""
    neu, n, offen = heile(slug, rohtext)
    ergebnis = {
        "slug": slug,
        "ok": False,
        "stufe": None,
        "vor": len([f for f in _ruinen(rohtext) if f[0] in HEILBAR]),
        "nach": None,
        "gruende": [],
        "offen": offen,
        "neu_raw": rohtext,
    }
    if offen:
        ergebnis["gruende"].append(
            "Marker-Zeile ohne eigenständigen Inhalt – redaktioneller Fall "
            f"({len(offen)}): {offen[0][:80]}")
        return ergebnis
    if not n and not ergebnis["vor"]:
        ergebnis.update(ok=True, stufe="nichts-zu-tun", nach=0)
        ergebnis["gruende"].append("keine heilbare Ruine gefunden")
        return ergebnis
    gruende = verifiziere(slug, rohtext, neu, verlust_erklärt=n)
    if gruende:
        ergebnis["gruende"] = gruende
        return ergebnis
    ergebnis.update(ok=True, stufe="deterministisch", neu_raw=neu,
                    nach=len([f for f in _ruinen(neu) if f[0] in HEILBAR]))
    ergebnis["gruende"].append(
        f"{n} Ruine(n) geheilt, Tor T1–T4 erfüllt")
    return ergebnis


# ---------------------------------------------------------------------------
#  WIRKUNGSPROBE – der Maschinenvertrag der Klasse
# ---------------------------------------------------------------------------
#  Fixture: je EINE reale Ruine pro heilbarer Klasse, eingebettet in einen
#  vollständigen Artikel. Die Probe schreibt in eine temporäre Datei-Kopie und
#  beweist damit Wirkung UND Tor, ohne Netz, ohne Kontingent, ohne Bestand.
def _fixture() -> str:
    return (
        "---\n"
        "title: \"Probe: Politur-Ruinen\"\n"
        "description: \"Fixture für die Wirkungsprobe\"\n"
        "draft: true\n"
        "---\n"
        "\n"
        "Der Vertrag startet am 2 Januar 2026 mit neuen Regeln.\n"
        "\n"
        "Im Jahr 20 26 steigen die Preise für viele Haushalte deutlich an.\n"
        "\n"
        "| Standard | Frequenz | Reichweite |\n"
        "|---|---|---|\n"
        "| Zigbee | 2,4 GHz | 10–20 m |\n"
        "SATZ: | Thread | 2,4 GHz | 10–20 m |\n"
        "\n"
        "Zum Schluss prüfst du deine Fixkosten in Ruhe und wechselst den Tarif.\n"
    )


def wirkungsprobe() -> tuple[bool, int | None, int | None, str]:
    """(ok, Ruinen vorher, Ruinen nachher, Meldung) – Exit 0 heißt Wirkung."""
    slug = "politur-ruine-fixture"
    fixture = _fixture()
    vor = len([f for f in _ruinen(fixture) if f[0] in HEILBAR])
    ergebnis = heile_text(slug, fixture)
    if not ergebnis["ok"]:
        return False, vor, None, ("Heilung verworfen: "
                                  + "; ".join(ergebnis["gruende"])[:180])
    nach = len([f for f in _ruinen(ergebnis["neu_raw"]) if f[0] in HEILBAR])
    if vor == 0 or nach != 0:
        return False, vor, nach, f"Wirkung nicht belegt ({vor} → {nach})"
    if "| Thread |" not in ergebnis["neu_raw"]:
        return False, vor, nach, "Tabellenzeile nach der Heilung zerstört"
    # Zweiter Lauf = Fixpunkt (Beleg der Idempotenz, Teil von T4).
    zweit = heile_text(slug, ergebnis["neu_raw"])
    if not zweit["ok"] or zweit["neu_raw"] != ergebnis["neu_raw"]:
        return False, vor, nach, "Heilung ist nicht idempotent"
    return True, vor, nach, (f"Wirkungsprobe: {vor} → {nach} heilbare Ruinen, "
                             f"Tor T1–T4 erfüllt, zweiter Lauf ohne Änderung")


# ---------------------------------------------------------------------------
#  KANDIDATEN + CLI
# ---------------------------------------------------------------------------
def _ist_entwurf(rohtext: str) -> bool:
    teile = rohtext.split("---", 2)
    return len(teile) >= 2 and re.search(r"(?m)^draft:\s*true\s*$", teile[1]) is not None


def _slug_von(pfad: str) -> str:
    return os.path.basename(os.path.dirname(os.path.abspath(pfad)))


def hole_neue() -> list[str]:
    """Artikel/Entwürfe des heutigen Datums (Live-Engine Phase 3)."""
    heute = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    treffer = []
    for name in sorted(os.listdir(POSTS_DIR)):
        if not name.startswith(heute):
            continue
        index = os.path.join(POSTS_DIR, name, "index.md")
        if os.path.isfile(index):
            treffer.append(index)
    return treffer


def _verarbeite(pfade: list[str], *, fix: bool, auch_live: bool,
                erlaube_live: bool, max_n: int | None = None):
    berichte, befund = [], 0
    if max_n:
        pfade = pfade[:max_n]
    for pfad in pfade:
        with open(pfad, encoding="utf-8") as fh:
            rohtext = fh.read()
        slug = _slug_von(pfad)
        if not _ist_entwurf(rohtext) and not auch_live and not erlaube_live:
            berichte.append({"slug": slug, "ok": True, "stufe": "übersprungen",
                             "befund": "kein Entwurf (draft: false) – Scope-Schutz",
                             "vor": 0, "nach": 0, "geschrieben": False})
            continue
        ergebnis = heile_text(slug, rohtext)
        geschrieben = False
        if ergebnis["ok"] and ergebnis["neu_raw"] != rohtext:
            if fix:
                with open(pfad, "w", encoding="utf-8") as fh:
                    fh.write(ergebnis["neu_raw"])
                geschrieben = True
        elif not ergebnis["ok"]:
            befund += 1
        ergebnis["geschrieben"] = geschrieben
        ergebnis["pfad"] = os.path.relpath(pfad, BLOG_DIR)
        berichte.append(ergebnis)
    return berichte, befund


def _menschen_text(berichte: list[dict], befund: int) -> str:
    zeilen = ["# POLITUR-RUINEN-HEILER (R11/R13/R14, Vorgang WF-D4E0 / #612)", ""]
    for b in berichte:
        vor = b.get("vor") if b.get("vor") is not None else "–"
        nach = b.get("nach") if b.get("nach") is not None else "–"
        marke = "🟢" if b.get("ok") else "🔴"
        zeilen.append(f"{marke} {b.get('slug')}: Ruinen {vor} → {nach} "
                      f"[{b.get('stufe') or 'offen'}]"
                      + (" (geschrieben)" if b.get("geschrieben") else ""))
        for g in (b.get("gruende") or [])[:4]:
            zeilen.append(f"     · {g}")
    zeilen += ["",
               "Heilbare Klassen (SSOT `sprachkern.POLITUR_RUINEN`): "
               + ", ".join(sorted(HEILBAR)),
               "Bewusst nur gemeldet: " + ", ".join(sorted(NICHT_HEILBAR)),
               f"Ungeheilt (fail-closed, nichts Halbfertiges geschrieben): {befund}"]
    return "\n".join(zeilen)


def run_selftest() -> int:
    fehler: list[str] = []
    # 1) SSOT-Abdeckung: jede Klasse der Musterliste ist eingeordnet.
    for regel, _rx, _d in sprachkern.POLITUR_RUINEN:
        if regel not in HEILBAR and regel not in NICHT_HEILBAR:
            fehler.append(f"{regel}: neue Klasse ohne Einordnung (fail-closed)")
    # 2) Wirkung je heilbarer Klasse einzeln
    faelle = {
        "R11-JAHRESZAHL-SPLIT": ("Im Jahr 20 26 steigen die Preise.", "2026"),
        "R13-DATUM-PUNKT": ("Der Vertrag startet am 2 Januar 2026.", "2. Januar"),
        "R14-MARKER-RUINE": ("| Zigbee | 2,4 GHz |\nSATZ: | Thread | 2,4 GHz |",
                             "| Thread | 2,4 GHz |"),
    }
    for regel, (alt, muss) in faelle.items():
        neu, k, _offen = heile("t", f"---\ntitle: \"x\"\n---\n\n{alt}\n")
        if not k or muss not in neu:
            fehler.append(f"{regel}: nicht geheilt („{alt[:40]}“)")
        elif any(f[0] == regel for f in _ruinen(neu)):
            fehler.append(f"{regel}: Ruine steht nach der Heilung noch im Text")
    # 3) Nicht heilbar → keine Änderung, aber Meldung
    r12 = "Du bist der 0 am deutschen Strommarkt."
    neu, k, _offen = heile("t", f"---\ntitle: \"x\"\n---\n\n{r12}\n")
    if k or r12 not in neu:
        fehler.append("R12: nicht heilbare Ruine wurde angefasst (Raten verboten)")
    # 4) Marker mit halbem Satz bleibt liegen (fail-closed)
    halb = "SATZ: und dann noch etwas"
    neu, k, offen = heile("t", f"---\ntitle: \"x\"\n---\n\n{halb}\n")
    if k or not offen or halb not in neu:
        fehler.append("R14: halbe Aussage wurde als Zeile geschrieben (kein Tor)")
    ergebnis = heile_text("t", f"---\ntitle: \"x\"\n---\n\n{halb}\n")
    if ergebnis["ok"]:
        fehler.append("R14: offene Zeile führt trotzdem zu ok=True")
    # 5) Tabellenzeile steht danach für sich, Linkzahl bleibt stabil
    fixture = _fixture()
    ok, vor, nach, _meldung = wirkungsprobe()
    if not ok:
        fehler.append(f"Wirkungsprobe rot ({vor} → {nach})")
    text_neu, _n, _o = heile("t", fixture)
    if _link_zahl(text_neu) != _link_zahl(fixture) or \
            _shortcode_zahl(text_neu) != _shortcode_zahl(fixture):
        fehler.append("Tor T3: Links/Shortcodes verändert")
    # 6) Frontmatter wird nie angefasst
    if text_neu.split("---", 2)[1] != fixture.split("---", 2)[1]:
        fehler.append("Tor T3: Frontmatter verändert")
    # 7) Idempotenz (Fixpunkt in EINEM Lauf)
    zweit, k, _offen = heile("t", text_neu)
    if k or zweit != text_neu:
        fehler.append("Idempotenz verletzt: zweiter Lauf ändert weiter")
    # 8) Ein Fund NACH der Heilung blockiert das Schreiben (Tor, nicht Werkzeug)
    slug = "t"
    gut = "---\ntitle: \"x\"\n---\n\nSATZ: | Thread | 2,4 GHz |\n"
    kaputt = "---\ntitle: \"x\"\n---\n\nSATZ: | Thread | 2,4 GHz |\n\nDu bist der 0 am Strommarkt.\n"
    # kaputt bleibt heilbar (R12 ist keine heilbare Klasse) – aber T1 darf
    # keine NEUE Ruine zulassen: der Eingriff selbst muss sie unberührt lassen.
    ergebnis = heile_text(slug, kaputt)
    if not ergebnis["ok"] or "der 0 am" not in ergebnis["neu_raw"]:
        fehler.append("R12 muss unangetastet bleiben, ohne die R14-Heilung zu blockieren")
    if any(f[0] == "R14-MARKER-RUINE" for f in _ruinen(ergebnis["neu_raw"])):
        fehler.append("R14 in gemischtem Fall nicht geheilt")
    if not heile_text(slug, gut)["ok"]:
        fehler.append("reiner R14-Fall gilt nicht als geheilt")
    if fehler:
        for f in fehler:
            print(f"🛑 {f}")
        print(f"🛑 Selbsttest politur_ruine_heiler: {len(fehler)} Befund(e)")
        return 1
    print("✅ Selbsttest politur_ruine_heiler: SSOT-Abdeckung, Wirkung je "
          "Klasse (R11/R13/R14), fail-closed bei R12 und halben Markern, "
          "Tor T3 (Frontmatter/Links/Shortcodes), Idempotenz und "
          "Wirkungsprobe grün.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Politur-Ruinen-Heiler R11/R13/R14 (fail-closed, Tor T1–T4)")
    ap.add_argument("--file", action="append", default=[],
                    help="einzelne Datei (mehrfach möglich)")
    ap.add_argument("--new-only", action="store_true",
                    help="Artikel/Entwürfe des heutigen Datums")
    ap.add_argument("--fix", action="store_true", help="schreiben (sonst Trockenlauf)")
    ap.add_argument("--auch-live", action="store_true",
                    help="auch Nicht-Entwürfe anfassen (Standard: nur draft:true)")
    ap.add_argument("--max", type=int, default=None, help="höchstens N Dateien")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--report", action="store_true",
                    help="Report nach POLITUR-RUINEN-HEILER-REPORT.md schreiben")
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
                              "meldung": meldung}, ensure_ascii=False))
        else:
            print(("✅ " if ok else "🛑 ") + meldung)
        return 0 if ok else 2

    pfade = list(args.file)
    if args.new_only:
        pfade += hole_neue()
    if not pfade:
        ap.error("Quelle fehlt: --file oder --new-only "
                 "(oder --selftest/--wirkungsprobe)")

    berichte, befund = _verarbeite(sorted(dict.fromkeys(pfade)), fix=args.fix,
                                   auch_live=args.auch_live,
                                   erlaube_live=args.new_only, max_n=args.max)
    if args.json:
        print(json.dumps({"befund": befund, "berichte": berichte},
                         ensure_ascii=False, indent=1, default=str))
    else:
        print(_menschen_text(berichte, befund))
    if args.report:
        ziel = os.path.join(BLOG_DIR, "POLITUR-RUINEN-HEILER-REPORT.md")
        with open(ziel, "w", encoding="utf-8") as fh:
            fh.write(f"<!-- erzeugt: {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M} UTC -->\n\n")
            fh.write(_menschen_text(berichte, befund) + "\n")
        print(f"📄 Report: {os.path.relpath(ziel, BLOG_DIR)}")
    return 1 if befund else 0


if __name__ == "__main__":
    sys.exit(main())
