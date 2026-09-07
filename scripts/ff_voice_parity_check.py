#!/usr/bin/env python3
"""ff_voice_parity_check.py — Paritäts-Gate zwischen Tonspur und Browserstimme.

Warum dieses Gate existiert
    Derselbe Artikel wird auf zwei Wegen gesprochen:
      (a) STUDIO-TONSPUR   serverseitig erzeugt (Python)
      (b) BROWSER-ENGINE   im Gerät erzeugt (JavaScript)
    Weichen die beiden voneinander ab, klingt derselbe Artikel je nach
    Gerät anders — mal „650 Euro“, mal „650 €“, mal mit anderer Pause
    zwischen Überschrift und Fließtext. Genau das verhindert dieses Gate.

Was geprüft wird
    0. NUR-DEUTSCH — in BEIDEN Quellen verbietet das Gate jede zweite
       Sprache: keine EN-Stimmenkette, kein Sprachwechsel im Satz,
       keine EN-Aussprachetabellen (Befund 07.09.2026).
    1. AUSSPRACHE — dieselben Beispieltexte durch die JavaScript- und die
       Python-Normalisierung (Zahlen, Währungen, Daten, Zeiten, Bereiche,
       Einheiten, Abkürzungen, URLs, Symbole). Englische Beispieltexte
       bleiben enthalten: sie beweisen, dass beide Seiten sie nach
       DEUTSCHEM Regelwerk lesen, nicht englisch.
    2. BLÖCKE     — dieselbe Seiten-HTML durch collectBlocks() (JS) und
       extract_blocks() (Python). Reihenfolge, Rolle, Sprache und Text
       müssen identisch sein, sonst wandert die Live-Markierung der
       Tonspur am gesprochenen Text vorbei.
    3. PROSODIE   — die Rollenprofile in beiden Implementierungen.

Aufruf: python3 scripts/ff_voice_parity_check.py
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import ff_voice_audio as gen  # noqa: E402
import ff_voice_backends as ttb  # noqa: E402

PROBE = os.path.join(ROOT, "scripts", "ff_voice_probe.mjs")

# ---------------------------------------------------------------------------
# 1 · Aussprache-Beispiele (ein Regelwerk: deutsch)
# ---------------------------------------------------------------------------

SAMPLES = [
    ("bis zu 650 €", "de"),
    ("rund 3,5 %", "de"),
    ("rund 30%", "de"),
    ("§ 12 EnWG", "de"),
    ("12 – 24 Monate", "de"),
    ("12-24 Monate", "de"),
    ("20.000 kWh", "de"),
    ("20 000 kWh", "de"),
    ("12 ct/kWh", "de"),
    ("80 m²", "de"),
    ("1,5 Mio. €", "de"),
    ("Stand 02.01.2006", "de"),
    ("um 14:30 Uhr", "de"),
    ("um 14:00 Uhr", "de"),
    ("z. B. Strom", "de"),
    ("Strom bzw. Gas", "de"),
    ("ca. 400 Euro", "de"),
    ("Strom & Gas", "de"),
    ("1.234,56 Euro", "de"),
    ("siehe franksfinanzcheck.de", "de"),
    ("Nr. 3 und S. 12", "de"),
    ("Der Wechsel lohnt sich.", "de"),
    # Englische Texte: werden bewusst DEUTSCH behandelt (Nur-Deutsch-
    # Vertrag). Sie bleiben als Beispiele erhalten — beide Seiten müssen
    # sie identisch deutsch normalisieren.
    ("Save $1,200", "de"),
    ("about 20%", "de"),
    ("e. g. gas", "de"),
    ("e.g. gas", "de"),
    ("tariffs etc.", "de"),
    ("20,000 kWh", "de"),
    ("on 02/01/2006", "de"),
    ("gas & oil", "de"),
    ("Switching saves money.", "de"),
    # NUR-DEUTSCH-AUSSPRACHE (Befund 07.09.2026): englisch geschriebene
    # Fach- und Markenbegriffe müssen auf BEIDEN Seiten identisch in
    # deutsche Lautschreibung überführt werden — das Code-Switching der
    # Neuronalstimme darf nirgends durchschlagen.
    ("Der Service ist gut.", "de"),
    ("Im Homeoffice arbeitet es sich gut.", "de"),
    ("Der Live-Stream laeuft.", "de"),
    ("Jetzt den Download starten.", "de"),
    ("Der Newsletter kommt heute.", "de"),
    ("Zwei Apps genuegen.", "de"),
    ("Vergleich bei Check24.", "de"),
    ("Die Dienstleistung zaehlt.", "de"),
    ("Cloud und Cookie sind Begriffe.", "de"),
    ("Das Update und das Upgrade laufen.", "de"),
    ("Social Media und der Podcast.", "de"),
    ("Der Cashback und die Watchlist.", "de"),
    ("E-Mail an uns schicken.", "de"),
    ("Online und offline immer live.", "de"),
    ("Der Browser nutzt den Router.", "de"),
    # Flektionsformen (Plural/Genitiv -s, schwache Endung -n) muessen
    # BEIDSEITIG identisch gedeutscht werden (Befund 07.09.2026).
    ("Der Providers des Services ueberzeugt.", "de"),
    ("Zwei Apps und drei Updates genuegen.", "de"),
    ("Die Podcasts und Channels in den Streams.", "de"),
    ("Die Broker und Trader sowie Leads.", "de"),
    # Hochfrequenz-Fremdwoerter aus dem Content-Bestand (07.09.2026)
    ("Der Standby des Gaming-PC und das Phishing.", "de"),
    ("Privacy beim Cookieless-Tracking, Resolver und Cluster.", "de"),
    ("Excel mit Mesh-Repeater, Tools und Access-Log.", "de"),
    ("Smart Home, der Runway und der Discounter mit Banner.", "de"),
    ("Cache leeren, die Logfiles und Logs pruefen.", "de"),
    ("Der Gamer liest seine Mails als User.", "de"),
    ("Den Transfer und das Hosting beim Provider.", "de"),
]

# ---------------------------------------------------------------------------
# 1b · Wortuhr-Aligner (Grundlage der wortgenauen Leseanzeige)
# ---------------------------------------------------------------------------
# Je Paar (Sprechtext, Rohtext) müssen BEIDE Seiten dieselbe Karte
# liefern: welches rohe Wort des Artikels klingt, wenn der Sprecher das
# normalisierte Wort liest. Weicht die Karte ab, leuchtet beim Studio-Ton
# ein anderes Wort als beim Browser-Ton — genau das verhindert dieses Gate.

ALIGN_PAIRS = [
    ("bis zu 650 Euro", "bis zu 650 €"),
    ("12 bis 24 Monate", "12 – 24 Monate"),
    ("Stand 2. Januar 2006", "Stand 02.01.2006"),
    ("20.000 Kilowattstunden", "20 000 kWh"),
    ("12 Cent pro Kilowattstunde", "12 ct/kWh"),
    ("80 Quadratmeter", "80 m²"),
    ("1.500 Euro", "1.500 €"),
    ("about 20 Prozent", "about 20%"),
    ("Strom und Gas", "Strom & Gas"),
    ("Paragraph 12 EnWG", "§ 12 EnWG"),
    ("circa 400 Euro", "ca. 400 Euro"),
    ("zum Beispiel Strom", "z. B. Strom"),
    ("Erster Satz ganz normal. Zweiter auch.", "Erster Satz ganz normal. Zweiter auch."),
    ("Das Router-Modell 4 kostet 120 Euro monatlich", "Das Router-Modell 4 kostet 120 € monatlich"),
    # Fremdwort-Erweiterung (Befund 07.09.2026): die Lautschreibung muss
    # auf das rohe Fremdwort im Artikeltext zurueckgeschlagen werden —
    # auf beiden Seiten wortgleich, sonst wandert die Leseanzeige.
    ("Der sörwis ist gut", "Der Service ist gut"),
    ("Im homoffis arbeitet es sich gut", "Im Homeoffice arbeitet es sich gut"),
    ("Der leif schtrihm läuft", "Der Live-Stream läuft"),
    ("Jetzt den daunloht starten", "Jetzt den Download starten"),
    ("Der njusletter kommt heute", "Der Newsletter kommt heute"),
    ("Zwei äpps genügen", "Zwei Apps genügen"),
    ("Die klaud und das kucki sind Begriffe", "Die Cloud und das Cookie sind Begriffe"),
]


# ---------------------------------------------------------------------------
# 2 · Seiten-Fixtures für die Block-Parität
# ---------------------------------------------------------------------------

PAGE_FIXTURE = gen.FIXTURE

PAGE_TABLE = """<!doctype html><html lang="de"><body>
<article class="post-content">
<h2 id="a">Erster Abschnitt</h2>
<p>Der Arbeitspreis liegt bei 12 ct/kWh und spart bis zu 650 € im Jahr.</p>
<div class="ff-tarifvergleich">
<h3 class="ff-tv-title">Tarife im Vergleich</h3>
<p class="ff-tv-sub">Stand 02.01.2006</p>
<div class="ff-tv-tablewrap"><table>
<thead><tr><th>Tarif</th><th>Preis</th></tr></thead>
<tbody><tr><td>Basis</td><td>1.200 €</td></tr>
<tr><td>Komfort</td><td>980 €</td></tr></tbody>
<tfoot><tr><td>Summe</td><td>2.180 €</td></tr></tfoot>
</table></div>
<div class="ff-tv-cards"><p>Dieselbe Tabelle als Kartenstapel</p></div>
<div class="ff-tv-footnote"><strong>Hinweis:</strong> Alle Angaben ohne Gewähr.</div>
</div>
<p><strong>Merksatz: Prüfe die Laufzeit genau.</strong></p>
<blockquote>Ein Zitat aus der Branche.</blockquote>
<ul><li>Arbeitspreis</li><li>Grundpreis</li></ul>
</article>
<script type="application/json" id="ff-voice-config">{"title":"Tarife","lang":"de","readingTime":6,"description":""}</script>
</body></html>"""

PAGE_EN = """<!doctype html><html lang="en"><body>
<article class="post-content">
<h2 id="a">Save money on energy</h2>
<p>Switching your tariff can save you about 20% every year on your costs.</p>
<h3>The three parts</h3>
<ol><li>Unit price</li><li>Base price</li></ol>
</article>
<script type="application/json" id="ff-voice-config">{"title":"Save money","lang":"en","readingTime":4,"description":""}</script>
</body></html>"""

# Tabellen-Härtfälle der Premium-Generation (Markdown-Wrapper, ARIA-Grid,
# colspan/rowspan, Summenzeile im tbody, Werbelink-Zeile, small-Ziertext).
PAGE_TABLES_PREMIUM = gen.FIXTURE_TABLES

# Reproduktion des Doppel-Lesers auf /pillar/strom-sparen/ (Befund vom
# 05.09.2026): Fettdruck-Lead-ins in Listenpunkten und Absätzen durften
# nie als eigener Merksatz-Zweiblock erklingen. Dieses Fixture ist die
# ABSOLUTE Prüfung — sie schlägt an, wenn BEIDE Implementierungen
# identisch falsch lesen, die Parität allein also nicht reicht.
PAGE_PILLAR = """<!doctype html><html lang="de"><body>
<article class="post-content">
<h3 id="das-wichtigste">Das Wichtigste auf einen Blick</h3>
<ul>
<li><strong>Tarifwechsel als größter Hebel:</strong> Ein Wechsel des Strom- oder Gasanbieters dauert online weniger als zehn Minuten und spart im Schnitt 300&nbsp;€ bis 800&nbsp;€ pro Jahr.</li>
<li><strong>Heimliche Stromfresser eliminieren:</strong> Standby-Geräte, veraltete Kühltechnik und Dauerverbraucher verursachen bis zu 20&nbsp;% deiner jährlichen Stromrechnung.</li>
</ul>
<p><strong>Februar.</strong> Jahresabrechnung lesen. Verbrauch, Preis, Abschlag.</p>
<p>👉 <strong>Jetzt aktuellen Stromtarif prüfen und sparen:</strong> <a href="/go/strom/"><strong>→ Jetzt Stromtarife vergleichen</strong></a></p>
<p><strong>Merksatz: Prüfe die Laufzeit genau.</strong></p>
</article>
<script type="application/json" id="ff-voice-config">{"title":"Strom und Gas sparen","lang":"de","readingTime":8,"description":""}</script>
</body></html>"""

PAGES = [PAGE_FIXTURE, PAGE_TABLE, PAGE_EN, PAGE_TABLES_PREMIUM, PAGE_PILLAR]


def run_probe():
    payload = json.dumps({
        "samples": [{"text": t, "lang": l} for t, l in SAMPLES],
        "aligns": [{"norm": n, "raw": r} for n, r in ALIGN_PAIRS],
        "pages": [{"html": h} for h in PAGES],
    }, ensure_ascii=False)
    proc = subprocess.run(["node", PROBE], input=payload.encode("utf-8"),
                          capture_output=True, timeout=300, cwd=ROOT)
    if proc.returncode != 0:
        raise RuntimeError("Probe fehlgeschlagen: %s"
                           % proc.stderr.decode("utf-8", "replace")[:400])
    return json.loads(proc.stdout.decode("utf-8"))


def main() -> int:
    results = []

    def check(name, cond, detail=""):
        results.append((name, bool(cond), detail))

    try:
        answer = run_probe()
    except Exception as exc:
        print("  ✗ Paritäts-Fühler nicht ausführbar: %s" % exc)
        print("FF-VOICE-PARITÄT – Selbsttest: 0/1 bestanden")
        return 1

    # ---------- 1 · Aussprache ----------
    js_norm = answer.get("normalized", [])
    check("Fühler liefert Ergebnisse", len(js_norm) == len(SAMPLES),
          "%d von %d" % (len(js_norm), len(SAMPLES)))
    for i, (text, lang) in enumerate(SAMPLES):
        if i >= len(js_norm):
            break
        py_norm = ttb.normalize_speech(text, lang)
        check("Aussprache gleich: %r (%s)" % (text[:34], lang),
              py_norm == js_norm[i],
              "Python %r vs. JS %r" % (py_norm, js_norm[i]))

    # ---------- 1b · Wortuhr-Aligner (Leseanzeige-Brücke) ----------
    js_aligns = answer.get("aligns", [])
    check("Aligner-Fühler liefert Ergebnisse", len(js_aligns) == len(ALIGN_PAIRS),
          "%d von %d" % (len(js_aligns), len(ALIGN_PAIRS)))
    for i, (norm_t, raw_t) in enumerate(ALIGN_PAIRS):
        py_map = gen.align_norm_to_raw(gen.norm_tokens(norm_t), gen.norm_tokens(raw_t))
        check("Kartenlänge = Wortzahl: %r" % norm_t[:28], len(py_map) == len(gen.norm_tokens(norm_t)))
        if i >= len(js_aligns):
            continue
        js_map = js_aligns[i]
        check("Wortuhr-Karte gleich: %r → %r" % (norm_t[:28], raw_t[:28]),
              [int(x) for x in py_map] == [int(x) for x in js_map],
              "Python %s vs. JS %s" % (list(py_map), list(js_map)))

    # ---------- 2 · Blöcke ----------
    js_pages = answer.get("pages", [])
    check("Alle Seiten verarbeitet", len(js_pages) == len(PAGES))
    for pi, html in enumerate(PAGES):
        root = gen.parse_html(html)
        cfg = gen.read_reader_config(root)
        py_blocks, _lang = gen.extract_blocks(root, cfg)
        py_simple = [{"lang": b["lang"], "type": b["type"], "text": b["text"]} for b in py_blocks]
        js_simple = js_pages[pi] if pi < len(js_pages) else []
        check("Seite %d: gleiche Blockzahl" % (pi + 1), len(py_simple) == len(js_simple),
              "Python %d vs. JS %d" % (len(py_simple), len(js_simple)))
        for bi in range(min(len(py_simple), len(js_simple))):
            a, b = py_simple[bi], js_simple[bi]
            check("Seite %d · Block %d: Rolle gleich (%s)" % (pi + 1, bi + 1, a["type"]),
                  a["type"] == b["type"], "Python %s vs. JS %s" % (a["type"], b["type"]))
            check("Seite %d · Block %d: Sprache gleich" % (pi + 1, bi + 1),
                  a["lang"] == b["lang"], "Python %s vs. JS %s" % (a["lang"], b["lang"]))
            check("Seite %d · Block %d: Text gleich" % (pi + 1, bi + 1),
                  a["text"] == b["text"],
                  "Python %r vs. JS %r" % (a["text"][:60], b["text"][:60]))

    # ---------- 3 · Prosodie ----------
    # Die Profile der Python-Seite müssen in der JS-Datei vorkommen.
    js_path = os.path.join(ROOT, "static", "premium", "ff-voice.js")
    with open(js_path, "r", encoding="utf-8") as fh:
        js_source = fh.read()
    for role in ("intro", "outro", "h2", "h3", "p", "li", "blockquote", "warning",
                 "table-intro", "table-row", "table-group", "table-sum",
                 "table-cta", "table-outro",
                 "overview-title", "overview-note", "emphasis"):
        # Reader-Notation: `intro:` (nackt) oder `'overview-title':` (zitiert)
        pattern = re.compile(r"^\s{2,}[\x27\"]?" + re.escape(role) + r"[\x27\"]?\s*:", re.M)
        check("Rolle „%s“ auch im Reader definiert" % role, bool(pattern.search(js_source)))

    # Harte Grenzen müssen übereinstimmen
    check("Harte Chunk-Grenze identisch",
          ("var HARD_CHUNK = %d;" % ttb.HARD_CHUNK) in js_source,
          "Python %d" % ttb.HARD_CHUNK)
    check("Referenztempo identisch",
          ("BASE_CPS = %s" % ttb.BASE_CPS) in js_source.replace("var BASE_CPS = ", "BASE_CPS = "),
          "Python %s" % ttb.BASE_CPS)

    # ---------- 4 · Doppel-Lese-Schleuse (absolut, nicht nur Parität) --
    # Der Befund vom 05.09.2026 auf /pillar/strom-sparen/: Hinter
    # „… 800 € pro Jahr“ erklang erneut „Tarifwechsel als größter
    # Hebel.“ — der Fettdruck-Lead-in wurde als zweiter Block gesprochen.
    pillar_js = js_pages[4] if len(js_pages) > 4 else []
    pillar_root = gen.parse_html(PAGE_PILLAR)
    pillar_cfg = gen.read_reader_config(pillar_root)
    pillar_py, _plang = gen.extract_blocks(pillar_root, pillar_cfg)

    LEADS = [
        "Tarifwechsel als größter Hebel",
        "Heimliche Stromfresser eliminieren",
    ]
    for lead in LEADS:
        py_hits = sum(1 for b in pillar_py if lead in b["text"])
        js_hits = sum(1 for b in pillar_js if lead in b["text"])
        check("Lead-in genau einmal: %r" % lead, py_hits == 1 and js_hits == 1,
              "Python %d×, JS %d×" % (py_hits, js_hits))
        check("Lead-in ohne Merksatz-Zweiblock: %r" % lead,
              all(b["type"] != "emphasis" or lead not in b["text"] for b in pillar_py)
              and all(b["type"] != "emphasis" or lead not in b["text"] for b in pillar_js),
              "Lead-in als eigener Fettdruck-Block")

    check("Kurzdatum im Absatz genau einmal: Februar",
          sum(1 for b in pillar_py if "Februar" in b["text"]) == 1
          and sum(1 for b in pillar_js if "Februar" in b["text"]) == 1,
          "Absatz-Lead-in doppelt")
    check("CTA-Linktext genau einmal (kein Zweiblock)",
          sum(1 for b in pillar_py if "Jetzt Stromtarife vergleichen" in b["text"]) == 1
          and sum(1 for b in pillar_js if "Jetzt Stromtarife vergleichen" in b["text"]) == 1,
          "CTA doppelt gelesen")
    check("Echter Merksatz bleibt eigener Block",
          any(b["type"] == "emphasis" and "Prüfe die Laufzeit genau" in b["text"] for b in pillar_py)
          and any(b["type"] == "emphasis" and "Prüfe die Laufzeit genau" in b["text"] for b in pillar_js),
          "Eigenständiger Merksatz wurde verschluckt")
    check("Pillar: keine Doppeltexte (Python-Join eindeutig)",
          len({b["text"] for b in pillar_py}) == len(pillar_py),
          "Doppelte Blocktexte")
    check("Pillar: jede Blocksprache ist de (Nur-Deutsch-Vertrag)",
          all(b["lang"] == "de" for b in pillar_py)
          and all(b["lang"] == "de" for b in pillar_js),
          "Fremdsprache im Pillar-Block")

    # ---------- 5 · Nur-Deutsch-Vertrag in beiden Quellen ----------
    # Harte Zeichenketten-Verbote, damit kein späterer Patch die
    # Sprachmehrgleisigkeit „nur kurz“ zurückholt.
    check("Reader: keine englische Locale-Kette", "'en-US'" not in js_source)
    check("Reader: keine Wortlauf-Regie", "languageRuns" not in js_source)
    check("Reader: keine EN-Aussprachetabelle", "MONTHS_EN" not in js_source)
    gen_path = os.path.join(ROOT, "scripts", "ff_voice_audio.py")
    with open(gen_path, "r", encoding="utf-8") as fh:
        gen_source = fh.read()
    check("Generator: keine Wortlauf-Segmentierung mehr", "def language_runs" not in gen_source)
    check("Generator: Spracherkennung liefert nur noch de",
          'return "de"' in gen_source and 'def detect_language' in gen_source)

    # ---------- 6 · Germanisierungs-Glossar (Befund 07.09.2026) ----------
    # Der Code-Switching-Fix muss in BEIDEN Quellen vorhanden sein und
    # drahtgebunden in der Normalisierung laufen — ein reines
    # Bekenntnis im Kommentar genuegt nicht.
    back_path = os.path.join(ROOT, "scripts", "ff_voice_backends.py")
    with open(back_path, "r", encoding="utf-8") as fh:
        back_source = fh.read()
    check("Generator: Germanisierungs-Glossar vorhanden",
          "_GERMANIZE_PAIRS" in back_source and "def germanize_speech" in back_source)
    check("Generator: Germanisierung ist verdrahtet",
          "germanize_speech(out)" in back_source)
    check("Generator: Wortuhr-Bruecke fuer Fremdwoerter",
          "def germanize_spoken_cores" in back_source)
    check("Reader: Germanisierungs-Glossar vorhanden",
          "GERMANIZE_PAIRS" in js_source and "function germanizeSpeech" in js_source)
    check("Reader: Germanisierung ist verdrahtet",
          "germanizeSpeech(out)" in js_source)
    check("Reader: Wortuhr-Bruecke fuer Fremdwoerter",
          "FOREIGN_SPOKEN" in js_source)
    check("Rezept-Version: Reader und Generator synchron",
          ttb.RECIPE_VERSION.split("-")[-1] in js_source,
          "Generator %s" % ttb.RECIPE_VERSION)

    failed = [(n, d) for n, ok, d in results if not ok]
    for name, detail in failed[:25]:
        print("  ✗ %s%s" % (name, (" — " + detail) if detail else ""))
    total = len(results)
    print("FF-VOICE-PARITÄT – Gate: %d/%d bestanden" % (total - len(failed), total))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
