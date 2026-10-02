#!/usr/bin/env python3
"""Saisonaler Startseiten-Hero: Agent Reach + Claude, sicher automatisiert.

Der alte, statische Willkommenstext in ``hugo.toml`` wurde absichtlich
entfernt. Die Startseite nimmt ihre H1 und ihren Antwort-zuerst-Lead aus der
jeweils aktiven Saison in ``data/saisons.yaml``. Dieses Skript verfeinert nur
``hero_title`` und ``hero_lead`` – nie Templates, Links, CTAs, CSS oder Fakten.

Kette
-----
1. Der Workflow erzeugt vorher mit Agent Reach einen LESENDEN Recherche-Brief
   unter ``data/research/saisonal/``. Der Brief ist ein Signal-Pool, keine
   Quelle für Behauptungen.
2. Claude Sonnet 5 poliert daraus mit Franks Stilprofil eine saisonale,
   suchintentionklare Passage. Der Prompt bekommt nur kontrollierte saisonale
   Themen, keine unbestätigten Behauptungen aus dem Brief.
3. Eine lokale Verifikation verlangt Entity-first, Suchintention, mindestens
   drei Kernkategorien, du-Ansprache, keine Zahlen/URLs/Quellenbehauptungen,
   keine KI-Floskeln und ausreichende Neuheit.
4. Die bestehende Startseiten-Wache prüft danach Schema, Markenstimme, Farben
   und den Render-Vertrag. Fällt irgendeine Ebene durch, wird nichts geschrieben.

Dauerfestigkeit (Premium-Fix 02.10.2026)
----------------------------------------
Früher galt jede Abweichung vom gespeicherten Fingerprint als „fällig". Eine
redaktionelle Änderung am Hero machte den Lauf damit dauerhaft fällig – und
jeder Ausfall der Claude-Kette (fehlender Token, Kontingent, Netz) erzeugte
täglich einen roten Lauf plus Fehl-Issue, obwohl der live ausgelieferte Hero
geprüft und frisch war. Drei Stufen beenden das:

* **Stufe 1 – Redaktion einholen:** Ist der Hero redaktionell geändert worden
  und besteht er SEO/GEO-Vertrag *und* Startseiten-Wache, wird er automatisch
  als geprüfter Basisstand übernommen (Modell ``approved-seasonal-baseline``).
  Es wird nichts generiert und nichts als KI-poliert ausgegeben; nur der
  Nachweis holt auf. Besteht er den Vertrag nicht, bleibt der Lauf hart rot.
* **Stufe 2 – Kette mit Wiederholung:** Claude wird bis zu drei Mal befragt;
  verworfene Kandidaten gehen als präzise Korrekturauflage zurück in den
  Prompt. Jeder Versuch steht im Report.
* **Stufe 3 – gestufte Eskalation:** Ein Kettenausfall bei gesunder, frischer
  Basis ist gelb (Warnung + Report + Ausfallzähler im State), kein stiller
  Fallback. Rot wird es erst bei defektem Live-Hero, bei
  ``MAX_AGE_DAYS + GRACE_DAYS`` Tagen Alter oder nach
  ``FAILURE_STREAK_LIMIT`` Ausfällen in Folge.

Jeder Ausgang schreibt denselben Diagnose-Report (``SAISONALER-HERO-REPORT.md``)
mit Grundcode, Kettennachweis und Versuchsprotokoll – auch im Fehlerfall.

Claude wird ausschliesslich kostenlos über die vorhandene Puter-Brücke
(``scripts/puter_chat.mjs``) mit ``claude-sonnet-5`` genutzt. Kein
Anthropic-API-Key, kein Modellfallback. Fehlt ein frischer Agent-Reach-Brief
oder der Puter-Token, wird fail-closed abgebrochen: Die kuratierte saisonale
Basis bleibt sichtbar, aber es erscheint kein als KI-poliert ausgegebener Text.

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
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover - Workflow installs PyYAML
    raise SystemExit("PyYAML fehlt: python3 -m pip install pyyaml") from exc

ROOT = Path(__file__).resolve().parent.parent
SAISONS = ROOT / "data" / "saisons.yaml"
STATE = ROOT / "data" / "saisonaler_hero_state.json"
HISTORY = ROOT / "data" / "saisonaler_hero_history.jsonl"
RESEARCH_DIR = ROOT / "data" / "research" / "saisonal"
BRUECKE = ROOT / "scripts" / "puter_chat.mjs"
STIL = ROOT / "data" / "schreibstil.yaml"
BRAND = ROOT / "data" / "brand_brain.yaml"
GUARD = ROOT / "scripts" / "saisonale_startseite_guard.py"
REPORT = ROOT / "SAISONALER-HERO-REPORT.md"

MODEL = "claude-sonnet-5"
MAX_AGE_DAYS = 21
# Kulanzfenster: Solange die kuratierte Basis den kompletten SEO/GEO-Vertrag und
# die Startseiten-Wache besteht, ist ein Ausfall der Claude-Kette (Token, Netz,
# Puter-Kontingent) KEIN Live-Schaden. Der Lauf bleibt dann grün, meldet den
# Zustand aber sichtbar als Warnung im Report und im Step-Summary. Erst wenn der
# Ausfall bleibt (Serie) oder die Politur wirklich überaltert, wird eskaliert.
GRACE_DAYS = 14
HARD_STALE_DAYS = MAX_AGE_DAYS + GRACE_DAYS
FAILURE_STREAK_LIMIT = 3
CLAUDE_ATTEMPTS = 3
CLAUDE_BACKOFF_SECONDS = (0, 20, 45)
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


def newest_research_brief(day: dt.date) -> Path | None:
    """Nur ein Brief vom selben UTC-Tag zählt als Recherche-Vorleistung.

    Ein alter Brief wäre für eine saisonale Aktualisierung lediglich Dekor. Die
    Datei wird vom Workflow unmittelbar vor Claude erzeugt; ihre Existenz ist
    daher ein überprüfbarer Agent-Reach-Nachweis, ohne Rohsignale als Fakten zu
    behandeln.
    """
    expected = RESEARCH_DIR / f"{day.isoformat()}-internet-recherche.md"
    return expected if expected.is_file() else None


def research_topics(brief: Path, season: dict) -> list[str]:
    """Leitet ausschließlich kontrollierte Themenwörter ab, keine Fakten.

    Aus dem Agent-Reach-Brief werden nur bereits in data/saisons.yaml erlaubte
    Keywords ausgewählt. Titel/Zahlen/Behauptungen bleiben bewusst außerhalb
    des Claude-Prompts, damit eine frische Meldung nicht ungeprüft in die H1
    oder den GEO-Lead gelangen kann.
    """
    text = brief.read_text(encoding="utf-8", errors="ignore").lower()
    topics = []
    for keyword in season.get("keywords") or []:
        clean = str(keyword).strip().lower()
        if clean and clean in text and clean not in topics:
            topics.append(clean)
    return topics[:5] or [str(x) for x in (season.get("keywords") or [])[:3]]


def style_summary() -> str:
    """Kleiner, persönlicher Stil-Auszug statt eines zweiten Stilprofils."""
    pieces = []
    for path, keys in ((STIL, ("haltung", "satzrhythmus", "tonfall", "hebel")),
                       (BRAND, ("voice", "audience"))):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            data = {}
        for key in keys:
            value = data.get(key) if isinstance(data, dict) else None
            if isinstance(value, list):
                pieces.extend(str(x).strip() for x in value[:3] if str(x).strip())
            elif isinstance(value, dict):
                pieces.extend(f"{k}: {v}" for k, v in list(value.items())[:3])
            elif value:
                pieces.append(str(value).strip())
    return "\n".join(f"- {item}" for item in pieces[:12]) or "- klar, freundlich, konkret, du-Form"


def prompt_for(season: dict, topics: list[str]) -> tuple[str, str]:
    system = f"""Du bist Senior-Copywriter einer deutschen Finanz-Redaktion auf
Premium-Niveau. Du polierst ausschließlich eine kurze saisonale H1 plus einen
GEO-Lead für FranksFinanzcheck. Schreibe in Franks persönlicher Stimme:
{style_summary()}

Harte Regeln:
- Keine Recherche-Fakten erfinden oder aus Signalen übernehmen: keine Zahlen,
  Preise, Fristen, Gesetze, Quellen, Studien, Anbieter, URLs oder Superlative.
- Du-Ansprache, klar, ruhig, konkret, kein Verkaufsdruck und keine KI-Floskeln.
- Der Lead beginnt buchstäblich mit "FranksFinanzcheck". Er ist eine
  eigenständige Antwortpassage: Saison, mindestens drei der Themen Strom, Gas,
  Internet, Versicherungen, Konto und der Nutzen des Vergleichs sind ohne
  Seitenkontext verständlich.
- Keine Anführungszeichen, kein Markdown, keine Listen, keine Emojis, kein HTML.
- Ändere nur Sprache und Reihenfolge, nicht die Seitenstruktur oder CTAs.

Antworte exakt in zwei Zeilen:
TITLE: <42 bis 100 Zeichen, klarer Spar-/Vergleichsnutzen>
LEAD: <220 bis 560 Zeichen, ein Absatz>"""
    user = f"""AKTIVE SAISON: {season.get('name')} ({season.get('zeitraum')})
KURATIERTER SAISONHINWEIS: {season.get('hinweis')}
ERLAUBTE THEMEN, in Agent-Reach-Signalen erneut sichtbar: {', '.join(topics)}

AKTUELLER H1: {season.get('hero_title')}
AKTUELLER LEAD: {season.get('hero_lead')}

Formuliere eine frische, präzise Variante. Der Hinweis und die Themen geben nur
Kontext; mache daraus keine neue Tatsachenbehauptung."""
    return system, user


def call_claude(system: str, user: str) -> str | None:
    payload = json.dumps({
        "system": system,
        "user": user,
        "model": MODEL,
        "temperature": 0.45,
        "max_tokens": 700,
    })
    try:
        proc = subprocess.run(
            ["node", str(BRUECKE)], input=payload, text=True, capture_output=True, timeout=300,
        )
    except FileNotFoundError:
        LAST_BRIDGE_ERROR.append("node nicht gefunden – Puter-Brücke nicht ausführbar")
        return None
    except subprocess.TimeoutExpired:
        LAST_BRIDGE_ERROR.append("Zeitüberschreitung (300 s) der Puter-Brücke")
        return None
    if proc.returncode != 0:
        LAST_BRIDGE_ERROR.append(
            f"Puter-Brücke Exit {proc.returncode}: {(proc.stderr or '').strip()[-400:]}")
        return None
    text = (proc.stdout or "").strip()
    if not text:
        LAST_BRIDGE_ERROR.append("Puter-Brücke lieferte eine leere Antwort")
        return None
    return text


def claude_candidate(season: dict, topics: list[str], history: list[dict],
                     attempts: int = CLAUDE_ATTEMPTS,
                     sleep=time.sleep) -> tuple[tuple[str, str] | None, list[str]]:
    """Holt eine vertragsfeste Fassung – mit Wiederholung statt Einmal-Versuch.

    Ein einzelner Netz-, Kontingent- oder Formatfehler hat den Lauf früher
    sofort rot gemacht. Jetzt wird bis zu ``attempts`` mal versucht; abgelehnte
    Kandidaten gehen als präzise Korrekturauflage zurück in den Prompt, statt
    verworfen zu werden. Der Protokollpfad bleibt vollständig nachweisbar.
    """
    system, user = prompt_for(season, topics)
    protokoll: list[str] = []
    auflage = ""
    for attempt in range(1, max(1, attempts) + 1):
        if attempt > 1:
            sleep(CLAUDE_BACKOFF_SECONDS[min(attempt - 1, len(CLAUDE_BACKOFF_SECONDS) - 1)])
        LAST_BRIDGE_ERROR.clear()
        answer = call_claude(system, user + auflage)
        if not answer:
            protokoll.append(f"Versuch {attempt}: keine Antwort – "
                             + (LAST_BRIDGE_ERROR[-1] if LAST_BRIDGE_ERROR else "unbekannter Brückenfehler"))
            continue
        parsed = parse_answer(answer)
        if not parsed:
            protokoll.append(f"Versuch {attempt}: Antwort ohne gültiges TITLE/LEAD-Format")
            auflage = ("\n\nKORREKTURAUFLAGE: Antworte ausschließlich in genau zwei Zeilen, "
                       "die erste beginnt mit 'TITLE: ', die zweite mit 'LEAD: '.")
            continue
        title, lead = parsed
        errors = validate_candidate(title, lead, season, history)
        if not errors:
            protokoll.append(f"Versuch {attempt}: Kandidat besteht den SEO/GEO-Vertrag")
            return (title, lead), protokoll
        protokoll.append(f"Versuch {attempt}: verworfen – " + "; ".join(errors))
        auflage = "\n\nKORREKTURAUFLAGE: Die letzte Fassung wurde verworfen: " + "; ".join(errors) \
                  + ". Behebe genau diese Punkte, ohne neue Fakten zu erfinden."
    return None, protokoll


def parse_answer(answer: str) -> tuple[str, str] | None:
    title = re.search(r"(?mi)^TITLE:\s*(.+?)\s*$", answer or "")
    lead = re.search(r"(?mi)^LEAD:\s*(.+?)\s*$", answer or "")
    if not title or not lead:
        return None
    return title.group(1).strip(), lead.group(1).strip()


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
    if not any(word in title.lower() for word in ("sparen", "vergleich", "fixkosten", "günstiger")):
        errors.append("Titel ohne Spar-/Vergleichsintention")
    if not lead.lower().startswith("franksfinanzcheck"):
        errors.append("Lead beginnt nicht mit der Entity FranksFinanzcheck")
    categories = [word for word in CORE_CATEGORIES if word in low]
    if len(categories) < 3:
        errors.append(f"zu wenige Kernkategorien: {categories}")
    if str(season.get("name", "")).lower() not in low:
        errors.append("Saisonname fehlt")
    if FORMAL_ANREDE.search(joined):
        errors.append("formelle Sie-Anrede")
    hits = [phrase for phrase in BANNED_PHRASES if phrase in low]
    if hits:
        errors.append("KI-Floskel: " + ", ".join(hits))
    if re.search(r"[\d€%]|https?://|www\.", joined, re.I):
        errors.append("Zahl, Preis, Prozent oder URL im Text – Faktenvertrag verletzt")
    if re.search(r"[\"'<>`{}\[\]\r\n]", joined):
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
                   Claude-Zwang und keinen roten Lauf auslösen.
    ``rotation``   Die freigegebene Fassung ist älter als MAX_AGE_DAYS – hier
                   ist eine echte saisonale Auffrischung fällig.
    """
    saved = saved_record(season, state)
    age = days_since_polish(saved, now)
    if force:
        return {"due": True, "code": "force", "reason": "manuell erzwungen", "age_days": age}
    if not saved or not saved.get("fingerprint"):
        return {"due": True, "code": "neu",
                "reason": "neue Saison noch nicht mit Agent Reach + Claude poliert", "age_days": age}
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
    Tag erneut einen Claude-Lauf samt Fehl-Issue erzwingt.
    """
    title = str(season.get("hero_title") or "").strip()
    lead = str(season.get("hero_lead") or "").strip()
    record = {
        "updated": iso_now(), "fingerprint": fingerprint(season), "model": model,
        "research_brief": "", "research_sha256": "",
        "set_current": True, "reason": reason,
    }
    state.setdefault("version", 1)
    state.setdefault("saisons", {})[str(season["id"])] = record
    save_json(STATE, state)
    append_history({
        "ts": record["updated"], "season": season["id"], "hero_title": title,
        "hero_lead": lead, "model": model, "research_brief": "", "research_sha256": "",
        "topics": [], "set_current": True, "reason": reason,
    })
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
    if isinstance(saved, dict) and (saved.pop("fehler_serie", None) is not None
                                    or saved.pop("letzter_fehler", None) is not None):
        save_json(STATE, state)


def failure_streak(season: dict, state: dict) -> int:
    saved = saved_record(season, state)
    return int((saved or {}).get("fehler_serie") or 0)


def chain_status(day: dt.date) -> dict:
    """Beweisbare Vorbedingungen der Kette – für Report, Issue und Eskalation."""
    brief = newest_research_brief(day)
    return {
        "research_brief": str(brief.relative_to(ROOT)) if brief else "",
        "brief_vorhanden": bool(brief),
        "token_vorhanden": bool((os.environ.get("PUTER_AUTH_TOKEN") or "").strip()),
        "bruecke_vorhanden": BRUECKE.is_file(),
    }


def escalate(reason_code: str, age: int | None, streak: int, baseline_ok: bool) -> tuple[bool, str]:
    """Entscheidet, ob ein Kettenausfall rot (Issue) oder gelb (Warnung) ist."""
    if not baseline_ok:
        return True, "der live ausgelieferte Saison-Hero verletzt selbst den Vertrag"
    if age is not None and age >= HARD_STALE_DAYS:
        return True, f"die freigegebene Fassung ist {age} Tage alt (Grenze {HARD_STALE_DAYS})"
    if streak >= FAILURE_STREAK_LIMIT:
        return True, f"{streak} Läufe in Folge ohne erfolgreiche Claude-Politur"
    return False, ""


def write_report(lines: list[str]) -> None:
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
    antworten = ["kaputt", f"TITLE: {fake['hero_title']}\nLEAD: {fake['hero_lead']}"]
    _echtes_call_claude = globals()["call_claude"]
    globals()["call_claude"] = lambda system, user: antworten.pop(0) if antworten else None
    try:
        parsed, protokoll = claude_candidate(fake, [], [], attempts=3, sleep=lambda _s: None)
    finally:
        globals()["call_claude"] = _echtes_call_claude
    ok &= parsed == (fake["hero_title"], fake["hero_lead"]) and len(protokoll) == 2

    if not ok:
        print("❌ Saisonaler-Hero-Selbsttest fehlgeschlagen")
        return 2
    print("✅ Saisonaler-Hero-Selbsttest: Saisonlogik, GEO-Vertrag und Faktenbremse grün.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Saisonaler SEO-/GEO-Hero mit Agent Reach + Claude")
    parser.add_argument("--fix", action="store_true", help="bei Fälligkeit die geprüfte Hero-Fassung schreiben")
    parser.add_argument("--force", action="store_true", help="Rotation/Fingerprint übergehen")
    parser.add_argument("--check", action="store_true", help="nur Fälligkeit berichten")
    parser.add_argument("--set-current", action="store_true", help="aktuellen Saison-Hero als freigegebenen Basisstand markieren (keine KI-Änderung)")
    parser.add_argument("--reason", default="", help="Begründung für --set-current (Merge/Freigabe-Akte)")
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
            f"**Alter der freigegebenen Fassung:** "
            + (f"{age} Tage (Rotation {MAX_AGE_DAYS}, harte Grenze {HARD_STALE_DAYS})"
               if age is not None else "unbekannt"),
            "", "## Kettennachweis", "",
            "| Vorbedingung | Status |", "|---|---|",
            f"| Agent-Reach-Brief ({day.isoformat()}) | {'✅ ' + chain['research_brief'] if chain['brief_vorhanden'] else '❌ fehlt'} |",
            f"| PUTER_AUTH_TOKEN | {'✅ gesetzt' if chain['token_vorhanden'] else '❌ fehlt/leer'} |",
            f"| Puter-Brücke `scripts/puter_chat.mjs` | {'✅ vorhanden' if chain['bruecke_vorhanden'] else '❌ fehlt'} |",
            f"| Ausfall-Serie | {failure_streak(season, load_json(STATE, {})) or 0} (Eskalation ab {FAILURE_STREAK_LIMIT}) |",
            "",
        ]
        report.extend(zeilen)
        report.extend([
            "", "---",
            "_Automatisch verändert werden ausschließlich `hero_title` und `hero_lead` "
            "in `data/saisons.yaml`. Templates, CSS, Links, CTAs und Fakten bleiben "
            "unberührt; jede Fassung muss SEO/GEO-Vertrag und Startseiten-Wache bestehen._",
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
            print(json.dumps({**base, "zustand": zustand, "exit": exit_code},
                             ensure_ascii=False, indent=2))
        return exit_code

    if not due:
        clear_failure(season, state)
        return finish(0, "grün – nichts zu tun", "kein Refresh nötig",
                      [f"Die freigegebene Fassung ist aktuell: {reason}."])

    # Stufe 1: Redaktionelle Änderung einholen, statt sie täglich als Defekt zu
    # behandeln. Wenn der live ausgelieferte Hero den vollen Vertrag und die
    # Wache besteht, ist er eine gültige Basis – der Nachweis holt nur auf.
    if code == "redaktion" and not args.force:
        ok, errors, gate_message = baseline_healthy(season)
        if ok:
            grund = ("redaktionell geänderter Saison-Hero automatisch als geprüfte Basis "
                     "übernommen (SEO/GEO-Vertrag und Startseiten-Wache bestanden)")
            record_baseline(season, state, grund, "approved-seasonal-baseline")
            clear_failure(season, load_json(STATE, {"version": 1, "saisons": {}}))
            print(f"✅ Redaktionsstand übernommen: {season['id']} – kein KI-Lauf nötig.")
            return finish(0, "grün – kuratierte Redaktion übernommen",
                          "Redaktionsstand als Basis bestätigt", [
                              "## Übernommene H1", str(season.get("hero_title")), "",
                              "## Übernommener GEO-Lead", str(season.get("hero_lead")), "",
                              "Es wurde **kein** Text generiert und nichts als KI-poliert "
                              "ausgegeben. Die nächste turnusmäßige Politur ist in "
                              f"{MAX_AGE_DAYS} Tagen fällig.",
                          ])
        print("🛑 Der redaktionell geänderte Saison-Hero verletzt den Vertrag: "
              + "; ".join(errors), file=sys.stderr)
        return finish(2, "rot – kuratierter Stand defekt",
                      "Redaktionsstand nicht freigabefähig",
                      ["## Befunde", ""] + [f"- {e}" for e in errors]
                      + ([""] + ["```", gate_message, "```"] if gate_message else []))

    # Stufe 2: Vorbedingungen der Kette. Fehlen sie, entsteht kein stiller
    # Fallback – aber auch kein täglicher Fehlalarm, solange der Live-Hero
    # geprüft, frisch und vertragsfest ist.
    hindernisse = []
    if not chain["brief_vorhanden"]:
        hindernisse.append("frischer Agent-Reach-Brief fehlt "
                           f"(erwartet: data/research/saisonal/{day.isoformat()}-internet-recherche.md)")
    if not chain["token_vorhanden"]:
        hindernisse.append("PUTER_AUTH_TOKEN fehlt oder ist leer – Claude Sonnet 5 "
                           "darf nicht still ersetzt werden")
    if not chain["bruecke_vorhanden"]:
        hindernisse.append("Puter-Brücke scripts/puter_chat.mjs fehlt")

    baseline_ok, baseline_errors, baseline_message = baseline_healthy(season)

    if hindernisse:
        streak = note_failure(season, state, "kette-unvollstaendig", "; ".join(hindernisse))
        hart, warum = escalate(code, age, streak, baseline_ok)
        zeilen = ["## Blockierte Vorbedingungen", ""] + [f"- {h}" for h in hindernisse]
        if not baseline_ok:
            zeilen += ["", "## Zusätzlich: Live-Hero defekt", ""] + [f"- {e}" for e in baseline_errors]
        if hart:
            print("🛑 Claude-Kette nicht lauffähig: " + "; ".join(hindernisse)
                  + f" · Eskalation, weil {warum}.", file=sys.stderr)
            return finish(3, f"rot – {warum}", "Kette nicht lauffähig",
                          zeilen + ["", f"**Eskalation:** {warum}."])
        print(f"::warning title=Saisonaler Hero::Claude-Kette pausiert "
              f"({'; '.join(hindernisse)}). Der geprüfte Saison-Hero bleibt live; "
              f"Eskalation ab {FAILURE_STREAK_LIMIT} Läufen in Folge oder "
              f"{HARD_STALE_DAYS} Tagen Alter.")
        return finish(0, "gelb – Kette pausiert, geprüfte Basis bleibt live",
                      "Kette pausiert (sichtbar, kein stiller Fallback)",
                      zeilen + ["", "Der live ausgelieferte Saison-Hero besteht SEO/GEO-Vertrag "
                                "und Startseiten-Wache. Es wurde nichts überschrieben und nichts "
                                "als KI-poliert ausgegeben.",
                                f"Serie: {streak} von {FAILURE_STREAK_LIMIT} bis zur Eskalation."])

    # Stufe 3: Claude mit Wiederholung und Korrekturauflage.
    brief = newest_research_brief(day)
    topics = research_topics(brief, season)
    history = read_history()
    parsed, protokoll = claude_candidate(season, topics, history)
    if not parsed:
        streak = note_failure(season, state, "claude-ohne-gueltige-fassung", " | ".join(protokoll))
        hart, warum = escalate(code, age, streak, baseline_ok)
        zeilen = ["## Versuchsprotokoll", ""] + [f"- {p}" for p in protokoll]
        if hart:
            print("🛑 Claude lieferte keine vertragsfeste Fassung: " + " | ".join(protokoll)
                  + f" · Eskalation, weil {warum}.", file=sys.stderr)
            return finish(4, f"rot – {warum}", "Keine vertragsfeste Claude-Fassung",
                          zeilen + ["", f"**Eskalation:** {warum}."])
        print("::warning title=Saisonaler Hero::Claude lieferte keine vertragsfeste Fassung "
              f"({len(protokoll)} Versuche). Der geprüfte Saison-Hero bleibt unverändert live.")
        return finish(0, "gelb – Kandidaten verworfen, geprüfte Basis bleibt live",
                      "Kandidaten verworfen (Faktenbremse hat gegriffen)",
                      zeilen + ["", f"Serie: {streak} von {FAILURE_STREAK_LIMIT} bis zur Eskalation."])

    title, lead = parsed
    original = SAISONS.read_text(encoding="utf-8")
    try:
        rewrite_fields(str(season["id"]), title, lead)
        healthy, gate_message = guard_source()
        if not healthy:
            SAISONS.write_text(original, encoding="utf-8")
            note_failure(season, state, "wache-verwirft-kandidat", gate_message)
            print("🛑 Saison-Wache verwirft den Kandidaten; Quelle zurückgesetzt.\n" + gate_message,
                  file=sys.stderr)
            return finish(2, "rot – Wache verwirft Kandidat", "Kandidat von der Wache verworfen",
                          ["## Wache", "", "```", gate_message, "```"])
    except Exception as exc:  # noqa: BLE001 - atomic rollback is the contract
        SAISONS.write_text(original, encoding="utf-8")
        note_failure(season, state, "schreibfehler", str(exc))
        print(f"🛑 Saisonaler Hero konnte nicht sicher geschrieben werden: {exc}", file=sys.stderr)
        return finish(2, "rot – Schreibpfad unsicher", "Schreibvorgang abgebrochen",
                      [f"Fehler: `{exc}` – `data/saisons.yaml` wurde unverändert zurückgesetzt."])

    _, changed_seasons = load_seasons()
    changed = next(s for s in changed_seasons if s.get("id") == season.get("id"))
    brief_hash = hashlib.sha256(brief.read_bytes()).hexdigest()
    record = {
        "updated": iso_now(), "fingerprint": fingerprint(changed), "model": MODEL,
        "research_brief": str(brief.relative_to(ROOT)), "research_sha256": brief_hash,
    }
    state.setdefault("version", 1)
    state.setdefault("saisons", {})[str(season["id"])] = record
    save_json(STATE, state)
    append_history({
        "ts": record["updated"], "season": season["id"], "hero_title": title,
        "hero_lead": lead, "model": MODEL, "research_brief": record["research_brief"],
        "research_sha256": brief_hash, "topics": topics,
    })
    print(f"✅ Saisonaler Hero poliert: {season['id']} · Agent Reach + {MODEL}.")
    return finish(0, "grün – Agent Reach + Claude", "Agent Reach + Claude", [
        f"**Agent-Reach-Brief:** `{record['research_brief']}` (SHA-256 `{brief_hash[:12]}…`)",
        f"**Claude-Modell:** `{MODEL}` über Puter.js, ohne Anthropic-API",
        f"**Themen aus Signalen:** {', '.join(topics) or '–'}", "",
        "## Neue H1", title, "", "## Neuer GEO-Lead", lead, "",
        "## Versuchsprotokoll", "",
    ] + [f"- {p}" for p in protokoll])


if __name__ == "__main__":
    raise SystemExit(main())
