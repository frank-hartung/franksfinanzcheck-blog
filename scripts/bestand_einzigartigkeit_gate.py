#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
#  BESTANDS-EINZIGARTIGKEITS-DIFF-TOR (#1027 / #1060, 06.11.2026)
# ------------------------------------------------------------
#  WARUM ES DIESES TOR GIBT
#
#  Der Vorfall: Am 02.11.2026 (#1017, committet als 69f08c40) landete
#  derselbe BNetzA-Absatz wörtlich in drei LIVE Gas-Artikeln
#  (08-10-sicher-heizen, 08-12-preisgarantie-gas, 08-24-preisgarantie-gas).
#  Zwei Tage später (03.11.) meldete das Einzigartigkeits-Tagesaudit zwei
#  kritische live↔live-Überlappungen (#1027). Seither war Ebene 1–3
#  geheilt (Bestand umformuliert, `check_uniqueness.aenderung_befunde` +
#  V4 im Publikations-Vertrag) — Ebene 4 nicht:
#
#    * Der Publikations-Vertrag misst GEPLANTE Änderungen geklammerter
#      Schreiber (redaktions_standard `--ai`). Handänderungen und
#      Skripte jenseits dieses Weges (heal_article, update_articles,
#      fix_*.py, ein mutiges `git commit` eines Menschen) liefen an
#      JEDER Einzigartigkeitsmessung vorbei.
#
#  Dieses Tor ist die Antwort auf Ebene 4. Es misst GENAU den Unterschied,
#  den ein Diff darstellt – egal welches Werkzeug oder welcher Mensch
#  geschrieben hat – und verwirft ALLE Altlasten:
#
#    Gemeldet wird NUR, wenn `nachher >= KRITISCH_AB` UND `nachher > vorher`.
#    Eine Altlast wird weder angelastet noch als Freispruch gewertet.
#
#  EINE MESSUNG, KEINE ZWEITE WAHRHEIT
#    `clean_body`, `ngrams`, `KRITISCH_AB` und `lade_bestand` kommen aus
#    `check_uniqueness`; die V4-Entscheidungslogik
#    (`aenderung_befunde`) wird mit `strukturiert=True` aufgerufen.
#    Dieses Modul definiert KEINE Schwelle und kopiert KEINE Regel.
#
#  KANONISCHE PARE
#    Paare werden alphabetisch kanonisch geordnet und genau EINMAL gemeldet;
#    der eigene Slug (die geänderte Datei) ist nie Gegner gegen sich selbst.
#
#  FAIL-CLOSED
#    Leerer Bestand oder unauflösbare Git-Basis → Exit 2 (Werkzeugfehler),
#    niemals ein leeres grünes Ergebnis.
#
#  KEIN AUTO-HEILER
#    Das Tor meldet und blockiert. Es formuliert nichts um.
#
#  NUTZUNG
#    python3 scripts/bestand_einzigartigkeit_gate.py --basis HEAD~1
#    python3 scripts/bestand_einzigartigkeit_gate.py --selftest
#
#  Exit: 0 = keine neuen kritischen Überlappungen
#        1 = mindestens eine NEUE kritische Überlappung (fail-closed)
#        2 = Werkzeugfehler / Selbsttest rot
# ============================================================
import argparse
import os
import subprocess
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BLOG_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import check_uniqueness as cu  # noqa: E402  DIE eine Messung

# Schwert-Import: bewusst KEINE lokale Zahl. Wer hier eine kopierte
# Schwelle hinterlässt, umgeht den Audit-Maßstab – Governance C48 findet sie.
KRITISCH_AB = cu.KRITISCH_AB
PHRASE_LEN = cu.PHRASE_LEN
POSTS_REL = "content/posts"


class GateFehler(Exception):
    """Unauflösbare Grundlage (Basis-Ref, leserbare Posts, leerer Bestand)."""


def _slug_aus_relpath(rel: str) -> str:
    base = os.path.splitext(os.path.basename(rel))[0]
    if base and base != "index":
        return base
    return os.path.basename(os.path.dirname(rel))


def _lade_bestand_aus_root(root: str) -> dict:
    """Bestand eines gegebenen Arbeitsbaums (Tests/Dritt-Wurzeln)."""
    import glob as _glob

    pfade = sorted(set(
        _glob.glob(os.path.join(root, POSTS_REL, "*.md"))
        + _glob.glob(os.path.join(root, POSTS_REL, "*", "index.md"))))
    return cu.lade_bestand(paths=pfade)


def git_text_at(ref: str, relpath: str, root: str = BLOG_DIR) -> str | None:
    """Datei an der Git-Basis lesen (None = existierte dort nicht).

    Unauflösbare Basis oder unlesbare Blobs sind KEIN leeres Ergebnis:
    ein Diff gegen nichts hätte jeden Befund unsichtbar gemacht.
    """
    probe = subprocess.run(
        ["git", "-C", root, "cat-file", "-e", f"{ref}:{relpath}"],
        capture_output=True, text=True)
    if probe.returncode != 0:
        return None  # neue Datei – alles ist neu
    blob = subprocess.run(
        ["git", "-C", root, "show", f"{ref}:{relpath}"],
        capture_output=True)
    if blob.returncode != 0:
        raise GateFehler(
            f"Git-Objekt {ref}:{relpath} nicht lesbar: "
            f"{blob.stderr.decode(errors='replace').strip()}")
    return blob.stdout.decode("utf-8", errors="replace")


def changed_post_paths(basis: str, root: str = BLOG_DIR) -> list[str]:
    """Geänderte/unversionierte Posts der Basis-Diff (Arbeitsbaum)."""
    diff = subprocess.run(
        ["git", "-C", root, "diff", "--name-only", basis, "--", POSTS_REL],
        capture_output=True, text=True)
    if diff.returncode != 0:
        raise GateFehler(
            f"Git-Basis {basis!r} unauflösbar: {diff.stderr.strip()}")
    others = subprocess.run(
        ["git", "-C", root, "ls-files", "--others", "--exclude-standard",
         "--", POSTS_REL],
        capture_output=True, text=True)
    if others.returncode != 0:
        raise GateFehler(
            f"git ls-files --others fehlgeschlagen: {others.stderr.strip()}")
    paths = {line.strip() for line in (diff.stdout + "\n" + others.stdout).splitlines()
             if line.strip() and line.strip().endswith(".md")}
    return sorted(p for p in paths if _slug_aus_relpath(p))


def befunde(changed: list[str], basis: str,
            bestand: dict | None = None,
            root: str = BLOG_DIR) -> list[dict]:
    """Kanonisch deduplizierte V4-Befunde des Diffs.

    Je Paar genau EIN Eintrag, alphabetisch kanonisch geordnet; live und
    Entwurf zählen (die Entwürfe sind die Vorabaufgabe VOR der Frage,
    ob ein Artefakt live geht – dieselbe Logik wie in der V4-Messung).
    """
    if bestand is None:
        bestand = (cu.lade_bestand() if os.path.realpath(root) == os.path.realpath(BLOG_DIR)
                   else _lade_bestand_aus_root(root))
    if not bestand:
        raise GateFehler(
            "leerer Bestand (0 Artikel) – das Diff-Tor weigert sich zu raten "
            "und bleibt fail-closed rot")
    paare: dict[tuple, dict] = {}
    for rel in sorted(changed):
        slug = _slug_aus_relpath(rel)
        alt_text = git_text_at(basis, rel, root=root) or ""
        try:
            with open(os.path.join(root, rel), encoding="utf-8") as fh:
                neu_text = fh.read()
        except OSError:
            # Datei in der Basis gelöscht oder unlesbar – nichts Neues erzeugt.
            continue
        fund_funde = cu.aenderung_befunde(
            slug, alt_text, neu_text, bestand=bestand, strukturiert=True)
        for f in fund_funde:
            andere = f["anderer"]
            key = tuple(sorted((slug, andere)))
            prev = paare.get(key)
            if prev is None:
                paare[key] = dict(f, geaendert=slug)
    return [paare[k] for k in sorted(paare)]


def _block(eintrag: dict) -> str:
    a, b = sorted((eintrag["geaendert"], eintrag["anderer"]))
    return (f"  🚨 NEU: {a} ↔ {b} – {eintrag['neu_n']} gleiche "
            f"{eintrag['n']}-Wort-Phrasen (war {eintrag['alt_n']}; z. B. "
            f"„{eintrag['beispiel']}“) – ab {KRITISCH_AB} ist es Dopplung, "
            f"Passage eigenständig formulieren")


# ============================================================
#  SELFTEST – das Tor ist beweispflichtig (Sabotage-Proben)
# ============================================================
def selftest() -> int:
    fehler: list[str] = []
    passage = ("Bei einer einseitigen Preisaenderung koennen Verbraucher "
               "grundsaetzlich ohne Frist zum Zeitpunkt der Aenderung "
               "kuendigen; der Vertrag endet am Vortag der Aenderung.")
    passage_teil = ("Bei einer einseitigen Preisaenderung koennen Verbraucher "
                    "grundsaetzlich ohne Frist zum Zeitpunkt der Aenderung kuendigen.")
    eigen = ("Ein Router steht selten am besten Platz; wer ihn vom Boden auf "
             "das Regal hebt, gewinnt oft mehr als ein neuer Tarif verspricht.")
    eigener = ("Ein zweiter, ganz eigener Gedanke über Katzen, Hypotheken "
               "und den Herbst steht hier.")
    korpus = {
        "k/dsl":  {"slug": "2026-10-07-dsl", "body": cu.clean_body(passage),
                   "live": True, "grund": "", "date": "2026-09-11T08:00:00Z"},
        "k/entw": {"slug": "2026-09-01-entwurf", "body": cu.clean_body(passage),
                   "live": False, "grund": "draft:true", "date": "2026-09-01T08:00:00Z"},
        "k/gegen": {"slug": "2026-10-07-gegen", "body": cu.clean_body(eigen),
                    "live": True, "grund": "", "date": "2026-10-07T08:00:00Z"},
    }

    def _probe(name: str, alt: str, neu: str, bestand: dict | None,
               erwartet: int) -> None:
        res = cu.aenderung_befunde("2026-10-07-eigen", alt, neu,
                                   bestand=bestand, strukturiert=True)
        if len(res) != erwartet:
            fehler.append(f"{name}: erwartet {erwartet} Befund(e), "
                          f"bekam {len(res)}: {res}")

    # 1) Erzeugung wird erkannt (Auslöser 69f08c40/#1027) – beide Gegner
    #    (live UND Entwurf) tragen den Befund.
    _probe("Erzeugung gegen Live- und Entwurf-Artikel", eigen,
           eigen + " " + passage, korpus, 2)
    # 2) Altlast ist still: alt == neu (selbst dann, wenn der Entwurf bzw.
    #    der Live-Artikel dieselbe Passage tragen – sie zählt nicht als neu).
    _probe("Altlast bleibt still", eigen + " " + passage,
           eigen + " " + passage, korpus, 0)
    # 3) Verstärkung ab Teil-Passage wird erkannt (Teil- → Voll-Passage in
    #    beiden Gegnern).
    _probe("Verstärkung", eigen + " " + passage_teil,
           eigen + " " + passage, korpus, 2)
    # 4) unverwandter Satz erzeugt nichts
    _probe("unverwandter Satz still", eigen, eigen + " " + eigener, korpus, 0)
    # 5) Leerer Bestand → fail-closed (Governance-Versprechen)
    try:
        befunde(["2026-10-07-eigen/index.md"], "HEAD", bestand={})
        fehler.append("leerer Bestand gilt als sauber (fail-open)")
    except GateFehler:
        pass
    # 6) Der eigene Slug ist nie Gegenseite
    funde = cu.aenderung_befunde("2026-10-07-dsl", eigen, eigen + " " + passage,
                                 bestand=korpus, strukturiert=True)
    if any(f["anderer"] == "2026-10-07-dsl" for f in funde):
        fehler.append("eigener Slug zählt als Gegenartikel")
    # 7) Die Messung importiert die Schwelle (Sabotage-Schutz C48): Wer
    #    cu.KRITISCH_AB anhebt, hebt sie hiermit gemeinsam – eine zweite,
    #    kopierte Zahl würde das nicht mitmachen.
    echtes_min = cu.KRITISCH_AB
    try:
        cu.KRITISCH_AB = 99
        funde = cu.aenderung_befunde("2026-10-07-eigen", eigen,
                                     eigen + " " + passage,
                                     bestand=korpus, strukturiert=True)
        if funde:
            fehler.append("angehobene SSOT-Schwelle ändert das Urteil nicht "
                          "– KRITISCH_AB wäre hier kopiert")
    finally:
        cu.KRITISCH_AB = echtes_min

    if fehler:
        print("🛑 BESTANDS-EINZIGARTIGKEITS-DIFF-TOR – SELFTEST FEHLGESCHLAGEN "
              "(Exit 2):")
        for f in fehler:
            print(f"   - {f}")
        return 2
    print("✅ BESTANDS-EINZIGARTIGKEITS-DIFF-TOR-SELFTEST bestanden: Erzeugung, "
          "Verstärkung, Altlast-Versicherung, leerer Bestand (fail-closed), "
          "SSOT-Schwertfunktion – #1060.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Diff-Tor Bestands-Einzigartigkeit (#1027/#1060): meldet nur "
                    "NEUE kritische Überlappungen gegen die Git-Basis.")
    parser.add_argument("--basis",
                        help="Git-Ref der Vergleichsbasis "
                             "(CI: pull_request.base.sha || github.event.before || HEAD~1)")
    parser.add_argument("--root", default=BLOG_DIR,
                        help="Arbeitsbaum mit content/posts (Standard: Repo-Root)")
    parser.add_argument("--selftest", action="store_true",
                        help="Sabotage-Proben statt Bestand (C6/C48)")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.basis:
        parser.error("--basis fehlt (oder --selftest verwenden)")

    try:
        changed = changed_post_paths(args.basis, root=args.root)
        funde = befunde(changed, args.basis, root=args.root)
    except GateFehler as exc:
        print(f"🛑 BESTANDS-EINZIGARTIGKEITS-DIFF-TOR – WERKZEUGFEHLER: {exc}")
        return 2

    basis_kurz = args.basis[:12]
    if not changed:
        print(f"✅ Diff-Tor: keine content/posts-Änderungen gegen {basis_kurz} – "
              f"nichts zu messen, sauber.")
        return 0
    if not funde:
        print(f"✅ Diff-Tor: {len(changed)} geänderte(r) Artikel gegen {basis_kurz} – "
              f"keine NEUE kritische Überlappung (ab {KRITISCH_AB} geteilte "
              f"{PHRASE_LEN}-Wort-Phrasen). Altlasten werden dem Diff nicht angelastet.")
        return 0

    print(f"🚨 BESTANDS-EINZIGARTIGKEITS-DIFF-TOR: {len(funde)} NEUE kritische "
          f"Überlappung(en) gegen {basis_kurz} – der Artikel darf in dieser "
          f"Fassung nicht live:")
    for eintrag in funde:
        print(_block(eintrag))
    print("   Jede Meldung ist eine Passage, die eigenständig formuliert werden "
          "muss (V4, Audit-Messung, #1027).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
