#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
#  CWV-FELD-WACHE – die Zahlen, die echte Besucher erleben
#  ------------------------------------------------------------
#  WARUM ES DIESE WACHE GIBT (26.10.2026 · gehärtet 03.11.2026, #1026)
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
#  3. Ein Netzfehler oder 0 geprüfte Ziele ist STÖRUNG (Exit 2), kein
#     Befund und niemals Grün. Transiente PSI-Störungen (HTTP 429/5xx,
#     Zeitlimit) fängt `hole()` mit begrenztem Backoff ab; was danach
#     offen bleibt, wird mit HTTP-Status (geheimnisfrei!) benannt, und
#     der Bericht trennt ausdrücklich „API erreichbar, aber noch keine
#     CrUX-28-Tage-Daten" von „API-/Netzstörung".
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
#  Exit: 0 = mindestens ein Ziel mit CrUX-Daten, keins SCHLECHT
#        1 = Befund (mindestens ein Ziel SCHLECHT)
#        2 = Störung (Netz/API-Fehler oder alle Ziele ohne CrUX-Daten – C2)
#
#  API-Schlüssel: `PSI_API_KEY` (optional). Ohne Schlüssel antwortet
#  die API stark gedrosselt; der Lauf bleibt möglich. Der Schlüssel
#  wird NIE ausgegeben, geloggt oder in eine Datei geschrieben.
# ============================================================

from __future__ import annotations

import argparse
import contextlib
import datetime
import email.message
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
ZIELE_DATEI = ROOT / "data" / "cwv" / "feld_ziele.json"
BEFUND_JSON = ROOT / "data" / "cwv" / "feld" / "befund.json"
BEFUND_MD = ROOT / "data" / "cwv" / "feld" / "befund.md"
VERLAUF = ROOT / "data" / "cwv" / "feld" / "verlauf.jsonl"

API = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

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

# Transiente HTTP-Statuscodes der PageSpeed-Insights-API, bei denen eine
# begrenzte Wiederholung sinnvoll ist (insbesondere Rate-Limits ohne Key auf
# geteilten CI-Runner-IPs). Permanente Client-Fehler (400/401/403/404) werden
# nie wiederholt.
TRANSIENTE_HTTP_CODES = frozenset({408, 429, 500, 502, 503, 504})
MAX_RETRY_WARTEZEIT = 30.0
STANDARD_ZIEL_PAUSE = 1.5

HTTP_HINWEISE = {
    400: "Ungültige Abfrage",
    401: "API-Zugriff verweigert – PSI_API_KEY prüfen",
    403: "API-Zugriff verweigert – PSI_API_KEY prüfen",
    404: "API-Endpunkt nicht gefunden",
    408: "Zeitlimit der PageSpeed-API",
    429: "Rate-Limit – PSI_API_KEY setzen oder später wiederholen",
    500: "PageSpeed-API vorübergehend gestört",
    502: "PageSpeed-API vorübergehend gestört",
    503: "PageSpeed-API vorübergehend gestört",
    504: "PageSpeed-API-Zeitüberschreitung",
}

# Linearer Query-Parameter-Filter ohne Backtracking (ReDoS-fest).
KEY_QUERY_MUSTER = re.compile(r"([?&]key=)[^&\s\"'>]+", re.IGNORECASE)


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
#  Geheimnisschutz & Störungs-Klassifikation (rein, ohne Netz)
# --------------------------------------------------------------------------

def schwaerze_geheimnis(text: str, schluessel: str | None = None) -> str:
    """Tilgt `key=...`-Parameter und den API-Schlüssel aus jedem Text."""
    bereinigt = KEY_QUERY_MUSTER.sub(r"\1[GESCHWAERZT]", str(text or ""))
    if schluessel:
        bereinigt = bereinigt.replace(schluessel, "[GESCHWAERZT]")
        codiert = urllib.parse.quote(schluessel)
        if codiert:
            bereinigt = bereinigt.replace(codiert, "[GESCHWAERZT]")
    return bereinigt


def klassifiziere_stoerung(exc: BaseException, schluessel: str | None = None) -> str:
    """Formatiert Netz-/API-Ausnahmen mit HTTP-Status und garantiert ohne Key."""
    if isinstance(exc, urllib.error.HTTPError):
        hinweis = HTTP_HINWEISE.get(exc.code)
        basis = f"HTTPError {exc.code}" + (f" ({hinweis})" if hinweis else "")
        return schwaerze_geheimnis(basis, schluessel)
    if isinstance(exc, TimeoutError):
        return "TimeoutError (Zeitlimit der PageSpeed-API überschritten)"
    if isinstance(exc, urllib.error.URLError):
        grund = getattr(exc, "reason", None)
        grund_name = grund.__class__.__name__ if isinstance(grund, BaseException) else ""
        zusatz = f" ({grund_name})" if grund_name and grund_name != "URLError" else ""
        return schwaerze_geheimnis(f"URLError{zusatz}", schluessel)
    return schwaerze_geheimnis(exc.__class__.__name__, schluessel)


def stoerung_ursache(punkte: list[dict], stoerungen: list[str]) -> str | None:
    """Unterscheidet echten Abrufausfall von fehlenden CrUX-28-Tage-Daten."""
    if not punkte:
        return "abruf_fehlgeschlagen"
    if stoerungen:
        return "teilabruf_fehlgeschlagen"
    if all(p.get("urteil") == "UNGEPRUEFT" for p in punkte):
        return "keine_crux_daten"
    return None


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
        # Keine einzige Seite mit Felddaten: Ungeprüft gilt nie als Grün (C2).
        return "STOERUNG", 0
    schlechtestes = max((s["urteil"] for s in geprueft), key=lambda u: RANG.get(u, 3))
    return schlechtestes, len(geprueft)


# --------------------------------------------------------------------------
#  Netz (mit begrenztem Backoff für transiente PSI-Störungen)
# --------------------------------------------------------------------------

def _retry_wartezeit(exc: BaseException, versuch: int, basis_pause: float) -> float:
    standard = min(MAX_RETRY_WARTEZEIT, basis_pause * (3 ** (versuch - 1)))
    if isinstance(exc, urllib.error.HTTPError) and exc.headers is not None:
        roh = str(exc.headers.get("Retry-After") or "").strip()
        if roh.isdigit():
            return min(MAX_RETRY_WARTEZEIT, max(standard, float(int(roh))))
    return standard


def hole(
    url: str,
    zeitlimit: int = 60,
    *,
    versuche: int = 3,
    basis_pause: float = 2.0,
    schlaf: Callable[[float], None] = time.sleep,
) -> dict:
    """Eine PSI-Antwort mit begrenzter Wiederholung bei 429/5xx/Netzstörung."""
    anzahl_versuche = max(1, versuche)
    for versuch in range(1, anzahl_versuche + 1):
        request = urllib.request.Request(
            url, headers={"User-Agent": "franksfinanzcheck-cwv-feld/1.0"}
        )
        try:
            with urllib.request.urlopen(request, timeout=zeitlimit) as antwort:  # noqa: S310 – feste API
                return json.loads(antwort.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            with contextlib.suppress(Exception):
                exc.close()
            if exc.code in TRANSIENTE_HTTP_CODES and versuch < anzahl_versuche:
                schlaf(_retry_wartezeit(exc, versuch, basis_pause))
                continue
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if versuch < anzahl_versuche:
                schlaf(_retry_wartezeit(exc, versuch, basis_pause))
                continue
            raise
    raise RuntimeError("unerreichbar")


def api_schluessel() -> str | None:
    """Optionaler Schlüssel aus der Umgebung – wird nie ausgegeben."""
    wert = (os.environ.get("PSI_API_KEY") or "").strip()
    return wert or None


# --------------------------------------------------------------------------
#  Bericht
# --------------------------------------------------------------------------

def bericht(
    punkte: list[dict],
    strategie: str,
    datum: str,
    urteil: str,
    stoerungen: list[str] | None = None,
) -> str:
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
    ursache = stoerung_ursache(punkte, stoerungen or [])
    if urteil == "STOERUNG" and ursache == "keine_crux_daten":
        zeilen += [
            "",
            "**Einordnung der Störung:** Die PageSpeed-Insights-API hat für alle "
            "geprüften Ziele geantwortet, liefert im 28-Tage-Fenster von CrUX "
            "aber noch für keine Seite Felddaten (Besucheraufkommen unter Googles "
            "CrUX-Mindestschwelle). Gemäß Hausregel (C2) gilt „ungeprüft\" nicht "
            "als grün (Exit 2) – das ist keine kaputte API und kein schlechter "
            "Messwert.",
        ]
    schlecht = [p["pfad"] for p in punkte if p["urteil"] == "SCHLECHT"]
    if schlecht:
        zeilen += ["", "**Befund (schlecht):** " + ", ".join(f"`{p}`" for p in schlecht)]
    return "\n".join(zeilen) + "\n"


def schreibe(
    punkte: list[dict],
    strategie: str,
    datum: str,
    urteil: str,
    stoerungen: list[str] | None = None,
) -> None:
    ursache = stoerung_ursache(punkte, stoerungen or [])
    for ziel in (BEFUND_JSON, BEFUND_MD, VERLAUF):
        ziel.parent.mkdir(parents=True, exist_ok=True)
    BEFUND_JSON.write_text(
        json.dumps({"datum": datum, "strategie": strategie, "urteil": urteil,
                    "stoerung_grund": ursache, "seiten": punkte},
                   ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    BEFUND_MD.write_text(bericht(punkte, strategie, datum, urteil, stoerungen), encoding="utf-8")
    with VERLAUF.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"datum": datum, "strategie": strategie, "urteil": urteil,
                            "stoerung_grund": ursache,
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

    # 7. Bericht nennt UNGEPRÜFT und erklärt fehlende CrUX-Daten ohne Scheingrün
    text = bericht([{"pfad": "/", "urteil": "UNGEPRUEFT", "feld": {}, "labor_scores": {}}],
                   "mobile", "2026-10-26", "STOERUNG")
    muss("UNGEPRÜFT" in text, "Bericht muss UNGEPRÜFT ausweisen")
    muss("Einordnung der Störung:" in text,
         "Bericht muss fehlende CrUX-28-Tage-Daten von einer kaputten API trennen")
    muss(stoerung_ursache([{"pfad": "/", "urteil": "UNGEPRUEFT"}], []) == "keine_crux_daten",
         "stoerung_ursache muss keine_crux_daten erkennen")
    muss(stoerung_ursache([], ["/: HTTPError 429"]) == "abruf_fehlgeschlagen",
         "stoerung_ursache muss abruf_fehlgeschlagen erkennen")

    # 8. Geheimnisschutz & HTTP-Klassifikation (HTTPError trägt die volle URL inkl. &key=...)
    hdrs = email.message.Message()
    hdrs["Retry-After"] = "7"
    http_429 = urllib.error.HTTPError(
        "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=https%3A%2F%2Fx.de&key=geheim-999",
        429, "Too Many Requests", hdrs, io.BytesIO(b""))
    http_429.close()
    diag = klassifiziere_stoerung(http_429, "geheim-999")
    muss("429" in diag and "Rate-Limit" in diag, f"429 muss als Rate-Limit erkennbar sein: {diag}")
    muss("geheim-999" not in diag, "API-Schlüssel darf nie in der Störungszeile stehen")
    muss("geheim-999" not in schwaerze_geheimnis("Fehler bei ?url=x&key=geheim-999 im Lauf", "geheim-999"),
         "schwaerze_geheimnis muss key-Parameter und Klartext-Key tilgen")
    muss(_retry_wartezeit(http_429, 1, 2.0) == 7.0, "Retry-After-Header muss respektiert werden")

    if fehler:
        print("🛑 SELBSTTEST DER CWV-FELD-WACHE FEHLGESCHLAGEN:")
        for f in fehler:
            print("  ·", f)
        return 2
    print("✅ CWV-Feld-Wache: Selbsttest grün (Abbildung, Aggregation, UNGEPRÜFT-Regel, Geheimnisschutz, URL-Bau, Bericht)")
    return 0


# --------------------------------------------------------------------------
#  Hauptlauf
# --------------------------------------------------------------------------

def messe(
    ziele: list[dict],
    basis: str,
    strategie: str,
    schluessel: str | None,
    fixture: Path | None = None,
    *,
    ziel_pause: float = 0.0,
    schlaf: Callable[[float], None] = time.sleep,
) -> tuple[list[dict], list[str]]:
    punkte: list[dict] = []
    stoerungen: list[str] = []
    schluessel_teil = f"&key={urllib.parse.quote(schluessel)}" if schluessel else ""
    for idx, ziel in enumerate(ziele):
        if idx > 0 and ziel_pause > 0 and not fixture:
            schlaf(ziel_pause)
        pfad = str(ziel["pfad"])
        url = baue_url(basis, pfad)
        try:
            if fixture:
                antwort = json.loads(fixture.read_text(encoding="utf-8"))
            else:
                antwort = hole(psi_url(url, strategie) + schluessel_teil)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError,
                json.JSONDecodeError) as exc:
            stoerungen.append(f"{pfad}: {klassifiziere_stoerung(exc, schluessel)}")
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

    schluessel = api_schluessel()
    punkte, stoerungen = messe(
        ziele,
        args.basis,
        args.strategie,
        schluessel,
        args.fixture,
        ziel_pause=0.0 if args.fixture else STANDARD_ZIEL_PAUSE,
    )

    if not punkte:
        print("🛑 Keine Seite messbar – das ist eine Störung, kein Befund.", file=sys.stderr)
        for s in stoerungen:
            print("  ·", schwaerze_geheimnis(s, schluessel), file=sys.stderr)
        return 2

    urteil, anzahl = gesamturteil(punkte)
    ursache = stoerung_ursache(punkte, stoerungen)
    text = bericht(punkte, args.strategie, datum, urteil, stoerungen)
    if args.schreiben:
        schreibe(punkte, args.strategie, datum, urteil, stoerungen)

    if args.json:
        print(json.dumps({"datum": datum, "strategie": strategie_wert(args.strategie), "urteil": urteil,
                          "stoerung_grund": ursache, "geprueft": anzahl, "seiten": punkte,
                          "stoerungen": stoerungen},
                         ensure_ascii=False, indent=2))
    else:
        print(text, end="")
        for s in stoerungen:
            print(f"⚠️  Störung: {schwaerze_geheimnis(s, schluessel)}")

    # Ein Befund ist ein Befund – auch wenn einzelne Seiten nicht messbar waren.
    if "SCHLECHT" in [p["urteil"] for p in punkte]:
        return 1
    if urteil == "STOERUNG" or stoerungen:
        return 2
    return 0


def strategie_wert(strategie: str) -> str:
    return strategie


if __name__ == "__main__":
    sys.exit(main())
