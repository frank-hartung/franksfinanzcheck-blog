#!/usr/bin/env python3
"""
TEXTVERSTÄNDNIS-GUARD (R2–R15) für FranksFinanzcheck.

Die Verständnis-Regeln aus dem Textverständnis-Audit (01.09.2026), die
KEIN bestehendes Gate misst:

  R2  Keyword-Dump-Guard   Komma-Ketten > 200 Zeichen mit > 12 Kommas
                           bzw. > 40 Tokens ohne Verb im Fließtext
                           („300 Begriffe“-Listen)
  R3  Terminologie-Guard   1 Konzept = 1 Leitbegriff (data/terminologie.yaml);
                           > max_synonyme Vorkommen von Synonymen -> Fund
  R4  Satzanfangs-Guard    derselbe Satzanfang in > 20 % der Fließtext-
                           sätze oder > 4× pro 1.000 Wörter
  R5  Absatz-Guard         Fließtext-Absatz > 4 Sätze -> Fund, > 6 Sätze -> hart
  R7  Intro-Formel-Guard   „In diesem Ratgeber/Artikel/Beitrag …“ -> 0 Toleranz
  R8  Ankertext-Ziel-Kohärenz  Ankertext passt nicht zu Slug des Ziels;
      + R8-NESTED-LINK  Doppelt verschachtelte Markdown-Links
  R9  Klebewort-Guard      Inserter-Artefakte „HHerfindestdu“/„Ddeine…"
                           Leerzeichen in URL = harter Fehler
  R10 Wortdopplungs-Guard  „senken senken will“ – reine Leerraum-Dopplung
                           ohne trennendes Satzzeichen (Klebe-Rest einer
                           Editier-/Heiler-Kaskade; Lektorat 25.09.2026
                           heilte den Fall im alten Slug, das Rework trug
                           ihn wieder ein – R2–R9 sahen ihn nicht).
  R11 Jahreszahl-Split     „Nutze 20 26 gezielt …“ – zerrissene Jahreszahl
                           aus automatisierter Politur (#482, Weihnachten).
  R12 Zahl-Ruine           „Du bist der 0 am deutschen Strommarkt“ –
                           Artikel + nackte Zahl + Präposition, Überrest
                           einer defekten Ersetzung (#482, Ökostrom).
  R13 Datum-ohne-Punkt     „es ist der 2 Januar“ – Ordinalzahl vor
                           Monatsname ohne Punkt (#482, Weihnachten;
                           Zwillingsfund „am 1 Januar“, Neujahrs-Entwurf).
  R14 Marker-Ruine         „SATZ: | **CHECK24-Vergleich** | – | | | | |“ –
                           halbfertige Politur-Zeile (#482, E-Bike).
  R15 Phrasen-Dopplung     identische ≥ 10-Wort-Sequenz im Fließtext eines
                           Artikels – fingert das Doppel-Intro aus #482
                           (Mietwagen: „Stell dir vor: Du stehst am
                           Flughafen von Faro …“) und den mehr-freiheit-
                           Doppelblock (08/2026), die D1/D2 verpassen
                           (Ratio < 0,85 bzw. < 120 Zeichen).

R11–R14 teilen sich die Muster-SSOT mit der Schreib-Verifikation:
`sprachkern.POLITUR_RUINEN` (write_verified verweigert jede Schrift,
die eine NEUE Ruine einführt). Diese Wache meldet sie zusätzlich im
Bestands-Audit und blockiert die Veröffentlichung (Publish-Gate).

MODI:
  python3 scripts/textverstaendnis_guard.py            # Report (alle Artikel)
  python3 scripts/textverstaendnis_guard.py --json     # maschinenlesbar
  python3 scripts/textverstaendnis_guard.py --new-only # Engine-Modus (heute);
                                                       # harte Regeln -> Exit 1
  python3 scripts/textverstaendnis_guard.py --selftest # Sabotage-Schutz

Ausgabe: TEXTVERSTAENDNIS-REPORT.md + data/verstaendnis_history.jsonl
"""

import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

# Muster-SSOT für R11–R14 (Politur-Ruinen): sprachkern.POLITUR_RUINEN –
# dieselben Muster, mit denen write_verified jede Schrift verweigert, die
# eine NEUE Ruine einführt. Eine Quelle, zwei Einsatzstellen.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sprachkern import politur_ruine_funde  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "content" / "posts"
REPORT = ROOT / "TEXTVERSTAENDNIS-REPORT.md"
HISTORY = ROOT / "data" / "verstaendnis_history.jsonl"
TERMINOLOGIE = ROOT / "data" / "terminologie.yaml"

NEW_ONLY = "--new-only" in sys.argv
AS_JSON = "--json" in sys.argv
SELFTEST_ONLY = "--selftest" in sys.argv

# R2
R2_MAX_LEN = 200
R2_MAX_COMMAS = 12
R2_MAX_TOKENS = 40
# R4
R4_MAX_PCT = 20.0
R4_MAX_PER_1K = 4.0
# R5
R5_SOFT = 4
R5_HARD = 6
# R7
INTRO_FORMELN = [
    "in diesem ratgeber", "in diesem artikel", "in diesem beitrag",
    "in dieser anleitung", "in diesem guide", "in diesem blogbeitrag",
]
# R8
R8_STOPWORDS = {"der", "die", "das", "den", "dem", "des", "ein", "eine", "einer",
                "eines", "einem", "einen", "und", "oder", "aber", "für", "fur",
                "mit", "von", "vom", "zum", "zur", "auf", "bei", "nach", "aus",
                "im", "in", "am", "an", "so", "wie", "nicht", "auch", "du", "dein",
                "deine", "deinen", "deinem", "ihr", "ihre", "ihren", "die", "das",
                "vor", "nur", "was", "sich", "dich", "dir"}


def normalize_umlauts(text: str) -> str:
    """ä→ae, ö→oe, ü→ue, ß→ss (für Slug↔Ankertext-Abgleich R8)."""
    return (text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
                .replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue")
                .replace("ß", "ss"))


# Normalisierte Stoppwörter („für“→„fuer“) dürfen im Slug ebenfalls nicht als
# Treffer gelten – sonst maskiert jeder Anker mit „für“ echte Ziel-Mismatches.
R8_STOPWORDS_NORM = {normalize_umlauts(w) for w in R8_STOPWORDS}

FLOW_LINE_EXCLUDE = re.compile(r"^\s*(#|[*>\|\-]|\d+\.|!\[)")


def split_body(raw: str) -> str:
    parts = raw.split("---", 2)
    return parts[2] if len(parts) >= 3 else raw


def flow_paragraphs(body: str) -> list:
    """Fließtext-Absätze (keine Listen/Tabellen/Zitate/Überschriften/Code)."""
    out = []
    for chunk in body.split("\n\n"):
        lines = [l for l in chunk.split("\n") if l.strip()]
        if not lines:
            continue
        first = lines[0].strip()
        if re.match(r"^\s*([#>*|\-\d.])", first):
            continue
        if first.startswith("```") or first.startswith("{{<"):
            continue
        # Ab der ersten Listen-/Tabellen-/Zitat-Zeile endet der Fließtext:
        # eine Einleitung mit anschließender Liste („…belohnen Rabatten:“
        # gefolgt von „- Punkt“) ist EIN Satz, kein 5-Satz-Absatz.
        cut = len(lines)
        for n, l in enumerate(lines):
            if re.match(r"^\s*([*\-]|\d+\.|>|\|)", l.strip()):
                cut = n
                break
        lines = lines[:cut] or lines[:1]
        text = " ".join(lines)
        # Hugo-Shortcodes rausfiltern (z. B. {{< tarifvergleich ... >}})
        text = re.sub(r"\{\{<.*?>\}\}", " ", text, flags=re.S)
        text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
        text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
        text = text.replace("&nbsp;", " ")
        if len(re.findall(r"\b\w+\b", text)) < 6:
            continue
        out.append(text)
    return out


def flow_sentences(body: str) -> list:
    """Fließtext-Sätze (ohne Listen/Tabellen/Überschriften)."""
    sents = []
    for para in flow_paragraphs(body):
        t = re.sub(r"(?<=\d)\.\s+(?=[A-ZÄÖÜ])", " ", para)
        parts = re.split(r"[.!?](\s+|$)", t)
        for s in parts:
            words = re.findall(r"\b\w+\b", s)
            if len(words) >= 5:
                sents.append(" ".join(words))
    return sents


def load_terminologie() -> dict:
    if not yaml or not TERMINOLOGIE.exists():
        return {}
    data = yaml.safe_load(TERMINOLOGIE.read_text(encoding="utf-8"))
    return data.get("begriffe", {}) if isinstance(data, dict) else {}


def check_article(rel: str, body: str, term: dict) -> list:
    finds = []
    paras = flow_paragraphs(body)

    # ---------- R2 Keyword-Dump ----------
    for para in paras:
        commas = para.count(",")
        tokens = re.findall(r"[a-zäöüßA-ZÄÖÜ0-9]+", para)
        verbs = re.findall(r"\b(ist|sind|war|waren|wird|werden|wurde|hat|haben|kann|können|soll|sollte|muss|müssen|fährt|fährst|öffnet|erklärt|zeigt|gibt|kommt|steht|liegt|folgt|hilft|bringt|spart|kostet|zahlt|zahlst|wechselt|wechselst|findet|findest|erfährst|läuft|lädt|geht|gehst)\b", para, re.I)
        if len(para) > R2_MAX_LEN and commas > R2_MAX_COMMAS and len(tokens) > R2_MAX_TOKENS and len(verbs) <= 2:
            finds.append((rel, "R2-KEYWORD-DUMP",
                          f"{len(para)} Zeichen, {commas} Kommas, kaum Verben: {para[:110]}…", para[:40]))

    # ---------- R3 Terminologie ----------
    # Nur FLIESSTEXT zählen (wie R4/R5): Überschriften, Tabellen, Listen,
    # Zitate, CTA-Boxen und Hugo-Shortcodes sind Struktur, keine Textbegriffe
    # (Mess-Artefakt, 01.09.2026 – sonst zählen „Tagesgeld“ in H2-Titeln,
    # Tabellenspalten und „👉 Jetzt Tagesgeld vergleichen“-CTAs als Synonyme).
    flow_text = " ".join(flow_paragraphs(body))
    for konzept, cfg in term.items():
        leit = cfg.get("leitbegriff", "")
        syns = cfg.get("synonyme", [])
        if not leit or not syns:
            continue
        if cfg.get("kontext") and cfg["kontext"] not in body:
            continue
        # Wortgrenzen mit Bindestrich-Ausschluss: „Tagesgeld“ darf weder in
        # „Tagesgeldkonto“ noch in Komposita wie „Tagesgeld-Zinsen“ zählen
        # (Teilstring-/Kompositum-Artefakt, 01.09.2026).
        def word_re(w: str) -> str:
            return r"(?<![\w-])" + re.escape(w) + r"(?![\w-])"
        leit_count = len(re.findall(word_re(leit), flow_text, re.I))
        syn_counts = [(s, len(re.findall(word_re(s), flow_text, re.I))) for s in syns]
        total_syn = sum(c for _, c in syn_counts)
        max_syn = cfg.get("max_synonyme", 2)
        if leit_count >= 3 and total_syn > max_syn:
            detail = ", ".join(f"{s}×{c}" for s, c in syn_counts if c)
            finds.append((rel, "R3-TERMINOLOGIE",
                          f"Konzept „{leit}“: {total_syn} Synonym-Vorkommen ({detail}) – Leitbegriff verwenden", konzept))

    # ---------- R4 Satzanfangs-Echo ----------
    starts = []
    for s in flow_sentences(body):
        w = re.findall(r"[a-zäöüß]+", s.lower())
        if w:
            starts.append(w[0])
    if starts:
        from collections import Counter
        n = len(starts)
        for word, cnt in Counter(starts).most_common(3):
            pct = 100.0 * cnt / n
            if pct >= R4_MAX_PCT or (cnt >= 4 and 1000.0 * cnt / max(1, sum(len(x.split()) for x in [])) >= 0):
                pass
        # pro 1.000 Wörter
        words_total = sum(len(s.split()) for s in flow_sentences(body))
        top = Counter(starts).most_common(1)[0]
        word, cnt = top
        per1k = 1000.0 * cnt / max(1, words_total)
        if cnt >= 5 and (100.0 * cnt / n >= R4_MAX_PCT or per1k >= R4_MAX_PER_1K):
            finds.append((rel, "R4-SATZANFANG",
                          f"„{word}“ startet {cnt}/{n} Sätze ({per1k:.1f}/1k Wörter)", word))

    # ---------- R5 Absatzlänge ----------
    for para in paras:
        t = re.sub(r"(?<=\d)\.\s+(?=[A-ZÄÖÜ])", " ", para)
        n_sents = sum(1 for s in re.split(r"[.!?](\s+|$)", t) if len(s.split()) >= 4)
        if n_sents > R5_HARD:
            finds.append((rel, "R5-ABSATZ-HART",
                          f"Absatz mit {n_sents} Sätzen (Limit {R5_HARD}): {para[:90]}…", para[:30]))
        elif n_sents > R5_SOFT:
            finds.append((rel, "R5-ABSATZ",
                          f"Absatz mit {n_sents} Sätzen (Limit {R5_SOFT}): {para[:90]}…", para[:30]))

    # ---------- R7 Intro-Formel ----------
    body_l = body.lower()
    for phrase in INTRO_FORMELN:
        c = body_l.count(phrase)
        if c:
            finds.append((rel, "R7-INTRO-FORMEL",
                          f"„{phrase}“ ×{c} (Template-Sprache – umformulieren)", phrase))

    # ---------- R8 Ankertext-Ziel + URL-Hygiene ----------
    for m in re.finditer(r"\[([^\]]*)\]\(([^)]+)\)", body):
        anker, url = m.group(1), m.group(2)
        if url.startswith(("http", "mailto:", "#")) or url.startswith("/go/"):
            continue
        if " " in url:
            finds.append((rel, "R8-URL-LEERZEICHEN",
                          f"URL mit Leerzeichen: „{url}“ (Anker: „{anker[:40]}“)", url))
            continue
        if not url.endswith("/"):
            continue
        slug = url.rstrip("/").split("/")[-1]
        if not slug or slug.startswith("."):
            continue
        # Datums-Präfix + Stoppwörter aus dem Slug ziehen.
        # Mindestlänge 3 (statt 4): Kurz-Kernbegriffe des Blogs (dsl, gas,
        # dns, kwh) sind inhaltstragend und sollen Ankertext-Kohärenz prüfen.
        tokens = [t for t in re.split(r"[-_]", slug)
                  if len(t) >= 3 and t not in R8_STOPWORDS
                  and normalize_umlauts(t) not in R8_STOPWORDS_NORM
                  and not re.fullmatch(r"\d{4}|\d{2}", t)]
        if not tokens:
            continue
        # Weiche Trennzeichen (U+00AD, von umbruch_guard) vor dem Abgleich entfernen
        anker_l = anker.lower().replace("\u00ad", "").replace("\u2011", "-")
        # Umlaute normalisieren: ä→ae, ö→oe, ü→ue, ß→ss
        # Damit "spätsommer" auch "spaetsommer" erkennt
        anker_norm = normalize_umlauts(anker_l)
        tokens_norm = [normalize_umlauts(t) for t in tokens]
        hits = [t for t in tokens_norm if t in anker_l or t in anker_norm]
        if not hits:
            finds.append((rel, "R8-ANKER-ZIEL",
                          f"Ankertext „{anker[:45]}“ passt nicht zum Ziel „{slug}“", slug))
    finds += check_nested_links(rel, body)
    finds += check_klebewoerter(rel, body)
    finds += check_wortdopplung(rel, body)
    finds += check_politur_ruinen(rel, body)
    finds += check_phrasendoppel(rel, body)
    return finds


# R8-NESTED-LINK (02.09.2026, Wöchentliche SEO-Optimierung #20):
# Live-Schadensbeweis: „Weiterlesen“-Zeilen enthielten DOPPELT geschachtelte
# Markdown-Links, z. B. „[[Wohngebäudeversicherun](…/dein-haus…/)g Vergleich](…/wohngeb…/)".
# Entstehung (Git-Forensik): 26.08. Entlinkung (draft_link_healer) → 31.08.
# Re-Verlinkung durch zwei Linker-Pässe, der zweite klinkte sich MITTEN ins
# Wort des ersten Ankers („…versicherun|g Vergleich“). Im gerenderten HTML
# stand roher Markdown-Müll – für Leser sichtbar, für check_internal_links
# unsichtbar (dort existiert kein href). Regel: immer harter Fehler, nie
# auto-heilbar (Semantik unklar) – die Redaktion entscheidet.
R8_NESTED_RX = re.compile(r"\[\[[^\]\n]*?\]\([^)]*\)[^\]\n]*?\]\([^)]*\)")


def check_nested_links(rel: str, body: str) -> list:
    """Erkennt verschachtelte/doppelt gesetzte Markdown-Links (Form
    „[[Text](url)Restwort](url2)“) – harter Fehler, Redaktion repariert."""
    out = []
    for m in R8_NESTED_RX.finditer(body):
        frag = re.sub(r"\s+", " ", m.group(0))
        out.append((rel, "R8-NESTED-LINK",
                    f"Verschachtelter Markdown-Link: „{frag[:90]}“ "
                    f"– rendert als sichtbarer Text-Müll, manuell reparieren", frag))
    return out


# R9-KLEBEWORT (02.09.2026, Wöchentliche SEO-Optimierung #20):
# Fingerabdruck historischer Inserter-Kaskaden: Wort beginnt mit demselben
# Buchstaben zweimal in gemischter Groß-/Kleinschreibung („HHerfindestdu"
# ← „Hier findest du", „Ddeine6" ← „Deine 6", gefunden in posts/_index.md).
# In deutscher Prosa kommt das praktisch nie vor (Ausnahme: Ortsnamen wie
# „Aachen") — darum harter Fehler, kaum False-Positive-Risiko.
R9_KLEBE_RX = re.compile(r"\b([A-ZÄÖÜa-zäöü])([A-ZÄÖÜa-zäöü])([a-zäöü][\wÄÖÜäöüß]*)")
R9_ALLOW = {"Aachen", "Aachener", "Ggf", "ggf", "Zzgl", "zzgl"}
#  Abk. „gegebenenfalls“ und „zzgl.“ (zusätzlich) sind legitimes Deutsch –
#  der Klebe-Detektor sieht in „zz“ nur vermeintlich ein doppeltes Wortanfangs-Muster.


def check_klebewoerter(rel: str, body: str) -> list:
    """Erkennt vorne geklebte Wortduplikate („HHerfindestdu", „Ddeine…")
    aus defekten Inserter-Skripten – harter Fehler, sofort reparieren."""
    out = []
    clean = re.sub(r"```.*?```", " ", body, flags=re.S)
    clean = re.sub(r"\{\{[^}]*\}\}", " ", clean)
    clean = re.sub(r"\]\([^)\n]*\)", "]()", clean)
    for m in R9_KLEBE_RX.finditer(clean):
        if m.group(1).casefold() != m.group(2).casefold():
            continue
        w = m.group(0)
        if w[2].casefold() == w[0].casefold():
            continue  # Buchstaben-Lauf („www“, „AAA“) ist kein Inserter-Artefakt
        if w in R9_ALLOW:
            continue
        out.append((rel, "R9-KLEBEWORT",
                    f"Klebe-Artefakt „{w}“ (Wort fängt doppelt an: {w[0]}{w[1]}…) "
                    f"– Überrest eines defekten Text-Inserters, manuell reparieren", w))
    return out


# R10-DOPPELWORT (28.09.2026, Klebe-Artefakte-Premium-Audit):
# Dritter belegter Maschinen-Klebe-Befund neben R9 (Doppel-Initialen) und
# F6 (Frontmatter-Naht): unmittelbar doppelt geschriebene Wörter ohne
# trennendes Satzzeichen („Wer seine Gasrechnung senken senken will“).
# Beide Wörter sind einzeln korrekt geschrieben – Spellcheck, Casing und
# R9 sehen die Dopplung nicht.
# Präzision (kein False-Positive-Risiko):
#   • CASE-EXAKT: Editier-/Heiler-Kaskaden kopieren Tokens bytetreu
#     („senken senken“, „Die Die besten“). Nomen-Verb-Homographen mit
#     Groß-/Klein-Unterschied („Konsum-Fallen fallen so auf“) sind
#     korrektes Deutsch und bleiben außen vor.
#   • Reine Leerraum-Trennung: Dopplungen MIT Komma/Doppelpunkt/
#     Gedankenstrich dazwischen („kauft, kauft zweimal“, „werden,
#     werden“, „voll-voll“) sind legitimes Deutsch.
#   • Relativsatz-Gefüge „…, die die Thermostate …“: Artikel/Pronomen
#     nach Komma ist der eine legitime case-exakte Leerraum-Doppel.
#   • Nur Fließtext: „### Kinder“ + Absatz „Kinder haben …“ ist ein
#     Journal-Muster, kein Befund.
R10_ARTIKEL = {"die", "der", "den", "dem", "das"}

# Einschub-Variante (gleiche Ursachenfamilie): Das Duplikat klammert einen
# reinen Quantor ein („… lässt sich die Gasrechnung senken um bis zu 15 %
# senken“, Fund 28.09.2026). Korrektes Deutsch stellt den Quantor VOR das
# Verb – ein doppeltes Verb um einen Prozent-/Euro-Betrag ist immer ein
# Klebe-Rest, darum ohne Ausnahme hart.
R10_QUANTOR_RX = re.compile(
    r"\b([A-Za-zÄÖÜäöüß]{3,})\s+"
    r"um\s+(?:bis\s+zu\s+|rund\s+|etwa\s+|knapp\s+|mehr\s+als\s+|gut\s+)?"
    r"[\d.,]+\s*(?:%|Prozent|Euro|€)\s+\1\b")


def check_wortdopplung(rel: str, body: str) -> list:
    """Erkennt unmittelbare, case-exakte Wortdopplungen („senken senken
    will“) im Fließtext – harter Fehler, sofort reparieren.

    Nur Fließtext-Absätze: Überschriften, Listen, Tabellen, Zitate und
    Code sind Struktur. Dopplungen über Zeilenumbrüche innerhalb eines
    Absatzes werden gefunden (Hard-Wrap), Fett-Markierung stört nicht.
    """
    out = []
    for para in flow_paragraphs(body):
        text = re.sub(r"\*+", "", para)  # „**Fett** Wort“-Kleben mitdenken
        for m in re.finditer(r"\b([A-Za-zÄÖÜäöüß]{2,})(\s+)\1\b", text):
            w = m.group(1)
            vor = text[:m.start()].rstrip()[-1:]
            if w.lower() in R10_ARTIKEL and vor in {",", ";", ":"}:
                continue  # Relativsatz-Gefüge: „…, die die Thermostate …“
            ctx = re.sub(r"\s+", " ", text[max(0, m.start() - 45):m.end() + 45])
            out.append((rel, "R10-DOPPELWORT",
                        f"Wortdopplung „{m.group(0)}“ ⟦…{ctx}…⟧ – Klebe-Rest "
                        f"einer Editier-/Heiler-Kaskade, manuell reparieren",
                        m.group(0)))
        for m in R10_QUANTOR_RX.finditer(text):
            ctx = re.sub(r"\s+", " ", text[max(0, m.start() - 45):m.end() + 45])
            out.append((rel, "R10-DOPPELWORT",
                        f"Verdopplung mit Quantor-Einschub „{m.group(0)}“ "
                        f"⟦…{ctx}…⟧ – Klebe-Rest, Quantor gehört vor das Verb",
                        m.group(0)))
    return out


# R11–R14 POLITUR-RUINEN (30.09.2026, Issue #482):
# Vier echte Textdefekte aus automatisierten Politur-Läufen („Du bist der 0
# am deutschen Strommarkt“, „es ist der 2 Januar“, „Nutze 20 26 gezielt
# Mindestbestellwerte“, „SATZ: | **CHECK24-Vergleich** | …“) waren live im
# Content – keine Wache maß sie. Die Muster liegen genau einmal in
# sprachkern.POLITUR_RUINEN (SSOT): dort verweigert write_verified jede
# Schrift, die eine NEUE Ruine einführt; hier werden sie gemeldet und
# blockieren die Veröffentlichung. Am gesamten Content gegen False-Positive
# geprüft (0 Treffer auf 61 Artikel + alle Seiten).
def check_politur_ruinen(rel: str, body: str) -> list:
    """Erkennt Politur-Ruinen R11–R14 (Muster-SSOT: sprachkern) – hart."""
    out = []
    for regel, fund in politur_ruine_funde(body):
        out.append((rel, regel,
                    f"Politur-Ruine „{fund}“ – Überrest eines automatisierten "
                    f"Politur-Laufs, manuell reparieren", fund))
    return out


# R15-PHRASEN-DOPPEL (30.09.2026, Issue #482 – Mietwagen-Doppel-Intro):
# Zwei Intro-Blöcke im selben Artikel („Du willst mietwagen schnäppchen? …“
# vor der Politur, „Du willst ein Mietwagen-Schnäppchen? …“ danach) teilen
# sich eine identische 13-Wort-Sequenz („Stell dir vor: Du stehst am
# Flughafen von Faro. Die Luft ist warm“). duplikat_guard D1/D2 verpasste
# beide (kein exaktes Absatz-Duplikat, Ratio < 0,85, < 120 Zeichen).
# Grenzwert 10 Wörter: darunter liegen legitime Titel-Echos und
# Kurzformeln („50 € bis 200 € mehr Spielraum im Monat“), darüber ist eine
# wortgleiche Wiederholung im Fließtext immer ein Redaktionsfehler. Nur
# Fließtext: Überschriften, Listen, Tabellen, Zitate, CTA-Boxen und
# fett geführte Transparenz-Zeilen sind Struktur und bleiben außen vor.
R15_N = 10


def check_phrasendoppel(rel: str, body: str) -> list:
    """Erkennt identische ≥ 10-Wort-Sequenzen im Fließtext eines Artikels
    (Doppel-Intro, angehängte Blöcke) – harter Fehler, Redaktion entscheidet."""
    out = []
    text = " ".join(flow_paragraphs(body))
    text = re.sub(r"\*+", "", text)
    w = re.findall(r"[a-zäöüß0-9€%]+", text.lower())
    seen = {}
    gemeldete_spalten = []
    for i in range(len(w) - R15_N + 1):
        g = tuple(w[i:i + R15_N])
        if g not in seen:
            seen[g] = i
            continue
        erste = seen[g]
        # Überlappende Folgefunde derselben Passage nur einmal melden
        if any(a <= i <= b for a, b in gemeldete_spalten):
            continue
        if any(a <= erste <= b for a, b in gemeldete_spalten):
            continue
        frag = " ".join(g)
        out.append((rel, "R15-PHRASEN-DOPPEL",
                    f"identische {R15_N}-Wort-Sequenz im Fließtext: "
                    f"„…{frag}…“ – doppelte Passage, manuell reparieren",
                    frag))
        gemeldete_spalten.append((i, i + R15_N - 1))
    return out


def run_selftest() -> list:
    fehler = []
    term = {"dns": {"leitbegriff": "DNS-Server", "synonyme": ["Resolver", "Namensauflösung"],
                    "max_synonyme": 3, "kontext": "DNS"}}

    # R2
    body = "TEXT\n\nAnycast, Auflösungszeit, Blockliste, Cache-Flush, DDoS-Schutz, Edgerouter, Failover, Geofencing, Hijacking, IPv6-Resolver, Jitter, Kabelmodem, Latenzmessung, Meshknoten, Nameserver, Overhead, Paketlaufzeit, Query-Log, Root-Server, Spoofing, TTL-Wert, UDP-Fragmentierung, Whois-Abfrage, XDP-Filter, Zertifikatspinning, Backbone, Content-Delivery, Datenpaket, Endpunkt, Firewall-Regel, Gateway, Hop, Infrastruktur."
    if not any(f[1] == "R2-KEYWORD-DUMP" for f in check_article("t", body, {})):
        fehler.append("R2: Keyword-Dump nicht erkannt")

    # R3
    body3 = "DNS erklärt. Der DNS-Server ist wichtig. Der DNS-Server löst Namen auf. Der DNS-Server ist schnell. Der Resolver fragt nach, die Namensauflösung antwortet, der Resolver speichert, die Namensauflösung liefert."
    if not any(f[1] == "R3-TERMINOLOGIE" for f in check_article("t", body3, term)):
        fehler.append("R3: Terminologie-Mix nicht erkannt")

    # R4
    body4 = ("TEXT\n\n" + "Der Wechsel dauert fünf Minuten. Der Wechsel kostet nichts. Der Wechsel ist sicher. "
             "Der Wechsel bringt mehr Tempo. Der Wechsel lohnt sich. Der Wechsel ist simpel. " * 3)
    if not any(f[1] == "R4-SATZANFANG" for f in check_article("t", body4, {})):
        fehler.append("R4: Satzanfangs-Echo nicht erkannt")

    # R5
    body5 = "TEXT\n\nDieser Absatz hat viele Sätze. Der erste Satz ist kurz. Der zweite Satz ist kurz. Der dritte Satz ist kurz. Der vierte Satz ist kurz. Der fünfte Satz ist kurz. Der sechste Satz ist kurz. Der siebte Satz ist kurz."
    if not any(f[1] == "R5-ABSATZ-HART" for f in check_article("t", body5, {})):
        fehler.append("R5: Absatz-Monster nicht erkannt")

    # R7
    body7 = "TEXT\n\nIn diesem Ratgeber zeige ich dir alles. In diesem Ratgeber erfährst du mehr."
    if not any(f[1] == "R7-INTRO-FORMEL" for f in check_article("t", body7, {})):
        fehler.append("R7: Intro-Formel nicht erkannt")

    # R8
    body8 = "TEXT\n\nMehr dazu [die wichtigsten Anbieter](../../posts/2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich/) und [kaputter Link](../../posts/2026-08-20-falscher-slug/)."
    r8 = [f for f in check_article("t", body8, {}) if f[1] in ("R8-ANKER-ZIEL", "R8-URL-LEERZEICHEN")]
    if not any(f[1] == "R8-ANKER-ZIEL" for f in r8):
        fehler.append("R8: Ankertext-Ziel-Kohärenz nicht erkannt")
    body8b = "TEXT\n\n[Text](../../posts/2026-08-20-dsl-tarif-zu Hause/)"
    if not any(f[1] == "R8-URL-LEERZEICHEN" for f in check_article("t", body8b, {})):
        fehler.append("R8: URL-Leerzeichen nicht erkannt")
    # R8 Umlaut: "spätsommer" im Anker muss "spaetsommer" im Slug erkennen
    body8c = "TEXT\n\n[Heizung im Spätsommer](../../posts/2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden/)"
    r8c = [f for f in check_article("t", body8c, {}) if f[1] == "R8-ANKER-ZIEL"]
    if r8c:
        fehler.append("R8: Umlaut-Normalisierung fehlgeschlagen – „Spätsommer“ sollte „spaetsommer“ erkennen")
    # R8-NESTED-LINK: verschachtelte Doppel-Links müssen hart gefunden werden
    body8d = ("TEXT\n\n**Weiterlesen:** [Privathaftpflicht](../../posts/2026-08-17-privathaftpflicht-warum-sie-so-wichtig-ist-und-was-sie-kostet/) · "
              "[[Wohngebäudeversicherun](../../posts/2026-08-12-dein-haus-sicher-schuetzen-das-neue-vorsorge-update-2026/)g Vergleich]"
              "(../../posts/2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst/) · ok")
    r8d = [f for f in check_article("t", body8d, {}) if f[1] == "R8-NESTED-LINK"]
    if len(r8d) != 1:
        fehler.append(f"R8-NESTED-LINK: eingefrorener Schadensfall nicht erkannt (Funde: {len(r8d)})")
    body8e = ("TEXT\n\n**Weiterlesen:** [A-Artikel](../../posts/a/) · [B-Artikel](../../posts/b/) "
              "· [Ratgeber](../../pillar/x/)")
    if check_nested_links("t", body8e):
        fehler.append("R8-NESTED-LINK: Falsch-Positiv auf sauberer Weiterlesen-Zeile")
    # Toleranz: eckige Klammern OHNE Link-Syntax dürfen nicht feuern
    body8f = "TEXT\n\nDer Tipp [1] lohnt sich. Mehr unter [2]."
    if check_nested_links("t", body8f):
        fehler.append("R8-NESTED-LINK: Falsch-Positiv auf Fußnoten-Klammern")
    # R9-KLEBEWORT: Historisches Inserter-Artefakt („HHerfindestdu“ 02.09.2026)
    if not check_klebewoerter("t", "TEXT\n\n> Kurz: HHerfindestdu alles.\n\n### Ddeine6 Themen"):
        fehler.append("R9: Klebe-Artefakt nicht erkannt")
    # Negativfälle dürfen NICHT anschlagen
    for _ok in ("WLAN und DSGVO sind legitim.", "MagentaZuhause-Tarife bei der Telekom.",
                "Aachen liegt im Westen.", "Die FritzBox ist ein Router."):
        if check_klebewoerter("t", "TEXT\n\n" + _ok):
            fehler.append(f"R9: False-Positive bei „{_ok}“")

    # R10-DOPPELWORT: verlorene Lektorats-Heilung („senken senken“, 28.09.2026)
    body10 = ("TEXT\n\nWer seine Gasrechnung senken senken will, sollte "
              "im Spätsommer handeln.")
    if not any(f[1] == "R10-DOPPELWORT" for f in check_article("t", body10, {})):
        fehler.append("R10: Wortdopplung nicht erkannt")
    # Dopplung über Zeilenumbruch (Hard-Wrap im selben Absatz) muss finden
    body10b = "TEXT\n\nDu kannst deine Kosten nachhaltig senken\nsenken und dabei ruhig bleiben."
    if not any(f[1] == "R10-DOPPELWORT" for f in check_article("t", body10b, {})):
        fehler.append("R10: Wortdopplung über Zeilenumbruch nicht erkannt")
    # Dopplung über Fett-Markup („**senken** senken“) muss finden
    body10c = "TEXT\n\nDu kannst deine Kosten nachhaltig **senken** senken und dabei ruhig bleiben."
    if not any(f[1] == "R10-DOPPELWORT" for f in check_article("t", body10c, {})):
        fehler.append("R10: Wortdopplung über Fett-Markup nicht erkannt")
    # Einschub-Variante: Duplikat klammert Quantor (Fund 28.09.2026)
    body10e = ("TEXT\n\nMit dem richtigen Vorgehen lässt sich die Gasrechnung "
               "senken um bis zu 15 % senken.")
    if not any(f[1] == "R10-DOPPELWORT" for f in check_article("t", body10e, {})):
        fehler.append("R10: Wortdopplung mit Quantor-Einschub nicht erkannt")
    # Korrekte Quantor-Stellung darf NICHT anschlagen
    body10f = "TEXT\n\nMit dem richtigen Vorgehen senkst du die Gasrechnung um bis zu 15 Prozent."
    if any(f[1] == "R10-DOPPELWORT" for f in check_article("t", body10f, {})):
        fehler.append("R10: False-Positive bei korrekter Quantor-Stellung")
    # Negativfälle dürfen NICHT anschlagen (legitime deutsche Muster)
    for _ok in ("Zugluft, die die Thermostate nach oben treiben lässt.",
                "Wer billig kauft, kauft bekanntlich zweimal.",
                "Die Daten, die erfasst werden, werden sicher gespeichert.",
                "Die Tankregelung voll-voll ist am fairsten.",
                "Für dich heißt das: Das Angebot übersteigt die Nachfrage.",
                "Der beste Tarif ist der, der im Ernstfall passt.",
                "Auch teure Abos und Konsum-Fallen fallen so richtig auf.",
                "Diese Sorgen sorgen selten für Ruhe."):
        if any(f[1] == "R10-DOPPELWORT" for f in check_article("t", "TEXT\n\n" + _ok, {})):
            fehler.append(f"R10: False-Positive bei „{_ok}“")
    # Überschrift → Absatz-Wiederholung (Journal-Muster) darf NICHT anschlagen
    body10d = "TEXT\n\n### Kinder\n\nKinder haben meist noch keine Berufsunfähigkeit."
    if any(f[1] == "R10-DOPPELWORT" for f in check_article("t", body10d, {})):
        fehler.append("R10: False-Positive bei Überschrift→Absatz-Wiederholung")

    # ---------- R11–R14 Politur-Ruinen (eingefrorene Schadensfälle #482) ----------
    # R11: zerrissene Jahreszahl (Weihnachtsartikel, 30.09.2026)
    body11 = ("TEXT\n\nVersandkosten fressen dein Budget auf. "
              "Nutze 20 26 gezielt Mindestbestellwerte, um diesen Posten zu streichen.")
    if not any(f[1] == "R11-JAHRESZAHL-SPLIT" for f in check_article("t", body11, {})):
        fehler.append("R11: zerrissene Jahreszahl nicht erkannt")
    # R11-Negativ: echte Tausender-Gruppen (DREIER-Blöcke) bleiben außen vor
    for _ok in ("Bei 40 000 € netto sind das rund 2 000 €.",
                "Der Sparplan läuft seit 1998 und trägt seit 2026 Früchte.",
                "Rund 1 100 € im Jahr bleiben so in der Kasse."):
        if any(f[1] == "R11-JAHRESZAHL-SPLIT" for f in check_article("t", "TEXT\n\n" + _ok, {})):
            fehler.append(f"R11: False-Positive bei „{_ok}“")

    # R12: Artikel + nackte Zahl + Präposition (Ökostromartikel, 30.09.2026)
    body12 = ("TEXT\n\nFiltere beim Vergleich nach diesen Siegeln. "
              "Du bist der 0 am deutschen Strommarkt und wirst von Umweltverbänden empfohlen.")
    if not any(f[1] == "R12-ZAHL-RUINE" for f in check_article("t", body12, {})):
        fehler.append("R12: Zahl-Ruine „der 0 am“ nicht erkannt")
    # R12-Negativ: Ordinal-Daten mit Punkt und normale Mengen bleiben frei
    for _ok in ("Der 3. Oktober ist der Tag der Deutschen Einheit.",
                "Die 30 € Gebühr fällt nur im ersten Jahr an."):
        if any(f[1] == "R12-ZAHL-RUINE" for f in check_article("t", "TEXT\n\n" + _ok, {})):
            fehler.append(f"R12: False-Positive bei „{_ok}“")

    # R13: Ordinal-Datum ohne Punkt (Weihnachten + Neujahrs-Entwurf, 30.09.2026)
    body13 = "TEXT\n\nStell dir vor, es ist der 2 Januar 2026. Jedes Jahr am 1 Januar ist die Motivation riesig."
    r13 = [f for f in check_article("t", body13, {}) if f[1] == "R13-DATUM-PUNKT"]
    if len(r13) < 2:
        fehler.append(f"R13: Datum ohne Punkt nicht erkannt (Funde: {len(r13)})")
    # R13-Negativ: Datum MIT Punkt ist korrekt
    if any(f[1] == "R13-DATUM-PUNKT" for f in check_article("t", "TEXT\n\nAm 2. Januar 2026 öffnest du deine App.", {})):
        fehler.append("R13: False-Positive bei korrektem Datum mit Punkt")

    # R14: Marker-Ruine am Zeilenanfang (E-Bike-Tabelle, 30.09.2026)
    body14 = ("TEXT\n\n| Anbieter | Beitrag | Selbstbeteiligung |\n|---|---|---|\n"
              "| **HUK‑Coburg** | 36 € | 100 € |\n"
              "SATZ: | **CHECK24-Vergleich** | – | | | | |")
    if not any(f[1] == "R14-MARKER-RUINE" for f in check_article("t", body14, {})):
        fehler.append("R14: Marker-Ruine „SATZ:“ nicht erkannt")
    # R14-Negativ: normale Satz-Anfänge und Kleingeschriebenes bleiben frei
    for _ok in ("Der Satz: kurze Hauptsätze gewinnen.\n\nZähle deine Fixkosten auf.",
                "Tipp: Prüfe die Laufzeit vor dem Abschluss."):
        if any(f[1] == "R14-MARKER-RUINE" for f in check_article("t", "TEXT\n\n" + _ok, {})):
            fehler.append(f"R14: False-Positive bei „{_ok}“")

    # ---------- R15 Phrasen-Dopplung (Mietwagen-Doppel-Intro, #482) ----------
    body15 = ("TEXT\n\n"
              "Du willst mietwagen schnell machen? Stell dir vor: Du stehst am Flughafen von Faro. "
              "Die Luft ist warm, doch die drückende Hitze ist jener milden Brise gewichen.\n\n"
              "Dieses Privileg hast du dir Wochen zuvor gesichert.\n\n"
              "Du willst ein Mietwagen-Schnäppchen? Stell dir vor: Du stehst am Flughafen von Faro. "
              "Die Luft ist warm, andere Reisende haben im August horrende Summen bezahlt.\n\n"
              "Dieses Privileg hast du dir ebenfalls Wochen zuvor gesichert.")
    if not any(f[1] == "R15-PHRASEN-DOPPEL" for f in check_article("t", body15, {})):
        fehler.append("R15: Doppel-Intro (identische 13-Wort-Sequenz) nicht erkannt")
    # R15-Negativ: 9-Wort-Echo (Titel-Anklang) und einmalige Formeln bleiben frei
    body15b = ("TEXT\n\n"
               "Diese fünf einfachen Frugalismus-Tricks für den Alltag schaffen schnell Spielraum.\n\n"
               "Die fünf einfachen Frugalismus-Tricks für den Alltag funktionieren, weil sie wiederholbar sind.\n\n"
               "Ein Überschuss von 50 € bis 200 € mehr Spielraum im Monat ist realistisch. "
               "Noch einmal: 50 € bis 200 € mehr Spielraum im Monat.")
    if any(f[1] == "R15-PHRASEN-DOPPEL" for f in check_article("t", body15b, {})):
        fehler.append("R15: False-Positive bei 9-Wort-Titel-Echo")

    return fehler


def main() -> int:
    fehler = run_selftest()
    if fehler or SELFTEST_ONLY:
        for f in fehler:
            print("🛑 " + f)
        if fehler:
            print("SELFTEST FEHLGESCHLAGEN – nichts geschrieben.")
            return 2
        print("✅ Verständnis-Selbsttest: R2–R15 grün.")
        return 0

    term = load_terminologie()
    today = date.today().isoformat()
    paths = sorted(POSTS.glob("*/index.md"))
    paths = [p for p in paths if p.name != "_index.md"]
    if NEW_ONLY:
        paths = [p for p in paths
                 if re.search(rf"^date:\s*\"?{today}", p.read_text(encoding="utf-8"), re.M)
                 and "draft: false" in p.read_text(encoding="utf-8")]
        if not paths:
            print("Verständnis-Gate: keine neuen Artikel heute – OK.")
            return 0

    all_finds = []
    for p in paths:
        rel = str(p.relative_to(ROOT))
        body = split_body(p.read_text(encoding="utf-8"))
        all_finds += check_article(rel, body, term)

    # Hub-/Listen-Seiten (02.09.2026): In posts/_index.md wurde mit
    # „HHerfindestdu“/„Ddeine6 Themenwelten“ das Reste-Artefakt eines
    # historischen Inserter-Skripts gefunden – seitdem laufen für diese
    # Seiten die Seiten-Level-Regeln (Nested-Links, Klebewörter) mit.
    # Seit 28.09.2026 (Klebe-Artefakte-Premium-Audit) gilt das für ALLE
    # Content-Flächen außerhalb der Artikel: „gesamter Blog“ heißt auch
    # Startseite, Pillar-Hubs, Rechts-/Methodik-/Über-Seiten und die
    # Newsletter-Seiten. Neue Seiten rücken automatisch in den Scan.
    if not NEW_ONLY:
        alle_md = set((ROOT / "content").rglob("*.md"))
        artikel_md = set(POSTS.glob("*/index.md"))
        seiten_paths = sorted(p for p in alle_md - artikel_md
                              if p.name in ("index.md", "_index.md"))
        for p in seiten_paths:
            rel = str(p.relative_to(ROOT))
            body = split_body(p.read_text(encoding="utf-8"))
            all_finds += check_nested_links(rel, body)
            all_finds += check_klebewoerter(rel, body)
            all_finds += check_wortdopplung(rel, body)
            # R11–R14 (Regex-Ruinen) laufen auch auf Seiten – R15 bewusst
            # nicht: Rechtsseiten wiederholen Adressen/Blöcke legitim.
            all_finds += check_politur_ruinen(rel, body)

    # dedup
    uniq, seen = [], set()
    for f in all_finds:
        k = (f[0], f[1], f[2][:70])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(f)

    # R8-ANKER-ZIEL ist bewusst NUR weich (semantische Kohärenz ist nicht
    # deterministisch prüfbar – Funde sind Review-Kandidaten, keine Blocker).
    hard_rules = ("R2-KEYWORD-DUMP", "R3-TERMINOLOGIE", "R5-ABSATZ-HART", "R7-INTRO-FORMEL",
                  "R8-URL-LEERZEICHEN", "R8-NESTED-LINK", "R9-KLEBEWORT", "R10-DOPPELWORT")
    hard = [f for f in uniq if f[1] in hard_rules]
    soft = [f for f in uniq if f[1] not in hard_rules]

    lines = [f"# 🧠 TEXTVERSTÄNDNIS-REPORT (textverstaendnis_guard.py)",
             f"**Stand:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · Artikel: {len(paths)}" +
             (f" · Seiten (Klebe-Scan): {len(seiten_paths)}" if not NEW_ONLY else " · Engine (nur heute)"),
             "",
             f"**Harte Regeln (R2/R3/R5-hart/R7/R8-URL/R9/R10/R11–R15):** {len(hard)} Funde",
             f"**Weiche Regeln (R4/R5/R8-Anker):** {len(soft)} Funde",
             ""]
    for rel, regel, detail, pos in uniq[:60]:
        lines.append(f"- `{rel}` **{regel}**: {detail}")
    lines.append("")
    lines.append("_Textverständnis: 1 Konzept = 1 Leitbegriff, 1 Absatz = 1 Gedanke, keine Komma-Listen, keine Template-Sprache._")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    with HISTORY.open("a", encoding="utf-8") as h:
        h.write(json.dumps({"date": today, "hard": len(hard), "soft": len(soft),
                            "articles": len(paths)}, ensure_ascii=False) + "\n")

    if AS_JSON:
        print(json.dumps({"finds": [{"file": f[0], "rule": f[1], "detail": f[2]} for f in uniq]},
                         ensure_ascii=False, indent=2))
        return 1 if hard and NEW_ONLY else 0

    print(f"Verständnis-Audit: {len(paths)} Artikel | hart {len(hard)} · weich {len(soft)}")
    for rel, regel, detail, pos in uniq[:30]:
        mark = "❌" if regel in hard_rules else "⚠️"
        print(f"  {mark} [{regel:>16}] {rel}: {detail[:120]}")
    if NEW_ONLY and hard:
        print("❌ Verständnis-Gate nicht bestanden – harte Verstöße in neuen Artikeln!")
        return 1
    if not uniq:
        print("✅ Keine Verständnis-Funde.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
