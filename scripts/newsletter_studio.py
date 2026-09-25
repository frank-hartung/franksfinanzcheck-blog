#!/usr/bin/env python3
"""newsletter_studio.py – E-Mail-Studio des Newsletters: Marke, Blöcke, Betreff, Layout.

WARUM (Auftrag 22.09.2026: „Newsletter auf Agentur-Niveau, aber kostenlos“)
----------------------------------------------------------------------------
Kommerzielle Newsletter-Plattformen (Migma & Co.) verkaufen vier Dinge:
sie ziehen die MARKE ein, bauen TEXT und LAYOUT daraus, prüfen vor dem
Versand (Rendering, Links, Ton) und exportieren zum Versanddienst. Genau
diese vier Schichten liegen hier als eigener, kostenloser Code im Repo –
bestimmt durch Daten, nicht durch ein Abo:

  MARKE      design/-Block aus data/newsletter_studio.json, gespiegelt aus
             DESIGN.md §1. `--brand` beweist, dass die Werte exakt in
             assets/css/extended/custom.css stehen (Drift = Befund).
  TEXT       deterministische Bausteine: Betreff-Varianten (3 Stück, Länge
             als Gate), Preheader, Eröffnung, Zahlen-Hero. Kein KI-Aufruf –
             damit die Funktion dauerhaft 0 € kostet und reproduzierbar ist.
  LAYOUT     Table-basiertes E-Mail-HTML (620 px, Outlook-sicherer
             Bulletproof-Button, Dark-Mode-Block, preheader), gebaut aus
             Blöcken – jedes E-Mail ist dieselbe Hierarchie, kein HTML-Schnitzel.
  EXPORT     `--build` liefert html/text/betreff/preheader an
             scripts/newsletter_digest.py, das vor dem Versand die QA-Wache
             (scripts/newsletter_qa.py) durchlässt.

BELEG-PFLICHT: Die Hero-Zahl („bis zu 240 €“) wird nicht erfunden, sondern
aus dem Kurzantwort-/Description-Text des Tages gehoben und als `beleg`
mitgeführt; die QA-Wache verlangt, dass die Zahl dort wirklich steht.

Nur Standardbibliothek – der Versand-Workflow installiert bewusst nichts nach.

Nutzung:
    python3 scripts/newsletter_studio.py --brand
    python3 scripts/newsletter_studio.py --build --days 1 [--out DIR] [--json]
    python3 scripts/newsletter_studio.py --vorschau --out DIR
    python3 scripts/newsletter_studio.py --selftest

Exit: 0 = ok · 1 = Befund · 2 = Fehler
"""
from __future__ import annotations

import argparse
import datetime
import glob
import html as _html
import json
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Der Versandvertrag (Dienstag/Freitag, nächster Termin, deutsche Wochentagsnamen
# ohne Locale-Falle) liegt in einer eigenen Datei: Website, Wache und Doku lesen
# dieselbe Stelle. Kein Zirkel – newsletter_schedule importiert nichts von hier.
import newsletter_schedule as plan                        # noqa: E402
KONFIG_REL = os.path.join("data", "newsletter_studio.json")
CUSTOM_CSS_REL = os.path.join("assets", "css", "extended", "custom.css")
THEMENWELTEN_REL = os.path.join("data", "themenwelten.json")
GRUND_URL = "https://franksfinanzcheck.de"

# Rollen, die im Design-Block vorkommen müssen – die QA-Wache misst die
# Pflichtpaare aus design.kontraste, hier wird nur die Vollständigkeit geprüft.
PFLICHT_ROLLEN = ("seite", "karte", "grenze", "text", "sekundaer", "headline",
                  "link", "cta_flaeche", "cta_text", "akzent_auf_marke", "soft")


# ------------------------------------------------------------------ Grundbausteine
def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def _doku_bereinigen(wert):
    """`_doku`-Schlüssel entfernen: sie erklären die Datei dem Menschen und
    müssen keinem Konsumenten im Weg stehen (Hugo, Studio, QA)."""
    if isinstance(wert, dict):
        return {k: _doku_bereinigen(v) for k, v in wert.items() if not k.startswith("_doku")}
    if isinstance(wert, list):
        return [_doku_bereinigen(v) for v in wert]
    return wert


def konfiguration(root: str = BLOG_DIR, *, streng: bool = True) -> dict:
    """Die Studio-Konfiguration (data/newsletter_studio.json), mit hugo.toml-Überschreibung.

    Präzedenz wie im Shortcode: ein Wert in `hugo.toml` `params.newsletter*`
    gewinnt, sonst gilt die JSON. Eine Regel, zwei Orte, dieselbe Reihenfolge –
    sonst melden Website und Wache verschiedene Zustände.

    `streng=False` für Prüfer, die nur den Capture-Block brauchen
    (newsletter_digest `--check`): fehlt die Datei, gilt ausschließlich
    hugo.toml, statt den Lauf abzublasen – die Wache meldet den Zustand ohnehin.
    """
    pfad = os.path.join(root, KONFIG_REL)
    roh = _read(pfad)
    if not roh.strip():
        if streng:
            raise SystemExit(f"❌ newsletter_studio: {KONFIG_REL} fehlt – ohne Studio-Konfiguration "
                             "gibt es kein E-Mail-Layout und keinen Anmeldeweg.")
        konf = {}
    else:
        try:
            konf = json.loads(roh)
        except json.JSONDecodeError as exc:
            # Ein kaputtes JSON ist kein „Leerzustand“, sondern ein Fehler: wer
            # hier still auf Codewerte fiele, verschicke im ungünstigsten Fall
            # ein Mail ohne eigene Marke. `streng` ändert daran nichts.
            raise SystemExit(f"❌ newsletter_studio: {KONFIG_REL} ist kein gültiges JSON: {exc}")
    konf = _doku_bereinigen(konf)
    # hugo.toml-Insel (kein Hugo-Build nötig, dieselbe Technik wie der Digest)
    toml = _read(os.path.join(root, "hugo.toml"))
    ueber = {}
    for schlussel, parameter in (("form_action", "newsletterFormAction"),
                                  ("form_url", "newsletterFormUrl"),
                                  ("versprechen", "newsletterPromise")):
        m = re.search(r'(?m)^\s*' + parameter + r'\s*=\s*"([^"]*)"', toml)
        if m and m.group(1).strip():
            ueber[schlussel] = m.group(1).strip()
    konf.setdefault("capture", {}).update(ueber)
    return konf


def capture(root: str = BLOG_DIR) -> dict:
    c = konfiguration(root, streng=False).get("capture", {})
    return {
        "form_action": (c.get("form_action") or "").strip(),
        "form_url": (c.get("form_url") or "").strip(),
        "versprechen": (c.get("versprechen") or "").strip(),
        # Die Feldnamen sind Teil des Vertrags mit dem Anbieter – die Wache N4
        # liest sie aus derselben Quelle wie das Template, statt sie zu kopieren.
        "feld_email": (c.get("feld_email") or "email").strip(),
        "feld_themen": (c.get("feld_themen") or "themen").strip(),
        "aktiv": bool((c.get("form_action") or "").strip() or (c.get("form_url") or "").strip()),
    }


def hex_zerlegen(farbe: str) -> tuple[int, int, int]:
    f = (farbe or "").strip().lstrip("#")
    if len(f) == 3:
        f = "".join(c * 2 for c in f)
    if len(f) != 6 or re.fullmatch(r"[0-9a-fA-F]{6}", f) is None:
        raise ValueError(f"keine hex-Farbe: {farbe!r}")
    return int(f[0:2], 16), int(f[2:4], 16), int(f[4:6], 16)


def kontrast(hinten: str, vorn: str) -> float:
    """WCAG 2.1 Kontrastverhältnis – gemessen statt geschätzt (DESIGN.md §8)."""
    def relatives_leuchten(rgb):
        out = []
        for c in rgb:
            s = c / 255
            out.append(s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4)
        r, g, b = out
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    l1, l2 = relatives_leuchten(hex_zerlegen(hinten)), relatives_leuchten(hex_zerlegen(vorn))
    oben, unten = max(l1, l2), min(l1, l2)
    return round((oben + 0.05) / (unten + 0.05), 2)


# -------------------------------------------------------------------------- Marke
CSS_EBENEN = (("hell", re.compile(r":root\s*\{(?P<b>[^}]*)\}", re.S)),
              ("dunkel", re.compile(r":root\[data-theme=[\"']?dark[\"']?\]\s*\{(?P<b>[^}]*)\}", re.S)))
THEME_VARS_REL = os.path.join("themes", "PaperMod", "assets", "css", "core", "theme-vars.css")


def _farbe_norm(wert: str) -> str:
    """`#0E5A43`, `rgb(14, 90, 67)` und 3-Stelligen auf `#rrggbb` (klein) bringen.

    → None, wenn der Wert kein Lösen kennt (var(), color-mix(), Keywords). Genau
    das ist der Grund, warum das Studio keine color-mix()-Werte übernehmen kann:
    E-Mail-Clients rechnen nicht.
    """
    v = (wert or "").strip().rstrip(";").strip()
    if not v or "color-mix" in v or "var(" in v or "calc(" in v:
        return None
    m = re.fullmatch(r"#([0-9a-fA-F]{6})", v)
    if m:
        return "#" + m.group(1).lower()
    m = re.fullmatch(r"#([0-9a-fA-F]{3})", v)
    if m:
        return "#" + "".join(c * 2 for c in m.group(1).lower())
    m = re.fullmatch(r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})[^)]*\)", v)
    if m:
        return "#" + "".join(f"{min(255, int(g)):02x}" for g in m.groups(0)[:3])
    return None


def css_tokens(root: str = BLOG_DIR) -> dict:
    """Die Farb-Tokens, die der Build wirklich benutzt – aufgelöst, nicht abgeschrieben.

    → {"hell": {"--ff-emerald": "#0e5a43", …}, "dunkel": {…}, "dateien": […]}
    Geladen werden assets/css/extended/*.css (alphabetisch, wie Hugo sie lädt –
    die spätere Datei gewinnt also) und PaperMods theme-vars.css als Basis.
    """
    quelle = {
        "hell": {"secondary": "#6c6c6c", "theme": "#ffffff", "entry": "#ffffff",
                 "primary": "#1e1e1e", "border": "#eeeeee"},
        "dunkel": {},
    }
    dateien = sorted(glob.glob(os.path.join(root, "assets", "css", "extended", "*.css")))
    basis = os.path.join(root, THEME_VARS_REL)
    if os.path.exists(basis):
        dateien.insert(0, basis)
    gefunde = {"hell": {}, "dunkel": {}}
    for pfad in dateien:
        text = _read(pfad)
        for modus, muster in CSS_EBENEN:
            for blk in muster.finditer(text):
                for m in re.finditer(r"(--[\w-]+)\s*:\s*([^;]+);", blk.group("b")):
                    name, roh = m.group(1), m.group(2)
                    norm = _farbe_norm(roh)
                    if norm:
                        gefunde[modus][name] = norm
                    elif "color-mix" in roh:
                        # color-mix() kann der E-Mail-Client nicht – als gemischt
                        # merken, damit die Herleitung nicht auf „fehlt" prallt,
                        # sondern den Konflikt benennen kann.
                        gefunde[modus].setdefault(name + ":gemischt", roh.strip())
    # Dark-Modus: was dort nicht steht, gilt aus dem Hell-Block (CSS-Kaskade)
    merged = dict(gefunde["hell"])
    merged.update(gefunde["dunkel"])
    return {"hell": gefunde["hell"], "dunkel": merged, "alle": gefunde,
            "dateien": [os.path.relpath(p, root) for p in dateien]}


def marken_abgleich(root: str = BLOG_DIR) -> tuple[list, list]:
    """Jede E-Mail-Farbe hat eine Herleitung – oder einen dokumentierten Grund.

    → (Funde, geprüfte Rollen). Gedacht ist das als Antwort auf die teure Sorte
    Fehler, die dieses Repo kennt: ein Studio, das eigene Farbwerte pflegt,
    driftet in drei Monaten von der Site ab und versendet ein Mail, das nach
    einem anderen Unternehmen aussieht. Deshalb: Token auflösen, vergleichen,
    und jede Rolle, die weder hergeleitet noch begründet ist, ist ein Befund.
    """
    design = konfiguration(root).get("design", {})
    token = css_tokens(root)
    funde: list = []
    herleitung = design.get("herleitung") or {}
    eigene = design.get("email_eigene") or {}
    if not token["hell"]:
        return ([f"keine CSS-Tokens lesbar ({', '.join(token['dateien'][:3])} …) – "
                 "Markenabgleich ausgefallen, nicht bestanden"], [])
    rollen = set()
    for modus in ("hell", "dunkel"):
        farben = design.get(modus) or {}
        rollen |= {f"{modus}.{r}" for r in farben}
        for rolle, wert in farben.items():
            schlussel = f"{modus}.{rolle}"
            norm = _farbe_norm(wert)
            if norm is None:
                funde.append(f"design.{schlussel} = {wert!r} ist kein hex/rgb-Wert")
                continue
            if schlussel in herleitung and schlussel in eigene:
                funde.append(f"{schlussel} ist gleichzeitig hergeleitet ({herleitung[schlussel]}) "
                             "und E-Mail-eigen – eine Rolle, eine Wahrheit")
                continue
            if schlussel in eigene:
                if not str(eigene[schlussel] or "").strip():
                    funde.append(f"{schlussel} ist als E-Mail-eigen deklariert, ohne Begründung "
                                 "– eine Ausrede ist keine Herleitung")
                continue
            if schlussel not in herleitung:
                funde.append(f"{schlussel} = {wert} hat weder einen Eintrag in design.herleitung "
                             "noch in design.email_eigene – jede E-Mail-Farbe braucht beides")
                continue
            marke = str(herleitung[schlussel])
            if marke not in token[modus]:
                warum = " (nur als color-mix() gemischt – im E-Mail nicht auflösbar)" \
                    if marke + ":gemischt" in token[modus] else ""
                funde.append(f"{schlussel} verweist auf {marke}, den es im Build nicht als "
                             f"hex/rgb-Token gibt{warum}")
                continue
            if token[modus][marke] != norm:
                funde.append(f"{schlussel} = {wert} widerspricht {marke} = "
                             f"{token[modus][marke]} (Site) – Marke im Studio muss die der Site sein")
    for schlussel, marke in herleitung.items():
        if schlussel not in rollen:
            funde.append(f"design.herleitung nennt {schlussel}, aber keine Farbe dieses Namens "
                         "existiert im Designblock – toter Verweis")
    # Pflichtrollen: ohne sie bricht render_html mit KeyError – laut melden statt
    # im Build-Log des Workflows verschenken.
    for modus in ("hell", "dunkel"):
        for rolle in design.get("pflicht_rollen", []):
            if rolle not in (design.get(modus) or {}):
                funde.append(f"design.{modus}.{rolle} fehlt – der Renderer braucht die Rolle "
                             "in beiden Modi")
    return (funde, sorted(rollen))


def themen_abgleich(root: str = BLOG_DIR) -> list:
    """Die Präferenz-Themen müssen die Themenwelten der Site sein – sonst meldet
    das Formular Interessen, die es im Blog nicht gibt."""
    konf = konfiguration(root)
    quel = _read(os.path.join(root, THEMENWELTEN_REL))
    if not quel:
        return [f"{THEMENWELTEN_REL} nicht lesbar – Themenabgleich ausgefallen"]
    try:
        welten = json.loads(quel)
    except json.JSONDecodeError as exc:
        return [f"{THEMENWELTEN_REL} nicht lesbar: {exc}"]
    ids = {t.get("id") for t in welten.get("topics", []) if t.get("id")}
    funde = []
    for t in konf.get("themen", []):
        if t.get("id") not in ids:
            funde.append(f"Studio-Thema „{t.get('id')}“ ist keine Themenwelt der Site "
                         f"(erlaubt: {', '.join(sorted(i for i in ids if i))})")
    return funde


WORKER_BASIS = "https://abos.franksfinanzcheck.de"
WRANGLER_REL = "newsletter-worker/wrangler.toml"


def worker_basis_abgleich(root: str = BLOG_DIR) -> list:
    """hugo.toml: der Capture-Endpunkt muss die FESTE Worker-Subdomain sein.

    Die drei Info-Seiten (/newsletter/bestaetigung/, /newsletter/abmelden/,
    /newsletter/praeferenzen/) und die Journey-Links in den Mails referenzieren
    genau diese Domäne als Text. Zeigt der Endpunkt woanders hin, lügen die
    Seiten – das meldet diese Wache, statt der Widerspruch im Build
    unterzugehen.
    """
    toml = _read(os.path.join(root, "hugo.toml"))
    m = re.search(r'(?m)^\s*newsletterFormAction\s*=\s*"([^"]*)"', toml)
    basis = (m.group(1).strip() if m else "")
    if basis == WORKER_BASIS + "/anmeldung":
        return []
    if not basis:
        return ["hugo.toml: newsletterFormAction leer – der Capture-Endpunkt ist nicht "
                "die Worker-Subdomain, die die Info-Seiten benennen (" + WORKER_BASIS + ")"]
    return [f"hugo.toml: newsletterFormAction = {basis!r} – muss {WORKER_BASIS}/anmeldung "
            f"sein (die Journey-Infoseiten sind an diese Domäne gebunden)"]


def wrangler_themen_abgleich(root: str = BLOG_DIR) -> list:
    """newsletter-worker/wrangler.toml: THEMEN_IDS + Labels deckungsgleich mit Studio.

    Der Worker validiert Anmelde-Themen gegen THEMEN_IDS und rendert die
    Präferenzseite-Labels aus THEMEN_LABELS. Beide werden von Hand gepflegt
    (Watch steht im Wrangler-Kommentar) – driften sie vom Studio ab, verschluckt
    das Formular Themen still.
    """
    pfad = os.path.join(root, WRANGLER_REL)
    roh = _read(pfad)
    if not roh:
        return [f"{WRANGLER_REL} nicht lesbar – Worker-Themenabgleich ausgefallen"]
    funde = []
    m = re.search(r'(?m)^\s*THEMEN_IDS\s*=\s*"([^"]*)"', roh)
    if not m:
        return ["wrangler.toml: THEMEN_IDS fehlt – der Worker akzeptiert kein Thema"]
    wrangler_ids = {t.strip() for t in m.group(1).split(",") if t.strip()}
    studio_ids = {t.get("id") for t in konfiguration(root).get("themen", []) if t.get("id")}
    if wrangler_ids != studio_ids:
        funde.append("wrangler.toml: THEMEN_IDS weicht vom Studio ab "
                     f"(nur Worker: {', '.join(sorted(wrangler_ids - studio_ids)) or '–'}; "
                     f"nur Studio: {', '.join(sorted(studio_ids - wrangler_ids)) or '–'})")
    m2 = re.search(r'(?m)^\s*THEMEN_LABELS\s*=\s*"((?:[^"\\]|\\.)*)"', roh)
    if not m2:
        funde.append("wrangler.toml: THEMEN_LABELS fehlt – die Präferenzseite fällt auf IDs zurück")
        return funde
    try:
        labels = json.loads(re.sub(r'\\(.)', r'\1', m2.group(1)))
    except json.JSONDecodeError as exc:
        return funde + [f"wrangler.toml: THEMEN_LABELS ist kein gültiges JSON: {exc}"]
    if set(labels) != wrangler_ids:
        funde.append("wrangler.toml: THEMEN_LABELS-Keys != THEMEN_IDS "
                     f"(fehlt: {', '.join(sorted(wrangler_ids - set(labels))) or '–'}; "
                     f"übrig: {', '.join(sorted(set(labels) - wrangler_ids)) or '–'})")
    for id_, text in labels.items():
        if not (isinstance(text, str) and text.strip()):
            funde.append(f"wrangler.toml: THEMEN_LABELS[{id_!r}] leer")
    return funde


def kontrast_pruefung(konf: dict) -> list[dict]:
    """Die Pflichtpaare aus design.kontraste in BEIDEN Modi nachmessen.

    → [{"modus","paar","hinten","vorn","wert","mindest","ok"}] – gemessen nach
    WCAG 2.1, nicht geschätzt (DESIGN.md §8). Ein E-Mail, dessen Sekundärtext auf
    der Soft-Fläche unter 4.5:1 fällt, ist im Reader mit abgeschaltetem Kontrast
    schlicht unlesbar – und das sieht kein Screenshot-Review.
    """
    out = []
    design = konf.get("design", {})
    for modus in ("hell", "dunkel"):
        farben = design.get(modus) or {}
        for paar in design.get("kontraste", []):
            try:
                name, hinten, vorn, mindest = paar[0], paar[1], paar[2], float(paar[3])
            except (IndexError, TypeError, ValueError):
                out.append({"modus": modus, "paar": str(paar), "wert": 0.0,
                            "mindest": 0.0, "ok": False, "fehler": "unvollständiges Paar"})
                continue
            h, v = farben.get(hinten, ""), farben.get(vorn, "")
            if not h or not v:
                out.append({"modus": modus, "paar": name, "wert": 0.0, "mindest": mindest,
                            "ok": False, "fehler": f"Rolle fehlt ({hinten}/{vorn})"})
                continue
            try:
                wert = kontrast(h, v)
            except ValueError as exc:
                out.append({"modus": modus, "paar": name, "wert": 0.0, "mindest": mindest,
                            "ok": False, "fehler": str(exc)})
                continue
            out.append({"modus": modus, "paar": name, "hinten": h, "vorn": v,
                        "wert": wert, "mindest": mindest, "ok": wert >= mindest})
    return out


# ------------------------------------------------------------------- Material
# Tausendertrenner erlaubt Punkt, Komma und geschütztes Leerzeichen
# (U+00A0/U+202F), weil die
# Redaktionspipeline alle drei schreibt; nach dem Betrag muss zwingend die
# Währung stehen – sonst werden Datums- und Prozentzahlen zu Euro erklärt.
EURO_RE = re.compile(r"(?<![\d.,])(\d{1,3}(?:[.\u00a0\u202F]\d{3})*|\d{1,4})(?:[,.]\d{1,2})?"
                     r"[ \u00a0\u202F]*(?:€|Euro(?![\w-]))")
PROZENT_RE = re.compile(r"(?<![\d.,])(\d{1,3})(?:[,.]\d{1,2})?[ \u00a0\u202F]*(?:%|Prozent(?![\w-]))")
# Spar-Kontext: Ein Euro-Betrag in einem Ratgeber kann eine Vermögenszahl, ein
# Preis oder eine Ersparnis sein. Die Hero-Zahl darf nur eine ERS.PARNIS sein –
# deshalb muss Spar-Vokabular in der Nähe stehen (Zeichenfenster: 90).
SPAR_KONTEXT_RE = re.compile(r"(?i)(spar|erspar|billiger|g[üu]nstig|senk|sink|reduzier|"
                             r"bonus|pr[äa]mie|gutschrift|weniger|zur[üu]ck|erstatt|wechseln|"
                             r"effektiv|spart|niedriger|g[üu]nstiger)")
KONTEXT_FENSTER = 90


def _clean(text: str, laenge: int = 0) -> str:
    text = re.sub(r"\[\[?[^\]]*\]\]?", "", text or "")          # Shortcodes & wikilinks
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)             # Bilder
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)         # Links → Text
    text = re.sub(r"[*_`>#]", "", text)
    text = re.sub(r"[\u00a0\u202F]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if laenge and len(text) > laenge:
        gekuerzt = text[:laenge].rsplit(" ", 1)[0]
        text = gekuerzt.rstrip(" ,;:.") + " …"
    return text


def zahl_aus_text(*texte: str, min_betrag: int = 20, max_betrag: int = 5000,
                  kontextpflicht: bool = True) -> dict:
    """Größte im Material genannte Ersparnis – inkl. Belegstelle.

    → {"wert": int|None, "text": "240 €", "beleg": "…"}
    Zwei Leitplanken, die erfundene Schlagzeilen verhindern:
      1. Kontextpflicht – nur Beträge in Spar-Nähe zählen (sonst wird der
         „Notgroschen 156.000 €" zur Tagesersparnis aufgeblasen).
      2. Plausibilität – unter `min_betrag` ist es Kleingeld, über `max_betrag`
         kein Betrag, den ein Tarifwechsel in einer Viertelstunde bringt.
    Die Zahl wird nie umgeschrieben: `beleg` ist der Wortsatz, den die QA-Wache
    im Quelltext verlangen muss.
    """
    bester = None
    beleg = ""
    for quelle in texte:
        quelle = quelle or ""
        for m in EURO_RE.finditer(quelle):
            try:
                wert = int(m.group(1).replace(".", "").replace("\u00a0", "").replace("\u202F", ""))
            except ValueError:
                continue
            if wert < min_betrag or wert > max_betrag:
                continue
            if kontextpflicht:
                rand = quelle[max(0, m.start() - KONTEXT_FENSTER): m.end() + KONTEXT_FENSTER]
                if not SPAR_KONTEXT_RE.search(rand):
                    continue
            if bester is None or wert > bester:
                bester, beleg = wert, m.group(0).strip()
    if bester is None:
        return {"wert": None, "text": "", "beleg": ""}
    return {"wert": bester, "text": f"{bester:,}".replace(",", ".") + " €", "beleg": beleg}


ZAHL_RE = re.compile(r"\d{1,3}(?:[.\u00a0\u202F ,]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?")


def zahlen_im_text(text: str) -> set[str]:
    """Alle Zahlen eines Textes als Ziffernfolge – 2.800 € = 2 800 € = 2800 €.

    Die Belegprüfung der QA-Wache vergleicht Zahlen so und nicht als Zeichenkette:
    ein Tausendertrenner darf einen Beleg nicht unkenntlich machen, sonst meldet
    die Wache eine Erfindung, wo eine Zahl mit anderem Trenner steht.
    """
    out = set()
    for m in ZAHL_RE.finditer(text or ""):
        ziffern = re.sub(r"\D", "", m.group(0))
        if ziffern:
            out.add(ziffern)
    return out


def material_aus_artikel(root: str, artikel: list[dict]) -> list[dict]:
    """Frontmatter der Digest-Artikel zu E-Mail-Material machen (kurzantwort
    schlägt description: sie ist die kürzeste ehrliche Aussage des Artikels)."""
    out = []
    for a in artikel:
        pfad = os.path.join(root, a.get("path", "")) if a.get("path") else ""
        kurza = a.get("kurzantwort") or ""
        if not kurza and pfad:
            quell = _read(pfad)
            m = re.search(r'(?m)^kurzantwort:\s*["\']?(.*?)["\']?\s*$', quell, re.S)
            kurza = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
        stueck = dict(a)
        stueck["kurzantwort"] = kurza
        stueck["quelle_text"] = _clean(kurza or a.get("beschreibung", ""))
        out.append(stueck)
    return out


# ------------------------------------------------------------- Creative (Text)
def ausgabe_nr(datum: datetime.date) -> str:
    kw = datum.isocalendar()[1]
    return f"Ausgabe {kw:02d}/{datum.year}"


# Neutraltexte: ein Mail wird nie leer oder namenlos, weil ein Rahmen fehlt –
# die Konfiguration darf dünner sein als der Code, aber der Versand steht.
NEUTRAL_AUFMACHER = ("Rechne nach, bevor du bezahlst – die Ratgeber der letzten Tage "
                     "in einer Mail, jede Zahl mit Frist und Beleg.")
NEUTRAL_GRUSS = ("Wenn eine Rechnung bei dir nicht passt, schreib mir – ich lese "
                 "jede Antwort.")
NEUTRAL_VORSCHAU = "Dazu: Fristen und Tarifwechsel im Überblick."


def kadenz_rahmen(datum: datetime.date, konf: dict) -> dict:
    """Der Redaktionsrahmen eines Versandtags – aus `creative.kadenz`.

    Zwei Mails pro Woche sind nur dann ein Abonnement und kein Rauschen, wenn
    beide einen eigenen Auftrag haben: dienstags der Wochen-Check (was sich
    bewegt hat), freitags der Wochen-Abschluss (was sich bis Montag erledigen
    lässt). Die Texte stehen in der Konfiguration, weil sie Redaktion sind; die
    FAKTEN (welche Tage, welcher Termin als Nächstes) kommen aus
    `scripts/newsletter_schedule.py`, damit Mail und Website nicht zwei
    Kalender kennen.

    Schlüssel der Konfiguration sind `str(datum.weekday())` – keine
    Wochentagsnamen: `strftime("%A")` liefert die Prozess-Locale („Tuesday“ auf
    dem Runner), und eine Bedingung gegen „Freitag“ läuft dort still ins Leere.
    """
    reg = (konf.get("creative", {}) or {}).get("kadenz") or {}

    def _feld(name: str, neutral: str) -> str:
        wert = (reg.get(name) or {}).get(str(datum.weekday()), "")
        return str(wert).strip() or neutral

    return {
        "schluessel": str(datum.weekday()),
        "versandtag": plan.ist_versandtag(datum),
        "tag": plan.wochentag(datum),
        "tag_kurz": plan.tag_kurz(datum),
        "ausgabe": _feld("ausgabe", "Spar-Ausgabe"),
        "aufmacher": _feld("aufmacher", NEUTRAL_AUFMACHER),
        "betreff": _feld("betreff", ""),
        "vorschau": _feld("preheader_hinweis", NEUTRAL_VORSCHAU),
        "gruss": _feld("gruss", NEUTRAL_GRUSS),
        "naechste_zeile": bool(reg.get("naechste_zeile", True)),
        "naechste": plan.naechste_ausgabe_text(datum),
    }


def spar_zahl(material: list[dict], konf: dict) -> dict:
    """Die Hero-Zahl einer Ausgabe – aus dem Material, mit den Leitplanken der Konfiguration.

    `min_betrag`/`max_betrag`/`kontextpflicht` stehen in data/newsletter_studio.json
    (`creative.hero`), weil sie eine redaktionelle Entscheidung sind: was als
    „Sparbetrag des Tages" gelten darf, legt die Redaktion fest, nicht der Parser.
    """
    reg = konf.get("creative", {}).get("hero", {})
    return zahl_aus_text(*[a.get("quelle_text", "") or a.get("beschreibung", "") for a in material],
                         min_betrag=int(reg.get("min_betrag", 20)),
                         max_betrag=int(reg.get("max_betrag", 5000)),
                         kontextpflicht=bool(reg.get("kontextpflicht", True)))


def _titelkern(titel: str, laenge: int) -> str:
    """Der erste Sinnabschnitt eines Titels – Klammer-/Nachsatz-Bruch inklusive.

    Ein Betreff, der mit „…“ endet, wirkt wie ein halbfertiger Entwurf. Deshalb:
    erst am Trennzeichen schneiden, dann am Wort – und nie mit Auslassungspunkten.
    """
    kern = re.split(r"\s*[:–—|]\s*", titel or "", maxsplit=1)[0].strip()
    kern = re.sub(r"^(So |Wie |Warum |Was |Dein |Deine |Der |Die |Das )", "", kern).strip()
    kern = _clean(kern)
    if len(kern) > laenge:
        kern = kern[:laenge].rsplit(" ", 1)[0].rstrip(" ,;:.")
    return kern


def betreff_varianten(material: list[dict], datum: datetime.date, konf: dict) -> list[dict]:
    """Drei Betreffzeilen, Länge als Gate – die Varianz entscheidet der Versandtag.

    Rotationsbasis ist der Wochentag, und zwar als Zahl (1 = Dienstag,
    4 = Freitag): keine Personalisierung, sondern Kadenz – reproduzierbar ohne
    Nutzerdaten. Die Kadenz-Variante kommt aus `creative.kadenz`, damit die
    Redaktion sie ändert, ohne Code anzufassen.
    """
    marke = konf.get("creative", {}).get("marke_kurz", "FranksFinanzcheck")
    max_anz = int(konf.get("email", {}).get("max_artikel", 5))
    # Gezählt wird das, was in der Mail steht – nicht der Bestand. Ein Betreff
    # „26 Sparechnungen“ über fünf Blöcken ist eine gebrochene Ansage (Wache Q16).
    anzahl = min(len(material), max_anz)
    zahl = spar_zahl(material, konf)
    erster = material[0]["titel"] if material else ""
    reg = konf.get("creative", {}).get("betreff", {})
    max_l = int(reg.get("max_zeichen", 45))
    kern = _titelkern(erster, max_l - len(marke) - 8)
    rahmen = kadenz_rahmen(datum, konf)
    # Jede Variante trägt die Marke: im Postfach entscheidet die Wiedererkennung,
    # ob überhaupt geöffnet wird – ein Betreff ohne Absender-Marke ist verschenktes
    # Vertrauen (QA-Regel Q8 meldet ihn als Warnung, wenn er von Hand ergänzt wird).
    varianten: list[tuple[str, str]] = []
    # An einem Versandtag führt die Kadenz-Variante die Liste: sie ist der
    # Auftrag des Tages und gehört in die ersten drei, die wirklich gebaut
    # werden. Die Mengen-Variante („3 Sparechnungen heute“) ist die schwächste
    # der vier und bleibt an Versandtagen draußen – eine Ausgabe mit Zahl und
    # Titel braucht sie nicht. Außerhalb der Versandtage (manuelle Vorschau)
    # gilt die alte Reihenfolge; dort behauptet die Mail keinen Wochenauftrag.
    if rahmen["versandtag"] and rahmen["betreff"]:
        varianten.append((f"{marke}: {rahmen['betreff']}", "kadenz"))
    if zahl["wert"]:
        varianten.append((f"{marke}: {zahl['text']} heute prüfen", "zahl"))
    if anzahl > 1 and not (rahmen["versandtag"] and rahmen["betreff"]):
        varianten.append((f"{marke}: {anzahl} Sparechnungen heute", "menge"))
    if kern:
        varianten.append((f"{marke}: {kern}", "thema"))
    if not varianten:
        varianten.append((f"{marke}: {datum.strftime('%d.%m.%Y')}", "datum"))
    reg = konf.get("creative", {}).get("betreff", {})
    min_l, max_l = int(reg.get("min_zeichen", 30)), int(reg.get("max_zeichen", 45))
    out, gesehen = [], set()
    for text, art in varianten:
        text = re.sub(r"\s+", " ", text).strip()
        # Kürzer als erlaubt? Marke voranstellen – sie ist der Grund, warum der
        # Betreff im Postfach zwischen Amazon und Newsletter-Werbung auffindbar ist.
        if len(text) < min_l and marke not in text:
            text = f"{marke}: {text}"
        # Länger als erlaubt? Am Wort schneiden, nie mit Auslassungspunkten –
        # ein Betreff mit „…“ liest sich wie ein halb gespielter Entwurf.
        if len(text) > max_l:
            text = text[:max_l].rsplit(" ", 1)[0].rstrip(" ,;:.…")
        if text in gesehen:
            continue
        gesehen.add(text)
        out.append({"text": text, "art": art, "laenge": len(text),
                    "zu_kurz": len(text) < min_l, "zu_lang": len(text) > max_l})
        if len(out) >= int(reg.get("varianten", 3)):
            break
    return out


# Welche Betreffvariante ein Versandtag führt. Dienstag rechnet (Zahl), Freitag
# mahnt an die Frist (Kadenz) – beides mit Rückfall, damit ein Tag ohne Zahl
# oder ohne Rahmen nie ohne Betreff dasteht. Vorher entschied
# `datum.weekday() % len(var)`: bei drei Varianten landen Dienstag (1 % 3) und
# Freitag (4 % 3) beide auf Index 1 – die „Rotation“ hat zwischen den beiden
# Versandtagen nie unterschieden.
VORZUG_VARIANTE = {1: ("zahl", "kadenz", "thema"), 4: ("kadenz", "zahl", "thema")}


def variante_fuer_tag(datum: datetime.date, varianten: list[dict]) -> int:
    """Index der Betreffvariante, die der Versandtag führt."""
    if not varianten:
        return 0
    for art in VORZUG_VARIANTE.get(datum.weekday(), ()):
        for i, v in enumerate(varianten):
            if v.get("art") == art:
                return i
    return 0


def preheader(material: list[dict], betreff: str, konf: dict,
              datum: datetime.date | None = None) -> str:
    """Der zweite Satz in der Inbox-Vorschau – nie eine Wiederholung des Betreffs."""
    reg = konf.get("creative", {}).get("preheader", {})
    min_l, max_l = int(reg.get("min_zeichen", 40)), int(reg.get("max_zeichen", 120))
    rahmen = kadenz_rahmen(datum or datetime.date.today(), konf)
    vorschau = rahmen["vorschau"].rstrip(".")
    anriss = _clean(material[0].get("quelle_text") or material[0]["titel"]) if material else ""
    if anriss and rahmen["versandtag"] and vorschau:
        # Komponiert statt abgeschnitten: Der zweite Satz der Inbox-Vorschau
        # beginnt mit dem Auftrag des Tages und reicht dann so weit in den
        # Aufmacher, wie das Zeichenbudget trägt. Ein Preheader, der mitten im
        # Satz endet, verschenkt genau die Zeile, die über den Öffner entscheidet.
        platz = max(20, max_l - len(vorschau) - 3)
        text = f"{vorschau} – {_clean(anriss, platz).rstrip(' …')}"
    elif anriss:
        text = _clean(anriss, max_l)
    else:
        text = _clean(rahmen["aufmacher"], max_l) or \
            konf.get("capture", {}).get("versprechen", "")
    text = re.sub(r"\s+", " ", text).strip()
    if text.lower()[:min_l] == (betreff or "").lower()[:min_l]:
        # Zweiter Satz statt Echo: die Ergänzung kommt aus dem Rahmen des Tages,
        # nicht aus einer Floskel.
        text = (text + " – " + vorschau).strip(" -")
    if len(text) < min_l:
        text = (text + ". " + (vorschau or
                               konf.get("capture", {}).get("versprechen", ""))).strip(" .")
        text = _clean(text, max_l)
    return text[:max_l].rstrip(" ,;.…")


# ------------------------------------------------------------------- Layout
def _esc(text: str) -> str:
    return _html.escape(text or "", quote=True)


def blocks_bauen(material: list[dict], datum: datetime.date, konf: dict) -> list[dict]:
    """Die Ausgabenhierarchie – identisch in HTML und Text, daher ableitbar."""
    e_mail = konf.get("email", {})
    max_anz = int(e_mail.get("max_artikel", 5))
    versprechen = (konf.get("capture", {}) or {}).get("versprechen") or \
        "Zweimal pro Woche: Spartipps und Rechner – dienstags und freitags."
    rahmen = kadenz_rahmen(datum, konf)
    bl: list[dict] = [{
        "typ": "kopf", "titel": "FranksFinanzcheck",
        # Der Wochentag steht im Kopf, weil die Kadenz das Versprechen ist:
        # „Dienstag, 23.09.2026 · Ausgabe 39/2026“ beantwortet im Postfach die
        # Frage, warum diese Mail heute kommt – ohne einen Blick ins Impressum.
        "zeile": (f"{rahmen['tag']}, {datum.strftime('%d.%m.%Y')} · "
                  f"{ausgabe_nr(datum)}"),
        "ausgabe": rahmen["ausgabe"],
        "versprechen": versprechen}]
    zahl = spar_zahl(material, konf)
    if zahl["wert"]:
        bl.append({"typ": "hero",
                   "zahl": zahl["text"],
                   "beleg": zahl["beleg"],
                   "text": "Der größte Sparbetrag, den diese Ausgabe nennt – die "
                           "Rechnung dazu steht im Artikel. Nachrechnen dauert "
                           "keine Viertelstunde.",
                   "ziel": material[0]["url"]})
    else:
        bl.append({"typ": "hero", "zahl": "", "beleg": "",
                   "text": rahmen["aufmacher"],
                   "ziel": "/posts/",
                   "cta": "Alle Ratgeber ansehen"})
    bl[1].setdefault("cta", "Jetzt nachrechnen")
    # Themenzeile: nur genannte Themen, damit die Präferenzen der Anmeldung folgen
    themen = {t["id"]: t["label"] for t in konf.get("themen", [])}
    gruppen = []
    for a in material:
        gruppen.append({"typ": "artikel", "titel": a["titel"],
                        "text": _clean(a.get("quelle_text") or a.get("beschreibung", ""),
                                       int(konf.get("creative", {}).get("block_text_zeichen", 190))),
                        "url": a["url"], "thema": themen.get(a.get("pillar", ""), ""),
                        "datum": a.get("datum", "")})
    if gruppen:
        bl.extend(gruppen[:max_anz])
    bl.append({"typ": "gruss",
               "text": rahmen["gruss"],
               "antwort": e_mail.get("antwort_an", "")})
    # Die Zeile „Nächste Ausgabe“ ist Erwartungsmanagement, kein Fülltext: wer
    # weiß, wann die nächste Mail kommt, meldet sich seltener ab, weil eine
    # Pause nach Plan aussieht statt nach Funkstille.
    naechste = (rahmen["naechste"] + " – und nur, wenn es etwas zu rechnen gibt.") \
        if rahmen["naechste_zeile"] else ""
    antwort = e_mail.get("antwort_an") or "kontakt@franksfinanzcheck.de"
    formlos = ("mailto:" + str(antwort).strip()
               + "?subject=Newsletter%20abmelden"
               + "&body=Bitte%20diese%20Adresse%20vom%20Spar-Newsletter%20abmelden.")
    bl.append({"typ": "fuss",
               "anschrift": e_mail.get("rechtliches", {}).get("anschrift", ""),
               "impressum": e_mail.get("rechtliches", {}).get("impressum_url", ""),
               "datenschutz": e_mail.get("rechtliches", {}).get("datenschutz_url", ""),
               "hinweis": "Du erhältst diese Mail, weil du dich auf franksfinanzcheck.de "
                          "mit Double-Opt-In angemeldet hast.",
               "naechste": naechste,
               "werbung": e_mail.get("rechtliches", {}).get("werbung_hinweis", ""),
               "antwort": antwort,
               "formlos": formlos})
    return bl


def _button(url: str, text: str, farben: dict, schrift: str) -> str:
    """Bulletproof Button: Tabelle + VML-Reliquiat für Outlook 2007-2019.
    Ein `border-radius` allein ist dort eine Linie ohne Fläche – und ein
    CTA ohne Fläche ist kein CTA."""
    bg = farben["cta_flaeche"]
    fg = farben["cta_text"]
    marke = farben.get("marke") or bg
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center" '
        'style="margin:0 auto;"><tr>'
        '<td align="center" style="border-radius:10px;background:' + bg + ';">'
        '<!--[if mso]><v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" '
        'xmlns:w="urn:schemas-microsoft-com:office:word" href="' + _esc(url) + '" '
        'style="height:44px;v-text-anchor:middle;width:230px;" arcsize="23%" strokecolor="'
        + marke + '" fillcolor="' + bg + '"><w:anchorlock/><center style="color:' + fg
        + ';font-family:' + schrift + ';font-size:15px;font-weight:700;">'
        + _esc(text) + '</center></v:roundrect><![endif]-->'
        '<!--[if !mso]><!--><a href="' + _esc(url) + '" class="knopf-a" '
        'style="background:' + bg + ';border-radius:10px;color:' + fg + ';display:inline-block;'
        'font-family:' + schrift + ';font-size:15px;font-weight:700;line-height:44px;'
        'text-align:center;text-decoration:none;width:230px;-webkit-text-size-adjust:none;">'
        + _esc(text) + '</a><!--<![endif]-->'
        '</td></tr></table>')


def render_html(blocks: list[dict], *, betreff: str, vorlage_text: str, datum: datetime.date,
                konf: dict) -> str:
    """Ein E-Mail, das in Outlook, Gmail (App + Web) und Apple Mail dieselbe
    Hierarchie zeigt: 620 px, Tabellen-Layout, kein Flex/Grid, keine Externen
    Assets, inline gestylt, Dark-Mode-Block per `!important`."""
    design = konf.get("design", {})
    h, d = design.get("hell", {}), design.get("dunkel", {})
    schrift = design.get("schrift", "Arial,sans-serif")
    e_mail = konf.get("email", {})
    breite = int(e_mail.get("breite", 620))
    runden = int(design.get("radius", 14))
    marken = e_mail.get("marken", {})
    url = lambda p: p if str(p).startswith("http") else GRUND_URL + "/" + str(p).lstrip("/")

    stil_dunkel = ("@media (prefers-color-scheme: dark){.dk-hintergrund{background-color:"
                   + d["seite"] + " !important}.dk-karte{background-color:" + d["karte"]
                   + " !important;border-color:" + d["grenze"] + " !important}.dk-text{color:"
                   + d["text"] + " !important}.dk-headline{color:" + d["headline"] + " !important"
                   "}.dk-weich{background-color:" + d["soft"] + " !important}.dk-rand{border-color:"
                   + d["grenze"] + " !important}}")
    mobil = ("@media only screen and (max-width:620px){.spalte{display:block !important;"
             "width:100% !important;max-width:100% !important}.kachel{padding-left:16px !important;"
             "padding-right:16px !important}.knopf-a{width:100% !important;max-width:100% !important}}")

    zeilen: list[str] = []
    for i, b in enumerate(blocks):
        typ = b["typ"]
        if typ == "kopf":
            # Der Ausgaben-Name steht als Kicker unter der Marke: zwei Mails pro
            # Woche brauchen einen erkennbaren Rhythmus, sonst liest sich die
            # zweite wie eine Wiederholung der ersten.
            kicker = (f'<div style="font-family:{schrift};font-size:12px;font-weight:700;'
                      f'letter-spacing:.5px;text-transform:uppercase;color:{h["marke"]};'
                      f'margin-top:3px;">{_esc(b["ausgabe"])}</div>') if b.get("ausgabe") else ""
            zeilen.append(
                f'<tr><td class="kachel dk-karte" style="padding:20px 24px 16px;border-bottom:1px solid {h["grenze"]};border-radius:{runden}px {runden}px 0 0;background:{h["karte"]};">'
                f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
                f'<td class="spalte" style="font-family:{schrift};font-size:17px;font-weight:700;color:{h["headline"]};letter-spacing:.2px;">'
                f'{_esc(b["titel"])}{kicker}</td>'
                f'<td class="spalte" align="right" style="font-family:{schrift};font-size:12.5px;color:{h["sekundaer"]};">'
                f'{_esc(b["zeile"])}</td></tr></table>'
                f'<div class="dk-text" style="margin-top:8px;font-family:{schrift};font-size:14px;line-height:1.5;color:{h["sekundaer"]};">'
                f'{_esc(b["versprechen"])}</div></td></tr>')
        elif typ == "hero":
            zahl = b.get("zahl", "")
            zeiger = (f'<div class="dk-headline" style="font-family:{schrift};font-size:34px;'
                      f'line-height:1.05;font-weight:800;color:{h["marke_dunkel"]};'
                      f'font-variant-numeric:tabular-nums;">{_esc(zahl)}</div>' if zahl else "")
            link = b.get("ziel") or ""
            # Der CTA ist ein Bulletproof-Button, kein Textlink: in Outlook ist ein
            # unterstrichener Satz keine Handlungsaufforderung, und die Mail lebt von
            # genau einem primären Klickziel (Craft-Floor: ein CTA, nicht drei).
            ziel = (_button(url(link), b.get("cta") or "Jetzt nachrechnen", h, schrift)
                    if link else "")
            zeilen.append(
                f'<tr><td class="kachel dk-weich" style="padding:20px 24px 24px;background:{h["soft"]}">'
                f'{zeiger}'
                f'<div class="dk-text" style="margin-top:{8 if zahl else 0}px;font-family:{schrift};'
                f'font-size:15px;line-height:1.55;color:{h["text"]};">{_esc(b["text"])}</div>'
                f'<div style="margin-top:16px;">{ziel}</div>'
                f'</td></tr>')
        elif typ == "artikel":
            marke = (f'<div style="font-family:{schrift};font-size:12px;font-weight:700;'
                     f'letter-spacing:.4px;text-transform:uppercase;color:{h["marke"]};'
                     f'margin-bottom:6px;">{_esc(b["thema"])}</div>') if b.get("thema") else ""
            zeilen.append(
                f'<tr><td class="kachel dk-karte dk-rand" style="padding:18px 24px;border-bottom:1px solid {h["grenze"]};background:{h["karte"]};" valign="top">'
                f'{marke}'
                f'<h2 class="dk-headline" style="margin:0 0 6px;font-family:{schrift};font-size:19px;'
                f'line-height:1.28;color:{h["headline"]};font-weight:700;text-wrap:balance;">'
                f'<a href="{_esc(url(b["url"]))}" style="color:{h["headline"]};text-decoration:none;">'
                f'{_esc(b["titel"])}</a></h2>'
                f'<p class="dk-text" style="margin:0;font-family:{schrift};font-size:15px;line-height:1.6;'
                f'color:{h["text"]};">{_esc(b["text"])}</p>'
                f'<p style="margin:10px 0 0;"><a href="{_esc(url(b["url"]))}" '
                f'style="font-family:{schrift};font-size:14.5px;font-weight:700;color:{h["link"]};'
                f'text-decoration:underline;">Weiterlesen</a></p></td></tr>')
        elif typ == "gruss":
            zeilen.append(
                f'<tr><td class="kachel dk-karte" style="padding:18px 24px;background:{h["karte"]}">'
                f'<p class="dk-text" style="margin:0 0 8px;font-family:{schrift};font-size:15px;'
                f'line-height:1.6;color:{h["text"]};">{_esc(b["text"])}</p>'
                f'<p style="margin:0;font-family:{schrift};font-size:14px;color:{h["sekundaer"]};">'
                f'— Frank · <a href="mailto:{_esc(b["antwort"])}" style="color:{h["link"]};'
                f'text-decoration:underline;">{_esc(b["antwort"])}</a></p></td></tr>')
        elif typ == "fuss":
            marken_links = []
            if marken.get("mirror"):
                marken_links.append(f'<a href="{_esc(marken["mirror"])}" style="color:{h["link"]};'
                                    f'text-decoration:underline;">Im Browser ansehen</a>')
            if marken.get("profil"):
                marken_links.append(f'<a href="{_esc(marken["profil"])}" style="color:{h["link"]};'
                                    f'text-decoration:underline;">Präferenzen</a>')
            # Die Nächste-Ausgabe-Zeile steht über dem Rechtsteil: sie ist die
            # einzige Zeile des Fußes, die dem Leser etwas sagt – Erwartung
            # statt Funkstille. Der Rest ist Pflicht.
            naechste = (f'<p class="dk-text" style="margin:0 0 10px;font-family:{schrift};'
                        f'font-size:13px;line-height:1.6;color:{h["sekundaer"]};">'
                        f'<strong>{_esc(b["naechste"])}</strong></p>') if b.get("naechste") else ""
            formlos = str(b.get("formlos") or "mailto:kontakt@franksfinanzcheck.de?subject=Newsletter%20abmelden")
            zeilen.append(
                f'<tr><td class="kachel dk-karte" style="padding:18px 24px 22px;border-top:1px solid {h["grenze"]};'
                f'border-radius:0 0 {runden}px {runden}px;background:{h["karte"]}">{naechste}'
                f'<p class="dk-text" style="margin:0 0 8px;font-family:{schrift};font-size:12.5px;'
                f'line-height:1.6;color:{h["sekundaer"]};">{_esc(b["hinweis"])}</p>'
                f'<p class="dk-text" style="margin:0 0 12px;font-family:{schrift};font-size:15px;'
                f'line-height:1.6;color:{h["text"]};">'
                f'<a href="{_esc(marken.get("unsubscribe", "#"))}" style="color:{h["link"]};'
                f'font-weight:700;text-decoration:underline;">Newsletter abmelden</a>'
                f' · oder formlos an '
                f'<a href="{_esc(formlos)}" style="color:{h["link"]};text-decoration:underline;">'
                f'{_esc((b.get("antwort") or "kontakt@franksfinanzcheck.de"))}</a></p>'
                f'<p style="margin:0 0 8px;font-family:{schrift};font-size:12.5px;line-height:1.6;'
                f'color:{h["sekundaer"]};">{" · ".join(marken_links) if marken_links else ""}</p>'
                f'<p class="dk-text" style="margin:0;font-family:{schrift};font-size:12.5px;line-height:1.6;'
                f'color:{h["sekundaer"]};">{_esc(b["anschrift"])} · '
                f'<a href="{_esc(b["impressum"])}" style="color:{h["link"]};text-decoration:underline;">Impressum</a> · '
                f'<a href="{_esc(b["datenschutz"])}" style="color:{h["link"]};text-decoration:underline;">Datenschutz</a></p>'
                f'<p class="dk-text" style="margin:8px 0 0;font-family:{schrift};font-size:12px;'
                f'line-height:1.6;color:{h["sekundaer"]};">{_esc(b["werbung"])}</p>'
                f'</td></tr>')
    vor = (f'<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;'
           f'font-size:1px;line-height:1px;color:{h["karte"]};opacity:0;">{_esc(vorlage_text)}'
           f'&#8203;&zwnj;</div>')
    return (
        '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" '
        '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n'
        '<html lang="de" xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:v="urn:schemas-microsoft-com:vml" '
        'xmlns:o="urn:schemas-microsoft-com:office:office">\n<head>\n'
        '<meta http-equiv="Content-Type" content="text/html; charset=utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<meta name="color-scheme" content="light dark">\n'
        '<meta name="supported-color-schemes" content="light dark">\n'
        '<meta name="x-apple-disable-message-reformatting">\n'
        f'<title>{_esc(betreff)}</title>\n'
        '<!--[if mso]><noscript><xml><o:OfficeDocumentSettings>'
        '<o:AllowPNG/><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript><![endif]-->\n'
        '<style type="text/css">' + stil_dunkel + mobil + '</style>\n'
        '</head>\n'
        f'<body class="dk-hintergrund" style="margin:0;padding:0;background:{h["seite"]};'
        f'-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;" bgcolor="{h["seite"]}">\n'
        f'{vor}'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="background:{h["seite"]};"><tr><td align="center" style="padding:16px 10px;">\n'
        f'<table role="presentation" class="dk-karte dk-rand" width="{breite}" cellpadding="0" cellspacing="0" '
        f'border="0" style="width:{breite}px;max-width:{breite}px;background:{h["karte"]};'
        f'border:1px solid {h["grenze"]};border-radius:{runden}px;">\n'
        + "\n".join(zeilen) +
        '\n</table>\n<p class="dk-text" style="margin:12px 0 0;font-family:' + schrift + ';'
        'font-size:11.5px;color:' + h["sekundaer"] + ';">franksfinanzcheck.de · unabhängig, '
        'provisionstransparent</p>\n</td></tr></table>\n</body>\n</html>\n')


def render_text(blocks: list[dict], *, betreff: str, konf: dict) -> str:
    """Die Textalternative: jeder Link steht drin, jede Zahl, jede Rechtszeile.
    Ein E-Mail ohne gleichwertige Textfassung verliert Leser mit abgeschaltetem
    HTML – und die Spamfilternote `text_part_missing`."""
    zeilen = [betreff, ""]
    for b in blocks:
        if b["typ"] == "kopf":
            kopf = b["titel"] + (" · " + b["ausgabe"] if b.get("ausgabe") else "")
            zeilen += [kopf + " – " + b["zeile"], b["versprechen"], ""]
        elif b["typ"] == "hero":
            if b.get("zahl"):
                zeilen.append("HEUTE RECHENBAR: " + b["zahl"])
            zeilen.append(b["text"])
            if b.get("ziel"):
                zeilen.append(GRUND_URL + "/" + str(b["ziel"]).lstrip("/"))
            zeilen.append("")
        elif b["typ"] == "artikel":
            kopf = b["titel"] if not b.get("thema") else f"{b['thema']}: {b['titel']}"
            zeilen += [kopf, GRUND_URL + "/" + str(b["url"]).lstrip("/")]
            if b.get("text"):
                zeilen.append(b["text"])
            zeilen.append("")
        elif b["typ"] == "gruss":
            zeilen += [b["text"], "— Frank · " + b["antwort"], ""]
        elif b["typ"] == "fuss":
            zeilen += ["--"]
            if b.get("naechste"):
                zeilen.append(b["naechste"])
            zeilen += [b["hinweis"],
                       "Newsletter abmelden: " + str(_marken(konf)["unsubscribe"]),
                       "Formlos abmelden: " + str(b.get("formlos") or b.get("antwort") or ""),
                       "Präferenzen: " + str(_marken(konf)["profil"]),
                       "Im Browser: " + str(_marken(konf)["mirror"]), b["anschrift"],
                       "Impressum: " + b["impressum"], "Datenschutz: " + b["datenschutz"]]
            if b.get("werbung"):
                zeilen.append(b["werbung"])
    return "\n".join(zeilen).strip() + "\n"


def _marken(konf: dict) -> dict:
    grund = {"unsubscribe": "{{unsubscribe}}", "mirror": "{{mirror}}",
             "profil": "{{update_profile}}", "datum": ""}
    grund.update((konf.get("email", {}).get("marken") or {}))
    return grund


def baue_email(material: list[dict], *, datum: datetime.date | None = None,
               root: str = BLOG_DIR, variante: int | None = None,
               versprechen: str = "") -> dict:
    """Ein Eintrag pro Ausgabe: Blocks → HTML + Text + Betreff + Preheader."""
    datum = datum or datetime.date.today()
    konf = konfiguration(root)
    if versprechen:
        konf.setdefault("capture", {})["versprechen"] = versprechen.strip()
    material = material or []
    var = betreff_varianten(material, datum, konf)
    if variante is None:
        # Rotation über den Versandtag (1 = Dienstag, 4 = Freitag): dienstags
        # führt die Zahl, freitags die Frist – redaktionell gesetzt, nicht
        # errechnet, und ohne Nutzerdaten (siehe VORZUG_VARIANTE).
        index = variante_fuer_tag(datum, var)
    else:
        index = variante % max(1, len(var))
    betreff = (var[index]["text"] if var else "FranksFinanzcheck – die Sparechnungen des Tages")
    blöcke = blocks_bauen(material, datum, konf)
    vor = preheader(material, betreff, konf, datum=datum)
    return {"datum": datum.isoformat(), "betreff": betreff, "betreff_varianten": var,
            "variante": index, "preheader": vor, "blocks": blöcke,
            "html": render_html(blöcke, betreff=betreff, vorlage_text=vor, datum=datum, konf=konf),
            "text": render_text(blöcke, betreff=betreff, konf=konf),
            # `material` trägt den Quelltext mit: nur so kann die Vor-Versand-Wache
            # die Belegpflicht der Hero-Zahl unabhängig prüfen (Q16). Der Schlüssel
            # verlässt das Repo nie – er landet in der Mail nicht, nur im Prüfvorgang.
            "material": [{k: a.get(k, "") for k in ("slug", "titel", "url", "datum", "pillar",
                                                     "quelle_text", "beschreibung")}
                         for a in material]}


def vorschau_seite(emails: list[dict], konf: dict) -> str:
    """Agentur-Übergabe an einen Menschen: das E-Mail in drei Breiten, hell und
    dunkel, ohne fremden Server – ein Frame pro Client-Klasse."""
    blocks = []
    for nr, e in enumerate(emails):
        blocks.append(
            f'<section class="vs-block"><h2>Ausgabe {e["datum"]} · Variante {nr + 1}</h2>'
            f'<p class="vs-meta"><strong>Betreff</strong> {len(e["betreff"])} Zeichen · '
            f'{_html.escape(e["betreff"])}<br><strong>Preheader</strong> '
            f'{len(e["preheader"])} Zeichen · {_html.escape(e["preheader"])}</p>'
            f'<div class="vs-breiten">'
            + "".join(f'<figure class="vs-frame vs-{b}"><figcaption>{w}</figcaption>'
                      f'<iframe title="Vorschau {b} px" srcdoc="{_html.escape(e["html"], quote=True)}"></iframe></figure>'
                      for b, w in (("mobil", "375 px · Mail-App"), ("tablet", "600 px · Gmail Web"),
                                   ("desktop", "820 px · Outlook + Paneel")))
            + '</div></section>')
    return ("<!doctype html><html lang=\"de\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>Newsletter-Vorschau</title><style>"
            ":root{--bg:#F4F6F8;--fg:#17211D;--card:#fff;--border:#DCE6E1;--accent:#0E5A43}"
            "[data-theme=dark]{--bg:#141517;--fg:#E6E7E8;--card:#1D1E20;--border:#33353A;--accent:#7FD1B4}"
            "body{margin:0;padding:24px;background:var(--bg);color:var(--fg);"
            "font:15px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif}"
            "header{display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between;margin-bottom:18px}"
            "h1{font-size:22px;margin:0}h2{font-size:16px;margin:26px 0 6px;color:var(--accent)}"
            ".vs-meta{margin:0 0 12px;font-size:13px;color:var(--fg);opacity:.8}"
            "button{padding:8px 14px;border:1px solid var(--border);border-radius:8px;background:var(--card);"
            "color:var(--fg);font-weight:600;cursor:pointer}"
            ".vs-breiten{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(300px,1fr))}"
            ".vs-frame{margin:0;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:10px}"
            ".vs-frame figcaption{font-size:12px;margin-bottom:8px;opacity:.75}"
            ".vs-frame iframe{width:100%;height:560px;border:0;background:#fff;display:block}"
            "</style></head><body><header><h1>Newsletter-Vorschau · FranksFinanzcheck</h1>"
            "<button type=\"button\" onclick=\"document.documentElement.dataset.theme="
            "document.documentElement.dataset.theme==='dark'?'':'dark'\">Hell/Dunkel</button></header>"
            + "".join(blocks) + "</body></html>")


# ------------------------------------------------------------------------- CLI
def _artikel_suchen(root: str, tage: int) -> list[dict]:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import newsletter_digest as nd            # einziger Sammler – keine zweite Liste
    return nd.live_artikel(root, datetime.date.today() - datetime.timedelta(days=max(1, tage)))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Newsletter-Studio (Marke, Blöcke, Betreff, Layout)")
    ap.add_argument("--root", default=BLOG_DIR)
    ap.add_argument("--build", action="store_true", help="E-Mail aus dem aktuellen Bestand bauen")
    ap.add_argument("--vorschau", action="store_true", help="HTML-Vorschauseite bauen")
    ap.add_argument("--brand", action="store_true", help="Marken- und Themenabgleich prüfen")
    ap.add_argument("--days", type=int, default=1)
    ap.add_argument("--datum", default="", help="ISO-Datum (Sonst heute) – für reproduzierbare Läufe")
    ap.add_argument("--variante", type=int, default=-1, help="Betreffvarianz erzwingen (0..2), -1 = Rotation")
    ap.add_argument("--out", default=os.path.join(".cache", "newsletter-studio"))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root)
    if args.selftest:
        return _selftest()
    if args.brand:
        funde, gepruefte = marken_abgleich(root)
        funde += themen_abgleich(root)
        funde += worker_basis_abgleich(root)
        funde += wrangler_themen_abgleich(root)
        messung = kontrast_pruefung(konfiguration(root))
        for m in messung:
            if not m["ok"]:
                funde.append(f"Kontrast {m['modus']}: {m['paar']} "
                             + (m.get("fehler", "") or f"{m['wert']}:1 < {m['mindest']}:1 "
                                                       f"({m.get('vorn')} auf {m.get('hinten')})"))
        if args.json:
            print(json.dumps({"funde": funde, "gepruefte_rollen": len(gepruefte),
                              "rollen": gepruefte, "kontraste": messung,
                              "token_quellen": css_tokens(root)["dateien"]},
                             ensure_ascii=False, indent=2))
        else:
            for f in funde:
                print("  ❌ " + f)
            for m in messung:
                print(f"  {'✓' if m['ok'] else '✗'} {m['modus']:6} {m['paar']:34} "
                      f"{m['wert']}:1 (Soll {m['mindest']}:1)")
            if not funde:
                print(f"✅ Marke + Themen: {len(gepruefte)} Farbrollen aus dem Build-CSS "
                      f"hergeleitet, {len(konfiguration(root).get('themen', []))} Themenwelten "
                      "deckungsgleich mit data/themenwelten.json, Capture-Endpunkt und "
                      "Worker-Themen (THEMEN_IDS/Labels) stimmen überein.")
        return 1 if funde else 0
    datum = datetime.date.fromisoformat(args.datum) if args.datum else datetime.date.today()
    material = material_aus_artikel(root, _artikel_suchen(root, args.days))
    if not material:
        print("📬 Studio: kein Material im Zeitraum – die Ausgabe bleibt leer, "
              "statt Alte[s] neu zu verpacken.")
        return 0
    e = baue_email(material, datum=datum, root=root,
                   variante=(args.variante if args.variante >= 0 else None))
    out = os.path.join(root, args.out) if not os.path.isabs(args.out) else args.out
    os.makedirs(out, exist_ok=True)
    for ende, inhalt in (("html", e["html"]), ("txt", e["text"]),
                         ("betreff.txt", "\n".join(f"{v['laenge']:>3}  {v['text']}"
                                                   for v in e["betreff_varianten"]))):
        with open(os.path.join(out, f"ausgabe-{e['datum']}.{ende}"), "w", encoding="utf-8") as fh:
            fh.write(inhalt)
    if args.vorschau:
        with open(os.path.join(out, "vorschau.html"), "w", encoding="utf-8") as fh:
            fh.write(vorschau_seite([e], konfiguration(root)))
    if args.json:
        print(json.dumps({k: e[k] for k in ("datum", "betreff", "preheader", "variante",
                                            "betreff_varianten")} |
                         {"html_bytes": len(e["html"].encode()), "dateien": out},
                     ensure_ascii=False, indent=2))
    else:
        print(f"📬 Ausgabe {e['datum']} · {len(material)} Artikel · Betreff "
              f"{len(e['betreff'])} Z. ({e['betreff_varianten'][e['variante']]['art']}) → {out}")
    return 0


# -------------------------------------------------------------------- Selbsttest
def _selftest() -> int:
    """Kein Netz, kein Repo-Schreibzugriff, kein echtes Datum (uhrfest: 97/1461
    Tage vorgestellte Uhren müssen dasselbe Ergebnis liefern)."""
    import shutil
    import tempfile
    fehler, zaehler = [], 0

    def pruefe(bedingung: bool, meldung: str) -> None:
        nonlocal zaehler
        if bedingung:
            zaehler += 1
        else:
            fehler.append(meldung)

    MAT = [{"slug": "s1", "titel": "Stromrechnung prüfen",
            "beschreibung": "Bis zu 240 € sind drin.",
            "url": "/posts/s1/", "path": "", "datum": "2026-09-22", "pillar": "strom-sparen",
            "quelle_text": "Beim Wechsel lassen sich 240 € im Jahr sparen."},
           {"slug": "s2", "titel": "DSL-Wechselbonus", "beschreibung": "Bonus: 120 €.",
            "url": "/posts/s2/", "path": "", "datum": "2026-09-22", "pillar": "internet-dsl",
            "quelle_text": "Der Bonus liegt bei 120 €."}]
    FIX = datetime.date(2026, 9, 22)          # ein Dienstag
    try:
        konf = konfiguration(BLOG_DIR)
        pruefe(bool(konf.get("design", {}).get("hell")), "Konfiguration ohne Designblock")
        # 1) Marke: echte Herleitung grün, mutierte Farbe und blinde Rolle gefunden
        funde, _rollen = marken_abgleich(BLOG_DIR)
        pruefe(funde == [], f"Markenabgleich der Live-Konfiguration meldet: {funde}")
        pruefe(len(_rollen) >= 20, f"zu wenige Farbrollen geprüft: {len(_rollen)}")
        pruefe(themen_abgleich(BLOG_DIR) == [], "Themen weichen von data/themenwelten.json ab")
        # 1b) Worker-Wachen: Live-Konfiguration grün, abweichende Wurzeln rot
        pruefe(worker_basis_abgleich(BLOG_DIR) == [],
               f"Worker-Basis-Wache meldet an Live-Repo: {worker_basis_abgleich(BLOG_DIR)}")
        pruefe(wrangler_themen_abgleich(BLOG_DIR) == [],
               f"Wrangler-Themen-Wache meldet an Live-Repo: {wrangler_themen_abgleich(BLOG_DIR)}")
        with tempfile.TemporaryDirectory(prefix="studio-worker-") as tw:
            os.makedirs(os.path.join(tw, "data"), exist_ok=True)
            open(os.path.join(tw, "hugo.toml"), "w", encoding="utf-8").write(
                "newsletterFormAction = \"https://fremd.example/anmeldung\"\n")
            open(os.path.join(tw, "data", "newsletter_studio.json"), "w", encoding="utf-8").write(
                json.dumps({"themen": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}]}))
            funde = worker_basis_abgleich(tw)
            pruefe(any("muss " + WORKER_BASIS + "/anmeldung" in f for f in funde),
                   f"fremde Basis nicht erkannt: {funde}")
            open(os.path.join(tw, "hugo.toml"), "w", encoding="utf-8").write(
                "newsletterFormAction = \"\"\n")
            pruefe(any("leer" in f for f in worker_basis_abgleich(tw)),
                   "leere Basis nicht erkannt")
            pruefe(any("nicht lesbar" in f for f in wrangler_themen_abgleich(tw)),
                   "fehlende wrangler.toml nicht erkannt")
            os.makedirs(os.path.join(tw, "newsletter-worker"), exist_ok=True)
            open(os.path.join(tw, "newsletter-worker", "wrangler.toml"), "w",
                 encoding="utf-8").write(
                'THEMEN_IDS = "a,c"\n'
                'THEMEN_LABELS = "' + json.dumps({"a": "A"}, separators=(",", ":")).replace('"', '\\"') + '"\n')
            funde = wrangler_themen_abgleich(tw)
            pruefe(any("THEMEN_IDS weicht" in f for f in funde),
                   f"ID-Drift nicht erkannt: {funde}")
            pruefe(any("THEMEN_LABELS-Keys" in f for f in funde),
                   f"Label-Drift nicht erkannt: {funde}")
        with tempfile.TemporaryDirectory(prefix="studio-brand-") as td:
            os.makedirs(os.path.join(td, "data"), exist_ok=True)
            os.makedirs(os.path.join(td, "assets", "css", "extended"), exist_ok=True)
            os.makedirs(os.path.join(td, "themes", "PaperMod", "assets", "css", "core"),
                        exist_ok=True)
            shutil.copy(os.path.join(BLOG_DIR, THEME_VARS_REL),
                        os.path.join(td, THEME_VARS_REL))
            for cf in glob.glob(os.path.join(BLOG_DIR, "assets", "css", "extended", "*.css")):
                shutil.copy(cf, os.path.join(td, "assets", "css", "extended", os.path.basename(cf)))
            mut = json.loads(json.dumps(konfiguration(BLOG_DIR)))
            mut["design"]["hell"]["text"] = "#FF0000"          # mutierte Markenfarbe
            del mut["design"]["herleitung"]["hell.zahl"]        # blinde Rolle
            del mut["design"]["herleitung"]["dunkel.zahl"]
            mut["design"]["email_eigene"]["dunkel.zahl"] = "  "   # Grund ohne Grund
            with open(os.path.join(td, "data", "newsletter_studio.json"), "w",
                      encoding="utf-8") as fh:
                json.dump(mut, fh, ensure_ascii=False)
            drift, _ = marken_abgleich(td)
            pruefe(any("widerspricht" in d for d in drift),
                   "mutierte Markenfarbe bleibt unbemerkt")
            pruefe(any("weder einen Eintrag" in d for d in drift),
                   "Farbrolle ohne Herleitung bleibt unbemerkt")
            pruefe(any("ohne Begründung" in d for d in drift),
                   "leere Ausrede für eine E-Mail-eigene Fläche bleibt unbemerkt")
        # 2) Kontrast: gemessen, nicht behauptet
        pruefe(kontrast("#FFFFFF", "#2E2E33") > 12 and kontrast("#FFFFFF", "#0E5A43") > 7,
               "Kontrastfunktion liefert unplausible Werte")
        pruefe(abs(kontrast("#777777", "#FFFFFF") - 4.48) < 0.05,
               "Kontrastfunktion weichet vom Normwert ab")
        # 3) Zahl nur mit Beleg – und nur, wenn sie eine Ersparnis ist
        z = zahl_aus_text("Beim Wechsel lassen sich 240 € im Jahr sparen.", "Der Bonus liegt bei 120 €.")
        pruefe(z["wert"] == 240 and "240" in z["beleg"], f"Hero-Zahl/Beleg falsch: {z}")
        pruefe(zahl_aus_text("kein geld")["wert"] is None, "Hero-Zahl ohne Beleg erfunden")
        pruefe(zahl_aus_text("5 € Kleingeld")["wert"] is None, "Kleinstbetrag wird zur Schlagzeile")
        pruefe(zahl_aus_text("Ein Notgroschen von 156.000 € ist nötig")["wert"] is None,
               "Vermögenszahl ohne Spar-Kontext wurde zur Tagesersparnis aufgeblasen")
        pruefe(zahl_aus_text("Preis: 400 €", kontextpflicht=False)["wert"] == 400,
               "Kontextpflicht ist nicht abschaltbar")
        pruefe(zahl_aus_text("1.800 € pro Jahr sparen")["wert"] == 1800,
               "Tausendertrennung wird nicht gelesen")
        # 4) Betreff: Länge + Varianz + Rotation
        var = betreff_varianten(MAT, FIX, konf)
        pruefe(len(var) >= 2 and all(v["laenge"] <= konf["creative"]["betreff"]["max_zeichen"] + 1
                                     for v in var), f"Betreffvarianten zu lang: {var}")
        pruefe(len({v["text"] for v in var}) == len(var), "Betreffvarianten sind Duplikate")
        a = baue_email(MAT, datum=FIX, root=BLOG_DIR)
        b = baue_email(MAT, datum=FIX + datetime.timedelta(days=1), root=BLOG_DIR)
        pruefe(a["betreff"] and b["betreff"], "Betreffrotation liefert leer")
        # 5) Blöcke → HTML + Text, alle Marken present, kein Flex/Grid
        html_a, text_a = a["html"], a["text"]
        pruefe("{{unsubscribe}}" in html_a and "{{unsubscribe}}" in text_a,
               "Abmelde-Marke {{unsubscribe}} fehlt im Template")
        pruefe("{{mirror}}" in html_a and "{{update_profile}}" in html_a,
               "Browser-/Präferenz-Marke fehlt")
        pruefe('role="presentation"' in html_a and "display:flex" not in html_a
               and "display:grid" not in html_a, "HTML-Mailsruktur: Tabellen statt Flex/Grid")
        pruefe('v:roundrect' in html_a, "Bulletproof-Button (VML) fehlt")
        pruefe(html_a.count("<img") == 0 or all("alt=" in t and "width=" in t
                                                for t in re.findall(r"<img[^>]*>", html_a)),
               "Bild ohne alt/width im E-Mail")
        for marke in ("Impressum", "Datenschutz", "Double-Opt-In"):
            pruefe(marke in html_a, f"Rechtsbaustein {marke} fehlt im E-Mail")
        pruefe("240 €" in html_a and "/posts/s1/" in html_a, "Material taucht nicht im HTML auf")
        for url in re.findall(r'<a href="([^"]+)"', html_a):
            if url.startswith(("{{", "mailto:")):
                continue
            pruefe(url.startswith("https://"), f"Relative/http-Link im E-Mail: {url}")
        pruefe(all(u in text_a for u in ("/posts/s1/", "/posts/s2/")),
               "Textfassung enthält nicht alle Links")
        # 6) uhrfest: identische Struktur an einem anderen Kalendertag
        c = baue_email(MAT, datum=datetime.date(2030, 12, 31), root=BLOG_DIR)
        pruefe([bl["typ"] for bl in c["blocks"]] == [bl["typ"] for bl in a["blocks"]],
               "Blockhierarchie hängt am Kalenderdatum")
        # 7) Vorlage mit 0 Material: kein Crash, kein leeres Versprechen
        leer = baue_email([], datum=FIX, root=BLOG_DIR)
        pruefe(leer["html"].count("<table") >= 3 and "{{unsubscribe}}" in leer["html"],
               "Leerausgabe bricht das E-Mail-Layout ab")
        # 8) Begrenzung: mehr Artikel als max_artikel werden gekappt
        viel = MAT * 4
        d = baue_email(viel, datum=FIX, root=BLOG_DIR)
        pruefe(sum(1 for bl in d["blocks"] if bl["typ"] == "artikel")
               <= int(konf["email"]["max_artikel"]),
               "Ausgabe überläuft max_artikel")
        # 9) Vorschauseite: eigenständig, kein Fremdskript
        v = vorschau_seite([a], konf)
        pruefe("<iframe" in v and "src=\"http" not in v and "cdn" not in v.lower(),
               "Vorschauseite lädt etwas Externes")
        # 10) capture(): Leerzustand ist sichtbar, nicht still
        with tempfile.TemporaryDirectory(prefix="studio-capture-") as td:
            os.makedirs(os.path.join(td, "data"), exist_ok=True)
            with open(os.path.join(td, "data", "newsletter_studio.json"), "w",
                      encoding="utf-8") as fh:
                fh.write(json.dumps({"capture": {"form_action": ""}}))
            pruefe(capture(td)["aktiv"] is False, "Leerzustand meldet sich als aktiv")
            with open(os.path.join(td, "data", "newsletter_studio.json"), "w",
                      encoding="utf-8") as fh:
                fh.write(json.dumps({"capture": {"form_action": "https://forms.beispiel.de/x"}}))
            pruefe(capture(td)["form_action"].startswith("https://"),
                   "konfigurierte Anmeldung wird nicht erkannt")
    except Exception as exc:                                   # noqa: BLE001
        import traceback
        fehler.append(f"Ausführung: {exc.__class__.__name__}: {exc}\n" + traceback.format_exc()[-500:])
    if fehler:
        print("🛑 newsletter_studio-Selbsttest FEHLGESCHLAGEN:")
        for f in fehler:
            print("  -", f)
        return 2
    print(f"✅ Studio-Selbsttest: {zaehler} Fälle grün (Marke, Kontrast, Belegpflicht, "
          f"Betreffrotation, Blockhierarchie, Marken-Syntax, Leerausgabe, Vorschau, Capture-Zustand).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
