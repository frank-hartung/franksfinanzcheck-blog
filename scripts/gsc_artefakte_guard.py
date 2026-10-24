#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gsc_artefakte_guard.py – Wache über die Search-Console-Artefakte
================================================================

WARUM ES DIESE WACHE GIBT (24.10.2026)
-------------------------------------
Am 21.10.2026 wurde in `data/gsc/` zum ersten Mal eine Datei zusammengesetzt
statt geschrieben. Seitdem stand in `main`:

    data/gsc/meta.json             – fünf Läufe (20.–24.10.) übereinander
                                     geklebt: `"stand"` viermal im selben
                                     Objekt, Klammer fehlt, kein gültiges JSON.
    data/gsc/top_seiten_28t.json   – zwei Läufe ineinander geschoben, mitten
                                     im Eintrag „impressum“ drei Fragmente
                                     ohne Komma.
    data/gsc/top_suchbegriffe_28t.json – dito; ein Suchbegriff-Objekt trägt
                                     die Kennzahlen des nächsten Laufs.

Der Import selbst kann das nicht: `gsc_import.py` schreibt jede Datei mit
`Path.write_text(json.dumps(...))`, also immer vollständig und immer gültig.
Die Verkettung ist beim **Zusammenführen** entstanden: Die Bot-Branches
`automation/gsc-tagesdaten-*` liefen hinter `main` her, jede berührte
dieselben drei Dateien, und Git hat die Konflikte als Text gemergt
(`Merge branch 'main' into automation/gsc-tagesdaten-20261021`, PR #828).
Ein Text-Merge hat auf einem ganzen Messartefakt nichts zu suchen: Es gibt
keine Zeile, die zu beiden Läufen gehört.

Vier Tage lang hat das niemandem wehgetan – bis der **Artefakt-Wächter** im
`Integritäts-Siegel` es las und jeden Pull-Request des Repos rot machte
(`A1-JSON-SYNTAX`, drei Funde). Genau die Klasse, die `#346`
(`data/integrity_lock.json`), `#634` (Reserve-Snapshots) und `#783`
(Quelltext-Wachen) schon kennen: **ein Ganzartefakt wird nie gemischt.**

DREI SCHICHTEN, EINE AUSSAGE
----------------------------
 1. STRUKTUR (`.gitattributes`)
    `data/gsc/*.json merge=binary` – Git darf die Dateien nicht mehr als Text
    zusammensetzen. Bei parallelen Änderungen bleibt EIN vollständiger Stand
    übrig; den Konflikt löst ein Mensch bewusst.
 2. BEDEUTUNG (diese Wache)
    Gültiges JSON ist nicht genug. Zwei gültige Top-Listen hintereinander
    ergeben weiterhin gültiges JSON – aber mit doppelten Suchbegriffen und
    Zahlen aus zwei Fenstern. G2/G3 prüfen deshalb Eindeutigkeit, G4 prüft,
    ob `meta.json` noch zu `tagesdaten.jsonl` passt.
 3. HERKUNFT (`--heal`)
    Repariert wird nur mit Beweis: Der Stand wird aus dem Git geholt
    (`git show <rev>:<pfad>`) und muss die volle Prüfung bestehen. Es wird
    nichts rekonstruiert, nichts gemittelt, nichts erfunden – gibt es keinen
    belegbar gültigen Stand, bleibt der Fund stehen (Exit 1).

PRÜFUNGEN
---------
    G1 META      data/gsc/meta.json ist ein Objekt mit den Pflichtfeldern
                 stand/quelle/site/zeitraum/status/grund/datenschutz;
                 `stand` ist ISO-8601 (UTC, `Z`), `zeitraum.von <= bis`,
                 `status` aus {ok, nicht_konfiguriert, fehler}.
                 Bei `status: ok` zusätzlich tage_neu/tage_gesamt/
                 klicks_zeitraum (ganze Zahlen, >= 0, tage_neu <= tage_gesamt).
    G2 TOP       top_seiten_28t.json / top_suchbegriffe_28t.json sind Listen
                 aus Objekten mit genau den Schlüsseln des Erzeugers
                 (`seite` bzw. `suchbegriff`, clicks, impressions, ctr,
                 position), Zahlen in gültigen Bereichen, Schlüssel nicht
                 leer und **je Liste eindeutig** (Splice-Indikator).
    G3 LEDGER    data/gsc/tagesdaten.jsonl: je Zeile ein Objekt mit datum/
                 clicks/impressions/ctr/position, Datum ISO und **streng
                 aufsteigend ohne Doppel** (Splice-Indikator).
    G4 KREUZ     Passt der Kopf zu den Zahlen? `meta.zeitraum.bis` darf nicht
                 hinter dem letzten Ledger-Tag liegen, `tage_gesamt` nicht
                 über der Zahl der Ledger-Tage (der Ledger wächst nur).
                 Das ist die Prüfung, die eine gültige, aber aus zwei Läufen
                 zusammengesetzte Datei noch erwischt.

NUTZUNG
    python3 scripts/gsc_artefakte_guard.py            # prüfen (hart, Exit 1 bei Fund)
    python3 scripts/gsc_artefakte_guard.py --check    # dasselbe, explizit
    python3 scripts/gsc_artefakte_guard.py --heal     # belegbaren Git-Stand zurückholen
    python3 scripts/gsc_artefakte_guard.py --selftest # Sabotageschutz (schreibt nur in tmp, C15)
    python3 scripts/gsc_artefakte_guard.py --json     # maschinenlesbar

EXIT: 0 = grün · 1 = Fund (bzw. Heilung nicht möglich) · 2 = Selbsttest rot
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GSC = Path("data") / "gsc"

META = "meta.json"
TOP_SEITEN = "top_seiten_28t.json"
TOP_SUCHBEGRIFFE = "top_suchbegriffe_28t.json"
LEDGER = "tagesdaten.jsonl"

TOP_DATEIEN = ((TOP_SEITEN, "seite"), (TOP_SUCHBEGRIFFE, "suchbegriff"))
STATUS_WERTE = ("ok", "nicht_konfiguriert", "fehler")
META_PFLICHT = ("stand", "quelle", "site", "zeitraum", "status", "grund", "datenschutz")
KENNZAHLEN = ("clicks", "impressions", "ctr", "position")
ISO_TAG = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ISO_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


# --------------------------------------------------------------------------- Fund

class Fund:
    """Ein Befund: Prüfung, Datei, Meldung, Reparaturweg."""

    __slots__ = ("pruefung", "datei", "meldung", "reparatur")

    def __init__(self, pruefung: str, datei: str, meldung: str, reparatur: str = ""):
        self.pruefung = pruefung
        self.datei = datei
        self.meldung = meldung
        self.reparatur = reparatur

    def als_dict(self) -> dict:
        return {"pruefung": self.pruefung, "datei": self.datei,
                "meldung": self.meldung, "reparatur": self.reparatur}

    def __str__(self) -> str:
        return f"[{self.pruefung}] {self.datei}: {self.meldung}"

    def __repr__(self) -> str:  # pragma: no cover – Debug-Hilfe
        return f"Fund({self.pruefung!r}, {self.datei!r}, {self.meldung!r})"


HEILUNG = "python3 scripts/gsc_artefakte_guard.py --heal"


# ------------------------------------------------------------------ JSON-Helfer

def _ohne_doppelte(paare):
    """object_pairs_hook: doppelter Schlüssel im selben Objekt = Fund, kein Überschreiben."""
    gesehen = {}
    for schluessel, wert in paare:
        if schluessel in gesehen:
            raise ValueError(f"doppelter Schlüssel {schluessel!r}")
        gesehen[schluessel] = wert
    return gesehen


def _json(text: str):
    """Strenge Auswertung: UTF-8-Text → Objekt, mit Doppelschlüssel-Prüfung."""
    try:
        return json.loads(text, object_pairs_hook=_ohne_doppelte)
    except ValueError as e:  # json.JSONDecodeError ist ein ValueError
        raise ValueError(str(e)) from None


def _ist_zahl(wert) -> bool:
    return isinstance(wert, (int, float)) and not isinstance(wert, bool)


def _ist_ganzzahl(wert) -> bool:
    return isinstance(wert, int) and not isinstance(wert, bool)


# ------------------------------------------------------------------ Prüfungen

def pruefe_meta(daten) -> list[str]:
    """G1 – Kopf der Messung."""
    fehler: list[str] = []
    if not isinstance(daten, dict):
        return ["meta.json ist kein Objekt"]
    for feld in META_PFLICHT:
        if feld not in daten:
            fehler.append(f"Pflichtfeld fehlt: {feld}")
    stand = daten.get("stand")
    if "stand" in daten:
        if not isinstance(stand, str) or not ISO_UTC.match(stand):
            fehler.append(f"stand ist nicht ISO-8601/UTC: {stand!r}")
        else:
            try:
                dt.datetime.strptime(stand, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                fehler.append(f"stand ist kein gültiger Zeitpunkt: {stand!r}")
    zeitraum = daten.get("zeitraum")
    if "zeitraum" in daten:
        if not isinstance(zeitraum, dict) or set(zeitraum) != {"von", "bis"}:
            fehler.append("zeitraum muss genau {von, bis} tragen")
        else:
            von, bis = zeitraum.get("von"), zeitraum.get("bis")
            if not (isinstance(von, str) and ISO_TAG.match(von)
                    and isinstance(bis, str) and ISO_TAG.match(bis)):
                fehler.append("zeitraum.von/bis sind keine ISO-Datumsangaben")
            else:
                try:
                    if dt.date.fromisoformat(von) > dt.date.fromisoformat(bis):
                        fehler.append(f"zeitraum ist verdreht: {von} > {bis}")
                except ValueError:
                    fehler.append("zeitraum enthält kein gültiges Datum")
    status = daten.get("status")
    if "status" in daten and status not in STATUS_WERTE:
        fehler.append(f"status ist unbekannt: {status!r} (erlaubt: {', '.join(STATUS_WERTE)})")
    if status == "ok":
        for feld in ("tage_neu", "tage_gesamt", "klicks_zeitraum"):
            if feld not in daten:
                fehler.append(f"status ok, aber Kennzahl fehlt: {feld}")
            elif not _ist_ganzzahl(daten[feld]) or daten[feld] < 0:
                fehler.append(f"{feld} ist keine ganze Zahl >= 0: {daten[feld]!r}")
        neu, gesamt = daten.get("tage_neu"), daten.get("tage_gesamt")
        if _ist_ganzzahl(neu) and _ist_ganzzahl(gesamt) and neu > gesamt:
            fehler.append(f"tage_neu ({neu}) > tage_gesamt ({gesamt})")
    return fehler


def pruefe_top(daten, dimension: str) -> list[str]:
    """G2 – Top-Liste: Schema, Wertebereiche, Eindeutigkeit."""
    fehler: list[str] = []
    if not isinstance(daten, list):
        return ["keine Liste"]
    if not daten:
        return fehler  # leere Liste ist ein gültiger Zustand (kein Traffic im Fenster)
    erwartet = {dimension, *KENNZAHLEN}
    gesehen: dict[str, int] = {}
    for i, eintrag in enumerate(daten):
        wo = f"Eintrag {i}"
        if not isinstance(eintrag, dict):
            fehler.append(f"{wo} ist kein Objekt")
            continue
        if set(eintrag) != erwartet:
            fehlend = sorted(erwartet - set(eintrag))
            zusatz = sorted(set(eintrag) - erwartet)
            teile = []
            if fehlend:
                teile.append("fehlt: " + ", ".join(fehlend))
            if zusatz:
                teile.append("unerwartet: " + ", ".join(zusatz))
            fehler.append(f"{wo}: Schlüssel weichen vom Erzeuger ab ({'; '.join(teile)})")
            continue
        schluessel = eintrag[dimension]
        if not isinstance(schluessel, str) or not schluessel.strip():
            fehler.append(f"{wo}: {dimension} ist leer")
        elif schluessel in gesehen:
            fehler.append(f"{wo}: {dimension} doppelt "
                          f"(zuerst Eintrag {gesehen[schluessel]}) – zwei Läufe übereinander?")
        else:
            gesehen[schluessel] = i
        for feld in ("clicks", "impressions"):
            if not _ist_ganzzahl(eintrag[feld]) or eintrag[feld] < 0:
                fehler.append(f"{wo}: {feld} ist keine ganze Zahl >= 0: {eintrag[feld]!r}")
        ctr = eintrag["ctr"]
        if not _ist_zahl(ctr) or not 0.0 <= float(ctr) <= 1.0:
            fehler.append(f"{wo}: ctr außerhalb 0…1: {ctr!r}")
        position = eintrag["position"]
        if not _ist_zahl(position) or float(position) < 0:
            fehler.append(f"{wo}: position ist keine Zahl >= 0: {position!r}")
    return fehler


def pruefe_ledger(text: str) -> list[str]:
    """G3 – Tagesledger: Zeilen-Schema, streng aufsteigende, eindeutige Tage."""
    fehler: list[str] = []
    erwartet = {"datum", *KENNZAHLEN}
    letzter: dt.date | None = None
    zeilen = [z for z in text.splitlines() if z.strip()]
    for nr, zeile in enumerate(zeilen, start=1):
        try:
            eintrag = _json(zeile)
        except ValueError as e:
            fehler.append(f"Zeile {nr}: kein gültiges JSON ({e})")
            continue
        if not isinstance(eintrag, dict) or set(eintrag) != erwartet:
            fehler.append(f"Zeile {nr}: Schlüssel weichen vom Erzeuger ab "
                          f"(erwartet: {', '.join(sorted(erwartet))})")
            continue
        datum = eintrag["datum"]
        if not isinstance(datum, str) or not ISO_TAG.match(datum):
            fehler.append(f"Zeile {nr}: datum ist kein ISO-Datum: {datum!r}")
            continue
        try:
            tag = dt.date.fromisoformat(datum)
        except ValueError:
            fehler.append(f"Zeile {nr}: datum ist ungültig: {datum!r}")
            continue
        if letzter is not None:
            if tag == letzter:
                fehler.append(f"Zeile {nr}: Tag {datum} doppelt – zwei Ledger-Stände gemischt?")
            elif tag < letzter:
                fehler.append(f"Zeile {nr}: Tag {datum} läuft rückwärts (vorher {letzter.isoformat()})")
        letzter = tag
        for feld in ("clicks", "impressions"):
            if not _ist_ganzzahl(eintrag[feld]) or eintrag[feld] < 0:
                fehler.append(f"Zeile {nr}: {feld} ist keine ganze Zahl >= 0")
        ctr = eintrag["ctr"]
        if not _ist_zahl(ctr) or not 0.0 <= float(ctr) <= 1.0:
            fehler.append(f"Zeile {nr}: ctr außerhalb 0…1: {ctr!r}")
        if not _ist_zahl(eintrag["position"]) or float(eintrag["position"]) < 0:
            fehler.append(f"Zeile {nr}: position ist keine Zahl >= 0")
    return fehler


def pruefe_kreuz(meta, ledger_text: str) -> list[str]:
    """G4 – Kopf gegen Zahlen: Fensterende und Tageszahl müssen zum Ledger passen."""
    fehler: list[str] = []
    if not isinstance(meta, dict) or meta.get("status") != "ok":
        return fehler
    tage = []
    for zeile in ledger_text.splitlines():
        if not zeile.strip():
            continue
        try:
            eintrag = _json(zeile)
        except ValueError:
            continue
        if isinstance(eintrag, dict) and isinstance(eintrag.get("datum"), str):
            try:
                tage.append(dt.date.fromisoformat(eintrag["datum"]))
            except ValueError:
                continue
    if not tage:
        return ["status ok, aber der Tagesledger ist leer – Aussage ohne Messung"]
    zeitraum = meta.get("zeitraum")
    if isinstance(zeitraum, dict) and isinstance(zeitraum.get("bis"), str):
        try:
            bis = dt.date.fromisoformat(zeitraum["bis"])
        except ValueError:
            bis = None
        if bis is not None and bis > max(tage):
            fehler.append(f"meta.zeitraum.bis ({bis.isoformat()}) liegt hinter dem "
                          f"letzten Ledger-Tag ({max(tage).isoformat()})")
    gesamt = meta.get("tage_gesamt")
    if _ist_ganzzahl(gesamt) and gesamt > len(set(tage)):
        fehler.append(f"meta.tage_gesamt ({gesamt}) > Ledger-Tage ({len(set(tage))}) – "
                      f"der Kopf beschreibt mehr Tage, als gemessen sind")
    return fehler


# ------------------------------------------------------------------ Datei-Ebene

def dateien(wurzel: Path) -> list[Path]:
    return [wurzel / GSC / META, wurzel / GSC / LEDGER,
            *(wurzel / GSC / name for name, _ in TOP_DATEIEN)]


def _misst(wurzel: Path) -> bool:
    """Misst der letzte Lauf überhaupt? Nur dann sind fehlende Dateien ein Fund.

    `gsc_import.py` schreibt `meta.json` in JEDEM Fall, die Messdateien aber
    nur mit Zugang. Ein Repo ohne Search-Console-Zugang hat deshalb genau eine
    Datei – und die sagt selbst, warum. Das ist ein deklarierter Zustand
    (`status: nicht_konfiguriert`), kein Defekt; ihn als Fund zu melden würde
    die Wache dauerhaft rot stellen und damit blind machen.
    """
    try:
        meta = _json((wurzel / GSC / META).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return True  # ohne lesbaren Kopf gilt: alles muss da und gültig sein
    return isinstance(meta, dict) and meta.get("status") == "ok"


def pruefe_datei(pfad: Path, fehlend_ist_fund: bool = True) -> list[str]:
    """Alle Prüfungen für EINE Datei (ohne Kreuzprüfung)."""
    rel = f"{GSC.as_posix()}/{pfad.name}"
    if not pfad.exists():
        if pfad.name != META and not fehlend_ist_fund:
            return []
        return [f"{rel} fehlt – der Import hat nie geschrieben"]
    try:
        text = pfad.read_text(encoding="utf-8")
    except OSError as e:
        return [f"{rel} ist nicht lesbar ({e})"]
    if pfad.suffix == ".jsonl":
        return pruefe_ledger(text)
    if pfad.name == META:
        try:
            return pruefe_meta(_json(text))
        except ValueError as e:
            return [f"kein gültiges JSON ({e})"]
    for name, dimension in TOP_DATEIEN:
        if pfad.name == name:
            try:
                return pruefe_top(_json(text), dimension)
            except ValueError as e:
                return [f"kein gültiges JSON ({e})"]
    return []  # pragma: no cover – nur bekannte Dateien werden übergeben


def pruefe_alle(wurzel: Path | None = None) -> list[Fund]:
    """G1–G4 über den ganzen Satz. Liefert die Befunde in Dateireihenfolge."""
    wurzel = wurzel or ROOT
    funde: list[Fund] = []
    messung = _misst(wurzel)
    for pfad in dateien(wurzel):
        rel = f"{GSC.as_posix()}/{pfad.name}"
        pruefung = "G3" if pfad.name == LEDGER else ("G1" if pfad.name == META else "G2")
        for meldung in pruefe_datei(pfad, fehlend_ist_fund=messung):
            funde.append(Fund(pruefung, rel, meldung, HEILUNG))
    # G4 nur, wenn die Einzelprüfungen sauber sind: aus kaputten Bytes eine
    # Kreuzaussage zu bauen hieße, den Fehler zu interpretieren.
    if not funde:
        meta_pfad = wurzel / GSC / META
        ledger_pfad = wurzel / GSC / LEDGER
        try:
            meta = _json(meta_pfad.read_text(encoding="utf-8"))
            ledger_text = ledger_pfad.read_text(encoding="utf-8")
        except (OSError, ValueError):
            return funde
        for meldung in pruefe_kreuz(meta, ledger_text):
            funde.append(Fund("G4", f"{GSC.as_posix()}/{META}", meldung, HEILUNG))
    return funde


# --------------------------------------------------------------------- Heilung

def _git(wurzel: Path, *args: str) -> str | None:
    try:
        r = subprocess.run(["git", *args], cwd=str(wurzel), capture_output=True,
                           text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def belegbarer_stand(pfad: Path, wurzel: Path, max_revs: int = 60) -> tuple[str, str] | None:
    """(Rev, Text) des jüngsten Commits, in dem die Datei die volle Prüfung besteht.

    LIEST NUR. Gibt es keinen solchen Stand, wird None zurückgegeben – es wird
    nichts rekonstruiert (ein zusammengesetztes Artefakt lässt sich nicht
    zurückrechnen, ohne Zahlen zu erfinden).
    """
    rel = pfad.relative_to(wurzel).as_posix()
    revs = _git(wurzel, "log", "--format=%H", "--", rel)
    if not revs:
        return None
    for rev in revs.split()[:max_revs]:
        text = _git(wurzel, "show", f"{rev}:{rel}")
        if not text:
            continue
        hinweis = pruefe_text(text, pfad.name)
        if not hinweis:
            return rev, text
    return None


def pruefe_text(text: str, dateiname: str) -> list[str]:
    """Wie `pruefe_datei`, aber auf einem Text im Speicher (Git-Historie, Tests)."""
    if dateiname == LEDGER:
        return pruefe_ledger(text)
    try:
        if dateiname == META:
            return pruefe_meta(_json(text))
    except ValueError as e:
        return [f"kein gültiges JSON ({e})"]
    for name, dimension in TOP_DATEIEN:
        if dateiname == name:
            try:
                return pruefe_top(_json(text), dimension)
            except ValueError as e:
                return [f"kein gültiges JSON ({e})"]
    return []  # pragma: no cover


def heile(wurzel: Path | None = None, rev: str | None = None) -> tuple[list[str], list[Fund]]:
    """Stellt jede Datei mit Befund auf ihren belegbar gültigen Git-Stand zurück.

    Ohne `rev` sucht jede Datei ihren EIGENEN jüngsten gültigen Stand. Mit
    `rev` werden die drei Kopfdaten (meta + beide Top-Listen) aus EINEM Commit
    geholt: Ein Lauf ist eine Messung, und drei Dateien aus drei Läufen sind
    wieder eine Chimäre – nur eine, die die Syntaxprüfung besteht. Der
    Tagesledger bleibt in jedem Fall unangetastet: Er ist append-only und
    wächst; ein Rückgriff auf einen älteren Ledger würde gemessene Tage
    löschen.

    Rückgabe: (Berichtszeilen, verbleibende Funde). Geschrieben wird NUR, wenn
    der Kandidat aus dem Git die volle Prüfung besteht – und danach wird die
    geschriebene Datei erneut geprüft (kein „signiert, ohne zu messen“).
    """
    wurzel = wurzel or ROOT
    if rev:
        return _heile_aus_rev(rev, wurzel)
    bericht: list[str] = []
    messung = _misst(wurzel)
    for pfad in dateien(wurzel):
        rel = f"{GSC.as_posix()}/{pfad.name}"
        aktuell = pruefe_datei(pfad, fehlend_ist_fund=messung)
        if not aktuell:
            continue
        stand = belegbarer_stand(pfad, wurzel)
        if stand is None:
            bericht.append(f"⛔ {rel}: kein belegbar gültiger Stand im Git – "
                           f"keine Heilung (Rekonstruktion wäre eine Fälschung)")
            continue
        rev, text = stand
        ziel = wurzel / pfad.relative_to(wurzel)
        alt = ziel.read_text(encoding="utf-8") if ziel.exists() else ""
        ziel.write_text(text, encoding="utf-8")
        nachher = pruefe_datei(ziel)
        if nachher:
            ziel.write_text(alt, encoding="utf-8")
            bericht.append(f"⛔ {rel}: Git-Stand {rev[:12]} besteht die Prüfung nicht "
                           f"({nachher[0]}) – Datei unverändert gelassen")
            continue
        bericht.append(f"🔧 {rel}: auf {rev[:12]} zurückgeholt "
                       f"({len(aktuell)} Befund(e): {aktuell[0]}" +
                       (" …" if len(aktuell) > 1 else "") + ")")
    verbleibend = pruefe_alle(wurzel)
    return bericht, verbleibend


def _heile_aus_rev(rev: str, wurzel: Path) -> tuple[list[str], list[Fund]]:
    """Alle Kopfdaten aus EINEM Commit – erst vollständig prüfen, dann schreiben.

    Kein Teil-Erfolg: Besteht eine der drei Dateien die Prüfung nicht, wird
    KEINE geschrieben. Ein halber Gesamtstand wäre schlimmer als der Befund.
    """
    kopf = _git(wurzel, "rev-parse", "--verify", f"{rev}^{{commit}}")
    if not kopf:
        return [f"⛔ Commit {rev!r} ist im Repo nicht auflösbar – keine Heilung"], pruefe_alle(wurzel)
    sha = kopf.strip()
    kandidaten: list[tuple[Path, str]] = []
    for name in (META, TOP_SEITEN, TOP_SUCHBEGRIFFE):
        rel = f"{GSC.as_posix()}/{name}"
        text = _git(wurzel, "show", f"{sha}:{rel}")
        if not text:
            return [f"⛔ {rel} existiert in {sha[:12]} nicht – kein Gesamtstand, "
                    f"keine Heilung"], pruefe_alle(wurzel)
        hinweis = pruefe_text(text, name)
        if hinweis:
            return [f"⛔ {rel} besteht in {sha[:12]} die Prüfung nicht ({hinweis[0]}) – "
                    f"kein Gesamtstand, keine Heilung"], pruefe_alle(wurzel)
        kandidaten.append((wurzel / rel, text))
    bericht = [f"🔧 Gesamtstand {sha[:12]}: {META} + beide Top-Listen werden gemeinsam gesetzt "
               f"(der Tagesledger bleibt unverändert)"]
    for ziel, text in kandidaten:
        alt = ziel.read_text(encoding="utf-8") if ziel.exists() else ""
        ziel.write_text(text, encoding="utf-8")
        nachher = pruefe_datei(ziel)
        if nachher:
            ziel.write_text(alt, encoding="utf-8")
            bericht.append(f"⛔ {ziel.name}: Prüfung nach dem Schreiben rot ({nachher[0]}) – "
                           f"Datei unverändert gelassen")
    return bericht, pruefe_alle(wurzel)


# ------------------------------------------------------------------- Ausgabe

def als_markdown(funde: list[Fund], wurzel: Path | None = None) -> str:
    wurzel = wurzel or ROOT
    zeilen = ["### 🛰️ GSC-Artefakte (Wache über die Search-Console-Daten)", ""]
    if not funde:
        zeilen.append("✅ Alle vier Artefakte sind gültig, eindeutig und zueinander passend.")
        return "\n".join(zeilen) + "\n"
    zeilen.append(f"🛑 **{len(funde)} Fund(e)** in `{GSC.as_posix()}/`")
    zeilen.append("")
    zeilen.append("| Prüfung | Datei | Befund |")
    zeilen.append("|---|---|---|")
    for f in funde:
        zeilen.append(f"| {f.pruefung} | `{f.datei}` | {f.meldung.replace('|', '/')} |")
    zeilen.append("")
    zeilen.append(f"Reparatur: `{HEILUNG}` (holt den letzten belegbar gültigen "
                  f"Git-Stand; erfindet nichts).")
    return "\n".join(zeilen) + "\n"


# ------------------------------------------------------------------ Selbsttest

def _fixture_meta(**aenderungen) -> dict:
    meta = {
        "stand": "2026-10-20T10:01:45Z",
        "quelle": "google-search-console-api (Dienstkonto, nur lesen)",
        "site": "sc-domain:franksfinanzcheck.de",
        "zeitraum": {"von": "2026-07-20", "bis": "2026-10-17"},
        "status": "ok",
        "grund": "",
        "datenschutz": "nur aggregierte Kennzahlen je Tag, Seite oder Suchbegriff",
        "tage_neu": 28,
        "tage_gesamt": 28,
        "klicks_zeitraum": 0,
    }
    meta.update(aenderungen)
    return meta


def _fixture_top(dimension: str) -> list[dict]:
    return [
        {dimension: "a", "clicks": 0, "impressions": 3, "ctr": 0.0, "position": 1.67},
        {dimension: "b", "clicks": 0, "impressions": 1, "ctr": 0.0, "position": 9.0},
    ]


def _fixture_ledger(tage: int = 28, ende: dt.date = dt.date(2026, 10, 17)) -> str:
    """28 Tage bis zum Fensterende der Fixture-Meta (tage_gesamt: 28)."""
    return "\n".join(
        json.dumps({"datum": (ende - dt.timedelta(days=off)).isoformat(), "clicks": 0,
                    "impressions": 1, "ctr": 0.0, "position": 5.0})
        for off in range(tage - 1, -1, -1)) + "\n"


def _schreibe_satz(wurzel: Path, meta=None, top_seiten=None,
                   top_suchbegriffe=None, ledger: str | None = None) -> None:
    d = wurzel / GSC
    d.mkdir(parents=True, exist_ok=True)
    (d / META).write_text(json.dumps(meta if meta is not None else _fixture_meta(),
                                     ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (d / TOP_SEITEN).write_text(json.dumps(
        top_seiten if top_seiten is not None else _fixture_top("seite"),
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (d / TOP_SUCHBEGRIFFE).write_text(json.dumps(
        top_suchbegriffe if top_suchbegriffe is not None else _fixture_top("suchbegriff"),
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (d / LEDGER).write_text(ledger if ledger is not None else _fixture_ledger(),
                            encoding="utf-8")


def run_selftest() -> int:
    """Beweist, dass die Wache bei jeder bekannten Defektklasse anschlägt (C15: nur tmp)."""
    faelle: list[tuple[str, list[Fund], str]] = []

    def pruefe(name: str, wurzel: Path, erwartete_pruefung: str | None):
        """erwartete_pruefung: Code wie "G2" · None = muss grün sein."""
        funde = pruefe_alle(wurzel)
        faelle.append((name, funde, "gruen" if erwartete_pruefung is None
                       else erwartete_pruefung))

    with tempfile.TemporaryDirectory() as tmp:
        basis = Path(tmp)

        # 0) Gesunder Satz = grün.
        gesund = basis / "gesund"
        _schreibe_satz(gesund)
        pruefe("gesund", gesund, None)

        # 1) Verkettete meta.json (der reale Schaden vom 21.10.2026).
        schief = basis / "meta-verkettet"
        _schreibe_satz(schief)
        roh = (schief / GSC / META).read_text(encoding="utf-8")
        (schief / GSC / META).write_text(roh.replace(
            '{\n  "stand"', '{\n  "stand": "2026-10-21T10:06:23Z",\n  "stand"', 1),
            encoding="utf-8")
        pruefe("meta-verkettet", schief, "G1")

        # 2) GÜLTIGES JSON, aber zwei Läufe als eine Liste (der Fall, den ein
        #    Text-Merge mit `union` erzeugt – Syntaxprüfung sieht nichts).
        doppelt = basis / "top-doppelt"
        _schreibe_satz(doppelt)
        zwei = _fixture_top("suchbegriff") + _fixture_top("suchbegriff")
        (doppelt / GSC / TOP_SUCHBEGRIFFE).write_text(json.dumps(zwei, indent=2) + "\n",
                                                      encoding="utf-8")
        pruefe("top-doppelt", doppelt, "G2")

        # 3) Pflichtfeld fehlt.
        ohne = basis / "meta-ohne-feld"
        meta = _fixture_meta()
        meta.pop("datenschutz")
        _schreibe_satz(ohne, meta=meta)
        pruefe("meta-ohne-feld", ohne, "G1")

        # 4) ctr außerhalb 0…1 (Zahl aus einem anderen Feld übernommen).
        ctr = basis / "ctr-ausserhalb"
        _schreibe_satz(ctr)
        kaputt = _fixture_top("seite")
        kaputt[0]["ctr"] = 71.0
        (ctr / GSC / TOP_SEITEN).write_text(json.dumps(kaputt, indent=2) + "\n",
                                            encoding="utf-8")
        pruefe("ctr-ausserhalb", ctr, "G2")

        # 5) Ledger mit doppeltem Tag.
        tag_doppelt = basis / "ledger-doppelt"
        _schreibe_satz(tag_doppelt, ledger=_fixture_ledger()
                       + _fixture_ledger().splitlines()[-1] + "\n")
        pruefe("ledger-doppelt", tag_doppelt, "G3")

        # 6) Ledger läuft rückwärts.
        rueck = basis / "ledger-rueckwaerts"
        _schreibe_satz(rueck, ledger="\n".join([
            json.dumps({"datum": "2026-10-17", "clicks": 0, "impressions": 1,
                        "ctr": 0.0, "position": 5.0}),
            json.dumps({"datum": "2026-10-15", "clicks": 0, "impressions": 1,
                        "ctr": 0.0, "position": 5.0}),
        ]) + "\n")
        pruefe("ledger-rueckwaerts", rueck, "G3")

        # 7) Kreuzprüfung: Kopf behauptet ein Fenster hinter dem letzten Tag.
        kreuz = basis / "kreuz"
        _schreibe_satz(kreuz, meta=_fixture_meta(zeitraum={"von": "2026-07-20",
                                                           "bis": "2026-10-29"}))
        pruefe("kreuz", kreuz, "G4")

        # 8) Kreuzprüfung: Kopf behauptet mehr Tage als gemessen.
        mehr = basis / "kreuz-tage"
        _schreibe_satz(mehr, meta=_fixture_meta(tage_neu=30, tage_gesamt=30))
        pruefe("kreuz-tage", mehr, "G4")

        # 9) Leere Top-Liste ist KEIN Fehler (kein Traffic im Fenster).
        leer = basis / "top-leer"
        _schreibe_satz(leer, top_seiten=[])
        pruefe("top-leer", leer, None)

        # 10) Heilung: kaputte Datei, gültiger Stand in der Historie → zurückgeholt.
        repo = basis / "repo-heilbar"
        _schreibe_satz(repo)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        for cmd in (["git", "config", "user.email", "t@example.invalid"],
                    ["git", "config", "user.name", "Selbsttest"],
                    ["git", "add", "-A"],
                    ["git", "commit", "-qm", "gültiger Stand"]):
            subprocess.run(["git", *cmd[1:]], cwd=str(repo), check=True,
                           capture_output=True)
        (repo / GSC / META).write_text('{\n  "stand": "x"\n  "stand": "y"\n  }\n',
                                       encoding="utf-8")
        bericht, rest = heile(repo)
        faelle.append(("heilung-git", [Fund("H", "bericht", b) for b in bericht], "H"))
        faelle.append(("heilung-danach-gruen", rest, "gruen"))

        # 10b) Gesamtstand: alle Kopfdaten aus EINEM Commit – kein Teil-Erfolg.
        gesamt = basis / "repo-gesamtstand"
        _schreibe_satz(gesamt)
        subprocess.run(["git", "init", "-q", str(gesamt)], check=True)
        for cmd in (["config", "user.email", "t@example.invalid"],
                    ["config", "user.name", "Selbsttest"]):
            subprocess.run(["git", *cmd], cwd=str(gesamt), check=True, capture_output=True)
        for i, dimension in enumerate(("seite", "suchbegriff")):
            _schreibe_satz(gesamt, meta=_fixture_meta(stand=f"2026-10-2{i}T10:00:00Z"),
                           top_seiten=_fixture_top("seite"),
                           top_suchbegriffe=_fixture_top("suchbegriff"))
            subprocess.run(["git", "add", "-A"], cwd=str(gesamt), check=True,
                           capture_output=True)
            subprocess.run(["git", "commit", "-qm", f"Lauf {i}"], cwd=str(gesamt),
                           check=True, capture_output=True)
        erster = subprocess.run(["git", "rev-list", "--max-parents=0", "HEAD"],
                                cwd=str(gesamt), capture_output=True, text=True
                                ).stdout.strip()
        # Kopf zerlegt: meta aus Lauf 0 zurückholen, Top-Listen bleiben Lauf 1.
        meta0 = subprocess.run(["git", "show", f"{erster}:{GSC.as_posix()}/{META}"],
                               cwd=str(gesamt), capture_output=True, text=True).stdout
        (gesamt / GSC / META).write_text(meta0.replace("\n  ", "\n  \"stand\": \"x\",\n  ", 1),
                                         encoding="utf-8")
        bericht3, rest3 = heile(gesamt, rev=erster)
        # Lauf 0 hat 28 Tage, der Ledger bleibt der aktuelle → G4 muss passen.
        faelle.append(("gesamtstand-aus-einem-commit",
                       [Fund("H", "b", b) for b in bericht3 if "🔧" in b], "H"))
        faelle.append(("gesamtstand-danach-gruen", rest3, "gruen"))
        # Ein Commit, in dem eine Kopfsdatei kaputt ist, darf NICHTS schreiben.
        (gesamt / GSC / TOP_SEITEN).write_text("[{\"seite\": 1}]", encoding="utf-8")
        subprocess.run(["git", "commit", "-qam", "kaputter Lauf"], cwd=str(gesamt),
                       check=True, capture_output=True)
        kaputter_rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(gesamt),
                                      capture_output=True, text=True).stdout.strip()
        vorher = (gesamt / GSC / META).read_text(encoding="utf-8")
        bericht4, _ = heile(gesamt, rev=kaputter_rev)
        unveraendert = (gesamt / GSC / META).read_text(encoding="utf-8") == vorher
        faelle.append(("gesamtstand-verweigert-bei-kaputtem-glied",
                       [Fund("H", "b", b) for b in bericht4 if "⛔" in b], "H"))
        faelle.append(("gesamtstand-schreibt-kein-teilstueck",
                       [] if unveraendert else [Fund("H", "x", "Teilstand geschrieben")],
                       "gruen"))

        # 10c) Ohne Zugang schreibt der Import nur den Kopf: gültig, kein Fund.
        ohne_zugang = basis / "ohne-zugang"
        (ohne_zugang / GSC).mkdir(parents=True, exist_ok=True)
        (ohne_zugang / GSC / META).write_text(json.dumps(_fixture_meta(
            status="nicht_konfiguriert", tage_neu=None, tage_gesamt=None,
            klicks_zeitraum=None, site=None,
            grund="GSC_SITE_URL fehlt"), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        pruefe("ohne-zugang-nur-kopf", ohne_zugang, None)
        # … aber sobald gemessen wurde, muss die Messung da sein.
        halb = basis / "messung-ohne-listen"
        _schreibe_satz(halb)
        (halb / GSC / TOP_SEITEN).unlink()
        pruefe("messung-ohne-listen", halb, "G2")

        # 11) Heilung verweigert ohne belegbaren Stand (nichts wird erfunden).
        ohne_historie = basis / "repo-unheilbar"
        _schreibe_satz(ohne_historie)
        (ohne_historie / GSC / TOP_SEITEN).write_text("[{\"seite\": \"x\"}]",
                                                      encoding="utf-8")
        bericht2, rest2 = heile(ohne_historie)
        inhalt = (ohne_historie / GSC / TOP_SEITEN).read_text(encoding="utf-8")
        faelle.append(("heilung-ohne-stand-verweigert",
                       [Fund("H", "bericht", b) for b in bericht2 if "⛔" in b] or
                       [Fund("H", "x", "kein Verweigerungshinweis")], "H"))
        faelle.append(("heilung-laesst-unheilbares-unberuehrt",
                       [] if inhalt == "[{\"seite\": \"x\"}]" else
                       [Fund("H", "x", "Datei wurde trotz fehlendem Stand verändert")], "gruen"))

    rot = 0
    for name, funde, erwartet in faelle:
        if erwartet == "gruen":
            ok = not funde
            detail = "grün" if ok else f"{len(funde)} Fund(e): {funde[0]}"
        elif erwartet == "H":
            ok = bool(funde)
            detail = "greift" if ok else "kein Befund (Wache blind)"
        else:
            ok = any(f.pruefung == erwartet for f in funde)
            codes = ", ".join(sorted({f.pruefung for f in funde})) or "grün"
            detail = f"{codes}"
        print(f"  {'✅' if ok else '⛔'} {name}: {detail}")
        rot += 0 if ok else 1
    print(f"{'✅' if not rot else '🛑'} GSC-Artefakt-Wache: "
          f"{len(faelle) - rot}/{len(faelle)} Fälle grün.")
    return 0 if not rot else 2


# ---------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Wache über data/gsc/ (Search Console).")
    ap.add_argument("--check", action="store_true", help="prüfen (Standard)")
    ap.add_argument("--heal", action="store_true", help="belegbaren Git-Stand zurückholen")
    ap.add_argument("--rev", default=None,
                    help="mit --heal: alle Kopfdaten aus EINEM Commit (ein Lauf = eine Messung)")
    ap.add_argument("--selftest", action="store_true", help="Sabotageschutz")
    ap.add_argument("--json", action="store_true", help="Funde maschinenlesbar")
    ap.add_argument("--md", action="store_true", help="Markdown für die Lauf-Summary")
    args = ap.parse_args(argv)

    if args.selftest:
        return run_selftest()

    if args.heal:
        bericht, funde = heile(rev=args.rev)
        for zeile in bericht:
            print(zeile)
        if not bericht:
            print("🔧 Nichts zu heilen – alle Artefakte bestehen die Prüfung.")
        if funde:
            print(f"🛑 {len(funde)} Fund(e) bleiben nach der Heilung:")
            for f in funde:
                print(f"   {f}")
            return 1
        print("✅ data/gsc/ ist nach der Heilung grün.")
        return 0

    funde = pruefe_alle()
    if args.json:
        print(json.dumps({"funde": [f.als_dict() for f in funde]},
                         ensure_ascii=False, indent=2))
        return 0 if not funde else 1
    if args.md:
        print(als_markdown(funde))
        return 0 if not funde else 1
    if not funde:
        print("✅ GSC-Artefakte grün: vier Dateien gültig, eindeutig und zueinander passend.")
        return 0
    print(f"🛑 GSC-ARTEFAKT-WACHE: {len(funde)} Fund(e) in data/gsc/")
    for f in funde:
        print(f"   [{f.pruefung}] {f.datei}: {f.meldung}")
    print(f"   Reparatur: {HEILUNG} – holt den letzten belegbar gültigen Git-Stand.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
