#!/usr/bin/env python3
# ============================================================
#  SUCHINDEX-WACHE – der Pagefind-Index gegen die Seiten geprüft
#  ------------------------------------------------------------
#  Warum diese Wache (Dauerheilung #644, 08.10.2026):
#  `pagefind --site` schreibt eine gültige pagefind.js auch dann, wenn
#  der Index LEER ist – etwa weil ein Template data-pagefind-body verliert
#  oder der Body versehentlich data-pagefind-ignore="all" bekommt. Ein
#  `test -s` im Deploy sieht das nicht. Diese Wache vergleicht darum den
#  Index mit der Regel, die die Seiten selbst tragen:
#
#    indexiert wird eine gebaute Seite, wenn sie
#      · ein Element mit data-pagefind-body hat,
#      · am <body> NICHT data-pagefind-ignore="all" trägt und
#      · im robots-Meta NICHT „noindex“ sagt.
#
#  Pagefind ignoriert das robots-Meta selbst. Die Wache erzwingt es, damit
#  noindex-Seiten (404, Newsletter-Abmeldung, Blätterseiten …) nie als
#  Treffer erscheinen. Die Regel spiegelt layouts/baseof.html und
#  layouts/_partials/seo_indexierbar.html – geprüft wird das gebaute HTML,
#  nicht die Templates.
#
#  AUFRUF
#    python3 scripts/suchindex_check.py --site public   # prüft den Index
#    python3 scripts/suchindex_check.py --selftest      # Sabotage-Proben
#
#  EXIT   0 = Index entspricht den indexierbaren Seiten
#         1 = Abweichung (fehlende, zusätzliche oder falsch gezählte Seiten)
#         2 = Index fehlt/unlesbar oder Selbsttest defekt (fail-closed)
#
#  Nur Standardbibliothek: läuft im Deploy ohne pip.
# ============================================================
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRAGMENT_KOPF = b"pagefind_dcd"  # Kopf jedes Pagefind-Fragments (Pagefind 1.5.x)


class IndexFehler(Exception):
    """Index fehlt, ist unlesbar oder hat ein unbekanntes Format (Exit 2)."""


class _Seite(HTMLParser):
    """Liest nur die drei Merkmale, die über Indexierung entscheiden."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hat_body_marker = False
        self.body_ignoriert = False
        self.robots = ""

    def handle_starttag(self, tag, attrs):
        werte = {k: ("" if v is None else v) for k, v in attrs}
        if "data-pagefind-body" in werte:
            self.hat_body_marker = True
        if tag == "body":
            self.body_ignoriert = werte.get("data-pagefind-ignore", "").strip().lower() == "all"
        if tag == "meta" and werte.get("name", "").strip().lower() == "robots":
            self.robots = werte.get("content", "").strip().lower()


def url_von(rel: Path) -> str:
    """Dateipfad im Build -> URL-Pfad, so wie Pagefind ihn ausgibt."""
    teile = rel.parts
    if rel.name == "index.html":
        return "/" + "/".join(teile[:-1]) + ("/" if teile[:-1] else "")
    return "/" + rel.as_posix()


def indexierbare_seiten(site: Path) -> tuple[set[str], int]:
    """(URLs, die indexiert werden müssen; Anzahl gebauter HTML-Dateien)."""
    erwartet: set[str] = set()
    gebaut = 0
    for pfad in sorted(site.rglob("*.html")):
        rel = pfad.relative_to(site)
        if rel.parts and rel.parts[0] == "pagefind":
            continue
        gebaut += 1
        parser = _Seite()
        parser.feed(pfad.read_text(encoding="utf-8", errors="replace"))
        if not parser.hat_body_marker or parser.body_ignoriert:
            continue
        if "noindex" in parser.robots:
            continue
        erwartet.add(url_von(rel))
    return erwartet, gebaut


def index_lesen(pagefind_dir: Path) -> tuple[int, set[str], int]:
    """(page_count laut pagefind-entry.json, URLs aller Fragmente, Anzahl Fragmentdateien)."""
    eintrag = pagefind_dir / "pagefind-entry.json"
    if not eintrag.is_file():
        raise IndexFehler(f"{eintrag} fehlt – der Index wurde nicht gebaut.")
    try:
        entry = json.loads(eintrag.read_text(encoding="utf-8"))
        zahl = sum(int(v.get("page_count", 0)) for v in entry["languages"].values())
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        raise IndexFehler(f"{eintrag} ist nicht lesbar: {e}") from None
    urls: set[str] = set()
    dateien = sorted((pagefind_dir / "fragment").glob("*.pf_fragment"))
    for frag in dateien:
        try:
            roh = gzip.decompress(frag.read_bytes())
        except OSError:
            raise IndexFehler(f"{frag.name}: kein gzip – Pagefind-Format geändert?") from None
        if not roh.startswith(FRAGMENT_KOPF):
            raise IndexFehler(f"{frag.name}: unbekannter Kopf – Pagefind-Format geändert?")
        try:
            daten = json.loads(roh[len(FRAGMENT_KOPF):].decode("utf-8"))
            urls.add(str(daten["url"]))
        except (ValueError, KeyError, TypeError):
            raise IndexFehler(f"{frag.name}: keine URL lesbar.") from None
    return zahl, urls, len(dateien)


def bewerte(erwartet: set[str], zahl: int, urls: set[str], dateien: int | None = None) -> list[str]:
    """Befunde als Text; leere Liste = Index ist korrekt."""
    befunde: list[str] = []
    if dateien is not None and dateien != zahl:
        befunde.append(
            f"{dateien} Fragmentdateien für {zahl} Seiten: alte Ausgabe liegt im Ordner. "
            "Ausgabeordner vor dem Lauf leeren (npm run suchindex)."
        )
    if not urls:
        befunde.append("Index ist leer – keine Seite wurde indexiert.")
    zu_viel = sorted(urls - erwartet)
    fehlt = sorted(erwartet - urls)
    if zu_viel:
        befunde.append(
            f"{len(zu_viel)} Seite(n) im Index, die nicht indexiert sein dürfen "
            f"(noindex, Suchseite, Blätterseite oder ohne Inhaltsmarke): " + ", ".join(zu_viel[:12])
        )
    if fehlt:
        befunde.append(
            f"{len(fehlt)} indexierbare Seite(n) fehlen im Index: " + ", ".join(fehlt[:12])
        )
    if zahl != len(urls):
        befunde.append(
            f"pagefind-entry.json meldet {zahl} Seiten, die Fragmente enthalten {len(urls)}."
        )
    return befunde


def pruefe(site: Path) -> tuple[int, list[str], str]:
    """(Exit-Code, Befunde, Zusammenfassung) für einen gebauten Stand."""
    pagefind_dir = site / "pagefind"
    try:
        erwartet, gebaut = indexierbare_seiten(site)
        zahl, urls, dateien = index_lesen(pagefind_dir)
    except IndexFehler as e:
        return 2, [str(e)], ""
    befunde = bewerte(erwartet, zahl, urls, dateien)
    zusammen = (f"{gebaut} HTML-Seiten gebaut · {len(erwartet)} indexierbar · "
                f"{len(urls)} im Index · {gebaut - len(erwartet)} bewusst ausgeschlossen")
    return (1 if befunde else 0), befunde, zusammen


# ------------------------------------------------------------ Selbsttest
def _schreibe_seite(site: Path, rel: str, *, body_marker=True, body_ignore=False, robots="index, follow"):
    pfad = site / rel
    pfad.parent.mkdir(parents=True, exist_ok=True)
    marker = " data-pagefind-body" if body_marker else ""
    ignore = ' data-pagefind-ignore="all"' if body_ignore else ""
    pfad.write_text(
        "<!DOCTYPE html><html lang=\"de\"><head>"
        f"<meta name=robots content=\"{robots}\"><title>T</title></head>"
        f"<body{ignore}><main{marker}><h1>T</h1></main></body></html>",
        encoding="utf-8",
    )


def _schreibe_index(site: Path, urls: list[str], zahl: int | None = None, kopf: bytes = FRAGMENT_KOPF):
    pagefind = site / "pagefind"
    (pagefind / "fragment").mkdir(parents=True, exist_ok=True)
    for i, url in enumerate(urls):
        daten = json.dumps({"url": url, "content": "x"}, ensure_ascii=False).encode("utf-8")
        (pagefind / "fragment" / f"de_{i:04d}.pf_fragment").write_bytes(gzip.compress(kopf + daten))
    anzahl = len(urls) if zahl is None else zahl
    entry = {"version": "1.5.2", "languages": {"de": {"hash": "de_x", "page_count": anzahl}}}
    (pagefind / "pagefind-entry.json").write_text(json.dumps(entry), encoding="utf-8")


def _baue_probestand(site: Path) -> None:
    _schreibe_seite(site, "index.html")
    _schreibe_seite(site, "posts/a/index.html")
    _schreibe_seite(site, "werkzeuge/x/index.html")
    _schreibe_seite(site, "suche/index.html", body_ignore=True)                       # Suchseite
    _schreibe_seite(site, "newsletter/index.html", robots="noindex, nofollow")         # noindex
    _schreibe_seite(site, "posts/page/2/index.html", body_ignore=True, robots="noindex, follow")
    _schreibe_seite(site, "404.html", body_ignore=True, robots="noindex, nofollow")
    _schreibe_seite(site, "google123.html", body_marker=False)                        # ohne Inhalt


GUT = ["/", "/posts/a/", "/werkzeuge/x/"]

# Sabotagen mit erwartetem Ergebnis. Jede MUSS auffallen (Exit != 0).
SABOTAGEN = [
    ("Suchseite leakt in den Index", GUT + ["/suche/"], None, None),
    ("noindex-Seite leakt in den Index", GUT + ["/newsletter/"], None, None),
    ("Blätterseite leakt in den Index", GUT + ["/posts/page/2/"], None, None),
    ("indexierbare Seite fehlt im Index", ["/", "/posts/a/"], None, None),
    ("Index ist leer", [], None, None),
    ("page_count passt nicht zu den Fragmenten", GUT, 99, None),
    ("fremdes Fragment-Format", GUT, None, b"anderes_format"),
]


def selftest() -> tuple[list[str], int]:
    """(Fehlerliste, Anzahl geprüfter Proben). Leere Fehlerliste = Wache bewährt."""
    fehler: list[str] = []
    proben = 0
    with tempfile.TemporaryDirectory() as tmp:
        basis = Path(tmp)

        # 1) Positivprobe: korrekter Index -> Exit 0
        gut = basis / "gut"
        _baue_probestand(gut)
        _schreibe_index(gut, GUT)
        proben += 1
        code, befunde, _ = pruefe(gut)
        if code != 0:
            fehler.append(f"Positivprobe rot: {befunde}")

        # 2) Sabotagen: Index falsch -> Exit 1 (oder 2 bei Formatfehler)
        for n, (name, urls, zahl, kopf) in enumerate(SABOTAGEN):
            s = basis / f"sabotage_{n}"
            _baue_probestand(s)
            _schreibe_index(s, urls, zahl, kopf or FRAGMENT_KOPF)
            proben += 1
            if pruefe(s)[0] == 0:
                fehler.append(f"Sabotage unentdeckt: {name}")

        # 2b) Alte Fragmentdatei aus einem früheren Lauf im Ordner -> Exit 1
        s = basis / "sabotage_altes_fragment"
        _baue_probestand(s)
        _schreibe_index(s, GUT)
        (s / "pagefind" / "fragment" / "de_alt.pf_fragment").write_bytes(
            gzip.compress(FRAGMENT_KOPF + json.dumps({"url": "/posts/a/", "content": "alt"}).encode("utf-8")))
        proben += 1
        if pruefe(s)[0] != 1:
            fehler.append("Sabotage unentdeckt: alte Fragmentdatei im Ausgabeordner")

        # 3) Fehlender oder beschädigter Index -> Exit 2 (fail-closed)
        s = basis / "sabotage_kein_index"
        _baue_probestand(s)
        proben += 1
        if pruefe(s)[0] != 2:
            fehler.append("Sabotage unentdeckt: kein Index gebaut")
        s = basis / "sabotage_kaputte_entry"
        _baue_probestand(s)
        (s / "pagefind").mkdir(parents=True, exist_ok=True)
        (s / "pagefind" / "pagefind-entry.json").write_text("{kaputt", encoding="utf-8")
        proben += 1
        if pruefe(s)[0] != 2:
            fehler.append("Sabotage unentdeckt: beschädigte pagefind-entry.json")

        # 4) Regelwerk: Dateipfad -> URL
        for rel, soll in [("index.html", "/"), ("posts/a/index.html", "/posts/a/"), ("x.html", "/x.html")]:
            proben += 1
            if url_von(Path(rel)) != soll:
                fehler.append(f"url_von({rel}) != {soll}")
    return fehler, proben


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Prüft den Pagefind-Index gegen die indexierbaren Seiten.")
    ap.add_argument("--site", default=str(ROOT / "public"), help="gebauter Stand (Standard: public/)")
    ap.add_argument("--selftest", action="store_true", help="Sabotage-Proben statt Prüfung")
    args = ap.parse_args(argv)
    annotation = bool(os.environ.get("GITHUB_ACTIONS"))

    if args.selftest:
        fehler, proben = selftest()
        if fehler:
            print("❌ suchindex_check --selftest: " + " | ".join(fehler))
            return 2
        print(f"✅ suchindex_check --selftest: {proben} Proben bestanden (Positiv-, Sabotage- und Regelproben).")
        return 0

    code, befunde, zusammen = pruefe(Path(args.site))
    if code == 0:
        print(f"✅ Suchindex korrekt: {zusammen}.")
        return 0
    for b in befunde:
        if annotation:
            print(f"::error title=Suchindex::{b}")
        print(f"❌ {b}")
    if code == 2:
        print("   → Index fehlt oder ist unlesbar: Deploy stoppt (fail-closed). Runbook: docs/ANLEITUNG-SUCHE-PAGEFIND.md")
    else:
        print(f"   → {zusammen}. Runbook: docs/ANLEITUNG-SUCHE-PAGEFIND.md")
    return code


if __name__ == "__main__":
    sys.exit(main())
