#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
#  MCP-WACHE – ein Werkzeug für Agenten, kein Einfallstor
#  ------------------------------------------------------------
#  WARUM ES DIESE WACHE GIBT (26.10.2026)
#
#  `.mcp.json` ist die Datei, mit der ein KI-Client (Claude Code,
#  Cursor, VS Code …) Werkzeuge bekommt, die in diesem Repo laufen.
#  Sie ist damit dreierlei gleichzeitig:
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
#  WAS GEPRÜFT WIRD (M1–M6)
#    M1 DATEI      `.mcp.json` existiert, ist gültiges JSON und hat
#                  einen `mcpServers`-Block.
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


def lade(pfad: Path | None = None) -> dict:
    datei = pfad or KONFIG
    return json.loads(datei.read_text(encoding="utf-8"))


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
                    "--allowed-origins",
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

    if fehler:
        print("🛑 SELBSTTEST DER MCP-WACHE FEHLGESCHLAGEN:")
        for f in fehler:
            print("  ·", f)
        return 2
    print("✅ MCP-Wache: Selbsttest grün (M1–M6, jede Regel feuert an ihrer Sabotageprobe)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wache über .mcp.json (Pinning, Befugnisse, Geheimnisse).")
    parser.add_argument("--json", action="store_true", help="Maschinenausgabe")
    parser.add_argument("--selftest", action="store_true", help="Sabotageproben ohne Dateizugriff")
    parser.add_argument("--datei", type=Path, default=None, help="abweichende Konfiguration prüfen")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    datei = args.datei or KONFIG
    try:
        config = lade(datei)
    except FileNotFoundError:
        print(f"🛑 {datei.relative_to(ROOT) if datei.is_relative_to(ROOT) else datei} fehlt – "
              "ohne Konfiguration hat kein Agent Werkzeuge (und niemand weiß warum).")
        return 1
    except json.JSONDecodeError as exc:
        print(f"🛑 {datei}: kein gültiges JSON – {exc}")
        return 1

    fehler = pruefe(config)
    if args.json:
        print(json.dumps({"datei": str(datei), "befunde": fehler}, ensure_ascii=False, indent=2))
    elif fehler:
        print(f"🛑 MCP-Wache: {len(fehler)} Befund(e) in {datei.name}")
        for f in fehler:
            print("  ·", f)
        print("\nRunbook: docs/ANLEITUNG-PLAYWRIGHT-MCP.md")
    else:
        server = ", ".join(config.get("mcpServers", {})) or "keine"
        print(f"✅ MCP-Wache: {datei.name} sauber (Server: {server})")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
