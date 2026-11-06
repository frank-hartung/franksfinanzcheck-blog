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
#  KEIN AUTO-HEILER FÜR PROSA
#    Das Tor meldet und blockiert. Es formuliert NICHTS um.
#    Ausnahme (06.11.2026, ausdrücklicher Auftrag): `--heilen` entfernt eine
#    Passage, die beweisbar WÖRTLICH aus einem anderen Artikel stammt und in
#    diesem Diff NEU hinzukam – das ist keine Formulierung, das ist das
#    Zurücknehmen einer Kopie. Live-Artikel nur mit `--auch-live`.
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


# ============================================================
#  SELBSTHEILUNG – aber nur die KOPIE, niemals die Prosa
# ============================================================
#  Das Tor meldete bisher nur („KEIN AUTO-HEILER“). Für alles, was ein
#  Mensch oder ein Schreiber zu FORMULIEREN hat, bleibt das richtig: ein
#  Richter, der Prosa umschreibt, ist ein Autor. Es gibt aber genau eine
#  Klasse, die keine Formulierung braucht, weil sie beweisbar kein eigener
#  Text ist: eine Passage, die wörtlich aus einem ANDEREN Artikel stammt und
#  in diesem Diff NEU hinzukam. Sie zu entfernen stellt den vorherigen Stand
#  wieder her – es wird nichts erfunden, nichts umgeschrieben, nichts
#  gekürzt, was vorher schon da war.
#
#  Deshalb heilt `heilen()` ausschließlich:
#    1. Blöcke, die der Diff HINZUGEFÜGT hat (nicht der Bestand),
#    2. von denen mindestens KOPIE_MIN_WOERTER Wörter wörtlich in einem
#       FREM DEN Artikel des Bestands stehen (beweisbar fremd),
#    3. und niemals in live geschalteten Artikeln ohne ausdrücklichen Auftrag
#       (`--auch-live`) – Publikumsänderungen sind ein Betreiber-Entscheid.
#  Alles andere bleibt Befund und geht an die Redaktion.

KOPIE_MIN_WOERTER = 25   # kürzere Blöcke: gemeinsame Wendung, keine Kopie


def _bloecke(text: str) -> list[str]:
    """Absätze eines Artikels (Leerzeilen-getrennt), in Reihenfolge."""
    return [b for b in text.split("\n\n")]


def hinzugefuegte_bloecke(alt_text: str, neu_text: str) -> list[str]:
    """Die Absätze, die NEU sind (in der Basis nicht vorhanden).

    Bewusst auf Absatzebene und über Textgleichheit, nicht über Indizes:
    eine Zeilennummer verschiebt sich, sobald irgendwo oben etwas
    hinzukommt – dann würde Bestandstext als „hinzugefügt“ gelten und die
    Heilung echten Inhalt löschen.
    """
    alt = {b.strip() for b in _bloecke(alt_text or "")}
    return [b for b in _bloecke(neu_text or "") if b.strip() and b.strip() not in alt]


def kopie_treffer(block: str, fremdtexte) -> tuple[str, int] | None:
    """(slug, wörter) wenn der Block wörtlich in einem fremden Artikel steht.

    Verglichen wird über `cu.norm` (dieselbe Normalisierung wie die Messung:
    Groß-/Kleinschreibung, Umlaute), in Fenstern von KOPIE_MIN_WOERTER
    Wörtern. `fremdtexte` ist eine Folge von (slug, body) mit `clean_body`,
    also ROH wie im Bestand – normalisiert wird hier.

    Beide Seiten MÜSSEN normalisiert werden: Am 06.11.2026 suchte diese
    Funktion „garantie kann sich lohnen“ in einem Text, der „Eine Garantie
    kann sich lohnen“ enthält. Die Folge war eine Heilung, die nie etwas
    fand und still „nichts zu tun“ meldete – die gefährlichste Form von
    grün.
    """
    woerter = cu.norm(block).split()
    if len(woerter) < KOPIE_MIN_WOERTER:
        return None
    ziel = {" ".join(woerter[i:i + KOPIE_MIN_WOERTER])
            for i in range(len(woerter) - KOPIE_MIN_WOERTER + 1)}
    bester: tuple[str, int] | None = None
    for slug, fremd in fremdtexte:
        if not fremd:
            continue
        fw = cu.norm(fremd).split()
        if len(fw) < KOPIE_MIN_WOERTER:
            continue
        fremd_set = {" ".join(fw[i:i + KOPIE_MIN_WOERTER])
                     for i in range(len(fw) - KOPIE_MIN_WOERTER + 1)}
        gemeinsame = ziel & fremd_set
        if gemeinsame and (bester is None or len(woerter) > bester[1]):
            bester = (slug, len(woerter))
    return bester


def heilbare_kopien(rel: str, basis: str, bestand: dict,
                    root: str = BLOG_DIR) -> list[dict]:
    """Die Blöcke dieses Artikels, die beweisbar fremde Kopien sind."""
    slug = _slug_aus_relpath(rel)
    alt_text = git_text_at(basis, rel, root=root) or ""
    try:
        with open(os.path.join(root, rel), encoding="utf-8") as fh:
            neu_text = fh.read()
    except OSError:
        return []
    fremd = [(i.get("slug", ""), i.get("body", ""))
             for i in bestand.values() if i.get("slug") and i.get("slug") != slug]
    treffer = []
    for block in hinzugefuegte_bloecke(alt_text, neu_text):
        fund = kopie_treffer(block, fremd)
        if fund:
            treffer.append({"slug": slug, "pfad": rel, "block": block,
                            "von": fund[0], "woerter": fund[1]})
    return treffer


def _entferne_bloecke(text: str, bloecke) -> str:
    """Die gegebenen Absätze aus dem Rohtext entfernen (exakt, in Reihenfolge)."""
    weg = {b.strip() for b in bloecke if b.strip()}
    behalten, uebersprungen = [], 0
    for block in _bloecke(text):
        if block.strip() in weg and uebersprungen < len(weg):
            uebersprungen += 1
            continue
        behalten.append(block)
    return "\n\n".join(behalten)


def heilen(basis: str, auch_live: bool = False, bestand: dict | None = None,
           schreiben: bool = True, root: str = BLOG_DIR) -> dict:
    """Entfernt beweisbar hinzugefügte Kopien – und sonst nichts.

    Rückgabe: {"geheilt": [...], "uebersprungen": [...], "offen": [...]}
      geheilt      – Datei wurde (falls `schreiben`) bereinigt
      uebersprungen – Kopie erkannt, aber live und ohne --auch-live
      offen        – Befund ohne heilbare Kopie (echte Formulierungsarbeit)
    """
    changed = changed_post_paths(basis, root=root)
    if bestand is None:
        bestand = (cu.lade_bestand() if os.path.realpath(root) == os.path.realpath(BLOG_DIR)
                   else _lade_bestand_aus_root(root))
    ergebnis = {"geheilt": [], "uebersprungen": [], "offen": []}
    heilbare_slugs: set[str] = set()   # einmal rechnen, nicht dreimal
    for rel in changed:
        slug = _slug_aus_relpath(rel)
        live = bool(next((i.get("live") for i in bestand.values()
                          if i.get("slug") == slug), False))
        kopien = heilbare_kopien(rel, basis, bestand, root=root)
        if kopien:
            heilbare_slugs.add(slug)
        if kopien and live and not auch_live:
            ergebnis["uebersprungen"].append(
                {"slug": slug, "bloecke": len(kopien),
                 "grund": "live geschaltet – nur mit --auch-live"})
            continue
        if not kopien:
            continue
        pfad = os.path.join(root, rel)
        with open(pfad, encoding="utf-8") as fh:
            text = fh.read()
        if schreiben:
            with open(pfad, "w", encoding="utf-8") as fh:
                fh.write(_entferne_bloecke(text, [k["block"] for k in kopien]))
        ergebnis["geheilt"].append(
            {"slug": slug, "bloecke": len(kopien), "live": live,
             "von": sorted({k["von"] for k in kopien})})
    # Was der Befund zusätzlich meldet, ist Redaktionsarbeit – nie heilbar.
    for eintrag in befunde(changed, basis, bestand=bestand, root=root):
        if eintrag.get("geaendert") not in heilbare_slugs:
            ergebnis["offen"].append(eintrag)
    return ergebnis


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

    # ------------------------------------------------------------------
    # 8) SELBSTHEILUNG (06.11.2026, Auftrag „automatische Selbstheilung“):
    #    Sie darf NUR beweisbare Kopien entfernen – und das nachweisbar.
    # ------------------------------------------------------------------
    lang = ("Bei einer einseitigen Preisaenderung koennen Verbraucher "
            "grundsaetzlich ohne Frist zum Zeitpunkt der Aenderung kuendigen, "
            "der Vertrag endet am Vortag der Aenderung und die Abschlaege "
            "werden ab diesem Zeitpunkt neu berechnet.")
    fremd = [("2026-10-07-dsl", cu.clean_body(lang))]
    # (a) Eine wörtlich übernommene Passage gilt als Kopie …
    if kopie_treffer(lang, fremd) is None:
        fehler.append("Heilung: eine wörtlich kopierte Passage gilt nicht "
                      "als Kopie – die Selbstheilung würde #1027 nicht "
                      "erkennen")
    # (b) … eigener Text, kurze Wendungen und Bestandstext NICHT.
    if kopie_treffer(eigen, fremd) is not None:
        fehler.append("Heilung: eigener Text gilt als Kopie – die Heilung "
                      "würde echten Inhalt löschen (Freibrief)")
    if kopie_treffer("Die Bundesnetzagentur hat im Oktober Zahlen "
                     "veröffentlicht.", fremd) is not None:
        fehler.append("Heilung: eine kurze gemeinsame Wendung gilt als "
                      "Kopie – löschbar wäre jeder Halbsatz")
    # (c) Nur HINZUGEFÜGTES ist heilbar: unveränderter Text nie.
    if hinzugefuegte_bloecke(lang, lang):
        fehler.append("Heilung: unveränderter Bestandstext gilt als "
                      "hinzugefügt – die Heilung würde Bestand löschen")
    if len(hinzugefuegte_bloecke(eigen, eigen + "\n\n" + lang)) != 1:
        fehler.append("Heilung: der hinzugefügte Block wird nicht erkannt")
    # (d) Entfernen trifft genau den Block und lässt alles andere stehen.
    rest = _entferne_bloecke(eigen + "\n\n" + lang, [lang])
    if lang in rest or eigen not in rest:
        fehler.append("Heilung: _entferne_bloecke trifft nicht genau den "
                      "kopierten Block")
    # (e) FAIL-CLOSED: Ohne lesbare Basis heilt NICHTS (sonst würde der
    #     gesamte Artikel als „hinzugefügt“ gelten und gelöscht).
    if hinzugefuegte_bloecke("", lang) != [lang]:
        fehler.append("Heilung: ohne Basis ist nicht alles hinzugefügt – "
                      "die Annahme des Fail-CLOSED-Pfads stimmt nicht")
    # (f) Die Schwelle für „Kopie“ ist importiert/abgeleitet, keine zweite
    #     Zahl: Sie muss über der Phrasenlänge der Messung liegen.
    if KOPIE_MIN_WOERTER <= PHRASE_LEN:
        fehler.append("Heilung: KOPIE_MIN_WOERTER liegt nicht über der "
                      "Phrasenlänge – dann wäre eine geteilte Wendung schon "
                      "eine „Kopie“")

    if fehler:
        print("🛑 BESTANDS-EINZIGARTIGKEITS-DIFF-TOR – SELFTEST FEHLGESCHLAGEN "
              "(Exit 2):")
        for f in fehler:
            print(f"   - {f}")
        return 2
    print("✅ BESTANDS-EINZIGARTIGKEITS-DIFF-TOR-SELFTEST bestanden: Erzeugung, "
          "Verstärkung, Altlast-Versicherung, leerer Bestand (fail-closed), "
          "Selbstheilung nur beweisbarer Kopien, "
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
    parser.add_argument("--heilen", action="store_true",
                        help="beweisbar HINZUGEFÜGTE Kopien entfernen (nie Prosa)")
    parser.add_argument("--auch-live", action="store_true",
                        help="mit --heilen auch live geschaltete Artikel (Auftrag nötig)")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.basis:
        parser.error("--basis fehlt (oder --selftest verwenden)")
    if args.auch_live and not args.heilen:
        parser.error("--auch-live wirkt nur mit --heilen")

    if args.heilen:
        try:
            ergebnis = heilen(args.basis, auch_live=args.auch_live, root=args.root)
        except GateFehler as exc:
            print(f"🛑 BESTANDS-EINZIGARTIGKEITS-DIFF-TOR – WERKZEUGFEHLER: {exc}")
            return 2
        for e in ergebnis["geheilt"]:
            herkunft = ", ".join(e["von"]) if e["von"] else "fremder Artikel"
            print(f"🧹 GEHEILT: {e['slug']} – {e['bloecke']} hinzugefügte "
                  f"Kopie(n) aus {herkunft} entfernt"
                  f"{' (LIVE-Artikel, ausdrücklicher Auftrag)' if e['live'] else ''}")
        for e in ergebnis["uebersprungen"]:
            print(f"⏸️ ÜBERSPRUNGEN: {e['slug']} – {e['grund']} "
                  f"({e['bloecke']} Kopie(n) bleiben stehen)")
        for e in ergebnis["offen"]:
            print(_block(e))
        if ergebnis["offen"]:
            print("   Diese Befunde sind Formulierungsarbeit und werden NICHT "
                  "automatisch umgeschrieben (ein Richter, der Prosa "
                  "umschreibt, ist ein Autor).")
            return 1
        if ergebnis["geheilt"] or ergebnis["uebersprungen"]:
            return 0
        print(f"✅ Diff-Tor: nichts zu heilen gegen {args.basis[:12]}.")
        return 0

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
