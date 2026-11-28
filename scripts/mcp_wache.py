#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
#  MCP-WACHE – ein Werkzeug für Agenten, kein Einfallstor
#  ------------------------------------------------------------
#  WARUM ES DIESE WACHE GIBT (26.10.2026)
#
#  Ein aktives MCP-Profil gibt einem Agenten Werkzeuge. Seit 26.11.2026
#  bleibt der Projektstandard `.mcp.json` leer; ausschließlich der
#  Diagnose-Agent besitzt das Startprofil. Dieses ist dreierlei:
#
#    · eine ABHÄNGIGKEIT (ein npm-Paket, das ohne Pin ein anderes
#      Programm ist als gestern),
#    · eine NETZBEFUGNIS (ein Browser, der jede URL laden darf),
#    · ein DATEIZUGRIFF (Werkzeuge lesen und schreiben Dateien).
#
#  Genau die Klasse, für die dieses Repo Regeln hat: Versionen exakt
#  gepinnt (Regel A1), keine Geheimnisse in Dateien (Regel 2), fremder
#  Text ist Daten und keine Anweisung (Regel 1). Eine Konfiguration,
#  die niemand prüft, ist eine Hintertür mit guter Absicht.
#
#  WAS GEPRÜFT WIRD (M1–M7)
#    M1 DATEI      Das aktive Profil enthält einen nichtleeren
#                  `mcpServers`-Block.
#    M2 GEHEIMNIS  Kein Wert sieht wie ein Token/Schlüssel aus. Kein
#                  Klartext-Bearer. Umgebungsvariablen-Verweise
#                  (`${VAR}`) sind erlaubt – sie sind keine Werte.
#    M3 PIN        Jeder Server nennt eine EXAKTE Version
#                  (`paket@1.2.3`). `@latest`, `^`, `~`, `*`, `>`
#                  sind verboten: Ein Range ist eine Hoffnung.
#    M4 ERLAUBT    Nur Server aus der Allowlist (heute: playwright).
#                  Ein neuer Server ist eine Entscheidung, kein
#                  Nebeneffekt eines Rebase.
#    M5 HÄRTUNG    Der Browser-Server muss isoliert laufen
#                  (`--isolated`), Service-Worker blocken, headless
#                  sein, den Dateizugriff NICHT freischalten und die
#                  Ziele über `--allowed-origins` begrenzen – ohne
#                  `*`.
#    M6 PLATZHALTER  Keine `CHANGE_ME`/`YOUR_`/`<…>`-Werte.
#
#    M7 BEDARF     Projektstandard ohne Server. Nur der Diagnose-Agent
#                  erhält die fünf benannten Werkzeuge; keine automatischen
#                  Seitenbäume, Codebeispiele oder Werkzeuge aus der Seite.
#
#  WAS DIESE WACHE NICHT LEISTET
#  Sie ersetzt keine Sandbox. `--allowed-origins` ist laut Upstream
#  ausdrücklich KEINE Sicherheitsgrenze (Redirects bleiben möglich).
#  Sie hält den Zustand fest, den ein Mensch entschieden hat – und
#  macht jede stille Änderung daran sichtbar.
#
#  AUFRUF
#    python3 scripts/mcp_wache.py            # Arbeitsbaum prüfen
#    python3 scripts/mcp_wache.py --json     # Maschinenausgabe
#    python3 scripts/mcp_wache.py --selftest # Sabotageproben, ohne Netz
#
#  Exit: 0 = sauber · 1 = Befund · 2 = Werkzeugfehler (Selbsttest rot)
# ============================================================

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KONFIG = ROOT / ".mcp.json"
EINSTELLUNGEN = ROOT / ".claude" / "settings.json"
PROFIL = ROOT / ".claude" / "agents" / "ff-browserdiagnose.md"
DIAGNOSE_TOOLS = tuple("mcp__playwright__browser_" + name for name in (
    "navigate", "find", "snapshot", "console_messages", "network_requests",
))

# Einziger ausführbarer Hook im Profil. Keine globale Freigabe, kein Shell-Input
# aus der Seite. Auch ein fehlender Interpreter muss den Toolaufruf blockieren.
DIAGNOSE_HOOKS = {"PreToolUse": [{
    "matcher": "mcp__playwright__.*",
    "hooks": [{"type": "command", "command": 'python3 "$CLAUDE_PROJECT_DIR/scripts/mcp_wache.py" --vor-aufruf || exit 2'}],
}]}

# Server, die in diesem Repo laufen dürfen. Ein Eintrag hier ist eine
# Entscheidung des Inhabers, keine Bequemlichkeit: Wer einen Server
# ergänzt, ergänzt Netz- und Dateibefugnisse.
ERLAUBTE_SERVER = ("playwright",)

# Herkunftsziele, die der Browser erreichen darf: die Produktionsdomain
# (Leseprüfung der echten Seite) und der lokale E2E-Server (Prüfung des
# Builds vor dem Deploy).
ERLAUBTE_ORIGINS = (
    "https://franksfinanzcheck.de",
    "http://127.0.0.1:4173",
)

# Pflichtschalter des Browser-Servers – jeder verhindert eine belegte
# Fehlerklasse: Profilreste mit Anmeldedaten, nicht-deterministische
# Cache-Antworten, ein Browser, der CI-Läufe blockiert.
PFLICHT_ARGUMENTE = ("--isolated", "--block-service-workers", "--headless",
                     "--output-dir")

# Verbote: Freigaben, die mehr dürfen als nötig.
VERBOTENE_ARGUMENTE = ("--allow-unrestricted-file-access", "--extension")

# Ablage der Belege (Bildschirmfotos, Snapshots): MUSS im ignorierten
# Arbeitsordner liegen. Ein Werkzeug, das Dateien ins Repo-Root schreibt,
# erzeugt bei jedem Lauf einen ungewollten Commit-Kandidaten.
ABLAGE_PRAEFIX = ".cache/"

RE_EXAKTE_VERSION = re.compile(r"@\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
RE_RANGE = re.compile(r"(?:\^|~|\*|>=|<=|>|<|\blatest\b)")
RE_GEHEIMNIS = re.compile(
    r"(?i)(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{16,}"
    r"|AIza[0-9A-Za-z_-]{30,}|xox[baprs]-[A-Za-z0-9-]{10,}"
    r"|bearer\s+[A-Za-z0-9._-]{12,}|[A-Fa-f0-9]{40,})"
)
RE_PLATZHALTER = re.compile(r"(?i)(change[_-]?me|your[_-]|example\.com|<\s*[a-z_]+\s*>)")
RE_UMGEBUNG = re.compile(r"^\$\{[A-Za-z_][A-Za-z0-9_]*\}$")


def _werte(server: dict) -> list[str]:
    """Alle Textwerte einer Server-Definition (args, env, url, headers …)."""
    werte: list[str] = []
    for schluessel, wert in (server or {}).items():
        if isinstance(wert, str):
            werte.append(wert)
        elif isinstance(wert, list):
            werte.extend(str(w) for w in wert if isinstance(w, str))
        elif isinstance(wert, dict):
            for k, v in wert.items():
                werte.append(str(k))
                if isinstance(v, str):
                    werte.append(v)
    return werte


def pruefe(config: dict) -> list[str]:
    """Prüft eine MCP-Konfiguration und liefert alle Befunde (rein, ohne IO)."""
    fehler: list[str] = []
    if not isinstance(config, dict):
        return ["M1: Die Konfiguration ist kein JSON-Objekt."]
    server = config.get("mcpServers")
    if not isinstance(server, dict) or not server:
        return ["M1: `mcpServers` fehlt oder ist leer – ohne Server tut die Datei nichts."]

    for name, definition in server.items():
        if name not in ERLAUBTE_SERVER:
            fehler.append(
                f"M4: Server „{name}“ steht nicht in der Allowlist "
                f"({', '.join(ERLAUBTE_SERVER)}) – ein neuer Server ist eine Entscheidung."
            )
        if not isinstance(definition, dict):
            fehler.append(f"M1: Server „{name}“ ist kein Objekt.")
            continue

        if "args" in definition and not isinstance(definition["args"], list):
            fehler.append(f"M1: Argumente von „{name}“ sind keine Liste.")
            continue
        pakete = [str(a) for a in (definition.get("args") or []) if str(a).startswith("@")]
        if definition.get("command") in ("npx", "npm", "bunx", "pnpx"):
            if not pakete:
                fehler.append(f"M3: Server „{name}“ startet über {definition.get('command')} ohne Paketangabe.")
            for paket in pakete:
                if RE_RANGE.search(paket.split("@")[1] if paket.count("@") > 1 else paket):
                    fehler.append(f"M3: „{paket}“ enthält einen Versions-Range – exakt pinnen.")
                elif not RE_EXAKTE_VERSION.search(paket):
                    fehler.append(
                        f"M3: „{paket}“ hat keine exakte Version (erwartet paket@1.2.3) – "
                        "ein Range ist eine Hoffnung, ein Pin eine Aussage."
                    )

        for wert in _werte(definition):
            if RE_GEHEIMNIS.search(wert):
                fehler.append(f"M2: Server „{name}“ enthält einen Wert, der wie ein Geheimnis aussieht.")
            if RE_PLATZHALTER.search(wert):
                fehler.append(f"M6: Server „{name}“ enthält einen Platzhalter: {wert!r}")

        if name == "playwright":
            argumente = [str(a) for a in (definition.get("args") or [])]
            for pflicht in PFLICHT_ARGUMENTE:
                if pflicht not in argumente:
                    fehler.append(f"M5: „{name}“ startet ohne {pflicht}.")
            for verboten in VERBOTENE_ARGUMENTE:
                if verboten in argumente:
                    fehler.append(f"M5: „{name}“ nutzt {verboten} – mehr Befugnis als nötig.")
            if "--output-dir" in argumente:
                stelle = argumente.index("--output-dir")
                ziel = argumente[stelle + 1] if stelle + 1 < len(argumente) else ""
                if not ziel.startswith(ABLAGE_PRAEFIX):
                    fehler.append(
                        f"M5: „{name}“ legt Belege in {ziel or '—'} ab – sie gehören unter "
                        f"{ABLAGE_PRAEFIX} (ignoriert), sonst wächst das Repo mit Screenshots.")
            if "--allowed-origins" not in argumente:
                fehler.append(f"M5: „{name}“ begrenzt die Ziele nicht (--allowed-origins fehlt).")
            else:
                stelle = argumente.index("--allowed-origins")
                if stelle + 1 >= len(argumente):
                    fehler.append(f"M5: „{name}“: --allowed-origins ohne Wert.")
                else:
                    for origin in argumente[stelle + 1].split(";"):
                        origin = origin.strip()
                        if not origin:
                            continue
                        if origin == "*":
                            fehler.append(f"M5: „{name}“ erlaubt jedes Ziel (*) – das ist keine Grenze.")
                        elif origin.rstrip("/") not in [o.rstrip("/") for o in ERLAUBTE_ORIGINS]:
                            fehler.append(
                                f"M5: „{name}“ erlaubt ein fremdes Ziel: {origin} "
                                f"(erlaubt: {', '.join(ERLAUBTE_ORIGINS)})."
                            )
    return fehler


def _eindeutig(paare: list[tuple]) -> dict:
    # YAML- und JSON-Clients behandeln doppelte Schlüssel unterschiedlich.
    obj = dict(paare)
    if len(obj) != len(paare):
        raise ValueError("doppelter Konfigurationsschlüssel")
    return obj


def lade(pfad: Path | None = None) -> dict:
    datei = pfad or KONFIG
    return json.loads(datei.read_text(encoding="utf-8"), object_pairs_hook=_eindeutig)


def lade_profil(pfad: Path) -> dict:
    # JSON ist gültiges YAML. So lesen Client, Offline-Wache und Export genau
    # ein Frontmatter, ohne YAML-Abhängigkeit oder zweite Kopie des Startprofils.
    zeilen = pfad.read_text(encoding="utf-8").splitlines()
    if not zeilen or zeilen[0] != "---" or "---" not in zeilen[1:]:
        raise ValueError("Diagnoseprofil ohne abgeschlossenes Frontmatter")
    return json.loads("\n".join(zeilen[1:zeilen.index("---", 1)]), object_pairs_hook=_eindeutig)


def _kompakter_start(server: dict) -> bool:
    """Stdio ohne weitere Startoptionen; Reihenfolge der Schalter ist egal."""
    args = server.get("args")
    if (set(server) != {"command", "args"} or server["command"] != "npx"
            or not isinstance(args, list) or not all(isinstance(a, str) for a in args)
            or len(args) < 2 or args[0] != "-y" or args[1].rpartition("@")[0] != "@playwright/mcp"):
        return False
    # Exaktheit des Paket-Pins prüft weiterhin M3.
    soll = dict.fromkeys((*PFLICHT_ARGUMENTE, "--no-webmcp"))
    soll.update({"--output-dir": ".cache/mcp", "--allowed-origins": ";".join(ERLAUBTE_ORIGINS),
                 "--console-level": "warning", "--snapshot-mode": "none", "--codegen": "none"})
    it = iter(args[2:])
    for schalter in it:
        if schalter not in soll:
            return False  # auch doppelte Schalter und --option=wert
        wert = soll.pop(schalter)
        if wert is not None and next(it, None) != wert:
            return False
    return not soll


def pruefe_projekt(standard: dict, profil: dict, einstellungen: dict) -> tuple[dict, list[str]]:
    """Normaler Start und bewusst aktivierte Diagnose sind getrennte Verträge."""
    fehler = [] if standard == {"mcpServers": {}} else [
        "M7: Der Projektstandard muss genau einen leeren mcpServers-Block enthalten."
    ]
    if not isinstance(einstellungen, dict) or einstellungen.get("agent") == PROFIL.stem:
        fehler.append("M7: Der Browseragent darf nicht als Standard in .claude/settings.json starten.")
    if not isinstance(profil, dict) or set(profil) != {"name", "description", "tools", "mcpServers", "hooks"}:
        return {}, fehler + ["M7: Unerwartetes oder unvollständiges Diagnose-Frontmatter."]
    if profil["hooks"] != DIAGNOSE_HOOKS:
        fehler.append("M7: Genau der lokale PreToolUse-Hook muss die Diagnoseaufrufe prüfen.")
    if (profil["name"] != PROFIL.stem or not isinstance(profil["description"], str)
            or not profil["description"].strip()):
        fehler.append("M7: Name oder Beschreibung des Diagnose-Agenten fehlt oder passt nicht.")
    tools = profil["tools"]
    if (not isinstance(tools, list) or len(tools) != len(DIAGNOSE_TOOLS)
            or not all(t in tools for t in DIAGNOSE_TOOLS)):
        fehler.append("M7: Der Diagnose-Agent braucht genau die fünf benannten Playwright-Werkzeuge.")
    inline = profil["mcpServers"]
    if not isinstance(inline, list) or len(inline) != 1 or not isinstance(inline[0], dict):
        return {}, fehler + ["M7: Genau eine lokale Inline-Serverdefinition erwartet."]
    config = {"mcpServers": inline[0]}
    fehler.extend(pruefe(config))  # M1–M6 gelten unverändert für das aktive Profil
    server = inline[0].get("playwright")
    if not isinstance(server, dict) or not _kompakter_start(server):
        fehler.append("M7: Startprofil weicht ab (Pin/Startbefehl, Origins, Ablage oder kompakte Ausgabe).")
    return config, fehler


def pruefe_aufruf(event: dict, root: Path) -> str | None:
    """Prüft nur das Tool-Ereignis, startet keinen Browser und schreibt nichts."""
    if (not isinstance(event, dict) or event.get("hook_event_name") != "PreToolUse"
            or event.get("tool_name") not in DIAGNOSE_TOOLS or not isinstance(event.get("tool_input"), dict)):
        return "Unbekannter Diagnoseaufruf; kein Werkzeug freigegeben."
    tool = event["tool_name"].removeprefix("mcp__playwright__browser_")
    args = event["tool_input"]
    datei = args.get("filename")
    if "filename" in args:
        # Explizite Dateinamen wertet Playwright relativ zum Workspace aus,
        # NICHT relativ zu --output-dir. Auch Umwege über Symlinks ablehnen.
        if not isinstance(datei, str) or not re.fullmatch(r"\.cache/mcp/[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", datei):
            return "Belege nur als .cache/mcp/<dateiname> ohne weitere Verzeichnisse ablegen."
        cwd = event.get("cwd")
        if (not isinstance(cwd, str) or Path(cwd).resolve() != root
                or (root / datei).resolve() != root / datei):
            return "Belege nur aus der Projektwurzel und nicht über Symlinks ablegen."

    def nichtleer(wert: object) -> bool:
        return isinstance(wert, str) and bool(wert.strip())

    if tool == "find" and not nichtleer(args.get("text")):
        return "Mit browser_find einen konkreten Text suchen."
    if tool == "snapshot" and not datei:
        tiefe = args.get("depth")
        if "depth" in args and (type(tiefe) is not int or not 1 <= tiefe <= 3):
            return "Für eine Inline-Antwort depth zwischen 1 und 3 wählen."
        if not nichtleer(args.get("target")) and tiefe is None:
            return "Keinen Vollbaum in den Chat laden: target, depth oder lokalen Belegpfad angeben."
    if tool == "console_messages" and args.get("level") not in ("warning", "error"):
        return "Konsole nur mit level warning oder error abrufen."
    if tool == "network_requests" and not datei and (not nichtleer(args.get("filter")) or args.get("static")):
        return "Netzwerkliste filtern und statische Erfolge auslassen oder als lokalen Beleg ablegen."
    return None


def vor_aufruf() -> int:
    try:
        grund = pruefe_aufruf(json.load(sys.stdin), ROOT)
    except (OSError, ValueError, RuntimeError):
        grund = "Diagnoseaufruf oder Belegpfad nicht lesbar."
    if grund:
        print(grund, file=sys.stderr)  # Keine Argumente, URLs oder Inhalte protokollieren.
        return 2  # Claude PreToolUse: blockiert. 0 lässt reguläre Berechtigungen unberührt.
    return 0


# --------------------------------------------------------------------------
#  Selbsttest: jede Regel muss an einer vergifteten Kopie feuern
# --------------------------------------------------------------------------

def _gute_config() -> dict:
    return {
        "mcpServers": {
            "playwright": {
                "command": "npx",
                "args": [
                    "-y", "@playwright/mcp@0.0.83", "--headless", "--isolated",
                    "--block-service-workers", "--output-dir", ".cache/mcp",
                    "--console-level", "warning", "--snapshot-mode", "none",
                    "--codegen", "none", "--no-webmcp", "--allowed-origins",
                    "https://franksfinanzcheck.de;http://127.0.0.1:4173",
                ],
            }
        }
    }


def _mit_args(*neue: str) -> dict:
    config = _gute_config()
    config["mcpServers"]["playwright"]["args"] = list(neue)
    return config


def selftest() -> int:
    fehler: list[str] = []

    def muss(bedingung: bool, text: str) -> None:
        if not bedingung:
            fehler.append(text)

    muss(pruefe(_gute_config()) == [], f"gute Konfiguration muss sauber sein, gemeldet: {pruefe(_gute_config())}")

    # M3: Range statt Pin
    fall = _mit_args("-y", "@playwright/mcp@latest", "--headless", "--isolated",
                     "--block-service-workers", "--output-dir", ".cache/mcp",
                     "--allowed-origins", "https://franksfinanzcheck.de")
    muss(any(f.startswith("M3") for f in pruefe(fall)), "@latest muss als Range auffallen")
    fall = _mit_args("-y", "@playwright/mcp^0.0.83", "--headless", "--isolated",
                     "--block-service-workers", "--output-dir", ".cache/mcp",
                     "--allowed-origins", "https://franksfinanzcheck.de")
    muss(any(f.startswith("M3") for f in pruefe(fall)), "ein ^-Range muss auffallen")
    fall = _mit_args("-y", "@playwright/mcp", "--headless", "--isolated",
                     "--block-service-workers", "--output-dir", ".cache/mcp",
                     "--allowed-origins", "https://franksfinanzcheck.de")
    muss(any(f.startswith("M3") for f in pruefe(fall)), "ein Paket ohne Version muss auffallen")

    # M2: Geheimnis im Klartext
    fall = _gute_config()
    fall["mcpServers"]["playwright"]["env"] = {"GITHUB_TOKEN": "ghp_" + "a" * 24}
    muss(any(f.startswith("M2") for f in pruefe(fall)), "ein Klartext-Token muss auffallen")
    fall["mcpServers"]["playwright"]["env"] = {"GITHUB_TOKEN": "${GITHUB_TOKEN}"}
    muss(not any(f.startswith("M2") for f in pruefe(fall)), "ein ${VAR}-Verweis ist kein Geheimnis")

    # M4: fremder Server
    fall = _gute_config()
    fall["mcpServers"]["github"] = {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-github@1.0.0"]}
    muss(any(f.startswith("M4") for f in pruefe(fall)), "ein nicht erlaubter Server muss auffallen")

    # M5: Härtung fehlt
    fall = _mit_args("-y", "@playwright/mcp@0.0.83", "--allowed-origins", "https://franksfinanzcheck.de")
    gemeldet = pruefe(fall)
    for pflicht in PFLICHT_ARGUMENTE:
        muss(any(pflicht in f for f in gemeldet), f"fehlendes {pflicht} muss auffallen")
    fall = _mit_args("-y", "@playwright/mcp@0.0.83", "--headless", "--isolated",
                     "--block-service-workers", "--allow-unrestricted-file-access",
                     "--allowed-origins", "https://franksfinanzcheck.de")
    muss(any("unrestricted" in f for f in pruefe(fall)), "freier Dateizugriff muss auffallen")
    fall = _mit_args("-y", "@playwright/mcp@0.0.83", "--headless", "--isolated",
                     "--block-service-workers", "--output-dir", ".cache/mcp",
                     "--allowed-origins", "*")
    muss(any("*" in f and f.startswith("M5") for f in pruefe(fall)), "ein *-Ziel muss auffallen")
    fall = _mit_args("-y", "@playwright/mcp@0.0.83", "--headless", "--isolated",
                     "--block-service-workers", "--output-dir", ".cache/mcp",
                     "--allowed-origins", "https://beispielbank.de")
    muss(any("fremdes Ziel" in f for f in pruefe(fall)), "ein fremdes Ziel muss auffallen")

    # M6: Platzhalter
    fall = _mit_args("-y", "@playwright/mcp@0.0.83", "--headless", "--isolated",
                     "--block-service-workers", "--output-dir", ".cache/mcp",
                     "--allowed-origins", "https://CHANGE_ME")
    muss(any(f.startswith("M6") for f in pruefe(fall)), "ein Platzhalter muss auffallen")

    # M1: kaputte Struktur
    muss(any(f.startswith("M1") for f in pruefe({})), "fehlende mcpServers müssen auffallen")
    muss(any(f.startswith("M1") for f in pruefe({"mcpServers": {"playwright": "npx"}})),
         "ein Server ohne Objekt muss auffallen")

    # M7: Autostart, zu breite Toolmenge oder automatische Vollbäume.
    standard = {"mcpServers": {}}
    profil = {"name": PROFIL.stem, "description": "Diagnose", "tools": list(DIAGNOSE_TOOLS),
              "mcpServers": [_gute_config()["mcpServers"]], "hooks": DIAGNOSE_HOOKS}
    muss(not pruefe_projekt(standard, profil, {})[1], "getrennte Profile müssen grün sein")
    muss(bool(pruefe_projekt(_gute_config(), profil, {})[1]), "Autostart muss auffallen")
    muss(bool(pruefe_projekt(standard, {**profil, "tools": ["mcp__playwright__*"]}, {})[1]),
         "eine pauschale Werkzeugfreigabe muss auffallen")
    args = profil["mcpServers"][0]["playwright"]["args"]
    args[args.index("--snapshot-mode") + 1] = "full"
    muss(bool(pruefe_projekt(standard, profil, {})[1]), "automatische Vollbäume müssen auffallen")
    event = {"hook_event_name": "PreToolUse", "tool_name": "mcp__playwright__browser_snapshot", "tool_input": {}}
    muss(bool(pruefe_aufruf(event, ROOT)), "expliziter Inline-Vollbaum muss blockieren")
    muss(not pruefe_aufruf({**event, "tool_input": {"depth": 2}}, ROOT), "begrenzter Snapshot muss gehen")

    if fehler:
        print("🛑 SELBSTTEST DER MCP-WACHE FEHLGESCHLAGEN:")
        for f in fehler:
            print("  ·", f)
        return 2
    print("✅ MCP-Wache: Selbsttest grün (M1–M7, jede Regel feuert an ihrer Sabotageprobe)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MCP-Projektstandard und Diagnoseprofil prüfen.")
    ausgabe = parser.add_mutually_exclusive_group()
    ausgabe.add_argument("--vor-aufruf", action="store_true", help="PreToolUse: Diagnoseaufruf auf stdin prüfen")
    ausgabe.add_argument("--json", action="store_true", help="Maschinenausgabe der Befunde")
    ausgabe.add_argument("--export-profil", action="store_true", help="geprüftes Sitzungsprofil als MCP-JSON ausgeben")
    parser.add_argument("--selftest", action="store_true", help="Sabotageproben ohne Dateizugriff")
    parser.add_argument("--datei", type=Path, help="ein separat vorliegendes aktives MCP-Profil prüfen (M1–M6)")
    args = parser.parse_args(argv)
    if args.vor_aufruf:
        return vor_aufruf()
    if args.export_profil and (args.datei or args.selftest):
        parser.error("--export-profil exportiert ausschließlich das geprüfte Projektprofil")
    if args.selftest:
        return selftest()

    datei = args.datei or KONFIG
    projektlauf = datei.resolve() == KONFIG
    try:
        config = lade(datei)
        if projektlauf:
            einstellungen = lade(EINSTELLUNGEN) if EINSTELLUNGEN.exists() else {}
            config, fehler = pruefe_projekt(config, lade_profil(PROFIL), einstellungen)
        else:
            fehler = pruefe(config)
    except FileNotFoundError as exc:
        fehler = [f"M1: {exc.filename} fehlt."]
    except (OSError, ValueError) as exc:
        fehler = [f"M1: Keine lesbare Konfiguration / kein gültiges JSON: {exc}"]

    if args.export_profil:
        if fehler:
            print("\n".join(fehler), file=sys.stderr)
        else:
            print(json.dumps(config, ensure_ascii=False, indent=2))
    elif args.json:
        print(json.dumps({"datei": str(datei), "befunde": fehler}, ensure_ascii=False, indent=2))
    elif fehler:
        print("🛑 MCP-Wache:", *fehler, sep="\n  · ")
        print("Runbook: docs/ANLEITUNG-PLAYWRIGHT-MCP.md")
    elif not projektlauf:
        print(f"✅ MCP-Wache: {datei.name} sauber (Server: {', '.join(config['mcpServers'])})")
    else:
        print("✅ MCP-Wache: Standard ohne Server · Browserdiagnose auf Abruf mit fünf Werkzeugen.")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
