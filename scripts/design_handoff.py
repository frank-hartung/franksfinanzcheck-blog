#!/usr/bin/env python3
"""Reproduzierbarer Figma-/Relume-Handoff aus dem Design-SSOT.

Erzeugt keine SaaS-Verbindung und veröffentlicht nichts. Das Skript baut
prüfbare Import-/Briefing-Artefakte, validiert sie gegen das Marken-Regelwerk
und verhindert Drift mit --check.
"""
from __future__ import annotations

import argparse
import hashlib
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
VERSION = 1
GENERATED = (
    "figma-tokens.tokens.json",
    "relume-project-brief.md",
    "component-inventory.md",
)


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
        if "dark" not in states:
            errors.append(f"Komponente {cid} dokumentiert keinen Dark-Mode-Zustand")

    pages = data.get("relume", {}).get("pages", [])
    paths: set[str] = set()
    for page in pages:
        path = page.get("path", "")
        if not path or path in paths:
            errors.append(f"Relume-Seitenpfad fehlt oder ist doppelt: {path!r}")
        paths.add(path)
        if not page.get("sections"):
            errors.append(f"Relume-Seite {path} hat keine Sections")

    if errors:
        raise ValueError("Design-Handoff ungültig:\n- " + "\n- ".join(errors))


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


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def render(data: dict[str, Any]) -> dict[str, str]:
    return {
        "figma-tokens.tokens.json": figma_tokens(data),
        "relume-project-brief.md": relume_brief(data),
        "component-inventory.md": component_inventory(data),
    }


def manifest(data: dict[str, Any], outputs: dict[str, str]) -> str:
    sources = [SOURCE, RULES, ROOT / "DESIGN.md", ROOT / "PRODUCT.md", ROOT / "scripts/design_handoff.py"]
    value = {
        "schema": VERSION,
        "stand": data["stand"],
        "generator": "scripts/design_handoff.py",
        "generator_version": VERSION,
        "sources": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources
        },
        "artifacts": {name: sha256(content) for name, content in sorted(outputs.items())},
    }
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def write_outputs(target: Path, outputs: dict[str, str]) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for name, content in outputs.items():
        (target / name).write_text(content, encoding="utf-8")


def check_outputs(expected: dict[str, str]) -> list[str]:
    drift: list[str] = []
    for name, content in expected.items():
        path = OUT / name
        if not path.exists():
            drift.append(f"fehlt: {path.relative_to(ROOT)}")
        elif path.read_text(encoding="utf-8") != content:
            drift.append(f"veraltet: {path.relative_to(ROOT)}")
    return drift


def selftest() -> None:
    data = load_yaml(SOURCE)
    rules = load_yaml(RULES)
    validate(data, rules)
    first = render(data)
    second = render(data)
    assert first == second, "Ausgabe ist nicht deterministisch"
    parsed = json.loads(first["figma-tokens.tokens.json"])
    assert len(parsed["$themes"]) == 2
    assert "Semantic/Dark" in parsed
    assert parsed["Primitives"]["spacing"]["8"]["value"] == "8px"
    assert parsed["Semantic/Light"]["color"]["heading"]["value"] == "{color.emerald}"
    with tempfile.TemporaryDirectory() as tmp:
        write_outputs(Path(tmp), first)
        assert all((Path(tmp) / name).exists() for name in GENERATED)
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
    outputs = render(data)
    outputs["handoff-manifest.json"] = manifest(data, outputs)

    if args.check:
        drift = check_outputs(outputs)
        if drift:
            print("❌ Figma-/Relume-Handoff hat Drift:\n- " + "\n- ".join(drift))
            print("Beheben: python3 scripts/design_handoff.py")
            return 1
        print("✅ Figma-/Relume-Handoff ist aktuell und regelkonform.")
        return 0

    write_outputs(OUT, outputs)
    print(f"✅ {len(outputs)} Handoff-Artefakte nach {OUT.relative_to(ROOT)}/ geschrieben.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        raise SystemExit(2)
