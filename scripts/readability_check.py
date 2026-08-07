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
"""
import os
import re
import sys
import glob
import json

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
# Top-Level-Schwellen
SCORE_MIN = 55
SENT_MAX = 20
LONG_WORD_MAX = 18
NESTED_MAX = 12
ABSATZ_MAX_SENT = 4

PASSIV_RE = re.compile(r'\b(wird|werden|wurde|wurden|kann .{1,20} werden|muss .{1,20} werden|sollte .{1,20} werden)\b', re.I)


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
    # ZUERST Listen-Einträge (Bullets) und Überschriften entfernen –
    # sie sind KEINE Fließtext-Sätze (Mess-Artefakte). WICHTIG: VOR dem
    # Entfernen der Markdown-Sonderzeichen (sonst fehlt das Bullet-Zeichen).
    body = re.sub(r'^\s*[*+-]\s+.*$', ' ', body, flags=re.M)
    body = re.sub(r'^\s*\d+\.\s+.*$', ' ', body, flags=re.M)  # num. Listen
    body = re.sub(r'^#{1,6}\s.*$', ' ', body, flags=re.M)
    body = re.sub(r'^\|.*$', ' ', body, flags=re.M)  # Tabellen
    body = re.sub(r'[#*_>`|~-]', ' ', body)
    body = re.sub(r'\s+', ' ', body)
    return {'file': os.path.basename(path), 'body': body}


def count_syllables(word):
    """Silbenzählung (deutsch, vereinfacht): Vokalgruppen zählen."""
    word = word.lower()
    # Umlaute normalisieren
    word = word.replace('ä', 'a').replace('ö', 'o').replace('ü', 'u')
    groups = re.findall(r'[aeiouy]+', word)
    # Stummes e am Ende abziehen (häufig im Deutschen)
    n = len(groups)
    if word.endswith('e') and n > 1:
        n -= 1
    return max(1, n)


def analyze(a):
    text = a['body']
    words = re.findall(r'\b[a-zäöüßA-ZÄÖÜ0-9]+\b', text)
    # Sätze an Satzzeichen teilen
    raw_sents = re.split(r'[.!?]\s+', text)
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

    # Schachtelsätze (> 25 Wörter)
    nested = [s for s in sentences if len(re.findall(r'\b\w+\b', s)) > 25]
    nested_pct = 100 * len(nested) / n_sents

    # Absatzlängen (Roh-Body vor Glättung – nutze Original)
    c = open(os.path.join(POSTS_DIR, a['file']), encoding='utf-8').read()
    raw_body = c.split('---', 2)[2]
    paras = [p for p in raw_body.split('\n\n') if len(re.findall(r'\b\w+\b', p)) > 1
             and not p.strip().startswith(('#', '*', '-', '|'))]
    long_paras = [p for p in paras if len(re.findall(r'[.!?]\s+', p)) >= ABSATZ_MAX_SENT]

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
    if passiv_count > 8:
        score -= 5
        issues.append(f"{passiv_count} Passiv-Formulierungen")

    return {
        'file': a['file'], 'flesch': round(flesch, 1), 'wps': round(wps, 1),
        'word_len': round(avg_word_len, 1), 'long_pct': round(long_pct, 1),
        'nested_pct': round(nested_pct, 1), 'long_paras': len(long_paras),
        'passiv': passiv_count, 'score': max(0, min(100, score)), 'issues': issues,
    }


def main():
    import datetime
    today = datetime.date.today().isoformat()
    as_json = '--json' in sys.argv
    new_only = '--new-only' in sys.argv
    files = None
    if '--file' in sys.argv:
        files = [sys.argv[sys.argv.index('--file') + 1]]
    paths = files or sorted(glob.glob(os.path.join(POSTS_DIR, '*.md')))

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

    if as_json:
        print(json.dumps({'avg': round(avg, 1), 'articles': results},
                         ensure_ascii=False, indent=2))
        return

    print(f"Lesbarkeits-Audit: {len(results)} Artikel | Ø Score {avg:.0f}/100")
    print(f"{'Score':>5} {'Flesch':>7} {'Satz':>5} {'Wort':>5} {'Lang%':>6} {'Schacht%':>8}  Artikel")
    print('-' * 80)
    for r in results:
        mark = '✅' if r['score'] >= 75 else ('⚠️' if r['score'] >= 60 else '❌')
        print(f"{mark} {r['score']:4d} {r['flesch']:6.0f} {r['wps']:5.1f} {r['word_len']:5.1f} "
              f"{r['long_pct']:5.1f} {r['nested_pct']:7.1f}  {r['file'][:40]}")
    print('-' * 80)
    below = [r for r in results if r['score'] < 75]
    print(f"\nUnter Top-Level (Score < 75): {len(below)} Artikel")
    if below and new_only:
        print("❌ Lesbarkeits-Gate nicht bestanden – neue Artikel unter Schwelle!")
        sys.exit(1)
    elif below:
        print("⚠️ Bestandsartikel unter Schwelle (nur Hinweis – kein Abbruch)")
    else:
        print("✅ Lesbarkeit auf Top-Level")


if __name__ == '__main__':
    main()
