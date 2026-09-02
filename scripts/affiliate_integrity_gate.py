#!/usr/bin/env python3
# ============================================================
#  AFFILIATE-INTEGRITY-GATE – strukturelle CTA-Prüfung + RENDER-BEWEIS
#  (Premium-Ausbau 02.09.2026 · Version 2)
#
#  Auftrag (Frank, 14.08.2026, unverändert gültig):
#    "Die Affiliate-Links wurden beschädigt. Bitte dauerhaft beheben
#     (Automatik und Selbstheilung), indem die Veröffentlichung nur
#     vorgenommen wird, wenn alle Links funktionieren und tatsächlich im
#     Blog erscheinen. Ansonsten soll sofort eine Reparatur erfolgen."
#
#  ------------------------------------------------------------
#  WARUM VERSION 2 (Vorfall 01./02.09.2026 – "stille Blindheit"):
#
#  Am 01.09.2026 wurde der Render-Hook layouts/_default/_markup/
#  render-link.html erweitert (Awin-SubID `?subid=<artikel>`, Umami-
#  Kontext-Attribute). Seitdem zählte der Render-Beweis AI4 in JEDEM
#  Artikel 0 Affiliate-Links – obwohl alle Links korrekt im HTML standen.
#  Ursache: AI4 war als EIN starres Regex auf die exakte Attribut-Reihen-
#  folge der damaligen Ausgabe genagelt:
#      r"<a href=/go/[\w-]+/[^>]*affiliate_click[^>]*>"
#  Der Hook liefert aber (a) ein QUOTIERTES href und (b) zwischen href und
#  data-umami-event vier weitere Attribute (`?subid=` bricht zusätzlich das
#  `[\w-]+/`-Muster). Folge: 24/24 Artikel "Render-Probleme", die tägliche
#  Wache rot (Issues #76/#78/#95/#99/#137/#146), BESTAND-REPORT rot, und –
#  am gefährlichsten – publish_gate.py hätte jeden Re-Queue-Kandidaten wegen
#  eines Phantom-Fehlers zurückgestuft.
#
#  LEHRE (diese Version setzt sie um): Ein Beweis, der die HTML-Ausgabe
#  nur "anblickt", bricht bei jeder Layout-Änderung. Deshalb:
#    1. ATTRIBUT-TOLERANTE AUSWERTUNG: <a>-Tags werden geparst (href,
#       rel, data-umami-event, target) statt per Positions-Regex gezählt.
#       Minifiziert oder nicht, quotes oder nicht, ?subid= oder nicht –
#       alles gleich gültig.
#    2. EINGEFRORENER SELBSTTEST (--selftest): Fixtures aus REALER
#       Hook-Ausgabe (01.09.-Format, 14.08.-Format, unminifiziert) plus
#       die Schadensfälle von 14.08. Dazu ein ABGLEICH GEGEN DAS LIVE-
#       TEMPLATE: enthält render-link.html den Gateway-Link noch mit
#       `data-umami-event="affiliate_click"`? Fehlt der Fingerabdruck,
#       meldet das Gate "Detektor veraltet" (Exit 2) statt grüner Nullen.
#    3. FAIL-CLOSED: Kann der Beweis nicht geführt werden (kein public/,
#       Hugo-Build失败, Selbsttest rot), ist das ein WERKZEUGFEHLER
#       (Exit 2) – publish_gate.py verwirft dann Kandidaten, statt sie
#       ungeprüft durchzuwinken. Unbewiesen = unveröffentlicht.
#    4. SCHADENSBILDER WERDEN ERKANNT, NICHT GERATEN: 0 gerenderte Links
#       bei N gültigen Markdown-CTAs ist ein Inhaltsschaden; 0 gerenderte
#       Links bei ALLEN Artikeln gleichzeitig ist ein Detektorschaden.
#       Beides wird unterschiedlich behandelt (Inhalt → heilen, Detektor
#       → Exit 2 + Issue), damit sich die Wache nie wieder still selbst
#       blind schaltet.
#
#  ------------------------------------------------------------
#  PRÜFUNGEN
#    AI1 STRUKTUR   Jede CTA-Marker-Zeile enthält einen VOLLSTÄNDIGEN
#                   Markdown-Link [**Text**](/go/<key>/) – kein Dangling
#                   (Vorfall 14.08.: `[**Text**` ohne `](url)`).
#    AI2 REGISTRY   Jedes /go/<key>/ im Artikel ist in
#                   scripts/check24_links.yaml registriert; KEINE rohen
#                   Partner-URLs (a.check24.net / partner-versicherung.de)
#                   im Content – Tracking, rel=sponsored und Partner-
#                   korrektheit laufen ausschließlich über das Gateway.
#    AI3 PLAUSIBILITÄT  Wörter direkt an der CTA gegen hunspell –
#                   Verstümmelungen wie "DStiebendenTarife" fallen auf.
#    AI4 RENDER-BEWEIS  Nach `hugo --minify` muss JEDER Affiliate-Link des
#                   Markdowns als echter <a href="/go/<key>/…"> im gebauten
#                   HTML stehen – inkl. Schlüssel-Vergleich (nicht nur
#                   Anzahl), inkl. rel="sponsored" (Werbekennzeichnung/
#                   Google-Richtlinie) und Umami-Klick-Attribution.
#    AI5 GATEWAY-BEWEIS  Jede referenzierte /go/<key>/-Seite existiert
#                   (public/ bzw. static/go/) und leitet per Meta-Refresh
#                   oder JS exakt auf die registrierte Ziel-URL weiter
#                   (noindex Pflicht) – sonst Klick-Verlust.
#
#  SELBSTHEILUNG (nie Text-Patch, nie Löschen):
#    • defekte CTA-Zeile        → KOMPLETT neu aus affiliate_marketer.py-
#                                 Vorlage (build_top_cta/mid_cta/end_cta),
#                                 Route thematisch korrekt via route_for()
#    • nicht registrierter Key  → auf die Artikel-Route umgeschrieben
#    • rohe Partner-URL         → auf das /go/-Gateway umgeschrieben
#    Nach Heilung: automatischer Hugo-Rebuild + erneuter Beweis.
#
#  EINBINDUNG
#    • .github/workflows/affiliate-integrity-daily.yml (täglich 06:00 MESZ)
#    • deploy.yml → publish_gate.py (neue/Re-Queue-Kandidaten, hart)
#    • seo-weekly.yml → bestand_gate.py (Bestand, nicht-destruktiv)
#
#  EXIT-CODES
#    0  grün – alle Links intakt, registriert, gerendert, Gateway belegt
#    1  Inhaltsschaden – nach Heilungsversuch bleibt etwas offen
#    2  WERKZEUGFEHLER – Beweis nicht möglich (Build/Selbsttest/Detektor).
#       Fail-closed: publish_gate.py veröffentlicht dann NICHTS.
#
#  Aufruf
#    python3 scripts/affiliate_integrity_gate.py               # prüfen + heilen
#    python3 scripts/affiliate_integrity_gate.py --dry-run     # nur prüfen
#    python3 scripts/affiliate_integrity_gate.py --json        # Maschinenformat
#    python3 scripts/affiliate_integrity_gate.py --selftest    # Detektor-Test
#    python3 scripts/affiliate_integrity_gate.py --no-build    # public/ nicht anfassen
#    python3 scripts/affiliate_integrity_gate.py --slug <slug> # Einzelartikel
# ============================================================

from __future__ import annotations

import html as html_mod
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
POSTS_DIR = ROOT / "content" / "posts"
PUBLIC = ROOT / "public"
STATIC_GO = ROOT / "static" / "go"
REPORT = ROOT / "AFFILIATE-INTEGRITY-REPORT.md"
STATE = ROOT / ".affiliate_integrity_state.json"
RENDER_HOOK = ROOT / "layouts" / "_default" / "_markup" / "render-link.html"

sys.path.insert(0, str(SCRIPTS))

EXIT_OK = 0
EXIT_CONTENT = 1
EXIT_TOOL = 2

# (Marker-Text, CTA-Typ) – Reihenfolge = erwartete Position im Artikel.
CTA_MARKERS = [
    ("Schnell-Tipp von FranksFinanzcheck", "top"),
    ("Spar-Tipp zwischendurch", "mid"),
    ("Jetzt vergleichen und sparen", "end"),
    ("Sparend zuerst vergleichen", "end"),
]
RAW_PARTNER_RE = re.compile(
    r"https?://a\.(?:check24\.net|partner-versicherung\.de)/[^\s)\"'<>]+"
)
GO_LINK_RE = re.compile(r"/go/([\w-]+)/")
MD_LINK_RE = re.compile(r"\[\*\*([^\]]*)\*\*\]\(([^)\s]+)\)")
# Fingerabdruck des Gateway-Links im Render-Hook (Drift-Wächter im Selftest)
HOOK_FINGERPRINTS = ("/go/", "affiliate_click")

# ------------------------------------------------------------------ #
#  CLI
# ------------------------------------------------------------------ #
ARGS = sys.argv[1:]
DRY_RUN = "--dry-run" in ARGS
AS_JSON = "--json" in ARGS
SELFTEST = "--selftest" in ARGS
NO_BUILD = "--no-build" in ARGS
ONLY_SLUGS: list[str] = []
if "--slug" in ARGS:
    ONLY_SLUGS = [ARGS[i + 1] for i, a in enumerate(ARGS)
                  if a == "--slug" and i + 1 < len(ARGS)]


def _say(msg: str) -> None:
    """Diagnose nach stderr – stdout bleibt im --json-Modus reines JSON."""
    print(msg, file=sys.stderr)


# ------------------------------------------------------------------ #
#  Registry / Artikel
# ------------------------------------------------------------------ #
def load_registry(root: Path | None = None) -> dict:
    """Zentrale Partner-Registry (scripts/check24_links.yaml)."""
    import affiliate_marketer as am
    if root is None or root == ROOT:
        return am.load_registry()
    reg = {}
    reg_file = root / "scripts" / "check24_links.yaml"
    for line in reg_file.read_text(encoding="utf-8").splitlines():
        ls = line.strip()
        if ls and not ls.startswith("#") and ": " in ls and '"' in ls:
            reg[ls.split(":")[0].strip()] = ls.split('"')[1]
    return reg


def article_route(article: dict, reg: dict) -> str:
    """Thematisch korrekte Gateway-Route des Artikels (nie hartkodiert)."""
    import affiliate_marketer as am
    try:
        route = am.route_for(article.get("body", ""), article.get("pillar", ""))
    except Exception:  # noqa: BLE001
        route = am.PILLAR_ROUTE.get(article.get("pillar", ""), "allgemein")
    return route if route in reg else "allgemein"


def load_live_articles(posts_dir: Path | None = None) -> list[dict]:
    posts_dir = posts_dir or POSTS_DIR
    arts = []
    if not posts_dir.is_dir():
        return arts
    for slug_dir in sorted(posts_dir.iterdir()):
        index_md = slug_dir / "index.md"
        if not index_md.is_file():
            continue
        text = index_md.read_text(encoding="utf-8")
        if not text.startswith("---") or text.count("---") < 2:
            continue
        parts = text.split("---", 2)
        fm, body = parts[1], parts[2]
        if re.search(r"^draft:\s*true\s*$", fm, re.MULTILINE):
            continue
        pillar_m = re.search(r'^pillar:\s*"?([\w-]+)', fm, re.MULTILINE)
        arts.append({
            "slug": slug_dir.name,
            "path": index_md,
            "content": text,
            "fm": fm,
            "body": body,
            "pillar": pillar_m.group(1) if pillar_m else "",
        })
    if ONLY_SLUGS:
        arts = [a for a in arts if a["slug"] in ONLY_SLUGS]
    return arts


# ------------------------------------------------------------------ #
#  Markdown-Seite (AI1–AI3)
# ------------------------------------------------------------------ #
def find_cta_lines(body: str) -> list[tuple[str, str, str, int, int]]:
    """(marker, kind, zeile, start, ende) für jede CTA-Marker-Zeile.
    Mehrere Marker in derselben Zeile werden zu EINEM Eintrag zusammen-
    gefasst (sonst Doppelzählung im Render-Beweis)."""
    spans: dict[tuple[int, int], list[str]] = {}
    for marker, kind in CTA_MARKERS:
        for m in re.finditer(re.escape(marker), body):
            line_start = body.rfind("\n", 0, m.start()) + 1
            line_end = body.find("\n", m.start())
            if line_end == -1:
                line_end = len(body)
            entry = spans.setdefault((line_start, line_end), [])
            if kind not in entry:
                entry.append(kind)
    found = []
    for (line_start, line_end), kinds in sorted(spans.items()):
        line = body[line_start:line_end]
        marker = next((mk for mk, _kd in CTA_MARKERS if mk in line), CTA_MARKERS[0][0])
        found.append((marker, kinds[0], line, line_start, line_end))
    return found


def markdown_cta_links(body: str) -> list[dict]:
    """Alle Affiliate-Verweise im Markdown – Markdown-CTAs UND rohe
    <a href="/go/…">-Tags (Fallback-Pfad des Render-Hooks bei toten
    internen Zielen)."""
    out = []
    for marker, kind, line, start, end in find_cta_lines(body):
        for m in MD_LINK_RE.finditer(line):
            out.append({"kind": kind, "marker": marker, "url": m.group(2),
                        "anchor": m.group(1), "line_start": start,
                        "line_end": end, "form": "markdown"})
    for m in re.finditer(r'<a\s[^>]*href=["\']?(/go/[^"\'\s>]+)["\']?[^>]*>', body):
        out.append({"kind": "inline", "marker": "", "url": m.group(1),
                    "anchor": "", "line_start": body.rfind("\n", 0, m.start()) + 1,
                    "line_end": m.end(), "form": "html"})
    return out


def check_cta_line(marker: str, line: str, reg_keys: set) -> list[str]:
    """AI1 + AI2 + AI3 für eine einzelne CTA-Zeile."""
    problems: list[str] = []
    link_m = MD_LINK_RE.search(line)
    if not link_m:
        raw = RAW_PARTNER_RE.search(line)
        if raw:
            problems.append(
                f"Rohe Partner-URL statt /go/-Redirect in CTA-Zeile ('{marker}'): {raw.group(0)}")
        elif GO_LINK_RE.search(line):
            problems.append(
                f"Unvollständiger Markdown-Link in CTA-Zeile ('{marker}') – "
                "Ziel vorhanden, aber Syntax defekt (Dangling Link)")
        else:
            problems.append(f"Kein vollständiger Markdown-Link in CTA-Zeile ('{marker}')")
        return problems  # Folgeprüfungen ohne gültigen Link sinnlos

    url = link_m.group(2)
    if url.startswith("http"):
        problems.append(
            f"Rohe externe URL statt /go/-Redirect in CTA-Zeile ('{marker}'): {url}")
    else:
        go_m = GO_LINK_RE.search(url)
        if not go_m:
            problems.append(f"Ungültiges Linkziel in CTA-Zeile ('{marker}'): {url}")
        elif go_m.group(1) not in reg_keys:
            problems.append(
                f"/go/{go_m.group(1)}/ ist nicht in check24_links.yaml registriert ('{marker}')")

    # AI3: Text-Plausibilität (Wörter direkt nach dem Marker, vor dem Link)
    after_marker = line.split(marker, 1)[1] if marker in line else line
    before_link = after_marker.split("[", 1)[0]
    words = re.findall(r"[A-Za-zÄÖÜäöüß]+", before_link)[:6]
    if words and hunspell_unknown_ratio(words) > 0.5:
        problems.append(
            f"Verdächtig viele unbekannte Wörter direkt an der CTA ('{marker}'): "
            f"{' '.join(words)}")
    return problems


def hunspell_unknown_ratio(words: list[str]) -> float:
    """Anteil der Wörter, die hunspell nicht kennt (Verstümmelungs-Indiz).
    Fehlt hunspell, wird die Prüfung übersprungen (0.0) – sie blockiert nie."""
    candidates = [w for w in words if w.isalpha() and len(w) > 3 and not w[0].isupper()]
    if not candidates or shutil.which("hunspell") is None:
        return 0.0
    try:
        proc = subprocess.run(["hunspell", "-d", "de_DE"], input="\n".join(candidates),
                              capture_output=True, text=True, timeout=15)
    except Exception:  # noqa: BLE001
        return 0.0
    unknown = sum(1 for line in proc.stdout.splitlines()
                  if line.startswith("&") or line.startswith("#"))
    return unknown / len(candidates)


# ------------------------------------------------------------------ #
#  HTML-Seite (AI4) – attribut-tolerant statt positions-regex
# ------------------------------------------------------------------ #
ANCHOR_TAG_RE = re.compile(r"<a\b([^>]*)>", re.IGNORECASE | re.DOTALL)
ATTR_RE = re.compile(
    r"""([:\w@.\-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))""",
    re.IGNORECASE,
)


def parse_anchors(html_text: str) -> list[dict]:
    """Alle <a>-Tags eines HTML-Dokuments als Attribut-Dicts.

    Der Kern der Premium-Härtung: ausgewertet wird die ATTRIBUT-MENGE des
    Tags, nicht seine Zeichenreihenfolge. Damit bleibt der Beweis gültig,
    wenn der Render-Hook neue Attribute bekommt, href quotiert/unquotiert
    ausgibt oder `?subid=` anhängt (Vorfall 01.09.2026)."""
    anchors = []
    for tag in ANCHOR_TAG_RE.finditer(html_text or ""):
        attrs = {}
        for m in ATTR_RE.finditer(tag.group(1)):
            name = m.group(1).lower()
            value = m.group(2) if m.group(2) is not None else (
                m.group(3) if m.group(3) is not None else (m.group(4) or ""))
            attrs[name] = html_mod.unescape(value)
        if attrs.get("href"):
            anchors.append(attrs)
    return anchors


def gateway_key(href: str) -> str:
    m = GO_LINK_RE.search(href or "")
    return m.group(1) if m else ""


def classify_affiliate_anchor(attrs: dict) -> str:
    """"gateway" | "raw-partner" | "" (kein Affiliate-Bezug)."""
    href = attrs.get("href", "")
    if gateway_key(href):
        return "gateway"
    if RAW_PARTNER_RE.search(href):
        return "raw-partner"
    return ""


def rendered_affiliate_anchors(html_text: str) -> tuple[list[dict], list[dict]]:
    """(Gateway-Links, rohe Partner-Links) des gebauten HTML."""
    gateway, raw = [], []
    for attrs in parse_anchors(html_text):
        kind = classify_affiliate_anchor(attrs)
        if kind == "gateway":
            gateway.append(attrs)
        elif kind == "raw-partner":
            raw.append(attrs)
    return gateway, raw


def article_html_path(slug: str, public: Path | None = None) -> Path:
    public = public or PUBLIC
    for cand in (public / "posts" / slug / "index.html",
                 public / slug / "index.html"):
        if cand.is_file():
            return cand
    return public / "posts" / slug / "index.html"


def build_is_stale(root: Path) -> bool:
    """True, wenn public/ fehlt oder älter ist als der neueste Quellbestand.
    Git-Checkouts setzen alle mtime auf Checkout-Zeit → in CI gilt public/
    dann als aktuell (dort baut der Workflow selbst, bevor das Gate läuft)."""
    public = root / "public"
    if not public.is_dir():
        return True
    sources = [root / "hugo.toml", root / "content", root / "layouts", root / "static"]
    newest_src = 0.0
    for src in sources:
        if not src.exists():
            continue
        if src.is_file():
            newest_src = max(newest_src, src.stat().st_mtime)
            continue
        for dirpath, _dirnames, filenames in os.walk(src):
            for name in filenames:
                try:
                    newest_src = max(newest_src, os.path.getmtime(os.path.join(dirpath, name)))
                except OSError:
                    pass
    oldest_out = None
    for dirpath, _dirnames, filenames in os.walk(public):
        for name in filenames:
            try:
                mt = os.path.getmtime(os.path.join(dirpath, name))
            except OSError:
                continue
            oldest_out = mt if oldest_out is None else min(oldest_out, mt)
    if oldest_out is None:
        return True
    return newest_src > oldest_out + 1


def find_hugo(root: Path | None = None) -> str | None:
    for cand in (shutil.which("hugo"),
                 os.environ.get("HUGO_BIN"),
                 str(Path.home() / ".tools" / "hugowheel" / "hugo" / "binaries" / "hugo"),
                 "/tmp/hugo"):
        if cand and Path(cand).exists() and os.access(cand, os.X_OK):
            return cand
    return None


def rebuild_hugo(root: Path | None = None) -> tuple[bool, str]:
    root = root or ROOT
    hugo_bin = find_hugo(root)
    if not hugo_bin:
        return False, "kein Hugo-Binary gefunden (hugo im PATH?)"
    try:
        r = subprocess.run([hugo_bin, "--minify"], cwd=root,
                           capture_output=True, text=True, timeout=600)
    except Exception as exc:  # noqa: BLE001
        return False, f"Hugo-Build fehlgeschlagen: {exc}"
    if r.returncode != 0:
        tail = (r.stderr or r.stdout or "").strip().splitlines()[-6:]
        return False, "Hugo-Build fehlgeschlagen: " + " | ".join(tail)
    return True, ""


def ensure_build(root: Path | None = None) -> tuple[bool, dict]:
    """Stellt sicher, dass der Render-Beweis gegen einen AKTUELLEN Build
    geführt wird. Ohne Build kein Beweis → fail-closed (Werkzeugfehler)."""
    root = root or ROOT
    public = root / "public"
    info = {"built": False, "reason": "", "ok": True}
    if NO_BUILD:
        info["ok"] = public.is_dir()
        info["reason"] = ("--no-build: public/ fehlt" if not public.is_dir()
                          else "--no-build: vorhandenes public/ genutzt")
        return info["ok"], info
    if not public.is_dir():
        info["reason"] = "public/ fehlte → Hugo-Build"
        ok, err = rebuild_hugo(root)
        info["built"], info["ok"] = ok, ok
        if not ok:
            info["reason"] = err
        return ok, info
    if build_is_stale(root):
        info["reason"] = "public/ veraltet → Hugo-Rebuild"
        ok, err = rebuild_hugo(root)
        info["built"], info["ok"] = ok, ok
        if not ok:
            info["reason"] = err
        return ok, info
    info["reason"] = "public/ aktuell (kein Rebuild nötig)"
    return True, info


# ------------------------------------------------------------------ #
#  AI5 – Gateway-Beweis (/go/<key>/ leitet wirklich weiter)
# ------------------------------------------------------------------ #
def gateway_page_html(key: str, public: Path | None = None,
                      static_go: Path | None = None) -> tuple[Path | None, str]:
    public = public or PUBLIC
    static_go = static_go or STATIC_GO
    built = public / "go" / key / "index.html"
    if built.is_file():
        return built, "gebaut"
    shipped = static_go / key / "index.html"
    if shipped.is_file():
        return shipped, "static/go (nicht im Build!)"
    return None, "fehlt"


def verify_gateway(key: str, expected_url: str, public: Path | None = None,
                   static_go: Path | None = None) -> tuple[bool, str]:
    page, origin = gateway_page_html(key, public, static_go)
    if page is None:
        return False, f"/go/{key}/ referenziert, aber keine Gateway-Seite vorhanden"
    text = page.read_text(encoding="utf-8", errors="ignore")
    flat = text.replace('"', "").replace("'", "")
    has_refresh = "http-equiv=refresh" in flat
    has_js = bool(re.search(r"location\.(?:replace|assign|href)\s*[=(]", text))
    if not (has_refresh or has_js):
        return False, f"/go/{key}/ leitet nicht weiter (weder Meta-Refresh noch JS)"
    if expected_url:
        target = html_mod.unescape(expected_url)
        if target not in text and target.split("?")[0] not in text:
            return False, (f"/go/{key}/ leitet auf ein anderes Ziel als die Registry "
                           f"(erwartet: {target[:90]})")
    if "noindex" not in flat:
        return False, f"/go/{key}/ ist nicht auf noindex gesetzt (Duplicate-Content-Risiko)"
    if origin.startswith("static/go"):
        return False, f"/go/{key}/ existiert nur in static/go, fehlt aber im Build"
    return True, ""


# ------------------------------------------------------------------ #
#  Selbstheilung
# ------------------------------------------------------------------ #
def cta_generators():
    import affiliate_marketer as am
    return {"top": am.build_top_cta, "mid": am.mid_cta, "end": am.end_cta}


def heal_article_ctas(article: dict, broken_kinds: set,
                      reg: dict | None = None) -> list[str]:
    """Ersetzt JEDE defekte CTA-Zeile komplett durch eine neu generierte,
    garantiert syntaktisch korrekte Version (keine Text-Patches – die haben
    den Vorfall 14.08.2026 verursacht)."""
    import affiliate_marketer as am
    reg = reg if reg is not None else load_registry()
    body = article["body"]
    generators = cta_generators()
    healed: list[str] = []

    for marker, kind in CTA_MARKERS:
        if kind not in broken_kinds:
            continue
        idx = body.find(marker)
        if idx == -1:
            continue
        line_start = body.rfind("\n", 0, idx) + 1
        line_end = body.find("\n", idx)
        if line_end == -1:
            line_end = len(body)
        new_block = generators[kind](article["pillar"], reg, body).strip("\n")
        if kind == "mid":
            body = body[:line_start] + new_block + body[line_end:]
        else:
            rest = body[line_end:]
            disclaimer_m = re.match(
                r"\n_?\*?\(?Dieser Artikel enthält Affiliate-Links[^\n]*\n?", rest)
            if disclaimer_m:
                rest = rest[disclaimer_m.end():]
            prefix = re.sub(r"\n?---\s*\n?\Z", "\n", body[:line_start])
            body = prefix + new_block + "\n" + rest
        if kind not in healed:
            healed.append(kind)

    if not healed:
        return []
    write_article(article, body)
    return healed


def heal_unregistered_keys(article: dict, reg: dict) -> list[str]:
    """AI2-Heilung: /go/<unbekannt>/ und rohe Partner-URLs → Artikel-Route."""
    route = article_route(article, reg)
    body = article["body"]
    fixed: list[str] = []

    def _replace_key(match: re.Match) -> str:
        key = match.group(1)
        if key in reg:
            return match.group(0)
        fixed.append(f"/go/{key}/ → /go/{route}/")
        return f"/go/{route}/"

    new_body = GO_LINK_RE.sub(_replace_key, body)
    for raw_match in sorted({m.group(0) for m in RAW_PARTNER_RE.finditer(new_body)}):
        new_body = new_body.replace(raw_match, f"/go/{route}/")
        fixed.append(f"rohe Partner-URL → /go/{route}/")

    if fixed and new_body != body:
        write_article(article, new_body)
    return fixed


def write_article(article: dict, new_body: str) -> None:
    """Schreibt den Artikel neu – Frontmatter 1:1, Vorspann erhalten."""
    prefix = article["content"].split("---", 1)[0]
    article["body"] = new_body
    article["content"] = prefix + "---" + article["fm"] + "---" + new_body
    Path(article["path"]).write_text(article["content"], encoding="utf-8")


# ------------------------------------------------------------------ #
#  Render-Beweis pro Artikel (AI4 + AI5)
# ------------------------------------------------------------------ #
def verify_article_render(article: dict, reg: dict,
                          public: Path | None = None) -> dict:
    """Beweist, dass JEDER Affiliate-Link des Artikels wirklich im gebauten
    HTML erscheint – schlüsselgenau, nicht nur als Anzahl."""
    slug = article["slug"]
    result = {"slug": slug, "problems": [], "notes": [],
              "expected_keys": [], "rendered_keys": [],
              "expected": 0, "rendered": 0, "html_found": False}

    html_path = article_html_path(slug, public)
    if not html_path.is_file():
        result["problems"].append(
            f"Gebaute Seite fehlt: {html_path.relative_to(ROOT)} "
            "(Hugo-Build gelaufen? Artikel evtl. draft/zukünftig)")
        return result
    html_text = html_path.read_text(encoding="utf-8", errors="ignore")
    result["html_found"] = True

    gateway_anchors, raw_anchors = rendered_affiliate_anchors(html_text)
    rendered_keys = [gateway_key(a["href"]) for a in gateway_anchors]
    result["rendered"] = len(gateway_anchors)
    result["rendered_keys"] = sorted(set(rendered_keys))

    md_links = [l for l in markdown_cta_links(article["body"]) if gateway_key(l["url"])]
    expected_keys = [gateway_key(l["url"]) for l in md_links]
    result["expected"] = len(md_links)
    result["expected_keys"] = sorted(set(expected_keys))

    # --- Rohe Partner-Links im fertigen HTML = Tracking-/Kennzeichnungs-Leck
    for attrs in raw_anchors:
        result["problems"].append(
            f"Roher Partner-Link im gebauten HTML (Gateway umgangen): {attrs['href'][:90]}")

    # --- Schlüssel-Vergleich: jeder Markdown-Key muss gerendert sein
    missing = [k for k in set(expected_keys) if k not in set(rendered_keys)]
    if missing:
        result["problems"].append(
            "Affiliate-Link(s) erscheinen NICHT im gebauten HTML: "
            + ", ".join(f"/go/{k}/" for k in sorted(missing))
            + f" (Markdown: {len(md_links)} Link(s), HTML: {len(gateway_anchors)})")
    elif len(gateway_anchors) < len(md_links):
        result["problems"].append(
            f"Nur {len(gateway_anchors)} von {len(md_links)} Affiliate-Links "
            "im gebauten HTML (Link verloren – z. B. durch Publikations-Guard "
            "oder Layout-Änderung)")

    # --- Mindestbestand: ein Artikel ohne gerenderten Affiliate-Link
    #     monetarisiert nicht und ist kein Beweis-fähiger Zustand.
    if not gateway_anchors:
        result["problems"].append(
            "Kein einziger Affiliate-Link im gebauten HTML – CTA fehlt "
            "oder wird nicht gerendert")

    # --- Compliance/Attribution der gerenderten Gateway-Links
    unregistered = sorted({k for k in rendered_keys if k not in reg})
    for key in unregistered:
        result["problems"].append(
            f"/go/{key}/ wird gerendert, ist aber nicht in check24_links.yaml registriert")
    for key in sorted(set(rendered_keys) & set(reg)):
        ok, msg = verify_gateway(key, reg[key], public)
        if not ok:
            result["problems"].append(msg)

    for attrs in gateway_anchors:
        rel = (attrs.get("rel") or "").lower()
        if "sponsored" not in rel:
            result["problems"].append(
                f"Gateway-Link {attrs['href'][:60]} ohne rel=\"sponsored\" "
                "(Werbekennzeichnung/Google-Richtlinie) – Prüfpunkt: "
                "layouts/_default/_markup/render-link.html")
            break
    for attrs in gateway_anchors:
        umami = " ".join(f"{k}={v}" for k, v in attrs.items() if "umami" in k)
        if "affiliate_click" not in umami:
            result["notes"].append(
                "Klick-Attribution (data-umami-event=affiliate_click) fehlt an "
                "mindestens einem Gateway-Link – Umsatz-Messung pro Artikel "
                "unvollständig (Prüfpunkt: render-link.html)")
            break

    if result["rendered"] > 3:
        result["notes"].append(
            f"{result['rendered']} Affiliate-Links im Artikel – Anti-Stuffing "
            "prüfen (affiliate_profi_check.py A5)")
    return result


def detector_drift() -> list[str]:
    """Drift-Wächter: Der Render-Hook muss Gateway-Links weiterhin als
    affiliate_click-Anker ausgeben, sonst ist der Beweis wertlos."""
    problems = []
    if not RENDER_HOOK.is_file():
        return problems  # Hook optional (Default-Rendering) – kein Alarm
    hook = RENDER_HOOK.read_text(encoding="utf-8", errors="ignore")
    for fp in HOOK_FINGERPRINTS:
        if fp not in hook:
            problems.append(
                f"Render-Hook enthält '{fp}' nicht mehr – Render-Beweis "
                "möglicherweise veraltet (affiliate_integrity_gate.py "
                "--selftest neu justieren)")
    return problems


# ------------------------------------------------------------------ #
#  Hauptlauf
# ------------------------------------------------------------------ #
def run(root: Path | None = None, posts_dir: Path | None = None,
        do_heal: bool | None = None, allow_build: bool = True) -> dict:
    """Kernprüfung – von CLI, publish_gate und bestand_gate genutzt."""
    root = root or ROOT
    posts_dir = posts_dir or POSTS_DIR
    do_heal = (not DRY_RUN) if do_heal is None else do_heal

    reg = load_registry(root)
    reg_keys = set(reg)
    articles = load_live_articles(posts_dir)
    errors: list[str] = []

    # ---- Markdown-Prüfung (AI1–AI3) --------------------------------
    findings: dict[str, dict] = {}
    for a in articles:
        problems: list[str] = []
        broken_kinds: set[str] = set()
        for marker, kind, line, *_ in find_cta_lines(a["body"]):
            line_problems = check_cta_line(marker, line, reg_keys)
            if line_problems:
                problems.extend(line_problems)
                broken_kinds.add(kind)
        for m in RAW_PARTNER_RE.finditer(a["body"]):
            problems.append(f"Rohe Partner-URL im Artikeltext: {m.group(0)[:90]}")
        for m in GO_LINK_RE.finditer(a["body"]):
            if m.group(1) not in reg_keys:
                problems.append(f"/go/{m.group(1)}/ nicht registriert")
        if problems:
            findings[a["slug"]] = {"problems": sorted(set(problems)),
                                   "broken_kinds": broken_kinds, "healed": []}

    # ---- Selbstheilung (nie Text-Patch, nie Löschen) ----------------
    healed_slugs: list[str] = []
    if findings and do_heal:
        for a in articles:
            f = findings.get(a["slug"])
            if not f:
                continue
            actions: list[str] = []
            rerouted = heal_unregistered_keys(a, reg)
            if rerouted:
                actions.append("Linkziele neu geroutet: " + "; ".join(rerouted))
            if f["broken_kinds"]:
                kinds = heal_article_ctas(a, f["broken_kinds"], reg)
                if kinds:
                    actions.append("CTA neu generiert: " + ", ".join(kinds))
            if actions:
                # Nach Heilung neu prüfen (Markdown-Ebene)
                f["healed"] = actions
                healed_slugs.append(a["slug"])
                remaining = []
                for marker, kind, line, *_ in find_cta_lines(a["body"]):
                    remaining.extend(check_cta_line(marker, line, reg_keys))
                f["problems"] = sorted(set(remaining))

    # ---- Render-Beweis (AI4 + AI5) ---------------------------------
    render_problems: dict[str, str] = {}
    per_article: list[dict] = []
    build_info = {"built": False, "reason": "übersprungen", "ok": True}

    if articles:
        if allow_build and not NO_BUILD:
            ok, build_info = ensure_build(root)
            if not ok:
                errors.append("Render-Beweis nicht möglich: " + build_info["reason"])
        elif not (root / "public").is_dir():
            errors.append("Render-Beweis nicht möglich: public/ fehlt (--no-build)")

        if not errors:
            for a in articles:
                res = verify_article_render(a, reg, root / "public")
                per_article.append(res)
                if res["problems"]:
                    render_problems[a["slug"]] = " · ".join(res["problems"])

    # ---- Plausibilität: Massen-Blindheit = Detektorfehler ------------
    if per_article and not errors:
        with_expectation = [r for r in per_article if r["expected"] > 0]
        zero_rendered = [r for r in per_article if r["rendered"] == 0]
        if with_expectation and len(zero_rendered) == len(per_article):
            errors.append(
                "Detektor-Verdacht: KEIN einziger Artikel zeigt gerenderte "
                f"Affiliate-Links ({len(zero_rendered)}/{len(per_article)} bei 0) – "
                "das spricht gegen einen Inhaltsschaden und für eine veraltete "
                "Auswertung (Layout-/Render-Hook-Änderung). Bitte "
                "`affiliate_integrity_gate.py --selftest` prüfen und den "
                "Detektor an die aktuelle Ausgabe anpassen. Fail-closed: "
                "es wird nichts als 'defekt' geheilt oder verworfen.")
            render_problems = {}
            for r in per_article:
                r["problems"] = []
        errors.extend(detector_drift())

    still_broken = {slug: f for slug, f in findings.items()
                    if not f["healed"] or f["problems"] or slug in render_problems}

    if errors:
        code = EXIT_TOOL
    elif still_broken or render_problems:
        code = EXIT_CONTENT
    else:
        code = EXIT_OK

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "checked": len(articles),
        "slugs": [a["slug"] for a in articles],
        "findings": findings,
        "healed": healed_slugs,
        "healed_count": len(healed_slugs),
        "render_problems": render_problems,
        "per_article": per_article,
        "build": build_info,
        "registry_routes": len(reg),
        "errors": errors,
        "exit_code": code,
    }


# Konvergenz (02.09.2026): Zeitstempel und Build-Herkunft sind flüchtig und
# umgebungsabhängig. Würde der Report sie bei jedem Lauf neu schreiben, gäbe
# es TÄGLICH ein Git-Diff ohne inhaltliche Änderung – der Workflow committet
# dann, git_sync.sh meldet Erfolg, und der Deploy-Trigger springt ohne echte
# Heilung an. Deshalb: geschrieben wird nur bei inhaltlicher Änderung
# (Vergleich ohne die flüchtigen Zeilen). Gleiches Prinzip wie das
# "konvergent" in deploy.yml.
VOLATILE_REPORT_LINE = re.compile(r"^\*\*(?:Stand|Build):\*\*.*$")
VOLATILE_STATE_KEYS = ("generated_at", "build")


def _report_fingerprint(text: str) -> str:
    return "\n".join(l for l in (text or "").splitlines()
                      if not VOLATILE_REPORT_LINE.match(l.strip()))


def _state_fingerprint(payload: dict) -> str:
    return json.dumps({k: v for k, v in payload.items()
                       if k not in VOLATILE_STATE_KEYS},
                      ensure_ascii=False, sort_keys=True, default=list)


def write_report(result: dict) -> str:
    findings = result["findings"]
    render_problems = result["render_problems"]
    per_article = {r["slug"]: r for r in result["per_article"]}
    healed = result["healed"]

    status_icon = {EXIT_OK: "🟢", EXIT_CONTENT: "🔴", EXIT_TOOL: "🟠"}[result["exit_code"]]
    status_text = {
        EXIT_OK: "Alle Affiliate-Links intakt, registriert und im gebauten HTML bewiesen",
        EXIT_CONTENT: "Inhaltsschäden offen (Selbstheilung nicht vollständig)",
        EXIT_TOOL: "Beweis nicht möglich – WERKZEUGFEHLER (fail-closed, nichts veröffentlicht)",
    }[result["exit_code"]]

    lines = [
        "# 🔗 AFFILIATE-INTEGRITY-REPORT (affiliate_integrity_gate.py)",
        "",
        f"**Stand:** {result['generated_at']} · **Status:** {status_icon} {status_text}",
        "",
        f"**Geprüfte Live-Artikel:** {result['checked']} · "
        f"**Automatisch geheilt:** {len(healed)} "
        f"({', '.join(healed) if healed else '–'}) · "
        f"**Struktur-Funde:** {len(findings)} · "
        f"**Render-Funde:** {len(render_problems)} · "
        f"**Registry-Routen:** {result['registry_routes']}",
        "",
        f"**Build:** {result['build'].get('reason', '–')}",
        "",
    ]

    if result["errors"]:
        lines += ["## 🟠 Werkzeugfehler (Beweis nicht geführt – fail-closed)", ""]
        lines += [f"- {e}" for e in result["errors"]]
        lines.append("")

    if result["exit_code"] == EXIT_OK and not findings and not render_problems:
        lines += [
            "🎉 Alle CTA-Boxen sind strukturell intakt, jedes Linkziel ist in "
            "`scripts/check24_links.yaml` registriert, jeder Link erscheint "
            "tatsächlich im gebauten HTML (AI4) und jede `/go/`-Seite leitet "
            "auf die registrierte Partner-URL weiter (AI5).",
            "",
        ]

    if findings:
        lines += ["## Struktur-Funde (AI1–AI3)", ""]
        for slug, f in sorted(findings.items()):
            lines.append(f"### {slug}")
            for p in f["problems"]:
                lines.append(f"- ⚠️ {p}")
            for h in f["healed"]:
                lines.append(f"- ✅ {h}")
            lines.append("")

    if render_problems:
        lines += ["## Render-/Gateway-Funde (AI4–AI5)", ""]
        for slug, msg in sorted(render_problems.items()):
            lines.append(f"### {slug}")
            lines.append(f"- ❌ {msg}")
            lines.append("")

    if per_article and not render_problems and not findings:
        lines += ["## Render-Beweis je Artikel", "",
                  "| Artikel | Affiliate-Links (Markdown → HTML) | Gateway-Ziele |",
                  "|:---|:---:|:---|"]
        for slug in sorted(per_article):
            r = per_article[slug]
            lines.append(
                f"| {slug} | {r['expected']} → {r['rendered']} ✅ | "
                f"{', '.join('/go/' + k + '/' for k in r['rendered_keys']) or '–'} |")
        lines.append("")

    notes = [(r["slug"], n) for r in result["per_article"] for n in r["notes"]]
    if notes:
        lines += ["## Hinweise (nicht blockierend)", ""]
        lines += [f"- {slug}: {n}" for slug, n in notes]
        lines.append("")

    lines += [
        "---",
        "_Defekte CTA-Boxen werden NIE per Text-Patch geflickt, sondern komplett "
        "neu aus den geprüften Vorlagen (affiliate_marketer.py) generiert; nicht "
        "registrierte Linkziele werden auf die thematisch korrekte Route "
        "umgeroutet. Bestandsartikel werden nie gelöscht. Detektor-Selbsttest: "
        "`python3 scripts/affiliate_integrity_gate.py --selftest`._",
    ]
    text = "\n".join(lines) + "\n"
    previous = REPORT.read_text(encoding="utf-8") if REPORT.is_file() else ""
    if _report_fingerprint(previous) == _report_fingerprint(text):
        # Inhalt unverändert → Datei nicht anfassen (kein Git-Diff, kein
        # Commit, kein Deploy-Trigger). Der Log zeigt trotzdem den frischen Stand.
        result["report_written"] = False
        return text
    REPORT.write_text(text, encoding="utf-8")
    result["report_written"] = True
    return text


def write_state(result: dict) -> None:
    """Maschinenlesbarer Zustand für die Workflows (Deploy-Trigger, Issue-
    Pflege). Bewusst kleines, stabiles Schema."""
    payload = {
        "generated_at": result["generated_at"],
        "exit_code": result["exit_code"],
        "checked": result["checked"],
        "healed": result["healed"],
        "healed_count": result["healed_count"],
        "content_problems": sorted(set(result["findings"]) | set(result["render_problems"])),
        "errors": result["errors"],
        "build": result["build"],
    }
    try:
        previous = json.loads(STATE.read_text(encoding="utf-8")) if STATE.is_file() else {}
        if _state_fingerprint(previous) == _state_fingerprint(payload):
            return  # konvergent: gleicher Befund → keine Dateiänderung
        STATE.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                         encoding="utf-8")
    except (OSError, json.JSONDecodeError) as exc:
        try:
            STATE.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                             encoding="utf-8")
        except OSError as exc2:
            _say(f"⚠ Zustand konnte nicht geschrieben werden: {exc2} ({exc})")


# ------------------------------------------------------------------ #
#  SELBSTTEST (eingefrorene Fixtures – Sabotage-/Drift-Schutz)
# ------------------------------------------------------------------ #
# Reale Hook-Ausgaben. FIXTURE_CURRENT stammt 1:1 aus dem Build vom
# 02.09.2026 (Render-Hook mit Awin-SubID + Umami-Kontext), FIXTURE_LEGACY
# aus dem Stand 14.08.2026. Genau zwischen diesen beiden Formaten ist das
# alte Gate blind geworden – deshalb sind BEIDE eingefroren.
FIXTURE_CURRENT = (
    '<p>Text <a href="/go/kfz-versicherung/?subid=2026-08-26-kfz" '
    'rel="sponsored nofollow noopener" target=_blank '
    'data-umami-event=affiliate_click data-umami-event-slug=kfz-versicherung '
    'data-umami-event-article=posts/2026-08-26-kfz/index.md '
    'data-umami-event-pillar=versicherungen '
    'title="Weiter zu Check24 · Kfz-Versicherung (Partnerlink = Werbung)">'
    '<strong>Jetzt vergleichen</strong></a> und '
    '<a href="/go/haftpflicht/?subid=2026-08-26-kfz" rel="sponsored nofollow noopener" '
    'target="_blank" data-umami-event="affiliate_click" '
    'data-umami-event-slug="haftpflicht">Kostenlos vergleichen</a></p>'
)
FIXTURE_LEGACY = (
    '<a href=/go/strom/ rel="sponsored nofollow noopener" target=_blank '
    'data-umami-event=affiliate_click><strong>Kostenlos vergleichen</strong></a>'
)
FIXTURE_UNMINIFIED = (
    '<a href="/go/gas/"\n   rel="sponsored nofollow noopener"\n'
    '   target="_blank"\n   data-umami-event="affiliate_click"\n'
    '   title="Weiter zu Check24 · Gastarife (Partnerlink = Werbung)">\n'
    '  <strong>Vergleichen</strong>\n</a>'
)
FIXTURE_NO_TRACKING = '<a href="/go/dsl/">Vergleichen</a>'
FIXTURE_RAW_PARTNER = (
    '<a href="https://a.check24.net/misc/click.php?pid=80968&aid=18&deep=strom" '
    'rel="sponsored">Direkt zum Partner</a>'
)
FIXTURE_DANGLING_MD = (
    "💡 **Schnell-Tipp von FranksFinanzcheck:** Starte jetzt den Vergleich: "
    "[**Kostenlos vergleichen**  \n_(Dieser Artikel enthält Affiliate-Links.)_"
)
FIXTURE_RAW_MD = (
    "💡 **Schnell-Tipp von FranksFinanzcheck:** Starte jetzt den Vergleich: "
    "[**Kostenlos vergleichen**](https://a.check24.net/misc/click.php?pid=80968&aid=18&deep=strom)"
)
FIXTURE_UNREGISTERED_MD = (
    "👉 **Jetzt vergleichen und sparen:** [**Tarifrechner starten**](/go/geheim-partner/)"
)
FIXTURE_INTACT_MD = (
    "💡 **Schnell-Tipp von FranksFinanzcheck:** Die besten Tarife findest du über "
    "unseren Partner-Vergleich: [**Kostenlos vergleichen**](/go/kfz-versicherung/)"
)
FIXTURE_GATEWAY_PAGE = """<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">
<meta name="robots" content="noindex,nofollow,noarchive">
<script>location.replace("https://a.check24.net/misc/click.php?pid=80968&aid=18&deep=kfz-versicherung");</script>
<meta http-equiv="refresh" content="0; url=https://a.check24.net/misc/click.php?pid=80968&aid=18&deep=kfz-versicherung">
</head><body><p>Du wirst weitergeleitet …</p></body></html>
"""


def run_selftest() -> list[str]:
    """Beweist, dass Detektor, Markdown-Prüfung, Heilung und Gateway-Beweis
    funktionieren – mit eingefrorenen Fixtures aus REALER Hook-Ausgabe.
    Exit 2 bei Bruch (Haus-Konvention aller Wachen)."""
    import tempfile
    errors: list[str] = []

    def expect(cond: bool, msg: str) -> None:
        if not cond:
            errors.append(msg)

    # 1) Attribut-tolerante Anker-Erkennung (der Kern des Vorfalls 01.09.)
    cur = parse_anchors(FIXTURE_CURRENT)
    expect(len(cur) == 2, f"aktuelles Hook-Format: 2 Anker erwartet, {len(cur)} gefunden")
    gw, raw = rendered_affiliate_anchors(FIXTURE_CURRENT)
    expect(len(gw) == 2 and not raw,
           "aktuelles Hook-Format: beide Gateway-Links müssen erkannt werden")
    expect(sorted(gateway_key(a["href"]) for a in gw) == ["haftpflicht", "kfz-versicherung"],
           "Gateway-Schlüssel müssen trotz ?subid= korrekt extrahiert werden")
    expect(all("sponsored" in (a.get("rel") or "") for a in gw),
           "rel=sponsored muss im aktuellen Format erkannt werden")

    legacy_gw, _ = rendered_affiliate_anchors(FIXTURE_LEGACY)
    expect(len(legacy_gw) == 1 and gateway_key(legacy_gw[0]["href"]) == "strom",
           "Legacy-Format (14.08., unquotiertes href) muss weiterhin erkannt werden")

    unmin_gw, _ = rendered_affiliate_anchors(FIXTURE_UNMINIFIED)
    expect(len(unmin_gw) == 1 and gateway_key(unmin_gw[0]["href"]) == "gas",
           "unminifiziertes, mehrzeiliges Format muss erkannt werden")

    no_track, _ = rendered_affiliate_anchors(FIXTURE_NO_TRACKING)
    expect(len(no_track) == 1, "Gateway-Link OHNE Umami-Attribut muss trotzdem zählen "
                               "(Zählung darf nicht an Attributen hängen)")
    _, raw_only = rendered_affiliate_anchors(FIXTURE_RAW_PARTNER)
    expect(len(raw_only) == 1, "roher Partner-Link im HTML muss als Leck erkannt werden")
    expect(len(rendered_affiliate_anchors("<p>kein Link</p>")[0]) == 0,
           "leere Seite muss 0 Affiliate-Links liefern")

    # 2) Markdown-Prüfung AI1–AI3 (Schadensbilder 14.08.2026)
    reg_keys = {"kfz-versicherung", "haftpflicht", "strom", "gas", "allgemein"}
    expect(bool(check_cta_line("Schnell-Tipp von FranksFinanzcheck",
                               FIXTURE_DANGLING_MD, reg_keys)),
           "Dangling-Link (Vorfall 14.08.) muss erkannt werden")
    expect(any("Rohe" in p for p in check_cta_line(
        "Schnell-Tipp von FranksFinanzcheck", FIXTURE_RAW_MD, reg_keys)),
        "rohe Partner-URL in der CTA muss erkannt werden")
    expect(any("registriert" in p for p in check_cta_line(
        "Jetzt vergleichen und sparen", FIXTURE_UNREGISTERED_MD, reg_keys)),
        "nicht registrierter /go/-Key muss erkannt werden")
    expect(not check_cta_line("Schnell-Tipp von FranksFinanzcheck",
                              FIXTURE_INTACT_MD, reg_keys),
           "intakte CTA-Zeile darf keine Funde liefern")

    # 3) CTA-Zeilen-Deduplikation (mehrere Marker in einer Zeile)
    double = ("👉 **Jetzt vergleichen und sparen:** "
              "[**Sparend zuerst vergleichen**](/go/strom/)")
    expect(len(find_cta_lines(double)) == 1,
           "zwei Marker in einer Zeile dürfen nur EINE CTA ergeben (Doppelzählung)")
    expect(len(markdown_cta_links(double)) == 1,
           "zwei Marker in einer Zeile dürfen nur EINEN Link ergeben")

    # 4) Gateway-Beweis AI5
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "public" / "go" / "kfz-versicherung").mkdir(parents=True)
        (root / "public" / "go" / "kfz-versicherung" / "index.html").write_text(
            FIXTURE_GATEWAY_PAGE, encoding="utf-8")
        ok, msg = verify_gateway(
            "kfz-versicherung",
            "https://a.check24.net/misc/click.php?pid=80968&aid=18&deep=kfz-versicherung",
            root / "public", root / "static" / "go")
        expect(ok, f"gültige Gateway-Seite muss bestehen ({msg})")
        ok2, msg2 = verify_gateway("strom", "https://x/y", root / "public",
                                   root / "static" / "go")
        expect(not ok2, "fehlende Gateway-Seite muss auffallen")
        ok3, msg3 = verify_gateway(
            "kfz-versicherung",
            "https://partner.example/ganz-anderes-ziel",
            root / "public", root / "static" / "go")
        expect(not ok3, "Gateway-Seite mit falschem Ziel muss auffallen")
        (root / "public" / "go" / "kfz-versicherung" / "index.html").write_text(
            "<html><head></head><body><p>nix</p></body></html>", encoding="utf-8")
        ok4, _ = verify_gateway("kfz-versicherung", "", root / "public",
                                root / "static" / "go")
        expect(not ok4, "Seite ohne Redirect muss auffallen")

        # 5) Selbstheilung: defekte CTA wird neu generiert (kein Text-Patch)
        posts = root / "content" / "posts" / "2026-09-02-test"
        posts.mkdir(parents=True)
        broken = ("---\ntitle: \"Test\"\npillar: \"versicherungen\"\ndraft: false\n---\n\n"
                  "Intro.\n\n## Abschnitt\n\n" + FIXTURE_DANGLING_MD + "\n\n"
                  "## Fazit\n\n" + FIXTURE_UNREGISTERED_MD + "\n")
        (posts / "index.md").write_text(broken, encoding="utf-8")
        article = load_live_articles(root / "content" / "posts")[0]
        kinds = set()
        for marker, kind, line, *_ in find_cta_lines(article["body"]):
            if check_cta_line(marker, line, reg_keys):
                kinds.add(kind)
        expect(kinds == {"top", "end"}, f"beide defekten CTA-Arten erwarten, {kinds} gefunden")
        reg = {k: "https://a.check24.net/x" for k in reg_keys}
        rerouted = heal_unregistered_keys(article, reg)
        healed = heal_article_ctas(article, kinds, reg)
        expect(bool(healed), "Heilung muss mindestens eine CTA neu generieren")
        text_after = Path(posts / "index.md").read_text(encoding="utf-8")
        expect(not GO_LINK_RE.findall(text_after.replace("/go/haftpflicht/", ""))
               or all(k in reg for k in GO_LINK_RE.findall(text_after)),
               "nach Heilung dürfen nur registrierte /go/-Keys im Artikel stehen")
        expect(bool(rerouted), "nicht registrierter Key muss umgeroutet werden")
        for marker, kind, line, *_ in find_cta_lines(
                text_after.split("---", 2)[2]):
            expect(not check_cta_line(marker, line, reg_keys),
                   f"geheilte CTA ({kind}) muss die Prüfung bestehen")

    # 6) Build-Frische-Erkennung (eigenes Wurzel-Fixture, unabhängig von 4/5)
    with tempfile.TemporaryDirectory() as tmp2:
        root2 = Path(tmp2)
        (root2 / "content").mkdir()
        (root2 / "hugo.toml").write_text("baseURL = '/'\n", encoding="utf-8")
        expect(build_is_stale(root2) is True, "fehlendes public/ muss als 'baue' gelten")
        (root2 / "public").mkdir()
        (root2 / "public" / "index.html").write_text("<html></html>", encoding="utf-8")
        future = os.path.getmtime(root2 / "public" / "index.html") + 10
        os.utime(root2 / "public" / "index.html", (future, future))
        expect(build_is_stale(root2) is False,
               "frisches public/ darf keinen Rebuild auslösen")
        os.utime(root2 / "hugo.toml", (future + 100, future + 100))
        expect(build_is_stale(root2) is True,
               "geänderte Quelle muss Rebuild auslösen")

    # 7) Drift-Wächter gegen das Live-Template
    if RENDER_HOOK.is_file():
        hook = RENDER_HOOK.read_text(encoding="utf-8", errors="ignore")
        for fp in HOOK_FINGERPRINTS:
            expect(fp in hook,
                   f"Render-Hook-Fingerabdruck '{fp}' fehlt – Detektor neu justieren")
    else:
        errors.append(f"{RENDER_HOOK.relative_to(ROOT)} fehlt – "
                      "Gateway-Links würden ohne Tracking gerendert")

    return errors


# ------------------------------------------------------------------ #
def main() -> int:
    if SELFTEST:
        errs = run_selftest()
        if errs:
            print("🛑 AFFILIATE-INTEGRITY-SELFTEST FEHLGESCHLAGEN – "
                  "der Detektor ist defekt (fail-closed, nichts wird geheilt/verworfen):")
            for e in errs:
                print(f"   - {e}")
            return EXIT_TOOL
        print("✅ AFFILIATE-INTEGRITY-SELFTEST bestanden (attribut-tolerante Anker-"
              "Erkennung inkl. ?subid=/Legacy/unminifiziert, rohe Partner-Links, "
              "AI1–AI3-Schadensbilder, Deduplikation, AI5-Gateway-Beweis, "
              "Selbstheilung, Build-Frische, Hook-Drift-Wächter).")
        return EXIT_OK

    result = run()

    if AS_JSON:
        result["report_written"] = False   # --json schreibt keine Dateien
        print(json.dumps(result, ensure_ascii=False, indent=1, default=list))
    else:
        print(write_report(result))
        write_state(result)
        if result["exit_code"] == EXIT_TOOL:
            _say("🟠 WERKZEUGFEHLER – Render-Beweis konnte nicht geführt werden "
                 "(fail-closed: keine Veröffentlichung).")
        elif result["exit_code"] == EXIT_CONTENT:
            _say(f"🔴 {len(result['render_problems']) + len(result['findings'])} "
                 "Fund(e) offen – Details im Report oben.")
        else:
            _say("🟢 Affiliate-Integrität bewiesen.")
    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
