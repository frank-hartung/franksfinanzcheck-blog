#!/usr/bin/env python3
"""Figma-Qualitäts-Gate: 36 Kriterien zwischen SSOT, CSS-Bestand und Plugin.

WOZU DIESE DATEI EXISTIERT
--------------------------
Das Figma-Handoff ist eine zweite Darstellung des Designs. Sobald es
zwei Darstellungen gibt, gibt es auch zwei Wahrheiten – und die zweite
veraltet lautlos. `scripts/design_handoff.py` erzeugt die Artefakte,
dieses Gate prüft, ob sie noch das behaupten, was Marke, CSS und
Regelwerk tatsächlich hergeben.

Die entscheidende Frage ist nicht „existiert eine Datei?“, sondern
„stammt sie aus der Quelle?“ Deshalb prüft das Gate nicht nur
Anwesenheit, sondern Hashes, Verträge und Widersprüche:

  A  Quelle & Verträge    Hat die SSOT selbst Löcher? (P1–P12)
  B  CSS-Vertrag          Gibt es die dokumentierten Klassen wirklich? (P13–P17)
  C  Artefakte            Stimmen Hashes, Netzfreiheit, Vollständigkeit? (P18–P27)
  D  Plugin               Baut es, ohne Figma und ohne Netz? (P28–P33)
  E  Governance           Ist der Figma-freie Weg begehbar dokumentiert? (P34–P36)

EIN KRITERIUM, DAS NIE FEHLSCHLÄGT, IST KEIN KRITERIUM
------------------------------------------------------
Jeder Befund trägt `besitzer` (auto = Generator heilt es, human = nur
ein Mensch), `schwere` (P1 blockiert, P2 muss vor Merge, P3 Hinweis)
und `kanal` (wohin gemeldet wird). Ein P1 ohne Heilmöglichkeit ist eine
Sackgasse – deshalb nennt jeder Befund einen `fix`.

AUFRUF
------
  python3 scripts/figma_quality_gate.py            # alle 36 Kriterien
  python3 scripts/figma_quality_gate.py --json     # maschinenlesbar
  python3 scripts/figma_quality_gate.py --nur P9   # ein Kriterium
  python3 scripts/figma_quality_gate.py --selftest # Gate gegen sich selbst
  python3 scripts/figma_quality_gate.py --liste    # Kriterienkatalog

EXIT-CODES
----------
  0 = bestanden (nur P3-Hinweise erlaubt)
  1 = P1/P2-Befund
  2 = Gate selbst konnte nicht laufen (fehlende Quelle)

Ehrliche Grenze: Dieses Gate prüft Token-Paarungen und Verträge, nicht
gerenderte Flächen. Ob ein Fokusring im Browser wirklich sichtbar ist,
entscheidet e2e/design-metrics.mjs – nicht diese Datei.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import design_handoff as handoff  # noqa: E402

SOURCE = handoff.SOURCE
RULES = handoff.RULES
OUT = handoff.OUT
PLUGIN = handoff.PLUGIN_OUT
PLUGIN_SOURCE = handoff.PLUGIN_SOURCE
PLUGIN_CODE = PLUGIN / "code.js"
PLUGIN_MANIFEST = PLUGIN / "manifest.json"
PLUGIN_UI = PLUGIN / "ui.html"
DOKU = ROOT / "docs/ANLEITUNG-FIGMA-EINRICHTUNG.md"
WORKFLOW = ROOT / ".github/workflows/design-varianten.yml"

# Kanäle: wohin ein Befund gehört. `repo` = PR, `figma` = Handoff-Ordner,
# `agentur` = die Design-Übergabe an den Menschen.
KANAL_REPO = "repo"
KANAL_FIGMA = "figma-handoff"
KANAL_AGENTUR = "design-uebergabe"


@dataclass
class Befund:
    """Ein einzelner Verstoß – mit Besitzer, Schwere und Reparaturweg."""

    kriterium: str
    text: str
    schwere: str = "P2"          # P1 blockiert, P2 vor Merge, P3 Hinweis
    besitzer: str = "human"      # auto = Generator kann heilen
    kanal: str = KANAL_REPO
    fix: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "kriterium": self.kriterium,
            "text": self.text,
            "schwere": self.schwere,
            "besitzer": self.besitzer,
            "kanal": self.kanal,
            "fix": self.fix,
        }


@dataclass
class Pruefung:
    """Ein Kriterium: Name, Frage, Prüffunktion, Standard-Schwere."""

    id: str
    name: str
    frage: str
    lauf: Callable[[dict[str, Any], dict[str, Any]], list[Befund]]
    schwere: str = "P2"
    besitzer: str = "human"
    kanal: str = KANAL_REPO
    fix: str = ""


# ====================================================================
#  Hilfen
# ====================================================================
def _css() -> str:
    return handoff.css_bestand()


def _artefakt(name: str) -> str | None:
    pfad = OUT / name
    return pfad.read_text(encoding="utf-8") if pfad.exists() else None


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _echte_farben(css: str) -> set[str]:
    return {f"#{wert.upper()}" for wert in re.findall(r"#([0-9A-Fa-f]{6})\b", css)}


def _b(kriterium: str, text: str, **abweichung: str) -> Befund:
    """Befund mit den Standardwerten seines Kriteriums.

    Die Vorgaben kommen aus dem Katalog (Schwere, Besitzer, Kanal, Fix),
    damit eine Regel nur an EINER Stelle definiert ist. Ein unbekanntes
    Kriterium ist ein Programmierfehler, kein stiller Durchlauf.
    """
    vorgabe = NAMEN[kriterium]
    daten = {
        "kriterium": vorgabe.id,
        "text": text,
        "schwere": vorgabe.schwere,
        "besitzer": vorgabe.besitzer,
        "kanal": vorgabe.kanal,
        "fix": vorgabe.fix,
    }
    daten.update(abweichung)
    return Befund(**daten)


def _code_klassen(code: str) -> list[str]:
    """`.a .b` → ['a', 'b']; `#x` → ['#x']."""
    return [teil.lstrip(".") for teil in re.split(r"[\s>+~]+", code.strip()) if teil.strip()]


# ====================================================================
#  A – Quelle & Verträge (P1–P12)
# ====================================================================
def p1(data, rules):
    if not data:
        return [_b("P1", "data/design/handoff.yaml fehlt oder ist leer", schwere="P1")]
    return []


def p2(data, rules):
    if data.get("version") != handoff.VERSION:
        return [_b("P2", f"version ist {data.get('version')!r}, erwartet {handoff.VERSION}")]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(data.get("stand", ""))):
        return [_b("P2", f"stand {data.get('stand')!r} ist kein ISO-Datum")]
    return []


def p3(data, rules):
    """Ohne Projektkontext ist ein Handoff nicht zuzuordnen.

    Geprüft wird, was die SSOT tatsächlich führt: Name, Sprache, Produkt,
    Ziel und Ton. Eine Domain steht bewusst nicht hier – sie gehört in
    hugo.toml, nicht in die Design-Quelle (eine zweite Wahrheit weniger).
    """
    fehlt = [k for k in ("name", "sprache", "produkt", "ziel", "ton")
             if not str(data.get("projekt", {}).get(k, "")).strip()]
    if fehlt:
        return [_b("P3", "Projekt-Metadaten unvollständig: " + ", ".join(fehlt))]
    return []


def p4(data, rules):
    erlaubt = {str(v).upper() for v in rules.get("marke", {}).get("farben_erlaubt", [])}
    befund = []
    for name, wert in data["figma"]["primitives"]["colors"].items():
        if str(wert).upper() not in erlaubt:
            befund.append(_b("P4", f"Farbe {name}={wert} fehlt in regelwerk.yaml → marke.farben_erlaubt",
                             schwere="P1"))
    return befund


def p5(data, rules):
    erlaubt = set(rules.get("marke", {}).get("radien_px_erlaubt", []))
    return [
        _b("P5", f"Radius {name}={wert}px ist nicht im Regelwerk")
        for name, wert in data["figma"]["primitives"]["radius_px"].items()
        if wert not in erlaubt
    ]


def p6(data, rules):
    sem = data["figma"]["semantic"]
    hell, dunkel = set(sem["light"]), set(sem["dark"])
    if hell == dunkel:
        return []
    return [_b("P6", f"Rollen asymmetrisch – nur hell {sorted(hell - dunkel)}, "
                   f"nur dunkel {sorted(dunkel - hell)}", schwere="P1")]


def p7(data, rules):
    farben = set(data["figma"]["primitives"]["colors"])
    befund = []
    for modus, rollen in data["figma"]["semantic"].items():
        for rolle, ziel in rollen.items():
            if ziel not in farben:
                befund.append(_b("P7", f"Alias {modus}.{rolle} → {ziel!r} zeigt ins Leere", schwere="P1"))
    return befund


def p8(data, rules):
    befund = []
    for name, stil in data["figma"]["typography"].items():
        gross, mobil = stil["size_px"], stil["mobile_px"]
        ueberschrift = name.startswith(("h1", "h2", "h3", "h4", "subline"))
        minimum = 0.55 if (ueberschrift or gross >= 40) else 0.85
        if mobil < gross * minimum:
            befund.append(_b("P8", f"Typo {name}: mobil {mobil}px unterschreitet "
                                 f"{int(minimum * 100)} % von {gross}px"))
        if not 1.0 <= float(stil["line_height"]) <= 2.0:
            befund.append(_b("P8", f"Typo {name}: line_height {stil['line_height']} außerhalb 1.0–2.0"))
    return befund


def p9(data, rules):
    muster = re.compile(r"^0 \d+px \d+px rgba\(\d+, ?\d+, ?\d+, ?[0-9.]+\)$")
    return [
        _b("P9", f"Schatten {name}={wert!r} ist nicht Figma-fähig")
        for name, wert in data["figma"]["primitives"]["elevation"].items()
        if not muster.match(str(wert).strip())
    ]


def p10(data, rules):
    ids = [c["id"] for c in data["components"]]
    doppelt = sorted({i for i in ids if ids.count(i) > 1})
    fehlend = [i for i in ids if not i.strip()]
    befund = [_b("P10", f"Komponenten-ID doppelt: {doppelt}", schwere="P1")] if doppelt else []
    befund += [_b("P10", "Komponente ohne ID", schwere="P1")] if fehlend else []
    figma_namen = [c["figma"] for c in data["components"]]
    dub = sorted({n for n in figma_namen if figma_namen.count(n) > 1})
    if dub:
        befund.append(_b("P10", f"Figma-Name doppelt (Kollision in Figma): {dub}"))
    return befund


INTERAKTIV = {"button-primary", "button-secondary", "newsletter-form", "header", "article-card", "faq"}
FOKUS = {"focus", "focus-visible", "focus-within", "keyboard"}


def p11(data, rules):
    return [
        _b("P11", f"Interaktive Komponente {c['id']} dokumentiert keinen Fokuszustand", schwere="P1")
        for c in data["components"]
        if c["id"] in INTERAKTIV and not FOKUS & set(c["states"])
    ]


def p12(data, rules):
    """Jede Komponente muss im Dunkelmodus existieren – auf einem von zwei Wegen.

    Entweder sie trägt einen eigenen `dark`-Zustand, oder sie ist eine
    Fläche, die ausschließlich über ihre Modi definiert wird (Desktop,
    Mobil, Druck, Artikel). Beides ist zulässig; „gar nichts“ nicht.
    """
    return [
        _b("P12", f"Komponente {c['id']} hat weder Dark-Zustand noch Modus-Achse")
        for c in data["components"]
        if "dark" not in c["states"] and not set(c["states"]) & handoff.MODUS_ZUSTAENDE
    ]


# ====================================================================
#  B – CSS-Vertrag (P13–P17)
# ====================================================================
def p13(data, rules):
    return [
        _b("P13", f"Komponente {c['id']} hat keinen code-Vertrag", schwere="P1")
        for c in data["components"]
        if not str(c.get("code", "")).strip()
    ]


def p14(data, rules):
    css = _css()
    befund = []
    for c in data["components"]:
        code = str(c["code"]).strip()
        if code.startswith((".", "#")):
            if handoff.pruefe_css_vertrag({"components": [c], "figma": data["figma"]}, css):
                befund.append(_b("P14", f"{c['id']}: {code} existiert nicht im ausgelieferten CSS",
                                 schwere="P1", besitzer="auto",
                                 fix="Klasse im CSS anlegen oder Inventar korrigieren"))
    return befund


def p15(data, rules):
    rollen = set(data["figma"]["semantic"]["light"])
    befund = []
    for c in data["components"]:
        for variable in c.get("variablen", []):
            if variable not in rollen:
                befund.append(_b("P15", f"{c['id']}: Rolle {variable!r} fehlt in der Semantik", schwere="P1"))
    return befund


def p16(data, rules):
    """Jede semantische Rolle muss von mindestens einer Komponente benutzt werden.

    Eine Rolle, die niemand liest, ist Ballast – oder schlimmer: ein
    Zeichen dafür, dass eine Komponente ihre Farbe fest verdrahtet hat.
    """
    benutzt = {v for c in data["components"] for v in c.get("variablen", [])}
    unbenutzt = sorted(set(data["figma"]["semantic"]["light"]) - benutzt)
    if unbenutzt:
        return [_b("P16", f"Semantische Rollen ohne Verwender: {unbenutzt}", schwere="P3",
                   besitzer="human", fix="Rolle einer Komponente zuordnen oder streichen")]
    return []


def p17(data, rules):
    """Jede interaktive Komponente braucht sichtbaren Tastaturfokus.

    Der Blog löst das an EINER Stelle: ein globaler 3-px-Ring auf
    `a, button, input, textarea, summary` (zzz-agency-polish.css, §9).
    Ein klassenspezifischer Selektor ist daher nicht Pflicht – der
    Nachweis ist entweder die Klasse selbst oder der globale Vertrag.
    Wer beides verlangt, erzeugt dreißig identische Regeln und nennt das
    dann Barrierefreiheit.
    """
    css = _css()
    globaler_ring = bool(re.search(
        r"(?:^|[,\s])(?:a|button|input|textarea|summary|select):focus-visible", css))
    befund = []
    for c in data["components"]:
        if c["id"] not in INTERAKTIV:
            continue
        klassen = [k for k in _code_klassen(c["code"]) if not k.startswith("#")]
        if not klassen:
            continue
        klasse = klassen[0]
        muster = re.compile(
            r"[^{}]*\." + re.escape(klasse) + r"[^{}]*:focus(?:-visible|-within)?[^{}]*\{")
        if not muster.search(css) and not globaler_ring:
            befund.append(_b("P17", f"{klasse} hat weder eigene :focus-Regel noch deckt "
                                     "der globale Fokusring dieses Element ab", schwere="P1"))
    return befund


# ====================================================================
#  C – Artefakte (P18–P27)
# ====================================================================
def p18(data, rules):
    return [
        _b("P18", f"Artefakt fehlt: design/handoff/{name}", schwere="P1", besitzer="auto",
           fix="python3 scripts/design_handoff.py")
        for name in handoff.GENERATED
        if not (OUT / name).exists()
    ]


def p19(data, rules):
    html = _artefakt("design-system.html") or ""
    treffer = re.findall(r'(?:src|href)="(https?://[^"]+)"|@import[^;]*url\(["\']?(https?://[^)"\']+)',
                         html)
    if treffer:
        return [_b("P19", f"design-system.html lädt aus dem Netz: {[t[0] or t[1] for t in treffer][:3]}",
                   schwere="P1")]
    return []


def p20(data, rules):
    html = _artefakt("design-system.html") or ""
    fehlend = [m for m in ("light", "dark")
               if f'data-modus="{m}"' not in html and f"setze('{m}')" not in html]
    if fehlend:
        return [_b("P20", f"design-system.html zeigt Modus nicht: {fehlend}")]
    return []


def p21(data, rules):
    html = _artefakt("design-system.html") or ""
    fehlend = [c["id"] for c in data["components"] if f'data-probe="{c["id"]}"' not in html]
    if fehlend:
        return [_b("P21", f"Komponenten fehlen auf der Design-System-Seite: {fehlend}")]
    if html.count('class="karte"') < len(data["components"]):
        return [_b("P21", "weniger Komponentenkarten als Komponenten – die Seite "
                          "zeigt nicht den vollen Bestand")]
    return []


def p22(data, rules):
    roh = _artefakt("figma-tokens.tokens.json")
    if roh is None:
        return [_b("P22", "figma-tokens.tokens.json fehlt", schwere="P1", besitzer="auto")]
    tokens = json.loads(roh)
    fehler = []
    if len(tokens.get("$themes", [])) != 2:
        fehler.append(_b("P22", "Tokens brauchen genau zwei Themes (Hell/Dunkel)"))
    if "Semantic/Dark" not in tokens:
        fehler.append(_b("P22", "Semantic/Dark fehlt – Dunkelmodus wäre in Figma unsichtbar"))
    if "Primitives" not in tokens:
        fehler.append(_b("P22", "Primitives fehlen"))
    return fehler


def p23(data, rules):
    tokens = json.loads(_artefakt("figma-tokens.tokens.json") or "{}")
    raum = tokens.get("Primitives", {}).get("spacing", {})
    if len(raum) != len(data["figma"]["primitives"]["spacing_px"]):
        return [_b("P23", f"Spacing-Tokens {len(raum)} ≠ SSOT {len(data['figma']['primitives']['spacing_px'])}")]
    return []


def p24(data, rules):
    text = _artefakt("ANNOTATIONEN.md") or ""
    paare = len(handoff.KONTRAST_PAARE)
    zeilen = len(re.findall(r"^\|\s*(?:light|dark|hell|dunkel)\s*\|", text, re.MULTILINE))
    if zeilen < paare * 2:
        return [_b("P24", f"Kontrast-Matrix unvollständig: {zeilen} Zeilen, erwartet ≥ {paare * 2}")]
    # Jede Zeile muss ein gerechnetes Verhältnis tragen – eine Tabelle ohne
    # Zahlen sieht aus wie ein Nachweis und ist nur eine Behauptung.
    werte = re.findall(r"\d+[.,]\d+:1", text)
    if len(werte) < paare * 2:
        return [_b("P24", f"nur {len(werte)} gerechnete Kontrastwerte, erwartet {paare * 2}")]
    if not re.search(r"4[.,]5:1", text):
        return [_b("P24", "Kontrast-Matrix nennt die WCAG-Schwelle 4,5:1 nicht")]
    return []


def p25(data, rules):
    text = _artefakt("patterns.md") or ""
    fehlend = [k for k in ("Seitenrhythmus", "Abnahme je Entwurf",
                           "Was das System niemals tut") if k not in text]
    if fehlend:
        return [_b("P25", f"patterns.md unvollständig: fehlt {fehlend}")]
    if "Erfundene" not in text:
        return [_b("P25", "patterns.md übernimmt das Verbot erfundener Beweise nicht")]
    mindestens = len(data["components"]) // 3
    if text.count("###") < mindestens:
        return [_b("P25", "patterns.md beschreibt zu wenige Komponentenmuster "
                          f"({text.count('###')} statt ≥ {mindestens})")]
    return []


def p26(data, rules):
    html = _artefakt("spezifikation.html") or ""
    fehlend = [c["id"] for c in data["components"] if c["id"] not in html]
    if fehlend:
        return [_b("P26", f"spezifikation.html lässt Komponenten aus: {fehlend}")]
    return []


def p27(data, rules):
    roh = _artefakt("handoff-manifest.json")
    if roh is None:
        return [_b("P27", "handoff-manifest.json fehlt", schwere="P1", besitzer="auto")]
    manifest = json.loads(roh)
    befund = []
    if "handoff-manifest.json" in manifest.get("artifacts", {}):
        befund.append(_b("P27", "Manifest hasht sich selbst – das ist logisch unmöglich"))
    for name, wert in manifest.get("artifacts", {}).items():
        pfad = OUT / name
        if not pfad.exists():
            befund.append(_b("P27", f"Manifest nennt {name}, Datei fehlt", besitzer="auto"))
        elif _sha256(pfad.read_text(encoding="utf-8")) != wert:
            befund.append(_b("P27", f"{name}: Hash weicht ab – Artefakt ist veraltet",
                             besitzer="auto", fix="python3 scripts/design_handoff.py"))
    for name, wert in manifest.get("plugins", {}).items():
        pfad = ROOT / name
        if not pfad.exists():
            befund.append(_b("P27", f"Manifest nennt Plugin-Datei {name}, sie fehlt", besitzer="auto"))
        elif _sha256(pfad.read_text(encoding="utf-8")) != wert:
            befund.append(_b("P27", f"{name}: Plugin-Hash weicht ab", besitzer="auto",
                             fix="python3 scripts/design_handoff.py"))
    return befund


# ====================================================================
#  D – Plugin (P28–P33)
# ====================================================================
def p28(data, rules):
    if not PLUGIN_SOURCE.exists():
        return [_b("P28", "figma/design-system-builder/source.js fehlt", schwere="P1")]
    if "const DATA = DATA_MARKE;" not in PLUGIN_SOURCE.read_text(encoding="utf-8"):
        return [_b("P28", "source.js enthält die Datenmarke nicht – der Generator kann "
                        "nichts injizieren", schwere="P1", besitzer="human")]
    return []


def p29(data, rules):
    if not PLUGIN_CODE.exists():
        return [_b("P29", "code.js fehlt", schwere="P1", besitzer="auto",
                   fix="python3 scripts/design_handoff.py")]
    if PLUGIN_CODE.read_text(encoding="utf-8") != handoff.plugin_code(data):
        return [_b("P29", "code.js ist nicht aus der aktuellen SSOT erzeugt", schwere="P1",
                   besitzer="auto", fix="python3 scripts/design_handoff.py")]
    return []


def p30(data, rules):
    if not PLUGIN_CODE.exists():
        return []
    quelle = PLUGIN_CODE.read_text(encoding="utf-8")
    treffer = [m for m in ("fetch(", "XMLHttpRequest", "require(", "import(") if m in quelle]
    if treffer:
        return [_b("P30", f"Plugin greift auf Netz/Module zu: {treffer} – Figma-Plugins "
                        "müssen offline laufen", schwere="P1")]
    return []


def p31(data, rules):
    if not PLUGIN_MANIFEST.exists():
        return [_b("P31", "figma/design-system-builder/manifest.json fehlt", schwere="P1")]
    manifest = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
    befund = []
    if "id" in manifest:
        befund.append(_b("P31", "Manifest enthält ein id-Feld. Ein leeres id kann den "
                              "Import blockieren; die ID gehört in handoff.yaml → figma.plugin_id",
                         schwere="P1", besitzer="human"))
    for feld in ("name", "api", "main", "ui", "editorType"):
        if feld not in manifest:
            befund.append(_b("P31", f"Manifest ohne {feld}", schwere="P1"))
    if manifest.get("main") != "code.js":
        befund.append(_b("P31", f"main ist {manifest.get('main')!r}, erwartet code.js"))
    if manifest.get("ui") != "ui.html":
        befund.append(_b("P31", f"ui ist {manifest.get('ui')!r}, erwartet ui.html"))
    if "documentAccess" not in manifest:
        befund.append(_b("P31", "documentAccess fehlt – ohne 'dynamic-page' schlägt der "
                              "asynchrone Seitenaufbau fehl", schwere="P1"))
    netz = (manifest.get("networkAccess") or {}).get("allowedDomains")
    if netz != ["none"]:
        befund.append(_b("P31", f"networkAccess.allowedDomains ist {netz!r} – erwartet ['none']"))
    return befund


def p32(data, rules):
    if not PLUGIN_UI.exists():
        return [_b("P32", "figma/design-system-builder/ui.html fehlt", schwere="P1")]
    html = PLUGIN_UI.read_text(encoding="utf-8")
    befund = []
    if re.search(r'(?:src|href)="https?://', html):
        befund.append(_b("P32", "ui.html lädt externe Ressourcen – das Plugin muss eigenständig sein",
                         schwere="P1"))
    if "<script" not in html or "pluginMessage" not in html:
        befund.append(_b("P32", "ui.html spricht nicht mit dem Plugin-Code (pluginMessage fehlt)"))
    if not re.search(r"<button", html):
        befund.append(_b("P32", "ui.html hat keine auslösende Schaltfläche"))
    for marker in ("aufbauen", "fertig"):
        if marker not in html:
            befund.append(_b("P32", f"ui.html kennt das Protokoll „{marker}“ nicht"))
    return befund


def p33(data, rules):
    skript = ROOT / "scripts/tests/figma_plugin_sim.mjs"
    if not skript.exists():
        return [_b("P33", "scripts/tests/figma_plugin_sim.mjs fehlt", schwere="P1")]
    try:
        lauf = subprocess.run(
            ["node", str(skript)],
            capture_output=True, text=True, timeout=120, cwd=str(ROOT),
        )
    except FileNotFoundError:
        return [_b("P33", "Node fehlt in dieser Umgebung – Simulation nicht ausgeführt",
                   schwere="P3", fix="node scripts/tests/figma_plugin_sim.mjs")]
    except subprocess.TimeoutExpired:
        return [_b("P33", "Plugin-Simulation läuft in den Timeout", schwere="P1")]
    if lauf.returncode != 0:
        detail = (lauf.stdout + lauf.stderr).strip().splitlines()[-3:]
        return [_b("P33", "Plugin-Simulation rot: " + " / ".join(detail), schwere="P1")]
    return []


# ====================================================================
#  E – Governance (P34–P36)
# ====================================================================
def p34(data, rules):
    """Der Figma-freie Weg muss ausdrücklich dokumentiert sein.

    Ohne diese Zusage wird das Handoff zur Figma-Abhängigkeit – und wer
    kein Figma hat, steht vor einer Wand. Das ist der Punkt, an dem eine
    Agentur-Übergabe ihren Wert verliert.
    """
    if not DOKU.exists():
        return [_b("P34", "docs/ANLEITUNG-FIGMA-EINRICHTUNG.md fehlt", schwere="P1")]
    text = DOKU.read_text(encoding="utf-8")
    fehlend = [k for k in ("design-system.html", "ohne Figma") if k not in text]
    if fehlend:
        return [_b("P34", f"Anleitung nennt den Figma-freien Weg nicht: {fehlend}", schwere="P1")]
    return []


def p35(data, rules):
    """Die Design-System-Seite muss ohne Server und ohne Netz aufgehen."""
    html = _artefakt("design-system.html") or ""
    if not html:
        return []
    befund = []
    if "<style" not in html:
        befund.append(_b("P35", "design-system.html bringt kein eigenes CSS mit"))
    if "file://" in html or "<base" in html:
        befund.append(_b("P35", "design-system.html ist nicht datei-lokal öffnbar"))
    if "@media" not in html:
        befund.append(_b("P35", "design-system.html hat keine responsive Regel – 390 px "
                              "ist der Abnahme-Viewport"))
    return befund


def p36(data, rules):
    """Die Prüfkette muss im Workflow hängen, sonst läuft sie nur bei mir."""
    if not WORKFLOW.exists():
        return [_b("P36", ".github/workflows/design-varianten.yml fehlt", schwere="P1")]
    text = WORKFLOW.read_text(encoding="utf-8")
    fehlend = [k for k in ("figma_quality_gate.py", "figma_plugin_sim.mjs",
                           "test_figma_handoff.py") if k not in text]
    if fehlend:
        return [_b("P36", f"Workflow ruft nicht auf: {fehlend}", schwere="P1",
                   besitzer="human", fix="Schritte im Gate-Job ergänzen")]
    return []


# ====================================================================
#  Katalog – 36 Kriterien, namentlich
# ====================================================================
PRUEFUNGEN: tuple[Pruefung, ...] = (
    Pruefung("P1", "SSOT vorhanden", "Ist data/design/handoff.yaml lesbar?",
             p1, "P1", "auto", KANAL_FIGMA, "Datei anlegen"),
    Pruefung("P2", "Version & Stand", "Trägt die SSOT Version und ISO-Datum?",
             p2, "P2", "auto", KANAL_FIGMA),
    Pruefung("P3", "Projekt-Metadaten", "Sind Name, Domain, Sprache, Claim gesetzt?",
             p3),
    Pruefung("P4", "Markenfarben", "Steht jede Figma-Farbe in regelwerk.yaml?",
             p4, "P1", "human", KANAL_FIGMA),
    Pruefung("P5", "Radien", "Sind alle Radien im Regelwerk erlaubt?",
             p5),
    Pruefung("P6", "Rollen-Symmetrie", "Tragen Hell und Dunkel dieselben Rollen?",
             p6, "P1", "auto", KANAL_FIGMA, "fehlende Rolle ergänzen"),
    Pruefung("P7", "Alias-Ziele", "Zeigt jeder Alias auf eine existierende Primitive?",
             p7, "P1", "auto", KANAL_FIGMA),
    Pruefung("P8", "Typo-Kohäsion", "Zerfällt die Schrift-Skala auf 390 px?",
             p8),
    Pruefung("P9", "Schatten-Format", "Sind alle Schatten Figma-Effektstile?",
             p9),
    Pruefung("P10", "Komponenten-IDs", "Sind IDs und Figma-Namen eindeutig?",
             p10, "P1"),
    Pruefung("P11", "Fokuszustand", "Dokumentiert jede interaktive Komponente Fokus?",
             p11, "P1"),
    Pruefung("P12", "Dark-Mode-Abdeckung", "Hat jede Komponente einen Dark-Zustand?",
             p12),
    Pruefung("P13", "code-Vertrag", "Hat jede Komponente eine CSS-Klasse?",
             p13, "P1"),
    Pruefung("P14", "Klassen-Existenz", "Gibt es jede dokumentierte Klasse im CSS?",
             p14, "P1", "human", KANAL_REPO, "CSS oder Inventar korrigieren"),
    Pruefung("P15", "Rollen-Verweise", "Verweist jede Komponente auf echte Rollen?",
             p15, "P1"),
    Pruefung("P16", "Rollen-Abdeckung", "Wird jede semantische Rolle benutzt?",
             p16, "P3"),
    Pruefung("P17", "Fokus im CSS", "Hat jede interaktive Klasse eine :focus-Regel?",
             p17, "P1"),
    Pruefung("P18", "Artefakte vorhanden", "Liegen alle generierten Dateien?",
             p18, "P1", "auto", KANAL_FIGMA, "python3 scripts/design_handoff.py"),
    Pruefung("P19", "Netzfreiheit", "Lädt design-system.html irgendetwas aus dem Netz?",
             p19, "P1"),
    Pruefung("P20", "Beide Modi sichtbar", "Zeigt die Seite Hell und Dunkel?",
             p20),
    Pruefung("P21", "Komponenten-Abdeckung", "Steht jede Komponente auf der Seite?",
             p21),
    Pruefung("P22", "Tokens-Studio-Vertrag", "Sind zwei Themes und Dunkel-Semantik da?",
             p22, "P1", "auto", KANAL_FIGMA),
    Pruefung("P23", "Spacing-Tokens", "Entspricht die Spacing-Skala der SSOT?",
             p23, "P2", "auto", KANAL_FIGMA),
    Pruefung("P24", "Kontrast-Matrix", "Sind alle Paare × Modi gerechnet?",
             p24),
    Pruefung("P25", "Pattern-Bibliothek", "Enthält patterns.md Rhythmus und Verbote?",
             p25),
    Pruefung("P26", "Spezifikation", "Sind alle Komponenten spezifiziert?",
             p26),
    Pruefung("P27", "Manifest-Integrität", "Stimmen alle Hashes?",
             p27, "P1", "auto", KANAL_FIGMA, "python3 scripts/design_handoff.py"),
    Pruefung("P28", "Plugin-Quelle", "Ist source.js mit Datenmarke vorhanden?",
             p28, "P1"),
    Pruefung("P29", "Plugin aktuell", "Ist code.js aus der aktuellen SSOT erzeugt?",
             p29, "P1", "auto", KANAL_FIGMA),
    Pruefung("P30", "Plugin offline", "Vermeidet das Plugin Netz und Module?",
             p30, "P1"),
    Pruefung("P31", "Manifest korrekt", "Stimmen main/ui/networkAccess, kein id-Feld?",
             p31, "P1"),
    Pruefung("P32", "UI eigenständig", "Läuft ui.html ohne externe Ressourcen?",
             p32, "P1"),
    Pruefung("P33", "Plugin-Simulation", "Baut das Plugin durch, ohne doppelt anzulegen?",
             p33, "P1", "auto", KANAL_FIGMA, "node scripts/tests/figma_plugin_sim.mjs"),
    Pruefung("P34", "Figma-freier Weg", "Ist der Weg ohne Figma dokumentiert?",
             p34, "P1"),
    Pruefung("P35", "Lokal öffnbar", "Öffnet die Seite ohne Server und Netz?",
             p35),
    Pruefung("P36", "In der Prüfkette", "Ruft der Workflow Gate, Simulation und Tests?",
             p36, "P1"),
)

NAMEN = {p.id: p for p in PRUEFUNGEN}


def pruefe(nur: str | None = None) -> list[Befund]:
    if len(PRUEFUNGEN) != 36:
        raise RuntimeError(f"Katalog beschädigt: {len(PRUEFUNGEN)} statt 36 Kriterien")
    try:
        data = handoff.load_yaml(SOURCE)
        rules = handoff.load_yaml(RULES)
    except FileNotFoundError as exc:
        raise SystemExit(f"❌ Quelle fehlt: {exc}") from exc
    befunde: list[Befund] = []
    for pruefung in PRUEFUNGEN:
        if nur and pruefung.id != nur:
            continue
        try:
            befunde.extend(pruefung.lauf(data, rules))
        except Exception as exc:  # noqa: BLE001 – ein kaputtes Kriterium darf das Gate nicht kippen
            befunde.append(Befund(pruefung.id, f"Prüfung selbst fehlgeschlagen: {exc}",
                                  "P1", "human", KANAL_REPO, "Gate reparieren"))
    return befunde


def bericht(befunde: list[Befund], nur: str | None = None) -> int:
    betroffen = {b.kriterium for b in befunde}
    gruen = [p for p in PRUEFUNGEN if p.id not in betroffen and (not nur or p.id == nur)]
    print(f"Figma-Qualitäts-Gate · {len(PRUEFUNGEN)} Kriterien")
    print(f"  ✅ {len(gruen)} bestanden   ⚠️ {sum(1 for b in befunde if b.schwere == 'P3')} Hinweise"
          f"   ❌ {sum(1 for b in befunde if b.schwere != 'P3')} Befunde")
    if not befunde:
        print("  Der Handoff ist stimmig, vollständig und ohne Netzabhängigkeit.")
        return 0
    for b in sorted(befunde, key=lambda x: (x.schwere, x.kriterium)):
        zeichen = "⚠️" if b.schwere == "P3" else "❌"
        print(f"  {zeichen} {b.kriterium} [{b.schwere}/{b.besitzer}/{b.kanal}] {b.text}")
        if b.fix:
            print(f"     ↳ Beheben: {b.fix}")
    print()
    print("  Beheben: python3 scripts/design_handoff.py  (erzeugt alle abgeleiteten Dateien neu)")
    blockiert = [b for b in befunde if b.schwere in ("P1", "P2")]
    return 1 if blockiert else 0


def selftest() -> int:
    """Sabotage-Proben: Ein Gate, das nur bei sich selbst grün ist, lügt."""
    if len(PRUEFUNGEN) != 36:
        print(f"❌ Katalog hat {len(PRUEFUNGEN)} statt 36 Kriterien")
        return 1
    ids = [p.id for p in PRUEFUNGEN]
    if len(set(ids)) != 36:
        print("❌ Kriterien-IDs sind nicht eindeutig")
        return 1
    data = handoff.load_yaml(SOURCE)
    rules = handoff.load_yaml(RULES)

    def faengt(kriterium: str, mutiert: dict[str, Any], regeln: dict[str, Any] | None = None) -> bool:
        return bool(NAMEN[kriterium].lauf(mutiert, regeln or rules))

    def kopie() -> dict[str, Any]:
        return json.loads(json.dumps(data))

    proben: list[tuple[str, bool]] = []

    k = kopie(); k["figma"]["primitives"]["colors"]["emerald"] = "#123456"
    proben.append(("P4 erfundene Farbe", faengt("P4", k)))

    k = kopie(); k["figma"]["semantic"]["dark"].pop("focus")
    proben.append(("P6 fehlende Dunkel-Rolle", faengt("P6", k)))

    k = kopie(); k["figma"]["semantic"]["light"]["background"] = "gibtsnicht"
    proben.append(("P7 toter Alias", faengt("P7", k)))

    k = kopie(); k["figma"]["typography"]["body"]["mobile_px"] = 8
    proben.append(("P8 zerfallene Skala", faengt("P8", k)))

    k = kopie(); k["figma"]["primitives"]["elevation"]["karte"] = "0 2px 6px #000"
    proben.append(("P9 fremdes Schattenformat", faengt("P9", k)))

    k = kopie(); k["components"][0]["code"] = ".gibt-es-nicht"
    proben.append(("P14 erfundene Klasse", faengt("P14", k)))

    k = kopie(); k["components"][0]["variablen"] = ["zauber-rolle"]
    proben.append(("P15 erfundene Rolle", faengt("P15", k)))

    k = kopie(); k["components"][0]["states"] = ["default"]
    proben.append(("P11 fehlender Fokus", faengt("P11", k)))
    proben.append(("P12 fehlender Dark-Zustand", faengt("P12", k)))

    k = kopie(); k["components"].append(dict(k["components"][0]))
    proben.append(("P10 doppelte ID", faengt("P10", k)))

    # P27: Hash-Manipulation muss auffallen. Dafür wird das Manifest kurz
    # verfälscht und danach byte-genau zurückgeschrieben – kein Test darf
    # den Arbeitsbaum verändern.
    manifest_pfad = OUT / "handoff-manifest.json"
    original = manifest_pfad.read_text(encoding="utf-8")
    try:
        m = json.loads(original)
        erstes = sorted(m["artifacts"])[0]
        m["artifacts"][erstes] = "0" * 64
        manifest_pfad.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        proben.append(("P27 verfälschter Hash", faengt("P27", data)))
    finally:
        manifest_pfad.write_text(original, encoding="utf-8")

    # P19: Netzbezug in einer Kopie des HTML darf nicht durchgehen.
    html_pfad = OUT / "design-system.html"
    html_original = html_pfad.read_text(encoding="utf-8")
    try:
        html_pfad.write_text(html_original.replace("</head>",
                             '<link rel="stylesheet" href="https://cdn.example/x.css"></head>', 1),
                             encoding="utf-8")
        proben.append(("P19 Netzbezug", faengt("P19", data)))
        # P20 separat: ein Modus, der nirgends mehr auftaucht, muss auffallen.
        ohne_modi = html_original.replace('data-modus="light"', '')
        for modus in ("light", "dark"):
            ohne_modi = ohne_modi.replace(f"setze('{modus}')", "/* entfernt */")
        html_pfad.write_text(ohne_modi, encoding="utf-8")
        proben.append(("P20 fehlender Modus", faengt("P20", data)))
    finally:
        html_pfad.write_text(html_original, encoding="utf-8")

    # P29: SSOT minimal ändern, code.js bleibt alt → Drift.
    k = kopie(); k["figma"]["primitives"]["spacing_px"].append(72)
    proben.append(("P29 veraltetes code.js", faengt("P29", k)))

    # P31: id-Feld darf den Import nicht gefährden.
    original_manifest = PLUGIN_MANIFEST.read_text(encoding="utf-8")
    try:
        m = json.loads(original_manifest)
        m["id"] = ""
        PLUGIN_MANIFEST.write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
        proben.append(("P31 id-Feld im Manifest", faengt("P31", data)))
    finally:
        PLUGIN_MANIFEST.write_text(original_manifest, encoding="utf-8")

    verletzt = [name for name, ok in proben if not ok]
    print(f"Figma-Gate-Selbsttest · {len(PRUEFUNGEN)} Kriterien · {len(proben)} Sabotage-Proben")
    if verletzt:
        for name in verletzt:
            print(f"  ❌ nicht erkannt: {name}")
        return 1
    print("  ✅ Jede Probe wurde erkannt; der Arbeitsbaum ist unverändert.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="maschinenlesbar")
    parser.add_argument("--nur", metavar="P9", help="nur ein Kriterium prüfen")
    parser.add_argument("--liste", action="store_true", help="Kriterienkatalog zeigen")
    parser.add_argument("--selftest", action="store_true", help="Sabotage-Proben fahren")
    args = parser.parse_args()

    if args.liste:
        print(f"{len(PRUEFUNGEN)} Kriterien:")
        for p in PRUEFUNGEN:
            print(f"  {p.id:4} {p.schwere}  {p.besitzer:5}  {p.name} – {p.frage}")
        return 0
    if args.selftest:
        return selftest()
    if args.nur and args.nur not in NAMEN:
        print(f"❌ Unbekanntes Kriterium {args.nur}; --liste zeigt alle.", file=sys.stderr)
        return 2

    befunde = pruefe(args.nur)
    if args.json:
        print(json.dumps({
            "kriterien": len(PRUEFUNGEN),
            "gepruefter": args.nur or "alle",
            "befunde": [b.as_dict() for b in befunde],
            "bestanden": not any(b.schwere in ("P1", "P2") for b in befunde),
        }, ensure_ascii=False, indent=2))
        return 1 if any(b.schwere in ("P1", "P2") for b in befunde) else 0
    return bericht(befunde, args.nur)


if __name__ == "__main__":
    raise SystemExit(main())
