#!/usr/bin/env python3
# ============================================================
#  HAKEN-WÄCHTER – die Commit-Sperre stellt sich selbst scharf
#  ------------------------------------------------------------
#  WARUM ES DIESEN WÄCHTER GIBT (04.10.2026, Vorgang WF-A4E0 / #552):
#    Die Commit-Sperre `.githooks/pre-commit` hält Betriebssprache aus
#    dem README (= Markenfläche). Git führt mitgelieferte Haken aber aus
#    Sicherheitsgründen NIE von selbst aus: in einer frischen Arbeits-
#    kopie ist die Sperre schlicht nicht da – lautlos. Der Restbefund
#    nach der ersten Heilung lautete deshalb „einmal pro Arbeitskopie
#    `npm run hooks:install` ausführen". Das ist eine Bitte, keine
#    Leitplanke: Wer sie vergisst, merkt es erst am roten Lauf nach dem
#    Push – also genau dort, wo der Fehler schon öffentlich ist.
#
#  WAS DIESER WÄCHTER TUT:
#    · stellt die Sperre scharf und LIEST DAS ERGEBNIS ZURÜCK –
#      scharf gilt nur, was nachgeprüft ist
#    · hängt sich dafür als kleine Weiterleitung in die Hakenablage, die
#      git tatsächlich benutzt (`git rev-parse --git-path hooks`), statt
#      mit `core.hooksPath` alle anderen Haken stillzulegen
#    · BEWAHRT vorhandene Haken: ein fremder pre-commit wird zur Seite
#      gelegt und von der Weiterleitung zuerst aufgerufen, nicht ersetzt
#    · repariert das Ausführungsrecht, ist idempotent, kennt keinen
#      Netzzugriff, braucht kein Zugangsrecht und läuft < 1 Sekunde
#    · läuft an jedem Eingang, den eine Arbeitskopie realistisch nimmt:
#      `npm install` (prepare), jeder Marken-Lauf, `npm run hooks:install`
#    · ist leise, wenn alles steht (`--leise`), und laut, wenn nicht
#
#  WARUM WEITERLEITUNG STATT core.hooksPath:
#    `core.hooksPath=.githooks` war der erste Weg (04.10.2026 vormittags).
#    Er schaltet aber ALLE Haken unter .git/hooks ab – lautlos, inklusive
#    fremder Werkzeuge (Signatur-, Trailer- oder Lint-Haken). Eine
#    Leitplanke, die anderen Leitplanken die Bremse zieht, ist keine.
#    Bereits so eingerichtete Arbeitskopien bleiben gültig; verdeckt die
#    Einstellung dort echte Haken, zieht `--install` sie auf die
#    Weiterleitung um und sagt es.
#
#  BEFEHLE:
#    --status     Bericht (menschlich oder --json), Exit immer 0
#    --check      nur prüfen: Exit 1, wenn die Sperre nicht scharf ist
#    --install    scharfstellen + Nachprüfung (idempotent)
#    --leise      nur reden, wenn sich etwas ändert oder etwas fehlt
#    --selftest   Beweis in Wegwerf-Repos (ein blinder Wächter wäre
#                 schlimmer als keiner)
# ============================================================
"""Selbstscharfstellung und Zustandsbericht der lokalen Commit-Sperre."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ABLAGE = ".githooks"            # versionierte Haken (die Wahrheit im Repo)
HAKEN = "pre-commit"
BEWAHRT = "pre-commit.lokal"    # zur Seite gelegter fremder Haken
MARKE = "haken-wache:1"         # Erkennungs- und Versionsmarke der Weiterleitung
DOKU = "docs/ENTWICKLER-WERKZEUGE.md"

# Zustände (Reihenfolge = Dringlichkeit)
SCHARF = "scharf"              # alles steht
NACHGEZOGEN = "nachgezogen"    # war nicht scharf, ist es jetzt
UNSCHARF = "unscharf"          # Sperre fehlt, wäre aber einrichtbar
FREMD = "fremd"                # fremde Hakenablage – wird nicht angefasst
KEIN_REPO = "kein-repo"        # Export/Tarball ohne .git – gegenstandslos
DEFEKT = "defekt"              # Hakendatei fehlt oder ist nicht ausführbar

WEITERLEITUNG = """#!/bin/sh
# ------------------------------------------------------------------
#  Weiterleitung auf die versionierte Commit-Sperre der Markenfläche.
#  Erzeugt von scripts/haken_wache.py ({marke}) – diese Datei liegt
#  bewusst NICHT im Repo: jede Arbeitskopie richtet sie selbst ein
#  (npm install, npm run hooks:install oder jeder Marken-Lauf).
#
#  Reihenfolge: erst ein bereits vorhandener örtlicher Haken
#  ({bewahrt}), dann die Markenflächen-Sperre. Nichts wird
#  stillgelegt, nichts überschrieben.
# ------------------------------------------------------------------
ORDNER="$(dirname "$0")"
if [ -x "$ORDNER/{bewahrt}" ]; then
  "$ORDNER/{bewahrt}" "$@" || exit $?
fi
WURZEL="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
SPERRE="$WURZEL/{ablage}/{haken}"
[ -x "$SPERRE" ] || exit 0   # alter Stand ohne Sperre: nichts zu tun
exec "$SPERRE" "$@"
""".format(marke=MARKE, bewahrt=BEWAHRT, ablage=ABLAGE, haken=HAKEN)


# =====================================================================
#  Git-Zugriff (klein gehalten – der Selbsttest fährt echte Repos)
# =====================================================================
def git(*argumente: str, cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *argumente], cwd=cwd, capture_output=True,
                          text=True, timeout=30)


def ist_repo(wurzel: str) -> bool:
    if not shutil.which("git"):
        return False
    ergebnis = git("rev-parse", "--is-inside-work-tree", cwd=wurzel)
    return ergebnis.returncode == 0 and ergebnis.stdout.strip() == "true"


def hakenordner(wurzel: str) -> str:
    """Die Ablage, aus der git in DIESER Arbeitskopie Haken startet.

    `--git-path hooks` beantwortet das für Klone, Worktrees und
    Sonderfälle korrekt und berücksichtigt `core.hooksPath`.
    """
    ergebnis = git("rev-parse", "--git-path", "hooks", cwd=wurzel)
    pfad = ergebnis.stdout.strip() or os.path.join(".git", "hooks")
    return pfad if os.path.isabs(pfad) else os.path.normpath(os.path.join(wurzel, pfad))


def hookspath_einstellung(wurzel: str) -> str:
    ergebnis = git("config", "--get", "core.hooksPath", cwd=wurzel)
    return ergebnis.stdout.strip() if ergebnis.returncode == 0 else ""


def _ist_unsere_ablage(wert: str, wurzel: str) -> bool:
    if not wert:
        return False
    kandidat = wert if os.path.isabs(wert) else os.path.join(wurzel, wert)
    try:
        return os.path.realpath(kandidat) == os.path.realpath(os.path.join(wurzel, ABLAGE))
    except OSError:  # pragma: no cover - defensiv
        return False


def _ausfuehrbar(pfad: str) -> bool:
    return os.path.isfile(pfad) and os.access(pfad, os.X_OK)


def _ausfuehrbar_machen(pfad: str) -> bool:
    """True, wenn etwas geändert wurde. Dateisysteme ohne x-Bit melden
    das ehrlich über `_ausfuehrbar` danach (siehe Zustand DEFEKT)."""
    if not os.path.isfile(pfad) or _ausfuehrbar(pfad):
        return False
    os.chmod(pfad, os.stat(pfad).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return True


def _inhalt(pfad: str) -> str:
    try:
        with open(pfad, encoding="utf-8", errors="replace") as datei:
            return datei.read()
    except OSError:  # pragma: no cover - defensiv
        return ""


# =====================================================================
#  Befund (reiner Lesevorgang)
# =====================================================================
def befund(wurzel: str = HIER) -> dict:
    sperre = os.path.join(wurzel, ABLAGE, HAKEN)
    zustand = {
        "wurzel": wurzel,
        "git": shutil.which("git") is not None,
        "repo": False,
        "sperre_vorhanden": os.path.isfile(sperre),
        "sperre_ausfuehrbar": _ausfuehrbar(sperre),
        "hooksPath": "",
        "hakenordner": "",
        "weg": "",              # „weiterleitung" | „hooksPath" | „"
        "weiterleitung_aktuell": False,
        "bewahrter_haken": False,
        "verdeckte_haken": [],
        "scharf": False,
        "zustand": KEIN_REPO,
    }

    if not ist_repo(wurzel):
        return zustand
    zustand["repo"] = True

    einstellung = hakenpfad = hookspath_einstellung(wurzel)
    zustand["hooksPath"] = einstellung
    ordner = hakenordner(wurzel)
    zustand["hakenordner"] = ordner

    if not zustand["sperre_vorhanden"]:
        zustand["zustand"] = DEFEKT
        return zustand

    # Weg 1 (Standard): Weiterleitung in der benutzten Hakenablage
    ziel = os.path.join(ordner, HAKEN)
    inhalt = _inhalt(ziel)
    zustand["weiterleitung_aktuell"] = MARKE in inhalt and _ausfuehrbar(ziel)
    zustand["bewahrter_haken"] = _ausfuehrbar(os.path.join(ordner, BEWAHRT))

    # Weg 2 (Altbestand): core.hooksPath zeigt direkt auf .githooks
    eigener_hookspath = _ist_unsere_ablage(hakenpfad, wurzel)

    if hakenpfad and not eigener_hookspath and not zustand["weiterleitung_aktuell"]:
        # Fremde Ablage ohne unsere Weiterleitung: wir dürfen dort schreiben,
        # aber nur, wenn die Ablage nicht Teil des Arbeitsbaums ist (sonst
        # würden wir fremden, versionierten Bestand verändern).
        if _im_arbeitsbaum(ordner, wurzel):
            zustand["weg"] = ""
            zustand["zustand"] = FREMD
            return zustand

    if zustand["weiterleitung_aktuell"]:
        zustand["weg"] = "weiterleitung"
        zustand["scharf"] = zustand["sperre_ausfuehrbar"]
        zustand["zustand"] = SCHARF if zustand["scharf"] else DEFEKT
    elif eigener_hookspath:
        zustand["weg"] = "hooksPath"
        zustand["scharf"] = zustand["sperre_ausfuehrbar"]
        zustand["zustand"] = SCHARF if zustand["scharf"] else DEFEKT
        # Was legt diese Einstellung still? Das gehört auf den Tisch.
        zustand["verdeckte_haken"] = _echte_haken(_standard_hakenordner(wurzel))
    else:
        zustand["zustand"] = UNSCHARF

    return zustand


def _im_arbeitsbaum(pfad: str, wurzel: str) -> bool:
    try:
        gemein = os.path.realpath(os.path.commonpath(
            [os.path.realpath(pfad), os.path.realpath(wurzel)]))
    except ValueError:  # pragma: no cover - verschiedene Laufwerke
        return False
    if gemein != os.path.realpath(wurzel):
        return False
    rest = os.path.relpath(os.path.realpath(pfad), os.path.realpath(wurzel))
    return not rest.startswith(".git" + os.sep) and rest != ".git"


def _standard_hakenordner(wurzel: str) -> str:
    gemeinsam = git("rev-parse", "--git-common-dir", cwd=wurzel).stdout.strip() or ".git"
    if not os.path.isabs(gemeinsam):
        gemeinsam = os.path.join(wurzel, gemeinsam)
    return os.path.join(gemeinsam, "hooks")


def _echte_haken(ordner: str) -> list[str]:
    """Ausführbare Haken ohne `.sample` – also solche, die wirklich liefen."""
    if not os.path.isdir(ordner):
        return []
    return sorted(name for name in os.listdir(ordner)
                  if not name.endswith(".sample")
                  and name not in (HAKEN, BEWAHRT)
                  and _ausfuehrbar(os.path.join(ordner, name)))


# =====================================================================
#  Scharfstellen (mit Nachprüfung – „geschrieben" ist kein Beweis)
# =====================================================================
def scharfstellen(wurzel: str = HIER) -> tuple[dict, list[str]]:
    getan: list[str] = []
    vorher = befund(wurzel)

    if not vorher["repo"] or vorher["zustand"] == FREMD:
        return vorher, getan

    sperre = os.path.join(wurzel, ABLAGE, HAKEN)
    if _ausfuehrbar_machen(sperre):
        getan.append(f"Ausführungsrecht für {ABLAGE}/{HAKEN} gesetzt")
    if not os.path.isfile(sperre):
        return befund(wurzel), getan

    # Altbestand: core.hooksPath=.githooks legt echte Haken stumm → umziehen.
    if vorher["weg"] == "hooksPath" and vorher["verdeckte_haken"]:
        git("config", "--local", "--unset", "core.hooksPath", cwd=wurzel)
        getan.append("core.hooksPath gelöst – die Einstellung legte vorhandene "
                     f"Haken still ({', '.join(vorher['verdeckte_haken'])})")

    ordner = hakenordner(wurzel)
    os.makedirs(ordner, exist_ok=True)
    ziel = os.path.join(ordner, HAKEN)

    # Fremden Haken bewahren statt überschreiben.
    if os.path.isfile(ziel) and MARKE not in _inhalt(ziel):
        bewahrt = os.path.join(ordner, BEWAHRT)
        if os.path.exists(bewahrt):
            os.replace(bewahrt, bewahrt + ".alt")
            getan.append(f"früher bewahrter Haken nach {BEWAHRT}.alt gesichert")
        os.replace(ziel, bewahrt)
        _ausfuehrbar_machen(bewahrt)
        getan.append(f"vorhandenen pre-commit bewahrt → {BEWAHRT} "
                     "(läuft weiterhin, jetzt vor der Sperre)")

    if _inhalt(ziel) != WEITERLEITUNG:
        with open(ziel, "w", encoding="utf-8") as datei:
            datei.write(WEITERLEITUNG)
        getan.append(f"Commit-Sperre eingehängt → {os.path.relpath(ziel, wurzel)}")
    _ausfuehrbar_machen(ziel)

    nachher = befund(wurzel)   # Nachprüfung: zurücklesen, nicht glauben
    if getan and nachher["zustand"] == SCHARF and not vorher["scharf"]:
        nachher["zustand"] = NACHGEZOGEN
    return nachher, getan


# =====================================================================
#  Bericht
# =====================================================================
def _reparaturweg(zustand: dict) -> list[str]:
    lage = zustand["zustand"]
    if lage == FREMD:
        return [
            f"Diese Arbeitskopie startet Haken aus „{zustand['hooksPath']}“ "
            "(fremdes Hakenwerkzeug) – das wird nicht überschrieben.",
            f"Weg 1: dort eine Zeile ergänzen → "
            f"exec \"$(git rev-parse --show-toplevel)\"/{ABLAGE}/{HAKEN} \"$@\"",
            "Weg 2: bewusst umschalten → `git config --local --unset "
            "core.hooksPath && npm run hooks:install`",
            f"Hintergrund: {DOKU}",
        ]
    if lage == KEIN_REPO:
        return ["Kein Git-Arbeitsbaum (Export/Tarball) – eine Commit-Sperre ist "
                "hier gegenstandslos. Im Klon richtet sie sich selbst ein."]
    if lage == DEFEKT and not zustand["sperre_vorhanden"]:
        return [f"Hakendatei fehlt: {ABLAGE}/{HAKEN} – Arbeitskopie unvollständig "
                f"(`git checkout {ABLAGE}`).", f"Hintergrund: {DOKU}"]
    if lage == DEFEKT:
        return ["Die Hakendatei ist nicht ausführbar und das Dateisystem erlaubt "
                "kein x-Bit. Abhilfe: `git update-index --chmod=+x "
                f"{ABLAGE}/{HAKEN}` oder Arbeitskopie auf ein Dateisystem mit "
                "Ausführungsrechten legen.", f"Hintergrund: {DOKU}"]
    if lage == UNSCHARF:
        return ["Scharfstellen: `npm run hooks:install` (oder einmal `npm install`).",
                f"Hintergrund: {DOKU}"]
    return []


def bericht(zustand: dict, getan: list[str], leise: bool) -> None:
    lage = zustand["zustand"]
    if leise and lage == SCHARF and not getan:
        return

    if lage in (SCHARF, NACHGEZOGEN):
        kopf = ("✅ Commit-Sperre Markenfläche ist scharf"
                if lage == SCHARF else "🔧 Commit-Sperre Markenfläche scharfgestellt")
        weg = ("Weiterleitung in " + os.path.relpath(zustand["hakenordner"],
                                                     zustand["wurzel"])
               if zustand["weg"] == "weiterleitung" else
               f"core.hooksPath={zustand['hooksPath']}")
        print(f"{kopf} ({weg}).")
        for schritt in getan:
            print(f"   · {schritt}")
        if zustand["bewahrter_haken"]:
            print(f"   · vorhandener örtlicher Haken bleibt aktiv ({BEWAHRT})")
        if zustand["verdeckte_haken"]:
            print("   ⚠ core.hooksPath legt diese Haken still: "
                  + ", ".join(zustand["verdeckte_haken"])
                  + " – `npm run hooks:install` zieht das auf die Weiterleitung um.")
        return

    symbol = "ℹ️" if lage == KEIN_REPO else "🛑"
    titel = {
        FREMD: "Commit-Sperre NICHT scharf – fremde Hakenablage",
        KEIN_REPO: "Commit-Sperre nicht anwendbar",
        DEFEKT: "Commit-Sperre NICHT scharf – Hakendatei defekt",
        UNSCHARF: "Commit-Sperre NICHT scharf",
    }.get(lage, "Commit-Sperre NICHT scharf")
    print(f"{symbol} {titel}.")
    for zeile in _reparaturweg(zustand):
        print(f"   {zeile}")


# =====================================================================
#  Selbsttest – ein blinder Wächter wäre schlimmer als keiner
# =====================================================================
def _wegwerf_repo(ordner: str, mit_wache: bool = False) -> None:
    """Minimaler Klon-Ersatz: Repo mit .githooks/pre-commit, ohne Einrichtung."""
    subprocess.run(["git", "init", "-q", ordner], check=True, timeout=30)
    for name, wert in (("user.email", "test@example.invalid"), ("user.name", "Test")):
        subprocess.run(["git", "-C", ordner, "config", name, wert], check=True, timeout=30)
    os.makedirs(os.path.join(ordner, ABLAGE), exist_ok=True)
    ziel = os.path.join(ordner, ABLAGE, HAKEN)
    shutil.copyfile(os.path.join(HIER, ABLAGE, HAKEN), ziel)
    os.chmod(ziel, 0o644)   # bewusst ohne x-Bit: der Wächter soll es richten
    if mit_wache:
        os.makedirs(os.path.join(ordner, "scripts"), exist_ok=True)
        shutil.copyfile(os.path.join(HIER, "scripts", "brand_surface_guard.py"),
                        os.path.join(ordner, "scripts", "brand_surface_guard.py"))
        os.makedirs(os.path.join(ordner, "data"), exist_ok=True)
        open(os.path.join(ordner, "data", "brand_surface_allowlist.txt"), "w").close()


def _commit_versuch(ordner: str, text: str) -> subprocess.CompletedProcess:
    with open(os.path.join(ordner, "README.md"), "w", encoding="utf-8") as datei:
        datei.write(text)
    subprocess.run(["git", "-C", ordner, "add", "README.md"], check=True, timeout=30)
    return subprocess.run(["git", "-C", ordner, "commit", "-m", "Probe"],
                          capture_output=True, text=True, timeout=120)


BETRIEBSSPRACHE = ("# FranksFinanzcheck\n\n## Blogautomatik\n"
                   "Vollautomatische Workflows über `scripts/publish.py`.\n")
MARKENTEXT = ("# FranksFinanzcheck\n\nUnabhängiger Finanz-Ratgeber von Frank "
              "Hartung: Strom, Gas, DSL, Versicherungen.\n")


def selftest() -> int:
    fehler: list[str] = []

    with tempfile.TemporaryDirectory() as basis:
        # F1: frische Arbeitskopie ist NICHT scharf (sonst wäre der Befund blind)
        eins = os.path.join(basis, "frisch")
        _wegwerf_repo(eins, mit_wache=True)
        if befund(eins)["scharf"]:
            fehler.append("F1: unscharfe Arbeitskopie wird als scharf gemeldet")

        # F2: Scharfstellen wirkt, wird nachgelesen und repariert das x-Bit
        nachher, getan = scharfstellen(eins)
        if nachher["zustand"] != NACHGEZOGEN or nachher["weg"] != "weiterleitung":
            fehler.append(f"F2: Scharfstellen ohne Wirkung ({nachher['zustand']})")
        if not _ausfuehrbar(os.path.join(eins, ABLAGE, HAKEN)):
            fehler.append("F2: Hakendatei blieb ohne Ausführungsrecht")
        if not any("Ausführungsrecht" in schritt for schritt in getan):
            fehler.append("F2: Reparatur des x-Bits wurde nicht berichtet")

        # F3: scharf heißt WIRKSAM – echter Commit-Versuch, beide Richtungen
        rot = _commit_versuch(eins, BETRIEBSSPRACHE)
        if rot.returncode == 0:
            fehler.append("F3: scharfe Sperre ließ Betriebssprache durch")
        elif "Markenflächen-Sperre" not in (rot.stdout + rot.stderr):
            fehler.append("F3: Sperre schlug an, aber ohne erkennbare Begründung")
        gruen = _commit_versuch(eins, MARKENTEXT)
        if gruen.returncode != 0:
            fehler.append(f"F3: saubere Markenfläche wurde blockiert: {gruen.stderr}")

        # F4: zweiter Lauf ändert nichts (idempotent, leise)
        wieder, getan2 = scharfstellen(eins)
        if wieder["zustand"] != SCHARF or getan2:
            fehler.append(f"F4: zweiter Lauf ist nicht idempotent ({getan2})")

        # F5: vorhandener fremder Haken wird bewahrt und läuft weiter
        zwei = os.path.join(basis, "fremder-haken")
        _wegwerf_repo(zwei, mit_wache=True)
        spur = os.path.join(zwei, "spur.txt")
        eigener = os.path.join(zwei, ".git", "hooks", HAKEN)
        os.makedirs(os.path.dirname(eigener), exist_ok=True)
        with open(eigener, "w", encoding="utf-8") as datei:
            datei.write(f"#!/bin/sh\necho eigen >> {spur}\n")
        os.chmod(eigener, 0o755)
        bewahrt_zustand, bewahrt_getan = scharfstellen(zwei)
        if not bewahrt_zustand["bewahrter_haken"]:
            fehler.append("F5: vorhandener Haken wurde nicht bewahrt")
        if not any("bewahrt" in schritt for schritt in bewahrt_getan):
            fehler.append("F5: Bewahrung wurde nicht berichtet")
        _commit_versuch(zwei, MARKENTEXT)
        if not os.path.exists(spur):
            fehler.append("F5: bewahrter Haken lief nach dem Einhängen nicht mehr")
        if _commit_versuch(zwei, BETRIEBSSPRACHE).returncode == 0:
            fehler.append("F5: mit bewahrtem Haken greift die Sperre nicht mehr")

        # F6: Altbestand core.hooksPath=.githooks gilt als scharf …
        drei = os.path.join(basis, "altbestand")
        _wegwerf_repo(drei, mit_wache=True)
        os.chmod(os.path.join(drei, ABLAGE, HAKEN), 0o755)
        subprocess.run(["git", "-C", drei, "config", "core.hooksPath", ABLAGE],
                       check=True, timeout=30)
        alt = befund(drei)
        if alt["zustand"] != SCHARF or alt["weg"] != "hooksPath":
            fehler.append(f"F6: Altbestand gilt nicht als scharf ({alt['zustand']})")

        # F7: … wird aber umgezogen, sobald er echte Haken stilllegt
        stiller = os.path.join(drei, ".git", "hooks", "commit-msg")
        os.makedirs(os.path.dirname(stiller), exist_ok=True)
        with open(stiller, "w", encoding="utf-8") as datei:
            datei.write("#!/bin/sh\nexit 0\n")
        os.chmod(stiller, 0o755)
        if "commit-msg" not in befund(drei)["verdeckte_haken"]:
            fehler.append("F7: stillgelegter Haken wird nicht gemeldet")
        umzug, umzug_getan = scharfstellen(drei)
        if umzug["weg"] != "weiterleitung" or hookspath_einstellung(drei):
            fehler.append("F7: Umzug auf die Weiterleitung fand nicht statt")
        if not any("core.hooksPath" in schritt for schritt in umzug_getan):
            fehler.append("F7: Umzug wurde nicht begründet")
        if _commit_versuch(drei, BETRIEBSSPRACHE).returncode == 0:
            fehler.append("F7: nach dem Umzug greift die Sperre nicht")

        # F8: fremdes Hakenwerkzeug im Arbeitsbaum wird nicht angefasst
        vier = os.path.join(basis, "fremde-ablage")
        _wegwerf_repo(vier)
        os.makedirs(os.path.join(vier, ".husky"), exist_ok=True)
        subprocess.run(["git", "-C", vier, "config", "core.hooksPath", ".husky"],
                       check=True, timeout=30)
        fremd, fremd_getan = scharfstellen(vier)
        if fremd["zustand"] != FREMD or fremd_getan:
            fehler.append("F8: fremde Hakenablage wurde angefasst")
        if hookspath_einstellung(vier) != ".husky":
            fehler.append("F8: fremde Einstellung wurde überschrieben")
        if not _reparaturweg(fremd):
            fehler.append("F8: fremde Ablage ohne Reparaturweg gemeldet")

        # F9: kein Git-Arbeitsbaum → gegenstandslos, aber ehrlich
        fuenf = os.path.join(basis, "kein-repo")
        os.makedirs(os.path.join(fuenf, ABLAGE))
        shutil.copyfile(os.path.join(HIER, ABLAGE, HAKEN),
                        os.path.join(fuenf, ABLAGE, HAKEN))
        ohne = befund(fuenf)
        if ohne["zustand"] != KEIN_REPO or ohne["scharf"]:
            fehler.append("F9: fehlendes Repo wird nicht erkannt")

        # F10: fehlende Hakendatei ist DEFEKT, nicht „scharf"
        sechs = os.path.join(basis, "ohne-haken")
        _wegwerf_repo(sechs)
        os.remove(os.path.join(sechs, ABLAGE, HAKEN))
        kaputt, _ = scharfstellen(sechs)
        if kaputt["zustand"] != DEFEKT or kaputt["scharf"]:
            fehler.append(f"F10: fehlender Haken gilt als {kaputt['zustand']}")

        # F11: alter Stand ohne Sperre blockiert nicht (Weiterleitung ins Leere)
        sieben = os.path.join(basis, "alter-stand")
        _wegwerf_repo(sieben, mit_wache=True)
        scharfstellen(sieben)
        os.remove(os.path.join(sieben, ABLAGE, HAKEN))
        frei = _commit_versuch(sieben, BETRIEBSSPRACHE)
        if frei.returncode != 0:
            fehler.append("F11: Weiterleitung bricht, wenn die Sperre fehlt "
                          f"({frei.stdout}{frei.stderr})")

    if fehler:
        for eintrag in fehler:
            print(f"::error::{eintrag}")
        print(f"❌ Selbsttest Haken-Wächter: {len(fehler)} Fehler.")
        return 1
    print("✅ Selbsttest Haken-Wächter: 11 Fallgruppen bestanden "
          "(unscharf erkannt, scharfgestellt und nachgelesen, echter Commit-Versuch "
          "in beide Richtungen, idempotent, fremder Haken bewahrt und weiterhin "
          "wirksam, Altbestand erkannt und bei Stilllegung umgezogen, fremde Ablage "
          "unangetastet, kein Repo erkannt, defekter Haken erkannt, alter Stand "
          "ohne Sperre bleibt arbeitsfähig).")
    return 0


# =====================================================================
#  Hauptlauf
# =====================================================================
def main(argv: list[str] | None = None) -> int:
    zerleger = argparse.ArgumentParser(
        description="Haken-Wächter: Commit-Sperre der Markenfläche scharfstellen")
    zerleger.add_argument("--install", action="store_true",
                          help="scharfstellen (idempotent, mit Nachprüfung)")
    zerleger.add_argument("--check", action="store_true",
                          help="nur prüfen: Exit 1, wenn nicht scharf")
    zerleger.add_argument("--status", action="store_true", help="Zustandsbericht")
    zerleger.add_argument("--leise", action="store_true",
                          help="schweigen, solange alles steht")
    zerleger.add_argument("--json", action="store_true", help="Befund als JSON")
    zerleger.add_argument("--selftest", action="store_true",
                          help="Beweis in Wegwerf-Repos")
    zerleger.add_argument("--wurzel", default=HIER,
                          help="Arbeitskopie (Standard: dieses Repo)")
    args = zerleger.parse_args(argv)

    if args.selftest:
        return selftest()

    getan: list[str] = []
    if args.install:
        zustand, getan = scharfstellen(args.wurzel)
    else:
        zustand = befund(args.wurzel)

    if args.json:
        print(json.dumps({**zustand, "getan": getan}, ensure_ascii=False, indent=2))
    else:
        bericht(zustand, getan, leise=args.leise and not args.status)

    if args.check:
        return 0 if zustand["zustand"] in (SCHARF, NACHGEZOGEN) else 1
    if args.install:
        # „Kein Repo" ist kein Fehler des Nutzers (Export/Tarball, CI-Archiv):
        # `npm install` darf daran nicht scheitern.
        return 0 if zustand["zustand"] in (SCHARF, NACHGEZOGEN, KEIN_REPO) else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
