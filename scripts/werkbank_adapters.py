#!/usr/bin/env python3
# ============================================================
#  WERKBANK-ADAPTER – vier Fremdwerkzeuge, ein Vertrag
#  ------------------------------------------------------------
#  Rollout 03.10.2026. SSOT: data/werkbank.yaml
#  Wache: scripts/werkbank_gate.py · Runbook: docs/ANLEITUNG-WERKBANK.md
#
#  Jedes Gewerk beantwortet hier dieselben drei Fragen:
#    1. Bin ich einsatzbereit?        → verfuegbar() ohne Netzaufruf
#    2. Was kann ich konkret?         → eine Funktion mit festem Rückgabe-Schema
#    3. Was mache ich, wenn nicht?    → Standby, nie ein Absturz
#
#  LEITPLANKEN (Gate B1–B9):
#    · Kein Adapter wirft nach außen. Netzfehler werden zu `fehler`-Text,
#      nie zu einer Exception, die einen Redaktionslauf killt.
#    · verfuegbar() macht NIEMALS einen Netzaufruf – sonst wäre der
#      Selbsttest nicht offline und die CI nicht reproduzierbar.
#    · Secrets werden ausschließlich über ENV gelesen, nie geloggt.
#    · Nur der Konnektor darf schreiben, und nur nach Freigabe.
# ============================================================
from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SSOT = ROOT / "data" / "werkbank.yaml"

USER_AGENT = "franksfinanzcheck-werkbank/1.0 (+https://franksfinanzcheck.de)"

# Zustände eines Gewerks. „standby" ist ausdrücklich kein Fehler (B3).
BEREIT = "bereit"
STANDBY = "standby"
DEFEKT = "defekt"


# --------------------------------------------------------------- SSOT
def lade_ssot(pfad: Path | str | None = None) -> dict:
    """Liest data/werkbank.yaml. Unlesbar → leerer Vertrag (fail-safe)."""
    import yaml

    pfad = Path(pfad or SSOT)
    try:
        daten = yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        return {"version": 1, "gewerke": [], "antwortwerk": {}, "fragen": []}
    except Exception as exc:  # noqa: BLE001 – Konfig darf nie den Lauf killen
        print(f"⚠ werkbank.yaml nicht lesbar ({exc}) – Werkbank läuft leer.")
        return {"version": 1, "gewerke": [], "antwortwerk": {}, "fragen": []}
    daten.setdefault("gewerke", [])
    daten.setdefault("antwortwerk", {})
    daten.setdefault("fragen", [])
    return daten


def gewerk(ssot: dict, gid: str) -> dict:
    for g in ssot.get("gewerke") or []:
        if g.get("id") == gid:
            return g
    return {}


def jetzt_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def heute() -> str:
    return dt.date.today().isoformat()


def domain_von(url: str) -> str:
    """Hostname einer URL – ohne `www.`, ohne Port, ohne Zugangsdaten.

    Der Port muss weg: Sonst matcht `example.org:8080` gegen keinen
    Listeneintrag, und eine Sperrliste, die sich mit `:443` umgehen
    lässt, ist keine.
    """
    try:
        netloc = urllib.parse.urlparse(url).netloc.lower()
    except ValueError:
        return ""
    netloc = netloc.rpartition("@")[2]          # user:pass@host entfernen
    if netloc.startswith("["):                  # IPv6 in Klammern
        netloc = netloc.partition("]")[0].lstrip("[")
    else:
        netloc = netloc.partition(":")[0]       # Port entfernen
    return netloc[4:] if netloc.startswith("www.") else netloc


def _env(name: str | None) -> str:
    """ENV-Wert holen. Leerstring statt None, damit Prüfungen simpel bleiben."""
    return (os.environ.get(name) or "").strip() if name else ""


def _modul_da(name: str) -> bool:
    """Ist ein Python-Modul importierbar? Ohne es zu importieren."""
    import importlib.util

    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _hole(url: str, timeout: int = 30, headers: dict | None = None) -> tuple[str, str | None]:
    """Ein GET, der nie wirft. Rückgabe: (text, fehler)."""
    kopf = {"User-Agent": USER_AGENT, "Accept-Language": "de-DE,de;q=0.9"}
    kopf.update(headers or {})
    try:
        req = urllib.request.Request(url, headers=kopf)
        with urllib.request.urlopen(req, timeout=timeout) as antw:
            roh = antw.read()
        return roh.decode("utf-8", errors="replace"), None
    except urllib.error.HTTPError as exc:
        return "", f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001
        return "", f"{type(exc).__name__}: {exc}"


# ======================================================================
#  GEWERK 1 – SUCHE (Teil des Antwortwerks)
# ======================================================================
def such_anbieter(ssot: dict) -> list[dict]:
    return (ssot.get("antwortwerk") or {}).get("suche") or []


def such_status(anbieter: dict) -> dict:
    """Einsatzbereitschaft eines Suchanbieters – ohne Netzaufruf (B7)."""
    aid = anbieter.get("id", "?")
    if aid == "searxng":
        url = _env(anbieter.get("env_url"))
        if not url:
            return {"id": aid, "zustand": STANDBY,
                    "grund": f"{anbieter.get('env_url')} nicht gesetzt – "
                             "SearXNG-Instanz unbekannt (Runbook: Docker-Einzeiler)"}
        if not url.startswith(("http://", "https://")):
            return {"id": aid, "zustand": DEFEKT,
                    "grund": f"{anbieter.get('env_url')} ist keine http(s)-URL"}
        return {"id": aid, "zustand": BEREIT, "grund": f"Instanz: {url}"}
    if aid == "duckduckgo":
        return {"id": aid, "zustand": BEREIT, "grund": "schlüsselfrei, gedrosselt"}
    if aid == "themenpool":
        plan = ROOT / (anbieter.get("quelle") or "")
        if plan.is_file():
            return {"id": aid, "zustand": BEREIT, "grund": "kuratierter Plan vorhanden"}
        return {"id": aid, "zustand": STANDBY, "grund": "Themenplan fehlt"}
    return {"id": aid, "zustand": STANDBY, "grund": "unbekannter Anbieter"}


def suche_searxng(frage: str, anbieter: dict, limit: int, timeout: int) -> tuple[list[dict], str | None]:
    """SearXNG-JSON-API. Setzt `search.formats: [html, json]` voraus."""
    basis = _env(anbieter.get("env_url")).rstrip("/")
    if not basis:
        return [], "SEARXNG_URL nicht gesetzt"
    params = dict(anbieter.get("parameter") or {})
    params["q"] = frage
    ziel = f"{basis}{anbieter.get('pfad', '/search')}?{urllib.parse.urlencode(params)}"
    # SearXNGs Bot-Erkennung erwartet einen Proxy-Header, sonst 403.
    text, fehler = _hole(ziel, timeout=timeout, headers={"X-Forwarded-For": "127.0.0.1"})
    if fehler:
        return [], f"SearXNG nicht erreichbar ({fehler})"
    try:
        daten = json.loads(text)
    except json.JSONDecodeError:
        return [], ("SearXNG antwortet nicht in JSON – `search.formats` in "
                    "settings.yml um `json` ergänzen (Runbook)")
    treffer = []
    for r in (daten.get("results") or [])[:limit]:
        url = (r.get("url") or "").strip()
        if not url:
            continue
        treffer.append({
            "titel": (r.get("title") or "").strip(),
            "url": url,
            "auszug": (r.get("content") or "").strip()[:400],
            "quelle": f"SearXNG/{r.get('engine', '?')}",
        })
    return treffer, None


_DDG_TREFFER = re.compile(
    r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.S)
_TAGS = re.compile(r"<[^>]+>")


def suche_duckduckgo(frage: str, anbieter: dict, limit: int, timeout: int) -> tuple[list[dict], str | None]:
    """Schlüsselfreier Rückfall. DuckDuckGo drosselt – darum nie der Hauptweg."""
    ziel = anbieter.get("endpunkt") or "https://html.duckduckgo.com/html/"
    daten = urllib.parse.urlencode({"q": frage, "kl": "de-de"}).encode()
    try:
        req = urllib.request.Request(
            ziel, data=daten,
            headers={"User-Agent": USER_AGENT,
                     "Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=timeout) as antw:
            text = antw.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return [], f"DuckDuckGo nicht erreichbar ({type(exc).__name__})"

    treffer = []
    for roh_url, roh_titel in _DDG_TREFFER.findall(text)[: limit * 2]:
        url = html.unescape(roh_url)
        # DuckDuckGo verpackt Ziele in /l/?uddg=<url>
        if "uddg=" in url:
            teil = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("uddg")
            if teil:
                url = teil[0]
        if not url.startswith("http"):
            continue
        titel = html.unescape(_TAGS.sub("", roh_titel)).strip()
        treffer.append({"titel": titel, "url": url, "auszug": "", "quelle": "DuckDuckGo"})
        if len(treffer) >= limit:
            break
    if not treffer:
        return [], "DuckDuckGo lieferte keine auswertbaren Treffer (Drosselung?)"
    return treffer, None


def suche_themenpool(frage: str, anbieter: dict, limit: int, timeout: int) -> tuple[list[dict], str | None]:
    """Letzte Ebene: die kuratierten Feeds des Hauses, per RSS gelesen."""
    import yaml

    plan_pfad = ROOT / (anbieter.get("quelle") or "")
    if not plan_pfad.is_file():
        return [], "Themenplan nicht vorhanden"
    try:
        plan = yaml.safe_load(plan_pfad.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001
        return [], f"Themenplan nicht lesbar ({exc})"

    # Struktur von data/agent_reach/themenplan.yaml: Top-Level-Listen
    # `rss: [{name,url,kategorie}]` und `web: [{url}]`.
    feeds = [e["url"] for e in (plan.get("rss") or [])
             if isinstance(e, dict) and e.get("url")]
    if not feeds:
        return [], "Themenplan enthält keine RSS-Quellen"

    begriffe = [w.lower() for w in re.findall(r"\w{4,}", frage)]
    treffer: list[dict] = []
    for feed_url in feeds[:6]:
        text, fehler = _hole(feed_url, timeout=timeout)
        if fehler:
            continue
        for titel, link in _feed_eintraege(text)[:30]:
            punkte = sum(1 for b in begriffe if b in titel.lower())
            if punkte:
                treffer.append({"titel": titel, "url": link, "auszug": "",
                                "quelle": "Themenpool (RSS)", "_punkte": punkte})
    treffer.sort(key=lambda t: t.get("_punkte", 0), reverse=True)
    for t in treffer:
        t.pop("_punkte", None)
    if not treffer:
        return [], "Keine thematisch passenden Feed-Einträge"
    return treffer[:limit], None


def _feed_eintraege(text: str) -> list[tuple[str, str]]:
    """Titel/Link-Paare aus RSS *und* Atom.

    Der Hausplan mischt beides (tagesschau liefert Atom, Spiegel RSS).
    Ein Parser, der nur <item> kennt, übersieht die halbe Quellenliste –
    genau dieser Fehler hat den ersten Probelauf leer ausgehen lassen.
    """
    eintraege: list[tuple[str, str]] = []
    for block in re.findall(r"<(?:item|entry)\b[^>]*>(.*?)</(?:item|entry)>", text, re.S):
        titel = _first(block, r"<title[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>")
        # RSS: <link>URL</link> · Atom: <link href="URL" .../>
        link = _first(block, r"<link[^>]*>(?:<!\[CDATA\[)?\s*(https?://[^<\s]+)")
        if not link:
            link = _first(block, r'<link[^>]+href="([^"]+)"')
        if not link:
            continue
        eintraege.append((html.unescape(_TAGS.sub("", titel)).strip(),
                          html.unescape(link).strip()))
    return eintraege


def _first(text: str, muster: str) -> str:
    m = re.search(muster, text, re.S)
    return m.group(1) if m else ""


SUCH_FUNKTIONEN = {
    "searxng": suche_searxng,
    "duckduckgo": suche_duckduckgo,
    "themenpool": suche_themenpool,
}


def suche(frage: str, ssot: dict, limit: int | None = None,
          timeout: int | None = None) -> dict:
    """Sucht über die Anbieterkette. Erster Treffer gewinnt, Rest bleibt Rückfall."""
    budget = (ssot.get("antwortwerk") or {}).get("budget") or {}
    limit = limit or int(budget.get("max_treffer_suche", 12))
    timeout = timeout or int(budget.get("timeout_sekunden", 30))

    versuche: list[dict] = []
    for anbieter in such_anbieter(ssot):
        aid = anbieter.get("id")
        status = such_status(anbieter)
        if status["zustand"] != BEREIT:
            versuche.append({"anbieter": aid, "ergebnis": status["zustand"],
                             "hinweis": status["grund"]})
            continue
        fn = SUCH_FUNKTIONEN.get(aid)
        if not fn:
            versuche.append({"anbieter": aid, "ergebnis": DEFEKT,
                             "hinweis": "kein Adapter hinterlegt"})
            continue
        treffer, fehler = fn(frage, anbieter, limit, timeout)
        if treffer:
            versuche.append({"anbieter": aid, "ergebnis": "treffer",
                             "hinweis": f"{len(treffer)} Ergebnisse"})
            return {"treffer": treffer, "anbieter": aid, "versuche": versuche}
        versuche.append({"anbieter": aid, "ergebnis": "leer",
                         "hinweis": fehler or "keine Treffer"})
    return {"treffer": [], "anbieter": None, "versuche": versuche}


# ======================================================================
#  GEWERK 2 – LESER (Crawl4AI)
# ======================================================================
def leser_status(ssot: dict) -> dict:
    """Welcher Leseweg steht bereit? Reihenfolge: crawl4ai → jina → urllib."""
    g = gewerk(ssot, "leser")
    if _modul_da("crawl4ai"):
        return {"id": "leser", "zustand": BEREIT, "weg": "crawl4ai",
                "grund": "Crawl4AI installiert (Volltext → Markdown)"}
    rueckfall = g.get("rueckfall") or ["jina", "urllib"]
    return {"id": "leser", "zustand": BEREIT, "weg": rueckfall[0],
            "grund": "Crawl4AI nicht installiert – Rückfall aktiv "
                     "(pip install -r requirements-werkbank.txt)"}


def _lies_crawl4ai(urls: list[str], max_zeichen: int, timeout: int) -> dict[str, dict]:
    """Volltext über Crawl4AI. Läuft im eigenen Event-Loop, isoliert."""
    import asyncio

    from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
    from crawl4ai.content_filter_strategy import PruningContentFilter
    from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

    async def lauf() -> dict[str, dict]:
        md = DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(threshold=0.48, threshold_type="fixed"))
        cfg = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            markdown_generator=md,
            excluded_tags=["nav", "footer", "aside", "form"],
            exclude_external_links=True,
            page_timeout=timeout * 1000,
        )
        ergebnis: dict[str, dict] = {}
        async with AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False)) as c:
            for res in await c.arun_many(urls=urls, config=cfg):
                if not getattr(res, "success", False):
                    ergebnis[res.url] = {"fehler": getattr(res, "error_message", "unbekannt")}
                    continue
                # fit_markdown ist der entrümpelte Hauptinhalt; raw als Rückfall.
                mdobj = getattr(res, "markdown", None)
                text = (getattr(mdobj, "fit_markdown", "") or
                        getattr(mdobj, "raw_markdown", "") or str(mdobj or ""))
                ergebnis[res.url] = {"text": text[:max_zeichen], "weg": "crawl4ai"}
        return ergebnis

    return asyncio.run(lauf())


def _lies_jina(url: str, max_zeichen: int, timeout: int) -> dict:
    """Jina Reader – schlüsselfrei, liefert Klartext. Bestehender Hausweg."""
    text, fehler = _hole(f"https://r.jina.ai/{url}", timeout=timeout)
    if fehler:
        return {"fehler": f"Jina Reader: {fehler}"}
    return {"text": re.sub(r"\n{3,}", "\n\n", text).strip()[:max_zeichen], "weg": "jina"}


# Beiwerk, das nie in eine zitierte Passage gehört. Crawl4AI erledigt das
# mit dem PruningContentFilter, der Browser-Beweis per DOM-Entfernung –
# die unterste Ebene braucht dieselbe Disziplin, sonst landet
# „Navigation Impressum" mitten im Beleg.
_BEIWERK = re.compile(
    r"<(script|style|noscript|nav|footer|header|aside|form|head)[^>]*>.*?</\1>",
    re.S | re.I)


def _lies_urllib(url: str, max_zeichen: int, timeout: int) -> dict:
    """Letzte Ebene: rohes HTML, Beiwerk und Tags raus. Nie offline."""
    roh, fehler = _hole(url, timeout=timeout)
    if fehler:
        return {"fehler": f"Direktabruf: {fehler}"}
    text = _BEIWERK.sub(" ", roh)
    text = _TAGS.sub(" ", text)
    text = html.unescape(re.sub(r"[ \t]{2,}", " ", text))
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return {"text": text[:max_zeichen], "weg": "urllib"}


def lies(urls: list[str], ssot: dict, max_zeichen: int | None = None,
         timeout: int | None = None) -> dict[str, dict]:
    """Liest Seiten zu Markdown/Klartext. Fällt still von Stufe zu Stufe."""
    budget = (ssot.get("antwortwerk") or {}).get("budget") or {}
    max_zeichen = max_zeichen or int(budget.get("max_zeichen_je_seite", 6000))
    timeout = timeout or int(budget.get("timeout_sekunden", 30))
    if not urls:
        return {}

    if _modul_da("crawl4ai"):
        try:
            ergebnis = _lies_crawl4ai(urls, max_zeichen, timeout)
            # Crawl4AI kann einzelne Seiten verfehlen – die holt der Rückfall.
            fehlend = [u for u in urls if not (ergebnis.get(u) or {}).get("text")]
            for u in fehlend:
                ergebnis[u] = _lies_jina(u, max_zeichen, timeout)
            return ergebnis
        except Exception as exc:  # noqa: BLE001 – Crawl4AI darf nie den Lauf killen
            print(f"⚠ Crawl4AI-Lauf gescheitert ({type(exc).__name__}) – Rückfall aktiv.")

    ergebnis: dict[str, dict] = {}
    for u in urls:
        res = _lies_jina(u, max_zeichen, timeout)
        if not res.get("text"):
            res = _lies_urllib(u, max_zeichen, timeout)
        ergebnis[u] = res
    return ergebnis


# ======================================================================
#  GEWERK 3 – BROWSER (Playwright)
# ======================================================================
def browser_status(ssot: dict) -> dict:
    """Ist der Browser-Beweis startbar? Prüft Brücke + node, nie das Netz."""
    cfg = ssot.get("browser") or {}
    bruecke = ROOT / (cfg.get("bruecke") or "tools/werkbank/render.mjs")
    if not bruecke.is_file():
        return {"id": "browser", "zustand": DEFEKT,
                "grund": f"Brücke fehlt: {cfg.get('bruecke')}"}
    if not shutil.which("node"):
        return {"id": "browser", "zustand": STANDBY, "grund": "node nicht im PATH"}
    if not (ROOT / "node_modules" / "playwright-core").is_dir():
        return {"id": "browser", "zustand": STANDBY,
                "grund": "playwright-core fehlt (npm ci)"}
    return {"id": "browser", "zustand": BEREIT, "grund": "Chromium-Beweis startbar"}


def browser_beweis(url: str, ssot: dict, suchbegriffe: list[str] | None = None) -> dict:
    """Rendert eine Seite wirklich und meldet, was dort steht.

    Das ist der Teil, den eine Snippet-API nicht kann: Wir sehen, ob die
    zitierte Seite die Aussage überhaupt trägt – und ob sie ohne
    JavaScript-Fehler erreichbar ist.
    """
    status = browser_status(ssot)
    if status["zustand"] != BEREIT:
        return {"zustand": status["zustand"], "grund": status["grund"], "url": url}

    cfg = ssot.get("browser") or {}
    bruecke = ROOT / (cfg.get("bruecke") or "tools/werkbank/render.mjs")
    argumente = ["node", str(bruecke), "--url", url,
                 "--timeout", str(cfg.get("timeout_ms", 20000))]
    for begriff in (suchbegriffe or [])[:5]:
        argumente += ["--suche", begriff]
    try:
        proc = subprocess.run(argumente, capture_output=True, text=True,
                              timeout=int(cfg.get("timeout_ms", 20000)) / 1000 + 30,
                              cwd=str(ROOT))
    except subprocess.TimeoutExpired:
        return {"zustand": DEFEKT, "grund": "Browser-Beweis lief in den Timeout", "url": url}
    if proc.returncode != 0:
        kurz = (proc.stderr or "").strip().splitlines()
        return {"zustand": DEFEKT, "url": url,
                "grund": kurz[-1][:200] if kurz else f"Exit {proc.returncode}"}
    try:
        daten = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"zustand": DEFEKT, "grund": "Brücke lieferte kein JSON", "url": url}
    daten["zustand"] = BEREIT
    return daten


# ======================================================================
#  GEWERK 4 – KONNEKTOR (Composio)
# ======================================================================
def konnektor_status(ssot: dict) -> dict:
    """Composio-Bereitschaft. Schlüssel fehlt = Standby, nicht Fehler (B3)."""
    g = gewerk(ssot, "konnektor")
    schluessel = _env(g.get("env"))
    if not schluessel:
        return {"id": "konnektor", "zustand": STANDBY,
                "grund": f"{g.get('env')} nicht gesetzt – Konnektor schläft"}
    freigabe = g.get("freigabe") or {}
    erlaubt = freigabe.get("erlaubte_aktionen") or []
    if not erlaubt:
        return {"id": "konnektor", "zustand": STANDBY,
                "grund": "Schlüssel vorhanden, aber keine Aktion freigegeben "
                         "(data/werkbank.yaml → freigabe.erlaubte_aktionen)"}
    if not _modul_da("composio"):
        return {"id": "konnektor", "zustand": STANDBY,
                "grund": "composio-SDK nicht installiert – REST-Weg wird genutzt"}
    return {"id": "konnektor", "zustand": BEREIT,
            "grund": f"{len(erlaubt)} Aktion(en) freigegeben"}


def konnektor_toolkits(ssot: dict, limit: int = 20) -> tuple[list[dict], str | None]:
    """LESENDER Probeabruf: Welche Toolkits stehen bereit? Beweist den Zugang."""
    g = gewerk(ssot, "konnektor")
    schluessel = _env(g.get("env"))
    if not schluessel:
        return [], "Kein COMPOSIO_API_KEY – Standby"
    basis = (g.get("basis_url") or "https://backend.composio.dev/api/v3.1").rstrip("/")
    text, fehler = _hole(f"{basis}/toolkits?limit={limit}", timeout=30,
                         headers={"x-api-key": schluessel})
    if fehler:
        return [], f"Composio nicht erreichbar ({fehler})"
    try:
        daten = json.loads(text)
    except json.JSONDecodeError:
        return [], "Composio-Antwort nicht lesbar"
    roh = daten.get("items") if isinstance(daten, dict) else daten
    return [{"slug": t.get("slug"), "name": t.get("name")}
            for t in (roh or [])][:limit], None


def konnektor_ausfuehren(slug: str, argumente: dict, ssot: dict,
                         trocken: bool = True) -> dict:
    """Führt eine Composio-Aktion aus – mit zwei Schlössern davor (B4).

    Schloss 1: Die Aktion muss in `freigabe.erlaubte_aktionen` stehen.
    Schloss 2: Ist `trockenlauf_pflicht` gesetzt, ist `trocken=False` nur
               zulässig, wenn der Aufrufer es ausdrücklich erzwingt.
    """
    g = gewerk(ssot, "konnektor")
    freigabe = g.get("freigabe") or {}
    erlaubt = freigabe.get("erlaubte_aktionen") or []
    if slug not in erlaubt:
        return {"zustand": "verweigert", "slug": slug,
                "grund": "Aktion steht nicht auf der Freigabeliste "
                         "(data/werkbank.yaml → konnektor.freigabe)"}
    schluessel = _env(g.get("env"))
    # Der Trockenlauf kommt VOR der Schlüsselprüfung: Er plant nur und
    # sendet nie. Wer vorher wissen will, was passieren würde, soll das
    # auch ohne hinterlegtes Secret können.
    if trocken:
        return {"zustand": "trockenlauf", "slug": slug, "argumente": argumente,
                "schluessel_vorhanden": bool(schluessel),
                "grund": "Trockenlauf – es wurde nichts ausgeführt"
                         + ("" if schluessel else " (Schlüssel fehlt ohnehin)")}
    if not schluessel:
        return {"zustand": STANDBY, "slug": slug, "grund": "kein COMPOSIO_API_KEY"}

    basis = (g.get("basis_url") or "https://backend.composio.dev/api/v3.1").rstrip("/")
    nutzlast = json.dumps({
        "user_id": (ssot.get("konnektor") or {}).get("nutzer_id", "default"),
        "arguments": argumente,
    }).encode()
    try:
        req = urllib.request.Request(
            f"{basis}/tools/execute/{urllib.parse.quote(slug)}", data=nutzlast,
            headers={"x-api-key": schluessel, "Content-Type": "application/json",
                     "User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as antw:
            return {"zustand": "ausgefuehrt", "slug": slug,
                    "antwort": json.loads(antw.read().decode("utf-8", errors="replace"))}
    except Exception as exc:  # noqa: BLE001
        return {"zustand": DEFEKT, "slug": slug, "grund": f"{type(exc).__name__}: {exc}"}


# ======================================================================
#  GESAMTBILD
# ======================================================================
def gesamtlage(ssot: dict) -> dict:
    """Ein Blick auf alle vier Gewerke – ohne einen einzigen Netzaufruf."""
    such_zustaende = [such_status(a) for a in such_anbieter(ssot)]
    bester_such = next((s for s in such_zustaende if s["zustand"] == BEREIT), None)
    antwort = {
        "id": "antwortwerk",
        "zustand": BEREIT if bester_such else STANDBY,
        "grund": (f"Suche über {bester_such['id']}" if bester_such
                  else "kein Suchanbieter bereit"),
        "suche": such_zustaende,
        "synthese": synthese_zustaende(ssot),
    }
    return {
        "zeitpunkt": jetzt_iso(),
        "gewerke": [antwort, leser_status(ssot), browser_status(ssot),
                    konnektor_status(ssot)],
    }


def synthese_zustaende(ssot: dict) -> list[dict]:
    zustaende = []
    for s in (ssot.get("antwortwerk") or {}).get("synthese") or []:
        if not s.get("schluessel_noetig"):
            zustaende.append({"id": s.get("id"), "zustand": BEREIT,
                              "grund": "schlüsselfrei"})
        elif _env(s.get("env")):
            zustaende.append({"id": s.get("id"), "zustand": BEREIT,
                              "grund": f"{s.get('env')} gesetzt"})
        else:
            zustaende.append({"id": s.get("id"), "zustand": STANDBY,
                              "grund": f"{s.get('env')} nicht gesetzt"})
    return zustaende
