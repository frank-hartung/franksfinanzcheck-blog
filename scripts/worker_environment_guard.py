#!/usr/bin/env python3
"""Fail-closed-Vertrag für das GitHub-Environment des Worker-Deploys.

Ein Environment wird beim ersten Workflow-Aufruf automatisch angelegt –
standardmäßig OHNE Required Reviewer und OHNE Branch-Beschränkung. Ein bloßes
`environment: cloudflare-produktion` in YAML ist deshalb kein Schutz. Dieses
read-only Gate prüft die tatsächlich wirksame GitHub-Konfiguration, bevor ein
Deploy-Job das Environment und seine Cloudflare-Secrets anfordert.

Erwarteter Vertrag:
  * mindestens ein Required Reviewer;
  * genau der Branch `main` (keine Tags und keine weiteren Branch-Muster);
  * Administratoren dürfen die Freigabe nicht umgehen.

Es werden weder Secrets gelesen noch Konfigurationen geschrieben. Der einzige
Netzweg ist die GitHub-REST-API unter api.github.com.
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
from typing import Callable, Mapping

from github_kommando import annotation

API = "https://api.github.com"
ENVIRONMENT = "cloudflare-produktion"
API_VERSION = "2022-11-28"
MAX_BODY = 1_000_000
MAX_PAGES = 20
REPO_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$")
NEXT_LINK_RE = re.compile(r"<([^<>]+)>\s*;\s*rel=\"?([^\";, ]+)\"?")


class PruefFehler(RuntimeError):
    """Die GitHub-Konfiguration ist nicht sicher oder nicht belegbar."""

    exit_code = 1


class ApiFehler(PruefFehler):
    """Die read-only-Prüfung konnte den Konfigurationsstand nicht belegen."""

    exit_code = 2


class _KeineWeiterleitung(urllib.request.HTTPRedirectHandler):
    """GitHub-Tokens niemals an ein Redirect-Ziel weiterreichen."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.URLError("Weiterleitung der GitHub-API wird abgelehnt")


def _repo_pruefen(repo: str) -> str:
    wert = str(repo or "").strip()
    if not REPO_RE.fullmatch(wert):
        raise ApiFehler("GITHUB_REPOSITORY fehlt oder hat kein gültiges owner/repo-Format.")
    return wert


def _api_url_pruefen(url: str, *, repo: str, policies: bool) -> None:
    """API-Aufrufe bleiben auf genau dem Environment-Endpunkt und seiner Policy-Liste."""
    teile = urllib.parse.urlsplit(url)
    if (teile.scheme != "https" or teile.netloc.lower() != "api.github.com"
            or teile.username is not None or teile.password is not None or teile.fragment):
        raise ApiFehler("Unsicheres GitHub-API-Ziel wurde abgewiesen.")
    basis = f"/repos/{repo}/environments/{ENVIRONMENT}"
    erwarteter_pfad = basis + "/deployment-branch-policies" if policies else basis
    if teile.path != erwarteter_pfad:
        raise ApiFehler("Nicht erlaubter GitHub-API-Pfad wurde abgewiesen.")
    if policies:
        parameter = urllib.parse.parse_qs(teile.query, keep_blank_values=True)
        if set(parameter) - {"per_page", "page"}:
            raise ApiFehler("Nicht erlaubte GitHub-API-Parameter wurden abgewiesen.")
        if parameter.get("per_page", ["100"]) != ["100"]:
            raise ApiFehler("Die Branch-Policy-Abfrage muss vollständig paginiert werden.")
        if "page" in parameter:
            try:
                if len(parameter["page"]) != 1 or int(parameter["page"][0]) < 1:
                    raise ValueError
            except ValueError:
                raise ApiFehler("Ungültige GitHub-API-Seitennummer.") from None
    elif teile.query:
        raise ApiFehler("Der Environment-Endpunkt darf keine Query-Parameter enthalten.")


def _api_roh(url: str, token: str, *, repo: str, policies: bool,
             timeout: float = 20.0) -> tuple[int, Mapping[str, str], bytes]:
    _api_url_pruefen(url, repo=repo, policies=policies)
    if not token or any(ord(c) < 33 or ord(c) > 126 for c in token):
        raise ApiFehler("GITHUB_TOKEN/GH_TOKEN fehlt oder hat kein gültiges Headerformat.")
    anfrage = urllib.request.Request(url, headers={
        "accept": "application/vnd.github+json",
        "authorization": f"Bearer {token}",
        "user-agent": "franksfinanzcheck-worker-environment-guard/1.0",
        "x-github-api-version": API_VERSION,
    })
    opener = urllib.request.build_opener(_KeineWeiterleitung())
    try:
        with opener.open(anfrage, timeout=timeout) as antwort:
            roh = antwort.read(MAX_BODY + 1)
            status = int(getattr(antwort, "status", 200))
            kopf = dict(antwort.headers.items())
    except urllib.error.HTTPError as fehler:
        status = int(fehler.code)
        kopf = dict(fehler.headers.items()) if fehler.headers else {}
        fehler.close()
        return status, kopf, b""
    except (urllib.error.URLError, OSError, TimeoutError, ValueError) as fehler:
        # Keine Exception-/Response-Texte ausgeben: sie können fremde Header
        # oder Transportdetails enthalten. Der konkrete Typ reicht zur Triage.
        raise ApiFehler(
            f"GitHub-Environment ist nicht erreichbar ({type(fehler).__name__}); "
            "Freigabe und Branch-Policy sind nicht nachgewiesen."
        ) from None
    if len(roh) > MAX_BODY:
        raise ApiFehler("GitHub-Antwort überschreitet das sichere Größenlimit.")
    return status, kopf, roh


def _json_holen(url: str, token: str, *, repo: str, policies: bool,
                holen: Callable | None = None) -> tuple[dict, Mapping[str, str]]:
    if holen is None:
        status, kopf, roh = _api_roh(url, token, repo=repo, policies=policies)
    else:
        # Der injizierte Transport ist ausschließlich eine lokale Testgrenze;
        # Produktionsaufrufe benutzen immer den fest verankerten _api_roh.
        status, kopf, roh = holen(url, token)
    if status != 200:
        if not policies and status == 404:
            raise PruefFehler(
                f"GitHub-Environment `{ENVIRONMENT}` fehlt. Es muss vor dem Deploy "
                "explizit mit Required Reviewer und Branch-Regel `main` eingerichtet werden."
            )
        if status in (401, 403):
            raise ApiFehler(
                f"GitHub-Environment-Policy ist nicht lesbar (HTTP {status}); "
                "dem Workflow-Token fehlt möglicherweise `actions: read`. Kein Deploy freigegeben."
            )
        raise ApiFehler(f"GitHub-Environment-Policy ist nicht belegbar (HTTP {status}).")
    try:
        daten = json.loads(roh.decode("utf-8"))
    except (UnicodeError, ValueError):
        raise ApiFehler("GitHub-Environment-API lieferte kein gültiges JSON.") from None
    if not isinstance(daten, dict):
        raise ApiFehler("GitHub-Environment-API lieferte kein JSON-Objekt.")
    return daten, kopf


def _naechste_seite(link_kopf: str | None, *, aktuelle_url: str, repo: str) -> str | None:
    """Liest ausschließlich `rel=next` auf exakt derselben Policy-API-Route."""
    if not link_kopf:
        return None
    for ziel, rel in NEXT_LINK_RE.findall(str(link_kopf)):
        if rel.lower() != "next":
            continue
        absolut = urllib.parse.urljoin(aktuelle_url, ziel)
        _api_url_pruefen(absolut, repo=repo, policies=True)
        return absolut
    return None


def _branch_policies_holen(repo: str, token: str, *, holen: Callable | None = None) -> list[dict]:
    basis = f"{API}/repos/{repo}/environments/{ENVIRONMENT}/deployment-branch-policies"
    url = basis + "?per_page=100"
    gesehen: set[str] = set()
    gesammelt: list[dict] = []
    erwartet: int | None = None
    for _ in range(MAX_PAGES):
        if url in gesehen:
            raise ApiFehler("GitHub-Branch-Policy liefert eine wiederholte Paginierungsseite.")
        gesehen.add(url)
        daten, kopf = _json_holen(url, token, repo=repo, policies=True, holen=holen)
        gesamt = daten.get("total_count")
        if not isinstance(gesamt, int) or isinstance(gesamt, bool) or gesamt < 0:
            raise ApiFehler("GitHub-Branch-Policy liefert keinen gültigen `total_count`.")
        if erwartet is None:
            erwartet = gesamt
        elif gesamt != erwartet:
            raise ApiFehler("GitHub-Branch-Policy `total_count` ändert sich zwischen Seiten.")
        regeln = daten.get("branch_policies")
        if not isinstance(regeln, list) or any(not isinstance(r, dict) for r in regeln):
            raise ApiFehler("GitHub-Branch-Policy hat kein gültiges `branch_policies`-Format.")
        gesammelt.extend(regeln)
        link = next((v for k, v in kopf.items() if str(k).lower() == "link"), None)
        url = _naechste_seite(link, aktuelle_url=url, repo=repo) or ""
        if not url:
            if len(gesammelt) != erwartet:
                raise ApiFehler(
                    "GitHub-Branch-Policy ist unvollständig: `total_count` und gelesene Regeln weichen ab."
                )
            return gesammelt
    raise ApiFehler(f"GitHub-Branch-Policy überschreitet das Seitenlimit ({MAX_PAGES}).")


def _reviewer_gueltig(eintrag: object) -> bool:
    """Akzeptiert nur echte GitHub-User-/Team-Referenzen mit positiver ID."""
    if not isinstance(eintrag, dict) or eintrag.get("type") not in {"User", "Team"}:
        return False
    ziel = eintrag.get("reviewer")
    ident = (ziel.get("id", eintrag.get("id"))
             if isinstance(ziel, dict) else eintrag.get("id"))
    return isinstance(ident, int) and not isinstance(ident, bool) and ident > 0


def abweichungen(environment: object, branch_policies: object) -> list[str]:
    """Validiert die minimale, tatsächlich wirksame Produktionsfreigabe."""
    if not isinstance(environment, dict):
        return ["GitHub-Environment-Antwort hat kein Objektformat."]
    gruende: list[str] = []

    regeln = environment.get("protection_rules")
    if not isinstance(regeln, list) or any(not isinstance(r, dict) for r in regeln):
        gruende.append("Protection Rules sind nicht lesbar; Required Reviewer nicht nachgewiesen.")
    else:
        reviewer_regeln = [r for r in regeln if r.get("type") == "required_reviewers"]
        if not reviewer_regeln:
            gruende.append("Required Reviewer fehlt.")
        elif len(reviewer_regeln) != 1:
            gruende.append("Required Reviewer-Regel ist mehrdeutig.")
        else:
            reviewer = reviewer_regeln[0].get("reviewers")
            if not isinstance(reviewer, list) or not reviewer:
                gruende.append("Required Reviewer-Regel enthält keinen Reviewer.")
            elif any(not _reviewer_gueltig(e) for e in reviewer):
                gruende.append("Required Reviewer-Liste enthält einen ungültigen Eintrag.")

    if environment.get("can_admins_bypass") is not False:
        gruende.append("Administrator-Bypass ist aktiv oder nicht belegbar; auf `false` setzen.")

    policy = environment.get("deployment_branch_policy")
    if not isinstance(policy, dict):
        gruende.append("Deployment-Branch-Policy fehlt; aktuell ist kein Branch eingeschränkt.")
    elif policy.get("protected_branches") is not False or policy.get("custom_branch_policies") is not True:
        gruende.append("Deployment-Branch-Policy muss explizit `Selected branches and tags` verwenden.")
    else:
        if not isinstance(branch_policies, list) or any(not isinstance(p, dict) for p in branch_policies):
            gruende.append("Ausgewählte Deployment-Branches sind nicht lesbar; `main` nicht nachgewiesen.")
        else:
            nur_main = (
                len(branch_policies) == 1
                and branch_policies[0].get("name") == "main"
                and branch_policies[0].get("type") == "branch"
            )
            if not nur_main:
                sichtbare = [
                    f"{p.get('name', '?')} ({p.get('type', 'Typ unbekannt')})"
                    for p in branch_policies
                ]
                gruende.append(
                    "Deployment-Policy muss genau den Branch `main` enthalten; aktuell: "
                    + (", ".join(sichtbare) if sichtbare else "keine Regeln") + "."
                )
    return gruende


def _einstellungen_holen(repo: str, token: str, *, holen: Callable | None = None) -> tuple[dict, list[dict] | None]:
    basis = f"{API}/repos/{repo}/environments/{ENVIRONMENT}"
    environment, _kopf = _json_holen(basis, token, repo=repo, policies=False, holen=holen)
    policy = environment.get("deployment_branch_policy")
    if (isinstance(policy, dict) and policy.get("protected_branches") is False
            and policy.get("custom_branch_policies") is True):
        branch_policies = _branch_policies_holen(repo, token, holen=holen)
    else:
        branch_policies = None
    return environment, branch_policies


def pruefen(umgebung: Mapping[str, str] | None = None, *, holen: Callable | None = None) -> list[str]:
    umgebung = os.environ if umgebung is None else umgebung
    repo = _repo_pruefen(umgebung.get("GITHUB_REPOSITORY", ""))
    token = (umgebung.get("GITHUB_TOKEN") or umgebung.get("GH_TOKEN") or "").strip()
    if not token:
        raise ApiFehler("GITHUB_TOKEN fehlt; die Produktions-Policy ist nicht nachgewiesen.")
    environment, policies = _einstellungen_holen(repo, token, holen=holen)
    return abweichungen(environment, policies)


def _selbsttest() -> int:
    reviewer = {"type": "User", "reviewer": {"id": 42, "login": "owner"}}
    korrekt = {
        "protection_rules": [{"type": "required_reviewers", "reviewers": [reviewer]}],
        "can_admins_bypass": False,
        "deployment_branch_policy": {"protected_branches": False, "custom_branch_policies": True},
    }
    policy_main = [{"name": "main", "type": "branch"}]
    if abweichungen(korrekt, policy_main):
        print("❌ Selbsttest: sichere Produktions-Policy wurde abgewiesen.")
        return 2
    faelle = [
        ({"protection_rules": [], "can_admins_bypass": True, "deployment_branch_policy": None}, None,
         ("Required Reviewer fehlt", "Administrator-Bypass", "Branch-Policy fehlt")),
        ({**korrekt, "protection_rules": [{"type": "required_reviewers", "reviewers": []}]}, policy_main,
         ("enthält keinen Reviewer",)),
        ({**korrekt, "can_admins_bypass": True}, policy_main, ("Administrator-Bypass",)),
        ({**korrekt, "deployment_branch_policy": {"protected_branches": True,
                                                     "custom_branch_policies": False}}, None,
         ("Selected branches and tags",)),
        (korrekt, [{"name": "main", "type": "branch"}, {"name": "release/*", "type": "branch"}],
         ("genau den Branch `main`",)),
        (korrekt, [{"name": "main", "type": "tag"}], ("genau den Branch `main`",)),
        (korrekt, None, ("nicht lesbar",)),
    ]
    for environment, policies, erwartet in faelle:
        fehler = abweichungen(environment, policies)
        if not all(any(nadel in f for f in fehler) for nadel in erwartet):
            print("❌ Selbsttest: erwartete Abweichung fehlt: " + ", ".join(erwartet))
            return 2
    print(f"✅ SELBSTTEST OK — sichere Policy akzeptiert, {len(faelle)} unsichere/unklare Zustände fail-closed erkannt.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prüft die GitHub-Produktionsfreigabe vor Worker-Secrets.")
    gruppe = parser.add_mutually_exclusive_group()
    gruppe.add_argument("--selftest", action="store_true", help="Sabotage- und Gegenproben ohne Netz")
    gruppe.add_argument("--check", action="store_true", help="GitHub-Environment read-only live prüfen")
    args = parser.parse_args(argv)
    if args.selftest:
        return _selbsttest()
    try:
        gruende = pruefen()
    except PruefFehler as fehler:
        annotation("error", str(fehler), titel="Cloudflare-Produktionsfreigabe nicht nachgewiesen")
        return fehler.exit_code
    if gruende:
        ziel = f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', '')}/settings/environments/{ENVIRONMENT}"
        meldung = (f"Environment `{ENVIRONMENT}` ist nicht deploy-sicher: " + " ".join(gruende)
                   + f" Settings: {ziel}"
                   + " Deploy bleibt vor dem Zugriff auf Cloudflare-Secrets gesperrt.")
        annotation("error", meldung, titel="Cloudflare-Produktionsfreigabe unsicher")
        return 1
    annotation("notice", f"Environment `{ENVIRONMENT}`: Reviewer, ausschließlich `main` und Admin-Bypass-Sperre nachgewiesen.",
               titel="Cloudflare-Produktionsfreigabe")
    return 0


if __name__ == "__main__":
    sys.exit(main())
