#!/usr/bin/env python3
# ============================================================
#  SCHALTWERK – TRIGGER (die „Wenn …“-Seite des Zapier-Nachbaus)
#  ------------------------------------------------------------
#  Jeder Trigger ist eine Funktion:
#
#      def trigger_xy(params: dict, ctx: dict) -> list[dict]
#
#  Rückgabe ist eine Liste von Ereignissen:
#      {"key": "<eindeutig>", "daten": {...beliebiger Kontext...}}
#
#  Der `key` ist die Dedupe-Marke: Das Schaltwerk feuert jede Marke
#  nur ein einziges Mal (Zapier nennt das „Deduplication“).
#
#  REGELN FÜR TRIGGER:
#    · Nur lesen. Trigger verändern nichts außer dem Merker-State.
#    · Nie eine Exception nach außen – lieber eine leere Liste.
#    · Offline-tauglich: ohne Netz liefert ein Netz-Trigger [].
#    · Keine kostenpflichtige API (Kosten-Regel des Repositories).
# ============================================================
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BLOG_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

USER_AGENT = "FranksFinanzcheck-Schaltwerk/1.0 (+https://franksfinanzcheck.de)"


def _jetzt(ctx: dict) -> datetime:
    import schaltwerk

    return ctx.get("jetzt") or schaltwerk.berlin_now()


def _naiv(dt: datetime | None) -> datetime | None:
    return dt.replace(tzinfo=None) if dt is not None else None


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:16]


# ============================================================ 1 · Blog-Events
def trigger_neuer_artikel(params: dict, ctx: dict) -> list[dict]:
    """Ein Artikel ist frisch veröffentlicht (Launch-Welle über alle Kanäle).

    params: max_alter_stunden (Standard 72), pillar (optional, Filterhilfe)
    """
    import schaltwerk

    try:
        import social_copywriter as copy
    except Exception:  # noqa: BLE001 – ohne Artikelpool kein Trigger
        return []

    max_alter = float(params.get("max_alter_stunden") or 72)
    jetzt = _jetzt(ctx)
    grenze = _naiv(jetzt) - timedelta(hours=max_alter)

    events = []
    for art in copy.article_pool():
        veroeffentlicht = _naiv(schaltwerk.parse_dt(art.get("published") or ""))
        if not veroeffentlicht or veroeffentlicht < grenze or veroeffentlicht > _naiv(jetzt) + timedelta(hours=2):
            continue
        events.append({
            "key": f"artikel:{art.get('slug')}",
            "daten": {
                "artikel": {
                    "slug": art.get("slug"),
                    "title": art.get("title"),
                    "description": art.get("description"),
                    "kurzantwort": art.get("kurzantwort"),
                    "url": art.get("url"),
                    "pillar": art.get("pillar"),
                    "tags": art.get("tags") or [],
                    "published": art.get("published"),
                    "cover": art.get("cover"),
                },
                "titel": art.get("title"),
                "url": art.get("url"),
            },
        })
    events.sort(key=lambda e: str((e["daten"]["artikel"]).get("published") or ""), reverse=True)
    return events


def trigger_artikel_aktualisiert(params: dict, ctx: dict) -> list[dict]:
    """Ein Bestandsartikel wurde inhaltlich überarbeitet (Update-Welle).

    Liest .article_updates.json (schreibt die Faktenfrische-Kette).
    params: max_alter_tage (Standard 3)
    """
    import schaltwerk

    pfad = os.path.join(BLOG_DIR, ".article_updates.json")
    try:
        with open(pfad, encoding="utf-8") as fh:
            daten = json.load(fh) or {}
    except (OSError, json.JSONDecodeError):
        return []

    max_alter = float(params.get("max_alter_tage") or 3)
    grenze = _naiv(_jetzt(ctx)) - timedelta(days=max_alter)
    eintraege = daten.get("updates") if isinstance(daten, dict) else daten
    if isinstance(eintraege, dict):
        eintraege = [{"slug": k, **(v if isinstance(v, dict) else {"datum": v})}
                     for k, v in eintraege.items()]
    if not isinstance(eintraege, list):
        return []

    events = []
    for e in eintraege:
        if not isinstance(e, dict):
            continue
        slug = e.get("slug") or e.get("artikel") or ""
        stamp = e.get("datum") or e.get("date") or e.get("updated") or ""
        dt = _naiv(schaltwerk.parse_dt(str(stamp)))
        if not slug or (dt and dt < grenze):
            continue
        events.append({
            "key": f"update:{slug}:{str(stamp)[:10]}",
            "daten": {"artikel": {"slug": slug, "title": e.get("title") or slug},
                      "update": e, "titel": e.get("title") or slug},
        })
    return events


# ====================================================== 2 · Agent-Reach-Signale
def trigger_recherche_signal(params: dict, ctx: dict) -> list[dict]:
    """Treffer aus dem jüngsten Agent-Reach-Brief (data/research/*.json).

    WICHTIG: Agent Reach ist und bleibt LESEND. Diese Signale sind Anlässe
    für die Redaktion, niemals fertiger Social-Text. Das Schaltwerk legt sie
    deshalb nur zur Kuratierung ab (Aktion `themen_vorschlag`).

    params: stichworte [Liste], max_treffer (Standard 8),
            max_alter_tage (Standard 9)
    """
    import schaltwerk

    ordner = os.path.join(BLOG_DIR, "data", "research")
    try:
        dateien = sorted(f for f in os.listdir(ordner) if f.endswith(".json"))
    except OSError:
        return []
    if not dateien:
        return []

    neueste = os.path.join(ordner, dateien[-1])
    try:
        with open(neueste, encoding="utf-8") as fh:
            brief = json.load(fh) or {}
    except (OSError, json.JSONDecodeError):
        return []

    max_alter = float(params.get("max_alter_tage") or 9)
    brief_dt = _naiv(schaltwerk.parse_dt(str(brief.get("datum") or "")))
    if brief_dt and brief_dt < _naiv(_jetzt(ctx)) - timedelta(days=max_alter):
        return []

    stichworte = [str(s).lower() for s in (params.get("stichworte") or [])]
    max_treffer = int(params.get("max_treffer") or 8)

    def sammle(knoten, quelle: str = "") -> list[dict]:
        out = []
        if isinstance(knoten, dict):
            if "titel" in knoten and "url" in knoten:
                out.append({"titel": knoten.get("titel"), "url": knoten.get("url"),
                            "datum": knoten.get("datum"),
                            "quelle": knoten.get("quelle") or quelle})
                return out
            for schluessel, wert in knoten.items():
                out.extend(sammle(wert, quelle or str(schluessel)))
        elif isinstance(knoten, list):
            for wert in knoten:
                out.extend(sammle(wert, quelle))
        return out

    treffer = sammle(brief.get("ergebnisse") or {})
    events = []
    for t in treffer:
        titel = str(t.get("titel") or "").strip()
        if not titel:
            continue
        if stichworte and not any(s in titel.lower() for s in stichworte):
            continue
        events.append({
            "key": f"signal:{_hash(str(t.get('url') or titel))}",
            "daten": {
                "signal": t,
                "titel": titel,
                "url": t.get("url") or "",
                "quelle": t.get("quelle") or "",
                "brief": os.path.basename(neueste),
                "brief_datum": brief.get("datum") or "",
            },
        })
        if len(events) >= max_treffer:
            break
    return events


# ============================================================== 3 · Zeitplan
def trigger_zeitplan(params: dict, ctx: dict) -> list[dict]:
    """Klassischer Zeit-Trigger („Schedule by Zapier“) in Berliner Ortszeit.

    params: zeiten ["07:30","18:00"], tage [0..6] (Mo=0),
            toleranz_minuten (Standard 45 – deckt Actions-Verzug ab),
            nachholen (bei true: erster Lauf nach dem Slot am selben Tag)

    Der Slot feuert höchstens einmal pro Tag, auch wenn der Lauf mehrfach in
    das Toleranzfenster fällt. Kritische Tagesaufgaben setzen ``nachholen``:
    GitHub darf einen Cron dann um Stunden verzögern, ohne dass die Aufgabe
    für den ganzen Tag verloren ist (State: slots).
    """
    import schaltwerk

    jetzt = _jetzt(ctx)
    tage = params.get("tage")
    if tage is not None and jetzt.weekday() not in [int(t) for t in tage]:
        return []
    toleranz = int(params.get("toleranz_minuten") or 45)
    nachholen = bool(params.get("nachholen", False))
    state = ctx.get("state") or {}
    heute = jetzt.date().isoformat()

    events = []
    for zeit in params.get("zeiten") or []:
        try:
            stunde, minute = [int(x) for x in str(zeit).split(":")[:2]]
        except ValueError:
            continue
        soll = jetzt.replace(hour=stunde, minute=minute, second=0, microsecond=0)
        verzug = (jetzt - soll).total_seconds() / 60.0
        if verzug < 0 or (verzug > toleranz and not nachholen):
            continue
        slot = f"slot:{heute}:{zeit}"
        if slot in (state.get("slots") or {}):
            continue
        state.setdefault("slots", {})[slot] = schaltwerk.iso(jetzt)
        events.append({"key": slot,
                       "daten": {"slot": zeit, "datum": heute,
                                 "wochentag": jetzt.weekday(),
                                 "verzug_minuten": round(verzug)}})
    return events


def trigger_intervall(params: dict, ctx: dict) -> list[dict]:
    """Feuert, wenn seit dem letzten Mal mindestens X Minuten vergangen sind.

    params: minuten (Standard 180), name (Merker-Schlüssel)
    """
    import schaltwerk

    minuten = int(params.get("minuten") or 180)
    name = str(params.get("name") or f"intervall-{minuten}")
    state = ctx.get("state") or {}
    jetzt = _jetzt(ctx)
    letzter = _naiv(schaltwerk.parse_dt((state.get("marker") or {}).get(name) or ""))
    if letzter and _naiv(jetzt) - letzter < timedelta(minutes=minuten):
        return []
    state.setdefault("marker", {})[name] = schaltwerk.iso(jetzt)
    return [{"key": f"{name}:{jetzt.strftime('%Y-%m-%dT%H')}",
             "daten": {"intervall_minuten": minuten, "name": name}}]


# ============================================================ 4 · Kanal-Wache
def trigger_kanal_standby(params: dict, ctx: dict) -> list[dict]:
    """Ein Kanal ist in channels.yaml aktiv, aber ohne Zugangsdaten.

    Damit „vollautomatisch“ nicht still scheitert: Das Schaltwerk erinnert
    (höchstens alle `erinnerung_tage` Tage) daran, welches Secret fehlt.
    params: erinnerung_tage (Standard 14), ignoriere [Kanal-ids]
    """
    import schaltwerk_actions as act

    ignoriere = {str(k).lower() for k in (params.get("ignoriere") or [])}
    tage = int(params.get("erinnerung_tage") or 14)
    periode = _jetzt(ctx).date().isoformat()[:7] if tage >= 28 else \
        f"{_jetzt(ctx).isocalendar().year}-KW{_jetzt(ctx).isocalendar().week // max(1, tage // 7)}"

    events = []
    for kanal in act.kanal_zustand():
        if not kanal["enabled"] or kanal["bereit"] or kanal["id"] in ignoriere:
            continue
        events.append({
            "key": f"standby:{kanal['id']}:{periode}",
            "daten": {"kanal": kanal["id"], "kanal_label": kanal["label"],
                      "grund": kanal["grund"], "secrets": kanal["secrets"]},
        })
    return events


def trigger_kanal_stille(params: dict, ctx: dict) -> list[dict]:
    """Ein sendebereiter Kanal hat seit X Stunden nichts veröffentlicht.

    Das ist der Wachhund gegen „läuft, postet aber nicht“.
    params: stunden (Standard 36)
    """
    import schaltwerk
    import schaltwerk_actions as act

    stunden = float(params.get("stunden") or 36)
    jetzt = _jetzt(ctx)
    try:
        import social_planner as planner

        state = planner.load_state()
    except Exception:  # noqa: BLE001
        return []

    events = []
    for kanal in act.kanal_zustand():
        if not kanal["bereit"]:
            continue
        verlauf = [e for e in (state.get("history") or [])
                   if e.get("channel") == kanal["id"] and e.get("ok")]
        letzter = _naiv(schaltwerk.parse_dt((verlauf[-1].get("posted_at") if verlauf else "") or ""))
        if letzter and _naiv(jetzt) - letzter < timedelta(hours=stunden):
            continue
        events.append({
            "key": f"stille:{kanal['id']}:{jetzt.date().isoformat()}",
            "daten": {"kanal": kanal["id"], "kanal_label": kanal["label"],
                      "stunden": stunden,
                      "letzter_post": verlauf[-1].get("posted_at") if verlauf else "nie"},
        })
    return events


# =========================================================== 5 · Messwerte
def trigger_kennzahl(params: dict, ctx: dict) -> list[dict]:
    """Ein Wert in einer JSON-Datei über-/unterschreitet eine Schwelle.

    params: datei (relativ zum Repo), pfad ("a.b.c"),
            operator (">"|"<"), schwelle, name
    """
    rel = str(params.get("datei") or "")
    pfad = str(params.get("pfad") or "")
    if not rel or not pfad:
        return []
    voll = os.path.join(BLOG_DIR, rel)
    try:
        with open(voll, encoding="utf-8") as fh:
            daten = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return []

    import schaltwerk

    wert = schaltwerk.get_path(daten if isinstance(daten, dict) else {}, pfad)
    try:
        zahl = float(str(wert).replace(",", "."))
        schwelle = float(str(params.get("schwelle")).replace(",", "."))
    except (TypeError, ValueError):
        return []
    op = str(params.get("operator") or ">")
    getroffen = zahl > schwelle if op in (">", "groesser") else zahl < schwelle
    if not getroffen:
        return []
    name = str(params.get("name") or f"{rel}:{pfad}")
    return [{"key": f"kennzahl:{_hash(name)}:{_jetzt(ctx).date().isoformat()}",
             "daten": {"kennzahl": {"name": name, "wert": zahl, "schwelle": schwelle,
                                    "operator": op, "datei": rel, "pfad": pfad},
                       "titel": name}}]


def trigger_datei_geaendert(params: dict, ctx: dict) -> list[dict]:
    """Eine beobachtete Datei hat sich geändert (Inhalts-Hash).

    params: datei (relativ zum Repo), name
    """
    rel = str(params.get("datei") or "")
    if not rel:
        return []
    voll = os.path.join(BLOG_DIR, rel)
    try:
        with open(voll, "rb") as fh:
            digest = hashlib.sha256(fh.read()).hexdigest()[:16]
    except OSError:
        return []
    state = ctx.get("state") or {}
    merker = f"datei:{rel}"
    if (state.get("marker") or {}).get(merker) == digest:
        return []
    alt = (state.get("marker") or {}).get(merker)
    state.setdefault("marker", {})[merker] = digest
    if alt is None:
        # Erstkontakt: nur merken, nicht feuern (sonst feuert alles beim Rollout).
        return []
    return [{"key": f"datei:{rel}:{digest}",
             "daten": {"datei": rel, "hash": digest, "titel": os.path.basename(rel)}}]


# ============================================================== 6 · Netz/RSS
def trigger_rss(params: dict, ctx: dict) -> list[dict]:
    """Neue Einträge in einem RSS-/Atom-Feed (kostenlos, ohne Fremddienst).

    Ohne Netz oder bei Fehler: leere Liste – der Lauf bleibt grün.
    params: url, max_treffer (Standard 5), stichworte [Liste]
    """
    url = str(params.get("url") or "")
    if not url:
        return []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=20) as resp:
            roh = resp.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError, ValueError):
        return []

    eintraege = re.findall(r"<(?:item|entry)\b.*?</(?:item|entry)>", roh, re.S | re.I)
    stichworte = [str(s).lower() for s in (params.get("stichworte") or [])]
    max_treffer = int(params.get("max_treffer") or 5)

    def feld(block: str, tag: str) -> str:
        m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", block, re.S | re.I)
        if not m:
            m = re.search(rf"<{tag}[^>]*href=[\"'](.*?)[\"']", block, re.S | re.I)
            return (m.group(1).strip() if m else "")
        text = m.group(1)
        text = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", text, flags=re.S)
        return re.sub(r"<[^>]+>", "", text).strip()

    events = []
    for block in eintraege:
        titel = feld(block, "title")
        link = feld(block, "link")
        if not titel:
            continue
        if stichworte and not any(s in titel.lower() for s in stichworte):
            continue
        events.append({"key": f"rss:{_hash(link or titel)}",
                       "daten": {"titel": titel, "url": link,
                                 "quelle": url, "feed": url}})
        if len(events) >= max_treffer:
            break
    return events


# ============================================================= 7 · Webhook
def trigger_webhook(params: dict, ctx: dict) -> list[dict]:
    """Externes Ereignis (GitHub `repository_dispatch` → `--event <json>`).

    So ersetzt das Schaltwerk auch Zapiers „Webhooks by Zapier“ – kostenlos:
        gh api repos/$REPO/dispatches -f event_type=schaltwerk \\
           -F 'client_payload[typ]=mein-ereignis'
    params: typ (optional: nur dieses client_payload.typ akzeptieren)
    """
    event = ctx.get("event")
    if not isinstance(event, dict) or not event:
        return []
    erwartet = str(params.get("typ") or "").strip()
    if erwartet and str(event.get("typ") or event.get("type") or "") != erwartet:
        return []
    import schaltwerk

    stempel = schaltwerk.iso(_jetzt(ctx))
    return [{"key": f"webhook:{_hash(json.dumps(event, sort_keys=True) + stempel)}",
             "daten": {"webhook": event, **{k: v for k, v in event.items()
                                            if isinstance(v, (str, int, float, bool))}}}]


def trigger_manuell(params: dict, ctx: dict) -> list[dict]:
    """Feuert bei jedem Lauf genau einmal – für Wartungs-/Sammelregeln."""
    import schaltwerk

    jetzt = _jetzt(ctx)
    return [{"key": f"manuell:{schaltwerk.iso(jetzt)}",
             "daten": {"zeitpunkt": schaltwerk.iso(jetzt)}}]


# ============================================================= 8 · Whisper & n8n (0 € Stack)
def trigger_whisper_aufnahme(params: dict, ctx: dict) -> list[dict]:
    """Prüft den Whisper-Posteingang (data/whisper_inbox/) auf neue Audiodateien."""
    inbox = os.path.join(BLOG_DIR, str(params.get("inbox_dir") or "data/whisper_inbox"))
    if not os.path.isdir(inbox):
        return []
    erlaubte_endungen = {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".flac", ".aac"}
    events = []
    for datei in sorted(os.listdir(inbox)):
        ext = os.path.splitext(datei)[1].lower()
        if ext in erlaubte_endungen:
            voll = os.path.join(inbox, datei)
            st = os.stat(voll)
            events.append({
                "key": f"whisper:{datei}:{int(st.st_mtime)}",
                "daten": {
                    "datei": datei,
                    "pfad": voll,
                    "groesse_bytes": st.st_size,
                    "kategorie": params.get("kategorie", "spartipps"),
                },
            })
    return events


def trigger_n8n_event(params: dict, ctx: dict) -> list[dict]:
    """Empfängt ein Ereignis von n8n (via webhook oder repository_dispatch)."""
    event = ctx.get("event")
    if not isinstance(event, dict) or not event:
        return []
    typ = str(event.get("typ") or event.get("event_type") or "").strip()
    erwartet = str(params.get("typ") or "").strip()
    if erwartet and typ != erwartet:
        return []
    import schaltwerk

    stempel = schaltwerk.iso(_jetzt(ctx))
    return [{
        "key": f"n8n:{_hash(json.dumps(event, sort_keys=True) + stempel)}",
        "daten": {
            "n8n": event,
            "typ": typ,
            **{k: v for k, v in event.items() if isinstance(v, (str, int, float, bool))},
        },
    }]


# ------------------------------------------------------------- Registrierung
PROVIDER = {
    "neuer_artikel": trigger_neuer_artikel,
    "artikel_aktualisiert": trigger_artikel_aktualisiert,
    "recherche_signal": trigger_recherche_signal,
    "zeitplan": trigger_zeitplan,
    "intervall": trigger_intervall,
    "kanal_standby": trigger_kanal_standby,
    "kanal_stille": trigger_kanal_stille,
    "kennzahl": trigger_kennzahl,
    "datei_geaendert": trigger_datei_geaendert,
    "rss": trigger_rss,
    "webhook": trigger_webhook,
    "manuell": trigger_manuell,
    "whisper_aufnahme": trigger_whisper_aufnahme,
    "n8n_event": trigger_n8n_event,
}


if __name__ == "__main__":  # pragma: no cover – Handprobe
    import schaltwerk

    ctx = {"jetzt": schaltwerk.berlin_now(), "state": schaltwerk.load_state(),
           "dry_run": True}
    for name, fn in PROVIDER.items():
        try:
            n = len(fn({}, ctx) or [])
        except Exception as exc:  # noqa: BLE001
            n = f"Fehler: {exc}"
        print(f"{name:24s} → {n}")
