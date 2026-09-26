#!/usr/bin/env python3
"""Design-Varianten-Gate: der Vertrag zwischen KI-Entwurf und Produktion.

Teil der Design-Varianten-Werkbank (Rollout 26.09.2026, Runbook:
docs/ANLEITUNG-DESIGN-VARIANTEN.md).

WOZU
----
Eine KI darf für diesen Blog Layoutvarianten entwerfen und Messdaten
auswerten. Sie darf das Design nicht austauschen. Dieses Gate ist die
Stelle, an der aus „sieht gut aus" ein prüfbarer Zustand wird. Es
beantwortet genau drei Fragen:

  1. Hält sich die Variante an die Marke?   (statisch, aus dem CSS)
  2. Ist sie vollständig vermessen?         (Tier A + Tier B)
  3. Hat ein Mensch unterschrieben?         (Freigabe-Akte)

Erst wenn alle drei mit Ja beantwortet sind, darf eine Variante scharf
geschaltet werden. Das Gate schaltet nichts – es erlaubt oder verweigert.

PRÜFUNGEN
---------
  Registerhygiene   IDs, Pflichtfelder, Status-Lebenslauf, Dubletten
  Marken-Audit      Farben/Radien/Schatten/Easing/Verbote im Varianten-CSS
  Freigabe-Kontrakt Unterschrift, Berechtigung, Datum, Verfallsfrist
  Messvertrag       Tier A (statisch) + Tier B (Browser) vorhanden & grün
  Produktionswache  hugo.toml darf keine unfreigegebene Variante aktivieren

BESITZ-TRENNUNG (Governance C14)
--------------------------------
Jeder Befund trägt `besitzer` (auto = Maschine kann heilen, human = nur
ein Mensch), `schwere` (P1–P3) und `kanal`. Befunde ohne Besitzer sind
der Anfang des Dauer-Alarms – siehe docs/ALARMROUTING-2026-09-12.md.

AUFRUF
------
  python3 scripts/design_variant_gate.py                  # alle Varianten
  python3 scripts/design_variant_gate.py --variante v-x   # nur eine
  python3 scripts/design_variant_gate.py --json           # maschinenlesbar
  python3 scripts/design_variant_gate.py --produktionswache
  python3 scripts/design_variant_gate.py --selftest

EXIT-CODES
----------
  0 = keine Befunde (bzw. nur P3 ohne --strict)
  1 = Befunde vorhanden
  2 = schwerer Fehler (Regelwerk/Register unlesbar) – fail-closed
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGELWERK = ROOT / "data" / "design" / "regelwerk.yaml"
REGISTER = ROOT / "data" / "design" / "varianten.yaml"
ASSETS = ROOT / "assets"
MESSUNGEN = ROOT / ".cache" / "design-varianten"
HUGO_TOML = ROOT / "hugo.toml"

KANAL = "design-varianten"

# Schlüssel, die das Gate im Regelwerk kennt und prüft. Ein unbekannter
# Schlüssel ist ein Fehler: Sonst entstehen Regeln, die nur wie Regeln
# aussehen (siehe Kopf von regelwerk.yaml).
BEKANNTE_ABSCHNITTE = {
    "version", "stand", "marke", "barrierefreiheit", "seo",
    "performance", "conversion", "freigabe",
}
BEKANNTE_SCHLUESSEL = {
    "marke": {
        "farben_erlaubt", "variablen_praefixe_erlaubt", "rgba_basen_erlaubt",
        "radien_px_erlaubt", "uebergang_dauer_s_erlaubt", "easing_erlaubt",
        "verbote", "pflichten", "css_budget_bytes",
    },
    "barrierefreiheit": {
        "kontrast_fliesstext_min", "kontrast_grosse_typo_min",
        "kontrast_meta_min", "tap_ziel_min_px", "tap_ziel_soll_px",
        "fokusring_sichtbar", "lighthouse_accessibility_min", "begruendung",
    },
    "seo": {
        "h1_anzahl_exakt", "canonical_pflicht", "titel_identisch_zur_basis",
        "description_identisch_zur_basis", "robots_identisch_zur_basis",
        "schema_typen_pflicht", "interne_links_min_anteil_basis",
        "bilder_ohne_masse_erlaubt", "alt_texte_luecken_erlaubt",
        "lighthouse_seo_min", "begruendung",
    },
    "performance": {
        "dom_kinder_max", "dom_head_kinder_max", "dom_tiefe_max",
        "dom_elemente_max", "dom_elemente_laufzeit_max",
        "stylesheet_zuwachs_bytes_max", "seiten_gewicht_zuwachs_bytes_max",
        "zusaetzliche_anfragen_max", "lcp_ms_max", "cls_max", "tbt_ms_max",
        "lighthouse_performance_min", "lighthouse_best_practices_min",
        "begruendung",
    },
    "conversion": {"erhalten", "ziele", "begruendung"},
    "freigabe": {
        "mensch_pflicht", "berechtigte", "pflichtfelder", "messung_pflicht",
        "gueltigkeit_tage", "erlaubte_status", "begruendung",
    },
}

PFLICHTFELDER_VARIANTE = (
    "id", "titel", "hypothese", "oberflaeche", "herkunft", "status", "css",
    "freigabe",
)
ID_MUSTER = re.compile(r"^[a-z0-9][a-z0-9-]*$")
MIN_HYPOTHESE = 80          # Zeichen – kürzer ist keine Hypothese, sondern ein Wunsch


# ======================================================================
# Befunde
# ======================================================================

@dataclass
class Befund:
    """Ein Prüfergebnis mit Besitzer – nie ohne (Governance C14)."""
    regel: str
    variante: str
    schwere: str          # P1 | P2 | P3
    besitzer: str         # auto | human
    text: str
    kanal: str = KANAL

    def zeile(self) -> str:
        return f"[{self.schwere}/{self.besitzer}] {self.variante}: {self.text}  ({self.regel})"


@dataclass
class Bericht:
    befunde: list[Befund] = field(default_factory=list)
    varianten: dict = field(default_factory=dict)
    geprueft: int = 0

    def melde(self, **kw) -> None:
        self.befunde.append(Befund(**kw))

    @property
    def p1(self) -> int:
        return sum(1 for b in self.befunde if b.schwere == "P1")

    @property
    def blockierend(self) -> list[Befund]:
        return [b for b in self.befunde if b.schwere in ("P1", "P2")]


# ======================================================================
# Laden
# ======================================================================

def _yaml():
    try:
        import yaml  # PyYAML – im Repo Standard
    except ImportError:  # pragma: no cover
        raise SystemExit("PyYAML fehlt: pip install pyyaml")
    return yaml


def lade_yaml(pfad: Path, was: str) -> dict:
    if not pfad.exists():
        raise SystemExit(f"{was} nicht gefunden: {pfad}")
    daten = _yaml().safe_load(pfad.read_text(encoding="utf-8")) or {}
    if not isinstance(daten, dict):
        raise SystemExit(f"{was} ungültig (kein Mapping): {pfad}")
    return daten


def pruefe_regelwerk_schema(rw: dict) -> list[str]:
    """Unbekannte Schlüssel sind Fehler – siehe Kopf von regelwerk.yaml."""
    fehler: list[str] = []
    unbekannt = set(rw) - BEKANNTE_ABSCHNITTE
    if unbekannt:
        fehler.append(
            f"Regelwerk: unbekannte Abschnitte {sorted(unbekannt)} – das Gate "
            "prüft sie nicht. Entweder im Gate ergänzen oder entfernen.")
    for abschnitt, erlaubt in BEKANNTE_SCHLUESSEL.items():
        block = rw.get(abschnitt) or {}
        if not isinstance(block, dict):
            fehler.append(f"Regelwerk: Abschnitt `{abschnitt}` ist kein Mapping.")
            continue
        fremd = set(block) - erlaubt
        if fremd:
            fehler.append(
                f"Regelwerk: `{abschnitt}` kennt die Schlüssel {sorted(fremd)} nicht.")
    return fehler


# ======================================================================
# CSS-Werkzeuge
# ======================================================================

KOMMENTAR = re.compile(r"/\*.*?\*/", re.S)


def ohne_kommentare(css: str) -> str:
    """CSS-Kommentare entfernen.

    Unverzichtbar: Varianten-CSS dokumentiert sich selbst und schreibt
    dabei Sätze wie „kein !important" oder nennt Beispielfarben. Ohne
    diesen Schritt würde das Gate die eigene Dokumentation anklagen.
    """
    return KOMMENTAR.sub(" ", css)


def hex_normalisieren(wert: str) -> str:
    """#abc → #aabbcc, alles klein. Macht Vergleiche verlässlich."""
    w = wert.strip().lower()
    if len(w) == 4:  # #rgb
        return "#" + "".join(c * 2 for c in w[1:])
    return w


def finde_hex(css: str) -> set[str]:
    return {hex_normalisieren(m) for m in re.findall(r"#[0-9a-fA-F]{3,8}\b", css)}


def finde_rgba_basen(css: str) -> set[tuple[int, int, int]]:
    basen = set()
    for m in re.finditer(r"rgba?\(\s*([0-9]+)[,\s]+([0-9]+)[,\s]+([0-9]+)", css):
        basen.add((int(m.group(1)), int(m.group(2)), int(m.group(3))))
    return basen


def finde_variablen(css: str) -> set[str]:
    return set(re.findall(r"var\(\s*(--[a-zA-Z0-9_-]+)", css))


def finde_radien_px(css: str) -> set[float]:
    werte: set[float] = set()
    for m in re.finditer(r"border-radius\s*:\s*([^;}]+)", css):
        for zahl in re.findall(r"(-?\d*\.?\d+)px", m.group(1)):
            werte.add(float(zahl))
    return werte


def finde_dauern_s(css: str) -> set[float]:
    """Dauern aus transition/animation – in Sekunden normalisiert."""
    werte: set[float] = set()
    for m in re.finditer(r"(?:transition|animation)(?:-duration)?\s*:\s*([^;}]+)", css):
        block = m.group(1)
        for zahl, einheit in re.findall(r"(-?\d*\.?\d+)(ms|s)\b", block):
            wert = float(zahl) / 1000.0 if einheit == "ms" else float(zahl)
            werte.add(round(wert, 4))
    return werte


def finde_easing(css: str) -> set[str]:
    gefunden: set[str] = set()
    for m in re.finditer(r"cubic-bezier\([^)]*\)", css):
        gefunden.add(re.sub(r"\s+", "", m.group(0)).lower())
    for m in re.finditer(r"(?:transition|animation)(?:-timing-function)?\s*:\s*([^;}]+)", css):
        for name in re.findall(r"\b(ease-in-out|ease-in|ease-out|ease|linear|step-start|step-end)\b",
                               m.group(1)):
            gefunden.add(name)
    return gefunden


def setzt_farbe(css: str) -> bool:
    return bool(re.search(
        r"(?:^|[;{\s])(color|background|background-color|border-color|"
        r"box-shadow|fill|stroke|outline-color)\s*:", css))


def setzt_bewegung(css: str) -> bool:
    return bool(re.search(r"(?:^|[;{\s])(transition|animation|transform)\s*:", css))


# ======================================================================
# Prüfung: Marken-Audit eines Varianten-Stylesheets
# ======================================================================

def pruefe_css(vid: str, css_roh: str, marke: dict, bericht: Bericht) -> None:
    css = ohne_kommentare(css_roh)
    klein = css.lower()

    # --- Budget -------------------------------------------------------
    budget = int(marke.get("css_budget_bytes", 8192))
    groesse = len(css_roh.encode("utf-8"))
    if groesse > budget:
        bericht.melde(
            regel="marke.css_budget_bytes", variante=vid, schwere="P2",
            besitzer="human",
            text=f"Varianten-CSS ist {groesse} Bytes groß (Budget {budget}). "
                 "Eine Variante ist Feinschliff, keine zweite Designschicht.")

    # --- Farben -------------------------------------------------------
    erlaubt_hex = {hex_normalisieren(h) for h in marke.get("farben_erlaubt", [])}
    for gefunden in sorted(finde_hex(css) - erlaubt_hex):
        bericht.melde(
            regel="marke.farben_erlaubt", variante=vid, schwere="P2",
            besitzer="human",
            text=f"Farbe {gefunden} steht nicht in den Marken-Tokens "
                 "(DESIGN.md §1). Token verwenden oder Token erweitern – "
                 "aber nicht still erfinden.")

    erlaubt_rgba = {tuple(t) for t in marke.get("rgba_basen_erlaubt", [])}
    for basis in sorted(finde_rgba_basen(css) - erlaubt_rgba):
        bericht.melde(
            regel="marke.rgba_basen_erlaubt", variante=vid, schwere="P2",
            besitzer="human",
            text=f"rgb(a)-Basis {basis} ist nicht freigegeben (DESIGN.md §4).")

    praefixe = tuple(marke.get("variablen_praefixe_erlaubt", []))
    for v in sorted(finde_variablen(css)):
        if praefixe and not v.startswith(praefixe):
            bericht.melde(
                regel="marke.variablen_praefixe_erlaubt", variante=vid,
                schwere="P2", besitzer="human",
                text=f"CSS-Variable {v} liegt außerhalb der erlaubten Präfixe "
                     f"{list(praefixe)}.")

    # --- Radien -------------------------------------------------------
    erlaubte_radien = {float(r) for r in marke.get("radien_px_erlaubt", [])}
    for r in sorted(finde_radien_px(css) - erlaubte_radien):
        bericht.melde(
            regel="marke.radien_px_erlaubt", variante=vid, schwere="P3",
            besitzer="human",
            text=f"Radius {r:g}px liegt neben der Skala "
                 f"{sorted(int(x) for x in erlaubte_radien)} (DESIGN.md §4).")

    # --- Bewegung -----------------------------------------------------
    erlaubte_dauern = {round(float(d), 4) for d in marke.get("uebergang_dauer_s_erlaubt", [])}
    for d in sorted(finde_dauern_s(css) - erlaubte_dauern - {0.0}):
        bericht.melde(
            regel="marke.uebergang_dauer_s_erlaubt", variante=vid, schwere="P3",
            besitzer="human",
            text=f"Übergangsdauer {d:g}s ist nicht Teil der Skala "
                 f"{sorted(erlaubte_dauern)} (DESIGN.md §6).")

    erlaubtes_easing = {re.sub(r"\s+", "", e).lower() for e in marke.get("easing_erlaubt", [])}
    for e in sorted(finde_easing(css) - erlaubtes_easing):
        bericht.melde(
            regel="marke.easing_erlaubt", variante=vid, schwere="P3",
            besitzer="human",
            text=f"Easing `{e}` ist nicht freigegeben (DESIGN.md §6: kein "
                 "bounce/elastic).")

    # --- Verbote ------------------------------------------------------
    for name, regel in (marke.get("verbote") or {}).items():
        muster = (regel or {}).get("muster")
        if not muster:
            bericht.melde(
                regel=f"marke.verbote.{name}", variante=vid, schwere="P2",
                besitzer="human",
                text="Verbot ohne `muster` – eine Regel, die nichts prüft.")
            continue
        if re.search(muster, klein):
            grund = " ".join((regel.get("begruendung") or "").split())
            bericht.melde(
                regel=f"marke.verbote.{name}", variante=vid, schwere="P2",
                besitzer="human",
                text=f"Verbot `{name}` verletzt. {grund}")

    # --- Pflichten ----------------------------------------------------
    ausloeser = {"farbe_gesetzt": setzt_farbe(css), "bewegung_gesetzt": setzt_bewegung(css)}
    for name, regel in (marke.get("pflichten") or {}).items():
        regel = regel or {}
        schluessel = regel.get("ausloeser")
        erwartet = regel.get("erwartet")
        if schluessel not in ausloeser or not erwartet:
            bericht.melde(
                regel=f"marke.pflichten.{name}", variante=vid, schwere="P2",
                besitzer="human",
                text=f"Pflicht `{name}` hat einen unbekannten Auslöser "
                     f"({schluessel!r}) – das Gate kann sie nicht prüfen.")
            continue
        if ausloeser[schluessel] and erwartet.lower() not in klein:
            grund = " ".join((regel.get("begruendung") or "").split())
            bericht.melde(
                regel=f"marke.pflichten.{name}", variante=vid, schwere="P2",
                besitzer="human",
                text=f"Pflicht `{name}` nicht erfüllt: `{erwartet}` fehlt. {grund}")


# ======================================================================
# Prüfung: Register + Freigabe
# ======================================================================

def _datum(wert) -> dt.date | None:
    if isinstance(wert, dt.date):
        return wert
    try:
        return dt.date.fromisoformat(str(wert).strip())
    except (ValueError, AttributeError):
        return None


def pruefe_register(reg: dict, rw: dict, bericht: Bericht,
                    heute: dt.date, nur: str | None) -> None:
    freigabe_rw = rw.get("freigabe") or {}
    erlaubte_status = set(freigabe_rw.get("erlaubte_status") or [])
    berechtigte = set(freigabe_rw.get("berechtigte") or [])
    pflichtfelder = list(freigabe_rw.get("pflichtfelder") or [])
    gueltig_tage = int(freigabe_rw.get("gueltigkeit_tage") or 30)
    messung_pflicht = list(freigabe_rw.get("messung_pflicht") or [])

    eintraege = reg.get("varianten") or []
    gesehen: set[str] = set()
    live_nicht_basis: list[str] = []

    for eintrag in eintraege:
        vid = str(eintrag.get("id", "")).strip()
        if not vid:
            bericht.melde(regel="register.id", variante="(ohne id)", schwere="P2",
                          besitzer="human", text="Eintrag ohne `id`.")
            continue
        if vid in gesehen:
            bericht.melde(regel="register.dublette", variante=vid, schwere="P2",
                          besitzer="human",
                          text="ID kommt mehrfach vor – welche gilt?")
        gesehen.add(vid)

        if nur and vid != nur:
            continue
        bericht.geprueft += 1

        status = str(eintrag.get("status", "")).strip()
        ist_basis = vid == "basis"
        bericht.varianten[vid] = {"status": status, "basis": ist_basis}

        if not ID_MUSTER.match(vid):
            bericht.melde(regel="register.id", variante=vid, schwere="P2",
                          besitzer="human",
                          text="ID darf nur Kleinbuchstaben, Ziffern und "
                               "Bindestriche enthalten (sie ist ein Dateiname).")

        for feld in PFLICHTFELDER_VARIANTE:
            if feld not in eintrag:
                bericht.melde(regel="register.pflichtfeld", variante=vid,
                              schwere="P2", besitzer="human",
                              text=f"Pflichtfeld `{feld}` fehlt.")

        if status not in erlaubte_status:
            bericht.melde(regel="register.status", variante=vid, schwere="P2",
                          besitzer="human",
                          text=f"Status {status!r} ist nicht erlaubt "
                               f"({sorted(erlaubte_status)}).")

        hypothese = " ".join(str(eintrag.get("hypothese") or "").split())
        if not ist_basis and len(hypothese) < MIN_HYPOTHESE:
            bericht.melde(
                regel="register.hypothese", variante=vid, schwere="P2",
                besitzer="human",
                text=f"Hypothese ist zu dünn ({len(hypothese)} Zeichen, "
                     f"mindestens {MIN_HYPOTHESE}). Ohne „was soll besser "
                     "werden und woran erkennt man es\" ist jede Messung "
                     "hinterher interpretierbar.")

        # --- CSS ------------------------------------------------------
        css_pfad = str(eintrag.get("css") or "").strip()
        if ist_basis:
            if css_pfad:
                bericht.melde(regel="register.basis", variante=vid, schwere="P2",
                              besitzer="human",
                              text="Die Basis ist die Kontrollgruppe und darf "
                                   "kein eigenes CSS haben.")
        elif not css_pfad:
            bericht.melde(regel="register.css", variante=vid, schwere="P2",
                          besitzer="human", text="Kein `css:` angegeben.")
        else:
            datei = ASSETS / css_pfad
            erwarteter_name = f"{vid}.css"
            if datei.name != erwarteter_name:
                bericht.melde(
                    regel="register.css_name", variante=vid, schwere="P3",
                    besitzer="human",
                    text=f"Dateiname {datei.name!r} weicht von der ID ab "
                         f"(erwartet {erwarteter_name!r}) – erschwert jedes "
                         "spätere Aufräumen.")
            if not datei.exists():
                bericht.melde(regel="register.css", variante=vid, schwere="P2",
                              besitzer="human",
                              text=f"CSS-Datei assets/{css_pfad} fehlt.")
            else:
                pruefe_css(vid, datei.read_text(encoding="utf-8"),
                           rw.get("marke") or {}, bericht)

        # --- Freigabe-Akte -------------------------------------------
        akte = eintrag.get("freigabe") or {}
        if not isinstance(akte, dict):
            bericht.melde(regel="freigabe.akte", variante=vid, schwere="P2",
                          besitzer="human", text="`freigabe:` ist kein Mapping.")
            akte = {}

        unterschrieben = bool(akte.get("mensch"))
        scharf = status in ("freigegeben", "live")

        if scharf and not ist_basis:
            for feld in pflichtfelder:
                if not str(akte.get(feld) or "").strip() and feld != "mensch":
                    bericht.melde(
                        regel="freigabe.pflichtfeld", variante=vid, schwere="P1",
                        besitzer="human",
                        text=f"Status {status!r}, aber Freigabefeld `{feld}` ist leer.")
            if not unterschrieben:
                bericht.melde(
                    regel="freigabe.mensch", variante=vid, schwere="P1",
                    besitzer="human",
                    text=f"Status {status!r} ohne menschliche Unterschrift "
                         "(`freigabe.mensch: false`). Genau das soll die "
                         "Werkbank verhindern.")
            name = str(akte.get("name") or "").strip()
            if name and berechtigte and name not in berechtigte:
                bericht.melde(
                    regel="freigabe.berechtigte", variante=vid, schwere="P1",
                    besitzer="human",
                    text=f"{name!r} steht nicht in regelwerk.yaml → "
                         f"freigabe.berechtigte ({sorted(berechtigte)}).")
            datum = _datum(akte.get("datum"))
            if akte.get("datum") and not datum:
                bericht.melde(
                    regel="freigabe.datum", variante=vid, schwere="P2",
                    besitzer="human",
                    text=f"Freigabedatum {akte.get('datum')!r} ist kein ISO-Datum.")
            elif datum:
                if datum > heute:
                    bericht.melde(
                        regel="freigabe.datum", variante=vid, schwere="P1",
                        besitzer="human",
                        text=f"Freigabedatum {datum} liegt in der Zukunft.")
                elif status == "freigegeben" and (heute - datum).days > gueltig_tage:
                    bericht.melde(
                        regel="freigabe.verfall", variante=vid, schwere="P2",
                        besitzer="human",
                        text=f"Freigabe ist {(heute - datum).days} Tage alt "
                             f"(gültig {gueltig_tage}). Der Blog hat sich "
                             "seitdem verändert – neu messen und neu "
                             "unterschreiben.")

            # Verweist die Freigabe auf einen Beleg, der auch existiert?
            verweis = str(akte.get("messprotokoll") or "").strip()
            if verweis:
                if not (PROTOKOLLE / verweis).exists():
                    bericht.melde(
                        regel="freigabe.messprotokoll", variante=vid, schwere="P1",
                        besitzer="human",
                        text=f"Freigabe nennt das Messprotokoll data/{verweis} – "
                             "die Datei fehlt. Eine Unterschrift auf einen "
                             "Beleg, den es nicht gibt, ist keine Unterschrift.")
                else:
                    protokoll = lade_protokoll(akte) or {}
                    if str(protokoll.get("variante")) != vid:
                        bericht.melde(
                            regel="freigabe.messprotokoll", variante=vid,
                            schwere="P1", besitzer="human",
                            text=f"Das Messprotokoll data/{verweis} gehört zu "
                                 f"{protokoll.get('variante')!r}, nicht zu {vid!r}.")
                    gemessen = _datum((protokoll.get("erstellt") or "")[:10])
                    if gemessen and datum and gemessen > datum:
                        bericht.melde(
                            regel="freigabe.messprotokoll", variante=vid,
                            schwere="P2", besitzer="human",
                            text=f"Das Protokoll ist vom {gemessen}, die Freigabe "
                                 f"vom {datum} – unterschrieben wurde also auf "
                                 "einer älteren Messung als der hinterlegten.")

            # Messvertrag
            for tier in messung_pflicht:
                if not messung_vorhanden(vid, tier, akte):
                    bericht.melde(
                        regel="freigabe.messung", variante=vid, schwere="P1",
                        besitzer="human",
                        text=f"Status {status!r}, aber Messung `{tier}` fehlt "
                             f"(.cache/design-varianten/{vid}/messung.json). "
                             "Eine Freigabe ohne Messung ist ein Bauchgefühl "
                             "mit Unterschrift.")

        if unterschrieben and status in ("entwurf", "gemessen"):
            bericht.melde(
                regel="freigabe.widerspruch", variante=vid, schwere="P3",
                besitzer="human",
                text=f"Unterschrift vorhanden, Status aber {status!r} – "
                     "einer von beiden Werten ist veraltet.")

        if status == "live" and not ist_basis:
            live_nicht_basis.append(vid)

    # --- Basis & aktiv müssen zusammenpassen --------------------------
    if not nur or nur == "basis":
        basis = next((e for e in eintraege if str(e.get("id")) == "basis"), None)
        if basis is None:
            bericht.melde(regel="register.basis", variante="basis", schwere="P2",
                          besitzer="human",
                          text="Kein `basis`-Eintrag – dann hat keine Messung "
                               "eine Kontrollgruppe.")
        elif str(basis.get("status")) != "live":
            bericht.melde(regel="register.basis", variante="basis", schwere="P2",
                          besitzer="human",
                          text="Die Basis muss den Status `live` haben – sie "
                               "ist das, was ausgeliefert wird. Varianten "
                               "liegen additiv darüber.")

    if len(live_nicht_basis) > 1:
        bericht.melde(
            regel="register.aktiv", variante=", ".join(live_nicht_basis),
            schwere="P1", besitzer="human",
            text="Mehr als eine Variante steht auf `live`. Es kann nur eine "
                 "geben – sonst weiß niemand, was der Besucher sieht.")

    aktiv = str(reg.get("aktiv") or "").strip()
    if aktiv:
        if aktiv not in gesehen:
            bericht.melde(regel="register.aktiv", variante=aktiv, schwere="P1",
                          besitzer="human",
                          text="`aktiv:` nennt eine ID, die es nicht gibt.")
        elif aktiv not in live_nicht_basis:
            bericht.melde(regel="register.aktiv", variante=aktiv, schwere="P1",
                          besitzer="human",
                          text="`aktiv:` nennt eine Variante, die nicht auf "
                               "`live` steht.")
    elif live_nicht_basis:
        bericht.melde(
            regel="register.aktiv", variante=live_nicht_basis[0], schwere="P1",
            besitzer="human",
            text="Variante steht auf `live`, `aktiv:` ist aber leer – zwei "
                 "Wahrheiten über denselben Zustand.")


PROTOKOLLE = ROOT / "data"


def lade_protokoll(akte: dict | None) -> dict | None:
    """Das committete Messprotokoll einer Freigabe – oder None.

    Eine Freigabe muss auf einen DAUERHAFTEN Beleg zeigen. Messungen
    entstehen in .cache/ (gitignored, flüchtig): Läge der Beleg nur
    dort, wäre jede unterschriebene Variante nach einem frischen
    Checkout „freigegeben ohne Messung" – ein P1 in jedem CI-Lauf, den
    niemand verursacht hat. Deshalb friert
    `design_variant_lab.py --protokoll` die Messung nach
    data/design/messungen/ ein, und die Freigabe nennt sie unter
    `messprotokoll:`.
    """
    if not akte:
        return None
    pfad = str(akte.get("messprotokoll") or "").strip()
    if not pfad:
        return None
    datei = PROTOKOLLE / pfad
    if not datei.exists():
        return None
    try:
        return json.loads(datei.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def messung_vorhanden(vid: str, tier: str, akte: dict | None = None) -> bool:
    """Liegt `tier` als grüne Messung vor? Protokoll schlägt Cache.

    Reihenfolge ist Absicht: Der committete Beleg ist die Wahrheit, der
    Cache nur die bequeme Abkürzung für den laufenden Arbeitstag.
    """
    protokoll = lade_protokoll(akte)
    if protokoll is not None:
        if str(protokoll.get("variante")) != vid:
            return False  # Beleg gehört zu einer anderen Variante
        block = (protokoll.get("tiers") or {}).get(tier) or {}
        return block.get("status") == "ok"

    datei = MESSUNGEN / vid / "messung.json"
    if not datei.exists():
        return False
    try:
        daten = json.loads(datei.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    block = (daten.get("tiers") or {}).get(tier) or {}
    return block.get("status") == "ok"


# ======================================================================
# Prüfung: Messwerte gegen Budgets
# ======================================================================

def lade_messung(vid: str) -> dict | None:
    datei = MESSUNGEN / vid / "messung.json"
    if not datei.exists():
        return None
    try:
        return json.loads(datei.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _verletzt(wert, soll, richtung: str) -> bool:
    return wert > soll if richtung == "max" else wert < soll


def _schlechter(wert, referenz, richtung: str) -> bool:
    return wert > referenz if richtung == "max" else wert < referenz


# Budget-Tabelle: (Regelname, Schlüssel in der Messung, Pfad im Regelwerk,
# Richtung). Eine Tabelle statt 20 Einzelaufrufe – so kann dieselbe Logik
# die Variante UND die Basis prüfen, ohne dass ein Fall vergessen wird.
BUDGETS_STATISCH = [
    ("performance.dom_kinder_max", "dom_kinder_max",
     ("performance", "dom_kinder_max"), "max"),
    ("performance.dom_head_kinder_max", "dom_head_kinder_max",
     ("performance", "dom_head_kinder_max"), "max"),
    ("performance.dom_tiefe_max", "dom_tiefe_max",
     ("performance", "dom_tiefe_max"), "max"),
    ("performance.dom_elemente_max", "dom_elemente_max",
     ("performance", "dom_elemente_max"), "max"),
    ("seo.bilder_ohne_masse_erlaubt", "bilder_ohne_masse",
     ("seo", "bilder_ohne_masse_erlaubt"), "max"),
    ("seo.alt_texte_luecken_erlaubt", "alt_luecken",
     ("seo", "alt_texte_luecken_erlaubt"), "max"),
]

BUDGETS_GERENDERT = [
    ("barrierefreiheit.kontrast_fliesstext_min", "kontrast_min",
     ("barrierefreiheit", "kontrast_fliesstext_min"), "min"),
    ("barrierefreiheit.tap_ziel_min_px", "tap_min_px",
     ("barrierefreiheit", "tap_ziel_min_px"), "min"),
    ("performance.cls_max", "cls", ("performance", "cls_max"), "max"),
    # KEIN lcp_ms hier – bewusst.
    # Playwright misst auf localhost ohne Drosselung; der Wert lag im
    # Messlauf vom 26.09.2026 bei 184 ms, während Lighthouse mit
    # simulierter Drosselung 3110 ms für dieselbe Seite meldete. Die
    # Google-Schwelle von 2500 ms gehört zur gedrosselten Messung.
    # Prüfte man den ungedrosselten Wert dagegen, wäre das Ergebnis
    # immer grün – ein Budget, das nie anschlägt, ist Dekoration.
    # Der Playwright-LCP bleibt im Report als Basis/Variante-Delta
    # (dafür taugt er: gleiche Bedingungen auf beiden Seiten).
]

# Lighthouse liefert als Einziges eine belastbare Total Blocking Time –
# im Browser selbst wäre sie eine Schätzung, die man später für eine
# Messung halten würde.
BUDGETS_LIGHTHOUSE = [
    ("performance.tbt_ms_max", "tbt_ms", ("performance", "tbt_ms_max"), "max"),
    ("performance.lcp_ms_max", "lcp_ms", ("performance", "lcp_ms_max"), "max"),
    ("performance.cls_max", "cls", ("performance", "cls_max"), "max"),
]

LIGHTHOUSE_BUDGETS = [
    ("lighthouse.performance", "performance",
     ("performance", "lighthouse_performance_min")),
    ("lighthouse.accessibility", "accessibility",
     ("barrierefreiheit", "lighthouse_accessibility_min")),
    ("lighthouse.seo", "seo", ("seo", "lighthouse_seo_min")),
    ("lighthouse.best-practices", "best-practices",
     ("performance", "lighthouse_best_practices_min")),
]


def _soll(rw: dict, pfad: tuple[str, str]):
    return (rw.get(pfad[0]) or {}).get(pfad[1])


def _werte(messung: dict | None, tier: str) -> dict | None:
    """Messwerte einer Ebene – None, wenn die Ebene nicht `ok` ist."""
    if not messung:
        return None
    block = (messung.get("tiers") or {}).get(tier) or {}
    return block.get("werte") or {} if block.get("status") == "ok" else None


def pruefe_bestand(rw: dict, bericht: Bericht) -> None:
    """Budgets, die schon die BASIS reißt, gehören der Basis – nicht der Variante.

    Ohne diese Trennung passiert genau das, was Vorfall #343 beschreibt:
    Ein Bestandszustand wird jeder neuen Arbeit angelastet, der Befund
    wandert mit jeder Variante mit und niemand behebt ihn je. Solche
    Befunde sind deshalb P3 (sichtbar, nicht blockierend) und tragen die
    Basis als Besitzer.
    """
    basis = lade_messung("basis")

    # Alle drei Ebenen, nicht nur die statische: Ein gerissenes
    # LCP-Budget der Basis blieb sonst unsichtbar, weil die Variante
    # dafür (zu Recht) nicht angeklagt wird – und damit NIEMAND.
    ebenen = [
        ("statisch", BUDGETS_STATISCH),
        ("gerendert", BUDGETS_GERENDERT),
        ("lighthouse", BUDGETS_LIGHTHOUSE),
    ]
    for tier, tabelle in ebenen:
        werte = _werte(basis, tier)
        if werte is None:
            continue
        for regel, schluessel, pfad, richtung in tabelle:
            ist, soll = werte.get(schluessel), _soll(rw, pfad)
            if ist is None or soll is None or not _verletzt(ist, soll, richtung):
                continue
            bericht.melde(
                regel=f"bestand.{regel}", variante="basis", schwere="P3",
                besitzer="human",
                text=f"Bestand ({tier}): Die ausgelieferte Basis liegt mit {ist} "
                     f"bereits {'über' if richtung == 'max' else 'unter'} dem "
                     f"Budget {soll}. Das ist kein Varianten-Befund – es gehört "
                     "in einen eigenen Vorgang.")

    # Lighthouse-Kategorien der Basis ebenfalls prüfen
    lh_werte = (_werte(basis, "lighthouse") or {}).get("lighthouse") or {}
    for regel, kategorie, pfad in LIGHTHOUSE_BUDGETS:
        ist, soll = lh_werte.get(kategorie), _soll(rw, pfad)
        if ist is None or soll is None or not _verletzt(ist, soll, "min"):
            continue
        bericht.melde(
            regel=f"bestand.{regel}", variante="basis", schwere="P3",
            besitzer="human",
            text=f"Bestand (lighthouse): Die Basis erreicht {kategorie} nur mit "
                 f"{ist} (Budget {soll}).")


def pruefe_messwerte(reg: dict, rw: dict, bericht: Bericht, nur: str | None) -> None:
    """Bewertet vorhandene Messungen gegen die Budgets.

    Fehlende Messungen sind hier KEIN Befund – sie sind nur dann einer,
    wenn die Variante freigegeben sein will (siehe Messvertrag oben).
    Sonst würde jeder frische Entwurf sofort rot leuchten.
    """
    basis = lade_messung("basis")
    basis_a = _werte(basis, "statisch")
    basis_b = _werte(basis, "gerendert")
    seo = rw.get("seo") or {}
    perf = rw.get("performance") or {}
    conv = (rw.get("conversion") or {}).get("erhalten") or {}
    a11y = rw.get("barrierefreiheit") or {}

    for eintrag in reg.get("varianten") or []:
        vid = str(eintrag.get("id", "")).strip()
        if not vid or vid == "basis" or (nur and vid != nur):
            continue

        messung = lade_messung(vid)
        if not messung:
            continue

        # ---------- Tier A: statisch ---------------------------------
        w = _werte(messung, "statisch")
        if w is not None:
            for regel, schluessel, pfad, richtung in BUDGETS_STATISCH:
                _budget(bericht, vid, regel, w.get(schluessel), _soll(rw, pfad),
                        richtung, (basis_a or {}).get(schluessel))

            # SEO-Invarianten: keine Budgets, sondern Ja/Nein.
            if w.get("h1_abweichungen"):
                bericht.melde(
                    regel="seo.h1_anzahl_exakt", variante=vid, schwere="P1",
                    besitzer="human",
                    text=f"{w['h1_abweichungen']} Seite(n) der Stichprobe haben "
                         f"nicht genau {seo.get('h1_anzahl_exakt', 1)} <h1>.")
            if seo.get("canonical_pflicht") and w.get("canonical_fehlt"):
                bericht.melde(
                    regel="seo.canonical_pflicht", variante=vid, schwere="P1",
                    besitzer="human",
                    text=f"{w['canonical_fehlt']} Seite(n) ohne rel=canonical.")
            for typ in w.get("schema_typen_fehlen") or []:
                bericht.melde(
                    regel="seo.schema_typen_pflicht", variante=vid, schwere="P1",
                    besitzer="human",
                    text=f"Pflicht-Schema {typ} fehlt im gebauten HTML.")

            # Vergleiche gegen die Basis
            if basis_a:
                _zuwachs(bericht, vid, "performance.stylesheet_zuwachs_bytes_max",
                         w.get("stylesheet_bytes"), basis_a.get("stylesheet_bytes"),
                         perf.get("stylesheet_zuwachs_bytes_max"))
                _zuwachs(bericht, vid, "performance.seiten_gewicht_zuwachs_bytes_max",
                         w.get("seiten_gewicht_bytes_max"),
                         basis_a.get("seiten_gewicht_bytes_max"),
                         perf.get("seiten_gewicht_zuwachs_bytes_max"))
                _anteil(bericht, vid, "seo.interne_links_min_anteil_basis",
                        w.get("interne_links"), basis_a.get("interne_links"),
                        seo.get("interne_links_min_anteil_basis"))
                _anteil(bericht, vid, "conversion.cta_anzahl_min_anteil_basis",
                        w.get("cta_anzahl"), basis_a.get("cta_anzahl"),
                        conv.get("cta_anzahl_min_anteil_basis"))

            # Conversion-Erhaltungsregeln – hart, weil sie die Messkette schützen
            if conv.get("umami_events_vollstaendig") and w.get("cta_ohne_umami"):
                bericht.melde(
                    regel="conversion.umami_events_vollstaendig", variante=vid,
                    schwere="P1", besitzer="human",
                    text=f"{w['cta_ohne_umami']} CTA(s) ohne data-umami-event. "
                         "Wer die Messkette kappt, gewinnt jeden A/B-Test – "
                         "auf dem Papier.")
            if conv.get("affiliate_rel_attribute_intakt") and w.get("affiliate_rel_fehler"):
                bericht.melde(
                    regel="conversion.affiliate_rel_attribute_intakt", variante=vid,
                    schwere="P1", besitzer="human",
                    text=f"{w['affiliate_rel_fehler']} Affiliate-Link(s) ohne "
                         "vollständiges rel (sponsored/nofollow/noopener).")
            for fehlt in w.get("pflicht_bausteine_fehlen") or []:
                bericht.melde(
                    regel="conversion.pflicht_bausteine", variante=vid,
                    schwere="P1", besitzer="human",
                    text=f"Pflicht-Baustein {fehlt} fehlt im gebauten HTML.")
            if conv.get("newsletter_einstieg_vorhanden") and \
                    w.get("newsletter_einstieg") is False:
                bericht.melde(
                    regel="conversion.newsletter_einstieg_vorhanden", variante=vid,
                    schwere="P1", besitzer="human",
                    text="Kein Newsletter-Einstieg mehr auf der Startseite.")
            if w.get("variante_im_markup") is False:
                bericht.melde(
                    regel="messung.variante_im_markup", variante=vid,
                    schwere="P1", besitzer="auto",
                    text="Der vermessene Bau trägt keine Variantenmarke – hier "
                         "wurde die Basis gemessen und für die Variante "
                         "gehalten. Messung wiederholen.")

        # ---------- Tier B: gerendert --------------------------------
        w = _werte(messung, "gerendert")
        if w is not None:
            for regel, schluessel, pfad, richtung in BUDGETS_GERENDERT:
                _budget(bericht, vid, regel, w.get(schluessel), _soll(rw, pfad),
                        richtung, (basis_b or {}).get(schluessel))

            if a11y.get("fokusring_sichtbar") and w.get("fokusring_sichtbar") is False:
                bericht.melde(
                    regel="barrierefreiheit.fokusring_sichtbar", variante=vid,
                    schwere="P1", besitzer="human",
                    text="Der Tastatur-Fokusring ist nicht mehr sichtbar.")

        # ---------- Lighthouse ---------------------------------------
        w = _werte(messung, "lighthouse")
        if w is not None:
            basis_lh_werte = _werte(basis, "lighthouse") or {}
            for regel, schluessel, pfad, richtung in BUDGETS_LIGHTHOUSE:
                _budget(bericht, vid, regel, w.get(schluessel), _soll(rw, pfad),
                        richtung, basis_lh_werte.get(schluessel))
            lh = w.get("lighthouse") or {}
            basis_lh = basis_lh_werte.get("lighthouse") or {}
            for regel, kategorie, pfad in LIGHTHOUSE_BUDGETS:
                _budget(bericht, vid, regel, lh.get(kategorie), _soll(rw, pfad),
                        "min", basis_lh.get(kategorie))


def _budget(bericht: Bericht, vid: str, regel: str, ist, soll, richtung: str,
            basis_wert=None) -> None:
    """Ein Budget prüfen – aber Regression von Bestand unterscheiden.

    Der Unterschied ist der ganze Punkt: Reißt die Basis ein Budget
    bereits, dann hat die Variante das nicht verursacht. Sie dafür
    anzuklagen erzeugt einen Befund, der mit jeder neuen Variante
    mitwandert und nie verschwindet – die Fehlalarm-Klasse aus
    Vorfall #343. Gemeldet wird hier nur, was die Variante WIRKLICH
    verschlechtert.
    """
    if ist is None or soll is None:
        return
    if not _verletzt(ist, soll, richtung):
        return

    ueber = "über" if richtung == "max" else "unter"

    if basis_wert is not None and _verletzt(basis_wert, soll, richtung):
        if not _schlechter(ist, basis_wert, richtung):
            return  # Bestand – gehört der Basis, nicht dieser Variante
        bericht.melde(
            regel=regel, variante=vid, schwere="P2", besitzer="human",
            text=f"Bestandsbefund verschärft: Basis {basis_wert} → Variante "
                 f"{ist} (Budget {soll}).")
        return

    zusatz = f" Die Basis lag mit {basis_wert} im Budget." if basis_wert is not None else ""
    bericht.melde(
        regel=regel, variante=vid, schwere="P2", besitzer="human",
        text=f"Messwert {ist} liegt {ueber} dem Budget {soll}.{zusatz}")


def _zuwachs(bericht: Bericht, vid: str, regel: str, ist, basis, max_zuwachs) -> None:
    if ist is None or basis is None or max_zuwachs is None:
        return
    delta = ist - basis
    if delta > max_zuwachs:
        bericht.melde(
            regel=regel, variante=vid, schwere="P2", besitzer="human",
            text=f"Zuwachs gegenüber der Basis: +{delta} Bytes "
                 f"(erlaubt +{max_zuwachs}).")


def _anteil(bericht: Bericht, vid: str, regel: str, ist, basis, min_anteil) -> None:
    if ist is None or basis in (None, 0) or min_anteil is None:
        return
    anteil = ist / basis
    if anteil < float(min_anteil):
        bericht.melde(
            regel=regel, variante=vid, schwere="P1", besitzer="human",
            text=f"{ist} statt {basis} gegenüber der Basis "
                 f"({anteil:.0%}, mindestens {float(min_anteil):.0%}).")


# ======================================================================
# Produktionswache
# ======================================================================

def produktionswache(reg: dict, bericht: Bericht) -> None:
    """Darf das, was in hugo.toml steht, überhaupt ausgeliefert werden?

    Diese Prüfung ist der eigentliche Schutz vor dem Szenario, das der
    Auftrag beschreibt: „KI tauscht das Blogdesign aus". Sie läuft im
    Deploy VOR dem Build.
    """
    param = hugo_param_variante()
    aktiv = str(reg.get("aktiv") or "").strip()
    eintraege = {str(e.get("id")): e for e in (reg.get("varianten") or [])}

    if param and param != aktiv:
        bericht.melde(
            regel="produktionswache.drift", variante=param or "(keine)",
            schwere="P1", besitzer="human",
            text=f"hugo.toml aktiviert {param!r}, das Register sagt "
                 f"aktiv={aktiv!r}. Zwei Wahrheiten über den Produktionsstand.")

    if not param:
        return

    eintrag = eintraege.get(param)
    if not eintrag:
        bericht.melde(
            regel="produktionswache.unbekannt", variante=param, schwere="P1",
            besitzer="human",
            text="hugo.toml aktiviert eine Variante, die nicht im Register steht.")
        return

    if str(eintrag.get("status")) not in ("freigegeben", "live"):
        bericht.melde(
            regel="produktionswache.status", variante=param, schwere="P1",
            besitzer="human",
            text=f"hugo.toml aktiviert eine Variante mit Status "
                 f"{eintrag.get('status')!r}. Nur `freigegeben` oder `live` "
                 "darf auf den Server.")
    if not (eintrag.get("freigabe") or {}).get("mensch"):
        bericht.melde(
            regel="produktionswache.freigabe", variante=param, schwere="P1",
            besitzer="human",
            text="hugo.toml aktiviert eine Variante ohne menschliche Freigabe.")


def hugo_param_variante(pfad: Path | None = None) -> str:
    """Liest params.designVariante aus hugo.toml (leer = Basis)."""
    pfad = pfad or HUGO_TOML
    if not pfad.exists():
        return ""
    try:
        import tomllib
        daten = tomllib.loads(pfad.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 – kaputtes TOML meldet der Build selbst
        return ""
    return str(((daten.get("params") or {}).get("designVariante")) or "").strip()


# ======================================================================
# Lighthouse-Assertions – abgeleitet, nicht abgeschrieben
# ======================================================================

LIGHTHOUSE_EXPORT = ROOT / "lighthouse" / "assertions.json"


def lighthouse_assertions(rw: dict) -> dict:
    """Erzeugt die LHCI-Assertions AUS dem Regelwerk.

    Zwei getrennt gepflegte Zahlensätze driften garantiert
    auseinander – und zwar unbemerkt, weil beide „grün" melden.
    Deshalb ist lighthouse/assertions.json ein ERZEUGTES Artefakt;
    die Wahrheit steht in data/design/regelwerk.yaml.
    """
    perf = rw.get("performance") or {}
    a11y = rw.get("barrierefreiheit") or {}
    seo = rw.get("seo") or {}
    return {
        "_hinweis": (
            "ERZEUGT aus data/design/regelwerk.yaml – nicht von Hand ändern. "
            "Neu erzeugen: python3 scripts/design_variant_gate.py --lighthouse-export"
        ),
        "assertions": {
            "categories:performance": ["error", {"minScore": perf.get("lighthouse_performance_min")}],
            "categories:accessibility": ["error", {"minScore": a11y.get("lighthouse_accessibility_min")}],
            "categories:seo": ["error", {"minScore": seo.get("lighthouse_seo_min")}],
            "categories:best-practices": ["error", {"minScore": perf.get("lighthouse_best_practices_min")}],
            "largest-contentful-paint": ["error", {"maxNumericValue": perf.get("lcp_ms_max"),
                                                   "aggregationMethod": "median"}],
            "cumulative-layout-shift": ["error", {"maxNumericValue": perf.get("cls_max"),
                                                  "aggregationMethod": "pessimistic"}],
            "total-blocking-time": ["error", {"maxNumericValue": perf.get("tbt_ms_max"),
                                              "aggregationMethod": "median"}],
            "dom-size": ["error", {"maxNumericValue": perf.get("dom_elemente_laufzeit_max")}],
        },
    }


def pruefe_lighthouse_export(rw: dict, bericht: Bericht) -> None:
    """Meldet Drift zwischen Regelwerk und erzeugter LHCI-Datei."""
    soll = lighthouse_assertions(rw)
    if not LIGHTHOUSE_EXPORT.exists():
        bericht.melde(
            regel="lighthouse.export", variante="(konfiguration)", schwere="P3",
            besitzer="auto",
            text="lighthouse/assertions.json fehlt – erzeugen mit "
                 "`python3 scripts/design_variant_gate.py --lighthouse-export`.")
        return
    try:
        ist = json.loads(LIGHTHOUSE_EXPORT.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        bericht.melde(
            regel="lighthouse.export", variante="(konfiguration)", schwere="P2",
            besitzer="auto", text=f"lighthouse/assertions.json ist kaputt: {exc}")
        return
    if ist.get("assertions") != soll["assertions"]:
        bericht.melde(
            regel="lighthouse.export", variante="(konfiguration)", schwere="P2",
            besitzer="auto",
            text="lighthouse/assertions.json weicht vom Regelwerk ab. Lighthouse "
                 "würde gegen andere Schwellen prüfen als das Gate – neu erzeugen "
                 "mit `--lighthouse-export`.")


# ======================================================================
# Ausgabe
# ======================================================================

def ausgabe(bericht: Bericht, als_json: bool, wache: bool) -> None:
    if als_json:
        print(json.dumps({
            "geprueft": bericht.geprueft,
            "varianten": bericht.varianten,
            "befunde": [asdict(b) for b in bericht.befunde],
            "bestanden": not bericht.blockierend,
        }, ensure_ascii=False, indent=2))
        return

    print("Design-Varianten-Gate")
    print("=====================")
    print(f"Geprüfte Varianten: {bericht.geprueft}")
    if wache:
        print(f"hugo.toml aktiviert: {hugo_param_variante() or '(keine – Basis)'}")
    for vid, info in sorted(bericht.varianten.items()):
        print(f"  · {vid:24} status={info['status']}")
    if bericht.befunde:
        print("\nBefunde:")
        for b in sorted(bericht.befunde, key=lambda x: (x.schwere, x.variante)):
            print("  " + b.zeile())
    else:
        print("\nKeine Befunde.")
    print("\nErgebnis:", "BESTANDEN" if not bericht.blockierend else "DURCHGEFALLEN")


# ======================================================================
# Selbsttest
# ======================================================================

def _selftest() -> int:
    """Offline-Nachweis, dass die Regeln wirklich greifen."""
    marke = {
        "farben_erlaubt": ["#0E5A43", "#FFB300", "#333"],
        "variablen_praefixe_erlaubt": ["--ff-"],
        "rgba_basen_erlaubt": [[0, 0, 0]],
        "radien_px_erlaubt": [8, 12, 16, 999],
        "uebergang_dauer_s_erlaubt": [0.16, 0.3],
        "easing_erlaubt": ["ease-out", "cubic-bezier(.2,.7,.2,1)"],
        "css_budget_bytes": 4096,
        "verbote": {
            "wichtig_holzhammer": {"muster": "!important", "begruendung": "x"},
            "webfont_im_body": {"muster": "@font-face", "begruendung": "y"},
        },
        "pflichten": {
            "dark_mode_variante": {"ausloeser": "farbe_gesetzt",
                                   "erwartet": "[data-theme=\"dark\"]",
                                   "begruendung": "z"},
        },
    }

    # 1) Saubere Variante → keine Befunde
    b = Bericht()
    pruefe_css("sauber", """
        .a { color: var(--ff-emerald); border-radius: 12px;
             transition: opacity 0.16s ease-out; }
        :root[data-theme="dark"] .a { color: #FFB300; }
    """, marke, b)
    assert not b.befunde, [x.text for x in b.befunde]

    # 2) Kommentare dürfen NICHT anklagen (sonst klagt sich jede Doku selbst an)
    b = Bericht()
    pruefe_css("kommentar", """
        /* bewusst ohne !important und ohne @font-face, Farbe #ABCDEF wäre falsch */
        .a { opacity: 1; }
    """, marke, b)
    assert not b.befunde, [x.text for x in b.befunde]

    # 3) Fremdfarbe, !important, falscher Radius, fehlender Dark-Block
    b = Bericht()
    pruefe_css("schlecht", """
        .a { color: #ABCDEF !important; border-radius: 7px;
             transition: width 2s ease-in; }
    """, marke, b)
    regeln = {x.regel for x in b.befunde}
    assert "marke.farben_erlaubt" in regeln
    assert "marke.verbote.wichtig_holzhammer" in regeln
    assert "marke.radien_px_erlaubt" in regeln
    assert "marke.pflichten.dark_mode_variante" in regeln
    assert "marke.uebergang_dauer_s_erlaubt" in regeln
    assert "marke.easing_erlaubt" in regeln

    # 4) #333 == #333333 (Kurzform-Normalisierung)
    b = Bericht()
    pruefe_css("kurz", ".a{border-color:#333333}", marke, b)
    assert not [x for x in b.befunde if x.regel == "marke.farben_erlaubt"]

    # 5) background-color darf NICHT als „Gelb als Textfarbe" gelten
    marke2 = dict(marke)
    # Pflichten hier bewusst leeren: Dieser Test isoliert die Verbots-Regex.
    # Ohne das würde die (korrekte) Dark-Mode-Pflicht mitfeuern und der Test
    # prüfte zwei Dinge gleichzeitig.
    marke2["pflichten"] = {}
    marke2["verbote"] = {"gelb_als_textfarbe": {
        "muster": r"(?:^|[;{\s])color\s*:\s*(#ffb300|var\(--ff-yellow[^)]*\))",
        "begruendung": "x"}}
    b = Bericht()
    pruefe_css("bg", ".a{background-color:#FFB300}", marke2, b)
    assert not b.befunde, [x.text for x in b.befunde]
    b = Bericht()
    pruefe_css("fg", ".a{color:#FFB300}", marke2, b)
    assert {x.regel for x in b.befunde} == {"marke.verbote.gelb_als_textfarbe"}

    # 6) Freigabe ohne Unterschrift blockiert
    rw = {"freigabe": {"erlaubte_status": ["entwurf", "gemessen", "freigegeben",
                                           "live", "verworfen"],
                       "berechtigte": ["Frank Hartung"],
                       "pflichtfelder": ["mensch", "name", "datum", "kommentar"],
                       "messung_pflicht": [], "gueltigkeit_tage": 30},
          "marke": {}}
    reg = {"aktiv": "", "varianten": [
        {"id": "basis", "titel": "B", "hypothese": "-", "oberflaeche": ["/"],
         "herkunft": "x", "status": "live", "css": "",
         "freigabe": {"mensch": True, "name": "Frank Hartung",
                      "datum": "2026-09-01", "kommentar": "ok"}},
        {"id": "v-test", "titel": "T", "hypothese": "H" * 100,
         "oberflaeche": ["/"], "herkunft": "KI", "status": "freigegeben",
         "css": "css/varianten/v-test.css",
         "freigabe": {"mensch": False, "name": "", "datum": "", "kommentar": ""}},
    ]}
    b = Bericht()
    pruefe_register(reg, rw, b, dt.date(2026, 9, 26), None)
    regeln = {x.regel for x in b.befunde}
    assert "freigabe.mensch" in regeln
    assert "freigabe.pflichtfeld" in regeln
    assert any(x.schwere == "P1" for x in b.befunde)

    # 7) Zu dünne Hypothese wird erkannt
    reg2 = {"aktiv": "", "varianten": [
        {"id": "basis", "titel": "B", "hypothese": "-", "oberflaeche": ["/"],
         "herkunft": "x", "status": "live", "css": "",
         "freigabe": {"mensch": True, "name": "Frank Hartung",
                      "datum": "2026-09-01", "kommentar": "ok"}},
        {"id": "v-duenn", "titel": "T", "hypothese": "sieht besser aus",
         "oberflaeche": ["/"], "herkunft": "KI", "status": "entwurf",
         "css": "", "freigabe": {"mensch": False, "name": "", "datum": "",
                                 "kommentar": ""}},
    ]}
    b = Bericht()
    pruefe_register(reg2, rw, b, dt.date(2026, 9, 26), None)
    assert "register.hypothese" in {x.regel for x in b.befunde}

    # 8) Budget-Vergleiche
    b = Bericht()
    _budget(b, "v", "r", 10, 5, "max"); assert len(b.befunde) == 1
    _budget(b, "v", "r", 3, 5, "max"); assert len(b.befunde) == 1
    _budget(b, "v", "r", 3, 5, "min"); assert len(b.befunde) == 2
    _anteil(b, "v", "r", 2, 3, 1.0); assert len(b.befunde) == 3
    _zuwachs(b, "v", "r", 100, 10, 50); assert len(b.befunde) == 4

    # 8b) Bestand vs. Regression – der Kern von Vorfall #343.
    #     Basis reißt das Budget bereits (58 > 54): gleich schlechte oder
    #     bessere Variante darf NICHT angeklagt werden.
    b = Bericht()
    _budget(b, "v", "r", 58, 54, "max", basis_wert=58)
    assert not b.befunde, [x.text for x in b.befunde]
    _budget(b, "v", "r", 55, 54, "max", basis_wert=58)
    assert not b.befunde, "Verbesserung gegenüber der Basis ist kein Befund"
    _budget(b, "v", "r", 61, 54, "max", basis_wert=58)
    assert len(b.befunde) == 1 and "verschärft" in b.befunde[0].text
    # Basis im Budget, Variante darüber -> echte Regression
    b = Bericht()
    _budget(b, "v", "r", 55, 54, "max", basis_wert=50)
    assert len(b.befunde) == 1 and "im Budget" in b.befunde[0].text
    # min-Richtung (Kontrast): Basis 4.0 unter Soll 4.5, Variante 4.2 besser
    b = Bericht()
    _budget(b, "v", "r", 4.2, 4.5, "min", basis_wert=4.0)
    assert not b.befunde
    _budget(b, "v", "r", 3.8, 4.5, "min", basis_wert=4.0)
    assert len(b.befunde) == 1 and "verschärft" in b.befunde[0].text

    # 9) Regelwerk-Schema meldet unbekannte Schlüssel
    fehler = pruefe_regelwerk_schema({"version": 1, "quatsch": {}})
    assert fehler and "quatsch" in fehler[0]

    # 10) Das echte Regelwerk muss dem Schema genügen
    if REGELWERK.exists():
        echt = lade_yaml(REGELWERK, "Regelwerk")
        assert not pruefe_regelwerk_schema(echt), pruefe_regelwerk_schema(echt)

    print("selftest: OK (11 Gruppen)")
    return 0


# ======================================================================
# main
# ======================================================================

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Design-Varianten-Gate (Marke, Messung, Freigabe)")
    ap.add_argument("--variante", default=None, help="nur diese ID prüfen")
    ap.add_argument("--json", action="store_true", help="maschinenlesbare Ausgabe")
    ap.add_argument("--produktionswache", action="store_true",
                    help="prüft, ob hugo.toml eine erlaubte Variante aktiviert")
    ap.add_argument("--strict", action="store_true",
                    help="auch P3-Befunde führen zu Exit 1")
    ap.add_argument("--lighthouse-export", action="store_true",
                    help="lighthouse/assertions.json aus dem Regelwerk erzeugen")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return _selftest()

    if args.lighthouse_export:
        rw = lade_yaml(REGELWERK, "Regelwerk")
        LIGHTHOUSE_EXPORT.parent.mkdir(parents=True, exist_ok=True)
        LIGHTHOUSE_EXPORT.write_text(
            json.dumps(lighthouse_assertions(rw), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        print(f"geschrieben: {LIGHTHOUSE_EXPORT.relative_to(ROOT)}")
        return 0

    rw = lade_yaml(REGELWERK, "Regelwerk")
    reg = lade_yaml(REGISTER, "Varianten-Register")

    schema_fehler = pruefe_regelwerk_schema(rw)
    if schema_fehler:
        for f in schema_fehler:
            print(f"FEHLER: {f}", file=sys.stderr)
        return 2

    bericht = Bericht()
    pruefe_register(reg, rw, bericht, dt.date.today(), args.variante)
    pruefe_bestand(rw, bericht)
    pruefe_lighthouse_export(rw, bericht)
    pruefe_messwerte(reg, rw, bericht, args.variante)
    if args.produktionswache:
        produktionswache(reg, bericht)

    ausgabe(bericht, args.json, args.produktionswache)

    if bericht.blockierend:
        return 1
    if args.strict and bericht.befunde:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
