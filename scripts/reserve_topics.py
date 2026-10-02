#!/usr/bin/env python3
"""
reserve_topics.py – Themen-Disposition der Content-Reserve (Premium #387)

WARUM DIESE DATEI EXISTIERT (Root-Cause 26.09.2026, Run 36230666076)
--------------------------------------------------------------------
Der nächtliche Reserve-Lauf war rot, weil die Nachproduktion NICHTS mehr
lieferte – und zwar strukturell, nicht zufällig:

  `engine_generate._reserve_topup` wählte sein Thema mit `freie[0]`, also
  IMMER das erste Thema der Datei `data/topics.yaml`, das die alte
  Dublettenprüfung passierte. Diese Prüfung vergleicht Themen-Titel mit
  Artikel-Titeln über eine 60-%-Token-Regel. „Stromfresser im Haushalt
  entlarven" teilt mit „Stromfresser finden: So senkst du deine
  Stromrechnung massiv" aber nur EIN Token – das Thema galt also auf ewig
  als „frei", obwohl der Blog dazu längst sechs Artikel hatte:

      Energiediebe stoppen: So kannst du Stromfresser finden
      Standby Kosten reduzieren: So entlarvst du Stromfresser
      Stromfresser finden: So stoppst du teure Energiediebe
      Stromfresser finden: So stoppst du teure Energiediebe 2026
      Stromfresser finden: So senkst du deine Stromrechnung massiv
      Stromfresser finden: So stoppst du die Energie-Lecks

  Zwei Schäden aus derselben Wurzel:
    1. KANNIBALISIERUNG: Der Vorrat füllte sich mit Varianten desselben
       Themas (vorher dieselbe Kaskade mit „Gasrechnung senken" – fünf
       Varianten, davon vier am selben Tag live, danach wieder auf `draft`
       zurückgestuft). Ein Vorrat aus Dubletten ist kein Vorrat.
    2. STILLSTAND: Irgendwann ist zu einem Thema alles gesagt – die
       KI-Generierung scheitert dann am Profi-Gate bzw. an der
       Titel-Dublette, und zwar JEDE NACHT AUFS NEUE, weil immer dasselbe
       Thema an erster Stelle steht. Am 26.09. lieferten beide
       Produktionsstufen exakt 0 Kandidaten, obwohl 145 Themen frei waren.

Diese Disposition ersetzt `freie[0]` durch eine begründete Reihenfolge:

  AUSSCHLUSS   Themen, zu denen der Bestand (live + Entwürfe + Pool) schon
               einen Artikel mit demselben LEITBEGRIFF hat.
  GEDÄCHTNIS   `data/reserve-topic-ledger.json` merkt sich pro Thema
               Erfolg/Misserfolg und sperrt es befristet (Cooldown). Ein
               Thema, das dreimal scheitert, blockiert nicht mehr die Nacht.
  ROTATION     Nie gewählte Themen zuerst, danach die am längsten nicht
               versuchten – deterministisch, damit ein Lauf reproduzierbar
               bleibt (kein Zufall, keine API-Lotterie).
  MEHRFACH     `disponieren()` liefert eine LISTE. Scheitert ein Thema an
               der KI, nimmt der Aufrufer das nächste, statt die Nacht
               abzubrechen.

MODI:
  python3 scripts/reserve_topics.py --status      # Bericht (Mensch)
  python3 scripts/reserve_topics.py --json        # Maschine
  python3 scripts/reserve_topics.py --klumpen     # Themen-Klumpen im Bestand
  python3 scripts/reserve_topics.py --selftest    # Sabotage-Schutz

EXIT: 0 = ok · 1 = kein freies Thema (echter Engpass) · 2 = Selbsttest rot
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "content" / "posts"
LEDGER = ROOT / "data" / "reserve-topic-ledger.json"


def ledger_pfad(pfad: Path | None = None) -> Path:
    """Wo das Themen-Gedächtnis liegt – zur LAUFZEIT aufgelöst.

    Die Umgebungsvariable RESERVE_TOPIC_LEDGER lenkt es um. Das ist kein
    Luxus: Test- und Trockenläufe dürfen dem Repository keine echten
    Cooldowns unterschieben (ein Thema, das nur mangels API-Schlüssel
    scheiterte, wäre sonst drei Tage gesperrt).
    """
    if pfad is not None:
        return Path(pfad)
    ziel = (os.environ.get("RESERVE_TOPIC_LEDGER") or "").strip()
    return Path(ziel) if ziel else LEDGER

# Cooldowns (Tage). Bewusst konservativ: Der Themenpool hat >170 Einträge,
# ein gesperrtes Thema kostet also nie die Nacht.
SPERRE_ERFOLG = 180      # Thema produziert -> es steht jetzt im Bestand
SPERRE_FEHLER = 3        # einmal gescheitert -> ein paar Nächte Pause
SPERRE_DAUERFEHLER = 30  # ab DAUERFEHLER_AB Fehlversuchen: lange Pause
# 27.09.2026 (Content-Reserve #27, Issue #412): Infrastruktur-Ausfälle sind
# KEIN Thema-Urteil. try_generate kennzeichnet reine Provider-/Key-Ausfälle
# mit „[infra]“ in der Meldung; solche Themen bekommen nur eine Nacht Pause
# und zählen NICHT auf den Content-Fehlerzähler. Hält ein Ausfall über
# INFRA_DAUER_AB Nächte an, greift die Notbremse (Budget-Schutz).
SPERRE_INFRA = 1           # Provider-Ausfall -> morgen erneut versuchen
SPERRE_INFRA_DAUER = 7     # anhaltender Ausfall -> eine Woche Ruhe
INFRA_DAUER_AB = 3         # ab so vielen Infra-Nächten in Folge: Notbremse
INFRA_TAG = "[infra]"
DAUERFEHLER_AB = 3

# Füllwörter, die KEIN Thema unterscheiden. Bewusst klein gehalten: Der
# Leitbegriff soll das Sachthema sein („stromfresser", „tagesgeld"),
# nicht die Verpackung („ratgeber", „tipps", „check").
FUELLWOERTER = {
    "alltag", "anleitung", "beispiel", "beispiele", "check", "checkliste",
    "deine", "deinen", "dein", "diese", "einfach", "erklaert", "fuer",
    "guide", "ratgeber", "richtig", "schritt", "schritte", "sofort",
    "tipps", "tricks", "ueberblick", "vergleich", "wichtigste", "wirklich",
    "jahr", "jahre", "monat", "woche", "heute", "neue", "neuen", "neues",
    "beste", "besten", "besser", "mehr", "weniger", "guenstig",
    "guenstiger", "clever", "clevere", "smart", "einfache", "kleine",
    "grosse", "praxis", "update", "ueberblick", "haushalt", "zuhause",
    # Tätigkeiten und Allerwelts-Nomen: Sie stehen in fast jedem
    # Finanz-Titel und würden sonst wildfremde Themen verheiraten
    # („Ratenkredit Kosten" ~ „kostenloses Girokonto").
    "senken", "sparen", "sparst", "finden", "findest", "stoppen",
    "stoppst", "vergleichen", "vergleichst", "sichern", "sicherst",
    "wechseln", "wechselst", "reduzieren", "vermeiden", "planen",
    "optimieren", "verstehen", "kosten", "kostenlos", "kostenlose",
    "kostenloses", "kostenloser", "ausgaben", "euro", "geld", "budget",
    "lohnen", "lohnt", "brauchst", "solltest", "musst", "kannst",
    "bekommst", "zahlen", "zahlst", "pruefen", "pruefst", "nutzen",
    "nutzt", "machen", "machst", "starten", "startest", "aendern",
    "aendert", "wissen", "weisst", "bringt", "bringen",
}

# Leitbegriff = inhaltstragendes Token ab dieser Länge (nach Normalisierung).
LEIT_MIN = 6
# Präfix-Toleranz für Wortformen: „gasrechnung" ~ „gasrechnungen".
# Bewusst ab 7 Zeichen: Bei 6 hätte „kosten" jedes „kostenlos…" geschluckt
# und wildfremde Themen als Dublette gemeldet.
PRAEFIX_MIN = 7


# ---------------------------------------------------------------------------
#  Normalisierung & Leitbegriffe
# ---------------------------------------------------------------------------
def normalisieren(text: str) -> str:
    s = (text or "").lower()
    s = s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
    s = s.replace("ß", "ss").replace("é", "e").replace("è", "e")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def tokens(text: str) -> list[str]:
    return [w for w in normalisieren(text).split() if w]


def leitbegriffe(text: str) -> set[str]:
    """Die Sachbegriffe eines Titels: lange Wörter + Zahlen (50-30-20).

    Zahlen sind inhaltstragend („50-30-20-Regel"); kurze Wörter und
    Füllwörter sind es nicht. Zusammensetzungen werden zusätzlich über
    einen Präfix-Vergleich erkannt (siehe `verwandt`).
    """
    out = set()
    for w in tokens(text):
        if w.isdigit():
            if len(w) >= 2:
                out.add(w)
            continue
        if len(w) >= LEIT_MIN and w not in FUELLWOERTER:
            out.add(w)
    return out


def verwandt(a: str, b: str) -> bool:
    """Zwei Leitbegriffe meinen dasselbe Sachthema."""
    if a == b:
        return True
    if a.isdigit() or b.isdigit():
        return False
    kurz, lang = (a, b) if len(a) <= len(b) else (b, a)
    return len(kurz) >= PRAEFIX_MIN and lang.startswith(kurz)


def thema_kollision(titel: str, bestands_titel: dict[str, str]) -> tuple[str, str] | None:
    """(slug, begriff) des Bestands-Artikels mit demselben Leitbegriff.

    Zahlen-Themen („50-30-20-Regel") brauchen ZWEI gemeinsame Zahlen, sonst
    würde „2026" jedes Thema mit jedem verheiraten.
    """
    meine = leitbegriffe(titel)
    if not meine:
        return None
    for slug, anderer in bestands_titel.items():
        seine = leitbegriffe(anderer)
        if not seine:
            continue
        woerter = [a for a in meine if not a.isdigit()
                   and any(verwandt(a, b) for b in seine if not b.isdigit())]
        if woerter:
            return slug, sorted(woerter)[0]
        zahlen = [a for a in meine if a.isdigit() and a in seine]
        if len(zahlen) >= 2:
            return slug, "-".join(sorted(zahlen))
    return None


# ---------------------------------------------------------------------------
#  Bestand (live + Entwürfe + Pool)
# ---------------------------------------------------------------------------
def bestands_titel(posts_dir: Path = POSTS) -> dict[str, str]:
    """slug -> Titel für ALLE Artikel (live wie Entwurf).

    Entwürfe zählen mit: Ein Reserve-Kandidat ist ein fertiger Artikel, der
    nur auf seinen Tag wartet – ein zweiter zum selben Thema wäre die
    Dublette von morgen.
    """
    out: dict[str, str] = {}
    if not posts_dir.is_dir():
        return out
    for index in sorted(posts_dir.glob("*/index.md")):
        try:
            text = index.read_text(encoding="utf-8")
        except OSError:
            continue
        m = re.search(r'(?m)^title:\s*["\']?(.+?)["\']?\s*$', text)
        if m:
            out[index.parent.name] = m.group(1).strip()
    return out


def klumpen(posts_dir: Path = POSTS, ab: int = 2) -> dict[str, list[str]]:
    """Themen-Klumpen im Bestand: Leitbegriff -> Slugs (ab N Artikeln).

    Sichtbarkeit statt Bauchgefühl: Der Bericht zeigt, wo der Blog sich
    selbst kannibalisiert (am 26.09.2026: 6× „stromfresser", 5× „gasrechnung").
    """
    index: dict[str, list[str]] = {}
    for slug, titel in bestands_titel(posts_dir).items():
        for begriff in leitbegriffe(titel):
            if begriff.isdigit():
                continue
            ziel = next((k for k in index if verwandt(k, begriff)), begriff)
            index.setdefault(ziel, []).append(slug)
    return {k: sorted(v) for k, v in sorted(index.items()) if len(v) >= ab}


# ---------------------------------------------------------------------------
#  Gedächtnis (Ledger)
# ---------------------------------------------------------------------------
def ledger_laden(pfad: Path | None = None) -> dict:
    pfad = ledger_pfad(pfad)
    try:
        data = json.loads(pfad.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def ledger_speichern(data: dict, pfad: Path | None = None) -> None:
    pfad = ledger_pfad(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(data, ensure_ascii=False, indent=2,
                               sort_keys=True) + "\n", encoding="utf-8")


def _heute(jetzt: dt.date | None = None) -> dt.date:
    return jetzt or dt.date.today()


def gesperrt(eintrag: dict, jetzt: dt.date | None = None) -> bool:
    bis = (eintrag or {}).get("sperre_bis")
    if not bis:
        return False
    try:
        return dt.date.fromisoformat(str(bis)[:10]) > _heute(jetzt)
    except ValueError:
        return False


def merke(titel: str, ok: bool, grund: str = "", *, pfad: Path | None = None,
          jetzt: dt.date | None = None) -> dict:
    """Erfolg/Misserfolg eines Themas festhalten und Cooldown setzen.

    Klassenscharf seit 27.09.2026 (#412): Eine Meldung mit „[infra]“
    (trägt try_generate ein, wenn ALLE Versuche an Provider/Key/Ausfall
    hingen) ist ein System-Ausfall und kein Content-Urteil. Solche Themen
    zählen nicht auf `fehler` (kein Dauerfehler-Pfad), bekommen nur eine
    Nacht Pause; erst ab INFRA_DAUER_AB Infra-Nächten in Serie greift die
    Notbremse, damit ein dauerhaft toter Schlüssel das Budget schont.
    """
    pfad = ledger_pfad(pfad)
    heute = _heute(jetzt)
    data = ledger_laden(pfad)
    eintrag = dict(data.get(titel) or {})
    eintrag["letzter_versuch"] = heute.isoformat()
    if ok:
        eintrag["letzter_erfolg"] = heute.isoformat()
        eintrag["fehler"] = 0
        eintrag["infra_fehler"] = 0
        eintrag["sperre_bis"] = (heute + dt.timedelta(days=SPERRE_ERFOLG)).isoformat()
        eintrag["grund"] = grund or "produziert"
    elif INFRA_TAG in (grund or ""):
        eintrag["infra_fehler"] = int(eintrag.get("infra_fehler") or 0) + 1
        tage = (SPERRE_INFRA_DAUER if eintrag["infra_fehler"] >= INFRA_DAUER_AB
                else SPERRE_INFRA)
        eintrag["sperre_bis"] = (heute + dt.timedelta(days=tage)).isoformat()
        eintrag["grund"] = (grund or "Infrastruktur-Ausfall")[:200]
    else:
        eintrag["infra_fehler"] = 0
        eintrag["fehler"] = int(eintrag.get("fehler") or 0) + 1
        tage = (SPERRE_DAUERFEHLER if eintrag["fehler"] >= DAUERFEHLER_AB
                else SPERRE_FEHLER)
        eintrag["sperre_bis"] = (heute + dt.timedelta(days=tage)).isoformat()
        eintrag["grund"] = (grund or "Generierung gescheitert")[:200]
    data[titel] = eintrag
    ledger_speichern(data, pfad)
    return eintrag


# ---------------------------------------------------------------------------
#  Abgleich: ein Erfolgseintrag ohne Artefakt ist kein Erfolg
# ---------------------------------------------------------------------------
#  PREMIUM-FIX 02.10.2026 (Issue #521). `merke(..., ok=True)` wird gesetzt,
#  sobald der Entwurf GESCHRIEBEN ist – nicht, wenn er die Gates überlebt.
#  Das Thema bekommt dabei SPERRE_ERFOLG (180 Tage). Verwirft das Publish-Gate
#  den Artikel danach, bleibt ein Ledger-Eintrag „produziert: <slug>“ zurück,
#  zu dem es keinen Artikel mehr gibt: Das Thema ist ein halbes Jahr gesperrt,
#  der Blog hat nichts davon.
#
#  Realer Fund vom 02.10.2026: „Urlaubskasse clever aufbessern: 7 Tipps für
#  mehr Reisebudget“ → `produziert: so-bringst-du-deine-urlaubskasse-in-
#  schwung…`, gesperrt bis 2027-03-31 – der Slug existiert im Repository
#  nicht. Ein Produktionsslot und ein Thema, beide weg, ohne eine Zeile Text.
#  Insgesamt behaupteten 47 von 63 Ledger-Einträgen eine Produktion, zu der
#  es keinen Artikel gibt. Genau diese Phantom-Sperren – nicht ein leerer
#  Themenpool – ließen die Disposition am 02.10. nur noch 3 von 187 Themen
#  finden.
#
#  WARUM DAS GEFAHRLOS IST: Der Abgleich hebt ausschließlich den COOLDOWN
#  auf, nie den Dubletten-Schutz. Ob zu einem Thema schon ein Artikel
#  existiert, entscheidet weiterhin `thema_kollision()` gegen den echten
#  Bestand. Ein Thema ohne Artikel ist per Definition nicht belegt.
#
#  WARUM ES KEINE SCHLEIFE GIBT: Ein einzelner Phantom-Eintrag ist ein
#  Buchhaltungsfehler und wird nicht bestraft (kein `fehler`-Zähler, keine
#  Sperre). Wiederholt er sich, ist es ein Inhaltsproblem – ab
#  DAUERFEHLER_AB Abgleichen greift die lange Sperre.
ABGLEICH_ZAEHLER = "abgleich_fehler"


def _produzierter_slug(grund: str) -> str:
    """Slug aus einem Erfolgs-Eintrag („produziert: <slug>“) – sonst ''."""
    text = str(grund or "").strip()
    if not text.lower().startswith("produziert:"):
        return ""
    rest = text.split(":", 1)[1].strip()
    return rest.split()[0] if rest else ""


# Die Engine merkt sich den Slug OHNE Datumspräfix („hausratversicherung-…“),
# das Bündel auf der Platte heißt aber „2026-10-02-hausratversicherung-…“ –
# und bei Titel-Dubletten hängt save_article zusätzlich „-2“ an. Wer hier
# naiv `posts_dir / slug` prüft, erklärt JEDEN produzierten Artikel für
# verschwunden und gibt den halben Themenpool frei. Genau diese Falle wurde
# beim Bau von `abgleich()` einmal gestellt und durch Messen gefunden.
_DATUMSPRAEFIX = re.compile(r"^\d{4}-\d{2}-\d{2}-")
_DUBLETTEN_SUFFIX = re.compile(r"-\d+$")


def _bestands_slugs(posts_dir: Path) -> set[str]:
    """Alle Artikel-Slugs auf der Platte, normalisiert wie im Ledger."""
    out: set[str] = set()
    posts_dir = Path(posts_dir)
    if not posts_dir.is_dir():
        return out
    for index in posts_dir.glob("*/index.md"):
        name = index.parent.name
        out.add(name)
        ohne_datum = _DATUMSPRAEFIX.sub("", name)
        out.add(ohne_datum)
        out.add(_DUBLETTEN_SUFFIX.sub("", ohne_datum))
    return out


def abgleich(posts_dir: Path = POSTS, *, pfad: Path | None = None,
             jetzt: dt.date | None = None, apply: bool = True) -> list[dict]:
    """Erfolgs-Sperren ohne Artefakt auflösen – Themen zurück in die Rotation.

    Prüft jeden Eintrag „produziert: <slug>“ gegen das Dateisystem. Fehlt der
    Artikel, war die Meldung falsch: Die 180-Tage-Erfolgssperre fällt und das
    Thema steht der nächsten Disposition sofort wieder zur Verfügung. Der
    Dubletten-Schutz (`thema_kollision`) bleibt davon unberührt – er misst
    den echten Bestand, nicht das Gedächtnis.

    Wiederholt sich der Fund für dasselbe Thema (ab DAUERFEHLER_AB), ist es
    kein Buchhaltungsfehler mehr, sondern ein Thema, dessen Artikel immer
    wieder an den Gates stirbt: dann greift die lange Sperre.

    Rückgabe: Liste der Korrekturen (leer = Ledger und Bestand sind einig).
    """
    posts_dir = Path(posts_dir)
    pfad = ledger_pfad(pfad)
    heute = _heute(jetzt)
    data = ledger_laden(pfad)
    vorhanden = _bestands_slugs(posts_dir)
    korrekturen: list[dict] = []
    for titel, eintrag in list(data.items()):
        if not isinstance(eintrag, dict):
            continue
        slug = _produzierter_slug(eintrag.get("grund", ""))
        if not slug:
            continue
        if slug in vorhanden:
            continue
        runden = int(eintrag.get(ABGLEICH_ZAEHLER) or 0) + 1
        chronisch = runden >= DAUERFEHLER_AB
        korrekturen.append({
            "titel": titel,
            "slug": slug,
            "war_gesperrt_bis": eintrag.get("sperre_bis"),
            "runde": runden,
            "chronisch": chronisch,
        })
        if not apply:
            continue
        neu = dict(eintrag)
        neu[ABGLEICH_ZAEHLER] = runden
        neu.pop("letzter_erfolg", None)
        if chronisch:
            neu["fehler"] = int(neu.get("fehler") or 0) + 1
            neu["sperre_bis"] = (
                heute + dt.timedelta(days=SPERRE_DAUERFEHLER)).isoformat()
            neu["grund"] = (
                f"Artefakt fehlt ({slug}) – bereits {runden}× ohne Ergebnis "
                f"produziert, Thema für {SPERRE_DAUERFEHLER} Tage geparkt")[:200]
        else:
            # Kein Urteil über das Thema: nur die falsche Sperre fällt.
            neu.pop("sperre_bis", None)
            neu["grund"] = (
                f"Artefakt fehlt ({slug}) – Erfolgsmeldung zurückgenommen, "
                f"Thema wieder frei (Dubletten-Schutz bleibt aktiv)")[:200]
        data[titel] = neu
    if apply and korrekturen:
        ledger_speichern(data, pfad)
    return korrekturen


# ---------------------------------------------------------------------------
#  Disposition
# ---------------------------------------------------------------------------
#: Standard-Bahn der Disposition. Siehe `scripts/engine_capacity.py`.
#: Wer den GESAMTEN Pool sehen will (Reports, Kollisions-Tests), ruft
#: ausdrücklich mit `bahn=None` auf.
BAHN_DEFAULT = "auto"


def _bahn_filter(topics: list, bahn: str | None) -> list:
    """Themen auf eine Publikations-Bahn eingrenzen (fail-open).

    PREMIUM-FIX 02.10.2026 (Issue #521): Bis hierher war die Disposition
    blind gegenüber der Frage, ob ein Thema überhaupt automatisch
    veröffentlicht werden DARF. 46 der 187 Themen sind YMYL-Hochrisiko und
    damit per `editorial_review_gate` fail-closed – sie brauchen eine
    namentliche Fachfreigabe. Am 02.10.2026 hat die Disposition zwei davon
    in die Tagesquote gegeben; beide Artikel wurden sauber erzeugt, vom Gate
    korrekt gehalten und der Tag endete bei 0/2 LIVE.

    Die Einstufung wird NICHT hier nachgebaut: `engine_capacity` leitet sie
    aus derselben Funktion ab, die das Gate später am fertigen Artikel
    benutzt. Lädt das Modul nicht, disponieren wir wie früher über den
    ganzen Pool – eine kaputte Kapazitätsrechnung darf die Produktion
    nicht anhalten, sie soll sie nur besser planen.
    """
    if bahn is None:
        return list(topics or [])
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import engine_capacity as ec  # noqa: PLC0415 – fail-open, siehe oben
    except Exception as exc:  # noqa: BLE001
        print(f"  ⚠ Bahn-Filter inaktiv ({exc}) – Disposition nutzt den "
              f"gesamten Themenpool.")
        return list(topics or [])
    return [t for t in (topics or [])
            if (t or {}).get("title") and ec.bahn_fuer_thema(t) == bahn]


def disponieren(topics: list, used_titles=None, *, posts_dir: Path = POSTS,
                pfad: Path | None = None, limit: int = 5,
                jetzt: dt.date | None = None,
                bestand: dict[str, str] | None = None,
                bahn: str | None = BAHN_DEFAULT) -> list[dict]:
    """Beste Themen für die Reserve-Produktion – begründet und rotierend.

    Rückgabe: Liste von Themen-Dicts (Original-Objekte aus topics.yaml),
    höchstens `limit` Stück, beste zuerst.

    `bahn` (seit 02.10.2026, Issue #521) grenzt auf Themen ein, die die
    Automatik auch ausliefern darf. Default ist die AUTO-Bahn – die
    Tagesquote wird nie wieder mit Hochrisiko-Themen geplant, die nur ein
    Mensch freigeben kann. `bahn=None` liefert den gesamten Pool.
    """
    topics = _bahn_filter(topics, bahn)
    bestand = bestands_titel(posts_dir) if bestand is None else bestand
    data = ledger_laden(pfad)
    kandidaten = []
    for pos, topic in enumerate(topics or []):
        titel = (topic or {}).get("title") or ""
        if not titel:
            continue
        if thema_kollision(titel, bestand):
            continue
        eintrag = data.get(titel) or {}
        if gesperrt(eintrag, jetzt):
            continue
        letzter = str(eintrag.get("letzter_versuch") or "")
        # Nie versucht (leer) sortiert vor jedem Datum – deterministisch.
        kandidaten.append(((letzter, int(eintrag.get("fehler") or 0), pos),
                           topic))
    kandidaten.sort(key=lambda p: p[0])
    return [t for _, t in kandidaten[:max(1, limit)]]


def bericht(topics: list | None = None, *, posts_dir: Path = POSTS,
            pfad: Path | None = None) -> dict:
    if topics is None:
        sys.path.insert(0, str(ROOT / "scripts"))
        import generate_drafts as g  # noqa: PLC0415 – optional
        topics = g.load_topics()
    bestand = bestands_titel(posts_dir)
    frei = disponieren(topics, posts_dir=posts_dir, pfad=pfad, limit=10,
                       bestand=bestand)
    # Der Bericht nennt beide Bahnen getrennt (Issue #521): „frei“ ohne
    # Bahn-Angabe war die Zahl, die am 02.10. in die Irre geführt hat.
    frei_alle = disponieren(topics, posts_dir=posts_dir, pfad=pfad,
                            limit=10_000, bestand=bestand, bahn=None)
    belegt = sum(1 for t in topics
                 if thema_kollision((t or {}).get("title") or "", bestand))
    data = ledger_laden(pfad)
    return {
        "themen_gesamt": len(topics),
        "themen_belegt": belegt,
        "themen_gesperrt": sum(1 for e in data.values() if gesperrt(e)),
        "frei_auto": len(disponieren(topics, posts_dir=posts_dir, pfad=pfad,
                                     limit=10_000, bestand=bestand)),
        "frei_alle_bahnen": len(frei_alle),
        "naechste": [t.get("title") for t in frei],
        "erfolge_ohne_artefakt": len(abgleich(posts_dir, pfad=pfad,
                                              apply=False)),
        "klumpen": {k: len(v) for k, v in klumpen(posts_dir).items()},
    }


# ---------------------------------------------------------------------------
#  Sabotage-Schutz
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    import tempfile
    fehler = []

    # 1. Der reale Befund vom 26.09.2026: Das Thema galt als frei, obwohl
    #    der Bestand sechs Artikel dazu hatte.
    bestand = {
        "a": "Energiediebe stoppen: So kannst du Stromfresser finden",
        "b": "Stromfresser finden: So stoppst du teure Energiediebe",
        "c": "Gasrechnung senken: Warum ich meine Heizung im August prüfe",
        "d": "Die 50-30-20-Regel einfach erklärt",
    }
    if not thema_kollision("Stromfresser im Haushalt entlarven", bestand):
        fehler.append("Themen-Kollision „Stromfresser“ nicht erkannt "
                      "(genau dieser Fund machte den Lauf rot)")
    if not thema_kollision("Gasrechnung senken vor dem Winter", bestand):
        fehler.append("Themen-Kollision „Gasrechnung“ nicht erkannt")
    if not thema_kollision("50-30-20-Regel: Dein Finanz-Kompass 2026", bestand):
        fehler.append("Zahlen-Thema (50-30-20) nicht erkannt")
    # … und ein echtes neues Thema darf NICHT blockiert werden.
    for frisch in ("Tagesgeld-Vergleich: Zinsen sichern",
                   "Zahnzusatzversicherung: Leistungen im Blick",
                   "Mietwagen im Urlaub clever buchen"):
        if thema_kollision(frisch, bestand):
            fehler.append(f"Falsch-Positiv bei frischem Thema: {frisch!r}")

    # 2. Rotation: nie versuchte Themen zuerst, dann das älteste.
    #    Alle drei Themen liegen bewusst in der AUTO-Bahn: Seit Issue #521
    #    filtert `disponieren` Hochrisiko-Themen aus der Tagesquote, ein
    #    Versicherungs-Thema würde hier also die Rotation prüfen wollen und
    #    stattdessen den Bahn-Filter messen. Die Bahn hat ihren eigenen
    #    Prüfblock (8); hier geht es ausschließlich um die Reihenfolge.
    topics = [{"title": "Tagesgeld-Vergleich: Zinsen sichern"},
              {"title": "Mietwagen im Urlaub clever buchen"},
              {"title": "Haushaltsbuch führen: App, Excel oder Papier?"}]
    with tempfile.TemporaryDirectory() as tmp:
        pfad = Path(tmp) / "ledger.json"
        heute = dt.date(2026, 9, 26)
        merke(topics[0]["title"], False, "KI-Ausfall", pfad=pfad,
              jetzt=heute - dt.timedelta(days=10))
        merke(topics[1]["title"], False, "KI-Ausfall", pfad=pfad,
              jetzt=heute - dt.timedelta(days=4))
        reihe = [t["title"] for t in
                 disponieren(topics, posts_dir=Path(tmp), pfad=pfad,
                             jetzt=heute, bestand=bestand)]
        if reihe != [topics[2]["title"], topics[0]["title"],
                     topics[1]["title"]]:
            fehler.append(f"Rotation falsch: {reihe}")

        # 3. Cooldown: ein frisch gescheitertes Thema blockiert die nächste
        #    Nacht nicht mehr (das war der Dauer-Stillstand).
        merke(topics[2]["title"], False, "Profi-Gate", pfad=pfad, jetzt=heute)
        reihe = [t["title"] for t in
                 disponieren(topics, posts_dir=Path(tmp), pfad=pfad,
                             jetzt=heute, bestand=bestand)]
        if topics[2]["title"] in reihe:
            fehler.append("gescheitertes Thema wurde sofort erneut gewählt")
        if not reihe:
            fehler.append("Cooldown hat den kompletten Pool gesperrt")

        # 4. Erfolg sperrt lange – sonst entsteht die Dubletten-Kaskade.
        merke(topics[0]["title"], True, "produziert", pfad=pfad, jetzt=heute)
        eintrag = ledger_laden(pfad)[topics[0]["title"]]
        if not gesperrt(eintrag, heute + dt.timedelta(days=90)):
            fehler.append("Erfolgs-Sperre hält keine 90 Tage")
        if eintrag.get("fehler") != 0:
            fehler.append("Erfolg setzt den Fehlerzähler nicht zurück")

        # 5. Dauerfehler -> lange Sperre (ein totes Thema blockiert nie wieder)
        for _ in range(DAUERFEHLER_AB):
            merke(topics[1]["title"], False, "kein Text", pfad=pfad, jetzt=heute)
        if not gesperrt(ledger_laden(pfad)[topics[1]["title"]],
                        heute + dt.timedelta(days=20)):
            fehler.append("Dauerfehler-Sperre greift nicht")

        # 6. Leeres/kaputtes Ledger darf nie blockieren (fail-open).
        (Path(tmp) / "kaputt.json").write_text("{kaputt", encoding="utf-8")
        if ledger_laden(Path(tmp) / "kaputt.json") != {}:
            fehler.append("kaputtes Ledger wird nicht ignoriert")
        if not disponieren(topics, posts_dir=Path(tmp),
                           pfad=Path(tmp) / "gibt-es-nicht.json",
                           bestand={}):
            fehler.append("ohne Ledger muss jedes Thema wählbar sein")

        # 8. Infra-Klasse (27.09.2026, #412): Ein reiner Provider-Ausfall
        #    („[infra]“) darf KEINEN Content-Cooldown auslösen – nur eine
        #    Nacht Pause, Fehlerzähler unberührt. Erst nach INFRA_DAUER_AB
        #    Infra-Nächten in Serie greift die Budget-Notbremse, und ein
        #    Erfolg räumt beide Zähler ab.
        t = topics[0]["title"]
        e = merke(t, False, "3 Versuche ohne Erfolg [infra] "
                            "(Provider-Fehler (GROQ): 429)", pfad=pfad,
                  jetzt=heute)
        if e.get("fehler"):
            fehler.append("Infra-Ausfall zählt auf den Content-Fehlerzähler")
        if e.get("infra_fehler") != 1:
            fehler.append("Infra-Zähler zählt nicht mit")
        if gesperrt(e, heute + dt.timedelta(days=1)) or \
           not gesperrt(e, heute):
            fehler.append("Infra-Pause muss genau eine Nacht sein")
        if gesperrt(e, heute + dt.timedelta(days=2)):
            fehler.append("Infra-Ausfall sperrt wie ein Content-Fehler")
        #    Content-Fehler danach: läuft weiter auf dem alten Zähler.
        e = merke(t, False, "3 Versuche ohne Erfolg [inhalt] (Profi-Gate)",
                  pfad=pfad, jetzt=heute)
        if e.get("fehler") != 1 or e.get("infra_fehler") != 0:
            fehler.append("Content-Fehler nach Infra setzt die Zähler falsch")
        #    Anhaltender Ausfall -> Notbremse.
        for _ in range(INFRA_DAUER_AB):
            e = merke(t, False, "3 Versuche ohne Erfolg [infra] "
                                "(Provider-Fehler: 503)", pfad=pfad,
                      jetzt=heute)
        if not gesperrt(e, heute + dt.timedelta(days=5)):
            fehler.append("Infra-Dauerbremse greift nicht")
        e = merke(t, True, "produziert: test", pfad=pfad, jetzt=heute)
        if e.get("fehler") != 0 or e.get("infra_fehler") != 0:
            fehler.append("Erfolg setzt die Infra-/Fehlerzähler nicht zurück")

    # 7. Klumpen-Erkennung (Bericht an die Redaktion)
    import tempfile as _tf
    with _tf.TemporaryDirectory() as tmp:
        posts = Path(tmp) / "posts"
        for name, titel in bestand.items():
            (posts / f"2026-09-01-{name}").mkdir(parents=True)
            (posts / f"2026-09-01-{name}" / "index.md").write_text(
                f'---\ntitle: "{titel}"\ndraft: true\n---\n\nText.\n',
                encoding="utf-8")
        gefunden = klumpen(posts)
        if "stromfresser" not in gefunden:
            fehler.append(f"Klumpen-Bericht findet „stromfresser“ nicht: "
                          f"{sorted(gefunden)}")

    # 8. BAHN-FILTER (02.10.2026, Issue #521): Die Tagesquote darf kein
    #    Hochrisiko-Thema mehr bekommen. Eingefroren mit den zwei Themen,
    #    die am 02.10. real zwei Slots verbrannt haben.
    with _tf.TemporaryDirectory() as tmp:
        pfad = Path(tmp) / "ledger.json"
        pool = [
            {"title": "Vergleich von Hausratversicherungen und wie du sparst"},
            {"title": "Reisekrankenversicherung: Wann sie sich wirklich lohnt"},
            {"title": "Black Friday DSL-Deals: Diese Angebote lohnen sich wirklich"},
        ]
        quote = [t["title"] for t in
                 disponieren(pool, posts_dir=Path(tmp), pfad=pfad, limit=10,
                             bestand={})]
        if quote != ["Black Friday DSL-Deals: Diese Angebote lohnen sich wirklich"]:
            fehler.append(f"Bahn-Filter lässt Hochrisiko-Themen in die "
                          f"Tagesquote: {quote}")
        alle = [t["title"] for t in
                disponieren(pool, posts_dir=Path(tmp), pfad=pfad, limit=10,
                            bestand={}, bahn=None)]
        if len(alle) != 3:
            fehler.append(f"bahn=None muss den ganzen Pool liefern: {alle}")

    # 9. ABGLEICH (02.10.2026, Issue #521): Eine Erfolgsmeldung ohne Artikel
    #    sperrt das Thema 180 Tage für nichts. Realer Fund: „Urlaubskasse
    #    clever aufbessern“ → produziert: <slug>, Slug existiert nicht.
    with _tf.TemporaryDirectory() as tmp:
        pfad = Path(tmp) / "ledger.json"
        posts = Path(tmp) / "posts"
        posts.mkdir()
        heute = dt.date(2026, 10, 2)
        echt, phantom = "Thema mit Artikel", "Urlaubskasse clever aufbessern"
        (posts / "2026-10-02-echt").mkdir()
        (posts / "2026-10-02-echt" / "index.md").write_text(
            '---\ntitle: "Echt"\ndraft: false\n---\n\nText.\n',
            encoding="utf-8")
        # Das Ledger merkt sich den Slug OHNE Datum – der Abgleich muss
        # das Bündel trotzdem finden (sonst gibt er alles frei).
        merke(echt, True, "produziert: echt", pfad=pfad, jetzt=heute)
        merke(phantom, True, "produziert: 2026-10-02-phantom", pfad=pfad,
              jetzt=heute)
        korrekturen = abgleich(posts, pfad=pfad, jetzt=heute)
        if [k["titel"] for k in korrekturen] != [phantom]:
            fehler.append(f"Abgleich erkennt die Phantom-Produktion nicht: "
                          f"{korrekturen}")
        data = ledger_laden(pfad)
        if gesperrt(data[phantom], heute):
            fehler.append("Phantom-Thema bleibt nach dem Abgleich gesperrt – "
                          "genau diese Sperre ließ die Disposition am "
                          "02.10.2026 nur 3 von 187 Themen finden")
        if not gesperrt(data[echt], heute + dt.timedelta(days=30)):
            fehler.append("Abgleich hebt eine ECHTE Erfolgssperre auf "
                          "(der Artikel existiert – das Thema ist belegt)")
        # Wiederholung ist ein Inhaltsproblem, kein Buchhaltungsfehler:
        # ab DAUERFEHLER_AB Runden muss die lange Sperre greifen.
        for _ in range(DAUERFEHLER_AB - 1):
            merke(phantom, True, "produziert: 2026-10-02-phantom", pfad=pfad,
                  jetzt=heute)
            abgleich(posts, pfad=pfad, jetzt=heute)
        data = ledger_laden(pfad)
        if not gesperrt(data[phantom], heute + dt.timedelta(days=20)):
            fehler.append("Chronische Phantom-Produktion wird nicht geparkt "
                          "– das Thema dreht sich endlos im Kreis")

    if fehler:
        print("🛑 RESERVE-TOPICS-SELBSTTEST FEHLGESCHLAGEN:")
        for f in fehler:
            print(f"   - {f}")
        return 2
    print("✅ Reserve-Themen-Selbsttest grün (Leitbegriff-Kollision, "
          "Rotation, Cooldown, Erfolgs-/Dauerfehler-Sperre, fail-open, "
          "Infra-Klasse ohne Content-Cooldown, Klumpen-Bericht, "
          "Bahn-Filter, Abgleich).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Themen-Disposition der "
                                             "Content-Reserve")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--klumpen", action="store_true")
    ap.add_argument("--abgleich", action="store_true",
                    help="Erfolgs-Sperren ohne Artefakt auflösen (Issue #521)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return run_selftest()
    if args.abgleich:
        korrekturen = abgleich()
        if not korrekturen:
            print("✅ Ledger und Bestand sind einig – keine Erfolgsmeldung "
                  "ohne Artikel.")
            return 0
        print(f"🔧 {len(korrekturen)} Erfolgsmeldung(en) ohne Artikel "
              f"zurückgenommen – Themen wieder frei:")
        for k in korrekturen:
            print(f"   - „{k['titel']}“ (war gesperrt bis "
                  f"{k['war_gesperrt_bis']}, Slug {k['slug']} existiert nicht)")
        return 0
    if args.klumpen:
        gefunden = klumpen()
        if not gefunden:
            print("✅ Keine Themen-Klumpen im Bestand.")
            return 0
        print("🔎 Themen-Klumpen im Bestand (Leitbegriff: Artikel):")
        for begriff, slugs in sorted(gefunden.items(),
                                     key=lambda kv: -len(kv[1])):
            print(f"   {len(slugs):>2}× {begriff}")
            for slug in slugs:
                print(f"        - {slug}")
        return 0
    daten = bericht()
    if args.json:
        print(json.dumps(daten, ensure_ascii=False))
    else:
        print(f"Themenpool: {daten['themen_gesamt']} Themen · "
              f"{daten['themen_belegt']} thematisch belegt · "
              f"{daten['themen_gesperrt']} im Cooldown")
        print(f"Frei disponierbar: {daten['frei_auto']} in der AUTO-Bahn "
              f"(quotenfähig) von {daten['frei_alle_bahnen']} über alle "
              f"Bahnen – Details: python3 scripts/engine_capacity.py")
        if daten["erfolge_ohne_artefakt"]:
            print(f"⚠️ {daten['erfolge_ohne_artefakt']} Erfolgsmeldung(en) "
                  f"ohne Artikel – `--abgleich` gibt die Themen frei.")
        print("Nächste Themen der Reserve-Produktion:")
        for titel in daten["naechste"]:
            print(f"   - {titel}")
        if daten["klumpen"]:
            print("Themen-Klumpen im Bestand: "
                  + ", ".join(f"{k} ({n}×)" for k, n in
                              sorted(daten["klumpen"].items(),
                                     key=lambda kv: -kv[1])[:6]))
    return 0 if daten["naechste"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
