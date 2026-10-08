#!/usr/bin/env python3
# ============================================================
#  MANIFEST-WACHE (Profi-Agentur-Level, WF-7B6B / #654, 08.10.2026)
#  ------------------------------------------------------------
#  ANLASS: Am 08.10.2026 brach der E2E-Lauf auf main im Schritt
#  „Abhängigkeiten installieren“ (`npm ci`) in Sekunde 1 ab (#654).
#  Ursache: Ein Merge (#647, 10:41 UTC) ließ package.json als
#  UNGÜLTIGES JSON zurück – ein fehlendes Komma, zwei Blöcke mit
#  demselben Schlüssel („pagefind“), „lighthouse“ doppelt. Dieselbe
#  Datei brach danach den Produktions-Deploy: Von 10:41 bis 12:50 UTC
#  scheiterte jeder Lauf im Schritt „Suchindex bauen (Pagefind)“ –
#  ohne Livegang. Repariert durch #651 (12:50 UTC).
#
#  Die Meldung zu #654 riet zu API-Keys und GitHub-Ausfall. Die
#  Ursache stand in einer Zeile der Datei. Diese Wache prüft Manifest
#  und Lockfile VOR dem Install und nennt Datei, Zeile und Ursache.
#
#  PRÜFUNGEN (je Verzeichnis: package.json + package-lock.json):
#    K1  KONFLIKTMARKER      <<<<<<< / ======= / >>>>>>> in der Datei:
#                            der Merge ist nicht aufgelöst.
#    J1  JSON-GÜLTIGKEIT     Die Datei ist gültiges JSON – mit Zeile,
#                            Spalte und Ursache in Klartext.
#    J2  DOPPELTER SCHLÜSSEL JSON erlaubt ihn, npm übernimmt still den
#                            LETZTEN Wert. Eine stille Falle.
#    F1  FORM                dependencies/devDependencies/… sind Objekte
#                            aus Name und Text, scripts ebenso.
#    D1  DOPPELT DEKLARIERT  Ein Paket in dependencies UND
#                            devDependencies: WARNUNG (npm toleriert es,
#                            ist aber das typische Merge-Rest-Muster).
#    L1  LOCK-FORMAT         lockfileVersion 2 oder 3, Feld `packages`
#                            und der Wurzel-Eintrag `packages[""]`.
#    L2  WURZEL-SYNC         packages[""] trägt exakt die Deklarationen
#                            des Manifests. Genau daran scheitert `npm ci`
#                            mit „nicht synchron“.
#    L3  LOCK-VOLLSTÄNDIG    Jede deklarierte Abhängigkeit hat einen
#                            Eintrag node_modules/<name> im Lock.
#    L4  PIN-TREUE           Exakt gepinnte Versionen (1.2.3) stimmen mit
#                            dem Lock überein.
#    P1  PAARUNG             Lock ohne Manifest: FEHLER. Manifest ohne
#                            Lock: WARNUNG (npm ci braucht ein Lock).
#
#  GRENZE: Die Wache ersetzt npm nicht. `npm ci` bleibt die letzte
#  Instanz. Sie fängt die Klassen, die Vorfälle verursacht haben, und
#  sagt vorher, woran es liegt. Versions-RANGES (^1.2.3) prüft sie
#  bewusst nicht – das entscheidet npm.
#
#  SABOTAGE-SCHUTZ: `--selftest` baut kaputte Paare im Speicher und
#  verlangt, dass jede Regel genau dort feuert. Eine Gegenprobe
#  (gültiges Paar) muss grün bleiben. Der Vorfall selbst ist als
#  Fixture enthalten: Die Zeile des fehlenden Kommas muss stimmen.
#
#  Aufruf:
#    python3 scripts/manifest_guard.py                 # Arbeitsbaum, Exit 1 bei Befund
#    python3 scripts/manifest_guard.py --selftest      # nur Sabotageproben
#    python3 scripts/manifest_guard.py --ref <sha>     # Stand eines Commits (Vorfall nachspielen)
#    python3 scripts/manifest_guard.py --json          # Maschinenausgabe
#
#  Exit: 0 = grün (Warnungen zulässig) · 1 = Befund (npm ci würde
#        scheitern) · 2 = Werkzeugfehler (Selbsttest rot, Ref unlesbar)
#  In GitHub Actions erscheinen Befunde als Annotation an der Zeile.
#  Runbook: docs/ANLEITUNG-MANIFEST-WACHE.md
# ============================================================

from __future__ import annotations

import json
import os
import posixpath
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

HIER = Path(__file__).resolve().parent
ROOT = HIER.parent

MANIFEST = "package.json"
LOCK = "package-lock.json"
BLOCKE = ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies")
ABHAENGIG_BLOCKE = ("dependencies", "devDependencies", "optionalDependencies")
FEHLER = "FEHLER"
WARNUNG = "WARNUNG"
# Verzeichnisse, die nie Quelle sind (Build-Ausgabe, Abhängigkeiten, Git).
AUSGESCHLOSSEN = {".git", "node_modules", "public", "resources", ".cache", "__pycache__",
                  ".venv", "venv"}
# Begründete Ausnahme: Dieses Manifest hat bewusst KEIN Lockfile und wird in
# keinem Workflow per npm ci installiert (Cloudflare-Worker, Deploy über
# wrangler; geprüft am 08.10.2026). Nur der P1-Hinweis entfällt – jede andere
# Prüfung gilt weiter. Neue Ausnahmen brauchen eine Begründung hier.
OHNE_LOCKFILE_ERLAUBT = {
    "newsletter-worker/package.json":
        "Cloudflare-Worker, kein npm ci in CI (wrangler, geprüft 08.10.2026)",
}
EXAKT = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.\-]+)?(?:\+[0-9A-Za-z.\-]+)?$")
# Git-Konfliktmarker. In gültigem JSON kann keine Zeile so aussehen.
KONFLIKT = re.compile(r"^[ \t]*(<{7}(?: |$)|={7}[ \t]*$|>{7}(?: |$))", re.M)


class WerkzeugFehler(Exception):
    """Die Wache selbst kann nicht arbeiten (Exit 2), nicht das Manifest ist kaputt."""


@dataclass
class Befund:
    code: str
    schwere: str
    datei: str
    text: str
    zeile: int | None = None
    spalte: int | None = None
    hinweis: str = ""


# =====================================================================
#  Einzelprüfungen (rein, ohne Dateisystem – deshalb prüfbar)
# =====================================================================
def _hinweis_json(meldung: str) -> str:
    m = meldung.lower()
    if "expecting ',' delimiter" in m or "illegal trailing comma" in m:
        return ("Fehlendes Komma zwischen zwei Einträgen. Typisch für einen Merge, der zwei "
                "Blöcke nebeneinander legt – `git log -p -- <datei>` zeigt den Moment.")
    if "expecting property name" in m:
        return "Überzähliges Komma vor `}` oder ein Schlüssel ohne Anführungszeichen."
    if "expecting value" in m:
        return "Ein Wert fehlt, z. B. `\"version\": ,`."
    if "expecting ':' delimiter" in m:
        return "Zwischen Schlüssel und Wert fehlt der Doppelpunkt."
    if "extra data" in m:
        return "Text nach dem Ende des JSON – meist ein Merge-Rest hinter der schließenden Klammer."
    if "unterminated string" in m:
        return "Ein Anführungszeichen ist nicht geschlossen."
    return "npm ci bricht bei dieser Datei ab, bevor es Abhängigkeiten prüft."


def _parse_json(text: str, datei: str, befunde: list[Befund]):
    """Parst JSON; meldet J1 (ungültig) und J2 (doppelter Schlüssel). None bei J1."""
    doppelt: list[str] = []

    def hook(paare):
        namen = [k for k, _ in paare]
        for k in namen:
            if namen.count(k) > 1 and k not in doppelt:
                doppelt.append(k)
        return dict(paare)

    try:
        obj = json.loads(text.lstrip("\ufeff"), object_pairs_hook=hook)
    except json.JSONDecodeError as exc:
        befunde.append(Befund(
            "J1", FEHLER, datei,
            f"kein gültiges JSON: {exc.msg}",
            zeile=exc.lineno, spalte=exc.colno, hinweis=_hinweis_json(exc.msg)))
        return None
    zeilen = text.splitlines()
    for k in doppelt:
        muster = re.compile(r'^\s*"' + re.escape(k) + r'"\s*:')
        stellen = [i + 1 for i, z in enumerate(zeilen) if muster.match(z)]
        befunde.append(Befund(
            "J2", FEHLER, datei,
            f"Schlüssel „{k}“ steht mehrfach im selben Objekt (Zeilen "
            f"{', '.join(str(s) for s in stellen)}).",
            zeile=stellen[1] if len(stellen) > 1 else None,
            hinweis="JSON erlaubt das, npm übernimmt still den letzten Wert. "
                    "Einen der Einträge löschen."))
    return obj


def _konflikte(text: str, datei: str, befunde: list[Befund]) -> bool:
    treffer = list(KONFLIKT.finditer(text))
    if not treffer:
        return False
    zeile = text[:treffer[0].start()].count("\n") + 1
    befunde.append(Befund(
        "K1", FEHLER, datei,
        f"Git-Konfliktmarker gefunden ({len(treffer)} Stelle(n)) – der Merge ist nicht aufgelöst.",
        zeile=zeile,
        hinweis="Datei auf einen gültigen Stand bringen, bevor sie committet wird."))
    return True


def _form_manifest(obj: dict, datei: str, befunde: list[Befund]) -> None:
    for block in BLOCKE + ("scripts",):
        if block not in obj:
            continue
        wert = obj[block]
        if not isinstance(wert, dict):
            befunde.append(Befund(
                "F1", FEHLER, datei,
                f"„{block}“ ist kein Objekt, sondern {type(wert).__name__}.",
                hinweis="Erwartet wird ein Objekt aus Name und Text, z. B. "
                        "`\"pagefind\": \"1.5.2\"`."))
            continue
        for name, spec in wert.items():
            if not isinstance(spec, str):
                befunde.append(Befund(
                    "F1", FEHLER, datei,
                    f"„{block}“ → „{name}“ hat keinen Text als Wert ({type(spec).__name__}).",
                    hinweis="Versionsangaben sind Zeichenketten."))


def _doppelt_deklariert(m: dict, datei: str, befunde: list[Befund]) -> None:
    deps = m.get("dependencies") if isinstance(m.get("dependencies"), dict) else {}
    dev = m.get("devDependencies") if isinstance(m.get("devDependencies"), dict) else {}
    for name in sorted(set(deps) & set(dev)):
        befunde.append(Befund(
            "D1", WARNUNG, datei,
            f"„{name}“ steht in dependencies UND devDependencies.",
            hinweis="npm toleriert das, es ist aber das typische Merge-Rest-Muster. "
                    "Eine Stelle löschen."))


def _lock_format(lock: dict, datei: str, befunde: list[Befund]) -> bool:
    version = lock.get("lockfileVersion")
    pakete = lock.get("packages")
    if version not in (2, 3) or not isinstance(pakete, dict):
        befunde.append(Befund(
            "L1", FEHLER, datei,
            f"Lockfile-Format nicht unterstützt (lockfileVersion {version!r}, "
            f"packages {'vorhanden' if isinstance(pakete, dict) else 'fehlt'}).",
            hinweis="Mit npm 10 neu erzeugen: `npm install --package-lock-only --ignore-scripts`."))
        return False
    if not isinstance(pakete.get(""), dict):
        befunde.append(Befund(
            "L1", FEHLER, datei,
            "Lockfile ohne Wurzel-Eintrag packages[\"\"].",
            hinweis="Mit npm 10 neu erzeugen: `npm install --package-lock-only --ignore-scripts`."))
        return False
    return True


def _wurzel_sync(m: dict, lock: dict, datei_m: str, datei_l: str, befunde: list[Befund]) -> None:
    wurzel = lock["packages"][""]
    for block in BLOCKE:
        mb = m.get(block, {})
        lb = wurzel.get(block, {})
        if not isinstance(mb, dict) or not isinstance(lb, dict):
            continue  # F1 hat den Befund schon; hier nicht doppeln
        nur_m = sorted(k for k in mb if k not in lb)
        nur_l = sorted(k for k in lb if k not in mb)
        abw = sorted(k for k in mb if k in lb and str(mb[k]) != str(lb[k]))
        teile = []
        if nur_m:
            teile.append("nur im Manifest: " + ", ".join(f"{k}@{mb[k]}" for k in nur_m))
        if nur_l:
            teile.append("nur im Lock: " + ", ".join(f"{k}@{lb[k]}" for k in nur_l))
        if abw:
            teile.append("abweichend: " + ", ".join(
                f"{k} (Manifest {mb[k]}, Lock {lb[k]})" for k in abw))
        if teile:
            befunde.append(Befund(
                "L2", FEHLER, datei_l,
                f"Lock und Manifest nicht synchron – {block}: " + "; ".join(teile) + ".",
                hinweis="`npm install --package-lock-only --ignore-scripts` ausführen und "
                        "package.json UND package-lock.json gemeinsam committen."))


def _lock_vollstaendig(m: dict, lock: dict, datei_l: str, befunde: list[Befund]) -> None:
    pakete = lock["packages"]
    for block in ABHAENGIG_BLOCKE:
        if not isinstance(m.get(block), dict):
            continue
        for name, spec in m[block].items():
            eintrag = pakete.get(f"node_modules/{name}")
            if not isinstance(eintrag, dict):
                befunde.append(Befund(
                    "L3", FEHLER, datei_l,
                    f"„{name}“ ({block}, {spec}) fehlt im Lock – npm ci bricht ab.",
                    hinweis="Lock neu erzeugen, siehe L2."))
                continue
            if isinstance(spec, str) and EXAKT.match(spec):
                ist = eintrag.get("version")
                if ist != spec:
                    befunde.append(Befund(
                        "L4", FEHLER, datei_l,
                        f"„{name}“ ist exakt auf {spec} gepinnt, der Lock hat {ist}.",
                        hinweis="Lock neu erzeugen, siehe L2. Den Pin nicht im Lock ändern."))


def _als_text(wert, datei: str, befunde: list[Befund]) -> str | None:
    """Bytes = keine UTF-8-Datei: das ist selbst ein Befund (J1), kein Absturz."""
    if wert is None or isinstance(wert, str):
        return wert
    befunde.append(Befund("J1", FEHLER, datei,
                          "Datei ist kein UTF-8-Text und kann nicht gelesen werden.",
                          hinweis="Datei als reinen UTF-8-Text speichern."))
    return None


def pruefe_manifeste(dateien: dict[str, "str | bytes"]) -> list[Befund]:
    """Prüft alle package.json/package-lock.json-Paare. Schlüssel = relativer Pfad."""
    befunde: list[Befund] = []
    verzeichnisse = sorted({posixpath.dirname(p) for p in dateien})
    for verz in verzeichnisse:
        pfad_m = posixpath.join(verz, MANIFEST) if verz else MANIFEST
        pfad_l = posixpath.join(verz, LOCK) if verz else LOCK
        txt_m = _als_text(dateien.get(pfad_m), pfad_m, befunde)
        txt_l = _als_text(dateien.get(pfad_l), pfad_l, befunde)
        if pfad_m not in dateien and pfad_l in dateien:
            befunde.append(Befund(
                "P1", FEHLER, pfad_l,
                "package-lock.json ohne package.json – ein Merge hat das Manifest entfernt.",
                hinweis="Manifest aus der letzten guten Fassung wiederherstellen."))
        if pfad_m in dateien and pfad_l not in dateien and pfad_m not in OHNE_LOCKFILE_ERLAUBT:
            befunde.append(Befund(
                "P1", WARNUNG, pfad_m,
                "Kein package-lock.json neben dem Manifest. npm ci braucht ein Lockfile.",
                hinweis="Nur harmlos, wenn dieses Verzeichnis nie per npm ci installiert wird."))
        # Konflikte und JSON zuerst – alles Weitere braucht gültiges JSON.
        m = l = None
        if txt_m is not None and not _konflikte(txt_m, pfad_m, befunde):
            m = _parse_json(txt_m, pfad_m, befunde)
        if txt_l is not None and not _konflikte(txt_l, pfad_l, befunde):
            l = _parse_json(txt_l, pfad_l, befunde)
        if m is not None and not isinstance(m, dict):
            befunde.append(Befund("F1", FEHLER, pfad_m, "package.json ist kein JSON-Objekt.",
                                  hinweis="Die Datei muss mit `{` beginnen und enden."))
            m = None
        if l is not None and not isinstance(l, dict):
            befunde.append(Befund("L1", FEHLER, pfad_l, "package-lock.json ist kein JSON-Objekt.",
                                  hinweis="Mit npm 10 neu erzeugen: `npm install --package-lock-only`."))
            l = None
        if m is not None:
            _form_manifest(m, pfad_m, befunde)
            _doppelt_deklariert(m, pfad_m, befunde)
        if l is not None and _lock_format(l, pfad_l, befunde) and m is not None:
            _wurzel_sync(m, l, pfad_m, pfad_l, befunde)
            _lock_vollstaendig(m, l, pfad_l, befunde)
    return befunde


def gruen(befunde: list[Befund]) -> bool:
    return not any(b.schwere == FEHLER for b in befunde)


# =====================================================================
#  Quellen: Arbeitsbaum oder ein Commit (`--ref`)
# =====================================================================
def _lesen(blob: bytes):
    try:
        return blob.decode("utf-8")
    except UnicodeDecodeError:
        return blob  # bleibt Bytes -> J1 in pruefe_manifeste


def dateien_aus_baum(root: Path) -> dict[str, "str | bytes"]:
    """Liest alle package.json/package-lock.json (Arbeitsbaum, ohne Build-Ausgabe)."""
    gefunden: dict[str, "str | bytes"] = {}
    for verz, unterverz, namen in os.walk(root):
        unterverz[:] = [d for d in unterverz if d not in AUSGESCHLOSSEN]
        for name in (MANIFEST, LOCK):
            if name in namen:
                pfad = Path(verz) / name
                rel = pfad.relative_to(root).as_posix()
                gefunden[rel] = _lesen(pfad.read_bytes())
    return gefunden


def dateien_aus_ref(root: Path, ref: str) -> dict[str, "str | bytes"]:
    """Liest dieselben Dateien aus einem Commit – für die Nachspielprobe des Vorfalls."""
    try:
        liste = subprocess.run(["git", "-C", str(root), "ls-tree", "-r", "--name-only", ref],
                               capture_output=True, text=True, check=True).stdout.splitlines()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise WerkzeugFehler(f"Ref „{ref}“ nicht lesbar: {exc}") from exc
    gefunden: dict[str, "str | bytes"] = {}
    for rel in liste:
        if posixpath.basename(rel) not in (MANIFEST, LOCK):
            continue
        if any(teil in AUSGESCHLOSSEN for teil in rel.split("/")):
            continue
        blob = subprocess.run(["git", "-C", str(root), "show", f"{ref}:{rel}"],
                              capture_output=True, check=True).stdout
        gefunden[rel] = _lesen(blob)
    return gefunden


# =====================================================================
#  Bericht
# =====================================================================
def _ort(b: Befund) -> str:
    if b.zeile is None:
        return b.datei
    return f"{b.datei} Zeile {b.zeile}" + (f", Spalte {b.spalte}" if b.spalte else "")


def bericht(befunde: list[Befund], quelle: str, dateien: dict) -> str:
    zeilen = [f"🔎 MANIFEST-WACHE · {len(dateien)} Datei(en) · Quelle: {quelle}"]
    if not dateien:
        zeilen.append("  (keine package.json / package-lock.json gefunden)")
    for b in befunde:
        symbol = "❌" if b.schwere == FEHLER else "⚠️ "
        zeilen.append(f"  {symbol} {b.schwere} [{b.code}] {_ort(b)}: {b.text}")
        if b.hinweis:
            zeilen.append(f"        → {b.hinweis}")
    fehler = sum(1 for b in befunde if b.schwere == FEHLER)
    warn = len(befunde) - fehler
    if fehler:
        zeilen.append(f"ERGEBNIS: ROT – {fehler} Befund(e), {warn} Warnung(en). "
                      "npm ci würde hier abbrechen (Exit 1).")
    else:
        zeilen.append(f"ERGEBNIS: GRÜN – keine Befunde, {warn} Warnung(en).")
    return "\n".join(zeilen)


def _annotationen(befunde: list[Befund]) -> None:
    """GitHub-Annotationen: der Befund erscheint an der Zeile im PR."""
    for b in befunde:
        stufe = "error" if b.schwere == FEHLER else "warning"
        ort = f"file={b.datei}"
        if b.zeile:
            ort += f",line={b.zeile}"
        if b.spalte:
            ort += f",col={b.spalte}"
        titel = f"Manifest-Wache {b.code}"
        nachricht = b.text + (f" → {b.hinweis}" if b.hinweis else "")
        print(f"::{stufe} {ort},title={titel}::{nachricht}")


# =====================================================================
#  Selbsttest: die Wache beweist sich vor jeder Aussage
# =====================================================================
GUT_MANIFEST = """{
  "name": "fixture-e2e",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "test": "node --test"
  },
  "devDependencies": {
    "@playwright/test": "1.63.0",
    "jsdom": "^30.1.2"
  },
  "dependencies": {
    "pagefind": "1.5.2"
  }
}
"""


def _lock_text(root_extra_dev: dict | None = None, ohne: tuple = (),
               aendern: dict | None = None, wurzel_umbenennen: bool = False,
               version: int = 3) -> str:
    """Erzeugt ein Lock-Fixture; Schalter sabotieren genau eine Stelle."""
    daten = {
        "name": "fixture-e2e", "version": "1.0.0", "lockfileVersion": version,
        "requires": True,
        "packages": {
            "": {"name": "fixture-e2e", "version": "1.0.0",
                 "dependencies": {"pagefind": "1.5.2"},
                 "devDependencies": {"@playwright/test": "1.63.0", "jsdom": "^30.1.2"}},
            "node_modules/@playwright/test": {"version": "1.63.0", "dev": True},
            "node_modules/jsdom": {"version": "30.1.2", "dev": True},
            "node_modules/pagefind": {"version": "1.5.2"},
        },
    }
    if root_extra_dev:
        daten["packages"][""]["devDependencies"].update(root_extra_dev)
    for pfad in ohne:
        daten["packages"].pop(pfad, None)
    for pfad, wert in (aendern or {}).items():
        daten["packages"][pfad] = wert
    if wurzel_umbenennen:
        daten["packages"]["x-entfernt"] = daten["packages"].pop("")
    return json.dumps(daten, indent=2) + "\n"


GUT_LOCK = _lock_text()

# Der Vorfall vom 08.10.2026 (#654), auf die Kernstelle verkürzt: zwei
# Blöcke ohne Komma, doppelter Schlüssel „pagefind“, „lighthouse“ doppelt.
VORFALL_MANIFEST = """{
  "name": "fixture-e2e",
  "version": "1.0.0",
  "private": true,
  "devDependencies": {
    "@playwright/test": "1.63.0",
    "jsdom": "^30.1.2",
    "lighthouse": "13.5.0"
  },
  "dependencies": {
    "pagefind": "1.5.2"
    "lighthouse": "13.5.0",
    "pagefind": "^1.5.2"
  }
}
"""


def _zeile_des_befunds() -> int:
    """Die Zeile, an der Python im Vorfall-Fixture bricht: das `"lighthouse"` nach dem fehlenden Komma."""
    zeilen = VORFALL_MANIFEST.splitlines()
    treffer = [i for i, z in enumerate(zeilen, start=1) if z.strip() == '"lighthouse": "13.5.0",']
    if len(treffer) != 1:
        raise AssertionError("Vorfall-Fixture: Kernzeile nicht eindeutig")
    return treffer[0]


def _probe_werte() -> list[dict]:
    """Jede Probe: Eingabe, erwartete FEHLER-/WARNUNG-Codes, optional Befundzeile.

    `rein=False` markiert Proben, deren Folgebefunde (z. B. L2 nach einer
    geänderten Manifest-Zeile) zwangsläufig sind. Nur sie dürfen mehr Codes
    tragen als erwartet; alle anderen müssen exakt ihren Befund zeigen.
    """
    return [
        {"name": "gegenprobe-gueltig",
         "dateien": {MANIFEST: GUT_MANIFEST, LOCK: GUT_LOCK},
         "erwartet": set(), "warnung": set()},
        {"name": "vorfall-08.10.2026-fehlendes-komma",
         "dateien": {MANIFEST: VORFALL_MANIFEST, LOCK: GUT_LOCK},
         "erwartet": {"J1"}, "warnung": set(), "zeile": _zeile_des_befunds()},
        {"name": "konfliktmarker-im-manifest",
         "dateien": {MANIFEST: GUT_MANIFEST.replace(
             '    "pagefind": "1.5.2"',
             '<<<<<<< HEAD\n    "pagefind": "1.5.2"\n=======\n    "pagefind": "1.5.3"\n>>>>>>> main'),
             LOCK: GUT_LOCK},
         "erwartet": {"K1"}, "warnung": set()},
        {"name": "konfliktmarker-im-lock",
         "dateien": {MANIFEST: GUT_MANIFEST, LOCK: "<<<<<<< HEAD\n" + GUT_LOCK},
         "erwartet": {"K1"}, "warnung": set()},
        {"name": "doppelter-schluessel-gueltiges-json",
         "dateien": {MANIFEST: GUT_MANIFEST.replace(
             '"pagefind": "1.5.2"', '"pagefind": "1.5.2",\n    "pagefind": "1.5.3"'),
             LOCK: GUT_LOCK},
         "erwartet": {"J2"}, "warnung": set(), "rein": False},
        {"name": "form-block-ist-liste",
         "dateien": {MANIFEST: GUT_MANIFEST.replace(
             '"dependencies": {\n    "pagefind": "1.5.2"\n  }', '"dependencies": ["pagefind"]'),
             LOCK: GUT_LOCK},
         "erwartet": {"F1"}, "warnung": set()},
        {"name": "form-version-ist-zahl",
         "dateien": {MANIFEST: GUT_MANIFEST.replace('"pagefind": "1.5.2"', '"pagefind": 152'),
                     LOCK: GUT_LOCK},
         "erwartet": {"F1"}, "warnung": set(), "rein": False},
        {"name": "paket-in-beiden-bloecken-ist-warnung",
         "dateien": {MANIFEST: GUT_MANIFEST.replace(
             '"devDependencies": {\n    "@playwright/test": "1.63.0",',
             '"devDependencies": {\n    "pagefind": "1.5.2",\n    "@playwright/test": "1.63.0",'),
             LOCK: _lock_text(root_extra_dev={"pagefind": "1.5.2"})},
         "erwartet": set(), "warnung": {"D1"}},
        {"name": "lock-ist-kein-json",
         "dateien": {MANIFEST: GUT_MANIFEST, LOCK: GUT_LOCK[:-40]},
         "erwartet": {"J1"}, "warnung": set()},
        {"name": "lock-version-1-nicht-unterstuetzt",
         "dateien": {MANIFEST: GUT_MANIFEST, LOCK: _lock_text(version=1)},
         "erwartet": {"L1"}, "warnung": set()},
        {"name": "lock-ohne-wurzel-eintrag",
         "dateien": {MANIFEST: GUT_MANIFEST, LOCK: _lock_text(wurzel_umbenennen=True)},
         "erwartet": {"L1"}, "warnung": set()},
        {"name": "wurzel-nicht-synchron-neue-abhaengigkeit",
         "dateien": {MANIFEST: GUT_MANIFEST.replace(
             '"pagefind": "1.5.2"\n  }', '"pagefind": "1.5.2",\n    "left-pad": "1.3.0"\n  }'),
             LOCK: GUT_LOCK},
         "erwartet": {"L2", "L3"}, "warnung": set(), "rein": False},
        {"name": "wurzel-nicht-synchron-abweichende-version",
         "dateien": {MANIFEST: GUT_MANIFEST.replace('"jsdom": "^30.1.2"', '"jsdom": "^31.0.0"'),
                     LOCK: GUT_LOCK},
         "erwartet": {"L2"}, "warnung": set()},
        {"name": "lock-fehlt-paket",
         "dateien": {MANIFEST: GUT_MANIFEST,
                     LOCK: _lock_text(ohne=("node_modules/jsdom",))},
         "erwartet": {"L3"}, "warnung": set()},
        {"name": "exakter-pin-stimmt-nicht",
         "dateien": {MANIFEST: GUT_MANIFEST,
                     LOCK: _lock_text(aendern={"node_modules/pagefind": {"version": "1.5.1"}})},
         "erwartet": {"L4"}, "warnung": set()},
        {"name": "lock-ohne-manifest",
         "dateien": {LOCK: GUT_LOCK},
         "erwartet": {"P1"}, "warnung": set()},
        {"name": "manifest-ohne-lock-ist-warnung",
         "dateien": {MANIFEST: GUT_MANIFEST},
         "erwartet": set(), "warnung": {"P1"}},
        {"name": "ausnahme-ohne-lock-gilt-nur-fuer-den-pfad",
         "dateien": {"newsletter-worker/" + MANIFEST: GUT_MANIFEST},
         "erwartet": set(), "warnung": set()},
        {"name": "ausnahme-ist-eng-anderer-pfad-bleibt-warnung",
         "dateien": {"tools/x/" + MANIFEST: GUT_MANIFEST},
         "erwartet": set(), "warnung": {"P1"}},
    ]


def selftest() -> list[str]:
    """Liefert Fehlertexte; leere Liste = die Wache hat alle Proben gefangen."""
    fehler: list[str] = []
    for probe in _probe_werte():
        befunde = pruefe_manifeste(probe["dateien"])
        fehler_codes = {b.code for b in befunde if b.schwere == FEHLER}
        warn_codes = {b.code for b in befunde if b.schwere == WARNUNG}
        name = probe["name"]
        if not probe["erwartet"] and not probe["warnung"]:
            if befunde:
                fehler.append(f"{name}: Gegenprobe ist nicht grün – "
                              + "; ".join(f"{b.code} {b.text}" for b in befunde))
            continue
        if not probe["erwartet"] <= fehler_codes:
            fehler.append(f"{name}: erwartet FEHLER {sorted(probe['erwartet'])}, "
                          f"gefunden {sorted(fehler_codes)} – die Regel feuert nicht.")
        if not probe["warnung"] <= warn_codes:
            fehler.append(f"{name}: erwartet WARNUNG {sorted(probe['warnung'])}, "
                          f"gefunden {sorted(warn_codes)}.")
        if probe.get("rein", True) and probe["erwartet"] and not fehler_codes <= probe["erwartet"]:
            fehler.append(f"{name}: unerwartete FEHLER {sorted(fehler_codes - probe['erwartet'])} "
                          "– die Probe ist nicht sauber sabotiert.")
        if "zeile" in probe:
            gemeldet = [b.zeile for b in befunde if b.code == "J1"]
            if probe["zeile"] not in gemeldet:
                fehler.append(f"{name}: erwartet J1 in Zeile {probe['zeile']}, "
                              f"gemeldet {gemeldet}.")
    vorfall = [b for b in pruefe_manifeste({MANIFEST: VORFALL_MANIFEST, LOCK: GUT_LOCK})
               if b.code == "J1"]
    if not any("Komma" in b.hinweis for b in vorfall):
        fehler.append("vorfall: J1 ohne Ursachen-Hinweis zum fehlenden Komma.")
    return fehler


# =====================================================================
#  Lauf
# =====================================================================
def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in args:
        fehler = selftest()
        if fehler:
            print("🛑 MANIFEST-WACHE: Selbsttest ROT – die Wache misst nicht zuverlässig.")
            for f in fehler:
                print("   - " + f)
            return 2
        print(f"✅ MANIFEST-WACHE: Selbsttest grün – {len(_probe_werte())} Proben "
              "(Sabotage + Gegenprobe) gefangen.")
        return 0
    try:
        if "--ref" in args:
            ref = args[args.index("--ref") + 1]
            quelle = f"Commit {ref}"
            dateien = dateien_aus_ref(ROOT, ref)
        else:
            quelle = "Arbeitsbaum"
            dateien = dateien_aus_baum(ROOT)
    except (WerkzeugFehler, IndexError) as exc:
        print(f"🛑 MANIFEST-WACHE: Werkzeugfehler – {exc}", file=sys.stderr)
        return 2
    befunde = pruefe_manifeste(dateien)
    if "--json" in args:
        print(json.dumps({"quelle": quelle, "gruen": gruen(befunde),
                          "befunde": [asdict(b) for b in befunde]},
                         ensure_ascii=False, indent=2))
    else:
        print(bericht(befunde, quelle, dateien))
    if os.environ.get("GITHUB_ACTIONS") == "true":
        _annotationen(befunde)
    return 0 if gruen(befunde) else 1


if __name__ == "__main__":
    sys.exit(main())
