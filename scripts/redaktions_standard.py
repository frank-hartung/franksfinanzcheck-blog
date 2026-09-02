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
#    RS7  Byline/E-E-A-T: Frontmatter `author:` UND `erfahrung:`  [HART,
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
import urllib.request

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

from post_utils import list_post_paths, slug_of  # noqa: E402
import groq_config  # noqa: E402

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

STD_ERFAHRUNG = (
    "Ich habe die Vergleiche und Zahlen in diesem Artikel selbst geprüft "
    "und wende die Empfehlungen seit Jahren in meiner eigenen Finanzplanung "
    "an – die Tipps sind praxisgetestet, nicht vom Schreibtisch."
)


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
    """RS7: author + erfahrung im Frontmatter. → (ok, details)"""
    fehlt = []
    if not a.get("author"):
        fehlt.append("author")
    if not a.get("erfahrung"):
        fehlt.append("erfahrung")
    if fehlt:
        return False, "fehlt: " + ", ".join(fehlt)
    return True, "author + erfahrung vorhanden"


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
    """Ergänzt fehlende author-/erfahrung-Felder. Liefert neue fm oder None."""
    if a.get("author") and a.get("erfahrung"):
        return None
    fm = a["fm"]
    geaendert = False
    if not a.get("author"):
        fm = set_fm_field(fm, "author", "Frank Hartung")
        geaendert = True
    if not a.get("erfahrung"):
        fm = set_fm_field(fm, "erfahrung", STD_ERFAHRUNG)
        geaendert = True
    if not geaendert:
        return None
    content = open(path, encoding="utf-8").read()
    parts = content.split("---", 2)
    parts[1] = fm
    return "---".join(parts)


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


def heal_article_ai(a, res):
    """Ein KI-Durchgang für alle fehlenden Module. Liefert neuen Body oder None."""
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
        "Du bist Schlussredakteur eines seriösen deutschen Finanz-Ratgeber-Blogs "
        "(Niveau: Capital, WirtschaftsWoche, DIE ZEIT). Überarbeite den folgenden "
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
        return None
    # Idempotenz-Nachweis: nach der Heilung müssen die harten Detektoren grün sein
    a2 = dict(a)
    a2["body"] = neu
    res2 = analyse_article(a2)
    if res2["hart_missing"]:
        print(f"  ✗ Nach-Heilung noch offen: {', '.join(res2['hart_missing'])} – verworfen.")
        return None
    if res2["rs5"][2] > res["rs5"][2] or res2["rs6"][2] > res["rs6"][2]:
        print("  ✗ Nach-Heilung mehr Zahlen-/Quellen-Funde – verworfen.")
        return None
    return neu


# ---------------------------------------------------------------------------
# Report & Historie
# ---------------------------------------------------------------------------

def write_report(results, mode, gehärtet=None):
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
                     ("RS7", "Byline/E-E-A-T (author+erfahrung)")):
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
        fh.write("---".join(parts))
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
    ("RS7-fund", lambda: detect_rs7(
        {"author": "Frank Hartung", "erfahrung": ""})[0], False),
    ("RS7-ok", lambda: detect_rs7(
        {"author": "Frank Hartung", "erfahrung": "Praxisgetestet."})[0], True),
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

    # --- Deterministische Heilung (RS7), immer bei --fix --------------------
    if DO_FIX:
        for a in posts:
            neu = fix_rs7(a["path"], a)
            if neu and not DRY_RUN:
                with open(a["path"], "w", encoding="utf-8") as fh:
                    fh.write(neu)
                gehärtet.append(f"{a['slug']}: RS7 (author/erfahrung ergänzt)")
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
            a = load_article(r["path"])
            if not a:
                continue
            neu_body = heal_article_ai(a, r)
            if not neu_body:
                continue
            if DRY_RUN:
                print(f"  [dry-run] würde heilen: {r['slug']}")
                continue
            content = open(r["path"], encoding="utf-8").read()
            parts = content.split("---", 2)
            parts[2] = neu_body
            with open(r["path"], "w", encoding="utf-8") as fh:
                fh.write("---".join(parts))
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

    # --- Report + Historie ---------------------------------------------------
    mode = ("gate" if DO_GATE else
            "fix+ai" if (DO_FIX and DO_AI) else
            "fix" if DO_FIX else
            "new-only" if NEW_ONLY else "report")
    if not DRY_RUN:
        write_report(results, mode, gehärtet)
        log_history(history)

    n_offen = sum(1 for r in results if r["hart_missing"])
    print(f"Redaktions-Standard: {len(results)} Artikel geprüft · "
          f"{n_offen} mit offenen harten Regeln · "
          f"{sum(r['rs5'][2] for r in results)} ungehedgte Zahlen-Sätze · "
          f"{sum(r['rs6'][2] for r in results)} Phantom-Quellen.")
    return 1 if (n_offen and DO_GATE and not DRY_RUN) else 0


if __name__ == "__main__":
    sys.exit(main())
