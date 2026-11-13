#!/usr/bin/env python3
"""produktions_schutz_selbstheilung.py – WF-829B / #922: der Heilweg läuft selbst.

WARUM DIESE DATEI EXISTIERT (07.11.2026)
----------------------------------------
Seit dem 25.10.2026 ist `cloudflare-produktion` ungesichert: kein Required
Reviewer, keine Branch-Regel, Administrator-Bypass an. `worker_environment_guard.py`
hält den Deploy deshalb fail-closed vor jedem Secret-Zugriff – richtigerweise.
`worker_environment_einrichten.py --anwenden` kann bei leerem Ausgangszustand
zwei Ziele per API versuchen; den Bypass setzt das Werkzeug nicht. **Aber:
Dieser Befehl stand seit dem 30.10.2026 in keinem automatischen Lauf.** Die Tages-Wache
ruft ausschließlich `--pruefen --warnstufe` auf. Jeden Morgen wurde derselbe
Befund neu gemeldet, jeden Tag blieb er liegen. Das ist keine Wache, sondern
eine Warteschlange – dieselbe Klasse wie GSC #1097, nur an der teureren Stelle.

Dieses Modul schließt die Lücke, ohne das Gate anzutasten:

  · VERTRAG      `data/produktions_schutz_vertrag.json` – der Zielzustand an
                 EINER Stelle, strikt validiert gegen die Regeln des
                 Einrichters und des Gates (kein zweiter Wahrheitsbegriff).
  · EICHPROBE    Vor JEDEM Urteil wird der Vorfall im Speicher nachgebaut.
                 Erkennt der Prüfer ihn nicht mehr, gibt es kein Urteil und
                 keinen Schreibzugriff: Exit 3 „MESSGERÄT NICHT EICHFÄHIG"
                 (dieselbe Lehre wie das Integritäts-Siegel am 04.11.2026).
  · HEILUNG      messen → nur im nachweislich leeren Ausgangszustand schreiben
                 → NACHMESSEN. Ohne Nachmessung gilt nichts als geheilt; ein
                 Verlust bereits belegter Ziele ist ein Abbruch (Exit 2).
  · BELEGKETTE   append-only JSONL mit verketteten SHA-256-Prüfsummen: jeder
                 Lauf hält Vormessung, Nachmessung, Schritte, Klasse und Grund
                 fest. Kein Token, kein Antworttext, kein Fremdlink.
  · VERDRAHTUNG  `--wache` prüft, dass der Heilschritt wirklich im Workflow
                 steht (nicht bloß in einem Kommentar), dass der harte Stopp
                 im Deploy-Pfad unangetastet ist und die Kette heil ist.
                 Fällt die Verdrahtung weg, wird sie zum Befund – die Wache
                 heilt sich also selbst, statt zu verrotten.

GRENZEN, DIE DIESES WERKZEUG NICHT ÜBERSCHREITET
  · Es gibt NIE eine Deploy-Freigabe (`pending_deployments` bleibt tabu).
  · Es setzt nie `can_admins_bypass`: Der Schreibparameter ist in der
    offiziellen REST-Spezifikation nicht dokumentiert; Dashboard + Nachmessung
    bleiben für dieses Werkzeug der bestätigte Weg.
  · Es liest keine Cloudflare-Secrets und berührt nur `api.github.com` über
    die bereits geprüften Endpunkte des Einrichters.
  · Kein DELETE und kein automatisches Ersetzen oder Erweitern bestehender
    Schutzregeln. Zeitgleiche Dashboard-Änderungen sind nicht atomar sperrbar;
    diese nicht parallel zum Lauf ausführen.
  · HTTP 401/403 ist ein Zugriffs-/Rechtebefund, kein belegter Code-Fehler,
    kein Grün und kein „übersprungen".

Bedienung:
    python3 scripts/produktions_schutz_selbstheilung.py --selftest
    python3 scripts/produktions_schutz_selbstheilung.py --wache
    python3 scripts/produktions_schutz_selbstheilung.py --pruefen [--json] [--md PFAD]
    python3 scripts/produktions_schutz_selbstheilung.py --heilen [--json] [--md PFAD]
                                                       [--beleg PFAD]

Exit: 0 = Zielzustand belegt (SICHER oder GEHEILT mit Nachmessung) ·
1 = OFFEN (Rechtebefund oder Dashboard-Schalter; fail-closed bleibt) ·
2 = nicht belegbar (Netz/API/Kette/Verschlechterung) · 3 = Messgerät nicht eichfähig.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Callable, NamedTuple

import worker_environment_einrichten as einrichter
import worker_environment_guard as guard
from github_kommando import annotation
from integrity_guard import _doppelte_schluessel

BLOG_DIR = Path(__file__).resolve().parent.parent

VERTRAG_PFAD = "data/produktions_schutz_vertrag.json"
LEDGER_PFAD = "data/produktions_schutz_belege.jsonl"
ARBEITSFLUSS = ".github/workflows/produktions-schutz-selbstheilung.yml"
DEPLOY_FLUSS = ".github/workflows/worker-deploy.yml"
SKRIPT = "scripts/produktions_schutz_selbstheilung.py"
TESTDATEI = "scripts/tests/test_produktions_schutz_selbstheilung.py"
TESTMODUL = "scripts.tests.test_produktions_schutz_selbstheilung"
DEPLOY_NAME = "Cloudflare-Worker deployen"

PFlicht_PFADE = (
    SKRIPT, TESTDATEI, VERTRAG_PFAD, LEDGER_PFAD, ARBEITSFLUSS, DEPLOY_FLUSS,
    "scripts/worker_environment_einrichten.py", "scripts/tests/test_worker_environment_einrichten.py",
    "scripts/worker_environment_guard.py", "scripts/tests/test_worker_environment_guard.py",
)

VERTRAG_SCHLUESSEL = {
    "schema", "environment", "zweig", "reviewer_login", "ziele",
    "dashboard_ziele", "nur_verschaerfen", "ledger", "begruendung",
}
LEDGER_PFAD_RE = re.compile(r"^data/[A-Za-z0-9_.-]+\.jsonl$")
LAUF_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
GENESIS = "0" * 64
SHA_RE = re.compile(r"^[0-9a-f]{64}$")

KLASSE_SICHER = "SICHER"
KLASSE_GEHEILT = "GEHEILT"
KLASSE_OFFEN = "OFFEN"
KLASSE_RECHT = "RECHT"
KLASSE_OBERFLAECHE = "OBERFLAECHE"
KLASSE_NICHT_BELEGBAR = "NICHT_BELEGBAR"
KLASSE_MESSGERAET = "MESSGERAET"
KLASSE_VERSCHLECHTERUNG = "VERSCHLECHTERUNG"

EXIT_CODES = {
    KLASSE_SICHER: 0, KLASSE_GEHEILT: 0, KLASSE_OFFEN: 1,
    KLASSE_NICHT_BELEGBAR: 2, KLASSE_MESSGERAET: 3,
    KLASSE_VERSCHLECHTERUNG: 2,
}

# Eingefrorene Vorlagen für die Eichprobe. Sie sind ABSICHTLICH der heutige
# Live-Befund: drei Ziele offen, zwei davon per API machbar, eines nur im
# Dashboard. Ein Prüfer, der dazu „ok" sagt, darf nicht urteilen.
UNSICHER = {
    "protection_rules": [],
    "can_admins_bypass": True,
    "deployment_branch_policy": None,
}
SICHER = {
    "protection_rules": [{"type": "required_reviewers",
                          "reviewers": [{"type": "User", "reviewer": {"id": 42}}]}],
    "can_admins_bypass": False,
    "deployment_branch_policy": {"protected_branches": False,
                                 "custom_branch_policies": True},
}
REGELN_MAIN = [{"name": "main", "type": "branch"}]


class NichtBelegbar(RuntimeError):
    """Ungeprüft ist nicht sauber (C34)."""


class KetteKaputt(RuntimeError):
    """Die Belegkette ist keine ganze Messung mehr (D7)."""


class Lage(NamedTuple):
    vorher: dict
    nachher: dict
    schritte: list[str]
    gruende: list[str]


class Ergebnis(NamedTuple):
    klasse: str
    code: int
    lage: Lage
    beleg: dict


# --------------------------------------------------------------------------- #
#  Vertrag – der Zielzustand an einer Stelle
# --------------------------------------------------------------------------- #

def vertrag_fehler(daten: object) -> list[str]:
    """Reine Prüfung des Vertrags: kein Netz, keine Datei, keine Uhr."""
    fehler: list[str] = []
    if not isinstance(daten, dict):
        return ["Vertrag ist kein Objekt."]
    if set(daten) != VERTRAG_SCHLUESSEL:
        fehler.append("Vertrag hat unbekannte oder fehlende Schlüssel.")
        return fehler
    if daten.get("schema") != 1 or isinstance(daten.get("schema"), bool):
        fehler.append("Vertrag: `schema` muss 1 sein.")
    if daten.get("environment") != einrichter.UMGEBUNG:
        fehler.append("Vertrag: Environment weicht vom Gate ab.")
    if daten.get("zweig") != einrichter.ZWEIG:
        fehler.append("Vertrag: Zweig weicht vom Einrichter ab.")
    if list(daten.get("ziele") or []) != list(einrichter.ZIELE):
        fehler.append("Vertrag: Ziele weichen von `einrichter.ZIELE` ab.")
    if daten.get("dashboard_ziele") != ["bypass"]:
        fehler.append("Vertrag: nur `bypass` ist ein Dashboard-Ziel.")
    if daten.get("nur_verschaerfen") is not True:
        fehler.append("Vertrag: `nur_verschaerfen` darf nie falsch sein.")
    login = daten.get("reviewer_login")
    if not isinstance(login, str) or not einrichter.LOGIN_RE.fullmatch(login):
        fehler.append("Vertrag: `reviewer_login` ist kein gültiger Anmeldename.")
    ledger = daten.get("ledger")
    if not isinstance(ledger, str) or not LEDGER_PFAD_RE.fullmatch(ledger):
        fehler.append("Vertrag: `ledger` muss eine Datei unter `data/` sein.")
    if not isinstance(daten.get("begruendung"), str) or not daten["begruendung"].strip():
        fehler.append("Vertrag: Begründung fehlt.")
    return fehler


def vertrag_laden(pfad: Path | str | None = None) -> dict:
    """Liest den Vertrag als BYTE-Prüfung – doppelte Schlüssel sind ein Bruch."""
    ziel = Path(pfad) if pfad is not None else BLOG_DIR / VERTRAG_PFAD
    try:
        roh = ziel.read_bytes()
        text = roh.decode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise NichtBelegbar(f"Vertrag nicht lesbar ({type(exc).__name__}).") from None
    doppelt = _doppelte_schluessel(text)
    if doppelt:
        raise NichtBelegbar(
            "Vertrag enthält doppelte Schlüssel (" + ", ".join(doppelt) +
            ") – zwei Fassungen wurden übereinandergelegt; keine Messung.")
    try:
        daten = json.loads(text)
    except ValueError as exc:
        raise NichtBelegbar(f"Vertrag ist kein gültiges JSON ({type(exc).__name__}).") from None
    fehler = vertrag_fehler(daten)
    if fehler:
        raise NichtBelegbar("Vertrag ungültig: " + "; ".join(fehler))
    return daten


def vertrag_sha256(pfad: Path | str | None = None) -> str:
    ziel = Path(pfad) if pfad is not None else BLOG_DIR / VERTRAG_PFAD
    return hashlib.sha256(ziel.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
#  Eichprobe – vor jedem Urteil, ohne Netz und ohne Datei
# --------------------------------------------------------------------------- #

def eichprobe() -> list[str]:
    """Baut den Vorfall im Speicher nach und verlangt das richtige Urteil.

    Die Probe prüft den Code, der sie GERADE ausführt – nicht den Code, der
    irgendwann in der CI lag. Fällt die Doppelprüfung weg oder wird `planen`
    durch eine „immer grün"-Fassung ersetzt, liefert sie einen Fehler und der
    Lauf verweigert jedes Urteil (Exit 3).
    """
    fehler: list[str] = []

    lagen = einrichter.planen(UNSICHER, None)
    klassen = {l.ziel: l.klasse for l in lagen}
    erwartet = {"reviewer": einrichter.KLASSE_MACHBAR,
                "branch": einrichter.KLASSE_MACHBAR,
                "bypass": einrichter.KLASSE_OBERFLAECHE}
    if klassen != erwartet:
        fehler.append(f"E1 Vorfall wird falsch eingeordnet: {klassen}")

    sicher = einrichter.planen(SICHER, REGELN_MAIN)
    if [l for l in sicher if l.klasse != einrichter.KLASSE_ERFUELLT]:
        fehler.append("E2 sicherer Zustand wird nicht als erfüllt erkannt")

    if not guard.abweichungen(UNSICHER, None):
        fehler.append("E3 der harte Stopp sieht den Vorfall nicht mehr")
    if guard.abweichungen(SICHER, REGELN_MAIN):
        fehler.append("E4 der harte Stopp meldet den sicheren Zustand als Befund")

    if einrichter.SCHREIBEN_ERLAUBT != {("PUT", "umgebung"), ("POST", "regeln")}:
        fehler.append("E5 neue Schreibwege im Einrichter – Nur-Verschärfen nicht mehr belegt")

    transport = Transport()
    try:
        rest, _schritte = einrichter.schreiben(
            klassen_zu_lagen(lagen), UNSICHER, repo="eich/probe",
            token="EICHPROBE", reviewer_id=42, transport=transport)
        if not any(l.ziel == "bypass" and l.klasse == einrichter.KLASSE_OBERFLAECHE for l in rest):
            fehler.append("E6 ungeschriebener Bypass wird als geheilt ausgegeben")
    except (einrichter.WerkzeugFehler, einrichter.BefundFehler) as exc:
        fehler.append(f"E6 Schreibprobe abgebrochen: {type(exc).__name__}")
    rufe = transport.rufe
    methoden = [(m, u.rsplit("/", 1)[-1]) for m, u, _k in rufe]
    if any(m == "DELETE" for m, _ in methoden):
        fehler.append("E6 DELETE im Heilweg")
    if not any(m == "PUT" for m, _ in methoden) or not any(m == "POST" for m, _ in methoden):
        fehler.append("E6 die zwei erlaubten Schreibwege wurden nicht ausgeführt")
    if not any(k and "reviewers" in k for _m, _u, k in rufe):
        fehler.append("E6 Reviewer wird nicht gesetzt")
    if any(k and "can_admins_bypass" in json.dumps(k) for _m, _u, k in rufe):
        fehler.append("E6 undokumentiertes Bypass-Feld im Schreibkörper")
    if sum(m == "GET" for m, _u, _k in rufe) < 5:
        fehler.append("E6 Vor-, Zwischen- oder Nachmessung fehlt")
    if any(l.ziel == "bypass" and l.klasse != einrichter.KLASSE_OBERFLAECHE
           for l in einrichter.planen({**SICHER, "can_admins_bypass": True}, REGELN_MAIN)):
        fehler.append("E7 Admin-Bypass als automatisch heilbar ausgewiesen")

    # Ein geschützter Zustand darf nicht durch einen partiellen PUT gelockert
    # werden – insbesondere keine Erweiterung bestehender Reviewer-Listen.
    geschuetzt = {**UNSICHER, "can_admins_bypass": False}
    t = Transport(umgebung=geschuetzt)
    try:
        einrichter.schreiben(einrichter.planen(geschuetzt, None), geschuetzt,
                             repo="eich/probe", token="EICHPROBE", reviewer_id=42, transport=t)
    except (einrichter.WerkzeugFehler, einrichter.BefundFehler):
        # Ein expliziter Sicherheitsabbruch ist ebenfalls zulässig.
        pass
    if any(m != "GET" for m, _u, _k in t.rufe):
        fehler.append("E8 geschützter Ausgangszustand wurde geschrieben")
    return fehler


def klassen_zu_lagen(lagen: list) -> list:
    """Identität – nur für die Eichprobe, damit kein Fall verloren geht."""
    return list(lagen)


# --------------------------------------------------------------------------- #
#  Messen, Heilen, Nachmessen
# --------------------------------------------------------------------------- #

def klassen(lagen: list) -> dict:
    """Ziel → Klasse, einschließlich unbekannter Befundzeilen."""
    return {l.ziel: l.klasse for l in lagen}


def messen(repo: str, token: str, transport: Callable | None = None
           ) -> tuple[dict | None, list | None, list]:
    """Ein einziger Messweg: `einrichter.stand` + `einrichter.planen`."""
    umgebung, regeln = einrichter.stand(repo, token, transport=transport)
    # 404 bedeutet fehlend ODER nicht sichtbar: niemals automatisch anlegen,
    # keinen Zustand raten und insbesondere keine Nachmessung behaupten.
    if umgebung is None:
        raise einrichter.WerkzeugFehler(einrichter._status_text(404, "lesen"))
    lagen = einrichter.planen(umgebung, regeln)
    return umgebung, regeln, lagen


def verschlechterungen(vorher: dict, nachher: dict) -> list[str]:
    """Bereits belegte Ziele dürfen nicht verloren gehen.

    MACHBAR und ABWEICHUNG beschreiben den Handlungsweg, keine Rangfolge der
    Sicherheit. Beispielsweise ist eine ausgewählte leere Branch-Liste zwar
    manuell zu bearbeiten, aber restriktiver als eine fehlende Branch-Policy.
    """
    offen: list[str] = []
    for ziel, klasse in vorher.items():
        jetzt = nachher.get(ziel)
        if jetzt is None or (klasse == einrichter.KLASSE_ERFUELLT
                             and jetzt != einrichter.KLASSE_ERFUELLT):
            offen.append(f"{ziel}: {klasse} → {jetzt}")
    return offen


def _gruende(lagen: list, recht: str | None) -> list[str]:
    texte: list[str] = []
    if recht:
        texte.append(KLASSE_RECHT + ": " + recht)
    for lage in lagen:
        if lage.klasse == einrichter.KLASSE_ERFUELLT:
            continue
        ziel = einrichter.ZIEL_TEXT.get(lage.ziel, lage.ziel)
        if lage.klasse == einrichter.KLASSE_MACHBAR:
            # Der Rat des Einrichters nennt seinen Handbefehl. Im automatischen
            # Lauf wäre das ein Rückfall in genau die Warteschlange, die dieser
            # Vorgang beendet: Deshalb steht hier der Heil-Lauf, nicht der
            # Handbefehl. Für alle anderen Klassen bleibt die Originalmaßnahme.
            naechster = ("Automatisch: Der Heil-Lauf kann dies mit gültigem "
                         "Repository-Recht `Administration: write` versuchen; "
                         "die Nachmessung entscheidet. Alternativ im Dashboard setzen.")
        else:
            naechster = lage.massnahme or "von Hand prüfen"
        texte.append(f"{lage.klasse} · {ziel}: {lage.text} → {naechster}")
    return texte


def heilen(*, repo: str, token: str, vertrag: dict, transport: Callable | None = None,
           ledger: Path | str | None = None, lauf: str = "lokal",
           jetzt: str | None = None, schreiben_erlaubt: bool = True) -> Ergebnis:
    """Messen → im leeren Ausgangszustand begrenzt schreiben → nachmessen.

    `transport` ist die einzige Testgrenze; `ledger=None` unterdrückt das
    Schreiben der Belegkette (für Selbsttest und `--pruefen`).
    """
    zeit = jetzt or datetime.datetime.now(datetime.timezone.utc).isoformat()
    protokoll = {"art": "selbstheilung", "zeit": zeit, "lauf": lauf, "repo": repo,
                 "eichprobe": "bestanden", "vertrag_sha256": None,
                 "vorher": {}, "nachher": {}, "schritte": [], "gruende": [],
                 "ergebnis": None}

    eich_fehler = eichprobe()
    if eich_fehler:
        protokoll.update({"art": "messgeraet", "eichprobe": "gescheitert",
                          "gruende": eich_fehler, "ergebnis": KLASSE_MESSGERAET})
        lage = Lage({}, {}, [], eich_fehler)
        return _abschluss(KLASSE_MESSGERAET, lage, protokoll, ledger)

    try:
        protokoll["vertrag_sha256"] = vertrag_sha256()
    except OSError:
        protokoll["vertrag_sha256"] = "nicht lesbar"

    fehler_vertrag = vertrag_fehler(vertrag)
    if fehler_vertrag:
        protokoll.update({"art": "vertrag", "gruende": fehler_vertrag,
                          "ergebnis": KLASSE_NICHT_BELEGBAR})
        return _abschluss(KLASSE_NICHT_BELEGBAR, Lage({}, {}, [], fehler_vertrag),
                          protokoll, ledger)

    try:
        umgebung, _regeln, lagen = messen(repo, token, transport)
    except einrichter.WerkzeugFehler as exc:
        grund = f"Vormessung nicht belegbar: {exc}"
        protokoll.update({"art": "messung", "gruende": [grund],
                          "ergebnis": KLASSE_NICHT_BELEGBAR})
        return _abschluss(KLASSE_NICHT_BELEGBAR, Lage({}, {}, [], [grund]),
                          protokoll, ledger)

    vorher = klassen(lagen)
    protokoll["vorher"] = dict(vorher)
    schritte: list[str] = []
    recht: str | None = None

    machbar = any(l.klasse == einrichter.KLASSE_MACHBAR for l in lagen)
    if machbar and schreiben_erlaubt:
        try:
            reviewer_id = einrichter.nutzer_id(
                vertrag["reviewer_login"], repo=repo, token=token, transport=transport)
            _rest, schritte = einrichter.schreiben(
                lagen, umgebung, repo=repo, token=token, reviewer_id=reviewer_id,
                transport=transport)
        except einrichter.BefundFehler as exc:
            schritte = list(exc.schritte)
            text = str(exc)
            if "Recht" in text or "403" in text or "401" in text:
                recht = ("GitHub-API verweigert das Schreiben (HTTP 401/403). "
                         "GitHub-Verbindung und Repository-Recht `Administration: write` "
                         "prüfen; der harte Stopp bleibt.")
            else:
                grund = f"Schreiben nicht belegbar: {exc}"
                protokoll.update({"art": "messung", "gruende": [grund],
                                  "ergebnis": KLASSE_NICHT_BELEGBAR,
                                  "vorher": dict(vorher), "schritte": schritte})
                return _abschluss(KLASSE_NICHT_BELEGBAR,
                                  Lage(dict(vorher), {}, schritte, [grund]), protokoll, ledger)
        except einrichter.WerkzeugFehler as exc:
            schritte = list(exc.schritte)
            grund = f"Schreiben nicht belegbar: {exc}"
            protokoll.update({"art": "messung", "gruende": [grund],
                              "ergebnis": KLASSE_NICHT_BELEGBAR,
                              "vorher": dict(vorher), "schritte": schritte})
            return _abschluss(KLASSE_NICHT_BELEGBAR,
                              Lage(dict(vorher), {}, schritte, [grund]), protokoll, ledger)

    # NACHMESSUNG: ohne sie ist „geheilt" eine Behauptung. Sie läuft auch dann,
    # wenn nichts geschrieben wurde – Idempotenz ist sonst unbelegt.
    try:
        _u, _r, lagen_nachher = messen(repo, token, transport)
    except einrichter.WerkzeugFehler as exc:
        grund = f"Nachmessung nicht belegbar: {exc}"
        protokoll.update({"art": "messung", "gruende": [grund],
                          "ergebnis": KLASSE_NICHT_BELEGBAR,
                          "schritte": schritte})
        return _abschluss(KLASSE_NICHT_BELEGBAR,
                          Lage(dict(vorher), {}, schritte, [grund]), protokoll, ledger)

    nachher = klassen(lagen_nachher)
    verschlechtert = verschlechterungen(vorher, nachher)
    protokoll.update({"nachher": dict(nachher), "schritte": list(schritte)})

    if verschlechtert:
        gruende = ["Der Zustand ist nach dem Eingriff schlechter: "
                   + ", ".join(verschlechtert)] + _gruende(lagen_nachher, recht)
        protokoll.update({"art": "verschlechterung", "gruende": gruende,
                          "ergebnis": KLASSE_VERSCHLECHTERUNG})
        return _abschluss(KLASSE_VERSCHLECHTERUNG,
                          Lage(dict(vorher), dict(nachher), schritte, gruende),
                          protokoll, ledger)

    offen = [l for l in lagen_nachher if l.klasse != einrichter.KLASSE_ERFUELLT]
    if offen or recht:
        klasse = KLASSE_OFFEN
        gruende = _gruende(lagen_nachher, recht)
        if schritte:
            gruende.insert(0, f"{len(schritte)} Schreibschritt(e) von GitHub angenommen; "
                              "der Zustand wurde nachgemessen, weitere Ziele bleiben offen.")
    elif schritte:
        klasse, gruende = KLASSE_GEHEILT, []
    else:
        klasse, gruende = KLASSE_SICHER, []

    protokoll.update({"gruende": gruende, "ergebnis": klasse})
    return _abschluss(klasse, Lage(dict(vorher), dict(nachher), schritte, gruende),
                      protokoll, ledger)


def _abschluss(klasse: str, lage: Lage, protokoll: dict,
               ledger: Path | str | None) -> Ergebnis:
    if ledger is not None:
        try:
            eintrag = ledger_anhaengen(ledger, protokoll)
        except (NichtBelegbar, KetteKaputt) as exc:
            lage = Lage(lage.vorher, lage.nachher, lage.schritte,
                        lage.gruende + [f"Belegkette nicht fortschreibbar: {exc}"])
            klasse = KLASSE_NICHT_BELEGBAR
        else:
            protokoll = eintrag
    return Ergebnis(klasse, EXIT_CODES[klasse], lage, protokoll)


# --------------------------------------------------------------------------- #
#  Belegkette – append-only, verkettet, ohne Geheimnisse
# --------------------------------------------------------------------------- #

def _hash(eintrag: dict) -> str:
    nutzdaten = {k: v for k, v in eintrag.items() if k != "sha256"}
    roh = json.dumps(nutzdaten, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(roh).hexdigest()


def _geheimnis(eintrag: dict) -> bool:
    """Kein Token, kein Bearer, kein Antworttext darf in die Kette geraten."""
    text = json.dumps(eintrag, ensure_ascii=False)
    return any(wort in text for wort in ("Bearer ", "GITHUB_TOKEN=", "ghp_", "github_pat_"))


def ledger_zeilen_pruefen(zeilen: list[str]) -> list[str]:
    """Reine Kettenprüfung – kein Dateizugriff, auch im Selbsttest nutzbar."""
    fehler: list[str] = []
    vorher = GENESIS
    for nr, zeile in enumerate(zeilen, start=1):
        if not zeile.strip():
            fehler.append(f"Zeile {nr}: leere Zeile in der Belegkette")
            continue
        if _doppelte_schluessel(zeile):
            fehler.append(f"Zeile {nr}: doppelte Schlüssel – keine ganze Messung")
            continue
        try:
            eintrag = json.loads(zeile)
        except ValueError:
            fehler.append(f"Zeile {nr}: kein gültiges JSON")
            continue
        if not isinstance(eintrag, dict):
            fehler.append(f"Zeile {nr}: kein Objekt")
            continue
        if eintrag.get("seq") != nr:
            fehler.append(f"Zeile {nr}: `seq` ist nicht {nr}")
        if eintrag.get("prev_sha256") != vorher:
            fehler.append(f"Zeile {nr}: `prev_sha256` passt nicht zur Kette")
        sha = eintrag.get("sha256")
        if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
            fehler.append(f"Zeile {nr}: `sha256` fehlt oder hat kein Format")
            vorher = GENESIS
            continue
        if _hash(eintrag) != sha:
            fehler.append(f"Zeile {nr}: Prüfsumme stimmt nicht mit dem Eintrag überein")
        if _geheimnis(eintrag):
            fehler.append(f"Zeile {nr}: Geheimnisspur im Beleg")
        vorher = sha
    return fehler


def ledger_pruefen(pfad: Path | str | None = None) -> list[str]:
    ziel = Path(pfad) if pfad is not None else BLOG_DIR / LEDGER_PFAD
    try:
        text = ziel.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"Belegkette `{ziel.name}` nicht lesbar ({type(exc).__name__})."]
    return ledger_zeilen_pruefen(text.splitlines())


def ledger_anhaengen(pfad: Path | str, nutzdaten: dict) -> dict:
    """Hängt GENAU eine ganze Messung an – nie rekonstruieren, nie überschreiben."""
    ziel = Path(pfad)
    bestehend: list[str] = []
    if ziel.exists():
        try:
            bestehend = ziel.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as exc:
            raise KetteKaputt(f"Belegkette nicht lesbar ({type(exc).__name__}).") from None
    fehler = ledger_zeilen_pruefen(bestehend)
    if fehler:
        raise KetteKaputt("Kette ist kaputt: " + "; ".join(fehler[:3]))
    vorher = GENESIS
    for zeile in bestehend:
        if zeile.strip():
            try:
                vorher = json.loads(zeile).get("sha256", GENESIS)
            except ValueError:
                raise KetteKaputt("Kette enthält eine unlesbare Zeile.") from None
    eintrag = dict(nutzdaten)
    eintrag["seq"] = len([z for z in bestehend if z.strip()]) + 1
    eintrag["prev_sha256"] = vorher
    eintrag["sha256"] = _hash(eintrag)
    if _geheimnis(eintrag):
        raise NichtBelegbar("Beleg würde eine Geheimnisspur enthalten.")
    try:
        ziel.parent.mkdir(parents=True, exist_ok=True)
        with ziel.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(eintrag, sort_keys=True, ensure_ascii=False,
                                separators=(",", ":")) + "\n")
    except OSError as exc:
        raise NichtBelegbar(f"Beleg nicht schreibbar ({type(exc).__name__}).") from None
    return eintrag


# --------------------------------------------------------------------------- #
#  Verdrahtungs-Wache – die Selbstheilung bewacht ihre eigene Selbstheilung
# --------------------------------------------------------------------------- #

def run_bloecke(text: str) -> list[str]:
    """Nur echte `run:`-Blöcke, ohne Kommentare. Ein Kommentar ist keine Verdrahtung."""
    zeilen = text.splitlines()
    bloecke: list[str] = []
    index = 0
    while index < len(zeilen):
        kopf = re.match(r"^(\s*)run:\s*[|>][-+]?\s*(?:#.*)?$", zeilen[index])
        if not kopf:
            # Einzeiler (`run: python3 …`) sind im Deploy-Pfad die Regel. Sie
            # müssen mitzählen, sonst wäre der harte Stopp „nicht verdrahtet",
            # obwohl er längst läuft.
            inline = re.match(r"^(\s*)run:\s*(\S.*)$", zeilen[index])
            if inline:
                befehl = re.sub(r"\s+#.*$", "", inline.group(2))
                if befehl.strip() and not befehl.lstrip().startswith("#"):
                    bloecke.append(befehl)
            index += 1
            continue
        einzug = len(kopf.group(1))
        index += 1
        inhalt: list[str] = []
        while index < len(zeilen):
            zeile = zeilen[index]
            if zeile.strip() and (len(zeile) - len(zeile.lstrip(" "))) <= einzug:
                break
            bereinigt = re.sub(r"\s+#.*$", "", zeile)
            if bereinigt.lstrip().startswith("#"):
                bereinigt = ""
            inhalt.append(bereinigt)
            index += 1
        bloecke.append("\n".join(inhalt))
    return bloecke


def ereignis_block(text: str, ereignis: str) -> list[str]:
    """Zeilen eines `on:`-Ereignisblocks (Einzug 2), ohne YAML-Abhängigkeit."""
    zeilen = text.splitlines()
    start = None
    for nr, zeile in enumerate(zeilen):
        if re.match(rf"^  {re.escape(ereignis)}:\s*(?:#.*)?$", zeile):
            start = nr + 1
            break
    if start is None:
        return []
    block: list[str] = []
    for zeile in zeilen[start:]:
        if zeile.strip() and (len(zeile) - len(zeile.lstrip(" "))) <= 2:
            break
        block.append(zeile)
    return block


def pfadliste(text: str, ereignis: str) -> list[str]:
    block = ereignis_block(text, ereignis)
    pfade: list[str] = []
    im_pfad = False
    for zeile in block:
        tiefe = len(zeile) - len(zeile.lstrip(" "))
        if re.match(r"^\s{4}paths:\s*$", zeile):
            im_pfad = True
            continue
        if im_pfad:
            if zeile.strip() and tiefe <= 4:
                break
            treffer = re.match(r'^\s+-\s+"([^"]+)"\s*(?:#.*)?$', zeile)
            if treffer:
                pfade.append(treffer.group(1))
    return pfade


def verdrahtung(wf_text: str, deploy_text: str, *, root: Path | str | None = None) -> list[str]:
    """Befunde der Verdrahtung. Reine Textprüfung – kein PyYAML, kein Netz."""
    fehler: list[str] = []
    basis = Path(root) if root is not None else BLOG_DIR
    bloecke = run_bloecke(wf_text)
    lauftext = "\n".join(bloecke)

    for token, hinweis in (
        ("--selftest", "Selbsttest des Heilers"),
        ("--wache", "Verdrahtungs-Wache"),
        ("--heilen", "der Heilschriftzug selbst"),
        ("--beleg", "Belegkette"),
        (TESTMODUL, "Vertragstests"),
        ("$GITHUB_STEP_SUMMARY", "Job-Zusammenfassung"),
    ):
        if token not in lauftext:
            fehler.append(f"W1 `{token}` steht in keinem `run:`-Block ({hinweis}) – "
                          "ein Kommentar zählt nicht.")

    for ereignis in ("schedule", "workflow_dispatch", "workflow_run", "push", "pull_request"):
        if not ereignis_block(wf_text, ereignis):
            fehler.append(f"W2 Auslöser `{ereignis}` fehlt – der Heilweg läuft nicht automatisch.")
    if DEPLOY_NAME not in "\n".join(ereignis_block(wf_text, "workflow_run")):
        fehler.append("W2 Ereignis-Heilung nach einem Worker-Deploy ist nicht verdrahtet.")
    if "secrets.UMGEBUNGS_ADMIN_TOKEN" not in wf_text or "github.token" not in wf_text:
        fehler.append("W3 Kein Token-Pfad mit Admin-Fallback und `github.token` verdrahtet.")
    if "CF_WORKERS_DEPLOY_TOKEN" in wf_text or "CLOUDFLARE_ACCOUNT_ID" in wf_text:
        fehler.append("W3 Der Heil-Lauf führt Cloudflare-Secrets – das ist verboten.")
    if "pending_deployments" in wf_text:
        fehler.append("W3 Der Heil-Lauf würde Deploy-Freigaben selbst erteilen – das ist verboten.")
    if "github.ref == 'refs/heads/main'" not in wf_text or "head_branch == 'main'" not in wf_text:
        fehler.append("W3 Der Live-Job ist nicht auf `main` begrenzt.")
    if "cancel-in-progress: false" not in wf_text:
        fehler.append("W3 Zwei gleichzeitige Heilungen wären möglich (Concurrency-Sperre fehlt).")

    links, rechts = pfadliste(wf_text, "push"), pfadliste(wf_text, "pull_request")
    if set(links) != set(rechts):
        fehler.append("W4 `push`- und `pull_request`-Filter sind nicht deckungsgleich (W3 der Trigger-Wache).")
    for pfad in PFlicht_PFADE:
        if pfad not in links or pfad not in rechts:
            fehler.append(f"W4 Pfadfilter nennt `{pfad}` nicht – eine Änderung daran löst den Lauf nicht aus.")
    for pfad in links + rechts:
        if not any(zeichen in pfad for zeichen in "*?[") and not (basis / pfad).exists():
            fehler.append(f"W4 Pfadfilter zeigt ins Leere: `{pfad}`")

    deploy_laeufe = "\n".join(run_bloecke(deploy_text))
    if "worker_environment_guard.py --check" not in deploy_laeufe:
        fehler.append("W5 Der harte Stopp im Deploy-Pfad fehlt oder steht nur in einem Kommentar.")
    if "--anwenden" in deploy_laeufe or "--heilen" in deploy_laeufe:
        fehler.append("W5 Der Heilweg ersetzt das Gate im Deploy-Pfad – fail-closed darf nie umgangen werden.")
    if "worker_environment_guard.py --selftest" not in deploy_laeufe:
        fehler.append("W5 Der Selbsttest des harten Stopps läuft im Deploy-Pfad nicht mehr.")
    return fehler


def wache(*, root: Path | str | None = None, ledger: Path | str | None = None) -> list[str]:
    """Vertrag, Verdrahtung und Belegkette in einem lesenden Urteil."""
    basis = Path(root) if root is not None else BLOG_DIR
    fehler: list[str] = []
    try:
        vertrag_laden(basis / VERTRAG_PFAD)
    except NichtBelegbar as exc:
        fehler.append(f"V1 {exc}")
    try:
        wf_text = (basis / ARBEITSFLUSS).read_text(encoding="utf-8")
        deploy_text = (basis / DEPLOY_FLUSS).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return fehler + [f"V2 Verdrahtung nicht lesbar ({type(exc).__name__})."]
    fehler += ["V3 " + text for text in verdrahtung(wf_text, deploy_text, root=basis)]
    ziel = Path(ledger) if ledger is not None else basis / LEDGER_PFAD
    fehler += ["V4 " + text for text in ledger_pruefen(ziel)]
    return fehler


# --------------------------------------------------------------------------- #
#  Ausgabe
# --------------------------------------------------------------------------- #

ZIEL_TEXT = {"reviewer": "Required Reviewer", "branch": "Branch-Regel `main`",
             "bypass": "Kein Administrator-Bypass", "unbekannt": "Unbekannter Befund"}
NACHSTER_SCHRITT = {
    KLASSE_SICHER: "Environment-Policy belegt; Zugang und Deploy separat prüfen. Freigeben bleibt Menschenhandlung.",
    KLASSE_GEHEILT: "Environment-Policy nachgemessen; Zugang und Deploy separat prüfen. Freigeben bleibt Menschenhandlung.",
    KLASSE_OFFEN: "Offene Ziele in der Tabelle prüfen und im Dashboard absichern; "
                  "danach den Guard erneut ausführen.",
    KLASSE_RECHT: "GitHub-Verbindung und Repository-Recht `Administration: write` prüfen.",
    KLASSE_OBERFLAECHE: "Ein Schalter im Dashboard.",
    KLASSE_NICHT_BELEGBAR: "Netz/API prüfen, danach erneut messen. Ungeprüft gilt nicht als sauber.",
    KLASSE_MESSGERAET: "Heiler nicht eichfähig: keine Freigabe, kein Schreiben. Code prüfen.",
    KLASSE_VERSCHLECHTERUNG: "Eingriff sofort prüfen: der Zustand ist schlechter als vorher.",
}


def als_md(ergebnis: Ergebnis) -> str:
    e = ergebnis
    ziele = sorted(set(e.lage.vorher) | set(e.lage.nachher))
    zeilen = ["## Produktions-Schutz · automatische Selbstheilung", "",
              f"- **Ergebnis:** `{e.klasse}` (Exit {e.code})",
              f"- **Eichprobe:** {e.beleg.get('eichprobe', '?')}",
              f"- **Nachmessung:** {'belegt' if e.lage.nachher else 'nicht möglich'}",
              "", "| Ziel | vorher | nachher |", "|---|---|---|"]
    for ziel in ziele:
        zeilen.append(f"| {ZIEL_TEXT.get(ziel, ziel)} | "
                      f"{e.lage.vorher.get(ziel, '–')} | {e.lage.nachher.get(ziel, '–')} |")
    zeilen.append("")
    if e.lage.schritte:
        zeilen += ["**Schreibversuche und angenommene Schritte:**"] + [
            f"- {s}" for s in e.lage.schritte] + [""]
        zeilen += ["_Annahme ist kein Nachweis der Wirkung; die Nachmessung entscheidet._", ""]
    else:
        zeilen += ["**Schreibschritte:** keine belegt.", ""]
    if e.lage.gruende:
        zeilen += ["**Offene Befunde:**"] + [f"- {g}" for g in e.lage.gruende] + [""]
    zeilen += [f"**Nächster Schritt:** {NACHSTER_SCHRITT.get(e.klasse, '–')}", "",
               "_Der harte Stopp im Deploy-Pfad bleibt unangetastet. Dieses Werkzeug "
               "gibt keine Deploy-Freigabe und setzt keinen Administrator-Bypass._", ""]
    return "\n".join(zeilen)


def _ausgabe(text: str, md_pfad: str | None) -> None:
    print(text)
    if not md_pfad or md_pfad == "-":
        return
    try:
        with open(md_pfad, "a", encoding="utf-8") as fh:
            fh.write(text)
    except OSError as exc:
        raise NichtBelegbar(f"Bericht nicht schreibbar ({type(exc).__name__}).") from None


# --------------------------------------------------------------------------- #
#  Selbsttest – offline, ohne Netz, ohne Schreibzugriff, ohne Wanduhr
# --------------------------------------------------------------------------- #

def _beispiel_workflow() -> str:
    """Minimale, aber vollständige Verdrahtung für die Gegenproben."""
    pfade = "\n".join(f'      - "{p}"' for p in PFlicht_PFADE)
    return f'''name: Produktions-Schutz
on:
  push:
    branches: [main]
    paths:
{pfade}
  pull_request:
    paths:
{pfade}
  schedule:
    - cron: "55 5 * * *"
  workflow_dispatch:
    inputs:
      modus:
        type: choice
  workflow_run:
    workflows:
      - "{DEPLOY_NAME}"
    types: [completed]
permissions:
  contents: read
concurrency:
  group: produktions-schutz
  cancel-in-progress: false
jobs:
  vertraege:
    runs-on: ubuntu-24.04
    steps:
      - name: Vertraege
        run: |
          python3 {SKRIPT} --selftest
          python3 {SKRIPT} --wache
          python3 -m unittest {TESTMODUL} -v
  selbstheilung:
    if: github.ref == 'refs/heads/main' && head_branch == 'main'
    runs-on: ubuntu-24.04
    steps:
      - name: Heilen
        env:
          GITHUB_TOKEN: ${{{{ secrets.UMGEBUNGS_ADMIN_TOKEN || github.token }}}}
        run: |
          python3 {SKRIPT} --heilen --beleg "$RUNNER_TEMP/beleg.jsonl" \\
            --md "$GITHUB_STEP_SUMMARY"
'''


def _beispiel_deploy() -> str:
    return '''name: Cloudflare-Worker deployen
jobs:
  policy:
    steps:
      - name: Gate
        run: |
          python3 scripts/worker_environment_guard.py --selftest
          python3 scripts/worker_environment_guard.py --check
'''


class Transport:
    """Zustandsbehafteter Netzersatz; der nicht gesendete Bypass bleibt unverändert."""

    def __init__(self, *, umgebung=None, regeln=None, danach=None,
                 schreiben=200, nutzer=None):
        self.umgebung = json.loads(json.dumps(UNSICHER if umgebung is None else umgebung))
        self.danach = json.loads(json.dumps(danach)) if danach is not None else None
        self.regeln = json.loads(json.dumps([] if regeln is None else regeln))
        self.danach_regeln = list(REGELN_MAIN)
        self.schreiben = schreiben
        self.nutzer = {"id": 42} if nutzer is None else nutzer
        self.rufe: list[tuple[str, str, object]] = []

    def __call__(self, methode, url, token, koerper):
        self.rufe.append((methode, url, koerper))
        if methode == "GET":
            if url.endswith("/users/frank-hartung"):
                return 200, {}, json.dumps(self.nutzer).encode()
            if url.endswith("/deployment-branch-policies?per_page=100"):
                return 200, {}, json.dumps({"total_count": len(self.regeln),
                                            "branch_policies": self.regeln}).encode()
            return 200, {}, json.dumps(self.umgebung).encode()
        if methode in ("PUT", "POST"):
            if self.schreiben >= 400:
                return self.schreiben, {}, b"{}"
            if methode == "PUT":
                self.umgebung["deployment_branch_policy"] = koerper["deployment_branch_policy"]
                self.umgebung["protection_rules"] = [
                    {"type": "required_reviewers", "reviewers": [
                        {"type": r["type"], "reviewer": {"id": r["id"]}}
                        for r in koerper["reviewers"]]}, {"type": "branch_policy"}]
            else:
                self.regeln.append(dict(koerper))
                if self.danach is not None:
                    self.umgebung = self.danach
                    self.regeln = list(self.danach_regeln)
        return 200, {}, b"{}"


def _selftest() -> int:
    """Sabotage- und Gegenproben. Schreibt nichts, ruft kein Netz, kennt keine Uhr."""
    fehler: list[str] = []

    # 1 · Eichprobe ist grün und sabotagefest.
    if eichprobe():
        fehler.append("1 Eichprobe schlägt am gesunden Code an")
    original = einrichter.planen

    def immer_gruen(*_a, **_k):
        return [einrichter.Lage(z, einrichter.KLASSE_ERFUELLT, "ok", "")
                for z in einrichter.ZIELE]

    einrichter.planen = immer_gruen
    try:
        if not eichprobe():
            fehler.append("1 Sabotage (planen → immer grün) wurde nicht erkannt")
    finally:
        einrichter.planen = original

    # 2 · Vertragsprüfung: gültig und sechs Sabotagefälle.
    try:
        vertrag = vertrag_laden()
    except NichtBelegbar as exc:
        fehler.append(f"2 Vertrag nicht lesbar: {exc}")
        vertrag = {}
    if vertrag_fehler(vertrag):
        fehler.append("2 gültiger Vertrag wird abgelehnt")
    for name, aenderung in (
        ("Lockern", {"nur_verschaerfen": False}),
        ("Fremdes Environment", {"environment": "github-pages"}),
        ("Fremder Zweig", {"zweig": "develop"}),
        ("Ziele gekürzt", {"ziele": ["reviewer"]}),
        ("Bypass als API-Ziel", {"dashboard_ziele": []}),
        ("Ledger außerhalb", {"ledger": "../flucht.jsonl"}),
        ("Zusatzschlüssel", {"extra": 1}),
    ):
        probe = dict(vertrag)
        probe.update(aenderung)
        if not vertrag_fehler(probe):
            fehler.append(f"2 Vertragssabotage nicht erkannt: {name}")

    # 3 · Teilheilung: Der Stub verändert nur tatsächlich gesendete Felder.
    #     Der nicht gesendete Bypass bleibt wahr – niemals als GEHEILT buchen.
    t = Transport()
    erg = heilen(repo="frank/x", token="PROBE", vertrag=vertrag, transport=t,
                 ledger=None, lauf="selftest", jetzt="2026-11-07T00:00:00+00:00")
    if erg.klasse != KLASSE_OFFEN or erg.code != 1:
        fehler.append(f"3 Teilheilung falsch eingeordnet: {erg.klasse}")
    if erg.lage.vorher.get("reviewer") != einrichter.KLASSE_MACHBAR:
        fehler.append("3 Vormessung fehlt")
    if erg.lage.nachher.get("reviewer") != einrichter.KLASSE_ERFUELLT:
        fehler.append("3 Nachmessung fehlt oder ist nicht grün")
    if erg.lage.nachher.get("bypass") != einrichter.KLASSE_OBERFLAECHE:
        fehler.append("3 offener Bypass wurde verschwiegen")
    methoden = [m for m, _u, _k in t.rufe if m in ("PUT", "POST", "DELETE")]
    if sorted(methoden) != ["POST", "PUT"]:
        fehler.append(f"3 falsche Schreibwege: {methoden}")
    if any(m == "DELETE" for m, _u, _k in t.rufe):
        fehler.append("3 DELETE im Heilweg")

    # 3b · Eine 200/201-Antwort ohne die erwartete Nachmessung ist kein Erfolg.
    t = Transport(danach={**SICHER, "protection_rules": []})
    erg = heilen(repo="frank/x", token="PROBE", vertrag=vertrag, transport=t,
                 ledger=None, lauf="selftest", jetzt="2026-11-07T00:00:00+00:00")
    if erg.klasse != KLASSE_NICHT_BELEGBAR or len(erg.lage.schritte) != 2:
        fehler.append(f"3b nicht belegte Nachmessung falsch eingeordnet: {erg.klasse}")

    # 4 · Idempotenz: sicherer Zustand schreibt nichts und sagt SICHER.
    t = Transport(umgebung=dict(SICHER), danach=dict(SICHER), regeln=list(REGELN_MAIN))
    erg = heilen(repo="frank/x", token="PROBE", vertrag=vertrag, transport=t,
                 ledger=None, lauf="selftest", jetzt="2026-11-07T00:00:00+00:00")
    if erg.klasse != KLASSE_SICHER or [m for m, _u, _k in t.rufe if m != "GET"]:
        fehler.append(f"4 nicht idempotent: {erg.klasse}")

    # 5 · 403 ist ein Rechtebefund: OFFEN, nie Grün, nie „übersprungen".
    t = Transport(schreiben=403)
    erg = heilen(repo="frank/x", token="PROBE", vertrag=vertrag, transport=t,
                 ledger=None, lauf="selftest", jetzt="2026-11-07T00:00:00+00:00")
    if erg.klasse != KLASSE_OFFEN or erg.code != 1:
        fehler.append(f"5 Rechtebefund falsch eingeordnet: {erg.klasse}")
    if not any(KLASSE_RECHT in g for g in erg.lage.gruende):
        fehler.append("5 Rechtebefund ohne RECHT-Klasse")
    if not any(KLASSE_OBERFLAECHE in g for g in erg.lage.gruende):
        fehler.append("5 Dashboard-Schalter wurde verschwiegen")

    # 6 · Lesefehler ist nicht belegbar (Exit 2), niemals ein Befund „ok".
    def kaputt(_methode, _url, _token, _koerper):
        raise einrichter.WerkzeugFehler("Netz weg")

    erg = heilen(repo="frank/x", token="PROBE", vertrag=vertrag, transport=kaputt,
                 ledger=None, lauf="selftest", jetzt="2026-11-07T00:00:00+00:00")
    if erg.klasse != KLASSE_NICHT_BELEGBAR or erg.code != 2:
        fehler.append(f"6 unlesbarer Stand als {erg.klasse} ausgegeben")

    # 7 · Sabotiertes Messgerät: Exit 3 und KEIN Schreibzugriff.
    einrichter.planen = immer_gruen
    t = Transport()
    try:
        erg = heilen(repo="frank/x", token="PROBE", vertrag=vertrag, transport=t,
                     ledger=None, lauf="selftest", jetzt="2026-11-07T00:00:00+00:00")
    finally:
        einrichter.planen = original
    if erg.klasse != KLASSE_MESSGERAET or erg.code != 3:
        fehler.append(f"7 Sabotage nicht als MESSGERAET erkannt: {erg.klasse}")
    if [m for m, _u, _k in t.rufe if m != "GET"]:
        fehler.append("7 trotz kaputter Eichprobe geschrieben")

    # 8 · Verschlechterung wird zum Abbruch, nie zum Teilerfolg.
    if not verschlechterungen({"reviewer": "ERFUELLT"}, {"reviewer": "MACHBAR"}):
        fehler.append("8 Lockerung nicht erkannt")
    if verschlechterungen({"reviewer": "MACHBAR"}, {"reviewer": "ERFUELLT"}):
        fehler.append("8 Heilung als Lockerung gezählt")

    # 9 · Belegkette: gültig, verkettet und manipulationsfest.
    eintrag = {"seq": 1, "prev_sha256": GENESIS, "art": "messung"}
    eintrag["sha256"] = _hash(eintrag)
    ketten_zeilen = [json.dumps(eintrag, sort_keys=True)]
    if ledger_zeilen_pruefen(ketten_zeilen):
        fehler.append("9 gültige Kette abgelehnt")
    gefaelscht = dict(eintrag, ergebnis="SICHER")
    for fall in (dict(eintrag, seq=2), dict(eintrag, prev_sha256="f" * 64),
                 dict(gefaelscht), '{"seq": 1, "seq": 1}'):
        text = json.dumps(fall, sort_keys=True) if isinstance(fall, dict) else fall
        if not ledger_zeilen_pruefen([text]):
            fehler.append(f"9 Manipulation nicht erkannt: {str(fall)[:60]}")
    if not ledger_zeilen_pruefen([json.dumps({"seq": 1, "prev_sha256": GENESIS,
                                              "sha256": "x" * 64, "token": "Bearer ghp_x"})]):
        fehler.append("9 Geheimnisspur im Beleg nicht erkannt")

    # 10 · Verdrahtung: echte Blöcke zählen, Kommentare nicht.
    gut = _beispiel_workflow()
    if verdrahtung(gut, _beispiel_deploy(), root=BLOG_DIR):
        fehler.append("10 gültige Beispiel-Verdrahtung abgelehnt")
    for name, boese in (
        ("Heilschritt nur im Kommentar", gut.replace(" --heilen ", " # --heilen ")),
        ("Heilschritt entfernt", gut.replace(" --heilen ", " --pruefen ")),
        ("Tageslauf entfernt", gut.replace("  schedule:", "  #schedule:")),
        ("Ereignis-Heilung entfernt", gut.replace("  workflow_run:", "  #workflow_run:")),
        ("Asymmetrischer Filter", gut.replace(f'      - "{SKRIPT}"\n', "", 1)),
        ("Secrets im Heil-Lauf", gut + "\n# CF_WORKERS_DEPLOY_TOKEN\n"),
        ("Selbstfreigabe", gut + "\n# pending_deployments\n"),
        ("Gate im Deploy gelöscht", None),
    ):
        text = gut if boese is None else boese
        deploy = "" if boese is None else _beispiel_deploy()
        if not verdrahtung(text, deploy, root=BLOG_DIR):
            fehler.append(f"10 Verdrahtungssabotage nicht erkannt: {name}")

    # 11 · Geheimnisfreiheit der Ausgabe.
    if "PROBE" in als_md(erg) or "Bearer" in als_md(erg):
        fehler.append("11 Geheimnis im Bericht")

    if fehler:
        print("❌ Selbsttest: " + "; ".join(fehler))
        return 2
    print("✅ SELBSTTEST OK — Eichprobe (inkl. Sabotage), Vertragsgrenzen, "
          "Heilung mit Nachmessung, Idempotenz, Rechtebefund, Nicht-Belegbar, "
          "Verschlechterung, Belegkette, Verdrahtung und Geheimnisfreiheit belegt.")
    return 0


# --------------------------------------------------------------------------- #
#  Kommandozeile
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="WF-829B: Produktions-Schutz automatisch messen, heilen, belegen.")
    gruppe = ap.add_mutually_exclusive_group(required=True)
    gruppe.add_argument("--selftest", action="store_true", help="Sabotage- und Gegenproben, offline")
    gruppe.add_argument("--wache", action="store_true", help="Vertrag, Verdrahtung und Belegkette lesend prüfen")
    gruppe.add_argument("--pruefen", action="store_true", help="nur messen, ohne zu schreiben")
    gruppe.add_argument("--heilen", action="store_true", help="messen, verschärfen, nachmessen, belegen")
    ap.add_argument("--json", action="store_true", help="maschinenlesbare Ausgabe")
    ap.add_argument("--md", help="Bericht an diese Datei anhängen (oder '-')")
    ap.add_argument("--beleg", help="Belegkette an diesen Pfad hängen (Default: Vertrag)")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()

    if args.wache:
        fehler = wache(ledger=args.beleg)
        if args.json:
            print(json.dumps({"befunde": fehler, "anzahl": len(fehler)}, indent=2))
        elif fehler:
            print("❌ Verdrahtungs-Wache – die Selbstheilung ist nicht mehr belegt:")
            for text in fehler:
                print("   " + text)
        else:
            print("✅ Verdrahtungs-Wache: Vertrag, Verdrahtung, harter Stopp und "
                  "Belegkette sind heil. Der Heilweg läuft automatisch.")
        return 1 if fehler else 0

    try:
        vertrag = vertrag_laden()
        repo = einrichter._repo()
        token = einrichter._token()
        lauf = str(os.environ.get("GITHUB_RUN_ID", "lokal"))
        if not LAUF_RE.fullmatch(lauf):
            raise NichtBelegbar("GITHUB_RUN_ID hat kein gültiges Format.")
        ledger = args.beleg or str(BLOG_DIR / vertrag["ledger"])
        ergebnis = heilen(
            repo=repo, token=token, vertrag=vertrag,
            ledger=ledger if args.heilen else None,
            schreiben_erlaubt=bool(args.heilen), lauf=lauf)
    except (NichtBelegbar, einrichter.WerkzeugFehler) as exc:
        annotation("error", str(exc), titel="Produktions-Schutz nicht belegbar")
        return 2

    if args.json:
        print(json.dumps({"ergebnis": ergebnis.klasse, "exit": ergebnis.code,
                          "vorher": ergebnis.lage.vorher, "nachher": ergebnis.lage.nachher,
                          "schritte": ergebnis.lage.schritte,
                          "gruende": ergebnis.lage.gruende,
                          "eichprobe": ergebnis.beleg.get("eichprobe")}, indent=2,
                         ensure_ascii=False))
    else:
        try:
            _ausgabe(als_md(ergebnis), args.md)
        except NichtBelegbar as exc:
            annotation("error", str(exc), titel="Produktions-Schutz nicht belegbar")
            return 2
        for grund in ergebnis.lage.gruende:
            print(f"❌ {grund}")

    # Bei --json bleibt die Ausgabe EIN Objekt: Annotationen und Klartext
    # würden sonst „Extra data" in jedem auswertenden Schritt erzeugen.
    if not args.json:
        if ergebnis.code == 0:
            print(f"✅ {ergebnis.klasse}: Zielzustand mit Nachmessung belegt. "
                  "Der harte Stopp bleibt; Freigeben bleibt Menschenhandlung.")
        elif ergebnis.code == 1:
            annotation("warning", f"{ergebnis.klasse}: Der Deploy bleibt fail-closed "
                       "gesperrt; offene Ziele im Dashboard prüfen und die Schreibgrenze beachten.",
                       titel="Produktions-Schutz offen")
        elif ergebnis.code == 2:
            annotation("error", f"{ergebnis.klasse}: ungeprüft gilt nicht als sauber.",
                       titel="Produktions-Schutz nicht belegbar")
        else:
            annotation("error", "MESSGERÄT NICHT EICHFÄHIG: kein Urteil, kein Schreiben.",
                       titel="Produktions-Schutz: Eichprobe gescheitert")
    return ergebnis.code


if __name__ == "__main__":
    sys.exit(main())
