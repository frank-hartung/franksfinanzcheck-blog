#!/usr/bin/env python3
"""Titel-Qualitäts-Gate (vollautomatisch) für FranksFinanzcheck.

Verhindert, dass Artikel-Überschriften (und damit auch die Cover-Texte,
die aus dem Titel gerendert werden) durch Meta-Optimierung oder
KI-Titelgenerierung verschlimmbessert werden.

Regeln (deterministisch):
  R1  Titel > 45 Zeichen OHNE Doppelpunkt → FAIL
      (Blog-Konvention "Hauptkeyword: Untertitel"; smart_wrap bricht
      Cover-Texte semantisch nach dem Doppelpunkt – ohne ihn zerfällt
      der Cover-Umbruch, z. B. "Weiterfördern / oder kündigen dieses Jahr")
  R2  Bekannte Komposita ohne Bindestrich (Eigennamen+Substantiv) → FAIL
      (z. B. "Riester Rente" statt "Riester-Rente"); --fix korrigiert
  R3  Holprige Zeit-Anhängsel am Titelende → FAIL
      ("dieses Jahr", "dieses Monat", "im Jahr 20XX"); --fix entfernt
      sie, wenn der Rest-Titel noch aussagekräftig ist (>= 20 Zeichen)
  R4  Doppelte Leerzeichen, " :", ": " (ohne Sinn) → FAIL; --fix korrigiert

Nutzung:
  python3 scripts/check_titles.py            # nur prüfen (Exit 0/1)
  python3 scripts/check_titles.py --fix      # R2–R4 deterministisch korrigieren
  python3 scripts/check_titles.py --json     # JSON-Output

Exit: 0 = alle Titel ok · 1 = mind. 1 Verstoß (Workflow kann alerten).
"""
import os
import re
import sys
import json
import glob

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# R2: Eindeutige Komposita (Eigenname/Abkürzung + Substantiv) – Bindestrich-Pflicht
COMPOUND_FIXES = [
    (r"\bRiester Rente\b", "Riester-Rente"),
    (r"\bRiester Vertrag\b", "Riester-Vertrag"),
    (r"\bRiester Förderung\b", "Riester-Förderung"),
    (r"\bKfz Versicherung\b", "Kfz-Versicherung"),
    (r"\bKfz Versicherungen\b", "Kfz-Versicherungen"),
    (r"\bDSL Tarif\b", "DSL-Tarif"),
    (r"\bDSL Tarife\b", "DSL-Tarife"),
    (r"\bETF Sparplan\b", "ETF-Sparplan"),
    (r"\bETF Sparpläne\b", "ETF-Sparpläne"),
]

# R3: Holprige Zeit-Anhängsel am Titelende
TIME_TAIL = re.compile(r"\b(dieses Jahr|dieses Monat|im Jahr 20\d\d)\s*\.?$")

TITLE_NO_COLON_MAX = 45  # R1: länger ohne Doppelpunkt → Cover-Umbruch kaputt
REST_MIN = 20            # R3: Rest nach Anhängsel-Entfernung muss aussagekräftig sein


def check_title(title):
    """Gibt Liste von (rule, message) zurück."""
    issues = []
    t = title.strip()
    if not t:
        return [("R0", "Titel ist leer")]
    if len(t) > TITLE_NO_COLON_MAX and ":" not in t:
        issues.append(("R1", f"Titel {len(t)} Zeichen ohne Doppelpunkt "
                             f"(Konvention 'Hauptkeyword: Untertitel', "
                             f"Cover-Umbruch bricht sonst semantisch kaputt)"))
    for pat, repl in COMPOUND_FIXES:
        if re.search(pat, t):
            issues.append(("R2", f"Kompositum ohne Bindestrich: {pat[1:-1]!r} "
                                 f"→ {repl!r}"))
    m = TIME_TAIL.search(t)
    if m:
        issues.append(("R3", f"holpriges Zeit-Anhängsel am Ende: {m.group(0)!r}"))
    if "  " in t:
        issues.append(("R4", "doppelte Leerzeichen"))
    if " :" in t or re.search(r":\s{2,}", t):
        issues.append(("R4", "Leerzeichen vor/mehrfach nach Doppelpunkt"))
    return issues


def fix_title(title):
    """Deterministische Korrekturen R2–R4 (kein R1-Fix – semantisch)."""
    t = title.strip()
    for pat, repl in COMPOUND_FIXES:
        t = re.sub(pat, repl, t)
    t = TIME_TAIL.sub("", t).strip()
    t = re.sub(r"\s{2,}", " ", t)
    t = re.sub(r"\s+:", ":", t)
    t = re.sub(r":\s{2,}", ": ", t)
    if len(t) < REST_MIN and title != t:
        # Anhängsel-Entfernung hat den Titel entkernt → Änderung verwerfen
        t = title.strip()
    return t


def collect():
    posts = []
    for pattern in ["content/posts/*/index.md", "content/pillar/*/index.md"]:
        for f in glob.glob(os.path.join(BLOG_DIR, pattern)):
            content = open(f, encoding="utf-8").read()
            m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.M)
            if m:
                posts.append({"file": f, "title": m.group(1).strip()})
    return posts


def main():
    fix = "--fix" in sys.argv
    as_json = "--json" in sys.argv
    posts = collect()
    all_issues = []
    fixed = 0
    for p in posts:
        issues = check_title(p["title"])
        if issues and fix:
            new_title = fix_title(p["title"])
            if new_title != p["title"]:
                content = open(p["file"], encoding="utf-8").read()
                old_line = re.search(r'^title:.*$', content, re.M)
                content = (content[:old_line.start()]
                           + f'title: "{new_title}"'
                           + content[old_line.end():])
                open(p["file"], "w", encoding="utf-8").write(content)
                fixed += 1
                p["title"] = new_title
                issues = [i for i in issues if i[0] != "R2"
                          and i[0] != "R3" and i[0] != "R4"]
                issues = check_title(new_title)
        for rule, msg in issues:
            all_issues.append({"file": p["file"], "title": p["title"][:60],
                               "rule": rule, "msg": msg})

    print(f"Titel-Check: {len(posts)} Titel | Verstöße: {len(all_issues)}"
          + (f" | automatisch gefixt: {fixed}" if fix else ""))
    for i in all_issues:
        print(f"  ❌ [{i['rule']}] {os.path.basename(os.path.dirname(i['file']))}: "
              f"{i['msg']}  ({i['title']})")
    if as_json:
        print(json.dumps({"total": len(posts), "issues": len(all_issues),
                          "fixed": fixed, "items": all_issues},
                         ensure_ascii=False))
    return 1 if all_issues else 0


if __name__ == "__main__":
    sys.exit(main())
