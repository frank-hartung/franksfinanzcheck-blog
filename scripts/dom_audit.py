#!/usr/bin/env python3
"""dom_audit.py – DOM-/Layout-Budget der gebauten Website (statisch, ohne Browser).

WARUM (Issue #338, 21.09.2026 – Layout-Automatisierung meldete Probleme)
-----------------------------------------------------------------------
Der Browser-Audit (`layout_browser_check.js`, Puppeteer) maß die DOM-Größe
nur auf VIER Seiten (Startseite + 3 neueste Artikel). Zwei Fehlerklassen
blieben dadurch unsichtbar bzw. wurden falsch bewertet:

  1. Die *Tag-Übersicht* `/tags/` trug ein einziges `<ul class="terms-tags">`
     mit 136 direkten Kindern (681 Elemente) – Lighthouse warnt ab 60 Kindern.
     Kein Lauf hat die Seite je geprüft, weil sie nie im Sample lag.
  2. Artikel-Seiten tragen 48–60 Kinder allein im `<head>`. Der Audit warnte
     ab 58 Kindern und traf damit dauerhaft die Artikel-Seiten statt einer
     Regression – eine Wache, die nur Fehlalarme liefert, wird abgeschaltet
     oder ignoriert (genau das war Issue #338).

Diese Datei ist die Antwort darauf: eine **vollständige**, browser-treue
DOM-Vermessung des gebauten Stands – für JEDE Seite, ohne Chrome, ohne Netz
(nur Standardbibliothek). Sie läuft damit auch dann, wenn der Browser-Download
im CI scheitert (der Puppeteer-Schritt ist bewusst weich).

Browser-Treue (kein Wunschdenken, sondern Vertrag)
--------------------------------------------------
Gemessen wird derselbe Baum, den ein Browser mit aktivem JavaScript aufbaut
(Referenz `document.querySelectorAll('*')`; Element-/Tiefen-/Kindmaße wie in
Lighthouse „Avoid an excessive DOM size"):
  · Void-Elemente (meta, link, img, br, hr, input, source, …) haben keine Kinder.
  · Optionale End-Tags werden wie im HTML5-Parser automatisch geschlossen
    (`<li>`, `<p>`, `<td>`, `<tr>`, `<option>`, `<dt>/<dd>` …) – nötig, weil
    `hugo --minify` End-Tags weglässt und das der AUSGELIEFERTE Stand ist.
  · `<table>` bekommt bei direkt folgendem `<tr>` ein implizites `<tbody>`
    (erzeugt wie der Browser ein zusätzliches Element).
  · In Fremd-Inhalt (`<svg>`, `<math>`) schließt `/>` das Element sofort.
  · `<script>`, `<style>`, `<textarea>`, `<title>` sind Rohtext – und
    `<noscript>` ebenfalls: mit aktivem JavaScript sieht der Browser dort
    KEINE Elemente (genau der Unterschied, der Zählungen sonst verschiebt).
  · `<template>`-Inhalt ist ein eigenes Dokument-Fragment und gehört wie im
    Browser NICHT zum Messbaum.
  · Kommentare, `<!DOCTYPE>` und `<?…?>` erzeugen keine Elemente.

Beleg statt Behauptung: `--selftest` (8 eingefrorene Parser-Fälle + Budget-Logik)
und der Browser-Audit (`layout_browser_check.js`) vergleicht seine echten
Browser-Messwerte mit diesen Zahlen – Abweichung = Parser-Drift = Warnung.

Budgets
-------
Zwei Stufen, eine Wahrheit: `LIMIT` = Lighthouse-Messgrenze (die Grenze des
Messwerkzeugs, nicht unsere Meinung), `BUDGET` = Frühwarnung deutlich darunter –
und so gewählt, dass sie mit Abstand erreichbar ist (sonst entsteht wieder ein
Dauer-Alarm wie in #338).

  Metrik            Frühwarnung   Lighthouse-Grenze
  Kinder/Element    54            60
  Kinder im <head>  52            58
  Tiefe             28            32
  Elemente gesamt   1100          1400

Zwei Messbereiche (Lehre aus dem ersten PR-Gate-Lauf, 21.09.2026)
---------------------------------------------------------------
Dieses Werkzeug vermisst die AUSGELIEFERTE HTML – jede Seite, ohne Browser.
Der Browser sieht zur Laufzeit mehr: `static/premium/ff-premium.js` baut eine
Mini-Inhaltsübersicht, Anker-Buttons und die Lese-Fortschrittsleiste, die
Lesehilfen kommen dazu. Das ist eine Funktion, kein Fehler – gemessen auf der
schwersten Artikelseite: 968 Elemente ausgeliefert, 1109 zur Laufzeit (+141,
und der Zuwachs wächst mit der Artikel-Länge).

Deshalb gibt es zwei Budgets mit klarer Zuständigkeit:
  · `BUDGET`/`LIMIT` (oben) = ausgelieferte HTML, gilt für JEDE Seite.
  · `BUDGET_RUNTIME` = Laufzeit-DOM der Site (Frühwarnung 1350 Elemente):
    Kopf/Tiefe wachsen durch die Erweiterung nachweislich nicht, nur die
    Elementzahl – und zwar um den nachgemessenen Puffer (1109 + Reserve).
    Die harte Grenze bleibt die Lighthouse-Grenze (1400); die billigt auch
    Lighthouse dem Laufzeit-DOM zu. Ein eigener Kopf-/Tiefenwert wäre eine
    erfundene Zahl – deshalb steht dort derselbe Wert wie statisch.

Der Browser-Audit liest beide Sätze aus dem JSON dieses Werkzeugs (keine
zweite Zahlenkopie) und vergleicht seinen Parser-Gegenwert mit der
Skript-freien Messung – nicht mit der Laufzeitmessung. Sonst meldet jede
Erweiterung „Drift" und die Prüfung wird wertlos.

Exit: 0 = alles im Budget · 1 = Lighthouse-Grenze gerissen (kritisch)
      · 2 = Ausführungsfehler. Frühwarnungen allein sind Exit 0: sie stehen im
      Report, ein Issue entsteht nur an der gerissenen Grenze.

Aufruf:
  python3 scripts/dom_audit.py                     # public/ vermessen
  python3 scripts/dom_audit.py --json .cache/layout/dom-audit.json
  python3 scripts/dom_audit.py --top 15            # größte Seiten zeigen
  python3 scripts/dom_audit.py --selftest
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_BASE = os.path.join(BLOG_DIR, "public")

# ---------------------------------------------------------------
# Budgets (eine Wahrheit für alle Werkzeuge)
# ---------------------------------------------------------------
BUDGET = {
    "children": 54,          # Kinder EINES Elements
    "head_children": 52,     # Kinder von <head> (rein template-gesteuert)
    "depth": 28,
    "elements": 1100,
}
LIMIT = {
    "children": 60,
    "head_children": 58,
    "depth": 32,
    "elements": 1400,
}
# Laufzeit-DOM (nur der Browser kann das messen): Kopf/Tiefe/Kinder bleiben,
# die Erweiterungsschicht (Premium-Mini-TOC, Anker, Lesehilfen) wächst mit der
# Artikel-Länge. Nachgemessen 21.09.2026: ausgeliefert max. 968 → Laufzeit
# max. 1109 Elemente. Die Frühwarnung liegt darüber, aber weiterhin deutlich
# unter der Lighthouse-Grenze (1400) – sonst wäre sie ein Dauer-Alarm.
BUDGET_RUNTIME = {
    "children": 54,
    "head_children": 52,
    "depth": 28,
    "elements": 1350,
}

# ---------------------------------------------------------------
# HTML5-Teilmenge, die für die Vermessung gebraucht wird
# ---------------------------------------------------------------
VOID = frozenset((
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr", "basefont", "bgsound",
    "frame", "keygen", "image",
))
RAW_TEXT = frozenset(("script", "style", "textarea", "title", "plaintext"))
# Mit aktivem JavaScript ist <noscript> für den Parser Rohtext (der Inhalt wird
# NICHT zu Elementen) – exakt das Verhalten des Browsers.
RAW_TEXT_ALWAYS = frozenset(("noscript",))
FOREIGN = frozenset(("svg", "math"))

# Optional-Endtag-Regeln: Start-Tag X schließt offene Elemente dieser Menge.
AUTOCLOSE: dict[str, frozenset[str]] = {
    "li": frozenset(("li",)),
    "dt": frozenset(("dt", "dd")),
    "dd": frozenset(("dt", "dd")),
    "tr": frozenset(("tr", "td", "th")),
    "td": frozenset(("td", "th")),
    "th": frozenset(("td", "th")),
    "option": frozenset(("option",)),
    "optgroup": frozenset(("option", "optgroup")),
    "thead": frozenset(("tbody", "tfoot")),
    "tbody": frozenset(("tbody", "tfoot")),
    "tfoot": frozenset(("tbody",)),
    "rt": frozenset(("rt", "rp")),
    "rp": frozenset(("rt", "rp")),
    "caption": frozenset(("caption",)),
    "colgroup": frozenset(("colgroup",)),
}
# Ein offenes <p> endet am nächsten Block-Starttag (HTML5: „close a p
# element"). Ohne diese Regel würden Absätze ganze Abschnitte verschachteln –
# Elemente, die im Browser Geschwister sind, landeten hier als Kinder
# (Tiefe/Kinderzahl wären falsch, genau die Maße, um die es geht).
P_CLOSERS = frozenset((
    "address", "article", "aside", "blockquote", "details", "div", "dl",
    "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2", "h3",
    "h4", "h5", "h6", "header", "hgroup", "hr", "main", "menu", "nav", "ol",
    "p", "pre", "section", "table", "ul",
))


class Node:
    """Element-Knoten des Messbaums (Tag, id, Klassen, Kinder, Tiefe)."""

    __slots__ = ("tag", "id", "cls", "children", "depth", "implicit", "parent")

    def __init__(self, tag: str, attrs: dict[str, str], depth: int,
                 implicit: bool = False) -> None:
        self.tag = tag
        self.id = attrs.get("id", "")
        self.cls = attrs.get("class", "")
        self.children: list["Node"] = []
        self.depth = depth
        self.implicit = implicit
        self.parent: "Node | None" = None

    def add(self, child: "Node") -> None:
        child.parent = self
        self.children.append(child)


def parse_attrs(raw: str) -> dict[str, str]:
    """Attribute eines Start-Tags – mit und ohne Anführungszeichen (minify)."""
    attrs: dict[str, str] = {}
    for m in re.finditer(
            r"""([^\s=/>"']+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]*)))?""",
            raw):
        name = m.group(1).lower()
        if name in attrs:
            continue
        attrs[name] = (m.group(2) if m.group(2) is not None else
                       (m.group(3) if m.group(3) is not None else
                        (m.group(4) or "")))
    return attrs


def path_of(node: Node) -> str:
    """Stabiler, reparierbarer DOM-Pfad (gleiche Form wie im Browser-Audit)."""
    parts: list[str] = []
    cur: Node | None = node
    while cur is not None and len(parts) < 5:
        part = cur.tag
        if cur.id:
            part += "#" + cur.id
        elif cur.cls:
            part += "." + ".".join(cur.cls.split()[:2])
        parts.insert(0, part)
        cur = cur.parent
    return " > ".join(parts)


def parse_document(html: str) -> tuple[Node | None, list[Node]]:
    """Baut den Elementbaum wie ein Browser (Scripting aktiv).

    Liefert (root=<html>, nodes=alle Elemente in Dokumentordnung) – `nodes`
    entspricht der Menge von `document.querySelectorAll('*')`.
    """
    if not html:
        return None, []
    root = Node("html", {}, 0)
    nodes: list[Node] = [root]
    stack: list[Node] = [root]
    foreign_depth = 0
    head: Node | None = None
    body: Node | None = None
    # Tags, die ein Browser einem fehlenden <head> zuordnet (impliziter Kopf).
    headish = frozenset(("base", "basefont", "bgsound", "link", "meta",
                         "noframes", "script", "style", "template", "title",
                         "noscript"))
    n = len(html)
    i = 0
    while i < n:
        lt = html.find("<", i)
        if lt < 0:
            break
        i = lt
        if html.startswith("<!--", i):
            end = html.find("-->", i + 4)
            i = n if end < 0 else end + 3
            continue
        if html.startswith("<!", i) or html.startswith("<?", i):
            end = html.find(">", i)
            i = n if end < 0 else end + 1
            continue
        end = html.find(">", i)
        if end < 0:
            break
        inner = html[i + 1:end]
        i = end + 1
        if not inner:
            continue
        if inner[0] == "/":
            name = re.split(r"[\s>]", inner[1:].strip(), 1)[0].lower()
            if not name:
                continue
            for pos in range(len(stack) - 1, 0, -1):
                if stack[pos].tag == name:
                    for popped in stack[pos:]:
                        if popped.tag in FOREIGN:
                            foreign_depth -= 1
                    del stack[pos:]
                    break
            continue

        name = re.split(r"[\s/>]", inner.lstrip("/"), 1)[0].lower()
        if not name:
            continue
        attrs_raw = inner[len(name):]
        self_closing = attrs_raw.rstrip().endswith("/")
        if self_closing:
            attrs_raw = attrs_raw.rstrip()[:-1]
        in_foreign = foreign_depth > 0

        if name == "html":
            # Der Wurzelknoten ist bereits <html> – Attribute übernehmen,
            # kein zweites Element erzeugen (Browser: ein Wurzelelement).
            if attrs_raw.strip():
                attrs = parse_attrs(attrs_raw)
                root.id = attrs.get("id", "")
                root.cls = attrs.get("class", "")
            continue

        if not in_foreign:
            # implizites <head>/<body> wie im HTML5-Parser (fehlt das Tag, legt
            # der Browser die Struktur an – ohne sie stimmen die Zählungen nicht)
            if head is None and body is None and name not in ("head", "body"):
                if name in headish:
                    head = Node("head", {}, 1, implicit=True)
                    root.add(head)
                    nodes.append(head)
                    stack = [root, head]
                else:
                    body = Node("body", {}, 1, implicit=True)
                    root.add(body)
                    nodes.append(body)
                    stack = [root, body]
            # Ein offenes <colgroup> endet mit jedem anderen Starttag
            # (HTML5 „in column group": alles außer <col> schließt die Gruppe).
            if stack[-1].tag == "colgroup" and name not in ("col",):
                stack.pop()
            # implizite Tabellen-Elemente – genau wie der HTML5-Parser:
            # <tr> direkt in <table> erhält ein <tbody>, <col> ein <colgroup>
            if name == "tr" and stack[-1].tag == "table":
                tbody = Node("tbody", {}, stack[-1].depth + 1, implicit=True)
                stack[-1].add(tbody)
                nodes.append(tbody)
                stack.append(tbody)
            elif name == "col" and stack[-1].tag == "table":
                colgroup = Node("colgroup", {}, stack[-1].depth + 1,
                                implicit=True)
                stack[-1].add(colgroup)
                nodes.append(colgroup)
                stack.append(colgroup)
            if name in P_CLOSERS and stack[-1].tag == "p":
                stack.pop()
            close = AUTOCLOSE.get(name)
            if close:
                while len(stack) > 1 and stack[-1].tag in close:
                    stack.pop()

        if name == "template":
            # Das <template>-Element selbst ZÄHLT; sein Inhalt ist ein eigenes
            # Dokument-Fragment und gehört wie im Browser nicht zum Messbaum.
            node = Node(name, parse_attrs(attrs_raw), stack[-1].depth + 1)
            stack[-1].add(node)
            nodes.append(node)
            depth = 1
            while depth > 0:
                nxt = html.find("<", i)
                if nxt < 0:
                    i = n
                    break
                if html.startswith("<!--", nxt):
                    e = html.find("-->", nxt + 4)
                    i = n if e < 0 else e + 3
                    continue
                e = html.find(">", nxt)
                if e < 0:
                    i = n
                    break
                tag = html[nxt + 1:e]
                if tag.startswith("/template"):
                    depth -= 1
                elif re.match(r"template[\s/>]", tag, re.I):
                    depth += 1
                i = e + 1
            continue

        node = Node(name, parse_attrs(attrs_raw), stack[-1].depth + 1)
        stack[-1].add(node)
        nodes.append(node)
        if name == "head":
            head = node
        elif name == "body":
            body = node

        if name in RAW_TEXT or name in RAW_TEXT_ALWAYS:
            # Rohtext: bis zum passenden End-Tag überspringen (keine Elemente)
            idx = html.lower().find("</" + name, i)
            i = n if idx < 0 else idx
            continue
        if name in VOID:
            continue
        if self_closing and in_foreign:
            continue
        stack.append(node)
        if name in FOREIGN:
            foreign_depth += 1

    # Ein Browser hat IMMER <head> und <body>; fehlen sie im Markup, legt er sie an.
    if head is None:
        head = Node("head", {}, 1, implicit=True)
        head.parent = root
        root.children.insert(0, head)
        nodes.append(head)
    if body is None:
        body = Node("body", {}, 1, implicit=True)
        root.add(body)
        nodes.append(body)
    return root, nodes


class Metrics:
    """Kennzahlen einer Seite – dieselben Maße wie Lighthouse."""

    __slots__ = ("rel", "elements", "depth", "depth_path", "max_children",
                 "max_children_path", "head_children", "head_path")

    def __init__(self) -> None:
        self.rel = ""
        self.elements = 0
        self.depth = 0
        self.depth_path = ""
        self.max_children = 0
        self.max_children_path = ""
        self.head_children = 0
        self.head_path = "html > head"

    def as_dict(self) -> dict:
        return {
            "rel": self.rel,
            "elements": self.elements,
            "depth": self.depth,
            "depth_path": self.depth_path,
            "maxchildren": self.max_children,
            "maxchildren_path": self.max_children_path,
            "headchildren": self.head_children,
            "head_path": self.head_path,
        }


def measure(html: str, rel: str) -> Metrics:
    """Vermesse eine HTML-Seite wie ein Browser."""
    root, nodes = parse_document(html)
    m = Metrics()
    m.rel = rel
    m.elements = len(nodes)
    if root is None:
        return m
    max_depth, max_depth_path = 0, "html"
    max_children, max_children_path = 0, "html"
    stack = [root]
    while stack:
        node = stack.pop()
        count = len(node.children)
        if count > max_children:
            max_children, max_children_path = count, path_of(node)
        for child in node.children:
            if child.depth > max_depth:
                max_depth, max_depth_path = child.depth, path_of(child)
            stack.append(child)
    m.depth = max_depth
    m.depth_path = max_depth_path
    m.max_children = max_children
    m.max_children_path = max_children_path
    head = next((c for c in root.children if c.tag == "head"), None)
    if head is not None:
        m.head_children = len(head.children)
        m.head_path = path_of(head)
    return m


def violations(m: Metrics) -> tuple[list[str], list[str]]:
    """(kritisch, frühwarnung) – mit Ist/Soll und reparierbarem Element-Pfad."""
    crit: list[str] = []
    warn: list[str] = []
    checks = (
        ("Kinder/Elements", m.max_children, BUDGET["children"],
         LIMIT["children"], m.max_children_path),
        ("Kinder im <head>", m.head_children, BUDGET["head_children"],
         LIMIT["head_children"], m.head_path),
        ("Verschachtelungstiefe", m.depth, BUDGET["depth"], LIMIT["depth"],
         m.depth_path),
        ("Elemente gesamt", m.elements, BUDGET["elements"], LIMIT["elements"],
         m.rel),
    )
    for label, value, budget, limit, where in checks:
        if value > limit:
            crit.append(f"{label}: {value} > {limit} (Lighthouse-Grenze) – {where}")
        elif value > budget:
            warn.append(f"{label}: {value} > {budget} (Frühwarnung) – {where}")
    return crit, warn


def iter_pages(base: str):
    """Alle gebauten Seiten; Paginierung (`/page/N/`) ausgenommen: sie ist eine
    Kopie der Vorlage und würde den Report mit denselben Zahlen fluten."""
    for path in sorted(glob.glob(os.path.join(base, "**", "index.html"),
                                 recursive=True)):
        rel = os.path.relpath(path, base).replace(os.sep, "/")
        if rel.startswith("page/") or "/page/" in rel:
            continue
        yield path, "/" + rel[:-len("index.html")]


def audit_dir(base: str) -> dict:
    rows: list[dict] = []
    for path, rel in iter_pages(base):
        with open(path, encoding="utf-8", errors="ignore") as fh:
            html = fh.read()
        m = measure(html, rel)
        crit, warn = violations(m)
        row = m.as_dict()
        row["critical"] = crit
        row["warnings"] = warn
        rows.append(row)
    critical = [r for r in rows if r["critical"]]
    warnings = [r for r in rows if r["warnings"]]
    rows.sort(key=lambda r: (-r["maxchildren"], -r["elements"]))
    critical.sort(key=lambda r: (-r["maxchildren"], -r["elements"]))
    warnings.sort(key=lambda r: (-r["maxchildren"], -r["elements"]))
    return {
        "base": base,
        "budgets": {
            "fruehwarnung": BUDGET,
            "fruehwarnung_runtime": BUDGET_RUNTIME,
            "lighthouse": LIMIT,
        },
        "pages": len(rows),
        "rows": rows,
        "critical": critical,
        "warnings": warnings,
        "all_ok": not critical,
        "worst": rows[0] if rows else None,
    }


def markdown(result: dict, top: int = 3) -> list[str]:
    """Report-Zeilen im Stil des LAYOUT-REPORT.md (✅/⚠️/❌)."""
    b, l = BUDGET, LIMIT
    rows = result["rows"]
    lines = [
        f"DOM-Budget: {result['pages']} Seiten browser-treu vermessen "
        f"(ohne Chrome, ausgelieferte HTML). Grenzen – Lighthouse: "
        f"{l['children']} Kinder/Element, {l['head_children']} im Head, "
        f"{l['depth']} Tiefe, {l['elements']} Elemente; Laufzeit-DOM "
        f"(Browser, mit Erweiterungsschicht) wird zusätzlich gegen "
        f"{BUDGET_RUNTIME['elements']} Elemente geprüft.",
    ]
    if result["critical"]:
        lines.append(f"❌ {len(result['critical'])} Seite(n) über der "
                     "Lighthouse-Grenze:")
        for r in result["critical"][:top]:
            for c in r["critical"]:
                lines.append(f"  - {r['rel']}: {c}")
    if rows and not result["critical"]:
        worst_kids = max(rows, key=lambda r: r["maxchildren"])
        worst_head = max(rows, key=lambda r: r["headchildren"])
        worst_el = max(rows, key=lambda r: r["elements"])
        worst_depth = max(rows, key=lambda r: r["depth"])
        lines.append(
            f"✅ Kinder/Element: max. {worst_kids['maxchildren']} "
            f"({worst_kids['maxchildren_path']}) auf {worst_kids['rel']} – "
            f"Frühwarnung {b['children']}, Grenze {l['children']}.")
        lines.append(
            f"✅ Head-DOM: max. {worst_head['headchildren']} Kinder "
            f"({worst_head['rel']}) – Frühwarnung {b['head_children']}, "
            f"Grenze {l['head_children']}.")
        lines.append(
            f"✅ Tiefe: max. {worst_depth['depth']} – Frühwarnung "
            f"{b['depth']}, Grenze {l['depth']}.")
        lines.append(
            f"✅ Elemente: max. {worst_el['elements']} ({worst_el['rel']}) – "
            f"Frühwarnung {b['elements']}, Grenze {l['elements']}.")
    if result["warnings"]:
        lines.append(f"⚠️ Frühwarnung auf {len(result['warnings'])} Seite(n) "
                     f"(nur Hinweis, kein Issue):")
    for r in result["warnings"][:top]:
        for w in r["warnings"]:
            lines.append(f"  - {r['rel']}: {w}")
    return lines


# ---------------------------------------------------------------
# Selbsttest
# ---------------------------------------------------------------
# Die Erwartungen sind NICHT geschätzt, sondern mit einem echten HTML-Parser
# (jsdom, gleiche Regeln wie Chrome/Firefox) an genau diesen Zeichenketten
# gemessen – so bleibt der Vertrag „browser-treu“ überprüfbar.
SELFTEST_CASES: list[tuple[str, dict]] = [
    # 1 – unquotierte Attribute (hugo --minify)
    ('<html><head><meta charset=utf-8><meta name=viewport content="a b">'
     '</head><body><p>x</p></body></html>',
     {"elements": 6, "headchildren": 2, "depth": 2, "maxchildren": 2}),
    # 2 – Void-Elemente erzeugen keine Kinder, <p> endet am Block-Start
    ('<html><body><p>a<div>b</div><br><img src="x"></body></html>',
     {"elements": 7, "depth": 2, "maxchildren": 4}),
    # 3 – optionale End-Tags (minifiziert) + implizites <tbody>
    ('<html><body><table><tr><td>a<td>b</table><ul><li>1<li>2</ul>'
     '</body></html>',
     {"elements": 11, "depth": 5, "maxchildren": 2}),
    # 4 – <noscript> ist Rohtext: enthaltene <style> zählen NICHT.
    #      Bewusst NICHT mit jsdom gepinnt: jsdom parst ohne Scripting und
    #      sieht dort Elemente – der Browser mit aktivem JavaScript nicht
    #      (HTML5 „in head": noscript → RAWTEXT). Der Browser-Audit prüft
    #      diesen Fall an jeder echten Seite gegen (Parser-Drift-Vergleich).
    ('<html><head><noscript><style>a{}</style></noscript></head>'
     '<body></body></html>',
     {"elements": 4, "headchildren": 1, "depth": 2}),
    # 5 – <template> zählt, sein Inhalt gehört nicht zum Messbaum
    ('<html><body><template><p>a</p></template><p>b</p></body></html>',
     {"elements": 5, "depth": 2}),
    # 6 – Fremd-Inhalt: <path/> und <circle/> schließen sich selbst
    ('<html><body><svg viewBox="0 0 1 1"><path d="M0 0"/><circle r="1"/></svg>'
     '<div></div></body></html>',
     {"elements": 7, "depth": 3}),
    # 7 – Kommentare und ">" im Attributwert täuschen keine Tags vor;
    #     ein fehlender <head> wird wie im Browser ergänzt
    ('<html><body><!-- <p>x</p> --><a title="a > b">x</a></body></html>',
     {"elements": 4, "depth": 2}),
    # 8 – nicht geschlossene <p>/<li> (kaputtes Markup) bleiben stabil
    ('<html><body><ul><li>a<li>b</ul><p>c</body></html>',
     {"elements": 7, "depth": 3}),
]


def _selftest() -> int:
    fails = 0
    for i, (html, want) in enumerate(SELFTEST_CASES, 1):
        m = measure(html, f"case{i}")
        got = {"elements": m.elements, "depth": m.depth,
               "maxchildren": m.max_children}
        if "headchildren" in want:
            got["headchildren"] = m.head_children
        for key, value in want.items():
            if got.get(key) != value:
                print(f"❌ Selbsttest {i} ({key}): erwartet {value}, "
                      f"gemessen {got.get(key)}")
                fails += 1
    m = Metrics()
    m.rel = "/x/"
    m.elements = LIMIT["elements"] + 1
    crit, _ = violations(m)
    if not crit:
        print("❌ Selbsttest: Lighthouse-Grenze wird nicht als kritisch erkannt")
        fails += 1
    m = Metrics()
    m.rel = "/y/"
    # Zwei Messbereiche, zwei Budgets: der Laufzeit-Satz muss über dem
    # statischen liegen (die Erweiterungsschicht ist nachgemessen) und unter
    # der Lighthouse-Grenze bleiben – sonst wäre er kein Frühwarnwert.
    for key, value in BUDGET_RUNTIME.items():
        assert BUDGET[key] <= value <= LIMIT[key], (
            f"BUDGET_RUNTIME.{key}={value} liegt nicht zwischen "
            f"BUDGET ({BUDGET[key]}) und LIMIT ({LIMIT[key]})")
    assert BUDGET_RUNTIME["elements"] > BUDGET["elements"], (
        "Laufzeit-Frühwarnung muss über der statischen liegen "
        "(Erweiterungsschicht)")
    m.elements = BUDGET["elements"] + 1
    crit, warn = violations(m)
    if crit or not warn:
        print("❌ Selbsttest: Frühwarnung wird nicht als Warnung erkannt")
        fails += 1
    # Pfadangaben müssen reparierbar sein (Selektor-Form, >-getrennt)
    m = measure('<html><head></head><body><main id="m"><ul class="terms-tags">'
                '<li>1</li><li>2</li><li>3</li></ul></main></body></html>', "/t/")
    if "terms-tags" not in m.max_children_path or " > " not in m.max_children_path:
        print(f"❌ Selbsttest: DOM-Pfad unbrauchbar: {m.max_children_path!r}")
        fails += 1
    if fails == 0:
        print(f"Selbsttest: bestanden ({len(SELFTEST_CASES)} Parser-Fälle + "
              "Budget-Logik + Pfadform).")
    else:
        print(f"Selbsttest: {fails} Fehler.")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="DOM-/Layout-Budget (statisch)")
    ap.add_argument("--base", default=os.environ.get("LAYOUT_BASE_DIR",
                                                     DEFAULT_BASE))
    ap.add_argument("--json", dest="json_path", default="")
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--only", default="", help="nur Seiten mit diesem Pfad-Teil")
    ap.add_argument("--strict", action="store_true",
                    help="Frühwarnungen zählen als Fehler (PR-Gate)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return _selftest()
    if not os.path.isdir(args.base):
        print(f"FEHLER: {args.base} existiert nicht – erst `hugo` bauen.")
        return 2
    result = audit_dir(args.base)
    if args.json_path:
        target = os.path.abspath(args.json_path)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=1)
    print("\n".join(markdown(result, top=args.top)))
    if args.only:
        for row in result["rows"]:
            if args.only in row["rel"]:
                print("  · " + json.dumps(row, ensure_ascii=False))
    if args.strict and result["warnings"]:
        return 1
    return 0 if result["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
