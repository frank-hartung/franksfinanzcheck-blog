#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
#  CWV-FELD-WACHE – die Zahlen, die echte Besucher erleben
#  ------------------------------------------------------------
#  WARUM ES DIESE WACHE GIBT (26.10.2026)
#
#  Das Haus misst Core Web Vitals bisher nur im Labor:
#    · `scripts/cwv_guard.py`         – statischer Build (Bytes, Bilder, JS)
#    · `lighthouse/assertions.json`   – Varianten-Builds auf einem CI-Runner
#  Beides ist wertvoll und beides ist NICHT die Wirklichkeit. Ein
#  LCP von 1,4 s auf einem unbelasteten Runner sagt nichts über einen
#  Haushalt, der mit 4G im Zug einen Stromvergleich liest. Google
#  veröffentlicht genau diese Wirklichkeit als CrUX-Felddaten (Chrome
#  User Experience Report) über die PageSpeed-Insights-API.
#
#  DIESE WACHE LIEST NUR – SIE RECHNET NICHTS SCHÖN
#  1. Felddaten kommen aus der API, nicht aus einer eigenen Formel.
#     Die Bewertung (gut / verbesserungswürdig / schlecht) liefert die
#     API selbst pro Metrik (`category`). Damit gibt es keine zweite,
#     erfundene Schwelle im Repo: 2,5 s / 200 ms / 0,1 sind Googles
#     Definition, nicht unsere.
#  2. Keine Felddaten heißt UNGEPRÜFT – niemals GRÜN. Eine neue Seite
#     mit zu wenig Traffic hat keine CrUX-Daten; sie als „gut" zu
#     führen wäre eine Lüge mit grünem Häkchen.
#  3. Ein Netzfehler ist STÖRUNG (Exit 2), kein Befund. Ungeprüft ist
#     nicht sauber (gleiche Regel wie `abhaengigkeits_wache.py --audit`).
#
#  WAS SIE NICHT IST
#  Kein Ersatz für `design-varianten.yml` (Labor-Gate vor dem Deploy)
#  und kein Ersatz für den Menschen: Felddaten hinken bis zu 28 Tage
#  hinterher. Sie sind der Blick von außen, nicht der Freibrief.
#
#  AUFRUF
#    python3 scripts/cwv_feld_wache.py                 # messen, Bericht auf stdout
#    python3 scripts/cwv_feld_wache.py --schreiben     # + data/cwv/feld/*
#    python3 scripts/cwv_feld_wache.py --json          # Maschinenausgabe
#    python3 scripts/cwv_feld_wache.py --ziel /cockpit/ --ziel /werkzeuge/
#    python3 scripts/cwv_feld_wache.py --strategie desktop
#    python3 scripts/cwv_feld_wache.py --fixture antwort.json --datum 2026-10-26
#    python3 scripts/cwv_feld_wache.py --selftest      # ohne Netz, ohne Schreiben
#
#  Exit: 0 = kein Feldbefund (auch: keine Daten) · 1 = Befund (POOR)
#        2 = Störung (Netz, API, kein Ziel messbar)
#
#  DREI HÄRTUNGEN AUS DEM WOCHENLAUF 41456548199 (04.11.2026, #1026)
#  ---------------------------------------------------------------
#  1. GEHEIMNIS-SCHWÄRZUNG. Der PSI-Schlüssel steht als `&key=…` in der
#     Anfrage-URL und damit potenziell in jeder Fehlermeldung, die eine
#     URL nennt. `schwaerze()` entfernt ihn aus JEDEM Text, der das Haus
#     verlässt (Bericht, JSON, stderr) – auch aus fremden Ausnahmetexten,
#     deren Form wir nicht kontrollieren.
#  2. TRANSIENTEN-RETRY. 408/425/429 und 5xx sind Aussagen über den
#     Messweg, nicht über die Seite. Sie werden begrenzt wiederholt, ein
#     `Retry-After` (bis 30 s) respektiert. Erst danach ist es eine
#     STÖRUNG – und die bleibt STÖRUNG, nie ein grünes Häkchen (Hausregel C2).
#  3. FEHLSCHLÄGE WERDEN BENANNT, NICHT VERSCHLUCKT. Jede Störung trägt
#     Pfad, Klasse und geschwärzten Grund; eine leere Störungsliste ist
#     eine Aussage, kein Zufall.
#
#  API-Schlüssel: `PSI_API_KEY` (optional). Ohne Schlüssel antwortet
#  die API stark gedrosselt; der Lauf bleibt möglich. Der Schlüssel
#  wird NIE ausgegeben, geloggt oder in eine Datei geschrieben.
# ============================================================

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ZIELE_DATEI = ROOT / "data" / "cwv" / "feld_ziele.json"
BEFUND_JSON = ROOT / "data" / "cwv" / "feld" / "befund.json"
BEFUND_MD = ROOT / "data" / "cwv" / "feld" / "befund.md"
VERLAUF = ROOT / "data" / "cwv" / "feld" / "verlauf.jsonl"

API = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

# Transiente Antworten: Aussage über den Messweg, nicht über die Seite.
TRANSIENT_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})
VERSUCHE = 3
PAUSE_SEKUNDEN = 2.0
RETRY_AFTER_MAX = 30.0

# Google-Referenz (Web Vitals, Stand der API-Antwort): Die Bewertung
# kommt als `category` je Metrik zurück – FAST / AVERAGE / SLOW. Diese
# Abbildung ist der einzige Ort, an dem aus der API-Sprache unsere wird.
FELD_URTEIL = {"FAST": "GUT", "AVERAGE": "VERBESSERUNGSWUERDIG", "SLOW": "SCHLECHT"}

# Die drei Kernmetriken (CLS kommt als skaliertes Integer-Feld).
KERN_METRIKEN = (
    ("LARGEST_CONTENTFUL_PAINT_MS", "LCP", "ms"),
    ("INTERACTION_TO_NEXT_PAINT", "INP", "ms"),
    ("CUMULATIVE_LAYOUT_SHIFT_SCORE", "CLS", ""),
)

# Rangfolge für das Gesamturteil je Seite.
RANG = {"GUT": 0, "VERBESSERUNGSWUERDIG": 1, "SCHLECHT": 2, "UNGEPRUEFT": 3}


# --------------------------------------------------------------------------
#  Ziele
# --------------------------------------------------------------------------

def lade_ziele(pfad: Path | None = None) -> list[dict]:
    """Liest die kuratierte Zielliste (Pfad + Anzeigename)."""
    datei = pfad or ZIELE_DATEI
    daten = json.loads(datei.read_text(encoding="utf-8"))
    ziele = daten.get("ziele") or []
    if not isinstance(ziele, list) or not ziele:
        raise ValueError(f"{datei}: `ziele` fehlt oder ist keine Liste")
    for z in ziele:
        if not str(z.get("pfad") or "").startswith("/"):
            raise ValueError(f"{datei}: Ziel ohne absoluten Pfad: {z!r}")
    return ziele


def baue_url(basis: str, pfad: str) -> str:
    """Basis + Pfad → absolute URL, ohne doppelte Schrägstriche."""
    return basis.rstrip("/") + "/" + pfad.lstrip("/")


def psi_url(ziel: str, strategie: str) -> str:
    """PageSpeed-Insights-Abfrage für EINE URL."""
    params = {
        "url": ziel,
        "strategy": strategie,
        "category": ["performance", "accessibility", "best-practices", "seo"],
    }
    return API + "?" + urllib.parse.urlencode(params, doseq=True)


# --------------------------------------------------------------------------
#  Bewertung (rein, ohne Netz – damit prüfbar)
# --------------------------------------------------------------------------

def feld_metriken(antwort: dict) -> dict:
    """Felddaten (CrUX) aus einer PSI-Antwort – Seite vor Origin."""
    for schluessel in ("loadingExperience", "originLoadingExperience"):
        block = antwort.get(schluessel) or {}
        metriken = block.get("metrics") or {}
        if metriken:
            return metriken
    return {}


def bewerte_metrik(roh: dict) -> dict:
    """Eine CrUX-Metrik → (Wert, Einheit, Urteil). Unbekannt = UNGEPRUEFT."""
    kategorie = str((roh or {}).get("category") or "").upper()
    return {
        "urteil": FELD_URTEIL.get(kategorie, "UNGEPRUEFT"),
        "percentile": (roh or {}).get("percentile"),
        "kategorie_roh": kategorie or None,
    }


def bewerte_seite(antwort: dict) -> dict:
    """Eine PSI-Antwort → Befund für eine Seite.

    Das Gesamturteil ist das SCHLECHTESTE Einzelurteil: Eine Seite, die
    beim INP „schlecht" ist, ist nicht „gut", nur weil der LCP passt.
    Ohne Felddaten bleibt sie UNGEPRUEFT – nie GUT.
    """
    metriken = feld_metriken(antwort)
    befund: dict[str, dict] = {}
    for roh_name, kurz, einheit in KERN_METRIKEN:
        if roh_name in metriken:
            eintrag = bewerte_metrik(metriken[roh_name])
            eintrag["einheit"] = einheit
            befund[kurz] = eintrag
    if not befund:
        gesamt = "UNGEPRUEFT"
    else:
        gesamt = max((e["urteil"] for e in befund.values()), key=lambda u: RANG.get(u, 3))
    labor = (antwort.get("lighthouseResult") or {}).get("categories") or {}
    labor_scores = {
        name: round((labor.get(name) or {}).get("score", 0) * 100)
        for name in ("performance", "accessibility", "best-practices", "seo")
        if name in labor
    }
    return {
        "urteil": gesamt,
        "feld": befund,
        "feld_quelle": "loadingExperience" if (antwort.get("loadingExperience") or {}).get("metrics")
        else ("originLoadingExperience" if metriken else None),
        "labor_scores": labor_scores,
        "abrufzeit": (antwort.get("analysisUTCTimestamp") or "")[:19] or None,
    }


def gesamturteil(seiten: list[dict]) -> tuple[str, int]:
    """Gesamturteil + Anzahl geprüfter Seiten (ohne Felddaten)."""
    geprueft = [s for s in seiten if s["urteil"] != "UNGEPRUEFT"]
    if not seiten:
        return "STOERUNG", 0
    if not geprueft:
        # Keine einzige Seite mit Felddaten: Das ist keine Gesundmeldung,
        # die Messung selbst steht infrage (falsche Domain, API-Wechsel).
        return "STOERUNG", 0
    schlechtestes = max((s["urteil"] for s in geprueft), key=lambda u: RANG.get(u, 3))
    return schlechtestes, len(geprueft)


# --------------------------------------------------------------------------
#  Geheimnis-Schwärzung (eine Stelle – jeder Ausgabeweg geht hier durch)
# --------------------------------------------------------------------------
_SCHLUESSEL_MUSTER = re.compile(r"([?&](?:key|api_key|apikey)=)[^&\s'\"<>]+", re.I)


def schwaerze(text: object) -> str:
    """Entfernt API-Schlüssel aus beliebigem Text.

    Der Schlüssel reist als Query-Parameter (`…&key=AIza…`). Er darf weder
    im Bericht noch im JSON noch in einer Fehlerzeile auftauchen – und weil
    fremde Ausnahmetexte URLs mitschleppen können, wird jeder Text durch
    diese eine Funktion geführt, nicht nur die, die wir selbst schreiben.
    """
    return _SCHLUESSEL_MUSTER.sub(r"\1***", str(text))


# --------------------------------------------------------------------------
#  Netz
# --------------------------------------------------------------------------

def _wartezeit(antwort_kopf, versuch: int) -> float:
    """Wartezeit vor dem nächsten Versuch: `Retry-After`, sonst Backoff."""
    roh = ""
    try:
        roh = (antwort_kopf or {}).get("Retry-After", "") or ""
    except AttributeError:
        roh = ""
    try:
        return min(max(float(str(roh).strip()), 0.0), RETRY_AFTER_MAX)
    except (TypeError, ValueError):
        return PAUSE_SEKUNDEN * (2 ** versuch)


def hole(url: str, zeitlimit: int = 60, *, versuche: int = VERSUCHE,
         pause=time.sleep) -> dict:
    """Eine PSI-Antwort. Netz-/HTTP-Fehler sind Störung, kein Befund.

    Transiente Antworten (408/425/429/5xx) werden begrenzt wiederholt; ein
    `Retry-After` bis 30 s wird respektiert. Nach dem letzten Versuch wird
    die Ausnahme ERHOBEN – der Aufrufer macht daraus eine Störung. Die
    Meldung ist geschwärzt, damit der Schlüssel nicht im Log landet.
    """
    request = urllib.request.Request(
        url, headers={"User-Agent": "franksfinanzcheck-cwv-feld/1.0"})
    gesamt = max(1, versuche)
    letzter_fehler: Exception | None = None
    for versuch in range(gesamt):
        try:
            with urllib.request.urlopen(request, timeout=zeitlimit) as antwort:  # noqa: S310 – feste API
                return json.loads(antwort.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            letzter_fehler = exc
            if int(exc.code) not in TRANSIENT_STATUS or versuch + 1 >= gesamt:
                raise
            pause(_wartezeit(getattr(exc, "headers", None), versuch))
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            letzter_fehler = exc
            if versuch + 1 >= gesamt:
                raise
            pause(PAUSE_SEKUNDEN * (2 ** versuch))
    raise letzter_fehler if letzter_fehler else RuntimeError("Abruf ohne Ergebnis")


def api_schluessel() -> str | None:
    """Optionaler Schlüssel aus der Umgebung – wird nie ausgegeben."""
    wert = (os.environ.get("PSI_API_KEY") or "").strip()
    return wert or None


# --------------------------------------------------------------------------
#  Bericht
# --------------------------------------------------------------------------

def bericht(punkte: list[dict], strategie: str, datum: str, urteil: str) -> str:
    zeilen = [
        "# Core Web Vitals – Felddaten",
        "",
        f"**Stand:** {datum} · **Strategie:** {strategie} · **Gesamturteil:** {urteil}",
        "",
        "> Quelle: Chrome UX Report über PageSpeed Insights. Die Bewertung je",
        "> Metrik stammt von der API (`category`), nicht aus einer eigenen",
        "> Schwelle. Keine Felddaten = UNGEPRÜFT, nie GRÜN.",
        "",
        "| Seite | Urteil | LCP | INP | CLS | Labor (P / A11y / BP / SEO) |",
        "|---|---|---|---|---|---|",
    ]
    for p in punkte:
        def zelle(k, _p=p):
            e = (_p.get("feld") or {}).get(k)
            if not e:
                return "–"
            wert = e.get("percentile")
            if k == "CLS" and wert is not None:
                wert = f"{wert / 100:.2f}"
            # CLS hat keine Einheit – kein doppeltes Leerzeichen im Bericht.
            teile = [str(wert)] + ([e["einheit"]] if e.get("einheit") else [])
            return f"{' '.join(teile)} ({e['urteil'][:4]})".strip()

        labor = p.get("labor_scores") or {}
        labor_txt = " / ".join(str(labor.get(k, "–")) for k in
                               ("performance", "accessibility", "best-practices", "seo"))
        zeilen.append(
            f"| `{p['pfad']}` | {p['urteil']} | {zelle('LCP')} | {zelle('INP')} | {zelle('CLS')} | {labor_txt} |"
        )
    offen = [p["pfad"] for p in punkte if p["urteil"] == "UNGEPRUEFT"]
    if offen:
        zeilen += ["", "**Ohne Felddaten (UNGEPRÜFT):** " + ", ".join(f"`{p}`" for p in offen),
                   "", "Zu wenig Traffic im 28-Tage-Fenster (CrUX) – nicht als grün gewertet."]
    schlecht = [p["pfad"] for p in punkte if p["urteil"] == "SCHLECHT"]
    if schlecht:
        zeilen += ["", "**Befund (schlecht):** " + ", ".join(f"`{p}`" for p in schlecht)]
    return "\n".join(zeilen) + "\n"


def schreibe(punkte: list[dict], strategie: str, datum: str, urteil: str) -> None:
    for ziel in (BEFUND_JSON, BEFUND_MD, VERLAUF):
        ziel.parent.mkdir(parents=True, exist_ok=True)
    BEFUND_JSON.write_text(
        json.dumps({"datum": datum, "strategie": strategie, "urteil": urteil,
                    "seiten": punkte}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    BEFUND_MD.write_text(bericht(punkte, strategie, datum, urteil), encoding="utf-8")
    with VERLAUF.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"datum": datum, "strategie": strategie, "urteil": urteil,
                            "seiten": {p["pfad"]: p["urteil"] for p in punkte}},
                           ensure_ascii=False, sort_keys=True) + "\n")


# --------------------------------------------------------------------------
#  Selbsttest (ohne Netz, ohne Schreiben)
# --------------------------------------------------------------------------

def _fixture_antwort(lcp: str, inp: str, cls: str) -> dict:
    return {
        "loadingExperience": {
            "metrics": {
                "LARGEST_CONTENTFUL_PAINT_MS": {"category": lcp, "percentile": 2100},
                "INTERACTION_TO_NEXT_PAINT": {"category": inp, "percentile": 180},
                "CUMULATIVE_LAYOUT_SHIFT_SCORE": {"category": cls, "percentile": 5},
            }
        },
        "lighthouseResult": {"categories": {
            "performance": {"score": 0.93}, "accessibility": {"score": 1.0},
            "best-practices": {"score": 1.0}, "seo": {"score": 1.0}}},
        "analysisUTCTimestamp": "2026-10-26T05:00:00.000Z",
    }


def selftest() -> int:
    fehler: list[str] = []

    def muss(bedingung: bool, text: str) -> None:
        if not bedingung:
            fehler.append(text)

    # 1. Abbildung der API-Sprache
    muss(bewerte_metrik({"category": "FAST"})["urteil"] == "GUT", "FAST muss GUT sein")
    muss(bewerte_metrik({"category": "SLOW"})["urteil"] == "SCHLECHT", "SLOW muss SCHLECHT sein")
    muss(bewerte_metrik({})["urteil"] == "UNGEPRUEFT", "ohne Kategorie muss UNGEPRUEFT stehen")

    # 2. Das schlechteste Einzelurteil gewinnt
    gut = bewerte_seite(_fixture_antwort("FAST", "FAST", "FAST"))
    muss(gut["urteil"] == "GUT", f"alles FAST muss GUT sein, war {gut['urteil']}")
    gemischt = bewerte_seite(_fixture_antwort("FAST", "AVERAGE", "FAST"))
    muss(gemischt["urteil"] == "VERBESSERUNGSWUERDIG",
         f"ein AVERAGE muss das Gesamturteil heben, war {gemischt['urteil']}")
    schlecht = bewerte_seite(_fixture_antwort("FAST", "SLOW", "FAST"))
    muss(schlecht["urteil"] == "SCHLECHT", f"ein SLOW muss SCHLECHT ergeben, war {schlecht['urteil']}")

    # 3. Ohne Felddaten: UNGEPRUEFT – niemals GUT
    leer = bewerte_seite({"lighthouseResult": {"categories": {"performance": {"score": 1.0}}}})
    muss(leer["urteil"] == "UNGEPRUEFT", "ohne Felddaten darf nie GUT herauskommen")

    # 4. Origin-Felddaten werden genutzt, wenn Seiten-Daten fehlen
    origin = _fixture_antwort("FAST", "FAST", "FAST")
    origin["originLoadingExperience"] = origin.pop("loadingExperience")
    muss(bewerte_seite(origin)["feld_quelle"] == "originLoadingExperience",
         "Origin-Felddaten müssen erkannt werden")

    # 5. Gesamturteil: keine einzige geprüfte Seite ist STOERUNG, nicht GUT
    urteil, anzahl = gesamturteil([{"pfad": "/", "urteil": "UNGEPRUEFT"}])
    muss(urteil == "STOERUNG" and anzahl == 0,
         f"ohne geprüfte Seite muss STOERUNG stehen, war {urteil}/{anzahl}")
    urteil, anzahl = gesamturteil([{"pfad": "/", "urteil": "UNGEPRUEFT"},
                                  {"pfad": "/x/", "urteil": "SCHLECHT"}])
    muss(urteil == "SCHLECHT" and anzahl == 1, f"Befund muss gewinnen, war {urteil}/{anzahl}")

    # 6. URL-Bau
    muss(baue_url("https://franksfinanzcheck.de", "/cockpit/") == "https://franksfinanzcheck.de/cockpit/",
         "baue_url muss doppelte Schrägstriche vermeiden")
    muss("strategy=desktop" in psi_url("https://x.de/", "desktop"), "Strategie muss in der Abfrage stehen")

    # 7. Bericht nennt UNGEPRÜFT statt „grün"
    text = bericht([{"pfad": "/", "urteil": "UNGEPRUEFT", "feld": {}, "labor_scores": {}}],
                   "mobile", "2026-10-26", "STOERUNG")
    muss("UNGEPRÜFT" in text, "Bericht muss UNGEPRÜFT ausweisen")

    # 8. Geheimnis-Schwärzung (#1026): der Schlüssel darf NIRGENDS stehen.
    geheim = "AIzaSyD-geheim-1234567890"
    roh = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=x&key={geheim}"
    muss(geheim not in schwaerze(roh), "Schlüssel überlebt die Schwärzung")
    muss("key=***" in schwaerze(roh), "geschwärzter Platzhalter fehlt")
    muss(geheim not in schwaerze(f"Fehler bei {roh}: HTTP 429"),
         "Schlüssel überlebt die Schwärzung in fremdem Text")
    muss(schwaerze("ohne Schlüssel") == "ohne Schlüssel",
         "Schwärzung verändert Text ohne Schlüssel")

    # 9. Transiente Antworten werden begrenzt wiederholt, 404 nicht.
    import io as _io
    import urllib.error as _ue

    def _http(code, kopf=None):
        fehler_obj = _ue.HTTPError("https://x", code, "Fehler", kopf or {}, _io.BytesIO(b""))

        def hole_attrappe(url, zeitlimit=60, versuche=VERSUCHE, pause=lambda s: None):
            raise fehler_obj
        return hole_attrappe

    # hole() mit injizierter Pause prüfen (kein echter Wartetakt im Selbsttest)
    zaehler = {"n": 0}

    class _Antwort:
        def __init__(self, nutzlast): self._roh = nutzlast
        def read(self): return self._roh
        def __enter__(self): return self
        def __exit__(self, *a): return False

    pausen: list[float] = []

    def urlopen_wackelig(request, timeout=0):
        zaehler["n"] += 1
        if zaehler["n"] < 3:
            raise _ue.HTTPError(request.full_url, 503, "Service Unavailable", {}, None)
        return _Antwort(b'{"ok": true}')

    original_urlopen = urllib.request.urlopen
    urllib.request.urlopen = urlopen_wackelig
    try:
        antwort = hole("https://x/api?key=geheim", versuche=3, pause=pausen.append)
    finally:
        urllib.request.urlopen = original_urlopen
    muss(antwort == {"ok": True}, f"Retry lieferte keine Antwort: {antwort!r}")
    muss(zaehler["n"] == 3, f"Retry-Zahl falsch: {zaehler['n']}")
    muss(len(pausen) == 2 and all(p >= 0 for p in pausen), f"Backoff fehlt: {pausen}")

    # Ein 404 ist endgültig: genau EIN Versuch, dann Ausnahme.
    zaehler["n"] = 0

    def urlopen_404(request, timeout=0):
        zaehler["n"] += 1
        raise _ue.HTTPError(request.full_url, 404, "Not Found", {}, None)

    urllib.request.urlopen = urlopen_404
    try:
        try:
            hole("https://x/api?key=geheim", versuche=3, pause=lambda s: None)
            fehler.append("404 wurde nicht erhoben")
        except _ue.HTTPError as ausnahme:
            muss(ausnahme.code == 404, "404 kam nicht durch")
    finally:
        urllib.request.urlopen = original_urlopen
    muss(zaehler["n"] == 1, f"404 wurde {zaehler['n']}× versucht (muss 1 sein)")

    if fehler:
        print("🛑 SELBSTTEST DER CWV-FELD-WACHE FEHLGESCHLAGEN:")
        for f in fehler:
            print("  ·", f)
        return 2
    print("✅ CWV-Feld-Wache: Selbsttest grün (Abbildung, Aggregation, UNGEPRÜFT-Regel, "
          "URL-Bau, Bericht, Schwärzung, Retry)")
    return 0


# --------------------------------------------------------------------------
#  Hauptlauf
# --------------------------------------------------------------------------

def messe(ziele: list[dict], basis: str, strategie: str, schluessel: str | None,
          fixture: Path | None = None) -> tuple[list[dict], list[str]]:
    punkte: list[dict] = []
    stoerungen: list[str] = []
    schluessel_teil = f"&key={urllib.parse.quote(schluessel)}" if schluessel else ""
    for ziel in ziele:
        pfad = str(ziel["pfad"])
        url = baue_url(basis, pfad)
        try:
            if fixture:
                antwort = json.loads(fixture.read_text(encoding="utf-8"))
            else:
                antwort = hole(psi_url(url, strategie) + schluessel_teil)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError,
                json.JSONDecodeError) as exc:
            grund = schwaerze(str(exc)).strip()
            stoerungen.append(f"{pfad}: {exc.__class__.__name__}"
                              + (f" – {grund}" if grund else ""))
            continue
        befund = bewerte_seite(antwort)
        befund["pfad"] = pfad
        befund["name"] = ziel.get("name") or pfad
        befund["url"] = url
        punkte.append(befund)
    return punkte, stoerungen


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Core Web Vitals aus Felddaten (CrUX über PageSpeed Insights).")
    parser.add_argument("--ziel", action="append", default=[],
                        help="Pfad, mehrfach möglich (überschreibt die Zielliste)")
    parser.add_argument("--basis", default="https://franksfinanzcheck.de")
    parser.add_argument("--strategie", default="mobile", choices=("mobile", "desktop"))
    parser.add_argument("--json", action="store_true", help="Maschinenausgabe")
    parser.add_argument("--schreiben", action="store_true",
                        help="data/cwv/feld/* schreiben (Befund + Verlauf)")
    parser.add_argument("--fixture", type=Path, help="Antwort aus Datei statt Netz")
    parser.add_argument("--datum", help="Datum für den Bericht (JJJJ-MM-TT)")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    datum = args.datum or datetime.date.today().isoformat()
    if args.ziel:
        ziele = [{"pfad": p, "name": p} for p in args.ziel]
    else:
        try:
            ziele = lade_ziele()
        except (OSError, ValueError) as exc:
            print(f"🛑 Zielliste nicht lesbar: {exc}", file=sys.stderr)
            return 2

    punkte, stoerungen = messe(ziele, args.basis, args.strategie, api_schluessel(),
                              args.fixture)

    if not punkte:
        print("🛑 Keine Seite messbar – das ist eine Störung, kein Befund.", file=sys.stderr)
        for s in stoerungen:
            print("  ·", s, file=sys.stderr)
        return 2

    urteil, anzahl = gesamturteil(punkte)
    text = bericht(punkte, args.strategie, datum, urteil)
    if args.schreiben:
        schreibe(punkte, args.strategie, datum, urteil)

    if args.json:
        print(json.dumps({"datum": datum, "strategie": args.strategie, "urteil": urteil,
                          "geprueft": anzahl, "seiten": punkte, "stoerungen": stoerungen},
                         ensure_ascii=False, indent=2))
    else:
        print(text, end="")
        for s in stoerungen:
            print(f"⚠️  Störung: {s}")

    # Ein Befund ist ein Befund – auch wenn einzelne Seiten nicht messbar waren.
    if "SCHLECHT" in [p["urteil"] for p in punkte]:
        return 1
    if urteil == "STOERUNG" or stoerungen:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
