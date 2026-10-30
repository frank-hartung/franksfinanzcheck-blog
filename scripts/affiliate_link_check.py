"""Affiliate-Link-Checker (vollautomatisch, Top-Level) für FranksFinanzcheck.

Prüft ALLE Posts auf:
  1) Vorhandensein: Jeder kommerzielle Post braucht einen Affiliate-Link.
     Redaktionelle Fachseiten ohne passendes Angebot dürfen mit
     `affiliate_exempt: true` UND einer Begründung ausdrücklich ausgenommen
     werden. Ein unpassender CTA wird nicht automatisch in den Text gedrückt.
  2) DEEP-LINK-KORREKTHEIT: Der Post muss auf den thematisch passenden
     Deep-Link verweisen. Spezifische Bestandszuordnungen bleiben erhalten;
     die eindeutige Produktklasse Handytarife wird zusätzlich über den
     zentralen `affiliate_intent_contract` erkannt, bevor der grobe
     Internet-Pillar-Fallback greift. Breitere Themen- und Cross-Selling-Fälle
     bleiben bewusst kuratiert, statt aus beliebigen Textwörtern zu raten.
  3) PARTNER-IDS: pid=80968&aid=18 (CHECK24) bzw. partner_id=47086&ad_id=15
     (Tarifcheck) müssen korrekt sein – keine fremden/vertippten IDs.

Modi:
  python3 scripts/affiliate_link_check.py            # nur prüfen (Exit 0/1)
  python3 scripts/affiliate_link_check.py --fix      # generische CTA-Links durch
                                                     # passende Deep-Links ersetzen
  python3 scripts/affiliate_link_check.py --json     # JSON-Output

Exit-Codes: 0 = alles ok · 1 = Probleme gefunden (Workflow kann alerten)
"""
import os
import re
import sys
import json
import glob
import yaml

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import affiliate_intent_contract as affiliate_contract  # noqa: E402
import affiliate_exemption as exemption_contract  # noqa: E402 – Ausnahme-Vertrag (#762)

POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
REPORT_FILE = os.path.join(BLOG_DIR, "AFFILIATE-REPORT.md")
JSON_FILE = os.path.join(BLOG_DIR, ".affiliate_report.json")

CHECK24 = "https://a.check24.net/misc/click.php?pid=80968&aid=18"
TARIFCHECK = "https://a.partner-versicherung.de/click.php?partner_id=47086&ad_id=15"

# ---------------------------------------------------------------- Deep-Mapping
# Slug → (deep-Parameter, Anzeige-Name). Präzise Themen-Zuordnung.
SLUG_DEEP = {
    # Strom & Energie
    "stromanbieter-wechseln-2026": ("stromanbieter-wechseln&cat=1", "Stromtarif-Vergleich"),
    "strom-sparen-haushalt-20-tipps": ("stromanbieter-wechseln&cat=1", "Stromtarif-Vergleich"),
    "stromfresser-im-haushalt-entlarven": ("stromanbieter-wechseln&cat=1", "Stromtarif-Vergleich"),
    "e-auto-laden-stromkosten-senken": ("stromanbieter-wechseln&cat=1", "Stromtarif-Vergleich"),
    "waermepumpe-vs-gasheizung-2026": ("stromanbieter-wechseln&cat=1", "Stromtarif-Vergleich"),
    "stromtarif-fuer-waermepumpe-so-sparst-du-beim-heizen": ("stromanbieter-wechseln&cat=1", "Stromtarif-Vergleich"),
    "gastarife-vergleichen-vor-dem-herbst": ("gasanbieter-wechseln&cat=3", "Gastarif-Vergleich"),
    "heizperiode-vorbereiten-spaetsommer": ("gasanbieter-wechseln&cat=3", "Gastarif-Vergleich"),
    # Internet & DSL
    "dsl-internet-flat-guenstig-sichern": ("dsl-anbieterwechsel&cat=4", "DSL-Tarifvergleich"),
    "wlan-verstaerker-vs-mesh-wlan": ("dsl-anbieterwechsel&cat=4", "DSL-Tarifvergleich"),
    "dns-server-aendern-schnelleres-internet": ("dsl-anbieterwechsel&cat=4", "DSL-Tarifvergleich"),
    "2026-08-05-internet-turbo-warum-ich-meinen-dns-server-getauscht-habe": ("dsl-anbieterwechsel&cat=4", "DSL-Tarifvergleich"),
    "2026-08-06-turbo-fuers-netz": ("dsl-anbieterwechsel&cat=4", "DSL-Tarifvergleich"),
    "handytarife-vergleichen-guenstigster-tarif": ("handytarife", "Handytarif-Vergleich"),
    # Mietwagen & Reisen
    "mietwagen-fuer-den-spaetsommer": ("mietwagen-preisvergleich&cat=10", "Mietwagen-Vergleich"),
    "mietwagen-buchen-so-sparst-du": ("mietwagen-preisvergleich&cat=10", "Mietwagen-Vergleich"),
    "mietwagen-fallen-vermeiden": ("mietwagen-preisvergleich&cat=10", "Mietwagen-Vergleich"),
    "guenstige-fluege-spaetsommer-finden": ("pauschalreisen-vergleich&cat=9", "Pauschalreisen-Vergleich"),
    "last-minute-urlaubsangebote-sichern": ("pauschalreisen-vergleich&cat=9", "Pauschalreisen-Vergleich"),
    "urlaubskasse-aufbessern-spartipps": ("pauschalreisen-vergleich&cat=9", "Pauschalreisen-Vergleich"),
    # 21.10.2026 (#829): datierter Urlaubsbudget-Ratgeber (Nachfolger von
    # urlaubskasse-aufbessern-spartipps / urlaub-mit-kindern-guenstig-spartricks)
    # liegt im Sammel-Pillar „mietwagen“ („Mietwagen & Reisen“) und verlinkt
    # vertragskonform /go/reisen/ (pauschalreisen-vergleich&cat=9).
    "2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen": ("pauschalreisen-vergleich&cat=9", "Pauschalreisen-Vergleich"),
    # Konto & Karten
    "kostenloses-girokonto-finden": ("c24bank&cat=14", "C24 Girokonto"),
    "notgroschen-aufbauen-wie-viel-reicht": ("c24bank&cat=14", "C24 Girokonto"),
    "kreditkarte-ohne-jahresgebuehr": ("kreditkarte", "Kreditkarten-Vergleich"),
    # 08.09.2026: datierter Kreditkarten-Ratgeber fehlte im Mapping – der
    # Pillar-Fallback (konto-karten) erwartete fälschlich c24bank&cat=14
    # (C24 Girokonto) und der Report blieb dauerhaft rot.
    "2026-09-03-kreditkarte-vergleichen-kostenlos-sicher-bezahlen": ("kreditkarte", "Kreditkarten-Vergleich"),
    "ratenkredit-bestszins-vergleichen": ("kredit-vergleich", "Kreditvergleich"),
    "tagesgeld-zinsen-sicher-anlegen": ("c24bank&cat=14", "C24 Tagesgeld"),
    # Versicherungen (CHECK24)
    "kfz-versicherung-wechseln": ("kfz-versicherung", "Kfz-Versicherung"),
    # Zusaetzliche Artikel (thematisch korrekte Deep-Links)
    "heizkosten-senken-10-massnahmen": ("gasanbieter-wechseln&cat=3", "Gastarif-Vergleich"),
    "nachtspeicherheizung-wechseln-oder-behalten": ("gasanbieter-wechseln&cat=3", "Gastarif-Vergleich"),
    "2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas": ("gasanbieter-wechseln&cat=3", "Gastarif-Vergleich"),
    "2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026": ("gasanbieter-wechseln&cat=3", "Gastarif-Vergleich"),
    "2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden": ("gasanbieter-wechseln&cat=3", "Gastarif-Vergleich"),
    "2026-08-16-gas-anbieter-wechseln-praxis-tipps-fuer-guenstige-tarife": ("gasanbieter-wechseln&cat=3", "Gastarif-Vergleich"),
    "2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen": ("gasanbieter-wechseln&cat=3", "Gastarif-Vergleich"),
    "5g-home-router-oder-dsl": ("handytarife", "Handytarif-Vergleich"),
    "2026-08-10-dsl-wechselbonus-sichern": ("dsl-anbieterwechsel&cat=4", "DSL-Tarifvergleich"),
    "flug-buchen-9-tricks-guenstige-tickets": ("pauschalreisen-vergleich&cat=9", "Pauschalreisen-Vergleich"),
    "pauschalreise-buchen-bester-zeitpunkt": ("pauschalreisen-vergleich&cat=9", "Pauschalreisen-Vergleich"),
    "urlaub-mit-kindern-guenstig-spartricks": ("pauschalreisen-vergleich&cat=9", "Pauschalreisen-Vergleich"),
    "mietwagen-im-winter-schnaeppchen-tricks": ("mietwagen-preisvergleich&cat=10", "Mietwagen-Vergleich"),
    "festgeld-oder-tagesgeld-2026": ("c24bank&cat=14", "C24 Tagesgeld"),
    "dispozinsen-verstehen-alternativen": ("kredit-vergleich", "Kreditvergleich"),
    "gebuehrenfallen-banking-vermeiden": ("kreditkarte", "Kreditkarten-Vergleich"),
    "reiseversicherung-richtig-kombinieren": ("kfz-versicherung", "Kfz-Versicherung"),
}

# Artikel, die Tarifcheck (partner-versicherung.de) nutzen statt CHECK24
TARIF_SLUG_DEEP_EXTRA = {
    "reiseversicherung-richtig-kombinieren": "reisekrankenversicherung",
}

# Pillar-Fallback: wenn der Slug nicht gemappt ist → Pillar-Default
PILLAR_DEEP = {
    "strom-sparen": ("stromanbieter-wechseln&cat=1", "Stromtarif-Vergleich"),
    "internet-dsl": ("dsl-anbieterwechsel&cat=4", "DSL-Tarifvergleich"),
    "mietwagen": ("mietwagen-preisvergleich&cat=10", "Mietwagen-Vergleich"),
    "konto-karten": ("c24bank&cat=14", "C24 Girokonto"),
    "frugalismus": None,  # generisch erlaubt (thematisch breit)
    "versicherungen": None,  # partner-versicherung.de mit eigenem Deep (siehe TARIF_DEEP)
}

# 12.09.2026 / 21.10.2026 (#829): Mehrprodukt-Pillars bündeln verwandte
# CHECK24-Produktfamilien unter einem gemeinsamen Dach:
# - „strom-sparen“ („Strom & Gas sparen“): Strom + Gas/Heizung
# - „mietwagen“ („Mietwagen & Reisen“): Mietwagen + Pauschalreisen/Flüge
# - „konto-karten“ („Konto & Karten“): C24 Girokonto/Tagesgeld + Kreditkarte + Ratenkredit
# Wenn ein Artikel im Pillar keinen abweichenden Einzelprodukt-Intent trägt,
# ist die Produktfamilie des Pillars zulässig; ein generischer Link ohne Deep
# bleibt ein Fehler, und fix_post zielt weiter auf den Primär-Deep.
PILLAR_DEEP_ALT = {
    "strom-sparen": [
        ("gasanbieter-wechseln&cat=3", "Gastarif-Vergleich"),
    ],
    "mietwagen": [
        ("pauschalreisen-vergleich&cat=9", "Pauschalreisen-Vergleich"),
    ],
    "konto-karten": [
        ("kreditkarte", "Kreditkarten-Vergleich"),
        ("kredit-vergleich", "Kreditvergleich"),
    ],
}

# Eindeutige Einzelprodukt-Routen aus `affiliate_intent_contract.py`, die in
# Slug/Titel eine spezifische Kaufabsicht belegen und deshalb vor dem breiten
# Pillar-Fallback Vorrang haben (#742 / #829).
EXPLICIT_PRODUCT_ROUTES = frozenset({
    "handytarife",
    "kreditkarte",
    "kredit",
    "fluege",
    "kfz-versicherung",
    "haftpflicht",
    "hausrat",
    "wohngebaeudeversicherung",
    "unfallversicherung",
    "reisekrankenversicherung",
    "zahnzusatzversicherung",
    "hunde",
})

# Für die breite Sammelroute `reisen` belegen diese Begriffe in Slug/Titel
# eindeutig einen Pauschalreise-/Urlaubsbudget-Ratgeber statt eines
# Mietwagen-Artikels mit Urlaubsbezug im Titel.
REISEN_EXPLICIT_RE = re.compile(
    r"pauschal|all.inclusive|urlaubskasse|urlaub[- ]sparen",
    re.I,
)

# Primärrouten, bei denen Slug/Titel bereits das Hauptprodukt des Pillars
# versprechen und deshalb NICHT über PILLAR_DEEP_ALT auf ein Nachbarprodukt
# ausweichen dürfen (Schutz der NIE_PAARE aus affiliate_intent_contract.py).
STRICT_PRIMARY_ROUTES = frozenset({
    "strom",
    "dsl",
    "mietwagen",
    "girokonto",
    "tagesgeld",
})
# Pillar-Seiten (content/pillar/<slug>/index.md) → erwarteter Deep-Link
PILLAR_PAGE_DEEP = {
    "strom-sparen": ("stromanbieter-wechseln&cat=1", "Stromtarif-Vergleich"),
    "internet-dsl": ("dsl-anbieterwechsel&cat=4", "DSL-Tarifvergleich"),
    "mietwagen": ("mietwagen-preisvergleich&cat=10", "Mietwagen-Vergleich"),
    "konto-karten": ("c24bank&cat=14", "C24 Girokonto"),
    "frugalismus": None,  # generisch
    "versicherungen": None,  # Tarifcheck generisch
}

# Tarifcheck-Deep-Links (partner-versicherung.de)
TARIF_SLUG_DEEP = {
    "privathaftpflicht-warum-pflicht-kosten": "haftpflichtversicherung",
    "hausratversicherung-wer-braucht-leistung": "hausratversicherung",
    "reisekrankenversicherung-wann-lohnt": "reisekrankenversicherung",
    "zahnzusatzversicherung-lohnt-sich": "zahnzusatzversicherung",
    "private-unfallversicherung-fuer-wen-sie-sich-wirklich-lohnt": "unfallversicherung",
    "2026-08-08-dein-tier-im-krankheitsfall": "hundekrankenversicherung",
}
TARIF_PILLAR_DEEP = {
    "versicherungen": None,  # generisch erlaubt, wenn kein Slug-Deep passt
}

# Partner-IDs, die NIE vorkommen dürfen (fremde/vertippte IDs)
FORBIDDEN_IDS = [
    re.compile(r"pid=\d+(?!&)" + "|pid=80968", re.I),  # placeholder – unten ersetzt
]


def norm_url(u):
    return u.replace("&amp;", "&").strip().rstrip(")")


def affiliate_exemption(post):
    """(ausgenommen, Grund, Metadatenfehler) – fail-closed bei halber Angabe.

    Der VERTRAG liegt seit #762 in `scripts/affiliate_exemption.py` – dort, wo
    auch die tägliche Integritäts-Wache ihn liest. Vorher stand die Regel
    nur hier; die zweite Wache kannte die Ausnahme nicht und meldete den
    redaktionell ausgenommenen Artikel täglich als Inhaltsschaden (Issue
    #762). Diese Funktion bleibt als Adapter erhalten (Aufrufer und Tests
    sprechen sie so an).
    """
    return exemption_contract.affiliate_exemption(post.get("frontmatter", ""))


def load_posts():
    posts = []
    pillar_dir = os.path.join(BLOG_DIR, "content", "pillar")
    for path in sorted(glob.glob(os.path.join(POSTS_DIR, "*", "index.md"))
                       + glob.glob(os.path.join(pillar_dir, "*", "index.md"))):
        with open(path, encoding="utf-8") as source:
            content = source.read()
        parts = content.split("---", 2)
        if len(parts) < 3:
            continue
        fm, body = parts[1], parts[2]
        if "draft: true" in fm:
            continue

        def get(key, _fm=fm):
            m = re.search(rf'^{key}:\s*["\']?(.+?)["\']?\s*$', _fm, re.M)
            return m.group(1).strip() if m else ""

        slug = os.path.basename(os.path.dirname(path))
        is_pillar = "/pillar/" in path
        posts.append({
            "path": path, "slug": slug, "title": get("title"),
            "pillar": get("pillar").strip('"'), "body": body, "content": content,
            "frontmatter": fm, "is_pillar": is_pillar,
        })
    return posts


def _load_registry():
    yf = os.path.join(BLOG_DIR, "scripts", "check24_links.yaml")
    if os.path.exists(yf):
        with open(yf, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return data.get("links", {})
    return {}

_REGISTRY = _load_registry()


def _target_from_registered_route(route):
    """Leitet Zieltyp und Deep-Link aus dem zentralen Gateway-Register ab."""
    url = _REGISTRY.get(route)
    if not url:
        return None
    url = norm_url(url)
    if url.startswith(CHECK24):
        art = "check24"
    elif url.startswith(TARIFCHECK):
        art = "tarifcheck"
    else:
        return None

    deep_match = re.search(r"(?:[?&])deep=([^&]+)(?:&cat=([^&]+))?", url)
    ziel = affiliate_contract.ziel(route)
    name = ziel.produkt if ziel else route
    if not deep_match:
        return ("generic_ok", None, f"Route {route}: generischer Link erlaubt")
    deep = deep_match.group(1)
    if deep_match.group(2):
        deep += f"&cat={deep_match.group(2)}"
    return (art, deep, name)


def find_affiliate_links(body):
    """Affiliate-Links (raw ODER /go/<key>/), normiert + dedupliziert."""
    links = set()
    for m in re.finditer(r"https://a\.(?:check24\.net/misc/click\.php\?[^)\s\"']+|partner-versicherung\.de/click\.php\?[^)\s\"']+)", body):
        links.add(norm_url(m.group(0)))
    # /go/: simpel, robust, escape-frei
    for token in re.findall(r"/go/[\w-]+/", body):
        key = token.split("/")[2]
        url = _REGISTRY.get(key)
        if url:
            links.add(norm_url(url))
    return sorted(links)


def cta_ziele(body: str) -> list[str]:
    """Menschenlesbare CTA-Ziele für Befundtexte: erst `/go/`-Schlüssel,
    dann rohe Partner-URLs. Die Prüfung rechnet mit normalisierten URLs
    (`find_affiliate_links`); ein Befund muss aber das nennen, was im Text
    steht – sonst sucht der Leser im Artikel nach einer URL, die dort nicht
    vorkommt (#948)."""
    keys = sorted({m.group(1) for m in re.finditer(r"/go/([\w-]+)/?", body or "")})
    raw = sorted({m.group(0) for m in re.finditer(
        r"https://a\.(?:check24\.net|partner-versicherung\.de)/[^)\s\"']+",
        body or "")})
    return [f"/go/{k}/" for k in keys] + raw


def expected_target(post):
    """Erwartetes Ziel für einen Post: (art, deep, name)
    art: 'check24' | 'tarifcheck' | 'generic_ok'"""
    slug = post["slug"]
    # 0) Pillar-Seite: eigener Mapping-Block
    if post.get("is_pillar"):
        if slug in PILLAR_PAGE_DEEP:
            entry = PILLAR_PAGE_DEEP[slug]
            if entry is None:
                return ("generic_ok", None, f"Pillar {slug}: generischer Link erlaubt")
            return ("check24", entry[0], entry[1])
        return ("generic_ok", None, f"Pillar {slug}: kein Mapping – generisch erlaubt")
    # 1) Tarifcheck-Deep (Versicherungen)
    if slug in TARIF_SLUG_DEEP_EXTRA:
        return ("tarifcheck", TARIF_SLUG_DEEP_EXTRA[slug], f"Tarifcheck: {TARIF_SLUG_DEEP_EXTRA[slug]}")
    if slug in TARIF_SLUG_DEEP:
        return ("tarifcheck", TARIF_SLUG_DEEP[slug], f"Tarifcheck: {TARIF_SLUG_DEEP[slug]}")
    # 2) CHECK24-Slug-Deep
    if slug in SLUG_DEEP:
        deep, name = SLUG_DEEP[slug]
        return ("check24", deep, name)
    # Neue/umbenannte Ratgeber zuerst fachlich einordnen. Die zentrale
    # Intent-Reihe kennt Produktbegriffe wie „Handyvertrag“; ein breiter
    # Pillar wie `internet-dsl` darf diese konkrete Kaufabsicht nicht zu
    # einem DSL-Deep-Link überschreiben. Nur Slug und Titel sind belastbare
    # Themenbelege: Body/Weiterlesen-Links enthalten oft Cross-Selling und
    # dürfen die eigene Artikelabsicht nicht überstimmen.
    route = affiliate_contract.route_fuer_text(
        text=slug.replace('-', ' '),
        titel=post.get("title", ""),
    )
    # Eindeutige Einzelprodukt-Klassen (Handytarife, Kreditkarte, Ratenkredit,
    # Flüge sowie spezifische Versicherungs-Sparten) überschreiben den breiten
    # Pillar-Fallback automatisch aus dem zentralen Intent-Vertrag (#742/#829).
    if route in EXPLICIT_PRODUCT_ROUTES:
        target = _target_from_registered_route(route)
        if target:
            return target
    # Die Sammelroute `reisen` enthält auch breite Wörter wie „Urlaub“ oder
    # „Camping“, die im Mietwagen-Pillar als Roadtrip-/Urlaubskontext vorkommen.
    # Bei expliziten Pauschalreise-/Urlaubsbudget-Begriffen in Slug oder Titel
    # ist jedoch eindeutig `pauschalreisen-vergleich&cat=9` (/go/reisen/) gemeint.
    if route == "reisen" and REISEN_EXPLICIT_RE.search(
        f"{slug.replace('-', ' ')} {post.get('title', '')}"
    ):
        target = _target_from_registered_route("reisen")
        if target:
            return target
    # 3) Pillar-Fallback
    pillar = post["pillar"]
    if pillar in PILLAR_DEEP:
        entry = PILLAR_DEEP[pillar]
        if entry is None:
            return ("generic_ok", None, f"Pillar {pillar}: generischer Link erlaubt")
        deep, name = entry
        return ("check24", deep, name)
    # 4) Unbekannt → generisch erlaubt (mit Hinweis)
    return ("generic_ok", None, "kein Mapping – generisch erlaubt")


def check_post(post):
    """Liefert Liste von Problemen für einen Post."""
    exempt, exemption_reason, metadata_error = affiliate_exemption(post)
    links = find_affiliate_links(post["body"])
    if not links:
        if exempt and not metadata_error:
            return [{
                "severity": "info",
                "msg": f"Kein Affiliate-Link (redaktionell ausgenommen: {exemption_reason})",
            }]
        problems = []
        if metadata_error:
            problems.append({"severity": "error", "msg": metadata_error})
        problems.append({"severity": "error", "msg": "KEIN Affiliate-Link vorhanden"})
        return problems

    problems = []
    if metadata_error:
        # Ein Metadatenfehler blockiert zwar den Lauf, darf aber die
        # unabhängige Link-/Partner-ID-Prüfung nicht kurzschließen.
        problems.append({"severity": "error", "msg": metadata_error})
    if exempt:
        # DAUERHEILUNG #948 (30.10.2026): Eine Ausnahme und ein vorhandener
        # Affiliate-CTA sind eine HALBE ANGABE – zwei redaktionelle
        # Entscheidungen, die sich widersprechen. Der Vertrag aus #762 bleibt
        # unangetastet (die Ausnahme hebt nur die Mindestpflicht auf, jeder
        # vorhandene Link bleibt voll geprüft); hier wird der Widerspruch
        # aber BENANNT, bevor die Deep-Link-Prüfung mit einer irreführenden
        # Meldung antwortet. Genau daran scheiterte die Tageswache am
        # 29.10.2026: Der einzige sichtbare Satz war „Fehlt der passende
        # Deep-Link“ – die Ursache („ausgenommen, aber CTA im Text“) stand
        # nirgends. Keine Heilung: ob CTA oder Ausnahme weicht, ist eine
        # Redaktionsentscheidung.
        problems.append({
            "severity": "info",
            "msg": ("Ausnahme und CTA widersprechen sich: `affiliate_exempt: true` "
                    f"({exemption_reason}), aber der Artikel enthält "
                    f"{len(links)} Affiliate-CTA(s) – "
                    + ", ".join(cta_ziele(post["body"])[:3] or links[:3])
                    + (" …" if len(cta_ziele(post["body"])) > 3 else "")
                    + ". Die Ausnahme hebt nur die Mindestpflicht auf; CTA "
                      "entfernen oder Ausnahme zurücknehmen (Redaktionsentscheidung, "
                      "keine automatische Heilung)."),
        })
    art, deep, name = expected_target(post)

    # Partner-IDs validieren
    joined = " ".join(links)
    if re.search(r"pid=\d{4,}", joined) and "pid=80968" not in joined:
        problems.append({"severity": "error", "msg": "Fremde CHECK24-Partner-ID gefunden (pid≠80968)"})
    if re.search(r"partner_id=\d+", joined) and "partner_id=47086" not in joined:
        problems.append({"severity": "error", "msg": "Fremde Tarifcheck-Partner-ID gefunden (partner_id≠47086)"})

    if art == "check24":
        expected_url = f"{CHECK24}&deep={deep}"
        getroffen = any(expected_url in l or l == expected_url for l in links)
        if not getroffen and not post.get("is_pillar"):
            slug_title_route = affiliate_contract.route_fuer_text(
                text=post["slug"].replace("-", " "),
                titel=post.get("title", ""),
            )
            pillar_default = PILLAR_DEEP.get(post["pillar"])
            if (
                pillar_default
                and deep == pillar_default[0]
                and slug_title_route not in STRICT_PRIMARY_ROUTES
            ):
                for alt_deep, alt_name in PILLAR_DEEP_ALT.get(post["pillar"], ()):
                    alt_url = f"{CHECK24}&deep={alt_deep}"
                    if any(alt_url in l for l in links):
                        problems.append({
                            "severity": "info",
                            "msg": ("Deep-Link aus der Produktfamilie des Pillars "
                                   f"„{post['pillar']}“: {alt_name} statt {name} – "
                                   "thematisch passend, kein Fehler"),
                        })
                        getroffen = True
                        break
        if not getroffen:
            problems.append({
                "severity": "error",
                "msg": f"Fehlt der passende Deep-Link: {expected_url} (erwartet: {name})",
            })
    elif art == "tarifcheck":
        expected_url = f"{TARIFCHECK}&deep={deep}"
        if not any(expected_url in l for l in links):
            problems.append({
                "severity": "error",
                "msg": f"Fehlt der passende Tarifcheck-Deep-Link: deep={deep}",
            })
    elif art == "generic_ok":
        # generisch erlaubt, aber nur CHECK24-Basis-URL oder Tarifcheck-Basis
        if not any(l.startswith(CHECK24) or l.startswith(TARIFCHECK) for l in links):
            problems.append({"severity": "error", "msg": "Kein gültiger Affiliate-Link gefunden"})
        else:
            problems.append({
                "severity": "info",
                "msg": f"Generischer Link (erlaubt): {name} – prüfen, ob ein Deep-Link sinnvoll wäre",
            })
    return problems


def fix_post(post, dry=True):
    """Ersetzt generische CTA-Links durch passende Deep-Links (nur CHECK24-Fälle
    mit eindeutigem Mapping). Liefert Anzahl der Ersetzungen."""
    art, deep, name = expected_target(post)
    if art != "check24":
        return 0
    expected_url = f"{CHECK24}&deep={deep}"
    content = post["content"]
    # Nur die GENERISCHE Basis-URL ersetzen (nicht vorhandene Deep-Links!)
    # Achtung: CHECK24 ist Präfix von expected_url – nur exakte generische Links ersetzen
    pattern = re.compile(r"https://a\.check24\.net/misc/click\.php\?pid=80968&aid=18(?![&\w])")
    new_content, n = pattern.subn(lambda m: expected_url, content)
    if n:
        if not dry:
            open(post["path"], "w", encoding="utf-8").write(new_content)
        return n
    return 0


def _selftest_post(slug, title, pillar, body, frontmatter=""):
    return {
        "path": "(selftest)", "slug": slug, "title": title,
        "pillar": pillar, "body": body, "content": body,
        "frontmatter": frontmatter, "is_pillar": False,
    }


def selftest():
    """Eingefrorene Regressionen für Themen-vor-Pillar und Ausnahmen."""
    failures = []
    mobile = _selftest_post(
        "2026-10-07-handyvertrag-kuendigen",
        "Handyvertrag kündigen: Enddatum und Rufnummer",
        "internet-dsl",
        "👉 Jetzt Handytarife vergleichen: [Handytarife vergleichen](/go/handytarife/)",
    )
    expected = expected_target(mobile)
    if expected != ("check24", "handytarife", "Handytarife"):
        failures.append(f"Handytarif unter internet-dsl falsch zugeordnet: {expected}")
    mobile_errors = [p["msg"] for p in check_post(mobile)
                     if p["severity"] == "error"]
    if mobile_errors:
        failures.append(f"Handytarif-CTA fällt durch den Check: {mobile_errors}")

    cross_sell = _selftest_post(
        "wlan-mesh-ratgeber", "WLAN verbessern: Mesh und Empfang",
        "internet-dsl", "Ein Stromtarif kann die Fixkosten senken.",
    )
    if expected_target(cross_sell) != (
        "check24", "dsl-anbieterwechsel&cat=4", "DSL-Tarifvergleich"
    ):
        failures.append("Breite Text-/Cross-Selling-Wörter überschreiben den Pillar")

    unmarked = _selftest_post("neuer-ratgeber", "Neuer Technikratgeber", "", "DNS-Tipps.")
    if not any(p["msg"] == "KEIN Affiliate-Link vorhanden"
               for p in check_post(unmarked)):
        failures.append("Ein nicht ausgenommener Linkmangel wird nicht blockiert")

    exempt = _selftest_post(
        "dns-messtest", "DNS-Antwortzeiten testen", "internet-dsl", "Messanleitung.",
        'affiliate_exempt: true\naffiliate_exempt_reason: "Reiner DNS-Messtest ohne passendes Tarifangebot."',
    )
    exempt_problems = check_post(exempt)
    if any(p["severity"] == "error" for p in exempt_problems) or not any(
        p["severity"] == "info" and "Reiner DNS-Messtest" in p["msg"]
        for p in exempt_problems
    ):
        failures.append(f"Begründete redaktionelle Ausnahme greift nicht: {exempt_problems}")

    malformed = _selftest_post(
        "2026-10-07-handyvertrag-kuendigen",
        "Handyvertrag kündigen: Enddatum und Rufnummer",
        "internet-dsl",
        "[Jetzt DSL vergleichen](/go/dsl/)",
        "affiliate_exempt: true\n",
    )
    malformed_problems = [p["msg"] for p in check_post(malformed)
                          if p["severity"] == "error"]
    if not any("braucht eine nichtleere Begründung" in msg
               for msg in malformed_problems):
        failures.append("Eine Ausnahme ohne Begründung wird nicht fail-closed blockiert")
    if not any("Fehlt der passende Deep-Link" in msg
               for msg in malformed_problems):
        failures.append("Ungültige Ausnahmemetadaten überspringen die Linkprüfung")

    vacation_budget = _selftest_post(
        "2026-10-19-urlaubskasse-clever-aufbessern",
        "Urlaubskasse clever aufbessern",
        "mietwagen",
        "👉 Jetzt Pauschalreisen vergleichen: [Pauschalreisen vergleichen](/go/reisen/)",
    )
    vacation_expected = expected_target(vacation_budget)
    if vacation_expected[:2] != ("check24", "pauschalreisen-vergleich&cat=9"):
        failures.append(
            f"Urlaubsbudget-Ratgeber unter mietwagen falsch zugeordnet: {vacation_expected}"
        )
    vacation_errors = [p["msg"] for p in check_post(vacation_budget)
                       if p["severity"] == "error"]
    if vacation_errors:
        failures.append(f"Urlaubsbudget-CTA (/go/reisen/) fällt durch den Check: {vacation_errors}")

    strict_mietwagen = _selftest_post(
        "2026-10-21-mietwagen-fallen-im-urlaub-vermeiden",
        "Mietwagen-Fallen im Urlaub vermeiden",
        "mietwagen",
        "[Pauschalreisen vergleichen](/go/reisen/)",
    )
    strict_mietwagen_errors = [p["msg"] for p in check_post(strict_mietwagen)
                               if p["severity"] == "error"]
    if not any("mietwagen-preisvergleich&cat=10" in msg for msg in strict_mietwagen_errors):
        failures.append(
            "Reiner Mietwagen-Ratgeber darf nicht über PILLAR_DEEP_ALT auf /go/reisen/ ausweichen"
        )

    registered_targets = {
        (t[0], t[1])
        for route in _REGISTRY
        for t in (_target_from_registered_route(route),)
        if t and t[1] is not None
    }
    for label, mapping in (
        ("SLUG_DEEP", SLUG_DEEP),
        ("PILLAR_DEEP", {k: v for k, v in PILLAR_DEEP.items() if v is not None}),
        ("PILLAR_PAGE_DEEP", {k: v for k, v in PILLAR_PAGE_DEEP.items() if v is not None}),
    ):
        for key, (deep_val, _name) in mapping.items():
            if ("check24", deep_val) not in registered_targets:
                failures.append(f"{label}[{key!r}] verweist auf nicht registrierten Deep-Link: {deep_val}")
    for pillar_key, entries in PILLAR_DEEP_ALT.items():
        for deep_val, _name in entries:
            if ("check24", deep_val) not in registered_targets:
                failures.append(
                    f"PILLAR_DEEP_ALT[{pillar_key!r}] verweist auf nicht registrierten Deep-Link: {deep_val}"
                )
    for label, mapping in (
        ("TARIF_SLUG_DEEP", TARIF_SLUG_DEEP),
        ("TARIF_SLUG_DEEP_EXTRA", TARIF_SLUG_DEEP_EXTRA),
    ):
        for key, deep_val in mapping.items():
            if ("tarifcheck", deep_val) not in registered_targets:
                failures.append(f"{label}[{key!r}] verweist auf nicht registrierten Tarifcheck-Deep: {deep_val}")

    if failures:
        print("Affiliate-Link-Check Selbsttest: FEHLER")
        for failure in failures:
            print(f"  ❌ {failure}")
        return 2
    print("Affiliate-Link-Check Selbsttest: 8 Verträge grün")
    return 0


def main():
    if "--selftest" in sys.argv:
        return selftest()

    fix = "--fix" in sys.argv
    as_json = "--json" in sys.argv
    posts = load_posts()

    results = []
    for post in posts:
        problems = check_post(post)
        fixed = 0
        if fix and any(p["severity"] == "error" for p in problems):
            fixed = fix_post(post, dry=False)
            if fixed:
                # nach Fix neu prüfen
                post["content"] = open(post["path"], encoding="utf-8").read()
                parts = post["content"].split("---", 2)
                post["body"] = parts[2] if len(parts) == 3 else ""
                problems = check_post(post)
        errors = [p for p in problems if p["severity"] == "error"]
        infos = [p for p in problems if p["severity"] == "info"]
        results.append({
            "slug": post["slug"], "title": post["title"][:50],
            "pillar": post["pillar"], "fixed": fixed,
            "errors": [p["msg"] for p in errors],
            "infos": [p["msg"] for p in infos],
            "ok": not errors,
        })

    total = len(results)
    errors_total = sum(1 for r in results if not r["ok"])
    fixed_total = sum(r["fixed"] for r in results)

    # Report
    lines = [
        "# 🔗 Affiliate-Link-Report", "",
        f"> **Automatisch** – {total} Posts geprüft, {errors_total} mit Problemen, {fixed_total} Links korrigiert.",
        "",
        "## Zusammenfassung", "",
        f"- ✅ Korrekt: {total - errors_total}/{total}",
        f"- ❌ Mit Problemen: {errors_total}",
        f"- 🔧 Korrigiert (--fix): {fixed_total}",
        "",
    ]
    if errors_total:
        lines += ["## ❌ Probleme", ""]
        for r in results:
            if not r["ok"]:
                lines.append(f"### {r['slug']}")
                for e in r["errors"]:
                    lines.append(f"- ❌ {e}")
                lines.append("")
    infos = [(r, i) for r in results for i in r["infos"]]
    if infos:
        lines += ["## ℹ️ Hinweise", ""]
        for r, i in infos:
            lines.append(f"- {r['slug']}: {i}")
        lines.append("")
    lines += ["---", "*Erzeugt von scripts/affiliate_link_check.py*", ""]
    open(REPORT_FILE, "w", encoding="utf-8").write("\n".join(lines))
    json.dump({"total": total, "errors": errors_total, "fixed": fixed_total,
               "posts": results}, open(JSON_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"Affiliate-Link-Check: {total} Posts | Probleme: {errors_total} | Korrigiert: {fixed_total}")
    if as_json:
        print(json.dumps({"total": total, "errors": errors_total, "fixed": fixed_total,
                          "posts": results}, ensure_ascii=False))
    for r in results:
        if not r["ok"]:
            print(f"  ❌ {r['slug']}: {'; '.join(r['errors'])}")
    for r, i in infos:
        print(f"  ℹ️ {r['slug']}: {i}")
    return 1 if errors_total else 0


if __name__ == "__main__":
    sys.exit(main())
