#!/usr/bin/env python3
# ============================================================
#  BESTANDS-EINZIGARTIGKEIT-GATE – die Lücke, durch die #1027 entstand
#
#  WARUM DIESES TOR (Meldung #1027, 04.11.2026)
#  --------------------------------------------
#  Zweimal wurde derselbe Fehler auf zwei verschiedene Weisen geheilt, und
#  beide Male blieb ein Weg offen, auf dem er zurückkommen konnte:
#
#    · #714/#766 heilten den BESTAND (Faustregel-Massensatz, Haus-Formeln).
#    · #1027 heilte den Bestand und fügte V4 in den Publikations-Vertrag ein.
#
#  V4 ist die richtige Antwort – aber sie wirkt nur dort, wo ein Schreiber
#  sie aufruft. `publikations_vertrag.pruefe` wird heute von
#  `redaktions_standard.py`, `extend_articles.py`, `profi_polish.py` und
#  `lesbarkeit_heiler.py` benutzt. Daneben schreiben `satz_heiler.py`,
#  `politur_heiler.py`, `politur_ruine_heiler.py`, `r5_absatz_splitter.py`,
#  `endredaktion.py`, `update_articles.py`, `hardcases_guard.py`,
#  `faktenfrische.py`, `fix_*.py` und `generate_kurzantworten.py` weiter
#  direkt in `content/posts/**`. Und der Fall, der #1027 überhaupt ausgelöst
#  hat, war gar kein Schreiber: Commit 69f08c40 (#1017) hat den BNetzA-Absatz
#  von Hand in drei Live-Artikel gesetzt.
#
#  Ein Vertrag, den man aufrufen MUSS, ist eine Empfehlung. Ein Tor, das
#  jeden geänderten Artikel MISST – egal wer ihn geschrieben hat –, ist eine
#  Wache. Dieses Skript ist dieses Tor:
#
#    Es vergleicht die Fassung aus der Git-Basis mit der Fassung im
#    Arbeitsbaum und meldet NUR das, was DER DIFF NEU erzeugt hat.
#
#  DIE MESSUNG IST DIE DES AUDITS (keine zweite Wahrheit)
#  -----------------------------------------------------
#    · `check_uniqueness.clean_body`   – dieselbe Textnormierung
#    · `check_uniqueness.ngrams`       – dieselbe 7-Gramm-Messung
#    · `check_uniqueness.KRITISCH_AB`  – dieselbe Schwelle (5)
#    · `check_uniqueness.load_bestand` – derselbe Leseweg für die Gegenseite
#  Es gibt keine eigene Zahl, keine Ausnahmeliste für Rechtsprosa und keinen
#  zweiten Detektor. Was das Tagesaudit als „kritisch (live↔live)" meldet,
#  meldet dieses Tor am Diff – nur früher.
#
#  ALTLASTEN WERDEN NICHT ANGELASTET
#  ---------------------------------
#  Befund ist eine Überlappung nur dann, wenn sie
#
#    (a) neu ENTSTEHT   (vorher < KRITISCH_AB, nachher >= KRITISCH_AB), oder
#    (b) VERSTÄRKT wird (vorher >= KRITISCH_AB und nachher > vorher).
#
#  Wer eine Dublette abbaut, wird nie bestraft. Das ist dieselbe Regel wie
#  in `check_uniqueness.aenderung_befunde` (V4) und der Grund, warum die
#  Heilung von #1027 selbst nicht am Tor scheitert: Sie senkt Zahlen.
#
#  WAS DAS TOR *NICHT* TUT
#  -----------------------
#    · Es schreibt nichts. Kein Auto-Heiler: eine fremde Rechtspassage
#      umzuschreiben ist eine redaktionelle Aufgabe, keine Maschinenaufgabe.
#    · Es prüft keine Altlasten im Bestand – dafür ist das Tagesaudit da
#      (`check_uniqueness.py`). Wer hier eine Zahl sieht, hat sie gerade
#      erzeugt; wer dort eine Zahl sieht, erbt sie.
#
#  BENUTZUNG
#  ---------
#    python3 scripts/bestand_einzigartigkeit_gate.py --base origin/main
#    python3 scripts/bestand_einzigartigkeit_gate.py --base HEAD   # lokal
#    python3 scripts/bestand_einzigartigkeit_gate.py --selftest    # Sabotage
#    python3 scripts/bestand_einzigartigkeit_gate.py --base X --json
#
#  Exit 0 = kein neuer Befund · 1 = Diff erzeugt eine Dublette
#  Exit 2 = Selbsttest rot oder Messung nicht möglich (fail-closed)
# ============================================================
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import PurePosixPath

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BLOG_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import check_uniqueness as cu  # noqa: E402  (die eine Messung)

POSTS_PREFIX = ("content", "posts")

# Ein Artikel gilt als „live", wenn die Basis-Fassung ausgeliefert wurde.
# Die Definition kommt aus `check_uniqueness.audit_publication_state` –
# also aus `post_utils.build_state`, nicht aus einem `draft:`-Regex.


def _git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=BLOG_DIR).decode("utf-8")


def aenderungen(base: str) -> list[str]:
    """Geänderte Artikel-Bundles zwischen `base` und dem Arbeitsbaum.

    `--diff-filter=M` wie in `ymyl_siegel_wache.pruefe_base`: neue Artikel
    haben keine Vorfassung und damit keine Altlast, die sie verletzen
    könnten – ihr Einzigartigkeitsurteil spricht das Publish-Gate.
    """
    _basis_pruefen(base)
    out = _git(["diff", "--name-only", "-z", "--diff-filter=M", "--no-renames",
                base, "--", "content/posts"])
    pfade = [p for p in out.split("\0") if p]
    erlaubt = []
    for name in pfade:
        teile = PurePosixPath(name).parts
        if len(teile) == 4 and teile[:2] == POSTS_PREFIX and teile[-1] == "index.md":
            erlaubt.append(name)
    return sorted(erlaubt)


def _basis_pruefen(base: str) -> None:
    """Klartext, wenn die Basis lokal fehlt – statt eines nackten git-Fehlers.

    Im CI ist das der Regelfall bei einem seichten Checkout: `git diff <sha>`
    scheitert mit Exit 128, das Tor meldet „nicht messbar". Die richtige
    Antwort ist nicht, die Messung zu lockern, sondern die Basis zu holen –
    der Workflow läuft mit `fetch-depth: 0` und lädt notfalls nach. Diese
    Meldung sagt das, damit niemand das Tor abschaltet statt den Checkout
    zu reparieren (Lehre #1027).
    """
    if not base or base.startswith("-"):
        raise ValueError(f"unbrauchbare Basis {base!r} – fail-closed")
    try:
        _git(["cat-file", "-e", f"{base}^{{commit}}"])
    except subprocess.CalledProcessError:
        raise ValueError(
            f"Basis {base} liegt nicht im lokalen Objektspeicher – die "
            f"Einzigartigkeit ist so nicht messbar. Abhilfe: "
            f"`git fetch --no-tags --deepen=200 origin` (oder "
            f"`fetch-depth: 0` beim Checkout). Die Prüfung bleibt stehen, "
            f"sie wird nur mit History versorgt.") from None


def _fassung(base: str, pfad: str) -> str | None:
    """Inhalt der Basis-Fassung (None = in der Basis nicht vorhanden)."""
    try:
        return _git(["show", f"{base}:{pfad}"])
    except subprocess.CalledProcessError:
        return None


def _slug(pfad: str) -> str:
    return cu._slug(os.path.join(BLOG_DIR, pfad))


def _grams_bestand(bestand: dict) -> dict:
    """Gegenseite → 7-Gramme, EINMAL gerechnet (der Bestand hat ~106 Artikel)."""
    return {info["slug"]: cu.ngrams(info.get("body", ""), cu.PHRASE_LEN)
            for info in bestand.values()}


def dubletten_einer_aenderung(slug: str, alt_raw: str, neu_raw: str,
                             grams_bestand: dict) -> list[dict]:
    """Reine Messung: welche Paare schiebt diese Änderung über die Schwelle?

    Kein Dateizugriff, keine Uhr, kein Git – damit ist die REGEL selbst
    prüfbar (Sabotage-Proben unten) und nicht nur ihr Aufrufer. Rückgabe
    sind Datensätze `{paar, andere, vorher, nachher, beispiel, art}`; das
    Paar wird kanonisch (alphabetisch) benannt, damit ein Paar, in dem beide
    Seiten geändert wurden, nur EINEN Befund ergibt.
    """
    alt_grams = cu.ngrams(cu.clean_body(alt_raw), cu.PHRASE_LEN)
    neu_grams = cu.ngrams(cu.clean_body(neu_raw), cu.PHRASE_LEN)
    treffer: list[dict] = []
    for andere, andere_grams in sorted(grams_bestand.items()):
        if andere == slug:
            continue                      # der eigene Artikel ist keine Gegenseite
        alt_ov = len(alt_grams & andere_grams)
        neu_ov = len(neu_grams & andere_grams)
        if neu_ov < cu.KRITISCH_AB:
            continue                      # unter der Schwelle: normal, kein Befund
        if neu_ov <= alt_ov:
            continue                      # unverändert oder abgebaut: kein Vorwurf
        gemeinsam = sorted(neu_grams & andere_grams)
        paar = tuple(sorted((slug, andere)))
        treffer.append({
            "paar": paar, "andere": andere, "vorher": alt_ov, "nachher": neu_ov,
            "beispiel": gemeinsam[0],
            "art": "erzeugt" if alt_ov < cu.KRITISCH_AB else "verstärkt",
        })
    return treffer


def befunde_fuer_aenderung(slug: str, alt_raw: str, neu_raw: str,
                           grams_bestand: dict) -> list[str]:
    """Wie `dubletten_einer_aenderung`, aber als lesbare Meldungen."""
    return [_meldung(d) for d in
            dubletten_einer_aenderung(slug, alt_raw, neu_raw, grams_bestand)]


def _meldung(d: dict) -> str:
    links, rechts = d["paar"]
    return (f"{links} ↔ {rechts}: {d['nachher']} gleiche "
            f"{cu.PHRASE_LEN}-Wort-Phrasen (vorher {d['vorher']}, Schwelle "
            f"{cu.KRITISCH_AB}) – diese Änderung {d['art']} eine kritische "
            f"Textdopplung; z. B. „{d['beispiel']}“")


def pruefe_diff(base: str, bestand: dict | None = None,
                aenderungen_liste: list[str] | None = None,
                inhalte: dict | None = None) -> list[str]:
    """Befunde: Änderungen im Diff, die eine kritische Dublette ERZEUGEN.

    `inhalte` ersetzt nur im Selbsttest den Dateizugriff (Pfad → neue Fassung).
    """
    bestand = cu.lade_bestand() if bestand is None else bestand
    if not bestand:
        raise ValueError("Bestand ist leer – die Einzigartigkeit ist nicht "
                         "messbar (fail-closed)")
    grams = _grams_bestand(bestand)
    gefunden: dict[tuple, dict] = {}
    fehler: list[str] = []
    for pfad in (aenderungen(base) if aenderungen_liste is None
                 else aenderungen_liste):
        alt_raw = _fassung(base, pfad)
        if alt_raw is None:
            continue                      # neuer Artikel: keine Altlast möglich
        if inhalte is not None:
            neu_raw = inhalte.get(pfad)
            if neu_raw is None:
                continue
        else:
            try:
                with open(os.path.join(BLOG_DIR, pfad), encoding="utf-8") as fh:
                    neu_raw = fh.read()
            except OSError as exc:
                fehler.append(f"nicht lesbar ({exc.__class__.__name__}) – "
                              f"fail-closed: {pfad}")
                continue
        for treffer in dubletten_einer_aenderung(_slug(pfad), alt_raw, neu_raw, grams):
            # Ein Paar, in dem BEIDE Seiten geändert wurden, wird zweimal
            # gemessen – beide Diffs haben die Dopplung erzeugt. Für die
            # Redaktion ist es EIN Befund; gemeldet wird der höhere Wert.
            vorher = gefunden.get(treffer["paar"])
            if vorher is None or treffer["nachher"] > vorher["nachher"]:
                gefunden[treffer["paar"]] = treffer
    return fehler + [_meldung(d) for _, d in sorted(gefunden.items())]


# ============================================================
#  SELFTEST – die Wache ist beweispflichtig, bevor sie blockiert
# ============================================================
FREMD = ("Lies die Laufzeit in deinem Vertrag bevor du ein neues Angebot "
         "annimmst denn die erste feste Laufzeit darf hoechstens vierundzwanzig "
         "Monate dauern und danach kannst du jederzeit mit einer Frist von "
         "einem Monat kuendigen wenn der Vertrag still weiterlaeuft.")
EIGEN = ("Ein Router steht selten am besten Platz; wer ihn vom Boden auf das "
         "Regal hebt, gewinnt oft mehr als ein neuer Tarif verspricht. Miss das "
         "WLAN in jedem Zimmer, bevor du den Vertrag anfasst.")
# Ein dritter, eigenständiger Text: der Abbau einer Altlast darf keine NEUE
# Dublette erzeugen – sonst prüft der Fall nicht den Abbau, sondern eine
# Übernahme (der Selbsttest hat genau das am 04.11.2026 aufgedeckt).
DRITT = ("Die Schlussrechnung kommt meist dann, wenn niemand mehr hinsieht. "
         "Notiere den Endstand am letzten Liefertag und vergleiche ihn mit dem "
         "Foto vom Zaehler; so bleibt jede Position nachpruefbar.")


def _rohtext(body: str) -> str:
    return '---\ntitle: "X"\ndraft: false\n---\n\n' + body + "\n"


def selftest() -> int:
    """Sabotage-Proben: Fehler MÜSSEN erkannt werden, Gutes MUSS still bleiben."""
    fehler: list[str] = []
    bestand = {
        "/k/posts/2026-10-01-fremd/index.md": {
            "slug": "2026-10-01-fremd", "title": "Fremd",
            "body": cu.clean_body(_rohtext(FREMD)),
            "live": True, "grund": "", "date": "2026-10-01T08:00:00Z"},
        "/k/posts/2026-10-02-eigen/index.md": {
            "slug": "2026-10-02-eigen", "title": "Eigen",
            "body": cu.clean_body(_rohtext(EIGEN)),
            "live": True, "grund": "", "date": "2026-10-02T08:00:00Z"},
    }
    grams = _grams_bestand(bestand)
    slug = "2026-11-01-probe"

    # 1) Die geplante Fassung übernimmt die fremde Passage → Befund, mit Namen.
    b1 = befunde_fuer_aenderung(slug, _rohtext(EIGEN), _rohtext(FREMD), grams)
    if not b1:
        fehler.append("eine übernommene Fremdpassage wird nicht erkannt "
                      "(das ist genau die Lücke aus #1027)")
    elif "2026-10-01-fremd" not in b1[0]:
        fehler.append("der Befund nennt den Gegenartikel nicht – der Redakteur "
                      "kann ihn nicht aufsuchen")

    # 2) Eigener Text bleibt still (kein Scheinrot).
    b2 = befunde_fuer_aenderung(slug, _rohtext(EIGEN),
                                _rohtext(EIGEN + " Ein weiterer Satz."), grams)
    if b2:
        fehler.append(f"eigenständiger Text erhält einen Befund: {b2[:1]}")

    # 3) Altlast: stand schon vorher über der Schwelle und wächst nicht → still.
    b3 = befunde_fuer_aenderung(slug, _rohtext(FREMD),
                                _rohtext(FREMD + " Zusatz."), grams)
    if b3:
        fehler.append(f"unveränderte Altlast wird als neuer Verstoß gemeldet: {b3[:1]}")

    # 4) Altlast wird ABGEBAUT → still (wer heilt, wird nicht bestraft).
    b4 = befunde_fuer_aenderung(slug, _rohtext(FREMD), _rohtext(DRITT), grams)
    if b4:
        fehler.append(f"Abbau einer Altlast wird bestraft: {b4[:1]}")

    # 5) Der eigene Artikel ist keine Gegenseite.
    b5 = befunde_fuer_aenderung("2026-10-01-fremd", _rohtext(EIGEN),
                                _rohtext(FREMD), grams)
    if b5:
        fehler.append(f"der geänderte Artikel wird mit sich selbst verglichen: {b5[:1]}")

    # 6) Leerer Bestand = keine Messung = kein Freispruch (fail-closed).
    try:
        pruefe_diff("HEAD", bestand={})
    except ValueError:
        pass
    else:
        fehler.append("leerer Bestand gilt als freigegeben (fail-open)")

    # 7) Die Schwelle ist importiert, nicht kopiert (keine zweite Wahrheit).
    with open(__file__, encoding="utf-8") as fh:
        if any(z.strip().startswith("KRITISCH_AB") for z in fh):
            fehler.append("das Gate definiert eine eigene Schwelle statt der "
                          "SSOT check_uniqueness.KRITISCH_AB")

    # 8) Die Messung muss die des Audits sein – nicht eine ähnliche.
    if cu.KRITISCH_AB != 5:
        fehler.append(f"die Audit-Schwelle ist nicht mehr 5, sondern "
                      f"{cu.KRITISCH_AB} – Gate und Audit laufen auseinander")

    if fehler:
        print("🛑 BESTANDS-EINZIGARTIGKEIT-GATE – SELFTEST FEHLGESCHLAGEN "
              "(Exit 2, die Wache selbst ist defekt):")
        for f in fehler:
            print(f"   - {f}")
        return 2
    print("✅ BESTANDS-EINZIGARTIGKEIT-GATE-SELFTEST bestanden: übernommene "
          "Fremdpassage erkannt, eigener Text still, Altlast weder angelastet "
          "noch als Freispruch gewertet, fail-closed, Schwelle importiert.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Prüft, ob ein Diff eine kritische Textdopplung erzeugt.")
    ap.add_argument("--base", default=os.environ.get("EINZIGARTIGKEIT_BASE", "HEAD"),
                    help="Git-Basis für den Vergleich (Default: HEAD)")
    ap.add_argument("--selftest", action="store_true", help="nur Sabotage-Schutz")
    ap.add_argument("--json", action="store_true", help="maschinenlesbare Ausgabe")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)

    code = selftest()
    if code:                      # Selbsttest zuerst – eine Wache, die sich
        return code               # nicht beweisen kann, blockiert nicht.
    if args.selftest:
        return 0

    try:
        befunde = pruefe_diff(args.base)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"🛑 Einzigartigkeit nicht messbar ({exc.__class__.__name__}: {exc}) "
              f"– fail-closed, die Änderung wird nicht freigegeben.")
        return 2

    if args.json:
        print(json.dumps({"base": args.base, "befunde": befunde}, ensure_ascii=False))
    elif befunde:
        print(f"🛑 {len(befunde)} neue kritische Textdopplung(en) im Diff gegen "
              f"{args.base}:")
        for b in befunde:
            print(f"   - {b}")
        print("\n   Das ist keine Altlast: die Zahlen sind VORHER kleiner. "
              "Die Passage eigenständig formulieren – Fakten, Quellen und "
              "Zahlen bleiben unverändert. Kein Auto-Heiler (V4/PR #1043).")
    else:
        print(f"✅ Kein geänderter Artikel erzeugt eine kritische Textdopplung "
              f"(Basis {args.base}, Schwelle {cu.KRITISCH_AB} geteilte "
              f"{cu.PHRASE_LEN}-Wort-Phrasen).")
    return 1 if befunde else 0


if __name__ == "__main__":
    sys.exit(main())
