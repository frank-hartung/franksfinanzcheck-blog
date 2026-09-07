#!/usr/bin/env python3
"""
LESBARKEITS-AUDIT für FranksFinanzcheck (deutsche Readability-Formeln).

Misst für jeden Artikel die wichtigsten Lesbarkeits-Kennzahlen auf
Top-Level-Niveau (deutsche Amstad-Formel – Flesch-Reading-Ease angepasst):

  - Flesch-Score (Amstad): 180 − (Wörter/Sätze) − (58,5 × Silben/Wörter)
      Ziel: ≥ 55 (verständlich) – Top-Level: 60–75
  - Ø Satzlänge            Ziel: 12–18 Wörter
  - Ø Wortlänge            Ziel: ≤ 6 Buchstaben
  - Anteil langer Wörter   Ziel: < 15 % (> 12 Buchstaben)
  - Schachtelsätze         Ziel: < 10 % (> 25 Wörter)
  - Absätze > 4 Sätze      Ziel: 0
  - Passiv-Formulierungen  Ziel: wenige ("wird/werden/kann ... werden")

NUTZUNG:
  python3 scripts/readability_check.py            # Audit aller Artikel
  python3 scripts/readability_check.py --json     # maschinenlesbar
  python3 scripts/readability_check.py --file X.md
  python3 scripts/readability_check.py --new-only # Publish-Gate (neue Artikel)
  python3 scripts/readability_check.py --gate-bestand [--report LESBARKEIT-REPORT.md]
                                                 # Wochen-Wache (Ø ≥ 62, Floor ≥ 55)
  python3 scripts/readability_check.py --selftest # Sabotage-Schutz für CI
"""
import os
import re
import sys
import glob
import json

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
# Top-Level-Schwellen (gehärtet 01.09.2026 – Audit: vorher zu lasch)
SCORE_MIN = 60              # war 50
SENT_MAX = 16               # war 20
LONG_WORD_MAX = 15          # war 18
NESTED_MAX = 10             # war 12
ABSATZ_MAX_SENT = 4         # war 6

# Zielgrößen (vereinheitlicht 07.09.2026 mit Qualitäts-Regelwerk R6):
# Die Chefredakteur-Scorecard zeigte vorher „Ziel ≥ 70“ – ein Mess-Artefakt aus
# der Zeit, als Lesbarkeit aus einer nie existierenden Datei gelesen und mit
# `(v or 100) >= 70` grün gefärbt wurde (Härtung G2). Das Regelwerk definiert
# als Zielhorizont Flesch-Amstad Ø ≥ 62. Scorecard und Gate nutzen jetzt
# dieselben Schwellen – eine Kennzahl, eine Wahrheit.
AVG_TARGET = 62.0        # Regelwerk: Flesch-Amstad Ø ≥ 62 (6-Monats-Zielhorizont)
FLOOR_MIN = 55.0         # Bestand: kein Artikel dauerhaft unter 55 (Warn-/Issue-Schwelle)
NEW_FLESCH_MIN = 60.0    # R6: neue Artikel Flesch ≥ 60 – hart im Publish-Gate
# Keyword-Dump-Grenze (R2): einzelne Zeile/Block > 500 Zeichen mit > 12 Kommas
DUMP_MAX_LEN = 500
DUMP_MAX_COMMAS = 12

PASSIV_RE = re.compile(r'\b(wird|werden|wurde|wurden|kann .{1,20} werden|muss .{1,20} werden|sollte .{1,20} werden)\b', re.I)

# Paarige Hugo-Block-Shortcodes mit Inhalt: {{< tarif … >}} … {{< /tarif >}}
_PAIRED_SHORTCODE_RE = re.compile(
    r'\{\{\s*<\s*[A-Za-z][^{}]*?\s>\}\}.*?\{\{\s*<\s*/\s*[A-Za-z][^{}]*?\s>\}\}',
    re.S)


def _strip_shortcodes(body):
    """Entfernt HUGO-Shortcodes inklusive Block-Inhalt (siehe load_article)."""
    body = _PAIRED_SHORTCODE_RE.sub(' ', body)
    body = re.sub(r'\{\{<.*?/?>\}\}', ' ', body)
    return body


def load_article(path):
    c = open(path, encoding='utf-8').read()
    parts = c.split('---', 2)
    if len(parts) < 3:
        return None
    body = parts[2]
    # Markdown-Syntax entfernen, Links/Code maskieren
    body = re.sub(r'```.*?```', ' ', body, flags=re.S)
    body = re.sub(r'!\[[^\]]*\]\([^)]*\)', ' ', body)
    body = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', body)
    # HUGO-SHORTCODES entfernen (z. B. {{< tarifvergleich … >}}): sie sind
    # Markup, keine Fließtext-Sätze (Mess-Artefakt, 01.09.2026 – Audit P1
    # „Lesbarkeits-Gate ehrlich machen“). Ohne diese Zeile werden komplette
    # Tarifvergleich-Blöcke als EIN „Schachtelsatz“ mit mehreren hundert
    # Wörtern gezählt und verzerren wps/Flesch/nested systematisch.
    # Erweiterung (07.09.2026 – Audit „Ø Lesbarkeit 53.3“): Auch PAARIGE
    # Block-Shortcodes ({{< tarif … >}} … {{< /tarif >}} mit Inhalt) entfernen.
    # Vorher matchte die Regex nur das öffnende Tag bis zum ersten „>}}“; der
    # Inhalt (Zahlenreihen, „<br><small>…“-Fragmente) blieb als Pseudo-Satz mit
    # dutzenden Wörtern im Mess-Text und verzerrte wps/Flesch/nested massiv.
    body = _strip_shortcodes(body)
    # HTML-Kommentare entfernen (z. B. <!-- premium-length-2026 -->): Markup,
    # kein Fließtext. Vorher zählten „premium length 2026“ als Phantom-Wörter
    # und klebten nach dem Heading-Removal Absätze zu Pseudosätzen zusammen
    # (Mess-Artefakt, 07.09.2026 – Audit „Ø Lesbarkeit 53.3“).
    body = re.sub(r'<!--.*?-->', ' ', body, flags=re.S)
    # ZUERST Listen-Einträge (Bullets) und Überschriften entfernen –
    # sie sind KEINE Fließtext-Sätze (Mess-Artefakte). WICHTIG: VOR dem
    # Entfernen der Markdown-Sonderzeichen (sonst fehlt das Bullet-Zeichen).
    # Mehrzeilige Listen-Einträge (Folgezeilen ohne Bullet) werden mit-
    # entfernt, solange sie zur Liste gehören (kein Leerzeilen-Abstand).
    lines = body.split('\n')
    out = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        if re.match(r'^[*+-]\s+', stripped) or re.match(r'^\d+\.\s+', stripped):
            in_list = True
            out.append(' ')
            continue
        if in_list and stripped and not stripped.startswith('#'):
            # Folgezeile einer Liste (ohne Leerzeile dazwischen)
            if not stripped:
                in_list = False
                out.append(line)
            else:
                out.append(' ')
            continue
        if re.match(r'^#{1,6}\s', stripped):
            out.append(' ')
            continue
        if stripped.startswith('|'):
            out.append(' ')
            continue
        if stripped.startswith('>'):
            # Callout-Boxen/Zitate („> 💡 Schnell-Tipp …“, „> ⚠️ …“) sind
            # KEINE Fließtext-Sätze – sonst verschmelzen sie beim
            # Zeilenumbruch-Collapse mit dem Nachbar-Absatz zu Pseudosätzen
            # (Mess-Artefakt, 01.09.2026 – Audit P1).
            out.append(' ')
            continue
        if stripped.startswith(('💡', '👉', '**Weiterlesen:**', '**Weiterlesen :**')):
            # Promo-/CTA-/Footer-Boilerplate („💡 Schnell-Tipp …“, „👉 Jetzt
            # vergleichen …“, „**Weiterlesen:** …“): Affiliate-Aufrufe und
            # Link-Footer, kein Fließtext. Endet ohne Satzzeichen und würde
            # sonst mit dem Folgeabsatz (Disclaimer/FAQ) verschmelzen
            # (Mess-Artefakt, 01.09.2026 – Audit P1).
            out.append(' ')
            continue
        if in_list and not stripped:
            in_list = False
        out.append(line)
    body = '\n'.join(out)
    body = re.sub(r'[#*_>`|~-]', ' ', body)
    # Satzende vor schließender Klammer normalisieren: „…Mehrkosten.) Nächster
    # Satz.“ – der Punkt endet den Satz, die Klammer gehört zum Disclaimer.
    # Ohne diese Zeile verschmilzt der Affiliate-Disclaimer mit dem ersten
    # Satz des Folgeabsatzes zu einem Pseudosatz (Mess-Artefakt, Audit P1).
    body = re.sub(r'\.\)', '. ', body)
    # Zeilenumbrüche als Satztrenner erhalten (verhindert, dass Absätze
    # mit Zeilenumbruch zu langen "Schachtelsätzen" zusammengeklebt werden)
    body = re.sub(r'\s*\n\s*', '\n', body)
    body = re.sub(r'\n+', '\n', body)
    # „…:“ am ZEILENENDE ist eine Strukturgrenze (Listen-/Abschnitts-Intro),
    # kein Satz-interner Doppelpunkt. Als Marker schützen, damit der folgende
    # Absatz nicht mit dem Intro zu einem Pseudosatz verschmilzt
    # (Mess-Artefakt, 01.09.2026 – Audit P1).
    body = re.sub(r':\n', ':\n\x00', body)
    body = re.sub(r'\s+', ' ', body)
    body = body.replace('\x00', '\n')
    return {'file': os.path.relpath(path, POSTS_DIR), 'body': body}


def count_syllables(word):
    """Silbenzählung (deutsch, 01.09.2026 gehärtet).

    Audit-Fund: die alte Heuristik zog bei jedem Wort auf „-e“ eine Silbe
    ab („danke“ → 1 statt 2) und verzerrte den Flesch-Score systematisch.
    Im Deutschen ist das End-e nach Konsonant fast immer eine eigene Silbe
    (dan-ke, ma-che, Ta-bel-le). Neue Regeln:
      - Vokalgruppen (inkl. Diphthonge ei/au/eu/äu/ie) je 1 Silbe
      - End-e: NICHT mehr abziehen
      - „ie“ am Wortende nach mehreren Silben zählt 2 (Fa-mi-li-e, Stu-di-e)
        – außer in Einsilblern (die, wie, nie, sie)
    """
    word = word.lower().replace('ä', 'a').replace('ö', 'o').replace('ü', 'u')
    n = len(re.findall(r'[aeiouy]+', word))
    # Endung „-ion“ (ti-on, si-on, li-on): die „io“-Gruppe zählt als 1,
    # gesprochen sind es aber 2 Silben (In-for-ma-ti-on, Mil-li-on,
    # Vi-si-on, Re-gi-on).
    if re.search(r'ion$', word):
        n += 1
    # „ie" am Wortende ist nach mehreren Silben meist 2-silbig
    # (Fa-mi-li-e, Stu-di-e, Se-ri-e, Li-li-e) – außer in Einsilblern
    # (die, wie, nie, sie), dort ist n == 1 und der Zuschlag entfällt.
    elif n > 1 and word.endswith('ie') and len(word) >= 4:
        n += 1
    return max(1, n)


def analyze(a):
    text = a['body'].replace('&nbsp;', ' ')
    words = re.findall(r'\b[a-zäöüßA-ZÄÖÜ0-9]+\b', text)
    # Sätze an Satzzeichen teilen – Datumspunkte ("30. November") ausnehmen
    text_protected = re.sub(r'(\b\d{1,2})\.\s+([A-ZÄÖÜ][a-zäöüß]{2,}\b)', r'\1 \2', text)
    raw_sents = re.split(r'[.!?]\s+|\n', text_protected)
    sentences = [s for s in raw_sents if len(re.findall(r'\b\w+\b', s)) > 1]

    n_words = len(words)
    n_sents = len(sentences) if sentences else 1
    syllables = sum(count_syllables(w) for w in words)

    # Flesch (Amstad, deutsch)
    wps = n_words / n_sents
    spw = syllables / n_words
    flesch = 180 - wps - (58.5 * spw)

    # Wortlängen
    avg_word_len = sum(len(w) for w in words) / n_words if words else 0
    long_words = [w for w in words if len(w) > 12]
    long_pct = 100 * len(long_words) / n_words if words else 0

    # Schachtelsätze (> 25 Wörter) – NUR echte Fließtext-Sätze
    # (Listen-Zeilen wurden oben bereits entfernt; kein Notbehelf mehr)
    nested = [s for s in sentences if len(re.findall(r'\b\w+\b', s)) > 25]
    nested_pct = 100 * len(nested) / n_sents

    # Keyword-Dumps (R2): Komma-Ketten als eigene Metrik zählen –
    # sie verzerren sonst Satzlängen-Maxima und verstecken sich vor der Messung
    raw = open(os.path.join(POSTS_DIR, a['file']), encoding='utf-8').read()
    raw_body = raw.split('---', 2)[2]
    dumps = 0
    for line in raw_body.split('\n'):
        if len(line) > DUMP_MAX_LEN and line.count(',') > DUMP_MAX_COMMAS:
            dumps += 1

    # Absatzlängen (Roh-Body vor Glättung – nutze Original)
    c = raw
    raw_body = c.split('---', 2)[2]
    paras = [p for p in raw_body.split('\n\n') if len(re.findall(r'\b\w+\b', p)) > 1
             and not p.strip().startswith(('#', '*', '-', '|', '>', '<'))]
    # Nur echte Fließtext-Absätze: ohne Listen-/Zitat-/Tabellen-Marker in der Zeile
    real_paras = []
    for p in paras:
        lines = [l for l in p.split('\n') if l.strip()]
        if lines and re.match(r'^\s*[*+-]|^\s*\d+\.|^\s*>|^\s*\|', lines[0]):
            continue
        # Nummerierte Anleitungen (1. ... 2. ...) als Liste erkennen
        if len(lines) >= 3 and all(re.match(r'^\s*\d+\.', l) for l in lines[:3]):
            continue
        real_paras.append(p)
    long_paras = [p for p in real_paras
                  if len(re.findall(r'[.!?]\s+', re.sub(r'(\b\d{1,2})\.\s+', r'\1 ', p))) >= ABSATZ_MAX_SENT]

    # Passiv
    passiv_count = len(PASSIV_RE.findall(text))

    # Score 0–100 (gewichtet)
    score = 100
    issues = []
    if flesch < SCORE_MIN:
        score -= 20
        issues.append(f"Flesch {flesch:.0f} (Ziel ≥ {SCORE_MIN})")
    if wps > SENT_MAX:
        score -= 15
        issues.append(f"Ø Satzlänge {wps:.0f} Wörter (Ziel ≤ {SENT_MAX})")
    if avg_word_len > 6.5:
        score -= 10
        issues.append(f"Ø Wortlänge {avg_word_len:.1f} (Ziel ≤ 6,5)")
    if long_pct > LONG_WORD_MAX:
        score -= 10
        issues.append(f"{long_pct:.0f}% lange Wörter (Ziel < {LONG_WORD_MAX}%)")
    if nested_pct > NESTED_MAX:
        score -= 10
        issues.append(f"{nested_pct:.0f}% Schachtelsätze (Ziel < {NESTED_MAX}%)")
    if long_paras:
        score -= 5
        issues.append(f"{len(long_paras)} Absätze > {ABSATZ_MAX_SENT} Sätze")
    if dumps:
        score -= 10
        issues.append(f"{dumps} Keyword-Dump(s) (Komma-Ketten > {DUMP_MAX_LEN} Zeichen)")
    if passiv_count > 8:
        score -= 5
        issues.append(f"{passiv_count} Passiv-Formulierungen")

    # Satzlängen-Streuung (SD) als Info-Metrik – monotone Satzrhythmen
    # (alle Sätze gleich lang) sind schwer lesbar
    sent_lens = [len(re.findall(r'\b\w+\b', s)) for s in sentences]
    sd = 0.0
    if len(sent_lens) > 1:
        mean = sum(sent_lens) / len(sent_lens)
        sd = (sum((x - mean) ** 2 for x in sent_lens) / (len(sent_lens) - 1)) ** 0.5

    return {
        'file': a['file'], 'flesch': round(flesch, 1), 'wps': round(wps, 1),
        'word_len': round(avg_word_len, 1), 'long_pct': round(long_pct, 1),
        'nested_pct': round(nested_pct, 1), 'long_paras': len(long_paras),
        'dumps': dumps, 'sat_len_sd': round(sd, 1),
        'passiv': passiv_count, 'score': max(0, min(100, score)), 'issues': issues,
    }


def _selftest():
    """Sabotage-Schutz (CI): Schwellen = Regelwerk R6, Paar-Shortcodes weg."""
    fails = []
    if not (AVG_TARGET >= 62.0 and FLOOR_MIN <= 60.0 and NEW_FLESCH_MIN >= 60.0):
        fails.append(f"Schwellen falsch: {AVG_TARGET}/{FLOOR_MIN}/{NEW_FLESCH_MIN}")
    body = ("{{< tarif preis=\"x\" >}}Nur Figuren: 1.000 Wörter 2.000 Wörter"
            "{{< /tarif >}} Danach ein echter Satz mit Inhalt.")
    out = _strip_shortcodes(body)
    if "1.000 Wörter" in out or "2.000 Wörter" in out:
        fails.append("Paar-Shortcode-Body wurde nicht entfernt")
    if "Danach ein echter Satz" not in out:
        fails.append("Fließtext nach Shortcode ging verloren")
    single = "Text {{< tarifvergleich anbieter=\"a\" >}} danach."
    if "tarifvergleich" in _strip_shortcodes(single):
        fails.append("Einzel-Shortcode wurde nicht entfernt")
    if fails:
        for f in fails:
            print("❌ " + f)
        return 1
    print("✅ readability_check --selftest OK (R6-Schwellen + Shortcode-Stripping)")
    return 0


def main():
    if '--selftest' in sys.argv:
        sys.exit(_selftest())
    import datetime
    today = datetime.date.today().isoformat()
    as_json = '--json' in sys.argv
    new_only = '--new-only' in sys.argv
    files = None
    if '--file' in sys.argv:
        files = [sys.argv[sys.argv.index('--file') + 1]]
    paths = files or sorted(
        glob.glob(os.path.join(POSTS_DIR, "*.md"))
        + glob.glob(os.path.join(POSTS_DIR, "*", "index.md"))
    )
    # Inhaltsverzeichnis (_index.md) ist keine Lesbarkeits-Messgröße
    paths = [p for p in paths if os.path.basename(os.path.dirname(p)) != "posts"
             or os.path.basename(p) != "_index.md"]

    if new_only:
        # Nur Artikel, die heute publiziert wurden (draft ausgeschlossen)
        filtered = []
        for p in paths:
            c = open(p, encoding='utf-8').read()
            m = re.search(r'^date:\s*"?([0-9-]+)', c, re.M)
            if m and m.group(1).startswith(today) and 'draft: true' not in c:
                filtered.append(p)
        paths = filtered
        if not paths:
            print("Lesbarkeits-Gate: keine neuen Artikel heute – OK.")
            return

    results = []
    for p in paths:
        a = load_article(p)
        if a:
            results.append(analyze(a))

    results.sort(key=lambda r: r['score'])
    avg = sum(r['score'] for r in results) / len(results) if results else 0
    avg_flesch = sum(r['flesch'] for r in results) / len(results) if results else 0

    if as_json:
        print(json.dumps({
            'avg': round(avg, 1), 'avg_flesch': round(avg_flesch, 1),
            'target': AVG_TARGET, 'floor': FLOOR_MIN,
            'articles': results}, ensure_ascii=False, indent=2))
        return

    print(f"Lesbarkeits-Audit: {len(results)} Artikel | Ø Score {avg:.0f}/100 "
          f"(Top-Level ≥ 75) | Ø Flesch {avg_flesch:.1f} (Ziel ≥ {AVG_TARGET:.0f}, "
          f"Regelwerk R6)")
    print(f"{'Score':>5} {'Flesch':>7} {'Satz':>5} {'Wort':>5} {'Lang%':>6} {'Schacht%':>8} {'Dump':>5}  Artikel")
    print('-' * 96)
    for r in results:
        mark = '✅' if r['flesch'] >= AVG_TARGET else ('⚠️' if r['flesch'] >= FLOOR_MIN else '❌')
        print(f"{mark} {r['score']:4d} {r['flesch']:6.1f} {r['wps']:5.1f} {r['word_len']:5.1f} "
              f"{r['long_pct']:5.1f} {r['nested_pct']:7.1f} {r['dumps']:5d}  {r['file'][:48]}")
    print('-' * 96)
    below_floor = [r for r in results if r['flesch'] < FLOOR_MIN]
    below_target = [r for r in results if r['flesch'] < AVG_TARGET]
    print(f"Ø Flesch {avg_flesch:.1f} (Ziel ≥ {AVG_TARGET:.0f}) | "
          f"unter Floor {FLOOR_MIN:.0f}: {len(below_floor)} Artikel | "
          f"unter Ziel {AVG_TARGET:.0f}: {len(below_target)} Artikel")

    # Gate-Modi:
    #  --new-only     Publish-Gate: neue Artikel müssen Top-Level-Score UND
    #                 Regelwerk R6 (Flesch ≥ 60) erfüllen – sonst Entwurf.
    #  --gate-bestand Wochen-Wache: Ø Flesch ≥ 62 UND kein Artikel < 55,
    #                 sonst Exit 1 (meldet den Bestand als Handlungsfeld).
    if new_only:
        viol = [r for r in results if r['score'] < 75 or r['flesch'] < NEW_FLESCH_MIN]
        if viol:
            for r in sorted(viol, key=lambda x: x['flesch']):
                print(f"❌ Neue Artikel unter Schwelle (Score ≥ 75, Flesch ≥ {NEW_FLESCH_MIN:.0f}): "
                      f"{r['file']} – Score {r['score']}, Flesch {r['flesch']:.1f}")
            print("❌ Lesbarkeits-Gate nicht bestanden – neue Artikel parken als Entwurf!")
            sys.exit(1)
        print("✅ Lesbarkeits-Gate OK – neue Artikel auf Top-Level (Score ≥ 75, Flesch ≥ 60)")
        return
    if '--gate-bestand' in sys.argv:
        issues = []
        if avg_flesch < AVG_TARGET:
            issues.append(f"Ø Flesch {avg_flesch:.1f} < Ziel {AVG_TARGET:.0f}")
        for r in below_floor:
            issues.append(f"Floor: {r['file']} Flesch {r['flesch']:.1f} < {FLOOR_MIN:.0f}")
        # Governance-/Alerting-Report (Ampel + Befundtabelle), damit die Wache
        # für governance_gate auswertbar ist (Exit-Code allein ist kein Befund).
        if '--report' in sys.argv:
            rep = (sys.argv[sys.argv.index('--report') + 1]
                   if sys.argv.index('--report') + 1 < len(sys.argv) else '')
            if rep:
                ampel = ('RED' if below_floor
                         else ('AMBER' if avg_flesch < AVG_TARGET else 'GREEN'))
                rows = []
                if avg_flesch < AVG_TARGET:
                    rows.append(f"| AMBER | read_avg | Ø Flesch {avg_flesch:.1f} "
                                f"< Ziel {AVG_TARGET:.0f} (Regelwerk R6) |")
                for r in below_floor:
                    rows.append(f"| RED | read_floor | {r['file']} – Flesch "
                                f"{r['flesch']:.1f} < Floor {FLOOR_MIN:.0f} |")
                content = (
                    "# Lesbarkeits-Wache – Bestands-Gate (Flesch-Amstad, deutsch)\n\n"
                    "Gesamt-Ampel: **" + ampel + "**\n\n"
                    f"- Geprüfte Artikel: **{len(results)}**\n"
                    f"- Ø Flesch: **{avg_flesch:.1f}** (Ziel ≥ {AVG_TARGET:.0f})\n"
                    f"- Unter Floor {FLOOR_MIN:.0f}: **{len(below_floor)}**\n\n"
                    "## Befunde\n\n"
                    "| Level | Code | Befund |\n"
                    "|---|---|---|\n" + "\n".join(rows) + "\n")
                try:
                    with open(os.path.join(BLOG_DIR, rep), 'w', encoding='utf-8') as fh:
                        fh.write(content)
                except OSError as exc:
                    print(f"⚠️ Report {rep} nicht schreibbar: {exc}")
        if issues:
            for i in issues:
                print("❌ " + i)
            print("❌ Bestands-Gate nicht bestanden – Lesbarkeit ist Handlungsfeld.")
            sys.exit(1)
        print("✅ Bestands-Gate OK – Ø Flesch im Ziel, kein Artikel unter Floor")
        return
    if below_floor or avg_flesch < AVG_TARGET:
        print("⚠️ Lesbarkeit unter Ziel/Floor – rote Artikel zuerst redaktionell heben "
              "(Hebel je Artikel: `python3 scripts/readability_check.py --json`)")
    else:
        print("✅ Lesbarkeit auf Ziel (Ø Flesch ≥ 62, kein Artikel unter 55)")


if __name__ == '__main__':
    main()
