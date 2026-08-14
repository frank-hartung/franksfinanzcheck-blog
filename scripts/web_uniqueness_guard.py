#!/usr/bin/env python3
# ============================================================
#  WEB-UNIQUENESS-GUARD – Profi-Level Duplicate-Content-Prüfung
#  (13.08.2026, Frank: "Tool zur Prüfung von Unique Content mit
#  Selbstheilung – Web-Duplikate, interne Duplikate, Crawl nach
#  Duplicate Content, Indexierungsprobleme.")
#
#  ARBEITSTEILUNG mit bestehenden Wachen (keine Doppelarbeit):
#    - INTERNE Duplikate (Shingle-Jaccard übers eigene Corpus,
#      Fingerprint-Registry) macht bereits scripts/plagiat_guard.py.
#    - Content-TIEFE/Folgefragen/Sonderfälle macht das neue
#      scripts/content_depth_guard.py (separates Skript).
#    - DIESES Skript deckt die verbleibende Lücke ab:
#
#  W1  WEB-DUPLIKAT-SUCHE (optional, braucht API-Key): entnimmt jedem
#      Artikel 2 unverwechselbare ~12-Wort-Phrasen (Body, kein CTA/
#      Disclaimer-Boilerplate) und sucht sie als Exakt-Phrase über die
#      Google Programmable Search Engine (Custom Search JSON API,
#      kostenlos bis 100 Anfragen/Tag). Taucht eine Phrase auf einer
#      FREMDEN Domain auf → Fund. Ohne Key: sauberer Exit mit
#      Setup-Anleitung (wie social_poster.py/mastodon_profile_sync.py).
#  W2  TECHNISCHER SITE-CRAWL: liest den kompletten Hugo-Build
#      (public/) und gruppiert ALLE echten Seiten (keine Alias-
#      Redirect-Stubs, keine Thin-Taxonomie) nach exaktem <title> bzw.
#      Meta-Description. Mehr als 1 Seite pro Gruppe = technischer
#      Duplicate-Content-Fund.
#  W3  KANONISIERUNGS-AUDIT: jede echte Seite braucht eine gültige
#      rel=canonical (selbstreferenzierend oder bewusst auf ein Ziel,
#      das seinerseits real/index-fähig ist – keine Kanonisierungs-
#      Ketten, keine widersprüchlichen Signale). Redirect-Stubs
#      (Hugo-Aliase) müssen korrekt auf ihr Ziel zeigen – das ist der
#      GEWÜNSCHTE Zustand, kein Fund.
#  W4  INDEXIERUNGS-AUDIT: robots-Meta konsistent mit der Thin-
#      Taxonomie-Regel (< 4 Artikel -> noindex,follow); Sitemap enthält
#      exakt die erwartete Seitenmenge (keine Thin-Taxonomie, keine
#      Redirect-Stubs); IndexNow-Einreichungsstatus als Proxy für
#      Einreichung (NICHT für tatsächliche Aufnahme in den Google-Index
#      – das kann nur die Google Search Console API beantworten, siehe
#      ANLEITUNG-GOOGLE-SEARCH-CONSOLE.md, hier bewusst offen gelassen
#      wie schon bei cadence_manager.py).
#
#  AKTUELLER STAND DER SPIELREGELN (recherchiert 14.08.2026, Quellen in
#  SEO-STANDARDS-2026.md): Google kennt KEINE "Duplicate-Content-Strafe"
#  auf Basis einer Prozent-Schwelle (verbreiteter Mythos) – es
#  konsolidiert stattdessen per Kanonisierung auf eine bevorzugte URL.
#  Das eigentliche Risiko für eine KI-Content-Seite wie diese ist
#  "Scaled Content Abuse" (Google-Spam-Richtlinie, verschärft durch das
#  März-2026-Core-Update, seit 15.05.2026 explizit auch für AI Overviews
#  gültig): viele Seiten mit wenig echtem Mehrwert. Gegenmittel laut
#  Google: echte Tiefe/Originalität pro Artikel, sichtbare Autorenschaft
#  (E-E-A-T), keine Schablonen-Struktur. Dieses Skript prüft die
#  TECHNISCHE Seite davon; content_depth_guard.py die inhaltliche.
#
#  SELBSTHEILUNG (bewusst eng begrenzt): doppelte Meta-Description ist
#  die einzige hier sicher automatisch behebbare Ursache (Trigger:
#  meta_optimizer.py --fix). Alles andere (externe Kopien, Template-
#  Bugs bei Titel/Canonical) braucht redaktionelles bzw. Entwickler-
#  Urteilsvermögen -> Report + Exit 1 (Fehler-Alerting).
#
#  Aufruf:
#    python3 scripts/web_uniqueness_guard.py            # voller Check
#    python3 scripts/web_uniqueness_guard.py --dry-run  # ohne Heilung
#    python3 scripts/web_uniqueness_guard.py --json
#
#  Voraussetzung: `hugo --minify` muss vorher gelaufen sein (liest
#  public/, wie seo_audit.py/publish_gate.py es auch tun).
# ============================================================

import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
PUBLIC = ROOT / "public"
POSTS_DIR = ROOT / "content" / "posts"
REPORT = ROOT / "WEB-UNIQUENESS-REPORT.md"
CACHE_FILE = ROOT / "data" / "web_uniqueness_cache.json"
BASE_URL = "https://franksfinanzcheck.de"

DRY_RUN = "--dry-run" in sys.argv
AS_JSON = "--json" in sys.argv

GOOGLE_CSE_KEY = (os.environ.get("GOOGLE_CSE_API_KEY") or "").strip()
GOOGLE_CSE_CX = (os.environ.get("GOOGLE_CSE_CX") or "").strip()
CSE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"
CSE_MAX_QUERIES_PER_RUN = int(os.environ.get("WEB_UNIQUENESS_MAX_QUERIES") or "20")
CACHE_DAYS = 21  # eine geprüfte Phrase erst nach 3 Wochen erneut abfragen (Free-Tier schonen)


# ------------------------------------------------------------------ HTML-Parsing

class PageMeta(HTMLParser):
    """Robuster HTML-Meta-Parser (kein Regex – minifiziertes HTML kann
    Attribut-Reihenfolge/Anführungszeichen beliebig setzen)."""

    def __init__(self):
        super().__init__()
        self.title = None
        self.description = None
        self.canonical = None
        self.robots = None
        self.is_redirect_stub = False
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = (a.get("name") or "").lower()
            if name == "description" and self.description is None:
                self.description = a.get("content")
            elif name == "robots":
                self.robots = a.get("content")
            if (a.get("http-equiv") or "").lower() == "refresh":
                self.is_redirect_stub = True
        elif tag == "link" and (a.get("rel") or "").lower() == "canonical":
            self.canonical = a.get("href")

    def handle_data(self, data):
        if self._in_title and self.title is None:
            self.title = data.strip()

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False


def parse_page(path: Path) -> PageMeta:
    html = path.read_text(encoding="utf-8", errors="ignore")
    p = PageMeta()
    p.feed(html)
    return p


def url_for(html_path: Path) -> str:
    rel = html_path.relative_to(PUBLIC).parent
    rel_str = str(rel).replace(os.sep, "/")
    if rel_str == ".":
        return BASE_URL + "/"
    return f"{BASE_URL}/{rel_str}/"


def norm_url(u: str) -> str:
    """Normalisiert URLs für Vergleiche: Hugo/Browser percent-encoden
    Umlaute etc. im href-Attribut (z. B. 'ä' -> '%C3%A4'), während dieses
    Skript Pfade direkt aus dem Dateisystem baut (unkodiert). Ohne diese
    Normalisierung meldet der Canonical-Vergleich für jede Umlaut-URL
    einen Falsch-Fund."""
    if not u:
        return u
    return urllib.parse.unquote(u)


def is_affiliate_redirect(url: str) -> bool:
    """Die /go/<key>/-Kurzlinks sind ABSICHTLICH externe Redirects
    (Affiliate-Cloaking auf a.check24.net / a.partner-versicherung.de,
    siehe scripts/check24_links.yaml) – kein interner Alias, der auf eine
    eigene Seite zeigen müsste."""
    return "/go/" in url


def all_pages() -> list[tuple[Path, PageMeta, str]]:
    """Alle index.html unter public/, jeweils mit geparsten Metadaten +
    voller URL."""
    out = []
    for html_path in sorted(PUBLIC.rglob("index.html")):
        meta = parse_page(html_path)
        out.append((html_path, meta, url_for(html_path)))
    return out


def is_taxonomy_term_url(url: str) -> bool:
    """Erkennt Taxonomie-TERM-Seiten (/tags/<name>/, /categories/<name>/)
    – NICHT die Taxonomie-Index-Seiten selbst (/tags/, /categories/), die
    Hugo als eigenen Kind='taxonomy' führt und NIE der Thin-Content-Regel
    unterliegt (siehe head.html: nur Kind=='term' zählt)."""
    return bool(re.match(r"^https?://[^/]+/(tags|categories)/[^/]+/(page/\d+/)?$", url))


def term_slug_and_count(url: str, tag_counts: dict, cat_counts: dict):
    m = re.match(r"^https?://[^/]+/(tags|categories)/([^/]+)/", url)
    if not m:
        return None
    kind, slug = m.group(1), urllib.parse.unquote(m.group(2))
    counts = tag_counts if kind == "tags" else cat_counts
    return counts.get(slug, 0)


def build_taxonomy_counts():
    """Zählt Tags/Kategorien direkt aus den Frontmatter-Quellen – exakte
    Nachbildung von Hugos len(.Pages) pro Taxonomie-Term, damit die
    Thin-Content-Prüfung (< 4 Artikel -> noindex) hier genauso rechnet
    wie layouts/_partials/head.html."""
    from collections import Counter
    tag_counts, cat_counts = Counter(), Counter()
    for slug_dir in POSTS_DIR.iterdir():
        index_md = slug_dir / "index.md"
        if not index_md.is_file():
            continue
        text = index_md.read_text(encoding="utf-8", errors="ignore")
        if not text.startswith("---") or text.count("---") < 2:
            continue
        fm = text.split("---", 2)[1]
        if re.search(r"^draft:\s*true\s*$", fm, re.MULTILINE):
            continue
        tm = re.search(r"^tags:\s*(\[.*?\])\s*$", fm, re.MULTILINE)
        if tm:
            try:
                for t in json.loads(tm.group(1)):
                    tag_counts[slugify_taxonomy(t)] += 1
            except (json.JSONDecodeError, ValueError):
                pass
        cm = re.search(r"^categories:\s*(\[.*?\])\s*$", fm, re.MULTILINE)
        if cm:
            try:
                for c in json.loads(cm.group(1)):
                    cat_counts[slugify_taxonomy(c)] += 1
            except (json.JSONDecodeError, ValueError):
                pass
    return tag_counts, cat_counts


def slugify_taxonomy(name: str) -> str:
    """Grobe Nachbildung von Hugos Standard-Slugifizierung für Tag-/
    Kategorie-URLs (Kleinschreibung, Leerzeichen -> Bindestrich)."""
    s = name.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s_]+", "-", s)
    return s


# ------------------------------------------------------------------ W2 + W3: Crawl, Titel/Desc-Duplikate, Canonical

def is_taxonomy_url(url: str) -> bool:
    """Breite Erkennung: irgendeine Tag-/Kategorie-bezogene Seite (Index
    oder Term). Für den Titel-/Description-Duplikat-Vergleich werden ALLE
    davon ausgeschlossen (Vorlagen-Titel wie 'Schufa – Alle Artikel' sind
    gewollt gleich strukturiert, kein echtes Duplicate-Content-Risiko)."""
    return "/tags/" in url or "/categories/" in url


def crawl_site():
    pages = all_pages()
    real_pages = [(p, m, u) for p, m, u in pages if not m.is_redirect_stub]
    redirect_pages = [(p, m, u) for p, m, u in pages if m.is_redirect_stub]

    # Nur "substantielle" Seiten (Artikel, Pillar, Startseite, Über-uns
    # etc. – NICHT Taxonomie/Pagination) fließen in den Titel-/
    # Description-Duplikat-Vergleich ein, sonst wären z. B. alle
    # Tag-Seiten mit generischer Vorlagen-Description Falschfunde.
    substantial = [(p, m, u) for p, m, u in real_pages
                   if not is_taxonomy_url(u) and "/page/" not in u]

    from collections import defaultdict
    by_title = defaultdict(list)
    by_desc = defaultdict(list)
    for _, m, u in substantial:
        if m.title:
            by_title[m.title].append(u)
        if m.description:
            by_desc[m.description].append(u)

    dup_titles = {k: v for k, v in by_title.items() if len(v) > 1}
    dup_descs = {k: v for k, v in by_desc.items() if len(v) > 1}

    # W3 Canonical-Audit
    canonical_problems = []
    real_urls = {u for _, _, u in real_pages}
    real_urls_norm = {norm_url(u) for u in real_urls}
    for _, m, u in real_pages:
        if not m.canonical:
            canonical_problems.append(f"{u}: kein rel=canonical gesetzt")
            continue
        if m.is_redirect_stub:
            continue  # Ziel-Prüfung für Redirect-Stubs folgt separat
        # Self-referencing ist der Normalfall; ein bewusst abweichendes
        # Ziel muss auf eine ECHTE, ebenfalls indexierbare Seite zeigen
        # (keine Kanonisierungs-Kette auf eine Thin-/Redirect-Seite).
        canon_norm = norm_url(m.canonical)
        if canon_norm != norm_url(u) and canon_norm not in real_urls_norm:
            canonical_problems.append(
                f"{u}: canonical zeigt auf '{m.canonical}', das nicht im Crawl als reale Seite gefunden wurde"
            )

    # Redirect-Stubs (Hugo-Aliase + /go/-Affiliate-Kurzlinks): interne
    # Alias-Ziele müssen real sein; /go/-Links dürfen (=sollen) auf
    # externe Affiliate-URLs zeigen.
    redirect_problems = []
    for _, m, u in redirect_pages:
        if not m.canonical:
            redirect_problems.append(f"{u}: Redirect-Stub ohne canonical-Ziel")
            continue
        if is_affiliate_redirect(u):
            if not m.canonical.startswith("http"):
                redirect_problems.append(f"{u}: Affiliate-Redirect ohne gültige externe Ziel-URL")
            continue
        if norm_url(m.canonical) not in real_urls_norm:
            redirect_problems.append(f"{u}: Redirect zeigt auf '{m.canonical}', kein reales Ziel im Crawl gefunden")

    return {
        "total_pages": len(pages),
        "real_pages": len(real_pages),
        "redirect_pages": len(redirect_pages),
        "substantial_checked": len(substantial),
        "dup_titles": dup_titles,
        "dup_descriptions": dup_descs,
        "canonical_problems": canonical_problems,
        "redirect_problems": redirect_problems,
    }


# ------------------------------------------------------------------ W4: Indexierungs-/Sitemap-Audit

def audit_indexation(crawl):
    problems = []
    pages = all_pages()
    tag_counts, cat_counts = build_taxonomy_counts()

    def expected_thin(url: str) -> bool | None:
        """None = keine Taxonomie-Term-Seite (Regel gilt nicht), sonst
        True/False je nach echter Artikelanzahl für diesen Term (exakte
        Nachbildung von head.html: Kind=='term' and len(.Pages) < 4)."""
        if not is_taxonomy_term_url(url):
            return None
        count = term_slug_and_count(url, tag_counts, cat_counts)
        return (count or 0) < 4

    thin_urls = set()
    # Thin-Taxonomie-Terme müssen noindex,follow sein; alle anderen
    # substantiellen/Term-Seiten müssen index,follow sein (Produktion).
    for _, m, u in pages:
        if m.is_redirect_stub or "/page/" in u:
            continue
        thin = expected_thin(u)
        if thin is True:
            thin_urls.add(u)
            if m.robots and "noindex" not in m.robots:
                problems.append(f"{u}: erwartet noindex (< 4 Artikel für diesen Term), tatsächlich robots='{m.robots}'")
        elif m.robots and "noindex" in m.robots:
            problems.append(f"{u}: fälschlich noindex, obwohl kein Thin-Taxonomie-Fall (robots='{m.robots}')")

    # Sitemap-Konsistenz: keine Thin-Taxonomie-Terme, keine Redirect-Stubs
    sitemap_path = PUBLIC / "sitemap.xml"
    if sitemap_path.is_file():
        sitemap_text = sitemap_path.read_text(encoding="utf-8", errors="ignore")
        sitemap_urls = {norm_url(u) for u in re.findall(r"<loc>([^<]+)</loc>", sitemap_text)}
        redirect_urls = {norm_url(u) for _, m, u in pages if m.is_redirect_stub}
        thin_urls_norm = {norm_url(u) for u in thin_urls}
        leaked = (sitemap_urls & redirect_urls) | (sitemap_urls & thin_urls_norm)
        if leaked:
            problems.append(f"Sitemap enthält {len(leaked)} URL(s), die eigentlich ausgeschlossen sein sollten: "
                             + ", ".join(sorted(leaked)[:5]))
    else:
        problems.append("public/sitemap.xml fehlt (hugo --minify vorher ausgeführt?)")

    # IndexNow-Einreichungs-Proxy (NICHT: tatsächliche Google-Aufnahme)
    indexnow_state = ROOT / ".indexnow_submitted.json"
    submitted = set()
    if indexnow_state.is_file():
        try:
            submitted = set(json.loads(indexnow_state.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            pass
    live_post_urls = {
        u for _, m, u in pages
        if re.match(r"^https?://[^/]+/posts/[^/]+/$", u) and "/page/" not in u
        and not m.is_redirect_stub and (not m.robots or "noindex" not in m.robots)
    }
    not_submitted = sorted(u for u in live_post_urls if u not in submitted)
    if not_submitted:
        problems.append(f"{len(not_submitted)} Artikel noch nicht bei IndexNow eingereicht: "
                         + ", ".join(not_submitted[:5]))

    return problems


# ------------------------------------------------------------------ W1: Web-Duplikat-Suche (optional)

BOILERPLATE_MARKERS = (
    "jetzt vergleichen und sparen", "affiliate-links", "dieser artikel enthält",
    "häufige fragen", "schnell-tipp von franksfinanzcheck",
)


def extract_phrases(body: str, n: int = 2, words: int = 12) -> list[str]:
    """Entnimmt N unverwechselbare ~12-Wort-Phrasen aus dem Artikeltext,
    Boilerplate/CTA-Blöcke ausgeschlossen."""
    # grobe Markdown-Bereinigung
    text = re.sub(r"```.*?```", " ", body, flags=re.DOTALL)
    text = re.sub(r"[#*_>`\[\]]", " ", text)
    text = re.sub(r"\(https?://[^)]*\)", " ", text)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    candidates = []
    for s in sentences:
        s_clean = s.strip()
        low = s_clean.lower()
        if any(m in low for m in BOILERPLATE_MARKERS):
            continue
        word_list = s_clean.split()
        if len(word_list) < words:
            continue
        candidates.append(" ".join(word_list[:words]))
    # Bevorzugt Phrasen aus der Mitte des Artikels (Intro/Outro sind oft generischer)
    mid_start = len(candidates) // 4
    ordered = candidates[mid_start:] + candidates[:mid_start]
    return ordered[:n]


def load_cache() -> dict:
    if CACHE_FILE.is_file():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {}
    return {}


def save_cache(cache: dict) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")


def cse_search(phrase: str) -> list[str]:
    params = urllib.parse.urlencode({
        "key": GOOGLE_CSE_KEY, "cx": GOOGLE_CSE_CX, "q": f'"{phrase}"', "num": 5,
    })
    req = urllib.request.Request(f"{CSE_ENDPOINT}?{params}")
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode())
    return [item.get("link", "") for item in data.get("items", [])]


def web_duplicate_check():
    if not GOOGLE_CSE_KEY or not GOOGLE_CSE_CX:
        return None, (
            "Kein GOOGLE_CSE_API_KEY/GOOGLE_CSE_CX gesetzt – Web-Duplikat-Suche übersprungen.\n"
            "AKTIVIEREN (kostenlos, ~5 Minuten, 100 Anfragen/Tag gratis):\n"
            "  1. https://programmablesearchengine.google.com/ -> Neue Suchmaschine ->\n"
            "     'Gesamtes Web durchsuchen' aktivieren -> Suchmaschinen-ID (cx) kopieren.\n"
            "  2. https://console.cloud.google.com/apis/library/customsearch.googleapis.com\n"
            "     -> aktivieren -> API-Key erzeugen.\n"
            "  3. GitHub-Repo -> Settings -> Secrets and variables -> Actions:\n"
            "     Secret GOOGLE_CSE_API_KEY, Variable GOOGLE_CSE_CX.\n"
            "  Details: ANLEITUNG-WEB-DUPLICATE-CHECK.md"
        )

    cache = load_cache()
    now = time.time()
    findings = []
    queries_used = 0

    for slug_dir in sorted(POSTS_DIR.iterdir()):
        index_md = slug_dir / "index.md"
        if not index_md.is_file():
            continue
        text = index_md.read_text(encoding="utf-8")
        if not text.startswith("---") or text.count("---") < 2:
            continue
        fm_raw, body = text.split("---", 2)[1], text.split("---", 2)[2]
        if re.search(r"^draft:\s*true\s*$", fm_raw, re.MULTILINE):
            continue
        slug = slug_dir.name

        for phrase in extract_phrases(body):
            cache_key = f"{slug}::{hash(phrase) & 0xffffffff}"
            cached = cache.get(cache_key)
            if cached and (now - cached.get("ts", 0)) < CACHE_DAYS * 86400:
                if cached.get("external_hits"):
                    findings.append({"slug": slug, "phrase": phrase, "hits": cached["external_hits"], "cached": True})
                continue
            if queries_used >= CSE_MAX_QUERIES_PER_RUN:
                continue
            queries_used += 1
            try:
                links = cse_search(phrase)
            except urllib.error.HTTPError as exc:
                cache[cache_key] = {"ts": now, "external_hits": [], "error": f"HTTP {exc.code}"}
                continue
            except Exception as exc:  # noqa: BLE001
                cache[cache_key] = {"ts": now, "external_hits": [], "error": str(exc)[:150]}
                continue
            external = [link for link in links if "franksfinanzcheck.de" not in link]
            cache[cache_key] = {"ts": now, "external_hits": external}
            if external:
                findings.append({"slug": slug, "phrase": phrase, "hits": external, "cached": False})

    save_cache(cache)
    return findings, None


# ------------------------------------------------------------------ Selbstheilung

def heal_duplicate_descriptions(dup_descs: dict) -> list[str]:
    """meta_optimizer.py --fix prüft nur JEDEN Artikel für sich (Länge/
    Keyword-Präsenz) und kennt keine Cross-Artikel-Duplikate – ein
    inhaltlich einwandfreier, aber zufällig identischer Text bleibt dort
    unangetastet. Deshalb wird hier gezielt für jede Duplikat-Gruppe die
    JÜNGERE Seite (der ÄLTERE Artikel behält seinen Text, Priorität wie
    bei plagiat_guard.py's Klon-Quarantäne) über meta_optimizer.py's
    eigene generate_description()/ai_description()-Funktion neu
    beschrieben (echte Wiederverwendung statt Parallel-Code)."""
    if not dup_descs:
        return []

    if "meta_optimizer" in sys.modules:
        del sys.modules["meta_optimizer"]
    mo = __import__("meta_optimizer")
    articles = {a["slug"]: a for a in mo.load_articles()}
    use_ai = bool(os.environ.get("GROQ_API_KEY") or os.environ.get("GEMINI_API_KEY"))

    healed_slugs = []
    for desc, urls in dup_descs.items():
        # Nach Datum im Slug sortieren (YYYY-MM-DD-... Präfix) – älteste
        # Seite zuerst, behält ihre Beschreibung.
        slugs = sorted((u.rstrip("/").rsplit("/", 1)[-1] for u in urls))
        for slug in slugs[1:]:
            a = articles.get(slug)
            if not a:
                continue
            try:
                new_desc = mo.ai_description(a) if use_ai else mo.generate_description(a)
            except Exception:  # noqa: BLE001
                new_desc = mo.generate_description(a)
            if not new_desc or new_desc.strip() == a["description"].strip():
                continue
            new_content = re.sub(
                r"^description:\s*.*$", f"description: {new_desc}", a["content"], count=1, flags=re.MULTILINE
            )
            Path(a["path"]).write_text(new_content, encoding="utf-8")
            healed_slugs.append(slug)
    return healed_slugs


# ------------------------------------------------------------------ Main

def main():
    if not PUBLIC.is_dir():
        sys.exit("FEHLER: public/ fehlt – vorher `hugo --minify` ausführen.")

    crawl = crawl_site()
    healed = []
    if crawl["dup_descriptions"] and not DRY_RUN:
        healed = heal_duplicate_descriptions(crawl["dup_descriptions"])
        if healed:
            hugo_bin = shutil.which("hugo") or ("/tmp/hugo" if Path("/tmp/hugo").is_file() else "hugo")
            subprocess.run([hugo_bin, "--minify"], cwd=ROOT, capture_output=True, text=True, timeout=180)
            crawl = crawl_site()  # erneut prüfen nach Heilung

    indexation_problems = audit_indexation(crawl)
    web_findings, web_note = web_duplicate_check()

    hard_problems = (
        list(crawl["dup_titles"].keys())
        + list(crawl["dup_descriptions"].keys())
        + crawl["canonical_problems"]
        + crawl["redirect_problems"]
        + [p for p in indexation_problems if "noch nicht bei IndexNow" not in p]  # IndexNow-Rückstand ist Hinweis, kein hartes Gate
    )
    web_hits = web_findings or []

    if AS_JSON:
        print(json.dumps({
            "crawl": {k: v for k, v in crawl.items() if k not in ()},
            "indexation_problems": indexation_problems,
            "web_duplicate_findings": web_hits,
            "web_check_note": web_note,
            "healed_descriptions": healed,
        }, ensure_ascii=False, indent=2, default=list))
        return 1 if (hard_problems or web_hits) else 0

    lines = [
        "# 🔍 WEB-UNIQUENESS-REPORT (web_uniqueness_guard.py)",
        "",
        f"**Geprüfte Seiten:** {crawl['total_pages']} ({crawl['real_pages']} real, "
        f"{crawl['redirect_pages']} Alias-Redirects) · **Substantiell verglichen:** {crawl['substantial_checked']}",
        f"**Heilung durchgeführt:** {('ja: ' + ', '.join(healed)) if healed else 'nein'}",
        "",
        "## W2/W3 – Technischer Duplicate-Content- & Canonical-Crawl",
    ]
    if not crawl["dup_titles"] and not crawl["dup_descriptions"] and not crawl["canonical_problems"] and not crawl["redirect_problems"]:
        lines.append("🎉 Keine doppelten Titel/Descriptions, keine Canonical-Probleme.")
    else:
        for title, urls in crawl["dup_titles"].items():
            lines.append(f"- ❌ Doppelter Titel „{title}“: {', '.join(urls)}")
        for desc, urls in crawl["dup_descriptions"].items():
            lines.append(f"- ❌ Doppelte Description „{desc[:60]}…“: {', '.join(urls)}")
        for p in crawl["canonical_problems"]:
            lines.append(f"- ❌ Canonical: {p}")
        for p in crawl["redirect_problems"]:
            lines.append(f"- ❌ Redirect: {p}")

    lines.append("")
    lines.append("## W4 – Indexierungs-Audit")
    if not indexation_problems:
        lines.append("🎉 robots-Meta/Sitemap/IndexNow konsistent.")
    else:
        for p in indexation_problems:
            lines.append(f"- ⚠️ {p}")
    lines.append("")
    lines.append(
        "_Hinweis: Dies prüft Einreichbarkeit/Konsistenz, NICHT die tatsächliche Aufnahme in den Google-Index "
        "(dafür wäre die Google Search Console API nötig, siehe ANLEITUNG-GOOGLE-SEARCH-CONSOLE.md)._"
    )

    lines.append("")
    lines.append("## W1 – Web-Duplikat-Suche (externe Kopien)")
    if web_note:
        lines.append(web_note)
    elif not web_hits:
        lines.append("🎉 Keine externen Treffer für die geprüften Textphrasen.")
    else:
        for f in web_hits:
            cached_tag = " (Cache)" if f.get("cached") else ""
            lines.append(f"- ❌ {f['slug']}{cached_tag}: „{f['phrase']}…“ gefunden auf {', '.join(f['hits'])}")

    lines.append("")
    lines.append(
        "---\n_Aktueller Rechtsstand/Google-Richtlinien: siehe SEO-STANDARDS-2026.md. "
        "Selbstheilung nur für doppelte Meta-Descriptions (meta_optimizer.py --fix) – "
        "externe Kopien und Template-Bugs brauchen redaktionelles bzw. Entwickler-Urteilsvermögen."
    )

    report_text = "\n".join(lines)
    print(report_text)
    REPORT.write_text(report_text + "\n", encoding="utf-8")
    return 1 if (hard_problems or web_hits) else 0


if __name__ == "__main__":
    sys.exit(main())
