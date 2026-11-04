#!/usr/bin/env python3
"""Belegketten-Wache: Prüft, ob die zitierten Quellen noch die zitierten sind.

WARUM DIESE WACHE (Prüfqueue #826, 24.10.2026)
----------------------------------------------
Zwei reale Fälle aus der redaktionellen Prüfung dieses Tages:

* Die Verbraucherzentrale hat ihre Seiten umgezogen. Drei der sechs in
  Hochrisiko-Artikeln zitierten URLs antworteten mit **404** – darunter die
  Unfallversicherungs-Seite, auf der fast das ganze Prüfprotokoll eines
  Artikels aufbaute.
* Die zitierte GDV-Seite existierte weiter, zeigte aber unter derselben
  Adresse einen **anderen Artikel mit anderen Zahlen** (Regionalklassen 2027
  statt der zitierten 2026er-Werte). Die Belegkette war damit nicht „tot“,
  sondern schlimmer: sie widersprach dem Text, den sie belegen sollte.

Beides sieht das Freigabe-Gate nicht. Es prüft den Text, nicht das Netz. Das
``--seal``-Siegel bindet die Fassung, nicht die Quelle. Und ``faktenfrische``
erhebt Recherche-Signale, prüft aber keine Zitate.

Was diese Wache deshalb tut: Sie liest die Belegketten (``quellen``) des
Bestands, ruft jede URL genau einmal ab und meldet drei Zustände:

======  ===================================================================
ok      HTTP 200 unter genau der zitierten Adresse
umgeleitet  HTTP 200, aber unter anderer Adresse – Inhalt kann abweichen
tot     HTTP 4xx (außer 429) – die Belegkette trägt nichts mehr
======  ===================================================================

Netzfehler (Timeout, DNS, 5xx, 403, 429) gelten als **unklar** und blockieren
im Diagnosemodus nicht: Eine Wache, die bei jedem Wackler rot wird, wird abgeschaltet statt
gelesen. Ein definitives 404 dagegen ist ein Befund. Für automatische
Queue-Erledigung verlangt ``--require-complete`` zusätzlich einen Abruf ohne
unklare oder umgeleitete Quellen. Lesefehler blockieren immer mit ``--strict``.

Die Wache schreibt keinen Inhalt. Sie entscheidet nichts. Sie zeigt nur,
wo eine Prüfung fällig ist – die Entscheidung bleibt redaktionell.

WARUM DER AMTLICHE TEXT NICHT DIREKT GELESEN WIRD (04.11.2026, #1024)
--------------------------------------------------------------------
`www.gesetze-im-internet.de` verwirft TCP-Verbindungen aus den Netzen der
CI-Runner (`URLError` nach SSL-EOF, nicht nach Inhalt). Für den Beleg ist
das kein Urteil über die Quelle, sondern über den Messweg. Der tägliche
Bundesrecht-Spiegel `Gesetze-fuer-KI/bundesrecht` übernimmt dieselben
amtlichen Texte jede Nacht; gemessen wird deshalb am SPIEGEL, wenn der
Direktabruf nicht belastbar ist.

Drei Fehler in dieser Ausweichmessung sind am 03.11.2026 aufgefallen und
hier dauerhaft geheilt:

1. `sicherer_abruf()` liefert ein **3-Tupel** `(status, kopf, roh)`. Die
   Abruffunktion entpackte es als 2-Tupel – `ValueError: too many values
   to unpack (expected 2)` –, und ein `except Exception:` tarnte diesen
   PROGRAMMIERFEHLER als „unklar“. Vier gültige Bundesrechts-Zitate
   standen dadurch dauerhaft als unprüfbar in der YMYL-Queue (#1024).
2. Der Spiegelschlüssel wurde aus den ersten zwei Zeichen des Slugs
   gebildet (`vv/vvg_2008.md`, `bg/bgb.md`, `go/got_2022.md`). Das ist
   die Ablageordnung des Spiegels, aber nirgends festgeschrieben; sie
   stand als stilles Wissen im Code. Fällt eine Datei aus der Ordnung,
   meldet die Wache fälschlich „Gesetz aufgehoben“.
3. `except Exception:` deckte auch Tippfehler, Attribut- und Typfehler zu.
   Ein Werkzeug, das seinen eigenen Defekt als Quelleigenschaft ausgibt,
   ist schlimmer als kein Werkzeug.

Deshalb gilt jetzt: Netzfehler sind eine **abgeschlossene Liste**
(`NETZ_AUSNAHMEN`); alles andere schlägt mit Exit 2 durch. Der Spiegel
wird über die GitHub-API adressiert (`Accept: application/vnd.github.raw`),
weil dieser Weg auch Dateien über 1 MB liefert (`bg/bgb.md` hat 1,7 MB)
und weil er den `GH_TOKEN` für das Kontingent zulässt – ohne ihn
antwortet die API unauthentifiziert bei 60 Abrufen pro Stunde.

AUFRUF
------
  python3 scripts/belegketten_wache.py                       # Bestand
  python3 scripts/belegketten_wache.py --nur-hochrisiko      # YMYL
  python3 scripts/belegketten_wache.py --nur-hochrisiko --strict --report
  python3 scripts/belegketten_wache.py --nur-hochrisiko --require-complete --json
  python3 scripts/belegketten_wache.py --probe-bundesrecht   # Messweg beweisen
  python3 scripts/belegketten_wache.py --selftest            # offline

EXIT
----
  0 = keine blockierende Quelle · 1 = Befund (`--strict`/`--require-complete`)
  2 = WERKZEUGFEHLER (Programmierfehler, Netzklasse außerhalb der Liste).
  Der Unterschied ist der ganze Punkt: Ein Befund ist eine Aussage über
  die Quelle, Exit 2 eine Aussage über dieses Skript.
"""
from __future__ import annotations

import argparse
import datetime as dt
import http.client
import json
import os
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote, urlparse

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import yaml  # noqa: E402  (Frontmatter-Fehler sind ein DATENbefund)
import editorial_review_gate as gate  # noqa: E402  (eine Regelquelle)
from url_host import ist_host_oder_subdomain  # noqa: E402  (Host-Wahrheit)

REPORT = ROOT / "BELEGKETTEN-WACHE-REPORT.md"
USER_AGENT = "FranksFinanzcheck-Belegketten-Wache/1.0 (+https://franksfinanzcheck.de)"
TOT = "tot"
UMGELEITET = "umgeleitet"
UNKLAR = "unklar"
OK = "ok"

_GII_BASIS_HOST = "gesetze-im-internet.de"
_GII_SPIEGEL_BASIS = "https://raw.githubusercontent.com/Gesetze-fuer-KI/bundesrecht/main"
# Die API-Adresse ist der Rückfallweg für Dateien über 1 MB (raw.githubusercontent
# begrenzt nicht, die API schon – aber nur sie liefert bei großen Dateien den
# vollständigen Inhalt mit `Accept: application/vnd.github.raw`, und nur sie
# nimmt den Token für das Kontingent an).
_GII_SPIEGEL_API = "https://api.github.com/repos/Gesetze-fuer-KI/bundesrecht/contents"
_GII_MAX_BYTES = 8 * 1024 * 1024
# Ablageordnung des Spiegels: die ersten ZWEI Zeichen der GII-Kennung.
# `vvg_2008` → `vv/`, `bgb` → `bg/` (Artikel „bg/bgb.md“ der Spiegel-README),
# `got_2022` → `go/`, `estg` → `es/`. Für Kennungen, die mit einer Ziffer
# beginnen, gibt es den Sammelordner `0-9`.
_GII_SHARD_LAENGE = 2
_GII_SLUG_ZEICHEN = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_-")
_GII_NORM_ZEICHEN = frozenset("abcdefghijklmnopqrstuvwxyz0123456789")

# Netzfehler, die eine AUSSAGE ÜBER DEN MESSWEG sind – nicht über die Quelle.
# Nur diese Klassen dürfen einen Abruf „unklar“ machen. Ein Tippfehler, ein
# Attributfehler oder ein falsch entpacktes Tupel gehört NICHT hierher: Er ist
# ein Defekt dieses Skripts und muss mit Exit 2 durchschlagen (#1024).
NETZ_AUSNAHMEN = (
    urllib.error.URLError,
    urllib.error.HTTPError,
    http.client.HTTPException,
    socket.timeout,
    TimeoutError,
    ConnectionError,
    ssl.SSLError,
    OSError,
)

# Wiederholungen bei transienten PSI-/Netz-Antworten. Zwei Versuche mit
# kurzer Pause: ein Wackler ist kein Befund, ein Dauerausfall bleibt einer.
_GII_VERSUCHE = 2
_GII_PAUSE_SEKUNDEN = 1.5
_GII_TRANSIENT_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})


def _normalisiert(url: str) -> tuple[str, str, str]:
    """Vergleichsform einer URL: Host ohne www, Pfad ohne Schlussschräge."""
    try:
        teile = urlparse(url)
    except ValueError:
        return ("", "", "")
    host = (teile.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return (host, teile.path.rstrip("/") or "/", teile.query or "")


SPRACHSEGMENTE = {"de", "en", "at", "ch"}


def _nur_sprachpfad(zitat: str, end_url: str) -> bool:
    """Weiterleitung, die nur den Sprachpfad der GLEICHEN Seite ergänzt.

    Befund 26.10.2026 (Prüfqueue #826): `https://kontenvergleich.bafin.de/`
    antwortet mit 200 auf `…/de`. Die Wache meldete das als „anderer Endpunkt"
    – zwei Artikel standen dadurch dauerhaft als Prüfauftrag in der YMYL-Queue,
    obwohl unter dem Ziel dieselbe Seite in der deutschen Fassung liegt. Ein
    Sprachpräfix ist aber ein Umzug des Inhaltsverzeichnisses, kein
    Inhaltswechsel: Host und Restschicht müssen identisch sein, und der
    zusätzliche Pfad darf ausschließlich aus genau einem Sprachsegment
    bestehen. Alles andere bleibt `umgeleitet` (Prüfauftrag).
    """
    try:
        zitat_teile = urlparse(zitat)
        ziel_teile = urlparse(end_url)
    except ValueError:
        return False
    zitat_host = (zitat_teile.hostname or "").lower().removeprefix("www.")
    ziel_host = (ziel_teile.hostname or "").lower().removeprefix("www.")
    if not zitat_host or zitat_host != ziel_host:
        return False
    if (zitat_teile.query or "") != (ziel_teile.query or ""):
        return False
    zitat_pfad = zitat_teile.path.rstrip("/")
    ziel_pfad = ziel_teile.path.rstrip("/")
    if zitat_pfad == ziel_pfad:
        return True
    ziel_segmente = [s for s in ziel_pfad.split("/") if s]
    zitat_segmente = [s for s in zitat_pfad.split("/") if s]
    return (len(ziel_segmente) == len(zitat_segmente) + 1
            and ziel_segmente[0].lower() in SPRACHSEGMENTE
            and ziel_segmente[1:] == zitat_segmente)


def abruf_http(url: str, timeout: float = 10.0) -> tuple[int, str]:
    """Ein GET mit sicherer Weiterleitungsverfolgung. Gibt (Status, End-URL) zurück."""
    from net_safety import sicherer_abruf_status

    return sicherer_abruf_status(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
        erlaube_loopback=False,
    )


def _github_kopf(*, roh: bool) -> dict[str, str]:
    """Kopfzeilen für GitHub.

    `GH_TOKEN` geht AUSSCHLIESSLICH an `api.github.com`. Ein Bearer-Token an
    `raw.githubusercontent.com` wäre ein Geheimnis auf einem Weg, der es
    nicht braucht – und der Rohweg kennt kein Kontingent, das es lohnt.
    """
    kopf = {
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github.raw" if roh else "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    return kopf


def _github_token() -> str:
    """Kontingent-Schlüssel für `api.github.com` – wird nie ausgegeben."""
    return (os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or "").strip()


def _spiegel_abruf(url: str, *, timeout: float) -> tuple[int, bytes]:
    """Ein Abruf des Spiegels über `net_safety` – mit dem 3-Tupel-Vertrag.

    DER FEHLER VON #1024: `sicherer_abruf()` gibt `(status, kopf, roh)` zurück.
    Wer es als 2-Tupel entpackt, bekommt einen `ValueError` – und ein
    `except Exception:` machte daraus „Quelle unklar“. Hier wird der Vertrag
    deshalb EINMAL an genau einer Stelle ausgepackt, benannt und geprüft.
    """
    from net_safety import sicherer_abruf

    ist_api = _normalisiert(url)[0] == _normalisiert(_GII_SPIEGEL_API)[0]
    kopf = _github_kopf(roh=ist_api)
    token = _github_token()
    if ist_api and token:
        kopf["Authorization"] = f"Bearer {token}"
    status, _antwort_kopf, roh = sicherer_abruf(
        url,
        headers=kopf,
        timeout=timeout,
        max_bytes=_GII_MAX_BYTES,
        erlaube_loopback=False,
    )
    return int(status), bytes(roh or b"")


def abruf_gii_spiegel_http(url: str, timeout: float = 10.0,
                           *, abruf=None, versuche: int = _GII_VERSUCHE) -> tuple[int, bytes]:
    """Lädt eine Datei des täglichen Bundesrecht-Spiegels: (Status, Rohbytes).

    Wiederholt wird AUSSCHLIESSLICH, was transient ist (408/425/429/5xx und
    reine Netzabbrüche). Ein 403 oder 404 wiederholt sich nicht – ein
    Wiederholen würde nur das Kontingent des Spiegels verbrauchen und die
    Laufzeit verlängern, ohne eine andere Antwort zu bekommen. Danach wird
    der Status GEMELDET, nicht geschluckt: Was daraus folgt, entscheidet
    `pruefe_quelle`.
    """
    abruf = abruf or _spiegel_abruf
    letzter_status = 0
    gesamt = max(1, versuche)
    for versuch in range(gesamt):
        wiederholen = versuch + 1 < gesamt
        try:
            status, roh = abruf(url, timeout=timeout)
        except urllib.error.HTTPError as exc:
            letzter_status = int(exc.code)
            if letzter_status in _GII_TRANSIENT_STATUS and wiederholen:
                time.sleep(_GII_PAUSE_SEKUNDEN)
                continue
            return letzter_status, b""
        except NETZ_AUSNAHMEN:
            if wiederholen:
                time.sleep(_GII_PAUSE_SEKUNDEN)
                continue
            raise
        letzter_status = int(status)
        if letzter_status not in _GII_TRANSIENT_STATUS:
            return letzter_status, roh
        if wiederholen:
            time.sleep(_GII_PAUSE_SEKUNDEN)
    return letzter_status, b""


def _gii_shard(slug: str) -> str:
    """Ablageordner des Spiegels für eine GII-Kennung (eine Stelle, ein Grund)."""
    return ("0-9" if slug[0].isdigit()
            else slug[:_GII_SHARD_LAENGE].replace("-", "_"))


def _gii_spiegel_url(slug: str) -> str:
    """Primärweg: Raw-Adresse im täglichen Bundesrecht-Spiegel."""
    return f"{_GII_SPIEGEL_BASIS}/{_gii_shard(slug)}/{quote(slug, safe='')}.md"


def _gii_spiegel_api_url(slug: str) -> str:
    """Rückfallweg über die GitHub-API (Dateien > 1 MB, Kontingent mit Token)."""
    return (f"{_GII_SPIEGEL_API}/{_gii_shard(slug)}/{quote(slug, safe='')}.md"
            "?ref=main")


def _spiegel_primaer(slug: str, *, timeout: float, abruf) -> tuple[int, bytes]:
    """Raw-Abruf – GENAU EIN Versuch.

    Der Rückfall auf `api.github.com` ist der zweite Versuch; ein eigener
    Retry davor würde dasselbe Kontingent zweimal belasten und den Lauf
    verlängern, ohne eine andere Antwort zu bekommen.
    """
    try:
        return abruf_gii_spiegel_http(_gii_spiegel_url(slug), timeout,
                                      abruf=abruf, versuche=1)
    except urllib.error.HTTPError as exc:
        return int(exc.code), b""
    except NETZ_AUSNAHMEN:
        return 0, b""


def abruf_gii_spiegel(slug: str, timeout: float = 10.0, *,
                      abruf=None) -> tuple[int, str]:
    """Zweistufiger Abruf; gibt (Status, TEXT) zurück (UTF-8, verlustarm)."""
    """Zweistufiger Spiegelabruf: Raw zuerst, `api.github.com` als Rückfall.

    Beide Wege liefern denselben Dateiinhalt; der zweite existiert, weil
    `raw.githubusercontent.com` bei großen Dateien und ohne Token unzuverlässig
    ist (Kontingent, Rate-Limit). Scheitern beide, bleibt der Status des
    PRIMÄRWEGS stehen – er beschreibt, was der Messweg gesagt hat.
    """
    abruf = abruf or _spiegel_abruf
    status, roh = _spiegel_primaer(slug, timeout=timeout, abruf=abruf)
    if 200 <= status < 300 and roh:
        return status, _dekodiere(roh)
    if status in (404, 410):
        # Endgültige Auskunft des Spiegels – kein zweiter Weg nötig.
        return status, ""
    api_status, api_roh = 0, b""
    try:
        api_status, api_roh = abruf_gii_spiegel_http(
            _gii_spiegel_api_url(slug), timeout, abruf=abruf)
    except urllib.error.HTTPError as exc:
        api_status = int(exc.code)
    except NETZ_AUSNAHMEN:
        api_status = 0
    if 200 <= api_status < 300 and api_roh:
        return api_status, _dekodiere(api_roh)
    return status or api_status, ""


def _dekodiere(roh: bytes | str) -> str:
    """Ein Abrufergebnis als Text. Bytes und Text sind beide zulässig,
    weil Tests Attrappen in der jeweils bequemeren Form stellen dürfen."""
    return roh.decode("utf-8", errors="replace") if isinstance(roh, bytes) else str(roh)


def probe_bundesrecht(urls: list[str] | None = None, *, timeout: float = 15.0) -> int:
    """Live-Nachweis des Messwegs für die Bundesrechts-Zitate (`--probe-bundesrecht`).

    Diese Probe ist KEIN Gate (sie braucht Netz und ist damit nicht
    reproduzierbar); sie beantwortet im Betrieb die eine Frage, die kein
    Selbsttest beantworten kann: Kommt der amtliche Text über den Spiegel
    wirklich an? Aufruf im YMYL-Workflow als eigener Schritt mit
    `continue-on-error: true` – ein Netzausfall darf die Silbe nicht rot machen.
    """
    geprueft = urls or [
        "https://www.gesetze-im-internet.de/vvg_2008/__40.html",
        "https://www.gesetze-im-internet.de/vvg_2008/__96.html",
        "https://www.gesetze-im-internet.de/bgb/__502.html",
        "https://www.gesetze-im-internet.de/got_2022/",
    ]
    fehler = 0
    for url in geprueft:
        zerlegt = _parse_gii_ziel(url)
        if zerlegt is None:
            print(f"❔ {url} – keine kanonische GII-Adresse (nichts zu prüfen)")
            continue
        slug, einzelnorm = zerlegt
        status, inhalt = abruf_gii_spiegel(slug, timeout)
        quelle_ok = _spiegel_bestaetigt_quelle(inhalt, slug) if status == 200 else False
        norm_ok = True
        bezeichnung = ""
        if quelle_ok and einzelnorm is not None:
            gefunden, aktiv = _spiegel_pruefe_einzelnorm(inhalt, einzelnorm)
            norm_ok = gefunden and aktiv
            bezeichnung = f"{einzelnorm[0]} {einzelnorm[1]}".strip()
        if not quelle_ok or not norm_ok:
            fehler += 1
            print(f"🛑 {url} → {slug}: HTTP {status}, Quelle bestätigt="
                  f"{quelle_ok}, Norm {bezeichnung or '–'} aktiv={norm_ok}")
            continue
        print(f"✅ {url} → {slug}"
              + (f" · {bezeichnung} aktiv" if bezeichnung else " · Gesamtwerk bestätigt"))
    print(f"Bundesrechts-Messweg: {len(geprueft) - fehler}/{len(geprueft)} Zitate belegt.")
    return 0 if fehler == 0 else 1


def _parse_gii_ziel(zitat: str) -> tuple[str, tuple[str, str] | None] | None:
    """Zerlegt offizielle gesetze-im-internet.de-URLs in (Gesetzes-Slug, Einzelnorm).

    Befund 30.10.2026 (Prüfqueue #826): `www.gesetze-im-internet.de` verwirft
    TCP-Verbindungen von Azure-/GitHub-Actions-Runnern (`URLError` nach Timeout),
    wodurch alle 4 Gesetz-Zitate im Hochrisiko-Bestand (`vvg_2008/__40.html`,
    `bgb/__502.html`, `got_2022/`) dauerhaft `unklar` blieben und
    `--require-complete` das Auto-Schließen blockierte.

    Diese Zerlegung erlaubt ausschließlich kanonische GII-Pfade (Gesamtwerk,
    `__<nr>.html`, `art_<nr>.html`, `anhang.html`, `anlage.html`). Unbekannte
    Pfadformen liefern `None` und bleiben fail-closed `unklar`.
    """
    if not ist_host_oder_subdomain(zitat, _GII_BASIS_HOST):
        return None
    try:
        teile_url = urlparse(zitat)
    except ValueError:
        return None
    if teile_url.query:
        return None
    segmente = [s for s in (teile_url.path or "").split("/") if s]
    if len(segmente) not in (1, 2):
        return None
    slug = segmente[0].lower()
    if not slug or len(slug) > 80 or any(c not in _GII_SLUG_ZEICHEN for c in slug):
        return None
    if len(segmente) == 1:
        return slug, None
    datei = segmente[1].lower()
    if datei == "index.html" or (
        datei.startswith("bjnr")
        and datei.endswith(".html")
        and len(datei) > 9
        and all(c in _GII_NORM_ZEICHEN for c in datei[4:-5])
    ):
        return slug, None
    if datei == "anhang.html":
        return slug, ("Anhang", "")
    if datei == "anlage.html":
        return slug, ("Anlage", "")
    if datei.startswith("__") and datei.endswith(".html"):
        nr = datei[2:-5]
        if nr and len(nr) <= 16 and all(c in _GII_NORM_ZEICHEN for c in nr):
            return slug, ("§", nr)
        return None
    if datei.startswith("art_") and datei.endswith(".html"):
        nr = datei[4:-5]
        if nr and len(nr) <= 16 and all(c in _GII_NORM_ZEICHEN for c in nr):
            return slug, ("Art.", nr)
        return None
    return None


def _gii_spiegel_url(slug: str) -> str:
    """Deterministischer Pfad im täglichen Bundesrecht-Spiegel (gii-toc.xml)."""
    shard = (
        "0-9"
        if slug[0].isdigit()
        else "".join(c if c.isalnum() else "_" for c in slug[:2])
    )
    return f"{_GII_SPIEGEL_BASIS}/{shard}/{slug}.md"


def _spiegel_bestaetigt_quelle(inhalt: str, slug: str) -> bool:
    """Prüft im YAML-Kopf des Spiegels, dass die Datei genau vom GII-Slug stammt."""
    zeilen = inhalt.splitlines()
    if not zeilen or zeilen[0].strip() != "---":
        return False
    for zeile in zeilen[1:60]:
        streifen = zeile.strip()
        if streifen == "---":
            break
        if streifen.lower().startswith("quelle:"):
            roh = streifen.split(":", 1)[1].strip().strip("\"'")
            if not ist_host_oder_subdomain(roh, _GII_BASIS_HOST):
                return False
            try:
                pfad = urlparse(roh).path.strip("/").lower()
            except ValueError:
                return False
            return pfad == slug
    return False


def _spiegel_pruefe_einzelnorm(
    inhalt: str, einzelnorm: tuple[str, str]
) -> tuple[bool, bool]:
    """Prüft zeilenweise ohne Backtracking, ob die Einzelnorm existiert und aktiv ist."""
    typ, nr = einzelnorm
    gefunden = False
    aktiv = False
    for zeile in inhalt.splitlines():
        if not zeile.startswith("#"):
            continue
        titel = zeile.lstrip("#").strip().lower()
        if not titel:
            continue
        if typ == "§":
            ziel = f"§ {nr}"
            treffer = titel == ziel or titel.startswith(ziel + " ")
        elif typ == "Art.":
            treffer = any(
                titel == praefix or titel.startswith(praefix + " ")
                for praefix in (f"art. {nr}", f"art {nr}", f"artikel {nr}")
            )
        else:
            praefix = typ.lower()
            treffer = (
                titel == praefix
                or titel.startswith(praefix + " ")
                or titel.startswith(praefix + ":")
            )
        if treffer:
            gefunden = True
            if "(weggefallen)" not in titel:
                aktiv = True
                break
    return gefunden, aktiv


def _pruefe_gii_spiegel(
    zitat: str, basis: dict, *, spiegel_abruf, timeout: float
) -> dict:
    """Fail-closed Normprüfung über den täglichen GII-Spiegel bei Runner-Blockade.

    `spiegel_abruf` bekommt den SLUG (nicht die fertige URL): Der Abrufweg ist
    Sache der Abrufschicht (Raw → API-Rückfall), die Wache entscheidet nur
    über das Ergebnis. Netzfehler sind eine abgeschlossene Liste; alles
    andere schlägt durch (Programmierfehler ≠ Quellenbefund, #1024).
    """
    zerlegt = _parse_gii_ziel(zitat)
    if zerlegt is None:
        return basis
    slug, einzelnorm = zerlegt
    try:
        status, inhalt = spiegel_abruf(slug, timeout=timeout)
    except NETZ_AUSNAHMEN:
        return basis
    if status in (404, 410):
        return {
            "status": TOT,
            "zitat": zitat,
            "end_url": "",
            "befund": (
                f"Gesetz/Verordnung '{slug}' im aktuellen Bundesrechtsbestand "
                f"nicht mehr vorhanden (Spiegel HTTP {status})"
            ),
        }
    if not (200 <= status < 300) or not _spiegel_bestaetigt_quelle(inhalt, slug):
        return basis
    if einzelnorm is not None:
        gefunden, aktiv = _spiegel_pruefe_einzelnorm(inhalt, einzelnorm)
        bezeichnung = f"{einzelnorm[0]} {einzelnorm[1]}".strip()
        if not gefunden:
            return {
                "status": TOT,
                "zitat": zitat,
                "end_url": "",
                "befund": (
                    f"Einzelnorm {bezeichnung} in '{slug}' nicht vorhanden – "
                    "Beleg trägt nicht mehr"
                ),
            }
        if not aktiv:
            return {
                "status": TOT,
                "zitat": zitat,
                "end_url": "",
                "befund": (
                    f"Einzelnorm {bezeichnung} in '{slug}' ist weggefallen – "
                    "Beleg trägt nicht mehr"
                ),
            }
    return {
        "status": OK,
        "zitat": zitat,
        "end_url": zitat,
        "befund": "",
        "hinweis": (
            "Direktabruf durch GII-Runner-Filter blockiert; "
            "aktiver Normbestand über täglichen Bundesrechts-Spiegel bestätigt"
        ),
    }


def pruefe_quelle(
    url: str, *, abruf=None, spiegel_abruf=None, timeout: float = 10.0,
    direkt_timeout: float | None = None,
) -> dict:
    """Ein Zitat prüfen. ``abruf`` und ``spiegel_abruf`` sind injizierbar."""
    nutze_spiegel = spiegel_abruf or (abruf_gii_spiegel if abruf is None else None)
    abruf = abruf or abruf_http
    zitat = str(url or "").strip()
    if not zitat.startswith("https://"):
        return {"status": TOT, "zitat": zitat, "end_url": "",
                "befund": "keine HTTPS-Quelle – als Beleg unzulässig"}
    eff_timeout = timeout if direkt_timeout is None else direkt_timeout
    basis_unklar: dict | None = None
    try:
        status, end_url = abruf(zitat, timeout=eff_timeout)
    except urllib.error.HTTPError as exc:
        if int(exc.code) in (403, 429) or int(exc.code) >= 500:
            basis_unklar = {
                "status": UNKLAR, "zitat": zitat, "end_url": "",
                "befund": f"HTTP {exc.code} – nicht belastbar prüfbar",
            }
        else:
            return {"status": TOT, "zitat": zitat, "end_url": "",
                    "befund": f"HTTP {exc.code} – Beleg nicht mehr abrufbar"}
    except NETZ_AUSNAHMEN as exc:
        # Abgeschlossene Liste: Netzfehler sind ein Befund über den Messweg.
        # Ein NameError/ValueError/TypeError gehört hier NICHT hin – er wäre
        # der Defekt dieses Skripts und muss mit Exit 2 durchschlagen (#1024).
        basis_unklar = {
            "status": UNKLAR, "zitat": zitat, "end_url": "",
            "befund": f"nicht erreichbar ({type(exc).__name__})",
        }
    if basis_unklar is None and (status in (403, 429) or status >= 500):
        basis_unklar = {
            "status": UNKLAR, "zitat": zitat, "end_url": end_url,
            "befund": f"HTTP {status} – nicht belastbar prüfbar",
        }
    if basis_unklar is not None:
        if nutze_spiegel is not None and ist_host_oder_subdomain(zitat, _GII_BASIS_HOST):
            return _pruefe_gii_spiegel(
                zitat, basis_unklar, spiegel_abruf=nutze_spiegel, timeout=timeout,
            )
        return basis_unklar
    if status >= 400:
        return {"status": TOT, "zitat": zitat, "end_url": end_url,
                "befund": f"HTTP {status} – Beleg nicht mehr abrufbar"}
    if _normalisiert(end_url) != _normalisiert(zitat):
        if _nur_sprachpfad(zitat, end_url):
            return {"status": OK, "zitat": zitat, "end_url": end_url,
                    "hinweis": "Sprachpfad kanonisiert (gleicher Host, gleiche Seite)"}
        return {"status": UMGELEITET, "zitat": zitat, "end_url": end_url,
                "befund": "anderer Endpunkt als zitiert – Aussage gegen die neue Fassung prüfen"}
    return {"status": OK, "zitat": zitat, "end_url": end_url, "befund": ""}


def belegketten(*, nur_hochrisiko: bool = False) -> list[dict]:
    """Alle Artikel mit ihren Quellen (slug, risk, review-Status, quellen)."""
    eintraege = []
    for pfad in gate.all_post_paths():
        try:
            fm, _, _ = gate.load_article(pfad)
        except (OSError, ValueError, yaml.YAMLError, KeyError, TypeError):
            # Bewusst aufgezählt statt `except Exception`: Nur eine
            # unlesbare DATEI darf zu einem Befund werden. Ein DEFEKT in
            # `load_article` (Attribut-, Namensfehler) ist ein Werkzeug-
            # fehler und muss mit Exit 2 durchschlagen (#1024).
            eintraege.append({
                "slug": pfad.parent.name, "path": str(pfad.relative_to(ROOT)),
                "risk": "unbekannt", "approved": False, "quellen": [],
                "lesefehler": "Frontmatter nicht auswertbar",
            })
            continue
        risk = gate.inferred_risk(fm)
        if nur_hochrisiko and risk != gate.RISK_HIGH:
            continue
        review = fm.get("redaktionelle_pruefung") or {}
        quellen = fm.get("quellen") or []
        eintraege.append({
            "slug": pfad.parent.name,
            "path": str(pfad.relative_to(ROOT)),
            "risk": risk,
            "approved": bool(review.get("inhalt_sha256")),
            "quellen": [
                {"id": str(q.get("id") or ""), "url": str(q.get("url") or ""),
                 "titel": str(q.get("titel") or "")}
                for q in quellen if isinstance(q, dict)
            ],
        })
    return eintraege


def pruefe_alle(*, nur_hochrisiko: bool = False, abruf=None,
                spiegel_abruf=None, timeout: float = 10.0) -> dict:
    ergebnisse = []
    cache = {}
    gii_direkt_blockiert = False
    for artikel in belegketten(nur_hochrisiko=nur_hochrisiko):
        if artikel.get("lesefehler"):
            ergebnisse.append({
                "status": TOT, "slug": artikel["slug"], "risk": artikel["risk"],
                "approved": False, "id": "Frontmatter", "titel": "",
                "zitat": artikel["path"], "end_url": "",
                "befund": artikel["lesefehler"],
            })
        for quelle in artikel["quellen"]:
            url = quelle["url"]
            if url not in cache:
                ist_gii = ist_host_oder_subdomain(url, _GII_BASIS_HOST)
                d_timeout = min(timeout, 3.0) if (ist_gii and gii_direkt_blockiert) else None
                res = pruefe_quelle(
                    url, abruf=abruf, spiegel_abruf=spiegel_abruf,
                    timeout=timeout, direkt_timeout=d_timeout,
                )
                if ist_gii and (
                    res["status"] == UNKLAR or "GII-Runner-Filter" in str(res.get("hinweis") or "")
                ):
                    gii_direkt_blockiert = True
                cache[url] = res
            # Kopie: Zuordnung eines Artikels darf andere nicht überschreiben.
            ergebnis = dict(cache[url])
            ergebnis.update({
                "slug": artikel["slug"], "risk": artikel["risk"],
                "approved": artikel["approved"], "id": quelle["id"],
                "titel": quelle["titel"],
            })
            ergebnisse.append(ergebnis)
    zaehler = {OK: 0, UMGELEITET: 0, TOT: 0, UNKLAR: 0}
    for eintrag in ergebnisse:
        zaehler[eintrag["status"]] += 1
    blockierend = [e for e in ergebnisse if e["status"] == TOT]
    return {
        "geprueft": len(ergebnisse), "zaehler": zaehler,
        "befunde": [e for e in ergebnisse if e["status"] != OK],
        "blockierend": blockierend,
    }


def _zeile(eintrag: dict) -> str:
    symbol = {OK: "✅", UMGELEITET: "⚠️ ", TOT: "🛑", UNKLAR: "❔"}[eintrag["status"]]
    return (f"  {symbol} {eintrag['slug']} · {eintrag['id']} · "
            f"{eintrag['befund']}\n     {eintrag['zitat']}"
            + (f"\n     → {eintrag['end_url']}" if eintrag.get("end_url")
               and eintrag["status"] == UMGELEITET else ""))


def report_schreiben(ergebnis: dict) -> None:
    zaehler = ergebnis["zaehler"]
    zeilen = [
        "# Belegketten-Wache",
        "",
        f"**Stand:** {dt.date.today().isoformat()} · "
        f"**Wache:** `scripts/belegketten_wache.py`",
        "",
        "> Geprüft wird nur die Erreichbarkeit der zitierten Quelle, nicht die",
        "> Richtigkeit der Aussage. Eine „umgeleitete“ Quelle ist ein Prüfauftrag,",
        "> kein Freispruch: unter derselben Adresse kann ein anderer Text stehen.",
        "",
        f"- Geprüfte Quellen: **{ergebnis['geprueft']}**",
        f"- Unverändert erreichbar: **{zaehler[OK]}**",
        f"- Umgeleitet (Inhalt prüfen): **{zaehler[UMGELEITET]}**",
        f"- Nicht mehr abrufbar: **{zaehler[TOT]}**",
        f"- Nicht prüfbar (Netz/Timeout): **{zaehler[UNKLAR]}**",
        "",
    ]
    if ergebnis["befunde"]:
        zeilen += ["## Befunde", ""]
        for eintrag in ergebnis["befunde"]:
            zeilen += [_zeile(eintrag), ""]
    else:
        zeilen += ["## Befunde", "", "Keine Befunde – alle Belegketten unverändert erreichbar.", ""]
    REPORT.write_text("\n".join(zeilen), encoding="utf-8")


def selftest() -> list[str]:
    """Offline: die vier Zustände und die Weiterleitungslogik."""
    fehler: list[str] = []

    def erwarte(name, bedingung):
        if not bedingung:
            fehler.append(name)

    def abruf_ok(url, timeout=10.0):
        return 200, url

    def abruf_404(url, timeout=10.0):
        raise urllib.error.HTTPError(url, 404, "Not Found", None, None)

    def abruf_500(url, timeout=10.0):
        raise urllib.error.HTTPError(url, 503, "Service Unavailable", None, None)

    def abruf_umzug(url, timeout=10.0):
        return 200, "https://www.verbraucherzentrale.de/wissen/neu-13888"

    def abruf_netz(url, timeout=10.0):
        raise urllib.error.URLError("DNS")

    def abruf_slash(url, timeout=10.0):
        return 200, url.rstrip("/") + "/"

    ziel = "https://www.verbraucherzentrale.de/wissen/alt-13888"
    erwarte("200 ist ok", pruefe_quelle(ziel, abruf=abruf_ok)["status"] == OK)
    erwarte("404 ist tot", pruefe_quelle(ziel, abruf=abruf_404)["status"] == TOT)
    erwarte("503 ist unklar", pruefe_quelle(ziel, abruf=abruf_500)["status"] == UNKLAR)
    erwarte("Netzfehler ist unklar", pruefe_quelle(ziel, abruf=abruf_netz)["status"] == UNKLAR)
    erwarte("Umzug ist umgeleitet",
            pruefe_quelle(ziel, abruf=abruf_umzug)["status"] == UMGELEITET)
    erwarte("Schlussschräge ist kein Umzug",
            pruefe_quelle(ziel, abruf=abruf_slash)["status"] == OK)

    # Sprachpfad (Befund #826): gleiche Seite unter /de – kein Inhaltswechsel.
    def abruf_sprache(url, timeout=10.0):
        return 200, "https://kontenvergleich.bafin.de/de"

    erwarte("Sprachpfad ist kein Umzug",
            pruefe_quelle("https://kontenvergleich.bafin.de/",
                          abruf=abruf_sprache)["status"] == OK)

    def abruf_sprache_anderer_inhalt(url, timeout=10.0):
        return 200, "https://kontenvergleich.bafin.de/de/andere-seite"

    erwarte("Sprachpfad mit anderem Inhalt bleibt Umzug",
            pruefe_quelle("https://kontenvergleich.bafin.de/",
                          abruf=abruf_sprache_anderer_inhalt)["status"] == UMGELEITET)

    def abruf_fremder_host(url, timeout=10.0):
        return 200, "https://example.org/de"

    erwarte("Sprachpfad-Regel gilt nicht hostübergreifend",
            pruefe_quelle("https://kontenvergleich.bafin.de/",
                          abruf=abruf_fremder_host)["status"] == UMGELEITET)
    erwarte("http ohne s ist tot",
            pruefe_quelle("http://example.org/a", abruf=abruf_ok)["status"] == TOT)
    erwarte("leere URL ist tot", pruefe_quelle("", abruf=abruf_ok)["status"] == TOT)

    # GII-Spiegel-Normprüfung (Befund #826, 30.10.2026)
    vvg_md = (
        "---\n"
        "titel: Versicherungsvertragsgesetz\n"
        "quelle: https://www.gesetze-im-internet.de/vvg_2008/\n"
        "---\n\n"
        "### § 40 Kündigung bei Prämienerhöhung\n\n(1) Erhöht der Versicherer ...\n\n"
        "### § 41 (weggefallen)\n"
    )

    def spiegel_vvg(slug, timeout=10.0):
        """Spiegel-Abruf im neuen Vertrag: (slug, timeout) -> (status, text)."""
        if slug == "vvg_2008":
            return 200, vvg_md
        return 404, ""

    def spiegel_offline(slug, timeout=10.0):
        raise urllib.error.URLError("offline")

    erwarte("GII aktive Einzelnorm trotz Runner-Block ok",
            pruefe_quelle("https://www.gesetze-im-internet.de/vvg_2008/__40.html",
                          abruf=abruf_netz, spiegel_abruf=spiegel_vvg)["status"] == OK)
    erwarte("GII Gesamtwerk trotz Runner-Block ok",
            pruefe_quelle("https://www.gesetze-im-internet.de/vvg_2008/",
                          abruf=abruf_netz, spiegel_abruf=spiegel_vvg)["status"] == OK)
    erwarte("GII weggefallene Einzelnorm ist tot",
            pruefe_quelle("https://www.gesetze-im-internet.de/vvg_2008/__41.html",
                          abruf=abruf_netz, spiegel_abruf=spiegel_vvg)["status"] == TOT)
    erwarte("GII fehlende Einzelnorm ist tot",
            pruefe_quelle("https://www.gesetze-im-internet.de/vvg_2008/__999.html",
                          abruf=abruf_netz, spiegel_abruf=spiegel_vvg)["status"] == TOT)
    erwarte("GII aufgehobenes Gesetz (Spiegel 404) ist tot",
            pruefe_quelle("https://www.gesetze-im-internet.de/altgesetz/__1.html",
                          abruf=abruf_netz, spiegel_abruf=spiegel_vvg)["status"] == TOT)
    erwarte("GII direktes 404 wird niemals durch Spiegel überstimmt",
            pruefe_quelle("https://www.gesetze-im-internet.de/vvg_2008/__40.html",
                          abruf=abruf_404, spiegel_abruf=spiegel_vvg)["status"] == TOT)
    erwarte("GII + Spiegel offline bleibt fail-closed unklar",
            pruefe_quelle("https://www.gesetze-im-internet.de/vvg_2008/__40.html",
                          abruf=abruf_netz, spiegel_abruf=spiegel_offline)["status"] == UNKLAR)

    # ----- Fehlerklassen (04.11.2026, #1024) -------------------------------
    # Der Defekt war ein ValueError aus einem falsch entpackten Tupel, den ein
    # `except Exception:` als „unklar“ tarnte. Ein PROGRAMMIERFEHLER darf
    # niemals als Quellenbefund erscheinen – er muss durchschlagen.
    def abruf_typfehler(url, timeout=10.0):
        raise ValueError("too many values to unpack (expected 2)")

    try:
        pruefe_quelle("https://www.verbraucherzentrale.de/wissen/alt-13888",
                      abruf=abruf_typfehler)
    except ValueError:
        pass
    else:
        fehler.append("Programmierfehler wurde als Quellenbefund getarnt")

    def spiegel_typfehler(slug, timeout=10.0):
        raise AttributeError("'NoneType' object has no attribute 'decode'")

    try:
        pruefe_quelle("https://www.gesetze-im-internet.de/vvg_2008/__40.html",
                      abruf=abruf_netz, spiegel_abruf=spiegel_typfehler)
    except AttributeError:
        pass
    else:
        fehler.append("Programmierfehler im Spiegelabruf wurde getarnt")

    # ----- Netzfehlerliste ist abgeschlossen ------------------------------
    for klasse in (urllib.error.URLError, urllib.error.HTTPError,
                   TimeoutError, ConnectionResetError, ssl.SSLError):
        erwarte(f"{klasse.__name__} gehört zu NETZ_AUSNAHMEN",
                issubclass(klasse, NETZ_AUSNAHMEN))

    # ----- Ablageordnung des Spiegels (eine Stelle, ein Grund) ------------
    erwarte("vvg_2008 liegt in vv/", _gii_shard("vvg_2008") == "vv")
    erwarte("bgb liegt in bg/", _gii_shard("bgb") == "bg")
    erwarte("got_2022 liegt in go/", _gii_shard("got_2022") == "go")
    erwarte("estg liegt in es/", _gii_shard("estg") == "es")
    erwarte("Ziffernkennung liegt in 0-9", _gii_shard("1wofg") == "0-9")
    erwarte("Spiegel-URL trägt Ordner und Datei",
            _gii_spiegel_url("vvg_2008").endswith("/vv/vvg_2008.md"))
    erwarte("API-URL pinnt die Fassung",
            _gii_spiegel_api_url("bgb").endswith("/bg/bgb.md?ref=main"))
    erwarte("API-Abruf fragt rohen Inhalt an", "vnd.github.raw" in _github_kopf(roh=True)["Accept"])
    erwarte("Raw-Abruf fragt keine API-Version an",
            "X-GitHub-Api-Version" in _github_kopf(roh=False))

    # ----- Der 3-Tupel-Vertrag von sicherer_abruf (#1024) ----------------
    # Der Spiegelabruf MUSS das Tupel korrekt zerlegen. Geprüft wird gegen
    # eine Attrappe mit dem echten Rückgabevertrag, damit ein künftiger
    # Fehler in `_spiegel_abruf` hier auffällt und nicht als „unklar“ endet.
    import net_safety as _ns
    original = _ns.sicherer_abruf

    def attrappe_3_tupel(url, *, headers=None, timeout=20.0, max_bytes=0,
                         erlaube_loopback=False):
        return 200, {"content-type": "text/markdown"}, vvg_md.encode("utf-8")

    _ns.sicherer_abruf = attrappe_3_tupel
    try:
        status, inhalt = _spiegel_abruf(_gii_spiegel_url("vvg_2008"), timeout=1.0)
        erwarte("3-Tupel von sicherer_abruf wird entpackt", status == 200)
        erwarte("Inhalt kommt als Rohbytes an",
                b"quelle: https://www.gesetze-im-internet.de/vvg_2008/" in inhalt)
    finally:
        _ns.sicherer_abruf = original

    # ----- Zweistufiger Abruf: Raw vor API, 404 endgültig ----------------
    aufrufe = []

    def zweistufig_erfolg(url, timeout=10.0):
        aufrufe.append(url)
        return 200, "---\nquelle: https://www.gesetze-im-internet.de/vvg_2008/\n---\n### § 40 Test\n"

    erwarte("Raw-Abruf genügt, wenn er trägt",
            abruf_gii_spiegel("vvg_2008", abruf=zweistufig_erfolg)[0] == 200
            and len(aufrufe) == 1)
    erwarte("ERSTER Weg ist raw.githubusercontent.com",
            _normalisiert(aufrufe[0])[0] == "raw.githubusercontent.com")

    aufrufe.clear()

    def zweistufig_fallback(url, timeout=10.0):
        aufrufe.append(url)
        if _normalisiert(url)[0] == "raw.githubusercontent.com":
            raise urllib.error.HTTPError(url, 429, "rate limited", None, None)
        return 200, "---\nquelle: https://www.gesetze-im-internet.de/bgb/\n---\n"

    status, _ = abruf_gii_spiegel("bgb", abruf=zweistufig_fallback)
    erwarte("429 auf dem Raw-Weg führt zum API-Rückfall",
            status == 200 and len(aufrufe) >= 2
            and _normalisiert(aufrufe[-1])[0] == "api.github.com")
    erwarte("Rückfall adressiert dieselbe Datei",
            "/bg/bgb.md" in aufrufe[-1] and "ref=main" in aufrufe[-1])

    aufrufe.clear()

    def zweistufig_404(url, timeout=10.0):
        aufrufe.append(url)
        raise urllib.error.HTTPError(url, 404, "Not Found", None, None)

    erwarte("404 auf dem Raw-Weg ist endgültig (kein Rückfall)",
            abruf_gii_spiegel("altgesetz", abruf=zweistufig_404)[0] == 404
            and len(aufrufe) == 1)

    # ----- Retry bei transienten Antworten --------------------------------
    versuche = {"n": 0}

    def wackelig(url, timeout=10.0):
        versuche["n"] += 1
        if versuche["n"] == 1:
            raise urllib.error.HTTPError(url, 503, "Service Unavailable", None, None)
        return 200, "---\nquelle: https://www.gesetze-im-internet.de/vvg_2008/\n---\n"

    status, _ = abruf_gii_spiegel_http(_gii_spiegel_url("vvg_2008"), 1.0,
                                      abruf=wackelig, versuche=2)
    erwarte("ein 503 wird einmal wiederholt", status == 200 and versuche["n"] == 2)
    return fehler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nur-hochrisiko", action="store_true",
                        help="nur Risikoklasse hoch (YMYL)")
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1, wenn eine Quelle definitiv nicht mehr abrufbar ist")
    parser.add_argument("--require-complete", action="store_true",
                        help="Exit 1 auch bei unklaren oder umgeleiteten Quellen; "
                             "für automatische Queue-Erledigung")
    parser.add_argument("--json", action="store_true", help="Ergebnis als JSON")
    parser.add_argument("--report", action="store_true",
                        help="BELEGKETTEN-WACHE-REPORT.md schreiben")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--probe-bundesrecht", action="store_true",
                        help="Live-Nachweis des Messwegs für die Bundesrechts-Zitate")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)

    if args.probe_bundesrecht:
        return probe_bundesrecht(timeout=max(args.timeout, 15.0))

    if args.selftest:
        fehler = selftest()
        if fehler:
            print("🛑 Belegketten-Wache: Selbsttest fehlgeschlagen")
            for eintrag in fehler:
                print("  -", eintrag)
            return 2
        print("✅ Belegketten-Wache: Selbsttest bestanden (ok, umgeleitet, tot, unklar).")
        return 0

    ergebnis = pruefe_alle(nur_hochrisiko=args.nur_hochrisiko, timeout=args.timeout)
    if args.report:
        report_schreiben(ergebnis)
    if args.json:
        print(json.dumps(ergebnis, ensure_ascii=False, indent=2))
    else:
        z = ergebnis["zaehler"]
        print(f"Belegketten-Wache: {ergebnis['geprueft']} Quellen · "
              f"{z[OK]} ok · {z[UMGELEITET]} umgeleitet · "
              f"{z[TOT]} tot · {z[UNKLAR]} unklar")
        for eintrag in ergebnis["befunde"]:
            print(_zeile(eintrag))
    return 1 if ((args.strict and ergebnis["blockierend"])
                 or (args.require_complete and ergebnis["befunde"])) else 0


if __name__ == "__main__":
    raise SystemExit(main())
