#!/usr/bin/env python3
"""
SPRACHGLATT – DeepL-Write-Nachbau („glätten"), komplett offline, ohne API.

Auftrag (Frank, 25.09.2026): „Sämtliche Blogartikel dauerhaft automatisch mit
DeepL Write glätten (KOSTENLOS, OHNE API nachbauen) und auf Premium-Level
einer Profi-Agentur beheben." DeepL Write glättet Texte innerhalb einer
Sprache: Füllwörter raus, Behördendeutsch raus, Bandagen rein – das wird hier
als deterministischer, nachvollziehbarer Regelsatz NACHGEBAUT. Kein Netz,
kein Schlüssel, kein externer Dienst (DSGVO: null Datenabfluss), keine
KI-Umschreibungen mit Sinnrisiko – nur 100 %-sichere Glätt-Fälle.

REGEL-Ebenen (einmalig hier, nicht in lektor_guard/hardcases_guard):
  DW1  Meinungs-Bandage   „ist der Meinung, dass“ → „meint, dass“
  DW2  Können-Hebel       „bist in der Lage, Geld zu sparen“ → „kannst Geld sparen“
  DW3  Möglichkeit-Hebel  „hast die Möglichkeit, zu sparen“ → „kannst sparen“
  DW4  Anschluss-Lasur    „des Weiteren“ → „Außerdem“
  DW5  Abstrakt-Verdichtung „in Betracht ziehen“ → „erwägen“
  DW6  Entscheidungs-Hebel „eine Entscheidung treffen“ → „entscheiden“
  DW7  Nominalstil-Hebel  „eine Überprüfung vornehmen“ → „überprüfen“
  DW8  Folge-Glättung     „, mit der Folge, dass“ → „, sodass“
  DW9  Passiv-Nebel       „Anwendung finden“ → „genutzt werden“

  V1   VORSCHLAGSSCHICHT (Report, nie Auto): im Hinblick auf, hinsichtlich,
       eine Vielzahl von (Kasus-Falle!), wegen dem/trotz dem (Genitiv),
       zur Verfügung stellen, von Bedeutung sein, einen Beitrag leisten,
       in Angriff nehmen, „es ist möglich, zu“, „trotzdem + Subjekt“,
       „Es gilt zu beachten, dass“ …

Bewusst ANDERSWO (keine Doppel-Regeln):
  - Füllphrasen/Intensiv/Pleonasmus/Zahlen = lektor_guard.py (L2/L10/L11)
  - einzigste/daß/seid-Pleonasmen = hardcases_guard.py (H1–H9)
  - Grammatik/Rechtschreibung = grammar_check.py (LT1–LT4, offline)
  - Stil-Messung (Passiv, LIX …) = stil_guard.py (S1–S8)

SICHERHEIT: Schutzzonen + Verifikation vor dem Schreiben (sprachkern.py),
Selbsttest vor JEDEM Schreibvorgang (Exit 2 = Sabotage, kein Schreiben).
Frontmatter: description wird mitgeheilt, title NUR gemeldet (Cover-Lock).

NUTZUNG:
  python3 scripts/sprachglatt.py               # Prüfung + Report
  python3 scripts/sprachglatt.py --fix         # glätten (sichere Fälle)
  python3 scripts/sprachglatt.py --file X.md [--include-drafts]
  python3 scripts/sprachglatt.py --new-only    # nur Artikel von heute
  python3 scripts/sprachglatt.py --json        # maschinenlesbar
  python3 scripts/sprachglatt.py --selftest    # nur Sabotage-Schutz

AUSGABE: SPRACHGLATT-REPORT.md + .sprachglatt_report.json
         + data/sprachglatt_history.jsonl (Verlauf, wird mitcommittet)
Exit 0 = gelaufen · Exit 1 = offene Vorschläge (nur --strict) · Exit 2 = Selbsttest rot
"""
import json
import os
import sys
from datetime import datetime, timezone
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sprachkern import (  # noqa: E402
    ROOT, case_match, scan_rules, apply_rules, load_articles,
    rebuild, write_verified, now_utc,
)

REPORT_FILE = os.path.join(ROOT, "SPRACHGLATT-REPORT.md")
JSON_FILE = os.path.join(ROOT, ".sprachglatt_report.json")
HISTORY = os.path.join(ROOT, "data", "sprachglatt_history.jsonl")

# ============================================================ DW-Regeln
RULES = []
VORSCHLAEGE = []   # (ID, Regex, Label, Vorschlag) – NUR Report

# ---- DW1 Meinungs-Bandage -------------------------------------------------
_MEINUNG = {"bin": "meine", "bist": "meinst", "ist": "meint",
            "sind": "meinen", "seid": "meint", "war": "meinte",
            "waren": "meinten"}
RULES.append((
    "DW1", re.compile(r"\b(bin|bist|ist|sind|seid|war|waren) der Meinung, dass\b"),
    (lambda m: _MEINUNG[m.group(1)] + ", dass"),
    "… der Meinung, dass → … meint/meinen, dass",
))

# ---- DW2 Können-Hebel: „in der Lage sein, X zu Verb“ → „können X Verb“ -----
_KOENNEN = {"bin": "kann", "bist": "kannst", "ist": "kann",
            "sind": "können", "seid": "könnt", "war": "konnte",
            "waren": "konnten"}


def _dw2_fix(m):
    return _KOENNEN[m.group(1)] + " " + m.group(2) + " " + m.group(3)


RULES.append((
    "DW2",
    re.compile(r"\b(bin|bist|ist|sind|seid|war|waren) in der Lage, "
               r"([^,.;:!?]{2,60}?) zu ([a-zäöüß]{2,30})\b"),
    _dw2_fix,
    "in der Lage sein, … zu V → können … V",
))

# ---- DW3 Möglichkeit-Hebel ------------------------------------------------
_KANN = {"habe": "kann", "hast": "kannst", "hat": "kann",
         "haben": "können", "habt": "könnt"}


def _dw3_fix(m):
    return _KANN[m.group(1)] + " " + m.group(2) + " " + m.group(3)


RULES.append((
    "DW3",
    re.compile(r"\b(habe|hast|hat|haben|habt) (?:die )?M[öo]glichkeit, "
               r"([^,.;:!?]{2,60}?) zu ([a-zäöüß]{2,30})\b"),
    _dw3_fix,
    "die Möglichkeit haben, … zu V → können … V",
))

# ---- DW4 Anschluss-Lasur --------------------------------------------------
RULES.append((
    "DW4", re.compile(r"\bdes Weiteren\b"),
    (lambda m: "Außerdem"),
    "des Weiteren → Außerdem",
))

# ---- DW5 Abstrakt-Verdichtung: in Betracht ziehen → erwägen ----------------
# NEGATIV-SCHUTZ: „in Betracht kommen“ (andere Wendung) bleibt unangetastet!
_ERWAEGEN = {"zu ziehen": "zu erwägen", "ziehen": "erwägen",
             "ziehe": "erwäge", "ziehst": "erwägst", "zieht": "erwägt"}
RULES.append((
    "DW5",
    re.compile(r"\bin Betracht (zu ziehen|ziehen|ziehe|ziehst|zieht)\b"),
    (lambda m: _ERWAEGEN[m.group(1)]),
    "in Betracht ziehen → erwägen",
))

# ---- DW6 Entscheidungs-Hebel: (eine|die) Entscheidung treffen → entscheiden
_ENTSCHEID = {"treffen": "entscheiden", "treffe": "entscheide",
              "triffst": "entscheidest", "trifft": "entscheidet",
              "trefft": "entscheidet"}
RULES.append((
    "DW6",
    re.compile(r"\b(?:eine|die) Entscheidung "
               r"(treffen|treffe|triffst|trifft|trefft)\b"),
    (lambda m: _ENTSCHEID[m.group(1)]),
    "eine Entscheidung treffen → entscheiden",
))
RULES.append((
    "DW6",
    re.compile(r"\b(treffen|treffe|triffst|trifft|trefft) "
               r"(?:eine|die) Entscheidung\b"),
    (lambda m: _ENTSCHEID[m.group(1)]),
    "… treffen eine Entscheidung → … entscheiden",
))

# ---- DW7 Nominalstil-Hebel: „eine N vornehmen“ → „V“ (nur Infinitiv-Konstr.)
_VORNEHMEN = {
    "Überprüfung": "überprüfen", "Anpassung": "anpassen",
    "Optimierung": "optimieren", "Reduzierung": "reduzieren",
    "Erhöhung": "erhöhen", "Senkung": "senken", "Änderung": "ändern",
    "Aktualisierung": "aktualisieren", "Installation": "installieren",
    "Verlängerung": "verlängern", "Kürzung": "kürzen",
    "Erneuerung": "erneuern", "Prüfung": "prüfen",
}
RULES.append((
    "DW7",
    re.compile(r"\beine[nmrs]? (" + "|".join(_VORNEHMEN) + r") vornehmen\b"),
    (lambda m: _VORNEHMEN[m.group(1)]),
    "eine N vornehmen → V",
))

# ---- DW8 Folge-Glättung ---------------------------------------------------
RULES.append((
    "DW8", re.compile(r",\s*mit der Folge, dass\b"),
    (lambda m: ", sodass"),
    "mit der Folge, dass → sodass",
))
RULES.append((
    "DW8", re.compile(r"(\S)\s+mit der Folge, dass\b"),
    (lambda m: m.group(1) + ", sodass"),
    "mit der Folge, dass → sodass",
))

# ---- DW9 Passiv-Nebel: Anwendung finden → genutzt werden ------------------
_ANWENDUNG = [
    (r"\bAnwendung finden\b", "genutzt werden"),
    (r"\bAnwendung findet\b", "genutzt wird"),
    (r"\bAnwendung fanden\b", "genutzt wurden"),
    (r"\bfindet Anwendung\b", "wird genutzt"),
    (r"\bfinden Anwendung\b", "werden genutzt"),
]
for _pat, _kanon in _ANWENDUNG:
    RULES.append((
        "DW9", re.compile(_pat),
        (lambda m, k=_kanon: k),
        f"Anwendung finden → { _kanon }",
    ))

# ============================================================ V1 Vorschlagsschicht
def _v(rid, pat, label, vorschlag):
    VORSCHLAEGE.append((rid, re.compile(pat, re.I), label, vorschlag))


_v("V1", r"\bim\s+Hinblick\s+auf\b", "Abstrakt: „im Hinblick auf“",
   "glätten zu „für“ / „bei“ / „zu“ – je nach Bezug")
_v("V1", r"\bhinsichtlich\b", "Abstrakt: „hinsichtlich“",
   "glätten zu „bei“ / „zu“")
_v("V1", r"\beine\s+(?:Vielzahl|große Anzahl|ganze Reihe)\s+(?:von|an)\b",
   "Quantor: „eine Vielzahl von“", "glätten zu „viele“ – ABER Kasus des "
   "Nomens prüfen („von Angeboten“ ≠ „viele Angeboten“)")
_v("V1", r"\b(wegen|trotz|anstatt|statt)\s+(dem|diesem)\b", "Kasus: + Dativ",
   "Amtssprache: Genitiv prüfen („wegen des …“)")
_v("V1", r"\bzur\s+Verfügung\s+stellen(?:\s+(?:dir|euch|Ihnen))?\b",
   "Bandage: „zur Verfügung stellen“", "glätten zu „bereitstellen“")
_v("V1", r"\bvon\s+(?:großer\s+)?Bedeutung\s+sein\b", "Bandage: „von Bedeutung sein“",
   "glätten zu „wichtig sein“")
_v("V1", r"\beinen\s+Beitrag\s+leisten\b", "Bandage: „einen Beitrag leisten“",
   "glätten zu „beitragen“")
_v("V1", r"\bin\s+Angriff\s+nehmen\b", "Bandage: „in Angriff nehmen“",
   "glätten zu „beginnen“ / „loslegen“")
_v("V1", r"\bEs\s+(?:ist|wäre)\s+möglich,\s+[^,.;:!?]{2,60}?\s+zu\s+[a-zäöüß]{2,30}\b",
   "Schleife: „Es ist möglich, … zu V“", "glätten zu „… können … V“")
_v("V1", r"\btrotzdem\s+(?:das|die|der|es|er|sie|ich|du|wir|ihr|Sie)\b",
   "Falscher Anschluss: „trotzdem + Subjekt“",
   "hochdeutsch: „obwohl + Subjekt“")
_v("V1", r"\bEs\s+gilt\s+zu\s+beachten,\s+dass\b", "Floskel: „Es gilt zu beachten, dass“",
   "glätten zu „Wichtig:“ (wie lektor_guard L2)")
_v("V1", r"\bEs\s+gibt\s+(?:viele|zahlreiche|eine Menge)\b", "KI-Floskel: „Es gibt viele …“",
   "konkretisieren (profi_text_check-Blacklist)")


def scan_vorschlaege(text: str):
    out = []
    for vid, rx, label, vorschlag in VORSCHLAEGE:
        for m in rx.finditer(text):
            out.append({"rule": vid, "found": m.group(0), "fix": None,
                        "label": label, "vorschlag": vorschlag,
                        "ctx": text[max(0, m.start() - 36): m.end() + 36]
                               .replace("\n", " ").strip()})
    return out


# ============================================================ Selbsttest
def run_selftest():
    """Eingefrorene Fälle inkl. Negativ-Fallen (25.09.2026). Exit 2 bei Rot."""
    fehler = []

    def fix(t):
        out, _, _ = apply_rules(t, RULES)
        return out

    # 1) DW2 Können-Hebel
    if fix("Du bist in der Lage, Geld zu sparen.") != "Du kannst Geld sparen.":
        fehler.append("DW2: „bist in der Lage, Geld zu sparen“ → „kannst Geld sparen“")
    # 2) DW1 Meinung
    if fix("Er ist der Meinung, dass es klappt.") != "Er meint, dass es klappt.":
        fehler.append("DW1: „ist der Meinung, dass“ → „meint, dass“")
    # 3) NEGATIV: „der Meinung des Chefs“ bleibt
    if fix("Er ist der Meinung des Chefs.") != "Er ist der Meinung des Chefs.":
        fehler.append("DW1 FALSCH-POSITIV: „der Meinung des Chefs“ verändert")
    # 4) DW6 Entscheidung
    if fix("Wir müssen eine Entscheidung treffen.") != "Wir müssen entscheiden.":
        fehler.append("DW6: „eine Entscheidung treffen“ → „entscheiden“")
    # 5) NEGATIV: „in Betracht kommen“ bleibt
    if fix("Das kommt nicht in Betracht.") != "Das kommt nicht in Betracht.":
        fehler.append("DW5 FALSCH-POSITIV: „in Betracht kommen“ verändert")
    # 6) DW5 erwägen
    if fix("Das solltest du in Betracht ziehen.") != "Das solltest du erwägen.":
        fehler.append("DW5: „in Betracht ziehen“ → „erwägen“")
    # 7) DW8 sodass
    out7 = fix("Die Kosten steigen, mit der Folge, dass du mehr zahlst.")
    if out7 != "Die Kosten steigen, sodass du mehr zahlst.":
        fehler.append(f"DW8: „mit der Folge, dass“ → „sodass“ (ergab: {out7!r})")
    # 8) DW3 Möglichkeit
    if fix("Du hast die Möglichkeit, täglich zu sparen.") != "Du kannst täglich sparen.":
        fehler.append("DW3: „hast die Möglichkeit, … zu V“ → „kannst … V“")
    # 9) NEGATIV: „die Möglichkeit zum Sparen“ (kein zu-Verb) bleibt
    if fix("Du hast die Möglichkeit zum Sparen.") != "Du hast die Möglichkeit zum Sparen.":
        fehler.append("DW3 FALSCH-POSITIV: „Möglichkeit zum Sparen“ verändert")
    # 10) Schutzzonen
    s = "In `der Lage, zu` und [in der Lage, zu](https://x.de) bleibt alles."
    if fix(s) != s:
        fehler.append("Schutzzonen verletzt")
    # 11) Idempotenz
    einmal = fix("Du bist in der Lage, eine Entscheidung zu treffen, des Weiteren.")
    if fix(einmal) != einmal:
        fehler.append(f"Idempotenz verletzt: {fix(einmal)!r}")
    # 12) DW9
    if "wird genutzt" not in fix("Das Verfahren findet Anwendung."):
        fehler.append("DW9: „findet Anwendung“ nicht geglättet")
    if "genutzt wird" not in fix("Das Verfahren, das hier Anwendung findet, bleibt."):
        fehler.append("DW9: „Anwendung findet“ nicht geglättet")
    return fehler


# ============================================================ Lauf
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
            print("🛑 SPRACHGLATT-SELBSTTEST ROT (DeepL-Write-Nachbau):")
            print("\n".join("  " + f for f in stf))
            return 2
        print("✅ Sprachglatt-Selbsttest: 12 Fälle grün (offline, ohne API).")
        return 0

    stf = run_selftest()
    if stf:
        print("🛑 SELBSTTEST ROT – Sabotage verhindert, kein Schreiben:")
        print("\n".join("  " + f for f in stf))
        return 2

    files = None
    if only_file:
        p = only_file if os.path.isabs(only_file) else os.path.join(ROOT, only_file)
        if not os.path.exists(p):
            p = os.path.join(ROOT, "content", "posts", only_file)
        files = [p]
    arts = load_articles(files, new_only=new_only, include_drafts=include_drafts)

    total = fixed = vorschlag_n = 0
    rows = []
    for a in arts:
        funde = scan_rules(a["body"], RULES)
        vorschlaege = scan_vorschlaege(a["body"])
        if a.get("description"):
            funde += scan_rules(a["description"], RULES)
            vorschlaege += scan_vorschlaege(a["description"])
        if a.get("title"):
            t_v = scan_vorschlaege(a["title"])
            t_f = scan_rules(a["title"], RULES)
            for f in t_f:
                f["fix"] = None  # Titel nie schreiben (Cover-Lock)
                f["zone"] = "title"
            funde += t_f
            vorschlaege += t_v
        if not funde and not vorschlaege:
            continue
        total += len(funde)
        vorschlag_n += len(vorschlaege)
        neu_body, n, _ = apply_rules(a["body"], RULES)
        neu_desc = None
        if a.get("description"):
            d2, n2, _ = apply_rules(a["description"], RULES)
            if n2:
                neu_desc, n = d2, n + n2
        if do_fix and n:
            ok, grund = write_verified(a, rebuild(a, neu_body, neu_desc), "sprachglatt")
            if ok:
                fixed += n
            else:
                rows.append({"slug": a["slug"], "rule": "SCHREIBSPERRE",
                             "found": grund, "fix": None, "vorschlag": "",
                             "label": "Verifikation fehlgeschlagen"})
        for f in funde:
            rows.append({"slug": a["slug"], "vorschlag": "", **f})
        for v in vorschlaege:
            rows.append({"slug": a["slug"], **v})

    offen = max(0, total - fixed)
    hist = {"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "mode": "FIX" if do_fix else "REPORT", "posts": len(arts),
            "DW": total, "fixed": fixed, "V1": vorschlag_n}
    os.makedirs(os.path.dirname(HISTORY), exist_ok=True)
    with open(HISTORY, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(hist, ensure_ascii=False) + "\n")

    if as_json:
        print(json.dumps({
            "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "engine": "sprachglatt (DeepL-Write-Nachbau, offline)",
            **hist, "open": offen, "items": rows[:200],
        }, ensure_ascii=False, indent=2))
        return 1 if (strict and offen) else 0

    L = ["# 🧴 SPRACHGLATT-REPORT (sprachglatt.py – DeepL-Write-Nachbau, offline)", "",
         f"**Stand:** {now_utc()} UTC",
         f"**Modus:** {'FIX' if do_fix else 'REPORT'} · DW1–DW9 (Auto) + V1 (Vorschlag)",
         f"**Artikel:** {len(arts)} · **Glätt-Funde:** {total} "
         f"(geheilt: {fixed} · offen: {offen}) · **Vorschläge:** {vorschlag_n}", ""]
    if rows:
        L.append("| Regel | Artikel | Fund | Fix/Vorschlag |")
        L.append("|---|---|---|---|")
        for r in rows[:60]:
            info = f"→ `{r['fix']}`" if r.get("fix") else \
                (f"*Vorschlag: {r.get('vorschlag', '')}*" if r.get("vorschlag") else "*(Report)*")
            L.append(f"| {r['rule']} | `{r['slug']}` | „{r['found']}“ | {info} |")
    else:
        L.append("🎉 Nichts zu glätten – Bestand auf Profi-Level.")
    L += ["", "---",
          "_Offline-Nachbau von DeepL Write (Auftrag 25.09.2026: kostenlos, ohne API). "
          "Grammatik: grammar_check.py (LT1–LT4) · Fest-Fehler: hardcases_guard.py · "
          "Füllphrasen: lektor_guard.py · Stil-Messung: stil_guard.py._"]
    with open(REPORT_FILE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    with open(JSON_FILE, "w", encoding="utf-8") as fh:
        json.dump({"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   **hist, "open": offen, "items": rows[:200]},
                  fh, ensure_ascii=False, indent=2)

    print("\n".join(L[:8]))
    return 1 if (strict and offen) else 0


if __name__ == "__main__":
    sys.exit(main())
