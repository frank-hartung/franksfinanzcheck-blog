#!/usr/bin/env python3
"""Transaktionale Selbstheilung für den Live-Bestand der Release-Scorecard (#1098).

Die Scorecard bleibt ein reiner Beweismesslauf (C15). Dieses Modul ist ihr
vorgeschalteter SCHREIBER: es wählt nur blockierende, als automatisierbar
deklarierte Prüfungen mit einem vorhandenen deterministischen Heiler aus.
Fachbefunde, Siegel und Freigaben werden nie angetastet.

Vertrag:
  * Auswahl über release_scorecard + data/release_scorecard.yaml, keine
    zweite Ampel und keine kopierte Schwelle.
  * Nur T5 (Lesbarkeit), T6 (Textverständnis) und artikelinterne RD1-
    Duplikate. Cross-Artikel-Plagiate (RD2) und alle human-Checks bleiben
    Aufgabe der Redaktion. Ein Artikel mit zusätzlichem human-Blocker wird
    nicht automatisch umgeschrieben: sein Prüfstand bleibt stabil.
  * Vor jedem Schreiben: vorhandene Heiler-Tore, Publikations-Vertrag,
    YMYL-Schreibschutz, Frontmatter-Grenzen und Formbewahrung.
  * Nach jedem Schreiben: neuer Hugo-Bau durch die gemeinsame Action, dann
    vollständige Scorecard. `--bestaetigen` verwirft den gesamten Versuch,
    sobald ein neuer Blocker/Werkzeugfehler auftaucht, kein Ziel-Check besser
    wurde oder eine Datei inzwischen fremd geändert wurde.
  * Begrenzung: höchstens DEFAULT_MAX_ARTIKEL Dateien je Lauf; die Heiler
    laufen bis zu ihrem eigenen Fixpunkt. Kein endloser Retry, kein KI-Call.

CLI: --plan (Standard, schreibt nichts) · --apply · --bestaetigen ·
     --zurueckrollen · --json · --selftest
Exit: 0 = Versuch abgeschlossen/kein automatisierbarer Auftrag;
      1 = Nachmessung hat den Versuch verworfen (Original wiederhergestellt);
      2 = Werkzeug-/Vertragsfehler, niemals ein Freispruch.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

STATE = ROOT / "data" / "release_bestand_heilung_state.json"
REPORT = ROOT / "RELEASE-BESTAND-HEILUNG.md"
DEFAULT_MAX_ARTIKEL = 8
UNTERSTUETZT = frozenset({"T5-lesbarkeit", "T6-textverstaendnis", "RD1-duplikate"})
BLOCK_URTEILE = frozenset({"blockiert", "nicht beweisbar"})


class HeilFehler(RuntimeError):
    """Beweis oder Schreibvertrag nicht führbar."""


def _modul(name: str):
    alt = sys.argv
    sys.argv = [alt[0]]
    try:
        return __import__(name)
    finally:
        sys.argv = alt


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def jetzt() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def atomar_schreiben(pfad: Path, data: bytes) -> None:
    """Dateiersatz am gleichen Ort; ein Abbruch lässt nie halbe Bytes zurück."""
    pfad.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(dir=pfad.parent, prefix=f".{pfad.name}.",
                                         delete=False) as fh:
            tmp = Path(fh.name)
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        if pfad.exists():
            os.chmod(tmp, pfad.stat().st_mode & 0o777)
        os.replace(tmp, pfad)
    finally:
        if tmp is not None and tmp.exists():
            tmp.unlink()


def blocker(artikel: dict) -> set[tuple[str, str]]:
    """Stabile Check-Identität; Detailtexte dürfen sich ohne neue Regel ändern."""
    return {(slug, str(b.get("check") or ""))
            for slug, art in artikel.items()
            if art.get("urteil") in BLOCK_URTEILE
            for b in (art.get("befunde") or art.get("checks") or [])
            if b.get("wirkung") == "blockiert" and not b.get("ausnahme")
            and not b.get("werkzeugfehler")}


def menschliche_blocker(art: dict, register: dict) -> list[str]:
    return sorted({str(b["check"]) for b in art.get("befunde") or []
                   if b.get("wirkung") == "blockiert" and not b.get("ausnahme")
                   and not b.get("werkzeugfehler")
                   and (register.get(str(b.get("check")), {}).get("entscheidung")
                        != "auto")})


def automatische_ziele(art: dict, register: dict) -> list[str]:
    return sorted({str(b["check"]) for b in art.get("befunde") or []
                   if b.get("wirkung") == "blockiert" and not b.get("ausnahme")
                   and not b.get("werkzeugfehler") and b.get("check") in UNTERSTUETZT
                   and register.get(str(b.get("check")), {}).get("entscheidung")
                   == "auto"})


def auswahl(ergebnis: dict, register: dict, *, max_artikel: int) -> tuple[list, list]:
    """Deterministische Auswahl; Schutz geht immer vor Durchsatz."""
    if max_artikel < 1 or max_artikel > DEFAULT_MAX_ARTIKEL:
        raise HeilFehler(f"Artikelbudget muss 1–{DEFAULT_MAX_ARTIKEL} sein")
    if ergebnis.get("tool_fehler"):
        raise HeilFehler("Scorecard nicht beweisbar: " +
                         "; ".join(f"{k}: {v}" for k, v in ergebnis["tool_fehler"].items()))
    kandidaten, uebergaben = [], []
    erg = _modul("editorial_review_gate")
    rs = _modul("release_scorecard")
    for slug, art in sorted((ergebnis.get("artikel") or {}).items()):
        if art.get("urteil") not in BLOCK_URTEILE:
            continue
        menschen = menschliche_blocker(art, register)
        ziele = automatische_ziele(art, register)
        grund = None
        if menschen:
            grund = "menschlicher Prüfstand: " + ", ".join(menschen)
        elif not ziele:
            grund = "kein sicherer deterministischer Bestandsheiler"
        elif art.get("risikoklasse") == erg.RISK_HIGH or erg.automatic_write_protected(rs.artikel_pfad(slug)):
            grund = "YMYL-/Freigabe-Schutz"
        if grund:
            uebergaben.append({"slug": slug, "grund": grund,
                               "checks": sorted({str(b.get("check")) for b in art.get("befunde") or []
                                                 if b.get("wirkung") == "blockiert"
                                                 and not b.get("ausnahme")})})
        elif len(kandidaten) < max_artikel:
            kandidaten.append({"slug": slug, "checks": ziele})
        else:
            uebergaben.append({"slug": slug, "grund": "Artikelbudget erreicht", "checks": ziele})
    return kandidaten, uebergaben


def vorschlag(slug: str, raw: str, ziele: list[str]) -> tuple[str, list[str]]:
    """Nur Bibliotheksaufrufe der bestehenden Heiler; kein eigener Textgenerator."""
    if not ziele or not set(ziele) <= UNTERSTUETZT:
        raise HeilFehler(f"{slug}: nicht unterstützte automatische Checks: {sorted(set(ziele) - UNTERSTUETZT)}")
    ph, lh, r5 = (_modul(n) for n in ("politur_heiler", "lesbarkeit_heiler", "r5_absatz_splitter"))
    dg, pv, eg, fm = (_modul(n) for n in ("duplikat_guard", "publikations_vertrag",
                                         "editorial_review_gate", "fm_boundary_guard"))
    post = _modul("post_utils")
    neu = raw
    stufen = []
    if "T6-textverstaendnis" in ziele:
        p = ph.heile_text(slug, neu)
        if p.get("ok") and p.get("neu_raw") != neu:
            neu = p["neu_raw"]
            stufen.append("politur_heiler")
        gespalten, n, warnungen = r5.heal_text(neu, label=slug)
        if warnungen:
            raise HeilFehler(f"{slug}: R5-Heiler nicht beweisbar: {'; '.join(warnungen)}")
        if n and gespalten != neu and not ph.verifiziere(slug, raw, gespalten):
            neu = gespalten
            stufen.append("r5_absatz_splitter")
    if "RD1-duplikate" in ziele:
        teile = post.split_article(neu)
        if not teile[1]:
            raise HeilFehler(f"{slug}: Frontmatter nicht lesbar")
        body, n, _ = dg.auto_fix(f"content/posts/{slug}/index.md", teile[2])
        kandidat = post.join_article(teile[1], body, teile[0])
        # Bewusst konservativ: gelöschte Duplikate dürfen keine eindeutigen
        # Zahlen, Links oder Überschriften mitnehmen. Sonst Redaktion.
        if n and kandidat != neu and not ph.bewahre_form(raw, kandidat):
            neu = kandidat
            stufen.append("duplikat_guard (formbewahrende Teilmenge)")
    if "T5-lesbarkeit" in ziele:
        l = lh.heile_text(slug, neu, ki=False)
        if l.get("ok") and l.get("neu_raw") != neu:
            kandidat = l["neu_raw"]
            if lh.flesch(kandidat, slug) >= lh.flesch(raw, slug):
                neu = kandidat
                stufen.append("lesbarkeit_heiler Stufe A")
    if neu == raw:
        return raw, []
    gruende = []
    gruende += eg.automatic_change_findings(raw, neu)
    gruende += pv.pruefe(slug, raw, neu)
    gruende += ph.bewahre_form(raw, neu)
    grenze, kleber, _text, defekte, doppel = fm.inspect_text(neu)
    if grenze or kleber or defekte or doppel:
        gruende.append("Frontmatter-Grenzen nach Heilung nicht beweisbar")
    if gruende:
        raise HeilFehler(f"{slug}: Schreibtor verworfen: {'; '.join(gruende[:8])}")
    return neu, stufen


def messen() -> dict:
    rs = _modul("release_scorecard")
    iso = _modul("repo_isolation")
    live, entwuerfe, fingerprints = rs.bestand_aufnehmen()
    # Auch Collector-Nebenwirkungen (Affiliate-Profi-Audit) gehören bei einer
    # Planungs-/Auswahlmessung nicht ins Betriebsbuch (C27). Das eigentliche
    # Heilungsereignis wird unten ausdrücklich protokolliert.
    with iso.ledger_sandbox("release-bestand-heiler"):
        return rs.durchfuehren("live", dt.date.today(), live, entwuerfe,
                               fingerprints, rs.zustand_laden(), None)


def git(*args: str) -> str:
    p = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True)
    if p.returncode:
        raise HeilFehler(f"git {' '.join(args)}: {p.stderr.strip()}")
    return p.stdout.strip()


def sauberer_bestand() -> None:
    if git("status", "--porcelain", "--", "content/posts"):
        raise HeilFehler("content/posts ist nicht sauber – keine automatische Heilung über fremde Änderungen")


def zustand_schreiben(zustand: dict) -> None:
    atomar_schreiben(STATE, (json.dumps(zustand, ensure_ascii=False, indent=2) + "\n").encode())
    zeilen = ["# Release-Bestand – Selbstheilung", "",
              f"**Stand:** {zustand['generated_at']} · **Status:** {zustand['status']}", "",
              "Die Scorecard misst; dieser Lauf heilt nur die sichere, deterministische Teilmenge.",
              "Fachbefunde und Freigaben bleiben menschlich. Ein verworfener Versuch wird vollständig zurückgerollt.", "",
              "| Artikel | Ziel-Checks | Heiler |", "|---|---|---|"]
    for a in zustand.get("artikel", []):
        zeilen.append(f"| `{a['slug']}` | {', '.join(a['checks'])} | {', '.join(a.get('stufen', [])) or '–'} |")
    zeilen += ["", "## Übergabe an Redaktion/Fachwache", ""]
    for a in zustand.get("uebergaben", []):
        zeilen.append(f"- `{a['slug']}` ({', '.join(a['checks'])}): {a['grund']}")
    if not zustand.get("uebergaben"):
        zeilen.append("- Keine.")
    if zustand.get("fehler"):
        zeilen += ["", "## Versuch verworfen", "", zustand["fehler"]]
    atomar_schreiben(REPORT, ("\n".join(zeilen) + "\n").encode())


def plan(*, apply: bool = False, max_artikel: int = DEFAULT_MAX_ARTIKEL) -> dict:
    if max_artikel < 1 or max_artikel > DEFAULT_MAX_ARTIKEL:
        raise HeilFehler(f"Artikelbudget muss 1–{DEFAULT_MAX_ARTIKEL} sein")
    ergebnis = messen()
    rs = _modul("release_scorecard")
    register = rs.check_register(rs.ssot_laden())
    ziele, uebergaben = auswahl(ergebnis, register, max_artikel=max_artikel)
    zustand = {"version": 1, "generated_at": jetzt(), "modus": "apply" if apply else "plan",
               "status": "geplant", "basis_commit": git("rev-parse", "HEAD"),
               "baseline_blocker": sorted(blocker(ergebnis["artikel"])),
               "baseline_hashes": {s: a["sha256"] for s, a in ergebnis["artikel"].items()},
               "artikel": [], "uebergaben": uebergaben, "fehler": None}
    for ziel in ziele:
        slug = ziel["slug"]
        pfad = rs.artikel_pfad(slug)
        raw = pfad.read_bytes()
        neu, stufen = vorschlag(slug, raw.decode("utf-8"), ziel["checks"])
        if neu.encode("utf-8") != raw:
            zustand["artikel"].append({**ziel, "pfad": str(pfad.relative_to(ROOT)),
                                       "vorher_sha256": sha(raw), "nachher_sha256": sha(neu.encode()),
                                       "stufen": stufen})
        else:
            uebergaben.append({**ziel, "grund": "deterministische Stufe reicht nicht"})
    if not apply:
        zustand["status"] = "trockenlauf"
        return zustand
    sauberer_bestand()
    # Journal VOR dem ersten Content-Byte: auch ein Prozessabbruch zwischen
    # zwei Dateiersätzen lässt einen beweisbaren Rückweg zurück.
    zustand["status"] = "schreiben"
    zustand_schreiben(zustand)
    try:
        for a in zustand["artikel"]:
            pfad = ROOT / a["pfad"]
            if sha(pfad.read_bytes()) != a["vorher_sha256"]:
                raise HeilFehler(f"{pfad}: inzwischen fremd geändert")
            # Inhalt erneut aus dem geschützten Ursprung erzeugen; kein ungeprüfter Cache.
            neu, _ = vorschlag(a["slug"], pfad.read_text(encoding="utf-8"), a["checks"])
            daten = neu.encode("utf-8")
            if sha(daten) != a["nachher_sha256"]:
                raise HeilFehler(f"{pfad}: Heiler nicht deterministisch")
            atomar_schreiben(pfad, daten)
    except Exception as exc:
        zurueckrollen(zustand, f"Schreiblauf abgebrochen: {exc}")
        raise
    zustand["status"] = "geschrieben" if zustand["artikel"] else "nichts-zu-heilen"
    zustand_schreiben(zustand)
    _modul("audit_log").log_event(module="release_bestand_heiler", action="apply",
                                 input={"artikel": len(zustand["artikel"])},
                                 output={"status": zustand["status"]}, commit=zustand["basis_commit"])
    return zustand


def _journal() -> dict:
    try:
        z = json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HeilFehler(f"Heilungsjournal nicht lesbar: {exc}") from exc
    if z.get("version") != 1:
        raise HeilFehler("Unbekanntes Heilungsjournal")
    return z


def zurueckrollen(zustand: dict, grund: str) -> None:
    """Eigene Bytes zurücknehmen, fremde Bytes niemals überschreiben.

    Erst alle Originale/Blobs prüfen, dann ersetzen. Bei einer fremden
    Änderung werden die übrigen eigenen Änderungen trotzdem zurückgenommen;
    der Konflikt bleibt als Werkzeugfehler sichtbar.
    """
    originale, fremde = [], []
    for a in reversed(zustand.get("artikel", [])):
        pfad = ROOT / a["pfad"]
        aktuell = sha(pfad.read_bytes())
        if aktuell == a["vorher_sha256"]:
            continue
        if aktuell != a["nachher_sha256"]:
            fremde.append(a["pfad"])
            continue
        original = subprocess.run(["git", "show", f"{zustand['basis_commit']}:{a['pfad']}"],
                                  cwd=ROOT, capture_output=True)
        if original.returncode or sha(original.stdout) != a["vorher_sha256"]:
            raise HeilFehler(f"Original nicht beweisbar: {a['pfad']} – nichts ersetzt")
        originale.append((pfad, original.stdout))
    for pfad, data in originale:
        atomar_schreiben(pfad, data)
    zustand.update(status="rollback-unvollstaendig" if fremde else "zurueckgerollt",
                   fehler=grund + (("; fremde Änderungen bewahrt: " + ", ".join(fremde)) if fremde else ""),
                   generated_at=jetzt())
    zustand_schreiben(zustand)
    _modul("audit_log").log_event(module="release_bestand_heiler", action="rollback",
                                 input={"artikel": len(zustand.get("artikel", []))},
                                 output={"grund": grund[:500], "fremde": fremde}, status="error")
    if fremde:
        raise HeilFehler("Fremde Änderungen bewahrt, eigener Rollback unvollständig: " + ", ".join(fremde))


def bestaetigen() -> int:
    z = _journal()
    if z.get("status") != "geschrieben":
        return 0
    try:
        state = json.loads((ROOT / "data" / "release_scorecard_state.json").read_text(encoding="utf-8"))
        if state.get("modus") != "live":
            raise HeilFehler("Nachmessung ist nicht der vollständige Live-Bestand")
        if state.get("generated_at", "") < z["generated_at"]:
            raise HeilFehler("Nachmessung ist älter als der Heilungsversuch")
        if state.get("commit") != z["basis_commit"]:
            raise HeilFehler("Nachmessung gehört nicht zum Basis-Commit des Heilungsversuchs")
        artikel = state.get("artikel") or {}
        if set(artikel) != set(z.get("baseline_hashes") or {}):
            raise HeilFehler("Nachmessung hat einen anderen Live-Bestand")
        gezielte = {a["slug"] for a in z["artikel"]}
        for slug, alter_hash in z["baseline_hashes"].items():
            if slug not in gezielte and artikel[slug].get("sha256") != alter_hash:
                raise HeilFehler(f"{slug}: Nicht-Ziel zwischen Messung und Bestätigung geändert")
        for a in z["artikel"]:
            pfad = ROOT / a["pfad"]
            if sha(pfad.read_bytes()) != a["nachher_sha256"]:
                raise HeilFehler(f"{pfad}: seit dem Versuch fremd geändert")
            if artikel.get(a["slug"], {}).get("sha256") != a["nachher_sha256"]:
                raise HeilFehler(f"{a['slug']}: Scorecard hat nicht die geheilte Bytes geprüft")
            danach = {c["check"] for c in artikel[a["slug"]].get("checks", [])
                      if c.get("wirkung") == "blockiert"}
            if not set(a["checks"]) - danach:
                raise HeilFehler(f"{a['slug']}: kein Ziel-Check behoben")
        vorher = {tuple(x) for x in z["baseline_blocker"]}
        danach = blocker(artikel)
        if state.get("tool_fehler") or danach - vorher or not vorher - danach:
            raise HeilFehler("Nachmessung zeigt neue Blocker/Werkzeugfehler oder keine Verbesserung")
    except HeilFehler as exc:
        zurueckrollen(z, str(exc))
        print(f"↩ Heilung verworfen, Original wiederhergestellt: {exc}")
        return 1
    z.update(status="bestaetigt", generated_at=jetzt())
    zustand_schreiben(z)
    _modul("audit_log").log_event(module="release_bestand_heiler", action="bestaetigt",
                                 input={"artikel": len(z["artikel"])}, output={"status": "bestaetigt"})
    return 0


def selftest() -> list[str]:
    """Eigene Auswahl-/Transaktionslogik, offline und ohne Repo-Schreibzugriff."""
    fehler = []
    register = {c: {"entscheidung": "auto"} for c in UNTERSTUETZT}
    register["F4-fachbefund"] = {"entscheidung": "human"}
    def art(*checks):
        return {"urteil": "blockiert", "risikoklasse": "standard",
                "befunde": [{"check": c, "wirkung": "blockiert"} for c in checks]}
    if menschliche_blocker(art("F4-fachbefund", "T6-textverstaendnis"), register) != ["F4-fachbefund"]:
        fehler.append("Human-Blocker wird nicht erkannt")
    if automatische_ziele(art("RD2-einzigartigkeit"), register):
        fehler.append("RD2 wird fälschlich automatisch geheilt")
    if blocker({"a": art("T6-textverstaendnis")}) != {("a", "T6-textverstaendnis")}:
        fehler.append("Blocker-Identität instabil")
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "index.md"
        p.write_bytes(b"original")
        try:
            atomar_schreiben(p, b"neu")
        except OSError:
            fehler.append("Atomarer Dateiersatz fehlgeschlagen")
        if p.read_bytes() != b"neu" or list(Path(tmp).glob(".*.tmp*")):
            fehler.append("Dateiersatz nicht vollständig")
    return fehler


def _output(name: str, wert: str) -> None:
    """GitHub-Output ohne shell-interpolierte Werte; lokal ein No-op."""
    datei = os.environ.get("GITHUB_OUTPUT")
    if datei:
        with open(datei, "a", encoding="utf-8") as fh:
            fh.write(f"{name}={wert}\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--plan", action="store_true")
    g.add_argument("--apply", action="store_true")
    g.add_argument("--bestaetigen", action="store_true")
    g.add_argument("--zurueckrollen", action="store_true")
    g.add_argument("--journal-status", action="store_true",
                   help="Status des Heilungsjournals ausgeben (ohne Schreibzugriff)")
    g.add_argument("--selftest", action="store_true")
    ap.add_argument("--max-artikel", type=int, default=DEFAULT_MAX_ARTIKEL)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        fehler = selftest()
        for f in fehler:
            print("🛑", f)
        print("❌ Selbsttest rot" if fehler else "✅ Bestands-Selbstheilung: Auswahl, Schutz und Dateiersatz grün")
        return 2 if fehler else 0
    try:
        if args.journal_status:
            print(_journal().get("status") if STATE.exists() else "kein-journal")
            return 0
        if args.bestaetigen:
            code = bestaetigen()
            _output("zurueckgerollt", "true" if code == 1 else "false")
            return code
        if args.zurueckrollen:
            z = _journal()
            aktiv = z.get("status") in ("schreiben", "geschrieben")
            if aktiv:
                zurueckrollen(z, "Lauf abgebrochen – vorsorglicher Rollback")
            _output("zurueckgerollt", "true" if aktiv else "false")
            return 0
        z = plan(apply=args.apply, max_artikel=args.max_artikel)
        _output("geaendert", "true" if args.apply and z.get("artikel") else "false")
        if args.json:
            print(json.dumps(z, ensure_ascii=False, indent=2))
        else:
            print(f"Bestands-Selbstheilung ({z['status']}): {len(z['artikel'])} Artikel, "
                  f"{len(z['uebergaben'])} Übergaben.")
        return 0
    except Exception as exc:
        print(f"🛑 Bestands-Selbstheilung nicht beweisbar: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
