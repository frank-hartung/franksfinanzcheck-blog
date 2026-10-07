#!/usr/bin/env python3
"""Robustheits-Gate – die Seite darf nie stumm sterben (Vertrag C31, 07.10.2026).

WARUM DIESES GATE EXISTIERT
---------------------------
Ein Blog hat zwei Arten von Fehlern: die lauten (Build bricht ab, Deploy bleibt
liegen – die fangen die übrigen Wachen) und die stillen. Die stillen sind
teurer, weil sie niemand meldet: ein Rechner, der beim Initialisieren stirbt und
einen toten Knopf hinterlässt; ein Anmeldeformular, das unbegrenzt auf einen
hängenden Worker wartet; ein Service Worker, dessen Cache-Fehler einen Request
verschlingt, der ohne ihn längst durchgegangen wäre; ein Kopierversuch, der
„copied!" verspricht, obwohl die Zwischenablage die Erlaubnis verweigerte.

Diese Klasse ist unsichtbar für Build-Gates, weil die Seite BAUT. Sie fällt nur
im Browser auf – bei einem Leser, auf einem Gerät, das niemand hier hat. Dieses
Gate macht die Gegenmittel überprüfbar: nicht „funktioniert heute", sondern
„das Fangnetz steht noch, wo es stehen muss".

REGELN
------
R1  SCHICHT      static/premium/ff-robust.js existiert, trägt die API
                 (insel/ablage/zwischenablage/bericht) und ist genau einmal
                 über asset_url (Cache-Busting) eingebunden.
R2  BOOTSTRAP    Der Fehler-Horcher sitzt im <head> – und zwar IM vorhandenen
                 Head-Skript: kein neues Head-Kind (DOM-Budget 58,
                 scripts/dom_audit.py). Ohne ihn sind Fehler der Inline-Skripte
                 weg, bevor ein Skript am Fuß des Body horchen kann.
R3  IDEMPOTENZ   Beide Stufen melden sich nur einmal an (R.boot). Ein doppelter
                 Horcher verdoppelt jeden Befund und lügt in der Diagnose.
R4  ZEITLIMIT    Jeder Fetch der Erstparteienskripte hat ein Zeitlimit
                 (FFRobust.hole / AbortController / zeitlimit). Unbegrenztes
                 Warten friert Knöpfe ein – der Leser kommt nicht mehr raus.
R5  SW FAIL-OFFEN Der Service Worker darf einen Request nie verschlucken:
                 Cache-Zugriff im Fangnetz, Offline-Fangnetz (404.html),
                 Range-Anfragen ins Netz, /sw.js nie cache-first,
                 SKIP_WAITING-Horcher.
R6  INSELN       Jeder interaktive Baustein hat sein eigenes Fangnetz und
                 sagt im Ausfall einen Satz (Rechner, Kurzfassung-Netz,
                 Kopier-Knopf, Anmeldung, Präferenzen, Feedback).
R7  MARKUP       innerHTML nur mit statischem Literal; nie document.write,
                 eval(), insertAdjacentHTML oder outerHTML-Zuweisung.
R8  SPEICHER     Jeder localStorage/sessionStorage-Zugriff liegt in einem
                 try/catch (Safari privat, blockierte Cookies, volle Quota
                 werfen – ein Werkzeug darf daran nicht sterben).
R9  HINWEIS      Der Ausfall-Satz ist gestylt, hat eine Dark-Variante und
                 ist als role="status" angekündigt (WCAG 4.1.3).
R10 SYNTAX       Jedes Erstparteienskript ist parsebar (node --check), der
                 Service Worker eingeschlossen.
R11 FIRST-PARTY  Resilienzschicht und Bootstrap laden keine fremde Domain.
R12 EINE EINBINDUNG  ff-robust.js wird genau einmal geladen.

Das Gate repariert nie selbst. Ein Fangnetz, das sich selbst wieder einhängt,
wäre keines.

Aufruf:
  python3 scripts/robustheits_gate.py --source-only      # Quelle (ohne Hugo)
  python3 scripts/robustheits_gate.py --public public    # gebaute Wahrheit
  python3 scripts/robustheits_gate.py --selftest         # Detektor beweisen
  python3 scripts/robustheits_gate.py --json --strict    # maschinenlesbar

Exit: 0 = grün · 1 = Verstoß (Deploy stoppen) · 2 = Ausführungsfehler
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Iterable

ROOT = Path(__file__).resolve().parents[1]

SCHICHT = "static/premium/ff-robust.js"
BOOTSTRAP = "layouts/_partials/extend_head.html"
EINBINDUNG = "layouts/_partials/deferred_scripts.html"
SW = "layouts/index.sw.js"
FUSS = "layouts/_partials/footer.html"
CSS = "assets/css/extended/zz-robustheit.css"
PREMIUM = "static/premium"

# API, die die Schicht anbieten MUSS – fehlt ein Baustein, ist die Schicht
# eine andere (und die Bausteine, die sie abrufen, laufen ins Leere).
API = ("insel", "ablage", "zwischenablage", "bericht", "melden", "sicher", "bereit")

# <script>-Tags in extend_head.html (alle, auch JSON-LD-Dateninseln): Der
# Bootstrap teilt sich das vorhandene Consent-Skript, damit der <head> nicht
# wächst – 58 Kinder sind die Lighthouse-Messgrenze (dom_audit.LIMIT.head_children)
# und Artikel-Seiten liegen bei 48–58. Repo-Regel (docs/LAYOUT-AUTOMATISIERUNG.md):
# „Wer ein Tag ergänzt, nimmt ein anderes weg." Steigt diese Zahl, muss hier
# eine Begründung stehen, nicht nur eine neue Zahl.
HEAD_SKRIPT_ERWARTET = 8

# Begründete Ausnahmen: data/robustheit_ausnahmen.yaml (Vertrag je Eintrag:
# pfad, regel, grund, entscheidung, faellig). Ausnahmen werden im Bericht
# genannt – sie verschwinden nicht still.
AUSNAHMEN = "data/robustheit_ausnahmen.yaml"

# Bausteine, die ihr eigenes Fangnetz brauchen (R6): Datei → Marker.
INSELN: dict[str, tuple[str, ...]] = {
    "static/premium/ff-rechner.js": ("ausfallHinweis", "verdrahten", "try {"),
    "static/premium/ff-summary-safety.js": (
        "document.body", "MutationObserver", "FEHLER_LIMIT", "anschliessen"),
    "static/premium/ff-newsletter.js": ("unterwegs", "anfragen", "zeitlimit"),
    "static/premium/ff-nl-praef.js": ("anfragen", "zeitlimit"),
    "static/premium/ff-feedback.js": ("Array.prototype.forEach.call", "zeitlimit"),
    "layouts/_partials/footer.html": ("knopfBauen", "copy-code", "textContent",
                                      "type = 'button'"),
}


# ------------------------------------------------------------ Grundlagen
_AUSNAHMEN_PUFFER: dict[str, list[dict]] = {}


def ausnahmen_laden(root: Path) -> list[dict]:
    """Begründete Ausnahmen – mit Rückfall-Parser, falls PyYAML fehlt.

    Ein Gate, das nur mit einer Zusatzbibliothek läuft, läuft im Zweifel
    genau dann nicht, wenn es gebraucht wird (frischer Container, PR-Lauf
    ohne Abhängigkeiten). Deshalb: PyYAML wenn da, sonst derselbe Vertrag
    aus der einfachen Listenstruktur gelesen.
    """
    pfad = root / AUSNAHMEN
    if not pfad.exists():
        return []
    roh = pfad.read_text(encoding="utf-8", errors="replace")
    try:
        import yaml  # type: ignore

        daten = yaml.safe_load(roh) or {}
        liste = daten.get("ausnahmen") or []
        return [e for e in liste if isinstance(e, dict)]
    except Exception:
        eintraege: list[dict] = []
        for block in re.split(r"(?m)^\s*-\s+pfad:", roh)[1:]:
            eintrag = {"pfad": ""}
            for zeile in ("pfad:" + block).splitlines():
                m = re.match(r"\s*(pfad|regel|grund|entscheidung|faellig)\s*:\s*(.*)$", zeile)
                if m:
                    eintrag[m.group(1)] = m.group(2).strip().strip('"')
            if eintrag.get("pfad"):
                eintraege.append(eintrag)
        return eintraege


def ausnahmen(root: Path, regel: str) -> set[str]:
    """Pfade, die für eine Regel begründet ausgenommen sind."""
    schlüssel = str(root)
    if schlüssel not in _AUSNAHMEN_PUFFER:
        _AUSNAHMEN_PUFFER[schlüssel] = ausnahmen_laden(root)
    return {e["pfad"] for e in _AUSNAHMEN_PUFFER[schlüssel]
            if str(e.get("regel", "")).strip() == regel}


def genutzte_ausnahmen(root: Path) -> list[str]:
    """Für den Bericht: welche Ausnahme wurde in Anspruch genommen."""
    schlüssel = str(root)
    if schlüssel not in _AUSNAHMEN_PUFFER:
        _AUSNAHMEN_PUFFER[schlüssel] = ausnahmen_laden(root)
    return [f"{e.get('regel')} · {e.get('pfad')} (fällig {e.get('faellig', 'unbekannt')})"
            for e in _AUSNAHMEN_PUFFER[schlüssel]]


def text(root: Path, rel: str) -> str:
    pfad = root / rel
    if not pfad.exists():
        return ""
    return pfad.read_text(encoding="utf-8", errors="replace")


def erstpartei_js(root: Path) -> list[str]:
    """Erstparteienskripte ohne Fremdcode (vendor/ bleibt außen vor)."""
    basis = root / PREMIUM
    if not basis.exists():
        return []
    return sorted(
        str(p.relative_to(root)) for p in basis.glob("*.js") if p.is_file()
    )


def skript_bloecke(quelltext: str) -> list[str]:
    """Inhalt aller <script>-Blöcke (ohne type=…-Dateninseln wie JSON-LD)."""
    return re.findall(r"<script(?![^>]*\btype=)[^>]*>(.*?)</script>",
                      quelltext, re.S | re.I)


def kommentarlos(zeile: str) -> bool:
    """True, wenn die Zeile kein reiner Kommentar ist (Befund zählt nur Code)."""
    s = zeile.strip()
    return not (s.startswith("//") or s.startswith("*") or s.startswith("/*"))


def fenster(quelltext: str, muster: str, vor: int = 300, nach: int = 200) -> Iterable[tuple[int, str]]:
    """Treffer mit Umgebung – für „liegt es in einem try/catch?"-Fragen."""
    for m in re.finditer(muster, quelltext):
        anfang = max(0, m.start() - vor)
        yield m.start(), quelltext[anfang:m.end() + nach]


# ------------------------------------------------------------ R1 Schicht
def pruefe_schicht(root: Path) -> list[str]:
    funde: list[str] = []
    inhalt = text(root, SCHICHT)
    if not inhalt:
        return [f"R1 {SCHICHT} fehlt – die zweite Stufe der Resilienzschicht existiert nicht"]
    if len(inhalt) < 1500:
        funde.append(f"R1 {SCHICHT} ist verdächtig klein ({len(inhalt)} Zeichen) – "
                     "eine Schicht ohne Inhalt ist keine")
    # Gegen den Code OHNE Kommentare: Eine Docstring, die `ablage` erwähnt,
    # erfüllt den Vertrag nicht – sonst täuscht die Schicht sich selbst.
    code = js_kommentarfrei(inhalt)
    for baustein in API:
        if not re.search(r"\b" + re.escape(baustein) + r"\b", code):
            funde.append(f"R1 {SCHICHT} bietet `{baustein}` nicht an – Bausteine, "
                         "die ihn abrufen, laufen ins Leere")
    if "FFRobust" not in code:
        funde.append(f"R1 {SCHICHT} hängt sich nicht an window.FFRobust")
    if not inhalt.lstrip().startswith(("/*", "(function", "'use strict'", ";")):
        funde.append(f"R1 {SCHICHT} beginnt unerwartet – keine IIFE/kein Kommentar")
    return funde


# ------------------------------------------------------------ R2 Bootstrap
def pruefe_bootstrap(root: Path) -> list[str]:
    funde: list[str] = []
    roh = text(root, BOOTSTRAP)
    if not roh:
        return [f"R2 {BOOTSTRAP} fehlt – ohne Bootstrap im <head> ist jeder Fehler "
                "der Inline-Skripte unsichtbar"]
    inhalt = hugo_kommentarfrei(roh)
    bloecke = skript_bloecke(inhalt)
    gemeinsame = [b for b in bloecke if "ff_cookie_consent" in b and "FFRobust" in b]
    if not gemeinsame:
        funde.append("R2 Der Robustheits-Bootstrap teilt sich kein <script> mit dem "
                     "Consent-Vorlauf: entweder fehlt er im <head>, oder er ist ein "
                     "EIGENES Head-Kind (DOM-Budget: 58 ist die Lighthouse-Grenze, "
                     "docs/LAYOUT-AUTOMATISIERUNG.md – „wer ein Tag ergänzt, nimmt "
                     "ein anderes weg\")")
    tags = len(re.findall(r"<script", inhalt, re.I))
    if tags != HEAD_SKRIPT_ERWARTET:
        funde.append(f"R2 {BOOTSTRAP} trägt {tags} <script>-Tags, eingefroren sind "
                     f"{HEAD_SKRIPT_ERWARTET}: Jedes weitere Tag ist ein zusätzliches "
                     "Head-Kind (Lighthouse-Grenze 58). Entweder zusammenlegen, "
                     "ein anderes Tag wegnehmen oder HEAD_SKRIPT_ERWARTET mit "
                     "Begründung anheben (docs/LAYOUT-AUTOMATISIERUNG.md)")
    for pflicht in ("unhandledrejection", "addEventListener('error'", "R.melden",
                    "R.sicher", "R.hole"):
        if pflicht not in inhalt:
            funde.append(f"R2 Bootstrap in {BOOTSTRAP} ohne `{pflicht}` – "
                         "der Horcher ist unvollständig")
    if "}, true);" not in inhalt:
        funde.append("R2 Der Fehler-Horcher läuft nicht in der Capture-Phase "
                     "(`}, true)`): Ressourcen-Fehler (Bild, Skript, CSS) bubble'n "
                     "nicht und blieben stumm")
    return funde


# ------------------------------------------------------------ R3 Idempotenz
def pruefe_idempotenz(root: Path) -> list[str]:
    funde: list[str] = []
    for rel in (BOOTSTRAP, SCHICHT):
        inhalt = text(root, rel)
        if not inhalt:
            continue
        if "R.boot" not in inhalt and "FFRobust.boot" not in inhalt:
            funde.append(f"R3 {rel} meldet sich ohne `boot`-Marke an – doppelte "
                         "Einbindung verdoppelt jeden Befund")
        horcher = len(re.findall(r"addEventListener\('unhandledrejection'", inhalt))
        if horcher > 1:
            funde.append(f"R3 {rel} hat {horcher} unhandledrejection-Horcher – "
                         "ein Befund würde mehrfach gezählt")
    return funde


# ------------------------------------------------------------ R4 Zeitlimit
def pruefe_zeitlimit(root: Path) -> list[str]:
    funde: list[str] = []
    for rel in erstpartei_js(root):
        if rel.endswith("ff-robust.js"):
            continue  # die Schicht selbst IST das Zeitlimit
        if rel in ausnahmen(root, "R4"):
            continue
        inhalt = text(root, rel)
        zeilen = inhalt.splitlines()
        for zeile_nr, zeile in enumerate(zeilen, start=1):
            if not kommentarlos(zeile):
                continue
            # \bfetch: „prefetch(" ist ein Link-Hinweis, kein Netzaufruf.
            if not re.search(r"\bfetch\s*\(", zeile):
                continue
            umgebung = "\n".join(zeilen[max(0, zeile_nr - 13):zeile_nr + 12])
            if not re.search(r"\bhole\s*\(|AbortController|zeitlimit", umgebung):
                funde.append(f"R4 {rel}:{zeile_nr} ruft fetch() ohne Zeitlimit – "
                             "ein hängender Dienst friert den Baustein ein "
                             "(FFRobust.hole, AbortController oder `zeitlimit`)")
        # Durchreichen ist erlaubt (Helferfunktion) – aber dann muss das
        # Zeitlimit irgendwo in derselben Datei gesetzt werden.
        if re.search(r"\.hole\s*\(", inhalt) and "zeitlimit" not in inhalt:
            funde.append(f"R4 {rel} ruft FFRobust.hole(), setzt aber nirgends "
                         "`zeitlimit` – dann gilt die Vorgabe, und die ist "
                         "eine Entscheidung, keine Versehentlichkeit")
    return funde


# ------------------------------------------------------------ R5 Service Worker
SW_PFLICHTEN: tuple[tuple[str, str], ...] = (
    (r"async function fach\(\)", "Cache-Öffnung im Fangnetz (H1 fail-open)"),
    (r"return null;", "fail-open: ohne Cache geht der Request ins Netz"),
    (r"OFFLINE_PFAD", "Offline-Fangnetz (H2)"),
    (r"404\.html", "die eigene 404-Seite als Offline-Fangnetz"),
    (r"status: 503", "offline ehrlich als 503 ausgeliefert"),
    (r"headers\.get\('range'\)", "Range-Anfragen gehen ins Netz (H3)"),
    (r"EIGEN_PFAD", "/sw.js wird nie cache-first bedient (H4)"),
    (r"'SKIP_WAITING'", "Seite darf sich selbst befreien (message-Horcher)"),
    (r"try \{ self\.skipWaiting\(\); \} catch", "skipWaiting im Fangnetz – ein Wurf "
     "darf die Installation nicht blockieren"),
)


def pruefe_sw(root: Path) -> list[str]:
    funde: list[str] = []
    inhalt = text(root, SW)
    if not inhalt:
        return [f"R5 {SW} fehlt – ohne Service Worker kein Langzeit-Cache und "
                "kein Offline-Fangnetz"]
    for muster, warum in SW_PFLICHTEN:
        if not re.search(muster, inhalt):
            funde.append(f"R5 {SW}: {warum} fehlt ({muster})")
    # PRECACHE muss die Offline-Seite wirklich vorladen, nicht nur kennen.
    precache = re.search(r"const PRECACHE = \[(.*?)\];", inhalt, re.S)
    if not precache:
        funde.append(f"R5 {SW}: PRECACHE-Liste nicht gefunden")
    elif "OFFLINE_PFAD" not in precache.group(1):
        funde.append(f"R5 {SW}: OFFLINE_PFAD steht nicht in PRECACHE – das "
                     "Offline-Fangnetz wäre beim ersten Ausfall nicht geladen")
    # Jede Cache-Öffnung muss in einem try/catch stehen (fail-open).
    for stelle, umgebung in fenster(inhalt, r"caches\.open\(", vor=200, nach=120):
        if "try {" not in umgebung:
            funde.append(f"R5 {SW}: caches.open() bei Zeichen {stelle} ohne "
                         "try/catch – ein Cache-Fehler verschluckt den Request")
    # networkFirst/cacheFirst dürfen nicht nackt `await fetch` ohne Netz-Fangnetz.
    for name in ("cacheFirst", "networkFirst"):
        block = re.search(r"async function " + name + r"\(req\) \{(.*?)\n\}",
                          inhalt, re.S)
        if not block:
            funde.append(f"R5 {SW}: Strategie {name} fehlt")
        elif "catch" not in block.group(1):
            funde.append(f"R5 {SW}: {name} hat kein catch – ein Netzfehler wird "
                         "zum Seitenfehler")
    return funde


# ------------------------------------------------------------ R6 Inseln
def pruefe_inseln(root: Path) -> list[str]:
    funde: list[str] = []
    for rel, marker in INSELN.items():
        inhalt = text(root, rel)
        if not inhalt:
            funde.append(f"R6 {rel} fehlt – der Baustein ist weg, nicht nur sein Fangnetz")
            continue
        for m in marker:
            if m not in inhalt:
                funde.append(f"R6 {rel} ohne `{m}` – das Fangnetz dieses Bausteins "
                             "ist unvollständig")
    # Ein Fangnetz, das keinen Satz sagt, ist keines: Der Ausfall-Hinweis muss
    # als role="status" angekündigt sein (sonst bleibt er für Screenreader stumm).
    for rel in ("static/premium/ff-rechner.js", SCHICHT):
        inhalt = text(root, rel)
        if inhalt and "ff-robust-hinweis" in inhalt and 'role", "status"' not in inhalt \
                and "role=\"status\"" not in inhalt and "'role', 'status'" not in inhalt:
            funde.append(f"R6 {rel} erzeugt einen Ausfall-Hinweis ohne role=status – "
                         "der Satz bliebe für Screenreader stumm (WCAG 4.1.3)")
    return funde


# ------------------------------------------------------------ R7 Markup
VERBOTEN = (
    (r"document\.write\s*\(", "document.write"),
    (r"(?<![\w.])eval\s*\(", "eval()"),
    (r"insertAdjacentHTML\s*\(", "insertAdjacentHTML"),
    (r"\.outerHTML\s*=", "outerHTML-Zuweisung"),
)

LITERAL_EINFACH = re.compile(r"'(?:[^'\\]|\\.)*'", re.S)
LITERAL_DOPPELT = re.compile(r'"(?:[^"\\]|\\.)*"', re.S)
BEZEICHNER = re.compile(r"[A-Za-z_$][\w$]*")


def js_kommentarfrei(inhalt: str) -> str:
    """Blockkommentare entfernen (Zeilennummern bleiben über \n-Ersatz erhalten)."""
    def ersetzer(m: re.Match) -> str:
        return "\n" * m.group(0).count("\n")
    return re.sub(r"/\*.*?\*/", ersetzer, inhalt, flags=re.S)


def hugo_kommentarfrei(inhalt: str) -> str:
    def ersetzer(m: re.Match) -> str:
        return "\n" * m.group(0).count("\n")
    return re.sub(r"\{\{-?\s*/\*.*?\*/\s*-?\}\}", ersetzer, inhalt, flags=re.S)


def statische_konstanten(inhalt: str) -> dict[str, str]:
    """Namen, deren Wert ausschließlich aus Literalen gebaut ist."""
    roh: dict[str, str] = {}
    for m in re.finditer(r"(?:var|const|let)\s+([A-Za-z_$][\w$]*)\s*=\s*([^;]*);",
                         inhalt, re.S):
        roh[m.group(1)] = m.group(1), m.group(2)
    bekannt: dict[str, str] = {}
    for name, (_n, ausdruck) in roh.items():
        if ist_statisch(ausdruck, bekannt, tiefe=0):
            bekannt[name] = ausdruck
    return bekannt


def ist_statisch(ausdruck: str, konstanten: dict[str, str], tiefe: int = 0) -> bool:
    """True, wenn der Ausdruck nur Literale und bekannte statische Namen nutzt."""
    if tiefe > 3:
        return False
    for teil in re.split(r"\s*\+\s*", ausdruck.strip()):
        teil = teil.strip()
        if not teil:
            return False
        if LITERAL_EINFACH.fullmatch(teil) or LITERAL_DOPPELT.fullmatch(teil):
            continue
        if BEZEICHNER.fullmatch(teil) and teil in konstanten:
            if ist_statisch(konstanten[teil], konstanten, tiefe + 1):
                continue
        return False
    return True


def layout_dateien(root: Path) -> list[str]:
    basis = root / "layouts"
    if not basis.exists():
        return []
    return sorted(str(p.relative_to(root)) for p in basis.rglob("*.html"))


def pruefe_markup(root: Path) -> list[str]:
    funde: list[str] = []
    verboten_pfade = ausnahmen(root, "R7")
    for rel in erstpartei_js(root) + layout_dateien(root):
        if rel in verboten_pfade:
            continue
        roh = text(root, rel)
        if not roh:
            continue
        inhalt = hugo_kommentarfrei(js_kommentarfrei(roh)) if rel.endswith(".js") \
            else hugo_kommentarfrei(roh)
        zeilen = inhalt.splitlines()
        for zeile_nr, zeile in enumerate(zeilen, start=1):
            if not kommentarlos(zeile):
                continue
            for muster, name in VERBOTEN:
                if re.search(muster, zeile):
                    funde.append(f"R7 {rel}:{zeile_nr} benutzt {name} – Markup aus "
                                 "dem Nichts ist die klassische Einschleusung")
        konstanten = statische_konstanten(inhalt)
        for m in re.finditer(r"innerHTML\s*=\s*([^;]*);", inhalt, re.S):
            zeile_nr = inhalt[:m.start()].count("\n") + 1
            if zeile_nr <= len(zeilen) and not kommentarlos(zeilen[zeile_nr - 1]):
                continue
            if not ist_statisch(m.group(1), konstanten):
                funde.append(f"R7 {rel}:{zeile_nr} schreibt innerHTML aus etwas "
                             "anderem als einem statischen Literal – damit kann "
                             "berechneter oder fremder Text ins Markup "
                             "(textContent/createElement sind der Weg)")
    return funde


# ------------------------------------------------------------ R8 Speicher
def pruefe_speicher(root: Path) -> list[str]:
    funde: list[str] = []
    erlaubt = ausnahmen(root, "R8")
    for rel in erstpartei_js(root) + [BOOTSTRAP, EINBINDUNG, FUSS]:
        if rel in erlaubt:
            continue
        inhalt = text(root, rel)
        if not inhalt:
            continue
        for stelle, umgebung in fenster(inhalt, r"(localStorage|sessionStorage)\.",
                                        vor=320, nach=80):
            if "try {" in umgebung or "try{" in umgebung or "ablage" in umgebung:
                continue
            zeile = inhalt[:stelle].count("\n") + 1
            funde.append(f"R8 {rel}:{zeile} greift ohne try/catch auf Web Storage zu – "
                         "Safari privat, blockierte Cookies und volle Quota werfen, "
                         "und der Baustein stirbt mitten im Bedienen")
    return funde


# ------------------------------------------------------------ R9 Hinweis
def pruefe_hinweis(root: Path) -> list[str]:
    funde: list[str] = []
    css = text(root, CSS)
    if not css:
        return [f"R9 {CSS} fehlt – der Ausfall-Satz wäre ungestylt (und im Dark Mode "
                "unlesbar)"]
    if ".ff-robust-hinweis" not in css:
        funde.append(f"R9 {CSS} definiert .ff-robust-hinweis nicht")
    if ':root[data-theme="dark"] .ff-robust-hinweis' not in css:
        funde.append(f"R9 {CSS} hat keine Dark-Variante des Hinweises "
                     "(PRODUCT.md §6: jede Farbe braucht eine)")
    if re.search(r"transition:\s*(?!none)(?!(transform|opacity|color|border-color|background-color|background)\b)[a-z-]+", css):
        funde.append(f"R9 {CSS} animiert eine Layout-Eigenschaft (DESIGN.md §7: "
                     "nur transform/opacity/Farbe)")
    schicht = text(root, SCHICHT)
    if schicht and "ff-robust-hinweis" in schicht and "role" not in schicht:
        funde.append(f"R9 {SCHICHT} erzeugt den Hinweis ohne role – stumm für "
                     "Screenreader")
    return funde


# ------------------------------------------------------------ R10 Syntax
def pruefe_syntax(root: Path) -> list[str]:
    node = shutil.which("node")
    if not node:
        return []  # ohne node keine Aussage – kein falsches Grün, kein falsches Rot
    funde: list[str] = []
    for rel in erstpartei_js(root) + [SW]:
        pfad = root / rel
        if not pfad.exists():
            continue
        proc = subprocess.run([node, "--check", str(pfad)],
                              capture_output=True, text=True)
        if proc.returncode != 0:
            funde.append(f"R10 {rel} ist nicht parsebar: "
                         f"{(proc.stderr or proc.stdout).strip().splitlines()[-1] if (proc.stderr or proc.stdout) else 'unbekannt'}")
    return funde


# ------------------------------------------------------------ R11 First-Party
def pruefe_first_party(root: Path) -> list[str]:
    funde: list[str] = []
    for rel in (SCHICHT,):
        inhalt = text(root, rel)
        if inhalt and re.search(r"https?://", inhalt):
            funde.append(f"R11 {rel} nennt eine fremde Domain – die Resilienzschicht "
                         "darf nichts nachladen und nichts wohin senden")
    bootstrap = text(root, BOOTSTRAP)
    for block in skript_bloecke(bootstrap):
        if "FFRobust" in block and re.search(r"https?://", block):
            funde.append(f"R11 Der Bootstrap in {BOOTSTRAP} nennt eine fremde Domain")
    return funde


# ------------------------------------------------------------ R12 Einbindung
def pruefe_einbindung(root: Path) -> list[str]:
    funde: list[str] = []
    treffer = 0
    for rel in layout_dateien(root):
        inhalt = text(root, rel)
        # Nur echte Einbindungen zählen – ein Dateipfad in einem Kommentar
        # ist Dokumentation, kein zweiter Ladevorgang.
        for zeile in inhalt.splitlines():
            if "premium/ff-robust.js" in zeile and "<script" in zeile:
                treffer += 1
    if treffer == 0:
        funde.append("R12 ff-robust.js wird in keinem Layout geladen – die Schicht "
                     "existiert, läuft aber nie")
    elif treffer > 1:
        funde.append(f"R12 ff-robust.js wird {treffer}× geladen – zweimal dieselbe "
                     "Schicht kostet Ladezeit und verdoppelt Befunde")
    einbindung = text(root, EINBINDUNG)
    if "premium/ff-robust.js" in einbindung and 'partial "asset_url.html"' not in einbindung:
        funde.append(f"R12 {EINBINDUNG} lädt die Schicht ohne asset_url – kein "
                     "?v=<SHA>, also kein Cache-Busting nach einem Deploy")
    return funde


REGELN: tuple[tuple[str, str, Callable[[Path], list[str]]], ...] = (
    ("R1", "Resilienzschicht vorhanden und vollständig", pruefe_schicht),
    ("R2", "Bootstrap im <head>, ohne neues Head-Kind", pruefe_bootstrap),
    ("R3", "Fehler-Horcher sind idempotent", pruefe_idempotenz),
    ("R4", "Jeder Fetch hat ein Zeitlimit", pruefe_zeitlimit),
    ("R5", "Service Worker ist fail-open und offline-fähig", pruefe_sw),
    ("R6", "Interaktive Bausteine haben ein Fangnetz", pruefe_inseln),
    ("R7", "Markup entsteht nie aus fremdem Text", pruefe_markup),
    ("R8", "Web Storage liegt immer im try/catch", pruefe_speicher),
    ("R9", "Der Ausfall-Satz ist sichtbar, dunkeltauglich, angekündigt", pruefe_hinweis),
    ("R10", "Jedes Skript ist parsebar", pruefe_syntax),
    ("R11", "Resilienz ist first-party", pruefe_first_party),
    ("R12", "Die Schicht läuft genau einmal", pruefe_einbindung),
)


# ------------------------------------------------------------ Gebaute Wahrheit
def pruefe_public(public: Path) -> list[str]:
    """Nach dem Build: Steht das Fangnetz auch in der AUSGELIEFERTEN Seite?"""
    funde: list[str] = []
    if not public.exists():
        return [f"R5 public/ fehlt ({public}) – ohne Build keine Aussage über die "
                "ausgelieferte Wahrheit"]
    sw = public / "sw.js"
    if not sw.exists():
        funde.append("R5 public/sw.js fehlt – der Service Worker wird nicht ausgeliefert")
    else:
        inhalt = sw.read_text(encoding="utf-8", errors="replace")
        for muster, warum in (("404.html", "Offline-Fangnetz"),
                              ("range", "Range-Umgehung"),
                              ("SKIP_WAITING", "Selbstbefreiung")):
            if muster not in inhalt:
                funde.append(f"R5 public/sw.js ohne {warum} ({muster})")
        if "{{" in inhalt:
            funde.append("R5 public/sw.js enthält Hugo-Platzhalter – die Vorlage "
                         "wurde nicht gerendert")
    seite = public / "index.html"
    if seite.exists():
        html = seite.read_text(encoding="utf-8", errors="replace")
        if "FFRobust" not in html:
            funde.append("R2 public/index.html ohne Bootstrap – die ausgelieferte "
                         "Seite hat keinen Fehler-Horcher")
        if "ff-robust.js" not in html:
            funde.append("R1 public/index.html lädt ff-robust.js nicht")
    return funde


# ------------------------------------------------------------ Selbsttest
def selbsttest() -> int:
    """Der Detektor muss sich selbst beweisen: Sabotagen finden, Sauberes
    freigeben. Ein Gate, das nur grün kennt, ist schlimmer als keines."""
    fehler: list[str] = []
    quelle = ROOT

    with tempfile.TemporaryDirectory(prefix="robustheit-") as tmp_name:
        sandbox = Path(tmp_name)

        def baum() -> Path:
            """Kopie der echten Dateien (nur die, die das Gate liest)."""
            ziel = Path(tempfile.mkdtemp(prefix="fall-", dir=sandbox))
            for rel in [SCHICHT, BOOTSTRAP, EINBINDUNG, SW, FUSS, CSS] + erstpartei_js(quelle):
                original = quelle / rel
                if not original.exists():
                    continue
                kopie = ziel / rel
                kopie.parent.mkdir(parents=True, exist_ok=True)
                kopie.write_text(original.read_text(encoding="utf-8"), encoding="utf-8")
            return ziel

        def lauf(root: Path) -> list[str]:
            funde: list[str] = []
            for _, _, pruefung in REGELN:
                funde.extend(pruefung(root))
            return funde

        # FALL 0: Der echte Stand ist grün (keine Selbsttäuschung).
        sauber = baum()
        grund_funde = lauf(sauber)
        if grund_funde:
            fehler.append("Fall0 sauberer Stand meldet Funde: " + "; ".join(sorted(set(f[:70] for f in grund_funde))))

        def sabotage(name: str, rel: str, alt: str, neu: str, regel: str,
                     alle: bool = False) -> None:
            """Echte Datei verbiegen und prüfen, ob die Regel es merkt."""
            baum_root = baum()
            pfad = baum_root / rel
            if not pfad.exists():
                fehler.append(f"{name}: {rel} fehlt im Prüfbaum")
                return
            inhalt = pfad.read_text(encoding="utf-8")
            if alt not in inhalt:
                fehler.append(f"{name}: Sabotage-Anker nicht gefunden in {rel}")
                return
            pfad.write_text(inhalt.replace(alt, neu) if alle
                            else inhalt.replace(alt, neu, 1), encoding="utf-8")
            funde = lauf(baum_root)
            if not any(f.startswith(regel) for f in funde):
                fehler.append(f"{name}: {regel} schlägt nicht an "
                              f"(Funde: {[f[:60] for f in funde][:3]})")

        def fixture(name: str, rel: str, inhalt: str, regel: str) -> None:
            """Künstlichen Baustein in den Prüfbaum legen und die Regel fordern.

            Für Regeln, deren Sabotage an der echten Datei zu klein wäre, um
            die Umgebungssuche zu täuschen (R4 prüft ±12 Zeilen)."""
            baum_root = baum()
            pfad = baum_root / rel
            pfad.parent.mkdir(parents=True, exist_ok=True)
            pfad.write_text(inhalt, encoding="utf-8")
            funde = lauf(baum_root)
            if not any(f.startswith(regel) and rel in f for f in funde):
                fehler.append(f"{name}: {regel} schlägt auf der Fixture nicht an "
                              f"(Funde: {[f[:60] for f in funde][:3]})")

        # FALL 1: Service Worker öffnet den Cache ohne Fangnetz.
        sabotage("Fall1", SW,
                 "  try {\n    if (typeof caches === 'undefined') return null;\n    return await caches.open(CACHE);\n  } catch (e) {\n    return null;\n  }",
                 "  return await caches.open(CACHE);", "R5")

        # FALL 2: Offline-Fangnetz aus der Vorladung entfernt.
        sabotage("Fall2", SW,
                 "  OFFLINE_PFAD\n];", "];", "R5")

        # FALL 3: Range-Anfragen landen im Cache (Audio-Spulen bricht).
        sabotage("Fall3", SW,
                 "  try { if (req.headers.get('range')) return; } catch (e) {}",
                 "  /* range entfernt */", "R5")

        # FALL 4: Bootstrap bekommt ein eigenes Head-Skript (DOM-Budget).
        sabotage("Fall4", BOOTSTRAP,
                 "})();\n\n/* ---- Robustheits-Bootstrap",
                 "})();\n</script>\n<script>\n/* ---- Robustheits-Bootstrap", "R2")

        # FALL 5: Fetch ohne Zeitlimit (Fixture – an der echten Datei wäre die
        # Umgebung von ±12 Zeilen noch voll mit den Helfern).
        fixture("Fall5", "static/premium/ff-pruef-ohne-zeitlimit.js",
                "(function () {\n  'use strict';\n"
                "  function laden(url) {\n    return window.fetch(url).then(function (a) { return a.json(); });\n  }\n"
                "  window.__pruef = laden;\n})();\n", "R4")

        # FALL 5b: Derselbe Baustein MIT Zeitlimit muss durchgehen (Gegenprobe).
        gegen5 = baum()
        pfad5 = gegen5 / "static/premium/ff-pruef-mit-zeitlimit.js"
        pfad5.write_text("(function () {\n  'use strict';\n"
                         "  function laden(url) {\n"
                         "    return window.FFRobust.hole(url, { zeitlimit: 8000 });\n  }\n"
                         "  window.__pruef = laden;\n})();\n", encoding="utf-8")
        if any(f.startswith("R4") and "ff-pruef-mit-zeitlimit" in f for f in lauf(gegen5)):
            fehler.append("Gegenprobe 5b: ein Fetch MIT Zeitlimit wird zu Unrecht "
                          "gemeldet (R4 ist zu scharf)")

        # FALL 6: innerHTML aus einer Variablen.
        sabotage("Fall6", "static/premium/ff-rechner.js",
                 "  function robust() {",
                 "  function boese(text) { var d = document.createElement('p'); d.innerHTML = text; return d; }\n\n  function robust() {",
                 "R7")

        # FALL 7: document.write – statisch erlaubt, hier verboten.
        sabotage("Fall7", "static/premium/ff-feedback.js",
                 "(function () {\n  'use strict';",
                 "(function () {\n  'use strict';\n  document.write('<p>x</p>');", "R7")

        # FALL 8: Speicherzugriff ohne Fangnetz.
        sabotage("Fall8", "static/premium/ff-newsletter.js",
                 "    try { bereits = localStorage.getItem(SCHLUESSEL) === 'angemeldet'; } catch (e) { bereits = false; }",
                 "    bereits = localStorage.getItem(SCHLUESSEL) === 'angemeldet';", "R8")

        # FALL 9: Schicht wird nicht mehr geladen.
        sabotage("Fall9", EINBINDUNG,
                 '<script defer src="{{ partial "asset_url.html" "premium/ff-robust.js" }}"></script>',
                 '<!-- Schicht entfernt -->', "R12")

        # FALL 10: Dark-Variante des Hinweises fehlt.
        sabotage("Fall10", CSS,
                 ':root[data-theme="dark"] .ff-robust-hinweis {',
                 '.ff-robust-hinweis--irrelevant {', "R9")

        # FALL 11: Fangnetz des Rechners entfernt (Insel-Marker).
        sabotage("Fall11", "static/premium/ff-summary-safety.js",
                 "FEHLER_LIMIT", "GRENZE_ENTFERNT", "R6", alle=True)

        # FALL 12: Schicht ohne API-Baustein.
        sabotage("Fall12", SCHICHT, "zwischenablage", "clipboardWeg", "R1", alle=True)

        # GEGENPROBE: Ein statisches innerHTML-Literal ist erlaubt.
        gegen = baum()
        pfad = gegen / "static/premium/ff-feedback.js"
        inhalt = pfad.read_text(encoding="utf-8")
        pfad.write_text(inhalt.replace(
            "(function () {\n  'use strict';",
            "(function () {\n  'use strict';\n  var x = document.createElement('p'); x.innerHTML = '<span class=\"a\"></span>';",
            1), encoding="utf-8")
        if any(f.startswith("R7") for f in lauf(gegen)):
            fehler.append("Gegenprobe: statisches innerHTML-Literal wird zu Unrecht "
                          "gemeldet (R7 ist zu scharf)")

    if fehler:
        print("❌ SELBSTTEST FEHLGESCHLAGEN")
        for f in fehler:
            print("   · " + f)
        return 1
    print("✅ SELBSTTEST OK – 13 Sabotage-Proben erkannt, 2 Gegenproben freigegeben, "
          "echter Stand grün")
    return 0


# ------------------------------------------------------------ Bericht
def bericht(funde: list[str], modus: str, root: Path | None = None) -> str:
    zeilen = ["# 🔎 ROBUSTHEITS-GATE (Vertrag C31)", "",
              f"**Modus:** {modus} · **Regeln:** {len(REGELN)} · "
              f"**Funde:** {len(funde)}", ""]
    if root is not None:
        ausnahmelist = genutzte_ausnahmen(root)
        if ausnahmelist:
            zeilen += ["**Begründete Ausnahmen** (data/robustheit_ausnahmen.yaml):"]
            zeilen += [f"- {a}" for a in ausnahmelist]
            zeilen.append("")
    if not funde:
        zeilen += ["🎉 Jeder Baustein hat sein Fangnetz: Fehler werden gefangen, "
                   "gemeldet und – wo der Leser es braucht – in einen Satz gefasst.",
                   "",
                   "Geprüft: Resilienzschicht, Bootstrap im <head>, Zeitlimits, "
                   "Service Worker (fail-open + offline), Insel-Fangnetze, "
                   "Markup-Sicherheit, Web Storage, Hinweis-Stil, Syntax, "
                   "First-Party, Einbindung."]
    else:
        nach_regel: dict[str, list[str]] = {}
        for f in funde:
            nach_regel.setdefault(f.split(" ", 1)[0], []).append(f)
        for regel, _, titel in REGELN:
            if regel not in nach_regel:
                continue
            zeilen += [f"## ✗ {regel} – {titel}", ""]
            zeilen += [f"- {f}" for f in nach_regel[regel]]
            zeilen.append("")
    zeilen += ["", "_Runbook: docs/ANLEITUNG-ROBUSTHEIT.md · "
               "Hintergrund: ROBUSTHEIT-PREMIUM-2026-10-07.md_"]
    return "\n".join(zeilen)


# ------------------------------------------------------------ CLI
def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Robustheits-Gate (Vertrag C31)")
    parser.add_argument("--source-only", action="store_true",
                        help="nur die Quelle prüfen (ohne Hugo-Build)")
    parser.add_argument("--public", metavar="VERZ", default=None,
                        help="gebaute Wahrheit prüfen (public/)")
    parser.add_argument("--root", metavar="VERZ", default=None,
                        help="abweichende Repo-Wurzel (Prüfbaum, Tests)")
    parser.add_argument("--json", action="store_true", help="maschinenlesbar")
    parser.add_argument("--no-report", action="store_true", help="kein Textbericht")
    parser.add_argument("--strict", action="store_true",
                        help="auch fehlendes node als Befund werten")
    parser.add_argument("--selftest", action="store_true",
                        help="den Detektor selbst beweisen")
    args = parser.parse_args(argv)

    if args.selftest:
        return selbsttest()

    root = Path(args.root).resolve() if args.root else ROOT
    if not root.exists():
        print(f"❌ Repo-Wurzel nicht gefunden: {root}", file=sys.stderr)
        return 2

    funde: list[str] = []
    for _, _, pruefung in REGELN:
        try:
            funde.extend(pruefung(root))
        except Exception as fehler:  # ein kaputter Prüfer darf kein Grün liefern
            funde.append(f"R0 Prüfer selbst fehlgeschlagen ({pruefung.__name__}): {fehler}")

    if args.public:
        funde.extend(pruefe_public(Path(args.public)))
    if args.strict and not shutil.which("node"):
        funde.append("R10 node fehlt – die Syntaxprüfung konnte nicht laufen "
                     "(--strict wertet das als Befund)")

    if args.json:
        print(json.dumps({
            "gate": "robustheit",
            "modus": "public" if args.public else "source",
            "regeln": [r[0] for r in REGELN],
            "funde": funde,
            "ok": not funde,
        }, ensure_ascii=False, indent=2))
        return 1 if funde else 0

    if not args.no_report:
        print(bericht(funde, "gebaute Wahrheit" if args.public else "Quelle", root))
    if funde:
        print(f"\n🛑 {len(funde)} Befund(e) – Robustheit ist verletzt. "
              "Das Gate heilt nicht selbst: Fangnetze, die sich selbst "
              "wieder einhängen, wären keine.")
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.exit(2)
