#!/usr/bin/env python3
"""reserve_recert.py – Nachzertifizierung der Content-Reserve (Issue #462).

WARUM ES DIESES SKRIPT GIBT
---------------------------
Das Reife-Zertifikat `data/reserve-readiness.json` gilt ausdrücklich nur für
GENAU DIE BYTES eines Entwurfs, die am Gate gemessen wurden (sha256). Das ist
richtig so – aber es gab keinen Besitzer für die Folge daraus:

Die Reserve-Entwürfe werden zwischen zwei Zertifizierungsläufen von mehreren
Veredelungs-Linien angefasst (Stilpolitur, Rechtschreib-/Typografie-Heiler,
Faktenfrische, Pinterest-SEO-Healer, Link-Heiler, KI-Redaktion …). Jede dieser
Linien committet ihren Heil-Erfolg – und macht damit ALLE betroffenen
Zertifikate ungültig, ohne sie zu erneuern. Am nächsten Morgen zählte der
Bot-Watchdog deshalb Kandidaten, die fachlich längst fertig waren, als
„Zertifikat passt nicht mehr zum Entwurf“ und eröffnete täglich erneut das
Automations-Ticket (#462). Der Engpass war kein Content-Engpass, sondern ein
NACHWEIS-Engpass: geheilter Content ohne frischen Nachweis.

Dieselbe Fehlklasse wie #393 (Alarmschwelle == Ziel) und #272 (ein Meldeweg
für alles): Das Ticket kam per Konstruktion zurück, weil niemand den Zustand
heilen konnte, den es meldete.

WAS ES TUT
----------
1. DRIFT ERKENNEN (billig, ohne Hugo, ohne Netz):
   Für jeden Zertifikatseintrag wird der sha256 des Entwurfs neu berechnet.
   Abweichung = Drift. Zusätzlich wird der VERURSACHER benannt (letzter
   Commit, der die Datei angefasst hat) – ein Befund ohne Besitzer ist
   Rauschen.
2. DRIFT HEILEN (`--fix`): Nur die gedrifteten Kandidaten laufen erneut durch
   das ECHTE Produktions-Gate (`reserve_readiness.certify_one`, also
   quality_score + publish_gate STRICT + Hugo-Render-Beweis). Unberührte
   Zeilen bleiben unangetastet – die Nachzertifizierung ist damit um ein
   Vielfaches billiger als ein Volllauf und in jedem Workflow tragbar.
3. EHRLICH BLEIBEN: Fehlt das Gate-Werkzeug (kein `hugo` im PATH), wird
   NICHTS geschrieben (Exit 3). Ein Zertifikat, das aus Werkzeugmangel
   „nicht bereit“ sagt, wäre eine Lüge in die andere Richtung – und würde
   echten Bestand vernichten.

VERWENDUNG
----------
    python3 scripts/reserve_recert.py --check     # nur melden (Exit 1 = Drift)
    python3 scripts/reserve_recert.py --fix       # Drift nachzertifizieren
    python3 scripts/reserve_recert.py --fix --json
    python3 scripts/reserve_recert.py --selftest  # Sabotageschutz

EXIT-CODES
----------
    0 = kein Drift (bzw. Drift vollständig nachzertifiziert)
    1 = Drift vorhanden (--check) bzw. nach --fix weiterhin offen
    2 = Zertifikat fehlt/unlesbar (kein Nachweis – Volllauf nötig)
    3 = Nachzertifizierung nicht möglich (Gate-Werkzeug fehlt) – nichts getan
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CERT = ROOT / "data" / "reserve-readiness.json"
sys.path.insert(0, str(ROOT / "scripts"))
import reserve_artifacts as artifacts  # noqa: E402


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def draft_paths(root: Path = ROOT) -> dict:
    """slug -> Pfad aller aktuellen Reserve-Entwürfe (draft+reserve)."""
    import reserve_pool as rp
    posts = root / "content" / "posts"
    return {p.parent.name: p for p in rp.reserve_drafts(posts)}


def file_digest(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def last_touch(path: Path, root: Path = ROOT) -> str:
    """Letzter Commit, der diesen Entwurf angefasst hat – der Verursacher.

    Best effort: ohne Git-Historie (Shallow-Checkout, Test-Sandkasten) gibt
    es schlicht keine Zuordnung, und das darf nie ein Fehler sein.
    """
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%h %an: %s",
             "--", str(path.relative_to(root))],
            cwd=str(root), capture_output=True, text=True, timeout=20)
        line = (out.stdout or "").strip().splitlines()
        return line[0][:120] if line else "unbekannt (keine Historie)"
    except Exception:  # noqa: BLE001 – Diagnose darf nie blockieren
        return "unbekannt (keine Historie)"


def load_cert(cert_path: Path = CERT) -> dict | None:
    try:
        data = artifacts.read_certificate(cert_path)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("candidates"), list):
        return None
    return data


def drift(cert: dict, drafts: dict) -> list[dict]:
    """Alle Zertifikatszeilen, deren Nachweis nicht mehr zum Entwurf passt.

    Drei Drift-Arten, bewusst unterschieden:
      · `geaendert` – Entwurf existiert, Bytes anders (Heiler-Lauf)
      · `verschwunden` – Entwurf ist weg/veröffentlicht (Zeile ist Altlast)
      · `unzertifiziert` – Entwurf ohne Zeile im Zertifikat (neuer Kandidat)
    """
    out: list[dict] = []
    gesehen = set()
    for row in cert.get("candidates", []):
        if not isinstance(row, dict):
            continue
        slug = row.get("slug")
        if not isinstance(slug, str):
            continue
        gesehen.add(slug)
        path = drafts.get(slug)
        if path is None:
            out.append({"slug": slug, "art": "verschwunden",
                        "ready": bool(row.get("ready")),
                        "ursache": "kein Reserve-Entwurf mehr (veröffentlicht "
                                   "oder entfernt)"})
            continue
        digest = file_digest(path)
        if digest is None:
            out.append({"slug": slug, "art": "verschwunden",
                        "ready": bool(row.get("ready")),
                        "ursache": "Entwurf nicht lesbar"})
            continue
        if digest != row.get("sha256"):
            out.append({"slug": slug, "art": "geaendert",
                        "ready": bool(row.get("ready")),
                        "ursache": last_touch(path)})
    for slug in drafts:
        if slug not in gesehen:
            out.append({"slug": slug, "art": "unzertifiziert",
                        "ready": False,
                        "ursache": last_touch(drafts[slug])})
    return out


def gate_verfuegbar() -> tuple[bool, str]:
    """Kann hier überhaupt VOLLWERTIG gemessen werden?

    Diese Prüfung ist das Herzstück der Sicherheit. Eine Nachzertifizierung
    schreibt `ready: false` – sie kann also Bestand VERNICHTEN. Das darf sie
    nur, wenn die komplette Messkette steht:

      · `hugo` (Render-Beweis im publish_gate) und
      · die Rechtschreib-Kette (`hunspell` + `spellcheck.analyze_article`).

    Warum der zweite Punkt hart ist: `quality_score` wertet eine nicht
    lauffähige Rechtschreibprüfung als `spelling = 0.5` („unbekannt“). Bei
    Gewicht 0.20 drückt das JEDEN Artikel um bis zu 0.10 – quer unter die
    0.85-Schwelle. Ein Lauf ohne hunspell hätte am 30.09.2026 also acht
    fachlich gesunde Kandidaten als unreif abgestempelt und den Bestand
    rechnerisch auf null gesetzt: ein Werkzeugmangel, der wie ein
    Qualitätsproblem aussieht. Genau diese stille Abwertung wird hier
    fail-closed abgefangen (vgl. Governance-Regel C2: eine nicht ausgeführte
    Messung ist kein Ergebnis).
    """
    if shutil.which("hugo") is None:
        return False, "hugo fehlt im PATH (Gate rendert nicht)"
    try:
        import reserve_readiness  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        return False, f"reserve_readiness nicht importierbar: {exc}"
    ok, grund = messkette_rechtschreibung()
    if not ok:
        return False, grund
    return True, "Gate-Werkzeug vollständig (hugo + Rechtschreib-Kette)"


def messkette_rechtschreibung() -> tuple[bool, str]:
    """Beweist an einer Probe, dass die Rechtschreib-Wertung echt misst."""
    try:
        import spellcheck as sc
        # #634: Ein vorhandener CLI-Pfad ist noch kein Messwerkzeug. Manche
        # Hunspell-Installationen ohne de_DE liefern eine leere Trefferliste;
        # das darf weder „fehlerfrei“ noch einen frischen READY-Beleg ergeben.
        probe = subprocess.run(
            ["hunspell", "-d", "de_DE", "-l"],
            input="Haushalt\nFheler\n", text=True, capture_output=True,
            timeout=15, check=False,
        )
        if probe.returncode != 0 or probe.stdout.split() != ["Fheler"]:
            raise RuntimeError("Hunspell/de_DE erkennt die Kontrollwörter "
                               "nicht korrekt (Wörterbuch/CLI prüfen)")
        wl = sc.load_whitelist()
        sc.analyze_article({"body": "Ein kurzer Satz zur Probe.",
                            "content": "Ein kurzer Satz zur Probe.",
                            "fm": "", "meta": {}}, wl)
    except Exception as exc:  # noqa: BLE001 – jede Ursache ist dieselbe Gefahr
        return False, (f"Rechtschreib-Kette nicht lauffähig ({exc}) – "
                       f"quality_score würde spelling=0.5 („unbekannt“) "
                       f"werten – kein vollständiger Zertifizierungsnachweis. "
                       f"Abhilfe: `sudo apt-get install -y hunspell "
                       f"hunspell-de-de`.")
    return True, "Rechtschreib-Kette lauffähig"


def recertify(cert: dict, drafts: dict, betroffen: list[str]) -> dict:
    """Misst die betroffenen Kandidaten neu und baut das Zertifikat neu auf."""
    import reserve_economy
    import reserve_readiness as rr

    rows: list[dict] = []
    erneuert: list[str] = []
    for row in cert.get("candidates", []):
        if not isinstance(row, dict) or not isinstance(row.get("slug"), str):
            continue
        slug = row["slug"]
        if slug not in drafts:
            continue  # Altlast: veröffentlicht oder entfernt
        if slug in betroffen:
            neu = rr.certify_one(drafts[slug])
            erneuert.append(slug)
            rows.append(neu)
        else:
            rows.append(row)
    vorhanden = {r["slug"] for r in rows}
    for slug, path in drafts.items():
        if slug not in vorhanden:
            rows.append(rr.certify_one(path))
            erneuert.append(slug)

    ready = sum(1 for r in rows if r.get("ready") is True)
    _abwertungs_bremse(cert, rows)
    neu_cert = dict(cert)
    neu_cert.update({
        "target": reserve_economy.ziel(),
        "ready": ready,
        "pool_size": len(rows),
        "generated_at": _now(),
        "candidates": rows,
        # Provenienz: Ein nachgezogenes Zertifikat muss sich als solches zu
        # erkennen geben – sonst sieht ein Teil-Lauf aus wie ein Volllauf.
        "recert": {"at": _now(), "renewed": sorted(set(erneuert)),
                   "tool": "scripts/reserve_recert.py"},
    })
    return neu_cert


class Abwertungsverdacht(RuntimeError):
    """Massenabwertung mit EINEM gemeinsamen Muster – Werkzeug statt Qualität."""


def _abwertungs_bremse(alt: dict, neu_rows: list[dict],
                       schwelle: float = 0.5) -> None:
    """Zweite Sicherung gegen Werkzeug-Ausfälle (#462).

    Die erste Sicherung (`gate_verfuegbar`) kennt die bekannten Lücken. Für
    die unbekannten gilt eine Faustregel aus dem Betrieb: Wenn ein Lauf mehr
    als die Hälfte des zertifizierten Bestands abwertet UND alle Abwertungen
    dieselbe schwächste Teilnote nennen, ist mit hoher Wahrscheinlichkeit das
    Messwerkzeug kaputt – nicht der Content. Dann wird NICHTS geschrieben.
    Bewusstes Übersteuern: `RESERVE_RECERT_FORCE=1`.
    """
    import os
    if os.environ.get("RESERVE_RECERT_FORCE") == "1":
        return
    war_ready = {r["slug"] for r in alt.get("candidates", [])
                 if isinstance(r, dict) and r.get("ready") is True
                 and isinstance(r.get("slug"), str)}
    if not war_ready:
        return
    verloren = [r for r in neu_rows
                if r.get("slug") in war_ready and r.get("ready") is not True]
    if len(verloren) <= len(war_ready) * schwelle:
        return
    muster = set()
    for r in verloren:
        parts = r.get("parts") or {}
        if parts:
            muster.add(min(parts, key=lambda k: parts[k]))
    if len(muster) == 1:
        teil = muster.pop()
        raise Abwertungsverdacht(
            f"{len(verloren)} von {len(war_ready)} zertifizierten Kandidaten "
            f"würden abgewertet – ALLE mit derselben schwächsten Teilnote "
            f"'{teil}'. Das ist das Bild eines fehlenden Messwerkzeugs, nicht "
            f"eines Qualitätseinbruchs. Zertifikat bleibt unverändert "
            f"(bewusst erzwingen: RESERVE_RECERT_FORCE=1).")


def bericht(befunde: list[dict]) -> str:
    if not befunde:
        return "✅ Zertifikat und Entwürfe stimmen überein (kein Drift)."
    zeilen = [f"⚠ Zertifikats-Drift: {len(befunde)} Kandidat(en) ohne gültigen "
              f"Nachweis"]
    for b in befunde:
        marke = "🔻" if b.get("ready") else "·"
        zeilen.append(f"   {marke} {b['slug']} [{b['art']}] – {b['ursache']}")
    verlust = sum(1 for b in befunde if b.get("ready"))
    if verlust:
        zeilen.append(f"   → {verlust} zuvor gate-fertige Artikel zählen ohne "
                      f"Nachzertifizierung NICHT mehr zum Bestand.")
    return "\n".join(zeilen)


def selftest() -> int:
    """Sabotageschutz: Drift-Erkennung muss in einem Sandkasten beweisbar sein."""
    import tempfile
    fehler = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "content" / "posts" / "a").mkdir(parents=True)
        idx = root / "content" / "posts" / "a" / "index.md"
        idx.write_text("---\ndraft: true\nreserve: true\n---\nText\n",
                       encoding="utf-8")
        cert = {"candidates": [
            {"slug": "a", "ready": True, "sha256": file_digest(idx)},
            {"slug": "weg", "ready": True, "sha256": "0" * 64},
        ]}
        drafts = {"a": idx}
        if "a" in {b["slug"] for b in drift(cert, drafts)}:
            fehler.append("unveränderter Entwurf wird fälschlich als Drift "
                          "gemeldet")
        idx.write_text("---\ndraft: true\nreserve: true\n---\nText geheilt\n",
                       encoding="utf-8")
        befunde = {b["slug"]: b["art"] for b in drift(cert, drafts)}
        if befunde.get("a") != "geaendert":
            fehler.append("geänderter Entwurf wird nicht als Drift erkannt")
        if befunde.get("weg") != "verschwunden":
            fehler.append("verschwundener Entwurf wird nicht erkannt")
        drafts["neu"] = idx
        if "neu" not in {b["slug"] for b in drift(cert, drafts)}:
            fehler.append("unzertifizierter Entwurf wird nicht erkannt")
    if fehler:
        print("🛑 SELBSTTEST FEHLGESCHLAGEN – keine Änderung:")
        for f in fehler:
            print(f"   {f}")
        return 2
    print("✅ Selbsttest ok (Drift-Erkennung beweisbar).")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fix", action="store_true",
                    help="gedriftete Kandidaten neu zertifizieren")
    ap.add_argument("--check", action="store_true",
                    help="nur melden (Standard)")
    ap.add_argument("--json", action="store_true", help="Befunde als JSON")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    cert = load_cert()
    if cert is None:
        print("🛑 Reife-Zertifikat fehlt oder ist unlesbar – Nachzertifizierung "
              "kann nichts retten. Volllauf nötig: "
              "`python3 scripts/reserve_readiness.py`.")
        return 2

    drafts = draft_paths()
    befunde = drift(cert, drafts)
    print(bericht(befunde))
    if args.json:
        print(json.dumps({"drift": befunde}, ensure_ascii=False))

    if not befunde:
        return 0
    if not args.fix:
        print("   Heilung: `python3 scripts/reserve_recert.py --fix` "
              "(misst nur die betroffenen Kandidaten neu).")
        return 1

    ok, grund = gate_verfuegbar()
    if not ok:
        print(f"🛑 Nachzertifizierung nicht möglich: {grund}. "
              f"Zertifikat bleibt unverändert (keine erfundene Reife).")
        return 3

    betroffen = [b["slug"] for b in befunde if b["art"] != "verschwunden"]
    try:
        neu = recertify(cert, drafts, betroffen)
    except Abwertungsverdacht as exc:
        print(f"🛑 Nachzertifizierung abgebrochen: {exc}")
        return 3
    artifacts.certificate_rows(neu)
    artifacts.write_object(CERT, neu)
    ready = neu["ready"]
    print(f"✅ Zertifikat nachgezogen: {len(neu['recert']['renewed'])} "
          f"Kandidat(en) neu gemessen · {ready}/{neu['target']} gate-fertig "
          f"(Pool {neu['pool_size']}).")
    for row in neu["candidates"]:
        if row.get("slug") in neu["recert"]["renewed"]:
            mark = "✅" if row.get("ready") else "⛔"
            grund = f" – {row['reason']}" if row.get("reason") else ""
            print(f"   {mark} {row['slug']}{grund}")

    rest = drift(neu, draft_paths())
    if rest:
        print(bericht(rest))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
