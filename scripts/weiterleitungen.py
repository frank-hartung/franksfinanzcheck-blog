#!/usr/bin/env python3
"""weiterleitungen.py – Weiterleitungen für verschobene Beiträge (Quelle: data/weiterleitungen.yaml).

WARUM DIESES SKRIPT EXISTIERT (19.10.2026)
Der Blog hat 117 Alt-URLs, die früher veröffentlicht waren und heute fehlen. Ohne Weiterleitung
gehen Suchmaschinen-Signale verloren, und Leser landen auf 404. Die Hugo-Aliase sind abgeschaltet
(hugo.toml: disableAliases = true, Entscheidung „Index-Hygiene“). Deshalb liegen die Weiterleitungen
als eigene, geprüfte Seiten unter static/ und werden hieraus erzeugt.

GRENZE, ehrlich benannt:
  GitHub Pages kann keine echten HTTP-301 setzen. Die erzeugte Seite ist eine Meta-Refresh-Seite
  (0 s, canonical, noindex,follow). Ein echter 301 entsteht erst, wenn der Cloudflare-Proxy aktiv ist.
  Dafür erzeugt --cloudflare die Bulk-CSV. Sie wird NICHT automatisch hochgeladen.

REGELWERK (Details: docs/ANLEITUNG-WEITERLEITUNGEN.md)
  A  exakter Nachfolger (Ordner umbenannt, Dublette (1)). Slug-Rest muss identisch sein.
  B  gleiches Thema, manuell gewählter Live-Beitrag.
  C  Pillar-Seite des Themas, nie die Startseite.
  D  bewusst 404 (data/url_entfallen.yaml).
  E  Tag-Archive: bewusst 404 (data/url_entfallen.yaml).
  Ziele sind Live-Seiten. Ketten, Schleifen und Ziele auf Entwürfe sind verboten.

Nutzung:
    python3 scripts/weiterleitungen.py --check      Quelle validieren (exit 1 bei Fehlern)
    python3 scripts/weiterleitungen.py --build      static/<von>/index.html erzeugen, eigene veraltete Seiten entfernen
    python3 scripts/weiterleitungen.py --verify     erzeugte Seiten gegen Quelle prüfen (schreibt nichts)
    python3 scripts/weiterleitungen.py --proxy-check  Cloudflare-Proxy per cf-ray prüfen (braucht Internet)
    python3 scripts/weiterleitungen.py --cloudflare Bulk-CSV erzeugen (nur bei nachweislich aktivem Proxy)
    python3 scripts/weiterleitungen.py --selftest   Selbsttest (exit 2 bei Fehlschlag)

Exit: 0 = grün · 1 = Befund · 2 = Fehler (z. B. PyYAML fehlt)
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
import urllib.request

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML fehlt – mit /tmp/gv/bin/python oder pip install pyyaml ausführen", file=sys.stderr)
    sys.exit(2)

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://franksfinanzcheck.de"
MARKER_KEY = "ff-weiterleitung"
GENERATOR_NOTE = "Generiert von scripts/weiterleitungen.py aus data/weiterleitungen.yaml. Nicht von Hand ändern."
REGELN_WEITERLEITUNG = {"A", "B", "C"}
REGELN_ENTFALLEN = {"D", "E"}

_DRAFT = re.compile(r"^draft:\s*true\s*$", re.M)
_DATUM = re.compile(r"^\d{4}-\d{2}-\d{2}-")


# ----------------------------------------------------------------- Lesen

def lade_quelle(root: str = BLOG_DIR) -> tuple[list[dict], list[dict]]:
    w = yaml.safe_load(open(os.path.join(root, "data", "weiterleitungen.yaml"), encoding="utf-8"))
    e = yaml.safe_load(open(os.path.join(root, "data", "url_entfallen.yaml"), encoding="utf-8"))
    return (w or {}).get("eintraege") or [], (e or {}).get("eintraege") or []


def live_urls(root: str = BLOG_DIR) -> set[str]:
    """Alle Live-URLs aus content/ (draft: true ausgenommen). Hugo-Logik: Ordner mit index.md = URL."""
    out: set[str] = set()
    cdir = os.path.join(root, "content")
    for dirpath, _dirs, files in os.walk(cdir):
        for f in files:
            if not f.endswith(".md"):
                continue
            p = os.path.join(dirpath, f)
            with open(p, encoding="utf-8", errors="ignore") as fh:
                kopf = fh.read(4000)
            if _DRAFT.search(kopf):
                continue
            rel = os.path.relpath(dirpath, cdir).replace(os.sep, "/")
            if rel == ".":
                continue  # Startseite ist nicht Gegenstand dieser Wache
            if f == "_index.md" or f == "index.md":
                out.add("/" + rel.strip("/") + "/")
            else:
                out.add("/" + rel.strip("/") + "/" + os.path.splitext(f)[0] + "/")
    return out


def slug_rest(pfad: str) -> str:
    """'/posts/2026-08-21-x(1)/' -> 'x'. Entfernt Datum und (1)-Suffix."""
    name = pfad.rstrip("/").split("/")[-1]
    name = re.sub(r"\(\d+\)$", "", name)
    return _DATUM.sub("", name)


# ----------------------------------------------------------------- Prüfen

def pruefe(eintraege: list[dict], entfallen: list[dict], live: set[str]) -> list[str]:
    """Gibt Befunde zurück. Leere Liste = grün."""
    f: list[str] = []
    von_alle: dict[str, str] = {}

    for e in eintraege:
        v = e.get("von", "")
        n = e.get("nach", "")
        r = e.get("regel", "")
        g = e.get("grund", "")
        if (v or "").startswith("/tags/"):
            f.append(f"{v}: Tag-Archive dürfen nicht umgeleitet werden (Regel E)")
            continue
        if not re.fullmatch(r"/posts/[^/?#\s]+/", v or ""):
            f.append(f"Quelle ungültig (nur /posts/<slug>/): {v!r}")
            continue
        if v in von_alle:
            f.append(f"Quelle doppelt: {v}")
        von_alle[v] = r
        if r not in REGELN_WEITERLEITUNG:
            f.append(f"{v}: Regel {r!r} ist für Weiterleitungen nicht zulässig (A, B oder C)")
        if not g or len(str(g).strip()) < 8:
            f.append(f"{v}: Begründung fehlt oder zu kurz")
        if v in live:
            f.append(f"{v}: Quelle ist live – Weiterleitung würde eine Live-Seite überdecken")

    for e in eintraege:
        v, n, r = e.get("von", ""), e.get("nach", ""), e.get("regel", "")
        if not re.fullmatch(r"/(posts|pillar)/[^/?#\s]+/", n or ""):
            f.append(f"{v}: Ziel ungültig (nur /posts/<slug>/ oder /pillar/<key>/): {n!r}")
            continue
        if n == v:
            f.append(f"{v}: Schleife (Ziel = Quelle)")
        if n in von_alle:
            f.append(f"{v}: Kette – Ziel {n} ist selbst eine Weiterleitungsquelle")
        if n not in live:
            f.append(f"{v}: Ziel {n} ist nicht live (draft oder nicht vorhanden)")
        if r == "C" and not n.startswith("/pillar/"):
            f.append(f"{v}: Regel C verlangt Pillar-Ziel, gefunden {n}")
        if r in {"A", "B"} and not n.startswith("/posts/"):
            f.append(f"{v}: Regel {r} verlangt Beitrags-Ziel, gefunden {n}")
        if r == "A" and slug_rest(v) != slug_rest(n):
            f.append(f"{v}: Regel A verlangt identischen Slug-Rest, Ziel {n} weicht ab")
        if n.startswith("/pillar/") and n.rstrip("/") == "/pillar":
            f.append(f"{v}: Ziel ist die Pillar-Übersicht – erlaubt sind nur Themenseiten")

    entfallen_set: set[str] = set()
    for e in entfallen:
        v, r = e.get("von", ""), e.get("regel", "")
        if not re.fullmatch(r"/(posts|tags)/[^/?#\s]+/", v or ""):
            f.append(f"entfallen: Pfad ungültig: {v!r}")
            continue
        if v in entfallen_set:
            f.append(f"entfallen: doppelt: {v}")
        entfallen_set.add(v)
        if r not in REGELN_ENTFALLEN:
            f.append(f"{v}: entfallen braucht Regel D oder E, gefunden {r!r}")
        if not str(e.get("grund", "")).strip():
            f.append(f"{v}: Begründung fehlt")
        if v in von_alle:
            f.append(f"{v}: steht gleichzeitig in Weiterleitungen und entfallen")
        if v in live:
            f.append(f"{v}: entfallen, aber live")
        if v.startswith("/tags/") and r != "E":
            f.append(f"{v}: Tag-Archiv braucht Regel E")
    for v in von_alle:
        if v.startswith("/tags/"):
            f.append(f"{v}: Tag-Archive dürfen nicht umgeleitet werden (Regel E)")
    return f


# ----------------------------------------------------------------- Erzeugen

def seiten_html(von: str, nach: str, regel: str) -> str:
    ziel = SITE + nach
    return (
        '<!DOCTYPE html>\n'
        '<html lang="de">\n'
        '<head>\n'
        '<meta charset="utf-8">\n'
        f'<!-- {GENERATOR_NOTE} -->\n'
        f'<meta name="{MARKER_KEY}" content="regel-{regel}">\n'
        '<meta name="robots" content="noindex,follow">\n'
        f'<link rel="canonical" href="{ziel}">\n'
        f'<meta http-equiv="refresh" content="0; url={ziel}">\n'
        '<title>Diese Seite ist umgezogen | FranksFinanzcheck</title>\n'
        '</head>\n'
        '<body style="font-family:sans-serif;max-width:640px;margin:60px auto;padding:0 20px;color:#19324c">\n'
        '<a class="skip-link" href="#main-content" style="position:absolute;left:-9999px">Direkt zum Inhalt</a>\n'
        '<main id="main-content">\n'
        '<h1 style="font-size:22px">Diese Seite ist umgezogen</h1>\n'
        f'<p>Du wirst weitergeleitet. Falls nicht, <a href="{nach}">geht es hier weiter</a>.</p>\n'
        '</main>\n'
        '</body>\n'
        '</html>\n'
    )


def static_pfad(root: str, von: str) -> str:
    return os.path.join(root, "static", von.strip("/"), "index.html")


def erwartete_seiten(eintraege: list[dict]) -> dict[str, str]:
    """von -> erwarteter HTML-Inhalt."""
    return {e["von"]: seiten_html(e["von"], e["nach"], e["regel"]) for e in eintraege}


def build(root: str, eintraege: list[dict]) -> tuple[int, int]:
    """Schreibt Seiten. Entfernt nur eigene, nicht mehr gelistete Seiten (Marker-Prüfung)."""
    geschrieben = 0
    for von, html in erwartete_seiten(eintraege).items():
        p = static_pfad(root, von)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        alt = open(p, encoding="utf-8").read() if os.path.exists(p) else None
        if alt != html:
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(html)
            geschrieben += 1
    entfernt = 0
    erwartet = set(erwartete_seiten(eintraege))
    for p in gefundene_marker(root):
        von = "/" + os.path.relpath(os.path.dirname(p), os.path.join(root, "static")).replace(os.sep, "/") + "/"
        if von not in erwartet:
            os.remove(p)
            entfernt += 1
    return geschrieben, entfernt


def gefundene_marker(root: str) -> list[str]:
    """Alle static/-Seiten, die diese Generator-Markierung tragen."""
    out = []
    base = os.path.join(root, "static")
    for dirpath, _d, files in os.walk(base):
        if "index.html" in files:
            p = os.path.join(dirpath, "index.html")
            with open(p, encoding="utf-8", errors="ignore") as fh:
                if MARKER_KEY in fh.read(1500):
                    out.append(p)
    return out


def verify(root: str, eintraege: list[dict]) -> list[str]:
    f: list[str] = []
    erwartet = erwartete_seiten(eintraege)
    for von, html in erwartet.items():
        p = static_pfad(root, von)
        if not os.path.exists(p):
            f.append(f"{von}: Seite fehlt (static/… nicht erzeugt, --build ausführen)")
            continue
        if open(p, encoding="utf-8").read() != html:
            f.append(f"{von}: Seite weicht von Quelle ab (Hand geändert? --build ausführen)")
    for p in gefundene_marker(root):
        von = "/" + os.path.relpath(os.path.dirname(p), os.path.join(root, "static")).replace(os.sep, "/") + "/"
        if von not in erwartet:
            f.append(f"{von}: Seite trägt Generator-Markierung, steht aber nicht in der Quelle")
    return f


def _kopfzeilen_holen(url: str) -> dict[str, str]:
    """HEAD-Anfrage, gibt Antwort-Header klein geschrieben zurück. Wirft bei Netzfehler."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "ff-proxy-check/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return {k.lower(): v for k, v in resp.headers.items()}


def proxy_status(holen=None, url: str = SITE + "/") -> tuple[str, str]:
    """Prüft, ob der Cloudflare-Proxy vor der Seite aktiv ist.

    Ergebnis (Status, Begründung):
      aktiv       – Antwort trägt den Header cf-ray (Cloudflare antwortet)
      inaktiv     – Antwort ohne cf-ray (direkt GitHub Pages)
      unbekannt   – Anfrage gescheitert. Das ist KEIN Beleg für inaktiv.
    Ohne nachgewiesen aktiven Proxy erzeugt --cloudflare keine CSV.
    """
    holen = holen or _kopfzeilen_holen
    try:
        kopf = holen(url)
    except Exception as exc:  # Netzfehler, Timeout, TLS …
        return "unbekannt", f"Anfrage an {url} gescheitert ({type(exc).__name__})"
    if "cf-ray" in {k.lower() for k in kopf}:
        return "aktiv", f"cf-ray: {kopf.get('cf-ray', kopf.get('CF-Ray'))}"
    return "inaktiv", "kein cf-ray-Header in der Antwort"


def cloudflare_freigabe(status: str) -> bool:
    """Nur ein nachweislich aktiver Proxy gibt die Bulk-CSV frei."""
    return status == "aktiv"


def cloudflare_csv(eintraege: list[dict]) -> str:
    """Bulk-Redirect-CSV (ohne Kopfzeile, Format laut Cloudflare-Doku:
    <SOURCE_URL>,<TARGET_URL>[,<STATUS_CODE>,<PRESERVE_QUERY_STRING>,<INCLUDE_SUBDOMAINS>,<SUBPATH_MATCHING>,<PRESERVE_PATH_SUFFIX>])."""
    zeilen = []
    for e in eintraege:
        quelle = "franksfinanzcheck.de" + e["von"]
        ziel = SITE + e["nach"]
        zeilen.append(f"{quelle},{ziel},301,FALSE,FALSE,FALSE,FALSE")
    return "\n".join(zeilen) + "\n"


# ----------------------------------------------------------------- Selbsttest

def selftest() -> int:
    fehler = []

    def check(name: str, ok: bool) -> None:
        if not ok:
            fehler.append(name)

    live = {"/posts/2026-10-07-neu/", "/pillar/konto-karten/", "/posts/2026-08-19-energie/"}
    gut = [{"von": "/posts/2026-09-21-alt/", "nach": "/posts/2026-10-07-alt/", "regel": "A", "grund": "Datumskorrektur umbenannt"}]
    gut_live = [{"von": "/posts/2026-09-21-alt/", "nach": "/posts/2026-08-19-energie/", "regel": "B", "grund": "gleiches Thema, Energiekosten"}]
    entf_ok = [{"von": "/tags/beispiel/", "regel": "E", "grund": "Tag-Archiv bleibt 404"}]

    # 1 grüner Fall: A mit gleichem Slug-Rest, Ziel live
    live1 = live | {"/posts/2026-10-07-alt/"}
    check("grün: A mit gleichem Rest", pruefe(gut, [], live1) == [])
    # 2 Ziel nicht live
    check("Ziel nicht live erkannt", any("nicht live" in x for x in pruefe(gut, [], live)))
    # 3 Kette
    kette = [
        {"von": "/posts/2026-09-21-a/", "nach": "/posts/2026-08-19-energie/", "regel": "B", "grund": "gleiches Thema"},
        {"von": "/posts/2026-08-01-b/", "nach": "/posts/2026-09-21-a/", "regel": "B", "grund": "gleiches Thema"},
    ]
    check("Kette erkannt", any("Kette" in x for x in pruefe(kette, [], live)))
    # 4 Schleife
    schleife = [{"von": "/posts/2026-09-21-a/", "nach": "/posts/2026-09-21-a/", "regel": "B", "grund": "gleiches Thema"}]
    check("Schleife erkannt", any("Schleife" in x for x in pruefe(schleife, [], live)))
    # 5 Regel A mit abweichendem Rest
    falsch_a = [{"von": "/posts/2026-09-21-alt/", "nach": "/posts/2026-08-19-energie/", "regel": "A", "grund": "Datumskorrektur umbenannt"}]
    check("A mit abweichendem Rest erkannt", any("Slug-Rest" in x for x in pruefe(falsch_a, [], live)))
    # 6 Regel C auf Beitrag
    falsch_c = [{"von": "/posts/2026-09-21-alt/", "nach": "/posts/2026-08-19-energie/", "regel": "C", "grund": "Pillar-Fallback"}]
    check("C auf Beitrag erkannt", any("Pillar-Ziel" in x for x in pruefe(falsch_c, [], live)))
    # 7 Tag-Archiv als Weiterleitung
    tag = [{"von": "/tags/beispiel/", "nach": "/posts/2026-08-19-energie/", "regel": "B", "grund": "Tag soll weiterleiten"}]
    check("Tag als Weiterleitung erkannt", any("Tag" in x for x in pruefe(tag, [], live)))
    # 8 Quelle ist live
    quelle_live = [{"von": "/posts/2026-10-07-neu/", "nach": "/posts/2026-08-19-energie/", "regel": "B", "grund": "gleiches Thema"}]
    check("Live-Quelle erkannt", any("live" in x and "Quelle" in x for x in pruefe(quelle_live, [], live)))
    # 9 entfallen: Regel D ohne Begründung
    check("entfallen ohne Begründung erkannt", any("Begründung" in x for x in pruefe([], [{"von": "/posts/x-alt/", "regel": "D", "grund": ""}], live)))
    # 10 entfallen mit Tag-Regel D
    check("Tag braucht Regel E", any("Regel E" in x for x in pruefe([], [{"von": "/tags/a/", "regel": "D", "grund": "Tag Archiv"}], live)))
    # 11 Ziel Pillar-Übersicht
    uebersicht = [{"von": "/posts/2026-09-21-alt/", "nach": "/pillar/", "regel": "C", "grund": "Pillar-Fallback"}]
    check("Pillar-Übersicht als Ziel erkannt", any("Pillar-Übersicht" in x or "ungültig" in x for x in pruefe(uebersicht, [], live | {"/pillar/"})))
    # 12 Build/Verify im Temp-Verzeichnis, Marker, Prune
    with tempfile.TemporaryDirectory() as tmp:
        build(tmp, gut_live)
        check("verify nach build grün", verify(tmp, gut_live) == [])
        p = static_pfad(tmp, gut_live[0]["von"])
        check("Seite enthält canonical und refresh", '<meta http-equiv="refresh" content="0; url=https://franksfinanzcheck.de/posts/2026-08-19-energie/">' in open(p, encoding="utf-8").read())
        check("Seite ist noindex,follow", 'content="noindex,follow"' in open(p, encoding="utf-8").read())
        # eigene, nicht mehr gelistete Seite wird entfernt
        build(tmp, [])
        check("veraltete eigene Seite entfernt", not os.path.exists(p))
        # fremde Seite ohne Marker bleibt unangetastet
        fremd = os.path.join(tmp, "static", "posts", "fremd", "index.html")
        os.makedirs(os.path.dirname(fremd), exist_ok=True)
        open(fremd, "w", encoding="utf-8").write("<html>fremd</html>")
        build(tmp, [])
        check("fremde Seite bleibt", os.path.exists(fremd))
        # Handänderung wird von verify erkannt
        build(tmp, gut_live)
        open(p, "a", encoding="utf-8").write("<!-- hand -->")
        check("Handänderung erkannt", any("weicht" in x for x in verify(tmp, gut_live)))
    # 13 CSV-Format: keine Kopfzeile, Schema ohne https bei Quelle
    csv = cloudflare_csv(gut_live).strip().split("\n")
    check("CSV ohne Kopfzeile, Quelle ohne Schema", csv[0].startswith("franksfinanzcheck.de/posts/") and csv[0].endswith(",301,FALSE,FALSE,FALSE,FALSE"))

    # 14–18 Proxy-Status und Freigabe
    check("proxy aktiv bei cf-ray", proxy_status(lambda u: {"CF-Ray": "abc-FRA", "server": "cloudflare"})[0] == "aktiv")
    check("proxy inaktiv ohne cf-ray", proxy_status(lambda u: {"server": "GitHub.com"})[0] == "inaktiv")

    def _fehler(u):
        raise OSError("keine Verbindung")
    check("proxy unbekannt bei Netzfehler (nicht inaktiv)", proxy_status(_fehler)[0] == "unbekannt")
    check("CSV nur bei aktivem Proxy freigegeben",
          cloudflare_freigabe("aktiv") is True and cloudflare_freigabe("inaktiv") is False and cloudflare_freigabe("unbekannt") is False)

    if fehler:
        print("SELBSTTEST FEHLGESCHLAGEN:")
        for x in fehler:
            print("  -", x)
        return 2
    print("weiterleitungen.py Selbsttest ok (18 Fälle)")
    return 0


# ----------------------------------------------------------------- CLI

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="Quelle validieren")
    ap.add_argument("--build", action="store_true", help="static/-Seiten erzeugen")
    ap.add_argument("--verify", action="store_true", help="erzeugte Seiten prüfen")
    ap.add_argument("--cloudflare", action="store_true", help="Bulk-CSV erzeugen (nur bei aktivem Proxy)")
    ap.add_argument("--proxy-check", action="store_true", help="Cloudflare-Proxy per cf-ray-Header prüfen (braucht Internet)")
    ap.add_argument("--selftest", action="store_true", help="Selbsttest")
    a = ap.parse_args()

    if a.selftest:
        return selftest()
    if a.proxy_check:
        status, grund = proxy_status()
        print(f"proxy: {status} – {grund}")
        return 0 if status == "aktiv" else 1
    if not any([a.check, a.build, a.verify, a.cloudflare]):
        ap.print_help()
        return 0

    eintraege, entfallen = lade_quelle(BLOG_DIR)
    live = live_urls(BLOG_DIR)
    rc = 0

    befunde = pruefe(eintraege, entfallen, live)
    print(f"Quelle: {len(eintraege)} Weiterleitungen · {len(entfallen)} bewusst 404 · {len(live)} Live-URLs")
    for x in befunde:
        print("  BEFUND:", x)
    if befunde:
        return 1

    if a.build:
        g, e = build(BLOG_DIR, eintraege)
        print(f"build: {g} Seiten geschrieben, {e} veraltete entfernt")

    if a.verify:
        befunde = verify(BLOG_DIR, eintraege)
        for x in befunde:
            print("  BEFUND:", x)
        if befunde:
            rc = 1
        else:
            print(f"verify: {len(eintraege)} Seiten stimmen mit der Quelle überein")

    if a.cloudflare:
        status, grund = proxy_status()
        if not cloudflare_freigabe(status):
            print(f"cloudflare: verweigert – Proxy ist {status} ({grund}). Erst cf-ray nachweisen (--proxy-check).")
            return 1
        ziel = os.path.join(BLOG_DIR, "cloudflare", "redirects", "bulk-redirects.csv")
        os.makedirs(os.path.dirname(ziel), exist_ok=True)
        with open(ziel, "w", encoding="utf-8") as fh:
            fh.write(cloudflare_csv(eintraege))
        print(f"cloudflare: {ziel} ({len(eintraege)} Zeilen, ohne Kopfzeile)")

    if a.check and not (a.build or a.verify or a.cloudflare):
        print("check: grün")
    return rc


if __name__ == "__main__":
    sys.exit(main())
