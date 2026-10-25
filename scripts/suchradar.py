#!/usr/bin/env python3
"""Suchradar – Google-Suchergebnis-Erfassung ohne API, ohne Schlüssel, ohne Kosten.

    python3 scripts/suchradar.py                 # Lauf: suchen → messen → berichten
    python3 scripts/suchradar.py --probe         # Erreichbarkeit der Anbieter testen
    python3 scripts/suchradar.py --status        # Cockpit-Ausgabe
    python3 scripts/suchradar.py --selftest      # Offline-Selbsttest (Fail-closed)
    python3 scripts/suchradar.py --anfrage "stromkosten senken"

WAS DAS IST
-----------
Ein Nachbau des Apify-Actors `apify/google-search-scraper`: dieselbe Frage
(„Was steht für diese Suchbegriffe auf der Ergebnisseite?"), dieselbe
Ausgabe (Rang, Titel, Beschreibung, Adresse, Merkmale), nur eben als
blogeigene Kette. Läuft **ohne API-Anbindung** – kein Schlüssel, kein
Konto, keine Rechnung. Die Anbieter-Schicht und die Begründung, warum
google.com nicht direkt angefragt wird, stehen in
`scripts/serp_anbieter.py`.

WAS ES FÜR DEN BLOG TUT
-----------------------
Der reine Trefferabruf ist die halbe Sache. Wert entsteht durch die drei
Schichten darüber:

  1. **Rang-Verfolgung.** Wo steht franksfinanzcheck.de für die eigenen
     Schlüsselbegriffe – und wie hat sich das seit dem letzten Lauf
     bewegt? Deltas, nicht Momentaufnahmen.
  2. **Wettbewerbs-Radar.** Welche Domänen belegen die Ergebnisseiten der
     eigenen Themenwelt? Das ist die Eingangsgröße für jede
     Inhaltsentscheidung, die nicht auf Bauchgefühl steht.
  3. **Merkmal-Erkennung.** Sitelinks, FAQ, Video, Vorschaubild – wer die
     Ergebnisseite mit Sonderflächen besetzt, verdrängt organische
     Treffer nach unten. Das ist messbar, also wird es gemessen.

BETRIEBSSICHERHEIT (die Regeln, die den Unterschied machen)
-----------------------------------------------------------
  · **Quote ist hart.** Jeder Anbieter hat ein Tageslimit; der Zähler
    steht in `data/suchradar/quota.json` und stoppt den Lauf, bevor das
    Limit gerissen wird. Ohne Zähler wäre „kostenlos" ein Versprechen.
  · **Zwischenspeicher.** Dieselbe Anfrage am selben Tag kostet kein
    zweites Abrufbudget (`data/suchradar/cache/`).
  · **Instanzen-Gesundheit.** SearXNG-Instanzen kommen und gehen. Jede
    Antwort wird gemessen, die Reihenfolge folgt der Erfolgsquote. Ein
    Ausfall ist eine Umschaltung, kein Laufabbruch.
  · **Kein Anbieter ≠ keine Treffer.** Liefert niemand etwas, ist der Lauf
    rot (Exit 3) und meldet. Ein leerer Bericht, der „alles gut" sagt, ist
    die teuerste Art dieses Fehlers – derselbe Befund wie #514.
  · **Trennung von Messung und Bewertung.** Alles hier misst. Kein Treffer
    wird ungeprüft in einen Artikel übernommen; die Ausgabe ist ein
    Befund für Frank, kein Redaktionstext.

GRENZE, DIE BLEIBT
------------------
Ohne Schlüssel gibt es kein Google-Original-Ranking. SearXNG bündelt den
Google-Index über fremde Instanzen, DuckDuckGo und Mojeek sind eigene
Indizes. Die Ränge sind deshalb **Indikationen**, keine Positions-Garantie.
Wo es auf die exakte Position ankommt, ist die Google Search Console die
richtige Quelle – und die ist ebenfalls kostenlos
(`docs/ANLEITUNG-GSC-API-ZUGRIFF.md`).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import serp_anbieter as sa                                # noqa: E402
from url_host import ist_host_oder_subdomain              # noqa: E402

try:                                                       # pragma: no cover
    import yaml
except ImportError:                                        # pragma: no cover
    yaml = None

ROOT = Path(__file__).resolve().parent.parent
KONFIG = ROOT / "data" / "suchradar.yaml"
ZUSTAND = ROOT / "data" / "suchradar"
# Name bewusst NICHT `*-STATUS.md`: Die .gitignore-Regel `/*-STATUS.md`
# würde das Cockpit verschlucken – und damit den einzigen menschenlesbaren
# Output eines vollautomatischen Systems in ein CI-Artefakt verbannen.
# Vorbild sind KENNZAHLEN-RADAR.md und AUTHORITY-RADAR.md: erzeugt vom
# Skript, versioniert, vom Workflow committet. Der Test
# `test_cockpit_ist_nicht_git_ignoriert` hält diesen Namen fest.
COCKPIT = ROOT / "SUCHRADAR-RADAR.md"

CACHE_VERZEICHNIS = ZUSTAND / "cache"
QUOTEN_DATEI = ZUSTAND / "quota.json"
INSTANZEN_DATEI = ZUSTAND / "instanzen.json"
VERLAUF_DATEI = ZUSTAND / "verlauf.jsonl"
RANKING_DATEI = ZUSTAND / "rankings.json"
RANKING_VERLAUF = ZUSTAND / "rankings.jsonl"
WETTBEWERB_DATEI = ZUSTAND / "wettbewerb.json"
ERGEBNIS_DATEI = ZUSTAND / "letzte_ergebnisse.json"

BERLIN = timezone(timedelta(hours=2), "MESZ")


def berlin_now() -> datetime:
    return datetime.now(BERLIN)


def heute() -> str:
    return berlin_now().strftime("%Y-%m-%d")


# ====================================================================
#  KONFIGURATION
# ====================================================================
VORGABEN = {
    "eigene_domaene": "franksfinanzcheck.de",
    "land": "de",
    "sprache": "de",
    "geraet": "desktop",
    "max_treffer": 10,
    "max_anfragen_pro_lauf": 25,
    "max_abfragen_pro_tag": 120,
    "zwischenspeicher_stunden": 18,
    "entdoppeln": True,
    "reihenfolge": list(sa.STANDARD_REIHENFOLGE),
    "searxng_instanzen": list(sa.STANDARD_SEARXNG_INSTANZEN),
    "anfragen": [],
    "schluesselbegriffe_aus_themenpool": True,
    "schluesselbegriffe_hoechstens": 15,
}


def lade_konfiguration(pfad: Path | None = None) -> dict:
    """SSOT lesen und über die Vorgaben legen.

    Eine unlesbare SSOT ist kein Grund für einen Abbruch: Der Lauf fällt
    auf die Vorgaben zurück und sagt das laut. Eine stillschweigend
    andere Konfiguration wäre schlimmer als ein Fehler.
    """
    konfig = dict(VORGABEN)
    pfad = Path(pfad) if pfad else KONFIG
    if yaml is None:
        print("HINWEIS: PyYAML fehlt – Vorgaben werden genutzt.", file=sys.stderr)
        konfig["_hinweis"] = "PyYAML fehlt"
        return konfig
    try:
        with open(pfad, encoding="utf-8") as fh:
            daten = yaml.safe_load(fh) or {}
    except FileNotFoundError:
        konfig["_hinweis"] = f"{pfad} fehlt – Vorgaben werden genutzt"
        return konfig
    except (OSError, yaml.YAMLError) as fehler:
        print(f"WARNUNG: {pfad} unlesbar ({fehler}) – Vorgaben greifen.",
              file=sys.stderr)
        konfig["_hinweis"] = "SSOT unlesbar"
        return konfig
    if not isinstance(daten, dict):
        return konfig
    for schluessel, wert in daten.items():
        if schluessel.startswith("_") or wert is None:
            continue
        konfig[schluessel] = wert
    return konfig


# ====================================================================
#  ANFRAGEN
# ====================================================================
# Unsichtbare Zeichen, die in kopierten Suchbegriffen regelmäßig auftauchen
# (PDF, Web, Tabellenkalkulation). Ein weicher Trennstrich ist ein
# Umbruch-Hinweis, kein Wortzwischenraum: „Strom­kosten" IST „stromkosten".
# Wird er zum Leerzeichen, zerfällt der Begriff – und die Anfrage findet
# nichts mehr, ohne dass jemand den Unterschied sieht. Der Themenpool
# dieses Repos hat genau diese Klasse von Korruption zweimal erlebt
# (siehe Kopfeintrag in data/topics.yaml).
#
# Die Tabelle trennt zwei Fälle: Trenn- und Bindezeichen verschwinden
# ersatzlos, Leerzeichen-Varianten werden zum echten Leerzeichen.
UNSICHTBAR_ENTFERNEN = dict.fromkeys(map(ord, "\u00ad\u200b\u200c\u200d\ufeff\u2060"), "")
UNSICHTBAR_LEERZEICHEN = dict.fromkeys(map(ord, "\u00a0\u2000\u2001\u2002\u2003"
                                                "\u2004\u2005\u2006\u2007\u2008"
                                                "\u2009\u200a\u202f\u205f\u3000"), " ")


def schlank(text: str) -> str:
    """Suchbegriff normalisieren: Kleinschreibung, Akzente weg, ein Leerzeichen."""
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = text.translate(UNSICHTBAR_ENTFERNEN).translate(UNSICHTBAR_LEERZEICHEN)
    text = "".join(z for z in text if not unicodedata.combining(z))
    # Sichtbare Gedanken- und Bindestriche bleiben ein Bindestrich.
    text = text.replace("\u2010", "-").replace("\u2011", "-").replace("\u2013", "-")
    text = re.sub(r"[^a-z0-9äöüß\s-]", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def ermittle_anfragen(konfig: dict, root: Path | None = None) -> list[dict]:
    """Anfragen aus der SSOT, ergänzt um Schlüsselbegriffe des Themenpools.

    Warum automatisch ergänzt wird: Die Konfiguration pflegt niemand
    täglich. `data/topics.yaml` wächst mit jedem neuen Thema – und genau
    diese Themen sind es, für die Rang und Wettbewerb interessieren. Wer
    die Liste von Hand führen muss, hat nach vier Wochen eine veraltete.
    """
    root = Path(root) if root else ROOT
    anfragen: list[dict] = []
    gesehen: set[str] = set()

    def hinzufuegen(text, herkunft, prioritaet=1.0):
        begriff = str(text or "").strip()
        if len(begriff) < 3:
            return
        schluessel = schlank(begriff)
        if not schluessel or schluessel in gesehen:
            return
        gesehen.add(schluessel)
        anfragen.append({"anfrage": begriff, "herkunft": herkunft,
                         "prioritaet": prioritaet})

    for eintrag in konfig.get("anfragen") or []:
        if isinstance(eintrag, str):
            hinzufuegen(eintrag, "konfiguration", 1.0)
        elif isinstance(eintrag, dict):
            hinzufuegen(eintrag.get("anfrage") or eintrag.get("query"),
                        "konfiguration", float(eintrag.get("prioritaet", 1.0)))

    if konfig.get("schluesselbegriffe_aus_themenpool", True):
        hoechstens = int(konfig.get("schluesselbegriffe_hoechstens", 15))
        for begriff in _themenpool_begriffe(root, hoechstens):
            hinzufuegen(begriff, "themenpool", 0.7)

    # Eigene Marke immer dabei: Dafür ist Rang-Verfolgung überhaupt da.
    hinzufuegen(konfig.get("eigene_domaene", ""), "marke", 1.0)

    anfragen.sort(key=lambda e: (-e["prioritaet"], e["anfrage"]))
    limit = int(konfig.get("max_anfragen_pro_lauf", 25))
    return anfragen[:max(1, limit)]


def _themenpool_begriffe(root: Path, hoechstens: int) -> list[str]:
    """Schlüsselbegriffe aus data/topics.yaml – deterministisch ausgewählt.

    Der Pool hat über 200 Einträge; alle abzufragen würde jedes
    Tagesbudget sprengen. Deshalb: stabile Auswahl über das Datum. So
    wandert der Lauf Tag für Tag durch den Pool, ohne zufällig zu sein –
    derselbe Tag liefert dieselbe Auswahl, auch im Nachvollzug.
    """
    if yaml is None:
        return []
    pfad = root / "data" / "topics.yaml"
    try:
        with open(pfad, encoding="utf-8") as fh:
            daten = yaml.safe_load(fh) or {}
    except (OSError, yaml.YAMLError):
        return []
    begriffe: list[str] = []
    for thema in daten.get("topics", []) or []:
        if not isinstance(thema, dict):
            continue
        for begriff in thema.get("keywords", []) or []:
            if str(begriff).strip():
                begriffe.append(str(begriff).strip())
    if not begriffe:
        return []
    begriffe = sorted(set(begriffe), key=str.lower)
    versatz = int(heute().replace("-", "")) % max(1, len(begriffe))
    # FLACH zurückgeben. Die erste Fassung packte den Ausschnitt noch in
    # eine Liste: `[(...)]`. `hinzufuegen()` machte daraus per str() die
    # Python-Darstellung EINER Anfrage – messbar im Cockpit als
    # "['Visa Mastercard ohne Gebühren', 'Vorteile', ...]". Ein Lauf, der
    # 15 Keywords als einen kaputten Suchstring verschickt, verbraucht
    # Budget und misst nichts. Siehe Live-SERP-Prüfung 25.10.2026.
    return (begriffe * 2)[versatz:versatz + hoechstens]


# ====================================================================
#  ZWISCHENSPEICHER
# ====================================================================
def _sicherer_pfad(verzeichnis: Path) -> Path:
    verzeichnis.mkdir(parents=True, exist_ok=True)
    return verzeichnis


def cache_relevante_optionen(konfig: dict) -> dict:
    """Die Optionen, die den Zwischenspeicher-Schlüssel bestimmen.

    Eine einzige Quelle für beide Aufrufer (`suchen` und `lauf`). Solange
    jede Stelle ihren eigenen Ausschnitt zusammenbaut, driftet der
    Schlüssel auseinander – und der Cache trifft nie, ohne dass irgendwo
    ein Fehler stünde. Genau so ist der erste Entwurf durchgefallen.
    """
    return {
        "land": konfig.get("land", "de"),
        "sprache": konfig.get("sprache", "de"),
        "geraet": konfig.get("geraet", "desktop"),
        "max_treffer": int(konfig.get("max_treffer", 10)),
    }


def cache_schluessel(anfrage: str, optionen: dict) -> str:
    roh = json.dumps({"q": schlank(anfrage),
                      "land": optionen.get("land"),
                      "sprache": optionen.get("sprache"),
                      "max": optionen.get("max_treffer"),
                      "geraet": optionen.get("geraet")},
                     sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(roh.encode("utf-8")).hexdigest()[:24]


def cache_lesen(anfrage: str, optionen: dict, stunden: float) -> list[dict] | None:
    """Frischer Zwischenspeicher → Treffer, sonst None.

    Ohne diese Schicht kostet jeder Probelauf echtes Abrufbudget. Ein
    Werkzeug, dessen Testlauf das Tageslimit frisst, wird nicht getestet –
    und damit nicht gewartet.
    """
    if stunden <= 0:
        return None
    pfad = CACHE_VERZEICHNIS / f"{cache_schluessel(anfrage, optionen)}.json"
    if not pfad.exists():
        return None
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    try:
        zeitpunkt = datetime.fromisoformat(daten.get("zeitstempel", ""))
    except ValueError:
        return None
    if berlin_now() - zeitpunkt > timedelta(hours=stunden):
        return None
    treffer = daten.get("treffer")
    return treffer if isinstance(treffer, list) else None


def cache_schreiben(anfrage: str, optionen: dict, treffer: list[dict],
                    anbieter: str) -> None:
    pfad = _sicherer_pfad(CACHE_VERZEICHNIS) / f"{cache_schluessel(anfrage, optionen)}.json"
    daten = {"anfrage": anfrage, "anbieter": anbieter,
             "zeitstempel": berlin_now().isoformat(), "treffer": treffer}
    try:
        pfad.write_text(json.dumps(daten, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    except OSError:
        pass


def cache_raeumen() -> int:
    """Abgelaufene Einträge entfernen, damit das Verzeichnis nicht wächst."""
    if not CACHE_VERZEICHNIS.exists():
        return 0
    konfig = lade_konfiguration()
    grenze = timedelta(hours=float(konfig.get("zwischenspeicher_stunden", 18)) * 3)
    geraeumt = 0
    for pfad in CACHE_VERZEICHNIS.glob("*.json"):
        try:
            daten = json.loads(pfad.read_text(encoding="utf-8"))
            zeitpunkt = datetime.fromisoformat(daten.get("zeitstempel", ""))
        except (OSError, json.JSONDecodeError, ValueError):
            geraeumt += 1
            pfad.unlink(missing_ok=True)
            continue
        if berlin_now() - zeitpunkt > grenze:
            pfad.unlink(missing_ok=True)
            geraeumt += 1
    return geraeumt


# ====================================================================
#  QUOTE
# ====================================================================
def quota_laden() -> dict:
    try:
        daten = json.loads(QUOTEN_DATEI.read_text(encoding="utf-8"))
        return daten if isinstance(daten, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def quota_buchen(anbieter: str, anzahl: int = 1, quota: dict | None = None,
                 speichern: bool = True) -> dict:
    """Abrufe zählen. Tageswechsel setzt den Zähler zurück."""
    daten = quota if quota is not None else quota_laden()
    tag = daten.setdefault(heute(), {})
    tag[anbieter] = int(tag.get(anbieter, 0)) + max(0, anzahl)
    # Nur die letzten sieben Tage behalten; älteres ist Ballast.
    if len(daten) > 7:
        for alter in sorted(daten)[:-7]:
            daten.pop(alter, None)
    if speichern:
        _sicherer_pfad(ZUSTAND)
        QUOTEN_DATEI.write_text(json.dumps(daten, ensure_ascii=False, indent=1),
                                encoding="utf-8")
    return daten


def quota_verbleibend(anbieter: str, konfig: dict, quota: dict | None = None) -> int:
    """Wie viele Abrufe sind heute noch übrig? Minimum aus beiden Grenzen.

    Zwei Grenzen, weil sie unterschiedliches schützen: Das Anbieter-Limit
    schützt die Quelle vor uns, das Gesamtlimit schützt uns vor einem
    Amoklauf der eigenen Automatik.

    Ein unterschrittenes Budget ergibt 0, nicht „unendlich": Wer ein
    negatives Restbudget wegfiltert statt ihn auf 0 zu klemmen, gibt
    genau dann unbegrenzt frei, wenn das Budget bereits gerissen ist.
    """
    daten = quota if quota is not None else quota_laden()
    tag = daten.get(heute(), {}) or {}
    verbraucht = int(tag.get(anbieter, 0))
    anbieter_limit = int(sa.ANBIETER.get(anbieter, {}).get("tageslimit", 0) or 0)
    gesamt = int(konfig.get("max_abfragen_pro_tag", 120))
    gesamt_verbraucht = sum(int(v) for v in tag.values())

    rest_gesamt = gesamt - gesamt_verbraucht
    rest_anbieter = (anbieter_limit - verbraucht) if anbieter_limit > 0 \
        else float("inf")
    return max(0, int(min(rest_anbieter, rest_gesamt)))


# ====================================================================
#  INSTANZEN-GESUNDHEIT
# ====================================================================
def instanzen_laden() -> dict:
    try:
        daten = json.loads(INSTANZEN_DATEI.read_text(encoding="utf-8"))
        return daten if isinstance(daten, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def instanzen_sortieren(instanzen: list, zustand: dict | None = None) -> list:
    """Instanzen nach gemessener Zuverlässigkeit, dann nach Antwortzeit.

    Ungemessene Instanzen bekommen eine Erfolgsquote von 0,5 – sie
    sortieren sich damit **zwischen** bewährte und ausgefallene. Nicht
    nach vorn: Wer neunmal geliefert hat, verdient mehr Vertrauen als ein
    Unbekannter. Aber auch nicht nach hinten: Sonst friert die Reihenfolge
    den ersten Messfehler ein und eine neue Instanz käme nie zum Zug.
    """
    zustand = zustand if zustand is not None else instanzen_laden()

    def guete(instanz: str):
        eintrag = zustand.get(str(instanz), {})
        erfolge = int(eintrag.get("erfolge", 0))
        fehler = int(eintrag.get("fehler", 0))
        gesamt = erfolge + fehler
        quote = (erfolge / gesamt) if gesamt else 0.5
        dauer = float(eintrag.get("letzte_dauer_ms", 0) or 0)
        return (-quote, dauer if gesamt else 0.0, str(instanz))

    return sorted({str(i).rstrip("/") for i in instanzen}, key=guete)


def instanz_merken(instanz: str, erfolg: bool, dauer_ms: float = 0.0,
                   fehler: str = "") -> None:
    zustand = instanzen_laden()
    schl = str(instanz).rstrip("/")
    eintrag = zustand.setdefault(schl, {"erfolge": 0, "fehler": 0})
    if erfolg:
        eintrag["erfolge"] = int(eintrag.get("erfolge", 0)) + 1
        eintrag["letzte_antwort"] = berlin_now().isoformat()
        eintrag["letzter_fehler"] = ""
    else:
        eintrag["fehler"] = int(eintrag.get("fehler", 0)) + 1
        eintrag["letzter_fehler"] = str(fehler)[:200]
    if dauer_ms:
        eintrag["letzte_dauer_ms"] = round(float(dauer_ms), 1)
    _sicherer_pfad(ZUSTAND)
    INSTANZEN_DATEI.write_text(json.dumps(zustand, ensure_ascii=False, indent=1),
                               encoding="utf-8")


def _instanz_aus_treffern(treffer: list[dict]) -> str:
    for t in treffer:
        for merkmal in t.get("merkmale", []):
            if str(merkmal).startswith("instanz:"):
                return str(merkmal).split("instanz:", 1)[1]
    return ""


# ====================================================================
#  DATENQUALITÄT – organisches Ranking ≠ Wissens-Rückfall
# ====================================================================
def ist_organisch(treffer: dict) -> bool:
    """Kommt dieser Treffer aus einem echten Suchmaschinen-Index?

    Fail-closed: Eine unbekannte Quelle ist KEIN organisches Ranking. Wer
    die Herkunft nicht kennt, darf sie nicht als Position verkaufen.
    """
    quelle = str(treffer.get("quelle") or "")
    return bool(sa.ANBIETER.get(quelle, {}).get("organisch", False))


def organische_treffer(treffer: list[dict]) -> list[dict]:
    """Nur Treffer, hinter denen ein echter Suchindex steht.

    Wikipedia ist im Register als `organisch: false` geführt. Es ist ein
    Wissens-Rückfall, damit ein Lauf nie völlig leer bleibt – aber seine
    „Ränge" sind API-Treffer, keine Suchpositionen. Vor dem Fix vom
    25.10.2026 stammten 60 von 70 Treffern aus diesem Rückfall; das
    Wettbewerbs-Radar wies wikipedia.org als stärksten „Wettbewerber" aus.
    """
    return [t for t in treffer if ist_organisch(t)]


def datenqualitaet(ergebnisse: list[dict]) -> dict:
    """Wie belastbar ist dieser Lauf? Zählt Anfragen, nicht nur Treffer.

    Eine Anfrage, die nur über den Wissens-Rückfall beantwortet wurde,
    liefert NULL verwertbare Ranking-Daten. Das im Cockpit auszuweisen
    ist wichtiger als eine schöne Gesamttrefferzahl.
    """
    anbieter: dict[str, int] = {}
    organische_anfragen = 0
    treffer_gesamt = 0
    treffer_organisch = 0
    for ergebnis in ergebnisse:
        treffer = ergebnis.get("treffer") or []
        organisch = organische_treffer(treffer)
        treffer_gesamt += len(treffer)
        treffer_organisch += len(organisch)
        if organisch:
            organische_anfragen += 1
        quelle = str((treffer[0].get("quelle") if treffer else "")
                     or ergebnis.get("quelle") or "unbekannt")
        anbieter[quelle] = anbieter.get(quelle, 0) + 1
    erfolgreich = len(ergebnisse)
    anteil = round(1 - (treffer_organisch / treffer_gesamt), 3) if treffer_gesamt else 0.0
    if not erfolgreich or not organische_anfragen:
        aussagekraft = "keine"
    elif organische_anfragen < erfolgreich:
        aussagekraft = "eingeschraenkt"
    else:
        aussagekraft = "voll"
    return {
        "anfragen_erfolgreich": erfolgreich,
        "anfragen_organisch": organische_anfragen,
        "anfragen_rueckfall": erfolgreich - organische_anfragen,
        "treffer_gesamt": treffer_gesamt,
        "treffer_organisch": treffer_organisch,
        "treffer_rueckfall": treffer_gesamt - treffer_organisch,
        "rueckfall_anteil": anteil,
        "anbieter": dict(sorted(anbieter.items(), key=lambda x: -x[1])),
        "aussagekraft": aussagekraft,
    }


# ====================================================================
#  SUCHLAUF
# ====================================================================
def suchen(anfrage: str, konfig: dict, trocken: bool = False,
           ohne_cache: bool = False) -> dict:
    """Eine Anfrage abarbeiten – mit Cache, Quote und Instanzensteuerung.

    Rückgabe ist immer ein Wörterbuch mit `treffer`, `quelle`, `status`.
    Ein Fehler wird darin vermerkt und nicht geworfen: Eine einzelne
    unerreichbare Quelle darf den Lauf nicht beenden.
    """
    optionen = {
        **cache_relevante_optionen(konfig),
        "entdoppeln": bool(konfig.get("entdoppeln", True)),
        "reihenfolge": konfig.get("reihenfolge") or sa.STANDARD_REIHENFOLGE,
        "searxng_instanzen": instanzen_sortieren(
            konfig.get("searxng_instanzen") or sa.STANDARD_SEARXNG_INSTANZEN),
    }
    stunden = 0 if ohne_cache else float(konfig.get("zwischenspeicher_stunden", 18))

    if not trocken:
        frisch = cache_lesen(anfrage, optionen, stunden)
        if frisch is not None:
            return {"anfrage": anfrage, "treffer": frisch, "quelle": "cache",
                    "status": "cache", "dauer_ms": 0}

    start = time.perf_counter()
    try:
        treffer = sa.hole_treffer(anfrage, optionen)
    except sa.AnfrageFehler as fehler:
        return {"anfrage": anfrage, "treffer": [], "quelle": "",
                "status": "fehler", "fehler": str(fehler)[:500],
                "dauer_ms": round((time.perf_counter() - start) * 1000, 1)}

    dauer_ms = round((time.perf_counter() - start) * 1000, 1)
    quelle = treffer[0]["quelle"] if treffer else ""
    instanz = _instanz_aus_treffern(treffer)
    if instanz:
        instanz_merken(instanz, True, dauer_ms)

    if not trocken:
        quota_buchen(quelle or "unbekannt", 1)
        cache_schreiben(anfrage, optionen, treffer, quelle)

    return {"anfrage": anfrage, "treffer": treffer, "quelle": quelle,
            "status": "ok", "dauer_ms": dauer_ms}


def lauf(konfig: dict | None = None, anfragen: list | None = None,
         trocken: bool = False, ohne_cache: bool = False) -> dict:
    """Alle Anfragen abarbeiten und die drei Auswertungsschichten bauen."""
    konfig = konfig if konfig is not None else lade_konfiguration()
    auftraege = anfragen if anfragen is not None else ermittle_anfragen(konfig)
    quota = quota_laden()

    ergebnisse: list[dict] = []
    fehler: list[dict] = []
    zaehlung = {"ok": 0, "cache": 0, "fehler": 0, "uebersprungen": 0}

    for auftrag in auftraege:
        anfrage = auftrag["anfrage"] if isinstance(auftrag, dict) else str(auftrag)
        reihenfolge = konfig.get("reihenfolge") or sa.STANDARD_REIHENFOLGE
        # Vor dem Abruf die Quote prüfen: Nachher ist das Budget schon weg.
        if not trocken and not ohne_cache and cache_lesen(
                anfrage, cache_relevante_optionen(konfig),
                float(konfig.get("zwischenspeicher_stunden", 18))) is None:
            frei = max(quota_verbleibend(a, konfig, quota) for a in reihenfolge
                       if a in sa.ANBIETER) if reihenfolge else 0
            if frei <= 0:
                zaehlung["uebersprungen"] += 1
                fehler.append({"anfrage": anfrage,
                               "fehler": "Tagesbudget ausgeschöpft"})
                continue
        ergebnis = suchen(anfrage, konfig, trocken=trocken, ohne_cache=ohne_cache)
        if ergebnis["status"] == "fehler":
            zaehlung["fehler"] += 1
            fehler.append({"anfrage": anfrage, "fehler": ergebnis.get("fehler", "")})
            continue
        zaehlung[ergebnis["status"]] = zaehlung.get(ergebnis["status"], 0) + 1
        ergebnisse.append(ergebnis)
        if not trocken:
            quota = quota_laden()

    alle_treffer = [t for e in ergebnisse for t in e["treffer"]]
    # Rang und Wettbewerb sind RANGSYSTEME. Ein Wissens-Rückfall (Wikipedia)
    # darf in beide nicht einfließen – er hat keine Suchposition. Gemessen
    # wird er trotzdem: `datenqualitaet` weist ihn offen aus.
    verwertbar = organische_treffer(alle_treffer)
    befund = {
        "zeitstempel": berlin_now().isoformat(),
        "eigene_domaene": konfig.get("eigene_domaene", ""),
        "anfragen_geplant": len(auftraege),
        "zaehlung": zaehlung,
        "treffer_gesamt": len(alle_treffer),
        "treffer_organisch": len(verwertbar),
        "datenqualitaet": datenqualitaet(ergebnisse),
        "ergebnisse": ergebnisse,
        "fehler": fehler,
        "rang": rang_verfolgung(ergebnisse, konfig.get("eigene_domaene", "")),
        "wettbewerb": wettbewerbs_radar(verwertbar),
    }
    if not trocken:
        befund["quota"] = quota_laden().get(heute(), {})
        _ablegen(befund)
    return befund


def _ablegen(befund: dict) -> None:
    """Ergebnisse schreiben. Jeder Pfad einzeln abgesichert.

    Ein Schreibfehler am Bericht darf nicht die Rang-Historie verlieren –
    und umgekehrt. Deshalb keine gemeinsame Transaktion.
    """
    _sicherer_pfad(ZUSTAND)
    ERGEBNIS_DATEI.write_text(
        json.dumps({k: v for k, v in befund.items() if k != "ergebnisse"},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    with open(VERLAUF_DATEI, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "zeitstempel": befund["zeitstempel"],
            "anfragen": befund["anfragen_geplant"],
            "zaehlung": befund["zaehlung"],
            "treffer": befund["treffer_gesamt"],
            "sichtbar": len([r for r in befund["rang"] if r.get("eigener_rang")]),
        }, ensure_ascii=False) + "\n")
    RANKING_DATEI.write_text(json.dumps(
        {"stand": befund["zeitstempel"], "rankings": befund["rang"]},
        ensure_ascii=False, indent=1), encoding="utf-8")
    with open(RANKING_VERLAUF, "a", encoding="utf-8") as fh:
        for eintrag in befund["rang"]:
            fh.write(json.dumps({"zeitstempel": befund["zeitstempel"], **eintrag},
                                ensure_ascii=False) + "\n")
    WETTBEWERB_DATEI.write_text(json.dumps(
        {"stand": befund["zeitstempel"], **befund["wettbewerb"]},
        ensure_ascii=False, indent=1), encoding="utf-8")


# ====================================================================
#  AUSWERTUNG 1: RANG-VERFOLGUNG
# ====================================================================
def rang_verfolgung(ergebnisse: list[dict], eigene_domaene: str) -> list[dict]:
    """Wo steht die eigene Domaene – und wie hat sich das bewegt?

    Die Veränderung wird gegen den letzten Rang **derselben Anfrage** aus
    der Historie gerechnet, nicht gegen den letzten Lauf pauschal. Sonst
    erscheint jede Anfrage, die gestern nicht dabei war, als Absturz.
    """
    eigene = str(eigene_domaene or "").lower().strip()
    vorher = _letzte_raenge()
    rangliste = []
    for ergebnis in ergebnisse:
        anfrage = ergebnis["anfrage"]
        eigener_rang = 0
        eigener_titel = ""
        eigene_url = ""
        for treffer in organische_treffer(ergebnis["treffer"]):
            if eigene and eigene in (treffer.get("domaene") or ""):
                eigener_rang = treffer["rang"]
                eigener_titel = treffer.get("titel", "")
                eigene_url = treffer.get("url", "")
                break
        alt = vorher.get(schlank(anfrage), {}).get("rang", 0)
        if eigener_rang and alt:
            delta = alt - eigener_rang
        elif eigener_rang and not alt:
            delta = 0
        else:
            delta = 0
        rangliste.append({
            "anfrage": anfrage,
            "eigener_rang": eigener_rang,
            "vorher": alt,
            "delta": delta,
            "titel": eigener_titel,
            "url": eigene_url,
            "quelle": ergebnis.get("quelle", ""),
            "sichtbar": bool(eigener_rang),
        })
    rangliste.sort(key=lambda e: (not e["sichtbar"], e["eigener_rang"] or 999,
                                  e["anfrage"]))
    return rangliste


def _letzte_raenge() -> dict:
    """Letzter bekannter Rang je Anfrage aus der Historie."""
    if not RANKING_VERLAUF.exists():
        return {}
    letzte: dict[str, dict] = {}
    try:
        for zeile in RANKING_VERLAUF.read_text(encoding="utf-8").splitlines():
            if not zeile.strip():
                continue
            try:
                eintrag = json.loads(zeile)
            except json.JSONDecodeError:
                continue
            schluessel = schlank(eintrag.get("anfrage", ""))
            if not schluessel:
                continue
            zeit = eintrag.get("zeitstempel", "")
            bisher = letzte.get(schluessel)
            if bisher is None or zeit >= bisher.get("zeitstempel", ""):
                letzte[schluessel] = {"rang": int(eintrag.get("eigener_rang") or 0),
                                      "zeitstempel": zeit}
    except OSError:
        return {}
    return letzte


# ====================================================================
#  AUSWERTUNG 2: WETTBEWERBS-RADAR
# ====================================================================
def wettbewerbs_radar(treffer: list[dict], spitze: int = 15) -> dict:
    """Welche Domänen besetzen die Ergebnisseiten der eigenen Themenwelt?

    `durchschnitts_rang` zählt mehr als die bloße Häufigkeit: Eine Seite,
    die achtmal auf Rang 9 steht, ist schwächer als eine, die dreimal auf
    Rang 1 steht. Beides wird deshalb getrennt ausgewiesen.
    """
    zaehlung: dict[str, dict] = {}
    for treffer_eintrag in treffer:
        domaene = treffer_eintrag.get("domaene") or ""
        if not domaene:
            continue
        eintrag = zaehlung.setdefault(domaene, {"treffer": 0, "rang_summe": 0,
                                                "top3": 0, "beste": 99,
                                                "anfragen": []})
        rang = int(treffer_eintrag.get("rang") or 0)
        eintrag["treffer"] += 1
        eintrag["rang_summe"] += rang
        eintrag["beste"] = min(eintrag["beste"], rang)
        if rang <= 3:
            eintrag["top3"] += 1
        if treffer_eintrag.get("anfrage") not in eintrag["anfragen"]:
            eintrag["anfragen"].append(treffer_eintrag.get("anfrage"))
    liste = []
    for domaene, daten in zaehlung.items():
        liste.append({
            "domaene": domaene,
            "treffer": daten["treffer"],
            "top3": daten["top3"],
            "bester_rang": daten["beste"] if daten["beste"] < 99 else 0,
            "durchschnitts_rang": round(daten["rang_summe"] / max(1, daten["treffer"]), 2),
            "anfragen": daten["anfragen"][:6],
        })
    liste.sort(key=lambda e: (-e["treffer"], e["durchschnitts_rang"], e["domaene"]))
    merkmale: dict[str, int] = {}
    for treffer_eintrag in treffer:
        for merkmal in treffer_eintrag.get("merkmale", []):
            if str(merkmal).startswith(("instanz:", "engine:")):
                continue
            merkmale[str(merkmal)] = merkmale.get(str(merkmal), 0) + 1
    return {"domaenen": liste[:spitze], "domaenen_gesamt": len(liste),
            "merkmale": dict(sorted(merkmale.items(), key=lambda x: -x[1])[:12])}


# ====================================================================
#  BERICHT
# ====================================================================
def bericht(befund: dict, konfig: dict | None = None) -> str:
    """Menschenlesbares Cockpit. Wird als SUCHRADAR-RADAR.md abgelegt."""
    konfig = konfig if konfig is not None else lade_konfiguration()
    jetzt = befund.get("zeitstempel", berlin_now().isoformat())
    z = befund.get("zaehlung", {})
    rang = befund.get("rang", [])
    sichtbar = [r for r in rang if r.get("sichtbar")]
    wb = befund.get("wettbewerb", {})

    zeilen = [
        "# SUCHRADAR – Status",
        "",
        f"> Stand: {jetzt[:19].replace('T', ' ')} Uhr · "
        f"Anbieter: {', '.join(konfig.get('reihenfolge') or sa.STANDARD_REIHENFOLGE)}",
        "> Schlüssellos · 0 € · Anleitung: `docs/ANLEITUNG-SUCHRADAR.md`",
        "",
        "## Lauf",
        "",
        "| Kennzahl | Wert |",
        "|---|---|",
        f"| Anfragen geplant | {befund.get('anfragen_geplant', 0)} |",
        f"| Erfolgreich | {z.get('ok', 0)} |",
        f"| Aus dem Zwischenspeicher | {z.get('cache', 0)} |",
        f"| Fehlgeschlagen | {z.get('fehler', 0)} |",
        f"| Übersprungen (Budget) | {z.get('uebersprungen', 0)} |",
        f"| Treffer gesamt | {befund.get('treffer_gesamt', 0)} |",
        f"| Davon organisch | {befund.get('treffer_organisch', befund.get('treffer_gesamt', 0))} |",
        f"| Eigene Treffer | {len(sichtbar)} von {len(rang)} Anfragen |",
        "",
    ]

    dq = befund.get("datenqualitaet")
    if dq:
        zeilen += [
            "## Datenqualität",
            "",
            "| Kennzahl | Wert |",
            "|---|---|",
            f"| Anfragen mit echtem Suchindex | {dq.get('anfragen_organisch', 0)} "
            f"von {dq.get('anfragen_erfolgreich', 0)} |",
            f"| Anfragen nur mit Wissens-Rückfall | {dq.get('anfragen_rueckfall', 0)} |",
            f"| Organische Treffer | {dq.get('treffer_organisch', 0)} "
            f"von {dq.get('treffer_gesamt', 0)} |",
            f"| Rückfall-Anteil | {round(float(dq.get('rueckfall_anteil', 0)) * 100)} % |",
            f"| Aussagekraft | {dq.get('aussagekraft', '–')} |",
            "",
            "_Nur organische Treffer gehen in Rang und Wettbewerb ein. Der "
            "Wikipedia-Rückfall verhindert leere Läufe, ist aber kein Ranking._",
            "",
        ]

    quota = befund.get("quota") or quota_laden().get(heute(), {})
    if quota:
        zeilen += ["## Abrufbudget heute", "",
                   "| Anbieter | Abrufe | Limit |", "|---|---|---|"]
        for anbieter, anzahl in sorted(quota.items()):
            limit = sa.ANBIETER.get(anbieter, {}).get("tageslimit", "–")
            zeilen.append(f"| {anbieter} | {anzahl} | {limit} |")
        zeilen.append("")

    zeilen += ["## Eigene Sichtbarkeit", ""]
    if sichtbar:
        zeilen += ["| Suchbegriff | Rang | Vorher | Δ | Quelle |",
                   "|---|---|---|---|---|"]
        for eintrag in sichtbar[:25]:
            delta = eintrag.get("delta", 0)
            pfeil = "▲" if delta > 0 else ("▼" if delta < 0 else "·")
            zeilen.append(
                f"| {eintrag['anfrage']} | {eintrag['eigener_rang']} "
                f"| {eintrag.get('vorher') or '–'} | {pfeil} {abs(delta)} "
                f"| {eintrag.get('quelle', '–')} |")
    else:
        zeilen.append("_Kein eigener Treffer in den gemessenen Anfragen._")
    zeilen.append("")

    zeilen += ["## Wettbewerb", ""]
    if wb.get("domaenen"):
        zeilen += ["| Domäne | Treffer | Top 3 | Ø Rang | Bester Rang |",
                   "|---|---|---|---|---|"]
        for eintrag in wb["domaenen"][:12]:
            zeilen.append(
                f"| {eintrag['domaene']} | {eintrag['treffer']} "
                f"| {eintrag['top3']} | {eintrag['durchschnitts_rang']} "
                f"| {eintrag['bester_rang']} |")
    else:
        zeilen.append("_Keine Treffer ausgewertet._")
    zeilen.append("")

    if wb.get("merkmale"):
        zeilen += ["## Sonderflächen auf den Ergebnisseiten", ""]
        zeilen += ["| Merkmal | Vorkommen |", "|---|---|"]
        for merkmal, anzahl in wb["merkmale"].items():
            zeilen.append(f"| {merkmal} | {anzahl} |")
        zeilen.append("")

    if befund.get("fehler"):
        zeilen += ["## Störungen", "",
                   "| Suchbegriff | Meldung |", "|---|---|"]
        for eintrag in befund["fehler"][:15]:
            meldung = str(eintrag.get("fehler", "")).replace("|", "/")[:180]
            zeilen.append(f"| {eintrag.get('anfrage', '')} | {meldung} |")
        zeilen.append("")

    zeilen += [
        "## Einordnung",
        "",
        "Ohne API-Schlüssel gibt es kein Google-Original-Ranking: SearXNG",
        "bündelt den Google-Index über fremde Instanzen, DuckDuckGo und",
        "Mojeek sind eigene Indizes. Die Ränge sind Indikationen, keine",
        "Positionsgarantie. Für die exakte Position ist die Google Search",
        "Console die richtige Quelle – ebenfalls kostenlos. Ergänzend liegt",
        "ein **einmalig live geprüfter Google-SERP-Snapshot** unter",
        "`data/serp/` (siehe `SERP-LIVE-PRUEFUNG-HIGHEND-2026-10-25.md`);",
        "die Wache `scripts/serp_live_wache.py` hält ihn und die eigenen",
        "Snippets dauerhaft im Blick. Automatisiertes google.com-Scraping",
        "bleibt aus Vertrags- und Datenqualitätsgründen tabu.",
        "",
        "Kein Treffer aus diesem Bericht wird ungeprüft in einen Artikel",
        "übernommen. Das Radar misst; die Entscheidung trifft Frank.",
        "",
    ]
    return "\n".join(zeilen)


def bericht_schreiben(befund: dict, konfig: dict | None = None) -> Path:
    text = bericht(befund, konfig)
    COCKPIT.write_text(text, encoding="utf-8")
    return COCKPIT


# ====================================================================
#  PROBE: Erreichbarkeit messen
# ====================================================================
def probe(konfig: dict | None = None, anfrage: str = "stromkosten senken") -> dict:
    """Jeden schlüssellosen Anbieter einzeln antesten.

    Getrennt von der Kette, weil die Kette sonst den Fehler versteckt:
    Liefert SearXNG, fällt der DuckDuckGo-Ausfall nicht auf – bis
    SearXNG selbst ausfällt und nichts mehr da ist.
    """
    konfig = konfig if konfig is not None else lade_konfiguration()
    befunde = []
    for anbieter_id in sa.ANBIETER:
        meta = sa.ANBIETER[anbieter_id]
        eintrag = {"anbieter": anbieter_id, "name": meta["name"],
                   "schluessellos": bool(meta.get("schluessellos"))}
        erlaubt, grund = sa.pruefe_freigabe(anbieter_id)
        eintrag["freigegeben"] = erlaubt
        eintrag["grund"] = grund
        if not erlaubt:
            eintrag["status"] = "gesperrt"
            befunde.append(eintrag)
            continue
        if not meta.get("schluessellos") and not sa.schluessel_vorhanden(anbieter_id):
            eintrag["status"] = "kein_schluessel"
            befunde.append(eintrag)
            continue
        start = time.perf_counter()
        try:
            treffer = sa.AUSFUEHRER[anbieter_id](anfrage, {
                "land": konfig.get("land", "de"),
                "sprache": konfig.get("sprache", "de"),
                "max_treffer": 5,
                "searxng_instanzen": konfig.get("searxng_instanzen")
                or sa.STANDARD_SEARXNG_INSTANZEN,
            })
            eintrag["status"] = "ok" if treffer else "leer"
            eintrag["treffer"] = len(treffer)
            eintrag["beispiel"] = treffer[0]["url"] if treffer else ""
        except Exception as fehler:                       # noqa: BLE001
            eintrag["status"] = "fehler"
            eintrag["fehler"] = str(fehler)[:220]
        eintrag["dauer_ms"] = round((time.perf_counter() - start) * 1000, 1)
        if anbieter_id == "searxng":
            instanz = _instanz_aus_treffern(
                sa.entdoppeln(treffer)) if eintrag["status"] == "ok" else ""
            if instanz:
                instanz_merken(instanz, eintrag["status"] == "ok",
                               eintrag["dauer_ms"])
        befunde.append(eintrag)
    return {"anfrage": anfrage, "zeitstempel": berlin_now().isoformat(),
            "anbieter": befunde}


# ====================================================================
#  SELBSTTEST (offline – kein Netz, keine Modellabhängigkeit)
# ====================================================================
def selbsttest() -> int:
    """Fail-closed-Prüfungen. Deckt Sabotage ab, nicht nur den Glücksfall."""
    problem: list[str] = []

    def pruefe(bedingung, meldung):
        if not bedingung:
            problem.append(meldung)

    konfig = dict(VORGABEN)

    # 1) Anfragenermittlung ist deterministisch und entdoppelt
    a1 = ermittle_anfragen({**konfig, "anfragen": ["Stromkosten senken",
                                                  "stromkosten  senken!",
                                                  "Notgroschen aufbauen"]})
    a2 = ermittle_anfragen({**konfig, "anfragen": ["Stromkosten senken",
                                                  "stromkosten  senken!",
                                                  "Notgroschen aufbauen"]})
    pruefe(a1 == a2, "Anfragenermittlung ist nicht deterministisch")
    begriffe = [e["anfrage"] for e in a1]
    pruefe(len(begriffe) == len(set(schlank(b) for b in begriffe)),
           "Anfragenermittlung lässt Duplikate durch")
    pool = _themenpool_begriffe(ROOT, 5)
    pruefe(len(pool) > 1 and all(isinstance(b, str) and not b.startswith("[")
                                 for b in pool),
           "Themenpool liefert keine flachen Suchbegriffe (Listen-Repr gelandet)")

    # 2) Budget-Limit greift
    begrenzt = ermittle_anfragen({**konfig, "max_anfragen_pro_lauf": 3,
                                  "anfragen": [f"begriff {i}" for i in range(30)]})
    pruefe(len(begrenzt) <= 3, f"Anfragenlimit ignoriert: {len(begrenzt)}")

    # 3) Marke ist immer dabei
    pruefe(any(konfig["eigene_domaene"] in e["anfrage"] for e in a1),
           "Eigene Marke fehlt in den Anfragen")

    # 4) Quote: Tageslimit wird hart unterschritten
    quota = {heute(): {"searxng": 10 ** 6}}
    pruefe(quota_verbleibend("searxng", konfig, quota) == 0,
           "Quoten-Zähler lässt ein überschrittenes Anbieterlimit durch")
    quota2 = {heute(): {"searxng": 1, "mojeek": 10 ** 6}}
    pruefe(quota_verbleibend("duckduckgo", {**konfig, "max_abfragen_pro_tag": 2},
                             quota2) == 0,
           "Gesamtbudget wird nicht durchgesetzt")
    pruefe(quota_verbleibend("duckduckgo", konfig, {}) > 0,
           "Quoten-Zähler blockiert einen frischen Tag")

    # 5) Zwischenspeicher: Alter Eintrag zählt nicht mehr
    alt = {"zeitstempel": (berlin_now() - timedelta(hours=99)).isoformat(),
           "treffer": [{"url": "https://alt.de", "rang": 1}]}
    frisch = {"zeitstempel": berlin_now().isoformat(),
              "treffer": [{"url": "https://neu.de", "rang": 1}]}
    pruefe(cache_lesen("x", {"land": "de"}, 18) is None
           or isinstance(cache_lesen("x", {"land": "de"}, 18), list),
           "cache_lesen liefert etwas Unerwartetes")
    pruefe(_ist_abgelaufen(alt, 18), "Abgelaufener Cache-Eintrag gilt als frisch")
    pruefe(not _ist_abgelaufen(frisch, 18), "Frischer Cache-Eintrag gilt als alt")

    # 6) Instanzen-Reihenfolge: bewährte zuerst, Ausfälle zuletzt.
    #    Ungemessene liegen DAZWISCHEN – nicht vorn. Eine Instanz mit
    #    neun Erfolgen hat mehr Vertrauen verdient als eine unbekannte;
    #    hinter einem bekannten Ausfall darf sie aber nie stehen.
    zustand = {"https://tot.example": {"erfolge": 0, "fehler": 9, "letzte_dauer_ms": 5},
               "https://gut.example": {"erfolge": 9, "fehler": 0, "letzte_dauer_ms": 900}}
    reihe = instanzen_sortieren(["https://tot.example", "https://neu.example",
                                 "https://gut.example"], zustand)
    pruefe(reihe[0] == "https://gut.example",
           f"Bewährte Instanz steht nicht vorn: {reihe}")
    pruefe(reihe.index("https://neu.example") < reihe.index("https://tot.example"),
           f"Ungemessene Instanz steht hinter dem bekannten Ausfall: {reihe}")
    pruefe(reihe[-1] == "https://tot.example",
           f"Ausgefallene Instanz steht nicht hinten: {reihe}")

    # 7) Rang-Verfolgung findet die eigene Domaene und rechnet das Delta
    ergebnisse = [{"anfrage": "Stromkosten senken", "quelle": "searxng",
                   "treffer": [{"domaene": "verivox.de", "rang": 1, "titel": "V",
                                "quelle": "searxng"},
                               {"domaene": "franksfinanzcheck.de", "rang": 2,
                                "titel": "F", "url": "https://franksfinanzcheck.de/x",
                                "quelle": "searxng"},
                               {"domaene": "check24.de", "rang": 3, "titel": "C",
                                "quelle": "searxng"}]}]
    rang = rang_verfolgung(ergebnisse, "franksfinanzcheck.de")
    pruefe(rang[0]["eigener_rang"] == 2, "Eigener Rang nicht erkannt")
    pruefe(rang[0]["sichtbar"] is True, "Sichtbarkeitskennzeichen fehlt")

    # 8) Ohne eigenen Treffer: sichtbar=false, kein Phantom-Rang.
    #    Zusätzlich: Ein Wissens-Rückfall darf keinen Rang erfinden.
    fremd = [{"anfrage": "irgendwas", "quelle": "mojeek",
              "treffer": [{"domaene": "andere.de", "rang": 1, "titel": "A",
                           "quelle": "mojeek"}]}]
    pruefe(rang_verfolgung(fremd, "franksfinanzcheck.de")[0]["sichtbar"] is False,
           "Fremder Treffer zählt als eigener")
    rueckfall = [{"anfrage": "irgendwas", "quelle": "wikipedia",
                  "treffer": [{"domaene": "franksfinanzcheck.de", "rang": 1,
                               "titel": "F", "quelle": "wikipedia"},
                              {"domaene": "de.wikipedia.org", "rang": 2,
                               "titel": "W", "quelle": "wikipedia"}]}]
    pruefe(rang_verfolgung(rueckfall, "franksfinanzcheck.de")[0]["eigener_rang"] == 0,
           "Wissens-Rückfall wird als echter Rang gezählt")
    dq = datenqualitaet([*ergebnisse, *rueckfall])
    pruefe(dq["anfragen_organisch"] == 1 and dq["anfragen_rueckfall"] == 1,
           "Datenqualität zählt Rückfall-Anfragen falsch")
    pruefe(dq["aussagekraft"] == "eingeschraenkt",
           "Datenqualität bewertet einen halben Rückfall-Lauf falsch")
    pruefe("de.wikipedia.org" not in
           {e["domaene"] for e in wettbewerbs_radar(
               organische_treffer(rueckfall[0]["treffer"]))["domaenen"]},
           "Wikipedia-Rückfall landet im Wettbewerbs-Radar")

    # 9) Wettbewerbs-Radar: Häufigkeit UND Rangtiefe getrennt
    treffer = [
        {"domaene": "a.de", "rang": 9, "anfrage": "q1", "merkmale": []},
        {"domaene": "a.de", "rang": 9, "anfrage": "q2", "merkmale": []},
        {"domaene": "b.de", "rang": 1, "anfrage": "q1", "merkmale": ["sitelinks"]},
    ]
    wb = wettbewerbs_radar(treffer)
    praef = {e["domaene"]: e for e in wb["domaenen"]}
    pruefe(praef["a.de"]["treffer"] == 2, "Wettbewerbs-Zählung falsch")
    pruefe(praef["a.de"]["durchschnitts_rang"] == 9.0, "Ø-Rang falsch gerechnet")
    pruefe(praef["b.de"]["top3"] == 1, "Top-3-Zählung falsch")
    pruefe(wb["merkmale"].get("sitelinks") == 1, "Merkmale nicht gezählt")

    # 10) Interne Technik-Kennzeichen gehören nicht in die Merkmalsliste
    intern = wettbewerbs_radar([{"domaene": "a.de", "rang": 1, "anfrage": "q",
                                 "merkmale": ["instanz:https://x", "engine:google",
                                              "faq"]}])
    pruefe("instanz:https://x" not in intern["merkmale"]
           and "engine:google" not in intern["merkmale"],
           "Interne Technik-Kennzeichen landen im Bericht")

    # 11) Parser-Vertrag an echten HTML-Proben
    proben = ROOT / "scripts" / "tests" / "serp_proben"
    ddg = sa.parse_duckduckgo("stromkosten senken",
                              (proben / "duckduckgo.html").read_text(encoding="utf-8"))
    pruefe(len(ddg) == 3, f"DuckDuckGo-Probe: {len(ddg)} statt 3 Treffer (Anzeige?)")
    pruefe(all(not ist_host_oder_subdomain(t["url"], "duckduckgo.com") for t in ddg),
           "DuckDuckGo-Umleitungen nicht ausgepackt")
    pruefe(any(t["domaene"] == "franksfinanzcheck.de" for t in ddg),
           "Eigene Domaene in der DuckDuckGo-Probe nicht gefunden")
    sx = sa.parse_searxng("stromkosten senken",
                          (proben / "searxng.html").read_text(encoding="utf-8"))
    pruefe(len(sx) == 3, f"SearXNG-Probe: {len(sx)} statt 3 Treffer (Anzeige?)")
    pruefe(all(t["titel"] and t["titel"] != t["anzeigedomaene"] for t in sx),
           "SearXNG-Probe: Titel ist die Adresse (Selektor-Reihenfolge)")

    # 12) Bericht enthält die Kernzahlen und keine internen Pfade
    text = bericht({"zeitstempel": berlin_now().isoformat(), "zaehlung": {"ok": 1},
                    "anfragen_geplant": 1, "treffer_gesamt": 3,
                    "treffer_organisch": 3, "datenqualitaet": dq, "rang": rang,
                    "wettbewerb": wb, "fehler": []}, konfig)
    for pflicht in ("SUCHRADAR", "Datenqualität", "Eigene Sichtbarkeit",
                    "Wettbewerb", "Einordnung"):
        pruefe(pflicht in text, f"Bericht: Abschnitt „{pflicht}“ fehlt")
    pruefe("data/suchradar/" not in text, "Bericht leakt interne Pfade")

    # 13) Kostensperre wirkt: bezahlter Anbieter bleibt ohne Freigabe raus
    pruefe(not sa.pruefe_freigabe("apify")[0],
           "Apify-Adapter ist ohne Freigabe nutzbar")
    pruefe(not sa.pruefe_freigabe("serpapi")[0],
           "SerpApi-Adapter ist ohne Freigabe nutzbar")

    if problem:
        for zeile in problem:
            print("  ✗ " + zeile, file=sys.stderr)
        return 1
    print("Suchradar-Selbsttest bestanden: 13 Prüfblöcke, offline, ohne Netz.")
    return 0


def _ist_abgelaufen(eintrag: dict, stunden: float) -> bool:
    """Hilfsfunktion für den Selbsttest – dieselbe Regel wie cache_lesen."""
    try:
        zeitpunkt = datetime.fromisoformat(eintrag.get("zeitstempel", ""))
    except ValueError:
        return True
    return berlin_now() - zeitpunkt > timedelta(hours=stunden)


# ====================================================================
#  CLI
# ====================================================================
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Suchradar – Suchergebnis-Erfassung ohne API und ohne Kosten")
    parser.add_argument("--selftest", action="store_true",
                        help="Offline-Selbsttest (13 Prüfblöcke)")
    parser.add_argument("--probe", action="store_true",
                        help="Erreichbarkeit jedes Anbieters einzeln messen")
    parser.add_argument("--status", action="store_true", help="Cockpit ausgeben")
    parser.add_argument("--json", action="store_true", help="Maschinenausgabe")
    parser.add_argument("--dry-run", action="store_true",
                        help="Suchen, aber nichts schreiben")
    parser.add_argument("--ohne-cache", action="store_true",
                        help="Zwischenspeicher übergehen")
    parser.add_argument("--anfrage", action="append", default=[],
                        help="Ad-hoc-Anfrage (wiederholbar)")
    parser.add_argument("--max-anfragen", type=int, default=0,
                        help="Höchstzahl der Anfragen in diesem Lauf")
    parser.add_argument("--kein-bericht", action="store_true",
                        help="SUCHRADAR-RADAR.md nicht überschreiben")
    parser.add_argument("--cache-raeumen", action="store_true",
                        help="Abgelaufene Zwischenspeicher-Einträge löschen")
    argumente = parser.parse_args(argv)

    if argumente.selftest:
        code = selbsttest()
        return code or sa.selbsttest()

    if argumente.cache_raeumen:
        print(f"{cache_raeumen()} abgelaufene Einträge entfernt.")
        return 0

    konfig = lade_konfiguration()
    if konfig.get("_hinweis"):
        print(f"HINWEIS: {konfig['_hinweis']}", file=sys.stderr)

    if argumente.probe:
        befund = probe(konfig)
        if argumente.json:
            print(json.dumps(befund, ensure_ascii=False, indent=1))
        else:
            print(f"Probe „{befund['anfrage']}“ – {befund['zeitstempel'][:19]}\n")
            for eintrag in befund["anbieter"]:
                symbol = {"ok": "✓", "leer": "·", "gesperrt": "⊘",
                          "kein_schluessel": "⊘"}.get(eintrag["status"], "✗")
                zusatz = eintrag.get("fehler") or eintrag.get("grund", "")
                dauer = eintrag.get("dauer_ms")
                dauer_txt = f" ({dauer} ms)" if dauer else ""
                print(f"  {symbol} {eintrag['anbieter']:<12} {eintrag['status']:<14}"
                      f"{dauer_txt} {zusatz[:90]}")
        lebendig = [e for e in befund["anbieter"]
                    if e["status"] in ("ok", "leer") and e["schluessellos"]]
        return 0 if lebendig else 3

    if argumente.status:
        if COCKPIT.exists():
            print(COCKPIT.read_text(encoding="utf-8"))
            return 0
        print("Noch kein Lauf – SUCHRADAR-RADAR.md fehlt.", file=sys.stderr)
        return 1

    anfragen = ([{"anfrage": a, "herkunft": "adhoc", "prioritaet": 1.0}
                 for a in argumente.anfrage]
                or ermittle_anfragen(konfig))
    if argumente.max_anfragen:
        anfragen = anfragen[:argumente.max_anfragen]

    befund = lauf(konfig, anfragen, trocken=argumente.dry_run,
                  ohne_cache=argumente.ohne_cache)

    if not argumente.dry_run and not argumente.kein_bericht:
        bericht_schreiben(befund, konfig)

    if argumente.json:
        ausgabe = {k: v for k, v in befund.items() if k != "ergebnisse"}
        print(json.dumps(ausgabe, ensure_ascii=False, indent=1))
    else:
        z = befund["zaehlung"]
        print(f"Suchradar: {z.get('ok', 0)} frisch, {z.get('cache', 0)} aus dem "
              f"Cache, {z.get('fehler', 0)} Fehler, "
              f"{z.get('uebersprungen', 0)} übersprungen "
              f"({befund['treffer_gesamt']} Treffer)")
        sichtbar = [r for r in befund["rang"] if r.get("sichtbar")]
        print(f"Sichtbarkeit: {len(sichtbar)} von {len(befund['rang'])} Anfragen "
              f"mit eigenem Treffer")
        for eintrag in sichtbar[:10]:
            print(f"  Rang {eintrag['eigener_rang']:>2}  {eintrag['anfrage']}")
        if not argumente.dry_run:
            # Der Cockpit-Pfad kann außerhalb des Repos liegen (Tests,
            # Sandbox). Ein nacktes relative_to() wirft dann – und ein
            # Hinweis, der den erfolgreichen Lauf in einen Absturz
            # verwandelt, ist schlechter als gar keiner.
            try:
                anzeige = COCKPIT.relative_to(ROOT)
            except ValueError:
                anzeige = COCKPIT
            print(f"Cockpit: {anzeige}")

    # Kein Anbieter lieferte etwas → rot. Ein stiller leerer Bericht wäre
    # die teuerste Variante dieses Fehlers.
    if befund["zaehlung"].get("ok", 0) == 0 and befund["zaehlung"].get("cache", 0) == 0:
        print("KEIN EINZIGER TREFFER: Kein Anbieter hat geliefert. "
              "Prüfen: python3 scripts/suchradar.py --probe", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
