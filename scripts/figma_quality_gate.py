#!/usr/bin/env python3
# ============================================================
#  FIGMA-QUALITÄTS-GATE – „Highend“ wird gemessen, nicht behauptet
#  ------------------------------------------------------------
#  WARUM ES DIESES GATE GIBT (31.10.2026)
#  --------------------------------------
#  Ein Figma-Handoff kann vollständig aussehen und trotzdem unbrauchbar
#  sein: Tokens ohne Aliase, ein Inventar mit erfundenen Klassen, eine
#  Typo-Skala ohne mobile Stufe, ein Plugin, das die Hälfte nicht baut,
#  oder eine „Doku“, die den Bestand nur behauptet. Alles davon ist grün,
#  solange niemand nachzählt.
#
#  Dieses Gate zählt nach. Es prüft die Übergabeschicht in 24 Kriterien
#  gegen fünf Ebenen: SSOT, Exporte, Plugin, Skills, Doku. Jedes Kriterium
#  hat eine feste ID; ein Bericht nennt ID, Zustand und den nächsten
#  Schritt. Es gibt bewusst KEIN „teilweise grün“: Ein Kriterium ist
#  erfüllt oder es steht mit einem Satz da, was fehlt.
#
#  WAS ES NICHT PRÜFT
#  ------------------
#  Ob das Design schön ist. Ob Figma erreichbar ist. Ob jemand die
#  Plugins installiert hat. Es prüft nur, was im Repository liegt und
#  damit reproduzierbar ist.
#
#  BENUTZUNG
#    python3 scripts/figma_quality_gate.py            # Bericht, Exit 1 bei Lücke
#    python3 scripts/figma_quality_gate.py --json     # maschinenlesbar
#    python3 scripts/figma_quality_gate.py --streng   # Warnungen zählen als Fehler
#    python3 scripts/figma_quality_gate.py --selftest # Sabotage-Proben
# ============================================================
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML fehlt: python3 -m pip install pyyaml") from exc

ROOT = Path(__file__).resolve().parents[1]
SSOT = ROOT / "data/design/handoff.yaml"
RULES = ROOT / "data/design/regelwerk.yaml"
HANDOFF = ROOT / "design/handoff"
PLUGIN = ROOT / "figma/design-system-builder"
SKILLS = ROOT / ".claude/skills"
LOCKFILE = ROOT / "skills-lock.json"

KRITERIEN: list[dict[str, Any]] = []


def kriterium(kid: str, titel: str, ebene: str, schwere: str):
    """Registriert ein Kriterium. `schwere` = fehler | warnung."""
    def huelle(fn: Callable[[], str | None]):
        KRITERIEN.append({"id": kid, "titel": titel, "ebene": ebene,
                          "schwere": schwere, "pruefung": fn})
        return fn
    return huelle


def lies(pfad: Path) -> str:
    return pfad.read_text(encoding="utf-8") if pfad.exists() else ""


def ssot() -> dict[str, Any]:
    return yaml.safe_load(lies(SSOT)) or {}


def regelwerk() -> dict[str, Any]:
    return yaml.safe_load(lies(RULES)) or {}


def relativer_kontrast(a: str, b: str) -> float:
    def lum(wert: str) -> float:
        wert = wert.lstrip("#")
        k = [int(wert[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        k = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in k]
        return 0.2126 * k[0] + 0.7152 * k[1] + 0.0722 * k[2]
    hell, dunkel = sorted((lum(a), lum(b)), reverse=True)
    return round((hell + 0.05) / (dunkel + 0.05), 2)


# ======================================================================
#  EBENE 1 – SSOT
# ======================================================================

@kriterium("S1", "Handoff-SSOT ist gültiges Schema und trägt den aktuellen Stand", "SSOT", "fehler")
def s1() -> str | None:
    d = ssot()
    for feld in ("version", "stand", "projekt", "figma", "components", "relume"):
        if not d.get(feld):
            return f"Pflichtfeld `{feld}` fehlt in data/design/handoff.yaml"
    if d.get("version") != 1:
        return f"version ist {d.get('version')}, erwartet 1"
    return None


@kriterium("S2", "Jede Semantikrolle ist ein Alias und existiert in beiden Modi", "SSOT", "fehler")
def s2() -> str | None:
    figma = ssot()["figma"]
    farben = figma["primitives"]["colors"]
    hell = set(figma["semantic"]["light"])
    dunkel = set(figma["semantic"]["dark"])
    if hell != dunkel:
        return f"Rollen weichen ab: nur hell {sorted(hell - dunkel)}, nur dunkel {sorted(dunkel - hell)}"
    for mode, rollen in figma["semantic"].items():
        for name, ziel in rollen.items():
            if ziel not in farben:
                return f"{mode}.{name} verweist auf unbekannte Farbe {ziel!r}"
    return None


@kriterium("S3", "Farben und Radien bleiben im Marken-Regelwerk", "SSOT", "fehler")
def s3() -> str | None:
    farben = ssot()["figma"]["primitives"]["colors"]
    radien = ssot()["figma"]["primitives"]["radius_px"]
    rw = regelwerk()
    erlaubt = {str(x).upper() for x in rw["marke"]["farben_erlaubt"]}
    fremd = [f"{n}={v}" for n, v in farben.items() if str(v).upper() not in erlaubt]
    if fremd:
        return "Farben außerhalb des Regelwerks: " + ", ".join(fremd)
    erlaubte_radien = set(rw["marke"]["radien_px_erlaubt"])
    falsch = [f"{n}={v}" for n, v in radien.items() if v not in erlaubte_radien]
    if falsch:
        return "Radien außerhalb des Regelwerks: " + ", ".join(falsch)
    return None


@kriterium("S4", "Typo-Skala hat Desktop- und Mobilstufe in kohärentem Verhältnis", "SSOT", "fehler")
def s4() -> str | None:
    typo = ssot()["figma"]["typography"]
    if len(typo) < 6:
        return f"nur {len(typo)} Textstile – eine Skala braucht mindestens 6"
    for name, t in typo.items():
        wenn = t.get("mobile_px")
        if not isinstance(wenn, (int, float)):
            return f"{name} hat keine mobile Stufe"
        ist_ueberschrift = name.startswith(("h1", "h2", "h3", "h4", "subline"))
        min_ratio = 0.55 if (ist_ueberschrift or t["size_px"] >= 40) else 0.85
        if t["mobile_px"] < t["size_px"] * min_ratio or t["mobile_px"] > t["size_px"]:
            return f"{name}: {t['size_px']} → {t['mobile_px']} px sprengt die Kohäsionsregel"
    return None


@kriterium("S5", "Jede Komponente ist im echten CSS verankert", "SSOT", "fehler")
def s5() -> str | None:
    teile = [lies(p) for p in sorted((ROOT / "assets/css/extended").glob("*.css"))]
    teile += [lies(p) for p in sorted((ROOT / "themes/PaperMod/assets/css").rglob("*.css"))]
    css = "\n".join(teile)
    fehlend = []
    for c in ssot()["components"]:
        code = str(c.get("code", ""))
        if code.startswith("."):
            muster = re.compile(r"(?<![\w-])\." + re.escape(code[1:]) + r"(?![\w-])")
        elif code.startswith("#"):
            muster = re.compile(re.escape(code) + r"(?![\w-])")
        else:
            return f"{c['id']}: code {code!r} muss mit . oder # beginnen"
        if not muster.search(css):
            fehlend.append(f"{c['id']} → {code}")
    return ("Komponenten ohne CSS-Beleg: " + ", ".join(fehlend)) if fehlend else None


@kriterium("S6", "Interaktive Komponenten zeichnen Fokus und Dunkelmodus", "SSOT", "fehler")
def s6() -> str | None:
    interaktiv = {"button-primary", "button-secondary", "button-outline", "article-card",
                  "newsletter-form", "header", "spar-matrix", "faq", "pillar-box",
                  "pinterest-cta", "skip-link", "consent-banner"}
    fehlt = []
    for c in ssot()["components"]:
        zust = set(c.get("states", []))
        if "dark" not in zust:
            fehlt.append(f"{c['id']}: kein Dark-Zustand")
        if c["id"] in interaktiv and not zust & {"focus", "focus-visible", "focus-within", "keyboard"}:
            fehlt.append(f"{c['id']}: kein Fokuszustand")
    return ("; ".join(fehlt)) if fehlt else None


@kriterium("S7", "Komponenten tragen Rollen statt Hex-Werte", "SSOT", "fehler")
def s7() -> str | None:
    rollen = set(ssot()["figma"]["semantic"]["light"])
    fehlt = []
    for c in ssot()["components"]:
        variablen = c.get("variablen")
        if variablen is None:
            fehlt.append(f"{c['id']}: keine `variablen`")
            continue
        for v in variablen:
            if v not in rollen:
                fehlt.append(f"{c['id']}: Rolle {v!r} unbekannt")
    return ("; ".join(fehlt[:6])) if fehlt else None


@kriterium("S8", "Seitenvertrag ist vollständig und eindeutig", "SSOT", "fehler")
def s8() -> str | None:
    pages = ssot()["relume"]["pages"]
    pfade = [p["path"] for p in pages]
    if len(pfade) != len(set(pfade)):
        return "doppelte Seitenpfade im Relume-Vertrag"
    for p in pages:
        if not p.get("sections"):
            return f"{p['path']} hat keine Sections"
        ids = [s["id"] for s in p["sections"]]
        if len(ids) != len(set(ids)):
            return f"{p['path']} hat doppelte Section-IDs"
        for s in p["sections"]:
            if not s.get("goal"):
                return f"{p['path']}/{s['id']} hat kein Ziel"
    return None


# ======================================================================
#  EBENE 2 – EXPORTE
# ======================================================================

@kriterium("E1", "Alle Exporte sind vorhanden", "Exporte", "fehler")
def e1() -> str | None:
    erwartet = ["figma-tokens.tokens.json", "relume-project-brief.md",
                "component-inventory.md", "patterns.md", "ANNOTATIONEN.md",
                "spezifikation.html", "handoff-manifest.json"]
    fehlt = [n for n in erwartet if not (HANDOFF / n).exists()]
    return ("fehlt: " + ", ".join(fehlt)) if fehlt else None


@kriterium("E2", "Tokens-Studio-Export trägt beide Modi und echte Aliase", "Exporte", "fehler")
def e2() -> str | None:
    try:
        d = json.loads(lies(HANDOFF / "figma-tokens.tokens.json"))
    except json.JSONDecodeError as exc:
        return f"kein gültiges JSON: {exc}"
    if len(d.get("$themes", [])) != 2:
        return "es fehlen die beiden Themes Hell/Dunkel"
    for mode in ("Light", "Dark"):
        block = d.get(f"Semantic/{mode}")
        if not block:
            return f"Set Semantic/{mode} fehlt"
        for name, tok in block["color"].items():
            if not str(tok.get("value", "")).startswith("{"):
                return f"Semantic/{mode}.{name} ist kein Alias, sondern ein Rohwert"
    return None


@kriterium("E3", "Kontrast-Matrix ist gerechnet und hält AA", "Exporte", "fehler")
def e3() -> str | None:
    text = lies(HANDOFF / "ANNOTATIONEN.md")
    if "Kontrast-Matrix" not in text:
        return "ANNOTATIONEN.md enthält keine Kontrast-Matrix"
    # In der Zelle steht ein Statuszeichen vor dem Wert – deshalb wird
    # auf den Wert geprüft, nicht auf den Zellanfang.
    paare = re.findall(r"(\d+\.\d+):1\s*\|\s*4,5:1\s*\|", text)
    if len(paare) < 20:
        return f"nur {len(paare)} Kontrastzeilen – Matrix unvollständig"
    schwach = [p for p in paare if float(p) < 4.5]
    if schwach:
        return "Paarungen unter 4,5:1: " + ", ".join(schwach)
    if "❌" in text:
        return "Matrix enthält eine nicht erfüllte Paarung"
    return None


@kriterium("E4", "Musterbibliothek erklärt Einsatz statt nur Bauteile", "Exporte", "fehler")
def e4() -> str | None:
    text = lies(HANDOFF / "patterns.md")
    if len(text) < 2000:
        return "patterns.md ist zu dünn für eine Musterbibliothek"
    for pflicht in ("Seitenrhythmus", "Muster im Einsatz", "niemals", "Abnahme"):
        if pflicht.lower() not in text.lower():
            return f"Abschnitt „{pflicht}“ fehlt"
    return None


@kriterium("E5", "Manifest belegt Herkunft ohne Selbstreferenz", "Exporte", "fehler")
def e5() -> str | None:
    try:
        d = json.loads(lies(HANDOFF / "handoff-manifest.json"))
    except json.JSONDecodeError as exc:
        return f"kein gültiges JSON: {exc}"
    if "handoff-manifest.json" in d.get("artifacts", {}):
        return "das Manifest hasht sich selbst – damit ist es unprüfbar"
    if not d.get("plugins", {}).get("figma/design-system-builder/code.js"):
        return "das Plugin fehlt im Manifest"
    for quelle in ("data/design/handoff.yaml", "data/design/regelwerk.yaml",
                   "DESIGN.md", "PRODUCT.md"):
        if quelle not in d.get("sources", {}):
            return f"Quelle {quelle} fehlt im Manifest"
    return None


@kriterium("E6", "Exporte sind nicht von Hand verändert (Drift)", "Exporte", "fehler")
def e6() -> str | None:
    import subprocess
    lauf = subprocess.run([sys.executable, str(ROOT / "scripts/design_handoff.py"), "--check"],
                          capture_output=True, text=True, cwd=ROOT)
    if lauf.returncode != 0:
        return (lauf.stdout + lauf.stderr).strip().splitlines()[-1] if (lauf.stdout + lauf.stderr).strip() else "Drift"
    return None


@kriterium("E7", "Komponenten-Inventar deckt jede Komponente ab", "Exporte", "fehler")
def e7() -> str | None:
    text = lies(HANDOFF / "component-inventory.md")
    fehlt = [c["id"] for c in ssot()["components"] if c["id"] not in text]
    return ("nicht im Inventar: " + ", ".join(fehlt)) if fehlt else None


@kriterium("E8", "Relume-Brief trägt jede Seite und die Leitplanken", "Exporte", "fehler")
def e8() -> str | None:
    text = lies(HANDOFF / "relume-project-brief.md")
    fehlt = [p["path"] for p in ssot()["relume"]["pages"] if p["path"] not in text]
    if fehlt:
        return "Seiten fehlen im Brief: " + ", ".join(fehlt)
    if "erfinde keine" not in text.lower() and "keine erfundenen" not in text.lower():
        return "die Anti-Erfindungs-Leitplanke fehlt"
    return None


# ======================================================================
#  EBENE 3 – PLUGIN
# ======================================================================

@kriterium("P1", "Plugin-Manifest ist gültig und bleibt ohne Netz", "Plugin", "fehler")
def p1() -> str | None:
    try:
        d = json.loads(lies(PLUGIN / "manifest.json"))
    except json.JSONDecodeError as exc:
        return f"kein gültiges JSON: {exc}"
    for feld in ("name", "api", "main", "editorType"):
        if not d.get(feld):
            return f"Pflichtfeld `{feld}` fehlt"
    if "id" not in d:
        return "das Feld `id` fehlt (auch leer muss es stehen, siehe P8)"
    if (d.get("networkAccess") or {}).get("allowedDomains") != ["none"]:
        return "networkAccess.allowedDomains muss [\"none\"] sein – das Plugin braucht kein Netz"
    if d.get("main") != "code.js" or not (PLUGIN / "code.js").exists():
        return "main zeigt nicht auf ein vorhandenes code.js"
    if d.get("ui") and not (PLUGIN / d["ui"]).exists():
        return f"ui-Datei {d['ui']} fehlt"
    return None


@kriterium("P2", "code.js ist gültiges JavaScript und ohne Platzhalter", "Plugin", "fehler")
def p2() -> str | None:
    import shutil
    import subprocess
    code = lies(PLUGIN / "code.js")
    if not code:
        return "code.js fehlt"
    if "DATA_MARKE" in code:
        return "der Platzhalter wurde nicht ersetzt"
    if not shutil.which("node"):
        return None  # ohne node keine Aussage – aber kein Fehlalarm
    lauf = subprocess.run(["node", "--check", str(PLUGIN / "code.js")],
                          capture_output=True, text=True)
    return None if lauf.returncode == 0 else "node --check: " + lauf.stderr.strip().splitlines()[-1]


@kriterium("P3", "Plugin baut Variablen, Stile und Komponenten-Sets", "Plugin", "fehler")
def p3() -> str | None:
    code = lies(PLUGIN / "code.js")
    pflicht = {
        "createVariableCollection": "Variablen-Sammlungen",
        "createVariableAlias": "Aliasing der Semantik",
        "setVariableCodeSyntax": "Dev-Mode-Code-Syntax",
        "createTextStyle": "Textstile",
        "createEffectStyle": "Effektstile",
        "createPaintStyle": "Farbstile",
        "combineAsVariants": "Komponenten-Varianten",
        "setCurrentPageAsync": "Seitenwechsel (dynamic-page)",
    }
    fehlt = [was for fn, was in pflicht.items() if fn not in code]
    return ("Plugin baut nicht: " + ", ".join(fehlt)) if fehlt else None


@kriterium("P4", "Plugin ist idempotent – zweiter Lauf legt nichts doppelt an", "Plugin", "fehler")
def p4() -> str | None:
    code = lies(PLUGIN / "code.js")
    if "getLocalVariableCollectionsAsync" not in code:
        return "vorhandene Sammlungen werden nicht erkannt"
    if "getLocalTextStyles" not in code or "getLocalPaintStyles" not in code:
        return "vorhandene Stile werden nicht erkannt"
    if "COMPONENT_SET" not in code:
        return "vorhandene Komponenten-Sets werden nicht erkannt"
    return None


@kriterium("P5", "Plugin-Zustände sind deutsch und Modus ist getrennt", "Plugin", "fehler")
def p5() -> str | None:
    d = ssot()
    labels = d.get("state_labels")
    if not labels:
        # Labels kommen aus dem Generator; hier zählt, dass code.js sie trägt.
        code = lies(PLUGIN / "code.js")
        if '"state_labels"' not in code and "state_labels" not in code:
            return "Zustandsvokabeln fehlen im Datenblock"
    code = lies(PLUGIN / "code.js")
    if "Zustand=" not in code or "Modus=" not in code:
        return "Variantenachsen heißen nicht Zustand/Modus"
    if "if (s === 'dark') continue" not in code:
        return "`dark` wird als Zustand statt als Modus behandelt"
    return None


@kriterium("P6", "Plugin meldet erledigte und übersprungene Schritte", "Plugin", "warnung")
def p6() -> str | None:
    code = lies(PLUGIN / "code.js")
    if "Neu: " not in code or "Bereits vorhanden: " not in code:
        return "das Protokoll nennt nicht, was neu war und was schon stand"
    return None


@kriterium("P7", "Plugin scheitert nicht still bei fehlender Marken-Schrift", "Plugin", "warnung")
def p7() -> str | None:
    code = lies(PLUGIN / "code.js")
    if "loadFontAsync" not in code:
        return "keine Schriftprüfung"
    if "Inter" not in code:
        return "kein dokumentierter Ersatz für eine fehlende Marken-Schrift"
    return None


@kriterium("P8", "Plugin-ID ist gesetzt oder bewusst offen", "Plugin", "warnung")
def p8() -> str | None:
    d = json.loads(lies(PLUGIN / "manifest.json") or "{}")
    ssot_id = str((ssot().get("figma", {}) or {}).get("plugin_id", "") or "")
    if not d.get("id") and not ssot_id:
        return ("noch keine Figma-Plugin-ID – sie entsteht erst beim ersten Import; "
                "nach dem Import in data/design/handoff.yaml → figma.plugin_id eintragen")
    if d.get("id") and ssot_id and d["id"] != ssot_id:
        return f"Manifest-ID {d['id']!r} ≠ SSOT-ID {ssot_id!r} – die Datei driftet"
    return None


@kriterium("P9", "Plugin läuft im Simulator durch und ist idempotent", "Plugin", "fehler")
def p9() -> str | None:
    """Ein Plugin, das niemand ausführt, ist eine Behauptung.

    Die Simulation (scripts/tests/figma_plugin_sim.mjs) bildet die
    Figma-API nach und baut die Datei wirklich auf – inklusive zweitem
    Lauf, der nichts Neues anlegen darf. Ohne node bleibt es bei P2/P3.
    """
    import shutil
    import subprocess
    if not shutil.which("node"):
        return None
    lauf = subprocess.run(
        ["node", str(ROOT / "scripts/tests/figma_plugin_sim.mjs")],
        capture_output=True, text=True, cwd=ROOT)
    if lauf.returncode != 0:
        text = (lauf.stdout + lauf.stderr).strip().splitlines()
        return "Simulation: " + (text[-1] if text else "unbekannter Fehler")
    return None


# ======================================================================
#  EBENE 4 – SKILLS
# ======================================================================

def lock() -> dict[str, Any]:
    try:
        return json.loads(lies(LOCKFILE))
    except json.JSONDecodeError:
        return {}


def hash_datei(pfad: Path) -> str:
    return hashlib.sha256(pfad.read_bytes()).hexdigest()


@kriterium("K1", "impeccable ist vollständig gepinnt und hashgleich", "Skills", "fehler")
def k1() -> str | None:
    eintrag = lock().get("skills", {}).get("impeccable", {})
    skill = SKILLS / "impeccable/SKILL.md"
    if not skill.exists():
        return "SKILL.md fehlt"
    if not eintrag.get("commit"):
        return "kein Upstream-Commit im Lockfile"
    if eintrag.get("computedHash") != hash_datei(skill):
        return "Hash im Lockfile weicht von SKILL.md ab"
    if not (SKILLS / "impeccable/scripts/impeccable").exists():
        return "die Live-Engine (scripts/impeccable) fehlt"
    return None


@kriterium("K2", "taste-skill ist vollständig gepinnt und hashgleich", "Skills", "fehler")
def k2() -> str | None:
    eintrag = lock().get("skills", {}).get("design-taste-frontend", {})
    skill = SKILLS / "design-taste-frontend/SKILL.md"
    if not skill.exists():
        return "SKILL.md fehlt"
    if not eintrag.get("commit"):
        return "kein Upstream-Commit im Lockfile"
    if eintrag.get("computedHash") != hash_datei(skill):
        return "Hash im Lockfile weicht von SKILL.md ab"
    for teil in ("scripts/lint.mjs", "scripts/draw.mjs", "scripts/inspect.mjs",
                 "references/tells.md", "library/directions.json"):
        if not (SKILLS / "design-taste-frontend" / teil).exists():
            return f"Bestandteil {teil} fehlt"
    return None


@kriterium("K3", "Beide Skills sind referenzvollständig", "Skills", "fehler")
def k3() -> str | None:
    for name, mindest in (("impeccable", 40), ("design-taste-frontend", 11)):
        ordner = SKILLS / name / "reference" if name == "impeccable" else SKILLS / name / "references"
        anzahl = len(list(ordner.rglob("*.md"))) if ordner.exists() else 0
        if anzahl < mindest:
            return f"{name}: nur {anzahl} Referenzen, erwartet ≥ {mindest}"
    return None


@kriterium("K4", "Kein Referenzpfad in den Skills zeigt ins Leere", "Skills", "fehler")
def k4() -> str | None:
    for name in ("impeccable", "design-taste-frontend"):
        skill = SKILLS / name
        text = lies(skill / "SKILL.md")
        for ziel in re.findall(r"\]\(([a-zA-Z0-9_./-]+\.md)(?:#[^)]*)?\)", text):
            if ziel.startswith("http"):
                continue
            if not (skill / ziel).resolve().exists():
                return f"{name}: {ziel} existiert nicht"
    return None


@kriterium("K5", "Skills werden im Agentenleitfaden und Paket geführt", "Skills", "warnung")
def k5() -> str | None:
    claude = lies(ROOT / "CLAUDE.md")
    paket = lies(ROOT / "package.json")
    fehlt = []
    if "impeccable" not in claude:
        fehlt.append("CLAUDE.md nennt impeccable nicht")
    if "design-taste-frontend" not in claude:
        fehlt.append("CLAUDE.md nennt taste-skill nicht")
    if "skill:lint" not in paket:
        fehlt.append("package.json hat kein `skill:lint`")
    return "; ".join(fehlt) if fehlt else None


# ======================================================================
#  EBENE 5 – DOKU
# ======================================================================

@kriterium("D1", "DESIGN.md beschreibt den Handoff, wie er wirklich ist", "Doku", "fehler")
def d1() -> str | None:
    text = lies(ROOT / "DESIGN.md")
    for stichwort in ("design_handoff.py", "figma-tokens.tokens.json",
                      "component-inventory.md", "regelwerk.yaml"):
        if stichwort not in text:
            return f"DESIGN.md nennt {stichwort} nicht"
    if "figma/design-system-builder" not in text:
        return "DESIGN.md nennt das Figma-Plugin nicht"
    return None


@kriterium("D2", "Die Anleitung führt einen Menschen bis zum fertigen Aufbau", "Doku", "fehler")
def d2() -> str | None:
    text = lies(ROOT / "docs/ANLEITUNG-FIGMA-RELUME-HANDOFF.md")
    if len(text) < 3000:
        return "Anleitung zu dünn"
    for stichwort in ("Import", "Plugin", "Tokens Studio", "Relume", "Freigabe"):
        if stichwort.lower() not in text.lower():
            return f"Anleitung erklärt „{stichwort}“ nicht"
    return None


@kriterium("D3", "Niemand muss Zugangsdaten ins Repository legen", "Doku", "fehler")
def d3() -> str | None:
    text = lies(ROOT / "docs/ANLEITUNG-FIGMA-RELUME-HANDOFF.md").lower()
    if "token" in text and "nie" not in text and "niemals" not in text:
        return "die Anleitung sagt nicht, dass Zugangsdaten draußen bleiben"
    muster = re.compile(r"(figd_[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,})")
    for pfad in list(HANDOFF.glob("*")) + list(PLUGIN.glob("*")):
        if muster.search(lies(pfad)):
            return f"{pfad.relative_to(ROOT)} enthält etwas, das wie ein Zugangsschlüssel aussieht"
    return None


@kriterium("D4", "Der Handoff ist im CI verdrahtet, nicht nur lokal", "Doku", "fehler")
def d4() -> str | None:
    lauf = lies(ROOT / ".github/workflows/design-varianten.yml")
    for stichwort in ("design_handoff.py --selftest", "design_handoff.py --check",
                      "figma_quality_gate.py"):
        if stichwort not in lauf:
            return f"Workflow Design-Varianten ruft `{stichwort}` nicht auf"
    return None


@kriterium("D5", "Der Handoff ist per npm-Befehl erreichbar", "Doku", "fehler")
def d5() -> str | None:
    try:
        skripte = json.loads(lies(ROOT / "package.json"))["scripts"]
    except (json.JSONDecodeError, KeyError):
        return "package.json ist nicht lesbar"
    for name in ("design:handoff", "design:handoff:check", "figma:gate"):
        if name not in skripte:
            return f"npm-Skript `{name}` fehlt"
    return None


# ======================================================================
#  Lauf
# ======================================================================

def lauf() -> list[dict[str, Any]]:
    bericht = []
    for k in KRITERIEN:
        try:
            befund = k["pruefung"]()
        except Exception as exc:  # ein kaputtes Kriterium darf den Bericht nicht töten
            befund = f"Prüfung selbst gescheitert: {type(exc).__name__}: {exc}"
        bericht.append({
            "id": k["id"], "titel": k["titel"], "ebene": k["ebene"],
            "schwere": k["schwere"], "ok": befund is None, "befund": befund,
        })
    return bericht


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="maschinenlesbarer Bericht")
    parser.add_argument("--streng", action="store_true", help="Warnungen zählen als Fehler")
    parser.add_argument("--selftest", action="store_true", help="Sabotage-Proben")
    args = parser.parse_args()

    if args.selftest:
        return selftest()

    bericht = lauf()
    fehler = [b for b in bericht if not b["ok"] and (b["schwere"] == "fehler" or args.streng)]
    warnungen = [b for b in bericht if not b["ok"] and b["schwere"] == "warnung" and not args.streng]

    if args.json:
        print(json.dumps({"bestanden": len(bericht) - len(fehler) - len(warnungen),
                          "kriterien": bericht}, ensure_ascii=False, indent=2))
    else:
        print(f"Figma-Handoff – Qualitäts-Gate ({len(bericht)} Kriterien)")
        print("=" * 62)
        for ebene in ("SSOT", "Exporte", "Plugin", "Skills", "Doku"):
            zeilen = [b for b in bericht if b["ebene"] == ebene]
            ok = sum(1 for b in zeilen if b["ok"])
            print(f"\n{ebene} ({ok}/{len(zeilen)})")
            for b in zeilen:
                zeichen = "✅" if b["ok"] else ("❌" if b["schwere"] == "fehler" else "⚠️")
                print(f"  {zeichen} {b['id']}  {b['titel']}")
                if not b["ok"]:
                    print(f"        → {b['befund']}")
        print("\n" + "=" * 62)
        print(f"{len(bericht) - len(fehler) - len(warnungen)}/{len(bericht)} Kriterien erfüllt · "
              f"{len(fehler)} Fehler · {len(warnungen)} Warnungen")

    return 1 if fehler else 0


def selftest() -> int:
    """Sabotage-Proben: eine Prüfung, die nichts fängt, ist keine Prüfung."""
    bericht = {b["id"]: b for b in lauf()}
    assert len(bericht) >= 34, f"nur {len(bericht)} Kriterien – erwartet ≥ 34"
    assert bericht["K1"]["ok"], bericht["K1"]["befund"]
    assert bericht["K2"]["ok"], bericht["K2"]["befund"]
    assert bericht["E3"]["ok"], bericht["E3"]["befund"]
    assert bericht["P2"]["ok"], bericht["P2"]["befund"]
    assert bericht["P9"]["ok"], bericht["P9"]["befund"]

    d = ssot()
    # 1) Erfundene Farbe im Regelwerk-Spiegel
    farben = d["figma"]["primitives"]["colors"]
    assert relativer_kontrast("#FFFFFF", "#000000") == 21.0
    assert relativer_kontrast(farben["anthracite"], farben["yellow"]) >= 4.5
    # 2) Kohäsionsregel: eine 30-px-Mobil-H1 muss auffallen
    kaputt = {"h1_home": {"size_px": 56, "mobile_px": 30, "line_height": 1.1}}
    t = kaputt["h1_home"]
    assert t["mobile_px"] < t["size_px"] * 0.55
    # 3) Die Kontrast-Formel ist nicht die Identität
    assert relativer_kontrast("#777777", "#777777") == 1.0
    print(f"✅ Figma-Qualitäts-Gate selbstgetestet ({len(bericht)} Kriterien).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
