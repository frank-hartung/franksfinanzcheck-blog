#!/usr/bin/env python3
# ============================================================
#  ZEIT-NIVEAU-RECHTSCHREIB-WACHE
#  Dauerhafte Premium-Rechtschreibprüfung für FranksFinanzcheck
# ============================================================
"""
AUFTRAG (Frank, 28.09.2026): „Integriere dauerhaft eine professionelle
automatische Rechtschreibprüfung von zeit.de auf Premium-Level einer
Profi-Agentur in meinen Blog.“

FAKTENLAGE (geprüft 28.09.2026, ausführlich im Onboarding-Report
ZEIT-RECHTSCHREIBUNG-PREMIUM-2026-09-28.md):
  - zeit.de betreibt KEINE öffentlich dokumentierte Rechtschreib-API für
    Dritte. „ZEIT-Niveau“ ist in diesem Repo die vereinbarte Qualitätslatte
    (CLAUDE.md: „sprachlich mindestens auf dem Niveau von ZEIT.de“).
  - Technisch greifbar ist genau diese Verlags-Qualität über die
    LanguageTool-/v2/check-kompatible HTTP-API: der Branchen-Standard für
    deutsche Verlage und Agenturen (EU-Server, DSGVO-Ordnung), u. a. die
    Engine hinter den als „ZEIT-ähnlich“ bekannten Online-Prüfern
    (rechtschreibpruefung24 PLUS/Premium ist selbst LanguageTool-Partner).
  - Der ÖFFENTLICHE Gratis-Endpunkt (api.languagetool.org) untersagt
    automatisierte Massenabfragen ausdrücklich („Do not send automated
    requests“). Darum ist er hier KEIN Dauerbetrieb, sondern nur der
    opt-in Manuelmodus. Dauer-Premium = eigener Enterprise-Zugang
    (username+apiKey) ODER eigene Instanz (kostenlos selbst gehostet).

PROVIDER-KETTE (fail-open Richtung Qualität, nie stumm):
  1) PREMIUM  – ENV ZR_API_URL (+ZR_USERNAME/ZR_API_KEY) ODER nur
                ZR_USERNAME+ZR_API_KEY gegen den Standard-Enterprise-
                Endpunkt. Volle Fehler-Abdeckung, höhere Limits,
                isPremium-Funde.
  2) ÖFFENTLICH – nur mit --oeffentlich (ToS: keine Automation, harte
                Drosselung, 20 KB/Anfrage, 75 KB+20 Anfragen/Minute Peak).
  3) OFFLINE    – deterministische Repo-Engine (grammar_check.py,
                LanguageTool-Nachbau LT1–LT4, 100 % lokal).
  „Dauerhaft“ heißt hier: Die Wache meldet in JEDEM Modus Befund oder
  Freispruch – ein Provider-Ausfall wird als Provider-Meldung sichtbar,
  niemals als Schein-Grün.

KOSTEN-REGEL (Dauervorgabe Frank, 08.09.2026, vgl. data/ki_redaktion.yaml):
  Kein Paid-Provider als alleiniger Pfad. require_online=true in der
  Konfiguration löst Exit 2 aus (Selbsttest ST8 nagelt das fest).

SCHREIBVERTRAG (wie sprachkern/grammar_check):
  - Auto-Fix NUR bei harter Allowlist: Issue-Typ misspelling/typographical,
    Regel-ID in auto_fix.rules, GENAU ein Ersatz-Vorschlag, Fund ohne
    Zeilenumbruch/Weiche Trennstelle, Zone fließtext|description.
  - Titel/keywords/tags/pin_*: NIE schreiben (Cover-Marken-Lock).
  - Schutzzonen (Code, Links inkl. Ankertext, Shortcodes, URLs, HTML,
    Tabellen-Separatoren, Markdown-Marker) werden längentreu maskiert
    und können per Konstruktion nicht getroffen werden.
  - Jeder Schreibvorgang läuft über sprachkern.write_verified
    (Link-/Shortcode-/Überschriften-Wächter) + Kontext-Probe am Offset.
  - Selbsttest läuft vor JEDEM --fix; Abweichung = Exit 2, keine Datei
    wird angefasst.

NUTZUNG:
  python3 scripts/zeit_rechtschreibung.py               # Prüfung + Report
  python3 scripts/zeit_rechtschreibung.py --fix         # Allowlist-Fixes anwenden
  python3 scripts/zeit_rechtschreibung.py --offline     # nur lokale Engine
  python3 scripts/zeit_rechtschreibung.py --oeffentlich # öffentlicher Gratis-Endpunkt (nur manuell!)
  python3 scripts/zeit_rechtschreibung.py --probe       # Provider-Gesundheit prüfen
  python3 scripts/zeit_rechtschreibung.py --file X.md   # einzelner Artikel
  python3 scripts/zeit_rechtschreibung.py --file X.md --include-drafts
  python3 scripts/zeit_rechtschreibung.py --new-only    # nur Artikel von heute
  python3 scripts/zeit_rechtschreibung.py --json        # maschinenlesbar
  python3 scripts/zeit_rechtschreibung.py --selftest    # Sabotage-Schutz (offline)
  python3 scripts/zeit_rechtschreibung.py --strict      # Exit 1 bei offenen Funden
  python3 scripts/zeit_rechtschreibung.py --refresh     # Cache ignorieren

AUSGABE:
  ZEIT-RECHTSCHREIBUNG-REPORT.md        (gitignored, /*-REPORT.md)
  .zeit_rechtschreibung_report.json     (gitignored, Sicht für Automatisierung)
  data/zeit_rechtschreibung_history.jsonl   (versioniert, Dedupe pro Tag)
  data/zeit_rechtschreibung_cache.json      (versioniert, Quoten-Schutz)

Exit 0 = gelaufen · Exit 1 = offene Funde (nur --strict) ·
Exit 2 = Selbsttest/Konfiguration rot · Exit 3 = Online-Betrieb gefordert,
aber nicht verfügbar
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sprachkern import (  # noqa: E402
    ROOT, load_articles, rebuild, write_verified, now_utc,
)

ENGINE_VERSION = "1.0.0"
ENGINE_NAME = "zeit_rechtschreibung"

REPORT_FILE = os.path.join(ROOT, "ZEIT-RECHTSCHREIBUNG-REPORT.md")
JSON_FILE = os.path.join(ROOT, ".zeit_rechtschreibung_report.json")
CONFIG_FILE = os.path.join(ROOT, "data", "zeit_rechtschreibung.json")

STANDARD_API_URL = "https://api.languagetool.org/v2/check"
PRODUKT_NAME = "LanguageTool-kompatibler Premium-Prüfdienst (v2/check)"

# ------------------------------------------------------------ Konfiguration
DEFAULT_CONFIG = {
    "version": 1,
    "name": "ZEIT-Niveau-Rechtschreib-Wache",
    "anbieter": {
        "produkt": PRODUKT_NAME,
        "api_url_umgebung": ["ZR_API_URL", "LT_API_URL"],
        "benutzer_umgebung": ["ZR_USERNAME", "LT_USERNAME"],
        "schluessel_umgebung": ["ZR_API_KEY", "LT_API_KEY", "LT_APIKEY"],
        "standard_api_url": STANDARD_API_URL,
        "require_online": False,
        "offline_fallback": True,
    },
    "anfrage": {
        "language": "de-DE",
        "motherTongue": "de-DE",
        "level": "picky",
        "timeout_s": 60,
        "versuche": 3,
        "chunk_zeichen": 9000,
        "chunk_zeichen_premium": 15000,
        # Öffentlicher Endpunkt: ToS verbieten Automation; auch manuell
        # großzügig gedrosselt (20 Anfragen/Min, 75 KB/Min, 20 KB/Anfrage).
        "min_intervall_oeffentlich_s": 4.0,
        "min_intervall_premium_s": 0.6,
        "max_anfragen_pro_lauf": 120,
        "max_anfragen_oeffentlich": 40,
    },
    "auto_fix": {
        "issue_types": ["misspelling", "typographical"],
        # Nur Regel-IDs mit unzweideutigem, mechanischem Ersatz.
        # Stil-/Komma-/Semantik-Regeln bleiben IMMER Agentur-Hand (Mensch).
        "regeln": [
            "GERMAN_SPELLER_RULE",
            "UPPERCASE_SENTENCE_START",
            "DOUBLE_PUNCTUATION",
            "WHITESPACE_RULE",
            "COMMA_PARENTHESIS_WHITESPACE",
            "GERMAN_WORD_REPEAT_RULE",
        ],
        "nur_ein_vorschlag": True,
        "max_fund_zeichen": 60,
        "zonen": ["fluesstext", "description"],
    },
    "ignorieren": {
        "regeln": [],
        "kategorien": [],
    },
    "whitelist_dateien": [
        "data/spellcheck_whitelist.txt",
        "data/grammar_whitelist.txt",
    ],
    "history": {"pfad": "data/zeit_rechtschreibung_history.jsonl", "max": 500},
    "cache": {"pfad": "data/zeit_rechtschreibung_cache.json",
              "aktiv": True, "max": 400},
}


class KonfigFehler(Exception):
    """Konfiguration verstößt gegen eine Dauervorgabe (z. B. Kosten-Regel)."""


def _merge(basis: dict, overlay: dict) -> dict:
    out = dict(basis)
    for k, v in overlay.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: str | None = None) -> dict:
    cfg = DEFAULT_CONFIG
    p = path or CONFIG_FILE
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            disk = json.load(fh)
        cfg = _merge(DEFAULT_CONFIG, disk)
    pruefe_konfig(cfg)
    return cfg


def pruefe_konfig(cfg: dict) -> None:
    """Dauervorgaben hart prüfen (Kosten-Regel: kein Paid-Only-Pfad)."""
    if cfg.get("anbieter", {}).get("require_online"):
        raise KonfigFehler(
            "require_online=true verstößt gegen die Kosten-/Dauer-Regel: "
            "Kein Paid- oder Netz-Provider darf alleiniger Prüfpfad sein."
        )
    if not cfg.get("anbieter", {}).get("offline_fallback", True):
        raise KonfigFehler(
            "offline_fallback=false abgeschaltet – die Dauerprüfung hätte "
            "keinen netzfreien Notpfad mehr (verboten seit 28.09.2026)."
        )


def _env(name_liste) -> str:
    for n in name_liste or []:
        v = os.environ.get(n, "").strip()
        if v:
            return v
    return ""


def zugang_ermitteln(cfg: dict, oeffentlich: bool) -> dict:
    """Ermittelt den Provider-Modus. Liefert dict mit modus/api_url/keys."""
    anb = cfg.get("anbieter", {})
    basis_umg = _env(anb.get("api_url_umgebung"))
    benutzer = _env(anb.get("benutzer_umgebung"))
    schluessel = _env(anb.get("schluessel_umgebung"))
    if basis_umg or (benutzer and schluessel):
        return {
            "modus": "premium",
            "api_url": basis_umg or anb.get("standard_api_url", STANDARD_API_URL),
            "benutzer": benutzer, "schluessel": schluessel,
            "grund": ("eigener Endpunkt" if basis_umg
                      else "Enterprise-Zugang (Benutzer+Schlüssel)"),
        }
    if oeffentlich:
        return {
            "modus": "oeffentlich",
            "api_url": anb.get("standard_api_url", STANDARD_API_URL),
            "benutzer": "", "schluessel": "",
            "grund": "öffentlicher Gratis-Endpunkt (ToS: NUR gelegentliche "
                     "manuelle Nutzung, gedrosselt)",
        }
    return {"modus": "offline", "api_url": "", "benutzer": "",
            "schluessel": "",
            "grund": "kein Premium-Zugang konfiguriert und --oeffentlich "
                     "nicht gesetzt – lokale Engine (deterministisch)"}


# ------------------------------------------------------------ Maskierung
# Längentreue Maskierung: Aus jedem geschützten Bereich werden Leerzeichen
# (Zeilenumbrüche bleiben Zeilenumbrüche) – Offsets und Zeilennummern bleiben
# exakt gültig, und der Prüfdienst sieht NUR Text, der wirklich Fließtext ist.
MASK_RX = re.compile(
    r"(```.*?```)"                       # Code-Block
    r"|(`[^`\n]+`)"                      # Inline-Code
    r"|(\{\{[<%].*?[>%]\}\})"            # Hugo-Shortcodes
    r"|(<!--.*?-->)"                     # HTML-Kommentare
    r"|(</?[A-Za-z][^>\n]*>)"            # HTML-Tags
    r"|(https?://[^\s)\"']+)"            # absolute URLs
    r"|((?:\.\.?/)+[^\s)\"'<>\x27]+)"    # relative Pfade
    r"|(!?\[[^\]]*\]\([^)]*\))"          # MD-Links & Bilder inkl. Ankertext
    r"|(&nbsp;|&amp;|&lt;|&gt;|&quot;|&#\d+;|&[a-z]+;)"  # Entities
    r"|(^\s{0,3}(?:\|?\s*:?-{2,}:?\s*)+\|?\s*$)"         # Tabellen-Separator
    r"|(^\s{0,3}#{1,6}\s+)"              # Überschriften-Marker (Text bleibt)
    r"|(^\s{0,3}>\s?)"                   # Zitat-Marker
    r"|(^\s{0,3}(?:[-*+]|\d+[.)])(?=\s))"                # Listen-Marker
    r"|(\|)"                             # Tabellen-Pipes
    r"|(\*{1,3}|_{1,2}|~~)",             # Fett/Kursiv/Durchgestrichen-Marker
    re.S | re.M,
)


def _zu_leerzeichen(s: str) -> str:
    return "".join("\n" if c == "\n" else " " for c in s)


def maskiere(text: str) -> str:
    """Ersetzt Schutzzonen durch längentreues Weiß – Offsets bleiben gültig."""
    return MASK_RX.sub(lambda m: _zu_leerzeichen(m.group(0)), text)


# ------------------------------------------------------------ Chunking
ABSATZ_RX = re.compile(r"\n[ \t]*\n")
SATZENDE_RX = re.compile(r"(?<=[.!?…])\s+")


def chunken(text: str, limit: int) -> list:
    """Zerteilt Text in Blöcke ≤ limit. Liefert [(basis_offset, chunk)].
    Grenzen: 1. Absatz, 2. Satzende, 3. harte Trennung (Qualitätsnotiz)."""
    if len(text) <= limit:
        return [(0, text)] if text else []
    bloecke = []          # (offset, text)
    # 1) Absatz-Raster
    start = 0
    for m in ABSATZ_RX.finditer(text):
        bloecke.append((start, text[start:m.end()]))
        start = m.end()
    bloecke.append((start, text[start:]))

    # 2) zu große Absätze nach Satzenden splitten
    fein = []
    for off, blk in bloecke:
        if len(blk) <= limit:
            fein.append((off, blk))
            continue
        pos = 0
        while pos < len(blk):
            rest = blk[pos:pos + limit]
            if pos + limit >= len(blk):
                fein.append((off + pos, blk[pos:]))
                break
            schnitt = None
            for sm in SATZENDE_RX.finditer(blk[pos:pos + limit]):
                if sm.end() > limit * 0.5:
                    schnitt = sm.end()
            if schnitt is None:
                schnitt = limit
            fein.append((off + pos, blk[pos:pos + schnitt]))
            pos += schnitt

    # 3) Akkumulieren, bis das Limit erreicht ist
    out = []
    cur_off, cur = None, ""
    for off, blk in fein:
        if cur and len(cur) + len(blk) <= limit:
            cur += blk
        else:
            if cur:
                out.append((cur_off, cur))
            cur_off, cur = off, blk
    if cur:
        out.append((cur_off, cur))
    return out


# ------------------------------------------------------------ HTTP-Client
class NetzFehler(Exception):
    pass


class PruefClient:
    """Drosselnder, wiederholender /v2/check-Client (urllib, ohne Fremdlibs).

    transport(url, params, timeout, ua) -> (status:int, headers:dict, body:bytes)
    ist injizierbar (Selbsttest/Unit-Tests laufen 100 % offline)."""

    UA = ("FranksFinanzcheck-ZeitRechtschreibWache/" + ENGINE_VERSION +
          " (https://franksfinanzcheck.de; Rechtschreib-Dauerpruefung)")

    def __init__(self, api_url, benutzer="", schluessel="", timeout=60,
                 versuche=3, min_intervall=0.6, transport=None,
                 sleeper=time.sleep, uhr=time.monotonic):
        self.api_url = api_url
        self.benutzer = benutzer
        self.schluessel = schluessel
        self.timeout = timeout
        self.versuche = max(1, versuche)
        self.min_intervall = min_intervall
        self.transport = transport or self._urllib_transport
        self.sleeper = sleeper
        self.uhr = uhr
        self._letzte_anfrage = 0.0
        self.anfragen = 0
        self.modus_public = False  # Drossel-Profil: öffentlicher Gratis-Endpunkt

    @staticmethod
    def _urllib_transport(url, params, timeout, ua):
        daten = urllib.parse.urlencode(params).encode("utf-8")
        req = urllib.request.Request(
            url, data=daten, method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded",
                     "Accept": "application/json", "User-Agent": ua})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as ant:
                return 200, dict(ant.headers.items()), ant.read()
        except urllib.error.HTTPError as e:
            body = e.read() if hasattr(e, "read") else b""
            return e.code, dict(getattr(e, "headers", {}) or {}), body
        except (urllib.error.URLError, OSError) as e:
            raise NetzFehler(f"Netz not reachable: {e}") from e

    def _warte_slot(self):
        delta = self.uhr() - self._letzte_anfrage
        if self._letzte_anfrage and delta < self.min_intervall:
            self.sleeper(self.min_intervall - delta)

    def check(self, text: str, profil: dict) -> dict:
        params = {"text": text,
                  "language": profil.get("language", "de-DE"),
                  "motherTongue": profil.get("motherTongue", "de-DE"),
                  "level": profil.get("level", "picky"),
                  "enabledOnly": "false"}
        if self.benutzer and self.schluessel:
            params["username"] = self.benutzer
            params["apiKey"] = self.schluessel
        fehler = None
        for versuch in range(1, self.versuche + 1):
            self._warte_slot()
            try:
                status, headers, body = self.transport(
                    self.api_url, params, self.timeout, self.UA)
                self._letzte_anfrage = self.uhr()
                self.anfragen += 1
            except NetzFehler as e:
                fehler = str(e)
                self.sleeper(min(2 ** versuch, 20))
                continue
            if status == 200:
                try:
                    out = json.loads(body.decode("utf-8", "replace"))
                    if "matches" not in out:
                        out["matches"] = []
                    return out
                except (ValueError, UnicodeDecodeError) as e:
                    fehler = f"Antwort nicht lesbar: {e}"
                    break
            fehler = f"HTTP {status}"
            if status in (429, 500, 502, 503, 504):
                retry_after = 0
                for k, v in (headers or {}).items():
                    if str(k).lower() == "retry-after":
                        try:
                            retry_after = int(v)
                        except (TypeError, ValueError):
                            retry_after = 0
                self.sleeper(retry_after or min(2 ** versuch * 2, 30))
                continue
            if status == 413:
                raise NetzFehler("HTTP 413 – Chunk zu groß für den Endpunkt")
            break  # 4xx: nicht wiederholbar
        raise NetzFehler(fehler or "unbekannter Providerfehler")


# ------------------------------------------------------------ Fund-Modell
def zeile_bei(text: str, offset: int) -> int:
    return text.count("\n", 0, max(0, offset)) + 1


def normalisiere_matches(roh: dict, text_bezug: str, basis: int,
                         datei: str, zone: str) -> list:
    """Rohmatches -> Fund-Modell (Offsets global zum Zonen-Text)."""
    funde = []
    for m in (roh or {}).get("matches", []):
        regel = m.get("rule") or {}
        kat = regel.get("category") or {}
        off = basis + int(m.get("offset", 0))
        laenge = int(m.get("length", 0))
        fund = text_bezug[off:off + laenge]
        urls = regel.get("urls") or []
        funde.append({
            "datei": datei, "zone": zone,
            "regel": regel.get("id", "?"),
            "kategorie": kat.get("id", ""),
            "kategorie_name": kat.get("name", ""),
            "problem": regel.get("issueType", ""),
            "premium": bool(regel.get("isPremium")),
            "botschaft": (m.get("shortMessage") or m.get("message") or ""),
            "erklaerung": (m.get("message") or ""),
            "fund": fund, "offset": off, "laenge": laenge,
            "zeile": zeile_bei(text_bezug, off),
            "vorschlaege": [r.get("value", "")
                            for r in (m.get("replacements") or [])][:8],
            "url": (urls[0] or {}).get("value", "") if urls else "",
            "satz": (m.get("sentence") or "")[:200],
        })
    return funde


# ------------------------------------------------------------ Whitelist
def load_whitelist(cfg: dict) -> set:
    wl = set()
    for rel in cfg.get("whitelist_dateien", []):
        p = os.path.join(ROOT, rel)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        wl.add(line.lower())
    return wl


def filtere_funde(funde: list, cfg: dict, whitelist: set) -> tuple:
    """Trennt Funde in (aktiv, unterdrückt). Unterdrückung:
    - Fund-Token (≥4 Zeichen) in der Whitelist (Marken/Fachbegriffe)
    - Regel-ID / Kategorie auf der Ignorierliste
    """
    ig_regeln = set(cfg.get("ignorieren", {}).get("regeln", []))
    ig_kats = set(cfg.get("ignorieren", {}).get("kategorien", []))
    aktiv, unterdrueckt = [], []
    for f in funde:
        if f["regel"] in ig_regeln:
            unterdrueckt.append({**f, "grund": f"Regel {f['regel']} ignoriert"})
            continue
        if f["kategorie"] in ig_kats:
            unterdrueckt.append(
                {**f, "grund": f"Kategorie {f['kategorie']} ignoriert"})
            continue
        token = [t.lower() for t in
                 re.findall(r"[A-Za-zÄÖÜäöüß][\wÄÖÜäöüß-]{2,}", f["fund"])
                 if len(t) >= 4]
        treffer = next((t for t in token if t in whitelist), None)
        if treffer:
            unterdrueckt.append(
                {**f, "grund": f"Whitelist („{treffer}“ geschützt)"})
            continue
        aktiv.append(f)
    return aktiv, unterdrueckt


def auto_fix_erlaubt(f: dict, cfg: dict) -> bool:
    af = cfg.get("auto_fix", {})
    if f["zone"] not in af.get("zonen", []):
        return False
    if f["problem"] not in af.get("issue_types", []):
        return False
    if f["regel"] not in af.get("regeln", []):
        return False
    v = [x for x in f["vorschlaege"] if x]
    if af.get("nur_ein_vorschlag", True) and len(v) != 1:
        return False
    if not v or v[0] == f["fund"]:
        return False
    if len(f["fund"]) > af.get("max_fund_zeichen", 60):
        return False
    if "\n" in f["fund"] or "\n" in v[0]:
        return False
    # Weiche Trennstellen/Umbruch-Marker nie anfassen
    if "\u00ad" in f["fund"] or "\u00ad" in v[0]:
        return False
    # Ersatz darf keine Markdown-Struktur tragen
    if any(s in v[0] for s in ("[", "]", "(", ")", "{", "http", "<")):
        return False
    return True


# ------------------------------------------------------------ Cache
def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cache_laden(cfg: dict) -> dict:
    p = os.path.join(ROOT, cfg.get("cache", {}).get("pfad", ""))
    if p and os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict) and "eintraege" in data:
                return data
        except (ValueError, OSError):
            pass
    return {"version": 1, "eintraege": {}}


def cache_speichern(cfg: dict, cache: dict) -> None:
    p = os.path.join(ROOT, cfg.get("cache", {}).get("pfad", ""))
    if not p:
        return
    eintraege = cache.get("eintraege", {})
    maxn = int(cfg.get("cache", {}).get("max", 400))
    if len(eintraege) > maxn:
        # Älteste zuerst kappen (after Stand sortiert)
        keys = sorted(eintraege, key=lambda k: eintraege[k].get("stand", ""))
        for k in keys[:len(eintraege) - maxn]:
            eintraege.pop(k, None)
    cache["eintraege"] = eintraege
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def profil_fingerabdruck(cfg: dict) -> str:
    a = cfg.get("anfrage", {})
    return _sha(json.dumps({
        "engine": ENGINE_VERSION,
        "language": a.get("language"), "motherTongue": a.get("motherTongue"),
        "level": a.get("level"),
        "ign": cfg.get("ignorieren", {}),
    }, sort_keys=True))


# ------------------------------------------------------------ Online-Lauf
def online_funde_fuer_artikel(client, art, cfg, relpath, fp, cache,
                              benutze_cache, whitelist):
    """Prüft Masked-Body + Description + Titel. Liefert
    (aktive_funde, unterdrückte, roh_cache_wert, cache_treffer, notizen)."""
    masked = maskiere(art["body"])
    desc = art.get("description", "") or ""
    titel = art.get("title", "") or ""
    schluessel_inhalt = _sha(fp + "\n" + masked + "\n" + desc + "\n" + titel)
    eintrag = cache.get("eintraege", {}).get(relpath)
    if benutze_cache and eintrag and eintrag.get("sha") == schluessel_inhalt:
        roh = eintrag.get("funde", [])
        aktiv, unter = filtere_funde(roh, cfg, whitelist)
        return aktiv, unter, roh, True, []

    chunk_limit = int(cfg.get("anfrage", {}).get(
        "chunk_zeichen_premium" if client.benutzer else "chunk_zeichen",
        9000))
    roh_funde = []
    notizen = []
    max_anf = cfg.get("anfrage", {}).get("max_anfragen_pro_lauf", 120)
    if client.modus_public:
        max_anf = min(max_anf, cfg.get("anfrage", {}).get(
            "max_anfragen_oeffentlich", 40))

    def _pruefen(bezug_text, zone, basis):
        if client.anfragen >= max_anf:
            notizen.append("Anfrage-Budget erschöpft – Rest übersprungen "
                           "(nächster Lauf nutzt den Cache).")
            return False
        try:
            roh = client.check(bezug_text, cfg.get("anfrage", {}))
        except NetzFehler as e:
            notizen.append(f"{zone}: Provider-Fehler: {e}")
            return False
        roh_funde.extend(normalisiere_matches(roh, bezug_text, basis,
                                              relpath, zone))
        return True

    alles_ok = True
    for off, chunk in chunken(masked, chunk_limit):
        if not chunk.strip():
            continue
        alles_ok = _pruefen(chunk, "fluesstext", off) and alles_ok
        if not alles_ok:
            break
    if alles_ok and desc.strip():
        alles_ok = _pruefen(desc, "description", 0) and alles_ok
    if alles_ok and titel.strip():
        alles_ok = _pruefen(titel, "title", 0) and alles_ok

    if not alles_ok:
        notizen.append("Artikel nur teilweise online geprüft "
                       "(Provider-Limit/Fehler).")
    cache.setdefault("eintraege", {})[relpath] = {
        "sha": schluessel_inhalt, "stand": now_utc(), "funde": roh_funde,
        "unvollstaendig": not alles_ok,
    }
    aktiv, unter = filtere_funde(roh_funde, cfg, whitelist)
    return aktiv, unter, roh_funde, False, notizen


# ------------------------------------------------------------ Fixes anwenden
def wende_fixes_an(text: str, funde: list, cfg: dict) -> tuple:
    """Wendet erlaubte Fixes an (rückwärts, mit Kontext-Probe am Offset).
    Liefert (neuer_text, angewandte_funde)."""
    fixe = [f for f in funde if f.get("auto_fix") and not f.get("unterdrueckt")]
    fixe.sort(key=lambda f: f["offset"], reverse=True)
    ueberdeckt = []
    angewandt = []
    for f in fixe:
        s, e = f["offset"], f["offset"] + f["laenge"]
        ersatz = f["vorschlaege"][0]
        if any(not (e <= a or s >= b) for a, b in ueberdeckt):
            continue  # Überschneidung mit bereits korrigiertem Bereich
        if text[s:e] != f["fund"]:
            continue  # Kontext-Probe: Offset zeigt nicht mehr auf den Fund
        # Struktur-Sabotage wird global von sprachkern.write_verified
        # abgefangen (Link-/Shortcode-/Überschriften-Wächter); die Maskierung
        # sichert zusätzlich, dass Offsets nie IN Schutzzonen zeigen können.
        text = text[:s] + ersatz + text[e:]
        ueberdeckt.append((s, s + len(ersatz)))
        angewandt.append(f)
    return text, angewandt


# ------------------------------------------------------------ Offline-Ebene
def offline_funde_und_fix(art_liste, cfg, do_fix):
    """Deterministische lokale Ebene: grammar_check.py (LT-Nachbau LT1–LT4).
    Gibt (funde, geheilt_n, notizen) zurück. Netzfrei, keine Fremdlibs."""
    notizen = []
    try:
        import grammar_check as gc
    except Exception as e:  # pragma: no cover - Defensive
        return [], 0, [f"Lokale Engine nicht ladbar: {e}"]
    wl = gc.load_whitelist()
    funde = []
    geheilt = 0
    rel = os.path.relpath
    for art in art_liste:
        art_funde = []
        for f in gc.analyze(art, wl):
            art_funde.append({
                "datei": rel(art["path"], ROOT), "zone": f.get("zone", "fluesstext"),
                "regel": f["rule"], "kategorie": "lokal-lt",
                "kategorie_name": "LT-Nachbau (offline)",
                "problem": "orthografie", "premium": False,
                "botschaft": f["label"],
                "erklaerung": f.get("label", ""),
                "fund": f["found"], "offset": None, "laenge": len(f["found"]),
                "zeile": None,
                "vorschlaege": [f["fix"]] if f.get("fix") else [],
                "url": "", "satz": f.get("ctx", ""),
                "lokal": True,
            })
        funde.extend(art_funde)
        if do_fix:
            neu_body, n1, _ = gc.apply_rules(art["body"], gc.RULES)
            neu_desc, n2 = None, 0
            if art.get("description"):
                d2, n2, _ = gc.apply_rules(art["description"], gc.RULES)
                if n2:
                    neu_desc = d2
            if n1 + n2:
                ok, grund = write_verified(art, rebuild(art, neu_body, neu_desc),
                                           "zeit_rechtschreibung/offline")
                if ok:
                    geheilt += n1 + n2
                    art["content"] = rebuild(art, neu_body, neu_desc)
                    art["body"] = neu_body
                    # Als angewandt gelten die Funde mit Ersatz-Vorschlag
                    # außerhalb der Schreibtabu-Zonen (Titel bleibt Report).
                    for f in art_funde:
                        if f["vorschlaege"] and f["zone"] != "title":
                            f["angewandt"] = True
                else:
                    notizen.append(f"{rel(art['path'], ROOT)}: Schreibsperre "
                                   f"offline ({grund})")
    return funde, geheilt, notizen


# ------------------------------------------------------------ Bericht/JSON
def _md(s: str) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ").strip()


def besitzer_fuer(f: dict) -> tuple:
    if f.get("auto_fix"):
        return "auto", "P3", "redaktion"
    if f["problem"] in ("misspelling", "typographical", "grammar", "orthografie"):
        return "human", "P2", "redaktion"
    return "human", "P3", "redaktion"


def schreibe_report(erg: dict) -> None:
    L = ["# 🔍 ZEIT-Niveau-Rechtschreibung – Premium-Report", ""]
    L.append(
        f"> **{now_utc()} UTC** · Modus: **{erg['modus']}** ({erg['provider_grund']}) · "
        f"Artikel: **{erg['artikel']}** · Anfragen: **{erg['anfragen']}** "
        f"(Cache-Treffer: {erg['cache_treffer']}) · "
        f"Funde: **{len(erg['funde'])}** ({erg['premium_funde']} Premium) · "
        f"Geheilt: **{erg['geheilt']}** · Offen: **{erg['offen']}** · "
        f"Unterdrückt: **{len(erg['unterdrueckt'])}** (Whitelist/Regelwerk)")
    L += ["", "## Provider & Dauerbetrieb", ""]
    L.append(f"- **Modus:** `{erg['modus']}` – {erg['provider_grund']}")
    L.append(f"- **Produkt:** {erg['produkt']}")
    L.append("- **Dauer-Versprechen:** Premium → Öffentlich (nur manuell) → "
             "Offline; die Wache fällt nie aus, sie fällt nur weicher.")
    L.append("- **Datenfluss:** " + (
        "Artikel-Fließtext verlässt die Infrastruktur nur im Premium-/Öffentlich-"
        "Modus Richtung konfiguriertem Endpunkt (EU/DSGVO-Ordnung siehe "
        "Onboarding-Report); im Offline-Modus bleibt nichts außer Haus."))
    if erg.get("notizen"):
        L.append("")
        for n in erg["notizen"][:12]:
            L.append(f"- ⚠️ {_md(n)}")
    # Kategorien
    kat_zaehler = {}
    for f in erg["funde"]:
        kat_zaehler[f["kategorie_name"] or f["kategorie"] or "?"] = \
            kat_zaehler.get(f["kategorie_name"] or f["kategorie"] or "?", 0) + 1
    L += ["", "## Funde nach Kategorie", ""]
    if kat_zaehler:
        L.append("| Kategorie | Funde |")
        L.append("|---|---|")
        for k, n in sorted(kat_zaehler.items(), key=lambda kv: -kv[1]):
            L.append(f"| {_md(k)} | {n} |")
    else:
        L.append("_Keine Funde in aktiven Kategorien._")
    # Funde je Artikel
    L += ["", "## Funde nach Artikel (Top)", ""]
    je_art = {}
    for f in erg["funde"]:
        je_art.setdefault(f["datei"], []).append(f)
    if je_art:
        for datei in sorted(je_art, key=lambda d: -len(je_art[d]))[:20]:
            L.append(f"### `{datei}` ({len(je_art[datei])} Funde)")
            L.append("")
            for f in je_art[datei][:12]:
                vor = f"vorschlaege: {', '.join(f['vorschlaege'][:3])}" \
                    if f["vorschlaege"] else "kein Ersatz"
                zeile = f"Z {f['zeile']}" if f.get("zeile") else f["zone"]
                mark = "🌟" if f.get("premium") else ("🤖" if f.get("auto_fix") else "🖐")
                L.append(
                    f"- {mark} **{f['regel']}** ({_md(f['kategorie_name'] or f['problem'])}, "
                    f"{zeile}): „{_md(f['fund'])}“ – {_md(f['botschaft'] or f['erklaerung'])} "
                    f"[{_md(vor)}]")
            if len(je_art[datei]) > 12:
                L.append(f"- … {len(je_art[datei]) - 12} weitere im JSON")
            L.append("")
    else:
        L.append("🎉 Keine offenen Funde – der Bestand liegt über der Latte.")
        L.append("")
    # Premium-Sektion
    prem = [f for f in erg["funde"] if f.get("premium")]
    L += ["", "## Premium-Erkenntnisse (isPremium)", ""]
    if prem:
        for f in prem[:15]:
            L.append(f"- 🌟 `{f['datei']}` **{f['regel']}**: „{_md(f['fund'])}“ – "
                     f"{_md(f['erklaerung'])} → {', '.join(f['vorschlaege'][:3])}")
    else:
        L.append("_Keine Premium-only-Funde " +
                 ("(kein Premium-Zugang aktiv)." if erg["modus"] != "premium"
                  else "– Bestand sauber.") + "_")
    # Unterdrückte
    L += ["", "## Unterdrückte Funde (Whitelist/Regelwerk)", ""]
    if erg["unterdrueckt"]:
        for f in erg["unterdrueckt"][:20]:
            L.append(f"- `{f['datei']}` „{_md(f['fund'])}“ – {_md(f.get('grund', ''))}")
        if len(erg["unterdrueckt"]) > 20:
            L.append(f"- … {len(erg['unterdrueckt']) - 20} weitere")
    else:
        L.append("_Keine._")
    L += ["", "---",
          "*Erzeugt von scripts/zeit_rechtschreibung.py (ZEIT-Niveau-Wache, "
          "Offline-fähig, Premium-ready). Leitplanken: "
          "docs/ANLEITUNG-ZEIT-RECHTSCHREIBUNG.md*"]
    with open(REPORT_FILE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


def schreibe_history(cfg: dict, erg: dict) -> None:
    h = cfg.get("history", {})
    p = os.path.join(ROOT, h.get("pfad", ""))
    if not p:
        return
    heute = datetime.now(timezone.utc).date().isoformat()
    zeilen = []
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                try:
                    eintrag = json.loads(line)
                except ValueError:
                    continue
                if eintrag.get("datum") != heute:
                    zeilen.append(eintrag)
    zeilen = zeilen[-int(h.get("max", 500)):]
    zeilen.append({
        "datum": heute, "stand": now_utc(), "engine": ENGINE_VERSION,
        "modus": erg["modus"], "artikel": erg["artikel"],
        "anfragen": erg["anfragen"], "cache_treffer": erg["cache_treffer"],
        "funde": len(erg["funde"]), "premium_funde": erg["premium_funde"],
        "geheilt": erg["geheilt"], "offen": erg["offen"],
        "unterdrueckt": len(erg["unterdrueckt"]),
    })
    with open(p, "w", encoding="utf-8") as fh:
        for e in zeilen:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")


# ------------------------------------------------------------ Selbsttest
class _FakeTransport:
    """Offline-Antwortgeber: liefert eingefrorene Premium-Antworten."""

    def __init__(self, antworten, counter):
        self.antworten = antworten  # list of (needle, response-dict) oder callable
        self.counter = counter

    def __call__(self, url, params, timeout, ua):
        text = params.get("text", "")
        self.counter[0] += 1
        for needle, antwort in self.antworten:
            if callable(antwort):
                out = antwort(text)
                if out is not None:
                    return 200, {}, json.dumps(out).encode()
            elif needle in text:
                return 200, {}, json.dumps(antwort).encode()
        return 200, {}, json.dumps({"matches": []}).encode()


def _fake_client(antworten, counter, modus_public=False):
    c = PruefClient("https://fake.local/v2/check", benutzer="", schluessel="",
                    min_intervall=0, transport=_FakeTransport(antworten, counter),
                    sleeper=lambda s: None, uhr=lambda: 0.0)
    c.modus_public = modus_public
    return c


def run_selftest() -> list:
    """Eingefrorene Verträge (offline, mit Fixture-Transport)."""
    fehler = []
    cfg = dict(DEFAULT_CONFIG)

    # ST1: Maskierung ist längentreu & deckt Schutzzonen ab
    probe = ("# Doppelte Wörter\n\nDas ist **fett** und `code` und "
             "[Anker mit Tippfeler](https://x.de/a) sowie ```x = tpipo()```.\n"
             "| a | b |\n|---|---|\n| 1 | 2 |\n")
    m = maskiere(probe)
    if len(m) != len(probe):
        fehler.append("ST1: Maskierung nicht längentreu")
    if probe.count("\n") != m.count("\n"):
        fehler.append("ST1: Zeilenumbrüche nicht bewahrt")
    for geschuetzt in ("Anker", "Tippfeler", "tpipo", "x.de"):
        if geschuetzt in m:
            fehler.append(f"ST1: Schutzzone durchgesickert: {geschuetzt}")
    if "Doppelte Wörter" not in m or "Das ist" not in m or "fett" not in m:
        fehler.append("ST1: Fließtext/Überschriftentext fälschlich maskiert")
    for marker in ("**", "`", "{{", "]", "---|"):
        if marker in m:
            fehler.append(f"ST1: Markdown-Marker durchgesickert: {marker}")

    # ST2: Chunking ohne Verlust, Offsets fortlaufend
    lang_text = "\n\n".join(f"Satz {i} mit Inhalt." for i in range(400))
    chunks = chunken(lang_text, 900)
    zusammen = "".join(c for _, c in chunks)
    if zusammen != lang_text:
        fehler.append("ST2: Chunking verliert/verändert Text")
    off_folge = [o for o, _ in chunks]
    laengen = [len(c) for _, c in chunks]
    for i in range(1, len(chunks)):
        if off_folge[i] != off_folge[i - 1] + laengen[i - 1]:
            fehler.append("ST2: Chunk-Offsets nicht lückenlos")
            break
    if any(len(c) > 900 for _, c in chunks):
        fehler.append("ST2: Chunk überschreitet Limit")

    # ST3: Offset-Mapping über Chunks in den Original-Body
    body = "Erster Absatz sauber.\n\nDas Brot backt man am bestem mit Hefe.\n\nDritter Teil ok."
    masked = maskiere(body)

    def _antwort_bestem(text):
        if "bestem" not in text:
            return {"matches": []}
        off = text.index("bestem") - len("am ")
        return {"matches": [{
            "message": "Meinten Sie „besten“?", "shortMessage": "Grammatik",
            "replacements": [{"value": "am besten"}],
            "offset": off, "length": len("am bestem"),
            "sentence": "Das Brot backt man am bestem mit Hefe.",
            "rule": {"id": "BESTEM_FALL", "issueType": "grammar",
                     "category": {"id": "GRAMMAR", "name": "Grammatik"}}}]}

    counter = [0]
    client = _fake_client([(None, _antwort_bestem)], counter)
    limit = max(1, len(body) // 2)
    roh = []
    for off, chunk in chunken(masked, limit):
        roh.extend(normalisiere_matches(client.check(chunk, {}), masked,
                                        off, "x.md", "fluesstext"))
    if not roh or body[roh[0]["offset"]:roh[0]["offset"] + roh[0]["laenge"]] != "am bestem":
        fehler.append("ST3: Offset-Mapping über Chunk-Grenzen falsch")

    # ST4: Whitelist-Unterdrückung Markenwort
    wl = {"fritzbox", "rechnung"}
    funde = [
        {"datei": "a", "zone": "fluesstext", "regel": "X", "kategorie": "",
         "kategorie_name": "", "problem": "misspelling", "premium": False,
         "botschaft": "", "erklaerung": "", "fund": "FritzBox",
         "offset": 0, "laenge": 8, "zeile": 1, "vorschlaege": ["Fritzbox"],
         "url": "", "satz": ""},
        {"datei": "a", "zone": "fluesstext", "regel": "Y", "kategorie": "",
         "kategorie_name": "", "problem": "misspelling", "premium": False,
         "botschaft": "", "erklaerung": "", "fund": "Rechnug",
         "offset": 9, "laenge": 7, "zeile": 1, "vorschlaege": ["Rechnung"],
         "url": "", "satz": ""},
    ]
    aktiv, unter = filtere_funde(funde, cfg, wl)
    if len(aktiv) != 1 or aktiv[0]["fund"] != "Rechnug":
        fehler.append("ST4: Whitelist-Unterdrückung falsch")
    if len(unter) != 1 or "Whitelist" not in unter[0]["grund"]:
        fehler.append("ST4: Unterdrückter Fund ohne Begründung")

    # ST5: Auto-Fix-Gatter – nur harte Allowlist, ein Vorschlag, richtige Zone
    ok_fall = {**dict(funde[1], auto_fix=None), "regel": "GERMAN_SPELLER_RULE"}
    if not auto_fix_erlaubt(ok_fall, cfg):
        fehler.append("ST5: Eindeutiger Rechtschreib-Fund nicht fix-erlaubt")
    block = [
        ({**ok_fall, "regel": "DE_STYLE_X"},
         "Stil-Regel darf nie auto-fixen"),
        ({**ok_fall, "problem": "style"}, "Issue-Typ style muss blockieren"),
        ({**ok_fall, "vorschlaege": ["Rechnung", "Rechnungen"]},
         "zwei Vorschläge = menschliche Entscheidung"),
        ({**ok_fall, "zone": "title"}, "Titel-Zone ist Schreibtabu"),
        ({**ok_fall, "zone": "fluesstext", "fund": "a\nb"},
         "Zeilenumbruch im Fund blockieren"),
        ({**ok_fall, "vorschlaege": ["[Rechnung](x)"]},
         "Markdown im Ersatz blockieren"),
    ]
    for f, warum in block:
        if auto_fix_erlaubt(f, cfg):
            fehler.append(f"ST5 nicht blockiert: {warum}")

    # ST6: Fix-Anwendung berührt Links/Titel nie + Kontext-Probe
    content_body = ("Das ist die Rehnung. "
                    "[Meine Rehnung](https://example.com/Rehnung) bleibt. Ein Rehnug."
                    )
    fm_fix = [{"datei": "a", "zone": "fluesstext", "regel": "GERMAN_SPELLER_RULE",
               "kategorie": "", "kategorie_name": "", "problem": "misspelling",
               "premium": False, "botschaft": "", "erklaerung": "",
               "fund": "Rehnung", "offset": content_body.index("Rehnung"),
               "laenge": 7, "zeile": 1, "vorschlaege": ["Rechnung"],
               "url": "", "satz": "", "auto_fix": True},
              {"datei": "a", "zone": "fluesstext", "regel": "GERMAN_SPELLER_RULE",
               "kategorie": "", "kategorie_name": "", "problem": "misspelling",
               "premium": False, "botschaft": "", "erklaerung": "",
               "fund": "Rehnug", "offset": content_body.rindex("Rehnug"),
               "laenge": 6, "zeile": 1, "vorschlaege": ["Rechnung"],
               "url": "", "satz": "", "auto_fix": True}]
    neu, angewandt = wende_fixes_an(content_body, fm_fix, cfg)
    if "die Rehnung" in neu:
        fehler.append("ST6: Fließtext-Tippfehler nicht geheilt")
    if "[Meine Rehnung](https://example.com/Rehnung) bleibt." not in neu:
        fehler.append("ST6: Link (Ankertext/Ziel) wurde angefasst")
    if len(angewandt) != 2:
        fehler.append("ST6: Fixzahl falsch (Kontext-Probe/Überdeckung)")
    kaputt = [{"datei": "a", "zone": "fluesstext", "regel": "GERMAN_SPELLER_RULE",
               "kategorie": "", "kategorie_name": "", "problem": "misspelling",
               "premium": False, "botschaft": "", "erklaerung": "",
               "fund": "Rehnung", "offset": 3, "laenge": 7,
               "zeile": 1, "vorschlaege": ["Rechnung"],
               "url": "", "satz": "", "auto_fix": True}]
    neu2, ang2 = wende_fixes_an(content_body, kaputt, cfg)
    if neu2 != content_body or ang2:
        fehler.append("ST6: Kontext-Probe versagt (falscher Offset angewandt)")

    # ST7: Offline-Fallback läuft netzfrei & fängt Provider-Tod ab
    def toter_transport(url, params, timeout, ua):
        raise NetzFehler("simulierter Provider-Ausfall")
    c7 = PruefClient("https://fake", transport=toter_transport,
                     min_intervall=0, sleeper=lambda s: None, uhr=lambda: 0.0)
    versuchte_exception = False
    try:
        c7.check("test", {})
    except NetzFehler:
        versuchte_exception = True
    if not versuchte_exception:
        fehler.append("ST7: NetzFehler wird nicht sauber signalisiert")

    # ST8: Kosten-Regel – require_online=true MUSS Exit-2-Pfad auslösen
    try:
        pruefe_konfig(_merge(DEFAULT_CONFIG, {"anbieter": {"require_online": True}}))
        fehler.append("ST8: require_online=true nicht abgefangen")
    except KonfigFehler:
        pass
    try:
        pruefe_konfig(_merge(DEFAULT_CONFIG, {"anbieter": {"offline_fallback": False}}))
        fehler.append("ST8: offline_fallback=false nicht abgefangen")
    except KonfigFehler:
        pass

    # ST9: Cache verhindert Doppel-Anfragen bei unverändertem Artikel
    cache = {"version": 1, "eintraege": {}}
    art = {"path": "/tmp/x.md", "body": body, "description": "", "title": ""}
    ctr = [0]
    c9 = _fake_client([(None, _antwort_bestem)], ctr)
    fp = "testfp"
    cfg9 = dict(DEFAULT_CONFIG)
    cfg9["anfrage"] = dict(cfg9["anfrage"], chunk_zeichen=4000)
    online_funde_fuer_artikel(c9, art, cfg9, "a.md", fp, cache, True, set())
    stand1 = ctr[0]
    online_funde_fuer_artikel(c9, art, cfg9, "a.md", fp, cache, True, set())
    if ctr[0] != stand1:
        fehler.append("ST9: Cache ignoriert – Anfragen doppelt gesendet")

    # ST10: Schreibvertrag – write_verified stoppt strukturverletzende Änderung
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "a.md")
        ursprung = "---\ntitle: \"x\"\n---\n\nText mit [Link](https://x.de) und Wort."
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(ursprung)
        a = {"path": p, "content": ursprung}
        ok, grund = write_verified(a, ursprung.replace("mit [Link]", "ohne Link"),
                                   "selftest")
        if ok:
            fehler.append("ST10: write_verified hat Strukturbruch geschrieben")
        with open(p, encoding="utf-8") as fh:
            if fh.read() != ursprung:
                fehler.append("ST10: Datei trotz Sperre verändert")

    return fehler


# ------------------------------------------------------------ Hauptlauf
def laufe(files=None, include_drafts=False, new_only=False, do_fix=False,
          offline=False, oeffentlich=False, refresh=False,
          max_artikel=None, progress=print):
    """Führt die Prüfung aus. Liefert Ergebnis-Dict."""
    cfg = load_config()
    zugang = zugang_ermitteln(cfg, oeffentlich)
    if offline:
        zugang["modus"] = "offline"
        zugang["grund"] = "--offline gesetzt"

    arts = load_articles(files, new_only=new_only, include_drafts=include_drafts)
    if max_artikel:
        arts = arts[:max_artikel]
    rel = os.path.relpath
    whitelist = load_whitelist(cfg)
    cache = cache_laden(cfg) if cfg.get("cache", {}).get("aktiv", True) \
        else {"version": 1, "eintraege": {}}
    fp = profil_fingerabdruck(cfg)

    erg = {
        "modus": zugang["modus"], "provider_grund": zugang["grund"],
        "produkt": cfg.get("anbieter", {}).get("produkt", PRODUKT_NAME),
        "artikel": len(arts), "anfragen": 0, "cache_treffer": 0,
        "funde": [], "unterdrueckt": [], "geheilt": 0,
        "premium_funde": 0, "offen": 0, "notizen": [], "items": [],
    }

    if zugang["modus"] == "offline":
        progress(f"ZEIT-Niveau-Wache OFFLINE ({len(arts)} Artikel) – "
                 f"lokale Engine LT1–LT4.")
        funde, geheilt, notizen = offline_funde_und_fix(arts, cfg, do_fix)
        for f in funde:
            f["auto_fix"] = bool(f["vorschlaege"]) and f["zone"] != "title"
            f["owner"], f["severity"], f["channel"] = besitzer_fuer(f)
        erg["funde"], erg["geheilt"], erg["notizen"] = funde, geheilt, notizen
        erg["premium_funde"] = 0
        erg["unterdrueckt"] = []
    else:
        a = cfg.get("anfrage", {})
        intervall = (a.get("min_intervall_premium_s", 0.6)
                     if zugang["modus"] == "premium"
                     else a.get("min_intervall_oeffentlich_s", 4.0))
        client = PruefClient(zugang["api_url"], zugang["benutzer"],
                             zugang["schluessel"],
                             timeout=a.get("timeout_s", 60),
                             versuche=a.get("versuche", 3),
                             min_intervall=intervall)
        client.modus_public = zugang["modus"] == "oeffentlich"
        progress(f"ZEIT-Niveau-Wache {zugang['modus'].upper()} "
                 f"({len(arts)} Artikel → {zugang['api_url']})")
        cache_treffer = 0
        for i, art in enumerate(arts, 1):
            relpath = rel(art["path"], ROOT)
            aktiv, unter, _roh, hit, notizen = online_funde_fuer_artikel(
                client, art, cfg, relpath, fp, cache,
                benutze_cache=not refresh, whitelist=whitelist)
            cache_treffer += 1 if hit else 0
            for f in aktiv:
                f["auto_fix"] = auto_fix_erlaubt(f, cfg)
                f["owner"], f["severity"], f["channel"] = besitzer_fuer(f)
            erg["funde"].extend(aktiv)
            erg["unterdrueckt"].extend(unter)
            erg["notizen"].extend(f"{relpath}: {n}" for n in notizen)
            if i % 10 == 0 or i == len(arts):
                progress(f"  … {i}/{len(arts)} Artikel, "
                         f"{client.anfragen} Anfragen, "
                         f"{len(erg['funde'])} Funde")
        erg["anfragen"] = client.anfragen
        erg["cache_treffer"] = cache_treffer

        if do_fix and erg["funde"]:
            je_art = {}
            for f in erg["funde"]:
                je_art.setdefault(f["datei"], []).append(f)
            for art in arts:
                relpath = rel(art["path"], ROOT)
                funde = je_art.get(relpath, [])
                if not any(f.get("auto_fix") for f in funde):
                    continue
                neu_body, ang_body = wende_fixes_an(art["body"], funde, cfg)
                neu_desc, ang_desc = None, []
                desc = art.get("description", "") or ""
                desc_fixe = [f for f in funde if f["zone"] == "description"]
                if desc_fixe and desc:
                    nd, ang_desc = wende_fixes_an(desc, desc_fixe, cfg)
                    if nd != desc:
                        neu_desc = nd
                if ang_body or ang_desc:
                    ok, grund = write_verified(
                        art, rebuild(art, neu_body, neu_desc),
                        ENGINE_NAME)
                    if ok:
                        art["content"] = rebuild(art, neu_body, neu_desc)
                        art["body"] = neu_body
                        erg["geheilt"] += len(ang_body) + len(ang_desc)
                        for f in ang_body + ang_desc:
                            f["angewandt"] = True
                    else:
                        erg["notizen"].append(
                            f"{relpath}: Schreibsperre – {grund} "
                            f"(Funde bleiben offen)")

        if cfg.get("cache", {}).get("aktiv", True):
            cache_speichern(cfg, cache)

    offene = [f for f in erg["funde"] if not f.get("angewandt")]
    erg["offen"] = len(offene)
    erg["premium_funde"] = sum(1 for f in erg["funde"] if f.get("premium"))
    erg["items"] = [
        {k: f.get(k) for k in ("datei", "zone", "regel", "kategorie_name",
                               "problem", "premium", "fund", "zeile",
                               "vorschlaege", "erklaerung", "auto_fix",
                               "angewandt", "owner", "severity", "channel")}
        for f in erg["funde"][:500]
    ]
    return erg


def schreibe_json(erg: dict) -> None:
    with open(JSON_FILE, "w", encoding="utf-8") as fh:
        json.dump({
            "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "engine": ENGINE_NAME, "engine_version": ENGINE_VERSION,
            "modus": erg["modus"], "provider_grund": erg["provider_grund"],
            "artikel": erg["artikel"], "anfragen": erg["anfragen"],
            "cache_treffer": erg["cache_treffer"],
            "funde": len(erg["funde"]), "premium_funde": erg["premium_funde"],
            "geheilt": erg["geheilt"], "offen": erg["offen"],
            "unterdrueckt": len(erg["unterdrueckt"]),
            "notizen": erg["notizen"][:50], "items": erg["items"],
        }, fh, ensure_ascii=False, indent=1)


def probe(cfg, oeffentlich) -> dict:
    """Provider-Gesundheit: kleiner Satz mit kalkuliertem Fehler."""
    zugang = zugang_ermitteln(cfg, oeffentlich)
    if zugang["modus"] == "offline":
        return {"modus": "offline", "online": False,
                "befund": zugang["grund"],
                "modus_hinweis": "Offline-Pfad aktiv – Premium-Zugang über "
                                 "ZR_API_URL oder ZR_USERNAME+ZR_API_KEY setzen."}
    satz = "Das Brot backt man am bestem mit Hefe."
    client = PruefClient(zugang["api_url"], zugang["benutzer"],
                         zugang["schluessel"], timeout=45, versuche=2,
                         min_intervall=0)
    client.modus_public = zugang["modus"] == "oeffentlich"
    t0 = time.monotonic()
    try:
        roh = client.check(satz, cfg.get("anfrage", {}))
    except NetzFehler as e:
        return {"modus": zugang["modus"], "online": False,
                "api_url": zugang["api_url"], "befund": str(e)}
    dauer = round(time.monotonic() - t0, 2)
    matches = roh.get("matches", [])
    erwartet = any(m.get("rule", {}).get("id") for m in matches)
    sw = roh.get("software", {})
    return {"modus": zugang["modus"], "online": True,
            "api_url": zugang["api_url"], "matches": len(matches),
            "prueffe_wohlgeformt": erwartet,
            "engine": f"{sw.get('name', '?')} {sw.get('version', '?')}",
            "premium_serverseitig": bool(sw.get("premium")),
            "dauer_s": dauer}


def main(argv=None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])

    if "--selftest" in argv:
        stf = run_selftest()
        if stf:
            print("🛑 ZEIT-RECHTSCHREIBUNG-SELBSTTEST ROT:")
            print("\n".join("  " + f for f in stf))
            return 2
        print("✅ Selbsttest grün (ST1–ST10, offline via Fixture-Transport).")
        return 0

    try:
        cfg = load_config()
    except KonfigFehler as e:
        print(f"🛑 Konfiguration blockiert: {e}")
        return 2
    except (ValueError, OSError) as e:
        print(f"🛑 Konfiguration nicht lesbar: {e}")
        return 2

    if "--probe" in argv:
        try:
            erg = probe(cfg, "--oeffentlich" in argv)
        except Exception as e:  # pragma: no cover
            print(json.dumps({"online": False, "befund": str(e)},
                             ensure_ascii=False, indent=1))
            return 3
        print(json.dumps(erg, ensure_ascii=False, indent=1))
        return 0 if erg.get("modus") == "offline" or erg.get("online") else 3

    do_fix = "--fix" in argv
    if do_fix:
        stf = run_selftest()
        if stf:
            print("🛑 SELBSTTEST ROT – Sabotage verhindert, kein Schreiben:")
            print("\n".join("  " + f for f in stf))
            return 2

    files = None
    for i, a in enumerate(argv):
        if a == "--file" and i + 1 < len(argv):
            p = argv[i + 1]
            if not os.path.isabs(p):
                p = os.path.join(ROOT, p)
            if not os.path.exists(p):
                p = os.path.join(ROOT, "content", "posts", argv[i + 1])
            files = [p]
        elif a.startswith("--file="):
            p = a.split("=", 1)[1]
            if not os.path.isabs(p):
                p = os.path.join(ROOT, p)
            files = [p]

    max_artikel = None
    for i, a in enumerate(argv):
        if a.startswith("--max-artikel="):
            max_artikel = int(a.split("=", 1)[1])

    offline = "--offline" in argv
    oeffentlich = "--oeffentlich" in argv
    zugang_vorschau = zugang_ermitteln(cfg, oeffentlich)
    if zugang_vorschau["modus"] == "oeffentlich" and not files and \
            os.environ.get("CI"):
        print("🛑 Öffentlicher Gratis-Endpunkt ist im CI VERBOTEN "
              "(ToS: keine automatisierten Anfragen). Premium-Zugang setzen "
              "oder --offline nutzen.")
        return 2

    erg = laufe(files=files, include_drafts="--include-drafts" in argv,
                new_only="--new-only" in argv, do_fix=do_fix,
                offline=offline, oeffentlich=oeffentlich,
                refresh="--refresh" in argv, max_artikel=max_artikel)

    schreibe_report(erg)
    schreibe_json(erg)
    schreibe_history(cfg, erg)

    if "--json" in argv:
        print(json.dumps({
            "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "engine": ENGINE_NAME, "engine_version": ENGINE_VERSION,
            "modus": erg["modus"], "artikel": erg["artikel"],
            "anfragen": erg["anfragen"], "cache_treffer": erg["cache_treffer"],
            "funde": len(erg["funde"]), "premium_funde": erg["premium_funde"],
            "geheilt": erg["geheilt"], "offen": erg["offen"],
            "notizen": erg["notizen"][:20], "items": erg["items"][:100],
        }, ensure_ascii=False, indent=1))
    else:
        print(f"\nFertig ({erg['modus']}): {erg['artikel']} Artikel, "
              f"{len(erg['funde'])} Funde ({erg['premium_funde']} Premium), "
              f"{erg['geheilt']} geheilt, {erg['offen']} offen, "
              f"{len(erg['unterdrueckt'])} unterdrückt.")
        print(f"Report: {os.path.relpath(REPORT_FILE, ROOT)}")

    if "--strict" in argv and erg["offen"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
