#!/usr/bin/env python3
"""Interne Linkvorschläge als Vorschlagsliste (28.10.2026).

WARUM DIESE DATEI EXISTIERT
===========================
`scripts/internal_linker.py --apply` schreibt Links direkt in Artikel. Das
ist für die Automatik richtig, für Redaktion falsch: Wer 300 Vorschläge
bekommt, davon 3 geschrieben, hat 297 ungeprüfte Änderungen im Rücken.
Yoast Premium zeigt Vorschläge – und schreibt sie nicht.

Dieses Werkzeug ist die Vorschlagsliste: es liest denselben Korpus, nutzt
dieselben Anker-Kandidaten, dieselben Sperrzonen (Shortcodes, Code,
Überschriften, bestehende Links, CTA-/Offenlegungsblöcke) wie der Linker –
und SCHREIBT NICHTS. Ausgabe sind CSV, Markdown und JSON in
`.cache/link-vorschlaege/`, mit dem fertigen Markdown-Link zum Einfügen.

KEIN ZWEITER LINKER
-------------------
Die Qualitätslogik wird nicht kopiert, sondern importiert:
`internal_linker.build_anchor_candidates`, `.find_anchor`, `.topic_overlap`,
`.load_pages`. Zwei Linker mit zwei Meinungen wären schlimmer als keiner –
sie würden abwechselnd Links setzen und entfernen (Ping-Pong, im Repo am
12.08.2026 schon einmal passiert).

WAS DIE BEWERTUNG WIRKLICH SAGT
-------------------------------
Der Score ist eine Reihenfolge für Menschen, kein Rankingfaktor:

    base (Keyword-Abdeckung des Ziels)
  + 100 × Themenüberlappung in Keywords/Tags
  + 25   Ziel hat noch keinen eingehenden Link (verwaist)
  + 10   Ziel hat höchstens zwei eingehende Links
  + 15   Ziel ist als Cornerstone markiert (`cornerstone: true`)
  + 5    Anker-Fundstelle liegt im ersten Drittel des Textes

Jeder Vorschlag trägt seine Gründe im Klartext. Wer den Score nicht
versteht, soll ihm nicht folgen müssen.

Nutzung:
    python3 scripts/link_vorschlaege.py                  # Liste erzeugen
    python3 scripts/link_vorschlaege.py --json           # auf stdout
    python3 scripts/link_vorschlaege.py --nur-verwaiste  # nur Ziele ohne Links
    python3 scripts/link_vorschlaege.py --min-score 150 --pro-artikel 5
    python3 scripts/link_vorschlaege.py --selftest

Exit: 0 immer (Vorschläge sind kein Fehler), 2 bei Eingabefehlern.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUSGABE = os.path.join(BLOG_DIR, ".cache", "link-vorschlaege")

BONUS_VERWAIST = 25
BONUS_WENIG_LINKS = 10
BONUS_CORNERSTONE = 15
BONUS_FRUEH = 5
MAX_VORSCHLAEGE = 5


def _lade_module():
    """Importiert Linker und Graph-Helfer – mit klarer Meldung statt Traceback."""
    try:
        import internal_linker as il
    except ImportError as fehler:  # pragma: no cover - Umgebung ohne PyYAML
        print(f"❌ Linkvorschläge: internal_linker nicht ladbar ({fehler}). "
              f"PyYAML ist in requirements-ci.in gepinnt.", file=sys.stderr)
        raise SystemExit(2)
    import cornerstone_wache as cw
    return il, cw


def graph() -> dict[str, dict]:
    """Eingehende Links und Cornerstone-Status je Slug.

    Absichtlich aus `cornerstone_wache`: EINE Zählung für Gate und
    Vorschlag. Zwei Zähler, die unterschiedlich zählen, erzeugen einen
    Vorschlag für ein Ziel, das die Wache gleichzeitig als verwaist meldet.
    """
    _, cw = _lade_module()
    stand = cw.pruefe(BLOG_DIR)
    return {slug: {"eingehend": seite["eingehend"],
                   "cornerstone": seite["cornerstone"],
                   "pillar": seite["pillar"],
                   "titel": seite["titel"]}
            for slug, seite in stand["seiten"].items()}


def _links(body: str) -> set[str]:
    """Bereits verlinkte Ziele – alle Linkformen, nicht nur `../../posts/`.

    Gezählt wird mit `cornerstone_wache.links_im_body`, damit Gate und
    Vorschlag dieselbe Zahl sehen (eine Zählung, zwei Werkzeuge).
    """
    import cornerstone_wache as cw
    return cw.links_im_body(body)


def bewerte(quelle: str, seite: dict, kandidaten: list, pages: dict,
            graph_: dict, *, max_vorschlaege: int = MAX_VORSCHLAEGE,
            nur_verwaiste: bool = False) -> list[dict]:
    """Vorschläge für EINEN Artikel – reine Funktion, ohne Dateizugriff.

    Getrennt vom Repo-Lauf, damit der Selbsttest die Bewertung ohne
    Dateisystem prüfen kann. `kandidaten` ist die Liste aus
    internal_linker.build_anchor_candidates.
    """
    import internal_linker as il

    body = seite["body"]
    bestand = _links(body)
    vorhandene_links = len(bestand)
    am_deckel = vorhandene_links >= il.MAX_TOTAL_PER_ARTICLE
    vorschlaege: list[dict] = []
    besetzte_ziele: set[str] = set(bestand)
    besetzte_anker: set[str] = set()
    belegte_stellen: list[tuple[int, int]] = []

    gereiht = []
    for phrase, ziel_slug, base_score in kandidaten:
        if ziel_slug == quelle or ziel_slug not in pages:
            continue
        ueberlappung = il.topic_overlap(seite, pages[ziel_slug])
        if ueberlappung == 0 and base_score < 70:
            continue  # kein thematischer Bezug – genau die Regel des Linkers
        ziel = graph_.get(ziel_slug, {})
        eingehend = ziel.get("eingehend", 0)
        if nur_verwaiste and eingehend:
            continue
        score = base_score + 100 * ueberlappung
        gruende = [f"Themenüberlappung {ueberlappung} (Keywords/Tags)" if ueberlappung
                   else "Bezug nur über den Titel (kein gemeinsames Keyword)"]
        if eingehend == 0:
            score += BONUS_VERWAIST
            gruende.append("Ziel hat noch keinen eingehenden Link")
        elif eingehend <= 2:
            score += BONUS_WENIG_LINKS
            gruende.append(f"Ziel hat {eingehend} eingehende Links")
        else:
            gruende.append(f"Ziel hat {eingehend} eingehende Links")
        if ziel.get("cornerstone"):
            score += BONUS_CORNERSTONE
            gruende.append("Ziel ist Cornerstone")
        gereiht.append((score, phrase, ziel_slug, gruende))
    gereiht.sort(key=lambda eintrag: (-eintrag[0], eintrag[1]))

    # Zwei Stufen, damit der Lauf nicht 40 Sekunden kostet:
    #  1. Grobfilter: Kommt die Phrase im Artikel überhaupt vor? Das ist ein
    #     C-schneller Teilstring-Test und wirft den Großteil der ~20.000
    #     Kandidaten (Titel-N-Gramme fremder Artikel) sofort aus.
    #  2. Feinprüfung: Nur die verbliebenen laufen durch `find_anchor`, das
    #     für jede Phrase alle Sperrzonen (Links, Code, Shortcodes, CTA)
    #     prüft – das ist der teure Teil.
    # Je Ziel werden höchstens zwei Anker geprüft; zehn Varianten desselben
    # Ziels würden sonst alle anderen Ziele aus der Liste verdrängen.
    heu = body.casefold()
    pruef_bar: list[tuple] = []
    pro_ziel: dict[str, int] = {}
    for eintrag in gereiht:
        score, phrase, ziel_slug, gruende = eintrag
        if phrase.casefold() not in heu:
            continue
        if pro_ziel.get(ziel_slug, 0) >= 2:
            continue
        pro_ziel[ziel_slug] = pro_ziel.get(ziel_slug, 0) + 1
        pruef_bar.append(eintrag)
    for score, phrase, ziel_slug, gruende in pruef_bar:
        if len(vorschlaege) >= max_vorschlaege:
            break
        if ziel_slug in besetzte_ziele or phrase in besetzte_anker:
            continue
        treffer = il.find_anchor(body, phrase)
        if not treffer:
            continue
        start, ende = treffer
        if any(start < b_ende and ende > b_start for b_start, b_ende in belegte_stellen):
            continue
        anteil = start / max(len(body), 1)
        if anteil <= 0.33:
            score += BONUS_FRUEH
            gruende = gruende + ["Anker liegt im ersten Drittel"]
        besetzte_ziele.add(ziel_slug)
        besetzte_anker.add(phrase)
        belegte_stellen.append((start, ende))
        anker_text = body[start:ende].strip()
        vorschlaege.append({
            "quelle": quelle,
            "quelle_datei": os.path.relpath(seite["path"], BLOG_DIR),
            "anker": anker_text,
            "ziel": ziel_slug,
            "ziel_titel": pages[ziel_slug]["title"],
            "ziel_url": f"/posts/{ziel_slug}/",
            "markdown": f"[{anker_text}](../../posts/{ziel_slug}/)",
            "score": score,
            "gruende": gruende,
            "eingehend_ziel": graph_.get(ziel_slug, {}).get("eingehend", 0),
            "vorhandene_links": vorhandene_links,
            "deckel_erreicht": am_deckel,
            "hinweis": ("Artikel ist am Verlinkungsdeckel – erst bestehende Links "
                        "konsolidieren, dann ergänzen." if am_deckel else ""),
        })
    return vorschlaege


def erzeuge(*, max_vorschlaege: int = MAX_VORSCHLAEGE,
            nur_verwaiste: bool = False, min_score: int = 0,
            datei: str | None = None) -> list[dict]:
    """Vorschläge für den ganzen Live-Korpus (oder genau eine Datei)."""
    il, _ = _lade_module()
    pages = il.load_pages()
    kandidaten = il.build_anchor_candidates(pages)
    graph_ = graph()
    quellen = pages
    if datei:
        quellen = il.load_single_source(datei)
        if not quellen:
            raise SystemExit(2)
    alle: list[dict] = []
    for quelle, seite in sorted(quellen.items()):
        alle += bewerte(quelle, seite, kandidaten, pages, graph_,
                        max_vorschlaege=max_vorschlaege, nur_verwaiste=nur_verwaiste)
    return [v for v in alle if v["score"] >= min_score]


# --------------------------------------------------------------------------
#  Ausgabe
# --------------------------------------------------------------------------
def schreibe_csv(vorschlaege: list[dict], ziel: str) -> None:
    import sys as _sys
    _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from seo_cockpit import safe_csv  # eine Neutralisierung für alle CSV-Exporte
    kopf = ["Quelle", "Quelldatei", "Ankertext", "Ziel-Slug", "Ziel-Titel",
            "Ziel-URL", "Markdown zum Einfügen", "Score", "Begründung",
            "Eingehende Links (Ziel)", "Links im Artikel (vorher)", "Hinweis"]
    zeilen = [kopf]
    for v in vorschlaege:
        zeilen.append([v["quelle"], v["quelle_datei"], v["anker"], v["ziel"],
                       v["ziel_titel"], v["ziel_url"], v["markdown"], v["score"],
                       "; ".join(v["gruende"]), v["eingehend_ziel"],
                       v["vorhandene_links"], v["hinweis"]])
    os.makedirs(os.path.dirname(ziel) or ".", exist_ok=True)
    with open(ziel, "w", encoding="utf-8-sig", newline="") as fh:
        fh.write(safe_csv(zeilen))


def bericht_md(vorschlaege: list[dict]) -> str:
    kopf = [
        "# Interne Linkvorschläge", "",
        f"Vorschläge: {len(vorschlaege)} · Artikel: "
        f"{len({v['quelle'] for v in vorschlaege})}", "",
        "Diese Liste ändert nichts. Der Markdown-Link ist zum Einfügen gedacht – "
        "prüfen, ob der Satz ihn trägt, dann einfügen. Ein Link, der nur der Zahl "
        "dient, ist ein schlechter Link.", "",
    ]
    aktuell = None
    for v in sorted(vorschlaege, key=lambda x: (x["quelle"], -x["score"])):
        if v["quelle"] != aktuell:
            aktuell = v["quelle"]
            kopf += [f"## {v['quelle']}", "", f"`{v['quelle_datei']}` "
                     f"· {v['vorhandene_links']} bestehende interne Links", ""]
            if v["deckel_erreicht"]:
                kopf += ["> Am Verlinkungsdeckel (9). Erst bestehende Links "
                         "konsolidieren, dann ergänzen.", ""]
        kopf += [
            f"### „{v['anker']}“ → {v['ziel_titel']}",
            f"- **Einfügen:** `{v['markdown']}`",
            f"- **Score:** {v['score']} · {'; '.join(v['gruende'])}",
            f"- **Ziel:** {v['ziel_url']} · {v['eingehend_ziel']} eingehende Links",
            "",
        ]
    if not vorschlaege:
        kopf += ["Keine Vorschläge für die gewählte Auswahl. Das heißt nicht, "
                 "dass die Verlinkung gut ist – nur, dass der Linker mit seinen "
                 "Ankerregeln nichts Passendes findet.", ""]
    return "\n".join(kopf) + "\n"


def selftest() -> int:
    """Bewertet eine synthetische Lage – ohne Dateisystem, ohne Schreibzugriff."""
    try:
        il, _ = _lade_module()
    except SystemExit:
        return 2
    fails: list[str] = []
    body = ("Ein Absatz über Tagesgeld und Zinsen.\n\n"
            "[Schon verlinkt](../../posts/schon-da/).\n\n"
            "Hier steht ein Notgroschen im Text, später noch einmal Notgroschen.\n\n"
            '{{< rechner typ="notgroschen" >}}\n')
    quelle = {"title": "Tagesgeld Ratgeber", "keywords": ["tagesgeld", "zinsen"],
              "tags": ["konto"], "body": body, "score": 60, "path": "content/posts/q/index.md"}
    pages = {
        "q": quelle,
        "schon-da": {"title": "Schon da", "keywords": ["tagesgeld"], "tags": [],
                     "body": "", "score": 50, "path": "content/posts/schon-da/index.md"},
        "notgroschen": {"title": "Notgroschen aufbauen", "keywords": ["notgroschen"],
                        "tags": ["konto"], "body": "", "score": 50,
                        "path": "content/posts/notgroschen/index.md"},
    }
    kandidaten = [
        ("tagesgeld", "schon-da", 70),      # bereits verlinkt → kein Vorschlag
        ("notgroschen", "notgroschen", 70),  # Treffer im Fließtext
        ("rechner", "notgroschen", 70),      # nur im Shortcode → gesperrt
    ]
    graph_ = {"schon-da": {"eingehend": 0, "cornerstone": False},
              "notgroschen": {"eingehend": 0, "cornerstone": True}}
    vorschlaege = bewerte("q", quelle, kandidaten, pages, graph_, max_vorschlaege=5)
    ziele = [v["ziel"] for v in vorschlaege]
    if "schon-da" in ziele:
        fails.append("bereits verlinktes Ziel wird vorgeschlagen")
    if "notgroschen" not in ziele:
        fails.append("freies Fließtext-Ziel fehlt")
    if any(v["anker"].lower().startswith("rechner") for v in vorschlaege):
        fails.append("Shortcode-Parameter als Anker vorgeschlagen")
    if any(v["ziel"] == "q" for v in vorschlaege):
        fails.append("Selbstverlinkung vorgeschlagen")
    notgroschen = next(v for v in vorschlaege if v["ziel"] == "notgroschen")
    if notgroschen["markdown"] != "[Notgroschen](../../posts/notgroschen/)":
        fails.append(f"Markdown falsch: {notgroschen['markdown']}")
    if not any("Cornerstone" in g for g in notgroschen["gruende"]):
        fails.append("Cornerstone-Bonus fehlt in den Gründen")
    if not any("eingehenden Link" in g for g in notgroschen["gruende"]):
        fails.append("Verwaist-Bonus fehlt in den Gründen")
    # Deckel: viele bestehende Links → Hinweis, aber kein stiller Vorschlag
    voll = {"title": "Voll", "keywords": ["notgroschen"], "tags": [],
            "body": "\n\n".join(f"[a{i}](../../posts/z{i}/)" for i in range(9))
                    + "\n\nEin Notgroschen im Text.\n",
            "score": 50, "path": "content/posts/voll/index.md"}
    am_deckel = bewerte("voll", voll, [("notgroschen", "notgroschen", 70)],
                        {**pages, "voll": voll}, graph_)
    if not am_deckel or not am_deckel[0]["deckel_erreicht"]:
        fails.append("Deckel-Hinweis fehlt bei 9 bestehenden Links")
    if am_deckel and not am_deckel[0]["hinweis"]:
        fails.append("Deckel-Hinweis ist leer")
    # Begrenzung greift
    viele = [("notgroschen", "notgroschen", 70), ("tagesgeld", "schon-da", 70)]
    begrenzt = bewerte("q", quelle, viele, pages, graph_, max_vorschlaege=1)
    if len(begrenzt) > 1:
        fails.append("max_vorschlaege wird nicht eingehalten")
    # Verwaist-Filter
    nur_verwaist = bewerte("q", quelle, kandidaten, pages,
                           {"notgroschen": {"eingehend": 4, "cornerstone": False}},
                           nur_verwaiste=True)
    if nur_verwaist:
        fails.append("--nur-verwaiste schlägt Ziel mit eingehenden Links vor")
    # CSV: Formel-Injektion wird neutralisiert, Markdown bleibt erhalten
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        ziel = os.path.join(tmp, "v.csv")
        boese = dict(notgroschen, anker="=HYPERLINK(\"http://x\")")
        schreibe_csv([boese], ziel)
        with open(ziel, encoding="utf-8-sig") as fh:
            inhalt = fh.read()
        if "'=HYPERLINK" not in inhalt:
            fails.append("CSV neutralisiert Formel-Anfänge nicht")
        if not os.path.exists(os.path.join(tmp, "v.csv")):
            fails.append("CSV wurde nicht geschrieben")
        md = bericht_md([notgroschen])
        if "../../posts/notgroschen/" not in md:
            fails.append("Markdown-Bericht enthält den Link nicht")
        if "Diese Liste ändert nichts" not in md:
            fails.append("Bericht nennt seine Wirkungslosigkeit nicht")
    if fails:
        for f in fails:
            print(f"❌ Linkvorschläge: {f}")
        return 2
    print("✅ Linkvorschläge: Selbsttest bestanden – Sperrzonen, Selbstverlinkung, "
          "Deckel, Begrenzung, Verwaist-Filter, Bewertungsgründe und CSV-Sicherheit "
          "sind belegt. Der Lauf schreibt ausschließlich nach .cache/.")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pro-artikel", type=int, default=MAX_VORSCHLAEGE)
    parser.add_argument("--nur-verwaiste", action="store_true")
    parser.add_argument("--min-score", type=int, default=0)
    parser.add_argument("--datei", help="nur Vorschläge für eine Datei")
    parser.add_argument("--output", default=AUSGABE, help="Ausgabeverzeichnis")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    if args.json:
        with contextlib.redirect_stdout(sys.stderr):
            if selftest() != 0:
                return 2
    elif selftest() != 0:
        return 2

    vorschlaege = erzeuge(max_vorschlaege=args.pro_artikel,
                          nur_verwaiste=args.nur_verwaiste,
                          min_score=args.min_score, datei=args.datei)
    if args.json:
        print(json.dumps(vorschlaege, ensure_ascii=False, indent=2))
        return 0
    ausgabe = os.path.abspath(args.output)
    for unsicher in ("public", "static", "content", "layouts", ".git"):
        if ausgabe == os.path.join(BLOG_DIR, unsicher) or \
                ausgabe.startswith(os.path.join(BLOG_DIR, unsicher) + os.sep):
            print(f"❌ Ausgabe gehört nicht in {unsicher}/.", file=sys.stderr)
            return 2
    os.makedirs(ausgabe, exist_ok=True)
    schreibe_csv(vorschlaege, os.path.join(ausgabe, "vorschlaege.csv"))
    with open(os.path.join(ausgabe, "bericht.md"), "w", encoding="utf-8") as fh:
        fh.write(bericht_md(vorschlaege))
    with open(os.path.join(ausgabe, "vorschlaege.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(vorschlaege, ensure_ascii=False, indent=2) + "\n")
    artikel = len({v["quelle"] for v in vorschlaege})
    print(f"Linkvorschläge: {len(vorschlaege)} Vorschläge für {artikel} Artikel.")
    print(f"Öffnen: {os.path.join(ausgabe, 'bericht.md')}")
    print("Nichts geschrieben außerhalb von .cache/ – Einfügen bleibt Handarbeit.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
