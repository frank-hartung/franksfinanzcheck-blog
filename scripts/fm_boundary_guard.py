#!/usr/bin/env python3
"""fm_boundary_guard.py – FM-GRENZEN-WACHE (Front-Matter-Boundary-Gate, 11.09.2026)

BAUURSACHE (Fr 11.09.2026 – main rot in den Runs 34594479696, 34597633413,
34598288171; zuletzt grün in Run 34587113270 auf abfc359):
  Ein Content-Engine-Artikel schrieb die pin_description mit dem
  UWG-Prefix „*Werbung | …“ UNQUOTIERT ins Frontmatter. In YAML beginnt mit
  „*“ ein Alias → der Wert ist kein gültiges Skalar mehr. Hugo bricht ab mit
      ERROR error building site: assemble: failed to create page from
      pageMetaSource …: invalid header option: " Der Traumurlaub …"
  Der Deploy stirbt nach Sekunden im Schritt „Build (für Publish-Gate +
  Publish)“ (hugo --minify, Exit 1). ALLE nachgelagerten Stufen (Spam-Gate,
  Publish-Gate, Anker-Wache, Vorlesen, Publish, Catchup) laufen dann nicht
  mehr – der Blog bleibt auf dem Stand vor dem Fehler stehen, die
  Publish-Kette (RSS → Pinterest) trocknet aus.

GRUNDSÄTZLICH: Frontmatter ist die einzige Fehlerklasse, die den Build HART
beendet – und sie entsteht genau dort, wo Engine und Heiler Werte ZEILENWEISE
schreiben (engine_generate.yaml_quote, pin_text_sync.fm_set, spam_guard,
Meta-/Cover-Heiler). Jeder Wert mit YAML-Indikator am Anfang („*Werbung“,
„&…“, „!!tag“, „- …“) oder mit „: “ im unquotierten Text ist ein potenzieller
Build-Abbruch.

PRÜFPRINZIP (bewusst anders als die Text-Wachen):
  1) Der ganze Frontmatter-BLOCK wird geparst (Hugo-Sicht). Parsbar = RUHE.
     → keine False Positives gegen legale Konstrukte wie
       tags: ["Energie-Update: was sich ändert", …]  (Liste mit Doppelpunkt)
  2) Fehlt die Grenze oben (F1) oder unten (F2), ist der Block nicht parbar
     (F3) oder unvollständig quotiert (F4) → Zeile wird lokalisiert.
  3) GEHEILT wird nur, was nachweislich besser ist: Wert in doppelte
     YAML-Guillemets („\\“ und „"“ escaped), Block NOCHMAL geparst. Parsen
     fehlschlug und die Heilung nichts bringt → nichts wird geschrieben
     (kein Schema-Eingriff, kein Content-Verlust – eine Liste darf durch
     eine Heilung NIEMALS zu einem String werden).
  Ohne PyYAML arbeitet die Wache deterministisch nach Regelkanon (F5), heilt
  aber nur die eindeutig gefahrlosen Fälle.

KLEBER (Hinweis, nicht baukritisch): Hugo schließt das Frontmatter an der
ERSTEN Zeile ab Index 1, die mit „---“ BEGINNT – auch wenn der erste Absatz
direkt dahinterklebt („---Warum zahlen …“). Der geklebte Rest gehört dann
NICHT zum Body. Diese Wache mirrornt das Verhalten (sonst meldet jede
Kleber-Datei einen falschen Grenzfehler) und meldet den Fund nur; das
Zerlegen ist Aufgabe der Umbruch-/Casing-Wache.

AUFRUF:
  python3 scripts/fm_boundary_guard.py --selftest   # Sabotage-Schutz, Exit 2
  python3 scripts/fm_boundary_guard.py --check      # nur melden, Exit 1 bei F1–F4
  python3 scripts/fm_boundary_guard.py --fix         # heilen (konvergent)
"""
import datetime
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR = os.path.join(BLOG_DIR, "content")
REPORT = os.path.join(BLOG_DIR, "FM-GRENZEN-REPORT.md")

OPEN_RX = re.compile(r"^---[ \t]*$")
CLOSE_RX = re.compile(r"^---")            # Hugo: Schluss an „---…“ (Präfix)
TOP_KEY_RX = re.compile(r"^([A-Za-z_][A-Za-z0-9_.\-]*):[ \t]*(.*)$")
INDICATORS = ("*", "&", "!", "@", "`")

try:
    import yaml as _yaml                   # Gegenprüfung (im Deploy installiert)
except Exception:                          # pragma: no cover
    _yaml = None


# ------------------------------------------------------------------- Frontmatter
def content_files():
    """Alle Content-Quellen (posts, pillar, statische Seiten) – sortiert."""
    out = []
    for base, _dirs, names in os.walk(CONTENT_DIR):
        for name in names:
            if name.endswith((".md", ".markdown")):
                out.append(os.path.join(base, name))
    return sorted(out)


def split_fm(text):
    """(zeilen, beginn_idx, end_idx) des FM-Blocks – Hugo-Semantik.

    zeilen is None  → keine eigene ---Zeile am Dateianfang (F1)
    end_idx is None → Block nie geschlossen (F2)"""
    lines = text.split("\n")
    if not lines or not OPEN_RX.match(lines[0]):
        return None, None, None
    for i in range(1, len(lines)):
        if CLOSE_RX.match(lines[i]):
            return lines[1:i], 1, i
    return lines[1:], 1, None


def closing_glue(text):
    """Kleber-Rest der FM-Schlusszeile: '---Warum zahlen …' → 'Warum zahlen …'."""
    lines = text.split("\n")
    if not lines or not OPEN_RX.match(lines[0]):
        return ""
    for i in range(1, len(lines)):
        if CLOSE_RX.match(lines[i]):
            return lines[i][3:].strip()
    return ""


def parse_ok(block_text):
    """Block/Zeile als YAML: True/False, None = ohne PyYAML nicht prüfbar."""
    if _yaml is None:
        return None
    try:
        _yaml.safe_load(block_text)
        return True
    except Exception:
        return False


def heuristic_defects(fm_lines):
    """Regelkanon F5 (Fallback ohne PyYAML) – nur eindeutig gefährliche Form."""
    defects = []
    for idx, raw in enumerate(fm_lines):
        if not raw.strip() or raw[:1] in (" ", "\t", "#"):
            continue
        m = TOP_KEY_RX.match(raw)
        if not m:
            defects.append((idx, "F5",
                            f"Top-Level-Zeile ohne 'key:' – {raw[:60]!r}"))
            continue
        value = m.group(2).strip()
        if not value or value[0] in ("[", "{", "\"", "'", "|", ">"):
            continue                       # legal oder nur mit Parser beurteilbar
        if (value[0] in INDICATORS or value.startswith("- ")
                or ": " in value or value.endswith(":")):
            defects.append((idx, "F5",
                            "Wertform, die YAML nach Hausregeln nicht als "
                            "Plain-Scalar akzeptiert (Indikator/Sequenz/': ')"))
    return defects


def find_defects(fm_lines):
    """Baukritische Funde im Block. Liefert [(index, regel, nachricht)]."""
    if _yaml is None:
        return heuristic_defects(fm_lines)
    defects = []
    for idx, raw in enumerate(fm_lines):
        if not raw.strip() or raw[:1] in (" ", "\t", "#"):
            continue
        if not TOP_KEY_RX.match(raw):
            continue
        if parse_ok(raw + "\n") is False:
            defects.append((idx, "F3",
                            "Zeile ist kein gültiges Top-Level-YAML-Paar – "
                            "Hugo verliert hier das Frontmatter"))
    return defects


# YAML-Indikatoren am Wertanfang – ein Plain-Scalar darf mit keinem davon
# beginnen (Alias *, Anker &, Tag !, reserved @ `, Directive %, Block | >,
# Flow [ ] { }, Quote " ', Kommentar #, Block-Mapping -, Key-Grenz :).
START_INDICATORS = ("-", "?", ":", "*", "&", "!", "@", "`", "|", ">", "%",
                    "[", "]", "{", "}", '"', "'", "#", ",")


def needs_quote(value) -> bool:
    """True, wenn ein Frontmatter-Wert NICHT als Plain-Scalar sicher ist.

    Single Source of Truth für ALLE FM-Schreiber (engine_generate,
    Pin-/Meta-Heiler) – genau diese Lücke erzeugte den Build-Abbruch am
    11.09.2026: '*Werbung | …' begann mit '*' und wurde unquotiert
    geschrieben (alte Regel kannte nur ':', '#' und die Starts ' ', '-',
    '?', '!')."""
    v = "" if value is None else str(value)
    if not v or v != v.strip():
        return True
    if v[0] in START_INDICATORS:
        return True
    if ": " in v or v.endswith(":") or " #" in v or "\n" in v:
        return True
    return False


def yaml_quote(value):
    """Wert → nur falls nötig doppeltes YAML-Quote (verlustfrei).

    Das Frontmatter wird zeilenweise geschrieben – ein echter Umbruch im Wert
    würde die Folgezeilen zu YAML-Content machen. Darum wird \\n escapt."""
    if value is None:
        return '""'
    v = str(value)
    if not needs_quote(v):
        return v
    v = v.replace("\\", "\\\\").replace('"', '\\"')
    v = v.replace("\r", "").replace("\n", "\\n")
    return '"' + v + '"'


def heal_line(raw):
    """Schlüssel behalten, WERT quotieren – alles andere bleibt bytegleich."""
    m = TOP_KEY_RX.match(raw)
    if not m:
        return raw
    key, value = m.group(1), m.group(2).strip()
    if not value:
        return raw
    return f"{key}: {yaml_quote(value)}"


# ------------------------------------------------------------------- Prüfen/Heilen
def inspect(path):
    """(grenzregel, kleber, text, defects) einer Content-Datei."""
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    fm_lines, begin, end = split_fm(text)
    if fm_lines is None:
        return "F1", "", text, []
    if end is None:
        return "F2", "", text, []
    block = "\n".join(fm_lines) + "\n"
    if _yaml is not None and parse_ok(block) is True:
        return None, closing_glue(text), text, []      # Hugo-Sicht: sauber
    return None, closing_glue(text), text, find_defects(fm_lines)


def heal(path, text, defects):
    """Werte quotieren – und NUR schreiben, wenn der Block danach parst.

    Rückgabe: (changes, ok). ok=False → nichts geschrieben (unheilbar)."""
    fm_lines, begin, _end = split_fm(text)
    lines = text.split("\n")
    changes = []
    for idx, _regel, _msg in defects:
        real = begin + idx
        fixed = heal_line(lines[real])
        if fixed != lines[real]:
            changes.append((real, lines[real], fixed))
            lines[real] = fixed
    if not changes:
        return [], True
    new_text = "\n".join(lines)
    new_fm, _b, new_end = split_fm(new_text)
    if _yaml is not None and (new_end is None or parse_ok("\n".join(new_fm) + "\n") is not True):
        return [], False                                # Heilung hilft nicht
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new_text)
    return [(alt, neu) for _i, alt, neu in changes], True


def run(fix):
    """→ (hart, hinweise, heilungen, unheilbar, geprüfte_dateien)."""
    hart, hinweise, heilungen, unheilbar, geprüfte = [], [], [], [], 0
    for path in content_files():
        geprüfte += 1
        rel = os.path.relpath(path, BLOG_DIR)
        grenze, glue, text, defects = inspect(path)
        if grenze:
            note = ("keine eigene ---Zeile am Dateianfang" if grenze == "F1"
                    else "Frontmatter-Block nicht geschlossen – der Body wird "
                         "zum Frontmatter")
            hart.append((rel, grenze, note))
            continue
        if glue:
            hinweise.append((rel, "G",
                             f"FM-Schlussgrenze zugeklebt: '---{glue[:56]}'"))
        if not defects:
            continue
        for idx, regel, msg in defects:
            hart.append((rel, regel, msg))
        if not fix:
            continue
        changes, ok = heal(path, text, defects)
        if not ok:
            unheilbar.append(rel)
            continue
        for alt, neu in changes:
            heilungen.append((rel, alt, neu))
    residual = []
    if fix and heilungen:
        for path in content_files():
            rel = os.path.relpath(path, BLOG_DIR)
            grenze, _glue, _text, defects = inspect(path)
            if grenze or defects:
                residual.append(rel)
    return hart, hinweise, heilungen, unheilbar, residual, geprüfte


def write_report(hart, hinweise, heilungen, unheilbar, residual, geprüfte, modus):
    stand = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
    zeilen = [
        "# 🧱 FM-GRENZEN-REPORT (fm_boundary_guard.py)",
        "",
        f"**Stand:** {stand} UTC · Modus: {modus.upper()}",
        f"**Geprüfte Dateien:** {geprüfte} · **baukritisch:** {len(hart)} · "
        f"**automatisch geheilt:** {len(heilungen)} · **unheilbar:** "
        f"{len(unheilbar)} · **offen nach Heilung:** {len(residual)} · "
        f"**Kleber-Hinweise:** {len(hinweise)}",
        "",
        "**Regelkanon:** F1 Grenze oben · F2 Grenze unten · F3 Block/Zeile "
        "nicht YAML-parbar · F4 Quote/Flow nicht geschlossen · F5 "
        "Fallback-Regel ohne PyYAML · G Kleber an der Schlussgrenze (Hinweis)",
        "",
        f"**Gegenprüfung:** PyYAML "
        f"{'aktiv (Block-Parse vor und nach jeder Heilung)' if _yaml is not None else 'fehlt – nur deterministische Formregeln, Heilung auf eindeutig gefahrlose Fälle beschränkt'}",
        "",
    ]
    if not hart:
        zeilen.append("🎉 Alle Frontmatter-Blöcke sind baufest – Grenzen und "
                      "Werte YAML-konform. `hugo --minify` kann am "
                      "Frontmatter nicht mehr scheitern.")
    else:
        zeilen += ["## ⚠️ Baukritische Funde", "",
                   "| Datei | Regel | Befund |", "|---|---|---|"]
        zeilen += [f"| `{f}` | {r} | {m} |" for f, r, m in hart[:60]]
        if len(hart) > 60:
            zeilen.append(f"| … | … | {len(hart) - 60} weitere |")
    if heilungen:
        zeilen += ["", "## Selbstheilung (nur Wert-Quote, Text bytegleich)", ""]
        zeilen += [f"- `{rel}`: `{alt[:70]}` → `{neu[:70]}`"
                   for rel, alt, neu in heilungen[:60]]
    if unheilbar:
        zeilen += ["", "## ⚠️ Nicht automatisch heilbar (manuell)", ""]
        zeilen += [f"- `{rel}`" for rel in unheilbar[:40]]
    if residual:
        zeilen += ["", "## ⚠️ Nach Heilung weiterhin auffällig", ""]
        zeilen += [f"- `{rel}`" for rel in residual[:40]]
    if hinweise:
        zeilen += ["", "## Hinweise: Kleber an der FM-Schlussgrenze", "",
                   "Hugo schließt das Frontmatter an der ersten Zeile, die mit "
                   "`---` beginnt – der Text dahinter ist damit NICHT Teil des "
                   "Body (deshalb erscheint der Einstiegsabsatz doppelt, wenn er "
                   "unter der Grenze noch einmal steht). Zerlegen ist Aufgabe "
                   "der Umbruch-/Casing-Wache, hier nur gemeldet.", "",
                   ]
        zeilen += [f"- `{rel}` {msg}" for rel, _r, msg in hinweise[:20]]
        if len(hinweise) > 20:
            zeilen.append(f"- … {len(hinweise) - 20} weitere")
    zeilen += ["", "---",
               "_Hartes Gate VOR `hugo --minify` (deploy.yml): FM-Fehler sind "
               "die einzige Klasse, die den gesamten Deploy stoppt – ohne "
               "Gate-Report, ohne verwertbares Fehler-Alerting, nur ein toter "
               "Build._"]
    with open(REPORT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(zeilen) + "\n")


# ------------------------------------------------------------------- Selbsttest
SELFTEST_CASES = [
    # (name, FM-Zeile, befund_mit_pyyaml, geheilte_zeile, befund_ohne_pyyaml)
    #  befund_ohne_pyyaml = None → gleiche Erwartung im Fallback-Modus
    ("Regression 11.09.2026: *Werbung-Prefix",
     "pin_description: *Werbung | Der Traumurlaub scheitert am Budget?",
     True, 'pin_description: "*Werbung | Der Traumurlaub scheitert am Budget?"',
     None),
    ("Alias ohne Ziel", "excerpt: *unbekannt", True, 'excerpt: "*unbekannt"', None),
    ("Unbekannter Tag", "inspiration: !!unbekannt Bild", True,
     'inspiration: "!!unbekannt Bild"', None),
    ("Bullethochladung", "excerpt: - nicht ok", True, 'excerpt: "- nicht ok"', None),
    ("Key-Konflikt im Wert", "title: Reisekasse: 7 Tipps", True,
     'title: "Reisekasse: 7 Tipps"', None),
    ("Wert endet auf Doppelpunkt", "pinwand: Günstig reisen:", True,
     'pinwand: "Günstig reisen:"', None),
    ("Quote nicht geschlossen", 'description: "halb offen', True,
     'description: "\\"halb offen"', False),
    ("Blockscalar mit Text", "description: | zu viel text", True,
     'description: "| zu viel text"', False),
    # Ruhe-Fälle – sie schützen den Bestand vor False Positives
    ("Ruhe: Double-Quote mit Doppelpunkt", 'title: "Reisekasse: 7 Tipps"',
     False, None, None),
    ("Ruhe: Flow-Sequence mit ': ' im Item",
     'tags: ["Energie-Update: was sich jetzt ändert", "Strom", "Gas"]',
     False, None, None),
    ("Ruhe: Plain-Scalar", "pillar: mietwagen", False, None, None),
    ("Ruhe: ISO-Datum", "date: 2026-09-11T11:17:28Z", False, None, None),
    ("Ruhe: Blockschlüssel", "cover:", False, None, None),
    ("Ruhe: verschachtelte Zeile", "  alt: !!str Bild", False, None, None),
    ("Ruhe: Pipe/Ampersand mittig", "pinwand: Günstig reisen | Budget & Auto",
     False, None, None),
    ("Ruhe: Boolesche Werte", "draft: false", False, None, None),
    ("Ruhe: legaler Anker (nur Parser urteilt)", "title: &titel Reisekasse",
     False, None, True),
    ("Ruhe: legaler Tag (nur Parser urteilt)", "inspiration: !!str Bild",
     False, None, True),
]

GRENZE_CASES = [
    ("geschlossener Block", "---\ntitle: x\n---\nBody\n", None),
    ("Kleber-Schluss (Hugo akzeptiert)", "---\ntitle: x\n---Warum zahlen…\n", None),
    ("ohne obere Grenze", "title: x\n---\nBody\n", "F1"),
    ("ohne untere Grenze", "---\ntitle: x\nBody\n", "F2"),
]


def selftest():
    fehler = []
    hinweise = []
    if _yaml is None:
        hinweise.append("PyYAML fehlt – es gilt der deterministische "
                        "Fallback-Regelkanon (Deploy installiert pyyaml vor "
                        "der Wache: 'Py-Abhängigkeiten für Gate-Chain')")
    for name, zeile, erwartet, ziel, fallback in SELFTEST_CASES:
        soll = erwartet if _yaml is not None else (
            erwartet if fallback is None else fallback)
        defects = find_defects(zeile.split("\n"))
        if bool(defects) != soll:
            fehler.append(f"{name}: Befund={bool(defects)} erwartet={soll}")
            continue
        got = heal_line(zeile)
        if soll and ziel is not None and got != ziel:
            fehler.append(f"{name}: Heilung {got!r} != {ziel!r}")
        if got != zeile:                        # Konvergenz + Schema-Ruhe
            if find_defects([got]):
                fehler.append(f"{name}: geheilte Zeile bleibt auffällig "
                              f"(nicht konvergent)")
            if parse_ok(got + "\n") is False:
                fehler.append(f"{name}: geheilte Zeile ist kein gültiges YAML")
    for name, text, erwartet in GRENZE_CASES:
        fm_lines, _b, end = split_fm(text)
        grenze = None if (fm_lines is not None and end is not None) else erwartet
        if grenze != erwartet:
            fehler.append(f"{name}: Grenze {grenze!r} != {erwartet!r}")
    if closing_glue("---\nt: x\n---Warum zahlen…\nBody\n") != "Warum zahlen…":
        fehler.append("Kleber-Erkennung defekt")
    if closing_glue("---\nt: x\n---\nBody\n") != "":
        fehler.append("Kleber-Erkennung meldet saubere Grenze")
    # Round-Trip-Eigenschaft: jeder Wert – so hässlich er für YAML ist –
    # muss durch yaml_quote so geschrieben werden, dass Hugo ihn exakt
    # zurückbekommt (Quote nur wo nötig, Escaping immer korrekt).
    NASTY = ['*Werbung | Der Traumurlaub: 500 €', ': führend', '- listig',
             'a: b', 'text # kommentar', 'sag "hi" \\back', 'mehr\nzeilig',
             "it's ok", '', '  lead', 'trail  ', '{} klammern', '[1, 2]',
             '&anker', '*alias', '%direktive', '@at', '`tick`', '>fold',
             '|literal', 'ganz normal']
    for v in NASTY:
        q = yaml_quote(v)
        if needs_quote(v) and not (q.startswith('"') and q.endswith('"')):
            fehler.append(f"Round-Trip {v!r}: Quote fehlt trotz Bedarf")
            continue
        if not needs_quote(v) and q != v:
            fehler.append(f"Round-Trip {v!r}: unnötig umgeschrieben")
            continue
        if _yaml is not None:
            try:
                back = _yaml.safe_load("key: " + q + "\n")
            except Exception as exc:
                fehler.append(f"Round-Trip {v!r}: {exc}")
                continue
            if not isinstance(back, dict) or back.get("key") != v:
                fehler.append(f"Round-Trip {v!r} → {q!r} → {back!r}")
    # Schema-Schutz: eine Liste darf durch eine Heilung nie zum String werden
    listenzeile = 'tags: ["Energie-Update: was sich jetzt ändert"]'
    if find_defects([listenzeile]):
        fehler.append("Schema-Risiko: legale Flow-Sequence würde umgeschrieben")
    for h in hinweise:
        print(f"ℹ FM-Grenzen-Selbsttest: {h}")
    if fehler:
        print("❌ FM-Grenzen-Selbsttest FEHLERHALFT – die Wache greift nicht "
              "ins Content-Regiment ein:")
        for f in fehler:
            print("  -", f)
        return 2
    print(f"✅ FM-Grenzen-Selbsttest: {len(SELFTEST_CASES)} Wert-Fälle + "
          f"{len(GRENZE_CASES)} Grenz-Fälle + Kleber/Quote/Schema-Schutz grün "
          f"(inkl. Regression '*Werbung |').")
    return 0


def main():
    if "--selftest" in sys.argv:
        return selftest()
    fix = "--fix" in sys.argv
    hart, hinweise, heilungen, unheilbar, residual, geprüfte = run(fix)
    write_report(hart, hinweise, heilungen, unheilbar, residual, geprüfte,
                 "fix" if fix else "check")
    for rel, regel, msg in hart:
        print(f"⚠ FM-Grenze {regel}: {rel} – {msg}")
    for rel, alt, neu in heilungen:
        print(f"🩹 FM-Grenze geheilt: {rel}: {alt[:60]} → {neu[:60]}")
    if unheilbar:
        for rel in unheilbar:
            print(f"❌ nicht automatisch heilbar: {rel}")
    if residual:
        print(f"❌ {len(residual)} Datei(en) bleiben nach Heilung auffällig – "
              f"Details: FM-GRENZEN-REPORT.md")
        return 1
    if unheilbar:
        print(f"❌ {len(unheilbar)} Datei(en) müssen manuell repariert werden – "
              f"Report: FM-GRENZEN-REPORT.md")
        return 1
    if heilungen:
        print(f"✅ FM-Grenzen: {len(heilungen)} Wert(e) selbstgeheilt "
              f"({geprüfte} Dateien geprüft) – der Build ist wieder möglich.")
        return 0
    if hart:
        print(f"❌ {len(hart)} baukritische(r) FM-Fund/Funde (--fix heilt "
              f"deterministisch). Report: FM-GRENZEN-REPORT.md")
        return 1
    print(f"✅ FM-Grenzen sauber ({geprüfte} Dateien, {len(hinweise)} "
          f"Kleber-Hinweis(e) gemeldet) – der Build kann am Frontmatter nicht "
          f"mehr sterben.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
