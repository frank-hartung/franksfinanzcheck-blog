#!/usr/bin/env python3
"""Whole, byte-bound reserve snapshots, never text-merged evidence (#634).

All reserve readers use the same strict JSON/candidate parser. Writers replace
complete snapshots atomically. The offline PR check validates bookkeeping and
READY source bytes/editorial structure, not the wall-clock age of a nightly
measurement; the production end gate still enforces the 36-hour limit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE_FILES = ("reserve-readiness.json", "reserve-custody.json",
               "reserve-quarantine.json")


def _unique_object(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"doppelter JSON-Schlüssel: {key}")
        result[key] = value
    return result


def _reject_constant(value: str):
    raise ValueError(f"ungültige JSON-Zahl: {value}")


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        _reject_constant(value)
    return number


def parse_object(text: str) -> dict:
    data = json.loads(text, object_pairs_hook=_unique_object,
                      parse_constant=_reject_constant, parse_float=_finite_float)
    if not isinstance(data, dict):
        raise ValueError("JSON-Wurzel ist kein Objekt")
    return data


def read_object(path: Path) -> dict:
    return parse_object(path.read_text(encoding="utf-8"))


def certificate_rows(data: dict) -> list[dict]:
    """A malformed row or repeated identity invalidates the whole snapshot.

    Legacy summary fields are not authority: readers count the list, and the
    PR check reports inconsistent summaries. A READY row must always carry a
    real SHA-256; absence is not an invitation to trust a flag.
    """
    rows = data.get("candidates")
    if not isinstance(rows, list):
        raise ValueError("Kandidatenliste fehlt oder ist ungültig")
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Kandidatenzeile ist kein Objekt")
        slug = row.get("slug")
        if (not isinstance(slug, str)
                or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", slug)):
            raise ValueError(f"ungültiger Kandidaten-Slug: {slug!r}")
        if slug in seen:
            raise ValueError(f"doppelter Kandidaten-Slug: {slug}")
        seen.add(slug)
        if type(row.get("ready")) is not bool:
            raise ValueError(f"{slug}: ready ist kein Boolean")
        digest = row.get("sha256")
        if row["ready"] or digest is not None:
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError(f"{slug}: SHA-256 fehlt oder ist ungültig")
    return rows


def check_memories(data_dir: Path) -> None:
    """Missing bootstrap history is allowed; corrupt history is never empty."""
    for name in STATE_FILES[1:]:
        try:
            data = read_object(data_dir / name)
            if any(not isinstance(row, dict) for row in data.values()):
                raise ValueError("Gedächtnis-Eintrag ist kein Objekt")
        except FileNotFoundError:
            continue
        except (OSError, ValueError) as exc:
            raise ValueError(f"{name}: {exc}") from exc


def read_certificate(path: Path) -> dict:
    data = read_object(path)
    certificate_rows(data)
    check_memories(path.parent)
    return data


def reserve_metadata(content: str) -> dict:
    """Use the existing F1–F7 guard before PyYAML's last-key-wins parser."""
    import fm_boundary_guard as fm
    import yaml

    content = content.replace("\r\n", "\n")  # validation only; never rewrite source bytes
    boundary, glue, _text, defects, duplicates = fm.inspect_text(content)
    if boundary or glue or defects or duplicates:
        raise ValueError("Frontmatter beschädigt (F1–F7; Grenze, YAML oder doppelte Schlüssel)")
    lines, _begin, _end = fm.split_fm(content)
    metadata = yaml.safe_load("\n".join(lines))
    if not isinstance(metadata, dict):
        raise ValueError("Frontmatter ist kein Mapping")
    return metadata


def candidate_problem(row: dict, posts_dir: Path) -> str | None:
    """Cheap source proof: exact bytes, valid metadata and actual pool ownership."""
    index = posts_dir / row["slug"] / "index.md"
    try:
        if not index.resolve().is_relative_to(posts_dir.resolve()):
            return "Entwurf liegt außerhalb des Reserve-Bestands"
        raw = index.read_bytes()
        if hashlib.sha256(raw).hexdigest() != row["sha256"]:
            return "SHA-256 passt nicht mehr zum Entwurf; Nachzertifizierung nötig"
        metadata = reserve_metadata(raw.decode("utf-8"))
        if metadata.get("draft") is not True or metadata.get("reserve") is not True:
            return "kein aktueller Reserve-Entwurf (draft: true + reserve: true fehlen)"
        if any(metadata.get(key) for key in
               ("reserve_blocked", "reserve_retired", "reserve_published")):
            return "Kandidat ist blockiert, zurückgezogen oder bereits veröffentlicht"
    except (OSError, ValueError, ImportError) as exc:
        return f"Entwurf nicht prüfbar: {exc}"
    return None


def verified_rows(data: dict, posts_dir: Path) -> list[dict]:
    """Return a diagnostic view, never modify the certificate or source files."""
    result = []
    for row in certificate_rows(data):
        checked = dict(row)
        if row["ready"]:
            problem = candidate_problem(row, posts_dir)
            if problem:
                checked.update(ready=False, reason=f"Zertifikats-Integrität: {problem}")
        result.append(checked)
    return result


def write_object(path: Path, data: dict, *, sort_keys: bool = False) -> None:
    """Write, fsync and read back on the same filesystem before atomic replace.

    On validation/write/readback/rename failure the old snapshot survives and
    the temporary file is removed. Never leave truncated evidence in Git.
    """
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=sort_keys,
                      allow_nan=False) + "\n"
    if parse_object(text) != data:
        raise ValueError("JSON-Rückleseprobe stimmt nicht mit dem Zustand überein")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                         dir=path.parent, prefix=f".{path.name}.",
                                         suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        if read_object(temporary) != data:
            raise ValueError("JSON-Rückleseprobe der geschriebenen Datei fehlgeschlagen")
        mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
        temporary.chmod(mode)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def snapshot_findings(root: Path = ROOT) -> list[str]:
    """Offline PR proof of the complete snapshot and every claimed READY draft."""
    findings = []
    for name in STATE_FILES:
        try:
            read_object(root / "data" / name)
        except (OSError, ValueError) as exc:
            findings.append(f"{name}: {exc}")
    try:
        data = read_certificate(root / "data" / STATE_FILES[0])
    except (OSError, ValueError) as exc:
        findings.append(f"Reserve-Zertifikat: {exc}")
        return findings

    rows = data["candidates"]
    for key, value in (("ready", sum(r["ready"] for r in rows)),
                       ("pool_size", len(rows))):
        if type(data.get(key)) is not int or data[key] != value:
            findings.append(f"Reserve-Zertifikat: {key} stimmt nicht mit der Kandidatenliste überein")
    from reserve_gate import cert_age_hours
    if cert_age_hours(root / "data" / STATE_FILES[0]) is None:
        findings.append("Reserve-Zertifikat: generated_at fehlt oder ist ungültig")

    import reserve_readiness as readiness
    posts = root / "content" / "posts"
    for row in rows:
        if not row["ready"]:
            continue
        problem = candidate_problem(row, posts)
        if problem:
            findings.append(f"{row['slug']}: {problem}")
            continue
        index = posts / row["slug"] / "index.md"
        for finding in readiness.reserve_editorial_findings(
                index, index.read_bytes().decode("utf-8")):
            findings.append(f"{row['slug']}: {finding}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Offline-Snapshot- und Redaktionsprüfung")
    parser.parse_args()
    findings = snapshot_findings()
    if findings:
        print("🛑 Reserve-Snapshot beschädigt oder unbelegt:")
        for finding in findings:
            print(f"   - {finding}")
        print("   Ganze Zustandsfassung wiederherstellen; danach reserve_readiness.py ausführen.")
        return 1
    print("✅ Reserve-Snapshot vollständig: eindeutiges JSON, echte READY-Bytes und Redaktionsvertrag.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
