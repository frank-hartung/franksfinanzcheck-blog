#!/usr/bin/env python3
"""Ein wartender Deploy ist kein grüner Deploy — Freigabe-Wache (#922, 01.11.2026).

Seit das Environment `cloudflare-produktion` einen Required Reviewer trägt, ist
der Worker-Deploy **absichtlich** zweistufig: Der Lauf startet, der Secret-
tragende Job wartet auf die Freigabe eines Menschen, und erst danach läuft
Wrangler. Das ist die gewollte Wirkung. Es hat nur einen stillen Preis, den
dieses Repository am 24.10.2026 schon einmal bezahlt hat:

    Ein Lauf, der auf Freigabe wartet, sieht in der Übersicht aus wie ein
    laufender Lauf. Er wird nicht rot, er meldet nichts, er altert nur —
    und belegt dabei den Concurrency-Slot `worker-deploy`. Der nächste Push
    reiht sich dahinter ein, der Nachweis für #922 entsteht nie, und niemand
    hat einen Anlass nachzusehen.

Diese Wache macht ausschließlich diesen einen Zustand sichtbar. Sie liest
die Workflow-Läufe der beiden Environment-gebundenen Ketten und nennt jeden
Lauf, der länger als die Schwelle auf Freigabe wartet — mit Alter, Lauf-Link
und dem Satz, der ihn schließt (freigeben oder abbrechen).

Bewusste Grenzen:

  * **Read-only.** Ausschließlich `GET` auf die Läufe-Liste zweier namentlich
    fixierter Workflows unter api.github.com. Keine Freigabe, kein Abbruch,
    kein Schreibzugriff — wer freigibt, ist ein Mensch, und das bleibt so.
  * **Kein Geheimnis.** Token nur im Header, nie in Ausgabe oder Markdown;
    Lauf-Links werden aus geprüfter Repository-Angabe und geprüfter Lauf-ID
    selbst gebaut, nie aus der API-Antwort übernommen.
  * **Junge Wartung ist kein Befund.** Bis zur Schwelle (Standard 120 Minuten)
    ist Warten normal; gemeldet wird erst, was niemand mehr im Blick hat.
  * **Nicht belegbar ist nicht in Ordnung.** Unlesbare Antwort, kaputte
    Zeitstempel oder eine Lauf-ID, die keine ist, enden mit Exit 2 (C33).

EXIT: 0 = keine Freigabe wartet zu lange · 1 = Befund (Freigabe überfällig)
      2 = der Zustand ist nicht belegbar

Bedienung:
  python3 scripts/worker_freigabe_wache.py --check
  python3 scripts/worker_freigabe_wache.py --check --md "$GITHUB_STEP_SUMMARY"
  python3 scripts/worker_freigabe_wache.py --check --schwelle 45
  python3 scripts/worker_freigabe_wache.py --selftest      # offline, ohne Netz

Hintergrund: WARTUNG-VEROEFFENTLICHUNG-WF-829B-922-DAUERHEILUNG-HIGHEND-2026-11-01.md
Runbook: docs/SICHERHEIT-BETRIEB-RUNBOOK.md, A4 (Freigabe) und D2 (Worker-Rot).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterable, Mapping

from github_kommando import annotation

API = "https://api.github.com"
REPO_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$")
WORKFLOW_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,60}\.yml$")
MAX_BODY = 1_000_000
PER_PAGE = "30"
SCHWELLE_MINUTEN = 120
MAX_SCHWELLE_MINUTEN = 24 * 60

# Genau die Ketten, die das Environment `cloudflare-produktion` anfordern –
# und damit genau die, deren Läufe auf eine Freigabe warten können.
WORKFLOWS = ("worker-deploy.yml", "worker-zugang-pruefen.yml")

# Zustände, in denen GitHub einen Lauf als „wartet" führt: `waiting` ist die
# Freigabe durch Required Reviewer, `pending` die Deployment-Protection-Regel,
# `action_required` der manuelle Eingriff. Alle drei sind ein Mensch, kein
# Fortschritt.
WARTEZUSTAENDE = frozenset({"waiting", "pending", "action_required"})


class WachenFehler(RuntimeError):
    """Der Zustand der Freigabe ist nicht belegbar."""


def _repo_pruefen(repo: str) -> str:
    wert = str(repo or "").strip()
    if not REPO_RE.fullmatch(wert):
        raise WachenFehler("GITHUB_REPOSITORY fehlt oder hat kein gültiges owner/repo-Format.")
    return wert


def _workflow_pruefen(workflow: str) -> str:
    wert = str(workflow or "").strip()
    if not WORKFLOW_RE.fullmatch(wert):
        raise WachenFehler("Workflow-Name ist nicht zulässig (erwartet: name.yml).")
    return wert


def lauf_link(repo: str, run_id: int) -> str:
    """Baut den Lauf-Link aus geprüften Teilen – nie aus der API-Antwort."""
    return f"https://github.com/{_repo_pruefen(repo)}/actions/runs/{int(run_id)}"


def laeufe_url(repo: str, workflow: str) -> str:
    return (f"{API}/repos/{_repo_pruefen(repo)}/actions/workflows/"
            f"{_workflow_pruefen(workflow)}/runs?per_page={PER_PAGE}")


def _url_pruefen(url: str, *, repo: str, workflow: str) -> None:
    """Der einzige erlaubte Netzweg: exakt die Läufe-Liste dieses Workflows."""
    teile = urllib.parse.urlsplit(url)
    if (teile.scheme != "https" or teile.netloc.lower() != "api.github.com"
            or teile.username is not None or teile.password is not None or teile.fragment):
        raise WachenFehler("Unsicheres GitHub-API-Ziel wurde abgewiesen.")
    erwarteter_pfad = (f"/repos/{_repo_pruefen(repo)}/actions/workflows/"
                       f"{_workflow_pruefen(workflow)}/runs")
    if teile.path != erwarteter_pfad:
        raise WachenFehler("Nicht erlaubter GitHub-API-Pfad wurde abgewiesen.")
    parameter = urllib.parse.parse_qs(teile.query, keep_blank_values=True)
    if set(parameter) != {"per_page"} or parameter.get("per_page") != [PER_PAGE]:
        raise WachenFehler("Nicht erlaubte GitHub-API-Parameter wurden abgewiesen.")


class _KeineWeiterleitung(urllib.request.HTTPRedirectHandler):
    """GitHub-Tokens niemals an ein Redirect-Ziel weiterreichen."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.URLError("Weiterleitung der GitHub-API wird abgelehnt")


def _api_roh(url: str, token: str, *, repo: str, workflow: str,
             timeout: float = 20.0) -> tuple[int, bytes]:
    _url_pruefen(url, repo=repo, workflow=workflow)
    if not token or any(ord(c) < 33 or ord(c) > 126 for c in token):
        raise WachenFehler("GITHUB_TOKEN/GH_TOKEN fehlt oder hat kein gültiges Headerformat.")
    anfrage = urllib.request.Request(url, headers={
        "accept": "application/vnd.github+json",
        "authorization": f"Bearer {token}",
        "user-agent": "franksfinanzcheck-worker-freigabe-wache/1.0",
        "x-github-api-version": "2022-11-28",
    })
    opener = urllib.request.build_opener(_KeineWeiterleitung())
    try:
        with opener.open(anfrage, timeout=timeout) as antwort:
            status = int(getattr(antwort, "status", 200))
            roh = antwort.read(MAX_BODY + 1)
    except urllib.error.HTTPError as fehler:
        status = int(fehler.code)
        roh = b""
        fehler.close()
    except (urllib.error.URLError, OSError, TimeoutError, ValueError) as fehler:
        # Keine Exception-/Antworttexte ausgeben: sie können Transportdetails
        # oder fremde Header enthalten. Der Typname reicht zur Triage.
        raise WachenFehler(
            f"GitHub-Läufe sind nicht erreichbar ({type(fehler).__name__}); "
            "der Freigabestand ist nicht nachgewiesen."
        ) from None
    if len(roh) > MAX_BODY:
        raise WachenFehler("GitHub-Antwort überschreitet das sichere Größenlimit.")
    return status, roh


def _runs_holen(repo: str, workflow: str, token: str,
                holen: Callable | None = None) -> list[dict]:
    url = laeufe_url(repo, workflow)
    if holen is None:
        status, roh = _api_roh(url, token, repo=repo, workflow=workflow)
    else:
        # Der injizierte Transport ist ausschließlich eine lokale Testgrenze;
        # Produktionsaufrufe benutzen immer den fest verankerten _api_roh.
        status, roh = holen(url, token)
    if status in (401, 403):
        raise WachenFehler(
            f"Workflow-Läufe sind nicht lesbar (HTTP {status}); dem Workflow-Token "
            "fehlt möglicherweise `actions: read`. Der Freigabestand ist unbelegt."
        )
    if status == 404:
        raise WachenFehler(
            f"Workflow `{workflow}` ist nicht auffindbar (HTTP 404) – die Kette, "
            "deren Freigabe diese Wache bewacht, fehlt oder wurde umbenannt."
        )
    if status != 200:
        raise WachenFehler(f"Workflow-Läufe sind nicht belegbar (HTTP {status}).")
    try:
        daten = json.loads(roh.decode("utf-8"))
    except (UnicodeError, ValueError):
        raise WachenFehler("GitHub-Läufe-API lieferte kein gültiges JSON.") from None
    if not isinstance(daten, dict) or not isinstance(daten.get("workflow_runs"), list):
        raise WachenFehler("GitHub-Läufe-API lieferte kein gültiges `workflow_runs`.")
    return daten["workflow_runs"]


def _zeitpunkt(wert: object) -> datetime:
    """Liest ausschließlich `JJJJ-MM-TTTHH:MM:SSZ` — keine Ratestunde."""
    if not isinstance(wert, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", wert):
        raise WachenFehler("Ein Lauf trägt keinen lesbaren Zeitstempel.")
    try:
        return datetime.strptime(wert, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        raise WachenFehler("Ein Lauf trägt keinen gültigen Zeitstempel.") from None


def lauf_normalisieren(lauf: object, *, repo: str, workflow: str) -> dict:
    """Ein Lauf wird zu {workflow, id, status, start, link} — oder zum Befund."""
    if not isinstance(lauf, dict):
        raise WachenFehler("Ein Lauf hat kein Objektformat.")
    run_id = lauf.get("id")
    if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0:
        raise WachenFehler("Ein Lauf trägt keine gültige Lauf-ID.")
    status = lauf.get("status")
    if not isinstance(status, str) or not status.strip():
        raise WachenFehler("Ein Lauf trägt keinen lesbaren Zustand.")
    return {
        "workflow": workflow,
        "id": run_id,
        "status": status.strip().lower(),
        "start": _zeitpunkt(lauf.get("created_at")),
        "link": lauf_link(repo, run_id),
    }


def bewerten(laeufe: Iterable[dict], *, jetzt: datetime, schwelle: int,
             repo: str) -> tuple[int, list[dict]]:
    """Reine Bewertung: (Exit-Code, Befunde). Ohne Netz, ohne Uhr, ohne Ausgabe."""
    if not isinstance(schwelle, int) or isinstance(schwelle, bool) or not 1 <= schwelle <= MAX_SCHWELLE_MINUTEN:
        raise WachenFehler(f"Schwelle muss zwischen 1 und {MAX_SCHWELLE_MINUTEN} Minuten liegen.")
    if not isinstance(jetzt, datetime):
        raise WachenFehler("Bezugszeit fehlt; ohne Uhr ist kein Alter belegbar.")
    if jetzt.tzinfo is None:
        jetzt = jetzt.replace(tzinfo=timezone.utc)
    befunde: list[dict] = []
    for lauf in laeufe:
        if lauf["status"] not in WARTEZUSTAENDE:
            continue
        alter = jetzt - lauf["start"]
        if alter < timedelta(0):
            raise WachenFehler(
                "Ein Lauf trägt einen Zeitstempel in der Zukunft; das Alter ist nicht belegbar."
            )
        minuten = int(alter.total_seconds() // 60)
        if minuten >= schwelle:
            befunde.append({**lauf, "minuten": minuten})
    befunde.sort(key=lambda b: b["minuten"], reverse=True)
    return (1 if befunde else 0), befunde


def beschreibe(befunde: list[dict], *, schwelle: int) -> str:
    """Eine Zeile je wartendem Lauf – ohne Geheimnisse, mit Lauf-Link."""
    teile = [
        f"Lauf {b['id']} ({b['workflow']}) wartet seit {b['minuten']} Minuten "
        f"auf Freigabe (Schwelle {schwelle}): {b['link']}"
        for b in befunde
    ]
    return " | ".join(teile)


def markdown(befunde: list[dict], *, schwelle: int, repo: str) -> str:
    zeilen = [
        "",
        "### Wartende Deploy-Freigaben",
        "",
        f"- Repository: **{repo}** · Schwelle: **{schwelle} Minuten**",
        "",
    ]
    if not befunde:
        zeilen += ["Kein Lauf wartet über der Schwelle auf eine Freigabe.", ""]
        return "\n".join(zeilen)
    zeilen += [
        "| Lauf | Workflow | Wartet seit | Link |",
        "|---|---|---|---|",
    ]
    for b in befunde:
        zeilen.append(
            f"| `{b['id']}` | `{b['workflow']}` | {b['minuten']} min | [Lauf öffnen]({b['link']}) |"
        )
    zeilen += [
        "",
        "Ein wartender Lauf blockiert den Concurrency-Slot `worker-deploy`; der "
        "nächste Deploy reiht sich dahinter ein. Schließen: im Lauf *Review "
        "deployments* freigeben oder den Lauf abbrechen.",
        "",
    ]
    return "\n".join(zeilen)


def pruefen(umgebung: Mapping[str, str] | None = None, *, schwelle: int = SCHWELLE_MINUTEN,
            jetzt: datetime | None = None, holen: Callable | None = None) -> tuple[int, list[dict]]:
    umgebung = os.environ if umgebung is None else umgebung
    repo = _repo_pruefen(umgebung.get("GITHUB_REPOSITORY", ""))
    token = (umgebung.get("GITHUB_TOKEN") or umgebung.get("GH_TOKEN") or "").strip()
    if not token:
        raise WachenFehler("GITHUB_TOKEN fehlt; der Freigabestand ist nicht nachgewiesen.")
    gesammelt: list[dict] = []
    for workflow in WORKFLOWS:
        roh = _runs_holen(repo, workflow, token, holen=holen)
        for lauf in roh:
            gesammelt.append(lauf_normalisieren(lauf, repo=repo, workflow=workflow))
    return bewerten(gesammelt, jetzt=jetzt or datetime.now(timezone.utc),
                    schwelle=schwelle, repo=repo)


def _lauf(run_id: int, status: str, created: str) -> dict:
    return {"id": run_id, "status": status, "created_at": created}


def _selbsttest() -> int:
    jetzt = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)
    repo = "frank-hartung/franksfinanzcheck-blog"

    def fehlerfall(name: str, bedingung: bool) -> str | None:
        return None if bedingung else f"{name} nicht erkannt"

    def bewerte(laeufe: list[dict], schwelle: int = 120) -> tuple[int, list[dict]]:
        normalisiert = [lauf_normalisieren(l, repo=repo, workflow="worker-deploy.yml")
                       for l in laeufe]
        return bewerten(normalisiert, jetzt=jetzt, schwelle=schwelle, repo=repo)

    faelle: list[str | None] = []

    # K1 – überfällige Freigabe ist ein Befund.
    code, befunde = bewerte([_lauf(9001, "waiting", "2026-11-01T06:00:00Z")])
    faelle.append(fehlerfall("K1 überfällige Freigabe",
                             code == 1 and len(befunde) == 1 and befunde[0]["minuten"] == 360))

    # K2 – junge Wartung ist kein Befund.
    code, befunde = bewerte([_lauf(9002, "waiting", "2026-11-01T11:30:00Z")])
    faelle.append(fehlerfall("K2 junge Wartung", code == 0 and befunde == []))

    # K3 – genau auf der Schwelle wartet zu lange, eine Minute darunter nicht.
    code, _ = bewerte([_lauf(9003, "waiting", "2026-11-01T10:00:00Z")])
    faelle.append(fehlerfall("K3a Schwelle erreicht", code == 1))
    code, _ = bewerte([_lauf(9004, "waiting", "2026-11-01T10:01:00Z")])
    faelle.append(fehlerfall("K3b eine Minute darunter", code == 0))

    # K4 – alle drei Wartezustände zählen, `completed` nicht.
    for index, status in enumerate(sorted(WARTEZUSTAENDE), start=1):
        code, _ = bewerte([_lauf(9010 + index, status, "2026-11-01T06:00:00Z")])
        faelle.append(fehlerfall(f"K4 Zustand {status}", code == 1))
    code, _ = bewerte([_lauf(9020, "completed", "2026-11-01T06:00:00Z")])
    faelle.append(fehlerfall("K4 completed ist kein Befund", code == 0))

    # K5 – der Link kommt aus geprüften Teilen, nie aus der API-Antwort.
    manipuliert = {**_lauf(9021, "waiting", "2026-11-01T06:00:00Z"),
                   "html_url": "https://boese.example/uebernehmen"}
    normal = lauf_normalisieren(manipuliert, repo=repo, workflow="worker-deploy.yml")
    faelle.append(fehlerfall("K5 Link aus eigener Konstruktion",
                             normal["link"] == lauf_link(repo, 9021)))

    # K6 – fremde Ziele und Pfade werden abgewiesen.
    for ziel in ("https://boese.example/repos/x/actions/workflows/worker-deploy.yml/runs?per_page=30",
                 "http://api.github.com/repos/x/y/actions/workflows/worker-deploy.yml/runs?per_page=30",
                 "https://api.github.com/repos/x/y/actions/workflows/worker-deploy.yml/runs?per_page=100",
                 "https://api.github.com/repos/x/y/actions/workflows/worker-deploy.yml/runs"):
        abgewiesen = False
        try:
            _url_pruefen(ziel, repo="x/y", workflow="worker-deploy.yml")
        except WachenFehler:
            abgewiesen = True
        faelle.append(fehlerfall(f"K6 Ziel {ziel[:60]}", abgewiesen))

    # K7 – unlesbare Läufe sind nicht „in Ordnung" (C33).
    for name, lauf in (
        ("K7a Lauf-ID", {"id": "9001", "status": "waiting", "created_at": "2026-11-01T06:00:00Z"}),
        ("K7b Zeitstempel", {"id": 9001, "status": "waiting", "created_at": "gestern"}),
        ("K7c Zustand", {"id": 9001, "status": "", "created_at": "2026-11-01T06:00:00Z"}),
        ("K7d kein Objekt", "lauf"),
    ):
        rot = False
        try:
            lauf_normalisieren(lauf, repo=repo, workflow="worker-deploy.yml")
        except WachenFehler:
            rot = True
        faelle.append(fehlerfall(name, rot))

    # K8 – ein Zeitstempel in der Zukunft ist nicht belegbar, nicht „frisch".
    zukunft = [lauf_normalisieren(_lauf(9030, "waiting", "2026-11-01T13:00:00Z"),
                                  repo=repo, workflow="worker-deploy.yml")]
    rot = False
    try:
        bewerten(zukunft, jetzt=jetzt, schwelle=120, repo=repo)
    except WachenFehler:
        rot = True
    faelle.append(fehlerfall("K8 Zukunft ist kein Alter", rot))

    # K9 – Geheimnisfreiheit: kein Token, kein Header in Ausgabe oder Markdown.
    geheim = "GIFT_TOKEN_DARF_NIE_ERSCHEINEN"
    code, befunde = bewerte([_lauf(9040, "waiting", "2026-11-01T06:00:00Z")])
    text = beschreibe(befunde, schwelle=120) + markdown(befunde, schwelle=120, repo=repo)
    faelle.append(fehlerfall("K9 Geheimnisfreiheit", geheim not in text and "Bearer" not in text))

    # K10 – Gegenprobe: eine Bewertung, die grundlos „alles gut" sagt, fällt auf.
    code, _ = bewerte([_lauf(9050, "waiting", "2026-10-30T06:00:00Z")])
    faelle.append(fehlerfall("K10 Gegenprobe", code != 0))

    offen = [f for f in faelle if f]
    if offen:
        for eintrag in offen:
            print(f"❌ Selbsttest: {eintrag}")
        return 2
    print(f"✅ SELBSTTEST OK — {len(faelle)} Fälle: überfällige Freigaben erkannt, "
          "junge Wartung still, unlesbare Zustände nie grün, Geheimnisse nie in der Ausgabe.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Meldet Worker-Deploy-Läufe, die auf eine Freigabe warten.")
    gruppe = parser.add_mutually_exclusive_group()
    gruppe.add_argument("--selftest", action="store_true", help="Sabotage- und Gegenproben ohne Netz")
    gruppe.add_argument("--check", action="store_true", help="GitHub-Läufe read-only live prüfen")
    parser.add_argument("--schwelle", type=int, default=SCHWELLE_MINUTEN,
                        help=f"Minuten bis ein wartender Lauf als Befund gilt (Standard {SCHWELLE_MINUTEN})")
    parser.add_argument("--md", default=None, help="Markdown-Abschnitt an diese Datei anhängen ('-' = stdout)")
    args = parser.parse_args(argv)
    if args.selftest:
        return _selbsttest()
    try:
        code, befunde = pruefen(schwelle=args.schwelle)
    except WachenFehler as fehler:
        annotation("error", str(fehler), titel="Wartende Deploy-Freigabe nicht belegt")
        return 2
    if args.md:
        text = markdown(befunde, schwelle=args.schwelle,
                        repo=os.environ.get("GITHUB_REPOSITORY", "?"))
        if args.md == "-":
            print(text)
        else:
            with open(args.md, "a", encoding="utf-8") as datei:
                datei.write(text + "\n")
    if code == 1:
        annotation(
            "warning",
            beschreibe(befunde, schwelle=args.schwelle)
            + " — freigeben (Review deployments) oder abbrechen; ein wartender Lauf hält den "
              "Concurrency-Slot `worker-deploy` und damit den Nachweis für #922 offen.",
            titel="Deploy wartet auf Freigabe",
        )
        return 1
    if befunde:
        annotation("notice", beschreibe(befunde, schwelle=args.schwelle),
                   titel="Deploy wartet auf Freigabe (innerhalb der Schwelle)")
    else:
        annotation("notice", "Kein Worker-Deploy wartet auf eine Freigabe.",
                   titel="Wartende Deploy-Freigabe")
    return 0


if __name__ == "__main__":
    sys.exit(main())
