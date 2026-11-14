#!/usr/bin/env python3
"""KI-Cover-Inventar und fassungsgebundenes Veröffentlichungs-Gate.

Unbekannt ist weder KI noch menschlich. Das Gate validiert nur ausdrücklich
als KI deklariertes Bildmaterial; es bestätigt keine rechtliche Konformität.
Aufruf: python3 scripts/ki_cover_provenienz.py [--gate] [--json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def content_cover(p: Path):
    text = p.read_text(encoding="utf-8")
    if text.startswith(("---\n", "+++\n")):
        fence = text[:3]
        end = re.search(r"(?m)^" + re.escape(fence) + r"[ \t]*\r?$", text[4:])
        if not end:
            raise ValueError(f"{p}: Frontmatter nicht abgeschlossen")
        raw = text[4:4 + end.start()]
        fm = yaml.safe_load(raw) if fence == "---" else tomllib.loads(raw)
    elif text.startswith("{"):
        fm, _ = json.JSONDecoder().raw_decode(text)
    else:
        return None
    fm = fm or {}
    if not isinstance(fm, dict):
        raise ValueError(f"{p}: Frontmatter ist kein Mapping")
    cover = fm.get("cover")
    if cover is None:
        return None
    if not isinstance(cover, dict):
        raise ValueError(f"{p}: cover ist kein Mapping")
    return fm, cover


def local_cover(root: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or any(c in name for c in ("?", "#", "\\")) or "://" in name:
        raise ValueError("KI-Cover muss eine lokale statische Originaldatei ohne Query sein")
    base = (root / "static").resolve()
    target = (base / name.lstrip("/")).resolve()
    if not target.is_relative_to(base) or target == base:
        raise ValueError("Bildpfad außerhalb von static")
    return target


def pruefe_ki_cover(root: Path, cover: dict) -> tuple[Path, str]:
    """Fassungsgebundenen Nachweis für EIN deklariertes Original prüfen.

    Auch Social-Publisher nutzen dieselbe Prüfung an ihrer Sendegrenze;
    ein bloßes `deepfake: false` ersetzt Hash, Quelle und Datum nicht.
    """
    path = local_cover(root, cover.get("image"))
    if not path.is_file():
        raise ValueError("Originaldatei fehlt")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    evidence = cover.get("ki_pruefung")
    if not isinstance(evidence, dict):
        raise ValueError("cover.ki_pruefung mit sha256, quelle, geprueft_am und deepfake fehlt")
    if evidence.get("sha256") != sha:
        raise ValueError("sha256 stimmt nicht mit Originaldatei überein")
    if not isinstance(evidence.get("quelle"), str) or not evidence["quelle"].strip():
        raise ValueError("konkreter Herkunftsnachweis fehlt")
    try:
        date = dt.date.fromisoformat(str(evidence.get("geprueft_am", "")))
    except ValueError:
        raise ValueError("geprueft_am muss ein ISO-Datum sein") from None
    if date > dt.date.today():
        raise ValueError("geprueft_am liegt in der Zukunft")
    if type(evidence.get("deepfake")) is not bool:
        raise ValueError("Deepfake-Einzelfallprüfung (true/false) fehlt")
    if evidence["deepfake"]:
        raise ValueError("Deepfake nicht freigegeben: Social-, OG- und sonstige Ausspielwege gesondert absichern")
    return path, sha


def collect(root: Path = ROOT):
    result = []
    for p in sorted((root / "content").rglob("*.md")):
        parsed = content_cover(p)
        if not parsed:
            continue
        fm, cover = parsed
        if not cover.get("image") and "ai_generated" not in cover:
            continue
        result.append((p, fm, cover))
    return result


def protected_paths(root: Path = ROOT) -> set[Path]:
    """Schützt alle deklarierten Originale, einschließlich Entwürfen und Aliases."""
    paths = set()
    for p, _, cover in collect(root):
        value = cover.get("ai_generated")
        if value is not None and type(value) is not bool:
            raise ValueError(f"{p}: cover.ai_generated muss true oder false sein")
        if value is True:
            paths.add(local_cover(root, cover.get("image")))
    return paths


def audit(root: Path = ROOT):
    records, errors = [], []
    covers = collect(root)
    declared = {}
    # Dieselbe Datei darf nicht auf einer anderen Seite ohne Hinweis oder
    # über responsive Varianten ausgespielt werden (auch bei Pfad-Aliases).
    for p, _, cover in covers:
        if cover.get("ai_generated") is True:
            try:
                declared[local_cover(root, cover.get("image"))] = p
            except ValueError:
                pass  # audit meldet den fehlerhaften Pfad unten
    for p, fm, cover in covers:
        rel = p.relative_to(root).as_posix()
        ai = cover.get("ai_generated")
        rec = {"content": rel, "image": cover.get("image"), "draft": fm.get("draft") is True,
               "herkunft": "ki_deklariert" if ai is True else "nicht_belegt"}
        records.append(rec)
        if ai is not None and type(ai) is not bool:
            errors.append(f"{rel}: cover.ai_generated muss true oder false sein")
            continue
        if ai is not True:
            try:
                path = local_cover(root, cover.get("image"))
            except ValueError:
                pass  # unbekannte/externe Cover sind kein KI-Herkunftsnachweis
            else:
                if path in declared:
                    errors.append(f"{rel}: dieselbe Datei ist in {declared[path].relative_to(root).as_posix()} als KI-Cover deklariert; auch hier Kennzeichnung und Prüfung ergänzen")
            continue
        try:
            _, rec["sha256"] = pruefe_ki_cover(root, cover)
        except (OSError, ValueError) as exc:
            errors.append(f"{rel}: {exc}")
    return records, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        records, errors = audit()
    except (OSError, ValueError, yaml.YAMLError, tomllib.TOMLDecodeError) as exc:
        print(f"KI-Cover-Inventar nicht lesbar: {exc}")
        return 2
    result = {"cover": records, "fehler": errors}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"KI-Cover: {len(records)} Referenzen, {sum(r['herkunft'] == 'ki_deklariert' for r in records)} als KI deklariert, {len(errors)} Fehler; übrige Herkunft ungeklärt.")
        for error in errors:
            print(f"::error title=KI-Cover-Provenienz::{error}")
    return 1 if args.gate and errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
