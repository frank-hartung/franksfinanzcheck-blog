#!/usr/bin/env python3
"""Formale Nachweis- und Freigabesicherung für die KI-VO-Frist #1028.

Das Werkzeug prüft Belegdateien, ihre Hashes, Register und GitHub-Deploy- und
Workflow-Identität. Ein Hash oder eine Statuszeile beweist NICHT, dass ein
Dokument wahr, vollständig oder rechtlich ausreichend ist. Die fachliche
Prüfung und die bewusste Freigabe bleiben Aufgabe des Betreibers.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import quote, urlsplit

try:
    from . import deploy_drift_guard as drift
    from . import ki_provenienz as kp
except ImportError:
    import deploy_drift_guard as drift
    import ki_provenienz as kp

FRIST_ID = kp.FRIST_ID
FRIST_DATUM = kp.FRIST_DATUM
FRIST_ISSUE = 1028
FRIST_TITEL = "KI-VO: maschinenlesbare KI-Kennzeichnung für Bestandssysteme (Frist 02.12.2026)"
REPOSITORY = "frank-hartung/franksfinanzcheck-blog"
BETREIBER_LOGIN = "frank-hartung"
BELEG_ORDNER = "docs/ki-vo-abschluss"
BELEG = f"{BELEG_ORDNER}/abschluss.json"
KANAELE = {"seite", "feed", "tonspur", "bild", "pinterest"}
MAX_BELEG_BYTES = 900_000  # GitHub-Contents-API muss die Originalbytes liefern.
FINAL_SCHRITT = "KI-Frist: Issue nach Beleg und State schließen"
TEST_SCHRITT = "KI-Abschlusswege isoliert testen"

# Der Testjob läuft auf der Dispatch-Revision, der spätere KI-Job checkt main
# aus und git_sync kann rebasen. Diese Dateien müssen darum beim Readback in
# beiden Revisionen UND im tatsächlich ausgeführten Checkout identisch sein.
# Dies ist eine Bindung der Gegenproben an den ausgeführten Code, keine
# kryptografische Attestierung der Runner-Umgebung oder fachlicher Wahrheit.
ABSCHLUSS_CODE = (
    ".github/workflows/fristen-check.yml", "requirements-ci.txt",
    "scripts/fristen_check.py", "scripts/ki_frist_freigabe.py",
    "scripts/ki_provenienz.py", "scripts/deploy_drift_guard.py",
    "scripts/git_sync.sh", "scripts/tests/test_ki_frist_freigabe.py",
)
ABSCHLUSS_EINGABEN = (
    "data/recht-fristen.yaml", "data/ki_kennzeichnung.yaml", "data/ki_provenienz_state.json",
)


class FreigabeFehler(ValueError):
    """Abschluss nicht belegt; keine Verbuchung oder Issue-Schließung."""


def _eindeutig(paare):
    result = {}
    for key, value in paare:
        if key in result:
            raise FreigabeFehler(f"Doppelter Belegschlüssel: {key}")
        result[key] = value
    return result


def _json(data: bytes):
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=_eindeutig)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise FreigabeFehler(f"JSON nicht lesbar: {exc}") from exc


def _text(value, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise FreigabeFehler(f"{name}: konkrete Angabe fehlt")
    if re.search(r"\b(todo|tbd|unbekannt|offen|platzhalter)\b|[<>]", value, re.I):
        raise FreigabeFehler(f"{name}: ungeklärter Platzhalter")
    return value


def _datum(value, name: str, heute: dt.date) -> dt.date:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise FreigabeFehler(f"{name}: ISO-Datum fehlt")
    try:
        tag = dt.date.fromisoformat(value)
    except ValueError as exc:
        raise FreigabeFehler(f"{name}: ungültiges Datum") from exc
    if tag > heute:
        raise FreigabeFehler(f"{name}: Datum liegt in der Zukunft")
    return tag


def _zeit(value, name: str) -> dt.datetime:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
        raise FreigabeFehler(f"{name}: UTC-Zeitpunkt im Format YYYY-MM-DDTHH:MM:SSZ fehlt")
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FreigabeFehler(f"{name}: ungültiger Zeitpunkt") from exc


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _datei(root: Path, rel: str) -> bytes:
    pfad = Path(rel)
    base = (root / BELEG_ORDNER).resolve()
    if (pfad.is_absolute() or ".." in pfad.parts or not base.is_relative_to(root)
            or pfad.parts[:2] != ("docs", "ki-vo-abschluss")):
        raise FreigabeFehler(f"Beleg muss unter {BELEG_ORDNER} innerhalb des Repositories liegen")
    try:
        target = (root / pfad).resolve(strict=True)
        if not target.is_relative_to(base) or not target.is_file():
            raise FreigabeFehler(f"Belegdatei außerhalb von {BELEG_ORDNER}: {rel}")
        if target.stat().st_size > MAX_BELEG_BYTES:
            raise FreigabeFehler(f"Belegdatei für GitHub-Readback zu groß: {rel}")
        return target.read_bytes()
    except OSError as exc:
        raise FreigabeFehler(f"Belegdatei nicht lesbar: {rel}: {exc}") from exc


def _dokument(root: Path, eintrag, name: str) -> tuple[str, bytes]:
    if not isinstance(eintrag, dict):
        raise FreigabeFehler(f"{name}: Belegreferenz fehlt")
    rel = _text(eintrag.get("datei"), f"{name}.datei")
    digest = _text(eintrag.get("sha256"), f"{name}.sha256")
    if rel == BELEG or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise FreigabeFehler(f"{name}: Belegpfad oder SHA-256 ungültig")
    data = _datei(root, rel)
    if not data.strip() or _sha(data) != digest:
        raise FreigabeFehler(f"{name}: leerer Beleg oder SHA-256 stimmt nicht")
    return rel, data


def buendel_sha256(beleg: dict) -> str:
    """Kanonische Bindung der Freigabe an alles außer dem Freigabeblock."""
    bundle = {key: val for key, val in beleg.items() if key != "betreiberfreigabe"}
    return _sha(json.dumps(bundle, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False).encode("utf-8"))


def _api(endpoint: str):
    try:
        result = subprocess.run(["gh", "api", endpoint], capture_output=True,
                                text=True, timeout=30, check=False)
        if result.returncode:
            raise FreigabeFehler(f"GitHub-Nachweis nicht abrufbar: {endpoint}")
        return _json(result.stdout.encode("utf-8"))
    except (OSError, subprocess.SubprocessError) as exc:
        raise FreigabeFehler(f"GitHub-Nachweis nicht messbar: {exc}") from exc


def _job(jobs, name: str) -> dict:
    if not isinstance(jobs, list):
        raise FreigabeFehler("GitHub-Jobs nicht messbar")
    hits = [j for j in jobs if isinstance(j, dict) and j.get("name") == name]
    if len(hits) != 1 or hits[0].get("status") != "completed" or hits[0].get("conclusion") != "success":
        raise FreigabeFehler(f"GitHub-Job nicht erfolgreich: {name}")
    return hits[0]


def _schritt(job: dict, name: str) -> int:
    schritte = job.get("steps")
    if not isinstance(schritte, list):
        raise FreigabeFehler(f"Schritte von {job.get('name')} fehlen")
    hits = [s for s in schritte if isinstance(s, dict) and s.get("name") == name]
    if (len(hits) != 1 or hits[0].get("conclusion") != "success"
            or type(hits[0].get("number")) is not int):
        raise FreigabeFehler(f"GitHub-Schritt nicht erfolgreich: {name}")
    return hits[0]["number"]


def _neuestes_pages_deployment(repo: str, deployment_id: int, api) -> None:
    # Das Environment ist die öffentliche Auslieferungsquelle. Auch ein
    # neuer Deploy mit anderem Ref kann die abgenommene Site überholen.
    deployments = api(f"repos/{repo}/deployments?environment=github-pages&per_page=100")
    if (not isinstance(deployments, list) or not deployments
            or not isinstance(deployments[0], dict)
            or type(deployments[0].get("id")) is not int
            or deployments[0]["id"] != deployment_id):
        raise FreigabeFehler("Abgenommenes Deployment ist nicht das neueste Pages-Deployment "
                             "oder die Auslieferung ist nicht messbar")


def _deployment(repo: str, deploy: dict, live_zeit: dt.datetime, api, aktuell: bool) -> None:
    run_id = deploy.get("run_id")
    deployment_id = deploy.get("deployment_id")
    sha = _text(deploy.get("head_sha"), "deploy.head_sha")
    if (type(run_id) is not int or run_id <= 0 or type(deployment_id) is not int
            or deployment_id <= 0 or not re.fullmatch(r"[0-9a-f]{40}", sha)):
        raise FreigabeFehler("Deploy-Run, Pages-Deployment-ID oder vollständige Ausgangsrevision fehlen")
    run = api(f"repos/{repo}/actions/runs/{run_id}")
    if not isinstance(run, dict) or any((
        run.get("id") != run_id, run.get("path") != ".github/workflows/deploy.yml",
        run.get("head_branch") != "main", run.get("head_sha") != sha,
        run.get("event") not in ("push", "workflow_dispatch"),
        run.get("status") != "completed", run.get("conclusion") != "success",
        type(run.get("run_attempt")) is not int or run.get("run_attempt", 0) <= 0,
    )):
        raise FreigabeFehler("Kein erfolgreicher main-Deploy-Run der angegebenen Ausgangsrevision")
    if live_zeit < _zeit(run.get("updated_at"), "deploy.updated_at"):
        raise FreigabeFehler("Live-Abnahme liegt vor Abschluss des Deploy-Runs")

    antwort = api(f"repos/{repo}/actions/runs/{run_id}/jobs?filter=latest&per_page=100")
    jobs = antwort.get("jobs") if isinstance(antwort, dict) else None
    if (not isinstance(jobs, list) or type(antwort.get("total_count")) is not int
            or antwort["total_count"] != len(jobs)):
        raise FreigabeFehler("Deploy-Jobs nicht vollständig messbar")
    job = _job(jobs, "deploy")
    pages = _job(jobs, "An GitHub Pages ausliefern (Environment github-pages)")
    if any(type(j.get("run_attempt")) is not int or j["run_attempt"] != run["run_attempt"]
           for j in (job, pages)):
        raise FreigabeFehler("Deploy- und Pages-Job müssen im selben Workflow-Versuch erfolgreich sein")
    cover = _schritt(job, "KI-Cover – finale Provenienzprüfung")
    gate = _schritt(job, "KI-Provenienz – finales Veröffentlichungs-Gate")
    artifact = _schritt(job, "Artefakt für offizielles Pages-Deployment hochladen")
    _schritt(pages, "Deployment auslösen")
    if not cover < gate < artifact or type(pages.get("id")) is not int:
        raise FreigabeFehler("Finale KI-Gates oder Pages-Job sind dem Artefakt nicht eindeutig zugeordnet")

    deployment = api(f"repos/{repo}/deployments/{deployment_id}")
    if (not isinstance(deployment, dict) or deployment.get("id") != deployment_id
            or deployment.get("environment") != "github-pages"
            or deployment.get("ref") not in ("main", "refs/heads/main")
            or deployment.get("sha") != sha):
        raise FreigabeFehler("Offizielles Pages-Deployment passt nicht zum geprüften Run")
    statuses = api(f"repos/{repo}/deployments/{deployment_id}/statuses?per_page=100")
    log_url = f"https://github.com/{repo}/actions/runs/{run_id}/job/{pages['id']}"
    if (not isinstance(statuses, list) or not statuses or not isinstance(statuses[0], dict)
            or statuses[0].get("state") not in (("success",) if aktuell else ("success", "inactive"))):
        raise FreigabeFehler("Aktueller Pages-Status ist kein belegter Erfolg")
    erfolge = [s for s in statuses if isinstance(s, dict) and s.get("state") == "success"
               and s.get("log_url") == log_url]
    if not erfolge or all(_zeit(s.get("created_at"), "pages.success") > live_zeit for s in erfolge):
        raise FreigabeFehler("Erfolgreiches Pages-Deployment vor der Live-Abnahme fehlt")
    if aktuell:
        _neuestes_pages_deployment(repo, deployment_id, api)


def _beleg_lesen(root: Path) -> dict:
    beleg = _json(_datei(root, BELEG))
    if not isinstance(beleg, dict) or beleg.get("frist_id") != FRIST_ID:
        raise FreigabeFehler("Abschlussbeleg gehört nicht zu dieser Frist")
    return beleg


def _pruefen(root: Path, repository: str, heute: dt.date, jetzt: dt.datetime,
             api, aktuell: bool) -> tuple[dict, set[str]]:
    if not isinstance(repository, str) or repository.lower() != REPOSITORY:
        raise FreigabeFehler("Falsches oder unbekanntes GitHub-Repository")
    if kp.ungeklaert(root):
        raise FreigabeFehler("Register enthält noch ungeklärte menschlich-Einträge")
    wachzustand = kp.state_lesen(root)
    if (wachzustand["ungeklaert_erstmals"] or type(wachzustand.get("funde")) is not int
            or wachzustand["funde"] != 0 or wachzustand.get("frist") != FRIST_DATUM):
        raise FreigabeFehler("Wachzustand enthält offene Fälle, technische Funde oder eine falsche Frist")
    beleg = _beleg_lesen(root)
    dateien = {BELEG}
    systeme = beleg.get("systeme")
    if not isinstance(systeme, list) or not systeme:
        raise FreigabeFehler("Inventar tatsächlich verwendeter Systeme fehlt")
    gesehen = set()
    for index, system in enumerate(systeme, start=1):
        if not isinstance(system, dict):
            raise FreigabeFehler(f"System {index}: Eintrag fehlt")
        identitaet = tuple(_text(system.get(name), f"System {index}.{name}")
                            for name in ("name", "version", "anbieter"))
        if identitaet in gesehen:
            raise FreigabeFehler(f"System {index}: doppelter Eintrag")
        gesehen.add(identitaet)
        if system.get("rolle") not in ("betreiber", "anbieter", "beides"):
            raise FreigabeFehler(f"System {index}: Rolle ungeklärt")
        _datum(system.get("inverkehrgebracht_am"), f"System {index}.inverkehrgebracht_am", heute)
        dateien.add(_dokument(root, system.get("nachweis"), f"System {index}.nachweis")[0])
    for name in ("bildinventar", "registerpruefung"):
        dateien.add(_dokument(root, beleg.get(name), name)[0])
    live = beleg.get("live_abnahme")
    if not isinstance(live, dict):
        raise FreigabeFehler("Live-Abnahme fehlt")
    live_zeit = _zeit(live.get("zeitpunkt"), "live_abnahme.zeitpunkt")
    if live_zeit > jetzt:
        raise FreigabeFehler("Live-Abnahme liegt in der Zukunft")
    _text(live.get("pruefer"), "live_abnahme.pruefer")
    url = urlsplit(_text(live.get("url"), "live_abnahme.url"))
    if (url.scheme != "https" or url.hostname != "franksfinanzcheck.de" or url.username
            or url.password or url.port not in (None, 443)):
        raise FreigabeFehler("Live-Abnahme-URL ist nicht die öffentliche Blog-Domain")
    kanaele = live.get("kanaele")
    if not isinstance(kanaele, list) or not all(isinstance(k, str) for k in kanaele) or not KANAELE.issubset(set(kanaele)):
        raise FreigabeFehler("Live-Abnahme muss Seite, Feed, Tonspur, Bild und Pinterest umfassen")
    dateien.add(_dokument(root, live.get("nachweis"), "live_abnahme.nachweis")[0])
    freigabe = beleg.get("betreiberfreigabe")
    if not isinstance(freigabe, dict):
        raise FreigabeFehler("Betreiberfreigabe fehlt")
    zeit = _zeit(freigabe.get("zeitpunkt"), "betreiberfreigabe.zeitpunkt")
    if zeit < live_zeit or zeit > jetzt:
        raise FreigabeFehler("Betreiberfreigabe liegt vor der Live-Abnahme oder in der Zukunft")
    _text(freigabe.get("name"), "betreiberfreigabe.name")
    login = _text(freigabe.get("github_login"), "betreiberfreigabe.github_login")
    if login.lower() != BETREIBER_LOGIN:
        raise FreigabeFehler("Betreiberfreigabe muss dem Repository-Inhaber zugeordnet sein")
    digest = buendel_sha256(beleg)
    if freigabe.get("buendel_sha256") != digest:
        raise FreigabeFehler("Betreiberfreigabe ist nicht an dieses Nachweis-Bündel gebunden")
    rel, text = _dokument(root, freigabe.get("nachweis"), "betreiberfreigabe.nachweis")
    dateien.add(rel)
    try:
        freigabetext = text.decode("utf-8")
    except UnicodeError as exc:
        raise FreigabeFehler("Betreiberfreigabe muss als lesbarer UTF-8-Text vorliegen") from exc
    if not all(wert in freigabetext for wert in (digest, login, freigabe["zeitpunkt"])):
        raise FreigabeFehler("Freigabetext nennt Bündel-Hash, Konto und Zeitpunkt nicht")
    deploy = beleg.get("deploy")
    if not isinstance(deploy, dict):
        raise FreigabeFehler("Offizieller Deploy-Run fehlt")
    _deployment(repository, deploy, live_zeit, api, aktuell)
    return beleg, dateien


def pruefen(root: Path, repository: str, heute: dt.date, *, api=None,
            jetzt: dt.datetime | None = None, aktuell: bool = True) -> list[str]:
    """Leere Liste = formale Prüfung bestanden, nicht = menschlicher Wahrheitsbeweis."""
    try:
        _pruefen(Path(root).resolve(), repository, heute,
                 jetzt or dt.datetime.now(dt.timezone.utc), api or _api, aktuell)
    except (FreigabeFehler, kp.WerkzeugFehler, OSError, UnicodeError, TypeError, ValueError) as exc:
        return [str(exc)]
    return []


def dispatcher_pruefen(root: Path, env=None, *, api=None) -> dict:
    """Nur die bewusste Anforderung des Repo-Inhabers im echten main-Workflow."""
    env = os.environ if env is None else env
    api = api or _api
    erwartet_ref = f"{REPOSITORY}/.github/workflows/fristen-check.yml@refs/heads/main"
    if (env.get("GITHUB_ACTIONS") != "true" or env.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
            or env.get("GITHUB_REF") != "refs/heads/main"
            or env.get("GITHUB_JOB") not in ("fristen", "ki-freigabe")
            or str(env.get("GITHUB_WORKFLOW_REF") or "").lower() != erwartet_ref
            or str(env.get("GITHUB_REPOSITORY") or "").lower() != REPOSITORY):
        raise FreigabeFehler("KI-Frist nur per manuellem Fristen-Workflow auf main abschließen")
    beleg = _beleg_lesen(Path(root).resolve())
    freigabe = beleg.get("betreiberfreigabe")
    login = freigabe.get("github_login") if isinstance(freigabe, dict) else None
    if (not isinstance(login, str) or login.lower() != BETREIBER_LOGIN
            or str(env.get("GITHUB_ACTOR") or "").lower() != BETREIBER_LOGIN
            or str(env.get("GITHUB_TRIGGERING_ACTOR") or "").lower() != BETREIBER_LOGIN):
        raise FreigabeFehler("Workflow muss vom freigebenden Repository-Inhaber gestartet werden")
    try:
        event = _json(Path(env.get("GITHUB_EVENT_PATH", "")).read_bytes())
        eingabe = event["inputs"]["erledigt"]
        if not isinstance(eingabe, str) or FRIST_ID not in {x.strip() for x in eingabe.split(",")}:
            raise FreigabeFehler("Manueller Workflow muss diese Frist ausdrücklich als Eingabe nennen")
        run_id = int(env.get("GITHUB_RUN_ID", ""))
        versuch = int(env.get("GITHUB_RUN_ATTEMPT", ""))
        if run_id <= 0 or versuch <= 0:
            raise ValueError("ungültige Run-ID oder Versuch")
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise FreigabeFehler(f"Workflow-Eingabe oder Run-ID nicht prüfbar: {exc}") from exc
    run = api(f"repos/{REPOSITORY}/actions/runs/{run_id}")
    sha = str(env.get("GITHUB_SHA") or "")
    if (not re.fullmatch(r"[0-9a-f]{40}", sha) or not isinstance(run, dict)
            or run.get("id") != run_id or run.get("path") != ".github/workflows/fristen-check.yml"
            or run.get("head_branch") != "main" or run.get("head_sha") != sha
            or type(run.get("run_attempt")) is not int or run["run_attempt"] != versuch
            or run.get("event") != "workflow_dispatch" or run.get("status") != "in_progress"
            or not isinstance(run.get("actor"), dict) or not isinstance(run.get("triggering_actor"), dict)
            or str(run["actor"].get("login") or "").lower() != BETREIBER_LOGIN
            or str(run["triggering_actor"].get("login") or "").lower() != BETREIBER_LOGIN):
        raise FreigabeFehler("GitHub bestätigt keinen laufenden manuellen Inhaber-Workflow dieser Revision")
    if _zeit(run.get("created_at"), "workflow.created_at") < _zeit(freigabe.get("zeitpunkt"), "betreiberfreigabe.zeitpunkt"):
        raise FreigabeFehler("Workflow wurde vor der dokumentierten Betreiberfreigabe gestartet")
    return run


def quittung_erstellen(root: Path, env=None, *, api=None, heute: dt.date | None = None) -> dict:
    env = os.environ if env is None else env
    run = dispatcher_pruefen(root, env, api=api)
    if env.get("GITHUB_JOB") != "fristen":
        raise FreigabeFehler("Abschluss darf nur im Fristen-Job beantragt werden")
    return {"version": 1, "beleg_sha256": _sha(_datei(Path(root).resolve(), BELEG)),
            "workflow_run_id": int(env["GITHUB_RUN_ID"]), "workflow_attempt": run["run_attempt"],
            "workflow_sha": run["head_sha"], "github_login": BETREIBER_LOGIN,
            "workflow_start": run["created_at"], "beantragt_am": (heute or dt.date.today()).isoformat()}


def _remote_datei(repo: str, ref: str, rel: str, api) -> bytes:
    antwort = api(f"repos/{repo}/contents/{quote(rel, safe='/')}?ref={ref}")
    if not isinstance(antwort, dict) or antwort.get("encoding") != "base64":
        raise FreigabeFehler(f"GitHub-Readback nicht verfügbar: {rel}")
    try:
        return base64.b64decode("".join(antwort["content"].split()), validate=True)
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        raise FreigabeFehler(f"GitHub-Readback beschädigt: {rel}") from exc


def _abschluss_vorjobs(repository: str, run_id: int, versuch: int, api) -> list[dict]:
    antwort = api(f"repos/{repository}/actions/runs/{run_id}/jobs?filter=latest&per_page=100")
    jobs = antwort.get("jobs") if isinstance(antwort, dict) else None
    if (not isinstance(jobs, list) or type(antwort.get("total_count")) is not int
            or antwort["total_count"] != len(jobs)):
        raise FreigabeFehler("Freigabe-Jobs nicht vollständig messbar")
    fristen = _job(jobs, "fristen")
    testen = _job(jobs, "KI-Abschluss-Gegenproben")
    if fristen.get("run_attempt") != versuch or testen.get("run_attempt") != versuch:
        raise FreigabeFehler("Fristen- und Testjob müssen zu diesem Workflow-Versuch gehören")
    pruefung = _schritt(fristen, "Fristen prüfen + Issues eskalieren")
    commit = _schritt(fristen, "Report & State committen")
    _schritt(testen, TEST_SCHRITT)
    if pruefung >= commit:
        raise FreigabeFehler("Fristen-Prüfung und State-Push sind falsch angeordnet")
    return jobs


def quittung_pruefen(root: Path, repository: str, heute: dt.date, fstate: dict, *,
                     api=None, env=None, jetzt: dt.datetime | None = None) -> list[str]:
    """Altflags allein zählen nicht; Quittung muss zu einem echten Workflow passen."""
    api = api or _api
    env = os.environ if env is None else env
    root = Path(root).resolve()
    try:
        q = fstate.get("ki_abschluss")
        if (not isinstance(q, dict) or type(q.get("version")) is not int or q["version"] != 1
                or type(q.get("workflow_run_id")) is not int or q["workflow_run_id"] <= 0
                or type(q.get("workflow_attempt")) is not int or q["workflow_attempt"] <= 0
                or not isinstance(q.get("workflow_sha"), str)
                or not re.fullmatch(r"[0-9a-f]{40}", q["workflow_sha"])
                or q.get("github_login") != BETREIBER_LOGIN
                or q.get("beleg_sha256") != _sha(_datei(root, BELEG))):
            raise FreigabeFehler("Erledigt-Flag ohne passende Workflow-/Belegquittung")
        erledigt = _datum(fstate.get("erledigt_am"), "erledigt_am", heute)
        if (fstate.get("last_done") != fstate["erledigt_am"]
                or q.get("beantragt_am") != fstate["erledigt_am"]):
            raise FreigabeFehler("Erledigungsdaten der KI-Frist widersprechen sich")
        start = _zeit(q.get("workflow_start"), "workflow_start")
        if start.date() > erledigt:
            raise FreigabeFehler("Erledigung liegt vor dem manuellen Workflow")
        beleg, _ = _pruefen(root, repository, heute, jetzt or dt.datetime.now(dt.timezone.utc), api, False)
        if start < _zeit(beleg["betreiberfreigabe"]["zeitpunkt"], "betreiberfreigabe.zeitpunkt"):
            raise FreigabeFehler("Workflow wurde vor der Betreiberfreigabe gestartet")
        # Während der einmaligen Ausführung ist deren Schluss-Schritt noch
        # nicht fertig. Nur dieser echte manuelle Lauf darf sich selbst prüfen.
        if str(q["workflow_run_id"]) == str(env.get("GITHUB_RUN_ID") or ""):
            if env.get("GITHUB_JOB") != "ki-freigabe":
                raise FreigabeFehler("Laufende Freigabe darf nur im nachgelagerten Job geprüft werden")
            run = dispatcher_pruefen(root, env, api=api)
            if (run.get("created_at") != q["workflow_start"] or run.get("head_sha") != q["workflow_sha"]
                    or run.get("run_attempt") != q["workflow_attempt"]):
                raise FreigabeFehler("Quittung passt nicht zur Revision und zum Versuch des aktuellen Workflows")
            _abschluss_vorjobs(repository, q["workflow_run_id"], q["workflow_attempt"], api)
            return []
        rid = q["workflow_run_id"]
        run = api(f"repos/{repository}/actions/runs/{rid}")
        if (not isinstance(run, dict) or run.get("id") != rid
                or run.get("path") != ".github/workflows/fristen-check.yml"
                or run.get("event") != "workflow_dispatch" or run.get("head_branch") != "main"
                or run.get("status") != "completed" or run.get("conclusion") != "success"
                or run.get("created_at") != q["workflow_start"]
                or run.get("run_attempt") != q["workflow_attempt"] or run.get("head_sha") != q["workflow_sha"]
                or (run.get("actor") or {}).get("login", "").lower() != BETREIBER_LOGIN
                or (run.get("triggering_actor") or {}).get("login", "").lower() != BETREIBER_LOGIN):
            raise FreigabeFehler("Freigabe-Workflow ist nicht erfolgreich oder nicht vom Betreiber")
        sha = run.get("head_sha")
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise FreigabeFehler("Revision des Freigabe-Workflows fehlt")
        if _sha(_remote_datei(repository, sha, BELEG, api)) != q["beleg_sha256"]:
            raise FreigabeFehler("Beleg lag beim manuellen Freigabe-Workflow nicht in dieser Form vor")
        jobs = _abschluss_vorjobs(repository, rid, q["workflow_attempt"], api)
        abschluss_job = _job(jobs, "KI-Freigabe nach State und Tests")
        if abschluss_job.get("run_attempt") != q["workflow_attempt"]:
            raise FreigabeFehler("KI-Freigabejob gehört zu einem anderen Workflow-Versuch")
        vorbereiten = _schritt(abschluss_job, "KI-Freigabe nach Tests vorbereiten")
        state_commit = _schritt(abschluss_job, "KI-Abschluss-State committen")
        abschluss = _schritt(abschluss_job, FINAL_SCHRITT)
        if not vorbereiten < state_commit < abschluss:
            raise FreigabeFehler("Freigabe-Workflow hat Prüfung, State und Issue falsch angeordnet")
    except (FreigabeFehler, kp.WerkzeugFehler, OSError, UnicodeError, TypeError, ValueError, AttributeError) as exc:
        return [str(exc)]
    return []


def _auslieferungsdrift_pruefen(repository: str, deployed_sha: str, main_sha: str, api) -> None:
    """Keine Abschlussfreigabe, wenn ausstehende Site-/KI-Änderungen main erreichten."""
    vergleich = api(f"repos/{repository}/compare/{deployed_sha}...{main_sha}?per_page=100")
    if (not isinstance(vergleich, dict) or vergleich.get("status") not in ("ahead", "identical")
            or vergleich.get("behind_by") != 0 or type(vergleich.get("total_commits")) is not int
            or not isinstance(vergleich.get("merge_base_commit"), dict)
            or vergleich["merge_base_commit"].get("sha") != deployed_sha):
        raise FreigabeFehler("Vergleich zwischen Deploy-Ausgangsrevision und main nicht belastbar")
    dateien = vergleich.get("files")
    # GitHub begrenzt die Compare-Dateiliste auf 300 Einträge. Ein abgeschnittener
    # Diff darf weder als vollständig noch als harmlos gelten.
    if not isinstance(dateien, list) or len(dateien) >= 300:
        raise FreigabeFehler("Deploy/main-Dateivergleich fehlt oder ist möglicherweise abgeschnitten")
    ki_praefixe = (
        "scripts/ki_", "scripts/pinterest", "scripts/generate_pins.py", "scripts/social_",
        "scripts/image_optimizer.py", ".github/workflows/deploy.yml",
        ".github/workflows/notfall-deploy.yml",
        ".github/workflows/ki-provenienz-wache.yml", ".github/workflows/pinterest-ai.yml",
        ".github/workflows/repin-weekly.yml", ".github/workflows/social-autopilot.yml",
    )
    relevant = []
    for eintrag in dateien:
        if not isinstance(eintrag, dict) or not isinstance(eintrag.get("filename"), str) or not eintrag["filename"]:
            raise FreigabeFehler("Deploy/main-Dateivergleich ist beschädigt")
        pfade = [eintrag["filename"]]
        if eintrag.get("status") == "renamed":
            if not isinstance(eintrag.get("previous_filename"), str) or not eintrag["previous_filename"]:
                raise FreigabeFehler("Umbenannter Pfad im Deploy/main-Vergleich ist unvollständig")
            pfade.append(eintrag["previous_filename"])
        relevant.extend(p for p in pfade if drift.is_site_relevant(p) or p.startswith(ki_praefixe))
    if relevant:
        raise FreigabeFehler("main enthält seit dem abgenommenen Deploy ungeprüfte Site-/KI-Änderungen: "
                            + ", ".join(sorted(set(relevant))[:8]))


def _laufende_deploys_pruefen(repository: str, deployment_id: int, api) -> None:
    # Der Notfall-Workflow checkt main auch dann aus, wenn der Dispatch von
    # einem anderen Ref stammt. Deshalb beide Veröffentlichungs-Workflows
    # über ALLE Branches prüfen, nicht nur deploy.yml auf main.
    for workflow in ("deploy.yml", "notfall-deploy.yml"):
        for status in ("queued", "in_progress", "waiting", "requested", "pending"):
            antwort = api(f"repos/{repository}/actions/workflows/{workflow}/runs?status={status}&per_page=1")
            if (not isinstance(antwort, dict) or type(antwort.get("total_count")) is not int
                    or antwort["total_count"] != 0 or antwort.get("workflow_runs") != []):
                raise FreigabeFehler(f"{workflow}: Deploy-Läufe im Zustand {status} "
                                     "laufen noch oder sind nicht messbar")
    _neuestes_pages_deployment(repository, deployment_id, api)
    statuses = api(f"repos/{repository}/deployments/{deployment_id}/statuses?per_page=1")
    if not isinstance(statuses, list) or not statuses or not isinstance(statuses[0], dict) or statuses[0].get("state") != "success":
        raise FreigabeFehler("Abgenommenes Pages-Deployment ist nicht mehr aktuell erfolgreich")


def remote_state_pruefen(root: Path, repository: str, fstate: dict, *, api=None,
                         heute: dt.date | None = None, jetzt: dt.datetime | None = None) -> tuple[str, int]:
    """State, Belege und Drift nachweisen; main-SHA und Pages-ID für letzten Fence liefern."""
    api = api or _api
    root = Path(root).resolve()
    heute = heute or dt.datetime.now(dt.timezone.utc).date()
    beleg, dateien = _pruefen(root, repository, heute, jetzt or dt.datetime.now(dt.timezone.utc), api, True)
    ref_endpoint = f"repos/{repository}/git/ref/heads/main"
    ref = api(ref_endpoint)
    sha = (ref.get("object") or {}).get("sha") if isinstance(ref, dict) else None
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise FreigabeFehler("Aktueller main-Stand nicht lesbar")
    remote = _json(_remote_datei(repository, sha, "data/fristen_state.json", api))
    if not isinstance(remote, dict) or remote.get(FRIST_ID) != fstate:
        raise FreigabeFehler("Freigabe-State wurde nicht unverändert auf main gespeichert")
    vorgemerkt = fstate.get("ki_abschluss_vorgemerkt")
    quittung = (vorgemerkt.get("quittung") if isinstance(vorgemerkt, dict)
                else fstate.get("ki_abschluss"))
    workflow_sha = quittung.get("workflow_sha") if isinstance(quittung, dict) else None
    if not isinstance(workflow_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", workflow_sha):
        raise FreigabeFehler("Geprüfte Workflow-Revision in der Quittung fehlt")
    for rel in dateien:
        lokal = _datei(root, rel)
        if (_remote_datei(repository, sha, rel, api) != lokal
                or _remote_datei(repository, workflow_sha, rel, api) != lokal):
            raise FreigabeFehler(f"Beleg lag auf main oder beim Dispatch nicht in der geprüften Fassung vor: {rel}")
    for rel in ABSCHLUSS_CODE + ABSCHLUSS_EINGABEN:
        try:
            lokal = (root / rel).read_bytes()
        except OSError as exc:
            raise FreigabeFehler(f"Abschluss-Code oder Eingabe nicht lesbar: {rel}") from exc
        if (_remote_datei(repository, workflow_sha, rel, api) != lokal
                or _remote_datei(repository, sha, rel, api) != lokal):
            raise FreigabeFehler(f"Abschluss-Code oder Eingabe änderte sich seit Dispatch oder Checkout: {rel}")
    _auslieferungsdrift_pruefen(repository, beleg["deploy"]["head_sha"], sha, api)
    _laufende_deploys_pruefen(repository, beleg["deploy"]["deployment_id"], api)
    if api(ref_endpoint) != ref:
        raise FreigabeFehler("main änderte sich während des Readbacks; erneut prüfen")
    return sha, beleg["deploy"]["deployment_id"]


def letzte_freigabe_pruefen(repository: str, sha: str, deployment_id: int, *, api=None) -> None:
    """Letzter begrenzter Race-Check unmittelbar vor dem Issue-Close.

    GitHub bietet keine atomare Transaktion für main, Deploy und Issue. Auch
    nach dieser Prüfung bleibt ein kleines Zeitfenster; Operator und Runbook
    müssen parallele Änderungen deshalb weiterhin vermeiden.
    """
    api = api or _api
    endpoint = f"repos/{repository}/git/ref/heads/main"
    for phase in ("vor", "nach"):
        ref = api(endpoint)
        if (not isinstance(ref, dict) or not isinstance(ref.get("object"), dict)
                or ref["object"].get("sha") != sha):
            raise FreigabeFehler(f"main änderte sich {phase} der letzten Deploy-Prüfung")
        if phase == "vor":
            _laufende_deploys_pruefen(repository, deployment_id, api)
