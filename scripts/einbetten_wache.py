#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
#  EINBETT-WACHE – DAS VERLINKBARE ANGEBOT MUSS STIMMEN
#  ------------------------------------------------------------
#  WARUM ES DIESE WACHE GIBT (27.10.2026)
#
#  Der Seobility-Check nennt als einzigen kritischen Punkt: „fast keine
#  Links von anderen Webseiten“ (Externe Faktoren 0 %). Der Gegenhebel
#  ist kein Pitch, sondern ein fertiger Copy-Paste-Block: Bild plus
#  Quellenzeile, beides mit Link. Genau diesen Block liefert
#  `layouts/_partials/ff_einbetten.html` aus (Shortcode „einbetten“).
#
#  Dieses Angebot ist nur dann einen Backlink wert, wenn der Block
#  fehlerfrei ist. Ein falscher Block ist schlimmer als kein Block:
#    · ein relativer `src` bricht, sobald jemand den Code woanders
#      einfügt (dann zeigt das Bild auf die fremde Domain),
#    · ein `rel="nofollow"` im Snippet bittet um genau den Link, den
#      die Seite nicht bekommt,
#    · ein `?utm_…` im Snippet macht aus der Quellenzeile Werbung,
#    · ein leerer `alt`/fehlende Maße erzeugen im fremden Layout
#      Sprünge und im eigenen A11Y-Audit einen Fehler,
#    · ein Kopier-Knopf ohne Ziel-ID kopiert nichts und meldet nichts.
#
#  WAS GEPRÜFT WIRD (Build, `public/`)
#    E1  Der Block hat einen Namen: `aria-labelledby` zeigt seitenweit auf
#        eine echte Überschrift (die steht außerhalb der <section>, weil der
#        Chunker-Vertrag im Artikelinhalt keine H2 im Container erlaubt).
#    E2  Das Snippet enthält genau ein `<figure>` mit `<img>`, dessen
#        `src` absolut ist und `width`/`height`/nicht-leeren `alt` hat.
#    E3  Beide Links im Snippet sind absolut, zeigen auf DIESELBE URL
#        (Bild und Quellenzeile) und tragen kein `nofollow`/`sponsored`.
#    E4  Die Links enthalten keine Tracking-Parameter (utm_*, pk_*, mtm_*,
#        gclid, fbclid, mc_cid, ref).
#    E5  Es gibt kein `<script>`/`<iframe>`/`<form>` im Snippet – das
#        Angebot muss ohne Cookie und ohne Fremdcode funktionieren.
#    E6  Kopier-Knopf: `data-ff-einbetten-kopieren` zeigt auf eine
#        existierende ID, und ein Live-Bereich (`role="status"`) ist da.
#
#  WARUM EIGENER PARSER STATT bs4 (28.10.2026, roter Lauf „gate“)
#  ------------------------------------------------------------
#  Diese Wache läuft über `scripts/selftest_runner.py` in jedem Gate.
#  Der Gate-Job installiert nur `requirements-ci.txt` – dort steht kein
#  bs4. Die erste Fassung starb dort mit `ModuleNotFoundError` und riss
#  den ganzen Gate-Job mit. Die anderen Build-Wachen dieses Repos
#  (`linktext_wache.py`, `a11y_audit.py`) lesen HTML deshalb mit
#  `html.parser` aus der Standardbibliothek. Ein Prüfwerkzeug, das nur in
#  einer Umgebung mit Zusatzpaketen funktioniert, prüft überall sonst
#  nichts.
#
#  Kein Whitelisting: Was hier durchfällt, ist ein echter Defekt im
#  Angebot – nicht ein Sonderfall der Redaktion.
# ============================================================
from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qsl

BLOG_DIR = Path(__file__).resolve().parent.parent
PUBLIC = BLOG_DIR / "public"

# Nur echte Kampagnen-Parameter. Ein Blick auf `href="…"` würde sonst
# schon am Wort „ref=“ in `href=` anschlagen – genau dieser Fehlalarm
# stand beim ersten Lauf auf dem Zettel.
SPUR_PARAMETER = ("utm_source", "utm_medium", "utm_campaign", "utm_content",
                  "utm_term", "pk_campaign", "pk_kwd", "mtm_campaign",
                  "gclid", "fbclid", "mc_cid", "mc_eid", "ref")
VERBOTENE_TAGS = ("script", "iframe", "form", "object", "embed")
UEBERSCHRIFTEN = ("h1", "h2", "h3", "h4", "h5", "h6")
LEER = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}


class Knoten:
    """Minimaler DOM-Knoten: Tag, Attribute, Kinder, eigener Text."""

    __slots__ = ("tag", "attrs", "kids", "texte", "eltern")

    def __init__(self, tag: str, attrs: dict | None = None, eltern=None):
        self.tag = tag
        self.attrs = attrs or {}
        self.kids: list[Knoten] = []
        self.texte: list[str] = []
        self.eltern = eltern

    # --- Attribute ---------------------------------------------------
    def get(self, name: str, vorgabe: str | None = None) -> str | None:
        return self.attrs.get(name, vorgabe)

    @property
    def klassen(self) -> set[str]:
        return set((self.attrs.get("class") or "").split())

    def hat_klasse(self, name: str) -> bool:
        return name in self.klassen

    # --- Baum --------------------------------------------------------
    def alle(self, tag: str | None = None):
        for kind in self.kids:
            if tag is None or kind.tag == tag:
                yield kind
            yield from kind.alle(tag)

    def erste(self, tag: str | None = None, klasse: str | None = None):
        for knoten in self.alle(tag):
            if klasse is None or knoten.hat_klasse(klasse):
                return knoten
        return None

    def mit_id(self, wert: str):
        for knoten in self.alle():
            if knoten.attrs.get("id") == wert:
                return knoten
        return None

    def text(self) -> str:
        """textContent: eigener Text plus alle Nachfahren, in Reihenfolge."""
        teile = list(self.texte)
        for kind in self.kids:
            teile.append(kind.text())
        return "".join(teile)


class Baum(HTMLParser):
    """Baut aus HTML einen Knotenbaum (tolerant, ohne Zusatzpakete)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.wurzel = Knoten("#dokument")
        self._stapel = [self.wurzel]

    def _anhaengen(self, tag: str, attrs) -> Knoten:
        knoten = Knoten(tag, {k: (v if v is not None else "") for k, v in attrs},
                        self._stapel[-1])
        self._stapel[-1].kids.append(knoten)
        return knoten

    def handle_starttag(self, tag, attrs):
        knoten = self._anhaengen(tag, attrs)
        if tag not in LEER:
            self._stapel.append(knoten)

    def handle_startendtag(self, tag, attrs):
        self._anhaengen(tag, attrs)

    def handle_endtag(self, tag):
        # Tolerant schließen: bis zum passenden Tag zurückrollen.
        for i in range(len(self._stapel) - 1, 0, -1):
            if self._stapel[i].tag == tag:
                del self._stapel[i:]
                return

    def handle_data(self, data):
        self._stapel[-1].texte.append(data)


def baum(html_text: str) -> Knoten:
    parser = Baum()
    parser.feed(html_text)
    parser.close()
    return parser.wurzel


def _absolut(wert: str) -> bool:
    return wert.startswith("https://") or wert.startswith("http://")


def pruefe_block(block: Knoten, seite: str, dokument: Knoten | None = None) -> list[str]:
    """Prüft einen `.ff-einbetten`-Block und gibt Befunde zurück.

    `dokument` ist die ganze Seite: Die Überschrift steht seit dem
    Chunker-Vertrag (layout_audit.py) AUSSERHALB der <section> – eine H2
    mit id darf im Artikelinhalt kein Container-Kind sein, sonst reißt die
    Text-Teilung den Block auf. Der Name der Section muss trotzdem auf eine
    echte Überschrift zeigen, deshalb wird seitenweit gesucht.
    """
    funde: list[str] = []
    titel_id = block.get("aria-labelledby")
    if not titel_id:
        funde.append(f"E1: Block ohne aria-labelledby ({seite})")
    else:
        ziel = dokument.mit_id(titel_id) if dokument is not None else None
        if ziel is None:
            funde.append(f"E1: aria-labelledby zeigt auf fehlende ID {titel_id!r} ({seite})")
        elif ziel.tag not in UEBERSCHRIFTEN:
            funde.append(f"E1: aria-labelledby zeigt auf <{ziel.tag}>, keine Überschrift ({seite})")

    code = block.erste(klasse="ff-einbetten__code")
    if code is None:
        funde.append(f"E1: kein <pre class=ff-einbetten__code> ({seite})")
        return funde
    snippet_text = code.text()
    if "{{" in snippet_text or "}}" in snippet_text:
        funde.append(f"E2: unrenderte Template-Reste im Snippet ({seite})")
    if "%!" in snippet_text:
        funde.append(f"E2: kaputter Format-String im Snippet ({seite})")

    unter = baum(snippet_text)
    for tag in VERBOTENE_TAGS:
        if unter.erste(tag) is not None:
            funde.append(f"E5: <{tag}> im Snippet – Angebot muss statisch sein ({seite})")

    figuren = list(unter.alle("figure"))
    if len(figuren) != 1:
        funde.append(f"E2: Snippet enthält {len(figuren)} <figure> statt genau eins ({seite})")
        return funde
    figure = figuren[0]

    bilder = list(figure.alle("img"))
    if len(bilder) != 1:
        funde.append(f"E2: Snippet enthält {len(bilder)} <img> statt genau eins ({seite})")
        return funde
    bild = bilder[0]
    src = bild.get("src") or ""
    if not _absolut(src):
        funde.append(f"E2: Bild-src ist nicht absolut: {src!r} ({seite})")
    if not (bild.get("alt") or "").strip():
        funde.append(f"E2: Bild ohne alt-Text ({seite})")
    for mass in ("width", "height"):
        wert = (bild.get(mass) or "").strip()
        if not wert.isdigit() or int(wert) <= 0:
            funde.append(f"E2: Bild ohne gültiges {mass} ({seite})")

    links = list(figure.alle("a"))
    if len(links) != 2:
        funde.append(f"E3: {len(links)} Links im Snippet (erwartet: Bild + Quellenzeile) ({seite})")
    ziele = {(a.get("href") or "") for a in links}
    if len(ziele) != 1:
        funde.append(f"E3: Bild und Quellenzeile zeigen auf verschiedene URLs: "
                     f"{sorted(ziele)} ({seite})")
    for ziel in ziele:
        if not _absolut(ziel):
            funde.append(f"E3: Linkziel nicht absolut: {ziel!r} ({seite})")
    for a in links:
        rel = " ".join((a.get("rel") or "").split()).lower()
        if "nofollow" in rel or "sponsored" in rel:
            funde.append(f"E3: Snippet-Link trägt rel={rel!r} ({seite})")
        # Ein Link um ein Bild hat als Linktext naturgemäß keinen Text –
        # sein Name kommt aus dem alt-Text (E2 prüft, dass er da ist).
        if not a.text().strip() and a.erste("img") is None:
            funde.append(f"E3: Snippet-Link ohne Linktext ({seite})")

    for ziel in ziele:
        for schluessel, _wert in parse_qsl(ziel.split("?", 1)[-1]):
            if schluessel.lower() in SPUR_PARAMETER:
                funde.append(f"E4: Tracking-Parameter {schluessel!r} im Link ({seite})")

    knopf = None
    for knoten in block.alle():
        if "data-ff-einbetten-kopieren" in knoten.attrs:
            knopf = knoten
            break
    if knopf is None:
        funde.append(f"E6: kein Kopier-Knopf ({seite})")
    else:
        ziel_id = knopf.get("data-ff-einbetten-kopieren") or ""
        if ziel_id != (code.get("id") or ""):
            funde.append(
                f"E6: Knopf zielt auf {ziel_id!r}, das <pre> hat "
                f"id={(code.get('id') or '')!r} ({seite})"
            )
    live = any(k.get("role") == "status" for k in block.alle())
    if not live:
        funde.append(f"E6: kein Live-Bereich (role=status) für die Rückmeldung ({seite})")
    return funde


def pruefe_public(public: Path | str = PUBLIC) -> tuple[int, list[str]]:
    root = Path(public)
    if not root.is_dir():
        return 0, [f"E0: Build fehlt ({root}) – erst `hugo --minify` laufen lassen"]
    blocke = 0
    funde: list[str] = []
    for html_datei in sorted(root.rglob("*.html")):
        seite = "/" + str(html_datei.relative_to(root))
        dokument = baum(html_datei.read_text(encoding="utf-8", errors="replace"))
        for block in dokument.alle("section"):
            if not block.hat_klasse("ff-einbetten"):
                continue
            blocke += 1
            funde.extend(pruefe_block(block, seite, dokument))
    return blocke, funde


def selftest() -> int:
    gutes_snippet = (
        '<figure><a href="https://franksfinanzcheck.de/x/">'
        '<img src="https://franksfinanzcheck.de/downloads/x.svg" width="1200" '
        'height="628" alt="Grafik"></a><figcaption>Grafik: '
        '<a href="https://franksfinanzcheck.de/x/">Quelle</a></figcaption></figure>'
    )

    def block(snippet: str = gutes_snippet, knopf_ziel: str = "ff-einbetten-x",
              titel: bool = True) -> str:
        aria = ' aria-labelledby="ff-einbetten-x-titel"' if titel else ""
        kopf = '<h2 id="ff-einbetten-x-titel">Grafik einbetten</h2>' if titel else ""
        # Der Code steht escaped im <pre> – wie im echten Build.
        from html import escape
        return (
            f'<main>{kopf}<section class="ff-einbetten"{aria}>'
            f'<pre class="ff-einbetten__code" id="ff-einbetten-x">'
            f'<code>{escape(snippet, quote=False)}</code></pre>'
            f'<button data-ff-einbetten-kopieren="{knopf_ziel}">kopieren</button>'
            '<p role="status"></p></section></main>'
        )

    def funde(markup: str) -> list[str]:
        dokument = baum(markup)
        block_knoten = dokument.erste("section", "ff-einbetten")
        return pruefe_block(block_knoten, "test", dokument)

    faelle = [
        ("guter Block", funde(block()), 0),
        ("relativer Bildpfad", funde(block(gutes_snippet.replace(
            'src="https://franksfinanzcheck.de/downloads/x.svg"', 'src="/downloads/x.svg"'))), 1),
        ("nofollow im Snippet", funde(block(gutes_snippet.replace(
            '<a href="https://franksfinanzcheck.de/x/"><img',
            '<a rel="nofollow" href="https://franksfinanzcheck.de/x/"><img'))), 1),
        ("Tracking-Parameter", funde(block(gutes_snippet.replace(
            "https://franksfinanzcheck.de/x/",
            "https://franksfinanzcheck.de/x/?utm_source=li"))), 1),
        ("leerer alt-Text", funde(block(gutes_snippet.replace('alt="Grafik"', 'alt=""'))), 1),
        ("iframe im Snippet", funde(block(
            gutes_snippet + '<iframe src="https://x.test/"></iframe>')), 1),
        ("Knopf zeigt ins Leere", funde(block(knopf_ziel="ff-einbetten-y")), 1),
        ("Block ohne Namen", funde(block(titel=False)), 1),
        ("Format-Reste", funde(block(gutes_snippet + "%!d(string=1200)")), 1),
    ]
    fehler = 0
    for name, gefunden, erwartet in faelle:
        if len(gefunden) != erwartet:
            print(f"SELFTEST FEHLER: {name}: {len(gefunden)} statt {erwartet} Befunde")
            for f in gefunden:
                print("   ", f)
            fehler += 1
    if fehler:
        return 1
    print(f"✅ Selbsttest: {len(faelle)} Fälle – E1–E6 sind scharf.")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return selftest()
    public = PUBLIC
    if "--public" in argv:
        public = Path(argv[argv.index("--public") + 1])
    blocke, funde = pruefe_public(public)
    print("== EINBETT-WACHE – das verlinkbare Angebot ==")
    print(f"  Blöcke im Build: {blocke}")
    for f in funde:
        print(f"  ❌ {f}")
    if funde:
        print(f"\n❌ {len(funde)} Befunde – ein fehlerhaftes Angebot ist schlimmer als keins.")
        return 1
    if blocke == 0:
        print("\n❌ Kein Einbett-Block im Build – das Angebot ist verschwunden.")
        return 1
    print("\n✅ Einbett-Blöcke sind absolut, statisch, ohne Tracking und kopierbar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
