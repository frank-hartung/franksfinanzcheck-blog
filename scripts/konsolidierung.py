#!/usr/bin/env python3
"""konsolidierung.py – die Regel F: wann eine Zusammenführung erlaubt ist.

WARUM DIESES MODUL EXISTIERT (26.10.2026)
------------------------------------------
Seit dem 19.10.2026 steht in `data/entscheidungen.yaml` (E-01): „Keine
Zusammenführung, keine Löschung und keine URL-Änderung, solange keine
Weiterleitungen existieren." Der Satz war richtig und hat elf Tage lang jede
Konsolidierung blockiert – denn er sagt nicht, WANN eine Weiterleitung
zulässig ist. Genau diese Lücke schließt dieses Modul: Es macht die
Entscheidung prüfbar, statt sie zu wiederholen.

Das Regelwerk `data/weiterleitungen.yaml` kennt bisher drei Fälle:
  A  Ordner umbenannt (Datumskorrektur, Dublette „(1)")
  B  gleiches Thema, manuell gewählter Live-Beitrag
  C  kein gleichwertiger Beitrag → Pillar-Seite
Neu ist:
  F  **Konsolidierung**: zwei Seiten mit identischer Suchabsicht werden zu
     einer. Das ist der einzige Fall, in dem eine Weiterleitung Inhalt
     vernichtet – deshalb verlangt F drei Belege, und zwar alle drei.

DIE DREI BELEGE (jeder maschinell geprüft, keiner verhandelbar)
---------------------------------------------------------------
1. SUCHABSICHT IDENTISCH
   Gemessen am Titel, nicht am Slug: Anteil gemeinsamer sinntragender Wörter
   am kürzeren Titel ≥ 0,50 UND gleiches Themenfeld (`pillar`). Füllwörter
   und Jahreszahlen zählen nicht – sonst wäre „…-schritt-fuer-schritt" eine
   Kannibalisierung (genau dieser Fehlalarm ist am 26.10. aufgefallen).

2. NACHFRAGE BELEGT
   Die Quell-URL braucht Impressionen > 0 in `data/gsc/top_seiten_28t.json`.
   Ohne Nachfrage ist eine Weiterleitung ein Denkmal für eine Seite, die
   niemand gesucht hat – dann ist ein 404 die ehrliche Antwort (Regel D).
   Dass Google die URL *kennt* (Detail-Liste), ist ausdrücklich NICHT genug:
   Bekanntheit ist keine Nachfrage.

3. KEINE LIVE-VERLINKUNG
   Kein redaktioneller Link im Bestand zeigt auf die Quell-URL. Solange einer
   existiert, würde die Weiterleitung einen kaputten Link verdecken statt ihn
   zu reparieren – erst den Link umhängen, dann konsolidieren.

WAS DAS MODUL NICHT TUT
-----------------------
Es löscht nichts, es schreibt nichts in `content/` und nichts in
`data/weiterleitungen.yaml`. `--vorschlag` sagt, ob eine Konsolidierung
zulässig WÄRE; die Entscheidung trifft ein Mensch, der Eintrag wird von Hand
aufgenommen. Dieselbe Grenze wie bei `gsc_abdeckung.py --entscheiden`.

AUFRUF
    python3 scripts/konsolidierung.py --pruefen          # alle F-Einträge prüfen
    python3 scripts/konsolidierung.py --vorschlag URL    # wäre F erlaubt?
    python3 scripts/konsolidierung.py --vorschlag URL --ziel ZIEL
    python3 scripts/konsolidierung.py --meldung          # Kurzfassung für Berichte
    python3 scripts/konsolidierung.py --selftest         # offline, ohne Netz

Exit: 0 = grün · 1 = Befund · 2 = Fehler
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Wie url_wache.py: der Repo-Wurzelpfad macht die Geschwistermodule
# importierbar, egal ob das Skript direkt oder als `scripts.konsolidierung`
# importiert wird.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
WEITERLEITUNGEN = ROOT / "data" / "weiterleitungen.yaml"
ENTFALLEN = ROOT / "data" / "url_entfallen.yaml"

REGELN_WEITERLEITUNG = ("A", "B", "C", "F")
REGELN_ENTFALLEN = ("D", "E")

# Schwellen sind bewusst benannt und nicht im Code versteckt: Wer sie ändert,
# ändert eine Entscheidung – und soll das hier tun, sichtbar.
SCHWELLE_ABSICHT = 0.5
MIN_IMPRESSIONEN = 1

_DATUM_PRAEFIX = re.compile(r"^\d{4}-\d{2}-\d{2}-")
_EINTRAG = re.compile(r"(\w+):\s*\"([^\"]*)\"")


# --------------------------------------------------------------------------
#  Lesen (ohne YAML-Abhängigkeit – wie gsc_abdeckung.py)
# --------------------------------------------------------------------------

def eintraege_lesen(pfad: Path | None = None) -> list[dict]:
    """Liest die Ein-Zeilen-Einträge aus `data/weiterleitungen.yaml`.

    Bewusst ohne PyYAML: Der Selbsttest dieses Moduls muss auch dort laufen,
    wo die Bibliothek fehlt (Hausregel der GSC-Werkzeuge). Die Datei hat je
    Eintrag genau eine Zeile in der Form `- {von: "…", nach: "…", …}`.
    """
    pfad = Path(pfad or WEITERLEITUNGEN)
    if not pfad.exists():
        return []
    aus = []
    for zeile in pfad.read_text(encoding="utf-8", errors="replace").splitlines():
        if not zeile.strip().startswith("- {"):
            continue
        eintrag = dict(_EINTRAG.findall(zeile))
        if eintrag.get("von"):
            aus.append(eintrag)
    return aus


def entfallene_lesen(pfad: Path | None = None) -> list[dict]:
    return eintraege_lesen(pfad or ENTFALLEN)


# --------------------------------------------------------------------------
#  Die drei Belege
# --------------------------------------------------------------------------

def _slug(pfad: str) -> str:
    return _DATUM_PRAEFIX.sub("", str(pfad).rstrip("/").split("/")[-1])


def _gsc():
    """`gsc_abdeckung` – als Paketmodul oder als Geschwistermodul importiert.

    Beide Wege liefern dieselbe Datei; der Unterschied ist nur, wie das Skript
    gestartet wurde (`python3 scripts/…` vs. `python3 -m unittest …`).
    """
    try:
        from scripts import gsc_abdeckung as g
    except ImportError:  # direkter Start: scripts/ liegt schon auf dem Pfad
        import gsc_abdeckung as g
    return g


def absicht(von: str, nach: str, root: Path = ROOT) -> dict:
    """Beleg 1: identische Suchabsicht – Titel-Überschneidung + Themenfeld."""
    g = _gsc()

    karte = g._titel_register(root)
    a, b = karte.get(von), karte.get(nach)
    if not a or not b:
        return {"belegt": False,
                "grund": ("Quelle oder Ziel hat keinen Titel im Bestand – "
                          "Suchabsicht nicht messbar."),
                "mass": 0.0, "gemeinsam": [], "pillar": None}
    mass = g.titel_ueberschneidung(a["titel"], b["titel"])
    gleiches_feld = bool(a.get("pillar")) and a.get("pillar") == b.get("pillar")
    belegt = mass["mass"] >= SCHWELLE_ABSICHT and gleiches_feld
    teile = []
    if not gleiches_feld:
        teile.append(f"verschiedene Themenfelder ({a.get('pillar')!r} ≠ {b.get('pillar')!r})")
    if mass["mass"] < SCHWELLE_ABSICHT:
        teile.append(f"Titel-Überschneidung {mass['mass']:.2f} < {SCHWELLE_ABSICHT:.2f}")
    return {"belegt": belegt,
            "grund": ("Titel-Überschneidung "
                      f"{mass['mass']:.2f} ({', '.join(mass['gemeinsam']) or 'keine'}), "
                      f"Themenfeld {a.get('pillar')!r}"
                      + (" – " + "; ".join(teile) if teile else "")),
            "mass": mass["mass"], "gemeinsam": mass["gemeinsam"],
            "pillar": a.get("pillar")}


def _seitenpfad(wert: str) -> str:
    """Alles, was eine URL zur Seite macht: Schema, Host, Query und Anker weg."""
    pfad = re.sub(r"^https?://[^/]+", "", str(wert or "").strip())
    pfad = pfad.split("?")[0].split("#")[0]
    return pfad if pfad.startswith("/") else "/" + pfad


def nachfrage(url: str, root: Path = ROOT) -> dict:
    """Beleg 2: belegte Nachfrage – Impressionen, nicht bloße Bekanntheit."""
    pfad = Path(root) / "data" / "gsc" / "top_seiten_28t.json"
    if not pfad.exists():
        return {"belegt": False, "impressionen": 0, "position": None,
                "quelle": "keine Top-Seiten-Daten",
                "grund": "Keine Leistungsdaten (`data/gsc/top_seiten_28t.json`) – "
                         "Nachfrage nicht belegbar."}
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"belegt": False, "impressionen": 0, "position": None,
                "quelle": "unlesbar", "grund": "Leistungsdaten nicht lesbar."}
    treffer = None
    for eintrag in daten if isinstance(daten, list) else []:
        if not isinstance(eintrag, dict):
            continue
        # Die Search Console exportiert die volle Adresse unter `seite`, die
        # eigene Aufbereitung schreibt `url`. Beides muss zählen – sonst wäre
        # jede Nachfrage „nicht belegt“ und F würde aus dem falschen Grund
        # blockieren.
        wert = eintrag.get("url") or eintrag.get("seite") or ""
        if _seitenpfad(wert).rstrip("/") == _seitenpfad(url).rstrip("/"):
            treffer = eintrag
            break
    if not treffer:
        return {"belegt": False, "impressionen": 0, "position": None,
                "quelle": "top_seiten_28t.json",
                "grund": "URL kommt in den Top-Seiten der letzten 28 Tage nicht vor – "
                         "keine belegte Nachfrage."}
    impressionen = int(treffer.get("impressions") or treffer.get("impressionen") or 0)
    position = treffer.get("position")
    return {"belegt": impressionen >= MIN_IMPRESSIONEN,
            "impressionen": impressionen, "position": position,
            "quelle": "top_seiten_28t.json",
            "grund": (f"{impressionen} Impression(en) in 28 Tagen"
                      + (f", Position {position}" if position else "")
                      + ("" if impressionen >= MIN_IMPRESSIONEN else
                         " – unter der Schwelle, keine Nachfrage belegt."))}


def verlinkung(url: str, root: Path = ROOT) -> dict:
    """Beleg 3: kein redaktioneller Link zeigt auf die Quell-URL."""
    g = _gsc()

    karte = g.redaktionelle_links(root)
    seite = (karte.get("seiten") or {}).get(url) or {"ein": 0, "quellen": []}
    return {"belegt": not seite.get("ein"),
            "ein": seite.get("ein") or 0,
            "quellen": sorted(seite.get("quellen") or [])[:10],
            "grund": (f"{seite.get('ein') or 0} redaktionelle(r) Link(s) zeigen auf die URL"
                      if seite.get("ein") else
                      "Kein redaktioneller Link zeigt auf die URL.")}


def urteil(von: str, nach: str, regel: str = "F", root: Path = ROOT) -> dict:
    """Alle drei Belege plus Urteil. `erlaubt` ist die UND-Verknüpfung."""
    pruefungen = {
        "suchabsicht": absicht(von, nach, root),
        "nachfrage": nachfrage(von, root),
        "verlinkung": verlinkung(von, root),
    }
    fehlend = [name for name, wert in pruefungen.items() if not wert["belegt"]]
    erlaubt = not fehlend
    return {
        "von": von, "nach": nach, "regel": regel,
        "erlaubt": erlaubt, "fehlend": fehlend, "pruefungen": pruefungen,
        "empfehlung": empfehlung(von, nach, fehlend),
    }


def empfehlung(von: str, nach: str, fehlend: list[str]) -> str:
    """Was der nächste Schritt ist – je nachdem, welcher Beleg fehlt."""
    if not fehlend:
        return ("Konsolidierung zulässig (Regel F): Artikel zurückziehen, Eintrag "
                f"{{von: \"{von}\", nach: \"{nach}\", regel: \"F\", grund: \"…\"}} "
                "aufnehmen, dann `weiterleitungen.py --check --build`.")
    if "suchabsicht" in fehlend:
        return ("Nicht konsolidieren: Die Suchabsicht ist nicht identisch. Zwei Seiten "
                "mit verschiedenen Titeln und Themenfeldern sind zwei Rollen – "
                "Rollen trennen (R2) statt zusammenführen (R1).")
    if "nachfrage" in fehlend:
        return ("Nicht konsolidieren, sondern bewusst 404: Ohne belegte Nachfrage ist "
                "eine Weiterleitung ein Denkmal für eine Seite, die niemand gesucht hat "
                "(Regel D in data/url_entfallen.yaml).")
    return ("Erst den Link umhängen: Solange ein redaktioneller Link auf die URL zeigt, "
            "würde die Weiterleitung einen kaputten Link verdecken. Danach erneut prüfen.")


def pruefe(alle: list[dict], root: Path = ROOT) -> list[dict]:
    """Prüft jeden Eintrag mit Regel F. Rückgabe: Befunde (leer = grün)."""
    befunde = []
    for eintrag in alle:
        if eintrag.get("regel") != "F":
            continue
        geprueft = urteil(eintrag["von"], eintrag.get("nach", ""), "F", root)
        if geprueft["erlaubt"]:
            continue
        befunde.append({
            "regel": "F1", "schwere": "hart", "url": eintrag["von"],
            "text": ("Konsolidierung ohne Beleg: "
                     + "; ".join(geprueft["pruefungen"][name]["grund"]
                                 for name in geprueft["fehlend"])
                     + ". " + geprueft["empfehlung"]),
        })
    return befunde


def bilanz(alle: list[dict]) -> dict:
    """Wie viele Einträge je Regel – der Überblick, den ein Bericht braucht."""
    zaehler: dict[str, int] = {}
    for eintrag in alle:
        regel = eintrag.get("regel") or "?"
        zaehler[regel] = zaehler.get(regel, 0) + 1
    return {"gesamt": len(alle), "nach_regel": dict(sorted(zaehler.items())),
            "konsolidierungen": zaehler.get("F", 0)}


def bester_kandidat(von: str, root: Path = ROOT) -> str | None:
    """Live-Beitrag im selben Themenfeld mit der höchsten Titel-Überschneidung."""
    g = _gsc()

    karte = g._titel_register(root)
    eigen = karte.get(von)
    if not eigen:
        return None
    bestes, ziel = 0.0, None
    for url, daten in karte.items():
        if url == von or daten.get("draft"):
            continue
        if eigen.get("pillar") and daten.get("pillar") != eigen.get("pillar"):
            continue
        mass = g.titel_ueberschneidung(eigen["titel"], daten["titel"])["mass"]
        if mass > bestes:
            bestes, ziel = mass, url
    return ziel


# --------------------------------------------------------------------------
#  Rollenpaare (Dauerheilung 30.10.2026)
#
#  Am 26.10.2026 wurde für zwei Seiten entschieden: „Rollen trennen, nicht
#  zusammenführen“ (Regel F verweigert die Zusammenführung, weil die
#  Suchabsicht nicht identisch ist). Diese Entscheidung war richtig – aber
#  sie war unbewacht. Am 30.10.2026 lief der Test `test_der_zwilling_hat_
#  keine_nachfrage_aus_seite_eins` rot, weil eine der beiden Seiten von 4 auf
#  14 Impressionen gewachsen war. Der Test sagte damit das Richtige
#  („Konsolidierung prüfen“), verlangte aber eine Zahl statt einer Prüfung –
#  und wer ihn reparieren will, senkt die Schwelle. Genau das darf nicht
#  passieren.
#
#  Deshalb steht die Rollentrennung ab jetzt auf drei Beinen, die man messen
#  und verlieren kann:
#    1. STRUKTUR    Die Seiten sind verschieden – nicht nur im Titel, sondern
#                   in den Zwischenüberschriften und im Satzbestand.
#    2. ENTSCHEIDUNG Sie ist dokumentiert (Feld `paar` im Entscheidungs-
#                   Register), hat Eigentümer und Frist, und die Frist ist
#                   nicht überfällig.
#    3. ROLLENLINK  Beide Seiten verlinken sich gegenseitig mit Rollenanker.
#  Und die Nachfrage-Regel: Ab SCHWELLE_NACHFRAGE_ROLLE Impressionen muss die
#  Entscheidung die Nachfrage ausdrücklich beantworten (`erwartung:
#  impressionen`) – sonst ist „Rollen trennen“ eine Behauptung gegen die
#  Messung.
#
#  Keine dieser Regeln lockert Regel F. Sie macht die Alternative prüfbar.
# --------------------------------------------------------------------------
SCHWELLE_NACHFRAGE_ROLLE = 10      # ab hier verlangt die Nachfrage eine Antwort
SCHWELLE_STRUKTUR = 0.05           # wörtliche Sätze (ohne Boilerplate)
_BOILERPLATE = re.compile(r"Affiliate|Werbung|Provision", re.I)
_KOMMENTAR = re.compile(r"<!--.*?-->", re.S)


def _verzeichnis(url: str) -> str:
    """Letztes Pfadstück MIT Datumspräfix – so heißt der Ordner im Bestand."""
    return _seitenpfad(url).rstrip("/").split("/")[-1]


def beitragspfad(url: str, root: Path = ROOT) -> Path | None:
    """URL → index.md. `None`, wenn die Seite fehlt oder nicht eindeutig ist.

    Gesucht wird über den Verzeichnisnamen (`2026-10-12-slug`) und – für alte
    URLs ohne Datumspräfix – über den Slug. `_slug()` allein greift zu kurz:
    Es schneidet das Datum ab, der Ordner trägt es aber.
    """
    verz = _verzeichnis(url)
    if not verz:
        return None
    basis = Path(root) / "content" / "posts"
    treffer = sorted(basis.glob(verz + "/index.md")) or \
        sorted(basis.glob(verz + "*/index.md"))
    return treffer[0] if len(treffer) == 1 else None


def _koerper(text: str) -> str:
    return text.split("\n---\n", 1)[1] if "\n---\n" in text else text


def _norm(text: str) -> str:
    text = re.sub(r"[*_`#>\[\]]|\([^)]*\)", " ", text)
    text = text.lower().replace("„", '"').replace("“", '"')
    return re.sub(r"\s+", " ", re.sub(r"[^a-zäöüß0-9 ]+", " ", text)).strip()


def _lies(pfad: Path) -> str:
    return Path(pfad).read_text(encoding="utf-8", errors="replace")


def ueberschriften(pfad: Path) -> list[str]:
    """Die inhaltlichen Zwischenüberschriften einer Seite (normalisiert)."""
    return [_norm(h) for h in
            re.findall(r"^##+ (.+)$", _koerper(_lies(pfad)), re.M)]


def saetze(pfad: Path) -> list[str]:
    """Inhaltliche Sätze – ohne Affiliate-Boilerplate und Kleinkram."""
    text = _KOMMENTAR.sub(" ", _koerper(_lies(pfad)))
    aus = []
    for roh in re.split(r"(?<=[.!?])\s+", text):
        if _BOILERPLATE.search(roh):
            continue                      # Hinweiszeile, kein Inhalt
        normal = _norm(roh)
        if len(normal.split()) >= 6:
            aus.append(normal)
    return aus


def struktur(von: str, nach: str, root: Path = ROOT) -> dict:
    """Wie ähnlich sind zwei Seiten wirklich? Überschriften + wörtliche Sätze."""
    pa, pb = beitragspfad(von, root), beitragspfad(nach, root)
    if not pa or not pb:
        return {"messbar": False, "gemeinsam": [], "ueberschneidung": None,
                "grund": ("Seite nicht eindeutig im Bestand – Struktur nicht "
                          "messbar (Tippfehler in der URL?)")}
    ua, ub = ueberschriften(pa), ueberschriften(pb)
    sa, sb = saetze(pa), saetze(pb)
    gemeinsam = sorted(set(ua) & set(ub))
    fremd = set(sb)
    gleich = [s for s in sa if s in fremd]
    return {"messbar": True, "gemeinsam": gemeinsam,
            "ueberschneidung": len(gleich) / max(1, len(sa)),
            "saetze": (len(sa), len(sb)), "gleiche_saetze": gleich}


def _verlinkt(von: str, nach: str, root: Path = ROOT) -> bool:
    pfad = beitragspfad(von, root)
    if not pfad:
        return False
    return bool(re.search(r"\]\([^)]*" + re.escape(_verzeichnis(nach)) + r"/?\)",
                          _lies(pfad)))


def rollenpaare(root: Path = ROOT, register: dict | None = None) -> list[dict]:
    """Dokumentierte Rollenpaare – aus dem Entscheidungs-Register (`paar`)."""
    reg = register if register is not None else _gsc().entscheidungen()
    paare: dict[tuple[str, str], dict] = {}
    for url, eintrag in reg.items():
        partner = (eintrag or {}).get("paar")
        if not partner:
            continue
        schluessel = tuple(sorted((_seitenpfad(url).rstrip("/"),
                                   _seitenpfad(partner).rstrip("/"))))
        if schluessel in paare:
            continue          # beide Zeilen zeigen auf dasselbe Paar
        paare[schluessel] = {"a": url, "b": partner}
    return list(paare.values())


def rollenpaar_pruefen(a: str, b: str, root: Path = ROOT,
                      register: dict | None = None,
                      heute: dt.date | None = None) -> list[dict]:
    """Prüft EIN Rollenpaar gegen Struktur, Entscheidung, Frist, Link, Nachfrage."""
    heute = heute or dt.date.today()
    reg = register if register is not None else _gsc().entscheidungen()
    befunde: list[dict] = []

    def befund(text: str, schwere: str = "hart", url: str = a) -> None:
        befunde.append({"regel": "R2", "schwere": schwere, "url": url,
                        "paar": [a, b], "text": text})

    st = struktur(a, b, root)
    if not st["messbar"]:
        befund(f"Struktur nicht messbar: {st['grund']}", "weich")
    elif st["gemeinsam"]:
        befund("Struktur gleich: gemeinsame Zwischenüberschriften "
               f"{', '.join(repr(x) for x in st['gemeinsam'][:3])} – "
               "Regel F neu prüfen, statt Rollen zu behaupten.")
    elif st["ueberschneidung"] is not None and st["ueberschneidung"] > SCHWELLE_STRUKTUR:
        befund(f"Struktur gleich: {st['ueberschneidung']:.1%} der Sätze stehen "
               f"wörtlich in beiden Seiten (Schwelle {SCHWELLE_STRUKTUR:.0%}) – "
               "Regel F neu prüfen.")

    for url in (a, b):
        eintrag = reg.get(url) or {}
        if not eintrag:
            befund("Keine dokumentierte Rollen-Entscheidung – die "
                   "Rollentrennung ist nicht belegt.", url=url)
            continue
        frist = (eintrag.get("wiedervorlage") or "")[:10]
        try:
            tage = (dt.date.fromisoformat(frist) - heute).days if frist else None
        except ValueError:
            tage = None
        if tage is None:
            befund("Wiedervorlage fehlt oder ist kein Datum – eine "
                   "Entscheidung ohne Frist ist nicht prüfbar.", url=url)
        elif tage < 0:
            befund(f"Wiedervorlage {frist} ist seit {-tage} Tagen "
                   "überfällig – Entscheidung neu treffen.", url=url)
        if not (eintrag.get("eigentuemer") or "").strip():
            befund("kein Eigentümer eingetragen – ohne Namen prüft "
                   "niemand die Frist.", url=url)
        nach = nachfrage(url, root)
        if (nach["impressionen"] >= SCHWELLE_NACHFRAGE_ROLLE
                and (eintrag.get("erwartung") or "") != "impressionen"):
            befund(f"{nach['impressionen']} Impressionen "
                   f"≥ {SCHWELLE_NACHFRAGE_ROLLE}, aber die Entscheidung trägt "
                   f"die Erwartung {eintrag.get('erwartung')!r} – die Nachfrage "
                   "ist nicht beantwortet (erwartung: impressionen).", url=url)

    for url, partner in ((a, b), (b, a)):
        if not _verlinkt(url, partner, root):
            befund(f"verlinkt {partner} nicht – Rollentrennung ohne "
                   "Rollenlink ist eine Behauptung (R2).", url=url)

    return befunde


def rollenpaare_pruefen(root: Path = ROOT, register: dict | None = None,
                        heute: dt.date | None = None) -> list[dict]:
    """Alle dokumentierten Rollenpaare prüfen. Leer = grün."""
    reg = register if register is not None else _gsc().entscheidungen()
    befunde: list[dict] = []
    for paar in rollenpaare(root, reg):
        befunde.extend(rollenpaar_pruefen(paar["a"], paar["b"], root, reg, heute))
    return befunde


# --------------------------------------------------------------------------
#  Selbsttest
# --------------------------------------------------------------------------

def selbsttest() -> int:
    """Belege werden nicht geglaubt, sondern gerechnet – mit echten Fixtures."""
    ok, fehler = 0, []

    def pruefe_(name, bedingung):
        nonlocal ok
        if bedingung:
            ok += 1
        else:
            fehler.append(name)

    g = _gsc()

    tmp = Path(__import__("tempfile").mkdtemp())
    try:
        # Zwei Seiten mit identischer Absicht, gleiches Themenfeld.
        cdir = tmp / "content" / "posts"
        for slug, titel, pillar in (
            ("2026-10-01-haushaltsbuch-fuehren-app-excel", "Haushaltsbuch führen: App oder Excel", "konto-karten"),
            ("2026-10-02-haushaltsbuch-fuehren-mit-excel", "Haushaltsbuch führen mit Excel", "konto-karten"),
            ("2026-10-03-girokonto-ohne-gebuehren", "Girokonto ohne Gebühren: der Vergleich", "konto-karten"),
            ("2026-10-04-strom-sparen-im-haushalt", "Strom sparen im Haushalt", "strom-sparen"),
        ):
            (cdir / slug).mkdir(parents=True)
            (cdir / slug / "index.md").write_text(
                f'---\ntitle: "{titel}"\npillar: "{pillar}"\ndraft: false\n---\n\nText\n',
                encoding="utf-8")
        # Ein Link von einer anderen Seite auf die Quelle (Beleg 3 verletzt).
        (cdir / "2026-10-03-girokonto-ohne-gebuehren" / "index.md").write_text(
            '---\ntitle: "Girokonto ohne Gebühren: der Vergleich"\n'
            'pillar: "konto-karten"\ndraft: false\n---\n\n'
            'Siehe [Haushaltsbuch](../../posts/2026-10-02-haushaltsbuch-fuehren-mit-excel/).\n',
            encoding="utf-8")

        a = "/posts/2026-10-02-haushaltsbuch-fuehren-mit-excel/"
        b = "/posts/2026-10-01-haushaltsbuch-fuehren-app-excel/"
        pruefe_("F-Absicht erkannt", absicht(a, b, tmp)["belegt"])
        pruefe_("F-Absicht verneint bei anderem Thema",
                not absicht(a, "/posts/2026-10-04-strom-sparen-im-haushalt/", tmp)["belegt"])

        # Nachfrage: Datei fehlt → nicht belegt (keine erfundene Zahl).
        pruefe_("F-Nachfrage ohne Daten nicht belegt", not nachfrage(a, tmp)["belegt"])
        (tmp / "data" / "gsc").mkdir(parents=True)
        (tmp / "data" / "gsc" / "top_seiten_28t.json").write_text(json.dumps(
            [{"url": a, "impressions": 4, "position": 12.0}]), encoding="utf-8")
        pruefe_("F-Nachfrage mit Impressionen belegt", nachfrage(a, tmp)["belegt"])
        # Der echte GSC-Export nennt das Feld `seite` und schreibt die volle
        # Adresse. Beides muss als dieselbe Seite erkannt werden.
        (tmp / "data" / "gsc" / "top_seiten_28t.json").write_text(json.dumps(
            [{"seite": "https://franksfinanzcheck.de" + a, "impressions": 5}]), encoding="utf-8")
        pruefe_("F-Nachfrage erkennt die volle GSC-Adresse", nachfrage(a, tmp)["belegt"])
        (tmp / "data" / "gsc" / "top_seiten_28t.json").write_text(json.dumps(
            [{"url": a, "impressions": 4, "position": 12.0}]), encoding="utf-8")
        pruefe_("F-Nachfrage bei 0 Impressionen nicht belegt",
                not nachfrage(b, tmp)["belegt"])

        pruefe_("F-Verlinkung erkennt Inlink", not verlinkung(a, tmp)["belegt"]
                and verlinkung(a, tmp)["ein"] == 1)
        pruefe_("F-Verlinkung grün ohne Inlink", verlinkung(b, tmp)["belegt"])

        # Urteil: alle drei zusammen.
        # `a` hat Nachfrage, aber einen Inlink; `b` hat keinen Inlink, aber
        # keine Nachfrage. Jeder der beiden Belege muss einzeln greifen.
        u_a = urteil(a, b, "F", tmp)
        u_b = urteil(b, a, "F", tmp)
        pruefe_("F-Urteil verweigert bei fehlender Nachfrage",
                not u_b["erlaubt"] and u_b["fehlend"] == ["nachfrage"])
        pruefe_("F-Urteil verweigert bei vorhandenem Inlink",
                not u_a["erlaubt"] and u_a["fehlend"] == ["verlinkung"])
        (tmp / "data" / "gsc" / "top_seiten_28t.json").write_text(json.dumps(
            [{"url": a, "impressions": 4, "position": 12.0},
             {"url": b, "impressions": 2, "position": 8.0}]), encoding="utf-8")
        # Inlink bleibt: also weiterhin nicht erlaubt.
        pruefe_("F-Urteil bleibt rot bei Inlink", not urteil(a, b, "F", tmp)["erlaubt"])
        u2 = urteil(b, a, "F", tmp)
        pruefe_("F-Urteil grün, wenn alle Belege da sind", u2["erlaubt"])

        pruefe_("F-Empfehlung nennt Regel D ohne Nachfrage",
                "Regel D" in empfehlung(b, a, ["nachfrage"]))
        pruefe_("F-Empfehlung nennt Rollentrennung bei anderer Absicht",
                "Rollen trennen" in empfehlung(b, a, ["suchabsicht"]))
        pruefe_("F-Empfehlung nennt Link umhängen",
                "Link umhängen" in empfehlung(b, a, ["verlinkung"]))

        # Die Wache schlägt zu – und nur bei F.
        kaputt = [{"von": a, "nach": b, "regel": "F", "grund": "Testfall Konsolidierung"}]
        befund = pruefe(kaputt, tmp)
        pruefe_("F-Wache meldet fehlenden Beleg",
                len(befund) == 1 and befund[0]["regel"] == "F1"
                and befund[0]["schwere"] == "hart")
        sauber = [{"von": b, "nach": a, "regel": "F", "grund": "Testfall Konsolidierung"}]
        pruefe_("F-Wache schweigt bei belegtem Fall", pruefe(sauber, tmp) == [])
        pruefe_("F-Wache prüft A/B/C nicht",
                pruefe([{"von": a, "nach": b, "regel": "B", "grund": "Altbestand"}], tmp) == [])

        pruefe_("F-Bilanz zählt je Regel",
                bilanz(sauber + [{"von": "/x/", "regel": "A"}])["nach_regel"] == {"A": 1, "F": 1})

        # Bestand: Die echte Datei darf nur gültige Regeln enthalten.
        echt = eintraege_lesen()
        pruefe_("F-Bestand liest alle Einträge", len(echt) >= 115)
        pruefe_("F-Bestand kennt nur A, B, C, F",
                all(e.get("regel") in REGELN_WEITERLEITUNG for e in echt))
        pruefe_("F-Bestand hat noch keine Konsolidierung",
                bilanz(echt)["konsolidierungen"] == 0)
        pruefe_("F-Bestand: jede Konsolidierung wäre belegt",
                pruefe(echt) == [])

        # --- Rollenpaare (Dauerheilung 30.10.2026) -------------------------
        # Zwei Seiten, zwei Rollen: verschiedene Überschriften, kein
        # gemeinsamer Satz, gegenseitiger Rollenlink, dokumentierte
        # Entscheidung mit Frist. Jede einzelne Zusicherung wird hier
        # verletzt – damit die Wache nicht nur „grün“ kann.
        rdir = tmp / "content" / "posts"
        (rdir / "2026-10-12-jahresplan").mkdir(parents=True, exist_ok=True)
        (rdir / "2026-10-12-jahresplan" / "index.md").write_text(
            '---\ntitle: "Jahresplan"\n---\n\n'
            "Am Anfang sammelst du alle Abbuchungen eines Jahres.\n"
            "Danach ordnest du sie nach Kategorien und Fristen.\n"
            "## Alle Zahlungen sammeln\n\nText\n## Fristen sichern\n\nText\n",
            encoding="utf-8")
        (rdir / "2026-10-12-kontrollpfad").mkdir(parents=True, exist_ok=True)
        (rdir / "2026-10-12-kontrollpfad" / "index.md").write_text(
            '---\ntitle: "Kontrollpfad"\n---\n\n'
            "Der Prüfpfad geht an einem Nachmittag durch alle Fixkosten.\n"
            "Am Ende steht die Entscheidung über jeden Vertrag.\n"
            "## Preistreiber finden\n\nText\n## Konditionen rechnen\n\nText\n",
            encoding="utf-8")
        r1 = "/posts/2026-10-12-jahresplan/"
        r2 = "/posts/2026-10-12-kontrollpfad/"
        st = struktur(r1, r2, tmp)
        pruefe_("R2-Struktur messbar", st["messbar"] and st["gemeinsam"] == []
                and st["ueberschneidung"] == 0.0)
        pruefe_("R2-Rollenlink fehlt wird gemeldet",
                any("verlinkt" in b["text"] for b in
                    rollenpaar_pruefen(r1, r2, tmp, register={}, heute=dt.date(2026, 10, 30))))
        # Entscheidungen eintragen (Register als Dict, wie `entscheidungen()` es liefert).
        reg = {
            r1: {"url": r1, "paar": r2, "wiedervorlage": "2026-11-13",
                 "eigentuemer": "redaktion", "erwartung": "impressionen"},
            r2: {"url": r2, "paar": r1, "wiedervorlage": "2026-11-13",
                 "eigentuemer": "redaktion", "erwartung": "impressionen"},
        }
        # Ohne Nachfrage-Daten ist die Nachfrage 0 → keine Nachfrage-Regel.
        gruen = rollenpaar_pruefen(r1, r2, tmp, register=reg, heute=dt.date(2026, 10, 30))
        pruefe_("R2-Grün nur ohne Rollenlink-Befund",
                all("verlinkt" in b["text"] for b in gruen) and len(gruen) == 2)
        # Rollenlink setzen → grün.
        # Wichtig: die Rollenlinks tragen VERSCHIEDENE Sätze. Zwei identische
        # Sätze (nur mit anderem Ziel) wären strukturell eine Dublette – der
        # Wächter würde zu Recht meckern, und die Fixture wäre selbst der Fehler.
        for seite, ziel, satz in (
                ("2026-10-12-jahresplan", r2,
                 "Wenn du die Fixkosten zuerst durchgehen willst, nimm den Kontrollpfad."),
                ("2026-10-12-kontrollpfad", r1,
                 "Wenn du das Ganze einmal im Jahr neu aufsetzen willst, nimm den Jahresplan.")):
            p = rdir / seite / "index.md"
            p.write_text(p.read_text(encoding="utf-8").replace(
                "## ", f"{satz} [Rolle](../../posts/{_verzeichnis(ziel)}/).\n\n## ", 1),
                encoding="utf-8")
        pruefe_("R2 fertig verdrahtet ist grün",
                rollenpaar_pruefen(r1, r2, tmp, register=reg,
                                   heute=dt.date(2026, 10, 30)) == [])
        # Frist überfällig → rot.
        alt = {k: dict(v, wiedervorlage="2026-10-01") for k, v in reg.items()}
        pruefe_("R2 überfällige Frist ist rot",
                any("überfällig" in b["text"] for b in
                    rollenpaar_pruefen(r1, r2, tmp, register=alt,
                                       heute=dt.date(2026, 10, 30))))
        # Nachfrage über der Schwelle ohne Nachfrage-Erwartung → rot.
        (tmp / "data" / "gsc" / "top_seiten_28t.json").write_text(json.dumps(
            [{"url": r1, "impressions": SCHWELLE_NACHFRAGE_ROLLE, "position": 40.9}]),
            encoding="utf-8")
        ohne = {k: dict(v, erwartung="indexiert") for k, v in reg.items()}
        pruefe_("R2 Nachfrage ohne Antwort ist rot",
                any("Impressionen" in b["text"] for b in
                    rollenpaar_pruefen(r1, r2, tmp, register=ohne,
                                       heute=dt.date(2026, 10, 30))))
        pruefe_("R2 Nachfrage mit Antwort bleibt grün",
                rollenpaar_pruefen(r1, r2, tmp, register=reg,
                                   heute=dt.date(2026, 10, 30)) == [])
        # Struktur kippt: gemeinsame Überschrift → F neu prüfen.
        p = rdir / "2026-10-12-kontrollpfad" / "index.md"
        p.write_text(p.read_text(encoding="utf-8").replace(
            "## Preistreiber finden", "## Fristen sichern"), encoding="utf-8")
        pruefe_("R2 gleiche Struktur ist rot",
                any("Struktur gleich" in b["text"] for b in
                    rollenpaar_pruefen(r1, r2, tmp, register=reg,
                                       heute=dt.date(2026, 10, 30))))
        # Paare kommen aus dem Register, nicht aus einer zweiten Liste.
        pruefe_("R2 Paare kommen aus dem Register",
                rollenpaare(tmp, reg) == [{"a": r1, "b": r2}])
        # Nur eine Seite dokumentiert: Der Link steht da, die Entscheidung
        # fehlt auf der Gegenseite – die halbe Zusage zählt nicht.
        halb = {r1: dict(reg[r1])}
        pruefe_("R2 einseitige Dokumentation ist rot",
                rollenpaare(tmp, halb) == [{"a": r1, "b": r2}]
                and any("Keine dokumentierte Rollen-Entscheidung" in b["text"]
                        for b in rollenpaar_pruefen(r1, r2, tmp, register=halb,
                                                    heute=dt.date(2026, 10, 30))))
        # Ohne `paar` gibt es keine Paare – und keinen Anspruch, der geprüft
        # wäre. Die CLI sagt das ausdrücklich, statt „belegt: 0 Paare“ zu
        # behaupten (genau das war am 30.10.2026 der stille Zustand).
        pruefe_("R2 ohne Register-Feld kein Paar", rollenpaare(tmp, {}) == [])
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    if fehler:
        print(f"🛑 KONSOLIDIERUNG SELBSTTEST: {len(fehler)} von {ok + len(fehler)} rot")
        for name in fehler:
            print(f"   ✗ {name}")
        return 2
    print(f"✅ KONSOLIDIERUNG SELBSTTEST: {ok} Fälle grün")
    return 0


# --------------------------------------------------------------------------
#  CLI
# --------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Regel F: Wann ist eine Konsolidierung (Weiterleitung) zulässig?")
    p.add_argument("--pruefen", action="store_true",
                   help="alle Einträge mit Regel F gegen die drei Belege prüfen")
    p.add_argument("--vorschlag", metavar="URL",
                   help="wäre eine Konsolidierung dieser URL zulässig?")
    p.add_argument("--ziel", metavar="URL", help="Ziel-URL (sonst bester Kandidat)")
    p.add_argument("--meldung", action="store_true", help="Kurzfassung ausgeben")
    p.add_argument("--rollenpaare", action="store_true",
                   help="dokumentierte Rollenpaare prüfen (Struktur, Entscheidung, "
                        "Frist, Rollenlink, Nachfrage) – Exit 1 bei Befund")
    p.add_argument("--json", action="store_true", help="Ergebnis als JSON")
    p.add_argument("--selftest", action="store_true", help="offline, ohne Netz")
    args = p.parse_args(argv)

    if args.selftest:
        return selbsttest()

    if args.rollenpaare:
        paare = rollenpaare()
        befunde = rollenpaare_pruefen()
        if args.json:
            print(json.dumps({"paare": paare, "befunde": befunde},
                             ensure_ascii=False, indent=1))
            return 1 if befunde else 0
        for paar in paare:
            st = struktur(paar["a"], paar["b"])
            schnitt = ("—" if st["ueberschneidung"] is None
                       else f"{st['ueberschneidung']:.1%}")
            print(f"Rollenpaar: {paar['a']}")
            print(f"            ↔ {paar['b']}")
            print(f"  Struktur: {len(st['gemeinsam'])} gemeinsame "
                  f"Zwischenüberschrift(en), {schnitt} wörtliche Sätze")
        for befund in befunde:
            print(f"🛑 {befund['regel']} {befund['url']}: {befund['text']}")
        if not paare:
            print("ℹ️ Kein Rollenpaar im Register (Feld `paar`) – hier ist "
                  "nichts behauptet, also auch nichts belegt.")
        elif not befunde:
            print(f"✅ Rollentrennung belegt: {len(paare)} Paar(e), "
                  "Entscheidung, Frist, Struktur und Rollenlink stehen.")
        return 1 if befunde else 0

    if args.vorschlag:
        von = args.vorschlag
        ziel = args.ziel or bester_kandidat(von)
        if not ziel:
            print(f"🛑 Kein Kandidat im selben Themenfeld für {von} – "
                  "ohne Ziel keine Konsolidierung.", file=sys.stderr)
            return 1
        geprueft = urteil(von, ziel, "F")
        if args.json:
            print(json.dumps(geprueft, ensure_ascii=False, indent=1))
            return 0 if geprueft["erlaubt"] else 1
        print(f"Konsolidierung: {von}")
        print(f"            → {ziel}")
        print(f"  Urteil: {'zulässig' if geprueft['erlaubt'] else 'nicht zulässig'}")
        for name, wert in geprueft["pruefungen"].items():
            zeichen = "✅" if wert["belegt"] else "🛑"
            print(f"  {zeichen} {name}: {wert['grund']}")
        print(f"\n  → {geprueft['empfehlung']}")
        return 0 if geprueft["erlaubt"] else 1

    alle = eintraege_lesen()
    befunde = pruefe(alle)
    if args.meldung or not (args.pruefen or args.json):
        b = bilanz(alle)
        print(f"Regel F (Konsolidierung): {b['konsolidierungen']} Eintrag/Einträge · "
              f"Bestand {b['gesamt']} ({', '.join(f'{k}: {v}' for k, v in b['nach_regel'].items())})")
        for befund in befunde:
            print(f"🛑 {befund['regel']} {befund['url']}: {befund['text']}")
        if not befunde:
            print("✅ Keine Konsolidierung ohne die drei Belege.")
        return 1 if befunde else 0

    if args.json:
        print(json.dumps({"bilanz": bilanz(alle), "befunde": befunde},
                         ensure_ascii=False, indent=1))
    else:
        for befund in befunde:
            print(f"🛑 {befund['regel']} {befund['url']}: {befund['text']}")
        print("✅ Alle Konsolidierungen belegt." if not befunde
              else f"{len(befunde)} Befund(e).")
    return 1 if befunde else 0


if __name__ == "__main__":
    sys.exit(main())
