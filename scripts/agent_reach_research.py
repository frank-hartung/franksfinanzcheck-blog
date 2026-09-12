#!/usr/bin/env python3
"""Agent-Reach-Recherche: kuratierte Internet-Signale für die Redaktion.

Premium-Integration von Agent Reach (github.com/Panniantong/Agent-Reach)
in den Redaktionsbetrieb von franksfinanzcheck.de (12.09.2026).

Was dieses Skript tut
---------------------
Es liest den KURATIERTEN Themenplan (data/agent_reach/themenplan.yaml)
und sammelt darüber ausschließlich LESEND Signale aus dem Internet –
über die von Agent Reach gerouteten Kanäle:

  RSS       → feedparser            (Agent-Reach-Kanal „rss")
  YouTube   → yt-dlp ytsearch       (Agent-Reach-Kanal „youtube")
  GitHub    → gh search repos       (Agent-Reach-Kanal „github")
  Webseiten → Jina Reader r.jina.ai (Agent-Reach-Kanal „web")

Ergebnis ist ein deutschsprachiges Recherche-Brief unter
data/research/ (Markdown + JSON-Beilage) mit Quellenangabe je Treffer.

Leitplanken (entsprechen dem KI-Redaktions-Statut, siehe KI-REDAKTION.md)
--------------------------------------------------------------------------
* NUR LESEN: Das Skript postet, kommentiert und schreibt nirgends.
* KEINE Faktenübernahme: Der Brief ist ein Signal-Pool für Menschen/
  Agenten. Fakten dürfen erst nach Prüfung in kuratierte Dateien wie
  data/aktuelle_entwicklungen.yaml übernommen werden.
* KEINE Secrets: Alle hier genutzten Kanäle sind Zero-Config
  (ohne API-Keys/Logins). Login-pflichtige Agent-Reach-Kanäle
  (Twitter, Reddit, XiaoHongShu …) gehören ausschließlich auf den
  lokalen Rechner – niemals in CI (siehe ANLEITUNG-AGENT-REACH.md).

Aufruf
------
  python3 scripts/agent_reach_research.py                 # Standardlauf
  python3 scripts/agent_reach_research.py --dry-run       # nur anzeigen
  python3 scripts/agent_reach_research.py --selftest      # Offline-Test

Exit-Codes: 0 = mindestens eine Quelle lieferte, 2 = Plan/Skript-Fehler,
3 = keine einzige Quelle erreichbar (CI soll dann warnen, nicht hart
abbrechen – die Kanalmatrix kann sich ändern).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN = ROOT / "data" / "agent_reach" / "themenplan.yaml"
DEFAULT_OUT = ROOT / "data" / "research"

USER_AGENT = "franksfinanzcheck-recherche/1.0 (Agent-Reach-Integration)"
TIMEOUT_STD = 30          # Sekunden je Einzelabruf
TIMEOUT_DOCTOR = 90       # Sekunden für agent-reach doctor

# ----------------------------------------------------------------------
# Kleinkram
# ----------------------------------------------------------------------

def slugify(text: str, maxlen: int = 60) -> str:
    """Deterministischer, ASCII-sicherer Slug für Dateinamen."""
    text = text.strip().lower()
    text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:maxlen].strip("-") or "recherche"


def heute() -> str:
    return dt.date.today().isoformat()


def jetzt_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def finde_agent_reach_bin(explicit: str | None) -> str | None:
    """Löst das agent-reach-Binary auf (explizit > $PATH > .venv)."""
    if explicit:
        return explicit if Path(explicit).exists() else None
    found = shutil.which("agent-reach")
    if found:
        return found
    venv_bin = ROOT / ".venv" / "bin" / "agent-reach"
    return str(venv_bin) if venv_bin.exists() else None


def lade_plan(pfad: Path) -> dict:
    try:
        import yaml  # PyYAML – im Repo ohnehin Standard
    except ImportError:
        raise SystemExit("PyYAML fehlt: pip install pyyaml")
    if not pfad.exists():
        raise SystemExit(f"Themenplan nicht gefunden: {pfad}")
    daten = yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}
    if not isinstance(daten, dict):
        raise SystemExit(f"Themenplan ungültig (kein Mapping): {pfad}")
    return daten


# ----------------------------------------------------------------------
# Agent-Reach-Diagnose (doctor) – ehrliche Kanalmatrix in jeden Brief
# ----------------------------------------------------------------------

def doctor(binpfad: str | None) -> dict:
    """Führt `agent-reach doctor --json` aus; {} wenn nicht verfügbar."""
    if not binpfad:
        return {}
    try:
        proc = subprocess.run(
            [binpfad, "doctor", "--json"],
            capture_output=True, text=True, timeout=TIMEOUT_DOCTOR,
        )
        return json.loads(proc.stdout) if proc.returncode == 0 else {}
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return {}


def kanal_status(doctordaten: dict, kanal: str) -> str:
    info = doctordaten.get(kanal) or {}
    status = info.get("status", "unbekannt")
    backend = info.get("active_backend")
    return f"{status}" + (f" ({backend})" if backend else "")


# ----------------------------------------------------------------------
# Sammler (einer je Kanal) – liefern (trefferliste, fehlermeldung)
# ----------------------------------------------------------------------

def sammle_rss(eintrag: dict, limit: int, timeout: int) -> tuple[list[dict], str | None]:
    name, url = eintrag.get("name", "Feed"), eintrag.get("url", "")
    try:
        import feedparser
    except ImportError:
        return [], "feedparser nicht installiert (pip install feedparser)"
    try:
        feed = feedparser.parse(url, agent=USER_AGENT)
    except Exception as exc:  # noqa: BLE001 – Netzwerkfehler sauber melden
        return [], f"Abruf fehlgeschlagen: {exc}"
    if getattr(feed, "bozo", 0) and not feed.entries:
        return [], "Feed nicht lesbar (bozo, keine Einträge)"
    treffer = []
    for e in feed.entries[:limit]:
        datum = ""
        for feld in ("published", "updated"):
            if e.get(feld):
                datum = str(e[feld])[:16]
                break
        treffer.append({
            "titel": (e.get("title") or "(ohne Titel)").strip(),
            "url": e.get("link", ""),
            "datum": datum,
            "quelle": name,
        })
    return treffer, None


def sammle_youtube(query: str, limit: int, timeout: int) -> tuple[list[dict], str | None]:
    if not shutil.which("yt-dlp"):
        return [], "yt-dlp nicht installiert (pip install yt-dlp)"
    cmd = ["yt-dlp", "--flat-playlist", "--dump-json", f"ytsearch{limit}:{query}"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return [], "Timeout bei der YouTube-Suche"
    if proc.returncode != 0 and not proc.stdout.strip():
        meldung = (proc.stderr or "").strip().splitlines()
        return [], f"yt-dlp-Fehler: {meldung[0][:120] if meldung else 'unbekannt'}"
    treffer = []
    for zeile in proc.stdout.splitlines():
        try:
            d = json.loads(zeile)
        except json.JSONDecodeError:
            continue
        vid = d.get("id") or ""
        treffer.append({
            "titel": d.get("title", "(ohne Titel)"),
            "url": d.get("url") or (f"https://www.youtube.com/watch?v={vid}" if vid else ""),
            "kanal": d.get("channel") or d.get("uploader") or "",
            "quelle": "YouTube",
        })
    return treffer, None


def sammle_github(query: str, limit: int, timeout: int) -> tuple[list[dict], str | None]:
    if not shutil.which("gh"):
        return [], "gh CLI nicht installiert/erreichbar"
    cmd = ["gh", "search", "repos", query, "--limit", str(limit),
           "--json", "fullName,description,stargazersCount,url"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return [], "Timeout bei der GitHub-Suche"
    if proc.returncode != 0:
        meldung = (proc.stderr or "").strip().splitlines()
        return [], f"gh-Fehler: {meldung[0][:120] if meldung else 'unbekannt'}"
    try:
        roh = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return [], "gh-Antwort nicht lesbar"
    treffer = [{
        "titel": r.get("fullName", ""),
        "url": r.get("url", ""),
        "beschreibung": (r.get("description") or "")[:160],
        "sterne": r.get("stargazersCount", 0),
        "quelle": "GitHub",
    } for r in roh]
    return treffer, None


def sammle_web(url: str, max_zeichen: int, timeout: int) -> tuple[dict | None, str | None]:
    ziel = f"https://r.jina.ai/{url}"
    req = urllib.request.Request(ziel, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as antw:
            text = antw.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001 – Netzwerkfehler sauber melden
        return None, f"Jina-Reader-Abruf fehlgeschlagen: {exc}"
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return {"url": url, "auszug": text[:max_zeichen], "quelle": "Web (Jina Reader)"}, None


# ----------------------------------------------------------------------
# Brief-Erzeugung
# ----------------------------------------------------------------------

def erzeuge_brief(plan: dict, doctordaten: dict, ergebnisse: dict,
                  ar_version: str) -> tuple[str, dict]:
    datum = heute()
    e = plan.get("einstellungen") or {}
    zeilen: list[str] = [
        f"# Internet-Recherche {datum}",
        "",
        f"> Automatisch erzeugt von `scripts/agent_reach_research.py` um {jetzt_utc()}.",
        f"> {ar_version or 'Agent Reach nicht installiert'} – Kanalmatrix laut `agent-reach doctor`.",
        "> **Status: Signalsammlung.** Kein Treffer ist redaktionell geprüft oder",
        "> veröffentlicht; Faktenübernahme nur über menschliche Kuratierung",
        "> (siehe KI-Redaktions-Statut in `KI-REDAKTION.md`).",
        "",
        "## Kanalmatrix (agent-reach doctor)",
        "",
        "| Kanal | Status |",
        "|---|---|",
    ]
    for kanal in ("rss", "youtube", "github", "web", "v2ex", "twitter", "reddit"):
        zeilen.append(f"| {kanal} | {kanal_status(doctordaten, kanal)} |")
    if not doctordaten:
        zeilen.append("| _alle_ | _doctor nicht ausführbar (agent-reach fehlt?)_ |")

    ok, fehler = 0, 0

    zeilen += ["", "## RSS-Signale", ""]
    for name, daten in ergebnisse.get("rss", {}).items():
        treffer, err = daten
        if err:
            fehler += 1
            zeilen += [f"### {name}", f"- Fehler: {err}", ""]
            continue
        ok += 1
        zeilen.append(f"### {name}")
        if not treffer:
            zeilen.append("- (keine Einträge)")
        for t in treffer:
            d = f" ({t['datum']})" if t.get("datum") else ""
            zeilen.append(f"- [{t['titel']}]({t['url']}){d}")
        zeilen.append("")

    zeilen += ["## YouTube-Signale", ""]
    for query, daten in ergebnisse.get("youtube", {}).items():
        treffer, err = daten
        zeilen.append(f"### Suche: „{query}“")
        if err:
            fehler += 1
            zeilen += [f"- Fehler: {err}", ""]
            continue
        ok += 1
        if not treffer:
            zeilen.append("- (keine Treffer)")
        for t in treffer:
            kanal = f" – {t['kanal']}" if t.get("kanal") else ""
            zeilen.append(f"- [{t['titel']}]({t['url']}){kanal}")
        zeilen.append("")

    zeilen += ["## GitHub-Signale", ""]
    for query, daten in ergebnisse.get("github", {}).items():
        treffer, err = daten
        zeilen.append(f"### Suche: „{query}“")
        if err:
            fehler += 1
            zeilen += [f"- Fehler: {err}", ""]
            continue
        ok += 1
        if not treffer:
            zeilen.append("- (keine Treffer)")
        for t in treffer:
            zeilen.append(
                f"- [{t['titel']}]({t['url']}) – {t['sterne']} Sterne"
                + (f": {t['beschreibung']}" if t.get("beschreibung") else ""))
        zeilen.append("")

    zeilen += ["## Web-Auszüge (Jina Reader)", ""]
    for url, daten in ergebnisse.get("web", {}).items():
        inhalt, err = daten
        zeilen.append(f"### {url}")
        if err:
            fehler += 1
            zeilen += [f"- Fehler: {err}", ""]
            continue
        ok += 1
        zeilen += ["", "```", inhalt["auszug"] or "(leer)", "```", ""]

    zeilen += [
        "---",
        f"**Bilanz:** {ok} Quelle(n) lieferten Ergebnisse, {fehler} Fehler.",
        "",
        "_Alle Angaben ohne Gewähr. Quellen sind verlinkt und vor jeder",
        "redaktionellen Übernahme zu prüfen. Agent Reach wird hier rein",
        "lesend betrieben (keine Schreiboperationen auf Plattformen)._",
        "",
    ]
    brief = "\n".join(zeilen)
    beilage = {
        "datum": datum,
        "erzeugt_utc": jetzt_utc(),
        "agent_reach": ar_version,
        "kanal_ok": ok,
        "kanal_fehler": fehler,
        "ergebnisse": {
            k: {q: {"treffer": t, "fehler": err} for q, (t, err) in v.items()}
            for k, v in ergebnisse.items() if k != "web"
        },
    }
    return brief, beilage


# ----------------------------------------------------------------------
# Hauptlauf
# ----------------------------------------------------------------------

def lauf(plan: dict, binpfad: str | None, timeout: int) -> tuple[dict, dict, str]:
    e = plan.get("einstellungen") or {}
    rss_limit = int(e.get("rss_max_je_feed", 5))
    yt_limit = int(e.get("youtube_max", 5))
    gh_limit = int(e.get("github_max", 5))
    web_limit = int(e.get("web_max_zeichen", 1200))

    doctordaten = doctor(binpfad)

    version = ""
    if binpfad:
        try:
            proc = subprocess.run([binpfad, "--version"], capture_output=True,
                                  text=True, timeout=30)
            version = (proc.stdout or proc.stderr).strip().splitlines()[0]
        except (subprocess.TimeoutExpired, OSError, IndexError):
            version = ""

    ergebnisse: dict = {"rss": {}, "youtube": {}, "github": {}, "web": {}}

    for eintrag in plan.get("rss") or []:
        name = eintrag.get("name") or eintrag.get("url", "Feed")
        ergebnisse["rss"][name] = sammle_rss(eintrag, rss_limit, timeout)

    for eintrag in plan.get("youtube") or []:
        query = eintrag.get("query", "")
        if query:
            ergebnisse["youtube"][query] = sammle_youtube(query, yt_limit, timeout)

    for eintrag in plan.get("github") or []:
        query = eintrag.get("query", "")
        if query:
            ergebnisse["github"][query] = sammle_github(query, gh_limit, timeout)

    for eintrag in (plan.get("web") or [])[:3]:
        url = eintrag.get("url", "")
        if url:
            inhalt, err = sammle_web(url, web_limit, timeout)
            ergebnisse["web"][url] = (inhalt, err)

    return ergebnisse, doctordaten, version


def main() -> int:
    ap = argparse.ArgumentParser(description="Agent-Reach-Recherche für franksfinanzcheck.de")
    ap.add_argument("--plan", default=str(DEFAULT_PLAN), help="Pfad zum Themenplan (YAML)")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT), help="Ausgabeverzeichnis der Briefs")
    ap.add_argument("--bin", default=None, help="Pfad zum agent-reach-Binary (optional)")
    ap.add_argument("--timeout", type=int, default=TIMEOUT_STD, help="Timeout je Abruf (s)")
    ap.add_argument("--dry-run", action="store_true", help="Plan zeigen, nichts abrufen")
    ap.add_argument("--selftest", action="store_true", help="Offline-Selbsttest der Helfer")
    args = ap.parse_args()

    if args.selftest:
        assert slugify("Strompreis & Gas – 2026!") == "strompreis-gas-2026"
        assert slugify("Ärger mit Öltanks") == "aerger-mit-oeltanks"
        assert heute().count("-") == 2
        brief, beilage = erzeuge_brief(
            {"einstellungen": {}}, {},
            {"rss": {"Test-Feed": ([{"titel": "x", "url": "u", "datum": "", "quelle": "q"}], None)},
             "youtube": {}, "github": {}, "web": {}}, "v-selftest")
        assert "# Internet-Recherche" in brief and beilage["kanal_ok"] == 1
        print("selftest: OK")
        return 0

    plan = lade_plan(Path(args.plan))

    if args.dry_run:
        print(f"Themenplan: {args.plan}")
        for k in ("rss", "youtube", "github", "web"):
            n = len(plan.get(k) or [])
            print(f"  {k:8} {n} Eintrag/Einträge")
        return 0

    binpfad = finde_agent_reach_bin(args.bin)
    if not binpfad:
        print("Hinweis: agent-reach-Binary nicht gefunden – "
              "Kanalmatrix entfällt (pip install -r requirements-agent-reach.txt).",
              file=sys.stderr)

    ergebnisse, doctordaten, version = lauf(plan, binpfad, args.timeout)
    brief, beilage = erzeuge_brief(plan, doctordaten, ergebnisse, version)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ziel = out_dir / f"{heute()}-internet-recherche.md"
    ziel.write_text(brief, encoding="utf-8")
    (out_dir / f"{heute()}-internet-recherche.json").write_text(
        json.dumps(beilage, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Brief geschrieben: {ziel}")
    print(f"Quellen ok: {beilage['kanal_ok']}, Fehler: {beilage['kanal_fehler']}")
    return 0 if beilage["kanal_ok"] > 0 else 3


if __name__ == "__main__":
    sys.exit(main())
