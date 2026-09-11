#!/usr/bin/env python3
"""
TEXTVERSTÄNDNIS-GUARD (R2–R9) für FranksFinanzcheck.

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

HUB-WACHEN (11.09.2026 – Premium-Reparatur /posts/: die Artefakte
„Hhierfindest“ und „Ddeine6“ standen WOCHENLANG live, weil die Hub-Seiten
nur im Report mitliefen (und dort hinter 60 Artikel-Funden abgeschnitten
wurden) – es gab kein Gate. Jetzt R10–R14 plus harter --hub-gate-Modus,
verankert im Qualitäts-Gate (link-check.yml, läuft bei jedem Push/PR +
täglich). Regeln für content/**/_index.md (Sektions-Hubs) & pillar-Bundles:

  R10 Zahl-Kleber-Guard    Buchstabe+Zahl geklebt („Ddeine6“, „zahlst20“) –
                           Folgeklasse des defekten Inserters. Marken/Akronyme
                           (CHECK24, CAT7, MP3) und „90ern“ bleiben verschont.
  R11 Hub-Link-Regel       Sektions-Hubs dürfen keine ../-Relativlinks
                           enthalten – die brechen still um, sobald Hugo-
                           Ref-Auflösung/Pagination sich ändert. Wurzel-
                           absolut (/posts/…, /pillar/…) ist Hausstandard.
  R12 Hub-Ziel-Existenz    Jeder /posts/<slug>/- und /pillar/<slug>/-Link
                           eines Hubs muss auf ein existierendes, nicht als
                           draft markiertes Content-Bundle zeigen.
  R13 Hub-Meta             Titel 10–130 Zeichen, Description 80–160
                           (SERP-Korridor), lastmod gültig & nicht in der
                           Zukunft; posts/_index.md braucht lastmod zwingend
                           („sortiert nach Aktualität" ist ein Versprechen).
  R14 Kurz-&-knapp-Block   posts/_index.md beginnt mit dem Zitat
                           „> 💡 **Kurz & knapp:** …" (≤ 420 Zeichen) –
                           Snippet-/Pin-Kanon der Sektionsseite.

MODI:
  python3 scripts/textverstaendnis_guard.py            # Report (alle Artikel)
  python3 scripts/textverstaendnis_guard.py --json     # maschinenlesbar
  python3 scripts/textverstaendnis_guard.py --new-only # Engine-Modus (heute);
                                                       # harte Regeln -> Exit 1
  python3 scripts/textverstaendnis_guard.py --hub-gate # Hubs hart prüfen;
                                                       # Fund -> Exit 1 (CI-Gate)
  python3 scripts/textverstaendnis_guard.py --selftest # Sabotage-Schutz

Ausgabe: TEXTVERSTAENDNIS-REPORT.md + data/verstaendnis_history.jsonl
(Hub-Funde stehen im Report VOR den Artikel-Funden – nicht mehr hinten
abgeschnitten.)
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

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "content" / "posts"
REPORT = ROOT / "TEXTVERSTAENDNIS-REPORT.md"
HISTORY = ROOT / "data" / "verstaendnis_history.jsonl"
TERMINOLOGIE = ROOT / "data" / "terminologie.yaml"

NEW_ONLY = "--new-only" in sys.argv
AS_JSON = "--json" in sys.argv
SELFTEST_ONLY = "--selftest" in sys.argv
HUB_GATE = "--hub-gate" in sys.argv

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
R9_ALLOW = {"Aachen", "Aachener", "Ggf", "ggf", "zgl", "Zzgl", "zzgl"}  # „gegebenenfalls“/„zuzüglich“ = legitime Abk.
# (Live-Fund 11.09.2026: R9 meldete „zzgl“ und haette jeden neuen Artikel im Engine-Gate blockiert)


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


# ---------------------------------------------------------------------------
# HUB-WACHEN R10–R14 (11.09.2026) – schützen die Sektions-/Hub-Seiten, die
# von der Artikel-Kette (Engine-Gate, Lektor, Rechtschreib-Report) bisher
# nicht hart erwischt wurden. Alle Funde sind HART: Hub-Seiten sind klein,
# jede Regel ist dort deterministisch beweisbar – False-Positive-Ausreden
# wie bei Langtext-Weichregeln gibt es hier bewusst nicht.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# HUB-WACHEN R10–R14 (11.09.2026) – schützen die Sektions-/Hub-Seiten, die
# von der Artikel-Kette (Engine-Gate, Lektor, Rechtschreib-Report) bisher
# nicht hart erwischt wurden. Alle Funde sind HART: Hub-Seiten sind klein,
# jede Regel ist dort deterministisch beweisbar – False-Positive-Ausreden
# wie bei Langtext-Weichregeln gibt es hier bewusst nicht.
# ---------------------------------------------------------------------------

# R10: Kleinbuchstabe klebt direkt an Ziffern („Ddeine6“, „zahlst20“).
# Nur die Richtung Buchstabe→Zahl: die Gegenrichtung erzeugt im Deutschen
# regulär legitime Formen („90ern“, „20er-Jahre“). Großbuchstaben vor der
# Zahl sind Marken/Akronyme (CHECK24, CAT7, VDSL50) und bleiben unberührt.
R10_ZAHL_RX = re.compile(r"\b[A-ZÄÖÜ]?[a-zäöüß]{2,}\d+\b")
R10_ALLOW = {"mp3", "mp4", "x86", "utf8"}  # Technik-Terme: Buchstabe+Zahl ist korrekt


def check_zahl_kleber(rel: str, body: str) -> list:
    """R10: Buchstabe+Zahl geklebt – Resteschaden desselben Inserter-Typs wie R9."""
    out = []
    clean = re.sub(r"```.*?```", " ", body, flags=re.S)
    clean = re.sub(r"\{\{[^}]*\}\}", " ", clean)
    clean = re.sub(r"\]\([^)\n]*\)", "]()", clean)  # Link-Ziele (Datums-Slugs) ausklammern
    for m in R10_ZAHL_RX.finditer(clean):
        w = m.group(0)
        if w.lower() in R10_ALLOW:
            continue
        out.append((rel, "R10-ZAHL-KLEBER",
                    f"„{w}“ – Buchstabe klebt an Zahl (Muster „Ddeine6“): "
                    "liest sich nie so gemeint – Leerzeichen ergänzen oder Wort trennen", w))
    return out


# R11: Ausbrechende Relativlinks in Sektions-Hubs. „../../posts/x/“ wird
# aktuell von Hugo zur Permalink-Auflösung genutzt – verlässt man sich
# darauf, wird die Seite beim kleinsten Ref-/Pagination-Umbau still falsch.
R11_ESC_RX = re.compile(r"\]\((\.\.[^)\n]*)\)")


def check_hub_links(rel: str, body: str) -> list:
    out = []
    for m in R11_ESC_RX.finditer(body):
        out.append((rel, "R11-HUB-LINK",
                    f"Hub-Seite verlinkt relativ ausbrechend „{m.group(1)[:60]}“ – "
                    "wurzel-absolut setzen (/posts/…, /pillar/…)", m.group(1)))
    return out


# R12: Ziel-Existenz. Ein Slug-Umbau lässt Hub-Links zu 404-Waisen
# verkommen; geprüft wird deterministisch gegen die Content-Struktur
# (identische Auflösung wie Hugo-Pages, ohne Hugo).
R12_TARGET_RX = re.compile(r"\]\((/posts/[^)\s#?]+|/pillar(?:/[^)\s#?]+)?)/?\)")


def hub_target_state(href: str, root: Path = None) -> tuple:
    """(ok, grund) – prüft Bundle-/Datei-Existenz und draft-Status eines Ziels."""
    root = root or ROOT
    path = href.strip().rstrip("/")
    if path == "/pillar":
        ok = (root / "content" / "pillar" / "_index.md").exists()
        return (True, "") if ok else (False, "content/pillar/_index.md fehlt")
    parts = [x for x in path.split("/") if x]
    if len(parts) < 2:
        return (True, "")  # /posts/ (Sektion selbst) – entsteht immer mit dem Bau
    sec, slug = parts[0], parts[1]
    for cand in (root / "content" / sec / slug / "index.md",
                 root / "content" / sec / (slug + ".md")):
        if cand.exists():
            if re.search(r"^draft:\s*true\s*$", cand.read_text(encoding="utf-8"), re.M):
                return (False, "Ziel existiert, ist aber Entwurf (draft: true) – im Live-Bau 404")
            return (True, "")
    return (False, f"Content-Bundle content/{sec}/{slug}/ fehlt – toter Link im Live-Bau")


def check_hub_targets(rel: str, body: str, resolve=None) -> list:
    resolve = resolve or hub_target_state
    out = []
    for m in R12_TARGET_RX.finditer(body):
        href = m.group(1)
        ok, grund = resolve(href)
        if not ok:
            out.append((rel, "R12-HUB-ZIEL", f"Hub-Link {href} → {grund}", href))
    return out


def _fm_field(fm: str, key: str) -> str:
    m = re.search(rf"^{key}:\s*\"?([^\"\n]*?)\"?\s*$", fm, re.M)
    return m.group(1).strip() if m else ""


def check_hub_meta(rel: str, raw: str) -> list:
    """R13: Frontmatter-Maße der Hub-Seite (SERP-Korridor + ehrliche Aktualität)."""
    out = []
    fm = raw.split("---", 2)[1] if raw.startswith("---") else ""
    title = _fm_field(fm, "title")
    desc = _fm_field(fm, "description")
    lm = _fm_field(fm, "lastmod")
    if not (10 <= len(title) <= 130):
        out.append((rel, "R13-HUB-META",
                    f"Titel {len(title)} Zeichen (Korridor 10–130) – außerhalb kein sauberes SERP-Snippet", title[:80]))
    if not (80 <= len(desc) <= 160):
        out.append((rel, "R13-HUB-META",
                    f"Description {len(desc)} Zeichen (Korridor 80–160) – Google kürzt ab ~160; Unterlänge verschenkt die Snippet-Zeile", desc[:80]))
    if lm:
        m = re.match(r"(\d{4}-\d{2}-\d{2})", lm)
        if not m:
            out.append((rel, "R13-HUB-META", f"lastmod „{lm[:20]}“ nicht im Format JJJJ-MM-TT", lm))
        elif m.group(1) > date.today().isoformat():
            out.append((rel, "R13-HUB-META",
                        f"lastmod {m.group(1)} liegt in der Zukunft (heute {date.today()}) – „zuletzt aktualisiert“ wäre eine Lüge", lm))
    if rel.replace("\\", "/").endswith("posts/_index.md") and not lm:
        out.append((rel, "R13-HUB-META",
                    "posts/_index.md braucht lastmod – die Seite verspricht „sortiert nach Aktualität“; frische Inhalte ohne frisches lastmod wirken veraltet", lm))
    return out


R14_KURZ_RX = re.compile(r"^>\s*💡?\s*\*\*Kurz & knapp:\*\*\s*\S")
R14_MAX = 420


def check_kurz_block(rel: str, body: str) -> list:
    """R14: Der Kurz-&-knapp-Satz ist der kanonische Teaser der Sektionsseite
    (Snippet-/Pin-Quelle) – er muss ERSTES Element und kurz genug sein."""
    for line in body.split("\n"):
        if not line.strip():
            continue
        stripped = line.strip()
        if not R14_KURZ_RX.match(stripped):
            return [(rel, "R14-KURZ-BLOCK",
                     "Erstes Element von posts/_index.md muss das Zitat „> 💡 **Kurz & knapp:** …“ sein "
                     "(Snippet-/Pin-Kanon der Sektionsseite) – gefunden: „" + stripped[:50] + "“", stripped)]
        if len(stripped) > R14_MAX:
            return [(rel, "R14-KURZ-BLOCK",
                     f"Kurz-&-knapp-Block {len(stripped)} Zeichen (Limit {R14_MAX}) – Meta-Vorschau und Pin-Text laufen sonst über", stripped[:80])]
        return []
    return [(rel, "R14-KURZ-BLOCK", "posts/_index.md hat keinen Textkörper – die Sektionsseite wäre leer", "")]


def hub_files() -> list:
    files = [ROOT / "content" / "_index.md", POSTS / "_index.md",
             ROOT / "content" / "pillar" / "_index.md"]
    files += sorted((ROOT / "content" / "pillar").glob("*/index.md"))
    return [p for p in files if p.exists()]


def check_hub(rel: str, path: Path) -> list:
    """Alle Hub-Regeln für eine Datei. R11–R14 gelten nur für echte
    Sektions-Hubs (_index.md); die Pillar-Bundles pflegen bewusst den
    bestehenden Hausstil (../../-Relativlinks) – dort wären R11/R13
    sofort falscher Alarm, R9/R10 laufen für sie trotzdem."""
    raw = path.read_text(encoding="utf-8")
    body = split_body(raw)
    out = []
    out += check_nested_links(rel, body)
    out += check_klebewoerter(rel, body)
    out += check_zahl_kleber(rel, body)
    if path.name == "_index.md":
        out += check_hub_links(rel, body)
        out += check_hub_targets(rel, body)
        out += check_hub_meta(rel, raw)
        if rel.replace("\\", "/").endswith("posts/_index.md"):
            out += check_kurz_block(rel, body)
    return out


def run_hub_gate() -> int:
    finds = []
    for p in hub_files():
        finds += check_hub(str(p.relative_to(ROOT)), p)
    if finds:
        print(f"❌ Hub-Gate: {len(finds)} Fundstelle(n) in den Sektions-/Hub-Seiten:")
        for rel, regel, detail, _pos in finds[:40]:
            print(f"  [{regel}] {rel}: {detail[:170]}")
        return 1
    print(f"✅ Hub-Gate: {len(hub_files())} Hub-Seiten grün "
          "(Kleber R9, Zahl-Kleber R10, Hub-Links R11, Ziel-Existenz R12, Meta R13, Kurz-&-knapp R14).")
    return 0


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
                "Aachen liegt im Westen.", "Die FritzBox ist ein Router.",
                "Die Buchung kostet 49 € zzgl. 19 % MwSt."):
        if check_klebewoerter("t", "TEXT\n\n" + _ok):
            fehler.append(f"R9: False-Positive bei „{_ok}“")

    # R10–R14 HUB-Wachen (11.09.2026, Live-Schaden posts/_index.md):
    # R10 muss den Zahl-Kleber finden, aber Marken & Ordinalzahlen verschonen
    if not check_zahl_kleber("t", "TEXT\n\ndu zahlst20 € extra"):
        fehler.append("R10: Zahl-Kleber nicht erkannt")
    for _ok2 in ("**CHECK24** prüfst du in Minuten.", "15 m CAT7 verlegen.",
                 "Nachtspeicher aus den 90ern.", "Die 50–30–20-Regel hilft.",
                 "mp3-Player und mp4-Video bleiben ruhig."):
        if check_zahl_kleber("t", "TEXT\n\n" + _ok2):
            fehler.append(f"R10: False-Positive bei „{_ok2}“")
    # R11: ausbrechende Relativlinks finden, wurzel-absolute & Kinderrefs lassen
    if not check_hub_links("t", "[a](../../posts/x/)"):
        fehler.append("R11: ../-Hub-Link nicht erkannt")
    if check_hub_links("t", "[a](/posts/x/) und [b](strom-sparen/)"):
        fehler.append("R11: False-Positive auf sauberen Hub-Links")
    # R12: mit eingesetzter Fake-Auflösung hermetisch testen
    fake = lambda href: (href != "/posts/gespenst/", "feht")
    if len(check_hub_targets("t", "[x](/posts/gespenst/) [y](/posts/reales/)", resolve=fake)) != 1:
        fehler.append("R12: Hub-Ziel-Prüfung nicht korrekt (Geist-Ziel nicht gefunden oder False-Positive)")
    # R13: Meta-Maße
    bad_fm = "---\ntitle: \"x\"\ndescription: \"zu kurz\"\n---\n\nText"
    if len([f for f in check_hub_meta("content/posts/_index.md", bad_fm)]) < 2:
        fehler.append("R13: Meta-Verstöße nicht erkannt")
    good_fm = ("---\ntitle: \"" + "A" * 60 + "\"\ndescription: \"" + "B" * 120 +
               "\"\nlastmod: 2026-01-01\n---\n\nText")
    if check_hub_meta("content/pillar/_index.md", good_fm):
        fehler.append("R13: False-Positive auf gesunder Hub-Meta")
    # R14: Kurz-&-knapp-Pflicht nur posts/_index.md – positiv + negativ
    if check_kurz_block("content/posts/_index.md",
                        "\n> 💡 **Kurz & knapp:** Hier findest du alles.\n\n## Mehr\n"):
        fehler.append("R14: sauberer Kurz-&-knapp-Block wurde gefunden (False-Positive)")
    if not check_kurz_block("content/posts/_index.md", "\n## Los geht es\n\nText.\n"):
        fehler.append("R14: fehlender Kurz-&-knapp-Block nicht erkannt")
    if not check_kurz_block("content/posts/_index.md", "\n> 💡 **Kurz & knapp:** " + "x" * 500 + "\n"):
        fehler.append("R14: überlanger Kurz-&-knapp-Block nicht erkannt")

    return fehler


def main() -> int:
    fehler = run_selftest()
    if fehler or SELFTEST_ONLY:
        for f in fehler:
            print("🛑 " + f)
        if fehler:
            print("SELFTEST FEHLGESCHLAGEN – nichts geschrieben.")
            return 2
        print("✅ Verständnis-Selbsttest: alle Fälle grün (R2–R14 inkl. Hub-Wachen).")
        return 0

    # Hub-Gate (11.09.2026): liest NUR die content/**/_index.md + Pillar-Hubs,
    # schreibt nichts – der harte Blocker für Push/PR im Qualitäts-Gate.
    if HUB_GATE:
        return run_hub_gate()

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

    # Hub-/Listen-Seiten (02.09.2026, gehärtet 11.09.2026): In posts/_index.md
    # standen die Inserter-Artefakte „Hhierfindest“/„Ddeine6“ wochenlang live,
    # weil Hub-Funde nur im Report mittliefen und dort hinter den ersten 60
    # Artikel-Funden abschnitten. Jetzt: volle Hub-Regeln R9–R14 (check_hub)
    # + harter --hub-gate-Modus als CI-Blocker. Hub-Funde stehen im Report
    # vor den Artikel-Funden.
    if not NEW_ONLY:
        for p in hub_files():
            all_finds += check_hub(str(p.relative_to(ROOT)), p)

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
                  "R8-URL-LEERZEICHEN", "R8-NESTED-LINK", "R9-KLEBEWORT",
                  "R10-ZAHL-KLEBER", "R11-HUB-LINK", "R12-HUB-ZIEL", "R13-HUB-META", "R14-KURZ-BLOCK")
    hard = [f for f in uniq if f[1] in hard_rules]
    soft = [f for f in uniq if f[1] not in hard_rules]

    lines = [f"# 🧠 TEXTVERSTÄNDNIS-REPORT (textverstaendnis_guard.py)",
             f"**Stand:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · Artikel: {len(paths)} · Hub-Seiten: {len(hub_files())}" +
             (" · Engine (nur heute)" if NEW_ONLY else ""),
             "",
             f"**Harte Regeln (R2/R3/R5-hart/R7/R8/R9/R10–R14):** {len(hard)} Funde",
             f"**Weiche Regeln (R4/R5/R8-Anker):** {len(soft)} Funde",
             ""]
    # Harte Funde ZUERST – Hub-Reparaturen dürfen nicht mehr hinter weichen
    # Artikel-Echos im 60-Zeilen-Abschneiden untergehen (Ursache #posts-Typo).
    for rel, regel, detail, pos in hard[:150]:
        lines.append(f"- `{rel}` **{regel}**: {detail}")
    for rel, regel, detail, pos in soft[:60]:
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
