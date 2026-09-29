#!/usr/bin/env python3
"""index_hygiene_gate.py – PREMIUM-GATE: Crawl-Fläche und Indexierbarkeit.

WARUM DIESE WACHE EXISTIERT (Befund 29.09.2026)
Die Google Search Console meldete 237 nicht indexierte Seiten. Kein einziger
Artikel war schuld – die Site baute schlicht viel mehr URLs, als sie Inhalte
hat. Gemessen im Build vom 29.09.2026, VOR der Reparatur:

    58 indexierbare Seiten  ·  347 nicht indexierbare URLs   (Verhältnis 1 : 6,0)
      147  Tag-Archive (193 Roh-Tags mit genau EINEM Artikel)
      154  /page/1/-Alias-Weiterleitungen (Hugo-Automatik, nirgends verlinkt)
       20  /go/-Affiliate-Weiterleitungen (gewollt, per robots.txt gesperrt)
       14  Pager-Seiten
        6  Kategorie-Archive + 404 + Newsletter-Funnel

Die bestehenden Wachen prüften jede Seite EINZELN und korrekt (schema_seo_gate
S6: „Archive tragen noindex" war grün). Niemand prüfte die MENGE. Genau das ist
die Lücke, die diese Wache schließt: nicht „ist die Seite richtig ausgezeichnet",
sondern „darf es diese Seite überhaupt geben".

Denkmodell: jede gebaute URL kostet Crawl-Budget. Eine URL, die weder indexiert
werden soll noch von Menschen benutzt wird, ist ein Verlustgeschäft.

REGELWERK (harte Funde => Exit 1):
  H1  Sitemap-Deckung – jede indexierbare Seite steht in der Sitemap
                        (Ausnahme: Verifikationsdateien in VERIFIKATION)
  H2  Aliase          – keine /page/1/-Weiterleitungen im Build
                        (hugo.toml: [pagination] disableAliases = true)
  H3  Tag-Archive     – Anzahl <= budget.max_tag_archive (seit 29.09.2026: 0,
                        die Taxonomie `tags` ist abgeschaltet)
  H4  Kategorien      – keine /categories/-Archive (Taxonomie abgeschaltet)
  H5  Verhältnis      – nicht-indexierbare URLs <= budget.max_verhaeltnis
                        mal indexierbare Seiten
  H6  Slugs           – keine Prozent-Kodierung und kein doppelter Bindestrich
                        in Taxonomie-URLs (kaputte Tag-Namen)
  H7  Waisen          – jede indexierbare Seite ist intern verlinkt
  H8  Noindex-Lecks   – keine noindex-URL steht in der Sitemap

Selbstheilung: bewusst KEIN --fix. Jeder Fund ist eine Architektur- oder
Konfigurationsentscheidung (Taxonomie, Pagination, Sitemap) – das entscheidet
die Redaktion, nicht eine Wache.

Nutzung:
    hugo --destination public
    python3 scripts/index_hygiene_gate.py            # prüft public/
    python3 scripts/index_hygiene_gate.py --json     # Maschinen-Ausgabe
    python3 scripts/index_hygiene_gate.py --selftest # 8 Fälle

Exit: 0 = grün · 1 = harte Funde · 2 = Fehler/Selbsttest fehlgeschlagen
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from urllib.parse import unquote, urlparse

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC = os.environ.get("INDEX_GATE_BASE", os.path.join(BLOG_DIR, "public"))

# Besitznachweise für Suchmaschinen/Pinterest: indexierbar, aber kein Inhalt.
# Sie gehören nicht in die Sitemap und sind keine Waisenseiten.
VERIFIKATION = re.compile(
    r"^/(google[0-9a-f]+\.html|pinterest-[0-9a-f]+\.html|BingSiteAuth\.xml)$")

# Budget der Crawl-Fläche.
#
# max_tag_archive = 0: Die Taxonomie `tags` ist seit 29.09.2026 in hugo.toml
# abgeschaltet (Entscheidung Frank). Es DARF kein /tags/-Archiv mehr entstehen –
# taucht doch eines auf, hat jemand den `[taxonomies]`-Block wieder befüllt.
# Das ist dann eine bewusste Architekturänderung und muss hier mitgezogen
# werden, nicht stillschweigend durchrutschen.
#
# max_verhaeltnis = 1.0: Ist nach der Reparatur 0,66 (38 : 58). Vorher 5,98.
# Der Puffer bis 1.0 trägt normales Wachstum (jeder neue Artikel bringt eine
# indexierbare Seite und ggf. eine Pager-Seite), schlägt aber an, bevor sich
# wieder eine ganze URL-Klasse unbemerkt aufbaut.
BUDGET = {
    "max_tag_archive": 0,       # Taxonomie abgeschaltet · Ist: 0 · vorher: 147
    "max_verhaeltnis": 1.0,     # Ist: 0,66 · vor der Reparatur: 5,98
}


class Funde:
    def __init__(self) -> None:
        self.hart: list[tuple[str, str, str]] = []
        self.weich: list[tuple[str, str, str]] = []

    def add(self, regel: str, wo: str, text: str) -> None:
        self.hart.append((regel, wo, text))

    def warn(self, regel: str, wo: str, text: str) -> None:
        self.weich.append((regel, wo, text))


# ---------------------------------------------------------------------------
def rel_url(pfad: str, basis: str) -> str:
    rel = "/" + os.path.relpath(pfad, basis).replace(os.sep, "/")
    return rel[: -len("index.html")] if rel.endswith("index.html") else rel


def ist_alias(html: str) -> bool:
    return bool(re.search(r'http-equiv=["\']?refresh', html, re.I))


def robots_wert(html: str) -> str:
    m = re.search(r'<meta[^>]+name=["\']?robots["\']?[^>]*content=["\']([^"\']*)',
                  html, re.I)
    return (m.group(1) if m else "").lower()


# href-Werte in drei Schreibweisen. Die dritte ist Pflicht, weil Produktion mit
# `hugo --minify` baut und der Minifier die Anführungszeichen entfernt
# (`href=https://…`). Ohne diesen Zweig meldet H7 im echten Deploy jede zweite
# Seite als Waise – ein Fehlalarm, der die Wache wertlos machen würde.
HREF = re.compile(r"""<a\b[^>]*?\bhref\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))""",
                  re.I | re.S)


def interne_ziele(html: str) -> set[str]:
    """Alle internen href-Ziele einer Seite, auf Pfad normalisiert."""
    ziele: set[str] = set()
    for m in HREF.finditer(html):
        h = (m.group(1) or m.group(2) or m.group(3) or "").strip()
        h = h.split("#", 1)[0]
        if not h:
            continue
        if h.startswith(("mailto:", "tel:", "javascript:", "data:")):
            continue
        if h.startswith("http"):
            p = urlparse(h)
            if "franksfinanzcheck.de" not in (p.netloc or ""):
                continue
            h = p.path or "/"
        else:
            h = urlparse(h).path or "/"
        if not h.startswith("/"):
            continue
        ziele.add(unquote(h))
    return ziele


def sammle(basis: str) -> dict:
    seiten: dict[str, dict] = {}
    verlinkt: set[str] = set()
    for root, _dirs, files in os.walk(basis):
        for f in files:
            if not f.endswith(".html"):
                continue
            p = os.path.join(root, f)
            try:
                html = open(p, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            url = rel_url(p, basis)
            alias = ist_alias(html)
            rb = robots_wert(html)
            seiten[url] = {
                "alias": alias,
                "robots": rb,
                "indexierbar": (not alias) and "noindex" not in rb,
            }
            if not alias:
                verlinkt |= interne_ziele(html)
    return {"seiten": seiten, "verlinkt": verlinkt}


def sitemap_urls(basis: str) -> set[str] | None:
    pfad = os.path.join(basis, "sitemap.xml")
    if not os.path.exists(pfad):
        return None
    roh = open(pfad, encoding="utf-8", errors="ignore").read()
    out = set()
    for u in re.findall(r"<loc>\s*(.*?)\s*</loc>", roh, re.S):
        out.add(unquote(urlparse(u.strip()).path or "/"))
    return out


# ---------------------------------------------------------------------------
def pruefe(basis: str = PUBLIC, budget: dict | None = None) -> tuple[Funde, dict]:
    F = Funde()
    b = dict(BUDGET)
    b.update(budget or {})

    if not os.path.isdir(basis):
        F.add("H0", basis, "Build-Verzeichnis fehlt – zuerst `hugo` laufen lassen")
        return F, {}

    daten = sammle(basis)
    seiten, verlinkt = daten["seiten"], daten["verlinkt"]
    sm = sitemap_urls(basis)

    indexierbar = {u for u, d in seiten.items() if d["indexierbar"]}
    aliase = {u for u, d in seiten.items() if d["alias"]}
    noindex = {u for u, d in seiten.items() if not d["alias"] and not d["indexierbar"]}
    tag_archive = {u for u in noindex if u.startswith("/tags/")
                   and not re.search(r"/page/\d+/$", u)}
    kategorie = {u for u in seiten if u.startswith("/categories/")}
    pager = {u for u in seiten if re.search(r"/page/\d+/$", u)}
    pager_eins = {u for u in seiten if re.search(r"/page/1/$", u)}
    go = {u for u in aliase if u.startswith("/go/")}

    # ---- H1: Sitemap-Deckung ----
    if sm is None:
        F.add("H1", "/sitemap.xml", "sitemap.xml fehlt im Build")
    else:
        for u in sorted(indexierbar):
            if VERIFIKATION.match(u):
                continue
            if u not in sm:
                F.add("H1", u, "indexierbare Seite fehlt in der Sitemap "
                               "(nur über interne Links auffindbar)")
        # ---- H8: noindex-Leck in der Sitemap ----
        for u in sorted(sm):
            d = seiten.get(u)
            if d is None:
                F.warn("H8", u, "Sitemap-URL ohne Datei im Build")
            elif not d["indexierbar"]:
                F.add("H8", u, "nicht indexierbare URL steht in der Sitemap "
                               "(widersprüchliches Signal an Google)")

    # ---- H2: /page/1/-Aliase ----
    for u in sorted(pager_eins):
        F.add("H2", u, "/page/1/-Weiterleitung im Build – "
                       "hugo.toml: [pagination] disableAliases = true fehlt")

    # ---- H3: Tag-Archive ----
    if len(tag_archive) > b["max_tag_archive"]:
        if b["max_tag_archive"] == 0:
            F.add("H3", "/tags/",
                  f"{len(tag_archive)} Tag-Archive im Build, erlaubt sind 0 – "
                  f"die Taxonomie `tags` ist in hugo.toml bewusst abgeschaltet "
                  f"(Themen-Navigation läuft über themenwelt_chips.html)")
        else:
            F.add("H3", "/tags/",
                  f"{len(tag_archive)} Tag-Archive (Budget: {b['max_tag_archive']}) – "
                  f"Taxonomie wuchert, siehe data/seo/tag_register.yaml")

    # ---- H4: Kategorie-Archive ----
    for u in sorted(kategorie):
        F.add("H4", u, "Kategorie-Archiv im Build – die Taxonomie `category` "
                       "ist in hugo.toml bewusst abgeschaltet")

    # ---- H5: Verhältnis ----
    nicht_idx = len(seiten) - len(indexierbar)
    verh = (nicht_idx / len(indexierbar)) if indexierbar else float("inf")
    if verh > b["max_verhaeltnis"]:
        F.add("H5", "/",
              f"{nicht_idx} nicht indexierbare URLs auf {len(indexierbar)} "
              f"indexierbare = Verhältnis {verh:.2f} "
              f"(Budget: {b['max_verhaeltnis']:.2f})")

    # ---- H6: kaputte Slugs ----
    for u in sorted(tag_archive):
        if "%" in u:
            F.add("H6", u, "prozent-kodierter Tag-Slug – Tag-Name enthält ein "
                           "Sonderzeichen (siehe tag_register.yaml)")
        if "--" in u:
            F.add("H6", u, "doppelter Bindestrich im Tag-Slug – Tag-Name endet "
                           "auf Bindestrich oder enthält ' - '")

    # ---- H7: Waisen ----
    for u in sorted(indexierbar):
        if u in ("/", "/404.html") or VERIFIKATION.match(u):
            continue
        if u not in verlinkt:
            F.warn("H7", u, "indexierbare Seite ohne internen Link "
                            "(nur über die Sitemap erreichbar)")

    bericht = {
        "html_gesamt": len(seiten),
        "indexierbar": len(indexierbar),
        "nicht_indexierbar": nicht_idx,
        "verhaeltnis": round(verh, 2) if indexierbar else None,
        "tag_archive": len(tag_archive),
        "kategorie_archive": len(kategorie),
        "pager": len(pager),
        "pager_eins": len(pager_eins),
        "aliase": len(aliase),
        "go_weiterleitungen": len(go),
        "noindex": len(noindex),
        "sitemap_eintraege": len(sm) if sm is not None else None,
        "budget": b,
    }
    return F, bericht


# ---------------------------------------------------------------------------
def drucke(F: Funde, b: dict) -> None:
    print("=" * 66)
    print(" INDEX-HYGIENE – Crawl-Fläche des Builds")
    print("=" * 66)
    if not b:
        return
    print(f"  HTML-URLs gesamt ........... {b['html_gesamt']}")
    print(f"  davon indexierbar .......... {b['indexierbar']}")
    print(f"  davon NICHT indexierbar .... {b['nicht_indexierbar']}"
          f"   (Verhältnis {b['verhaeltnis']} : 1, Budget {b['budget']['max_verhaeltnis']})")
    print()
    print(f"    Tag-Archive .............. {b['tag_archive']:4d}"
          f"   (Budget {b['budget']['max_tag_archive']})")
    print(f"    Kategorie-Archive ........ {b['kategorie_archive']:4d}")
    print(f"    Pager-Seiten ............. {b['pager']:4d}")
    print(f"    /page/1/-Aliase .......... {b['pager_eins']:4d}")
    print(f"    /go/-Weiterleitungen ..... {b['go_weiterleitungen']:4d}   (gewollt)")
    print(f"    Sitemap-Einträge ......... {b['sitemap_eintraege']}")
    if F.weich:
        print(f"\n  Hinweise ({len(F.weich)}):")
        for r, wo, t in F.weich[:30]:
            print(f"    [{r}] {wo}: {t}")
        if len(F.weich) > 30:
            print(f"    … {len(F.weich) - 30} weitere")
    if F.hart:
        print(f"\n  HARTE FUNDE ({len(F.hart)}):")
        for r, wo, t in F.hart[:60]:
            print(f"    [{r}] {wo}: {t}")
        if len(F.hart) > 60:
            print(f"    … {len(F.hart) - 60} weitere")


# ---------------------------------------------------------------------------
def selftest() -> int:
    import tempfile
    ok, fehl = 0, []

    def check(name: str, cond: bool) -> None:
        nonlocal ok
        if cond:
            ok += 1
        else:
            fehl.append(name)

    IDX = ('<html><head><meta name="robots" content="index, follow">'
           '</head><body><a href="{links}">x</a></body></html>')
    NOIDX = ('<html><head><meta name="robots" content="noindex, follow">'
             "</head><body></body></html>")
    ALIAS = '<html><head><meta http-equiv="refresh" content="0; url=/"></head></html>'

    def baue(tmp: str, seiten: dict[str, str], sm: list[str] | None) -> None:
        for url, html in seiten.items():
            p = os.path.join(tmp, url.strip("/"), "index.html") if url.endswith("/") \
                else os.path.join(tmp, url.lstrip("/"))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w", encoding="utf-8").write(html)
        if sm is not None:
            locs = "".join(f"<url><loc>https://franksfinanzcheck.de{u}</loc></url>"
                           for u in sm)
            open(os.path.join(tmp, "sitemap.xml"), "w", encoding="utf-8").write(
                f"<urlset>{locs}</urlset>")

    # 1 sauberer Build ist grün
    with tempfile.TemporaryDirectory() as t:
        baue(t, {"/": IDX.format(links="/a/"), "/a/": IDX.format(links="/")},
             ["/", "/a/"])
        F, b = pruefe(t)
        check("sauberer Build grün", not F.hart)

    # 1b MINIFIZIERTES HTML (Produktion baut mit `hugo --minify`): der Minifier
    #     entfernt die Anführungszeichen um Attributwerte. Erkennt die Wache
    #     `href=/a/` nicht, meldet H7 im Deploy massenhaft Falsch-Waisen.
    with tempfile.TemporaryDirectory() as t:
        mini_root = ('<html><head><meta name=robots content="index, follow">'
                     "</head><body><a href=/a/ title=x>a</a></body></html>")
        mini_a = ('<html><head><meta name=robots content="index, follow">'
                  "</head><body><a href=https://franksfinanzcheck.de/ >h</a></body></html>")
        baue(t, {"/": mini_root, "/a/": mini_a}, ["/", "/a/"])
        F, _ = pruefe(t)
        check("minifiziertes HTML: keine Falsch-Waisen",
              not any(r == "H7" for r, _, _ in F.weich))
    # 2 Zählung stimmt
    check("Zählung indexierbar", b["indexierbar"] == 2 and b["nicht_indexierbar"] == 0)

    # 3 H1 fehlende Sitemap-Deckung
    with tempfile.TemporaryDirectory() as t:
        baue(t, {"/": IDX.format(links="/a/"), "/a/": IDX.format(links="/")}, ["/"])
        F, _ = pruefe(t)
        check("H1 fehlt in Sitemap", any(r == "H1" for r, _, _ in F.hart))

    # 4 H2 /page/1/-Alias
    with tempfile.TemporaryDirectory() as t:
        baue(t, {"/": IDX.format(links="/"), "/page/1/": ALIAS}, ["/"])
        F, _ = pruefe(t)
        check("H2 page/1-Alias", any(r == "H2" for r, _, _ in F.hart))

    # 5 H3 Tag-Budget
    with tempfile.TemporaryDirectory() as t:
        s = {"/": IDX.format(links="/")}
        for i in range(40):
            s[f"/tags/t{i}/"] = NOIDX
        baue(t, s, ["/"])
        F, _ = pruefe(t)
        check("H3 Tag-Budget", any(r == "H3" for r, _, _ in F.hart))

    # 5b Seit dem Abschalten der Taxonomie ist bereits EIN Archiv ein Fund.
    #    Ohne diesen Fall würde ein versehentlich wieder befüllter
    #    [taxonomies]-Block mit wenigen Tags unter einem alten Budget durchrutschen.
    with tempfile.TemporaryDirectory() as t:
        baue(t, {"/": IDX.format(links="/"), "/tags/eines/": NOIDX}, ["/"])
        F, _ = pruefe(t)
        check("H3 ein einzelnes Tag-Archiv reicht",
              any(r == "H3" for r, _, _ in F.hart))

    # 6 H4 Kategorie-Archiv
    with tempfile.TemporaryDirectory() as t:
        baue(t, {"/": IDX.format(links="/"), "/categories/x/": NOIDX}, ["/"])
        F, _ = pruefe(t)
        check("H4 Kategorie", any(r == "H4" for r, _, _ in F.hart))

    # 7 H6 kaputter Slug
    with tempfile.TemporaryDirectory() as t:
        baue(t, {"/": IDX.format(links="/"), "/tags/a%C3%BC/": NOIDX}, ["/"])
        F, _ = pruefe(t)
        check("H6 Prozent-Slug", any(r == "H6" for r, _, _ in F.hart))

    # 8 H8 noindex in der Sitemap
    with tempfile.TemporaryDirectory() as t:
        baue(t, {"/": IDX.format(links="/x/"), "/x/": NOIDX}, ["/", "/x/"])
        F, _ = pruefe(t)
        check("H8 noindex in Sitemap", any(r == "H8" for r, _, _ in F.hart))

    print(f"Selbsttest: {ok} bestanden, {len(fehl)} fehlgeschlagen")
    for f in fehl:
        print(f"  ✗ {f}")
    return 0 if not fehl else 2


def main() -> int:
    ap = argparse.ArgumentParser(description="Wache für die Crawl-Fläche")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--base", default=PUBLIC)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    F, b = pruefe(a.base)
    if a.json:
        print(json.dumps({
            "hart": [{"regel": r, "wo": w, "text": t} for r, w, t in F.hart],
            "weich": [{"regel": r, "wo": w, "text": t} for r, w, t in F.weich],
            "bericht": b,
        }, ensure_ascii=False, indent=2))
        return 1 if F.hart else 0
    drucke(F, b)
    if F.hart:
        print(f"\n✗ {len(F.hart)} harte Funde – Crawl-Fläche nicht sauber.")
        return 1
    print("\n✓ Crawl-Fläche sauber: jede gebaute URL ist gewollt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
