#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EIN Meldeweg für GitHub-Workflow-Kommandos – Fluchtschutz und Teststille.

WARUM ES DIESEN MELDER GIBT (WF-E813 / #815, 27.10.2026)
--------------------------------------------------------
Der Vorgang WF-E813 stand seit dem 19.10.2026 offen, weil zwei Live-Prüfungen
rot waren. Beim Nachmessen des Laufs `40499567144`
(„Sicherheits-Wache“, 27.10.2026, Event `schedule`) fiel etwas anderes auf:
Der Job **„Abhängigkeiten (Pins offline · Audit online)“ war grün** – und trug
trotzdem **drei rote Annotationen** an seiner Fassade:

    ::error title=Abhängigkeits-Wache A1::`pyyaml` ist als Bereich genannt …
    ::error title=Schwachstelle GHSA-q::x@1.0.0 (npm, high) – Fix: … – Test
    ::error title=Abhängigkeits-Audit gestört::Kein GITHUB_TOKEN/GH_TOKEN …

Keine davon beschrieb den Lauf. Sie waren die **Ausgabe der Vertragstests**:
`test_abhaengigkeits_wache.py` ruft `wache.main(["--check", …])` auf einem
vergifteten Testbaum auf – und `main()` druckt seine Befunde als
Workflow-Kommando. GitHub parst jede Zeile, die mit `::` beginnt, aus dem
Job-Log und macht daraus eine Annotation. Ergebnis: Ein grüner Job, der wie
ein roter aussieht, mit einem Dateiverweis auf `requirements-x.txt` und einem
Schwachstellen-Treffer `x@1.0.0`, die es beide im Repository nicht gibt.

Das ist keine Kosmetik. Die ganze WF-E813-Kette lebt davon, dass **rot etwas
bedeutet**. Wer täglich falsche rote Kreuze im eigenen Lauf sieht, gewöhnt
sich an rote Kreuze – genau die Betriebsblindheit, die den stillen
Worker-Deploy (#829B) und das stille CodeQL-Gate (26.10.2026) erst möglich
gemacht hat. Ein Signal, das auch ohne Anlass leuchtet, ist kein Signal.

DIE ZWEITE HÄLFTE: EIN KOMMANDO IST EINE SCHNITTSTELLE, KEIN TEXT
------------------------------------------------------------------
`::error file=…,line=…,title=…::Text` ist kein Log-Text, sondern ein Befehl
an den Runner. Wer Datei- und Textinhalte ungeprüft einsetzt, kann Befehle
**erzeugen**: Ein Zeilenumbruch beginnt ein neues Kommando, ein `,` bricht
aus der Eigenschaftsliste aus. Die Werte stammen hier aus dem Baum
(Dateinamen, Requirement-Zeilen, HTTP-Antworten) – also aus Inhalten, die ein
Pull Request beeinflussen kann. Deshalb wird nach der GitHub-Vorschrift
prozent-kodiert: `%`, CR, LF im Text; zusätzlich `:` und `,` in
Eigenschaften. Ein Befund bleibt damit immer **ein** Kommando.

WAS `aktiv()` ENTSCHEIDET (und warum die Reihenfolge so ist)
-----------------------------------------------------------
    1. `GITHUB_KOMMANDOS=an|aus` – eine ausdrückliche Ansage gewinnt immer.
       Sie ist der Notausgang für beide Richtungen (lokale Gegenprobe,
       Sonderfall in einem Lauf).
    2. Ohne `GITHUB_ACTIONS=true` gibt es keinen Runner, der die Zeile
       versteht. Dann ist sie Lärm in einem Log – also nur Klartext.
    3. Läuft der Prozess unter einem Test-Runner (`unittest`, `pytest`),
       wird **nie** ein Kommando gesendet. Ein Test prüft Verhalten; er
       darf den Lauf, in dem er läuft, nicht einfärben. Genau diese Lücke
       erzeugte die drei falschen Annotations.

EHRLICHE GRENZE
---------------
Punkt 3 erkennt die Test-Runner, die dieses Repo benutzt. Ein fremder
Runner (oder ein Test, der `main()` in einem eigenen Prozess startet) wird
nicht erkannt – dort hilft nur `GITHUB_KOMMANDOS=aus` in der Umgebung des
Schritts. Die Umkehr gilt ebenfalls: Ein Produktionsskript, das `unittest`
importiert, bliebe stumm; das ist im Bestand nicht der Fall und wäre beim
ersten fehlenden Signal sofort sichtbar. Die Vertragstests in
`scripts/tests/test_github_kommando.py` prüfen beide Richtungen –
Stille im Testlauf und Kommando mit `GITHUB_KOMMANDOS=an`.

BENUTZUNG
---------
    from github_kommando import annotation, kommando

    annotation("error", "Header fehlt", datei="content/x.md", zeile=12,
               titel="Wache A1")        # sendet oder schreibt Klartext
    kommando("error", "Header fehlt")   # reine Zeichenkette (testbar)

`annotation()` gibt zurück, ob ein Workflow-Kommando gesendet wurde. Der
Rückgabewert ist die einzige ehrliche Auskunft darüber – nicht das Log.
"""
from __future__ import annotations

import os
import sys
from typing import Mapping

EBENEN = ("error", "warning", "notice")

# Runner, die dieses Repo benutzt. Wer hier steht, färbt keinen Lauf.
TEST_RUNNER = ("unittest", "pytest")

AN = ("an", "ein", "on", "1", "true", "wahr", "ja")
AUS = ("aus", "off", "0", "false", "falsch", "nein")


def _prozent(wert: object) -> str:
    """Kodiert Text für die Kommando-Nutzlast (`%`, CR, LF)."""
    return (str(wert).replace("%", "%25")
            .replace("\r", "%0D").replace("\n", "%0A"))


def _eigenschaft(wert: object) -> str:
    """Kodiert Text für eine Eigenschaft (`file=`, `title=`).

    Zusätzlich zu `%`, CR und LF werden `:` und `,` kodiert – sonst könnte
    ein Wert die Eigenschaftsliste verlassen (`file=a,line=1` → zwei
    Eigenschaften) oder ein Folgekommando einleiten.
    """
    return _prozent(wert).replace(":", "%3A").replace(",", "%2C")


def kommando(ebene: str, text: object, *, datei: object | None = None,
             zeile: int | None = None, titel: object | None = None) -> str:
    """Baut die Workflow-Kommandozeile. Reine Funktion, ohne Ausgabe."""
    if ebene not in EBENEN:
        raise ValueError(f"Unbekannte Ebene {ebene!r}; erlaubt: {EBENEN}")
    eigenschaften: list[str] = []
    if datei is not None and str(datei) != "":
        eigenschaften.append(f"file={_eigenschaft(datei)}")
    if zeile is not None:
        eigenschaften.append(f"line={int(zeile)}")
    if titel is not None and str(titel) != "":
        eigenschaften.append(f"title={_eigenschaft(titel)}")
    kopf = "::" + ebene + ((" " + ",".join(eigenschaften)) if eigenschaften else "") + "::"
    return kopf + _prozent(text)


def aktiv(umgebung: Mapping[str, str] | None = None,
          module: Mapping[str, object] | None = None) -> bool:
    """Darf dieser Prozess Workflow-Kommandos senden?"""
    umgebung = os.environ if umgebung is None else umgebung
    module = sys.modules if module is None else module
    wahl = str(umgebung.get("GITHUB_KOMMANDOS", "")).strip().lower()
    if wahl in AN:
        return True
    if wahl in AUS:
        return False
    if str(umgebung.get("GITHUB_ACTIONS", "")).strip().lower() != "true":
        return False
    return not any(name in module for name in TEST_RUNNER)


def klartext(ebene: str, text: object, *, datei: object | None = None,
             zeile: int | None = None, titel: object | None = None) -> str:
    """Lesbare Ersatzzeile für Läufe ohne Runner (lokal, Test, Debug).

    Sie trägt dieselbe Information wie das Kommando (Titel, Ort, Text) in
    einer Form, die kein Runner als Befehl deutet – ein lokaler Lauf soll
    nicht schlechter lesbar sein als ein CI-Lauf.
    """
    ort = ""
    if datei is not None and str(datei) != "":
        ort = f"{datei}:{int(zeile)}: " if zeile is not None else f"{datei}: "
    elif zeile is not None:
        ort = f"Zeile {int(zeile)}: "
    kopf = f"[{ebene}] "
    if titel is not None and str(titel) != "":
        kopf += f"{titel}: "
    return f"{kopf}{ort}{text}"


def annotation(ebene: str, text: object, *, datei: object | None = None,
               zeile: int | None = None, titel: object | None = None,
               erzwingen: bool = False) -> bool:
    """Sended ein Workflow-Kommando – oder eine Klartextzeile.

    Gibt ``True`` zurück, wenn ein Workflow-Kommando tatsächlich gesendet
    wurde. ``erzwingen`` ist nur für die eigene Gegenprobe gedacht (Tests
    der Sendezeile); im Betrieb entscheidet ``aktiv()``.
    """
    if erzwingen or aktiv():
        print(kommando(ebene, text, datei=datei, zeile=zeile, titel=titel))
        return True
    print(klartext(ebene, text, datei=datei, zeile=zeile, titel=titel))
    return False


# --------------------------------------------------------------------------- #
#  Selbstdiagnose (bewusst KEIN Kommando: eine Probe darf nichts einfärben)
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Zeigt, ob dieser Prozess Workflow-Kommandos senden würde.")
    parser.add_argument("--probe", action="store_true",
                        help="Zustand und ein kodiertes Beispiel ausgeben (Standard)")
    args = parser.parse_args(argv)  # noqa: F841 - nur ein Schalter, Meldung unten

    zustand = "AN" if aktiv() else "AUS"
    print(f"Workflow-Kommandos: {zustand}")
    print(f"  GITHUB_ACTIONS={os.environ.get('GITHUB_ACTIONS', '')!r}"
          f" · GITHUB_KOMMANDOS={os.environ.get('GITHUB_KOMMANDOS', '')!r}"
          f" · Test-Runner={'ja' if any(m in sys.modules for m in TEST_RUNNER) else 'nein'}")
    print("Beispiel (kodiert, ein Befund bleibt eine Zeile):")
    print("  " + kommando("error", "Befund mit Umbruch\n::warning::erfunden",
                          datei="requirements-x.txt", zeile=1,
                          titel="Abhängigkeits-Wache A1"))
    print("Hinweis: Im Test-Runner ist AUS der richtige Zustand; "
          "GITHUB_KOMMANDOS=an erzwingt das Senden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
