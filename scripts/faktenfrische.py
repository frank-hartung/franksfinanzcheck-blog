#!/usr/bin/env python3
# ============================================================
#  FAKTENFRISCHE – Agent-Reach-Recherche + Claude-Fachprüfung
#  für BESTEHENDE und ZUKÜNFTIGE Blogartikel
#  ------------------------------------------------------------
#  AUFTRAG (Frank, 27.09.2026), sinngemäß wörtlich:
#    „Die bestehenden Blogartikel und zukünftigen Blogartikel
#     sollten automatisch mit Agent Reach und Claude dahingehend
#     optimiert werden, dass bei Content-Erstellung und in
#     sinnvollen Abständen eine Recherche im Internet erfolgt, um
#     die Blogartikel fachlich und inhaltlich auf Premium-Level
#     einer Profi-Agentur zu optimieren.“
#
#  EINORDNUNG (Regel genau einmal):
#    scripts/agent_reach_research.py  → BREITE Signalsammlung
#                                       (Themenplan, ein Brief/Woche)
#    DIESE Datei                      → TIEFE, artikelgenaue
#                                       Faktenrecherche + Belegkette
#    DIESE Datei                      → FACHLICHKEIT (ob es stimmt)
#    scripts/decay_radar.py           → misst Alter/Verfall
#    DIESE Datei                      → handelt: recherchiert, belegt,
#                                       meldet fachliche Befunde
#
#  WAS SIE TUT
#    1. Fälligkeit: Welche Artikel brauchen JETZT Recherche?
#       - Neu erstellt & ohne `faktencheck` → Priorität 0
#         (das ist der „bei Content-Erstellung“-Teil des Auftrags)
#       - YMYL-Artikel nach `intervalle.ymyl_tage`
#       - Saison-Artikel im Saisonfenster früher
#       - Rest nach `intervalle.standard_tage`
#    2. Recherche (NUR LESEND, Agent-Reach-Kanäle rss/web):
#       je Themenwelt kuratierte Feeds + Referenzseiten aus
#       data/agent_reach/faktenfrische.yaml, gefiltert auf die
#       Schlagworte/Keywords DES ARTIKELS.
#    3. Dossier: data/research/artikel/<slug>.md + .json
#       (datierte Fundstellen mit Quelle – prüfbar, nicht behauptet)
#    4. KI-Fachprüfung über den gemeinsamen Multi-Provider-Zugang:
#       findet veraltete Angaben und schlägt Belege vor.
#       ANTI-HALLUZINATIONS-VERTRAG: Jede von Claude genannte URL
#       muss WÖRTLICH im Dossier stehen UND auf einer Allowlist-
#       Domain liegen – sonst wird sie verworfen. Erfundene Belege
#       können dieses Skript nicht verlassen.
#    5. Anwenden (eng begrenzt, deshalb gefahrlos automatisierbar):
#       nur die Frontmatter-Felder `faktencheck` (Datum der Prüfung)
#       und `quellen` (Belegkette). Ein von publish_gate gesetzter
#       `faktenfrische:`-Hold darf nach erfolgreicher Recherche außerdem
#       ausschließlich in die Re-Queue zurückkehren – nie direkt live.
#       Der ARTIKELTEXT wird NIE automatisch umgeschrieben; fachliche
#       Befunde landen in data/faktenfrische_queue.json +
#       FAKTENFRISCHE-REPORT.md.
#       `lastmod` bleibt unangetastet (keine Frische-Inflation).
#
#  NUTZUNG
#    python3 scripts/faktenfrische.py                  # Report (trocken)
#    python3 scripts/faktenfrische.py --apply          # Belege schreiben
#    python3 scripts/faktenfrische.py --neu --apply    # nur neue Artikel
#    python3 scripts/faktenfrische.py --file <pfad>    # ein Artikel
#    python3 scripts/faktenfrische.py --offline        # ohne Netz (GEO-Reife)
#    python3 scripts/faktenfrische.py --selftest       # eingefrorene Fälle
#
#  EXIT: 0 gelaufen · 1 offene fachliche Befunde (nur --strict)
#        2 Selbsttest rot / Konfigurationsfehler
#        3 keine einzige Quelle erreichbar · 4 KI-Fachprüfung unvollständig
# ============================================================
from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import post_utils as pu  # noqa: E402
from net_safety import pruefe_url_ziel, sicherer_abruf  # noqa: E402

try:  # gemeinsamer Multi-Provider-Zugang (nur Standardbibliothek)
    import llm_client  # noqa: E402
except Exception:  # noqa: BLE001 - ohne Client läuft alles außer der Fachprüfung
    llm_client = None

# Spiegelung von routing.faktenpruefung in data/ki_transportweg.yaml.
# Gemini zuerst für Modellvielfalt; Groq, NVIDIA und Cloudflare als Fallback.
# Ein Schlüssel bedeutet keine bestätigte Erreichbarkeit oder Fachqualität.
PROVIDER_ORDER = ("gemini", "groq", "nvidia", "cloudflare")
TRANSPORT_PFAD = os.path.join(BLOG_DIR, "data", "ki_transportweg.yaml")

CONFIG_PFAD = os.path.join(BLOG_DIR, "data", "agent_reach", "faktenfrische.yaml")
DOSSIER_DIR = os.path.join(BLOG_DIR, "data", "research", "artikel")
QUEUE_PFAD = os.path.join(BLOG_DIR, "data", "faktenfrische_queue.json")
HISTORIE_PFAD = os.path.join(BLOG_DIR, "data", "faktenfrische_history.jsonl")
REPORT_PFAD = os.path.join(BLOG_DIR, "FAKTENFRISCHE-REPORT.md")

USER_AGENT = "franksfinanzcheck-faktenfrische/1.0 (Agent-Reach-Integration)"
TIMEOUT_STD = 30
MAX_ABRUF_BYTES = 2 * 1024 * 1024

# YMYL-Erkennung: Geld, Verträge, Fristen, Gesundheit/Absicherung.
YMYL_MUSTER = re.compile(
    r"versicher|kredit|zins|konto|karte|tarif|vertrag|frist|kündig|steuer|"
    r"rente|altersvorsorge|police|beitrag|geb(ü|ue)hr|strom|gas|heiz|energie|"
    r"preisgarantie|geld|budget|notgroschen|schuld",
    re.IGNORECASE)

# Saison-Erkennung: Artikel mit hartem Zeitbezug altern schneller.
SAISON_MUSTER = re.compile(
    r"heiz|winter|herbst|spätsommer|spaetsommer|jahreswechsel|stichtag|"
    r"30\.\s?11|kfz-versicherung|wechselfrist|urlaub|sommer|weihnacht",
    re.IGNORECASE)

# Eine Fundstelle zählt nur, wenn sie ein Datum ODER eine Zahl trägt:
# „Premium“ heißt belegbar, nicht bloß thematisch verwandt.
ZAHL_MUSTER = re.compile(r"\d")


# ----------------------------------------------------------------------
# Kleinkram
# ----------------------------------------------------------------------

def heute() -> dt.date:
    return dt.date.today()


def jetzt_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def lade_config(pfad: str = CONFIG_PFAD) -> dict:
    try:
        import yaml
    except ImportError:
        raise SystemExit("PyYAML fehlt: pip install pyyaml")
    if not os.path.exists(pfad):
        raise SystemExit(f"Recherche-Vertrag nicht gefunden: {pfad}")
    with open(pfad, encoding="utf-8") as fh:
        daten = yaml.safe_load(fh) or {}
    if not isinstance(daten, dict):
        raise SystemExit(f"Recherche-Vertrag ungültig (kein Mapping): {pfad}")
    return daten


def domain_von(url: str) -> str:
    try:
        netloc = urllib.parse.urlparse(url).netloc.lower()
    except ValueError:
        return ""
    return netloc[4:] if netloc.startswith("www.") else netloc


def allowlist_index(cfg: dict) -> dict:
    """{domain: {herausgeber, rang}} – die einzige Belegwahrheit."""
    index = {}
    for eintrag in cfg.get("quellen_allowlist") or []:
        domain = (eintrag.get("domain") or "").strip().lower()
        if domain:
            index[domain] = {
                "herausgeber": eintrag.get("herausgeber") or domain,
                "rang": int(eintrag.get("rang") or 3),
            }
    return index


def ist_belegfaehig(url: str, index: dict) -> dict | None:
    """Beleg nur von Allowlist-Domains (inkl. Subdomains), nur https."""
    if not url.startswith("https://"):
        return None
    dom = domain_von(url)
    if not dom:
        return None
    for erlaubt, meta in index.items():
        if dom == erlaubt or dom.endswith("." + erlaubt):
            return dict(meta, domain=erlaubt)
    return None


def yaml_quote(wert: str) -> str:
    """YAML-sicherer doppelt gequoteter Skalar (FM-Grenzen-Wache, F4)."""
    return json.dumps(str(wert), ensure_ascii=False)


# ----------------------------------------------------------------------
# Artikel lesen
# ----------------------------------------------------------------------

def fm_wert(fm: str, key: str) -> str:
    m = re.search(rf"^{re.escape(key)}:\s*(.+?)\s*$", fm, re.MULTILINE)
    if not m:
        return ""
    return m.group(1).strip().strip('"').strip("'")


def fm_liste(fm: str, key: str) -> list[str]:
    """Liest sowohl Inline-Listen (`k: ["a","b"]`) als auch Blocklisten."""
    inline = re.search(rf"^{re.escape(key)}:\s*\[(.*?)\]\s*$", fm, re.MULTILINE | re.DOTALL)
    if inline:
        return [t.strip().strip('"').strip("'") for t in inline.group(1).split(",") if t.strip()]
    block = re.search(rf"^{re.escape(key)}:\s*$\n((?:[ \t]+[-#].*\n?)+)", fm, re.MULTILINE)
    if block:
        return [re.sub(r"^\s*-\s*", "", z).strip().strip('"').strip("'")
                for z in block.group(1).splitlines() if z.strip().startswith("-")]
    return []


def datum_von(text: str) -> dt.date | None:
    if not text:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", text.strip())
    if not m:
        return None
    try:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def lade_artikel(pfad: str) -> dict | None:
    try:
        with open(pfad, encoding="utf-8") as fh:
            roh = fh.read()
    except OSError:
        return None
    _, fm, body = pu.split_article(roh)
    if not fm:
        return None
    titel = fm_wert(fm, "title")
    keywords = fm_liste(fm, "keywords") or fm_liste(fm, "tags")
    return {
        "pfad": pfad,
        "slug": os.path.basename(os.path.dirname(pfad)),
        "titel": titel,
        "beschreibung": fm_wert(fm, "description"),
        "kurzantwort": fm_wert(fm, "kurzantwort"),
        "pillar": fm_wert(fm, "pillar"),
        "keywords": keywords,
        "draft": fm_wert(fm, "draft").lower() == "true",
        "reserve": fm_wert(fm, "reserve").lower() == "true",
        "cadence_grund": fm_wert(fm, "cadence_grund"),
        "datum": datum_von(fm_wert(fm, "date")),
        "faktencheck": datum_von(fm_wert(fm, "faktencheck")),
        "quellen_vorhanden": bool(re.search(r"^quellen:\s*$", fm, re.MULTILINE)),
        "fm": fm,
        "body": body,
        "roh": roh,
    }


def alle_artikel(scope: str = "alle") -> list[dict]:
    """Bestand nach Bereich.

    `posts`  – Blogartikel (content/posts)
    `pillar` – RATGEBERSEITEN (content/pillar): die Silo-Seiten sind die
               langlebigsten YMYL-Texte des Blogs und altern am teuersten,
               weil jede interne Verlinkung auf sie zeigt.
    `alle`   – beides (Default; Auftrag 27.09.2026 nennt ausdrücklich
               „Blogartikel UND Ratgeberseiten").
    """
    treffer = []
    if scope in ("alle", "posts"):
        basis = os.path.join(BLOG_DIR, "content", "posts")
        for eintrag in sorted(os.listdir(basis)) if os.path.isdir(basis) else []:
            pfad = os.path.join(basis, eintrag, "index.md")
            if os.path.exists(pfad):
                art = lade_artikel(pfad)
                if art:
                    art["bereich"] = "artikel"
                    treffer.append(art)
    if scope in ("alle", "pillar"):
        pillar = os.path.join(BLOG_DIR, "content", "pillar")
        for eintrag in sorted(os.listdir(pillar)) if os.path.isdir(pillar) else []:
            pfad = os.path.join(pillar, eintrag, "index.md")
            if os.path.exists(pfad):
                art = lade_artikel(pfad)
                if art:
                    art["pillar"] = art["pillar"] or eintrag
                    art["bereich"] = "ratgeber"
                    treffer.append(art)
    return treffer


# ----------------------------------------------------------------------
# Fälligkeit („in sinnvollen Abständen“)
# ----------------------------------------------------------------------

def faelligkeit(art: dict, cfg: dict, stichtag: dt.date | None = None) -> dict:
    """(faellig, prio, grund, alter_tage, frist, restlaufzeit).

    DIE EINE FÄLLIGKEITSREGEL. Publish-Gate (`publish_gate.
    faktenfrische_failures`), Release-Scorecard und Deckungsrechnung lesen
    ausschließlich diese Funktion – wer sie umgeht, baut eine zweite
    Wahrheit (Lektion #521, Governance C19).

    Seit 29.10.2026 (#912) liefert sie zusätzlich die FRIST selbst
    (`frist` = letzter Prüftag + Intervall) und die Restlaufzeit in
    Tagen. Vorher rechnete die Scorecard „faktencheck + Intervall“ ein
    zweites Mal nach (§`naechste_pruefung`) – zwei Stellen, eine Zahl,
    aber zwei Chancen, sich zu unterscheiden. Jetzt gibt es die eine
    Stelle, und alle anderen lesen sie.
    """
    stichtag = stichtag or heute()
    iv = cfg.get("intervalle") or {}
    text = " ".join([art.get("titel", ""), art.get("beschreibung", ""),
                     " ".join(art.get("keywords") or []), art.get("pillar", "")])
    ymyl = bool(YMYL_MUSTER.search(text))
    saison = bool(SAISON_MUSTER.search(text))

    if saison:
        intervall = int(iv.get("saison_tage", 30))
        klasse = "saisonal"
    elif ymyl:
        intervall = int(iv.get("ymyl_tage", 45))
        klasse = "YMYL"
    else:
        intervall = int(iv.get("standard_tage", 90))
        klasse = "standard"

    if art.get("faktencheck") is None:
        if iv.get("erstrecherche_bei_erstellung", True):
            return {"faellig": True, "prio": 0, "klasse": klasse,
                    "grund": "Erstrecherche – noch nie faktengeprüft",
                    "alter_tage": None, "intervall": intervall,
                    "frist": None, "restlaufzeit": None}
        return {"faellig": False, "prio": 9, "klasse": klasse,
                "grund": "Erstrecherche abgeschaltet", "alter_tage": None,
                "intervall": intervall, "frist": None, "restlaufzeit": None}

    alter = (stichtag - art["faktencheck"]).days
    frist = art["faktencheck"] + dt.timedelta(days=intervall)
    rest = (frist - stichtag).days
    if alter >= intervall:
        return {"faellig": True, "prio": 1 if klasse != "standard" else 2,
                "klasse": klasse,
                "grund": f"{alter} Tage seit letzter Prüfung (Intervall {intervall} Tage, {klasse})",
                "alter_tage": alter, "intervall": intervall,
                "frist": frist, "restlaufzeit": rest}
    return {"faellig": False, "prio": 9, "klasse": klasse,
            "grund": f"frisch geprüft vor {alter} Tagen (Intervall {intervall} Tage)",
            "alter_tage": alter, "intervall": intervall,
            "frist": frist, "restlaufzeit": rest}


# ----------------------------------------------------------------------
# GEO-Reife (Generative Engine Optimization je Artikel)
# ----------------------------------------------------------------------

GEO_KRITERIEN = (
    ("kurzantwort", "Kurzantwort-Box (direkte Antwort für AI Overviews)"),
    ("faq", "FAQ-Abschnitt (FAQPage-Schema, Antwortmaschinen-Futter)"),
    ("quellen", "Belegkette im Frontmatter (`quellen:` → citation-Schema)"),
    ("zahlen", "Konkrete Zahlen/Euro-Beträge im Text (Zitierbarkeit)"),
    ("tabelle", "Mindestens eine Tabelle (extrahierbare Struktur)"),
    ("faktencheck", "Sichtbares Prüfdatum (`faktencheck:`)"),
)


def geo_reife(art: dict) -> dict:
    body = art.get("body") or ""
    treffer = {
        "kurzantwort": bool(art.get("kurzantwort")),
        "faq": bool(re.search(r"^#{2,3}\s*(häufige fragen|faq|fragen und antworten)",
                              body, re.IGNORECASE | re.MULTILINE)),
        "quellen": art.get("quellen_vorhanden", False),
        "zahlen": len(re.findall(r"\d+\s?(?:€|%|Euro|Prozent)", body)) >= 3,
        "tabelle": "|---" in body.replace(" ", "") or bool(re.search(r"^\|.+\|$", body, re.MULTILINE)),
        "faktencheck": art.get("faktencheck") is not None,
    }
    erfuellt = sum(1 for k, _ in GEO_KRITERIEN if treffer[k])
    return {
        "punkte": erfuellt,
        "maximum": len(GEO_KRITERIEN),
        "prozent": round(100 * erfuellt / len(GEO_KRITERIEN)),
        "offen": [beschr for k, beschr in GEO_KRITERIEN if not treffer[k]],
        "treffer": treffer,
    }


# ----------------------------------------------------------------------
# Recherche (Agent-Reach-Kanäle, NUR LESEND)
# ----------------------------------------------------------------------

def suchbegriffe(art: dict, cfg: dict) -> list[str]:
    welt = (cfg.get("themenwelten") or {}).get(art.get("pillar") or "", {})
    begriffe = list(art.get("keywords") or [])
    begriffe += list(welt.get("schlagworte") or [])
    titelworte = [w for w in re.findall(r"[A-Za-zÄÖÜäöüß]{5,}", art.get("titel", ""))]
    begriffe += titelworte[:4]
    gesehen, sauber = set(), []
    for b in begriffe:
        k = b.strip().lower()
        if k and k not in gesehen:
            gesehen.add(k)
            sauber.append(b.strip())
    return sauber[:12]


def passt(text: str, begriffe: list[str]) -> int:
    """Wie viele Suchbegriffe kommen im Text vor? (0 = kein Bezug)"""
    klein = text.lower()
    return sum(1 for b in begriffe if b.lower() in klein)


def sammle_rss(feed: dict, begriffe: list[str], limit: int) -> tuple[list[dict], str | None]:
    try:
        import feedparser
    except ImportError:
        return [], "feedparser nicht installiert (pip install feedparser)"
    name = feed.get("name") or "Feed"
    url = feed.get("url") or ""
    try:
        _status, _kopf, daten = sicherer_abruf(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT_STD,
            max_bytes=MAX_ABRUF_BYTES,
            erlaube_loopback=False,
        )
        parsed = feedparser.parse(daten)
    except ValueError as exc:
        if "Groessenlimit" in str(exc):
            return [], f"{name}: Feed überschreitet das Größenlimit"
        return [], f"{name}: Abruf fehlgeschlagen ({exc})"
    except Exception as exc:  # noqa: BLE001
        return [], f"{name}: Abruf fehlgeschlagen ({exc})"
    if getattr(parsed, "bozo", 0) and not parsed.entries:
        return [], f"{name}: Feed nicht lesbar"
    treffer = []
    for e in parsed.entries[:60]:
        titel = (e.get("title") or "").strip()
        zusammenfassung = re.sub(r"<[^>]+>", " ", e.get("summary", "") or "")[:400]
        score = passt(f"{titel} {zusammenfassung}", begriffe)
        if score == 0:
            continue
        datum = ""
        for feld in ("published", "updated"):
            if e.get(feld):
                datum = str(e[feld])[:16]
                break
        treffer.append({
            "titel": titel or "(ohne Titel)",
            "url": e.get("link", ""),
            "datum": datum,
            "quelle": name,
            "kanal": "rss",
            "auszug": zusammenfassung.strip(),
            "score": score,
        })
    treffer.sort(key=lambda t: t["score"], reverse=True)
    return treffer[:limit], None


def sammle_web(url: str, begriffe: list[str], max_zeichen: int) -> tuple[dict | None, str | None]:
    """Klartext-Lektüre über den Agent-Reach-Kanal „web" (Jina Reader)."""
    ok_ziel, ziel_grund = pruefe_url_ziel(url, erlaube_loopback=False, aufloesen=False)
    if not ok_ziel:
        return None, f"{domain_von(url)}: Ziel abgelehnt ({ziel_grund})"
    ziel = f"https://r.jina.ai/{url}"
    try:
        _status, _kopf, daten = sicherer_abruf(
            ziel,
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT_STD,
            max_bytes=MAX_ABRUF_BYTES,
            erlaube_loopback=False,
        )
        text = daten.decode("utf-8", errors="replace")
    except ValueError as exc:
        if "Groessenlimit" in str(exc):
            return None, f"{domain_von(url)}: Antwort überschreitet das Größenlimit"
        return None, f"{domain_von(url)}: Jina-Reader-Abruf fehlgeschlagen ({exc})"
    except Exception as exc:  # noqa: BLE001
        return None, f"{domain_von(url)}: Jina-Reader-Abruf fehlgeschlagen ({exc})"
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    # Nur die Absätze mit Artikelbezug – sonst ist das Dossier Rauschen.
    absaetze = [a.strip() for a in text.split("\n\n") if passt(a, begriffe) > 0]
    auszug = "\n\n".join(absaetze)[:max_zeichen] or text[:max_zeichen]
    return {
        "titel": f"Referenzseite {domain_von(url)}",
        "url": url,
        "datum": "",
        "quelle": domain_von(url),
        "kanal": "web",
        "auszug": auszug,
        "score": passt(auszug, begriffe),
    }, None


def recherchiere(art: dict, cfg: dict, offline: bool = False) -> dict:
    begriffe = suchbegriffe(art, cfg)
    welt = (cfg.get("themenwelten") or {}).get(art.get("pillar") or "")
    plan = welt or cfg.get("standard") or {}
    budget = cfg.get("budget") or {}
    max_treffer = int(budget.get("max_treffer_je_artikel", 6))
    index = allowlist_index(cfg)

    treffer: list[dict] = []
    fehler: list[str] = []
    kanaele: list[str] = []

    if offline:
        return {"begriffe": begriffe, "treffer": [], "fehler": ["offline: keine Abrufe"],
                "kanaele": [], "erzeugt": jetzt_utc()}

    for feed in plan.get("rss") or []:
        kanaele.append(f"rss:{feed.get('name')}")
        got, err = sammle_rss(feed, begriffe, max_treffer)
        treffer += got
        if err:
            fehler.append(err)

    for url in (plan.get("web") or [])[:2]:
        kanaele.append(f"web:{domain_von(url)}")
        got, err = sammle_web(url, begriffe, int(budget.get("web_max_zeichen", 1800)))
        if got:
            treffer.append(got)
        if err:
            fehler.append(err)

    # Bewertung: Allowlist-Rang schlägt Trefferzahl, Belegbarkeit schlägt Nähe.
    bewertet = []
    for t in treffer:
        meta = ist_belegfaehig(t.get("url", ""), index)
        t["belegfaehig"] = bool(meta)
        t["herausgeber"] = (meta or {}).get("herausgeber", t.get("quelle", ""))
        t["rang"] = (meta or {}).get("rang", 9)
        t["zitierbar"] = bool(ZAHL_MUSTER.search(t.get("auszug", "") + t.get("titel", "")))
        bewertet.append(t)
    bewertet.sort(key=lambda t: (t["rang"], -t["score"], not t["zitierbar"]))

    return {
        "begriffe": begriffe,
        "treffer": bewertet[:max_treffer],
        "fehler": fehler,
        "kanaele": kanaele,
        "erzeugt": jetzt_utc(),
    }


# ----------------------------------------------------------------------
# Dossier
# ----------------------------------------------------------------------

def dossier_schreiben(art: dict, dossier: dict, geo: dict, faellig: dict,
                      befunde: list[dict], trocken: bool,
                      fachpruefung: str = "unbekannt") -> str:
    os.makedirs(DOSSIER_DIR, exist_ok=True)
    basis = os.path.join(DOSSIER_DIR, art["slug"])
    zeilen = [
        f"# Faktenfrische: {art['titel']}",
        "",
        f"> Automatisch erzeugt von `scripts/faktenfrische.py` am {dossier['erzeugt']}.",
        "> Agent-Reach-Kanäle, nur lesend. Fundstellen sind Signale, keine Freigabe.",
        "",
        f"- **Artikel:** `{os.path.relpath(art['pfad'], BLOG_DIR)}`",
        f"- **Themenwelt:** {art.get('pillar') or '–'}",
        f"- **Fälligkeit:** {faellig['grund']} (Klasse: {faellig['klasse']})",
        f"- **GEO-Reife:** {geo['punkte']}/{geo['maximum']} ({geo['prozent']} %)",
        f"- **Suchbegriffe:** {', '.join(dossier['begriffe']) or '–'}",
        f"- **Kanäle:** {', '.join(dossier['kanaele']) or '–'}",
        "",
        "## Fundstellen",
        "",
    ]
    if dossier["treffer"]:
        for t in dossier["treffer"]:
            marke = "✅ belegfähig" if t.get("belegfaehig") else "· Signal"
            zeilen.append(f"### {t['titel']}")
            zeilen.append("")
            zeilen.append(f"- {marke} · Herausgeber: {t.get('herausgeber')}"
                          f"{' · ' + t['datum'] if t.get('datum') else ''}")
            zeilen.append(f"- Quelle: <{t.get('url')}>")
            if t.get("auszug"):
                zeilen.append("")
                zeilen.append("> " + t["auszug"][:600].replace("\n", "\n> "))
            zeilen.append("")
    else:
        zeilen += ["_Keine thematisch passende Fundstelle in diesem Lauf._", ""]

    zeilen += ["## Fachliche Befunde (KI-Fachprüfung)", "",
               f"Status: {fachpruefung}", ""]
    if befunde:
        for b in befunde:
            zeilen.append(f"- **{b.get('typ', 'Befund')}** – {b.get('text', '').strip()}"
                          + (f" (Beleg: <{b['beleg']}>)" if b.get("beleg") else ""))
    else:
        zeilen.append("_Keine Befunde gemeldet; Prüfstatus siehe oben._")
    zeilen += ["", "## Offene GEO-Punkte", ""]
    zeilen += [f"- {p}" for p in geo["offen"]] or ["- keine"]
    if dossier["fehler"]:
        zeilen += ["", "## Kanal-Störungen", ""] + [f"- {f}" for f in dossier["fehler"]]
    text = "\n".join(zeilen) + "\n"

    if not trocken:
        with open(basis + ".md", "w", encoding="utf-8") as fh:
            fh.write(text)
        with open(basis + ".json", "w", encoding="utf-8") as fh:
            # `default=str`: `faellig` trägt seit #912 die Frist als Datum
            # (`frist`). Ohne diesen Rückfall stirbt der ERSTE Lauf mit einem
            # echten Prüfdatum an „Object of type date is not JSON
            # serializable“ – ein Fehler, der erst in Produktion auffällt.
            json.dump({"slug": art["slug"], "titel": art["titel"], "erzeugt": dossier["erzeugt"],
                       "faellig": faellig, "geo": geo, "treffer": dossier["treffer"],
                       "befunde": befunde, "fehler": dossier["fehler"],
                       "fachpruefung": fachpruefung},
                      fh, ensure_ascii=False, indent=2, default=str)
    return basis + ".md"


# ----------------------------------------------------------------------
# KI-Fachprüfung über den gemeinsamen Multi-Provider-Zugang
# ----------------------------------------------------------------------

SYSTEM_PROMPT = """Du bist Fachprüfer einer deutschen Premium-Finanzredaktion \
(Niveau Capital/Finanztest). Du prüfst einen veröffentlichten Ratgeber gegen \
frische Recherche-Fundstellen.

HARTE REGELN:
1. Du erfindest NICHTS. Jede Aussage, die du als Beleg nutzt, muss in den \
gelieferten Fundstellen stehen.
2. Du nennst NUR URLs, die wörtlich in den Fundstellen vorkommen.
3. Du schreibst den Artikel NICHT um. Du meldest Befunde.
4. Antworte AUSSCHLIESSLICH mit einem JSON-Objekt, ohne Vorspann, ohne \
Code-Fence, in diesem Schema:
{"befunde":[{"typ":"veraltet|luecke|praezision","text":"...","beleg":"https://..."}],
 "quellen":[{"titel":"...","url":"https://...","herausgeber":"...","datum":"YYYY-MM-DD"}],
 "kurzfazit":"ein Satz"}
5. Maximal 5 Befunde, maximal 4 Quellen. Deutsche Sprache, konkret, ohne Floskeln.
6. Ein Befund ist nur dann ein Befund, wenn er dem Leser Geld, Zeit oder einen \
Fehler erspart.
7. Trenne Tatsachenbehauptungen, ausdrücklich als solche markierte \
Modellannahmen und Werbung. Modellannahmen sind keine Marktdaten; prüfe ihre \
Rechnung, Einheiten, Voraussetzungen und die Kennzeichnung, statt einen \
Quellenbeleg für frei gewählte Eingabewerte zu verlangen.
8. Eine Übersichtsseite belegt keine konkreten Prozent-, Geräte- oder \
Marktwerte. Fehlende Erwähnung ist kein Gegenbeweis: Melde gegebenenfalls \
eine Beleglücke, aber behaupte nicht, die Quelle widerlege den Artikel. \
Ein klar gekennzeichneter Affiliate-Link braucht keine behördliche Empfehlung; \
prüfe stattdessen unbelegte Preis-, Vollständigkeits- oder Empfehlungsaussagen. \
Erfinde weder ein Quellen-Publikationsdatum noch eine Quellenempfehlung.
9. Befund-Klassen aus #823 (20.10.2026) ausdrücklich mitprüfen: \
(a) Preis-Trends und Markt-Pauschalen („Neukundenpreise sind stark gesunken“, \
„nach 24 Monaten wird es massiv teurer“) sind Marktdaten – ohne Fundstelle \
sind sie veraltet oder luecke. (b) Zahlen in Marktfakten-Positur (Preise, \
Gebühren, Ersparnisse) brauchen eine Fundstelle ODER die klare Kennzeichnung \
als Modellrechnung mit frei gewählten Annahmen; fehlt beides, melde luecke. \
(c) Fehlt ein für das Thema relevanter Regulierungsrahmen, den die Fundstellen \
nahelegen (Aufsichtsbehörde, Pflichten für Unternehmen), melde luecke. \
(d) Leistungsversprechen müssen den betroffenen Mechanismus nennen und \
Systemgrenzen einräumen (Namensauflösung ist nicht Bandbreite; Router, WLAN \
und Hardware setzen Obergrenzen) – sonst praezision. (e) Anbieter-Rankings \
und Superlative ohne messbare Daten („oft die beste Wahl für hohes Tempo“) \
sind praezision-Befunde; verlange eigene Messung statt Pauschalurteil.
10. Befund-Klassen aus #911 (27.10.2026) ausdrücklich mitprüfen: \
(a) Vollständigkeits- und Vergleichsversprechen von Portalen („fast alle \
Firmen und Tarife“, „alle wichtigen Konditionen“) sind ohne Messgröße und \
Auswahlkriterium praezision; ein Portal zeigt eine Auswahl, nicht den \
gesamten Markt. (b) Verbrauchs-Schwellen als Tarifregel („ab 3.000 kWh \
Festpreis“, „unter 2.000 kWh variabel“) sind ohne Daten praezision; die \
Tarifwahl hängt vom Angebot und vom Preisrisiko ab. (c) „Kostenlos“, „keine \
Gebühr“ oder „keine Abschiedsgebühr“ nur mit Norm- oder Behördenbezug und \
genannter Zielgruppe (Haushaltskunden) – sonst luecke. (d) Sparprozente aus \
Heizverhalten brauchen Quelle und Kennzeichnung als Richtwert; \
Scheingenauigkeit („2 °C = 6 %“) und Hochrechnungen ohne Verbrauchsanteil \
sind praezision. (e) Aufsicht ist keine Preisgenehmigung: „reguliert“ oder \
„überwacht“ nicht mit „genehmigt“ verwechseln und nicht „nicht jeden Preis“ \
schreiben, wenn es keine staatliche Genehmigung gibt. (f) Behördenfristen \
(Preisänderung, Wechsel) mit Zielgruppe, Stichtag und der Abgrenzung \
zwischen technischem Prozess und Vertragskündigung nennen."""


def lade_provider_order(pfad: str = TRANSPORT_PFAD) -> tuple[str, ...]:
    """Routing aus der SSOT lesen; ungültige Konfiguration nicht kaschieren."""
    daten = lade_config(pfad)
    routing = daten.get("routing")
    eintrag = routing.get("faktenpruefung") if isinstance(routing, dict) else None
    kette = eintrag.get("kette") if isinstance(eintrag, dict) else None
    erlaubt = set(PROVIDER_ORDER)
    if (not isinstance(kette, list) or len(kette) < 2
            or any(not isinstance(p, str) or p not in erlaubt for p in kette)
            or len(set(kette)) != len(kette)
            or not any(p in ("groq", "nvidia", "cloudflare") for p in kette)):
        raise SystemExit("KI-Transportweg: ungültiges Routing für faktenpruefung")
    return tuple(kette)


def verfuegbare_anbieter() -> list:
    """Anbieter mit Schlüssel in der Reihenfolge der Transportweg-SSOT."""
    kette = lade_provider_order()
    if llm_client is None:
        return []
    return [p for p in kette if llm_client.available(p)]


def claude_fachpruefung(art: dict, dossier: dict, cfg: dict,
                        trocken: bool = False) -> tuple[list[dict], list[dict], str]:
    """Fachprüfung über den gemeinsamen LLM-Zugang des Blogs.

    Der Anti-Halluzinations-Vertrag (claude_antwort_pruefen) bleibt unverändert:
    Befunde zählen nur mit Beleg aus dem Dossier. Geändert hat sich allein der
    Transportweg – statt der nie genutzten Puter-Brücke die Schlüssel, die im
    Repo tatsächlich gesetzt sind.
    """
    ccfg = cfg.get("claude") or {}
    if trocken:
        return [], [], "übersprungen (Trockenlauf)"
    anbieter = verfuegbare_anbieter()
    if not anbieter:
        return [], [], "übersprungen (kein KI-Schlüssel: GROQ_API_KEY/GEMINI_API_KEY)"
    if not dossier["treffer"]:
        return [], [], "übersprungen (keine Fundstellen)"

    fund_text = "\n\n".join(
        f"[{i+1}] {t['titel']}\nURL: {t['url']}\nHerausgeber: {t.get('herausgeber')}"
        f"{chr(10) + 'Datum: ' + t['datum'] if t.get('datum') else ''}\n"
        f"Auszug: {t.get('auszug', '')[:900]}"
        for i, t in enumerate(dossier["treffer"]))

    user = (
        f"ARTIKEL: {art['titel']}\n"
        f"BESCHREIBUNG: {art['beschreibung']}\n"
        f"KURZANTWORT: {art.get('kurzantwort') or '–'}\n\n"
        f"ARTIKELTEXT (gekürzt):\n{art['body'][:9000]}\n\n"
        f"FRISCHE FUNDSTELLEN:\n{fund_text}\n\n"
        "Aufgabe: Nenne fachliche Befunde (veraltete Angaben, fehlende Aspekte, "
        "unpräzise Formulierungen) und belege sie ausschließlich mit den obigen URLs."
    )
    fehler = []
    for provider in anbieter:
        modell = llm_client.model_for(provider)
        try:
            antwort = llm_client.chat(
                provider, system=SYSTEM_PROMPT, prompt=user,
                temperature=float(ccfg.get("temperatur", 0.2)),
                max_tokens=int(ccfg.get("max_tokens", 4096)),
                timeout=int(ccfg.get("timeout", 30)), attempts=int(ccfg.get("versuche", 1)),
                require_complete=True, raise_on_error=True, log_errors=False)
        except Exception as exc:  # noqa: BLE001 - Lauf darf daran nicht sterben
            fehler.append(f"{provider}: {type(exc).__name__}")
            continue
        if isinstance(antwort, str) and antwort.strip():
            if _antwort_daten(antwort) is not None:
                return *claude_antwort_pruefen(antwort, dossier, cfg), f"geprüft ({provider}:{modell})"
            fehler.append(f"{provider}/{modell}: ungültiges Antwortformat")
            continue
        fehler.append(f"{provider}/{modell}: keine verwertbare Antwort")
    return [], [], "Fehler: " + "; ".join(fehler)[:300]


def _antwort_daten(rohantwort: str) -> dict | None:
    """Validiert das äußere Antwortschema; ungültig ist nicht gleich befundfrei."""
    if not isinstance(rohantwort, str):
        return None
    match = re.search(r"\{.*\}", rohantwort.strip(), re.DOTALL)
    if not match:
        return None
    try:
        daten = json.loads(match.group(0))
    except (ValueError, RecursionError):
        return None
    if (not isinstance(daten, dict)
            or not isinstance(daten.get("befunde"), list)
            or not isinstance(daten.get("quellen"), list)):
        return None
    for b in daten["befunde"]:
        if (not isinstance(b, dict) or not isinstance(b.get("text"), str)
                or not b["text"].strip()
                or any(k in b and not isinstance(b[k], str) for k in ("typ", "beleg"))):
            return None
    for q in daten["quellen"]:
        if (not isinstance(q, dict) or not isinstance(q.get("url"), str)
                or not q["url"].strip()
                or any(k in q and not isinstance(q[k], str)
                       for k in ("titel", "herausgeber", "datum"))):
            return None
    return daten


def _text(wert: object) -> str:
    return wert.strip() if isinstance(wert, str) else ""


def claude_antwort_pruefen(rohantwort: str, dossier: dict, cfg: dict) -> tuple[list[dict], list[dict]]:
    """ANTI-HALLUZINATIONS-VERTRAG.

    Verworfen wird alles, was nicht doppelt gedeckt ist:
      (a) die URL muss WÖRTLICH im Dossier stehen und
      (b) ihre Domain muss auf der Allowlist liegen.
    Damit kann keine erfundene Quelle und keine Provisionsseite in einen
    Artikel gelangen – unabhängig davon, was das Modell antwortet.
    """
    index = allowlist_index(cfg)
    erlaubte_urls = {t.get("url", "") for t in dossier.get("treffer", []) if t.get("url")}
    daten = _antwort_daten(rohantwort)
    if daten is None:
        return [], []

    befunde = []
    for b in (daten.get("befunde") or [])[:5]:
        if not isinstance(b, dict) or not _text(b.get("text")):
            continue
        beleg = _text(b.get("beleg"))
        if beleg and (beleg not in erlaubte_urls or not ist_belegfaehig(beleg, index)):
            beleg = ""   # ungedeckte URL fliegt raus, der Befund bleibt lesbar
        befunde.append({"typ": (_text(b.get("typ")) or "befund")[:20],
                        "text": _text(b["text"])[:400], "beleg": beleg})

    max_q = int((cfg.get("budget") or {}).get("max_quellen_frontmatter", 4))
    quellen, gesehen = [], set()
    fundstellen = {t.get("url"): t for t in dossier.get("treffer", []) if t.get("url")}
    if max_q <= 0:
        return befunde, quellen
    for q in (daten.get("quellen") or []):
        if not isinstance(q, dict):
            continue
        url = _text(q.get("url"))
        meta = ist_belegfaehig(url, index)
        if url not in erlaubte_urls or not meta or url in gesehen:
            continue
        gesehen.add(url)
        quellen.append({
            "titel": _text(fundstellen[url].get("titel"))[:140] or meta["herausgeber"],
            "url": url,
            "herausgeber": meta["herausgeber"][:80],
            "datum": datum_aus_feed(_text(fundstellen[url].get("datum"))),
        })
        if len(quellen) >= max_q:
            break
    return befunde, quellen


def quellen_aus_dossier(dossier: dict, cfg: dict) -> list[dict]:
    """Belegfähige Dossier-Signale; die Allowlist wird erneut geprüft.

    Ein Treffer ist kein Nachweis für eine konkrete Aussage im Artikel.
    """
    max_q = int((cfg.get("budget") or {}).get("max_quellen_frontmatter", 4))
    quellen, gesehen = [], set()
    index = allowlist_index(cfg)
    if max_q <= 0:
        return quellen
    for t in dossier.get("treffer", []):
        url = t.get("url", "")
        meta = ist_belegfaehig(url, index)
        if not t.get("belegfaehig") or not meta or url in gesehen:
            continue
        gesehen.add(url)
        quellen.append({
            "titel": t.get("titel", "")[:140],
            "url": t.get("url", ""),
            "herausgeber": meta["herausgeber"],
            "datum": (datum_aus_feed(t.get("datum", "")) or ""),
        })
        if len(quellen) >= max_q:
            break
    return quellen


def datum_aus_feed(roh: str) -> str:
    """RFC-822/ISO-Datum eines Feeds → YYYY-MM-DD (leer, wenn unklar)."""
    if not roh:
        return ""
    iso = re.match(r"(\d{4}-\d{2}-\d{2})", roh)
    if iso:
        try:
            return dt.date.fromisoformat(iso.group(1)).isoformat()
        except ValueError:
            return ""
    try:
        return email.utils.parsedate_to_datetime(roh).date().isoformat()
    except (ValueError, TypeError, OverflowError):
        return ""



# ----------------------------------------------------------------------
# Frontmatter anwenden (eng begrenzt: faktencheck + quellen)
# ----------------------------------------------------------------------

def fm_setze_faktencheck(fm: str, datum: str) -> str:
    if re.search(r"^faktencheck:\s*.*$", fm, re.MULTILINE):
        return re.sub(r"^faktencheck:\s*.*$", f"faktencheck: {datum}", fm,
                      count=1, flags=re.MULTILINE)
    return fm.rstrip("\n") + f"\nfaktencheck: {datum}"


def fm_setze_quellen(fm: str, quellen: list[dict]) -> str:
    """Schreibt einen kanonischen `quellen:`-Block (YAML-sicher)."""
    if not quellen:
        return fm
    block = ["quellen:"]
    for nr, q in enumerate(quellen, 1):
        # Stabile Quellen-ID für das YMYL-Zahlenprotokoll. Eine geprüfte Zahl
        # verweist auf Q1/Q2 statt lose auf „irgendeine Quelle im Kasten“.
        block.append(f"  - id: {yaml_quote(f'Q{nr}')}")
        block.append(f"    titel: {yaml_quote(q['titel'])}")
        block.append(f"    url: {yaml_quote(q['url'])}")
        if q.get("herausgeber"):
            block.append(f"    herausgeber: {yaml_quote(q['herausgeber'])}")
        if q.get("datum"):
            block.append(f"    datum: {yaml_quote(q['datum'])}")
    neu = "\n".join(block)
    quelle = fm + "\n"
    vorhanden = re.search(r"^quellen:[^\n]*\n(?:[ \t]+.*\n?)*", quelle, re.MULTILINE)
    if vorhanden:
        ersetzt = quelle[:vorhanden.start()] + neu + "\n" + quelle[vorhanden.end():]
        return ersetzt.rstrip("\n")
    return fm.rstrip("\n") + "\n" + neu


def _ymyl_gate():
    """Das Freigabe-Gate als einzige Regelquelle (C19). ``None`` = fail-closed."""
    try:
        import editorial_review_gate  # noqa: PLC0415 – Zyklus vermeiden
        return editorial_review_gate
    except Exception:  # noqa: BLE001 – ohne Gate wird nicht geschrieben
        return None


def artikel_anwenden(art: dict, quellen: list[dict], datum: str,
                     trocken: bool) -> list[str]:
    """Schreibt NUR Frontmatter. Body bleibt byte-identisch (Vertrag).

    YMYL-Schreibgrenze (Prüfqueue #826, 24.10.2026)
    -------------------------------------------------
    Vorher schrieb dieser Lauf ``quellen:`` aus dem Recherche-Dossier in JEDEN
    Artikel – auch in Hochrisiko-Texte. Zwei Folgen waren real:

    1. Ein *Signal* wurde zur *Belegkette*. Der verworfene Entwurf vom
       15.10.2026 trug danach genau eine „Quelle“: ``Referenzseite
       destatis.de``, ohne Datum und ohne Bezug zu einer Aussage. Das Gate
       liest ``quellen`` als Beweis – Signale gehören ins Dossier.
    2. Der Schreibvorgang lief an ``editorial_review_gate`` vorbei. Ein
       Faktenfrische-Lauf hätte damit ein vorhandenes Siegel (E17) brechen
       können, ohne dass jemand den Text angefasst hat.

    Deshalb gilt jetzt: Hochrisiko-Belegketten bleiben redaktionell (nur der
    ``faktencheck``-Stempel wird gesetzt), und jeder Schreibvorgang wird vor
    dem Schreiben gegen ``automatic_change_findings`` geprüft. Fehlt das Gate,
    wird nichts geschrieben (fail-closed) – dieselbe Lehre wie WF-54C4/#607:
    ein Schreiber ohne zugehöriges Tor ist ein Blocker-Produzent.
    """
    gate = _ymyl_gate()
    if gate is None:
        return ["ABGEBROCHEN: YMYL-Gate nicht verfügbar – fail-closed, nichts geschrieben"]
    try:
        fm_dict, _, roh_alt = gate.load_article(art["pfad"])
    except Exception as exc:  # noqa: BLE001 – unlesbar heißt: nicht schreiben
        return [f"ABGEBROCHEN: Artikel nicht auswertbar ({type(exc).__name__}) – fail-closed"]
    if "roh" in art and roh_alt != art["roh"]:
        return ["ABGEBROCHEN: Artikel seit dem Einlesen verändert – nichts geschrieben"]
    hochrisiko = gate.inferred_risk(fm_dict) == gate.RISK_HIGH

    aenderungen: list[str] = []
    schreibabsicht = False
    fm = art["fm"]
    if hochrisiko:
        if gate.automatic_write_protected(art["pfad"]):
            return ["ABGEBROCHEN: versiegelte YMYL-Freigabe – Faktenfrische schreibt nicht; "
                    "den Takt gibt der Review-Termin vor (Prüfqueue #826)"]
        aenderungen.append(
            "YMYL: Belegkette bleibt redaktionell (Signale nur im Dossier)")
    elif quellen:
        fm_neu = fm_setze_quellen(fm, quellen)
        if fm_neu != fm:
            aenderungen.append(f"quellen: {len(quellen)} Belege")
            fm = fm_neu
            schreibabsicht = True
    fm_neu = fm_setze_faktencheck(fm, datum)
    if fm_neu != fm:
        aenderungen.append(f"faktencheck: {datum}")
        fm = fm_neu
        schreibabsicht = True
    if not schreibabsicht or trocken:
        return aenderungen

    neu = pu.join_article(fm, art["body"])
    # Vertrag: der Body darf sich durch diesen Schreibvorgang nicht ändern.
    _, _, body_neu = pu.split_article(neu)
    if body_neu.strip() != art["body"].strip():
        return ["ABGEBROCHEN: Body-Drift erkannt – nichts geschrieben"]
    # YMYL-Vertrag: eine bestehende Freigabe wird nie automatisch verändert.
    gruende = gate.automatic_change_findings(roh_alt, neu)
    if gruende:
        return ["ABGEBROCHEN: " + "; ".join(gruende) + " – nichts geschrieben"]
    with open(art["pfad"], "w", encoding="utf-8") as fh:
        fh.write(neu)
    return aenderungen


def rearm_faktenfrische_hold(art: dict, beleg: str) -> bool:
    """Reife Fakten-Holds nur nach echtem Faktencheck in die Re-Queue legen.

    `publish_gate` markiert fehlende/überfällige Recherche mit dem eindeutigen
    Präfix ``faktenfrische:`` und hält den Inhalt bewusst ohne
    `cadence_wait`. Sobald dieser Lauf einen neuen Faktencheck geschrieben
    hat, darf nur diese maschinenverwaltete Hold-Klasse wieder warten; manuelle
    Entwürfe und andere redaktionelle Holds bleiben unangetastet. Es gibt
    weiterhin keinen Direkt-Publish – die Kadenz und das vollständige Gate
    entscheiden im nächsten Slot.
    """
    if not str(art.get("cadence_grund") or "").startswith("faktenfrische:"):
        return False
    try:
        import park_state
        grund = (f"faktenfrische aufgehoben: {beleg} – Re-Queue für "
                 "vollständigen Publish-Gate-Lauf")
        return bool(park_state.rearm(art["pfad"], grund))
    except Exception as exc:  # noqa: BLE001 – Hold bleibt sicher stehen
        print(f"  ⚠ Faktenfrische-Hold nicht rearmt ({art.get('slug')}): {exc}")
        return False


# ----------------------------------------------------------------------
# Report
# ----------------------------------------------------------------------

def _kapazitaet_nachrechnen(cfg: dict, artikel: list[dict], budget: int,
                            stichtag: dt.date) -> dict:
    """Deckungszahlen für Bericht/Queue – nie ein Absturz, nie ein Scheinwert."""
    try:
        import faktenfrische_kapazitaet as kapazitaet
        laeufe, _ = kapazitaet.laeufe_aus_workflow()
        if not laeufe:
            return {"nicht_beweisbar": "Laufplan (cron) nicht lesbar"}
        return kapazitaet.plan(artikel, cfg, budget, laeufe, stichtag)
    except Exception as exc:  # noqa: BLE001 – Bericht darf daran nicht sterben
        return {"nicht_beweisbar": str(exc)}


def budget_fuer_lauf(cfg: dict, artikel: list[dict], stichtag: dt.date | None = None,
                     explizit: int | None = None,
                     auto_erlaubt: bool = True) -> tuple[int, dict]:
    """Wie viele Seiten dieser Lauf schafft – gerechnet, nicht geraten.

    BEFUND #912 (29.10.2026): Das Budget war die einzige Mengengrenze des
    Bestands-Takts (3 je Lauf, zwei Läufe je Woche) und deckte 33 % des
    Bedarfs. Jede Woche wurden zwölf Seiten mehr überfällig, als geprüft
    werden konnten; die Release-Scorecard konnte deshalb nie grün werden.

    Die Heilung ist nicht „weniger messen“, sondern genug liefern: Ist
    `budget.auto_skalierung` gesetzt, nimmt der Lauf so viele Seiten, wie
    die Deckungsrechnung (`faktenfrische_kapazitaet`) für einen
    fristgerechten Abbau braucht – nie unter dem Sockel
    `max_artikel_pro_lauf`, nie über `hartes_limit_pro_lauf`.
    Ein ausdrückliches `--max` gewinnt immer (Handbetrieb, Nachweise).
    """
    vorgaben = {"max_artikel_pro_lauf": 3, "auto_skalierung": True,
                "hartes_limit_pro_lauf": 10}
    vorgaben.update({k: v for k, v in (cfg.get("budget") or {}).items()
                     if v is not None})
    sockel = max(1, int(vorgaben["max_artikel_pro_lauf"]))
    limit = max(sockel, int(vorgaben["hartes_limit_pro_lauf"]))
    if explizit:
        return max(1, int(explizit)), {"quelle": "--max", "sockel": sockel,
                                       "limit": limit, "erreicht": True}
    if not vorgaben.get("auto_skalierung") or not auto_erlaubt:
        # `--neu` (Erstellungstakt der Content-Engine) bleibt beim Sockel:
        # Dort ist die Frage „welche Seite ist neu?“, nicht „wie viel
        # Rückstand ist da?“. Ein skaliertes Budget würde nur Leerlauf
        # erzeugen – die Neu-Artikel sind ohnehin wenige.
        grund = ("Auto-Skalierung aus" if not vorgaben.get("auto_skalierung")
                 else "Erstellungstakt (--neu)")
        return sockel, {"quelle": f"Sockel ({grund})",
                        "sockel": sockel, "limit": limit, "erreicht": True}
    try:
        import faktenfrische_kapazitaet as kapazitaet
        laeufe, _hinweise = kapazitaet.laeufe_aus_workflow()
        if not laeufe:
            # Ohne lesbaren Plan keine Scheinpräzision – Sockel, laut.
            return sockel, {"quelle": "Sockel (Laufplan nicht lesbar)",
                            "sockel": sockel, "limit": limit, "erreicht": False}
        empfehlung = kapazitaet.empfohlenes_budget(
            artikel, cfg, laeufe, stichtag or heute())
    except Exception as exc:  # noqa: BLE001 – Sockel ist der sichere Fall
        return sockel, {"quelle": f"Sockel (Deckungsrechnung nicht möglich: {exc})",
                        "sockel": sockel, "limit": limit, "erreicht": False}
    return max(sockel, int(empfehlung["budget"])), {
        "quelle": "Auto-Skalierung (Deckungsrechnung)",
        "sockel": sockel, "limit": limit,
        "erreicht": bool(empfehlung["erreicht"]),
        "plan": empfehlung["plan"],
    }


def _de_zahl(wert, stellen: int = 2) -> str:
    """Deutsche Zahlenschreibweise für den Report (Lesetext, keine Daten)."""
    try:
        return f"{float(wert):.{stellen}f}".replace(".", ",")
    except (TypeError, ValueError):
        return "–"


def _report_deckung(uebersicht: dict) -> list[str]:
    """Der Abschnitt, der den Dauer-Alarm #912 erklärt hätte, bevor er kam."""
    deckung = uebersicht.get("deckung_prozent")
    if deckung is None:
        return ["_Deckung nicht berechenbar – Bedarf oder Laufplan nicht lesbar. "
                "Das ist ein Befund, kein Freibrief (fail-closed)._"]
    zeilen = [
        f"- Deckung: **{deckung:.0f} %** · Bedarf "
        f"**{_de_zahl(uebersicht.get('bedarf_je_woche', 0), 1)}** Prüfungen/Woche",
    ]
    if uebersicht.get("abbau_tage") is not None:
        zeilen.append(f"- Rückstand abgebaut in **{uebersicht['abbau_tage']} Tagen** "
                      f"(Frist {uebersicht.get('nachhol_frist_tage', 7)} Tage)")
    elif uebersicht.get("faellig"):
        zeilen.append("- Rückstand **nicht fristgerecht abbaubar** – Kadenz in "
                      "`data/agent_reach/faktenfrische.yaml` erhöhen "
                      "oder Intervall fachlich entscheiden.")
    else:
        zeilen.append("- Kein Rückstand.")
    zeilen.append("- Regel: `scripts/faktenfrische_kapazitaet.py` "
                  "(einzige Fälligkeitsregel `faktenfrische.faelligkeit`, "
                  "Governance C45).")
    return zeilen


def report_schreiben(laeufe: list[dict], uebersicht: dict, trocken: bool) -> None:
    z = [
        "# Faktenfrische-Report",
        "",
        f"> Erzeugt von `scripts/faktenfrische.py` am {jetzt_utc()}"
        f"{' (Trockenlauf)' if trocken else ''}.",
        "> Recherche: Agent Reach (nur lesend) · Fachprüfung über die",
        "> Gratis-Kette aus `data/ki_transportweg.yaml` (`routing.faktenpruefung`).",
        "> Belege nur von der Allowlist in `data/agent_reach/faktenfrische.yaml` "
        "(kein kostenpflichtiger Anbieter, keine Browser-Brücke).",
        "",
        "## Überblick",
        "",
        f"- Geprüfte Seiten im Bestand: **{uebersicht['gesamt']}** "
        f"(davon Ratgeberseiten: {uebersicht.get('ratgeber', 0)})",
        f"- Recherche-fällig: **{uebersicht['faellig']}** "
        f"(+{uebersicht.get('vorlauf', 0)} im Vorlauf)",
        f"- In diesem Lauf bearbeitet: **{uebersicht['bearbeitet']}** "
        f"(Budget {uebersicht.get('budget')}: {uebersicht.get('budget_quelle')})",
        f"- Durchschnittliche GEO-Reife: **{uebersicht['geo_schnitt']} %**",
        f"- Offene fachliche Befunde: **{uebersicht['befunde']}**",
        "",
        "## Deckung (Bedarf gegen Angebot)",
        "",
    ]
    z += _report_deckung(uebersicht)
    z += [
        "",
        "## Läufe",
        "",
        "| Seite | Bereich | Fälligkeit | Fundstellen | Belege | Befunde | GEO |",
        "|---|---|---|---|---|---|---|",
    ]
    for l in laeufe:
        z.append(f"| {l['titel'][:52]} | {l.get('bereich', 'artikel')} | "
                 f"{l['grund'][:40]} | {l['treffer']} | "
                 f"{l['quellen']} | {len(l['befunde'])} | {l['geo']} % |")
    z += ["", "## Fachliche Befunde (redaktionelle Entscheidung)", ""]
    offen = [(l, b) for l in laeufe for b in l["befunde"]]
    if offen:
        for l, b in offen:
            z.append(f"- **{l['slug']}** · {b.get('typ')}: {b.get('text')}"
                     + (f" ([Beleg]({b['beleg']}))" if b.get("beleg") else ""))
    else:
        z.append("_Keine Befunde gemeldet; der Status der Fachprüfung steht unten._")
    z += ["", "## Status der Fachprüfung", ""]
    z += [f"- {l['slug']}: {l.get('fachpruefung', 'unbekannt')}" for l in laeufe] or ["- Kein Artikel bearbeitet."]
    z += ["", "## GEO-Lücken im Bestand", ""]
    for name, anzahl in sorted(uebersicht["geo_luecken"].items(), key=lambda x: -x[1]):
        z.append(f"- {anzahl}× {name}")
    z.append("")
    with open(REPORT_PFAD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(z))


# ----------------------------------------------------------------------
# Selbsttest (eingefrorene Fälle – läuft vor JEDEM Schreibvorgang)
# ----------------------------------------------------------------------

def selftest() -> int:
    fehler = []

    def pruefe(name, ist, soll):
        if ist != soll:
            fehler.append(f"{name}: {ist!r} != {soll!r}")

    cfg = lade_config()
    index = allowlist_index(cfg)

    # ST1 – Allowlist: nur https, nur erlaubte Domains, Subdomain zählt
    pruefe("ST1a", bool(ist_belegfaehig("https://www.bundesnetzagentur.de/x", index)), True)
    pruefe("ST1b", bool(ist_belegfaehig("https://daten.destatis.de/x", index)), True)
    pruefe("ST1c", ist_belegfaehig("http://www.destatis.de/x", index), None)
    pruefe("ST1d", ist_belegfaehig("https://www.check24.de/strom/", index), None)
    pruefe("ST1e", ist_belegfaehig("https://destatis.de.evil.example/x", index), None)

    # ST2 – Fälligkeit
    basis = {"titel": "Kfz-Versicherung vergleichen", "beschreibung": "",
             "keywords": ["Kfz-Versicherung"], "pillar": "versicherungen"}
    f_neu = faelligkeit(dict(basis, faktencheck=None), cfg)
    pruefe("ST2a", (f_neu["faellig"], f_neu["prio"]), (True, 0))
    stichtag = dt.date(2026, 9, 27)
    f_frisch = faelligkeit(dict(basis, faktencheck=dt.date(2026, 9, 20)), cfg, stichtag)
    pruefe("ST2b", f_frisch["faellig"], False)
    f_alt = faelligkeit(dict(basis, faktencheck=dt.date(2026, 6, 1)), cfg, stichtag)
    pruefe("ST2c", f_alt["faellig"], True)
    f_std = faelligkeit({"titel": "Aufräumen mit System", "beschreibung": "",
                         "keywords": ["Ordnung"], "pillar": "",
                         "faktencheck": dt.date(2026, 8, 1)}, cfg, stichtag)
    pruefe("ST2d", (f_std["klasse"], f_std["faellig"]), ("standard", False))

    # ST3 – Anti-Halluzination: erfundene und nicht gedeckte URLs fliegen raus
    dossier = {"treffer": [{"url": "https://www.destatis.de/echt", "titel": "Echt"}]}
    antwort = json.dumps({
        "befunde": [{"typ": "veraltet", "text": "Zahl X ist alt",
                     "beleg": "https://www.erfunden.example/quelle"}],
        "quellen": [
            {"titel": "Erfunden", "url": "https://www.erfunden.example/q",
             "herausgeber": "X", "datum": "2026-01-01"},
            {"titel": "Echt", "url": "https://www.destatis.de/echt",
             "herausgeber": "Statistisches Bundesamt", "datum": "2026-09-01"},
        ]})
    befunde, quellen = claude_antwort_pruefen(antwort, dossier, cfg)
    pruefe("ST3a", len(befunde), 1)
    pruefe("ST3b", befunde[0]["beleg"], "")
    pruefe("ST3c", [q["url"] for q in quellen], ["https://www.destatis.de/echt"])

    # ST4 – Frontmatter: YAML-sicher, idempotent, Body unberührt
    fm = 'title: "Test"\ndate: 2026-09-01\n'
    q = [{"titel": 'Preis: "hoch"', "url": "https://www.destatis.de/x",
          "herausgeber": "Statistisches Bundesamt", "datum": "2026-09-01"}]
    fm1 = fm_setze_quellen(fm, q)
    fm1 = fm_setze_faktencheck(fm1, "2026-09-27")
    fm2 = fm_setze_faktencheck(fm_setze_quellen(fm1, q), "2026-09-27")
    pruefe("ST4a", fm2, fm1)
    pruefe("ST4b", fm1.count("faktencheck:"), 1)
    try:
        import yaml
        geparst = yaml.safe_load(fm1)
        pruefe("ST4c", geparst["quellen"][0]["titel"], 'Preis: "hoch"')
        pruefe("ST4d", str(geparst["faktencheck"]), "2026-09-27")
    except ImportError:
        pass

    # ST5 – GEO-Reife zählt, was Antwortmaschinen brauchen
    reif = geo_reife({"kurzantwort": "Ja.", "quellen_vorhanden": True,
                      "faktencheck": dt.date(2026, 9, 1),
                      "body": "## Häufige Fragen\n\n| a | b |\n|---|---|\n"
                              "10 € sparen, 20 % mehr, 30 Euro weniger"})
    pruefe("ST5a", reif["punkte"], 6)
    mager = geo_reife({"kurzantwort": "", "quellen_vorhanden": False,
                       "faktencheck": None, "body": "Text ohne alles."})
    pruefe("ST5b", mager["punkte"], 0)

    # ST6 – Feed-Datum
    pruefe("ST6a", datum_aus_feed("Fri, 26 Sep 2026 08:00"), "2026-09-26")
    pruefe("ST6b", datum_aus_feed("2026-09-26T08:00"), "2026-09-26")
    pruefe("ST6c", datum_aus_feed(""), "")

    # ST7 – Bereiche: Ratgeberseiten sind Teil des Bestands und als solche
    # erkennbar (Auftrag 27.09.2026: Blogartikel UND Ratgeberseiten).
    nur_pillar = alle_artikel("pillar")
    nur_posts = alle_artikel("posts")
    pruefe("ST7a", bool(nur_pillar) and all(a["bereich"] == "ratgeber" for a in nur_pillar), True)
    pruefe("ST7b", bool(nur_posts) and all(a["bereich"] == "artikel" for a in nur_posts), True)
    pruefe("ST7c", len(alle_artikel("alle")), len(nur_pillar) + len(nur_posts))

    if fehler:
        print("🛑 Selbsttest FAKTENFRISCHE rot:")
        for f in fehler:
            print("   -", f)
        return 2
    print("✅ Selbsttest Faktenfrische: 23/23 Fälle grün.")
    return 0


# ----------------------------------------------------------------------
# Hauptlauf
# ----------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description="Faktenfrische: Agent-Reach-Recherche + Claude-Fachprüfung")
    p.add_argument("--apply", action="store_true",
                   help="Belegkette (`quellen`) und `faktencheck` ins Frontmatter schreiben")
    p.add_argument("--neu", action="store_true",
                   help="nur Artikel ohne `faktencheck` (Content-Erstellung)")
    p.add_argument("--file", help="genau diesen Artikel prüfen (Pfad zur index.md)")
    p.add_argument("--max", type=int, help="Budget je Lauf überschreiben")
    p.add_argument("--scope", choices=("alle", "posts", "pillar"), default="alle",
                   help="Bereich: posts = Blogartikel, pillar = Ratgeberseiten, "
                        "alle = beides (Default)")
    p.add_argument("--offline", action="store_true", help="ohne Netzabruf (nur GEO-Reife)")
    p.add_argument("--strict", action="store_true", help="Exit 1 bei offenen Befunden")
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args()

    if args.selftest:
        return selftest()
    if args.max is not None and args.max < 1:
        p.error("--max muss mindestens 1 sein")

    # Sabotage-Schutz: kein Schreibvorgang ohne grünen Selbsttest.
    if args.apply and selftest() != 0:
        return 2

    cfg = lade_config()
    stichtag = heute()

    if args.file:
        art = lade_artikel(args.file)
        if not art:
            print(f"🛑 Artikel nicht lesbar: {args.file}", file=sys.stderr)
            return 2
        bestand = [art]
    else:
        bestand = alle_artikel(args.scope)

    budget, budget_info = budget_fuer_lauf(cfg, bestand, stichtag, args.max,
                                           auto_erlaubt=not args.neu)
    vorlauf = int((cfg.get("planung") or {}).get("vorlauf_tage", 7))

    # Reserve-/Entwurfsartikel zählen als „neu“ – sie sollen VOR der
    # Veröffentlichung ihre Erstrecherche bekommen.
    kandidaten = []
    vorlauf_kandidaten = []
    geo_luecken: dict[str, int] = {}
    geo_werte = []
    for art in bestand:
        geo = geo_reife(art)
        geo_werte.append(geo["prozent"])
        for luecke in geo["offen"]:
            geo_luecken[luecke] = geo_luecken.get(luecke, 0) + 1
        f = faelligkeit(art, cfg, stichtag)
        art["_geo"], art["_faellig"] = geo, f
        if args.neu and art.get("faktencheck") is not None:
            continue
        if f["faellig"]:
            kandidaten.append(art)
        elif (f.get("restlaufzeit") is not None
              and f["restlaufzeit"] <= vorlauf):
            # VORLAUF (#912): Eine Seite wird arbeitbar, bevor sie fällig
            # wird. Wer erst am Stichtag anfängt, arbeitet an einer roten
            # Scorecard. Der Vorlauf ist kein zweiter Fälligkeitsbegriff –
            # „fällig“ bleibt `faellig`, hier wird nur früher gearbeitet.
            vorlauf_kandidaten.append(art)

    # Reihenfolge: EDF (früheste Frist zuerst) → Erstrecherche vor allem
    # → Ratgeber-Silo vor Einzelartikel (eine Silo-Seite trägt die interne
    # Verlinkung vieler Artikel) → Slug als stabiler letzter Schlüssel.
    #
    # WARUM EDF (Reparatur #912): Die alte Reihenfolge sortierte nach
    # Prioritätsklasse (saisonal/YMYL vor standard). Bei dauerhaftem
    # Rückstand verhungerten die Standard-Seiten (90 Tage) unbegrenzt,
    # obwohl sie längst überfällig waren – die Klasse war stärker als die
    # Frist. Earliest-Deadline-First ist die Reihenfolge, die nachweislich
    # die wenigsten Fristen reißt, und sie macht Verhungern unmöglich.
    def _edf(a: dict):
        frist = a["_faellig"].get("frist")
        return (0 if a["_faellig"]["prio"] == 0 else 1,
                frist or dt.date.min,
                a["_faellig"]["prio"],
                0 if a.get("bereich") == "ratgeber" else 1,
                a.get("slug") or "")

    arbeitsvorrat = sorted(kandidaten + vorlauf_kandidaten, key=_edf)
    auswahl = arbeitsvorrat[:budget]

    print(f"Faktenfrische: {len(bestand)} Artikel im Blick · {len(kandidaten)} fällig · "
          f"{len(vorlauf_kandidaten)} im Vorlauf ({vorlauf} Tage) · "
          f"{len(auswahl)} in diesem Lauf (Budget {budget}, {budget_info['quelle']})"
          + (" · OFFLINE" if args.offline else ""))

    laeufe, befunde_gesamt, unvollstaendig = [], 0, []
    for art in auswahl:
        print(f"\n▸ {art['titel'][:70]}\n  Fälligkeit: {art['_faellig']['grund']}")
        dossier = recherchiere(art, cfg, offline=args.offline)
        print(f"  Fundstellen: {len(dossier['treffer'])}"
              + (f" · Störungen: {len(dossier['fehler'])}" if dossier["fehler"] else ""))

        befunde, claude_quellen, status = claude_fachpruefung(
            art, dossier, cfg, trocken=args.offline)
        print(f"  KI-Fachprüfung: {status}")
        quellen = claude_quellen or quellen_aus_dossier(dossier, cfg)

        aenderungen = []
        geprueft = status.startswith("geprüft (")
        if args.apply and not args.offline and (not geprueft or not quellen):
            unvollstaendig.append(art)
            print("  ⚠ Fachprüfung oder belegfähige Quelle fehlt – Artikel bleibt unverändert.")
        if args.apply and quellen and geprueft:
            aenderungen = artikel_anwenden(art, quellen, heute().isoformat(), trocken=False)
            if any(a.startswith("ABGEBROCHEN:") for a in aenderungen):
                unvollstaendig.append(art)
            for a in aenderungen:
                print(f"  ✍ {a}")
            if any(a.startswith("faktencheck:") for a in aenderungen):
                if rearm_faktenfrische_hold(art, "; ".join(aenderungen)):
                    aenderungen.append("faktenfrische-Hold: Re-Queue aktiviert")
                    print("  ♻ Faktenfrische-Hold: Re-Queue aktiviert (kein Direkt-Publish)")
        elif quellen and not args.apply:
            print(f"  (Trockenlauf) {len(quellen)} Belege bereit – mit --apply schreiben")

        dossier_schreiben(art, dossier, art["_geo"], art["_faellig"], befunde,
                          trocken=False, fachpruefung=status)
        befunde_gesamt += len(befunde)
        laeufe.append({
            "slug": art["slug"], "titel": art["titel"],
            "bereich": art.get("bereich", "artikel"),
            "grund": art["_faellig"]["grund"], "treffer": len(dossier["treffer"]),
            "quellen": len(quellen), "befunde": befunde,
            "geo": art["_geo"]["prozent"], "fehler": dossier["fehler"],
            "fachpruefung": status,
            "aenderungen": aenderungen,
        })

    # Deckungsnachweis für Bericht und Queue: EINE Rechnung, zwei Leser.
    kapazitaet = budget_info.get("plan") or _kapazitaet_nachrechnen(
        cfg, bestand, budget, stichtag)

    uebersicht = {
        "gesamt": len(bestand),
        "ratgeber": sum(1 for a in bestand if a.get("bereich") == "ratgeber"),
        "faellig": len(kandidaten),
        "vorlauf": len(vorlauf_kandidaten),
        "bearbeitet": len(auswahl),
        "budget": budget,
        "budget_quelle": budget_info.get("quelle"),
        "geo_schnitt": round(sum(geo_werte) / len(geo_werte)) if geo_werte else 0,
        "befunde": befunde_gesamt,
        "geo_luecken": geo_luecken,
        "deckung_prozent": kapazitaet.get("deckung_prozent"),
        "bedarf_je_woche": kapazitaet.get("bedarf_je_woche"),
        "abbau_tage": kapazitaet.get("abbau_tage"),
        "nachhol_frist_tage": kapazitaet.get("nachhol_frist_tage"),
    }
    report_schreiben(laeufe, uebersicht, trocken=not args.apply)

    with open(QUEUE_PFAD, "w", encoding="utf-8") as fh:
        json.dump({"erzeugt": jetzt_utc(), "uebersicht": uebersicht,
                   "kapazitaet": kapazitaet,
                   "offen": [{"slug": a["slug"], "titel": a["titel"],
                              "grund": a["_faellig"]["grund"],
                              "faellig": bool(a["_faellig"]["faellig"]),
                              "frist": (a["_faellig"]["frist"].isoformat()
                                        if a["_faellig"].get("frist") else None),
                              "geo": a["_geo"]["prozent"]}
                             for a in unvollstaendig + arbeitsvorrat[budget:]],
                   "laeufe": laeufe}, fh, ensure_ascii=False, indent=2)

    if laeufe:
        with open(HISTORIE_PFAD, "a", encoding="utf-8") as fh:
            for l in laeufe:
                fh.write(json.dumps({"zeit": jetzt_utc(), **{k: v for k, v in l.items()
                                                             if k != "befunde"},
                                     "befunde": len(l["befunde"])},
                                    ensure_ascii=False) + "\n")

    print(f"\nGEO-Reife im Bestand: {uebersicht['geo_schnitt']} % · "
          f"Report: {os.path.relpath(REPORT_PFAD, BLOG_DIR)}")

    alle_kanaele_tot = bool(auswahl) and all(
        l["treffer"] == 0 and l["fehler"] for l in laeufe)
    if alle_kanaele_tot and not args.offline:
        print("⚠ Keine einzige Quelle erreichbar – Kanalmatrix prüfen.", file=sys.stderr)
        return 3
    if args.apply and unvollstaendig:
        print("⚠ Recherche oder Schreibvorgang unvollständig – betroffene Artikel bleiben in der Queue.",
              file=sys.stderr)
        return 4
    if args.strict and befunde_gesamt:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
