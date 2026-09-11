#!/usr/bin/env python3
"""Verbindliches, schreibfreies Gate für die Themen-Navigation.

Der frühere R9-Scan meldete _index.md zwar, gab im Bestandsmodus aber
Exit 0 zurück; --new-only übersprang die Übersicht vollständig. Dieses
Gate prüft die zentrale Datenquelle UND den fertigen Hugo-Build, unabhängig
vom Alter der Artikel. Fehlende Builds sind Fehler, kein stiller Skip.

  python3 scripts/themenwelten_guard.py --source-only
  python3 scripts/themenwelten_guard.py --public public
  python3 scripts/themenwelten_guard.py --public tmp/subdir --base-path /blog/

Keine Reparatur-Heuristik: Ein Defekt stoppt den Deploy (Exit 1), statt
Redaktionstext umzuschreiben oder fehlende Themen still zu unterschlagen.
Nur Python-Standardbibliothek + vorhandene R8/R9-Prüfung, keine API/Reports.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from textverstaendnis_guard import check_klebewoerter, check_nested_links, split_body

ROOT = Path(__file__).resolve().parents[1]
TOPIC_IDS = (
    "strom-sparen", "internet-dsl", "versicherungen",
    "konto-karten", "frugalismus", "mietwagen",
)
TITLE_ID = "deine-6-themenwelten"
LEGACY_ID = "ddeine6-themenwelten"


def text_findings(label: str, text: str) -> list[str]:
    return [f"{label}: {rule}: {detail}" for _, rule, detail, _ in
            check_klebewoerter(label, text) + check_nested_links(label, text)]


def validate_data(data: object) -> list[str]:
    if not isinstance(data, dict):
        return ["Themen-Daten müssen ein JSON-Objekt sein."]
    errors = []
    if data.get("title") != f"Deine {len(TOPIC_IDS)} Themenwelten":
        errors.append("Die Überschrift muss exakt ‚Deine 6 Themenwelten‘ lauten.")
    topics = data.get("topics")
    if not isinstance(topics, list) or len(topics) != len(TOPIC_IDS):
        return errors + ["Genau sechs Themen sind erforderlich."]
    ids = [topic.get("id") for topic in topics if isinstance(topic, dict)]
    if Counter(str(key) for key in ids) != Counter(TOPIC_IDS):
        errors.append("Die sechs Themen-IDs müssen vollständig und eindeutig sein.")
    for label, record, keys in [("Themenwelten", data, ("title", "intro", "tip"))] + [
        (f"Thema {i + 1}", topic, ("id", "title", "description", "emoji"))
        for i, topic in enumerate(topics)
    ]:
        if not isinstance(record, dict):
            errors.append(f"{label}: kein Objekt.")
            continue
        for key in keys:
            value = record.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{label}: {key} muss ein nicht leerer Text sein.")
            elif re.search(r"[<>{}\r\n]", value):
                errors.append(f"{label}: {key} darf kein Markup enthalten.")
            else:
                errors.extend(text_findings(f"{label}/{key}", value))
    return errors


def validate_source(root: Path) -> tuple[dict, list[str]]:
    try:
        data = json.loads((root / "data/themenwelten.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {}, [f"Themen-Daten nicht lesbar: {exc}"]
    errors = validate_data(data)
    for key in TOPIC_IDS:
        if not (root / f"content/pillar/{key}/index.md").is_file():
            errors.append(f"Ratgeber-Quelle fehlt: content/pillar/{key}/index.md")
    try:
        source = (root / "content/posts/_index.md").read_text(encoding="utf-8")
        errors.extend(text_findings("content/posts/_index.md", source))
        if re.search(r"^#{1,6}\s+[^\n]*Themenwelten\b", split_body(source), re.M | re.I):
            errors.append("Keine zweite Themen-Überschrift in _index.md pflegen; das Layout rendert sie.")
    except OSError as exc:
        errors.append(f"Blog-Übersicht nicht lesbar: {exc}")
    return data, errors


@dataclass(eq=False)
class Node:
    tag: str
    attrs: dict
    parent: Node | None
    parts: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join("".join(self.parts).split())

    def has_class(self, name: str) -> bool:
        return name in (self.attrs.get("class") or "").split()

    def inside(self, ancestor: Node) -> bool:
        parent = self.parent
        while parent:
            if parent is ancestor:
                return True
            parent = parent.parent
        return False


class Page(HTMLParser):
    """Kleine Strukturansicht für Hugos HTML (auch minifizierte Attribute).

    Versteckte Anker/SVGs gehören nicht zum sichtbaren Überschriftentext.
    Es werden keine CSS-/JS-Inhalte als Prosa auf Tippfehler geprüft.
    """
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, html: str):
        super().__init__(convert_charrefs=True)
        self.nodes: list[Node] = []
        self.stack: list[Node] = []
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attrs):
        # Optional ausgelassene End-Tags bei HTML-Minifizierung.
        if self.stack and self.stack[-1].tag == "p" and tag in {"p", "div", "section", "h2", "h3", "ul", "ol", "header"}:
            self.stack.pop()
        if tag == "li":
            for node in reversed(self.stack):
                if node.tag in {"ul", "ol"}:
                    break
                if node.tag == "li":
                    self.handle_endtag("li")
                    break
        node = Node(tag, dict(attrs), self.stack[-1] if self.stack else None)
        self.nodes.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if any(n.tag in {"script", "style", "svg"} or "hidden" in n.attrs
               or n.attrs.get("aria-hidden") == "true" for n in self.stack):
            return
        for node in self.stack:
            node.parts.append(data)

    def by_class(self, name: str) -> list[Node]:
        return [n for n in self.nodes if n.has_class(name)]

    def by_id(self, name: str) -> list[Node]:
        return [n for n in self.nodes if n.attrs.get("id") == name]


def output_path(public: Path, href: str, base_path: str) -> Path | None:
    """Nur lokale Verzeichnisse innerhalb dieses Build-Artefakts auflösen."""
    url = urlsplit(href)
    path = unquote(url.path)
    if url.scheme or url.netloc or not path.startswith(base_path) or url.query:
        return None
    dest = (public / path[len(base_path):] / "index.html").resolve()
    return dest if dest.is_relative_to(public.resolve()) else None


def check_worlds(page: Page, data: dict, public: Path, base_path: str, *, home=False) -> list[str]:
    errors = []
    regions = page.by_class("ff-topics")
    cards = page.by_class("ff-topic-card")
    if len(regions) != 1 or len(cards) != 6:
        return ["Genau ein Themenbereich mit sechs Karten muss im HTML stehen."]
    region = regions[0]
    heading_id = "home-themenwelten" if home else TITLE_ID
    headings = page.by_id(heading_id)
    if len(headings) != 1 or headings[0].tag != "h2" or not headings[0].inside(region):
        errors.append("Eine eindeutige H2 mit stabilem Themen-Anker ist erforderlich.")
    elif not home and headings[0].text != data["title"]:
        errors.append("Der sichtbare Themen-Titel weicht von der geprüften Datenquelle ab.")
    if region.attrs.get("aria-labelledby") != heading_id:
        errors.append("Der Themenbereich muss über seine Überschrift beschriftet sein.")
    errors.extend(text_findings("Themenbereich", region.text))
    ids = [n.attrs["id"] for n in page.nodes if n.inside(region) and n.attrs.get("id")]
    if len(ids) != len(set(ids)):
        errors.append("Doppelte IDs im Themenbereich.")
    for card, topic in zip(cards, data["topics"]):
        label = topic["id"]
        if card.tag != "a" or not card.inside(region) or card.attrs.get("data-topic") != label:
            errors.append(f"{label}: Reihenfolge/Struktur der Karte stimmt nicht.")
        nested = [n for n in page.nodes if n.inside(card) and n.tag in {"a", "button", "input", "select", "textarea"}]
        if nested:
            errors.append(f"{label}: keine verschachtelten Bedienelemente in einer Link-Karte.")
        titles = [n for n in page.nodes if n.inside(card) and n.tag == "h3"]
        if len(titles) != 1 or titles[0].text != topic["title"]:
            errors.append(f"{label}: Kartentitel fehlt oder weicht von der Datenquelle ab.")
        elif card.attrs.get("aria-labelledby") != titles[0].attrs.get("id"):
            errors.append(f"{label}: zugänglicher Linkname stimmt nicht mit dem Titel überein.")
        descriptions = [n for n in page.by_class("ff-topic-description") if n.inside(card)]
        if len(descriptions) != 1 or descriptions[0].text != topic["description"]:
            errors.append(f"{label}: Beschreibung fehlt oder weicht von der Datenquelle ab.")
        refs = (card.attrs.get("aria-describedby") or "").split()
        if len(refs) != 2 or any(len(page.by_id(ref)) != 1 or not page.by_id(ref)[0].inside(card) for ref in refs):
            errors.append(f"{label}: Beschreibung/Zähler nicht eindeutig zugänglich verknüpft.")
        if any("hidden" in n.attrs or n.attrs.get("aria-hidden") == "true" for n in (card, region)):
            errors.append(f"{label}: Navigation darf nicht versteckt sein.")
        href = card.attrs.get("href", "")
        target = output_path(public, href, base_path)
        if href != f"{base_path}pillar/{label}/" or not target or not target.is_file():
            errors.append(f"{label}: Themen-Ziel fehlt im Build oder URL ist falsch: {href}")
            continue
        target_page = Page(target.read_text(encoding="utf-8"))
        if not any(n.tag == "h1" for n in target_page.nodes) or any(
                n.tag == "meta" and (n.attrs.get("http-equiv") or "").lower() == "refresh" for n in target_page.nodes):
            errors.append(f"{label}: Ziel ist kein veröffentlichter Ratgeber.")
        article_links = [n for n in target_page.nodes if n.tag == "a"
                         and (n.attrs.get("aria-label") or "").startswith("Weiterlesen:")]
        counts = [n for n in page.by_class("ff-topic-count") if n.inside(card)]
        count = len(article_links)
        expected = f"{count} Artikel" if count else "Basis-Ratgeber"
        if len(counts) != 1 or counts[0].attrs.get("data-article-count") != str(count) or counts[0].text != expected:
            errors.append(f"{label}: Artikelzahl stimmt nicht mit dem veröffentlichten Themen-Ratgeber überein.")
        for link in article_links:
            dest = output_path(public, link.attrs.get("href", ""), base_path)
            if not dest or not dest.is_file():
                errors.append(f"{label}: verlinkter Themen-Artikel fehlt im Build: {link.attrs.get('href')}")
    return errors


def validate_build(public: Path, data: dict, base_path="/") -> list[str]:
    errors = []
    for rel, home in (("posts/index.html", False), ("index.html", True)):
        file = public / rel
        if not file.is_file():
            errors.append(f"Build fehlt: {file}")
            continue
        page = Page(file.read_text(encoding="utf-8"))
        errors.extend(f"{rel}: {error}" for error in check_worlds(page, data, public, base_path, home=home))
        if not home:
            if len(page.by_id(LEGACY_ID)) != 1:
                errors.append(f"{rel}: der alte Themen-Anker muss als unsichtbares Sprungziel erhalten bleiben.")
            feed = page.by_id("neueste-artikel")
            if len(feed) != 1 or not page.by_class("ff-posts-feed"):
                errors.append(f"{rel}: Artikelliste/Sprungziel fehlt.")
            elif page.by_class("ff-topics") and page.nodes.index(feed[0]) < page.nodes.index(page.by_class("ff-topics")[0]):
                errors.append(f"{rel}: die Themen-Navigation muss vor der Artikelliste stehen.")
            if page.by_class("ff-filter-bar"):
                errors.append(f"{rel}: die doppelte Pseudo-Filterleiste darf nicht wiederkehren.")
    for file in sorted((public / "posts/page").glob("*/index.html")):
        page = Page(file.read_text(encoding="utf-8"))
        # /page/1/ ist ein legitimer Hugo-Redirect, keine zweite Listenseite.
        if file.parent.name == "1":
            continue
        if page.by_class("ff-topics") or page.by_class("ff-posts-guide") or page.by_class("ff-filter-bar"):
            errors.append(f"{file}: Themen/Einleitung dürfen auf Folgeseiten nicht erneut erscheinen.")
        if not page.by_class("ff-posts-feed"):
            errors.append(f"{file}: Artikelliste fehlt.")
        if not any(n.tag == "a" and n.attrs.get("href") == f"{base_path}posts/#{TITLE_ID}" for n in page.nodes):
            errors.append(f"{file}: Rückweg zu den Themenwelten fehlt.")
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--public", type=Path, default=ROOT / "public")
    parser.add_argument("--source-only", action="store_true")
    parser.add_argument("--base-path", default="/")
    args = parser.parse_args(argv)
    data, errors = validate_source(args.root)
    prefix = "/" + args.base_path.strip("/") + "/" if args.base_path.strip("/") else "/"
    if not errors and not args.source_only:
        errors.extend(validate_build(args.public, data, prefix))
    if errors:
        print("Themenwelten-Gate: NICHT bestanden – Veröffentlichung stoppen.")
        for error in errors:
            print(f"  ✗ {error}")
        return 1
    print("Themenwelten-Gate: sechs eindeutige Themen, saubere Texte" +
          (" (Quellprüfung)." if args.source_only else ", erreichbare Ziele und konsistente Live-Zähler geprüft."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
