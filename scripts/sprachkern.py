#!/usr/bin/env python3
"""Sprachkern – gemeinsame Offline-Basis der Sprach-Politur OHNE API.

Auftrag (Frank, 25.09.2026): „Sämtliche Blogartikel dauerhaft automatisch mit
DeepL Write oder LanguageTool glätten (KOSTENLOS, OHNE API nachbauen) und auf
Premium-Level einer Profi-Agentur beheben."

Dieser Kern ist der geteilte, netzfreie Teil der beiden Engines:
  - scripts/grammar_check.py  – LanguageTool-Nachbau (Korrektur-Ebene)
  - scripts/sprachglatt.py    – DeepL-Write-Nachbau (Glätt-Ebene)

Er liefert NUR Mechanik – Schutzzonen, Case-Erhalt, Regel-Executor,
Artikel-Lauf. Die REGELN liegen bewusst genau einmal, je in der Engine,
die sie besitzt (Qualitäts-Regelwerk: „Jede Lektorats-Regel genau einmal").

Sicherheitsverträge (gelten für BEIDE Engines):
  - Schutzzonen: Code-Blöcke, Inline-Code, Markdown-Links/-Bilder inkl.
    Linkziel, Shortcodes, URLs, HTML-Tags/Kommentare werden maskiert und
    NIE verändert (auch Link-TEXTE nicht – sie sind Marken-/Anker-Verträge).
  - Frontmatter: title wird nie geschrieben (Cover-Marken-Lock, check_covers),
    description wird nur über die sichere Regelschicht geheilt.
  - Verifikation vor dem Schreiben: Link-/Shortcode-/Überschriften-Zahl
    konstant, Wortzahl ≥ 90 % – sonst wird die Datei NICHT geschrieben.
  - Selbsttest vor JEDEM Schreibvorgang; Abweichung = Exit 2, kein Schreiben.
"""
from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from post_utils import list_post_paths, join_article  # noqa: E402

# YMYL-Schutz (Premium-Fix #613): Hochrisiko-Artikel mit gültigem Siegel
# dürfen nicht von der Sprach-Politur umgeschrieben werden. Der Schutz liegt
# im Kern, damit alle Engines (grammar_check, sprachglatt, zeit_rechtschreibung)
# automatisch profitieren.
try:
    import editorial_review_gate as _ymyl_gate
    _YMYL_AVAILABLE = True
except Exception:
    _ymyl_gate = None
    _YMYL_AVAILABLE = False


def _is_ymyl_sealed(path: str) -> bool:
    if not _YMYL_AVAILABLE or _ymyl_gate is None:
        return False
    try:
        result = _ymyl_gate.evaluate_path(path)
        return bool(result.get("approved") and not result.get("blocking") and result.get("risk") == "hoch")
    except Exception:
        return False

# ---------------------------------------------------------------- Schutzzonen
PROTECT_RX = re.compile(
    r"(```.*?```"                # Code-Block
    r"|`[^`\n]+`"                # Inline-Code
    r"|\{\{[<%].*?[>%]\}\}"      # Hugo-Shortcodes
    r"|!?\[[^\]]*\]\([^)]*\)"    # MD-Links & Bilder inkl. Ziel (Text = Anker-Vertrag!)
    r"|https?://\S+"             # URLs
    r"|<!--.*?-->"               # HTML-Kommentare
    r"|<[^>\n]+>"                # HTML-Tags
    r")", re.S)

_SENT_TRAP = re.compile(r"(?:\d{1,2}\.){1,3}\s*$")


def protect_zones(text: str):
    """Maskiert Schutzzonen durch Platzhalter. Rückgabe: (maskiert, Originale)."""
    origs = []

    def repl(m):
        origs.append(m.group(0))
        return f"\x00Z{len(origs) - 1}\x00"

    return PROTECT_RX.sub(repl, text), origs


def unprotect(text: str, origs: list) -> str:
    for i, o in enumerate(origs):
        text = text.replace(f"\x00Z{i}\x00", o)
    return text


def case_match(src: str, canon: str) -> str:
    """Übernimmt die Anfangsgroßschreibung des Fundwortes auf den Kanon."""
    if src[:1].isupper():
        return canon[:1].upper() + canon[1:]
    return canon


# ------------------------------------------------------------ Regel-Executor
# Regel = (ID, Regex, Fixer, Label)
#   Fixer: Callable[Match -> str]  = Auto-Fix (100 % sicher)
#          None                    = NUR Report (Vorschlagsschicht)

def scan_rules(text: str, rules) -> list:
    """Liefert Funde (dicts) ohne zu schreiben. Identity-Fixe (fix == found)
    sind Falsch-Alarme und werden verworfen (Sicherheitsnetz für alle Engines)."""
    body, _ = protect_zones(text)
    out = []
    for rid, rx, fixer, label in rules:
        for m in rx.finditer(body):
            fix = fixer(m) if fixer else None
            if fixer is not None and fix == m.group(0):
                continue
            ctx = body[max(0, m.start() - 36): m.end() + 36].replace("\n", " ").strip()
            out.append({
                "rule": rid, "found": m.group(0), "fix": fix,
                "label": label, "ctx": ctx,
            })
    return out


def apply_rules(text: str, rules):
    """Führt Auto-Fixes aus, bewahrt Schutzzonen. Rückgabe: (text, n_fixes, funde)."""
    body, origs = protect_zones(text)
    n = 0
    funde = []
    for rid, rx, fixer, label in rules:
        if fixer is None:
            continue
        def _safe_sub(m, _fixer=fixer):
            ersatz = _fixer(m)
            return m.group(0) if ersatz == m.group(0) else ersatz
        found = [m for m in rx.finditer(body) if fixer(m) != m.group(0)]
        if not found:
            continue
        for m in found:
            funde.append({
                "rule": rid, "found": m.group(0), "fix": fixer(m),
                "label": label,
                "ctx": body[max(0, m.start() - 36): m.end() + 36]
                       .replace("\n", " ").strip(),
            })
        body, _k = rx.subn(_safe_sub, body)
        n += len(found)
    return unprotect(body, origs), n, funde


# ------------------------------------------------------------ Artikel-Lauf
def load_articles(files=None, new_only=False, include_drafts=False):
    """Lädt Posts (Bundle + Legacy). new_only: Frontmatter-Datum ODER Slug = heute."""
    today = datetime.now(timezone.utc).date().isoformat()
    arts = []
    paths = files or list_post_paths()
    for path in paths:
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
        parts = content.split("---", 2)
        if len(parts) < 3:
            continue
        fm, body = parts[1], parts[2]
        if not include_drafts and "draft: true" in fm:
            continue

        def get(key, _fm=fm):
            m = re.search(rf"^{key}:\s*[\"']?(.+?)[\"']?\s*$", _fm, re.M)
            return m.group(1).strip() if m else ""

        if new_only:
            in_slug = today in os.path.basename(os.path.dirname(path)) \
                or today in os.path.basename(path)
            if not (in_slug or get("date").startswith(today)):
                continue
        arts.append({
            "path": path,
            "slug": (os.path.basename(os.path.dirname(path))
                     if os.path.basename(path) == "index.md"
                     else os.path.basename(path)[:-3]),
            "title": get("title"), "description": get("description"),
            "fm": fm, "body": body, "content": content, "prefix": parts[0],
        })
    return arts


def link_count(text: str) -> int:
    return len(re.findall(r"\[[^\]]*\]\([^)]*\)", text))


def shortcode_count(text: str) -> int:
    return len(re.findall(r"\{\{[<%].*?[>%]\}\}", text))


def heading_count(text: str) -> int:
    return len(re.findall(r"(?m)^#{1,6}\s", text))


def words(text: str) -> int:
    return len(re.findall(r"\w+", text, re.UNICODE))


# ------------------------------------------------- Politur-Ruinen (30.09.2026)
# Issue #482 – vier echte Textdefekte, alle aus automatisierten Politur-Läufen
# (Sprachglatt/Grammatik/SEO-Heiler), alle durch write_verified durchgegangen,
# weil die Verifikation nur Struktur zählt (Links, Shortcodes, Überschriften,
# Wortzahl), nie den Ergebnis-Text selbst. Diese Muster sind der gemeinsame
# Detektor (SSOT): sprachkern.write_verified verweigert jede Schrift, die eine
# NEUE Ruine enthält, und textverstaendnis_guard meldet sie als R11–R14
# (tägliches Audit + Publish-Gate). Jedes Muster ist am gesamten Content
# (61 Artikel + alle Seiten) gegen False-Positive geprüft – 0 Treffer.
POLITUR_RUINEN = [
    # R11: durch Leerraum zerrissene Jahreszahl („Nutze 20 26 gezielt
    # Mindestbestellwerte“, Weihnachtsartikel 30.09.2026). Tausender-Gruppen
    # sind DREIER-Blöcke („40 000“) – Zweier-Zweier mit 19/20-Anfang ist
    # immer eine Ruine.
    ("R11-JAHRESZAHL-SPLIT",
     re.compile(r"\b(19|20)[\s\u00A0\u202F]\d{2}\b"),
     "Jahreszahl durch Leerraum zerrissen"),
    # R12: Artikel + nackte Zahl + Präposition („Du bist der 0 am deutschen
    # Strommarkt“, Ökostrom-Artikel 30.09.2026 – Überrest einer defekten
    # Ersetzungs-Kaskade).
    ("R12-ZAHL-RUINE",
     re.compile(r"\b(der|die|das|den|dem|des)\s+\d{1,2}\s+"
                r"(am|im|auf|für|vom|zum|beim|an|in|aus|über)\b", re.I),
     "nackte Zahl nach Artikel (Ersetzungs-Ruine)"),
    # R13: Ordinal-Datum ohne Punkt („es ist der 2 Januar“, Weihnachtsartikel
    # 30.09.2026; Zwillingsfund „am 1 Januar“, Neujahrs-Entwurf 30.09.2026).
    # Korrekt ist „2. Januar“ – die Zahl vor dem Monatsnamen trägt immer
    # einen Punkt; der Lookbehind schließt „20. November“ aus.
    ("R13-DATUM-PUNKT",
     re.compile(r"(?<![\d.])(\d{1,2})\s+"
                r"(Januar|Februar|März|April|Mai|Juni|Juli|August|"
                r"September|Oktober|November|Dezember)\b"),
     "Ordinal-Datum ohne Punkt"),
    # R14: Marker-Ruine am Zeilenanfang („SATZ: | **CHECK24-Vergleich** |
    # – | | | | |“, E-Bike-Artikel 30.09.2026 – halbfertige Tabellenzeile
    # eines Politur-Laufs). Debug-/Platzhalter-Marker sind niemals Inhalt.
    ("R14-MARKER-RUINE",
     re.compile(r"(?m)^\s*(SATZ|TOKEN|MARKER|PLACEHOLDER|TODO|FIXME|"
                r"XXX|DEBUG|ROW|ZEILE|NL|REST)\s*[:|]"),
     "Marker-/Debug-Ruine am Zeilenanfang"),
    # R15 ist eine Phrasen-Regel und wohnt in textverstaendnis_guard.
    # R16: Der Generator spricht mit sich selbst. Das Ausgabeformat der
    # KI-Prompts lautet „TITLE: …\nDESCRIPTION: …\n<Artikel>“;
    # `generate_drafts.parse_article` hat diese Kopfzeilen bis zum
    # 02.10.2026 nur erkannt, wenn sie EXAKT auf Zeile 1 und 2 standen.
    # Setzte das Modell eine Leerzeile dazwischen – am 02.10.2026 real
    # geschehen – blieben die Marker im Fließtext stehen UND die
    # Beschreibung wurde aus der Marker-Zeile gebildet:
    #
    #   description:     "TITLE: Preiswert surfen: So findest du den …"
    #   pin_description: "*Werbung | TITLE: Preiswert surfen: …"
    #   Fließtext Zeile 1: "TITLE: Preiswert surfen: …"
    #
    # Gestoppt hat den Entwurf nur zufällig die Zeichenlänge, keine Wache.
    # Mit Meta-Description und Pin-Text wäre die Prompt-Ruine bis zu
    # Google und Pinterest durchgeschlagen.
    #
    # Nur VERSALE ASCII-Marker am Zeilenanfang: „Beispiel:“, „Faustregel:“
    # und „Tipp:“ bleiben unberührt – „TITLE:“ ist im deutschen Fließtext
    # nie Inhalt.
    ("R16-PROMPT-ECHO",
     re.compile(r"(?m)^\s{0,3}(TITLE|DESCRIPTION|BODY|ARTIKEL|ARTICLE|"
                r"KEYWORDS|META|METADESCRIPTION|SLUG|H1|OUTPUT|AUSGABE|"
                r"ANTWORT|PROMPT|SYSTEM|ASSISTANT|USER|PILLAR)\s*:"),
     "Prompt-/Ausgabeformat-Marker im Artikeltext"),
]

# Dieselben Marker ohne Zeilenanker – für einzelne Frontmatter-Felder
# (description, pin_description, kurzantwort), in die die Ruine am
# 02.10.2026 ebenfalls geflossen ist. EINE Quelle, zwei Einsatzorte: Wer
# die Marker-Liste oben erweitert, erweitert automatisch auch diese Prüfung.
PROMPT_ECHO_RX = POLITUR_RUINEN[-1][1]
PROMPT_ECHO_FELD_RX = re.compile(
    PROMPT_ECHO_RX.pattern.replace(r"(?m)^\s{0,3}", r"(?:^|\|)\s*"))


def prompt_echo_im_feld(wert: str) -> str:
    """Erste Prompt-Marker-Fundstelle in einem Frontmatter-Wert (sonst '')."""
    treffer = PROMPT_ECHO_FELD_RX.search(str(wert or ""))
    return treffer.group(0).strip() if treffer else ""


def politur_ruine_funde(text: str) -> list:
    """Alle Politur-Ruinen in `text` als Liste (Regel, Fundstelle).

    Deterministisch, offline, ohne Schonzeiten – diese Muster sind
    im deutschen Satz nie korrekt. Rückgabe ist leer ⇔ kein Befund.
    """
    out = []
    for regel, rx, _desc in POLITUR_RUINEN:
        for m in rx.finditer(text):
            out.append((regel, m.group(0)))
    return out


def write_verified(a: dict, new_content: str, engine: str) -> tuple[bool, str]:
    """Verifikation VOR dem Schreiben (Repo-Vertrag). Rückgabe: (geschrieben, Grund)."""
    if _is_ymyl_sealed(a["path"]):
        return False, "YMYL-Siegel aktiv – keine automatische Politur"
    old, new = a["content"], new_content
    if link_count(old) != link_count(new):
        return False, "Link-Zahl verändert"
    if shortcode_count(old) != shortcode_count(new):
        return False, "Shortcode-Zahl verändert"
    if heading_count(old) != heading_count(new):
        return False, "Überschriften-Zahl verändert"
    if words(new) < 0.90 * words(old):
        return False, "Wortzahl unter 90 % des Originals"
    # Politur-Ruinen (R11–R14, Issue #482): keine Schrift darf eine NEUE
    # Ruine einführen. Bestehende Ruinen blockieren die Heilung nicht –
    # sonst wäre ein Artikel mit Alt-Ruine für jede Politur eingefroren.
    alte_ruinen = set(politur_ruine_funde(old))
    neue_ruinen = set(politur_ruine_funde(new)) - alte_ruinen
    if neue_ruinen:
        regel, fund = sorted(neue_ruinen)[0]
        return False, f"Politur-Ruine eingeführt ({regel}: „{fund}“)"
    with open(a["path"], "w", encoding="utf-8") as fh:
        fh.write(new)
    return True, "ok"



def rebuild(a: dict, new_body: str, new_description: str | None = None) -> str:
    """Setzt die Datei FM-sicher aus Teilen zusammen (Kanon-Naht via post_utils)."""
    fm = a["fm"]
    if new_description is not None:
        fm2 = re.sub(r"(?m)^description:\s*[\"']?.+?[\"']?\s*$",
                     'description: "' + new_description.replace('"', "'") + '"',
                     fm, count=1)
        if fm2 == fm and new_description:
            fm2 = fm.rstrip("\n") + '\ndescription: "' + new_description.replace('"', "'") + '"\n'
        fm = fm2
    return join_article(fm, new_body, a["prefix"])


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
