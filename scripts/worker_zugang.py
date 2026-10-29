#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
#  DEPLOY-ZUGANG PRÜFEN – EIN DOSSIER STATT EIN RATESPIEL
#  ------------------------------------------------------------
#  WARUM ES DIESES WERKZEUG GIBT (Vorgang WF-829B / Meldung #922,
#  27./29.10.2026)
#
#  Der Lauf `40569123622` („Cloudflare-Worker deployen“, Push
#  `0b6a1a27` auf main) scheiterte in BEIDEN Deploy-Jobs im Schritt
#  „Produktive Ressource auflösen“ – nach 0 Sekunden, vor Wrangler.
#  Die Annotation war korrekt und trotzdem zu wenig:
#
#      newsletter-worker: Produktionsressource nicht eindeutig
#      aufgelöst – Deploy bleibt fail-closed. CF_WORKERS_DEPLOY_TOKEN
#      fehlt im Environment cloudflare-produktion; die bestehende
#      Worker-Bindung kann nicht gelesen werden.
#
#  Fail-closed war hier richtig (der Vorfall vom 24.10.2026 war ein
#  stiller, grün gemeldeter Nicht-Deploy). Falsch war die FORM der
#  Auskunft. `worker_ressourcen.py` bricht beim ERSTEN fehlenden
#  Baustein ab – aus Prinzip, weil es die IDs für den Deploy braucht.
#  Für den Menschen vor dem Dashboard ist genau das die falsche
#  Reihenfolge: Er hinterlegt den Token, startet neu, bekommt den
#  nächsten roten Lauf für die Konto-ID, startet neu … Eine Runde
#  Freigabe (Environment `cloudflare-produktion`, Required reviewer)
#  pro einzelnem Feld. Und geprüft wird überhaupt nur, wenn ein
#  Worker-Push oder eine Änderung an der Deploy-Kette einen Lauf
#  auslöst: Der Zugang ist der einzige Teil der Kette, den man
#  NICHT auf Knopfdruck prüfen konnte, ohne einen Deploy zu wagen.
#
#  WAS DIESES WERKZEUG ANDERS MACHT
#  --------------------------------
#    · SAMMELN STATT KURZSCHLIESSEN. Alle Befunde eines Laufs werden
#      erhoben und EINMAL gemeldet: Token fehlt, Konto-ID fehlt/hat
#      falsches Format, Token ungültig/abgelehnt, Recht fehlt,
#      Worker unbekannt, Bindung fehlt/mehrdeutig, Netzstörung.
#      Ein Arbeitsgang statt fünf.
#    · NUR LESEN. Aufgerufen werden ausschließlich
#      `GET /user/tokens/verify` und die Script-Einstellungen der
#      beiden automatischen Worker. Kein Anlegen, Ändern, Löschen,
#      Migrieren; keine `workers.dev`-Veröffentlichung; kein Wrangler.
#    · KEIN GEHEIMNIS, KEINE ID IM TEXT. Befunde entstehen aus
#      festen Vorlagen; eingefügt werden nur Klassennamen und
#      HTTP-Status. Vor jeder Ausgabe werden Token-Wert, Konto-ID und
#      alle Ressourcen-IDs zusätzlich maskiert – auch wenn ein
#      Cloudflare-Text sie enthielte.
#    · DOKUMENT STATT LOGZEILE. `--md` schreibt ein Dossier in die
#      Step Summary: was fehlt, wo es hingehört (Settings →
#      Environments → cloudflare-produktion → Environment secrets),
#      welche Rechte der Token braucht, welcher Schritt danach kommt.
#      Das ist die Vorlage für den Inhaber, nicht für den Agenten.
#    · EHRLICHE ABHÄNGIGKEIT. Fehlt der Token, sind Token-Gültigkeit
#      und Bindungen NICHT PRÜFBAR – das steht dann auch so da
#      (`OFFEN`), nicht als „in Ordnung“. Eine ungeprüfte Zeile, die
#      grün aussieht, ist die Blindstelle, die #829B erzeugt hat.
#    · VORRANG DER REPOSITORY-VARIABLE. Ist `KV_NAMESPACE_ID_ABO`
#      bzw. `D1_DATABASE_ID` gültig gesetzt, ist die Bindung dieses
#      Workers keine Voraussetzung (`worker_ressourcen.py` verwendet
#      sie ohnehin nicht). Der Token bleibt trotzdem Pflicht – ihn
#      braucht Wrangler selbst.
#
#  WAS DIESES WERKZEUG AUSDRÜCKLICH NICHT KANN
#  --------------------------------------------
#    Es kann keinen Zugang erzeugen. Solange `CF_WORKERS_DEPLOY_TOKEN`
#    im Environment fehlt, bleibt WF-829B offen – diese Datei macht
#    die Lücke präzise, sichtbar und in einem Schritt behebbar, nicht
#    unsichtbar. Ein „grün“ an dieser Stelle wäre der Betrug, den die
#    Deploy-Kette seit dem 24.10.2026 gerade verhindert.
#
#  NUTZUNG
#    python3 scripts/worker_zugang.py --pruefen            # beide Worker
#    python3 scripts/worker_zugang.py --pruefen --worker newsletter-worker
#    python3 scripts/worker_zugang.py --pruefen --md bericht.md   # + Dossier
#    python3 scripts/worker_zugang.py --pruefen --json
#    python3 scripts/worker_zugang.py --selftest           # ohne Netz
#
#  EXIT: 0 = alle Voraussetzungen belegt · 1 = Befund (fail-closed)
#        2 = Werkzeugfehler (nicht als Zugangsbefund ausgeben)
#
#  Runbook: docs/SICHERHEIT-BETRIEB-RUNBOOK.md, A4 und D2.
# ============================================================
"""Read-only Zugangsprüfung für den Worker-Deploy (WF-829B / #922)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

HIER = Path(__file__).resolve().parent
if str(HIER) not in sys.path:
    sys.path.insert(0, str(HIER))

import github_kommando as gk  # noqa: E402
import worker_ressourcen as wrr  # noqa: E402

CF_API = "https://api.cloudflare.com/client/v4"
TOKEN_VARIABLE = "CF_WORKERS_DEPLOY_TOKEN"
KONTO_VARIABLE = "CLOUDFLARE_ACCOUNT_ID"
ENVIRONMENT = "cloudflare-produktion"
AUTOMATISCHE_WORKER = ("newsletter-worker", "klick-zaehler")
RUNBOOK = "docs/SICHERHEIT-BETRIEB-RUNBOOK.md"

# Klassen der Befunde. `OK` ist der einzige grüne Zustand; `OFFEN` heißt
# ausdrücklich „nicht prüfbar“ (weil eine Voraussetzung fehlt) und ist
# niemals ein Beleg.
OK = "OK"
FEHLT = "FEHLT"
FORMAT = "FORMAT"
UNGUELTIG = "UNGUELTIG"
RECHT = "RECHT"
UNBEKANNT = "UNBEKANNT"
BINDUNG = "BINDUNG"
NETZ = "NETZ"
OFFEN = "OFFEN"

BEFUNDKLASSEN = (OK, FEHLT, FORMAT, UNGUELTIG, RECHT, UNBEKANNT, BINDUNG, NETZ, OFFEN)

# Feste Handlungssätze je Klasse – nichts davon enthält Werte aus der Umgebung.
MASSNAHME = {
    FEHLT: "Wert im Environment hinterlegen (Settings → Environments → "
            f"{ENVIRONMENT} → Environment secrets).",
    FORMAT: "Wert neu setzen; die Prüfung hat das Format abgelehnt, nicht den Inhalt.",
    UNGUELTIG: "Token widerrufen/neu erzeugen (Cloudflare → My Profile → API Tokens) "
               "und im Environment ersetzen.",
    RECHT: "Dem Token das fehlende Recht geben (Workers Scripts: Read für das Lesen, "
           "Workers Scripts: Edit für den Deploy; D1: Edit beim Klick-Zähler).",
    UNBEKANNT: "Worker-Name bzw. Konto prüfen; ohne Migrationsplan wird nichts neu angelegt.",
    BINDUNG: "Bindung im Worker herstellen oder die Ressourcen-ID als Repository-Variable "
             "hinterlegen – niemals raten.",
    NETZ: "Kein Zugangsfehler: später erneut prüfen (Cloudflare nicht erreichbar oder "
          "gedrosselt).",
    OFFEN: "Nach Behebung der fehlenden Voraussetzung prüft derselbe Lauf diesen Punkt.",
    OK: "",
}


class Netzfehler(RuntimeError):
    """Transportstörung ohne Zugangsbefund (kein Geheimnis im Text)."""


class Werkzeugfehler(RuntimeError):
    """Interner Fehler – wird NICHT als Zugangsbefund ausgegeben."""


@dataclass(frozen=True)
class Befund:
    pruefung: str
    klasse: str
    text: str
    massnahme: str

    @property
    def gruen(self) -> bool:
        return self.klasse == OK


def _befund(pruefung: str, klasse: str, text: str) -> Befund:
    if klasse not in BEFUNDKLASSEN:
        raise Werkzeugfehler(f"Unbekannte Befundklasse: {klasse}")
    return Befund(pruefung, klasse, text, MASSNAHME[klasse])


# ------------------------------------------------------------
#  Transport: genau zwei Endpunktformen, keine Weiterleitung
# ------------------------------------------------------------
class _KeineWeiterleitung(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise OSError("Unerwartete Weiterleitung; Bearer-Token wird nicht weitergereicht")


def _hole(url: str, token: str, timeout: float = 30.0) -> tuple[int, dict | None]:
    """Liefert (HTTP-Status, JSON-Objekt oder None). Wirft nur `Netzfehler`.

    Der Antwortkörper wird NICHT in Fehlertexte übernommen: er kann
    Kontodaten enthalten, und ein Befund ist eine Anweisung, kein Dump.
    """
    if not url.startswith(CF_API + "/"):
        raise Werkzeugfehler("Interne Sicherheitsgrenze: fremder Endpunkt.")
    anfrage = urllib.request.Request(url, headers={
        "accept": "application/json",
        "authorization": f"Bearer {token}",
        "user-agent": "franksfinanzcheck-worker-zugang/1.0",
    })
    opener = urllib.request.build_opener(_KeineWeiterleitung())
    try:
        with opener.open(anfrage, timeout=timeout) as antwort:
            roh = antwort.read(1_000_001)
            status = antwort.status
    except urllib.error.HTTPError as fehler:
        status = fehler.code
        try:
            roh = fehler.read(1_000_001)
        except OSError:
            roh = b""
        finally:
            fehler.close()
    except (urllib.error.URLError, TimeoutError, OSError) as fehler:
        raise Netzfehler(type(fehler).__name__) from None
    if len(roh) > 1_000_000:
        raise Netzfehler("Antwortlimit")
    if not roh:
        return status, None
    try:
        daten = json.loads(roh.decode("utf-8"))
    except (UnicodeError, ValueError):
        return status, None
    return status, daten if isinstance(daten, dict) else None


# ------------------------------------------------------------
#  Einzelprüfungen (jede für sich, keine bricht die anderen ab)
# ------------------------------------------------------------
def _token_pruefung(umgebung: dict) -> tuple[Befund, str | None]:
    wert = (umgebung.get(TOKEN_VARIABLE) or "").strip()
    if not wert:
        return _befund(TOKEN_VARIABLE, FEHLT,
                       f"{TOKEN_VARIABLE} ist im Environment {ENVIRONMENT} nicht lesbar."), None
    if any(ord(zeichen) < 33 or ord(zeichen) > 126 for zeichen in wert):
        return _befund(TOKEN_VARIABLE, FORMAT,
                       f"{TOKEN_VARIABLE} enthält Zeichen, die kein HTTP-Header zulässt "
                       "(z. B. Zeilenumbruch oder Leerzeichen)."), None
    if len(wert) < 20:
        return _befund(TOKEN_VARIABLE, FORMAT,
                       f"{TOKEN_VARIABLE} ist zu kurz für einen Cloudflare-API-Token."), None
    return _befund(TOKEN_VARIABLE, OK, f"{TOKEN_VARIABLE} ist hinterlegt."), wert


def _konto_pruefung(umgebung: dict) -> tuple[Befund, str | None]:
    wert = (umgebung.get(KONTO_VARIABLE) or "").strip()
    if not wert:
        return _befund(KONTO_VARIABLE, FEHLT,
                       f"{KONTO_VARIABLE} ist im Environment {ENVIRONMENT} nicht lesbar."), None
    if not wrr.KONTO_ID.fullmatch(wert):
        return _befund(KONTO_VARIABLE, FORMAT,
                       f"{KONTO_VARIABLE} hat nicht das erwartete Format "
                       "(32 Hexzeichen); der Wert wird nicht geraten."), None
    return _befund(KONTO_VARIABLE, OK, f"{KONTO_VARIABLE} ist hinterlegt und hat "
                                       "das erwartete Format."), wert.lower()


def _token_gueltig(token: str, hole) -> Befund:
    """`GET /user/tokens/verify` – belegt, ob der Token überhaupt lebt."""
    try:
        status, daten = hole(f"{CF_API}/user/tokens/verify", token)
    except Netzfehler as fehler:
        return _befund("Token-Gültigkeit", NETZ,
                       f"Cloudflare war nicht erreichbar ({fehler}); der Token ist "
                       "weder bestätigt noch widerlegt.")
    if status in (401, 403):
        return _befund("Token-Gültigkeit", UNGUELTIG,
                       f"Cloudflare hat den Token abgelehnt (HTTP {status}).")
    if status == 429 or status >= 500:
        return _befund("Token-Gültigkeit", NETZ,
                       f"Cloudflare antwortet vorübergehend nicht prüfbar (HTTP {status}).")
    if status != 200 or not isinstance(daten, dict) or daten.get("success") is not True:
        return _befund("Token-Gültigkeit", UNGUELTIG,
                       f"Die Token-Prüfung war nicht erfolgreich (HTTP {status}).")
    ergebnis = daten.get("result")
    zustand = ergebnis.get("status") if isinstance(ergebnis, dict) else None
    if zustand != "active":
        return _befund("Token-Gültigkeit", UNGUELTIG,
                       f"Der Token ist nicht aktiv (Zustand: {str(zustand)[:32]}).")
    return _befund("Token-Gültigkeit", OK, "Der Token ist aktiv.")


def _ressourcen_pruefung(name: str, umgebung: dict, token: str | None,
                         konto: str | None, hole) -> list[Befund]:
    """Bindung eines Workers – oder, mit gültiger Repository-Variable, entbehrlich."""
    ressource = wrr.RESSOURCEN.get(name)
    if ressource is None:
        return [_befund(f"{name} · Ressource", OK,
                        f"{name} benötigt keine KV-/D1-Ressource.")]
    explizit = (umgebung.get(ressource.variable) or "").strip()
    if explizit:
        if ressource.muster.fullmatch(explizit):
            return [_befund(f"{name} · Ressource", OK,
                            f"{ressource.variable} ist als Repository-Variable gültig gesetzt; "
                            "die Bindung muss dafür nicht gelesen werden.")]
        return [_befund(f"{name} · Ressource", FORMAT,
                        f"Repository-Variable {ressource.variable} hat kein gültiges Format; "
                        "sie wird nicht durch eine geratene Alternative ersetzt.")]
    if token is None or konto is None:
        return [_befund(f"{name} · Ressource", OFFEN,
                        f"Nicht prüfbar: {TOKEN_VARIABLE} bzw. {KONTO_VARIABLE} fehlt. "
                        f"Ohne {ressource.variable} oder lesbaren Token bricht der Deploy ab.")]
    try:
        status, daten = hole(f"{CF_API}/accounts/{konto}/workers/scripts/"
                             f"{ressource.script}/settings", token)
    except Netzfehler as fehler:
        return [_befund(f"{name} · Ressource", NETZ,
                        f"Cloudflare war nicht erreichbar ({fehler}); Bindung {ressource.binding} "
                        "ist weder bestätigt noch widerlegt.")]
    if status in (401, 403):
        return [_befund(f"{name} · Ressource", RECHT,
                        f"Der Token darf die Einstellungen von {ressource.script} nicht lesen "
                        f"(HTTP {status}); benötigt wird Workers Scripts: Read.")]
    if status == 404:
        return [_befund(f"{name} · Ressource", UNBEKANNT,
                        f"{ressource.script} ist in diesem Konto nicht lesbar (HTTP 404). "
                        "Es wird kein Ersatzspeicher angelegt.")]
    if status == 429 or status >= 500:
        return [_befund(f"{name} · Ressource", NETZ,
                        f"Cloudflare-Einstellungen sind vorübergehend nicht lesbar (HTTP {status}).")]
    if status != 200 or daten is None:
        return [_befund(f"{name} · Ressource", UNBEKANNT,
                        f"Die Einstellungen von {ressource.script} wurden nicht geliefert "
                        f"(HTTP {status}).")]
    try:
        wrr.binding_id(daten, ressource)
    except wrr.RessourcenFehler as fehler:
        return [_befund(f"{name} · Ressource", BINDUNG, str(fehler))]
    return [_befund(f"{name} · Ressource", OK,
                    f"Die produktive Bindung {ressource.binding} von {ressource.script} ist "
                    "eindeutig lesbar (ID wird nur in die Lauf-Ausgabe geschrieben).")]


def pruefen(umgebung: dict | None = None, *, hole=None,
            worker: str | None = None) -> list[Befund]:
    """Erhebt ALLE Befunde eines Laufs, ohne beim ersten abzubrechen."""
    umgebung = os.environ if umgebung is None else umgebung
    if worker is not None and worker not in AUTOMATISCHE_WORKER:
        raise Werkzeugfehler(f"Unbekannter automatischer Worker: {worker}")
    ziele = (worker,) if worker else AUTOMATISCHE_WORKER
    hole = hole or _hole

    befunde: list[Befund] = []
    token_befund, token = _token_pruefung(umgebung)
    konto_befund, konto = _konto_pruefung(umgebung)
    befunde.append(token_befund)
    befunde.append(konto_befund)

    if token is None:
        befunde.append(_befund("Token-Gültigkeit", OFFEN,
                               f"Nicht prüfbar, solange {TOKEN_VARIABLE} fehlt."))
    else:
        befunde.append(_token_gueltig(token, hole))

    for name in ziele:
        befunde.extend(_ressourcen_pruefung(name, umgebung, token, konto, hole))
    return befunde


def urteil(befunde: list[Befund]) -> tuple[bool, str]:
    """(deploybar, Kurzurteil). `OFFEN` zählt nie als Beleg."""
    blocker = [b for b in befunde if b.klasse != OK]
    if not blocker:
        return True, "Alle Voraussetzungen des Deploys sind belegt."
    fehlend = sorted({b.klasse for b in blocker})
    return False, (f"{len(blocker)} Befund(e) · Klassen: {', '.join(fehlend)}. "
                   f"Der Deploy bleibt fail-closed; nichts wurde angelegt oder geändert.")


# ------------------------------------------------------------
#  Ausgabe: Dossier, JSON, Annotationen – nie Werte
# ------------------------------------------------------------
def _maskiere(text: str, umgebung: dict) -> str:
    """Entfernt Token-, Konto- und Ressourcen-IDs aus einem beliebigen Text."""
    werte: list[str] = []
    for variable in (TOKEN_VARIABLE, KONTO_VARIABLE, "KV_NAMESPACE_ID_ABO", "D1_DATABASE_ID"):
        wert = (umgebung.get(variable) or "").strip()
        if len(wert) >= 6:
            werte.append(wert)
    # Längere zuerst, damit kein Teil eines Treffers stehen bleibt.
    for wert in sorted(werte, key=len, reverse=True):
        text = text.replace(wert, "***")
    return text


def dossier(befunde: list[Befund], umgebung: dict) -> str:
    """Inhaber-Vorlage: was fehlt, wo es hingehört, was danach kommt."""
    deploybar, kurz = urteil(befunde)
    zeilen = [
        "# Deploy-Zugang (Cloudflare)",
        "",
        f"**Urteil:** {'✅ ' if deploybar else '❌ '}{kurz}",
        "",
        "| Prüfung | Befund | Lage |",
        "|---|---|---|",
    ]
    for befund in befunde:
        zeilen.append(f"| {befund.pruefung} | {befund.klasse} | {befund.text} |")
    # Der Inhaber sieht zuerst, was ER tun kann. Ein `OFFEN` ist keine eigene
    # Aufgabe, sondern die Folge einer fehlenden Voraussetzung – es wird
    # deshalb getrennt geführt und nicht als sechster Arbeitsschritt verkauft.
    offene = [b for b in befunde if b.klasse not in (OK, OFFEN)]
    unpruefbar = [b for b in befunde if b.klasse == OFFEN]
    if offene:
        zeilen += ["", "## Was zu tun ist", ""]
        for nummer, befund in enumerate(offene, start=1):
            zeilen.append(f"{nummer}. **{befund.pruefung}** ({befund.klasse}): "
                          f"{befund.text}  \n   → {befund.massnahme}")
    if unpruefbar and offene:
        zeilen += [
            "",
            "**Danach prüft derselbe Lauf automatisch nach:** "
            + ", ".join(b.pruefung for b in unpruefbar)
            + ". Diese Punkte sind heute ausdrücklich NICHT bestätigt.",
        ]
        zeilen += [
            "",
            "**Wo die Werte hingehören:** GitHub → Settings → Environments → "
            f"`{ENVIRONMENT}` → *Environment secrets*: `{TOKEN_VARIABLE}` und "
            f"`{KONTO_VARIABLE}`. Required reviewer und Beschränkung auf Branch `main` "
            "bleiben unverändert.",
            "",
            "**Rechte des Tokens:** Vorlage „Edit Cloudflare Workers“; benötigt werden "
            "Workers Scripts: Read **und** Edit (sowie D1: Edit für den Klick-Zähler), "
            "begrenzt auf dieses Konto.",
            "",
            "**Danach:** Actions → „Cloudflare-Worker deployen“ → *Run workflow* (`main`). "
            "Der erste vollständig grüne Deploy schließt die Meldung WF-829B von selbst.",
            "",
            "**Vorher prüfen, ohne zu deployen:** Actions → „Deploy-Zugang prüfen“ → "
            "*Run workflow* – liest nur, ändert nichts.",
        ]
    zeilen += [
        "",
        "## Grenzen dieser Prüfung",
        "",
        "- Gelesen werden ausschließlich `GET /user/tokens/verify` und die "
        "Script-Einstellungen der beiden automatischen Worker. Es wird nichts "
        "angelegt, geändert oder gelöscht; kein Wrangler, kein Deploy.",
        "- Ein `OFFEN` ist kein Beleg. Es bedeutet: nicht prüfbar, weil eine "
        "Voraussetzung fehlt.",
        "- Token- und Ressourcen-IDs stehen weder im Log noch in dieser Übersicht.",
        "",
        f"Runbook: `{RUNBOOK}`, Abschnitte A4 und D2.",
    ]
    return _maskiere("\n".join(zeilen), umgebung)


def ausgabe(befunde: list[Befund], umgebung: dict, *, md_pfad: str | None,
            als_json: bool) -> int:
    deploybar, kurz = urteil(befunde)
    if als_json:
        print(json.dumps({
            "deploybar": deploybar,
            "urteil": _maskiere(kurz, umgebung),
            "befunde": [{schluessel: _maskiere(str(wert), umgebung)
                         for schluessel, wert in asdict(b).items()} for b in befunde],
        }, ensure_ascii=False))
    else:
        for befund in befunde:
            zeichen = "✅" if befund.gruen else "❌"
            print(f"{zeichen} [{befund.klasse}] {befund.pruefung}: {befund.text}")
        print(("✅ " if deploybar else "❌ ") + kurz)
    if md_pfad:
        text = dossier(befunde, umgebung)
        if md_pfad == "-":
            print(text)
        else:
            with open(md_pfad, "a", encoding="utf-8") as datei:
                datei.write(text + "\n\n")
    if not deploybar:
        # Nur eigenständige Befunde werden Annotation: `OFFEN` ist immer die
        # Folge eines anderen Befunds und würde dieselbe Ursache nur doppelt
        # melden (Annotation-Lärm ist die Klasse, die #829B unsichtbar machte).
        for befund in befunde:
            if befund.klasse not in (OK, OFFEN):
                gk.annotation("error", f"[{befund.klasse}] {befund.pruefung}: {befund.text}",
                              titel="Deploy-Zugang")
    return 0 if deploybar else 1


# ------------------------------------------------------------
#  Selbsttest: Sabotage ohne Netz
# ------------------------------------------------------------
def _selftest() -> int:
    fehler: list[str] = []
    token = "t" * 40
    konto = "c" * 32
    kv = "b" * 32

    def antwort(status: int, koerper: dict | None):
        return lambda url, _tok: (status, koerper)

    ok_umgebung = {
        TOKEN_VARIABLE: token,
        KONTO_VARIABLE: konto,
        "KV_NAMESPACE_ID_ABO": kv,
    }

    def ok_hole(url: str, _token: str):
        if url.endswith("/user/tokens/verify"):
            return 200, {"success": True, "result": {"status": "active"}}
        if "ff-newsletter" in url:
            return 200, {"success": True, "result": {"bindings": [
                {"type": "kv_namespace", "name": "ABO", "namespace_id": "d" * 32}]}}
        return 200, {"success": True, "result": {"bindings": [
            {"type": "d1", "name": "DB", "id": "12345678-1234-1234-1234-123456789abc"}]}}

    # 1. Gesunder Zugang: alles grün, deploybar.
    gesund = pruefen(ok_umgebung, hole=ok_hole)
    if not all(b.gruen for b in gesund):
        fehler.append("gesunder Zugang wurde nicht grün bewertet")
    if not urteil(gesund)[0]:
        fehler.append("gesunder Zugang gilt nicht als deploybar")

    # 2. SAMMELN STATT KURZSCHLIESSEN: fehlender Token UND fehlende Konto-ID
    #    müssen zusammen erscheinen – nicht nur der erste Befund.
    leer = pruefen({}, hole=ok_hole)
    klassen = {b.pruefung: b.klasse for b in leer}
    if klassen.get(TOKEN_VARIABLE) != FEHLT:
        fehler.append("fehlender Token nicht als FEHLT gemeldet")
    if klassen.get(KONTO_VARIABLE) != FEHLT:
        fehler.append("fehlende Konto-ID nicht als FEHLT gemeldet (kurzgeschlossen)")
    if not any(b.klasse == OFFEN for b in leer):
        fehler.append("Unprüfbares wurde nicht als OFFEN gekennzeichnet")
    if urteil(leer)[0]:
        fehler.append("leerer Zugang galt als deploybar")

    # 3. Ungültige Konto-ID ist ein Formatbefund, kein Ratefall.
    falsch = pruefen({TOKEN_VARIABLE: token, KONTO_VARIABLE: "nicht-hex"}, hole=ok_hole)
    if {b.pruefung: b.klasse for b in falsch}.get(KONTO_VARIABLE) != FORMAT:
        fehler.append("ungültige Konto-ID nicht als FORMAT gemeldet")

    # 4. Abgelehnter Token.
    abgelehnt = pruefen(ok_umgebung, hole=antwort(401, None))
    if not any(b.klasse == UNGUELTIG for b in abgelehnt):
        fehler.append("HTTP 401 nicht als UNGUELTIG gemeldet")

    # 5. Fehlendes Leserecht auf den Worker-Einstellungen.
    def recht(url, _t):
        if url.endswith("/user/tokens/verify"):
            return 200, {"success": True, "result": {"status": "active"}}
        return 403, None
    if not any(b.klasse == RECHT for b in pruefen(ok_umgebung, hole=recht)):
        fehler.append("HTTP 403 nicht als RECHT gemeldet")

    # 6. Mehrdeutige Bindung bleibt gesperrt.
    def doppelt(url, _t):
        if url.endswith("/user/tokens/verify"):
            return 200, {"success": True, "result": {"status": "active"}}
        return 200, {"success": True, "result": {"bindings": [
            {"type": "kv_namespace", "name": "ABO", "namespace_id": "d" * 32},
            {"type": "kv_namespace", "name": "ABO", "namespace_id": "e" * 32}]}}
    if not any(b.klasse == BINDUNG for b in pruefen(ok_umgebung, hole=doppelt)):
        fehler.append("mehrdeutige Bindung nicht als BINDUNG gemeldet")

    # 7. Netzstörung ist ein NETZ-Befund, kein Zugangsfehler und kein Absturz.
    def kaputt(url, _t):
        raise Netzfehler("Timeout")
    if not any(b.klasse == NETZ for b in pruefen(ok_umgebung, hole=kaputt)):
        fehler.append("Netzstörung nicht als NETZ gemeldet")

    # 8. Kein Geheimnis in irgendeiner Ausgabe.
    umgebung = dict(ok_umgebung, D1_DATABASE_ID="12345678-1234-1234-1234-123456789abc")
    bericht = dossier(pruefen({TOKEN_VARIABLE: token, KONTO_VARIABLE: konto}, hole=kaputt),
                      umgebung) + dossier(leer, umgebung)
    for wert in (token, konto, kv, "12345678-1234-1234-1234-123456789abc"):
        if wert in bericht:
            fehler.append(f"Dossier enthält einen Wert aus der Umgebung ({wert[:4]}…)")

    # 9. Unbekannter Worker ist ein Werkzeugfehler, kein stilles Überspringen.
    try:
        pruefen(ok_umgebung, hole=ok_hole, worker="gibt-es-nicht")
        fehler.append("unbekannter Worker wurde stillschweigend akzeptiert")
    except Werkzeugfehler:
        pass

    # 10. Die Prüfung selbst schreibt und ändert nichts in Cloudflare:
    #     jeder Transportaufruf ist ein GET auf einen festen Endpunkt.
    aufrufe: list[str] = []

    def mitschreiben(url, _t):
        aufrufe.append(url)
        return ok_hole(url, _t)
    pruefen(dict(ok_umgebung, KV_NAMESPACE_ID_ABO=""), hole=mitschreiben)
    if any("?" in url or "#" in url for url in aufrufe):
        fehler.append("Transport hat Abfrage- oder Fragmentteile benutzt")
    if not all(url.startswith(CF_API + "/") for url in aufrufe):
        fehler.append("Transport hat einen fremden Endpunkt benutzt")

    for eintrag in fehler:
        gk.annotation("error", eintrag, titel="Selbsttest Deploy-Zugang")
    if fehler:
        print(f"❌ SELBSTTEST FEHLGESCHLAGEN ({len(fehler)} Fälle)")
        return 2
    print("✅ SELBSTTEST OK — Sammelbefund, Klassen, Maskierung und Grenzen belegt; kein Netz.")
    return 0


def main(argv: list[str] | None = None) -> int:
    zerleger = argparse.ArgumentParser(description=__doc__,
                                       formatter_class=argparse.RawDescriptionHelpFormatter)
    zerleger.add_argument("--pruefen", action="store_true",
                          help="Zugang lesend prüfen (Exit 1 bei Befund)")
    zerleger.add_argument("--worker", choices=AUTOMATISCHE_WORKER,
                          help="nur einen Worker prüfen")
    zerleger.add_argument("--md", metavar="PFAD",
                          help="Dossier anhängen ('-' schreibt auf stdout)")
    zerleger.add_argument("--json", action="store_true", help="Maschinenausgabe")
    zerleger.add_argument("--selftest", action="store_true", help="Logik-Beweis ohne Netz")
    args = zerleger.parse_args(argv)

    if args.selftest:
        return _selftest()
    if not args.pruefen:
        zerleger.print_help()
        return 0
    try:
        befunde = pruefen(os.environ, worker=args.worker)
    except Werkzeugfehler as fehler:
        print(f"::error::Deploy-Zugangsprüfung abgebrochen (Werkzeugfehler): {fehler}")
        return 2
    return ausgabe(befunde, os.environ, md_pfad=args.md, als_json=args.json)


if __name__ == "__main__":
    sys.exit(main())
