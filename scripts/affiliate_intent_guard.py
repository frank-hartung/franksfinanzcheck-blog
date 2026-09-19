#!/usr/bin/env python3
# ============================================================
#  AFFILIATE-INTENT-GUARD – die Intent-Wache (IW0–IW9)
#  (Premium-Reparatur 19.09.2026 · Auftrag Frank: „Falsche Affiliate-
#   Ziele sofort reparieren … Dazu sollte eine automatische Intent-Wache
#   entstehen, die beispielsweise verhindert, dass ein Kfz-Artikel
#   jemals wieder auf Haftpflicht geroutet wird. Bitte dauerhaft auf dem
#   Premium-Level einer Profi-Agentur beheben.")
#
#  ------------------------------------------------------------
#  DIE LÜCKE, DIE DIESE WACHE SCHLIESST
#
#  Affiliate-Integrität hieß hier bis 19.09.2026: Der Link ist registriert,
#  strukturell heil, steht im gebauten HTML und leitet auf die registrierte
#  Partner-URL weiter (AI1–AI5). Das ist die TECHNIK. Am 19.09. zeigte der
#  Bestand sieben Funde, die alle technisch grün waren und trotzdem den
#  Besucher in ein anderes Produkt schickten:
#
#    Artikel                          CTA-Ziel                    richtig
#    Kfz-Versicherungsvergleich       /go/haftpflicht/            /go/kfz-versicherung/
#    Kostenloses Girokonto            /go/kredit/                 /go/girokonto/
#    Kreditkartenvergleich            /go/reisekrankenversicherung/ /go/kreditkarte/
#    Mietwagen-Ratgeber (1.+letzter)  /go/kfz-versicherung/       /go/mietwagen/
#    „Tagesgeldvergleich“             → C24 Bank (Einzelanbieter, kein Vergleich)
#    „Flüge“                          → Pauschalreise-Angebot (kein Flugvergleich)
#    Wohngebäudeversicherung          → Hausrat (andere Police)
#
#  Dazu zwei stille Nachbarn desselben Musters:
#    · „Gasvergleich“ → /go/strom/ (Gas-Rechnungsartikel, 19.09.)
#    · „Standby Kosten reduzieren …“ / „Ratgeber Strom Sparen“ → /go/gas/
#      (interne Weiterlesen-Links wurden zu Affiliate-Gateways entführt)
#
#  Gemeinsame Wurzel: niemand verglich das VERSPROCHENE Angebot (Anker,
#  CTA-Satz, Artikelthema) mit dem GELIEFERTEN Angebot (Route → Partner-
#  zielseite). Diese Wache tut genau das – pro Link, deterministisch,
#  ohne KI, mit Selbstheilung und eingefrorenen Regressionstests.
#
#  ------------------------------------------------------------
#  PRÜFUNGEN
#
#    IW0 KONTRAKT       Kontrakt-Selbsttest grün · jede registrierte Route
#                       hat ein Ziel (und umgekehrt) · data/affiliate_ziele.yaml
#                       ist bytegleich zum Kontrakt · affiliate_health.py hat
#                       einen ROUTE_CONTRACT-Eintrag je Route.
#    IW1 ANKER↔ROUTE    Nennt der Anker EINDEUTIG ein Produkt, muss die
#                       Route dieses Produkt liefern. („Kfz-Versicherung
#                       vergleichen" → /go/haftpflicht/ = Fund.)
#    IW2 PRIMÄR-CTA     Top-/Mid-/End-CTA muss dem Artikelthema dienen
#                       (oder durch den CTA-Kontext gedeckt sein) – und der
#                       Anker muss das Angebot nennen.
#    IW3 EHRLICHKEIT    Routen mit dokumentierter Abweichung (C24 Bank statt
#                       Marktvergleich, Pauschalreise statt Flugvergleich)
#                       müssen das echte Ziel im Anker/CTA-Satz benennen und
#                       dürfen das nicht lieferbare Versprechen nicht nennen.
#    IW4 NIE-PAARE      Eingefrorene Verbots-Paare (Artikelthema → Route),
#                       z. B. (kfz-versicherung → haftpflicht). Jeder Eintrag
#                       trägt den Beleg-Fund. Hart: kein Publish, kein Merge.
#    IW5 GATEWAY        static/go/<key>/ benennt das echte Ziel (Name aus dem
#                       Kontrakt), ist noindex und leitet auf exakt die
#                       registrierte Partner-URL weiter.
#    IW6 GENERATOR      affiliate_marketer.py muss für JEDE Route konforme
#                       CTAs erzeugen (Route, produkt-exakter Anker, ehrliche
#                       Abweichungs-Nennung). Wer die Vorlagen verwässert,
#                       bekommt Exit 2 – die Quelle ist mitbewacht.
#    IW7 INTERNE LINKS  Ein /go/-Link, dessen Anker ein interner Artikel-/
#                       Pillar-Titel ist (oder im selben Artikel bereits als
#                       interner Link existiert), ist ein entführter Lesetipp.
#    IW8 ANKER-GENERISCH „Jetzt Angebote vergleichen“/„Tarifrechner starten“
#                       nennen kein Angebot → Heilung auf den ehrlichen Anker.
#    IW9 TEMPLATES      Hartkodierte /go/-CTAs in layouts/ (Pillar-Boxen,
#                       Vergleichstabellen) und Shortcode-Parameter
#                       (cta_url/cta_text) gegen denselben Kontrakt.
#
#  SELBSTHEILUNG (deterministisch, idempotent, nie Lösch-Aktionismus):
#    · IW1/IW2/IW4 → Route wird umgeschrieben (Anker = Versprechen, Artikel-
#      thema = Kaufabsicht), Anker wird produkt-exakt aus dem Kontrakt gesetzt.
#    · IW3         → Primär-CTA wird KOMPLETT aus Kontrakt-Satz + Anker neu
#      gesetzt (Haus-Regel: CTA-Boxen nie text-flicken). In-Text-Anker
#      bekommen den grammatisch sicheren Kontrakt-Anhang („… der C24 Bank“);
#      ist das Versprechen selbst falsch („Tagesgeldvergleich“), meldet die
#      Wache mit Rewrite-Vorschlag (owner=human) statt halber Arbeit.
#    · IW5/IW0     → Gateway-Seiten und data/affiliate_ziele.yaml werden neu
#      gebacken (Generatoren, keine Handarbeit).
#    · IW7         → entführter Lesetipp wird zum internen Link; ist die
#      korrekte Zeile schon da, fällt die entführte Doppelzeile weg.
#    · IW6/IW9     → melden (owner=human): Generatoren und Templates sind
#      Verantwortung von Menschen, die Wache beweist nur die Abweichung.
#
#  EINBINDUNG
#    · scripts/affiliate_integrity_gate.py  (AI6: Intent-Beweis im Tageslauf)
#    · scripts/publish_gate.py              (hartes Kriterium 5 pro Kandidat)
#    · .github/workflows/affiliate-integrity-daily.yml (täglich 06:00 MESZ)
#    · .github/workflows/content-engine-v2.yml (--fix --new-only vor Publish)
#    · .github/workflows/seo-weekly.yml     (Bestand, nicht-destruktiv)
#    · scripts/tests/test_affiliate_intent_guard.py (Unit-Beweis)
#
#  Aufruf:
#    python3 scripts/affiliate_intent_guard.py                # Report
#    python3 scripts/affiliate_intent_guard.py --fix          # heilen
#    python3 scripts/affiliate_intent_guard.py --selftest     # Sabotage-Schutz
#    python3 scripts/affiliate_intent_guard.py --bake         # Daten+Gateways
#    python3 scripts/affiliate_intent_guard.py --json         # Maschine
#    python3 scripts/affiliate_intent_guard.py --heal --file <pfad>  # Reserve
#    python3 scripts/affiliate_intent_guard.py --dry-run      # nichts schreiben
#
#  Exit: 0 grün/geheilt · 1 Inhaltsschaden offen · 2 Werkzeugfehler
#        (fail-closed: ohne Beweis keine Veröffentlichung)
# ============================================================

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
CONTENT = ROOT / "content"
GO_DIR = ROOT / "static" / "go"
REGISTRY = ROOT / "scripts" / "check24_links.yaml"
DATA_ZIELE = ROOT / "data" / "affiliate_ziele.yaml"
REPORT = ROOT / "AFFILIATE-INTENT-REPORT.md"
STATE = ROOT / ".affiliate_intent_state.json"
HISTORY = ROOT / "data" / "affiliate_intent_history.jsonl"
RENDER_HOOK = ROOT / "layouts" / "_default" / "_markup" / "render-link.html"
ANCHOR_PARTIAL = ROOT / "layouts" / "_partials" / "affiliate_anchor_attrs.html"
# Lädt data/affiliate_ziele.yaml für die Templates – über os.ReadFile, NICHT
# über hugo.Data/site.Data (data/ enthält *.jsonl-Protokolle; ein einziger
# site.Data-Zugriff lässt Hugo den ganzen Baum parsen und den Build sterben).
ZIELE_PARTIAL = ROOT / "layouts" / "_partials" / "affiliate_ziele_data.html"
LAYOUTS = ROOT / "layouts"
# Verbotener Zugriff auf den data/-Baum in Layouts (Build-Killer, 19.09.2026)
DATENBAUM_GRIFF = re.compile(r"\b(?:site\.Data|\.Site\.Data|hugo\.Data)\b")
HUGO_KOMMENTAR = re.compile(r"\{\{-?\s*/\*.*?\*/\s*-?\}\}", re.S)
HTML_KOMMENTAR = re.compile(r"<!--.*?-->", re.S)

sys.path.insert(0, str(SCRIPTS))

import affiliate_intent_contract as vk  # noqa: E402  (Kontrakt = Wahrheit)
from post_utils import join_article, split_article  # noqa: E402

EXIT_OK = 0
EXIT_CONTENT = 1
EXIT_TOOL = 2

ARGS = sys.argv[1:]
DO_FIX = "--fix" in ARGS or "--bake" in ARGS
DRY_RUN = "--dry-run" in ARGS
AS_JSON = "--json" in ARGS
SELFTEST = "--selftest" in ARGS
BAKE_ONLY = "--bake" in ARGS
NEW_ONLY = "--new-only" in ARGS
HEAL = "--heal" in ARGS
NO_GATEWAY = "--no-gateway" in ARGS
INCLUDE_DRAFTS = "--include-drafts" in ARGS or HEAL or True
HEAL_FILES: list[str] = [ARGS[i + 1] for i, a in enumerate(ARGS)
                         if a == "--file" and i + 1 < len(ARGS)]

# ------------------------------------------------------------------ #
#  Muster
# ------------------------------------------------------------------ #
# Markdown-Link auf ein Gateway. Anker MIT/ohne Bold, Query-Parameter
# (?subid=…) erlaubt – wie im Render-Hook.
MD_GO_LINK = re.compile(
    r"\[(?P<anchor>[^\]\[]*)\]\((?P<url>/go/(?P<key>[\w-]+)(?P<slash>/?)\??[^)\s]*)\)")
GO_KEY = re.compile(r"/go/([\w-]+)")
CTA_PARAM = re.compile(r'(?P<name>cta_url|cta-url)\s*=\s*"(?P<url>/go/(?P<key>[\w-]+)/*)"')
CTA_TEXT_PARAM = re.compile(r'cta_text\s*=\s*"(?P<text>[^"]*)"')
# CTA-Zeile: [> ][Emoji ]**Marker:** Satz [Anker](/go/key/) Rest
CTA_LINE = re.compile(
    r"^(?P<prefix>(?:>\s*)?[^\n\[]*?\*\*[^*\n]{3,}:\*\*\s*)"
    r"(?P<satz>[^\n\[]*?)"
    r"\[(?P<anchor>[^\]\[]*)\]\((?P<url>[^)\s]+)\)"
    r"(?P<rest>[^\n]*)$")

DASH_NORMAL = dict.fromkeys(
    [0x2010, 0x2011, 0x2012, 0x2013, 0x2014, 0x2015, 0x2212], ord("-"))


def marker_view(text: str) -> str:
    """Such-Sicht mit normalen Bindestrichen – Offsets bleiben gültig
    (Konvention aus affiliate_integrity_gate.py, Vorfall 14.09.2026)."""
    return text.translate(DASH_NORMAL)


# (Marker, Slot) – dieselbe Wahrheit wie im Integritäts-Gate + die
# Varianten, die affiliate_marketer.py erzeugt.
CTA_MARKERS = [
    ("Schnell-Tipp von FranksFinanzcheck", "top"),
    ("Spar-Tipp zwischendurch", "mid"),
    ("Spar-Tipp von FranksFinanzcheck", "mid"),
    ("Jetzt vergleichen und sparen", "end"),
    ("Sparend zuerst vergleichen", "end"),
]


# Struktur-Erkennung (19.09.2026): Nicht jeder CTA trägt einen kanonischen
# Marker. Pillar-Seiten und ältere Artikel bauen dieselbe Struktur mit eigenen
# Worten („👉 **Passendes Tagesgeldkonto finden:** [**→ …**](/go/…)"). Ohne
# diese Erkennung galten sie als In-Text-Prosa, und die Wache durfte sie nicht
# deterministisch heilen (Menschen-Fund statt Kontrakt-Zeile).
# Im Bestand vorkommende CTA-Emojis: 👉 (78×), 💡 (51×), 💶 (44×).
CTA_STRUKTUR = re.compile(
    r"^(?:>\s*)?(?P<emoji>\U0001F4A1|\U0001F4B6|\U0001F449)\s*"
    r"\*\*[^*\n]{3,}:?\*\*.*?\[\*\*[^\]\n]+\*\*\]\(/go/")
SLOT_EMOJI = {"\U0001F4A1": "top", "\U0001F4B6": "mid", "\U0001F449": "end"}


def slot_of_line(line: str) -> str:
    """top/mid/end für eine CTA-Zeile, sonst "intext".

    Zwei Beweise: (1) kanonischer Marker-Text ( Hausstil, den auch
    affiliate_integrity_gate.py kennt), (2) CTA-Struktur (Emoji + fetter
    Marker + fetter /go/-Link). Prosa mit ungefettetem Link bleibt intext –
    dort ist der Anker Teil der Grammatik und darf nicht automatisiert
    umgebaut werden.
    """
    view = marker_view(line).lower()
    for marker, slot in CTA_MARKERS:
        if marker.lower() + ":" in view or marker.lower() + "**:" in view:
            return slot
    m = CTA_STRUKTUR.match(line)
    if m:
        return SLOT_EMOJI.get(m.group("emoji"), "mid")
    return "intext"


# ------------------------------------------------------------------ #
#  Registry / Kontrakt laden
# ------------------------------------------------------------------ #
def load_registry(root: Path | None = None) -> dict[str, str]:
    """scripts/check24_links.yaml → {route: partner-url} (Simpelparse,
    Konvention aus affiliate_shield.py – kein PyYAML im CI-Pfad nötig)."""
    reg_file = (root or ROOT) / "scripts" / "check24_links.yaml"
    out: dict[str, str] = {}
    for line in reg_file.read_text(encoding="utf-8").splitlines():
        m = re.match(r'^\s+([\w-]+):\s*"(https://[^"]+)"', line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def fm_value(fm: str, key: str) -> str:
    m = re.search(rf'(?m)^{key}:\s*(.*)$', fm or "")
    return m.group(1).strip().strip('"\'') if m else ""


def fm_list(fm: str, key: str) -> list[str]:
    raw = fm_value(fm, key)
    if not raw:
        return []
    if raw.startswith("["):
        return [x.strip().strip('"\'') for x in raw.strip("[]").split(",") if x.strip()]
    return [x.strip().strip('-"\' ') for x in raw.splitlines() if x.strip()]


# ------------------------------------------------------------------ #
#  Artikel-Inventar
# ------------------------------------------------------------------ #
def content_files() -> list[Path]:
    """Alle Content-Dateien mit Gateway-Links (Posts inkl. Entwürfe, Pillar).

    Entwürfe gehören dazu: Die Reserve ist der Vorrat der Content-Engine –
    eine Fehllink-Route, die erst beim Publish auffällt, ist ein Live-Fund.
    """
    dateien: list[Path] = []
    dateien += sorted((CONTENT / "posts").glob("*/index.md"))
    dateien += sorted((CONTENT / "posts").glob("*.md"))
    dateien += sorted((CONTENT / "pillar").glob("*/index.md"))
    dateien += sorted((CONTENT / "pillar").glob("*/_index.md"))
    if HEAL_FILES:
        wanted = {Path(p).resolve() for p in HEAL_FILES}
        dateien = [p for p in dateien if p.resolve() in wanted]
        for raw in HEAL_FILES:            # Reserve-Pfade außerhalb content/posts
            p = Path(raw)
            if p.is_file() and p not in dateien:
                dateien.append(p)
    elif NEW_ONLY:
        heute = date.today().isoformat()
        dateien = [p for p in dateien if p.parent.name.startswith(heute)]
    return dateien


def load_articles(paths: list[Path] | None = None) -> list[dict]:
    arts: list[dict] = []
    for path in paths or content_files():
        text = path.read_text(encoding="utf-8")
        prefix, fm, body = split_article(text)
        slug = path.parent.name if path.name in ("index.md", "_index.md") \
            else path.stem
        arts.append({
            "slug": slug,
            "path": path,
            "rel": os.path.relpath(path, ROOT),
            "prefix": prefix,
            "fm": fm,
            "body": body,
            "text": text,
            "title": fm_value(fm, "title"),
            "tags": fm_list(fm, "tags") + fm_list(fm, "keywords"),
            "pillar": fm_value(fm, "pillar"),
            "draft": bool(re.search(r"(?m)^draft:\s*true\s*$", fm or "")),
            "section": "pillar" if f"{os.sep}pillar{os.sep}" in str(path) else "posts",
        })
    return arts


def titel_index(arts: list[dict]) -> dict[str, str]:
    """Normierter Titel → relativer Pfad (für IW7, entführte Lesetipps)."""
    idx: dict[str, str] = {}
    for a in arts:
        if a["title"]:
            idx[vk.norm(a["title"])] = a["slug"]
    return idx


# ------------------------------------------------------------------ #
#  Artikelthema (Kaufabsicht des Lesers)
# ------------------------------------------------------------------ #
def pillar_route(pillar: str) -> str:
    return {
        "frugalismus": "allgemein",
        "internet-dsl": "dsl",
        "konto-karten": "girokonto",
        "strom-sparen": "strom",
        "mietwagen": "mietwagen",
        "versicherungen": "haftpflicht",
    }.get(pillar, "allgemein")


def themen(art: dict) -> dict:
    """Dominantes Thema + belegte Themen des Artikels.

    Reihenfolge der Beweiskraft (Profi-Regel: der TITEL ist die klarste
    Aussage, ein schon vorhandener /go/-Link die schwächste – sonst
    „wäscht“ ein Fehllink sein eigenes Thema rein, genau der Mechanismus,
    der am 19.09. den Gas-Artikel auf /go/strom/ stehen ließ):
      1. Titel   2. Tags/Keywords   3. Intro (erste 1200 Zeichen)
      4. ganzer Body   5. Pillar   6. erste /go/-Route im Artikel
    """
    body = art["body"] or ""
    body_ohne_cta = "\n".join(
        l for l in body.split("\n") if slot_of_line(l) == "intext"
        or not GO_KEY.search(l))
    kandidaten = [
        vk.route_fuer_text("", art["title"]),
        vk.route_fuer_text(" ".join(art["tags"])),
        vk.route_fuer_text(body_ohne_cta[:1200]),
        vk.route_fuer_text(body_ohne_cta),
    ]
    belegt: dict[str, int] = {}
    for pos, k in enumerate(kandidaten):
        if k:
            belegt[k] = max(belegt.get(k, 0), 4 - pos)
    for m in GO_KEY.finditer(body):
        key = m.group(1).lower()
        if key in vk.ZIELE:
            belegt.setdefault(key, 1)
    dominant = next((k for k in kandidaten if k), "")
    if not dominant:
        dominant = pillar_route(art["pillar"])
    if not dominant:
        dominant = "allgemein"
    belegt[dominant] = max(belegt.get(dominant, 0), 5)
    return {"dominant": dominant, "belegt": belegt, "kandidaten": kandidaten}


def kontext_route(body: str, pos: int, fenster: int = 220) -> str:
    """Thema im Umfeld einer CTA (Satz davor + Abschnitt danach).

    Beweist Cross-Selling: Steht direkt an der CTA das Produkt der Route
    (z. B. „Wie lassen sich Strom und Energie clever managen?“ unter dem
    Top-CTA), ist die Route redaktionell gedeckt – auch wenn das dominante
    Artikelthema ein anderes ist.
    """
    anfang = max(0, pos - fenster)
    ende = min(len(body), pos + fenster)
    return vk.route_fuer_text(body[anfang:ende])


# ------------------------------------------------------------------ #
#  Befund-Baustein
# ------------------------------------------------------------------ #
def befund(code: str, art: dict, zeile: int, route: str, anchor: str,
           slot: str, problem: str, heilung: str = "", owner: str = "auto",
           severity: str = "P1", ziel_route: str = "", ziel_anker: str = "",
           blocking: bool | None = None) -> dict:
    """Ein Fund. `blocking` entscheidet über Exit 1 / Publish-Stopp.

    Nicht blockierend sind HINWEISE (severity P3): ehrliches Cross-Selling,
    das die Wache nicht verändern darf, das ein Mensch aber sehen sollte.
    Ein Hinweis, der blockiert, wäre ein Dauer-Alarm ohne Schließpfad
    (Governance-Regel C14: jeder Fund braucht Besitzer und Schließpfad).
    """
    if blocking is None:
        blocking = severity != "P3"
    return {
        "code": code, "slug": art["slug"], "path": art["rel"], "line": zeile,
        "line_datei": zeile + body_offset(art),
        "route": route, "anchor": anchor, "slot": slot, "problem": problem,
        "heilung": heilung, "owner": owner, "severity": severity,
        "ziel_route": ziel_route, "ziel_anker": ziel_anker,
        "blocking": blocking,
    }


def body_anfang(text: str) -> int:
    """Offset, an dem der Body beginnt (direkt hinter der Frontmatter-Naht).

    Bewusst KEIN `post_utils.join_article()` zum Zurückschreiben: Die
    Naht-Normalisierung fräße Leerzeilen hinter der Frontmatter (Fund
    19.09.2026: 59 Leerzeilen in 25 Artikeln im Diff, obwohl nur Anker
    geheilt wurden). Ein Heiler darf ausschließlich die Zeilen anfassen,
    die er heilt – alles andere bleibt byte-exakt.
    """
    if not text.startswith("---"):
        return 0
    ende = text.find("\n---", 3)
    if ende < 0:
        return 0
    nl = text.find("\n", ende + 1)
    return nl + 1 if nl >= 0 else len(text)


def body_offset(art: dict) -> int:
    """Zeilenversatz des Bodys in der Datei – der Report nennt DATEIzeilen
    (Menschen öffnen die Datei, nicht den Body)."""
    text, body = art.get("text", ""), art.get("body", "") or ""
    if body and body in text:
        return text[:text.index(body)].count("\n")
    if not text:
        return 0                      # Werkzeug-/Template-Fund: keine Zeile
    return (art.get("fm", "") or "").count("\n") + 3


def zeile_von(body: str, pos: int) -> int:
    return body.count("\n", 0, pos) + 1


# ------------------------------------------------------------------ #
#  IW1/IW2/IW3/IW4/IW7/IW8 – Link-Prüfung im Content
# ------------------------------------------------------------------ #
def interne_ziele(arts: list[dict]) -> dict[str, str]:
    """Normierter Titel → Markdown-Zielpfad (../../posts/<slug>/)."""
    out: dict[str, str] = {}
    for a in arts:
        if not a["title"]:
            continue
        if a["section"] == "pillar":
            out[vk.norm(a["title"])] = f"../../pillar/{a['slug']}/"
        else:
            out[vk.norm(a["title"])] = f"../../posts/{a['slug']}/"
    return out


def pruefe_artikel(art: dict, reg: dict, titel_pfad: dict[str, str]) -> list[dict]:
    body = art["body"] or ""
    funde: list[dict] = []
    th = themen(art)
    dominant = th["dominant"]
    # Themenwelten-/Pillar-Seiten sind HUBS: Sie bündeln bewusst mehrere
    # Angebote (Konto & Karten = Girokonto + Kreditkarte + Tagesgeld +
    # Kredit). Ein „dominantes Thema" gibt es dort nicht – IW2/IW4 würden
    # jedes ehrliche Zweitangebot als Fund melden (15 Hinweise auf 3 Pillar-
    # Seiten, 19.09.2026). Ehrlichkeit (IW1/IW3/IW8) gilt dort natürlich
    # weiter: Jeder Anker nennt sein Produkt.
    hub = art.get("section") == "pillar" or "/pillar/" in art.get("rel", "")
    view = marker_view(body)

    # interne Link-Ziele desselben Artikels (für IW7b)
    interne_anker: dict[str, str] = {}
    for m in re.finditer(r"\[([^\]\[]*)\]\(((?:\.\./)+[^)\s]*|/(?:posts|pillar)/[^)\s]*)\)",
                         body):
        interne_anker.setdefault(vk.norm(m.group(1)), m.group(2))

    for m in MD_GO_LINK.finditer(body):
        key = m.group("key").lower()
        anchor = m.group("anchor")
        anchor_klar = re.sub(r"^\*\*|\*\*$", "", anchor).strip()
        pos = m.start()
        zeile = zeile_von(body, pos)
        slot = slot_of_line(body[body.rfind("\n", 0, pos) + 1:
                                 body.find("\n", pos) if body.find("\n", pos) > 0
                                 else len(body)])
        z = vk.ziel(key)
        primär = slot in ("top", "mid", "end")
        # Prosa = In-Text-Link ohne Fettung, grammatisch Teil des Satzes
        # („Bei der [C24 Bank](/go/girokonto/) sind Kategorien integriert“).
        # So einen Anker gegen eine CTA-Phrase zu tauschen erzeugt kaputtes
        # Deutsch – und wenn er Partner oder Produkt nennt, ist er auch
        # ehrlich. Deshalb: IW8 greift in Prosa nur ohne Ziel-Nennung.
        ist_prosa = not primär and not anchor.startswith("**")

        # --- IW2a: Route nicht registriert (Register-Gate) ---------------
        if key not in reg:
            funde.append(befund(
                "IW0", art, zeile, key, anchor_klar, slot,
                f"Route /go/{key}/ ist nicht in scripts/check24_links.yaml "
                "registriert – Ziel unbekannt, keine Beweisbarkeit",
                owner="human", ziel_route=dominant))
            continue
        if z is None:
            funde.append(befund(
                "IW0", art, zeile, key, anchor_klar, slot,
                f"Route /go/{key}/ hat keinen Eintrag im Intent-Kontrakt "
                "(scripts/affiliate_intent_contract.py) – Angebot unbekannt",
                owner="human", ziel_route=dominant))
            continue

        # --- IW7: entführter interner Link ------------------------------
        norm_anker = vk.norm(anchor_klar)
        intern = titel_pfad.get(norm_anker) or interne_anker.get(norm_anker)
        if intern and len(norm_anker) > 12:
            funde.append(befund(
                "IW7", art, zeile, key, anchor_klar, slot,
                f"Anker ist ein interner Titel („{anchor_klar[:60]}“), das Ziel "
                f"aber ein Affiliate-Gateway /go/{key}/ – der Lesetipp wurde "
                "zum Werbelink entführt",
                heilung=f"→ {intern}", owner="auto", ziel_route=intern))
            continue

        # --- IW1: Anker nennt eindeutig ein anderes Produkt -------------
        anker_routes = vk.anker_routes(anchor_klar)
        if len(anker_routes) == 1 and anker_routes[0] != key:
            p = anker_routes[0]
            if p in reg:
                pz = vk.ziel(p)
                funde.append(befund(
                    "IW1", art, zeile, key, anchor_klar, slot,
                    f"Anker verspricht „{pz.produkt}“, der Link führt zu "
                    f"„{z.produkt}“ ({z.partner}: {z.landing})",
                    heilung=f"→ /go/{p}/", ziel_route=p,
                    ziel_anker=pz.anker_fuer(slot if primär else "intext",
                                             art["slug"])))
                continue
            funde.append(befund(
                "IW1", art, zeile, key, anchor_klar, slot,
                f"Anker verspricht „{p}“, das ist keine registrierte Route",
                owner="human"))
            continue

        # --- IW4: Nie-Paar (Primär-CTA) ---------------------------------
        # Hart, wenn der Leser NICHT erkennen kann, was er bekommt
        # (generischer Anker). Ehrliches Cross-Selling (Anker nennt Produkt
        # oder Partner) bleibt erlaubt und wird nur als Hinweis gemeldet –
        # sonst würde die Wache redaktionelle Zweitangebote zerstoeren.
        if primär and dominant != "allgemein" and not hub:
            grund = vk.nie_paar(dominant, key)
            if grund:
                transparent = vk.nennt_ziel(anchor_klar, key)
                dz = vk.ziel(dominant)
                funde.append(befund(
                    "IW4", art, zeile, key, anchor_klar, slot,
                    f"Verbotenes Paar: Artikelthema „{dz.produkt}“ → Route "
                    f"„{z.produkt}“. {grund}"
                    + ("" if not transparent else
                       " – Der Anker nennt das Ziel ehrlich, deshalb kein "
                       "Täuschungs-Fund, aber ein redaktioneller Prüfpunkt: "
                       f"Fehlt dem Artikel das Hauptangebot /go/{dominant}/?"),
                    heilung=("" if transparent else f"→ /go/{dominant}/"),
                    owner=("human" if transparent else "auto"),
                    severity=("P3" if transparent else "P1"),
                    ziel_route=("" if transparent else dominant),
                    ziel_anker=("" if transparent else
                               dz.anker_fuer(slot, art["slug"]))))
                if not transparent:
                    continue

        # --- IW2: Primär-CTA dient nicht dem Artikelthema ---------------
        if primär and key != dominant and dominant != "allgemein" and not hub:
            ctx = kontext_route(view, pos)
            if ctx != key:
                dz = vk.ziel(dominant)
                transparent = vk.nennt_ziel(anchor_klar, key)
                funde.append(befund(
                    "IW2", art, zeile, key, anchor_klar, slot,
                    f"{slot}-CTA führt zu „{z.produkt}“, das Artikelthema ist "
                    f"aber „{dz.produkt}“ (ohne Kontextbeweis an der CTA)"
                    + (" – Anker nennt das Ziel, also ehrliches Cross-Selling "
                       "(Prüfpunkt, keine Täuschung)" if transparent else ""),
                    heilung=("" if transparent else f"→ /go/{dominant}/"),
                    owner=("human" if transparent else "auto"),
                    severity=("P3" if transparent else "P1"),
                    ziel_route=("" if transparent else dominant),
                    ziel_anker=("" if transparent else
                               dz.anker_fuer(slot, art["slug"]))))
                if not transparent:
                    continue

        # --- IW3: Ehrlichkeit (Abweichung vom naheliegenden Namen) ------
        zeilen_anfang = body.rfind("\n", 0, pos) + 1
        zeilen_ende = body.find("\n", pos)
        cta_zeile = body[zeilen_anfang:zeilen_ende if zeilen_ende > 0 else len(body)]
        satz = cta_zeile if primär else _satz_um(body, pos)
        ok, grund = z.ehrlich(satz)
        # Satz-Ehrlichkeit (19.09.2026): Auch ein korrekter Anker kann von
        # einem Satz umgeben sein, der mehr verspricht als das Ziel liefert
        # („Vergleiche jetzt führende gebührenfreie Girokonten" → ein einziges
        # C24-Angebot). Bei Primär-CTAs wird OHNE Haus-Marker geprüft: Der
        # Marker („Jetzt vergleichen und sparen:") ist Hausstil und wird von
        # AI1/AI3, dash_guard und umbruch_guard erkannt – ihn umzuschreiben
        # würde den CTA für alle Wächter unsichtbar machen.
        satz_ok, satz_grund = True, ""
        marker_grund = ""
        if ok and z.abweichung and z.abweichung.satz_verbot:
            if primär:
                m2 = CTA_LINE.match(cta_zeile)
                prefix = m2.group("prefix") if m2 else ""
                teilsatz = (m2.group("satz") if m2 else "") + " " + anchor_klar
                satz_ok, satz_grund = z.satz_ehrlich(teilsatz)
                # Kanonische Haus-Marker („Jetzt vergleichen und sparen:")
                # sind Vertrag: AI1/AI3, dash_guard und umbruch_guard
                # erkennen CTA-Zeilen an diesem Text – er darf nicht
                # umgeschrieben werden. EIGENE Marker-Formulierungen schon.
                kanonisch = any(mk.lower() in marker_view(prefix).lower()
                                for mk, _ in CTA_MARKERS)
                if prefix and not kanonisch:
                    m_ok, m_grund = z.satz_ehrlich(prefix)
                    if not m_ok:
                        marker_grund = m_grund
            else:
                satz_ok, satz_grund = z.satz_ehrlich(satz)
        if not ok or not satz_ok or marker_grund:
            if marker_grund and ok and satz_ok:
                funde.append(befund(
                    "IW3", art, zeile, key, anchor_klar, slot,
                    f"CTA-Marker benennt das Angebot falsch: {marker_grund}",
                    heilung=("Marker-Text ohne Vergleichs-Versprechen "
                             "formulieren (Anker und Ziel werden getrennt "
                             "geprüft/geheilt)"),
                    owner="human", ziel_route=key, ziel_anker=anchor_klar))
                # kein continue: Ein generischer Anker in derselben Zeile
                # wird trotzdem deterministisch geheilt (IW8 unten) – ein
                # Menschen-Fund darf die Automatik nicht ausbremsen.
            else:
                heilung, owner, ziel_anker = _ehrlich_heilung(
                    z, anchor_klar, primär, slot, art, nur_satz=bool(ok))
                funde.append(befund(
                    "IW3", art, zeile, key, anchor_klar, slot,
                    f"Angebot wird falsch benannt: {grund or satz_grund}",
                    heilung=heilung, owner=owner, ziel_route=key,
                    ziel_anker=ziel_anker))
                continue

        # --- IW8: generischer Anker (kein Angebot genannt) --------------
        if vk.anker_ist_generisch(anchor_klar) and not (
                ist_prosa and vk.nennt_ziel(anchor_klar, key)):
            neu = z.anker_fuer(slot if primär else "intext", art["slug"])
            funde.append(befund(
                "IW8", art, zeile, key, anchor_klar, slot,
                "Anker nennt kein Angebot – der Leser erfährt erst nach dem "
                f"Klick, dass er zu „{z.produkt}“ ({z.partner}) kommt",
                heilung=f"Anker → „{neu}“", ziel_route=key, ziel_anker=neu))
            continue

        # --- Anker nennt das Produkt, Route passt, Ehrlichkeit ok -------
        # (Cross-Selling bleibt erlaubt: der Anker selbst ist das Versprechen.)

    # --- Shortcode-CTAs (tarifvergleich / einspartabelle) ---------------
    # Jede ZEILE mit cta_text wird geprüft, nicht nur der erste Treffer im
    # Umkreis des cta_url: Eine Vergleichstabelle hat mehrere Tarif-Zeilen,
    # und am 19.09. sah die Wache nur die erste („Nicht empfohlen") – die
    # generischen Anker der Klick-Zeilen blieben unsichtbar.
    #
    # `cta_muted="true"` rendert ein <span class="ff-tv-btn--muted">, also
    # KEINEN Link (layouts/shortcodes/tarifvergleich.html): „Nicht
    # empfohlen" ist ein redaktionelles Urteil, kein Angebots-Versprechen.
    funde.extend(_shortcode_funde(body, art, reg))
    return funde


_DEKO_VORN = re.compile(r"^[^\w]*")
_DEKO_HINTEN = re.compile(r"[^\w]*$")
_MUTED_PARAM = re.compile(r'cta[_-]muted\s*=\s*"(?:true|1|yes|ja)"', re.I)


def cta_deko(alt: str, neu: str) -> str:
    """Emoji-/Pfeil-Garnitur eines cta_text erhalten (Design-Sprache der
    Vergleichstabellen): „🏆 Jetzt wechseln" → „🏆 Gastarife vergleichen",
    „Tarife prüfen →" → „Gastarife vergleichen →"."""
    vorn = _DEKO_VORN.match(alt or "").group(0)
    hinten = _DEKO_HINTEN.search(alt or "").group(0)
    if len(hinten) > 3:                 # kein Satzende-Schluck
        hinten = ""
    return f"{vorn}{neu}{hinten}"


SHORTCODE_TOKEN = re.compile(
    r"\{\{<\s*(?P<close>/)?\s*(?P<name>[\w-]+)(?P<params>.*?)(?:/)?\}\}", re.S)


def _shortcode_funde(body: str, art: dict, reg: dict) -> list[dict]:
    """Prüft Shortcode-CTAs mit echter Block-Scope (Stack statt Fenster).

    Warum nicht „nächstes cta_url im Umkreis": Eine Vergleichstabelle
    (`tarifvergleich`) trägt das cta_url im ELTERN-Tag, die cta_text-Werte
    stehen in den KIND-Tags (`tarif`). Zwischen beiden schließen Kind-Tags
    (`{{< /tarif >}}`, `{{< /zeile >}}`) – ein zeilenweiser „Reset" hätte
    die gültige URL verworfen und die Klick-Zeilen unsichtbar gemacht
    (Fund 19.09.2026: gesehen wurde nur die stumme Zeile „Nicht
    empfohlen"). Der Stack liefert zu jedem cta_text das zuständige cta_url.
    """
    funde: list[dict] = []
    stack: list[tuple[str, str]] = []          # (Name, Parameter)
    for tok in SHORTCODE_TOKEN.finditer(body):
        if tok.group("close"):
            name = tok.group("name")
            for i in range(len(stack) - 1, -1, -1):
                if stack[i][0] == name:
                    del stack[i:]
                    break
            continue
        params = tok.group("params") or ""
        stack.append((tok.group("name"), params))
        tm = CTA_TEXT_PARAM.search(params)
        if not tm:
            continue
        if _MUTED_PARAM.search(params):
            continue                    # <span class="ff-tv-btn--muted">: kein Link
        um = CTA_PARAM.search(params)
        url = um.group("url") if um else ""
        if not url:
            for _, eltern in reversed(stack[:-1]):
                um2 = CTA_PARAM.search(eltern)
                if um2:
                    url = um2.group("url")
                    break
        if not url:
            continue
        key = url.strip("/").split("/")[-1].lower()
        anchor = tm.group("text").strip()
        zeile = body.count("\n", 0, tok.start() + tm.start()) + 1
        z = vk.ziel(key)
        if key not in reg or z is None:
            funde.append(befund(
                "IW0", art, zeile, key, anchor, "shortcode",
                f"Shortcode-CTA auf nicht registrierte/unbekannte Route /go/{key}/",
                owner="human"))
            continue
        neu_anker = cta_deko(anchor, z.anker_fuer("intext", art["slug"]))
        ok, grund = z.ehrlich(anchor)
        if not ok:
            funde.append(befund(
                "IW3", art, zeile, key, anchor, "shortcode",
                f"Shortcode-CTA benennt das Angebot falsch: {grund}",
                heilung=f"cta_text → „{neu_anker}“", owner="auto",
                ziel_anker=neu_anker))
        elif vk.anker_ist_generisch(anchor):
            funde.append(befund(
                "IW8", art, zeile, key, anchor, "shortcode",
                "Shortcode-CTA nennt kein Angebot – der Leser erfährt erst "
                f"nach dem Klick, dass er zu „{z.produkt}“ ({z.partner}) kommt",
                heilung=f"cta_text → „{neu_anker}“", owner="auto",
                ziel_anker=neu_anker))
        else:
            routen = vk.anker_routes(anchor)
            if len(routen) == 1 and routen[0] != key:
                verspricht = vk.ziel(routen[0])
                funde.append(befund(
                    "IW1", art, zeile, key, anchor, "shortcode",
                    "Shortcode-CTA verspricht "
                    f"„{verspricht.produkt if verspricht else routen[0]}“, "
                    f"führt zu „{z.produkt}“",
                    heilung=f"cta_url → /go/{routen[0]}/ (oder cta_text anpassen)",
                    owner="human", ziel_route=routen[0]))
    return funde


def _heile_shortcode(body: str, f: dict) -> tuple[str, list[str]]:
    """Ersetzt den cta_text einer Shortcode-Zeile (Garnitur bleibt)."""
    zeilen = body.split("\n")
    idx = f["line"] - 1
    if idx >= len(zeilen) or not zeilen[idx].strip():
        return body, []
    zl = zeilen[idx]
    neu = f.get("ziel_anker") or ""
    if not neu:
        return body, []
    m = CTA_TEXT_PARAM.search(zl)
    if not m or m.group("text").strip() == neu:
        return body, []                 # schon geheilt (Idempotenz)
    zeilen[idx] = zl[:m.start(1)] + neu + zl[m.end(1):]
    return ("\n".join(zeilen),
            [f"{f['code']} L{f['line']}: Shortcode-CTA „{m.group('text')}“ "
             f"→ „{neu}“ (/go/{f['route']}/)"])


def _satz_um(body: str, pos: int) -> str:
    """Satz(-bereich) um einen In-Text-Link: Ehrlichkeit darf auch im
    umgebenden Satz stehen (Haus-Regel aus dem C24-Deal, 11.08.2026)."""
    anfang = max(body.rfind("\n", 0, max(0, pos - 240)), 0)
    ende = body.find("\n", pos)
    return body[anfang:ende if ende > 0 else len(body)]


def _ehrlich_heilung(z: vk.Ziel, anchor: str, primär: bool, slot: str,
                     art: dict, nur_satz: bool = False) -> tuple[str, str, str]:
    """(Heilungstext, owner, Ziel-Anker) für eine Ehrlichkeits-Verletzung.

    Ein Anker, ein Entscheidungsweg – Prüfen und Heilen dürfen hier nicht
    auseinanderlaufen (Lehre aus #295: zwei Wege zur CTA-Zeile zählten einen
    Fund, der nie geheilt wurde). Stufen:
      1. Anhang („verzinstes Tagesgeldkonto der C24 Bank") – nur wenn er
         grammatisch trägt UND danach ein Produkt im Anker steht.
      2. Primär-CTA: Kontrakt-Anker (Satz bleibt, wenn er ehrlich ist).
      3. In-Text: Kontrakt-Anker ist eine CTA-Phrase und in Prosa
         grammatisch riskant → Menschen-Fund mit Vorschlag.
    """
    kontrakt = z.anker_fuer(slot if primär else "intext", art["slug"])
    if vk.anhang_sicher(z, anchor) and not nur_satz:
        mit_anhang = anchor + z.abweichung.anhang
        if not vk.anker_ist_generisch(mit_anhang):
            return f"Anker → „{mit_anhang}“", "auto", mit_anhang
    if primär:
        return (f"CTA-Zeile aus dem Kontrakt (ehrlicher Satz + Anker "
                f"„{kontrakt}“)", "auto", kontrakt)
    hinweis = z.abweichung.hinweis if z.abweichung else ""
    return (f"Satz/Anker redaktionell umbauen, Vorschlag: „{kontrakt}“"
            + (f" ({hinweis})" if hinweis else ""), "human", kontrakt)


def heile_artikel(art: dict, funde: list[dict], reg: dict,
                  titel_pfad: dict[str, str]) -> tuple[str, list[str]]:
    """Setzt die Funde deterministisch um. Rückgabe: (neuer Body, Aktionen).

    Reihenfolge (offset-sicher):
      1. Link-Funde zeilenweise von HINTEN nach VORN (IW1/IW2/IW3/IW4/IW8) –
         Zeilennummern bleiben dabei gültig, weil keine Zeile verschwindet.
      2. Entführte Lesetipps (IW7) ÜBER INHALT statt Index: Dieser Schritt
         kann Zeilen entfernen (entführte Doppelzeile), also darf er keine
         Index-Wahrheit aus Schritt 1 erben.
    """
    body = art["body"] or ""
    aktionen: list[str] = []

    sc_funde = [f for f in funde if f["slot"] == "shortcode"
                and f["owner"] == "auto"]
    for f in sorted(sc_funde, key=lambda x: -x["line"]):
        body, akt = _heile_shortcode(body, f)
        aktionen.extend(akt)

    link_funde = [f for f in funde
                  if f["code"] in ("IW1", "IW2", "IW3", "IW4", "IW8")
                  and f["slot"] != "shortcode"]
    # Eine Zeile, ein Urteil: Trifft IW8/IW2/IW4 (Kontrakt-Anker) UND IW3
    # (Anhang) dieselbe Zeile, gewinnt der stärkere Heilweg – der Kontrakt-
    # Anker ist produkt-exakt UND ehrlich, der Anhang nur ehrlich.
    stark = {(f["line"]) for f in link_funde if f["code"] in ("IW2", "IW4", "IW8")}
    link_funde = [f for f in link_funde
                  if not (f["code"] == "IW3" and f["line"] in stark)]
    for f in sorted(link_funde, key=lambda x: -x["line"]):
        body, akt = _heile_link(body, art, f, reg)
        aktionen.extend(akt)

    iw7 = [f for f in funde if f["code"] == "IW7"]
    if iw7:
        body, akt = _heile_lesetipps(body, art, iw7)
        aktionen.extend(akt)
    return body, aktionen


def _heile_lesetipps(body: str, art: dict, iw7: list[dict]) -> tuple[str, list[str]]:
    """IW7: /go/-Links, die in Wahrheit interne Lesetipps sind.

    Zwei Beweise (beide deterministisch):
      a) Der Anker ist exakt ein Artikel-/Pillar-Titel des Bestands.
      b) Derselbe Anker steht im Artikel bereits als korrekter interner Link
         (typisches Schadensbild: Ein Heiler duplizierte den Block und
         routete die Kopie auf das Affiliate-Gateway – Fund 19.09.2026 im
         Artikel „Gasrechnung senken: Deine Strategie für den Winter 2026“).
    Heilung: Ziel zurück auf den internen Pfad. Ist die korrekte Zeile schon
    vorhanden, fällt die entführte Zeile weg (kein doppelter Lesetipp).
    """
    aktionen: list[str] = []
    zeilen = body.split("\n")
    interne_anker: dict[str, str] = {}
    for m in re.finditer(
            r"\[([^\]\[]*)\]\(((?:\.\./)+[^)\s]*|/(?:posts|pillar)/[^)\s]*)\)",
            body):
        interne_anker.setdefault(vk.norm(m.group(1)), m.group(2))
    vorhanden = {}
    for z in zeilen:
        if z.strip():
            vorhanden.setdefault(vk.norm(z), z)

    for f in iw7:
        idx = f["line"] - 1
        if idx >= len(zeilen):
            continue
        ursprung = zeilen[idx]
        if "/go/" not in ursprung:
            continue                     # Zeile ist schon geheilt (Idempotenz)
        intern = f.get("ziel_route") or interne_anker.get(vk.norm(f["anchor"]), "")
        if not intern or intern.startswith("/go/"):
            continue
        neue = MD_GO_LINK.sub(
            lambda m, _z=intern: f"[{m.group('anchor')}]({_z})", ursprung, count=1)
        schon_da = vorhanden.get(vk.norm(neue))
        if schon_da and schon_da != ursprung:
            zeilen[idx] = ""
            aktionen.append(f"IW7 L{f['line']}: entführte Doppelzeile entfernt "
                            f"(korrekter Lesetipp „{f['anchor'][:40]}“ steht bereits da)")
        else:
            zeilen[idx] = neue
            vorhanden[vk.norm(neue)] = neue
            aktionen.append(f"IW7 L{f['line']}: Lesetipp „{f['anchor'][:40]}“ "
                            f"zurück auf {intern} (war /go/{f['route']}/)")
    return "\n".join(zeilen), aktionen


def _heile_link(body: str, art: dict, f: dict, reg: dict) -> tuple[str, list[str]]:
    """Heilt genau einen Link-Fund (zeilenweise, offset-sicher).

    Grundregel der Heilung:
      · IW1 – der Anker IST das Versprechen: nur die Route wird korrigiert,
        der redaktionelle Anker bleibt (Ausnahme: das neue Ziel weicht vom
        Namen ab, dann muss der Anker das echte Ziel nennen → IW3-Logik).
      · IW2/IW4 – die Route folgt dem Artikelthema, der Anker kommt aus dem
        Kontrakt (produkt-exakt).
      · IW3/IW8 – der Anker wird ehrlich bzw. produkt-exakt, Route bleibt.
    """
    zeilen = body.split("\n")
    idx = f["line"] - 1
    if idx >= len(zeilen):
        return body, []
    zeile = zeilen[idx]
    code, route, slot = f["code"], f["route"], f["slot"]
    if f"/go/{route}/" not in zeile:
        return body, []                  # schon geheilt (Idempotenz)
    z = vk.ziel(route)
    neu_route = f.get("ziel_route") or route
    if neu_route.startswith("/go/") or neu_route.startswith("../"):
        return body, []                  # internes Ziel gehört zu IW7
    if neu_route not in reg:
        return body, [f"{code} L{f['line']}: Ziel-Route /go/{neu_route}/ ist "
                      "nicht registriert – keine Heilung (Register ergänzen)"]
    neu_z = vk.ziel(neu_route)
    aktionen: list[str] = []
    primär = slot in ("top", "mid", "end")

    m = MD_GO_LINK.search(zeile)
    if not m:
        return body, [f"{code} L{f['line']}: Link nicht gefunden (kein Heil-Pfad)"]
    anchor = m.group("anchor")
    anchor_klar = anchor.strip("*").strip()

    # ---- Anker-Entscheidung ------------------------------------------
    neu_anker = anchor_klar
    if code == "IW1":
        # Route folgt dem Anker. Nur wenn das neue Ziel ehrlich benannt
        # werden muss (C24/Pauschalreise), wird auch der Anker angefasst.
        if neu_z and neu_z.abweichung and not neu_z.ehrlich(anchor_klar)[0]:
            neu_anker = (f.get("ziel_anker")
                         or neu_z.anker_fuer(slot if primär else "intext",
                                             art["slug"]))
    elif code in ("IW2", "IW4", "IW8"):
        neu_anker = (f.get("ziel_anker")
                     or neu_z.anker_fuer(slot if primär else "intext", art["slug"]))
    elif code == "IW3":
        if f["owner"] == "human":
            return body, [f"IW3 L{f['line']}: {f['problem']} – Vorschlag "
                          f"„{f.get('ziel_anker', '')}“ (redaktionell umbauen)"]
        neu_anker = (f.get("ziel_anker")
                     or neu_z.anker_fuer(slot if primär else "intext",
                                         art["slug"]))

    # ---- Primär-CTA: ganze Zeile aus dem Kontrakt, wenn der SATZ lügt --
    satz_luegt = False
    if neu_z and neu_z.abweichung and neu_z.abweichung.art != "portal":
        probe = zeile.replace(anchor_klar, neu_anker)
        if not neu_z.ehrlich(probe)[0]:
            satz_luegt = True
        elif neu_z.abweichung.satz_verbot:
            m2 = CTA_LINE.match(zeile)
            teil = (m2.group("satz") if m2 else probe) + " " + neu_anker
            satz_luegt = not neu_z.satz_ehrlich(teil)[0]
    if primär and (satz_luegt or (code in ("IW2", "IW4"))):
        neue_zeile, ok = _cta_zeile_neu(zeile, neu_route, slot, art["slug"])
        if ok:
            zeilen[idx] = neue_zeile
            aktionen.append(f"{code} L{f['line']}: {slot}-CTA neu aus dem "
                            f"Kontrakt → /go/{neu_route}/ "
                            f"({neu_z.produkt}, {neu_z.partner})")
            return "\n".join(zeilen), aktionen

    # ---- sonst: chirurgisch (href und/oder Anker) ----------------------
    # Pfeil-Hausstil bleibt: „→ Zur C24 Bank“ → „→ C24 Bank Girokonto“.
    # Der Pfeil ist Gestaltung, nicht Versprechen – ihn zu schlucken würde
    # das CTA-Design der Pillar-Seiten verändern (Design-Regression).
    pfeil = ""
    for zeichen in ("→ ", "➜ ", "» "):
        if anchor_klar.startswith(zeichen) and not neu_anker.startswith(zeichen):
            pfeil = zeichen
            break
    neu_anker = pfeil + neu_anker
    bold = anchor.startswith("**") and anchor.endswith("**")
    if bold:
        neu_anker = f"**{neu_anker}**"
    zeilen[idx] = (zeile[:m.start()] + f"[{neu_anker}](/go/{neu_route}/)"
                   + zeile[m.end():])
    aktionen.append(f"{code} L{f['line']}: /go/{route}/ → /go/{neu_route}/ · "
                    f"Anker „{anchor_klar}“ → „{neu_anker.strip('*')}“")
    return "\n".join(zeilen), aktionen


DISCLAIMER = ("_(Dieser Artikel enthält Affiliate-Links (Werbung). Beim "
              "Abschluss über einen Link erhalten wir eine Provision – für "
              "dich entstehen keine Mehrkosten.)_")


def _cta_zeile_neu(zeile: str, route: str, slot: str, slug: str) -> tuple[str, bool]:
    """Baut eine CTA-Zeile vollständig neu (Vorlage aus dem Kontrakt).

    Erhalt bleibt bytegenau: Blockquote-Prefix, Emoji, Marker-Schreibweise
    (inkl. U+2011-Variante), harter Umbruch (zwei Leerzeichen) und ein
    vorhandener Nachsatz. Neu kommen: Satz (nur bei Abweichung), Anker,
    Route. So bleibt die Wache idempotent und die Layout-Wächter
    (dash_guard, umbruch_guard) sehen dieselbe Struktur wie vorher.
    """
    z = vk.ziel(route)
    if z is None:
        return zeile, False
    m = CTA_LINE.match(zeile)
    if not m:
        return zeile, False
    prefix, satz, rest = m.group("prefix"), m.group("satz"), m.group("rest")
    anker = z.anker_fuer(slot, slug)
    abw = z.abweichung
    braucht_satz = bool(abw and abw.art != "portal" and (
        not z.ehrlich(satz + anker)[0]
        or not z.satz_ehrlich(satz + " " + anker)[0]))
    if braucht_satz:
        neu_satz = z.saetze.get(slot) or z.saetze.get("top") or ""
        if not neu_satz:
            return zeile, False
        satz = neu_satz + ": "
    else:
        if satz and not satz.endswith((":", " ", "–", "-")):
            satz = satz.rstrip() + ": "
        elif not satz:
            satz = ""
    neu = f"{prefix}{satz}[**{anker}**](/go/{route}/){rest}"
    return neu, True


# ------------------------------------------------------------------ #
#  IW0: Kontrakt, Register, Daten-Datei, Health-Kontrakt
# ------------------------------------------------------------------ #
def kommentarfrei(text: str) -> str:
    """Template-Text ohne Hugo-/HTML-Kommentare.

    Kommentare dürfen den verbotenen Zugriff BENENNEN (sie dokumentieren ihn
    ja gerade) – nur echter Code zählt. Ohne diese Unterscheidung würde die
    Wache ihre eigene Warnung im Partial als Sabotage melden.
    """
    return HTML_KOMMENTAR.sub("", HUGO_KOMMENTAR.sub("", text))


def datenbaum_griffe(text: str) -> list[tuple[int, str]]:
    """(Zeile, Treffer) für jeden hugo.Data/site.Data-Zugriff im TEMPLATE-CODE.

    Warum das ein harter Fund ist: data/ enthält Bot-Protokolle als *.jsonl
    (u. a. data/audit/). Hugo parst den kompletten data/-Baum, sobald ein
    Template hugo.Data oder site.Data anfasst, und bricht den Build ab mit
    „unmarshal of format "" is not supported" – die Seite baut nicht mehr,
    kein Deploy, kein Beweis. Am 19.09.2026 genau so passiert, als die
    ehrlichen Zielnamen in den Render-Hook einzogen.
    """
    code = kommentarfrei(text)
    return [(code[:m.start()].count("\n") + 1, m.group(0))
            for m in DATENBAUM_GRIFF.finditer(code)]


def datenpfad_fehler(text: str) -> list[str]:
    """Was am Daten-Partial falsch wäre – rein funktional.

    Dieselbe Logik für IW0, Selbsttest und Regressionstests, damit kein
    Prüfer seine eigene Ausnahme ist. Der Format-Pin ist kein Stil: Ohne
    `format` rät Hugo bei YAML mit #-Kommentarkopf TOML und der Build stirbt
    mit „toml: expected '=' after key" (19.09.2026, PR #321).
    """
    fehler: list[str] = []
    if 'os.ReadFile "data/affiliate_ziele.yaml"' not in text:
        fehler.append("liest data/affiliate_ziele.yaml nicht per os.ReadFile "
                      "(Hausmuster aus themenwelten_data.html)")
    if "transform.Unmarshal" not in text:
        fehler.append("entpackt die Datei nicht mit transform.Unmarshal")
    if '"format" "yaml"' not in text:
        fehler.append("nennt transform.Unmarshal kein explizites Format – Hugo rät "
                      "bei dem #-Kommentarkopf TOML und der Build stirbt "
                      "(„toml: expected '=' after key“)")
    for zeile, treffer in datenbaum_griffe(text):
        fehler.append(f"Zeile {zeile}: Zugriff auf {treffer} – Hugo parst dann den "
                      "ganzen data/-Baum inklusive *.jsonl und der Build stirbt")
    return fehler


def pruefe_datenpfad() -> list[dict]:
    """IW0, Teil Datenpfad: Wie kommt die Angebots-Wahrheit in die Templates?

    Drei Regeln, alle build-kritisch:
      1. kein Layout fasst hugo.Data/site.Data an (Build-Killer),
      2. das Partial lädt data/affiliate_ziele.yaml per os.ReadFile,
      3. beide Verbraucher rufen genau dieses Partial auf.
    """
    funde: list[dict] = []
    pseudo = {"slug": "(Datenpfad)", "rel": "layouts/", "title": "", "tags": [],
              "pillar": "", "body": "", "section": ""}

    for datei in sorted(LAYOUTS.rglob("*.html")):
        for zeile, treffer in datenbaum_griffe(datei.read_text(encoding="utf-8")):
            rel = datei.relative_to(ROOT)
            funde.append(befund(
                "IW0", {**pseudo, "rel": str(rel)}, zeile, "", "", treffer,
                f"{rel}:{zeile} greift auf {treffer} zu – Hugo parst dann den "
                "ganzen data/-Baum inklusive *.jsonl-Protokollen und der Build "
                "stirbt (unmarshal of format "" is not supported). Zielnamen "
                "über layouts/_partials/affiliate_ziele_data.html laden "
                "(os.ReadFile + transform.Unmarshal)", owner="human"))

    if not ZIELE_PARTIAL.exists():
        funde.append(befund(
            "IW0", pseudo, 0, "", "", "",
            "layouts/_partials/affiliate_ziele_data.html fehlt – die Templates "
            "kämen nur noch über hugo.Data an die Zielnamen (Build-Killer)",
            owner="human"))
    else:
        txt = ZIELE_PARTIAL.read_text(encoding="utf-8")
        for fehler_text in datenpfad_fehler(txt):
            funde.append(befund(
                "IW0", {**pseudo, "rel": str(ZIELE_PARTIAL.relative_to(ROOT))},
                0, "", "", "", f"affiliate_ziele_data.html: {fehler_text}",
                owner="human"))

    for pfad in (RENDER_HOOK, ANCHOR_PARTIAL):
        if not pfad.exists():
            continue
        txt = pfad.read_text(encoding="utf-8")
        if 'partialCached "affiliate_ziele_data.html"' not in txt:
            funde.append(befund(
                "IW0", {**pseudo, "rel": str(pfad.relative_to(ROOT))}, 0, "", "", "",
                f"{pfad.relative_to(ROOT)} ruft affiliate_ziele_data.html nicht "
                "auf – Tooltip-Namen hängen dann nur am Fallback-Dict",
                owner="human"))
    return funde


def pruefe_iw0(reg: dict) -> list[dict]:
    funde: list[dict] = []
    pseudo = {"slug": "(Kontrakt)", "rel": "scripts/affiliate_intent_contract.py",
              "title": "", "tags": [], "pillar": "", "body": "", "section": ""}

    for fehler in vk.selftest():
        funde.append(befund("IW0", pseudo, 0, "", "", "", 
                            f"Kontrakt-Selbsttest: {fehler}", owner="human"))

    for route in sorted(set(reg) - set(vk.ZIELE)):
        funde.append(befund(
            "IW0", pseudo, 0, route, "", "",
            "Route ist registriert, hat aber keinen Intent-Kontrakt-Eintrag "
            "(Angebot, Ehrlichkeit, Anker fehlen) – Wache ist für sie blind",
            owner="human"))
    for route in sorted(set(vk.ZIELE) - set(reg)):
        funde.append(befund(
            "IW0", pseudo, 0, route, "", "",
            "Kontrakt kennt die Route, scripts/check24_links.yaml nicht – "
            "keine Partner-URL, kein Gateway", owner="human"))

    # Health-Kontrakt (E2E-Erwartung je Route)
    try:
        import affiliate_health as ah
        fehlt = sorted(set(reg) - set(ah.CONTRACT))
        for route in fehlt:
            funde.append(befund(
                "IW0", pseudo, 0, route, "", "",
                "affiliate_health.py hat keinen ROUTE_CONTRACT-Eintrag – die "
                "Wochenwache kann die Zielseite nicht beweisen", owner="human"))
    except Exception as exc:  # noqa: BLE001
        funde.append(befund("IW0", pseudo, 0, "", "", "",
                            f"affiliate_health.py nicht lesbar: {exc}", owner="human"))

    # Daten-Datei für Hugo
    if not DATA_ZIELE.exists():
        funde.append(befund("IW0", pseudo, 0, "", "", "",
                            "data/affiliate_ziele.yaml fehlt (Hugo-Tooltips "
                            "fallen auf die Template-Kopie zurück)", owner="auto",
                            heilung="python3 scripts/affiliate_intent_guard.py --bake"))
    else:
        soll = vk.bake_yaml()
        ist = DATA_ZIELE.read_text(encoding="utf-8")
        if ist != soll:
            funde.append(befund("IW0", pseudo, 0, "", "", "",
                                "data/affiliate_ziele.yaml weicht vom Kontrakt ab "
                                "(Drift zwischen Template-Wahrheit und Python-Wahrheit)",
                                owner="auto",
                                heilung="python3 scripts/affiliate_intent_guard.py --bake"))

    # Template-Kopien (Fallback-Dict) müssen zum Kontrakt passen
    for pfad in (RENDER_HOOK, ANCHOR_PARTIAL):
        # Fund zeigt auf die TEMPLATE-Datei, nicht auf den Kontrakt –
        # sonst sucht der Mensch an der falschen Stelle.
        pseudo = {"slug": "(Template)", "rel": str(pfad.relative_to(ROOT)),
                  "title": "", "tags": [], "pillar": "", "body": "", "section": ""}
        if not pfad.exists():
            funde.append(befund("IW0", pseudo, 0, "", "", "",
                                f"{pfad.relative_to(ROOT)} fehlt – Tooltips ohne Zielnamen",
                                owner="human"))
            continue
        txt = pfad.read_text(encoding="utf-8")
        if "affiliate_ziele" not in txt:
            funde.append(befund(
                "IW0", pseudo, 0, "", "", "",
                f"{pfad.relative_to(ROOT)} liest data/affiliate_ziele.yaml nicht "
                "(Tooltip hängt an einer Template-Kopie)", owner="human"))
        for route, z in vk.ZIELE.items():
            if route not in txt:
                funde.append(befund(
                    "IW0", pseudo, 0, route, "", "",
                    f"{pfad.relative_to(ROOT)}: Fallback-Name für /go/{route}/ fehlt",
                    owner="human"))
            elif z.anzeige not in txt:
                funde.append(befund(
                    "IW0", pseudo, 0, route, "", "",
                    f"{pfad.relative_to(ROOT)}: Fallback-Name für /go/{route}/ "
                    f"weicht vom Kontrakt ab (erwartet „{z.anzeige}“)",
                    owner="human"))

    # Datenpfad: kein Layout darf den data/-Baum über hugo.Data/site.Data parsen
    funde += pruefe_datenpfad()
    return funde


# ------------------------------------------------------------------ #
#  IW5: Gateway-Seiten
# ------------------------------------------------------------------ #
def pruefe_iw5(reg: dict) -> list[dict]:
    pseudo = {"slug": "(Gateway)", "rel": "static/go/", "title": "", "tags": [],
              "pillar": "", "body": "", "section": ""}
    funde: list[dict] = []
    for route, url in sorted(reg.items()):
        z = vk.ziel(route)
        if z is None:
            continue
        seite = GO_DIR / route / "index.html"
        if not seite.exists():
            funde.append(befund("IW5", pseudo, 0, route, "", "",
                                f"Gateway static/go/{route}/index.html fehlt – "
                                "Klick läuft ins Leere", owner="auto",
                                heilung="Gateway neu backen"))
            continue
        html = seite.read_text(encoding="utf-8")
        if url not in html:
            funde.append(befund("IW5", pseudo, 0, route, "", "",
                                "Gateway leitet NICHT auf die registrierte "
                                "Partner-URL weiter (Drift)", owner="auto",
                                heilung="Gateway neu backen"))
        if "noindex" not in html:
            funde.append(befund("IW5", pseudo, 0, route, "", "",
                                "Gateway ohne noindex – Werbeseite im Index",
                                owner="auto", heilung="Gateway neu backen"))
        if z.ziel_phrase() not in html:
            funde.append(befund("IW5", pseudo, 0, route, "", "",
                                f"Gateway nennt das echte Ziel nicht "
                                f"(erwartet „Weiter {z.ziel_phrase()}“, Seite "
                                f"sagt „{_gateway_name(html)}“) – unehrliche "
                                "Übergabe", owner="auto",
                                heilung="Gateway neu backen"))
    return funde


def _gateway_name(html: str) -> str:
    m = re.search(r"<strong>([^<]+)</strong>", html)
    return m.group(1) if m else "?"


def _md5(pfad: Path) -> str:
    try:
        return hashlib.md5(pfad.read_bytes()).hexdigest()
    except OSError:
        return ""


def backe_gateways(reg: dict) -> int:
    """Gateway-Seiten aus dem Kontrakt neu erzeugen (affiliate_shield ist der
    Generator; hier mit den ehrlichen Namen aus dem Intent-Kontrakt).

    Rückgabe: Anzahl der Seiten, die sich WIRKLICH geändert haben. Ein Bake,
    das jeden Lauf „20 Seiten gebacken" meldet, obwohl die Bytes identisch
    bleiben, ist ein falsches Heilungs-Signal: Der tägliche CI-Lauf würde
    daraus Commit + Deploy ableiten und eine Reparatur behaupten, die keine
    war. Erst vergleichen, dann zählen.
    """
    try:
        import affiliate_shield as sh
    except Exception:  # noqa: BLE001
        return 0
    sh.GO_NAMES = {k: vk.ZIELE[k].gateway for k in reg if k in vk.ZIELE}
    pfade = [GO_DIR / k / "index.html" for k in reg]
    vorher = {p_: _md5(p_) for p_ in pfade}
    sh.generate_go_pages(reg)
    return sum(1 for p_ in pfade if _md5(p_) != vorher[p_])


def backe_daten() -> bool:
    """Datendatei aus dem Kontrakt backen – True nur bei echter Änderung."""
    neu = vk.bake_yaml()
    if DATA_ZIELE.is_file() and DATA_ZIELE.read_text(encoding="utf-8") == neu:
        return False
    DATA_ZIELE.parent.mkdir(parents=True, exist_ok=True)
    DATA_ZIELE.write_text(neu, encoding="utf-8")
    return True


# ------------------------------------------------------------------ #
#  IW6: Generator-Kontrakt (affiliate_marketer)
# ------------------------------------------------------------------ #
def pruefe_iw6(reg: dict) -> list[dict]:
    """Beweist, dass die CTA-Vorlagen der Engine konform sind.

    Ohne diese Prüfung wäre die Wache ein Eimer unter einem laufenden Hahn:
    Neue Artikel entstünden weiter mit generischen Ankern und Pillar-
    Fallbacks. Geprüft wird pro Route: route_for(Probe) == Route und die
    drei CTA-Bauer liefern Route + produkt-exakten + ehrlichen Anker.
    """
    pseudo = {"slug": "(Generator)", "rel": "scripts/affiliate_marketer.py",
              "title": "", "tags": [], "pillar": "", "body": "", "section": ""}
    funde: list[dict] = []
    try:
        import affiliate_marketer as am
    except Exception as exc:  # noqa: BLE001
        return [befund("IW6", pseudo, 0, "", "", "",
                       f"affiliate_marketer.py nicht ladbar: {exc}", owner="human")]

    for route, z in vk.ZIELE.items():
        probe = f"{z.produkt} – {z.anker_fuer('intext')} im Test"
        if route == "allgemein":
            probe = "Budget und Haushaltsbuch im Alltag, ganz ohne Fachprodukt"
        try:
            got = am.route_for(probe, "", z.produkt)
        except Exception as exc:  # noqa: BLE001
            funde.append(befund("IW6", pseudo, 0, route, "", "",
                                f"route_for() wirft: {exc}", owner="human"))
            continue
        if got != route and route != "allgemein":
            funde.append(befund(
                "IW6", pseudo, 0, route, "", "",
                f"Generator route_for() liefert /go/{got}/ für ein "
                f"{z.produkt}-Thema (erwartet /go/{route}/)", owner="human"))
        for bau, slot in ((am.build_top_cta, "top"), (am.mid_cta, "mid"),
                          (am.end_cta, "end")):
            try:
                cta = bau("", reg, probe) if route == "allgemein" else \
                    bau("", reg, f"{probe} [Test](/go/{route}/)")
            except Exception as exc:  # noqa: BLE001
                funde.append(befund("IW6", pseudo, 0, route, "", slot,
                                    f"{bau.__name__} wirft: {exc}", owner="human"))
                continue
            m = MD_GO_LINK.search(cta) or re.search(
                r"\[(?P<anchor>[^\]]*)\]\((?P<url>/go/[\w-]+/)\)", cta)
            if not m:
                funde.append(befund("IW6", pseudo, 0, route, "", slot,
                                    f"{bau.__name__} erzeugt keinen Gateway-Link",
                                    owner="human"))
                continue
            href_key = m.group("url").strip("/").split("/")[-1]
            anchor = m.group("anchor").strip("*").strip()
            if href_key != route:
                funde.append(befund(
                    "IW6", pseudo, 0, href_key, anchor, slot,
                    f"{bau.__name__} liefert /go/{href_key}/ für ein "
                    f"{z.produkt}-Thema", owner="human"))
            if vk.anker_ist_generisch(anchor):
                funde.append(befund(
                    "IW6", pseudo, 0, href_key, anchor, slot,
                    f"{bau.__name__} erzeugt einen generischen Anker "
                    "(„Angebote vergleichen“) – Quelle der Fehlrouten vom 19.09.",
                    owner="human"))
            ok, grund = z.ehrlich(anchor)
            if not ok:
                funde.append(befund("IW6", pseudo, 0, href_key, anchor, slot,
                                    f"{bau.__name__} erzeugt unehrlichen Anker: {grund}",
                                    owner="human"))
    return funde


# ------------------------------------------------------------------ #
#  IW9: Templates (layouts/)
# ------------------------------------------------------------------ #
def pruefe_iw9(reg: dict) -> list[dict]:
    funde: list[dict] = []
    layout_dir = ROOT / "layouts"
    for pfad in sorted(layout_dir.rglob("*.html")):
        if "_markup" in str(pfad):
            continue                      # Render-Hook: IW0 prüft die Namen
        txt = pfad.read_text(encoding="utf-8")
        if "/go/" not in txt:
            continue
        rel = str(pfad.relative_to(ROOT))
        # Fund zeigt auf Datei + echte Zeile des Templates
        pseudo = {"slug": "(Template)", "rel": rel, "title": "", "tags": [],
                  "pillar": "", "body": "", "section": ""}
        for m in re.finditer(r'href="(/go/([\w-]+)/?)"[^>]*>([^<]{0,80})<', txt):
            key, label = m.group(2), m.group(3).strip()
            z = vk.ziel(key)
            zeile = txt.count("\n", 0, m.start()) + 1
            if key not in reg or z is None:
                funde.append(befund("IW9", pseudo, zeile, key, label, "template",
                                    "Template-CTA auf unbekannte Route",
                                    owner="human"))
                continue
            label_routen = vk.anker_routes(label) if label else []
            if label_routen and label_routen[0] != key:
                verspricht = vk.ziel(label_routen[0])
                funde.append(befund(
                    "IW9", pseudo, zeile, key, label, "template",
                    "Template-CTA verspricht "
                    f"{verspricht.produkt if verspricht else label_routen[0]}, "
                    f"führt aber zu {z.produkt}", owner="human"))
            elif label and z.ehrlich(label)[0] is False:
                funde.append(befund("IW9", pseudo, zeile, key, label, "template",
                                    z.ehrlich(label)[1], owner="human"))
        # dict-basierte Pillar-CTAs: "url" "/go/x/" "text" "…"
        for m in re.finditer(r'"url"\s+"(/go/([\w-]+)/?)"\s+"text"\s+"([^"]+)"', txt):
            key, label = m.group(2), m.group(3)
            z = vk.ziel(key)
            zeile = txt.count("\n", 0, m.start()) + 1
            if not z:
                continue
            ok, grund = z.ehrlich(label)
            if not ok:
                funde.append(befund("IW9", pseudo, zeile, key, label, "template",
                                    grund, owner="human"))
            elif vk.anker_ist_generisch(label):
                funde.append(befund("IW9", pseudo, zeile, key, label, "template",
                                    "CTA nennt kein Angebot", owner="human"))
    return funde


# ------------------------------------------------------------------ #
#  Lauf
# ------------------------------------------------------------------ #
def run(root: Path | None = None, do_heal: bool | None = None) -> dict:
    root = root or ROOT
    do_heal = (DO_FIX and not DRY_RUN) if do_heal is None else do_heal
    reg = load_registry(root)
    errors: list[str] = []
    if not reg:
        errors.append("scripts/check24_links.yaml lieferte keine Routen "
                      "(Werkzeugfehler – fail-closed)")

    arts = load_articles()
    titel_pfad = interne_ziele(arts)

    funde: list[dict] = []
    if not BAKE_ONLY:
        funde += pruefe_iw0(reg)
        for art in arts:
            funde += pruefe_artikel(art, reg, titel_pfad)
        funde += pruefe_iw5(reg)
        funde += pruefe_iw6(reg)
        funde += pruefe_iw9(reg)

    geheilt: list[str] = []
    if do_heal:
        if BAKE_ONLY or any(f["code"] == "IW0" and f["owner"] == "auto" for f in funde):
            if backe_daten():
                geheilt.append("data/affiliate_ziele.yaml aus dem Kontrakt gebacken")
            elif BAKE_ONLY:
                print("ℹ data/affiliate_ziele.yaml ist auf Kontrakt-Stand – nichts zu backen.")
        if not NO_GATEWAY:
            n = backe_gateways(reg)
            if n:
                geheilt.append(f"{n} Gateway-Seiten mit ehrlichen Zielnamen gebacken")
            elif BAKE_ONLY:
                print(f"ℹ {len(reg)} Gateway-Seiten sind auf Kontrakt-Stand – nichts zu backen.")
        for art in arts:
            art_funde = [f for f in funde if f["slug"] == art["slug"]
                         and f["owner"] == "auto" and f.get("blocking")]
            if not art_funde:
                continue
            neuer_body, aktionen = heile_artikel(art, art_funde, reg, titel_pfad)
            if aktionen:
                geheilt.extend(f"{art['slug']}: {a}" for a in aktionen)
            if neuer_body != art["body"]:
                if not DRY_RUN:
                    raw = art.get("text", "")
                    anfang = body_anfang(raw)
                    if raw[anfang:] == (art["body"] or ""):
                        neu_text = raw[:anfang] + neuer_body   # byte-exakt
                    else:
                        # Naht unerwartet – Sicherheit vor Schönheit:
                        # kanonischer Weg über die post_utils-Naht.
                        neu_text = join_article(art["fm"], neuer_body,
                                                art["prefix"])
                    art["path"].write_text(neu_text, encoding="utf-8")
                    art["text"] = neu_text
                art["body"] = neuer_body

    # Nach der Heilung: Restfund (Beweis, dass die Heilung trägt)
    rest: list[dict] = []
    if do_heal and not DRY_RUN and not BAKE_ONLY:
        arts2 = load_articles()
        titel_pfad2 = interne_ziele(arts2)
        rest += pruefe_iw0(reg)
        for art in arts2:
            rest += pruefe_artikel(art, reg, titel_pfad2)
        rest += pruefe_iw5(reg)
        rest += pruefe_iw6(reg)
        rest += pruefe_iw9(reg)
        funde = rest

    offen = funde
    blocking = [f for f in funde if f.get("blocking")]
    if errors:
        code = EXIT_TOOL
    elif blocking:
        code = EXIT_CONTENT
    else:
        code = EXIT_OK

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "checked_articles": len(arts),
        "checked_links": sum(1 for a in arts for _ in MD_GO_LINK.finditer(a["body"] or "")),
        "registry_routes": len(reg),
        "contract_routes": len(vk.ZIELE),
        "nie_paare": len(vk.NIE_PAARE),
        "findings": offen,
        "blocking_count": len(blocking),
        "healed": geheilt,
        "healed_count": len(geheilt),
        "errors": errors,
        "exit_code": code,
        "modus": "DRY-RUN" if DRY_RUN else ("FIX" if DO_FIX else "REPORT"),
    }


# ------------------------------------------------------------------ #
#  Report / Zustand / Historie
# ------------------------------------------------------------------ #
def write_report(res: dict) -> str:
    funde = res["findings"]
    namen = {
        "IW0": "Kontrakt & Register", "IW1": "Anker ↔ Route",
        "IW2": "Primär-CTA ↔ Artikelthema", "IW3": "Ehrlicher Zielname",
        "IW4": "Nie-Paare", "IW5": "Gateway-Seiten", "IW6": "Generator",
        "IW7": "Entführte Lesetipps", "IW8": "Generische Anker",
        "IW9": "Templates/Shortcodes",
    }
    L = [
        "# 🎯 AFFILIATE-INTENT-REPORT (affiliate_intent_guard.py)", "",
        f"**Stand:** {res['generated_at']} · **Modus:** {res['modus']} · "
        f"**Status:** "
        + ("🟢 Jeder Link liefert das versprochene Angebot"
           if not any(f.get("blocking") for f in funde)
           else f"🔴 {sum(1 for f in funde if f.get('blocking'))} harte Intent-Funde offen"),
        "",
        f"**Geprüfte Artikel:** {res['checked_articles']} · "
        f"**Gateway-Links:** {res['checked_links']} · "
        f"**Routen im Register:** {res['registry_routes']} · "
        f"**Nie-Paare:** {res['nie_paare']} · "
        f"**Geheilt:** {res['healed_count']}", "",
    ]
    if res["errors"]:
        L += ["## 🟠 Werkzeugfehler (fail-closed)", ""]
        L += [f"- {e}" for e in res["errors"]] + [""]
    if res["healed"]:
        L += [f"## 🩹 Geheilt ({res['healed_count']})", ""]
        L += [f"- {h}" for h in res["healed"][:80]] + [""]
    hart = [f for f in funde if f.get("blocking")]
    hinweise = [f for f in funde if not f.get("blocking")]

    def zeile(f: dict) -> str:
        """Eine Fund-Zeile. Artikel-Funde zeigen DATEIzeile, Slot, Route und
        Anker (Menschen öffnen die Datei); Werkzeugs-/Template-Funde zeigen
        nur Pfad und Problem – Slot/Anker wären dort Rauschen."""
        owner = ("ℹ️ Hinweis" if not f.get("blocking")
                 else "🧑 Mensch" if f["owner"] == "human" else "🤖 heilbar")
        if f["line_datei"] > 0:
            ort = f"`{f['path']}`:{f['line_datei']} [{f['slot']}] /go/{f['route']}/"
            if f["anchor"]:
                ort += f" «{f['anchor'][:60]}»"
            return f"- {ort} – {f['problem']} ({owner})"
        return f"- `{f['path']}` – {f['problem']} ({owner})"

    def block(titel: str, liste: list[dict]) -> None:
        if not liste:
            return
        L.extend([titel, ""])
        gruppen: dict[str, list[dict]] = {}
        for f in liste:
            gruppen.setdefault(f["code"], []).append(f)
        for code in sorted(gruppen):
            teil = gruppen[code]
            L.extend([f"### {code} – {namen.get(code, code)} ({len(teil)})", ""])
            for f in teil[:40]:
                L.append(zeile(f))
                if f.get("heilung"):
                    L.append(f"  - Heilung: {f['heilung']}")
            if len(teil) > 40:
                L.append(f"- … {len(teil) - 40} weitere")
            L.append("")

    if funde:
        block(f"## 🔴 Harte Funde ({len(hart)}) – Veröffentlichung gestoppt", hart)
        block("## 🟡 Hinweise – nicht blockierend (ehrliches Cross-Selling, "
              "redaktioneller Prüfpunkt)", hinweise)
    else:
        L += ["🎉 Jeder Affiliate-Link im Bestand liefert das Angebot, das "
              "Anker, CTA-Satz und Artikelthema versprechen. Abweichungen "
              "(C24 Bank, Pauschalreise) sind im Anker benannt.", ""]
    L += ["## Vertrag", "",
          "| Prüfung | Garantie |", "|:--|:--|",
          "| IW1 | Nennt der Anker ein Produkt, liefert die Route genau dieses Produkt. |",
          "| IW2 | Top-/Mid-/End-CTA dient dem Artikelthema (oder ist durch den CTA-Kontext gedeckt). |",
          "| IW3 | Routen mit Abweichung (C24 Bank, Pauschalreise statt Flug) benennen das echte Ziel. |",
          "| IW4 | Eingefrorene Nie-Paare (z. B. Kfz-Artikel → Haftpflicht) sind unmöglich. |",
          "| IW5 | Jede /go/-Seite nennt das echte Ziel, ist noindex und leitet exakt auf die Register-URL. |",
          "| IW6 | Die Engine-Vorlagen erzeugen für jede Route konforme CTAs (Quelle mitbewacht). |",
          "| IW7 | Interne Lesetipps werden nicht zu Affiliate-Links entführt. |",
          "| IW8 | Kein Anker bleibt generisch – jeder nennt das Angebot. |",
          "| IW9 | Template- und Shortcode-CTAs gelten derselbe Kontrakt. |", "",
          "---",
          "_Wahrheit: `scripts/affiliate_intent_contract.py` (Angebote, Namen, "
          "ehrliche Anker, Nie-Paare). Selbsttest: "
          "`python3 scripts/affiliate_intent_guard.py --selftest`. "
          "Heilung: `--fix` (deterministisch, idempotent, keine KI)._"]
    text = "\n".join(L) + "\n"
    if not DRY_RUN:
        REPORT.write_text(text, encoding="utf-8")
    return text


def write_state(res: dict) -> None:
    if DRY_RUN or AS_JSON:
        return
    payload = {
        "generated_at": res["generated_at"],
        "exit_code": res["exit_code"],
        "modus": res["modus"],
        "checked_articles": res["checked_articles"],
        "checked_links": res["checked_links"],
        "healed_count": res["healed_count"],
        "healed": res["healed"][:50],
        "findings": [
            {k: f[k] for k in ("code", "slug", "line", "route", "slot",
                               "owner", "problem")}
            for f in res["findings"][:100]
        ],
        "errors": res["errors"],
    }
    STATE.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                     encoding="utf-8")
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "date": date.today().isoformat(),
            "generated_at": res["generated_at"],
            "modus": res["modus"],
            "funde": len(res["findings"]),
            "geheilt": res["healed_count"],
            "exit_code": res["exit_code"],
        }, ensure_ascii=False) + "\n")


# ------------------------------------------------------------------ #
#  Selbsttest (Sabotage-Schutz, eingefrorene Vorfälle vom 19.09.2026)
# ------------------------------------------------------------------ #
FIXTURES = {
    "kfz": ("---\ntitle: \"Kfz-Versicherung Vergleich 2026: Bis zu 800 € sparen\"\n"
            "tags: [\"Kfz Versicherung\"]\npillar: \"versicherungen\"\ndraft: false\n---\n\n"
            "Intro zum Kfz-Versicherungsvergleich.\n\n"
            "💡 **Schnell-Tipp von FranksFinanzcheck:** Starte jetzt den kostenlosen "
            "Vergleich: [**Kfz-Versicherung vergleichen**](/go/haftpflicht/)  \n"
            "_(Dieser Artikel enthält Affiliate-Links (Werbung).)_\n\n"
            "## Warum wechseln?\n\nText.\n\n---\n\n"
            "👉 **Jetzt vergleichen und sparen:** [**→ Jetzt Angebote vergleichen**](/go/kfz-versicherung/)\n"),
    "girokonto": ("---\ntitle: \"Kostenloses Girokonto: So findest du ein Konto ohne Gebühren\"\n"
                  "tags: [\"Girokonto\"]\npillar: \"konto-karten\"\ndraft: false\n---\n\n"
                  "Intro zum Girokonto.\n\n"
                  "💡 **Schnell-Tipp von FranksFinanzcheck:** Vergleiche jetzt "
                  "Girokonten: [**Kostenlos vergleichen**](/go/kredit/)  \n"
                  "_(Dieser Artikel enthält Affiliate-Links (Werbung).)_\n"),
    "mietwagen": ("---\ntitle: \"Mietwagen ohne Kautionsfallen: So sparst du im Urlaub\"\n"
                  "tags: [\"Mietwagen\"]\npillar: \"mietwagen\"\ndraft: false\n---\n\n"
                  "Intro.\n\n💡 **Schnell-Tipp von FranksFinanzcheck:** Sichere dir "
                  "einen Preisvergleich: [**Jetzt Mietwagen vergleichen**](/go/kfz-versicherung/)  \n"
                  "_(Werbung)_\n\n## Kasko\n\nText.\n\n---\n\n"
                  "👉 **Jetzt vergleichen und sparen:** [**→ Mietwagen mit Vollkasko "
                  "ohne Selbstbeteiligung vergleichen**](/go/kfz-versicherung/)\n"),
    "kreditkarte": ("---\ntitle: \"Kreditkarte vergleichen: Kostenlos und sicher zahlen\"\n"
                    "tags: [\"Kreditkarte\"]\npillar: \"konto-karten\"\ndraft: false\n---\n\n"
                    "Intro.\n\n💡 **Schnell-Tipp von FranksFinanzcheck:** Die besten "
                    "Tarife findest du über unseren Partner-Vergleich: "
                    "[**Tarifrechner starten**](/go/reisekrankenversicherung/)\n"),
    "wohngebaeude": ("---\ntitle: \"Wohngebäudeversicherung Vergleich: Worauf du achten musst\"\n"
                     "tags: [\"Wohngebäudeversicherung\"]\npillar: \"versicherungen\"\n---\n\n"
                     "Intro.\n\n💡 **Schnell-Tipp von FranksFinanzcheck:** Schütze dein "
                     "Hab und Gut: [**Versicherungsvergleich starten**](/go/hausrat/)  \n"
                     "_(Werbung)_\n\n---\n\n👉 **Jetzt vergleichen und sparen:** "
                     "[**→ Jetzt Angebote vergleichen**](/go/haftpflicht/)\n"),
    "fluege": ("---\ntitle: \"Flugtickets günstig buchen: Strategien für deine Reise\"\n"
               "tags: [\"Flugvergleich\"]\npillar: \"mietwagen\"\ndraft: true\n---\n\n"
               "Intro.\n\n💡 **Schnell-Tipp von FranksFinanzcheck:** Die besten Tarife "
               "findest du über unseren Partner-Vergleich: [**Kostenlos vergleichen**](/go/mietwagen/)  \n"
               "_(Werbung)_\n\n---\n\n👉 **Jetzt vergleichen und sparen:** "
               "[**→ Jetzt Angebote vergleichen**](/go/mietwagen/)\n"),
    "tagesgeld": ("---\ntitle: \"Tagesgeld-Zinsen 2026: Die besten Zinssätze im Vergleich\"\n"
                  "tags: [\"Tagesgeld\"]\npillar: \"konto-karten\"\n---\n\n"
                  "Intro.\n\n💡 **Schnell-Tipp von FranksFinanzcheck:** Sichere dir die "
                  "Spitzenzinsen: [**Jetzt Tagesgeld vergleichen**](/go/tagesgeld/)  \n"
                  "_(Werbung)_\n\nStarte mit dem [Tagesgeldvergleich](/go/tagesgeld/) "
                  "und filtere nach Zinssatz.\n"),
    "gas_auf_strom": ("---\ntitle: \"Gasrechnung senken: Spätsommer-Check spart hunderte Euro\"\n"
                      "tags: [\"Gasrechnung senken\"]\npillar: \"strom-sparen\"\n---\n\n"
                      "Intro zur Gasrechnung.\n\n💡 **Schnell-Tipp von FranksFinanzcheck:** "
                      "Die besten Tarife findest du über unseren Partner-Vergleich: "
                      "[**Tarifrechner starten**](/go/strom/)  \n_(Werbung)_\n\n"
                      "Prüfe, wie viel du bei deinem [Gasvergleich](/go/strom/) sparst.\n"),
    "lesetipp": ("---\ntitle: \"Gasrechnung senken: Deine Strategie für den Winter 2026\"\n"
                 "tags: [\"Gas\"]\npillar: \"strom-sparen\"\n---\n\n"
                 "Intro zur Gasrechnung und zum Gasanbieter-Wechsel.\n\n"
                 "**Weiterlesen:** [Ratgeber Strom Sparen](/go/gas/)\n"
                 "**Lesetipp:** [Standby Kosten reduzieren: So entlarvst du Stromfresser]"
                 "(../../posts/2026-09-11-standby-kosten-reduzieren-so-entlarvst-du-stromfresser/)\n\n"
                 "**Lesetipp:** [Standby Kosten reduzieren: So entlarvst du Stromfresser](/go/gas/)\n\n"
                 "**Weiterlesen:** [Ratgeber Strom Sparen](../../pillar/strom-sparen/)\n"),
    "clean": ("---\ntitle: \"Strom sparen im Haushalt: Die besten Tipps für den Herbst\"\n"
              "tags: [\"Strom sparen\"]\npillar: \"strom-sparen\"\n---\n\n"
              "Intro zum Stromsparen.\n\n💡 **Schnell-Tipp von FranksFinanzcheck:** "
              "Die besten Tarife findest du über unseren Partner-Vergleich: "
              "[**Jetzt Stromtarife vergleichen**](/go/strom/)  \n_(Werbung)_\n\n"
              "---\n\n👉 **Jetzt vergleichen und sparen:** [**→ Jetzt Stromtarife "
              "vergleichen**](/go/strom/)\n"),
}


def run_selftest() -> list[str]:
    """Eingefrorene Vorfälle: Erkennung UND Heilung müssen stimmen.

    Ohne diesen Beweis wäre die Wache selbst das Risiko (Vorfall 01.09.2026:
    ein Detektor, der nur „anblickt“, machte sich still blind). Exit 2.
    """
    fehler: list[str] = []

    def muss(bedingung: bool, meldung: str) -> None:
        if not bedingung:
            fehler.append(meldung)

    reg = load_registry()
    muss(bool(reg), "Register konnte nicht geladen werden (Selftest sinnlos)")
    arts = []
    for name, text in FIXTURES.items():
        prefix, fm, body = split_article(text)
        arts.append({
            "slug": name, "path": Path(f"/tmp/{name}/index.md"), "rel": f"fixture:{name}",
            "prefix": prefix, "fm": fm, "body": body, "text": text,
            "title": fm_value(fm, "title"),
            "tags": fm_list(fm, "tags"), "pillar": fm_value(fm, "pillar"),
            "draft": False,
            "section": "posts",
        })
    by_name = {a["slug"]: a for a in arts}
    titel_pfad = {
        vk.norm("Standby Kosten reduzieren: So entlarvst du Stromfresser"):
            "../../posts/2026-09-11-standby-kosten-reduzieren-so-entlarvst-du-stromfresser/",
    }

    def art_neu(name: str) -> dict:
        """Fixture frisch aus FIXTURES bauen (Selftest-Abschnitte dürfen sich
        nicht gegenseitig durch geheilte Bodys täuschen)."""
        prefix, fm, body = split_article(FIXTURES[name])
        return {
            "slug": name, "path": Path(f"/tmp/{name}/index.md"),
            "rel": f"fixture:{name}", "prefix": prefix, "fm": fm, "body": body,
            "text": FIXTURES[name], "title": fm_value(fm, "title"),
            "tags": fm_list(fm, "tags"), "pillar": fm_value(fm, "pillar"),
            "draft": False, "section": "posts",
        }

    def funde_von(name: str) -> list[dict]:
        return pruefe_artikel(by_name[name], reg, titel_pfad)

    def codes(name: str) -> set[str]:
        return {f["code"] for f in funde_von(name)}

    # 1) Erkennung der sieben Live-Funde vom 19.09.2026
    muss("IW1" in codes("kfz"), "Kfz-CTA → /go/haftpflicht/ muss IW1 auslösen")
    muss(any(f["code"] == "IW4" or f["ziel_route"] == "kfz-versicherung"
             for f in funde_von("kfz")),
         "Kfz-Fund: Heilziel muss /go/kfz-versicherung/ sein")
    muss("IW4" in codes("girokonto") or "IW2" in codes("girokonto"),
         "Girokonto-CTA → /go/kredit/ muss als Fehllink erkannt werden")
    muss("IW1" in codes("mietwagen"),
         "Mietwagen-Anker → /go/kfz-versicherung/ muss IW1 auslösen")
    muss("IW4" in codes("kreditkarte") or "IW2" in codes("kreditkarte"),
         "Kreditkarten-CTA → /go/reisekrankenversicherung/ muss erkannt werden")
    muss("IW4" in codes("wohngebaeude"),
         "Wohngebäude-CTA → /go/hausrat/ muss das Nie-Paar auslösen")
    muss("IW4" in codes("fluege"),
         "Flug-CTA → /go/mietwagen/ muss das Nie-Paar auslösen")
    muss("IW3" in codes("tagesgeld"),
         "„Jetzt Tagesgeld vergleichen“ → C24 Bank muss IW3 auslösen")
    muss("IW1" in codes("gas_auf_strom"),
         "„Gasvergleich“ → /go/strom/ muss IW1 auslösen")
    muss("IW7" in codes("lesetipp"),
         "entführter Lesetipp → /go/gas/ muss IW7 auslösen")
    muss(not codes("clean"), f"sauberer Artikel darf keine Funde haben: {codes('clean')}")

    # 2) Heilung: Route + Anker stimmen danach, Struktur bleibt erhalten
    def heile(name: str) -> str:
        art = by_name[name]
        neu, _ = heile_artikel(art, funde_von(name), reg, titel_pfad)
        return neu

    kfz_body = heile("kfz")
    muss("/go/haftpflicht/" not in kfz_body, "Kfz-Heilung: /go/haftpflicht/ muss weg sein")
    muss(kfz_body.count("/go/kfz-versicherung/") == 2,
         "Kfz-Heilung: beide CTAs müssen auf /go/kfz-versicherung/ stehen")
    muss("Kfz-Versicherung vergleichen" in kfz_body,
         "Kfz-Heilung: Anker muss das Produkt nennen")
    muss("**Schnell-Tipp von FranksFinanzcheck:**" in kfz_body,
         "Kfz-Heilung: Marker/Struktur muss erhalten bleiben")
    muss("_(Dieser Artikel enthält Affiliate-Links (Werbung).)_" in kfz_body,
         "Kfz-Heilung: Disclaimer darf nicht verloren gehen")

    miet_body = heile("mietwagen")
    muss("/go/kfz-versicherung/" not in miet_body,
         "Mietwagen-Heilung: /go/kfz-versicherung/ muss weg sein")
    muss("Vollkasko" in miet_body,
         "Mietwagen-Heilung: redaktioneller Anker-Inhalt darf nicht verloren gehen")

    tg_body = heile("tagesgeld")
    muss("Jetzt C24 Bank Tagesgeld ansehen" in tg_body,
         f"Tagesgeld-Heilung: Top-CTA muss C24 ehrlich benennen: {tg_body}")
    muss("/go/tagesgeld/" in tg_body, "Tagesgeld-Heilung: Route bleibt erhalten")
    # In-Text „Tagesgeldvergleich“: Der Anhang wäre kaputtes Deutsch UND das
    # Wort „Vergleich“ bliebe ein Marktversprechen, das es nicht gibt.
    # Deshalb: keine Automatik, sondern Menschen-Fund mit Vorschlag (Ehrlichkeit
    # schlägt Halbautomatik).
    tg_funde = [f for f in funde_von("tagesgeld")
                if f["code"] == "IW3" and f["slot"] != "top"]
    muss(len(tg_funde) == 1 and tg_funde[0]["owner"] == "human",
         f"In-Text-Tagesgeldvergleich muss Menschen-Fund sein: {tg_funde}")
    muss("C24" in tg_funde[0]["heilung"],
         "Menschen-Fund braucht einen konkreten C24-Vorschlag")
    muss("[Tagesgeldvergleich](/go/tagesgeld/)" in tg_body,
         "In-Text-Anker darf NICHT automatisch umgebaut werden")

    flug_body = heile("fluege")
    muss("/go/mietwagen/" not in flug_body, "Flug-Heilung: /go/mietwagen/ muss weg sein")
    muss("pauschalreise" in flug_body.lower(),
         "Flug-Heilung: ehrliche Benennung als Pauschalreise fehlt")
    muss("/go/fluege/" in flug_body, "Flug-Heilung: Route /go/fluege/ muss gesetzt sein")

    wg_body = heile("wohngebaeude")
    muss("/go/hausrat/" not in wg_body and "/go/haftpflicht/" not in wg_body,
         "Wohngebäude-Heilung: fremde Policen müssen weg sein")
    muss("/go/wohngebaeudeversicherung/" in wg_body,
         "Wohngebäude-Heilung: eigene Route muss gesetzt sein")

    gas_body = heile("gas_auf_strom")
    muss("[Gasvergleich](/go/gas/)" in gas_body,
         "Gas-Heilung: Anker „Gasvergleich“ muss auf /go/gas/ zeigen")

    lese_body = heile("lesetipp")
    muss("/go/gas/" not in lese_body, "Lesetipp-Heilung: kein Gateway im Weiterlesen-Block")
    muss(lese_body.count("Standby Kosten reduzieren") == 1,
         "Lesetipp-Heilung: entführte Doppelzeile muss wegfallen")
    muss("../../pillar/strom-sparen/" in lese_body,
         "Lesetipp-Heilung: korrekter Pillar-Lesetipp bleibt stehen")

    # 3) Idempotenz: zweiter Lauf findet/heilt nichts mehr
    for name in FIXTURES:
        art = by_name[name]
        neu1, akt1 = heile_artikel(art, funde_von(name), reg, titel_pfad)
        art["body"] = neu1
        f2 = pruefe_artikel(art, reg, titel_pfad)
        neu2, akt2 = heile_artikel(art, [f for f in f2 if f["owner"] == "auto"],
                                   reg, titel_pfad)
        muss(neu2 == neu1, f"{name}: Heilung ist nicht idempotent")
        auto_rest = [f for f in pruefe_artikel(art, reg, titel_pfad)
                     if f.get("blocking") and f["owner"] == "auto"]
        muss(not auto_rest,
             f"{name}: nach Heilung bleiben auto-Funde: "
             f"{[(f['code'], f['anchor'][:30], f['problem'][:60]) for f in auto_rest]}")

    # 3b) IW4-Transparenz: ehrlich benanntes Zweitangebot ist kein harter Fund
    # (frische Fixture – Abschnitt 3 hat by_name bereits geheilt/überschrieben)
    wg_art = art_neu("wohngebaeude")
    wg_funde = pruefe_artikel(wg_art, reg, titel_pfad)
    hart_wg = [f for f in wg_funde if f["code"] == "IW4" and f.get("blocking")]
    muss(hart_wg, f"generische Hausrat-CTAs im Wohngebäude-Artikel müssen hart sein: {wg_funde}")
    haus = {
        "slug": "haus", "path": Path("/tmp/haus/index.md"), "rel": "fixture:haus",
        "prefix": "", "fm": "", "text": "", "tags": [], "pillar": "",
        "draft": False, "section": "posts",
        "title": "Dein Haus sicher schützen: Das neue Vorsorge-Update 2026",
        "body": ("\n💡 **Schnell-Tipp von FranksFinanzcheck:** Prüfe die "
                 "Elementardeckung: [**Jetzt Hausratversicherung vergleichen**]"
                 "(/go/hausrat/)  \n_(Werbung)_\n"),
    }
    haus_funde = pruefe_artikel(haus, reg, titel_pfad)
    muss(all(not f.get("blocking") for f in haus_funde),
         f"ehrlich benanntes Zweitangebot darf nicht blockieren: "
         f"{[(f['code'], f['severity']) for f in haus_funde]}")
    neu_haus, _ = heile_artikel(haus, haus_funde, reg, titel_pfad)
    muss(neu_haus == haus["body"],
         "ehrlich benanntes Zweitangebot darf nicht umgeschrieben werden")

    # 3c) Ehrlichkeits-Heilung: bleibt der Anhang generisch, gewinnt der
    #     produkt-exakte Kontrakt-Anker (ein Fund, ein Heilweg).
    giro = art_neu("girokonto")
    giro["body"] = ("\n> 💶 **Spar-Tipp von FranksFinanzcheck:** Wer heute noch "
                    "Kontogebühren zahlt, verbrennt Geld. [**Sichere dir hier "
                    "dein kostenloses Konto**](/go/girokonto/)\n")
    gf = [f for f in pruefe_artikel(giro, reg, titel_pfad) if f["code"] == "IW3"]
    muss(len(gf) == 1 and gf[0]["owner"] == "auto",
         f"Girokonto-In-Text-CTA muss automatisch heilbar sein: {gf}")
    muss("Girokonto" in gf[0]["ziel_anker"],
         f"Ziel-Anker muss das Produkt nennen: {gf[0]['ziel_anker']}")
    gneu, _ = heile_artikel(giro, gf, reg, titel_pfad)
    muss("Wer heute noch Kontogebühren zahlt, verbrennt Geld." in gneu,
         f"redaktioneller Satz muss bleiben: {gneu}")
    muss("kostenloses Konto**" not in gneu and "C24" in gneu,
         f"Anker muss produkt-exakt und ehrlich sein: {gneu}")
    muss(not [f for f in pruefe_artikel(
        {**giro, "body": gneu}, reg, titel_pfad) if f.get("blocking")],
         "nach der Heilung darf kein harter Fund bleiben")

    # 3d) Satz-Ehrlichkeit: Anker nennt C24, der SATZ verspricht aber einen
    #     Marktvergleich → Primär-CTA wird neu gesetzt, Prosa bleibt Menschen-Fund.
    satz_art = art_neu("girokonto")
    satz_art["body"] = (
        "\n💡 **Schnell-Tipp von FranksFinanzcheck:** Vergleiche jetzt führende "
        "gebührenfreie Girokonten: [**Kostenloses C24 Girokonto eröffnen**]"
        "(/go/girokonto/)  \n_(Werbung)_\n\n"
        "Sieh dir unseren detaillierten Vergleich zur [Gebührenfreien "
        "Girokonto-Auswahl](/go/girokonto/) an.\n")
    sf = pruefe_artikel(satz_art, reg, titel_pfad)
    top = [f for f in sf if f["slot"] == "top"]
    muss(len(top) == 1 and top[0]["code"] == "IW3" and top[0]["owner"] == "auto",
         f"Vergleichs-Satz zur C24-Route muss IW3 (auto) sein: {sf}")
    menschen = [f for f in sf if f["owner"] == "human"]
    muss(menschen and "vergleich" in menschen[0]["problem"].lower(),
         f"Prosa-Vergleich muss Menschen-Fund sein: {sf}")
    satz_neu, _ = heile_artikel(satz_art, [f for f in sf if f["owner"] == "auto"],
                                reg, titel_pfad)
    muss("Vergleiche jetzt führende gebührenfreie Girokonten" not in satz_neu,
         f"unehrlicher Satz muss verschwinden: {satz_neu}")
    muss("C24 Bank" in satz_neu.split("\n")[1],
         f"neuer Top-CTA-Satz muss C24 nennen: {satz_neu.split(chr(10))[1]}")
    muss("detaillierten Vergleich zur [Gebührenfreien Girokonto-Auswahl]" in satz_neu,
         f"Prosa darf nicht automatisch umgeschrieben werden: {satz_neu}")
    rest_satz = [f for f in pruefe_artikel({**satz_art, "body": satz_neu}, reg, titel_pfad)
                 if f.get("blocking") and f["owner"] == "auto"]
    muss(not rest_satz, f"Satz-Heilung ist nicht idempotent: {rest_satz}")

    # 3d2) Eigener (nicht kanonischer) Marker mit Vergleichs-Versprechen:
    #      Menschen-Fund – kanonische Haus-Marker bleiben dagegen Vertrag.
    marker_art = art_neu("konto-karten") if "konto-karten" in FIXTURES else art_neu("girokonto")
    marker_art["title"] = "Konto & Karten: Girokonto, Kreditkarte, Tagesgeld"
    marker_art["rel"] = "content/pillar/konto-karten/index.md"
    marker_art["section"] = "pillar"
    marker_art["body"] = (
        "\n👉 **Jetzt kostenloses Girokonto bei unserem Testsieger "
        "eröffnen:** [**→ Kostenloses Girokonto bei der C24 Bank eröffnen**]"
        "(/go/girokonto/)\n\n"
        "👉 **Jetzt vergleichen und sparen:** [**→ Kostenloses Girokonto bei "
        "der C24 Bank eröffnen**](/go/girokonto/)\n")
    mf = pruefe_artikel(marker_art, reg, titel_pfad)
    muss(len(mf) == 1 and mf[0]["owner"] == "human" and "Marker" in mf[0]["problem"],
         f"eigener Marker mit Testsieger-Versprechen muss Menschen-Fund sein: {mf}")
    muss("kanonisch" not in str(mf), "kanonischer Marker darf kein Fund sein")

    # 3e) Prosa mit Partner-Nennung bleibt unangetastet (Grammatik-Schutz)
    prosa = art_neu("clean")
    prosa["title"] = "Haushaltsbuch führen: App, Excel oder Papier"
    prosa["body"] = ("\n\n\n\nBei der [C24 Bank](/go/girokonto/) sind "
                     "Kategorien und Haushaltsbuch direkt im Girokonto "
                     "integriert – ohne Zusatz-App.\n\n"
                     "👉 **Jetzt vergleichen und sparen:** [**→ Jetzt Angebote "
                     "vergleichen**](/go/girokonto/)\n")
    prosa_funde = pruefe_artikel(prosa, reg, titel_pfad)
    muss(not any(f["code"] == "IW8" and "C24 Bank" == f["anchor"]
                 for f in prosa_funde),
         f"Prosa-Anker mit Partner-Nennung darf kein IW8-Fund sein: {prosa_funde}")
    prosa_neu, _ = heile_artikel(prosa, [f for f in prosa_funde
                                         if f["owner"] == "auto"], reg, titel_pfad)
    muss("Bei der [C24 Bank](/go/girokonto/) sind Kategorien" in prosa_neu,
         f"Prosa-Satz darf nicht umgebaut werden: {prosa_neu}")
    muss(prosa_neu.startswith("\n\n\n\n"),
         "Leerzeilen hinter der Frontmatter müssen byte-exakt bleiben")
    muss("Jetzt Angebote vergleichen" not in prosa_neu
         and "C24" in prosa_neu.split("👉")[1]
         and "Girokonto" in prosa_neu.split("👉")[1],
         f"fetter End-CTA muss den Kontrakt-Anker bekommen: {prosa_neu}")

    # 3f) Themenwelten (Pillar-Hubs) bündeln mehrere Angebote – IW2/IW4
    #     gelten dort nicht, Ehrlichkeit (IW3/IW8) schon.
    hub_art = art_neu("clean")
    hub_art["rel"] = "content/pillar/konto-karten/index.md"
    hub_art["section"] = "pillar"
    hub_art["title"] = "Konto & Karten: Girokonto, Kreditkarte, Tagesgeld"
    hub_art["tags"] = ["Konto", "Karten"]
    hub_art["body"] = (
        "\n👉 **Jetzt kostenloses Girokonto eröffnen:** [**→ Kostenloses "
        "Girokonto bei der C24 Bank eröffnen**](/go/girokonto/)\n\n"
        "👉 **Kreditkarte ohne Jahresgebühr:** [**→ Jetzt Kreditkarten "
        "vergleichen**](/go/kreditkarte/)\n\n"
        "👉 **Zinsen sichern:** [**→ Jetzt C24 Bank Tagesgeld ansehen**]"
        "(/go/tagesgeld/)\n")
    hub_funde = pruefe_artikel(hub_art, reg, titel_pfad)
    muss(not hub_funde,
         f"Pillar-Hub mit ehrlichen Angeboten darf keine Funde haben: "
         f"{[(f['code'], f['anchor'][:40]) for f in hub_funde]}")
    hub_art["body"] = hub_art["body"].replace(
        "→ Jetzt Kreditkarten vergleichen", "→ Jetzt Angebote vergleichen")
    muss(any(f["code"] == "IW8" for f in pruefe_artikel(hub_art, reg, titel_pfad)),
         "generischer Anker muss auch auf Hub-Seiten auffallen")

    # 4) Cross-Selling mit ehrlichem Anker bleibt erlaubt
    cross = {
        "slug": "cross", "path": Path("/tmp/cross/index.md"), "rel": "fixture:cross",
        "prefix": "", "fm": "", "body": "", "text": "", "title": "", "tags": [],
        "pillar": "", "draft": False, "section": "posts",
    }
    cross["title"] = "Mietwagen ohne Kautionsfallen: So sparst du im Urlaub"
    cross["body"] = ("Wer keine Karte hat, braucht ein [gebührenfreies "
                     "Kreditkarten-Konto](/go/kreditkarte/) oder eine "
                     "[Auslandsreise-Absicherung](/go/reisekrankenversicherung/).\n")
    muss(not pruefe_artikel(cross, reg, {}),
         "ehrliches Cross-Selling darf nicht als Fund gelten")

    # 5) Daten-Datei + Gateway-Namen kommen aus dem Kontrakt
    muss("C24 Bank" in vk.bake_yaml(), "bake_yaml: C24-Nennung fehlt")
    muss("Pauschalreisen (Flug im Paket)" in vk.bake_yaml(),
         "bake_yaml: ehrlicher Flug-Name fehlt")
    for fehler_text in vk.selftest():
        fehler.append(f"Kontrakt-Selftest: {fehler_text}")

    # 6) Datenpfad: hugo.Data/site.Data im Layout killt den Build (19.09.2026).
    #    Der Detektor muss die Sabotage SEHEN und die Dokumentation derselben
    #    (Kommentar) schweigen lassen – sonst ist er entweder blind oder ein
    #    Dauer-Alarm, den jemand abschaltet.
    muss(bool(datenbaum_griffe('{{- with site.Data.affiliate_ziele -}}x{{- end -}}')),
         "Datenpfad-Detektor sieht site.Data im Template-Code nicht")
    muss(bool(datenbaum_griffe('{{ $x := hugo.Data.affiliate_ziele }}')),
         "Datenpfad-Detektor sieht hugo.Data im Template-Code nicht")
    muss(not datenbaum_griffe('{{/* site.Data ist verboten – siehe Partial */}}\n'
                              '<!-- hugo.Data ebenso -->'),
         "Datenpfad-Detektor hält einen KOMMENTAR für Code (Dauer-Alarm)")
    muss(bool(datenpfad_fehler('{{ $d := os.ReadFile "data/affiliate_ziele.yaml" '
                               '| transform.Unmarshal }}')),
         "Datenpfad-Prüfer sieht das fehlende YAML-Format nicht (Build-Killer: "
         "Hugo rät TOML)")
    muss(not datenpfad_fehler(
        '{{- if fileExists "data/affiliate_ziele.yaml" -}}'
        '{{- $d = os.ReadFile "data/affiliate_ziele.yaml" '
        '| transform.Unmarshal (dict "format" "yaml") -}}{{- end -}}'),
        "Datenpfad-Prüfer meldet das korrekte Partial als Fehler (Dauer-Alarm)")
    datenpfad = pruefe_datenpfad()
    muss(not datenpfad,
         "Datenpfad der Templates ist nicht build-sauber: "
         + "; ".join(f"{f['path']}:{f['line']} {f['problem'][:70]}"
                     for f in datenpfad[:3]))
    return fehler


# ------------------------------------------------------------------ #
#  main
# ------------------------------------------------------------------ #
def main() -> int:
    if SELFTEST:
        errs = run_selftest()
        if errs:
            print("🛑 INTENT-SELFTEST FEHLGESCHLAGEN – die Wache ist blind "
                  "(fail-closed, es wird nichts geheilt):")
            for e in errs:
                print(f"   - {e}")
            return EXIT_TOOL
        print("✅ INTENT-SELFTEST bestanden: sieben Live-Funde vom 19.09.2026 "
              "(Kfz→Haftpflicht, Girokonto→Kredit, Kreditkarte→Reisekranken, "
              "Mietwagen→Kfz, Wohngebäude→Hausrat, Flüge→Mietwagen, "
              "Tagesgeld→C24 ohne Nennung) + Gas→Strom + entführte Lesetipps "
              "werden erkannt, korrekt geheilt, bleiben idempotent, und "
              "ehrliches Cross-Selling wird nicht angetastet.")
        return EXIT_OK

    res = run()

    if AS_JSON:
        print(json.dumps(res, ensure_ascii=False, indent=1, default=list))
    else:
        print(write_report(res))
        write_state(res)
        if res["exit_code"] == EXIT_TOOL:
            print("🟠 WERKZEUGFEHLER – Intent-Beweis nicht möglich "
                  "(fail-closed: keine Veröffentlichung).", file=sys.stderr)
        elif res["exit_code"] == EXIT_CONTENT:
            hart = [f for f in res["findings"] if f.get("blocking")]
            menschen = sum(1 for f in hart if f["owner"] == "human")
            hinweise = len(res["findings"]) - len(hart)
            print(f"🔴 {len(hart)} harte Intent-Fund(e) offen "
                  f"({menschen} brauchen einen Menschen, {hinweise} Hinweise "
                  "nicht blockierend) – Details im Report.", file=sys.stderr)
        else:
            print("🟢 Intent-Wache: jeder Link liefert das versprochene Angebot.",
                  file=sys.stderr)
    return res["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
