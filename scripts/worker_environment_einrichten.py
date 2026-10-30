#!/usr/bin/env python3
"""worker_environment_einrichten.py – das Produktions-Environment herstellen, nicht nur beschreiben.

WARUM (WF-829B / #922, 30.10.2026)
----------------------------------
`worker_environment_guard.py` bricht den Worker-Deploy fail-closed ab, wenn das
Environment `cloudflare-produktion` nicht mit einem Required Reviewer, exakt dem
Branch `main` und ohne Administrator-Bypass eingerichtet ist. Seit dem
25.10.2026 ist genau das der Befund: GitHub legt ein Environment beim ersten
Verweis aus einem Workflow AUTOMATISCH und ungesichert an
(`can_admins_bypass: true`, keine Protection Rules, keine Branch-Policy), und
im Repo existierte kein Weg, diesen Zustand zu beenden – nur einer, ihn zu
melden. Das Gate ist damit eine Prüfung ohne Heilpfad: Jeder Deploy war rot,
und die einzige Antwort war ein Rat in Prosa.

Dieses Werkzeug ist der Heilpfad. Es führt den Zielzustand herbei, soweit eine
GitHub-API ihn überhaupt zulässt, und sagt über den Rest die Wahrheit:

  · `reviewer`   – Required Reviewer                    → per API setzbar
  · `branch`     – exakt der Branch `main`              → per API setzbar
  · `bypass`     – kein Administrator-Bypass            → NUR im Dashboard

Die dritte Spalte ist keine Unlust, sondern eine Grenze der Schnittstelle: Die
REST-Route „Create or update an environment" nimmt ausschließlich `wait_timer`,
`prevent_self_review`, `reviewers` und `deployment_branch_policy` an
(`additionalProperties: false`, geprüft gegen die veröffentlichte
OpenAPI-Beschreibung der GitHub-REST-API), und die GraphQL-Mutation
`updateEnvironment` kennt `can_admins_bypass` nicht. Ein Werkzeug, das hier
„eingerichtet" meldet, würde den Deploy freigeben, den das Gate zu Recht
blockiert. Es meldet deshalb „eingerichtet bis auf einen Schalter" – mit dem
Link dorthin.

GRUNDSATZ: DIESES SKRIPT VERSCHÄRFT NUR, ES LOCKERT NIE.
  · Es entfernt keinen Reviewer und löscht keine Branch-Regel (kein DELETE).
  · Es ergänzt einen fehlenden Reviewer, statt eine Liste zu ersetzen.
  · Es setzt keine `wait_timer`- und keine `prevent_self_review`-Werte: Beides
    ist eine Betriebsentscheidung eines Menschen, nicht eine Lücke.
  · Es liest und schreibt ausschließlich api.github.com, folgt keinen
    Weiterleitungen und gibt kein Token, keinen Antworttext und keinen Header
    aus – nur Klassen, HTTP-Status und feste Satztemplate.

Bedienung:
    python3 scripts/worker_environment_einrichten.py --pruefen [--json] [--md PFAD]
    python3 scripts/worker_environment_einrichten.py --anwenden [--reviewer LOGIN|-id ID]
    python3 scripts/worker_environment_einrichten.py --inventur [--md PFAD]
    python3 scripts/worker_environment_einrichten.py --selftest

Exit: 0 = Zielzustand belegt · 1 = Abweichung belegt (fail-closed) ·
2 = nicht belegbar (Netz/API/Rechte beim Lesen).
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
from typing import Callable, NamedTuple

from github_kommando import annotation

import worker_environment_guard as guard

API = "https://api.github.com"
API_VERSION = "2022-11-28"
UMGEBUNG = guard.ENVIRONMENT
ZWEIG = "main"
MAX_BODY = 1_000_000
MAX_SEITEN = 20

REPO_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$")
LOGIN_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
NEXT_LINK_RE = re.compile(r"<([^<>]+)>\s*;\s*rel=\"?([^\";, ]+)\"?")

# Erlaubte Ziele der GitHub-API. Alles andere wird abgewiesen, bevor ein Paket
# das Haus verlässt – die Liste ist die einzige Stelle, an der dieses Skript
# überhaupt Netz spricht.
PFAD_UMGEBUNG = re.compile(r"^/repos/(?P<repo>[^/]+/[^/]+)/environments/(?P<name>[^/]+)$")
PFAD_LISTE = re.compile(r"^/repos/(?P<repo>[^/]+/[^/]+)/environments$")
PFAD_REGELN = re.compile(
    r"^/repos/(?P<repo>[^/]+/[^/]+)/environments/(?P<name>[^/]+)/deployment-branch-policies$")
PFAD_NUTZER = re.compile(r"^/users/(?P<login>[^/]+)$")

SCHREIBEN_ERLAUBT = {("PUT", "umgebung"), ("POST", "regeln")}

# Zuordnung der Abweichungstexte des Gates auf ein Ziel. Der Text kommt aus
# `worker_environment_guard.abweichungen` – EINE Quelle der Wahrheit. Fällt ein
# Text heraus, den diese Tabelle nicht kennt, ist das ein offener Befund
# (Klasse UNBEKANNT) und kein stillschweigendes „machbar".
ZUORDNUNG = (
    # Kein Ziel, sondern ein unlesbarer Zustand: Dann ist KEINES der Ziele belegt.
    ("antwort", ("GitHub-Environment-Antwort",)),
    ("bypass", ("Administrator-Bypass",)),
    ("reviewer", ("Required Reviewer", "Protection Rules")),
    ("branch", ("Branch-Policy", "Branch `main`", "Deployment-Branches", "Deployment-Policy")),
)
ZIELE = ("reviewer", "bypass", "branch")

KLASSE_ERFUELLT = "ERFUELLT"
KLASSE_MACHBAR = "MACHBAR"
KLASSE_OBERFLAECHE = "OBERFLAECHE"
KLASSE_RECHT = "RECHT"
KLASSE_ABWEICHUNG = "ABWEICHUNG"
KLASSE_UNBEKANNT = "UNBEKANNT"
KLASSE_OFFEN = "OFFEN"

MASSNAHME = {
    "reviewer": (
        "Automatisch setzbar: `python3 scripts/worker_environment_einrichten.py "
        "--anwenden` (ergänzt den fehlenden Reviewer, bestehende bleiben stehen)."
    ),
    "branch": (
        "Automatisch setzbar: `python3 scripts/worker_environment_einrichten.py "
        "--anwenden` (Branch-Auswahl auf `Selected branches and tags` und Regel `main`)."
    ),
    "bypass": (
        "Nur im Dashboard: Settings → Environments → `cloudflare-produktion` → "
        "„Allow administrators to bypass configured protection rules“ AUS. Keine "
        "GitHub-API nimmt dieses Feld an (REST: `additionalProperties: false`; "
        "GraphQL `updateEnvironment` kennt es nicht)."
    ),
    "unbekannt": (
        "Nicht automatisch gesetzt: zuerst von Hand im Dashboard prüfen, danach "
        "`--pruefen` erneut ausführen."
    ),
}

ZIEL_TEXT = {
    "reviewer": "Required Reviewer",
    "branch": "Branch-Regel exakt `main`",
    "bypass": "Kein Administrator-Bypass",
}


class WerkzeugFehler(RuntimeError):
    """Der Zustand ist nicht belegbar – ungeprüft ist nicht sauber (C34)."""

    exit_code = 2


class BefundFehler(RuntimeError):
    """Der Zustand ist belegt und weicht ab – fail-closed."""

    exit_code = 1


class _KeineWeiterleitung(urllib.request.HTTPRedirectHandler):
    """GitHub-Tokens niemals an ein Weiterleitungsziel weiterreichen."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.URLError("Weiterleitung der GitHub-API wird abgelehnt")


def _art(url: str, repo: str) -> tuple[str, dict]:
    """Prüft ein Ziel gegen die erlaubten Endpunkte und liefert (Art, Felder)."""
    teile = urllib.parse.urlsplit(url)
    if (teile.scheme != "https" or teile.netloc.lower() != "api.github.com"
            or teile.username is not None or teile.password is not None or teile.fragment):
        raise WerkzeugFehler("Unsicheres GitHub-API-Ziel wurde abgewiesen.")
    for art, muster in (("umgebung", PFAD_UMGEBUNG), ("liste", PFAD_LISTE),
                        ("regeln", PFAD_REGELN), ("nutzer", PFAD_NUTZER)):
        treffer = muster.fullmatch(teile.path)
        if not treffer:
            continue
        felder = treffer.groupdict()
        if "repo" in felder and felder["repo"] != repo:
            raise WerkzeugFehler("GitHub-API-Ziel außerhalb dieses Repositories wurde abgewiesen.")
        if "name" in felder and felder["name"] != UMGEBUNG:
            raise WerkzeugFehler(
                f"Nur das Environment `{UMGEBUNG}` darf berührt werden.")
        if art == "nutzer" and not LOGIN_RE.fullmatch(felder["login"]):
            raise WerkzeugFehler("Ungültiger GitHub-Anmeldename für die Reviewer-Auflösung.")
        parameter = urllib.parse.parse_qs(teile.query, keep_blank_values=True)
        if art in ("liste", "regeln"):
            if set(parameter) - {"per_page", "page"}:
                raise WerkzeugFehler("Nicht erlaubte GitHub-API-Parameter wurden abgewiesen.")
            if parameter.get("per_page", ["100"]) != ["100"]:
                raise WerkzeugFehler("Listen der GitHub-API müssen vollständig paginiert werden.")
            if "page" in parameter:
                try:
                    if len(parameter["page"]) != 1 or int(parameter["page"][0]) < 1:
                        raise ValueError
                except ValueError:
                    raise WerkzeugFehler("Ungültige GitHub-API-Seitennummer.") from None
        elif parameter:
            raise WerkzeugFehler("Dieser GitHub-API-Endpunkt darf keine Parameter tragen.")
        return art, felder
    raise WerkzeugFehler("Nicht erlaubter GitHub-API-Pfad wurde abgewiesen.")


def _senden(methode: str, url: str, token: str, *, repo: str,
            koerper: dict | None = None, timeout: float = 20.0,
            transport: Callable | None = None) -> tuple[int, dict, bytes]:
    """Ein Aufruf. `transport` ist ausschließlich eine lokale Testgrenze."""
    if methode not in ("GET", "PUT", "POST"):
        raise WerkzeugFehler(f"Nicht erlaubte HTTP-Methode: {methode}.")
    art, _ = _art(url, repo=repo)
    if methode != "GET" and (methode, art) not in SCHREIBEN_ERLAUBT:
        raise WerkzeugFehler(f"{methode} ist auf diesem Endpunkt nicht erlaubt.")
    if koerper is not None and methode == "GET":
        raise WerkzeugFehler("Ein lesender Aufruf darf keinen Körper tragen.")
    try:
        if transport is not None:
            status, kopf, roh = transport(methode, url, token, koerper)
        else:
            daten = json.dumps(koerper).encode("utf-8") if koerper is not None else None
            anfrage = urllib.request.Request(url, data=daten, method=methode, headers={
                "accept": "application/vnd.github+json",
                "authorization": f"Bearer {token}",
                "content-type": "application/json",
                "user-agent": "franksfinanzcheck-worker-environment-einrichten/1.0",
                "x-github-api-version": API_VERSION,
            })
            opener = urllib.request.build_opener(_KeineWeiterleitung())
            with opener.open(anfrage, timeout=timeout) as antwort:
                status = int(getattr(antwort, "status", 200))
                kopf = dict(antwort.headers.items())
                roh = antwort.read(MAX_BODY + 1)
    except urllib.error.HTTPError as fehler:
        status = int(fehler.code)
        kopf = dict(fehler.headers.items()) if fehler.headers else {}
        fehler.close()
        roh = b""
    except (urllib.error.URLError, OSError, TimeoutError, ValueError) as fehler:
        # Keine Exception-Texte ausgeben: Sie können fremde Transport- oder
        # Header-Details tragen. Der Typ genügt für die Einordnung.
        raise WerkzeugFehler(
            f"GitHub-Environment ist nicht erreichbar ({type(fehler).__name__}); "
            "der Einrichtungsstand ist nicht belegbar."
        ) from None
    if len(roh) > MAX_BODY:
        raise WerkzeugFehler("GitHub-Antwort überschreitet das sichere Größenlimit.")
    return status, kopf, roh


def _json_lesen(status: int, roh: bytes, *, art: str) -> object:
    if status != 200:
        raise WerkzeugFehler(_status_text(status, art))
    try:
        return json.loads(roh.decode("utf-8"))
    except (UnicodeError, ValueError):
        raise WerkzeugFehler("GitHub-API lieferte kein gültiges JSON.") from None


def _status_text(status: int, art: str) -> str:
    """Feste Satztemplate je Status – keine fremden Antworttexte im Log."""
    if status in (401, 403):
        return (
            f"GitHub-API verweigert den Zugriff (HTTP {status}). Dem Token fehlt das Recht, "
            f"Environments zu {'schreiben' if art == 'schreiben' else 'lesen'} "
            "(feingranular: `Environments: read/write`, klassisch: `repo`/"
            "`administration`). Das ist ein Rechtebefund, keine Code-Regression – "
            "die Einrichtung bleibt eine Inhaber-Aufgabe."
        )
    if status == 404:
        return (
            f"GitHub-Environment `{UMGEBUNG}` ist nicht erreichbar (HTTP 404). "
            "Es wird mit `--anwenden` mitsamt Reviewer und Branch-Regel angelegt."
        )
    return f"GitHub-API antwortete mit HTTP {status}; der Stand ist nicht belegbar."


def _token(umgebung: Mapping | None = None) -> str:
    """Liest das Token, ohne es jemals auszugeben."""
    quelle = os.environ if umgebung is None else umgebung
    wert = (quelle.get("GITHUB_TOKEN") or quelle.get("GH_TOKEN") or "").strip()
    if not wert or any(ord(c) < 33 or ord(c) > 126 for c in wert):
        raise WerkzeugFehler("GITHUB_TOKEN/GH_TOKEN fehlt oder hat kein gültiges Headerformat.")
    return wert


def _repo(umgebung: Mapping | None = None) -> str:
    quelle = os.environ if umgebung is None else umgebung
    wert = str(quelle.get("GITHUB_REPOSITORY", "")).strip()
    if not REPO_RE.fullmatch(wert):
        raise WerkzeugFehler("GITHUB_REPOSITORY fehlt oder hat kein gültiges owner/repo-Format.")
    return wert


class Lage(NamedTuple):
    """Ein Ziel des Environments mit seinem Stand."""

    ziel: str
    klasse: str
    text: str
    massnahme: str

    def als_dict(self) -> dict:
        return {"ziel": self.ziel, "klasse": self.klasse,
                "text": self.text, "massnahme": self.massnahme}


def zuordnen(abweichung: str) -> str:
    """Ordnet eine Abweichung des Gates einem Ziel zu – sonst UNBEKANNT."""
    for ziel, begriffe in ZUORDNUNG:
        if any(begriff in abweichung for begriff in begriffe):
            return ziel
    return "unbekannt"


def planen(umgebung: dict, regeln: list | None) -> list[Lage]:
    """Übersetzt den gemessenen Stand in eine Lage je Ziel.

    Die Bewertung selbst kommt aus `worker_environment_guard.abweichungen` –
    dieses Skript erfindet keine zweite Wahrheit, es übersetzt sie nur in
    Ziele und machbare Schritte.
    """
    abweichungen = guard.abweichungen(umgebung, regeln)
    gefunden: dict[str, list[str]] = {ziel: [] for ziel in ZIELE}
    unbekannt: list[str] = []
    for text in abweichungen:
        ziel = zuordnen(text)
        if ziel in gefunden:
            gefunden[ziel].append(text)
        else:
            unbekannt.append(text)

    lagen: list[Lage] = []
    for ziel in ZIELE:
        texte = gefunden[ziel]
        if not texte:
            lagen.append(Lage(ziel, KLASSE_ERFUELLT,
                              f"{ZIEL_TEXT[ziel]}: belegt.", ""))
            continue
        klasse = KLASSE_OBERFLAECHE if ziel == "bypass" else KLASSE_MACHBAR
        lagen.append(Lage(ziel, klasse, " ".join(texte), MASSNAHME[ziel]))
    if unbekannt:
        grund = " ".join(unbekannt)
        lagen = [Lage(l.ziel, KLASSE_OFFEN, f"Nicht belegbar: {grund}", MASSNAHME["unbekannt"])
                 if l.klasse == KLASSE_ERFUELLT else l for l in lagen]
    for text in unbekannt:
        lagen.append(Lage("unbekannt", KLASSE_UNBEKANNT, text, MASSNAHME["unbekannt"]))
    return lagen


def _reviewer_id(eintrag: object) -> int | None:
    """ID eines Reviewer-Eintrags – gleichermaßen für Lese- und Schreibform.

    Die API liest Reviewer als `{"type": …, "reviewer": {"id": …}}` und
    schreibt sie als `{"type": …, "id": …}`. Beide Formen zählen hier als
    derselbe Reviewer, sonst würde ein Durchlauf denselben Menschen doppelt
    eintragen.
    """
    if not isinstance(eintrag, dict):
        return None
    ziel = eintrag.get("reviewer", eintrag)
    if not isinstance(ziel, dict):
        return None
    ident = ziel.get("id")
    if isinstance(ident, int) and not isinstance(ident, bool) and ident > 0:
        return ident
    return None


def _reviewer_gueltig(eintrag: object) -> bool:
    """Ein Reviewer ist eine echte User-/Team-Referenz mit positiver ID.

    Dieselbe Grenze wie im Gate, hier noch einmal formuliert: Dieses Skript
    greift bewusst nicht in das Gate ein, sondern prüft vor jedem Schreiben
    selbst, was es fortschreibt.
    """
    if not isinstance(eintrag, dict) or eintrag.get("type") not in ("User", "Team"):
        return False
    return _reviewer_id(eintrag) is not None


def _reviewer(umgebung: dict) -> list[dict]:
    """Bestehende, gültige Reviewer-Einträge in Schreibform (ergänzt, nie ersetzt)."""
    regeln = umgebung.get("protection_rules")
    if not isinstance(regeln, list):
        return []
    eintraege: list[dict] = []
    for regel in regeln:
        if not isinstance(regel, dict) or regel.get("type") != "required_reviewers":
            continue
        liste = regel.get("reviewers")
        if not isinstance(liste, list):
            continue
        for eintrag in liste:
            if not _reviewer_gueltig(eintrag):
                continue
            eintraege.append({"type": eintrag.get("type"), "id": _reviewer_id(eintrag)})
    return eintraege


def nutzer_id(login: str, *, repo: str, token: str,
              transport: Callable | None = None) -> int:
    """Löst einen Anmeldenamen in eine Reviewer-ID auf (ein Aufruf, lesend)."""
    status, _kopf, roh = _senden("GET", f"{API}/users/{urllib.parse.quote(login)}",
                                 token, repo=repo, transport=transport)
    daten = _json_lesen(status, roh, art="lesen")
    if not isinstance(daten, dict):
        raise WerkzeugFehler("GitHub-API lieferte kein Nutzer-Objekt.")
    ident = daten.get("id")
    if not isinstance(ident, int) or isinstance(ident, bool) or ident <= 0:
        raise WerkzeugFehler("GitHub-API lieferte keine gültige Nutzer-ID.")
    return ident


def schreiben(lagen: list[Lage], umgebung: dict | None, *, repo: str, token: str,
              reviewer_id: int | None, transport: Callable | None = None,
              melden: Callable[[str], None] | None = None) -> tuple[list[Lage], list[str]]:
    """Wendet an, was die API zulässt. Liefert (Rest-Lage, ausgeführte Schritte).

    Verschärft nur: kein DELETE, keine Ersetzung bestehender Reviewer, keine
    Änderung von `wait_timer`/`prevent_self_review`.
    """
    sagen = melden or (lambda text: None)
    schritte: list[str] = []
    rest: list[Lage] = list(lagen)

    def klasse(ziel: str) -> str | None:
        return next((l.klasse for l in lagen if l.ziel == ziel), None)

    if klasse("reviewer") == KLASSE_MACHBAR and reviewer_id is None:
        raise WerkzeugFehler(
            "Required Reviewer fehlt, aber es ist keine Reviewer-ID bekannt. "
            "`--reviewer <login>` oder `--reviewer-id <id>` übergeben "
            "(im Workflow: `github.repository_owner_id`)."
        )

    fehlend = klasse("branch") == KLASSE_MACHBAR or klasse("reviewer") == KLASSE_MACHBAR
    neu = umgebung is None
    if not fehlend and not neu:
        return rest, schritte

    koerper: dict = {}
    if klasse("reviewer") == KLASSE_MACHBAR:
        eintraege = _reviewer(umgebung) if umgebung else []
        if not any(e.get("id") == reviewer_id for e in eintraege):
            eintraege.append({"type": "User", "id": reviewer_id})
        koerper["reviewers"] = eintraege
    if klasse("branch") == KLASSE_MACHBAR:
        koerper["deployment_branch_policy"] = {
            "protected_branches": False,
            "custom_branch_policies": True,
        }
    if not koerper:
        return rest, schritte

    status, _kopf, roh = _senden("PUT", f"{API}/repos/{repo}/environments/{UMGEBUNG}",
                                 token, repo=repo, koerper=koerper, transport=transport)
    if status not in (200, 201):
        raise BefundFehler(_status_text(status, "schreiben"))
    _json_lesen(200, b"{}", art="schreiben")
    sagen("PUT Environment: " + (", ".join(sorted(koerper)) or "nichts"))
    schritte.append("Environment `" + UMGEBUNG + "` geschrieben: " + ", ".join(sorted(koerper)))

    if klasse("branch") == KLASSE_MACHBAR:
        status, _kopf, _roh = _senden(
            "POST", f"{API}/repos/{repo}/environments/{UMGEBUNG}/deployment-branch-policies",
            token, repo=repo, koerper={"name": ZWEIG, "type": "branch"}, transport=transport)
        if status not in (200, 201):
            raise BefundFehler(_status_text(status, "schreiben"))
        schritte.append(f"Branch-Regel `{ZWEIG}` ergänzt.")

    rest = [l for l in lagen if l.klasse not in (KLASSE_MACHBAR,)]
    return rest, schritte


def stand(repo: str, token: str, *, transport: Callable | None = None
          ) -> tuple[dict | None, list | None]:
    """Liest Environment und Branch-Regeln. (None, None) = Environment fehlt."""
    status, _kopf, roh = _senden("GET", f"{API}/repos/{repo}/environments/{UMGEBUNG}",
                                 token, repo=repo, transport=transport)
    if status == 404:
        return None, None
    daten = _json_lesen(status, roh, art="lesen")
    if not isinstance(daten, dict):
        raise WerkzeugFehler("GitHub-API lieferte kein Environment-Objekt.")
    regeln: list | None = None
    policy = daten.get("deployment_branch_policy")
    if (isinstance(policy, dict) and policy.get("protected_branches") is False
            and policy.get("custom_branch_policies") is True):
        regeln = _regeln(repo, token, transport=transport)
    return daten, regeln


def _regeln(repo: str, token: str, *, transport: Callable | None = None) -> list:
    """Branch-Regeln vollständig paginiert lesen (ohne Lücke ist keine Regel belegt)."""
    url = f"{API}/repos/{repo}/environments/{UMGEBUNG}/deployment-branch-policies?per_page=100"
    gesehen: set[str] = set()
    gesammelt: list = []
    erwartet: int | None = None
    for _ in range(MAX_SEITEN):
        if url in gesehen:
            raise WerkzeugFehler("GitHub-Branch-Regeln liefern eine wiederholte Seite.")
        gesehen.add(url)
        status, kopf, roh = _senden("GET", url, token, repo=repo, transport=transport)
        daten = _json_lesen(status, roh, art="lesen")
        if not isinstance(daten, dict):
            raise WerkzeugFehler("GitHub-Branch-Regeln liefern kein Objekt.")
        gesamt = daten.get("total_count")
        if not isinstance(gesamt, int) or isinstance(gesamt, bool) or gesamt < 0:
            raise WerkzeugFehler("GitHub-Branch-Regeln liefern keinen gültigen `total_count`.")
        if erwartet is None:
            erwartet = gesamt
        elif gesamt != erwartet:
            raise WerkzeugFehler("`total_count` der Branch-Regeln ändert sich zwischen Seiten.")
        regeln = daten.get("branch_policies")
        if not isinstance(regeln, list):
            raise WerkzeugFehler("GitHub-Branch-Regeln haben kein gültiges Format.")
        gesammelt.extend(regeln)
        weiter = _naechste_seite(kopf.get("link") or kopf.get("Link"), url=url, repo=repo)
        if not weiter:
            if len(gesammelt) != erwartet:
                raise WerkzeugFehler(
                    "GitHub-Branch-Regeln sind unvollständig: `total_count` und "
                    "gelesene Regeln weichen ab.")
            return gesammelt
        url = weiter
    raise WerkzeugFehler(f"Branch-Regeln überschreiten das Seitenlimit ({MAX_SEITEN}).")


def _naechste_seite(link: str | None, *, url: str, repo: str) -> str | None:
    """Folgt ausschließlich `rel=next` auf derselben erlaubten Route."""
    if not link:
        return None
    for ziel, rel in NEXT_LINK_RE.findall(str(link)):
        if rel.lower() != "next":
            continue
        absolut = urllib.parse.urljoin(url, ziel)
        _art(absolut, repo=repo)
        return absolut
    return None


def inventur(repo: str, token: str, *, transport: Callable | None = None) -> list[dict]:
    """Alle Environments des Repositories mit ihrem Härtungsstand (ein Blick)."""
    url = f"{API}/repos/{repo}/environments?per_page=100"
    gesehen: set[str] = set()
    zeilen: list[dict] = []
    for _ in range(MAX_SEITEN):
        if url in gesehen:
            raise WerkzeugFehler("Environment-Liste liefert eine wiederholte Seite.")
        gesehen.add(url)
        status, kopf, roh = _senden("GET", url, token, repo=repo, transport=transport)
        daten = _json_lesen(status, roh, art="lesen")
        if not isinstance(daten, dict) or not isinstance(daten.get("environments"), list):
            raise WerkzeugFehler("GitHub-Environment-Liste hat kein gültiges Format.")
        for eintrag in daten["environments"]:
            if not isinstance(eintrag, dict):
                continue
            regeln = eintrag.get("protection_rules")
            reviewer = 0
            if isinstance(regeln, list):
                for regel in regeln:
                    if isinstance(regel, dict) and regel.get("type") == "required_reviewers":
                        liste = regel.get("reviewers")
                        if isinstance(liste, list):
                            reviewer += sum(1 for e in liste if _reviewer_gueltig(e))
            policy = eintrag.get("deployment_branch_policy")
            zeilen.append({
                "name": str(eintrag.get("name", "?")),
                "reviewer": reviewer,
                "bypass": eintrag.get("can_admins_bypass") is not False,
                "branch_policy": "custom" if isinstance(policy, dict)
                and policy.get("custom_branch_policies") is True
                else ("protected" if isinstance(policy, dict)
                      and policy.get("protected_branches") is True else "keine"),
            })
        weiter = _naechste_seite(kopf.get("link") or kopf.get("Link"), url=url, repo=repo)
        if not weiter:
            return sorted(zeilen, key=lambda z: z["name"])
        url = weiter
    raise WerkzeugFehler(f"Environment-Liste überschreitet das Seitenlimit ({MAX_SEITEN}).")


def als_md(lagen: list[Lage], *, schritte: list[str] | None = None,
           inventar: list[dict] | None = None) -> str:
    zeilen = ["## Produktions-Environment: Einrichtungsstand", "",
              f"- Environment: **{UMGEBUNG}**",
              f"- Ziel: Required Reviewer · exakt `{ZWEIG}` · kein Administrator-Bypass", ""]
    if schritte:
        zeilen += ["**Ausgeführt:**"] + [f"- {s}" for s in schritte] + [""]
    zeilen += ["| Ziel | Stand | Befund | Nächster Schritt |", "|---|---|---|---|"]
    for lage in lagen:
        zeilen.append(f"| {ZIEL_TEXT.get(lage.ziel, lage.ziel)} | {lage.klasse} | "
                      f"{lage.text} | {lage.massnahme or '–'} |")
    zeilen.append("")
    if inventar:
        zeilen += ["### Inventur aller Environments", "",
                   "| Environment | Reviewer | Admin-Bypass | Branch-Auswahl |",
                   "|---|---|---|---|"]
        for eintrag in inventar:
            zeilen.append(f"| `{eintrag['name']}` | {eintrag['reviewer']} | "
                          f"{'aus' if not eintrag['bypass'] else '**an**'} | "
                          f"{eintrag['branch_policy']} |")
        zeilen += ["", "Nur `cloudflare-produktion` ist hart verriegelt; die übrigen "
                       "Environments stehen hier zur Entscheidung, nicht zur automatischen "
                       "Härtung (ein Required Reviewer auf `github-pages` würde die "
                       "Veröffentlichung anhalten).", ""]
    return "\n".join(zeilen) + "\n"


def _ausgabe(text: str, md_pfad: str | None) -> None:
    print(text)
    if not md_pfad or md_pfad == "-":
        return
    try:
        with open(md_pfad, "a", encoding="utf-8") as fh:
            fh.write(text)
    except OSError as fehler:
        raise WerkzeugFehler(f"Bericht nicht schreibbar: {type(fehler).__name__}.") from None


def _selftest() -> int:
    """Sabotage- und Gegenproben OHNE Netz."""
    sicher = {
        "protection_rules": [{"type": "required_reviewers",
                              "reviewers": [{"type": "User", "reviewer": {"id": 42}}]}],
        "can_admins_bypass": False,
        "deployment_branch_policy": {"protected_branches": False,
                                     "custom_branch_policies": True},
    }
    regeln_main = [{"name": "main", "type": "branch"}]
    fehler: list[str] = []

    # 1 · Zielzustand: nichts offen, nichts machbar.
    lagen = planen(sicher, regeln_main)
    if [l for l in lagen if l.klasse != KLASSE_ERFUELLT]:
        fehler.append("1 Zielzustand wird nicht als erfüllt erkannt")

    # 2 · Der heutige Live-Stand: drei Ziele, zwei machbar, eines nur im Dashboard.
    lagen = planen({"protection_rules": [], "can_admins_bypass": True,
                    "deployment_branch_policy": None}, None)
    klassen = {l.ziel: l.klasse for l in lagen}
    if klassen != {"reviewer": KLASSE_MACHBAR, "bypass": KLASSE_OBERFLAECHE,
                   "branch": KLASSE_MACHBAR}:
        fehler.append(f"2 Live-Stand falsch eingeordnet: {klassen}")

    # 3 · Admin-Bypass ist NIE als machbar gekennzeichnet – die API kann ihn nicht.
    lagen = planen({**sicher, "can_admins_bypass": True}, regeln_main)
    if [l for l in lagen if l.ziel == "bypass" and l.klasse != KLASSE_OBERFLAECHE]:
        fehler.append("3 Admin-Bypass als machbar ausgegeben")

    # 4 · Endpunkt-Grenzen: fremder Host, fremder Pfad, verbotener Parameter.
    for ziel in ("https://example.invalid/x", "http://api.github.com/x",
                 f"{API}/repos/frank/x/environments/backup",
                 f"{API}/repos/frank/x/environments/{UMGEBUNG}?per_page=100",
                 f"{API}/users/has space"):
        try:
            _art(ziel, repo="frank/x")
            fehler.append(f"4 unsicheres Ziel durchgelassen: {ziel}")
        except WerkzeugFehler:
            pass

    # 5 · DELETE und PATCH sind ausgeschlossen; nur zwei Schreibwege existieren.
    for methode, url in (("DELETE", f"{API}/repos/frank/x/environments/{UMGEBUNG}"),
                         ("PATCH", f"{API}/repos/frank/x/environments/{UMGEBUNG}"),
                         ("PUT", f"{API}/repos/frank/x/environments/{UMGEBUNG}"
                                 "/deployment-branch-policies")):
        try:
            _senden(methode, url, "TOKEN", repo="frank/x")
            fehler.append(f"5 verbotener Schreibweg durchgelassen: {methode}")
        except WerkzeugFehler:
            pass

    # 6 · Schreiben verschärft nur: bestehender Reviewer bleibt, keiner fliegt raus,
    #     kein can_admins_bypass im Körper.
    gesendet: list[tuple[str, str, dict | None]] = []

    def transport(methode, url, token, koerper):
        gesendet.append((methode, url, koerper))
        if methode == "GET":
            if url.endswith("/deployment-branch-policies?per_page=100"):
                return 200, {}, json.dumps({"total_count": 0, "branch_policies": []}).encode()
            return 200, {}, json.dumps({"protection_rules": [], "can_admins_bypass": True,
                                        "deployment_branch_policy": None}).encode()
        return 200, {}, b"{}"

    # Zwei Required-Reviewer-Regeln: das Gate meldet „mehrdeutig" – ein echter
    # Mensch (ID 7) steht aber schon drin. Er darf beim Zusammenführen nicht
    # herausfallen; die Mehrdeutigkeit wird aufgelöst, nicht die Person entfernt.
    doppelt = {"protection_rules": [
        {"type": "required_reviewers", "reviewers": [{"type": "User", "reviewer": {"id": 7}}]},
        {"type": "required_reviewers", "reviewers": [{"type": "User", "reviewer": {"id": 8}}]},
    ], "can_admins_bypass": True, "deployment_branch_policy": None}
    lagen = planen(doppelt, None)
    if not any(l.ziel == "reviewer" and l.klasse == KLASSE_MACHBAR for l in lagen):
        fehler.append("6 mehrdeutige Reviewer-Regel nicht als machbar erkannt")
    rest, schritte = schreiben(lagen, doppelt, repo="frank/x", token="TOKEN",
                               reviewer_id=42, transport=transport)
    koerper = next((k for m, _u, k in gesendet if m == "PUT"), None)
    if not koerper:
        fehler.append("6 kein PUT gesendet")
    else:
        ids = {e.get("id") for e in koerper.get("reviewers", [])}
        if not {7, 8, 42} <= ids:
            fehler.append(f"6 bestehender Reviewer verloren: {ids}")
        if len(koerper.get("reviewers", [])) != len(ids):
            fehler.append("6 Reviewer doppelt eingetragen")
        if "can_admins_bypass" in json.dumps(koerper):
            fehler.append("6 can_admins_bypass im Schreibkörper")
    if [l for l in rest if l.ziel == "bypass" and l.klasse != KLASSE_OBERFLAECHE]:
        fehler.append("6 Admin-Bypass nach dem Schreiben verschwiegen")

    # 7 · Idempotenz: erfüllter Zustand sendet keinen Schreibaufruf.
    gesendet.clear()
    rest, schritte = schreiben(planen(sicher, regeln_main), sicher, repo="frank/x",
                               token="TOKEN", reviewer_id=42, transport=transport)
    if gesendet or schritte:
        fehler.append(f"7 nicht idempotent: {[m for m, _u, _k in gesendet]}")

    # 8 · Fehlender Reviewer OHNE ID ist ein Werkzeugfehler, kein Teilerfolg.
    try:
        schreiben(planen({"protection_rules": [], "can_admins_bypass": False,
                          "deployment_branch_policy": {"protected_branches": False,
                                                       "custom_branch_policies": True}},
                         regeln_main),
                  {"protection_rules": []}, repo="frank/x", token="TOKEN",
                  reviewer_id=None, transport=transport)
        fehler.append("8 fehlende Reviewer-ID wurde nicht gemeldet")
    except WerkzeugFehler:
        pass

    # 9 · HTTP 403 wird als Rechtebefund übersetzt – nie als Code-Fehler.
    def verweigert(methode, url, token, koerper):
        return 403, {}, b"{}"

    try:
        stand("frank/x", "TOKEN", transport=verweigert)
        fehler.append("9 HTTP 403 nicht als nicht belegbar gemeldet")
    except WerkzeugFehler as exc:
        if "Recht" not in str(exc):
            fehler.append("9 HTTP 403 ohne Rechte-Hinweis")

    # 10 · Kein Token und kein fremder Text im Bericht.
    text = als_md(planen({"protection_rules": [], "can_admins_bypass": True,
                          "deployment_branch_policy": None}, None))
    if "TOKEN" in text or "Bearer" in text:
        fehler.append("10 Geheimnis im Bericht")

    # 11 · Unlesbare Antwort: kein Ziel gilt als erfüllt (OFFEN ist nie grün).
    lagen = planen("kein Objekt", None)
    if [l.ziel for l in lagen if l.klasse == KLASSE_ERFUELLT]:
        fehler.append("11 unlesbare Antwort als erfüllt ausgewiesen")
    if not any(l.klasse == KLASSE_OFFEN for l in lagen):
        fehler.append("11 unlesbare Antwort ohne OFFEN-Klasse")
    if any(l.klasse == KLASSE_UNBEKANNT for l in lagen) is False:
        fehler.append("11 unlesbare Antwort ohne Befundzeile")

    if fehler:
        print("❌ Selbsttest: " + "; ".join(fehler))
        return 2
    print("✅ SELBSTTEST OK — Zuordnung, OFFEN ist nie grün, Endpunktgrenzen, "
          "Nur-Verschärfen, Idempotenz, Rechtebefund und Geheimnisfreiheit belegt.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Stellt die Produktionsfreigabe des Worker-Deploys her (nur verschärfend).")
    gruppe = ap.add_mutually_exclusive_group(required=True)
    gruppe.add_argument("--pruefen", action="store_true",
                        help="Einrichtungsstand lesen und je Ziel einordnen")
    gruppe.add_argument("--anwenden", action="store_true",
                        help="setzt, was die GitHub-API zulässt (idempotent)")
    gruppe.add_argument("--inventur", action="store_true",
                        help="alle Environments des Repositories auflisten")
    gruppe.add_argument("--selftest", action="store_true", help="Sabotage- und Gegenproben")
    ap.add_argument("--reviewer", help="Anmeldename des Required Reviewers")
    ap.add_argument("--reviewer-id", type=int, help="GitHub-ID des Required Reviewers")
    ap.add_argument("--warnstufe", action="store_true",
                    help="Befund als Warnung melden (Beobachtung statt Stopp)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--md", help="Bericht an diese Datei anhängen (oder '-')")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()

    try:
        repo = _repo()
        token = _token()
        if args.reviewer and args.reviewer_id:
            raise WerkzeugFehler("Entweder --reviewer oder --reviewer-id, nicht beides.")
        reviewer_id = args.reviewer_id
        if args.reviewer and not reviewer_id:
            reviewer_id = nutzer_id(args.reviewer, repo=repo, token=token)

        if args.inventur:
            inventar = inventur(repo, token)
            if args.json:
                print(json.dumps({"environment": UMGEBUNG, "inventar": inventar}, indent=2))
            else:
                _ausgabe(als_md([], inventar=inventar), args.md)
            offen = [i for i in inventar if i["bypass"] or not i["reviewer"]]
            if offen and not args.json:
                print(f"❌ {len(offen)} von {len(inventar)} Environments ohne "
                      "vollständige Härtung (Reviewer + kein Admin-Bypass).")
            return 1 if offen else 0

        umgebung, regeln = stand(repo, token)
        if umgebung is None:
            lagen = [Lage(ziel, KLASSE_MACHBAR,
                          f"Environment `{UMGEBUNG}` existiert nicht.",
                          MASSNAHME[ziel]) for ziel in ("reviewer", "branch")]
            lagen.append(Lage("bypass", KLASSE_OBERFLAECHE,
                              "Beim Anlegen ist der Administrator-Bypass der "
                              "Voreinstellung nach an.", MASSNAHME["bypass"]))
        else:
            lagen = planen(umgebung, regeln)

        schritte: list[str] = []
        if args.anwenden:
            lagen, schritte = schreiben(
                lagen, umgebung, repo=repo, token=token, reviewer_id=reviewer_id)
            if umgebung is None or any(s.startswith("Environment") or s.startswith("Branch")
                                       for s in schritte):
                umgebung, regeln = stand(repo, token)
                lagen = planen(umgebung, regeln) if umgebung else lagen
    except WerkzeugFehler as exc:
        annotation("error", str(exc), titel="Produktions-Environment nicht belegbar")
        return exc.exit_code
    except BefundFehler as exc:
        annotation("error", str(exc), titel="Produktions-Environment nicht einrichtbar")
        return exc.exit_code

    offen = [l for l in lagen if l.klasse != KLASSE_ERFUELLT]
    if args.json:
        print(json.dumps({"environment": UMGEBUNG, "lagen": [l.als_dict() for l in lagen],
                          "schritte": schritte, "offen": len(offen)}, indent=2))
        return 1 if offen else 0

    _ausgabe(als_md(lagen, schritte=schritte), args.md)
    for lage in offen:
        print(f"❌ [{lage.klasse}] {ZIEL_TEXT.get(lage.ziel, lage.ziel)}: {lage.text}")
        if lage.massnahme:
            print(f"   → {lage.massnahme}")
    if offen:
        # `--warnstufe` für die tägliche Beobachtung: Der harte Stopp liegt im
        # Deploy-Pfad (fail-closed). Wo nur sichtbar gemacht wird, darf die
        # Meldung nicht denselben Rotton tragen wie ein fehlgeschlagener Lauf.
        annotation("warning" if args.warnstufe else "error",
                   f"Environment `{UMGEBUNG}`: {len(offen)} Ziel(e) nicht erreicht – "
                   "der Deploy bleibt fail-closed gesperrt.",
                   titel="Produktions-Environment nicht deploy-sicher")
        return 1
    print(f"✅ Environment `{UMGEBUNG}`: Reviewer, exakt `{ZWEIG}` und kein "
          "Administrator-Bypass sind belegt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
