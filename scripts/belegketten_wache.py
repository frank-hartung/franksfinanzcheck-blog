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
import datetime as dt
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import editorial_review_gate as gate  # noqa: E402  (eine Regelquelle)

REPORT = ROOT / "BELEGKETTEN-WACHE-REPORT.md"
USER_AGENT = "FranksFinanzcheck-Belegketten-Wache/1.0 (+https://franksfinanzcheck.de)"
TOT = "tot"
UMGELEITET = "umgeleitet"
UNKLAR = "unklar"
OK = "ok"


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


def pruefe_quelle(url: str, *, abruf=None, timeout: float = 10.0) -> dict:
    """Ein Zitat prüfen. ``abruf`` ist injizierbar (Selbsttest, Tests)."""
    abruf = abruf or abruf_http
    zitat = str(url or "").strip()
    if not zitat.startswith("https://"):
        return {"status": TOT, "zitat": zitat, "end_url": "",
                "befund": "keine HTTPS-Quelle – als Beleg unzulässig"}
    try:
        status, end_url = abruf(zitat, timeout=timeout)
    except urllib.error.HTTPError as exc:
        if int(exc.code) in (403, 429) or int(exc.code) >= 500:
            return {"status": UNKLAR, "zitat": zitat, "end_url": "",
                    "befund": f"HTTP {exc.code} – nicht belastbar prüfbar"}
        return {"status": TOT, "zitat": zitat, "end_url": "",
                "befund": f"HTTP {exc.code} – Beleg nicht mehr abrufbar"}
    except Exception as exc:  # noqa: BLE001 – Netzfehler sind kein Befund
        return {"status": UNKLAR, "zitat": zitat, "end_url": "",
                "befund": f"nicht erreichbar ({type(exc).__name__})"}
    if status in (403, 429) or status >= 500:
        return {"status": UNKLAR, "zitat": zitat, "end_url": end_url,
                "befund": f"HTTP {status} – nicht belastbar prüfbar"}
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
                timeout: float = 10.0) -> dict:
    ergebnisse = []
    cache = {}
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
                cache[url] = pruefe_quelle(url, abruf=abruf, timeout=timeout)
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
