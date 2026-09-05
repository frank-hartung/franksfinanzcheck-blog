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
    1. AUSSPRACHE — dieselben Beispieltexte durch die JavaScript- und die
       Python-Normalisierung (Zahlen, Währungen, Daten, Zeiten, Bereiche,
       Einheiten, Abkürzungen, URLs, Symbole).
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
# 1 · Aussprache-Beispiele (DE & EN)
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
    ("Save $1,200", "en"),
    ("about 20%", "en"),
    ("e. g. gas", "en"),
    ("e.g. gas", "en"),
    ("tariffs etc.", "en"),
    ("20,000 kWh", "en"),
    ("on 02/01/2006", "en"),
    ("gas & oil", "en"),
    ("Switching saves money.", "en"),
]

# ---------------------------------------------------------------------------
# 1b · Wortlauf-Beispiele (Sprachwechsel mitten im Satz)
# ---------------------------------------------------------------------------

RUN_SAMPLES = [
    # Finanz-Englisch im deutschen Satz — jeder Lauf eigene Stimme
    ("Ein Robo Advisor nutzt Compound Interest und Cost Averaging.", "de"),
    ("Der Cashflow kommt jeden Monat.", "de"),
    ("Mit Buy and Hold bleibst du entspannt.", "de"),
    ("Das nennt man Side Hustles.", "de"),
    ("Wer seinen Emergency Fund aufbaut, schläft besser.", "de"),
    ("Trading kostet Gebühren.", "de"),
    # Scheinfreunde und Fehlwechsel-Vermeidung
    ("Was hat er damit gemeint?", "de"),
    ("Die Waschmaschine läuft im Fast Mode.", "de"),
    ("Der Tarifwechsel spart im Schnitt 300 Euro bis 800 Euro pro Jahr.", "de"),
    ("Tarifwechsel als größter Hebel: Ein Wechsel dauert weniger als zehn Minuten.", "de"),
    # Deutsche Einschübe in englischen Artikeln
    ("Switching your tariff can save money, und die Versicherung kostet mehr.", "en"),
    ("Compare your insurance costs every year before you switch.", "en"),
    # Reinsprachige Sätze bleiben unangetastet
    ("Der Wechsel lohnt sich für jeden Haushalt.", "de"),
    ("This sentence is clearly English and must be spoken by the English male voice.", "en"),
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
        "runs": [{"text": t, "lang": l} for t, l in RUN_SAMPLES],
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

    # ---------- 1b · Wortlauf-Regie (Sprachwechsel im Satz) ----------
    js_runs = answer.get("runs", [])
    check("Wortlauf-Fühler liefert Ergebnisse", len(js_runs) == len(RUN_SAMPLES),
          "%d von %d" % (len(js_runs), len(RUN_SAMPLES)))
    for i, (text, lang) in enumerate(RUN_SAMPLES):
        if i >= len(js_runs):
            break
        py_segs = gen.language_runs(text, lang)
        py_view = [{"text": s["text"], "lang": s["lang"]} for s in py_segs]
        # Vertrag 1: identische Segmentierung
        check("Wortläufe gleich: %r (%s)" % (text[:38], lang),
              py_view == js_runs[i],
              "Python %s vs. JS %s" % (py_view, js_runs[i]))
        # Vertrag 2: Segmente konkatenieren exakt zum Eingabetext
        check("Wortläufe konkatenieren exakt: %r" % text[:38],
              "".join(s["text"] for s in py_view) == text,
              "Konkatenation verletzt")

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
    check("Pillar: Wortlauf im Listenpunkt vertont Robo-frei deutsch",
          all(gen.language_runs(b["text"], b["lang"]) for b in pillar_py),
          "Leere Wortlauf-Segmentierung")

    failed = [(n, d) for n, ok, d in results if not ok]
    for name, detail in failed[:25]:
        print("  ✗ %s%s" % (name, (" — " + detail) if detail else ""))
    total = len(results)
    print("FF-VOICE-PARITÄT – Gate: %d/%d bestanden" % (total - len(failed), total))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
