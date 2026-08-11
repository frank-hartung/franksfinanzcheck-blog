#!/usr/bin/env python3
"""
Einzigartigkeits-Audit für alle Blog-Artikel.

Prüft:
  1) Jeden Artikel gegen die Pinterest-Pin-Texte (Quelle: data/pinterest_plan.yaml)
  2) Jeden Artikel gegen alle anderen Artikel (interne Duplikate)
  3) SAME-DAY-TWINS: Titel-/Themen-Aehnlichkeit innerhalb desselben
     Kalendertags (Keyword-Kannibalisierung verhindern, 11.08.2026 –
     Anlass: Gas-Zwilling). --fix heilt: juengerer Zweitling → draft:true.

WICHTIG: Template-Bausteine (Werbekennzeichnung, Affiliate-CTA, FAQ-Rahmen)
werden VOR dem Vergleich entfernt – nur der echte Fließtext zählt.

SABOTAGE-SCHUTZ: SELFTEST_SAMEDAY (6 eingefrorene Faelle inkl. echtem
Fall) laeuft vor jedem Audit; Abweichung → Exit 2.

Nutzung:
    python3 scripts/check_uniqueness.py            # alle Artikel prüfen
    python3 scripts/check_uniqueness.py --strict   # strengere Schwelle (5-Wort-Phrasen)
    python3 scripts/check_uniqueness.py --sameday --fix  # Geburts-Modus (Engine)
"""
import os
import re
import sys
from itertools import combinations

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
from post_utils import list_post_paths
PINTEREST_PLAN = os.path.join(BLOG_DIR, "data", "pinterest_plan.yaml")

PHRASE_LEN = int(os.environ.get("PHRASE_LEN", "7"))
MAX_SIMILAR = int(os.environ.get("MAX_SIMILAR", "1"))


def norm(s):
    s = s.lower()
    s = re.sub(r"[äàáâ]", "ae", s)
    s = re.sub(r"[öòóô]", "oe", s)
    s = re.sub(r"[üùúû]", "ue", s)
    s = re.sub(r"ß", "ss", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def clean_body(content):
    """Entfernt Frontmatter und alle Template-Bausteine → nur Fließtext."""
    parts = content.split("---", 2)
    body = parts[2] if len(parts) == 3 else content
    # Werbekennzeichnung (variiert in Zeilenumbrüchen)
    body = re.sub(r"\*?Dieser Artikel enthält Affiliate-Links.*?(Mehrkosten|Mehrkosten\.)\*?", " ", body, flags=re.S)
    # Affiliate-CTA-Blöcke (👉 ... Link ...)
    body = re.sub(r"👉.*?\)", " ", body, flags=re.S)
    # ROBUST: ALLE URLs entfernen (unabhängig vom CTA-Format – der Polish
    # variiert den CTA-Text, dadurch blieben URL-Bruchstücke als
    # "Duplikate" im Audit zurück)
    body = re.sub(r"https?://[^\s)\"']+", " ", body)
    body = re.sub(r"www\.[^\s)\"']+", " ", body)
    # Markdown-Links: nur den Ankertext behalten. Interne Link-ZIELE
    # (../../posts/slug/) sind Navigation, kein Inhalt – sonst erzeugen
    # identische Link-Ziele in mehreren Artikeln falsche "Duplikate".
    body = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", body)
    # FAQ-Intro-Standardsätze
    body = re.sub(r"## Häufige Fragen", " ", body)
    # Übrige Markdown-Syntax
    body = re.sub(r"[*_#>`|~-]{1,}", " ", body)
    return body


def ngrams(text, n):
    words = re.findall(r"\w+", norm(text))
    return set(" ".join(words[i:i + n]) for i in range(len(words) - n + 1))


def load_pinterest_plan():
    pins = []
    if not os.path.exists(PINTEREST_PLAN):
        return pins
    current = None
    with open(PINTEREST_PLAN, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("- tag:"):
                current = {"tag": line.split(":", 1)[1].strip()}
                pins.append(current)
            elif current and ":" in line:
                key, val = line.split(":", 1)
                current[key.strip()] = val.strip().strip("\"'")
    return pins


def find_pin_for_topic(topic_title, pins):
    t = norm(topic_title)
    best, best_score = None, 0
    for p in pins:
        ref = norm((p.get("titel") or "") + " " + (p.get("pinwand") or ""))
        score = 0
        t_tokens = t.split()
        ref_tokens = ref.split()
        for i in range(min(len(t_tokens), 6)):
            if i < len(ref_tokens) and t_tokens[i] == ref_tokens[i]:
                score += 1
        if score > best_score:
            best, best_score = p, score
    return best if best_score >= 2 else None


# ============================================================
#  3) SAME-DAY-TWIN-RADAR (11.08.2026, Frank-Auftrag)
#  Anlass: Zwei Lebendiges zum selben Gas-Thema am selben Tag
#  (Keyword-Kannibalisierung!). Faengt Titel-/Themen-Aehnlichkeit
#  innerhalb desselben Kalendertags. --fix heilt selbst: der
#  juengere Zweitling wird draft:true gesetzt (Alias bewahrt sein
#  URL-Kapital), der aeltere ist kanonisch. Sabotage-Schutz via
#  SELFTEST unten (Exit 2 vor jeder Schreibaktion).
# ============================================================
STOP = set("""der die das ein eine einem einer einem einen so du dich dein deine
sich vor gegen mit und oder aber ist sind als zum zur im in am an auf aus wie
was wer wann warum sicherst schuetzt einfach erklaert leicht gemacht ab
vergleich vergleichen vergleichs vergleichstabelle""".split())
SAMEDAY_JACCARD = 0.25  # fuzzy-Jaccard (Komposita werden aufgesplittet)


def title_sig(title: str) -> set:
    # Generische Vergleichs-Vokabeln + Jahreszahlen (überall gleich) zählen nicht.
    return {t for t in norm(title).split()
            if t not in STOP and len(t) >= 3 and not re.fullmatch(r"20\d\d", t)}


def _tok_match(a: str, b: str) -> bool:
    """Gleich ODER Kompositum-Teildach: gaspreisgarantie ~ preisgarantie."""
    if a == b:
        return True
    return len(a) >= 6 and len(b) >= 6 and (a in b or b in a)


def same_day_twin(t_a: str, t_b: str) -> bool:
    a, b = title_sig(t_a), title_sig(t_b)
    if not a or not b:
        return False
    inter = max(sum(1 for x in a if any(_tok_match(x, y) for y in b)),
                sum(1 for y in b if any(_tok_match(x, y) for x in a)))
    return inter / (len(a) + len(b) - inter) >= SAMEDAY_JACCARD


SELFTEST_SAMEDAY = [
    # DER echte Zwillings-Fall vom 11.08.2026:
    ("Gaspreisgarantie: So sicherst du dich gegen Preissprünge ab",
     "Preisgarantie Gas: So schützt du dich vor Preiserhöhungen", True),
    ("DSL-Wechselbonus sichern: So holst du dir das Extra",
     "DSL-Wechselbonus – das Extra ist größer als gedacht", True),
    ("Mietwagen buchen – die besten Tricks", "Mietwagen buchen im Urlaub", True),
    ("Tagesgeld-Zinsen 2026 im Vergleich", "Handytarife vergleichen 2026", False),
    ("50-30-20-Regel einfach erklärt", "Haushaltsbuch führen leicht gemacht", False),
    ("Kfz-Versicherung wechseln", "Handyvertrag kündigen", False),
]


def run_selftest() -> list:
    fehler = []
    for i, (a, b, want) in enumerate(SELFTEST_SAMEDAY, 1):
        got = same_day_twin(a, b)
        if got != want:
            fehler.append(f"  Fall {i}: erwartet „{want}“, bekam „{got}“  ← {a[:40]!r} ↔ {b[:40]!r}")
    return fehler


def heal_twin(path_younger: str) -> bool:
    """Setzt den juengeren Zweitling auf draft:true (stopft Publication)."""
    with open(path_younger, encoding="utf-8") as f:
        src = f.read()
    m = re.search(r"(?m)^draft:\s*false\s*$", src)
    if not m:
        return False
    src = src[:m.start()] + "draft: true" + src[m.end():]
    with open(path_younger, "w", encoding="utf-8") as f:
        f.write(src)
    return True


def main():
    # SABOTAGE-SCHUTZ zuerst: Same-Day-Twin-Radar prueft sich selbst,
    # bevor irgendetwas gemeldet oder geheilt wird.
    fehler = run_selftest()
    if fehler:
        print("🛑 UNIQUENESS-SELBSTTEST FEHLGESCHLAGEN – Sabotage verhindert.")
        print("   Kein Audit, keine Heilung. Bitte same_day_twin() prüfen:")
        print("\n".join(fehler))
        sys.exit(2)
    print(f"✅ Selbsttest: {len(SELFTEST_SAMEDAY)} Twin-Faelle stimmen.")

    strict = "--strict" in sys.argv
    do_fix = "--fix" in sys.argv
    only_sameday = "--sameday" in sys.argv
    n = 5 if strict else PHRASE_LEN
    max_sim = 1 if strict else MAX_SIMILAR

    articles = {}
    titles = {}
    drafts = set()
    dates = {}
    for path in list_post_paths():
        content = open(path, encoding="utf-8").read()
        m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.M)
        titles[path] = m.group(1) if m else path
        articles[path] = clean_body(content)
        if re.search(r'(?m)^draft:\s*true', content):
            drafts.add(path)
        dm = re.search(r'(?m)^date:\s*["\']?([0-9T:\-]+)', content)
        dates[path] = dm.group(1) if dm else ""

    # 3) Same-Day-Twin-Radar (laeuft immer zuerst; bei --sameday: NUR dieser)
    print("=== 3) Same-Day-Zwillinge (Titel-/Themen-Aehnlichkeit, gleicher Tag) ===")
    same_crit = 0
    healed = []
    by_day = {}
    for fn in articles:
        base = os.path.basename(os.path.dirname(fn))
        dm = re.match(r"(20\d\d-\d\d-\d\d)", base)
        if dm and fn not in drafts:
            by_day.setdefault(dm.group(1), []).append(fn)
    for day, fns in sorted(by_day.items()):
        for a, b in combinations(sorted(fns), 2):
            if same_day_twin(titles[a], titles[b]):
                same_crit += 1
                print(f"  🚨 TWIN am {day}: {os.path.basename(os.path.dirname(a))}")
                print(f"               ↔ {os.path.basename(os.path.dirname(b))}")
                print(f"               ({titles[a][:44]!r} ↔ {titles[b][:44]!r})")
                if do_fix:
                    loser = max(a, b, key=lambda p: (dates.get(p, ""), p))
                    if heal_twin(loser):
                        drafts.add(loser)
                        healed.append(os.path.basename(os.path.dirname(loser)))
                        print(f"               🛠️ geheilt: Zweitling {os.path.basename(os.path.dirname(loser))} → draft:true")
    if not same_crit:
        print("  ✅ Keine Same-Day-Zwillinge")
    if only_sameday:
        if same_crit:
            print(f"\nErgebnis: {same_crit} Same-Day-Zwilling(e)" + (f", geheilt: {len(healed)}" if healed else ""))
            sys.exit(0 if healed else 1)
        print("\n✅ Geburtstag sauber – kein Zwilling.")
        sys.exit(0)

    print(f"Prüfe {len(articles)} Artikel (Phrasenlänge: {n}, max. ähnlich: {max_sim})\n")

    # 1) Gegen Pinterest-Pins
    pins = load_pinterest_plan()
    print("=== 1) Vergleich mit Pinterest-Pins ===")
    pin_problems = 0
    for fn in sorted(articles):
        pin = find_pin_for_topic(titles[fn], pins)
        if not pin:
            continue
        ref = norm((pin.get("titel") or "") + " " + (pin.get("beschreibung") or "") + " " + (pin.get("keywords") or ""))
        ref_words = ref.split()
        if len(ref_words) < n:
            continue
        ref_grams = set(" ".join(ref_words[i:i + n]) for i in range(len(ref_words) - n + 1))
        my_grams = ngrams(articles[fn], n)
        hits = len(my_grams & ref_grams)
        if hits > max_sim:
            pin_problems += 1
            print(f"  ⚠️ {fn[:45]}: {hits} gleiche Phrasen mit Pin (Tag {pin.get('tag')})")
    if not pin_problems:
        print("  ✅ Alle Artikel einzigartig gegenüber den Pin-Texten")

    # 2) Interne Duplikate
    print("\n=== 2) Interne Duplikate (Artikel untereinander) ===")
    names = sorted(articles.keys())
    grams = {fn: ngrams(articles[fn], n) for fn in names}
    internal = 0
    critical = 0
    for a, b in combinations(names, 2):
        overlap = len(grams[a] & grams[b])
        if overlap > max_sim:
            internal += 1
            if overlap >= 5:
                critical += 1
                print(f"  🚨 KRITISCH {a[:32]} ↔ {b[:32]}: {overlap} gleiche Phrasen")
            else:
                print(f"  ℹ️ unkritisch {a[:32]} ↔ {b[:32]}: {overlap} Phrasen (Standard-Formulierungen)")
    if not internal:
        print("  ✅ Keine internen Duplikate")
    else:
        print(f"  (davon kritisch: {critical} – unter 5 Phrasen ist normal und kein Duplicate Content)")

    same_open = same_crit - len(healed)
    print(f"\nErgebnis: Pin-Konflikte: {pin_problems} | Interne Überlappungen: {internal} | Kritisch: {critical} | Same-Day-Twins: {same_crit} (geheilt: {len(healed)})")

    # Exit-Code für CI/Automatisierung:
    #   0 = alles ok (keine kritischen Probleme)
    #   1 = kritische Duplikate gefunden → Workflow bricht ab, nichts wird veröffentlicht
    #   2 = SELBSTTEST fehlgeschlagen (Sabotage-Schutz)
    if pin_problems > 0 or critical > 0 or same_open > 0:
        print("\n⚠️ KRITISCHE DUPLIKATE GEFUNDEN – Bitte Artikel überarbeiten, bevor veröffentlicht wird.")
        print("  Tipp: Betroffene Passagen umformulieren und Audit erneut ausführen.")
        sys.exit(1)
    else:
        print("\n✅ Audit bestanden – alle Artikel sind einzigartig.")


if __name__ == "__main__":
    main()
