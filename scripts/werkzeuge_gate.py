#!/usr/bin/env python3
"""Produktvertrag für Franks Werkzeuge (eigenständige Finanz-Rechner).

Die acht Werkzeuge unter /werkzeuge/ sind der zweite Produktkern des Blogs
neben dem Fixkosten-Cockpit. Ihr Wert hängt an Eigenschaften, die man einer
Seite nicht ansieht und die beim nächsten Umbau still verschwinden könnten:
vollständige Nutzbarkeit ohne Affiliate-Klick, Rechnen ohne Datenabfluss,
offengelegte Formeln und Quellen. Dieses Gate macht aus diesen Zusagen
überprüfbare Regeln – vor dem Hugo-Build gegen die Quelle, danach gegen die
veröffentlichte Wahrheit.

Aufruf:
  python3 scripts/werkzeuge_gate.py --source-only
  python3 scripts/werkzeuge_gate.py --public public
  python3 scripts/werkzeuge_gate.py --selftest

W1 VERSPRECHEN   Der Vertrauenssatz steht wörtlich auf dem Hub und auf jeder
                 Werkzeugseite – im Markup und maschinenlesbar im Schema.
W2 VOLLSTÄNDIG   Zu jedem Werkzeug der SSOT existiert genau eine Seite und
                 umgekehrt; der Hub verlinkt alle acht.
W3 WERBEFREI     Unter /werkzeuge/ gibt es keinen Partnerlink – weder /go/,
                 noch rel=sponsored, noch eine Partner-Domain.
W4 VERDRAHTUNG   Jede Seite bindet {{< werkzeug >}} ein; Frontmatter-ID,
                 Ordner-Slug und gerendertes data-werkzeug stimmen überein.
W5 NACHVOLLZIEHBAR  Formel, Annahmen und mindestens eine Quelle mit Stand
                 werden auf jeder Werkzeugseite tatsächlich gerendert.
W6 LOKAL         Kein form action, kein Netzpfad im Rechenkern, kein externes
                 Asset – die Rechnung verlässt den Browser nicht.
W7 OFFEN         Die Methodik steht sichtbar auf der Seite, nicht in einem
                 zugeklappten <details> und nicht hinter einem Klick.

Das Gate repariert nie selbst. Ein Defekt stoppt den Deploy, statt das
Versprechen still abzuschwächen.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from html import unescape
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "werkzeuge.yaml"
KOMPASS_FILE = ROOT / "data" / "fixkosten_kompass.yaml"
ZIELE_FILE = ROOT / "data" / "affiliate_ziele.yaml"
CONTENT_DIR = ROOT / "content" / "werkzeuge"
PARTIAL = ROOT / "layouts" / "_partials" / "ff_werkzeug.html"
DATA_PARTIAL = ROOT / "layouts" / "_partials" / "werkzeuge_data.html"
SHORTCODE = ROOT / "layouts" / "shortcodes" / "werkzeug.html"
SINGLE = ROOT / "layouts" / "werkzeuge" / "single.html"
LIST = ROOT / "layouts" / "werkzeuge" / "list.html"
JS_FILE = ROOT / "static" / "premium" / "ff-werkzeuge.js"
CSS_FILE = ROOT / "assets" / "css" / "extended" / "zz-werkzeuge.css"
HUGO_CONFIG = ROOT / "hugo.toml"

# Der Satz ist das Produktversprechen. Er steht hier wörtlich, damit eine
# „kleine Umformulierung" in der YAML nicht unbemerkt durchrutscht.
VERSPRECHEN = "Du kannst das Tool vollständig nutzen, ohne einen Affiliate-Link anzuklicken."
ANZAHL_WERKZEUGE = 8
ERLAUBTE_TYPEN = {"euro", "zahl", "prozent", "datum", "auswahl"}
ERLAUBTE_BUCKETS = {"einnahme", "bedarf", "wunsch", "sparen"}
PFLICHT_EXPORTE = {"csv", "pdf"}


# ---------------------------------------------------------------- Werkzeuge


def read_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"{path.name} nicht lesbar: {exc}") from exc


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def read_source(path: Path, findings: list[str], label: str) -> str:
    if not path.is_file():
        findings.append(f"W4: {label} fehlt: {path.name}")
        return ""
    return path.read_text(encoding="utf-8")


def frontmatter(text: str) -> dict[str, Any]:
    """Liest den YAML-Frontmatter einer Markdown-Datei (ohne Hugo)."""
    if not text.startswith("---"):
        return {}
    ende = text.find("\n---", 3)
    if ende < 0:
        return {}
    try:
        daten = yaml.safe_load(text[3:ende])
    except yaml.YAMLError:
        return {}
    return daten if isinstance(daten, dict) else {}


def partner_domains(root: Path = ROOT) -> set[str]:
    """Partner-Domains aus der Affiliate-SSOT – keine zweite Liste hier."""
    pfad = root / "data" / "affiliate_ziele.yaml"
    if not pfad.is_file():
        return set()
    try:
        daten = yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return set()
    domains: set[str] = set()
    for ziel in (daten.get("ziele") or {}).values():
        if not isinstance(ziel, dict):
            continue
        landing = str(ziel.get("landing") or "")
        treffer = re.match(r"([a-z0-9][a-z0-9.\-]*\.[a-z]{2,})", landing.strip().lower())
        if treffer:
            domains.add(treffer.group(1))
    return domains


# ---------------------------------------------------------------- W1–W6 Quelle


def validate_data(data: Any, root: Path = ROOT) -> list[str]:
    """Datenvertrag der SSOT data/werkzeuge.yaml."""
    findings: list[str] = []
    if not isinstance(data, dict):
        return ["W2: data/werkzeuge.yaml ist kein YAML-Objekt"]

    for key in ("version", "name", "hub_titel", "hub_kicker", "positionierung",
                "versprechen", "vertrauen", "export", "werkzeuge"):
        if key not in data:
            findings.append(f"W2: Pflichtfeld {key!r} fehlt in data/werkzeuge.yaml")

    if data.get("versprechen") != VERSPRECHEN:
        findings.append(f"W1: Das Versprechen muss wörtlich lauten: {VERSPRECHEN!r}")

    vertrauen = data.get("vertrauen")
    if not isinstance(vertrauen, dict):
        findings.append("W1: 'vertrauen' fehlt oder ist kein Objekt")
    else:
        for key in ("ueberschrift", "speicher_hinweis", "export_hinweis"):
            if not nonempty(vertrauen.get(key)):
                findings.append(f"W1: vertrauen.{key} braucht einen Text")
        punkte = vertrauen.get("punkte")
        if not isinstance(punkte, list) or len(punkte) < 4:
            findings.append("W1: Der Vertrauensblock braucht mindestens vier Punkte")
        else:
            for i, punkt in enumerate(punkte, 1):
                if not isinstance(punkt, dict) or not all(nonempty(punkt.get(k)) for k in ("id", "titel", "text")):
                    findings.append(f"W1: Vertrauenspunkt {i} braucht id, titel und text")

    export = data.get("export")
    formate: set[str] = set()
    if not isinstance(export, dict):
        findings.append("W2: 'export' fehlt oder ist kein Objekt")
    else:
        if not nonempty(export.get("dateipraefix")):
            findings.append("W2: export.dateipraefix fehlt")
        for eintrag in export.get("formate") or []:
            if not isinstance(eintrag, dict) or not all(nonempty(eintrag.get(k)) for k in ("id", "label", "beschreibung")):
                findings.append("W2: Jedes Exportformat braucht id, label und beschreibung")
                continue
            formate.add(eintrag["id"])
        if not PFLICHT_EXPORTE <= formate:
            findings.append(f"W2: Die Formate {sorted(PFLICHT_EXPORTE)} sind Pflicht, gefunden: {sorted(formate)}")

    kompass_ids: set[str] = set()
    kompass_datei = root / "data" / "fixkosten_kompass.yaml"
    if kompass_datei.is_file():
        try:
            kompass = yaml.safe_load(kompass_datei.read_text(encoding="utf-8")) or {}
            kompass_ids = {s.get("id") for s in kompass.get("stages", []) if isinstance(s, dict)}
        except yaml.YAMLError:
            kompass_ids = set()

    werkzeuge = data.get("werkzeuge")
    if not isinstance(werkzeuge, list) or len(werkzeuge) != ANZAHL_WERKZEUGE:
        findings.append(f"W2: Es müssen genau {ANZAHL_WERKZEUGE} Werkzeuge beschrieben sein")
        werkzeuge = werkzeuge if isinstance(werkzeuge, list) else []

    gesehen_ids: set[str] = set()
    gesehen_slugs: set[str] = set()
    for index, w in enumerate(werkzeuge, 1):
        if not isinstance(w, dict):
            findings.append(f"W2: Werkzeug {index} ist kein Objekt")
            continue
        name = w.get("id") or f"#{index}"
        for key in ("id", "slug", "engine", "name", "kurz", "icon", "kompass",
                    "pillar", "pillar_label", "faq_hinweis"):
            if not nonempty(w.get(key)):
                findings.append(f"W2: Werkzeug {name!r} braucht {key!r}")
        if w.get("id") in gesehen_ids:
            findings.append(f"W2: Doppelte Werkzeug-ID {w.get('id')!r}")
        gesehen_ids.add(w.get("id"))
        if w.get("slug") in gesehen_slugs:
            findings.append(f"W2: Doppelter Slug {w.get('slug')!r}")
        gesehen_slugs.add(w.get("slug"))
        if not isinstance(w.get("speicher"), bool):
            findings.append(f"W2: Werkzeug {name!r} braucht speicher: true|false")
        if kompass_ids and w.get("kompass") not in kompass_ids:
            findings.append(f"W2: Werkzeug {name!r} nennt den unbekannten 4K-Schritt {w.get('kompass')!r}")

        exporte = w.get("exporte")
        if not isinstance(exporte, list) or not exporte:
            findings.append(f"W2: Werkzeug {name!r} braucht mindestens ein Exportformat")
        elif formate and not set(exporte) <= formate:
            findings.append(f"W2: Werkzeug {name!r} nennt unbekannte Exportformate: {sorted(set(exporte) - formate)}")

        felder = w.get("felder")
        if not isinstance(felder, list) or not felder:
            findings.append(f"W2: Werkzeug {name!r} hat keine Felder")
            felder = []
        feld_ids: set[str] = set()
        for feld in felder:
            if not isinstance(feld, dict):
                findings.append(f"W2: Werkzeug {name!r} hat ein Feld ohne Struktur")
                continue
            for key in ("id", "label", "typ", "hilfe"):
                if not nonempty(feld.get(key)):
                    findings.append(f"W2: Feld in {name!r} braucht {key!r}")
            if feld.get("id") in feld_ids:
                findings.append(f"W2: Werkzeug {name!r} hat die doppelte Feld-ID {feld.get('id')!r}")
            feld_ids.add(feld.get("id"))
            if feld.get("typ") not in ERLAUBTE_TYPEN:
                findings.append(f"W2: Feld {feld.get('id')!r} in {name!r} nutzt den unbekannten Typ {feld.get('typ')!r}")
            if feld.get("typ") == "auswahl":
                optionen = feld.get("optionen")
                if not isinstance(optionen, list) or len(optionen) < 2:
                    findings.append(f"W2: Auswahlfeld {feld.get('id')!r} in {name!r} braucht mindestens zwei Optionen")
                else:
                    for option in optionen:
                        if not isinstance(option, dict) or not all(nonempty(option.get(k)) for k in ("wert", "label")):
                            findings.append(f"W2: Option in {feld.get('id')!r} ({name!r}) braucht wert und label")
            if feld.get("bucket") is not None and feld.get("bucket") not in ERLAUBTE_BUCKETS:
                findings.append(f"W2: Feld {feld.get('id')!r} in {name!r} hat den unbekannten bucket {feld.get('bucket')!r}")
            korridor = feld.get("sparkorridor")
            if korridor is not None:
                if (not isinstance(korridor, list) or len(korridor) != 2
                        or not all(isinstance(v, (int, float)) for v in korridor)
                        or not 0 <= korridor[0] <= korridor[1] <= 1):
                    findings.append(f"W2: sparkorridor von {feld.get('id')!r} ({name!r}) muss [min, max] zwischen 0 und 1 sein")

        # W5 beginnt in der Quelle: ohne Formel und Quelle darf es kein Werkzeug geben.
        formel = w.get("formel")
        if not isinstance(formel, list) or len(formel) < 2:
            findings.append(f"W5: Werkzeug {name!r} braucht mindestens zwei Formelschritte")
        annahmen = w.get("annahmen")
        if not isinstance(annahmen, list) or not annahmen:
            findings.append(f"W5: Werkzeug {name!r} braucht mindestens eine Annahme")
        quellen = w.get("quellen")
        if not isinstance(quellen, list) or not quellen:
            findings.append(f"W5: Werkzeug {name!r} braucht mindestens eine Quelle")
        else:
            for quelle in quellen:
                if not isinstance(quelle, dict) or not all(nonempty(quelle.get(k)) for k in ("titel", "herausgeber", "url", "stand")):
                    findings.append(f"W5: Quelle in {name!r} braucht titel, herausgeber, url und stand")
                    continue
                if not quelle["url"].startswith("https://"):
                    findings.append(f"W5: Quelle {quelle['titel']!r} in {name!r} braucht eine https-URL")
                if not re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", str(quelle["stand"])):
                    findings.append(f"W5: Quelle {quelle['titel']!r} in {name!r} braucht einen Stand als JJJJ-MM")

        pillar = w.get("pillar")
        if nonempty(pillar):
            seite = root / "content" / "pillar" / pillar / "index.md"
            if not seite.is_file():
                findings.append(f"W2: Werkzeug {name!r} zeigt auf den fehlenden Pillar {pillar!r}")
            elif re.search(r"(?m)^draft:\s*true\s*$", seite.read_text(encoding="utf-8")):
                findings.append(f"W2: Werkzeug {name!r} zeigt auf einen Entwurf: {pillar!r}")
    return findings


def validate_content(data: dict[str, Any], root: Path = ROOT) -> list[str]:
    """W2/W4: Seiten und SSOT dürfen nicht auseinanderlaufen."""
    findings: list[str] = []
    content = root / "content" / "werkzeuge"
    if not (content / "_index.md").is_file():
        findings.append("W2: content/werkzeuge/_index.md (Hub-Seite) fehlt")

    werkzeuge = [w for w in (data.get("werkzeuge") or []) if isinstance(w, dict)]
    erwartet = {w.get("slug"): w for w in werkzeuge}
    gefunden: set[str] = set()

    for seite in sorted(content.glob("*/index.md")) if content.is_dir() else []:
        slug = seite.parent.name
        gefunden.add(slug)
        text = seite.read_text(encoding="utf-8")
        fm = frontmatter(text)
        w = erwartet.get(slug)
        if w is None:
            findings.append(f"W2: Seite /werkzeuge/{slug}/ hat kein Werkzeug in data/werkzeuge.yaml")
            continue
        if fm.get("werkzeug") != w.get("id"):
            findings.append(
                f"W4: /werkzeuge/{slug}/ nennt werkzeug: {fm.get('werkzeug')!r}, erwartet {w.get('id')!r}")
        if fm.get("draft") is True:
            findings.append(f"W2: /werkzeuge/{slug}/ ist ein Entwurf – ein Werkzeug ohne Seite ist kein Werkzeug")
        if not nonempty(fm.get("description")):
            findings.append(f"W2: /werkzeuge/{slug}/ braucht eine description")
        if "{{< werkzeug >}}" not in text and "{{% werkzeug %}}" not in text:
            findings.append(f"W4: /werkzeuge/{slug}/ bindet den Shortcode {{{{< werkzeug >}}}} nicht ein")
        if re.search(r"\{\{<\s*werkzeug[^>]*>\}\}[\s\S]*\{\{<\s*werkzeug[^>]*>\}\}", text):
            findings.append(f"W4: /werkzeuge/{slug}/ bindet mehr als ein Werkzeug ein")
        if "/go/" in text:
            findings.append(f"W3: /werkzeuge/{slug}/ enthält einen Partnerlink im Quelltext")
        if not re.search(r"(?m)^###\s+.+\?\s*$", text):
            findings.append(f"W5: /werkzeuge/{slug}/ braucht einen FAQ-Abschnitt mit '### Frage?'")

    for slug in sorted(set(erwartet) - gefunden):
        findings.append(f"W2: Zum Werkzeug {slug!r} fehlt content/werkzeuge/{slug}/index.md")
    return findings


def validate_source(root: Path = ROOT) -> list[str]:
    findings: list[str] = []
    try:
        data = read_yaml(root / "data" / "werkzeuge.yaml")
    except ValueError as exc:
        return [str(exc)]
    findings.extend(validate_data(data, root))
    findings.extend(validate_content(data if isinstance(data, dict) else {}, root))

    partial = read_source(root / "layouts" / "_partials" / "ff_werkzeug.html", findings, "Werkzeug-Partial")
    data_partial = read_source(root / "layouts" / "_partials" / "werkzeuge_data.html", findings, "Daten-Partial")
    shortcode = read_source(root / "layouts" / "shortcodes" / "werkzeug.html", findings, "Shortcode")
    single = read_source(root / "layouts" / "werkzeuge" / "single.html", findings, "Werkzeug-Template")
    liste = read_source(root / "layouts" / "werkzeuge" / "list.html", findings, "Hub-Template")
    script = read_source(root / "static" / "premium" / "ff-werkzeuge.js", findings, "Rechenkern")
    css = read_source(root / "assets" / "css" / "extended" / "zz-werkzeuge.css", findings, "Werkzeug-CSS")
    config = read_source(root / "hugo.toml", findings, "Hugo-Konfiguration")

    if partial:
        for marker in ("data-ff-werkzeug", "data-ff-wz-formel", "data-ff-wz-annahme",
                       "data-ff-wz-quelle", "data-ff-wz-ausgabe", "ff-werkzeuge.js",
                       "$daten.versprechen", "<noscript>"):
            if marker not in partial:
                findings.append(f"W4: Werkzeug-Partial enthält {marker!r} nicht")
        if re.search(r"<form\b[^>]*\baction\s*=", partial, re.I):
            findings.append("W6: Das Werkzeug-Formular darf kein action-Attribut besitzen")
        if re.search(r"(?:src|href)\s*=\s*[\"']https?://", partial):
            # Quellen-Links stehen als {{ .url }} im Markup – eine fest
            # verdrahtete externe URL wäre dagegen ein fremdes Asset.
            findings.append("W6: Werkzeug-Partial lädt eine fest verdrahtete externe Ressource")
        if "<details" in partial:
            findings.append("W7: Die Methodik darf nicht in einem <details> versteckt werden")
    if data_partial and not all(m in data_partial for m in ("os.ReadFile", "data/werkzeuge.yaml", "transform.Unmarshal", "errorf")):
        findings.append("W4: Daten-Partial lädt die SSOT nicht gezielt oder scheitert nicht laut")
    if shortcode and "ff_werkzeug.html" not in shortcode:
        findings.append("W4: Der Shortcode ruft das Werkzeug-Partial nicht auf")
    if single:
        if "SoftwareApplication" not in single:
            findings.append("W1: Die Werkzeugseite braucht ein SoftwareApplication-Schema")
        if "$daten.versprechen" not in single:
            findings.append("W1: Die Werkzeugseite muss das Versprechen aus der SSOT ausgeben")
    if liste and "$daten.versprechen" not in liste:
        findings.append("W1: Der Hub muss das Versprechen aus der SSOT ausgeben")
    if css and ':root[data-theme="dark"]' not in css:
        findings.append("W4: Das Werkzeug-CSS braucht eine Dark-Mode-Variante")
    if config and not re.search(r'identifier\s*=\s*"werkzeuge"[\s\S]{0,160}url\s*=\s*"/werkzeuge/"', config):
        findings.append("W2: Die Hauptnavigation verlinkt /werkzeuge/ nicht – die Seiten wären Waisen")

    if script:
        # Der Kopfkommentar benennt die verbotenen Muster; geprüft wird der Code.
        start = script.find("(function ()")
        code = script[start:] if start > 0 else script
        verboten = {
            r"\bfetch\s*\(": "fetch",
            r"\bXMLHttpRequest\b": "XMLHttpRequest",
            r"\bsendBeacon\b": "sendBeacon",
            r"\bWebSocket\b": "WebSocket",
            r"\.innerHTML\s*=": "innerHTML-Zuweisung",
            r"document\.cookie": "Cookie-Zugriff",
            r"https?://(?!www\.w3\.org)": "externe URL",
        }
        for muster, label in verboten.items():
            if re.search(muster, code):
                findings.append(f"W6: Der Rechenkern darf keinen {label}-Pfad enthalten")
        for marker in ("ff_werkzeug_", "FFWerkzeuge", "merken.checked", "speicherLoeschen"):
            if marker not in code:
                findings.append(f"W6: Opt-in-/Testvertrag im Rechenkern fehlt: {marker!r}")
        fehlende = [w.get("engine") for w in (data.get("werkzeuge") or [])
                    if isinstance(w, dict) and nonempty(w.get("engine"))
                    and f"logik.{w['engine']} =" not in code]
        for engine in fehlende:
            findings.append(f"W4: Der Rechenkern kennt die Engine {engine!r} nicht")
    return findings


# ---------------------------------------------------------------- W1–W7 Build


def public_path(public: Path, url: str, base_path: str = "/") -> Path | None:
    base = "/" + base_path.strip("/") + "/" if base_path.strip("/") else "/"
    if not url.startswith(base):
        return None
    rest = url[len(base):].split("?", 1)[0].split("#", 1)[0].strip("/")
    kandidat = (public / rest / "index.html").resolve()
    try:
        kandidat.relative_to(public.resolve())
    except ValueError:
        return None
    return kandidat


def partnerlinks(html: str, domains: set[str]) -> list[str]:
    """W3: Jede Form von Partnerverweis – Weiterleitung, rel oder Domain."""
    treffer: list[str] = []
    if re.search(r"""href\s*=\s*["']?[^"'>\s]*/go/""", html):
        treffer.append("/go/-Weiterleitung")
    if re.search(r"""rel\s*=\s*["'][^"']*\bsponsored\b""", html, re.I):
        treffer.append('rel="sponsored"')
    for domain in sorted(domains):
        if re.search(r"https?://[^\s\"'<>]*" + re.escape(domain), html, re.I):
            treffer.append(f"Partner-Domain {domain}")
    return treffer


def validate_build(public: Path, data: dict[str, Any], base_path: str = "/",
                   root: Path = ROOT) -> list[str]:
    findings: list[str] = []
    praefix = base_path.rstrip("/") or ""
    hub_datei = public_path(public, praefix + "/werkzeuge/", base_path)
    if not hub_datei or not hub_datei.is_file():
        return ["W2: Der gebaute Hub /werkzeuge/ fehlt"]

    domains = partner_domains(root)
    hub = hub_datei.read_text(encoding="utf-8")
    hub_text = unescape(hub)
    if VERSPRECHEN not in hub_text:
        findings.append("W1: Der Hub /werkzeuge/ nennt das Versprechen nicht wörtlich")
    for fund in partnerlinks(hub, domains):
        findings.append(f"W3: Der Hub /werkzeuge/ enthält einen Partnerlink ({fund})")

    werkzeuge = [w for w in (data.get("werkzeuge") or []) if isinstance(w, dict)]
    for w in werkzeuge:
        slug, wid, name = w.get("slug"), w.get("id"), w.get("name")
        url = f"{praefix}/werkzeuge/{slug}/"
        if not re.search(r"""href=["']?[^"'>\s]*/werkzeuge/""" + re.escape(str(slug)) + "/", hub):
            findings.append(f"W2: Der Hub verlinkt {name!r} nicht")

        datei = public_path(public, url, base_path)
        if not datei or not datei.is_file():
            findings.append(f"W2: Die gebaute Seite {url} fehlt")
            continue
        html = datei.read_text(encoding="utf-8")
        text = unescape(html)

        if VERSPRECHEN not in text:
            findings.append(f"W1: {url} nennt das Versprechen nicht wörtlich")
        if '"isAccessibleForFree":true' not in html.replace(" ", "") or "SoftwareApplication" not in html:
            findings.append(f"W1: {url} liefert kein SoftwareApplication-Schema mit kostenfreier Nutzung")

        for fund in partnerlinks(html, domains):
            findings.append(f"W3: {url} enthält einen Partnerlink ({fund})")

        anzahl = len(re.findall(r"\bdata-ff-werkzeug\b", html))
        if anzahl != 1:
            findings.append(f"W4: {url} enthält {anzahl} Werkzeug-Komponenten, erwartet genau eine")
        if f'data-werkzeug="{wid}"' not in html and f"data-werkzeug={wid}" not in html:
            findings.append(f"W4: {url} rendert nicht das Werkzeug {wid!r}")
        if f'data-engine="{w.get("engine")}"' not in html and f'data-engine={w.get("engine")}' not in html:
            findings.append(f"W4: {url} nennt die Engine {w.get('engine')!r} nicht")
        if "premium/ff-werkzeuge.js" not in html:
            findings.append(f"W6: {url} bindet den lokalen Rechenkern nicht ein")

        if re.search(r"<form\b[^>]*\baction\s*=", html, re.I):
            findings.append(f"W6: {url} besitzt ein Formular mit action-Attribut")
        for muster, label in ((r"<script[^>]+src=[\"']?https?://", "externes Skript"),
                              (r"<link[^>]+href=[\"']?https?://[^\"'>]+\.css", "externes Stylesheet"),
                              (r"<iframe", "iframe")):
            if re.search(muster, html, re.I):
                findings.append(f"W6: {url} lädt {label}")

        for marker, regel, label in (("data-ff-wz-formel", "W5", "Formel"),
                                     ("data-ff-wz-annahme", "W5", "Annahmen"),
                                     ("data-ff-wz-quelle", "W5", "Quelle")):
            if marker not in html:
                findings.append(f"{regel}: {url} rendert keine {label}")
        formel_block = re.search(r"data-ff-wz-formel[^>]*>(.*?)</ol>", html, re.S)
        if formel_block and len(re.findall(r"<li", formel_block.group(1))) < 2:
            findings.append(f"W5: {url} zeigt weniger als zwei Formelschritte")
        for quelle in w.get("quellen") or []:
            if isinstance(quelle, dict) and nonempty(quelle.get("url")) and quelle["url"] not in text:
                findings.append(f"W5: {url} verlinkt die Quelle {quelle.get('titel')!r} nicht")

        if "<details" in html:
            findings.append(f"W7: {url} versteckt Inhalte in einem <details>")
        methodik = html.find("data-ff-wz-formel")
        formular = html.find("<form")
        if methodik < 0 or (formular >= 0 and methodik < formular):
            findings.append(f"W7: {url} zeigt die Methodik nicht unterhalb des Werkzeugs")
        if "<noscript" not in html:
            findings.append(f"W7: {url} braucht einen noscript-Hinweis für Besucher ohne JavaScript")

    return findings


# ---------------------------------------------------------------- Selbsttest


def selftest(root: Path = ROOT) -> list[str]:
    """Sabotageproben gegen die Kernregeln – es wird nichts verändert."""
    fehler: list[str] = []
    try:
        data = read_yaml(root / "data" / "werkzeuge.yaml")
    except ValueError as exc:
        return [f"Selbsttest kann die SSOT nicht laden: {exc}"]

    if validate_data(data, root):
        fehler.append("Positivprobe der SSOT ist nicht grün")

    proben: list[tuple[str, Any]] = []

    kaputt = copy.deepcopy(data)
    kaputt["versprechen"] = "Du kannst das Tool weitgehend nutzen."
    proben.append(("abgeschwächtes Versprechen", kaputt))

    kaputt = copy.deepcopy(data)
    kaputt["werkzeuge"].pop()
    proben.append(("fehlendes Werkzeug", kaputt))

    kaputt = copy.deepcopy(data)
    kaputt["werkzeuge"][0]["quellen"] = []
    proben.append(("Werkzeug ohne Quelle", kaputt))

    kaputt = copy.deepcopy(data)
    kaputt["werkzeuge"][0]["formel"] = ["nur ein Schritt"]
    proben.append(("Werkzeug ohne nachvollziehbare Formel", kaputt))

    kaputt = copy.deepcopy(data)
    kaputt["werkzeuge"][1]["slug"] = kaputt["werkzeuge"][0]["slug"]
    proben.append(("doppelter Slug", kaputt))

    kaputt = copy.deepcopy(data)
    kaputt["werkzeuge"][0]["felder"][0]["typ"] = "zauberei"
    proben.append(("unbekannter Feldtyp", kaputt))

    kaputt = copy.deepcopy(data)
    kaputt["werkzeuge"][0]["pillar"] = "gibt-es-nicht"
    proben.append(("totes Pillar-Ziel", kaputt))

    kaputt = copy.deepcopy(data)
    kaputt["vertrauen"]["punkte"] = kaputt["vertrauen"]["punkte"][:2]
    proben.append(("ausgedünnter Vertrauensblock", kaputt))

    for label, probe in proben:
        if not validate_data(probe, root):
            fehler.append(f"Selbsttest: {label} wurde nicht erkannt")

    # W3-Erkennung muss jede Spielart finden.
    domains = partner_domains(root) or {"check24.net"}
    beispiel = next(iter(sorted(domains)))
    for html, label in (
        ('<a href="/go/strom/?subid=x">Jetzt vergleichen</a>', "/go/-Link"),
        ('<a href="https://example.test/x" rel="sponsored nofollow">Angebot</a>', "rel=sponsored"),
        (f'<a href="https://{beispiel}/dsl/">Tarife</a>', "Partner-Domain"),
    ):
        if not partnerlinks(html, domains):
            fehler.append(f"Selbsttest: {label} wurde nicht als Partnerlink erkannt")
    if partnerlinks('<a href="/werkzeuge/notgroschen-rechner/">Rechner</a>', domains):
        fehler.append("Selbsttest: interner Link wurde fälschlich als Partnerlink gewertet")

    if public_path(Path("/tmp/public"), "/werkzeuge/notgroschen-rechner/") != Path("/tmp/public/werkzeuge/notgroschen-rechner/index.html"):
        fehler.append("Selbsttest: sichere Public-Pfad-Auflösung ist defekt")
    if public_path(Path("/tmp/public"), "/werkzeuge/../../etc/") is not None:
        fehler.append("Selbsttest: Pfadausbruch wurde nicht verhindert")
    if frontmatter("---\nwerkzeug: notgroschen\n---\nText").get("werkzeug") != "notgroschen":
        fehler.append("Selbsttest: Frontmatter-Leser ist defekt")
    return fehler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-only", action="store_true", help="nur W1–W6 gegen den Quellbaum")
    parser.add_argument("--public", type=Path, help="zusätzlich W1–W7 gegen das Hugo-Ausgabeverzeichnis")
    parser.add_argument("--base-path", default="/", help="Basis-Pfad eines Subdirectory-Builds")
    parser.add_argument("--selftest", action="store_true", help="Sabotageproben ausführen")
    parser.add_argument("--json", action="store_true", help="Befunde als JSON ausgeben")
    args = parser.parse_args(argv)

    findings: list[str] = []
    if args.selftest:
        findings.extend("SELFTEST: " + item for item in selftest())
    if not args.selftest or args.source_only or args.public:
        findings.extend(validate_source())
    if args.public:
        try:
            data = read_yaml(DATA_FILE)
        except ValueError as exc:
            findings.append(str(exc))
        else:
            findings.extend(validate_build(args.public, data, args.base_path))

    if args.json:
        print(json.dumps({"ok": not findings, "findings": findings}, ensure_ascii=False, indent=2))
    elif findings:
        print("🛑 WERKZEUGE-GATE: Befunde")
        for finding in findings:
            print("  - " + finding)
    else:
        umfang = "Selbsttest + Quelle" if args.selftest else "Quelle"
        if args.public:
            umfang += " + Build"
        print(f"✅ WERKZEUGE-GATE bestanden ({umfang}).")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
