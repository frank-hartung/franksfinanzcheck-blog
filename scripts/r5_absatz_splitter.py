#!/usr/bin/env python3
"""
R5-ABSATZ-SPLITTER (Audit 01.09.2026, P0-Punkt 5: „Eine Idee pro Absatz").

Splittet Fließtext-Absätze mit mehr als 4 Sätzen an Satzgrenzen in zwei
Absätze (möglichst 2+3 oder 3+2 Sätze), ohne Markdown-Links zu zerschneiden
und ohne Abkürzungen (z. B., d. h., u. a., 18.000) als Satzende zu werten.

Verifikation: python3 scripts/textverstaendnis_guard.py --json
  → Anzahl R5-ABSATZ-Funde muss sinken, keine neuen harten Fälle.

Nutzung:
  python3 scripts/r5_absatz_splitter.py            # Vorschau (dry-run)
  python3 scripts/r5_absatz_splitter.py --apply    # schreibt Dateien
"""
import re
import sys
import glob

APPLY = "--apply" in sys.argv
MAX_SENT = 4

# Abkürzungen, deren Punkt kein Satzende ist (werden geschützt)
ABBR = re.compile(r'\b(z\.\s?b\.|d\.\s?h\.|u\.\s?a\.|etc\.|usw\.|bzw\.|inkl\.|ggf\.|ca\.|Nr\.|S\.|Abs\.|Mio\.|Mrd\.|vgl\.|St\.)\b', re.I)

def protect(text: str) -> tuple[str, list[str]]:
    tokens: list[str] = []
    def repl(m: re.Match) -> str:
        tokens.append(m.group(0))
        return f"\x00{len(tokens)-1}\x00"
    return ABBR.sub(repl, text), tokens

def restore(text: str, tokens: list[str]) -> str:
    def repl(m: re.Match) -> str:
        return tokens[int(m.group(1))]
    return re.sub(r'\x00(\d+)\x00', repl, text)

def split_para(para: str) -> str | None:
    """Teilt para an einer sinnvollen Satzgrenze. Gibt None, wenn nicht nötig."""
    p, tokens = protect(para)
    # Datumspunkte schützen
    p = re.sub(r'(\b\d{1,2})\.\s+([A-ZÄÖÜ][a-zäöüß]{2,}\b)', r'\1 \2', p)
    # Satzenden finden (inkl. schließender Klammer/Quote, danach Großbuchstabe/Zahl/Anführung)
    ends = [m.end() for m in re.finditer(r'[.!?][)\"]?\s+(?=[A-ZÄÖÜ0-9„"\[])', p)]
    if not ends:
        return None
    n_sents = len(ends) + 1
    if n_sents <= MAX_SENT:
        return None
    # bevorzugte Bruchstelle: Ende des 2. Satzes (2+3), sonst des 3. (3+2)
    for k in (2, 3):
        if k < len(ends):
            cut = ends[k-1]
            break
    else:
        cut = ends[len(ends)//2]
    a, b = p[:cut], p[cut:]
    a = restore(a, tokens)
    b = restore(b, tokens)
    return (a.rstrip() + "\n\n" + b.lstrip()).rstrip() + "\n"

def paras_with_many_sents(body: str):
    out = []
    for para in body.split("\n\n"):
        s = para.strip()
        if not s or s.startswith(("#", "*", "-", "|", ">", "<", "!", "{", "[")):
            continue
        # nur echte Fließtext-Absätze
        first = s.split("\n", 1)[0]
        if re.match(r'^\s*\d+\.\s', first):
            continue
        p, tokens = protect(s)
        p2 = re.sub(r'(\b\d{1,2})\.\s+([A-ZÄÖÜ][a-zäöüß]{2,}\b)', r'\1 \2', p)
        n = len(re.findall(r'[.!?][)\"]?\s+(?=[A-ZÄÖÜ0-9„"\[])', p2)) + 1
        if n > MAX_SENT:
            out.append((s, n))
    return out

def main() -> int:
    files = sorted(glob.glob("content/posts/*/index.md"))
    total, changed_files = 0, []
    for f in files:
        t = open(f, encoding="utf-8").read()
        body = t.split("---", 2)[2]
        hits = paras_with_many_sents(body)
        if not hits:
            continue
        print(f"\n=== {f} ({len(hits)} Absätze)")
        new_body = body
        for para, n in hits:
            res = split_para(para)
            if not res:
                continue
            assert new_body.count(para) == 1, f"{f}: Mehrfachfund"
            new_body = new_body.replace(para, res, 1)
            total += 1
            print(f"  [{n}→2 Sätze] {para[:60]}…")
        if new_body != body:
            if APPLY:
                open(f, "w", encoding="utf-8").write(t.split("---", 2)[0] + "---" + t.split("---", 2)[1] + "---" + new_body)
            changed_files.append(f)
    print(f"\n{total} Absätze gesplittet in {len(changed_files)} Dateien"
          + (" (geschrieben)" if APPLY else " (dry-run – --apply zum Schreiben)"))
    return 0

if __name__ == "__main__":
    sys.exit(main())
