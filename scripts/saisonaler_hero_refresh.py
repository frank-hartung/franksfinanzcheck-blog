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
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return (proc.stdout or "").strip() or None


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


def is_due(season: dict, state: dict, force: bool, now: dt.datetime) -> tuple[bool, str]:
    if force:
        return True, "manuell erzwungen"
    saved = (state.get("saisons") or {}).get(str(season.get("id")))
    if not isinstance(saved, dict):
        return True, "neue Saison noch nicht mit Agent Reach + Claude poliert"
    if saved.get("fingerprint") != fingerprint(season):
        return True, "Saisondaten wurden seit der letzten Politur verändert"
    try:
        last = dt.datetime.fromisoformat(str(saved.get("updated", "")).replace("Z", "+00:00"))
        if (now - last).days >= MAX_AGE_DAYS:
            return True, f"letzte Politur ist {(now - last).days} Tage alt"
    except ValueError:
        return True, "Zeitstempel der letzten Politur fehlt/ist ungültig"
    return False, "aktuell"


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
    if not ok:
        print("❌ Saisonaler-Hero-Selbsttest fehlgeschlagen")
        return 2
    print("✅ Saisonaler-Hero-Selbsttest: Saisonlogik, GEO-Vertrag und Faktenbremse grün.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Saisonaler SEO-/GEO-Hero mit Agent Reach + Claude")
    parser.add_argument("--fix", action="store_true", help="bei Fälligkeit Claude-Politur schreiben")
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
        errors = validate_candidate(title, lead, season, [])
        if errors:
            print("🛑 Aktueller Saison-Hero verletzt den SEO/GEO-Vertrag: "
                  + "; ".join(errors), file=sys.stderr)
            return 2
        healthy, gate_message = guard_source()
        if not healthy:
            print("🛑 Saison-Wache verwirft den aktuellen Basisstand.\n" + gate_message,
                  file=sys.stderr)
            return 2
        grund = (args.reason or "aktueller Saison-Hero als freigegebene Basis bestätigt").strip()
        record = {
            "updated": iso_now(), "fingerprint": fingerprint(season),
            "model": "approved-seasonal-baseline",
            "research_brief": "", "research_sha256": "",
            "set_current": True, "reason": grund,
        }
        state.setdefault("version", 1)
        state.setdefault("saisons", {})[str(season["id"])] = record
        save_json(STATE, state)
        append_history({
            "ts": record["updated"], "season": season["id"],
            "hero_title": title, "hero_lead": lead,
            "model": record["model"], "research_brief": "",
            "research_sha256": "", "topics": [],
            "set_current": True, "reason": grund,
        })
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

    due, reason = is_due(season, state, args.force, now)
    base = {"season": season.get("id"), "date": day.isoformat(), "due": due, "reason": reason}

    if args.check or not args.fix:
        if args.json:
            print(json.dumps(base, ensure_ascii=False, indent=2))
        else:
            print(f"Saisonaler Hero: {season.get('id')} · {'FÄLLIG' if due else 'aktuell'} – {reason}")
        return 1 if due else 0

    if not due:
        write_report([
            "# Saisonaler Hero – kein Refresh nötig", "",
            f"**Saison:** `{season.get('id')}` · **Stand:** {iso_now()}",
            f"**Grund:** {reason}",
        ])
        print(f"✅ Saisonaler Hero aktuell ({season.get('id')}: {reason}).")
        return 0

    brief = newest_research_brief(day)
    if not brief:
        print("🛑 Frischer Agent-Reach-Brief fehlt – kein Claude-Text ohne Recherche-Vorleistung.", file=sys.stderr)
        return 3
    if not (os.environ.get("PUTER_AUTH_TOKEN") or "").strip():
        print("🛑 PUTER_AUTH_TOKEN fehlt – Claude Sonnet 5 darf nicht still durch einen Fallback ersetzt werden.", file=sys.stderr)
        return 3
    if not BRUECKE.is_file():
        print("🛑 Puter-Brücke fehlt: scripts/puter_chat.mjs", file=sys.stderr)
        return 2

    topics = research_topics(brief, season)
    system, user = prompt_for(season, topics)
    answer = call_claude(system, user)
    parsed = parse_answer(answer or "")
    history = read_history()
    if not parsed:
        print("🛑 Claude lieferte kein gültiges TITLE/LEAD-Format; nichts geschrieben.", file=sys.stderr)
        return 3
    title, lead = parsed
    errors = validate_candidate(title, lead, season, history)
    if errors:
        print("🛑 Claude-Kandidat verworfen: " + "; ".join(errors), file=sys.stderr)
        return 3

    original = SAISONS.read_text(encoding="utf-8")
    try:
        rewrite_fields(str(season["id"]), title, lead)
        healthy, gate_message = guard_source()
        if not healthy:
            SAISONS.write_text(original, encoding="utf-8")
            print("🛑 Saison-Wache verwirft den Kandidaten; Quelle zurückgesetzt.\n" + gate_message,
                  file=sys.stderr)
            return 2
    except Exception as exc:  # noqa: BLE001 - atomic rollback is the contract
        SAISONS.write_text(original, encoding="utf-8")
        print(f"🛑 Saisonaler Hero konnte nicht sicher geschrieben werden: {exc}", file=sys.stderr)
        return 2

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
    write_report([
        "# Saisonaler Hero – Agent Reach + Claude", "",
        f"**Saison:** `{season['id']}` · **Stand:** {record['updated']}",
        f"**Agent-Reach-Brief:** `{record['research_brief']}` (SHA-256 `{brief_hash[:12]}…`)",
        f"**Claude-Modell:** `{MODEL}` über Puter.js, ohne Anthropic-API", "",
        "## Neue H1", title, "", "## Neuer GEO-Lead", lead, "",
        "---",
        "_Automatisch geändert wurden nur `hero_title` und `hero_lead`. Die"
        " saisonale Startseiten-Wache hat Quelle, Stimme und Kontrakt danach geprüft._",
    ])
    print(f"✅ Saisonaler Hero poliert: {season['id']} · Agent Reach + {MODEL}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
