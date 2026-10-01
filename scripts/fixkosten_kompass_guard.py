#!/usr/bin/env python3
"""Produktvertrag für Franks Fixkosten-Kompass und Fixkosten-Cockpit.

Der Blog positioniert sich dauerhaft über einen eigenen Produktkern statt über
lose Spartipps: Franks Fixkosten-Kompass (4K-Prüfpfad) und das lokale
Fixkosten-Cockpit. Dieses Gate prüft die Quelle VOR dem Hugo-Build und die
veröffentlichte Wahrheit DANACH.

Aufruf:
  python3 scripts/fixkosten_kompass_guard.py --source-only
  python3 scripts/fixkosten_kompass_guard.py --public public
  python3 scripts/fixkosten_kompass_guard.py --selftest

K1 Datenvertrag: genau vier 4K-Schritte und sechs kuratierte Bereiche.
K2 Markenvertrag: Brand Brain und Produktdaten verwenden denselben Namen und
   dieselben vier Schritte; alle Ziele führen zu live Pillar-Seiten.
K3 Privatsphärevertrag: Das Tool besitzt kein form action, kein fetch/XHR und
   schreibt lokale Daten nur hinter der Opt-in-Logik.
K4 Quellverdrahtung: Cockpit, Kompass-Partial, Homepage und Navigation können
   nicht still auseinanderlaufen.
B1 Buildvertrag: /cockpit/ enthält ein echtes Formular ohne action, alle sechs
   Kategorien, die vier Schritte und das lokale JavaScript; Startseite und
   Navigation führen zum Produkt.

Das Tool repariert nie selbst. Ein Defekt stoppt den Deploy, statt die
Positionierung oder den Datenschutz still abzuschwächen.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
from html import unescape
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "fixkosten_kompass.yaml"
BRAIN_FILE = ROOT / "data" / "brand_brain.yaml"
COCKPIT_CONTENT = ROOT / "content" / "cockpit" / "index.md"
COCKPIT_SHORTCODE = ROOT / "layouts" / "shortcodes" / "fixkosten-cockpit.html"
KOMPASS_PARTIAL = ROOT / "layouts" / "_partials" / "fixkosten_kompass.html"
KOMPASS_DATA_PARTIAL = ROOT / "layouts" / "_partials" / "fixkosten_kompass_data.html"
HOME_PARTIAL = ROOT / "layouts" / "_partials" / "home_info.html"
HUGO_CONFIG = ROOT / "hugo.toml"
JS_FILE = ROOT / "static" / "premium" / "ff-fixkosten-cockpit.js"

EXPECTED_STAGE_IDS = ("kosten", "konditionen", "kuendigungsfenster", "kurs")
EXPECTED_STAGE_TITLES = ("Kosten sehen", "Konditionen rechnen", "Kündigungsfenster sichern", "Kurs halten")
EXPECTED_CATEGORY_IDS = ("energie", "internet", "versicherung", "konto", "budget", "mobilitaet")


def read_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"{path.relative_to(ROOT)} nicht lesbar: {exc}") from exc


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_data(data: Any, root: Path = ROOT) -> list[str]:
    findings: list[str] = []
    if not isinstance(data, dict):
        return ["K1: fixkosten_kompass.yaml ist kein YAML-Objekt"]

    for key in ("version", "name", "short_name", "positioning", "promise", "privacy_note", "stages", "categories"):
        if key not in data:
            findings.append(f"K1: Pflichtfeld {key!r} fehlt")
    for key in ("name", "short_name", "positioning", "promise", "privacy_note"):
        if key in data and not nonempty(data[key]):
            findings.append(f"K1: {key!r} braucht einen nichtleeren Text")

    stages = data.get("stages")
    if not isinstance(stages, list) or len(stages) != 4:
        findings.append("K1: Es müssen genau vier Kompass-Schritte existieren")
    else:
        ids = [stage.get("id") if isinstance(stage, dict) else None for stage in stages]
        titles = [stage.get("title") if isinstance(stage, dict) else None for stage in stages]
        if tuple(ids) != EXPECTED_STAGE_IDS:
            findings.append("K1: Die vier Schritte müssen in der festen 4K-Reihenfolge Kosten/Konditionen/Kündigungsfenster/Kurs stehen")
        if tuple(titles) != EXPECTED_STAGE_TITLES:
            findings.append("K1: Die vier Schritttitel des Fixkosten-Kompasses wurden verändert")
        for index, stage in enumerate(stages, 1):
            if not isinstance(stage, dict):
                findings.append(f"K1: Schritt {index} ist kein Objekt")
                continue
            for key in ("id", "number", "title", "kicker", "description", "action"):
                if not nonempty(stage.get(key)):
                    findings.append(f"K1: Schritt {index} braucht {key!r}")

    categories = data.get("categories")
    if not isinstance(categories, list) or len(categories) != 6:
        findings.append("K1: Es müssen genau sechs Cockpit-Bereiche existieren")
    else:
        ids = [category.get("id") if isinstance(category, dict) else None for category in categories]
        if tuple(ids) != EXPECTED_CATEGORY_IDS:
            findings.append("K1: Cockpit-Bereiche fehlen, sind doppelt oder haben eine andere Reihenfolge")
        for index, category in enumerate(categories, 1):
            if not isinstance(category, dict):
                findings.append(f"K1: Bereich {index} ist kein Objekt")
                continue
            for key in ("id", "label", "icon", "pillar", "pillar_label", "help"):
                if not nonempty(category.get(key)):
                    findings.append(f"K1: Bereich {index} braucht {key!r}")
            pillar = category.get("pillar")
            if nonempty(pillar):
                page = root / "content" / "pillar" / pillar / "index.md"
                if not page.is_file():
                    findings.append(f"K2: Bereich {category.get('id')!r} zeigt auf fehlenden Pillar {pillar!r}")
                elif re.search(r"(?m)^draft:\s*true\s*$", page.read_text(encoding="utf-8")):
                    findings.append(f"K2: Bereich {category.get('id')!r} zeigt auf einen Entwurf: {pillar!r}")
    return findings


def read_source(path: Path, findings: list[str], label: str) -> str:
    if not path.is_file():
        findings.append(f"K4: {label} fehlt: {path.relative_to(ROOT)}")
        return ""
    return path.read_text(encoding="utf-8")


def validate_source(root: Path = ROOT) -> list[str]:
    findings: list[str] = []
    try:
        data = read_yaml(root / "data" / "fixkosten_kompass.yaml")
    except ValueError as exc:
        return [str(exc)]
    findings.extend(validate_data(data, root))

    try:
        brain = read_yaml(root / "data" / "brand_brain.yaml")
    except ValueError as exc:
        findings.append(str(exc))
        brain = {}
    kompass = brain.get("frameworks", {}).get("fixkosten_kompass", {}) if isinstance(brain, dict) else {}
    if not isinstance(kompass, dict):
        findings.append("K2: Brand Brain enthält keinen Fixkosten-Kompass")
    else:
        for key in ("name", "short_name", "positioning", "steps", "editorial_rule"):
            if key not in kompass:
                findings.append(f"K2: Brand Brain: fixkosten_kompass.{key} fehlt")
        for key in ("name", "short_name", "positioning"):
            if key in kompass and kompass.get(key) != data.get(key):
                findings.append(f"K2: Brand Brain und Produktdaten driften bei {key!r}")
        brain_steps = kompass.get("steps", [])
        if not isinstance(brain_steps, list) or len(brain_steps) != 4:
            findings.append("K2: Brand Brain braucht exakt vier 4K-Schritte")
        else:
            for title, step in zip(EXPECTED_STAGE_TITLES, brain_steps):
                if title not in str(step):
                    findings.append(f"K2: Brand-Brain-Schritt enthält {title!r} nicht")

    cockpit_content = read_source(root / "content" / "cockpit" / "index.md", findings, "Cockpit-Seite")
    if cockpit_content:
        for shortcode in ("{{< fixkosten-cockpit >}}", "{{< fixkosten-kompass >}}"):
            if shortcode not in cockpit_content:
                findings.append(f"K4: Cockpit-Seite bindet {shortcode!r} nicht ein")

    shortcode = read_source(root / "layouts" / "shortcodes" / "fixkosten-cockpit.html", findings, "Cockpit-Shortcode")
    partial = read_source(root / "layouts" / "_partials" / "fixkosten_kompass.html", findings, "Kompass-Partial")
    data_partial = read_source(root / "layouts" / "_partials" / "fixkosten_kompass_data.html", findings, "Kompass-Daten-Partial")
    home = read_source(root / "layouts" / "_partials" / "home_info.html", findings, "Startseiten-Partial")
    config = read_source(root / "hugo.toml", findings, "Hugo-Konfiguration")
    script = read_source(root / "static" / "premium" / "ff-fixkosten-cockpit.js", findings, "Cockpit-Skript")

    if shortcode:
        for marker in ("fixkosten_kompass_data.html", "data-ff-fixkosten-cockpit", "data-ff-cockpit-remember", "data-ff-cockpit-result", "ff-fixkosten-cockpit.js"):
            if marker not in shortcode:
                findings.append(f"K4: Cockpit-Shortcode enthält {marker!r} nicht")
        if re.search(r"<form\b[^>]*\baction\s*=", shortcode, re.I):
            findings.append("K3: Das Cockpit-Formular darf kein action-Attribut besitzen")
    if partial:
        for marker in ("fixkosten_kompass_data.html", "data-ff-fixkosten-kompass", "ff-kompass__steps"):
            if marker not in partial:
                findings.append(f"K4: Kompass-Partial enthält {marker!r} nicht")
    if data_partial and not all(marker in data_partial for marker in ("os.ReadFile", "data/fixkosten_kompass.yaml", "transform.Unmarshal")):
        findings.append("K4: Kompass-Daten-Partial lädt die kuratierte YAML-Datei nicht gezielt")
    if home and 'partial "fixkosten_kompass.html"' not in home:
        findings.append("K4: Startseite bindet den Fixkosten-Kompass nicht ein")
    if config and not re.search(r'identifier\s*=\s*"cockpit"[\s\S]{0,160}url\s*=\s*"/cockpit/"', config):
        findings.append("K4: Hauptnavigation verlinkt /cockpit/ nicht")

    if script:
        forbidden = {
            r"\bfetch\s*\(": "fetch",
            r"\bXMLHttpRequest\b": "XMLHttpRequest",
            r"\.innerHTML\s*=": "innerHTML-Zuweisung",
            r"document\.cookie": "Cookie-Zugriff",
        }
        for pattern, label in forbidden.items():
            if re.search(pattern, script):
                findings.append(f"K3: Cockpit-Skript darf keinen {label}-Pfad enthalten")
        for marker in ("STORAGE_KEY", "remember.checked", "safeStorageRemove", "FFFixkostenCockpitLogik"):
            if marker not in script:
                findings.append(f"K3: Opt-in-/Testvertrag im Cockpit-Skript fehlt: {marker!r}")
    return findings


def public_path(public: Path, url: str, base_path: str = "/") -> Path | None:
    base = "/" + base_path.strip("/") + "/" if base_path.strip("/") else "/"
    if not url.startswith(base):
        return None
    rest = url[len(base):].split("?", 1)[0].split("#", 1)[0].strip("/")
    candidate = (public / rest / "index.html").resolve()
    try:
        candidate.relative_to(public.resolve())
    except ValueError:
        return None
    return candidate


def validate_build(public: Path, data: dict[str, Any], base_path: str = "/") -> list[str]:
    findings: list[str] = []
    cockpit_file = public_path(public, (base_path.rstrip("/") or "") + "/cockpit/", base_path)
    home_file = public / "index.html"
    if not cockpit_file or not cockpit_file.is_file():
        return ["B1: Gebaute Cockpit-Seite /cockpit/ fehlt"]
    cockpit = cockpit_file.read_text(encoding="utf-8")
    # Der minifizierte Hugo-Build escaped deutsche Ampersands als &amp;.
    # Textverträge prüfen deshalb die lesbare HTML-Textrepräsentation,
    # nicht das zufällige Entity-Encoding des Ausgabemodus.
    cockpit_text = unescape(cockpit)
    if not home_file.is_file():
        findings.append("B1: Gebaute Startseite fehlt")
        home = ""
    else:
        home = home_file.read_text(encoding="utf-8")

    if len(re.findall(r"\bdata-ff-fixkosten-cockpit\b", cockpit)) != 1:
        findings.append("B1: /cockpit/ braucht genau eine Cockpit-Komponente")
    if re.search(r"<form\b[^>]*\baction\s*=", cockpit, re.I):
        findings.append("B1: Das gebaute Cockpit-Formular besitzt unerlaubt ein action-Attribut")
    if "premium/ff-fixkosten-cockpit.js" not in cockpit:
        findings.append("B1: /cockpit/ bindet das lokale Cockpit-Skript nicht ein")
    for stage in data.get("stages", []):
        if nonempty(stage.get("title")) and stage["title"] not in cockpit_text:
            findings.append(f"B1: Kompass-Schritt {stage['title']!r} fehlt im Build")
    for category in data.get("categories", []):
        if nonempty(category.get("label")) and category["label"] not in cockpit_text:
            findings.append(f"B1: Cockpit-Bereich {category['label']!r} fehlt im Build")
        pillar = category.get("pillar")
        if nonempty(pillar):
            target = public_path(public, (base_path.rstrip("/") or "") + f"/pillar/{pillar}/", base_path)
            if not target or not target.is_file():
                findings.append(f"B1: Cockpit-Ziel für {category.get('label')!r} fehlt im Build")
    if "data-ff-fixkosten-kompass" not in home:
        findings.append("B1: Startseite enthält den Fixkosten-Kompass nicht")
    cockpit_link_rx = re.compile(r'''href=(?:["'])?[^\s>"']*cockpit/''')
    if not cockpit_link_rx.search(home):
        findings.append("B1: Startseite verlinkt das Fixkosten-Cockpit nicht")
    if not cockpit_link_rx.search(cockpit):
        findings.append("B1: Die gebaute Cockpit-Seite ist nicht kanonisch verlinkbar")
    return findings


def selftest() -> list[str]:
    """Sabotageproben gegen die Kernregeln – keine Dateien werden verändert."""
    try:
        data = read_yaml(DATA_FILE)
    except ValueError as exc:
        return [f"Selbsttest kann Produktdaten nicht laden: {exc}"]
    errors: list[str] = []
    if validate_data(data):
        errors.append("Positivprobe der Produktdaten ist nicht grün")
    broken = copy.deepcopy(data)
    broken["stages"].pop()
    if not validate_data(broken):
        errors.append("Selbsttest: fehlender 4K-Schritt wurde nicht erkannt")
    broken = copy.deepcopy(data)
    broken["categories"][0]["pillar"] = "gibt-es-nicht"
    if not validate_data(broken):
        errors.append("Selbsttest: fehlendes Pillar-Ziel wurde nicht erkannt")
    if not re.search(r"\bfetch\s*\(", "fetch('/unzulässig')"):
        errors.append("Selbsttest: Netz-Muster ist defekt")
    if public_path(Path("/tmp/public"), "/cockpit/") != Path("/tmp/public/cockpit/index.html"):
        errors.append("Selbsttest: sichere Public-Pfad-Auflösung ist defekt")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-only", action="store_true", help="nur K1–K4 gegen den Quellbaum")
    parser.add_argument("--public", type=Path, help="zusätzlich B1 gegen das Hugo-Ausgabeverzeichnis")
    parser.add_argument("--base-path", default="/", help="Basis-Pfad eines Subdirectory-Builds")
    parser.add_argument("--selftest", action="store_true", help="Sabotageproben ausführen")
    parser.add_argument("--json", action="store_true", help="Befunde als JSON ausgeben")
    args = parser.parse_args(argv)

    findings: list[str] = []
    if args.selftest:
        findings.extend("SELFTEST: " + item for item in selftest())
    if not args.selftest or args.source_only or args.public:
        findings.extend(validate_source())
    if args.public:
        try:
            data = read_yaml(DATA_FILE)
        except ValueError as exc:
            findings.append(str(exc))
        else:
            findings.extend(validate_build(args.public, data, args.base_path))

    if args.json:
        print(json.dumps({"ok": not findings, "findings": findings}, ensure_ascii=False, indent=2))
    elif findings:
        print("🛑 FIXKOSTEN-KOMPASS-GATE: Befunde")
        for finding in findings:
            print("  - " + finding)
    else:
        scope = "Selbsttest + Quelle" if args.selftest else "Quelle"
        if args.public:
            scope += " + Build"
        print(f"✅ FIXKOSTEN-KOMPASS-GATE bestanden ({scope}).")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
