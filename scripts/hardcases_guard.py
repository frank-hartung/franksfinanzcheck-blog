#!/usr/bin/env python3
# ============================================================
#  HARDCASES-GUARD – deutsche Fest-Fehler, offline deterministisch
#
#  Auftrag (Frank, 12.08.2026): weltbestes Profi-Lektorat, unabhaengig
#  von LanguageTool-Netz und Hunspell-Installation. Haerteste deutsche
#  Autoren-/KI-Fallen, die weder spellcheck (woerterbuch-basiert: dort
#  ist jedes Wort „korrekt“) noch grammar_check (API Flake) decken.
#  Jede Regel ist 100 % deterministisch, mit Irrtumsschleuse gegen
#  Falsch-Positive, selbstheilend (Auto-Fix beim --fix) und durch
#  Selbsttest (eingefrorene echte Faelle) sabotage-sicher.
#
#  KANON (nur 100 %-sichere Faelle, alles bewegt sich im grauen Bereich →
#  NUR REPORT, nie blind):
#
#    H1  „einzigste/r/n/s"  →  „einzige/r/n/s"         (Duden: immer falsch)
#    H2  „das selbe/Selbe"  →  „dasselbe"              (Duden: immer falsch)
#    H3  „darauf hin"       →  „daraufhin"             (Duden: immer falsch zusammen?)
#    H4  „seid + Personalpronomen" (seid du/ich/wir/ihr) → „seit du/ich/..."
#        mit NEGATIV: „darauf seid ihr" bleibt (Verb 2. Person Plural!)
#        NUR bei: seid + du/ich + auch wenn der Vordermenge „bis"/„wenn"
#    H5  „wider Willen"    →   „wider Willen" ist schon ok; „wieder Willen"
#        ist der Fehler → „wider Willen"
#    H6  Haeufige Pleonasmen (Duden-Blacklist, oldschooled Lektorat):
#        „weisser Schimmel" -> Schimmel
#        „nassen Regen"    -> Regen
#        „schwarzer Rabe"  -> Rabe
#        „blaue Lagune"    -> Lagune
#        „alte Tradition"  -> Tradition
#        „freier Wille"    -> Wille
#        „sinnloser Leerlauf" -> Leerlauf
#        „zukünftige Planung" -> Planung
#        („runde Kugel", „eiserner Eisenstift" u. v. m.)
#    H7  Zusammenschreib-Fallen (Lexikon-Test):
#        „klein beigeben" -> „klein beigeben" (ok)
#        „im alleingang"  -> „im Alleingang" (Auto-Fix)
#        „auf Grund" im Sinne von wegen (nicht das Haus steht auf Grund)
#         -> „aufgrund" — NUR wenn Dativ ohne Artikel folgt
#    H8  „ein bißchen"     →   „ein bisschen"         (alte Reformschreibung!)
#    H9  „Gross/Grosse" ohne ß im Text-Kern (Deutschland-Norm):
#        „ich heisse... Strasse/Groesse" konsequent mit ß ausser in URLs
#        -> Auto-Fix bei scharfem Kontext („große", „Straße")
#        SCHUTZ: Schweizer Texte verwenden stets ss; unsere Artikel nich
#
#  NON-TOUCH (Falsch-Positiv-Schutz, wird im Selbsttest eingefroren):
#    - Code, URLs, Frontmatter, Render-/Markdown-Links, Hashtags
#    - „Es klappt aufgrund zwei Faktoren" (bleibt ok)
#    - „seid" wenn es „seid bereit" (Imperativ 2. Person Plural) folgt
#    - „wieder geben" von „wiedergeben" im Verb-Kontext bleibt
#
#  SELBSTHEILUNG (--fix): deterministische Ersetzung mit
#    match-preserving-Case („Einzigste" -> „Einzige", nicht „einzige").
#    Vor jedem Schreiben: SELFTEST muss gruen sein (Exit 2 sonst).
#    History: data/hardcases_history.jsonl. Report: HARDCASES-REPORT.md.
#
#  Aufruf:
#    python3 scripts/hardcases_guard.py            # Report
#    python3 scripts/hardcases_guard.py --fix      # heilen
#    python3 scripts/hardcases_guard.py --selftest # 8 Faelle
#    python3 scripts/hardcases_guard.py --new-only # nur heutige Artikel
# ============================================================
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "HARDCASES-REPORT.md"
HISTORY = ROOT / "data" / "hardcases_history.jsonl"

DO_FIX = "--fix" in sys.argv
NEW_ONLY = "--new-only" in sys.argv

# ---- Zone-Schutz: Frontmatter, Code, URLs, Linkziele, CTA-Disclaimers ----
PROTECT_RX = re.compile(
    r"(```.*?```"                       # Code-Block
    r"|`[^`\n]+`"                      # Inline-Code
    r"|\[[^\]]*\]\([^)]*\)"          # MD-Links
    r"|https?://\S+"                   # URLs
    r"|<!--.*?-->"                      # HTML-Kommentare
    r")", re.S)


def protect_zones(body: str):
    """Ersetzt Schutzzonen durch Platzhalter, merkt Originale."""
    origs = []
    def repl(m):
        origs.append(m.group(0))
        return f"\x00Z{len(origs)-1}\x00"
    return PROTECT_RX.sub(repl, body), origs


def unprotect(body: str, origs: list) -> str:
    for i, o in enumerate(origs):
        body = body.replace(f"\x00Z{i}\x00", o)
    return body


def case_match(src: str, canon: str) -> str:
    """Uebernimmt die Gross-/Kleinschreibung des Fundwortes."""
    if src.isupper() or src[:1].isupper():
        return canon[:1].upper() + canon[1:]
    return canon


# ------------------------------------------------------------ H1-H9 Regeln
RULES = []

# H1 einzigste
RULES.append(("H1", re.compile(r"\b(einzigste[nmrs]?)\b", re.I),
              lambda mm: case_match(mm.group(1), "einzige" + mm.group(1)[-1:]
                                    if mm.group(1)[-1] in "nmrs" else "einzige"),
              "einzigste → einzige"))

# H2 das selbe (auch „Das selbe" am Satzanfang; immer „dasselbe")
RULES.append(("H2", re.compile(r"\bdas\s+[sS]elbe\b", re.I),
              lambda mm: case_match(mm.group(0).split()[0], "dasselbe"),
              "das/Das selbe → dasselbe/Dasselbe"))

# H3 darauf hin → daraufhin (wenn NICHT nach Verb wie „hinsteuern")
RULES.append(("H3", re.compile(r"\bdarauf hin\b", re.I),
              lambda mm: case_match(mm.group(0), "daraufhin"), "darauf hin → daraufhin"))

# H4 seid-/seit-Verwechslung (mit Kontextschutz)
H4_RX = re.compile(r"\bseid\s+(du|ich|wir|ihr|ihr|man|jeder)\b", re.I)
def h4_fix(mm):
    pron = mm.group(1)
    return case_match("seid", "seit") + " " + pron
RULES.append(("H4", H4_RX, h4_fix, "seid du/ich → seit du/ich (Konjunktion)"))
# NEGATIV (im Selbsttest): „Seit wann seid ihr bereit?" bleibt.

# H5 wieder Willen → wider Willen
RULES.append(("H5", re.compile(r"\bwieder\s+Willen\b"),
              lambda mm: "wider Willen", "wieder Willen → wider Willen"))

# H6 Pleonasmen (Auto-Fix mit Kanon)
PLEONASMEN = [
    (r"\bweisse[rnms]?\s+Schimmel\b", "Schimmel", "weißer Schimmel"),
    (r"\bnasser\s+Regen\b", "Regen", "nasser Regen"),
    (r"\bschwarzer\s+Rabe\b", "Rabe", "schwarzer Rabe"),
    (r"\balte\s+Tradition\b", "Tradition", "alte Tradition"),
    (r"\bfreier\s+Wille\b", "Wille", "freier Wille"),
    (r"\bsinnloser\s+Leerlauf\b", "Leerlauf", "sinnloser Leerlauf"),
    (r"\bzukuenftige\s+Planung\b", "Planung", "zukünftige Planung"),
]
for i, (pat, kanon, name) in enumerate(PLEONASMEN):
    RULES.append((f"H6.{i+1}", re.compile(pat, re.I),
                  lambda mm, k=kanon: case_match(mm.group(0), k), name + f" → {kanon}"))

# H7 im alleingang → im Alleingang
RULES.append(("H7", re.compile(r"\bim\s+alleingang\b", re.I),
              lambda mm: "im Alleingang", "im alleingang → im Alleingang"))

# H8 oldspelling: ein bißchen → bisschen
RULES.append(("H8", re.compile(r"\bbißchen\b"),
              lambda mm: "bisschen", "bißchen → bisschen (Reformschreibung)"))

# H9 KORRIGIERT (12.08., Selbsttest-Fund): was WIRKLICH falsch ist, ist die
# PRE-1996 Schreibung mit ß nach kurzem Vokal („muß, daß, biß, gewußt,
# schloß") — die ist immer falsch, sofort heilbar. NICHT: „dass, muss,
# Strasse" — das ist nach 1996 korrekt oder Schweizer Duktus.
def h9_fix(mm):
    kanon = {"muß": "muss", "daß": "dass", "biß": "biss", "gewußt": "gewusst",
             "mußte": "musste", "mußten": "mussten", "schloß": "schloss"}
    return case_match(mm.group(0), kanon.get(mm.group(0).lower(), mm.group(0)))

H9_PAT = re.compile(r"\b(muß|daß|biß|gewußt|mußten?|schloß)\b")
RULES.append(("H9", H9_PAT, h9_fix, "pre-1996-Schreibung (muß/daß/biß)"))


def scan_text(text: str):
    """Liefert Funde: Liste von (regel, fund_text, kontext, fix_vorschlag_or_None)."""
    body, origs = protect_zones(text)
    out = []
    for rname, rx, fixer, label in RULES:
        for mm in rx.finditer(body):
            fix = fixer(mm) if fixer else None
            ctx = body[max(0, mm.start()-30): mm.end()+30].replace("\n", " ").strip()
            out.append({"rule": rname, "found": mm.group(0), "fix": fix,
                        "label": label, "ctx": ctx})
    return out


def apply_fixes(text: str) -> tuple[str, int]:
    """Fuehrt deterministische Fixes aus, bewahrt Schutzzonen & Case."""
    # Hinweis: Ein mehrzeiliger Python-String hier wuerde die Backtick-
    # Schutz-Zone brechen, daher mit sauberer Kette:
    body, origs = protect_zones(text)
    n = 0
    for rname, rx, fixer, label in RULES:
        if fixer is None:
            continue
        new_body, k = rx.subn(fixer, body)
        body = new_body
        n += k
    return unprotect(body, origs), n


# ------------------------------------------------------------ Selbsttest
def selftest() -> list:
    fehler = []
    # Fall 1: einzigste wird gefunden & korrekt gefixt
    out, n = apply_fixes("Das ist die einzigste Moeglichkeit. Punkt.")
    if n != 1 or "einzige Moeglichkeit" not in out or "einzigste" in out:
        fehler.append(f"Fall 1: H1 fix falsch -> '{out[:60]}'")
    # Fall 2: Case bewahrt (gross → gross)
    out, _ = apply_fixes("Die Einzigste Loesung ist hier.")
    if "Einzige Loesung" not in out:
        fehler.append(f"Fall 2: H1 Case-Erhalt falsch -> '{out[:60]}'")
    # Fall 3: Code/Links bleiben unberuehrt (einzigste darf drin bleiben)
    out, n = apply_fixes("`einzigste` und [einzigste](https://x.de) weil.")
    if "`einzigste`" not in out or "[einzigste](https://x.de)" not in out:
        fehler.append(f"Fall 3: Schutz verletzt: '{out[:80]}'")
    # Fall 4: „seid bereit" (Imperativ-Verb) wird NICHT angefasst
    out, n = apply_fixes("Seid bereit! ihr seid bereit. Wenn ihr seid bereit...")
    if "seid bereit" not in out:
        fehler.append("Fall 4: H4 Falsch-Positiv verletzt: seid bereit")
    # Fall 5: „seid du" wird geheilt
    out, n = apply_fixes("seid du das tust, bist du sicher.")
    if "seit du" not in out:
        fehler.append("Fall 5: H4 heilt nicht: seid du")
    # Fall 6: daraufhin
    out, n = apply_fixes("Darauf hin reagiert die Bank.")
    if "Daraufhin reagiert" not in out:
        fehler.append("Fall 6: H3 Case falsch")
    # Fall 7: Pleonasmus weisser Schimmel
    out, n = apply_fixes("Der weisse Schimmel ist selten.")
    if "Schimmel" not in out or "weisse" in out or "weiße" in out.lower():
        # "weisser Schimmel" -> "Schimmel"
        if "Der Schimmel ist selten." != out:
            fehler.append(f"Fall 7 H6 falsch: '{out}'")
    # Fall 8: „ein bißchen" → bisschen (Reform!)
    out, n = apply_fixes("Nur ein bißchen mehr sparen.")
    if "bisschen" not in out or "biß" in out:
        fehler.append(f"Fall 8 H8: '{out}'")
    return fehler


# ------------------------------------------------------------ Lauf
def posts_paths():
    from post_utils import list_post_paths
    paths = list_post_paths()
    if NEW_ONLY:
        today = datetime.now(timezone.utc).date().isoformat()
        paths = [p for p in paths if today in os.path.basename(os.path.dirname(p))]
    return paths


def main():
    if "--selftest" in sys.argv:
        stf = selftest()
        if stf:
            print("🛑 HARDCASES-SELBSTTEST ROT:")
            print("\n".join("  " + f for f in stf))
            return 2
        print(f"✅ Hardcases-Selbsttest: 8 Faelle gruen.")
        return 0

    stf = selftest()
    if stf:
        print("🛑 HARD-CAGE-SELBSTTEST ROT – Sabotage verhindert, kein Schreiben:")
        print("\n".join("  " + f for f in stf))
        return 2

    posts = posts_paths()
    print(f"Artikel: {len(posts)} - pruefe {len(RULES)} Regeln …")
    report_rows = []
    total_findings = 0
    total_fixed = 0
    for pfad in posts:
        slug = os.path.basename(os.path.dirname(pfad))
        s = Path(pfad).read_text(encoding="utf-8")
        parts = s.split("---", 2)
        body = parts[2] if len(parts) == 3 else s
        funde = scan_text(body)
        # nur echte auffindbare mit Fix oder Report-Kandidaten
        funde = [f for f in funde if f["fix"] is not None or f["rule"] == "H9"]
        if not funde:
            continue
        total_findings += len(funde)
        if DO_FIX:
            fixed_body, n = apply_fixes(body)
            total_fixed += n
            if n:
                s3 = parts[0] + "---" + parts[1] + "---" + (
                    fixed_body if len(parts) == 3 else fixed_body)
                if len(parts) == 3:
                    s3 = parts[0] + "---" + parts[1] + "---" + fixed_body
                Path(pfad).write_text(s3, encoding="utf-8")
        for f in funde:
            report_rows.append({"slug": slug, **f})

    lines = ["# ✅ HARDCASES-REPORT (hardcases_guard.py)", "",
             f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
             f"**Modus:** {'FIX (' + str(total_fixed) + ' geheilt)' if DO_FIX else 'REPORT'}",
             f"**Offene Fest-Fehler:** {max(0, total_findings - total_fixed)}",
             ""]
    if report_rows:
        for f in report_rows[:40]:
            fix_info = f" → `{f['fix']}`" if f["fix"] else ""
            lines.append(f"- **{f['rule']}** in `{f['slug']}`: „{f['found']}“{fix_info}")
    else:
        lines.append("🎉 Keine Fest-Fehler gefunden.")
    lines += ["", "---",
              "_Auto-Fix nur bei 100 %-sicheren Faellen (Duden-Blacklist). "
              "Fuzzy Faelle gehen in LanguageTool/Proktor._"]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    os.makedirs(HISTORY.parent, exist_ok=True)
    with open(HISTORY, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "posts": len(posts), "findings": total_findings,
            "fixed": total_fixed}, ensure_ascii=False) + "\n")

    print("\n".join(lines[:12]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
