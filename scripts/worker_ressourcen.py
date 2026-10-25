#!/usr/bin/env python3
"""Produktive Worker-Ressourcen ohne Kopierfehler auflösen (WF-E813/#815).

Der Deploy darf weder bei einer fehlenden GitHub-Variable still ausfallen noch
auf Verdacht einen neuen, leeren Datenspeicher verwenden. Für einen bereits
produktiven Worker liest dieses Werkzeug deshalb die vorhandene Bindung aus
seinen Cloudflare-Einstellungen:

    ABO  -> KV_NAMESPACE_ID_ABO  (newsletter-worker / ff-newsletter)
    DB   -> D1_DATABASE_ID       (klick-zaehler)

Eine gültige Repository-Variable bleibt für die Ersteinrichtung und bestehende
Installationen zulässig und hat Vorrang. Fehlt sie, ist ausschließlich die
bereits gebundene Produktionsressource die Quelle. Es wird nichts angelegt,
migriert, gelöscht oder in Cloudflare verändert. IDs werden nur in die jeweils
vorgesehene GITHUB_OUTPUT-Datei geschrieben, nicht in Log oder Step Summary.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass

CF_API = "https://api.cloudflare.com/client/v4"
KONTO_ID = re.compile(r"^[0-9a-fA-F]{32}$")
KV_ID = re.compile(r"^[0-9a-fA-F]{32}$")
D1_ID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


class RessourcenFehler(RuntimeError):
    """Sicher behandelbarer Auflösungsfehler ohne geheime Rohdaten."""


@dataclass(frozen=True)
class Ressource:
    variable: str
    ausgabe: str
    script: str
    binding: str
    typ: str
    id_feld: str
    muster: re.Pattern[str]


@dataclass(frozen=True)
class Aufloesung:
    ressource: Ressource
    wert: str
    quelle: str


RESSOURCEN = {
    "newsletter-worker": Ressource(
        variable="KV_NAMESPACE_ID_ABO",
        ausgabe="kv_namespace_id_abo",
        script="ff-newsletter",
        binding="ABO",
        typ="kv_namespace",
        id_feld="namespace_id",
        muster=KV_ID,
    ),
    "klick-zaehler": Ressource(
        variable="D1_DATABASE_ID",
        ausgabe="d1_database_id",
        script="klick-zaehler",
        binding="DB",
        typ="d1",
        id_feld="id",
        muster=D1_ID,
    ),
}
BEKANNTE_WORKER = frozenset((*RESSOURCEN, "ki-assistent"))


class _KeineWeiterleitung(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise OSError("Unerwartete Weiterleitung; Bearer-Token wird nicht weitergereicht")


def _token_und_konto(umgebung: dict) -> tuple[str, str]:
    token = (umgebung.get("CLOUDFLARE_API_TOKEN") or "").strip()
    konto = (umgebung.get("CLOUDFLARE_ACCOUNT_ID") or "").strip()
    if not token:
        raise RessourcenFehler(
            "CF_WORKERS_DEPLOY_TOKEN fehlt im Environment cloudflare-produktion; "
            "die bestehende Worker-Bindung kann nicht gelesen werden."
        )
    if any(ord(zeichen) < 33 or ord(zeichen) > 126 for zeichen in token):
        raise RessourcenFehler("Der Cloudflare-Token hat kein gültiges HTTP-Headerformat.")
    if not KONTO_ID.fullmatch(konto):
        raise RessourcenFehler(
            "CLOUDFLARE_ACCOUNT_ID fehlt oder hat kein gültiges 32-Hex-Format "
            "im Environment cloudflare-produktion."
        )
    return token, konto.lower()


def _einstellungen_holen(token: str, konto: str, script: str) -> dict:
    """Liest ausschließlich Script-Einstellungen; keine Antworttexte ins Log."""
    if not KONTO_ID.fullmatch(konto) or script not in {r.script for r in RESSOURCEN.values()}:
        raise RessourcenFehler("Interne Sicherheitsgrenze: Konto oder Workername ist ungültig.")
    url = f"{CF_API}/accounts/{konto.lower()}/workers/scripts/{script}/settings"
    anfrage = urllib.request.Request(url, headers={
        "accept": "application/json",
        "authorization": f"Bearer {token}",
        "user-agent": "franksfinanzcheck-worker-ressourcen/1.0",
    })
    opener = urllib.request.build_opener(_KeineWeiterleitung())
    try:
        with opener.open(anfrage, timeout=30) as antwort:
            roh = antwort.read(1_000_001)
    except urllib.error.HTTPError as fehler:
        status = fehler.code
        fehler.close()
        if status in (401, 403):
            raise RessourcenFehler(
                "Der Deploy-Token darf die bestehenden Worker-Einstellungen nicht lesen "
                f"(HTTP {status}). Benötigt wird Workers Scripts: Read für dieses Konto; "
                f"alternativ die Ressourcen-ID als Repository-Variable hinterlegen."
            ) from None
        if status == 404:
            raise RessourcenFehler(
                f"Der Worker {script} ist in diesem Konto noch nicht vorhanden oder nicht lesbar. "
                "Für eine echte Ersteinrichtung die vorhandene Ressourcen-ID als "
                "Repository-Variable hinterlegen; keinen neuen Speicher ohne Migrationsplan anlegen."
            ) from None
        if status == 429 or status >= 500:
            raise RessourcenFehler(
                f"Cloudflare-Einstellungen sind vorübergehend nicht lesbar (HTTP {status}); "
                "Deploy später erneut starten, keine Ersatzressource raten."
            ) from None
        raise RessourcenFehler(
            f"Cloudflare-Einstellungen wurden abgelehnt (HTTP {status}); "
            "Konto und Deploy-Token prüfen."
        ) from None
    except (OSError, ValueError) as fehler:
        raise RessourcenFehler(
            "Cloudflare-Einstellungen sind nicht erreichbar; Deploy später erneut starten "
            f"({type(fehler).__name__})."
        ) from None
    if len(roh) > 1_000_000:
        raise RessourcenFehler("Cloudflare-Einstellungen überschreiten das sichere Antwortlimit.")
    try:
        daten = json.loads(roh.decode("utf-8"))
    except (UnicodeError, ValueError):
        raise RessourcenFehler("Cloudflare-Einstellungen enthalten kein gültiges JSON.") from None
    if not isinstance(daten, dict):
        raise RessourcenFehler("Cloudflare-Einstellungen haben kein Objektformat.")
    return daten


def binding_id(antwort: dict, ressource: Ressource) -> str:
    """Extrahiert genau eine vorhandene Bindung; Raten ist ausdrücklich verboten."""
    if not isinstance(antwort, dict) or antwort.get("success") is not True:
        raise RessourcenFehler("Cloudflare meldet keine erfolgreiche Einstellungslesung.")
    resultat = antwort.get("result")
    bindings = resultat.get("bindings") if isinstance(resultat, dict) else None
    if not isinstance(bindings, list):
        raise RessourcenFehler("In den Worker-Einstellungen fehlt die Bindungsliste.")
    treffer = [
        eintrag for eintrag in bindings
        if isinstance(eintrag, dict)
        and eintrag.get("type") == ressource.typ
        and eintrag.get("name") == ressource.binding
    ]
    if len(treffer) != 1:
        raise RessourcenFehler(
            f"Erwartete genau eine produktive {ressource.binding}-Bindung vom Typ "
            f"{ressource.typ}, gefunden: {len(treffer)}. Keine Ersatzressource raten."
        )
    wert = treffer[0].get(ressource.id_feld)
    if not isinstance(wert, str) or not ressource.muster.fullmatch(wert.strip()):
        raise RessourcenFehler(
            f"Die produktive {ressource.binding}-Bindung enthält keine gültige Ressourcen-ID."
        )
    return wert.strip().lower()


def aufloesen(name: str, umgebung: dict | None = None, *, holen=None) -> Aufloesung | None:
    """Löst einen Worker fail-closed auf; `None` bedeutet: keine Ressource nötig."""
    umgebung = os.environ if umgebung is None else umgebung
    if name not in BEKANNTE_WORKER:
        raise RessourcenFehler(f"Unbekannter Worker: {name}")
    ressource = RESSOURCEN.get(name)
    if ressource is None:
        return None

    explizit = (umgebung.get(ressource.variable) or "").strip()
    if explizit:
        if not ressource.muster.fullmatch(explizit):
            raise RessourcenFehler(
                f"Repository-Variable {ressource.variable} hat kein gültiges Format; "
                "der Deploy wird nicht auf eine automatisch gefundene Alternative umgeleitet."
            )
        return Aufloesung(ressource, explizit.lower(), "Repository-Variable")

    token, konto = _token_und_konto(umgebung)
    funktion = holen or _einstellungen_holen
    antwort = funktion(token, konto, ressource.script)
    wert = binding_id(antwort, ressource)
    return Aufloesung(ressource, wert, f"bestehende {ressource.binding}-Bindung des Produktions-Workers")


def _output_schreiben(pfad: str, aufloesung: Aufloesung) -> None:
    if not pfad:
        raise RessourcenFehler("GITHUB_OUTPUT fehlt; die Auflösung läuft nur im Deploy-Schritt.")
    with open(pfad, "a", encoding="utf-8") as ausgabe:
        ausgabe.write(f"{aufloesung.ressource.ausgabe}={aufloesung.wert}\n")


def _summary_schreiben(pfad: str, text: str) -> None:
    if pfad:
        with open(pfad, "a", encoding="utf-8") as ausgabe:
            ausgabe.write(text + "\n\n")


def befehl_aufloesen(name: str, umgebung: dict | None = None, *, holen=None) -> int:
    umgebung = os.environ if umgebung is None else umgebung
    try:
        ergebnis = aufloesen(name, umgebung, holen=holen)
        if ergebnis is None:
            text = f"✅ {name}: keine KV-/D1-Ressource erforderlich."
            print(text)
            _summary_schreiben(umgebung.get("GITHUB_STEP_SUMMARY", ""), text)
            return 0
        _output_schreiben(umgebung.get("GITHUB_OUTPUT", ""), ergebnis)
        text = (f"✅ {name}: {ergebnis.ressource.variable} aus {ergebnis.quelle} aufgelöst; "
                "kein neuer Datenspeicher angelegt (ID nicht im Log).")
        print(text)
        _summary_schreiben(umgebung.get("GITHUB_STEP_SUMMARY", ""), text)
        return 0
    except (RessourcenFehler, OSError) as fehler:
        text = (f"{name}: Produktionsressource nicht eindeutig aufgelöst – Deploy bleibt "
                f"fail-closed. {fehler}")
        print(f"::error::{text}")
        _summary_schreiben(umgebung.get("GITHUB_STEP_SUMMARY", ""), f"## ❌ Worker-Ressource\n\n{text}")
        return 1


def selftest() -> int:
    """Offline-Kernproben; ausführliche Sabotagefälle stehen im Unit-Testmodul."""
    umgebung = {
        "CLOUDFLARE_API_TOKEN": "nur-test-token",
        "CLOUDFLARE_ACCOUNT_ID": "a" * 32,
    }
    antwort = {"success": True, "result": {"bindings": [
        {"type": "kv_namespace", "name": "ABO", "namespace_id": "b" * 32},
    ]}}
    aufrufe = []

    def fake(token, konto, script):
        aufrufe.append((token, konto, script))
        return antwort

    ergebnis = aufloesen("newsletter-worker", umgebung, holen=fake)
    assert ergebnis and ergebnis.wert == "b" * 32
    assert aufrufe == [("nur-test-token", "a" * 32, "ff-newsletter")]
    assert aufloesen("ki-assistent", {}) is None
    print("✅ SELBSTTEST OK — produktive Worker-Bindung aufgelöst, kein neuer Speicher, kein Netz im Test.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    gruppe = parser.add_mutually_exclusive_group(required=True)
    gruppe.add_argument("--aufloesen", choices=sorted(BEKANNTE_WORKER))
    gruppe.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    return befehl_aufloesen(args.aufloesen)


if __name__ == "__main__":
    sys.exit(main())
