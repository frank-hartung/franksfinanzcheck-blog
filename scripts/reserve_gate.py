#!/usr/bin/env python3
"""
reserve_gate.py – Hartes End-Gate der Content-Reserve-Produktionslinie.

Liest das von reserve_readiness.py geschriebene, hash-gesicherte
Zertifikat (data/reserve-readiness.json) und beantwortet EINE Frage:

    Sind mindestens RESERVE_TARGET Kandidaten am echten
    Produktions-Gate zertifiziert (ready=true)?

Grundregel „Stock shortage must not look successful": Bei Engpass
darf der Workflow NICHT grün werden. Exit-Code 0 nur bei vollem Ziel.

Premium-Fix 15.09.2026 (#295) – ZWEI zusätzliche Ehrlichkeits-Regeln:
  1. FRISCHE: Ein Zertifikat ohne `generated_at` oder mit einem Zeitstempel,
     der älter ist als RESERVE_CERT_MAX_AGE_H (Default 36 h), ist KEIN
     Nachweis. Genau diese Klasse („Zertifikat von gestern sagt 6/6, der Pool
     hat real 4 Entwürfe“) hat am 15.09. dazu geführt, dass der Lauf erst nach
     dem Push auffiel. Fehlt der Zeitstempel, wird gewarnt (Alt-Zertifikate
     bleiben lesbar), ist er zu alt, ist das Gate rot.
  2. Der Zähler kommt IMMER aus der Kandidatenliste (nie aus dem `ready`-Feld).

Verwendung:
    python3 scripts/reserve_gate.py                 # Workflow-End-Gate
    python3 scripts/reserve_gate.py --selftest      # Sabotageschutz
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CERT = ROOT / "data" / "reserve-readiness.json"
CERT_MAX_AGE_H = 36  # Notbremse gegen veraltete Zertifikate (env-übersteuerbar)


def evaluate(cert_path: Path) -> tuple[int, int, list[dict]]:
    """Liefert (ready, target, candidates). Fehlt das Zertifikat,
    gilt der Pool als leer (0/target) – ein abgestürzter Lauf darf
    nicht als erfolgreich aussehen.

    Premium-Fix 15.09.2026 (#287/#295): ready wird IMMER aus der
    candidates-Liste neu gezählt – nie dem gespeicherten `ready`-Feld
    blind vertraut (das konnte nach publish_to_min veraltete LIVE-Slugs
    mitzählen und 6/6 vortäuschen).
    """
    if not cert_path.exists():
        return 0, int(os.environ.get("RESERVE_TARGET", "6")), []
    data = json.loads(cert_path.read_text(encoding="utf-8"))
    target = int(data.get("target", os.environ.get("RESERVE_TARGET", "6")))
    candidates = list(data.get("candidates", []) or [])
    # Nur ready=true-Einträge; leere/kaputte Zeilen zählen nicht.
    ready = sum(1 for r in candidates if r.get("ready") is True)
    return ready, target, candidates


def max_age_hours() -> float:
    try:
        return float(os.environ.get("RESERVE_CERT_MAX_AGE_H")
                     or CERT_MAX_AGE_H)
    except ValueError:
        return float(CERT_MAX_AGE_H)


def cert_age_hours(cert_path: Path) -> float | None:
    """Alter des Zertifikats in Stunden; None = kein/defekter Zeitstempel."""
    try:
        data = json.loads(cert_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    raw = data.get("generated_at")
    if not isinstance(raw, str):
        return None
    m = re.match(r"(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})", raw)
    if not m:
        return None
    try:
        stamp = dt.datetime.strptime(f"{m.group(1)} {m.group(2)}",
                                     "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=dt.timezone.utc)
    except ValueError:
        return None
    return (dt.datetime.now(dt.timezone.utc) - stamp).total_seconds() / 3600.0


def freshness(cert_path: Path) -> tuple[bool, str]:
    """(frisch?, Meldung). Kein Zeitstempel = gewarnt, aber nicht blockierend;
    zu altes Zertifikat = blockierend (kein Nachweis)."""
    alter = cert_age_hours(cert_path)
    grenze = max_age_hours()
    if alter is None:
        return True, ("⚠ Zertifikat ohne verwertbaren Zeitstempel – "
                      "Alter nicht prüfbar.")
    if alter > grenze:
        return False, (f"🛑 Zertifikat ist veraltet ({alter:.1f} h > "
                       f"{grenze:.0f} h) – kein Nachweis für den aktuellen "
                       f"Pool. Ursache: reserve_readiness.py lief nicht "
                       f"(API-/Hugo-Fehler?) oder der Push ging verloren.")
    return True, f"Zertifikat {alter:.1f} h alt (Grenze {grenze:.0f} h)."


def themen_vielfalt(candidates: list[dict]) -> tuple[int, dict]:
    """Wie viele VERSCHIEDENE Themen stecken in den fertigen Kandidaten?

    Neu am 26.09.2026 (#387): Der Gate zählte Kandidaten, nicht Vorrat. Am
    Abend des Vorfalls waren 4 von 5 fertigen Kandidaten Varianten von
    „Stromfresser finden" – rechnerisch fast volles Lager, praktisch drei
    Artikel. Weil pro Tag nur EINER pro Thema live gehen kann (sonst stuft
    der Dubletten-Schutz ihn wieder zurück – die fünf Rückläufer), trägt so
    ein Lager an einem Ausfalltag nicht das, was die Zahl verspricht.
    Rückgabe: (Anzahl Themen, {Leitbegriff: [slugs]}).
    """
    familien: dict[str, list] = {}
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import reserve_topics as rt
        import reserve_pool as rp
    except Exception:  # noqa: BLE001 – Kennzahl darf nie blockieren
        return len(candidates), {}
    # Gruppiert wird wie im Disponenten: über KOLLISION, nicht über den
    # alphabetisch ersten Leitbegriff. „Stromfresser finden: … Energiediebe“
    # und „Stromfresser finden: … Stromrechnung“ teilen sich nur EIN Wort –
    # eine naive Schlüsselbildung hielte sie für zwei Themen.
    vertreter: dict[str, str] = {}   # Familienname -> Titel des Ersten
    bindung: dict[str, list] = {}    # Familienname -> verbindende Begriffe
    for row in candidates:
        if not row.get("ready"):
            continue
        slug = row.get("slug") or ""
        index = ROOT / "content" / "posts" / slug / "index.md"
        try:
            titel = rp._titel(index.read_text(encoding="utf-8"))
        except OSError:
            titel = ""
        titel = titel or slug
        treffer = rt.thema_kollision(titel, vertreter)
        if treffer:
            familien[treffer[0]].append(slug)
            # Der Name der Familie ist das Wort, das sie verbindet – nicht
            # der Zufallsbegriff des zuerst gesehenen Titels („massiv“).
            bindung.setdefault(treffer[0], []).append(treffer[1])
        else:
            name = (sorted(rt.leitbegriffe(titel)) or [slug])[0]
            vertreter[name] = titel
            familien[name] = [slug]
    for name, begriffe in bindung.items():
        haeufigster = max(set(begriffe), key=begriffe.count)
        if haeufigster != name and haeufigster not in familien:
            familien[haeufigster] = familien.pop(name)
    return len(familien), familien


def diagnose(ready: int, target: int, candidates: list[dict]) -> list[str]:
    """Warum ist der Vorrat unter dem Ziel? Ursachenklassen statt Rätselraten.

    Neu am 26.09.2026 (#387): Der Gate meldete bisher nur „N/6 gate-fertig"
    plus die Gründe der EINZELNEN Kandidaten. Die eigentliche Frage – warum
    kein Nachschub kam – beantwortete er nicht, und die Lauf-Logs verfallen.
    Am 26.09. standen drei verschiedene Ursachen gleichzeitig im Raum
    (Fahnen-Verlust, Themen-Stillstand, R5-Falsch-Positiv); das Ticket nannte
    keine einzige davon. Diese Funktion liest die beteiligten Gedächtnisse
    und schreibt die Ursache in den Lauf.
    """
    zeilen: list[str] = []

    # 1. LECK: Kandidaten, die ihre Fahne verloren haben (fremde Umschreibung)
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import reserve_custody as cust
        lage = cust.bestandsaufnahme()
        if lage["verloren"]:
            zeilen.append(
                f"LECK: {len(lage['verloren'])} Entwurf/Entwürfe waren im Pool, "
                f"haben aber die `reserve`-Fahne verloren "
                f"({', '.join(e['slug'] for e in lage['verloren'][:3])}). "
                f"Heilung: `python3 scripts/reserve_custody.py --heal`.")
        if lage["ruecklaeufer"]:
            zeilen.append(
                f"RÜCKLÄUFER: {len(lage['ruecklaeufer'])} veröffentlichte "
                f"Artikel stehen wieder auf `draft` – fertiger Content ohne "
                f"Zuhause. Redaktion entscheidet (draft_triage).")
    except Exception as exc:  # noqa: BLE001 – Diagnose darf nie blockieren
        zeilen.append(f"(Bestands-Wächter nicht lesbar: {exc})")

    # 2. BLOCKER: Kandidaten im Pool, die ein Gate ablehnt
    blocker = [c for c in candidates if not c.get("ready")]
    if blocker:
        zeilen.append(
            f"BLOCKER: {len(blocker)} Kandidat(en) im Pool scheitern an einem "
            f"Gate – erster Fund: "
            f"„{(blocker[0].get('reason') or 'ohne Angabe')[:120]}“.")

    # 3. NACHSCHUB: Gibt es überhaupt freie Themen?
    try:
        import generate_drafts as g
        import reserve_topics as rt
        frei = rt.disponieren(g.load_topics(), limit=3)
        if not frei:
            zeilen.append(
                "THEMENMANGEL: Die Disposition findet kein freies Thema "
                "(alles thematisch belegt oder im Cooldown). Nachschub in "
                "data/topics.yaml eintragen – `python3 "
                "scripts/reserve_topics.py --status` zeigt die Lage.")
        elif len(candidates) < target:
            zeilen.append(
                f"PRODUKTION: {target - len(candidates)} Kandidat(en) fehlen "
                f"im Pool, obwohl freie Themen bereitstehen (nächstes: "
                f"„{frei[0].get('title')}“). Ursache liegt bei der "
                f"KI-Generierung (API-Schlüssel, Profi-Gate) – siehe die "
                f"Meldungen der Stufen 1/4 weiter oben im Log.")
    except Exception as exc:  # noqa: BLE001
        zeilen.append(f"(Themen-Disposition nicht lesbar: {exc})")

    return zeilen


def chronik_schreiben(ready: int, target: int, candidates: list[dict]) -> None:
    """Eine Zeile pro Lauf – damit ein Trend sichtbar wird, nicht nur der Tag."""
    pfad = ROOT / "data" / "reserve-history.jsonl"
    zeile = {
        "ts": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ready": ready, "target": target, "pool": len(candidates),
        "lauf": os.environ.get("GITHUB_RUN_ID", "lokal"),
        "blocker": [c.get("slug") for c in candidates if not c.get("ready")],
        "themen": themen_vielfalt(candidates)[0],
    }
    try:
        pfad.parent.mkdir(parents=True, exist_ok=True)
        with pfad.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(zeile, ensure_ascii=False) + "\n")
    except OSError:
        pass


def report(ready: int, target: int, candidates: list[dict]) -> None:
    if ready >= target:
        print(f"\u2705 Reserve-Pool gate-fertig: {ready}/{target} Kandidaten zertifiziert.")
        return
    print(f"\U0001f6d1 RESERVE-ENGPA\u00df: nur {ready}/{target} Kandidaten gate-fertig.")
    for r in candidates:
        mark = "\u2705" if r.get("ready") else "\u26d4"
        score = f" | Score {r.get('score')}" if r.get("score") is not None else ""
        reason = f" \u2013 {r.get('reason', '')}" if r.get("reason") else ""
        print(f"   {mark} {r.get('slug', '<ohne-slug>')}{score}{reason}")
    if ready > 0 and not candidates:
        print("   (Zertifikat ohne Kandidatenliste)")
    print("   Diagnose: RESERVE-FINISH-REPORT.md (Score-Teile je Kandidat/Heiler).")
    themen, familien = themen_vielfalt(candidates)
    klumpen = {k: v for k, v in familien.items() if len(v) > 1}
    if klumpen:
        print(f"\n   VORRAT-VIELFALT: {ready} fertige Kandidaten, aber nur "
              f"{themen} verschiedene Themen.")
        for begriff, slugs in sorted(klumpen.items(),
                                     key=lambda kv: -len(kv[1])):
            print(f"   • „{begriff}“: {len(slugs)}× "
                  f"({', '.join(s[:48] for s in slugs[:3])}…)")
        print("     Pro Tag kann nur EIN Artikel je Thema live gehen – sonst "
              "stuft der Dubletten-Schutz ihn zurück. Der Vorrat trägt an "
              f"einem Ausfalltag also {themen}, nicht {ready} Artikel.")
    ursachen = diagnose(ready, target, candidates)
    if ursachen:
        print("\n   URSACHEN DIESES ENGPASSES:")
        for zeile in ursachen:
            print(f"   • {zeile}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        try:
            with open(summary, "a", encoding="utf-8") as fh:
                fh.write(f"\n## 🛑 Content-Reserve: {ready}/{target} "
                         f"gate-fertig\n\n")
                for zeile in ursachen:
                    fh.write(f"- {zeile}\n")
        except OSError:
            pass


def run_selftest() -> int:
    cert_cases = []
    with tempfile.TemporaryDirectory() as tmp:
        cert = Path(tmp) / "reserve-readiness.json"

        # Fall 1: kein Zertifikat -> wie leerer Pool behandeln
        ready, target, candidates = evaluate(cert)
        assert (ready, target, candidates) == (0, 6, []), "fehlendes Zertifikat muss leer zählen"

        # Fall 2: 5/6 -> Engpass
        cert.write_text(json.dumps({
            "target": 6, "ready": 5,
            "candidates": [{"slug": f"k{i}", "ready": i < 5,
                            "score": 0.9 if i < 5 else None,
                            "reason": None if i < 5 else "R5"} for i in range(6)],
        }, ensure_ascii=False), encoding="utf-8")
        ready, target, candidates = evaluate(cert)
        assert (ready, target) == (5, 6), f"5/6 erwartet, {ready}/{target}"
        assert len(candidates) == 6

        # Fall 3: 6/6 -> voll
        cert.write_text(json.dumps({
            "target": 6, "ready": 6,
            "candidates": [{"slug": f"k{i}", "ready": True, "score": 0.95} for i in range(6)],
        }, ensure_ascii=False), encoding="utf-8")
        ready, target, _ = evaluate(cert)
        assert (ready, target) == (6, 6), f"6/6 erwartet, {ready}/{target}"

        # Fall 4: überfüllt 7/6 -> ebenfalls grün
        cert.write_text(json.dumps({
            "target": 6, "ready": 7,
            "candidates": [{"slug": f"k{i}", "ready": True} for i in range(7)],
        }, ensure_ascii=False), encoding="utf-8")
        ready, target, _ = evaluate(cert)
        assert ready >= target, "7/6 muss grün sein"

        cert_cases.append("ok")

        # ---- Frische-Prüfung (#295): veraltetes Zertifikat ist kein Nachweis
        now = dt.datetime.now(dt.timezone.utc)
        cert.write_text(json.dumps({
            "target": 6, "ready": 1,
            "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "candidates": [{"slug": "k", "ready": True}],
        }, ensure_ascii=False), encoding="utf-8")
        frisch, meldung = freshness(cert)
        assert frisch, f"frisches Zertifikat muss frisch sein: {meldung}"
        assert "0.0 h" in meldung or "0.1 h" in meldung, meldung

        alt = (now - dt.timedelta(hours=max_age_hours() + 2)).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
        cert.write_text(json.dumps({
            "target": 6, "ready": 6, "generated_at": alt,
            "candidates": [{"slug": f"k{i}", "ready": True} for i in range(6)],
        }, ensure_ascii=False), encoding="utf-8")
        frisch, meldung = freshness(cert)
        assert not frisch, "veraltetes Zertifikat darf nicht als frisch gelten"
        assert "veraltet" in meldung, meldung
        # … und der End-Gate-Entscheid muss dann rot sein, obwohl 6/6 ready
        ready, target, _ = evaluate(cert)
        assert ready >= target and not frisch, "Alters-Regel greift nicht"

        cert.write_text(json.dumps({
            "target": 6, "ready": 6,
            "candidates": [{"slug": f"k{i}", "ready": True} for i in range(6)],
        }, ensure_ascii=False), encoding="utf-8")
        frisch, meldung = freshness(cert)
        assert frisch and "Zeitstempel" in meldung, meldung
        cert_cases.append("frische")
    print(f"\u2705 Selbsttest reserve_gate: {len(cert_cases)} Fälle bestanden "
          f"(Zählung aus der Liste, Frische-Grenze "
          f"{max_age_hours():.0f} h).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Harter End-Gate der Content-Reserve")
    ap.add_argument("--selftest", action="store_true", help="interne Tests ausführen")
    ap.add_argument("--cert", default=str(CERT), help="Pfad zum Zertifikat (für Tests)")
    args = ap.parse_args()
    if args.selftest:
        return run_selftest()
    cert = Path(args.cert)
    ready, target, candidates = evaluate(cert)
    report(ready, target, candidates)
    chronik_schreiben(ready, target, candidates)
    frisch, meldung = freshness(cert)
    print(f"   {meldung}")
    if ready >= target and frisch:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
