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
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import reserve_economy  # noqa: E402  (SSOT für Ziel und Alarmschwelle, #393)
import reserve_pool as rp  # noqa: E402
from publication_release import accept_candidate  # noqa: E402


def target() -> int:
    """Zielbestand – ausschließlich aus dem SSOT (#393).

    Das hier geschriebene Feld `target` im Zertifikat ist ab sofort ein
    PROTOKOLL („gegen diese Latte wurde gemessen"), keine Vorgabe mehr:
    reserve_gate und reserve_converge lesen ihr Ziel nicht mehr von hier
    zurück. Damit kann ein magerer Lauf die Messlatte nicht länger absenken.
    """
    return reserve_economy.ziel()


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


def reserve_editorial_findings(index: Path, content: str) -> list[str]:
    """Führt die unveränderte Reserve-Redaktionslatte vor dem Publish-Gate aus.

    So kann weder ein guter Score noch ein erfolgreiches Hugo-Rendering eine
    unbelegte Zahl, Phantomquelle oder H2-Zerstückelung überstimmen.
    """
    parts = (content or "").split("---", 2)
    if len(parts) != 3 or parts[0] != "":
        return ["Reserve-Qualitäts-Gate: Frontmatter-Grenze nicht lesbar"]
    fm, body = parts[1], parts[2]
    try:
        import yaml
        metadata = yaml.safe_load(fm) or {}
        if not isinstance(metadata, dict):
            return ["Reserve-Qualitäts-Gate: Frontmatter ist kein Mapping"]
        import redaktions_standard as rs
        return rs.reserve_quality_findings(
            body, author=metadata.get("author") or "",
            erfahrung=metadata.get("erfahrung"),
            erfahrung_beleg=metadata.get("erfahrung_beleg"))
    except Exception as exc:  # fail-closed, Messausfall ist kein Freispruch
        return [f"Reserve-Qualitäts-Gate nicht prüfbar: {exc}"]


def certify_one(index) -> dict:
    """Zertifiziert GENAU EINEN Entwurf am echten Produktions-Gate.

    Herausgelöst am 30.09.2026 (#462), damit die Nachzertifizierung
    (`scripts/reserve_recert.py`) exakt dieselbe Messung benutzt wie der
    nächtliche Volllauf. Zwei Messvorschriften für dieselbe Reife wären
    genau die Sorte „zweite Wahrheit“, die dieses Repo schon mehrfach
    Dauer-Alarme gekostet hat (#272, #393).

    Der Entwurf wird für die Messung kurz auf `draft: false` gesetzt und
    danach BYTEGENAU zurückgeschrieben – das Zertifikat gilt für genau
    diese Bytes.
    """
    original = index.read_text(encoding="utf-8")
    diag = score_diagnosis(index)
    # Unabhängig vom groben Lesbarkeits-Score: 58,0 → 59,0 bleibt dort
    # häufig 80/100. Konvergenz muss sichere Zwischenstufen erkennen können.
    # Gemessen werden dieselben Original-Bytes, deren Hash unten steht.
    from lesbarkeit_heiler import flesch
    measured_flesch = flesch(original, index.parent.name)
    content_findings = reserve_editorial_findings(index, original)
    if content_findings:
        row = {"slug": index.parent.name, "ready": False,
               "sha256": hashlib.sha256(original.encode()).hexdigest(),
               "flesch": measured_flesch,
               "reason": f"Reserve-Qualitäts-Gate: {content_findings[0]}",
               "details": content_findings}
        if diag:
            row["score"] = diag.get("score")
            row["parts"] = diag.get("parts")
        return row
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
           "sha256": hashlib.sha256(original.encode()).hexdigest(),
           "flesch": measured_flesch}
    if reason:
        row["reason"] = reason
    if details:
        row["details"] = details
    if diag:
        row["score"] = diag.get("score")
        row["parts"] = diag.get("parts")
    return row


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



def schreibe_zertifikat(pfad: Path, report: dict) -> None:
    """Schreibt das Zertifikat atomisch UND prüft, was es geschrieben hat.

    WARUM (08.10.2026, WF-D4E0 #653): Das Zertifikat wurde mit einem nackten
    `write_text` geschrieben. Fällt der Prozess mitten im Schreiben um, steht
    eine halbe Datei im Repo; wird sie danach von einem Merge verschmolzen,
    steht ein strukturell kaputtes Artefakt in `main` – und der harte
    End-Gate liest daraus „0/6 gate-fertig“ und meldet einen Vorrats-Engpass,
    den es nie gab.

    Zwei Lagen:
      1. ATOMAR – erst in eine temporäre Datei desselben Verzeichnisses,
         dann `os.replace`. Ein Zertifikat ist danach entweder alt oder neu,
         nie halb.
      2. SELBSTPRÜFUNG – der geschriebene Stand wird zurückgelesen und gegen
         den Bericht abgeglichen (parsebar, Objekt, Kandidatenliste, gleiche
         `ready`-Zahl, keine doppelten Schlüssel). Schlägt die Prüfung fehl,
         bleibt die alte Datei unangetastet und der Lauf stirbt laut –
         kein stilles „Zertifikat geschrieben“.
    """

    def doppelte(paare):
        gesehen: set = set()
        for schluessel, _ in paare:
            if schluessel in gesehen:
                raise ValueError(
                    f"doppelter Schlüssel {schluessel!r} im Zertifikat")
            gesehen.add(schluessel)
        return dict(paare)

    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    try:
        json.loads(text, object_pairs_hook=doppelte)
    except ValueError as exc:
        raise RuntimeError(
            f"Zertifikat nicht serialisierbar – es wird NICHT geschrieben: "
            f"{exc}") from exc

    pfad.parent.mkdir(parents=True, exist_ok=True)
    tmp = pfad.with_suffix(pfad.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    try:
        geprueft = json.loads(tmp.read_text(encoding="utf-8"),
                              object_pairs_hook=doppelte)
    except (OSError, ValueError) as exc:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(
            f"Zertifikat nicht gegenlesbar – es wird NICHT geschrieben: "
            f"{exc}") from exc
    if geprueft.get("ready") != report.get("ready") or \
            len(geprueft.get("candidates") or []) != \
            len(report.get("candidates") or []):
        tmp.unlink(missing_ok=True)
        raise RuntimeError(
            "Zertifikat stimmt nach dem Gegenlesen nicht mit dem Bericht "
            "überein – es wird NICHT geschrieben.")
    os.replace(tmp, pfad)


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

    # BESTANDSAUFNAHME (05.10.2026, WF-B594, #594): Erst zurückgeben, was dem
    # Pool gehört – DANN zählen. Befund F des Vorgangs: Am 05.10. meldete der
    # Watchdog „0 gate-fertige Artikel", während fünf Entwürfe im Repo lagen,
    # die am echten Gate 0,898–0,90 erreichten. Ihnen fehlte nur die Zeile
    # `reserve: true`; der Pool ist fahnen-definiert und sah sie deshalb nie.
    # Die Aufnahme übernimmt ausschließlich HERRENLOSE, maschinell erzeugte,
    # triage-reife, standardriskante und dublettenfreie Entwürfe (sechs
    # Prüfungen, jede Ablehnung mit Grund). Alles andere bleibt ein Angebot an
    # die Redaktion. Best-effort, nie blockierend – eine Bestandsaufnahme darf
    # die Zertifizierung nicht aufhalten.
    try:
        import reserve_intake
        aufnahme = reserve_intake.bestandsaufnahme()
        for kandidat in aufnahme["uebernehmbar"]:
            index = ROOT / "content" / "posts" / kandidat["slug"] / "index.md"
            ergebnis = reserve_intake.uebernehmen(
                index, "herrenlose Reife (automatische Bestandsaufnahme)")
            if ergebnis.get("ok") and not ergebnis.get("schon"):
                print(f"📥 In den Pool aufgenommen: {kandidat['slug']} "
                      f"– {kandidat['grund']}")
        if aufnahme["angebote"]:
            print(f"ℹ {len(aufnahme['angebote'])} fertige(r) Entwurf/Entwürfe "
                  "warten auf eine bewusste Freigabe "
                  "(python3 scripts/reserve_intake.py --md)")
    except Exception as exc:  # noqa: BLE001 – Aufnahme ist Zubringer, kein Gate
        print(f"⚠ Reserve-Bestandsaufnahme übersprungen: {exc}")

    rows = []
    # Nur aktuelle Reserve-Entwürfe (draft+reserve). Bereits veröffentlichte
    # Kandidaten (reserve_published) erscheinen hier bewusst nicht mehr.
    for index in rp.reserve_drafts():
        rows.append(certify_one(index))

    # REPARATUR 15.09.2026 (#295): Ein Kandidat, den kein Heiler reparieren
    # kann, darf den Zielbestand nicht dauerhaft unerreichbar machen. Nach
    # RESERVE_QUARANTINE_HITS Läufen mit demselben Fund verlässt er den Pool
    # (bleibt als BLOCKIERT im Bestand) und gibt den Platz für Nachschub frei.
    blocked = []
    geschont: list[dict] = []
    try:
        import reserve_quarantine as rq
        blocked = rq.record(rows, geschont_out=geschont)
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

    if geschont:
        # Reparatur 07.10.2026 (#614): Die Ausmusterung war unsichtbar. Wer den
        # Pool kleiner macht, muss sagen, wen er gehalten hat und warum – sonst
        # erklärt niemand dem Watchdog, warum der Vorrat schrumpft.
        print("\n🌱 Ausmusterung geschont (Befund-Klasse ist heilbar, Fahne "
              f"bleibt im Pool): {len(geschont)} Kandidat(en)")
        for g in geschont:
            print(f"   - {g['slug']}: [{g['klasse']}] {g['hits']} Lauf/Läufe · "
                  f"{(g.get('heiler') and ', '.join(g['heiler'])) or 'Heiler –'}")

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
    if geschont:
        # Die zweite Hälfte derselben Erklärung (#614): Ein gehaltener
        # Kandidat ist kein Zufall, sondern eine Klassen-Entscheidung.
        report["geschont"] = [{"slug": g["slug"], "klasse": g["klasse"],
                               "hits": g["hits"], "heiler": g["heiler"],
                               "warum": g["warum"]} for g in geschont]
    schreibe_zertifikat(ROOT / "data" / "reserve-readiness.json", report)
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
