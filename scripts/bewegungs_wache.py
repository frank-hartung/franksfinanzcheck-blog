#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
#  BEWEGUNGS-WACHE – die Easing-/Dauer-/Lift-Skala gilt auch dort,
#  wo kein Varianten-Gate hinsieht.
#  ------------------------------------------------------------
#  WARUM ES DIESE WACHE GIBT (01.11.2026, Audit nach der Aufnahme
#  des Skills `emil-design-eng`)
#
#  DESIGN.md §6 legt drei Zahlen fest (0.16 s Micro, 0.3 s Fläche,
#  cubic-bezier(.2,.7,.2,1) / ease-out) und `data/design/regelwerk.yaml`
#  spiegelt sie maschinenlesbar. Geprüft wurden sie aber NUR in
#  `assets/css/varianten/*.css` – durch `scripts/design_variant_gate.py`.
#  Die Dateien, die WIRKLICH ausgeliefert werden, liegen in
#  `assets/css/extended/*.css` und wurden von keiner Wache gegen die
#  eigene Skala gehalten. Ergebnis der Messung am 01.11.2026:
#
#    · 36 wirksame Übergangsdauern außerhalb der Skala (0.1 s, 0.12 s,
#      0.15 s, 0.2 s, 0.22 s, 0.25 s, 0.4 s, 0.65 s, 0.7 s),
#    · 125 Übergänge mit dem generischen `ease`,
#    · 2× `transition: all` – obwohl genau das die Easing-Entscheidung
#      an eine fremde Deklaration abgibt,
#    · 42 Hover-/Fokus-Lifts ohne `:active`-Gegenstück (Druck-Feedback
#      fehlt an genau den Flächen, die den Lift zeigen),
#    · 3 Layout-Animationen (`width`) – davon ist nur EINE als Ausnahme
#      dokumentiert (DESIGN.md §6: Voice-Progress). Die anderen zwei
#      sind die Voice-Leiste an zweiter Stelle und der Werkzeug-Balken.
#
#  Der Befund ist damit kein Geschmacksurteil, sondern eine Zahl: Was
#  als Vertrag aufgeschrieben ist, wird an der Mehrheit der Flächen
#  nicht eingehalten, weil der Prüfer nur eine Dateisorte kennt.
#
#  WAS DIESE WACHE PRÜFT (rein lesend, ohne Browser)
#  ------------------------------------------------------------
#    B1  Dauer        `transition`-Dauer außerhalb
#                     `marke.uebergang_dauer_s_erlaubt` (Quelle: Regelwerk,
#                     nicht abgetippt) – 0 s ist erlaubt.
#    B2  Easing       Easing außerhalb `marke.easing_erlaubt`. `ease` ist
#                     bewusst KEIN Verstoß (Regelwerk lässt es zu), wird
#                     aber als Hinweis gezählt: Die Skala will
#                     cubic-bezier(.2,.7,.2,1) oder ease-out.
#    B3  All          `transition: all` – die Deklaration entscheidet mit,
#                     welche Eigenschaften animiert werden.
#    B4  Layout       `transition` über width/height/top/left/right/bottom/
#                     margin/padding (DESIGN.md §6/§7), außer der im
#                     Regelwerk dokumentierten Ausnahme.
#    B5  Lift ohne    Eine Regel setzt bei :hover/:focus-within/:focus-visible
#        Druck        einen `transform`-Lift, aber im ganzen Baum gibt es
#                     für denselben Selektor kein `:active`. Ein Lift ohne
#                     Druck-Feedback ist eine halbe Rückmeldung.
#    B6  Ausnahme     Jede Ausnahme in `data/bewegungs_wache_ausnahmen.yaml`
#                     braucht Grund und Frist und muss noch greifen
#                     (veraltete Ausnahme = offenes Tor).
#
#  WARUM DIE WAAGE ZWEI STUFEN HAT
#  ------------------------------------------------------------
#  B1/B4 sind Vertragsbruch (Exit 1), B2/B3/B5 sind Hinweise (Exit 0,
#  solange keine Ausnahme fehlt). Grund: B2 (`ease` statt Kurve) und B5
#  (fehlendes Druck-Feedback) sind Gestaltungsqualität – sie am Tag des
#  Einbaus hart rot zu machen, hieße, die Auslieferung für einen
#  Politur-Grad anzuhalten. B1/B4 dagegen sind Zahlen, die im Regelwerk
#  stehen; wer sie reißt, hat den Vertrag gebrochen, nicht die Form.
#
#  Die Wache läuft NICHT automatisch im Gate (`governance_contract.GUARDS`),
#  solange der Bestand rot ist: Eine Wache, die am ersten Tag 36 Befunde
#  meldet, blockiert jeden Deploy ohne dass jemand etwas verschuldet hat –
#  die Lehre aus dem 19.09.2026 (Issue #316). Aufnahme in `GUARDS` ist der
#  Schritt NACH der Heilung; bis dahin ist sie über
#  `npm run test:bewegung` erreichbar und ihr Selbsttest beweist die Logik.
#
#  NUTZUNG
#    python3 scripts/bewegungs_wache.py                # Bericht (Exit 1 bei B1/B4)
#    python3 scripts/bewegungs_wache.py --nur-hinweise # nie Exit 1 (Bestand)
#    python3 scripts/bewegungs_wache.py --json
#    python3 scripts/bewegungs_wache.py --selftest     # Logik-Beweis, schreibt nie
#
#  EXIT: 0 = grün · 1 = Vertragsbruch (B1/B4) · 2 = der Prüfer selbst ist defekt
# ============================================================
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

BLOG_DIR = Path(__file__).resolve().parent.parent
CSS_KORPUS = ("assets/css/extended", "assets/css/varianten")
REGELWERK = BLOG_DIR / "data" / "design" / "regelwerk.yaml"
# Über BEWEGUNGS_AUSNAHMEN überschreibbar: Der Selbsttest und die Tests
# müssen die AUSNAHME-Logik prüfen können, auch wenn im Repo (absichtlich)
# keine Ausnahme steht. Eine Datei, die man nur im Ernstfall testen kann,
# wird im Ernstfall zum ersten Mal getestet.
AUSNAHMEN = Path(os.environ.get("BEWEGUNGS_AUSNAHMEN",
                                BLOG_DIR / "data" / "bewegungs_wache_ausnahmen.yaml"))

# Was ein Korpus mindestens enthalten muss. Eine Wache, die 0 Dateien
# geprüft hat, ist nicht grün, sondern blind (Lehre aus Meldung #900:
# „ein Audit über 0 Seiten meldete alle Checks OK").
MIN_DATEIEN = 10

LAYOUT_EIGENSCHAFTEN = ("width", "height", "top", "left", "right", "bottom",
                        "margin", "padding")
# Keine Layout-Animation (DESIGN.md §6/§7) – AUSSER den Fällen, die
# DESIGN.md §6.1 namentlich nennt. Die Liste steht maschinenlesbar in
# `marke.layout_animation_ausnahmen` (regelwerk.yaml), damit es keine
# zweite Wahrheit im Code gibt: Wer eine Ausnahme will, schreibt sie dorthin
# – mit Grund – und der Mensch liest sie in §6.1.
LAYOUT_AUSNAHMEN_SCHLUESSEL = "layout_animation_ausnahmen"

BEFUND_KLASSEN = {
    "B1": "Dauer außerhalb der Skala",
    "B3": "transition: all",
    "B4": "Layout-Eigenschaft animiert",
}
HINWEIS_KLASSEN = {
    "B2": "Easing außerhalb der Skala (Hinweis)",
    "B5": "Lift ohne Druck-Feedback (Hinweis)",
}


@dataclass(frozen=True)
class Fund:
    klasse: str
    pfad: str
    zeile: int
    selektor: str
    meldung: str

    def kurz(self) -> str:
        return f"[{self.klasse}] {self.pfad}:{self.zeile} {self.selektor} – {self.meldung}"


@dataclass(frozen=True)
class Regel:
    """Ein CSS-Block: Kopf, Rumpf, Zeile, umgebende @media-Klammern."""
    selektor: str
    rumpf: str
    zeile: int
    medien: str


# ------------------------------------------------------------------ Lesen
def ohne_kommentare(text: str) -> str:
    """Kommentare entfernen, Zeilenzahl erhalten (Zeilenangaben bleiben wahr)."""
    return re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)


def regeln(css: str) -> list[Regel]:
    """Blöcke lesen – zeilenweise, ohne rückverfolgendes Muster über den
    ganzen Text (Kern-Regel 6: keine katastrophale Rückverfolgung)."""
    ergebnis: list[Regel] = []
    medien: list[str] = []
    puffer = ""
    i, zeile, n = 0, 1, len(css)
    while i < n:
        zeichen = css[i]
        if zeichen == "\n":
            zeile += 1
        if zeichen == "{":
            kopf = puffer.strip()
            if kopf.startswith(("@media", "@supports", "@layer")):
                medien.append(kopf)
                puffer = ""
                i += 1
                continue
            ende = i + 1
            tiefe = 1
            while ende < n and tiefe:
                if css[ende] == "{":
                    tiefe += 1
                elif css[ende] == "}":
                    tiefe -= 1
                ende += 1
            ergebnis.append(Regel(kopf, css[i + 1:ende - 1], zeile, " ".join(medien)))
            zeile += css[i:ende].count("\n")
            i = ende
            puffer = ""
            continue
        if zeichen == "}":
            if medien:
                medien.pop()
            puffer = ""
            i += 1
            continue
        puffer += zeichen
        i += 1
    return ergebnis


def dekorationen(rumpf: str, name: str) -> list[str]:
    """Werte EINER Eigenschaft im Rumpf (`transition`, `animation`)."""
    return re.findall(rf"(?:^|[;\s]){name}\s*:\s*([^;}}]*)", rumpf)


_DAUER = re.compile(r"(?<![\w.-])(\d*\.?\d+)(ms|s)\b")
_EASING = re.compile(r"\b(ease-in-out|ease-in|ease-out|ease|linear|"
                     r"cubic-bezier\([^)]*\)|steps\([^)]*\))")


def dauern(dekoration: str) -> list[float]:
    return [round(float(zahl) / (1000 if einheit == "ms" else 1), 4)
            for zahl, einheit in _DAUER.findall(dekoration)]


def easings(dekoration: str) -> list[str]:
    return [re.sub(r"\s+", "", e) for e in _EASING.findall(dekoration)]


def einstieg(selektor: str) -> str:
    """Der Selektor ohne die Zustands-Pseudo-Klasse – die Kennung einer
    Fläche, an der Druck-Feedback hängen müsste."""
    basis = re.sub(r"::?(hover|focus-visible|focus-within|focus|active)\b", "", selektor)
    return re.sub(r"\s+", " ", basis).strip()


# ------------------------------------------------------------------ Regeln laden
def _skala_aus_yaml(text: str) -> tuple[set[float], set[str]]:
    """Erster Leser: echtes YAML. Wirft ImportError, wenn PyYAML fehlt."""
    import yaml  # type: ignore

    daten = yaml.safe_load(text) or {}
    marke = daten.get("marke") or {}
    dauern = {round(float(w), 4) for w in marke.get("uebergang_dauer_s_erlaubt") or []}
    kurven = {re.sub(r"\s+", "", str(k)).lower() for k in marke.get("easing_erlaubt") or []}
    return dauern, kurven


def _yaml_liste(text: str, schluessel: str) -> list[str]:
    """Zweiter Leser für EINE Liste – beide YAML-Schreibweisen.

    Blockform (`schluessel:` + eingerückte `- wert`) und Inline-Form
    (`schluessel: [a, b]`). Die Blockform ist der Grund, warum es diesen
    Leser überhaupt gibt: `easing_erlaubt` steht so im Regelwerk, und ein
    Leser, der nur `[...]` kennt, findet dort nichts.
    """
    zeilen = text.splitlines()
    for nummer, zeile in enumerate(zeilen):
        treffer = re.match(rf"^(\s*){re.escape(schluessel)}\s*:\s*(.*)$", zeile)
        if not treffer:
            continue
        einrueckung, rest = len(treffer.group(1)), treffer.group(2).strip()
        if rest.startswith("["):
            # Inline-Form, ggf. über mehrere Zeilen umbrochen.
            gesamt = rest
            folge = nummer + 1
            while "]" not in gesamt and folge < len(zeilen):
                gesamt += " " + zeilen[folge].split("#", 1)[0].strip()
                folge += 1
            inhalt = gesamt[gesamt.index("[") + 1:gesamt.rfind("]")] if "]" in gesamt else gesamt[1:]
            return [t.strip().strip("\"'") for t in inhalt.split(",") if t.strip()]
        werte = []
        for folge in zeilen[nummer + 1:]:
            if not folge.strip() or folge.strip().startswith("#"):
                continue
            eintrag = re.match(r"^(\s*)-\s*(.+?)\s*$", folge)
            if not eintrag or len(eintrag.group(1)) <= einrueckung:
                break
            werte.append(eintrag.group(2).strip().strip("\"'"))
        return werte
    return []


def _skala_rueckfall(text: str) -> tuple[set[float], set[str]]:
    """Zweiter Leser ohne Abhängigkeit – dieselben Zahlen, andere Mittel."""
    dauern = {round(float(w), 4)
              for w in _yaml_liste(text, "uebergang_dauer_s_erlaubt")}
    kurven = {re.sub(r"\s+", "", k).lower() for k in _yaml_liste(text, "easing_erlaubt")}
    return dauern, kurven


def layout_ausnahmen(regelwerk: Path) -> list[dict]:
    """Die dokumentierten Ausnahmen von „keine Layout-Animation" (DESIGN.md §6.1)."""
    text = regelwerk.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
        daten = yaml.safe_load(text) or {}
        roh = (daten.get("marke") or {}).get(LAYOUT_AUSNAHMEN_SCHLUESSEL) or []
        return [e for e in roh if isinstance(e, dict) and str(e.get("selektor") or "").strip()]
    except ImportError:
        pass
    return [e for e in _yaml_block(text, LAYOUT_AUSNAHMEN_SCHLUESSEL)
            if str(e.get("selektor") or "").strip()]


def skala(regelwerk: Path) -> tuple[set[float], set[str]]:
    """Dauer- und Easing-Skala aus dem Regelwerk lesen – eine Wahrheit.

    Zwei Leser, ein Ergebnis: PyYAML (CI) und der Rückfallleser (nackter
    Sandkasten). Fehlt eine der beiden Listen, ist das ein Fehler und keine
    leere Skala – eine leere Skala würde jedes `transition` als Verstoß
    melden und wäre damit ein Totalalarm statt einer Prüfung.
    """
    text = regelwerk.read_text(encoding="utf-8")
    try:
        dauern, kurven = _skala_aus_yaml(text)
    except ImportError:
        dauern, kurven = _skala_rueckfall(text)
    if not dauern or not kurven:
        raise ValueError("marke.uebergang_dauer_s_erlaubt / easing_erlaubt nicht "
                         f"lesbar (Dauern {sorted(dauern)}, Kurven {sorted(kurven)})")
    return dauern, kurven


def _rel(pfad: Path) -> str:
    """Anzeigepfad – auch für Dateien außerhalb des Repos (Selbsttest)."""
    try:
        return pfad.resolve().relative_to(BLOG_DIR).as_posix()
    except ValueError:
        return pfad.name


def _yaml_block(text: str, schluessel: str) -> list[dict]:
    """Eine YAML-Blockliste von Objekten lesen – ohne PyYAML.

    Deckt genau die Form, die dieses Repo in `bewegungs_wache_ausnahmen.yaml`
    und `marke.layout_animation_ausnahmen` benutzt:

        schluessel:
          - pfad: a.css          # Schlüssel direkt am Bindestrich
            grund: >             # mehrzeiliger Textblock
              Satz eins.
              Satz zwei.
            faellig: 2026-12-31  # Schlüssel auf Eintragsebene

    Was dieser Leser nicht versteht, fällt weg. Das ist die sichere Richtung:
    eine nicht gelesene Ausnahme lässt den Befund stehen, statt eine
    unbelegte Freigabe zu erzeugen. Die Rückfallliste ist nötig, weil der
    CI-Runner PyYAML hat, ein nackter Sandkasten aber nicht – und eine Wache,
    die dort blind ist, meldet dort Unsinn.
    """
    zeilen = text.splitlines()
    beginn = None
    for nummer, roh in enumerate(zeilen):
        treffer = re.match(rf"^(\s*){re.escape(schluessel)}\s*:\s*(.*)$", roh)
        if treffer:
            if treffer.group(2).strip() == "[]":
                return []
            beginn = nummer + 1
            basis = len(treffer.group(1))
            break
    if beginn is None:
        return []

    eintraege: list[dict] = []
    aktuell: dict | None = None
    block_schluessel: str | None = None
    block: list[str] = []
    block_einrueckung = 0

    def block_abschliessen() -> None:
        nonlocal block_schluessel, block
        if aktuell is not None and block_schluessel:
            aktuell[block_schluessel] = " ".join(block).strip()
        block_schluessel, block = None, []

    def abschliessen() -> None:
        nonlocal aktuell
        block_abschliessen()
        if aktuell is not None:
            eintraege.append(aktuell)
        aktuell = None

    for roh in zeilen[beginn:]:
        if not roh.strip() or roh.strip().startswith("#"):
            continue
        if len(roh) - len(roh.lstrip()) <= basis and not roh.lstrip().startswith("-"):
            break  # Liste zu Ende (nächster Schlüssel auf gleicher Ebene)
        inhalt = roh.split("#", 1)[0].rstrip()
        if block_schluessel is not None:
            if len(inhalt) - len(inhalt.lstrip()) > block_einrueckung:
                block.append(inhalt.strip())
                continue
            block_abschliessen()
        start_eintrag = re.match(r"^(\s*)-\s*(.*)$", inhalt)
        if start_eintrag:
            abschliessen()
            aktuell = {}
            rest = start_eintrag.group(2).strip()
            if rest:
                schluessel_teil, _, wert = rest.partition(":")
                if wert.strip() in (">", "|", ">-", "|-"):
                    block_schluessel = schluessel_teil.strip()
                    block = []
                    block_einrueckung = len(inhalt) - len(inhalt.lstrip())
                else:
                    aktuell[schluessel_teil.strip()] = wert.strip().strip("\"'")
            continue
        if aktuell is None:
            continue
        treffer = re.match(r"^\s+([A-Za-z_][\w-]*)\s*:\s*(.*)$", inhalt)
        if not treffer:
            continue
        schluessel_teil, wert = treffer.group(1), treffer.group(2).strip()
        if wert in (">", "|", ">-", "|-"):
            block_schluessel = schluessel_teil
            block = []
            block_einrueckung = len(inhalt) - len(inhalt.lstrip())
        else:
            aktuell[schluessel_teil] = wert.strip("\"'")
    abschliessen()
    return eintraege


def _pruefe_ausnahmen(eintraege, rel: str, stichtag: datetime.date) -> tuple[list[dict], list[Fund]]:
    """Eine Logik für beide Leser: Grund, Frist, und ob die Frist noch läuft."""
    funde: list[Fund] = []
    if not isinstance(eintraege, list):
        return [], [Fund("B6", rel, 0, "-", "`ausnahmen` ist keine Liste.")]
    sauber: list[dict] = []
    for nummer, eintrag in enumerate(eintraege, 1):
        stelle = f"Eintrag {nummer}"
        if not isinstance(eintrag, dict):
            funde.append(Fund("B6", rel, nummer, stelle,
                              "kein Objekt – kein Grund, keine Frist."))
            continue
        alle_pflichten_da = True
        for pflicht in ("pfad", "grund", "faellig"):
            if not str(eintrag.get(pflicht) or "").strip():
                alle_pflichten_da = False
                funde.append(Fund("B6", rel, nummer, stelle,
                                  f"ohne `{pflicht}` – eine Ausnahme ohne {pflicht} "
                                  "ist eine stille Abschaffung."))
        faellig = str(eintrag.get("faellig") or "").strip()
        if faellig:
            try:
                datum = datetime.date.fromisoformat(faellig)
            except ValueError:
                alle_pflichten_da = False
                funde.append(Fund("B6", rel, nummer, stelle,
                                  f"`faellig: {faellig}` ist kein ISO-Datum (JJJJ-MM-TT)."))
            else:
                if datum < stichtag:
                    funde.append(Fund("B6", rel, nummer, stelle,
                                      f"Frist {faellig} ist abgelaufen – die Ausnahme "
                                      "verlängert sich nicht von selbst."))
                elif str(eintrag.get("grund") or "").strip() and \
                        not str(eintrag.get("entscheidung") or "").strip():
                    funde.append(Fund("B6", rel, nummer, stelle,
                                      "ohne `entscheidung` – wer hat sie beschlossen? "
                                      "Eine Frist ohne Entscheidung ist ein Aufschub."))
        if alle_pflichten_da:
            sauber.append(eintrag)
    return sauber, funde


def ausnahmen(pfad: Path, stichtag: datetime.date) -> tuple[list[dict], list[Fund]]:
    """Ausnahmen lesen: Grund, Frist, und ob sie noch greifen."""
    if not pfad.is_file():
        return [], []
    rel = _rel(pfad)
    try:
        import yaml  # type: ignore
        daten = yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}
    except ImportError:
        return _pruefe_ausnahmen(_yaml_block(pfad.read_text(encoding="utf-8"), "ausnahmen"),
                                 rel, stichtag)
    return _pruefe_ausnahmen(daten.get("ausnahmen") or [], rel, stichtag)


def pruefe_baum(wurzel: Path, erlaubte_dauern: set[float],
                erlaubte_kurven: set[str], ausnahme_liste: list[dict],
                dateien: list[Path] | None = None,
                layout_frei: list[str] | None = None) -> tuple[list[Fund], list[Fund], int]:
    """B1–B5 über einen CSS-Baum. Gibt (Befunde, Hinweise, Dateizahl)."""
    pfade = dateien or [p for ordner in CSS_KORPUS
                        for p in sorted((wurzel / ordner).glob("*.css"))]
    ausnahmen_keys = {(str(a.get("pfad") or "").strip(), str(a.get("klasse") or "").strip())
                      for a in ausnahme_liste}
    befunde: list[Fund] = []
    hinweise: list[Fund] = []
    gesehen: set[tuple[str, str]] = set()
    aktive_selektoren: dict[str, list[str]] = {}

    for pfad in pfade:
        rel = pfad.relative_to(wurzel).as_posix() if pfad.is_relative_to(wurzel) else pfad.name
        bloecke = regeln(ohne_kommentare(pfad.read_text(encoding="utf-8", errors="replace")))
        for block in bloecke:
            sel = re.sub(r"\s+", " ", block.selektor).strip()
            for wert in dekorationen(block.rumpf, "transition"):
                for dauer in dauern(wert):
                    if dauer in erlaubte_dauern or dauer == 0.0:
                        continue
                    if (rel, "B1") in ausnahmen_keys:
                        continue
                    befunde.append(Fund(
                        "B1", rel, block.zeile, sel[:70],
                        f"Dauer {dauer:g}s ist nicht Teil der Skala "
                        f"{sorted(erlaubte_dauern)} (DESIGN.md §6, "
                        "data/design/regelwerk.yaml)."))
                for kurve in easings(wert):
                    if kurve.lower() in erlaubte_kurven:
                        continue
                    hinweise.append(Fund(
                        "B2", rel, block.zeile, sel[:70],
                        f"Easing `{kurve}` ist nicht die Haus-Kurve "
                        f"{sorted(erlaubte_kurven)} – der Standard-Ton "
                        "trifft die Absicht selten."))
                if re.search(r"(?:^|[\s,])all(?:[\s,]|$)", wert):
                    hinweise.append(Fund(
                        "B3", rel, block.zeile, sel[:70],
                        "`transition: all` – die Eigenschaftsliste entscheidet "
                        "mit; nenne transform/opacity/color explizit."))
                for eigenschaft in LAYOUT_EIGENSCHAFTEN:
                    if not re.search(rf"(?:^|[\s,]){eigenschaft}(?:\s|,|$)", wert):
                        continue
                    if any(muster in sel for muster in (layout_frei or ())):
                        continue  # DESIGN.md §6.1: namentlich dokumentierte Ausnahme
                    if (rel, "B4") in ausnahmen_keys:
                        continue
                    befunde.append(Fund(
                        "B4", rel, block.zeile, sel[:70],
                        f"Layout-Eigenschaft `{eigenschaft}` animiert – "
                        "erzwingt Reflow (DESIGN.md §6/§7)."))
            if re.search(r":(hover|focus-visible|focus-within)\b", sel) \
                    and "prefers-reduced-motion" not in block.medien \
                    and re.search(r"(?:^|[;\s])transform\s*:", block.rumpf):
                aktive_selektoren.setdefault(rel, []).append(einstieg(sel))
        for block in bloecke:
            sel = re.sub(r"\s+", " ", block.selektor).strip()
            if ":active" in sel:
                gesehen.add((rel, einstieg(sel)))

    for rel, kandidaten in aktive_selektoren.items():
        for kandidat in kandidaten:
            if (rel, kandidat) in gesehen:
                continue
            if (rel, "B5") in ausnahmen_keys:
                continue
            if CSS_HAT_AKTIV.get(kandidat):
                continue
            hinweise.append(Fund(
                "B5", rel, 0, kandidat[:70],
                "Lift bei :hover/:focus, aber kein `:active` im Baum – "
                "beim Drücken fehlt die Rückmeldung (transform: scale(.97))."))
    return befunde, hinweise, len(pfade)


# Selektoren, deren :active-Ableitung in einer ANDEREN Datei steht als der
# Lift (z. B. Lift in z-premium-blog.css, Druck in zzz-agency-polish.css).
# Bewusst leer: Die Wache sucht dateiübergreifend; bleibt ein Eintrag nötig,
# gehört er mit Grund in die Ausnahmedatei, nicht in diesen Set.
CSS_HAT_AKTIV: dict[str, bool] = {}


def sortiere_nach_datei(funde: list[Fund]) -> list[Fund]:
    """Sortieren UND doppelte Meldungen zusammenlegen.

    Ein `transition`-Kurzschreibweise nennt mehrere Eigenschaften mit je einer
    Dauer (`transform .15s ease, box-shadow .15s ease`). Ohne Zusammenlegung
    stünde derselbe Verstoß zweimal im Bericht – und eine Zahl, die doppelt
    zählt, ist keine Messung.
    """
    einzig: dict[tuple, Fund] = {}
    for fund in funde:
        einzig.setdefault((fund.klasse, fund.pfad, fund.zeile, fund.selektor, fund.meldung), fund)
    return sorted(einzig.values(), key=lambda f: (f.pfad, f.zeile, f.klasse, f.selektor))


# ------------------------------------------------------------------ Selbsttest
def selbsttest() -> int:
    import tempfile

    fehler: list[str] = []
    ok = 0

    def pruefe(name: str, bedingung: bool, detail: str = "") -> None:
        nonlocal ok
        if bedingung:
            ok += 1
        else:
            fehler.append(f"{name}{f' – {detail}' if detail else ''}")

    skala_dauer = {0.16, 0.18, 0.3}
    skala_kurve = {"ease-out", "linear", "cubic-bezier(.2,.7,.2,1)"}

    def lauf(css_text: str, dateiname: str = "probe.css") -> tuple[list[Fund], list[Fund]]:
        with tempfile.TemporaryDirectory() as tmp:
            ordner = Path(tmp) / "assets" / "css" / "extended"
            ordner.mkdir(parents=True)
            (ordner / dateiname).write_text(css_text, encoding="utf-8")
            for i in range(MIN_DATEIEN - 1):
                (ordner / f"leer{i}.css").write_text(".x{color:red}\n", encoding="utf-8")
            return pruefe_baum(Path(tmp), skala_dauer, skala_kurve, [])[:2]

    # 1) Saubere Datei → nichts
    b, h = lauf(".a { transition: transform .16s cubic-bezier(.2,.7,.2,1); }\n"
                ".a:hover { transform: translateY(-2px); }\n"
                ".a:active { transform: scale(.97); }\n")
    pruefe("L1 saubere Datei bleibt grün", not b, [f.meldung for f in b])
    pruefe("L2 saubere Datei erzeugt keinen Hinweis", not h, [f.meldung for f in h])

    # 2) Dauer außerhalb der Skala → B1
    b, _ = lauf(".a { transition: transform .2s ease; }")
    pruefe("L3 fremde Dauer wird als B1 gemeldet",
           [f.klasse for f in b] == ["B1"], [f.klasse for f in b])
    pruefe("L4 Meldung nennt den Wert", any(".2s" in f.meldung or "0.2s" in f.meldung for f in b))

    # 3) 0 s ist erlaubt (Abschalten ist keine Bewegung)
    b, _ = lauf(".a { transition: none; }\n.b { transition: transform 0s; }")
    pruefe("L5 Dauer 0 gilt nicht als Verstoß", not b, [f.meldung for f in b])

    # 4) `all` → Hinweis B3, nicht Befund
    b, h = lauf(".a { transition: all .16s ease; }")
    pruefe("L6 `transition: all` ist ein Hinweis",
           not b and any(f.klasse == "B3" for f in h), [f.klasse for f in h])

    # 5) Layout-Eigenschaft → B4
    b, _ = lauf(".a { transition: left .16s ease; }")
    pruefe("L7 animiertes `left` ist B4", [f.klasse for f in b] == ["B4"])

    # 6) Nur die in DESIGN.md §6.1 genannten Selektoren dürfen Layout animieren
    frei = [".ff-voice-progress"]
    with tempfile.TemporaryDirectory() as tmp:
        ordner = Path(tmp) / "assets" / "css" / "extended"
        ordner.mkdir(parents=True)
        (ordner / "probe.css").write_text(
            ".ff-voice-progress { transition: width .18s linear; }\n"
            ".ff-wz__balken-fuellung { transition: width .3s linear; }\n",
            encoding="utf-8")
        for i in range(MIN_DATEIEN - 1):
            (ordner / f"leer{i}.css").write_text(".x{color:red}\n", encoding="utf-8")
        b, _, _ = pruefe_baum(Path(tmp), skala_dauer, skala_kurve, [], layout_frei=frei)
    pruefe("L8 dokumentierte Layout-Ausnahme bleibt erlaubt",
           not [f for f in b if ".ff-voice-progress" in f.selektor], [f.selektor for f in b])
    pruefe("L8b nicht gelistete Layout-Animation ist B4",
           [f.klasse for f in b] == ["B4"], [f.klasse for f in b])

    # 7) Lift ohne Druck → Hinweis B5; mit `:active` → still
    _, h = lauf(".karte:hover { transform: translateY(-2px); }\n")
    pruefe("L9 Lift ohne :active ist ein Hinweis",
           any(f.klasse == "B5" for f in h), [f.klasse for f in h])
    _, h = lauf(".karte:hover { transform: translateY(-2px); }\n"
                ".karte:active { transform: scale(.98); }\n")
    pruefe("L10 Lift mit :active bleibt still",
           not [f for f in h if f.klasse == "B5"], [f.klasse for f in h])

    # 8) Kommentare zählen nicht (auskommentierte Regel ist keine Regel)
    b, h = lauf("/* .a { transition: all .7s left; } */\n.b { color: red; }")
    pruefe("L11 auskommentiertes CSS wird nicht geprüft", not b and not h,
           [f.meldung for f in b + h])

    # 9) Zeilenangabe bleibt trotz Kommentarblock wahr
    b, _ = lauf("/*\n * Kopf\n */\n.a { transition: transform .9s ease; }\n")
    pruefe("L12 Zeilenangabe zählt Kommentarzeilen mit",
           bool(b) and b[0].zeile == 4, [str(f.zeile) for f in b])

    # 10) @media-Kontext wird gelesen, nicht verschluckt
    b, _ = lauf("@media (min-width: 700px) {\n  .a { transition: transform .24s ease; }\n}\n")
    pruefe("L13 Regel in @media wird weiter geprüft", [f.klasse for f in b] == ["B1"])

    # 11) Kurve außerhalb der Skala → Hinweis B2
    _, h = lauf(".a { transition: transform .16s ease-in; }")
    pruefe("L14 fremde Kurve ist ein Hinweis B2",
           any(f.klasse == "B2" for f in h), [f.klasse for f in h])

    # 12) Ausnahmen: fehlende Frist ist ein Befund, abgelaufene auch
    with tempfile.TemporaryDirectory() as tmp:
        datesi = Path(tmp) / "ausnahmen.yaml"
        datesi.write_text(
            "ausnahmen:\n"
            "  - pfad: a.css\n"
            "    klasse: B1\n"
            "    grund: Altbestand\n"
            "    faellig: 2026-12-31\n"
            "  - pfad: b.css\n"
            "    klasse: B1\n",
            encoding="utf-8")
        sauber, funde = ausnahmen(datesi, datetime.date(2026, 11, 1))
        pruefe("L15 vollständige Ausnahme ist sauber", len(sauber) == 1)
        pruefe("L16 Ausnahme ohne Frist ist ein Befund",
               any("faellig" in f.meldung for f in funde), [f.meldung for f in funde])
        _, funde = ausnahmen(datesi, datetime.date(2027, 1, 1))
        pruefe("L17 abgelaufene Frist ist ein Befund",
               any("abgelaufen" in f.meldung for f in funde), [f.meldung for f in funde])

    # 13) Beide Leser liefern dasselbe – geprüft am ECHTEN Regelwerk, ohne
    #     sich darauf zu verlassen, ob PyYAML in dieser Umgebung da ist.
    with tempfile.TemporaryDirectory() as tmp:
        rw = Path(tmp) / "regelwerk.yaml"
        rw.write_text("marke:\n  uebergang_dauer_s_erlaubt: [0.16, 0.3]\n"
                      "  easing_erlaubt:\n    - \"ease-out\"\n    - \"cubic-bezier(.2,.7,.2,1)\"\n",
                      encoding="utf-8")
        werte, kurven = skala(rw)
        pruefe("L18 Skala wird aus dem Regelwerk gelesen",
               werte == {0.16, 0.3} and "ease-out" in kurven, f"{werte} {kurven}")
        rueck = _skala_rueckfall(rw.read_text(encoding="utf-8"))
        pruefe("L18a Rückfallleser liest die Blockliste `easing_erlaubt`",
               rueck[1] == kurven, f"Rückfall {rueck[1]} vs. YAML {kurven}")
        try:
            yaml_leser = _skala_aus_yaml(rw.read_text(encoding="utf-8"))
        except ImportError:
            yaml_leser = None
        pruefe("L18b beide Leser sind sich einig",
               yaml_leser is None or yaml_leser == rueck, f"{yaml_leser} vs {rueck}")

    # 13b) Ausnahmedatei OHNE PyYAML lesbar (dieser Fall ist real: der
    #      Sandkasten hat kein yaml, der CI-Runner schon)
    with tempfile.TemporaryDirectory() as tmp:
        datesi = Path(tmp) / "ausnahmen.yaml"
        datesi.write_text(
            "ausnahmen:\n"
            "  - pfad: a.css\n"
            "    klasse: B1\n"
            "    grund: >\n"
            "      Zwei Zeilen Grund,\n"
            "      die zusammengehören.\n"
            "    entscheidung: \"Mensch, 01.11.2026\"\n"
            "    faellig: 2026-12-31\n",
            encoding="utf-8")
        roh = _yaml_block(datesi.read_text(encoding="utf-8"), "ausnahmen")
        pruefe("L18d Rückfallleser liest die Ausnahmen (Block-Grund)",
               len(roh) == 1 and "zusammengehören" in roh[0].get("grund", ""), str(roh))
        sauber, funde = _pruefe_ausnahmen(roh, "x.yaml", datetime.date(2026, 11, 1))
        pruefe("L18e Rückfall-Ausnahme ist gültig", len(sauber) == 1 and not funde,
               [f.meldung for f in funde])

    # 13c) Eine Ausnahme ohne `entscheidung` ist ein Aufschub, kein Beschluss
    sauber, funde = _pruefe_ausnahmen(
        [{"pfad": "a.css", "grund": "x", "faellig": "2026-12-31"}],
        "x.yaml", datetime.date(2026, 11, 1))
    pruefe("L18f Ausnahme ohne Entscheidung wird gemeldet",
           any("entscheidung" in f.meldung for f in funde), [f.meldung for f in funde])

    # 14) Fehlt eine Liste, ist das ein Fehler – keine leere Skala
    with tempfile.TemporaryDirectory() as tmp:
        kaputt = Path(tmp) / "kaputt.yaml"
        kaputt.write_text("marke:\n  uebergang_dauer_s_erlaubt: [0.16]\n", encoding="utf-8")
        try:
            skala(kaputt)
            pruefe("L18c fehlende Easing-Liste ist ein Fehler", False, "keine Ausnahme")
        except ValueError:
            pruefe("L18c fehlende Easing-Liste ist ein Fehler", True)

    # 14) Leerer Baum ist ein Fehler, keine Entwarnung
    with tempfile.TemporaryDirectory() as tmp:
        pfade = list((Path(tmp) / "assets").rglob("*.css")) if (Path(tmp) / "assets").exists() else []
        pruefe("L19 leerer Bestand ergibt 0 Dateien (Aufrufer muss meckern)",
               len(pfade) == 0)

    if fehler:
        print(f"🛑 BEWEGUNGS-WACHE SELBSTTEST: {len(fehler)} von {ok + len(fehler)} Fällen rot")
        for name in fehler:
            print(f"   ✗ {name}")
        return 2
    print(f"✅ BEWEGUNGS-WACHE SELBSTTEST: {ok} Fälle grün")
    return 0


# ------------------------------------------------------------------ Lauf
def main(argv: list[str] | None = None) -> int:
    zerleger = argparse.ArgumentParser(
        description="Prüft die ausgelieferten Stylesheets gegen die Easing-/"
                    "Dauer-Skala aus DESIGN.md §6 und data/design/regelwerk.yaml.")
    zerleger.add_argument("--selftest", action="store_true", help="Logik-Beweis ohne Schreibzugriff")
    zerleger.add_argument("--json", action="store_true", help="Bericht als JSON")
    zerleger.add_argument("--nur-hinweise", action="store_true",
                          help="nie Exit 1 (Bestandslauf, z. B. im Gate vor der Heilung)")
    zerleger.add_argument("--stichtag", default=None,
                          help="JJJJ-MM-TT für die Fristprüfung (Default: heute)")
    args = zerleger.parse_args(argv)

    if args.selftest:
        return selbsttest()

    stichtag = datetime.date.today()
    if args.stichtag:
        try:
            stichtag = datetime.date.fromisoformat(args.stichtag)
        except ValueError:
            print(f"🛑 --stichtag {args.stichtag!r} ist kein ISO-Datum.")
            return 2

    if not REGELWERK.is_file():
        print(f"🛑 Regelwerk fehlt: {REGELWERK}")
        return 2
    try:
        erlaubte_dauern, erlaubte_kurven = skala(REGELWERK)
    except (ValueError, OSError) as fehler:
        print(f"🛑 Skala nicht lesbar: {fehler}")
        return 2

    ausnahme_liste, ausnahme_funde = ausnahmen(AUSNAHMEN, stichtag)
    try:
        layout_frei = [str(e["selektor"]) for e in layout_ausnahmen(REGELWERK)]
    except (OSError, ValueError) as fehler:
        print(f"🛑 Layout-Ausnahmen nicht lesbar: {fehler}")
        return 2
    befunde, hinweise, dateizahl = pruefe_baum(
        BLOG_DIR, erlaubte_dauern, erlaubte_kurven, ausnahme_liste,
        layout_frei=layout_frei)

    if dateizahl < MIN_DATEIEN:
        print(f"🛑 Nur {dateizahl} Stylesheet(s) gefunden (Minimum {MIN_DATEIEN}) – "
              "ein Prüfer ohne Prüflinge ist nicht grün, sondern blind.")
        return 2

    befunde = sortiere_nach_datei(befunde) + ausnahme_funde
    hinweise = sortiere_nach_datei(hinweise)
    zaehler: dict[str, int] = {}
    for fund in befunde + hinweise:
        zaehler[fund.klasse] = zaehler.get(fund.klasse, 0) + 1

    if args.json:
        print(json.dumps({
            "dateien": dateizahl,
            "skala_dauer_s": sorted(erlaubte_dauern),
            "skala_easing": sorted(erlaubte_kurven),
            "befunde": [asdict(f) for f in befunde],
            "hinweise": [asdict(f) for f in hinweise],
            "zaehler": zaehler,
            "ok": not befunde,
        }, ensure_ascii=False, indent=2))
        return 1 if (befunde and not args.nur_hinweise) else 0

    print("## Bewegungs-Wache – Easing, Dauer, Lift")
    print(f"\nGeprüft: {dateizahl} Stylesheets in {', '.join(CSS_KORPUS)}; "
          f"Skala {sorted(erlaubte_dauern)} s, Kurven {sorted(erlaubte_kurven)}.\n")
    for klasse, name in {**BEFUND_KLASSEN, **HINWEIS_KLASSEN}.items():
        if klasse in zaehler:
            print(f"- {klasse} · {name}: {zaehler[klasse]}")
    if befunde:
        print("\n**Vertragsbruch (B1/B4, plus B6 Ausnahmen):**\n")
        for fund in befunde:
            print(f"- {fund.kurz()}")
    if hinweise:
        print("\n**Hinweise (B2/B5):**\n")
        for fund in hinweise[:25]:
            print(f"- {fund.kurz()}")
        if len(hinweise) > 25:
            print(f"- … und {len(hinweise) - 25} weitere (--json für alle)")
    if not befunde and not hinweise:
        print("\n✅ Null Befunde: Die Skala wird überall eingehalten.")
    print(f"\nbewegungs_wache: {dateizahl} Dateien, {len(befunde)} Befund(e), "
          f"{len(hinweise)} Hinweis(e)")
    if befunde and args.nur_hinweise:
        print("(Bestandslauf: Befunde werden gemeldet, blockieren aber nicht – "
              "`--nur-hinweise`)")
        return 0
    return 1 if befunde else 0


if __name__ == "__main__":
    sys.exit(main())
