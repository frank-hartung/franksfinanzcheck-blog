#!/usr/bin/env python3
"""
DUPLIKAT-GUARD (R1) – Duplikat- & Redundanz-Wächter für FranksFinanzcheck.

Erkennt die Verständnis-Killer, die KEIN bestehendes Gate misst:

  D1  Exakte Absatz-Duplikate INNERHALB eines Artikels (SHA-256, >= 80 Zeichen)
  D2  Near-Duplikate INNERHALB eines Artikels (difflib-Ratio >= 0.85, >= 120 Zeichen)
      -> fängt auch die "Premium-Length"-Falle ab: angehängte Blöcke, die
         wortnah einen vorhandenen Abschnitt wiederholen (DNS-Artikel 08/2026).
  D3  Exakte Absatz-Duplikate ÜBER Artikel hinweg (>= 80 Zeichen)
  D4  Near-Duplikate ÜBER Artikel hinweg (Ratio >= 0.85, >= 150 Zeichen)
  D5  Sektions-Duplikate: zwei H2-Kapitel eines Artikels fast identisch
      (Ratio >= 0.85, Kapitel >= 150 Zeichen) – "Wann X spürbar ist / Wann Y
      spürbar ist"-Doppelstrukturen.
  D6  Premium-Length-Anhänge: Blöcke NACH dem Marker '<!-- premium-length -->'
      werden gegen den Rest des Artikels geprüft (Shingle-Überlappung >= 5).

MODI:
  python3 scripts/duplikat_guard.py             # Report (alle Artikel)
  python3 scripts/duplikat_guard.py --json      # maschinenlesbar
  python3 scripts/duplikat_guard.py --fix       # exakte + fast-exakte Duplikate
                                                # (Ratio >= 0.92, Längendiff < 25 %)
                                                # im SELBEN Artikel entfernen (spätere Version)
  python3 scripts/duplikat_guard.py --new-only  # Engine-Modus: nur Artikel von heute;
                                                # Funde -> Exit 1 (Gate blockierend)
  python3 scripts/duplikat_guard.py --selftest  # Sabotage-Schutz (eingefrorene Fälle)

Ausgabe: DUPLIKAT-REPORT.md + data/duplikat_history.jsonl
Sicherheit: Cross-Artikel-Funde werden NIE auto-gefixed, nur gemeldet.
"""

import difflib
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "content" / "posts"
REPORT = ROOT / "DUPLIKAT-REPORT.md"
HISTORY = ROOT / "data" / "duplikat_history.jsonl"

DO_FIX = "--fix" in sys.argv
AS_JSON = "--json" in sys.argv
NEW_ONLY = "--new-only" in sys.argv
SELFTEST_ONLY = "--selftest" in sys.argv

MIN_EXACT = 80          # Mindestlänge für exakte Duplikate (Zeichen)
MIN_NEAR = 120          # Mindestlänge für Near-Duplikate (Zeichen)
MIN_NEAR_X = 150        # Mindestlänge für Near-Duplikate über Artikel hinweg
RATIO_NEAR = 0.85       # Near-Duplikat-Schwelle
RATIO_FIX = 0.92        # Auto-Fix-Schwelle (innerhalb Artikel)
FIX_LEN_DIFF = 0.25     # max. relative Längendifferenz für Auto-Fix
PREMIUM_MARKER = "premium-length"
SHINGLE = 5             # N-Gramm-Größe für D6

# Boilerplate-Blöcke (sind absichtlich mehrfach im Artikel: Disclaimer, CTA,
# Weiterlesen-Boxen) – werden von der Duplikat-Messung ausgenommen.
BOILERPLATE_RE = [
    r"dieser artikel enthält affiliate-links",
    r"jetzt vergleichen und sparen",
    r"weiterlesen:",
    r"das wichtigste in kürze",
    r"schnell-tipp von franksfinanzcheck",
    r"lesetipps zum weitersparen",
    r"dieser beitrag enthält affiliate",
    r"beim abschluss über einen link",
]


def is_boilerplate(text: str) -> bool:
    t = text.lower()
    return any(p in t for p in BOILERPLATE_RE)


def split_body(frontmatter_body: str) -> str:
    parts = frontmatter_body.split("---", 2)
    return parts[2] if len(parts) >= 3 else frontmatter_body


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def blocks_of(body: str) -> list:
    """Liste von (block_text_normalized, start_zeichen, ist_premium)."""
    out = []
    premium = False
    pos = 0
    for chunk in body.split("\n\n"):
        chunk_n = normalize(re.sub(r"```.*?```", " ", chunk, flags=re.S))
        if not chunk_n:
            pos += len(chunk) + 2
            continue
        if PREMIUM_MARKER in chunk_n:
            premium = True
        if len(chunk_n) >= MIN_EXACT:
            out.append((chunk_n, pos, premium))
        pos += len(chunk) + 2
    return out


def sections_of(body: str) -> list:
    """H2-Kapitel (Text zwischen ##-Überschriften) für D5."""
    lines = body.split("\n")
    heads = [i for i, l in enumerate(lines) if re.match(r"^##\s+", l)]
    heads.append(len(lines))
    out = []
    for a, b in zip(heads[:-1], heads[1:]):
        sec = "\n".join(lines[a:b])
        sec_n = normalize(re.sub(r"```.*?```", " ", sec, flags=re.S))
        if len(sec_n) >= MIN_NEAR:
            out.append(sec_n)
    return out


def near_candidates(blocks: list, min_len: int):
    """Bucket-Strategie: vergleiche nur Blöcke ähnlicher Länge (Fenster ±1 Bucket)
    und gleichen Anfangsbuchstabens – vermeidet O(n²) über die ganze Flotte."""
    buckets = {}
    for b in blocks:
        key = (b[0][:1].lower(), len(b[0]) // 40)
        buckets.setdefault(key, []).append(b)
    for b in blocks:
        key = (b[0][:1].lower(), len(b[0]) // 40)
        for dk in (key[1] - 1, key[1], key[1] + 1):
            for o in buckets.get((key[0], dk), []):
                if o[0] < b[0]:
                    yield b, o


def check_article(path: Path, articles: list) -> list:
    """Gibt Liste von (artikel, regel, detail, pos) zurück."""
    rel = str(path.relative_to(ROOT))
    raw = path.read_text(encoding="utf-8")
    body = split_body(raw)
    blocks = blocks_of(body)
    finds = []

    # D1 + D2 (innerhalb Artikel)
    seen = {}
    for text, pos, premium in blocks:
        if is_boilerplate(text):
            continue
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if h in seen:
            finds.append((rel, "D1-EXAKT", f"Absatz doppelt (Z.{pos} ≈ Z.{seen[h]}): {text[:100]}…", pos))
            continue
        seen[h] = pos
    for a, b in near_candidates([bl for bl in blocks if not is_boilerplate(bl[0])], MIN_NEAR):
        ta, tb = a[0], b[0]
        if len(ta) < MIN_NEAR or len(tb) < MIN_NEAR:
            continue
        # Ratio-Obergrenze prüfen, bevor difflib läuft (schneller Filter)
        if min(len(ta), len(tb)) / max(len(ta), len(tb)) < RATIO_NEAR:
            continue
        if ta[:6] != tb[:6]:
            continue
        r = difflib.SequenceMatcher(None, ta, tb).ratio()
        if r >= RATIO_NEAR:
            finds.append((rel, "D2-NEAR",
                          f"Fast-Duplikat (Ratio {r:.2f}, Z.{a[1]} ≈ Z.{b[1]}): {ta[:90]}…", b[1]))

    # D5 (Sektions-Duplikate)
    secs = sections_of(body)
    for i in range(len(secs)):
        for j in range(i + 1, len(secs)):
            s1, s2 = secs[i], secs[j]
            if min(len(s1), len(s2)) / max(len(s1), len(s2)) < RATIO_NEAR:
                continue
            if s1[:10] == s2[:10]:
                r = difflib.SequenceMatcher(None, s1, s2).ratio()
                if r >= RATIO_NEAR:
                    finds.append((rel, "D5-SEKTION",
                                  f"Kapitel fast identisch (Ratio {r:.2f}): {s1[:80]}…", 0))

    # D6 (Premium-Anhänge): Blöcke nach dem Marker gegen frühere Blöcke
    premium_blocks = [b for b in blocks if b[2] and not is_boilerplate(b[0])]
    early_blocks = [b for b in blocks if not b[2] and not is_boilerplate(b[0])]
    if premium_blocks and early_blocks:
        early_ng = {ng for b in early_blocks for ng in ngrams(b[0], SHINGLE)}
        for text, pos, _ in premium_blocks:
            ng = ngrams(text, SHINGLE)
            hit = sum(1 for g in ng if g in early_ng)
            total = max(1, len(set(ng)))
            if hit >= 5 and hit / total >= 0.4:
                finds.append((rel, "D6-PREMIUM",
                              f"Premium-Anhang wiederholt früheren Text (Shingles {hit}/{total}): {text[:90]}…", pos))
    return finds


def ngrams(text: str, n: int) -> set:
    words = re.findall(r"[a-zäöüß0-9]+", text.lower())
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)} if len(words) >= n else set()


def fix_sections(body: str) -> tuple:
    """D5-Auto-Fix: fast identische H2-Kapitel (Ratio >= 0.92) – die spätere
    Version wird komplett entfernt (inkl. Überschrift). Nur Kapitel ohne
    Boilerplate und ohne Frontmatter-Bereich."""
    lines = body.split("\n")
    heads = [i for i, l in enumerate(lines) if re.match(r"^##\s+", l)]
    heads.append(len(lines))
    drop_ranges = set()
    removed = []
    for a in range(len(heads) - 1):
        for b in range(a + 1, len(heads) - 1):
            sec_a = "\n".join(lines[heads[a]:heads[a + 1]])
            sec_b = "\n".join(lines[heads[b]:heads[b + 1]])
            na = normalize(re.sub(r"```.*?```", " ", sec_a, flags=re.S))
            nb = normalize(re.sub(r"```.*?```", " ", sec_b, flags=re.S))
            if len(na) < MIN_NEAR or len(nb) < MIN_NEAR:
                continue
            if is_boilerplate(na) or is_boilerplate(nb):
                continue
            if min(len(na), len(nb)) / max(len(na), len(nb)) < RATIO_FIX - 0.1:
                continue
            r = difflib.SequenceMatcher(None, na, nb).ratio()
            if r >= RATIO_FIX:
                drop_ranges.add((heads[b], heads[b + 1]))
                removed.append(("D5-FIX", f"Kapitel {b + 1} entfernt (Ratio {r:.2f}): {na[:70]}…"))
                break
    if not drop_ranges:
        return body, 0, []
    keep = []
    prev = 0
    for start, end in sorted(drop_ranges):
        keep.append("\n".join(lines[prev:start]))
        prev = end
    keep.append("\n".join(lines[prev:]))
    return "\n".join(keep), len(removed), removed


def auto_fix(rel: str, body: str) -> tuple:
    """Entfernt exakte + fast-exakte Duplikate (spätere Version) im selben Artikel.
    Zwei Ebenen: Absätze (D1/D2) und H2-Kapitel (D5)."""
    blocks = blocks_of(body)
    if not blocks:
        return body, 0, []
    removed = []

    # Exakte Duplikate (D1)
    seen = {}
    keep_lines = []
    chunks = body.split("\n\n")
    for i, chunk in enumerate(chunks):
        c_n = normalize(re.sub(r"```.*?```", " ", chunk, flags=re.S))
        if not c_n:
            keep_lines.append(i)
            continue
        h = hashlib.sha256(c_n.encode("utf-8")).hexdigest()
        if len(c_n) >= MIN_EXACT and h in seen and "premium-length" not in c_n:
            removed.append(("D1-FIX", f"Z.{i}: {c_n[:70]}…"))
            continue
        seen[h] = i
        keep_lines.append(i)

    # Near-Duplikate (D2) mit hoher Schwelle (RATIO_FIX)
    keep = [chunks[i] for i in keep_lines]
    drop = set()
    cand = []
    for k, text in enumerate(keep):
        c_n = normalize(re.sub(r"```.*?```", " ", text, flags=re.S))
        if len(c_n) >= MIN_NEAR:
            cand.append((k, c_n))
    for i in range(len(cand)):
        for j in range(i + 1, len(cand)):
            ti, tj = cand[i][1], cand[j][1]
            if min(len(ti), len(tj)) / max(len(ti), len(tj)) < RATIO_FIX - 0.1:
                continue
            if ti[:6] != tj[:6]:
                continue
            r = difflib.SequenceMatcher(None, ti, tj).ratio()
            len_diff = abs(len(ti) - len(tj)) / max(len(ti), len(tj))
            if r >= RATIO_FIX and len_diff <= FIX_LEN_DIFF:
                # spätere Version entfernen (größerer Index)
                later = max(i, j)
                if later not in drop:
                    drop.add(later)
                    removed.append(("D2-FIX", f"Absatz {later}: {ti[:70]}…"))

    out = "\n\n".join(ch for k, ch in enumerate(keep) if k not in drop)

    # Zweite Ebene: H2-Kapitel-Duplikate (D5)
    out2, n5, rem5 = fix_sections(out)
    removed.extend(rem5)
    return out2, len(removed), removed


def run_selftest() -> list:
    fehler = []
    # Fall 1: exaktes Duplikat wird erkannt (D1-Logik direkt geprüft)
    b1 = ("Einleitung.\n\n"
          "Das ist ein längerer Beispielabsatz mit mehreren Wörtern, der exakt doppelt vorkommt und "
          "deshalb als Duplikat gelten muss, weil er wortgleich wiederholt wird.\n\n"
          "Das ist ein längerer Beispielabsatz mit mehreren Wörtern, der exakt doppelt vorkommt und "
          "deshalb als Duplikat gelten muss, weil er wortgleich wiederholt wird.")
    blocks = blocks_of(b1)
    hashes = [hashlib.sha256(t.encode()).hexdigest() for t, _, _ in blocks]
    if len(hashes) == len(set(hashes)):
        fehler.append("Fall 1 (D1-Erkennung): exaktes Duplikat nicht erkannt")
    # Fall 2: Auto-Fix entfernt exaktes Duplikat
    out, n, _ = auto_fix("t", b1)
    if n != 1 or out.count("Beispielabsatz") != 1:
        fehler.append(f"Fall 2 (D1-Fix): erwartet 1 Entfernung/1 Treffer, bekam {n}/{out.count('Beispielabsatz')}")
    # Fall 3: verschiedene Absätze werden NICHT gefixt (kein False-Positive)
    b2 = "Absatz eins über Stromsparen und ganz andere Inhalte.\n\nAbsatz zwei über Versicherungen mit völlig anderen Themen."
    _, n2, _ = auto_fix("t", b2)
    if n2 != 0:
        fehler.append(f"Fall 3 (False-Positive): unabhängige Absätze gefixt ({n2})")
    # Fall 4: D6-Marker-Erkennung (Premium-Anhänge werden als solche markiert)
    b3 = ("Erster Teil des Artikels mit ausreichend langem Inhalt, der über achtzig Zeichen "
          "hinausgeht und deshalb als Block zählt.\n\n<!-- premium-length-2026 -->\n\n"
          "Zweiter Teil des Artikels, ebenfalls lang genug, mit dem Premium-Marker davor "
          "und Inhalt, der als Anhang markiert werden muss.")
    early = [b for b in blocks_of(b3) if not b[2]]
    late = [b for b in blocks_of(b3) if b[2]]
    if not (early and late and late[0][2]):
        fehler.append("Fall 4 (D6-Marker): Premium-Marker-Erkennung fehlgeschlagen")
    # Fall 5: Near-Duplikat-Erkennung (D2) über blocks_of + buckets
    b5 = ("Kurz.\n\n"
          "Der DNS-Server ist wie ein Telefonbuch des Internets und übersetzt Namen in Adressen, "
          "damit dein Browser die richtige Seite findet und lädt.\n\n"
          "Der DNS-Server ist wie ein Telefonbuch des Internets und übersetzt Namen in Adressen, "
          "damit dein Browser die richtige Seite findet und lädt – fast wortgleich wiederholt.")
    b5_blocks = blocks_of(b5)
    pairs = list(near_candidates(b5_blocks, MIN_NEAR))
    hit = any(difflib.SequenceMatcher(None, a[0], b[0]).ratio() >= RATIO_NEAR
              for a, b in pairs)
    if not hit:
        fehler.append("Fall 5 (D2-Near): Fast-Duplikat nicht erkannt")
    return fehler


def main() -> int:
    fehler = run_selftest()
    if fehler or SELFTEST_ONLY:
        for f in fehler:
            print("🛑 " + f)
        if fehler:
            print("SELFTEST FEHLGESCHLAGEN – nichts geschrieben.")
            return 2
        print("✅ Duplikat-Selbsttest: 4 Fälle grün.")
        return 0

    today = date.today().isoformat()
    paths = sorted(POSTS.glob("*/index.md"))
    paths = [p for p in paths if p.name != "_index.md"]
    if NEW_ONLY:
        paths = [p for p in paths
                 if re.search(rf"^date:\s*\"?{today}", p.read_text(encoding="utf-8"), re.M)
                 and "draft: false" in p.read_text(encoding="utf-8")]
        if not paths:
            print("Duplikat-Gate: keine neuen Artikel heute – OK.")
            return 0

    all_finds, fixed_any = [], False
    for p in paths:
        raw = p.read_text(encoding="utf-8")
        body = split_body(raw)
        if DO_FIX:
            new_body, n, removed = auto_fix(str(p.relative_to(ROOT)), body)
            if n:
                p.write_text(raw.replace(body, new_body), encoding="utf-8")
                fixed_any = True
                for _, d in removed:
                    all_finds.append((str(p.relative_to(ROOT)), "FIX", d, 0))
                print(f"  ✂ {p.relative_to(ROOT)}: {n} Duplikat(e) entfernt")
        all_finds += check_article(p, paths)

    # deduplizieren (Fix + Check desselben Fundes)
    uniq, seen = [], set()
    for f in all_finds:
        k = (f[0], f[1], f[2][:60])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(f)

    d1 = [f for f in uniq if f[1] == "D1-EXAKT"]
    d2 = [f for f in uniq if f[1] == "D2-NEAR"]
    d3 = [f for f in uniq if f[1] == "D3-X"]
    d4 = [f for f in uniq if f[1] == "D4-X"]
    d5 = [f for f in uniq if f[1] == "D5-SEKTION"]
    d6 = [f for f in uniq if f[1] == "D6-PREMIUM"]
    fx = [f for f in uniq if f[1] == "FIX"]

    # Report
    lines = [f"# 🔁 DUPLIKAT-REPORT (duplikat_guard.py)",
             f"**Stand:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · Modus: {'FIX' if DO_FIX else 'REPORT'}" +
             (" · Engine (nur heute)" if NEW_ONLY else ""),
             "",
             f"| Regel | Anzahl |",
             f"|---|---|",
             f"| D1 Exakt (im Artikel) | {len(d1)} |",
             f"| D2 Near (im Artikel) | {len(d2)} |",
             f"| D5 Sektion (im Artikel) | {len(d5)} |",
             f"| D6 Premium-Anhang | {len(d6)} |",
             f"| Auto-Fixes | {len(fx)} |",
             ""]
    if uniq:
        lines.append("## Fundstellen (Auswahl)")
        for rel, regel, detail, pos in uniq[:40]:
            lines.append(f"- `{rel}` **{regel}**: {detail}")
    lines.append("")
    lines.append("_Kein Duplikat darf den Leser zweimal dieselbe Information lesen lassen._")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    with HISTORY.open("a", encoding="utf-8") as h:
        h.write(json.dumps({"date": today, "d1": len(d1), "d2": len(d2), "d5": len(d5),
                            "d6": len(d6), "fix": len(fx)}, ensure_ascii=False) + "\n")

    if AS_JSON:
        print(json.dumps({"duplicates": [{"file": f[0], "rule": f[1], "detail": f[2]} for f in uniq]},
                         ensure_ascii=False, indent=2))
        return 1 if (d1 or d2 or d5 or d6) and NEW_ONLY else 0

    print(f"Duplikat-Audit: {len(paths)} Artikel | D1 {len(d1)} · D2 {len(d2)} · D5 {len(d5)} · D6 {len(d6)} · Fixes {len(fx)}")
    for rel, regel, detail, pos in uniq[:25]:
        print(f"  {'❌' if regel.startswith('D') else '✂'} [{regel:>10}] {rel} Z.{pos}: {detail[:110]}")
    if NEW_ONLY and (d1 or d2 or d5 or d6):
        print("❌ Duplikat-Gate nicht bestanden – neue Artikel enthalten Redundanz!")
        return 1
    if not uniq:
        print("✅ Keine Duplikate gefunden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
