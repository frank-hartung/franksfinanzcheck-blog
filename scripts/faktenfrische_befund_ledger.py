#!/usr/bin/env python3
"""Dauerhafte Fachbefunde der Faktenfrische (#912, #984, #912-Nachlauf).

Ein erfolgreicher Faktencheck darf ein Alter zurücksetzen, aber keinen
inhaltlichen Befund löschen. Befunde bleiben bis zu einer dokumentierten
menschlichen Entscheidung offen.

WARUM ES ZWEI HASHES GIBT (Nachtrag 03.11.2026, #912)
----------------------------------------------------
Bis zum 02.11.2026 band eine Entscheidung an `pruef_hash` – den Hash über
Titel, Beschreibung, Kurzantwort, QUELLEN und Text. Das hatte zwei Folgen,
die zusammen jeden Bestand dauerhaft rot halten:

  1. Der Lauf selbst schreibt `quellen` (die Belegkette). Jede automatische
     Quellenpflege änderte damit die „Fassung“ – und machte jede bereits
     dokumentierte Entscheidung ungültig. Die Maschine löschte also durch
     ihre eigene Arbeit den Schließpfad.
  2. Wurde ein Text zur Heilung eines Befunds geändert (genau der Zweck des
     Befunds!), passte der alte Hash nicht mehr. Eine Entscheidung über den
     neuen Text konnte den alten Befund nie mehr schließen: 8 von 13 Seiten
     trugen am 03.11.2026 solche unschließbaren Befunde, zwei weitere nur
     den Platzhalter `legacy-unbekannt`.

Deshalb gilt jetzt: **Befund und Entscheidung hängen am TEXT**
(`text_hash`: Titel, Beschreibung, Kurzantwort, Text – ohne Quellen), die
KI-Fachprüfung weiterhin an der vollständigen Prüffassung (`pruef_hash`,
inklusive Quellen; sie belegt, dass die Quellen mitgeprüft wurden).

Eine Entscheidung nennt beide Seiten:
  * `befund_fassung`  – welcher Ledger-Eintrag gemeint ist (Beweis der Zuordnung)
  * `geprueft_fassung` – welcher Text tatsächlich gelesen wurde (Beweis der Prüfung)

Sie schließt genau diesen Befund an genau diesem Text. Ändert sich der Text
später, öffnet der Befund erneut – der Mensch muss die neue Aussage erneut
anschauen. Das bleibt die Regel: **die Maschine entscheidet nie fachlich.**

NACHLESE (#984): Ein Lauf schreibt das Dossier vor seiner Bilanz. Bricht er
danach ab, liegen seine Befunde nur im Dossier. `--nachlese` liest die
Dossiers und ergänzt ausschließlich, was im Ledger fehlt – idempotent, ohne
eine Fassung zu erfinden und ohne je einen Befund zu schließen.

NUTZUNG
  python3 scripts/faktenfrische_befund_ledger.py                 # offene Befunde
  python3 scripts/faktenfrische_befund_ledger.py --fassung <datei>
  python3 scripts/faktenfrische_befund_ledger.py --text-hash <datei>
  python3 scripts/faktenfrische_befund_ledger.py --entscheiden <befund-id> \\
      --von "Name" --begruendung "was geprüft/geändert wurde" [--beleg URL]
  python3 scripts/faktenfrische_befund_ledger.py --nachlese [--apply]
  python3 scripts/faktenfrische_befund_ledger.py --wache         # entscheidbar?
  python3 scripts/faktenfrische_befund_ledger.py --selftest

EXIT: 0 ok · 1 nicht entscheidbarer/strukturfehlerhafter Befundstand
      2 Selbsttest rot oder Werkzeugfehler
"""
from __future__ import annotations

import datetime as dt
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
AKTE = ROOT / "BEFUND-AKTE.md"

LEGACY = "legacy-unbekannt"
HASH_RE = re.compile(r"[0-9a-f]{64}")
# Eine Begründung, die nur „ok“ sagt, ist keine Entscheidung. Die Grenze ist
# bewusst klein (kein Aufsatz), aber groß genug, um die Prüfung zu benennen.
BEGRUENDUNG_MIN = 20


class LedgerFehler(ValueError):
    """Ungültiger Beweisstand; niemals als leere Befundliste behandeln."""


# ----------------------------------------------------------------------
# Hashes: eine Prüffassung, ein Text
# ----------------------------------------------------------------------
def body_hash(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _frontmatter(art: dict) -> dict:
    fm = yaml.safe_load(art.get("fm", "")) or {}
    if not isinstance(fm, dict):
        raise LedgerFehler("Frontmatter ist kein Mapping")
    return fm


def pruef_hash(art: dict) -> str:
    """Hash der vollständigen Prüffassung – inklusive Quellen (KI-Bindung)."""
    fm = _frontmatter(art)
    material = {
        "title": fm.get("title", ""),
        "description": fm.get("description", ""),
        "kurzantwort": fm.get("kurzantwort", ""),
        "quellen": fm.get("quellen") or [],
        "body": art.get("body", ""),
    }
    payload = json.dumps(material, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def text_hash(art: dict) -> str:
    """Hash der Aussageflächen – OHNE Quellen.

    Quellen schreibt der Lauf selbst. Ein Befund über eine Aussage darf
    nicht dadurch unschließbar werden, dass die Belegkette aufgefrischt
    wird; eine Aussageänderung dagegen muss jede Entscheidung öffnen.
    """
    fm = _frontmatter(art)
    material = {
        "title": fm.get("title", ""),
        "description": fm.get("description", ""),
        "kurzantwort": fm.get("kurzantwort", ""),
        "body": art.get("body", ""),
    }
def pruef_hash(art: dict) -> str:
    """Fassungs-Hash über Text UND die mitgeprüften Aussageflächen.

    Seit #996 (03.11.2026) gehören auch `pin_title` und `pin_description`
    zum Hash: Die Werbeflächen hatten Superlative und Sparversprechen
    zurückgebracht, ohne dass sich die Fassung änderte – eine
    fassungsgebundene Entscheidung hätte den Rückfall nicht gesehen.
    Ältere Dossier- und Queue-Hashes bleiben gespeicherte Historie; der
    nächste Lauf bindet die Fassung mit dem erweiterten Material neu.
    """
    fm = yaml.safe_load(art.get("fm", "")) or {}
    if not isinstance(fm, dict):
        raise LedgerFehler("Frontmatter ist kein Mapping")
    material = {}
    material["title"] = fm.get("title", "")
    material["description"] = fm.get("description", "")
    material["kurzantwort"] = fm.get("kurzantwort", "")
    material["pin_title"] = fm.get("pin_title", "")
    material["pin_description"] = fm.get("pin_description", "")
    material["quellen"] = fm.get("quellen") or []
    material["body"] = art.get("body", "")
    payload = json.dumps(material, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def befund_id(slug: str, befund: dict) -> str:
    text = "\x1f".join((slug, str(befund.get("typ", "befund")),
                        str(befund.get("text", "")).strip()))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:20]


def fassungen_aus_bestand() -> dict[str, dict]:
    """slug → {"text": Text-Hash, "pruef": Prüffassungs-Hash} für JEDE Seite.

    Blogartikel UND Ratgeberseiten: ein Befund kann auf beiden liegen.
    Ein Importfehler ist ein Werkzeugfehler – nie ein stilles „keine Seiten“.
    """
    try:
        import faktenfrische as ff  # noqa: PLC0415 – Zyklus: ff importiert uns
        seiten = ff.alle_artikel("alle")
    except Exception as exc:  # noqa: BLE001 – fail-closed
        raise LedgerFehler(f"Bestand nicht lesbar: {exc}") from exc
    return {str(a["slug"]): {"text": text_hash(a), "pruef": pruef_hash(a)}
            for a in seiten if a.get("slug")}


def _normalisiere_fassungen(fassungen) -> dict[str, dict]:
    """Akzeptiert {slug: hash} (Tests) und {slug: {"text","pruef"}}."""
    if not fassungen:
        return {}
    ergebnis = {}
    for slug, wert in dict(fassungen).items():
        if isinstance(wert, str):
            ergebnis[str(slug)] = {"text": wert, "pruef": wert}
        elif isinstance(wert, dict):
            ergebnis[str(slug)] = {"text": wert.get("text") or "",
                                   "pruef": wert.get("pruef") or ""}
    return ergebnis


# ----------------------------------------------------------------------
# Lesen
# ----------------------------------------------------------------------
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
                           "fassung_sha256": run.get("fassung_sha256", LEGACY),
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
        for feld in ("fassung_sha256", "text_sha256"):
            alt_wert = previous.get(feld, "")
            neu_wert = entry.get(feld, "")
            if HASH_RE.fullmatch(str(alt_wert)) and not HASH_RE.fullmatch(str(neu_wert)):
                candidate[feld] = alt_wert
        merged[key] = candidate
    return [merged[key] for key in sorted(merged)]


def entscheidungen_laden(path: Path = ENTSCHEIDUNGEN) -> dict[tuple[str, str], dict]:
    """Menschliche Schließakte – Schema v1 und v2.

    v1 (bis 02.11.2026): `fassung_sha256` – bindet an die Prüffassung.
    v2 (ab 03.11.2026): `befund_fassung` + `geprueft_fassung` – bindet an den
    Ledger-Eintrag UND an den tatsächlich gelesenen Text.
    """
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
                for k in ("slug", "befund_id", "entschieden_von", "begruendung")):
            raise LedgerFehler("Entscheidung braucht Slug, Befund, Person und Begründung")
        if len(entry["begruendung"].strip()) < BEGRUENDUNG_MIN:
            raise LedgerFehler(
                f"Entscheidung für {entry.get('befund_id')} braucht eine "
                f"Begründung (≥ {BEGRUENDUNG_MIN} Zeichen) – 'ok' ist keine Prüfung")
        if "befund_fassung" in entry or "geprueft_fassung" in entry:
            if not all(isinstance(entry.get(k), str) and entry[k].strip()
                       for k in ("befund_fassung", "geprueft_fassung")):
                raise LedgerFehler("Entscheidung braucht `befund_fassung` UND "
                                   "`geprueft_fassung`")
            if not HASH_RE.fullmatch(entry["geprueft_fassung"]):
                raise LedgerFehler("`geprueft_fassung` muss ein echter SHA-256 sein")
            befund_fassung = entry["befund_fassung"]
        else:
            if not isinstance(entry.get("fassung_sha256"), str) or \
                    not HASH_RE.fullmatch(entry["fassung_sha256"]):
                raise LedgerFehler("Entscheidung braucht einen echten SHA-256 der "
                                   "geprüften Fassung")
            befund_fassung = entry["fassung_sha256"]
            entry = dict(entry, geprueft_fassung=entry["fassung_sha256"])
        key = (entry["slug"], entry["befund_id"])
        if key in result:
            raise LedgerFehler(f"Doppelte Entscheidung: {key}")
        result[key] = dict(entry, befund_fassung=befund_fassung)
    return result


def _entscheidung_schliesst(decision: dict | None, entry: dict,
                            fassungen: dict) -> bool:
    """Schließt diese Entscheidung GENAU diesen Eintrag an GENAU diesem Text?"""
    if not decision:
        return False
    # 1) Der Mensch muss den richtigen Ledger-Eintrag adressiert haben.
    ziele = {str(entry.get("fassung_sha256") or ""),
             str(entry.get("text_sha256") or "")}
    if str(decision.get("befund_fassung") or "") not in ziele:
        return False
    geprueft = str(decision.get("geprueft_fassung") or "")
    # 2) v2: der Text, den der Mensch gelesen hat, muss der aktuelle sein.
    #    Ist die Seite nicht mehr lesbar, bleibt die dokumentierte Entscheidung
    #    gültig – sie betrifft eine Aussage, die es nicht mehr gibt.
    aktuell = fassungen.get(str(entry.get("slug")))
    if decision.get("befund_fassung") != decision.get("geprueft_fassung") and aktuell:
        if geprueft not in (aktuell.get("text"), aktuell.get("pruef")):
            return False
    return bool(geprueft)


def offene_eintraege(entries: list[dict], decisions: dict,
                     fassungen: dict | None = None) -> list[dict]:
    if fassungen is None:
        fassungen = fassungen_aus_bestand()
    fassungen = _normalisiere_fassungen(fassungen)
    result = []
    for entry in entries:
        decision = decisions.get((entry["slug"], entry["id"]))
        if _entscheidung_schliesst(decision, entry, fassungen):
            continue
        result.append(entry)
    return result


def offene_befunde(queue_path: Path = QUEUE,
                   decisions_path: Path = ENTSCHEIDUNGEN,
                   fassungen: dict | None = None) -> list[dict]:
    return offene_eintraege(zusammenfuehren(_json_object(queue_path), []),
                            entscheidungen_laden(decisions_path), fassungen)


# ----------------------------------------------------------------------
# Zustand eines Befunds – entscheidbar oder nicht?
# ----------------------------------------------------------------------
def _datum(wert: str) -> dt.date | None:
    try:
        return dt.date.fromisoformat(str(wert)[:10])
    except (TypeError, ValueError):
        return None


def fassung_status(entry: dict, fassungen: dict, stichtag: dt.date) -> dict:
    """Wo steht dieser Befund gegenüber dem heutigen Text?"""
    stored = {str(entry.get("fassung_sha256") or ""),
              str(entry.get("text_sha256") or "")}
    if not any(HASH_RE.fullmatch(w) for w in stored):
        return {"status": "ohne-fassung",
                "hinweis": "Kein gültiger Fassungs-Hash (Altbestand) – die "
                           "Entscheidung bindet an den heutigen Text."}
    aktuell = fassungen.get(str(entry.get("slug")))
    if not aktuell:
        return {"status": "seite-fehlt",
                "hinweis": "Seite ist im Bestand nicht lesbar – Entscheidung "
                           "würde eine gelöschte Seite bestätigen."}
    if aktuell.get("text") in stored or aktuell.get("pruef") in stored:
        return {"status": "aktuell",
                "hinweis": "Der Text ist seit dem Befund unverändert."}
    alt = next((w for w in stored if HASH_RE.fullmatch(w)), "")
    return {"status": "ueberholt",
            "hinweis": "Der Text wurde nach dem Befund geändert "
                       f"(`{alt[:12]}…` → `{(aktuell.get('text') or '')[:12]}…`). "
                       "Bitte den HEUTIGEN Text prüfen und entscheiden.",
            "alte_fassung": alt,
            "heutige_fassung": aktuell.get("text") or ""}


def befunde_mit_status(queue_path: Path = QUEUE,
                       decisions_path: Path = ENTSCHEIDUNGEN,
                       fassungen: dict | None = None,
                       stichtag: dt.date | None = None) -> list[dict]:
    """Offene Befunde, angereichert um Fassungsstand, Alter und Entscheidbarkeit."""
    stichtag = stichtag or dt.date.today()
    if fassungen is None:
        fassungen = fassungen_aus_bestand()
    fassungen = _normalisiere_fassungen(fassungen)
    result = []
    for entry in offene_befunde(queue_path, decisions_path, fassungen):
        stand = fassung_status(entry, fassungen, stichtag)
        gesehen = _datum(entry.get("zuletzt_gesehen", ""))
        alter = (stichtag - gesehen).days if gesehen else None
        result.append({
            **entry,
            "fassung_status": stand["status"],
            "fassung_hinweis": stand["hinweis"],
            "heutige_fassung": stand.get("heutige_fassung", ""),
            "alter_tage": alter,
            # Alle offenen Befunde sind entscheidbar – der Weg ist
            # `--entscheiden`, nicht das Editieren einer YAML-Datei.
            "entscheidbar": stand["status"] != "seite-fehlt",
            "nicht_entscheidbar_grund": (
                "" if stand["status"] != "seite-fehlt" else stand["hinweis"]),
        })
    result.sort(key=lambda e: (
        0 if e["fassung_status"] == "ueberholt" else 1,
        0 if e["fassung_status"] == "ohne-fassung" else 1,
        -(e["alter_tage"] if e["alter_tage"] is not None else -1),
        e["slug"], e["id"]))
    return result


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
        if not isinstance(fassung, str) or not HASH_RE.fullmatch(fassung):
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
                # Der Text-Hash macht den Befund auch nach einer Korrektur
                # entscheidbar (#912); fehlt er im Alt-Dossier, bleibt die
                # Prüffassung die Zuordnung.
                "text_sha256": (data.get("text_sha256")
                                if isinstance(data.get("text_sha256"), str)
                                and HASH_RE.fullmatch(data["text_sha256"]) else ""),
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


# ----------------------------------------------------------------------
# Entscheiden – der Schließpfad (statt Handarbeit an einer YAML-Datei)
# ----------------------------------------------------------------------
def _jetzt() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _yaml_kopf(path: Path) -> str:
    """Kommentarkopf der Schließakte erhalten (menschlich kuratiert)."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ("# Menschliche Schließakte zur Faktenfrische (#912).\n"
                "# Eine Entscheidung schließt nur genau diesen Befund an genau "
                "diesem Text.\n# Nie automatisch ergänzen. Nach einer Textänderung "
                "muss neu entschieden werden.\n")
    treffer = re.search(r"^entscheidungen:\s*$", text, re.MULTILINE)
    return text[:treffer.start()] if treffer else ""


def _yaml_schreiben(path: Path, daten: dict) -> None:
    kopf = _yaml_kopf(path)
    rumpf = yaml.safe_dump(daten, allow_unicode=True, sort_keys=False,
                           default_flow_style=False)
    tmp = Path(str(path) + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(kopf + rumpf, encoding="utf-8")
        tmp.replace(path)
    except OSError as exc:
        raise LedgerFehler(f"{path.name} nicht schreibbar: {exc}") from exc


def entscheidung_anfuegen(befund_id_: str, von: str, begruendung: str,
                          beleg: str = "", *,
                          queue_path: Path = QUEUE,
                          decisions_path: Path = ENTSCHEIDUNGEN,
                          fassungen: dict | None = None,
                          heute: dt.date | None = None) -> dict:
    """Eine menschliche Entscheidung dokumentieren, fassungsgebunden.

    Es gibt hier keinen Automatik-Pfad: Ohne Namen und Begründung schreibt
    diese Funktion nichts. Sie prüft die Zuordnung, bindet an den heutigen
    Text und macht den Befund damit schließbar – auch wenn der Text seit dem
    Befund korrigiert wurde (genau das ist der Normalfall einer Heilung).
    """
    von = (von or "").strip()
    begruendung = (begruendung or "").strip()
    if not von:
        raise LedgerFehler("`--von` fehlt – eine Entscheidung braucht eine Person")
    if len(begruendung) < BEGRUENDUNG_MIN:
        raise LedgerFehler(f"`--begruendung` braucht mindestens {BEGRUENDUNG_MIN} "
                           "Zeichen (was wurde geprüft, geändert oder verworfen?)")
    heute = heute or dt.date.today()
    if fassungen is None:
        fassungen = fassungen_aus_bestand()
    fassungen = _normalisiere_fassungen(fassungen)
    offen = offene_befunde(queue_path, decisions_path, fassungen)
    treffer = [e for e in offen if e["id"] == befund_id_]
    if not treffer:
        raise LedgerFehler(f"Kein offener Befund mit der ID `{befund_id_}` "
                           "(bereits entschieden, Tippfehler oder nicht im Ledger)")
    if len(treffer) > 1:
        raise LedgerFehler(f"Befund-ID `{befund_id_}` ist nicht eindeutig "
                           f"({len(treffer)} Seiten) – Ledger prüfen")
    entry = treffer[0]
    stand = fassung_status(entry, fassungen, heute)
    if stand["status"] == "seite-fehlt":
        raise LedgerFehler(f"{entry['slug']}: {stand['hinweis']}")
    aktuell = fassungen[entry["slug"]]["text"]
    decisions = entscheidungen_laden(decisions_path)
    if (entry["slug"], befund_id_) in decisions:
        raise LedgerFehler("Für diesen Befund existiert bereits eine Entscheidung")
    decision = {
        "slug": entry["slug"],
        "befund_id": befund_id_,
        "befund_fassung": entry.get("fassung_sha256") or LEGACY,
        "geprueft_fassung": aktuell,
        "typ": entry.get("typ", ""),
        "beanstandung": entry.get("text", "")[:400],
        "beleg": beleg.strip(),
        "entschieden_von": von,
        "entschieden_am": heute.isoformat(),
        "fassung_wechsel": stand["status"] != "aktuell",
        "begruendung": begruendung,
    }
    daten = {"entscheidungen": []}
    if decisions_path.exists():
        roh = yaml.safe_load(decisions_path.read_text(encoding="utf-8")) or {}
        if isinstance(roh, dict) and isinstance(roh.get("entscheidungen"), list):
            daten["entscheidungen"] = roh["entscheidungen"]
    daten["entscheidungen"].append(decision)
    _yaml_schreiben(decisions_path, daten)
    # Selbstkontrolle: Was wir geschrieben haben, muss den Befund schließen.
    if any(e["id"] == befund_id_ for e in
           offene_befunde(queue_path, decisions_path, fassungen)):
        raise LedgerFehler("Entscheidung geschrieben, aber der Befund bleibt "
                           "offen – Fassungsbindung prüfen")
    return decision


# ----------------------------------------------------------------------
# Wache: jeder offene Befund ist entscheidbar
# ----------------------------------------------------------------------
def wache(*, queue_path: Path = QUEUE, decisions_path: Path = ENTSCHEIDUNGEN,
          fassungen: dict | None = None, stichtag: dt.date | None = None) -> dict:
    """Strukturprüfung: kein Befund darf ohne Schließweg im Ledger liegen."""
    stichtag = stichtag or dt.date.today()
    befunde = befunde_mit_status(queue_path, decisions_path, fassungen, stichtag)
    nicht_entscheidbar = [e for e in befunde if not e["entscheidbar"]]
    ohne_begruendung = [e for e in befunde if not str(e.get("text") or "").strip()]
    return {
        "offen": len(befunde),
        "nicht_entscheidbar": len(nicht_entscheidbar),
        "ohne_beanstandung": len(ohne_begruendung),
        "seiten": len({e["slug"] for e in befunde}),
        "ueberholt": sum(1 for e in befunde if e["fassung_status"] == "ueberholt"),
        "ohne_fassung": sum(1 for e in befunde if e["fassung_status"] == "ohne-fassung"),
        "gruen": not nicht_entscheidbar and not ohne_begruendung,
        "funde": [f"{e['slug']} · {e['id']}: {e['nicht_entscheidbar_grund']}"
                  for e in nicht_entscheidbar],
    }


# ----------------------------------------------------------------------
# Selbsttest
# ----------------------------------------------------------------------
def selftest() -> int:
    finding = {"typ": "praezision", "text": "Unbelegte Preisangabe"}
    entry = {"id": befund_id("a", finding), "slug": "a",
             "fassung_sha256": body_hash("Fassung A"), **finding, "beleg": ""}
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
        tmp = Path(tmp)
        queue_path = tmp / "queue.json"
        decisions = tmp / "decisions.yaml"
        fassung_a = body_hash("Text A")
        fassung_b = body_hash("Text B")
        eintrag = {"id": befund_id("seite", finding), "slug": "seite",
                   "fassung_sha256": fassung_a, "text_sha256": fassung_a,
                   **finding, "beleg": "", "zuletzt_gesehen": "2026-10-30 11:01 UTC"}
        queue_path.write_text(json.dumps({"fachbefunde": [eintrag]}), encoding="utf-8")
        fassungen = {"seite": {"text": fassung_a, "pruef": fassung_a}}

        # (a) Ohne Entscheidung offen, und zwar entscheidbar.
        offen = befunde_mit_status(queue_path, decisions, fassungen,
                                   dt.date(2026, 11, 3))
        assert len(offen) == 1 and offen[0]["entscheidbar"], offen
        assert offen[0]["alter_tage"] == 4, offen

        # (b) Ein geänderter TEXT macht den Befund nicht unschließbar (#912).
        fassungen_neu = {"seite": {"text": fassung_b, "pruef": fassung_b}}
        offen = befunde_mit_status(queue_path, decisions, fassungen_neu,
                                   dt.date(2026, 11, 3))
        assert offen[0]["fassung_status"] == "ueberholt", offen
        entscheidung_anfuegen(eintrag["id"], "Redaktion",
                              "Preisangabe im aktuellen Text entfernt und geprüft",
                              queue_path=queue_path, decisions_path=decisions,
                              fassungen=fassungen_neu, heute=dt.date(2026, 11, 3))
        assert offene_befunde(queue_path, decisions, fassungen_neu) == []
        text = decisions.read_text(encoding="utf-8")
        assert "befund_fassung" in text and "geprueft_fassung" in text
        assert fassung_b in text and fassung_a in text
        # (c) Maschinen-Quellenpflege (pruef ändert sich, Text nicht) öffnet NICHT.
        assert offene_befunde(queue_path, decisions,
                              {"seite": {"text": fassung_b, "pruef": "f" * 64}}) == []
        # (d) Eine spätere Textänderung öffnet die Entscheidung erneut.
        spaeter = {"seite": {"text": body_hash("Text C"), "pruef": body_hash("Text C")}}
        assert len(offene_befunde(queue_path, decisions, spaeter)) == 1

        # (e) Eine Entscheidung ohne Person/Begründung ist keine Entscheidung.
        for kwargs in ({"von": "", "begruendung": "x" * 40},
                       {"von": "Redaktion", "begruendung": "ok"}):
            try:
                entscheidung_anfuegen(eintrag["id"], queue_path=queue_path,
                                      decisions_path=tmp / "leer.yaml",
                                      fassungen=fassungen, **kwargs)
            except LedgerFehler:
                pass
            else:
                raise AssertionError("Leere Entscheidung wurde akzeptiert")
        assert not (tmp / "leer.yaml").exists(), "Datei trotz Fehler geschrieben"

        # (f) `legacy-unbekannt` ist entscheidbar (Altbestand ohne Hash).
        legacy = dict(eintrag, id=befund_id("alt", finding), slug="alt",
                      fassung_sha256=LEGACY, text_sha256="")
        queue_path.write_text(json.dumps({"fachbefunde": [legacy]}), encoding="utf-8")
        fassungen_alt = {"alt": {"text": fassung_a, "pruef": fassung_a}}
        assert befunde_mit_status(queue_path, tmp / "neu.yaml", fassungen_alt,
                                  dt.date(2026, 11, 3))[0]["fassung_status"] == "ohne-fassung"
        entscheidung_anfuegen(legacy["id"], "Redaktion",
                              "Altbefund am heutigen Text geprüft und erledigt",
                              queue_path=queue_path, decisions_path=tmp / "alt.yaml",
                              fassungen=fassungen_alt, heute=dt.date(2026, 11, 3))
        assert offene_befunde(queue_path, tmp / "alt.yaml", fassungen_alt) == []

        # (g) Fehlt die Seite, bleibt der Befund offen und heißt so.
        assert wache(queue_path=queue_path, decisions_path=tmp / "alt.yaml",
                     fassungen=fassungen_alt,
                     stichtag=dt.date(2026, 11, 3))["gruen"]
        einsam = {"andere-seite": {"text": fassung_a, "pruef": fassung_a}}
        queue_path.write_text(json.dumps({"fachbefunde": [eintrag]}), encoding="utf-8")
        stand = befunde_mit_status(queue_path, tmp / "ohne.yaml", einsam,
                                   dt.date(2026, 11, 3))
        assert stand and stand[0]["fassung_status"] == "seite-fehlt"
        assert not wache(queue_path=queue_path, decisions_path=tmp / "alt.yaml",
                         fassungen=einsam, stichtag=dt.date(2026, 11, 3))["gruen"]

        # (h) Nachlese: Dossier-Befunde erreichen das Ledger, ohne zu schließen.
        dossier_dir = tmp / "artikel"
        dossier_dir.mkdir()
        (dossier_dir / "seite.json").write_text(json.dumps({
            "slug": "seite", "erzeugt": "2026-10-31 10:34 UTC",
            "fassung_sha256": fassung_a, "befunde": [finding]}), encoding="utf-8")
        (dossier_dir / "ohne_hash.json").write_text(json.dumps({
            "slug": "alt", "befunde": [finding]}), encoding="utf-8")
        leer = tmp / "queue2.json"
        leer.write_text("{}", encoding="utf-8")
        ergebnis = nachlese_anwenden(dossier_dir, leer)
        assert ergebnis["ergaenzt"] == 1, ergebnis
        assert any("ohne_hash.json" in h for h in ergebnis["hinweise"]), ergebnis
        assert len(zusammenfuehren(_json_object(leer), [])) == 1
        assert nachlese_anwenden(dossier_dir, leer)["fehlend"] == []

    print("✅ Faktenfrische-Befundledger: zwei Hashes, fassungsgebundene "
          "Entscheidung, Textänderung bleibt schließbar, Quellenpflege öffnet "
          "nicht, Altbestand entscheidbar, Nachlese, fail-closed.")
    return 0


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--fassung", help="SHA-256 der Prüffassung einer Artikel-Datei")
    parser.add_argument("--text-hash", help="SHA-256 der Aussageflächen (ohne Quellen)")
    parser.add_argument("--entscheiden", metavar="BEFUND_ID",
                        help="menschliche Entscheidung zu genau diesem Befund")
    parser.add_argument("--von", help="wer entscheidet (Pflicht bei --entscheiden)")
    parser.add_argument("--begruendung",
                        help="was geprüft/geändert/verworfen wurde (Pflicht)")
    parser.add_argument("--beleg", default="", help="fakultativer Beleg (URL)")
    parser.add_argument("--nachlese", action="store_true",
                        help="Dossier-Befunde finden, die im Ledger fehlen")
    parser.add_argument("--apply", action="store_true",
                        help="mit --nachlese: fehlende Befunde ins Ledger ergänzen")
    parser.add_argument("--wache", action="store_true",
                        help="Exit 1, wenn ein offener Befund keinen Schließweg hat")
    parser.add_argument("--json", action="store_true", help="maschinenlesbar")
    args = parser.parse_args()
    try:
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
                      f"{ergebnis['befunde_im_dossier']} Dossier-Befund(en) fehlen "
                      "im Ledger.")
                for eintrag in ergebnis["fehlend"]:
                    print(f"  - {eintrag['slug']} · {eintrag['typ']}: "
                          f"{eintrag['text'][:110]}")
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
        if args.text_hash:
            import faktenfrische as ff
            article = ff.lade_artikel(args.text_hash)
            if article is None:
                parser.error("Artikel nicht lesbar")
            print(text_hash(article))
            raise SystemExit(0)
        if args.entscheiden:
            if not args.von or not args.begruendung:
                parser.error("--entscheiden braucht --von und --begruendung")
            decision = entscheidung_anfuegen(args.entscheiden, args.von,
                                             args.begruendung, args.beleg)
            print(f"✅ {decision['slug']} · {decision['befund_id']} entschieden "
                  f"von {decision['entschieden_von']} "
                  f"({'Fassung hatte sich geändert' if decision['fassung_wechsel'] else 'Text unverändert'}).")
            raise SystemExit(0)
        if args.wache:
            stand = wache()
            if args.json:
                print(json.dumps(stand, ensure_ascii=False, indent=2))
            else:
                print(f"Offene Fachbefunde: {stand['offen']} auf {stand['seiten']} "
                      f"Seiten · überholte Fassung: {stand['ueberholt']} · "
                      f"ohne Fassung: {stand['ohne_fassung']}")
                if stand["gruen"]:
                    print("✅ Jeder offene Befund hat einen Schließweg "
                          "(eine menschliche Entscheidung am heutigen Text).")
                else:
                    print(f"❌ {stand['nicht_entscheidbar']} Befund(e) ohne "
                          "Schließweg:")
                    for fund in stand["funde"]:
                        print(f"   - {fund}")
            raise SystemExit(0 if stand["gruen"] else 1)
        if args.json:
            print(json.dumps(befunde_mit_status(), ensure_ascii=False, indent=2))
        else:
            for eintrag in befunde_mit_status():
                print(json.dumps(eintrag, ensure_ascii=False, indent=2))
    except LedgerFehler as exc:
        print(f"❌ {exc}", file=__import__("sys").stderr)
        raise SystemExit(2)
