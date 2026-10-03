#!/usr/bin/env python3
"""Kostensperre – fail-closed Schreibschutz vor allen Geldflächen.

    python3 scripts/kostensperre.py              # Bericht
    python3 scripts/kostensperre.py --pruefen    # Wache (Exit 1 bei Funden)
    python3 scripts/kostensperre.py --json       # Maschinen-Ausgabe
    python3 scripts/kostensperre.py --selftest   # Positiv- + Sabotageproben

WARUM ES DIESE WACHE GIBT (03.10.2026)
--------------------------------------
Nach dem Umbau des KI-Transportwegs gab es im Repo noch zwei Flächen, an
denen Geld fließen KÖNNTE: die Vorlese-Stimme (ElevenLabs) und die
Rechtschreibung auf ZEIT-Niveau. Beide kosteten 0 € – aber nur, weil kein
Schlüssel gesetzt war.

Das ist keine Zusicherung, das ist ein Zufall. Ein Zustand, der nur hält,
solange niemand ein Secret setzt, kippt irgendwann still: Die Automatik
läuft nachts, der Fehler ist keiner, und die Rechnung kommt mit einem
Monat Verspätung. Dieselbe Schadensklasse wie #514, nur mit Betrag.

WAS DIE SPERRE TUT
------------------
Der kostenpflichtige Zweig fragt VOR der ersten Ausgabe hier nach. Die
Antwort ist fail-closed: gesperrt, solange data/kostensperre.yaml nicht
ausdrücklich etwas anderes sagt. Ein gesetzter Schlüssel allein genügt
also nicht mehr – es braucht zusätzlich einen sichtbaren Commit mit
Begründung und Datum.

WAS SIE NICHT TUT
-----------------
Sie löscht nichts. Beide Premium-Pfade bleiben vollständig erhalten und
sind mit einer Zeile wieder scharf. Gesperrt ≠ entfernt: Die Vorlese-
Stimme ist hörbar besser als der Gratis-Weg, diese Entscheidung soll
Frank treffen können, nicht ein vergessenes Secret.

WARUM DIE SPERRE SELBST GEPRÜFT WIRD
------------------------------------
Eine Sperre, die niemand ruft, ist Dekoration. `--pruefen` belegt
deshalb nicht nur den Zustand der SSOT, sondern auch, dass jede Fläche
ihre Engstelle besitzt und diese Datei dort wirklich gefragt wird.
Regel T10 in scripts/ki_transportweg.py prüft dasselbe aus der anderen
Richtung, damit die beiden nicht auseinanderlaufen.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:                                    # pragma: no cover
    # KEIN SystemExit beim Import: Dieses Modul wird aus laufenden
    # Pipelines heraus importiert (Vertonung, Rechtschreibung). Ein
    # harter Abbruch hier wuerde eine fehlende Bibliothek in einen
    # Totalausfall verwandeln. Ohne YAML gilt die SSOT als unlesbar –
    # und damit ist fail-closed ohnehin ALLES gesperrt.
    yaml = None

ROOT = Path(__file__).resolve().parent.parent
SSOT = ROOT / "data" / "kostensperre.yaml"

# Einmal pro Prozess warnen, nicht pro Satz – sonst ersäuft die Meldung
# im Protokoll und wird dadurch wertlos.
_GEMELDET: set = set()


# ====================================================================
#  SSOT
# ====================================================================
def lade_ssot(pfad: Path | None = None) -> dict:
    """Liest die SSOT. Fehlt sie, gilt ALLES als gesperrt (fail-closed).

    Der Pfad wird beim AUFRUF aufgelöst, nicht beim Import. Als
    Default-Parameter gebunden (`pfad: Path = SSOT`) wäre er
    eingefroren – dann liesse sich die Wache weder umlenken noch
    pruefen, und eine Wache, die man nicht pruefen kann, ist eine
    Behauptung. Genau das fiel in der T10-Sabotageprobe auf.
    """
    pfad = Path(pfad) if pfad is not None else SSOT
    if yaml is None:
        return {"version": 0, "regeln": {}, "flaechen": [], "_defekt": True,
                "_grund": "PyYAML fehlt"}
    try:
        with open(pfad, encoding="utf-8") as fh:
            daten = yaml.safe_load(fh) or {}
    except (OSError, yaml.YAMLError):
        return {"version": 0, "regeln": {}, "flaechen": [], "_defekt": True}
    if not isinstance(daten, dict):
        return {"version": 0, "regeln": {}, "flaechen": [], "_defekt": True}
    daten.setdefault("regeln", {})
    daten.setdefault("flaechen", [])
    return daten


def flaeche(fid: str, ssot: dict | None = None) -> dict | None:
    for f in (ssot or lade_ssot()).get("flaechen", []):
        if isinstance(f, dict) and f.get("id") == fid:
            return f
    return None


# ====================================================================
#  DIE SPERRE (das, was die Geldpfade aufrufen)
# ====================================================================
def erlaubt(fid: str, ssot: dict | None = None) -> bool:
    """Darf diese Fläche Geld ausgeben?

    Fail-closed in jeder Richtung:
      · SSOT kaputt oder nicht lesbar      -> nein
      · Fläche unbekannt                   -> nein
      · freigegeben fehlt oder ist nicht True -> nein
      · Freigabe ohne Begründung/Datum     -> nein

    Der letzte Punkt ist Absicht: Eine Freigabe, die niemand begründet
    hat, ist kein Beschluss, sondern ein Ausrutscher beim Editieren.
    """
    daten = ssot if ssot is not None else lade_ssot()
    if daten.get("_defekt"):
        return False
    eintrag = flaeche(fid, daten)
    if eintrag is None:
        return False
    if eintrag.get("freigegeben") is not True:
        return False
    regeln = daten.get("regeln", {})
    if regeln.get("freigabe_braucht_grund", True) and not str(
            eintrag.get("grund", "")).strip():
        return False
    if regeln.get("freigabe_braucht_datum", True) and not str(
            eintrag.get("datum", "")).strip():
        return False
    return True


def wache(fid: str, ssot: dict | None = None, leise: bool = False) -> bool:
    """`erlaubt()` mit einer Klartext-Meldung beim ersten Nein.

    Stille Fehlschläge sind die teuerste Sorte (#514). Wer hier
    abgewiesen wird, soll im Protokoll sehen WARUM und WOHIN
    ausgewichen wird – nicht bloß ein unerklärtes Downgrade.
    """
    if erlaubt(fid, ssot):
        return True
    if not leise and fid not in _GEMELDET:
        _GEMELDET.add(fid)
        eintrag = flaeche(fid, ssot if ssot is not None else lade_ssot()) or {}
        name = eintrag.get("name", fid)
        gratis = eintrag.get("gratis_weg", "kostenloser Normalbetrieb")
        print(f"KOSTENSPERRE: „{name}“ ist gesperrt – es wird NICHTS "
              f"abgerechnet. Aktiver Weg: {gratis}. "
              f"Entsichern: data/kostensperre.yaml → flaechen[{fid}] → "
              f"freigegeben: true + grund + datum.", file=sys.stderr)
    return False


# ====================================================================
#  WACHE
# ====================================================================
def _quelltext(rel: str) -> str:
    try:
        return (ROOT / rel).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def pruefen(ssot: dict | None = None) -> list:
    """Alle Vertragsregeln. Rückgabe: Liste der Befunde (leer = gut)."""
    daten = ssot if ssot is not None else lade_ssot()
    befunde: list = []

    if daten.get("_defekt"):
        return ["data/kostensperre.yaml fehlt oder ist unlesbar – ohne SSOT "
                "ist jede Geldfläche gesperrt, aber der Zustand ist nicht "
                "mehr belegbar."]

    regeln = daten.get("regeln", {})
    if regeln.get("standard_gesperrt") is not True:
        befunde.append("Regel `standard_gesperrt` ist nicht true – die Sperre "
                       "wäre dann ein Vorschlag statt eines Schutzes.")

    flaechen = daten.get("flaechen", [])
    if not flaechen:
        befunde.append("Keine Geldfläche verzeichnet. Entweder ist die SSOT "
                       "leer oder eine Fläche wurde still entfernt.")

    gesehen: set = set()
    for eintrag in flaechen:
        if not isinstance(eintrag, dict):
            befunde.append(f"Fehlerhafter Eintrag in flaechen: {eintrag!r}")
            continue
        fid = eintrag.get("id", "")
        if not fid:
            befunde.append("Geldfläche ohne id – nicht referenzierbar.")
            continue
        if fid in gesehen:
            befunde.append(f"Geldfläche `{fid}` doppelt verzeichnet.")
        gesehen.add(fid)

        # 1) Zustand
        if eintrag.get("freigegeben") is True:
            fehlend = [feld for feld in ("grund", "datum")
                       if not str(eintrag.get(feld, "")).strip()]
            if fehlend:
                befunde.append(
                    f"`{fid}` ist freigegeben, aber {' und '.join(fehlend)} "
                    "fehlt. Eine Freigabe ohne Begründung und Datum ist kein "
                    "Beschluss – sie wird als Versehen behandelt und bleibt "
                    "wirkungslos.")

        # 2) Gratis-Weg
        if regeln.get("jede_flaeche_braucht_gratis_weg", True) and not str(
                eintrag.get("gratis_weg", "")).strip():
            befunde.append(
                f"`{fid}` benennt keinen kostenlosen Weg. Eine Sperre ohne "
                "Rückfall wäre ein Ausfall, kein Schutz.")

        # 3) Engstelle existiert …
        modul = eintrag.get("modul", "")
        funktion = eintrag.get("funktion", "")
        if not modul or not funktion:
            befunde.append(f"`{fid}` benennt keine Engstelle (modul/funktion) "
                           "– die Sperre wäre nicht nachweisbar verdrahtet.")
            continue
        quelle = _quelltext(modul)
        if not quelle:
            befunde.append(f"`{fid}`: {modul} ist nicht lesbar.")
            continue
        if f"def {funktion}" not in quelle:
            befunde.append(
                f"`{fid}`: {modul} hat keine Funktion `{funktion}` (mehr). "
                "Wurde sie umbenannt, zeigt die Sperre ins Leere.")

        # 4) … und fragt die Sperre wirklich
        if "kostensperre" not in quelle:
            befunde.append(
                f"`{fid}`: {modul} ruft die Kostensperre nicht auf. Ein "
                "gesetzter Schlüssel würde dort unbemerkt Geld ausgeben.")
        elif f'"{fid}"' not in quelle and f"'{fid}'" not in quelle:
            befunde.append(
                f"`{fid}`: {modul} importiert die Sperre, fragt aber nicht "
                f"nach der Fläche `{fid}`. Vermutlich eine Umbenennung.")

    return befunde


def lage(ssot: dict | None = None) -> dict:
    daten = ssot if ssot is not None else lade_ssot()
    flaechen = []
    for e in daten.get("flaechen", []):
        if not isinstance(e, dict):
            continue
        fid = e.get("id", "")
        flaechen.append({
            "id": fid,
            "name": e.get("name", fid),
            "gesperrt": not erlaubt(fid, daten),
            "gratis_weg": e.get("gratis_weg", ""),
            "endpunkt": e.get("endpunkt", ""),
            "modul": e.get("modul", ""),
        })
    befunde = pruefen(daten)
    return {"stand": daten.get("stand", ""),
            "flaechen": flaechen,
            "alle_gesperrt": all(f["gesperrt"] for f in flaechen) if flaechen
                             else False,
            "befunde": befunde,
            "ok": not befunde}


def bericht(daten: dict) -> str:
    zeilen = ["KOSTENSPERRE – Geldflächen des Repos", ""]
    for f in daten["flaechen"]:
        zeichen = "🔒" if f["gesperrt"] else "⚠️ OFFEN"
        zeilen.append(f"  {zeichen}  {f['name']}")
        zeilen.append(f"        Engstelle: {f['modul']}")
        zeilen.append(f"        Aktiv:     {f['gratis_weg']}")
    zeilen.append("")
    if daten["befunde"]:
        zeilen.append("BEFUNDE:")
        zeilen += [f"  ❌ {b}" for b in daten["befunde"]]
    else:
        zeilen.append("✅ Vertrag erfüllt: Jede Geldfläche ist verdrahtet, "
                      "begründet und fail-closed.")
    return "\n".join(zeilen)


# ====================================================================
#  SELBSTTEST
# ====================================================================
def _selftest() -> int:
    """Positivprobe am echten Bestand + Sabotageproben an Kopien.

    Die Sabotageproben sind der eigentliche Beweis: Eine Wache, die nur
    bestätigt, dass heute alles gut ist, hat nie gezeigt, dass sie einen
    Defekt überhaupt bemerken würde.
    """
    fehler: list = []
    echt = lade_ssot()

    # --- Positivprobe -------------------------------------------------
    befunde = pruefen(echt)
    if befunde:
        fehler.append(f"Positivprobe rot: {befunde}")
    if not lage(echt)["alle_gesperrt"]:
        fehler.append("Positivprobe: nicht alle Geldflächen sind gesperrt.")
    for fid in ("vorlese_stimme", "rechtschreibung_premium"):
        if erlaubt(fid, echt):
            fehler.append(f"{fid} ist NICHT gesperrt.")
        if flaeche(fid, echt) is None:
            fehler.append(f"{fid} fehlt in der SSOT.")

    import copy

    def probe(name: str, bauen, erwarte_befund: bool = True,
              pruefung=None) -> None:
        kopie = copy.deepcopy(echt)
        bauen(kopie)
        ergebnis = (pruefung(kopie) if pruefung else bool(pruefen(kopie)))
        if ergebnis != erwarte_befund:
            fehler.append(f"Sabotage „{name}“ wurde nicht bemerkt.")

    # ST1: Freigabe ohne Begründung darf nicht wirken
    def st1(d):
        d["flaechen"][0]["freigegeben"] = True
        d["flaechen"][0].pop("grund", None)
        d["flaechen"][0].pop("datum", None)
    probe("Freigabe ohne Grund/Datum", st1)
    kopie = copy.deepcopy(echt)
    st1(kopie)
    if erlaubt("vorlese_stimme", kopie):
        fehler.append("Freigabe ohne Begründung schaltet die Sperre frei.")

    # ST2: Engstelle umbenannt -> Sperre zeigt ins Leere
    probe("Funktion umbenannt",
          lambda d: d["flaechen"][0].update(funktion="gibt_es_nicht"))

    # ST3: Modul zeigt woandershin
    probe("Modul falsch",
          lambda d: d["flaechen"][0].update(modul="scripts/gibt_es_nicht.py"))

    # ST4: Gratis-Weg entfernt
    probe("Gratis-Weg fehlt",
          lambda d: d["flaechen"][0].update(gratis_weg=""))

    # ST5: Grundregel aufgeweicht
    probe("standard_gesperrt abgeschaltet",
          lambda d: d["regeln"].update(standard_gesperrt=False))

    # ST6: Fläche still entfernt
    probe("alle Flächen entfernt", lambda d: d.update(flaechen=[]))

    # ST7: doppelte id
    probe("doppelte id",
          lambda d: d["flaechen"].append(copy.deepcopy(d["flaechen"][0])))

    # ST8: kaputte SSOT -> alles gesperrt, aber gemeldet
    kaputt = {"_defekt": True, "regeln": {}, "flaechen": []}
    if not pruefen(kaputt):
        fehler.append("Kaputte SSOT wird nicht gemeldet.")
    if erlaubt("vorlese_stimme", kaputt):
        fehler.append("Kaputte SSOT erlaubt Ausgaben – nicht fail-closed!")

    # ST9: unbekannte Fläche ist gesperrt
    if erlaubt("gibt_es_nicht", echt):
        fehler.append("Unbekannte Fläche gilt als erlaubt – nicht fail-closed!")

    # ST10: Entsichern MUSS funktionieren – sonst ist es Löschen,
    #       und genau das war nicht gewollt.
    kopie = copy.deepcopy(echt)
    kopie["flaechen"][0].update(freigegeben=True, grund="Testfreigabe",
                                datum="2026-10-03")
    if not erlaubt(kopie["flaechen"][0]["id"], kopie):
        fehler.append("Eine ordentlich begründete Freigabe wirkt nicht – "
                      "die Sperre wäre eine Einbahnstraße.")
    if pruefen(kopie):
        fehler.append("Eine ordentlich begründete Freigabe erzeugt Befunde.")

    # ST11: wache() muss bei Sperre laut sein und False liefern
    _GEMELDET.clear()
    if wache("vorlese_stimme", echt, leise=True):
        fehler.append("wache() lässt eine gesperrte Fläche durch.")

    if fehler:
        print("❌ Kostensperre-Selbsttest ROT:", file=sys.stderr)
        for f in fehler:
            print(f"   · {f}", file=sys.stderr)
        return 1
    print("✅ Kostensperre-Selbsttest grün (Positivprobe + 11 Proben, "
          "inkl. Nachweis, dass Entsichern weiterhin möglich ist).")
    return 0


# ====================================================================
#  CLI
# ====================================================================
def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Kostensperre – fail-closed Schutz vor Geldflächen.")
    p.add_argument("--pruefen", action="store_true",
                   help="Wache (Exit 1 bei Funden)")
    p.add_argument("--json", action="store_true", help="Maschinen-Ausgabe")
    p.add_argument("--selftest", action="store_true",
                   help="Positiv- und Sabotageproben")
    args = p.parse_args(argv)

    if yaml is None:
        print("FEHLT: PyYAML (pip install pyyaml) – die Wache kann den "
              "Zustand nicht belegen. Geldflaechen sind trotzdem gesperrt.",
              file=sys.stderr)
        return 2

    if args.selftest:
        return _selftest()

    daten = lage()
    if args.json:
        print(json.dumps(daten, ensure_ascii=False, indent=2))
    else:
        print(bericht(daten))
    if args.pruefen and daten["befunde"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
