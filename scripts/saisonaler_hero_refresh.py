#!/usr/bin/env python3
"""Saisonaler Startseiten-Hero: Agent Reach + KI-Feinschliff, sicher automatisiert.

Der alte, statische Willkommenstext in ``hugo.toml`` wurde absichtlich
entfernt. Die Startseite nimmt ihre H1 und ihren Antwort-zuerst-Lead aus der
jeweils aktiven Saison in ``data/saisons.yaml``. Dieses Skript verfeinert nur
``hero_title`` und ``hero_lead`` – nie Templates, Links, CTAs, CSS oder Fakten.

Kette
-----
1. Der Workflow erzeugt vorher mit Agent Reach einen LESENDEN Recherche-Brief
   samt tagesgleichem JSON-Nachweis unter ``data/research/saisonal/``. Der
   Brief ist ein Signal-Pool, keine Quelle für Behauptungen.
2. Der gemeinsame LLM-Zugang des Blogs (``scripts/llm_client.py``) poliert
   daraus mit Franks Stilprofil eine saisonale, suchintentionklare Passage.
   Der Prompt bekommt nur kontrollierte saisonale Themen, keine unbestätigten
   Behauptungen aus dem Brief.
3. Eine lokale Verifikation verlangt Entity-first, Suchintention, mindestens
   drei Kernkategorien, du-Ansprache, keine Zahlen-/URL-Marker, keine
   KI-Floskeln und ausreichende Neuheit. Der Prompt untersagt neue Fakten;
   eine vollständige automatische Faktenprüfung ersetzt das nicht.
4. Die bestehende Startseiten-Wache prüft die Quelle. Im Workflow dürfen
   Hero und Erfolgsnachweise erst nach Hugo-Build und Render-Gates committet
   werden; bei Fehlschlag werden sie zurückgesetzt.

Dauerfestigkeit (Premium-Fix 02.10.2026)
----------------------------------------
Früher galt jede Abweichung vom gespeicherten Fingerprint als „fällig". Eine
redaktionelle Änderung am Hero machte den Lauf damit dauerhaft fällig – und
jeder Ausfall der Textkette (fehlender Schlüssel, Kontingent, Netz) erzeugte
täglich einen roten Lauf plus Fehl-Issue, obwohl der live ausgelieferte Hero
geprüft und frisch war. Drei Stufen beenden das:

* **Stufe 1 – Redaktion einholen:** Besteht eine redaktionelle Änderung den
  SEO/GEO-Vertrag *und* die Startseiten-Wache, wird sie ohne offene Ausfallserie
  als geprüfter Basisstand übernommen (``approved-seasonal-baseline``). Dabei
  wird nichts als KI-poliert ausgegeben. Bei offener Ausfallserie wird die
  Textkette erneut versucht; ein defekter Redaktionsstand bleibt hart rot.
* **Stufe 2 – Kette mit Wiederholung:** Bis zu drei Runden durchlaufen alle
  verfügbaren Anbieter. Auch bei ungültigen oder unvollständigen Antworten
  folgt das nächste Glied; Korrekturhinweise und alle Fehler stehen im Report.
* **Stufe 3 – gestufte Eskalation:** Ein Kettenausfall bei gesunder, frischer
  Basis ist gelb (Warnung + Report + Ausfallzähler im State), kein stiller
  Fallback. Rot wird es erst bei defektem Live-Hero, bei
  ``MAX_AGE_DAYS + GRACE_DAYS`` Tagen Alter oder nach
  ``FAILURE_STREAK_LIMIT`` Ausfällen in Folge.

Jeder Ausgang schreibt denselben Diagnose-Report (``SAISONALER-HERO-REPORT.md``)
mit Grundcode, Kettennachweis und Versuchsprotokoll – auch im Fehlerfall.

Anbieter (Korrektur 02.10.2026: Puter wird nicht genutzt)
---------------------------------------------------------
Die frühere Puter-Brücke (``PUTER_AUTH_TOKEN``, ``scripts/puter_chat.mjs``)
war im Betrieb nie aktiv – der Hero-Lauf konnte damit grundsätzlich nicht
gelingen. Der Feinschliff läuft jetzt über denselben Multi-Provider-Zugang,
den die KI-Redaktion ohnehin benutzt: ``scripts/llm_client.py`` mit den im
Repo etablierten Gratis-Schlüsseln ``GROQ_API_KEY``, ``NVIDIA_API_KEY``,
``CLOUDFLARE_API_TOKEN``/``CLOUDFLARE_ACCOUNT_ID`` und ``GEMINI_API_KEY``.
Kostenpflichtige Anbieter gibt es nicht. Der erste Anbieter in
``PROVIDER_ORDER``, der eine vollständige und vertragsfeste Fassung liefert,
gewinnt. Nur Standardbibliothek, kein Node, kein npm-Paket.

Fehlt ein frischer Agent-Reach-Brief oder jeder Schlüssel, wird fail-closed
abgebrochen: Die kuratierte saisonale Basis bleibt sichtbar, aber es erscheint
kein als KI-poliert ausgegebener Text.

Aufruf:
  python3 scripts/saisonaler_hero_refresh.py --check
  python3 scripts/saisonaler_hero_refresh.py --fix
  python3 scripts/saisonaler_hero_refresh.py --fix --force
  python3 scripts/saisonaler_hero_refresh.py --set-current --reason "Merge-Entscheid bestätigt"
  python3 scripts/saisonaler_hero_refresh.py --selftest
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover - Workflow installs PyYAML
    raise SystemExit("PyYAML fehlt: python3 -m pip install pyyaml") from exc

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

try:  # gemeinsamer Multi-Provider-Zugang der KI-Redaktion (nur Standardbibliothek)
    import llm_client
except Exception:  # noqa: BLE001 - ohne Client bleibt nur die kuratierte Basis
    llm_client = None

SAISONS = ROOT / "data" / "saisons.yaml"
STATE = ROOT / "data" / "saisonaler_hero_state.json"
HISTORY = ROOT / "data" / "saisonaler_hero_history.jsonl"
RESEARCH_DIR = ROOT / "data" / "research" / "saisonal"
STIL = ROOT / "data" / "schreibstil.yaml"
BRAND = ROOT / "data" / "brand_brain.yaml"
GUARD = ROOT / "scripts" / "saisonale_startseite_guard.py"
REPORT = ROOT / "SAISONALER-HERO-REPORT.md"

# Reihenfolge des Feinschliffs: der erste Anbieter mit Schlüssel gewinnt, bei
# Fehler rückt der nächste nach. Bewusst identisch zur KI-Redaktion, damit es
# genau EINEN Ort für Schlüssel, Modelle und Retries gibt.
# Reihenfolge seit 03.10.2026 (Transportweg-Vertrag T1/T3/T4): drei
# unabhängige Gratis-Hoster desselben OpenAI-Modells, danach Gemini.
# Genau diese Redundanz verhindert den Dauerausfall aus Issue #514 –
# ein leeres Tageskontingent ist dann kein roter Lauf mehr.
# Kostenpflichtige Anbieter gibt es im Repo nicht mehr.
# SSOT der Kette: data/ki_transportweg.yaml → routing.politur
PROVIDER_ORDER = ("groq", "nvidia", "cloudflare", "gemini")
MAX_AGE_DAYS = 21
# Kulanzfenster: Solange die kuratierte Basis den kompletten SEO/GEO-Vertrag und
# die Startseiten-Wache besteht, ist ein Ausfall der KI-Kette (Token, Netz,
# Anbieter-Kontingent) KEIN Live-Schaden. Der Lauf bleibt dann grün, meldet den
# Zustand aber sichtbar als Warnung im Report und im Step-Summary. Erst wenn der
# Ausfall bleibt (Serie) oder die Politur wirklich überaltert, wird eskaliert.
GRACE_DAYS = 14
HARD_STALE_DAYS = MAX_AGE_DAYS + GRACE_DAYS
FAILURE_STREAK_LIMIT = 3
POLISH_ROUNDS = 3
POLISH_BACKOFF_SECONDS = (0, 20, 45)
# Reasoning-Modelle verbrauchen einen Teil des Ausgabebudgets für interne
# Verarbeitung. 700 Tokens führten möglicherweise zu leeren/kurzen Antworten;
# der Finish-Code entscheidet zusätzlich, ob die Antwort vollständig ist.
POLISH_MAX_TOKENS = 3072
POLISH_TIMEOUT_SECONDS = 60
CORE_CATEGORIES = ("strom", "gas", "internet", "versicherung", "konto")
BANNED_PHRASES = (
    "in der heutigen schnelllebigen welt", "in der heutigen zeit",
    "es ist wichtig zu beachten", "zusammenfassend lässt sich sagen",
    "zusammenfassend kann man sagen", "des weiteren", "in diesem artikel werden wir",
    "in diesem artikel erfahren sie", "es gibt viele möglichkeiten",
    "es gibt zahlreiche", "wenn es darum geht", "heutzutage", "in der modernen welt",
    "tauchen wir ein", "lassen sie uns", "der schlüssel zum erfolg", "ein muss für jeden",
    "unverzichtbar für", "das a und o", "die welt der", "in einer welt, in der",
    "entdecke", "entdecken sie", "tauche ein", "willkommen in der welt",
)
LAST_BRIDGE_ERROR: list[str] = []
FORMAL_ANREDE = re.compile(r"\b(Sie|Ihnen|Ihrem|Ihrer|Ihren|Ihres|Ihr|Ihre)\b")
SEASON_BLOCK = re.compile(r"(?ms)(^  - id:\s*(?P<id>[a-z0-9-]+)\s*$.*?)(?=^  - id:|\Z)")


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso_now() -> str:
    return now_utc().isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_date(value: str | None) -> dt.date:
    if not value:
        return now_utc().date()
    return dt.date.fromisoformat(value)


def season_for(day: dt.date, seasons: list[dict]) -> dict | None:
    needle = day.month * 100 + day.day
    for season in seasons:
        try:
            start_month, start_day = str(season["ab"]).split("-", 1)
            end_month, end_day = str(season["bis"]).split("-", 1)
            start = int(start_month) * 100 + int(start_day)
            end = int(end_month) * 100 + int(end_day)
        except (KeyError, TypeError, ValueError):
            continue
        if (start <= end and start <= needle <= end) or (start > end and (needle >= start or needle <= end)):
            return season
    return None


def load_seasons() -> tuple[dict, list[dict]]:
    raw = yaml.safe_load(SAISONS.read_text(encoding="utf-8")) or {}
    seasons = raw.get("saisons") if isinstance(raw, dict) else None
    if not isinstance(seasons, list):
        raise ValueError("data/saisons.yaml braucht eine `saisons`-Liste")
    return raw, [s for s in seasons if isinstance(s, dict)]


def load_json(path: Path, fallback: dict) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else fallback
    except (OSError, json.JSONDecodeError):
        return fallback


def save_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def fingerprint(season: dict) -> str:
    payload = "\x1f".join(str(season.get(k, "")) for k in ("id", "hero_title", "hero_lead"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_history() -> list[dict]:
    rows = []
    if not HISTORY.exists():
        return rows
    for line in HISTORY.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def append_history(row: dict) -> None:
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def snapshot_files(paths: tuple[Path, ...]) -> dict[Path, bytes | None]:
    """Dateien vor einer Mehrdateiänderung vollständig sichern."""
    return {path: path.read_bytes() if path.exists() else None for path in paths}


def restore_files(snapshot: dict[Path, bytes | None]) -> None:
    """Gesicherte Dateien atomar pro Pfad wiederherstellen oder entfernen."""
    for path, content in snapshot.items():
        if content is None:
            path.unlink(missing_ok=True)
        else:
            tmp = path.with_suffix(path.suffix + ".rollback.tmp")
            tmp.write_bytes(content)
            tmp.replace(path)


def research_brief_status(day: dt.date) -> tuple[Path | None, str]:
    """Tagesbrief UND maschinenlesbaren Agent-Reach-Nachweis prüfen.

    Ein vorhandener Dateiname allein belegt weder einen erfolgreichen Abruf
    noch den richtigen Stichtag. Rohsignale bleiben trotzdem keine Fakten.
    """
    expected = RESEARCH_DIR / f"{day.isoformat()}-internet-recherche.md"
    metadata_path = expected.with_suffix(".json")
    try:
        if not expected.read_text(encoding="utf-8").strip():
            return None, "Recherche-Brief ist leer"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, "Tagesbrief oder JSON-Nachweis fehlt"
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None, "Tagesbrief oder JSON-Nachweis ist nicht lesbar"
    if not isinstance(metadata, dict) or metadata.get("datum") != day.isoformat():
        return None, "JSON-Nachweis hat keinen passenden Stichtag"
    if not isinstance(metadata.get("agent_reach"), str) or not metadata["agent_reach"].strip():
        return None, "Agent-Reach-Version im JSON-Nachweis fehlt"
    sources = metadata.get("kanal_ok")
    if isinstance(sources, bool) or not isinstance(sources, int) or sources < 1:
        return None, "JSON-Nachweis meldet keinen erfolgreichen Quellenabruf"
    return expected, "Tagesbrief und JSON-Nachweis vorhanden"


def newest_research_brief(day: dt.date) -> Path | None:
    return research_brief_status(day)[0]


def research_topics(brief: Path, season: dict) -> list[str]:
    """Leitet ausschließlich kontrollierte Themenwörter ab, keine Fakten.

    Aus den Treffertexten der Agent-Reach-JSON-Beilage werden nur bereits in
    data/saisons.yaml erlaubte Keywords ausgewählt. Titel/Zahlen/Behauptungen
    bleiben bewusst außerhalb des KI-Prompts, damit eine frische Meldung
    nicht ungeprüft in die H1 oder den GEO-Lead gelangen kann.
    """
    try:
        metadata = json.loads(brief.with_suffix(".json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []
    results = metadata.get("ergebnisse", {}) if isinstance(metadata, dict) else {}
    if not isinstance(results, dict):
        return []
    signal_texts = []
    # Nur echte Treffertexte, nicht Quellenüberschriften, URLs, Fehlermeldungen
    # oder das Kanalmatrix-Boilerplate. Web-Auszüge fehlen in der JSON-Beilage;
    # sie liefern hier deshalb lieber keinen als einen unbewiesenen Treffer.
    for channel in ("rss", "youtube", "github"):
        entries = results.get(channel, {})
        if not isinstance(entries, dict):
            continue
        for entry in entries.values():
            if not isinstance(entry, dict) or entry.get("fehler"):
                continue
            hits = entry.get("treffer", [])
            if not isinstance(hits, list):
                continue
            for hit in hits:
                if isinstance(hit, dict):
                    for key in ("titel", "beschreibung"):
                        value = hit.get(key)
                        if isinstance(value, str):
                            signal_texts.append(value)
    text = " ".join(signal_texts).lower()
    topics = []
    for keyword in season.get("keywords") or []:
        clean = str(keyword).strip().lower()
        if clean and clean in text and clean not in topics:
            topics.append(clean)
    # Kein Treffer ist kein Treffer: Kuratierte Standardwörter dürfen nicht
    # als tatsächlich beobachtete Agent-Reach-Signale ausgegeben werden.
    return topics[:5]


def style_summary() -> str:
    """Nur Hero-taugliche Stimmsignale aus den bestehenden Stilquellen.

    Das vollständige Artikelprofil verlangt Beispiele, Euro-Beträge und
    Zahlen. Solche Anweisungen widersprechen der Faktenbremse des kurzen
    Hero-Leads und dürfen nicht ungefiltert im selben Prompt stehen.
    """
    try:
        stil = yaml.safe_load(STIL.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        stil = {}
    try:
        brand = yaml.safe_load(BRAND.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        brand = {}
    stil = stil if isinstance(stil, dict) else {}
    brand = brand if isinstance(brand, dict) else {}
    voice = brand.get("voice") if isinstance(brand.get("voice"), dict) else {}
    audience = brand.get("audience") if isinstance(brand.get("audience"), dict) else {}
    tonfall = stil.get("tonfall") if isinstance(stil.get("tonfall"), list) else []
    tone = voice.get("tone") if isinstance(voice.get("tone"), str) else ""
    candidates = [tonfall[0] if tonfall else "", *tone.split(","),
                  audience.get("primary", ""), audience.get("reading_level", "")]
    pieces = []
    for candidate in candidates:
        if not isinstance(candidate, str):
            continue
        text = candidate.strip()
        if text and not re.search(r"[0-9€%]|zahl|euro|preis|frist|quelle|studie", text, re.I):
            pieces.append(text)
    return "\n".join(f"- {item}" for item in pieces) or "- klar, freundlich, konkret, du-Form"


def prompt_for(season: dict, topics: list[str]) -> tuple[str, str]:
    system = f"""Du bist Senior-Copywriter einer deutschen Finanz-Redaktion.
Formuliere ausschließlich eine saisonale H1 und einen GEO-Lead für
FranksFinanzcheck. Schreibe in Franks Stimme:
{style_summary()}

Harte Regeln:
- Keine neuen Fakten: keine Zahlen, Preise, Fristen, Gesetze, Quellen,
  Studien, Anbieter, URLs oder Superlative hinzufügen.
- Du-Ansprache, klar, ruhig, konkret, kein Verkaufsdruck und keine KI-Floskeln.
- Der Lead beginnt exakt mit FranksFinanzcheck. Er nennt die Saison,
  mindestens drei der Themen Strom, Gas, Internet, Versicherungen, Konto und
  den konkreten Nutzen. Er ist ein einzelner, vollständiger Absatz.
- In den Werten: keine Anführungszeichen, kein Markdown, keine Listen,
  keine Emojis und kein HTML. Keine Seitenstruktur oder CTAs ändern.

Antworte nur mit einem vollständigen JSON-Objekt mit genau zwei Textfeldern:
{{"title": "H1 mit 42 bis 100 Zeichen und Spar- oder Vergleichsintention",
 "lead": "Lead mit 220 bis 560 Zeichen und vollständigem Schlusssatz."}}
Keine weiteren Felder, Erklärungen oder Varianten."""
    signal_topics = ", ".join(topics) if topics else "keine passenden Themenwörter gefunden"
    user = f"""AKTIVE SAISON: {season.get('name')}
IN AGENT-REACH-SIGNALEN GEFUNDENE, KURATIERTE THEMENWÖRTER: {signal_topics}
AKTUELLER H1: {season.get('hero_title')}
AKTUELLER LEAD: {season.get('hero_lead')}

Formuliere eine frische, präzise Variante ohne neue Tatsachenbehauptungen."""
    return system, user


def verfuegbare_anbieter() -> list[str]:
    """Anbieter mit Schlüssel, in der festgelegten Reihenfolge."""
    if llm_client is None:
        return []
    return [p for p in PROVIDER_ORDER if llm_client.available(p)]


def _provider_error(exc: Exception) -> str:
    """Nur technische Fehlerklassen melden, niemals Providertexte/Schlüssel."""
    if llm_client is not None and isinstance(exc, llm_client.IncompleteResponseError):
        return f"Antwort nicht abgeschlossen ({exc.reason})"
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code}"
    if isinstance(exc, TimeoutError):
        return "Timeout"
    if isinstance(exc, urllib.error.URLError):
        return "Netzwerkfehler (URLError)"
    return f"Anbieterfehler ({type(exc).__name__})"


def call_model(system: str, user: str, provider: str | None = None) -> tuple[str | None, str, str]:
    """Ein Glied der Kette aufrufen; ohne Angabe Transport-Fallback nutzen.

    Die Hero-Pipeline wählt die Provider einzeln, damit auch ein inhaltlich
    verworfener Kandidat zum nächsten Anbieter führt. Ein Aufruf ist zeitlich
    begrenzt; die Runden-Wiederholung liegt ausschließlich bei polish_candidate.
    """
    if llm_client is None:
        LAST_BRIDGE_ERROR.append("scripts/llm_client.py nicht importierbar")
        return None, "", ""
    verfuegbar = verfuegbare_anbieter()
    anbieter = [provider] if provider in verfuegbar else ([] if provider else verfuegbar)
    if not anbieter:
        LAST_BRIDGE_ERROR.append(
            "kein nutzbarer KI-Schlüssel gesetzt oder angegebener Anbieter nicht verfügbar")
        return None, provider or "", ""
    for name in anbieter:
        modell = llm_client.model_for(name)
        try:
            antwort = llm_client.chat(
                name, system=system, prompt=user, temperature=0.35,
                max_tokens=POLISH_MAX_TOKENS, timeout=POLISH_TIMEOUT_SECONDS,
                attempts=1, require_complete=True, raise_on_error=True, log_errors=False,
            )
        except Exception as exc:  # noqa: BLE001 – keine internen Providerdetails ausgeben
            LAST_BRIDGE_ERROR.append(f"{name}/{modell}: {_provider_error(exc)}")
            continue
        if antwort and antwort.strip():
            return antwort.strip(), name, modell
        LAST_BRIDGE_ERROR.append(f"{name}/{modell}: leere Antwort")
    if provider:
        return None, provider, llm_client.model_for(provider)
    return None, "", ""


def polish_candidate(season: dict, topics: list[str], history: list[dict],
                     attempts: int = POLISH_ROUNDS,
                     sleep=time.sleep) -> tuple[tuple[str, str] | None, list[str], str]:
    """Jeden verfügbaren Gratis-Anbieter je Runde bis zur Vertragsprüfung nutzen.

    Auch Format-, Fakten- und Neuheitsfehler bewirken einen Anbieterwechsel;
    nur technische Wiederholungen hätten #891 nicht behoben. Protokolliert
    werden alle Glieder und Fehlerklassen, aber keine rohen Modellantworten.
    """
    system, user = prompt_for(season, topics)
    protokoll: list[str] = []
    auflage = ""
    anbieter = verfuegbare_anbieter()
    if not anbieter:
        return None, ["Kein Anbieter mit vollständigem Schlüssel verfügbar"], ""
    for runde in range(1, max(1, attempts) + 1):
        if runde > 1:
            sleep(POLISH_BACKOFF_SECONDS[min(runde - 1, len(POLISH_BACKOFF_SECONDS) - 1)])
        for name in anbieter:
            LAST_BRIDGE_ERROR.clear()
            answer, provider, modell = call_model(system, user + auflage, provider=name)
            quelle = f"{provider or name}:{modell or 'unbekannt'}"
            if not answer:
                detail = LAST_BRIDGE_ERROR[-1] if LAST_BRIDGE_ERROR else "keine verwertbare Antwort"
                protokoll.append(f"Runde {runde} ({quelle}): {detail}")
                continue
            parsed = parse_answer(answer)
            if not parsed:
                protokoll.append(f"Runde {runde} ({quelle}): ungültiges oder mehrdeutiges Antwortformat")
                auflage = ("\n\nKORREKTURAUFLAGE: Antworte ausschließlich mit einem "
                           "vollständigen JSON-Objekt mit genau den Textfeldern title und lead.")
                continue
            title, lead = parsed
            errors = validate_candidate(title, lead, season, history)
            # Bei einer erstmals aktiven Saison kann die Historie leer sein.
            # Ein unveränderter Live-Lead ist trotzdem kein neuer Feinschliff.
            current_lead = str(season.get("hero_lead") or "")
            if current_lead and jaccard(lead, current_lead) >= 0.82:
                errors.append("Lead zu ähnlich zur aktuell ausgelieferten Fassung")
            if not errors:
                protokoll.append(f"Runde {runde} ({quelle}): Kandidat besteht den SEO/GEO-Vertrag")
                return (title, lead), protokoll, quelle
            protokoll.append(f"Runde {runde} ({quelle}): verworfen – " + "; ".join(errors))
            auflage = ("\n\nKORREKTURAUFLAGE: Beachte bei der neuen Fassung besonders: "
                       + "; ".join(errors)
                       + ". Vermeide diese Fehler, ohne neue Fakten zu erfinden.")
    return None, protokoll, ""


MARKER_RE = re.compile(r"(?i)^\s*(?:[-*>]\s*)?(?:\*\*)?(TITLE|LEAD)(?:\*\*)?\s*:\s*(?:\*\*)?\s*(.*)$")
OTHER_MARKER_RE = re.compile(r"^\s*(?:#{1,6}\s+|(?:[-*]\s+)?[A-Za-zÄÖÜäöüß][\wÄÖÜäöüß -]{1,30}:\s+)")


def _saeubere_feld(text: str) -> str:
    """Zeilenumbruch/Whitespace vereinheitlichen, Inhalt nicht umschreiben."""
    return " ".join(text.split()).strip()


def _json_felder(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        normalized = key.lower()
        if normalized in result:
            raise ValueError("doppeltes Feld")
        result[normalized] = value
    return result


def parse_answer(answer: str) -> tuple[str, str] | None:
    """Vollständiges JSON oder eindeutig markierte TITLE/LEAD-Felder lesen.

    Ein einzelner Zeilenumbruch im Feld ist erlaubt (Regression #891).
    Duplikate, zusätzliche Absätze/Marker und Begleittext sind dagegen
    mehrdeutig und werden nicht still in den veröffentlichbaren Lead kopiert.
    Der eigentliche Inhalt bleibt für die anschließende Vertragsprüfung erhalten.
    """
    if not isinstance(answer, str) or len(answer) > 8192:
        return None
    text = answer.replace("\r\n", "\n").replace("\r", "\n").strip()
    if text.startswith("```"):
        fence = re.fullmatch(r"```(?:json)?[ \t]*\n(.*?)\n```", text, re.I | re.S)
        if not fence:
            return None
        text = fence.group(1).strip()
    if text.startswith("{"):
        try:
            fields = json.loads(text, object_pairs_hook=_json_felder)
        except (json.JSONDecodeError, ValueError):
            return None
        if not isinstance(fields, dict) or set(fields) != {"title", "lead"}:
            return None
        if not all(isinstance(fields[key], str) for key in ("title", "lead")):
            return None
        if any(re.search(r"\n[ \t]*\n", fields[key]) for key in ("title", "lead")):
            return None
        title, lead = (_saeubere_feld(fields[key]) for key in ("title", "lead"))
        return (title, lead) if title and lead else None

    fields: dict[str, str] = {}
    current = ""
    buffer: list[str] = []
    paragraph_ended = False
    for line in text.split("\n"):
        marker = MARKER_RE.match(line)
        if marker:
            key = marker.group(1).upper()
            if (not current and key != "TITLE") or (current and (current != "TITLE" or key != "LEAD")):
                return None
            if current:
                fields[current] = _saeubere_feld(" ".join(buffer))
            current, buffer, paragraph_ended = key, [marker.group(2)], False
        elif not line.strip():
            if current and _saeubere_feld(" ".join(buffer)):
                paragraph_ended = True
        elif not current or paragraph_ended or OTHER_MARKER_RE.match(line):
            return None
        else:
            buffer.append(line)
    if current:
        fields[current] = _saeubere_feld(" ".join(buffer))
    if set(fields) != {"TITLE", "LEAD"} or not fields["TITLE"] or not fields["LEAD"]:
        return None
    return fields["TITLE"], fields["LEAD"]


def norm(text: str) -> str:
    return " ".join(re.findall(r"[a-zäöüß0-9]+", (text or "").lower().replace("ß", "ss")))


def shingles(text: str, size: int = 4) -> set[str]:
    words = norm(text).split()
    if len(words) < size:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i:i + size]) for i in range(len(words) - size + 1)}


def jaccard(left: str, right: str) -> float:
    a, b = shingles(left), shingles(right)
    return len(a & b) / len(a | b) if a and b else 0.0


def validate_candidate(title: str, lead: str, season: dict, history: list[dict]) -> list[str]:
    errors: list[str] = []
    joined = f"{title} {lead}"
    low = joined.lower()
    if not (42 <= len(title) <= 100):
        errors.append(f"Titel-Länge {len(title)} außerhalb 42–100")
    if not (220 <= len(lead) <= 560):
        errors.append(f"Lead-Länge {len(lead)} außerhalb 220–560")
    if not lead.rstrip().endswith((".", "!", "?")):
        errors.append("Lead endet nicht mit einem vollständigen Satz")
    if not any(word in title.lower() for word in ("sparen", "vergleich", "fixkosten", "günstiger")):
        errors.append("Titel ohne Spar-/Vergleichsintention")
    lead_lower = lead.lower()
    if not re.match(r"^franksfinanzcheck\b", lead_lower):
        errors.append("Lead beginnt nicht mit der Entity FranksFinanzcheck")
    categories = [word for word in CORE_CATEGORIES if word in lead_lower]
    if len(categories) < 3:
        errors.append(f"zu wenige Kernkategorien im Lead: {categories}")
    season_name = str(season.get("name") or "").lower()
    if not season_name or season_name not in lead_lower:
        errors.append("Saisonname fehlt im Lead")
    if not re.search(r"\b(?:du|dir|dich|dein(?:e|en|em|er|es)?)\b", lead_lower):
        errors.append("Du-Ansprache fehlt im Lead")
    if FORMAL_ANREDE.search(joined):
        errors.append("formelle Sie-Anrede")
    hits = [phrase for phrase in BANNED_PHRASES if phrase in low]
    if hits:
        errors.append("KI-Floskel: " + ", ".join(hits))
    if re.search(r"[\d€%]|https?://|www\.|\b(?:zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn|elf|zwölf|hundert|tausend|prozent)\b", joined, re.I):
        errors.append("Zahl, Preis, Prozent oder URL im Text – Faktenvertrag verletzt")
    if re.search(r"[\"'<>`{}\[\]*_\r\n]", joined):
        errors.append("unerlaubtes Markup, Zitat oder Zeilenumbruch")
    for previous in history[-5:]:
        previous_lead = str(previous.get("hero_lead") or "")
        if previous_lead and jaccard(lead, previous_lead) >= 0.82:
            errors.append("Lead zu ähnlich zu einer der letzten fünf Versionen")
            break
    return errors


def yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def rewrite_fields(season_id: str, title: str, lead: str) -> None:
    source = SAISONS.read_text(encoding="utf-8")
    match = next((m for m in SEASON_BLOCK.finditer(source) if m.group("id") == season_id), None)
    if not match:
        raise ValueError(f"Saisonblock {season_id!r} in data/saisons.yaml nicht gefunden")
    block = match.group(1)
    for key, value in (("hero_title", title), ("hero_lead", lead)):
        rx = re.compile(rf"(?m)^(\s+{key}:\s*)\".*\"\s*$")
        if not rx.search(block):
            raise ValueError(f"Saison {season_id!r} hat kein einzeiliges Feld `{key}`")
        block = rx.sub(lambda m: m.group(1) + yaml_quote(value), block, count=1)
    replacement = source[:match.start(1)] + block + source[match.end(1):]
    tmp = SAISONS.with_suffix(".yaml.tmp")
    tmp.write_text(replacement, encoding="utf-8")
    tmp.replace(SAISONS)


def guard_source() -> tuple[bool, str]:
    proc = subprocess.run(
        [sys.executable, str(GUARD), "--source-only"], cwd=ROOT,
        capture_output=True, text=True, timeout=120,
    )
    message = (proc.stdout + "\n" + proc.stderr).strip()
    return proc.returncode == 0, message[-1800:]


def saved_record(season: dict, state: dict) -> dict | None:
    saved = (state.get("saisons") or {}).get(str(season.get("id")))
    return saved if isinstance(saved, dict) else None


def days_since_polish(saved: dict | None, now: dt.datetime) -> int | None:
    """Alter der letzten freigegebenen Fassung in Tagen (None = unbekannt)."""
    if not saved:
        return None
    try:
        last = dt.datetime.fromisoformat(str(saved.get("updated", "")).replace("Z", "+00:00"))
    except ValueError:
        return None
    if last.tzinfo is None:
        last = last.replace(tzinfo=dt.timezone.utc)
    return (now - last).days


def due_state(season: dict, state: dict, force: bool, now: dt.datetime) -> dict:
    """Fälligkeit mit maschinenlesbarem Grundcode.

    Der Code trennt die beiden grundverschiedenen Anlässe, die früher in einem
    einzigen „fällig" verschwammen:

    ``redaktion``  Jemand (Mensch oder Redaktions-Workflow) hat den kuratierten
                   Hero bewusst geändert. Der Live-Text ist dann gerade frisch,
                   nur der Nachweis hinkt hinterher. Das darf keinen täglichen
                   KI-Zwang und keinen roten Lauf auslösen.
    ``rotation``   Die freigegebene Fassung ist älter als MAX_AGE_DAYS – hier
                   ist eine echte saisonale Auffrischung fällig.
    """
    saved = saved_record(season, state)
    age = days_since_polish(saved, now)
    if force:
        return {"due": True, "code": "force", "reason": "manuell erzwungen", "age_days": age}
    if not saved or not saved.get("fingerprint"):
        return {"due": True, "code": "neu",
                "reason": "neue Saison noch nicht mit Agent Reach + KI poliert", "age_days": age}
    if saved.get("fingerprint") != fingerprint(season):
        return {"due": True, "code": "redaktion",
                "reason": "Saisondaten wurden seit der letzten Politur redaktionell verändert",
                "age_days": age}
    if age is None:
        return {"due": True, "code": "zeitstempel",
                "reason": "Zeitstempel der letzten Politur fehlt/ist ungültig", "age_days": None}
    if age >= MAX_AGE_DAYS:
        return {"due": True, "code": "rotation",
                "reason": f"letzte Politur ist {age} Tage alt", "age_days": age}
    if failure_streak(season, state):
        return {"due": True, "code": "wiederholung",
                "reason": "vorheriger Refresh ist noch nicht erfolgreich abgeschlossen", "age_days": age}
    return {"due": False, "code": "aktuell", "reason": "aktuell", "age_days": age}


def is_due(season: dict, state: dict, force: bool, now: dt.datetime) -> tuple[bool, str]:
    """Kompatible Kurzfassung von :func:`due_state` (ältere Aufrufer/Tests)."""
    status = due_state(season, state, force, now)
    return status["due"], status["reason"]


def baseline_healthy(season: dict) -> tuple[bool, list[str], str]:
    """Prüft, ob der aktuell ausgelieferte Saison-Hero den Vertrag erfüllt."""
    title = str(season.get("hero_title") or "").strip()
    lead = str(season.get("hero_lead") or "").strip()
    errors = validate_candidate(title, lead, season, [])
    if errors:
        return False, errors, ""
    healthy, message = guard_source()
    if not healthy:
        return False, ["Startseiten-Wache verwirft den aktuellen Stand"], message
    return True, [], message


def record_baseline(season: dict, state: dict, reason: str, model: str) -> dict:
    """Schreibt den aktuell ausgelieferten Hero als freigegebenen Basisstand.

    Kein Text wird erzeugt: Nur der Nachweis (State + Historie) holt auf, damit
    eine redaktionelle Änderung nicht dauerhaft als „unpoliert" gilt und jeden
    Tag erneut einen KI-Lauf samt Fehl-Issue erzwingt.
    """
    title = str(season.get("hero_title") or "").strip()
    lead = str(season.get("hero_lead") or "").strip()
    record = {
        "updated": iso_now(), "fingerprint": fingerprint(season), "model": model,
        "research_brief": "", "research_sha256": "",
        "set_current": True, "reason": reason,
    }
    updated_state = dict(state)
    updated_state.setdefault("version", 1)
    updated_state["saisons"] = dict(state.get("saisons") or {})
    updated_state["saisons"][str(season["id"])] = record
    snapshot = snapshot_files((STATE, HISTORY))
    try:
        save_json(STATE, updated_state)
        append_history({
            "ts": record["updated"], "season": season["id"], "hero_title": title,
            "hero_lead": lead, "model": model, "research_brief": "", "research_sha256": "",
            "topics": [], "set_current": True, "reason": reason,
        })
    except Exception:
        restore_files(snapshot)
        raise
    state.clear()
    state.update(updated_state)
    return record


def note_failure(season: dict, state: dict, code: str, detail: str) -> int:
    """Zählt Kettenausfälle pro Saison; eine Serie ist das Eskalationssignal."""
    saisons = state.setdefault("saisons", {})
    saved = saisons.get(str(season["id"]))
    if not isinstance(saved, dict):
        saved = {}
        saisons[str(season["id"])] = saved
    streak = int(saved.get("fehler_serie") or 0) + 1
    saved["fehler_serie"] = streak
    saved["letzter_fehler"] = {"ts": iso_now(), "code": code, "detail": detail[-600:]}
    state.setdefault("version", 1)
    save_json(STATE, state)
    return streak


def clear_failure(season: dict, state: dict) -> None:
    saved = (state.get("saisons") or {}).get(str(season["id"]))
    if isinstance(saved, dict):
        # Beide Felder entfernen; ein kurzschließendes `or` ließ bisher bei
        # vorhandener Serie den alten Fehler dauerhaft im State stehen.
        had_streak = saved.pop("fehler_serie", None) is not None
        had_error = saved.pop("letzter_fehler", None) is not None
        if had_streak or had_error:
            save_json(STATE, state)


def failure_streak(season: dict, state: dict) -> int:
    saved = saved_record(season, state)
    return int((saved or {}).get("fehler_serie") or 0)


def chain_status(day: dt.date) -> dict:
    """Beweisbare Vorbedingungen der Kette – für Report, Issue und Eskalation."""
    brief, brief_status = research_brief_status(day)
    anbieter = verfuegbare_anbieter()
    return {
        "research_brief": str(brief.relative_to(ROOT)) if brief else "",
        "brief_vorhanden": bool(brief),
        "brief_status": brief_status,
        "anbieter": anbieter,
        "anbieter_vorhanden": bool(anbieter),
        "llm_client": llm_client is not None,
    }


def escalate(reason_code: str, age: int | None, streak: int, baseline_ok: bool) -> tuple[bool, str]:
    """Entscheidet, ob ein Kettenausfall rot (Issue) oder gelb (Warnung) ist."""
    if not baseline_ok:
        return True, "der live ausgelieferte Saison-Hero verletzt selbst den Vertrag"
    if age is not None and age >= HARD_STALE_DAYS:
        return True, f"die freigegebene Fassung ist {age} Tage alt (Grenze {HARD_STALE_DAYS})"
    if streak >= FAILURE_STREAK_LIMIT:
        return True, f"{streak} Läufe in Folge ohne erfolgreiche KI-Politur"
    return False, ""


def write_report(lines: list[str]) -> None:
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def record_render_failure(season: dict, state: dict, reason: str) -> int:
    """Nach CI-Rollback Render-Ausfall dokumentieren, ohne Erfolg vorzutäuschen."""
    reason = " ".join(reason.split())[:300] or "Render-Beweis nicht erfolgreich"
    previous = REPORT.read_text(encoding="utf-8") if REPORT.exists() else ""
    streak = note_failure(season, state, "render-nachweis-fehlgeschlagen", reason)
    lines = [
        "# Saisonaler Hero – Render-Nachweis fehlgeschlagen", "",
        f"**Saison:** `{season['id']}` · **Stand:** {iso_now()}",
        "**Zustand:** rot – die Veröffentlichung ist nicht freigegeben.",
        f"**Befund:** {reason}",
        f"**Ausfall-Serie:** {streak}", "",
        "Der Workflow hat Hero, State und Historie vor diesem Nachweis auf den "
        "Ausgangsstand zurückgesetzt. Nur der Fehlerzähler und die Recherche "
        "dürfen bei fehlendem Render-Beweis gesichert werden.",
    ]
    if previous:
        lines += ["", "<details><summary>Zwischenstand vor Rücknahme (nicht freigegeben)</summary>",
                  "", previous.rstrip(), "", "</details>"]
    write_report(lines)
    return streak


def selftest() -> int:
    fake = {
        "id": "herbst", "name": "Herbst", "ab": "09-01", "bis": "11-30",
        "hero_title": "Herbst-Check: Bei Strom, Gas & Versicherung Geld sparen",
        "hero_lead": "FranksFinanzcheck hilft dir im Herbst, Strom, Gas, Internet und Versicherungen strukturiert zu vergleichen – unabhängig, verständlich und ohne Verkaufsdruck. Du prüfst zuerst die teuerste Rechnung, erkennst relevante Tarifangaben und findest den passenden nächsten Schritt.",
    }
    ok = True
    ok &= season_for(dt.date(2026, 9, 1), [fake]) is fake
    ok &= season_for(dt.date(2026, 8, 31), [fake]) is None
    ok &= not validate_candidate(fake["hero_title"], fake["hero_lead"], fake, [])
    bad = fake["hero_lead"].replace("Herbst", "Herbst 2026")
    ok &= bool(validate_candidate(fake["hero_title"], bad, fake, []))
    ok &= parse_answer("TITLE: Herbst-Check: Bei Strom, Gas & Versicherung Geld sparen\nLEAD: " + fake["hero_lead"]) is not None

    # Fälligkeits-Codes: redaktionelle Änderung darf nicht wie eine abgelaufene
    # Rotation behandelt werden – genau daran hing die tägliche Fehl-Eskalation.
    now = dt.datetime(2026, 10, 2, tzinfo=dt.timezone.utc)
    frisch = {"version": 1, "saisons": {"herbst": {
        "updated": "2026-09-30T06:00:00Z", "fingerprint": fingerprint(fake)}}}
    ok &= due_state(fake, frisch, False, now)["code"] == "aktuell"
    veraendert = {"version": 1, "saisons": {"herbst": {
        "updated": "2026-09-30T06:00:00Z", "fingerprint": "andere"}}}
    ok &= due_state(fake, veraendert, False, now)["code"] == "redaktion"
    alt = {"version": 1, "saisons": {"herbst": {
        "updated": "2026-08-01T06:00:00Z", "fingerprint": fingerprint(fake)}}}
    ok &= due_state(fake, alt, False, now)["code"] == "rotation"
    ok &= due_state(fake, {}, False, now)["code"] == "neu"
    ok &= due_state(fake, frisch, True, now)["code"] == "force"

    # Eskalationsvertrag: gesunde Basis + kurzer Ausfall = gelb, Serie/Überalterung
    # oder defekte Basis = rot.
    ok &= escalate("rotation", 22, 1, True)[0] is False
    ok &= escalate("rotation", 22, FAILURE_STREAK_LIMIT, True)[0] is True
    ok &= escalate("rotation", HARD_STALE_DAYS, 1, True)[0] is True
    ok &= escalate("rotation", 1, 1, False)[0] is True

    # Wiederholung mit Korrekturauflage statt Einmal-Abbruch.
    neue_h1 = "Herbst-Check: Strom, Gas und Konto gezielt vergleichen"
    neuer_lead = ("FranksFinanzcheck hilft dir im Herbst, Strom, Gas, Internet, Konto und "
                  "Versicherungen systematisch zu vergleichen. Du sammelst zuerst deine "
                  "aktuellen Verträge und ordnest die laufenden Kosten, bevor du Tarifdetails "
                  "und Wechselmöglichkeiten prüfst – unabhängig, verständlich und ohne Verkaufsdruck.")
    antworten = ["kaputt", json.dumps({"title": neue_h1, "lead": neuer_lead})]
    _echtes_call_model = globals()["call_model"]
    _echte_anbieter = globals()["verfuegbare_anbieter"]
    globals()["verfuegbare_anbieter"] = lambda: ["selftest"]
    globals()["call_model"] = lambda system, user, provider=None: (
        (antworten.pop(0), "selftest", "offline") if antworten else (None, "", ""))
    try:
        parsed, protokoll, quelle = polish_candidate(fake, [], [], attempts=3, sleep=lambda _s: None)
    finally:
        globals()["call_model"] = _echtes_call_model
        globals()["verfuegbare_anbieter"] = _echte_anbieter
    ok &= parsed == (neue_h1, neuer_lead) and len(protokoll) == 2
    ok &= quelle == "selftest:offline"

    # Anbieterkette: ohne Schlüssel darf nichts erfunden, aber auch nichts
    # geworfen werden – der Lauf muss die Lage als Klartext melden können.
    LAST_BRIDGE_ERROR.clear()
    umgebung = {k: os.environ.pop(k) for k in
                ("GROQ_API_KEY", "NVIDIA_API_KEY", "CLOUDFLARE_API_TOKEN",
                 "CLOUDFLARE_ACCOUNT_ID", "GEMINI_API_KEY")
                if k in os.environ}
    try:
        antwort, provider, _modell = _echtes_call_model("s", "u")
        ok &= antwort is None and provider == ""
        ok &= bool(LAST_BRIDGE_ERROR) and "Schlüssel" in LAST_BRIDGE_ERROR[-1]
    finally:
        os.environ.update(umgebung)

    if not ok:
        print("❌ Saisonaler-Hero-Selbsttest fehlgeschlagen")
        return 2
    print("✅ Saisonaler-Hero-Selbsttest: Saisonlogik, GEO-Vertrag und Faktenbremse grün.")
    return 0


class CandidateGuardError(Exception):
    """Der Kandidat hat die bestehende Startseiten-Wache nicht bestanden."""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Saisonaler SEO-/GEO-Hero mit Agent Reach + KI-Feinschliff")
    parser.add_argument("--fix", action="store_true", help="bei Fälligkeit die geprüfte Hero-Fassung schreiben")
    parser.add_argument("--force", action="store_true", help="Rotation/Fingerprint übergehen")
    parser.add_argument("--check", action="store_true", help="nur Fälligkeit berichten")
    parser.add_argument("--set-current", action="store_true", help="aktuellen Saison-Hero als freigegebenen Basisstand markieren (keine KI-Änderung)")
    parser.add_argument("--record-render-failure", action="store_true",
                        help="nach CI-Rollback den fehlgeschlagenen Render-Beweis dokumentieren")
    parser.add_argument("--reason", default="", help="Begründung für --set-current oder --record-render-failure")
    parser.add_argument("--date", help="Stichtag YYYY-MM-DD (Tests/Review)")
    parser.add_argument("--selftest", action="store_true", help="offline Selbsttest")
    parser.add_argument("--json", action="store_true", help="maschinenlesbare Ausgabe")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    if args.fix and args.check:
        parser.error("--fix und --check schließen sich aus")
    if args.set_current and (args.fix or args.check):
        parser.error("--set-current darf nicht mit --fix oder --check kombiniert werden")
    if args.record_render_failure and (args.fix or args.check or args.set_current):
        parser.error("--record-render-failure darf nicht mit --fix, --check oder --set-current kombiniert werden")

    day = parse_date(args.date)
    now = now_utc()
    try:
        _, seasons = load_seasons()
    except (OSError, yaml.YAMLError, ValueError) as exc:
        print(f"🛑 Saisonquelle nicht lesbar: {exc}", file=sys.stderr)
        return 2
    season = season_for(day, seasons)
    if not season:
        print(f"🛑 Keine Saison deckt {day.isoformat()} ab", file=sys.stderr)
        return 2
    state = load_json(STATE, {"version": 1, "saisons": {}})

    if args.record_render_failure:
        streak = record_render_failure(season, state, args.reason)
        print(f"🛑 Render-Beweis nicht bestanden; Ausgangsstand zurückgesetzt (Serie {streak}).")
        return 0

    if args.set_current:
        title = str(season.get("hero_title") or "").strip()
        lead = str(season.get("hero_lead") or "").strip()
        ok, errors, gate_message = baseline_healthy(season)
        if not ok:
            print("🛑 Aktueller Saison-Hero ist nicht freigabefähig: "
                  + "; ".join(errors) + ("\n" + gate_message if gate_message else ""),
                  file=sys.stderr)
            return 2
        grund = (args.reason or "aktueller Saison-Hero als freigegebene Basis bestätigt").strip()
        record = record_baseline(season, state, grund, "approved-seasonal-baseline")
        write_report([
            "# Saisonaler Hero – Basisstand bestätigt", "",
            f"**Saison:** `{season['id']}` · **Stand:** {record['updated']}",
            f"**Grund:** {grund}", "",
            "## Bestätigte H1", title, "", "## Bestätigter GEO-Lead", lead, "",
            "---",
            "_Es wurde kein Text neu generiert. Der vorhandene, freigegebene "
            "Saison-Hero wurde als aktueller Basisstand markiert, damit keine "
            "alte Willkommenstext-/Fallback-Rotation den Live-Stand überschreibt._",
        ])
        print(f"✅ Saisonaler Hero als Basisstand markiert: {season['id']}.")
        return 0

    status = due_state(season, state, args.force, now)
    due, reason, code, age = status["due"], status["reason"], status["code"], status["age_days"]
    streak = failure_streak(season, state)
    chain = chain_status(day)
    base = {
        "season": season.get("id"), "date": day.isoformat(), "due": due,
        "reason": reason, "code": code, "age_days": age, "fehler_serie": streak,
        **chain,
    }

    if args.check or not args.fix:
        if args.json:
            print(json.dumps(base, ensure_ascii=False, indent=2))
        else:
            print(f"Saisonaler Hero: {season.get('id')} · {'FÄLLIG' if due else 'aktuell'} – {reason}")
        return 1 if due else 0

    def finish(exit_code: int, zustand: str, kopf: str, zeilen: list[str]) -> int:
        """Jeder Ausgang hinterlässt denselben, prüfbaren Nachweis."""
        report = [
            f"# Saisonaler Hero – {kopf}", "",
            f"**Saison:** `{season.get('id')}` · **Stichtag:** {day.isoformat()} · "
            f"**Stand:** {iso_now()}",
            f"**Zustand:** {zustand} · **Grundcode:** `{code}` · **Exit:** `{exit_code}`",
            f"**Fälligkeitsgrund:** {reason}",
            f"**Alter der bisherigen Fassung zu Laufbeginn:** "
            + (f"{age} Tage (Rotation {MAX_AGE_DAYS}, harte Grenze {HARD_STALE_DAYS})"
               if age is not None else "unbekannt"),
            "", "## Kettennachweis", "",
            "| Vorbedingung | Status |", "|---|---|",
            f"| Agent-Reach-Brief + JSON ({day.isoformat()}) | {'✅ ' + chain['research_brief'] if chain['brief_vorhanden'] else '❌ ' + chain['brief_status']} |",
            f"| KI-Anbieter mit Schlüssel (nicht auf Gültigkeit geprüft) | {'✅ ' + ', '.join(chain['anbieter']) if chain['anbieter_vorhanden'] else '❌ keiner'} |",
            f"| `scripts/llm_client.py` | {'✅ geladen' if chain['llm_client'] else '❌ nicht importierbar'} |",
            f"| Ausfall-Serie | {failure_streak(season, load_json(STATE, {})) or 0} (Eskalation ab {FAILURE_STREAK_LIMIT}) |",
            "",
        ]
        report.extend(zeilen)
        report.extend([
            "", "---",
            "_Automatisch verändert werden ausschließlich `hero_title` und `hero_lead` "
            "in `data/saisons.yaml`; Templates, CSS, Links und CTAs bleiben unberührt. "
            "Neue Fakten sind untersagt; die automatische Prüfung ersetzt keine "
            "vollständige redaktionelle Faktenprüfung._",
        ])
        write_report(report)
        # Ampel maschinenlesbar an den Workflow geben: grün darf ein offenes
        # Störungs-Issue schließen, gelb hält es bewusst offen.
        ampel = "gruen" if zustand.startswith("grün") else ("gelb" if zustand.startswith("gelb") else "rot")
        output = os.environ.get("GITHUB_OUTPUT")
        if output:
            try:
                with open(output, "a", encoding="utf-8") as fh:
                    fh.write(f"ampel={ampel}\nzustand={zustand}\ngrundcode={code}\n")
            except OSError:
                pass
        if args.json:
            aktuelle_serie = failure_streak(season, load_json(STATE, {}))
            print(json.dumps({**base, "fehler_serie": aktuelle_serie,
                              "zustand": zustand, "exit": exit_code},
                             ensure_ascii=False, indent=2))
        return exit_code

    if not due:
        clear_failure(season, state)
        return finish(0, "grün – nichts zu tun", "kein Refresh nötig",
                      [f"Die freigegebene Fassung ist aktuell: {reason}."])

    # Stufe 1: Einen gesunden Redaktionsstand ohne frühere Störung einholen.
    # Bei offener Ausfallserie darf eine redaktionelle Änderung jedoch keinen
    # erfolgreichen KI-Lauf vortäuschen oder den Fehlerzähler zurücksetzen.
    if code == "redaktion" and not args.force:
        ok, errors, gate_message = baseline_healthy(season)
        if not ok:
            print("🛑 Der redaktionell geänderte Saison-Hero verletzt den Vertrag: "
                  + "; ".join(errors), file=sys.stderr)
            return finish(2, "rot – kuratierter Stand defekt",
                          "Redaktionsstand nicht freigabefähig",
                          ["## Befunde", ""] + [f"- {e}" for e in errors]
                          + ([""] + ["```", gate_message, "```"] if gate_message else []))
        if not streak:
            grund = ("redaktionell geänderter Saison-Hero automatisch als geprüfte Basis "
                     "übernommen (SEO/GEO-Vertrag und Startseiten-Wache bestanden)")
            record_baseline(season, state, grund, "approved-seasonal-baseline")
            print(f"✅ Redaktionsstand übernommen: {season['id']} – kein KI-Lauf nötig.")
            return finish(0, "grün – kuratierte Redaktion übernommen",
                          "Redaktionsstand als Basis bestätigt", [
                              "## Übernommene H1", str(season.get("hero_title")), "",
                              "## Übernommener GEO-Lead", str(season.get("hero_lead")), "",
                              "Es wurde **kein** Text generiert und nichts als KI-poliert "
                              "ausgegeben. Die nächste turnusmäßige Politur ist in "
                              f"{MAX_AGE_DAYS} Tagen fällig.",
                          ])
        print("ℹ️ Redaktionsstand ist geprüft; offene KI-Ausfallserie wird nicht "
              "zurückgesetzt und die Textkette erneut versucht.")

    # Stufe 2: Vorbedingungen der Kette. Fehlen sie, entsteht kein stiller
    # Fallback – aber auch kein täglicher Fehlalarm, solange der Live-Hero
    # geprüft, frisch und vertragsfest ist.
    hindernisse = []
    if not chain["brief_vorhanden"]:
        hindernisse.append("frischer Agent-Reach-Nachweis fehlt oder ist ungültig: "
                           f"{chain['brief_status']} "
                           f"(erwartet: data/research/saisonal/{day.isoformat()}-internet-recherche.md + .json)")
    if not chain["llm_client"]:
        hindernisse.append("scripts/llm_client.py ist nicht importierbar")
    elif not chain["anbieter_vorhanden"]:
        hindernisse.append("kein KI-Schlüssel gesetzt – erwartet wird einer der "
                           "kostenlosen Zugänge GROQ_API_KEY, NVIDIA_API_KEY, "
                           "CLOUDFLARE_API_TOKEN+CLOUDFLARE_ACCOUNT_ID oder "
                           "GEMINI_API_KEY; ohne Schlüssel wird kein Text als "
                           "KI-poliert ausgegeben")

    baseline_ok, baseline_errors, baseline_message = baseline_healthy(season)

    if hindernisse:
        streak = note_failure(season, state, "kette-unvollstaendig", "; ".join(hindernisse))
        hart, warum = escalate(code, age, streak, baseline_ok)
        zeilen = ["## Blockierte Vorbedingungen", ""] + [f"- {h}" for h in hindernisse]
        if not baseline_ok:
            zeilen += ["", "## Zusätzlich: Live-Hero defekt", ""] + [f"- {e}" for e in baseline_errors]
        if hart:
            print("🛑 Textkette nicht lauffähig: " + "; ".join(hindernisse)
                  + f" · Eskalation, weil {warum}.", file=sys.stderr)
            return finish(3, f"rot – {warum}", "Kette nicht lauffähig",
                          zeilen + ["", f"**Eskalation:** {warum}."])
        print(f"::warning title=Saisonaler Hero::Textkette pausiert "
              f"({'; '.join(hindernisse)}). Der geprüfte Saison-Hero bleibt live; "
              f"Eskalation ab {FAILURE_STREAK_LIMIT} Läufen in Folge oder "
              f"{HARD_STALE_DAYS} Tagen Alter.")
        return finish(0, "gelb – Kette pausiert, geprüfte Basis bleibt live",
                      "Kette pausiert (sichtbar, kein stiller Fallback)",
                      zeilen + ["", "Der live ausgelieferte Saison-Hero besteht SEO/GEO-Vertrag "
                                "und Startseiten-Wache. Es wurde nichts überschrieben und nichts "
                                "als KI-poliert ausgegeben.",
                                f"Serie: {streak} von {FAILURE_STREAK_LIMIT} bis zur Eskalation."])

    # Stufe 3: KI-Feinschliff mit Wiederholung und Korrekturauflage.
    brief = newest_research_brief(day)
    topics = research_topics(brief, season)
    history = read_history()
    parsed, protokoll, quelle = polish_candidate(season, topics, history)
    if not parsed:
        streak = note_failure(season, state, "ki-ohne-gueltige-fassung", " | ".join(protokoll))
        hart, warum = escalate(code, age, streak, baseline_ok)
        zeilen = ["## Versuchsprotokoll", ""] + [f"- {p}" for p in protokoll]
        if not baseline_ok:
            zeilen += ["", "## Zusätzlich: Live-Hero defekt", ""] + [f"- {e}" for e in baseline_errors]
            if baseline_message:
                zeilen += ["", "```", baseline_message, "```"]
        if hart:
            print("🛑 Kein Anbieter lieferte eine vertragsfeste Fassung: " + " | ".join(protokoll)
                  + f" · Eskalation, weil {warum}.", file=sys.stderr)
            return finish(4, f"rot – {warum}", "Keine vertragsfeste KI-Fassung",
                          zeilen + ["", f"**Eskalation:** {warum}."])
        print("::warning title=Saisonaler Hero::Kein Anbieter lieferte eine vertragsfeste Fassung "
              f"({len(protokoll)} Versuche). Der geprüfte Saison-Hero bleibt unverändert live.")
        return finish(0, "gelb – Kandidaten verworfen, geprüfte Basis bleibt live",
                      "Kandidaten verworfen (Faktenbremse hat gegriffen)",
                      zeilen + ["", f"Serie: {streak} von {FAILURE_STREAK_LIMIT} bis zur Eskalation."])

    title, lead = parsed
    # Auch State und Historie gehören zur Transaktion: Ein Fehler NACH der
    # Quell-Wache darf weder einen halben Hero noch einen falschen Nachweis
    # hinterlassen. Der Render-Beweis folgt zusätzlich im Workflow.
    paths = (SAISONS, STATE, HISTORY)
    try:
        original = snapshot_files(paths)
    except OSError as exc:
        print(f"🛑 Ausgangsstand nicht sicherbar: {type(exc).__name__}", file=sys.stderr)
        return finish(2, "rot – Schreibpfad unsicher", "Ausgangsstand nicht sicherbar",
                      [f"Fehlerklasse: `{type(exc).__name__}` – es wurde nichts geschrieben."])
    try:
        brief_hash = hashlib.sha256(brief.read_bytes()).hexdigest()
        metadata_path = brief.with_suffix(".json")
        metadata_hash = hashlib.sha256(metadata_path.read_bytes()).hexdigest()
        rewrite_fields(str(season["id"]), title, lead)
        healthy, gate_message = guard_source()
        if not healthy:
            raise CandidateGuardError(gate_message)
        _, changed_seasons = load_seasons()
        changed = next(s for s in changed_seasons if s.get("id") == season.get("id"))
        record = {
            "updated": iso_now(), "fingerprint": fingerprint(changed), "model": quelle,
            "research_brief": str(brief.relative_to(ROOT)), "research_sha256": brief_hash,
            "research_json": str(metadata_path.relative_to(ROOT)), "research_json_sha256": metadata_hash,
        }
        state.setdefault("version", 1)
        state.setdefault("saisons", {})[str(season["id"])] = record
        save_json(STATE, state)
        append_history({
            "ts": record["updated"], "season": season["id"], "hero_title": title,
            "hero_lead": lead, "model": record["model"], "research_brief": record["research_brief"],
            "research_sha256": brief_hash, "research_json": record["research_json"],
            "research_json_sha256": metadata_hash, "topics": topics,
        })
    except Exception as exc:  # noqa: BLE001 – vollständiger Rollback vor jeder Fehlermeldung
        try:
            restore_files(original)
        except OSError as rollback_exc:
            print(f"🛑 Rollback fehlgeschlagen: {type(rollback_exc).__name__}", file=sys.stderr)
            return finish(2, "rot – Rollback fehlgeschlagen", "Manuelle Prüfung erforderlich",
                          ["Der Ausgangsstand konnte nicht vollständig wiederhergestellt werden. "
                           "Nichts automatisch veröffentlichen; Lauf-Arbeitsverzeichnis prüfen."])
        restored_state = load_json(STATE, {"version": 1, "saisons": {}})
        rejected_by_guard = isinstance(exc, CandidateGuardError)
        failure_code = "wache-verwirft-kandidat" if rejected_by_guard else "schreibfehler"
        detail = str(exc) if rejected_by_guard else type(exc).__name__
        note_failure(season, restored_state, failure_code, detail)
        print(f"🛑 Kandidat nicht übernommen ({failure_code}); Ausgangsstand zurückgesetzt.",
              file=sys.stderr)
        if rejected_by_guard:
            return finish(2, "rot – Wache verwirft Kandidat", "Kandidat von der Wache verworfen",
                          ["## Wache", "", "```", detail, "```"])
        return finish(2, "rot – Schreibpfad unsicher", "Schreibvorgang abgebrochen",
                      [f"Fehlerklasse: `{detail}` – Hero und Historie wurden zurückgesetzt."])

    print(f"✅ Saisonaler Hero poliert: {season['id']} · Agent Reach + {record['model']}.")
    return finish(0, "grün – Agent Reach + KI-Feinschliff", "Agent Reach + KI-Feinschliff", [
        f"**Agent-Reach-Brief:** `{record['research_brief']}` (SHA-256 `{brief_hash[:12]}…`)",
        f"**JSON-Nachweis:** `{record['research_json']}` (SHA-256 `{metadata_hash[:12]}…`)",
        f"**Textmodell:** `{record['model']}` über `scripts/llm_client.py`",
        f"**Themen aus Signalen:** {', '.join(topics) or 'keine passenden Themenwörter'}", "",
        "Der Kandidat hat die Quellprüfung bestanden; eine Veröffentlichung im "
        "Workflow ist erst nach erfolgreichem Hugo-Build und Render-Gates erlaubt.", "",
        "## Neue H1", title, "", "## Neuer GEO-Lead", lead, "",
        "## Versuchsprotokoll", "",
    ] + [f"- {p}" for p in protokoll])


if __name__ == "__main__":
    raise SystemExit(main())
