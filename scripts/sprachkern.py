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
        return True  # Ohne Messung keine automatische Änderung.
    return _ymyl_gate.automatic_write_protected(path)


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


# ------------------------------------- Pflicht-Kennzeichnung (01.11.2026, #964)
# DER VORFALL: Der deterministische RS5-Heiler
# (`redaktions_standard._heal_rs5_block`) suchte die ERSTE Satzgrenze im
# Absatz und setzte dort „ im Modellfall“ / „ als Beispielwert“ ein – ohne zu
# prüfen, ob dieser Punkt eine Satzgrenze ist. Bei „ca.“, „z. B.“, „Nov.“
# oder einer Jahreszahl steht er mitten im Wort; bei „… 460 €.“ steht er
# hinter dem Betrag, aber vor dem Rest des Satzes. Ergebnis im Bestand:
# 494 zerstückelte Kennzeichnungen in 63 Dateien – live, in Snippets und in
# den Faktenfrische-Befunden von #964 („ca im Modellfall. 500 €“,
# „bis zum 30 als Beispielwert. November“, „3 als Modellwert. **Tür“).
#
# Diese Muster sind die gemeinsame Wahrheit (SSOT): `write_verified`
# verweigert jede Schrift, die eine NEUE Ruine einführt, und
# `textverstaendnis_guard` meldet sie als R18 (Audit + Publish-Gate).
PFLICHT_MARKER = (
    r"(?:im Modellfall|als Beispielwert|als Modellwert|im Rechenfall|"
    r"im Rechenbeispiel|als Modellannahme)"
)

# R18a – Kennzeichnung klebt an einer Abkürzung: „ca im Modellfall.“,
# „z als Modellwert.“ Die Abkürzung hat ihren Punkt an die Kennzeichnung
# verloren. Im deutschen Satz nie korrekt.
PFLICHT_MARKER_ABKUERZUNG = re.compile(
    rf"\b(?:ca|z|B|evtl|ggf|bzw|etc|usw|inkl|zzgl|max|min|Mio|Mrd|Std|"
    rf"Abs|Nr|vgl|sog)\s+{PFLICHT_MARKER}\b", re.I)

# R18b – Kennzeichnung klebt an einer nackten Zahl: „bis zum 30 als
# Beispielwert. November“, „3 als Modellwert. **Tür-Zugluftstopper**“.
# Zahl und Wort gehören zusammen; die Kennzeichnung hat sie getrennt.
PFLICHT_MARKER_ZAHL = re.compile(rf"\d\s+{PFLICHT_MARKER}\b")

# R18c – Kennzeichnung beendet einen Satz, obwohl danach Text folgt:
# „… fehlen am Ende über 460 € als Beispielwert. Rechne einen Bonus …“.
# „als Beispielwert“ ist adverbial und kann einen Satz nicht beschließen –
# es sei denn als Prädikativ nach einer Kopula („… ist ein Beispielwert.“).
# Genau diese Ausnahme bleibt frei; alles andere ist zerschnittenes Deutsch.
PFLICHT_MARKER_SATZ = re.compile(rf"{PFLICHT_MARKER}\.[ \t]+(?=\S)")
_KOPULA_PRAEDIKATIV = re.compile(
    r"\b(?:ist|sind|war|waren|bleibt|bleiben|wird|werden|gilt|gelten|heißt|"
    r"heisst|nennt man|nennen wir)\b[^.!?]{0,60}$", re.I)

PFLICHT_MARKER_RUINEN = (
    ("R18-MARKER-ABKUERZUNG", PFLICHT_MARKER_ABKUERZUNG,
     "Pflicht-Kennzeichnung klebt an einer Abkürzung"),
    ("R18-MARKER-ZAHL", PFLICHT_MARKER_ZAHL,
     "Pflicht-Kennzeichnung klebt an einer nackten Zahl"),
    ("R18-MARKER-SATZ", PFLICHT_MARKER_SATZ,
     "Pflicht-Kennzeichnung zerschneidet einen Satz"),
)


def pflicht_marker_funde(text: str) -> list:
    """Zerstückelte Modell-/Beispiel-Kennzeichnungen (R18a–R18c) als Liste.

    Rückgabe: [(Regel, Fundstelle, Zeichenindex)]. Deterministisch, offline.
    Leere Liste ⇔ keine Ruine.
    """
    text = text or ""
    out = []
    for regel, rx, _desc in PFLICHT_MARKER_RUINEN:
        if regel == "R18-MARKER-SATZ":
            continue
        for m in rx.finditer(text):
            out.append((regel, m.group(0), m.start()))
    # R18c: Die Kennzeichnung beschließt einen Satz, obwohl danach Text folgt.
    # „als Beispielwert“ ist adverbial und kann keinen Satz beschließen –
    # außer als Prädikativ nach einer Kopula („… ist ein Beispielwert.“).
    # Diese Form bleibt frei; alles andere ist zerschnittenes Deutsch.
    for m in PFLICHT_MARKER_SATZ.finditer(text):
        anfang = _satzanfang_vor(text, m.start())
        if _KOPULA_PRAEDIKATIV.search(text[anfang:m.start()]):
            continue
        out.append(("R18-MARKER-SATZ", m.group(0).strip(), m.start()))
    out.sort(key=lambda e: e[2])
    return out


# --- Reparatur (deterministisch, ohne Bedeutungseingriff) -------------------
# Die Reparatur setzt die Kennzeichnung NICHT neu irgendwohin, sondern stellt
# die vom Heiler zerschnittene Stelle wieder her und hängt die Kennzeichnung
# als eigenen Teilsatz an das Ende des betroffenen Satzes:
#
#   „… über 460 € als Beispielwert. Rechne …“
#     → „… über 460 €. Rechne …“                (Satz wiederhergestellt)
#     → „… über 460 €; das ist ein Beispielwert.“ (Kennzeichnung sauber)
#
# Diese Form ist nach jedem Satzende grammatisch (nach Betrag, nach Verb,
# nach Nebensatz) und trägt weiterhin den Ausdruck, den RS5 als
# Modellannahme akzeptiert. Der Wortlaut der Aussage bleibt unverändert.
_MARKER_NOMEN = (
    ("im Modellfall", "Modellwert"),
    ("als Modellwert", "Modellwert"),
    ("als Beispielwert", "Beispielwert"),
    ("im Rechenfall", "Rechenbeispiel"),
    ("im Rechenbeispiel", "Rechenbeispiel"),
    ("als Modellannahme", "Modellannahme"),
)

_ABKUERZUNG_PUNKT = (
    r"(?:ca|z|B|evtl|ggf|bzw|etc|usw|inkl|zzgl|max|min|Mio|Mrd|Std|Abs|Nr|"
    r"vgl|sog|d\.h|u\.a|z\.B|Dr|Prof|St|Tel|Art|Rn|S)"
)
_MONATE = (r"(?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|"
           r"Oktober|November|Dezember)")
_SAETZE_UNABHAENGIG = re.compile(rf"{_ABKUERZUNG_PUNKT}\.$")
_MONATE_RX = re.compile(_MONATE)
_SATZENDE = re.compile(r"[.!?](?=\s|$)")
_ZAHLBEHAUPTUNG = re.compile(
    r"\d[\d.,]*\s*(?:€|EUR|Euro|%|Prozent|kWh|ct|Cent|Mbit/s|GB|MB|km|Watt|W)"
    r"|(?<![\w.,])\d{3,}(?:[.,]\d+)*(?![\w.])", re.I)
# Kopula am Satzende („… ist eine Modellannahme.“) – dort ist die
# Kennzeichnung bereits korrekt als Prädikativ eingebaut.
_KOPULA_ENDE = re.compile(
    r"\b(?:ist|sind|war|waren|bleibt|bleiben|gilt|gelten|heisst|heißt)\b"
    r"[^.!?]{0,40}$", re.I)


def _satz_spans(zeile: str) -> list[tuple[int, int]]:
    """Satzspannen einer Zeile; Abkürzungen und Ordinaldaten sind keine Grenze."""
    spans, start = [], 0
    for m in _SATZENDE.finditer(zeile):
        i = m.start()
        if zeile[i] == "." and _SAETZE_UNABHAENGIG.search(zeile[max(0, i - 8):i + 1]):
            continue
        if (zeile[i] == "." and re.search(r"\d$", zeile[:i])
                and re.match(rf"\s*{_MONATE}\b", zeile[i + 1:])):
            continue
        spans.append((start, i + 1))
        start = i + 1
    if start < len(zeile.rstrip()):
        spans.append((start, len(zeile)))
    return spans


_MARKER_RX = re.compile(rf"\b{PFLICHT_MARKER}\b")
_GLUE_VOR = re.compile(
    rf"(\b{_ABKUERZUNG_PUNKT}|(?<![\d.,])\d{{1,2}})\s+$", re.I)
_TERMINATOR = re.compile(r"[.!?](?=\s|$)")


def _satzende_ab(text: str, pos: int = 0) -> int | None:
    """Index des ersten echten Satzendes ab `pos` (None: kein Satzende)."""
    for m in _TERMINATOR.finditer(text, pos):
        i = m.start()
        if text[i] == ".":
            if _SAETZE_UNABHAENGIG.search(text[max(0, i - 8):i + 1]):
                continue
            if re.search(r"\d$", text[:i]) and _MONATE_RX.match(text[i + 1:]):
                continue
        return i
    return None


def _satzanfang_vor(text: str, pos: int) -> int:
    """Index nach dem letzten echten Satzende vor `pos`."""
    letzte = 0
    for m in _TERMINATOR.finditer(text, 0, pos):
        i = m.start()
        if text[i] == ".":
            if _SAETZE_UNABHAENGIG.search(text[max(0, i - 8):i + 1]):
                continue
            if re.search(r"\d$", text[:i]) and _MONATE_RX.match(text[i + 1:]):
                continue
        letzte = i + 1
    return letzte


def _praedikativ(nomen: str) -> str:
    """Korrekte Artikelform des Teilsatzes: „das ist ein Modellwert.“ /
    „das ist eine Modellannahme.“ – Genus aus dem Nomen, nicht geraten."""
    unbestimmt = "eine" if nomen.endswith(("annahme", "regel", "schätzung")) else "ein"
    return f"das ist {unbestimmt} {nomen}"


def _marker_reparatur(zeile: str, treffer: re.Match, nomen: str) -> str:
    """Repariert EINE zerstückelte Kennzeichnung in einer Zeile."""
    vor, rest = zeile[:treffer.start()], zeile[treffer.end():]
    # (a) Klebstelle: „ca als Modellannahme.“ / „30 als Beispielwert. November“
    #     / „3 als Modellwert. **Tür“ → der Punkt gehört zur Abkürzung, zum
    #     Datum oder zur Ordnungszahl.
    glue = _GLUE_VOR.search(vor)
    if glue and rest.startswith(".") and not rest.startswith(".."):
        return f"{vor[:glue.start()]}{glue.group(1)}.{rest[1:]}"
    # (b) Marker beschließt einen Satz, obwohl Text folgt.
    #     Trägt der Satz eine Zahl, wird sie als Teilsatz ans Satzende gehängt
    #     („… 460 €; das ist ein Beispielwert. Rechne …“).
    #     Trägt er keine, kennzeichnet der Marker nichts und fällt ersatzlos
    #     weg – ein angehängter Füllsatz wäre genau die Maschinen-Prosa, die
    #     #964 abstellt.
    if rest.startswith(".") and rest[1:].strip():
        satz = vor[_satzanfang_vor(vor, len(vor)):]
        if _ZAHLBEHAUPTUNG.search(satz):
            return f"{vor.rstrip()}; {_praedikativ(nomen)}{rest}"
        return f"{vor.rstrip()}{rest}"
    # (c) Marker mitten im Satz: als Teilsatz ans Satzende hängen.
    ohne = vor.rstrip()
    zusammen = ohne + rest
    anfang = _satzanfang_vor(zusammen, len(ohne))
    satzende = _satzende_ab(zusammen, len(ohne)) or _satzende_ab(zusammen, 0)
    if satzende is None:
        trenner = "" if zusammen.rstrip().endswith(('.', '!', '?')) else "."
        return f"{zusammen.rstrip()}{trenner} {_praedikativ(nomen)}."
    satz = zusammen[anfang:satzende]
    rumpf = zusammen[:satzende].rstrip().rstrip(",;:")
    if _ZAHLBEHAUPTUNG.search(satz) and not _KOPULA_ENDE.search(satz):
        return f"{rumpf}; {_praedikativ(nomen)}{zusammen[satzende:]}"
    return f"{rumpf}{zusammen[satzende:]}"


# Überschrift, Tabelle, Zitat und Code sind keine Fließsätze: dort kann die
# Kennzeichnung keinen Satz zerschneiden. Aufzählungspunkte SIND Fließtext –
# gerade die umbrochenen Zeilen darin tragen die Ruinen.
_STRUKTUR_ZEILE = re.compile(r"(?:#{1,6}\s|[|>]|```|\*\*?[^*]*\*\*?\s*$)")


def pflicht_marker_heilen(text: str) -> tuple[str, int]:
    """Repariert zerstückelte Kennzeichnungen zeilenweise. → (Text, Anzahl).

    Tabellen, Zitate, Überschriften, Listen und Code bleiben unangetastet:
    dort steht die Kennzeichnung nie in einem Fließsatz, den sie zerschneiden
    könnte. Idempotent; die Aussage (jede Zahl, jeder Betrag) bleibt erhalten.
    """
    if not text or not pflicht_marker_funde(text):
        return text, 0
    geaendert = 0
    zeilen = text.split("\n")
    for i, zeile in enumerate(zeilen):
        if not pflicht_marker_funde(zeile):
            continue
        kopf = zeile.lstrip()
        # Nur echte Struktur bleibt unangetastet. Eine Zeile, die mit einer
        # Fett-Marke beginnt („**Modellrechnung:** …“), ist Fließtext.
        if not kopf or _STRUKTUR_ZEILE.match(kopf):
            continue
        aktuell, anzahl = zeile, 0
        # Von hinten nach vorn: Positionen der noch offenen Treffer bleiben gültig.
        for treffer in reversed(list(_MARKER_RX.finditer(zeile))):
            nomen = next((w for p, w in _MARKER_NOMEN if p == treffer.group(0)),
                         "Modellwert")
            neu = _marker_reparatur(aktuell, _MARKER_RX.search(aktuell, treffer.start()), nomen) \
                if _MARKER_RX.search(aktuell, treffer.start()) else aktuell
            if neu != aktuell:
                anzahl += 1
                aktuell = neu
        if anzahl and not pflicht_marker_funde(aktuell):
            zeilen[i] = aktuell
            geaendert += anzahl
    return "\n".join(zeilen), geaendert


def politur_ruine_funde(text: str) -> list:
    """Alle Politur-Ruinen in `text` als Liste (Regel, Fundstelle).

    Deterministisch, offline, ohne Schonzeiten – diese Muster sind
    im deutschen Satz nie korrekt. Rückgabe ist leer ⇔ kein Befund.
    """
    out = []
    for regel, rx, _desc in POLITUR_RUINEN:
        for m in rx.finditer(text):
            out.append((regel, m.group(0)))
    for regel, fund, _pos in pflicht_marker_funde(text):
        out.append((regel, fund))
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



DESCRIPTION_ZEILE = re.compile(r"(?m)^description:[^\n]*(?:\n|$)")


def setze_description(fm: str, text: str) -> str:
    """Schreibt GENAU EINE description-Zeile ins Frontmatter.

    WARUM NICHT ERSETZEN-ODER-ANHÄNGEN (26.10.2026, main baute nicht mehr):
    Die alte Fassung ersetzte per Regex die erste Fundstelle und HÄNGTE sonst
    eine Zeile an. Traf die Regex eine vorhandene Zeile nicht (z. B. nach
    einem Merge mit zwei description-Zeilen oder bei ungewöhnlicher
    Formatierung), standen danach zwei Schlüssel im Frontmatter. YAML lehnt
    das beim Bauen ab (`mapping key "description" already defined`) – der
    gesamte Hugo-Build stirbt, und zwar erst in der CI, nicht beim Autor.
    Deshalb: alle vorhandenen description-Zeilen fallen weg, die neue steht
    direkt hinter `title:` (oder ganz oben). Idempotent und ohne Duplikat.
    """
    wert = text.replace('"', "'").replace("\n", " ").strip()
    neue_zeile = f'description: "{wert}"'
    zeilen = [z for z in fm.splitlines() if not z.startswith("description:")]
    if zeilen and zeilen[0].strip() == "---":
        zeilen = zeilen[1:]
    einfuegen = 0
    for i, zeile in enumerate(zeilen):
        if zeile.startswith("title:"):
            einfuegen = i + 1
            break
    zeilen.insert(einfuegen, neue_zeile)
    return "\n".join(zeilen).rstrip("\n") + "\n"


def rebuild(a: dict, new_body: str, new_description: str | None = None) -> str:
    """Setzt die Datei FM-sicher aus Teilen zusammen (Kanon-Naht via post_utils)."""
    fm = a["fm"]
    if new_description is not None:
        fm = setze_description(fm, new_description)
        if len(DESCRIPTION_ZEILE.findall(fm)) != 1:
            raise ValueError("Frontmatter trägt nach dem Setzen nicht genau eine description-Zeile")
    return join_article(fm, new_body, a["prefix"])


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
