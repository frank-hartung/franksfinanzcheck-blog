#!/usr/bin/env python3
"""
themen_nachschub_waechter.py – der Vorlauf der AUTO-Bahn in TAGEN
================================================================

WARUM ES DIESE WACHE GIBT (25.10.2026, WF-D4E0 / #821)
------------------------------------------------------
Der Vorrat der Content-Reserve fiel zwischen dem 19.10. und dem 25.10. von
6 auf 1 gate-fertige Kandidaten. Jede Nacht lief derselbe Ablauf, jede Nacht
wurde derselbe Schritt rot („Stock shortage must not look successful"), und
jede Nacht nannte das Ticket nur den Vorrat – nie die Ursache:

    * 154 von 202 Themen galten als „thematisch belegt",
    * die übrigen 21 waren ausschließlich YMYL-Hochrisiko, also per Vertrag
      nie automatisch veröffentlichbar (Fachfreigabe-Bahn),
    * in der AUTO-Bahn war folglich **0** Themen frei.

Die Produktion hat nicht versagt – sie hatte nichts zu produzieren. Genau
diesen Zustand konnte bis heute niemand VORHER sehen:

  * ``engine_capacity.lage()`` misst ehrlich, aber in STÜCK („frei 0"),
    nicht in ZEIT („null Tage Vorlauf"). Für einen Redaktionsbetrieb ist
    die zweite Zahl die entscheidende: Sie sagt, wie lange die Automatik
    sich noch selbst versorgen kann.
  * Der Engpass wurde erst gemeldet, als der Vorrat schon leer war – also
    drei Wochen zu spät, mitten im Dauer-Alarm.

Diese Wache rechnet den Stück-Vorrat in Produktionstage um und vergleicht
ihn mit dem Mindestvorlauf. Sie ist bewusst eine WACHE und kein Heiler:
Themen kann man nicht erfinden, sie gehören in ``data/topics.yaml``.

EIN MASS, KEINE ZWEITE ZÄHLREGEL
--------------------------------
Gezählt wird ausschließlich über ``engine_capacity.lage()`` – und das zählt
über ``reserve_topics.disponieren()``, also mit demselben Maß, mit dem die
Engine ihr Thema wirklich auswählt (Leitbegriff-Kollision, Cooldown-Gedächtnis,
Bahn-Filter). Wer hier eine eigene Zählung einbaut, baut die Lüge wieder ein,
die ``engine_capacity`` am 02.10.2026 beendet hat („157 frei" vs. „3 frei").

NUTZUNG
    python3 scripts/themen_nachschub_waechter.py              # Lage + Urteil
    python3 scripts/themen_nachschub_waechter.py --json
    python3 scripts/themen_nachschub_waechter.py --warn-only   # nie Exit 1
    python3 scripts/themen_nachschub_waechter.py --selftest

EXIT: 0 = Vorlauf reicht · 1 = unter Mindestvorlauf (Themennachschub) ·
      2 = Selbsttest rot
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

# Wie viele Tage die Automatik ohne jedes neue Thema noch arbeiten kann,
# bevor sie stillsteht. Zwei Wochen sind im Redaktionsbetrieb die Größe, die
# einen Nachschub-Auftrag erlaubt, ohne dass er unter Zeitdruck entsteht:
# Ein Themenblatt braucht Titel, Keywords, /go/-Ziel und eine Kollisions-
# Prüfung – das ist Redaktionsarbeit, keine Nachtschicht.
HORIZON_TAGE_DEFAULT = 14
ENV_HORIZON = "THEMEN_HORIZON_TAGE"
# Unter dieser Restzeit ist die Lage nicht „knapp", sondern erschöpft.
KNAPP_FAKTOR = 2

VERDIKT_OK = "ok"
VERDIKT_KNAPP = "knapp"
VERDIKT_ERSCHOEPFT = "erschoepft"


def vorlauf_tage(frei_auto: int, tagesbedarf: int) -> float:
    """Stück-Vorrat in Produktionstage – die eine Formel für alle Verbraucher.

    ``reserve_gate`` benutzt dieselbe Rechnung für seinen Befund, ohne ein
    zweites Mal zu messen: Ein Vorrat von 0 Themen ergibt 0 Tage, nicht
    „unbekannt".
    """
    return round(int(frei_auto) / max(1, int(tagesbedarf)), 1)


def _zahl_aus_env(name: str, default: int, minimum: int, maximum: int,
                  warnungen: list[str], env: dict | None = None) -> int:
    """Geklemmte Zahl aus der Umgebung – nie still verschluckt."""
    quelle = os.environ if env is None else env
    roh = (quelle.get(name) or "").strip()
    if not roh:
        return default
    try:
        wert = int(roh)
    except (TypeError, ValueError):
        warnungen.append(f"{name}={roh!r} ist keine Zahl – es gilt {default}.")
        return default
    if wert < minimum or wert > maximum:
        warnungen.append(f"{name}={wert} liegt außerhalb {minimum}–{maximum} "
                         f"– geklemmt.")
        return max(minimum, min(maximum, wert))
    return wert


def lage(*, topics: list | None = None, posts_dir: Path | None = None,
         ledger: Path | None = None, jetzt=None, env: dict | None = None) -> dict:
    """Vorlauf der AUTO-Bahn in Tagen – gerechnet mit dem Maß der Engine."""
    import engine_capacity as ec
    import reserve_topics as rt

    warnungen: list[str] = []
    kapazitaet = ec.lage(topics, posts_dir=posts_dir or ec.POSTS,
                         ledger=ledger, jetzt=jetzt, env=env)

    if topics is None:
        import generate_drafts as g
        topics = g.load_topics()
    bestand = rt.bestands_titel(Path(posts_dir) if posts_dir else ec.POSTS)
    belegt = sum(1 for t in topics
                 if rt.thema_kollision((t or {}).get("title") or "", bestand))
    gedaechtnis = rt.ledger_laden(ledger) if ledger else rt.ledger_laden()
    gesperrt = sum(1 for e in gedaechtnis.values() if rt.gesperrt(e, jetzt))

    horizon = _zahl_aus_env(ENV_HORIZON, HORIZON_TAGE_DEFAULT, 1, 365,
                            warnungen, env)
    bedarf = max(1, int(kapazitaet.get("min_artikel_pro_tag") or 1))
    frei_auto = int(kapazitaet.get("frei_auto") or 0)
    frei_fach = int(kapazitaet.get("frei_fachfreigabe") or 0)

    # Der Vorlauf ist die einzige Zahl, die eine Redaktion planen kann:
    # „55 Themen" heißt nichts, „27 Produktionstage" heißt alles.
    vorlauf = vorlauf_tage(frei_auto, bedarf)
    if frei_auto == 0:
        verdikt = VERDIKT_ERSCHOEPFT
    elif vorlauf < horizon / KNAPP_FAKTOR:
        verdikt = VERDIKT_ERSCHOEPFT
    elif vorlauf < horizon:
        verdikt = VERDIKT_KNAPP
    else:
        verdikt = VERDIKT_OK

    fehlend = max(0, horizon * bedarf - frei_auto)
    if frei_auto == 0 and frei_fach > 0:
        befund = (f"Kein freies Thema der AUTO-Bahn. Die {frei_fach} freien "
                  f"Themen liegen ausschließlich in der FACHFREIGABE-Bahn "
                  f"(YMYL, menschliche Freigabe) – daraus kann die Automatik "
                  f"nichts produzieren. Das ist Themennachschub, keine "
                  f"KI-Störung und kein Provider-Ausfall.")
    elif frei_auto == 0:
        befund = (f"Kein freies Thema in irgendeiner Bahn: {belegt} von "
                  f"{kapazitaet['themen_gesamt']} Themen sind thematisch "
                  f"belegt, {gesperrt} im Cooldown.")
    elif verdikt == VERDIKT_OK:
        befund = (f"{frei_auto} AUTO-Themen frei = {vorlauf:g} "
                  f"Produktionstage bei {bedarf} Artikeln/Tag "
                  f"(Mindestvorlauf {horizon}).")
    else:
        befund = (f"Nur {frei_auto} AUTO-Themen frei = {vorlauf:g} "
                  f"Produktionstage bei {bedarf} Artikeln/Tag – unter dem "
                  f"Mindestvorlauf von {horizon} Tagen. Es fehlen {fehlend} "
                  f"Themen in data/topics.yaml.")

    return {
        "verdikt": verdikt,
        "befund": befund,
        "frei_auto": frei_auto,
        "frei_fachfreigabe": frei_fach,
        "vorlauf_tage": vorlauf,
        "mindestvorlauf_tage": horizon,
        "tagesbedarf": bedarf,
        "fehlende_themen": fehlend,
        "themen_gesamt": kapazitaet["themen_gesamt"],
        "themen_belegt": belegt,
        "themen_im_cooldown": gesperrt,
        "warnungen": list(kapazitaet.get("warnungen") or []) + warnungen,
    }


def bericht(daten: dict) -> str:
    symbol = {VERDIKT_OK: "✅", VERDIKT_KNAPP: "⚠️",
              VERDIKT_ERSCHOEPFT: "🛑"}[daten["verdikt"]]
    zeilen = [f"{symbol} Themennachschub: {daten['befund']}"]
    if daten["verdikt"] != VERDIKT_OK:
        zeilen.append(
            f"   AUTO frei {daten['frei_auto']} · Fachfreigabe frei "
            f"{daten['frei_fachfreigabe']} · belegt {daten['themen_belegt']}/"
            f"{daten['themen_gesamt']} · im Cooldown "
            f"{daten['themen_im_cooldown']}")
        zeilen.append(
            "   Was jetzt hilft: Themen mit Titel, drei Keywords und "
            "passendem /go/-Ziel in data/topics.yaml ergänzen (keine "
            "Versicherungs-, Kredit-, Renten- oder Baufi-Themen – die "
            "gehören in die Fachfreigabe-Bahn). Prüfen mit "
            "`python3 scripts/engine_capacity.py`.")
    for w in daten["warnungen"]:
        zeilen.append(f"   ⚠️ {w}")
    return "\n".join(zeilen)


# ---------------------------------------------------------------------------
#  Sabotage-Schutz
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    """Prüft das Urteil, nicht die Welt: Zahlen und Klassen, keine Modelle."""
    import tempfile

    fehler: list[str] = []

    def erwarte(bedingung, meldung):
        if not bedingung:
            fehler.append(meldung)

    # Neutrale, eindeutig AUTO-fähige Titel (kein YMYL-Muster, kein Pillar,
    # damit allein der Text über die Bahn entscheidet – wie im Betrieb).
    auto_titel = [
        "Kühlschrank reinigen", "Balkon bepflanzen", "Fahrradkette ölen",
        "Vorratsglas beschriften", "Küchenschrank ausmisten",
        "Teppich klopfen", "Blumen gießen", "Heftklammern sortieren",
        "Brot backen", "Socken stopfen", "Regal anbringen",
        "Lampe austauschen", "Kissen waschen", "Fenster putzen",
        "Schublade ölen", "Besen ausklopfen",
    ]
    hoch_titel = [
        "Hausratversicherung für Familien",
        "Risikolebensversicherung richtig bemessen",
        "Berufsunfähigkeitsversicherung prüfen",
        "Günstigen Ratenkredit vergleichen",
    ]

    with tempfile.TemporaryDirectory() as tmp:
        posts = Path(tmp) / "posts"
        posts.mkdir()
        ledger = Path(tmp) / "ledger.json"      # existiert nicht = keine Sperren
        env = {"MIN_ARTIKEL_PRO_TAG": "2", ENV_HORIZON: "5"}

        # ST1 – Gesunder Vorlauf (16 Themen / 2 pro Tag = 8 Tage ≥ 5): ok.
        daten = lage(topics=[{"title": t} for t in auto_titel],
                     posts_dir=posts, ledger=ledger, env=env)
        erwarte(daten["verdikt"] == VERDIKT_OK,
                f"ST1: 8 Tage Vorlauf bei Mindestvorlauf 5 muss ok sein "
                f"({daten['verdikt']})")
        erwarte(daten["vorlauf_tage"] == 8.0,
                f"ST1: Vorlauf falsch gerechnet ({daten['vorlauf_tage']})")

        # ST2 – Unter dem Mindestvorlauf: knapp, nicht erschöpft.
        daten = lage(topics=[{"title": t} for t in auto_titel[:8]],
                     posts_dir=posts, ledger=ledger, env=env)
        erwarte(daten["verdikt"] == VERDIKT_KNAPP,
                f"ST2: 4 Tage bei Mindestvorlauf 5 muss 'knapp' sein "
                f"({daten['verdikt']})")

        # ST3 – DER REALE BEFUND VOM 25.10.2026: frei ist nur, was die
        #       Fachfreigabe-Bahn nie automatisch ausliefern darf. Der
        #       Befund MUSS das benennen – sonst schickt er die Redaktion
        #       wieder auf die falsche Fährte (KI, Provider, Gate).
        daten = lage(topics=[{"title": t} for t in hoch_titel],
                     posts_dir=posts, ledger=ledger, env=env)
        erwarte(daten["verdikt"] == VERDIKT_ERSCHOEPFT,
                "ST3: leere AUTO-Bahn muss 'erschoepft' sein")
        erwarte(daten["frei_auto"] == 0 and daten["frei_fachfreigabe"] > 0,
                "ST3: Fachfreigabe-Themen dürfen nicht in die AUTO-Bahn zählen")
        erwarte("FACHFREIGABE" in daten["befund"].upper(),
                f"ST3: Befund nennt die Fachfreigabe-Bahn nicht: "
                f"{daten['befund']!r}")

        # ST4 – Echter Totalausfall: belegt + Cooldown, kein Bahn-Thema.
        daten = lage(topics=[{"title": t} for t in auto_titel[:3]],
                     posts_dir=posts, ledger=ledger, env={"THEMEN_HORIZON_TAGE": "abc"})
        erwarte(daten["mindestvorlauf_tage"] == HORIZON_TAGE_DEFAULT,
                "ST4: kaputter Env-Wert muss auf den Default fallen")
        erwarte(any(ENV_HORIZON in w for w in daten["warnungen"]),
                "ST4: geklemmter/ignorierter Env-Wert muss gemeldet werden")

        # ST5 – Der Bericht ist die Botschaft: ein grüner Vorlauf darf keine
        #       Nachschub-Aufforderung enthalten (kein Dauer-Alarm).
        gruen = lage(topics=[{"title": t} for t in auto_titel],
                     posts_dir=posts, ledger=ledger, env=env)
        erwarte("data/topics.yaml" not in bericht(gruen),
                "ST5: grüner Vorlauf enthält trotzdem eine Aufforderung")
        rot = lage(topics=[{"title": t} for t in hoch_titel],
                   posts_dir=posts, ledger=ledger, env=env)
        erwarte("data/topics.yaml" in bericht(rot),
                "ST5: roter Vorlauf nennt den Handlungsort nicht")

    if fehler:
        print("🛑 THEMEN-NACHSCHUB-WACHE: SELBSTTEST FEHLGESCHLAGEN:")
        for f in fehler:
            print(f"   - {f}")
        return 2
    print("✅ Themen-Nachschub-Wache: Selbsttest grün (Vorlauf in Tagen, "
          "Bahn-Trennung, Env-Klemmung, Bericht ohne Dauer-Alarm).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Vorlauf der AUTO-Bahn in Produktionstagen")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--warn-only", action="store_true",
                    help="nie Exit 1 – für Läufe, die nur berichten sollen")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return run_selftest()

    daten = lage()
    if args.json:
        print(json.dumps(daten, ensure_ascii=False, indent=2))
    else:
        print(bericht(daten))
    if args.warn_only:
        return 0
    return 1 if daten["verdikt"] != VERDIKT_OK else 0


if __name__ == "__main__":
    raise SystemExit(main())
