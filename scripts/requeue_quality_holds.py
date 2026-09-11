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

Dieses Skript ist die gezielte Selbstheilung für genau diese Klasse:
  - NUR Holds mit `cadence_grund`, das mit „quality-score“ beginnt,
    werden neu bewertet (alles andere bleibt unangetastet).
  - Liegt der NEUE Score ≥ 0.80 (Review-Schwelle), wird der Hold in eine
    Re-Queue verwandelt (cadence_wait: true) – der Artikel durchläuft beim
    nächsten Slot den VOLLEN Gate-Durchlauf (publish_gate STRICT +
    publication_release), bevor er live geht.
  - Bleibt der Score < 0.80, bleibt der Hold bestehen (echter Bedarf).

Nutzung:
  python3 scripts/requeue_quality_holds.py            # Report (weich)
  python3 scripts/requeue_quality_holds.py --fix      # Re-Queue schreiben
  python3 scripts/requeue_quality_holds.py --selftest # Sabotage-Schutz
"""
import os
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

REQUEUE_BAR = 0.80  # THRESHOLD_REVIEW: darunter bleibt „human review“ sinnvoll


def is_quality_hold(grund):
    """Ein bewusster quality-score-Hold? (nur diese Klasse wird angefasst)."""
    return bool(grund) and str(grund).startswith("quality-score")


def should_requeue(score):
    """Neu bewerteter Artikel ist reif genug für den vollen Gate-Durchlauf."""
    return score is not None and score >= REQUEUE_BAR


def evaluate(posts_dir=None):
    """Bewertet quality-score-Holds neu → (requeued, kept, errors).

    Rein lesend; schreibt NICHTS. `requeued`/`kept` sind Listen aus
    (slug, score) bzw. (slug, score, fehler).
    """
    import cadence_guard as cg
    import quality_score as qs

    requeued, kept, errors = [], [], []
    for p in cg.load_posts(posts_dir):
        if p.get("state") != "hold" or not is_quality_hold(p.get("grund")):
            continue
        try:
            score = qs.score_article(p["path"])["score"]
        except Exception as exc:  # noqa: BLE001 – nie am Scorer scheitern
            errors.append((p["slug"], None, str(exc)))
            continue
        if should_requeue(score):
            requeued.append((p["slug"], score))
        else:
            kept.append((p["slug"], score))
    return requeued, kept, errors


def fix(posts_dir=None):
    """Wandelt reife quality-score-Holds in Re-Queue (park_state.rearm)."""
    import cadence_guard as cg
    import park_state
    import quality_score as qs

    requeued, kept, errors = [], [], []
    for p in cg.load_posts(posts_dir):
        if p.get("state") != "hold" or not is_quality_hold(p.get("grund")):
            continue
        try:
            score = qs.score_article(p["path"])["score"]
        except Exception as exc:  # noqa: BLE001
            errors.append((p["slug"], None, str(exc)))
            continue
        if should_requeue(score):
            grund = (f"quality-hold aufgehoben (#251): Score {score:.3f} ≥ "
                     f"{REQUEUE_BAR:.2f} – Re-Queue für vollen Gate-Durchlauf")
            park_state.rearm(p["path"], grund)
            requeued.append((p["slug"], score))
        else:
            kept.append((p["slug"], score))
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

    print(f"Quality-Holds neu bewertet: {len(requeued)} reif → Re-Queue, "
          f"{len(kept)} bleiben gehalten, {len(errors)} Fehler.")
    for slug, score in requeued:
        print(f"  🟢 {slug}: Score {score:.3f} ≥ {REQUEUE_BAR:.2f} "
              f"→ {'cadence_wait: true gesetzt' if do_fix else 'Re-Queue möglich'}")
    for slug, score in kept:
        print(f"  🔴 {slug}: Score {score:.3f} < {REQUEUE_BAR:.2f} → Hold bleibt")
    for slug, _score, err in errors:
        print(f"  ⚠ {slug}: Bewertung fehlgeschlagen ({err})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
