#!/usr/bin/env python3
"""Template-Bausteine der Content-Automatisierung – SSOT für den Uniqueness-Vergleich.

WARUM DIESE DATEI (Issue #251, 11.09.2026):
============================================
Die Fazit-Schmiede (scripts/fazit_schmiede.py) erzeugt deterministische
Fazit- und FAQ-Blöcke für jeden Artikel, dem sie fehlen. Diese Blöcke sind
per Konstruktion nahezu wortgleich:

    ## Fazit: <Titel>
    "Der Hebel bei **X** sitzt nicht im Verzicht, sondern im
     Nachrechnen." <route-satz>
    "Prüfe einmal deine aktuellen Konditionen, halte den Unterschied
     schriftlich fest und wiederhole den Check jährlich …"

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


# ------------------------------------------------------------------
# NAVIGATION ≠ FLIESSTEXT (Issue #490, 01.10.2026)
# ------------------------------------------------------------------
# `scripts/internal_linker.py` setzt interne Verweise automatisch, und der
# Ankertext IST per Konstruktion der TITEL des Zielartikels:
#
#     [So findest du den richtigen DSL-Tarif für dein Zuhause](../../posts/…/)
#
# Verlinken zwei Ratgeber denselben Pillar-Artikel – genau das ist der Zweck
# interner Verlinkung –, teilen sie dadurch bis zu acht 7-Wort-Phrasen, OHNE
# dass ein einziger Satz Fließtext doppelt wäre. Im Einzigartigkeits-Audit vom
# 01.10.2026 war das die Ursache von 3 der 10 „kritischen" Funde: Die Wache
# bestrafte korrekte interne Verlinkung als Duplicate Content – und die
# „Heilung" wäre gewesen, Ankertexte zu verstümmeln oder Links zu löschen.
#
# Deshalb: Ankertexte INTERNER Links zählen nicht als Fließtext. Externe
# Linktexte bleiben erhalten (sie sind redaktionelle Formulierung, und zwei
# Artikel mit identischem Satz um einen Quellenlink herum sind ein echter
# Befund). Entfernt wird nur der Markdown-Link, nicht der Satz drumherum.
INTERNAL_LINK_RE = re.compile(
    r"\[[^\]]*\]\(\s*(?:\.{1,2}/|/)(?![/])[^)\s]*\)"
)


def strip_internal_link_anchors(text: str) -> str:
    """Entfernt interne Markdown-Links samt Ankertext (Navigation, kein Text).

    Intern = relatives Ziel (`../../posts/…`, `./…`) oder wurzel-relativ
    (`/posts/…`, `/pillar/…`, `/go/…`). Extern (`https://…`, `mailto:`) und
    Anker-Sprünge im selben Dokument (`#faq`) bleiben unangetastet.
    """
    return INTERNAL_LINK_RE.sub(" ", text)


# ------------------------------------------------------------------
#  NAVIGATIONS-BLOCK ≠ ABSATZ (Dauerheilung #824, 24.10.2026)
# ------------------------------------------------------------------
#  Am 24.10.2026 stand die Release-Scorecard für 25 von 62 Live-Artikeln
#  auf „blockiert“ – ausschließlich in der Dimension „Redundanz“. Die
#  Ursache war kein Duplicate Content, sondern die Toolbox am Artikelende:
#
#      - **Rechner:** [24-Monats-Effektivpreis-Rechner: Was der Tarif
#        wirklich kostet](../../werkzeuge/effektivpreis-rechner/)
#
#  Der Ankertext IST der Titel der Zielseite. Zwei Ratgeber, die denselben
#  Rechner verlinken – der Zweck eines Rechner-Hubs –, tragen dadurch
#  zwangsläufig denselben Satz. `check_uniqueness.py` nimmt solche Anker
#  seit #490 von der Messung aus (`strip_internal_link_anchors`),
#  `duplikat_guard` maß sie weiter: ZWEI Messungen, zwei Wahrheiten – genau
#  die Bauart, die #676, #714 und #766 nacheinander geheilt haben.
#
#  Deshalb ist die Ausnahme hier definiert – EINMAL, für beide Wachen:
#  Ein Block ist Navigation, wenn er (a) mindestens einen internen Link
#  trägt, (b) keinen externen Link enthält (der wäre redaktionelle
#  Formulierung) und (c) nach dem Entfernen aller internen Links höchstens
#  `NAVIGATION_REST_MAX_WOERTER` Wörter übrig lässt (Feldetikett wie
#  „Rechner:“/„Lesetipp:“). Ein einziger eigener Satz hebt die Ausnahme
#  auf – gemessen wird dann wieder alles (Freibrief-Schutz).
NAVIGATION_REST_MAX_WOERTER = 3

# Externe Ziele machen aus einem Link-Block redaktionellen Text. `mailto:`
# und `tel:` zählen mit: eine Kontaktzeile ist Inhalt, keine Navigation.
EXTERNAL_LINK_RE = re.compile(r"(?:https?://|www\.|mailto:|tel:)", re.I)


def navigation_rest(text: str) -> str:
    """Was von einem Block übrig bleibt, wenn alle internen Links weg sind."""
    return strip_internal_link_anchors(text or "")


def ist_nur_navigation(text: str) -> bool:
    """True, wenn der Block ausschließlich interne Verweise trägt.

    Bewusst streng (kein Inhalts-Freibrief): ohne internen Link keine
    Ausnahme, mit externem Link keine Ausnahme, und sobald mehr als
    `NAVIGATION_REST_MAX_WOERTER` Wörter Prosa übrig bleiben, wird der
    Block wieder voll gemessen.
    """
    text = text or ""
    if not INTERNAL_LINK_RE.search(text):
        return False
    if EXTERNAL_LINK_RE.search(INTERNAL_LINK_RE.sub(" ", text)):
        return False
    rest = navigation_rest(text)
    # Markdown-Schmuck, Aufzählungs- und Aufgaben-Marker sind keine Wörter.
    rest = re.sub(r"^\s*(?:[-*+]\s+|\[[ xX]\]\s*)", " ", rest, flags=re.M)
    rest = re.sub(r"[*_`>#|]+", " ", rest)
    worte = re.findall(r"[A-Za-zÄÖÜäöüß0-9]+", rest)
    return len(worte) <= NAVIGATION_REST_MAX_WOERTER


# ------------------------------------------------------------------
# HAUS-FORMELN: FORMAT ≠ INHALT (Issue #766, 15.10.2026)
# ------------------------------------------------------------------
# Der News-Desk schreibt in JEDEN News-Kompakt-Artikel dieselbe Dateline
# (`news_writer.STAND_INTRO` – nur das Datum wechselt). `duplikat_guard`
# kennt diese Formel seit #676 und nimmt sie dort von der Absatz-Duplikat-
# messung aus – das Einzigartigkeits-Audit maß sie weiter als Inhalt und
# meldete am 15.10.2026 sieben Paare „gleicher Text“ zwischen vier News-
# Entwürfen, die außer der Dateline nichts teilen (17 gleiche 7-Wort-Phrasen
# pro Paar). Das ist dieselbe Bauart, die #714 geheilt hat: ZWEI Messungen,
# zwei Wahrheiten – die strengere gewinnt nicht, sie fällt später auf.
#
# Deshalb liest diese Datei (SSOT für den Uniqueness-Vergleich) dieselben
# Haus-Formeln aus derselben Quelle wie `duplikat_guard` (AST-Zugriff auf die
# Modulkonstanten, kein Import der Produzenten: die ziehen PyYAML nach).
#
# FREIBRIEF-SCHUTZ – die Ausnahme ist absichtlich eng:
#   · Entfernt wird nur ein LITERALER Satz der Formel ab
#     `HAUS_FORMEL_MIN_LAENGE` Zeichen. Kurze Fragmente („Stand:“) bleiben
#     stehen – sonst wäre jedes Datum eine Lizenz.
#   · Ein Platzhalter der Formel (`{today}`) wird NICHT zu „beliebigem Text“:
#     Die Formel wird an ihren Platzhaltern geteilt, jeder Teil muss als
#     eigener Satz wieder auftauchen.
#   · Zwischen den Wörtern ist nur TYPOGRAFIE frei (Leerzeichen, geschützte
#     Leerzeichen, Binde-/Gedankenstriche, Satzzeichen). Eingeschobene eigene
#     Wörter heben die Ausnahme auf – der Satz wird dann wieder gemessen.
#   · Alles, was der Artikel SELBST um die Formel herum schreibt, bleibt im
#     Vergleich (Gegenprobe im Selbsttest).
HAUS_FORMEL_MIN_LAENGE = 40


def _formel_laeufe(wert: str) -> list:
    """Literale Sätze einer Haus-Formel (Platzhalter getrennt, Markdown weg)."""
    laeufe = []
    for teil in re.split(r"\{[^{}]*\}", wert or ""):
        teil = re.sub(r"[*_`>#]+", " ", teil)
        for satz in re.split(r"(?<=[.!?])\s+", teil):
            satz = satz.strip(" \t\r\n·:;,–—-")
            if len(satz) >= HAUS_FORMEL_MIN_LAENGE:
                laeufe.append(satz)
    return laeufe


def haus_formel_saetze() -> list:
    """Registrierte Haus-Formeln als Literalsätze: [(quelle, satz), …]."""
    import duplikat_guard as dg  # noqa: PLC0415 – stdlib-only, kein Zyklus
    saetze = []
    for modul, attribut in dg.HAUS_TEXT_QUELLEN:
        wert, _luecke = dg.ssot_konstante(modul, attribut)
        if not isinstance(wert, str):
            continue
        for satz in _formel_laeufe(wert):
            saetze.append((f"{modul}.{attribut}", satz))
    return saetze


def haus_formel_luecken() -> list:
    """Nicht lesbare/auswertbare Haus-Formeln – eine blinde Ausnahme.

    Wird als Befund geführt (und im Selbsttest des Audits als Werkzeugfehler
    gewertet): Eine Ausnahme, die ins Leere greift, lässt die Messung strenger
    werden – und niemand wüsste, warum die Formel plötzlich „doppelt“ ist.
    """
    import duplikat_guard as dg  # noqa: PLC0415
    luecken = []
    for modul, attribut in dg.HAUS_TEXT_QUELLEN:
        _wert, luecke = dg.ssot_konstante(modul, attribut)
        if luecke:
            luecken.append(f"{modul}.{attribut}: {luecke}")
    # Eine zu KURZE Formel (z. B. das CTA-Fragment „Jetzt vergleichen und
    # sparen:“) ist keine Lücke, sondern Absicht – sie ist unter der
    # Mindestlänge und wird bewusst nicht entfernt. Wird dagegen GAR KEINE
    # Formel mehr auswertbar, ist die Ausnahme blind und das ist ein Befund.
    if not haus_formel_saetze():
        luecken.append("keine einzige Haus-Formel auswertbar – die Ausnahme "
                       "wäre blind (Messung ohne Ansage strenger)")
    return luecken


def _haus_formel_muster(satz: str):
    """Tolerantes Muster EINES Formelsatzes (Wortfolge fest, Typografie frei)."""
    worte = re.findall(r"\w+", satz, re.UNICODE)
    return re.compile(r"(?<!\w)" + r"[^\w\n]{0,4}".join(re.escape(w) for w in worte)
                      + r"(?!\w)[.!]?")


_HAUS_FORMEL_MUSTER = None


def haus_formel_muster() -> list:
    """[(quelle, kompiliertes Muster)] – einmal gebaut, dann gecacht."""
    global _HAUS_FORMEL_MUSTER
    if _HAUS_FORMEL_MUSTER is None:
        _HAUS_FORMEL_MUSTER = [(quelle, _haus_formel_muster(satz))
                               for quelle, satz in haus_formel_saetze()]
    return _HAUS_FORMEL_MUSTER


def strip_house_formulas(text: str) -> str:
    """Entfernt registrierte Haus-Formel-Sätze (Format, kein Inhalt)."""
    for _quelle, muster in haus_formel_muster():
        text = muster.sub(" ", text)
    return text


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
    """Alle Schablonen-Klassen entfernen: Fazit/FAQ, Marketing, Haus-Formeln."""
    text = strip_generated_conclusions(text)
    text = strip_marketing_boilerplate(text)
    return strip_house_formulas(text)


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

    # Fall 5 (Issue #490): interne Link-Ankertexte sind Navigation. Zwei
    # Artikel, die denselben Ratgeber verlinken, teilen sonst dessen Titel als
    # „Duplikat“ – die Wache bestrafte damit korrekte interne Verlinkung.
    doc4 = ("Satz davor. Mehr dazu: "
            "[So findest du den richtigen DSL-Tarif für dein Zuhause]"
            "(../../posts/2026-08-20-so-findest-du-den-richtigen-dsl-tarif/). "
            "Satz danach.")
    stripped4 = strip_internal_link_anchors(doc4)
    if "richtigen DSL-Tarif" in stripped4:
        fehler.append("Fall 5: interner Link-Ankertext wurde nicht entfernt")
    if "Satz davor" not in stripped4 or "Satz danach" not in stripped4:
        fehler.append("Fall 5: Fließtext um den internen Link wurde mitentfernt")

    # Fall 6: wurzel-relative interne Ziele (/posts/, /pillar/, /go/) zählen
    # ebenfalls als Navigation – protokoll-relative (//cdn…) nicht.
    if "Girokonto ohne Gebühren" in strip_internal_link_anchors(
            "[Girokonto ohne Gebühren](/posts/konto/)"):
        fehler.append("Fall 6: wurzel-relativer interner Link blieb stehen")

    # Fall 7 (Gegenprobe): EXTERNE Linktexte sind redaktionelle Formulierung
    # und bleiben im Vergleich – sonst verschwände echte Dopplung rund um
    # Quellenangaben aus der Messung.
    extern = strip_internal_link_anchors(
        "Laut [Bundesnetzagentur](https://www.bundesnetzagentur.de/) gilt das.")
    if "Bundesnetzagentur]" not in extern:
        fehler.append("Fall 7: externer Linktext wurde fälschlich entfernt")

    # Fall 8: Idempotenz – ein zweiter Lauf ändert nichts mehr.
    if strip_internal_link_anchors(stripped4) != stripped4:
        fehler.append("Fall 8: strip_internal_link_anchors ist nicht idempotent")

    # --- Haus-Formeln (Issue #766, 15.10.2026) ---------------------------
    # Fall 9: Die registrierte News-Dateline fällt weg, der eigene Satz des
    # Artikels bleibt – sonst würde eine Formatzeile als Inhalt gemessen.
    dateline = ("**Stand: 06.10.2026.** Dieser News-Kompakt-Artikel ordnet "
                "eine aktuelle Entwicklung ein. Konditionen und Regeln können "
                "sich ändern – prüfe Details immer beim jeweiligen Anbieter.\n"
                "Der eigene Satz dieses Artikels bleibt stehen.")
    ohne_dateline = strip_house_formulas(dateline)
    if "Kompakt-Artikel" in ohne_dateline or "jeweiligen Anbieter" in ohne_dateline:
        fehler.append("Fall 9: News-Dateline (Haus-Formel) wurde nicht entfernt")
    if "eigene Satz dieses Artikels" not in ohne_dateline:
        fehler.append("Fall 9: eigener Satz um die Haus-Formel wurde mitentfernt")

    # Fall 10 (Freibrief-Schutz): Ein Satz, der nur ÄHNLICH klingt – hier mit
    # eingeschobenem eigenen Wort – ist NICHT die Haus-Formel und bleibt
    # gemessen. Sonst wäre „ordnet eine kurze aktuelle Entwicklung ein“
    # eine Lizenz für beliebigen Text.
    aehnlich = ("Dieser News-Kompakt-Artikel ordnet eine kurze aktuelle "
                "Entwicklung ein. Konditionen und Regeln können sich ändern – "
                "prüfe Details immer beim jeweiligen Anbieter.")
    if "kurze aktuelle" not in strip_house_formulas(aehnlich):
        fehler.append("Fall 10: Sätze, die der Haus-Formel nur ähneln, "
                      "werden fälschlich entfernt (Freibrief)")

    # Fall 11: Ein Zusatzsatz, den ZWEI Artikel teilen, bleibt gemessen –
    # nur die Formel selbst ist Format. (Sonst verschwände echte Dopplung,
    # die direkt an der Dateline klebt.)
    zusatz = ("**Stand: 01.10.2026.** Dieser News-Kompakt-Artikel ordnet eine "
              "aktuelle Entwicklung ein. Konditionen und Regeln können sich "
              "ändern – prüfe Details immer beim jeweiligen Anbieter. "
              "Belegbare Zahlen stammen aus den amtlichen Daten.")
    if "Belegbare Zahlen" not in strip_house_formulas(zusatz):
        fehler.append("Fall 11: eigener Zusatzsatz an der Dateline wurde "
                      "mitentfernt")

    # Fall 12: Die Formel-Quelle ist lesbar (eine blinde Ausnahme wäre eine
    # strengere Messung ohne Ansage) und die Entfernung ist idempotent.
    if haus_formel_luecken():
        fehler.append(f"Fall 12: Haus-Formel-Quelle nicht lesbar: "
                      f"{haus_formel_luecken()}")
    if strip_house_formulas(ohne_dateline) != ohne_dateline:
        fehler.append("Fall 12: strip_house_formulas ist nicht idempotent")

    # --- Navigations-Blöcke (Issue #824, 24.10.2026) ---------------------
    # Fall 13: Der Rechner-Link-Block ist Navigation – sein Ankertext IST der
    # Titel der Zielseite (#490). Er darf nicht als Fließtext-Absatz gelten.
    rechner_block = ("- **Rechner:** [24-Monats-Effektivpreis-Rechner: Was "
                     "der Tarif wirklich kostet](../../werkzeuge/"
                     "effektivpreis-rechner/)")
    if not ist_nur_navigation(rechner_block):
        fehler.append("Fall 13: Rechner-Link-Block wurde nicht als Navigation "
                      "erkannt – zwei Artikel mit demselben Werkzeug teilen "
                      "sonst zwangsläufig denselben Absatz (#824)")
    # Fall 14 (Freibrief-Schutz): Derselbe Link IN einem Redaktionssatz ist
    # Inhalt und bleibt messbar – sonst verschwände beliebiger Text hinter
    # einem Link.
    redaktionell = ("- **Rechner:** [Effektivpreis](../../werkzeuge/"
                    "effektivpreis-rechner/) hilft dir nur, wenn du die "
                    "Grundgebühr über die volle Laufzeit mitrechnest.")
    if ist_nur_navigation(redaktionell):
        fehler.append("Fall 14: Redaktionssatz mit internem Link wurde als "
                      "Navigation ausgenommen (Freibrief)")
    # Fall 15: Externe Ziele sind redaktionelle Formulierung – keine
    # Navigation, auch wenn der Block nur aus einem Link besteht.
    extern_block = ("[Bundesnetzagentur – Breitbandmessung]"
                    "(https://www.bundesnetzagentur.de/DE/Fachthemen/start.html)")
    if ist_nur_navigation(extern_block):
        fehler.append("Fall 15: externer Quellenlink wurde als Navigation "
                      "ausgenommen")
    # Fall 16: Ohne internen Link gibt es keine Ausnahme (leerer Text,
    # Bildzeile, Fließtext).
    for harmlos in ("", "*Abbildung: Merkkarte mit den Kernaussagen.*",
                    "Der Notgroschen ist kein Sparziel, sondern ein Puffer."):
        if ist_nur_navigation(harmlos):
            fehler.append(f"Fall 16: harmloser Block als Navigation "
                          f"ausgenommen: {harmlos[:40]!r}")
    # Fall 17: Idempotenz – das Entfernen der Verweise ändert beim zweiten
    # Lauf nichts mehr (sonst wäre die Messung nicht reproduzierbar).
    einmal = navigation_rest(rechner_block)
    if navigation_rest(einmal) != einmal:
        fehler.append("Fall 17: navigation_rest ist nicht idempotent")

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
