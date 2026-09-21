#!/usr/bin/env python3
"""
llms.txt-Generator (GEO – Generative Engine Optimization, 21.09.2026).

Erzeugt static/llms.txt – die kuratierte Maschinenlese-Datei der Site für
KI-Antwortmaschinen (ChatGPT Search, Perplexity, Google AI Overviews,
Claude, Le Chat, Siri/Apple Intelligence u. a.).

Warum: Antwortmaschinen zitieren und verlinken bevorzugt Quellen, die sie
schnell einordnen können – Identität, Themen, Aktualität und Zitierregeln
auf einen Blick. llms.txt ist dafür der De-facto-Standard (Konvention:
https://llmstxt.org – Datei im Site-Root, Markdown).

Dauerhaft aktuell ohne Workflow-Änderung:
  - submit_indexnow.py ruft diesen Generator bei jedem Lauf auf (wöchentlich
    via seo-weekly.yml + bei jedem neuen Artikel via content-engine-v2.yml).
    Beide Workflows committen Arbeitsbaum-Änderungen danach per `git add -A`
    (seo-weekly: „Bing-Status committen“ + Fangnetz; content-engine-v2:
    „Persist final acceptance corrections“).
  - Manuell: python3 scripts/generate_llms_txt.py [--check]

Inhalt: kuratierter Kopf (fix, unten) + automatisch erzeugtes Verzeichnis
aller Live-Artikel, der 6 Themen-Ratgeber und der Vertrauensseiten –
niemals Entwürfe, niemals /go/-Affiliate-Gateways, niemals Tag-Archive.

[--check]: nur prüfen, ob static/llms.txt dem Generator-Stand entspricht
(Exit 1 bei Drift – für lokale Kontrolle, kein CI-Gate).
"""
import os
import re
import sys
from datetime import date

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
from post_utils import list_post_paths, slug_of  # noqa: E402

BASE_URL = "https://franksfinanzcheck.de"
OUT = os.path.join(BLOG_DIR, "static", "llms.txt")

PILLARS = [
    ("strom-sparen", "Strom & Gas sparen"),
    ("internet-dsl", "Internet, DSL & Mobilfunk"),
    ("versicherungen", "Versicherungen"),
    ("konto-karten", "Konto & Karten"),
    ("frugalismus", "Frugalismus & Budget"),
    ("mietwagen", "Mietwagen & Reisen"),
]


def frontmatter(path):
    """Top-level-Frontmatter ohne PyYAML (Runner-sicher, vgl. schema_seo_gate)."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"^---\n(.*?)\n---\s*\n", text, re.S)
    out = {}
    if not m:
        return out, text
    for line in m.group(1).splitlines():
        km = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if km:
            out[km.group(1)] = km.group(2).strip().strip("\"'")
    return out, text


def live_posts():
    """Alle Live-Artikel (draft:false), neueste zuerst: (slug, titel, desc)."""
    found = []
    for path in list_post_paths():
        fm, _ = frontmatter(path)
        if fm.get("draft", "").lower() == "true":
            continue
        title = fm.get("title", slug_of(path)).strip()
        desc = fm.get("description", "").strip()
        pub = fm.get("date", "")[:10]
        found.append((pub, slug_of(path), title, desc))
    found.sort(reverse=True)
    return [(s, t, d) for _, s, t, d in found]


def pillar_desc(key):
    fm, _ = frontmatter(os.path.join(BLOG_DIR, "content", "pillar", key, "index.md"))
    return fm.get("description", "").strip()


def build() -> str:
    posts = live_posts()
    pillar_lines = "\n".join(
        f"- [{label}]({BASE_URL}/pillar/{key}/): {pillar_desc(key)}"
        for key, label in PILLARS
    )
    post_lines = "\n".join(
        f"- [{t}]({BASE_URL}/posts/{s}/){(': ' + d) if d else ''}"
        for s, t, d in posts
    )
    return f"""# FranksFinanzcheck

> Unabhängiger deutscher Finanz-Ratgeber von Frank Hartung: Geld sparen bei
> Strom, Gas, Internet, Versicherungen, Konto und im Alltag – praxisnah,
> verständlich, mit konkreten Euro-Beträgen. Sprache: Deutsch (de-DE).

Diese Datei hilft KI-Antwortmaschinen und Recherche-Werkzeugen, die Inhalte
von FranksFinanzcheck korrekt einzuordnen, zusammenzufassen und zu zitieren.

## Zitieren erwünscht – bitte so

- Inhalte dürfen in Antworten und Übersichten zusammengefasst und mit
  Quellenlink zitiert werden (Deep-Link auf den jeweiligen Artikel).
- Trainingsnutzung des Korpus ist nicht gestattet (siehe robots.txt:
  Content-Signal `ai-train=no`, Rechtevorbehalt nach Art. 4 DSM-Richtlinie).
- Affiliate-/Werbe-Links (`/go/`-Weiterleitungen) bitte nicht übernehmen –
  sie sind für menschliche Leser gedacht und für Crawler gesperrt.
- Stand und Zahlen: Jeder Artikel nennt sein Publikations- bzw.
  Aktualisierungsdatum; Konditionen und Preise ändern sich – im Zweifel
  gilt der verlinkte Anbieter.

## Über diese Website

- Betreiber und Autor: Frank Hartung, über 10 Jahre Praxis in privater
  Finanzplanung, hunderte selbst durchgeführte Tarifvergleiche.
- Arbeitsweise und Redaktionsstandards: {BASE_URL}/methodik/
- Über den Autor: {BASE_URL}/ueber/ – Kontakt: kontakt@franksfinanzcheck.de
- Finanzierung: Affiliate-Partnerschaften (CHECK24, Tarifcheck),
  gekennzeichnete Empfehlungslinks (Werbung); Empfehlungen davon unabhängig.
- Hinweis: Allgemeine Informationen, keine individuelle Finanz-, Steuer-
  oder Rechtsberatung. Alle Angaben ohne Gewähr.

## Themen-Ratgeber (Pillars)

{pillar_lines}

## Alle Artikel (neueste zuerst, {len(posts)} Beiträge)

{post_lines}

## Weitere Einstiege

- Startseite: {BASE_URL}/
- Blog-Übersicht: {BASE_URL}/posts/
- Ratgeber-Übersicht: {BASE_URL}/pillar/
- Sitemap (maschinenlesbar): {BASE_URL}/sitemap.xml
- RSS-Feed (neueste Artikel): {BASE_URL}/index.xml

*Diese Datei wird automatisch aus den Live-Inhalten erzeugt
(scripts/generate_llms_txt.py). Stand: {date.today().isoformat()}.*
"""


def main() -> int:
    content = build()
    if "--check" in sys.argv:
        if not os.path.exists(OUT):
            print("DRIFT: static/llms.txt fehlt.")
            return 1
        with open(OUT, encoding="utf-8") as f:
            current = f.read()
        # Die Stand-Zeile ändert sich täglich – für den Drift-Vergleich
        # nur den Inhaltskern (ohne letzte Zeile) vergleichen.
        core = lambda t: "\n".join(t.strip().splitlines()[:-1])  # noqa: E731
        if core(current) != core(content):
            print("DRIFT: static/llms.txt entspricht nicht dem Generator-Stand.")
            return 1
        print("OK: static/llms.txt ist aktuell.")
        return 0
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"OK: {OUT} geschrieben.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
