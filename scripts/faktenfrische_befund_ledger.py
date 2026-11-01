#!/usr/bin/env python3
"""Dauerhafte Fachbefunde der Faktenfrische (#912, #984).

Ein erfolgreicher Faktencheck darf ein Alter zurücksetzen, aber keinen
inhaltlichen Befund löschen. Befunde bleiben bis zu einer dokumentierten
menschlichen Entscheidung offen. Der Fassungs-Hash bindet die Entscheidung an
die tatsächlich geprüften Aussagen (Titel, Beschreibung, Kurzantwort, Quellen,
Text); eine spätere Textänderung öffnet sie erneut.

NACHLESE (#984): Ein Lauf schreibt das Dossier vor seiner Bilanz. Bricht er
danach ab, liegen seine Befunde nur im Dossier. `--nachlese` liest die
Dossiers und ergänzt ausschließlich, was im Ledger fehlt – idempotent, ohne
eine Fassung zu erfinden und ohne je einen Befund zu schließen.
"""
from __future__ import annotations

import hashlib
import json
import re
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data" / "faktenfrische_queue.json"
ENTSCHEIDUNGEN = ROOT / "data" / "faktenfrische_entscheidungen.yaml"
DOSSIERS = ROOT / "data" / "research" / "artikel"


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


# ----------------------------------------------------------------------
# Nachlese: Was im Dossier belegt ist, darf nicht außerhalb des Ledgers enden
# ----------------------------------------------------------------------
#  WARUM (Vorgang WF-8F6F / #984, 31.10.2026)
#  Ein Lauf schreibt das Dossier VOR seiner Bilanz. Brach er danach ab, lagen
#  die Befunde nur noch in `data/research/artikel/<slug>.json` – für die
#  Redaktion unsichtbar, für Publish-Gate und Scorecard (F4) nicht messbar,
#  für die Maschine „nichts gefunden“. Genau das passierte bei „Kostenloses
#  Girokonto ohne Gebühren finden“: fünf belegte Lücken, kein Ledger-Eintrag.
#
#  Die Nachlese schließt diese Lücke strukturell: Sie liest die Dossiers und
#  ergänzt ausschließlich, was fehlt. Sie schließt NIE einen Befund, erfindet
#  keine Fassung (ohne echten SHA-256 wird der Befund nicht übernommen) und
#  ist idempotent – zweimal ausgeführt ändert sie nichts.

def dossier_eintraege(dossier_dir: Path = DOSSIERS) -> tuple[list[dict], list[str]]:
    """(Ledger-Einträge, übersprungene Dateien/Gründe) aus den Dossiers."""
    eintraege: list[dict] = []
    hinweise: list[str] = []
    if not Path(dossier_dir).is_dir():
        return eintraege, [f"{dossier_dir} fehlt"]
    for pfad in sorted(Path(dossier_dir).glob("*.json")):
        try:
            data = json.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            hinweise.append(f"{pfad.name}: nicht lesbar ({exc})")
            continue
        if not isinstance(data, dict):
            hinweise.append(f"{pfad.name}: kein Objekt")
            continue
        findings = data.get("befunde") or []
        if not isinstance(findings, list) or not findings:
            continue
        fassung = data.get("fassung_sha256")
        slug = data.get("slug") or pfad.stem
        if not isinstance(fassung, str) or not re.fullmatch(r"[0-9a-f]{64}", fassung):
            # Ohne echte Fassung wäre eine spätere Entscheidung nicht bindbar.
            hinweise.append(f"{pfad.name}: kein gültiger Fassungs-Hash – "
                            f"{len(findings)} Befund(e) nicht übernommen")
            continue
        for finding in findings:
            if not isinstance(finding, dict) or not isinstance(finding.get("text"), str) \
                    or not finding["text"].strip():
                hinweise.append(f"{pfad.name}: unvollständiger Befund")
                continue
            eintraege.append({
                "id": befund_id(str(slug), finding),
                "slug": str(slug),
                "fassung_sha256": fassung,
                "typ": str(finding.get("typ") or "befund")[:20],
                "text": finding["text"].strip()[:400],
                "beleg": str(finding.get("beleg") or ""),
                "zuletzt_gesehen": str(data.get("erzeugt") or ""),
                "herkunft": "dossier-nachlese",
            })
    return eintraege, hinweise


def nachlese(dossier_dir: Path = DOSSIERS,
             queue_path: Path = QUEUE) -> dict:
    """Welche belegten Dossier-Befunde fehlen im Ledger? (rein lesend)"""
    vorhanden = {(e["slug"], e["id"]) for e in zusammenfuehren(
        _json_object(queue_path), [])}
    alle, hinweise = dossier_eintraege(dossier_dir)
    fehlend = [e for e in alle if (e["slug"], e["id"]) not in vorhanden]
    return {"dossiers": len(list(Path(dossier_dir).glob("*.json")))
            if Path(dossier_dir).is_dir() else 0,
            "befunde_im_dossier": len(alle),
            "fehlend": fehlend,
            "hinweise": hinweise}


def nachlese_anwenden(dossier_dir: Path = DOSSIERS,
                      queue_path: Path = QUEUE) -> dict:
    """Ergänzt fehlende Dossier-Befunde im Ledger – idempotent, nur ergänzend."""
    ergebnis = nachlese(dossier_dir, queue_path)
    if not ergebnis["fehlend"]:
        return ergebnis
    queue = _json_object(queue_path)
    queue["fachbefunde"] = zusammenfuehren(queue, ergebnis["fehlend"])
    queue["nachlese"] = {"zeit": _jetzt(), "ergaenzt": len(ergebnis["fehlend"]),
                         "quelle": "data/research/artikel"}
    tmp = Path(str(queue_path) + ".tmp")
    try:
        tmp.write_text(json.dumps(queue, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        tmp.replace(queue_path)
    except OSError as exc:
        raise LedgerFehler(f"{Path(queue_path).name} nicht schreibbar: {exc}") from exc
    ergebnis["ergaenzt"] = len(ergebnis["fehlend"])
    return ergebnis


def _jetzt() -> str:
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


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
    with tempfile.TemporaryDirectory() as tmp:
        dossier_dir = Path(tmp) / "artikel"
        dossier_dir.mkdir()
        queue_path = Path(tmp) / "queue.json"
        fassung = body_hash("Fassung Dossier")
        finding = {"typ": "luecke", "text": "Mindestguthaben ohne Beleg", "beleg": ""}
        (dossier_dir / "seite.json").write_text(json.dumps({
            "slug": "seite", "erzeugt": "2026-10-31 10:34 UTC",
            "fassung_sha256": fassung, "befunde": [finding]}), encoding="utf-8")
        (dossier_dir / "ohne_hash.json").write_text(json.dumps({
            "slug": "alt", "befunde": [finding]}), encoding="utf-8")
        # (a) Die Nachlese findet den Befund und legt ihn ins Ledger.
        ergebnis = nachlese_anwenden(dossier_dir, queue_path)
        assert ergebnis["ergaenzt"] == 1, ergebnis
        assert any("ohne_hash.json" in h for h in ergebnis["hinweise"]), ergebnis
        eintraege = zusammenfuehren(_json_object(queue_path), [])
        assert len(eintraege) == 1 and eintraege[0]["fassung_sha256"] == fassung
        # (b) Zweimal ist einmal: idempotent, kein Duplikat, keine Schließung.
        assert nachlese_anwenden(dossier_dir, queue_path)["fehlend"] == []
        assert len(zusammenfuehren(_json_object(queue_path), [])) == 1
        # (c) Eine menschliche Entscheidung bleibt unberührt.
        decisions = Path(tmp) / "decisions.yaml"
        decisions.write_text(yaml.safe_dump({"entscheidungen": [{
            "slug": "seite", "befund_id": eintraege[0]["id"],
            "fassung_sha256": fassung, "entschieden_von": "Redaktion",
            "begruendung": "Mindestguthaben belegt"}]}), encoding="utf-8")
        assert offene_befunde(queue_path, decisions) == []

    print("✅ Faktenfrische-Befundledger: Deduplizierung, Bestandsschutz, "
          "Fassungsbindung, Nachlese, fail-closed.")
    return 0


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--fassung", help="SHA-256 einer Artikel-Index-Datei für die Schließakte")
    parser.add_argument("--nachlese", action="store_true",
                        help="Dossier-Befunde finden, die im Ledger fehlen")
    parser.add_argument("--apply", action="store_true",
                        help="mit --nachlese: fehlende Befunde ins Ledger ergänzen")
    args = parser.parse_args()
    if args.selftest:
        raise SystemExit(selftest())
    if args.nachlese:
        if args.apply:
            ergebnis = nachlese_anwenden()
            print(f"Nachlese: {ergebnis.get('ergaenzt', 0)} Befund(e) ergänzt "
                  f"aus {ergebnis['dossiers']} Dossier(s).")
        else:
            ergebnis = nachlese()
            print(f"Nachlese (Trockenlauf): {len(ergebnis['fehlend'])} von "
                  f"{ergebnis['befunde_im_dossier']} Dossier-Befund(en) fehlen im Ledger.")
            for eintrag in ergebnis["fehlend"]:
                print(f"  - {eintrag['slug']} · {eintrag['typ']}: {eintrag['text'][:110]}")
        for hinweis in ergebnis["hinweise"]:
            print(f"  Hinweis: {hinweis}")
        raise SystemExit(0)
    if args.fassung:
        import faktenfrische as ff
        article = ff.lade_artikel(args.fassung)
        if article is None:
            parser.error("Artikel nicht lesbar")
        print(pruef_hash(article))
        raise SystemExit(0)
    print(json.dumps(offene_befunde(), ensure_ascii=False, indent=2))
