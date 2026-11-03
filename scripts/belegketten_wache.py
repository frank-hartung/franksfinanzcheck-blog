#!/usr/bin/env python3
"""Belegketten-Wache: Prüft, ob die zitierten Quellen noch die zitierten sind.

WARUM DIESE WACHE (Prüfqueue #826, 24.10.2026 · gehärtet 03.11.2026, #1024)
---------------------------------------------------------------------------
Zwei reale Fälle aus der redaktionellen Prüfung dieses Tages:

* Die Verbraucherzentrale hat ihre Seiten umgezogen. Drei der sechs in
  Hochrisiko-Artikeln zitierten URLs antworteten mit **404** – darunter die
  Unfallversicherungs-Seite, auf der fast das ganze Prüfprotokoll eines
  Artikels aufbaute.
* Die zitierte GDV-Seite existierte weiter, zeigte aber unter derselben
  Adresse einen **anderen Artikel mit anderen Zahlen** (Regionalklassen 2027
  statt der zitierten 2026er-Werte). Die Belegkette war damit nicht „tot“,
  sondern schlimmer: sie widersprach dem Text, den sie belegen sollte.

HÄRTUNG #1024 (03.11.2026):
* ``abruf_gii_spiegel_http()`` entpackt das vollständige 3-Tupel
  ``(status, kopf, nutzlast)`` aus ``net_safety.sicherer_abruf()`` und hält
  zusätzlich ``api.github.com/repos/Gesetze-fuer-KI/bundesrecht/contents/...``
  (``Accept: application/vnd.github.raw``) als authentifizierbare Zweitquelle
  bereit, falls ``raw.githubusercontent.com`` gedrosselt oder blockiert ist.
* Programmierfehler (``ValueError``, ``TypeError``, ``AttributeError``) werden
  in ``pruefe_quelle()`` und ``_pruefe_gii_spiegel()`` NICHT mehr als
  scheinbarer Netzfehler (``unklar``) geschluckt, sondern schlagen laut fehl.
* Transiente Abrufstörungen (Timeout, ``429``, ``5xx``) erhalten eine
  einmalige Wiederholung mit kurzem Backoff.

Was diese Wache tut: Sie liest die Belegketten (``quellen``) des Bestands,
ruft jede URL ab und meldet vier Zustände:

======  ===================================================================
ok      HTTP 200 unter genau der zitierten Adresse (bzw. bestätigte Norm)
umgeleitet  HTTP 200, aber unter anderer Adresse – Inhalt kann abweichen
tot     HTTP 4xx (außer 403/408/429) – die Belegkette trägt nichts mehr
unklar  Netzfehler (Timeout, DNS, 5xx, 403, 408, 429) – nicht prüfbar
======  ===================================================================

AUFRUF
------
  python3 scripts/belegketten_wache.py                       # Bestand
  python3 scripts/belegketten_wache.py --nur-hochrisiko      # YMYL
  python3 scripts/belegketten_wache.py --nur-hochrisiko --strict --report
  python3 scripts/belegketten_wache.py --json
  python3 scripts/belegketten_wache.py --selftest            # offline
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import http.client
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import editorial_review_gate as gate  # noqa: E402  (eine Regelquelle)
from net_safety import UnsicheresZielFehler  # noqa: E402
from url_host import ist_host_oder_subdomain  # noqa: E402  (Host-Wahrheit)

REPORT = ROOT / "BELEGKETTEN-WACHE-REPORT.md"
USER_AGENT = "FranksFinanzcheck-Belegketten-Wache/1.0 (+https://franksfinanzcheck.de)"
TOT = "tot"
UMGELEITET = "umgeleitet"
UNKLAR = "unklar"
OK = "ok"

_GII_BASIS_HOST = "gesetze-im-internet.de"
_GII_SPIEGEL_BASIS = "https://raw.githubusercontent.com/Gesetze-fuer-KI/bundesrecht/main"
_GII_GITHUB_API_BASIS = "https://api.github.com/repos/Gesetze-fuer-KI/bundesrecht/contents"
_GII_MAX_BYTES = 8 * 1024 * 1024
_GII_SLUG_ZEICHEN = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_-")
_GII_NORM_ZEICHEN = frozenset("abcdefghijklmnopqrstuvwxyz0123456789")

TRANSIENTE_HTTP_CODES = frozenset({408, 429, 500, 502, 503, 504})
UNKLARE_HTTP_CODES = frozenset({403, 408, 429})
MAX_RETRY_WARTEZEIT = 15.0

# Ausschließlich echte Transport-/Zielausnahmen – NIEMALS ValueError/TypeError!
# Ein kaputtes Tupel-Unpacking (#1024) muss sofort krachen statt als „URLError"
# in der YMYL-Prüfqueue zu landen.
NETZ_AUSNAHMEN = (
    urllib.error.URLError,
    TimeoutError,
    OSError,
    http.client.HTTPException,
    UnsicheresZielFehler,
)


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
    """Weiterleitung, die nur den Sprachpfad der GLEICHEN Seite ergänzt."""
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


def _retry_pause(exc: BaseException | None, versuch: int, basis_pause: float) -> float:
    standard = min(MAX_RETRY_WARTEZEIT, basis_pause * (2 ** (versuch - 1)))
    if isinstance(exc, urllib.error.HTTPError) and exc.headers is not None:
        roh = str(exc.headers.get("Retry-After") or "").strip()
        if roh.isdigit():
            return min(MAX_RETRY_WARTEZEIT, max(standard, float(int(roh))))
    return standard


def abruf_http(
    url: str,
    timeout: float = 10.0,
    *,
    versuche: int = 2,
    basis_pause: float = 1.5,
    schlaf: Callable[[float], None] = time.sleep,
) -> tuple[int, str]:
    """GET mit sicherer Weiterleitungsverfolgung und einmaligem Transienten-Retry."""
    from net_safety import sicherer_abruf_status

    # gesetze-im-internet.de blockt Runner-IPs auf TCP-Ebene; dort sofort in
    # den Spiegel-Fallback wechseln statt Zeit mit Doppel-Timeouts zu verlieren.
    anzahl_versuche = 1 if ist_host_oder_subdomain(url, _GII_BASIS_HOST) else max(1, versuche)
    for versuch in range(1, anzahl_versuche + 1):
        try:
            status, end_url = sicherer_abruf_status(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=timeout,
                erlaube_loopback=False,
            )
            if status in TRANSIENTE_HTTP_CODES and versuch < anzahl_versuche:
                schlaf(_retry_pause(None, versuch, basis_pause))
                continue
            return status, end_url
        except urllib.error.HTTPError as exc:
            with contextlib.suppress(Exception):
                exc.close()
            if int(exc.code) in TRANSIENTE_HTTP_CODES and versuch < anzahl_versuche:
                schlaf(_retry_pause(exc, versuch, basis_pause))
                continue
            raise
        except UnsicheresZielFehler:
            raise
        except NETZ_AUSNAHMEN as exc:
            if versuch < anzahl_versuche:
                schlaf(_retry_pause(exc, versuch, basis_pause))
                continue
            raise
    raise RuntimeError("unerreichbar")


def _github_spiegel_kandidaten(url: str) -> list[tuple[str, dict[str, str]]]:
    """Primär raw.githubusercontent.com, sekundär api.github.com (raw media type)."""
    basis_kopf = {"User-Agent": USER_AGENT}
    kandidaten: list[tuple[str, dict[str, str]]] = [(url, basis_kopf)]
    praefix = _GII_SPIEGEL_BASIS + "/"
    if url.startswith(praefix):
        rel_pfad = url[len(praefix):].lstrip("/")
        if rel_pfad:
            api_kopf = {
                "User-Agent": USER_AGENT,
                "Accept": "application/vnd.github.raw",
                "X-GitHub-Api-Version": "2022-11-28",
            }
            token = (os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or "").strip()
            if token:
                api_kopf["Authorization"] = f"Bearer {token}"
            kandidaten.append((f"{_GII_GITHUB_API_BASIS}/{rel_pfad}?ref=main", api_kopf))
    return kandidaten


def abruf_gii_spiegel_http(url: str, timeout: float = 10.0) -> tuple[int, str]:
    """Lädt den täglich synchronisierten GII-Bundesrecht-Spiegel über net_safety."""
    from net_safety import sicherer_abruf

    letzter_fehler: BaseException | None = None
    letzter_status = 503
    for kandidat_url, kopf in _github_spiegel_kandidaten(url):
        try:
            status, _antwort_kopf, nutzlast = sicherer_abruf(
                kandidat_url,
                headers=kopf,
                timeout=timeout,
                max_bytes=_GII_MAX_BYTES,
                erlaube_loopback=False,
            )
        except urllib.error.HTTPError as exc:
            with contextlib.suppress(Exception):
                exc.close()
            code = int(exc.code)
            if code in (404, 410):
                return code, ""
            letzter_status = code
            letzter_fehler = None
            continue
        except ValueError as exc:
            if "Groessenlimit" in str(exc):
                letzter_fehler = urllib.error.URLError(str(exc))
                continue
            raise
        except NETZ_AUSNAHMEN as exc:
            letzter_fehler = exc
            continue

        code = int(status)
        if 200 <= code < 300:
            return code, nutzlast.decode("utf-8", errors="replace")
        if code in (404, 410):
            return code, ""
        letzter_status = code
        letzter_fehler = None

    if letzter_fehler is not None:
        raise letzter_fehler
    return letzter_status, ""


def _parse_gii_ziel(zitat: str) -> tuple[str, tuple[str, str] | None] | None:
    """Zerlegt offizielle gesetze-im-internet.de-URLs in (Gesetzes-Slug, Einzelnorm)."""
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
    """Fail-closed Normprüfung über den täglichen GII-Spiegel bei Runner-Blockade."""
    zerlegt = _parse_gii_ziel(zitat)
    if zerlegt is None:
        return basis
    slug, einzelnorm = zerlegt
    spiegel_url = _gii_spiegel_url(slug)
    try:
        status, inhalt = spiegel_abruf(spiegel_url, timeout=timeout)
    except NETZ_AUSNAHMEN:
        # Ausschließlich echte Transportausfälle bleiben unklar; Programmierfehler
        # (wie das Tupel-Unpacking aus #1024) dürfen niemals geschluckt werden.
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
    nutze_spiegel = spiegel_abruf if spiegel_abruf is not None else (
        abruf_gii_spiegel_http if (abruf is None or ist_host_oder_subdomain(str(url or ""), _GII_BASIS_HOST)) else None
    )
    if abruf is not None and spiegel_abruf is None and not getattr(abruf, "_erlaube_live_spiegel", False):
        # Wenn ein Test `abruf` injiziert, darf `pruefe_quelle` nicht heimlich
        # ins echte Netz greifen (Offline-Vertrag). Für echte Läufe (`abruf is None`)
        # ist `abruf_gii_spiegel_http` immer aktiv.
        nutze_spiegel = None
    eff_abruf = abruf or abruf_http
    zitat = str(url or "").strip()
    if not zitat.startswith("https://"):
        return {"status": TOT, "zitat": zitat, "end_url": "",
                "befund": "keine HTTPS-Quelle – als Beleg unzulässig"}
    eff_timeout = timeout if direkt_timeout is None else direkt_timeout
    basis_unklar: dict | None = None
    try:
        status, end_url = eff_abruf(zitat, timeout=eff_timeout)
    except urllib.error.HTTPError as exc:
        with contextlib.suppress(Exception):
            exc.close()
        if int(exc.code) in UNKLARE_HTTP_CODES or int(exc.code) >= 500:
            basis_unklar = {
                "status": UNKLAR, "zitat": zitat, "end_url": "",
                "befund": f"HTTP {exc.code} – nicht belastbar prüfbar",
            }
        else:
            return {"status": TOT, "zitat": zitat, "end_url": "",
                    "befund": f"HTTP {exc.code} – Beleg nicht mehr abrufbar"}
    except NETZ_AUSNAHMEN as exc:
        basis_unklar = {
            "status": UNKLAR, "zitat": zitat, "end_url": "",
            "befund": f"nicht erreichbar ({type(exc).__name__})",
        }
    if basis_unklar is None and (status in UNKLARE_HTTP_CODES or status >= 500):
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
        except Exception:  # noqa: BLE001 – unlesbare Datei eigenständig melden
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


class _OfflineAntwort:
    """Minimale HTTPResponse-Attrappe für die Offline-Prüfung von sicherer_abruf."""

    def __init__(self, status: int, body: bytes, url: str) -> None:
        self.status = status
        self._body = body
        self._url = url
        self.headers = {"Content-Type": "text/markdown; charset=utf-8"}

    def read(self, amt: int | None = None) -> bytes:
        return self._body if amt is None else self._body[:amt]

    def geturl(self) -> str:
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def selftest() -> list[str]:
    """Offline: die vier Zustände, Weiterleitungslogik und echter 3-Tupel-Spiegelpfad."""
    from unittest.mock import patch as _patch

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

    # GII-Spiegel-Normprüfung (Befund #826, 30.10.2026 + #1024, 03.11.2026)
    vvg_md = (
        "---\n"
        "titel: Versicherungsvertragsgesetz\n"
        "quelle: https://www.gesetze-im-internet.de/vvg_2008/\n"
        "---\n\n"
        "##### § 40 Kündigung bei Prämienerhöhung\n\n(1) Erhöht der Versicherer ...\n\n"
        "##### § 96 Kündigung nach Veräußerung\n\n(1) Wird die versicherte Sache ...\n\n"
        "##### § 41 (weggefallen)\n"
    )

    def spiegel_vvg(url, timeout=10.0):
        if url.endswith("/vv/vvg_2008.md"):
            return 200, vvg_md
        return 404, ""

    def spiegel_offline(url, timeout=10.0):
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

    # #1024-Regressionsbeweis 1: Echter Produktionspfad `abruf_gii_spiegel_http`
    # gegen `net_safety.sicherer_abruf` (3-Tupel status, kopf, nutzlast) + Fallback
    # von raw.githubusercontent.com auf api.github.com.
    def fake_urlopen(req, timeout=10.0):
        ziel_url = req.full_url
        if "gesetze-im-internet.de" in ziel_url:
            raise urllib.error.URLError("GII TCP blockiert")
        if "raw.githubusercontent.com" in ziel_url:
            raise urllib.error.URLError("CDN gedrosselt")
        if "api.github.com/repos/Gesetze-fuer-KI/bundesrecht/contents/vv/vvg_2008.md" in ziel_url:
            return _OfflineAntwort(200, vvg_md.encode("utf-8"), ziel_url)
        raise urllib.error.HTTPError(ziel_url, 404, "Not Found", None, None)

    with _patch("urllib.request.urlopen", side_effect=fake_urlopen):
        echt_erg = pruefe_quelle("https://www.gesetze-im-internet.de/vvg_2008/__40.html")
    erwarte("#1024: abruf_gii_spiegel_http entpackt 3-Tupel + api.github.com-Fallback",
            echt_erg["status"] == OK)

    # #1024-Regressionsbeweis 2: Ein ValueError im Code (z. B. kaputtes Unpacking)
    # darf NIEMALS als scheinbarer Netzfehler (UNKLAR) geschluckt werden.
    def kaputter_spiegel(url, timeout=10.0):
        raise ValueError("too many values to unpack (expected 2)")

    code_bug_gefangen = False
    try:
        pruefe_quelle("https://www.gesetze-im-internet.de/vvg_2008/__40.html",
                      abruf=abruf_netz, spiegel_abruf=kaputter_spiegel)
    except ValueError:
        code_bug_gefangen = True
    erwarte("#1024: Programmierfehler (ValueError) schlägt laut fehl statt UNKLAR",
            code_bug_gefangen)

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
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)

    if args.selftest:
        fehler = selftest()
        if fehler:
            print("🛑 Belegketten-Wache: Selbsttest fehlgeschlagen")
            for eintrag in fehler:
                print("  -", eintrag)
            return 2
        print("✅ Belegketten-Wache: Selbsttest bestanden (ok, umgeleitet, tot, unklar, 3-Tupel-Spiegel).")
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
