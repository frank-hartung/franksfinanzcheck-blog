#!/usr/bin/env python3
# ============================================================
#  SHORTS-SCHMIEDE – vertikale Kurzvideos aus Artikeln
#  ------------------------------------------------------------
#  AUFTRAG (Frank, 29.09.2026): Aus jedem Artikel entsteht
#  vollautomatisch ein 9:16-Kurzvideo für YouTube Shorts, Reels
#  und Co. – ohne manuellen Schnitt, auf Agentur-Niveau, 0 €.
#
#  ABLAUF
#    1 WÄHLEN     welcher Artikel dran ist (neu, noch kein Video)
#    2 DREHBUCH   Hook · 3 Punkte · Abbinder – nur aus Artikel-Material
#    3 PRÜFEN     hartes Gate (Zahlen belegt, keine Versprechen, Hinweis da)
#    4 SPRECHEN   Tonspur über die Vorlese-Kette des Blogs (edge-tts/Piper)
#    5 BAUEN      ffmpeg: Ken-Burns auf dem Cover, eingebrannte Untertitel,
#                 Fortschrittsbalken, Pflichthinweis, Marken-Fußzeile
#    6 AUSLIEFERN MP4 + Metadaten-JSON für den Upload
#
#  WARUM NICHTS DAVON GELD KOSTET: Bild = vorhandenes Cover,
#  Stimme = ff_voice_backends (edge-tts/Piper), Schnitt = ffmpeg,
#  Text = Artikel + optionale Gratis-KI (Groq/Gemini).
#
#  EHRLICHKEITSREGELN (fail-closed):
#    · Keine Zahl im Video, die nicht im Artikel steht.
#    · Kein Versprechen, kein Reißer, kein „Geheimtipp".
#    · Der Hinweis „keine Anlage- oder Rechtsberatung" ist ab
#      Sekunde 0 sichtbar – nicht verhandelbar.
#    · Fehlt ffmpeg oder das Cover, bricht der Lauf SAUBER ab
#      (kein halbes Video, keine stille Fehlausgabe).
#
#  Aufruf:
#    python3 scripts/social_video.py --plan              # was wäre dran?
#    python3 scripts/social_video.py --drehbuch --slug X # nur Text zeigen
#    python3 scripts/social_video.py --bauen --limit 1
#    python3 scripts/social_video.py --bauen --slug X --ohne-ton
#    python3 scripts/social_video.py --selftest
#
#  Regie: data/social/video.yaml
#  Anleitung: docs/ANLEITUNG-SHORTS-SCHMIEDE.md
# ============================================================
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shutil
import subprocess
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BLOG_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

CONFIG_PATH = os.path.join(BLOG_DIR, "data", "social", "video.yaml")
STATE_PATH = os.path.join(BLOG_DIR, "data", "social", "video_state.yaml")
REPORT_PATH = os.path.join(BLOG_DIR, "SOCIAL-VIDEO-STATUS.md")


# =============================================================== Grundlagen
def _yaml():
    import yaml
    return yaml


def load_config(path: str | None = None) -> dict:
    try:
        with open(path or CONFIG_PATH, encoding="utf-8") as fh:
            return _yaml().safe_load(fh) or {}
    except FileNotFoundError:
        return {}
    except Exception as exc:  # noqa: BLE001
        print(f"⚠ video.yaml nicht lesbar ({exc}) – Shorts-Schmiede im Leerlauf.")
        return {}


def load_state() -> dict:
    try:
        with open(STATE_PATH, encoding="utf-8") as fh:
            data = _yaml().safe_load(fh) or {}
    except Exception:  # noqa: BLE001
        data = {}
    data.setdefault("version", 1)
    data.setdefault("produziert", [])
    return data


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    state["produziert"] = (state.get("produziert") or [])[-400:]
    with open(STATE_PATH, "w", encoding="utf-8") as fh:
        _yaml().safe_dump(state, fh, allow_unicode=True, sort_keys=False, width=100)


def _now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def _berlin() -> str:
    try:
        from zoneinfo import ZoneInfo
        return _now().astimezone(ZoneInfo("Europe/Berlin")).strftime("%d.%m.%Y %H:%M")
    except Exception:  # noqa: BLE001
        return _now().strftime("%d.%m.%Y %H:%M")


def has_ffmpeg() -> bool:
    return bool(shutil.which("ffmpeg"))


_FILTER_CACHE: dict[str, bool] = {}


def hat_filter(name: str) -> bool:
    """Prüft, ob dieses ffmpeg den Filter kann.

    Wichtig, weil manche Builds (z. B. die pip-Variante imageio-ffmpeg)
    OHNE libfreetype kommen und damit kein `drawtext` haben. Ohne diese
    Prüfung bricht der Lauf mit der nichtssagenden Meldung
    „Filter not found" ab – hier sagt er stattdessen, was zu tun ist.
    """
    if name in _FILTER_CACHE:
        return _FILTER_CACHE[name]
    if not has_ffmpeg():
        _FILTER_CACHE[name] = False
        return False
    try:
        res = subprocess.run(["ffmpeg", "-hide_banner", "-filters"],
                             capture_output=True, text=True, timeout=30)
        _FILTER_CACHE[name] = bool(re.search(rf"^\s*\S+\s+{re.escape(name)}\s",
                                             res.stdout or "", re.M))
    except Exception:  # noqa: BLE001
        _FILTER_CACHE[name] = False
    return _FILTER_CACHE[name]


def umgebung() -> dict:
    """Was die Maschine kann – ehrlich und in Klartext."""
    cfg = load_config()
    schrift = os.path.join(BLOG_DIR, (cfg.get("marke") or {}).get("schrift", ""))
    return {
        "ffmpeg": has_ffmpeg(),
        "ffprobe": bool(shutil.which("ffprobe")),
        "drawtext": hat_filter("drawtext"),
        "zoompan": hat_filter("zoompan"),
        "schrift": os.path.exists(schrift),
        "schrift_pfad": schrift,
    }


# ================================================================ 1 · WÄHLEN
def kandidaten(cfg: dict) -> list[dict]:
    """Artikel, aus denen ein Video werden soll – neueste zuerst."""
    meta = cfg.get("meta") or {}
    try:
        import social_copywriter as cw
        pool = cw.article_pool(meta.get("base_url") or "https://franksfinanzcheck.de")
    except Exception as exc:  # noqa: BLE001
        print(f"⚠ Artikel nicht lesbar ({exc})")
        return []

    state = load_state()
    gebaut = {p.get("slug"): p for p in state.get("produziert") or []}
    fenster = _now() - _dt.timedelta(days=int(meta.get("neu_fenster_tage") or 21))
    wieder = _dt.timedelta(days=int(meta.get("wiedervorlage_tage") or 120))

    raus = []
    for art in pool:
        if art.get("draft") or art.get("reserve"):
            continue
        pub = _parse(art.get("published"))
        if pub and pub < fenster:
            continue
        alt = gebaut.get(art.get("slug"))
        if alt:
            wann = _parse(alt.get("zeit"))
            if not wann or (_now() - wann) < wieder:
                continue
        # Ohne Material kein Drehbuch – lieber gar nicht als dünn.
        if not (art.get("kurzantwort") or art.get("description")):
            continue
        if len(art.get("takeaways") or []) < 2:
            continue
        raus.append(art)
    raus.sort(key=lambda a: a.get("published") or "", reverse=True)
    return raus


def _parse(value) -> _dt.datetime | None:
    if not value:
        return None
    try:
        dt = _dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=_dt.timezone.utc)
    except Exception:  # noqa: BLE001
        return None


# ============================================================= 2 · DREHBUCH
_ZAHL_RX = re.compile(r"\d[\d.,]*\s?(?:€|%|Euro|Prozent|kWh|Mbit)?", re.I)


def drehbuch(art: dict, cfg: dict) -> dict:
    """Baut das Drehbuch AUSSCHLIESSLICH aus Artikel-Material."""
    szenen_cfg = cfg.get("szenen") or []
    pflicht = cfg.get("pflicht") or {}
    marke = cfg.get("marke") or {}

    kurz = (art.get("kurzantwort") or art.get("description") or "").strip()
    saetze = [s.strip() for s in re.split(r"(?<=[.!?])\s+", kurz) if len(s.strip()) > 15]
    takeaways = [t for t in (art.get("takeaways") or []) if len(t) > 15]
    zahlen = art.get("numbers") or []

    szenen: list[dict] = []
    for i, s in enumerate(szenen_cfg):
        typ = s.get("typ")
        grenze = int(s.get("max_zeichen") or 130)
        if typ == "hook":
            text = _hook(art, zahlen, saetze, grenze)
        elif typ == "cta":
            text = _kuerze(
                f"Den vollständigen Ratgeber findest du auf {marke.get('domain') or 'dem Blog'}.",
                grenze)
        else:
            idx = len([x for x in szenen if x["typ"] == "punkt"])
            quelle = takeaways[idx] if idx < len(takeaways) else (
                saetze[idx + 1] if idx + 1 < len(saetze) else "")
            if not quelle:
                continue
            text = _kuerze(_saubern(quelle), grenze)
        if not text:
            continue
        szenen.append({"typ": typ, "text": text,
                       "sekunden": float(s.get("sekunden") or 8),
                       "untertitel": _umbrechen(text, cfg)})

    # Die stärkste Zahl gehört in die Mitte (Aufmerksamkeitsdelle).
    szenen = _zahl_in_die_mitte(szenen)

    db = {
        "slug": art.get("slug"),
        "titel": art.get("title"),
        "url": art.get("url"),
        "pillar": art.get("pillar"),
        "cover": art.get("cover"),
        "szenen": szenen,
        "sprechtext": " ".join(s["text"] for s in szenen),
        "hinweis": pflicht.get("hinweis") or "",
        "erstellt": _now().isoformat(),
        "quelle_text": " ".join(filter(None, [art.get("title"), art.get("kurzantwort"),
                                              art.get("description"),
                                              " ".join(art.get("takeaways") or [])])),
    }
    db["metadaten"] = metadaten(db, art, cfg)
    db = poliere(db, cfg)
    db["dauer"] = round(sum(_sprechdauer(s["text"]) for s in db["szenen"]), 1)
    return db


def _hook(art: dict, zahlen: list, saetze: list, grenze: int) -> str:
    """Erste Sekunde: eine echte Aussage mit Zahl – oder eine Frage.

    Reihenfolge nach Wirkung: Ein Satz aus dem Artikel, der eine Zahl
    trägt, schlägt alles. Danach die FAQ-Frage (Fragen halten Zuschauer),
    danach der erste Satz der Kurzantwort. Der Titel ist die letzte Wahl –
    Überschriften klingen gesprochen fast immer wie Werbung.
    """
    mit_zahl = [s for s in saetze
                if _ZAHL_RX.search(s) and len(re.sub(r"\D", "", _ZAHL_RX.search(s).group(0))) >= 2]
    if mit_zahl:
        return _kuerze(mit_zahl[0], grenze)
    if art.get("faq_question"):
        frage = _kuerze(_saubern(art["faq_question"]), grenze)
        return frage if frage.endswith("?") else frage.rstrip(".") + "?"
    if zahlen:
        kern = _saubern(art.get("title") or "")
        kern = kern.split(":", 1)[-1].strip() if ":" in kern else kern
        if kern:
            return _kuerze(f"{str(zahlen[0]).strip()}: {kern[0].lower() + kern[1:]}", grenze)
    if saetze:
        return _kuerze(saetze[0], grenze)
    return _kuerze(_saubern(art.get("title") or ""), grenze)


def _saubern(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", str(text or ""))
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    text = re.sub(r"[*_`#>]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _heilen(text: str) -> str:
    """Repariert Satzreste, die beim Kürzen entstehen können.

    Eine offene Klammer oder ein einsames „z. B." am Satzende klingt
    gesprochen wie ein Aussetzer – und genau daran erkennt ein Zuschauer
    einen Automaten.
    """
    text = (text or "").strip()
    if text.count("(") > text.count(")"):
        text = text[:text.rfind("(")].rstrip(" ,;:–-")
    text = re.sub(r"\s+(z\.\s?B\.|bzw\.|etwa|ca\.|u\.\s?a\.)$", "", text, flags=re.I)
    text = text.rstrip(" ,;:–-")
    if text and text[-1] not in ".!?":
        text += "."
    return text


def _saetze(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", _saubern(text)) if s.strip()]


def _kuerze(text: str, grenze: int) -> str:
    """Kürzt auf Sprechlänge – aber niemals mitten im Satz.

    Ein abgeschnittener Satz („… und.") ist der sicherste Weg, ein Video
    wie einen Bot aussehen zu lassen. Deshalb in dieser Reihenfolge:
    ganze Sätze → ganzer Teilsatz bis zum letzten Komma/Gedankenstrich →
    erst zuletzt (und nur im Notfall) auf Wortgrenze.
    """
    text = _saubern(text)
    if len(text) <= grenze:
        return _heilen(text)

    # 1) So viele VOLLSTÄNDIGE Sätze wie hineinpassen.
    gesammelt = ""
    for satz in _saetze(text):
        kandidat = f"{gesammelt} {satz}".strip()
        if len(kandidat) <= grenze:
            gesammelt = kandidat
        else:
            break
    if len(gesammelt) >= max(40, grenze * 0.45):
        return _heilen(gesammelt)

    # 2) Erster Satz, am letzten Teilsatz-Zeichen vor der Grenze gekappt.
    erster = _saetze(text)[0] if _saetze(text) else text
    fenster = erster[:grenze]
    schnitt = max(fenster.rfind(", "), fenster.rfind("; "), fenster.rfind(" – "),
                  fenster.rfind(": "))
    if schnitt >= max(40, grenze * 0.45):
        return _heilen(fenster[:schnitt])

    # 3) Notfall: Wortgrenze, aber ohne Satzruine am Ende.
    rest = fenster.rsplit(" ", 1)[0] if " " in fenster else fenster
    rest = re.sub(r"\s+(und|oder|aber|mit|für|von|die|der|das|dem|den|im|in|zu|bei)$",
                  "", rest.rstrip(" ,;:–-"), flags=re.I)
    return _heilen(rest)


def _umbrechen(text: str, cfg: dict) -> list[str]:
    u = cfg.get("untertitel") or {}
    breite = int(u.get("zeichen_pro_zeile") or 26)
    maxz = int(u.get("zeilen_max") or 3)
    worte, zeilen, akt = text.split(), [], ""
    for w in worte:
        if len(akt) + len(w) + 1 <= breite:
            akt = f"{akt} {w}".strip()
        else:
            zeilen.append(akt)
            akt = w
    if akt:
        zeilen.append(akt)
    return zeilen[:maxz]


def _zahl_in_die_mitte(szenen: list[dict]) -> list[dict]:
    punkte = [i for i, s in enumerate(szenen) if s["typ"] == "punkt"]
    if len(punkte) < 3:
        return szenen
    mit_zahl = [i for i in punkte if _ZAHL_RX.search(szenen[i]["text"])
                and len(re.sub(r"\D", "", _ZAHL_RX.search(szenen[i]["text"]).group(0))) >= 2]
    if not mit_zahl:
        return szenen
    mitte = punkte[len(punkte) // 2]
    quelle = mit_zahl[0]
    if quelle != mitte:
        szenen[mitte], szenen[quelle] = szenen[quelle], szenen[mitte]
    return szenen


def _sprechdauer(text: str) -> float:
    """Sprechdauer in Sekunden.

    Deutsche Nachrichtenlesung liegt bei rund 12,5 Zeichen/s; dazu kommt
    eine knappe Atempause je Szene. Der Wert ist die PLANGRÖSSE – beim
    echten Bau gilt die gemessene Länge der Tonspur (Bild folgt dem Ton).
    """
    return max(2.4, len(text) / 12.5 + 0.7)


def metadaten(db: dict, art: dict, cfg: dict) -> dict:
    """Titel, Beschreibung und Hashtags je Zielkanal."""
    pflicht = cfg.get("pflicht") or {}
    kan = cfg.get("kanaele") or {}
    tags = [t for t in (art.get("tags") or [])][:5]
    hash_basis = ["#" + re.sub(r"[^A-Za-zÄÖÜäöüß0-9]", "", t) for t in tags if t]

    yt = kan.get("youtube") or {}
    titel = _kuerze(art.get("title") or "", int(yt.get("titel_max") or 100) - 9)
    beschreibung = "\n\n".join(filter(None, [
        _saubern(art.get("kurzantwort") or art.get("description") or ""),
        f"Vollständiger Ratgeber: {art.get('url')}",
        (pflicht.get("beschreibung_hinweis") or "").strip(),
        " ".join(dict.fromkeys((yt.get("hashtags") or []) + hash_basis)),
    ]))
    return {
        "youtube": {"titel": f"{titel} #Shorts",
                    "beschreibung": beschreibung[:int(yt.get("beschreibung_max") or 4900)],
                    "kategorie_id": yt.get("kategorie_id") or "22",
                    "privatsphaere": yt.get("privatsphaere") or "public",
                    "tags": tags},
        "instagram": {"beschreibung": _kuerze(
            "\n\n".join(filter(None, [
                _saubern(art.get("kurzantwort") or ""),
                "Ganzer Ratgeber: Link in der Bio.",
                (pflicht.get("beschreibung_hinweis") or "").strip(),
                " ".join(dict.fromkeys(((kan.get("instagram") or {}).get("hashtags") or [])
                                        + hash_basis)),
            ])), 2200)},
    }


def poliere(db: dict, cfg: dict) -> dict:
    """Optionale KI-Politur der Szenentexte. Bei Zweifel gilt das Original."""
    llm_cfg = (cfg.get("meta") or {}).get("llm") or {}
    mode = (os.environ.get("VIDEO_LLM_MODE") or llm_cfg.get("mode") or "auto").lower()
    if mode == "off":
        return db
    try:
        import llm_client
    except Exception:  # noqa: BLE001
        return db
    provider = next((p for p in (llm_cfg.get("providers") or ["groq", "gemini"])
                     if llm_client.available(p)), "")
    if not provider:
        return db

    grenzen = [int((s.get("max_zeichen") or 130)) for s in (cfg.get("szenen") or [])]
    system = (
        "Du bist Video-Redakteur eines deutschen Finanzblogs und schreibst "
        "Sprechtexte für ein 9:16-Kurzvideo um – gesprochene Sprache, kurze Sätze.\n"
        "HARTE REGELN:\n"
        "- Gib GENAU so viele Zeilen zurück wie du bekommst, eine Szene pro Zeile, "
        "ohne Nummerierung.\n"
        "- KEINE neue Zahl, kein neuer Fakt, kein Link. Nur umformulieren.\n"
        "- Keine Werbesprache, kein „Geheimtipp\", keine Handlungsempfehlung.\n"
        "- Zeile 1 ist der Aufhänger und muss in unter 3 Sekunden sprechbar sein."
    )
    nutzer = "\n".join(s["text"] for s in db["szenen"])
    try:
        out = llm_client.chat(provider=provider, messages=[{"role": "user", "content": nutzer}],
                              system=system,
                              temperature=float(llm_cfg.get("temperature") or 0.4),
                              max_tokens=int(llm_cfg.get("max_tokens") or 700))
    except Exception:  # noqa: BLE001
        return db
    zeilen = [_saubern(z) for z in (out or "").splitlines() if _saubern(z)]
    if len(zeilen) != len(db["szenen"]):
        return db
    kandidat = []
    for i, (szene, neu) in enumerate(zip(db["szenen"], zeilen)):
        grenze = grenzen[i] if i < len(grenzen) else 130
        if len(neu) > grenze:
            return db
        kandidat.append(dict(szene, text=neu, untertitel=_umbrechen(neu, cfg)))
    # Die Politur darf keine Zahl erfinden – sonst gilt das Original.
    if not _zahlen_belegt(" ".join(s["text"] for s in kandidat), db["quelle_text"]):
        return db
    db["szenen"] = kandidat
    db["sprechtext"] = " ".join(s["text"] for s in kandidat)
    db["politur"] = provider
    return db


# =============================================================== 3 · PRÜFEN
def pruefe(db: dict, cfg: dict) -> list[str]:
    """Hartes Gate. Leere Liste = produzierbar."""
    g = cfg.get("gate") or {}
    f = cfg.get("format") or {}
    fehler: list[str] = []
    szenen = db.get("szenen") or []

    if len(szenen) < int(g.get("min_szenen") or 4):
        fehler.append(f"zu wenige Szenen ({len(szenen)})")
    if len(szenen) > int(g.get("max_szenen") or 6):
        fehler.append(f"zu viele Szenen ({len(szenen)})")

    gesamt = sum(_sprechdauer(s["text"]) for s in szenen)
    if gesamt < float(f.get("min_sekunden") or 28):
        fehler.append(f"zu kurz ({gesamt:.1f}s < {f.get('min_sekunden')}s)")
    if gesamt > float(f.get("max_sekunden") or 52):
        fehler.append(f"zu lang ({gesamt:.1f}s > {f.get('max_sekunden')}s)")

    volltext = " ".join(s["text"] for s in szenen)
    low = volltext.lower()
    for phrase in g.get("verbotene_phrasen") or []:
        if phrase and phrase.lower() in low:
            fehler.append(f"verbotene Formulierung: „{phrase}\"")
    for muster in g.get("verbotene_link_muster") or []:
        if muster and muster in volltext:
            fehler.append(f"verbotenes Linkmuster „{muster}\"")

    if g.get("zahl_pflicht", True):
        starke = [z for z in _ZAHL_RX.findall(volltext) if len(re.sub(r"\D", "", z)) >= 2]
        if not starke:
            fehler.append("keine belastbare Zahl im Video (bei Geldthemen Pflicht)")
    if g.get("zahlen_nur_aus_artikel", True) and not _zahlen_belegt(volltext, db.get("quelle_text", "")):
        fehler.append("Zahl im Video steht nicht im Artikel")

    if g.get("untertitel_pflicht", True):
        if any(not s.get("untertitel") for s in szenen):
            fehler.append("Szene ohne Untertitel")
    if g.get("hinweis_pflicht", True) and not (db.get("hinweis") or "").strip():
        fehler.append("Pflichthinweis (keine Beratung) fehlt")
    if not db.get("cover"):
        fehler.append("kein Cover-Bild – ohne Motiv kein Video")

    return fehler


def _zahlen_belegt(text: str, quelle: str) -> bool:
    quelle_ziffern = re.sub(r"[^\d]", "", quelle or "")
    for z in _ZAHL_RX.findall(text or ""):
        ziffern = re.sub(r"\D", "", z)
        if len(ziffern) < 2:
            continue
        if ziffern not in quelle_ziffern and z.strip() not in (quelle or ""):
            return False
    return True


# ============================================================= 4 · SPRECHEN
def sprich(db: dict, cfg: dict, arbeit: str) -> tuple[list[str], str]:
    """Erzeugt je Szene eine WAV-Datei. Rückgabe: (pfade, engine)."""
    st = cfg.get("stimme") or {}
    try:
        import ff_voice_backends as vb
    except Exception as exc:  # noqa: BLE001
        return [], f"Stimme nicht verfügbar ({str(exc)[:60]})"
    pfade, engine_used = [], ""
    for i, szene in enumerate(db["szenen"]):
        out = os.path.join(arbeit, f"szene{i:02d}.wav")
        try:
            engine, ok, _ = vb.synthesize(
                text=szene["text"], lang=st.get("sprache") or "de",
                engine="", profile_name=st.get("profil") or "news",
                out_wav=out, rate=float(st.get("tempo") or 1.0))
        except Exception as exc:  # noqa: BLE001
            return pfade, f"Synthese abgebrochen ({str(exc)[:60]})"
        if not ok or not os.path.exists(out):
            return pfade, f"Szene {i + 1} ohne Ton"
        engine_used = engine or engine_used
        pfade.append(out)
    return pfade, engine_used


def _dauer(pfad: str) -> float:
    if not shutil.which("ffprobe"):
        return 0.0
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", pfad],
            capture_output=True, text=True, timeout=30)
        return float((out.stdout or "0").strip() or 0)
    except Exception:  # noqa: BLE001
        return 0.0


# ================================================================ 5 · BAUEN
def _esc(text: str) -> str:
    """Escaping für ffmpeg-drawtext (Doppelstufe: Filtergraph + drawtext)."""
    return (str(text).replace("\\", "\\\\").replace(":", "\\:")
            .replace("'", "\u2019").replace("%", "\\%")
            .replace("[", "\\[").replace("]", "\\]").replace(",", "\\,"))


def filtergraph(db: dict, cfg: dict, dauern: list[float]) -> tuple[str, float]:
    """Baut die komplette ffmpeg-Filterkette. Rein funktional – testbar."""
    f = cfg.get("format") or {}
    m = cfg.get("marke") or {}
    u = cfg.get("untertitel") or {}
    p = cfg.get("pflicht") or {}
    B, H = int(f.get("breite") or 1080), int(f.get("hoehe") or 1920)
    fps = int(f.get("fps") or 30)
    gesamt = sum(dauern)
    font = (m.get("schrift") or "static/fonts/Inter-Bold.ttf").replace(":", "\\:")

    zoom = float(m.get("zoom_faktor") or 1.12)
    frames = max(int(gesamt * fps), fps)
    teile = [
        # Cover formatfüllend, dann langsame Ken-Burns-Fahrt.
        f"[0:v]scale={B * 2}:{H * 2}:force_original_aspect_ratio=increase,"
        f"crop={B * 2}:{H * 2},"
        f"zoompan=z='min(zoom+{(zoom - 1) / frames:.8f},{zoom})':d={frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={B}x{H}:fps={fps},"
        f"eq=brightness=-{float(m.get('bild_abdunklung') or 0.55) / 2:.3f}:saturation=0.9,"
        f"boxblur=2:1[bg]",
        # Abdunklung: Untertitel müssen IMMER lesbar sein.
        f"color=c={m.get('farbe_grund') or '0x0E1B2A'}@{float(m.get('bild_abdunklung') or 0.55)}:"
        f"s={B}x{H}:d={gesamt:.2f}:r={fps}[dim]",
        "[bg][dim]overlay=0:0[base]",
    ]

    kette = "base"
    zeit = 0.0
    groesse = int(u.get("schriftgroesse") or 62)
    rand = int(u.get("rand_unten") or 420)
    for i, (szene, d) in enumerate(zip(db["szenen"], dauern)):
        start, ende = zeit, zeit + d
        zeilen = szene.get("untertitel") or [szene["text"]]
        # Hook größer setzen – die erste Sekunde muss aus dem Feed springen.
        gr = int(groesse * (1.18 if szene["typ"] == "hook" else 1.0))
        block = len(zeilen) * (gr + 16)
        for j, zeile in enumerate(zeilen):
            y = H - rand - block + j * (gr + 16)
            farbe = (m.get("farbe_akzent") if (u.get("akzent_bei_zahlen", True)
                                               and _ZAHL_RX.search(zeile)
                                               and len(re.sub(r"\D", "", zeile)) >= 2)
                     else m.get("farbe_text")) or "0xFFFFFF"
            aus = f"out_{i}_{j}"
            teile.append(
                f"[{kette}]drawtext=fontfile='{font}':text='{_esc(zeile)}':"
                f"fontsize={gr}:fontcolor={farbe}:x=(w-text_w)/2:y={y}:"
                f"box={1 if u.get('box', True) else 0}:"
                f"boxcolor={m.get('farbe_grund') or '0x0E1B2A'}@{float(u.get('box_deckkraft') or 0.45)}:"
                f"boxborderw=18:shadowcolor={m.get('farbe_schatten') or '0x000000'}@0.6:"
                f"shadowx=2:shadowy=3:"
                f"enable='between(t,{start:.2f},{ende:.2f})'[{aus}]")
            kette = aus
        zeit = ende

    # Dauerhafte Pflicht-Einblendung + Marken-Fußzeile.
    klein = int(p.get("hinweis_schriftgroesse") or 30)
    if (p.get("hinweis") or "").strip():
        teile.append(
            f"[{kette}]drawtext=fontfile='{font}':text='{_esc(p['hinweis'])}':"
            f"fontsize={klein}:fontcolor={m.get('farbe_text') or '0xFFFFFF'}@0.75:"
            f"x=(w-text_w)/2:y=h-120:box=1:boxcolor=0x000000@0.35:boxborderw=10[hinw]")
        kette = "hinw"
    if (p.get("fusszeile") or "").strip():
        teile.append(
            f"[{kette}]drawtext=fontfile='{font}':text='{_esc(p['fusszeile'])}':"
            f"fontsize={klein + 6}:fontcolor={m.get('farbe_akzent') or '0xE9B44C'}:"
            f"x=(w-text_w)/2:y=110[fuss]")
        kette = "fuss"

    # Fortschrittsbalken: zeigt, dass es gleich vorbei ist – hält die Rate hoch.
    teile.append(
        f"[{kette}]drawbox=x=0:y=h-8:w='iw*t/{max(gesamt, 0.1):.2f}':h=8:"
        f"color={m.get('farbe_akzent') or '0xE9B44C'}@0.9:t=fill[vout]")
    return ";".join(teile), gesamt


def baue(db: dict, cfg: dict, ohne_ton: bool = False, ziel: str | None = None) -> dict:
    """Rendert das Video. Rückgabe: Ergebnis-Bündel (nie eine Exception)."""
    f = cfg.get("format") or {}
    meta = cfg.get("meta") or {}
    ausgabe = os.path.join(BLOG_DIR, meta.get("ausgabe_verzeichnis") or ".cache/social-video")
    os.makedirs(ausgabe, exist_ok=True)
    arbeit = os.path.join(ausgabe, f"_arbeit-{db['slug']}")
    os.makedirs(arbeit, exist_ok=True)
    ziel = ziel or os.path.join(ausgabe, f"{db['slug']}.mp4")

    if not has_ffmpeg():
        return {"ok": False, "grund": "ffmpeg fehlt (apt-get install -y ffmpeg)"}
    if not hat_filter("drawtext"):
        return {"ok": False, "grund": "dieses ffmpeg kann kein drawtext (ohne libfreetype "
                                      "gebaut) – Untertitel sind Pflicht, deshalb kein Video. "
                                      "Abhilfe: apt-get install -y ffmpeg"}
    schrift = os.path.join(BLOG_DIR, (cfg.get("marke") or {}).get("schrift", ""))
    if not os.path.exists(schrift):
        return {"ok": False, "grund": f"Schriftdatei fehlt: {schrift}"}

    cover = _cover_pfad(db, cfg)
    if not cover:
        return {"ok": False, "grund": "Cover-Bild nicht gefunden"}

    # --- Ton ----------------------------------------------------------
    tonspuren, engine = ([], "stumm") if ohne_ton else sprich(db, cfg, arbeit)
    if not ohne_ton and not tonspuren:
        if not (cfg.get("stimme") or {}).get("stille_erlaubt", True):
            return {"ok": False, "grund": f"Tonspur fehlgeschlagen: {engine}"}
        print(f"⚠ Ohne Tonspur ({engine}) – Video wird stumm gebaut.")
        tonspuren, engine = [], "stumm"

    if tonspuren:
        dauern = [max(_dauer(t) + 0.35, 2.0) for t in tonspuren]
    else:
        dauern = [_sprechdauer(s["text"]) for s in db["szenen"]]

    graph, gesamt = filtergraph(db, cfg, dauern)

    # --- Zusammenbau ---------------------------------------------------
    ton_datei = ""
    if tonspuren:
        ton_datei = os.path.join(arbeit, "ton.wav")
        liste = os.path.join(arbeit, "ton.txt")
        with open(liste, "w", encoding="utf-8") as fh:
            for t in tonspuren:
                fh.write(f"file '{os.path.abspath(t)}'\n")
        rc = _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", liste,
                   "-filter:a", f"loudnorm=I={f.get('loudness_lufs') or -14}:TP=-1.5:LRA=11",
                   "-ar", "48000", "-ac", "2", ton_datei])
        if rc != 0:
            ton_datei = ""

    cmd = ["ffmpeg", "-y", "-loop", "1", "-t", f"{gesamt:.2f}", "-i", cover]
    if ton_datei:
        cmd += ["-i", ton_datei]
    cmd += ["-filter_complex", graph, "-map", "[vout]"]
    if ton_datei:
        cmd += ["-map", "1:a", "-c:a", f.get("audio_codec") or "aac",
                "-b:a", f.get("audio_bitrate") or "160k", "-shortest"]
    cmd += ["-c:v", f.get("video_codec") or "libx264", "-preset", f.get("preset") or "medium",
            "-crf", str(f.get("crf") or 21), "-pix_fmt", "yuv420p",
            "-r", str(f.get("fps") or 30), "-movflags", "+faststart", ziel]

    rc = _run(cmd)
    if rc != 0 or not os.path.exists(ziel):
        return {"ok": False, "grund": f"ffmpeg brach ab (Code {rc})"}

    json_pfad = os.path.splitext(ziel)[0] + ".json"
    with open(json_pfad, "w", encoding="utf-8") as fh:
        json.dump({"slug": db["slug"], "titel": db["titel"], "url": db["url"],
                   "dauer": round(gesamt, 1), "engine": engine,
                   "szenen": db["szenen"], "metadaten": db["metadaten"],
                   "gebaut": _now().isoformat()}, fh, ensure_ascii=False, indent=2)

    shutil.rmtree(arbeit, ignore_errors=True)
    groesse = os.path.getsize(ziel) / (1024 * 1024)
    return {"ok": True, "datei": ziel, "json": json_pfad, "dauer": round(gesamt, 1),
            "engine": engine, "mb": round(groesse, 1)}


def _cover_pfad(db: dict, cfg: dict) -> str:
    """9:16-Variante bevorzugen, sonst das Original-Cover."""
    slug = db.get("slug") or ""
    try:
        import social_images
        pfad = social_images.target_path(slug, "9:16")
        if not os.path.exists(pfad):
            original = _original_cover(db)
            if original:
                try:
                    social_images.render(original, pfad, "9:16")  # type: ignore[attr-defined]
                except Exception:  # noqa: BLE001
                    pass
        if os.path.exists(pfad):
            return pfad
    except Exception:  # noqa: BLE001
        pass
    return _original_cover(db)


def _original_cover(db: dict) -> str:
    cover = (db.get("cover") or "").lstrip("/")
    if not cover:
        return ""
    for basis in (os.path.join(BLOG_DIR, "static"), BLOG_DIR,
                  os.path.join(BLOG_DIR, "content", "posts", db.get("slug") or "")):
        pfad = os.path.join(basis, cover)
        if os.path.exists(pfad):
            return pfad
    name = os.path.basename(cover)
    kandidat = os.path.join(BLOG_DIR, "static", "images", "covers", name)
    return kandidat if os.path.exists(kandidat) else ""


def _run(cmd: list[str], timeout: int = 900) -> int:
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=BLOG_DIR)
        if res.returncode != 0:
            print("   ffmpeg: " + (res.stderr or "")[-400:].replace("\n", " "))
        return res.returncode
    except subprocess.TimeoutExpired:
        print("   ffmpeg: Zeitüberschreitung")
        return 124
    except Exception as exc:  # noqa: BLE001
        print(f"   ffmpeg: {exc}")
        return 1



# =========================================================== 6 · AUSLIEFERN
#  Der Upload ist bewusst Teil DIESES Skripts und nicht des Social-
#  Autopiloten: Ein Video ist kein Textbeitrag. Es hat eigene Limits,
#  eigene Pflichtfelder und einen mehrstufigen Upload – das gehört zur
#  Produktion, nicht zur Textredaktion.

def youtube_token() -> str:
    """Frisches Access-Token aus dem Refresh-Token (OAuth2, kostenlos)."""
    import social_channels as sch
    refresh = (os.environ.get("YOUTUBE_REFRESH_TOKEN") or "").strip()
    cid = (os.environ.get("YOUTUBE_CLIENT_ID") or "").strip()
    secret = (os.environ.get("YOUTUBE_CLIENT_SECRET") or "").strip()
    if not (refresh and cid and secret):
        return ""
    _, data, err = sch.http_json(
        "https://oauth2.googleapis.com/token",
        data=sch.form_encode({"client_id": cid, "client_secret": secret,
                              "refresh_token": refresh, "grant_type": "refresh_token"}),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST", retries=2)
    if err or not isinstance(data, dict):
        return ""
    return str(data.get("access_token") or "")


def veroeffentliche_youtube(mp4: str, meta: dict, dry_run: bool = False) -> dict:
    """Lädt ein Short zu YouTube (resumable upload, Data API v3)."""
    import urllib.request
    token = youtube_token()
    if not token:
        return {"ok": False, "grund": "Standby – kein YouTube-Zugang hinterlegt"}
    if not os.path.exists(mp4):
        return {"ok": False, "grund": f"Datei fehlt: {mp4}"}
    yt = (meta or {}).get("youtube") or {}
    koerper = {
        "snippet": {"title": yt.get("titel") or "", "description": yt.get("beschreibung") or "",
                    "tags": yt.get("tags") or [], "categoryId": yt.get("kategorie_id") or "22",
                    "defaultLanguage": "de", "defaultAudioLanguage": "de"},
        "status": {"privacyStatus": yt.get("privatsphaere") or "public",
                   "selfDeclaredMadeForKids": False, "license": "youtube"},
    }
    if dry_run:
        return {"ok": True, "grund": "Trockenlauf", "titel": koerper["snippet"]["title"]}

    daten = json.dumps(koerper).encode("utf-8")
    groesse = os.path.getsize(mp4)
    req = urllib.request.Request(
        "https://www.googleapis.com/upload/youtube/v3/videos"
        "?uploadType=resumable&part=snippet,status",
        data=daten, method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                 "X-Upload-Content-Length": str(groesse),
                 "X-Upload-Content-Type": "video/mp4"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            sitz = resp.headers.get("Location")
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "grund": f"Upload-Sitzung abgelehnt: {str(exc)[:160]}"}
    if not sitz:
        return {"ok": False, "grund": "keine Upload-Adresse erhalten"}

    with open(mp4, "rb") as fh:
        inhalt = fh.read()
    req2 = urllib.request.Request(sitz, data=inhalt, method="PUT",
                                  headers={"Content-Type": "video/mp4",
                                           "Content-Length": str(groesse)})
    try:
        with urllib.request.urlopen(req2, timeout=900) as resp:
            antwort = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "grund": f"Upload fehlgeschlagen: {str(exc)[:160]}"}
    vid = antwort.get("id")
    if not vid:
        return {"ok": False, "grund": "YouTube lieferte keine Video-ID"}
    return {"ok": True, "url": f"https://www.youtube.com/shorts/{vid}", "id": vid}


def veroeffentliche_instagram(mp4_url: str, meta: dict, dry_run: bool = False) -> dict:
    """Reels über die Graph-API. Verlangt eine ÖFFENTLICH erreichbare URL."""
    import social_channels as sch
    import urllib.parse as up
    token = (os.environ.get("INSTAGRAM_ACCESS_TOKEN") or "").strip()
    konto = (os.environ.get("INSTAGRAM_ACCOUNT_ID") or "").strip()
    if not (token and konto):
        return {"ok": False, "grund": "Standby – kein Instagram-Zugang hinterlegt"}
    if not str(mp4_url).startswith("https://"):
        return {"ok": False, "grund": "Instagram braucht eine öffentliche https-URL der Datei"}
    if dry_run:
        return {"ok": True, "grund": "Trockenlauf"}
    _, data, err = sch.http_json(
        f"https://graph.facebook.com/v20.0/{up.quote(konto)}/media",
        data=sch.form_encode({"media_type": "REELS", "video_url": mp4_url,
                              "caption": ((meta or {}).get("instagram") or {}).get("beschreibung", ""),
                              "share_to_feed": "true", "access_token": token}),
        headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST", retries=2)
    if err or not isinstance(data, dict) or not data.get("id"):
        return {"ok": False, "grund": f"Container abgelehnt ({err})"}
    return {"ok": True, "container": data["id"],
            "grund": "Container erstellt – Veröffentlichung nach Verarbeitung (media_publish)"}


# ================================================================= BERICHT
def cockpit(ergebnisse: list[dict] | None = None) -> str:
    cfg, state = load_config(), load_state()
    fertig = state.get("produziert") or []
    z = [
        "# 🎬 Shorts-Schmiede – Stand der Videoproduktion",
        "",
        f"**Stand:** {_berlin()} Uhr",
        "",
        f"**Produziert gesamt:** {len(fertig)} · "
        f"**ffmpeg:** {'vorhanden' if has_ffmpeg() else 'FEHLT (apt-get install -y ffmpeg)'}"
        + ("" if hat_filter("drawtext") else " · ⚠️ **ohne drawtext** – Untertitel nicht "
           "renderbar, dieses ffmpeg wurde ohne libfreetype gebaut"),
        "",
    ]
    if ergebnisse:
        z += ["## Dieser Lauf", "", "| Artikel | Ergebnis | Dauer | Stimme |", "|---|---|---|---|"]
        for e in ergebnisse:
            zustand = "✅ gebaut" if e.get("ok") else f"❌ {e.get('grund') or 'Gate'}"
            z.append(f"| {e.get('slug')} | {zustand} | {e.get('dauer', '–')}s | "
                     f"{e.get('engine', '–')} |")
        z.append("")
        for e in ergebnisse:
            if e.get("gate"):
                z += [f"**Gate-Befund `{e.get('slug')}`:** " + "; ".join(e["gate"]), ""]
    if fertig:
        z += ["## Zuletzt produziert", "", "| Zeit | Artikel | Dauer | Datei |", "|---|---|---|---|"]
        for p in fertig[-10:][::-1]:
            z.append(f"| {p.get('zeit')} | {p.get('slug')} | {p.get('dauer')}s | "
                     f"`{os.path.basename(p.get('datei') or '')}` |")
        z.append("")
    z += [
        "## Aufbau jedes Videos",
        "",
        "1. **Hook** – Zahl oder Frage, nie der Blogname (die erste Sekunde entscheidet).",
        "2. **Drei Punkte** – je ein Gedanke, die stärkste Zahl in der Mitte.",
        "3. **Abbinder** – Verweis auf den vollständigen Ratgeber, ohne Marktschreierei.",
        "",
        "Dauerhaft im Bild: Pflichthinweis „keine Anlage- oder Rechtsberatung\" und die "
        "Marken-Fußzeile. Untertitel sind eingebrannt – rund 80 % sehen Shorts ohne Ton.",
        "",
        "Regie: `data/social/video.yaml` · Anleitung: `docs/ANLEITUNG-SHORTS-SCHMIEDE.md`",
        "",
        "*Erzeugt von `scripts/social_video.py`. Videos liegen unter "
        f"`{(cfg.get('meta') or {}).get('ausgabe_verzeichnis', '.cache/social-video')}/` "
        "und werden bewusst nicht versioniert.*",
    ]
    return "\n".join(z) + "\n"


# =============================================================== SELBSTTEST
def selftest() -> int:
    fehler: list[str] = []
    cfg = load_config()
    if not cfg:
        print("❌ video.yaml fehlt")
        return 1
    os.environ["VIDEO_LLM_MODE"] = "off"     # Selbsttest bleibt offline

    art = {
        "slug": "test-artikel", "title": "Stromkosten senken: 240 € im Jahr sparen",
        "url": "https://franksfinanzcheck.de/posts/test-artikel/",
        "kurzantwort": "Wer den Stromtarif einmal im Jahr prüft, spart im Schnitt 240 Euro. "
                       "Der Wechsel dauert rund 15 Minuten und läuft über den neuen Anbieter.",
        "description": "Stromkosten senken mit einem jährlichen Tarifcheck.",
        "takeaways": ["Der Grundversorgungstarif ist fast immer der teuerste Tarif im Haus.",
                      "Ein Wechsel spart im Schnitt 240 Euro pro Jahr bei gleichem Strom.",
                      "Die Kündigung übernimmt der neue Anbieter, du brauchst nur die Zählernummer."],
        "numbers": ["240 €", "15 Minuten"], "faq_question": "Wie oft sollte man den Tarif prüfen?",
        "tags": ["Stromsparen", "Tarifwechsel"], "keywords": ["strom"],
        "pillar": "strom-sparen", "cover": "images/covers/test.jpg",
        "published": _now().isoformat(), "draft": False,
    }

    db = drehbuch(art, cfg)
    if len(db["szenen"]) < 4:
        fehler.append(f"Drehbuch hat nur {len(db['szenen'])} Szenen")
    if db["szenen"][0]["typ"] != "hook":
        fehler.append("erste Szene ist kein Hook")
    if db["szenen"][-1]["typ"] != "cta":
        fehler.append("letzte Szene ist kein Abbinder")
    for s in db["szenen"]:
        if not s.get("untertitel"):
            fehler.append(f"Szene ohne Untertitel: {s['text'][:30]}")
        for zeile in s["untertitel"]:
            if len(zeile) > int((cfg.get("untertitel") or {}).get("zeichen_pro_zeile", 26)) + 12:
                fehler.append(f"Untertitelzeile zu lang: {zeile}")
    if not db.get("hinweis"):
        fehler.append("Pflichthinweis fehlt im Drehbuch")

    verstoesse = pruefe(db, cfg)
    if verstoesse:
        fehler.append(f"Gate blockiert ein sauberes Drehbuch: {verstoesse}")

    # Gate muss greifen
    schlecht = json.loads(json.dumps(db))
    schlecht["szenen"][1]["text"] = "Damit sparst du garantiert 9999 Euro, ein echter Geheimtipp."
    g = pruefe(schlecht, cfg)
    if not any("garantiert" in x for x in g):
        fehler.append("Gate übersieht das Versprechen „garantiert\"")
    if not any("Geheimtipp" in x or "geheimtipp" in x.lower() for x in g):
        fehler.append("Gate übersieht „Geheimtipp\"")
    if not any("nicht im Artikel" in x for x in g):
        fehler.append("Gate übersieht die erfundene Zahl 9999")

    ohne_zahl = json.loads(json.dumps(db))
    for s in ohne_zahl["szenen"]:
        s["text"] = re.sub(r"\d", "", s["text"])
    if not any("Zahl" in x for x in pruefe(ohne_zahl, cfg)):
        fehler.append("Gate übersieht das fehlende Zahlen-Fundament")

    ohne_cover = json.loads(json.dumps(db))
    ohne_cover["cover"] = ""
    if not any("Cover" in x for x in pruefe(ohne_cover, cfg)):
        fehler.append("Gate übersieht das fehlende Cover")

    # Filtergraph muss baubar und plausibel sein (ohne ffmpeg-Aufruf)
    dauern = [_sprechdauer(s["text"]) for s in db["szenen"]]
    graph, gesamt = filtergraph(db, cfg, dauern)
    if "[vout]" not in graph:
        fehler.append("Filtergraph ohne Ausgang [vout]")
    if graph.count("drawtext") < len(db["szenen"]):
        fehler.append("Filtergraph zeichnet nicht jede Szene")
    if "zoompan" not in graph:
        fehler.append("Ken-Burns-Fahrt fehlt")
    if (cfg.get("pflicht") or {}).get("hinweis", "")[:12] not in graph.replace("\\", ""):
        fehler.append("Pflichthinweis wird nicht eingeblendet")
    if not (float((cfg.get("format") or {}).get("min_sekunden", 28))
            <= gesamt <= float((cfg.get("format") or {}).get("max_sekunden", 52))):
        fehler.append(f"Gesamtdauer {gesamt:.0f}s außerhalb der Regie-Grenzen")

    # Escaping darf den Filtergraph nicht sprengen
    if ":" in _esc("18:30 Uhr").replace("\\:", "") or "'" in _esc("Frank's Tipp"):
        fehler.append("drawtext-Escaping unvollständig")

    # Metadaten
    md = db.get("metadaten") or {}
    if "#Shorts" not in (md.get("youtube") or {}).get("titel", ""):
        fehler.append("YouTube-Titel ohne #Shorts")
    if art["url"] not in (md.get("youtube") or {}).get("beschreibung", ""):
        fehler.append("YouTube-Beschreibung ohne Artikel-Link")
    if "keine Anlage" not in (md.get("youtube") or {}).get("beschreibung", ""):
        fehler.append("YouTube-Beschreibung ohne Pflichthinweis")

    # Schrift vorhanden?
    schrift = os.path.join(BLOG_DIR, (cfg.get("marke") or {}).get("schrift", ""))
    if not os.path.exists(schrift):
        fehler.append(f"Schriftdatei fehlt: {schrift}")

    # Standby-Regel: ohne Zugangsdaten wird NICHTS hochgeladen.
    gesichert = dict(os.environ)
    try:
        for key in ("YOUTUBE_REFRESH_TOKEN", "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET",
                    "INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_ACCOUNT_ID"):
            os.environ.pop(key, None)
        yt = veroeffentliche_youtube(__file__, {})
        if yt.get("ok") or "Standby" not in yt.get("grund", ""):
            fehler.append("YouTube-Upload ohne Zugangsdaten nicht im Standby")
        ig = veroeffentliche_instagram("https://example.com/x.mp4", {})
        if ig.get("ok") or "Standby" not in ig.get("grund", ""):
            fehler.append("Instagram-Upload ohne Zugangsdaten nicht im Standby")
    finally:
        os.environ.clear()
        os.environ.update(gesichert)

    if not cockpit().startswith("# "):
        fehler.append("Cockpit-Bericht fehlerhaft")

    if fehler:
        print("❌ Selbsttest fehlgeschlagen:")
        for f in fehler:
            print(f"   · {f}")
        return 1
    print(f"✅ Selbsttest bestanden (Drehbuch {len(db['szenen'])} Szenen / {gesamt:.0f}s, "
          f"Gate greift, Filtergraph baubar, ffmpeg "
          f"{'vorhanden' if has_ffmpeg() else 'fehlt – Bau erst im Runner'}).")
    return 0


# ==================================================================== CLI
def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Shorts-Schmiede: vertikale Kurzvideos aus Artikeln.")
    p.add_argument("--plan", action="store_true", help="zeigen, welche Artikel dran wären")
    p.add_argument("--drehbuch", action="store_true", help="nur das Drehbuch ausgeben")
    p.add_argument("--bauen", action="store_true", help="Video(s) rendern")
    p.add_argument("--slug", default="", help="bestimmten Artikel wählen")
    p.add_argument("--limit", type=int, default=0, help="höchstens so viele Videos")
    p.add_argument("--ohne-ton", action="store_true", help="stumm rendern (schnell, für Tests)")
    p.add_argument("--status", action="store_true", help="nur das Cockpit schreiben")
    p.add_argument("--pruefe-umgebung", action="store_true",
                   help="kann diese Maschine überhaupt rendern?")
    p.add_argument("--veroeffentlichen", action="store_true",
                   help="gebaute Videos hochladen (YouTube Shorts)")
    p.add_argument("--dry-run", action="store_true",
                   help="beim Veröffentlichen nichts wirklich hochladen")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args(argv)

    if a.selftest:
        return selftest()

    if a.pruefe_umgebung:
        u = umgebung()
        print("Render-Umgebung:")
        for k in ("ffmpeg", "ffprobe", "drawtext", "zoompan", "schrift"):
            print(f"  {'✅' if u[k] else '❌'} {k}" + (f"  ({u['schrift_pfad']})"
                                                      if k == "schrift" else ""))
        if not u["drawtext"]:
            print("  → ffmpeg ohne libfreetype: `apt-get install -y ffmpeg` "
                  "(die pip-Variante imageio-ffmpeg reicht NICHT).")
        return 0 if (u["ffmpeg"] and u["drawtext"] and u["schrift"]) else 1

    cfg = load_config()
    if not cfg:
        print("⚠ data/social/video.yaml fehlt – nichts zu tun.")
        return 0

    if a.status:
        _schreibe_cockpit()
        return 0

    liste = kandidaten(cfg)
    if a.slug:
        liste = [x for x in liste if x.get("slug") == a.slug]
        if not liste:
            try:
                import social_copywriter as cw
                liste = [x for x in cw.article_pool() if x.get("slug") == a.slug]
            except Exception:  # noqa: BLE001
                liste = []
        if not liste:
            print(f"⚠ Artikel „{a.slug}\" nicht gefunden.")
            return 1

    grenze = a.limit or int((cfg.get("meta") or {}).get("max_pro_lauf") or 2)

    if a.plan or (not a.bauen and not a.drehbuch):
        print("=" * 64)
        print("  SHORTS-SCHMIEDE – Produktionsplan")
        print("=" * 64)
        if not liste:
            print("  Nichts offen: alle jungen Artikel haben ihr Video.")
        for art in liste[:10]:
            db = drehbuch(art, cfg)
            g = pruefe(db, cfg)
            marke = "✅" if not g else "❌"
            print(f"  {marke} {art['slug']}  ({db['dauer']:.0f}s, {len(db['szenen'])} Szenen)")
            if g:
                print(f"      Gate: {'; '.join(g)}")
        print("-" * 64)
        print(f"  ffmpeg: {'vorhanden' if has_ffmpeg() else 'FEHLT – Bau nur im Runner'}")
        _schreibe_cockpit()
        return 0

    if a.drehbuch:
        for art in liste[:max(grenze, 1)]:
            db = drehbuch(art, cfg)
            print("=" * 64)
            print(f"  {db['titel']}")
            print(f"  {db['dauer']:.0f}s · {len(db['szenen'])} Szenen · {db['url']}")
            print("=" * 64)
            for i, s in enumerate(db["szenen"], 1):
                print(f"  [{i}] {s['typ'].upper():<6} {s['text']}")
            g = pruefe(db, cfg)
            print("-" * 64)
            print("  Gate: " + ("✅ frei" if not g else "❌ " + "; ".join(g)))
            print(f"  YouTube-Titel: {db['metadaten']['youtube']['titel']}")
        return 0

    # --------------------------------------------------------------- bauen
    state = load_state()
    ergebnisse = []
    for art in liste[:grenze]:
        db = drehbuch(art, cfg)
        g = pruefe(db, cfg)
        if g:
            print(f"❌ {art['slug']}: Gate blockiert – {'; '.join(g)}")
            ergebnisse.append({"slug": art["slug"], "ok": False, "grund": "Gate", "gate": g})
            continue
        print(f"🎬 {art['slug']} – {len(db['szenen'])} Szenen, ~{db['dauer']:.0f}s")
        erg = baue(db, cfg, ohne_ton=a.ohne_ton)
        erg["slug"] = art["slug"]
        ergebnisse.append(erg)
        if erg.get("ok"):
            print(f"   ✅ {erg['datei']} ({erg['dauer']}s, {erg['mb']} MB, Stimme {erg['engine']})")
            state.setdefault("produziert", []).append(
                {"slug": art["slug"], "zeit": _now().isoformat(), "dauer": erg["dauer"],
                 "datei": erg["datei"], "engine": erg["engine"]})
        else:
            print(f"   ❌ {erg.get('grund')}")
    if a.veroeffentlichen:
        for erg in [e for e in ergebnisse if e.get("ok")]:
            with open(erg["json"], encoding="utf-8") as fh:
                md = (json.load(fh) or {}).get("metadaten") or {}
            up = veroeffentliche_youtube(erg["datei"], md, dry_run=a.dry_run)
            erg["upload"] = up
            print(f"   {'📤 ' + up.get('url', '') if up.get('ok') else '⚠ ' + up.get('grund', '')}")
            for p_ in state.get("produziert") or []:
                if p_.get("slug") == erg.get("slug") and up.get("ok"):
                    p_["youtube"] = up.get("url")

    save_state(state)
    _schreibe_cockpit(ergebnisse)
    return 0


def _schreibe_cockpit(ergebnisse: list[dict] | None = None) -> None:
    try:
        with open(REPORT_PATH, "w", encoding="utf-8") as fh:
            fh.write(cockpit(ergebnisse))
        print(f"  Cockpit: {os.path.relpath(REPORT_PATH, BLOG_DIR)}")
    except Exception as exc:  # noqa: BLE001
        print(f"⚠ Cockpit nicht schreibbar: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
