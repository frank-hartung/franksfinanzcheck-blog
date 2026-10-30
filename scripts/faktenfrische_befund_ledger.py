#!/usr/bin/env python3
"""Dauerhafte Fachbefunde der Faktenfrische (#912).

Ein erfolgreicher Faktencheck darf ein Alter zurücksetzen, aber keinen
inhaltlichen Befund löschen. Befunde bleiben bis zu einer dokumentierten
menschlichen Entscheidung offen. Der Fassungs-Hash bindet die Entscheidung an
die tatsächlich geprüften Aussagen (Titel, Beschreibung, Kurzantwort, Quellen,
Text); eine spätere Textänderung öffnet sie erneut.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data" / "faktenfrische_queue.json"
ENTSCHEIDUNGEN = ROOT / "data" / "faktenfrische_entscheidungen.yaml"


class LedgerFehler(ValueError):
    """Ungültiger Beweisstand; niemals als leere Befundliste behandeln."""


def body_hash(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def pruef_hash(art: dict) -> str:
    """Fassungs-Hash über Text UND die mitgeprüften Aussageflächen."""
    fm = yaml.safe_load(art.get("fm", "")) or {}
    if not isinstance(fm, dict):
        raise LedgerFehler("Frontmatter ist kein Mapping")
    material = {}
    material["title"] = fm.get("title", "")
    material["description"] = fm.get("description", "")
    material["kurzantwort"] = fm.get("kurzantwort", "")
    material["quellen"] = fm.get("quellen") or []
    material["body"] = art.get("body", "")
    payload = json.dumps(material, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def befund_id(slug: str, befund: dict) -> str:
    text = "\x1f".join((slug, str(befund.get("typ", "befund")),
                         str(befund.get("text", "")).strip()))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:20]


def _json_object(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LedgerFehler(f"{path.name} nicht lesbar: {exc}") from exc
    if not isinstance(data, dict):
        raise LedgerFehler(f"{path.name}: Objekt erwartet")
    return data


def eintraege_aus_queue(data: dict) -> list[dict]:
    """Neues Ledger plus einmalige Migration der bisherigen Lauf-Befunde."""
    result = []
    entries = data.get("fachbefunde", [])
    if not isinstance(entries, list):
        raise LedgerFehler("fachbefunde ist keine Liste")
    for entry in entries:
        if not isinstance(entry, dict) or not all(
                isinstance(entry.get(k), str) and entry[k].strip()
                for k in ("id", "slug", "fassung_sha256", "typ", "text")):
            raise LedgerFehler("Unvollständiger Ledger-Eintrag")
        result.append(dict(entry))
    runs = data.get("laeufe", [])
    if not isinstance(runs, list):
        raise LedgerFehler("laeufe ist keine Liste")
    for run in runs:
        if not isinstance(run, dict) or not isinstance(run.get("slug"), str):
            raise LedgerFehler("Unvollständiger Lauf")
        findings = run.get("befunde", [])
        if not isinstance(findings, list):
            raise LedgerFehler("Lauf-Befunde sind keine Liste")
        for finding in findings:
            if not isinstance(finding, dict) or not isinstance(finding.get("text"), str):
                raise LedgerFehler("Unvollständiger Fachbefund")
            slug = run["slug"]
            result.append({"id": befund_id(slug, finding), "slug": slug,
                           "fassung_sha256": run.get("fassung_sha256", "legacy-unbekannt"),
                           "typ": str(finding.get("typ", "befund")),
                           "text": finding["text"], "beleg": finding.get("beleg", ""),
                           "zuletzt_gesehen": data.get("erzeugt", "")})
    return result


def zusammenfuehren(alt: dict, neu: list[dict]) -> list[dict]:
    """Deduplizieren, niemals still schließen; neuester Belegstand gewinnt."""
    merged: dict[tuple[str, str], dict] = {}
    for entry in eintraege_aus_queue(alt) + list(neu):
        key = (entry["slug"], entry["id"])
        previous = merged.get(key, {})
        candidate = {**previous, **entry}
        if re.fullmatch(r"[0-9a-f]{64}", previous.get("fassung_sha256", "")) and not re.fullmatch(r"[0-9a-f]{64}", entry.get("fassung_sha256", "")):
            candidate["fassung_sha256"] = previous["fassung_sha256"]
        merged[key] = candidate
    return [merged[key] for key in sorted(merged)]


def entscheidungen_laden(path: Path = ENTSCHEIDUNGEN) -> dict[tuple[str, str], dict]:
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise LedgerFehler(f"Entscheidungen nicht lesbar: {exc}") from exc
    entries = data.get("entscheidungen", []) if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise LedgerFehler("Entscheidungen müssen eine Liste sein")
    result = {}
    for entry in entries:
        if not isinstance(entry, dict) or not all(
                isinstance(entry.get(k), str) and entry[k].strip()
                for k in ("slug", "befund_id", "fassung_sha256", "entschieden_von", "begruendung")):
            raise LedgerFehler("Entscheidung braucht Slug, Befund, Fassungs-Hash, Person und Begründung")
        if not re.fullmatch(r"[0-9a-f]{64}", entry["fassung_sha256"]):
            raise LedgerFehler("Entscheidung braucht einen echten SHA-256 der geprüften Fassung")
        key = (entry["slug"], entry["befund_id"])
        if key in result:
            raise LedgerFehler(f"Doppelte Entscheidung: {key}")
        result[key] = entry
    return result


def offene_eintraege(entries: list[dict], decisions: dict) -> list[dict]:
    result = []
    for entry in entries:
        decision = decisions.get((entry["slug"], entry["id"]))
        if decision and decision["fassung_sha256"] == entry["fassung_sha256"]:
            continue
        result.append(entry)
    return result


def offene_befunde(queue_path: Path = QUEUE,
                   decisions_path: Path = ENTSCHEIDUNGEN) -> list[dict]:
    return offene_eintraege(zusammenfuehren(_json_object(queue_path), []),
                            entscheidungen_laden(decisions_path))


def selftest() -> int:
    finding = {"typ": "praezision", "text": "Unbelegte Preisangabe"}
    entry = {"id": befund_id("a", finding), "slug": "a", "fassung_sha256": body_hash("Fassung A"),
             **finding, "beleg": ""}
    assert zusammenfuehren({"fachbefunde": [entry]}, [entry]) == [entry]
    assert zusammenfuehren({"fachbefunde": [entry]}, []) == [entry]
    changed = dict(entry, fassung_sha256=body_hash("Fassung B"))
    assert zusammenfuehren({"fachbefunde": [entry]}, [changed]) == [changed]
    try:
        eintraege_aus_queue({"fachbefunde": [{}]})
    except LedgerFehler:
        pass
    else:
        raise AssertionError("Ungültiges Ledger wurde akzeptiert")
    print("✅ Faktenfrische-Befundledger: Deduplizierung, Bestandsschutz, Fassungsbindung, fail-closed.")
    return 0


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--fassung", help="SHA-256 einer Artikel-Index-Datei für die Schließakte")
    args = parser.parse_args()
    if args.selftest:
        raise SystemExit(selftest())
    if args.fassung:
        import faktenfrische as ff
        article = ff.lade_artikel(args.fassung)
        if article is None:
            parser.error("Artikel nicht lesbar")
        print(pruef_hash(article))
        raise SystemExit(0)
    print(json.dumps(offene_befunde(), ensure_ascii=False, indent=2))

