#!/usr/bin/env python3
# ============================================================
#  REDAKTIONS-STANDARD-WACHE (Capital · WirtschaftsWoche · DIE ZEIT)
#
#  Auftrag (Frank, 02.09.2026): Die Blogautomatik dauerhaft auf das
#  Qualitätsniveau der Online-Redaktionen von Capital, WirtschaftsWoche
#  und DIE ZEIT (Verbraucher-/Geld-Teil) heben – für BESTEHENDE und
#  ZUKÜNFTIGE Beiträge. Recherche + Quellen + Methoden-Übertragung:
#  REDAKTIONS-STANDARD-CAPITAL-WIWO-ZEIT.md (im Repo-Root).
#
#  REGELN RS1–RS8 (Kurzfassung; Details im Recherche-Dokument):
#    RS1  ZEIT-Artikelzusammenfassung: Pflicht-Modul
#         „**Das Wichtigste in Kürze**“ mit ≥ 3 Bullets         [HART]
#    RS2  Capital-erklärt-Stil: ≥ 2 Frage-Überschriften (H2 mit „?“) [HART]
#    RS3  Capital-Faustregel: ≥ 1 markierte „Faustregel: …“     [HART]
#         – seit #766 (15.10.2026) aus einem POOL gewählt und gegen den
#         Bestand gemessen; ein Satz darf nie zum Massensatz werden
#    RS4  ZEIT-/Dossier-Struktur: ≥ 1 nummerierte Schrittfolge
#         (≥ 3 Schritte) ODER ≥ 2 „Schritt“-Überschriften       [HART]
#    RS5  WiWo-Verifikation: harte Zahlen ohne Einordnung
#         (ca./rund/laut/Stand/Spanne)                          [WEICH]
#    RS6  WiWo-Quellen-Regel: Phantom-Quellen („laut einer Studie“,
#         „Experten sagen“ …) – ein Bot darf nichts erfinden     [WEICH]
#    RS7  Byline/E-E-A-T: `author:`; Erfahrung nur mit `erfahrung_beleg` [HART,
#         deterministische Selbstheilung]
#    RS8  Korrektur-Transparenz: `korrektur:`-Feld → Korrektur-Box
#         im Layout + Log data/korrekturen.yaml (dauerhaft aktiv)
#
#  MODI:
#    python3 scripts/redaktions_standard.py               # Report (alle live)
#    ... --new-only                                       # nur heute publizierte
#    ... --gate --new-only                                # harte Funde → draft
#                                                         #   (Circuit-Breaker >3)
#    ... --fix                                            # deterministisch (RS7
#                                                         #   + RS3-EINZIGARTIG)
#    ... --fix --ai [--backlog N] [--ai-budget N]         # KI-Heilung
#    ... --fix --nur-faustregel                            # nur RS3-Einzig-
#                                                         #   artigkeit (#766)
#    ... --selftest                                       # Sabotage-Schutz
#    ... --register-korrektur --file X.md --grund "…"     # RS8-Log-Eintrag
#
#  SICHERHEIT NACH JEDER KI-ÄNDERUNG (Verifikation VOR dem Schreiben):
#    - alle Links (Ziele) bleiben byte-identisch erhalten
#    - H2-Anzahl bleibt stabil (nur Text darf sich ändern)
#    - Länge ≥ 90 % des Originals
#    - Frontmatter bleibt byte-identisch
#    - Publikations-Vertrag (07.10.2026, WF-54C4/#607): Flesch fällt nicht
#      unter die importierte Publish-Schwelle, und die Änderung führt keine
#      NEUEN harten Verständnis-Regeln ein – sonst wird sie verworfen
#      (fail-closed, Beleg: scripts/publikations_vertrag.py)
#    - Idempotenz: nach der Heilung sind die Detektoren grün
#  Selbsttest (eingefrorene Fälle) schützt die Detektoren selbst:
#  Exit 2 = Sabotage an der Wache → CI bricht ab.
#
#  Report: REDAKTIONS-STANDARD-REPORT.md
#  Historie: data/redaktions_standard_history.jsonl
# ============================================================

import datetime
import hashlib
import json
import os
import re
import sys
import unicodedata

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

from post_utils import (list_post_paths, slug_of,  # noqa: E402
                        join_article, strip_generator_scaffolding)
import llm_client  # noqa: E402
import sprachkern  # noqa: E402

# YMYL-Schutz (Premium-Fix #613): Hochrisiko-Artikel mit gültigem Siegel
# dürfen nicht von der KI-Heilung umgeschrieben werden – sonst bricht das
# Siegel (E17) und die verankerten Aussagen/Zahlen (E13/E18/E19). Die Wache
# prüft das vor jeder Schreiboperation.
try:  # noqa: E402
    import editorial_review_gate as _ymyl_gate
    _YMYL_AVAILABLE = True
except Exception:  # noqa: BLE001
    _ymyl_gate = None
    _YMYL_AVAILABLE = False


def _is_ymyl_sealed(path: str) -> bool:
    """Auch abgelaufene/beschädigte Freigaben bleiben schreibgeschützt."""
    if not _YMYL_AVAILABLE or _ymyl_gate is None:
        return True  # Ohne Messung keine automatische Änderung.
    return _ymyl_gate.automatic_write_protected(path)


# PUBLIKATIONS-VERTRAG (Vorgang WF-54C4/#607, 07.10.2026): Die KI-Heilung
# prüfte bisher nur die STRUKTUR ihrer Änderung (Links, H2-Anzahl, Länge,
# Trennlinien) – nicht die Regeln, die über die Veröffentlichung entscheiden.
# Am 05.10.2026 schrieb sie Flesch 44,3 und die Intro-Formel „In diesem
# Beitrag…“ in einen Live-Artikel; blockiert hat das erst der nächste
# Deploy-Lauf (Exit 1, roter Produktionsalarm). Ab jetzt gilt: Kein
# KI-Text geht raus, der die Veröffentlichungsschwelle reißt oder neue harte
# Verständnis-Funde einführt. Ohne prüfbaren Vertrag wird nicht geschrieben.
try:  # noqa: E402
    from publikations_vertrag import pruefe as _vertrag_pruefe, verstoesse_kurz
    _VERTRAG_FEHLER = ""
except Exception as exc:  # noqa: BLE001 – ohne Vertrag KEINE KI-Änderung
    _vertrag_pruefe = None
    verstoesse_kurz = None
    _VERTRAG_FEHLER = f"{exc.__class__.__name__}: {exc}"

REPORT = os.path.join(BLOG_DIR, "REDAKTIONS-STANDARD-REPORT.md")
HISTORY = os.path.join(BLOG_DIR, "data", "redaktions_standard_history.jsonl")
KORREKTUR_LOG = os.path.join(BLOG_DIR, "data", "korrekturen.yaml")

DO_FIX = "--fix" in sys.argv
DO_AI = "--ai" in sys.argv
DO_GATE = "--gate" in sys.argv
# Nur die Einzigartigkeits-Klasse heilen (Issue #766): RS7/RS2 bleiben dem
# Tageslauf überlassen, wenn genau EINE Klasse repariert werden soll.
NUR_FAUSTREGEL = "--nur-faustregel" in sys.argv
NEW_ONLY = "--new-only" in sys.argv
DRY_RUN = "--dry-run" in sys.argv
INCLUDE_DRAFTS = "--include-drafts" in sys.argv
SINGLE_FILE = (sys.argv[sys.argv.index("--file") + 1]
               if "--file" in sys.argv and sys.argv.index("--file") + 1 < len(sys.argv)
               else "")

# ---------------------------------------------------------------------------
# HEDGE-MARKER (RS5): Wörter, die eine Zahl einordnen (WiWo-Verifikation).
# ---------------------------------------------------------------------------
HEDGE = [
    "ca", "circa", "rund", "etwa", "ungefähr", "schätzungsweise", "knapp",
    "gut", "mindestens", "höchstens", "mehr als", "weniger als", "fast",
    "beinahe", "in der regel", "durchschnittlich", "im schnitt",
    "im durchschnitt", "laut", "lt", "stand", "je nach", "typischerweise",
    "meist", "oft", "häufig", "bis zu", "zwischen", "von ... bis",
    "erfahrungsgemäß", "üblich", "im mittel", "median", "spannweite",
    "beispiel", "beispielhaft", "modellrechnung", "rechenbeispiel",
]

# Phantom-Quellen (RS6): Formulierungen, die eine nicht verifizierbare
# Quelle behaupten. Ein Bot darf solche Aussagen nicht erfinden.
PHANTOM_QUELLEN = [
    r"laut einer (aktuellen |neuen |jüngsten )?studie",
    r"einer (aktuellen |neuen )?studie zufolge",
    r"wie eine (aktuelle )?studie (zeigt|belegt|ergab|feststellte)",
    r"studien (zeigen|belegen|ergaben)",
    r"laut einer umfrage", r"einer umfrage zufolge", r"umfragen (zeigen|belegen)",
    r"laut experten", r"experten zufolge", r"experten (sagen|raten|empfehlen|schätzen)",
    r"wissenschaftler haben (herausgefunden|festgestellt|ermittelt)",
    r"forscher haben (herausgefunden|festgestellt|ermittelt)",
    r"laut forschern", r"laut einer auswertung", r"laut statistiken",
    r"statistiken (zeigen|belegen)", r"eine aktuelle untersuchung (zeigt|belegt)",
    r"laut einer untersuchung", r"einer untersuchung zufolge",
    r"fachleute (raten|empfehlen|schätzen)", r"marktforscher (haben|gehen)",
    r"laut einer erhebung", r"einer erhebung zufolge",
]

# Erfahrung ist optional. Eine Automatik darf weder Eigenpraxis erfinden noch
# ein Belegfeld ergänzen; vorhandene Erfahrungsangaben brauchen eine Referenz
# ins öffentliche Beweis-Register.


# ---------------------------------------------------------------------------
# Artikel laden
# ---------------------------------------------------------------------------

def load_article(path, include_drafts=False):
    try:
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
    except Exception:
        return None
    parts = content.split("---", 2)
    if len(parts) != 3:
        return None
    fm, body = parts[1], parts[2]
    if not (include_drafts or INCLUDE_DRAFTS) and "draft: true" in fm:
        return None

    def get(key):
        m = re.search(rf"^{key}:\s*(.+?)\s*$", fm, re.M)
        return m.group(1).strip().strip("\"'") if m else ""

    return {
        "path": path,
        "slug": slug_of(path),
        "fm": fm,
        "body": body,
        "title": get("title"),
        "description": get("description"),
        "kurzantwort": get("kurzantwort"),
        "erfahrung": get("erfahrung"),
        "erfahrung_beleg": get("erfahrung_beleg"),
        "author": get("author"),
        "korrektur": get("korrektur"),
        "date": get("date")[:10],
    }


def fm_field(fm, key):
    m = re.search(rf"^{key}:\s*(.+?)\s*$", fm, re.M)
    return m.group(1).strip() if m else None


def set_fm_field(fm, key, value, quote=True):
    """Setzt/ersetzt ein Frontmatter-Feld (sicher quotiert)."""
    v = value.replace("\\", "\\\\").replace('"', '\\"') if quote else value
    v = f'"{v}"' if quote else v
    if fm_field(fm, key) is not None:
        return re.sub(rf"^{key}:.*$", f"{key}: {v}", fm, count=1, flags=re.M)
    return fm.rstrip() + f"\n{key}: {v}\n"


# ---------------------------------------------------------------------------
# Detektoren RS1–RS8 (reine Funktionen → selbsttestbar)
# ---------------------------------------------------------------------------

def h2_lines(body):
    return [ln[3:].strip() for ln in body.splitlines() if ln.startswith("## ")]


def detect_rs1(body):
    """RS1: „Das Wichtigste in Kürze“-Box mit ≥ 3 Bullets. → (ok, details)"""
    m = re.search(r"\*\*Das Wichtigste in Kürze\*\*|#{2,4}\s*Das Wichtigste in Kürze",
                  body, re.I)
    if not m:
        return False, "kein „Das Wichtigste in Kürze“-Modul"
    window = body[m.end():m.end() + 400]
    bullets = len(re.findall(r"^\s*[-*•]\s+", window, re.M))
    if bullets < 3:
        return False, f"nur {bullets} Bullet-Punkte in der Kürze-Box"
    return True, f"{bullets} Bullets"


def detect_rs2(body):
    """RS2: ≥ 2 Frage-Überschriften (H2). → (ok, details)"""
    h2s = h2_lines(body)
    fragen = [h for h in h2s if h.rstrip().endswith("?")]
    if len(fragen) < 2:
        return False, f"nur {len(fragen)} Frage-H2 von {len(h2s)} H2 (Standard: ≥ 2)"
    return True, f"{len(fragen)} Frage-H2"


def detect_rs3(body):
    """RS3: ≥ 1 markierte Faustregel mit Satzinhalt. → (ok, details)"""
    lines = (body or "").splitlines()
    marker = re.compile(
        r"^\s*(?:>\s*)?\*\*[^*\n]*\bfaustregel\b[^*\n]*:\*\*\s*(.*)$",
        re.I,
    )
    n = 0
    for idx, line in enumerate(lines):
        match = marker.match(line)
        if not match:
            continue
        content = match.group(1).strip()
        if not content:
            # Support an intentionally wrapped blockquote marker while still
            # requiring real Faustregel copy (a bare word is not the module).
            for following in lines[idx + 1:]:
                content = re.sub(r"^\s*>\s?", "", following).strip()
                if content:
                    break
        if re.search(r"\w", content, re.UNICODE):
            n += 1
    if n < 1:
        return False, "keine markierte Faustregel mit Satzinhalt"
    return True, f"{n} markierte Faustregel(n)"


def detect_rs4(body):
    """RS4: nummerierte Schrittfolge ≥ 3 ODER ≥ 2 „Schritt“-Überschriften."""
    numbered = [ln for ln in body.splitlines()
                if re.match(r"^\s*\d+\.\s+\S", ln)]
    if len(numbered) >= 3:
        return True, f"nummerierte Liste ({len(numbered)} Schritte)"
    schritt_h = [ln for ln in body.splitlines()
                 if ln.startswith("#") and re.search(r"\bschritt\b", ln, re.I)]
    if len(schritt_h) >= 2:
        return True, f"{len(schritt_h)} Schritt-Überschriften"
    return False, f"weder Schrittfolge ({len(numbered)} nummerierte Zeilen) noch Schritt-Überschriften ({len(schritt_h)})"


def _satz_liste(body):
    """Fließtext-Sätze: ohne Markdown-Syntax, ohne Tabellenzeilen,
    ohne Überschriften, ohne Links, ohne Listen-Marker. → [(index, satz)]"""
    lines = []
    for ln in body.splitlines():
        s = ln.strip()
        if not s or s.startswith(("|", "#", ">", "!")):
            continue
        if re.match(r"^\s*[-*•]\s", ln) and "€" not in s and "%" not in s:
            continue
        # Listen-Marker (1. / 1) / - / *) entfernen, damit keine
        # Marker-Fragmente als "Sätze" analysiert werden
        s = re.sub(r"^\s*(?:\d+[.)]|[-*•])\s*", "", s)
        lines.append(s)
    text = re.sub(r"\[[^\]]*\]\([^)]*\)", " ", "\n".join(lines))
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"[*_`~]", "", text)
    saetze = re.split(r"(?<=[.!?])\s+", text)
    return [(i, s.strip()) for i, s in enumerate(saetze) if len(s.split()) >= 6]


def detect_rs5(body):
    """RS5: harte Zahlen (≥3 Stellen, €, %) ohne Einordnung im selben Satz.
    → (ok, [satz-beispiele])"""
    zahlen = re.compile(
        r"(?<!\w)(?:\d{3,}(?:[.,]\d+)?|\d+[.,]\d{3}|\d+\s*(?:€|EUR)|\d+[\d.,]*\s*%)(?!\w)")
    funde = []
    for _i, s in _satz_liste(body):
        if not zahlen.search(s):
            continue
        low = s.lower()
        if any(h in low for h in HEDGE):
            continue
        # „über 160 €“ / „unter 30 %“ = grobe Grenze, keine harte Zahl
        if re.search(r"\b(?:über|unter)\s+\d", low):
            continue
        # Bereiche wie „45–55 %“ oder „20 bis 40 Euro“ sind Spannen
        if re.search(r"\d+\s*[–-]\s*\d+", s) or re.search(r"\d+\s+bis\s+\d+", low):
            continue
        # Rechenbeispiel-Kennzeichnung zählt als Einordnung
        if "rechenbeispiel" in low or "beispiel" in low:
            continue
        funde.append(s)
    return (len(funde) == 0, funde[:3], len(funde))


def detect_rs6(body):
    """RS6: Phantom-Quellen (erfundene Studien/Umfragen/Experten)."""
    low = body.lower()
    funde = []
    for pat in PHANTOM_QUELLEN:
        for m in re.finditer(pat, low):
            start = max(0, m.start() - 60)
            funde.append(body[start:m.end() + 60].replace("\n", " ").strip())
    return (len(funde) == 0, funde[:3], len(funde))


def detect_rs7(a):
    """RS7: Autor Pflicht; persönliche Erfahrung nur mit Eigenbeleg."""
    if not a.get("author"):
        return False, "fehlt: author"
    if a.get("erfahrung") and not a.get("erfahrung_beleg"):
        return False, "erfahrung ohne erfahrung_beleg (keine automatische Schein-Evidenz)"
    return True, "author vorhanden; Erfahrung fehlt ehrlich oder ist belegt"


def _reserve_numeric_claim_findings(body):
    """Find numbers that lack a sentence-level source or explicit model basis.

    A hedge such as “about” is not evidence. Reserve copy needs a clickable
    source in the same sentence for external figures; calculations need to be
    clearly marked as a model with stated assumptions. Legal sections always
    require a source link.
    """
    link_re = re.compile(r"\[([^\]]+)\]\(\s*([^)\s]+)[^)]*\)", re.I)
    text = re.sub(r"```.*?```", " ", body or "", flags=re.S)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    # MESSFEHLER, nicht Defekt (WF-D4E0/#821, 25.10.2026): Formatierungs- und
    # Repo-Marker sind keine Zahlenbehauptungen. Vorher zerschnitt ein
    # Fett-Marker einen Satz („… **16. Oktober 2026**." → Fragment „Oktober
    # 2026**.") und eine Issue-Nummer (`#763`) wurde als harte Zahl gezählt.
    # Am 25.10.2026 trug der blockierte Pool-Kandidat dadurch „RS5: 9 …“,
    # obwohl nur 5 Sätze echte Zahlen tragen – der Befund log über sich selbst.
    text = re.sub(r"[*_]{1,3}", "", text)
    text = re.sub(r"(?<![\w&])#\d+", " ", text)
    # Strip internal links so year-bearing slugs are not claims. External
    # Markdown links leave a marker that proves sentence-level evidence.
    def _link_marker(match):
        target = match.group(2).strip().lower()
        return " QUELLENLINK " if target.startswith(("https://", "http://")) else " INTERNLINK "
    text = link_re.sub(_link_marker, text)
    number_words = (
        r"zwei|drei|vier|f[uü]nf|sechs|sieben|acht|"
        r"neun|zehn|elf|zw[oö]lf|dreizehn|vierzehn|f[uü]nfzehn|"
        r"sechzehn|siebzehn|achtzehn|neunzehn|zwanzig|drei[ßs]ig|"
        r"vierzig|f[uü]nfzig|sechzig|siebzig|achtzig|neunzig|"
        r"(?<!mehrere\s)(?<!einige\s)(?<!paar\s)"
        r"(?:(?:ein|zwei|drei|vier|f[uü]nf|sechs|sieben|acht|neun)?(?:hundert|tausend)"
        r"(?:und)?(?:ein|zwei|drei|vier|f[uü]nf|sechs|sieben|acht|neun|zehn|elf|zw[oö]lf|"
        r"dreizehn|vierzehn|f[uü]nfzehn|sechzehn|siebzehn|achtzehn|neunzehn|"
        r"zwanzig|drei[ßs]ig|vierzig|f[uü]nfzig|sechzig|siebzig|achtzig|neunzig)?)"
    )
    hard_units = (
        r"€|eur\b|euro\b|cent\b|ct\b|%|prozent\b|kwh\b|wh\b|mwh\b|"
        r"kilowattstunden?\b|wattstunden?\b|watt\b|(?<![a-z])w\b|"
        r"kw\b|kilowatt\b|mbit/s\b|gbit/s\b|gb\b|mb\b|"
        r"kilometer\b|km\b|meter\b"
    )
    time_units = r"tage?n?\b|wochen?\b|monate?n?\b|jahre?n?\b|stunden?\b|minuten?\b"
    # 25.10.2026 KONVERGENZ (WF-D4E0 #821 + #865/#867): Eine freistehende
    # Frist OHNE Beleg bleibt hart („Drei Monate reichen zum Prüfen nicht."
    # muss rot bleiben – Vertragstest „test_echte_unbelegte_zahl_bleibt_rot").
    # Der frühere Kontext-Gate (nur Vermögens-Vokabular) wurde entfernt: Er
    # machte dieselbe Frist je nach Nachbarsatz grün – eine Wache, die ihre
    # Schutzrichtung vom Wortschatz des Satzes abhängig machte.
    hard_numeric_claim = re.compile(
        rf"(?ix)(?:§\s*\d+[a-z]?\b|"
        rf"(?<!\w)(?:\d[\d.,]*|{number_words})\s*(?:{hard_units})(?!\w)|"
        rf"(?<![#\w])(?!(?:19|20)\d{{2}}\b)\d{{3,}}(?:[.,]\d+)*(?!\w))"
    )
    time_numeric_claim = re.compile(
        rf"(?ix)(?<!\w)(?:\d[\d.,]*|{number_words})\s*(?:{time_units})(?!\w)"
    )
    model_marker = re.compile(
        r"\b(?:rechenbeispiel\w*|modellrechnung\w*|modellannahme\w*|modellfall\w*|"
        r"modellwert\w*|rechenfall\w*|annahme|annahmen|musterrechnung\w*|"
        r"beispielrechnung\w*|beispielwert\w*|orientierungswert\w*|faustregel|"
        r"rechnerisch|angenommen|unterstellen wir|nehmen wir an|wir nehmen an|"
        r"in diesem beispiel|für das beispiel|zum beispiel|beispielsweise|"
        r"als orientierung|orientierung\s*:)\b",
        re.I,
    )
    ordinal_date_re = re.compile(
        r"\b(\d{1,2})\.\s+(Januar|Februar|März|April|Mai|Juni|Juli|August|"
        r"September|Oktober|November|Dezember)\b"
    )
    abbrev_re = re.compile(
        r"\b(ca|bzw|usw|ggf|inkl|mind|max|vgl|nr|abs)\.", re.I
    )

    # Eine Kalenderjahreszahl („im Jahr 2026", „für 2026") ist keine
    # Zahlenbehauptung – sie nennt keinen Betrag, keine Menge, keinen Preis.
    # Erst wenn nach dem Entfernen der Jahreszahlen noch eine Zahl mit Einheit
    # übrig bleibt, wird der Satz bewertet.
    jahr_re = re.compile(r"(?<!\w)(?:19|20)\d{2}(?!\w)")
    findings = []
    in_model_section = False
    section_model_numbers: set[str] = set()
    for raw_block in re.split(r"\n\s*\n", text):
        block = raw_block.strip()
        if not block:
            continue
        raw_lines = block.splitlines()
        content_lines = []
        for ln in raw_lines:
            s_ln = ln.lstrip()
            if not s_ln or s_ln.startswith(("<!--", ">", "|")):
                continue
            if s_ln.startswith("#"):
                if s_ln.startswith("## ") or s_ln.startswith("### "):
                    in_model_section = bool(model_marker.search(s_ln))
                    if not in_model_section:
                        section_model_numbers = set()
                    else:
                        section_model_numbers.update(re.findall(r"\d[\d.,]*", s_ln))
                continue
            content_lines.append(ln)
        if not content_lines:
            continue
        para_text = re.sub(r"\s+", " ", " ".join(content_lines))
        para_text = ordinal_date_re.sub(r"\1_ORD_ \2", para_text)
        para_text = abbrev_re.sub(r"\1_ABBR_", para_text)
        para_model_active = in_model_section
        for sentence in re.split(r"(?<=[.!?])\s+", para_text):
            sentence = sentence.strip().replace("_ORD_", ".").replace("_ABBR_", ".")
            if not sentence:
                continue
            if model_marker.search(sentence) and "§" not in sentence:
                para_model_active = True
                section_model_numbers.update(re.findall(r"\d[\d.,]*", sentence))
                continue
            ohne_jahr = jahr_re.sub(" ", sentence)
            has_hard = bool(hard_numeric_claim.search(ohne_jahr))
            has_time = bool(time_numeric_claim.search(ohne_jahr))
            if not (has_hard or has_time):
                continue
            if "QUELLENLINK" in sentence:
                continue
            # A model label must not disguise a statutory clause or a claimed study.
            if "§" not in sentence:
                if para_model_active:
                    continue
                nums = set(re.findall(r"\d[\d.,]*", sentence))
                if nums and section_model_numbers and nums.issubset(section_model_numbers):
                    continue
            findings.append(sentence[:240])
    return findings


def reserve_quality_findings(body, author=None, erfahrung=None,
                             erfahrung_beleg=None):
    """Strict editorial contract for reserve drafts and their generation.

    RS1–RS7, same-sentence evidence for numbers, phantom-source rejection,
    minimum substance and a calm H2 structure are hard requirements. A high
    average score or a successful render cannot compensate for these blockers.
    """
    body = body or ""
    findings = []
    for code, detector in (("RS1", detect_rs1), ("RS2", detect_rs2),
                           ("RS3", detect_rs3), ("RS4", detect_rs4)):
        ok, detail = detector(body)
        if not ok:
            findings.append(f"{code}: {detail}")
    if author is not None:
        rs7_ok, rs7_detail = detect_rs7({
            "author": author, "erfahrung": erfahrung,
            "erfahrung_beleg": erfahrung_beleg})
        if not rs7_ok:
            findings.append(f"RS7: {rs7_detail}")

    rs5_ok, _rs5_examples, _rs5_count = detect_rs5(body)
    ungrounded = _reserve_numeric_claim_findings(body)
    if ungrounded:
        findings.append(
            f"RS5: {len(ungrounded)} Zahlenbehauptung(en) ohne Satzbeleg "
            f"oder klare Modellannahme: {ungrounded[0]}")
    # The stricter sentence-level source/model rule supersedes RS5's softer
    # hedge test: a cited claim is stronger evidence than “ca.” or “rund”.
    _ = rs5_ok

    rs6_ok, rs6_examples, rs6_count = detect_rs6(body)
    if not rs6_ok:
        findings.append(
            f"RS6: {rs6_count} Phantomquelle(n): "
            f"{rs6_examples[0] if rs6_examples else 'Fund ohne Textbeispiel'}")

    words = len(re.findall(r"\w+", body))
    chars = len(re.sub(r"\s+", " ", body).strip())
    if words < 1400 or chars < 10000:
        findings.append(
            f"Umfang: {words} Wörter / {chars} Zeichen; Premium verlangt "
            "mindestens 1.400 Wörter und 10.000 Zeichen")
    h2 = re.findall(r"^##\s+(.+?)\s*$", body, re.M)
    if len(h2) < 5:
        findings.append(f"Struktur: nur {len(h2)} H2-Abschnitte (Minimum 5)")
    if len(h2) > 16:
        findings.append(
            f"Struktur: {len(h2)} H2-Abschnitte (Maximum 16; keine "
            "Abschnittszerstückelung)")
    normalized = [re.sub(
        r"[^\w]+", " ", unicodedata.normalize("NFKC", heading).casefold()).strip()
        for heading in h2]
    duplicate_headings = sorted({heading for heading in normalized
                                 if heading and normalized.count(heading) > 1})
    if duplicate_headings:
        findings.append("Struktur: doppelte H2-Überschrift(en): "
                         + ", ".join(duplicate_headings[:3]))
    faq_count = len(re.findall(r"^###\s+[^\n]*\?\s*$", body, re.M))
    if faq_count < 4:
        findings.append(f"FAQ: nur {faq_count} Fragen (Premium verlangt 4)")
    return findings


def analyse_article(a):
    """Gesamt-Befund eines Artikels. → dict mit allen RS-Ergebnissen."""
    body = a["body"]
    r1, d1 = detect_rs1(body)
    r2, d2 = detect_rs2(body)
    r3, d3 = detect_rs3(body)
    r4, d4 = detect_rs4(body)
    r5, b5, n5 = detect_rs5(body)
    r6, b6, n6 = detect_rs6(body)
    r7, d7 = detect_rs7(a)
    hart = [k for k, ok in (("RS1", r1), ("RS2", r2), ("RS3", r3),
                            ("RS4", r4), ("RS7", r7)) if not ok]
    return {
        "slug": a["slug"], "title": a["title"], "path": a["path"],
        "rs1": (r1, d1), "rs2": (r2, d2), "rs3": (r3, d3), "rs4": (r4, d4),
        "rs5": (r5, b5, n5), "rs6": (r6, b6, n6), "rs7": (r7, d7),
        "hart_missing": hart,
    }


# ---------------------------------------------------------------------------
# Deterministische Heilung (RS7) – sicher, idempotent
# ---------------------------------------------------------------------------

def fix_rs7(path, a):
    """Ergänzt nur den Autor; Erfahrung/Eigenbeleg sind niemals Auto-Felder."""
    if a.get("author"):
        return None
    fm = set_fm_field(a["fm"], "author", "Frank Hartung")
    with open(path, encoding="utf-8") as fh:
        content = fh.read()
    parts = content.split("---", 2)
    return join_article(fm, parts[2], parts[0])


_QUESTION_STARTS = (
    "warum ", "wie ", "was ", "wann ", "welche ", "welcher ", "welches ",
    "wo ", "worauf ", "wer ", "wieso ", "weshalb ", "ab wann ", "für wen ",
)


# ===========================================================================
#  RS3-EINZIGARTIGKEIT (Issue #766, 15.10.2026)
#  ---------------------------------------------------------------
#  BEFUND. Der deterministische RS3-Heiler unten schrieb EINEN Satz in jedes
#  Artikel-Loch, dem die Pflicht-Faustregel fehlte:
#
#      „Prüfe vor jeder Entscheidung zuerst die Gesamtkosten über die volle
#       Laufzeit und vergleiche mindestens zwei aktuelle Alternativen, bevor
#       du dich vertraglich festlegst.“
#
#  Am 15.10.2026 trugen ihn 30 live auslieferbare Artikel. Ein Satz dieser
#  Länge sind 21 Sieben-Wort-Phrasen – das Tagesaudit zählte daraus
#  C(30,2) = 435 „kritische“ Paare bei 30 beteiligten Artikeln. Der Befund
#  war kein Redaktionsfehler, sondern ein Heiler, der nur die REGEL kannte
#  („es muss eine Faustregel geben“) und nicht die MESSUNG („und sie darf
#  sich nicht gleichen“).
#
#  DAUERHEILUNG. Die Regel bleibt, der Satz wird zur WAHL:
#    · `FAUSTREGEL_POOL` – eigenständige, themenbezogene Faustregeln
#      (zahlfrei, damit RS5 sie nicht bewerten muss; ohne Anspruch auf
#      Belege, weil sie keine Tatsachen behaupten).
#    · `waehle_faustregel()` – wählt deterministisch (stabiler Hash je Slug,
#      nie Zufall) UND misst dabei mit DERSELBEN Messregel wie das
#      Einzigartigkeits-Audit (`check_uniqueness`: clean_body + 7-Gramme +
#      KRITISCH_AB): keiner der beiden Sätze, die ein Lauf in zwei Artikel
#      schreibt, darf den Bestand über die Schwelle heben. Findet der Wähler
#      keinen freien Satz, wird NICHTS geschrieben und der Grund gemeldet –
#      lieber eine offene Faustregel als ein neuer Massensatz (#714-Lehre:
#      grüner Schreiber, roter Nachlauf ist die teuerste Bauart dieses Repos).
#    · `ersetze_generische_faustregel()` – derselbe Heiler räumt den
#      Altbestand auf: Er erkennt den eingefrorenen Satz wieder (tolerant
#      gegen Typografie) und ersetzt ihn durch eine freie, themenpassende
#      Faustregel. Idempotent: danach findet er nichts mehr.
#
#  Der alte Satz bleibt als Konstante erhalten – nicht als Vorlage, sondern
#  als Suchmuster für den Heiler und als eingefrorener Selbsttest-Fall: Er
#  darf NIE wieder als „neuer“ Satz vergeben werden.
# ===========================================================================
FAUSTREGEL_MARKER = "**Faustregel:**"

FAUSTREGEL_LEGACY = (
    "Prüfe vor jeder Entscheidung zuerst die Gesamtkosten über die volle "
    "Laufzeit und vergleiche mindestens zwei aktuelle Alternativen, bevor "
    "du dich vertraglich festlegst."
)

# (thema, satz, stichwörter) – Stichwörter steuern die Themenwahl, nicht die
# Messung. Alle Sätze sind zahlfrei (RS5) und behaupten keine Tatsachen
# (RS6); sie sind Rat, keine Quelle.
FAUSTREGEL_POOL: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("laufzeit",
     "Wer Laufzeit und Kündigungsfrist vor dem Abschluss kennt, zahlt "
     "seltener für einen Vertrag, den er längst nicht mehr nutzt.",
     ("vertrag", "laufzeit", "kuendigung", "kündigung", "tarif", "abonnement",
      "abo", "verlängerung", "verlaengerung")),
    ("gesamtpreis",
     "Rechne jedes Angebot auf den Gesamtpreis um, bevor du unterschreibst; "
     "der beworbene Startpreis sagt wenig über das zweite Jahr.",
     ("wechselbonus", "rabatt", "cashback", "startpreis", "neukunde",
      "geschenk", "aktion", "sonderangebot")),
    ("vertragscheck",
     "Prüfe deine Verträge einmal im Jahr auf denselben drei Zeilen: Preis, "
     "Laufzeit, Kündigungsfrist.",
     ("fixkosten", "haushaltsplan", "budget", "dauerauftrag", "lastschrift",
      "abbuchung", "vertrag")),
    ("verbrauch",
     "Miss den Verbrauch, bevor du den Tarif wechselst; die größere Ersparnis "
     "sitzt meist nicht im Preis, sondern im Verbrauch.",
     ("strom", "gas", "verbrauch", "kwh", "tarif", "energie", "strompreis")),
    ("zaehlerstand",
     "Wer den Zählerstand regelmäßig notiert, erkennt teure Ausreißer, bevor "
     "die Jahresabrechnung sie erklärt.",
     ("zaehler", "zähler", "ablesen", "abrechnung", "nachzahlung",
      "abschlag", "schaetzung", "schätzung")),
    ("heizung",
     "Senke die Heizkosten in dieser Reihenfolge: erst Verbrauch verstehen, "
     "dann Tarif prüfen, erst zuletzt Technik kaufen.",
     ("heizung", "heizkosten", "waerme", "wärme", "gasheizung", "heizkoerper",
      "heizkörper", "warmwasser", "daemmung", "dämmung")),
    ("deckung",
     "Versicherungen gehören bei jedem Umzug auf den Tisch: Deckung, "
     "Selbstbeteiligung, Ausschlüsse – in dieser Reihenfolge.",
     ("versicherung", "haftpflicht", "kasko", "police", "beitrag",
      "versicherungsschutz")),
    ("kontofuehrung",
     "Ein Konto ohne Bedingungen ist selten wirklich kostenlos; vergleiche "
     "Gebühren, Verfügbarkeit und Zinsstaffel zusammen.",
     ("konto", "girokonto", "karte", "gebuehr", "gebühr", "dispo", "bank",
      "zinsen")),
    ("fixkosten",
     "Trag einmal im Monat alle Fixkosten in eine Liste ein; was du schwarz "
     "auf weiß siehst, kannst du verhandeln.",
     ("fixkosten", "haushalt", "monatskosten", "ausgaben", "budget",
      "einnahmen")),
    ("verzicht",
     "Spare zuerst dort, wo du dich nicht einschränkst: Verträge, Gebühren "
     "und Doppelkäufe kosten mehr als der tägliche Kaffee.",
     ("sparen", "spartipp", "frugalismus", "verzicht", "geld sparen",
      "alltag")),
    ("leistung",
     "Vergleiche nie den Preis allein, sondern den Preis für die Leistung, "
     "die du tatsächlich nutzt.",
     ("vergleich", "vergleichen", "anbieter", "test", "bewertung", "qualitaet",
      "qualität")),
    ("ruecklage",
     "Eine Rücklage in Höhe weniger Monatsausgaben verhindert mehr Kosten als "
     "jede Jagd nach der besten Rendite.",
     ("notgroschen", "ruecklage", "rücklage", "geldanlage", "etf", "tagesgeld",
      "sparplan")),
    ("standby",
     "Geräte, die dauerhaft Strom ziehen, gehören an eine schaltbare Leiste "
     "oder ganz aus der Wohnung.",
     ("standby", "stromfresser", "geraet", "gerät", "haushaltsgeraete",
      "haushaltsgeräte", "kuehlschrank", "kühlschrank")),
    ("reisekosten",
     "Bei Reisekosten entscheiden die Nebenkosten öfter als der beworbene "
     "Preis: Kaution, Umrechnung und Zusatzfahrer gehören in den Vergleich.",
     ("urlaub", "reise", "mietwagen", "kaution", "ausland", "flug",
      "hotel")),
    ("abos",
     "Kündige, was du nicht mehr nutzt, bevor du nach neuen Angeboten "
     "suchst; der günstigste Tarif bleibt teuer, wenn er ungenutzt läuft.",
     ("abo", "abos", "mitgliedschaft", "kuendigen", "kündigen", "newsletter",
      "streaming", "unnoetig", "unnötig")),
    # --- zweite Reihe (15.10.2026): Der Altbestand allein brauchte 30 Sätze.
    # Ein Pool, der nur für den Anlass reicht, wäre der nächste Dauerläufer.
    ("eigene-rechnung",
     "Ein Tarifvergleich ohne die eigene Rechnung bleibt Bauchgefühl; leg "
     "beide Zahlen nebeneinander, bevor du wechselst.",
     ("strompreis", "tarif", "wechseln", "anbieter", "vergleich")),
    ("vertragsende",
     "Notiere das Vertragsende dort, wo du montags hinsiehst; verpasste "
     "Fristen kosten mehr als jeder Preisunterschied.",
     ("frist", "kuendigungsfrist", "kündigungsfrist", "vertragsende",
      "verlaengerung", "verlängerung", "laufzeit")),
    ("policen-check",
     "Ein Beitrag steigt leiser als ein Tarif: Prüfe einmal im Jahr, ob deine "
     "Police noch zu deinem Leben passt.",
     ("versicherung", "beitrag", "police", "versicherungsbeitrag")),
    ("bindung",
     "Zinsen sind kein Geschenk, sondern der Preis für deine Bindung; "
     "entscheide erst die Bindung, dann den Zins.",
     ("zinsen", "tagesgeld", "festgeld", "anlage", "einlagen")),
    ("raten",
     "Vor jeder Ratenzahlung gehört der Gesamtbetrag auf den Tisch: Zins, "
     "Gebühren und Laufzeit zusammen.",
     ("kredit", "rate", "finanzierung", "dispo", "ratenzahlung")),
    ("umzug",
     "Ein Umzug ist der beste Moment für den Vertragscheck: Was du jetzt "
     "nicht kündigst, zahlst du auch am neuen Ort.",
     ("umzug", "wohnung", "miete", "mietvertrag")),
    ("rechnung",
     "Lies eine Rechnung einmal mit dem Taschenrechner; was du nachrechnest, "
     "korrigiert der Anbieter schneller als du denkst.",
     ("rechnung", "abrechnung", "nachzahlung", "abschlag")),
    ("festes-budget",
     "Jeder Euro ohne festen Platz wird im Monat ausgegeben; ein schriftliches "
     "Budget macht den Rest sichtbar.",
     ("budget", "haushalt", "ausgaben", "monatskosten", "planung")),
    ("kaufpause",
     "Zwischen Wunsch und Kauf gehört eine Nacht Bedenkzeit; wer wartet, "
     "bestellt seltener doppelt.",
     ("kauf", "anschaffung", "konsum", "bestellen", "shopping")),
    ("kalender",
     "Abos verlängern sich von selbst, deine Kündigung nicht: Der Kalender "
     "ist die wirksamste Sparmaßnahme.",
     ("abos", "abo", "streaming", "mitgliedschaft", "kalender")),
    ("erst-messen",
     "Erst messen, dann investieren: Jede Effizienz-Ausgabe ohne "
     "Verbrauchsdaten zahlt sich später aus – oder nie.",
     ("effizienz", "sanierung", "investition", "waermepumpe", "wärmepumpe",
      "daemmung", "dämmung")),
    ("sparziel",
     "Ein Sparziel ohne Endbetrag bleibt ein Vorsatz; nenne Summe und Termin, "
     "dann trägt der Plan sich selbst.",
     ("sparziel", "sparen", "vorsatz", "ziel", "sparplan")),
    ("leistung-zuerst",
     "Vergleiche zuerst die Leistung, dann den Preis; ein fehlender Baustein "
     "kostet später mehr als der Aufpreis heute.",
     ("vergleich", "preisvergleich", "angebot", "leistung", "tarif")),
    ("selbstbeteiligung",
     "Eine Selbstbeteiligung senkt den Beitrag und erhöht dein Risiko; "
     "entscheide nach dem Betrag, den du im Zweifel zahlen kannst.",
     ("selbstbeteiligung", "beitrag", "risiko", "versicherung", "kasko")),
    ("belege",
     "Belege gehören ins Ablagefach, nicht in die Schublade: Ohne Nachweis "
     "holt keine Erstattung Geld zurück.",
     ("steuer", "beleg", "erstattung", "werbungskosten", "unterlagen")),
    ("bindung-dauer",
     "Eine lange Bindung will begründet sein; prüfe vorher, wie sich dein "
     "Bedarf in dieser Zeit ändern kann.",
     ("laufzeit", "bindung", "vertragslaufzeit", "verlaengerung",
      "verlängerung")),
    ("zahlungsart",
     "Die Zahlungsart entscheidet mit: Gebühren, Umrechnung und "
     "Abbuchungsrhythmus gehören in denselben Vergleich.",
     ("zahlung", "kreditkarte", "abbuchung", "gebuehren", "gebühren",
      "umrechnung")),
    # --- dritte Reihe (15.10.2026): Vorrat statt Engpass. Wer nur so viele
    # Sätze schreibt, wie der Anlass braucht, plant den nächsten Stillstand
    # (der Heiler schreibt dann NICHTS – fail-closed). Der Selbsttest prüft
    # die Paar-Distanz über ALLE Reihen.
    ("monatsbetrag",
     "Kleine Beträge summieren sich leiser als große: Der Monatsbetrag zeigt, "
     "was ein Vertrag wirklich kostet.",
     ("monatlich", "monatskosten", "kleinbetrag", "summe", "abo")),
    ("eigene-aufstellung",
     "Notiere eine Woche lang, was du ausgibst; erst die eigene Aufstellung "
     "schlägt jeden Spartipp.",
     ("ausgaben", "aufstellung", "haushaltsbuch", "spartipp", "alltag")),
    ("garantie",
     "Eine Garantie ist nur so viel wert wie ihre Laufzeit; prüfe, was nach "
     "dem Ende der Zusage gilt.",
     ("garantie", "preisgarantie", "zusage", "laufzeit", "gewaehrleistung",
      "gewährleistung")),
    ("wechseltermin",
     "Beim Wechsel zählt der Termin: Wer die Frist verpasst, zahlt ein "
     "weiteres Jahr zum alten Preis.",
     ("wechsel", "termin", "frist", "verlaengerung", "verlängerung")),
    ("toepfe",
     "Plane den Monat in feste Töpfe; Geld ohne Topf verschwindet zuerst.",
     ("budget", "planung", "haushaltsplan", "monat", "fixkosten")),
    ("doppelt-bezahlt",
     "Prüfe zuerst, was du doppelt bezahlst: Doppelte Ausgaben kosten mehr "
     "als jeder erhöhte Preis.",
     ("doppelt", "abos", "ausgaben", "pruefen", "prüfen", "vertraege",
      "verträge")),
    ("zahlungsziel",
     "Zahlungsziel und Zinsen gehören zusammen; eine Karte ohne Gebühren kann "
     "trotzdem teuer werden.",
     ("kreditkarte", "zinsen", "zahlungsziel", "gebuehren", "gebühren")),
    ("nachtverbrauch",
     "Ein zweiter Zähler lohnt nur, wenn dein Verbrauch wirklich in die Nacht "
     "wandert.",
     ("nachtstrom", "zaehler", "zähler", "doppeltarif", "verbrauch")),
    ("sicherung",
     "Prüfe die Sicherung, bevor du die Rendite prüfst; ein Zinsvorteil wiegt "
     "keine offene Frage auf.",
     ("einlagensicherung", "sicherung", "rendite", "zinsvorteil", "bank")),
    ("gleichmaessig",
     "Wer jeden Monat denselben Betrag zurücklegt, muss im Zweifel nicht "
     "entscheiden, was gerade wichtiger ist.",
     ("vorsorge", "sparplan", "ruecklage", "rücklage", "monatlich")),
    ("bedarf",
     "Ein Anschluss folgt dem Haushalt, nicht dem Angebot: Prüfe erst den "
     "Bedarf, dann den Tarif.",
     ("anschluss", "bedarf", "tarif", "haushalt", "dsl", "internet")),
    ("warmwasser",
     "Prüfe erst deinen Warmwasserverbrauch und die Nutzungsgewohnheiten; "
     "erst danach wählst du passende Spararmaturen.",
     ("warmwasser", "warmwasserverbrauch", "spararmatur", "duschkopf",
      "wasserhahn", "wassersparen")),
    ("rechter-zeitpunkt",
     "Der beste Zeitpunkt für den Heizungscheck ist der Sommer; im Winter "
     "zahlst du die Eile mit.",
     ("heizung", "heizungscheck", "winter", "sommer", "vorbereitung")),
)


# Themen-spezifische Relevanzhinweise (#776): Sie ordnen einen Artikel einem
# Themenkreis zu, sind aber niemals ausgehender Text. Die tatsächlich
# geschriebene Faustregel stammt ausschließlich aus dem mess- und
# kollisionsgeprüften 45-Satz-Pool oben. Präzise Themen stehen zuerst; breite
# Treffer stehen zuletzt. Ohne Treffer gibt es keinen erfundenen Fallback.
_THEMEN_FAUSTREGELN: list[tuple[tuple[str, ...], str]] = [
    # Spezifische Themen zuerst – damit eng umgrenzte Artikel nicht an einem
    # breiten Stichwort wie „vertrag" oder „internet" hängen bleiben.
    (("warmwasser", "wasserhahn", "wassersparen", "duschkopf"),
     "Prüfe vor der Anschaffung von Spararmaturen erst den tatsächlichen "
     "Warmwasserverbrauch pro Person im Haushalt – die Armatur amortisiert "
     "sich nur bei regelmäßigem Verbrauch."),
    (("zaehlerstand", "zählerstand", "ablesen", "schätzwert", "jahresverbrauch",
      "ablesung"),
     "Lies den Zähler vor jeder Abrechnung selbst ab und dokumentiere den "
     "Stand mit Datum – Schätzwerte weichen systematisch von deinem echten "
     "Verbrauch ab."),
    (("grosseinkauf", "bevorraten", "vorratskauf"),
     "Kauf nur so viel auf Vorrat, wie du innerhalb der Haltbarkeit sicher "
     "verbrauchst – ein Rabatt auf die Großpackung verliert seinen Wert im "
     "Mülleimer."),
    (("mietwagen", "kaution", "selbstbehalt", "tankregel"),
     "Vergleiche vor der Buchung Gesamtpreis, Tankregel, Selbstbehalt und "
     "Kaution gemeinsam – der niedrigste Tagespreis ist selten der günstigste "
     "Gesamtpreis."),
    (("last-minute", "last minute", "reiseschnäppchen", "urlaubsschnäppchen",
      "sommer-schnaepp", "sommer-schnäpp"),
     "Vergleiche vor der Buchung den Gesamtpreis aus Flug, Unterkunft, Gepäck, "
     "Transfer und Versicherung gemeinsam – der prozentuale Rabatt auf dem "
     "Banner sagt nichts über den Endpreis."),
    (("einlagensicherung", "guthaben geschützt"),
     "Verteile größere Guthaben auf mehrere Banken innerhalb des "
     "Einlagensicherungsfonds – die gesetzliche Sicherung gilt pro Kunde und "
     "pro Institut, nicht pro Kontotyp."),
    (("kreditkarte", "karte bezahlen"),
     "Prüfe vor der Wahl einer Kreditkarte Jahresgebühr, Auslandseinsatzentgelt "
     "und Teilzahlungszinsen zusammen – die vermeintlich kostenlose Karte "
     "wird teuer bei Revolving-Kredit."),
    (("geld abheben", "ausland gebühr", "gebühren im ausland", "abheben im ausland"),
     "Vergleiche vor einer Auslandsreise die Gebühren für Abhebung und "
     "Kartenzahlung deiner bestehenden Karten – der günstigste Reisekurs "
     "gewinnt nichts, wenn jede Abhebung fünf Euro kostet."),
    (("girokonto", "kontoführungsgebühr"),
     "Vergleiche vor der Kontoeröffnung die Jahreskosten inklusive Abhebe-, "
     "Karten- und Überweisungsgebühren – ein kostenloses Konto ist nicht "
     "günstig, wenn jede Leistung extra kostet."),
    (("abos", "abonnement", "stiller posten"),
     "Prüfe einmal im Quartal jede laufende Abbuchung auf deinem Kontoauszug – "
     "vergessene Abonnements summieren sich über Monate zu einem stillen "
     "Kostenblock."),
    (("umzug", "umziehen", "wohnungswechsel"),
     "Plane vor dem Umzug alle laufenden Verträge mindestens drei Monate im "
     "Voraus – Nachsendeauftrag, Versicherungen und Energieanbieter laufen "
     "sonst in die alte Wohnung weiter."),
    (("handy", "mobilfunk", "smartphone-tarif", "handytarif", "sim-karte"),
     "Prüfe vor einem Handytarif-Wechsel zuerst deinen echten Datenverbrauch "
     "der letzten drei Monate – eine großzügige Flatrate lohnt nicht, wenn "
     "du einen Bruchteil davon nutzt."),
    (("nachtstrom", "doppeltarif", "heizstrom"),
     "Prüfe vor einem Nachtstromtarif, ob sich genug Verbrauch in die "
     "Niedertarifzeit verlagern lässt – sonst zahlt du den höheren Grundpreis "
     "ohne echte Ersparnis."),
    (("standby", "stromfresser", "energiedieb"),
     "Miss den Verbrauch verdächtiger Geräte einzeln vor dem Kauf von "
     "Steckdosen-Adaptern – nur was dauerhaft läuft, kostet dich auch Geld."),
    (("haushaltsbuch", "budget planen", "50-30-20", "fixkosten richtig ordnen",
      "erster eigener haushalt", "haushaltsplan"),
     "Zieh vor dem Sparen zuerst alle festen Ausgaben und laufenden "
     "Lebenshaltungskosten von den Nettoeinnahmen ab – was übrig bleibt, ist "
     "der echte Sparbetrag."),
    (("grundversorgung", "ersatzversorgung", "ersatzgas"),
     "Prüfe nach einem Wechsel in die Grundversorgung sofort einen neuen "
     "Tarifvergleich – die Versorgung ist sicher, aber meist deutlich teurer "
     "als ein regulärer Vertrag."),
    (("heizkosten senken", "guenstig durch den winter", "günstig durch den winter",
      "heizkosten", "heizsaison"),
     "Stell vor der Heizsaison zuerst Thermostat, Entlüftung und Dämmung der "
     "Rohre richtig ein – die Einstellung der Technik spart mehr als jeder "
     "kurzfristige Tarifwechsel."),
    (("gasrechnung senken", "gasrechnung"),
     "Prüfe vor dem Vergleich den Arbeitspreis pro Kilowattstunde und den "
     "Jahresverbrauch der letzten Abrechnung – der Bonus allein sagt nichts "
     "über die Ersparnis."),
    (("dauerauftrag", "lastschrift", "abbuchung"),
     "Sieh dir vor der Freigabe einer Lastschrift zuerst Vertragsbedingung "
     "und Mandatsreferenz an – unberechtigte Abbuchungen kannst du innerhalb "
     "von acht Wochen zurückgeben."),
    (("wlan", "empfang", "wlan-verbessern", "wlan verbessern"),
     "Miss vor jedem Gerätekauf zuerst die Signalstärke am Aufstellort – ein "
     "stärkerer Router nutzt nichts, wenn das Funksignal durch Wände "
     "blockiert wird."),
    (("dns", "resolver", "nameserver"),
     "Prüfe nach einem DNS-Wechsel Filterwirkung und Datenschutzbedingungen "
     "des gewählten Resolvers – ein anderer Server ändert weder Bandbreite "
     "noch Anonymität von allein."),
    (("dsl-wechselbonus", "wechselbonus", "cashback dsl"),
     "Prüfe vor einem Wechsel zuerst den Effektivpreis über 24 Monate inklusive "
     "Router, Bereitstellung und laufender Rabatte – nicht nur den Bonus des "
     "ersten Jahres."),
    (("dsl", "internet-tarif", "breitband", "glasfaser", "internetanbieter",
      "tarifvergleich internet", "anbieterwechsel"),
     "Prüfe vor einem Internetwechsel zuerst die verfügbare Bandbreite an "
     "deiner Adresse – der beste Tarif nützt nichts, wenn die Leitung die "
     "Geschwindigkeit nicht hergibt."),
    (("preisgarantie gas", "preisgarantie"),
     "Eine Preisgarantie schützt nur vor Preiserhöhungen während der Laufzeit – "
     "vergleiche trotzdem den Arbeitspreis, die Laufzeit und mögliche "
     "Anpassungsklauseln."),
    (("gas", "heizöl"),
     "Vergleiche vor einem Gasvertrag den Arbeitspreis pro Kilowattstunde über "
     "mehrere Abrechnungsperioden – ein kurzer Rabatt wiegt weniger als der "
     "laufende Preis."),
    (("notgroschen", "notgrosch", "finanzieller puffer"),
     "Baue den Notgroschen auf einem leicht zugänglichen Tagesgeldkonto auf, "
     "bevor du in riskantere Anlageformen investierst – Liquidität geht vor "
     "Rendite."),
    (("tagesgeld", "festgeld", "zinssatz"),
     "Vergleiche vor der Anlage Zinssatz, Einlagensicherung und Kündigungsfrist "
     "zusammen – der höchste Nominalzins nützt wenig bei schlechter Sicherung "
     "oder langer Bindung."),
    (("stromverbrauch", "strom"),
     "Miss den Verbrauch am Gerät, bevor du Tarife vergleichst – ein Wechsel "
     "bringt nur dann echte Ersparnis, wenn du weißt, wo dein Zähler wirklich "
     "läuft."),
    (("frugalismus", "verzicht", "sparen"),
     "Setz dir vor dem Sparen ein konkretes Ziel mit Datum und Betrag – ohne "
     "Messgröße verpuffen die kleinen Verzichte im Alltag."),
    # Breite Rückfälle ganz zum Schluss.
    (("internet", "festnetz", "router", "anschluss"),
     "Prüfe vor einem Wechsel zuerst den Effektivpreis über 24 Monate inklusive "
     "Router, Bereitstellung und laufender Rabatte – nicht nur den Bonus des "
     "ersten Jahres."),
]


def _enthaelt_themenwort(text: str, wort: str) -> bool:
    """Match whole normalized words/phrases, never accidental substrings."""
    text_norm = f" {_norm_satz(text)} "
    wort_norm = _norm_satz(wort)
    return bool(wort_norm and f" {wort_norm} " in text_norm)


def _themen_spezifische_faustregel(body: str) -> str:
    """Return a topic-relevance hint; never return article copy to write.

    The topical variants retained from #776 help rank the independently
    curated uniqueness pool. They are not emitted: every new or replacement
    sentence is selected from ``FAUSTREGEL_POOL`` and checked against the
    measured content inventory before it can be written.

    Matching prefers precise title/lead signals over incidental words later
    in the article. A missing match returns an empty hint so the selector can
    use its deterministic pool/hash fallback without inventing a template.
    """
    text = body or ""
    # Titel/Leadsignal extrahieren (Frontmatter `title:` oder erste Textzeile)
    title = ""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end > 0:
            fm = text[3:end]
            tm = re.search(r"(?m)^title:\s*[\"']?([^\"'\n]+)[\"']?\s*$", fm)
            if tm:
                title = tm.group(1).strip().lower()
            body_only = text[end + 4:]
        else:
            body_only = text
    else:
        body_only = text
        first_line, separator, remainder = text.partition("\n")
        title = first_line.lstrip("# ").strip().lower()
        if separator:
            body_only = remainder
    title_low = title
    head_len = min(1000, len(body_only))
    head = body_only[:head_len].lower()
    low = body_only.lower()

    for stufe in (title_low, head, low):
        for schluesselwoerter, satz in _THEMEN_FAUSTREGELN:
            if any(_enthaelt_themenwort(stufe, kw) for kw in schluesselwoerter):
                return satz
    # No hint is safer than inserting unmeasured generic copy.
    return ""


def faustregel_saetze() -> list[str]:
    """Alle Pool-Sätze – die Liste, gegen die der Bestand geprüft wird."""
    return [satz for _thema, satz, _stichworte in FAUSTREGEL_POOL]


def _norm_satz(text: str) -> str:
    """Vergleichsform eines Satzes (Kleinschreibung, Umlaute gefaltet).

    Absichtlich dieselbe Normalisierung wie `check_uniqueness.norm`: Ein Satz
    gilt als „im Bestand vorhanden“, wenn das Audit ihn als denselben Text
    messen würde.
    """
    text = (text or "").lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text = text.replace(a, b)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _messung():
    """Die Messregel des Tagesaudits – dieselbe Funktion, keine zweite Zählung.

    Lazy importiert: `check_uniqueness` liest beim Import nur Konstanten, aber
    ein Import auf Modulebene würde die Wache in jede Umgebung mitziehen, die
    nur diesen Schreiber braucht.
    """
    import check_uniqueness as cu  # noqa: PLC0415 – eine Messregel, lazy
    return cu


def faustregel_index(texte: dict) -> tuple:
    """Bestands-Messung für die Satz-Wahl. → (belegung, index)

    belegung  Menge der Pool-Sätze, die im Bestand (irgendwo) schon stehen.
    index     {slug: 7-Gramm-Menge des sauberen Artikeltexts} – die Gramme
              kommen aus `check_uniqueness.clean_body`, damit der Schreiber
              exakt das sieht, was das Audit später misst.
    """
    cu = _messung()
    belegung, index = set(), {}
    saetze = faustregel_saetze()
    for slug, inhalt in (texte or {}).items():
        normal = _norm_satz(inhalt)
        for satz in saetze:
            if _norm_satz(satz) in normal:
                belegung.add(satz)
        index[slug] = cu.ngrams(cu.clean_body(inhalt), cu.PHRASE_LEN)
    return belegung, index


def faustregel_kontext(texte: dict) -> dict:
    """Alles, was eine einzigartige Satz-Wahl braucht (ein Objekt, ein Lauf).

    `texte` sind die ROHEN Content-Dateien (`{slug: Inhalt}`). Der Kontext
    hält die Bestandsbelegung, den Gramm-Index und die im Lauf schon
    vergebenen Sätze – so kann ein Lauf mit 30 Heilungen nicht 30-mal
    denselben „freien“ Satz vergeben.
    """
    belegung, index = faustregel_index(texte)
    return {"belegung": belegung, "index": index, "vermeiden": set()}


FAUSTREGEL_VORRAT_WARNUNG = 5


def faustregel_vorrat(kontext: dict) -> int:
    """Wie viele Pool-Sätze sind noch frei? (Frühwarnung mit Vorlauf)

    Der Heiler ist die Notversorgung, nicht die Versorgung: Schreibt die
    Redaktion/KI die Faustregel selbst, bleibt er still. Ist der Vorrat
    trotzdem fast leer, muss das VOR dem Stillstand sichtbar sein – sonst
    steht plötzlich ein Artikel ohne RS3, und niemand weiß, warum.
    """
    belegt = set((kontext or {}).get("belegung") or set())
    belegt |= set((kontext or {}).get("vermeiden") or set())
    return len([s for s in faustregel_saetze() if s not in belegt])


def _kontext_aktualisieren(kontext: dict, slug: str, inhalt: str) -> None:
    """Hält die Bestands-Messung WÄHREND des Laufs aktuell.

    Ohne diesen Schritt plant ein `--dry-run` falsch: Er schreibt nichts, der
    nächste Artikel sähe den alten Bestand – und der Lauf meldete „kein freier
    Satz“, obwohl der Pool reicht. Mit dem Schritt ist der Dry-Run die ehrliche
    Vorschau auf den echten Lauf (gleiche Reihenfolge, gleiche Messung).
    """
    if kontext is None:
        return
    cu = _messung()
    kontext.setdefault("index", {})[slug] = cu.ngrams(cu.clean_body(inhalt),
                                                      cu.PHRASE_LEN)
    normal = _norm_satz(inhalt)
    belegung = kontext.setdefault("belegung", set())
    for satz in faustregel_saetze():
        if _norm_satz(satz) in normal:
            belegung.add(satz)


def _bestand_texte(paths=None) -> dict:
    """{slug: roher Inhalt} aller Content-Dateien – EINE Leseregel.

    Gelesen wird die Datei, nicht der `load_article`-Zwischenstand: Der
    Kontext soll den Bestand sehen, wie er auf der Platte steht (inklusive
    Entwürfe – ein Satz in der Reserve ist kein freier Satz, er wird
    spätestens am Publikationstag gemessen).
    """
    texte = {}
    for path in (paths if paths is not None else list_post_paths()):
        try:
            with open(path, encoding="utf-8") as fh:
                texte[slug_of(path)] = fh.read()
        except OSError:
            continue
    return texte


_THEMEN_HINWEIS_STOPPWOERTER = frozenset(
    "aber als am an auf aus bei bevor bis da damit dann das dass dein deine dem "
    "den der des die doch du durch ein eine einem einen einer eines er es erst "
    "für fuer ganz im in ist jede jeder jedes kann kein keine mit nach nicht nur "
    "oder ohne pruefe pruefen haushalt so sich sie sind statt über ueber um und "
    "uns unter von vor was "
    "weil wenn wer wie wird wir zu zum zur zwischen".split()
)


def _themen_score(satz: str, stichworte, artikel_text: str,
                  themenhinweis: str | None = None) -> tuple[int, int]:
    """Return (semantic hint overlap, weighted exact pool-keyword score).

    The #776 topical variants provide a fine-grained preference, while the
    candidate wording remains #766's collision-checked pool. Common function
    words are excluded so the hint does not reward generic sentence scaffolds.
    """
    text_norm = f" {_norm_satz(artikel_text)} "
    # Specific anchors (for example "warmwasser") must outrank a generic
    # incidental match such as "haushalt". Weight each distinct tag by its
    # normalized length; repeated occurrences in a long article do not inflate
    # the score.
    direkt = sum(
        len(norm.replace(" ", ""))
        for wort in stichworte
        if (norm := _norm_satz(wort)) and f" {norm} " in text_norm
    )
    hinweis = (themenhinweis if themenhinweis is not None
               else _themen_spezifische_faustregel(artikel_text))
    satzwoerter = set(_norm_satz(satz).split())
    hinweiswoerter = (set(_norm_satz(hinweis).split())
                      - _THEMEN_HINWEIS_STOPPWOERTER)
    themen_treffer = len(satzwoerter & hinweiswoerter)
    return themen_treffer, direkt


def waehle_faustregel(artikel_text: str, eigene_gramme: set, slug: str = "",
                      kontext: dict = None) -> tuple:
    """Wählt eine freie, themenpassende Faustregel. → (satz, grund)

    Auswahl in dieser Reihenfolge (deterministisch, nie zufällig):
      1. kein Satz des Pools steht schon im Bestand oder im laufenden Lauf,
      2. der Satz schiebt KEIN Artikelpaar über die Audit-Schwelle
         (KRITISCH_AB geteilte 7-Gramme – dieselbe Messung wie das Audit),
      3. höchste lexikalische Nähe zum präzisen Themenhinweis,
      4. explizite Pool-Stichwörter als thematische Gleichstandsauflösung,
      5. stabiler Hash über (Slug, Satz) als letzte Gleichstands-Entscheidung.
    Ohne freien Satz: (None, Grund) – der Aufrufer schreibt dann nichts.
    """
    cu = _messung()
    eigene_gramme = eigene_gramme or set()
    kontext = kontext if kontext is not None else {}
    belegung = kontext.get("belegung") or set()
    vermeiden = kontext.get("vermeiden")
    if not isinstance(vermeiden, set):
        vermeiden = set(vermeiden or ())
        kontext["vermeiden"] = vermeiden
    index = kontext.get("index") or {}
    schwelle = cu.KRITISCH_AB
    themenhinweis = _themen_spezifische_faustregel(artikel_text)

    kandidaten = []
    for thema, satz, stichworte in FAUSTREGEL_POOL:
        if satz in belegung or satz in vermeiden:
            continue
        satz_gramme = cu.ngrams(satz, cu.PHRASE_LEN)
        kollision = False
        for fremd_slug, fremd_gramme in index.items():
            if fremd_slug == slug:
                continue
            if len((eigene_gramme | satz_gramme) & fremd_gramme) >= schwelle:
                kollision = True
                break
        if kollision:
            continue
        hinweis_score, stichwort_score = _themen_score(
            satz, stichworte, artikel_text, themenhinweis=themenhinweis)
        rang = (-hinweis_score, -stichwort_score, thema)
        streuung = hashlib.sha1(f"{slug}|{satz}".encode("utf-8")).hexdigest()
        kandidaten.append((rang, streuung, satz))
    if not kandidaten:
        return None, ("kein freier Faustregel-Satz im Pool – alle Varianten "
                      "stehen schon im Bestand oder würden eine kritische "
                      "Überlappung erzeugen (redaktionelle Aufgabe)")
    kandidaten.sort(key=lambda k: (k[0], k[1]))
    satz = kandidaten[0][2]
    vermeiden.add(satz)
    return satz, f"{len(kandidaten)} freie Variante(n), Themenbezug gewählt"


def _faustregel_kandidaten(text: str, slug: str, kontext: dict,
                           basis_ohne_satz: str) -> tuple:
    """Satz + Grund; berechnet die Gramme des Artikels ohne den Alt-Satz."""
    cu = _messung()
    eigene = cu.ngrams(cu.clean_body(basis_ohne_satz), cu.PHRASE_LEN)
    return waehle_faustregel(f"{slug} {text}", eigene, slug=slug, kontext=kontext)


def _legacy_muster() -> re.Pattern:
    """Tolerantes Suchmuster für den eingefrorenen Heiler-Satz.

    Zwischen den Wörtern darf beliebige Typografie stehen (Leerzeichen,
    geschütztes Leerzeichen, Binde-/Gedankenstriche, Satzzeichen) – der
    Altbestand ist gewachsen, das Muster soll ihn finden, nicht bestrafen.
    Wortfolge und Wortbestand bleiben exakt: Ein Satz mit eingeschobenen
    eigenen Wörtern ist NICHT der Heiler-Satz und wird nicht angefasst.
    """
    worte = re.findall(r"\w+", FAUSTREGEL_LEGACY, re.UNICODE)
    # Der Schlusspunkt gehört zum Satz: Ohne ihn bliebe beim Ersetzen ein
    # doppelter Punkt stehen („… dann den Tarif..“ – im ersten echten Lauf
    # gesehen und hier eingefroren).
    return re.compile(r"(?<!\w)" + r"[^\w\n]{0,4}".join(re.escape(w) for w in worte)
                      + r"(?!\w)[.!]?")


def ersetze_generische_faustregel(body: str, slug: str = "", titel: str = "",
                                  kontext: dict = None) -> tuple:
    """Ersetzt den eingefrorenen Heiler-Satz durch eine freie Faustregel.

    Rückgabe: (neuer Body, Anzahl Ersetzungen, Meldung). Idempotent: Beim
    zweiten Lauf findet das Muster nichts mehr. Findet der Wähler keine freie
    Variante, bleibt der Text UNVERÄNDERT (keine Ersetzung durch einen neuen
    Massensatz) und die Meldung nennt den Grund.
    """
    cur = body or ""
    treffer = list(_legacy_muster().finditer(cur))
    if not treffer:
        return cur, 0, ""
    ohne = _legacy_muster().sub(" ", cur)
    satz, grund = _faustregel_kandidaten(
        f"{titel}\n{slug}\n{ohne}", slug,
        kontext if kontext is not None else {}, ohne)
    if not satz:
        return cur, 0, f"RS3-EINZIGARTIG: {grund}"
    neu = _legacy_muster().sub(satz, cur)
    return neu, len(treffer), (f"RS3-EINZIGARTIG: {len(treffer)} generische "
                               f"Faustregel(n) ersetzt ({grund})")


def fix_rs2_rs3_deterministic(body: str, slug: str = "", kontext: dict = None,
                              titel: str = "", nur_rs3: bool = False) -> tuple:
    """Heilt fehlende RS2 (Frage-H2) und RS3 (Faustregel) deterministisch,
    ohne Links, H2-Anzahl oder Zahlen-Aussagen zu verändern.

    Die Faustregel kommt seit #766 aus `FAUSTREGEL_POOL` und wird gegen den
    Bestand gemessen (`kontext`); ohne Kontext (Einzelaufruf, Tests) wählt
    der Wähler nach Thema und Hash – deterministisch, aber ungemessen. Im
    Betrieb ruft `main()` immer mit Kontext.
    """
    healed: list[str] = []
    cur = body or ""

    # RS2: mindestens 2 Frage-H2 mit '?'
    r2_ok, _ = detect_rs2(cur)
    if nur_rs3:
        r2_ok = True  # Klasse abgewählt (--nur-faustregel): RS2 bleibt liegen
    if not r2_ok:
        lines = cur.splitlines()
        q_count = sum(1 for ln in lines if ln.startswith("## ") and ln.rstrip().endswith("?"))
        for idx, ln in enumerate(lines):
            if q_count >= 2:
                break
            if not ln.startswith("## "):
                continue
            h_text = ln[3:].strip()
            if h_text.endswith("?"):
                continue
            low = h_text.lower()
            if low in ("häufige fragen", "faq", "fazit"):
                continue
            new_h = None
            if any(low.startswith(prefix) for prefix in _QUESTION_STARTS):
                new_h = h_text.rstrip(".!:") + "?"
            elif re.match(r"^typische fehler\b", low):
                rest = h_text[len("Typische Fehler"):].strip(" –—-:")
                new_h = (f"Welche typischen Fehler {rest} kosten dich Geld?"
                         if rest else "Welche typischen Fehler kosten dich Geld?")
            elif re.match(r"^fazit\s*[:–—-]\s*(.+)$", h_text, re.I):
                tail = re.match(r"^fazit\s*[:–—-]\s*(.+)$", h_text, re.I).group(1).rstrip(".!")
                new_h = f"Fazit: {tail}?" if any(tail.lower().startswith(p) for p in _QUESTION_STARTS) else f"Fazit: Was bedeutet das für {tail}?"
            if new_h and new_h != h_text:
                lines[idx] = f"## {new_h}"
                q_count += 1
        candidate = "\n".join(lines)
        if cur.endswith("\n") and not candidate.endswith("\n"):
            candidate += "\n"
        if detect_rs2(candidate)[0] and _links(cur) == _links(candidate) and len(h2_lines(cur)) == len(h2_lines(candidate)):
            cur = candidate
            healed.append("RS2")

    # RS3: mindestens 1 markierte Faustregel
    r3_ok, _ = detect_rs3(cur)
    if not r3_ok:
        # #766: Der Satz wird GEWÄHLT (Pool + Bestandsmessung), nicht gesetzt.
        satz, _grund = _faustregel_kandidaten(
            f"{titel}\n{slug}\n{cur}", slug,
            kontext if kontext is not None else {}, cur)
        if satz:
            faustregel_absatz = f"\n\n{FAUSTREGEL_MARKER} {satz}\n\n"
            m_faq = re.search(r"^##\s+(?:Häufige Fragen|FAQ|Fazit)\b", cur, re.M | re.I)
            if m_faq:
                pos = m_faq.start()
                candidate = cur[:pos].rstrip() + faustregel_absatz + cur[pos:]
            else:
                candidate = cur.rstrip() + faustregel_absatz
            if detect_rs3(candidate)[0] and _links(cur) == _links(candidate):
                cur = candidate
                healed.append("RS3")

    return cur, healed


_RS5_DETERMINISTIC_MARKERS = (
    "im Modellfall",
    "als Beispielwert",
    "als Modellwert",
    "im Rechenfall",
    "im Rechenbeispiel",
    "als Modellannahme",
)


def _heal_rs5_block(block: str, marker_idx: int) -> tuple[str, int]:
    """Qualifiziert den ersten unbelegten Zahlen-Satz eines Absatzes als Modellwert.

    WARUM NEU (01.11.2026, #964): Der Heiler suchte die ERSTE Satzgrenze im
    Absatz (`re.search(r"([.!?])(\s+|$)")`) und setzte dort „ im Modellfall“
    ein. Dieser Punkt ist aber nicht immer eine Satzgrenze: Bei „ca.“, „z. B.“,
    einer Ordnungszahl („3. **Tür“) oder einem Datum („30. November“) stand
    die Kennzeichnung MITTEN im Wort, bei „… 460 €. Rechne“ hinter dem Betrag,
    aber im nächsten Satz. Ergebnis im Bestand: 494 zerstückelte
    Kennzeichnungen in 63 Dateien („ca im Modellfall. 500 €“, „bis zum 30 als
    Beispielwert. November“) – live und in den Snippets.

    Die Heilung ist jetzt zielsicher: Der Satz mit der Zahlenbehauptung wird
    bestimmt (Abkürzungen und Ordinaldaten sind keine Grenze), und die
    Kennzeichnung hängt als eigener Teilsatz an SEINEM Ende:
    „… über 460 €; das ist ein Beispielwert.“ Diese Form ist nach jedem
    Satzende grammatisch und trägt den Ausdruck, den RS5 als Modellannahme
    akzeptiert. Die Aussage selbst bleibt unverändert.
    """
    lines = block.splitlines()
    for i, ln in enumerate(lines):
        s_ln = ln.lstrip()
        if not s_ln or s_ln.startswith(("#", ">", "|", "<!--")):
            continue
        if _reserve_numeric_claim_findings(ln) and "§" not in ln:
            marker = _RS5_DETERMINISTIC_MARKERS[
                marker_idx % len(_RS5_DETERMINISTIC_MARKERS)
            ]
            lines[i] = _kennzeichnung_ans_satzende(ln, marker)
            return "\n".join(lines), marker_idx + 1
    return block, marker_idx


# Abkürzungen und Ordinaldaten, nach deren Punkt KEIN Satz endet. Dieselbe
# Liste wie `_reserve_numeric_claim_findings.abbrev_re` – eine Regel, zwei
# Leser; ein neuer Eintrag muss an beiden Stellen nicht nachgezogen werden,
# weil diese Funktion die Grenzen selbst bestimmt.
_KEIN_SATZENDE = re.compile(
    r"\b(?:ca|bzw|usw|ggf|inkl|mind|max|vgl|nr|abs|z|B|Dr|Prof|Art|Rn|S|"
    r"d\.h|u\.a|evtl|etc|Mio|Mrd|Std)$", re.I)
_MONATSNAME = re.compile(
    r"\s*(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|"
    r"November|Dezember)\b")
_KENNZEICHNUNG_NOMEN = {
    "im Modellfall": "Modellwert",
    "als Modellwert": "Modellwert",
    "als Beispielwert": "Beispielwert",
    "im Rechenfall": "Rechenbeispiel",
    "im Rechenbeispiel": "Rechenbeispiel",
    "als Modellannahme": "Modellannahme",
}


def _satzgrenzen(zeile: str) -> list[int]:
    """Echte Satzenden (Index des Terminators) – ohne Abkürzung und Datum."""
    grenzen = []
    for m in re.finditer(r"[.!?](?=\s|$)", zeile):
        i = m.start()
        if zeile[i] == ".":
            if _KEIN_SATZENDE.search(zeile[max(0, i - 10):i]):
                continue
            if zeile[:i].rstrip().endswith("."):   # „z. B.“ / „u. a.“
                continue
            if re.search(r"\d$", zeile[:i]) and _MONATSNAME.match(zeile[i + 1:]):
                continue
        grenzen.append(i)
    return grenzen


def _kennzeichnung_ans_satzende(zeile: str, marker: str) -> str:
    """Hängt die Kennzeichnung als Teilsatz an das Satzende des Zahlensatzes."""
    nomen = _KENNZEICHNUNG_NOMEN.get(marker, "Modellwert")
    grenzen = _satzgrenzen(zeile)
    # Der Zahlensatz: der erste Satz, den `_reserve_numeric_claim_findings`
    # ohne Modellkennzeichnung beanstandet.
    start = 0
    for ende in grenzen:
        satz = zeile[start:ende + 1]
        if _reserve_numeric_claim_findings(satz) and "§" not in satz:
            rumpf = satz[:-1].rstrip().rstrip(",;:")
            termin = satz[-1]
            rest = zeile[ende + 1:]
            return f"{rumpf}; {sprachkern._praedikativ(nomen)}{termin}{rest}"
        start = ende + 1
    # Kein Satzende gefunden (Absatz ohne Punkt): als eigener Satz anhängen.
    rumpf = zeile.rstrip()
    trenner = "" if rumpf.endswith((".", "!", "?")) else "."
    satz = sprachkern._praedikativ(nomen)
    return f"{rumpf}{trenner} {satz[0].upper()}{satz[1:]}."


def fix_rs4_rs5_deterministic(body: str) -> tuple[str, list[str]]:
    """Heilt fehlende RS4 (Schrittfolge) und unbelegte RS5-Zahlen deterministisch.

    Gesetzliche §-Verweise werden bewusst NIE als Modellrechnung etikettiert
    (sie erfordern immer einen echten Primärquellen-Link).
    """
    healed: list[str] = []
    cur = body or ""

    # RS4: Vorhandene Checkliste (- [ ] ...) oder Schritt-Liste (>= 3 Punkte)
    # in nummerierte Schritte (1. / 2. / 3.) überführen.
    r4_ok, _ = detect_rs4(cur)
    if not r4_ok:
        lines = cur.splitlines()
        runs: list[list[int]] = []
        current_run: list[int] = []
        for idx, ln in enumerate(lines):
            if re.match(r"^\s*-\s*\[[ xX]?\]\s+\S", ln):
                current_run.append(idx)
            else:
                if len(current_run) >= 3:
                    runs.append(current_run)
                current_run = []
        if len(current_run) >= 3:
            runs.append(current_run)

        if not runs:
            seen_h2 = False
            current_run = []
            for idx, ln in enumerate(lines):
                if ln.startswith("## "):
                    seen_h2 = True
                if seen_h2 and re.match(r"^\s*[-*]\s+\S", ln):
                    current_run.append(idx)
                else:
                    if len(current_run) >= 3:
                        runs.append(current_run)
                    current_run = []
            if len(current_run) >= 3:
                runs.append(current_run)

        if runs:
            target_run = runs[0]
            cand_lines = list(lines)
            for step_no, line_idx in enumerate(target_run, start=1):
                cand_lines[line_idx] = re.sub(
                    r"^(\s*)(?:-\s*\[[ xX]?\]|[-*])\s+",
                    rf"\g<1>{step_no}. ",
                    cand_lines[line_idx],
                    count=1,
                )
            candidate = "\n".join(cand_lines)
            if cur.endswith("\n") and not candidate.endswith("\n"):
                candidate += "\n"
            if (
                detect_rs4(candidate)[0]
                and _links(cur) == _links(candidate)
                and len(h2_lines(cur)) == len(h2_lines(candidate))
            ):
                cur = candidate
                healed.append("RS4")

    # RS5: Unbelegte Zahlen-Sätze (ohne §) als Modell-/Beispielwert kennzeichnen.
    vorher_rs5 = _reserve_numeric_claim_findings(cur)
    if vorher_rs5:
        parts = re.split(r"(\n\s*\n)", cur)
        marker_idx = 0
        for idx in range(0, len(parts), 2):
            prefix_before = "".join(parts[:idx]) if idx > 0 else ""
            prefix_with = "".join(parts[: idx + 1])
            if len(_reserve_numeric_claim_findings(prefix_with)) > len(
                _reserve_numeric_claim_findings(prefix_before)
            ):
                new_block, marker_idx = _heal_rs5_block(parts[idx], marker_idx)
                parts[idx] = new_block
        candidate = "".join(parts)
        nachher_rs5 = _reserve_numeric_claim_findings(candidate)
        if (
            candidate != cur
            and len(nachher_rs5) < len(vorher_rs5)
            and _links(cur) == _links(candidate)
            and len(h2_lines(cur)) == len(h2_lines(candidate))
        ):
            cur = candidate
            healed.append("RS5")

    return cur, healed


# ---------------------------------------------------------------------------
# KI-Heilung (RS1–RS6) mit Verifikation
# ---------------------------------------------------------------------------

def _call_ai(prompt, max_tokens=6000):
    """Gemini zuerst, dann Groq – alle Aufrufe laufen über llm_client."""
    for provider in ("gemini", "groq"):
        if not llm_client.available(provider):
            continue
        try:
            text = llm_client.chat(
                provider, prompt=prompt,
                model=os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")
                if provider == "gemini" else None,
                max_tokens=max_tokens, timeout=180, attempts=3,
            )
            if text:
                return text
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠ {provider.capitalize()}: {e}")
    return None


def _links(body):
    """Alle Linkziele in stabilem Set (byte-identisch)."""
    return sorted(set(re.findall(r"\]\(([^)]*)\)", body)))


def _verify(orig_body, new_body, allow_h2_text_change=True):
    """Sicherheits-Verifikation vor dem Schreiben. → (ok, meldung)"""
    if _links(orig_body) != _links(new_body):
        return False, "Linkziele verändert – Heilung verworfen"
    if len(h2_lines(orig_body)) != len(h2_lines(new_body)):
        return False, "H2-Anzahl verändert – Heilung verworfen"
    if len(new_body) < int(0.9 * len(orig_body)):
        return False, "Länge < 90 % des Originals – Heilung verworfen"
    if "---" in new_body[:2000] and new_body.count("---") != orig_body.count("---"):
        return False, "Markdown-Trennlinien-Anzahl verändert – Heilung verworfen"
    return True, "ok"


def _merke_verworfen(verworfen, a, grund):
    """Hält eine abgelehnte KI-Änderung fest (Report + Historie).

    Ein Stopp, der nur im Log steht, ist beim nächsten Lauf vergessen. Diese
    Liste macht sichtbar, wie oft die Wache eine KI-Änderung verhindert hat –
    und warum (Vorfall WF-54C4/#607: genau dieser Nachweis fehlte).
    """
    if verworfen is None:
        return
    verworfen.append({"slug": a["slug"], "regel": "VERTRAG",
                      "aktion": "ki-heilung-verworfen", "grund": grund})


def _vertrag_gruende(a, neu_body):
    """Verstöße einer GEPLANTEN KI-Änderung gegen den Publikations-Vertrag.

    Fail-closed: Ist der Vertrag nicht prüfbar, gilt die Änderung als
    unzulässig (genau der Zustand, der am 05.10.2026 einen blockierten
    Deploy verursacht hat – nur diesmal VOR dem Schreiben).
    """
    if _vertrag_pruefe is None:
        return [f"V3 Messbarkeit: Publikations-Vertrag nicht verfügbar "
                f"({_VERTRAG_FEHLER}) – fail-closed, die Änderung wird verworfen"]
    try:
        alt_raw = join_article(a["fm"], a["body"])
        neu_raw = join_article(a["fm"], neu_body)
        return _vertrag_pruefe(a["slug"], alt_raw, neu_raw)
    except Exception as exc:  # noqa: BLE001 – ohne Mess KEIN grünes Urteil
        return [f"V3 Messbarkeit: Publikations-Vertrag nicht auswertbar "
                f"({exc.__class__.__name__}: {exc}) – fail-closed, die Änderung "
                f"wird verworfen"]


ZAHLEN_HEILER_MAX = 12


def build_zahlen_heiler_prompt(body, findings, titel=""):
    """Prompt für den Zahlen-Beleg-Heiler: repariert NUR die abgelehnten Sätze.

    WARUM (25.10.2026, WF-D4E0/#821)
    --------------------------------
    Das harte RS5-Gate lehnt jeden Satz ab, der eine Zahl mit Einheit ohne
    Quellenlink im SELBEN Satz und ohne Modell-Kennzeichnung nennt. Im Lauf vom
    25.10.2026 starben **vier** frische Themen bei der Geburt an genau dieser
    Regel (16, 20 und 8 Sätze). Der vorhandene KI-Heiler (`heal_article_ai`,
    Auftrag 5) kennt die Regel – aber **nicht die Sätze**: Er schickt den
    ganzen Artikel mit einer allgemeinen Anweisung an das Modell und hofft,
    dass es die richtigen Stellen findet. Das ist die Lehre von #612 („der
    Retry war blind“) eine Ebene tiefer: Ein Heiler, der den Befund nicht
    kennt, heilt ihn nicht.

    Dieser Prompt nennt die Sätze wörtlich. Zwei erlaubte Wege, beide
    dokumentiert im Gate: ohne Zahl formulieren **oder** die Zahl im selben
    Satz als Beispiel-/Modellrechnung mit genannter Annahme kennzeichnen.
    Erfunden werden darf nichts – ein Quellenlink ist ein Beleg, „ca.“ nicht.
    """
    nummeriert = "\n".join(f"{i}. \u00ab{s}\u00bb" for i, s in enumerate(findings, 1))
    return (
        "Du bist Schlussredakteur eines seriösen deutschen Finanz-Ratgeber-Blogs. "
        "Im folgenden Artikel lehnt das harte Zahlen-Gate diese Sätze ab, weil "
        "sie eine Zahl nennen, ohne im SELBEN Satz einen klickbaren Quellenlink "
        "oder eine ausdrückliche Modell-/Beispielrechnungs-Kennzeichnung zu "
        "tragen:\n\n"
        + nummeriert
        + "\n\nAUFTRAG: Formuliere AUSSCHLIESSLICH diese Sätze neu. Pro Satz "
        "sind genau zwei Wege erlaubt:\n"
        "(a) OHNE ZAHL formulieren – beschreibe den Hebel, nicht den Betrag.\n"
        "(b) Die Zahl behalten und im SELBEN Satz als Beispielrechnung / "
        "Modellrechnung mit genannter Annahme kennzeichnen („In der "
        "Beispielrechnung mit einer Annahme von … ergibt sich …“).\n\n"
        "VERBOTEN: neue Zahlen, neue Quellen, erfundene Studien oder Links; "
        "„ca.“, „rund“ oder „etwa“ als Ersatz für die Kennzeichnung.\n\n"
        "HARTE REGELN:\n"
        "- Alles außerhalb dieser Sätze bleibt WORTGLEICH.\n"
        "- Alle Links bleiben byte-identisch; keine neuen Links.\n"
        "- Die Anzahl der H2-Überschriften bleibt exakt gleich.\n"
        "- Der Text wird nicht kürzer.\n"
        "- Antwort: NUR der vollständige Markdown-Artikel, ohne Erklärungen.\n\n"
        f"TITEL: {titel}\n\nARTIKEL:\n{body}\n"
    )


def zahlen_beleg_heiler(body, titel="", ki=None):
    """Heilt die vom RS5-Gate abgelehnten Sätze gezielt. → neuer Body oder None.

    Fail-closed und idempotent geprüft, bevor etwas zurückkommt:

      1. Länge        – der Text darf nicht schrumpfen (≥ 97 % der Wörter).
      2. Struktur     – Linkziele byte-identisch, H2-Anzahl gleich.
      3. Wirkung      – die Zahl der RS5-Befunde muss STRIKT sinken; sonst
                        gibt es keine Änderung zurück.
      4. Keine neuen  – RS1–RS6 dürfen keinen neuen Befund dazubekommen.

    Ohne Befund wird **kein** Modell aufgerufen (Idempotenz, Kosten).
    """
    body = body or ""
    findings = _reserve_numeric_claim_findings(body)
    if not findings:
        return None, []
    stelle = findings[:ZAHLEN_HEILER_MAX]
    ruf = ki or _call_ai
    neu = ruf(build_zahlen_heiler_prompt(body, stelle, titel), max_tokens=8000)
    if not neu:
        print("  ✗ Zahlen-Heiler: keine Antwort – Befund bleibt.")
        return None, stelle
    neu = neu.strip()
    if neu.startswith("```"):
        neu = re.sub(r"^```[a-z]*\n|\n```$", "", neu).strip()
    if len(neu) < 500:
        print("  ✗ Zahlen-Heiler: Antwort zu kurz – verworfen.")
        return None, stelle
    if len(re.findall(r"\w+", neu)) < 0.97 * len(re.findall(r"\w+", body)):
        print("  ✗ Zahlen-Heiler: Text geschrumpft – verworfen.")
        return None, stelle
    if _links(neu) != _links(body):
        print("  ✗ Zahlen-Heiler: Linkziele verändert – verworfen.")
        return None, stelle
    if len(re.findall(r"^##\s", neu, re.M)) != len(re.findall(r"^##\s", body, re.M)):
        print("  ✗ Zahlen-Heiler: H2-Anzahl verändert – verworfen.")
        return None, stelle
    rest = _reserve_numeric_claim_findings(neu)
    if len(rest) >= len(findings):
        print(f"  ✗ Zahlen-Heiler ohne Wirkung ({len(findings)} → {len(rest)}) – verworfen.")
        return None, stelle
    vorher = {f.split(":", 1)[0].strip() for f in reserve_quality_findings(body)}
    nachher = {f.split(":", 1)[0].strip() for f in reserve_quality_findings(neu)}
    neu_dazu = sorted(nachher - vorher)
    if neu_dazu:
        print(f"  ✗ Zahlen-Heiler führt neue Befunde ein ({', '.join(neu_dazu)}) – verworfen.")
        return None, stelle
    print(f"  ✅ Zahlen-Heiler: {len(findings)} → {len(rest)} unbelegte Zahlenbehauptung(en).")
    return neu, stelle


def heal_article_ai(a, res, verworfen=None):
    """Ein KI-Durchgang für alle fehlenden Module. Liefert neuen Body oder None.

    Prüf-Kette VOR dem Schreiben (jede Stufe kann die Änderung verwerfen):
      1. `_verify`            – Struktur (Links, H2-Anzahl, Länge, Trennlinien)
      2. Publikations-Vertrag – V1 Lesbarkeit, V2 neue harte Verständnis-Funde
      3. Idempotenz           – harte RS-Module danach wirklich geschlossen
    Die dritte Stufe war schon da; Stufe 2 fehlte – und ohne sie ging am
    05.10.2026 ein Text mit Flesch 44,3 und „In diesem Beitrag…“ in den
    Bestand (WF-54C4/#607). `verworfen` sammelt die Ablehnungen für Report
    und Historie, damit ein Stopp nachvollziehbar bleibt statt still zu sein.
    """
    fehlend = res["hart_missing"]
    weiche = []
    rs5_strict_vorher = _reserve_numeric_claim_findings(a["body"])
    if not res["rs5"][0]:
        weiche.append(f"RS5 harte Zahlen ohne Einordnung ({res['rs5'][2]} Sätze)")
    elif rs5_strict_vorher:
        weiche.append(f"RS5 Zahlenbehauptungen ohne Satzbeleg/Modellannahme ({len(rs5_strict_vorher)} Sätze)")
    if not res["rs6"][0]:
        weiche.append(f"RS6 Phantom-Quellen ({res['rs6'][2]} Stellen)")
    if not fehlend and not weiche:
        return None
    if not (llm_client.available("gemini") or llm_client.available("groq")):
        print("  ⚠ keine API-Keys – KI-Heilung übersprungen")
        return None

    auftraege = []
    if "RS1" in fehlend:
        auftraege.append(
            "1. Ergänze direkt NACH der Einleitung (vor der ersten H2-Überschrift) "
            "das Modul:\n\n**Das Wichtigste in Kürze**\n\n- <Bullet 1>\n- <Bullet 2>\n"
            "- <Bullet 3>\n\nDrei bis vier konkrete Kernaussagen des Artikels "
            "(ohne unbelegte Zahlen; Zahlenwerte nur mit Verweis auf die "
            "Beispielrechnung im selben Satz), keine Floskeln.")
    if "RS2" in fehlend:
        auftraege.append(
            "2. Formuliere mindestens ZWEI bestehende H2-Überschriften in "
            "Frageform um (Capital-erklärt-Stil, z. B. „Warum lohnt sich X?“). "
            "Die ANZAHL der H2-Überschriften bleibt exakt gleich.")
    if "RS3" in fehlend:
        auftraege.append(
            "3. Füge genau EINE markierte Faustregel als eigenen Absatz ein "
            "(Muster: „**Faustregel:** Wer …, spart …“), am besten vor der FAQ- "
            "oder Fazit-Sektion.")
    if "RS4" in fehlend:
        auftraege.append(
            "4. Füge eine nummerierte Schrittfolge mit 3–6 Schritten ein "
            "(„So gehst du vor“), am besten vor der FAQ-/Fazit-Sektion:\n\n"
            "1. …\n2. …\n3. …")
    if weiche:
        auftraege.append(
            "5. Ehrlichkeit & Zahlen-Vertrag (RS5/RS6): Ein bloßes „ca.“, „rund“ oder "
            "„in der Regel“ gilt am Gate NICHT als Beleg! Jede Zahl mit Einheit (€, %, "
            "kWh, Monate, Jahre) muss im SELBEN Satz als Modell-/Beispielrechnung "
            "(„Beispielrechnung“, „Modellrechnung“, „Annahme“, „Rechenbeispiel“) "
            "gekennzeichnet sein oder ohne Zahl formuliert werden, sofern kein "
            "klickbarer Quellenlink im selben Satz steht. Entferne ALLE Phantom-Quellen "
            "(„laut einer Studie“, „Experten sagen“ …) – formuliere stattdessen "
            "neutrales Allgemeinwissen ohne erfundene Belege.")
    prompt = (
        "Du bist Schlussredakteur eines seriösen deutschen Finanz-Ratgeber-Blogs. "
        "Arbeite sprachlich mindestens auf dem Niveau von ZEIT.de, aber eigenständig "
        "und ohne Formeln oder Satzmuster nachzuahmen. Templates, austauschbare "
        "Einstiege, Übergänge und Schlussformeln sind zu vermeiden; die Form folgt "
        "dem konkreten Gegenstand. Überarbeite den folgenden "
        "Markdown-Artikel NUR gemäß dieser Aufträge:\n\n"
        + "\n".join(auftraege)
        + "\n\nHARTE REGELN:\n"
        "- Frontmatter nicht anfassen (nicht Teil des Textes).\n"
        "- ALLE Links exakt beibehalten (URLs byte-identisch).\n"
        "- Die ANZAHL der H2-Überschriften bleibt exakt gleich.\n"
        "- Der Text bleibt mindestens so lang wie das Original (nur ergänzen/"
        "umformulieren, nichts ersatzlos streichen).\n"
        "- Keine erfundenen Zahlen, Preise, Studien oder Zitate.\n"
        "- Deutsche Orthografie, du-Ansprache, aktive Sprache.\n\n"
        f"TITEL: {a['title']}\n\nARTIKEL:\n{a['body']}\n\n"
        "Liefere NUR den vollständigen überarbeiteten Markdown-Text "
        "(ohne Frontmatter, ohne Erklärungen)."
    )
    print(f"  → KI-Redaktions-Standard: {len(auftraege)} Auftrag/Aufträge …")
    neu = _call_ai(prompt)
    if not neu or len(neu) < 500:
        print("  ✗ KI-Antwort leer/zu kurz – übersprungen.")
        return None
    ok, meldung = _verify(a["body"], neu)
    if not ok:
        print(f"  🛑 Verifikation fehlgeschlagen: {meldung}")
        _merke_verworfen(verworfen, a, f"Struktur: {meldung}")
        return None
    # Publikations-Vertrag: Die Änderung darf den Artikel nicht unter die
    # Veröffentlichungsschwelle drücken und keine neuen harten Verständnis-
    # Funde einführen (Kernfall WF-54C4/#607, 05.10.2026).
    vertrag = _vertrag_gruende(a, neu)
    if vertrag:
        print("  🛑 Publikations-Vertrag verletzt – KI-Heilung verworfen:")
        for grund in vertrag:
            print(f"     • {grund}")
        _merke_verworfen(verworfen, a, verstoesse_kurz(vertrag) if verstoesse_kurz
                         else vertrag[0][:160])
        return None
    # Idempotenz-Nachweis: nach der Heilung müssen die harten Detektoren grün sein
    a2 = dict(a)
    a2["body"] = neu
    res2 = analyse_article(a2)
    if res2["hart_missing"]:
        print(f"  ✗ Nach-Heilung noch offen: {', '.join(res2['hart_missing'])} – verworfen.")
        _merke_verworfen(verworfen, a,
                         f"Idempotenz: {', '.join(res2['hart_missing'])} weiter offen")
        return None
    rs5_strict_nachher = _reserve_numeric_claim_findings(neu)
    if (res2["rs5"][2] > res["rs5"][2]
            or res2["rs6"][2] > res["rs6"][2]
            or len(rs5_strict_nachher) > len(rs5_strict_vorher)):
        print("  ✗ Nach-Heilung mehr Zahlen-/Quellen-Funde – verworfen.")
        _merke_verworfen(verworfen, a, "Idempotenz: mehr Zahlen-/Quellen-Funde")
        return None
    return neu


# ---------------------------------------------------------------------------
# Report & Historie
# ---------------------------------------------------------------------------

def write_report(results, mode, gehärtet=None, verworfen=None):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    n = len(results)
    n_ok = sum(1 for r in results if not r["hart_missing"])
    lines = [
        "# 📰 REDAKTIONS-STANDARD (Capital · WiWo · ZEIT)",
        "",
        f"**Stand:** {now} · **Modus:** {mode} · **Artikel geprüft:** {n}",
        f"**Standard erfüllt:** {n_ok}/{n}",
        "",
        "| Regel | Quelle | Status |",
        "|---|---|---|",
    ]
    counters = {"RS1": 0, "RS2": 0, "RS3": 0, "RS4": 0, "RS7": 0}
    r5f = 0
    r6f = 0
    for r in results:
        for k in ("RS1", "RS2", "RS3", "RS4", "RS7"):
            if not r[k.lower()][0]:
                counters[k] += 1
        if not r["rs5"][0]:
            r5f += r["rs5"][2]
        if not r["rs6"][0]:
            r6f += r["rs6"][2]
    for k, label in (("RS1", "„Das Wichtigste in Kürze“-Box"),
                     ("RS2", "≥ 2 Frage-Überschriften"),
                     ("RS3", "Faustregel"),
                     ("RS4", "Nummerierte Schrittfolge"),
                     ("RS7", "Byline/E-E-A-T (Autor; Erfahrung nur mit Eigenbeleg)")):
        lines.append(f"| {k} | {label} | "
                     f"{'✅ 0 Funde' if counters[k] == 0 else '⚠ ' + str(counters[k]) + ' Artikel'} |")
    lines.append(f"| RS5 | Harte Zahlen ohne Einordnung | "
                 f"{'✅ sauber' if r5f == 0 else '⚠ ' + str(r5f) + ' Sätze'} |")
    lines.append(f"| RS6 | Phantom-Quellen („laut einer Studie“ …) | "
                 f"{'✅ sauber' if r6f == 0 else '⚠ ' + str(r6f) + ' Stellen'} |")
    lines.append("| RS8 | Korrektur-Transparenz (Box + Log) | ✅ dauerhaft aktiv |")
    lines += ["", "## Artikel mit offenen harten Regeln", ""]
    offene = [r for r in results if r["hart_missing"]]
    if not offene:
        lines.append("Keine – die ganze Flotte erfüllt den Redaktions-Standard. ✅")
    for r in sorted(offene, key=lambda x: -len(x["hart_missing"])):
        lines.append(f"- **{r['title'][:70]}** (`{r['slug']}`): "
                     f"{', '.join(r['hart_missing'])}")
    if gehärtet:
        lines += ["", "## In diesem Lauf geheilt", ""]
        for g in gehärtet:
            lines.append(f"- ✅ {g}")
    if verworfen:
        # Ein Stopp ist ein Ergebnis, kein Zwischenfall – und muss sichtbar
        # bleiben (sonst heilt der nächste Lauf dieselbe Ursache erneut).
        lines += ["", "## Vom Publikations-Vertrag gestoppte KI-Änderungen", ""]
        for v in verworfen[:10]:
            lines.append(f"- 🛑 `{v['slug']}` – {v.get('grund', '')}")
        if len(verworfen) > 10:
            lines.append(f"- … und {len(verworfen) - 10} weitere (siehe Log).")
    lines += ["", "_Wird bei jedem Lauf der Redaktions-Standard-Wache aktualisiert._",
              "_Methoden-Quellen: REDAKTIONS-STANDARD-CAPITAL-WIWO-ZEIT.md_"]
    with open(REPORT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def log_history(entries):
    if not entries:
        return
    os.makedirs(os.path.dirname(HISTORY), exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with open(HISTORY, "a", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps({"zeit": now, **e}, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# RS8: Korrektur-Log (WiWo-Korrektur-Transparenz)
# ---------------------------------------------------------------------------

def register_korrektur():
    """--register-korrektur --file X --grund '…' → data/korrekturen.yaml."""
    path = None
    if "--file" in sys.argv:
        path = sys.argv[sys.argv.index("--file") + 1]
    grund = ""
    if "--grund" in sys.argv:
        grund = sys.argv[sys.argv.index("--grund") + 1]
    if not path or not os.path.exists(path):
        print("✗ --file fehlt oder existiert nicht.")
        return 1
    a = load_article(path)
    if not a:
        print("✗ Artikel nicht lesbar (oder draft).")
        return 1
    today = datetime.date.today().isoformat()
    # Frontmatter: korrektur-Feld setzen (Layout rendert die Box)
    with open(path, encoding="utf-8") as fh:
        content = fh.read()
    parts = content.split("---", 2)
    fm = set_fm_field(parts[1], "korrektur",
                      f"{today}: {grund}"[:200])
    parts[1] = fm
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(join_article(parts[1], parts[2], parts[0]))
    # YAML-Log ergänzen
    eintraege = []
    if os.path.exists(KORREKTUR_LOG):
        try:
            import yaml
            with open(KORREKTUR_LOG, encoding="utf-8") as fh:
                eintraege = yaml.safe_load(fh) or []
        except Exception:
            eintraege = []
    eintraege.append({"datum": today, "slug": a["slug"], "titel": a["title"],
                      "korrektur": grund})
    os.makedirs(os.path.dirname(KORREKTUR_LOG), exist_ok=True)
    with open(KORREKTUR_LOG, "w", encoding="utf-8") as fh:
        fh.write("# Korrektur-Log (WiWo-Standard: Fehler transparent korrigieren)\n")
        for e in eintraege:
            fh.write(f"- datum: \"{e['datum']}\"\n  slug: \"{e['slug']}\"\n"
                     f"  titel: \"{e['titel']}\"\n  korrektur: \"{e['korrektur']}\"\n")
    print(f"✅ Korrektur registriert: {a['slug']} – {grund[:60]}")
    return 0


# ---------------------------------------------------------------------------
# Selbsttest (Sabotage-Schutz – eingefrorene Fälle)
# ---------------------------------------------------------------------------

SELFTEST = [
    # (name, funktion, eingabe, erwartung)
    ("RS1-ok", lambda: detect_rs1(
        "Intro.\n\n**Das Wichtigste in Kürze**\n\n- A\n- B\n- C\n\n## Rest")[0], True),
    ("RS1-fehlt", lambda: detect_rs1(
        "Intro ohne Box.\n\n## Rest")[0], False),
    ("RS1-wenige-bullets", lambda: detect_rs1(
        "**Das Wichtigste in Kürze**\n\n- A\n- B")[0], False),
    ("RS2-ok", lambda: detect_rs2(
        "## Warum lohnt das?\n\nText\n\n## Was kostet es?\n\nText\n\n"
        "## Tipps\n\n## Fazit")[0], True),
    ("RS2-fehlt", lambda: detect_rs2(
        "## Einleitung\n\n## Tipps\n\n## Fazit")[0], False),
    ("RS3-ok", lambda: detect_rs3(
        "**Faustregel:** Wer vergleicht, spart.")[0], True),
    ("RS3-fehlt", lambda: detect_rs3("Keine Regel hier.")[0], False),
    ("RS4-liste-ok", lambda: detect_rs4(
        "1. Erster Schritt\n2. Zweiter Schritt\n3. Dritter Schritt")[0], True),
    ("RS4-h2-ok", lambda: detect_rs4(
        "## Schritt 1: Basis\n\n## Schritt 2: Vergleich")[0], True),
    ("RS4-fehlt", lambda: detect_rs4(
        "Nur Fließtext ohne Schritte.")[0], False),
    ("RS5-ok-gehedgt", lambda: detect_rs5(
        "Der Wechsel kostet in der Regel zwischen 20 und 40 Euro pro Jahr. "
        "Das lohnt sich für die meisten Haushalte.")[0], True),
    ("RS5-fund", lambda: detect_rs5(
        "Der Wechsel kostet 32 Euro im Monat. Die Ersparnis beträgt 240 Euro "
        "pro Jahr und lohnt sich sofort.")[0], False),
    ("RS5-rechenbeispiel-ok", lambda: detect_rs5(
        "Unser Rechenbeispiel 2026 zeigt: 300 Euro Einsparung pro Jahr sind "
        "bei einem Verbrauch von 3.500 kWh realistisch.")[0], True),
    ("RS6-fund", lambda: detect_rs6(
        "Laut einer aktuellen Studie sparen Nutzer 200 Euro im Jahr. "
        "Experten sagen, das sei erst der Anfang.")[0], False),
    ("RS6-ok", lambda: detect_rs6(
        "In der Praxis sparst du oft mehrere hundert Euro im Jahr.")[0], True),
    ("Reserve-RS5-blockiert-unbelegte-Zahl", lambda: any(
        f.startswith("RS5:") for f in reserve_quality_findings(
            "Ein Tarif kostet 240 Euro pro Jahr.", author="Frank Hartung")), True),
    ("Reserve-RS5-belegt-Primärquelle", lambda: not any(
        f.startswith("RS5:") for f in reserve_quality_findings(
            "Der Vertrag darf höchstens 24 Monate laufen "
            "([§ 56 TKG](https://www.gesetze-im-internet.de/tkg_2021/__56.html)).",
            author="Frank Hartung")), True),
    ("Reserve-RS6-Phantomquelle", lambda: any(
        f.startswith("RS6:") for f in reserve_quality_findings(
            "Laut einer aktuellen Studie sparen Kunden viel Geld.",
            author="Frank Hartung")), True),
    ("Reserve-H2-Duplikat", lambda: any(
        "doppelte H2" in f for f in reserve_quality_findings(
            "\n".join(("## Warum sparen?", "", "## Warum sparen?")),
            author="Frank Hartung")), True),
    ("RS7-fund", lambda: detect_rs7(
        {"author": "", "erfahrung": ""})[0], False),
    ("RS7-unbelegte-erfahrung", lambda: detect_rs7(
        {"author": "Frank Hartung", "erfahrung": "Praxisgetestet.",
         "erfahrung_beleg": ""})[0], False),
    ("RS7-ok-ohne-erfahrung", lambda: detect_rs7(
        {"author": "Frank Hartung", "erfahrung": "", "erfahrung_beleg": ""})[0], True),
    ("RS7-ok-mit-beleg", lambda: detect_rs7(
        {"author": "Frank Hartung", "erfahrung": "Dokumentierter Test.",
         "erfahrung_beleg": "WP-2026-001"})[0], True),
    ("Verify-link-schutz", lambda: _verify(
        "Text [A](https://a.check24.net/x) mehr Text.",
        "Text [A](https://a.check24.net/x) mehr Text, ergänzt.")[0], True),
    ("Verify-link-verlust", lambda: _verify(
        "Text [A](https://a.check24.net/x) mehr.",
        "Text ohne Link.")[0], False),
    ("Verify-h2-stabil", lambda: _verify(
        "## Eins\n\n## Zwei", "## Eins\n\n## Zwei (Frage?)")[0], True),
    ("Verify-h2-weg", lambda: _verify(
        "## Eins\n\n## Zwei", "## Eins")[0], False),
    ("Verify-laenge", lambda: _verify(
        "x" * 1000, "x" * 400)[0], False),
    # --- Publikations-Vertrag (WF-54C4/#607, 05.10.2026) ---------------------
    # Der Anlass: Die KI-Heilung schrieb Flesch 44,3 und „In diesem Beitrag…“
    # in einen Live-Artikel; die Struktur-Prüfung fand nichts, blockiert hat
    # erst der nächste Deploy-Lauf. Diese Fälle frieren die Schreib-Wache ein.
    ("Vertrag-gute-aenderung-still", lambda: not _vertrag_gruende(
        {"slug": "gut", "fm": 'title: "X"',
         "body": "Kurzer Satz hier. Noch ein kurzer Satz. Der Text bleibt leicht."},
        "Kurzer Satz steht hier. Noch ein kurzer Satz folgt. Der Text bleibt "
        "leicht lesbar."), True),
    ("Vertrag-flesch-absturz", lambda: any(
        g.startswith("V1") for g in _vertrag_gruende(
            {"slug": "hart", "fm": 'title: "X"',
             "body": "Kurzer Satz hier. Noch ein kurzer Satz. Der Text bleibt leicht."},
            "Die vorgenommene Umstrukturierung der Tariflandschaft, die sich "
            "insbesondere durch die Anpassung der Netzentgelte sowie der "
            "CO₂-Bepreisung im Kontext der fortschreitenden Dekarbonisierung der "
            "Energieversorgungssysteme ergibt, erfordert eine grundlegende "
            "Neubewertung der individuellen Vertragskonstellationen, wobei die "
            "Berücksichtigung der jeweiligen Verbrauchsprofile unabdingbar "
            "erscheint.")), True),
    ("Vertrag-neue-intro-formel", lambda: any(
        g.startswith("V2") for g in _vertrag_gruende(
            {"slug": "r7", "fm": 'title: "X"',
             "body": "Kurzer Satz hier. Noch ein kurzer Satz. Der Text bleibt leicht."},
            "In diesem Beitrag erfährst du alles Wichtige. Der Text bleibt leicht "
            "lesbar. Kurze Sätze helfen jedem Leser.")), True),
    ("Fix-RS2-RS3-deterministisch", lambda: (
        lambda out: detect_rs2(out[0])[0] and detect_rs3(out[0])[0] and out[1] == ["RS2", "RS3"]
    )(fix_rs2_rs3_deterministic(
        "## Warum ist der Vertrag wichtig\n\nKurzer Text.\n\n"
        "## Typische Fehler beim Tarifwechsel\n\nMehr Text.\n\n"
        "## Häufige Fragen\n\n### Frage 1?\nAntwort."
    )), True),
    # --- RS3-EINZIGARTIGKEIT (Issue #766, 15.10.2026) -----------------------
    # 435 „kritische“ Paare entstanden aus EINEM Satz, den der Heiler in 30
    # Artikel schrieb. Diese Fälle frieren die Dauerheilung ein: ein Pool
    # statt eines Satzes, eine Messung statt einer Hoffnung – und der alte
    # Satz bleibt auffindbar, aber unvergebbar.
    ("Faustregel-Pool-ist-gross-genug", lambda: (
        len(FAUSTREGEL_POOL) >= 12
        and len({satz for _t, satz, _w in FAUSTREGEL_POOL}) == len(FAUSTREGEL_POOL)
    ), True),
    ("Faustregel-Pool-ist-zahlfrei", lambda: all(
        not re.search(r"\d", satz) for satz in faustregel_saetze()), True),
    ("Faustregel-Pool-paare-sind-keine-Dopplung", lambda: (
        lambda cu, saetze: max(
            (len(cu.ngrams(a, cu.PHRASE_LEN) & cu.ngrams(b, cu.PHRASE_LEN))
             for i, a in enumerate(saetze) for b in saetze[i + 1:]), default=0
        ) < 5
    )(_messung(), faustregel_saetze()), True),
    ("Faustregel-Legacy-ist-nicht-im-Pool", lambda: (
        FAUSTREGEL_LEGACY not in faustregel_saetze()), True),
    ("Faustregel-Wahl-ist-deterministisch", lambda: (
        lambda a, b: a == b and a is not None
    )(waehle_faustregel("Strom sparen im Haushalt", set(), slug="strom")[0],
      waehle_faustregel("Strom sparen im Haushalt", set(), slug="strom")[0]), True),
    # Der eigentliche Regressionstest: Ein Lauf über N Artikel darf N-mal
    # NICHT denselben Satz vergeben – genau das war der #766-Befund. Der
    # gemeinsame Kontext ist der Betriebsfall (ein Lauf, ein Vermeidungs-Set).
    ("Faustregel-Lauf-vergibt-keinen-Satz-zweimal", lambda: (
        lambda ktx, pool: (
            lambda saetze: len(set(saetze)) == len(saetze) == len(pool)
        )([waehle_faustregel(f"Thema {i} im Haushalt", set(),
                             slug=f"artikel-{i}", kontext=ktx)[0]
           for i in range(len(pool))])
    )({"belegung": set(), "index": {}, "vermeiden": set()},
      FAUSTREGEL_POOL), True),
    # Der Wähler MUSS den Bestand mitmessen: Steht ein Satz schon (auch nur
    # als Fast-Kopie mit ≥ 5 geteilten 7-Grammen), wird er nicht vergeben.
    ("Faustregel-Wahl-meidet-Bestandstreffer", lambda: (
        lambda cu, satz: all(
            waehle_faustregel("Energie und Strom im Haushalt", set(),
                              slug=f"neu-{i}",
                              kontext={"belegung": set(),
                                       "index": {"alt": cu.ngrams(satz, cu.PHRASE_LEN)},
                                       "vermeiden": set()})[0] != satz
            for i in range(3))
    )(_messung(), FAUSTREGEL_POOL[3][1]), True),
    ("Fix-Legacy-Faustregel-wird-ersetzt", lambda: (
        lambda out: (FAUSTREGEL_LEGACY not in out[0]
                     and out[1] == 1
                     and ".." not in out[0]
                     and detect_rs3(out[0])[0]
                     and _links(out[0]) == _links(
                         f"**Faustregel:** {FAUSTREGEL_LEGACY}"))
    )(ersetze_generische_faustregel(
        f"Text davor.\n\n**Faustregel:** {FAUSTREGEL_LEGACY}\n\n## Fazit\n\nEnde.",
        slug="dsl-wechselbonus", titel="DSL-Wechselbonus sichern")), True),
    ("Fix-Legacy-Faustregel-ist-idempotent", lambda: (
        lambda einmal: ersetze_generische_faustregel(
            einmal, slug="x", titel="y")[1] == 0
    )(ersetze_generische_faustregel(
        f"**Faustregel:** {FAUSTREGEL_LEGACY}\n\nRest.", slug="x",
        titel="Strom sparen")[0]), True),
    ("Fix-Legacy-erkennt-auch-Typografie-Varianten", lambda: (
        lambda out: out[1] == 1
    )(ersetze_generische_faustregel(
        "**Faustregel:** Prüfe vor jeder Entscheidung zuerst die Gesamtkosten\u00a0"
        "über die volle Laufzeit und vergleiche mindestens zwei aktuelle "
        "Alternativen, bevor du dich vertraglich festlegst.",
        slug="konto", titel="Konto")), True),
    # Gegenprobe: Ein EIGENER Satz, der nur so ähnlich klingt, bleibt stehen –
    # sonst wäre der Heiler ein Freibrief für fremde Formulierungen.
    ("Fix-Legacy-laesst-aehnlichen-Satz-stehen", lambda: (
        lambda out: out[1] == 0 and "eigenen Worten" in out[0]
    )(ersetze_generische_faustregel(
        "**Faustregel:** Prüfe mit eigenen Worten zuerst die Gesamtkosten "
        "über die ganze Laufzeit und vergleiche mehrere Alternativen.",
        slug="konto", titel="Konto")), True),
    # Ohne freien Satz wird NICHTS geschrieben (fail-closed, kein neuer
    # Massensatz) – der Grund wird gemeldet.
    ("Faustregel-ohne-freien-Satz-schreibt-nichts", lambda: (
        lambda out: out[0] == out[1] and out[0] is not None and len(out[0]) > 0
    )((lambda ktx, body: (ersetze_generische_faustregel(
        body, slug="a", titel="Energie", kontext=ktx)[0], body))(
        {"belegung": set(faustregel_saetze()), "vermeiden": set()},
        f"**Faustregel:** {FAUSTREGEL_LEGACY}")), True),
    # --- WF-D4E0 (#821): RS5-Kontext & deterministische RS4/RS5-Heilung -----
    ("Reserve-RS5-Jahreszahl-ohne-Behauptung-frei", lambda: (
        _reserve_numeric_claim_findings(
            "Pauschale Aussagen zu den Preisen im Jahr 2026 bringen dir nichts. "
            "Digitale Vertragspapiere sind kein Spartrend für 2026."
        ) == []
    ), True),
    ("Reserve-RS5-Frist-belegt-und-frei", lambda: (
        # 25.10.2026 KONVERGENZ (WF-D4E0 #821 + #865/#867): freistehende
        # Fristen ohne Beleg bleiben Befund (die Gegenprüfung liegt im
        # Vertragstest test_echte_unbelegte_zahl_bleibt_rot); ausdrückliche
        # Modell-/Annahme-Kennzeichnung deckt denselben Satz.
        _reserve_numeric_claim_findings(
            "Drei Monate reichen zum Prüfen nicht.") != []
        and _reserve_numeric_claim_findings(
            "**Annahme:** Drei Monate reichen zum Prüfen nicht.") == []
    ), True),
    ("Reserve-RS5-Modellrechnung-Sektion-deckt-Folgesatz", lambda: (
        _reserve_numeric_claim_findings(
            "## Modellrechnung: 500 € ohne Bonusannahme\n\n"
            "Startest du mit den Abos erst nach sechs Monaten, bleiben nur "
            "150 € statt 300 € im Jahr."
        ) == []
    ), True),
    ("Fix-RS4-RS5-deterministisch", lambda: (
        lambda out: (
            detect_rs4(out[0])[0]
            and _reserve_numeric_claim_findings(out[0]) == []
            and out[1] == ["RS4", "RS5"]
        )
    )(fix_rs4_rs5_deterministic(
        "Ein kurzer Check spart dir oft 150 Euro im Jahr.\n\n"
        "## Checkliste für den Start\n\n"
        "- [ ] Kontoauszüge prüfen.\n"
        "- [ ] Tarife vergleichen.\n"
        "- [ ] Wechseltermin notieren.\n"
    )), True),
]


def wirkungsprobe() -> int:
    """Beweist an einem defekten Mustertext, dass die deterministische Heilung wirkt."""
    roh = (
        "Viele Kunden zahlen jedes Jahr 150 Euro zu viel für ihr Konto.\n\n"
        "**Das Wichtigste in Kürze**\n\n"
        "- Du prüfst deine Auszüge in Ruhe.\n"
        "- Du vergleichst die Konditionen deiner Bank.\n"
        "- Du stellst teure Zusatzkarten rechtzeitig ab.\n\n"
        "## Warum lohnt sich der Kontocheck\n\n"
        "Ein altes Girokonto kostet oft 10 Euro im Monat.\n\n"
        "## Typische Fehler beim Kontowechsel\n\n"
        "Wer Fristen übersieht, zahlt weiter Gebühren.\n\n"
        "## Checkliste für den Wechsel\n\n"
        "- [ ] Auszüge der letzten Monate prüfen.\n"
        "- [ ] Freigrenze für den Geldeingang kontrollieren.\n"
        "- [ ] Neue Bank auswählen und Daueraufträge umziehen.\n\n"
        "## Häufige Fragen\n\n"
        "### Wie schnell klappt der Wechsel?\n"
        "Der Wechsel klappt meist unkompliziert.\n"
    )
    vorher_rs2 = detect_rs2(roh)[0]
    vorher_rs3 = detect_rs3(roh)[0]
    vorher_rs4 = detect_rs4(roh)[0]
    vorher_rs5 = _reserve_numeric_claim_findings(roh)
    if vorher_rs2 or vorher_rs3 or vorher_rs4 or not vorher_rs5:
        print("🛑 Wirkungsprobe redaktions_standard: Ausgangstext nicht defekt genug.")
        return 2
    geheilt, schritte_23 = fix_rs2_rs3_deterministic(
        roh, slug="probe-konto", titel="Kontocheck"
    )
    geheilt, schritte_45 = fix_rs4_rs5_deterministic(geheilt)
    nachher_rs2 = detect_rs2(geheilt)[0]
    nachher_rs3 = detect_rs3(geheilt)[0]
    nachher_rs4 = detect_rs4(geheilt)[0]
    nachher_rs5 = _reserve_numeric_claim_findings(geheilt)
    if not (nachher_rs2 and nachher_rs3 and nachher_rs4) or nachher_rs5:
        print(
            f"🛑 Wirkungsprobe redaktions_standard fehlgeschlagen: "
            f"RS2={nachher_rs2}, RS3={nachher_rs3}, RS4={nachher_rs4}, RS5={nachher_rs5}"
        )
        return 1
    nochmal, schritte_nochmal = fix_rs4_rs5_deterministic(
        fix_rs2_rs3_deterministic(geheilt, slug="probe-konto", titel="Kontocheck")[0]
    )
    if nochmal != geheilt or schritte_nochmal:
        print("🛑 Wirkungsprobe redaktions_standard: Heilung ist nicht idempotent.")
        return 1
    print(
        f"✅ Wirkungsprobe redaktions_standard: "
        f"{'+'.join(schritte_23 + schritte_45)} geheilt "
        f"(RS5 {len(vorher_rs5)} → 0, Fixpunkt bestätigt)."
    )
    return 0


def selftest():
    fehler = []
    for name, fn, erwartung in SELFTEST:
        try:
            ist = fn()
        except Exception as e:  # noqa: BLE001
            fehler.append(f"{name}: Exception {e}")
            continue
        if ist != erwartung:
            fehler.append(f"{name}: {ist}, erwartet {erwartung}")
    if fehler:
        print("🛑 SELBSTTEST FEHLGESCHLAGEN – die Wache selbst ist defekt "
              "(Exit 2, keine Datei wird geschrieben):")
        for f in fehler:
            print("   -", f)
        return 2
    print(f"✅ Selbsttest: {len(SELFTEST)} eingefrorene Fälle bestanden.")
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if "--selftest" in sys.argv:
        return selftest()
    if "--wirkungsprobe" in sys.argv:
        return wirkungsprobe()
    if "--register-korrektur" in sys.argv:
        return register_korrektur()

    today = datetime.date.today().isoformat()
    raw_paths = [SINGLE_FILE] if SINGLE_FILE else list_post_paths()
    posts = [load_article(p) for p in raw_paths]
    posts = [p for p in posts if p]
    if NEW_ONLY and not SINGLE_FILE:
        posts = [p for p in posts if p["date"] == today]
    results = [analyse_article(a) for a in posts]
    gehärtet = []
    history = []
    verworfen = []

    # --- Deterministische Heilung (RS7 + RS2/RS3), immer bei --fix ----------
    if DO_FIX:
        # RS3-EINZIGARTIGKEIT (#766): Der Kontext misst den Bestand EINMAL vor
        # dem Lauf (Belegung der Pool-Sätze + 7-Gramm-Index je Artikel). Damit
        # kann kein Heiler-Schritt einen Satz vergeben, den das Tagesaudit
        # gleich wieder als Dopplung melden müsste – und ein Lauf mit 30
        # Heilungen vergibt 30 verschiedene Sätze.
        kontext = faustregel_kontext(_bestand_texte())
        offen = []
        vorrat = faustregel_vorrat(kontext)
        if vorrat < FAUSTREGEL_VORRAT_WARNUNG:
            print(f"  ⚠ Faustregel-Vorrat fast leer: {vorrat} freie Variante(n) "
                  f"– Pool erweitern, sonst kann der Heiler nichts mehr setzen "
                  f"(#766).")
        for a in posts:
            if _is_ymyl_sealed(a["path"]):
                print(f"  ⏭ YMYL-Siegel aktiv – RS7 übersprungen: {a['slug']}")
                continue
            neu = None if NUR_FAUSTREGEL else fix_rs7(a["path"], a)
            if neu and not DRY_RUN:
                with open(a["path"], "w", encoding="utf-8") as fh:
                    fh.write(neu)
                gehärtet.append(f"{a['slug']}: RS7 (fehlenden Autor ergänzt; keine Erfahrung erfunden)")
                history.append({"slug": a["slug"], "regel": "RS7",
                                "aktion": "fix-deterministisch"})
                a = load_article(a["path"]) or a
            with open(a["path"], encoding="utf-8") as fh:
                content = fh.read()
            parts = content.split("---", 2)

            def _schreibe(neu_body_inhalt: str, meldung: str, regel: str):
                """Schreibt EINE Heilung (oder plant sie im Dry-Run)."""
                nonlocal a
                vertrag_err = _vertrag_gruende(a, neu_body_inhalt)
                if vertrag_err:
                    offen.append(f"{a['slug']}: {meldung} – vom Publikations-"
                                 f"Vertrag gestoppt ({vertrag_err[0]})")
                    return
                neu_content = join_article(parts[1], neu_body_inhalt, parts[0])
                if not DRY_RUN:
                    with open(a["path"], "w", encoding="utf-8") as fh:
                        fh.write(neu_content)
                    gehärtet.append(f"{a['slug']}: {meldung}")
                    history.append({"slug": a["slug"], "regel": regel,
                                    "aktion": "fix-deterministisch"})
                    a = load_article(a["path"]) or a
                _kontext_aktualisieren(kontext, a["slug"], neu_content)

            # RS3-EINZIGARTIGKEIT (#766): eingefrorenen Heiler-Satz ersetzen
            neu_body, n_ersetzt, meldung = ersetze_generische_faustregel(
                a["body"], slug=a["slug"], titel=a["title"], kontext=kontext)
            if n_ersetzt and neu_body != a["body"]:
                _schreibe(neu_body, meldung, "RS3-EINZIGARTIG")
            elif meldung:
                # Kein freier Satz im Pool: NICHTS wird geschrieben. Ein
                # zweiter Massensatz wäre schlimmer als der erste (#766).
                offen.append(f"{a['slug']}: {meldung}")
            neu_body, rs_det = fix_rs2_rs3_deterministic(
                a["body"], slug=a["slug"], kontext=kontext, titel=a["title"],
                nur_rs3=NUR_FAUSTREGEL)
            if rs_det and neu_body != a["body"]:
                _schreibe(neu_body, f"{', '.join(rs_det)} (deterministisch)",
                          "+".join(rs_det))
            if not NUR_FAUSTREGEL:
                neu_body, rs_det45 = fix_rs4_rs5_deterministic(a["body"])
                if rs_det45 and neu_body != a["body"]:
                    _schreibe(neu_body, f"{', '.join(rs_det45)} (deterministisch)",
                              "+".join(rs_det45))
        if not DRY_RUN and gehärtet:
            print(f"✅ Deterministisch geheilt: {len(gehärtet)} Schritt(e)")
        # Ein offener RS3-EINZIGARTIG-Befund ist kein Betriebsgeräusch: Ohne
        # freien Satz bleibt ein generischer Satz im Bestand und das Audit
        # meldet ihn weiter. Sichtbar machen – in der CI als Annotation,
        # sonst als Logzeile (Muster: #607, unsichtbare Ausgänge).
        for eintrag in offen:
            if os.environ.get("GITHUB_ACTIONS"):
                print(f"::warning::RS3-EINZIGARTIG: {eintrag.replace('%', '%25')[:220]}")
            else:
                print(f"  ⚠ RS3-EINZIGARTIG offen: {eintrag}")
        posts = [load_article(p) for p in raw_paths]
        posts = [p for p in posts if p]
        if NEW_ONLY and not SINGLE_FILE:
            posts = [p for p in posts if p["date"] == today]
        results = [analyse_article(a) for a in posts]

    # --- KI-Heilung (RS1–RS6), bei --fix --ai -------------------------------
    if DO_FIX and DO_AI:
        kandidaten = [r for r in results
                      if r["hart_missing"] or not r["rs5"][0] or not r["rs6"][0]
                      or _reserve_numeric_claim_findings(load_article(r["path"])["body"])]
        kandidaten.sort(key=lambda r: (
            len(r["hart_missing"]), r["rs5"][2] + r["rs6"][2]), reverse=True)
        backlog = 0
        if "--backlog" in sys.argv:
            backlog = int(sys.argv[sys.argv.index("--backlog") + 1])
        budget = 3
        if "--ai-budget" in sys.argv:
            budget = int(sys.argv[sys.argv.index("--ai-budget") + 1])
        if NEW_ONLY:
            budget = min(budget, 3)  # Geburtstag: nie mehr als 3 KI-Durchgänge
        ziel = kandidaten[:backlog] if backlog else kandidaten[:budget]
        for r in ziel:
            if _is_ymyl_sealed(r["path"]):
                print(f"  ⏭ YMYL-Siegel aktiv – KI-Heilung übersprungen: {r['slug']}")
                verworfen.append({"slug": r["slug"], "regel": "YMYL",
                                  "aktion": "ki-heilung-ymyl-skip",
                                  "grund": "Hochrisiko-Artikel mit gültigem Siegel – keine KI-Umschreibung"})
                continue
            a = load_article(r["path"])
            if not a:
                continue
            neu_body = heal_article_ai(a, r, verworfen)
            if not neu_body:
                continue
            # Prompt-Gerüst („TITEL: …/ARTIKEL:") ist kein Artikeltext: Die KI
            # spiegelt den Kopf des Auftrags, die Prüfung sieht nur Links/H2/
            # Länge – das Gerüst rutschte so bis in die Auslieferung (7b51187).
            neu_body, geruest = strip_generator_scaffolding(neu_body)
            if geruest:
                print(f"  ⚠ Prompt-Gerüst der KI-Antwort entfernt "
                      f"({len(geruest)} Zeile(n): {geruest[0].strip()[:40]!r})")
            if DRY_RUN:
                print(f"  [dry-run] würde heilen: {r['slug']}")
                continue
            with open(r["path"], encoding="utf-8") as fh:
                content = fh.read()
            parts = content.split("---", 2)
            with open(r["path"], "w", encoding="utf-8") as fh:
                fh.write(join_article(parts[1], neu_body, parts[0]))
            gehärtet.append(f"{r['slug']}: {', '.join(r['hart_missing']) or 'RS5/RS6'}")
            history.append({"slug": r["slug"], "regel": "RS1-RS6",
                            "aktion": "fix-ki"})
        # Nach der Heilung neu bewerten
        posts = [load_article(p) for p in raw_paths]
        posts = [p for p in posts if p]
        if NEW_ONLY and not SINGLE_FILE:
            posts = [p for p in posts if p["date"] == today]
        results = [analyse_article(a) for a in posts]
        if not DRY_RUN and gehärtet:
            print(f"✅ KI-Heilung: {len(gehärtet)} Artikel auf Redaktions-Standard.")

    # --- Gate-Modus: harte Funde → draft (Entwurf statt Publikation) --------
    if DO_GATE:
        if not NEW_ONLY:
            print("⚠ --gate nur zusammen mit --new-only sinnvoll (Schutz des Bestands).")
        fail = [r for r in results if r["hart_missing"]]
        if len(fail) > 3:
            print("🛑 CIRCUIT-BREAKER: >3 neue Artikel mit harten Funden – "
                  "die Wache gilt als fehlerhaft, NICHTS wird geparkt.")
            write_report(results, "gate (Circuit-Breaker)")
            return 1
        for r in fail:
            if DRY_RUN:
                print(f"  [dry-run] würde parken: {r['slug']}")
                continue
            try:
                import park_state
                park_state.hold(r["path"],
                                "Redaktions-Standard: " + ", ".join(r["hart_missing"]))
                print(f"  🅿 → Entwurf: {r['slug']} ({', '.join(r['hart_missing'])})")
                history.append({"slug": r["slug"], "regel": "GATE",
                                "aktion": "draft (hold)"})
            except Exception as e:  # noqa: BLE001
                print(f"  ⚠ parken fehlgeschlagen ({r['slug']}): {e}")

    # Ein gestoppter Schreibvorgang ist ein Befund, kein Betriebsgeräusch:
    # in der CI als Annotation sichtbar. Die Workflows kürzen Exit-Codes mit
    # `|| echo` (redaktions-standard-neu.yml) – ohne diese Zeile verschwände
    # der Stopp im Log-Rauschen, und genau solche unsichtbaren Ausgänge hat
    # der Vorfall #607 begünstigt.
    if verworfen and os.environ.get("GITHUB_ACTIONS"):
        for v in verworfen:
            grund = str(v.get("grund", "")).replace("%", "%25").replace("\n", "%0A")
            print(f"::warning::Publikations-Vertrag: {v['slug']} – {grund[:220]}")

    # --- Report + Historie ---------------------------------------------------
    mode = ("gate" if DO_GATE else
            "fix+ai" if (DO_FIX and DO_AI) else
            "fix" if DO_FIX else
            "new-only" if NEW_ONLY else "report")
    if not DRY_RUN and not SINGLE_FILE:
        write_report(results, mode, gehärtet, verworfen)
        log_history(history + verworfen)

    n_offen = sum(1 for r in results if r["hart_missing"])
    print(f"Redaktions-Standard: {len(results)} Artikel geprüft · "
          f"{n_offen} mit offenen harten Regeln · "
          f"{sum(r['rs5'][2] for r in results)} ungehedgte Zahlen-Sätze · "
          f"{sum(r['rs6'][2] for r in results)} Phantom-Quellen · "
          f"{len(verworfen)} KI-Änderung(en) vom Publikations-Vertrag gestoppt.")
    return 1 if (n_offen and DO_GATE and not DRY_RUN) else 0


if __name__ == "__main__":
    sys.exit(main())
