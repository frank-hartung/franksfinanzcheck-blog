"""Affiliate-Link-Checker (vollautomatisch, Top-Level) für FranksFinanzcheck.

Prüft ALLE Posts auf:
  1) Vorhandensein: Jeder Post braucht mindestens einen Affiliate-Link.
  2) DEEP-LINK-KORREKTHEIT: Der Post muss auf den THEMATISCH PASSENDEN
     Deep-Link verlinken (Slug-Mapping + Pillar-Fallback). Ein generischer
     Link ohne deep= ist nur für thematisch breite Posts erlaubt
     (frugalismus, tier) – dort wird er im Report markiert.
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

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
    "guenstige-fluege-spaetsommer-finden": ("flugvergleich", "Flugvergleich"),
    "last-minute-urlaubsangebote-sichern": ("pauschalreisen-vergleich&cat=9", "Pauschalreisen-Vergleich"),
    "urlaubskasse-aufbessern-spartipps": ("pauschalreisen-vergleich&cat=9", "Pauschalreisen-Vergleich"),
    # Konto & Karten
    "kostenloses-girokonto-finden": ("c24bank&cat=14", "C24 Girokonto"),
    "notgroschen-aufbauen-wie-viel-reicht": ("c24bank&cat=14", "C24 Girokonto"),
    "kreditkarte-ohne-jahresgebuehr": ("kreditkarte", "Kreditkarten-Vergleich"),
    "ratenkredit-bestszins-vergleichen": ("kreditvergleich", "Kreditvergleich"),
    "tagesgeld-zinsen-sicher-anlegen": ("tagesgeldvergleich", "Tagesgeld-Vergleich"),
    # Versicherungen (CHECK24)
    "kfz-versicherung-wechseln": ("kfz-versicherung", "Kfz-Versicherung"),
    # Zusaetzliche Artikel (thematisch korrekte Deep-Links)
    "heizkosten-senken-10-massnahmen": ("gasanbieter-wechseln&cat=3", "Gastarif-Vergleich"),
    "nachtspeicherheizung-wechseln-oder-behalten": ("gasanbieter-wechseln&cat=3", "Gastarif-Vergleich"),
    "2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas": ("gasanbieter-wechseln&cat=3", "Gastarif-Vergleich"),
    "2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026": ("gasanbieter-wechseln&cat=3", "Gastarif-Vergleich"),
    "2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden": ("gasanbieter-wechseln&cat=3", "Gastarif-Vergleich"),
    "5g-home-router-oder-dsl": ("handytarife", "Handytarif-Vergleich"),
    "2026-08-10-dsl-wechselbonus-sichern": ("dsl-anbieterwechsel&cat=4", "DSL-Tarifvergleich"),
    "flug-buchen-9-tricks-guenstige-tickets": ("flugvergleich", "Flugvergleich"),
    "pauschalreise-buchen-bester-zeitpunkt": ("pauschalreisen-vergleich&cat=9", "Pauschalreisen-Vergleich"),
    "urlaub-mit-kindern-guenstig-spartricks": ("pauschalreisen-vergleich&cat=9", "Pauschalreisen-Vergleich"),
    "mietwagen-im-winter-schnaeppchen-tricks": ("mietwagen-preisvergleich&cat=10", "Mietwagen-Vergleich"),
    "festgeld-oder-tagesgeld-2026": ("tagesgeldvergleich", "Tagesgeld-Vergleich"),
    "dispozinsen-verstehen-alternativen": ("kreditvergleich", "Kreditvergleich"),
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


def load_posts():
    posts = []
    pillar_dir = os.path.join(BLOG_DIR, "content", "pillar")
    for path in sorted(glob.glob(os.path.join(POSTS_DIR, "*", "index.md"))
                       + glob.glob(os.path.join(pillar_dir, "*", "index.md"))):
        content = open(path, encoding="utf-8").read()
        parts = content.split("---", 2)
        if len(parts) < 3:
            continue
        fm, body = parts[1], parts[2]
        if "draft: true" in fm:
            continue

        def get(key):
            m = re.search(rf'^{key}:\s*["\']?(.+?)["\']?\s*$', fm, re.M)
            return m.group(1).strip() if m else ""

        slug = os.path.basename(os.path.dirname(path))
        is_pillar = "/pillar/" in path
        posts.append({
            "path": path, "slug": slug, "title": get("title"),
            "pillar": get("pillar").strip('"'), "body": body, "content": content,
            "is_pillar": is_pillar,
        })
    return posts


import yaml

def _load_registry():
    yf = os.path.join(BLOG_DIR, "scripts", "check24_links.yaml")
    if os.path.exists(yf):
        with open(yf, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return data.get("links", {})
    return {}

_REGISTRY = _load_registry()


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
    problems = []
    links = find_affiliate_links(post["body"])
    if not links:
        problems.append({"severity": "error", "msg": "KEIN Affiliate-Link vorhanden"})
        return problems

    art, deep, name = expected_target(post)

    # Partner-IDs validieren
    joined = " ".join(links)
    if re.search(r"pid=\d{4,}", joined) and "pid=80968" not in joined:
        problems.append({"severity": "error", "msg": "Fremde CHECK24-Partner-ID gefunden (pid≠80968)"})
    if re.search(r"partner_id=\d+", joined) and "partner_id=47086" not in joined:
        problems.append({"severity": "error", "msg": "Fremde Tarifcheck-Partner-ID gefunden (partner_id≠47086)"})

    if art == "check24":
        expected_url = f"{CHECK24}&deep={deep}"
        if not any(expected_url in l or l == expected_url for l in links):
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
    generic = CHECK24  # ohne deep
    # Achtung: CHECK24 ist Präfix von expected_url – nur exakte generische Links ersetzen
    pattern = re.compile(r"https://a\.check24\.net/misc/click\.php\?pid=80968&aid=18(?![&\w])")
    new_content, n = pattern.subn(lambda m: expected_url, content)
    if n:
        if not dry:
            open(post["path"], "w", encoding="utf-8").write(new_content)
        return n
    return 0


def main():
    fix = "--fix" in sys.argv
    as_json = "--json" in sys.argv
    posts = load_posts()

    results = []
    for post in posts:
        problems = check_post(post)
        fixed = 0
        if fix and problems:
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
        lines += ["## ℹ️ Generische Links (erlaubt, aber prüfen)", ""]
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
