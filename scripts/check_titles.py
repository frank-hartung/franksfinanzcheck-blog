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

# R5 (26.08.2026): Legitime Titel-Endwörter in Kleinschreibung.
# Hintergrund: Kürzungsbugs haben Titel mitten im Wort / mitten im Satz
# kaputtgelassen ("…Tarife – Gastari", "…und was sie", "…Vollkas").
# Deutscher Titel mit großem (Nomen/Eigenwort) oder Zahl/€/%-Ende ist
# per se ok; KLEINGESCHRIEBENE Endwörter müssen auf dieser Liste stehen,
# sonst meldet R5 "vermutlich unvollständiger Titel". Falsch-Positiv =
# Gate blockiert den Artikel bis Freigabe (sicher); die Liste ist
# bewusst großzügig für typische Ratgeber-Endungen.
R5_END_WHITELIST = {
    # Verben (Person/Infinitiv), die Titles ordentlich beenden
    "ist", "sind", "war", "waren", "hat", "haben", "kann", "können",
    "kannst", "muss", "müssen", "musst", "will", "willst", "sollst",
    "darfst", "magst", "möchte", "lohnt", "kostet",
    "kosten", "spart", "sparen", "spare", "senkt", "senken", "schützt",
    "schützen", "zahlt", "zahlen", "funktioniert", "funktionieren",
    "bleibt", "bleiben", "wird", "werden", "wächst", "wachsen", "fällt",
    "fallen", "steigt", "steigen", "sinkt", "sinken", "endet", "enden",
    "passt", "passen", "reicht", "reichen", "fehlt", "fehlen", "zählt",
    "zählen", "bringt", "bringen", "macht", "machen", "gibt", "geben",
    "nimmt", "nehmen", "nutzt", "nutzen", "testest", "testen", "prüfst",
    "prüfen", "wählst", "wählen", "vergleichst", "vergleichen", "buchst",
    "buchen", "findest", "finden", "verstehst", "verstehen", "erreichst",
    "erreichen", "gewinnst", "gewinnen", "kündigst", "kündigen",
    "wechselst", "wechseln", "sicherst", "sichern", "planst", "planen",
    "investierst", "investieren", "anlegst", "anlegen", "versicherst",
    "versichern", "heizt", "heizen", "ladest", "laden", "installierst",
    "installieren", "einrichtest", "einrichten", "richtest", "richten",
    "steuerst", "steuern", "behältst", "behalten", "kontrollierst",
    "kontrollieren", "überprüfst", "überprüfen", "kalkulierst",
    "kalkulieren", "betrachtet", "betrachten", "beobachtet", "beobachten",
    "spürst", "spüren", "sichtest", "sichten", "vermeidest", "vermeiden",
    "erzielst", "erringst", "erringen", "abgeben", "bezahlen", "bemerken",
    "sammeln", "einreichen", "beantragst", "beantragen", "bestellst",
    "bestellen", "versendest", "versenden", "ermitteln", "ermittelt",
    "zeigt", "zeigen", "weiß", "wissen", "siehst", "sehen", "hörst",
    "hören", "liest", "lesen", "schreibst", "schreiben", "suchst",
    "suchen", "startest", "starten", "läufst", "laufen", "klickst",
    "klicken", "tippst", "tippen", "suchst", "suche", "sucht", "sucht",
    # Infinitive (nach „zum/zur" oder als Endung)
    "sparen", "zahlen", "buchen", "wählen", "wechseln", "sichern",
    "senken", "finden", "testen", "prüfen", "vergleichen", "kalkulieren",
    "planen", "investieren", "anlegen", "versichern", "schützen",
    "heizen", "laden", "installieren", "einrichten", "nutzen",
    "verstehen", "erreichen", "gewinnen", "kündigen", "beobachten",
    "bemerken", "vergleichen", "betrachten", "spüren", "sammeln",
    "bezahlen", "sichten", "beantragen", "bestellen", "ermitteln",
    "zeigen", "wissen", "sehen", "hören", "lesen", "schreiben",
    "suchen", "starten", "laufen", "klicken", "tippen", "ausprobieren",
    "nachholen", "nachrüsten", "ausbauen", "nachweisen", "vorführen",
    # Adjektive / Partizipien
    "wichtig", "günstig", "einfach", "leicht", "schnell", "zügig",
    "bequem", "komfortabel", "sicher", "fair", "ehrlich", "transparent",
    "unabhängig", "verständlich", "kostenlos", "neu", "alt", "gut",
    "schlecht", "billig", "billiger", "teurer", "mehr", "weniger",
    "richtig", "falsch", "klar", "voll", "leer", "warm", "kalt",
    "frisch", "sauber", "stabil", "flexibel", "mobil", "digital",
    "smart", "clever", "schlau", "klug", "sinnvoll", "lohnend",
    "rentabel", "wertvoll", "ausreichend", "perfekt", "optimal",
    "ideal", "praktisch", "konkret", "real", "direkt", "automatisch",
    "wirklich", "echt", "extra", "besonders", "gratis", "bar", "cash",
    "umsetzbar", "praxistauglich", "alltagstauglich", "nachhaltig",
    # Substantive in Kleinschreibung (seltener, aber valide)
    "geld", "zinsen", "zins", "tarif", "tarife", "kosten", "preis",
    "preiswerte", "konto", "karte", "karten", "rate", "raten", "bonus",
    "boni", "rabatt", "prämie", "prämien", "guthaben", "depot",
    "sparplan", "etf", "etfs", "fonds", "aktie", "aktien", "anleihe",
    "anleihen", "dividende", "dividenden", "rendite", "versicherung",
    "versicherungen", "police", "vertrag", "verträge", "anbieter",
    "vergleich", "ratgeber", "tipps", "tricks", "ideen", "fehler",
    "fallen", "hacks", "checkliste", "leitfaden", "übersicht",
    "analyse", "strategie", "strategien", "methode", "methoden",
    "gewohnheiten", "regel", "regeln", "gründe", "gründe", "fragen",
    "antworten", "lösungen", "vorteile", "nachteile", "effekt",
    "effekte", "nutzen", "risiko", "risiken", "sicherheit", "sicherung",
    "abdeckung", "deckung", "schutz", "vorsorge", "verzicht",
    "freiheit", "budget", "budgets", "planung", "plan", "kontrolle",
    "buch", "app", "apps", "excel", "papier", "online", "offline",
    "internet", "dsl", "wlan", "router", "glasfaser", "netz", "handy",
    "handys", "smartphone", "mietwagen", "urlaub", "reise", "reisen",
    "flug", "flüge", "ticket", "tickets", "laufzeit", "kündigung",
    "notgroschen", "haushalt", "budgetplanung", "sparen", "sammeln",
}


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

    # R5 (26.08.2026): vermutlicher UNVOLLSTÄNDIGER Titel (Truncation-
    # Wächter). Der Cover-Text wird aus dem Titel gerendert – ein
    # mitten im Wort/Satz abgebrochener Titel macht den Cover-Text
    # unvollständig (Befund: „…Tarife – Gastari“ o. ä.). Detection:
    #   - Endet mit hängendem Konnektor (–, —, -, ,, ;) → sofort FAIL
    #   - Sonst: letztes Wort ohne Satz-Punktierung; groß (Nomen) oder
    #     Zahl/€/% → ok; Kleinschreibung MUSS auf R5_END_WHITELIST
    #     stehen (legitime Endung), sonst FAIL.
    # --fix kann R5 NICHTEINHEITEN (der fehlende Teil ist verloren) –
    # das Gate meldet den Titel zur Freigabe/Korrektur (publish_gate
    # hält neue Artikel zurück, Bestands-Titel werden beim nächsten
    # Lauf sichtbar).
    t_plain = re.sub(r"<[^>]+>", "", t).strip()
    if t_plain:
        last_ch = t_plain[-1]
        if last_ch in "–—-,;":
            issues.append(("R5", "Titel endet mit hängendem Konnektor "
                                 f"(„…{t_plain[-12:]}“) – vermutlich unvollständig"))
        elif not last_ch in ".!?":
            words = t_plain.split()
            last_word = re.sub(r"[.,;:!?\-–—\"'„“»«…]+$", "", words[-1]).strip()
            if not last_word:
                issues.append(("R5", "Titel endet ohne Endwort – vermutlich unvollständig"))
            elif last_word[0].isupper():
                pass  # Großes Endwort (Nomen/Eigenwort) = valide Titel-Endung
            elif re.fullmatch(r"[\d.,\s%€]+$", last_word):
                pass  # Zahl/€/%-Ende („…800 €", „…2026") = valide
            elif last_word not in R5_END_WHITELIST:
                issues.append(("R5", f"Titel endet in kleingeschriebenem „{last_word}“ – "
                                     "vermutlich unvollständig (Truncation-Check)"))
    return issues


def fix_title(title):
    """Deterministische Korrekturen R1–R4.

    R1 (Doppelpunkt-Konvention) wird über pinterest_seo_healer.ensure_colon_title
    geheilt, falls importierbar – sonst bleiben R2–R4.
    """
    t = title.strip()
    # Ellipsis-Reste (Meta-Optimizer-Kürzung) entfernen
    t = re.sub(r"[…\.]{1,}$", "", t).rstrip()
    for pat, repl in COMPOUND_FIXES:
        t = re.sub(pat, repl, t)
    t = TIME_TAIL.sub("", t).strip()
    t = re.sub(r"\s{2,}", " ", t)
    t = re.sub(r"\s+:", ":", t)
    t = re.sub(r":\s{2,}", ": ", t)
    # R1: Doppelpunkt erzwingen wenn Titel lang ohne :
    if len(t) > TITLE_NO_COLON_MAX and ":" not in t:
        try:
            from pinterest_seo_healer import ensure_colon_title, strip_ellipsis
            t = ensure_colon_title(strip_ellipsis(t))
        except Exception:
            words = t.split()
            if len(words) >= 4:
                mid = max(2, len(words) // 2)
                t = f"{' '.join(words[:mid])}: {' '.join(words[mid:])}"
    if len(t) < REST_MIN and title != t:
        # Anhängsel-Entfernung hat den Titel entkernt → Änderung verwerfen
        t = title.strip()
    return t


def collect():
    posts = []
    # Page-Bundles + Legacy-Posts + Pillars
    patterns = [
        "content/posts/*/index.md",
        "content/posts/*.md",
        "content/pillar/*/index.md",
    ]
    seen = set()
    for pattern in patterns:
        for f in glob.glob(os.path.join(BLOG_DIR, pattern)):
            if f.endswith("_index.md") or f in seen:
                continue
            seen.add(f)
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
