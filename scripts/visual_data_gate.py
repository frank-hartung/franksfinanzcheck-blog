#!/usr/bin/env python3
"""Fail-closed gate for versioned chart datasets and shortcode references."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "datasets"
CONTENT_DIR = ROOT / "content"
REQUIRED = {
    "schema_version", "id", "title", "description", "owner", "status",
    "chart_type", "unit", "x_label", "y_label", "updated",
    "update_frequency", "sources", "methodology", "changelog", "license", "values",
}
ALLOWED_STATUS = {"beobachtung", "modellrechnung", "prognose"}
ALLOWED_CHARTS = {"bar", "line"}
ALLOWED_FREQUENCIES = {
    "ereignisbasiert", "woechentlich", "monatlich", "quartalsweise", "jaehrlich", "statisch"
}
SHORTCODE_RE = re.compile(r'\{\{[<%]\s*chart\s+[^}]*?dataset=["\']([^"\']+)["\']', re.I)


def load_yaml(path: Path):
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit("PyYAML fehlt: pip install pyyaml") from exc
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # YAML parser gives useful location
        raise ValueError(f"YAML nicht lesbar: {exc}") from exc


def iso_date(value, field: str, errors: list[str]) -> dt.date | None:
    if not isinstance(value, str):
        errors.append(f"{field}: ISO-Datum als String erwartet")
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        errors.append(f"{field}: ungültiges ISO-Datum {value!r}")
        return None


def valid_url(value) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate_dataset(path: Path, doc) -> tuple[list[str], str | None]:
    errors: list[str] = []
    if not isinstance(doc, dict):
        return ["Wurzel muss ein Mapping sein"], None
    missing = sorted(REQUIRED - set(doc))
    if missing:
        errors.append("Pflichtfelder fehlen: " + ", ".join(missing))
    dataset_id = doc.get("id") if isinstance(doc.get("id"), str) else None
    if dataset_id and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", dataset_id):
        errors.append("id: nur Kleinbuchstaben, Ziffern und einzelne Bindestriche")
    if doc.get("schema_version") != "1.0":
        errors.append("schema_version: erwartet '1.0'")
    if doc.get("status") not in ALLOWED_STATUS:
        errors.append(f"status: erlaubt sind {sorted(ALLOWED_STATUS)}")
    if doc.get("chart_type") not in ALLOWED_CHARTS:
        errors.append(f"chart_type: erlaubt sind {sorted(ALLOWED_CHARTS)}")
    if doc.get("update_frequency") not in ALLOWED_FREQUENCIES:
        errors.append(f"update_frequency: erlaubt sind {sorted(ALLOWED_FREQUENCIES)}")
    for field in ("title", "description", "owner", "unit", "x_label", "y_label", "license"):
        if not isinstance(doc.get(field), str) or not doc.get(field, "").strip():
            errors.append(f"{field}: nichtleerer Text erforderlich")
    iso_date(doc.get("updated"), "updated", errors)

    sources = doc.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("sources: mindestens eine Quelle erforderlich")
    else:
        for i, source in enumerate(sources):
            prefix = f"sources[{i}]"
            if not isinstance(source, dict):
                errors.append(f"{prefix}: Mapping erwartet")
                continue
            for field in ("title", "publisher"):
                if not isinstance(source.get(field), str) or not source.get(field, "").strip():
                    errors.append(f"{prefix}.{field}: nichtleerer Text erforderlich")
            if not valid_url(source.get("url")):
                errors.append(f"{prefix}.url: absolute HTTP(S)-URL erforderlich")
            iso_date(source.get("accessed"), f"{prefix}.accessed", errors)

    method = doc.get("methodology")
    if not isinstance(method, dict):
        errors.append("methodology: Mapping erwartet")
    else:
        for field in ("summary", "version"):
            if not isinstance(method.get(field), str) or not method.get(field, "").strip():
                errors.append(f"methodology.{field}: nichtleerer Text erforderlich")
        if not valid_url(method.get("url")):
            errors.append("methodology.url: absolute HTTP(S)-URL erforderlich")
        if method.get("version") and not re.fullmatch(r"\d+\.\d+\.\d+", str(method["version"])):
            errors.append("methodology.version: semantische Version x.y.z erforderlich")

    changelog = doc.get("changelog")
    if not isinstance(changelog, list) or not changelog:
        errors.append("changelog: mindestens ein Eintrag erforderlich")
    else:
        for i, change in enumerate(changelog):
            prefix = f"changelog[{i}]"
            if not isinstance(change, dict):
                errors.append(f"{prefix}: Mapping erwartet")
                continue
            iso_date(change.get("date"), f"{prefix}.date", errors)
            if not isinstance(change.get("note"), str) or not change.get("note", "").strip():
                errors.append(f"{prefix}.note: nichtleerer Text erforderlich")

    values = doc.get("values")
    if not isinstance(values, list) or len(values) < 2:
        errors.append("values: mindestens zwei Datenpunkte erforderlich")
    else:
        labels: set[str] = set()
        for i, point in enumerate(values):
            prefix = f"values[{i}]"
            if not isinstance(point, dict):
                errors.append(f"{prefix}: Mapping erwartet")
                continue
            label = point.get("label")
            if not isinstance(label, str) or not label.strip():
                errors.append(f"{prefix}.label: nichtleerer Text erforderlich")
            elif label in labels:
                errors.append(f"{prefix}.label: doppeltes Label {label!r}")
            else:
                labels.add(label)
            value = point.get("value")
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                errors.append(f"{prefix}.value: endliche Zahl erforderlich")
            elif value < 0:
                errors.append(f"{prefix}.value: Phase 1 erlaubt keine negativen Werte")
    return errors, dataset_id


def run() -> dict:
    result = {"datasets": 0, "references": 0, "errors": [], "warnings": []}
    files = sorted(p for p in DATA_DIR.glob("*.yaml") if p.name != "schema.yaml")
    if not files:
        result["errors"].append("Keine Datensätze unter data/datasets gefunden")
        return result
    known_keys: set[str] = set()
    ids: dict[str, str] = {}
    for path in files:
        try:
            doc = load_yaml(path)
            errors, dataset_id = validate_dataset(path, doc)
        except ValueError as exc:
            errors, dataset_id = [str(exc)], None
        result["datasets"] += 1
        key = path.stem
        known_keys.add(key)
        for error in errors:
            result["errors"].append(f"{path.relative_to(ROOT)}: {error}")
        if dataset_id:
            if dataset_id in ids:
                result["errors"].append(f"{path.relative_to(ROOT)}: id {dataset_id!r} bereits in {ids[dataset_id]}")
            ids[dataset_id] = str(path.relative_to(ROOT))

    used: set[str] = set()
    for path in CONTENT_DIR.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for key in SHORTCODE_RE.findall(text):
            result["references"] += 1
            used.add(key)
            if key not in known_keys:
                result["errors"].append(f"{path.relative_to(ROOT)}: unbekannter Chart-Datensatz {key!r}")
    for key in sorted(known_keys - used):
        result["warnings"].append(f"data/datasets/{key}.yaml ist noch in keinem Inhalt eingebunden")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Visual-Data-Gate: {result['datasets']} Datensätze, {result['references']} Einbindungen")
        for warning in result["warnings"]:
            print(f"WARN: {warning}")
        for error in result["errors"]:
            print(f"FEHLER: {error}")
        print("ERGEBNIS:", "BESTANDEN" if not result["errors"] else "NICHT BESTANDEN")
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
