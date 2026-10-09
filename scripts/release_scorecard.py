#!/usr/bin/env python3
# ============================================================
#  RELEASE-SCORECARD – die Produktionswahrheit in einer Ansicht
#  (Auftrag Frank, 03.10.2026, Befund 10: „Ich würde daraus eine
#   einzige sichtbare Release-Scorecard machen – bitte dauerhaft
#   auf Highend-Level einer Profi-Agentur beheben.“)
#
#  WARUM DIESE WACHE
#  -----------------
#  Das Repository besitzt viele Gates, Reports und Automationen –
#  das ist Stärke UND Risiko: Niemand konnte auf einen Blick sagen
#  (1) welche Checks veröffentlichen blockieren, (2) welche nur
#  warnen, (3) wer bei fachlichen Konflikten entscheidet, (4) was
#  bei falschen Positivmeldungen passiert, (5) wie ein Artikel
#  fachlich freigegeben wird und (6) ob die VERÖFFENTLICHTE Version
#  wirklich die geprüfte ist. Diese Scorecard beantwortet alle sechs
#  Fragen an EINEM Ort, pro Artikel, mit acht Dimensionen:
#
#    Technik · Quellen · Faktenalter · Affiliate-Integrität ·
#    Redundanz · YMYL-Risiko · menschliche Freigabe ·
#    nächste Überprüfung
#
#  ARCHITEKTUR-VERTRAG (keine zweite Messregel, Lektion #521)
#  ----------------------------------------------------------
#  Die Scorecard ist eine SICHT, kein zweites Gate: Sie misst über
#  die Collector-Funktionen des Publish-Gates (scripts/publish_gate.py)
#  und die Prüffunktionen der Fachwachen (editorial_review_gate,
#  faktenfrische). Die deklarative Wahrheit
#  (blockiert/warnung, Besitz, Eskalation) steht in der menschlich
#  kuratierten SSOT data/release_scorecard.yaml; die Wache
#  scripts/governance_contract.py erzwingt mit Regel C19, dass jede
#  harte Gate-Familie dort deklariert ist.
#
#  Beweisläufe schreiben nichts (C15): Diese Wache heilt NICHT. Sie
#  setzt publish_gate.DRY_RUN=True und ruft affiliate_intent_guard
#  ohne Heilung auf – die einzigen Schreibzugriffe sind Scorecard-
#  Artefakte (Report, Zustand, Historie, Audit-Log).
#
#  Exit-Codes sind Vertrag:
#    0 = alle Artikel im Scope freigabe-reif (Warnungen erlaubt)
#    1 = mindestens ein Artikel im Scope hat blockierende Funde
#    2 = Werkzeug-/Konfigurationsfehler (fail-closed: Ein nicht
#        führbarer Beweis ist niemals „bestanden“)
#
#  Aufrufe:
#    python3 scripts/release_scorecard.py                 # Live-Bestand (Report)
#    python3 scripts/release_scorecard.py --live --streng # Bestand rot = Exit 1 (Tageswache)
#    python3 scripts/release_scorecard.py --kandidaten    # heutige Live-Kandidaten, hart (Deploy)
#    python3 scripts/release_scorecard.py --slug <slug>   # Einzelnachweis (schreibt nichts)
#    python3 scripts/release_scorecard.py --json          # maschinenlesbar nach stdout
#    python3 scripts/release_scorecard.py --selftest      # Sabotage-Proben
# ============================================================
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
POSTS = ROOT / "content" / "posts"
SSOT_PATH = ROOT / "data" / "release_scorecard.yaml"
REPORT_PATH = ROOT / "RELEASE-SCORECARD.md"
STATE_PATH = ROOT / "data" / "release_scorecard_state.json"
HISTORY_PATH = ROOT / "data" / "release_scorecard_history.jsonl"

EXIT_OK = 0
EXIT_BLOCKIERT = 1
EXIT_WERKZEUGFEHLER = 2

# Die acht Zeilen der Scorecard – Reihenfolge ist der Vertrag mit dem Report.
DIMENSIONS_FOLGE = (
    "technik", "quellen", "faktenalter", "affiliate", "redundanz",
    "ymyl", "freigabe", "revision",
)

# Status-Werte (Anzeige) und ihre Schärfe für worst-of-Bewertung.
STATUS_FOLGE = ("bestanden", "nicht erforderlich", "warnung",
                "nicht beweisbar", "blockiert")
URTEIL_FOLGE = ("freigabe-reif", "warnung", "nicht beweisbar", "blockiert")

# Diese Checks gelten ausnahmslos – ein Falsch-Alarm wird hier nie per
# Ausnahme weggebucht: Siegel-Bindung und Build-Beweis sind die Grundlage
# der Antwort auf Frage 6 („wurde die veröffentlichte Version geprüft?“).
NICHT_AUSNEHMBAR = frozenset({"M2-siegel-bindung", "T7-render-beweis"})

# Editorial-Befundcodes (editorial_review_gate.py, E00–E19) → Check-ID der
# SSOT. EINGEFROREN: Ein neuer E-Code ohne Mapping ist ein Fehler, nie Still.
ERG_CODE_ZU_CHECK = {
    "E00": "T0-artikel-lesbar",
    "E01": "Y1-risikoklasse",
    "E02": "Y1-risikoklasse",
    "E03": "M1-fachliche-freigabe",
    "E04": "M1-fachliche-freigabe",
    "E05": "M1-fachliche-freigabe",
    "E06": "M1-fachliche-freigabe",
    "E07": "M1-fachliche-freigabe",
    "E08": "M1-fachliche-freigabe",
    "E09": "F3-pruefdatum",
    "E10": "N1-naechste-pruefung",
    "E11": "M1-fachliche-freigabe",
    "E12": "Q1-belegkette",
    "E13": "Y2-pruefprotokoll",
    "E14": "Y2-pruefprotokoll",
    "E15": "Y2-pruefprotokoll",
    "E16": "F2-stand-kennzeichnung",
    "E17": "M2-siegel-bindung",
    "E18": "Y2-pruefprotokoll",
    "E19": "Y2-pruefprotokoll",
}

# Die harten Gate-Familien des Publish-Gates (scripts/publish_gate.py, main()).
# Jede MUSS in der SSOT als wirkung: blockiert deklariert sein – sonst wäre
# die Scorecard eine Sicht, die blockierende Gates verschweigt (C19).
# (quelle_muster muss im `quelle`-Feld des deklarierten Checks vorkommen.)
PUBLISH_GATE_HART_FAMILIEN = {
    "T1-zeichenlaenge": "check_length.py",
    "T2-seo-audit": "seo_audit.py",
    "F1-faktenfrische": "faktenfrische.py",
    "T3-titel-r5": "check_titles.py",
    "T4-keyword-score": "keyword_optimizer.py",
    "T5-lesbarkeit": "readability_check.py",
    "T6-textverstaendnis": "textverstaendnis_guard.py",
    "A1-link-integritaet": "affiliate_integrity_gate.py",
    "A2-intent": "affiliate_intent_guard.py",
    "A3-offenlegung": "offenlegung_gate.py",
    "A4-profi-check": "affiliate_profi_check.py",
    "M1-fachliche-freigabe": "editorial_review_gate.py",
    "M2-siegel-bindung": "editorial_review_gate.py",
    "RD1-duplikate": "duplikat_guard.py",
}

AUSNAHME_PFLICHTFELDER = ("slug", "check", "begruendung", "gueltig_bis", "entschieden_von")


class KonfigurationsFehler(RuntimeError):
    """SSOT oder Ausnahmen sind ungültig – fail-closed (Exit 2)."""


# ============================================================
#  Import-Hygiene: Gate-Module lesen teils sys.argv beim Import
#  (z. B. affiliate_intent_guard: ARGS = sys.argv[1:]). Unsere
#  eigenen Flags dürfen dort nie ankommen.
# ============================================================
@contextmanager
def _neutrale_argv():
    alt = sys.argv
    sys.argv = [alt[0]]
    try:
        yield
    finally:
        sys.argv = alt


def _importiere_gate_module(name: str):
    if SCRIPTS not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    with _neutrale_argv():
        return __import__(name)


# ============================================================
#  SSOT laden und prüfen
# ============================================================
def ssot_laden(pfad: Path = SSOT_PATH) -> dict:
    try:
        import yaml  # noqa: PLC0415 – erst nach Pfad-Fix importierbar
    except ImportError as exc:
        raise KonfigurationsFehler(f"PyYAML fehlt: {exc}") from exc
    try:
        ssot = yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}
    except OSError as exc:
        raise KonfigurationsFehler(f"SSOT nicht lesbar ({pfad}): {exc}") from exc
    except yaml.YAMLError as exc:
        raise KonfigurationsFehler(f"SSOT ist kein gültiges YAML: {exc}") from exc

    fehler = ssot_pruefen(ssot)
    if fehler:
        raise KonfigurationsFehler(
            "SSOT data/release_scorecard.yaml ist unvollständig: "
            + "; ".join(fehler))
    return ssot


def ssot_pruefen(ssot: dict) -> list[str]:
    """Strukturprüfung der SSOT – reine Funktion (Selbsttest ST1)."""
    fehler: list[str] = []
    dimensionen = ssot.get("dimensionen") or {}
    for dim in DIMENSIONS_FOLGE:
        if dim not in dimensionen:
            fehler.append(f"Dimension `{dim}` fehlt")
    checks = ssot.get("checks") or []
    register: dict[str, dict] = {}
    for check in checks:
        if not isinstance(check, dict):
            fehler.append("Check ist kein Mapping")
            continue
        cid = str(check.get("id") or "").strip()
        if not cid:
            fehler.append("Check ohne id")
            continue
        if cid in register:
            fehler.append(f"Check-ID `{cid}` doppelt")
        register[cid] = check
        if check.get("dimension") not in DIMENSIONS_FOLGE:
            fehler.append(f"Check `{cid}`: unbekannte Dimension")
        if check.get("wirkung") not in ("blockiert", "warnung"):
            fehler.append(f"Check `{cid}`: wirkung muss blockiert|warnung sein")
        if check.get("entscheidung") not in ("auto", "human"):
            fehler.append(f"Check `{cid}`: entscheidung muss auto|human sein")
        if not str(check.get("quelle") or "").strip():
            fehler.append(f"Check `{cid}`: quelle fehlt")
    for dim in DIMENSIONS_FOLGE:
        if not any(c.get("dimension") == dim for c in checks if isinstance(c, dict)):
            fehler.append(f"Dimension `{dim}` hat keinen Check")
    # Deckung mit dem Publish-Gate (C19-Spiegel, Selbsttest ST2)
    for cid, muste in PUBLISH_GATE_HART_FAMILIEN.items():
        check = register.get(cid)
        if check is None:
            fehler.append(f"Publish-Gate-Familie `{cid}` ist nicht deklariert")
        elif check.get("wirkung") != "blockiert":
            fehler.append(f"Publish-Gate-Familie `{cid}` muss blockierend sein")
        elif muste not in str(check.get("quelle") or ""):
            fehler.append(f"Check `{cid}`: quelle nennt `{muste}` nicht")
    # Nicht ausnehmbare Checks müssen existieren
    for cid in NICHT_AUSNEHMBAR:
        if cid not in register:
            fehler.append(f"Nicht-ausnehmbarer Check `{cid}` fehlt in der SSOT")
    return fehler


def check_register(ssot: dict) -> dict[str, dict]:
    return {str(c.get("id")): c for c in ssot.get("checks") or []
            if isinstance(c, dict) and c.get("id")}


# ============================================================
#  Ausnahmen (Falsch-Alarm-Protokoll, Frage 4)
# ============================================================
def ausnahme_fehler(eintrag: dict) -> list[str]:
    """Pflichtfelder und Formate einer Ausnahme prüfen (reine Funktion)."""
    fehler: list[str] = []
    if not isinstance(eintrag, dict):
        return ["Ausnahme ist kein Mapping"]
    for feld in AUSNAHME_PFLICHTFELDER:
        wert = eintrag.get(feld)
        if not isinstance(wert, str) or not wert.strip():
            fehler.append(f"Ausnahme ohne {feld}")
    if isinstance(eintrag.get("begruendung"), str) and len(eintrag.get("begruendung", "").strip()) < 15:
        fehler.append("Ausnahme-Begründung ist nicht aussagekräftig (<15 Zeichen)")
    gueltig = eintrag.get("gueltig_bis")
    if isinstance(gueltig, str):
        try:
            dt.date.fromisoformat(gueltig.strip())
        except ValueError:
            fehler.append(f"Ausnahme gueltig_bis `{gueltig}` ist kein ISO-Datum")
    check = str(eintrag.get("check") or "").strip()
    if check and check in NICHT_AUSNEHMBAR:
        fehler.append(f"Ausnahme für nicht-ausnehmbaren Check `{check}` ist unzulässig")
    return fehler


def ausnahmen_aufbereiten(ssot: dict, heute: dt.date) -> tuple[dict, list[dict]]:
    """(aktive {(slug, check): eintrag}, abgelaufene [eintrag]).

    Abgelaufene Ausnahmen werden ignoriert, aber sichtbar zurückgegeben –
    eine stille Verlängerung gibt es nicht (Antwort auf Frage 4).
    """
    aktive: dict[tuple[str, str], dict] = {}
    abgelaufen: list[dict] = []
    for eintrag in ssot.get("ausnahmen") or []:
        fehler = ausnahme_fehler(eintrag)
        if fehler:
            raise KonfigurationsFehler("; ".join(fehler))
        bis = dt.date.fromisoformat(str(eintrag["gueltig_bis"]).strip())
        if bis < heute:
            abgelaufen.append(eintrag)
            continue
        schluessel = (str(eintrag["slug"]).strip(), str(eintrag["check"]).strip())
        aktive[schluessel] = eintrag
    return aktive, abgelaufen


# ============================================================
#  Siegel (Frage 6): Fingerprint über die exakte Quelldatei
# ============================================================
def file_fingerprint(pfad: Path) -> str:
    """SHA-256 über die Artikel-Datei (CRLF-normalisiert) – bindet die
    geprüfte Version an den Nachweis, exakt wie editorial_review_gate
    die Freigabe an die Fassung bindet."""
    text = pfad.read_text(encoding="utf-8")
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def zustand_laden(pfad: Path = STATE_PATH) -> dict:
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def siegel_drift(alt: dict, slug: str, fingerprint: str) -> str:
    """'neu versiegelt' | 'unverändert' | 'geändert – neu geprüft'."""
    vorher = (alt.get("artikel") or {}).get(slug) or {}
    if not vorher.get("sha256"):
        return "neu versiegelt"
    if vorher["sha256"] == fingerprint:
        return "unverändert"
    return "geändert – neu geprüft"


# ============================================================
#  Bestand
# ============================================================
def artikel_pfad(slug: str) -> Path:
    return POSTS / slug / "index.md"


def bestand_aufnehmen() -> tuple[list[str], list[str], dict[str, str]]:
    """(Live-Slugs, Entwurfs-Slugs, {slug: fingerprint})."""
    live, entwuerfe, fingerprints = [], [], {}
    if not POSTS.is_dir():
        return live, entwuerfe, fingerprints
    for pfad in sorted(POSTS.glob("*/index.md")):
        slug = pfad.parent.name
        try:
            fingerprint = file_fingerprint(pfad)
        except OSError:
            continue
        fingerprints[slug] = fingerprint
        raw = pfad.read_text(encoding="utf-8", errors="replace")
        ist_draft = bool(re.search(r"(?m)^draft:\s*true\s*$", raw.split("---", 2)[1]
                                   if raw.startswith("---") and raw.count("---") >= 2 else ""))
        (entwuerfe if ist_draft else live).append(slug)
    return live, entwuerfe, fingerprints


# ============================================================
#  Messung: Collector-Aufrufe (alles reine Beweisläufe)
# ============================================================
def _merke(befunde: dict, slug: str, check_id: str, detail: str) -> None:
    befunde.setdefault(slug, {}).setdefault(check_id, []).append(detail)


def sammle(live_slugs: list[str], heute: dt.date) -> tuple[dict, dict, dict]:
    """Läuft alle Check-Familien über den Live-Bestand.

    Rückgabe: (befunde {slug: {check_id: [details]}},
               tool_fehler {check_id: grund},
               kontext {erg, fakten, render, kandidaten})
    """
    befunde: dict[str, dict[str, list[str]]] = {}
    tool_fehler: dict[str, str] = {}
    kontext: dict = {"kandidaten": [], "render": {}, "erg": {}, "fakten": {}}

    publish_gate = _importiere_gate_module("publish_gate")
    # BEWEISLAUF SCHREIBT NICHTS (C15): Publish-Gate-Kollektoren im
    # Trockenlauf – insbesondere heilt die Intent-Wache hier nicht.
    publish_gate.DRY_RUN = True

    # ---------- Editorial-Review (YMYL, Freigabe, Quellen, Daten) ----------
    erg = _importiere_gate_module("editorial_review_gate")
    for slug in live_slugs:
        ergebnis = erg.evaluate_path(artikel_pfad(slug), today=heute)
        kontext["erg"][slug] = ergebnis
        for befund in ergebnis.get("findings") or []:
            code = str(befund.get("code") or "").strip()
            check_id = ERG_CODE_ZU_CHECK.get(code)
            if check_id is None:
                # Unbekannter E-Code: laut melden, nie still übergehen –
                # sonst würde eine neue Wache unsichtbar für die Scorecard.
                tool_fehler[check_id or "Y2-pruefprotokoll"] = (
                    f"unbekannter editorial_review_gate-Code `{code}` – "
                    "Mapping in release_scorecard.py nachziehen")
                check_id = "Y2-pruefprotokoll"
            _merke(befunde, slug, check_id, f"{code}: {befund.get('detail')}")

    # ---------- Technik: Länge (hart + Optimum-Warnung) ----------
    try:
        len_fail, len_warn = publish_gate.check_length_failures()
        if len_warn:
            tool_fehler["T1-zeichenlaenge"] = len_warn
        for slug in len_fail:
            if slug in kontext["erg"] or slug in live_slugs:
                _merke(befunde, slug, "T1-zeichenlaenge",
                       "Zeichenlänge zu-kurz/zu-lang (check_length.py)")
    except Exception as exc:  # noqa: BLE001 – fail-closed, nie still grün
        tool_fehler["T1-zeichenlaenge"] = f"check_length nicht auswertbar: {exc}"
    try:
        check_length = _importiere_gate_module("check_length")
        for eintrag in check_length.collect():
            if eintrag.get("status") in ("unter-optimum", "ueber-optimum"):
                _merke(befunde, eintrag["slug"], "T1w-zeichenlaenge-optimum",
                       f"Zeichenlänge {eintrag['status']} "
                       f"({eintrag['chars']} Zeichen, Optimum 12.000–18.000)")
    except Exception as exc:  # noqa: BLE001
        tool_fehler["T1w-zeichenlaenge-optimum"] = f"Längen-Optimum nicht messbar: {exc}"

    # ---------- Technik: SEO-Audit (braucht public/) ----------
    try:
        daten = publish_gate._run_json(["scripts/seo_audit.py", "--json"])
        if daten is None:
            tool_fehler["T2-seo-audit"] = (
                "SEO-Audit nicht beweisbar – kein Messergebnis "
                "(public/ gebaut? hugo --minify)")
        else:
            seo_fail, seo_warn = publish_gate.seo_audit_failures()
            for slug in seo_fail:
                _merke(befunde, slug, "T2-seo-audit",
                       "harte SEO-Mängel (score_issues > 0, seo_audit.py)")
            if seo_warn:
                for slug in live_slugs:
                    _merke(befunde, slug, "T2-seo-audit", f"Sitemap: {seo_warn}")
    except Exception as exc:  # noqa: BLE001
        tool_fehler["T2-seo-audit"] = f"seo_audit nicht auswertbar: {exc}"

    # ---------- Technik: Titel R5, Keywords, Lesbarkeit, Verständnis ----------
    try:
        for slug in publish_gate.title_integrity_failures(live_slugs):
            _merke(befunde, slug, "T3-titel-r5",
                   "Titel vermutlich unvollständig (check_titles.py R5)")
    except Exception as exc:  # noqa: BLE001
        tool_fehler["T3-titel-r5"] = f"Titel-Prüfung nicht auswertbar: {exc}"

    try:
        keyword_optimizer = _importiere_gate_module("keyword_optimizer")
        if keyword_optimizer._selftest():
            tool_fehler["T4-keyword-score"] = "Keyword-Gate-Selbsttest fehlgeschlagen (fail-closed)"
        else:
            kw_fail, _ = publish_gate.keyword_failures(live_slugs)
            for slug, gruende in kw_fail.items():
                for grund in gruende:
                    _merke(befunde, slug, "T4-keyword-score", grund)
    except Exception as exc:  # noqa: BLE001
        tool_fehler["T4-keyword-score"] = f"Keyword-Prüfung nicht auswertbar: {exc}"

    try:
        rdl_fail, _ = publish_gate.readability_failures(live_slugs)
        for slug, gruende in rdl_fail.items():
            for grund in gruende:
                _merke(befunde, slug, "T5-lesbarkeit", grund)
    except Exception as exc:  # noqa: BLE001
        tool_fehler["T5-lesbarkeit"] = f"Lesbarkeit nicht auswertbar: {exc}"

    try:
        tv_fail, _ = publish_gate.textverstaendnis_failures(live_slugs)
        for slug, gruende in tv_fail.items():
            for grund in gruende:
                _merke(befunde, slug, "T6-textverstaendnis", grund)
    except Exception as exc:  # noqa: BLE001
        tool_fehler["T6-textverstaendnis"] = f"Textverständnis nicht auswertbar: {exc}"

    # ---------- Technik: Render-Beweis (Artikel im Build vorhanden) ----------
    for slug in live_slugs:
        html = ROOT / "public" / "posts" / slug / "index.html"
        kontext["render"][slug] = html.is_file()
        if not html.is_file():
            _merke(befunde, slug, "T7-render-beweis",
                   "Artikel fehlt im Build (public/posts/<slug>/index.html) – "
                   "Beweisbasis aller Render-Checks nicht vorhanden")

    # ---------- Affiliate (alle fail-closed wie im Publish-Gate) ----------
    try:
        profi_fail, profi_warn = publish_gate.affiliate_profi_failures()
        if profi_warn and not profi_fail:
            tool_fehler["A4-profi-check"] = profi_warn
        for slug, probleme in profi_fail.items():
            for problem in probleme:
                _merke(befunde, slug, "A4-profi-check", problem)
    except Exception as exc:  # noqa: BLE001
        tool_fehler["A4-profi-check"] = f"Profi-Check nicht auswertbar: {exc}"

    try:
        integ_fail, integ_warn, integ_tool = publish_gate.affiliate_integrity_failures(live_slugs)
        if integ_tool:
            tool_fehler["A1-link-integritaet"] = integ_warn or "Render-Beweis nicht führbar"
        for slug, probleme in integ_fail.items():
            for problem in probleme:
                _merke(befunde, slug, "A1-link-integritaet", problem)
    except Exception as exc:  # noqa: BLE001
        tool_fehler["A1-link-integritaet"] = f"Affiliate-Integrität nicht auswertbar: {exc}"

    try:
        intent_fail, intent_warn, intent_tool = publish_gate.affiliate_intent_failures(live_slugs)
        if intent_tool:
            tool_fehler["A2-intent"] = intent_warn or "Intent-Wache nicht führbar"
        for slug, probleme in intent_fail.items():
            for problem in probleme:
                _merke(befunde, slug, "A2-intent", problem)
    except Exception as exc:  # noqa: BLE001
        tool_fehler["A2-intent"] = f"Intent-Wache nicht auswertbar: {exc}"

    try:
        offen_fail, offen_warn, offen_tool = publish_gate.offenlegung_failures(live_slugs)
        if offen_tool:
            tool_fehler["A3-offenlegung"] = offen_warn or "Offenlegung nicht beweisbar"
        for slug, probleme in offen_fail.items():
            for problem in probleme:
                _merke(befunde, slug, "A3-offenlegung", problem)
    except Exception as exc:  # noqa: BLE001
        tool_fehler["A3-offenlegung"] = f"Offenlegung nicht auswertbar: {exc}"

    # ---------- Redundanz: derselbe Publish-Gate-Collector (D1–D6) ----------
    # WF-54C4/#674: Die Scorecard darf keine eigene Schleife über die
    # Duplikat-Wache besitzen. Sonst kann ein Kandidat das Publish-Gate
    # passieren und erst nach dem Build an einer zweiten Messung scheitern.
    # Der Collector ordnet Cross-Artikel-Funde beiden Seiten zu.
    try:
        dupl_fail, dupl_tool = publish_gate.duplicate_failures(live_slugs)
        if dupl_tool:
            tool_fehler["RD1-duplikate"] = dupl_tool
        for slug, probleme in dupl_fail.items():
            for problem in probleme:
                _merke(befunde, slug, "RD1-duplikate", problem)
    except Exception as exc:  # noqa: BLE001
        tool_fehler["RD1-duplikate"] = f"Duplikat-Wache nicht auswertbar: {exc}"

    # ---------- Faktenfrische (Faktenalter + nächste Überprüfung) ----------
    # Die Scorecard und das Publish-Gate benutzen denselben Collector. Damit
    # kann ein best-effort-Recherche-Schritt keinen Zustand erzeugen, in dem
    # der Publish-Pfad grün und erst die Scorecard rot ist (WF-54C4 / #583).
    try:
        f1_fail, f1_warn, f1_tool = publish_gate.faktenfrische_failures(
            live_slugs, stichtag=heute)
        if f1_tool:
            tool_fehler["F1-faktenfrische"] = f1_warn or "Faktenfrische nicht beweisbar"
    except Exception as exc:  # noqa: BLE001 – fail-closed, nie still grün
        f1_fail, f1_tool = {}, True
        tool_fehler["F1-faktenfrische"] = f"Faktenfrische nicht auswertbar: {exc}"

    try:
        faktenfrische = _importiere_gate_module("faktenfrische")
        cfg = faktenfrische.lade_config()
        for art in faktenfrische.alle_artikel("posts"):
            slug = art.get("slug")
            if slug not in live_slugs:
                continue
            faellig = faktenfrische.faelligkeit(art, cfg, stichtag=heute)
            kontext["fakten"][slug] = {"art": art, "faellig": faellig}
            if slug in f1_fail:
                _merke(befunde, slug, "F1-faktenfrische", "; ".join(f1_fail[slug]))
            if not art.get("quellen_vorhanden"):
                erg_result = kontext["erg"].get(slug) or {}
                if erg_result.get("risk") != erg.RISK_HIGH:
                    _merke(befunde, slug, "Q2-quellen-vorhanden",
                           "keine Belegkette im Frontmatter (quellen) – "
                           "nachpflegen (faktenfrische)")
    except Exception as exc:  # noqa: BLE001
        tool_fehler["F1-faktenfrische"] = f"Faktenfrische nicht auswertbar: {exc}"

    # ---------- Heutige Live-Kandidaten (Deploy-Scope) ----------
    try:
        kontext["kandidaten"] = publish_gate.todays_live_candidates()
    except Exception:  # noqa: BLE001 – Kandidaten sind Zusatzinformation
        kontext["kandidaten"] = []

    return befunde, tool_fehler, kontext


# ============================================================
#  Bewertung
# ============================================================
def _schwere(status: str) -> int:
    return STATUS_FOLGE.index(status) if status in STATUS_FOLGE else len(STATUS_FOLGE)


def check_laeuft_fuer(check: dict, risiko: str) -> bool:
    """Gilt der Check für diesen Artikel? (geltung-Feld der SSOT)"""
    geltung = str(check.get("geltung") or "alle").strip().lower()
    if geltung == "risikoklasse hoch":
        return risiko == "hoch"
    if geltung == "risikoklasse standard-und-erhoeht":
        return risiko != "hoch"
    return True


def check_ergebnis(slug: str, check: dict, artikel_befunde: dict,
                   tool_fehler: dict, aktive_ausnahmen: dict,
                   risiko: str) -> dict:
    """EIN Check → EIN Ergebnis. Vollständige Matrix, kein Scheingrün:

      Fund vorhanden        → blockiert/warnung (ggf. per befristeter
                              Ausnahme zu warnung herabgestuft)
      Werkzeugfehler        → nicht beweisbar (fail-closed)
      gelaufen und sauber   → bestanden
      gilt nicht für Artikel → nicht erforderlich
      hätte laufen müssen,  → nicht beweisbar (nicht gemessen ist nie
      wurde aber nie gemessen  „bestanden“)
    """
    check_id = check["id"]
    if check_id in artikel_befunde:
        ausnahme = aktive_ausnahmen.get((slug, check_id))
        status = "blockiert" if check["wirkung"] == "blockiert" else "warnung"
        detail = "; ".join(artikel_befunde[check_id])
        if ausnahme is not None:
            status = "warnung"
            detail += (f" – Ausnahme bis {ausnahme['gueltig_bis']} "
                       f"von {ausnahme['entschieden_von']}")
        return {"status": status, "detail": detail, "ausnahme": bool(ausnahme)}
    if check_id in tool_fehler:
        return {"status": "nicht beweisbar", "detail": tool_fehler[check_id],
                "werkzeugfehler": True}
    if check_laeuft_fuer(check, risiko):
        return {"status": "bestanden", "detail": ""}
    return {"status": "nicht erforderlich", "detail": ""}


def dimension_status(ergebnisse: list[dict]) -> str:
    """Worst-of über die Check-Ergebnisse einer Dimension.

    Ein Dimensionsergebnis ohne einzige Messung ist „nicht beweisbar“,
    niemals „bestanden“ – ein Scheingrün-Schutz (Selbsttest ST6).
    """
    if not ergebnisse:
        return "nicht beweisbar"
    relevant = [e for e in ergebnisse if e["status"] != "nicht erforderlich"]
    if not relevant:
        return "nicht erforderlich"
    return max((e["status"] for e in relevant), key=_schwere)


def naechste_pruefung(slug: str, erg_ergebnis: dict, fakten: dict | None,
                      heute: dt.date) -> tuple[str, bool]:
    """(Datum-Anzeige, überfällig?) – eine Regel, keine zweite.

    Risikoklasse hoch: redaktionelle_pruefung.naechste_pruefung (E10 wacht
    darüber). Sonst: faktencheck + Intervall (SSOT faktenfrische.yaml).
    """
    if erg_ergebnis.get("risk") == "hoch":
        review = erg_ergebnis.get("_review") or {}
        wert = str(review.get("naechste_pruefung") or "").strip()[:10]
        if not wert:
            return "unbekannt", True
        try:
            datum = dt.date.fromisoformat(wert)
        except ValueError:
            return wert, True
        return wert, datum < heute
    if not fakten:
        return "unbekannt", True
    faellig = fakten.get("faellig") or {}
    art = fakten.get("art") or {}
    faktencheck = art.get("faktencheck")
    intervall = int(faellig.get("intervall") or 90)
    if faktencheck is None:
        return "unbekannt (Erstrecherche ausstehend)", True
    datum = faktencheck + dt.timedelta(days=intervall)
    return datum.isoformat(), datum < heute


def bewerte_artikel(slug: str, befunde: dict, tool_fehler: dict, kontext: dict,
                    register: dict, aktive_ausnahmen: dict,
                    heute: dt.date) -> dict:
    """Bewertet EINEN Live-Artikel über alle acht Dimensionen."""
    artikel_befunde = befunde.get(slug) or {}
    erg_ergebnis = kontext["erg"].get(slug) or {}
    fakten = kontext["fakten"].get(slug)
    risiko = erg_ergebnis.get("risk") or "unbekannt"
    # Review-Block für die Terminanzeige nachladen (reiner Lesezugriff)
    if erg_ergebnis.get("risk") == "hoch":
        try:
            erg = _importiere_gate_module("editorial_review_gate")
            fm, _body, _raw = erg.load_article(artikel_pfad(slug))
            review = fm.get("redaktionelle_pruefung") or {}
        except Exception:  # noqa: BLE001 – Anzeige darf nie crashen
            review = {}
        erg_ergebnis["_review"] = review if isinstance(review, dict) else {}

    # Check-Ergebnisse je Dimension: VOLLE Matrix über alle deklarierten
    # Checks (reine Funktion check_ergebnis) – gelaufen+sauber = bestanden,
    # nicht anwendbar = nicht erforderlich, nicht gemessen = nicht beweisbar.
    #
    # REPARATUR #676 (09.10.2026): Beide Sammler standen UNTER der Schleife,
    # die sie befüllt. Solange jeder Fund einer deklarierten Check-ID
    # zugeordnet war, fiel das nicht auf – der erste undeklarierte Fund aber
    # lief in ein NameError. Ausgerechnet der Pfad, der „Funde zu nicht
    # deklarierten Prüfungen sind VERBOTEN – sie werden laut blockiert, nie
    # still ignoriert" durchsetzen sollte, starb mit einem rohen Traceback
    # statt mit einem Befund (die Klasse WF-A535 #529: ein roter Schritt,
    # der seine Ursache nicht nennt). Jetzt wird initialisiert, bevor
    # geschrieben wird.
    je_dimension: dict[str, list[dict]] = {dim: [] for dim in DIMENSIONS_FOLGE}
    befundliste: list[dict] = []

    for check_id in sorted(artikel_befunde):
        if check_id in register:
            continue
        je_dimension["technik"].append({
            "status": "blockiert",
            "detail": f"Check `{check_id}` ist in der SSOT nicht deklariert"})
        befundliste.append({"check": check_id, "dimension": "technik",
                            "wirkung": "blockiert",
                            "detail": "nicht in der SSOT deklariert: "
                                      + "; ".join(artikel_befunde[check_id])[:300]})

    for check_id in sorted(register):
        check = register[check_id]
        ergebnis = check_ergebnis(slug, check, artikel_befunde, tool_fehler,
                                  aktive_ausnahmen, risiko)
        je_dimension[check["dimension"]].append(ergebnis)
        if ergebnis["status"] in ("blockiert", "warnung", "nicht beweisbar"):
            befundliste.append({
                "check": check_id,
                "dimension": check["dimension"],
                "wirkung": check["wirkung"],
                "detail": ergebnis["detail"],
                "ausnahme": ergebnis.get("ausnahme", False),
                "werkzeugfehler": ergebnis.get("werkzeugfehler", False),
            })

    # 3) Dimensionsstatus + Sonderanzeigen
    dimensionen = {dim: dimension_status(je_dimension[dim]) for dim in DIMENSIONS_FOLGE}

    anzeige = {}
    if dimensionen["ymyl"] in ("blockiert", "nicht beweisbar"):
        anzeige["ymyl"] = ("Prüfung offen" if risiko == "hoch"
                           else "Klassifikation unklar")
    elif risiko == "hoch":
        anzeige["ymyl"] = "geprüft (hoch, freigegeben)" if erg_ergebnis.get("approved") \
            else "Prüfung offen (hoch)"
    elif risiko == "erhoeht":
        anzeige["ymyl"] = "geprüft (erhöht)"
    else:
        anzeige["ymyl"] = "geprüft (kein Hochrisiko)"

    if dimensionen["freigabe"] in ("blockiert", "nicht beweisbar"):
        anzeige["freigabe"] = "ausstehend" if risiko == "hoch" else "unklar"
    elif risiko == "hoch":
        anzeige["freigabe"] = "vorhanden" if erg_ergebnis.get("approved") else "ausstehend"
    else:
        anzeige["freigabe"] = "nicht erforderlich"

    termin, ueberfaellig = naechste_pruefung(slug, erg_ergebnis, fakten, heute)
    if dimensionen["revision"] == "blockiert":
        anzeige["revision"] = f"{termin}" + (" (überfällig)" if ueberfaellig else "")
    elif ueberfaellig:
        dimensionen["revision"] = "blockiert"
        anzeige["revision"] = f"{termin} (überfällig)"
    else:
        anzeige["revision"] = termin

    # Urteil: Schärfe über alle Dimensionen. „nicht erforderlich“ zählt wie
    # „bestanden“ – eine nicht benötigte Freigabe ist kein Makel.
    schaerfen = [
        "bestanden" if dimensionen[dim] in ("bestanden", "nicht erforderlich")
        else dimensionen[dim]
        for dim in DIMENSIONS_FOLGE
    ]
    urteil = max(schaerfen, key=_schwere)
    if urteil == "bestanden":
        urteil = "freigabe-reif"

    return {
        "slug": slug,
        "risikoklasse": risiko,
        "dimensionen": dimensionen,
        "anzeige": anzeige,
        "befunde": befundliste,
        "urteil": urteil,
        "naechste_pruefung": termin,
        "ueberfaellig": ueberfaellig,
    }


def bewerte_entwurf(slug: str, kontext: dict, heute: dt.date) -> dict:
    """Reduzierte Sicht für Entwürfe: die menschliche Freigabe-Seite.

    Entwürfe sind nicht release-relevant – aber die Frage „was ist noch
    offen, bevor dieser Artikel live gehen darf?“ braucht eine Antwort.
    """
    erg = kontext["erg"].get(slug)
    fakten = kontext["fakten"].get(slug)
    if erg is None:
        # Drafts werden von den Collectoren teils übersprungen – selbst nachladen
        try:
            erg_mod = _importiere_gate_module("editorial_review_gate")
            erg = erg_mod.evaluate_path(artikel_pfad(slug), today=heute)
        except Exception:  # noqa: BLE001
            erg = {"risk": "unbekannt", "approved": False, "findings": []}
    risiko = erg.get("risk") or "unbekannt"
    if fakten is None:
        try:
            ff = _importiere_gate_module("faktenfrische")
            cfg = ff.lade_config()
            for art in ff.alle_artikel("posts"):
                if art.get("slug") == slug:
                    fakten = {"art": art, "faellig": ff.faelligkeit(art, cfg, stichtag=heute)}
                    break
        except Exception:  # noqa: BLE001
            fakten = None
    erg_kontext = dict(erg)
    termin, ueberfaellig = naechste_pruefung(slug, erg_kontext, fakten, heute)
    offen = [f"{f.get('code')}: {f.get('detail')}" for f in erg.get("findings") or []]
    return {
        "slug": slug,
        "risikoklasse": risiko,
        "freigabe": ("vorhanden" if erg.get("approved")
                     else ("ausstehend" if risiko == "hoch" else "nicht erforderlich")),
        "faktencheck": (fakten or {}).get("faellig", {}).get("grund", "unbekannt"),
        "naechste_pruefung": termin,
        "ueberfaellig": ueberfaellig,
        "offen": offen[:8],
    }


# ============================================================
#  Report
# ============================================================
def _symbol(status: str) -> str:
    return {
        "bestanden": "✅ bestanden",
        "warnung": "⚠️ warnung",
        "blockiert": "❌ blockiert",
        "nicht beweisbar": "❔ nicht beweisbar",
        "nicht erforderlich": "➖ nicht erforderlich",
    }.get(status, "❔ " + status)


def report_schreiben(ergebnis: dict, ssot: dict, abgelaufene: list[dict],
                     pfad: Path = REPORT_PATH) -> str:
    heute = ergebnis["heute"]
    dimensionen = ssot.get("dimensionen") or {}
    zeilen: list[str] = []
    z = zeilen.append

    z("# Release-Scorecard – die Produktionswahrheit")
    z("")
    z(f"**Stand:** {heute.isoformat()} · **Modus:** {ergebnis['modus']} · "
      f"**Engine:** `scripts/release_scorecard.py` · "
      f"**SSOT:** `data/release_scorecard.yaml`")
    z("")
    z("> Eine Zeile pro Artikel, acht Dimensionen, ein Wahrheitsort. "
      "Was hier rot ist, ist rot – nichts wird weggeklammert.")
    z("")
    z("**Die sechs Fragen – kurz beantwortet (ausführlich: "
      "`docs/ANLEITUNG-RELEASE-SCORECARD.md`)**")
    z("")
    z("| Frage | Antwort |")
    z("|---|---|")
    z("| 1. Was blockiert Veröffentlichung? | jeder Check mit "
      "`wirkung: blockiert` in der SSOT – maschinell durchgesetzt "
      "(Governance C19) |")
    z("| 2. Was warnt nur? | Checks mit `wirkung: warnung` – sichtbar, "
      "stoppen nicht |")
    z("| 3. Wer entscheidet fachlich? | Herausgeber Frank Hartung "
      "(`eskalation` in der SSOT); die Maschine entscheidet fachlich nie |")
    z("| 4. Falsche Positivmeldungen? | keine zweite Messregel (Scorecard "
      "nutzt die Publish-Gate-Collectoren), fail-closed bei nicht führbarem "
      "Beweis, befristete Ausnahmen mit Ablaufdatum |")
    z("| 5. Fachliche Freigabe? | Risikoklasse hoch: Prüfer + Belegkette + "
      "Zahlenprotokoll + `--seal`; sonst AUTO-Bahn der Gate-Kette |")
    z("| 6. Nachweis der geprüften Version? | Release-Siegel: SHA-256 je "
      "Artikel + Dimensionen + Deploy-Commit in "
      "`data/release_scorecard_state.json` (Historie append-only) |")
    z("")

    # Gesamtergebnis je Dimension
    z("## Gesamtergebnis je Dimension (Live-Bestand)")
    z("")
    kopf = "| " + " | ".join(dimensionen[d]["titel"] for d in DIMENSIONS_FOLGE) + " |"
    z(kopf)
    z("|" + "---|" * len(DIMENSIONS_FOLGE))
    zeile = "| " + " | ".join(
        _symbol(ergebnis["dimensionen_gesamt"][d]) for d in DIMENSIONS_FOLGE) + " |"
    z(zeile)
    z("")

    # Kandidaten (falls vorhanden und nicht leer)
    if ergebnis.get("kandidaten"):
        z("## Heutige Live-Kandidaten (Deploy-Scope)")
        z("")
        z("| Artikel | " + " | ".join(dimensionen[d]["titel"] for d in DIMENSIONS_FOLGE)
          + " | Urteil |")
        z("|---|" + "---|" * (len(DIMENSIONS_FOLGE) + 1))
        for slug in ergebnis["kandidaten"]:
            art = ergebnis["artikel"].get(slug)
            if not art:
                continue
            zelle = [art["anzeige"].get("ymyl", _symbol(art["dimensionen"]["ymyl"])),
                     art["anzeige"].get("freigabe", _symbol(art["dimensionen"]["freigabe"])),
                     art["anzeige"].get("revision", _symbol(art["dimensionen"]["revision"]))]
            normal = [_symbol(art["dimensionen"][d]) for d in
                      DIMENSIONS_FOLGE if d not in ("ymyl", "freigabe", "revision")]
            z(f"| `{slug}` | " + " | ".join(normal + zelle) + f" | **{art['urteil']}** |")
        z("")

    # Live-Bestand
    z("## Live-Bestand (Artikel für Artikel)")
    z("")
    z("| Artikel | " + " | ".join(dimensionen[d]["titel"] for d in DIMENSIONS_FOLGE)
      + " | Urteil |")
    z("|---|" + "---|" * (len(DIMENSIONS_FOLGE) + 1))
    for slug in sorted(ergebnis["artikel"]):
        art = ergebnis["artikel"][slug]
        normal = [_symbol(art["dimensionen"][d]) for d in DIMENSIONS_FOLGE
                  if d not in ("ymyl", "freigabe", "revision")]
        zelle = [art["anzeige"].get("ymyl", "–"),
                 art["anzeige"].get("freigabe", "–"),
                 art["anzeige"].get("revision", "–")]
        z(f"| `{slug}` | " + " | ".join(normal + zelle) + f" | **{art['urteil']}** |")
    z("")

    # Blockierte Artikel im Detail
    blockiert = [a for a in ergebnis["artikel"].values()
                 if a["urteil"] in ("blockiert", "nicht beweisbar")]
    z(f"## Blockierende Funde ({len(blockiert)} Artikel)")
    z("")
    if not blockiert:
        z("Keine – der komplette Live-Bestand ist frei von blockierenden Funden.")
    else:
        for art in sorted(blockiert, key=lambda a: a["slug"]):
            z(f"### `{art['slug']}` ({art['urteil']}, Risikoklasse {art['risikoklasse']})")
            z("")
            for befund in art["befunde"]:
                if befund.get("ausnahme") or befund.get("werkzeugfehler"):
                    continue
                if befund["wirkung"] != "blockiert":
                    continue
                z(f"- **{befund['check']}** [{befund['dimension']}]: {befund['detail']}")
            for befund in art["befunde"]:
                if befund.get("werkzeugfehler"):
                    z(f"- ❔ **{befund['check']}** [{befund['dimension']}]: "
                      f"nicht beweisbar – {befund['detail']}")
            z("")
    # Nur-Warnungen
    nur_warnung = [a for a in ergebnis["artikel"].values() if a["urteil"] == "warnung"]
    z(f"## Warnungen ohne Blockade ({len(nur_warnung)} Artikel)")
    z("")
    for art in sorted(nur_warnung, key=lambda a: a["slug"])[:20]:
        warn = [b for b in art["befunde"]
                if b["wirkung"] == "warnung" or b.get("ausnahme")]
        if warn:
            detail = "; ".join(f"{b['check']}: {b['detail'][:120]}" for b in warn[:3])
            z(f"- `{art['slug']}` – {detail}")
    if not nur_warnung:
        z("Keine.")
    z("")

    # Entwürfe
    if ergebnis.get("entwuerfe"):
        z("## Entwürfe – was vor dem Livegang noch offen ist")
        z("")
        z("| Artikel | Risikoklasse | Freigabe | Faktenstand | Nächste Prüfung |")
        z("|---|---|---|---|---|")
        for e in ergebnis["entwuerfe"]:
            z(f"| `{e['slug']}` | {e['risikoklasse']} | {e['freigabe']} | "
              f"{e['faktencheck']} | {e['naechste_pruefung']}"
              + (" ⚠️ überfällig" if e["ueberfaellig"] else "") + " |")
        z("")

    # Ausnahmen
    z("## Ausnahmen (Falsch-Alarm-Protokoll)")
    z("")
    aktiv = [a for a in (ssot.get("ausnahmen") or []) if a not in abgelaufene]
    if aktiv:
        z("| Artikel | Check | gültig bis | entschieden von | Begründung |")
        z("|---|---|---|---|---|")
        for a in aktiv:
            z(f"| `{a['slug']}` | {a['check']} | {a['gueltig_bis']} | "
              f"{a['entschieden_von']} | {a['begruendung']} |")
    else:
        z("Keine aktiven Ausnahmen – alle Checks wirken unverändert.")
    if abgelaufene:
        z("")
        z("**Abgelaufen (wirken nicht mehr, sichtbar gemacht):** "
          + ", ".join(f"`{a['slug']}`/{a['check']} (bis {a['gueltig_bis']})"
                      for a in abgelaufene))
    z("")

    z("---")
    z("_Exit-Code-Vertrag: 0 = freigabe-reif · 1 = blockierende Funde im "
      "Scope · 2 = Werkzeugfehler (fail-closed). Ein nicht führbarer "
      "Beweis ist niemals „bestanden“._")
    z("")

    text = "\n".join(zeilen)
    pfad.write_text(text, encoding="utf-8")
    return text


# ============================================================
#  Hauptlauf
# ============================================================
def durchfuehren(modus: str, heute: dt.date, slugs_live: list[str],
                 slugs_entwurf: list[str], fingerprints: dict[str, str],
                 vorheriger_zustand: dict, commit_sha: str | None) -> dict:
    ssot = ssot_laden()
    register = check_register(ssot)
    aktive_ausnahmen, abgelaufene = ausnahmen_aufbereiten(ssot, heute)

    befunde, tool_fehler, kontext = sammle(slugs_live, heute)

    artikel = {}
    for slug in slugs_live:
        art = bewerte_artikel(slug, befunde, tool_fehler, kontext, register,
                              aktive_ausnahmen, heute)
        art["sha256"] = fingerprints.get(slug)
        art["siegel_drift"] = siegel_drift(vorheriger_zustand, slug, art["sha256"] or "")
        artikel[slug] = art

    entwuerfe = [bewerte_entwurf(slug, kontext, heute) for slug in slugs_entwurf]

    # Gesamtbild je Dimension (worst-of über den Live-Bestand)
    dimensionen_gesamt = {}
    for dim in DIMENSIONS_FOLGE:
        werte = [a["dimensionen"][dim] for a in artikel.values()]
        if not werte:
            dimensionen_gesamt[dim] = "nicht beweisbar"
        else:
            dimensionen_gesamt[dim] = max(werte, key=_schwere)

    kandidaten = [s for s in kontext.get("kandidaten") or [] if s in artikel]

    return {
        "version": 1,
        "heute": heute,
        "modus": modus,
        "artikel": artikel,
        "entwuerfe": entwuerfe,
        "dimensionen_gesamt": dimensionen_gesamt,
        "kandidaten": kandidaten,
        "tool_fehler": tool_fehler,
        "abgelaufene_ausnahmen": abgelaufene,
        "aktive_ausnahmen": sum(1 for _ in (ssot.get("ausnahmen") or [])
                                if _ not in abgelaufene),
        "commit": commit_sha,
        "ssot": ssot,
    }


def exit_code(ergebnis: dict, scope: list[str]) -> int:
    """Vertrag: 2 = Werkzeugfehler · 1 = blockierend im Scope · 0 = ok."""
    if ergebnis["tool_fehler"]:
        return EXIT_WERKZEUGFEHLER
    for slug in scope:
        art = ergebnis["artikel"].get(slug)
        if art and art["urteil"] in ("blockiert", "nicht beweisbar"):
            return EXIT_BLOCKIERT
    return EXIT_OK


def zustand_schreiben(ergebnis: dict) -> dict:
    """Siegel-Zustand (data/release_scorecard_state.json) + Historie."""
    jetzt = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    zustand = {
        "version": 1,
        "generated_at": jetzt,
        "modus": ergebnis["modus"],
        "commit": ergebnis.get("commit"),
        "artikel": {
            slug: {
                "sha256": art["sha256"],
                "urteil": art["urteil"],
                "risikoklasse": art["risikoklasse"],
                "dimensionen": art["dimensionen"],
                "naechste_pruefung": art["naechste_pruefung"],
                "siegel_drift": art["siegel_drift"],
            } for slug, art in sorted(ergebnis["artikel"].items())
        },
    }
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(zustand, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")

    blockiert = sorted(slug for slug, art in ergebnis["artikel"].items()
                       if art["urteil"] in ("blockiert", "nicht beweisbar"))
    historie = {
        "ts": jetzt,
        "modus": ergebnis["modus"],
        "commit": ergebnis.get("commit"),
        "live": len(ergebnis["artikel"]),
        "freigabe_reif": sum(1 for a in ergebnis["artikel"].values()
                             if a["urteil"] == "freigabe-reif"),
        "warnung": sum(1 for a in ergebnis["artikel"].values()
                       if a["urteil"] == "warnung"),
        "blockiert": blockiert,
        "tool_fehler": sorted(ergebnis["tool_fehler"]),
        "kandidaten": ergebnis["kandidaten"],
    }
    with HISTORY_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(historie, ensure_ascii=False, sort_keys=True) + "\n")
    return zustand


def audit_schreiben(ergebnis: dict, code: int) -> None:
    try:
        audit_log = _importiere_gate_module("audit_log")
        audit_log.log_event(
            module="release_scorecard",
            action=f"lauf:{ergebnis['modus']}",
            input={"modus": ergebnis["modus"],
                   "commit": ergebnis.get("commit")},
            output={"live": len(ergebnis["artikel"]),
                    "freigabe_reif": sum(1 for a in ergebnis["artikel"].values()
                                         if a["urteil"] == "freigabe-reif"),
                    "blockiert": sorted(s for s, a in ergebnis["artikel"].items()
                                        if a["urteil"] == "blockiert"),
                    "tool_fehler": sorted(ergebnis["tool_fehler"])},
            status="ok" if code == EXIT_OK else
            ("blockiert" if code == EXIT_BLOCKIERT else "fail_closed"))
    except Exception:  # noqa: BLE001 – Audit darf den Lauf nie crashen
        pass


def detail_anzeigen(art: dict) -> None:
    print(f"\n📊 {art['slug']} – Risikoklasse: {art['risikoklasse']}")
    for dim in DIMENSIONS_FOLGE:
        wert = art["anzeige"].get(dim) or _symbol(art["dimensionen"][dim])
        print(f"  {dim:<12} {wert}")
    print(f"  Urteil       {art['urteil']}")
    if art["befunde"]:
        print("  Funde:")
        for b in art["befunde"]:
            marke = ("❔" if b.get("werkzeugfehler")
                     else ("⚠️" if b["wirkung"] == "warnung" or b.get("ausnahme") else "❌"))
            print(f"    {marke} {b['check']} [{b['dimension']}]: {b['detail'][:160]}")
    if art.get("sha256"):
        print(f"  Siegel       sha256:{art['sha256'][:16]}… "
              f"({art.get('siegel_drift', '–')})")


# ============================================================
#  Selbsttest (C6/C15: trocken, eingefrorene Proben, schreibt nichts)
# ============================================================
def selftest() -> list[str]:
    fehler: list[str] = []

    def pruefe(name: str, bedingung: bool):
        if not bedingung:
            fehler.append(name)

    # ST1 – SSOT-Form: acht Dimensionen, Checks valide, deckungsgleich.
    try:
        ssot = ssot_laden()
        pruefe("ST1 SSOT lädt und ist vollständig", True)
    except KonfigurationsFehler as exc:
        fehler.append(f"ST1 SSOT unvollständig: {exc}")
        ssot = {"dimensionen": {}, "checks": [], "ausnahmen": []}
    register = check_register(ssot)
    pruefe("ST1 jede Dimension hat Checks",
           all(any(c.get("dimension") == d for c in ssot.get("checks") or [])
               for d in DIMENSIONS_FOLGE))

    # ST2 – Publish-Gate-Deckung: jede harte Familie deklariert & blockierend.
    for cid, muste in PUBLISH_GATE_HART_FAMILIEN.items():
        check = register.get(cid)
        pruefe(f"ST2 {cid} deklariert und blockierend",
               bool(check) and check.get("wirkung") == "blockiert"
               and muste in str(check.get("quelle") or ""))

    # ST3 – Ausnahmen: Pflichtfelder, Ablauf, nicht ausnehmbar.
    pruefe("ST3 unvollständige Ausnahme wird erkannt",
           bool(ausnahme_fehler({"slug": "x", "check": "T1-zeichenlaenge"})))
    pruefe("ST3 Begründung muss aussagekräftig sein",
           bool(ausnahme_fehler({"slug": "x", "check": "T1-zeichenlaenge",
                                 "begruendung": "kurz", "gueltig_bis": "2030-01-01",
                                 "entschieden_von": "Frank Hartung"})))
    pruefe("ST3 M2-Siegel-Bindung ist nicht ausnehmbar",
           bool(ausnahme_fehler({"slug": "x", "check": "M2-siegel-bindung",
                                 "begruendung": "sollte doch gehen",
                                 "gueltig_bis": "2030-01-01",
                                 "entschieden_von": "Frank Hartung"})))
    gut = {"slug": "x", "check": "T1-zeichenlaenge",
           "begruendung": "Messartefakt aus dem Cover-Rendering",
           "gueltig_bis": "2030-01-01", "entschieden_von": "Frank Hartung"}
    pruefe("ST3 vollständige Ausnahme ist gültig", not ausnahme_fehler(gut))
    try:
        aktive, abgelaufene = ausnahmen_aufbereiten(
            {"ausnahmen": [dict(gut, gueltig_bis="2020-01-01")]},
            dt.date(2026, 10, 3))
        pruefe("ST3 abgelaufene Ausnahme wirkt nicht",
               len(aktive) == 0 and len(abgelaufene) == 1)
    except KonfigurationsFehler:
        fehler.append("ST3 abgelaufene Ausnahme löst fälschlich Konfigurationsfehler aus")

    # ST4 – Siegel: Fingerprint stabil, ändert sich mit Inhalt, Drift erkannt.
    with tempfile.TemporaryDirectory() as tmp:
        datei = Path(tmp) / "index.md"
        datei.write_text("---\ntitle: A\n---\n\nText A\n", encoding="utf-8")
        fp1 = file_fingerprint(datei)
        pruefe("ST4 Fingerprint ist stabil",
               fp1 == file_fingerprint(datei))
        datei.write_text("---\ntitle: A\n---\n\nText A geändert\n", encoding="utf-8")
        pruefe("ST4 Fingerprint ändert sich mit dem Inhalt",
               fp1 != file_fingerprint(datei))
        alt = {"artikel": {"x": {"sha256": fp1}}}
        pruefe("ST4 Drift wird erkannt",
               siegel_drift(alt, "x", "anderer") == "geändert – neu geprüft")
        pruefe("ST4 unveränderte Version wird erkannt",
               siegel_drift(alt, "x", fp1) == "unverändert")
        pruefe("ST4 neuer Artikel wird erkannt",
               siegel_drift(alt, "neu", fp1) == "neu versiegelt")

    # ST5 – Editorial-Mapping: alle Codes gemappt, Unbekannter ist ein Fehler.
    bekannte = set(ERG_CODE_ZU_CHECK)
    pruefe("ST5 E00–E19 vollständig gemappt",
           bekannte == {f"E{i:02d}" for i in range(20)})

    # ST6 – Kein Scheingrün: leere Messung ist „nicht beweisbar“,
    #       Werkzeugfehler schlagen nie auf „bestanden“ durch.
    pruefe("ST6 Dimension ohne Messung ist nicht beweisbar",
           dimension_status([]) == "nicht beweisbar")
    pruefe("ST6 nicht erforderlich bleibt ohne Messurteil",
           dimension_status([{"status": "nicht erforderlich"}]) == "nicht erforderlich")
    pruefe("ST6 blockiert schlägt warnung",
           dimension_status([{"status": "warnung"}, {"status": "blockiert"}]) == "blockiert")
    pruefe("ST6 nicht beweisbar schlägt warnung",
           dimension_status([{"status": "warnung"}, {"status": "nicht beweisbar"}])
           == "nicht beweisbar")

    # ST7 – Exit-Code-Vertrag.
    beispiel = {
        "tool_fehler": {}, "artikel": {
            "a": {"urteil": "freigabe-reif"},
            "b": {"urteil": "blockiert"}}}
    pruefe("ST7 blockiert im Scope → 1",
           exit_code(beispiel, ["b"]) == EXIT_BLOCKIERT)
    pruefe("ST7 blockiert außerhalb des Scopes → 0",
           exit_code(beispiel, ["a"]) == EXIT_OK)
    pruefe("ST7 Werkzeugfehler → 2",
           exit_code({"tool_fehler": {"T2-seo-audit": "x"}, "artikel": {}}, [])
           == EXIT_WERKZEUGFEHLER)

    # ST8 – Nächste Prüfung: Intervall-Rechnung und Überfälligkeit.
    heute = dt.date(2026, 10, 3)
    fakten = {"faellig": {"intervall": 90}, "art": {"faktencheck": dt.date(2026, 9, 1)}}
    termin, ueber = naechste_pruefung("x", {"risk": "standard"}, fakten, heute)
    pruefe("ST8 Standard-Intervall = faktencheck + 90 Tage",
           termin == "2026-11-30" and not ueber)
    termin2, ueber2 = naechste_pruefung(
        "x", {"risk": "standard"},
        {"faellig": {"intervall": 30}, "art": {"faktencheck": dt.date(2026, 8, 1)}},
        heute)
    pruefe("ST8 überfällige Prüfung wird erkannt", ueber2)
    termin3, ueber3 = naechste_pruefung(
        "x", {"risk": "hoch", "_review": {"naechste_pruefung": "2026-11-01"}}, None, heute)
    pruefe("ST8 YMYL nimmt den Review-Termin",
           termin3 == "2026-11-01" and not ueber3)
    pruefe("ST8 fehlender Review-Termin ist überfällig",
           naechste_pruefung("x", {"risk": "hoch", "_review": {}}, None, heute)[1])

    return fehler


# ============================================================
#  CLI
# ============================================================
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Release-Scorecard – die Produktionswahrheit in einer Ansicht")
    parser.add_argument("--live", action="store_true",
                        help="kompletter Live-Bestand (Standard)")
    parser.add_argument("--streng", action="store_true",
                        help="mit --live: blockierende Funde im Bestand = Exit 1")
    parser.add_argument("--kandidaten", action="store_true",
                        help="heutige Live-Kandidaten, hart (Deploy-Modus)")
    parser.add_argument("--slug", help="Einzelnachweis für einen Artikel (schreibt nichts)")
    parser.add_argument("--json", action="store_true", help="maschinenlesbar ausgeben")
    parser.add_argument("--commit-sha", default=os.environ.get("GITHUB_SHA"),
                        help="Deploy-Commit ins Siegel (Default: $GITHUB_SHA)")
    parser.add_argument("--selftest", action="store_true", help="Sabotage-Proben")
    args = parser.parse_args(argv)

    if args.selftest:
        fehler = selftest()
        if fehler:
            print("🛑 RELEASE-SCORECARD-SELFTEST FEHLGESCHLAGEN:")
            for f in fehler:
                print(f"   - {f}")
            return EXIT_WERKZEUGFEHLER
        print("✅ RELEASE-SCORECARD-SELFTEST bestanden: SSOT-Form, Publish-Gate-"
              "Deckung, Ausnahmen-Protokoll, Siegel-Bindung, Editorial-Mapping, "
              "Scheingrün-Schutz, Exit-Vertrag, Terminrechnung.")
        return EXIT_OK

    heute = dt.date.today()

    # SSOT- und Ausnahmenfehler sind fail-closed – vor jeder Messung.
    try:
        ssot_laden()
    except KonfigurationsFehler as exc:
        print(f"🛑 Konfiguration unzulässig (Exit 2): {exc}")
        return EXIT_WERKZEUGFEHLER

    live, entwuerfe, fingerprints = bestand_aufnehmen()
    vorheriger_zustand = zustand_laden()
    modus = ("kandidaten" if args.kandidaten else
             ("slug" if args.slug else "live"))

    try:
        ergebnis = durchfuehren(modus, heute, live, entwuerfe, fingerprints,
                                vorheriger_zustand, args.commit_sha)
    except KonfigurationsFehler as exc:
        print(f"🛑 Konfiguration unzulässig (Exit 2): {exc}")
        return EXIT_WERKZEUGFEHLER

    # Scope für den Exit-Code bestimmen
    if args.kandidaten:
        scope = ergebnis["kandidaten"]
        if not scope:
            print("ℹ️ Keine Live-Kandidaten heute – Scope leer, Exit 0.")
    elif args.slug:
        scope = [args.slug]
    else:
        scope = live if args.streng else []

    code = exit_code(ergebnis, scope)

    if args.slug:
        art = ergebnis["artikel"].get(args.slug)
        if art is None:
            print(f"🛑 Artikel `{args.slug}` ist nicht live (Entwurf oder unbekannt).")
            if any(e["slug"] == args.slug for e in ergebnis["entwuerfe"]):
                e = next(e for e in ergebnis["entwuerfe"] if e["slug"] == args.slug)
                print(f"   Entwurf – Risikoklasse {e['risikoklasse']}, "
                      f"Freigabe: {e['freigabe']}, nächste Prüfung: "
                      f"{e['naechste_pruefung']}")
                return EXIT_OK
            return EXIT_WERKZEUGFEHLER
        detail_anzeigen(art)
        return code

    if args.json:
        print(json.dumps({
            "modus": ergebnis["modus"],
            "heute": ergebnis["heute"].isoformat(),
            "dimensionen_gesamt": ergebnis["dimensionen_gesamt"],
            "kandidaten": ergebnis["kandidaten"],
            "tool_fehler": ergebnis["tool_fehler"],
            "artikel": {
                slug: {"urteil": a["urteil"],
                       "risikoklasse": a["risikoklasse"],
                       "dimensionen": a["dimensionen"],
                       "naechste_pruefung": a["naechste_pruefung"],
                       "sha256": a["sha256"],
                       "siegel_drift": a["siegel_drift"]}
                for slug, a in sorted(ergebnis["artikel"].items())},
        }, ensure_ascii=False, indent=2))
    else:
        zustand = zustand_schreiben(ergebnis)
        report_schreiben(ergebnis, ergebnis["ssot"], ergebnis["abgelaufene_ausnahmen"])
        audit_schreiben(ergebnis, code)
        blockiert = sorted(s for s, a in ergebnis["artikel"].items()
                           if a["urteil"] in ("blockiert", "nicht beweisbar"))
        frei = sum(1 for a in ergebnis["artikel"].values()
                   if a["urteil"] == "freigabe-reif")
        print(f"Release-Scorecard ({modus}): {frei}/{len(ergebnis['artikel'])} "
              f"Live-Artikel freigabe-reif, {len(blockiert)} blockiert/unbeweisbar, "
              f"{len(ergebnis['tool_fehler'])} Werkzeugfehler.")
        for check_id, grund in sorted(ergebnis["tool_fehler"].items()):
            print(f"  ❔ {check_id}: {grund}")
        for slug in blockiert[:10]:
            art = ergebnis["artikel"][slug]
            print(f"  ❌ {slug} ({art['urteil']})")
            for b in art["befunde"][:3]:
                if b["wirkung"] == "blockiert" and not b.get("ausnahme"):
                    print(f"       {b['check']}: {b['detail'][:140]}")
        print(f"Report: RELEASE-SCORECARD.md · Siegel: "
              f"data/release_scorecard_state.json (versiegelt "
              f"{len(zustand['artikel'])} Artikel)")
        if code == EXIT_BLOCKIERT:
            hinweis = "blockierend im Scope"
        elif code == EXIT_WERKZEUGFEHLER:
            hinweis = "Werkzeugfehler, fail-closed"
        elif scope:
            hinweis = "Scope freigabe-reif"
        else:
            hinweis = ("Berichtsmodus ohne strengen Scope – Bestandsbefunde "
                       "stehen oben und im Report, Exit nur bei Werkzeugfehlern")
        print(f"Exit {code} ({hinweis}).")
    return code


if __name__ == "__main__":
    sys.exit(main())
