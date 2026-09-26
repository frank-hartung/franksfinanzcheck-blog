#!/usr/bin/env python3
"""Design-Briefing: Agent-Reach-Signale → prüfbare Varianten-Hypothesen.

Teil der Design-Varianten-Werkbank (Rollout 26.09.2026, Runbook:
docs/ANLEITUNG-DESIGN-VARIANTEN.md).

DIE ROLLENTEILUNG, UM DIE ES HIER GEHT
--------------------------------------
Der Auftrag an die Maschine lautet: Layoutvarianten erzeugen und Daten
auswerten – aber das Design nicht eigenmächtig austauschen. Dieses
Skript ist die erste Hälfte davon, und es hält sich strikt an die
Grenze:

  DARF  Signale aus dem Netz holen (nur lesend, über Agent Reach)
  DARF  sie dem kuratierten Hypothesen-Raster zuordnen
  DARF  Varianten-Skizzen VORSCHLAGEN, inklusive der Regeln, an denen
        sie später gemessen würden
  DARF NICHT  CSS schreiben, das Register ändern, etwas freigeben

Ergebnis ist ein deutschsprachiges Briefing unter
data/design/briefings/. Ob daraus eine Variante wird, entscheidet ein
Mensch – und trägt sie von Hand in data/design/varianten.yaml ein.

WIE ES ARBEITET
---------------
1. Es ruft `scripts/agent_reach_research.py` mit dem Design-Themenplan
   auf (data/agent_reach/design_themenplan.yaml). Kein zweiter Sammler:
   Kanalwahl, Timeouts, Fehlerbehandlung und die „nur lesen"-Leitplanke
   sind dort schon gelöst und getestet.
2. Es liest die JSON-Beilage des Briefs und ordnet jeden Treffer über
   die Stichwortliste des Rasters einem Thema zu.
3. Es schreibt das Briefing: je Thema die Belege, die betroffene
   Oberfläche und die Regeln aus dem Regelwerk, an denen eine solche
   Variante gemessen würde.

AUFRUF
------
  python3 scripts/design_reach_briefing.py                # sammeln + schreiben
  python3 scripts/design_reach_briefing.py --nur-auswerten # letzten Brief neu deuten
  python3 scripts/design_reach_briefing.py --dry-run
  python3 scripts/design_reach_briefing.py --selftest

EXIT-CODES
----------
  0 = Briefing geschrieben
  2 = Plan/Skript-Fehler
  3 = keine einzige Quelle erreichbar (CI soll warnen, nicht abbrechen –
      die Kanalmatrix darf sich ändern, ohne den Betrieb zu stoppen)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAN = ROOT / "data" / "agent_reach" / "design_themenplan.yaml"
BRIEFINGS = ROOT / "data" / "design" / "briefings"
SAMMLER = ROOT / "scripts" / "agent_reach_research.py"
REGELWERK = ROOT / "data" / "design" / "regelwerk.yaml"
REGISTER = ROOT / "data" / "design" / "varianten.yaml"

SAMMEL_TIMEOUT = 600


def _yaml():
    try:
        import yaml
    except ImportError:  # pragma: no cover
        raise SystemExit("PyYAML fehlt: pip install pyyaml")
    return yaml


def heute() -> str:
    return dt.date.today().isoformat()


def jetzt_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ----------------------------------------------------------------------
# Sammeln (delegiert an agent_reach_research.py)
# ----------------------------------------------------------------------

def sammle() -> tuple[int, Path | None]:
    """Ruft den vorhandenen Agent-Reach-Sammler mit dem Design-Plan auf."""
    BRIEFINGS.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [sys.executable, str(SAMMLER), "--plan", str(PLAN),
         "--out-dir", str(BRIEFINGS)],
        capture_output=True, text=True, timeout=SAMMEL_TIMEOUT,
    )
    sys.stderr.write(proc.stderr)
    print(proc.stdout.strip())
    beilage = BRIEFINGS / f"{heute()}-internet-recherche.json"
    return proc.returncode, beilage if beilage.exists() else None


def letzte_beilage() -> Path | None:
    if not BRIEFINGS.exists():
        return None
    treffer = sorted(BRIEFINGS.glob("*-internet-recherche.json"))
    return treffer[-1] if treffer else None


# ----------------------------------------------------------------------
# Auswerten
# ----------------------------------------------------------------------

def alle_treffer(beilage: dict) -> list[dict]:
    """Flache Liste aller Signale aus allen Kanälen."""
    raus: list[dict] = []
    for kanal, quellen in (beilage.get("ergebnisse") or {}).items():
        for quelle, daten in (quellen or {}).items():
            for t in (daten or {}).get("treffer") or []:
                raus.append({
                    "kanal": kanal,
                    "quelle": quelle,
                    "titel": str(t.get("titel") or "").strip(),
                    "url": str(t.get("url") or "").strip(),
                    "datum": str(t.get("datum") or "").strip(),
                })
    return raus


def _trifft(stichwort: str, titel: str) -> bool:
    """Stichwort im Titel – aber nur als ganzes Wort.

    Warum das hier steht: Die erste Fassung suchte per Substring. Damit
    schlug das Stichwort „aria" auf den Titel „Design-Tokens-CSS-
    **Vari**ables" an und das Briefing empfahl eine Barrierefreiheits-
    Variante auf Basis eines Token-Repositories. Falsche Belege sind
    schlimmer als keine: Sie sehen aus wie Evidenz.

    Mehrwortbegriffe („above the fold") funktionieren unverändert, weil
    die Wortgrenze nur außen gesetzt wird.
    """
    return re.search(rf"\b{re.escape(stichwort)}\b", titel) is not None


def ordne_zu(treffer: list[dict], raster: list[dict]) -> dict[str, list[dict]]:
    """Ordnet Signale den Themen zu – ein Signal darf zu mehreren passen.

    Bewusst simple Stichwortsuche im Titel: Ein Ranking-Modell würde
    eine Genauigkeit vortäuschen, die eine Überschriftenzeile nicht
    hergibt. Der Mensch liest ohnehin den Titel, nicht den Score.
    """
    zuordnung: dict[str, list[dict]] = {t["thema"]: [] for t in raster}
    for t in treffer:
        titel = t["titel"].lower()
        for thema in raster:
            woerter = [str(s).lower() for s in (thema.get("signale") or [])]
            getroffen = [w for w in woerter if _trifft(w, titel)]
            if getroffen:
                eintrag = dict(t)
                eintrag["stichwoerter"] = getroffen
                zuordnung[thema["thema"]].append(eintrag)
    return zuordnung


def bekannte_varianten() -> list[str]:
    if not REGISTER.exists():
        return []
    daten = _yaml().safe_load(REGISTER.read_text(encoding="utf-8")) or {}
    return [str(e.get("id")) for e in (daten.get("varianten") or [])]


def briefing(plan: dict, beilage: dict, zuordnung: dict[str, list[dict]]) -> str:
    raster = {t["thema"]: t for t in (plan.get("hypothesen_raster") or [])}
    gesamt = sum(len(v) for v in zuordnung.values())
    z: list[str] = [
        f"# Design-Briefing {heute()}",
        "",
        f"> Erzeugt von `scripts/design_reach_briefing.py` um {jetzt_utc()}.  ",
        f"> Quelle: Agent-Reach-Sammellauf vom {beilage.get('datum', '?')} "
        f"({beilage.get('kanal_ok', 0)} Quelle(n) ok, "
        f"{beilage.get('kanal_fehler', 0)} Fehler).",
        "",
        "> **Status: Vorschlag.** Nichts hier ist eine Entscheidung. Dieses",
        "> Briefing schlägt Varianten-Skizzen vor und nennt die Regeln, an",
        "> denen sie gemessen würden. Ob eine Skizze gebaut wird, entscheidet",
        "> ein Mensch und trägt sie dann von Hand in",
        "> `data/design/varianten.yaml` ein. Die KI schreibt weder CSS noch",
        "> Register noch Freigabe.",
        "",
        f"**{gesamt} von {len(alle_treffer(beilage))} Signalen** ließen sich dem",
        "Hypothesen-Raster zuordnen.",
        "",
    ]

    if not gesamt:
        z += [
            "## Keine Zuordnung",
            "",
            "Diese Woche passte kein Signal ins Raster. Das ist ein gültiges",
            "Ergebnis und kein Fehler – es bedeutet: keine Änderung vorschlagen.",
            "Wenn das mehrere Wochen in Folge passiert, gehört das Raster in",
            "`data/agent_reach/design_themenplan.yaml` überarbeitet, nicht der",
            "Blog.",
            "",
        ]

    vorhandene = bekannte_varianten()

    for thema, signale in zuordnung.items():
        if not signale:
            continue
        meta = raster.get(thema, {})
        z += [
            f"## {thema}",
            "",
            f"* **Oberfläche:** `{meta.get('oberflaeche', '?')}`",
            f"* **ID-Vorschlag:** `{meta.get('id_vorschlag', '?')}`",
            f"* **Würde gemessen an:** "
            + ", ".join(f"`{r}`" for r in (meta.get("pruefen_mit") or [])),
            "",
            "**Belege:**",
            "",
        ]
        for s in signale[:8]:
            datum = f" · {s['datum']}" if s["datum"] else ""
            stich = ", ".join(s["stichwoerter"][:3])
            z.append(f"* [{s['titel']}]({s['url']}) — {s['quelle']}{datum}  \n"
                     f"  <sub>Treffer über: {stich}</sub>")
        if len(signale) > 8:
            z.append(f"* … und {len(signale) - 8} weitere")
        z += [
            "",
            "**Nächster Schritt, falls angenommen:**",
            "",
            "```bash",
            f"# 1. Eintrag in data/design/varianten.yaml anlegen (id: {meta.get('id_vorschlag', 'v-…')})",
            "# 2. assets/css/varianten/<id>.css schreiben (nur Marken-Tokens!)",
            "python3 scripts/design_variant_gate.py --variante <id>   # Marke prüfen",
            "python3 scripts/design_variant_lab.py --lauf <id>        # Tier A",
            "node e2e/variant-metrics.mjs --variante <id>             # Tier B",
            "```",
            "",
        ]

    z += [
        "---",
        "",
        "## Bereits im Register",
        "",
        ", ".join(f"`{v}`" for v in vorhandene) or "_(leer)_",
        "",
        "## Leitplanken dieses Briefings",
        "",
        "* Agent Reach läuft **nur lesend** – keine Posts, keine Logins in CI.",
        "* Kein Signal wird zur Tatsache: Quellen sind verlinkt und vor jeder",
        "  Übernahme zu prüfen.",
        "* Eine Variante entsteht erst durch einen **menschlichen** Eintrag im",
        "  Register und wird erst durch eine **menschliche** Unterschrift live",
        "  (`data/design/regelwerk.yaml` → `freigabe`).",
        "",
    ]
    return "\n".join(z) + "\n"


# ----------------------------------------------------------------------
# Selbsttest
# ----------------------------------------------------------------------

def _selftest() -> int:
    plan = {
        "hypothesen_raster": [
            {"thema": "Hero & Primärhandlung", "oberflaeche": "/",
             "id_vorschlag": "v-hero-*", "signale": ["hero", "cta"],
             "pruefen_mit": ["conversion.ziele.cta_ueber_dem_falz_mobil"]},
            {"thema": "Barrierefreiheit", "oberflaeche": "alle",
             "id_vorschlag": "v-a11y-*", "signale": ["accessibility", "contrast"],
             "pruefen_mit": ["barrierefreiheit.kontrast_fliesstext_min"]},
        ]
    }
    beilage = {
        "datum": "2026-09-26", "kanal_ok": 2, "kanal_fehler": 0,
        "ergebnisse": {
            "rss": {
                "web.dev": {"treffer": [
                    {"titel": "Improving CTA contrast for accessibility",
                     "url": "https://x/1", "datum": "2026-09-20"},
                    {"titel": "Ein Beitrag ohne passendes Stichwort",
                     "url": "https://x/2", "datum": ""},
                ], "fehler": None},
            },
        },
    }

    treffer = alle_treffer(beilage)
    assert len(treffer) == 2

    z = ordne_zu(treffer, plan["hypothesen_raster"])
    # Ein Signal darf in mehreren Themen auftauchen (cta + accessibility)
    assert len(z["Hero & Primärhandlung"]) == 1
    assert len(z["Barrierefreiheit"]) == 1
    assert z["Hero & Primärhandlung"][0]["stichwoerter"] == ["cta"]

    text = briefing(plan, beilage, z)
    assert "# Design-Briefing" in text
    assert "Status: Vorschlag" in text
    assert "Improving CTA contrast" in text
    # Der Brief darf NIE behaupten, etwas sei entschieden
    assert "freigegeben" not in text.lower().split("freigabe")[0].split("\n## ")[0]

    # Wortgrenzen: „Variables" darf NICHT auf „aria" anschlagen
    # (echter Fehlfund vom 26.09.2026, siehe _trifft)
    falle = [{"kanal": "github", "quelle": "q", "datum": "",
              "titel": "renlew/Design-Tokens-CSS-Variables", "url": "u"}]
    z_falle = ordne_zu(falle, [{"thema": "Barrierefreiheit", "oberflaeche": "alle",
                                "id_vorschlag": "v-a11y-*",
                                "signale": ["aria", "contrast"],
                                "pruefen_mit": ["x"]}])
    assert z_falle["Barrierefreiheit"] == [], z_falle
    # …das echte Wort aber schon
    treffer_aria = ordne_zu([{"kanal": "rss", "quelle": "q", "datum": "",
                              "titel": "Using ARIA landmarks correctly", "url": "u"}],
                            [{"thema": "Barrierefreiheit", "oberflaeche": "alle",
                              "id_vorschlag": "v-a11y-*", "signale": ["aria"],
                              "pruefen_mit": ["x"]}])
    assert len(treffer_aria["Barrierefreiheit"]) == 1

    # Mehrwortbegriffe müssen weiter funktionieren
    mehrwort = ordne_zu([{"kanal": "rss", "quelle": "q", "datum": "",
                          "titel": "Designing above the fold in 2026", "url": "u"}],
                        [{"thema": "Hero & Primärhandlung", "oberflaeche": "/",
                          "id_vorschlag": "v-hero-*", "signale": ["above the fold"],
                          "pruefen_mit": ["x"]}])
    assert len(mehrwort["Hero & Primärhandlung"]) == 1

    # Leeres Raster → ehrliche Nullaussage statt erfundener Vorschläge
    leer = ordne_zu([{"kanal": "rss", "quelle": "q", "titel": "Nichts",
                      "url": "u", "datum": ""}], plan["hypothesen_raster"])
    text2 = briefing(plan, beilage, leer)
    assert "Keine Zuordnung" in text2

    # Der echte Plan muss parsbar sein und ein Raster haben
    if PLAN.exists():
        echt = _yaml().safe_load(PLAN.read_text(encoding="utf-8")) or {}
        assert echt.get("hypothesen_raster"), "Design-Themenplan ohne Raster"
        for thema in echt["hypothesen_raster"]:
            assert thema.get("signale"), f"{thema.get('thema')}: keine Stichwörter"
            assert thema.get("pruefen_mit"), f"{thema.get('thema')}: keine Regeln"

    print("selftest: OK (8 Gruppen)")
    return 0


# ----------------------------------------------------------------------
# main
# ----------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Design-Briefing aus Agent-Reach-Signalen")
    ap.add_argument("--nur-auswerten", action="store_true",
                    help="nicht sammeln, letzten Brief neu deuten")
    ap.add_argument("--dry-run", action="store_true", help="Plan zeigen")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return _selftest()

    if not PLAN.exists():
        print(f"Design-Themenplan fehlt: {PLAN}", file=sys.stderr)
        return 2
    plan = _yaml().safe_load(PLAN.read_text(encoding="utf-8")) or {}

    if args.dry_run:
        print(f"Plan: {PLAN}")
        for kanal in ("rss", "github", "web"):
            print(f"  {kanal:8} {len(plan.get(kanal) or [])} Eintrag/Einträge")
        print(f"  raster   {len(plan.get('hypothesen_raster') or [])} Themen")
        return 0

    if args.nur_auswerten:
        pfad = letzte_beilage()
        if not pfad:
            print("Kein vorheriger Brief in data/design/briefings/ gefunden.",
                  file=sys.stderr)
            return 2
        code = 0
    else:
        code, pfad = sammle()
        if not pfad:
            print("Sammellauf lieferte keine Beilage.", file=sys.stderr)
            return 3

    beilage = json.loads(pfad.read_text(encoding="utf-8"))
    zuordnung = ordne_zu(alle_treffer(beilage), plan.get("hypothesen_raster") or [])
    text = briefing(plan, beilage, zuordnung)

    ziel = BRIEFINGS / f"{heute()}-design-hypothesen.md"
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(text, encoding="utf-8")
    print(f"Briefing geschrieben: {ziel.relative_to(ROOT)}")

    zugeordnet = sum(len(v) for v in zuordnung.values())
    print(f"Signale zugeordnet: {zugeordnet}")
    return 3 if (code == 3 and not zugeordnet) else 0


if __name__ == "__main__":
    sys.exit(main())
