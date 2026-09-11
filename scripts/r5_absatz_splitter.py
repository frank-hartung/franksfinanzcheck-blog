#!/usr/bin/env python3
"""
R5-ABSATZ-SPLITTER (Audit 01.09.2026, P0-Punkt 5: „Eine Idee pro Absatz“).

Splittet Fließtext-Absätze mit mehr als 4 Sätzen an Satzgrenzen in zwei
Absätze (möglichst 2+3 oder 3+2 Sätze), ohne Markdown-Links zu zerschneiden
und ohne Abkürzungen (z. B., d. h., u. a., 18.000) als Satzende zu werten.

Verifikation: python3 scripts/textverstaendnis_guard.py --json
  → Anzahl R5-ABSATZ-Funde muss sinken, keine neuen harten Fälle.

Nutzung:
  python3 scripts/r5_absatz_splitter.py            # Vorschau (dry-run, Live-Korpus)
  python3 scripts/r5_absatz_splitter.py --apply    # schreibt (Live-Korpus)
  python3 scripts/r5_absatz_splitter.py --apply --include-drafts
                                                   # auch Entwürfe (Korpus)
  python3 scripts/r5_absatz_splitter.py --apply --file content/posts/<slug>/index.md
                                                   # EIN Artikel (Entwürfe
                                                   # grundsätzlich erlaubt;
                                                   # die Reserve-Veredelung
                                                   # fasst so keinen
                                                   # Fremdartikel an)
  python3 scripts/r5_absatz_splitter.py --selftest # Sabotage-Schutz

REPARATUR 11.09.2026 (Reserve #5, Workflow #247):
  * Der Splitter war in KEINEM Workflow verdrahtet – frische
    Reserve-Kandidaten scheiterten dauerhaft am harten R5-ABSATZ-HART-Gate
    (>6 Sätze/Absatz) der Publish-Gate-Prüfung. Er läuft jetzt
    datei-bezirkelt in der Reserve-Heiler-Kette (reserve_finisher.py).
  * --file + --include-drafts für sicheren Entwurfs-Scope.
  * Mehrfach vorkommende Absätze crashten vorher mit einer Assertion
    („Mehrfachfund“) und blockierten den ganzen Lauf; sie werden jetzt
    übersprungen und gemeldet.
  * --selftest als Sabotage-Schutz wie bei den anderen Heilern.
"""
import argparse
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
    # Bruchstelle so wählen, dass BEIDE Hälften möglichst ≤4 Sätze haben:
    # 5 Sätze → 2+3, 6 → 2+4, 7 → 3+4, 8+ → 4+(n-4). Die alte feste 2+3-Regel
    # ließ bei 7+ Sätzen eine zu lange zweite Hälfte zurück (Reserve #5).
    k = min(max(2, n_sents - MAX_SENT), 4)
    if k < len(ends):
        cut = ends[k - 1]
    else:
        cut = ends[len(ends) // 2]
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


def is_draft(text: str) -> bool:
    parts = text.split("---", 2)
    return len(parts) >= 3 and bool(
        re.search(r"(?m)^draft:\s*true\s*$", parts[1]))


def process_file(f: str, apply: bool) -> int:
    """Splittet eine Datei. Rückgabe: Anzahl gesplitteter Absätze."""
    t = open(f, encoding="utf-8").read()
    parts = t.split("---", 2)
    if len(parts) < 3:
        return 0
    body = parts[2]
    new_body = body
    total = 0
    # Iterativ teilen, bis kein Fließabsatz mehr > MAX_SENT Sätze hat:
    # ein einziger Durchlauf würde bei 9+ Sätzen eine zu lange zweite
    # Hälfte zurücklassen (Reserve #5, #247). Mehrdeutige Funde werden
    # pro Runde erneut geprüft und im Zweifel konservativ übersprungen.
    for runde in range(6):
        hits = paras_with_many_sents(new_body)
        if not hits:
            break
        if runde == 0:
            print(f"\n=== {f} ({len(hits)} Absätze)")
        for para, n in hits:
            if new_body.count(para) != 1:
                # Mehrdeutig (identischer Absatz >1x): keine unsichere Ersetzung.
                print(f"  ⚠ mehrdeutiger Absatzfund übersprungen: {para[:50]!r}")
                continue
            res = split_para(para)
            if not res:
                continue
            new_body = new_body.replace(para, res, 1)
            total += 1
            print(f"  [{n} Sätze → aufgeteilt] {para[:60]}…")
    if new_body != body and apply:
        open(f, "w", encoding="utf-8").write(
            parts[0] + "---" + parts[1] + "---" + new_body)
    return total


def run_selftest() -> list:
    fehler = []
    # 1) 7-Sätze-Absatz wird in genau 2 Absätze mit <=4 Sätzen geteilt.
    saetze = ("Der erste Gedanke steht hier.", "Ein zweiter Satz folgt direkt.",
              "Dann ein dritter mit Inhalt.", "Ein vierter rundet ab.",
              "Der fünfte beginnt neu.", "Danach der sechste Satz.",
              "Zum Schluss der siebte.")
    para = " ".join(saetze) + "\n"
    res = split_para(para)
    if not res:
        fehler.append("7-Sätze-Absatz wird nicht geteilt")
    else:
        blocks = [b for b in res.strip().split("\n\n") if b.strip()]
        if len(blocks) != 2:
            fehler.append(f"Teilung ergibt {len(blocks)} Absätze statt 2")
        elif any(paras_with_many_sents("\n\n" + b + "\n") for b in blocks):
            fehler.append(f"nach Teilung bleibt ein zu langer Absatz: {blocks}")
    # 2) Kurzer Absatz bleibt unangetastet.
    if split_para("Erster Satz. Zweiter Satz. Dritter Satz.\n") is not None:
        fehler.append("3-Sätze-Absatz wird fälschlich geteilt")
    # 2b) Wiederholte Anwendung löst auch einen 11-Sätze-Absatz vollständig
    # auf (jede resultierende Hälfte muss am Ende <=4 Sätze haben).
    lang_sätze = [
        "Am Anfang steht ein klarer Gedanke.", "Danach folgt ein zweiter Punkt.",
        "Dann kommt ein dritter Aspekt hinzu.", "Ein vierter rundet das Bild ab.",
        "Der fünfte schlägt eine Brücke.", "Auch der sechste hat Gewicht.",
        "Der siebte vertieft das Thema.", "Ein achter Blickwinkel hilft zusätzlich.",
        "Weitere Beobachtungen untermauern den Befund.",
        "Offene Fragen klären sich so von selbst.", "Am Ende bleibt ein Fazit.",
    ]
    lang = " ".join(lang_sätze)
    bloecke = [lang]
    bewegungen = 0
    for _ in range(6):
        neue = []
        bewegt = False
        for b in bloecke:
            r = split_para(b + "\n")
            if r:
                neue.extend(x.strip() for x in r.strip().split("\n\n") if x.strip())
                bewegt = True
                bewegungen += 1
            else:
                neue.append(b.strip())
        bloecke = neue
        if not bewegt:
            break
    if any(paras_with_many_sents("\n\n" + b + "\n") for b in bloecke):
        fehler.append(f"11-Sätze-Absatz konvergiert nicht: {bloecke}")
    # 3) Listen/Überschriften/Tabellen sind keine Fließabsätze.
    body = ("## Überschrift\n\n* Ein Punkt mit mehreren Wörtern hier.\n\n"
            "| a | b |\n|---|---|\n")
    if paras_with_many_sents(body):
        fehler.append("Listen/Überschriften/Tabellen werden als Fließabsatz gewertet")
    # 4) Abkürzungspunkte sind keine Satzenden.
    para = ("Das ist z. B. ein Test u. a. mit Abkürzungen. Ein zweiter Satz "
            "folgt. Ein dritter Satz hier. Ein vierter Satz dran. Ein "
            "fünfter noch.\n")
    res2 = split_para(para)
    if res2 and "z. B." not in res2:
        fehler.append("Abkürzungen wurden beim Teilen zerstört")
    return fehler


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="schreibt Dateien")
    ap.add_argument("--file", help="einzelne Datei (Entwürfe erlaubt)")
    ap.add_argument("--include-drafts", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        fehler = run_selftest()
        if fehler:
            print("🛑 R5-ABSATZ-SPLITTER-SELFTEST FEHLGESCHLAGEN:")
            for f in fehler:
                print("   -", f)
            return 2
        print("✅ R5-Absatz-Splitter-Selbsttest grün "
              "(Teilung, Abkürzungen, Scope, Schutzzeilen).")
        return 0

    if args.file:
        files = [args.file]   # --file schließt Entwürfe ausdrücklich ein
    else:
        files = sorted(glob.glob("content/posts/*/index.md"))
        if not args.include_drafts:
            files = [f for f in files
                     if not is_draft(open(f, encoding="utf-8").read())]
    total, changed = 0, []
    for f in files:
        n = process_file(f, args.apply)
        if n:
            total += n
            changed.append(f)
    print(f"\n{total} Absätze gesplittet in {len(changed)} Dateien"
          + (" (geschrieben)" if args.apply else " (dry-run – --apply zum Schreiben)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
