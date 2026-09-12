#!/usr/bin/env python3
"""schema_seo_gate.py – PREMIUM-GATE: Schema, Social-Tags, Indexierungs-Hygiene.

Warum diese Wache existiert (Audit 11.09.2026):
Der Blog hatte 23 intakte Wachen – keine davon prüfte den INHALT der
JSON-LD-Blöcke. Das Article-Schema war deshalb seit dem Theme-Override
doppelt escaped (`"@id": "\\"https://…\\""`) und damit für Google unbrauchbar:
syntaktisch gültiges JSON, wertseitig kaputt. Presence-Checks ( „Schema da?" )
und `json.loads` ( „JSON gültig?" ) liefen grün. Diese Wache prüft deshalb
Werte, Typen, Datums-Logik, Ziel-Existenz von Bildern und die
Indexierungs-Hygiene der gebauten Site.

Regelwerk (harte Funde => Exit 1):
  S1  JSON-LD     – jeder <script type="application/ld+json">-Block parst
  S2  Escaping    – kein Wert enthält führende/abschließende " (Doppel-Escape)
  S3  Article     – genau ein Article-Block pro Artikel/Ratgeber; benötigte
                    Felder; @id/URLs absolut + https + eigene Domain;
                    datePublished/dateModified ISO, modified >= published,
                    nicht in der Zukunft; image.url existiert im Build;
                    wordCount > 0
  S4  FAQPage     – mainEntity nicht leer, jede Frage mit Antwort >= 40 Zeichen
  S5  Open Graph  – og:title/-description/-image (+width/height/alt) und
                    twitter:card auf allen indexierbaren Seiten; og:image
                    existiert im Build und meldet die echten Pixelmaße
  S6  Hygiene     – Tag-/Kategorie-Archive, Paginierung und 404 tragen
                    noindex; Sitemap = Money-Pages (keine Archive, keine
                    Paginierung); alle Live-Artikel + 6 Ratgeber in der Sitemap
  S7  Lastmod     – jedes Sitemap-<lastmod> ist genau das Redaktionsdatum
                    (Frontmatter lastmod, sonst date) als YYYY-MM-DD –
                    nie ein Build-Zeitstempel, nie 0001-01-01, nie Zukunft
  S8  robots.txt  – Sitemap-Zeile da, /go/ für alle Roboter gesperrt,
                    Pinterestbot erlaubt; KI-Antwortmaschinen dokumentiert
  S9  Preload     – jedes vorgeladene Bild wird auf der Seite auch gerendert
                    (un-genutzter Preload = Lighthouse-Abzug + verlorene Bytes)
  S10 canonical   – genau ein canonical pro indexierbarer Seite, Ziel
                    existiert im Build

Selbstheilung: bewusst KEIN --fix. Die Funde betreffen Templates, Config und
Frontmatter – das entscheidet die Redaktionskette (DOKTOR), nicht eine Wache.

Nutzung:
    python3 scripts/schema_seo_gate.py                # prüft public/
    python3 scripts/schema_seo_gate.py --json         # Maschinen-Ausgabe
    python3 scripts/schema_seo_gate.py --selftest     # 8 Fälle (Sabotage-Schutz)

Exit: 0 = grün (Warnungen erlaubt) · 1 = harte Funde · 2 = Fehler/Selbsttest
"""
from __future__ import annotations

import glob
import html
import json
import os
import re
import sys
from datetime import date, datetime, timezone

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC = os.environ.get("SCHEMA_GATE_BASE", os.path.join(BLOG_DIR, "public"))
CONTENT = os.environ.get("SCHEMA_GATE_CONTENT", os.path.join(BLOG_DIR, "content"))
CONFIG = os.environ.get("SCHEMA_GATE_CONFIG", os.path.join(BLOG_DIR, "hugo.toml"))
REPORT = os.path.join(BLOG_DIR, "SCHEMA-SEO-REPORT.md")
HISTORY = os.path.join(BLOG_DIR, "data", "schema_seo_history.jsonl")

LD_RE = re.compile(
    r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>", re.S | re.I)
CANONICAL_RE = re.compile(r"<link[^>]+rel=[\"']?canonical[\"']?[^>]*>", re.I)
HREF_RE = re.compile(r"""href\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))""", re.I)
ROBOTS_RE = re.compile(
    r"""<meta[^>]+name=[\"']?robots[\"']?[^>]*content=[\"']([^\"']*)[\"']|"""
    r"""<meta[^>]+content=[\"']([^\"']*)[\"'][^>]*name=[\"']?robots\"?""", re.I)
PRELOAD_IMG_RE = re.compile(
    r"<link[^>]+rel=[\"']?preload[\"']?[^>]*as=[\"']?image[\"']?[^>]*>|"
    r"<link[^>]+as=[\"']?image[\"']?[^>]*rel=[\"']?preload[\"']?[^>]*>", re.I)
ATTR_RE = re.compile(r"""([a-zA-Z-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s">]+))""")
IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.I)
DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:?\d{2})?$")

# Seiten, die bewusst NICHT indexiert werden (dürfen/wachsen sonst Duplikate)
NON_INDEX_KINDS = ("/tags/", "/categories/")


# --------------------------------------------------------------------------
# Hilfsfunktionen
# --------------------------------------------------------------------------
def read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def site_base_url() -> str:
    """baseURL aus hugo.toml – ohne Netz, ohne Annahmen."""
    for line in read(CONFIG).splitlines():
        m = re.match(r"\s*baseURL\s*=\s*[\"']?([^\"'\s]+)", line)
        if m:
            return m.group(1).rstrip("/")
    return ""


def url_to_disk(url: str, base: str) -> str | None:
    """URL (absolut/relativ) -> Dateipfad im Build. None bei extern/unknown."""
    u = url.strip()
    if base and u.startswith(base):
        u = u[len(base):]
        # base kann mit oder ohne Slash übergeben werden (site_base_url() liefert
        # ohne, hugo.toml-BaseURL mit) – ohne Nachziehen wäre der Rest Pfad ohne
        # führende "/" und jede Existenzprüfung fiele aus.
        if u and not u.startswith("/"):
            u = "/" + u
    elif re.match(r"^https?://", u):
        return None
    u = u.split("?")[0].split("#")[0]
    u = html.unescape(u)
    if not u.startswith("/"):
        return None
    rel = u.lstrip("/")
    cand = os.path.join(PUBLIC, rel)
    if os.path.isfile(cand):
        return cand
    if rel == "":
        cand = os.path.join(PUBLIC, "index.html")
        return cand if os.path.isfile(cand) else None
    if os.path.isdir(cand):
        idx = os.path.join(cand, "index.html")
        return idx if os.path.isfile(idx) else None
    if os.path.isfile(cand + ".html"):
        return cand + ".html"
    return None


def parse_date(value: str) -> date | None:
    s = str(value).strip()
    if DATE_ONLY_RE.match(s):
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except ValueError:
            return None
    if ISO_RE.match(s):
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
        except ValueError:
            return None
    return None


def frontmatter(md_text: str) -> dict:
    """Winziger, absichtlich dumpler FM-Reader (nur top-level `key: value`).

    Kein PyYAML: die Wache muss auf jedem Runner laufen (auch ohne pip install)
    und sie darf nicht an Frontmatter-Syntaxdetails scheitern, die andere Wachen
    schon prüfen.
    """
    m = re.match(r"^---\n(.*?)\n---\s*\n", md_text, re.S)
    out: dict[str, str] = {}
    if not m:
        return out
    for line in m.group(1).splitlines():
        km = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if km:
            out[km.group(1)] = km.group(2).strip().strip("\"'")
    return out


def content_file_for(url_path: str) -> str | None:
    """URL-Pfad -> Quelldatei im content/ (posts, pillar, Single-Pages)."""
    p = url_path.strip("/")
    if not p:
        return None
    parts = p.split("/")
    if parts[0] in ("posts", "pillar") and len(parts) >= 2:
        cand = [os.path.join(CONTENT, parts[0], parts[1], "index.md"),
                os.path.join(CONTENT, parts[0], parts[1] + ".md")]
    else:
        cand = [os.path.join(CONTENT, p, "index.md"),
                os.path.join(CONTENT, p + ".md")]
    for c in cand:
        if os.path.isfile(c):
            return c
    return None


def editorial_lastmod(md_path: str) -> str | None:
    """Das Datum, das die Sitemap melden MUSS: lastmod (wenn >= date) sonst date."""
    fm = frontmatter(read(md_path))
    if fm.get("draft", "").lower() == "true":
        return None
    pub = parse_date(fm.get("date", ""))
    lm = parse_date(fm.get("lastmod", ""))
    if lm and pub and lm < pub:
        lm = pub
    chosen = lm or pub
    return chosen.isoformat() if chosen else None


def is_archive_url(rel: str) -> bool:
    return any(rel.startswith(x) for x in NON_INDEX_KINDS) or rel in (
        "/tags", "/categories")


def is_pager_url(rel: str) -> bool:
    return bool(re.search(r"/page/\d+/?$", rel))


def rel_of(page_path: str) -> str:
    rel = "/" + os.path.relpath(page_path, PUBLIC).replace(os.sep, "/")
    if rel.endswith("/index.html"):
        rel = rel[: -len("index.html")]
    elif rel == "/index.html":
        rel = "/"
    return rel


def is_hugo_page(page_path: str) -> bool:
    """Nur von Hugo gebaute Seiten prüfen.

    static/ liegt 1:1 im Build – Verifikationsdateien (google…html,
    pinterest-e238f.html), die OAuth-Landeseite und Fremd-HTML haben weder
    Open Graph noch canonical und dürfen der Wache nicht als Fehler
    angerechnet werden (sonst verliert die Wache ihre Aussagekraft – das
    Gegenteil von Premium).
    """
    rel = rel_of(page_path)
    return rel.endswith("/") or rel.endswith(".html") and "404" in rel


def iter_pages():
    for p in sorted(glob.glob(os.path.join(PUBLIC, "**", "*.html"), recursive=True)):
        yield p


def image_dims(path: str) -> tuple[int, int] | None:
    """Echte Pixelmaße – nativ (PIL falls vorhanden, sonst Header-Parsing)."""
    try:
        from PIL import Image  # type: ignore
        with Image.open(path) as im:
            return int(im.width), int(im.height)
    except Exception:
        pass
    try:
        with open(path, "rb") as f:
            head = f.read(64)
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            import struct
            w, h = struct.unpack(">II", head[16:24])
            return int(w), int(h)
    except Exception:
        return None
    return None


# --------------------------------------------------------------------------
# Prüfungen
# --------------------------------------------------------------------------
class Findings:
    def __init__(self) -> None:
        self.hard: list[tuple[str, str, str]] = []
        self.soft: list[tuple[str, str, str]] = []
        self.info: list[str] = []

    def add(self, rule: str, where: str, msg: str, soft: bool = False) -> None:
        (self.soft if soft else self.hard).append((rule, where, msg))

    @property
    def total(self) -> int:
        return len(self.hard) + len(self.soft)


def check_page(path: str, base: str, F: Findings, hugo: bool = True) -> dict:
    """S1–S5, S9, S10 pro gebauter Seite; liefert Metadaten für die Sitemap-Prüfung."""
    text = read(path)
    rel = rel_of(path)
    indexable = not re.search(r"noindex", "".join(
        m.group(1) or m.group(2) or "" for m in ROBOTS_RE.finditer(text)), re.I)
    out = {"rel": rel, "indexable": indexable, "has_article": False,
           "og_image": None, "og_dims": None}

    # ---------- S1/S2: JSON-LD ----------
    for raw in LD_RE.findall(text):
        try:
            data = json.loads(raw)
        except Exception as exc:
            F.add("S1", rel, f"JSON-LD nicht parsebar: {exc}")
            continue
        blocks = data if isinstance(data, list) else [data]
        for blk in blocks:
            if not isinstance(blk, dict):
                F.add("S1", rel, "JSON-LD-Block ist kein Objekt")
                continue
            _check_double_escape(rel, blk, F)
            t = blk.get("@type")
            if t == "Article":
                out["has_article"] = True
                _check_article(rel, blk, base, F)
            elif t == "FAQPage":
                _check_faq(rel, blk, F)

    # ---------- S5: Open Graph / Twitter ----------
    money = bool(re.match(r"^/(posts|pillar)/[^/]+/$", rel)) or rel == "/"
    if out["indexable"] and hugo:
        props = ("og:title", "og:description", "og:image") if money \
            else ("og:title", "og:description")
        for prop in props:
            if f'property="{prop}"' not in text and f"property={prop}" not in text:
                F.add("S5", rel, f"{prop} fehlt")
        card = 'name="twitter:card"' in text or "name=twitter:card" in text
        if not card:
            F.add("S5", rel, "twitter:card fehlt", soft=True)
        m = re.search(r"""og:image["']?\s+content=["']([^"']+)["']""", text)
        if m:
            out["og_image"] = m.group(1)
            img_disk = url_to_disk(m.group(1), base)
            if img_disk is None:
                F.add("S5", rel, f"og:image nicht auflösbar: {m.group(1)}")
            else:
                dims = image_dims(img_disk)
                wm = re.search(r"""og:image:width["']?\s+content=["'](\d+)["']""", text)
                hm = re.search(r"""og:image:height["']?\s+content=["'](\d+)["']""", text)
                if dims and wm and hm:
                    if (int(wm.group(1)), int(hm.group(1))) != dims:
                        F.add("S5", rel,
                              f"og:image:width/height meldet "
                              f"{wm.group(1)}×{hm.group(1)}, Bild ist {dims[0]}×{dims[1]}")
                out["og_dims"] = dims
                if dims and dims[0] < 200:
                    F.add("S5", rel, f"og:image zu klein ({dims[0]}px) – Pinterest/Discover erwarten mindestens 200px")
        if "/posts/" in rel or "/pillar/" in rel:
            if 'og:image:alt' not in text:
                F.add("S5", rel, "og:image:alt fehlt (Barrierefreiheit + Pin-Klickrate)",
                      soft=True)

    # ---------- S9: Preload ↔ Rendering ----------
    for tag in PRELOAD_IMG_RE.findall(text):
        attrs = {k.lower(): (v1 or v2 or v3 or "")
                 for k, v1, v2, v3 in ATTR_RE.findall(tag)}
        cand = attrs.get("imagesrcset") or attrs.get("href") or ""
        names = {os.path.basename(u.strip().split(" ")[0])
                 for u in cand.split(",") if u.strip()}
        if not names:
            continue
        body = text[text.lower().find("<body"):]
        rendered: set[str] = set()
        for img in IMG_TAG_RE.findall(body):
            for m in ATTR_RE.finditer(img):
                val = m.group(2) or m.group(3) or m.group(4) or ""
                for part in val.split(","):
                    base_name = os.path.basename(part.strip().split(" ")[0])
                    if base_name:
                        rendered.add(base_name)
        for want in sorted(names):
            # AVIF-Preload ↔ JPEG/WebP-Rendering: Name ohne Endung vergleichen
            stem = os.path.splitext(want)[0]
            if not any(os.path.splitext(r)[0] == stem for r in rendered):
                F.add("S9", rel,
                      f"Preload für {want} wird nicht gerendert "
                      f"(un-genutzter Preload: Bytes + Lighthouse-Abzug)")

    # ---------- S6: Hygiene der dünnen Seiten ----------
    if hugo and (is_archive_url(rel) or rel.endswith("404.html")) and indexable:
        F.add("S6", rel, "Archiv-/404-Seite ist indexierbar (muss noindex sein)")

    # ---------- S10: canonical ----------
    if indexable and hugo:
        cans = CANONICAL_RE.findall(text)
        if len(cans) != 1:
            F.add("S10", rel, f"{len(cans)} canonical-Tags (erwartet: genau 1)")
        else:
            m = HREF_RE.search(cans[0])
            target = (m.group(1) or m.group(2) or m.group(3) or "") if m else ""
            if target.startswith("http") and base and not target.startswith(base):
                F.add("S10", rel, f"canonical zeigt auf fremde Domain: {target}")
            elif target and url_to_disk(target, base) is None:
                F.add("S10", rel, f"canonical-Ziel existiert nicht im Build: {target}")

    # ---------- S11: PWA (Service Worker ohne Manifest = nie ein Install-Prompt)
    if rel == "/":
        mp = os.path.join(PUBLIC, "manifest.json")
        if not os.path.isfile(mp):
            F.add("S11", rel, "manifest.json fehlt im Build – die Site registriert "
                              'einen Service Worker, Chrome/Edge/iOS zeigen deshalb '
                              'niemals "Zum Startbildschirm hinzufügen" '
                              "(erzeugen: python3 scripts/generate_pwa_icons.py)")
        else:
            mtxt = read(mp)
            try:
                man = json.loads(mtxt)
            except json.JSONDecodeError as exc:
                F.add("S11", rel, f"manifest.json ist kein gültiges JSON: {exc}")
                man = {}
            for key in ("name", "short_name", "start_url", "scope", "display",
                        "theme_color", "icons"):
                if not man.get(key):
                    F.add("S11", rel, f"manifest.json: „{key}\u201c fehlt")
            if man.get("start_url") and base and \
                    not str(man["start_url"]).startswith(base):
                F.add("S11", rel, f"start_url „{man.get('start_url')}\u201c liegt "
                                  "außerhalb der Site – die Installation schlägt "
                                  "damit fehl")
            icons = man.get("icons") or []
            if len(icons) < 2:
                F.add("S11", rel, "manifest.json braucht mindestens zwei Icons "
                                  "(192 px + 512 px)")
            for ic in icons:
                src = str(ic.get("src", ""))
                f2 = url_to_disk(src, base)
                if f2 is None:
                    F.add("S11", rel, f"Manifest-Icon fehlt im Build: {src}")
                    continue
                d = image_dims(f2)
                if d and max(d) < 144:
                    F.add("S11", rel, f"Manifest-Icon {src} ist zu klein "
                                      f"({d[0]}×{d[1]}) – Android erwartet "
                                      "\u2265144 px")
                if not ic.get("purpose"):
                    F.add("S11", rel, f"Manifest-Icon {src} ohne \u201epurpose\u201c")
            if "maskable" not in mtxt:
                F.add("S11", rel, "kein maskable-Icon – bei Rundmasken schneidet "
                                   "Android Logo-Kanten ab", soft=True)
            if 'rel="manifest"' not in text and "rel=manifest" not in text:
                F.add("S11", rel, "Die Startseite verlinkt das Manifest nicht "
                                  '(<link rel="manifest"> fehlt im Kopf)')
            if re.search(r"(<link[^>]+rel=[\"']?manifest[\"']?[^>]*>){2,}", text):
                F.add("S11", rel, "Manifest wird mehrfach verlinkt")

    # ---------- Doppelte Kopf-Metas (gleiches Tag, anderer Wert) ----------
    for _name in ("theme-color", "robots", "description"):
        _hits = set(re.findall(
            r'<meta\s+name=[\"\']?' + _name + r'[\"\']?[^>]*content=([\"\'][^\"\']*[\"\'])',
            text, re.I))
        if len(_hits) > 1:
            F.add("S11", rel, f"Meta-Tag \u201e{_name}\u201c steht mehrfach mit "
                              f"unterschiedlichem Wert im Kopf ({len(_hits)}) – "
                              "welches gilt, rät Google. Ein Tag pro Sache.")
    return out


def _check_double_escape(rel: str, node, F: Findings, trail: str = "") -> None:
    """S2: class-Bug „doppelt gecastetes jsonify" – Werte mit literalen Quotes."""
    if isinstance(node, dict):
        for k, v in node.items():
            _check_double_escape(rel, v, F, f"{trail}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            _check_double_escape(rel, v, F, f"{trail}[{i}]")
    elif isinstance(node, str):
        s = node.strip()
        if (len(s) >= 2 and s[0] == '"' and s[-1] == '"') or '\\"' in node:
            F.add("S2", rel,
                  f"Doppelt escapeder JSON-LD-Wert in {trail or '@root'}: "
                  f"{node[:70]!r}")


def _check_article(rel: str, blk: dict, base: str, F: Findings) -> None:
    """S3: Article-Schema auf Wert-Ebene."""
    for field in ("@id", "headline", "datePublished", "dateModified",
                  "author", "publisher"):
        if field not in blk:
            F.add("S3", rel, f"Article.{field} fehlt")
    headline = blk.get("headline", "")
    if isinstance(headline, str) and len(headline) > 110:
        F.add("S3", rel, f"headline {len(headline)} Zeichen (> 110 → SERP-Abriss)")
    for url_field in ("@id",):
        val = blk.get(url_field)
        if isinstance(val, str) and val and base and not val.startswith(base):
            F.add("S3", rel, f"Article.{url_field} nicht auf eigener Domain: {val}")
    pub = parse_date(blk.get("datePublished", ""))
    mod = parse_date(blk.get("dateModified", ""))
    today = datetime.now(timezone.utc).date()
    if blk.get("datePublished") and pub is None:
        F.add("S3", rel, f"datePublished kein ISO-Datum: {blk.get('datePublished')!r}")
    if blk.get("dateModified") and mod is None:
        F.add("S3", rel, f"dateModified kein ISO-Datum: {blk.get('dateModified')!r}")
    if pub and mod and mod < pub:
        F.add("S3", rel, "dateModified liegt VOR datePublished")

    # Frische-Fabrik erkennen: dateModified MUSS das Redaktionsdatum aus dem
    # Frontmatter tragen (falls dort keines steht: das Datum des Artikels). Ein
    # pauschaler heutiger Wert ist erfunden – Google straft falsche Frische ab,
    # und die Site verspielt das einzige Signal, das eine Neubewertung auslöst.
    # Vorher prüfte nur die Sitemap-Regel S7 dagegen; der Wert auf der Seite
    # selbst war frei von Kontrolle.
    if mod is not None:
        _src = content_file_for(rel)
        _must = editorial_lastmod(_src) if _src else None
        if _must and mod.isoformat() != _must:
            F.add("S3", rel, f"dateModified {mod} ≠ Redaktionsdatum {_must} aus "
                             "dem Frontmatter – entweder Schema oder `lastmod` "
                             "pflegen; beides raten darf nicht sein")
    if mod and mod > today:
        F.add("S3", rel, f"dateModified in der Zukunft ({mod})")
    img = blk.get("image")
    img_url = None
    if isinstance(img, dict):
        img_url = img.get("url")
        w, h = img.get("width"), img.get("height")
        for name, val in (("width", w), ("height", h)):
            if val is not None and not (isinstance(val, int)
                                        or (isinstance(val, float) and val.is_integer())):
                F.add("S3", rel, f"image.{name} ist keine Ganzzahl: {val!r}")
    elif isinstance(img, str):
        img_url = img
    elif img is not None:
        F.add("S3", rel, "image hat unerwartete Struktur")
    if img_url:
        if base and not str(img_url).startswith(base):
            F.add("S3", rel, f"image.url nicht auf eigener Domain: {img_url}")
        elif url_to_disk(str(img_url), base) is None:
            F.add("S3", rel, f"image.url existiert nicht im Build: {img_url}")
    author = blk.get("author")
    if author is not None:
        items = author if isinstance(author, list) else [author]
        for a in items:
            if not isinstance(a, dict) or a.get("@type") not in ("Person", "Organization"):
                F.add("S3", rel, "author ohne @type Person/Organization")
    pub_obj = blk.get("publisher")
    if isinstance(pub_obj, dict):
        for field in ("name", "@id"):
            val = pub_obj.get(field)
            if val is None:
                F.add("S3", rel, f"publisher.{field} fehlt", soft=True)
    wc = blk.get("wordCount")
    if wc is not None and (not isinstance(wc, int) or wc <= 0):
        F.add("S3", rel, f"wordCount unschlüssig: {wc!r}")


def _check_faq(rel: str, blk: dict, F: Findings) -> None:
    """S4: FAQPage – Featured Snippets und AI-Antworten hängen daran."""
    ents = blk.get("mainEntity")
    if not isinstance(ents, list) or not ents:
        F.add("S4", rel, "FAQPage.mainEntity leer oder keine Liste")
        return
    for q in ents:
        if not isinstance(q, dict) or q.get("@type") != "Question":
            F.add("S4", rel, "FAQPage-Eintrag ist kein Question")
            continue
        if not (q.get("name") or "").strip():
            F.add("S4", rel, "Question.name leer")
        ans = q.get("acceptedAnswer") or {}
        text = (ans.get("text") or "").strip() if isinstance(ans, dict) else ""
        if len(text) < 40:
            F.add("S4", rel, f"Antwort zu „{(q.get('name') or '')[:40]}“ zu kurz "
                             f"({len(text)} Zeichen) – Google verwirft den Eintrag")


def check_sitemap(pages: list[dict], F: Findings) -> None:
    """S6/S7: Sitemap-Inhalt und Lastmod-Determinismus."""
    sm = os.path.join(PUBLIC, "sitemap.xml")
    if not os.path.isfile(sm):
        F.add("S6", "/", "sitemap.xml fehlt im Build")
        return
    xml = read(sm)
    urls = re.findall(r"<loc>\s*(.*?)\s*</loc>", xml, re.S)
    entries = re.findall(
        r"<loc>\s*(.*?)\s*</loc>\s*(?:<lastmod>\s*(.*?)\s*</lastmod>)?", xml, re.S)
    base = site_base_url()
    rels = set()
    for u in urls:
        rels.add(u[len(base):] if base and u.startswith(base) else u)
    # Archive und Paginierung dürfen nicht in der Sitemap stehen
    for r in sorted(rels):
        if is_archive_url(r) or is_pager_url(r):
            F.add("S6", r, "Archiv-/Paginierungs-URL in der Sitemap (Thin-Duplikat)")
    # Vollständigkeit: alle indexierbaren Artikel + Ratgeber
    for p in pages:
        if p["indexable"] and re.match(r"^/(posts|pillar)/[^/]+/$", p["rel"]):
            if p["rel"] not in rels:
                F.add("S6", p["rel"], "Live-Seite fehlt in der Sitemap")
    # Lastmod = rotes Redaktionsdatum
    for u, lm in entries:
        r = u[len(base):] if base and u.startswith(base) else u
        src = content_file_for(r)
        if src is None:
            continue
        must = editorial_lastmod(src)
        if must is None:
            continue
        if not lm:
            F.add("S7", r, "Sitemap-Eintrag ohne <lastmod>")
            continue
        if not DATE_ONLY_RE.match(lm):
            F.add("S7", r,
                  f"<lastmod> ist kein nacktes Datum (YYYY-MM-DD): {lm!r} "
                  f"– Verdacht auf Build-Zeitstempel statt Redaktionsdatum")
            continue
        if lm != must:
            F.add("S7", r, f"<lastmod> {lm} ≠ Redaktionsdatum {must}")
    if re.search(r"<lastmod>\s*0001-", xml):
        F.add("S7", "/", "Sitemap enthält 0001-01-01 (Datums-Fallback kaputt)")


def check_robots(F: Findings) -> None:
    """S8: robots.txt – Pinterest-, Gateway- und KI-Politik."""
    txt = read(os.path.join(PUBLIC, "robots.txt"))
    if not txt:
        F.add("S8", "/", "robots.txt fehlt im Build")
        return
    if "sitemap.xml" not in txt.lower():
        F.add("S8", "/", "robots.txt verweist nicht auf sitemap.xml")
    if not re.search(r"^Disallow:\s*/go/", txt, re.M):
        F.add("S8", "/", "/go/ (Affiliate-Gateways) ist nicht für alle Roboter gesperrt")
    pinterest_gruppen = [b for b in ("Pinterestbot", "Pinterest")
                         if re.search(rf"^User-agent:\s*{b}\s*$", txt, re.M)]
    if not pinterest_gruppen:
        F.add("S8", "/", "robots.txt nennt weder Pinterestbot noch Pinterest "
                         "– Rich-Pin-Crawl und Feed-Import gefährdet")
    groups: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in txt.splitlines():
        line = line.strip()
        m = re.match(r"^user-agent:\s*(.+)$", line, re.I)
        if m:
            current = groups.setdefault(m.group(1).strip(), [])
            continue
        if not line or line.startswith("#"):
            continue
        if current is not None:
            current.append(line)
    for group, rules in groups.items():
        blocked_home = any(re.match(r"^Disallow:\s*/\s*$", r) for r in rules)
        if blocked_home and group.lower() in (
                "oai-searchbot", "perplexitybot", "perplexity-user",
                "chatgpt-user", "duckassistbot", "claude-user",
                "meta-externalfetcher", "pinterestbot", "pinterest", "googlebot",
                "bingbot"):
            F.add("S8", "/", f"robots.txt sperrt {group} komplett – "
                             f"Sichtbarkeit in Suche/AI-Antworten/Pinterest kostet Reichweite")
    erlaubt = [g for g in groups if not any(re.match(r"^Disallow:\s*/\s*$", r)
                                            for r in groups[g])]
    ki = [g for g in erlaubt if g.lower() in (
        "oai-searchbot", "perplexitybot", "perplexity-user", "chatgpt-user",
        "duckassistbot", "claude-user", "meta-externalfetcher")]
    if ki:
        F.info.append("KI-Antwortmaschinen erlaubt: " + ", ".join(sorted(set(ki))))
    else:
        F.info.append("KI-Antwortmaschinen nicht explizit erlaubt "
                      "(nur Search-Bots) – Bewusste Entscheidung, kein Fehler")


# --------------------------------------------------------------------------
# Selbsttest – die Wache muss decisiv sein (Sabotage-Schutz, Konvention C6)
# --------------------------------------------------------------------------
def _selftest() -> list[str]:
    import shutil
    import tempfile
    errs: list[str] = []
    root = tempfile.mkdtemp(prefix="schema-gate-selftest-")
    try:
        pub = os.path.join(root, "public")
        content = os.path.join(root, "content")

        def page(rel: str, body: str) -> str:
            p = os.path.join(pub, rel.lstrip("/"))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(body)
            return p

        def art(good: bool, lm: str = "2026-09-01") -> str:
            ld = {
                "@context": "https://schema.org", "@type": "Article",
                "@id": "https://example.org/posts/a/",
                "headline": "Strom sparen im Herbst",
                "datePublished": "2026-08-10T10:00:00Z",
                "dateModified": f"{lm}T00:00:00Z",
                "author": {"@type": "Person", "name": "Frank Hartung"},
                "publisher": {"@type": "Organization", "name": "Ex",
                              "@id": "https://example.org/#organization"},
                "image": {"@type": "ImageObject",
                          "url": "https://example.org/i/cover.jpg",
                          "width": 1000, "height": 1500},
                "wordCount": 1200,
            }
            if not good:
                # exakt die alte Bugs-Form: Quotes im Wert
                ld["dateModified"] = f'"{lm}T00:00:00Z"'
                ld["@id"] = '"https://example.org/posts/a/"'
            head = ('<meta name=robots content="index, follow">'
                    '<meta property="og:title" content="T">'
                    '<meta property="og:description" content="D">'
                    '<meta property="og:image" content="https://example.org/i/cover.jpg">'
                    '<meta property="og:image:width" content="1000">'
                    '<meta property="og:image:height" content="1500">'
                    '<meta property="og:image:alt" content="T">'
                    '<meta name="twitter:card" content="summary_large_image">'
                    '<link rel="canonical" href="https://example.org/posts/a/">')
            return (f"<html><head>{head}"
                    f"<script type=application/ld+json>{json.dumps(ld)}</script>"
                    f"<script type=application/ld+json>{json.dumps({'@type':'FAQPage','mainEntity':[{'@type':'Question','name':'Sparen?','acceptedAnswer':{'@type':'Answer','text':'Ja – der Ratgeber nennt konkrete Euro-Beträge, Fristen und die drei häufigsten Fehler beim Wechsel.'}}]})}</script>"
                    f"</head><body><img src=/i/cover.jpg alt=x></body></html>")

        # Miniatur-Bilddatei, damit die og:image-Auflösung greift
        img_dir = os.path.join(pub, "i")
        os.makedirs(img_dir, exist_ok=True)
        with open(os.path.join(img_dir, "cover.jpg"), "wb") as f:
            f.write(b"\xff\xd8\xff\xe0" + b"0" * 40)

        # Mit echtem JPEG (Pillow) kann die Wache ihre Maß-Prüfung wirklich
        # durchspielen; ohne Pillow bleibt sie bei „nicht auswertbar\u201c hängen.
        real_image = False
        try:
            from PIL import Image as _Img
            _Img.new("RGB", (1000, 1500), (14, 90, 67)).save(
                os.path.join(img_dir, "cover.jpg"), quality=80)
            real_image = image_dims(os.path.join(img_dir, "cover.jpg")) == (1000, 1500)
        except Exception:
            real_image = False

        # --- Fall 1: grüner Stand ---
        page("/posts/a/index.html", art(True))
        page("/ueber/index.html", '<html><head><meta name=robots content="index, follow">'
                                  '<meta property="og:title" content="T">'
                                  '<meta property="og:description" content="D">'
                                  '<meta property="og:image" content="https://example.org/i/cover.jpg">'
                                  '<meta property="og:image:width" content="1000">'
                                  '<meta property="og:image:height" content="1500">'
                                  '<meta property="og:image:alt" content="T">'
                                  '<link rel="canonical" href="https://example.org/ueber/">'
                                  "</head><body></body></html>")
        page("/tags/eines/index.html", '<html><head><meta name=robots content="noindex, follow">'
                                       '<link rel=canonical href=https://example.org/tags/eines/>'
                                       "</head><body></body></html>")
        with open(os.path.join(pub, "sitemap.xml"), "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0"?><urlset><url><loc>https://example.org/posts/a/</loc>'
                    "<lastmod>2026-09-01</lastmod></url><url><loc>https://example.org/ueber/</loc>"
                    "<lastmod>2026-08-20</lastmod></url></urlset>")
        with open(os.path.join(pub, "robots.txt"), "w", encoding="utf-8") as f:
            f.write("User-agent: *\nAllow: /\nDisallow: /go/\n\n"
                    "User-agent: Pinterestbot\nAllow: /\n\n"
                    "User-agent: OAI-SearchBot\nAllow: /\n\n"
                    "Sitemap: https://example.org/sitemap.xml\n")
        os.makedirs(os.path.join(content, "posts", "a"), exist_ok=True)
        with open(os.path.join(content, "posts", "a", "index.md"), "w",
                  encoding="utf-8") as f:
            f.write("---\ntitle: \"Strom sparen im Herbst\"\ndate: 2026-08-10T10:00:00Z\n"
                    "lastmod: 2026-09-01\ndraft: false\n---\nText\n")
        os.makedirs(os.path.join(content, "ueber"), exist_ok=True)
        with open(os.path.join(content, "ueber", "index.md"), "w", encoding="utf-8") as f:
            f.write("---\ntitle: \"Über\"\ndate: 2026-08-20\nlastmod: 2026-08-20\n---\nx\n")
        cfg = os.path.join(root, "hugo.toml")
        with open(cfg, "w", encoding="utf-8") as f:
            f.write('baseURL = "https://example.org/"\n')

        def run() -> tuple[int, list[str], list[str]]:
            global PUBLIC, CONTENT, CONFIG
            PUBLIC, CONTENT, CONFIG = pub, content, cfg
            F = Findings()
            pages = [check_page(p, site_base_url(), F) for p in iter_pages()]
            check_sitemap(pages, F)
            check_robots(F)
            return (1 if F.hard else 0), [f"{r} {m}" for r, _, m in F.hard], \
                   [f"{r} {m}" for r, _, m in F.soft]

        code, hard, soft = run()
        if code != 0:
            errs.append(f"Fall 1 (grüner Stand) meldet harte Funde: {hard}")

        # --- Fall 2: Doppelt escapedes Schema (der Original-Bug) ---
        p = os.path.join(pub, "posts", "a", "index.html")
        txt = read(p).replace('"dateModified": "2026-09-01T00:00:00Z"',
                              '"dateModified": "\\"2026-09-01T00:00:00Z\\""')
        with open(p, "w", encoding="utf-8") as f:
            f.write(txt)
        code, hard, _ = run()
        if code != 1 or not any(h.startswith("S2") or h.startswith("S3") for h in hard):
            errs.append(f"Fall 2 (Doppel-Escape) wird nicht erkannt: {hard}")
        with open(p, "w", encoding="utf-8") as f:
            f.write(art(True))

        # --- Fall 3: kaputtes JSON ---
        with open(p, "w", encoding="utf-8") as f:
            f.write(read(p).replace('"wordCount": 1200', '"wordCount": 1200,,}'))
        code, hard, _ = run()
        if code != 1 or not any(h.startswith("S1") for h in hard):
            errs.append(f"Fall 3 (ungültiges JSON) wird nicht erkannt: {hard}")
        with open(p, "w", encoding="utf-8") as f:
            f.write(art(True))

        # --- Fall 4: Build-Zeitstempel als lastmod ---
        with open(os.path.join(pub, "sitemap.xml"), "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0"?><urlset><url><loc>https://example.org/posts/a/</loc>'
                    "<lastmod>2026-09-11T22:06:29+00:00</lastmod></url>"
                    "<url><loc>https://example.org/ueber/</loc><lastmod>2026-08-20</lastmod></url></urlset>")
        code, hard, _ = run()
        if code != 1 or not any(h.startswith("S7") for h in hard):
            errs.append(f"Fall 4 (Build-Lastmod) wird nicht erkannt: {hard}")
        with open(os.path.join(pub, "sitemap.xml"), "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0"?><urlset><url><loc>https://example.org/posts/a/</loc>'
                    "<lastmod>2026-09-01</lastmod></url><url><loc>https://example.org/ueber/</loc>"
                    "<lastmod>2026-08-20</lastmod></url></urlset>")

        # --- Fall 5: indexierbares Tag-Archiv + Sitemap-Fund ---
        tp = os.path.join(pub, "tags", "eines", "index.html")
        with open(tp, "w", encoding="utf-8") as f:
            f.write('<html><head><meta name=robots content="index, follow">'
                    '<link rel=canonical href=https://example.org/tags/eines/>'
                    "</head><body></body></html>")
        code, hard, _ = run()
        if code != 1 or not any(h.startswith("S6") for h in hard):
            errs.append(f"Fall 5 (indexierbares Archiv) wird nicht erkannt: {hard}")
        with open(tp, "w", encoding="utf-8") as f:
            f.write('<html><head><meta name=robots content="noindex, follow">'
                    '<link rel=canonical href=https://example.org/tags/eines/>'
                    "</head><body></body></html>")
        code, hard, _ = run()
        if code != 0:
            errs.append(f"Fall 5b (Rücksetzung) meldet weiter: {hard}")

        # --- Fall 6: robots.txt ohne /go/-Sperre + Pinterestbot gesperrt ---
        rb = os.path.join(pub, "robots.txt")
        with open(rb, "w", encoding="utf-8") as f:
            f.write("User-agent: *\nAllow: /\n\nUser-agent: Pinterestbot\nDisallow: /\n")
        code, hard, _ = run()
        if code != 1 or not any(h.startswith("S8") for h in hard):
            errs.append(f"Fall 6 (robots.txt-Gefahr) wird nicht erkannt: {hard}")
        with open(rb, "w", encoding="utf-8") as f:
            f.write("User-agent: *\nAllow: /\nDisallow: /go/\n\nUser-agent: Pinterestbot\n"
                    "Allow: /\n\nSitemap: https://example.org/sitemap.xml\n")

        # --- Fall 7: Preload ohne gerendertes Bild ---
        ghost = read(p).replace("<body>",
                                '<link rel=preload as=image imagesrcset="/i/ghost.avif 720w">'
                                "<body>")
        with open(p, "w", encoding="utf-8") as f:
            f.write(ghost)
        code, hard, _ = run()
        if code != 1 or not any(h.startswith("S9") for h in hard):
            errs.append(f"Fall 7 (Preload ohne Bild) wird nicht erkannt: {hard}")
        with open(p, "w", encoding="utf-8") as f:
            f.write(art(True))

        # --- Fall 8: og:image-Maße widersprechen der Datei ---
        wrong_dims = read(p).replace('og:image:width" content="1000"',
                                     'og:image:width" content="1200"')
        with open(p, "w", encoding="utf-8") as f:
            f.write(wrong_dims)
        code, hard, _ = run()
        if real_image:
            if not any(h.startswith("S5") and "1200" in h for h in hard):
                errs.append(f"Fall 8: falsche og:image-Maße werden nicht gesehen: {hard}")
        elif code == 2:
            errs.append("Fall 8: Wache crasht bei unförmigem Bild")
        with open(p, "w", encoding="utf-8") as f:
            f.write(art(True))

        # --- Fall 9: erfundene Frische (dateModified ≠ Redaktionsdatum) ---
        today = date.today().isoformat()
        fake = json.loads(re.search(LD_RE, read(p)).group(1))
        fake["dateModified"] = f"{today}T00:00:00Z"
        head_keep = read(p).split("<script")[0]
        faq_keep = re.search(LD_RE, read(p)).group(0)
        with open(p, "w", encoding="utf-8") as f:
            f.write(head_keep + f"<script type=application/ld+json>"
                    f"{json.dumps(fake)}</script>" + faq_keep +
                    "</head><body><img src=/i/cover.jpg alt=x></body></html>")
        code, hard, _ = run()
        if not any(h.startswith("S3") and "Redaktionsdatum" in h for h in hard):
            errs.append(f"Fall 9: erfundene dateModified-Frische wird nicht gesehen: {hard}")
        with open(p, "w", encoding="utf-8") as f:
            f.write(art(True))

        # --- Fall 10: Service Worker ohne Manifest (PWA, S11) ---
        home = os.path.join(pub, "index.html")
        home_ok = ('<html><head><meta name=robots content="index, follow">'
                   '<meta property="og:title" content="T">'
                   '<meta property="og:description" content="D">'
                   '<meta property="og:image" content="https://example.org/i/cover.jpg">'
                   '<meta property="og:image:width" content="1000">'
                   '<meta property="og:image:height" content="1500">'
                   '<meta name="twitter:card" content="summary_large_image">'
                   '<link rel="canonical" href="https://example.org/">'
                   "</head><body></body></html>")
        with open(home, "w", encoding="utf-8") as f:
            f.write(home_ok)
        code, hard, _ = run()
        if not any(h.startswith("S11") and "manifest.json fehlt" in h for h in hard):
            errs.append(f"Fall 10: fehlendes PWA-Manifest wird nicht gesehen: {hard}")
        with open(os.path.join(pub, "manifest.json"), "w", encoding="utf-8") as f:
            f.write(json.dumps({"name": "Ex", "short_name": "Ex",
                                "start_url": "https://example.org/",
                                "scope": "https://example.org/",
                                "display": "standalone", "theme_color": "#0E5A43",
                                "icons": [{"src": "/i/cover.jpg",
                                          "sizes": "1000x1500",
                                          "type": "image/jpeg",
                                          "purpose": "any"},
                                         {"src": "/i/cover.jpg",
                                          "sizes": "1000x1500",
                                          "type": "image/jpeg",
                                          "purpose": "maskable"}]}))
        code, hard, _ = run()
        if not any(h.startswith("S11") and "verlinkt das Manifest nicht" in h
                   for h in hard):
            errs.append(f"Fall 10b: Manifest ohne Link im Kopf wird nicht gesehen: {hard}")
        with open(home, "w", encoding="utf-8") as f:
            f.write(home_ok.replace("</head>",
                    '<link rel="manifest" href="/manifest.json"></head>'))
        code, hard, _ = run()
        if any(h.startswith("S11") for h in hard):
            errs.append(f"Fall 10c: Manifest verlinkt, meldet aber weiter: {hard}")
        os.remove(home)
        os.remove(os.path.join(pub, "manifest.json"))
        code, hard, _ = run()
        if code != 0:
            errs.append(f"Endzustand nach Rücksetzung nicht grün: {hard}")
    finally:
        shutil.rmtree(root, ignore_errors=True)
    return errs


# --------------------------------------------------------------------------
# Hauptlauf
# --------------------------------------------------------------------------
def main() -> int:
    if "--selftest" in sys.argv:
        errs = _selftest()
        if errs:
            print("🛑 SCHEMA-SEO-GATE Selbsttest FEHLGESCHLAGEN:")
            for e in errs:
                print("  -", e)
            return 2
        print("✅ Schema-/SEO-Gate-Selbsttest: alle Fälle grün.")
        return 0

    if not os.path.isdir(PUBLIC):
        print(f"❌ Build-Verzeichnis fehlt: {PUBLIC} (zuerst `hugo --minify` bauen)")
        return 2

    base = site_base_url()
    F = Findings()
    pages = []
    for path in iter_pages():
        pages.append(check_page(path, base, F, hugo=is_hugo_page(path)))
    check_sitemap(pages, F)
    check_robots(F)

    n_artikel = sum(1 for p in pages if p["indexable"]
                    and re.match(r"^/(posts|pillar)/[^/]+/$", p["rel"]))
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pages": len(pages), "money_pages": n_artikel,
        "hard": [{"rule": r, "where": w, "msg": m} for r, w, m in F.hard],
        "soft": [{"rule": r, "where": w, "msg": m} for r, w, m in F.soft],
        "info": F.info,
    }
    if "--json" in sys.argv:
        print(json.dumps(payload, ensure_ascii=False, indent=1))
        return 1 if F.hard else 0

    print(f"SCHEMA-/SEO-GATE: {len(pages)} gebaute Seiten, {n_artikel} Money-Pages "
          f"geprüft · harte Funde: {len(F.hard)} · Hinweise: {len(F.soft)}")
    for rule, where, msg in F.hard:
        print(f"  ❌ [{rule}] {where}: {msg}")
    for rule, where, msg in F.soft:
        print(f"  ⚠ [{rule}] {where}: {msg}")
    for line in F.info:
        print(f"  ℹ {line}")

    # Report + Historischer Nachweis (Report ist .gitignore-ignoriert)
    lines = [
        "# 🔐 SCHEMA-/SEO-GATE (Premium-Wache schema_seo_gate.py)", "",
        f"**Stand:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC · "
        f"{len(pages)} Seiten · {n_artikel} Money-Pages", "",
        f"**Harte Funde:** {len(F.hard)} · **Hinweise:** {len(F.soft)}", "",
    ]
    if F.hard:
        lines += ["## ❌ Harte Funde (blockieren)", ""]
        lines += [f"- `[{r}]` {w}: {m}" for r, w, m in F.hard]
        lines += [""]
    if F.soft:
        lines += ["## ⚠ Hinweise (reportieren, nicht blockieren)", ""]
        lines += [f"- `[{r}]` {w}: {m}" for r, w, m in F.soft]
        lines += [""]
    if F.info:
        lines += ["## ℹ Zustand", ""] + [f"- {x}" for x in F.info] + [""]
    lines += ["",
              "_Regeln S1–S10: JSON-LD-Parsing, Doppel-Escape, Article-Werte, "
              "FAQPage, Open Graph, Indexierungs-Hygiene, Lastmod-Determinismus, "
              "robots.txt, Preload↔Rendering, canonical. "
              "Diese Wache heilt nicht – sie entscheidet._"]
    try:
        with open(REPORT, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except OSError:
        pass
    try:
        os.makedirs(os.path.dirname(HISTORY), exist_ok=True)
        with open(HISTORY, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": payload["ts"], "pages": len(pages),
                "money": n_artikel, "hard": len(F.hard), "soft": len(F.soft),
                "rules": sorted({r for r, _, _ in F.hard}),
            }, ensure_ascii=False) + "\n")
    except OSError:
        pass

    if F.hard:
        print(f"→ {len(F.hard)} harte Funde – Details im Log und in SCHEMA-SEO-REPORT.md")
        return 1
    print("✅ Schema, Social-Signale und Indexierungs-Hygiene auf Premium-Level.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
