#!/usr/bin/env python3
"""requeue_quality_holds.py – falsche quality-score-Holds selbstheilend requeuen.

WARUM (Issue #251, 11.09.2026):
================================
Die Content-Engine parkte Artikel mit `cadence_grund: "quality-score: …"`,
wenn der (damals defekte) Score unter 0.80 fiel. Zwei Score-Fehler erzeugten
diese Holds massenhaft:

  1. uniqueness 0.0 – die Fazit-/FAQ-Schablonen der Fazit-Schmiede wurden
     nicht aus dem Einzigartigkeits-Vergleich entfernt (→ jeder Artikel
     „kollidierte“ mit 10+ unverwandten Artikeln).
  2. spelling 0.00 – Wörterbuch-Lücken („Gasanbieterwechsel“, „abrücken“ …)
     wurden wie echte Tippfehler gewertet.

Beide Fehler sind behoben (template_boilerplate.py + quality_score.py). Die
bereits geparkten Artikel blieben aber als „hold“ liegen – hold wird von der
Kadenz-Wache bewusst NIE automatisch rearmt (Schutz vor echter Gate-Hemmung).

Dieses Skript ist die gezielte Selbstheilung für genau diese Klassen:
  - Holds mit `cadence_grund`, der mit „quality-score“ beginnt → neu bewertet
    gegen quality_score (Alles andere bleibt unangetastet).
  - Holds, deren Grund eine verhängte Zeicbenlänge meldet („Zeichenlänge“) →
    neu gemessen am Length-SSOT `length_policy` (15.09.2026, zweiter Fund).
    Anlass: zwei Artikel lagen seit 07.09. mit „publish-gate: Zeichenlänge
    (check_length.py) nicht bestanden“, obwohl sie längst 13.812 bzw.
    17.1xx Zeichen messen. Niemandem fiel es auf, weil check_length.py
    Entwürfe überspringt (`draft: true` → continue) und publish_gate nur
    Kandidaten des HEUTIGEN Datums prüft: ein Hold auf einem Entwurf wird von
    der Wache, die ihn setzte, nie wieder angefasst.
  - Liegt der NEUE Score ≥ 0.80 (Review-Schwelle) bzw. die Länge im Korridor,
    wird der Hold in eine Re-Queue verwandelt (cadence_wait: true) – der
    Artikel durchläuft beim nächsten Slot den VOLLEN Gate-Durchlauf
    (publish_gate STRICT + publication_release), bevor er live geht.
  - Bleibt die Ursache bestehen, bleibt der Hold (echter Bedarf).

Kein automatischer Publish: rearm setzt nur cadence_wait. Wer „hold“ bewusst
gesetzt hat (redaktioneller Grund, Duplikat-Verdacht), wird nicht angefasst.

Nutzung:
  python3 scripts/requeue_quality_holds.py            # Report (weich)
  python3 scripts/requeue_quality_holds.py --fix      # Re-Queue schreiben
  python3 scripts/requeue_quality_holds.py --selftest # Sabotage-Schutz
"""
import os
import sys
from pathlib import Path

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

REQUEUE_BAR = 0.80  # THRESHOLD_REVIEW: darunter bleibt „human review“ sinnvoll


def is_quality_hold(grund):
    """Ein bewusster quality-score-Hold? (nur diese Klasse wird angefasst)."""
    return bool(grund) and str(grund).startswith("quality-score")


def is_length_hold(grund):
    """Ein Länge-Hold des Publish-Gates? (zweite Klasse, 15.09.2026)

    Erkennung am Wort, nicht an der Zeile: der Gate-Text lautet
    „publish-gate: Zeichenlänge (check_length.py) nicht bestanden“, und die
    Präfix-Regel wie bei quality-score würde ihn verfehlen, sobald das Gate den
    Satz umformuliert – verfehlen wäre hier das Gefährliche (der Hold bliebe).
    """
    return bool(grund) and "Zeichenlänge" in str(grund)


def length_reif(text):
    """Länge neu gemessen am SSOT – Rückgabe (reif?, Belegtext).

    Bewusst NICHT über check_length.py: dessen collect() überspringt Entwürfe,
    und ein Länge-Hold gilt definitionell einem Entwurf.
    """
    import length_policy as lp

    _w, chars = lp.measure(text)
    floor, maxm = lp.POSTS["heal_chars"], lp.POSTS["fat_chars"]
    z = lambda n: f"{n:,}".replace(",", ".")   # 12345 -> 12.345 (nur Gruppen, kein Satzzeichen)
    if chars < floor:
        return False, f"{z(chars)} Zeichen < Floor {z(floor)}"
    if chars > maxm:
        return False, f"{z(chars)} Zeichen > Maximum {z(maxm)}"
    return True, (f"{z(chars)} Zeichen im Korridor (Floor {z(floor)}, "
                  f"Maximum {z(maxm)})")


def should_requeue(score):
    """Neu bewerteter Artikel ist reif genug für den vollen Gate-Durchlauf."""
    return score is not None and score >= REQUEUE_BAR


def _holds(cg, posts_dir=None):
    """Alle Holds, die diesem Skript gehören – quality-score oder Länge."""
    for p in cg.load_posts(posts_dir):
        grund = p.get("grund")
        if p.get("state") == "hold" and (is_quality_hold(grund) or is_length_hold(grund)):
            yield p


def bewertung(p, qs):
    """Nachbewertung eines Holds -> (reif?, Belegtext). Der Beleg kommt ins
    Frontmatter, deshalb muss er die Zahl nennen, die die Aufhebung trägt."""
    if is_quality_hold(p.get("grund")):
        score = qs.score_article(p["path"])["score"]
        return should_requeue(score), (f"Score {score:.3f} ≥ {REQUEUE_BAR:.2f}"
                                      if should_requeue(score)
                                      else f"Score {score:.3f} < {REQUEUE_BAR:.2f}")
    text = Path(p["path"]).read_text(encoding="utf-8")
    reif, beleg = length_reif(text)
    return reif, beleg


def evaluate(posts_dir=None):
    """Bewertet quality-score-Holds neu → (requeued, kept, errors).

    Rein lesend; schreibt NICHTS. `requeued`/`kept` sind Listen aus
    (slug, score) bzw. (slug, score, fehler).
    """
    import cadence_guard as cg
    import quality_score as qs

    requeued, kept, errors = [], [], []
    for p in _holds(cg, posts_dir):
        try:
            reif, beleg = bewertung(p, qs)
        except Exception as exc:  # noqa: BLE001 – nie am Scorer scheitern
            errors.append((p["slug"], None, str(exc)))
            continue
        (requeued if reif else kept).append((p["slug"], beleg))
    return requeued, kept, errors


def fix(posts_dir=None):
    """Wandelt reife quality-score-Holds in Re-Queue (park_state.rearm)."""
    import cadence_guard as cg
    import park_state
    import quality_score as qs

    requeued, kept, errors = [], [], []
    for p in _holds(cg, posts_dir):
        try:
            reif, beleg = bewertung(p, qs)
        except Exception as exc:  # noqa: BLE001
            errors.append((p["slug"], None, str(exc)))
            continue
        if reif:
            kind = ("quality-hold" if is_quality_hold(p.get("grund"))
                    else "length-hold")
            grund = (f"{kind} aufgehoben: {beleg} – Re-Queue für vollen "
                     f"Gate-Durchlauf (PR #289)")
            park_state.rearm(p["path"], grund)
            requeued.append((p["slug"], beleg))
        else:
            kept.append((p["slug"], beleg))
    return requeued, kept, errors


def run_selftest() -> list:
    fehler = []
    if not is_quality_hold("quality-score: Score 0.70 < 0.80 (…) – Human-Review"):
        fehler.append("quality-score-Hold wird nicht erkannt")
    if is_quality_hold("duplikat (same-day-twin …)"):
        fehler.append("fremder Hold wird fälschlich als quality-score-Hold erkannt")
    if is_quality_hold(""):
        fehler.append("leerer Grund wird als quality-score-Hold erkannt")
    if not should_requeue(0.80) or not should_requeue(0.85):
        fehler.append("Score an der Review-Schwelle wird nicht requeued")
    if should_requeue(0.79) or should_requeue(None):
        fehler.append("Score unter der Review-Schwelle/None wird fälschlich requeued")
    # zweite Klasse: Länge
    gate_grund = "publish-gate: Zeichenlänge (check_length.py) nicht bestanden"
    if not is_length_hold(gate_grund):
        fehler.append("Zeichenlänge-Hold des Publish-Gates wird nicht erkannt")
    if is_length_hold("quality-score: Score 0.70 < 0.80") or is_length_hold(None):
        fehler.append("fremder Grund wird als Zeichenlänge-Hold erkannt")
    if is_quality_hold(gate_grund):
        fehler.append("Zeichenlänge-Hold wird fälschlich als quality-score-Hold erkannt")
    for n, erwartung in ((2000, False), (2600, True), (30000, False)):
        text = "wort " * n
        reif, beleg = length_reif(text)
        if reif != erwartung:
            fehler.append(f"length_reif({n} Wörter): reif={reif}, erwartet "
                          f"{erwartung} ({beleg})")
        if "Zeichen" not in beleg:
            fehler.append(f"length_reif({n} Wörter) nennt keine Zahl im Beleg: {beleg}")
    return fehler


def main() -> int:
    args = sys.argv[1:]
    if "--selftest" in args:
        errs = run_selftest()
        if errs:
            print("🛑 REQUEUE-QUALITY-HOLDS-SELFTEST FEHLGESCHLAGEN:")
            for e in errs:
                print("  -", e)
            return 2
        print("✅ Requeue-quality-holds-Selftest bestanden (Erkennung, Schwellen).")
        return 0

    do_fix = "--fix" in args
    requeued, kept, errors = (fix() if do_fix else evaluate())

    print(f"Holds neu bewertet: {len(requeued)} reif → Re-Queue, "
          f"{len(kept)} bleiben gehalten, {len(errors)} Fehler.")
    for slug, beleg in requeued:
        print(f"  🟢 {slug}: {beleg} "
              f"→ {'cadence_wait: true gesetzt' if do_fix else 'Re-Queue möglich'}")
    for slug, beleg in kept:
        print(f"  🔴 {slug}: {beleg} → Hold bleibt")
    for slug, _score, err in errors:
        print(f"  ⚠ {slug}: Bewertung fehlgeschlagen ({err})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
