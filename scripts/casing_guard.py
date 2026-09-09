#!/usr/bin/env python3
# ============================================================
#  CASING-GUARD – Groß-/Kleinschreibung, komplett (selbst entscheidend)
#
#  AUFTRAG (Bestand seit 10.08.2026; Premium-Ausbau 09.09.2026 auf Franks
#  Bitte „Prüfung der Groß- und Kleinschreibung einfügen, Fehler im ganzen
#  Blog finden, Blogautomatik auf Premium-Level"):
#  Der Guard war eine reine Akronym-Wache (C1–C3). Er prüft jetzt die
#  VOLLSTÄNDIGE deutsche Groß-/Kleinschreibung – 16 Regeln, deterministisch
#  statt Modell-Bauchgefühl, mit Selbsttest, Gate, Historie und Report.
#
#  REGELN
#    C1   Akronym-Kanon: „dsl"/„Dsl" → „DSL", „KfZ" → „Kfz" (Liste =
#         tag_casing.ACRONYMS: DSL, WLAN, DNS, VPN, IBAN, FTTH, DoH, SSD …)
#    C2   Akronym-Durchkopplung: „DSL Tarif" → „DSL-Tarif"
#    C3   Marken-Durchkopplung: „CHECK24 Vergleichsportal" → „CHECK24-Vergleichsportal"
#    C4   Nominalisierung: „zum sparen" → „zum Sparen" (nur nach zum/zur/beim/
#         ins/ans/aufs/übers/ums/vom – nie nach Modalverb, kein False-Positive)
#    C5   Feste Wendungen: „in der regel" → „in der Regel", „zum beispiel" →
#         „zum Beispiel", „im allgemeinen" → „im Allgemeinen" …
#    C6   Nominalisierte Adjektive: „etwas neues" → „etwas Neues", „nichts
#         genaues" → „nichts Genaues" (nur wenn kein Nomen danach folgt)
#    C7   Satzanfang nach . ! ? und am Absatzanfang → groß. Abkürzungs-aware:
#         „z. B.", „Mio.", „1.", „30.11." lösen KEINEN Fix aus (Falle #1)
#    C8   Anrede-Konsistenz (Hausduktus: „du", klein): „kann Du" → „kann du".
#         NIE am Satzanfang und NIE nach „**Label:**" – beides ist Duden-konform
#    C9   Marken-Kanon: „FritzBox"/„FRITZ! Box"/„Fritz! Box" → „FRITZ!Box",
#         „check24" → „CHECK24" (Hersteller-Schreibweise; congstar/idealo/ebay
#         bleiben bewusst klein – das ist korrekt, kein Fehler)
#    C10  Einheiten-Kanon: „KWH"/„Kwh" → „kWh", „Mbit/S" → „Mbit/s"
#    C11  GROSSBUCHSTABEN-Shouting: im Kompositum heilbar
#         („Zahlungs-ZUSATZ-Risiko" → „Zahlungs-Zusatz-Risiko"); freies
#         Shouting (NICHT/IMMER) ist Redaktionsentscheidung → REPORT + Dichte
#    C12  Title-Case-Leak in Überschriften (KI-Erblastung englischer Art:
#         „Den Stichtag 30.11. Kennen und nutzen") → Funktionswort/Verb klein
#    C13  Monat/Wochentag/Feiertag klein → groß („im august" → „im August")
#    C14  Binnenmajuskel-CamelCase-Tippfehler („StartSeite") → REPORT
#    C15  Nomen nach Artikel/Präposition/Possessiv klein → groß
#         („dein bonus" → „dein Bonus); nur Wörter aus tag_casing.NOUNS,
#         nie bei mehrdeutigen Wörtern, nie vor einem folgenden Nomen
#    T1   Tags/Kategorien (DISPLAY-ZONE, sichtbar auf Tag-Chips und
#         /tags/-Seite): deutsche Schreibweise + Term-Dedupe.
#         „frugalismus tipps" → „Frugalismus Tipps";
#         „50-30-20-Regel" UND „50 30 20 Regel" → EIN Term statt zwei.
#
#  ZONEN-MODELL (neu – der entscheidende Premium-Punkt)
#  Nicht „Front-Matter ist Tabu", sondern nach Feld-Typ differenziert:
#    PROTECT  keywords, slug, date/lastmod/draft, pillar, author, Bildpfade,
#             URLs, Link-Ziele, Code, Hashtags → NIEMALS anfassen.
#             keywords = SEO-Suchanfragen, die dürfen und sollen klein bleiben.
#    SEO      title, description → nur nachweisbare Tippfehler (C1, C9, C10,
#             C11 im Kompositum, C13). Kein Umstellen, keine Durchkopplung:
#             das Keyword-Setup im Titel bleibt redaktioneller Beschluss.
#    PIN      pin_title, pin_description, cover.alt/caption, kurzantwort →
#             alle Regeln außer C8 (Pinterest-Texte sind sichtbare Werbesätze)
#    TAGS     tags, categories → T1
#    BODY     Fließtext, Überschriften, Listen, Tabellen → alle Regeln
#
#  WIRKUNGSKEIS: Report → Auto-Fix (--fix) → Gate (--gate: harte Restfunde
#  eines FRISCH geborenen Artikels = Entwurf statt Publikation, nie Live-Fehler)
#  → CASING-REPORT.md + data/casing_history.jsonl + .casing_report.json.
#  Im Betrieb: Content-Engine v2 (bei der Geburt), blog_doctor (Visite),
#  seo-weekly (Bestand), reserve_finisher, redaktion_final, blog-health-gate.
#
#  SELBSTTEST (--selftest, wie in der Premium-Familie): eingefrorene ECHTE
#  Fälle inkl. Negativ-Fällen („darf nie angefasst werden"). Abweichung =
#  Exit 2 → es wird keine Datei geschrieben (Sabotage-Schutz der Automatik).
#
#  Aufruf:
#    python3 scripts/casing_guard.py                    # Report (Bestand)
#    python3 scripts/casing_guard.py --fix              # korrigieren
#    python3 scripts/casing_guard.py --dry-run          # Fix simulieren
#    python3 scripts/casing_guard.py --new-only         # Engine-Modus (heute)
#    python3 scripts/casing_guard.py --gate --new-only  # Restfunde → draft
#    python3 scripts/casing_guard.py --selftest         # Sabotage-Schutz
#    python3 scripts/casing_guard.py --json             # .casing_report.json
#    python3 scripts/casing_guard.py --fix --plan       # Pinterest-Masterplan
# ============================================================

from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import tag_casing as tc  # noqa: E402 – gemeinsamer Wortschatz-Kanon

REPORT = ROOT / "CASING-REPORT.md"
HISTORY = ROOT / "data" / "casing_history.jsonl"
JSON_OUT = ROOT / ".casing_report.json"
WHITELIST_FILE = ROOT / "data" / "casing_whitelist.txt"
PLAN_FILE = ROOT / "data" / "pinterest_plan.yaml"

FLAGS = set(sys.argv[1:])
DO_FIX = "--fix" in FLAGS
DRY_RUN = "--dry-run" in FLAGS
NEW_ONLY = "--new-only" in FLAGS
DO_GATE = "--gate" in FLAGS
DO_JSON = "--json" in FLAGS
DO_PLAN = "--plan" in FLAGS
DO_HEADGLUE = "--split-headglue" in FLAGS
NO_ANREDE = "--no-anrede" in FLAGS
DO_SELFTEST = "--selftest" in FLAGS

RULE_TITLES = {
    "C1": "Akronym-Kanon", "C2": "Akronym-Durchkopplung",
    "C3": "Marken-Durchkopplung", "C4": "Nominalisierung",
    "C5": "Feste Wendung", "C6": "Nominalisiertes Adjektiv",
    "C7": "Satzanfang", "C8": "Anrede (Hausduktus)", "C9": "Marken-Kanon",
    "C10": "Einheiten-Kanon", "C11": "Shouting (Report/Fix)",
    "C12": "Title-Case-Leak Heading", "C13": "Monat/Wochentag",
    "C14": "Binnenmajuskel (Report)", "C15": "Nomen-Kleinschreibung",
    "C16": "Redundanter Fettdruck in Überschrift",
    "C17": "Leerraum-Kompositum (Titel/Überschrift)",
    "T1": "Tag-/Kategorie-Kanon",
}
# HART = gate-würdig (Publikation nur, wenn der Fix nichts offenes lässt)
HARD_RULES = {"C1", "C4", "C7", "C9", "C13", "C15", "T1"}
ALL_RULES = set(RULE_TITLES)
# C3 und C17 gehoeren in die Titel-Zone: eine Ueberschrift/Titel ist die
# Term-Form schlechthin, dort ist „DSL Vergleich“ ebenso ein Fehler wie im
# Fliesstext – und der Redaktionsstandard will die Kopplung im H1.
TYPO_RULES = {"C1", "C3", "C9", "C10", "C13", "C11", "C17"}
SEO_RULES = (TYPO_RULES | {"C5", "C12"}) - {"C7", "C8", "C11"}
BODY_RULES = ALL_RULES
PIN_RULES = (ALL_RULES - {"C8", "C11"})   # Pin-Text = Werbung: Betonung bleibt

# ---------------------------------------------------------------------------
# Front-Matter-Zonen
# ---------------------------------------------------------------------------
FM_BRAND_ONLY = {"keywords"}
FM_PROTECT = {"keywords", "slug", "date", "lastmod", "draft", "pillar",
              "author", "ai_generated", "social_posted", "canonical",
              "weight", "type", "layout", "image", "url", "korrektur",
              "cadence_wait", "cadence_demoted", "cadence_grund"}
FM_SEO = {"title", "description"}
FM_PIN = {"pin_title", "pin_description", "pinwand", "alt", "caption",
          "kurzantwort"}
FM_TAGS = {"tags", "categories"}

# ---------------------------------------------------------------------------
# patterns
# ---------------------------------------------------------------------------
# Zerrissene Domains: „www. google. de", „@Anbieter. de" – vor allen Regeln
# maskieren, sonst biegt C7 aus „google." ein „Google." (Kaskaden-Falle).
SPACED_DOMAIN = re.compile(r"(?<![A-Za-z0-9])(?:[a-z0-9][a-z0-9-]*[ ]?\.\s){1,4}"
                           r"(?:de|com|net|org|io|eu|app|info|uk|at|ch)\b")

MASK_PATTERNS = [
    re.compile(r"https?://\S+"),
    re.compile(r"(?<![\w/])/[A-Za-z0-9äöüÄÖÜß_.\-]+(?:/[A-Za-z0-9äöüÄÖÜß_.\-]*)+/"),
    re.compile(r"!\[[^\]]*\]\([^)]*\)"),
    re.compile(r"\[[^\]]*\]\([^)]*\)"),                  # Markdown-Link komplett
    re.compile(r"`[^`]*`"),                               # Inline-Code
    re.compile(r"\{\{<[^>]*>\}\}"),                       # Hugo-Shortcodes
    re.compile(r"\{\{%[^%]*%\}\}"),
    re.compile(r"</?[A-Za-z][^>]*>"),                     # HTML
    re.compile(r"#[A-Za-z0-9_äöüÄÖÜ-]+"),                 # Hashtags (#5g bleibt)
    re.compile(r"@[A-Za-z0-9_.-]+"),                      # Handles
    re.compile(r"\b(?:[a-z0-9-]+\.)+(?:de|com|net|org|io|eu|app|box|one|cloud)\b",
               re.I),                                       # Hostnamen/fritz.box
    re.compile(r"(?<![\d.,])\d{1,2}\.\d{2}\.(?!\d)"),       # Datums-Kürzel 30.11.
    SPACED_DOMAIN,
]
LIST_MARKER = re.compile(r"^(\s*(?:[-*>+]|\d+[.)])\s+)(.*)$")
HEAD_MARK = re.compile(r"^\s*#{1,6}\s")

ACRO_KEYS = sorted(tc.ACRONYMS, key=len, reverse=True)
ACRO_RE = re.compile(r"(?<![A-Za-zÀ-ÿ0-9_-])(" + "|".join(map(re.escape, ACRO_KEYS))
                     + r")(s|en)?(?![A-Za-zÀ-ÿ0-9])")
# 2-Buchstaben-Formen sind im Fließtext mehrdeutig (englisches „it", „led") →
# hier nur melden, nie umbiegen.
ACRO_STRICT = {"it", "ui", "ux", "hd", "ont", "dot", "led", "tv"}

COUPLE_NOUNS = (
    "Tarif", "Tarife", "Tarifen", "Wechselbonus", "Anbieter", "Angebote",
    "Vergleich", "Vergleiche", "Netz", "Netze", "Vertrag", "Verträge",
    "Router", "Empfang", "Signal", "Zugang", "Flat", "Flatrate",
    "Geschwindigkeit", "Internet", "Karte", "Sparplan", "Depot", "Kosten",
    "Gebühren", "Preise", "Home", "Top", "Tipps", "Tipp", "Kabel",
    "Anschluss", "Option", "Optionen", "Paket", "Pakete", "Modem",
    "Server", "Rechner", "Rechnung", "Check", "Ordner", "Box", "Repeater",
    "Passwort", "Kanal", "Funk", "Anzeige", "Vergleichsportal",
    "Vergleichsrechner", "Tarifrechner", "Partnerprogramm", "Bonus",
    "Deal", "Deals", "Gutschein",
)
ACRO_COUPLE = tuple(sorted({v for v in tc.ACRONYMS.values() if v.isupper()},
                          key=len, reverse=True))
C2_RE = re.compile(r"(?<![A-Za-zÀ-ÿ0-9_-])(" + "|".join(map(re.escape, ACRO_COUPLE))
                   + r") ((?:" + "|".join(COUPLE_NOUNS) + r")(?:e[nrms]?|s|n)?)(?![A-Za-zÀ-ÿ])")
BRAND_CANON_WORDS = tuple(sorted({v for v in tc.BRANDS.values()}, key=len, reverse=True))
C3_RE = re.compile(r"(?<![A-Za-zÀ-ÿ0-9])((?:" + "|".join(map(re.escape, BRAND_CANON_WORDS))
                   + r")) ((?:" + "|".join(COUPLE_NOUNS) + r")(?:e[nrms]?|s|n)?)(?![A-Za-zÀ-ÿ])")

NOM_PREPS = ("zum", "zur", "beim", "ins", "ans", "aufs", "übers", "ums", "vom")
C4_RE = re.compile(r"(?<![A-Za-zÀ-ÿ])(" + "|".join(NOM_PREPS) + r") ("
                   + "|".join(sorted(tc.VERBAL_NOUNS, key=len, reverse=True))
                   + r")(?![A-Za-zÀ-ÿ])")
C5_RE = re.compile(r"(?<![A-Za-zÀ-ÿ])(" + "|".join(
    re.escape(k) for k in sorted(tc.FIXED_PHRASES, key=len, reverse=True))
    + r")(?![A-Za-zÀ-ÿ])")
C6_RE = re.compile(r"(?<![A-Za-zÀ-ÿ])(etwas|nichts|alles|vieles|manches|einiges"
                   r"|genug|viel|wenig)\s+([a-zäöüß]+(?:es|e|em|en))(?![A-Za-zÀ-ÿ])"
                   r"(?!\s+[A-ZÄÖÜ][a-zäöüß]{2,})")
C7_RE = re.compile(r"([.!?…])([ \u00a0]+)([a-zäöüß][\wäöüß-]*)")
ABBR_STEMS = ("vs", "bzw", "etc", "usw", "ca", "circa", "Nr", "Abs", "Art", "Mio",
              "Mrd", "Tsd", "Std", "Min", "Sek", "inkl", "exkl", "zzgl", "vgl",
              "sog", "resp", "ff", "lt", "evtl", "ggf", "dgl", "bspw", "usf",
              "mW", "aAO", "sO", "uU", "sog", "bzgl", "Angabe", "Stand")
ABBR_END = re.compile(r"(?:[A-Za-zÀ-ÿ]\.|" + "|".join(ABBR_STEMS) + r"\.)$", re.I)
# NUR die Du-/Euch-Form: die Höflichkeitsform („Sie/Ihnen/Ihre") ist korrekt
# gross und wird vom Person-Kanon des Lektorats (L3) behandelt – hier wäre ein
# Kleinschreib-Fix ein Grammatikfehler.
C8_RE = re.compile(r"(?<=[a-zäöüß,;]) (Du|Dein|Deine|Deinem|Deinen|Deiner|Deines"
                   r"|Dir|Dich|Euch|Euer|Eure|Euren|Eurer)(?![A-Za-zÀ-ÿ])")
C10_RE = re.compile(r"(?<![A-Za-zÀ-ÿ0-9])(" + "|".join(
    map(re.escape, sorted(tc.UNITS, key=len, reverse=True)))
    + r")(?![A-Za-zÀ-ÿ0-9])", re.I)
C11_RE = re.compile(r"(?<![A-Za-zÀ-ÿ0-9_-])([A-ZÄÖÜ][A-ZÄÖÜ0-9]{2,13})"
                    r"(?![A-Za-zÀ-ÿ0-9])")
C11_COMPOUND_RE = re.compile(
    "(?<=[a-z\u00e4\u00f6\u00fc\u00df])([-–—/\u2010\u2011])([A-Z\u00c4\u00d6\u00dc]{3,})(?=\\1)")
C11_OK = (set(tc.ACRONYMS.values()) | set(tc.BRANDS.values()) | set(tc.UNITS.values())
          | {"CO2", "ZÜRS", "BEHG", "URL", "IBAN", "TÜV", "DEKRA", "ADAC", "SIXT",
             "AVM", "OEM", "GmbH", "AG", "HGB", "BGB", "VVG", "MwSt", "USt",
             "FAQ", "SEO", "CTA", "CSS", "JS", "HTML", "PDF", "PNG", "JPG", "SVG",
             "WEBP", "AVIF", "MP4", "HTTP", "HTTPS", "SMTP", "IMAP", "TXT", "API",
             "CPU", "GPU", "RAM", "SSD", "HDD", "LAN", "VLAN", "VPN", "ONT", "FRITZ",
             "ONLINE", "TOP", "INFO", "APP", "TIPP", "EURO", "CENT", "OO", "OOO"})
C11_SHOUT_WORDS = {"NICHT", "IMMER", "ALLES", "KEINE", "KEIN", "SELBST", "MEHR",
                   "GRATIS", "GARANTIERT", "EXTREM", "TOTAL", "SUPER", "MEGA",
                   "HUNDERT", "TAUSEND", "ALLE", "NUR", "SOFORT", "ENDLICH",
                   "EWIG", "DOPPELT", "EINFACH", "FAST", "ÜBERHAUPT", "GENAU",
                   "SCHNELL", "NIEMALS", "WIRKLICH", "EFFEKTIV", "GRATIS", "NIE"}
C13_RE = re.compile(r"(?<![A-Za-zÀ-ÿ0-9])(" + "|".join(sorted(tc.MONTHDAYS))
                    + r")(?![A-Za-zÀ-ÿ])")
# Ausdruecklich erlaubte Binnenmajuskeln (Marken, Produktnamen, Fachformen).
C14_OK = {"MagentaEINS", "PayPal", "YouTube", "GitHub", "LinkedIn", "OpenAI",
          "iPhone", "iPad", "iMac", "E.ON", "Sparkasse", "FinTech", "FinTechs",
          "InsurTech", "LegalTech", "NetCologne", "FranksFinanzcheck",
          "EnergieDirekt", "VivaGas", "Stadtwerke", "WebSite", "SmartHome",
          "GmbH", "AG", "UG"}


def norm_brand_key_ci(w: str) -> bool:
    return tc.norm_brand_key(w) in tc.BRANDS or w in C14_OK


C14_RE = re.compile(r"(?<![A-Za-zÀ-ÿ])([A-ZÄÖÜ][a-zäöüß]{2,}[A-ZÄÖÜ][a-zäöüß]{2,})(?![A-Za-zÀ-ÿ])")
C15_PREPS = (r"dein|deine|deinem|deinen|deiner|deines|mein|meine|memin"
             r"|sein|seine|unser|unsere|euer|kein|keine|ein|eine|einem|einen"
             r"|einer|diesem|jenem|jedem|dem|den|des|im|am|vom|zum|zur|mit"
             r"|für|ohne|gegen|nach|vor|über|unter|durch|an|auf|bei|von|zu"
             r"|als|statt|trotz|wegen|dank|per|je|pro|bis|um")
C15_RE = re.compile(r"(?<![A-Za-zÀ-ÿ])(" + C15_PREPS + r") ([a-zäöüß]{3,})(?![A-Za-zÀ-ÿ])")
C15_STOP = {"du", "man", "wir", "ihr", "mir", "dir", "uns", "euch", "ihnen",
            "mehr", "wieder", "immer", "nur", "auch", "noch", "schon", "fast",
            "hinweg", "zusammen", "allein", "etwa", "so", "wie", "als"}

BRAND_RE = re.compile(r"(?<![A-Za-zÀ-ÿ0-9])("
                      + "|".join(map(re.escape, sorted(tc.BRANDS, key=len, reverse=True)))
                      + r")(?![A-Za-zÀ-ÿ0-9°])", re.I)
LOWER_BRANDS = tc.BRANDS_LOWER


def load_whitelist() -> set:
    """data/casing_whitelist.txt – von Frank geschützte Einzelwoerter."""
    words = set()
    if WHITELIST_FILE.exists():
        for line in WHITELIST_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                words.add(line.lower())
    return words


WHITELIST = load_whitelist()


# ---------------------------------------------------------------------------
# Maskierung der Schutzzonen (LIFO + Fixpunkt wie in der Wachen-Familie)
# ---------------------------------------------------------------------------
def mask(text: str) -> tuple:
    store = {}

    def put(m):
        key = f"\x00{len(store)}\x00"
        store[key] = m.group(0)
        return key

    for pat in MASK_PATTERNS:
        text = pat.sub(put, text)
    return text, store


def unmask(text: str, store: dict) -> str:
    for key in reversed(list(store.keys())):
        text = text.replace(key, store[key])
    for _ in range(8):
        if "\x00" not in text:
            break
        for key, val in reversed(list(store.items())):
            text = text.replace(key, val)
    return text


class Sink(list):
    """Sammelt Funde (dict) und zahlt sie auf Zeile/Zone ein."""

    def add(self, rule: str, before: str, after: str, zeile: int = 0, zone: str = "body") -> None:
        if before == after or not after:
            return
        self.append({"regel": rule, "vorher": before, "nachher": after,
                     "zeile": zeile, "zone": zone})


def protect(word: str) -> bool:
    return word.lower().strip('":.,;!?„“”()[]') in WHITELIST


# ---------------------------------------------------------------------------
# Regeln (Reihenfolge = Reihenfolge in apply_rules)
# ---------------------------------------------------------------------------
def r_c1(text: str, hits: Sink, line: int) -> str:
    def rep(m):
        token = m.group(1)
        tail = m.group(2) or ""
        canon = tc.ACRONYMS.get(token.lower())
        if not canon or protect(token):
            return m.group(0)
        new = canon + tail
        if new == m.group(0):
            return m.group(0)
        if token.lower() in ACRO_STRICT:
            hits.add("C1-report", m.group(0), new, line, "report")
            return m.group(0)
        hits.add("C1", m.group(0), new, line)
        return new
    return ACRO_RE.sub(rep, text)


def r_c2(text: str, hits: Sink, line: int) -> str:
    def rep(m):
        new = f"{m.group(1)}-{m.group(2)}"
        hits.add("C2", m.group(0), new, line)
        return new
    return C2_RE.sub(rep, text)


def r_c3(text: str, hits: Sink, line: int) -> str:
    def rep(m):
        new = f"{m.group(1)}-{m.group(2)}"
        hits.add("C3", m.group(0), new, line)
        return new
    return C3_RE.sub(rep, text)


def r_c4(text: str, hits: Sink, line: int) -> str:
    def rep(m):
        noun = m.group(2)
        new = f"{m.group(1)} {noun[0].upper() + noun[1:]}"
        hits.add("C4", m.group(0), new, line)
        return new
    return C4_RE.sub(rep, text)


def r_c5(text: str, hits: Sink, line: int) -> str:
    def rep(m):
        new = tc.FIXED_PHRASES.get(m.group(0).lower())
        if not new or new == m.group(0) or protect(m.group(0)):
            return m.group(0)
        hits.add("C5", m.group(0), new, line)
        return new
    return C5_RE.sub(rep, text)


ADJ_NOM = {"neues", "neue", "gutes", "gute", "wichtiges", "wichtige", "bestes",
           "beste", "mögliches", "mögliche", "ähnliches", "ähnliche", "gleiches",
           "gleiche", "schlimmes", "schlimme", "sinnvolles", "sinnvolle",
           "praktisches", "praktische", "interessantes", "interessante",
           "teures", "teure", "billiges", "billige", "nützliche", "nützliches",
           "folgende", "allgemeine", "einzelne", "wesentliche", "ganze",
           "richtige", "klare", "reine", "freie", "nöte", "notwendige",
           "beste", "bessere", "gute", "neues"}


def r_c6(text: str, hits: Sink, line: int) -> str:
    def rep(m):
        adj = m.group(2)
        if adj not in ADJ_NOM or protect(adj):
            return m.group(0)
        new = f"{m.group(1)} {adj[0].upper() + adj[1:]}"
        hits.add("C6", m.group(0), new, line)
        return new
    return C6_RE.sub(rep, text)


def r_c7(text: str, hits: Sink, line: int) -> str:
    """Satzanfang: nach . ! ? sowie am Absatzanfang (nur Prosa)."""
    out = []
    pos = 0
    for m in C7_RE.finditer(text):
        before = text[:m.end(1)]                 # Inkl. Satzzeichen – sonst
        words = before.split()                    # sieht „Z. B.“ aus wie „… Z.“
        last = words[-1] if words else ""
        if last and (ABBR_END.search(last) or re.search(r"[\d]\.$", last)):
            continue
        if re.search(r"\d[.,]$|\d$", before.rstrip()):
            continue
        if word.lower() in {"de", "com", "net", "org", "io", "eu", "app", "info"}:
            continue                                  # TLD-Stueck einer Domain
        word = m.group(3)
        if word[0].isupper() or protect(word) or tc.looks_like_slug(word):
            continue
        if word.lower() in LOWER_BRANDS:
            continue
        new = word[0].upper() + word[1:]
        hits.add("C7", word, new, line)
        out.append(text[pos:m.start(3)])
        out.append(new)
        pos = m.end(3)
    res = "".join(out) + text[pos:] if out else text
    # Absatzanfang: Zeile beginnt klein (nur Prosa, nie nach Weichumbruch)
    m2 = re.match(r"^([a-zäöüß][\wäöüß-]*)", res)
    if m2 and not line_is_continuation:
        w = m2.group(1)
        if not protect(w) and w.lower() not in LOWER_BRANDS and not tc.looks_like_slug(w):
            new = w[0].upper() + w[1:]
            hits.add("C7", w, new, line)
            res = new + res[len(w):]
    return res


line_is_continuation = False


def r_c8(text: str, hits: Sink, line: int) -> str:
    if NO_ANREDE:
        return text
    out = []
    pos = 0
    for m in C8_RE.finditer(text):
        pre = text[:m.start()]
        if pre.rstrip().endswith(("**:", ":", "!", "?", ".")) or not pre.strip():
            continue
        word = m.group(1)
        if protect(word):
            continue
        hits.add("C8", word, word.lower(), line)
        out.append(text[pos:m.start(1)])
        out.append(word.lower())
        pos = m.end(1)
    return "".join(out) + text[pos:] if out else text


# Sonderfaelle, die die Wort-Marke-Regex nicht erfasst: AVM setzt „FRITZ!Box",
# im Blog kursieren „FritzBox", „Fritz box", „FRITZ! Box" (Leerzeichen nach dem !),
# dazu U+2011-Hyphen in kompositen Namen.
BRAND_SPECIALS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bAVM\s+Fritz(?:en)?\s*!?\s*[Bb]ox\b", re.I), "AVM FRITZ!Box"),
    (re.compile(r"\bAVM\s+FRITZ\s*!\s*(Box|Repeater|Powerline|Fon|DECT|OS)\b"),
     r"AVM FRITZ!\1"),
    (re.compile(r"\bFritz(?:en)?\s*!?\s*[Bb]ox\b"), "FRITZ!Box"),
    (re.compile(r"\bFRITZ\s*!\s*(Box|Repeater|Powerline|Fon|DECT|OS|WLAN)\b"), r"FRITZ!\1"),
    (re.compile(r"\bfritz\s*!?\s*(box|repeater|powerline|fon|dect|os|wlan)\b"), r"FRITZ!\1"),
]


def r_specials(text: str, hits: Sink, line: int) -> str:
    for pat, canon in BRAND_SPECIALS:
        def rep(m, canon=canon, pat=pat):
            if protect(m.group(0)):
                return m.group(0)
            val = pat.sub(canon, m.group(0))
            if val == m.group(0):
                return m.group(0)
            hits.add("C9", m.group(0), val, line)
            return val
        text = pat.sub(rep, text)
    return text


def r_c9(text: str, hits: Sink, line: int) -> str:
    def rep(m):
        whole = m.group(1)
        if protect(whole):
            return m.group(0)
        canon = tc.BRANDS.get(tc.norm_brand_key(whole))
        if not canon or canon == whole:
            return m.group(0)
        hits.add("C9", whole, canon, line)
        return canon
    return BRAND_RE.sub(rep, text)


AMBIGUOUS_UNITS = {"kw", "v", "w", "mb"}     # z. B. „KW 42" = Kalenderwoche


def r_c10(text: str, hits: Sink, line: int) -> str:
    def rep(m):
        whole = m.group(1)
        if protect(whole):
            return m.group(0)
        canon = tc.UNITS.get(whole.lower())
        if not canon or canon == whole:
            return m.group(0)
        if whole.lower() in AMBIGUOUS_UNITS:
            if re.match(r"\s*\d", text[m.end(1):]):
                if whole.lower() == "kw":
                    # "KW 42" ist als Einheit unsinnig und als Kalenderwoche
                    # belegt: Zahl HINTER dem Kuerzel = Kalenderwoche. Kilowatt
                    # steht im Deutschen VOR der Zahl ("20 KW" -> "20 kW"),
                    # genau dort biegt der Regelzweig unter diesem Zweig.
                    return m.group(0)
                hits.add("C10-report", whole, "Einheit oder Kalenderwoche?",
                         line, "report")
                return m.group(0)
        hits.add("C10", whole, canon, line)
        return canon
    return C10_RE.sub(rep, text)


# Wortschatz, der NIE eine Abkuerzung ist: solche Caps sind Betonungs-Shouting.
SHOUT_LEXICON = (tc.NOUNS | tc.LOWER | set("""
zusatz risiko gefahr chance fehler hinweis wichtig sicher korrekt falsch
doppelt dreifach mehrfach einzigartig kostenlos guenstig günstig gratis
sofort endlich niemals immer wieder nichts alles nichts selbst nur alle
""".split()))


def _shout_candidate(tok: str, text: str) -> bool:
    """Kapitaelchen-Wort = Shouting? Nur wenn es ein deutsches Wort ist (Lexikon)
    oder im selben Kontext klein belegt ist. Echte Akronyme (TKG, EEX, ZKG,
    DNSSEC, C24 …) sind das nie und bleiben in Ruhe – die Abkuerzung-Falle."""
    low = tok.lower().rstrip(".,:;!?")
    if not low or tok in C11_OK or low in C11_OK or protect(tok):
        return False
    if tc.norm_brand_key(low) in tc.BRANDS:            # C9 regelt die Marke
        return False
    if low in SHOUT_LEXICON or tok in C11_SHOUT_WORDS:
        return True
    if len(tok) >= 6 and re.search(r"(?<![A-Za-z\u00c4\u00d6\u00dc\u00dfA-Za-z\u00e4\u00f6\u00fc])"
                                   + re.escape(low) + r"(?![A-Za-z\u00e4\u00f6\u00fc\u00df])", text):
        return True                                    # klein belegt => Betonung
    return False


def _markup_zeile(text: str) -> bool:
    """HTML/Shortcode/Tabellenzeile: Caps sind dort Technik, keine Betonung."""
    return "<" in text or ">" in text or "{{" in text or text.lstrip().startswith("|")


def r_c11(text: str, hits: Sink, line: int) -> str:
    def comp(m):
        sep, tok = m.group(1), m.group(2)
        if not _shout_candidate(tok, text):
            return m.group(0)
        cap = tok[0].upper() + tok[1:].lower()
        hits.add("C11", tok, cap, line)
        return f"{sep}{cap}"                # das zweite Zeichen ist Lookahead
    text = C11_COMPOUND_RE.sub(comp, text)

    def rep(m):
        tok = m.group(1)
        if not _shout_candidate(tok, text):
            return tok
        if _markup_zeile(text):
            hits.add("C11-report", tok, f"{tok[0].upper() + tok[1:].lower()} "
                     "(Shouting in Markup/Tabelle – von Hand)", line, "report")
            return tok
        hits.add("C11", tok, tok.lower(), line)
        return tok.lower()
    return C11_RE.sub(rep, text)


# Woerter, die formal wie ein Nomen aussehen duerfen, im Titel aber fast immer
# ein echtes Nomen sind -> nie klein biegen.
# Nomen-Endungen: ein Wort darauf ist IMMER ein Nomen (oder Marken-/Fachwort)
# und darf in einer Ueberschrift niemals kleingebogen werden.
# Geschlossene Klasse: Artikel, Pronomen, Konjunktionen, Hilfsverben. Diese
# Woerter sind in einer Ueberschrift NIE ein Nomen – ihr Kontext-Veto entfaellt.
C12_ALWAYS = set("""
der die das dem den des ein eine einem einen einer eines und oder aber doch
weil wenn dass sodass damit als wie so ist sind sein werden wird wurde kann
können muss müssen soll sollen will wollen darf dürfen mag mögen du dich dir
dein deine dein deines dein mir mich mein meine es er sie ihr euch uns man
niemand jemand alles nichts viel wenig mehr immer nie nur schon noch auch
""".split())


C12_STOP = {"links", "rechts", "mauschen", "glatt", "fluss", "kurs"}
C12_NOUN_VETO = ("er", "el", "ung", "ing", "heit", "keit", "schaft", "tum",
                 "ling", "nis", "sal", "at", "ion", "ur", "ent", "ant", "ist",
                 "or", "in", "ik", "ei", "ling")
# Nach Praeposition/Artikel/Pronomen folgt ein Nomen – die Grossschreibung ist
# dann Konjunktionspflicht, kein Title-Case: „Messen statt Raten“, „im Griff“
# bleibt als einziger Treffer klein, das Nomen daneben gross.
C12_PREP = {"in", "im", "am", "an", "auf", "aus", "bei", "beim", "mit", "nach",
            "von", "zu", "zur", "zum", "vor", "über", "unter", "durch", "für",
            "ohne", "gegen", "statt", "trotz", "wegen", "dank", "per", "je",
            "pro", "bis", "um", "ans", "ins", "aufs", "beim", "der", "die",
            "das", "dem", "den", "des", "ein", "eine", "einem", "einen",
            "einer", "kein", "keine", "dein", "deine", "sein", "seine"}


def _c12_lowercase(low: str) -> bool:
    """Darf dieses Wort in einer Ueberschrift kleingeschrieben werden?"""
    if low in tc.NOUNS or low in C12_NOMINAL:
        return False
    # VERBAL_NOUNS („sparen“, „finden“) sind hier bewusst KEIN Pauschal-Veto:
    # ob sie als Nomen („das Sparen“) oder als Verb („Geld sparen“) gemeint
    # sind, entscheidet der Kontext – und den sieht nur r_c12.
    if low in tc.VERBAL_NOUNS and False:
        return False
    if len(low) > 3 and low.endswith(C12_NOUN_VETO):
        return False
    if tc.classify(low)[0] == "lower":
        return True
    # Schmalste Konjugations-Ableitung: 2. Person Singular auf -st (eine echte
    # Nomen-Endung ist das nicht) – „du behältst“ -> Stamm „behal(t)“.
    if len(low) >= 6 and low.endswith("st") \
            and tc._fold(low[:-2]) in tc.VERB_STEMS:
        return True
    return False


HG_BOLD_SPAN = re.compile(r"\*\*\s*([^*\n]+?)\s*\*\*")
HG_CAP = re.compile(r"(?<= )(?=[A-ZÄÖÜ][a-zäöüß])([A-ZÄÖÜ][a-zäöüß]+)")
_ABBR_LOW = {x.lower() for x in ABBR_STEMS}


def _hg_after_abbr(prev_word: str) -> bool:
    """Falscher Satzanschluss nach Abkuerzung, Zahl oder Einzelbuchstabe:
    „7. Den Stichtag…“, „bis 30. November“, „z. B. Wechsel“, „5 % Wärmeverlust“."""
    w = prev_word.strip("()[]{}\"'„“”«»‚› " + "`")
    if not w:
        return True
    core = w.rstrip(".)")
    # Zahlenschema („Phase 3:“, „3. Schritt“, „bis 30.“) und Einzelbuchstaben
    # („z. B.“, „5 %“) sind keine Satzgrenze – sonst meldet die Wache jede
    # Phasen-Ueberschrift als angeklebten Absatz.
    return (len(core) <= 1 or core.lower() in _ABBR_LOW
            or bool(re.fullmatch(r"\d+[.):]?", w)))


def _sentence_glue(line: str) -> bool:
    """Nachweis: die Ueberschriftenzeile traegt einen ganzen Satz im Innern.

    Der Massstab ist die Satzgrenze, nie die Laenge. Ein Grossbuchstabe, hinter
    dem sich ein ganzer Satz bis zum Zeilenende aufbaut (und der nicht nach Artikel,
    Aufzaehlung, Abkuerzung, Klammer oder Rechenzeichen steht), ist ein
    angeklebter Absatz – eine Ueberschrift endet nie mit einem Punkt auf.
    """
    body = re.sub(r"^\s*#{1,6}\s+", "", line)
    for wm in HG_CAP.finditer(body):
        before = body[:wm.start()].rstrip()
        if not before or before.endswith((",", ":", ";", "–", "—", "(", "[",
                                          "+", "/", "&", "*", "|")):
            continue
        if _hg_after_abbr(before.split()[-1]):
            continue
        if protect(wm.group(1)) or wm.group(1).lower() in tc.MONTHDAYS:
            continue
        tail = body[wm.start():].strip().strip("*")
        if len(tail.split()) < 3:
            continue
        if not re.search(r"\.[”»\)]?$", tail):
            continue            # nur der Punkt schliesst einen Absatz ab –
                                # „(Achtung!)“ und „…oder nicht?“ sind Titel-Stil
        if _hg_has_verb(tail):
            return True
    return False


def _glue_signal(line: str) -> bool:
    """True, wenn eine Ueberschriftenzeile nachweislich Absatztext traegt.

    Drei Beweise – die Laenge ist keiner:
      * der Struktur-Modus wuerde trennen (Fettkoerper / Folgesatz / Listenkopf);
      * ein ganzer Satz steht im Innern und schliesst die Zeile mit einem
        Punkt ab (_sentence_glue) – Frage- und Ausrufetitel sind erlaubt;
      * ein Fettkoerper von >= 3 Woertern steht NICHT am Zeilenende.
    """
    if not re.match(r"^\s*#{1,6} ", line):
        return False
    if split_heading_glue(line) is not None:
        return True
    body = re.sub(r"^\s*#{1,6}\s+", "", line)
    # Nur _sentence_glue meldet, NICHT die rohe Satzzeichen-Fuge: „Tarifvergleich:
    # Altvertrag vs. Neukunden-Wechseltarif“, „… für Singles bzw. Familien?“ und
    # acht weitere „X vs. Y“-Ueberschriften waren mit dem nackten Muster
    # Fehlalarme – die Abkuerzungs-, Zahl- und Klammerbremsen wohnen im Zaehler.
    if _sentence_glue(line):
        return True
    for m in HG_BOLD_SPAN.finditer(body):
        if len(m.group(1).split()) >= 3 and body[m.end():].strip():
            return True
    return False


C12_ART = {"der", "die", "das", "dem", "den", "des", "ein", "eine", "einem",
           "einen", "einer", "kein", "keine", "dein", "deine", "sein", "seine"}


C12_NOMINAL = {"zahlen", "nutzen", "sparen", "rechnen", "vergleichen", "teilen",
               "mass", "werte", "teile", "laufen", "fallen", "steigen", "fahren"}


def r_c12(text: str, hits: Sink, line: int, glue=None) -> str:
    """Ueberschrift: englisches Title-Case (KI-Erblastung) -> deutsche Satzschreibung.

    Der Deutsche schreibt in Ueberschriften nur Gross, was Nomen ist oder am
    Satzanfang steht. Die KI uebernimmt dagegen englische Titel-Regeln
    („Der Stichtag Kennen und Nutzen“). Gebogen wird nur, was mit sicherem
    Abstand kein Nomen sein kann. Geschuetzt bleiben:

      * erstes Wort der Ueberschrift und jedes Wort nach fuehrender
        Nummerierung („### 3. So …“, „### Fehler 5: …“),
      * jedes Wort nach Doppelpunkt/Gedankenstrich (dort darf ein neuer
        Satz gross anfangen: „Fazit: Dein Haus …“),
      * jedes Wort nach Praeposition/Artikel/Pronomen (dann ist es ein Nomen:
        „Messen statt Raten“, „für interne Links“),
      * Nomen, nominalisierte Verben mit Nomen im naechsten Feld, Woerter auf
        typische Nomen-Endungen, Akronyme, Marken, Unbekanntes.
    """
    body = re.sub(r"^\s*#{1,6}\s+", "", text)
    prefix = text[:len(text) - len(body)]
    # Titel-Case darf nur an einer ECHTEN Ueberschrift gebogen werden: wird ein
    # Absatz angeklebt (Publishing-Fehler), sind die Grossbuchstaben korrekte
    # Satzanfaenge. C12 tritt zurueck und meldet die Struktur.
    #
    # Fruehere Fassung: Laenge (> 12 Woerter / > 90 Zeichen) oder ein `**`
    # galten als Verdacht. Das war ein Strohmann – FAQ-Fragen und Titel mit
    # Unterstitel sind regelmaessig laenger und voellig in Ordnung, die Wache
    # meldete funf saubere Ueberschriften als Strukturfehler. Gemeldet wird
    # jetzt nur noch, was INNERHALB der Zeile als Satz- oder Fettfuge belegt ist.
    if glue if glue is not None else _glue_signal(text):
        hits.add("C12-guard", body[:60], "Ueberschrift mit angeklebtem Text "
                 "(Struktur prüfen)", line, "report")
        return text

    toks = re.split(r"(\s+)", body)
    words = [w for w in toks if w and not w.isspace()]
    strip = '.,:;!?„“”"\'()[]&–—'
    out: list[str] = []
    seen_word = False
    guard_next = False
    prev_low = ""
    wi = -1

    def armed(tok: str) -> bool:
        """Nach Label-Doppelpunkt, Gedankenstrich oder Nr.-Punkt beginnt ein
        neuer Satz – dessen Grossbuchstabe ist duden-konform, kein Leak."""
        k = tok.rstrip("*_")
        return (k[-1:] in (":", "\u2013", "\u2014", "!", "?")
                or bool(re.fullmatch(r"\d+[.)]", tok.strip())))

    for tok in toks:
        if not tok or tok.isspace():
            out.append(tok)
            continue
        wi += 1
        bare = tok.strip(strip)
        nxt = words[wi + 1].strip(strip) if wi + 1 < len(words) else ""
        nxt_raw = words[wi + 1] if wi + 1 < len(words) else ""
        if nxt_raw.startswith(",") and re.fullmatch(r"[A-Z\u00c4\u00d6\u00dc][a-z\u00e4\u00f6\u00fc]{1,9}", bare):
            out.append(tok)                              # „Max, 28, Entwickler“ = Name
            seen_word = True
            prev_low = bare.lower()
            guard_next = armed(tok)
            continue
        if not bare or not bare[0].isupper():
            out.append(tok)
            seen_word = True
            prev_low = bare.lower()
            guard_next = armed(tok)
            continue
        if not seen_word:
            out.append(tok)
            seen_word = True
            prev_low = bare.lower()
            guard_next = armed(tok)
            continue
        if guard_next:
            out.append(tok)
            prev_low = bare.lower()
            guard_next = armed(tok)
            continue
        if protect(bare):
            out.append(tok)
            prev_low = bare.lower()
            guard_next = armed(tok)
            continue
        if re.fullmatch(r"[^\wÄÖÜäöüß]+", prev_low):
            out.append(tok)                              # „Hausrat + Elementar“
            prev_low = bare.lower()
            guard_next = armed(tok)
            continue
        low = bare.lower()
        nlow = nxt.lower()
        nominal = (low in tc.NOUNS or low in C12_NOMINAL or low in C12_STOP
                   or prev_low in C12_PREP
                   or (len(bare) > 3 and low.endswith(C12_NOUN_VETO))
                   or (low in tc.VERBAL_NOUNS
                       and (nlow in tc.NOUNS
                            or (nlow[:1].isupper() and not _c12_lowercase(nlow)))))
        # „Der Druck sinkt“ in einer Ueberschrift ist ein Artikel + Nomen, kein
        # Title-Case-Leak – und genau deshalb ist der Artikel hier unbiegbar,
        # solange das naechste Wort gross beginnt. Echte Leaks („Stichtag Kennen
        # und nutzen“) haben ein kleines Folgeglied.
        if low in C12_ART and nxt[:1].isupper():
            nominal = True
        if low in C12_ALWAYS:
            nominal = False
        if not nominal and _c12_lowercase(low):
            hits.add("C12", bare, low, line)
            out.append(tok.replace(bare, low))
        else:
            out.append(tok)
        prev_low = low
        seen_word = True
        guard_next = armed(tok)
    return prefix + "".join(out)


def r_c13(text: str, hits: Sink, line: int) -> str:
    def rep(m):
        w = m.group(1)
        if protect(w):
            return m.group(0)
        new = w[0].upper() + w[1:]
        hits.add("C13", w, new, line)
        return new
    return C13_RE.sub(rep, text)


def r_c14(text: str, hits: Sink, line: int) -> str:
    """Binnenmajuskel: im Deutschen werden Komposita zusammengeschrieben
    („StromFresser“ -> „Stromfresser“). GROSSBUCHSTABEN IN DER MITTE sind fast
    immer entweder (a) echte Marken (NetCologne, FranksFinanzcheck, PayPal) oder
    (b) deutsche Komposita mit KI-CamelCase. Unterschieden wird deterministisch:
    Nur wenn ALLE Wortteile im Lexikon liegen und kein Marken-Treffer vorliegt,
    gilt es als Kompositum-Fehler – gemeldet, nie verbogen (Struktur-Eingriff)."""
    def rep(m):
        w = m.group(1)
        if protect(w) or tc.norm_brand_key(w) in tc.BRANDS:
            return m.group(0)
        if w in C14_OK or norm_brand_key_ci(w) :
            return m.group(0)
        parts = re.findall(r"[A-Z\u00c4\u00d6\u00dc]?[a-z\u00e4\u00f6\u00fc\u00df]+", w)
        low = {x.lower() for x in parts}
        if len(parts) >= 2 and all(len(x) >= 3 for x in parts) \
                and all(x in tc.NOUNS or x in tc.LOWER or x in tc.VERBAL_NOUNS or x in C14_OK
                        for x in low):
            hits.add("C14-report", w, "".join(
                [parts[0][0].upper() + parts[0][1:]] + [x.lower() for x in parts[1:]]
            ) + " (Kompositum?)", line, "report")
        return m.group(0)
    return C14_RE.sub(rep, text)


def r_c15(text: str, hits: Sink, line: int) -> str:
    """Nomen nach Präposition/Possessiv kleingeschrieben -> gross.

    Sicherheitsstufen (warum das hier deterministisch ist):
      1. Nur Wörter aus dem kuratierten tag_casing.NOUNS-Kanon (kein Suffix-Rat).
      2. Kein Fix, wenn direkt danach @ . _ / folgt (E-Mail, Domain, Dateiname).
      3. Kein Fix, wenn ein Zahl-/Code-Argument folgt (z. B. „mit ping 1.1.1.1").
      4. Kein Fix, wenn ein grosses Wort folgt (Adjektiv vor Nomen: „von zusätzlichen
         Angeboten" – das Adjektiv bleibt klein)."""
    def rep(m):
        ctx, word = m.group(1), m.group(2)
        if word in C15_STOP or protect(word):
            return m.group(0)
        if word not in tc.NOUNS:
            return m.group(0)
        # E-Mail-/Domain-/Datei-Kontext erkennen (Punkt AM SATZENDE ist kein
        # Dateipunkt – deshalb muss nach dem Trenner ein Zeichen stehen)
        if re.match(r"[@_./\-][A-Za-z0-9]", text[m.end(2):]):
            return m.group(0)
        tail = text[m.end(2):]
        if re.match(r"\s+[A-ZÄÖÜ][a-zäöüß]{2,}", tail):      # Adjektiv vor Nomen
            return m.group(0)
        if re.match(r"\s+[\d`]", tail):                        # Code-/Zahlenargument
            return m.group(0)
        new = f"{ctx} {word[0].upper() + word[1:]}"
        hits.add("C15", m.group(0), new, line)
        return new
    return C15_RE.sub(rep, text)


# ---------------------------------------------------------------------------
# Regel-Plan pro Zone
# ---------------------------------------------------------------------------
def r_c17(text: str, hits: Sink, line: int) -> str:
    """Leerraum-Komposita in Titel und Ueberschrift: „Frugalismus Tipps“,
    „Heizung wartung“. Im Deutschen gehoert das in ein Wort oder an einen
    Bindestrich – und in Titelzeilen ist die Leerzeichenform zusaetzlich der
    Grund, dass Google die Phrase als zwei Begriffe liest. Gebogen wird nur nach
    Komposita-Kanon (tag_casing.COMPOUND_JOIN); Verbwendungen wie
    „Strom sparen im Haushalt“ sind korrekt und bleiben stehen."""
    out, geaendert = tc.join_compounds(text)
    if not geaendert:
        return text
    for alt, kanon in tc.COMPOUND_JOIN.items():
        n = len(re.findall(alt, text, re.I))
        for _ in range(n):
            hits.add("C17", alt, kanon, line)
    return out


def r_c16(text: str, hits: Sink, line: int) -> str:
    """Ueberschrift: **Fettdruck** ist in einer Ueberschrift die Betonung des
    bereits Fetten. Er wird optisch nicht getragen, taucht aber in TOC, Snippet
    und Social-Card-Auszuegen als Ballast mit. Rueckstandslos entfernt, wenn die
    Zeile KEINE Klebefuge traegt (sonst braucht der Struktur-Modus die Spur)."""
    def rep(m):
        hits.add("C16", m.group(0), m.group(1), line)
        return m.group(1)
    return re.sub(r"\*\*\s*([^*\n]+?)\s*\*\*", rep, text)


PIPELINE = [
    ("C9", r_c9), ("C1", r_c1), ("C2", r_c2), ("C3", r_c3), ("C4", r_c4),
    ("C5", r_c5), ("C6", r_c6), ("C10", r_c10), ("C11", r_c11),
    ("C13", r_c13), ("C15", r_c15), ("C8", r_c8), ("C7", r_c7),
    ("C14", r_c14), ("C17", r_c17),
]


def apply_rules(text: str, allowed, hits: Sink, line: int = 0,
                heading: bool = False, continuation: bool = False) -> str:
    global line_is_continuation
    if not text.strip():
        return text
    # Klebefuge EINMAL am unmaskierten Originaltext pruefen: C12 (Zuruecktreten)
    # und C16 (Fettdruck entfernen) muessen sich auf dieselbe Antwort stuetzen,
    # sonst hebt eine Wache auf, was die andere gerade gemeldet hat.
    glue = _glue_signal(text) if heading else False
    if "C9" in allowed:
        text = r_specials(text, hits, line)      # vor der Maskierung (siehe oben)
    masked, store = mask(text)
    line_is_continuation = continuation
    for code, fn in PIPELINE:
        if code in allowed:
            masked = fn(masked, hits, line)
    if heading and "C12" in allowed:
        masked = r_c12(masked, hits, line, glue=glue)
    if heading and "C16" in allowed and not glue:
        masked = r_c16(masked, hits, line)
    line_is_continuation = False
    return unmask(masked, store)


# ---------------------------------------------------------------------------
# Markdown-Datei
# ---------------------------------------------------------------------------
def split_frontmatter(lines):
    if not lines or lines[0].strip() != "---":
        return -1, -1
    for i in range(1, len(lines)):
        if lines[i].startswith("---"):
            return 0, i
    return 0, len(lines)


def inline_list(value: str):
    """YAML-Fliesstextliste `"a", "b"` -> [„a", „b"].

    Kein Regex-Trick: Zeichenzaehler mit Quote-Zustand und Backslash-Escape,
    damit `\"` im Term nicht den Rest der Zeile zerlegt (alter Parser-Fehler:
    Tags wurden zu Fragmenten mit haengenden Anfihrungszeichen)."""
    v = value.strip()
    if not (v.startswith("[") and v.endswith("]")):
        return None
    inner = v[1:-1]
    items: list[str] = []
    buf: list[str] = []
    quote = ""
    i = 0
    while i < len(inner):
        ch = inner[i]
        if quote:
            if ch == "\\" and i + 1 < len(inner) and inner[i + 1] == quote:
                buf.append(quote)
                i += 2
                continue
            if ch == quote:
                quote = ""
            else:
                buf.append(ch)
            i += 1
            continue
        if ch in "\"'":
            quote = ch
            i += 1
            continue
        if ch == ",":
            items.append("".join(buf).strip())
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    if "".join(buf).strip():
        items.append("".join(buf).strip())
    return items


def render_list(items) -> str:
    return "[" + ", ".join('"' + str(t).replace('"', '\\"') + '"' for t in items) + "]"


def fix_prose_line(raw: str, allowed, hits: Sink, lineno: int, prev_raw: str) -> str:
    s = raw.strip()
    if not s:
        return raw
    if s.startswith("|"):                     # Tabellenzeile: Zellen einzeln
        cells = raw.split("|")
        fixed = [fix_prose_line(c, allowed, hits, lineno, prev_raw) for c in cells]
        return "|".join(fixed)
    marker = ""
    body = raw
    m = LIST_MARKER.match(raw)
    if m:
        marker, body = m.group(1), m.group(2)
    heading = bool(HEAD_MARK.match(body))
    # C17 gilt nur fuer Titelzeilen: im Fliesstext kann „beim DSL Vergleich mit
    # dem Testbericht“ eine Aufzaehrung zweier Begriffe sein – dort wird nicht
    # gebogen. Ueberschriften und FM-Titel sind Term-Form, da ist sie ein Fehler.
    allowed = allowed if heading else (allowed - {"C17"})
    continuation = bool(prev_raw.rstrip()) and not prev_raw.strip().endswith(
        (".", "!", "?", ":", "”", '"', ")", "*", "|")) and not heading
    out = apply_rules(body, allowed, hits, lineno, heading=heading,
                      continuation=continuation)
    return marker + out


def process_file(path: Path):
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    fm_open, fm_close = split_frontmatter(lines)
    hits = Sink()
    out = []
    in_code = False
    in_shortcode = False
    current_key = None
    for i, raw in enumerate(lines):
        s = raw.strip()
        if s.startswith("```"):
            in_code = not in_code
            out.append(raw)
            continue
        if in_shortcode:                       # innerhalb eines {{< … >}}-Zauns
            out.append(raw)
            if ">}}" in raw or (">" in raw and "{{<" not in raw and "=" in raw):
                in_shortcode = False
            continue
        if "{{<" in raw and ">}}" not in raw and not re.search(r"\{\{<[^>]*>\}\}", raw):
            in_shortcode = True
            out.append(raw)
            continue
        if in_code:
            out.append(raw)
            continue
        in_fm = fm_open == 0 and fm_close > 0 and 0 < i < fm_close
        if in_fm:
            m = re.match(r"^([A-Za-z_][\w-]*):(.*)$", raw)
            if m:
                current_key = m.group(1)
            else:
                m2 = re.match(r"^\s+([A-Za-z_][\w-]*):(.*)$", raw)
                if m2:
                    current_key = m2.group(1)
            key = current_key
            if key in FM_BRAND_ONLY:
                # keywords: ist SEO-Feld, aber redaktionell heilig (Reihenfolge,
                # Wortlaut). Einzige Ausnahme: der Marken-Kanon – „FritzBox" im
                # Keyword ist ein Schreibfehler, der weitestgehend unsichtbar
                # bleibt. C8/C7/C11 etc. treten hier bewusst zurueck.
                new = apply_rules(raw, {"C9"}, hits, i + 1, continuation=True)
                if new != raw:
                    for h in list(hits)[-1:]:
                        h["zone"] = "fm:keywords"
                    out.append(new)
                    continue
                out.append(raw)
                continue
            if key is None or key in FM_PROTECT:
                out.append(raw)
                continue
            if key in FM_TAGS and m and inline_list(m.group(2)) is not None:
                alt = inline_list(m.group(2)) or []
                neu, changed, _ = tc.normalize_terms(alt)
                if changed and neu:
                    rendered = render_list(neu)
                    for old, new in zip(alt, neu):
                        hits.add("T1", old, new, i + 1, f"fm:{key}")
                    if len(neu) != len(alt):
                        hits.add("T1", f"{len(alt)} Terme",
                                 f"{len(neu)} Terme (Duplikat verschmolzen)",
                                 i + 1, f"fm:{key}")
                    out.append(f"{m.group(1)}: {rendered}")
                    continue
                out.append(raw)
                continue
            if m:
                sep = m.group(2)[:len(m.group(2)) - len(m.group(2).lstrip())] or " "
                val = m.group(2).strip()
                allowed = SEO_RULES if key in FM_SEO else (
                    PIN_RULES if key in FM_PIN else set())
                if not allowed or not val:
                    out.append(raw)
                    continue
                quote = val[0] if val[:1] in ("\"", "'") else ""
                core = val[1:-1] if quote and len(val) >= 2 else val
                new_core = apply_rules(core, allowed, hits, i + 1, continuation=True)
                if new_core != core:
                    out.append(f"{m.group(1)}:{sep}{quote}{new_core}{quote}")
                    continue
                out.append(raw)
                continue
            out.append(raw)
            continue
        prev = lines[i - 1] if i else ""
        out.append(fix_prose_line(raw, BODY_RULES, hits, i + 1, prev))
    return list(hits), "\n".join(out)


# ---------------------------------------------------------------------------
# Pinterest-Masterplan (Quelldatei der Pin-Texte – dort sitzt der Kanon)
# ---------------------------------------------------------------------------
PLAN_FIELDS = {"titel": PIN_RULES, "beschreibung": PIN_RULES, "pinwand": TYPO_RULES,
               "keywords": {"C9"}}


def process_plan(text: str):
    hits = Sink()
    out = []
    for i, raw in enumerate(text.split("\n")):
        m = re.match(r"^(\s*)(titel|beschreibung|pinwand|keywords):\s*(.*)$", raw)
        if not m:
            out.append(raw)
            continue
        indent, key, val = m.group(1), m.group(2), m.group(3).strip()
        quote = "'" if val.startswith("'") else ""
        inner = val.strip("'")
        before = len(hits)
        new = apply_rules(inner, PLAN_FIELDS[key], hits, i + 1, continuation=True)
        for h in list(hits)[before:]:
            h["zone"] = f"plan:{key}"
        out.append(f"{indent}{key}: {quote}{new}{quote}" if new != inner else raw)
    return list(hits), "\n".join(out)


# ---------------------------------------------------------------------------
# Zielmenge
# ---------------------------------------------------------------------------
def changed_since_head2():
    import subprocess
    try:
        out = subprocess.run(["git", "diff", "--name-only", "HEAD~2", "HEAD", "--", "content/"],
                             capture_output=True, text=True, cwd=ROOT, timeout=60).stdout
    except Exception:  # noqa: BLE001
        return set()
    return {ROOT / l.strip() for l in out.splitlines() if l.strip()}


def target_files():
    files = []
    for d in ("posts", "pillar", "ueber", "datenschutz", "impressum"):
        dd = ROOT / "content" / d
        if dd.is_dir():
            files += sorted(dd.rglob("*.md"))
    if files and NEW_ONLY:
        changed = changed_since_head2()
        today = date.today().isoformat()
        changed |= {f for f in files if today in str(f)}
        files = [f for f in files if f in changed]
    return files


def words_of(path: Path) -> int:
    try:
        txt = path.read_text(encoding="utf-8")
    except OSError:
        return 0
    body = txt.split("---", 2)[-1]
    return len(re.findall(r"[A-Za-zÀ-ÿ]{2,}", body))


# ---------------------------------------------------------------------------
# Report / Historie / JSON / Gate
# ---------------------------------------------------------------------------
def write_report(rows, mode, scanned):
    total = sum(len(r["funde"]) for r in rows)
    hart = sum(1 for r in rows for f in r["funde"] if f["regel"] in HARD_RULES)
    gefixt = sum(r.get("gefixt", 0) for r in rows)
    worte = sum(r["woerter"] for r in rows) or 1
    L = ["# 🔠 CASING-REPORT (Groß-/Kleinschreibung)", "",
         f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · Modus: {mode}", "",
         f"Geprüfte Dateien: {scanned} · Dateien mit Befund: {len(rows)} · "
         f"Befunde: {total} · hart (gate-würdig): {hart} · automatisch geheilt: {gefixt}",
         "",
         f"**Casing-Deliktquote:** {1000 * hart / worte:.2f} harte Befunde je 1.000 Wörter "
         "– Zielwert 0,00 (Redaktions-Standard Capital/WiWo/ZEIT).", ""]
    pro = {}
    for r in rows:
        for f in r["funde"]:
            pro[f["regel"]] = pro.get(f["regel"], 0) + 1
    if pro:
        L += ["| Regel | Bedeutung | Befunde |", "|---|---|---|"]
        for k in sorted(pro):
            basis = re.sub(r"-(report|guard)$", "", k)
            titel = RULE_TITLES.get(basis, basis)
            if k != basis:
                titel += " – **nur melden**, entscheidet die Redaktion"
            L.append(f"| {k} | {titel} | {pro[k]} |")
        L.append("")
    guard = sum(v for k, v in pro.items() if k.startswith("C12-guard"))
    if guard:
        L += ["## ⚠ Struktur-Hinweis (außerhalb des Casing-Kanons)", "",
              f"{guard} Überschriftenzeile(n) tragen Absatztext direkt hinter dem "
              "Titel – Hugo baut daraus eine **fette Überschrift über dem ganzen "
              "Absatz** (sichtbar auf der Live-Seite). Die Wache biegt dort "
              "bewusst nichts: die Großbuchstaben danach sind korrekte "
              "Satzanfänge, der Fehler ist die fehlende Absätzebene. Trennen: "
              "Zeile nach dem Titel mit `\n\n` aufbrechen (oder "
              "`python3 scripts/casing_guard.py --split-headglue` heilt die eindeutigen Faelle (Fettkoerper / Folgesatz), mehrdeutige bleiben hier stehen).", ""]
    if rows:
        L += ["## Befunde je Datei", ""]
        for r in rows[:45]:
            L.append(f"### `{r['pfad']}` – {len(r['funde'])} Befund(e)")
            L.append("")
            L.append("| Regel | Zeile | Zone | vorher → nachher |")
            L.append("|---|---|---|---|")
            for f in r["funde"][:30]:
                vor = str(f["vorher"]).replace("|", "\\|")[:58]
                nach = str(f["nachher"]).replace("|", "\\|")[:58]
                L.append(f"| {f['regel']} | {f['zeile']} | {f['zone']} | "
                         f"`{vor}` → `{nach}` |")
            if len(r["funde"]) > 30:
                L.append(f"| … | | | {len(r['funde']) - 30} weitere |")
            L.append("")
    else:
        L.append("🎉 Groß-/Kleinschreibung sauber (C1–C15 + T1: Duden, Marken- und "
                 "Hauskanon, Front-Matter-Zonen berücksichtigt).")
    trend = read_trend()
    if trend:
        L += ["", trend]
    L += ["", "---",
          "_Zonen: `keywords`/Slugs/URLs/Code = unantastbar · `title`/`description` = nur "
          "Tippfehler · `tags`/`categories` = Tag-Kanon + Term-Dedupe · Pin-Felder = volle "
          "Regeln · Body = alles._  ",
          "_Lexikon-Pflege: `scripts/tag_casing.py` (NOUNS/LOWER/BRANDS/ACRONYMS/"
          "FIXED_PHRASES) · geschützte Wörter: `data/casing_whitelist.txt`._"]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")


def read_trend():
    if not HISTORY.exists():
        return ""
    rows = []
    for line in HISTORY.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if len(rows) < 2:
        return ""
    prev, last = rows[-2], rows[-1]
    d = last.get("hart", 0) - prev.get("hart", 0)
    arrow = "↔️ stabil" if d == 0 else ("✅ besser" if d < 0 else "⚠️ gestiegen")
    return (f"**Trend:** {prev.get('hart', 0)} → {last.get('hart', 0)} harte Befunde "
            f"({d:+d}) {arrow} · Historie: `data/casing_history.jsonl`")


def log_history(rows, geparkt):
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "tag": date.today().isoformat(),
            "zeit": f"{datetime.now(timezone.utc):%H:%M}",
            "modus": ("gate" if DO_GATE else "fix" if DO_FIX else "dry-run" if DRY_RUN else "report"),
            "dateien": len(rows),
            "befunde": sum(len(r["funde"]) for r in rows),
            "hart": sum(1 for r in rows for f in r["funde"] if f["regel"] in HARD_RULES),
            "gefixt": sum(r.get("gefixt", 0) for r in rows),
            "geparkt": len(geparkt),
        }, ensure_ascii=False) + "\n")


def gate_new(rows):
    geparkt = []
    hard = [r for r in rows if any(f["regel"] in HARD_RULES for f in r["funde"]
                                   if not f["regel"].endswith("-report"))]
    if len(hard) > 3:
        print("🛑 CASING-CIRCUIT-BREAKER: >3 neue Artikel mit harten Restfunden – "
              "die Wache gilt als fehlerhaft, NICHTS wird geparkt.")
        return []
    try:
        import park_state
    except Exception as exc:  # noqa: BLE001
        print(f"⚠ park_state nicht nutzbar ({exc}) – Gate ohne Wirkung.")
        return []
    for r in hard:
        grund = "Casing: " + ", ".join(sorted({f["regel"] for f in r["funde"]
                                               if f["regel"] in HARD_RULES}))
        try:
            if not DRY_RUN:
                park_state.hold(ROOT / r["pfad"], grund)
            geparkt.append(f"{r['pfad']} ({grund})")
        except Exception as exc:  # noqa: BLE001
            print(f"  ⚠ parken fehlgeschlagen ({r['pfad']}): {exc}")
    return geparkt


# ---------------------------------------------------------------------------
# Struktur-Heilung: Absatztext, der direkt an eine Ueberschrift geklebt ist
# ---------------------------------------------------------------------------
# Zwei eindeutig bestimmbare Trennstellen (alles andere braucht die Redaktion):
#   1. der erste Fettkoerper  („### Titel **Was passiert?** …“)
#   2. der erste Folgesatz nach ? oder ! („### Frage? Antwort …“)
# Hugo baute aus solchen Zeilen eine fette Ueberschrift UEBER DEM GANZEN
# Absatz – ein sichtbarer Layout-Fehler, der aus der Casing-Pruefung
# herausfällt (die Grossbuchstaben danach sind korrekte Satzanfaenge).
HG_ENDHANG = {"der", "die", "das", "den", "dem", "des", "ein", "eine", "einem",
              "einen", "einer", "kein", "keine", "dein", "deine", "sein", "seine",
              "ihr", "ihre", "unser", "euer", "dieser", "diese", "dieses", "jener",
              "jene", "manche", "welche", "welcher", "und", "oder", "sowie", "bzw",
              "als", "wie", "aber", "doch", "denn", "sondern", "respektive",
              "entweder", "weder", "sowohl", "vs"}


HG_BOLD = re.compile(r"\s(?=\*\*)")
HG_SENT = re.compile(r"([?!])\s+(?=[A-ZÄÖÜ][a-zäöüß])")
# Listen-Stil-Ueberschriften: genau hier klebt der Publishing-Pfad gern den
# Folgeabsatz an („### Fehler 3: … Gekippte Fenster kühlen …“). Nur fuer diese
# Form existiert Regel (c) – lange, freie Ueberschriften bleiben unangetastet.
HG_LIST = re.compile(r"^\s*#{1,6}\s+(?:(?:Fehler|Schritt|Trick|Methode|Tipp|"
                     r"Bonus|Punkt|Kapitel|Phase|Regel|Stufe|Tag|Woche)\s*\d+\s*[.:]|"
                     r"\d+[.)])\s")
HG_STARTER = {                      # Satzanfang-Woerter (geschlossene Klasse)
    "der", "die", "das", "den", "dem", "des", "ein", "eine", "einem", "einen",
    "einer", "viele", "fast", "bevor", "auch", "und", "aber", "deshalb",
    "ausserdem", "außerdem", "allerdings", "zwar", "so", "wie", "was", "wer",
    "wenn", "weil", "obwohl", "damit", "in", "im", "am", "an", "auf", "bei",
    "nach", "vor", "seit", "durch", "gegen", "ohne", "dann", "dort", "hier",
    "beides", "beide", "regionales", "wechselst", "pruefe", "prüfe", "setze",
    "nimm", "nutze", "rechne", "lass", "lasse", "achte", "plane", "hole",
    "teile", "laedt", "lädt", "vergleiche", "notiere", "monat", "jahr",
}
HG_TAIL_VERB = re.compile(          # finites Verb in den ersten 6 Woertern
    r"^(?:[^\s]+[\s,]+){0,5}?(?:\w*(?:en|st|et|t|e|rn)\b)(?=[\s,])")


def _hg_words(text: str) -> int:
    return len(re.sub(r"^\s*#{1,6}\s+", "", text).split())


def _hg_has_verb(tail: str) -> bool:
    """Endet der Schwanz nicht wie ein Titel, sondern wie ein Satz? Beleg: ein
    kleines, Verb-ähnliches Wort in den ersten sechs Positionen („Die
    Grundversorgung liegt …“, „Viele zahlen …“)."""
    for w in re.findall(r"[A-Za-zÄÖÜäöüß][\wäöüß]*", tail.replace("**", ""))[:6]:
        lw = w.lower()
        if len(lw) < 4 or not lw[0].islower() or lw in tc.NOUNS:
            continue
        if lw.endswith(C12_NOUN_VETO):
            continue
        if re.search(r"(en|er|st|t|e|rn|te|et)$", lw):
            return True
    return False


def _hg_ok(head: str, tail: str) -> bool:
    if not head or not tail:
        return False
    if not (3 <= _hg_words(head) <= 12):
        return False
    if len(tail.replace("**", " ").split()) < 3:
        return False
    if re.match(r"^\s*#{1,6}\s", tail) or "{{<" in tail or tail.startswith("|"):
        return False
    if tail.lstrip().startswith("**") and "**" not in tail[2:]:
        return False        # einsamer Fettrumpf = eher Titel als Absatz
    # Der Kopf muss einen Titel BESCHLIESSEN. Einhangendes Artikel-/Pronomen-/
    # Konjunktionsende ist Grammatik-Rest: „### Welche Rolle spielt die |
    # **Elementarschadenversicherung** bei einer PV-Anlage?“ – hier trennte die
    # erste Fassung mitten in einer Frage und zerlegte sie. Trennwort-Präfixe
    # separabler Verben („… am besten auf?“, „… kommt es … an?“) sind erlaubt,
    # deshalb NUR die geschlossene Klasse der Begleiter als Sperre.
    last = head.rstrip().split()[-1] if head.rstrip().split() else ""
    if last.strip(".,:;!?„“”\"'()[]&–—").lower() in HG_ENDHANG:
        return False
    return True


def split_heading_glue(line: str):
    """(zeilen, grund) wenn angeklebter Absatztext eindeutig abtrennbar ist.

    Drei Trennstellen, frueheste gueltige Fuge. BEWUSST keine vierte: ein
    Satz, der mit einem Nomen beginnt („… verdeckte Konvektoren Staub,
    Vorhaenge und Moebel blockieren …“), laesst sich mit dem Wortschatz
    dieser Wache nicht gegen einen Titel abgrenzen, der an dieser Stelle noch
    laeuft – die Naht liegt im Zahlungsgefuege, nicht am Grossbuchstaben.
    Wer raten wuerde, trennte an der falschen Stelle und zerlegte thereby
    Ueberschriften. Solche Zeilen meldet _sentence_glue der Redaktion.
      (a) erster Fettkoerper         „### Fehler 1: … ignorieren **Was passiert?** …“
      (b) erster Folgesatz nach ?/!  „### Wie viel spart 1 Grad? Ein Grad …“
      (c) Listen-Kopf + Satzanfang   „### 3. Buendeln und kuendigen Viele zahlen …“
             Nur bei Listen-Ueberschriften (HG_LIST), nur wenn der Schwanz ein
             finites Verb in den ersten 6 Woertern UND ein Satzzeichen enthaelt –
             und das Wort davor klein oder ein Satzanfangswort ist.
    """
    if not re.match(r"^\s*#{1,6} ", line) or "|" in line:
        return None
    s = line.rstrip("\n")
    early: list[tuple[int, str]] = []
    m = HG_BOLD.search(s)
    if m:
        early.append((m.start(), "Fettkörper"))
    m = HG_SENT.search(s)
    if m:
        early.append((m.end(1), "Folgesatz"))
    if HG_LIST.match(s):
        for wm in HG_CAP.finditer(s):
            word = wm.group(1)
            before = s[:wm.start()].rstrip()
            if not before:
                continue
            if before.endswith((",", ":", "–", "—", ";", "(", "[", "+", "/", "&")):
                continue                       # Titel-interne Aufzaehlung
            if word.lower() in tc.MONTHDAYS or protect(word):
                continue
            tail = s[wm.start():].strip()
            if word.lower() in HG_STARTER and _hg_has_verb(tail) \
                    and (". " in tail[:140] or tail.endswith(".")):
                early.append((wm.start(), "Listenkopf"))
                continue
    for pos, grund in sorted(set(early)):
            head = s[:pos].rstrip()
            tail = s[pos:].strip()
            if not _hg_ok(head, tail):
                continue
            return [head, "", tail], grund
    return None


def headglue_pass(files):
    """Einmaliger Struktur-Durchlauf (bewusst separat vom Casing-Fix)."""
    gefixt = []
    for pth in files:
        text = pth.read_text(encoding="utf-8")
        lines = text.split("\n")
        fm_open, fm_close = split_frontmatter(lines)
        out, in_code = [], False
        touched = 0
        for i, raw in enumerate(lines):
            if raw.strip().startswith("```"):
                in_code = not in_code
                out.append(raw)
                continue
            if in_code or (fm_open == 0 and fm_close > 0 and 0 <= i <= fm_close):
                out.append(raw)
                continue
            got = split_heading_glue(raw)
            if got:
                out.extend(got[0])
                touched += 1
                gefixt.append(f"{pth.relative_to(ROOT)}: {got[1]} getrennt")
            else:
                out.append(raw)
        if touched and not DRY_RUN:
            pth.write_text("\n".join(out), encoding="utf-8")
    return gefixt


# ---------------------------------------------------------------------------
# Selbsttest (echte Faelle aus diesem Blog, inkl. Negativ-Fallen)
# ---------------------------------------------------------------------------
# (quelle, erwartet, erlaubte Regeln, Fortsetzung der Zeile?, Ueberschrift?)
FIX_CASES = [
    ("Ein dsl Wechselbonus ist weg.", "Ein DSL-Wechselbonus ist weg.", BODY_RULES, True, False),
    ("Der WLAN Empfang ist schlecht.", "Der WLAN-Empfang ist schlecht.", BODY_RULES, True, False),
    ("zum sparen von 300 €", "zum Sparen von 300 €", BODY_RULES, True, False),
    ("in der regel lohnt das", "in der Regel lohnt das", BODY_RULES, True, False),
    ("etwas neues dazu", "etwas Neues dazu", BODY_RULES, True, False),
    ("deine heizkosten im august.", "Deine Heizkosten im August.", BODY_RULES, False, False),
    ("und du zahlst mehr.", "Und du zahlst mehr.", BODY_RULES, False, False),
    ("Die FritzBox startet neu.", "Die FRITZ!Box startet neu.", BODY_RULES, True, False),
    ("Portale wie check24 zahlen Boni.", "Portale wie CHECK24 zahlen Boni.", BODY_RULES, True, False),
    ("Der Preis pro KWH steigt.", "Der Preis pro kWh steigt.", BODY_RULES, True, False),
    ("Zahlungs-ZUSATZ-Risiko prüfen.", "Zahlungs-Zusatz-Risiko prüfen.", BODY_RULES, True, False),
    ("## 7. Den Stichtag Kennen und nutzen", "## 7. Den Stichtag kennen und nutzen", BODY_RULES, True, True),
    ("und evtl. sinkt dein bonus.", "Und evtl. sinkt dein Bonus.", BODY_RULES, False, False),
    # SEO-Zone: nur Tippfehler, kein Umbauen
    ("DSL Vergleich: So sparst du 360 €", "DSL Vergleich: So sparst du 360 €", SEO_RULES, True, False),
    ("Fritzbox Rabatt für Neukunden", "FRITZ!Box Rabatt für Neukunden", SEO_RULES, True, False),
]
KEEP_CASES = [
    ("title: DSL Vergleich: So findest du den günstigsten Internettarif", TYPO_RULES),
    ("keywords: [\"dsl vergleich\", \"günstigeres internet\"]", set()),
    ("Details: [CHECK24](https://www.check24.de/dsl) und `fritz.box` im Netz.", BODY_RULES),
    ("https://franksfinanzcheck.de/posts/2026-08-19-dsl-vergleich-so-findest-du-guenstigeres-internet/", BODY_RULES),
    ("Mehr unter /go/dsl/ und per #5g bei @franksfinanzcheck.", BODY_RULES),
    ("Der Tarif kostet 44,95 €. Z. B. monatlich. Die Rechnung folgt.", BODY_RULES),
    ("Foto am 1. jeden Monats, drei Zahlen notieren.", BODY_RULES),
    ("Die Kündigung muss bis 30.11. raus. Bei manchen gilt das nicht.", BODY_RULES),
    ("Wichtig: du zahlst nur 12 €.", BODY_RULES),
    ("**Eröffnung:** Du eröffnest dein neues Konto online.", BODY_RULES),
    ("Immer schön: Du bekommst 100 € zurück.", BODY_RULES),
]


HG_CASES = [
    ("### Fehler 2: Verstaubte Heizkörper **Was passiert?** Staub blockiert die Wärme.",
     ["### Fehler 2: Verstaubte Heizkörper", "", "**Was passiert?** Staub blockiert die Wärme."], True),
    ("### Wann sollte ich entlüften? Am besten vor der Heizperiode, das spart Geld.",
     ["### Wann sollte ich entlüften?", "", "Am besten vor der Heizperiode, das spart Geld."], True),
    ("### Fehler 1: Heizkörper nicht entlüften und Druck prüfen Der Druck sinkt",
     None, False),
    ("## Fazit: Mit Preisgarantie sicher und günstig durch den Winter",
     None, False),
    ("### Fehler 5: Im teuren Grundversorgungstarif verharren Die Grundversorgung liegt häufig bei 12 Cent.",
     ["### Fehler 5: Im teuren Grundversorgungstarif verharren", "",
      "Die Grundversorgung liegt häufig bei 12 Cent."], True),
    ("### 3. Sachversicherungen bündeln und Altverträge kündigen Viele zahlen für alte Verträge. Das ist vermeidbar.",
     ["### 3. Sachversicherungen bündeln und Altverträge kündigen", "",
      "Viele zahlen für alte Verträge. Das ist vermeidbar."], True),
    ("## Tarifwechsel bei Strom und Gas: Der schnellste Weg zu mehreren hundert Euro Ersparnis",
     None, False),
    ("## Die Psychologie des Wartens: Warum du nicht bis zum letzten Tag warten solltest",
     None, False),
    # Nomen-Anfang im Schwanz: NICHT automatisch trennbar (die Naht liegt im
    # Zahlungsgefuege, ein Rat wuerde Ueberschriften zerlegen). GLAUBWUERDIG
    # gemeldet wird sie ueber GLUE_REPORT – und von dort von der Redaktion.
    ("### Fehler 2: Verstaubte Heizkörper & verdeckte Konvektoren Staub, Vorhänge "
     "und Möbel blockieren die Wärmeabgabe. Das Thermostat reagiert zu spät.",
     None, False),
    ("### Fehler 4: Veraltete, manuelle Thermostate im Dauereinsatz Alte Drehventile "
     "reagieren träge, heizen weiter, und ignorieren Sonnenwärme.",
     None, False),
    # duennere Schwanz-Verdachtsfaelle bleiben bewusst unangetastet
    ("### Fehler 3: Lüften mit System. Aber richtig", None, False),
    ("### 5. Mein Tipp: Endlich sparen. Jeder kann das", None, False),
    # Fettkoerper am Zeilenende ist KEINE Klebefuge, nur Ballast
    ("## Die 5 teuersten Spätsommer‑Fehler beim **Gasrechnung senken**", None, False),
    # Faellt die Trennung an den Kopf zurueck, zerlegt sie eine Frage – Sperre
    ("### Welche Rolle spielt die **Elementarschadenversicherung** bei einer "
     "Photovoltaik‑Anlage?", None, False),
    ("## Wie fange ich am einfachsten an?", None, False),
    ("## Die Tankregelung: Fair geht vor", None, False),
]

# Melde-Pflicht der Wache: Klebefalle = ja/nein. Fuenf echte Faelle, die der
# Struktur-Modus bewusst nicht anfasst, und fuenf saubere lange Ueberschriften,
# die die alte Laengen-Heuristik als Strukturfehler verraten hatte.
GLUE_REPORT = [
    ("### Fehler 2: Verstaubte Heizkörper & verdeckte Konvektoren Staub, Vorhänge "
     "und Möbel blockieren die Wärmeabgabe. Das Thermostat reagiert zu spät.", True),
    ("### Fehler 3: Dauerlüften über gekippten Fenstern Gekippte Fenster kühlen das "
     "Mauerwerk aus, ohne ausreichenden Luftaustausch. Das führt zu Feuchte.", True),
    ("### Fehler 4: Veraltete, manuelle Thermostate im Dauereinsatz Alte Drehventile "
     "reagieren träge, heizen weiter, und ignorieren Sonnenwärme.", True),
    ("### 5. Saisonale Lebensmittel & Vorratshaltung Kürbisse, Äpfel und Kohl haben "
     "im Herbst Saison. Importware kostet oft ein Vielfaches.", True),
    ("### 6. Energieeffizienz durch Fensterdichtungen Undichte Fenster lassen kalte "
     "Luft herein. Dichtungsbänder kosten 10 €. Die Räume bleiben warm.", True),
    ("## Die Psychologie des Wartens: Warum du nicht bis zum letzten Tag warten "
     "solltest", False),
    ("## Tarifwechsel bei Strom und Gas: Der schnellste Weg zu mehreren hundert "
     "Euro Ersparnis", False),
    ("### Gibt es einen Unterschied zwischen einer reinen Hausrat‑Police und einer "
     "Kombi‑Police (Hausrat + Elementar)?", False),
    ("### Was ist der Unterschied zwischen DNS over HTTPS (DoH) und DNS over TLS "
     "(DoT)?", False),
    ("## Die 5 teuersten Spätsommer‑Fehler beim **Gasrechnung senken**", False),
    ("### Phase 3: Neuen Anbieter beauftragen (Nicht selbst kündigen!)", False),
    ("## Tarifvergleich: Altvertrag vs. Neukunden-Wechseltarif", False),
    ("### Was kostet eine gute Privathaftpflicht für Singles bzw. Familien?", False),
    ("## Tagesgeld vs. Festgeld vs. Girokonto", False),
]

HEAD_KEEP = [
    ("## Strom sparen im Haushalt: Die 8 besten Tipps für den Herbst", BODY_RULES),
    ("## Mietwagen buchen: Kaution vergleichen und sparen", BODY_RULES),
    # Laenge und Unterstitel sind kein Strukturfehler – die alte Laengen-Heuristik
    # meldete genau diese sauberen Ueberschriften.
    ("## Die Psychologie des Wartens: Warum du nicht bis zum letzten Tag warten "
     "solltest", BODY_RULES),
    ("## Tarifwechsel bei Strom und Gas: Der schnellste Weg zu mehreren hundert "
     "Euro Ersparnis", BODY_RULES),
    ("### Gibt es einen Unterschied zwischen einer reinen Hausrat‑Police und einer "
     "Kombi‑Police (Hausrat + Elementar)?", BODY_RULES),
    ("### Was ist der Unterschied zwischen DNS over HTTPS (DoH) und DNS over TLS "
     "(DoT)?", BODY_RULES),
    # C16: in einer sauberen Ueberschrift wird Fettdruck entfernt …
    # … in einer geklebten Zeile bleibt er stehen (der Struktur-Modus braucht ihn)
    ("### Fehler 2: Verstaubte Heizkörper **Was passiert?** Staub blockiert die "
     "Wärmeabgabe. Das Thermostat reagiert zu spät.", BODY_RULES),
]

FIX_HEAD_CASES = [
    ("## Was sind die besten Frugalismus Tipps für den Einstieg?",
     "## Was sind die besten Frugalismus-Tipps für den Einstieg?", BODY_RULES),
    ('title: "Heizung wartung: So bereitest du dein Heim effizient vor"',
     'title: "Heizungswartung: So bereitest du dein Heim effizient vor"',
     TYPO_RULES),
    ("## Die 5 teuersten Fehler beim **Gasrechnung senken**",
     "## Die 5 teuersten Fehler beim Gasrechnung senken", BODY_RULES),
    ("### **Fazit:** Die Heizung wartet nicht",
     "### Fazit: Die Heizung wartet nicht", BODY_RULES),
]


def selftest():
    fehler = []
    for src, want, allowed, cont, is_head in FIX_CASES:
        got = apply_rules(src, allowed, Sink(), heading=is_head, continuation=cont)
        if got != want:
            fehler.append(f"Fix-Fall: {src!r} -> {got!r} (erwartet {want!r})")
        again = apply_rules(got, allowed, Sink(), heading=is_head, continuation=cont)
        if again != got:
            fehler.append(f"Nicht idempotent: {src!r} -> {got!r} -> {again!r}")
    for src, allowed in KEEP_CASES:
        got = apply_rules(src, allowed, Sink(), continuation=True) if allowed else src
        if got != src:
            fehler.append(f"Schutzfall verbogen: {src!r} -> {got!r}")
    for p in (ROOT / "scripts" / "tag_casing.py", WHITELIST_FILE):
        if not p.exists():
            fehler.append(f"Bestandteil fehlt: {p.relative_to(ROOT)}")
    for src, allowed in HEAD_KEEP:
        got = apply_rules(src, allowed, Sink(), heading=True, continuation=True)
        if got != src:
            fehler.append(f"Ueberschrift verbogen: {src[:48]!r} -> {got[:48]!r}")
    for src, want, allowed in FIX_HEAD_CASES:
        got = apply_rules(src, allowed, Sink(), heading=True, continuation=True)
        if got != want:
            fehler.append(f"Heading-Fix: {src!r} -> {got!r} (erwartet {want!r})")
    for src, must in GLUE_REPORT:
        got = _glue_signal(src)
        if got != must:
            fehler.append(f"Klebefuge-Fehlmeldung bei {src[:46]!r}: {got} != {must}")
    for src, want, must in HG_CASES:
        got = split_heading_glue(src)
        got_lines = got[0] if got else None
        if must and got_lines != want:
            fehler.append(f"HeadGlue: {src[:44]!r} -> {got_lines!r}")
        if not must and got_lines is not None:
            fehler.append(f"HeadGlue: unnoetige Trennung bei {src[:44]!r}")
    return fehler


def main():
    if DO_SELFTEST:
        f = selftest()
        if f:
            print("🛑 CASING-SELBSTTEST FEHLGESCHLAGEN:")
            print("\n".join("   " + x for x in f))
            return 2
        print(f"✅ Casing-Selbsttest: {len(FIX_CASES) + len(FIX_HEAD_CASES)} Fix-Faelle + "
              f"{len(KEEP_CASES) + len(HEAD_KEEP)} Schutz-Faelle + {len(HG_CASES)} "
              "Struktur-Faelle gruen (inkl. Idempotenz).")
        return 0

    st = selftest()
    if st:
        print("🛑 CASING-SELBSTTEST FEHLGESCHLAGEN – Sabotage verhindert, "
              "keine Datei wird geschrieben.")
        for e in st:
            print(f"   {e}")
        return 2

    if DO_HEADGLUE:
        done = headglue_pass(target_files())
        print(f"HeadGlue ({'dry-run' if DRY_RUN else 'fix'}): {len(done)} "
              "Ueberschrift(en) vom angeklebten Absatz getrennt.")
        for d in done[:20]:
            print("  ·", d)
        return 0

    rows = []
    files = target_files()
    for p in files:
        found, new_text = process_file(p)
        if not found:
            continue
        row = {"pfad": str(p.relative_to(ROOT)), "funde": found, "woerter": words_of(p)}
        heilbar = [h for h in found if not h["regel"].endswith("-report")]
        if heilbar and DO_FIX and not DRY_RUN and new_text != p.read_text(encoding="utf-8"):
            p.write_text(new_text, encoding="utf-8")
            row["gefixt"] = len(heilbar)
        rows.append(row)

    if DO_PLAN and PLAN_FILE.exists():
        found, new_text = process_plan(PLAN_FILE.read_text(encoding="utf-8"))
        if found:
            row = {"pfad": str(PLAN_FILE.relative_to(ROOT)), "funde": found,
                   "woerter": words_of(PLAN_FILE)}
            heilbar = [h for h in found if not h["regel"].endswith("-report")]
            if heilbar and DO_FIX and not DRY_RUN:
                PLAN_FILE.write_text(new_text, encoding="utf-8")
                row["gefixt"] = len(heilbar)
            rows.append(row)

    geparkt = gate_new(rows) if DO_GATE else []
    total = sum(len(r["funde"]) for r in rows)
    mode = ("gate" if DO_GATE else "fix" if DO_FIX else "dry-run" if DRY_RUN else "report")
    mode += " · " + ("new-only" if NEW_ONLY else "Bestand")
    mode += " · +Pinterest-Plan" if DO_PLAN else ""
    if not DRY_RUN:
        write_report(rows, mode, len(files))
        log_history(rows, geparkt)
    if DO_JSON:
        JSON_OUT.write_text(json.dumps({
            "stand": f"{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}",
            "modus": mode, "dateien": len(rows), "befunde": total,
            "hart": sum(1 for r in rows for f in r["funde"] if f["regel"] in HARD_RULES),
            "gefixt": sum(r.get("gefixt", 0) for r in rows), "geparkt": geparkt,
            "dateien_liste": [{"pfad": r["pfad"], "befunde": len(r["funde"]),
                               "woerter": r["woerter"]} for r in rows],
        }, ensure_ascii=False, indent=1), encoding="utf-8")

    if not total:
        print("Casing-Guard: 🎉 keine Befunde – Groß-/Kleinschreibung sauber.")
        return 0
    print(f"Casing-Guard ({mode}): {len(rows)} Datei(en), {total} Fundstelle(n).")
    if DO_FIX and not DRY_RUN:
        print(f"  ✅ Auto-Fix: {sum(r.get('gefixt', 0) for r in rows)} Korrektur(en) geschrieben.")
    if geparkt:
        print(f"  🅿 Gate: {len(geparkt)} Artikel als Entwurf geparkt (harte Restfunde).")
    for r in rows[:15]:
        rules = ", ".join(sorted({f["regel"] for f in r["funde"]}))
        print(f"  · {r['pfad']}: {len(r['funde'])} ({rules})")
    hart = sum(1 for r in rows for f in r["funde"] if f["regel"] in HARD_RULES)
    return 1 if (hart and not DO_FIX) else 0


if __name__ == "__main__":
    raise SystemExit(main())
