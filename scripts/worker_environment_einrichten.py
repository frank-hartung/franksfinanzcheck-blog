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

Dieses Werkzeug kann den leeren Ausgangszustand teilweise absichern und sagt
über den Rest die Wahrheit:

  · `reviewer`   – Required Reviewer                    → im leeren Zustand per API
  · `branch`     – exakt der Branch `main`              → im leeren Zustand per API
  · `bypass`     – kein Administrator-Bypass            → in diesem Werkzeug
                                                          nur im Dashboard

Die veröffentlichte REST-Spezifikation dokumentiert `can_admins_bypass` nicht
als Schreibparameter. Das belegt jedoch NICHT, dass die API das Feld generell
ablehnt: Andere Clients und externe Tests berichten von Unterstützung. Für
unser Repository und die verwendete API-Version ist das mangels Schreibrechten
nicht verifiziert. Dieses Werkzeug sendet das undokumentierte Feld daher nicht;
der Schalter wird im Dashboard gesetzt und anschließend vom Guard nachgemessen.
Ein offener oder unlesbarer Bypass wird niemals als eingerichtet gemeldet.

SCHREIBGRENZE: Nur ein nachweislich leeres, bestehendes Environment mit
aktivem Bypass und ohne Branch-Policy wird automatisch bearbeitet. Sobald eine
Schutzregel, ein abgeschalteter/unbekannter Bypass oder eine Branch-Policy
vorhanden ist, bleibt die Änderung beim Menschen. Ein zusätzlicher Reviewer
kann den Freigabekreis erweitern, da EINER der Reviewer genügt. Das Auslassen
von PUT-Feldern beweist nicht, dass GitHub sie in jeder API-Version erhält.
Vor dem PUT wird der Ausgangszustand erneut gelesen, nach PUT und POST wird
nachgemessen. Das ist keine atomare Sperre gegen gleichzeitige Dashboard-Edits;
solche Änderungen nicht parallel zum automatischen Lauf ausführen.

  · Kein DELETE und kein automatisches Ersetzen bestehender Schutzregeln.
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
from typing import Callable, Mapping, NamedTuple

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
        "Nur bei nachweislich leerem Ausgangszustand automatisch setzbar: "
        "`python3 scripts/worker_environment_einrichten.py --anwenden --reviewer <login>`."
    ),
    "branch": (
        "Nur bei nachweislich leerem Ausgangszustand automatisch setzbar: "
        "`python3 scripts/worker_environment_einrichten.py --anwenden --reviewer <login>`."
    ),
    "bypass": (
        "Dieses Werkzeug setzt den Bypass nicht: Im Dashboard Settings → Environments → "
        "`cloudflare-produktion` → „Allow administrators to bypass configured "
        "protection rules“ AUS; anschließend mit dem Guard nachmessen."
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

    def __init__(self, text: str, *, schritte: list[str] | None = None):
        super().__init__(text)
        self.schritte = list(schritte or [])


class BefundFehler(RuntimeError):
    """Der Zustand ist belegt und weicht ab – fail-closed."""

    exit_code = 1

    def __init__(self, text: str, *, schritte: list[str] | None = None):
        super().__init__(text)
        self.schritte = list(schritte or [])


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
        recht = ("Repository-Recht `Administration: write`"
                 if art == "schreiben" else "Repository-Recht `Actions: read`")
        return (
            f"GitHub-API verweigert den Zugriff (HTTP {status}). Berechtigung und "
            f"Gültigkeit der GitHub-Verbindung prüfen: benötigt wird {recht}. "
            "Das ist ein Zugriffs-/Rechtebefund, keine belegte Code-Regression – "
            "die Einrichtung bleibt bis dahin eine Inhaber-Aufgabe."
        )
    if status == 404:
        return (
            f"GitHub-Environment `{UMGEBUNG}` fehlt oder ist nicht sichtbar (HTTP 404). "
            "Es wird nicht automatisch angelegt; Zugriff und Dashboard prüfen."
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


def _leerer_ausgangszustand(umgebung: object, regeln: object) -> bool:
    """Nur der eindeutig ungeschützte Ausgangszustand ist automatisch änderbar.

    Bereits vorhandene Schutzregeln, ein deaktivierter/unbekannter Bypass oder
    eine Branch-Policy dürfen nicht durch einen partiellen PUT riskiert werden.
    """
    return (isinstance(umgebung, dict)
            and umgebung.get("protection_rules") == []
            and umgebung.get("can_admins_bypass") is True
            and "deployment_branch_policy" in umgebung
            and umgebung["deployment_branch_policy"] is None
            and regeln is None)


def planen(umgebung: object, regeln: list | None) -> list[Lage]:
    """Übersetzt den gemessenen Stand in eine Lage je Ziel.

    Die Bewertung selbst kommt aus `worker_environment_guard.abweichungen` –
    dieses Skript erfindet keine zweite Wahrheit, es übersetzt sie nur in
    Ziele und machbare Schritte.
    """
    if umgebung is None:
        return [Lage(ziel, KLASSE_OFFEN,
                     f"Environment `{UMGEBUNG}` fehlt oder ist nicht sichtbar; Zustand nicht belegbar.",
                     MASSNAHME["unbekannt"]) for ziel in ZIELE]
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
        if ziel == "bypass":
            klasse, massnahme = KLASSE_OBERFLAECHE, MASSNAHME[ziel]
        elif _leerer_ausgangszustand(umgebung, regeln):
            klasse, massnahme = KLASSE_MACHBAR, MASSNAHME[ziel]
        else:
            # Ein schon geschützter oder unklarer Zustand kann mit einem PUT
            # bestehende Einstellungen verlieren oder zusätzliche Personen
            # freigabeberechtigen. Das ist keine automatische Verschärfung.
            klasse, massnahme = KLASSE_ABWEICHUNG, MASSNAHME["unbekannt"]
        lagen.append(Lage(ziel, klasse, " ".join(texte), massnahme))
    if unbekannt:
        grund = " ".join(unbekannt)
        lagen = [Lage(l.ziel, KLASSE_OFFEN, f"Nicht belegbar: {grund}", MASSNAHME["unbekannt"])
                 if l.klasse in (KLASSE_ERFUELLT, KLASSE_MACHBAR) else l for l in lagen]
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


def _erwartete_absicherung(umgebung: object, reviewer_id: int, *,
                           bypass: tuple[bool, ...]) -> bool:
    """Nachweis der gesetzten Regeln, ohne andere oder unlesbare Regeln zu raten."""
    if not isinstance(umgebung, dict) or umgebung.get("can_admins_bypass") not in bypass:
        return False
    # `1 == True` in Python, ist aber keine belegte GitHub-Boolean-Antwort.
    if not isinstance(umgebung.get("can_admins_bypass"), bool):
        return False
    policy = umgebung.get("deployment_branch_policy")
    if (not isinstance(policy, dict) or policy.get("protected_branches") is not False
            or policy.get("custom_branch_policies") is not True):
        return False
    regeln = umgebung.get("protection_rules")
    if (not isinstance(regeln, list) or any(not isinstance(r, dict) for r in regeln)
            or any(r.get("type") not in ("required_reviewers", "branch_policy") for r in regeln)):
        return False
    reviewer_regeln = [r for r in regeln if r.get("type") == "required_reviewers"]
    if len(reviewer_regeln) != 1 or sum(r.get("type") == "branch_policy" for r in regeln) > 1:
        return False
    reviewer = reviewer_regeln[0].get("reviewers")
    return (isinstance(reviewer, list) and len(reviewer) == 1
            and _reviewer_gueltig(reviewer[0]) and reviewer[0].get("type") == "User"
            and _reviewer_id(reviewer[0]) == reviewer_id)


def schreiben(lagen: list[Lage], umgebung: dict | None, *, repo: str, token: str,
              reviewer_id: int | None, transport: Callable | None = None,
              melden: Callable[[str], None] | None = None) -> tuple[list[Lage], list[str]]:
    """Sichert nur den leeren Ausgangszustand ab; jeder Schritt wird nachgelesen.

    Eine veränderte oder bereits geschützte Umgebung wird NICHT überschrieben.
    Zwischen Vormessung und PUT gibt es keine atomare API-Sperre: Deshalb dürfen
    Dashboard-Änderungen nicht gleichzeitig mit diesem Lauf stattfinden.
    """
    sagen = melden or (lambda text: None)
    schritte: list[str] = []

    machbar = {l.ziel for l in lagen if l.klasse == KLASSE_MACHBAR}
    if not machbar:
        return list(lagen), schritte
    klassen = {l.ziel: l.klasse for l in lagen}
    if (len(lagen) != len(ZIELE) or klassen != {
            "reviewer": KLASSE_MACHBAR, "branch": KLASSE_MACHBAR,
            "bypass": KLASSE_OBERFLAECHE}
            or not _leerer_ausgangszustand(umgebung, None)):
        raise BefundFehler("Ausgangszustand ist nicht eindeutig leer – kein automatischer Schreibzugriff. "
                          "Schutzregeln im Dashboard prüfen und dort bearbeiten.")
    if not isinstance(reviewer_id, int) or isinstance(reviewer_id, bool) or reviewer_id <= 0:
        raise WerkzeugFehler("Eine gültige Reviewer-ID fehlt; `--reviewer <login>` oder "
                             "`--reviewer-id <id>` übergeben.")

    # Nicht mit einem veralteten Plan schreiben. Ein Vergleich des gesamten
    # gelesenen Objekts erkennt auch Änderungen außerhalb der drei Ziele.
    aktuell, aktuelle_regeln = stand(repo, token, transport=transport)
    if aktuell != umgebung or not _leerer_ausgangszustand(aktuell, aktuelle_regeln):
        raise BefundFehler("Environment wurde seit der Vormessung geändert oder ist nicht eindeutig leer – "
                          "kein automatischer Schreibzugriff. Erneut prüfen oder Dashboard verwenden.")

    koerper = {
        "reviewers": [{"type": "User", "id": reviewer_id}],
        "deployment_branch_policy": {"protected_branches": False, "custom_branch_policies": True},
    }
    try:
        status, _kopf, _roh = _senden("PUT", f"{API}/repos/{repo}/environments/{UMGEBUNG}",
                                      token, repo=repo, koerper=koerper, transport=transport)
    except WerkzeugFehler:
        raise WerkzeugFehler("Ergebnis des Environment-PUT nicht belegbar; Dashboard prüfen.",
                             schritte=["Environment-PUT versucht (Ergebnis unbekannt)."]) from None
    if status not in (200, 201):
        if status in (401, 403):
            raise BefundFehler(_status_text(status, "schreiben"))
        # Ein Serverfehler, eine unerwartete Antwort oder ein Konflikt belegt
        # nicht, dass der Request wirkungslos blieb. Auch keinen Retry raten.
        raise WerkzeugFehler(
            f"Environment-PUT antwortete mit HTTP {status}; Wirkung nicht belegbar. Dashboard prüfen.",
            schritte=["Environment-PUT versucht (Wirkung unbekannt)."])
    sagen("PUT Environment: deployment_branch_policy, reviewers")
    schritte.append(f"Environment-PUT für `{UMGEBUNG}` angenommen.")

    # Vor Freigabe des Branches muss der GET beweisen, dass Reviewer und
    # Selected-Policy wirklich stehen und keine alten Regeln reaktiviert wurden.
    try:
        zwischen, zwischen_regeln = stand(repo, token, transport=transport)
    except WerkzeugFehler:
        raise WerkzeugFehler("Environment-PUT wurde angenommen; Zwischenstand nicht lesbar. "
                             "Keine Branch-Regel hinzugefügt; Dashboard prüfen.",
                             schritte=schritte) from None
    if (not _erwartete_absicherung(zwischen, reviewer_id, bypass=(True,))
            or zwischen_regeln != []):
        raise WerkzeugFehler("Environment-PUT wurde angenommen, aber der Zwischenstand ist nicht "
                             "eindeutig. Keine Branch-Regel hinzugefügt; Dashboard prüfen.",
                             schritte=schritte)

    try:
        status, _kopf, _roh = _senden(
            "POST", f"{API}/repos/{repo}/environments/{UMGEBUNG}/deployment-branch-policies",
            token, repo=repo, koerper={"name": ZWEIG, "type": "branch"}, transport=transport)
    except WerkzeugFehler:
        raise WerkzeugFehler("Environment-PUT angenommen; Ergebnis des Branch-POST nicht belegbar. "
                             "Dashboard prüfen.", schritte=schritte +
                             ["Branch-POST versucht (Ergebnis unbekannt)."]) from None
    if status not in (200, 201):
        if status in (401, 403):
            raise BefundFehler("Environment-PUT wurde angenommen, Branch-Regel nicht belegt. "
                              + _status_text(status, "schreiben") + " Dashboard prüfen.",
                              schritte=schritte)
        raise WerkzeugFehler(
            f"Environment-PUT angenommen; Branch-POST antwortete mit HTTP {status}. "
            "Wirkung nicht belegbar. Dashboard prüfen.",
            schritte=schritte + ["Branch-POST versucht (Wirkung unbekannt)."])
    schritte.append(f"Branch-POST für `{ZWEIG}` angenommen.")

    try:
        nachher, regeln = stand(repo, token, transport=transport)
    except WerkzeugFehler:
        raise WerkzeugFehler("Environment-PUT und Branch-POST wurden angenommen; "
                             "Nachmessung nicht lesbar. Dashboard prüfen.",
                             schritte=schritte) from None
    if (not _erwartete_absicherung(nachher, reviewer_id, bypass=(True, False))
            or not isinstance(regeln, list) or len(regeln) != 1
            or not isinstance(regeln[0], dict)
            or regeln[0].get("name") != ZWEIG or regeln[0].get("type") != "branch"):
        raise WerkzeugFehler("Environment-PUT und Branch-POST wurden angenommen; "
                             "Nachmessung weicht ab. Dashboard prüfen.", schritte=schritte)
    return planen(nachher, regeln), schritte


def stand(repo: str, token: str, *, transport: Callable | None = None
          ) -> tuple[dict | None, list | None]:
    """Liest Environment und Branch-Regeln. (None, None) = 404/nicht sichtbar."""
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


def _fehler_ausgeben(exc: WerkzeugFehler | BefundFehler, *,
                     json_ausgabe: bool, md_pfad: str | None) -> int:
    """Auch bei einem Abbruch dürfen angenommene/ungewisse Schritte nicht verschwinden."""
    if json_ausgabe:
        print(json.dumps({"environment": UMGEBUNG, "fehler": str(exc),
                          "schritte": exc.schritte, "exit": exc.exit_code},
                         ensure_ascii=False, indent=2))
        return exc.exit_code

    titel = ("Produktions-Environment nicht belegbar" if isinstance(exc, WerkzeugFehler)
             else "Produktions-Environment nicht einrichtbar")
    if exc.schritte or md_pfad:
        zeilen = [f"## {titel}", "", f"- **Fehler:** {exc}"]
        if exc.schritte:
            zeilen += ["", "**Schreibversuche und angenommene Schritte:**"]
            zeilen += [f"- {schritt}" for schritt in exc.schritte]
            zeilen += ["", "Annahme ist kein Nachweis der Wirkung; Dashboard prüfen."]
        try:
            _ausgabe("\n".join(zeilen) + "\n", md_pfad)
        except WerkzeugFehler as bericht_fehler:
            annotation("error", str(bericht_fehler), titel="Bericht nicht belegbar")
            annotation("error", str(exc), titel=titel)
            return 2
    annotation("error", str(exc), titel=titel)
    return exc.exit_code


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

    # 3 · Das Werkzeug kennzeichnet den Admin-Bypass NIE als automatisch machbar.
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

    # 6 · Nur der ungeschützte Ausgangszustand wird bearbeitet. Der Stub
    #     bildet GET → PUT → Zwischenmessung → POST → Nachmessung ab.
    gesendet: list[tuple[str, str, dict | None]] = []
    leer = {"protection_rules": [], "can_admins_bypass": True, "deployment_branch_policy": None}
    nach_put = {"protection_rules": [
        {"type": "required_reviewers", "reviewers": [{"type": "User", "reviewer": {"id": 42}}]},
        {"type": "branch_policy"}], "can_admins_bypass": True,
        "deployment_branch_policy": {"protected_branches": False, "custom_branch_policies": True}}
    phase = [0]

    def transport(methode, url, token, koerper):
        gesendet.append((methode, url, koerper))
        if methode == "GET":
            if url.endswith("/deployment-branch-policies?per_page=100"):
                liste = regeln_main if phase[0] == 2 else []
                return 200, {}, json.dumps({"total_count": len(liste), "branch_policies": liste}).encode()
            return 200, {}, json.dumps(leer if phase[0] == 0 else nach_put).encode()
        phase[0] = 1 if methode == "PUT" else 2
        return 200, {}, b"{}"

    rest, schritte = schreiben(planen(leer, None), leer, repo="frank/x", token="TOKEN",
                               reviewer_id=42, transport=transport)
    koerper = next((k for m, _u, k in gesendet if m == "PUT"), None)
    if not koerper or koerper.get("reviewers") != [{"type": "User", "id": 42}]:
        fehler.append("6 fehlender Reviewer nicht eindeutig gesetzt")
    if koerper and "can_admins_bypass" in koerper:
        fehler.append("6 can_admins_bypass im Schreibkörper")
    if [m for m, _u, _k in gesendet].count("GET") < 5 or len(schritte) != 2:
        fehler.append("6 Zwischen- oder Nachmessung fehlt")
    if {l.ziel: l.klasse for l in rest} != {"reviewer": KLASSE_ERFUELLT,
                                             "branch": KLASSE_ERFUELLT,
                                             "bypass": KLASSE_OBERFLAECHE}:
        fehler.append("6 Teilheilung oder offener Bypass falsch eingeordnet")

    # Bestehende Reviewer dürfen nicht ergänzt/zusammengeführt werden: Schon
    # ein zusätzlicher Reviewer erweitert die Menge der Freigabeberechtigten.
    doppelt = {"protection_rules": [
        {"type": "required_reviewers", "reviewers": [{"type": "User", "reviewer": {"id": 7}}]},
        {"type": "required_reviewers", "reviewers": [{"type": "User", "reviewer": {"id": 8}}]},
    ], "can_admins_bypass": True, "deployment_branch_policy": None}
    gesendet.clear()
    lagen = planen(doppelt, None)
    if not any(l.ziel == "reviewer" and l.klasse == KLASSE_ABWEICHUNG for l in lagen):
        fehler.append("6 vorhandene Reviewer wurden als automatisch änderbar eingestuft")
    schreiben(lagen, doppelt, repo="frank/x", token="TOKEN", reviewer_id=42, transport=transport)
    if gesendet:
        fehler.append("6 geschützte Umgebung wurde automatisch geändert")

    # 7 · Idempotenz: erfüllter Zustand sendet keinen Schreibaufruf.
    gesendet.clear()
    rest, schritte = schreiben(planen(sicher, regeln_main), sicher, repo="frank/x",
                               token="TOKEN", reviewer_id=42, transport=transport)
    if gesendet or schritte:
        fehler.append(f"7 nicht idempotent: {[m for m, _u, _k in gesendet]}")

    # 8 · Fehlender Reviewer OHNE ID ist ein Werkzeugfehler, kein Teilerfolg.
    try:
        schreiben(planen(leer, None), leer, repo="frank/x", token="TOKEN",
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
    print("✅ SELBSTTEST OK — Zuordnung, OFFEN ist nie grün, Endpunkt- und Schreibgrenzen, "
          "Zwischen-/Nachmessung, Idempotenz, Rechtebefund und Geheimnisfreiheit belegt.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Prüft die Produktionsfreigabe; kann bei leerem Ausgangszustand begrenzt schreiben.")
    gruppe = ap.add_mutually_exclusive_group(required=True)
    gruppe.add_argument("--pruefen", action="store_true",
                        help="Einrichtungsstand lesen und je Ziel einordnen")
    gruppe.add_argument("--anwenden", action="store_true",
                        help="nur bei leerem Ausgangszustand Reviewer und Branch-Regel versuchen")
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
            raise WerkzeugFehler(_status_text(404, "lesen"))
        lagen = planen(umgebung, regeln)

        schritte: list[str] = []
        if args.anwenden:
            lagen, schritte = schreiben(
                lagen, umgebung, repo=repo, token=token, reviewer_id=reviewer_id)
            if schritte:
                try:
                    umgebung, regeln = stand(repo, token)
                    if umgebung is None:
                        raise WerkzeugFehler(_status_text(404, "lesen"))
                except WerkzeugFehler as exc:
                    raise WerkzeugFehler(f"Zusätzliche Nachmessung nicht belegbar: {exc}",
                                         schritte=schritte) from None
                lagen = planen(umgebung, regeln)
    except (WerkzeugFehler, BefundFehler) as exc:
        return _fehler_ausgeben(exc, json_ausgabe=args.json, md_pfad=args.md)

    offen = [l for l in lagen if l.klasse != KLASSE_ERFUELLT]
    if args.json:
        print(json.dumps({"environment": UMGEBUNG, "lagen": [l.als_dict() for l in lagen],
                          "schritte": schritte, "offen": len(offen)}, indent=2))
        return 1 if offen else 0

    try:
        _ausgabe(als_md(lagen, schritte=schritte), args.md)
    except WerkzeugFehler as exc:
        return _fehler_ausgeben(WerkzeugFehler(str(exc), schritte=schritte),
                               json_ausgabe=False, md_pfad=None)
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
