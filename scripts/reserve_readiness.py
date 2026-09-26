#!/usr/bin/env python3
"""Preflight the stock on quiet days. Count proven articles, not reserve flags.

Zertifiziert die Reife der Reserve-Pool-Kandidaten mit den ECHTEN
Produktions-Gates (quality_score >= 0.85 + publish_gate STRICT + hugo-Render-
Beweis) und schreibt hash-gesicherte Zertifikate nach
data/reserve-readiness.json. Ein Zertifikat gilt nur für EXAKT diesen
Datei-Inhalt (sha256) – jede spätere Änderung macht den Kandidaten wieder
„offen“ (wird von engine_generate/_reserve_topup und reserve_finisher
respektiert).

Reparatur 08.09.2026 (Issue #224): Diagnose pro Kandidat (Score-Teile bzw.
Gate-Grund) wird im JSON und auf stdout mitgeliefert, damit der tägliche
Lauf bei „Stock shortage“ die konkrete Ursache nennt statt nur 0/6.

Reparatur 15.09.2026 (Issue #295, Run 34967470666): Die Diagnose war trotzdem
wertlos, weil der häufigste Fall nur den Platzhalter
„publish_gate/hugo abgelehnt (STRICT dry-run) – Details im Workflow-Log“
schrieb. Die konkreten Funde (hier: „Kein vollständiger Markdown-Link in
CTA-Zeile ('Spar-Tipp zwischendurch')“) standen ausschließlich im Lauf-Log –
und Lauf-Logs verfallen. Die Gate-Ausgabe wird jetzt MITGELESEN: `reason`
nennt den ersten konkreten Fund, `details` alle. Zusätzlich übergibt die
Zertifizierung jeden nicht heilbaren Fund an reserve_quarantine.py, damit ein
einzelner Dauer-Blocker den Zielbestand nicht mehr unerreichbar macht.
"""
import contextlib
import hashlib
import io
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import reserve_pool as rp  # noqa: E402
from publication_release import accept_candidate  # noqa: E402


def target() -> int:
    try:
        return int(os.environ.get("RESERVE_TARGET") or "6")
    except ValueError:
        return 6


def capture_gate(index: Path) -> tuple[bool, str]:
    """(ready, Gate-Ausgabe). Die Ausgabe wird mitgelesen UND weitergereicht.

    Warum nicht einfach verschlucken? Der Workflow-Log ist die einzige Stelle,
    an der die Redaktion die volle Gate-Ausgabe sieht – sie darf durch die
    Zertifikats-Diagnose nicht verloren gehen.
    """
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ready = accept_candidate(index)
    text = buf.getvalue()
    if text:
        print(text, end="")
    return bool(ready), text


def gate_findings(text: str) -> list[str]:
    """Konkrete Gate-Gründe aus der publish_gate-Ausgabe.

    publish_gate meldet Ablehnungen als Block:
        🛑 <slug>: WIRD VERWORFEN (kein Artefakt, …)
           - Affiliate-Link-Integrität nicht bestanden …: <konkreter Fund>
    Genau diese Zeilen sind die verwertbare Diagnose – alles andere
    (Fortschrittsmeldungen, Hugo-Statistik) gehört nicht ins Zertifikat.
    """
    out: list[str] = []
    aktiv = False
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        kopf = any(z in stripped for z in
                   ("🛑", "⛔", "WIRD VERWORFEN", "nicht bereit", "scheitern"))
        if kopf:
            aktiv = True
            out.append(stripped)
            continue
        if aktiv and stripped.startswith("- "):
            out.append(stripped[2:].strip())
            continue
        if aktiv and not line[:1].isspace():
            aktiv = False
    return list(dict.fromkeys(out))


def grund_aus_funden(funde: list[str]) -> str:
    """Erster verwertbarer Fund als Kurzbegründung (ohne Überschriftszeile)."""
    for fund in funde:
        if any(z in fund for z in ("WIRD VERWORFEN", "scheitern", "🛑", "⛔")):
            continue
        return fund[:240]
    return (funde[0][:240] if funde else
            "publish_gate/hugo abgelehnt (STRICT dry-run) – Details im Lauf-Log")


def score_diagnosis(index) -> dict | None:
    """Lesende Score-Diagnose (weakest parts) – bevor das harte Gate läuft."""
    try:
        import quality_score as qs
        return qs.score_article(str(index))
    except Exception as exc:  # noqa: BLE001 – Diagnose darf nie blockieren
        return {"fehler": str(exc)}


def prune_stale_rows(rows: list[dict]) -> list[dict]:
    """Zählt nur echte Reserve-Entwürfe – nie bereits LIVE geschaltete.

    Premium-Fix 15.09.2026 (#287/#295): Nach publish_to_min bleiben die
    frisch live geschalteten Artikel fälschlich im Zertifikat (ready=true),
    weil der nächste Lauf sie nicht mehr in reserve_drafts() sieht und die
    alte JSON-Datei unangetastet ließ. Der Gate las dann 6/6, obwohl der
    Pool real 4 Entwürfe hatte. Jeder Lauf schreibt das Zertifikat neu aus
    den aktuellen Entwürfen – veröffentlichte Slugs fallen damit weg.
    """
    return [r for r in rows if r.get("slug")]


def main():
    # BESTANDS-WÄCHTER (26.09.2026, #387): Bevor irgendetwas über den Pool
    # geurteilt wird, bekommt er zurück, was ihm gehört. Fremde Umschreibungen
    # (Agenten, KI-Redaktion, Heiler) hatten am 25.09. zwei zertifizierte
    # Kandidaten die `reserve`-Fahne gekostet – der Vorrat schrumpfte lautlos
    # von 8 auf 3 und der End-Gate wurde rot, obwohl beide Entwürfe im Repo
    # lagen. Best-effort, nie blockierend.
    try:
        import reserve_custody
        reserve_custody.heal_quiet()
    except Exception as exc:  # noqa: BLE001 – Absicherung, kein Gate
        print(f"⚠ Bestands-Wächter übersprungen: {exc}")

    rows = []
    # Nur aktuelle Reserve-Entwürfe (draft+reserve). Bereits veröffentlichte
    # Kandidaten (reserve_published) erscheinen hier bewusst nicht mehr.
    for index in rp.reserve_drafts():
        original = index.read_text(encoding="utf-8")
        diag = score_diagnosis(index)
        ready, reason, details = False, None, []
        try:
            rp.publish_one(index)
            ready, gate_text = capture_gate(index)
            if not ready:
                details = gate_findings(gate_text)
                if diag and diag.get("score") is not None \
                        and diag["score"] < 0.85:
                    schwach = ", ".join(
                        f"{k} {v:.2f}" for k, v in sorted(
                            diag.get("parts", {}).items(),
                            key=lambda kv: kv[1])[:3])
                    reason = (f"quality-score {diag['score']} < 0.85 "
                              f"(schwach: {schwach})")
                else:
                    # REPARATUR 15.09.2026 (#295): der KONKRETE Gate-Fund,
                    # nicht der Platzhalter („Details im Workflow-Log“).
                    reason = grund_aus_funden(details)
        except Exception as exc:  # noqa: BLE001 – nie am Gate scheitern
            ready, reason = False, f"Gate-Ausnahme: {exc}"
        finally:
            index.write_text(original, encoding="utf-8")
        row = {"slug": index.parent.name, "ready": ready,
               "sha256": hashlib.sha256(original.encode()).hexdigest()}
        if reason:
            row["reason"] = reason
        if details:
            row["details"] = details
        if diag:
            row["score"] = diag.get("score")
            row["parts"] = diag.get("parts")
        rows.append(row)

    # REPARATUR 15.09.2026 (#295): Ein Kandidat, den kein Heiler reparieren
    # kann, darf den Zielbestand nicht dauerhaft unerreichbar machen. Nach
    # RESERVE_QUARANTINE_HITS Läufen mit demselben Fund verlässt er den Pool
    # (bleibt als BLOCKIERT im Bestand) und gibt den Platz für Nachschub frei.
    blocked = []
    try:
        import reserve_quarantine as rq
        blocked = rq.record(rows)
    except Exception as exc:  # noqa: BLE001 – Quarantäne darf nie blockieren
        print(f"⚠ Reserve-Quarantäne nicht ausführbar: {exc}")
    if blocked:
        blocked_slugs = {b["slug"] for b in blocked}
        rows = [r for r in rows if r["slug"] not in blocked_slugs]
        print("\n🧱 Dauerhaft blockierte Kandidaten aus dem Pool genommen "
              "(Entwurf bleibt im Bestand, draft_triage zeigt den Grund):")
        for b in blocked:
            print(f"   - {b['slug']}: {b['grund']} "
                  f"({b['hits']} Läufe mit demselben Fund)")

    rows = prune_stale_rows(rows)
    goal = target()
    ready_count = sum(1 for r in rows if r.get("ready"))
    # ready-Feld und candidates-Liste sind dieselbe Wahrheit – nie auseinander
    # laufen lassen (früher: ready-Zähler aus dem alten Lauf + neue Liste).
    report = {
        "target": goal,
        "ready": ready_count,
        "pool_size": len(rows),
        "generated_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "candidates": rows,
    }
    if blocked:
        # Der Pool-Stand ist ohne diese Information nicht zu verstehen: Ein
        # 5/6 nach einer Quarantäne heißt „ein Kandidat wurde ausgemustert“,
        # nicht „die Produktion ist eingeschlafen“.
        report["blocked"] = [{"slug": b["slug"], "grund": b["grund"],
                              "hits": b["hits"]} for b in blocked]
    (ROOT / "data" / "reserve-readiness.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    if ready_count < goal:
        print(f"\n🛑 RESERVE-ENGPAß: {ready_count}/{goal} Kandidaten "
              f"gate-fertig (Pool {len(rows)} Entwürfe).")
        for r in rows:
            mark = "✅" if r["ready"] else "⛔"
            extra = f" – {r.get('reason', '')}" if r.get("reason") else ""
            score = f" | Score {r.get('score')}" if "score" in r else ""
            print(f"   {mark} {r['slug']}{score}{extra}")
            for detail in (r.get("details") or [])[1:]:
                print(f"        · {detail}")
        print("   Nächster Schritt: Heiler-Kette via "
              "`python3 scripts/reserve_finisher.py --finish` (im Workflow "
              "automatisch) und/oder Redaktion prüft die Diagnose.")
    else:
        print(f"\n✅ Reserve-Pool vollständig gate-fertig ({ready_count}/{goal}).")
    return 0 if ready_count >= goal else 1


if __name__ == "__main__":
    raise SystemExit(main())
