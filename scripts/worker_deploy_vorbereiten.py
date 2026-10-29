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
#  Geheimnisse und kommen aus Repository-Variablen ODER werden erst im
#  freigabepflichtigen Deploy-Job durch worker_ressourcen.py aus der
#  bestehenden Produktionsbindung aufgelöst; dieses Skript setzt sie
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
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

KV_ID = re.compile(r"^[0-9a-f]{32}$")
D1_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
BUILD_RE = re.compile(r'^BUILD\s*=\s*"([^"]+)"', re.MULTILINE)
NEWSLETTER_HEALTHZ = "https://abos.franksfinanzcheck.de/healthz"
NACHWEIS_PAUSEN = (2.0, 5.0, 10.0)

WORKER: dict[str, dict] = {
    "newsletter-worker": {
        "verzeichnis": "newsletter-worker",
        "ersatz": {"HIER-DIE-ID-NACH-ERSTELLUNG": ("KV_NAMESPACE_ID_ABO", KV_ID)},
        "test": ["node", "--test"],
        "nur_manuell": False,
    },
    "klick-zaehler": {
        "verzeichnis": "cloudflare/klick-zaehler",
        "ersatz": {"EINTRAGEN-NACH-wrangler-d1-create": ("D1_DATABASE_ID", D1_ID)},
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

# Änderungen an der Deploy-Kette selbst müssen beide automatischen Worker
# erneut ausrollen. Nur so bleibt der produktive Stand nachweisbar derselbe,
# dessen Vorbereitung und Ressourcen-Auflösung gerade geändert wurde.
DEPLOY_DATEIEN = {
    ".github/workflows/worker-deploy.yml",
    "scripts/worker_deploy_vorbereiten.py",
    "scripts/worker_ressourcen.py",
    "scripts/worker_environment_guard.py",
}

# Nur für die REINE Strukturprüfung im Planungs-Job. Diese Werte verlassen
# `pruefe()` nicht und werden niemals geschrieben oder deployt. Die echten IDs
# löst worker_ressourcen.py erst nach der Environment-Freigabe auf.
PLAN_IDS = {
    "KV_NAMESPACE_ID_ABO": "0" * 32,
    "D1_DATABASE_ID": "00000000-0000-0000-0000-000000000000",
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


def plan_auswerten(
    umgebung: dict | None = None, root: Path = ROOT
) -> tuple[int, list[str], list[str], str]:
    """Plant Auswahl und Quellstruktur, niemals das Schicksal produktiver Daten.

    Rückgabe: (exit_code, bereit_liste, annotationen, step_summary_markdown).
    Der Planungs-Job läuft bewusst ohne Environment und ohne Cloudflare-
    Zugang. Deshalb prüft er hier nur Worker-Auswahl und statische Konfiguration.
    Die echte KV-/D1-ID wird später im freigabepflichtigen Deploy-Job aus einer
    Repository-Variable ODER der bereits produktiven Worker-Bindung aufgelöst.
    Fehlt beides oder ist die Bindung uneindeutig, bricht DER DEPLOY rot ab –
    niemals wird der Worker still aus der Matrix weggelassen (WF-E813/#815).
    """
    umgebung = os.environ if umgebung is None else umgebung
    ereignis = (umgebung.get("EREIGNIS") or "").strip()
    manuell = ereignis == "workflow_dispatch"
    annotationen: list[str] = []
    zeilen = ["## Worker-Deploy-Plan", ""]

    if manuell:
        ref = (umgebung.get("REF") or "").strip()
        if ref != "refs/heads/main":
            msg = ("Manueller Worker-Deploy ist ausschließlich auf `refs/heads/main` erlaubt; "
                   "kein Produktions-Environment wird angefordert.")
            annotationen.append(f"::error::{msg}")
            zeilen.append(f"- ❌ {msg}")
            return 1, [], annotationen, "\n".join(zeilen)
        auswahl = (umgebung.get("AUSWAHL") or "").strip()
        if auswahl not in WORKER:
            msg = f"Unbekannter Worker für manuellen Deploy: „{auswahl or '(leer)'}“."
            annotationen.append(f"::error::{msg}")
            zeilen.append(f"- ❌ {msg}")
            return 1, [], annotationen, "\n".join(zeilen)
        kandidaten = [auswahl]
    else:
        geaendert = [z.strip() for z in (umgebung.get("GEAENDERT") or "").splitlines() if z.strip()]
        alle = not geaendert or "*" in geaendert
        kandidaten = []
        for name, cfg in WORKER.items():
            if cfg["nur_manuell"]:
                continue
            praefix = cfg["verzeichnis"].rstrip("/") + "/"
            if (alle or any(p.startswith(praefix) for p in geaendert)
                    or any(p in DEPLOY_DATEIEN for p in geaendert)):
                kandidaten.append(name)

    if not kandidaten:
        zeilen.append("Keine geänderten Worker-Pfade in diesem Lauf – kein Deploy erforderlich.")
        return 0, [], annotationen, "\n".join(zeilen)

    bereit: list[str] = []
    blockiert: list[tuple[str, list[str]]] = []
    for name in kandidaten:
        # Ressourcen-IDs gehören nicht in diesen zugangslosen Planungs-Job.
        # Gültige Attrappen lassen `pruefe()` ausschließlich die übrige
        # Struktur prüfen; `pruefe()` schreibt nachweislich nichts.
        struktur_umgebung = dict(umgebung)
        for variable, _muster in WORKER[name]["ersatz"].values():
            struktur_umgebung[variable] = PLAN_IDS[variable]
        ok, gruende, _ = pruefe(name, struktur_umgebung, root)
        if ok:
            bereit.append(name)
            zeilen.append(
                f"- ✅ **{name}**: Deploy vorgemerkt; Ressource wird nach Freigabe in "
                "`cloudflare-produktion` aus Variable oder bestehender Produktions-Bindung aufgelöst."
            )
        else:
            blockiert.append((name, gruende))
            for grund in gruende:
                annotationen.append(f"::error::{name}: Ungültige Deploy-Konfiguration: {grund}.")
            zeilen.append(f"- ❌ **{name}**: **NICHT deployfähig** – " + "; ".join(gruende) + ".")

    if blockiert:
        zeilen += [
            "",
            "### Fail-closed statt Schein-Grün",
            "Die fehlerhafte Quellkonfiguration muss behoben werden. Der Deploy wird nicht "
            "übersprungen und als Erfolg dargestellt. Runbook: "
            "`docs/SICHERHEIT-BETRIEB-RUNBOOK.md`, Abschnitt D2.",
        ]
        return 1, [], annotationen, "\n".join(zeilen)

    zeilen += [
        "",
        "**Datensicherheit:** Der Deploy liest fehlende IDs ausschließlich aus der "
        "bereits gebundenen Produktionsressource. Er legt keinen Ersatzspeicher an "
        "und bricht bei fehlender oder mehrdeutiger Bindung ab.",
    ]
    return 0, bereit, annotationen, "\n".join(zeilen)


def plan(umgebung: dict | None = None, root: Path = ROOT) -> list[str]:
    """Reine Planungsfunktion ohne GitHub-Workflow-Kommando-Seiteneffekte (sicher in Tests/Selftests)."""
    _, bereit, _, _ = plan_auswerten(umgebung, root)
    return bereit


class _KeineWeiterleitung(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise OSError(f"Unerwartete Weiterleitung HTTP {code}")


def _hole_oeffentlichen_bau(url: str = NEWSLETTER_HEALTHZ, timeout: float = 10.0) -> str:
    anfrage = urllib.request.Request(url, headers={
        "accept": "application/json",
        "user-agent": "franksfinanzcheck-worker-deploy-nachweis/1.0",
    })
    opener = urllib.request.build_opener(_KeineWeiterleitung())
    try:
        antwort = opener.open(anfrage, timeout=timeout)
    except urllib.error.HTTPError as fehler:
        if fehler.code != 503:
            fehler.close()
            raise OSError(f"HTTP {fehler.code}") from None
        antwort = fehler
    with antwort:
        daten = json.loads(antwort.read(65_536).decode("utf-8"))
    if not isinstance(daten, dict):
        raise ValueError("Kein JSON-Objekt")
    bau = daten.get("bau")
    return bau.strip() if isinstance(bau, str) else ""


def deploy_nachweis(
    name: str,
    *,
    root: Path = ROOT,
    holen=_hole_oeffentlichen_bau,
    pausen: tuple[float, ...] = NACHWEIS_PAUSEN,
    schlaf=time.sleep,
) -> tuple[int, str]:
    """Prüft nach `wrangler deploy`, dass der neue Build-Stempel live auf /healthz antwortet."""
    if name not in WORKER:
        return 1, f"Unbekannter Worker: {name}"
    if name != "newsletter-worker":
        return 0, f"ℹ️ {name}: kein öffentlicher /healthz-Build-Stempel vorgesehen."
    wrangler = (root / WORKER[name]["verzeichnis"] / "wrangler.toml").read_text(encoding="utf-8")
    treffer = BUILD_RE.search(_toml_ohne_kommentare(wrangler))
    soll = treffer.group(1).strip() if treffer else ""
    if not soll:
        return 1, "BUILD fehlt in newsletter-worker/wrangler.toml – kein Deploy-Nachweis möglich."
    letzter_grund = "keine Antwort"
    for nr in range(len(pausen) + 1):
        if nr:
            schlaf(pausen[nr - 1])
        try:
            ist = holen()
        except (OSError, ValueError) as fehler:
            letzter_grund = f"Netz-/Formatfehler ({type(fehler).__name__})"
            continue
        if ist == soll:
            return 0, (f"✅ Live-Deploy-Nachweis erbracht: `/healthz` meldet Build `{soll}` "
                       f"(Versuch {nr + 1}).")
        letzter_grund = "Build-Stempel noch alt oder leer"
    return 1, (f"Live-Deploy-Nachweis fehlgeschlagen: `/healthz` liefert nach "
               f"{len(pausen) + 1} Versuchen nicht den erwarteten Build `{soll}` "
               f"({letzter_grund}). Custom-Domain/Route in Cloudflare prüfen.")


def _selftest() -> int:
    fehler = []
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        (t / "newsletter-worker").mkdir()
        (t / "newsletter-worker" / "wrangler.toml").write_text(
            'name = "x"\nworkers_dev = false\nBUILD = "ff-test-1"\n[[kv_namespaces]]\nid = "HIER-DIE-ID-NACH-ERSTELLUNG"\n',
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
        # WF-E813 / #815, zweite Stufe: Eine fehlende kopierte Variable darf
        # den vorhandenen Produktions-Worker nicht mehr aus der Matrix lassen.
        code_manuell, bereit_m, _, summary_m = plan_auswerten(
            {"EREIGNIS": "workflow_dispatch", "AUSWAHL": "newsletter-worker",
             "REF": "refs/heads/main"}, t)
        if (code_manuell != 0 or bereit_m != ["newsletter-worker"]
                or "bestehender Produktions-Bindung" not in summary_m):
            fehler.append("manueller Deploy auf main ohne Variable wurde weiterhin übersprungen")
        code_fremd, bereit_fremd, ann_fremd, _ = plan_auswerten(
            {"EREIGNIS": "workflow_dispatch", "AUSWAHL": "newsletter-worker",
             "REF": "refs/heads/arena/test"}, t)
        if code_fremd != 1 or bereit_fremd or not any("ausschließlich" in a for a in ann_fremd):
            fehler.append("manueller Deploy auf Nicht-main wurde nicht vor dem Environment abgewiesen")
        code_push, bereit_p, _, summary_p = plan_auswerten(
            {"EREIGNIS": "push", "GEAENDERT": "newsletter-worker/src/index.js"}, t)
        if code_push != 0 or bereit_p != ["newsletter-worker"] or "keinen Ersatzspeicher" not in summary_p:
            fehler.append("Push-Plan ohne Variable ließ den Produktions-Deploy weiterhin aus")
        # Live-Deploy-Nachweis: verzögerte Edge-Propagation heilt, falscher Stempel scheitert.
        antworten = iter(["alt", "ff-test-1"])
        code_nw, _ = deploy_nachweis(
            "newsletter-worker", root=t, holen=lambda: next(antworten),
            pausen=(0.0, 0.0), schlaf=lambda _: None)
        if code_nw != 0:
            fehler.append("Deploy-Nachweis trotz passendem Stempel im 2. Versuch gescheitert")
        code_alt, _ = deploy_nachweis(
            "newsletter-worker", root=t, holen=lambda: "veraltet",
            pausen=(0.0,), schlaf=lambda _: None)
        if code_alt != 1:
            fehler.append("Deploy-Nachweis akzeptierte veralteten Stempel")
        (t / "newsletter-worker" / "wrangler.toml").write_text(
            'name = "x"\nworkers_dev = true\n', encoding="utf-8")
        ok, _, _ = pruefe("newsletter-worker", {}, t)
        if ok:
            fehler.append("workers_dev = true akzeptiert")
        code_defekt, bereit_defekt, annotationen_defekt, _ = plan_auswerten(
            {"EREIGNIS": "push", "GEAENDERT": "newsletter-worker/src/index.js"}, t)
        if code_defekt != 1 or bereit_defekt or not any("::error::" in a for a in annotationen_defekt):
            fehler.append("defekte Push-Konfiguration wurde weiterhin grün übersprungen")
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
    print("✅ WORKER-DEPLOY-SELBSTTEST bestanden (Variablen, ID-Format, Platzhalter, workers_dev, Plan-Schutz, Live-Nachweis).")
    return 0


def _schreibe_summary(text: str) -> None:
    pfad = os.environ.get("GITHUB_STEP_SUMMARY")
    if pfad and text:
        with open(pfad, "a", encoding="utf-8") as f:
            f.write(text + "\n\n")


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return _selftest()
    if "--plan" in argv:
        code, liste, annotationen, summary = plan_auswerten()
        for a in annotationen:
            print(a)
        _schreibe_summary(summary)
        zeile = f"worker={json.dumps(liste)}"
        print(zeile)
        ausgabe = os.environ.get("GITHUB_OUTPUT")
        if ausgabe:
            with open(ausgabe, "a", encoding="utf-8") as f:
                f.write(zeile + "\n")
        return code
    if "--nachweis" in argv:
        i = argv.index("--nachweis")
        if i + 1 >= len(argv):
            print("--nachweis braucht einen Worker-Namen", file=sys.stderr)
            return 2
        code, meldung = deploy_nachweis(argv[i + 1])
        if code != 0:
            print(f"::error::{meldung}")
        else:
            print(meldung)
        _schreibe_summary(meldung)
        return code
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
    print(__doc__ or "Aufruf: --plan | --pruefen <worker> | --vorbereiten <worker> | --nachweis <worker> | --selftest")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
