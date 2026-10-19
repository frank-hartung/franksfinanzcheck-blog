#!/usr/bin/env python3
"""Automatische Indexierung über IndexNow (Bing/Yandex/Naver/Seznam – kostenlos).

IndexNow ist das offizielle Push-Protokoll von Microsoft/Bing: Man meldet
neue/geänderte URLs sofort – ohne Bing-API-Key, ohne Konto-Verwirrung.
Google nimmt an IndexNow nicht teil; für Google läuft dieselbe Logik über
`scripts/gsc_indexierung.py` (URL Inspection API). Beide Skripte lesen
dieselbe Quelle.

Voraussetzung (einmalig, eingerichtet):
  - `scripts/indexnow_key.txt` enthält den Schlüssel
  - `static/<schlüssel>.txt` liegt im Wurzelverzeichnis der Website
    (beide werden hier auf Übereinstimmung geprüft – ein Schlüssel, dessen
    Datei fehlt, liefert HTTP 422 und niemand merkt es)

UMSTELLUNG 12.10.2026 – ABLEITEN STATT AUFSCHREIBEN
---------------------------------------------------
Bis zu diesem Stand meldete das Skript eine HANDGESCHRIEBENE Liste:
alle Posts plus sechs namentlich genannte Pillar-Slugs, drei Hubs und die
Startseite. Gemessen am Build vom 12.10.2026:

    74 indexierbare URLs in der Sitemap
    54 URLs in der Meldeliste
    20 indexierbare Seiten, die NIE gemeldet wurden

Darunter alle Werkzeug-Rechner, das Fixkosten-Cockpit, die Studien-Seite,
`/ueber/`, `/transparenz/`, `/impressum/` und `/datenschutz/`. Genau dieselbe
Fehlerklasse, die `layouts/sitemap.xml` am 01.10.2026 schon einmal erledigt
hat: Eine Namensliste bricht bei jedem Wachstum – jede neue Seite fällt still
aus der Meldung, bis jemand den Namen nachträgt.

Jetzt gilt: Quelle ist die Sitemap (`scripts/indexierbare_seiten.py`). Eine
Seite, die indexierbar ist, wird gemeldet. Eine Seite, die auf noindex geht,
verschwindet von selbst aus der Meldung.

ZWEITER BEFUND, MIT ERLEDIGT: Im Zustand lagen 32 URLs der alten
github.io-Auslieferung (`https://frank-hartung.github.io/franksfinanzcheck-blog/…`).
IndexNow prüft, ob die gemeldete URL zum `host` des Schlüssels passt – diese
Einträge waren totes Gewicht und verhinderten, dass der Zustand als Beleg
taugt. Sie werden beim ersten Lauf entfernt und im Bericht gezählt.

Nutzung:
    python3 scripts/submit_indexnow.py            # alle fälligen URLs einreichen
    python3 scripts/submit_indexnow.py --dry-run  # Vorschau (kein Netz)
    python3 scripts/submit_indexnow.py --all      # alles erneut (ignoriert Zustand)
    python3 scripts/submit_indexnow.py --live     # Queue aus der LIVE-Sitemap
    python3 scripts/submit_indexnow.py --kein-llms # ohne llms.txt-Pflege (Tageslauf)
    python3 scripts/submit_indexnow.py --selftest # offline, kein Netz

Das Skript merkt sich eingereichte URLs in `.indexnow_submitted.json`.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from indexierbare_seiten import (  # noqa: E402
    SitemapFehler,
    basis_url,
    hole_seiten,
    live_sitemap_url,
    reihenfolge,
)

KEY_FILE = os.path.join(BLOG_DIR, "scripts", "indexnow_key.txt")
STATE_FILE = os.path.join(BLOG_DIR, ".indexnow_submitted.json")

INDEXNOW = "https://api.indexnow.org/indexnow"
# Protokoll-Grenze: höchstens 10.000 URLs je Anfrage.
MAX_URLS_PRO_ANFRAGE = 10_000
# Alte Auslieferung unter github.io – solche Einträge im Zustand sind tot.
FREMDER_HOST = re.compile(r"^https?://[^/]*github\.io/", re.I)


def lies_text(pfad: str) -> str:
    """Textdatei lesen und das Handle schließen.

    Eine Automatisierung, die pro Lauf Dutzende Dateien öffnet, darf ihre
    Handles nicht dem Garbage Collector überlassen: Unter
    `-W error::ResourceWarning` (und in den Unit-Tests dieses Repos) würde
    daraus ein Befund gegen die Wache selbst – Lärm, der echte Funde zudeckt.
    """
    with open(pfad, encoding="utf-8") as f:
        return f.read()


def schreibe_text(pfad: str, inhalt: str) -> None:
    os.makedirs(os.path.dirname(pfad) or ".", exist_ok=True)
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(inhalt)


def get_key() -> str:
    if not os.path.exists(KEY_FILE):
        raise SystemExit("FEHLER: scripts/indexnow_key.txt fehlt.")
    return lies_text(KEY_FILE).strip()


def pruefe_schluesseldatei(key: str) -> list[str]:
    """Schlüssel und seine öffentliche Datei müssen zusammenpassen.

    IndexNow antwortet mit 422 („Bad parameter"), wenn die Schlüssel-Datei
    unter `https://<host>/<key>.txt` nicht exakt den Schlüssel liefert. Der
    Fehler ist von der Meldung her kaum zu deuten – deshalb wird hier vorher
    geprüft, was im Repo liegt.
    """
    befunde: list[str] = []
    # IndexNow verlangt 8–128 Zeichen aus [0-9a-zA-Z]. Der Schlüssel dieses
    # Projekts enthält bewusst auch Buchstaben jenseits von a–f – eine
    # Hex-Prüfung wäre hier eine falsche Regel, die den eigenen Schlüssel
    # als ungültig meldet (beim ersten Lauf dieses Skripts passiert).
    if not re.fullmatch(r"[0-9a-zA-Z]{8,128}", key):
        befunde.append(
            "Schlüssel hat keine IndexNow-Form (8–128 Zeichen aus 0-9a-zA-Z): "
            f"{key[:6]!r}…")
    datei = os.path.join(BLOG_DIR, "static", f"{key}.txt")
    if not os.path.exists(datei):
        befunde.append(f"static/{key}.txt fehlt – IndexNow lehnt jede Meldung mit 422 ab")
    else:
        inhalt = lies_text(datei).strip()
        if inhalt != key:
            befunde.append(f"static/{key}.txt enthält {inhalt[:12]!r}…, erwartet {key[:12]!r}…")
    return befunde


def load_state() -> set[str]:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                return set(json.load(f))
        except (json.JSONDecodeError, OSError) as exc:
            raise SystemExit(
                f"FEHLER: {STATE_FILE} ist unlesbar ({exc}). Datei reparieren oder "
                "löschen – ein kaputter Zustand darf nicht als leer durchgehen.")
    return set()


def save_state(state: set[str]) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(state), f, indent=1)


def bereinige_zustand(state: set[str], erlaubter_host: str) -> tuple[set[str], int]:
    """Fremde/unerreichbare Einträge entfernen (github.io-Altlast)."""
    behalten: set[str] = set()
    fremd = 0
    for url in state:
        if FREMDER_HOST.match(url):
            fremd += 1
            continue
        behalten.add(url)
    return behalten, fremd


def queue_bauen(live: bool = False, sitemap_url: str | None = None,
                http=None) -> tuple[list[str], list[str]]:
    """URLs aus der Sitemap ableiten – in Wichtigkeits-Reihenfolge."""
    seiten, befunde = hole_seiten(sitemap_url=(sitemap_url or live_sitemap_url())
                                  if (live or sitemap_url) else None, http=http)
    urls = [s.url for s in reihenfolge(seiten)]
    return urls, befunde


def batches(urls: list[str]) -> list[list[str]]:
    return [urls[i:i + MAX_URLS_PRO_ANFRAGE]
            for i in range(0, len(urls), MAX_URLS_PRO_ANFRAGE)] or []


def submit(urls: list[str], key: str, http=None) -> int:
    """Sendet URLs an IndexNow (ein Batch, Protokollgrenze 10.000)."""
    host = os.path.basename(basis_url().rstrip("/"))
    body = json.dumps({
        "host": host,
        "key": key,
        "keyLocation": f"{basis_url()}{key}.txt",
        "urlList": urls,
    }).encode()
    req = urllib.request.Request(
        INDEXNOW,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status


def refresh_llms_txt() -> None:
    """GEO-Begleitdatei static/llms.txt aus den Live-Inhalten erneuern.

    Läuft bei jedem IndexNow-Lauf mit (wöchentlich + bei jedem neuen Artikel);
    die Workflows committen das Ergebnis per `git add -A`.
    Absichtlich feuerfest: Ein Fehler hier darf die Indexierung nie blockieren
    (Premium-Härtung #233 lässt grüßen).

    ABMELDUNG per `--kein-llms` (12.10.2026): Der GSC-Tageslauf reicht URLs ein,
    er pflegt keine Inhaltsdatei. `scripts/generate_llms_txt.py` schreibt
    `date.today()` in den Kopf – die Datei ändert sich also JEDEN Tag, und ein
    Commit auf main würde jeden Tag einen vollständigen Deploy auslösen
    (`static/llms.txt` ist zu Recht deploy-relevant, es ist eine ausgelieferte
    Datei). Genau das war Befund F1 des Premium-Audits: Lebenszeichen
    verstopfen die Deploy-Queue. Wöchentliche Pflege bleibt bei seo-weekly.yml.
    """
    try:
        import subprocess
        gen = os.path.join(BLOG_DIR, "scripts", "generate_llms_txt.py")
        r = subprocess.run([sys.executable, gen], capture_output=True,
                           text=True, timeout=120)
        print((r.stdout or "").strip() or "llms.txt: Generator ohne Ausgabe.")
        if r.returncode != 0:
            print(f"⚠️ llms.txt-Generator meldete Exit {r.returncode}: "
                  f"{(r.stderr or '')[:200]}")
    except Exception as e:  # noqa: BLE001 – Feuerfest-Prinzip, siehe oben
        print(f"⚠️ llms.txt-Aktualisierung übersprungen: {e}")


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    all_urls = "--all" in sys.argv
    live = "--live" in sys.argv
    kein_llms = "--kein-llms" in sys.argv
    if "--selftest" in sys.argv:
        return _selftest()

    key = get_key()
    schluessel_befunde = pruefe_schluesseldatei(key)
    for b in schluessel_befunde:
        print(f"❌ IndexNow-Schlüssel: {b}")
    if schluessel_befunde:
        return 2

    try:
        urls, sitemap_befunde = queue_bauen(live=live)
    except SitemapFehler as exc:
        print(f"❌ {exc}")
        return 2
    for b in sitemap_befunde:
        print(f"⚠️  Sitemap: {b}")

    state = load_state()
    state, fremd = bereinige_zustand(state, os.path.basename(basis_url().rstrip("/")))
    if fremd:
        if dry_run:
            print(f"🧹 {fremd} Altlast-URL(s) der github.io-Auslieferung stünden im "
                  "Zustand zur Bereinigung an (Probelauf schreibt nichts).")
        else:
            print(f"🧹 {fremd} Altlast-URL(s) der github.io-Auslieferung aus dem "
                  "Zustand entfernt (IndexNow prüft den Host – sie waren totes Gewicht).")

    neu = list(urls) if all_urls else [u for u in urls if u not in state]

    print(f"{len(urls)} indexierbare URLs aus der Sitemap, davon {len(neu)} neu für IndexNow.")
    # EIN PROBELAUF SCHREIBT NICHTS – auch nicht die Begleitdatei.
    #
    # `static/llms.txt` ist versioniert und deploy-relevant (siehe Kommentar an
    # `refresh_llms_txt`). Ein `--dry-run`, das sie erneuert, ändert den
    # Arbeitsbaum und kann einen Deploy auslösen, obwohl niemand etwas
    # eingereicht hat. Genau das passierte bis zum 12.10.2026: Die Vorschau
    # stand HINTER der Pflege, also wurde „nur mal schauen" zum Schreibvorgang.
    if dry_run:
        print("ℹ️ Probelauf: llms.txt und Einreichungs-Zustand bleiben unangetastet.")
    elif kein_llms:
        print("ℹ️ llms.txt bewusst nicht angefasst (--kein-llms): Pflege läuft "
              "wöchentlich in seo-weekly.yml, ein tägliches Neuschreiben würde "
              "jeden Tag einen Deploy auslösen.")
    else:
        refresh_llms_txt()

    if not neu:
        # Auch die Zustands-Bereinigung ist ein Schreibvorgang – im Probelauf
        # wird sie angekündigt, nicht ausgeführt.
        if fremd and not dry_run:
            save_state(state)
        print("✅ Alles bereits eingereicht – nichts zu tun.")
        return 1 if sitemap_befunde else 0

    if dry_run:
        print("\n(Vorschau – würde einreichen:)")
        for u in neu[:10]:
            print(f"  • {u}")
        if len(neu) > 10:
            print(f"  … und {len(neu) - 10} weitere")
        if fremd:
            print(f"  ℹ️ würde außerdem {fremd} Altlast-URL(s) aus dem Zustand entfernen")
        return 1 if sitemap_befunde else 0

    rc = 0
    for i, teil in enumerate(batches(neu), start=1):
        try:
            status = submit(teil, key)
        except urllib.error.HTTPError as e:
            print(f"❌ IndexNow-Fehler (Batch {i}): HTTP {e.code}")
            print(f"   {e.read().decode()[:300]}")
            return 1
        except (urllib.error.URLError, OSError) as e:
            print(f"❌ IndexNow nicht erreichbar (Batch {i}): {e}")
            return 1
        if status in (200, 202):
            print(f"✅ Batch {i}: {len(teil)} URLs eingereicht (HTTP {status})")
            state.update(teil)
        else:
            print(f"⚠️ IndexNow antwortete mit HTTP {status} (Batch {i})")
            rc = 1
    save_state(state)
    return rc or (1 if sitemap_befunde else 0)


# ---------------------------------------------------------------- Selbsttest
def _selftest() -> int:
    """Offline: Schlüsselprüfung, Queue-Ableitung, Batches, Zustands-Hygiene."""
    fehler: list[str] = []

    def erwarte(name: str, bedingung: bool) -> None:
        if not bedingung:
            fehler.append(name)

    # 1) Schlüssel und öffentliche Datei stimmen im Repo überein
    key = get_key()
    erwarte("Schlüssel hat IndexNow-Form", not pruefe_schluesseldatei(key))

    # 2) Schlüssel ohne Datei ist ein harter Befund
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        global BLOG_DIR
        alt_dir = BLOG_DIR
        try:
            BLOG_DIR = tmp
            os.makedirs(os.path.join(tmp, "scripts"), exist_ok=True)
            probe = "0123456789abcdef0123456789abcdef"
            schreibe_text(os.path.join(tmp, "scripts", "indexnow_key.txt"), probe)
            befunde = pruefe_schluesseldatei(probe)
            erwarte("fehlende Schlüssel-Datei erkannt",
                    any("fehlt" in b for b in befunde))
            os.makedirs(os.path.join(tmp, "static"), exist_ok=True)
            schreibe_text(os.path.join(tmp, "static", probe + ".txt"), "falscher-inhalt")
            befunde2 = pruefe_schluesseldatei(probe)
            erwarte("Inhalts-Drift erkannt", any("erwartet" in b for b in befunde2))
            befunde3 = pruefe_schluesseldatei("kurz")
            erwarte("zu kurzer Schlüssel erkannt", any("IndexNow-Form" in b for b in befunde3))
        finally:
            BLOG_DIR = alt_dir

    # 3) Queue kommt aus der Sitemap, nicht aus einer Namensliste
    sitemap = ('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
               '<url><loc>https://franksfinanzcheck.de/</loc><priority>1.0</priority></url>'
               '<url><loc>https://franksfinanzcheck.de/werkzeuge/scanner/</loc>'
               '<priority>0.7</priority></url>'
               '<url><loc>https://franksfinanzcheck.de/posts/neu/</loc>'
               '<priority>0.8</priority></url></urlset>')
    urls, befunde = queue_bauen(sitemap_url="https://x/sitemap.xml",
                                http=lambda url, timeout=30: (200, sitemap))
    erwarte("drei URLs abgeleitet", len(urls) == 3)
    erwarte("Reihenfolge nach Wichtigkeit",
            urls == ["https://franksfinanzcheck.de/",
                     "https://franksfinanzcheck.de/posts/neu/",
                     "https://franksfinanzcheck.de/werkzeuge/scanner/"])
    erwarte("keine Sitemap-Befunde", not befunde)

    # 4) Neue Seitentypen landen OHNE Code-Änderung in der Queue
    erwarte("Werkzeugseite ist dabei (früher: Namensliste)",
            "https://franksfinanzcheck.de/werkzeuge/scanner/" in urls)

    # 5) Leere Sitemap ist ein Fehler, kein „fertig"
    leer = '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>'
    try:
        queue_bauen(sitemap_url="https://x/sitemap.xml",
                    http=lambda url, timeout=30: (200, leer))
        fehler.append("leere Sitemap muss SitemapFehler werfen")
    except SitemapFehler:
        pass

    # 6) Batch-Grenze
    viele = [f"https://franksfinanzcheck.de/p{i}/" for i in range(MAX_URLS_PRO_ANFRAGE + 5)]
    teile = batches(viele)
    erwarte("Batch-Grenze eingehalten",
            len(teile) == 2 and len(teile[0]) == MAX_URLS_PRO_ANFRAGE and len(teile[1]) == 5)
    erwarte("leere Liste ergibt keine Batches", batches([]) == [])

    # 7) Zustands-Hygiene: github.io-Altlast fliegt raus, eigene Hosts bleiben
    state = {"https://frank-hartung.github.io/franksfinanzcheck-blog/posts/a/",
             "https://franksfinanzcheck.de/posts/a/",
             "https://frank-hartung.github.io/franksfinanzcheck-blog/"}
    behalten, fremd = bereinige_zustand(state, "franksfinanzcheck.de")
    erwarte("Altlast entfernt", fremd == 2 and behalten == {"https://franksfinanzcheck.de/posts/a/"})

    # 8) Bereits gemeldete URLs werden nicht doppelt geschickt
    neu = [u for u in urls if u not in behalten]
    erwarte("Dedupe über den Zustand", len(neu) == 3)

    if fehler:
        print("❌ INDEXNOW-SELBSTTEST fehlgeschlagen:")
        for f in fehler:
            print(f"   - {f}")
        return 1
    print("✅ submit_indexnow: Selbsttest bestanden "
          "(Schlüsselvertrag, Queue aus der Sitemap, Batch-Grenze, "
          "Zustands-Hygiene, Dedupe).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
