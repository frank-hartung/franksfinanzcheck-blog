#!/usr/bin/env python3
"""Template-Bausteine der Content-Automatisierung – SSOT für den Uniqueness-Vergleich.

WARUM DIESE DATEI (Issue #251, 11.09.2026):
============================================
Die Fazit-Schmiede (scripts/fazit_schmiede.py) erzeugt deterministische
Fazit- und FAQ-Blöcke für jeden Artikel, dem sie fehlen. Diese Blöcke sind
per Konstruktion nahezu wortgleich:

    ## Fazit: <Titel>
    "Sich gezielt mit dem Thema **X** zu beschäftigen, ist einer der
     einfachsten Hebel, um deine Finanzen selbst in die Hand zu nehmen
     und bares Geld zu sparen." <route-satz>
    "Fang am besten heute an, vergleiche die Angebote und sichere dir
     deine Ersparnis! 💸🚀"

    ## Häufige Fragen
    ### <Frage aus FAQ_POOL>
    <Antwort aus FAQ_POOL>

`check_uniqueness.py` und `quality_score.py` strippten diese Bausteine NICHT –
jeder so veredelte Artikel „kollidierte“ deshalb über die Template-Sätze mit
10+ UNVERWANDTEN Artikeln (Hebel-Satz + Vergleichs-CTA ergeben allein 22
geteilte 7-Gramm). Ergebnis: uniqueness = 0.0 → Massen-Parking → Tagesdefizit
→ Content-Engine rot → Bot-Watchdog #251.

PRINZIP (dokumentiert seit Reserve #4, 09.09.2026):
    Der Uniqueness-Score misst ECHTE Text-Dopplung, nicht Template-Repetition.
    Deshalb werden die deterministisch erzeugten Fazit-/FAQ-Blöcke hier ZENTRAL
    entfernt – für check_uniqueness.py UND quality_score.py aus einer Quelle,
    damit die Schablonenlisten nie wieder auseinanderlaufen.

Ein manuell verfasstes Fazit/FAQ ist im Zweifel einzigartig und erzeugt ohnehin
keine Überlappung – das Entfernen ganzer Fazit-/FAQ-Abschnitte ist deshalb
verlustfrei für die Duplikat-Erkennung des Fließtexts.
"""
import re

# Die Fazit-Schmiede erzeugt "## Fazit: <Titel>" + S1/S2/S3-Satzblock und
# "## Häufige Fragen" + FAQ_POOL. Beide Blöcke sind Template, kein Fließtext.
FAZIT_SECTION_RE = re.compile(
    r"(?m)^[ \t]*##\s+Fazit\b.*?(?=^[ \t]*##\s|\Z)", re.S)
FAQ_SECTION_RE = re.compile(
    r"(?m)^[ \t]*##\s+(?:Häufige Fragen|Häufig gestellte Fragen|FAQ)\b"
    r".*?(?=^[ \t]*##\s|\Z)", re.S)

# Marketing-/Affiliate-Bausteine, die jeder Artikel trägt (Werbekennzeichnung,
# Schnell-/Spar-Tipp, Conversion-CTA, „Das Wichtigste“-Hakenlistung, Hinweis-
# Klauseln). Entfernt wird die GANZE Zeile, die einen Baustein trägt – so wie
# es quality_score seit Reserve #4 (09.09.2026) macht. Damit check_uniqueness
# und quality_score dieselbe Schablonen-Liste nutzen (keine Drift mehr, #251).
# Hinweis: Die KI setzt in „Schnell-Tipp“/„Spar-Tipp“ teils den geschützten
# Bindestrich U+2011 „‑“ statt des ASCII-Hyphens – die Klasse [-‑\u2010]
# erlaubt beide (Befund Reserve #4, 09.09.2026).
MARKETING_PATTERNS = (
    r"💡[^\n]*Schnell[-‑\u2010]?Tipp[^\n]*",
    r"Spar[-‑\u2010]?Tipp zwischendurch",
    r"Wichtiger Hinweis",
    r"Lesetipps zum Weitersparen",
    r"Das Wichtigste in Kurzform",
    r"Das Wichtigste in Kürze",
    r"👉[^\n]*",
    # Affiliate-Disclosure in ALLEN Varianten & Groß-/Kleinschreibung
    # (inkl. kleingeschriebenem „dieser Artikel“, „Transparenz:“-Vorspann).
    r"affiliate[^\n]*?(werbung|provision)[^\n]*",
)


def strip_generated_conclusions(text: str) -> str:
    """Entfernt die deterministischen Fazit-/FAQ-Blöcke der Fazit-Schmiede.

    Rückgabe: Text, in dem der Abschnitt von „## Fazit“ bis zur nächsten
    H2-Überschrift sowie der Abschnitt „## Häufige Fragen“ bis zum nächsten
    H2/Dokumentende durch Leerraum ersetzt ist. Nur echter Fließtext bleibt.
    """
    text = FAZIT_SECTION_RE.sub(" ", text)
    text = FAQ_SECTION_RE.sub(" ", text)
    return text


def strip_marketing_boilerplate(text: str) -> str:
    """Entfernt Marketing-/Affiliate-Baustein-Zeilen (ganze Zeile je Treffer)."""
    for pattern in MARKETING_PATTERNS:
        text = re.sub(r"(?im)^[^\n]*" + pattern + r"[^\n]*$\n?", " ", text)
    return text


def strip_template_boilerplate(text: str) -> str:
    """Beide Schablonen-Klassen entfernen: Fazit/FAQ + Marketing/Affiliate."""
    return strip_marketing_boilerplate(strip_generated_conclusions(text))


def run_selftest() -> list:
    """Eingefrorene Fälle für die Sabotage-Abwehr (kein Schreiben)."""
    fehler = []

    # Fall 1: Fazit + FAQ werden vollständig entfernt, Fließtext davor bleibt.
    doc = (
        "Echter Fließtext davor mit genug Wörtern für den Vergleich.\n\n"
        "## Fazit: Testthema\n"
        "Sich gezielt mit dem Thema **Testthema** zu beschäftigen, ist einer "
        "der einfachsten Hebel, um deine Finanzen selbst in die Hand zu nehmen "
        "und bares Geld zu sparen. Fang am besten heute an, vergleiche die "
        "Angebote und sichere dir deine Ersparnis! 💸🚀\n\n"
        "## Häufige Fragen\n"
        "### Frage eins?\n"
        "Antwort eins.\n"
    )
    stripped = strip_generated_conclusions(doc)
    if "Hebel" in stripped or "Ersparnis" in stripped or "Frage eins" in stripped:
        fehler.append("Fall 1: Fazit-/FAQ-Bausteine wurden nicht entfernt")
    if "Echter Fließtext davor" not in stripped:
        fehler.append("Fall 1: echter Fließtext wurde mitentfernt")

    # Fall 2: manuelles Fazit ohne die Schablonen-Sätze wird trotzdem entfernt
    # (bewusst – verlustfrei für die Duplikat-Erkennung), der Rest bleibt.
    doc2 = "Fließtext vorher.\n\n## Fazit\nEin ganz individueller Schlusssatz.\n\nEnde."
    stripped2 = strip_generated_conclusions(doc2)
    if "individueller Schlusssatz" in stripped2:
        fehler.append("Fall 2: Fazit-Abschnitt wurde nicht entfernt")
    if "Fließtext vorher" not in stripped2:
        fehler.append("Fall 2: Fließtext vor dem Fazit fehlt")

    # Fall 3: Idempotenz – zweiter Lauf ändert nichts mehr.
    if strip_generated_conclusions(stripped) != stripped:
        fehler.append("Fall 3: strip_generated_conclusions ist nicht idempotent")

    # Fall 4: Marketing-Bausteine (Affiliate-Disclosure + Spar-Tipp) fallen weg,
    # echter Fließtext bleibt.
    doc3 = (
        "Echter Fließtext mit genug Wörtern für den Vergleich.\n"
        "**Transparenz:** dieser Artikel enthält Affiliate-Links (Werbung). "
        "Beim Abschluss über einen Link erhalten wir eine Provision – für dich "
        "entstehen keine Mehrkosten.\n"
        "> 💶 **Spar-Tipp zwischendurch:** faire Konditionen gibt es online in "
        "Minuten: [**Vergleichen & sparen**](/go/allgemein/)\n"
        "Noch ein echter Satz danach.\n"
    )
    stripped3 = strip_marketing_boilerplate(doc3)
    if "Affiliate-Links" in stripped3 or "Spar-Tipp" in stripped3:
        fehler.append("Fall 4: Marketing-/Affiliate-Bausteine wurden nicht entfernt")
    if "Echter Fließtext" not in stripped3 or "Noch ein echter Satz" not in stripped3:
        fehler.append("Fall 4: echter Fließtext wurde mitentfernt")

    return fehler


if __name__ == "__main__":
    import sys
    errs = run_selftest()
    if errs:
        print("🛑 TEMPLATE-BOILERPLATE-SELFTEST FEHLGESCHLAGEN:")
        for e in errs:
            print("  -", e)
        sys.exit(2)
    print("✅ Template-Boilerplate-Selftest bestanden (Fazit/FAQ-Strip, "
          "Fließtext-Schutz, Idempotenz).")
