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
  LT5  Kongruenz Genus      „Dein Schritt-für-Schritt-Anleitung" → „Deine …",
                            „die Geld" → „das Geld" (Beweis aus
                            data/genus_lexikon.txt; Auto-Fix nur bei
                            EINDEUTIGEM Ziel – sonst Report mit Vorschlägen)
  LT6  Präposition-Kasus    „mit dein Konto" → „mit deinem Konto" (der Kasus
                            kommt aus der Präposition, das Genus aus dem
                            Lexikon – ohne Präposition keine LT6-Prüfung)

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
    protect_zones, unprotect,
)

WHITELIST_FILE = os.path.join(ROOT, "data", "grammar_whitelist.txt")
GENUS_FILE = os.path.join(ROOT, "data", "genus_lexikon.txt")
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


# ============================================================ LT5/LT6 Kongruenz
# AUFTRAG (Frank, 30.10.2026): „Rechtschreib- und Grammatikprüfung dauerhaft
# auf Highend-Niveau einer Profi-Agentur nachschärfen und Fehler dauerhaft
# mit Selbstheilung beheben.“
#
# WARUM EINE ZWEITE PRÜF-ART: LT1–LT4 sind Wendungs-Regeln (Regex auf
# Oberflächen). Sie können per Konstruktion nicht sehen, dass „dein“ und
# „Anleitung“ nicht zueinander passen – das ist Morphologie, keine Wendung.
# Der Artikel 2026-10-24-etf-sparplan-… stand mit „Dein Schritt-für-Schritt-
# Anleitung“ in Titel, Cover, Pinterest und H1 im Netz, und ALLE Wachen
# meldeten 0 Funde. Genau diese Blindstelle schließt LT5.
#
# BEWEISART (kein Raten): Zu jeder Oberflächenform eines Artikelworts gibt es
# eine abzählbare Menge von Lesungen (Genus · Numerus · Kasus). Passt KEINE
# Lesung zum Genus des Nomens (data/genus_lexikon.txt), ist der Satz falsch –
# unabhängig davon, welchen Kasus der Autor wollte. Der Auto-Fix wird nur
# geschrieben, wenn genau EIN Ziel übrig bleibt; sonst bleibt es beim Report
# mit Vorschlagsliste. Damit kann die Wache nichts verschlechtern.
#
# LT6 benutzt dieselbe Maschinerie, nur ist der Kasus hier nicht gesucht,
# sondern gesetzt: „mit“ regiert Dativ, „für“ Akkusativ. Wechselpräpositionen
# (in, an, auf …) sind bewusst KEINE LT6-Auslöser, weil sie zwei Kasus regieren.
KASUS = ("nom", "akk", "dat", "gen")

# Endungen der Artikelwörter „ein/kein/mein/dein/sein/ihr/unser“ (ein-Paradigma)
EIN_ENDUNG = {
    ("m", "nom"): "", ("n", "nom"): "", ("f", "nom"): "e",
    ("m", "akk"): "en", ("n", "akk"): "", ("f", "akk"): "e",
    ("m", "dat"): "em", ("n", "dat"): "em", ("f", "dat"): "er",
    ("m", "gen"): "es", ("n", "gen"): "es", ("f", "gen"): "er",
    ("pl", "nom"): "e", ("pl", "akk"): "e", ("pl", "dat"): "en",
    ("pl", "gen"): "er",
}

# Endungen von „dies-/jed-/welch-/manch-“ (der-Paradigma als Stamm + Endung)
DIES_ENDUNG = {
    ("m", "nom"): "er", ("f", "nom"): "e", ("n", "nom"): "es",
    ("pl", "nom"): "e",
    ("m", "akk"): "en", ("f", "akk"): "e", ("n", "akk"): "es",
    ("pl", "akk"): "e",
    ("m", "dat"): "em", ("f", "dat"): "er", ("n", "dat"): "em",
    ("pl", "dat"): "en",
    ("m", "gen"): "es", ("f", "gen"): "er", ("n", "gen"): "es",
    ("pl", "gen"): "er",
}

# Bestimmter Artikel – eigene Formen je Merkmalsbündel
BESTIMMT = {
    ("m", "nom"): "der", ("f", "nom"): "die", ("n", "nom"): "das",
    ("pl", "nom"): "die",
    ("m", "akk"): "den", ("f", "akk"): "die", ("n", "akk"): "das",
    ("pl", "akk"): "die",
    ("m", "dat"): "dem", ("f", "dat"): "der", ("n", "dat"): "dem",
    ("pl", "dat"): "den",
    ("m", "gen"): "des", ("f", "gen"): "der", ("n", "gen"): "des",
    ("pl", "gen"): "der",
}

# Familie → (Bauart, Stamm/Tabelle, erlaubte Numeri)
# „ein“ hat KEINEN Plural – das ist der Grund, warum eine Pluralform nach
# „ein“ nie heilbar ist (dort bleibt es beim Report).
FAMILIEN = {}
for _stamm in ("kein", "mein", "dein", "sein", "ihr", "unser"):
    FAMILIEN[_stamm] = ("stamm", _stamm, EIN_ENDUNG, ("sg", "pl"))
FAMILIEN["ein"] = ("stamm", "ein", EIN_ENDUNG, ("sg",))
FAMILIEN["der"] = ("tabelle", BESTIMMT, None, ("sg", "pl"))
for _stamm in ("dies", "jed", "welch", "manch"):
    FAMILIEN[_stamm] = ("stamm", _stamm, DIES_ENDUNG, ("sg", "pl"))
# „euer“ verliert im flektierten Gebrauch das mittlere e (euer Haus, eurem Haus)
FAMILIEN["euer"] = ("liste", {
    ("m", "nom", "sg"): "euer", ("n", "nom", "sg"): "euer",
    ("n", "akk", "sg"): "euer",
    ("f", "nom", "sg"): "eure", ("f", "akk", "sg"): "eure",
    ("m", "dat", "sg"): "eurem", ("n", "dat", "sg"): "eurem",
    ("f", "dat", "sg"): "eurer", ("m", "gen", "sg"): "eures",
    ("n", "gen", "sg"): "eures", ("f", "gen", "sg"): "eurer",
    ("m", "akk", "sg"): "euren",
    ("pl", "nom", ""): "eure", ("pl", "akk", ""): "eure",
    ("pl", "dat", ""): "euren", ("pl", "gen", ""): "eurer",
}, None, ("sg", "pl"))

# FORM[(familie, genus, numer, kasus)] = Oberfläche
# LESUNG[oberflaeche] = set((familie, genus, numer, kasus))
FORM = {}
LESUNG = {}
for _fam, (_art, _a, _b, _numeri) in FAMILIEN.items():
    for _num in _numeri:
        for _genus in ("m", "f", "n", "pl"):
            if _num == "sg" and _genus == "pl":
                continue
            if _num == "pl" and _genus != "pl":
                continue
            for _kasus in KASUS:
                if _art == "tabelle":
                    _form = BESTIMMT.get((_genus if _num == "sg" else "pl",
                                          _kasus))
                elif _art == "liste":
                    _form = _a.get((_genus, _kasus,
                                    _num if _num == "sg" else ""))
                else:
                    _end = _b.get((_genus if _num == "sg" else "pl",
                                   _kasus))
                    _form = None if _end is None else _a + _end
                if not _form:
                    continue
                FORM[(_fam, _genus, _num, _kasus)] = _form.lower()
                LESUNG.setdefault(_form.lower(), set()).add(
                    (_fam, _genus, _num, _kasus))

# Oberflächen, die zu mehreren Familien gehören, sind mehrdeutig → raus
# (z. B. „der“ als Artikel und als Relativpronomen wäre egal, aber „ihr“
# als Possessiv und als Personalpronomen ist es nicht).
_MEHRFACH = {f for f, l in LESUNG.items()
             if len({x[0] for x in l}) > 1}
for _f in _MEHRFACH:
    LESUNG.pop(_f, None)

# Präpositionen mit EINDEUTIGEM Kasus. Wechselpräpositionen (in, an, auf,
# über, unter, vor, hinter, neben, zwischen) fehlen absichtlich.
PRAEP_DATIV = {
    "mit", "nach", "aus", "von", "zu", "bei", "seit", "gegenüber", "entgegen",
    "gemäß", "samt", "ab", "dank", "laut", "zufolge", "nahe", "entsprechend",
}
# „bis“ fehlt absichtlich: „bis der Anschluss geschaltet ist“ ist eine
# Konjunktion, keine Präposition – am Bestand 30.10.2026 belegt.
PRAEP_AKKUSATIV = {
    "durch", "für", "gegen", "ohne", "um", "wider",
}
PRAEP_GENITIV = {
    "wegen", "trotz", "statt", "anstatt", "während", "aufgrund", "infolge",
    "außerhalb", "innerhalb", "oberhalb", "unterhalb", "diesseits", "jenseits",
    "seitens", "hinsichtlich", "bezüglich", "mangels", "zugunsten", "anstelle",
    "anhand", "vorbehaltlich", "zwecks", "kraft",
}

# Genitiv nach Präposition ist im Fließtext dieser Seite die Ausnahme und
# strittig („dank des“, „laut des“) – LT6 heilt nur Dativ und Akkusativ.
_KASUS_NACH_PRAEP = {}
for _p in PRAEP_DATIV:
    _KASUS_NACH_PRAEP[_p] = frozenset({"dat"})
for _p in PRAEP_AKKUSATIV:
    _KASUS_NACH_PRAEP[_p] = frozenset({"akk"})

# Artikelwort + (Leerraum) + Nomen. Bindestriche gehören ZUM Nomen: „Budget‑Kontrolle“
# ist ein Kompositum und wird als Ganzes nachgeschlagen – nie halb geprüft.
HYPH = "\\-\u2010\u2011\u00ad"
# Der Bestand trennt mit normalem, geschütztem (U+00A0) und schmalem
# geschütztem Leerzeichen (U+202F, „Girokonto\u202fVergleich“) – alle gelten.
WS = " \u00A0\u202F\u2009\u2007"
KONGRUENZ_RX = re.compile(
    r"(?<![\w" + HYPH + r"])([A-Za-zÄÖÜäöüß]{2,12})([" + WS + r"])"
    r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß" + HYPH + r"]{3,})"
    r"(?![\w" + HYPH + r"])")

_LINKS_WORT_RX = re.compile(r"([A-Za-zÄÖÜäöüß]+)[" + WS + r"]+$")

# FALSCH-POSITIV-SPERREN (alle am Bestand vom 30.10.2026 belegt, siehe
# GRAMMATIK-KONGRUENZ-HIGHEND-2026-10-30.md). Jede Sperre ist ein Satz
# echter deutscher Grammatik, den eine Oberflächen-Regel nicht sehen kann:
#   1) Relativpronomen: „Personen, die Geld brauchen“ – „die“ ist kein Artikel.
#   2) Demonstrativpronomen: „sind das Werte, die …“ – „das“ zeigt auf etwas.
#   3) Schwache Adjektivdeklination: „dem einen Konto“, „auf der einen Seite“ –
#      nach bestimmtem Artikel ist „einen/eine“ Adjektiv, kein Artikelwort.
#   4) Zusammengesetztes mit Leerzeichen: „die Energieausweis Kosten“ – das
#      Nomen steht im Kompositum, der Kopf ist „Kosten“, nicht „Energieausweis“.
#   5) „um der Kontrolle willen“ – feste Genitivfügung, keine Akkusativ-Regel.
_PRONOMEN_DAVOR = re.compile(
    r"(?:^|[" + WS + r"])(?:und|oder|aber|denn|sondern|wie|als|dass|ob|wenn|"
    r"weil|ist|sind|war|waren|bleibt|bleiben|gibt|gilt|wird|werden)"
    r"[" + WS + r"]+$", re.I)
# Doppelpunkt und Klammer sind KEINE Pronomen-Anzeiger: „Titel: Dein Konto“
# ist der Normalfall dieses Blogs. Komma, Semikolon und Gedankenstrich sind es.
_PUNKT_DAVOR = ",;–—["
_ARTIKEL_DAVOR = {
    "der", "die", "das", "den", "dem", "des", "dieser", "diese", "dieses",
    "diesem", "diesen", "jeder", "jede", "jedes", "jedem", "jeden", "welcher",
    "welche", "welches", "welchem", "welchen", "mein", "meine", "meinem",
    "meinen", "dein", "deine", "deinem", "deinen", "sein", "seine", "seinem",
    "seinen", "unser", "unsere", "unserem", "unseren", "kein", "keine",
    "keinem", "keinen", "manche", "mancher", "manchen", "beide", "beiden",
}


GENUS_TAGS = {}


def lade_genus_lexikon(pfad=None):
    """Liest data/genus_lexikon.txt → {oberflaeche: ((genus, numer), …)}.

    Fehlt die Datei, ist die Prüfung AUS (keine Funde) – aber der Selbsttest
    sagt es laut und `--lexikon-pruefen` zeigt die Lücke. Ein stiller Ausfall
    wäre schlimmer als eine sichtbare Lücke.
    """
    global GENUS_TAGS
    pfad = pfad or GENUS_FILE
    tags = {}
    if not os.path.exists(pfad):
        GENUS_TAGS = {}
        return GENUS_TAGS
    with open(pfad, encoding="utf-8") as fh:
        for zeile in fh:
            zeile = zeile.split("#", 1)[0].strip()
            if not zeile or zeile.startswith("["):
                continue
            teile = zeile.split()
            if len(teile) != 2:
                continue
            wort, tag = teile[0].lower(), teile[1].lower()
            merkmale = []
            for einzeln in tag.split("/"):
                if einzeln == "pl":
                    merkmale.append(("pl", "pl"))
                elif einzeln in ("m", "f", "n"):
                    merkmale.append((einzeln, "sg"))
            if merkmale:
                tags[wort] = tuple(merkmale)
    GENUS_TAGS = tags
    return tags


def _gesperrt(text, m, det, nomen):
    """Falsch-Positiv-Sperren – Rückgabe: Grund (oder None)."""
    links = text[:m.start()]
    # 1) Direkt nach Satzzeichen ist ein Artikelwort im Deutschen ein Pronomen.
    if links.rstrip()[-1:] and links.rstrip()[-1] in _PUNKT_DAVOR:
        return "Pronomen nach Satzzeichen"
    # 2) „ist/sind/gibt das …“ → Demonstrativpronomen.
    if det.lower() == "das" and _PRONOMEN_DAVOR.search(links):
        return "Demonstrativpronomen"
    # 3) Bestimmter Artikel davor → „einen/eine“ ist Adjektiv (schwache Dekl.).
    vor = _LINKS_WORT_RX.search(links)
    if vor and vor.group(1).lower() in _ARTIKEL_DAVOR:
        return "schwache Adjektivdeklination"
    # 4) Nomen ist nur der erste Teil eines Kompositums mit Leerzeichen.
    if re.match(r"[" + WS + r"]+[A-ZÄÖÜ]", text[m.end():m.end() + 2]):
        return "Kompositum mit Leerzeichen"
    # 5) „um der Kontrolle willen“ – feste Fügung.
    if re.match(r"[" + WS + r"]+willen\b", text[m.end():m.end() + 9]):
        return "Fügung „um … willen“"
    return None


def _kasus_aus_praeposition(text, pos):
    """Kasus, den die unmittelbar vorangehende Präposition erzwingt (oder None)."""
    m = _LINKS_WORT_RX.search(text[:pos])
    if not m:
        return None
    return _KASUS_NACH_PRAEP.get(m.group(1).lower())


def _ziel_formen(familie, merkmale, kasus_menge):
    """Alle zulässigen Artikelwort-Formen für die Merkmale (ohne Duplikate)."""
    formen = set()
    for genus, numer in merkmale:
        if numer not in FAMILIEN[familie][3]:
            continue
        for kasus in kasus_menge:
            # Dativ Plural verlangt zusätzlich -n AM NOMEN („den Preisen“).
            # Nur das Artikelwort zu heilen ergäbe „den Preise“ – also nie.
            if numer == "pl" and kasus == "dat":
                continue
            form = FORM.get((familie, genus, numer, kasus))
            if form:
                formen.add(form)
    return formen


def kongruenz_funde(text, lexikon=None):
    """LT5/LT6-Funde in `text` (bereits schutzzonen-maskiert oder roh).

    Rückgabe je Fund: rule, found, fix (None = nur Report), label, ctx,
    start/end des Artikelworts, hinweis (Vorschläge, wenn mehrdeutig).
    """
    lexikon = GENUS_TAGS if lexikon is None else lexikon
    if not lexikon:
        return []
    funde = []
    for m in KONGRUENZ_RX.finditer(text):
        det = m.group(1)
        nomen = m.group(3)
        lesungen = LESUNG.get(det.lower())
        if not lesungen:
            continue
        merkmale = lexikon.get(nomen.lower())
        if not merkmale:
            continue
        if _gesperrt(text, m, det, nomen):
            continue
        familie = next(iter(lesungen))[0]
        praep_kasus = _kasus_aus_praeposition(text, m.start())
        passend = [l for l in lesungen if (l[1], l[2]) in merkmale]
        if praep_kasus is None:
            if passend:
                continue  # Kongruenz in Ordnung
            regel = "LT5"
            label = f"Genus/Numerus: „{det} {nomen}“"
        else:
            if any(l[3] in praep_kasus for l in passend):
                continue  # Kasus passt zur Präposition
            regel = "LT6"
            label = (f"Kasus nach Präposition ({'/'.join(sorted(praep_kasus))}): "
                     f"„{det} {nomen}“")

        # Intendierter Kasus = die Kasus, die die GESCHRIEBENE Form ausdrückt.
        # Wer „dein“ schreibt, meint Nominativ oder Akkusativ – deshalb ist
        # „dein Anleitung“ → „deine Anleitung“ eindeutig und nicht geraten.
        if praep_kasus is not None:
            kasus_menge = set(praep_kasus)
        else:
            kasus_menge = {l[3] for l in lesungen} or set(KASUS)
        kandidaten = _ziel_formen(familie, merkmale, kasus_menge)
        kandidaten.discard(det.lower())
        fix = None
        hinweis = ""
        # Mehrdeutige Nomen (m/pl: der Anbieter / die Anbieter) sind NIE
        # eindeutig heilbar – Singular und Plural verlangen verschiedene
        # Artikelwörter, und die Wache weiß nicht, was gemeint war.
        if len(kandidaten) == 1 and len(merkmale) == 1:
            ziel = next(iter(kandidaten))
            fix = ziel[:1].upper() + ziel[1:] if det[:1].isupper() else ziel
        else:
            hinweis = " · ".join(sorted(kandidaten)) if kandidaten else "—"
        ctx = text[max(0, m.start() - 36): m.end() + 36].replace("\n", " ")
        funde.append({
            "rule": regel,
            "found": m.group(0),
            "fix": fix,
            "label": label,
            "ctx": ctx.strip(),
            "start": m.start(),
            "end": m.end(1),
            "hinweis": hinweis,
        })
    return funde


def kongruenz_heilen(text, lexikon=None):
    """Wendet die eindeutigen LT5/LT6-Fixe an. Rückgabe: (text, n, funde)."""
    body, origs = protect_zones(text)
    funde = kongruenz_funde(body, lexikon)
    n = 0
    for f in sorted([f for f in funde if f["fix"]], key=lambda x: -x["start"]):
        body = body[:f["start"]] + f["fix"] + body[f["end"]:]
        n += 1
    return unprotect(body, origs), n, funde


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

    # ---------------- LT5/LT6 Kongruenz (30.10.2026) ----------------------
    lexikon = lade_genus_lexikon()
    if len(lexikon) < 400:
        fehler.append(f"LT5/LT6: Genus-Lexikon zu klein oder fehlt "
                      f"({len(lexikon)} Einträge, erwartet >= 400)")
        return fehler

    def kfix(t):
        return kongruenz_heilen(t, lexikon)[0]

    def kfund(t):
        return kongruenz_funde(t, lexikon)

    # 11) Der Vorfall: Titel des ETF-Sparplan-Artikels (24.10.2026)
    if "Deine Schritt-für-Schritt-Anleitung" not in kfix(
            "ETF-Sparplan starten: Dein Schritt-für-Schritt-Anleitung"):
        fehler.append("LT5: „Dein Schritt-für-Schritt-Anleitung“ nicht geheilt")
    # 12) Genus über den bestimmten Artikel
    if "das Geld" not in kfix("die Geld liegt auf dem Konto."):
        fehler.append("LT5: „die Geld“ → „das Geld“ fehlt")
    # 13) LT6: Kasus aus der Präposition, Genus aus dem Lexikon
    if "mit deinem Konto" not in kfix("Du sparst mit dein Konto."):
        fehler.append("LT6: „mit dein Konto“ → „mit deinem Konto“ fehlt")
    if "um einen Grad" not in kfix("Senke die Temperatur um ein Grad."):
        fehler.append("LT6: „um ein Grad“ → „um einen Grad“ fehlt")
    # 14) NEGATIV: Relativpronomen nach Komma („Personen, die Geld brauchen“)
    if kfix("Personen, die Geld für Ziele brauchen.") != \
            "Personen, die Geld für Ziele brauchen.":
        fehler.append("LT5 FALSCH-POSITIV: Relativpronomen „die Geld“ verändert")
    # 15) NEGATIV: Demonstrativpronomen („sind das Werte, die …“)
    if kfix("Sind das Werte, die gelten?") != "Sind das Werte, die gelten?":
        fehler.append("LT5 FALSCH-POSITIV: Demonstrativpronomen „das Werte“")
    # 16) NEGATIV: schwache Adjektivdeklination („auf dem einen Konto“)
    if kfix("Auf dem einen Konto laufen alle Abbuchungen.") != \
            "Auf dem einen Konto laufen alle Abbuchungen.":
        fehler.append("LT5 FALSCH-POSITIV: „dem einen Konto“ ist korrekt")
    # 17) NEGATIV: Kompositum mit Leerzeichen („für den Girokonto Vergleich“)
    if kfix("Kriterien für den Girokonto Vergleich") != \
            "Kriterien für den Girokonto Vergleich":
        fehler.append("LT6 FALSCH-POSITIV: „Girokonto Vergleich“ verändert")
    # 18) NEGATIV: Plural-Dativ wird NIE am Artikelwort allein geheilt
    #     („den Preise“ bräuchte „den Preisen“ – also Report statt Fix)
    if any(f["fix"] for f in kfund("Bei den Preise fehlt ein Wert.")):
        fehler.append("LT5: Plural-Dativ wurde am Artikelwort geheilt")
    # 19) NEGATIV: mehrdeutiges Nomen (der/die Anbieter) ist nie heilbar
    if any(f["fix"] for f in kfund("Die Anbieter senken den Preis.")):
        fehler.append("LT5 FALSCH-POSITIV: „Die Anbieter“ (Plural) beanstandet")
    # 20) Idempotenz der Kongruenz-Heilung
    k1 = kfix("Dein Anleitung liegt neben die Geld.")
    if kfix(k1) != k1:
        fehler.append("LT5/LT6 Idempotenz verletzt")
    return fehler


# ============================================================ Lauf
TITEL_ZEILE = re.compile(r"(?m)^title:[ \t]*(.+?)[ \t]*$")
# Marken-/Pin-nahe Frontmatter-Felder: sichtbar auf Pinterest, im Cover und in
# der Suchvorschau. Sie werden GEPRÜFT, aber nie automatisch geschrieben – ein
# Pin-Text ist ein Markenvertrag, und `cover.alt` gehört zum gerenderten Bild.
REPORT_FELDER = (
    ("kurzantwort", re.compile(r"(?m)^kurzantwort:[ \t]*(.+?)[ \t]*$")),
    ("pin_title", re.compile(r"(?m)^pin_title:[ \t]*(.+?)[ \t]*$")),
    ("pin_description", re.compile(r"(?m)^pin_description:[ \t]*(.+?)[ \t]*$")),
    ("cover.alt", re.compile(r"(?m)^\s+alt:[ \t]*[\"\']?(.+?)[\"\']?[ \t]*$")),
    ("cover.caption", re.compile(r"(?m)^\s+caption:[ \t]*[\"\']?(.+?)[\"\']?[ \t]*$")),
)


def feld_kongruenz(fm, lexikon=None):
    """Kongruenz in den markennahen Frontmatter-Feldern – Report ohne Fix."""
    lexikon = GENUS_TAGS if lexikon is None else lexikon
    out = []
    for zone, rx in REPORT_FELDER:
        m = rx.search(fm)
        if not m:
            continue
        for f in kongruenz_funde(m.group(1), lexikon):
            zeile = _kongruenz_zeile(f, "title")  # Fix bleibt aus (Markenvertrag)
            zeile["zone"] = zone
            zeile["vorschlag"] = f["fix"]
            out.append(zeile)
    return out


def _kongruenz_zeile(f, zone):
    """Fund → Report-Zeile. Titel sind Cover-Marken-Lock: Vorschlag, kein Fix."""
    return {
        "rule": f["rule"], "found": f["found"],
        "fix": None if zone == "title" else f["fix"],
        "label": f["label"], "ctx": f["ctx"], "hinweis": f["hinweis"],
        "vorschlag": f["fix"] if zone == "title" else "",
        "zone": zone,
    }


def heile_titelzeile(fm, lexikon=None):
    """Heilt die Kongruenz im Frontmatter-`title` (nur mit --fix-titel).

    Der Titel ist Cover-Marken-Lock: Er wird NUR geschrieben, wenn die
    Kongruenz-Wache genau ein Ziel beweist (nie bei mehrdeutigem Genus).
    Das Cover rendert den Titel – nach dem Schreiben erneuert
    `check_covers.py --fix` die Bildvarianten (Deploy- und Health-Lauf).
    Rückgabe: (neues_fm, (alt, neu) | None)
    """
    lexikon = GENUS_TAGS if lexikon is None else lexikon
    m = TITEL_ZEILE.search(fm)
    if not m:
        return fm, None
    roh = m.group(1).strip()
    zitat = roh[:1] if roh[:1] in ("\"", "'") else ""
    titel = roh.strip("\"'")
    neu, n, _ = kongruenz_heilen(titel, lexikon)
    if not n or neu == titel:
        return fm, None
    neue_zeile = f"title: {zitat}{neu}{zitat}" if zitat else f'title: "{neu}"'
    return fm[:m.start()] + neue_zeile + fm[m.end():], (titel, neu)


def analyze(a, whitelist, lexikon=None):
    """Prüft Body + description + title (LT1–LT6)."""
    lexikon = GENUS_TAGS if lexikon is None else lexikon
    funde = []
    body = a["body"]
    for f in scan_rules(body, RULES):
        if apply_whitelist_gate(f, whitelist):
            funde.append(f)
    # LT5/LT6 – Kongruenz (Morphologie; 30.10.2026)
    for f in kongruenz_funde(body, lexikon):
        funde.append(_kongruenz_zeile(f, "body"))
    # Description separat (Frontmatter, Auto-Fix erlaubt)
    if a.get("description"):
        for f in scan_rules(a["description"], RULES):
            if apply_whitelist_gate(f, whitelist):
                f["zone"] = "description"
                funde.append(f)
        for f in kongruenz_funde(a["description"], lexikon):
            funde.append(_kongruenz_zeile(f, "description"))
    # Title: nur melden, nie fixen (Cover-Marken-Lock; --fix-titel ist opt-in)
    if a.get("title"):
        for f in scan_rules(a["title"], RULES):
            if apply_whitelist_gate(f, whitelist):
                f["zone"] = "title"
                f["fix"] = None  # Titel nie schreiben
                funde.append(f)
        for f in kongruenz_funde(a["title"], lexikon):
            funde.append(_kongruenz_zeile(f, "title"))
    # Marken-/Pin-Felder: immer Report, nie Schreiben (Pin = Markenvertrag)
    if a.get("fm"):
        funde.extend(feld_kongruenz(a["fm"], lexikon))
    return funde


def lexikon_pruefen(lexikon=None):
    """Selbstkontrolle des Genus-Lexikons (Duplikate, Tags, Abdeckung)."""
    lexikon = GENUS_TAGS if lexikon is None else lexikon
    probleme = []
    gesehen = {}
    with open(GENUS_FILE, encoding="utf-8") as fh:
        for nr, zeile in enumerate(fh, 1):
            roh = zeile.split("#", 1)[0].strip()
            if not roh or roh.startswith("["):
                continue
            teile = roh.split()
            if len(teile) != 2:
                probleme.append(f"Zeile {nr}: erwartet „<wort> <tag>“ – {zeile.strip()!r}")
                continue
            wort, tag = teile[0].lower(), teile[1].lower()
            if wort != teile[0]:
                probleme.append(f"Zeile {nr}: Oberfläche nicht klein – {teile[0]!r}")
            for einzeln in tag.split("/"):
                if einzeln not in ("m", "f", "n", "pl"):
                    probleme.append(f"Zeile {nr}: unbekannter Tag {einzeln!r}")
            gesehen[wort] = gesehen.get(wort, 0) + 1
    for wort, n in gesehen.items():
        if n > 1:
            probleme.append(f"Oberfläche doppelt: {wort!r} ({n}×)")
    # Suffix-Plausibilität: Das Deutsche ist hier eindeutig, und ein falsches
    # Genus ist der teuerste Fehler im Lexikon – es erzeugt einen FALSCHEN
    # Fix („die Internet“ → „der Internet“). Geprüft werden nur Endungen ohne
    # Ausnahme in der Blog-Sprache; die Liste wächst nur mit Beleg.
    FEM_SUFFIX = ("ung", "heit", "keit", "schaft", "tion", "tät", "enz", "anz",
                  "sion", "ive", "ur", "ik", "ie")
    # „Notgroschen“, „Tropfen“, „Happen“: -en/-chen nach Konsonant ist oft
    # maskulin, nur das VERKLEINERUNGS-chen ist neutrum. Ausnahmen bleiben
    # deshalb eine Liste, keine Regel.
    NEU_SUFFIX = ("lein",)
    NEU_AUSNAHMEN = ("notgroschen",)
    for wort, merkmale in lexikon.items():
        genera = {g for g, _n in merkmale}
        if len(genera) > 1:
            continue  # absichtlich mehrdeutig
        if wort.endswith(FEM_SUFFIX) and "f" not in genera:
            probleme.append(f"Suffix „-{wort[-4:]}“ ist feminin, "
                            f"„{wort}“ steht aber als {'/'.join(sorted(genera))}")
        if (wort.endswith(NEU_SUFFIX) and "n" not in genera
                and wort not in NEU_AUSNAHMEN):
            probleme.append(f"Suffix „-{wort[-4:]}“ ist neutrum, "
                            f"„{wort}“ steht aber als {'/'.join(sorted(genera))}")
    # Plural-Gleichheit: „der Anbieter“ → „die Anbieter“, „das Kabel“ →
    # „die Kabel“. Steht so ein Nomen nur mit EINEM Genus im Lexikon, hält
    # die Wache den Plural für einen Numerus-Fehler und „heilt“ korrektes
    # Deutsch („keine Kabel“ → „kein Kabel“). Genau das passierte am
    # 30.10.2026 beim Aufbau. Zwei Ausnahmen bleiben gelistet, weil sie KEINE
    # gleiche Pluralform haben: Umlaut-Plural und Nomen ohne Plural.
    PLURAL_GLEICH_ENDUNG = ("er", "el", "en")
    PLURAL_ANDERS = frozenset({
        # Umlaut- oder Endungs-Plural
        "schaden", "faustregel", "formel", "kennnummer", "nummer", "regel",
        "rufnummer", "steuer", "umsatzsteuer", "zählernummer", "beispiel",
        "hotel", "papier", "rechenbeispiel", "klausel", "backofen",
        # kein Plural im Sprachgebrauch (Verb-Nominalisierung, Stoffname)
        "dauer", "sparen", "wissen", "wasser", "absenden",
    })
    for wort, merkmale in lexikon.items():
        genera = {g for g, _n in merkmale}
        num = {n for _g, n in merkmale}
        if len(genera) > 1 or num != {"sg"}:
            continue  # mehrdeutige Genera heilen ohnehin nie
        if len(wort) < 5 or not wort.endswith(PLURAL_GLEICH_ENDUNG):
            continue
        if wort in PLURAL_ANDERS:
            continue
        probleme.append(f"„{wort}“ ist formgleich im Plural – Tag "
                        f"„{'/'.join(sorted(genera))}/pl“ fehlt (sonst heilt "
                        "die Wache „keine " + wort.capitalize() + "“ zu "
                        "„kein " + wort.capitalize() + "“)")
    zaehler = {}
    for merkmale in lexikon.values():
        for genus, _numer in merkmale:
            zaehler[genus] = zaehler.get(genus, 0) + 1
    return probleme, zaehler


def lexikon_vorschlag(arts, lexikon=None, limit=60):
    """Häufigste Artikelwort+Nomen-Stellen OHNE Lexikon-Eintrag.

    Das ist der Wartungspfad: Der Bestand sagt, welche Form als Nächstes
    aufgenommen werden sollte – entschieden wird sie von Hand, nie im Lauf.
    """
    lexikon = GENUS_TAGS if lexikon is None else lexikon
    zaehler = {}
    for a in arts:
        for f in kongruenz_funde_alle(a["body"]):
            if f["nomen"] in lexikon:
                continue
            key = (f["det"], f["nomen"])
            zaehler[key] = zaehler.get(key, 0) + 1
    return sorted(zaehler.items(), key=lambda kv: -kv[1])[:limit]


def kongruenz_funde_alle(text):
    """Rohkandidaten ohne Lexikon-Filter (nur für den Lexikon-Vorschlag)."""
    out = []
    for m in KONGRUENZ_RX.finditer(text):
        det = m.group(1).lower()
        if det not in LESUNG:
            continue
        if _gesperrt(text, m, m.group(1), m.group(3)):
            continue
        out.append({"det": det, "nomen": m.group(3).lower(),
                    "nomen_roh": m.group(3)})
    return out


def _genus_zeugen():
    """Artikelwörter mit EINDEUTIGEM Genus.

    „ein“, „die“ und „keine“ tragen mehrere Genera und taugen als Zeuge nicht.
    Nur wer genau eine Lesart hat, darf für eine Genus-Aussage bürgen.
    """
    zeugen = {}
    for ober, lesungen in LESUNG.items():
        genera = {(l[1], l[2]) for l in lesungen}
        if len(genera) == 1:
            zeugen[ober] = next(iter(genera))
    return zeugen


GENUS_ZEUGEN = None


def lexikon_evidenz(arts, lexikon=None):
    """Genus-Zeugnis je Nomen aus dem BESTAND (kein Wörterbuch, kein Netz).

    Ein Nomen, das im Blog ausschließlich hinter eindeutigen femininen
    Artikelwörtern steht, ist mit hoher Wahrscheinlichkeit feminin. Ein Nomen
    mit gemischtem Zeugnis ist es nicht – dann wird es NICHT aufgenommen.
    Das ist der Unterschied zwischen einem Lexikon-Eintrag und einer
    Vermutung: Am 30.10.2026 standen „internet“, „land“ und „stadt“ mit
    falschem Genus in der Datei, und die Wache hätte damit falsche Sätze
    „geheilt“. Das Zeugnis hätte jeden dieser drei Fälle verhindert.
    """
    global GENUS_ZEUGEN
    if GENUS_ZEUGEN is None:
        GENUS_ZEUGEN = _genus_zeugen()
    lexikon = GENUS_TAGS if lexikon is None else lexikon
    zeugnis = {}
    for a in arts:
        for f in kongruenz_funde_alle(a["body"]):
            nomen = f["nomen"]
            if nomen in lexikon:
                continue
            # Nur Substantive: Im Satz groß geschrieben. Kleingeschriebene
            # Treffer sind Verben/Adjektive und als Genus-Zeuge wertlos.
            if not f["nomen_roh"][:1].isupper():
                continue
            zeuge = GENUS_ZEUGEN.get(f["det"])
            if not zeuge:
                continue
            eintrag = zeugnis.setdefault(nomen, {})
            schluessel = f"{zeuge[0]}-{zeuge[1]}"
            eintrag[schluessel] = eintrag.get(schluessel, 0) + 1
    return zeugnis


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    do_fix = "--fix" in argv
    strict = "--strict" in argv
    as_json = "--json" in argv
    include_drafts = "--include-drafts" in argv
    new_only = "--new-only" in argv
    fix_titel = "--fix-titel" in argv
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
        print("✅ Grammatik-Selbsttest: 20 Fälle grün (LT1–LT6, offline, ohne API).")
        return 0

    stf = run_selftest()
    if stf:
        print("🛑 SELBSTTEST ROT – Sabotage verhindert, kein Schreiben:")
        print("\n".join("  " + f for f in stf))
        return 2

    whitelist = load_whitelist()
    lexikon = lade_genus_lexikon()

    if "--lexikon-pruefen" in argv:
        probleme, zaehler = lexikon_pruefen(lexikon)
        print(f"📚 Genus-Lexikon: {len(lexikon)} Oberflächen · "
              + " · ".join(f"{k}: {v}" for k, v in sorted(zaehler.items())))
        if probleme:
            print("🛑 " + str(len(probleme)) + " Befund(e):")
            print("\n".join("  " + p for p in probleme))
            return 1
        print("✅ Format, Tags und Eindeutigkeit in Ordnung.")
        return 0

    files = None
    if only_file:
        p = only_file if os.path.isabs(only_file) \
            else os.path.join(ROOT, only_file)
        if not os.path.exists(p):
            p = os.path.join(ROOT, "content", "posts", only_file)
        files = [p]
    arts = load_articles(files, new_only=new_only, include_drafts=include_drafts)

    if "--lexikon-vorschlag" in argv:
        evidenz = lexikon_evidenz(arts, lexikon)
        print("Die häufigsten Artikelwort+Nomen-Stellen ohne Lexikon-Eintrag:")
        print("Zeugnis = eindeutige Artikelwörter aus dem Bestand. Ein gemischtes")
        print("Zeugnis wird NICHT aufgenommen – ein Eintrag wäre dann geraten.")
        for (det, nomen), n in lexikon_vorschlag(arts, lexikon):
            zeugnis = evidenz.get(nomen, {})
            if not zeugnis:
                spur = "ohne eindeutiges Zeugnis"
            elif len(zeugnis) == 1:
                spur = f"Zeugnis {next(iter(zeugnis))} ({sum(zeugnis.values())}×)"
            else:
                spur = "Zeugnis gemischt: " + ", ".join(
                    f"{k}:{v}" for k, v in sorted(zeugnis.items(),
                                                  key=lambda kv: -kv[1]))
            print(f"{n:4d}×  {det} {nomen:30s} {spur}")
        return 0

    total = fixed = 0
    titel_geheilt = []
    rows = []
    for a in arts:
        funde = analyze(a, whitelist, lexikon)
        neu_body, n, _ = apply_rules(a["body"], RULES)
        neu_body, nk, _ = kongruenz_heilen(neu_body, lexikon)
        n += nk
        neu_desc = None
        if a.get("description"):
            d2, n2, _ = apply_rules(a["description"], RULES)
            d2, n2k, _ = kongruenz_heilen(d2, lexikon)
            if n2 + n2k:
                neu_desc, n = d2, n + n2 + n2k
        fm_neu, titel_info = (heile_titelzeile(a["fm"], lexikon)
                              if (do_fix and fix_titel) else (a["fm"], None))
        if not funde and not n and not titel_info:
            continue
        total += len(funde)
        if do_fix and (n or titel_info):
            ziel = dict(a, fm=fm_neu)
            ok, grund = write_verified(ziel, rebuild(ziel, neu_body, neu_desc),
                                       "grammar_check")
            if ok:
                fixed += n + (1 if titel_info else 0)
                if titel_info:
                    titel_geheilt.append({"slug": a["slug"],
                                          "alt": titel_info[0], "neu": titel_info[1]})
                    rows.append({"slug": a["slug"], "rule": "LT5-TITEL",
                                 "found": titel_info[0], "fix": titel_info[1],
                                 "ctx": "Frontmatter title", "label": "Titel-Kongruenz",
                                 "hinweis": "", "zone": "title"})
            else:
                rows.append({"slug": a["slug"], "rule": "SCHREIBSPERRE",
                             "found": grund, "fix": None, "ctx": "",
                             "label": "Verifikation fehlgeschlagen"})
        for f in funde:
            rows.append({"slug": a["slug"], **f})

    offen = max(0, total - fixed)
    lex_daten = {"oberflaechen": len(lexikon)}
    if as_json:
        print(json.dumps({
            "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "engine": "grammar_check (LanguageTool-Nachbau, offline; LT1–LT6)",
            "posts": len(arts), "findings": total, "fixed": fixed,
            "open": offen, "lexikon": lex_daten, "items": rows[:200],
        }, ensure_ascii=False, indent=2))
        return 1 if (strict and offen) else 0

    L = ["# 📝 GRAMMATIK-REPORT (grammar_check.py – offline, ohne API)", "",
         f"**Stand:** {now_utc()} UTC",
         f"**Modus:** {'FIX' if do_fix else 'REPORT'} · LanguageTool-Nachbau "
         f"(LT1–LT6) · Genus-Lexikon {len(lexikon)} Oberflächen",
         f"**Artikel:** {len(arts)} · **Funde:** {total} "
         f"(geheilt: {fixed} · offen: {offen})", ""]
    if rows:
        L.append("| Regel | Zone | Artikel | Fund | Fix/Vorschlag |")
        L.append("|---|---|---|---|---|")
        for r in rows[:80]:
            if r.get("fix"):
                fix_info = f"→ `{r['fix']}`"
            elif r.get("vorschlag") and r.get("zone") == "title":
                fix_info = f"→ `{r['vorschlag']}` *(Titel: Cover-Marken-Lock, `--fix-titel`)*"
            elif r.get("vorschlag"):
                fix_info = (f"→ `{r['vorschlag']}` *(Report: Feld „{r.get('zone')}“ "
                            "wird nicht automatisch geschrieben)*")
            elif r.get("hinweis"):
                fix_info = f"*(Report: {r['hinweis']})*"
            else:
                fix_info = "*(Report)*"
            L.append(f"| {r['rule']} | {r.get('zone', 'body')} | `{r['slug']}` "
                     f"| „{r['found']}“ | {fix_info} |")
    else:
        L.append("🎉 Keine Grammatik-Funde – Bestand sauber.")
    if titel_geheilt:
        L += ["", "**Titel (Cover-Marken-Lock, `--fix-titel`) geheilt:**"]
        for t in titel_geheilt:
            L.append(f"- `{t['slug']}`: „{t['alt']}“ → **„{t['neu']}“** "
                     f"(Cover: `python3 scripts/check_covers.py --fix`)")
    L += ["", "---",
          "_Offline-Nachbau der LanguageTool-Prüfung (Auftrag 25.09.2026: ohne API). "
          "Stil/Glättung macht scripts/sprachglatt.py (DeepL-Write-Nachbau). "
          "Harte Fest-Fehler (einzigste, daß, seid/seit-Pleonasmen …) liegen in "
          "scripts/hardcases_guard.py, Wortdopplungen in scripts/lektor_guard.py (L1)._"]
    with open(REPORT_FILE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    with open(JSON_FILE, "w", encoding="utf-8") as fh:
        json.dump({"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "posts": len(arts), "findings": total, "fixed": fixed,
                   "open": offen, "lexikon": lex_daten, "items": rows[:200]},
                  fh, ensure_ascii=False, indent=2)

    print("\n".join(L[:8]))
    return 1 if (strict and offen) else 0


if __name__ == "__main__":
    sys.exit(main())
