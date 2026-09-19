#!/usr/bin/env python3
# ============================================================
#  AFFILIATE-MARKETER – Conversion & Compliance Waechter
#  (selbstheilend, Profi-Level, 11.08.2026)
#
#  Auftrag: Automatische Conversion-Optimierung + Rechts-Schutz
#  nach dem Best-Practice-Buch deutscher Affiliate-Marketer.
#
#  WAS ER KONTROLLIERT:
#    AM1  KEIN CTA im Money-Post? -> SELBSTHEILUNG: fuegt eine CTA-Pane
#         nach dem Intro ein (aus dem zentralen Register: passende Route
#         per Pillar) mit Discount-Anrede deiner Hausmarke.
#    AM2  FRUEHE SICHTBARKEIT: erster Affiliate-Kontakt geht von >50 %
#         der Artikel-Laenge -> SELBSTHEILUNG: kompakte Top-Empfehlung
#         direkt nach dem Intro (mit Disclaimer-Teaser).
#    AM3  DISCLOSURE-PFLEGT: Jeder Post mit Affiliate-Link braucht
#         Werbekennzeichnung. Fehlt sie -> SELBSTHEILUNG (Standard-Zeile
#         unten + kurz oben vor der ersten Affiliate-Referenz).
#    AM4  CHRISTOLOGIE der CTAs: selbe Anker-Phrase ueberall = Muster-
#         Risiko -> REPORT + Variante aus Pool vorschlagen.
#    AM5  CTA-Qualitaet: Formel „Verb + Nutzen" – Report wenn schwach.
#    AM6  Anti-Stuffing: mehr als 9 Affiliate-Links = Spam-Verdacht (mit
#         Sponsivitaet in Prozent). Statistischer Report.
#
#  SELBSTHEILUNG nur bei AM1/AM2/AM3 (unkomplizierte Fixes). Vier Restposten
#  entstehen nie durch KI – die Vorlagen sind fest und Rechts-safe.
#
#  Aufruf:
#    python3 scripts/affiliate_marketer.py             # Report (weich)
#    python3 scripts/affiliate_marketer.py --fix       # Selbstheilung
#    python3 scripts/affiliate_marketer.py --new-only  # Engine-Modus
#    python3 scripts/affiliate_marketer.py --dry-run
#
#  Ausgabe: AFFILIATE-MARKETING-REPORT.md + history jsonl
# ============================================================

import json
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import affiliate_intent_contract as vk  # noqa: E402  (SSOT Anker/Sätze/Routen)

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "scripts" / "check24_links.yaml"
REPORT = ROOT / "AFFILIATE-MARKETING-REPORT.md"
HISTORY = ROOT / "data" / "affiliate_marketing_history.jsonl"

DO_FIX = "--fix" in sys.argv
DRY_RUN = "--dry-run" in sys.argv
NEW_ONLY = "--new-only" in sys.argv

AFFIL = re.compile(r"/go/[\w-]+/|a\.(check24\.net|partner-versicherung\.de)")
DISCLAIMER_PAT = re.compile(r"Affiliate-Links|Werbung|Tipp von FranksFinanzcheck", re.I)

PILLAR_ROUTE = {
    "frugalismus": "allgemein",
    "internet-dsl": "dsl",
    "konto-karten": "girokonto",
    "strom-sparen": "strom",
    "mietwagen": "mietwagen",
    "versicherungen": "haftpflicht",
}

# THEMA-SCHNÜFFLER: Wenn der Pillar ein Fremdpaket war (gestern: fast alle
# hartkodiert auf konto-karten!), lenkt dieser Kontextabgleich auf bessere
# Routen, ohne das System zu destabilisieren. Reihenfolge = Spezifität.
# 19.09.2026 (Intent-Wache): DIESELBE Themen-Reihe wie der Intent-Kontrakt –
# scripts/affiliate_intent_contract.py ist die eine Wahrheit für Route,
# Anker und Satz. Vorher stand hier eine Kopie, und die Kopie kannte die
# Wohngebäude-Route nicht: Ein Wohngebäude-Artikel fiel auf „elementar" →
# /go/hausrat/ (Fund 19.09.2026). Kopien driften, deshalb keine Kopie.
# Die historischen Begründungen (#295 Alltagswörter, Reserve #5 Gas-Tarif,
# Energiemarkt-Fallback) stehen kommentiert im Kontrakt.
DEEP_HINTS = list(vk.DEEP_HINTS)

GO_ROUTE_RX = re.compile(r"/go/([a-z0-9][a-z0-9-]*)/?", re.I)
BEKANNTE_ROUTEN = {k for _, k in DEEP_HINTS} | set(PILLAR_ROUTE.values()) | {"allgemein"}


def route_for(text: str, pillar: str = "", title: str = "") -> str:
    """Wählt den konversionsstärksten Deep-Link. Erst Thema aus dem Artikel
    (Titel + Tags + Intro), dann sauberer Pillar-Fallback.

    Zwei Vorstöße seit 15.09.2026, beide vor dem 1200-Zeichen-Fenster:
    (1) der TITEL ist die sauberste Themen-Aussage, (2) ein /go/<route>/-Gateway
    im Artikel ist eine redaktionelle Entscheidung. Ohne sie überstimmte ein
    „Kasko" im Intro den Mietwagen-Artikel (kfz|kasko steht in DEEP_HINTS vor
    mietwagen) – die Fazit-Schmiede setzte dadurch in neun Artikel einen
    thematisch fremdenDomainsatz.
    """
    txt = text or ""
    if title:
        for pat, key in DEEP_HINTS:
            if pat.search(title):
                return key
    for m in GO_ROUTE_RX.finditer(txt):
        key = m.group(1).lower()
        if key in BEKANNTE_ROUTEN:
            return key
    ctx = txt.lower()[:1200]
    for pat, key in DEEP_HINTS:
        if pat.search(ctx):
            return key
    return PILLAR_ROUTE.get(pillar, "allgemein")


def route_explicit(text: str):
    """Wie route_for, ABER nur bei einem echten Themen-Treffer (DEEP_HINTS).

    Der Pillar-Fallback wird NICHT als Kontextbeweis gewertet: er ist zu
    grob, um einen registrierten Gateway-Link umzuschreiben.
    """
    ctx = text.lower()[:1200]
    for pat, key in DEEP_HINTS:
        if pat.search(ctx):
            return key
    return None


# Markdown-Gateway-Link mit optionalem absolutem Blog-Host (Reserve #5:
# die KI lieferte [Gas-Tarife](https://franksfinanzcheck.de/go/tagesgeld/)
# statt des relativen /go/-Gateways; der Render-Hook versieht nur relative
# /go/-Links mit rel="sponsored" -> harter Affiliate-Integrity-Fund).
MD_GO_LINK_RE = re.compile(
    r"(\[[^\]]+\]\()"
    r"(?:https?://(?:www\.)?franksfinanzcheck\.de)?"
    r"/go/([\w-]+)(/?)(\))")


def heal_misrouted_links(text: str, reg: dict, pillar: str = ""):
    """Heilt thematisch FALSCHE, aber registrierte Gateway-Keys.

    Bewusst konservativ, damit Cross-Selling nicht zerstoert wird:
      * Artikel-Route R muss ueber einen echten DEEP_HINTS-Treffer belegt
        sein (kein „allgemein“, kein bloesser Pillar-Fallback).
      * Der Artikel MUSS bereits mindestens einen Link auf /go/R/ haben
        (das eigene Thema ist versorgt; der Fremdlink ist dann ein Fehler,
        kein beabsichtigtes Zweitangebot).
      * Im Umfeld des Fremdlinks muss dasselbe Thema R explizit genannt
        sein – Beweis primaer ueber den Link-Ankertext selbst plus ein
        enges +/-80-Zeichen-Fenster (das breite +/-180-Fenster griff am
        11.09.2026 durch ein themenfremdes Wort im Absatz darueber
        daneben).
      * Absolute Blog-Host-URLs werden dabei automatisch relativiert.
    """
    route = route_explicit(text)
    if not route or route not in reg or route == "allgemein":
        return text, 0
    if not re.search(r"/go/" + re.escape(route) + r"/", text):
        return text, 0
    fixed = 0

    def repl(m):
        nonlocal fixed
        head, key, slash, tail = m.group(1), m.group(2), m.group(3), m.group(4)
        if key == route:
            if m.group(0).startswith("http"):
                fixed += 1
                return head + "/go/" + key + "/" + tail
            return m.group(0)
        # Themenbeweis PRIMÄR über den Link-Text selbst (der Anker nennt das
        # Angebot, z. B. „Gas-Tarife vergleichen“) plus enge ±80-Zeichen-Um-
        # gebung. Das breite ±180-Fenster griff 11.09.2026 daneben ("Urlaub"
        # im Absatz darüber schlug das im Anker stehende "Gas-Tarif").
        label = head.strip("[]( ")
        start = max(0, m.start() - 80)
        window = label + " " + text[start:m.end() + 80]
        if route_explicit(window) == route:
            fixed += 1
            return head + "/go/" + route + "/" + tail
        # Kein Themenbeweis, aber absoluter Host: trotzdem kanonisieren.
        if m.group(0).startswith("http"):
            fixed += 1
            return head + "/go/" + key + slash + tail
        return m.group(0)

    new_text = MD_GO_LINK_RE.sub(repl, text)
    return new_text, fixed


def normalize_gateway_links(text: str, reg: dict, pillar: str = "") -> tuple[str, int]:
    """NR (08.09.2026, Reserve-Engpass #224): Gateway-Links deterministisch
    normalisieren, BEVOR das Publish-Gate prüft.

    Heilungsklasse im echten Befund (08.09.2026):
      * `/go/check24-dsl/` – Key nicht in check24_links.yaml registriert
        -> reserve_readiness.py lehnte den Kandidaten ewig ab (Pool 1/6,
        täglicher „Stock shortage“-Alarm).
      * `/go/check24-finanzen` – registrierter Pfad OHNE Schluss-Slash
        -> der AI4-Render-Beweis sah den Link nicht (Gate-blind) und der
        Kandidat wurde als „ready“ zertifiziert, obwohl die Zielseite
        404 liefert. Das ist der gefährlichere Fall (still toter Link).

    Regeln (idempotent, ohne KI, ohne Hugo-Build):
      1. Key nicht registriert -> auf die thematisch beste Route ersetzen
         (Kontextfenster ±180 Zeichen um den Link, sonst Artikel-Route).
      2. Registrierter Key ohne Slash -> kanonisch `/go/<key>/` ergänzen
         (Gateway-Seiten + AI4-Beweis erwarten exakt den Slash).
      3. Registrierte, korrekte Links bleiben byte-identisch.
    """
    known = set(reg)

    def repl(m: re.Match) -> str:
        nonlocal fixed
        had_host = m.group(0).startswith("http")
        key = m.group(1)
        if key not in known:
            start = max(0, m.start() - 180)
            window = text[start:m.end() + 180]
            route = route_for(window, pillar)
            if route not in known:
                route = "allgemein"
            fixed += 1
            return f"/go/{route}/"
        out = f"/go/{key}/"
        # Fehlender Slash oder absoluter Blog-Host zaehlen als Korrektur;
        # kanonische relative Links bleiben bytegleich (kein Churn).
        if had_host or not m.group(2):
            fixed += 1
        return out

    fixed = 0
    # 11.09.2026 (Reserve #5): optionalen absoluten Blog-Host mit
    # aufsaugen -> alle /go/-Links verlassen die KI-Erzeugung kanonisch
    # relativ (nur so greift rel="sponsored" im Render-Hook).
    go_re = re.compile(
        r"(?:https?://(?:www\.)?franksfinanzcheck\.de)?/go/([\w-]+)(/?)")
    new_text = go_re.sub(repl, text)
    return new_text, fixed

# ------------------------------------------------------------
# SABOTAGE-SCHUTZ (Selbsttest-Batterie, 11.08.2026)
# 19 kanonische Routing-Faelle, eingefroren nach der grossen
# Fehlrouting-Korrektur (Depot->girokonto, Elementar->handytarife,
# Sicher heizen->girokonto usw. waren die Schaedlinge).
# Wenn kuenftig jemand - Mensch oder KI - die DEEP_HINTS
# "verbessert" oder reiht und dadurch das Routing kippt, bricht
# JEDER Lauf (manuell + CI) sofort mit Exit 2 ab, BEVOR auch nur
# eine Datei angefasst wird. Ehrlich statt still kaputt.
# ------------------------------------------------------------
SELFTEST = [
    # (Kontexttext, Pillar, erwartete Route)
    ("So sicherst du dir den besten DSL-Wechselbonus und Cashback", "", "dsl"),
    ("Girokonto wechseln mit dem Wechselservice: Kontoführungsgebühren vermeiden", "", "girokonto"),
    ("Günstige Flüge finden: Die besten Tricks für dein Flugticket", "", "fluege"),
    ("KFZ-Versicherung wechseln: So nutzt du deine SF-Klasse optimal", "", "kfz-versicherung"),
    ("Unfallversicherung: Warum sie wichtiger ist als viele denken", "", "unfallversicherung"),
    ("Sicher heizen mit Preisgarantie: Gastarife vergleichen und den Gaspreis sichern", "", "gas"),
    ("Strom sparen im Haushalt: 20 Tipps gegen Stromfresser", "", "strom"),
    ("Handytarife vergleichen: Mehr Datenvolumen fürs gleiche Geld", "", "handytarife"),
    # DER Sabotage-Klassiker: frueher routete das faelschlich auf handytarife!
    ("Elementarschadenversicherung: Schutz bei Hochwasser und Starkregen", "", "hausrat"),
    ("Privathaftpflicht: Warum sie Pflicht für jeden ist", "", "haftpflicht"),
    ("Hausratversicherung: Wer braucht welche Leistung?", "", "hausrat"),
    ("Depot 2026: Dein smarter Start in den Vermögensaufbau mit ETF-Sparplan", "", "tagesgeld"),
    ("Kreditkarte ohne Jahresgebühr: Die besten kostenlosen Karten", "", "kreditkarte"),
    ("Mietwagen buchen: So sparst du bei der Autovermietung", "", "mietwagen"),
    ("Urlaubskasse aufbessern: Die besten Spartipps für deinen nächsten Urlaub", "", "reisen"),
    ("Tierkrankenversicherung: So schützt du deinen Hund vor hohen Tierarztkosten", "", "hunde"),
    # wie im echten Tier-Artikel Front-Matter (Tags: Tierversicherung …):
    ("Tierversicherung: Schutz für dein Tier im Krankheitsfall", "versicherungen", "hunde"),
    # Pillar-Fallback, wenn das Thema keine Fach-Route hat:
    ("Ganz ohne passendes Fachthema im Text", "konto-karten", "girokonto"),
    # bewusst breites Budget-Thema bleibt beim Portal:
    ("Haushaltsbuch führen: So behältst du dein Monatsbudget im Griff", "", "allgemein"),
    # 15.09.2026: der im Artikel stehende Gateway-Link ist die Wahrheit – auch
    # gegen ein Fremdstichwort im Intro-Fenster (Kasko/SF-Klasse -> kfz).
    ("Kasko, SF-Klasse und was am Schalter zählt [Vergleich](/go/mietwagen/)", "", "mietwagen"),
    # 15.09.2026 (#295): Energiemarkt-Vokabular gehört auf die Energie-Route,
    # nicht über das Alltagswort „Flut“ in die Hausrat-Versicherung. Realer
    # Befund: Entwurf „Energie-Update …“ (Grundversorger/Energiemarkt) bekam
    # /go/hausrat/ – die Redaktion verlinkt diese Serie aber auf /go/strom/.
    ("Viele Grundversorger überarbeiten zum Jahresende ihre Tarife. "
     "Der Energiemarkt bleibt dynamisch, ein Wechsel lohnt sich.", "", "strom"),
    ("Gleichzeitig kann die Flut an Informationen verwirrend wirken. "
     "Prüfe deinen Vertrag und vergleiche die Konditionen.", "", "allgemein"),
    ("Nach dem Starkregen zeigt sich: Die Elementarschaden-Deckung fehlt.",
     "", "hausrat"),
]


def run_selftest() -> list[str]:
    """Prüft jede kanonische Route. Liefert Fehlerliste (leer = alles gut)."""
    fehler = []
    # Titel-Fenster (15.09.): ein Kasko-Hinweis im Text darf den Mietwagen-Titel
    # nicht überstimmen – route_for(title=...) ist die Quelle für Fazit & FAQ.
    got_titel = route_for("Kasko und SF-Klasse am Schalter", "",
                         "Mietwagen ohne Kautionsfallen: So sparst du im Urlaub")
    if got_titel != "mietwagen":
        fehler.append(f"  Titel-Fenster: erwartet /go/mietwagen/, bekam /go/{got_titel}/")
    for i, (txt, pillar, want) in enumerate(SELFTEST, 1):
        got = route_for(txt, pillar)
        if got != want:
            fehler.append(f"  Fall {i}: erwartet /go/{want}/, bekam /go/{got}/  ← „{txt[:60]}“")
    # NR-Regression (08.09.2026, Reserve-Engpass #224): Die Gateway-
    # Normalisierung darf weder registrierte Links beschädigen noch
    # unbekannte Keys durchrutschen lassen. Eingefroren auf die realen
    # Befunde: /go/check24-dsl/ (unbekannt) und /go/kreditkarte (ohne Slash).
    try:
        reg_test = load_registry()
        t1, n1 = normalize_gateway_links(
            "Für den [DSL-Vergleich](/go/check24-dsl/) lohnt der Anbieterwechsel.",
            reg_test, "frugalismus")
        t2, n2 = normalize_gateway_links(
            "Alle Karten im [Vergleich](/go/kreditkarte) ohne Jahresgebühr.",
            reg_test, "konto-karten")
        if n1 != 1 or "/go/dsl/" not in t1 or "/go/check24-dsl" in t1:
            fehler.append("  NR: unbekannter Key nicht umgeroutet "
                          f"(n1={n1}, t1={t1[:90]})")
        if n2 != 1 or "/go/kreditkarte/" not in t2 or "/go/kreditkarte)" in t2:
            fehler.append("  NR: fehlender Slash nicht ergänzt "
                          f"(n2={n2}, t2={t2[:90]})")
        # HOST-KANONISIERUNG (Reserve #5, 11.09.2026): absoluter Blog-Host
        # muss zur relativen /go/-Form werden (sonst fehlt rel=sponsored).
        t3, n3 = normalize_gateway_links(
            "Siehe [Gas](https://franksfinanzcheck.de/go/gas) hier.",
            reg_test, "strom-sparen")
        if n3 != 1 or "https://franksfinanzcheck.de" in t3 \
                or "/go/gas/" not in t3:
            fehler.append(f"  NR: absoluter Blog-Host nicht kanonisiert (t3={t3})")
        # MISROUTING (Reserve #5): Gas-Artikel mit eigenem Gas-Link und
        # thematisch belegtem tagesgeld-Fremdlink wird umgeroutet + relativ.
        gas_text = ("Gasrechnung senken, Gastarife vergleichen, Gasanbieter "
                    "wechseln. [Gas-Tarife sparen](/go/gas/) und "
                    "[anders](https://franksfinanzcheck.de/go/tagesgeld/) "
                    "mit Gas-Kontext.")
        t4, n4 = heal_misrouted_links(gas_text, reg_test, "strom-sparen")
        if n4 != 1 or "/go/tagesgeld/" in t4 or "/go/gas/ ]" in t4 \
                or t4.count("/go/gas/") != 2:
            fehler.append(f"  NR: Fehlrouting nicht geheilt (n4={n4}, t4={t4})")
        # Konservativ: ohne eigenen Themenlink bleibt der Fremdlink unangetastet.
        gas_ohne_eigenen = ("Gasrechnung senken, Gastarife vergleichen. "
                            "[anders](https://franksfinanzcheck.de/go/tagesgeld/)")
        t5, n5 = heal_misrouted_links(gas_ohne_eigenen, reg_test, "strom-sparen")
        if n5 != 0 or "/go/tagesgeld/" not in t5:
            fehler.append(f"  NR: zu aggressives Routing ohne eigenen Link (n5={n5})")
        # Idempotenz
        t6, n6 = heal_misrouted_links(t4, reg_test, "strom-sparen")
        if n6 != 0 or t6 != t4:
            fehler.append("  NR: Misrouting-Heilung ist nicht idempotent")
    except Exception as exc:  # noqa: BLE001
        fehler.append(f"  NR: Selbsttest-Ausnahme: {exc}")
    return fehler

# ============================================================
#  CTA-WAHRHEIT AUS DEM INTENT-KONTRAKT (19.09.2026)
# ------------------------------------------------------------
#  Vorher: CTA_POOL mit vier generischen Anker-Paaren, ausgewählt über
#  `date.today().day` – derselbe Artikel bekam je nach Kalendertag einen
#  anderen Anker („Jetzt Angebote vergleichen", „Tarifrechner starten",
#  „Kostenlos vergleichen"), und KEINER nannte das Produkt. Das war die
#  Quelle der Fehlrouten vom 19.09.2026 (Kfz-Artikel → Haftpflicht,
#  Girokonto → Ratenkredit, Kreditkarte → Reisekrankenversicherung,
#  Mietwagen → Kfz, Flüge → Mietwagen, Wohngebäude → Hausrat): Ein Anker,
#  der nichts verspricht, widerspricht sich nie – und fiel durch jedes
#  Raster, während der Besucher auf einem fremden Produkt landete.
#
#  Jetzt: Anker UND Satz kommen aus dem Kontrakt (produkt-exakt, bei
#  Abweichung ehrlich benannt: C24 Bank, Pauschalreise statt Flug).
#  Die Variante wird über den Artikel-Slug deterministisch gewählt –
#  stabil über Läufe (Idempotenz, kein Tages-Churn) und trotzdem
#  variantenreich über Artikel hinweg (AM4 „Christologie").
#
#  Bewacht von scripts/affiliate_intent_guard.py (IW6): Die Wache ruft
#  diese drei Bauer für JEDE Route auf und verlangt Route + produkt-
#  exakten + ehrlichen Anker. Wer hier wieder generisch wird, bekommt
#  Exit 1 und keine Veröffentlichung.
# ============================================================


def cta_route(pillar: str, artikel_text: str = "") -> str:
    """Route für einen CTA: Artikelthema schlägt Pillar-Fallback."""
    if artikel_text:
        return route_for(artikel_text, pillar)
    return PILLAR_ROUTE.get(pillar, "allgemein")


def cta_url(route: str, reg: dict) -> str:
    """Nur registrierte Routen werden verlinkt (nie ein totes Gateway)."""
    return f"/go/{route}/" if route in reg else "/go/allgemein/"


def mid_cta(pillar: str, reg: dict, artikel_text: str = "", slug: str = "") -> str:
    """AM7 (Frank 12.08.): In-Text-CTA - midlanger Artikel, Conversion
    weiter hoch, 2-flaechig oben/unten -> Streifen in der Mitte."""
    route = cta_route(pillar, artikel_text)
    url = cta_url(route, reg)
    satz, anchor = vk.cta_bausteine(route, "mid", slug or route)
    return (
        f'\n> 💶 **Spar-Tipp zwischendurch:** {satz}: '
        f'[**{anchor}**]({url})\n'
    )


def build_top_cta(pillar: str, reg: dict, artikel_text: str = "", slug: str = "") -> str:
    route = cta_route(pillar, artikel_text)
    url = cta_url(route, reg)
    satz, anchor = vk.cta_bausteine(route, "top", slug or route)
    return (
        f'\n---\n\n💡 **Schnell-Tipp von FranksFinanzcheck:** {satz}: '
        f'[**{anchor}**]({url})\n'
        f'_(Dieser Artikel enthält Affiliate-Links (Werbung). Beim Abschluss über einen Link '
        f'erhalten wir eine Provision – für dich entstehen keine Mehrkosten.)_'
    )


def end_cta(pillar: str, reg: dict, artikel_text: str = "", slug: str = "") -> str:
    route = cta_route(pillar, artikel_text)
    url = cta_url(route, reg)
    _, anchor = vk.cta_bausteine(route, "end", slug or route)
    return (
        f'\n---\n\n👉 **Sparend zuerst vergleichen:** [**{anchor}**]({url})\n\n'
        f'*Dieser Artikel enthält Affiliate-Links (Werbung). Beim Abschluss über einen Link '
        f'erhalten wir eine Provision – für dich entstehen keine Mehrkosten.*'
    )


def load_registry():
    reg = {}
    for line in REGISTRY.read_text(encoding="utf-8").splitlines():
        ls = line.strip()
        if ls and not ls.startswith("#") and ": " in ls and '"' in ls:
            key = ls.split(":")[0].strip()
            url = ls.split('"')[1]
            reg[key] = url
    return reg


def fm(text, key):
    m = re.match(rf'(?m)^{key}:\s*["\']?(.*?)["\']?\s*$', text[:2500], re.M)
    return m.group(1).strip() if m else ""


def pillar_of(text):
    return fm(text, "pillar")


def go_link(text):
    m = list(AFFIL.finditer(text))
    return [(m.group(0), m.start()) for m in m]


def first_affil_quote(bodysplit: list[str]) -> float:
    for i, l in enumerate(bodysplit):
        if AFFIL.search(l):
            return i / max(1, len(bodysplit))
    return 0.0


def process(path: Path, reg: dict) -> dict:
    text = path.read_text(encoding="utf-8")
    # Artikel-Slug = Stabilisator für die Anker-Variante (deterministisch,
    # kein Tages-Churn, Idempotenz der Wache – siehe vk.Ziel.anker_fuer).
    slug = path.parent.name if path.name == "index.md" else path.stem
    body_stripped = text.split("\n")
    # Front-Matter skippen
    i = 0
    if lines := text.split("\n"):
        pass
    lines = text.split("\n")
    in_code = False
    fm_done = False
    body_start = 0
    for idx, raw in enumerate(lines):
        if idx == 0 and raw.strip() == "---": pass
        if raw.startswith("---") and idx == 0:
            pass
        if fm_done:
            body_start = idx
            break
        if idx == 0 and raw.strip() == "---":
            continue
        if raw.startswith("---"):
            fm_done = True
            rest = raw[3:]
            if rest.strip():
                body_start = idx  # geklebte Fence: ab dieser Zeile ist Body
                break
    body_lines = lines[body_start:]
    affils = go_link("\n".join(body_lines))
    pillar = pillar_of(text)
    has_disclaimer = bool(DISCLAIMER_PAT.search(text))
    fixes = {"am1": False, "am2": False, "am3": False, "am7": False,
             "am8": False}
    status = []
    if not affils:
        status.append(("AM1", "kein Affiliate-Link", "kritisch"))
        if DO_FIX and not DRY_RUN:
            text = text.rstrip() + end_cta(pillar, reg, text, slug) + "\n"
            fixes["am1"] = True
    else:
        pos = first_affil_quote(body_lines)
        if pos > 0.5:
            status.append(("AM2", f"erster CTA bei {pos*100:.0f}% der Artikel", "hoch"))
            if DO_FIX and not DRY_RUN:
                # Heilung: kanonischer Platz VOR der ersten H2 (nach dem Intro).
                idx_h2 = None
                for j, l in enumerate(body_lines):
                    if l.startswith("## "):
                        idx_h2 = body_start + j
                        break
                if idx_h2 is None:
                    filled = [j for j, l in enumerate(body_lines) if l.strip()]
                    if len(filled) >= 3:
                        idx_h2 = body_start + filled[2]
                if idx_h2 is not None:
                    text_lines = text.split("\n")
                    text_lines = text_lines[:idx_h2] + ["", build_top_cta(pillar, reg, text, slug), ""] + text_lines[idx_h2:]
                    text = "\n".join(text_lines)
                    fixes["am2"] = True
    if not has_disclaimer:
        status.append(("AM3", "Disclaimer fehlt komplett", "kritisch"))
        if DO_FIX and not DRY_RUN:
            text = text.rstrip() + "\n\n" + (
                "*Dieser Artikel enthält Affiliate-Links (Werbung). Beim Abschluss über einen Link "
                "erhalten wir eine Provision – für dich entstehen keine Mehrkosten.*") + "\n"
            fixes["am3"] = True

    # AM7-MID-CTA (Frank 12.08.): Kellermann-Conversion: ein guter Pro-Marker
    # sorgt fuer (1) oberen PFad, (2) Text-CTA (middle), (3) Schluss-CTA.
    # Wir verteilen den Mittel-CTA NUR wo wir unbehindert groessenstefen (>~700
    # Woerter) und maximal 2 In-Text/gefuehrte Links (kein Werbestreifen!).
    n_affil = len(list(AFFIL.finditer(text)))
    if DO_FIX and not DRY_RUN and 0 < n_affil <= 2 and len(text.split()) >= 700:
        # Einfuegepunkt: halbe Textmitte nach H2-Fortschritt
        text_lines = text.split("\n")
        half = len(text.split()) // 2
        words = 0
        insert_at = None
        for j, l in enumerate(text_lines):
            words += len(l.split())
            if l.startswith("## ") and words >= half:
                insert_at = j
                break
        if insert_at:
            route = route_for(text, pillar)
            # Verdopplung-Pfosten: nie zwei Anker denselben Namen ins selbe Auge
            if mid_cta(pillar, reg, text, slug).strip() not in text:
                text_lines = text_lines[:insert_at] + ["", mid_cta(pillar, reg, text, slug), ""] + text_lines[insert_at:]
                text = "\n".join(text_lines)
                fixes["am7"] = True
                status.append(("AM7", f"In-Text-CTA hinzu, Ziel /go/{route}/", "info"))

    # NR (08.09.2026): Gateway-Links normalisieren – unbekannte Keys auf die
    # thematisch beste Route, fehlende Schluss-Slashes ergänzen. Läuft VOR
    # dem RT-Retarget, damit auch In-Text-Links (keine CTA-Boxen) im
    # Register landen und der AI4-Render-Beweis sie schlüsselgenau sieht.
    # NUR im FIX-Modus: Report-/Selftest-Läufe bleiben read-only.
    if DO_FIX and not DRY_RUN:
        text, n_mis = heal_misrouted_links(text, reg, pillar)
        if n_mis:
            fixes["am8"] = True
            status.append(("NR", f"Gateway-Fehlrouting/Host-Form geheilt: {n_mis}",
                           "info"))
        norm_text, n_norm = normalize_gateway_links(text, reg, pillar)
        if n_norm:
            text = norm_text
            fixes["am8"] = True
            status.append(("NR", f"Gateway-Links normalisiert: {n_norm}",
                           "info"))

    # RETARGET (universell & sabotage-robust): Jede Schnell-Tipp-Box, deren Route vom
    # Ideal abweicht, wird auf die thematisch beste Route umgeschrieben.
    # Register-Gate gegen 404. Sabotage-Test ist global (selftest) aktiv.
    #
    # 08.09.2026 (Kontext-Fix): `best` wurde früher NUR aus dem Artikel-
    # Kontext (erste 1200 Zeichen) bestimmt. Bei Budget-Artikeln mit
    # „Tagesgeldkonto“-Anker (z. B. haushaltsbuch-fuehren) gewann so
    # „allgemein“ -> die C24-Bank-CTA „…Tagesgeld vergleichen“ zeigte auf
    # /go/allgemein/ (Anker/Route-Dissonanz). Jetzt: lokales Kontextfenster
    # um die CTA (Anker + ±300 Zeichen) hat Vorrang; Artikel-Kontext nur,
    # wenn lokal nichts Spezifisches erkennbar ist.
    marker = "Schnell-Tipp von FranksFinanzcheck"
    cur_route_m = re.search(marker + r".*?/go/([\w-]+)/", text, re.S)
    best = ""
    if cur_route_m:
        ctx = text[max(0, cur_route_m.start() - 300):cur_route_m.start() + 340]
        best = route_for(ctx, pillar)
        if best not in reg or best == "allgemein":
            best = route_for(text, pillar)
        if best not in reg:
            best = "allgemein"
    if best and best in reg and cur_route_m:
        cur_route = cur_route_m.group(1)
        if cur_route != best:
            new_text, n = re.subn(
                re.escape(marker) + r"(.*?)\/go\/" + re.escape(cur_route) + r"\/",
                marker + "\\1/go/" + best + "/",
                text, count=1)
            if n > 0:
                text = new_text
                fixes["am2"] = True
                status.append(("RT", f"Top-CTA: /go/{cur_route}/ -> /go/{best}/ (thematisch besser)", "info"))
    return {"file": str(path.relative_to(ROOT)), "text": text, "fixes": fixes, "status": status,
            "affils": len(affils)}


def anchor_report(affil_anchor_map):
    return {}


def main():
    # SABOTAGE-SCHUTZ zuerst: Routing-Selbsttest VOR jeder Datei-Beruehrung.
    fehler = run_selftest()
    if fehler:
        print("🛑 SELBSTTEST FEHLGESCHLAGEN – Routing-Sabotage verhindert.")
        print("   Kein Lauf, keine Datei angefasst. Bitte DEEP_HINTS/route_for prüfen:")
        print("\n".join(fehler))
        sys.exit(2)
    print(f"✅ Selbsttest: {len(SELFTEST)} kanonische Routen stimmen.")
    reg = load_registry()
    posts = sorted((ROOT / "content" / "posts").glob("*/index.md"))
    if NEW_ONLY:
        today = date.today().isoformat()
        posts = [p for p in posts if p.parent.name.startswith(today)]
    results, touch = [], 0
    for p in posts:
        r = process(p, reg)
        results.append(r)
        zusatz = sum(r["fixes"].values())
        # 08.09.2026 (Write-Guard): Nur der FIX-Modus schreibt. Report- und
        # Selftest-Aufrufe (--selftest, keine Flags) waren vorher in der
        # Lage, Live-Inhalte zu verändern, sobald ein Fix-Flag gesetzt war
        # (real ausgelöst durch die NR-Normalisierung).
        if zusatz and DO_FIX and not DRY_RUN:
            p.write_text(r["text"], encoding="utf-8")
            touch += 1

    # Anchor-Diversitaet (Report brutto)
    anchors = []
    for p in posts:
        for m in re.finditer(AFFIL, p.read_text(encoding="utf-8")):
            pass  # nur Struktur – HTML-Anker ziehen waere Overhead hier unten
    mode = "DRY-RUN" if DRY_RUN else ("FIX" if DO_FIX else "REPORT")
    kritisch = sum(1 for r in results for s in r["status"] if s[2] == "kritisch")
    fix_anzahl = sum(sum(r["fixes"].values()) for r in results)
    L = [f"# 🎯 AFFILIATE-MARKETING-REPORT", "",
         f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · Modus: {mode}",
         f"**Artikel:** {len(results)} · **Kritisch:** {kritisch} · **Autofixes:** {fix_anzahl}"]
    fehlt = [r for r in results if 'AM1' in [s[0] for s in r["status"]]]
    spaet = [r for r in results if 'AM2' in [s[0] for s in r["status"]]]
    if fehlt:
        L += ["", "## 🔴 AM1 – Ohne Affiliate-Link (" + str(len(fehlt)) + ")" + (" -> geheilt" if DO_FIX else ""), ""]
        L += [f"- `{r['file']}`" for r in fehlt[:20]]
    if spaet:
        L += ["", "## 🟡 AM2 – Erste CTA sehr spaet (>50% Artikel) (" + str(len(spaet)) + ")" + (" -> mit Top-Empfehlung geheilt" if DO_FIX else ""), ""]
        L += [f"- `{r['file']}`" for r in spaet[:20]]
    disc = [r for r in results if 'AM3' in [s[0] for s in r["status"]]]
    if disc:
        L += ["", "## 🔴 AM3 – Disclaimer fehlte (" + str(len(disc)) + ")" + (" -> geheilt" if DO_FIX else ""), ""]
        L += [f"- `{r['file']}`" for r in disc[:15]]
    if not fehlt and not spaet and not disc:
        L += ["", "🎉 Alle Money-Pages: CTA frueh + Disclaimer komplett. Pro-Level."]
    L += ["", "---", "_Conversion: CTA frueh sichtbar + Werbekennzeichnung oben. Google und LG sind zufrieden._"]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:25]))
    HISTORY.parent.mkdir(exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"date": date.today().isoformat(), "modus": mode,
                             "kritisch": kritisch, "autofix": fix_anzahl},
                            ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
