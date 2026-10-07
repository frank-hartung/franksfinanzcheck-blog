#!/usr/bin/env python3
# ============================================================
#  H1-WACHE – „Genau eine H1 pro Seite“ (Dauerheilung #623)
#
#  ANLASS (07.10.2026, Meldung #623): Das wöchentliche
#  Barrierefreiheits-Audit meldete auf /presse/ und /studien/
#  je **zwei** H1. Ursache: Beide Markdown-Dokumente trugen im
#  FLIESSTEXT eine eigene `# …`-Überschrift, obwohl jedes Layout
#  die Seiten-H1 bereits aus dem Titel setzt. Der Leser sah
#  deshalb zwei Hauptüberschriften; Screenreader, Inhalts-
#  verzeichnis und KI-Antworten verloren die Gliederung
#  (WCAG 1.3.1 „Info und Beziehungen“, 2.4.6 „Überschriften“).
#
#  Der eigentliche Befund war jedoch größer als die Meldung:
#  Das Audit prüfte nur eine STICHPROBE von 20 Seiten – die
#  dritte Doppel-H1 (/studien/fixkosten-index-2026-q4/) stand
#  im selben Build und blieb unsichtbar. Ein Audit, das 20 von
#  107 Seiten sieht, ist kein Audit, sondern ein Würfel.
#
#  REGELN
#    S1 QUELLE   Kein Markdown-Dokument unter content/ oder
#                archetypes/ trägt im Fließtext eine `# …`-
#                Überschrift. Die H1 gehört dem Layout. Wer eine
#                eigene Schirmzeile braucht, setzt sie als
#                `heading:` ins Frontmatter.
#                Frontmatter, Code-Zäune (``` / ~~~) und
#                eingerückter Code werden übersprungen.
#    S2 LAYOUT   Der Artikel-Baustein (layouts/_partials/
#                artikel_einzeln.html) rendert GENAU EINE H1 und
#                ehrt `.Params.heading`. Beide Einzel-Templates
#                (_default/single.html und single.html) binden
#                genau diesen Baustein ein – eine zweite Kopie
#                des Bausteins wäre wieder ein Zweig, der ins
#                Leere läuft (s. u.). Die Abschnitts-Liste
#                (_default/list.html) ehrt `heading:` ebenfalls.
#    S3 BUILD    Jede gebaute Seite trägt GENAU EINE nicht-leere
#                H1. Ausnahmen sind dokumentiert und begründet
#                (Verifikationsdateien, reine Redirects).
#
#  WARUM S2 SO SCHARF IST (Beweis vom 07.10.2026):
#  Bis zur Dauerheilung lag der Artikel-Baustein ZWEIMAL im Repo
#  (layouts/_default/single.html und layouts/single.html), mit
#  dem Vermerk „layouts/single.html gewinnt die Template-
#  Auflösung“. Ein Baustein-Marker im gebauten HTML bewies das
#  Gegenteil: /presse/ und /ueber/ trugen `data-tpl=
#  "DEFAULTSINGLE"`. Die Kopie in layouts/single.html war der
#  tote Zweig – jede künftige Heilung dort wäre versandet.
#  Jetzt gibt es genau EINEN Baustein, und S2 hält das fest.
#
#  Die Wache heilt NICHT selbst: Eine H1 zu löschen heißt, einen
#  redaktionellen Satz zu vernichten. Sie meldet Datei, Zeile,
#  Text und den konkreten Handgriff (`heading:` + Zeile raus).
#
#  Aufruf:
#    python3 scripts/h1_wache.py --source-only   # nur Quellbaum
#    python3 scripts/h1_wache.py --public public # + Build
#    python3 scripts/h1_wache.py --selftest      # Sabotageproben + echte Quelle
#    python3 scripts/h1_wache.py --json          # maschinenlesbar
#
#  Exit: 0 = grün · 1 = Befund.
#  Verdrahtet: deploy.yml (Quelle vor dem Build, Build danach) ·
#  npm run h1:check · Vertrag C30 (scripts/governance_contract.py).
# ============================================================

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(os.environ.get("GITHUB_WORKSPACE") or Path(__file__).resolve().parents[1])
CONTENT_DIR = ROOT / "content"
ARCHETYPEN_DIR = ROOT / "archetypes"
LAYOUTS_DIR = ROOT / "layouts"
ARTIKEL_BAUSTEIN = LAYOUTS_DIR / "_partials" / "artikel_einzeln.html"
SINGLE_DEFAULT = LAYOUTS_DIR / "_default" / "single.html"
SINGLE_WURZEL = LAYOUTS_DIR / "single.html"
LISTE_DEFAULT = LAYOUTS_DIR / "_default" / "list.html"

# S1 – eine `# `-Überschrift am Zeilenanfang. `#hashtag` (ohne
# Leerzeichen) ist keine Überschrift, `###### x` schon (dann aber
# keine H1 – geprüft wird nur die Ebene 1).
H1_ZEILE = re.compile(r"^# (?!#)(?P<text>\S.*?)[ \t]*$", re.M)
CODE_ZAUN = re.compile(r"^\s{0,3}(```|~~~)")
FRONTMATTER_TRENNER = re.compile(r"^---[ \t]*$")

# S3 – Seiten, die im Build KEINEN Seiteninhalt tragen. Jede
# Ausnahme braucht einen Grund; eine Ausnahme ohne Grund ist eine
# Lücke mit Etikett.
AUSNAHMEN_H1: tuple[tuple[str, str], ...] = (
    # Verifikationsdateien: Google und Pinterest verlangen den
    # exakten Inhalt – dort darf kein Layout hinein.
    (r"(^|/)google[^/]*\.html$", "Verifikationsdatei (Google verlangt exakten Inhalt)"),
    (r"(^|/)pinterest-[a-z0-9]+\.html$", "Verifikationsdatei (Pinterest verlangt exakten Inhalt)"),
    # Blätter-Redirects: /page/N/ leitet sofort weiter.
    (r"(^|/)page/[0-9]+/", "Blätter-Redirect ohne Seiteninhalt"),
    # Client-Redirect der Pinterest-Autorisierung (Zwilling von
    # /pinterest-oauth.html – diese Datei selbst WIRD geprüft).
    (r"^pinterest-oauth/index\.html$", "Client-Redirect ohne Seiteninhalt"),
)

# Für das VOLLAUDIT (scripts/a11y_audit.py) gilt zusätzlich:
# Diese Seiten sind reine Weiterleitungen ohne Seitennavigation –
# sie tragen zwar eine H1, aber bewusst keinen Skip-Link. Die
# H1-Wache prüft sie (eine H1 ist eine H1), das Komplett-Audit
# nicht (ein Skip-Link wäre dort sinnlos).
AUSNAHMEN_SEITE: tuple[tuple[str, str], ...] = AUSNAHMEN_H1 + (
    (r"^go/", "Affiliate-Redirect (noindex, keine Seitennavigation)"),
    (r"^pinterest-oauth\.html$", "Client-Redirect (Pinterest-Autorisierung)"),
)

H1_TAG = re.compile(r"<h1(?=[\s>])(.*?)</h1>", re.S | re.I)
LEER = re.compile(r"<[^>]+>|\s|&[a-z]+;", re.I)


def _lesen(pfad: Path) -> str:
    try:
        return pfad.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def ausnahme_grund(rel: str, ausnahmen=AUSNAHMEN_H1) -> str:
    """Begründung, warum eine gebaute Seite nicht geprüft wird – sonst ''."""
    relativer_pfad = str(rel).replace(os.sep, "/")
    for muster, grund in ausnahmen:
        if re.search(muster, relativer_pfad):
            return grund
    return ""


# ------------------------------------------------------------ S1: Quelle

def markdown_ohne_huelle(text: str) -> list[tuple[int, str]]:
    """Liefert (Zeilennummer, Text) aller Fließtext-H1 – ohne Frontmatter
    und ohne Code-Zäune. Zeilennummern beziehen sich auf die Originaldatei."""
    zeilen = text.splitlines()
    start = 0
    if zeilen and FRONTMATTER_TRENNER.match(zeilen[0]):
        for i in range(1, len(zeilen)):
            if FRONTMATTER_TRENNER.match(zeilen[i]) or zeilen[i].strip() in ("...",):
                start = i + 1
                break
    funde: list[tuple[int, str]] = []
    im_code = False
    zaun = ""
    for nr in range(start, len(zeilen)):
        zeile = zeilen[nr]
        treffer = CODE_ZAUN.match(zeile)
        if treffer:
            if not im_code:
                im_code, zaun = True, treffer.group(1)
            elif zeile.strip().startswith(zaun):
                im_code, zaun = False, ""
            continue
        if im_code:
            continue
        m = H1_ZEILE.match(zeile)
        if m:
            funde.append((nr + 1, m.group("text")))
    return funde


def s1_quelle(wurzel: Path = ROOT) -> list[str]:
    funde: list[str] = []
    quellen = [wurzel / "content", wurzel / "archetypes"]
    for ordner in quellen:
        if not ordner.is_dir():
            funde.append(f"S1: {ordner.relative_to(wurzel) if ordner.is_relative_to(wurzel) else ordner} fehlt – "
                         "ohne Quellbaum ist die H1-Regel nicht prüfbar (fail-closed).")
            continue
        for pfad in sorted(ordner.rglob("*.md")):
            rel = str(pfad.relative_to(wurzel))
            for nr, text in markdown_ohne_huelle(_lesen(pfad)):
                funde.append(
                    f"S1: {rel}:{nr} trägt eine H1 im Fließtext: „{text[:80]}“. "
                    "Die H1 gehört dem Layout – Schirmzeile als `heading:` ins "
                    "Frontmatter, `# …`-Zeile entfernen (sonst zwei H1 pro Seite)."
                )
    return funde


# ------------------------------------------------------------ S2: Layout

def s2_layout(wurzel: Path = ROOT) -> list[str]:
    funde: list[str] = []
    baustein = _lesen(wurzel / "layouts" / "_partials" / "artikel_einzeln.html")
    single_default = _lesen(wurzel / "layouts" / "_default" / "single.html")
    single_wurzel = _lesen(wurzel / "layouts" / "single.html")
    liste = _lesen(wurzel / "layouts" / "_default" / "list.html")

    if not baustein:
        funde.append("S2: layouts/_partials/artikel_einzeln.html fehlt oder ist leer – "
                     "ohne den gemeinsamen Baustein gibt es wieder zwei Einzel-Templates, "
                     "von denen eines ins Leere läuft (Befund vom 07.10.2026, #623).")
    else:
        h1 = re.findall(r"<h1(?=[\s>])", baustein)
        if len(h1) != 1:
            funde.append(f"S2: layouts/_partials/artikel_einzeln.html rendert {len(h1)} H1 "
                         "(erwartet: genau 1) – jeder weitere Zweig erzeugt Doppel-H1.")
        if ".Params.heading" not in baustein:
            funde.append("S2: layouts/_partials/artikel_einzeln.html ehrt `.Params.heading` nicht – "
                         "eine eigene Schirmzeile ließe sich nur über eine `# …`-Zeile im "
                         "Fließtext setzen, also über genau die zweite H1, die #623 auslöste.")

    for name, text in (("_default/single.html", single_default), ("single.html", single_wurzel)):
        if not text.strip():
            funde.append(f"S2: layouts/{name} ist leer – die Einzelansicht würde nicht rendern.")
            continue
        if 'partial "artikel_einzeln.html"' not in text:
            funde.append(f"S2: layouts/{name} bindet den gemeinsamen Baustein "
                         "`artikel_einzeln.html` nicht ein – eine zweite Kopie des Artikels "
                         "wäre wieder ein toter Zweig (Befund vom 07.10.2026, #623).")
        if re.search(r"<h1(?=[\s>])", text):
            funde.append(f"S2: layouts/{name} rendert selbst eine H1 – die H1 gehört in den "
                         "Baustein, sonst zählt die Seite zwei.")

    if not liste.strip():
        funde.append("S2: layouts/_default/list.html ist leer – Abschnittsseiten würden nicht rendern.")
    elif ".Params.heading" not in liste:
        funde.append("S2: layouts/_default/list.html ehrt `.Params.heading` nicht – "
                     "Abschnittsseiten bräuchten für eine eigene Schirmzeile wieder eine "
                     "`# …`-Zeile im Fließtext (zweite H1, #623).")
    return funde


# ------------------------------------------------------------ S3: Build

def h1_der_seite(html: str) -> list[str]:
    """Sichtbare H1-Texte einer gebauten Seite (Tags entfernt)."""
    texte = []
    for treffer in H1_TAG.finditer(html):
        roh = html[treffer.start():treffer.end()]
        innen = re.sub(r"^<h1[^>]*>", "", roh, flags=re.I | re.S)
        innen = re.sub(r"</h1>$", "", innen, flags=re.I)
        text = LEER.sub("", innen)
        texte.append(text)
    return texte


def s3_build(public: Path, ausnahmen=AUSNAHMEN_H1) -> list[str]:
    funde: list[str] = []
    if not public.is_dir():
        return [f"S3: {public} fehlt – ohne Build ist die gebaute Wahrheit nicht prüfbar (fail-closed)."]
    geprueft = 0
    for pfad in sorted(public.rglob("*.html")):
        rel = str(pfad.relative_to(public)).replace(os.sep, "/")
        if ausnahme_grund(rel, ausnahmen):
            continue
        geprueft += 1
        texte = h1_der_seite(_lesen(pfad))
        if len(texte) != 1:
            fund = (f"S3: {rel} trägt {len(texte)} H1 (erwartet: 1)"
                    + (f": {texte[:3]}" if texte else " – gar keine"))
            funde.append(fund + ". Zwei H1 zerstören die Gliederung für Screenreader, "
                         "Inhaltsverzeichnis und KI-Antworten.")
            continue
        if not texte[0]:
            funde.append(f"S3: {rel} trägt eine leere H1 – eine Überschrift ohne Text ist keine.")
    if geprueft == 0:
        funde.append("S3: keine prüfbare Seite im Build gefunden – ein Build ohne Seiten ist ein Befund.")
    return funde


# ------------------------------------------------------------ Sabotageproben

def selftest(wurzel: Path = ROOT) -> list[str]:
    """Sabotageproben gegen S1–S3. Kein Dateizugriff außerhalb von temporären Ordnern."""
    fehler: list[str] = []

    def check(name: str, bedingung: bool) -> None:
        print(("  ✓ " if bedingung else "  ✗ ") + name)
        if not bedingung:
            fehler.append(name)

    # S1 – Erkennung
    check("S1: Fließtext-H1 wird erkannt",
          len(markdown_ohne_huelle("---\ntitle: \"x\"\n---\n\n# Schirmzeile\n\nText\n")) == 1)
    check("S1: H2 ist keine H1",
          markdown_ohne_huelle("## Zwischenzeile\n") == [])
    check("S1: `#hashtag` ist keine Überschrift",
          markdown_ohne_huelle("#ohneLeerzeichen\n") == [])
    check("S1: Code-Zaun schützt die Raute",
          markdown_ohne_huelle("```\n# Beispiel\n```\n") == [])
    check("S1: Frontmatter-Kommentar zählt nicht",
          markdown_ohne_huelle("---\ntitle: \"x\"\n# Kommentar im Frontmatter\n---\n\n## Echt\n") == [])
    check("S1: Zeilennummer stimmt",
          markdown_ohne_huelle("---\ntitle: \"x\"\n---\n\n## A\n\n# H1\n")[0][0] == 7)

    # S1 – Ausnahmen greifen nicht zu weit
    check("S1: mehrere H1 werden gemeldet",
          len(markdown_ohne_huelle("# eins\n\n# zwei\n")) == 2)

    # S2 – Layoutvertrag (gegen den echten Baum)
    check("S2: Layoutvertrag des echten Baums ist grün", s2_layout(wurzel) == [])

    # S3 – Build gegen einen künstlichen Baum
    with tempfile.TemporaryDirectory() as tmp:
        pub = Path(tmp) / "public"
        (pub / "presse").mkdir(parents=True)
        (pub / "presse" / "index.html").write_text(
            "<html lang=de><title>t</title><h1>Eins</h1><h1>Zwei</h1></html>", encoding="utf-8")
        (pub / "index.html").write_text("<html lang=de><h1>Startseite</h1></html>", encoding="utf-8")
        (pub / "leer").mkdir()
        (pub / "leer" / "index.html").write_text("<html lang=de><h1> </h1></html>", encoding="utf-8")
        funde = s3_build(pub)
        check("S3: Doppel-H1 wird erkannt", any("presse/index.html" in f and "2 H1" in f for f in funde))
        check("S3: H1-Texte werden genannt", any("Zwei" in f for f in funde))
        check("S3: leere H1 wird erkannt", any("leer/index.html" in f for f in funde))
        check("S3: saubere Seite bleibt still", not any("index.html trägt 1 H1" in f for f in funde))

        # Ausnahmen: begründet und nicht zu weit
        (pub / "page" / "2").mkdir(parents=True)
        (pub / "page" / "2" / "index.html").write_text("<html>redirect</html>", encoding="utf-8")
        (pub / "google123.html").write_text("google-site-verification: x", encoding="utf-8")
        funde2 = s3_build(pub)
        check("S3: Blätter-Redirect ist begründet ausgenommen",
              not any("page/2/index.html" in f for f in funde2))
        check("S3: Verifikationsdatei ist begründet ausgenommen",
              not any("google123.html" in f for f in funde2))

        # Sabotage: ohne die Ausnahme muss der Redirect auffallen
        check("S3: Ausnahme ohne Grund wäre eine Lücke – Redirect fiele auf",
              any("page/2/index.html" in f for f in s3_build(pub, ausnahmen=())))

    check("S3: fehlendes Build-Verzeichnis ist fail-closed",
          s3_build(Path("/tmp/gibt-es-nicht-h1-wache")) != [])

    # Echte Quelle: die Wache misst denselben Baum, den sie bewacht.
    echt = s1_quelle(wurzel)
    check("S1: echte Quelle (content/ + archetypes/) ist grün", echt == [])
    if echt:
        fehler.append("S1: echte Quelle nicht grün")
    return fehler


# ------------------------------------------------------------ Hauptprogramm

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="H1-Wache: genau eine H1 pro Seite (Quelle + Build).")
    parser.add_argument("--source-only", action="store_true",
                        help="nur S1 (Quelle) und S2 (Layout) – kein Build nötig")
    parser.add_argument("--public", type=Path, default=None,
                        help="zusätzlich S3 gegen das Hugo-Ausgabeverzeichnis")
    parser.add_argument("--selftest", action="store_true",
                        help="Sabotageproben + Prüfung der echten Quelle")
    parser.add_argument("--json", action="store_true", help="Befunde als JSON")
    args = parser.parse_args(argv)

    if not any((args.source_only, args.public, args.selftest)):
        args.source_only = True
        if (ROOT / "public").is_dir():
            args.public = ROOT / "public"

    funde: list[str] = []
    if args.selftest:
        funde.extend("SELFTEST: " + f for f in selftest(ROOT))
    if args.source_only or args.public or not args.selftest:
        funde.extend(s1_quelle(ROOT))
        funde.extend(s2_layout(ROOT))
    if args.public:
        funde.extend(s3_build(args.public))

    if args.json:
        print(json.dumps({"ok": not funde, "funde": funde}, ensure_ascii=False, indent=2))
    elif funde:
        print("🛑 H1-WACHE: Befunde")
        for fund in funde:
            print("  - " + fund)
    else:
        umfang = []
        if args.selftest:
            umfang.append("Sabotageproben")
        if args.source_only or not args.selftest:
            umfang.append("Quelle")
        if args.public:
            umfang.append("Build")
        print(f"✅ H1-WACHE bestanden ({' + '.join(umfang)}): jede Seite trägt genau eine H1.")
    return 1 if funde else 0


if __name__ == "__main__":
    sys.exit(main())
