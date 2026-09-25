#!/usr/bin/env python3
"""
TOP-LEVEL-GRAMMATIKPRÜFUNG für FranksFinanzcheck (LanguageTool-Nachbau, OFFLINE).

UMBAU 25.09.2026 (Frank-Auftrag): „grammar_check soll auch komplett offline,
ohne API funktionieren." Die öffentliche LanguageTool-API (api.languagetool.org)
ist damit AUSGEWICKELT – dieser Check läuft ab sofort 100 % lokal, kostenlos,
ohne Netz, ohne Schlüssel, ohne externe Dienste (DSGVO: null Datenabfluss).
Was LanguageTool online lieferte, wird hier als deterministischer Regelsatz
NACHGEBAUT (Rechtschreibung, Zeichensetzung, Kontext-Fälle, Fehlschreibungen).

GEPRÜFT WERDEN (Regel-Ebenen, offline):
  LT1  Partikel-Fallen      „wo mit" → „womit", „an Hand" → „anhand" …
  LT2  Kollokations-Kanon   „im gegensatz" → „im Gegensatz", „zu hause" → „zu Hause" …
  LT3  Kontext-Fälle        „seid drei Jahren" → „seit drei Jahren" (NEGATIV:
                            „ihr seid bereit" bleibt!), „wieder Erwarten" →
                            „wider Erwarten", „vorallem", „im Groben und Ganzen",
                            „wahr nehmen", „kennen lernen" …
  LT4  Fehlschreib-Kanon    „ansonten" → „ansonsten", „übbrigens" → „übrigens" …

SICHERHEIT (Verträge aus sprachkern.py):
  - Links/URLs/Code/Shortcodes/Link-TEXTE werden maskiert und NIE verändert
  - Whitelist (data/grammar_whitelist.txt) schützt Eigennamen/Fachbegriffe
  - NUR 100 %-sichere Kanon-Ersetzungen; Grauzonen gehen in den Report
  - Frontmatter: description wird mitgeheilt, title NUR gemeldet (Cover-Lock),
    tags/keywords bleiben unangetastet (SEO-Kleinschreibung ist gewollt)
  - Selbsttest (eingefrorene Fälle inkl. Negativ-Fallen) vor JEDEM Schreib-
    vorgang – Abweichung = Exit 2, keine Datei wird angefasst

NUTZUNG:
  python3 scripts/grammar_check.py               # Prüfung + Report
  python3 scripts/grammar_check.py --fix         # eindeutige Fehler korrigieren
  python3 scripts/grammar_check.py --file X.md   # einzelner Artikel
  python3 scripts/grammar_check.py --file X.md --include-drafts
  python3 scripts/grammar_check.py --new-only    # nur Artikel von heute
  python3 scripts/grammar_check.py --json        # maschinenlesbar
  python3 scripts/grammar_check.py --selftest    # nur Sabotage-Schutz
  python3 scripts/grammar_check.py --strict      # Exit 1 bei offenen Funden

AUSGABE: GRAMMATIK-REPORT.md + .grammar_report.json
Exit 0 = sauber/gelaufen · Exit 1 = offene Funde (nur --strict) · Exit 2 = Selbsttest rot
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sprachkern import (  # noqa: E402
    ROOT, case_match, scan_rules, apply_rules, load_articles,
    words, rebuild, write_verified, now_utc, heading_count,
)

WHITELIST_FILE = os.path.join(ROOT, "data", "grammar_whitelist.txt")
REPORT_FILE = os.path.join(ROOT, "GRAMMATIK-REPORT.md")
JSON_FILE = os.path.join(ROOT, ".grammar_report.json")

# Wörter, die nie angefasst werden (Dialekt/Marken/Fachbegriffe)
DEFAULT_WHITELIST = {
    "frugalismus", "frugalismus-tipps", "fritzbox", "check24", "tarifcheck",
    "cloudflare", "schufa", "cashback", "etf", "etfs", "mesh", "repeater",
    "wlan", "dns", "dsl", "mbit", "kbit", "smartphone", "smartphones",
    "girocard", "wallbox", "dispo", "app", "apps", "streaming", "tracking",
}


def load_whitelist():
    wl = set(DEFAULT_WHITELIST)
    if os.path.exists(WHITELIST_FILE):
        for line in open(WHITELIST_FILE, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#"):
                wl.add(line.lower())
    return wl


# ============================================================ LT-Regeln
# Regel = (ID, Regex, Fixer, Label). Fixer None = nur Report.
RULES = []

# ---- LT1 Partikel-Fallen (Zerlegungen, die immer ein Wort sind) -----------
# NUR unzweideutige Fälle. Bewusst NICHT dabei (Falsch-Positiv-Fallen):
# „da für" („Ich bin da für dich"), „da mit", „da zu", „da vor/rans/raus"
# (Verb-Präfixe: „da vorstellen"), „an Stelle" (echtes Nomen).
PARTIKEL = [
    ("an Hand", "anhand"), ("in Folge", "infolge"),
    ("zu mindest", "zumindest"), ("bei spielsweise", "beispielsweise"),
    ("viel leicht", "vielleicht"), ("mit hin", "mithin"),
    ("über dies", "überdies"), ("hin gegen", "hingegen"),
    ("dessen trotz", "trotzdem"), ("da von", "davon"),
    ("da zwischen", "dazwischen"),
    ("wo rüber", "worüber"), ("wo durch", "wodurch"), ("wo bei", "wobei"),
    ("wo für", "wofür"), ("wo gegen", "wogegen"), ("wo mit", "womit"),
    ("wo von", "wovon"), ("wo zu", "wozu"), ("wo raus", "woraus"),
    ("wo ran", "woran"), ("wo rin", "worin"), ("wo hin", "wohin"),
    ("wo her", "woher"),
]
for _i, (split, kanon) in enumerate(PARTIKEL):
    RULES.append((
        "LT1", re.compile(r"\b" + r"\s+".join(split.split()) + r"\b", re.I),
        (lambda m, k=kanon: case_match(m.group(0), k)),
        f"{split} → {kanon}",
    ))

# ---- LT2 Kollokations-Kanon (feststehende Wendungen, Nomen groß) ----------
KOLLOKATIONEN = [
    ("im", "gegensatz", "Gegensatz"), ("im", "zusammenhang", "Zusammenhang"),
    ("im", "allgemeinen", "Allgemeinen"), ("im", "besonderen", "Besonderen"),
    ("im", "endeffekt", "Endeffekt"), ("im", "grunde", "Grunde"),
    ("im", "schnitt", "Schnitt"), ("im", "vergleich", "Vergleich"),
    ("im", "übrigen", "Übrigen"), ("im", "vorfeld", "Vorfeld"),
    ("im", "hinblick", "Hinblick"), ("im", "notfall", "Notfall"),
    ("im", "zweifel", "Zweifel"), ("im", "gegenteil", "Gegenteil"),
    ("im", "klartext", "Klartext"), ("im", "handumdrehen", "Handumdrehen"),
    ("im", "falle", "Falle"), ("im", "ernst", "Ernst"),
    ("im", "prinzip", "Prinzip"), ("im", "wesentlichen", "Wesentlichen"),
    ("zu", "hause", "Hause"), ("nach", "hause", "Hause"),
    ("zu", "guter", "guter"), ("von", "anfang", "Anfang"),
]
for _i, (prep, low, upp) in enumerate(KOLLOKATIONEN):
    if (prep, low, upp) == ("zu", "guter", "guter"):
        # Sonderfall „zu guter Letzt“ – NUR die Kleinschreibung ist der Fehler
        RULES.append((
            "LT2", re.compile(r"\b[Zz]u guter letzt\b"),
            (lambda m: case_match(m.group(0), "zu guter Letzt")),
            "zu guter letzt → zu guter Letzt",
        ))
        continue
    if (prep, low, upp) == ("von", "anfang", "Anfang"):
        RULES.append((
            "LT2", re.compile(r"\b[Vv]on anfang an\b"),
            (lambda m: case_match(m.group(0), "von Anfang an")),
            "von anfang an → von Anfang an",
        ))
        continue
    # Ohne re.I: gematcht wird NUR die fehlerhafte Kleinschreibung des Nomens
    # („im gegensatz“), die korrekte Form („im Gegensatz“) bleibt draußen.
    RULES.append((
        "LT2",
        re.compile(rf"\b[{prep[0].upper()}{prep[0]}]{prep[1:]}\s+{low}\b"),
        (lambda m, p=prep, u=upp: case_match(m.group(0), f"{p} {u}")),
        f"{prep} {low} → {prep} {upp}",
    ))

# ---- LT3 Kontext-Fälle ----------------------------------------------------
# LT3a seid/seit + Zeitangabe, auch mit Zahl davor („seid drei Jahren“).
# NEGATIV (Selbsttest): „ihr seid bereit“ = Verb, „seid dem Kurs gefolgt“ =
# Hilfsverb – beide bleiben, weil „bereit“/„dem“ nicht in der Zeitliste stehen.
RULES.append((
    "LT3", re.compile(
        r"\b(seid)\s+(?:(?:\d{1,4}|zwei|drei|vier|fünf|sechs|sieben|acht|"
        r"neun|zehn|elf|zwölf|einigen|einigen|vielen|wenigen|mehreren|paar)"
        r"\s+)?"
        r"(gestern|vorgestern|damals|kurzem|langem|Anfang|Mitte|Ende|Jahren|"
        r"Jahrzehnten|Jahrhunderten|Monaten|Tagen|Wochen|Stunden|Minuten|"
        r"wann|Neujahr|(?:19|20)\d{2})\b", re.I),
    (lambda m: case_match(m.group(1), "seit") + m.group(0)[len(m.group(1)):]),
    "seid + Zeitangabe → seit",
))

# LT3b wieder/wider Erwarten & besseres Wissen (H5 in hardcases_guard deckt
# nur „wieder Willen“ – diese zwei Fälle sind der offline Rest).
# Groß „Erwarten/Wissen“ ist Pflicht: „ihn wieder erwarten“ = Verb (bleibt!).
RULES.append((
    "LT3", re.compile(r"\b[wW]ieder\s+Erwarten\b"),
    (lambda m: case_match(m.group(0), "wider") + " Erwarten"),
    "wieder Erwarten → wider Erwarten",
))
RULES.append((
    "LT3", re.compile(r"\b[wW]ieder\s+besseres\s+Wissen\b"),
    (lambda m: case_match(m.group(0), "wider") + " besseres Wissen"),
    "wieder besseres Wissen → wider besseres Wissen",
))

# LT3c feste Formen
RULES.append((
    "LT3", re.compile(r"\b([Ii]m )Groben und Ganzen\b"),
    (lambda m: m.group(1) + "Großen und Ganzen"),
    "im Groben und Ganzen → im Großen und Ganzen",
))
RULES.append((
    "LT3", re.compile(r"\bvorallem\b", re.I),
    (lambda m: case_match(m.group(0), "vor") + " allem"),
    "vorallem → vor allem",
))
RULES.append((
    "LT3", re.compile(r"\baufjeden\s?fall\b", re.I),
    (lambda m: case_match(m.group(0), "auf") + " jeden Fall"),
    "aufjedenfall → auf jeden Fall",
))
RULES.append((
    "LT3", re.compile(r"\b[Dd]es\s+öfteren\b"),
    (lambda m: case_match(m.group(0), "des") + " Öfteren"),
    "des öfteren → des Öfteren",
))
RULES.append((
    "LT3", re.compile(
        r"\bum so (mehr|weniger|besser|schlechter|schneller|langsamer|"
        r"einfacher|teurer|günstiger|höher|niedriger|größer|kleiner)\b", re.I),
    (lambda m: "umso " + m.group(1)),
    "um so … → umso …",
))
RULES.append((
    "LT3", re.compile(r"\bvor aus gesetzt\b", re.I),
    (lambda m: case_match(m.group(0), "vorausgesetzt")),
    "vor aus gesetzt → vorausgesetzt",
))

# LT3d Verb-Zusammensetzungen: wahrnehmen, kennenlernen (Duden 2024)
WAHR = {"nehmen": "wahrnehmen", "nimmt": "wahrnimmt", "nahm": "wahrnahm",
        "genommen": "wahrgenommen", "zu nehmen": "wahrzunehmen"}
RULES.append((
    "LT3", re.compile(r"\bwahr (nehmen|nimmt|nahm|genommen|zu nehmen)\b", re.I),
    (lambda m: case_match(m.group(0), WAHR.get(m.group(1).lower(), "wahrnehmen"))),
    "wahr nehmen → wahrnehmen",
))
KENNEN = {"lernen": "kennenlernen", "lernt": "kennenlernt", "lernte": "kennenlernte",
          "gelernt": "kennengelernt", "zu lernen": "kennenzulernen"}
RULES.append((
    "LT3", re.compile(r"\bkennen (lernen|lernt|lernte|gelernt|zu lernen)\b", re.I),
    (lambda m: case_match(m.group(0), KENNEN.get(m.group(1).lower(), "kennenlernen"))),
    "kennen lernen → kennenlernen",
))

# ---- LT4 Fehlschreib-Kanon (case-preserving) ------------------------------
TYPOS = {
    "ansonten": "ansonsten", "wiederrum": "wiederum", "übbrigens": "übrigens",
    "mittlerweil": "mittlerweile", "zusamen": "zusammen",
    "interesant": "interessant", "konktret": "konkret", "außdem": "außerdem",
    "möchlicherweise": "möglicherweise", "trozdem": "trotzdem",
    "vielleich": "vielleicht", "wirtschafftlich": "wirtschaftlich",
    "bezeihungsweise": "beziehungsweise", "vorraus": "voraus",
    "anscheind": "anscheinend", "überhaut": "überhaupt",
    "überhaubt": "überhaupt", "tätsächlich": "tatsächlich",
    "tatsälich": "tatsächlich", "vohin": "wohin",
}
TYPO_RX = re.compile(
    r"\b(" + "|".join(sorted((re.escape(t) for t in TYPOS),
                             key=len, reverse=True)) + r")\b",
    re.I | re.UNICODE)
RULES.append((
    "LT4", TYPO_RX,
    (lambda m: case_match(m.group(0), TYPOS[m.group(0).lower()])),
    "Fehlschreib-Kanon (LT4)",
))


def apply_whitelist_gate(fund, whitelist):
    """Wirft Funde gegen Whitelist-Wörter raus (Eigennamen/Fachbegriffe)."""
    w = fund["found"].lower().strip(".,;:!?\"'“”„")
    return w not in whitelist


# ============================================================ Selbsttest
def run_selftest():
    """Offline-Selbsttest der Regeln (eingefrorene Fälle, 25.09.2026).
    Negativ-Fallen sind PFLICHT (Falsch-Positiv = Sabotage). Exit 2 bei Rot."""
    fehler = []

    def fix(t):
        out, _, _ = apply_rules(t, RULES)
        return out

    # 1) seid + Zeitangabe → seit
    if "seit drei Jahren" not in fix("Du sparst seid drei Jahren."):
        fehler.append("LT3: „seid drei Jahren“ wird nicht geheilt")
    # 2) NEGATIV: Verb „seid“ bleibt
    if fix("Ihr seid bereit.") != "Ihr seid bereit.":
        fehler.append("LT3 FALSCH-POSITIV: „Ihr seid bereit.“ wurde verändert")
    # 3) NEGATIV: „seid dem Kurs gefolgt“ = Hilfsverb, bleibt
    if fix("Ihr seid dem Kurs gefolgt.") != "Ihr seid dem Kurs gefolgt.":
        fehler.append("LT3 FALSCH-POSITIV: „seid dem Kurs gefolgt.“ wurde verändert")
    # 4) Kollokation
    if "im Gegensatz dazu" not in fix("im gegensatz dazu spart du."):
        fehler.append("LT2: „im gegensatz“ wird nicht geheilt")
    # 5) NEGATIV: „da für“ („Ich bin da für dich“) bleibt
    if fix("Ich bin da für dich.") != "Ich bin da für dich.":
        fehler.append("LT1 FALSCH-POSITIV: „da für“ wurde verändert")
    # 6) Partikel
    if "womit" not in fix("Das ist das Werkzeug, wo mit du sparst."):
        fehler.append("LT1: „wo mit“ wird nicht geheilt")
    # 7) Schutzzonen
    geschuetzt = "`vorallem` und [aufjedenfall](https://x.de) bleiben."
    if fix(geschuetzt) != geschuetzt:
        fehler.append("Schutzzonen verletzt (Code/Link-Text angefasst)")
    # 8) Case-Erhalt
    if "Anhand der Daten" not in fix("An Hand der Daten spart jeder."):
        fehler.append("LT1 Case-Erhalt: „An Hand“ → „Anhand“ fehlt")
    # 9) wider Erwarten (kleingeschrieben im Satzfluss)
    if "wider Erwarten" not in fix("Er kam wieder Erwarten zu früh."):
        fehler.append("LT3: „wieder Erwarten“ wird nicht geheilt")
    # 9b) NEGATIV: Verb „wieder erwarten“ bleibt
    if fix("Ich hoffe, ihn wieder erwarten zu können.") != \
            "Ich hoffe, ihn wieder erwarten zu können.":
        fehler.append("LT3 FALSCH-POSITIV: Verb „wieder erwarten“ verändert")
    # 10) Idempotenz
    einmal = fix("Vorallem wo mit wir seid drei Jahren rechnen.")
    if fix(einmal) != einmal:
        fehler.append("Idempotenz verletzt: zweiter Lauf ändert nochmal")
    return fehler


# ============================================================ Lauf
def analyze(a, whitelist):
    """Prüft Body + description; title nur Report."""
    funde = []
    body = a["body"]
    for f in scan_rules(body, RULES):
        if apply_whitelist_gate(f, whitelist):
            funde.append(f)
    # Description separat (Frontmatter, Auto-Fix erlaubt)
    if a.get("description"):
        for f in scan_rules(a["description"], RULES):
            if apply_whitelist_gate(f, whitelist):
                f["zone"] = "description"
                funde.append(f)
    # Title: nur melden, nie fixen (Cover-Marken-Lock)
    if a.get("title"):
        for f in scan_rules(a["title"], RULES):
            if apply_whitelist_gate(f, whitelist):
                f["zone"] = "title"
                f["fix"] = None  # Titel nie schreiben
                funde.append(f)
    return funde


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    do_fix = "--fix" in argv
    strict = "--strict" in argv
    as_json = "--json" in argv
    include_drafts = "--include-drafts" in argv
    new_only = "--new-only" in argv
    only_file = None
    for i, a in enumerate(argv):
        if a == "--file" and i + 1 < len(argv):
            only_file = argv[i + 1]
        elif a.startswith("--file="):
            only_file = a.split("=", 1)[1]

    if "--selftest" in argv:
        stf = run_selftest()
        if stf:
            print("🛑 GRAMMATIK-SELBSTTEST ROT (offline LanguageTool-Nachbau):")
            print("\n".join("  " + f for f in stf))
            return 2
        print("✅ Grammatik-Selbsttest: 11 Fälle grün (offline, ohne API).")
        return 0

    stf = run_selftest()
    if stf:
        print("🛑 SELBSTTEST ROT – Sabotage verhindert, kein Schreiben:")
        print("\n".join("  " + f for f in stf))
        return 2

    whitelist = load_whitelist()
    files = None
    if only_file:
        p = only_file if os.path.isabs(only_file) \
            else os.path.join(ROOT, only_file)
        if not os.path.exists(p):
            p = os.path.join(ROOT, "content", "posts", only_file)
        files = [p]
    arts = load_articles(files, new_only=new_only, include_drafts=include_drafts)

    total = fixed = 0
    rows = []
    for a in arts:
        funde = analyze(a, whitelist)
        if not funde:
            continue
        total += len(funde)
        neu_body, n, _ = apply_rules(a["body"], RULES)
        neu_desc = None
        if a.get("description"):
            d2, n2, _ = apply_rules(a["description"], RULES)
            if n2:
                neu_desc, n = d2, n + n2
        if do_fix and n:
            ok, grund = write_verified(a, rebuild(a, neu_body, neu_desc),
                                       "grammar_check")
            if ok:
                fixed += n
            else:
                rows.append({"slug": a["slug"], "rule": "SCHREIBSPERRE",
                             "found": grund, "fix": None, "ctx": "",
                             "label": "Verifikation fehlgeschlagen"})
        for f in funde:
            rows.append({"slug": a["slug"], **f})

    offen = max(0, total - fixed)
    if as_json:
        print(json.dumps({
            "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "engine": "grammar_check (LanguageTool-Nachbau, offline)",
            "posts": len(arts), "findings": total, "fixed": fixed,
            "open": offen, "items": rows[:200],
        }, ensure_ascii=False, indent=2))
        return 1 if (strict and offen) else 0

    L = ["# 📝 GRAMMATIK-REPORT (grammar_check.py – offline, ohne API)", "",
         f"**Stand:** {now_utc()} UTC",
         f"**Modus:** {'FIX' if do_fix else 'REPORT'} · LanguageTool-Nachbau (LT1–LT4)",
         f"**Artikel:** {len(arts)} · **Funde:** {total} "
         f"(geheilt: {fixed} · offen: {offen})", ""]
    if rows:
        L.append("| Regel | Artikel | Fund | Fix/Vorschlag |")
        L.append("|---|---|---|---|")
        for r in rows[:60]:
            fix_info = f"→ `{r['fix']}`" if r.get("fix") else "*(Report)*"
            L.append(f"| {r['rule']} | `{r['slug']}` | „{r['found']}“ | {fix_info} |")
    else:
        L.append("🎉 Keine Grammatik-Funde – Bestand sauber.")
    L += ["", "---",
          "_Offline-Nachbau der LanguageTool-Prüfung (Auftrag 25.09.2026: ohne API). "
          "Stil/Glättung macht scripts/sprachglatt.py (DeepL-Write-Nachbau). "
          "Harte Fest-Fehler (einzigste, daß, seid/seit-Pleonasmen …) liegen in "
          "scripts/hardcases_guard.py._"]
    with open(REPORT_FILE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    with open(JSON_FILE, "w", encoding="utf-8") as fh:
        json.dump({"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "posts": len(arts), "findings": total, "fixed": fixed,
                   "open": offen, "items": rows[:200]},
                  fh, ensure_ascii=False, indent=2)

    print("\n".join(L[:8]))
    return 1 if (strict and offen) else 0


if __name__ == "__main__":
    sys.exit(main())
