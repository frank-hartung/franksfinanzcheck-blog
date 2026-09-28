#!/usr/bin/env python3
# ============================================================
#  OFFENLEGUNGS-WACHE – artikelgenaue Werbekennzeichnung, dauerhaft
#  ------------------------------------------------------------
#  AUFTRAG (Frank, 28.09.2026, aus dem ZEIT-Wettbewerbsvergleich):
#    „Unabhängigkeit/Kommerz | ZEIT 5 | FF 4 – FF hat Affiliate-
#     Governance; Offenlegung sollte artikelgenau und noch sichtbarer
#     sein. Bitte dauerhaft auf Premium-Level einer Profi-Agentur
#     heben."
#
#  „DAUERHAFT" IST DER EIGENTLICHE AUFTRAG.
#  Eine Kennzeichnung ist kein Text, den man einmal schreibt, sondern
#  ein Zustand, der bei jedem Build wahr sein muss. Genau daran
#  scheitern Affiliate-Seiten: Der Hinweis existiert, aber er steht an
#  der falschen Stelle, nennt die falschen Partner oder beschreibt
#  einen Artikel, den es so nicht mehr gibt.
#
#  BEFUND, DER ZU DIESER WACHE GEFÜHRT HAT (Messung im gebauten HTML
#  am 28.09.2026, vor dem Umbau):
#    * 48 Seiten mit Partnerlinks – in 27 davon stand der einzige
#      Hinweis NACH dem ersten Werbelink. Wer oben klickte, las die
#      Offenlegung nie.
#    * Die einzige dauerhafte Aussage war ein Konjunktiv in der
#      Trust-Box: „Dieser Artikel KANN Affiliate-Links enthalten
#      (CHECK24, Tarifcheck)" – identisch auf jeder Seite, unabhängig
#      von null oder fünf Links, mit Partnernamen, die im Text gar
#      nicht vorkamen. Ein Satz, der immer stimmt, sagt nichts.
#    * Es gab keine Gegenprobe: Ein Artikel ohne Partnerlink sah
#      exakt aus wie einer mit fünf.
#
#  LEHRE AUS AI4 (Vorfall 01./02.09.2026, „stille Blindheit"):
#  Ein Beweis, der die HTML-Ausgabe nur „anblickt", bricht bei der
#  nächsten Layout-Änderung und meldet dann grüne Nullen. Deshalb hier:
#    1. ATTRIBUT-TOLERANT: Es wird geparst, nicht gemustert –
#       minifiziert oder nicht, mit oder ohne Anführungszeichen,
#       beliebige Attributreihenfolge.
#    2. DETEKTOR-FRISCHE: Vor jeder Prüfung wird der Fingerabdruck im
#       LIVE-TEMPLATE geprüft (`data-ff-offenlegung` in
#       layouts/_partials/ff_offenlegung.html). Fehlt er, ist das ein
#       WERKZEUGFEHLER (Exit 2) – nicht „alles in Ordnung".
#    3. FAIL-CLOSED: Kein public/, keine Seiten, kein Register →
#       Exit 2. Unbewiesen ist nicht bewiesen.
#
#  GEPRÜFTE VERTRÄGE
#    O1 KENNZEICHNUNG  Jede Inhaltsseite trägt genau eine Offenlegung
#                      im Kopf (posts/*, pillar/*, /pillar/).
#    O2 REIHENFOLGE    Die Offenlegung steht VOR dem ersten /go/-Link
#                      (Dokumentposition, nicht Absicht).
#    O3 ARTIKELGENAU   Angegebene Zahl = gezählte Links; angegebene
#                      Ziele = verlinkte Ziele; angegebene Partner =
#                      Partner dieser Ziele laut Register
#                      (data/affiliate_ziele.yaml).
#    O4 PFLICHTANGABEN Sichtbarer Text nennt Werbung, Anzahl,
#                      Provision und „kein Aufpreis/keine Mehrkosten"
#                      und verlinkt /transparenz/.
#    O5 SICHTBARKEIT   Nicht versteckt (hidden, aria-hidden,
#                      display:none, visibility:hidden, font-size:0),
#                      und die Klasse ist im ausgelieferten CSS
#                      gestaltet.
#    O6 GEGENPROBE     Seiten OHNE Partnerlinks tragen die sichtbare
#                      Aussage „keine Partnerlinks"; der Abbinder in
#                      der Trust-Box widerspricht dem Kopf nie.
#    O7 REGISTER       /transparenz/ existiert, ist von jeder Seite
#                      verlinkt und führt JEDEN Partner und JEDEN
#                      Produktbereich des Zielregisters auf. Kein
#                      beworbener Partner darf dort fehlen.
#
#  NUTZUNG
#    python3 scripts/offenlegung_gate.py              # prüfen (public/)
#    python3 scripts/offenlegung_gate.py --json       # maschinenlesbar
#    python3 scripts/offenlegung_gate.py --selftest   # Wache prüft sich
#    python3 scripts/offenlegung_gate.py --public dir # anderer Build
#    python3 scripts/offenlegung_gate.py --seite posts/slug  # eine Seite
#
#  Voraussetzung für einen echten Lauf: ein Build (`hugo --minify`).
#  Diese Wache HEILT NICHT (C15: Beweisen ist nicht Heilen) – die
#  Kennzeichnung selbst erzeugt das Template automatisch aus den
#  gerenderten Links; hier wird nur bewiesen, dass sie stimmt.
#
#  EXIT: 0 grün · 1 Vertrag verletzt · 2 Werkzeug-/Selbsttestfehler
# ============================================================
from __future__ import annotations

import argparse
import datetime
import html as html_mod
import json
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC = os.path.join(BLOG_DIR, "public")
REGISTER = os.path.join(BLOG_DIR, "data", "affiliate_ziele.yaml")
TEMPLATE = os.path.join(BLOG_DIR, "layouts", "_partials", "ff_offenlegung.html")
SSOT = os.path.join(BLOG_DIR, "layouts", "_partials", "_funcs", "affiliate_offenlegung.html")
CSS_PFAD = os.path.join(BLOG_DIR, "assets", "css", "extended", "z-premium-blog.css")
REPORT = os.path.join(BLOG_DIR, "OFFENLEGUNG-REPORT.md")
STATE = os.path.join(BLOG_DIR, ".offenlegung_state.json")
HISTORY = os.path.join(BLOG_DIR, "data", "offenlegung_history.jsonl")

CHANNEL = "affiliate"
TRANSPARENZ_PFAD = "/transparenz/"

# Pflichtbausteine im sichtbaren Text (klein geschrieben geprüft).
PFLICHT_MIT = (
    ("werbung", "Werbekennzeichnung (§ 5a UWG / Google-Richtlinie)"),
    ("partnerlink", "Benennung der Partnerlinks"),
    ("provision", "Vergütungsmodell"),
)
PFLICHT_OHNE = (
    ("keine partnerlink", "Gegenprobe: Artikel ohne Werbung sagt das auch"),
)
KOSTEN_VARIANTEN = ("ohne aufpreis", "keine mehrkosten", "kein aufpreis", "keinen aufpreis")


# ------------------------------------------------------------ Befunde

def befund(code, seite, text, schritt, severity="P2", owner="auto"):
    """Ein Befund im Format des Alarm-Routings (C14: Besitz + Schließpfad)."""
    return {
        "id": f"offenlegung-{code.lower()}",
        "vertrag": code,
        "title": f"Offenlegung {code}",
        "seite": seite,
        "detail": text,
        "step": schritt,
        "severity": severity,
        "owner": owner,
        "channel": CHANNEL,
    }


# ------------------------------------------------------------ Parser

_TAG_RE = re.compile(r"<[^>]+>")
_ATTR_RE = re.compile(r"""([a-zA-Z0-9_:\-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'<>`]+))""")
# Anführungszeichen sind optional: `hugo --minify` entfernt sie, wo HTML das erlaubt.
_MARKER_RE = re.compile(r"""data-ff-offenlegung\s*=\s*(?:"|')?(mit-partnerlinks|ohne-partnerlinks)""")
_ABBINDER_RE = re.compile(
    r"""data-ff-offenlegung-abbinder\s*=\s*(?:"|')?(mit-partnerlinks|ohne-partnerlinks)""")
_GO_RE = re.compile(r"""href\s*=\s*(?:"|')?/go/([a-z0-9][a-z0-9\-]*)""")


def text_von(fragment: str) -> str:
    """Sichtbarer Text eines HTML-Fragments – Tags raus, Entities auf."""
    ohne = _TAG_RE.sub(" ", fragment)
    return re.sub(r"\s+", " ", html_mod.unescape(ohne)).strip()


def attribute(tag: str) -> dict:
    out = {}
    for m in _ATTR_RE.finditer(tag):
        wert = m.group(2) or m.group(3) or m.group(4) or ""
        out[m.group(1).lower()] = wert
    return out


def _tag_um(html: str, pos: int):
    """Öffnendes Tag, in dem `pos` liegt: (start, ende_exklusiv, tagtext)."""
    start = html.rfind("<", 0, pos)
    ende = html.find(">", pos)
    if start < 0 or ende < 0:
        return None
    return start, ende + 1, html[start:ende + 1]


def _block_ab(html: str, start: int, tagname: str) -> str:
    """Grober Blockschnitt bis zum passenden Schluss-Tag (verschachtelungsfrei
    genutzt: das Bauteil enthält kein zweites <details>/<p> derselben Sorte)."""
    schluss = html.find(f"</{tagname}>", start)
    if schluss < 0:
        return html[start:start + 4000]
    return html[start:schluss + len(tagname) + 3]


def finde_links(html: str):
    """Alle Affiliate-Anker der Seite: [(position, schluessel), …]."""
    return [(m.start(), m.group(1)) for m in _GO_RE.finditer(html)]


def finde_offenlegung(html: str):
    """Die Kennzeichnung im Seitenkopf – oder None."""
    treffer = list(_MARKER_RE.finditer(html))
    if not treffer:
        return None
    m = treffer[0]
    umschlag = _tag_um(html, m.start())
    if not umschlag:
        return None
    start, ende, tag = umschlag
    attrs = attribute(tag)
    tagname = re.match(r"<\s*([a-zA-Z0-9]+)", tag)
    block = _block_ab(html, start, tagname.group(1) if tagname else "div")
    keys = [k for k in (attrs.get("data-ff-offenlegung-keys") or "").split(",") if k]
    partner = [p for p in (attrs.get("data-ff-offenlegung-partner") or "").split("|") if p]
    try:
        anzahl = int(attrs.get("data-ff-offenlegung-anzahl", "-1"))
    except ValueError:
        anzahl = -1
    return {
        "pos": start,
        "treffer": len(treffer),
        "variante": m.group(1),
        "anzahl": anzahl,
        "keys": keys,
        "partner": partner,
        "tag": tag,
        "attrs": attrs,
        "block": block,
        "text": text_von(block),
    }


def lade_register(pfad: str = REGISTER) -> dict:
    """key → {partner, produkt} aus data/affiliate_ziele.yaml.

    Ohne PyYAML (schlanke Runner) greift ein bewusst simpler Zeilenleser:
    Das Register ist generiert und deshalb formattreu – zwei Ebenen,
    feste Einrückung. Ein Formatbruch fällt als leeres Register auf und
    endet in Exit 2, nicht in grünen Nullen.
    """
    try:
        roh = open(pfad, encoding="utf-8").read()
    except OSError:
        return {}
    try:
        import yaml  # type: ignore
        daten = yaml.safe_load(roh) or {}
        ziele = daten.get("ziele") or {}
        return {k: {"partner": (v or {}).get("partner", ""),
                    "produkt": (v or {}).get("produkt", "")}
                for k, v in ziele.items()}
    except Exception:  # pragma: no cover – Fallback ohne PyYAML
        out, key = {}, None
        for zeile in roh.splitlines():
            if re.match(r"^  [a-z0-9][a-z0-9\-]*:\s*$", zeile):
                key = zeile.strip().rstrip(":")
                out[key] = {"partner": "", "produkt": ""}
            elif key and re.match(r"^    (partner|produkt):", zeile):
                feld, _, wert = zeile.strip().partition(":")
                out[key][feld] = wert.strip().strip('"')
        return out


# ------------------------------------------------------------ Prüfungen

def pruefe_seite(name: str, html: str, register: dict) -> list:
    """O1–O6 für eine gebaute Seite."""
    out = []
    links = finde_links(html)
    off = finde_offenlegung(html)

    # ---- O1 KENNZEICHNUNG -------------------------------------------------
    if off is None:
        out.append(befund(
            "O1", name,
            f"keine Werbekennzeichnung im Seitenkopf ({len(links)} Partnerlink(s) auf der Seite)",
            "layouts/_partials/ff_offenlegung.html im Seiten-Layout einhängen "
            "(Artikel: layouts/single.html, Ratgeber: layouts/pillar/*.html)",
            severity="P1" if links else "P2"))
        return out
    if off["treffer"] > 1:
        out.append(befund(
            "O1", name,
            f"{off['treffer']} Kennzeichnungen auf einer Seite – welche gilt?",
            "Partial nur EINMAL pro Seite einhängen (Kopf), nicht zusätzlich im Inhalt"))

    # ---- O5 SICHTBARKEIT --------------------------------------------------
    tag_klein = off["tag"].lower()
    versteckt = []
    if re.search(r"(^|\s)hidden(\s|=|>)", tag_klein):
        versteckt.append("hidden-Attribut")
    if 'aria-hidden="true"' in tag_klein or "aria-hidden=true" in tag_klein:
        versteckt.append('aria-hidden="true"')
    stil = (off["attrs"].get("style") or "").replace(" ", "").lower()
    for muster, wie in (("display:none", "display:none"),
                        ("visibility:hidden", "visibility:hidden"),
                        ("font-size:0", "font-size:0"),
                        ("opacity:0", "opacity:0")):
        if muster in stil:
            versteckt.append(wie)
    if versteckt:
        out.append(befund(
            "O5", name,
            "Kennzeichnung ist für Leser unsichtbar gemacht: " + ", ".join(versteckt),
            "Verstecken einer Pflichtkennzeichnung ist kein Design-, sondern ein "
            "Rechtsproblem – Attribut entfernen",
            severity="P1"))
    if "ff-offenlegung" not in (off["attrs"].get("class") or ""):
        out.append(befund(
            "O5", name,
            "Kennzeichnung ohne Klasse `ff-offenlegung` – die Gestaltung (und damit "
            "die Sichtbarkeit) hängt an dieser Klasse",
            "Klasse im Partial wiederherstellen"))

    # ---- O4 PFLICHTANGABEN ------------------------------------------------
    text = off["text"].lower()
    if off["variante"] == "mit-partnerlinks":
        for baustein, warum in PFLICHT_MIT:
            if baustein not in text:
                out.append(befund(
                    "O4", name,
                    f"sichtbarer Text ohne „{baustein}“ – fehlt: {warum}",
                    "Pflichtbaustein in layouts/_partials/ff_offenlegung.html ergänzen",
                    severity="P1"))
        if not any(v in text for v in KOSTEN_VARIANTEN):
            out.append(befund(
                "O4", name,
                "sichtbarer Text sagt nicht, dass Leser keinen Aufpreis zahlen",
                "„für dich ohne Aufpreis“ / „keine Mehrkosten“ in die Kennzeichnung",
                severity="P1"))
    else:
        for baustein, warum in PFLICHT_OHNE:
            if baustein not in text:
                out.append(befund(
                    "O4", name,
                    f"Gegenprobe ohne „{baustein}“ – fehlt: {warum}",
                    "Werbefrei-Zweig in layouts/_partials/ff_offenlegung.html prüfen"))
    if TRANSPARENZ_PFAD not in off["block"]:
        out.append(befund(
            "O4", name,
            "Kennzeichnung verlinkt /transparenz/ nicht – der Leser kommt nicht "
            "von der Kennzeichnung zur vollständigen Offenlegung",
            "Link auf /transparenz/ in das Bauteil aufnehmen"))

    # ---- O2 REIHENFOLGE ---------------------------------------------------
    if links and off["pos"] > links[0][0]:
        out.append(befund(
            "O2", name,
            f"Kennzeichnung steht erst nach dem ersten Partnerlink "
            f"(Position {off['pos']} > {links[0][0]}, Ziel /go/{links[0][1]}/)",
            "Bauteil in den Seitenkopf verschieben – vor Inhalt, Kurzantwort und Cover",
            severity="P1"))

    # ---- O3 ARTIKELGENAU --------------------------------------------------
    gezaehlt = len(links)
    if off["anzahl"] != gezaehlt:
        out.append(befund(
            "O3", name,
            f"Kennzeichnung nennt {off['anzahl']} Partnerlink(s), gebaut sind {gezaehlt}",
            "Zähler im SSOT layouts/_partials/_funcs/affiliate_offenlegung.html prüfen "
            "(Layout-CTAs außerhalb von .Content brauchen `extraKeys`)",
            severity="P1"))
    ist_keys = sorted({k for _, k in links})
    soll_keys = sorted(set(off["keys"]))
    if ist_keys != soll_keys:
        fehlt = sorted(set(ist_keys) - set(soll_keys))
        zuviel = sorted(set(soll_keys) - set(ist_keys))
        out.append(befund(
            "O3", name,
            "Ziele der Kennzeichnung weichen von den verlinkten Zielen ab"
            + (f" · nicht offengelegt: {', '.join(fehlt)}" if fehlt else "")
            + (f" · offengelegt ohne Link: {', '.join(zuviel)}" if zuviel else ""),
            "SSOT prüfen – die Kennzeichnung muss aus den gerenderten Links entstehen",
            severity="P1" if fehlt else "P2"))
    unbekannt = sorted({k for k in ist_keys if k not in register})
    if unbekannt:
        out.append(befund(
            "O3", name,
            "beworbene Ziele fehlen im Register data/affiliate_ziele.yaml: "
            + ", ".join(unbekannt),
            "Ziel im Intent-Kontrakt registrieren und neu backen "
            "(python3 scripts/affiliate_intent_guard.py --bake)",
            severity="P1", owner="human"))
    soll_partner = sorted({register[k]["partner"] for k in ist_keys
                           if k in register and register[k]["partner"]})
    ist_partner = sorted(set(off["partner"]))
    if soll_partner and ist_partner != soll_partner:
        out.append(befund(
            "O3", name,
            f"genannte Partner {ist_partner or '—'} ≠ tatsächlich verlinkte Partner {soll_partner}",
            "Partnernamen kommen aus dem Register – Zuordnung im SSOT prüfen",
            severity="P1"))
    for p in ist_partner:
        if p and p not in off["text"]:
            out.append(befund(
                "O3", name,
                f"Partner „{p}“ steht nur im Datenattribut, nicht im sichtbaren Text",
                "Partnernamen sichtbar ausgeben – Attribute liest kein Leser",
                severity="P1"))

    # ---- O6 GEGENPROBE / ABBINDER ----------------------------------------
    if gezaehlt == 0 and off["variante"] != "ohne-partnerlinks":
        out.append(befund(
            "O6", name,
            "Seite ohne Partnerlinks trägt trotzdem eine Werbekennzeichnung – "
            "die Unterscheidung verliert damit ihren Wert",
            "Werbefrei-Zweig prüfen (SSOT liefert hat=false)"))
    if gezaehlt > 0 and off["variante"] != "mit-partnerlinks":
        out.append(befund(
            "O6", name,
            f"Seite mit {gezaehlt} Partnerlink(s) ist als werbefrei gekennzeichnet",
            "SSOT prüfen – die Zählung muss die gerenderten Links sehen",
            severity="P1"))
    abbinder = _ABBINDER_RE.search(html)
    if abbinder and abbinder.group(1) != off["variante"]:
        out.append(befund(
            "O6", name,
            f"Abbinder in der Trust-Box sagt „{abbinder.group(1)}“, der Kopf sagt "
            f"„{off['variante']}“ – zwei Aussagen auf einer Seite",
            "Beide Stellen speisen sich aus _funcs/affiliate_offenlegung.html – Drift prüfen",
            severity="P1"))

    # ---- O7 (seitenweiter Teil): Weg zur Offenlegung ----------------------
    if TRANSPARENZ_PFAD not in html:
        out.append(befund(
            "O7", name,
            "Seite verlinkt /transparenz/ nirgends (auch nicht im Fuß)",
            "Footer-Link in layouts/_partials/footer.html wiederherstellen"))
    return out


def pruefe_transparenzseite(html: str, register: dict, partner_live: set) -> list:
    """O7: Das Register ist vollständig offengelegt – ohne Lücke, ohne Verzug."""
    out = []
    text = text_von(html)
    fehlende_partner = sorted({v["partner"] for v in register.values()
                               if v["partner"] and v["partner"] not in text})
    if fehlende_partner:
        out.append(befund(
            "O7", "transparenz/",
            "Partner aus dem Zielregister fehlen auf der Offenlegungsseite: "
            + ", ".join(fehlende_partner),
            "Shortcode `partnerliste` erzeugt die Liste aus data/affiliate_ziele.yaml – "
            "Shortcode-Aufruf auf /transparenz/ prüfen",
            severity="P1", owner="human"))
    fehlende_produkte = sorted({v["produkt"] for v in register.values()
                                if v["produkt"] and v["produkt"] not in text})
    if fehlende_produkte:
        out.append(befund(
            "O7", "transparenz/",
            "Produktbereiche ohne Offenlegung: " + ", ".join(fehlende_produkte),
            "Partnerliste neu erzeugen lassen (Build) bzw. Register prüfen",
            owner="human"))
    nur_live = sorted({p for p in partner_live if p and p not in text})
    if nur_live:
        out.append(befund(
            "O7", "transparenz/",
            "auf Artikelseiten beworbene Partner fehlen auf /transparenz/: "
            + ", ".join(nur_live),
            "Kein Partner darf beworben werden, ohne offengelegt zu sein",
            severity="P1", owner="human"))
    for pflicht, warum in (("provision", "Vergütungsmodell"),
                           ("werbung", "Kennzeichnungspraxis"),
                           ("unabhängig", "Grenzen des Einflusses")):
        if pflicht not in text.lower():
            out.append(befund(
                "O7", "transparenz/",
                f"Offenlegungsseite ohne Abschnitt zu „{pflicht}“ ({warum})",
                "Seite content/transparenz/index.md vervollständigen",
                owner="human"))
    return out


def pruefe_werkzeug() -> list:
    """Detektor-Frische: Wächter, Template und CSS müssen zusammenpassen.

    Rückgabe sind WERKZEUGFEHLER (Exit 2), keine Inhaltsbefunde: Wenn der
    Fingerabdruck fehlt, weiß die Wache nicht mehr, wonach sie sucht – und
    genau dann darf sie nicht grün melden (Lehre aus AI4).
    """
    fehler = []
    try:
        tpl = open(TEMPLATE, encoding="utf-8").read()
    except OSError as exc:
        return [f"Template nicht lesbar: {exc}"]
    if "data-ff-offenlegung" not in tpl:
        fehler.append(f"{os.path.relpath(TEMPLATE, BLOG_DIR)}: Fingerabdruck "
                      "`data-ff-offenlegung` fehlt – Detektor veraltet")
    if "mit-partnerlinks" not in tpl or "ohne-partnerlinks" not in tpl:
        fehler.append(f"{os.path.relpath(TEMPLATE, BLOG_DIR)}: die beiden Varianten "
                      "(mit/ohne Partnerlinks) sind nicht mehr beide vorhanden")
    if not os.path.exists(SSOT):
        fehler.append("layouts/_partials/_funcs/affiliate_offenlegung.html fehlt – "
                      "ohne SSOT entstehen zwei Wahrheiten")
    try:
        css = open(CSS_PFAD, encoding="utf-8").read()
    except OSError as exc:
        fehler.append(f"CSS nicht lesbar: {exc}")
    else:
        if ".ff-offenlegung" not in css:
            fehler.append("z-premium-blog.css: `.ff-offenlegung` ist nicht gestaltet – "
                          "eine ungestaltete Kennzeichnung ist eine unsichtbare")
    if not lade_register():
        fehler.append("data/affiliate_ziele.yaml: kein Ziel gelesen – Registerformat geändert?")
    return fehler


# ------------------------------------------------------------ Lauf

def seiten_des_builds(public: str, nur: str = ""):
    """Alle geprüften Inhaltsseiten: (name, html).

    Umfang = Seiten, die redaktionelle Inhalte und Partnerlinks tragen:
    posts/*, pillar/* und die Ratgeber-Zentrale /pillar/. Paginierung
    (posts/page/2/) und Weiterleitungs-Stümpfe (/go/) bleiben außen vor –
    sie tragen keinen Artikeltext.
    """
    ziele = []
    for bereich in ("posts", "pillar"):
        wurzel = os.path.join(public, bereich)
        if not os.path.isdir(wurzel):
            continue
        index = os.path.join(wurzel, "index.html")
        if bereich == "pillar" and os.path.exists(index):
            ziele.append((f"{bereich}/", index))
        for eintrag in sorted(os.listdir(wurzel)):
            if eintrag in ("page", "index.html"):
                continue
            pfad = os.path.join(wurzel, eintrag, "index.html")
            if os.path.exists(pfad):
                ziele.append((f"{bereich}/{eintrag}/", pfad))
    out = []
    for name, pfad in ziele:
        if nur and nur.strip("/") not in name.strip("/"):
            continue
        try:
            roh = open(pfad, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        # Alias-/Weiterleitungsseiten haben keinen Artikelinhalt.
        if 'http-equiv="refresh"' in roh or "http-equiv=refresh" in roh:
            continue
        out.append((name, roh))
    return out


def lauf(public: str = PUBLIC, nur: str = "") -> dict:
    register = lade_register()
    seiten = seiten_des_builds(public, nur)
    befunde, partner_live = [], set()
    mit_links = 0
    for name, roh in seiten:
        befunde.extend(pruefe_seite(name, roh, register))
        off = finde_offenlegung(roh)
        if off:
            partner_live.update(off["partner"])
            if off["variante"] == "mit-partnerlinks":
                mit_links += 1

    transparenz = os.path.join(public, "transparenz", "index.html")
    if not os.path.exists(transparenz):
        befunde.append(befund(
            "O7", "transparenz/",
            "Offenlegungsseite /transparenz/ fehlt im Build – jede Kennzeichnung "
            "verlinkt damit ins Leere",
            "content/transparenz/index.md anlegen bzw. Build prüfen",
            severity="P1", owner="human"))
    else:
        befunde.extend(pruefe_transparenzseite(
            open(transparenz, encoding="utf-8", errors="ignore").read(),
            register, partner_live))

    return {
        "zeit": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "seiten": len(seiten),
        "seiten_mit_partnerlinks": mit_links,
        "ziele_registriert": len(register),
        "befunde": befunde,
        "grün": not befunde,
    }


def schreibe_report(ergebnis: dict) -> None:
    zeilen = [
        "# Offenlegungs-Report (artikelgenaue Werbekennzeichnung)",
        "",
        f"- Stand: {ergebnis['zeit']}",
        f"- Geprüfte Seiten: {ergebnis['seiten']}",
        f"- Davon mit Partnerlinks: {ergebnis['seiten_mit_partnerlinks']}",
        f"- Registrierte Ziele: {ergebnis['ziele_registriert']}",
        f"- Ergebnis: {'✅ O1–O7 erfüllt' if ergebnis['grün'] else '🛑 ' + str(len(ergebnis['befunde'])) + ' Befund(e)'}",
        "",
        "Erzeugt von `scripts/offenlegung_gate.py` (Verträge O1–O7, Herleitung im Dateikopf).",
        "",
    ]
    if ergebnis["befunde"]:
        zeilen += ["## Befunde", "", "| Vertrag | Seite | Befund | Nächster Schritt |", "|---|---|---|---|"]
        for b in ergebnis["befunde"]:
            zeilen.append(f"| {b['vertrag']} | `{b['seite']}` | {b['detail']} | {b['step']} |")
        zeilen.append("")
    else:
        zeilen += [
            "## Was damit bewiesen ist",
            "",
            "- Jede Inhaltsseite trägt ihre Kennzeichnung **vor** dem ersten Partnerlink (O1/O2).",
            "- Zahl, Ziele und Partner der Kennzeichnung entsprechen den gebauten Links (O3).",
            "- Pflichtangaben (Werbung, Provision, kein Aufpreis, Weg zur Offenlegung) stehen sichtbar (O4/O5).",
            "- Seiten ohne Partnerlinks sagen das ebenfalls – die Kennzeichnung bleibt unterscheidbar (O6).",
            "- Kein beworbener Partner fehlt auf `/transparenz/` (O7).",
            "",
        ]
    with open(REPORT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(zeilen))


def schreibe_zustand(ergebnis: dict) -> None:
    zustand = {
        "zeit": ergebnis["zeit"],
        "seiten": ergebnis["seiten"],
        "seiten_mit_partnerlinks": ergebnis["seiten_mit_partnerlinks"],
        "befunde": len(ergebnis["befunde"]),
        "grün": ergebnis["grün"],
    }
    with open(STATE, "w", encoding="utf-8") as fh:
        json.dump(zustand, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    try:
        os.makedirs(os.path.dirname(HISTORY), exist_ok=True)
        with open(HISTORY, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(zustand, ensure_ascii=False) + "\n")
    except OSError:
        pass


# ------------------------------------------------------------ Selbsttest

_KOPF = ('<p class="ff-pruef">Prüfzeile</p>'
         '<details class="ff-offenlegung" data-ff-offenlegung="mit-partnerlinks" '
         'data-ff-offenlegung-anzahl="{n}" data-ff-offenlegung-keys="{keys}" '
         'data-ff-offenlegung-partner="{partner}">'
         '<summary class="ff-offenlegung__kopf"><span class="ff-offenlegung__chip">Werbung</span>'
         '<span class="ff-offenlegung__satz"><strong>{n} Partnerlinks</strong> in diesem Artikel: '
         '{sichtbar}. Provision nur bei Abschluss, für dich ohne Aufpreis.</span></summary>'
         '<div class="ff-offenlegung__text"><a href="/transparenz/">Wie sich das finanziert</a>'
         '</div></details>')
_LINK = '<a href="/go/{key}/?subid=test" rel="sponsored nofollow noopener">Jetzt vergleichen</a>'
_FUSS = '<footer><a href="/transparenz/">Transparenz &amp; Werbung</a></footer>'


def _seite_mit(n=2, keys="strom,gas", partner="CHECK24", sichtbar="CHECK24 (Stromtarife, Gastarife)",
               links=("strom", "gas"), kopf=None, fuss=True):
    kopf = kopf if kopf is not None else _KOPF.format(n=n, keys=keys, partner=partner,
                                                      sichtbar=sichtbar)
    return ("<html><body>" + kopf + "".join(_LINK.format(key=k) for k in links)
            + (_FUSS if fuss else "") + "</body></html>")


def _seite_ohne():
    return ('<html><body><p class="ff-offenlegung ff-offenlegung--frei" '
            'data-ff-offenlegung="ohne-partnerlinks" data-ff-offenlegung-anzahl="0" '
            'data-ff-offenlegung-keys="" data-ff-offenlegung-partner="">'
            '<span class="ff-offenlegung__chip ff-offenlegung__chip--frei">Werbefrei</span>'
            '<span class="ff-offenlegung__satz"><strong>Keine Partnerlinks</strong> in diesem '
            'Artikel – an diesem Text verdient FranksFinanzcheck nichts.</span>'
            '<a class="ff-offenlegung__link" href="/transparenz/">Wie wir uns finanzieren</a>'
            '</p>' + _FUSS + '</body></html>')


def selftest() -> int:
    """Die Wache muss Verstöße ERKENNEN – jeder Fall einzeln belegt."""
    register = {"strom": {"partner": "CHECK24", "produkt": "Stromtarife"},
                "gas": {"partner": "CHECK24", "produkt": "Gastarife"},
                "tagesgeld": {"partner": "C24 Bank", "produkt": "Tagesgeld der C24 Bank"}}
    fehler = []

    def codes(html, name="posts/probe/"):
        return {b["vertrag"] for b in pruefe_seite(name, html, register)}

    # ST0 – die gesunden Fälle müssen still bleiben.
    if codes(_seite_mit()):
        fehler.append("ST0: saubere Seite mit Partnerlinks erzeugt Befunde "
                      f"({sorted(codes(_seite_mit()))})")
    if codes(_seite_ohne()):
        fehler.append("ST0: saubere werbefreie Seite erzeugt Befunde "
                      f"({sorted(codes(_seite_ohne()))})")

    # ST1 – minifizierte Ausgabe (ohne Anführungszeichen) muss gleich gelten.
    mini = _seite_mit().replace('href="/go/strom/?subid=test"', "href=/go/strom/?subid=test")
    mini = mini.replace('data-ff-offenlegung="mit-partnerlinks"',
                        "data-ff-offenlegung=mit-partnerlinks")
    if codes(mini):
        fehler.append(f"ST1: minifizierte Seite fälschlich beanstandet ({sorted(codes(mini))})")

    # ST2 – jede Sabotage muss genau ihren Vertrag auslösen.
    proben = [
        ("O1", _seite_mit(kopf="")),
        ("O2", "<html><body>" + _LINK.format(key="strom") + _LINK.format(key="gas")
               + _KOPF.format(n=2, keys="strom,gas", partner="CHECK24",
                              sichtbar="CHECK24 (Stromtarife, Gastarife)") + _FUSS + "</body></html>"),
        ("O3", _seite_mit(n=5)),                                  # falsche Zahl
        ("O3", _seite_mit(keys="strom")),                         # verschwiegenes Ziel
        ("O3", _seite_mit(partner="Tarifcheck", sichtbar="Tarifcheck (Hausrat)")),  # falscher Partner
        ("O3", _seite_mit(keys="strom,unbekannt", links=("strom", "unbekannt"),
                          sichtbar="CHECK24 (Stromtarife)")),     # Ziel ohne Register
        ("O4", _seite_mit().replace("Provision nur bei Abschluss, für dich ohne Aufpreis.", "")),
        ("O4", _seite_mit().replace('<a href="/transparenz/">Wie sich das finanziert</a>', "")
                           .replace(_FUSS, _FUSS.replace("/transparenz/", "/impressum/"))),
        ("O5", _seite_mit().replace('class="ff-offenlegung" data-ff-offenlegung=',
                                    'class="ff-offenlegung" hidden data-ff-offenlegung=')),
        ("O5", _seite_mit().replace('class="ff-offenlegung" data-ff-offenlegung=',
                                    'class="ff-offenlegung" style="display:none" data-ff-offenlegung=')),
        ("O6", _seite_ohne().replace("</body>", _LINK.format(key="strom") + "</body>")),
        ("O6", _seite_mit() + '<p data-ff-offenlegung-abbinder="ohne-partnerlinks">Abbinder</p>'),
        ("O7", _seite_mit(fuss=False).replace('<a href="/transparenz/">Wie sich das finanziert</a>',
                                              "Details")),
    ]
    for vertrag, html in proben:
        gefunden = codes(html)
        if vertrag not in gefunden:
            fehler.append(f"ST2-{vertrag}: Sabotage blieb unentdeckt (gefunden: {sorted(gefunden)})")

    # ST3 – Offenlegungsseite: fehlender Partner muss auffallen.
    seite_ok = ("<html><body>CHECK24 Stromtarife Gastarife C24 Bank Tagesgeld der C24 Bank "
                "Provision Werbung unabhängig</body></html>")
    if pruefe_transparenzseite(seite_ok, register, {"CHECK24"}):
        fehler.append("ST3: vollständige Offenlegungsseite wurde beanstandet")
    luecke = seite_ok.replace("C24 Bank Tagesgeld der C24 Bank ", "")
    if "O7" not in {b["vertrag"] for b in pruefe_transparenzseite(luecke, register, {"C24 Bank"})}:
        fehler.append("ST3: fehlender Partner auf /transparenz/ blieb unentdeckt")

    # ST4 – Detektor-Frische: der Fingerabdruck muss im echten Template stehen.
    werkzeug = pruefe_werkzeug()
    if werkzeug:
        fehler.append("ST4: Detektor/Bauteil passen nicht zusammen: " + "; ".join(werkzeug))

    if fehler:
        print("🛑 Selbsttest Offenlegungs-Wache rot:")
        for f in fehler:
            print("   -", f)
        return 2
    print(f"✅ Selbsttest Offenlegungs-Wache: {len(proben)} Sabotage-Proben erkannt, "
          "gesunde Fälle still, Detektor frisch.")
    return 0


# ------------------------------------------------------------ CLI

def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Artikelgenaue Werbekennzeichnung im gebauten HTML beweisen (O1–O7)")
    p.add_argument("--public", default=PUBLIC, help="Build-Verzeichnis (Default: public/)")
    p.add_argument("--seite", default="", help="nur Seiten, deren Pfad diesen Text enthält")
    p.add_argument("--json", action="store_true", help="Befunde maschinenlesbar")
    p.add_argument("--selftest", action="store_true", help="Wache prüft sich selbst (Trockenlauf)")
    p.add_argument("--no-report", action="store_true", help="Report/Zustand nicht schreiben")
    args = p.parse_args(argv)

    if args.selftest:
        return selftest()

    werkzeug = pruefe_werkzeug()
    if werkzeug:
        print("🛑 Werkzeugfehler – die Wache kann nicht beweisen, also meldet sie nicht grün:",
              file=sys.stderr)
        for f in werkzeug:
            print("   -", f, file=sys.stderr)
        return 2

    if not os.path.isdir(args.public):
        print(f"🛑 Kein Build unter {args.public} – erst `hugo --minify` laufen lassen.",
              file=sys.stderr)
        return 2

    ergebnis = lauf(args.public, args.seite)
    if ergebnis["seiten"] == 0:
        print(f"🛑 Keine Inhaltsseiten in {args.public} gefunden – Build unvollständig?",
              file=sys.stderr)
        return 2

    if not args.no_report and not args.seite:
        schreibe_report(ergebnis)
        schreibe_zustand(ergebnis)

    if args.json:
        print(json.dumps(ergebnis, ensure_ascii=False, indent=2))
        return 1 if ergebnis["befunde"] else 0

    if ergebnis["grün"]:
        print(f"✅ Offenlegung O1–O7 erfüllt · {ergebnis['seiten']} Seiten geprüft, "
              f"{ergebnis['seiten_mit_partnerlinks']} mit Partnerlinks, "
              f"{ergebnis['ziele_registriert']} Ziele offengelegt.")
        return 0

    print(f"🛑 Offenlegung: {len(ergebnis['befunde'])} Befund(e) auf {ergebnis['seiten']} Seiten")
    for b in ergebnis["befunde"]:
        print(f"   [{b['vertrag']} · {b['severity']}] {b['seite']}: {b['detail']}")
        print(f"        → {b['step']}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
