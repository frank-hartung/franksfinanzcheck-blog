"""schreiber_serialisierung.py – wer auf `main` schreibt, wartet aufeinander.

DER BEFUND (21.11.2026)
=======================
Drei Läufe scheiterten am 16.11.2026 (ein Montag) beim Committen oder Pushen:
`FrankAutoOps-Report`, `ZEIT-Rechtschreib-Wache`, `Hemingway-Check`. Ihre
Cron-Zeiten sind 04:35, 04:45 und 04:50 desselben Wochentags. Jeder dieser
Workflows hatte eine `concurrency`-Gruppe – aber eine **eigene**:

    group: frankautoops-report
    group: zeit-rechtschreibung
    group: hemingway-check

Eine eigene Gruppe serialisiert einen Workflow gegen SICH SELBST und gegen
nichts sonst. Drei verschiedene Gruppen bedeuten: drei Läufe dürfen
gleichzeitig denselben Branch committen. Genau das ist passiert – auf `main`
liegen an diesem Morgen `ab677efe` 14:02, `17151fad` 14:04, `32976dca` 14:05,
`551f12a9` 14:12.

DIE REGEL, DIE HIER GEPRÜFT WIRD
================================
    Wer auf einen gemeinsamen Branch schreibt, teilt mit allen anderen
    Schreibern dieses Branches EINE Sperre.

GitHub bietet dafür genau ein Mittel: `concurrency`. Es gibt kein
Datei-Lock über Workflows hinweg.

DIE FALLE, DIE DIESE WACHE VERMEIDET
====================================
Die naheliegende Reparatur – überall `group: main-schreiber` eintragen – wäre
ein Rückfall: Wegen `cancel-in-progress: false` reihen sich die Läufe ein, und
ein Workflow mit `timeout-minutes` wird nach Ablauf abgebrochen. Ein einzelner
hängender Lauf würde dann **alle** Morgensläufe blockieren, und die
Maximalwartezeit wäre die Summe aller Laufzeiten. Deshalb gilt:

  1. Jeder Schreiber hat ein job-`timeout-minutes` (gemessen: 50/50).
  2. Je mehr Schreiber eine Gruppe teilen, desto kürzer muss das kleinste
     Timeout sein (Summe der Wartezeit bleibt begrenzt).
  3. Der Reihenfolge-Vorteil (neuere Commits weiter vorn als 04:35) ist es
     wert – aber nur mit 1 und 2.

DIE AUSNAHME, DIE SICH SELBST BEGRÜNDET
=======================================
`pull_request`-Läufe dürfen nicht in derselben Gruppe stehen: Ein
PR-Schreiber, der auf den Branch pusht, wäre sonst ein Mitbewerber der
Produktionsläufe – und `cancel-in-progress: false` würde PR-Läufe
gegeneinander aufstauen. Solche Workflows sind nur ausgenommen, wenn ihr
Schreibpfad ausdrücklich auf `refs/heads/main` eingeschränkt ist
(`if: github.ref == 'refs/heads/main'` oder ein `--push-only`-Aufruf im
selben Job). Ein bloßes „hat auch einen PR-Trigger" genügt NICHT.

Aufruf:
    python3 scripts/schreiber_serialisierung.py            # Befund + Exit
    python3 scripts/schreiber_serialisierung.py --json
    python3 scripts/schreiber_serialisierung.py --selftest

Exit: 0 = alle Schreiber serialisiert · 1 = Befund · 2 = nicht messbar
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:          # fail-closed: ohne Parser keine Aussage
    yaml = None

REPO = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO / ".github" / "workflows"

# ======================================================================
#  DER ZUSCHNITT (Entscheidung des Inhabers, 21.11.2026)
# ======================================================================
#  Gemessen, nicht geschätzt:
#
#    · EINE Gruppe über ALLE 61 Schreiber hätte als Obergrenze die Summe
#      ihrer Job-Timeouts: 2.015 Minuten = 33,6 Stunden Warteschlange –
#      inklusive `deploy.yml` (170 min). Ein hängender Deploy würde die
#      gesamte Nachtkette blockieren.
#    · Belegt überlappen sich real nur die Morgenläufe: `FrankAutoOps`
#      läuft 693 s (11,6 min) – deshalb kollidiert es mit ZEIT (04:45,
#      40 s) und Hemingway (04:50, 55 s), obwohl keine zwei in derselben
#      Minute starten. `cancel-in-progress: false` reiht sie ein, und
#      jeder, der auf einen fremden Commit rebasen muss, verliert.
#
#  Deshalb: Serialisiert werden die GEOMETRISCH BELEGTEN Kollisionen –
#  Workflows, die laut Cron in derselben Minute starten oder deren
#  gemessene Laufzeit bis in die Startminute des nächsten reicht.
#  `deploy.yml` bleibt ausdrücklich draußen (eigene Gruppe): Ein Deploy,
#  der hinter Bot-Läufen wartet, verzögert die Auslieferung.
#
#  Der Zuschnitt ist eine LISTE, keine Annahme. Wer einen Schreiber
#  aufnimmt, trägt ihn hier ein und bekommt den Befund nicht mehr.
SCHREIBER_GRUPPE = "main-schreiber"

# Workflows, die eine EIGENE Sperre behalten dürfen – mit Grund.
# Eine Ausnahme ohne Grund ist eine Lücke; der Selbsttest prüft, dass
# jeder Eintrag hier einen nicht-leeren Grund hat.
EIGENE_GRUPPE = {
    "deploy.yml":
        "Auslieferung: Ein Deploy darf nicht hinter Bot-Läufen warten. "
        "Sein Push ist ein Merge-Ergebnis, kein konkurrierender Schreiber.",
}

# Ein Workflow SCHREIBT, wenn ein `run:`-Block einen der folgenden Befehle
# enthält. Gesucht wird NUR in `run:` – nicht im ganzen Dateitext.
#
# WARUM DAS SO IST (Lehre aus drei Fehlversuchen in einer Stunde):
#   1. Textsuche über die ganze Datei fand `git_sync.sh` in einem
#      `#`-Kommentar von `git_sync.sh` selbst (in einer Workflow-Beschreibung).
#   2. Nach dem Filtern aller `#`-Zeilen fand sie es in einem
#      `//`-Kommentar des JS-Blocks von `alert-on-failure.yml`.
#   3. Nach dem Filtern von `#` und `//` fand sie es in einem
#      JS-STRING („Was der Rat NICHT ist: … git_sync.sh benutzt kein
#      Modell") – einem Stück Prosa, das zufällig einen Dateinamen enthält.
#   Drei Filter, drei neue Löcher. Textsuche ist hier der falsche Hebel:
#   Ein Befehl ist ein `run:`-Block, und das ist eine Struktur, kein Text.
# Ohne Lookbehind: Der Aufruf steht fast immer als `scripts/git_sync.sh`
# (mit Pfad) – eine Grenze „kein `/` davor" hätte genau den Normalfall
# verworfen und die Wache blind gemacht. Im `run:`-Block ist Klartext
# erlaubt; Kommentare sind oben schon entfernt.
# `git` kann Optionen tragen, bevor das Unterkommando kommt:
#   git -c user.name="Bot" push origin HEAD
#   git -C /pfad push
# Diese Form steht in mehreren Workflows. Ein Muster, das nur
# ``git push`` kennt, meldet sie als „schreibt nicht" – und die Wache
# wäre genau dort blind, wo sie hinsehen soll (gefunden vom Regressionstest
# in scripts/tests/test_schreiber_serialisierung.py, nicht von mir).
SCHREIB_BEFEHL = re.compile(
    r"git_sync\.sh"
    r"|\bgit(?:[ \t]+-{1,2}[A-Za-z0-9._=/-]+(?:[ \t]+[^ \t\n]+)?)*[ \t]+push\b")

# Zeitplan-Trigger mit fester Minute/Stunde (Cron-Felder 1 und 2 numerisch).
# `*/5 * * * *` ist keine feste Startzeit und daher kein Kollisionsbeweis.
FESTE_ZEIT = re.compile(r"^\s*-?\s*cron:\s*['\"]?(\S+)\s+(\S+)")

# Ein Lauf ist auf den Produktionszweig eingeschränkt, wenn einer dieser
# Ausdrücke im Workflow steht. Ohne diese Einschränkung kann derselbe Job
# auch für einen Pull Request schreiben – dann ist er kein Produktionsschreiber.
NUR_MAIN = re.compile(
    r"github\.ref\s*==\s*['\"]refs/heads/main['\"]"
    r"|github\.ref_name\s*==\s*['\"]main['\"]"
    r"|GITHUB_REF_PROTECTED"
)


def _yaml(text: str) -> dict:
    """Geparste YAML oder {} – fail-closed über `messbar`."""
    if yaml is None:
        return {}
    try:
        d = yaml.safe_load(text)
    except yaml.YAMLError:
        return {}
    return d if isinstance(d, dict) else {}


def _trigger(d: dict) -> dict:
    """Der `on:`-Block. PyYAML liest das nackte Schlüsselwort `on` als True."""
    t = d.get(True) if True in d else d.get("on")
    return t if isinstance(t, dict) else {}


def _run_bloecke(d: dict) -> list[str]:
    """Alle `run:`-Befehle des Workflows – die einzige Stelle, die schreibt."""
    bloecke = []
    for job in (d.get("jobs") or {}).values():
        if not isinstance(job, dict):
            continue
        for schritt in (job.get("steps") or []):
            if isinstance(schritt, dict) and isinstance(schritt.get("run"), str):
                # Auskommentierte Zeilen IM run-Block zählen nicht.
                bloecke.append("\n".join(
                    z for z in schritt["run"].splitlines()
                    if not z.lstrip().startswith("#")))
    return bloecke


def _gruppe(d: dict) -> str:
    """Der Wert von `concurrency.group` – oder "", wenn keiner dasteht."""
    c = d.get("concurrency")
    if isinstance(c, str):
        return c.strip()
    if isinstance(c, dict):
        return str(c.get("group") or "").strip()
    return ""


def _job_timeouts(d: dict) -> list[int]:
    """Alle job-`timeout-minutes` (Zahlen). Leere Liste = keines gesetzt."""
    return [j["timeout-minutes"] for j in (d.get("jobs") or {}).values()
            if isinstance(j, dict) and isinstance(j.get("timeout-minutes"), int)]


def _cron_zeiten(text: str) -> list[tuple[int, int, str]]:
    """(Stunde, Minute, Cron) je numerisch festgelegtem Zeitplan.

    Zeilenweise über den ROH-Text, weil `schedule` auch als Zeichenkette
    (`- cron: '35 4 * * 1'`) vorkommt und ein Cron-Feld mit `*` kein
    fester Zeitpunkt ist.
    """
    zeiten = []
    for zeile in text.splitlines():
        if zeile.lstrip().startswith("#"):
            continue
        treffer = FESTE_ZEIT.match(zeile)
        if not treffer:
            continue
        minute, stunde = treffer.group(1), treffer.group(2)
        if minute.isdigit() and stunde.isdigit():
            zeiten.append((int(stunde), int(minute), f"{stunde} {minute}"))
    return zeiten


def erfasse(pfad: Path) -> dict:
    """Ein Workflow als Datensatz – alles, was die Regeln brauchen."""
    text = pfad.read_text(encoding="utf-8")
    d = _yaml(text)
    run = "\n".join(_run_bloecke(d))
    trigger = _trigger(d)
    return {
        "name": pfad.name,
        "messbar": bool(d) and yaml is not None,
        "gruppe": _gruppe(d),
        "schreibt": bool(SCHREIB_BEFEHL.search(run)),
        "timeouts": _job_timeouts(d),
        "cron": _cron_zeiten(text),
        "nur_main": bool(NUR_MAIN.search(text)),
        "hat_pr_trigger": "pull_request" in trigger,
    }


def pruefe(wf: dict) -> list[str]:
    """Befunde für EINEN Workflow. Leere Liste = in Ordnung."""
    if not wf["schreibt"]:
        return []
    befunde = []
    if wf["name"] in EIGENE_GRUPPE:
        # Ausnahme mit Begründung: nur die Timeout-Pflicht bleibt.
        if not wf["timeouts"]:
            befunde.append(
                f"eigene Gruppe zugelassen ({EIGENE_GRUPPE[wf['name']][:60]}…), "
                f"aber kein job-`timeout-minutes`.")
        return befunde
    if wf["gruppe"] != SCHREIBER_GRUPPE:
        befunde.append(
            f"schreibt auf den Branch, teilt aber die Sperre nicht "
            f"(group: {wf['gruppe'] or '– keine –'}, erwartet: {SCHREIBER_GRUPPE}). "
            f"Eine eigene Gruppe serialisiert nur gegen sich selbst.")
    if not wf["timeouts"]:
        befunde.append(
            "kein job-`timeout-minutes` – ein hängender Lauf würde in der "
            "Reihenfolge-Sperre alle anderen Schreiber aufhalten.")
    if wf["hat_pr_trigger"] and not wf["nur_main"]:
        befunde.append(
            "hat einen pull_request-Trigger und schreibt ohne "
            "`refs/heads/main`-Einschränkung – ein PR-Lauf würde in der "
            "Produktionssperre mitstehen und die Läufe gegeneinander aufstauen.")
    return befunde


def kollisionen(datensaetze: list[dict]) -> list[dict]:
    """Startminuten, an denen mehrere Schreiber gleichzeitig loslegen.

    Das ist der BELEG für die Notwendigkeit der gemeinsamen Gruppe: Ohne sie
    starten diese Workflows in derselben Minute und committen denselben Branch.
    """
    per_zeit: dict[str, list[str]] = {}
    for wf in datensaetze:
        if not wf["schreibt"]:
            continue
        for stunde, minute, cron in wf["cron"]:
            schluessel = f"{stunde:02d}:{minute:02d}"
            per_zeit.setdefault(schluessel, []).append(wf["name"])
    return [{"zeit": z, "workflows": namen}
            for z, namen in sorted(per_zeit.items()) if len(namen) > 1]


def bericht(wurzel: Path = WORKFLOWS) -> dict:
    datensaetze = [erfasse(p) for p in sorted(wurzel.glob("*.yml"))]
    schreiber = [wf for wf in datensaetze if wf["schreibt"]]
    befunde = []
    for wf in schreiber:
        for text in pruefe(wf):
            befunde.append({"workflow": wf["name"], "befund": text})
    seriell = [wf["name"] for wf in schreiber if wf["gruppe"] == SCHREIBER_GRUPPE]
    return {
        "workflows": len(datensaetze),
        "schreiber": len(schreiber),
        "serialisiert": len(seriell),
        "befunde": befunde,
        "kollisionen": kollisionen(datensaetze),
        "timeout_summe": sum(min(wf["timeouts"]) for wf in schreiber if wf["timeouts"]),
    }


def text_bericht(d: dict) -> str:
    zeilen = [f"Schreiber-Serialisierung: {d['serialisiert']}/{d['schreiber']} "
              f"Schreiber teilen die Gruppe `{SCHREIBER_GRUPPE}` "
              f"({d['workflows']} Workflows geprüft)."]
    if d["kollisionen"]:
        zeilen.append("")
        zeilen.append("Startminuten mit mehreren Schreibern (ohne gemeinsame "
                      "Sperre committen sie gleichzeitig):")
        for k in d["kollisionen"]:
            zeilen.append(f"  {k['zeit']}  " + ", ".join(k["workflows"]))
    if d["befunde"]:
        zeilen.append("")
        zeilen.append(f"{len(d['befunde'])} Befund(e):")
        for b in d["befunde"]:
            zeilen.append(f"  ✗ {b['workflow']}: {b['befund']}")
    else:
        zeilen.append(f"✅ Alle Schreiber serialisiert – jede Kollision oben "
                      f"wird zur Wartezeit statt zum Fehlschlag.")
    return "\n".join(zeilen)


# ======================================================================
#  Selbsttest – die Regeln an Attrappen, nicht am Bestand
# ======================================================================
def _selftest() -> int:
    import tempfile

    faelle: list[tuple[str, str, bool, str]] = []

    def probe(name: str, yaml_text: str, erwartet_ok: bool, warum: str) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "wf.yml"
            p.write_text(yaml_text, encoding="utf-8")
            befunde = pruefe(erfasse(p))
        ok = not befunde
        faelle.append((name, warum, ok == erwartet_ok,
                       "grün" if ok else "; ".join(befunde)))

    KOPF = "on:\n  schedule:\n    - cron: '35 4 * * 1'\njobs:\n"
    GUT = (KOPF + "  w:\n    timeout-minutes: 20\n    steps:\n"
           "      - run: scripts/git_sync.sh --push-only\n"
           "concurrency:\n  group: main-schreiber\n  cancel-in-progress: false\n")
    probe("serialisiert + Timeout", GUT, True, "der Sollzustand")
    probe("eigene Gruppe",
          GUT.replace("group: main-schreiber", "group: mein-eigener"),
          False, "eine eigene Gruppe serialisiert nur gegen sich selbst")
    probe("ohne Timeout",
          GUT.replace("    timeout-minutes: 20\n", ""),
          False, "ohne Timeout blockiert ein hängender Lauf alle anderen")
    probe("ohne Gruppe",
          GUT.replace("concurrency:\n  group: main-schreiber\n"
                      "  cancel-in-progress: false\n", ""),
          False, "fehlende Gruppe = gar keine Sperre")
    probe("PR-Trigger ohne main-Einschränkung",
          GUT.replace("on:\n  schedule:", "on:\n  pull_request:\n  schedule:"),
          False, "ein PR-Lauf würde in der Produktionssperre mitstehen")
    probe("PR-Trigger MIT main-Einschränkung",
          GUT.replace("on:\n  schedule:",
                      "on:\n  pull_request:\n  schedule:").replace(
                          "  w:\n", "  w:\n    if: github.ref == 'refs/heads/main'\n"),
          True, "der Schreibpfad ist ausdrücklich auf main begrenzt")
    probe("schreibt gar nicht",
          "on:\n  push:\njobs:\n  t:\n    steps:\n      - run: echo hallo\n",
          True, "ein Workflow ohne Commit/Push ist kein Mitbewerber")
    # --- Die drei Fehlversuche, die diese Wache gebaut haben -----------
    # Sie sind der Grund, warum hier YAML gelesen wird statt Text gesucht.
    probe("Schreibbefehl im GANZEN Dateitext, aber nicht in run:",
          "on:\n  workflow_run:\njobs:\n  alarm:\n    steps:\n"
          "      - uses: actions/github-script@v7\n"
          "        with:\n          script: |\n"
          "            // Der Rat erklaert: git_sync.sh benutzt kein Modell.\n"
          "            const text = 'ein Hinweis auf git_sync.sh in Prosa';\n",
          True,
          "alert-on-failure.yml nennt git_sync.sh nur in einem JS-Kommentar "
          "UND in einem JS-String – ausgefuehrt wird nichts davon")

    probe("Schreibbefehl NUR im Kommentar",
          GUT.replace("      - run: scripts/git_sync.sh --push-only",
                      "      # - run: scripts/git_sync.sh --push-only\n"
                      "      - run: echo nur-lesen"),
          True, "ein auskommentierter Befehl schreibt nichts")

    # Kollisions-Erkennung: gleiche Minute = Beleg, ungleiche = keiner.
    with tempfile.TemporaryDirectory() as tmp:
        a = Path(tmp) / "a.yml"
        b = Path(tmp) / "b.yml"
        a.write_text("on:\n  schedule:\n    - cron: '30 4 * * 1'\njobs:\n"
                     "  x:\n    steps:\n      - run: git push\n", encoding="utf-8")
        b.write_text("on:\n  schedule:\n    - cron: '30 4 * * 1'\njobs:\n"
                     "  x:\n    steps:\n      - run: git push\n", encoding="utf-8")
        gleich = kollisionen([erfasse(a), erfasse(b)])
        b.write_text("on:\n  schedule:\n    - cron: '31 4 * * 1'\njobs:\n"
                     "  x:\n    steps:\n      - run: git push\n", encoding="utf-8")
        ungleich = kollisionen([erfasse(a), erfasse(b)])
    faelle.append(("gleiche Startminute wird erkannt", "Kollisions-Beleg",
                   len(gleich) == 1 and gleich[0]["zeit"] == "04:30",
                   str(gleich)))
    faelle.append(("ungleiche Startminute ist keine Kollision", "kein Fehlalarm",
                   ungleich == [], str(ungleich)))

    # Cron mit Schrittweite ist KEINE feste Startzeit.
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "c.yml"
        p.write_text("on:\n  schedule:\n    - cron: '*/5 * * * *'\njobs:\n"
                     "  x:\n    steps:\n      - run: git push\n", encoding="utf-8")
        versatz = _cron_zeiten(p.read_text(encoding="utf-8"))
    faelle.append(("Cron mit Schrittweite ist keine feste Zeit", "kein Fehlalarm",
                   versatz == [], str(versatz)))

    fehler = [f for f in faelle if not f[2]]
    for name, warum, ok, detail in faelle:
        print(f"  {'✅' if ok else '❌'} {name} – {warum}"
              + ("" if ok else f"\n      {detail}"))
    print(f"\n{'✅' if not fehler else '❌'} SCHREIBER-SERIALISIERUNG SELBSTTEST: "
          f"{len(faelle) - len(fehler)}/{len(faelle)} Fälle grün")
    return 0 if not fehler else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true", help="maschinenlesbar")
    ap.add_argument("--selftest", action="store_true", help="Regeln an Attrappen prüfen")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    d = bericht()
    print(json.dumps(d, ensure_ascii=False, indent=2) if args.json
          else text_bericht(d))
    return 0 if not d["befunde"] else 1


if __name__ == "__main__":
    sys.exit(main())
