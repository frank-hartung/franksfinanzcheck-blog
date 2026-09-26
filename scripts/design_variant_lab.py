#!/usr/bin/env python3
"""Design-Varianten-Werkbank: bauen, statisch vermessen, vergleichen.

Teil der Design-Varianten-Werkbank (Rollout 26.09.2026, Runbook:
docs/ANLEITUNG-DESIGN-VARIANTEN.md).

DIE ZWEI MESSEBENEN
-------------------
  Tier A „statisch"  – DIESES SKRIPT. Baut die Variante mit Hugo und
                       vermisst das AUSGELIEFERTE HTML: DOM-Budget,
                       SEO-Invarianten, Conversion-Bausteine, Bytes.
                       Braucht keinen Browser, läuft überall, dauert
                       Sekunden.
  Tier B „gerendert"  – e2e/variant-metrics.mjs. Misst, was erst im
                       Browser entsteht: Kontraste, Tap-Ziele, Fokus,
                       CLS/LCP, Lighthouse-Kategorien.

Beide schreiben in dieselbe Datei
`.cache/design-varianten/<id>/messung.json` (Abschnitt `tiers`), und
`scripts/design_variant_gate.py` bewertet sie gegen
`data/design/regelwerk.yaml`. Eine Variante gilt erst als vermessen,
wenn BEIDE Ebenen `ok` melden – Tier A allein sieht keine Farbe.

WARUM DIE BASIS IMMER MITGEBAUT WIRD
------------------------------------
Ein Messwert ohne Kontrollgruppe ist eine Zahl, keine Aussage. Jeder
Vergleich läuft gegen eine Basis-Messung aus demselben Lauf – nicht
gegen einen Wert von letzter Woche, als der Blog noch andere Artikel
hatte.

AUFRUF
------
  python3 scripts/design_variant_lab.py --liste
  python3 scripts/design_variant_lab.py --lauf alle       # bauen + messen
  python3 scripts/design_variant_lab.py --lauf v-hero-conversion
  python3 scripts/design_variant_lab.py --vergleich       # Report schreiben
  python3 scripts/design_variant_lab.py --selftest

EXIT-CODES
----------
  0 = Lauf erfolgreich
  1 = mindestens ein Bau/Messlauf fehlgeschlagen
  2 = schwerer Fehler (Hugo fehlt, Register unlesbar)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

REGISTER = ROOT / "data" / "design" / "varianten.yaml"
REGELWERK = ROOT / "data" / "design" / "regelwerk.yaml"
CACHE = ROOT / ".cache" / "design-varianten"
REPORT = ROOT / "DESIGN-VARIANTEN-REPORT.md"

BAU_TIMEOUT = 300


# ======================================================================
# Kleinkram
# ======================================================================

def _yaml():
    try:
        import yaml
    except ImportError:  # pragma: no cover
        raise SystemExit("PyYAML fehlt: pip install pyyaml")
    return yaml


def lade_register() -> dict:
    if not REGISTER.exists():
        raise SystemExit(f"Varianten-Register fehlt: {REGISTER}")
    return _yaml().safe_load(REGISTER.read_text(encoding="utf-8")) or {}


def lade_regelwerk() -> dict:
    if not REGELWERK.exists():
        return {}
    return _yaml().safe_load(REGELWERK.read_text(encoding="utf-8")) or {}


def hugo_bin() -> str | None:
    """Hugo finden – PATH zuerst, dann die üblichen Installationsorte.

    Die PyPI-Installation (hugo-python-distributions) legt das Binary
    nicht in den PATH; genau dieser Fall kostet sonst jedes Mal zehn
    Minuten Suche.
    """
    if gefunden := shutil.which("hugo"):
        return gefunden
    kandidaten = [
        Path("/usr/local/bin/hugo"),
        Path.home() / ".local" / "bin" / "hugo",
    ]
    try:
        import hugo as hugo_pkg  # type: ignore
        basis = getattr(hugo_pkg, "__file__", None)
        wurzel = Path(basis).parent if basis else Path(list(hugo_pkg.__path__)[0])
        kandidaten.append(wurzel / "binaries" / "hugo")
    except Exception:  # noqa: BLE001
        pass
    for k in kandidaten:
        if k.exists() and os.access(k, os.X_OK):
            return str(k)
    return None


def jetzt() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ======================================================================
# Bauen
# ======================================================================

def bauen(vid: str, ist_basis: bool) -> tuple[bool, str, Path]:
    """Baut eine Variante nach .cache/design-varianten/<id>/public."""
    binaer = hugo_bin()
    if not binaer:
        return False, ("Hugo nicht gefunden. Installation: "
                       "pip install hugo==0.164.0 (Extended nötig)"), Path()

    ziel = CACHE / vid / "public"
    if ziel.exists():
        shutil.rmtree(ziel)
    ziel.mkdir(parents=True, exist_ok=True)

    umgebung = dict(os.environ)
    if ist_basis:
        # Ausdrücklich leeren: Eine geerbte Variable aus der Shell würde
        # sonst die Kontrollgruppe heimlich zur Variante machen – der
        # Vergleich wäre wertlos und niemand würde es merken.
        umgebung.pop("HUGO_PARAMS_DESIGNVARIANTE", None)
    else:
        umgebung["HUGO_PARAMS_DESIGNVARIANTE"] = vid

    proc = subprocess.run(
        [binaer, "--destination", str(ziel), "--logLevel", "warn"],
        cwd=str(ROOT), env=umgebung, capture_output=True, text=True,
        timeout=BAU_TIMEOUT,
    )
    if proc.returncode != 0:
        fehler = (proc.stderr or proc.stdout or "").strip().splitlines()
        return False, " | ".join(fehler[-3:]) or "Hugo-Build fehlgeschlagen", ziel
    return True, "", ziel


# ======================================================================
# Tier A – statische Messung am gebauten HTML
# ======================================================================

# Bewusst gezielte Regexe statt eines DOM-Baus: Die Attribute, die hier
# zählen (rel, data-umami-event, width/height, alt), hängt der Parser in
# dom_audit.py nicht an die Knoten – er misst Struktur, nicht Inhalt.
RE_H1 = re.compile(r"<h1[\s>]", re.I)
RE_CANONICAL = re.compile(r'<link[^>]+rel=["\']canonical["\']', re.I)
RE_STYLE = re.compile(r"<style\b[^>]*>(.*?)</style>", re.I | re.S)
RE_IMG = re.compile(r"<img\b[^>]*>", re.I)
RE_ANKER = re.compile(r"<a\b[^>]*>", re.I)
RE_ATTR = re.compile(r'([a-zA-Z0-9_:-]+)\s*=\s*"([^"]*)"')
RE_SCHEMA_TYP = re.compile(r'"@type"\s*:\s*"([^"]+)"')


def attrs_von(tag: str) -> dict[str, str]:
    return {m.group(1).lower(): m.group(2) for m in RE_ATTR.finditer(tag)}


def stichprobe(public: Path) -> list[tuple[str, Path]]:
    """Repräsentative Seiten: Startseite, Liste, Ratgeber, 3 Artikel.

    Nicht „alle Seiten": Die SEO-/Conversion-Kennzahlen sind je Seitentyp
    identisch (dasselbe Template) – 400-mal dasselbe zu zählen erzeugt
    große Zahlen ohne mehr Erkenntnis. Das DOM-Budget läuft davon
    unabhängig über ALLE Seiten (dom_audit).
    """
    seiten: list[tuple[str, Path]] = []
    start = public / "index.html"
    if start.exists():
        seiten.append(("/", start))
    for rel in ("posts/index.html", "pillar/index.html"):
        p = public / rel
        if p.exists():
            seiten.append(("/" + rel[: -len("index.html")], p))
    artikel = sorted((public / "posts").glob("*/index.html"), reverse=True)[:3]
    for p in artikel:
        seiten.append(("/" + p.parent.name + "/", p))
    return seiten


def messen_statisch(vid: str, public: Path, regelwerk: dict) -> dict:
    """Tier A: alles, was man dem ausgelieferten HTML ansehen kann."""
    try:
        import dom_audit
    except ImportError as exc:  # pragma: no cover
        return {"status": "fehler", "grund": f"dom_audit nicht importierbar: {exc}"}

    if not (public / "index.html").exists():
        return {"status": "fehler", "grund": f"Kein Build unter {public}"}

    # --- DOM-Budget über ALLE Seiten (Browser-treu, ohne Browser) -----
    dom = dom_audit.audit_dir(str(public))
    zeilen = dom.get("rows") or []
    werte: dict = {
        "seiten_gesamt": dom.get("pages", 0),
        "dom_kinder_max": max((r["maxchildren"] for r in zeilen), default=0),
        "dom_head_kinder_max": max((r["headchildren"] for r in zeilen), default=0),
        "dom_tiefe_max": max((r["depth"] for r in zeilen), default=0),
        "dom_elemente_max": max((r["elements"] for r in zeilen), default=0),
    }

    seo_rw = regelwerk.get("seo") or {}
    conv_rw = (regelwerk.get("conversion") or {}).get("erhalten") or {}
    pflicht_bausteine = list(conv_rw.get("pflicht_bausteine") or [])

    h1_abweichungen = canonical_fehlt = 0
    bilder_ohne_masse = alt_luecken = 0
    interne_links = 0
    affiliate_rel_fehler = 0
    seiten_gewicht_max = 0
    schema_typen: set[str] = set()
    variante_markiert = False
    proben: list[dict] = []

    for rel, pfad in stichprobe(public):
        html = pfad.read_text(encoding="utf-8", errors="ignore")
        seiten_gewicht_max = max(seiten_gewicht_max, len(html.encode("utf-8")))

        h1 = len(RE_H1.findall(html))
        if h1 != int(seo_rw.get("h1_anzahl_exakt", 1)):
            h1_abweichungen += 1
        if not RE_CANONICAL.search(html):
            canonical_fehlt += 1
        schema_typen.update(RE_SCHEMA_TYP.findall(html))
        if 'data-ff-variante="' in html:
            variante_markiert = True

        for tag in RE_IMG.findall(html):
            a = attrs_von(tag)
            if not (a.get("width") and a.get("height")):
                bilder_ohne_masse += 1
            if "alt" not in a:
                alt_luecken += 1

        for tag in RE_ANKER.findall(html):
            a = attrs_von(tag)
            href = a.get("href", "")
            if href.startswith("/go/"):
                rel_attr = a.get("rel", "")
                if not all(t in rel_attr for t in ("sponsored", "nofollow", "noopener")):
                    affiliate_rel_fehler += 1
            elif href.startswith("/") and not href.startswith("//"):
                interne_links += 1

        proben.append({"seite": rel, "h1": h1, "bytes": len(html.encode("utf-8"))})

    # --- Startseite im Detail: CTA-Kette, Pflicht-Bausteine, CSS ------
    start_html = (public / "index.html").read_text(encoding="utf-8", errors="ignore")
    stylesheet_bytes = sum(len(m.encode("utf-8")) for m in RE_STYLE.findall(start_html))

    cta_anzahl = cta_ohne_umami = 0
    for tag in RE_ANKER.findall(start_html):
        a = attrs_von(tag)
        if "ff-btn" in a.get("class", ""):
            cta_anzahl += 1
            if not a.get("data-umami-event"):
                cta_ohne_umami += 1

    fehlende_bausteine = [b for b in pflicht_bausteine
                          if b.lstrip(".#") not in start_html]
    newsletter = bool(re.search(r"newsletter-(anmeldung|footer)", start_html, re.I))

    werte.update({
        "h1_abweichungen": h1_abweichungen,
        "canonical_fehlt": canonical_fehlt,
        "schema_typen": sorted(schema_typen),
        "interne_links": interne_links,
        "bilder_ohne_masse": bilder_ohne_masse,
        "alt_luecken": alt_luecken,
        "affiliate_rel_fehler": affiliate_rel_fehler,
        "seiten_gewicht_bytes_max": seiten_gewicht_max,
        "stylesheet_bytes": stylesheet_bytes,
        "cta_anzahl": cta_anzahl,
        "cta_ohne_umami": cta_ohne_umami,
        "pflicht_bausteine_fehlen": fehlende_bausteine,
        "newsletter_einstieg": newsletter,
        "variante_im_markup": variante_markiert,
    })

    # Fehlende Pflicht-Schematypen als eigener Wert (das Gate liest ihn
    # nicht blind, sondern gegen seo.schema_typen_pflicht).
    pflicht_schema = set(seo_rw.get("schema_typen_pflicht") or [])
    werte["schema_typen_fehlen"] = sorted(pflicht_schema - schema_typen)

    return {
        "status": "ok",
        "gemessen": jetzt(),
        "stichprobe": proben,
        "werte": werte,
    }


# ======================================================================
# Messdatei (Tier A und Tier B teilen sich eine Datei)
# ======================================================================

def messdatei(vid: str) -> Path:
    return CACHE / vid / "messung.json"


def schreibe_tier(vid: str, tier: str, daten: dict) -> None:
    """Schreibt EINE Ebene, ohne die andere zu verlieren."""
    pfad = messdatei(vid)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    bestand = {}
    if pfad.exists():
        try:
            bestand = json.loads(pfad.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            bestand = {}
    bestand.setdefault("variante", vid)
    bestand.setdefault("tiers", {})
    bestand["tiers"][tier] = daten
    bestand["aktualisiert"] = jetzt()
    pfad.write_text(json.dumps(bestand, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def lies_messung(vid: str) -> dict:
    pfad = messdatei(vid)
    if not pfad.exists():
        return {}
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


# ======================================================================
# Lauf
# ======================================================================

def lauf(ids: list[str], register: dict, regelwerk: dict) -> int:
    eintraege = {str(e.get("id")): e for e in (register.get("varianten") or [])}
    fehler = 0

    for vid in ids:
        eintrag = eintraege.get(vid)
        if not eintrag:
            print(f"✗ {vid}: steht nicht im Register", file=sys.stderr)
            fehler += 1
            continue

        ist_basis = vid == "basis"
        status = str(eintrag.get("status", "?"))
        print(f"→ {vid} (Status {status}) bauen …", flush=True)
        ok, meldung, ziel = bauen(vid, ist_basis)
        if not ok:
            print(f"✗ {vid}: {meldung}", file=sys.stderr)
            schreibe_tier(vid, "statisch", {"status": "fehler", "grund": meldung})
            fehler += 1
            continue

        if not ist_basis and status not in ("freigegeben", "live"):
            print(f"  ⚠ {vid} ist {status} – dieser Bau gehört in die "
                  "Werkbank, nicht auf den Server.")

        messung = messen_statisch(vid, ziel, regelwerk)
        schreibe_tier(vid, "statisch", messung)
        if messung.get("status") != "ok":
            print(f"✗ {vid}: Messung fehlgeschlagen – {messung.get('grund')}",
                  file=sys.stderr)
            fehler += 1
            continue

        w = messung["werte"]
        marker = "ja" if w["variante_im_markup"] else "nein"
        print(f"  ✓ {w['seiten_gesamt']} Seiten · DOM max {w['dom_elemente_max']} "
              f"Elemente · CSS {w['stylesheet_bytes']} B · CTA {w['cta_anzahl']} "
              f"· Variantenmarke im Markup: {marker}")

        # Ein Varianten-Bau OHNE Marke ist ein stiller Fehlschlag: Man
        # vermisst die Basis und hält sie für die Variante.
        if not ist_basis and not w["variante_im_markup"]:
            print(f"✗ {vid}: Der Bau trägt keine Variantenmarke – es wurde die "
                  "Basis vermessen.", file=sys.stderr)
            fehler += 1

    return 1 if fehler else 0


# ======================================================================
# Vergleich / Report
# ======================================================================

VERGLEICHSFELDER = [
    ("dom_elemente_max", "DOM-Elemente (max)", "kleiner"),
    ("dom_head_kinder_max", "Head-Kinder (max)", "kleiner"),
    ("stylesheet_bytes", "Inline-CSS (Startseite)", "kleiner"),
    ("seiten_gewicht_bytes_max", "Seitengewicht (max)", "kleiner"),
    ("interne_links", "Interne Links (Stichprobe)", "groesser"),
    ("cta_anzahl", "CTAs (Startseite)", "groesser"),
    ("cta_ohne_umami", "CTAs ohne Umami-Event", "kleiner"),
    ("affiliate_rel_fehler", "Affiliate-Links ohne rel", "kleiner"),
    ("bilder_ohne_masse", "Bilder ohne width/height", "kleiner"),
    ("alt_luecken", "Bilder ohne alt", "kleiner"),
]


def vergleich(register: dict) -> str:
    basis = (lies_messung("basis").get("tiers") or {}).get("statisch") or {}
    basis_werte = basis.get("werte") or {}
    zeilen: list[str] = []

    zeilen.append("# Design-Varianten – Messvergleich")
    zeilen.append("")
    zeilen.append(f"> Erzeugt: {jetzt()} · `scripts/design_variant_lab.py --vergleich`  ")
    zeilen.append("> Lauf-Artefakt (gitignored). Die Entscheidung trifft ein Mensch, "
                  "nicht diese Tabelle.")
    zeilen.append("")

    if not basis_werte:
        zeilen.append("**Keine Basis-Messung vorhanden.** Ohne Kontrollgruppe ist "
                      "jeder Zahlenvergleich wertlos:")
        zeilen.append("")
        zeilen.append("```bash")
        zeilen.append("python3 scripts/design_variant_lab.py --lauf basis")
        zeilen.append("```")
        return "\n".join(zeilen) + "\n"

    for eintrag in register.get("varianten") or []:
        vid = str(eintrag.get("id"))
        if vid == "basis":
            continue
        messung = lies_messung(vid)
        tiers = messung.get("tiers") or {}
        a = tiers.get("statisch") or {}
        b = tiers.get("gerendert") or {}

        zeilen.append(f"## {vid} — {eintrag.get('titel', '')}")
        zeilen.append("")
        zeilen.append(f"* **Status:** `{eintrag.get('status')}`")
        zeilen.append(f"* **Herkunft:** {eintrag.get('herkunft', '—')}")
        hyp = " ".join(str(eintrag.get("hypothese") or "").split())
        zeilen.append(f"* **Hypothese:** {hyp or '—'}")
        zeilen.append("")

        if a.get("status") != "ok":
            zeilen.append(f"> Tier A (statisch): **{a.get('status', 'nicht gemessen')}** "
                          f"{a.get('grund', '')}")
            zeilen.append("")
            continue

        w = a.get("werte") or {}
        zeilen.append("| Kennzahl | Basis | Variante | Δ | Richtung |")
        zeilen.append("|---|---:|---:|---:|---|")
        for schluessel, name, gut in VERGLEICHSFELDER:
            bv, vv = basis_werte.get(schluessel), w.get(schluessel)
            if bv is None or vv is None:
                continue
            delta = vv - bv
            pfeil = "—" if delta == 0 else ("↑" if delta > 0 else "↓")
            bewertung = "neutral"
            if delta != 0:
                besser = (delta < 0) if gut == "kleiner" else (delta > 0)
                bewertung = "besser" if besser else "schlechter"
            zeilen.append(f"| {name} | {bv} | {vv} | {delta:+d} {pfeil} | {bewertung} |")
        zeilen.append("")

        if b.get("status") == "ok":
            bw = b.get("werte") or {}
            zeilen.append("**Tier B (Browser):** "
                          f"Kontrast min {bw.get('kontrast_min', '?')} · "
                          f"Tap min {bw.get('tap_min_px', '?')}px · "
                          f"CLS {bw.get('cls', '?')} · "
                          f"LCP {bw.get('lcp_ms', '?')}ms")
        else:
            zeilen.append("**Tier B (Browser): nicht gemessen** – ohne sie sieht "
                          "niemand Kontraste, Fokus oder CLS. "
                          "`node e2e/variant-metrics.mjs --variante " + vid + "`")
        zeilen.append("")

    zeilen.append("---")
    zeilen.append("")
    zeilen.append("Bewertung gegen die Budgets: `python3 scripts/design_variant_gate.py`")
    return "\n".join(zeilen) + "\n"


# ======================================================================
# Liste
# ======================================================================

def liste(register: dict) -> None:
    print("Design-Varianten")
    print("================")
    aktiv = str(register.get("aktiv") or "")
    print(f"Produktiv laut Register: {aktiv or '(Basis)'}\n")
    for e in register.get("varianten") or []:
        vid = str(e.get("id"))
        m = lies_messung(vid).get("tiers") or {}
        ta = (m.get("statisch") or {}).get("status", "—")
        tb = (m.get("gerendert") or {}).get("status", "—")
        unterschrift = "ja" if (e.get("freigabe") or {}).get("mensch") else "nein"
        print(f"  {vid:24} status={str(e.get('status')):12} "
              f"TierA={ta:12} TierB={tb:14} Freigabe={unterschrift}")
    print("\nMessdaten: .cache/design-varianten/<id>/messung.json")


# ======================================================================
# Selbsttest
# ======================================================================

def _selftest() -> int:
    import tempfile

    # 1) Attribut-Parser
    a = attrs_von('<a href="/go/dsl/" rel="sponsored nofollow noopener" '
                  'data-umami-event="affiliate_click">')
    assert a["href"] == "/go/dsl/" and "sponsored" in a["rel"]

    # 2) Statische Messung an einem Mini-Build
    with tempfile.TemporaryDirectory() as tmp:
        public = Path(tmp) / "public"
        public.mkdir()
        (public / "index.html").write_text("""<!doctype html><html><head>
<link rel="canonical" href="https://x/"><style data-ff-variante="v-x">.a{}</style>
<script type="application/ld+json">{"@type":"BreadcrumbList"}</script>
</head><body><h1>T</h1>
<div class="ff-home-ctas">
<a class="ff-btn ff-btn-primary" href="/posts/" data-umami-event="cta_click">A</a>
<a class="ff-btn ff-btn-secondary" href="/pillar/">B</a>
</div>
<div class="ff-trust-row">x</div>
<a href="/go/dsl/" rel="sponsored nofollow">Partner</a>
<img src="a.jpg" width="10" height="10" alt="x">
<img src="b.jpg">
<a href="/newsletter-anmeldung/">N</a>
</body></html>""", encoding="utf-8")

        regelwerk = {
            "seo": {"h1_anzahl_exakt": 1, "schema_typen_pflicht": ["BreadcrumbList"]},
            "conversion": {"erhalten": {"pflicht_bausteine": [".ff-home-ctas",
                                                              ".ff-trust-row",
                                                              ".gibt-es-nicht"]}},
        }
        m = messen_statisch("v-x", public, regelwerk)
        assert m["status"] == "ok", m
        w = m["werte"]
        assert w["cta_anzahl"] == 2, w["cta_anzahl"]
        assert w["cta_ohne_umami"] == 1, w["cta_ohne_umami"]
        # rel ohne noopener -> Befund
        assert w["affiliate_rel_fehler"] == 1, w["affiliate_rel_fehler"]
        assert w["bilder_ohne_masse"] == 1 and w["alt_luecken"] == 1
        assert w["variante_im_markup"] is True
        assert w["schema_typen_fehlen"] == []
        assert w["pflicht_bausteine_fehlen"] == [".gibt-es-nicht"]
        assert w["newsletter_einstieg"] is True
        assert w["h1_abweichungen"] == 0
        # /go/ zählt NICHT als interner Link (sonst belohnt man Affiliate-Spam)
        assert w["interne_links"] == 3, w["interne_links"]

    # 3) Messdatei-Merge: Tier B darf Tier A nicht löschen
    global CACHE
    original = CACHE
    with tempfile.TemporaryDirectory() as tmp:
        CACHE = Path(tmp)
        schreibe_tier("v-x", "statisch", {"status": "ok", "werte": {"a": 1}})
        schreibe_tier("v-x", "gerendert", {"status": "ok", "werte": {"b": 2}})
        daten = lies_messung("v-x")
        assert daten["tiers"]["statisch"]["werte"]["a"] == 1
        assert daten["tiers"]["gerendert"]["werte"]["b"] == 2
    CACHE = original

    # 4) Vergleich ohne Basis meldet das ehrlich
    with tempfile.TemporaryDirectory() as tmp:
        CACHE = Path(tmp)
        text = vergleich({"varianten": [{"id": "basis"}, {"id": "v-x"}]})
        assert "Keine Basis-Messung" in text
    CACHE = original

    print("selftest: OK (4 Gruppen)")
    return 0


# ======================================================================
# main
# ======================================================================

def main() -> int:
    ap = argparse.ArgumentParser(description="Design-Varianten-Werkbank")
    ap.add_argument("--liste", action="store_true", help="Register + Messstand zeigen")
    ap.add_argument("--lauf", metavar="ID|alle",
                    help="bauen + statisch messen (Basis läuft immer mit)")
    ap.add_argument("--vergleich", action="store_true",
                    help=f"Report schreiben ({REPORT.name})")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return _selftest()

    register = lade_register()

    if args.liste:
        liste(register)
        return 0

    if args.lauf:
        regelwerk = lade_regelwerk()
        alle = [str(e.get("id")) for e in (register.get("varianten") or [])]
        if args.lauf == "alle":
            ids = alle
        else:
            # Die Basis läuft immer mit: ein Vergleich ohne Kontrollgruppe
            # ist keine Messung, sondern eine Behauptung.
            ids = ["basis", args.lauf] if args.lauf != "basis" else ["basis"]
        code = lauf(ids, register, regelwerk)
        REPORT.write_text(vergleich(register), encoding="utf-8")
        print(f"\nReport: {REPORT.relative_to(ROOT)}")
        return code

    if args.vergleich:
        REPORT.write_text(vergleich(register), encoding="utf-8")
        print(f"Report geschrieben: {REPORT.relative_to(ROOT)}")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
