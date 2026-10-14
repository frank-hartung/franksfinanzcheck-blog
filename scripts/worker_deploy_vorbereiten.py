#!/usr/bin/env python3
# ============================================================
#  WORKER-DEPLOY VORBEREITEN – Sicherheitsaudit 14.10.2026 (M-14)
#
#  Problem: Die produktive Worker-Konfiguration existierte nur im
#  Cloudflare-Dashboard; im Repo standen Platzhalter-IDs. Was live lief,
#  war nicht nachvollziehbar, und `workers_dev = true` veröffentlichte den
#  Newsletter-Worker zusätzlich unter *.workers.dev (ohne Zonen-WAF).
#
#  Lösung: Deploy NUR per CI (.github/workflows/worker-deploy.yml) aus dem
#  Repo. Die Ressourcen-IDs (KV-Namespace, D1-Datenbank) sind keine
#  Geheimnisse und kommen aus Repository-Variablen; dieses Skript setzt sie
#  ein und verweigert den Deploy, wenn
#    · noch ein Platzhalter übrig ist,
#    · eine ID nicht das erwartete Format hat,
#    · `workers_dev = false` fehlt (oder irgendwo `workers_dev = true` steht).
#
#  Aufrufe (CI):
#    --plan                 Liste der deploybereiten Worker → GITHUB_OUTPUT
#                           (EREIGNIS, AUSWAHL, GEAENDERT aus der Umgebung)
#    --pruefen  <worker>    nur prüfen, nichts schreiben (Exit 1 = nicht bereit)
#    --vorbereiten <worker> IDs einsetzen (nur im CI-Arbeitsverzeichnis)
#    --selftest
# ============================================================
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

KV_ID = re.compile(r"^[0-9a-f]{32}$")
D1_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

WORKER: dict[str, dict] = {
    "newsletter-worker": {
        "verzeichnis": "newsletter-worker",
        "ersatz": {"HIER-DIE-ID-NACH-ERSTELLUNG": ("KV_NAMESPACE_ID_ABO", KV_ID)},
        "test": ["node", "--test"],
        "nur_manuell": False,
    },
    "klick-zaehler": {
        "verzeichnis": "cloudflare/klick-zaehler",
        "ersatz": {"EINTRAGEN-NACH-wrangler-d1-create": ("D1_DATABASE_ID_KLICKS", D1_ID)},
        "test": ["node", "--test", "test/worker.test.mjs"],
        "nur_manuell": False,
    },
    # Der KI-Assistent ist bewusst aus (M-04): Deploy nur von Hand ausgelöst.
    "ki-assistent": {
        "verzeichnis": "cloudflare/ki-assistent",
        "ersatz": {},
        "test": ["node", "--test", "test/worker.test.mjs"],
        "nur_manuell": True,
    },
}

PLATZHALTER_RE = re.compile(r"HIER-DIE-ID|EINTRAGEN|PLATZHALTER|<[A-Z_]+>", re.IGNORECASE)
WORKERS_DEV_FALSE = re.compile(r"^\s*workers_dev\s*=\s*false\s*(#.*)?$", re.MULTILINE)
WORKERS_DEV_TRUE = re.compile(r"^\s*workers_dev\s*=\s*true", re.MULTILINE)


def _toml_ohne_kommentare(text: str) -> str:
    return "\n".join(zeile for zeile in text.splitlines() if not zeile.lstrip().startswith("#"))


def pruefe(name: str, umgebung: dict | None = None, root: Path = ROOT) -> tuple[bool, list[str], str]:
    """(bereit, gründe, neuer_text). Schreibt nichts."""
    umgebung = os.environ if umgebung is None else umgebung
    if name not in WORKER:
        return False, [f"unbekannter Worker: {name}"], ""
    cfg = WORKER[name]
    pfad = root / cfg["verzeichnis"] / "wrangler.toml"
    if not pfad.is_file():
        return False, [f"{pfad.relative_to(root)} fehlt"], ""
    text = pfad.read_text(encoding="utf-8")
    gruende: list[str] = []
    for platzhalter, (variable, muster) in cfg["ersatz"].items():
        if platzhalter not in text:
            continue
        wert = (umgebung.get(variable) or "").strip()
        if not wert:
            gruende.append(f"Repository-Variable {variable} fehlt (ersetzt „{platzhalter}“)")
        elif not muster.match(wert):
            gruende.append(f"{variable} hat kein gültiges Format")
        else:
            text = text.replace(platzhalter, wert)
    ohne = _toml_ohne_kommentare(text)
    if not gruende:
        rest = PLATZHALTER_RE.search(ohne)
        if rest:
            gruende.append(f"Platzhalter übrig: „{rest.group(0)}“")
    if not WORKERS_DEV_FALSE.search(ohne):
        gruende.append("workers_dev = false fehlt (Worker wäre unter *.workers.dev erreichbar)")
    if WORKERS_DEV_TRUE.search(ohne):
        gruende.append("workers_dev = true gefunden")
    return (not gruende), gruende, text


def vorbereiten(name: str, umgebung: dict | None = None, root: Path = ROOT) -> int:
    bereit, gruende, text = pruefe(name, umgebung, root)
    if not bereit:
        for g in gruende:
            print(f"::error::{name}: {g}")
        return 1
    pfad = root / WORKER[name]["verzeichnis"] / "wrangler.toml"
    pfad.write_text(text, encoding="utf-8")
    print(f"✅ {name}: Konfiguration vollständig, IDs eingesetzt, workers_dev = false.")
    return 0


def plan(umgebung: dict | None = None, root: Path = ROOT) -> list[str]:
    umgebung = os.environ if umgebung is None else umgebung
    ereignis = umgebung.get("EREIGNIS", "")
    if ereignis == "workflow_dispatch":
        auswahl = (umgebung.get("AUSWAHL") or "").strip()
        kandidaten = [auswahl] if auswahl in WORKER else []
    else:
        geaendert = [z.strip() for z in (umgebung.get("GEAENDERT") or "").splitlines() if z.strip()]
        alle = not geaendert or "*" in geaendert
        kandidaten = []
        for name, cfg in WORKER.items():
            if cfg["nur_manuell"]:
                continue
            praefix = cfg["verzeichnis"].rstrip("/") + "/"
            if alle or any(p.startswith(praefix) for p in geaendert) \
                    or ".github/workflows/worker-deploy.yml" in geaendert:
                kandidaten.append(name)
    bereit = []
    for name in kandidaten:
        ok, gruende, _ = pruefe(name, umgebung, root)
        if ok:
            bereit.append(name)
        else:
            for g in gruende:
                print(f"::notice::{name} wird nicht deployt: {g}")
    return bereit


def _selftest() -> int:
    fehler = []
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        (t / "newsletter-worker").mkdir()
        (t / "newsletter-worker" / "wrangler.toml").write_text(
            'name = "x"\nworkers_dev = false\n[[kv_namespaces]]\nid = "HIER-DIE-ID-NACH-ERSTELLUNG"\n',
            encoding="utf-8")
        ok, gruende, _ = pruefe("newsletter-worker", {}, t)
        if ok or not any("KV_NAMESPACE_ID_ABO" in g for g in gruende):
            fehler.append("fehlende Variable nicht erkannt")
        ok, _, _ = pruefe("newsletter-worker", {"KV_NAMESPACE_ID_ABO": "kaputt"}, t)
        if ok:
            fehler.append("ungültiges ID-Format akzeptiert")
        ok, _, text = pruefe("newsletter-worker", {"KV_NAMESPACE_ID_ABO": "a" * 32}, t)
        if not ok or "a" * 32 not in text:
            fehler.append("gültige ID nicht eingesetzt")
        (t / "newsletter-worker" / "wrangler.toml").write_text(
            'name = "x"\nworkers_dev = true\n', encoding="utf-8")
        ok, _, _ = pruefe("newsletter-worker", {}, t)
        if ok:
            fehler.append("workers_dev = true akzeptiert")
        (t / "newsletter-worker" / "wrangler.toml").write_text(
            'name = "x"\n# workers_dev = false\n', encoding="utf-8")
        ok, _, _ = pruefe("newsletter-worker", {}, t)
        if ok:
            fehler.append("auskommentiertes workers_dev = false akzeptiert")
    if plan({"EREIGNIS": "workflow_dispatch", "AUSWAHL": "gibts-nicht"}) != []:
        fehler.append("unbekannte Auswahl nicht verworfen")
    if "ki-assistent" in plan({"EREIGNIS": "push", "GEAENDERT": "cloudflare/ki-assistent/worker.js"}):
        fehler.append("KI-Assistent bei push deployt (nur manuell erlaubt)")
    if fehler:
        print("❌ WORKER-DEPLOY-SELBSTTEST fehlgeschlagen:")
        for f in fehler:
            print(f"   - {f}")
        return 1
    print("✅ WORKER-DEPLOY-SELBSTTEST bestanden (Variablen, ID-Format, Platzhalter, workers_dev, Plan).")
    return 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return _selftest()
    if "--plan" in argv:
        liste = plan()
        zeile = f"worker={json.dumps(liste)}"
        print(zeile)
        ausgabe = os.environ.get("GITHUB_OUTPUT")
        if ausgabe:
            with open(ausgabe, "a", encoding="utf-8") as f:
                f.write(zeile + "\n")
        return 0
    for schalter, fn in (("--pruefen", None), ("--vorbereiten", vorbereiten)):
        if schalter in argv:
            i = argv.index(schalter)
            if i + 1 >= len(argv):
                print(f"{schalter} braucht einen Worker-Namen", file=sys.stderr)
                return 2
            name = argv[i + 1]
            if fn is None:
                ok, gruende, _ = pruefe(name)
                for g in gruende:
                    print(f"- {g}")
                print(f"{name}: {'bereit' if ok else 'NICHT bereit'}")
                return 0 if ok else 1
            return fn(name)
    print(__doc__ or "Aufruf: --plan | --pruefen <worker> | --vorbereiten <worker> | --selftest")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
