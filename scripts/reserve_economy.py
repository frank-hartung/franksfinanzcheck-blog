#!/usr/bin/env python3
"""
reserve_economy.py – EIN Besitzer für die Zahlen der Content-Reserve.
=====================================================================

WARUM ES DIESE DATEI GIBT (26.09.2026, Issue #393)
--------------------------------------------------
Der Vorrat kannte seine eigene Größe dreimal – an drei Orten, die nichts
voneinander wussten:

  * `.github/workflows/content-reserve.yml` → `RESERVE_TARGET` (Default 6)
  * `data/reserve-readiness.json`           → Feld `target`, vom Lauf selbst
                                              geschrieben
  * `scripts/bot_watchdog.py`               → `minimum = 4`, hart codiert

Daraus folgten zwei Fehler, die sich gegenseitig verdeckt haben:

1. SELBSTGESETZTE MESSLATTE.
   `reserve_gate.evaluate()` und `reserve_converge.cert_state()` lasen das
   Ziel AUS DEM ZERTIFIKAT – also aus genau dem Artefakt, über das sie
   urteilen sollten. Ein Lauf, der nur 4 Kandidaten schaffte, schrieb
   `target: 4`; der harte End-Gate bestätigte danach „✅ 4/4 gate-fertig".
   Schlimmer: die Konvergenz reichte diese 4 als `RESERVE_TARGET` an ihre
   Kindprozesse weiter, die sie erneut ins Zertifikat schrieben. Die
   abgesenkte Latte hielt sich damit selbst fest – das Produktionsziel aus
   dem Workflow wurde nie wieder gelesen. Eine Erhöhung der Variable wäre
   wirkungslos geblieben, bis zufällig jemand das Zertifikat löscht.

2. NULL PUFFER.
   Die Alarmschwelle des Watchdogs (4) und der Zielbestand (4) waren
   dieselbe Zahl. Ein Vorrat, der genau bis zur Alarmschwelle aufgefüllt
   wird, löst bei der NÄCHSTEN Veröffentlichung wieder Alarm aus – Ticket
   #393 kam deshalb per Konstruktion jeden Tag zurück.

Diese Datei ist die Antwort: EINE Quelle, zwei abgeleitete Zahlen, eine
erzwungene Invariante.

    ZIEL          – worauf die Produktionslinie auffüllt (`RESERVE_TARGET`).
    ALARMSCHWELLE – ab wann der Watchdog meldet. IMMER echt kleiner als das
                    Ziel (Ziel − Puffer). Genau dieser Abstand ist die
                    Hysterese, die das tägliche Flattern beendet.

Beim dokumentierten Ziel 6 ergibt sich die Alarmschwelle 4 – exakt der Wert,
der bisher hart im Watchdog stand. Die Alarm-Semantik bleibt also unverändert;
neu ist nur, dass die Zahl einen Besitzer hat und mitwandert, wenn das Ziel
sich ändert.

GRUNDREGELN
  * Das Zertifikat darf seine eigene Messlatte NICHT setzen. Sein Feld
    `target` ist Beweismittel („mit welcher Latte wurde gemessen?"), nie
    Vorgabe – `messlatten_drift()` macht daraus einen Befund.
  * Eine unlesbare oder absurde Konfiguration senkt das Ziel nie still: sie
    wird auf den erlaubten Bereich geklemmt UND meldet sich als Warnung.
  * Die Invariante `1 ≤ Alarmschwelle < Ziel` ist strukturell, nicht
    „per Konvention": sie wird gerechnet, nicht konfiguriert.

Nutzung:
    python3 scripts/reserve_economy.py            # Lage im Klartext
    python3 scripts/reserve_economy.py --json
    python3 scripts/reserve_economy.py --md
    python3 scripts/reserve_economy.py --selftest
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CERT = ROOT / "data" / "reserve-readiness.json"

# --------------------------------------------------------------------------
#  Die einzigen festen Zahlen der Reserve-Wirtschaft.
# --------------------------------------------------------------------------
#  ZIEL_DEFAULT: Stand der Doku und 16 Tage Zertifikats-Historie (10.09.–
#  26.09.2026). Bei 2–3 Artikeln je Publikationstag (Mo/Mi/Fr) trägt ein
#  voller Vorrat damit rund zwei Ausfalltage.
ZIEL_DEFAULT = 6
#  Ein „Vorrat" von 1 ist kein Vorrat – darunter gibt es keine Hysterese mehr.
ZIEL_MIN = 2
#  Deckel gegen einen Tippfehler, der die KI-Kosten explodieren ließe.
ZIEL_MAX = 60
#  Abstand zwischen Ziel und Alarm. 2 ≈ ein Publikationstag (2–3 Artikel):
#  Ein normaler Veröffentlichungstag darf den Vorrat NICHT in den Alarm
#  drücken, ein zweiter ohne Nachschub schon.
PUFFER_DEFAULT = 2
PUFFER_MIN = 1

ENV_ZIEL = "RESERVE_TARGET"
ENV_PUFFER = "RESERVE_PUFFER"


def _zahl_aus_env(name: str, default: int, minimum: int, maximum: int,
                  warnungen: list[str], env: dict | None = None) -> int:
    """Eine Zahl aus der Umgebung – geklemmt, nie still verschluckt.

    Fail-loud statt fail-silent: Jede Korrektur landet in `warnungen` und
    damit im Lauf-Log. Ein leerer String zählt als „nicht gesetzt" (GitHub
    Actions liefert für eine nicht existierende Variable exakt das).
    """
    quelle = os.environ if env is None else env
    roh = quelle.get(name)
    if roh is None or str(roh).strip() == "":
        return default
    try:
        wert = int(str(roh).strip())
    except (TypeError, ValueError):
        warnungen.append(
            f"{name}={roh!r} ist keine ganze Zahl – es gilt der Default "
            f"{default}.")
        return default
    if wert < minimum:
        warnungen.append(
            f"{name}={wert} liegt unter dem Minimum {minimum} – auf "
            f"{minimum} angehoben (ein Ziel darf nie still unter das "
            f"Sinnvolle fallen).")
        return minimum
    if wert > maximum:
        warnungen.append(
            f"{name}={wert} liegt über dem Maximum {maximum} – auf "
            f"{maximum} gedeckelt (Schutz vor KI-Kosten durch Tippfehler).")
        return maximum
    return wert


def ziel(warnungen: list[str] | None = None, env: dict | None = None) -> int:
    """Zielbestand der Produktionslinie – die EINE Wahrheit.

    Quelle ist ausschließlich die Umgebung (`RESERVE_TARGET`, im Workflow aus
    `vars.RESERVE_TARGET`). Bewusst NICHT das Zertifikat: das ist das
    gemessene Artefakt und darf seine eigene Note nicht vergeben.
    """
    return _zahl_aus_env(ENV_ZIEL, ZIEL_DEFAULT, ZIEL_MIN, ZIEL_MAX,
                         warnungen if warnungen is not None else [], env)


def puffer(warnungen: list[str] | None = None, env: dict | None = None) -> int:
    """Abstand zwischen Ziel und Alarmschwelle (Hysterese)."""
    return _zahl_aus_env(ENV_PUFFER, PUFFER_DEFAULT, PUFFER_MIN, ZIEL_MAX,
                         warnungen if warnungen is not None else [], env)


def alarmschwelle(warnungen: list[str] | None = None,
                  env: dict | None = None) -> int:
    """Ab wann der Watchdog meldet – abgeleitet, nie separat konfiguriert.

    Invariante (strukturell, nicht per Konvention):

        1 ≤ alarmschwelle() < ziel()

    Das obere Ende ist der eigentliche Fix zu #393: Wäre die Schwelle gleich
    dem Ziel, würde die Linie exakt bis zur Alarmgrenze auffüllen und die
    nächste Veröffentlichung löste sofort wieder Alarm aus.
    """
    w = warnungen if warnungen is not None else []
    z = ziel(w, env)
    p = puffer(w, env)
    return min(max(1, z - p), z - 1)


# --------------------------------------------------------------------------
#  Messlatten-Drift: Das Zertifikat als Zeuge, nicht als Gesetzgeber.
# --------------------------------------------------------------------------
def zertifikat_ziel(cert: Path | dict | None = None) -> int | None:
    """Mit welcher Latte wurde das vorliegende Zertifikat gemessen?

    Rückgabe `None`, wenn das Zertifikat fehlt, unlesbar ist oder kein
    verwertbares `target` trägt – „unbekannt" ist eine eigene Aussage und
    wird nirgends als „passt schon" gelesen.
    """
    daten: dict | None = None
    if isinstance(cert, dict):
        daten = cert
    else:
        pfad = CERT if cert is None else Path(cert)
        try:
            geladen = json.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if isinstance(geladen, dict):
            daten = geladen
    if not isinstance(daten, dict):
        return None
    roh = daten.get("target")
    if isinstance(roh, bool) or not isinstance(roh, (int, float, str)):
        return None
    try:
        return int(str(roh).strip())
    except (TypeError, ValueError):
        return None


def messlatten_drift(cert_ziel: int | None, produktions_ziel: int | None = None
                     ) -> str | None:
    """Befundtext, wenn das Zertifikat gegen eine NIEDRIGERE Latte gemessen hat.

    Genau dieser Fall stand am 26.09.2026 im Repo: Produktionsziel 6,
    Zertifikat `target: 4`, End-Gate „✅ 4/4". Ein höheres Zertifikatsziel
    ist harmlos (dann wurde strenger gemessen als verlangt) und wird nicht
    gemeldet.
    """
    if cert_ziel is None:
        return None
    soll = ziel() if produktions_ziel is None else produktions_ziel
    if cert_ziel >= soll:
        return None
    return (f"MESSLATTE: Das Zertifikat wurde gegen Ziel {cert_ziel} gemessen, "
            f"die Produktionslinie verlangt {soll}. Ein Zertifikat setzt seine "
            f"eigene Latte nicht – der nächste Lauf von "
            f"`scripts/reserve_readiness.py` stempelt sie auf {soll} um.")


def lage(cert: Path | None = None) -> dict:
    """Gesamtbild für Reporte, Watchdog und Lauf-Zusammenfassungen."""
    warnungen: list[str] = []
    z = ziel(warnungen)
    p = puffer(warnungen)
    a = alarmschwelle(warnungen)
    cz = zertifikat_ziel(CERT if cert is None else cert)
    drift = messlatten_drift(cz, z)
    if drift:
        warnungen.append(drift)
    return {
        "ziel": z,
        "puffer": p,
        "alarmschwelle": a,
        "zertifikat_ziel": cz,
        "drift": drift,
        "warnungen": warnungen,
        "quelle_ziel": (f"Umgebung {ENV_ZIEL}"
                        if str(os.environ.get(ENV_ZIEL, "")).strip()
                        else f"Default {ZIEL_DEFAULT}"),
    }


def als_markdown(daten: dict | None = None) -> str:
    d = lage() if daten is None else daten
    zeilen = [
        "## 📦 Content-Reserve – Zielbestand und Alarmschwelle",
        "",
        f"- **Ziel:** {d['ziel']} Kandidaten ({d['quelle_ziel']})",
        f"- **Alarmschwelle:** unter {d['alarmschwelle']} "
        f"(Ziel − Puffer {d['puffer']})",
        f"- **Zertifikat gemessen gegen:** "
        f"{d['zertifikat_ziel'] if d['zertifikat_ziel'] is not None else 'unbekannt'}",
    ]
    for w in d["warnungen"]:
        zeilen.append(f"- ⚠️ {w}")
    return "\n".join(zeilen) + "\n"


# --------------------------------------------------------------------------
#  Selbsttest – friert die Invariante ein, die #393 dauerhaft schließt.
# --------------------------------------------------------------------------
def run_selftest() -> int:
    fehler: list[str] = []
    gesichert = {k: os.environ.get(k) for k in (ENV_ZIEL, ENV_PUFFER)}

    def setze(**kv):
        for k, v in kv.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = str(v)

    try:
        # 1) Default-Lage: Ziel 6 → Alarm 4 (Semantik des alten Hardcodes).
        setze(**{ENV_ZIEL: None, ENV_PUFFER: None})
        if ziel() != ZIEL_DEFAULT:
            fehler.append(f"Default-Ziel {ziel()} statt {ZIEL_DEFAULT}")
        if alarmschwelle() != 4:
            fehler.append(
                f"Ziel 6 muss Alarmschwelle 4 ergeben (alter Watchdog-Wert), "
                f"ist {alarmschwelle()}")

        # 2) Der Fall aus #393: Ziel 4 darf NIE Alarmschwelle 4 ergeben.
        setze(**{ENV_ZIEL: 4})
        if alarmschwelle() >= 4:
            fehler.append(
                "Ziel 4 mit Alarmschwelle 4 – genau der Null-Puffer, der #393 "
                "täglich neu geöffnet hat")
        if alarmschwelle() != 2:
            fehler.append(f"Ziel 4 → Alarm 2 erwartet, ist {alarmschwelle()}")

        # 3) Die Invariante hält über den gesamten erlaubten Bereich – auch
        #    bei absurdem Puffer. Kein Wertepaar darf sie brechen.
        for z in range(ZIEL_MIN, 25):
            for p in (1, 2, 3, 7, 99):
                setze(**{ENV_ZIEL: z, ENV_PUFFER: p})
                a = alarmschwelle()
                if not (1 <= a < z):
                    fehler.append(
                        f"Invariante verletzt: Ziel {z}, Puffer {p} → "
                        f"Alarm {a} (erwartet 1 ≤ a < {z})")

        # 4) Müll in der Umgebung senkt das Ziel nicht still.
        for murks in ("", "   ", "sechs", "6.5", None):
            setze(**{ENV_ZIEL: murks, ENV_PUFFER: None})
            if ziel() != ZIEL_DEFAULT:
                fehler.append(f"{murks!r} hätte Default {ZIEL_DEFAULT} ergeben "
                              f"müssen, ergab {ziel()}")
        w: list[str] = []
        setze(**{ENV_ZIEL: "sechs"})
        ziel(w)
        if not w:
            fehler.append("Unlesbares Ziel wurde still verschluckt (keine Warnung)")

        # 5) Klemmen statt kippen – nach unten UND nach oben, jeweils laut.
        w = []
        setze(**{ENV_ZIEL: 1})
        if ziel(w) != ZIEL_MIN or not w:
            fehler.append(f"Ziel 1 muss auf {ZIEL_MIN} angehoben werden – laut")
        w = []
        setze(**{ENV_ZIEL: 10_000})
        if ziel(w) != ZIEL_MAX or not w:
            fehler.append(f"Ziel 10000 muss auf {ZIEL_MAX} gedeckelt werden – laut")
        w = []
        setze(**{ENV_ZIEL: -3})
        if ziel(w) != ZIEL_MIN:
            fehler.append("negatives Ziel muss angehoben werden")

        # 6) Messlatten-Drift: niedrigeres Zertifikatsziel ist ein Befund,
        #    ein höheres oder gleiches nicht, „unbekannt" nie stillschweigend.
        setze(**{ENV_ZIEL: 6, ENV_PUFFER: None})
        if not messlatten_drift(4, 6):
            fehler.append("Zertifikat mit Ziel 4 gegen Produktionsziel 6 muss "
                          "als Drift auffallen")
        if messlatten_drift(6, 6) or messlatten_drift(8, 6):
            fehler.append("gleiches/höheres Zertifikatsziel ist keine Drift")
        if messlatten_drift(None, 6) is not None:
            fehler.append("unbekanntes Zertifikatsziel ist keine Drift-Meldung")

        # 7) zertifikat_ziel() liest Zahlen, keine Wahrheiten – und stürzt
        #    bei kaputten Dateien nicht ab.
        if zertifikat_ziel({"target": 4}) != 4:
            fehler.append("zertifikat_ziel liest `target` nicht")
        if zertifikat_ziel({"target": "5"}) != 5:
            fehler.append("zertifikat_ziel liest `target` als String nicht")
        for kaputt in ({}, {"target": None}, {"target": True}, {"target": "x"},
                       {"target": []}):
            if zertifikat_ziel(kaputt) is not None:
                fehler.append(f"kaputtes Zertifikat {kaputt} muss None liefern")
        if zertifikat_ziel(Path("/nicht/vorhanden/cert.json")) is not None:
            fehler.append("fehlendes Zertifikat muss None liefern")

        # 8) lage() ist reine Auskunft – niemals ein Schreiber (C15).
        setze(**{ENV_ZIEL: 6})
        d = lage(Path("/nicht/vorhanden/cert.json"))
        if d["ziel"] != 6 or d["alarmschwelle"] != 4:
            fehler.append(f"lage() inkonsistent: {d}")
        if "Content-Reserve" not in als_markdown(d):
            fehler.append("Markdown-Bericht ohne Überschrift")
    finally:
        for k, v in gesichert.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    if fehler:
        print("🛑 SELBSTTEST reserve_economy FEHLGESCHLAGEN:")
        for f in fehler:
            print(f"   - {f}")
        return 2
    print("✅ Selbsttest reserve_economy: Invariante „1 ≤ Alarm < Ziel\" hält "
          "über alle Ziel/Puffer-Paare, Müll wird laut geklemmt, "
          "Messlatten-Drift wird erkannt.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Zielbestand und Alarmschwelle der Content-Reserve (SSOT)")
    ap.add_argument("--selftest", action="store_true",
                    help="interne Tests ausführen")
    ap.add_argument("--json", action="store_true", help="Lage als JSON")
    ap.add_argument("--md", action="store_true", help="Lage als Markdown")
    args = ap.parse_args()
    if args.selftest:
        return run_selftest()
    d = lage()
    if args.json:
        print(json.dumps(d, ensure_ascii=False, indent=2))
        return 0
    if args.md:
        print(als_markdown(d), end="")
        return 0
    print(f"Zielbestand      : {d['ziel']}  ({d['quelle_ziel']})")
    print(f"Puffer           : {d['puffer']}")
    print(f"Alarmschwelle    : unter {d['alarmschwelle']}")
    print(f"Zertifikat-Ziel  : "
          f"{d['zertifikat_ziel'] if d['zertifikat_ziel'] is not None else 'unbekannt'}")
    for w in d["warnungen"]:
        print(f"⚠ {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
