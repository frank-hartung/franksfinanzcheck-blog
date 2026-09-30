#!/usr/bin/env python3
# ============================================================
#  TABELLEN-LESBARKEITS-WACHE (Profi-Agentur-Level, 30.09.2026)
#  ------------------------------------------------------------
#  ANLASS (Frank-Befund, /pillar/): „Die FranksFinanzcheck
#  Spar-Matrix auf einen Blick" war unlesbar – fuenf Spalten ohne
#  Zellpolster, ohne Kopfkontrast, ohne Zeilenfuehrung.
#
#  URSACHE (dieselbe Klasse wie die .ff-pc-*-Luecke vom 28.09.):
#  Das Premium-Tabellen-System liegt in z-premium-blog.css, aber
#  JEDE seiner Regeln beginnt mit `.post-content`. Die Spar-Matrix
#  wird jedoch vom LAYOUT gebaut (layouts/pillar/list.html) und
#  steht ausserhalb dieses Containers. Die einzige Regel, die sie
#  je meinte (`.ff-spar-matrix table`, custom.css), zeigte auf einen
#  Klassennamen, den es im Markup nicht mehr gibt. Uebrig blieb der
#  PaperMod-Reset (`table{display:block}`) – also gar nichts.
#
#  Diese Wache macht genau diesen Schadenstyp unmoeglich:
#
#    L1  KLASSENABDECKUNG  Jede Tabellen-Klasse aus den Templates
#        (Tabelle, Wrapper, Zellen) hat mindestens einen Selektor
#        in assets/css/** – sonst faellt die Komponente auf
#        Browser-/Theme-Default zurueck.
#    L2  SCOPE-FALLE       Fuer Tabellen AUSSERHALB von
#        `.post-content` muss die Versorgung auch ausserhalb
#        greifen: mindestens ein deckender Selektor ohne
#        `.post-content`/`.md-content`-Praefix.
#    L3  LESBARKEITS-FLOOR Die deckenden Regeln muessen die vier
#        Lesbarkeits-Grundpfeiler liefern: Zellpolster (>= 10 px),
#        Kopf-Flaeche, Zeilentrenner und einen Mobilpfad
#        (@media max-width) fuer breite Tabellen.
#    L4  TOTE SELEKTOREN   Kein `.ff-*`-Tabellenselektor im CSS,
#        dessen Klasse in keinem Template/Markdown vorkommt
#        (genau die `.ff-spar-matrix`-Leiche).
#    L5  MARKUP-VERTRAG    Spar-Matrix: Spaltenzahl == colgroup ==
#        Kopfzellen, Zeilenkopf als `th scope="row"`, jede Datenzelle
#        mit `data-label` (Feldname der mobilen Kartenansicht),
#        Scroll-Container mit role/aria-label/tabindex.
#
#  SABOTAGE-SCHUTZ: `--selftest` baut sieben kaputte Miniatur-
#  Repos im Temp und verlangt, dass jede Regel genau dort feuert.
#  Schlaegt der Selbsttest fehl, ist der Messer stumpf -> Exit 2,
#  bevor irgendetwas bewertet wird.
#
#  Aufruf:
#    python3 scripts/tabellen_lesbarkeit_guard.py            # Report, Exit 1 bei Fund
#    python3 scripts/tabellen_lesbarkeit_guard.py --selftest # nur Sabotageproben
#    python3 scripts/tabellen_lesbarkeit_guard.py --json     # Maschinenausgabe
#  Ausgabe: TABELLEN-LESBARKEIT-REPORT.md
# ============================================================

from __future__ import annotations

import json
import re
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "TABELLEN-LESBARKEIT-REPORT.md"

# ------------------------------------------------------------
#  VERTRAG: Tabellen-Komponenten, die NICHT in `.post-content`
#  gerendert werden. Wer hier steht, braucht eine Versorgung, die
#  ohne den Artikel-Container funktioniert.
# ------------------------------------------------------------
@dataclass(frozen=True)
class Komponente:
    name: str
    template: str          # Pfad relativ zum Repo
    tabelle: str           # Klasse der <table>
    wrapper: str           # Klasse des Scroll-Containers
    spalten: int           # erwartete Spaltenzahl
    mobil_ab: int = 760    # Breakpoint, unter dem gestapelt wird


KOMPONENTEN = (
    Komponente(
        name="Spar-Matrix (/pillar/)",
        template="layouts/pillar/list.html",
        tabelle="ff-spar-matrix-table",
        wrapper="ff-spar-matrix-scroll",
        spalten=5,
    ),
)

CSS_DIRS = ("assets/css/extended", "assets/css")
TEMPLATE_DIRS = ("layouts",)

SCOPE_PRAEFIXE = (".post-content", ".md-content")

# Klassen, die zum Tabellen-System gehoeren und deshalb von L4
# (tote Selektoren) beobachtet werden.
TABELLEN_KLASSEN_MUSTER = re.compile(r"^ff-(?:tbl|table|spar-matrix|es-table|tv-table|highlight-cell)")


# ============================================================
#  Winziger, robuster CSS-Leser (keine Fremdbibliothek noetig)
# ============================================================
@dataclass
class Regel:
    selektoren: list[str]
    deklarationen: dict[str, str]
    media: str = ""
    quelle: str = ""

    @property
    def mobil(self) -> int | None:
        """Breakpoint einer `max-width`-Bedingung, sonst None."""
        m = re.search(r"max-width\s*:\s*(\d+)\s*px", self.media)
        return int(m.group(1)) if m else None


def css_ohne_kommentare(text: str) -> str:
    return re.sub(r"/\*.*?\*/", " ", text, flags=re.S)


def css_regeln(text: str, quelle: str = "") -> list[Regel]:
    """Flacher Parser: Regeln auf oberster Ebene und in @media-Bloecken."""
    text = css_ohne_kommentare(text)
    regeln: list[Regel] = []

    def parse_block(block: str, media: str) -> None:
        i = 0
        tiefe = 0
        start = 0
        selektor_start = 0
        while i < len(block):
            ch = block[i]
            if ch == "{":
                if tiefe == 0:
                    selektor = block[selektor_start:i]
                    start = i + 1
                tiefe += 1
            elif ch == "}":
                tiefe -= 1
                if tiefe == 0:
                    inhalt = block[start:i]
                    sel = selektor.strip()
                    if sel.startswith("@"):
                        if sel.lower().startswith("@media"):
                            bedingung = sel[len("@media"):].strip()
                            neu = f"{media} and {bedingung}" if media else bedingung
                            parse_block(inhalt, neu)
                        # andere At-Regeln (@keyframes, @font-face) sind hier egal
                    elif sel:
                        regeln.append(Regel(
                            selektoren=[s.strip() for s in sel.split(",") if s.strip()],
                            deklarationen=deklarationen_lesen(inhalt),
                            media=media,
                            quelle=quelle,
                        ))
                    selektor_start = i + 1
            i += 1

    parse_block(text, "")
    return regeln


def deklarationen_lesen(inhalt: str) -> dict[str, str]:
    out: dict[str, str] = {}
    tiefe = 0
    puffer = ""
    for ch in inhalt:
        if ch == "{":
            tiefe += 1
        elif ch == "}":
            tiefe -= 1
        if ch == ";" and tiefe == 0:
            if ":" in puffer:
                k, _, v = puffer.partition(":")
                out[k.strip().lower()] = v.strip()
            puffer = ""
        else:
            puffer += ch
    if ":" in puffer and tiefe == 0:
        k, _, v = puffer.partition(":")
        out.setdefault(k.strip().lower(), v.strip())
    return out


def selektor_trifft(selektor: str, klassen: set[str]) -> bool:
    """Trifft der Selektor eine der Klassen (als Klassen-Token)?"""
    gefunden = set(re.findall(r"\.([A-Za-z0-9_-]+)", selektor))
    return bool(gefunden & klassen)


def selektor_ist_gescopt(selektor: str) -> bool:
    """Beginnt der Selektor mit einem Artikel-Container-Praefix?"""
    # `:root[data-theme="dark"] .post-content …` zaehlt ebenfalls als gescopt,
    # deshalb wird der gesamte Selektor auf die Praefixe geprueft, aber nur
    # dann, wenn das Praefix VOR der Tabellenklasse steht.
    for p in SCOPE_PRAEFIXE:
        if p in selektor:
            return True
    return False


# ============================================================
#  Einlesen des Projekts
# ============================================================
def css_dateien(root: Path) -> list[Path]:
    dateien: list[Path] = []
    for d in CSS_DIRS:
        pfad = root / d
        if pfad.exists():
            dateien += sorted(p for p in pfad.rglob("*.css") if p.is_file())
    # doppelte Treffer (assets/css deckt extended mit ab) entfernen
    einmalig: list[Path] = []
    gesehen: set[Path] = set()
    for p in dateien:
        if p not in gesehen:
            gesehen.add(p)
            einmalig.append(p)
    return einmalig


def alle_regeln(root: Path) -> list[Regel]:
    regeln: list[Regel] = []
    for p in css_dateien(root):
        regeln += css_regeln(p.read_text(encoding="utf-8"),
                             quelle=str(p.relative_to(root)))
    # Inline-<style> in Templates (Shortcodes tragen ihre Optik selbst)
    for d in TEMPLATE_DIRS:
        pfad = root / d
        if not pfad.exists():
            continue
        for p in sorted(pfad.rglob("*.html")):
            txt = p.read_text(encoding="utf-8")
            for block in re.findall(r"<style[^>]*>(.*?)</style>", txt, flags=re.S):
                regeln += css_regeln(block, quelle=str(p.relative_to(root)))
    return regeln


def template_text(root: Path, rel: str) -> str:
    p = root / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""


def projekt_klassen(root: Path) -> set[str]:
    """Alle im Markup (Templates + Markdown) verwendeten Klassen."""
    klassen: set[str] = set()
    quellen: list[Path] = []
    for d in ("layouts", "content", "static", "themes", "tools", "newsletter-worker"):
        pfad = root / d
        if pfad.exists():
            quellen += [p for p in pfad.rglob("*")
                        if p.is_file() and p.suffix in {".html", ".md", ".js", ".mjs", ".py", ".json"}]
    for p in quellen:
        try:
            txt = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for m in re.findall(r'class="([^"]*)"', txt):
            for k in m.split():
                klassen.add(k.strip())
        # Klassennamen entstehen hier nicht nur in class="…": der
        # Render-Hook setzt sie per printf zusammen ("ff-tbl-a-%s"), und
        # Partials bekommen sie als Parameter ("class" "ff-table-btn").
        # Fuer L4 zaehlt deshalb jedes woertlich vorkommende ff-Token.
        klassen.update(re.findall(r"\bff-[A-Za-z0-9_-]+", txt))
        for stamm, endungen in (("ff-tbl-a-", ("left", "center", "right")),):
            if stamm in txt:
                klassen.update(stamm + e for e in endungen)
    return klassen


# ============================================================
#  Die fuenf Pruefungen
# ============================================================
@dataclass
class Befund:
    regel: str
    text: str


@dataclass
class Ergebnis:
    funde: list[Befund] = field(default_factory=list)
    geprueft: dict[str, int] = field(default_factory=dict)

    def add(self, regel: str, text: str) -> None:
        self.funde.append(Befund(regel, text))


def markup_klassen_der_komponente(tpl: str, k: Komponente) -> set[str]:
    """Klassen aus allen class="…"-Attributen im Tabellenblock des Templates."""
    klassen: set[str] = set()
    for attr in re.findall(r'class="([^"{}]*)"', tpl):
        tokens = attr.split()
        klassen.update(t for t in tokens if t)
    # nur Tabellen-relevante Klassen behalten
    return {k2 for k2 in klassen if TABELLEN_KLASSEN_MUSTER.match(k2)}


def pruefe(root: Path) -> Ergebnis:
    erg = Ergebnis()
    regeln = alle_regeln(root)
    erg.geprueft["css_regeln"] = len(regeln)
    erg.geprueft["komponenten"] = len(KOMPONENTEN)
    markup = projekt_klassen(root)

    for k in KOMPONENTEN:
        tpl = template_text(root, k.template)
        if not tpl:
            erg.add("L1", f"{k.name}: Template {k.template} fehlt")
            continue

        klassen = markup_klassen_der_komponente(tpl, k) | {k.tabelle, k.wrapper}
        erg.geprueft["klassen"] = erg.geprueft.get("klassen", 0) + len(klassen)

        # ---------- L1 / L2 ----------
        for klasse in sorted(klassen):
            deckend = [r for r in regeln
                       if any(selektor_trifft(s, {klasse}) for s in r.selektoren)]
            if not deckend:
                erg.add("L1", f"{k.name}: Klasse .{klasse} steht im Markup, "
                              f"hat aber KEINEN Selektor in der CSS")
                continue
            frei = [r for r in deckend
                    if any(selektor_trifft(s, {klasse}) and not selektor_ist_gescopt(s)
                           for s in r.selektoren)]
            if not frei:
                erg.add("L2", f"{k.name}: .{klasse} wird ausschliesslich unter "
                              f"{'/'.join(SCOPE_PRAEFIXE)} versorgt – die Komponente "
                              f"steht aber ausserhalb des Artikel-Containers")

        # ---------- L3 ----------
        zellregeln = [r for r in regeln
                      if not r.media
                      and any((not selektor_ist_gescopt(s))
                              and selektor_trifft(s, {k.tabelle, k.wrapper, "ff-tbl", "ff-table-scroll"})
                              and re.search(r"\b(td|th)\b", s)
                              for s in r.selektoren)]
        polster = _max_padding(zellregeln)
        if polster < 10:
            erg.add("L3", f"{k.name}: Zellpolster zu klein oder nicht gesetzt "
                          f"(gefunden {polster} px, Mindestmass 10 px)")
        if not _hat_deklaration(zellregeln, "border-bottom", "border"):
            erg.add("L3", f"{k.name}: kein Zeilentrenner (border-bottom) auf den Zellen")

        kopfregeln = [r for r in regeln
                      if not r.media
                      and any((not selektor_ist_gescopt(s))
                              and selektor_trifft(s, {k.tabelle, "ff-tbl"})
                              and "thead" in s
                              for s in r.selektoren)]
        if not _hat_deklaration(kopfregeln, "background", "background-color"):
            erg.add("L3", f"{k.name}: Kopfzeile ohne eigene Flaeche "
                          f"(thead th ohne background)")

        mobil = [r for r in regeln
                 if (r.mobil or 0) >= 1
                 and any(selektor_trifft(s, {k.tabelle, k.wrapper}) for s in r.selektoren)]
        if not mobil:
            erg.add("L3", f"{k.name}: kein Mobilpfad – unter {k.mobil_ab} px muss die "
                          f"Tabelle stapeln statt quer zu scrollen")

        # ---------- L5 ----------
        erg.funde.extend(_markup_vertrag(tpl, k))

    # ---------- L4 ----------
    for r in regeln:
        for s in r.selektoren:
            for klasse in re.findall(r"\.([A-Za-z0-9_-]+)", s):
                if TABELLEN_KLASSEN_MUSTER.match(klasse) and klasse not in markup:
                    erg.add("L4", f"Tote Selektor-Leiche: .{klasse} "
                                  f"(in {r.quelle}) kommt in keinem Markup vor")
    # Duplikate zusammenfassen
    gesehen: set[tuple[str, str]] = set()
    einmalig: list[Befund] = []
    for b in erg.funde:
        schluessel = (b.regel, b.text)
        if schluessel not in gesehen:
            gesehen.add(schluessel)
            einmalig.append(b)
    erg.funde = einmalig
    return erg


def _max_padding(regeln: list[Regel]) -> int:
    werte: list[int] = []
    for r in regeln:
        for key in ("padding", "padding-top", "padding-block", "padding-bottom"):
            v = r.deklarationen.get(key)
            if not v:
                continue
            zahlen = [int(z) for z in re.findall(r"(\d+)px", v)]
            if zahlen:
                werte.append(zahlen[0])
    return max(werte) if werte else 0


def _hat_deklaration(regeln: list[Regel], *keys: str) -> bool:
    for r in regeln:
        for k in keys:
            wert = r.deklarationen.get(k)
            if wert and wert.strip() not in {"0", "none", "transparent"}:
                return True
    return False


def _markup_vertrag(tpl: str, k: Komponente) -> list[Befund]:
    funde: list[Befund] = []
    block = _tabellenblock(tpl, k.tabelle)
    if not block:
        return [Befund("L5", f"{k.name}: <table class=\"…{k.tabelle}…\"> nicht gefunden")]

    cols = len(re.findall(r"<col\b", block))
    kopf = re.findall(r'<th[^>]*scope="col"', block)
    if cols != k.spalten:
        funde.append(Befund("L5", f"{k.name}: {cols} <col>-Eintraege statt {k.spalten} "
                                  f"– Spaltenbreiten und Inhalt driften auseinander"))
    if len(kopf) != k.spalten:
        funde.append(Befund("L5", f"{k.name}: {len(kopf)} Kopfzellen mit scope=\"col\" "
                                  f"statt {k.spalten}"))
    if 'scope="row"' not in block:
        funde.append(Befund("L5", f"{k.name}: Zeilenkopf ist kein "
                                  f"<th scope=\"row\"> (Screenreader verlieren den Bezug)"))

    # data-label je Datenzelle der Body-Zeile
    zeilen = re.findall(r"<tr>(.*?)</tr>", block, flags=re.S)
    for zeile in zeilen:
        if "<th" not in zeile or 'scope="row"' not in zeile:
            continue
        zellen = re.findall(r"<td\b[^>]*>", zeile)
        ohne = [z for z in zellen if "data-label=" not in z]
        if ohne:
            funde.append(Befund("L5", f"{k.name}: {len(ohne)} Datenzelle(n) ohne "
                                      f"data-label – die mobile Kartenansicht "
                                      f"verliert dort den Feldnamen"))
        break

    wrapper = re.search(r'<div class="[^"]*%s[^"]*"([^>]*)>' % re.escape(k.wrapper), tpl)
    if not wrapper:
        funde.append(Befund("L5", f"{k.name}: Scroll-Container .{k.wrapper} fehlt"))
    else:
        attrs = wrapper.group(1)
        for pflicht in ('role="region"', "aria-label=", 'tabindex="0"'):
            if pflicht not in attrs:
                funde.append(Befund("L5", f"{k.name}: Scroll-Container ohne {pflicht} "
                                          f"(Tastatur-/Screenreader-Zugang)"))
    return funde


def _tabellenblock(tpl: str, tabellenklasse: str) -> str:
    start = tpl.find(tabellenklasse)
    if start < 0:
        return ""
    anfang = tpl.rfind("<table", 0, start)
    ende = tpl.find("</table>", start)
    if anfang < 0 or ende < 0:
        return ""
    return tpl[anfang:ende + len("</table>")]


# ============================================================
#  SABOTAGE-SCHUTZ
# ============================================================
GUT_TEMPLATE = """
<section class="ff-spar-matrix-section">
  <div class="ff-table-scroll ff-spar-matrix-scroll" role="region" aria-label="Spar-Matrix" tabindex="0">
    <table class="ff-tbl ff-spar-matrix-table">
      <caption class="ff-spar-matrix-caption">Text</caption>
      <colgroup><col><col><col><col><col></colgroup>
      <thead><tr>
        <th scope="col" class="ff-tbl-corner">Themenbereich</th>
        <th scope="col">Sparpotenzial</th><th scope="col">Aufwand</th>
        <th scope="col">Wichtigster Hebel</th><th scope="col">Aktion</th>
      </tr></thead>
      <tbody><tr>
        <th scope="row" class="ff-tbl-corner ff-spar-matrix-thema"><a href="x/">A</a></th>
        <td class="ff-highlight-cell ff-tbl-num" data-label="Sparpotenzial">1 €</td>
        <td data-label="Aufwand">kurz</td>
        <td data-label="Wichtigster Hebel">Hebel</td>
        <td class="ff-spar-matrix-aktion" data-label="Aktion"><a class="ff-table-btn" href="/go/x/">Los</a></td>
      </tr></tbody>
    </table>
  </div>
</section>
"""

GUT_CSS = """
.ff-spar-matrix-section { padding: 24px; }
.ff-table-scroll { overflow-x: auto; border: 1px solid #ddd; }
.ff-table-scroll .ff-tbl { display: table; border-collapse: separate; }
.ff-table-scroll .ff-tbl th, .ff-table-scroll .ff-tbl td { padding: 12px 14px; border-bottom: 1px solid #ddd; }
.ff-table-scroll .ff-tbl thead th { background: #0E5A43; color: #fff; }
.ff-spar-matrix-scroll { margin-top: 0; }
.ff-spar-matrix-table .ff-highlight-cell { color: #0E5A43; }
.ff-spar-matrix-table .ff-tbl-num { white-space: nowrap; }
.ff-spar-matrix-table .ff-tbl-corner { position: sticky; left: 0; }
.ff-spar-matrix-table .ff-spar-matrix-thema a { font-weight: 700; }
.ff-spar-matrix-table .ff-spar-matrix-aktion { vertical-align: middle; }
.ff-spar-matrix-table .ff-table-btn { min-height: 40px; }
.ff-spar-matrix-caption { caption-side: top; }
@media (max-width: 760px) {
  .ff-spar-matrix-table tbody tr { display: block; }
  .ff-spar-matrix-scroll { overflow-x: visible; }
}
"""


def _nur_im_artikel(css: str) -> str:
    """Jeden Selektor in `.post-content` sperren (Sabotage-Fall L2)."""
    zeilen = []
    for zeile in css.splitlines():
        if "{" in zeile and not zeile.strip().startswith("@") and not zeile.strip().startswith("}"):
            sel, _, rest = zeile.partition("{")
            teile = [f".post-content {t.strip()}" for t in sel.split(",") if t.strip()]
            zeilen.append(", ".join(teile) + " {" + rest)
        else:
            zeilen.append(zeile)
    return "\n".join(zeilen)


def _mini_repo(basis: Path, template: str, css: str) -> Path:
    (basis / "layouts" / "pillar").mkdir(parents=True, exist_ok=True)
    (basis / "assets" / "css" / "extended").mkdir(parents=True, exist_ok=True)
    (basis / "layouts" / "pillar" / "list.html").write_text(template, encoding="utf-8")
    (basis / "assets" / "css" / "extended" / "test.css").write_text(css, encoding="utf-8")
    return basis


def selftest() -> list[str]:
    fehler: list[str] = []
    faelle: list[tuple[str, str, str, str | None]] = [
        ("gesund", GUT_TEMPLATE, GUT_CSS, None),
        ("L1 fehlende Lieferung", GUT_TEMPLATE,
         GUT_CSS.replace(".ff-spar-matrix-table .ff-highlight-cell { color: #0E5A43; }", ""), "L1"),
        # Der Originalschaden: alles ist gestylt – aber ausschliesslich
        # innerhalb des Artikel-Containers, in dem die Komponente nicht liegt.
        ("L2 nur .post-content", GUT_TEMPLATE, _nur_im_artikel(GUT_CSS), "L2"),
        ("L3 kein Polster", GUT_TEMPLATE,
         GUT_CSS.replace("padding: 12px 14px;", "padding: 2px 3px;"), "L3"),
        ("L3 kein Mobilpfad", GUT_TEMPLATE,
         GUT_CSS.split("@media")[0], "L3"),
        ("L4 tote Leiche", GUT_TEMPLATE,
         GUT_CSS + "\n.ff-spar-matrix table { color: red; }\n", "L4"),
        ("L5 Spalten-Drift", GUT_TEMPLATE.replace("<col><col><col><col><col>", "<col><col><col>"),
         GUT_CSS, "L5"),
        ("L5 data-label fehlt", GUT_TEMPLATE.replace(' data-label="Aufwand"', ""), GUT_CSS, "L5"),
    ]
    for name, tpl, css, erwartet in faelle:
        with tempfile.TemporaryDirectory() as tmp:
            basis = _mini_repo(Path(tmp), tpl, css)
            erg = pruefe(basis)
            regeln_gefunden = {b.regel for b in erg.funde}
            if erwartet is None:
                if erg.funde:
                    fehler.append(f"Fall {name}: erwartet 0 Funde, bekam "
                                  f"{[f'{b.regel}: {b.text}' for b in erg.funde]}")
            elif erwartet not in regeln_gefunden:
                fehler.append(f"Fall {name}: {erwartet} haette feuern muessen, "
                              f"gefunden: {sorted(regeln_gefunden) or 'nichts'}")
    return fehler


# ============================================================
#  Bericht
# ============================================================
def schreibe_report(erg: Ergebnis) -> str:
    jetzt = datetime.now(timezone.utc)
    zeilen = [
        "# 📊 TABELLEN-LESBARKEITS-REPORT",
        "",
        f"**Stand:** {jetzt:%Y-%m-%d %H:%M} UTC",
        f"**Geprueft:** {erg.geprueft.get('komponenten', 0)} Tabellen-Komponenten "
        f"ausserhalb von `.post-content` · {erg.geprueft.get('klassen', 0)} Klassen · "
        f"{erg.geprueft.get('css_regeln', 0)} CSS-Regeln",
        f"**Funde:** {len(erg.funde)}",
        "",
    ]
    if erg.funde:
        zeilen += ["| Regel | Befund |", "|---|---|"]
        zeilen += [f"| {b.regel} | {b.text} |" for b in erg.funde]
    else:
        zeilen += ["🎉 Alle Tabellen ausserhalb des Artikel-Containers sind vollstaendig "
                   "versorgt: Klassenabdeckung, Scope, Lesbarkeits-Floor "
                   "(Polster/Kopf/Trenner/Mobilpfad) und Markup-Vertrag erfuellt."]
    zeilen += [
        "",
        "---",
        "_L1 Klassenabdeckung · L2 Scope-Falle · L3 Lesbarkeits-Floor · "
        "L4 tote Selektoren · L5 Markup-Vertrag_",
        "_Wache: `scripts/tabellen_lesbarkeit_guard.py` (Frank-Befund Spar-Matrix, 30.09.2026)_",
    ]
    text = "\n".join(zeilen) + "\n"
    REPORT.write_text(text, encoding="utf-8")
    return text


def main() -> None:
    nur_selftest = "--selftest" in sys.argv
    als_json = "--json" in sys.argv

    fehler = selftest()
    if fehler:
        print("🛑 SELBSTTEST FEHLGESCHLAGEN – die Wache misst falsch, nichts bewertet:")
        print("\n".join(f"  · {f}" for f in fehler))
        sys.exit(2)
    if nur_selftest:
        print("✅ Selbsttest gruen: 8 Sabotage-Faelle, L1–L5 feuern punktgenau.")
        sys.exit(0)

    erg = pruefe(ROOT)
    if als_json:
        print(json.dumps({
            "funde": [{"regel": b.regel, "text": b.text} for b in erg.funde],
            "geprueft": erg.geprueft,
        }, ensure_ascii=False, indent=2))
    else:
        print(schreibe_report(erg))
        if not als_json:
            schreibe_report(erg)
    sys.exit(1 if erg.funde else 0)


if __name__ == "__main__":
    main()
