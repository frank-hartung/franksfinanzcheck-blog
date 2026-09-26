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
    """Erfolg/Misserfolg eines Themas festhalten und Cooldown setzen."""
    pfad = ledger_pfad(pfad)
    heute = _heute(jetzt)
    data = ledger_laden(pfad)
    eintrag = dict(data.get(titel) or {})
    eintrag["letzter_versuch"] = heute.isoformat()
    if ok:
        eintrag["letzter_erfolg"] = heute.isoformat()
        eintrag["fehler"] = 0
        eintrag["sperre_bis"] = (heute + dt.timedelta(days=SPERRE_ERFOLG)).isoformat()
        eintrag["grund"] = grund or "produziert"
    else:
        eintrag["fehler"] = int(eintrag.get("fehler") or 0) + 1
        tage = (SPERRE_DAUERFEHLER if eintrag["fehler"] >= DAUERFEHLER_AB
                else SPERRE_FEHLER)
        eintrag["sperre_bis"] = (heute + dt.timedelta(days=tage)).isoformat()
        eintrag["grund"] = (grund or "Generierung gescheitert")[:200]
    data[titel] = eintrag
    ledger_speichern(data, pfad)
    return eintrag


# ---------------------------------------------------------------------------
#  Disposition
# ---------------------------------------------------------------------------
def disponieren(topics: list, used_titles=None, *, posts_dir: Path = POSTS,
                pfad: Path | None = None, limit: int = 5,
                jetzt: dt.date | None = None,
                bestand: dict[str, str] | None = None) -> list[dict]:
    """Beste Themen für die Reserve-Produktion – begründet und rotierend.

    Rückgabe: Liste von Themen-Dicts (Original-Objekte aus topics.yaml),
    höchstens `limit` Stück, beste zuerst.
    """
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
    belegt = sum(1 for t in topics
                 if thema_kollision((t or {}).get("title") or "", bestand))
    data = ledger_laden(pfad)
    return {
        "themen_gesamt": len(topics),
        "themen_belegt": belegt,
        "themen_gesperrt": sum(1 for e in data.values() if gesperrt(e)),
        "naechste": [t.get("title") for t in frei],
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
    topics = [{"title": "Tagesgeld-Vergleich: Zinsen sichern"},
              {"title": "Mietwagen im Urlaub clever buchen"},
              {"title": "Zahnzusatzversicherung: Leistungen im Blick"}]
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

    if fehler:
        print("🛑 RESERVE-TOPICS-SELBSTTEST FEHLGESCHLAGEN:")
        for f in fehler:
            print(f"   - {f}")
        return 2
    print("✅ Reserve-Themen-Selbsttest grün (Leitbegriff-Kollision, "
          "Rotation, Cooldown, Erfolgs-/Dauerfehler-Sperre, fail-open, "
          "Klumpen-Bericht).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Themen-Disposition der "
                                             "Content-Reserve")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--klumpen", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return run_selftest()
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
