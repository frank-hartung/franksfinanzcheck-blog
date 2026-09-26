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

# ===========================================================================
#  R5 – TRUNCATION-WÄCHTER (Cover-Text-Komplettheit)
#
#  UMBAU 26.09.2026 (Issue #387, Run 36230666076) – WARUM DIE WORTLISTE WEG IST
#  --------------------------------------------------------------------------
#  R5 entschied bis heute per ERLAUBNISLISTE: Ein kleingeschriebenes Endwort
#  galt nur dann als vollständiger Titel, wenn es in `R5_END_WHITELIST` stand.
#  Diese Liste ist eine handgepflegte Kopie der deutschen Sprache – sie kann
#  nie vollständig sein und altert still. Genau das ist die Fehlerklasse, die
#  dieses Repo an anderer Stelle ausdrücklich verboten hat (selftest_runner.py:
#  "eine abgetippte Wachen-Liste altert still").
#
#  Die Rechnung dieser Konstruktion (belegt, nicht vermutet):
#    * 14.09.2026: 7 von 57 Titeln blockiert, 5 davon LIVE – Reparatur war
#      "Liste nachziehen" (die Klasse blieb).
#    * 26.09.2026: „Stromfresser finden: So senkst du deine Stromrechnung
#      massiv" – „massiv" fehlte in der Liste. Der Kandidat war inhaltlich
#      fertig, wurde aber Nacht für Nacht abgelehnt, landete in der Quarantäne
#      und riss den Vorrat unter das Ziel: Content-Reserve rot (Issue #387).
#      Zwei weitere Bestandstitel („… Kosten realistisch", „… einfach erklärt")
#      hingen an derselben Lücke.
#    * Was die Liste NICHT fand: „…Tarife – Gastari" und „…Vollkas" (großes
#      Endwort = per Regel immer erlaubt). Der Wächter blockierte also vor
#      allem korrekte Titel und ließ echte Abbrüche durch.
#
#  R5 prüft deshalb jetzt die WAHRHEITSPROBE statt eines Wortschatzes:
#  Ein Titel ist abgebrochen, wenn sein Ende GRAMMATISCH NICHT SCHLIESSEN
#  KANN – hängendes Satzzeichen/Konnektor, Auslassungspunkte, ein Wortrest
#  oder ein Wort aus einer GESCHLOSSENEN Wortklasse (Artikel, Pronomen,
#  Konjunktion, nicht-abtrennbare Präposition). Diese Klassen sind endlich
#  und ändern sich nicht – anders als der Bestand an Verben/Adjektiven.
#  Inhaltswörter (Verb, Adjektiv, Adverb, Substantiv) beenden einen Titel
#  immer gültig; neue Formulierungen brauchen keinen Listen-Nachtrag mehr.
#
#  Abtrennbare Verbzusätze („… bereitest du dich im Spätsommer VOR",
#  „… schaltest du Standby AB") sind ausdrücklich erlaubt: Sie stehen
#  regulär am Satzende. Der Wächter bleibt damit scharf für echte Abbrüche
#  („Der beste Tarif für", „… und was sie", „Kosten &") und stumm bei
#  vollständigen Sätzen.
# ===========================================================================

# Zeichen, die am Titelende IMMER auf einen Abbruch zeigen (hängender
# Konnektor, offene Klammer, offenes Anführungszeichen, Auslassung).
R5_HAENGENDE_ZEICHEN = "–—-,;:/&+·|~<([{\"„“‚‘'«»"
R5_AUSLASSUNG = ("…", "...")

# GESCHLOSSENE Wortklassen: Wörter, die einen deutschen Titel nicht beenden
# können. Endlich, vollständig, stabil – das Gegenteil einer Erlaubnisliste.
# (Groß geschriebene Endwörter = Nomen/Eigenwort und damit immer gültig;
# geprüft wird nur die kleingeschriebene Form.)
R5_SCHLUSS_TABU = {
    # Artikel / Determinative
    "der", "die", "das", "den", "dem", "des", "eine", "einen",
    "einem", "einer", "eines", "kein", "keine", "keinen", "keinem",
    "keiner", "keines", "mein", "meinen", "meinem", "meiner",
    "dein", "deine", "deinen", "deinem", "deiner", "seine",
    "seinen", "seinem", "seiner", "ihre", "ihren", "ihrem", "ihrer",
    "unser", "unsere", "unseren", "unserem", "euer", "eure", "euren",
    "dieser", "diese", "dieses", "diesen", "diesem", "jener", "jene",
    "jenes", "jeder", "jede", "jedes", "jeden", "jedem", "welcher",
    "welche", "welches", "welchen", "welchem", "manche", "mancher",
    "manches", "beide", "beiden", "solche", "solcher", "solches",
    # Pronomen
    "ich", "du", "er", "sie", "es", "wir", "man", "mich", "dich", "sich",
    "uns", "euch", "mir", "dir", "ihm", "ihnen", "ihn", "wen", "wem",
    "wessen", "derjenige", "dasselbe", "denselben", "was", "wer", "wo",
    "wohin", "woher",
    # Konjunktionen / Subjunktionen
    "und", "oder", "aber", "sowie", "sondern", "denn", "weil", "dass",
    "daß", "ob", "wenn", "falls", "obwohl", "während", "bevor",
    "nachdem", "sobald", "solange", "damit", "sodass", "bzw",
    "beziehungsweise", "entweder", "weder",
    # Präpositionen OHNE Verbzusatz-Rolle (können nie am Satzende stehen)
    "im", "am", "beim", "vom", "zum", "zur", "ins", "ans", "aufs", "fürs",
    "bei", "seit", "trotz", "wegen", "innerhalb", "außerhalb", "statt",
    "anstatt", "gemäß", "laut", "samt", "nebst", "ohne", "für", "gegen",
    "per", "pro", "je", "bis", "als", "wie", "von", "in",
    "zwischen", "gegenüber", "entlang", "dank", "mittels", "binnen",
    "außer", "seitens", "zwecks", "inklusive", "exklusive", "versus",
}
# Wörter, die zugleich abtrennbarer Verbzusatz sind, stehen NICHT im Tabu:
# „… bereitest du dich vor", „… schaltest du ab", „… fängst du an",
# „… hörst du auf", „… machst du mit", „… denkst du um", „… rüstest du nach",
# „… legst du zu", „… gehst du durch", „… zahlst du drauf".
R5_VERBZUSATZ = {
    "ab", "an", "auf", "aus", "ein", "mit", "nach", "um", "vor", "zu",
    "durch", "über", "unter", "zurück", "weg", "los", "hoch", "runter",
    "voran", "fest", "frei", "nebenbei", "drauf", "dran", "dazu", "mit",
}

# Historische Erlaubnisliste – seit 26.09.2026 NICHT mehr entscheidend.
# Sie bleibt als Regressions-Korpus erhalten: Der Selbsttest beweist, dass
# jedes dieser Endwörter weiterhin akzeptiert wird UND dass kein Eintrag
# versehentlich im Tabu gelandet ist (eine Liste, die nichts mehr entscheidet,
# kann auch nichts mehr still kaputt machen).
R5_END_WHITELIST = {
    # REPARATUR 14.09.2026: Der Gasvergleich-/Frugalismus-Lauf zeigte,
    # dass die Liste häufige saubere Endungen nicht kannte und deshalb
    # 7 von 57 Titeln blockierte (5 live!) – „… dein Netz beschleunigt“,
    # „… Energiediebe im Haushalt stoppen“, „… sparst du sofort“ sind
    # vollständige Titel. Nachziehen ist sicherer als Nachbessern: Die
    # Truncations-Falle bleibt für hängende Konnektoren und Pronomen an.
    "beschleunigt", "beschleunigen", "beschleunigst",
    "stoppen", "stopst", "stoppt",
    "ändern", "änderst", "ändert", "vermeiden", "vermeidest", "vermeidet",
    "senken", "reduzieren", "optimieren", "strukturieren", "organisieren",
    "einrichten", "umsetzen", "loslegen", "spüren", "entlasten",
    # Adverbien/Partikel, die einen Ratgebertitel regulär beenden
    "sofort", "endlich", "wirklich", "bewusst", "effizient", "nachhaltig",
    "vor", "zurück", "mit", "hoch", "runter",
    # Adjektive („Denke dich reich“, „Lebe bewusst minimal“) 
    "reich", "arm", "schlau", "sicher", "schnell", "günstig", "happy",
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
    # REPARATUR 11.09.2026 (Reserve #5): 1.-Person-Singular-Formen
    # (Ich-Perspektive des Blogs, z. B. „…warum ich meine Heizung im August
    # prüfe“). Der Truncation-Wächter kannte nur 2.-Person/Infinitiv und
    # blockierte vollständige Ich-Titel als „vermutlich unvollständig“.
    "prüfe", "senke", "zeige", "erkläre", "erklare", "verrate", "empfehle",
    "mache", "gehe", "schaue", "schau", "nutze", "nutz", "wechsle", "finde",
    "lege", "rechne", "schütze", "halte", "setze", "stelle", "beachte",
    "vergleiche", "wähle", "lerne", "kenne", "glaube", "meine",
    "sage", "lese", "sieh", "höre", "schreibe", "überprüfe", "spare",
    "plane", "klicke", "tippe", "starte", "laufe", "buche", "sichere",
    "heize", "lade", "richte", "steuere", "kontrolliere", "kalkuliere",
    "betrachte", "beobachte", "vermeide", "erziele", "erfährst",
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

    # R5: Truncation-Wächter (Wahrheitsprobe statt Wortliste, siehe Kopf).
    befund = r5_truncation(t)
    if befund:
        issues.append(("R5", befund))
    return issues


def r5_truncation(title):
    """Liefert die R5-Begründung, wenn der Titel abgebrochen ist – sonst None.

    Geprüft wird, ob das Titelende GRAMMATISCH SCHLIESSEN KANN:

      1. Auslassungspunkte („… das Wichtigste …“)
      2. hängendes Satzzeichen / offener Konnektor („… Kosten &“, „… Tarife –“)
      3. kein Endwort übrig (nur Satzzeichen)
      4. geschlossene Wortklasse am Ende: Artikel, Pronomen, Konjunktion,
         nicht-abtrennbare Präposition („… und was sie“, „Der Tarif für“)
      5. Wortrest: einzelner Buchstabe („… Strom s“)

    Alles andere ist ein vollständiger Titel – auch dann, wenn das Endwort in
    keiner Liste steht. Genau diese Umkehr beendet die Falsch-Positiv-Klasse
    aus Issue #387 („massiv“, „erklärt“, „realistisch“), ohne den Wächter
    stumpf zu machen: Echte Abbrüche enden fast immer auf Konnektor,
    Funktionswort oder Wortrest.
    """
    t_plain = re.sub(r"<[^>]+>", "", (title or "")).strip()
    if not t_plain:
        return None
    if t_plain.endswith(R5_AUSLASSUNG):
        return ("Titel endet mit Auslassungspunkten "
                f"(„…{t_plain[-14:]}“) – abgeschnitten")
    if t_plain[-1] in R5_HAENGENDE_ZEICHEN:
        return ("Titel endet mit hängendem Konnektor "
                f"(„…{t_plain[-12:]}“) – vermutlich unvollständig")
    if t_plain[-1] in ".!?":
        return None  # vollständiger Satz mit Schlusszeichen
    words = t_plain.split()
    last_word = re.sub(r"[.,;:!?\-–—\"'„“»«…]+$", "", words[-1]).strip()
    if not last_word:
        return "Titel endet ohne Endwort – vermutlich unvollständig"
    if last_word[0].isupper():
        return None  # Nomen/Eigenwort – gültiges Titelende
    if re.fullmatch(r"[\d.,\s%€]+", last_word):
        return None  # „…800 €", „…2026"
    kern = last_word.lower()
    if kern in R5_VERBZUSATZ:
        return None  # abtrennbarer Verbzusatz („… bereitest du dich vor“)
    if kern in R5_SCHLUSS_TABU:
        return (f"Titel endet auf das Funktionswort „{last_word}“ "
                "(Artikel/Pronomen/Konjunktion/Präposition) – der Satz "
                "ist abgebrochen")
    if len(kern) == 1 and kern.isalpha():
        return (f"Titel endet auf den Wortrest „{last_word}“ – "
                "vermutlich mitten im Wort abgeschnitten")
    return None  # Inhaltswort (Verb/Adjektiv/Adverb/Substantiv) = gültig


def heal_r5(title):
    """Heilt die HEILBAREN R5-Klassen deterministisch – oder lässt den Titel.

    Neu am 26.09.2026 (Issue #387): Bis heute galt „--fix kann R5 nicht
    heilen“ pauschal – und die Deckungs-Wache (reserve_healer_coverage.py)
    führte check_titles.py trotzdem als Heiler dieser Regel. Das war eine
    Behauptung ohne Wirkung: Ein Reserve-Kandidat mit R5-Fund blieb Nacht für
    Nacht unreif, bis die Quarantäne ihn ausmusterte (Vorrat unter Ziel).

    Wirklich heilbar ist genau der Abbruch, bei dem NICHTS verloren ist:
      * hängendes Satzzeichen / offener Konnektor am Ende („… Kosten &“),
      * ein angehängtes Funktionswort ohne Fortsetzung („… Tarife für“).
    Beides wird abgeschnitten – aber nur, wenn der Rest ein vollständiger,
    aussagekräftiger Titel bleibt (≥ REST_MIN Zeichen, ≥ 3 Wörter, R5-frei).
    Fehlt echter Text (mitten im Wort abgebrochen), bleibt der Titel wie er
    ist: Der Fund gehört dann einem Menschen, nicht der Maschine.
    """
    t = (title or "").strip()
    if not r5_truncation(t):
        return t
    for _ in range(4):  # höchstens vier hängende Teile abräumen
        rest = re.sub(r"[\s" + re.escape(R5_HAENGENDE_ZEICHEN) + r"]+$", "", t)
        rest = re.sub(r"(\.\.\.|…)+$", "", rest).rstrip()
        if rest == t:
            words = t.split()
            if len(words) < 2:
                return title.strip()
            letzt = re.sub(r"[^\wäöüß]+$", "", words[-1]).lower()
            if letzt in R5_SCHLUSS_TABU:
                rest = " ".join(words[:-1]).rstrip()
            else:
                return title.strip()   # echter Textverlust – nicht raten
        t = rest
        if not t or len(t) < REST_MIN or len(t.split()) < 3:
            return title.strip()
        if not r5_truncation(t):
            return t
    return title.strip()


def fix_title(title):
    """Deterministische Korrekturen R1–R5 (R5 nur die heilbaren Klassen).

    R1 (Doppelpunkt-Konvention) wird über pinterest_seo_healer.ensure_colon_title
    geheilt, falls importierbar – sonst bleiben R2–R4.
    """
    t = heal_r5(title.strip())
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


def run_selftest():
    """Sabotage-Schutz: friert die R5-Wahrheitsprobe als Vertrag ein.

    Der Selbsttest ist schreibfrei und uhr-unabhängig (Vorgabe des
    selftest_runner: eine Wache, die beim Prüfen heilt oder am Kalender
    hängt, ist keine Wache).
    """
    fehler = []

    # 1. ECHTE Abbrüche müssen weiterhin auffallen (historische Funde).
    abgebrochen = [
        "Unfallversicherung Vergleich 2026: Sinnvoll? Kosten &",  # 26.09.2026
        "Gastarife im Herbst: Anbieter vergleichen –",
        "Stromkosten senken: Der beste Tarif für",
        "Haushaltskasse: Diese Posten und was sie",
        "Wechselbonus sichern: Das Angebot der",
        "Depot-Vergleich: Die wichtigsten Kosten im",
        "Sparplan starten: Schritt eins ist das Wichtigste …",
        "Tagesgeld-Vergleich: Zinsen, Laufzeit, Bonus, ",
    ]
    for titel in abgebrochen:
        if not any(r == "R5" for r, _ in check_title(titel)):
            fehler.append(f"R5 übersieht den Abbruch: {titel!r}")

    # 2. VOLLSTÄNDIGE Titel dürfen nie blockiert werden. Die ersten drei
    #    Zeilen sind die realen Falsch-Positive aus Issue #387 (sie haben
    #    den Vorrat unter das Ziel gerissen), der Rest ist der Regressions-
    #    Korpus der früheren Erlaubnisliste.
    vollstaendig = [
        "Stromfresser finden: So senkst du deine Stromrechnung massiv",
        "Die 50-30-20-Regel einfach erklärt",
        "Tierkrankenversicherung für Hund & Katze: Kosten realistisch",
        "Gasrechnung senken: So bereitest du dich im Spätsommer vor",
        "Standby beenden: So schaltest du heimliche Verbraucher ab",
        "Haushaltsbuch führen: So fängst du diese Woche an",
        "Notgroschen aufbauen: Wie viel reicht wirklich?",
        "Tagesgeld 2026: Bis zu 3,5 % Zinsen sichern",
        "Frugalismus im Alltag: Sparen, ohne zu verzichten.",
        "Kfz-Versicherung wechseln: Der Stichtag ist der 30. November",
    ]
    for titel in vollstaendig:
        funde = [m for r, m in check_title(titel) if r == "R5"]
        if funde:
            fehler.append(f"R5 blockiert einen vollständigen Titel "
                          f"({titel!r}): {funde[0]}")

    # 3. Die historische Erlaubnisliste bleibt gültig – und darf dem Tabu
    #    nicht widersprechen (eine Liste, die beides behauptet, entscheidet
    #    zufällig).
    doppelt = sorted(R5_END_WHITELIST & R5_SCHLUSS_TABU)
    if doppelt:
        fehler.append(f"Wort steht in Erlaubnis UND Tabu: {doppelt[:5]}")
    doppelt2 = sorted(R5_VERBZUSATZ & R5_SCHLUSS_TABU)
    if doppelt2:
        fehler.append(f"Verbzusatz steht zugleich im Tabu: {doppelt2[:5]}")
    for wort in sorted(R5_END_WHITELIST):
        if r5_truncation(f"Sparen im Alltag: So geht es {wort}"):
            fehler.append(f"früher erlaubtes Endwort wird jetzt blockiert: {wort!r}")
            break

    # 4. HEILUNG: der heilbare Abbruch wird deterministisch geschlossen,
    #    der Textverlust-Fall bleibt unangetastet (kein Raten).
    geheilt = fix_title("Unfallversicherung Vergleich 2026: Sinnvoll? Kosten &")
    if geheilt != "Unfallversicherung Vergleich 2026: Sinnvoll? Kosten":
        fehler.append(f"Hängender Konnektor nicht geheilt: {geheilt!r}")
    if r5_truncation(geheilt):
        fehler.append(f"Heilung liefert erneut einen R5-Fund: {geheilt!r}")
    if fix_title(geheilt) != geheilt:
        fehler.append("Heilung ist nicht idempotent")
    mehrstufig = fix_title("Haushaltskasse: Diese Posten und was sie")
    if mehrstufig != "Haushaltskasse: Diese Posten":
        fehler.append(f"Mehrstufige Heilung falsch: {mehrstufig!r}")
    verlust = "Der Tarif für"   # Rest wäre zu kurz -> nichts raten
    if fix_title(verlust) != verlust:
        fehler.append("Textverlust-Fall wurde geraten statt gemeldet: "
                      f"{fix_title(verlust)!r}")
    unberuehrt = "Die 50-30-20-Regel einfach erklärt"
    if fix_title(unberuehrt) != unberuehrt:
        fehler.append(f"Gesunder Titel wurde verändert: {fix_title(unberuehrt)!r}")

    # 5. R1–R4 bleiben unverändert scharf (Regression der Altregeln).
    if not any(r == "R1" for r, _ in
               check_title("Ein sehr langer Titel ganz ohne Doppelpunkt der "
                           "über fünfundvierzig Zeichen hat")):
        fehler.append("R1 (Doppelpunkt-Konvention) feuert nicht mehr")
    if not any(r == "R2" for r, _ in check_title("Riester Rente im Check")):
        fehler.append("R2 (Komposita) feuert nicht mehr")
    if not any(r == "R3" for r, _ in
               check_title("Weiterfördern oder kündigen dieses Jahr")):
        fehler.append("R3 (Zeit-Anhängsel) feuert nicht mehr")
    if not any(r == "R4" for r, _ in check_title("Strom  sparen: Der Check")):
        fehler.append("R4 (doppelte Leerzeichen) feuert nicht mehr")

    if fehler:
        print("🛑 CHECK-TITLES-SELBSTTEST FEHLGESCHLAGEN:")
        for f in fehler:
            print(f"   - {f}")
        return 2
    print(f"✅ Titel-Selbsttest grün: {len(abgebrochen)} echte Abbrüche erkannt, "
          f"{len(vollstaendig)} vollständige Titel durchgelassen, "
          f"Heilung deterministisch + idempotent, R1–R4 scharf.")
    return 0


def main():
    if "--selftest" in sys.argv:
        return run_selftest()
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
