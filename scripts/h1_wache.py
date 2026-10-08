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
#                archetypes/ trägt im Fließtext eine H1. Die H1 gehört dem
#                Layout. Wer eine eigene Schirmzeile braucht, setzt sie als
#                `heading:` ins Frontmatter.
#                Geprüft wird die ECHTE Markdown-Wahrheit – also alles, was
#                Goldmark als <h1> rendert:
#                  · ATX mit bis zu DREI führenden Leerzeichen (`   # …`);
#                    vier Leerzeichen sind eingerückter Code und bleiben
#                    Code.
#                  · Setext (`Titel` in der Zeile darüber, `=====` darunter).
#                    Eine reine `#`-Suche sieht sie nie – Goldmark rendert
#                    sie trotzdem.
#                  · rohes `<h1 …>` (hugo.toml setzt `unsafe = true`; das
#                    Markup geht unverändert in den Build).
#                Frontmatter, Code-Zäune (``` / ~~~), eingerückter Code und
#                Inline-Code-Spans bleiben unberührt – dort ist `#` bzw.
#                `<h1>` Text, kein Markup.
#    S2 LAYOUT   Der Artikel-Baustein (layouts/_partials/artikel_einzeln.html)
#                rendert GENAU EINE H1 und ehrt `.Params.heading`. Beide
#                Einzel-Templates (_default/single.html und single.html)
#                binden genau diesen Baustein ein – eine zweite Kopie
#                des Bausteins wäre wieder ein Zweig, der ins Leere läuft
#                (s. u.). Die Abschnitts-Liste (_default/list.html) ehrt
#                `heading:` ebenfalls und trägt die H1 der Startseiten-
#                Blätterseiten (/page/2/ …). Die Abschnitts-Einzelansichten
#                mit eigener Vorlage (pillar/, werkzeuge/) folgen derselben
#                Parität: auch sie ehren `heading:`.
#                Jede Layout-Datei, die ein <h1> rendern DARF, steht im
#                Inventar H1_QUELLEN (Anzahl + Grund) und in der
#                Seitenarten-Tabelle SEITENARTEN. Fail-closed: Eine neue
#                H1-Quelle ohne Eintrag ist ein Befund – so kann keine
#                zweite H1 unbemerkt entstehen. Die beiden Tabellen müssen
#                zusammenpassen: jede Seitenart hat eine Quelle, jede Quelle
#                eine Seitenart.
#    S3 BUILD    Jede gebaute Seite trägt GENAU EINE nicht-leere
#                H1. Ausnahmen sind dokumentiert und begründet
#                (Verifikationsdateien, reine Redirects). Blätterseiten
#                (`page/N/`) sind KEINE Ausnahme: Seit
#                `[pagination] disableAliases = true` gibt es keine
#                inhaltsleeren Blätter-Redirects mehr – was bleibt, sind
#                echte, verlinkte Seiten, und die tragen eine H1
#                (Dauerheilung Stufe 2, 08.10.2026).
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
#  Verdrahtet: deploy.yml (Quelle vor dem Build, Build danach) · e2e.yml
#  (Build-Prüfung im Pull Request) · npm run h1:check · Vertrag C30
#  (scripts/governance_contract.py).
#
#  STUFE 2 (08.10.2026, „verifizieren & nachhärten“): Die Stufe-1-Wache
#  sah drei Dinge nicht, die diese Fassung nachholt:
#    1. GOLDGRÄBER IM MARKDOWN: eingerückte ATX-H1 (`   # …`), Setext-H1
#       (`=====`) und rohes `<h1 …>` wurden nicht gefunden – der Build
#       hätte sie gerendert, die Quellprüfung blieb still.
#    2. DIE AUSNAHME, DIE EINEN BEFUND VERDECKTE: `page/N/` galt pauschal
#       als „Blätter-Redirect ohne Inhalt“. Mit `disableAliases = true`
#       existieren diese Redirects nicht mehr; die Startseiten-Blätterseiten
#       /page/2/ … trugen real GAR KEINE H1 und waren trotzdem ausgenommen.
#       Ausnahmen sind jetzt auf Routen beschränkt, die nachweislich keinen
#       Seiteninhalt tragen.
#    3. BLINDE FLECKEN IM LAYOUT: S2 kannte vier Dateien. Jetzt gilt ein
#       vollständiges, fail-closed Inventar (H1_QUELLEN + SEITENARTEN) und
#       Parität für die Einzelansichten mit eigener Vorlage.
# ============================================================

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import unicodedata
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(os.environ.get("GITHUB_WORKSPACE") or Path(__file__).resolve().parents[1])
CONTENT_DIR = ROOT / "content"
ARCHETYPEN_DIR = ROOT / "archetypes"
LAYOUTS_DIR = ROOT / "layouts"
ARTIKEL_BAUSTEIN = LAYOUTS_DIR / "_partials" / "artikel_einzeln.html"
SINGLE_DEFAULT = LAYOUTS_DIR / "_default" / "single.html"
SINGLE_WURZEL = LAYOUTS_DIR / "single.html"
LISTE_DEFAULT = LAYOUTS_DIR / "_default" / "list.html"

# S1 – eine ATX-Überschrift der Ebene 1 am Zeilenanfang. `#hashtag` (ohne
# Leerzeichen) ist keine Überschrift, `###### x` schon (dann aber keine H1 –
# geprüft wird nur die Ebene 1).
# CommonMark erlaubt bis zu DREI führende Leerzeichen: `   # Titel` ist eine
# H1, `    # Titel` (vier) ist eingerückter Code und damit Code.
H1_ZEILE = re.compile(r"^ {0,3}# (?!#)(?P<text>\S.*?)[ \t]*$")
# Setext-Überschrift der Ebene 1: Textzeile, darunter eine Zeile nur aus `=`.
# Diese Form sieht eine reine `#`-Suche nie – Goldmark rendert sie trotzdem
# als <h1>. (`---` wäre die Ebene 2, also kein H1-Fall.)
SETEXT_UNTERSTRICH = re.compile(r"^ {0,3}=+[ \t]*$")
# Roh-HTML im Markdown: `unsafe = true` (hugo.toml) reicht `<h1 …>` unverändert
# in den Build. Das ist eine H1, die keine `#`-Zeile ist.
ROH_HTML_H1 = re.compile(r"<\s*h1(?=[\s/>])", re.I)
# Inline-Code-Spans (`…`, ``…``): dort ist Markup TEXT, kein Element.
INLINE_CODE = re.compile(r"(`+)(.+?)\1")
# Blätter-ALIAS (nicht die echten Blätterseiten): entsteht nur, wenn Hugo
# wieder Redirect-Dateien baut (`disableAliases` aus). Dann ist die Ursache
# benennbar – ein Befund ohne Weg ist nur die halbe Miete.
BLATTER_ALIAS = re.compile(r"^(?:[^/]+/)?page/1/index\.html$")
CODE_ZAUN = re.compile(r"^\s{0,3}(```|~~~)")
FRONTMATTER_TRENNER = re.compile(r"^---[ \t]*$")

# S3 – Seiten, die im Build KEINEN Seiteninhalt tragen. Jede
# Ausnahme braucht einen Grund; eine Ausnahme ohne Grund ist eine
# Lücke mit Etikett.
AUSNAHMEN_H1: tuple[tuple[str, str], ...] = (
    # Verifikationsdateien liegen ausschließlich im öffentlichen Root:
    # Google und Pinterest verlangen dort den exakten Inhalt – kein Layout.
    # Root-Anker verhindern, dass künftig eine echte Inhaltsseite nur wegen
    # eines gleichnamigen Segments versehentlich aus dem Gate fällt.
    (r"^google[^/]*\.html$", "Verifikationsdatei (Google verlangt exakten Inhalt)"),
    (r"^pinterest-[a-z0-9]+\.html$", "Verifikationsdatei (Pinterest verlangt exakten Inhalt)"),
    # Client-Redirect der Pinterest-Autorisierung (Zwilling von
    # /pinterest-oauth.html – diese Datei selbst WIRD geprüft).
    (r"^pinterest-oauth/index\.html$", "Client-Redirect ohne Seiteninhalt"),
)
# HIER STAND BIS 08.10.2026 EINE PAUSCHALE `page/N/`-AUSNAHME.
# Sie lautete „Blätter-Redirect ohne Seiteninhalt“ und war damit schlicht
# falsch: Seit `[pagination] disableAliases = true` (hugo.toml, 29.09.2026)
# erzeugt Hugo KEINE inhaltsleeren Blätter-Aliase mehr. Was unter
# `/page/2/`, `/posts/page/3/` … liegt, sind echte, verlinkte Seiten – und
# genau sie trugen die eine H1 nicht, die sie brauchen (Startseiten-Blätter
# ohne jede Überschrift). Eine Ausnahme, die den Befund deckt, ist keine
# Ausnahme, sondern ein Versteck. Blätterseiten werden deshalb wieder
# geprüft; die Config selbst bewacht `scripts/index_hygiene_gate.py` (H2).

# Für das VOLLAUDIT (scripts/a11y_audit.py) gilt zusätzlich:
# Diese exakt bekannten Routen sind reine Weiterleitungen ohne
# Seitennavigation – sie tragen zwar eine H1, aber bewusst keinen Skip-Link.
# Die H1-Wache prüft sie (eine H1 ist eine H1), das Komplett-Audit nicht
# (ein Skip-Link wäre dort sinnlos). Auch hier sind die Muster absichtlich
# routenscharf statt pauschal für ganze Pfadpräfixe.
AUSNAHMEN_SEITE: tuple[tuple[str, str], ...] = AUSNAHMEN_H1 + (
    (r"^go/[^/]+/index\.html$", "Affiliate-Redirect (noindex, keine Seitennavigation)"),
    (r"^pinterest-oauth\.html$", "Client-Redirect (Pinterest-Autorisierung)"),
)


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

def _fliesszeilen(text: str) -> list[tuple[int, str]]:
    """(Zeilennummer, Zeile) des Fließtexts – ohne Frontmatter, ohne
    Code-Zäune und ohne eingerückten Code (vier Leerzeichen/Tab). Genau die
    Zeilen, in denen Markdown Markup ist und Text Text bleibt."""
    zeilen = text.splitlines()
    start = 0
    if zeilen and FRONTMATTER_TRENNER.match(zeilen[0]):
        for i in range(1, len(zeilen)):
            if FRONTMATTER_TRENNER.match(zeilen[i]) or zeilen[i].strip() in ("...",):
                start = i + 1
                break
    raus: list[tuple[int, str]] = []
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
        if zeile.startswith("    ") or zeile.startswith("\t"):
            continue  # eingerückter Code: vier Leerzeichen = Code, kein Markup
        raus.append((nr + 1, zeile))
    return raus


def markdown_ohne_huelle(text: str) -> list[tuple[int, str]]:
    """(Zeilennummer, Text) jeder Fließtext-H1 in Markdown-Form: ATX (`# …`,
    auch mit bis zu drei führenden Leerzeichen) und Setext (`Titel` +
    `=====`). Frontmatter, Code-Zäune und eingerückter Code bleiben
    unberührt. Bei Setext nennt die Zeilennummer die TEXTZEILE (dort steht
    der redaktionelle Satz) – nicht den Unterstrich."""
    zeilen = _fliesszeilen(text)
    funde: list[tuple[int, str]] = []
    for index, (nr, roh) in enumerate(zeilen):
        m = H1_ZEILE.match(roh)
        if m:
            funde.append((nr, m.group("text")))
            continue
        if SETEXT_UNTERSTRICH.match(roh) and index > 0:
            vor_nr, vorher = zeilen[index - 1]
            text_davor = vorher.strip()
            if text_davor and not H1_ZEILE.match(vorher) and not SETEXT_UNTERSTRICH.match(vorher):
                funde.append((vor_nr, text_davor))
    return funde


def markdown_roh_html_h1(text: str) -> list[tuple[int, str]]:
    """(Zeilennummer, Fundstelle) jedes rohen `<h1 …>` im Fließtext.
    Inline-Code (`` `<h1>` ``) ist Text und wird nicht gemeldet; Frontmatter,
    Code-Zäune und eingerückter Code ebenfalls nicht. Verankert am Tag –
    `<h1>` in einem Code-Beispiel bleibt Code, `<h1>` im Text ist Markup."""
    funde: list[tuple[int, str]] = []
    for nr, zeile in _fliesszeilen(text):
        if ROH_HTML_H1.search(INLINE_CODE.sub("", zeile)):
            funde.append((nr, zeile.strip()[:120]))
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
            for nr, fund in markdown_roh_html_h1(_lesen(pfad)):
                funde.append(
                    f"S1: {rel}:{nr} rendert rohes `<h1 …>`: „{fund[:80]}“. "
                    "`unsafe = true` in hugo.toml reicht das Markup unverändert "
                    "in die Seite – zusammen mit der Layout-H1 sind das zwei. "
                    "Schirmzeile als `heading:` ins Frontmatter, Tag entfernen."
                )
    return funde


# ------------------------------------------------------------ S2: Layout

# ------------------------------------------------------------ S2: Layout

# Jede Layout-Datei, die ein <h1> rendern DARF – mit der Zahl der Vorkommen
# und dem Grund. Fail-closed: Eine Datei mit <h1>, die hier fehlt, ist ein
# Befund (niemand hat entschieden, dass diese Seite eine H1 braucht bzw. dass
# es genau eine bleibt); eine Zahl, die nicht mehr stimmt, ebenso.
H1_TAG = re.compile(r"<h1(?=[\s/>])", re.I)

H1_QUELLEN: tuple[tuple[str, int, str], ...] = (
    ("layouts/404.html", 1, "404-Seite: eigener Inhalt, keine Einzelansicht greift"),
    ("layouts/_default/list.html", 3,
     "drei sich ausschließende Zweige: Ratgeber-Liste (auch /posts/page/N/), "
     "Abschnitts-/Begriffsliste, Startseiten-Blätterkopf (/page/N/ ab Seite 2)"),
    ("layouts/_partials/artikel_einzeln.html", 1, "die eine H1 der Einzelansicht (Beitrag/Seite)"),
    ("layouts/_partials/home_info.html", 1, "saisonaler Hero der Startseite (data/saisons.yaml), nur Seite 1"),
    ("layouts/pillar/list.html", 1, "Hero der Ratgeber-Übersicht /pillar/"),
    ("layouts/pillar/single.html", 1, "Themenwelt-Einzelansicht (eigene Vorlage, Parität zum Baustein)"),
    ("layouts/taxonomy.html", 1, "Überschrift der Taxonomie-Übersicht"),
    ("layouts/werkzeuge/list.html", 1, "Kopf der Werkzeug-Übersicht /werkzeuge/"),
    ("layouts/werkzeuge/single.html", 1, "Werkzeug-Einzelansicht (eigene Vorlage, Parität zum Baustein)"),
)

# Welche Seitenart hat welche H1-Quelle? Zwei Sichten auf dieselbe Wahrheit:
# die Seitenart-Tabelle sagt „keine Seite ohne H1-Quelle“, das Inventar sagt
# „keine H1-Quelle ohne Seite“. Beide müssen zusammenpassen – sonst entsteht
# genau der tote Zweig, den #623 teuer machte.
SEITENARTEN: tuple[tuple[str, str, str], ...] = (
    ("startseite-seite-1", "layouts/_partials/home_info.html", "saisonaler Hero (nur Seite 1)"),
    ("startseite-blaetter", "layouts/_default/list.html", "Blätterkopf ab Seite 2 (/page/N/)"),
    ("ratgeber-liste", "layouts/_default/list.html", "/posts/ und /posts/page/N/"),
    ("abschnitt-und-begriff", "layouts/_default/list.html", "Abschnitts- und Begriffsseiten"),
    ("taxonomie", "layouts/taxonomy.html", "Taxonomie-Übersicht"),
    ("einzelansicht", "layouts/_partials/artikel_einzeln.html", "Beitrag/Seite über beide Single-Wrapper"),
    ("themenwelt", "layouts/pillar/single.html", "Themenwelt-Einzelansicht"),
    ("werkzeug", "layouts/werkzeuge/single.html", "Werkzeug-Einzelansicht"),
    ("ratgeber-uebersicht", "layouts/pillar/list.html", "/pillar/"),
    ("werkzeug-uebersicht", "layouts/werkzeuge/list.html", "/werkzeuge/"),
    ("nicht-gefunden", "layouts/404.html", "/404.html"),
)

# Einzelansichten mit eigener Vorlage rendern ihre H1 selbst – sie müssen
# dieselbe Mechanik tragen wie der gemeinsame Baustein. Sonst wäre die
# dokumentierte Heilung („Schirmzeile als `heading:` ins Frontmatter“) auf
# genau diesen Seiten falsch, und die nächste redaktionelle Schirmzeile
# landete wieder als zweite H1 im Fließtext.
PARITAET_TEMPLATES: tuple[str, ...] = ("layouts/pillar/single.html",
                                       "layouts/werkzeuge/single.html")

# Marker, an dem der Startseiten-Blätterkopf hängt (Layout und Wache teilen
# ihn). Der Marker ist kein Schmuck: Ohne ihn wüsste die Wache nicht, dass
# die Startseite zwei sich ausschließende H1-Quellen hat – und genau das
# fehlt der Seite /page/2/ bis zum 08.10.2026 komplett.
H1_BLAETTERKOPF_MARKER = "H1-BLÄTTERKOPF"


def _inventar_funde(wurzel: Path) -> list[str]:
    """Fail-closed-Inventar: Jede H1-Quelle im Layout-Baum ist registriert und
    die Zahl ihrer <h1>-Vorkommen stimmt. Eine neue H1 ohne Eintrag fällt auf,
    bevor sie gebaut wird."""
    funde: list[str] = []
    layouts = wurzel / "layouts"
    if not layouts.is_dir():
        return ["S2: layouts/ fehlt – ohne Vorlagen ist der Layoutvertrag nicht "
                "prüfbar (fail-closed)."]
    gefunden: dict[str, int] = {}
    for pfad in sorted(layouts.rglob("*.html")):
        rel = str(pfad.relative_to(wurzel)).replace(os.sep, "/")
        anzahl = len(H1_TAG.findall(_lesen(pfad)))
        if anzahl:
            gefunden[rel] = anzahl
    inventar = {rel: anzahl for rel, anzahl, _grund in H1_QUELLEN}
    for rel, anzahl in sorted(gefunden.items()):
        if rel not in inventar:
            funde.append(
                f"S2: {rel} rendert {anzahl}× `<h1` und steht nicht im Inventar "
                "H1_QUELLEN – eine neue H1-Quelle ohne Eintrag könnte eine "
                "Seite auf zwei H1 bringen. Eintrag mit Grund ergänzen oder "
                "die H1 entfernen.")
        elif inventar[rel] != anzahl:
            funde.append(
                f"S2: {rel} rendert {anzahl}× `<h1`, registriert sind "
                f"{inventar[rel]} (H1_QUELLEN) – die Zahl im Inventar ist "
                "Teil des Vertrags, keine Doku.")
    for rel, anzahl, _grund in H1_QUELLEN:
        if rel not in gefunden:
            funde.append(f"S2: H1_QUELLEN nennt {rel} mit {anzahl} H1 – die "
                         "Datei fehlt oder rendert keine H1 mehr.")
    # Beide Sichten müssen zusammenpassen: keine Seite ohne Quelle, keine
    # Quelle ohne Seite.
    for seitenart, rel, beschreibung in SEITENARTEN:
        if rel not in inventar:
            funde.append(f"S2: Seitenart „{seitenart}“ ({beschreibung}) steht auf "
                         f"{rel} – diese Quelle fehlt im Inventar H1_QUELLEN.")
    quellen_mit_seite = {rel for _art, rel, _b in SEITENARTEN}
    for rel, _anzahl, grund in H1_QUELLEN:
        if rel not in quellen_mit_seite:
            funde.append(f"S2: H1-Quelle {rel} ({grund}) gehört zu keiner "
                         "Seitenart in SEITENARTEN – dann weiß niemand, welche "
                         "Seite diese H1 trägt.")
    return funde


def _blaetterkopf_funde(wurzel: Path) -> list[str]:
    """Die Startseite hat zwei sich ausschließende H1-Quellen: den Hero auf
    Seite 1 und den Blätterkopf ab Seite 2. Der Blätterkopf wird über seinen
    Marker geprüft – fehlt er, trägt /page/2/ gar keine H1 (Befund vom
    08.10.2026, von einer pauschalen Ausnahme verdeckt)."""
    liste = _lesen(wurzel / "layouts" / "_default" / "list.html")
    if not liste.strip():
        return []  # „leer“ meldet bereits die Hauptprüfung
    stellen = [m.start() for m in re.finditer(re.escape(H1_BLAETTERKOPF_MARKER), liste)]
    if len(stellen) != 1:
        return [f"S2: layouts/_default/list.html trägt den Marker "
                f"„{H1_BLAETTERKOPF_MARKER}“ {len(stellen)}× (erwartet: 1) – die "
                "Startseiten-Blätterseiten /page/N/ brauchen ab Seite 2 eine "
                "eigene H1; ohne sie trägt die Seite gar keine."]
    stelle = stellen[0]
    davor = liste[max(0, stelle - 400):stelle]
    # Fenster: vom Marker bis zum Ende seines Zweigs (`{{- end }}`), höchstens
    # aber 2500 Zeichen – der Zweig darf seine H1 hinter einer Begründung
    # tragen, aber nicht irgendwo sonst in der Datei.
    danach = liste[stelle:stelle + 2500]
    zweig_ende = danach.find("{{- end }}")
    if zweig_ende != -1:
        danach = danach[:zweig_ende]
    funde: list[str] = []
    if ".IsHome" not in davor:
        funde.append(f"S2: der Marker „{H1_BLAETTERKOPF_MARKER}“ hängt an keinem "
                     "`.IsHome`-Zweig – er muss die Startseiten-Blätter meinen, "
                     "nicht irgendeine Liste.")
    if not H1_TAG.search(danach):
        funde.append(f"S2: nach dem Marker „{H1_BLAETTERKOPF_MARKER}“ folgt keine "
                     "`<h1` – die Blätterseite /page/2/ bliebe ohne "
                     "Hauptüberschrift (Befund vom 08.10.2026).")
    return funde


def _paritaets_funde(wurzel: Path) -> list[str]:
    """Einzelansichten mit eigener Vorlage (Themenwelt, Werkzeug) müssen
    `.Params.heading` genauso ehren wie der gemeinsame Baustein."""
    funde: list[str] = []
    for rel in PARITAET_TEMPLATES:
        text = _lesen(wurzel / rel)
        if not text.strip():
            funde.append(f"S2: {rel} ist leer – die Einzelansicht würde nicht rendern.")
        elif ".Params.heading" not in text:
            funde.append(f"S2: {rel} ehrt `.Params.heading` nicht – die "
                         "dokumentierte Schirmzeile („heading: ins Frontmatter“) "
                         "wäre auf dieser Seite wirkungslos, und die nächste "
                         "eigene Überschrift landete wieder als zweite H1 im "
                         "Fließtext (#623).")
    return funde


def s2_layout(wurzel: Path = ROOT) -> list[str]:
    funde: list[str] = []
    baustein = _lesen(wurzel / "layouts" / "_partials" / "artikel_einzeln.html")
    single_default = _lesen(wurzel / "layouts" / "_default" / "single.html")
    single_wurzel = _lesen(wurzel / "layouts" / "single.html")
    liste = _lesen(wurzel / "layouts" / "_default" / "list.html")
    # Vollständiges Inventar zuerst: es fängt jede H1, die niemand eingetragen
    # hat – die teuerste Klasse von Fehlern, weil sie unsichtbar entsteht.
    funde.extend(_inventar_funde(wurzel))
    funde.extend(_blaetterkopf_funde(wurzel))
    funde.extend(_paritaets_funde(wurzel))

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

class _H1TextParser(HTMLParser):
    """HTML-aware H1 counter; comments and script strings are not markup.

    Regex over serialized HTML can mistake ``<h1>`` in comments, JavaScript,
    CSS or inert ``<template>`` content for a real page heading. It also
    mistakes every named entity (including visible ``&amp;``) for whitespace.
    The standard-library parser gives the build gate and the full A11y audit
    one consistent, entity-aware view without adding a runtime dependency.
    """

    _TEXTLESS_TAGS = {"script", "style"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.h1_texts: list[list[str]] = []
        # A None stack entry marks an H1 inside inert <template> content, so
        # its closing tag cannot accidentally close a surrounding real H1.
        self._h1_stack: list[int | None] = []
        self._template_depth = 0
        self._textless_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag == "template":
            self._template_depth += 1
        if tag == "h1":
            if self._template_depth:
                self._h1_stack.append(None)
            else:
                self.h1_texts.append([])
                self._h1_stack.append(len(self.h1_texts) - 1)
        if tag in self._TEXTLESS_TAGS:
            self._textless_stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "h1" and self._h1_stack:
            self._h1_stack.pop()
        if tag in self._TEXTLESS_TAGS:
            for index in range(len(self._textless_stack) - 1, -1, -1):
                if self._textless_stack[index] == tag:
                    del self._textless_stack[index]
                    break
        if tag == "template":
            self._template_depth = max(0, self._template_depth - 1)

    def handle_data(self, data: str) -> None:
        if self._template_depth or self._textless_stack:
            return
        for index in reversed(self._h1_stack):
            if index is not None:
                self.h1_texts[index].append(data)
                break


def h1_der_seite(html: str) -> list[str]:
    """Gibt den normalisierten Text aller echten H1-Elemente zurück.

    HTML-Entities werden dekodiert, Inline-Markup wird entfernt und
    zusammenhängende Leerzeichen (inkl. NBSP) werden vereinheitlicht.
    Leere H1 bleiben als ``""`` erhalten, damit S3 sie ausdrücklich meldet.
    """
    parser = _H1TextParser()
    parser.feed(html)
    parser.close()
    return [" ".join("".join(teile).split()) for teile in parser.h1_texts]


def h1_ist_gefuellt(text: str) -> bool:
    """True only if the heading contains a visible, non-whitespace character."""
    return any(
        not char.isspace() and unicodedata.category(char) not in {"Cc", "Cf", "Cs"}
        for char in text
    )


def s3_build(public: Path, ausnahmen=AUSNAHMEN_H1) -> list[str]:
    funde: list[str] = []
    if not public.is_dir():
        return [f"S3: {public} fehlt – ohne Build ist die gebaute Wahrheit nicht prüfbar (fail-closed)."]
    geprueft = 0
    html_dateien = (pfad for pfad in public.rglob("*")
                    if pfad.is_file() and pfad.suffix.lower() == ".html")
    for pfad in sorted(html_dateien):
        rel = str(pfad.relative_to(public)).replace(os.sep, "/")
        if ausnahme_grund(rel, ausnahmen):
            continue
        geprueft += 1
        texte = h1_der_seite(_lesen(pfad))
        if len(texte) != 1:
            if not texte:
                fund = (f"S3: {rel} trägt GAR KEINE H1 (erwartet: 1) – eine Seite ohne "
                        "Hauptüberschrift gibt Screenreadern, Inhaltsverzeichnis und "
                        "KI-Antworten keinen Einstieg")
            else:
                fund = (f"S3: {rel} trägt {len(texte)} H1 (erwartet: 1): {texte[:3]} – "
                        "zwei H1 zerstören die Gliederung für Screenreader, "
                        "Inhaltsverzeichnis und KI-Antworten")
            if BLATTER_ALIAS.search(rel):
                fund += (". Blätter-Alias? Dann fehlt `[pagination] disableAliases = true` "
                         "in hugo.toml (Wache: scripts/index_hygiene_gate.py, H2)")
            funde.append(fund + ".")
            continue
        if not h1_ist_gefuellt(texte[0]):
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

    # S1 – die Markdown-Wahrheit jenseits der `#`-Zeile (Stufe 2, 08.10.2026)
    check("S1: eingerückte ATX-H1 (drei Leerzeichen) wird erkannt",
          markdown_ohne_huelle("---\n---\n\n   # Eingerückt\n") == [(4, "Eingerückt")])
    check("S1: vier Leerzeichen sind eingerückter Code, keine Überschrift",
          markdown_ohne_huelle("    # Code, kein Titel\n") == [])
    check("S1: Setext-H1 wird erkannt und nennt die Textzeile",
          markdown_ohne_huelle("---\n---\n\nSchirmzeile\n===========\n") == [(4, "Schirmzeile")])
    check("S1: Setext-Unterstrich im Code-Zaun bleibt still",
          markdown_ohne_huelle("```\nTitel\n=====\n```\n") == [])
    check("S1: rohes `<h1>` im Fließtext wird erkannt",
          [nr for nr, _ in markdown_roh_html_h1("Text\n\n<h1 class=\"x\">Titel</h1>\n")] == [3])
    check("S1: `<h1>` in Inline-Code ist Text, kein Markup",
          markdown_roh_html_h1("Beispiel: `<h1>Titel</h1>` – so rendert Goldmark es.\n") == [])
    check("S1: rohes `<h1>` im Code-Zaun bleibt Code",
          markdown_roh_html_h1("```html\n<h1>Titel</h1>\n```\n") == [])

    # S2 – Layoutvertrag (gegen den echten Baum)
    check("S2: Layoutvertrag des echten Baums ist grün", s2_layout(wurzel) == [])

    # S2 – Inventar und Parität greifen (künstlicher Baum)
    with tempfile.TemporaryDirectory() as tmp:
        kuenstlich = Path(tmp)
        (kuenstlich / "layouts" / "_default").mkdir(parents=True)
        (kuenstlich / "layouts" / "_partials").mkdir(parents=True)
        (kuenstlich / "layouts" / "_default" / "list.html").write_text(
            "{{- if and .IsHome (gt $paginator.PageNumber 1) }}\n"
            "{{- /* H1-BLÄTTERKOPF: Startseite ab Seite 2 */ -}}\n"
            "<h1>Weitere Ratgeber</h1>\n{{- end }}\n", encoding="utf-8")
        (kuenstlich / "layouts" / "_partials" / "artikel_einzeln.html").write_text(
            '<h1>{{ .Params.heading | default .Title }}</h1>', encoding="utf-8")
        (kuenstlich / "layouts" / "_default" / "single.html").write_text(
            '{{ partial "artikel_einzeln.html" . }}', encoding="utf-8")
        (kuenstlich / "layouts" / "single.html").write_text(
            '{{ partial "artikel_einzeln.html" . }}', encoding="utf-8")
        (kuenstlich / "layouts" / "pillar").mkdir()
        (kuenstlich / "layouts" / "pillar" / "single.html").write_text(
            "<h1>{{ .Title }}</h1>", encoding="utf-8")
        (kuenstlich / "layouts" / "_partials" / "neuer_kasten.html").write_text(
            "<h1>Neuer Kasten</h1>", encoding="utf-8")
        funde_k = s2_layout(kuenstlich)
        check("S2: unregistrierte H1-Quelle wird gemeldet",
              any("neuer_kasten.html" in f and "nicht im Inventar" in f for f in funde_k))
        check("S2: Einzelansicht ohne `.Params.heading` wird gemeldet (Parität)",
              any("pillar/single.html ehrt `.Params.heading` nicht" in f for f in funde_k))
        # Sabotage am Blätterkopf: H1 entfernt → Startseiten-Blätter ohne H1
        (kuenstlich / "layouts" / "_default" / "list.html").write_text(
            "{{- if and .IsHome (gt $paginator.PageNumber 1) }}\n"
            "{{- /* H1-BLÄTTERKOPF: Startseite ab Seite 2 */ -}}\n"
            "<p>Ohne Überschrift</p>\n{{- end }}\n", encoding="utf-8")
        check("S2: fehlende H1 im Startseiten-Blätterkopf wird gemeldet",
              any("folgt keine" in f for f in s2_layout(kuenstlich)))

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
        parserprobe = (
            '<!-- <h1>Kommentar</h1> -->'
            '<script>const markup = "<h1>Skript</h1>";</script>'
            '<template><h1>Vorlage</h1></template>'
            '<H1>Text &amp; <em>Mehr</em></H1>'
        )
        check("S3: HTML-Parser zählt nur echte H1 und dekodiert sichtbare Entities",
              h1_der_seite(parserprobe) == ["Text & Mehr"])
        check("S3: numerische Leerzeichen-Entities ergeben keine gefüllte H1",
              h1_der_seite("<h1>&nbsp;&#160;&#xA0;</h1>") == [""])
        unsichtbar = h1_der_seite("<h1>&#x200B;</h1>")
        check("S3: Zero-Width-Zeichen allein täuschen keine gefüllte H1 vor",
              len(unsichtbar) == 1 and not h1_ist_gefuellt(unsichtbar[0]))

        # Ausnahmen: begründet, routenscharf – und keine, die einen Befund deckt
        (pub / "page" / "2").mkdir(parents=True)
        (pub / "page" / "2" / "index.html").write_text("<html>ohne H1</html>", encoding="utf-8")
        (pub / "google123.html").write_text("google-site-verification: x", encoding="utf-8")
        (pub / "pinterest-ab12.html").write_text("pinterest-site-verification: y", encoding="utf-8")
        funde2 = s3_build(pub)
        check("S3: Blätterseite ohne H1 wird GEPRÜFT (keine Pauschalausnahme)",
              any("page/2/index.html" in f for f in funde2))
        check("S3: Verifikationsdatei ist begründet ausgenommen",
              not any("google123.html" in f for f in funde2))
        check("S3: Pinterest-Verifikationsdatei ist begründet ausgenommen",
              not any("pinterest-ab12.html" in f for f in funde2))

        # Sabotage: die frühere Pauschalausnahme darf nirgends zurückkehren –
        # eine Ausnahme, die den Befund deckt, ist ein Versteck.
        (pub / "page" / "2" / "index.html").write_text(
            "<html lang=de><h1>Weitere Ratgeber</h1></html>", encoding="utf-8")
        check("S3: Blätterseite mit genau einer H1 ist grün",
              not any("page/2/index.html" in f for f in s3_build(pub)))

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
