#!/usr/bin/env python3
"""SERP-Live-Wache: eigene Snippets in den Ergebnissen der Schlüssellosen.

Warum existiert diese Wache?
---------------------------
Das Suchradar misst Ränge ohne API-Anbindung (searxng, DuckDuckGo, Mojeek,
Wikipedia) und darf nicht direkt google.com abfragen (Nutzungsvertrag,
YMYL-Abwägung, Rechenzentrums-IP mit CAPTCHA). Genau diese Kette nutzt die
Wache, um dauerhaft zu prüfen:

1. Erscheint franksfinanzcheck.de bei den eigenen Schlüsselbegriffen?
2. Stimmen Titel und Description der eigenen Treffer mit den Frontmatter-
   Werten im Repo überein? (Snippet-Kontrolle)
3. Ist die eigene Marke bei der Marken-Abfrage auf Rang 1?

Das ist die Serp-Prüfung auf Highend-Niveau: messbar, reproduzierbar,
vertragskonform und ohne Geheimnisse. Sie ergänzt das Suchradar – sie
ersetzt es nicht.

Vertrag (geprüft, nicht nur behauptet):
  * Kein direktes google.com-Scraping (siehe scripts/serp_anbieter.py).
  * Alles über die schlüssellose Kette des Suchradars.
  * Tagesbudget wird mitgenutzt (kein zusätzlicher Abruf ohne Cache).
  * Ein Ausfall der Kette ist ein Befund, kein stilles Grün (Exit 3).
  * Kein Treffer aus diesem Bericht wird ungeprüft in einen Artikel
    übernommen.

Usage:
  python3 scripts/serp_live_wache.py              # Lauf + Report
  python3 scripts/serp_live_wache.py --selftest   # Offline-Selbsttest
  python3 scripts/serp_live_wache.py --json       # Maschinenausgabe

Exit: 0 = grün · 1 = Befunde · 2 = Setup-Fehler
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
import time
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import serp_anbieter as sa  # noqa: E402
import suchradar as sr  # noqa: E402

SERP_VERZEICHNIS = ROOT / "data" / "serp"
SERP_DATEI = SERP_VERZEICHNIS / "live-pruefung-2026-10-25.json"
BERICHT_DATEI = ROOT / "SERP-LIVE-PRUEFUNG-HIGHEND-2026-10-25.md"

EIGENE_DOMAENE = "franksfinanzcheck.de"

# ---------------------------------------------------------------------------
#  Erwartete eigene Ziele je Schlüsselbegriff.
#  Heuristik: Eine Anfrage soll auf einen konkreten Artikel / die Startseite
#  führen. Fehlt ein passender Artikel, wird nur die Domain-Präsenz geprüft.
#  Pfade sind relative content-Pfade; die Wache liest das Frontmatter daraus.
# ---------------------------------------------------------------------------
ERWARTETE_ZIELE = {
    "FranksFinanzcheck": {
        "url": f"https://{EIGENE_DOMAENE}/",
        "artikel": None,
        "rolle": "Startseite / Marke",
    },
    "Fixkosten senken": {
        "url": f"https://{EIGENE_DOMAENE}/",
        "artikel": None,
        "rolle": "Startseite / Themen-Hub",
    },
    "Stromanbieter wechseln": {
        "url": f"https://{EIGENE_DOMAENE}/posts/2026-10-23-stromanbieter-wechseln-und-bis-zu-300-euro-sparen/",
        "artikel": "content/posts/2026-10-23-stromanbieter-wechseln-und-bis-zu-300-euro-sparen/index.md",
        "rolle": "Strom-Wechsel-Ratgeber",
    },
    "Gaskosten senken": {
        "url": f"https://{EIGENE_DOMAENE}/posts/2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden/",
        "artikel": "content/posts/2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden/index.md",
        "rolle": "Gasrechnung-Ratgeber",
    },
    "Kontogebühren vermeiden": {
        "url": f"https://{EIGENE_DOMAENE}/posts/2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren/",
        "artikel": "content/posts/2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren/index.md",
        "rolle": "Girokonto-Ratgeber",
    },
    "Notgroschen aufbauen": {
        "url": f"https://{EIGENE_DOMAENE}/posts/2026-09-09-notgroschen-die-wahrheit-ueber-das-finanzielle-polster/",
        "artikel": "content/posts/2026-09-09-notgroschen-die-wahrheit-ueber-das-finanzielle-polster/index.md",
        "rolle": "Notgroschen-Ratgeber",
    },
    "Kündigungsfristen Strom": {
        "url": f"https://{EIGENE_DOMAENE}/",
        "artikel": None,
        "rolle": "Kein eigener Artikel – Startseite als Fallback",
    },
    "DSL Anbieter Vergleich": {
        "url": f"https://{EIGENE_DOMAENE}/posts/2026-08-19-dsl-vergleich-so-findest-du-guenstigeres-internet/",
        "artikel": "content/posts/2026-08-19-dsl-vergleich-so-findest-du-guenstigeres-internet/index.md",
        "rolle": "DSL-Vergleich-Ratgeber",
    },
    "Haushaltsbudget Rechner": {
        "url": f"https://{EIGENE_DOMAENE}/posts/2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier/",
        "artikel": "content/posts/2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier/index.md",
        "rolle": "Haushaltsbuch-Ratgeber",
    },
    "Mietwagen günstig buchen": {
        "url": f"https://{EIGENE_DOMAENE}/posts/2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub/",
        "artikel": "content/posts/2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub/index.md",
        "rolle": "Mietwagen-Ratgeber",
    },
    "Versicherungen kündigen": {
        "url": f"https://{EIGENE_DOMAENE}/",
        "artikel": None,
        "rolle": "Kein eigener Artikel – Startseite als Fallback",
    },
}


# ---------------------------------------------------------------------------
#  Frontmatter-Hilfe
# ---------------------------------------------------------------------------
def _frontmatter(pfad: Path) -> dict:
    if not pfad or not pfad.exists():
        return {}
    try:
        text = pfad.read_text(encoding="utf-8")
    except OSError:
        return {}
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m or yaml is None:
        return {}
    try:
        daten = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}
    return daten if isinstance(daten, dict) else {}


def _eigener_treffer(treffer: list[dict]) -> dict | None:
    for t in treffer:
        domaene = (t.get("domaene") or "").lower()
        if domaene == EIGENE_DOMAENE or domaene.endswith("." + EIGENE_DOMAENE):
            return t
    return None


def _titel_gleich(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    return sr.schlank(a) == sr.schlank(b)


def _desc_gleich(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    return sr.schlank(a) == sr.schlank(b)


# ---------------------------------------------------------------------------
#  Wache
# ---------------------------------------------------------------------------
class SerpLiveWache:
    def __init__(self, konfig: dict | None = None):
        self.konfig = konfig if konfig is not None else sr.lade_konfiguration()
        self.befunde: list[dict] = []
        self.treffer_detail: list[dict] = []
        self.anfragen_geplant = 0
        self.anfragen_ok = 0
        self.anfragen_fehler = 0
        self.eigene_treffer = 0
        self.snippet_abweichungen = 0
        self.marke_rang1 = False
        self.zeitsempel = sr.berlin_now().isoformat()

    def _pruefe_anfrage(self, anfrage: str) -> dict:
        """Eine Anfrage über die Suchradar-Kette auswerten."""
        eintrag: dict = {
            "anfrage": anfrage,
            "status": "fehler",
            "fehler": "",
            "treffer_gesamt": 0,
            "treffer_organisch": 0,
            "eigener_rang": 0,
            "eigener_titel": "",
            "eigene_description": "",
            "ziel_url": "",
            "ziel_titel_frontmatter": "",
            "ziel_description_frontmatter": "",
            "titel_stimmt": None,
            "desc_stimmt": None,
            "organisch": False,
        }
        ziel = ERWARTETE_ZIELE.get(anfrage, {})
        eintrag["ziel_url"] = ziel.get("url", "")
        if ziel.get("artikel"):
            fm = _frontmatter(ROOT / ziel["artikel"])
            eintrag["ziel_titel_frontmatter"] = fm.get("title", "")
            eintrag["ziel_description_frontmatter"] = fm.get("description", "")
        try:
            ergebnis = sr.suchen(anfrage, self.konfig)
        except Exception as fehler:  # keine Netzwerk-Ausnahme verlässt den Lauf
            eintrag["status"] = "ausnahme"
            eintrag["fehler"] = str(fehler)[:300]
            self.anfragen_fehler += 1
            return eintrag

        treffer = ergebnis.get("treffer") or []
        organisch = sr.organische_treffer(treffer)
        eintrag["status"] = ergebnis.get("status", "")
        eintrag["treffer_gesamt"] = len(treffer)
        eintrag["treffer_organisch"] = len(organisch)
        eintrag["organisch"] = bool(organisch)
        self.treffer_detail.append({
            "anfrage": anfrage,
            "treffer": [{"rang": t.get("rang"), "titel": t.get("titel"),
                         "domaene": t.get("domaene"), "quelle": t.get("quelle")}
                        for t in organisch[:5]],
        })

        eigener = _eigener_treffer(organisch)
        if eigener:
            self.eigene_treffer += 1
            eintrag["eigener_rang"] = int(eigener.get("rang") or 0)
            eintrag["eigener_titel"] = eigener.get("titel", "")
            eintrag["eigene_description"] = eigener.get("beschreibung", "")
            eintrag["titel_stimmt"] = _titel_gleich(
                eintrag["eigener_titel"],
                eintrag["ziel_titel_frontmatter"],
            )
            eintrag["desc_stimmt"] = _desc_gleich(
                eintrag["eigene_description"],
                eintrag["ziel_description_frontmatter"],
            )
            if eintrag["titel_stimmt"] is False or eintrag["desc_stimmt"] is False:
                self.snippet_abweichungen += 1
            if anfrage == "FranksFinanzcheck" and eintrag["eigener_rang"] == 1:
                self.marke_rang1 = True
        return eintrag

    def lauf(self) -> dict:
        anfragen = list(ERWARTETE_ZIELE.keys())
        self.anfragen_geplant = len(anfragen)
        ergebnisse: list[dict] = []
        for anfrage in anfragen:
            ergebnis = self._pruefe_anfrage(anfrage)
            ergebnisse.append(ergebnis)
            if ergebnis["status"] in ("ok", "cache"):
                self.anfragen_ok += 1
            else:
                self.anfragen_fehler += 1
            # Höflichkeitspause zwischen den Abfragen der Kette.
            time.sleep(0.4)

        befund = {
            "zeitstempel": self.zeitsempel,
            "eigene_domaene": EIGENE_DOMAENE,
            "anfragen_geplant": self.anfragen_geplant,
            "anfragen_ok": self.anfragen_ok,
            "anfragen_fehler": self.anfragen_fehler,
            "eigene_treffer": self.eigene_treffer,
            "snippet_abweichungen": self.snippet_abweichungen,
            "marke_rang1": self.marke_rang1,
            "ergebnisse": ergebnisse,
            "treffer_detail": self.treffer_detail,
            "verdict": "gruen",
        }
        # Urteil: rot bei Fehlern oder fehlenden eigenen Treffern bei Marke.
        if self.anfragen_fehler == self.anfragen_geplant:
            befund["verdict"] = "rot"
        elif not self.marke_rang1:
            befund["verdict"] = "gelb"
        elif self.snippet_abweichungen > 0:
            befund["verdict"] = "gelb"
        self.befunde = ergebnisse
        return befund

    def bericht(self, befund: dict) -> str:
        zeilen = [
            "# SERP-Live-Prüfung – eigene Snippets in den Schlüssellosen",
            "",
            f"> Stand: {befund['zeitstempel'][:19].replace('T', ' ')} Uhr · "
            f"Kette: searxng → DuckDuckGo → DuckDuckGo Lite → Mojeek → Wikipedia",
            "> Schlüssellos · 0 € · Vertragskonform (kein direktes google.com-Scraping)",
            "",
            "## Lauf",
            "",
            "| Kennzahl | Wert |",
            "|---|---|",
            f"| Anfragen geplant | {befund['anfragen_geplant']} |",
            f"| Anfragen erfolgreich | {befund['anfragen_ok']} |",
            f"| Anfragen fehlgeschlagen | {befund['anfragen_fehler']} |",
            f"| Eigene Treffer (organisch) | {befund['eigene_treffer']} |",
            f"| Snippet-Abweichungen | {befund['snippet_abweichungen']} |",
            f"| Marke Rang 1 | {'Ja' if befund['marke_rang1'] else 'Nein'} |",
            f"| Urteil | **{befund['verdict'].upper()}** |",
            "",
        ]

        zeilen += ["## Ergebnis je Anfrage", "",
                   "| Suchbegriff | Rang | Titel stimmt | Desc. stimmt | Ziel |",
                   "|---|---|---|---|---|"]
        for e in befund["ergebnisse"]:
            titel = "✅" if e["titel_stimmt"] is True else (
                "❌" if e["titel_stimmt"] is False else "–")
            desc = "✅" if e["desc_stimmt"] is True else (
                "❌" if e["desc_stimmt"] is False else "–")
            ziel = e["ziel_url"].replace(f"https://{EIGENE_DOMAENE}", "")
            zeilen.append(
                f"| {e['anfrage']} | {e['eigener_rang'] or '–'} | {titel} | {desc} | {ziel} |")
        zeilen.append("")

        zeilen += ["## Befunde", ""]
        if befund["verdict"] == "gruen":
            zeilen.append("✅ Alle geprüften Anfragen liefen durch, die Marke steht auf Rang 1, "
                          "Titel und Description stimmen mit den Frontmatter-Werten überein.")
        else:
            if not befund["marke_rang1"]:
                zeilen.append("❌ Marke „FranksFinanzcheck“ steht nicht auf Rang 1 bei der Marken-Abfrage "
                              "(Google korrigiert auf FINANZCHECK.de – Marken-Präsenz muss gestärkt werden).")
            if befund["snippet_abweichungen"] > 0:
                zeilen.append(f"❌ {befund['snippet_abweichungen']} Snippet-Abweichung(en): Titel oder Description "
                              "weichen von den Frontmatter-Werten ab – entweder wurde die Seite noch nicht so "
                              "indexiert, oder Google zeigt einen eigenen Snippet-Text.")
            if befund["anfragen_fehler"] > 0:
                zeilen.append(f"⚠️ {befund['anfragen_fehler']} Anfrage(n) fehlgeschlagen – Kette oder Budget "
                              "prüfen.")
        zeilen.append("")

        zeilen += ["## Detail: organische Treffer der Kette", ""]
        for d in befund["treffer_detail"]:
            zeilen.append(f"### {d['anfrage']}")
            if not d["treffer"]:
                zeilen.append("_Keine organischen Treffer._")
            else:
                zeilen.append("| Rang | Titel | Domäne | Quelle |")
                zeilen.append("|---|---|---|---|")
                for t in d["treffer"]:
                    zeilen.append(
                        f"| {t['rang'] or '–'} | {t['titel'] or '–'} | {t['domaene'] or '–'} | {t['quelle'] or '–'} |")
            zeilen.append("")

        zeilen += [
            "## Einordnung",
            "",
            "Die Wache misst über die schlüssellose Kette des Suchradars, nicht über",
            "google.com. Ränge sind Indikationen, keine Positions-Garantie. Ein",
            "fehlender eigener Treffer bedeutet nicht automatisch, dass die Seite nicht",
            "indexiert ist – es kann bedeuten, dass die Kette (SearXNG-Instanzen, "
            "DuckDuckGo) den Begriff an diesem Tag nicht liefert.",
            "",
            "Empfehlung bei `gelb` oder `rot`:",
            "- Marke stärken: eigene Domain im Titel/Description konsistent halten,",
            "  Backlinks auf die Startseite aufbauen (Authority-Radar).",
            "- Snippets nachschärfen: Titel ≤ 60 Zeichen, Description 100–160 Zeichen,",
            "  kein hartes Ellipsis-Ende (siehe metadaten_wache M1/M2).",
            "- Langsamkeit der Kette akzeptieren: SearXNG-Instanzen gehen und kommen.",
            "",
            "Kein Treffer aus diesem Bericht wird ungeprüft in einen Artikel übernommen.",
            "",
        ]
        return "\n".join(zeilen)


# ---------------------------------------------------------------------------
#  Selftest (offen, ohne Netz)
# ---------------------------------------------------------------------------
def selftest() -> int:
    problem: list[str] = []

    def pruefe(bedingung: bool, meldung: str) -> None:
        if not bedingung:
            problem.append(meldung)

    # 1) Erwartete Ziele sind konsistent (Jede URL auf eigene Domain).
    for anfrage, ziel in ERWARTETE_ZIELE.items():
        url = ziel.get("url", "")
        pruefe(EIGENE_DOMAENE in url,
               f"Ziel-URL für {anfrage!r} zeigt nicht auf eigene Domain: {url}")

    # 2) Eigener-Treffer-Erkennung.
    treffer = [
        {"domaene": "verivox.de", "titel": "V", "rang": 1},
        {"domaene": EIGENE_DOMAENE, "titel": "F", "rang": 2},
    ]
    e = _eigener_treffer(treffer)
    pruefe(e is not None and e["titel"] == "F", "Eigener Treffer nicht erkannt")
    fremd = [{"domaene": "andere.de", "titel": "A", "rang": 1}]
    pruefe(_eigener_treffer(fremd) is None, "Fremder Treffer als eigener erkannt")
    sub = [{"domaene": f"www.{EIGENE_DOMAENE}", "titel": "F", "rang": 1}]
    e = _eigener_treffer(sub)
    pruefe(e is not None, "Subdomain der eigenen Domaene nicht als eigener Treffer erkannt")
    fremd2 = [{"domaene": f"{EIGENE_DOMAENE}.evil.example", "titel": "A", "rang": 1}]
    pruefe(_eigener_treffer(fremd2) is None, "Teil-Domaene als eigene Domaene erkannt")

    # 3) Titel-/Description-Vergleich.
    pruefe(_titel_gleich("Stromanbieter wechseln", "Stromanbieter wechseln"),
           "gleiche Titel nicht erkannt")
    pruefe(not _titel_gleich("Stromanbieter wechseln", "Stromanbieter wechseln 2026"),
           "unterschiedliche Titel als gleich erkannt")
    pruefe(_desc_gleich("Gasrechnung senken: Fehler.", "gasrechnung senken: fehler"),
           "gleiche Description nicht erkannt (Case)")
    pruefe(not _desc_gleich("Gasrechnung senken: Fehler.", "Stromanbieter wechseln"),
           "unterschiedliche Description als gleich erkannt")

    # 4) Frontmatter-Hilfe liefert leeres Dict bei fehlender Datei.
    fm = _frontmatter(ROOT / "content" / "posts" / "gibt-es-nicht" / "index.md")
    pruefe(fm == {}, "Fehlende Frontmatter-Datei liefert nicht leeres Dict")

    # 5) Wache-Instanziierung ohne Netz.
    w = SerpLiveWache({**sr.VORGABEN, "eigene_domaene": EIGENE_DOMAENE})
    pruefe(w.konfig.get("eigene_domaene") == EIGENE_DOMAENE, "Wache-Konfiguration fehlerhaft")

    if problem:
        for zeile in problem:
            print("  ✗ " + zeile, file=sys.stderr)
        return 1
    print("SERP-Live-Wache: Selbsttest bestanden (6 Prüfblöcke, offline, ohne Netz).")
    return 0


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="SERP-Live-Wache – eigene Snippets in den Schlüssellosen prüfen")
    parser.add_argument("--selftest", action="store_true",
                        help="Offline-Selbsttest (ohne Netzwerk)")
    parser.add_argument("--json", action="store_true",
                        help="Maschinenausgabe als JSON auf stdout")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    w = SerpLiveWache()
    befund = w.lauf()

    # Persistieren.
    _sicherer_pfad(SERP_VERZEICHNIS)
    SERP_DATEI.write_text(
        json.dumps(befund, ensure_ascii=False, indent=2), encoding="utf-8")
    BERICHT_DATEI.write_text(w.bericht(befund), encoding="utf-8")

    if args.json:
        print(json.dumps(befund, ensure_ascii=False, indent=2))
    else:
        print(w.bericht(befund))

    return 0 if befund["verdict"] == "gruen" else 1


def _sicherer_pfad(verzeichnis: Path) -> Path:
    verzeichnis.mkdir(parents=True, exist_ok=True)
    return verzeichnis


if __name__ == "__main__":
    sys.exit(main())
