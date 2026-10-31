#!/usr/bin/env python3
"""Reproduzierbarer Figma-/Relume-Handoff aus dem Design-SSOT.

Erzeugt keine SaaS-Verbindung und veröffentlicht nichts. Das Skript baut
prüfbare Import-/Briefing-Artefakte, validiert sie gegen das Marken-Regelwerk
und verhindert Drift mit --check.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - klare Bedienmeldung
    raise SystemExit("PyYAML fehlt: python3 -m pip install pyyaml") from exc

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/design/handoff.yaml"
RULES = ROOT / "data/design/regelwerk.yaml"
OUT = ROOT / "design/handoff"
# Plugins sind Code, keine Textausgabe: eigener Ablageort, eigener Generator.
PLUGIN_OUT = ROOT / "figma/design-system-builder"
PLUGIN_SOURCE = PLUGIN_OUT / "source.js"
CSS_EXTENDED = ROOT / "assets/css/extended"
VERSION = 1
GENERATED = (
    "figma-tokens.tokens.json",
    "relume-project-brief.md",
    "component-inventory.md",
    "patterns.md",
    "ANNOTATIONEN.md",
    "spezifikation.html",
    "design-system.html",
    "handoff-manifest.json",
)
PLUGIN_GENERATED = ("code.js",)
# Zustandsvokabeln für Figma-Varianten. Der Modus (Hell/Dunkel) ist eine
# eigene Achse; `dark` ist deshalb kein Zustand, sondern ein Modus.
STATE_LABELS = {
    "default": "Standard",
    "hover": "Hover",
    "focus-visible": "Fokus",
    "focus-within": "Fokus",
    "focus": "Fokus",
    "disabled": "Deaktiviert",
    "error": "Fehler",
    "success": "Erfolg",
    "tip": "Tipp",
    "warning": "Warnung",
    "info": "Info",
    "open": "Offen",
    "keyboard": "Tastatur",
    "desktop": "Desktop",
    "mobile": "Mobil",
    "mobile-gestapelt": "Mobil gestapelt",
    "article": "Artikel",
    "print": "Druck",
}
MODES = {"light": "Hell", "dark": "Dunkel"}
# Grundbausteine, die keine eigenen Komponenten sind: ein Hero ist ein
# Layout, keine Karte – und `prose` ist die Lesefläche selbst.
RELUME_BAUSTEINE = {"hero", "prose"}
# Modi als Zustände: Eine Komponente, die ausschließlich in beiden Modi
# gezeichnet wird (`desktop`, `mobile`, `article`, `print`), trägt ihren
# Dunkelmodus über die Modus-Achse und braucht kein eigenes `dark`.
MODUS_ZUSTAENDE = {"desktop", "mobile", "article", "print", "keyboard"}


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.relative_to(ROOT)} muss ein YAML-Objekt sein")
    return value


def validate(data: dict[str, Any], rules: dict[str, Any]) -> None:
    errors: list[str] = []
    if data.get("version") != VERSION:
        errors.append(f"version muss {VERSION} sein")
    for key in ("stand", "projekt", "figma", "components", "relume"):
        if not data.get(key):
            errors.append(f"Pflichtfeld fehlt/leer: {key}")

    figma = data.get("figma", {})
    colors = figma.get("primitives", {}).get("colors", {})
    allowed = {str(v).upper() for v in rules.get("marke", {}).get("farben_erlaubt", [])}
    for name, value in colors.items():
        if str(value).upper() not in allowed:
            errors.append(f"Figma-Farbe {name}={value} ist kein erlaubtes Marken-Token")

    radii = figma.get("primitives", {}).get("radius_px", {})
    allowed_radii = set(rules.get("marke", {}).get("radien_px_erlaubt", []))
    for name, value in radii.items():
        if value not in allowed_radii:
            errors.append(f"Radius {name}={value}px ist nicht im Regelwerk")

    semantic = figma.get("semantic", {})
    for mode in ("light", "dark"):
        if mode not in semantic:
            errors.append(f"Semantische Figma-Collection fehlt: {mode}")
            continue
        for token, alias in semantic[mode].items():
            if alias not in colors:
                errors.append(f"Alias {mode}.{token} verweist auf unbekannte Farbe {alias}")

    # --- Typografie: Kohäsionsregel und Pflichtfelder -------------------
    typo = figma.get("typography", {})
    if not typo:
        errors.append("Figma-Typografie fehlt")
    for name, style in typo.items():
        for key in ("family", "size_px", "mobile_px", "line_height", "weight"):
            if style.get(key) in (None, ""):
                errors.append(f"Typo {name}: Pflichtfeld {key} fehlt")
        size, mobile = style.get("size_px"), style.get("mobile_px")
        if isinstance(size, (int, float)) and isinstance(mobile, (int, float)):
            if mobile > size:
                errors.append(f"Typo {name}: mobile_px {mobile} ist größer als size_px {size}")
            # Zwei ehrliche Grenzen: Überschriften skalieren fließend per
            # clamp() und dürfen deutlich schrumpfen. Fließtext, Meta und
            # Labels tragen die Lesbarkeit – dort zerfällt die Skala schnell.
            ist_ueberschrift = name.startswith(("h1", "h2", "h3", "h4", "subline"))
            min_ratio = 0.55 if (ist_ueberschrift or size >= 40) else 0.85
            if mobile < size * min_ratio:
                errors.append(
                    f"Typo {name}: mobile_px {mobile} fällt unter "
                    f"{int(min_ratio * 100)} % von size_px {size} "
                    "– die Skala zerfällt auf dem Abnahme-Viewport")
        if not 1.0 <= float(style.get("line_height", 0)) <= 2.0:
            errors.append(f"Typo {name}: line_height {style.get('line_height')} liegt außerhalb 1.0–2.0")

    # --- Semantik: Hell und Dunkel müssen dieselben Rollen tragen --------
    roles = {mode: set(semantic.get(mode, {})) for mode in ("light", "dark")}
    if roles["light"] != roles["dark"]:
        nur_hell = sorted(roles["light"] - roles["dark"])
        nur_dunkel = sorted(roles["dark"] - roles["light"])
        errors.append(f"Semantik-Rollen unvollständig: nur hell {nur_hell}, nur dunkel {nur_dunkel}")

    # --- Schatten: Format, damit Figma-Effektstile entstehen können ------
    elevation = figma.get("primitives", {}).get("elevation", {})
    schatten = re.compile(r"^0 \d+px \d+px rgba\(\d+, ?\d+, ?\d+, ?[0-9.]+\)$")
    for name, wert in elevation.items():
        if not schatten.match(str(wert).strip()):
            errors.append(f"Schatten {name}={wert!r} entspricht nicht '0 Ypx Bpx rgba(r, g, b, a)'")

    ids: set[str] = set()
    for component in data.get("components", []):
        cid = component.get("id", "")
        if not cid or cid in ids:
            errors.append(f"Komponenten-ID fehlt oder ist doppelt: {cid!r}")
        ids.add(cid)
        states = set(component.get("states", []))
        if not any(state in states for state in ("focus", "focus-visible", "keyboard", "focus-within")) and cid in {
            "button-primary", "button-secondary", "article-card", "newsletter-form", "header"
        }:
            errors.append(f"Interaktive Komponente {cid} dokumentiert keinen Fokuszustand")
        # Zwei ehrliche Wege: die Komponente hat einen eigenen Dark-Zustand
        # ODER sie lebt als reine Fläche in beiden Modi (dann zeigt der
        # Modus-Achse des Komponenten-Sets sie, nicht ein Zustand).
        if "dark" not in states and not (states & MODUS_ZUSTAENDE):
            errors.append(f"Komponente {cid} dokumentiert keinen Dark-Mode-Zustand")

    pages = data.get("relume", {}).get("pages", [])
    erlaubte_bausteine = {c.get("id") for c in data.get("components", [])} | RELUME_BAUSTEINE
    paths: set[str] = set()
    for page in pages:
        path = page.get("path", "")
        if not path or path in paths:
            errors.append(f"Relume-Seitenpfad fehlt oder ist doppelt: {path!r}")
        paths.add(path)
        if not page.get("sections"):
            errors.append(f"Relume-Seite {path} hat keine Sections")
        for section in page.get("sections", []):
            baustein = section.get("component")
            if baustein not in erlaubte_bausteine:
                errors.append(
                    f"Relume-Seite {path}: Section {section.get('id')!r} nutzt den unbekannten "
                    f"Baustein {baustein!r} – weder Komponente noch Grundbaustein")

    errors.extend(pruefe_css_vertrag(data, css_bestand()))

    if errors:
        raise ValueError("Design-Handoff ungültig:\n- " + "\n- ".join(errors))


def css_bestand() -> str:
    """Alle ausgelieferten Stylesheets als ein Text – Grundlage der Klassenprüfung."""
    teile: list[str] = []
    for pfad in sorted(CSS_EXTENDED.glob("*.css")):
        teile.append(pfad.read_text(encoding="utf-8"))
    for pfad in sorted((ROOT / "themes/PaperMod/assets/css").rglob("*.css")):
        teile.append(pfad.read_text(encoding="utf-8"))
    return "\n".join(teile)


def pruefe_css_vertrag(data: dict[str, Any], css: str) -> list[str]:
    """Jeder `code`-Vertrag muss im echten CSS vorkommen.

    Ein Inventar, das Klassen erfindet, die es nicht gibt, ist eine
    Fiktion mit Tabellenformat. Erlaubt sind Klassen (`.foo`) und
    Element-IDs (`#foo`), weil der Bestand beides benutzt.
    """
    fehler: list[str] = []
    for component in data.get("components", []):
        code = str(component.get("code", "")).strip()
        if not code:
            fehler.append(f"Komponente {component.get('id')} hat keinen code-Vertrag")
            continue
        if code.startswith("."):
            muster = re.compile(r"(?<![\w-])\." + re.escape(code[1:]) + r"(?![\w-])")
        elif code.startswith("#"):
            muster = re.compile(re.escape(code) + r"(?![\w-])")
        else:
            fehler.append(f"Komponente {component.get('id')}: code {code!r} muss mit . oder # beginnen")
            continue
        if not muster.search(css):
            fehler.append(
                f"Komponente {component.get('id')}: {code} existiert nicht im ausgelieferten CSS "
                "– Handoff-Inventar und Bestand sind auseinandergelaufen")
        for variable in component.get("variablen", []):
            if variable not in data["figma"]["semantic"]["light"]:
                fehler.append(
                    f"Komponente {component.get('id')}: Rolle {variable!r} fehlt in der Semantik")
    return fehler


def token(value: Any, token_type: str) -> dict[str, Any]:
    return {"value": value, "type": token_type}


def figma_tokens(data: dict[str, Any]) -> str:
    figma = data["figma"]
    primitives = figma["primitives"]
    primitive_set: dict[str, Any] = {
        "color": {name: token(value, "color") for name, value in primitives["colors"].items()},
        "spacing": {str(value): token(f"{value}px", "dimension") for value in primitives["spacing_px"]},
        "radius": {name: token(f"{value}px", "dimension") for name, value in primitives["radius_px"].items()},
        "typography": {},
    }
    for name, style in figma["typography"].items():
        primitive_set["typography"][name] = token(
            {
                "fontFamily": style["family"],
                "fontWeight": str(style["weight"]),
                "fontSize": f"{style['size_px']}px",
                "lineHeight": str(style["line_height"]),
            },
            "typography",
        )

    result: dict[str, Any] = {
        "$metadata": {
            "tokenSetOrder": ["Primitives", "Semantic/Light", "Semantic/Dark"],
            "source": "data/design/handoff.yaml",
            "stand": data["stand"],
        },
        "$themes": [
            {
                "id": "franksfinanzcheck-light",
                "name": "Light",
                "selectedTokenSets": {"Primitives": "source", "Semantic/Light": "enabled"},
            },
            {
                "id": "franksfinanzcheck-dark",
                "name": "Dark",
                "selectedTokenSets": {"Primitives": "source", "Semantic/Dark": "enabled"},
            },
        ],
        "Primitives": primitive_set,
    }
    for mode in ("Light", "Dark"):
        values = figma["semantic"][mode.lower()]
        result[f"Semantic/{mode}"] = {
            "color": {name: token(f"{{color.{alias}}}", "color") for name, alias in values.items()}
        }
    return json.dumps(result, ensure_ascii=False, indent=2) + "\n"


def relume_brief(data: dict[str, Any]) -> str:
    project = data["projekt"]
    relume = data["relume"]
    lines = [
        "# Relume-Projektbrief – FranksFinanzcheck",
        "",
        f"> Generiert aus `data/design/handoff.yaml` · Stand {data['stand']} · Strukturbrief, keine Veröffentlichungsfreigabe.",
        "",
        "## Projekt-Prompt",
        "",
        "```text",
        f"Erstelle eine mobile-first Sitemap und Wireframes für {project['name']}, {project['produkt']}. ",
        f"Ziel: {project['ziel']}. Ton: {project['ton']}. Sprache: {project['sprache']}. ",
        "Bewahre bestehende Inhalte und Informationsarchitektur; erfinde keine Fakten, Bewertungen, Siegel, Preise oder Testimonials. ",
        "Nutze klare visuelle Hierarchie, großzügige Leseflächen, exakt eine H1 je Seite und zugängliche Formulare. ",
        "Das Ergebnis ist ein Strukturvorschlag. Die Implementierung erfolgt ausschließlich über die Varianten-Werkbank mit menschlicher Freigabe.",
        "```",
        "",
        "## Globale Leitplanken",
        "",
    ]
    lines.extend(f"- {rule}" for rule in relume["global_rules"])
    lines += ["", "## Sitemap und Section-Vertrag", ""]
    for page in relume["pages"]:
        lines += [f"### {page['name']} — `{page['path']}`", "", f"**Nutzerabsicht:** {page['intent']}", "", "| Reihenfolge | Section-ID | Referenz | Aufgabe |", "|---:|---|---|---|"]
        for index, section in enumerate(page["sections"], 1):
            lines.append(f"| {index} | `{section['id']}` | `{section['component']}` | {section['goal']} |")
        lines.append("")
    lines += [
        "## Übergabe zurück in den Code",
        "",
        "1. Relume-Entwurf nur als Struktur- und UX-Hypothese exportieren.",
        "2. In Figma die Tokens aus `figma-tokens.tokens.json` verwenden; keine neuen Farben oder Radien anlegen.",
        "3. Abweichungen als Variante in `data/design/varianten.yaml` registrieren.",
        "4. Playwright und Lighthouse messen; Messprotokoll einfrieren.",
        "5. Erst nach menschlicher Freigabe über `designVariante` aktivieren.",
        "",
    ]
    return "\n".join(lines)


def component_inventory(data: dict[str, Any]) -> str:
    lines = [
        "# Figma ↔ Hugo Komponenten-Inventar",
        "",
        f"> Generiert aus `data/design/handoff.yaml` · Stand {data['stand']}.",
        "",
        "| ID | Figma-Komponente | Hugo/CSS-Vertrag | Pflichtzustände | A11y-Abnahme |",
        "|---|---|---|---|---|",
    ]
    for component in data["components"]:
        states = ", ".join(f"`{state}`" for state in component["states"])
        lines.append(
            f"| `{component['id']}` | `{component['figma']}` | `{component['code']}` | {states} | {component['accessibility']} |"
        )
    lines += [
        "",
        "## Benennungs- und Übergaberegel",
        "",
        "Figma verwendet `Bereich/Komponente/Variante`; der Code-Vertrag bleibt die angegebene CSS-Klasse. Ein visueller Entwurf darf den semantischen HTML-Vertrag nicht ersetzen. Neue Komponenten brauchen vor dem Export einen Inventar-Eintrag mit Fokus-, Dark-Mode- und Fehlerzustand, sofern sie interaktiv sind.",
        "",
    ]
    return "\n".join(lines)


def kontrast(hex_a: str, hex_b: str) -> float:
    """WCAG-2.2-Kontrast, gerechnet – nicht behauptet."""
    def luminanz(wert: str) -> float:
        wert = wert.lstrip("#")
        kanaele = [int(wert[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in kanaele]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    hell, dunkel = sorted((luminanz(hex_a), luminanz(hex_b)), reverse=True)
    return round((hell + 0.05) / (dunkel + 0.05), 2)


# Rollenpaare, die eine Seite tatsächlich braucht: Vordergrund auf Fläche.
KONTRAST_PAARE = (
    ("Fließtext auf Seite", "text", "background", 4.5),
    ("Fließtext auf Karte", "text", "surface", 4.5),
    ("Sekundärtext auf Seite", "text-secondary", "background", 4.5),
    ("Sekundärtext auf Karte", "text-secondary", "surface", 4.5),
    ("Überschrift auf Seite", "heading", "background", 4.5),
    ("Überschrift auf Karte", "heading", "surface", 4.5),
    ("Überschrift auf Soft-Fläche", "heading", "surface-soft", 4.5),
    ("Beschriftung auf Aktion", "action-text", "action", 4.5),
    ("Beschriftung auf Aktion-Hover", "action-text", "action-hover", 4.5),
    ("Invertiert auf Marke", "text-inverted", "heading", 4.5),
    ("Fehlertext auf Seite", "feedback-error", "background", 4.5),
    ("Erfolgstext auf Karte", "feedback-success", "surface", 4.5),
)


def kontrast_matrix(data: dict[str, Any]) -> list[tuple[str, str, str, str, str, str, float]]:
    farben = data["figma"]["primitives"]["colors"]
    zeilen = []
    for mode in ("light", "dark"):
        semantik = data["figma"]["semantic"][mode]
        for label, vg, hg, soll in KONTRAST_PAARE:
            a, b = semantik[vg], semantik[hg]
            zeilen.append((mode, label, a, b, farben[a], farben[b], kontrast(farben[a], farben[b])))
    return zeilen


def annotationen(data: dict[str, Any], rules: dict[str, Any]) -> str:
    """Barrierefreiheits-Spezifikation, die den Entwurf messbar macht."""
    farben = data["figma"]["primitives"]["colors"]
    a11y = rules.get("barrierefreiheit", {})
    kopf = [
        "# ANNOTATIONEN.md – Barrierefreiheit für den Figma-Handoff",
        "",
        f"**Erzeugt aus** `data/design/handoff.yaml` und `data/design/regelwerk.yaml` · "
        f"Stand {data['stand']} · **Nicht von Hand bearbeiten.**",
        "",
        "Ein Entwurf ist erst übergabefähig, wenn jede Rolle ihre Kontrast-",
        "anforderung kennt und nicht erst im Audit erfährt. Die Werte sind nach",
        "WCAG 2.2 gerechnet (relative Luminanz), nicht behauptet.",
        "",
        "## 1. Kontrast-Matrix",
        "",
        "| Modus | Paarung | Vordergrund | Hintergrund | Kontrast | Soll |",
        "|---|---|---|---|---|---|",
    ]
    for mode, label, vg, hg, a, b, wert in kontrast_matrix(data):
        zeichen = "✅" if wert >= 4.5 else ("⚠️" if wert >= 3 else "❌")
        kopf.append(f"| {mode} | {label} | `{vg}` {a} | `{hg}` {b} | {zeichen} {wert:.2f}:1 | 4,5:1 |")
    kopf += [
        "",
        "## 2. Was daraus folgt",
        "",
        f"- **Fließtext** erreicht mindestens {a11y.get('kontrast_fliesstext_min', 4.5)}:1.",
        f"- **Große Typografie** (ab 24 px) darf {a11y.get('kontrast_grosse_typo_min', 3.0)}:1 nutzen, "
        "kleinere Grade nicht.",
        f"- **Meta und Sekundärtext** sind klein: {a11y.get('kontrast_meta_min', 4.5)}:1, keine Ausnahme.",
        f"- **Signalgelb** trägt Anthrazit ({kontrast(farben['anthracite'], farben['yellow']):.2f}:1), "
        f"niemals Weiß. Auf Smaragd ist `accent-2` die Textfarbe "
        f"({kontrast(farben['accent-2'], farben['emerald']):.2f}:1).",
        "- **Fokusring**: 3 px Signalgelb, 2 px Abstand, auf jeder Fläche sichtbar.",
        "",
        "## 3. Zustände, die gezeichnet sein müssen",
        "",
        "| Komponententyp | Pflichtzustände | Zusätzlich bei YMYL |",
        "|---|---|---|",
        "| Aktion | Standard, Hover, Fokus, Deaktiviert | Ladezustand mit Text |",
        "| Formular | Standard, Fokus, Fehler, Erfolg, Deaktiviert | Fehlerzusammenfassung |",
        "| Karte/Link | Standard, Hover, Fokus | besucht, nur wenn relevant |",
        "| Navigation | Desktop, Mobil, Tastatur, aktuell | Skip-Link sichtbar |",
        "| Fläche | hell, dunkel | Druck bei Ratgebern |",
        "",
        "## 4. Nicht verhandelbar",
        "",
        "1. Farbe ist nie der einzige Träger einer Aussage.",
        "2. Jedes Eingabefeld hat ein persistentes Label, keinen Placeholder als Label.",
        "3. Fehlermeldungen benennen Feld und nächsten Schritt.",
        f"4. Tap-Ziele mindestens {a11y.get('tap_ziel_min_px', 24)} px, angestrebt "
        f"{a11y.get('tap_ziel_soll_px', 44)} px.",
        "5. `prefers-reduced-motion` wird respektiert; nichts Wesentliches hängt an Animation.",
        "6. Die DOM-Reihenfolge ist die Lesereihenfolge.",
        "",
    ]
    return "\n".join(kopf)


def pattern_bibliothek(data: dict[str, Any]) -> str:
    """Muster statt Bauteile: wann, wie viel, was nie."""
    typo = data["figma"]["typography"]
    figma = data["figma"]
    zeilen = [
        "# PATTERNS.md – Musterbibliothek für den Figma-Handoff",
        "",
        f"**Erzeugt aus** `data/design/handoff.yaml` · Stand {data['stand']} · "
        "**Nicht von Hand bearbeiten.**",
        "",
        "Ein Inventar sagt, was es gibt. Ein Muster sagt, wann es eingesetzt wird,",
        "wie es atmet und was es niemals tut. Ohne diese Ebene baut jeder Entwurf die",
        "Komponenten neu zusammen.",
        "",
        "## 1. Der Seitenrhythmus",
        "",
        "| Zone | Zweck | Typografie | Abstand danach |",
        "|---|---|---|---|",
        "| Einstieg | Eine Aussage, ein nächster Schritt | `h1_home` / `h1_article` + `lead` | 64 px |",
        "| Beweis | Warum man das glauben darf | `meta` + `trust-pill` | 32 px |",
        "| Kern | Die eigentliche Arbeit | `h2` + `body` | 44 px |",
        "| Werkzeug | Etwas tun, nicht nur lesen | `h2` + Komponente | 44 px |",
        "| Abschluss | Ein Angebot, keine Falle | `h2` + `button-primary` | 64 px |",
        "",
        "**Die tragende Regel:** Der Einstieg ist nie länger als zwei Zeilen H1.",
        "Passt die Aussage nicht in zwei Zeilen, ist sie eine Zusammenfassung –",
        "und die gehört in den Lead.",
        "",
        "## 2. Typografie im Einsatz",
        "",
        "| Stil | Desktop | Mobil | Familie | Aufgabe |",
        "|---|---|---|---|---|",
    ]
    for name, style in typo.items():
        zeilen.append(
            f"| `{name}` | {style['size_px']} px / {style['weight']} | {style['mobile_px']} px "
            f"| {style['family']} | {style.get('einsatz', '')} |")
    zeilen += [
        "",
        f"Skala: {figma['breakpoints']['mobile']} / {figma['breakpoints']['tablet']} / "
        f"{figma['breakpoints']['desktop']} px. Inhalt {figma['grid']['content_breite_px']} px breit,",
        f"Navigation {figma['grid']['nav_breite_px']} px. Grundraster "
        f"{figma['grid']['basis_px']} px mit den dokumentierten Feinstufen "
        f"{', '.join(str(x) for x in figma['grid']['feinstufen_px'])} px.",
        "",
        "## 3. Tiefe und Fläche",
        "",
        "| Ebene | Schatten | Radius | Wann |",
        "|---|---|---|---|",
    ]
    schatten = figma["primitives"]["elevation"]
    zeilen += [
        f"| Ruhende Karte | `{schatten['karte']}` | md (12) | Teaser, Cluster |",
        f"| Angehobene Karte | `{schatten['hover']}` | md (12) | Hover, nur ohne reduced-motion |",
        f"| Schwebende Fläche | `{schatten['schwebend']}` | lg (16) | Callout, Autorenbox |",
        f"| Handlung | `{schatten['cta']}` | pill (999) | ausschließlich Primär-Button |",
        "",
        "**Schatten oder Rand, nie beides hart übereinander.** Das System kennt vier",
        "Schattenstufen; wer eine fünfte braucht, hat ein Hierarchieproblem.",
        "",
        "## 4. Muster im Einsatz",
        "",
    ]
    texte = {
        "kurzantwort": "Steht direkt unter H1 und Lead. Ein Absatz, höchstens drei Sätze. "
                       "Das Signet ist dekorativ (`aria-hidden`), die Antwort ist echter Text.",
        "pillar-box": "Themenkasten auf der Ratgeber-Zentrale: Label als Überzeile, "
                      "H2 als Frage, drei Stichpunkte, ein Link. Keine vierte Zeile – "
                      "wer mehr erklären muss, braucht eine eigene Seite.",
        "pill": "Kleine Statusmarke („ungeprüft“, „aktualisiert“). Immer Text plus Fläche, "
                "nie Farbe allein; maximale Breite gilt für die Beschriftung, nicht für den Rand.",
        "consent-banner": "Einmal, ruhig, ohne Overlay-Falle: zwei gleichwertige Knöpfe, "
                          "Ablehnen so leicht wie Zustimmen, kein Vorausgewähltes, Fokus bleibt "
                          "im Banner bis zur Entscheidung.",
        "skip-link": "Erstes fokussierbares Element, außerhalb des Viewports, beim Fokus "
                     "sichtbar über der Navigation. Ziel ist `#main`, nicht der Seitenanfang.",
        "pinterest-cta": "Fremdmarken-Rot ausschließlich hier, immer mit Text „Auf Pinterest "
                         "speichern“ – die Farbe ist nie das einzige Signal.",
        "kurzantwort": "Steht direkt unter H1 und Lead. Ein Absatz, höchstens drei Sätze. "
                       "Das Signet ist dekorativ (`aria-hidden`), die Antwort ist echter Text.",
        "kostenprofil": "Das Markenobjekt: immer dieselben vier Schritte in derselben "
                        "Reihenfolge. Hier sind Indexzahlen erlaubt, weil der Inhalt eine "
                        "Reihenfolge ist – auf jeder anderen Fläche bleiben 01/02/03 verboten.",
        "spar-matrix": "Fünf Spalten, `tabular-nums`, Zebra, Sticky-Kopf. Unter 760 px wird "
                       "jede Zeile zur Karte (Feldnamen aus `data-label`, kein zweites Markup). "
                       "Fehlt eine Quelle, fehlt die Zeile.",
        "callout": "Vier Typen: Tipp, Info, Warnung, Gefahr. Der Typ steht als Text in der "
                   "Überschrift, nicht nur als Farbe. Linker Rand 3–4 px, Fläche getönt.",
        "newsletter-form": "Ein Feld, ein Knopf, ein Satz zum Zweck. Fehler unter dem Feld mit "
                           "einem Satz, der den nächsten Schritt nennt. Kein Overlay, kein Countdown.",
        "author-trust-box": "Avatar, Name, Qualifikation, Prüfhinweis – alles als Text. Eine "
                            "Autorenbox ohne nachvollziehbare Qualifikation schadet E-E-A-T.",
        "header": "Skip-Link zuerst, aktuelle Seite sichtbar markiert, Tastaturreihenfolge "
                  "gleich Lesereihenfolge.",
    }
    for component in data["components"]:
        if component["id"] not in texte:
            continue
        zeilen += [
            f"### `{component['figma']}` — `{component['code']}`",
            "",
            texte[component["id"]],
            "",
            f"Zustände: {', '.join(component['states'])}.  {component['accessibility']}",
            "",
        ]
    zeilen += [
        "## 5. Was das System niemals tut",
        "",
        "1. Zwei Primärhandlungen in einem Viewport.",
        "2. Signalgelb als Textfarbe auf hellem Grund.",
        "3. Karussell, Autoplay oder Parallax auf Leseflächen.",
        "4. Layout-Properties animieren (`width`, `height`, `top`, `margin`).",
        "5. `outline: none` ohne sichtbaren Ersatz.",
        "6. Externe CDNs, Fremdfonts im Fließtext, Tracking ohne Einwilligung.",
        "7. Erfundene Bewertungen, Siegel, Sparbeträge oder Testimonials.",
        "8. Eine zweite H1 pro Seite, auch nicht unsichtbar.",
        "",
        "## 6. Abnahme je Entwurf",
        "",
        "- [ ] Genau eine H1, maximal zwei Zeilen, kein Label darüber.",
        "- [ ] Alle Farben als Variablen, keine Hex-Werte im Entwurf.",
        "- [ ] Hell und Dunkel vollständig, inklusive Fokusring.",
        "- [ ] 390 px ohne horizontalen Überlauf, Tap-Ziele ≥ 44 px.",
        "- [ ] Hover, Fokus, Fehler, Leer- und Ladezustand gezeichnet.",
        "- [ ] `prefers-reduced-motion` bedacht.",
        "- [ ] Jede Zahl hat eine Quelle; keine Platzhalter-Fakten.",
        "",
    ]
    return "\n".join(zeilen)


def spezifikation(data: dict[str, Any], rules: dict[str, Any]) -> str:
    """Eine Seite, die das System aushaelt – ohne Figma, ohne Build."""
    figma = data["figma"]
    farben = figma["primitives"]["colors"]
    typo = figma["typography"]
    sem = figma["semantic"]
    a11y = rules.get("barrierefreiheit", {})
    schatten = figma["primitives"]["elevation"]

    def swatch(name: str) -> str:
        wert = farben[name]
        return (f'<div class="sw"><div class="chip" style="background:{wert}"></div>'
                f'<div><code>{name}</code><br /><span>{wert}</span></div></div>')

    kacheln = "".join(swatch(n) for n in farben)
    rollen_hell = "".join(
        f'<tr><td><code>{rolle}</code></td><td>{ziel}</td>'
        f'<td><span class="dot" style="background:{farben[ziel]}"></span>{farben[ziel]}</td></tr>'
        for rolle, ziel in sem["light"].items())
    rollen_dunkel = "".join(
        f'<tr><td><code>{rolle}</code></td><td>{ziel}</td>'
        f'<td><span class="dot" style="background:{farben[ziel]}"></span>{farben[ziel]}</td></tr>'
        for rolle, ziel in sem["dark"].items())

    typo_proben = "".join(
        f'<div class="typo"><div style="font-family:{t["family"]},system-ui;'
        f'font-size:{min(t["size_px"], 44)}px;font-weight:{t["weight"]};line-height:{t["line_height"]};'
        f'{"font-style:italic;" if str(t.get("style", "")) == "italic" else ""}'
        f'letter-spacing:{t.get("tracking", "0")}">'
        f'{"Fixkosten im Griff" if name.startswith("h") else "Klar rechnen statt hoffen"}</div>'
        f'<p><code>{name}</code> · {t["size_px"]} / {t["mobile_px"]} px · {t["weight"]} · '
        f'{t["family"]} · {t.get("einsatz", "")}</p></div>'
        for name, t in typo.items())

    abstaende = "".join(
        f'<div class="sp"><span style="width:{px}px"></span><code>{px}</code></div>'
        for px in figma["primitives"]["spacing_px"])
    radien = "".join(
        f'<div class="rd" style="border-radius:{px}px"></div><code>{name} {px}</code>'
        for name, px in figma["primitives"]["radius_px"].items() if px < 999)
    tiefe = "".join(
        f'<div class="sh" style="box-shadow:{wert}"><code>{name}</code></div>'
        for name, wert in schatten.items())

    matrix = "".join(
        f'<tr><td>{mode}</td><td>{label}</td><td class="num">{wert:.2f}:1</td></tr>'
        for mode, label, _vg, _hg, _a, _b, wert in kontrast_matrix(data))

    komponenten = "".join(
        f'<article class="karte" data-komponente="{c["id"]}">'
        f'<h3>{c["figma"]}</h3>'
        f'<p class="code"><code>{c["code"]}</code></p>'
        f'<p class="lead" style="margin:6px 0;font-size:13px">'
        f'{", ".join(STATE_LABELS.get(z, z) for z in c["states"])}</p>'
        f'<p class="lead" style="margin:0;font-size:13px">{c["accessibility"]}</p>'
        f'</article>'
        for c in data["components"])

    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>FranksFinanzcheck – Design-Spezifikation</title>
<style>
  :root {{
    --emerald:{farben['emerald']}; --bright:{farben['emerald-bright']};
    --yellow:{farben['yellow']}; --ink:{farben['anthracite']};
    --page:{farben['page-light']}; --line:{farben['border-light']};
    --soft:{farben['emerald-soft']}; --sec:{farben['secondary-light']};
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--page); color:var(--ink);
    font-family:Inter,system-ui,sans-serif; line-height:1.6; }}
  main {{ max-width:1100px; margin:0 auto; padding:0 24px 96px; }}
  header {{ background:var(--emerald); color:#fff; padding:72px 24px 56px; margin-bottom:56px; }}
  header .in {{ max-width:1100px; margin:0 auto; }}
  h1 {{ font-size:clamp(34px,6vw,64px); line-height:1.05; margin:0 0 12px;
    letter-spacing:-.02em; }}
  header p {{ color:var(--bright); margin:0; max-width:62ch; }}
  .strich {{ width:120px; height:6px; background:var(--yellow); border-radius:999px; margin:24px 0; }}
  h2 {{ font-size:26px; margin:64px 0 8px; color:var(--emerald); }}
  h2::after {{ content:""; display:block; width:56px; height:2px; background:var(--yellow); margin-top:10px; }}
  .lead {{ color:var(--sec); max-width:70ch; margin:12px 0 24px; }}
  .gitter {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:12px; }}
  .sw {{ display:flex; gap:10px; align-items:center; background:#fff;
    border:1px solid var(--line); border-radius:12px; padding:10px; }}
  .chip {{ width:38px; height:38px; border-radius:10px; flex:0 0 auto;
    box-shadow:inset 0 0 0 1px rgba(0,0,0,.08); }}
  .sw code {{ font-size:12px; }} .sw span {{ font-size:11px; color:var(--sec); }}
  table {{ width:100%; border-collapse:collapse; font-size:14px; background:#fff;
    border:1px solid var(--line); border-radius:12px; overflow:hidden; }}
  th, td {{ text-align:left; padding:9px 12px; border-bottom:1px solid var(--line); }}
  th {{ background:var(--soft); font-size:12px; letter-spacing:.04em; text-transform:uppercase; }}
  .dot {{ display:inline-block; width:12px; height:12px; border-radius:50%;
    margin-right:7px; vertical-align:middle; box-shadow:inset 0 0 0 1px rgba(0,0,0,.12); }}
  .num {{ font-variant-numeric:tabular-nums; }}
  .zwei {{ display:grid; grid-template-columns:1fr 1fr; gap:24px; }}
  @media (max-width:760px) {{ .zwei {{ grid-template-columns:1fr; }} }}
  .typo {{ border-bottom:1px solid var(--line); padding:18px 0; }}
  .typo p {{ margin:8px 0 0; font-size:13px; color:var(--sec); }}
  .sp {{ display:flex; align-items:center; gap:10px; margin-bottom:6px; }}
  .sp span {{ height:12px; background:var(--emerald); border-radius:3px; display:inline-block; }}
  .rd {{ width:72px; height:44px; border:2px solid var(--emerald); background:#fff;
    border-radius:12px; display:inline-block; margin:0 8px 8px 0; }}
  .sh {{ background:#fff; border-radius:12px; padding:16px; margin-bottom:12px; display:inline-block; }}
  .fuss {{ margin-top:64px; padding-top:24px; border-top:1px solid var(--line);
    font-size:13px; color:var(--sec); }}
  .grenze {{ display:inline-block; background:var(--yellow); color:var(--ink);
    border-radius:999px; padding:4px 14px; font-weight:800; font-size:13px; }}
  .karte {{ background:#fff; border:1px solid var(--line); border-radius:12px; padding:16px; }}
  .karte h3 {{ margin:0 0 6px; font-size:15px; color:var(--emerald); }}
  .karte .code code {{ background:var(--soft); border-radius:6px; padding:2px 6px;
    font-size:12px; color:var(--emerald); }}
  .karte .lead {{ color:var(--sec); }}
</style>
</head>
<body>
<header><div class="in">
  <h1>{data['projekt']['name']}<br />Design-Spezifikation</h1>
  <p>{data['projekt']['produkt']}. {data['projekt']['ziel']}.</p>
  <div class="strich"></div>
  <p style="font-size:13px">Stand {data['stand']} · {data['projekt']['sprache']} ·
    {figma['breakpoints']['mobile']}/{figma['breakpoints']['tablet']}/{figma['breakpoints']['desktop']}/{figma['breakpoints']['wide']} px ·
    {len(farben)} Farben · {len(typo)} Textstile · {len(data['components'])} Komponenten</p>
</div></header>
<main>
  <h2>1. Primitives</h2>
  <p class="lead">Rohwerte. Keine Rolle zeigt direkt hierher – Rollen sind Aliase
    und stehen im nächsten Abschnitt. {len(farben)} Farben, alle aus dem Regelwerk.</p>
  <div class="gitter">{kacheln}</div>

  <h2>2. Semantische Rollen</h2>
  <p class="lead">Dieselben Rollen in beiden Modi. Ein Entwurf, der eine Rolle
    nur hell definiert, ist unfertig.</p>
  <div class="zwei">
    <div><h3 style="font-size:15px">Hell</h3>
      <table><thead><tr><th>Rolle</th><th>Primitive</th><th>Wert</th></tr></thead>
      <tbody>{rollen_hell}</tbody></table></div>
    <div><h3 style="font-size:15px">Dunkel</h3>
      <table><thead><tr><th>Rolle</th><th>Primitive</th><th>Wert</th></tr></thead>
      <tbody>{rollen_dunkel}</tbody></table></div>
  </div>

  <h2>3. Typografie</h2>
  <p class="lead">Jede Stufe trägt Desktop- und Mobilwert. Überschriften dürfen
    fließend skalieren; Fließtext, Meta und Labels bleiben bei mindestens 85 %.</p>
  {typo_proben}

  <h2>4. Abstand, Radius, Tiefe</h2>
  <p class="lead">{figma['grid']['basis_px']}-px-Grundraster mit den dokumentierten
    Feinstufen. Vier Schattenstufen, keine fünfte.</p>
  <div class="zwei">
    <div>{abstaende}</div>
    <div>{radien}</div>
  </div>
  <div style="margin-top:24px">{tiefe}</div>

  <h2>5. Kontrastgrenze</h2>
  <p class="lead">Gerechnet nach WCAG 2.2. Soll für Fließtext:
    <span class="grenze">{a11y.get('kontrast_fliesstext_min', 4.5)}:1</span></p>
  <table><thead><tr><th>Modus</th><th>Paarung</th><th>Kontrast</th></tr></thead>
  <tbody>{matrix}</tbody></table>

  <h2>6. Komponenten</h2>
  <p class="lead">Achtzehn Bausteine, jeder mit seinem CSS-Vertrag. Der Vertrag ist
    die halbe Miete: eine Komponente ohne existierende Klasse ist eine Zeichnung,
    kein Bauteil.</p>
  <div class="gitter">{komponenten}</div>

  <p class="fuss">Erzeugt von <code>scripts/design_handoff.py</code> aus
    <code>data/design/handoff.yaml</code> und <code>data/design/regelwerk.yaml</code>.
    Diese Seite ist Nachweis, keine Freigabe: Produktionswahrheit bleiben
    DESIGN.md, das Regelwerk und der Hugo-Bestand.</p>
</main>
</body>
</html>
"""


def komponenten_katalog(data: dict[str, Any]) -> str:
    """Alle Komponenten als schematische Proben, nicht als Tabelle."""
    karten = []
    for c in data["components"]:
        zustaende = ", ".join(STATE_LABELS.get(z, z) for z in c["states"] if z != "dark")
        karten.append(f"""      <article class="karte">
        <div class="probe" data-probe="{c['id']}">
          <span class="probe-label">{c['figma'].split('/')[-1]}</span>
        </div>
        <h3>{c['figma']}</h3>
        <p class="code"><code>{c['code']}</code></p>
        <p class="meta">Zustände: {zustaende}</p>
        <p class="a11y">{c['accessibility']}</p>
      </article>""")
    return "\n".join(karten)


def design_system_seite(data: dict[str, Any], rules: dict[str, Any]) -> str:
    """Eigenständige Design-System-Sicht: ansehen und prüfen ohne Figma.

    Dieselben Rollen wie im Blog als CSS-Variablen, zwei Modi per Umschalter,
    alle Komponenten als Probe, Kontrast-Matrix als Nachweis. Kein Netz,
    keine Anmeldung, kein Build.
    """
    figma = data["figma"]
    farben = figma["primitives"]["colors"]
    typo = figma["typography"]
    sem = figma["semantic"]
    a11y = rules.get("barrierefreiheit", {})
    schatten = figma["primitives"]["elevation"]

    def variablen(mode: str) -> str:
        return "\n".join(
            f"    --{rolle.replace('_', '-')}: {farben[ziel]};"
            for rolle, ziel in sem[mode].items())

    swatches = "".join(
        f'<li><span class="sw" style="background:{wert}"></span>'
        f'<strong>{name}</strong><small>{wert}</small></li>'
        for name, wert in farben.items())

    typo_proben = "".join(
        f'<div class="typo-row">'
        f'<div class="typo-probe" style="font-family:{t["family"]},system-ui;'
        f'font-size:{min(t["size_px"], 40)}px;font-weight:{t["weight"]};'
        f'line-height:{t["line_height"]};'
        f'{"font-style:italic;" if str(t.get("style", "")) == "italic" else ""}">'
        f'{"Fixkosten im Griff" if name.startswith("h") else "Klar rechnen statt hoffen"}</div>'
        f'<dl><dt>{name}</dt><dd>{t["size_px"]} / {t["mobile_px"]} px · '
        f'{t["weight"]} · {t["family"]}</dd></dl></div>'
        for name, t in typo.items())

    abstaende = "".join(
        f'<li><span class="bar" style="width:{px}px"></span><code>{px} px</code></li>'
        for px in figma["primitives"]["spacing_px"])

    matrix = "".join(
        f'<tr><td>{mode}</td><td>{label}</td><td class="num">{wert:.2f}:1</td>'
        f'<td>{"✓" if wert >= 4.5 else "✗"}</td></tr>'
        for mode, label, _vg, _hg, _a, _b, wert in kontrast_matrix(data))

    return f"""<!doctype html>
<html lang="de" data-modus="light">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>FranksFinanzcheck – Design-System</title>
<style>
  /* Dieselben Rollen wie im Blog: eine Variable je Rolle, zwei Modi. */
  :root {{
{variablen('light')}
    --radius-sm: {figma['primitives']['radius_px']['sm']}px;
    --radius-md: {figma['primitives']['radius_px']['md']}px;
    --radius-lg: {figma['primitives']['radius_px']['lg']}px;
    --radius-pill: {figma['primitives']['radius_px']['pill']}px;
  }}
  html[data-modus="dark"] {{
{variablen('dark')}
  }}
  * {{ box-sizing: border-box; }}
  html {{ scroll-behavior: smooth; }}
  @media (prefers-reduced-motion: reduce) {{
    html {{ scroll-behavior: auto; }}
    * {{ transition: none !important; }}
  }}
  body {{
    margin: 0; background: var(--background); color: var(--text);
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    font-size: 18px; line-height: 1.65; -webkit-font-smoothing: antialiased;
    transition: background .3s, color .3s;
  }}
  h1, h2, h3 {{ font-family: Inter, system-ui, sans-serif; color: var(--heading);
    text-wrap: balance; margin: 0; }}
  .huelle {{ max-width: 1120px; margin: 0 auto; padding: 0 24px 96px; }}
  header.kopf {{
    background: var(--surface); border-bottom: 1px solid var(--border);
    padding: 40px 24px 32px; margin-bottom: 56px;
  }}
  header.kopf .innen {{ max-width: 1120px; margin: 0 auto; }}
  header.kopf h1 {{ font-size: clamp(30px, 5vw, 48px); letter-spacing: -.02em; }}
  header.kopf p {{ color: var(--text-secondary); max-width: 68ch; margin: 12px 0 0; }}
  .strich {{ width: 96px; height: 5px; background: var(--action);
    border-radius: var(--radius-pill); margin: 20px 0; }}
  .schalter {{ display: flex; gap: 8px; margin-top: 20px; flex-wrap: wrap; }}
  .schalter button {{
    font: inherit; font-size: 15px; font-weight: 700; cursor: pointer;
    min-height: 44px; padding: 0 20px; border-radius: var(--radius-pill);
    border: 1px solid var(--border); background: var(--background);
    color: var(--text); transition: background .16s, color .16s;
  }}
  .schalter button[aria-pressed="true"] {{
    background: var(--action); color: var(--action-text); border-color: var(--action);
  }}
  .schalter button:focus-visible {{ outline: 3px solid var(--focus); outline-offset: 2px; }}
  section {{ margin-top: 72px; scroll-margin-top: 24px; }}
  h2 {{ font-size: 26px; }}
  h2::after {{ content: ""; display: block; width: 56px; height: 2px;
    background: var(--action); margin-top: 10px; }}
  .lead {{ color: var(--text-secondary); max-width: 72ch; margin: 14px 0 26px; }}
  ul.swatches {{ list-style: none; padding: 0; margin: 0;
    display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 12px; }}
  ul.swatches li {{ background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-md); padding: 12px; display: flex;
    flex-direction: column; gap: 4px; }}
  .sw {{ display: block; height: 44px; border-radius: var(--radius-sm);
    box-shadow: inset 0 0 0 1px rgba(0,0,0,.10); margin-bottom: 6px; }}
  ul.swatches strong {{ font-size: 14px; }}
  ul.swatches small {{ color: var(--text-secondary); font-size: 12px;
    font-variant-numeric: tabular-nums; }}
  .typo-row {{ border-bottom: 1px solid var(--border); padding: 20px 0; }}
  .typo-row dl {{ margin: 10px 0 0; display: flex; gap: 12px; align-items: baseline; flex-wrap: wrap; }}
  .typo-row dt {{ font-weight: 700; font-size: 13px; color: var(--heading); }}
  .typo-row dd {{ margin: 0; font-size: 13px; color: var(--text-secondary); }}
  .raster {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; }}
  .karte {{ background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-lg); padding: 18px; box-shadow: {schatten['karte']}; }}
  .karte h3 {{ font-size: 15px; margin: 0 0 2px; }}
  .karte .code {{ margin: 0 0 8px; }}
  .karte code {{ font-size: 12px; background: var(--surface-soft);
    padding: 2px 6px; border-radius: 6px; color: var(--text); }}
  .karte .meta {{ font-size: 13px; color: var(--text-secondary); margin: 0 0 8px; }}
  .karte .a11y {{ font-size: 13px; margin: 0; }}
  .probe {{ min-height: 64px; border-radius: var(--radius-md);
    background: var(--surface-soft); display: flex; align-items: center;
    justify-content: center; margin-bottom: 12px; padding: 12px; }}
  .probe-label {{ font-size: 13px; font-weight: 700; color: var(--heading); }}
  .probe[data-probe^="button"] {{ background: var(--action); }}
  .probe[data-probe^="button"] .probe-label {{ color: var(--action-text); }}
  .probe[data-probe="callout"] {{ border-left: 4px solid var(--heading); justify-content: flex-start; }}
  .probe[data-probe="pinterest-cta"] {{ background: {farben['pinterest']}; }}
  .probe[data-probe="pinterest-cta"] .probe-label {{ color: #FFFFFF; }}
  ul.abstaende {{ list-style: none; padding: 0; margin: 0; }}
  ul.abstaende li {{ display: flex; align-items: center; gap: 12px; margin-bottom: 6px; }}
  .bar {{ height: 12px; background: var(--heading); border-radius: 3px; }}
  ul.abstaende code {{ font-size: 12px; color: var(--text-secondary); }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14px;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-md); overflow: hidden; }}
  th, td {{ text-align: left; padding: 10px 14px; border-bottom: 1px solid var(--border); }}
  th {{ background: var(--surface-soft); font-size: 12px; letter-spacing: .04em;
    text-transform: uppercase; color: var(--heading); }}
  .num {{ font-variant-numeric: tabular-nums; }}
  .fuss {{ margin-top: 72px; padding-top: 24px; border-top: 1px solid var(--border);
    font-size: 14px; color: var(--text-secondary); }}
  .fuss code {{ background: var(--surface-soft); padding: 1px 5px; border-radius: 5px; }}
  @media (max-width: 600px) {{
    body {{ font-size: 17px; }}
    .huelle {{ padding: 0 16px 72px; }}
    header.kopf {{ padding: 28px 16px 24px; }}
    section {{ margin-top: 52px; }}
  }}
</style>
</head>
<body>
<header class="kopf"><div class="innen">
  <h1>{data['projekt']['name']}<br />Design-System</h1>
  <p>{data['projekt']['produkt']}. {data['projekt']['ziel']}.</p>
  <div class="strich"></div>
  <div class="schalter" role="group" aria-label="Farbschema">
    <button type="button" id="btn-hell" aria-pressed="true">Hell</button>
    <button type="button" id="btn-dunkel" aria-pressed="false">Dunkel</button>
  </div>
</div></header>

<main class="huelle">
  <section id="farben">
    <h2>1. Farben</h2>
    <p class="lead">{len(farben)} Werte, alle aus dem Marken-Regelwerk. Jede Rolle
      darunter ist ein Alias auf genau einen dieser Werte.</p>
    <ul class="swatches">{swatches}</ul>
  </section>

  <section id="typografie">
    <h2>2. Typografie</h2>
    <p class="lead">Jede Stufe mit Desktop- und Mobilwert. Die Probe zeigt die
      Desktop-Größe; auf schmalen Geräten greift der kleinere Wert.</p>
    {typo_proben}
  </section>

  <section id="komponenten">
    <h2>3. Komponenten</h2>
    <p class="lead">Schematische Proben, keine fertigen Layouts. Sie zeigen
      Rollenbindung, Radius und Zustandsliste. Schalte oben auf „Dunkel", um
      beide Modi zu prüfen.</p>
    <div class="raster">
{komponenten_katalog(data)}
    </div>
  </section>

  <section id="abstand">
    <h2>4. Abstand</h2>
    <p class="lead">{figma['grid']['basis_px']}-px-Grundraster mit den
      dokumentierten Feinstufen {', '.join(str(x) for x in figma['grid']['feinstufen_px'])} px.</p>
    <ul class="abstaende">{abstaende}</ul>
  </section>

  <section id="kontrast">
    <h2>5. Kontrast</h2>
    <p class="lead">Gerechnet nach WCAG 2.2, Soll {a11y.get('kontrast_fliesstext_min', 4.5)}:1
      für Fließtext. Die Tabelle ist der Nachweis, nicht die Behauptung.</p>
    <table>
      <thead><tr><th>Modus</th><th>Paarung</th><th>Kontrast</th><th>AA</th></tr></thead>
      <tbody>{matrix}</tbody>
    </table>
  </section>

  <p class="fuss">Erzeugt von <code>scripts/design_handoff.py</code> aus
    <code>data/design/handoff.yaml</code>. Diese Seite braucht kein Netz, keine
    Anmeldung und kein Figma. Verbindlich bleiben DESIGN.md und das Regelwerk.</p>
</main>

<script>
  (function () {{
    var html = document.documentElement;
    var hell = document.getElementById('btn-hell');
    var dunkel = document.getElementById('btn-dunkel');
    function setze(modus) {{
      html.setAttribute('data-modus', modus);
      hell.setAttribute('aria-pressed', String(modus === 'light'));
      dunkel.setAttribute('aria-pressed', String(modus === 'dark'));
      try {{ localStorage.setItem('ff-design-modus', modus); }} catch (e) {{ /* privat */ }}
    }}
    var gespeichert = null;
    try {{ gespeichert = localStorage.getItem('ff-design-modus'); }} catch (e) {{ /* privat */ }}
    if (gespeichert === 'dark') setze('dark');
    hell.addEventListener('click', function () {{ setze('light'); }});
    dunkel.addEventListener('click', function () {{ setze('dark'); }});
  }})();
</script>
</body>
</html>
"""


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def plugin_daten(data: dict[str, Any]) -> dict[str, Any]:
    """Der Datenblock, den das Figma-Plugin als einzige Wahrheit liest."""
    figma = data["figma"]
    return {
        "stand": data["stand"],
        "projekt": data["projekt"],
        "pages": figma["page_order"],
        "breakpoints": figma["breakpoints"],
        "colors": figma["primitives"]["colors"],
        "semantic": figma["semantic"],
        "spacing": figma["primitives"]["spacing_px"],
        "radius": figma["primitives"]["radius_px"],
        "elevation": figma["primitives"]["elevation"],
        "typography": {
            name: {
                "family": style["family"],
                "size": style["size_px"],
                "mobile": style["mobile_px"],
                "lineHeight": style["line_height"],
                "weight": style["weight"],
                "italic": str(style.get("style", "")) == "italic",
            }
            for name, style in figma["typography"].items()
        },
        "components": [
            {"id": c["id"], "figma": c["figma"], "code": c["code"], "states": c["states"]}
            for c in data["components"]
        ],
        "state_labels": STATE_LABELS,
    }


def plugin_code(data: dict[str, Any]) -> str:
    """Baut das Plugin aus seiner Quelle plus Datenblock.

    Das Plugin ist Code, der in Figma läuft – deshalb wird es nicht als
    Text ins Repository geschrieben, sondern aus `source.js` + JSON
    erzeugt. Eine Zeile `const DATA = DATA_MARKE;` bleibt der einzige
    Kopplungspunkt; fehlt sie, bricht der Generator ab.
    """
    quelle = PLUGIN_SOURCE.read_text(encoding="utf-8")
    marke = "const DATA = DATA_MARKE;"
    if marke not in quelle:
        raise ValueError(f"figma/design-system-builder/{PLUGIN_SOURCE.name}: "
                         f"Platzhalter `{marke}` fehlt – der Generator kann nichts injizieren")
    daten = json.dumps(plugin_daten(data), ensure_ascii=False, indent=2, sort_keys=True)
    # `</script` in Daten würde in ui.html die Skriptgrenze sprengen.
    daten = daten.replace("</", "<\\/")
    return quelle.replace(marke, "const DATA = " + daten + ";", 1)


def render(data: dict[str, Any], rules: dict[str, Any]) -> dict[str, str]:
    return {
        "figma-tokens.tokens.json": figma_tokens(data),
        "relume-project-brief.md": relume_brief(data),
        "component-inventory.md": component_inventory(data),
        "patterns.md": pattern_bibliothek(data),
        "ANNOTATIONEN.md": annotationen(data, rules),
        "spezifikation.html": spezifikation(data, rules),
        "design-system.html": design_system_seite(data, rules),
    }


def manifest(data: dict[str, Any], outputs: dict[str, str], plugins: dict[str, str]) -> str:
    # KEINE Selbstreferenz: Eine Datei, die ihren eigenen Hash enthält, kann
    # sich nie selbst prüfen (Quadratur). Die Quellen sind der Vertrag, der
    # Generator ist die Version (`generator_version`).
    sources = [SOURCE, RULES, ROOT / "DESIGN.md", ROOT / "PRODUCT.md", PLUGIN_SOURCE]
    value = {
        "schema": VERSION,
        "stand": data["stand"],
        "generator": "scripts/design_handoff.py",
        "generator_version": VERSION,
        "sources": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources
        },
        "artifacts": {name: sha256(content) for name, content in sorted(outputs.items())},
        "plugins": {
            f"figma/design-system-builder/{name}": sha256(content)
            for name, content in sorted(plugins.items())
        },
    }
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def write_outputs(target: Path, outputs: dict[str, str]) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for name, content in outputs.items():
        (target / name).write_text(content, encoding="utf-8")


def check_outputs(expected: dict[str, str], target: Path | None = None) -> list[str]:
    ziel = target or OUT
    drift: list[str] = []
    for name, content in expected.items():
        path = ziel / name
        if not path.exists():
            drift.append(f"fehlt: {path.relative_to(ROOT)}")
        elif path.read_text(encoding="utf-8") != content:
            drift.append(f"veraltet: {path.relative_to(ROOT)}")
    return drift


def selftest() -> None:
    data = load_yaml(SOURCE)
    rules = load_yaml(RULES)
    validate(data, rules)

    # 1) Determinismus: zweimal rendern, Byte für Byte gleich.
    first = render(data, rules)
    second = render(data, rules)
    assert first == second, "Ausgabe ist nicht deterministisch"

    # 2) Tokens-Studio-Vertrag.
    parsed = json.loads(first["figma-tokens.tokens.json"])
    assert len(parsed["$themes"]) == 2
    assert "Semantic/Dark" in parsed
    assert parsed["Primitives"]["spacing"]["8"]["value"] == "8px"
    assert parsed["Semantic/Light"]["color"]["heading"]["value"] == "{color.emerald}"

    # 3) Kontrast: die Matrix muss rechnen, nicht raten.
    assert abs(kontrast("#FFFFFF", "#000000") - 21.0) < 0.01
    assert abs(kontrast("#FFB300", "#FFB300") - 1.0) < 0.01
    for mode, label, _vg, _hg, _a, _b, wert in kontrast_matrix(data):
        assert wert >= 4.5, f"Kontrast zu schwach: {mode} / {label} = {wert}"
    assert "Kontrast-Matrix" in first["ANNOTATIONEN.md"]

    # 4) Muster und lokale Sicht: keine Netzabhängigkeit, beide Modi.
    assert "Seitenrhythmus" in first["patterns.md"]
    assert "http" not in first["design-system.html"].split("<body>")[0]
    assert "data-modus" in first["design-system.html"]
    assert first["design-system.html"].count('class="karte"') >= len(data["components"])

    # 5) Plugin: Datenblock wird injiziert, Quelltext bleibt intakt.
    code = plugin_code(data)
    assert "DATA_MARKE" not in code, "Platzhalter wurde nicht ersetzt"
    assert "figma.showUI" in code
    assert "\n" in code

    # 6) Sabotage-Probe: erfundene CSS-Klasse muss auffallen.
    kaputt = json.loads(json.dumps(data))
    kaputt["components"].append({
        "id": "geist", "figma": "Geist/X", "code": ".gibt-es-nicht",
        "states": ["default", "dark"], "accessibility": "x",
    })
    assert pruefe_css_vertrag(kaputt, css_bestand()), "erfundene CSS-Klasse blieb unentdeckt"

    # 7) Sabotage-Probe: fehlende Dunkel-Rolle muss auffallen.
    kaputt2 = json.loads(json.dumps(data))
    kaputt2["figma"]["semantic"]["dark"].pop("focus")
    try:
        validate(kaputt2, rules)
    except ValueError as exc:
        assert "Semantik-Rollen" in str(exc), exc
    else:
        raise AssertionError("fehlende Dunkel-Rolle blieb unentdeckt")

    # 8) Schreiben: alle Artefakte liegen danach wirklich da.
    with tempfile.TemporaryDirectory() as tmp:
        write_outputs(Path(tmp), first)
        # GENERATED beschreibt den Zielordner; das Manifest entsteht erst
        # danach aus allen Artefakten und ist deshalb keine Render-Ausgabe.
        assert all((Path(tmp) / n).exists() for n in GENERATED if n != "handoff-manifest.json")
        write_outputs(Path(tmp) / "plugin", {"code.js": code})
        assert (Path(tmp) / "plugin/code.js").exists()

    print("✅ Design-Handoff-Selbsttest bestanden.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="committete Artefakte auf Drift prüfen")
    mode.add_argument("--selftest", action="store_true", help="Generator und Verträge prüfen")
    args = parser.parse_args()

    if args.selftest:
        selftest()
        return 0

    data = load_yaml(SOURCE)
    rules = load_yaml(RULES)
    validate(data, rules)
    outputs = render(data, rules)
    plugins = {"code.js": plugin_code(data)}
    outputs["handoff-manifest.json"] = manifest(data, outputs, plugins)

    if args.check:
        drift = check_outputs(outputs)
        drift += check_outputs(plugins, PLUGIN_OUT)
        if drift:
            print("❌ Figma-/Relume-Handoff hat Drift:\n- " + "\n- ".join(drift))
            print("Beheben: python3 scripts/design_handoff.py")
            return 1
        print("✅ Figma-/Relume-Handoff ist aktuell und regelkonform.")
        return 0

    write_outputs(OUT, outputs)
    write_outputs(PLUGIN_OUT, plugins)
    print(
        f"✅ {len(outputs)} Handoff-Artefakte nach {OUT.relative_to(ROOT)}/ und "
        f"{len(plugins)} Plugin-Datei nach {PLUGIN_OUT.relative_to(ROOT)}/ geschrieben.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        raise SystemExit(2)
