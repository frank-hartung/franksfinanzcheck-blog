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
#    ... --fix                                            # deterministisch (RS7)
#    ... --fix --ai [--backlog N] [--ai-budget N]         # KI-Heilung
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
import json
import os
import re
import sys
import unicodedata
import urllib.request

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

from post_utils import (list_post_paths, slug_of,  # noqa: E402
                        join_article, strip_generator_scaffolding)
import groq_config  # noqa: E402

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
    """True, wenn der Artikel Hochrisiko + freigegeben + Hash gültig ist."""
    if not _YMYL_AVAILABLE or _ymyl_gate is None:
        return False
    try:
        result = _ymyl_gate.evaluate_path(path)
        return bool(result.get("approved") and not result.get("blocking") and result.get("risk") == "hoch")
    except Exception:
        return False

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
NEW_ONLY = "--new-only" in sys.argv
DRY_RUN = "--dry-run" in sys.argv

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

def load_article(path):
    try:
        content = open(path, encoding="utf-8").read()
    except Exception:
        return None
    parts = content.split("---", 2)
    if len(parts) != 3:
        return None
    fm, body = parts[1], parts[2]
    if "draft: true" in fm:
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
    """RS3: ≥ 1 markierte Faustregel. → (ok, details)"""
    n = len(re.findall(r"faustregel", body, re.I))
    if n < 1:
        return False, "keine Faustregel markiert"
    return True, f"{n} Faustregel-Nennung(en)"


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
    # Strip internal links so year-bearing slugs are not claims. External
    # Markdown links leave a marker that proves sentence-level evidence.
    def _link_marker(match):
        target = match.group(2).strip().lower()
        return " QUELLENLINK " if target.startswith(("https://", "http://")) else " INTERNLINK "
    text = link_re.sub(_link_marker, text)
    lines = [ln for ln in text.splitlines()
             if not ln.lstrip().startswith(("#", ">", "<!--"))]
    text = re.sub(r"\s+", " ", " ".join(lines))
    sentences = re.split(r"(?<=[.!?])\s+", text)
    number_words = (
        r"ein(?:e|em|en|es)?|zwei|drei|vier|f[uü]nf|sechs|sieben|acht|"
        r"neun|zehn|elf|zw[oö]lf|dreizehn|vierzehn|f[uü]nfzehn|"
        r"sechzehn|siebzehn|achtzehn|neunzehn|zwanzig|drei[ßs]ig|"
        r"vierzig|f[uü]nfzig|sechzig|siebzig|achtzig|neunzig|hundert|"
        r"tausend|mehrere|einige")
    units = (
        r"€|eur\b|euro\b|cent\b|ct\b|%|prozent\b|kwh\b|wh\b|mwh\b|"
        r"kilowattstunden?\b|wattstunden?\b|watt\b|(?<![a-z])w\b|"
        r"kw\b|kilowatt\b|mbit/s\b|gbit/s\b|gb\b|mb\b|"
        r"tage?n?\b|wochen?\b|monate?n?\b|jahre?n?\b|stunden?\b|"
        r"minuten?\b|kilometer\b|km\b|meter\b|grad\b|°c\b")
    numeric_claim = re.compile(
        rf"(?ix)(?:§\s*\d+[a-z]?\b|"
        rf"(?<!\w)(?:\d[\d.,]*|{number_words})\s*(?:{units})(?!\w)|"
        rf"(?<!\w)\d{{3,}}(?:[.,]\d+)?(?!\w))")
    model_marker = re.compile(
        r"\b(?:rechenbeispiel|modellrechnung|modellfall|annahme|annahmen|"
        r"musterrechnung|beispielrechnung|angenommen|unterstellen wir)\b", re.I)
    findings = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not numeric_claim.search(sentence):
            continue
        if "QUELLENLINK" in sentence:
            continue
        # A model label must not disguise a statutory clause or a claimed study.
        if "§" not in sentence and model_marker.search(sentence):
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
    content = open(path, encoding="utf-8").read()
    parts = content.split("---", 2)
    return join_article(fm, parts[2], parts[0])


# ---------------------------------------------------------------------------
# KI-Heilung (RS1–RS6) mit Verifikation
# ---------------------------------------------------------------------------

def _call_ai(prompt, max_tokens=6000):
    """Gemini zuerst, dann Groq (gleiche Logik wie profi_polish)."""
    ua = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
          "Chrome/126.0 Safari/537.36")
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if gemini_key:
        try:
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            req = urllib.request.Request(
                "https://generativelanguage.googleapis.com/v1beta/models/"
                "gemini-3-flash-preview:generateContent?key=" + gemini_key,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json", "User-Agent": ua})
            resp = json.loads(urllib.request.urlopen(req, timeout=180).read())
            text = resp["candidates"][0]["content"]["parts"][0]["text"].strip()
            if text:
                return text
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠ Gemini: {e}")
    if groq_config.available():
        try:
            text = groq_config.chat(prompt, max_tokens=max_tokens, timeout=180)
            if text:
                return text
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠ Groq: {e}")
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
    if not res["rs5"][0]:
        weiche.append(f"RS5 harte Zahlen ohne Einordnung ({res['rs5'][2]} Sätze)")
    if not res["rs6"][0]:
        weiche.append(f"RS6 Phantom-Quellen ({res['rs6'][2]} Stellen)")
    if not fehlend and not weiche:
        return None
    if not (os.environ.get("GEMINI_API_KEY") or groq_config.available()):
        print("  ⚠ keine API-Keys – KI-Heilung übersprungen")
        return None

    auftraege = []
    if "RS1" in fehlend:
        auftraege.append(
            "1. Ergänze direkt NACH der Einleitung (vor der ersten H2-Überschrift) "
            "das Modul:\n\n**Das Wichtigste in Kürze**\n\n- <Bullet 1>\n- <Bullet 2>\n"
            "- <Bullet 3>\n\nDrei bis vier konkrete Kernaussagen des Artikels "
            "(Zahlen nur mit ca./rund/Spanne), keine Floskeln.")
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
            "5. Ehrlichkeit (WiWo-Standard): Ersetze harte Zahlen ohne Einordnung "
            "durch ehrliche Spannen („ca. X–Y €“, „in der Regel“) oder kennzeichne "
            "sie klar als Rechenbeispiel. Entferne ALLE Phantom-Quellen "
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
    if res2["rs5"][2] > res["rs5"][2] or res2["rs6"][2] > res["rs6"][2]:
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
    content = open(path, encoding="utf-8").read()
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
            eintraege = yaml.safe_load(open(KORREKTUR_LOG, encoding="utf-8")) or []
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
]


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
    if "--register-korrektur" in sys.argv:
        return register_korrektur()

    today = datetime.date.today().isoformat()
    posts = [load_article(p) for p in list_post_paths()]
    posts = [p for p in posts if p]
    if NEW_ONLY:
        posts = [p for p in posts if p["date"] == today]
    results = [analyse_article(a) for a in posts]
    gehärtet = []
    history = []
    verworfen = []

    # --- Deterministische Heilung (RS7), immer bei --fix --------------------
    if DO_FIX:
        for a in posts:
            if _is_ymyl_sealed(a["path"]):
                print(f"  ⏭ YMYL-Siegel aktiv – RS7 übersprungen: {a['slug']}")
                continue
            neu = fix_rs7(a["path"], a)
            if neu and not DRY_RUN:
                with open(a["path"], "w", encoding="utf-8") as fh:
                    fh.write(neu)
                gehärtet.append(f"{a['slug']}: RS7 (fehlenden Autor ergänzt; keine Erfahrung erfunden)")
                history.append({"slug": a["slug"], "regel": "RS7",
                                "aktion": "fix-deterministisch"})
        if not DRY_RUN and gehärtet:
            print(f"✅ RS7 deterministisch geheilt: {len(gehärtet)} Artikel")

    # --- KI-Heilung (RS1–RS6), bei --fix --ai -------------------------------
    if DO_FIX and DO_AI:
        kandidaten = [r for r in results
                      if r["hart_missing"] or not r["rs5"][0] or not r["rs6"][0]]
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
            content = open(r["path"], encoding="utf-8").read()
            parts = content.split("---", 2)
            with open(r["path"], "w", encoding="utf-8") as fh:
                fh.write(join_article(parts[1], neu_body, parts[0]))
            gehärtet.append(f"{r['slug']}: {', '.join(r['hart_missing']) or 'RS5/RS6'}")
            history.append({"slug": r["slug"], "regel": "RS1-RS6",
                            "aktion": "fix-ki"})
        # Nach der Heilung neu bewerten
        posts = [load_article(p) for p in list_post_paths()]
        posts = [p for p in posts if p]
        if NEW_ONLY:
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
    if not DRY_RUN:
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
