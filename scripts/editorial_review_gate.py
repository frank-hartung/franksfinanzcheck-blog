#!/usr/bin/env python3
"""Risikobasierte redaktionelle Freigabe für YMYL-Inhalte.

Ein Qualitäts-Score, eine KI-Prüfung oder ein vorhandenes Autorenfeld sind
KEINE fachliche Freigabe. Dieses Gate trennt deshalb drei Dinge:

* Autorenschaft: Wer verantwortet den Text?
* Belegkette: Auf welche externen Quellen stützen sich Aussagen und Zahlen?
* Freigabe: Wer hat welche Zahlen wann geprüft – und für welche Textfassung?

Für die Risikoklasse ``hoch`` (Baufinanzierung, Altersvorsorge, Kredite und
Versicherungen) gilt fail-closed. Eine Veröffentlichung ist nur zulässig, wenn
``redaktionelle_pruefung`` vollständig ist, die Belegkette belastbar ist und
der Freigabe-Hash exakt zur geprüften Fassung passt. Eine spätere Änderung an
Text, Kurzantwort, Prüfprotokoll oder Quellen entwertet die Freigabe automatisch.

Aufrufe:
  python3 scripts/editorial_review_gate.py --selftest
  python3 scripts/editorial_review_gate.py --file content/posts/.../index.md
  python3 scripts/editorial_review_gate.py --all --report
  python3 scripts/editorial_review_gate.py --all --strict
  python3 scripts/editorial_review_gate.py --published --strict
  python3 scripts/editorial_review_gate.py --seal --file content/posts/.../index.md

``--seal`` setzt ausschließlich ``inhalt_sha256`` in einem bereits vollständig
redigierten Freigabeblock. Es erfindet weder Prüfer noch Prüfergebnis und
schreibt einen unveränderlichen Audit-Eintrag nach
``data/editorial_review_history.jsonl``.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "content" / "posts"
REPORT = ROOT / "REDAKTIONELLE-PRUEFUNG-REPORT.md"
QUEUE = ROOT / "data" / "editorial_review_queue.json"
HISTORY = ROOT / "data" / "editorial_review_history.jsonl"

RISK_HIGH = "hoch"
RISK_ELEVATED = "erhoeht"
RISK_STANDARD = "standard"
RISK_ORDER = {RISK_STANDARD: 0, RISK_ELEVATED: 1, RISK_HIGH: 2}
REVIEW_INTERVAL_DAYS = 45
MIN_SOURCES_HIGH = 2
MIN_WORDS_BEFORE_AFFILIATE = 600
MIN_H2_BEFORE_AFFILIATE = 2
MIN_ANCHOR_LENGTH = 12

# Aussagen, bei denen generische KI-Texte besonders häufig unzulässig
# pauschalisieren. Jede Fundstelle muss im Prüfprotokoll auf eine konkrete,
# sichtbare Aussage und deren Quellen abgebildet sein.
BLANKET_CLAIM_PATTERNS = (
    re.compile(r"\b(?:zinsbindung\w*|eigenkapital\w*|banken?|kreditgeber\w*)\b[^.!?\n]{0,100}"
               r"\b(?:immer|nie|garantiert|ausnahmslos|grundsätzlich|optimal|am besten|muss|müssen|sollte|sollten)\b", re.I),
    re.compile(r"\b(?:immer|nie|garantiert|ausnahmslos|grundsätzlich)\b[^.!?\n]{0,100}"
               r"\b(?:zinsbindung\w*|eigenkapital\w*|banken?|kreditgeber\w*)\b", re.I),
    re.compile(r"\bohne\s+eigenkapital\b", re.I),
    re.compile(r"\b(?:banken?|kreditgeber\w*)\s+(?:akzeptieren|verlangen|finanzieren|lehnen|bewerten|rechnen)\b", re.I),
)
MATERIAL_NUMBER_RE = re.compile(r"(?<![\w])\d[\d. ]*(?:,\d+)?\s*(?:%|Prozent\b|Euro\b|€)", re.I)

# Nur Titel, Beschreibung, Keywords und Pillar werden klassifiziert. Interne
# Links im Body dürfen einen Artikel nie versehentlich zur Hochrisiko-Seite
# machen. Die vier vom Auftrag benannten YMYL-Familien stehen explizit hier.
HIGH_PATTERNS = (
    re.compile(r"\b(?:baufinanzier\w*|immobilienfinanzier\w*|immobilienkredit\w*|hypothek\w*|anschlussfinanzier\w*|hauskauf\s+finanzier\w*)\b", re.I),
    re.compile(r"\b(?:altersvorsorge\w*|rentenlücke\w*|riester(?:-rente)?|rürup(?:-rente)?|ruerup(?:-rente)?|betriebliche\s+altersvorsorge|rente\s+20\d{2})\b", re.I),
    re.compile(r"\b(?:ratenkredit\w*|immobiliendarlehen\w*|darlehen\w*|umschuld\w*|restschuld\w*|dispo(?:kredit)?|schufa|kredit(?!kart)\w*)\b", re.I),
    re.compile(r"\b(?:[a-zäöüß-]*versicher\w*|police\w*|berufsunfähigkeit\w*|berufsunfaehigkeit\w*)\b", re.I),
)
ELEVATED_PATTERNS = (
    re.compile(r"\b(?:tagesgeld|festgeld|girokonto|kreditkarte|depot|etf|sparplan|zins\w*|anlage\w*|steuer\w*)\b", re.I),
    re.compile(r"\b(?:stromtarif|gastarif|energievertrag|kündigungsfrist|kuendigungsfrist|handyvertrag|dsl.?vertrag)\b", re.I),
)

# Rang 1/2 der bestehenden Faktenfrische-Allowlist. Ein Affiliate-Partner ist
# absichtlich nie Belegquelle. Subdomains sind erlaubt.
TRUSTED_SOURCE_RANK = {
    "bundesnetzagentur.de": 1,
    "destatis.de": 1,
    "gesetze-im-internet.de": 1,
    "bafin.de": 1,
    "bundesbank.de": 1,
    "bmwk.de": 1,
    "bundesfinanzministerium.de": 1,
    "verbraucherzentrale.de": 2,
    "test.de": 2,
    "bdew.de": 2,
    "gdv.de": 2,
    "co2online.de": 2,
    "dena.de": 2,
    "tagesschau.de": 3,
    "heise.de": 3,
    "spiegel.de": 3,
}
AFFILIATE_DOMAINS = ("check24.net", "check24.de", "partner-versicherung.de", "awin1.com")
ALLOWED_REVIEWER_TYPES = {"fachpruefer", "redaktion-mit-externer-belegkette"}
APPROVED_STATUSES = {"freigegeben", "approved"}


class ParseError(RuntimeError):
    """Frontmatter konnte nicht verlässlich gelesen werden."""


def _yaml_module():
    try:
        import yaml  # type: ignore
    except ImportError as exc:  # pragma: no cover - CI installiert PyYAML
        raise ParseError("PyYAML fehlt: python3 -m pip install pyyaml") from exc
    return yaml


def split_article(text: str) -> tuple[str, str]:
    """(Frontmatter-Text, Body), nur bei echten Fence-Zeilen."""
    if not text.startswith("---\n"):
        raise ParseError("Datei beginnt nicht mit einer Frontmatter-Fence")
    lines = text.splitlines(keepends=True)
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise ParseError("schließende Frontmatter-Fence fehlt")
    return "".join(lines[1:end]), "".join(lines[end + 1:])


def load_article(path: Path | str) -> tuple[dict, str, str]:
    path = Path(path)
    raw = path.read_text(encoding="utf-8")
    fm_text, body = split_article(raw)
    yaml = _yaml_module()
    try:
        fm = yaml.safe_load(fm_text) or {}
    except Exception as exc:  # noqa: BLE001 - als Gate-Befund lesbar machen
        raise ParseError(f"ungültiges YAML-Frontmatter: {exc}") from exc
    if not isinstance(fm, dict):
        raise ParseError("Frontmatter ist kein Mapping")
    return fm, body, raw


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return " ".join(_text(v) for v in value)
    return str(value)


def classify_text(text: str, pillar: str = "") -> str:
    haystack = f"{text} {pillar}".strip()
    if pillar.strip().lower() == "versicherungen":
        return RISK_HIGH
    if any(pattern.search(haystack) for pattern in HIGH_PATTERNS):
        return RISK_HIGH
    if any(pattern.search(haystack) for pattern in ELEVATED_PATTERNS):
        return RISK_ELEVATED
    return RISK_STANDARD


def inferred_risk(fm: dict) -> str:
    """Hauptthema einstufen, nicht beiläufige Erwähnungen.

    Titel, Themenwelt und die ersten zwei SEO-Keywords sind die redaktionelle
    Themenzusage. Beschreibung/Tags enthalten dagegen oft Querverweise wie
    „Dispo mitprüfen“ oder den Sammel-Tag „Kreditkarte und Kredit“; würden sie
    mitklassifiziert, würde ein Girokonto- oder Mietwagenartikel allein wegen
    eines Nebensatzes zur Kredit-/Versicherungsfreigabe hochgestuft.
    """
    keywords = fm.get("keywords") or []
    if not isinstance(keywords, (list, tuple)):
        keywords = [keywords]
    material = " ".join((_text(fm.get("title")), _text(list(keywords)[:2])))
    return classify_text(material, _text(fm.get("pillar")))


def review_scaffold_yaml(risk: str) -> str:
    """Frontmatter-Gerüst für Generatoren; bewusst keine Scheinfelder."""
    reason = ("KI-Entwurf – fachliche Freigabe vor Veröffentlichung erforderlich"
              if risk == RISK_HIGH else
              "Erstentwurf – Risikoklasse bei der Redaktion vorgemerkt")
    return (
        "redaktionelle_pruefung:\n"
        f'  risikoklasse: "{risk}"\n'
        '  status: "ausstehend"\n'
        f'  aenderungsgrund: "{reason}"\n'
    )


def _iso(value) -> str:
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()[:10]
    return str(value or "").strip()[:10]


def _date(value) -> dt.date | None:
    try:
        return dt.date.fromisoformat(_iso(value))
    except (ValueError, TypeError):
        return None


def _json_safe(value):
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def content_fingerprint(fm: dict, body: str) -> str:
    """Bindet Inhalt UND Prüfprotokoll, nur das Hashfeld selbst bleibt außen."""
    review = copy.deepcopy(fm.get("redaktionelle_pruefung") or {})
    if isinstance(review, dict):
        review.pop("inhalt_sha256", None)
    relevant = {
        "title": fm.get("title"),
        "description": fm.get("description"),
        "kurzantwort": fm.get("kurzantwort"),
        "author": fm.get("author"),
        "quellen": fm.get("quellen") or [],
        "redaktionelle_pruefung": review,
        "body": body.replace("\r\n", "\n").strip(),
    }
    payload = json.dumps(_json_safe(relevant), ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _domain(url: str) -> str:
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def _source_rank(url: str) -> int | None:
    host = _domain(url)
    for domain, rank in TRUSTED_SOURCE_RANK.items():
        if host == domain or host.endswith("." + domain):
            return rank
    return None


def _finding(code: str, detail: str) -> dict:
    return {"code": code, "detail": detail}


def _body_sentences(body: str) -> list[str]:
    """Lesbare Satz-/Listenblöcke für die Fundstellen-Zuordnung."""
    plain = re.sub(r"```.*?```", " ", body, flags=re.S)
    plain = re.sub(r"`[^`]+`", " ", plain)
    sentences: list[str] = []
    for line in plain.splitlines():
        for part in re.split(r"(?<=[.!?])\s+", line):
            part = part.strip()
            if part and not part.lstrip().startswith(("#", "[")):
                sentences.append(part)
    return sentences


def _short(value: str, limit: int = 100) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    return value if len(value) <= limit else value[:limit - 1] + "…"


def validate_article(fm: dict, body: str, *, today: dt.date | None = None,
                     ignore_hash: bool = False) -> dict:
    """Reine Prüfung; geeignet für Gate, CLI und Unit-Tests."""
    today = today or dt.date.today()
    risk = inferred_risk(fm)
    review = fm.get("redaktionelle_pruefung") or {}
    if not isinstance(review, dict):
        review = {}
    declared = str(review.get("risikoklasse") or "").strip().lower()
    status = str(review.get("status") or "").strip().lower()
    findings: list[dict] = []

    # Eine manuell niedrigere Einstufung darf die automatische Erkennung nie
    # aushebeln. Höherstufungen sind erlaubt.
    if declared and declared not in RISK_ORDER:
        findings.append(_finding("E01", f"unbekannte Risikoklasse „{declared}“"))
    elif declared and RISK_ORDER.get(declared, -1) < RISK_ORDER[risk]:
        findings.append(_finding(
            "E02", f"Risikoklasse darf nicht von {risk} auf {declared} herabgestuft werden"))

    # Ein alter, als aktuell bezeichneter Artikelstand ist unabhängig von der
    # Risikoklasse ein Publikationsfehler (realer Fund: „Stand 2024“ in einem
    # 2026 erzeugten Entwurf). Quellenjahre und historische Vergleiche werden
    # absichtlich nicht erfasst – nur explizite Stand-Kennzeichnungen.
    for match in re.finditer(r"(?i)(?:\bStand\s*:?\s*|\(Stand\s+)(20\d{2})\b", body):
        year = int(match.group(1))
        if year < today.year:
            findings.append(_finding(
                "E16", f"veralteter Artikelstand {year} in einem Beitrag aus {today.year}"))
            break

    if risk != RISK_HIGH:
        return {
            "risk": risk, "declared_risk": declared or None, "status": status or None,
            "approved": False, "blocking": bool(findings), "findings": findings,
        }

    if not review:
        findings.append(_finding(
            "E03", "Hochrisiko-Thema ohne redaktionelle_pruefung (Freigabe fehlt)"))
        return {
            "risk": risk, "declared_risk": None, "status": None,
            "approved": False, "blocking": True, "findings": findings,
        }

    if declared != RISK_HIGH:
        findings.append(_finding("E04", "redaktionelle_pruefung.risikoklasse muss „hoch“ sein"))
    if status not in APPROVED_STATUSES:
        findings.append(_finding("E05", "Status ist nicht „freigegeben“"))
    if not str(fm.get("author") or "").strip():
        findings.append(_finding("E06", "Autor fehlt"))

    reviewer = review.get("pruefer") or {}
    if not isinstance(reviewer, dict):
        reviewer = {}
    reviewer_name = str(reviewer.get("name") or "").strip()
    reviewer_role = str(reviewer.get("rolle") or "").strip()
    reviewer_type = str(reviewer.get("typ") or "").strip().lower()
    if not reviewer_name or not reviewer_role:
        findings.append(_finding("E07", "Prüfername und konkrete Prüferrolle fehlen"))
    if reviewer_type not in ALLOWED_REVIEWER_TYPES:
        findings.append(_finding(
            "E08", "Prüfertyp muss fachpruefer oder redaktion-mit-externer-belegkette sein"))

    reviewed_at = _date(review.get("pruefdatum"))
    next_review = _date(review.get("naechste_pruefung"))
    if not reviewed_at:
        findings.append(_finding("E09", "gültiges Prüfdatum fehlt"))
    elif reviewed_at > today:
        findings.append(_finding("E09", "Prüfdatum liegt in der Zukunft"))
    elif (today - reviewed_at).days > REVIEW_INTERVAL_DAYS:
        findings.append(_finding(
            "E09", f"Prüfung ist älter als {REVIEW_INTERVAL_DAYS} Tage"))
    if not next_review:
        findings.append(_finding("E10", "nächster Review-Termin fehlt"))
    elif reviewed_at and next_review <= reviewed_at:
        findings.append(_finding("E10", "nächster Review muss nach dem Prüfdatum liegen"))
    elif reviewed_at and (next_review - reviewed_at).days > REVIEW_INTERVAL_DAYS:
        findings.append(_finding(
            "E10", f"Review-Intervall überschreitet {REVIEW_INTERVAL_DAYS} Tage"))
    elif next_review < today:
        findings.append(_finding("E10", "nächster Review-Termin ist überfällig"))

    reason = str(review.get("aenderungsgrund") or "").strip()
    if len(reason) < 10:
        findings.append(_finding("E11", "Änderungsgrund fehlt oder ist nicht aussagekräftig"))

    sources = fm.get("quellen") or []
    if not isinstance(sources, list):
        sources = []
    valid_source_ids: set[str] = set()
    ranks: list[int] = []
    if len(sources) < MIN_SOURCES_HIGH:
        findings.append(_finding(
            "E12", f"sichtbare Belegkette braucht mindestens {MIN_SOURCES_HIGH} Quellen"))
    for pos, source in enumerate(sources, 1):
        if not isinstance(source, dict):
            findings.append(_finding("E12", f"Quelle {pos} ist kein strukturierter Eintrag"))
            continue
        sid = str(source.get("id") or "").strip()
        url = str(source.get("url") or "").strip()
        if not sid or sid in valid_source_ids:
            findings.append(_finding("E12", f"Quelle {pos}: eindeutige id fehlt"))
        else:
            valid_source_ids.add(sid)
        if not str(source.get("titel") or "").strip() or not str(source.get("herausgeber") or "").strip():
            findings.append(_finding("E12", f"Quelle {pos}: Titel oder Herausgeber fehlt"))
        if not url.startswith("https://"):
            findings.append(_finding("E12", f"Quelle {pos}: nur HTTPS-Quellen sind zulässig"))
        if any(_domain(url) == d or _domain(url).endswith("." + d) for d in AFFILIATE_DOMAINS):
            findings.append(_finding("E12", f"Quelle {pos}: Affiliate-Partner ist kein Beleg"))
        rank = _source_rank(url)
        if rank is None:
            findings.append(_finding("E12", f"Quelle {pos}: Domain steht nicht auf der Beleg-Allowlist"))
        else:
            ranks.append(rank)
        source_date = _date(source.get("datum"))
        if not source_date:
            findings.append(_finding("E12", f"Quelle {pos}: Veröffentlichungs-/Abrufdatum fehlt"))
        elif source_date > today:
            findings.append(_finding("E12", f"Quelle {pos}: Datum liegt in der Zukunft"))
    if sources and not any(rank <= 2 for rank in ranks):
        findings.append(_finding("E12", "mindestens eine Quelle muss Rang 1 oder 2 haben"))

    # Auch nichtnumerische Kernaussagen brauchen eine sichtbare Zuordnung:
    # exakter Textanker → dokumentiertes Prüfergebnis → Quellen-IDs. So kann ein
    # pauschaler Satz über Zinsbindung, Eigenkapital oder Banken nicht hinter
    # zwei allgemeinen Quellen in der Linkliste verschwinden.
    reviewed_claims = review.get("gepruefte_aussagen") or []
    if not isinstance(reviewed_claims, list) or not reviewed_claims:
        findings.append(_finding(
            "E18", "Liste der geprüften Kernaussagen mit Textankern fehlt"))
        reviewed_claims = []
    claim_anchors: list[str] = []
    for pos, claim in enumerate(reviewed_claims, 1):
        if not isinstance(claim, dict):
            findings.append(_finding("E18", f"geprüfte Aussage {pos} ist kein strukturierter Eintrag"))
            continue
        anchor = str(claim.get("textanker") or "").strip()
        check = str(claim.get("pruefung") or "").strip()
        refs = claim.get("quellen") or []
        if isinstance(refs, str):
            refs = [refs]
        if len(anchor) < MIN_ANCHOR_LENGTH:
            findings.append(_finding(
                "E18", f"geprüfte Aussage {pos}: eindeutiger Textanker fehlt/ist zu kurz"))
        elif anchor.casefold() not in body.casefold():
            findings.append(_finding(
                "E18", f"geprüfte Aussage {pos}: Textanker kommt im Artikel nicht vor"))
        else:
            claim_anchors.append(anchor.casefold())
        if len(check) < 10:
            findings.append(_finding(
                "E18", f"geprüfte Aussage {pos}: konkretes Prüfergebnis fehlt"))
        if not refs or any(str(ref) not in valid_source_ids for ref in refs):
            findings.append(_finding(
                "E18", f"geprüfte Aussage {pos}: Quellenreferenz fehlt oder ist unbekannt"))

    sentences = _body_sentences(body)
    for sentence in sentences:
        if any(pattern.search(sentence) for pattern in BLANKET_CLAIM_PATTERNS):
            folded = sentence.casefold()
            if not any(anchor in folded for anchor in claim_anchors):
                findings.append(_finding(
                    "E18", "pauschale/entscheidungsrelevante Aussage ohne geprüften "
                    f"Textanker: „{_short(sentence)}“"))

    checked = review.get("gepruefte_zahlen") or []
    if not isinstance(checked, list) or not checked:
        findings.append(_finding("E13", "Liste der geprüften Zahlen/Rechenannahmen fehlt"))
        checked = []
    has_calculation = False
    figure_anchors: list[str] = []
    values_by_claim: dict[str, set[str]] = {}
    for pos, claim in enumerate(checked, 1):
        if not isinstance(claim, dict):
            findings.append(_finding("E13", f"geprüfte Zahl {pos} ist kein strukturierter Eintrag"))
            continue
        label = str(claim.get("aussage") or "").strip()
        value = str(claim.get("wert") or "").strip()
        anchor = str(claim.get("fundstelle") or "").strip()
        check = str(claim.get("pruefung") or "").strip()
        consistency = str(claim.get("konsistenzpruefung") or "").strip()
        if not label:
            findings.append(_finding("E13", f"geprüfte Zahl {pos}: Aussage fehlt"))
        if not value:
            findings.append(_finding("E13", f"geprüfte Zahl {pos}: Wert/Annahme fehlt"))
        if len(check) < 10:
            findings.append(_finding("E13", f"geprüfte Zahl {pos}: konkretes Prüfergebnis fehlt"))
        if len(consistency) < 10:
            findings.append(_finding(
                "E14", f"geprüfte Zahl {pos}: dokumentierte Konsistenzprüfung fehlt"))
        if len(anchor) < MIN_ANCHOR_LENGTH:
            findings.append(_finding(
                "E13", f"geprüfte Zahl {pos}: eindeutige Fundstelle fehlt/ist zu kurz"))
        elif anchor.casefold() not in body.casefold():
            findings.append(_finding(
                "E13", f"geprüfte Zahl {pos}: Fundstelle kommt im Artikel nicht vor"))
        else:
            figure_anchors.append(anchor.casefold())
        refs = claim.get("quellen") or []
        if isinstance(refs, str):
            refs = [refs]
        if not refs or any(str(ref) not in valid_source_ids for ref in refs):
            findings.append(_finding(
                "E13", f"geprüfte Zahl {pos}: Quellenreferenz fehlt oder ist unbekannt"))
        if str(claim.get("rechenweg") or "").strip():
            has_calculation = True
        if label and value:
            values_by_claim.setdefault(label.casefold(), set()).add(value.casefold())

    for label, values in values_by_claim.items():
        if len(values) > 1:
            findings.append(_finding(
                "E14", f"widersprüchliche geprüfte Werte für „{_short(label)}“: "
                + ", ".join(sorted(values))))

    # Jede materielle Zahl im Artikel (Euro/Prozent) muss über eine exakte
    # Fundstelle im Zahlenprotokoll erfasst sein. Ein allgemeines „geprüft“
    # neben einer Quellenliste reicht ausdrücklich nicht.
    for sentence in sentences:
        for number in MATERIAL_NUMBER_RE.findall(sentence):
            folded = sentence.casefold()
            token = number.casefold().strip()
            if not any(anchor in folded and token in anchor for anchor in figure_anchors):
                findings.append(_finding(
                    "E19", f"Zahl ohne Fundstelle im Prüfprotokoll: „{_short(sentence)}“"))

    if re.search(r"\bRechenbeispiel\b", body, re.I) and not has_calculation:
        findings.append(_finding(
            "E14", "Artikel enthält ein Rechenbeispiel, aber keinen dokumentierten Rechenweg"))

    # Ein Hochrisiko-Artikel darf nicht zuerst verkaufen und später erklären.
    cta_match = re.search(r"\]\(\s*/go/[\w-]+/", body, re.I)
    if cta_match:
        before = body[:cta_match.start()]
        word_count = len(re.findall(r"\b[\wÄÖÜäöüß-]+\b", before))
        h2_count = len(re.findall(r"(?m)^##\s+", before))
        if word_count < MIN_WORDS_BEFORE_AFFILIATE or h2_count < MIN_H2_BEFORE_AFFILIATE:
            findings.append(_finding(
                "E15", "Affiliate-CTA steht vor ausreichender fachlicher Grundlage "
                f"({word_count}/{MIN_WORDS_BEFORE_AFFILIATE} Wörter, "
                f"{h2_count}/{MIN_H2_BEFORE_AFFILIATE} H2 davor)"))

    expected_hash = content_fingerprint(fm, body)
    sealed_hash = str(review.get("inhalt_sha256") or "").strip().lower()
    if not ignore_hash and sealed_hash != expected_hash:
        detail = ("Freigabe-Hash fehlt" if not sealed_hash else
                  "Text/Quellen wurden nach der Freigabe verändert")
        findings.append(_finding("E17", detail))

    approved = status in APPROVED_STATUSES and not findings
    return {
        "risk": risk,
        "declared_risk": declared or None,
        "status": status or None,
        "approved": approved,
        "blocking": bool(findings),
        "findings": findings,
        "fingerprint": expected_hash,
    }


def evaluate_path(path: Path | str, *, today: dt.date | None = None) -> dict:
    path = Path(path)
    try:
        fm, body, _ = load_article(path)
        result = validate_article(fm, body, today=today)
    except (OSError, ParseError) as exc:
        result = {
            "risk": "unbekannt", "declared_risk": None, "status": None,
            "approved": False, "blocking": True,
            "findings": [_finding("E00", str(exc))],
        }
    result["path"] = str(path)
    result["slug"] = path.parent.name if path.name == "index.md" else path.stem
    return result


def _set_review_hash(raw: str, digest: str) -> str:
    lines = raw.splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines)
                  if line.startswith("redaktionelle_pruefung:")), None)
    if start is None:
        raise ParseError("redaktionelle_pruefung fehlt; nichts zu versiegeln")
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].strip() == "---" or (lines[i].strip() and not lines[i].startswith((" ", "\t"))):
            end = i
            break
    existing = next((i for i in range(start + 1, end)
                     if re.match(r"^  inhalt_sha256:\s*", lines[i])), None)
    line = f'  inhalt_sha256: "{digest}"\n'
    if existing is not None:
        lines[existing] = line
    else:
        # Direkt nach status, damit Status und Siegel zusammen lesbar bleiben.
        anchor = next((i + 1 for i in range(start + 1, end)
                       if re.match(r"^  status:\s*", lines[i])), start + 1)
        lines.insert(anchor, line)
    return "".join(lines)


def seal(path: Path | str, *, today: dt.date | None = None) -> dict:
    """Versiegelt nur eine vollständig ausgefüllte Freigabe; kein Auto-Approve."""
    path = Path(path)
    fm, body, raw = load_article(path)
    preflight = validate_article(fm, body, today=today, ignore_hash=True)
    blockers = [f for f in preflight["findings"] if f["code"] != "E17"]
    if blockers:
        details = "; ".join(f"{f['code']} {f['detail']}" for f in blockers)
        raise ParseError(f"Freigabe unvollständig; Siegel verweigert: {details}")
    digest = content_fingerprint(fm, body)
    new_raw = _set_review_hash(raw, digest)
    path.write_text(new_raw, encoding="utf-8")
    checked = evaluate_path(path, today=today)
    if checked.get("blocking"):
        path.write_text(raw, encoding="utf-8")
        raise ParseError("Siegel-Nachprüfung fehlgeschlagen; Datei wurde zurückgesetzt")

    review = fm.get("redaktionelle_pruefung") or {}
    reviewer = review.get("pruefer") or {}
    event = {
        "sealed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "path": str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path),
        "sha256": digest,
        "risk": checked.get("risk"),
        "reviewed_at": _iso(review.get("pruefdatum")),
        "next_review": _iso(review.get("naechste_pruefung")),
        "reviewer": reviewer.get("name"),
        "reviewer_role": reviewer.get("rolle"),
        "reason": review.get("aenderungsgrund"),
    }
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return checked


def all_post_paths() -> list[Path]:
    return sorted(POSTS.glob("*/index.md"))


def _draft_from_path(path: Path) -> bool:
    try:
        fm, _, _ = load_article(path)
        return bool(fm.get("draft"))
    except Exception:  # noqa: BLE001 - Report markiert unlesbare Datei
        return False


def write_report(results: list[dict], *, today: dt.date | None = None) -> None:
    today = today or dt.date.today()
    rows = []
    queue = []
    for result in results:
        if result.get("risk") != RISK_HIGH and not result.get("findings"):
            continue
        path = Path(result["path"])
        state = "Entwurf" if _draft_from_path(path) else "Live"
        findings = result.get("findings") or []
        status = "freigegeben" if result.get("approved") else "offen"
        rows.append((result["slug"], state, result.get("risk"), status, findings))
        if findings:
            queue.append({
                "slug": result["slug"],
                "path": str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path),
                "state": state.lower(),
                "risk": result.get("risk"),
                "findings": findings,
            })

    high = [r for r in results if r.get("risk") == RISK_HIGH]
    approved = [r for r in high if r.get("approved")]
    live_open = [q for q in queue if q["state"] == "live"]
    draft_open = [q for q in queue if q["state"] == "entwurf"]
    lines = [
        "# Redaktionelle YMYL-Prüfung",
        "",
        f"**Stand:** {today.isoformat()} · **Gate:** `scripts/editorial_review_gate.py`",
        "",
        "> Ein Qualitäts-Score ist keine fachliche Freigabe. Hochrisiko-Inhalte gehen",
        "> nur mit benanntem Prüfer, sichtbarer Belegkette, verankerten Aussagen und Zahlen,",
        "> Prüfdatum, Änderungsgrund, Review-Termin und fassungsgebundenem Hash live.",
        "",
        "## Überblick",
        "",
        f"- Hochrisiko-Artikel: **{len(high)}**",
        f"- Vollständig freigegeben: **{len(approved)}**",
        f"- Offene Live-Reviews: **{len(live_open)}**",
        f"- Offene Entwurfs-Reviews: **{len(draft_open)}**",
        "",
        "## Prüfliste",
        "",
        "| Artikel | Zustand | Risiko | Freigabe | Befund |",
        "|---|---|---|---|---|",
    ]
    for slug, state, risk, status, findings in rows:
        detail = "; ".join(f"{f['code']} {f['detail']}" for f in findings[:3]) or "–"
        lines.append(f"| `{slug}` | {state} | {risk} | {status} | {detail} |")
    if not rows:
        lines.append("| – | – | – | – | Keine Befunde |")
    lines += [
        "",
        "## Freigabeablauf",
        "",
        "1. Primär-/Verbraucherquellen im Frontmatter unter `quellen` mit IDs erfassen.",
        "2. Kernaussagen mit exaktem Textanker unter `gepruefte_aussagen` dokumentieren.",
        "3. Zahlen mit Fundstelle, Konsistenzprüfung und Rechenweg unter `gepruefte_zahlen` erfassen.",
        "4. Prüfer, Rolle, Prüfdatum, Änderungsgrund und nächsten Review-Termin eintragen.",
        "5. `status: freigegeben` setzen und `python3 scripts/editorial_review_gate.py --seal --file <pfad>` ausführen.",
        "6. Jede spätere Text-, Protokoll- oder Quellenänderung bricht das Siegel.",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    QUEUE.write_text(json.dumps({
        "generated_at": today.isoformat(),
        "high_risk_total": len(high),
        "approved": len(approved),
        "open_live": len(live_open),
        "open_drafts": len(draft_open),
        "items": queue,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def selftest() -> list[str]:
    errors: list[str] = []

    def expect(name: str, condition: bool):
        if not condition:
            errors.append(name)

    expect("Baufinanzierung ist hoch", classify_text("Hauskauf finanzieren: Baufinanzierung") == RISK_HIGH)
    expect("Altersvorsorge ist hoch", classify_text("ETF für die Altersvorsorge") == RISK_HIGH)
    expect("Ratenkredit ist hoch", classify_text("Ratenkredit umschulden") == RISK_HIGH)
    expect("Kreditkarte ist nicht durch Kredit hoch", classify_text("Kreditkarte vergleichen") != RISK_HIGH)
    expect("Versicherungs-Pillar ist hoch", classify_text("Schutz", "versicherungen") == RISK_HIGH)
    expect("DSL ist standard", classify_text("WLAN-Reichweite verbessern") == RISK_STANDARD)

    today = dt.date(2026, 10, 2)
    body = ("Einordnung " * 650 + "\n\nDas Ergebnis hängt von individuellen Annahmen ab.\n\n"
            "## Kriterien\n\nText\n\n## Risiken\n\n"
            "**Rechenbeispiel:** Die Modellrate nutzt 10.000 Euro als freie Annahme.\n\n"
            "[Vergleich](/go/kredit/)\n")
    fm = {
        "title": "Ratenkredit: Modellrechnung sauber prüfen",
        "description": "Ein sachlicher Kredit-Ratgeber.",
        "author": "Frank Hartung",
        "quellen": [
            {"id": "Q1", "titel": "Verbraucherinformation", "url": "https://www.bafin.de/a",
             "herausgeber": "BaFin", "datum": "2026-09-20"},
            {"id": "Q2", "titel": "Gesetz", "url": "https://www.gesetze-im-internet.de/b",
             "herausgeber": "BMJ", "datum": "2026-09-21"},
        ],
        "redaktionelle_pruefung": {
            "risikoklasse": "hoch", "status": "freigegeben",
            "pruefer": {"name": "Redaktion", "rolle": "Faktenprüfung anhand Primärquellen",
                         "typ": "redaktion-mit-externer-belegkette"},
            "pruefdatum": "2026-10-02", "naechste_pruefung": "2026-11-16",
            "aenderungsgrund": "Erstprüfung vor Veröffentlichung",
            "gepruefte_aussagen": [{
                "textanker": "Das Ergebnis hängt von individuellen Annahmen ab.",
                "pruefung": "Als fallabhängige Einordnung bestätigt",
                "quellen": ["Q1", "Q2"],
            }],
            "gepruefte_zahlen": [{
                "aussage": "Modellrate", "wert": "10.000 Euro",
                "fundstelle": "Die Modellrate nutzt 10.000 Euro als freie Annahme.",
                "pruefung": "Annahmen und Formel nachgerechnet",
                "konsistenzpruefung": "Fließtext und Rechenweg stimmen überein",
                "rechenweg": "Kapital mal Zinssatz",
                "quellen": ["Q1", "Q2"],
            }],
        },
    }
    fm["redaktionelle_pruefung"]["inhalt_sha256"] = content_fingerprint(fm, body)
    ok = validate_article(copy.deepcopy(fm), body, today=today)
    expect("vollständige Freigabe besteht", not ok["findings"] and ok["approved"])
    drift = validate_article(copy.deepcopy(fm), body + "Geändert.", today=today)
    expect("Textänderung bricht Hash", any(f["code"] == "E17" for f in drift["findings"]))
    early = validate_article(copy.deepcopy(fm), "[Vergleich](/go/kredit/)\n" + body, today=today)
    expect("früher CTA blockiert", any(f["code"] == "E15" for f in early["findings"]))
    stale = validate_article(copy.deepcopy(fm), body + "\n(Stand 2024)\n", today=today)
    expect("alter Stand blockiert", any(f["code"] == "E16" for f in stale["findings"]))
    blanket = validate_article(
        copy.deepcopy(fm), body + "\nBanken akzeptieren immer jedes Einkommen.\n", today=today)
    expect("pauschale Bankaussage blockiert", any(f["code"] == "E18" for f in blanket["findings"]))
    number = validate_article(
        copy.deepcopy(fm), body + "\nDie Zusatzgebühr beträgt 500 Euro.\n", today=today)
    expect("unprotokollierte Zahl blockiert", any(f["code"] == "E19" for f in number["findings"]))
    contradiction_fm = copy.deepcopy(fm)
    contradiction = copy.deepcopy(contradiction_fm["redaktionelle_pruefung"]["gepruefte_zahlen"][0])
    contradiction["wert"] = "20.000 Euro"
    contradiction_fm["redaktionelle_pruefung"]["gepruefte_zahlen"].append(contradiction)
    contradiction_fm["redaktionelle_pruefung"]["inhalt_sha256"] = content_fingerprint(
        contradiction_fm, body)
    contradicted = validate_article(contradiction_fm, body, today=today)
    expect("widersprüchliche Werte blockieren", any(
        f["code"] == "E14" for f in contradicted["findings"]))
    missing = validate_article({"title": "Baufinanzierung", "author": "A"}, "Text", today=today)
    expect("fehlende Freigabe blockiert", missing["blocking"] and missing["risk"] == RISK_HIGH)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", action="append", default=[], help="Artikelpfad (mehrfach möglich)")
    parser.add_argument("--all", action="store_true", help="alle Posts prüfen")
    parser.add_argument("--published", action="store_true",
                        help="nur veröffentlichte Posts prüfen (hartes Deploy-Gate)")
    parser.add_argument("--strict", action="store_true", help="Exit 1 bei Befunden")
    parser.add_argument("--json", action="store_true", help="Ergebnis als JSON")
    parser.add_argument("--report", action="store_true", help="Report und Queue schreiben")
    parser.add_argument("--seal", action="store_true", help="vollständige Freigabe fassungsgebunden versiegeln")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)

    if args.selftest:
        errors = selftest()
        if errors:
            print("🛑 Redaktionelle-Prüfung-Selbsttest fehlgeschlagen:")
            for error in errors:
                print("  -", error)
            return 2
        print("✅ Redaktionelle-Prüfung-Selbsttest bestanden (Risiko, Aussagen, Zahlen, Widersprüche, Hash, CTA, Frische).")
        return 0

    paths = [Path(p) if Path(p).is_absolute() else ROOT / p for p in args.file]
    if args.published:
        paths = [path for path in all_post_paths() if not _draft_from_path(path)]
    elif args.all or not paths:
        paths = all_post_paths()
    if args.seal:
        if len(paths) != 1:
            print("🛑 --seal braucht genau einen --file-Pfad.", file=sys.stderr)
            return 2
        try:
            result = seal(paths[0])
        except (OSError, ParseError) as exc:
            print(f"🛑 Freigabe nicht versiegelt: {exc}", file=sys.stderr)
            return 2
        print(f"✅ Freigabe versiegelt: {result['slug']} · {result.get('fingerprint')}")
        return 0

    results = [evaluate_path(path) for path in paths]
    if args.report:
        write_report(results)
    if args.json:
        print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
    else:
        high = sum(1 for r in results if r.get("risk") == RISK_HIGH)
        blocked = [r for r in results if r.get("blocking")]
        approved = sum(1 for r in results if r.get("approved"))
        print(f"Redaktionelle Prüfung: {len(results)} Artikel · {high} Hochrisiko · "
              f"{approved} freigegeben · {len(blocked)} blockiert")
        for result in blocked:
            print(f"  🛑 {result['slug']} ({result.get('risk')}):")
            for finding in result.get("findings", []):
                print(f"     - {finding['code']}: {finding['detail']}")
    return 1 if args.strict and any(r.get("blocking") for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
