#!/usr/bin/env python3
"""Cornerstone-Inhalte markieren und prüfen (28.10.2026).

WARUM DIESE DATEI EXISTIERT
===========================
Yoast Premium erlaubt es, Beiträge als „Cornerstone" zu markieren: die
Inhalte, die eine Themenwelt tragen und auf die alles andere verlinkt.
Das Blog hat diesen Begriff bisher nicht – es hatte nur das Gefühl, dass
manche Artikel wichtiger sind. Ohne Markierung gibt es aber keine Regel,
die prüft, ob die wichtigen Artikel auch WICHTIG BEHANDELT werden:

  · Ein Cornerstone ohne eingehende Links ist eine Visitenkarte im Keller.
  · Ein Cornerstone, der seit einem Jahr nicht angefasst wurde, verliert
    gegen frischere Wettbewerber.
  · Ein Cornerstone ohne benannte Hauptintention ist beliebig.

Das Feld ist deshalb ein Bekenntnis mit Folgen:

    cornerstone: true

REGELN (jede mit Selbsttest-Fall)
---------------------------------
  C1  `cornerstone` ist ein boolescher Wert (kein „ja", kein String)
  C2  Ein Cornerstone ist veröffentlicht (kein Draft/Zukunft/abgelaufen)
  C3  Mindestens N eingehende interne Links aus anderen Artikeln
      (Standard 5, `--min-eingehend`)
  C4  Zuletzt vor höchstens 180 Tagen aktualisiert (`--max-alter`)
  C5  Vollständig: Hauptintention (`keywords_fokus`), `kurzantwort`,
      Quellen (`quellen`) und Cover-Alt-Text
  C6  Hinweis: eingehende Links kommen aus nur einer Themenwelt
      (P3 – kein Gate, weil ein Nischen-Cornerstone legitim eng sein darf)

WER HAT DAS RECHT ZU ENTSCHEIDEN?
---------------------------------
Niemand automatisch. Diese Wache MARKIERT nicht, sie PRÜFT. Der Bericht
nennt zusätzlich Kandidaten – Seiten mit vielen eingehenden Links, die
noch nicht markiert sind – und liefert die Frontmatter-Zeile zum
Einfügen. Die Entscheidung bleibt redaktionell; ein Skript, das sich
selbst zu Cornerstones erklärt, hebt die Bedeutung des Feldes auf.

VERZAHNUNG
----------
  · `--json` liefert den Stand für scripts/seo_cockpit.py (Befunde
    erscheinen dort im selben Bericht wie Canonical und Sitemap).
  · C5 prüft `keywords_fokus` – dasselbe Feld, das
    scripts/fokus_keywords.py inhaltlich bewertet (F1–F8).

Nutzung:
    python3 scripts/cornerstone_wache.py                  # Prüfung
    python3 scripts/cornerstone_wache.py --kandidaten     # Vorschläge
    python3 scripts/cornerstone_wache.py --md bericht.md
    python3 scripts/cornerstone_wache.py --json
    python3 scripts/cornerstone_wache.py --selftest

Exit: 0 ohne Gate-Befund, 1 bei P1/P2, 2 bei Eingabefehlern.
"""
from __future__ import annotations

import argparse
import contextlib
import glob
import json
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fokus_keywords import (ist_live, ohne_code, parse_fokus,  # noqa: E402
                            split_frontmatter)

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATEIEN = ("content/posts/*/index.md", "content/posts/*.md")
SKIP = {"_index.md"}

FELD = "cornerstone"
MIN_EINGEHEND = 5
MAX_ALTER_TAGE = 180
KANDIDATEN_MAX = 10

# Interne Linkformen, die im Bestand wirklich vorkommen (28.10.2026 gemessen:
# 505 Verweise in 98 Dateien, überwiegend `](/posts/<slug>/)`, daneben
# `](../../posts/<slug>/)`). Absolute Marken-URLs kommen ebenfalls vor und
# zählen mit – sie sind für den Leser derselbe Link.
LINK_MUSTER = (
    re.compile(r"\]\(\s*(?:\.\./)+posts/([A-Za-z0-9._-]+)/?\s*(?:#[^)]*)?\)"),
    re.compile(r"\]\(\s*/posts/([A-Za-z0-9._-]+)/?\s*(?:#[^)]*)?\)"),
    re.compile(r"\]\(\s*https?://(?:www\.)?franksfinanzcheck\.de/posts/([A-Za-z0-9._-]+)/?\s*(?:#[^)]*)?\)"),
)


def _slug(pfad: str) -> str:
    return os.path.basename(os.path.dirname(pfad)) if os.path.basename(pfad) == "index.md" \
        else os.path.basename(pfad)[:-3]


def _body(text: str) -> str:
    return split_frontmatter(text)[1]


def links_im_body(body: str) -> set[str]:
    """Ziel-Slugs eines Artikels.

    Code-Blöcke und Shortcodes werden vorher entfernt: Ein Link in einem
    Beispiel-Snippet ist kein Verweis der Seite (dieselbe Grenze wie im
    internal_linker, dort aus einem echten Build-Schaden gelernt).
    """
    text = ohne_code(body)
    text = re.sub(r"`[^`\n]*`", " ", text)
    text = re.sub(r"\{\{[<%][^>%]{0,500}[>%]\}\}", " ", text)
    ziele: set[str] = set()
    for muster in LINK_MUSTER:
        ziele.update(muster.findall(text))
    return ziele


def _datum(fm: dict) -> str:
    return str(fm.get("lastmod") or fm.get("date") or "")[:10]


def _alter_tage(datum: str, heute: str) -> int | None:
    try:
        jahr, monat, tag = (int(x) for x in datum.split("-"))
        heute_d = date.fromisoformat(heute)
        return (heute_d - date(jahr, monat, tag)).days
    except (TypeError, ValueError):
        return None


def _cornerstone_wert(fm: dict) -> tuple[bool, str | None]:
    """(ist_cornerstone, fehler).

    `cornerstone: "ja"` ist kein Wahrheitswert, sondern ein Datenfehler:
    Hugo wertet den String als wahr, jede Auswertung hier würde ihn aber
    anders lesen als der Build. Deshalb meldet C1 das ausdrücklich.
    """
    if FELD not in fm:
        return False, None
    wert = fm[FELD]
    if isinstance(wert, bool):
        return wert, None
    if isinstance(wert, str) and wert.strip().lower() in ("true", "ja", "yes", "1"):
        return True, f"`{FELD}: \"{wert}\"` ist ein String – bitte als Boolean schreiben (true)."
    if isinstance(wert, str) and wert.strip().lower() in ("false", "nein", "no", "0"):
        return False, f"`{FELD}: \"{wert}\"` ist ein String – bitte als Boolean schreiben (false)."
    return False, f"`{FELD}: {wert!r}` ist kein Wahrheitswert."


def sammle(root: str) -> list[str]:
    dateien: list[str] = []
    for muster in DATEIEN:
        dateien += glob.glob(os.path.join(root, muster))
    return sorted(p for p in set(dateien) if os.path.basename(p) not in SKIP)


def pruefe(root: str = BLOG_DIR, min_eingehend: int = MIN_EINGEHEND,
           max_alter: int = MAX_ALTER_TAGE, heute: str | None = None) -> dict:
    """Bewertet alle Artikel gegen die Cornerstone-Regeln (ohne Schreibzugriff)."""
    heute = heute or os.environ.get("FF_HEUTE") or date.today().isoformat()
    seiten: dict[str, dict] = {}
    for pfad in sammle(root):
        with open(pfad, encoding="utf-8") as fh:
            text = fh.read()
        fm, body = split_frontmatter(text)
        if not fm:
            continue
        slug = _slug(pfad)
        ist_cs, fehler = _cornerstone_wert(fm)
        seiten[slug] = {
            "slug": slug,
            "datei": os.path.relpath(pfad, root),
            "titel": str(fm.get("title") or ""),
            "pillar": str(fm.get("pillar") or ""),
            "live": ist_live(fm, heute),
            "cornerstone": ist_cs,
            "flag_fehler": fehler,
            "datum": _datum(fm),
            "alter_tage": _alter_tage(_datum(fm), heute),
            "fokus": parse_fokus(fm),
            "hat_kurzantwort": bool(str(fm.get("kurzantwort") or "").strip()),
            "hat_quellen": bool(fm.get("quellen")),
            "hat_cover_alt": bool((fm.get("cover") or {}).get("alt")) if isinstance(fm.get("cover"), dict) else False,
            "ziele": sorted(links_im_body(body)),
            "eingehend": 0,
            "quellen_pillars": set(),
        }

    # Linkgraph: wer verweist auf wen – Selbstverweise zählen nicht.
    for slug, seite in seiten.items():
        for ziel in seite["ziele"]:
            if ziel == slug or ziel not in seiten:
                continue
            seiten[ziel]["eingehend"] += 1
            seiten[ziel]["quellen_pillars"].add(seite["pillar"] or "—")

    befunde: list[dict] = []
    kandidaten: list[dict] = []

    def add(seite: dict, regel: str, schwere: str, text: str, massnahme: str) -> None:
        befunde.append({"slug": seite["slug"], "datei": seite["datei"], "regel": regel,
                        "schwere": schwere, "text": text, "massnahme": massnahme})

    for slug in sorted(seiten):
        seite = seiten[slug]
        if seite["flag_fehler"]:
            add(seite, "C1", "P2", seite["flag_fehler"],
                f"`{FELD}: true` (Boolean) schreiben – sonst liest der Build den Wert anders als diese Prüfung.")
        if not seite["cornerstone"]:
            if seite["live"] and seite["eingehend"] >= min_eingehend:
                kandidaten.append({
                    "slug": slug, "datei": seite["datei"], "titel": seite["titel"],
                    "eingehend": seite["eingehend"],
                    "pillars": sorted(seite["quellen_pillars"]),
                    "yaml": f"{FELD}: true",
                })
            continue
        if not seite["live"]:
            add(seite, "C2", "P1", "Cornerstone ist nicht veröffentlicht (Draft/Zukunft/abgelaufen).",
                "Live stellen oder die Markierung entfernen – ein unsichtbarer Cornerstone trägt nichts.")
        if seite["eingehend"] < min_eingehend:
            add(seite, "C3", "P1",
                f"Nur {seite['eingehend']} eingehende interne Links (Soll: {min_eingehend}).",
                "Aus thematisch passenden Artikeln verlinken; der Linker schlägt Ziele vor "
                "(`python3 scripts/link_vorschlaege.py`).")
        if seite["alter_tage"] is None:
            add(seite, "C4", "P2", "Kein verwertbares Datum (date/lastmod).",
                "ISO-Datum im Frontmatter setzen – sonst ist die Frische nicht prüfbar.")
        elif seite["alter_tage"] > max_alter:
            add(seite, "C4", "P2",
                f"Seit {seite['alter_tage']} Tagen nicht aktualisiert (Soll: ≤ {max_alter}).",
                "Zahlen, Quellen und Preise prüfen und lastmod setzen – Cornerstones altern sichtbar.")
        if not seite["fokus"]:
            add(seite, "C5", "P2", "Keine Hauptintention (`keywords_fokus`) benannt.",
                "Ein bis drei Begriffe eintragen, wichtigster zuerst "
                "(`python3 scripts/fokus_keywords.py --vorschlag`).")
        if not seite["hat_kurzantwort"]:
            add(seite, "C5", "P2", "Keine Kurzantwort im Frontmatter.",
                "`kurzantwort` setzen – sie ist die Antwort, die Leser und Suchmaschine zuerst sehen.")
        if not seite["hat_quellen"]:
            add(seite, "C5", "P2", "Keine Quellen im Frontmatter.",
                "`quellen` mit Herausgeber, Titel und Datum belegen (E-E-A-T).")
        if not seite["hat_cover_alt"]:
            add(seite, "C5", "P2", "Cover ohne Alt-Text.",
                "`cover.alt` beschreibt den Inhalt des Bildes, nicht den Titel.")
        if len(seite["quellen_pillars"]) < 2:
            add(seite, "C6", "P3",
                f"Eingehende Links stammen aus {len(seite['quellen_pillars'])} Themenwelt(en).",
                "Prüfen, ob der Artikel auch außerhalb seiner Themenwelt gebraucht wird – "
                "kein Muss, aber ein Signal für Reichweite.")

    kandidaten.sort(key=lambda k: (-k["eingehend"], k["slug"]))
    for seite in seiten.values():
        seite["quellen_pillars"] = sorted(seite["quellen_pillars"])
    return {"heute": heute, "min_eingehend": min_eingehend, "max_alter": max_alter,
            "seiten": seiten, "befunde": befunde, "kandidaten": kandidaten[:KANDIDATEN_MAX]}


def bericht_md(stand: dict) -> str:
    markiert = [s for s in stand["seiten"].values() if s["cornerstone"]]
    zeilen = [
        "# Cornerstone-Inhalte – Bericht", "",
        f"Stand: {stand['heute']} · markiert: {len(markiert)} · "
        f"Befunde: {len(stand['befunde'])} · Kandidaten: {len(stand['kandidaten'])}", "",
        "Ein Cornerstone ist ein Bekenntnis mit Folgen: viel verlinkt, frisch, "
        "vollständig belegt. Die Markierung selbst setzt diese Wache nicht.", "",
    ]
    if markiert:
        zeilen += ["## Markierte Cornerstones", "",
                   "| Seite | Eingehend | Alter (Tage) | Hauptintention |",
                   "|---|---|---|---|"]
        for s in sorted(markiert, key=lambda x: -x["eingehend"]):
            zeilen.append(f"| `{s['slug']}` | {s['eingehend']} | "
                          f"{s['alter_tage'] if s['alter_tage'] is not None else '–'} | "
                          f"{s['fokus'][0] if s['fokus'] else '–'} |")
        zeilen.append("")
    if stand["befunde"]:
        zeilen += ["## Befunde", ""]
        for b in sorted(stand["befunde"], key=lambda x: (x["schwere"], x["datei"], x["regel"])):
            zeilen += [f"### {b['datei']} · {b['regel']} ({b['schwere']})",
                       f"- **Befund:** {b['text']}",
                       f"- **Maßnahme:** {b['massnahme']}", ""]
    if stand["kandidaten"]:
        zeilen += ["## Kandidaten (Vorschlag, keine Änderung)", "",
                   "Seiten mit vielen eingehenden Links ohne Markierung. "
                   "Die Zeile ist paste-fertig.", ""]
        for k in stand["kandidaten"]:
            zeilen += [f"### {k['slug']} ({k['eingehend']} eingehende Links)",
                       f"- {k['titel']}",
                       f"- Themenwelten der Quellen: {', '.join(k['pillars']) or '–'}",
                       f"- Frontmatter: `{k['yaml']}`", ""]
    if not markiert:
        zeilen += ["Hinweis: Es ist noch kein Artikel markiert. Ohne Markierung "
                   "prüft diese Wache nichts – sie schlägt aber Kandidaten vor.", ""]
    return "\n".join(zeilen) + "\n"


def selftest() -> int:
    """Baut ein Mini-Repo im Temp-Verzeichnis und spielt jede Regel durch."""
    import tempfile
    fails: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        def schreibe(name: str, text: str) -> None:
            ordner = os.path.join(tmp, "content", "posts", name)
            os.makedirs(ordner, exist_ok=True)
            with open(os.path.join(ordner, "index.md"), "w", encoding="utf-8") as fh:
                fh.write(text)

        def artikel(titel: str, links: str = "", *, extra: str = "", datum: str = "2026-10-01",
                    draft: bool = False, pillar: str = "strom") -> str:
            return (f'---\ntitle: "{titel}"\ndescription: "Beschreibung"\ndate: {datum}\n'
                    f'lastmod: {datum}\ndraft: {"true" if draft else "false"}\n'
                    f'pillar: "{pillar}"\n{extra}---\n\nText.\n\n{links}\n')

        gut = ('keywords_fokus: ["strom sparen"]\n'
               'kurzantwort: "Kurz."\nquellen:\n  - titel: "Q"\n    url: "https://example.org"\n'
               'cover:\n  image: "x.jpg"\n  alt: "Alt"\n')
        schreibe("cs-gut", artikel("Gut", extra=gut + "cornerstone: true\n"))
        for i in range(5):
            schreibe(f"quelle-{i}", artikel(f"Quelle {i}",
                                            links="[Gut](/posts/cs-gut/) [X](../../posts/cs-gut/)",
                                            pillar="strom" if i < 2 else "konto"))
        schreibe("cs-zu-wenig", artikel("Wenig", extra=gut + "cornerstone: true\n"))
        schreibe("cs-alt", artikel("Alt", links="[Alt](/posts/cs-alt/)",
                                   extra=gut + "cornerstone: true\n", datum="2025-01-01"))
        schreibe("cs-unvollstaendig", artikel("Unvollständig",
                                              links="[U](/posts/cs-unvollstaendig/)",
                                              extra="cornerstone: true\n"))
        schreibe("cs-draft", artikel("Entwurf", extra="cornerstone: true\n", draft=True))
        schreibe("cs-string", artikel("String", links="[S](/posts/cs-string/)",
                                      extra='cornerstone: "ja"\n'))
        schreibe("cs-eine-welt", artikel("Eng", links="[E](/posts/cs-eine-welt/)",
                                         extra=gut + "cornerstone: true\n"))
        # Ein Selbstverweis darf nicht als eingehender Link zählen.
        for i in range(4):
            schreibe(f"selbst-{i}", artikel("Selbst", links="[S](/posts/cs-eine-welt/)"))
        # Kandidat: nicht markiert, aber fünf eingehende Links.
        schreibe("cs-kandidat", artikel("Kandidat"))
        for i in range(5):
            schreibe(f"kandidat-quelle-{i}", artikel(f"Kandidat-Quelle {i}",
                                                    links="[K](/posts/cs-kandidat/)"))

        stand = pruefe(tmp, heute="2026-10-28")
        regeln = {(b["slug"], b["regel"]) for b in stand["befunde"]}
        erwartet = {("cs-zu-wenig", "C3"), ("cs-alt", "C4"),
                    ("cs-unvollstaendig", "C5"), ("cs-draft", "C2"),
                    ("cs-string", "C1")}
        fehlend = erwartet - regeln
        if fehlend:
            fails.append(f"Regeln lösen nicht aus: {sorted(fehlend)}")
        if ("cs-gut", "C3") in regeln:
            fails.append("sauberer Cornerstone wird als zu wenig verlinkt gemeldet")
        if any(r == "C1" and s != "cs-string" for s, r in regeln):
            fails.append("C1 meldet Seiten ohne String-Flag")
        if any(b["slug"] == "cs-gut" and b["regel"] in ("C2", "C4") for b in stand["befunde"]):
            fails.append("sauberer Cornerstone verletzt C2/C4")
        # C6: „cs-eine-welt" hat 4 eingehende Links aus derselben Quelle –
        # der Selbstverweis zählt nicht, deshalb C3 UND C6.
        if ("cs-eine-welt", "C6") not in regeln:
            fails.append("C6 (nur eine Themenwelt) löst nicht aus")
        if stand["seiten"]["cs-eine-welt"]["eingehend"] != 4:
            fails.append(f"eingehende Links falsch gezählt: {stand['seiten']['cs-eine-welt']['eingehend']}")
        # Kandidaten: viele eingehende Links, keine Markierung
        kandidaten = {k["slug"] for k in stand["kandidaten"]}
        if "cs-kandidat" not in kandidaten:
            fails.append("Seite mit 5 eingehenden Links wird nicht als Kandidat vorgeschlagen")
        if "cs-zu-wenig" in kandidaten:
            fails.append("Seite ohne eingehende Links wird als Kandidat vorgeschlagen")
        if "cs-gut" in kandidaten:
            fails.append("bereits markierter Artikel als Kandidat vorgeschlagen")
        # Drafts werden nie als Kandidat vorgeschlagen.
        if any(k["slug"] == "cs-draft" for k in stand["kandidaten"]):
            fails.append("Draft als Kandidat vorgeschlagen")
        md = bericht_md(stand)
        if "paste-fertig" not in md and stand["kandidaten"]:
            fails.append("Bericht nennt keine paste-fertige Zeile")
        if "Bekenntnis mit Folgen" not in md:
            fails.append("Bericht erklärt die Tragweite der Markierung nicht")
        # Die Prüfung darf nichts schreiben.
        # Schlüssel mit Pfad: alle Dateien heißen index.md – ein Dict über
        # Dateinamen würde kollabieren und den Test wertlos machen.
        def stand_dateien() -> dict:
            return {os.path.join(dp, p): os.path.getmtime(os.path.join(dp, p))
                    for dp, _, fs in os.walk(tmp) for p in fs}
        vorher = stand_dateien()
        pruefe(tmp, heute="2026-10-28")
        nachher = stand_dateien()
        if vorher != nachher:
            fails.append("Prüfung hat Dateien verändert")
    if fails:
        for f in fails:
            print(f"❌ Cornerstone: {f}")
        return 2
    print("✅ Cornerstone: Selbsttest bestanden – Flag-Typ, Veröffentlichung, "
          "eingehende Links, Frische, Vollständigkeit, Breite und Kandidaten sind belegt.")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--md", metavar="PFAD", help="Markdown-Bericht schreiben")
    parser.add_argument("--kandidaten", action="store_true", help="nur Kandidaten ausgeben")
    parser.add_argument("--min-eingehend", type=int, default=MIN_EINGEHEND)
    parser.add_argument("--max-alter", type=int, default=MAX_ALTER_TAGE)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--root", default=BLOG_DIR)
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    if args.json or args.kandidaten:
        with contextlib.redirect_stdout(sys.stderr):
            if selftest() != 0:
                return 2
    elif selftest() != 0:
        return 2

    stand = pruefe(args.root, args.min_eingehend, args.max_alter)
    if args.md:
        ziel = os.path.abspath(args.md)
        os.makedirs(os.path.dirname(ziel) or ".", exist_ok=True)
        with open(ziel, "w", encoding="utf-8") as fh:
            fh.write(bericht_md(stand))
        print(f"Bericht: {ziel}")
    if args.kandidaten:
        print(json.dumps(stand["kandidaten"], ensure_ascii=False, indent=2))
        return 0
    if args.json:
        print(json.dumps({k: v for k, v in stand.items() if k != "seiten"} |
                         {"seiten": {s: {kk: vv for kk, vv in d.items() if kk not in ("ziele",)}
                                     for s, d in stand["seiten"].items()}},
                         ensure_ascii=False, indent=2))
    else:
        for b in sorted(stand["befunde"], key=lambda x: (x["schwere"], x["datei"], x["regel"])):
            print(f"  [{b['regel']}/{b['schwere']}] {b['datei']}: {b['text']}")
        markiert = sum(1 for s in stand["seiten"].values() if s["cornerstone"])
        print(f"Cornerstone: {markiert} markiert, {len(stand['befunde'])} Befunde, "
              f"{len(stand['kandidaten'])} Kandidaten.")
    return 1 if any(b["schwere"] in ("P1", "P2") for b in stand["befunde"]) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
