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
    p.add_argument("--json", action="store_true", help="Ergebnis als JSON")
    p.add_argument("--selftest", action="store_true", help="offline, ohne Netz")
    args = p.parse_args(argv)

    if args.selftest:
        return selbsttest()

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
