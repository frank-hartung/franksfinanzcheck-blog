#!/usr/bin/env python3
# ============================================================
#  POPPY-WERKBANK – Kernbibliothek (kostenloser Poppy.ai-Nachbau)
#  ------------------------------------------------------------
#  Nachbau der Poppy-Kernidee (getpoppy.ai), self-hosted und
#  kostenlos im eigenen Repo:
#
#    1) QUELLEN EINSAMMELN  – YouTube-Transkripte, Podcast-Feeds
#       (RSS, optional Audio via Gratis-Whisper auf Groq),
#       Artikel-URLs, PDFs, eigene Notizen
#    2) INSIGHT-KARTEN      – jede Quelle wird eine Karte auf dem
#       Board (data/poppy/cards/*.json) mit KI-Erkenntnissen
#    3) VERWERTEN           – aus jeder Karte entstehen in Franks
#       Marken-Stimme (brand_brain.yaml + schreibstil.yaml Kontext
#       via agc_context) ein Blog-ENTWURF plus Newsletter-,
#       Mastodon- und Pinterest-Texte
#
#  KOSTEN-REGEL (wie KI-Redaktion, Dauervorgabe): ausschließlich
#  die Gratis-Zugänge GROQ_API_KEY / GEMINI_API_KEY über den
#  vorhandenen llm_client. Keine Paid-APIs. Ohne Keys läuft alles
#  im Offline-Modus (Heuristik/Gerüst) – die Pipeline bricht nie.
#
#  VERÖFFENTLICHUNG: Poppy erzeugt NUR Entwürfe (draft: true).
#  Live geht ein Artikel ausschließlich über den bewährten Weg:
#      python3 scripts/ki_redaktion.py --promote <slug>
#  (cadence_guard, Mo/Mi/Fr, 2–3 Artikel/Tag).
#
#  Abhängigkeiten: reine Standardbibliothek; optionale Extractoren
#  (feedparser, pypdf, trafilatura, youtube-transcript-api) werden
#  bei Bedarf geladen – fehlen sie, greifen eingebaute Fallbacks.
# ============================================================
from __future__ import annotations

import datetime
import html as html_mod
import io
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import yaml  # noqa: E402

import llm_client  # noqa: E402  (Gratis-Kette Groq → Gemini, SSOT)

try:  # Marken-Kontext (Brand Brain) – darf nie crashen
    import agc_context  # noqa: E402
except Exception:  # noqa: BLE001
    agc_context = None

POPPY_DIR = os.path.join(BLOG_DIR, "data", "poppy")
CARD_DIR = os.path.join(POPPY_DIR, "cards")
QUELLEN_FILE = os.path.join(POPPY_DIR, "quellen.yaml")
REPORT_FILE = os.path.join(BLOG_DIR, "POPPY-WERKBANK-REPORT.md")
BOARD_ASSETS = os.path.join(BLOG_DIR, "tools", "poppy-board")
BOARD_OUTPUT = os.path.join(BLOG_DIR, ".cache", "poppy-board")

TYPEN = ("youtube", "podcast", "artikel", "pdf", "text")
STATUS_NEU = "neu"
STATUS_VERWERTET = "verwertet"

# Fallback-Register, falls data/seo/tag_register.yaml (noch) fehlt –
# im Normalfall wird die Pillar-Liste dynamisch daraus gelesen.
PILLAR_FALLBACK = [
    "frugalismus", "internet-dsl", "konto-karten",
    "mietwagen", "strom-sparen", "versicherungen",
]

# Pillar-Heuristik für den Offline-Modus (ohne KI-Key)
PILLAR_SCHLUESSELWORTE = {
    "strom-sparen": ["strom", "gas", "heiz", "energie", "kwh", "tarif",
                     "nachzahlung", "preisgarantie", "wärmepumpe", "ökosprit"],
    "versicherungen": ["versicherung", "haftpflicht", "beitrag", "prämie",
                       "police", "schaden", "risiko", "gebäudeversicherung"],
    "internet-dsl": ["dsl", "internet", "wlan", "router", "mobilfunk",
                     "handy", "kabel", "glasfaser", "dns", "provider"],
    "konto-karten": ["konto", "gebühr", "girokonto", "kreditkarte", "bank",
                     "dispo", "zinsen", "zahlungs"],
    "mietwagen": ["mietwagen", "miete", "leasing", "auto", "tanken",
                  "führungsschein", "kaution", "carsharing"],
    "frugalismus": ["sparen", "frugal", "haushaltsbuch", "budget",
                    "ausgaben", "konsum", "verzicht", "geld im alltag"],
}

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


# ---------------------------------------------------------------- Zeit / Kleinkram
def now_utc_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def heute_iso() -> str:
    return datetime.date.today().isoformat()


def slugify(text: str) -> str:
    """Repository-Slug (identisch zur Content-Engine: generate_drafts)."""
    text = (text or "").lower().strip()
    text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
    text = text.replace("ß", "ss")
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:72].rstrip("-") or "quelle"


def kuerze(text: str, limit: int) -> tuple[str, bool]:
    """Text an Satzgrenze kürzen (nie mitten im Satz)."""
    text = (text or "").strip()
    if len(text) <= limit:
        return text, False
    schnitt = text[:limit]
    punkt = max(schnitt.rfind(". "), schnitt.rfind("! "), schnitt.rfind("? "))
    if punkt > limit * 0.5:
        return schnitt[:punkt + 1], True
    if " " in schnitt:
        return schnitt.rsplit(" ", 1)[0] + " …", True
    return schnitt + " …", True


# ---------------------------------------------------------------- HTTP (nie crashen)
def http_get(url: str, timeout: int = 25, max_bytes: int = 30_000_000):
    """GET → (bytes|None, content_type, fehlermeldung)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read(max_bytes + 1)
            if len(data) > max_bytes:
                return None, resp.headers.get("Content-Type", ""), (
                    f"Datei größer als {max_bytes // 1_000_000} MB – übersprungen")
            return data, resp.headers.get("Content-Type", ""), None
    except Exception as e:  # noqa: BLE001 – Netzwerk darf die Pipeline nie brechen
        return None, "", f"{type(e).__name__}: {e}"


# ---------------------------------------------------------------- Quelltyp-Erkennung
_YT_VIDEO = re.compile(
    r"(?:youtube\.com/(?:watch\?[^ ]*v=|shorts/|live/|embed/)"
    r"|youtu\.be/)[A-Za-z0-9_-]{11}", re.I)
_YT_KANAL = re.compile(
    r"youtube\.com/(?:@[^/\s]+|channel/[A-Za-z0-9_-]+|c/[^/\s]+|user/[^/\s]+)"
    r"(/videos|/featured|/?$)|youtube\.com/feeds/videos\.xml", re.I)


def erkenne_typ(eingabe: str) -> tuple[str, str]:
    """(typ, wert) für eine Eingabe. Typen siehe TYPEN + youtube_kanal/feed.

    YouTube-videos.xml-Feeds zählen als youtube_kanal (ihre Einträge sind
    Videos); alle anderen Feeds (RSS/Atom/Podcast) als feed.
    """
    s = (eingabe or "").strip()
    if not s:
        return "text", ""
    if s.lower().startswith("podcast:"):
        rest = s[len("podcast:"):].strip()
        return "feed", rest
    if not re.match(r"^https?://", s, re.I):
        return "text", s
    if _YT_VIDEO.search(s):
        return "youtube", s
    pfad = urllib.parse.urlparse(s).path.lower()
    if pfad.endswith(".pdf"):
        return "pdf", s
    if _YT_KANAL.search(s):
        return "youtube_kanal", s
    if (pfad.endswith((".xml", ".rss", ".atom"))
            or re.search(r"/(?:feed|rss|feeds?)(?:/|$)", pfad)):
        return "feed", s
    return "artikel", s


def youtube_video_id(url: str) -> str:
    m = re.search(r"(?:v=|youtu\.be/|shorts/|live/|embed/)([A-Za-z0-9_-]{11})",
                  url or "")
    return m.group(1) if m else ""


def youtube_feed_url(kanal_url: str) -> str:
    """Kanal-URL (Handle/channel/…) → videos.xml-Feed-URL.

    Handle (/@name) und Legacy-/c/-URLs enthalten die Channel-ID nicht –
    sie wird per Seitenabruf (externalId) aufgelöst. Schlägt das fehl,
    wird die Eingabe unverändert zurückgegeben (Aufrufer meldet sauber).
    """
    u = (kanal_url or "").strip()
    if "feeds/videos.xml" in u:
        m = re.search(r"channel_id=([A-Za-z0-9_-]+)", u)
        if m:
            return u
    m = re.search(r"channel/([A-Za-z0-9_-]{20,})", u)
    if m:
        return ("https://www.youtube.com/feeds/videos.xml?channel_id="
                + m.group(1))
    daten, _, fehler = http_get(u, timeout=20)
    if daten:
        m = re.search(r'"externalId"\s*:\s*"([A-Za-z0-9_-]{20,})"',
                      daten.decode("utf-8", "replace"))
        if m:
            return ("https://www.youtube.com/feeds/videos.xml?channel_id="
                    + m.group(1))
    return u


# ---------------------------------------------------------------- YouTube
def hole_youtube_transkript(video_id: str) -> tuple[str | None, str]:
    """(transkript|None, methode) – deutsch zuerst, dann englisch."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except Exception:  # noqa: BLE001 – optionale Abhängigkeit
        return None, "bibliothek fehlt"
    try:
        # youtube-transcript-api >= 1.0 (neue Objekt-API)
        if hasattr(YouTubeTranscriptApi, "fetch"):
            api = YouTubeTranscriptApi()
            try:
                erg = api.fetch(video_id, languages=["de", "de-DE", "en"])
            except TypeError:  # ältere Signatur ohne languages-Kwarg
                erg = api.fetch(video_id)
            texte = [s.text for s in erg]
        else:  # alte Klassen-API (0.x)
            erg = YouTubeTranscriptApi.get_transcript(
                video_id, languages=["de", "de-DE", "en"])
            texte = [z["text"] for z in erg]
        text = " ".join(texte)
        text = re.sub(r"\s+", " ", text).strip()
        return (text if len(text) > 80 else None), "transcript-api"
    except Exception as e:  # noqa: BLE001 – Video ohne Untertitel o. Ä.
        return None, f"kein transkript ({type(e).__name__})"


def hole_oembed(url: str) -> tuple[str, str]:
    """(titel, autor) via YouTube-oEmbed – key-los."""
    daten, _, _ = http_get(
        "https://www.youtube.com/oembed?"
        + urllib.parse.urlencode({"url": url, "format": "json"}),
        timeout=15)
    if not daten:
        return "", ""
    try:
        payload = json.loads(daten.decode("utf-8"))
        return (payload.get("title") or "", payload.get("author_name") or "")
    except Exception:  # noqa: BLE001
        return "", ""


# ---------------------------------------------------------------- Feeds (RSS/Atom/Podcast)
def _strip_cdata(s: str) -> str:
    return re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", s, flags=re.S)


def _tag(block: str, name: str) -> str:
    m = re.search(rf"<{name}[^>]*>(.*?)</{name}>", block, re.S | re.I)
    if not m:
        return ""
    return html_mod.unescape(_strip_cdata(m.group(1))).strip()


def mini_feed_parser(xml_text: str) -> list[dict]:
    """Notfall-RSS/Atom-Parser ohne feedparser (nur title/link/desc)."""
    eintraege = []
    for block in re.findall(r"<entry[^>]*>.*?</entry>|<item[^>]*>.*?</item>",
                            xml_text, re.S | re.I):
        link = _tag(block, "link")
        if not link:
            m = re.search(r'<link[^>]*href="([^"]+)"', block, re.I)
            link = m.group(1) if m else ""
        beschreibung = (_tag(block, "content:encoded")
                        or _tag(block, "summary")
                        or _tag(block, "description")
                        or _tag(block, "content"))
        audio = ""
        m = re.search(r'<enclosure[^>]*url="([^"]+)"[^>]*type="audio',
                      block, re.I)
        if not m:
            m = re.search(r'<enclosure[^>]*type="audio[^"]*"[^>]*url="([^"]+)"',
                          block, re.I)
        if m:
            audio = html_mod.unescape(m.group(1))
        eintraege.append({
            "titel": _tag(block, "title"),
            "link": html_mod.unescape(link),
            "beschreibung": re.sub(r"<[^>]+>", " ", beschreibung),
            "datum": _tag(block, "pubDate") or _tag(block, "updated")
            or _tag(block, "published"),
            "audio_url": audio,
        })
    return eintraege


def hole_feed(url: str) -> list[dict]:
    """Feed-Einträge (neueste zuerst), jede Menge Fehlertoleranz."""
    daten, _, fehler = http_get(url, timeout=30)
    if fehler or not daten:
        print(f"  ⚠ Feed nicht erreichbar ({url}): {fehler}")
        return []
    text = daten.decode("utf-8", "replace")
    eintraege = []
    try:
        import feedparser  # optionale Abhängigkeit
        geparst = feedparser.parse(text)
        for e in geparst.entries:
            audio = ""
            for enc in (e.get("links") or []):
                if str(enc.get("type", "")).startswith("audio"):
                    audio = enc.get("href", "")
                    break
            eintraege.append({
                "titel": getattr(e, "title", "") or "",
                "link": getattr(e, "link", "") or "",
                "beschreibung": re.sub(
                    r"<[^>]+>", " ",
                    getattr(e, "summary", "")
                    or (getattr(e, "description", "") or "")),
                "datum": (getattr(e, "published", "")
                          or getattr(e, "updated", "")),
                "audio_url": audio,
            })
    except Exception:  # noqa: BLE001 – Fallback ohne feedparser
        eintraege = mini_feed_parser(text)
    return eintraege


# ---------------------------------------------------------------- Artikel / PDF
def _html_lesetext(html_text: str) -> tuple[str, str]:
    """Schlanker Notfall-Extrakt: <title> + Fließtext aus <p>/<h1-3>/<li>."""
    html_text = re.sub(r"<(script|style|nav|header|footer|aside|form)"
                       r"\b.*?</\1>", " ", html_text, flags=re.S | re.I)
    titel = _tag(html_text, "title")
    texte = []
    for m in re.finditer(r"<(p|h1|h2|h3|li)\b[^>]*>(.*?)</\1>",
                         html_text, re.S | re.I):
        absatz = html_mod.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))
        absatz = re.sub(r"\s+", " ", absatz).strip()
        if len(absatz) > 30:
            texte.append(absatz)
    return "\n\n".join(texte), titel


def hole_artikel(url: str) -> tuple[str, str]:
    """(text, titel) – trafilatura, sonst eingebauter HTML-Extrakt."""
    daten, _, fehler = http_get(url, timeout=30)
    if fehler or not daten:
        return "", ""
    html_text = daten.decode("utf-8", "replace")
    try:
        import trafilatura  # optionale Abhängigkeit
        text = trafilatura.extract(html_text, include_comments=False,
                                   include_tables=True,
                                   favor_recall=True) or ""
        if len(text) > 200:
            titel = ""
            ged = trafilatura.extract(html_text, output_format="json",
                                      include_comments=False)
            if ged:
                titel = (json.loads(ged).get("title") or "")
            return text, titel or _tag(html_text, "title")
    except Exception:  # noqa: BLE001
        pass
    return _html_lesetext(html_text)


def hole_pdf(wert: str, max_seiten: int = 40) -> str:
    """PDF-Text (URL oder lokaler Pfad) via pypdf."""
    daten = None
    if re.match(r"^https?://", wert):
        daten, _, fehler = http_get(wert, timeout=60, max_bytes=20_000_000)
        if fehler or not daten:
            print(f"  ⚠ PDF nicht ladbar: {fehler}")
            return ""
    else:
        pfad = wert if os.path.isabs(wert) else os.path.join(BLOG_DIR, wert)
        if not os.path.exists(pfad):
            print(f"  ⚠ PDF nicht gefunden: {pfad}")
            return ""
        with open(pfad, "rb") as fh:
            daten = fh.read()
    try:
        from pypdf import PdfReader
    except Exception:  # noqa: BLE001
        print("  ⚠ pypdf nicht installiert – PDF-Extraktion übersprungen "
              "(pip install pypdf)")
        return ""
    try:
        leser = PdfReader(io.BytesIO(daten))
        seiten = []
        for i, seite in enumerate(leser.pages[:max_seiten]):
            seiten.append(seite.extract_text() or "")
            if sum(len(s) for s in seiten) > 60_000:
                break
        return "\n\n".join(s for s in seiten if s.strip())
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠ PDF nicht lesbar: {e}")
        return ""


# ---------------------------------------------------------------- Audio (Gratis-Whisper auf Groq, opt-in)
def transkribiere_audio(url: str, max_mb: int = 24) -> tuple[str | None, str]:
    """Podcast-Audio → Text via Groq Whisper (Gratis-Tier, opt-in).

    Grenzen des Gratis-Tiers: 25 MB pro Datei – größere Episoden werden
    sauber übersprungen (Shownotes bleiben die Basis der Karte).
    """
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        return None, "kein GROQ_API_KEY"
    daten, _, fehler = http_get(url, timeout=120, max_bytes=max_mb * 1_000_000)
    if fehler or not daten:
        return None, f"audio nicht ladbar ({fehler})"
    try:
        grenze = "----poppy" + datetime.datetime.now().strftime("%H%M%S%f")
        body = io.BytesIO()
        body.write(f"--{grenze}\r\n".encode())
        body.write(b'Content-Disposition: form-data; name="model"\r\n\r\n')
        body.write("whisper-large-v3-turbo\r\n".encode())
        body.write(f"--{grenze}\r\n".encode())
        body.write(
            b'Content-Disposition: form-data; name="file"; '
            b'filename="episode.mp3"\r\n'
            b'Content-Type: audio/mpeg\r\n\r\n')
        body.write(daten)
        body.write(f"\r\n--{grenze}--\r\n".encode())
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            data=body.getvalue(),
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": f"multipart/form-data; boundary={grenze}",
                     "User-Agent": USER_AGENT},
            method="POST")
        with urllib.request.urlopen(req, timeout=300) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return (payload.get("text") or "").strip(), "groq-whisper"
    except Exception as e:  # noqa: BLE001
        return None, f"whisper fehlgeschlagen ({type(e).__name__}: {e})"


# ---------------------------------------------------------------- Karten-Board
def lade_einstellungen() -> dict:
    defaults = {
        "max_karten_pro_lauf": 3,
        "max_verwertung_pro_lauf": 2,
        "transkript_max_zeichen": 20000,
        "quelle_max_zeichen": 24000,
        "audio_transkription": False,
    }
    try:
        if os.path.exists(QUELLEN_FILE):
            with open(QUELLEN_FILE, encoding="utf-8") as fh:
                cfg = yaml.safe_load(fh) or {}
            einst = cfg.get("einstellungen") or {}
            defaults.update({k: v for k, v in einst.items() if k in defaults})
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠ quellen.yaml nicht lesbar ({e}) – Defaults aktiv.")
    return defaults


def lade_watchlist() -> list[dict]:
    try:
        if os.path.exists(QUELLEN_FILE):
            with open(QUELLEN_FILE, encoding="utf-8") as fh:
                cfg = yaml.safe_load(fh) or {}
            return [q for q in (cfg.get("watchlist") or [])
                    if isinstance(q, dict) and q.get("aktiv")]
    except Exception:  # noqa: BLE001
        return []
    return []


def karten_datei(karten_id: str) -> str:
    return os.path.join(CARD_DIR, f"{karten_id}.json")


def lade_karten() -> list[dict]:
    karten = []
    if not os.path.isdir(CARD_DIR):
        return karten
    for name in os.listdir(CARD_DIR):
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(CARD_DIR, name), encoding="utf-8") as fh:
                karten.append(json.load(fh))
        except Exception:  # noqa: BLE001 – kaputte Karte wirft das Board nie
            continue
    karten.sort(key=lambda k: k.get("id", ""), reverse=True)
    return karten


def speichere_karte(karte: dict) -> str:
    os.makedirs(CARD_DIR, exist_ok=True)
    pfad = karten_datei(karte["id"])
    with open(pfad, "w", encoding="utf-8") as fh:
        json.dump(karte, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return pfad


def protokolliere(karte: dict, ereignis: str) -> None:
    karte.setdefault("historie", []).append(
        {"zeit": now_utc_iso(), "ereignis": ereignis})


def karte_existiert(quelle_url: str) -> bool:
    """Dedupe über die Quell-URL (Video-ID, Feed-Link, …)."""
    if not quelle_url:
        return False
    ziel = quelle_url.strip().rstrip("/")
    for karte in lade_karten():
        if str(karte.get("quelle", {}).get("url", "")).rstrip("/") == ziel:
            return True
    return False


def neue_karte(typ: str, *, titel: str, url: str, rohtext: str,
               autor: str = "", datum: str = "",
               methode: str = "", hinweis: str = "") -> dict:
    """Karten-Factory – Schema des Boards (Single Source of Truth)."""
    karte = {
        "id": f"{heute_iso()}-{slugify(titel or url)[:60]}",
        "status": STATUS_NEU,
        "quelle": {
            "typ": typ, "titel": titel, "url": url,
            "autor": autor, "veroeffentlicht": datum,
        },
        "inhalt": {
            "rohtext": rohtext,
            "zeichen": len(rohtext or ""),
            "methode": methode,
            "hinweis": hinweis,
        },
        "insights": [],
        "winkel": "",
        "pillar": "",
        "schlagworte": [],
        "erzeugnisse": {},
        "historie": [],
    }
    protokolliere(karte, f"Karte angelegt (Typ {typ}" +
                  (f", {methode})" if methode else ")"))
    return karte


# ---------------------------------------------------------------- LLM (Gratis-Kette)
def chat(system: str, prompt: str, *, kette: tuple = ("groq", "gemini"),
         temperature: float = 0.4, max_tokens: int = 4096):
    """(text|None, provider) – Kette aus data/poppy/quellen.yaml oder Env."""
    env_kette = os.environ.get("POPPY_PROVIDER_KETTE", "").strip()
    reihenfolge = (tuple(p.strip() for p in env_kette.split(",") if p.strip())
                   if env_kette else tuple(kette))
    for provider in reihenfolge:
        if provider not in ("groq", "gemini", "claude", "openai"):
            continue
        text = llm_client.chat(provider, prompt, system=system,
                               temperature=temperature, max_tokens=max_tokens)
        if text:
            return text, provider
    return None, ""


def extrahiere_json(text: str) -> dict | None:
    """Robustes JSON aus Modell-Antwort (Fences, Vorrede, Nachrede)."""
    if not text:
        return None
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.S)
    try:
        erg = json.loads(text)
        return erg if isinstance(erg, dict) else None
    except Exception:  # noqa: BLE001
        pass
    tiefe, start = 0, -1
    for i, zeichen in enumerate(text):
        if zeichen == "{":
            if tiefe == 0:
                start = i
            tiefe += 1
        elif zeichen == "}":
            tiefe -= 1
            if tiefe == 0 and start >= 0:
                try:
                    erg = json.loads(text[start:i + 1])
                    return erg if isinstance(erg, dict) else None
                except Exception:  # noqa: BLE001
                    start = -1
    return None


def lade_pillars() -> list[str]:
    """Pillar-Register (Themenwelten) aus dem Tag-Register lesen."""
    try:
        pfad = os.path.join(BLOG_DIR, "data", "seo", "tag_register.yaml")
        if os.path.exists(pfad):
            with open(pfad, encoding="utf-8") as fh:
                register = yaml.safe_load(fh) or {}
            pillars = sorted({str(e.get("pillar"))
                              for e in (register.get("tags")
                                        or register.get("register") or [])
                              if e.get("pillar")})
            if pillars:
                return pillars
    except Exception:  # noqa: BLE001
        pass
    return list(PILLAR_FALLBACK)


# ---------------------------------------------------------------- Insights (KI + Offline-Fallback)
INSIGHT_SYSTEM = """Du bist der Research-Analyst der Redaktion von \
FranksFinanzcheck (deutscher Finanzblog für Privathaushalte, Themen: \
Strom/Gas, DSL/Internet, Versicherungen, Konto, Mietwagen, Budget/Frugalismus). \
Du analysierst eine QUELLE und lieferst verwertbare Erkenntnisse für \
Artikel-Entwürfe. Antworte AUSSCHLIESSLICH mit validem JSON, ohne Vorrede.

Schema:
{
  "insights": ["3 bis 5 konkrete Erkenntnisse, je max. 200 Zeichen, \
Aussagen mit Zahlen aus der Quelle"],
  "winkel": "Ein Satz: welcher Artikel sich für Franks Leser daraus \
ableitet (konkret, alltagstauglich, kein Clickbait)",
  "pillar": "EINE Säule aus der erlaubten Liste",
  "schlagworte": ["3 bis 6 SEO-Schlagworte"],
  "artikel_titel": "Vorschlag für einen deutschen Artikel-Titel, \
30 bis 60 Zeichen, deutsche Satzschreibung (kein Title-Case)"
}

Regeln: ERFINDE NICHTS – nur was in der Quelle steht plus allgemeine \
Einordnung. Zugeordnete pillar MUSS aus der Liste sein. Ist die Quelle \
für den Blog nicht verwertbar, setze insights auf [] und pillar auf ""."""


def insights_offline(karte: dict) -> dict:
    """Heuristik ohne KI-Key: Sätze mit Zahlen + Pillar-Matching."""
    text = (karte.get("inhalt", {}).get("rohtext") or "")[:12000]
    titel = karte.get("quelle", {}).get("titel") or ""
    saetze = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text))
    bewertet = []
    for satz in saetze:
        satz = satz.strip()
        if not (40 <= len(satz) <= 220):
            continue
        score = 3 if re.search(r"\d", satz) else 0
        if re.search(r"€|Euro|Prozent|%|kWh", satz):
            score += 3
        bewertet.append((score, satz))
    bewertet.sort(key=lambda x: -x[0])
    insights = [s for score, s in bewertet if score >= 3][:5] or saetze[:3]
    insights = [kuerze(s, 200)[0] for s in insights]

    blob = f"{titel} {text[:4000]}".lower()
    pillar_punkte = {p: sum(1 for w in woerter if w in blob)
                     for p, woerter in PILLAR_SCHLUESSELWORTE.items()}
    pillar = max(pillar_punkte, key=lambda p: pillar_punkte[p])
    if pillar_punkte[pillar] == 0:
        pillar = ""
    titel_vorschlag = kuerze(titel or "Quelle verwerten", 58)[0]
    return {
        "insights": insights,
        "winkel": ("Zahlen und Fazit aus „{q}“ für Franks Leser in einem "
                   "eigenen Ratgeber aufbereiten.").format(
                       q=kuerze(titel, 60)[0]),
        "pillar": pillar,
        "schlagworte": [],
        "artikel_titel": titel_vorschlag,
    }


def insights_generieren(karte: dict) -> dict:
    """Insights per Gratis-KI; ohne Key/notfalls heuristisch."""
    rohtext = karte.get("inhalt", {}).get("rohtext") or ""
    quelle = karte.get("quelle", {})
    einstellungen = lade_einstellungen()
    auszug, _ = kuerze(rohtext, int(einstellungen["transkript_max_zeichen"]))
    prompt = (
        f"ERLAUBTE SÄULEN: {', '.join(lade_pillars())}\n\n"
        f"QUELLE ({quelle.get('typ')}): {quelle.get('titel') or '(ohne Titel)'}\n"
        f"URL: {quelle.get('url') or '-'}\n"
        f"AUTOR/Herausgeber: {quelle.get('autor') or 'unbekannt'}\n\n"
        f"QUELLENTTEXT:\n{auszug or '(kein Text – nur Titel/Shownotes)'}\n\n"
        "Analysiere die Quelle jetzt und antworte nur mit JSON.")
    text, provider = chat(INSIGHT_SYSTEM, prompt, temperature=0.2,
                          max_tokens=1200)
    erg = None
    if text:
        erg = extrahiere_json(text)
        if erg and not isinstance(erg.get("insights"), list):
            erg = None
    if not erg:
        erg = insights_offline(karte)
        provider = "offline-heuristik"
    # Fail-closed: Pillar immer gegen Register prüfen
    erlaubt = lade_pillars()
    if erg.get("pillar") not in erlaubt:
        erg["pillar"] = ""
    erg["insights"] = [kuerze(str(i), 220)[0]
                       for i in (erg.get("insights") or [])][:5]
    karte["insights"] = erg["insights"]
    karte["winkel"] = str(erg.get("winkel") or "")[:400]
    karte["pillar"] = erg.get("pillar") or ""
    karte["schlagworte"] = [str(s) for s in (erg.get("schlagworte") or [])][:6]
    karte.setdefault("artikel_titel", "")
    karte["artikel_titel"] = str(erg.get("artikel_titel") or "")[:80]
    protokolliere(karte, f"Insights generiert ({provider}, "
                   f"{len(karte['insights'])} Punkte)")
    return karte


# ---------------------------------------------------------------- Report
def schreibe_report(zeilen: list) -> None:
    stamp = datetime.datetime.now(datetime.timezone.utc)
    kopf = [
        "# POPPY-WERKBANK-REPORT",
        "",
        f"_Stand: {stamp.strftime('%d.%m.%Y %H:%M UTC')} – automatisch "
        "durch die Poppy-Werkbank (scripts/poppy_*.py) erzeugt._",
        "",
        f"Karten auf dem Board: `{len(lade_karten())}` – Board bauen mit "
        "`python3 scripts/poppy_board.py`, öffnen mit `npm run poppy:serve`.",
        "",
    ]
    with open(REPORT_FILE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(kopf + zeilen).rstrip() + "\n")


# ---------------------------------------------------------------- Selbsttest (fail-closed, Exit 2)
def selbsttest() -> int:
    print("Poppy-Werkbank – Selbsttest (offline)")
    fehler = []

    faelle = [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "youtube"),
        ("https://youtu.be/dQw4w9WgXcQ", "youtube"),
        ("https://www.youtube.com/@Finanztip/videos", "youtube_kanal"),
        ("https://www.youtube.com/feeds/videos.xml?channel_id=UCabc123",
         "youtube_kanal"),
        ("https://example.com/feed/", "feed"),
        ("https://example.com/podcast.rss", "feed"),
        ("podcast:https://example.com/feed.xml", "feed"),
        ("https://example.com/bericht.pdf", "pdf"),
        ("https://example.com/artikel/foobar", "artikel"),
        ("Einfach eine Notiz von Frank", "text"),
    ]
    for eingabe, erwartet in faelle:
        typ, _ = erkenne_typ(eingabe)
        if typ != erwartet:
            fehler.append(f"erkennt_typ: {eingabe!r} → {typ} (erwartet {erwartet})")

    if youtube_video_id("https://youtu.be/dQw4w9WgXcQ?t=1") != "dQw4w9WgXcQ":
        fehler.append("youtube_video_id hat die ID nicht erkannt")

    xml = ("<?xml version='1.0'?><rss><channel><item>"
           "<title><![CDATA[Strompreise 2026]]></title>"
           '<link>https://beispiel.de/a</link>'
           "<description>Der Preis steigt um 12 Prozent.</description>"
           '<enclosure url="https://beispiel.de/ep1.mp3" type="audio/mpeg"/>'
           "<pubDate>Mon, 1 Sep 2026 10:00:00 +0200</pubDate>"
           "</item></channel></rss>")
    eintraege = mini_feed_parser(xml)
    if not eintraege or eintraege[0]["titel"] != "Strompreise 2026" \
            or not eintraege[0]["audio_url"].endswith(".mp3"):
        fehler.append("mini_feed_parser hat Titel/Audio nicht erkannt")

    html_text = ("<html><head><title>Testseite</title></head><body>"
                 "<p>Dieser Absatz ist lang genug und zählt deshalb mit "
                 "zur Extraktion des Lesetextes.</p>"
                 "<script>ignore()</script></body></html>")
    lesetext, titel = _html_lesetext(html_text)
    if "lang genug" not in lesetext or titel != "Testseite":
        fehler.append("_html_lesetext hat Text/Titel nicht erkannt")

    # KI-WEG HERMETISCH (Dauerheilung Content-Engine v2 #138, 08.10.2026):
    # Hier stand „offline, da kein Key im Selbsttest“ – eine Annahme, keine
    # Garantie. Läuft der Selbsttest in einem Schritt MIT Schlüssel, fragte er
    # das Live-Modell, und dessen Säulenwahl entschied über Grün/Rot (genau
    # die Klasse, die Engine-Lauf #138 vor Phase 1 getötet hat). Der KI-Weg
    # läuft deshalb über eine Attrappe; geprüft werden beide Zweige:
    # Rückfall auf die Heuristik UND Fail-closed gegen eine erfundene Säule.
    mit_rueckfall = neue_karte("text", titel="Selbsttest-Karte", url="",
                               rohtext="Strom kostet 2026 rund 300 Euro mehr. "
                               "Ein Wechsel spart oft Geld.", methode="selbsttest")
    mit_ki = neue_karte("text", titel="Selbsttest-Karte", url="",
                        rohtext="Strom kostet 2026 rund 300 Euro mehr.",
                        methode="selbsttest")
    echter_chat = globals()["chat"]
    try:
        globals()["chat"] = lambda *_a, **_k: (None, "selbsttest-attrappe")
        insights_generieren(mit_rueckfall)
        globals()["chat"] = lambda *_a, **_k: (
            '{"insights": ["Strom wird teurer."], "pillar": "erfundene-saeule", '
            '"winkel": "w", "schlagworte": [], "artikel_titel": "t"}',
            "selbsttest-attrappe")
        insights_generieren(mit_ki)
    finally:
        globals()["chat"] = echter_chat
    karte = mit_rueckfall
    if not karte["insights"] or karte["pillar"] not in lade_pillars():
        fehler.append("insights_offline lieferte keine verwertbaren Insights")
    if karte["pillar"] != "strom-sparen":
        fehler.append(f"Pillar-Heuristik: {karte['pillar']!r} != strom-sparen")
    if mit_ki["pillar"] != "" or mit_ki["insights"] != ["Strom wird teurer."]:
        fehler.append("KI-Antwort mit erfundener Säule wird nicht fail-closed "
                      f"behandelt: pillar={mit_ki['pillar']!r}")

    for probe in ('{"a": 1}', '```json\n{"a": 1}\n```', 'Vorrede {"a": 1} Ende'):
        if not extrahiere_json(probe):
            fehler.append(f"extrahiere_json scheiterte an: {probe[:30]!r}")

    if fehler:
        print("  ✗ " + "\n  ✗ ".join(fehler))
        return 2
    print("  ✓ Quelltyp-Erkennung, Feed-/HTML-Fallback, Insights-Heuristik,")
    print("    JSON-Extraktion und Karten-Factory: in Ordnung.")
    return 0


if __name__ == "__main__":
    raise SystemExit(selbsttest())
