#!/usr/bin/env python3
"""
EDITORIAL-SCORECARD – Chefredakteur-Scorecard für FranksFinanzcheck

Ein Chefredakteur einer großen Zeitung will EINE zentrale Kennzahl-Anzeige:
"Wie gesund ist mein Blatt?" Dieses Skript bündelt alle relevanten Signale
(Content, Kadenz, Qualität, Lektorat, Affiliate, Decay, CWV, Secrets) zu einer
single Scorecard mit Ampel und Handlungsempfehlungen – für den wöchentlichen
Redaktions-Report.

Der Scorecard ist bewusst SCHNELL (keine teuren KI-Calls): er liest die
vorhandenen Daten/Reports der spezialisierten Wachen und ergänzt nur leichte
Inline-Zählungen aus `content/`.

AUSGABE:
  - `EDITORIAL-SCORECARD.md` – Scorecard
  - `--issue`                 – GitHub-Issue-Body (bei Score < 75)
  - `--selftest`

Exit-Codes: 0 = Score ≥ 75, 1 = Handlungsbedarf (Score < 75), 2 = Selftest/Fehler.

Nutzung:
  python3 scripts/editorial_scorecard.py            # erzeugen + ausgeben
  python3 scripts/editorial_scorecard.py --issue    # zusätzlich Issue-Body
  python3 scripts/editorial_scorecard.py --selftest
"""
import glob
import json
import os
import re
import sys
import datetime
import statistics

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
import post_utils  # noqa: E402

REPORT = os.path.join(BLOG_DIR, "EDITORIAL-SCORECARD.md")
TODAY = datetime.date.today()

DATA = lambda name: os.path.join(BLOG_DIR, "data", name)
_DECAY_Q = DATA("decay_queue.json")
_CWV_M = DATA("cwv_manifest.json")
_SECRETS_S = DATA("secrets_state.json")
_CLICK_S = DATA("click_stats.json")
_CLICK_META = DATA("umami_clicks.meta.json")
_AWIN_P = DATA("awin_provisions.json")
_HISTORY = DATA("scorecard_history.jsonl")
_SECRETS_REPORT = os.path.join(BLOG_DIR, "SECRETS-REPORT.md")
_CWV_REPORT = os.path.join(BLOG_DIR, "CWV-REPORT.md")

# Lesbarkeits-Zielgrößen – EINE Wahrheit mit readability_check / Regelwerk R6.
# Die Scorecard zeigte früher „Ziel ≥ 70“: ein Mess-Artefakt aus der G2-Ära
# (Lesbarkeit wurde aus einer nie existierenden Datei gelesen und per
# `(v or 100) >= 70` grün gefärbt). Das Qualitäts-Regelwerk definiert als Ziel
# Flesch-Amstad Ø ≥ 62 und als Bestands-Floor 55. Seit 07.09.2026 importiert
# die Scorecard dieselben Konstanten wie das Gate – kein abweichendes Ziel mehr.
try:
    from readability_check import AVG_TARGET as R_TARGET
    from readability_check import FLOOR_MIN as R_FLOOR
except Exception:  # pragma: no cover – Fallback hält die Scorecard lauffähig
    R_TARGET, R_FLOOR = 62.0, 55.0

# Wie alt eine Messung sein darf, bevor sie als Blindflug gilt (Wochenrhythmus + Puffer).
STALE_AFTER_DAYS = 9


def _read_text(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def _age_days(raw, today=None):
    """Tage seit einem ISO-Datum; None, wenn unlesbar (nie raten)."""
    if not raw:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(raw))
    if not m:
        return None
    try:
        d = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None
    delta = (today or TODAY) - d
    return delta.days if delta.days > 0 else 0


def _read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def _cwv_state(manifest, today=None):
    """CWV-Ampel mit Herkunftsnachweis.

    Kern der #206-Korrektur: die Scorecard hat das Manifest des Vorlaufs
    gelesen (sie lief IM Workflow VOR dem CWV-Schritt) und daraus eine
    falsche AMBER-Zeile samt 7 Punkten Abzug gebaut. Deshalb wird jetzt
    die Altersangabe mitgeführt und ein veraltetes/unvollständiges Bild
    als Blindflug ausgewiesen – nicht als Performance-Diagnose.
    """
    today = today or TODAY
    verdict = (manifest or {}).get("verdict") or "UNKNOWN"
    age = _age_days((manifest or {}).get("generated"), today)
    measured = bool((manifest or {}).get("build_measured", True))
    hard = [f for f in (manifest or {}).get("findings", []) if f.get("level") in ("red", "amber")]
    state = "OK"
    if verdict == "UNKNOWN":
        state = "MISSING"
    elif age is None or age > STALE_AFTER_DAYS:
        state = "STALE"
    elif not measured:
        state = "PARTIAL"
    display = {"OK": verdict, "STALE": f"STALE ({age}d)",
               "MISSING": "nicht gemessen", "PARTIAL": f"{verdict} (nur static/)"}[state]
    return {"verdict": verdict, "state": state, "display": display, "age": age,
            "findings": len(hard), "red": sum(1 for f in hard if f.get("level") == "red"),
            "measured": measured}


def _secret_state(state, report_text=""):
    """Secrets-Lage aus Report (Policy) + State (Nachweise) – nicht selbst erfunden.

    Formatsperre: der Report der v1-Wache hat keine `Nachweis`-Spalte und damit
    keine Nachweis-Qualität. Ein View darf aus einem unbekannten Format keine
    Ampel bauen (das ist genau die #206-Klasse: Verbraucher und Erzeuger
    schreiben aneinander vorbei) – also ⚪ statt 🟡, bis der Wächter neu läuft.
    """
    out = {"red": 0, "amber": 0, "info": 0, "entries": len((state or {}).get("entries") or {}),
           "proven": 0, "verdict": "UNKNOWN", "legacy": False}
    v1_tabelle = bool(re.search(r"^\|\s*Secret\s*\|\s*Status\s*\|\s*$", report_text or "", re.M))
    if v1_tabelle and "Nachweis" not in report_text:
        out["legacy"] = True
        out["verdict"] = "LEGACY"
        return out
    for m in re.finditer(r"^\|\s*(RED|AMBER)\s*\|\s*([A-Za-z0-9_\-]+)\s*\|", report_text or "", re.M):
        out["red" if m.group(1) == "RED" else "amber"] += 1
    m = re.search(r"Gesamt-Ampel:\s*\*\*(GREEN|AMBER|RED)\*\*", report_text or "")
    if m:
        out["verdict"] = m.group(1)
    for ent in ((state or {}).get("entries") or {}).values():
        if isinstance(ent, dict) and ent.get("quality") == "proven":
            out["proven"] += 1
    return out


def _drafts_lamp(n):
    """Entwürfe sind Vorrat, kein Mangel – erst die Stapelgröße macht Arbeit."""
    if n == 0:
        return "🟢"
    if n <= 3:
        return "⚪"
    return "🟡" if n <= 8 else "🔴"


def _data_lamp(total, articles, configured):
    """Lampen für Monetarisierungs-Signale.

    ⚪ = Datenlage offen (nie importiert) – das ist KEIN Befund und war in #206
        als 🟡 markiert, wodurch die Scorecard dauerhaft gelb erschien.
    🟡 = Import läuft, aber ohne zuordenbare Erlöse – Handlung: Attribute/CSV.
    🟢 = messbarer Umsatz-Hebel.
    """
    if not configured:
        return "⚪"
    if total >= 100:
        return "🟢"
    return "🟡"


def _trend():
    """Letzte Scorecard-Stände (für die eine Zahl, die ein Chefredakteur sieht)."""
    try:
        rows = [json.loads(l) for l in open(_HISTORY, encoding="utf-8") if l.strip()]
    except (OSError, json.JSONDecodeError):
        return None, None
    rows = [r for r in rows if isinstance(r, dict) and r.get("score") is not None]
    if not rows:
        return None, None
    prev = rows[-2].get("score") if len(rows) >= 2 else None
    return prev, len(rows)


def _count_live_drafts():
    live = drafts = 0
    slugs = post_utils.list_post_paths()
    for p in slugs:
        try:
            t = open(p, encoding="utf-8").read()
        except OSError:
            continue
        if post_utils.slug_of(p) == "_index":
            continue
        if "draft: false" in t:
            live += 1
        elif "draft: true" in t:
            drafts += 1
    return live, drafts


def _pillar_counts():
    counts = {}
    for p in post_utils.list_post_paths():
        try:
            t = open(p, encoding="utf-8").read()
        except OSError:
            continue
        m = re.search(r"^pillar:\s*[\"']?([^\"'\n]+)", t, re.M)
        if m:
            key = m.group(1).strip().strip("'\"")
            counts[key] = counts.get(key, 0) + 1
    return counts


def _avg_readability():
    """Misst die Lesbarkeit direkt am Bestand (Ø Flesch, Amstad-deutsch).

    Vorher wurde `VERSTAENDNIS-REPORT.md` nach "Flesch" durchsucht – diese
    Datei existiert im Repo nicht (der Report heißt TEXTVERSTAENDNIS-*.md und
    enthält keine Flesch-Werte). Ergebnis war dauerhaft `n/a`, obwohl die
    Kennzahl in der Scorecard bewertet wird. Jetzt wird sie aus der einen
    Wahrheitsquelle berechnet, die auch Publish-Gate und Quality-Score nutzen:
    `readability_check.analyze`.
    """
    try:
        from readability_check import load_article, analyze
    except ImportError:
        return {"avg": None, "floor": []}
    scores = []
    floor = []
    for p in post_utils.list_post_paths():
        if os.path.basename(p) == "_index.md":
            continue
        try:
            a = load_article(p)
            if not a:
                continue
            v = analyze(a).get("flesch")
        except Exception:
            continue
        if v is not None and 0 <= v <= 100:
            scores.append(v)
            if v < R_FLOOR:
                floor.append(os.path.relpath(p, os.path.join(BLOG_DIR, "content", "posts")))
    if not scores:
        return {"avg": None, "floor": []}
    return {"avg": round(statistics.mean(scores), 1), "floor": floor}


def _lektor_findings():
    fp = os.path.join(BLOG_DIR, "LEKTOR-REPORT.md")
    if not os.path.exists(fp):
        return None
    try:
        t = open(fp, encoding="utf-8").read()
    except OSError:
        return None
    # Nur AUTO-behebbare Regeln zählen als "Befund".
    #
    # Vorher wurde jede `| Lx ... | n |`-Zeile summiert – also auch die reinen
    # "(Report)"-Stilradare (L5 Echo, L7 Nominalstil, L8 Weichmacher, L9, L12).
    # Diese sind bewusst NICHT automatisch behebbar (sie bewerten Stil, nicht
    # Fehler). Ergebnis: eine dauerhaft gelbe Kennzahl mit der Empfehlung
    # `lektor_guard.py --fix`, die daran nichts ändern KANN – ein Ratschlag ins
    # Leere. Jetzt zählen wir das, was der Fix wirklich beheben kann, und
    # führen die Stil-Hinweise getrennt als Info.
    auto = advisory = 0
    for label, val in re.findall(r"\| (L\d+ [^|]+?) \|\s*([\d/]+)\s*\|", t):
        n = int(val.split("/")[0])
        if "(Auto" in label:
            auto += n
        else:
            advisory += n
    return {"auto": auto, "advisory": advisory}


_CASING_J = os.path.join(BLOG_DIR, ".casing_report.json")
_CASING_H = os.path.join(BLOG_DIR, "data", "casing_history.jsonl")


def _casing_state():
    """Groß-/Kleinschreibung: harte Befunde, Dichte je 1.000 Woerter, Trend.

    Die Zahl uebernimmt die Scorecard aus dem Bericht der Wache
    (.casing_report.json) – sie rechnet nicht selbst nach. Der Trend kommt aus
    data/casing_history.jsonl (letzter TAG vor heute); ohne Bericht ist die
    Lampe ⚪ (Datenluecke), nicht 🟡 – dieselbe Regel wie bei Klicks und CWV.
    """
    j = _read_json(_CASING_J, {})
    if not j:
        return None
    hist = []
    try:
        with open(_CASING_H, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        hist.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except OSError:
        hist = []
    woerter = sum(int(x.get("woerter") or 0) for x in j.get("dateien_liste", []))
    hart = int(j.get("hart") or 0)
    park = j.get("geparkt") or []
    vorher = None
    for h in reversed(hist):
        if h.get("tag") != TODAY.isoformat():
            vorher = h.get("hart")
            break
    return {
        "hart": hart,
        "hinweise": int(j.get("befunde") or 0) - hart,
        "gefixt": int(j.get("gefixt") or 0),
        "geparkt": len(park) if isinstance(park, list) else int(park or 0),
        "dichte": round(1000.0 * hart / woerter, 2) if woerter else None,
        "trend": None if vorher is None else hart - int(vorher),
        "stand": (j.get("stand") or "nie")[:10],
        "tage": len({h.get("tag") for h in hist if h.get("tag")}),
    }


def _casing_lamp(d):
    c = d.get("casing")
    if c is None:
        return "⚪"
    if c == 0 and not d.get("casing_geparkt"):
        return "🟢"
    return "🟡" if c <= 3 else "🔴"


def collect():
    """Sammelt alle Daten für die Scorecard."""
    live, drafts = _count_live_drafts()
    pillars = _pillar_counts()
    decay = _read_json(_DECAY_Q, {"count": 0, "queue": []})
    cwv_manifest = _read_json(_CWV_M, {})
    cwv = _cwv_state(cwv_manifest)
    secrets_state = _read_json(_SECRETS_S, {"entries": {}})
    secrets_lage = _secret_state(secrets_state, _read_text(_SECRETS_REPORT))
    clicks = _read_json(_CLICK_S, {})
    clicks_meta = _read_json(_CLICK_META, {}) or {}
    awin = _read_json(_AWIN_P, {})
    readability = _avg_readability()
    lektor = _lektor_findings()
    casing = _casing_state()
    # Affiliate-Klick-Attribution: summiert Klicks über Pillars / Artikel.
    click_articles = (clicks.get("articles") or {})
    click_pillars = (clicks.get("pillars") or {})
    total_clicks = sum(int(v.get("clicks", 0)) for v in click_articles.values())
    top_article = ""
    if click_articles:
        top_article = max(click_articles.items(), key=lambda kv: kv[1].get("clicks", 0))[0]

    # Secrets: die Wache selbst bewertet (rot = Kanal tot/fehlend, gelb = altern).
    # Vorher rechnete die Scorecard hier ein zweites Mal – mit anderer Regel und
    # ohne die Info-Stufen zu kennen; das Ergebnis war eine Ampel, die niemand
    # reproduzieren konnte.
    secret_red = secrets_lage["red"]

    # Awin-Provisions-Import (Klicks → Umsatz): aggregiert, DSGVO-sicher.
    _awin_un = awin.get("unmatched", 0)
    if isinstance(_awin_un, (list, tuple)):
        _awin_un = len(_awin_un)

    return {
        "date": TODAY.isoformat(),
        "live": live, "drafts": drafts,
        "pillars": pillars, "pillar_count": len(pillars),
        "decay_count": decay.get("count", 0),
        "cwv_verdict": cwv["verdict"], "cwv_state": cwv["state"], "cwv_display": cwv["display"],
        "cwv_age": cwv["age"], "cwv_findings": cwv["findings"], "cwv_red": cwv["red"],
        "cwv_measured": cwv["measured"],
        "readability": readability["avg"],
        "readability_floor": readability["floor"],
        # `lektor` = auto-behebbare Befunde (steuert Score & Empfehlung),
        # `lektor_advisory` = reine Stil-Hinweise (Info, nicht abstrafend).
        "lektor": (lektor or {}).get("auto") if lektor is not None else None,
        "lektor_advisory": (lektor or {}).get("advisory") if lektor is not None else None,
        # Casing: harte Befunde (Schreibkanon) steuern die Ampel, Hinweise sind
        # Redaktionsentscheidungen (Shouting-Betonung, angeklebte Ueberschriften).
        "casing": (casing or {}).get("hart") if casing is not None else None,
        "casing_hint": (casing or {}).get("hinweise") if casing is not None else None,
        "casing_dichte": (casing or {}).get("dichte") if casing is not None else None,
        "casing_trend": (casing or {}).get("trend") if casing is not None else None,
        "casing_geparkt": (casing or {}).get("geparkt") if casing is not None else None,
        "casing_stand": (casing or {}).get("stand") if casing is not None else None,
        "casing_hist": (casing or {}).get("tage") if casing is not None else None,
        "secret_red": secret_red,
        "secret_amber": secrets_lage["amber"], "secret_verdict": secrets_lage["verdict"],
        "secret_legacy": secrets_lage["legacy"],
        "secret_proven": secrets_lage["proven"], "secret_entries": secrets_lage["entries"],
        "click_articles": len(click_articles),
        "total_clicks": total_clicks,
        "top_article": top_article,
        "clicks_pipeline": clicks_meta.get("status") or "nie",
        "clicks_reason": clicks_meta.get("reason") or "",
        "clicks_stand": clicks_meta.get("written") or clicks_meta.get("attempted") or "nie",
        "awin_total": awin.get("total_commission", 0),
        "awin_paid": awin.get("total_paid", 0),
        "awin_articles": len(awin.get("articles", {})),
        "awin_unmatched": int(_awin_un or 0),
    }


def _readability_lamp(v):
    """Ampel für den Ø-Flesch-Wert (deutsche Amstad-Skala).

    Schwellen = Regelwerk R6: 🟢 ab Ziel Ø ≥ 62, 🟡 ab Bestands-Floor 55,
    🔴 darunter. Unbekannt ist NICHT grün – eine fehlende Messung ist ein
    Befund, kein Erfolg (vorher färbte `(v or 100) >= 70` sowohl `None` als
    auch 0 grün; Ziel „70“ war Artefakt, nicht Regelwerk).
    """
    if v is None:
        return "⚪"
    if v >= R_TARGET:
        return "🟢"
    if v >= R_FLOOR:
        return "🟡"
    return "🔴"


def _readability_floor_lamp(n):
    if not n:
        return "🟢"
    if n <= 3:
        return "🟡"
    return "🔴"


def _cwv_lamp(d):
    """Ampel inkl. Blindflug-Anzeige: nicht gemessen ≠ gut und ≠ schlecht."""
    if d.get("cwv_state") in ("STALE", "MISSING", "PARTIAL"):
        return "⚪"
    return {"GREEN": "🟢", "AMBER": "🟡", "RED": "🔴"}.get(d.get("cwv_verdict"), "⚪")


def _secret_lamp(d):
    if d.get("secret_legacy"):
        return "⚪"
    if d.get("secret_red", 0) > 0:
        return "🔴"
    if d.get("secret_amber", 0) > 0:
        return "🟡"
    if d.get("secret_verdict") == "GREEN":
        return "🟢"
    return "⚪"


def _render_datalage(d):
    """Was ist gemessen, was ist Lücke? (Agentur-Standard: keine Schein-Sicherheit.)"""
    body = [
        ("Core-Web-Vitals", "data/cwv_manifest.json",
         f"{(d.get('cwv_age') if d.get('cwv_age') is not None else '-')} d",
         {"OK": "gemessen", "STALE": "**zu alt – Messung läuft nicht**",
          "MISSING": "**fehlt**", "PARTIAL": "nur static/ (Build ausgefallen)"}
         .get(d.get("cwv_state"), "")),
        ("Decay-Radar", "data/decay_queue.json", "-",
         f"{d['decay_count']} Kandidat(en)"),
        ("Secrets", "SECRETS-REPORT.md + data/secrets_state.json", d.get("secret_verdict", "-"),
         "Report der v1-Wache – Format ohne Nachweis-Spalte, Neu erzeugen ausstehend"
         if d.get("secret_legacy") else
         f"{d.get('secret_proven', 0)}/{d['secret_entries']} live bewiesen"),
        ("Lektorat", "LEKTOR-REPORT.md",
         "heute" if os.path.exists(os.path.join(BLOG_DIR, "LEKTOR-REPORT.md")) else "fehlt",
         f"{d['lektor'] if d['lektor'] is not None else 'n/a'} auto-behebbar, "
         f"{d.get('lektor_advisory') if d.get('lektor_advisory') is not None else 'n/a'} Stil-Hinweise"),
        ("Casing", "CASING-REPORT.md + .casing_report.json",
         d.get("casing_stand") or "fehlt",
         f"{d['casing'] if d.get('casing') is not None else 'n/a'} hart, "
         f"{d.get('casing_hint') if d.get('casing_hint') is not None else 'n/a'} Hinweise, "
         f"{d['casing_hist'] or 0} Tage Historie"
         if d.get("casing") is not None else "Bericht noch nicht erzeugt "
         "(`casing_guard.py --json`)"),
        ("Affiliate-Klicks", "data/umami_clicks.json (via scripts/umami_clicks.py)",
         d.get("clicks_stand", "nie"),
         {"ok": "automatisch befüllt", "skipped": "Pipeline wartet auf Secret "
          "`UMAMI_API_TOKEN`"}.get(d.get("clicks_pipeline"), "Import nie gelaufen")),
        ("Awin-Provision", "data/awin_transactions.csv", "-",
         "CSV-Export fehlt" if int(d.get("awin_articles") or 0) == 0 else "befüllt"),
    ]
    out = ["| Kennzahl | Quelle | Stand | Bewertung |", "|---|---|---|---|"]
    for name, src, stand, note in body:
        out.append(f"| {name} | `{src}` | {stand} | {note} |")
    return "\n".join(out)


def _append_history(d, score):
    """Ein Score ohne Verlauf ist eine Meinung, keine Steuerung."""
    ampel = _ampel(score)
    row = {"date": d["date"], "score": score, "ampel": ampel,
           "live": d["live"], "drafts": d["drafts"], "decay": d["decay_count"],
           "cwv": d.get("cwv_verdict"), "cwv_state": d.get("cwv_state"),
           "readability": d["readability"], "lektor": d["lektor"],
           "secret_red": d["secret_red"], "secret_amber": d.get("secret_amber", 0),
           "clicks": d["total_clicks"], "awin": d["awin_total"]}
    try:
        os.makedirs(os.path.dirname(_HISTORY), exist_ok=True)
        with open(_HISTORY, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        lines = [l for l in open(_HISTORY, encoding="utf-8").read().splitlines() if l.strip()]
        if len(lines) > 260:                      # Retention: gut 5 Jahre Wochenläufe
            with open(_HISTORY, "w", encoding="utf-8") as f:
                f.write("\n".join(lines[-260:]) + "\n")
    except OSError:
        pass
    return row


def _score(d) -> int:
    """Gesamtscore 0..100."""
    s = 100
    # Content-Gesundheit: ein leerer/dünner Bestand = Problemlage
    if d["live"] < 15:
        s -= 15
    # Freshness blass: viele decay = Frische-Druck
    s -= min(30, d["decay_count"] * 3)
    # CWV: rot/amber nur, WENN gemessen wurde. Ein Blindflug (veraltete oder
    # ausgefallene Messung) kostet wenig, aber sichtbar – und die Empfehlung
    # nennt die Reparatur der Messung statt einer erfundenen Performance-Diagnose.
    if d.get("cwv_state") == "OK":
        if d["cwv_verdict"] == "RED":
            s -= 15
        elif d["cwv_verdict"] == "AMBER":
            s -= 7
    else:
        s -= 3
    # Lesbarkeit (wenn bekannt)
    if d["readability"] is not None:
        if d["readability"] < R_FLOOR:
            s -= 10
        elif d["readability"] < R_TARGET:
            s -= 4
    # Secrets: nur rote Befunde (Kanal tot/fehlt) ziehen ab, gelbe altern mit 1 pkt.
    s -= min(15, d["secret_red"] * 5) + min(2, d.get("secret_amber", 0))
    # Lektorat
    if d["lektor"] is not None:
        if d["lektor"] > 60:
            s -= 10
        elif d["lektor"] > 25:
            s -= 4
    # Monetarisierungs-Signal: Affiliate-Klicks vorhanden = gesunder Umsatz-Hebel;
    # ganz ohne Klick-Daten (neues Setup) ist das neutral, nicht strafend.
    if d.get("click_articles", 0) > 0:
        if d.get("total_clicks", 0) < 20:
            s -= 5
    # Monetarisierung (Awin-Provisions-Import): Umsatz-Maschinen belohnen.
    # Trade-off: Umsatz ist nur ein Bestandteil – er darf nie die Qualität
    # dominieren (~max +5). Kein Datensatz = neutral (kein Abzug).
    awin_total = float(d.get("awin_total", 0) or 0)
    awin_unmatched = int(d.get("awin_unmatched", 0) or 0)
    if awin_total > 0:
        s += min(5, int(awin_total / 50))  # alle 50 € +1, max +5
    # Nicht zugeordnete SubIDs = verlorene Umsatz-Zuordnung → warnen (min. 1).
    if awin_unmatched > 0:
        s -= min(3, awin_unmatched)
    return max(0, min(100, s))


def _ampel(score):
    if score >= 85:
        return "GREEN"
    if score >= 70:
        return "AMBER"
    return "RED"


def render(d, score):
    ampel = _ampel(score)
    prev, runs = _trend()
    trend = ""
    if prev is not None:
        delta = score - prev
        trend = f" · **Vorlauf {prev} → {score}** ({delta:+d})"
    elif runs:
        trend = " · erster erfasster Lauf"
    lines = [
        "# 🏆 Chefredakteur-Scorecard",
        f"**Stand:** {d['date']} · **Auftrag:** Redaktionelle Gesamt-Steuerung{trend}",
        "",
        f"## Gesamt-Score: **{score}/100** · Ampel: **{ampel}**",
        "",
        "| Kennzahl | Wert | Ampel |",
        "|---|---|---|",
        f"| Veröffentlichte Artikel | {d['live']} | {'🟢' if d['live'] >= 15 else '🔴'} |",
        f"| Entwürfe (Warteschlange) | {d['drafts']} | {_drafts_lamp(d['drafts'])} |",
        f"| Pillars / Themen-Cluster | {d['pillar_count']} | 🟢 |",
        f"| Decay-Kandidaten (STALE+DECAYING) | {d['decay_count']} | "
        f"{'🟢' if d['decay_count'] == 0 else ('🟡' if d['decay_count'] <= 5 else '🔴')} |",
        f"| Core-Web-Vitals | {d.get('cwv_display', d['cwv_verdict'])} | "
        f"{_cwv_lamp(d)} |",
        f"| Ø Lesbarkeit (Flesch, Ziel ≥ {R_TARGET:.0f}) | "
        f"{'n/a' if d['readability'] is None else d['readability']} | "
        f"{_readability_lamp(d['readability'])} |",
        f"| Artikel unter Flesch-Floor ({R_FLOOR:.0f}) | "
        f"{'n/a' if d['readability'] is None else len(d.get('readability_floor', []))} | "
        f"{'⚪' if d['readability'] is None else _readability_floor_lamp(len(d.get('readability_floor', [])))} |",
        f"| Lektorat-Befunde (auto-behebbar) | "
        f"{'n/a' if d['lektor'] is None else d['lektor']} | "
        f"{'⚪' if d['lektor'] is None else ('🟢' if d['lektor'] == 0 else '🟡')} |",
        f"| Stil-Hinweise (Lektorat, nur Info) | "
        f"{'n/a' if d.get('lektor_advisory') is None else d['lektor_advisory']} | ℹ️ |",
        f"| Groß-/Kleinschreibung – harte Befunde | "
        f"{'n/a' if d.get('casing') is None else d['casing']}"
        f"{' ' + chr(0xb7) + ' ' + str(d['casing_dichte']) + '/1.000 W.' if d.get('casing_dichte') else ''} "
        f"| {_casing_lamp(d)} |",
        f"| Schreibweise – Hinweise (nur Info) | "
        f"{'n/a' if d.get('casing_hint') is None else d.get('casing_hint')} | ℹ️ |",
        f"| Secrets ({'Wache v1 – Report veraltet' if d.get('secret_legacy') else 'rot / gelb / bewiesen'}) "
        f"| {d['secret_red']} / {d.get('secret_amber', 0)} / "
        f"{d.get('secret_proven', 0)} von {d['secret_entries']} | "
        f"{_secret_lamp(d)} |",
        f"| Affiliate-Klicks (Umsatz-Hebel) | {d['total_clicks']} über "
        f"{d['click_articles']} Artikel | "
        f"{_data_lamp(d['total_clicks'], d['click_articles'], d.get('clicks_pipeline') == 'ok')} |",
        f"| Awin-Provision (Klicks→Umsatz) | {d['awin_total']:.2f} € "
        f"({d['awin_paid']:.2f} € bezahlt) über {d['awin_articles']} Artikel | "
        f"{_data_lamp(int(d['awin_total'] or 0), d['awin_articles'], d['awin_articles'] > 0)} |",
        "",
        "## Affiliate-Klick-Attribution",
        "",
        _render_clicks(d),
        "",
        "## Awin-Provisions-Import (Monetarisierung)",
        "",
        _render_awin(d),
        "",
        "## Datenlagen (Messabdeckung)",
        "",
        _render_datalage(d),
        "",
        "## Pillar-Verteilung",
        "",
        _render_pillars(d["pillars"]),
        "",
        "## Handlungsempfehlungen",
        "",
    ]
    recs = []
    if d["decay_count"] > 0:
        recs.append(f"**{d['decay_count']}** Artikel veralten – `scripts/decay_radar.py` zeigt die "
                    "priorisierte Refresh-Queue (Stichtag-/Tarif-Themen zuerst).")
    if d.get("cwv_state") in ("STALE", "MISSING", "PARTIAL"):
        recs.append(f"Core-Web-Vitals **nicht aktuell gemessen** ({d.get('cwv_display')}) – "
                    "das ist eine Messlücke, keine Performance-Diagnose: Build-Step in "
                    "`premium-governance.yml` und `scripts/cwv_guard.py --public public/ "
                    "--strict-build` laufen lassen, bevor die Zahl wieder als Befund zählt.")
    elif d["cwv_verdict"] != "GREEN":
        recs.append("Core-Web-Vitals unter Soll – `scripts/cwv_guard.py` für Befunde; "
                    "Covers als AVIF/WebP, Bilder < 220 KB, `<img>` mit width/height.")
    if d.get("secret_legacy"):
        recs.append("Secrets-Wache im alten Format (ohne Nachweis-Spalte) – die Zeile "
                    "bleibt ⚪, bis `premium-governance.yml` den Report neu erzeugt "
                    "(Live-Probe `--verify`).")
    if d["secret_red"] > 0:
        recs.append(f"**{d['secret_red']}** rote Secret-Befunde – Kanal ist tot oder "
                    "abgelaufen: `python3 scripts/secrets_age_guard.py --verify` zeigt "
                    "live, welche API den Token ablehnt (Pinterest 30-Tage-Token, "
                    "Mastodon, KI-Keys).")
    elif d.get("secret_amber", 0) > 0:
        recs.append(f"{d['secret_amber']} gelber Secret-Hinweis(e) – altern, aber "
                    "functieren; `--verify` im Wochentakt hält den Nachweis frisch.")
    if d.get("casing"):
        recs.append(f"**{d['casing']}** harte Casing-Befunde (Marken/Akronymen/"
                    f"Tags) – `python3 scripts/casing_guard.py --fix --plan` heilt "
                    f"Inhalt UND Pinterest-Plan; `--gate` parkt betroffene "
                    f"Neugeburten stattdessen. Dichte: "
                    f"{d.get('casing_dichte')} je 1.000 Woerter.")
    if (d.get("casing_trend") or 0) > 0:
        recs.append(f"Casing verschlechtert um {d['casing_trend']} Befund(e) "
                    "gegenüber dem Vortag – meist ein Hinweis, dass ein Editor "
                    "(KI-Nachtrag, SEO-Keyword) vor der Wache geschrieben hat.")
    if d.get("casing_geparkt"):
        recs.append(f"{d['casing_geparkt']} Artikel wegen Casing-Gate geparkt – "
                    "CASING-REPORT.md zeigt die Zeilen; nach der Korrektur "
                    "entblockt `casing_guard.py --gate --new-only` automatisch.")
    if d["lektor"]:
        recs.append(f"**{d['lektor']}** auto-behebbare Lektorat-Befunde – "
                    "`scripts/lektor_guard.py --fix` (Doppelwörter, Füll-Phrasen, "
                    "Zahlenschreibweise).")
    # Stil-Hinweise sind KEIN --fix-Fall; sie brauchen redaktionelle Hand.
    if (d.get("lektor_advisory") or 0) > 120:
        recs.append(f"**{d['lektor_advisory']}** Stil-Hinweise (Echo, Nominalstil, "
                    "Weichmacher) – nicht automatisch behebbar. Redaktionell in der "
                    "Refresh-Queue mitziehen: `scripts/lektor_guard.py` listet die "
                    "Fundstellen pro Artikel.")
    if d["readability"] is not None and d["readability"] < R_TARGET:
        names = d.get("readability_floor", [])
        floor_txt = ""
        if names:
            slugs = [re.sub(r"^\d{4}-\d{2}-\d{2}-", "", n.split("/")[0]) for n in names[:4]]
            floor_txt = " Unter dem Floor: " + ", ".join(slugs) + "."
        recs.append(f"Ø Lesbarkeit {d['readability']} (Ziel ≥ {R_TARGET:.0f}, Regelwerk R6 – "
                    "vorher fälschlich „≥ 70“ in der Scorecard, nie im Regelwerk; "
                    "Zielgrößen sind seit 07.09.2026 vereinheitlicht). Lange Sätze splittern, "
                    "Nominalstil auflösen; Hebel je Artikel zeigt "
                    "`python3 scripts/readability_check.py --json`. Lesbarkeit ist bei "
                    "Pinterest-/Suchtraffic der Verweil-Dauer-Hebel." + floor_txt)
    if d["drafts"] > 0:
        recs.append(f"**{d['drafts']}** Artikel in der Entwurf-Warteschlange – Freigabe "
                    "prüfen (`python3 scripts/publish_gate.py` bzw. Kadenz-Gate). "
                    "Vorrat ist kein Mangel – erst > 8 Entwürfe werden zu Altlasten.")
    if d.get("clicks_pipeline") in (None, "nie", "skipped"):
        recs.append("Umsatz-Daten fehlen, weil die Pipeline nie gefüllt wurde – nicht, "
                    "weil niemand klickt: `python3 scripts/umami_clicks.py --fetch` "
                    "(Secret `UMAMI_API_TOKEN`; Website-ID steht schon in `hugo.toml`).")
    if not recs:
        recs.append("Keine akuten Handlungsfelder – Frequenz halten (Mo/Mi/Fr), "
                    "Decay & CWV weiter beobachten.")
    for r in recs:
        lines.append(f"- {r}")
    lines += ["", "_Erzeugt von `scripts/editorial_scorecard.py` (Chefredakteur-View)._"]
    return "\n".join(lines) + "\n"


def _render_clicks(d):
    """Zeigt den Umsatz-Hebel (Affiliate-Klicks) kompakt an."""
    if d.get("click_articles", 0) == 0:
        return "_Noch keine Klick-Daten – Umami-Export nach `data/umami_clicks.json` legen, " \
               "dann `scripts/click_attribution.py` ausführen._"
    top = d.get("top_article") or "-"
    top = top.rsplit("/", 2)[-2] if top else "-"
    return (f"- **{d['total_clicks']}** Affiliate-Klicks über **{d['click_articles']}** Artikel.\n"
            f"- **Umsatz-Maschine (Top):** `{top}`\n"
            f"- Empfehlung: Top-Arbeits-Check `scripts/click_attribution.py` für die "
            f"Voll-Liste (Umsatz-Hebel-Priorisierung).")


def _render_awin(d):
    """Zeigt den Awin-Umsatz-Hebel (Klicks→Umsatz) kompakt an."""
    total = float(d.get("awin_total", 0) or 0)
    if total <= 0:
        return ("_Noch keine Awin-Provisions-Daten – `scripts/awin_provisions.py` mit "
                "dem Awin-Transaktions-CSV ausführen (Dashboard → Reports → Transactions)._\n"
                "- Hinweis: `--gen-subid-map` erzeugt `data/subid_map.yaml`; danach "
                "`--awin-csv <pfad>` → `AWIN-REPORT.md` + `data/awin_provisions.json`.")
    unmatched = int(d.get("awin_unmatched", 0) or 0)
    lines = [
        f"- **{total:.2f} €** Provision (davon **{float(d.get('awin_paid', 0) or 0):.2f} €** "
        f"bezahlt) über **{d.get('awin_articles', 0)}** Artikel.",
        f"- **Umsatz-Maschine (Top-Artikel):** Top-Artikel siehe `AWIN-REPORT.md` "
        f"(Priorisierung nach Umsatz-Hebel).",
    ]
    if unmatched:
        lines.append(f"- ⚠ **{unmatched}** SubID(s) nicht zugeordnet → Umsatz geht verloren; "
                     f"`scripts/awin_provisions.py` zeigt die Liste (`data/subid_map.yaml` pflegen).")
    lines.append("- Empfehlung: `scripts/awin_provisions.py` laufend ausführen "
                 "(z. B. ins Content-Engine-Workflow nach `--ingest-csv` bündeln).")
    return "\n".join(lines)


def _render_pillars(counts):
    if not counts:
        return "_Keine Pillar-Zuordnung gefunden._"
    rows = ["| Pillar | Artikel |", "|---|---|"]
    for k in sorted(counts):
        rows.append(f"| {k} | {counts[k]} |")
    return "\n".join(rows)


def _selftest():
    failures = []
    # _ampel Grenzen
    if _ampel(90) != "GREEN" or _ampel(75) != "AMBER" or _ampel(50) != "RED":
        failures.append("Ampel-Grenzen")
    # --- _age_days: tolerierend, nie ratend
    ref = datetime.date(2026, 9, 7)
    if _age_days("2026-09-01", ref) != 6:
        failures.append("_age_days zählt falsch")
    if _age_days("2026-09-13", ref) != 0:
        failures.append("Zukunft datum gibt negativen Wert")
    if _age_days(None, ref) is not None or _age_days("gestern", ref) is not None:
        failures.append("_age_days rät bei Müll")
    # --- CWV-Herkunft (#206-Kern): veraltete Messung != Befund
    man_ok = {"generated": "2026-09-07", "verdict": "GREEN", "build_measured": True, "findings": []}
    st = _cwv_state(man_ok, ref)
    if st["state"] != "OK" or st["display"] != "GREEN" \
            or _cwv_lamp({"cwv_state": st["state"], "cwv_verdict": st["verdict"]}) != "🟢":
        failures.append(f"frische grüne CWV-Messung wird nicht als OK gelesen ({st})")
    st = _cwv_state({"generated": "2026-08-20", "verdict": "AMBER", "findings": [
        {"level": "amber", "code": "img_soft"}]}, ref)
    if st["state"] != "STALE" \
            or _cwv_lamp({"cwv_state": st["state"], "cwv_verdict": st["verdict"]}) != "⚪":
        failures.append("veraltetes Manifest wird als aktueller Befund verkauft (#206-Fall)")
    st = _cwv_state({"generated": "2026-09-07", "verdict": "GREEN", "build_measured": False,
                     "findings": [{"level": "info", "code": "build_missing"}]}, ref)
    if st["state"] != "PARTIAL":
        failures.append("Build-Lücke (public/ fehlgeschlagen) bleibt unsichtbar")
    if _cwv_state({}, ref)["state"] != "MISSING":
        failures.append("fehlendes Manifest != MISSING")
    # --- Score: Blindflug < echter roter Befund (Reihenfolge muss stimmen)
    base = {"live": 20, "decay_count": 0, "lektor": 0, "secret_red": 0, "readability": 80}
    s_ok = _score(dict(base, cwv_state="OK", cwv_verdict="GREEN"))
    s_red = _score(dict(base, cwv_state="OK", cwv_verdict="RED"))
    s_blind = _score(dict(base, cwv_state="STALE", cwv_verdict="AMBER"))
    if not (s_ok > s_blind > s_red):
        failures.append(f"Score-Hierarchie CWV falsch: ok={s_ok} blind={s_blind} rot={s_red}")
    # --- Secrets-Ampel aus Report-Policy (nicht aus eigener Rechnung)
    lage = _secret_state({"entries": {"A": {"quality": "proven"}}},
                         "| Secret | Status | Nachweis |\n|---|---|---|\n"
                         "## Gesamt-Ampel: **RED**\n\n| RED | dead | `A` – tot |\n"
                         "| AMBER | aging | `B` – alt |")
    if lage["red"] != 1 or lage["amber"] != 1 or lage["verdict"] != "RED" or lage["proven"] != 1:
        failures.append(f"Secrets-Report wird falsch gelesen: {lage}")
    legacy = _secret_state({"entries": {"A": {}}},
                           "| Secret | Status |\n|---|---|\n## Gesamt-Ampel: **AMBER**\n"
                           "\n| AMBER | untracked | `PINTEREST` – kein Erfolgs-Log |")
    if not legacy["legacy"] or legacy["red"] or legacy["amber"]:
        failures.append("v1-Report (ohne Nachweis-Spalte) wird als Bewertung gelesen")
    if _secret_lamp({"secret_legacy": True, "secret_red": 0, "secret_amber": 0}) != "⚪":
        failures.append("Legacy-Secrets-Zeile leuchtet trotzdem")
    if _secret_lamp({"secret_red": 1}) != "🔴" or _secret_lamp({"secret_red": 0, "secret_amber": 2}) != "🟡" \
            or _secret_lamp({"secret_red": 0, "secret_amber": 0, "secret_verdict": "GREEN"}) != "🟢":
        failures.append("Secrets-Lampe inkonsistent")
    # --- Entwurfs-Lampe: 0 Entwürfe dürfen nie gelb sein (war Dauer-🟡 in #206)
    if _drafts_lamp(0) != "🟢" or _drafts_lamp(2) != "⚪" or _drafts_lamp(9) not in ("🟡", "🔴"):
        failures.append("Entwurfs-Lampe bestraft den leeren Warteschlangen-Stand")
    # --- Datenlampen: „noch keine Daten" ist ⚪, nicht 🟡
    if _data_lamp(0, 0, False) != "⚪" or _data_lamp(0, 0, True) != "🟡" \
            or _data_lamp(250, 5, True) != "🟢":
        failures.append("Monetarisierungs-Lampe verwechselt Datenlücke mit Befund")
    # --- Casing-Lampe: Datenluecke ⚪, sauber 🟢, Ausreisser 🔴
    if _casing_lamp({"casing": None}) != "⚪" or _casing_lamp({"casing": 0}) != "🟢" \
            or _casing_lamp({"casing": 2}) != "🟡" or _casing_lamp({"casing": 9}) != "🔴" \
            or _casing_lamp({"casing": 0, "casing_geparkt": 1}) != "🟡":
        failures.append("Casing-Lampe verwechselt Datenluecke/Befund/Parken")
    if _casing_state() is not None:
        _c = _casing_state()
        if _c["hart"] < 0 or (_c["dichte"] or 0) < 0:
            failures.append("Casing-Zustand negativ")
    # --- _age_days in render(): fehlende Historie darf nicht crashen
    if _trend()[0] is not None and not isinstance(_trend()[0], int):
        failures.append("Trend-Lieferform unstetig")
    # _score monoton (mehr decay = schlechter)
    a = _score({"live": 20, "decay_count": 0, "cwv_verdict": "GREEN",
                "readability": 80, "lektor": 10, "secret_red": 0})
    b = _score({"live": 20, "decay_count": 8, "cwv_verdict": "RED",
                "readability": 50, "lektor": 80, "secret_red": 3})
    if not (a > b):
        failures.append("Score-Monotonie: a={}, b={}".format(a, b))
    # Awin-Monetarisierung: Umsatz belohnt (max +5), kein Datensatz = neutral,
    # unmatched SubIDs warnen (min. 1) – darf nie Qualität dominieren.
    # Basis mit Spielraum: lektor 50 (-4), secret_red 1 (-5) → Base 91.
    base_rev = {"live": 20, "decay_count": 0, "cwv_verdict": "GREEN",
                "readability": 80, "lektor": 50, "secret_red": 1}
    c = _score(dict(base_rev, awin_total=250))
    d0 = _score(base_rev)
    if not (c > d0 and (c - d0) <= 5):
        failures.append("Awin-Bonus begrenzt: c={}, d0={}".format(c, d0))
    cu = _score(dict(base_rev, awin_total=250, awin_unmatched=4))
    if not (c > cu and (c - cu) <= 3):
        failures.append("Awin-unmatched-Abzug begrenzt: c={}, cu={}".format(c, cu))
    if failures:
        print("❌ SCORECARD-SELFTEST FEHLGESCHLAGEN:")
        for f in failures:
            print("   -", f)
        return 2
    print("✅ SCORECARD-SELFTEST bestanden (Ampel-Grenzen, Score-Monotonie).")
    return 0


def main():
    if "--selftest" in sys.argv:
        return _selftest()
    d = collect()
    score = _score(d)
    rep = render(d, score)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write(rep)
    _append_history(d, score)
    print(rep)
    if "--issue" in sys.argv and score < 75:
        print("\n===== ISSUE BODY =====\n")
        print(f"## 🏆 Chefredakteur-Scorecard: **{score}/100** ({_ampel(score)})\n\n{rep}")
    return 0 if score >= 75 else 1


if __name__ == "__main__":
    sys.exit(main())
