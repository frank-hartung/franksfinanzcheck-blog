#!/usr/bin/env python3
# ============================================================
#  SOCIAL-PERF-FEEDBACK – der fehlende Rückkanal des Autopiloten
#  ------------------------------------------------------------
#  AUFTRAG (Frank, 03.10.2026, Audit "Highend-Level weltweit"):
#  Der Social-Planer (`social_planner.py`) plant bisher rein nach
#  Regeln (Launch-Welle, Evergreen-Rotation, Themenmix) – aber ohne
#  jedes Wissen darüber, was tatsächlich funktioniert hat. Pinterest
#  hat mit `pinterest_perf_feedback.py` längst eine Lernschleife;
#  für alle anderen Kanäle fehlte sie. Dieses Skript schließt den
#  Kreis für den GESAMTEN Autopiloten (aktuell: Mastodon live,
#  weitere Kanäle schalten sich automatisch zu, sobald sie Tokens
#  und damit echte Sendehistorie haben – siehe METRIC_FETCHERS).
#
#  ABLAUF
#    1 LESEN    `data/social/state.yaml` (Sendehistorie) + Artikel-Pool
#               (Slug → Pillar/Themenwelt über social_copywriter)
#    2 MESSEN   `--fetch`: aktuelle Kennzahlen je Kanal nachladen
#               (Mastodon: favourites/reblogs/replies, öffentlich,
#               kein Token nötig). Ohne `--fetch` wird nur der
#               bestehende Cache (`data/social/engagement_cache.json`)
#               verwendet – der Lauf bleibt dann netzlos und schnell.
#    3 BEWERTEN Score je Winkel und je Themenwelt/Pillar, mit
#               Bayes'scher Glättung (Epsilon-Smoothing) gegen den
#               Kanal-Durchschnitt – ein einzelner Ausreißer-Post
#               darf die Gewichtung nicht kippen.
#    4 SCHREIBEN `data/social/performance.yaml` (von social_planner.py
#               gelesen: Winkel-Gewichte fürs Multi-Armed-Bandit,
#               Cooldown-Faktor je Pillar) + `SOCIAL-PERF-REPORT.md`
#               (Cockpit) + Audit-Zeile in
#               `data/social/performance_history.jsonl`.
#
#  WARUM DAS SO UND NICHT ANDERS:
#    - Reblogs wiegen am schwersten (W_BOOST): ein Reblog verteilt den
#      Post außerhalb des eigenen Publikums – das eigentliche Ziel von
#      organischem Social. Favoriten sind ein schwächeres Signal,
#      Antworten ein mittleres (echte Interaktion, aber oft nur 1:1).
#    - Mindest-Stichprobe (MIN_SAMPLES): Ein Winkel mit nur einem Post
#      bekommt KEIN Gewicht ungleich 1.0 – sonst overfittet die Engine
#      auf Zufall. Das ist bewusst konservativer als nötig.
#    - 80/20-Bandit (nicht 100/0): Der Planer bevorzugt den bisherigen
#      Sieger-Winkel in 80 % der Fälle, probiert in 20 % bewusst einen
#      anderen – sonst lernt die Engine nie etwas Neues dazu, wenn sich
#      Geschmack/Algorithmus ändert.
#    - Harmlos ohne Daten: Kanäle ohne Historie (Standby) erscheinen im
#      Report als "noch keine Daten" – kein Fehler, kein Absturz.
#
#  Aufruf:
#    python3 scripts/social_perf_feedback.py              # aus Cache
#    python3 scripts/social_perf_feedback.py --fetch       # + Netz
#    python3 scripts/social_perf_feedback.py --dry-run     # nichts schreiben
#    python3 scripts/social_perf_feedback.py --selftest
#
#  Regie: data/social/channels.yaml (Winkel je Kanal), gelesen von
#  social_planner.load_performance(). Anleitung:
#  docs/ANLEITUNG-SOCIAL-PERF-FEEDBACK.md
# ============================================================
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BLOG_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

DATA_DIR = os.path.join(BLOG_DIR, "data", "social")
STATE_FILE = os.path.join(DATA_DIR, "state.yaml")
CACHE_FILE = os.path.join(DATA_DIR, "engagement_cache.json")
PERFORMANCE_FILE = os.path.join(DATA_DIR, "performance.yaml")
HISTORY_FILE = os.path.join(DATA_DIR, "performance_history.jsonl")
REPORT_FILE = os.path.join(BLOG_DIR, "SOCIAL-PERF-REPORT.md")

TODAY = _dt.date.today()
WINDOW_DAYS = 60          # nur Posts der letzten X Tage fließen in den Score ein
MIN_SAMPLES = 3           # unter dieser Stichprobe bleibt das Gewicht neutral (1.0)
FETCH_REFRESH_HOURS = 20  # Cache-Eintrag gilt erst nach dieser Zeit wieder als "frisch zu holen"
MAX_FETCH_PER_RUN = 60    # Rate-Limit-Schonung je Lauf

# Signal-Gewichte (Reichweite über das eigene Publikum hinaus zählt am meisten)
W_FAV = 1.0     # Gefällt-mir/Favorit – schwächstes Signal, aber am häufigsten
W_BOOST = 1.8   # Reblog/Share/Repost – verteilt den Post, das eigentliche Ziel
W_REPLY = 1.3   # Antwort/Kommentar – echte Interaktion, aber selten
EP = 3.0        # Pseudo-Count fürs Epsilon-Smoothing (Bayes gegen Kanal-Mittel)

COOLDOWN_MIN_FACTOR = 0.6   # Top-Performer: Sperrfrist höchstens auf 60 % verkürzen
COOLDOWN_MAX_FACTOR = 1.4   # Flops: Sperrfrist höchstens auf 140 % verlängern

# Je Kanal eine Funktion, die (ref, channel_cfg) -> {"favourites","reblogs","replies"}
# oder None liefert. Neue Kanäle reihen sich hier ein, sobald sie live senden –
# der Rest der Maschine (Scoring, Gewichtung, Report) ist bereits kanal-generisch.
METRIC_FETCHERS: dict = {}


def _load_yaml(path: str, default):
    try:
        import yaml

        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or default
    except FileNotFoundError:
        return default
    except Exception as exc:  # noqa: BLE001
        print(f"⚠ {os.path.basename(path)} nicht lesbar ({exc}) – nutze Leerwert.")
        return default


def _save_yaml(path: str, data) -> None:
    import yaml

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, allow_unicode=True, sort_keys=False)


def _load_json(path: str, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _save_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")


# ------------------------------------------------------------------ Eingaben
def load_history(window_days: int = WINDOW_DAYS) -> list[dict]:
    """Erfolgreiche Sendungen der letzten `window_days` Tage aus state.yaml."""
    state = _load_yaml(STATE_FILE, {})
    cutoff = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=window_days)
    out = []
    for entry in (state.get("history") or []):
        if not entry.get("ok"):
            continue
        at = _parse_dt(entry.get("posted_at") or "")
        if at and at < cutoff:
            continue
        out.append(entry)
    return out


def _parse_dt(value: str):
    if not value:
        return None
    try:
        dt = _dt.datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_dt.timezone.utc)
    return dt


def slug_pillar_map() -> dict:
    """Slug -> Pillar/Themenwelt, aus dem echten Artikel-Bestand.

    Fällt bewusst auf ein leeres Dict zurück, wenn der Bestand nicht lesbar
    ist (z. B. in Unit-Tests ohne Content-Verzeichnis) – der Score rechnet
    dann einfach ohne Pillar-Aufschlüsselung weiter.
    """
    try:
        import social_copywriter as copy

        pool = copy.article_pool()
        return {a["slug"]: (a.get("pillar") or "") for a in pool if a.get("slug")}
    except Exception as exc:  # noqa: BLE001
        print(f"⚠ Artikel-Bestand nicht lesbar ({exc.__class__.__name__}) – "
              f"Score ohne Pillar-Aufschlüsselung.")
        return {}


# ------------------------------------------------------------------- Messung
def _mastodon_instance(entry: dict) -> str:
    return (os.environ.get("MASTODON_INSTANCE") or "https://mastodon.social").strip().rstrip("/")


def fetch_mastodon(entry: dict) -> dict | None:
    """Liest favourites/reblogs/replies eines öffentlichen Toots (kein Token nötig)."""
    ref = str(entry.get("ref") or "").strip()
    if not ref or not ref.isdigit():
        return None
    try:
        import social_channels as sch
    except Exception:  # noqa: BLE001
        return None
    instance = _mastodon_instance(entry)
    headers = {}
    token = (os.environ.get("MASTODON_ACCESS_TOKEN") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    status, data, err = sch.http_json(
        f"{instance}/api/v1/statuses/{ref}", headers=headers or None, method="GET", retries=2,
    )
    if err or not isinstance(data, dict):
        return None
    return {
        "favourites": int(data.get("favourites_count") or 0),
        "reblogs": int(data.get("reblogs_count") or 0),
        "replies": int(data.get("replies_count") or 0),
    }


METRIC_FETCHERS["mastodon"] = fetch_mastodon


def refresh_cache(history: list[dict], limit: int = MAX_FETCH_PER_RUN) -> dict:
    """Holt frische Kennzahlen für Posts, deren Cache-Eintrag fehlt oder alt ist."""
    cache = _load_json(CACHE_FILE, {})
    now = _dt.datetime.now(_dt.timezone.utc)
    fetched = 0
    for entry in history:
        if fetched >= limit:
            break
        channel = entry.get("channel") or ""
        ref = str(entry.get("ref") or "")
        fetcher = METRIC_FETCHERS.get(channel)
        if not fetcher or not ref:
            continue
        bucket = cache.setdefault(channel, {})
        cached = bucket.get(ref)
        if cached:
            last = _parse_dt(cached.get("fetched_at") or "")
            if last and (now - last) < _dt.timedelta(hours=FETCH_REFRESH_HOURS):
                continue
        metrics = fetcher(entry)
        fetched += 1
        if metrics is None:
            continue
        metrics["fetched_at"] = now.isoformat()
        bucket[ref] = metrics
    if fetched:
        _save_json(CACHE_FILE, cache)
        print(f"  → {fetched} Kennzahlen-Abfrage(n) aktualisiert.")
    return cache


# ------------------------------------------------------------------ Scoring
def _raw_score(metrics: dict) -> float:
    return (
        float(metrics.get("favourites") or 0) * W_FAV
        + float(metrics.get("reblogs") or 0) * W_BOOST
        + float(metrics.get("replies") or 0) * W_REPLY
    )


def _aggregate(buckets: dict) -> dict:
    """buckets: key -> list[raw_score]. Liefert key -> {score, samples}.

    `score` ist relativ zum Durchschnitt ALLER Einträge dieses Kanals
    (1.0 = Durchschnitt), geglättet mit einem Pseudo-Count EP gegen den
    Durchschnitt – das dämpft Ausreißer bei kleinen Stichproben.
    """
    all_scores = [s for lst in buckets.values() for s in lst]
    if not all_scores:
        return {}
    global_avg = sum(all_scores) / len(all_scores)
    global_avg = global_avg or 1.0  # Division durch 0 vermeiden, wenn alles 0 ist
    out = {}
    for key, scores in buckets.items():
        n = len(scores)
        total = sum(scores)
        smoothed = (total + EP * global_avg) / (n + EP)
        out[key] = {"score": round(smoothed / global_avg, 3), "samples": n}
    return out


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def cooldown_factor_for(score: float) -> float:
    """Score > 1 (überdurchschnittlich) → Faktor < 1 (kürzere Sperrfrist).
    Score < 1 (unterdurchschnittlich) → Faktor > 1 (längere Sperrfrist)."""
    score = max(0.4, score)
    return round(_clamp(1.0 / score, COOLDOWN_MIN_FACTOR, COOLDOWN_MAX_FACTOR), 3)


def build_performance(history: list[dict], cache: dict, slug_pillar: dict,
                      min_samples: int = MIN_SAMPLES) -> dict:
    """Baut die komplette Auswertung je Kanal aus Historie + Kennzahlen-Cache."""
    by_channel: dict[str, list[dict]] = {}
    for entry in history:
        by_channel.setdefault(entry.get("channel") or "", []).append(entry)

    channels_out = {}
    for channel, entries in sorted(by_channel.items()):
        bucket = cache.get(channel) or {}
        angle_scores: dict[str, list[float]] = {}
        pillar_scores: dict[str, list[float]] = {}
        posts = []
        for entry in entries:
            ref = str(entry.get("ref") or "")
            metrics = bucket.get(ref)
            if not metrics:
                continue
            raw = _raw_score(metrics)
            angle = entry.get("angle") or ""
            slug = entry.get("slug") or ""
            pillar = slug_pillar.get(slug, "")
            if angle:
                angle_scores.setdefault(angle, []).append(raw)
            if pillar:
                pillar_scores.setdefault(pillar, []).append(raw)
            posts.append({
                "slug": slug, "angle": angle, "pillar": pillar,
                "raw": round(raw, 2), "url": entry.get("url") or "",
                "title": entry.get("title") or "",
            })

        angle_agg = _aggregate(angle_scores)
        pillar_agg = _aggregate(pillar_scores)

        # Unterhalb der Mindeststichprobe bleibt das Gewicht neutral (1.0) –
        # sonst overfittet die Engine auf einen einzelnen Zufallstreffer.
        angle_weights = {
            a: (d["score"] if d["samples"] >= min_samples else 1.0)
            for a, d in angle_agg.items()
        }
        pillar_weights = {
            p: {
                "score": d["score"] if d["samples"] >= min_samples else 1.0,
                "samples": d["samples"],
                "cooldown_factor": (cooldown_factor_for(d["score"])
                                    if d["samples"] >= min_samples else 1.0),
            }
            for p, d in pillar_agg.items()
        }

        posts.sort(key=lambda p: p["raw"], reverse=True)
        channels_out[channel] = {
            "samples": len(posts),
            "angles": {a: {"score": angle_weights[a], "samples": angle_agg[a]["samples"]}
                      for a in angle_agg},
            "pillars": pillar_weights,
            "top": posts[:5],
            "flop": list(reversed(posts[-5:])) if len(posts) > 5 else [],
        }

    return {
        "version": 1,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "window_days": WINDOW_DAYS,
        "min_samples": min_samples,
        "channels": channels_out,
    }


# ------------------------------------------------------------------- Bericht
def render_report(perf: dict, all_channel_ids: list[str]) -> str:
    lines = [
        "# 📈 SOCIAL-PERF-REPORT",
        "",
        f"**Stand:** {TODAY.isoformat()} · Fenster: {perf.get('window_days')} Tage · "
        f"Mindeststichprobe: {perf.get('min_samples')} Posts",
        "",
        "Rückkanal \"Was performt?\" für den Social-Autopiloten. Score 1.0 = "
        "Kanal-Durchschnitt; die Werte fließen automatisch in "
        "`data/social/performance.yaml` und werden vom Planer gelesen "
        "(Winkel-Gewichtung + Cooldown je Themenwelt).",
        "",
    ]
    channels = perf.get("channels") or {}
    for cid in sorted(set(all_channel_ids) | set(channels.keys())):
        data = channels.get(cid)
        lines.append(f"## {cid}")
        lines.append("")
        if not data or not data.get("samples"):
            lines.append("_Noch keine Daten – Kanal im Standby oder frisch aktiv. "
                         "Winkel werden gleichverteilt ausprobiert (reine Exploration)._")
            lines.append("")
            continue
        lines.append(f"**{data['samples']} gemessene Posts** in diesem Fenster.")
        lines.append("")
        if data.get("angles"):
            lines.append("| Winkel | Score | Stichprobe |")
            lines.append("|---|---|---|")
            for a, d in sorted(data["angles"].items(), key=lambda kv: -kv[1]["score"]):
                lines.append(f"| {a} | {d['score']} | {d['samples']} |")
            lines.append("")
        if data.get("pillars"):
            lines.append("| Themenwelt | Score | Cooldown-Faktor | Stichprobe |")
            lines.append("|---|---|---|---|")
            for p, d in sorted(data["pillars"].items(), key=lambda kv: -kv[1]["score"]):
                lines.append(f"| {p} | {d['score']} | {d['cooldown_factor']} | {d['samples']} |")
            lines.append("")
        if data.get("top"):
            best = data["top"][0]
            lines.append(f"**Bester Post:** „{best['title']}“ ({best['angle']}, "
                         f"Score {best['raw']}) → {best['url']}")
            lines.append("")
        if data.get("flop"):
            worst = data["flop"][0]
            lines.append(f"**Schwächster Post:** „{worst['title']}“ ({worst['angle']}, "
                         f"Score {worst['raw']})")
            lines.append("")
    lines += [
        "## 🎯 Was die Engine daraus macht",
        "",
        "1. **Winkel-Bandit (80/20):** Der Planer wählt den Sieger-Winkel in 80 % "
        "der Fälle, probiert in 20 % bewusst einen anderen – damit lernt er "
        "weiter dazu, statt sich festzufahren.",
        "2. **Cooldown nach Erfolg:** Themenwelten mit überdurchschnittlichem "
        "Score kommen bis zu 40 % früher wieder dran (Evergreen-Recycling); "
        "Flops bis zu 40 % später.",
        "3. **Ohne Daten = Exploration:** Kanäle ohne Historie bekommen keine "
        "Vorab-Meinung aufgezwungen – sie probieren alle Winkel gleich oft, "
        "bis genug Stichprobe da ist.",
        "",
        f"_Erzeugt von `scripts/social_perf_feedback.py` am {TODAY.isoformat()}._",
    ]
    return "\n".join(lines) + "\n"


def _append_history(perf: dict) -> None:
    rec = {"date": TODAY.isoformat()}
    for cid, data in (perf.get("channels") or {}).items():
        angles = data.get("angles") or {"": {"score": 0}}
        pillars = data.get("pillars") or {"": {"score": 0}}
        top_angle = max(angles.items(), key=lambda kv: kv[1]["score"], default=("", {}))[0]
        top_pillar = max(pillars.items(), key=lambda kv: kv[1]["score"], default=("", {}))[0]
        rec[cid] = {"samples": data.get("samples", 0), "top_angle": top_angle,
                   "top_pillar": top_pillar}
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


# -------------------------------------------------------------------- Lauf
def run(fetch: bool = False, dry_run: bool = False) -> int:
    history = load_history()
    cache = _load_json(CACHE_FILE, {})
    if fetch:
        cache = refresh_cache(history)
    slug_pillar = slug_pillar_map()
    perf = build_performance(history, cache, slug_pillar)

    try:
        import social_channels as sch

        cfg = sch.load_config()
        all_channel_ids = list(sch.channel_map(cfg).keys())
    except Exception:  # noqa: BLE001
        all_channel_ids = list(perf.get("channels") or {}).copy()

    report = render_report(perf, all_channel_ids)

    print(f"Historie: {len(history)} Posts im {WINDOW_DAYS}-Tage-Fenster, "
         f"{len(perf.get('channels') or {})} Kanal/Kanäle mit gemessenen Daten.")

    if dry_run:
        print("--dry-run: nichts geschrieben.")
        print(report)
        return 0

    _save_yaml(PERFORMANCE_FILE, perf)
    with open(REPORT_FILE, "w", encoding="utf-8") as fh:
        fh.write(report)
    _append_history(perf)
    print(f"✓ {PERFORMANCE_FILE} und {REPORT_FILE} aktualisiert.")
    return 0


# ---------------------------------------------------------------- Selbsttest
def _selftest() -> int:
    failures = []

    # Reblogs müssen stärker wiegen als Favoriten bei gleicher Summe.
    hi_boost = _raw_score({"favourites": 0, "reblogs": 10, "replies": 0})
    hi_fav = _raw_score({"favourites": 10, "reblogs": 0, "replies": 0})
    if not (hi_boost > hi_fav):
        failures.append("Reblogs wiegen nicht stärker als Favoriten")

    # Aggregation: ein Winkel mit durchweg hohen Werten bekommt Score > 1.
    agg = _aggregate({
        "gut": [20.0, 22.0, 18.0, 21.0],
        "schlecht": [1.0, 0.0, 2.0, 1.0],
    })
    if not (agg["gut"]["score"] > 1.0 > agg["schlecht"]["score"]):
        failures.append(f"Score-Trennung versagt: {agg}")

    # Mindeststichprobe: zu wenige Datenpunkte -> neutrales Gewicht (1.0),
    # auch wenn der Rohwert extrem wäre.
    history = [
        {"channel": "x", "ref": "1", "ok": True, "angle": "mythos", "slug": "s1",
         "posted_at": _dt.datetime.now(_dt.timezone.utc).isoformat()},
    ]
    cache = {"x": {"1": {"favourites": 999, "reblogs": 999, "replies": 999}}}
    perf_one = build_performance(history, cache, {"s1": "strom-sparen"})
    angle_w = perf_one["channels"]["x"]["angles"]["mythos"]["score"]
    if angle_w != 1.0:
        failures.append(f"Mindeststichprobe greift nicht: Gewicht {angle_w} bei 1 Sample")

    # Cooldown-Faktor: monoton fallend mit steigendem Score, innerhalb der Grenzen.
    f_hi = cooldown_factor_for(2.5)
    f_mid = cooldown_factor_for(1.0)
    f_lo = cooldown_factor_for(0.3)
    if not (f_hi <= f_mid <= f_lo):
        failures.append(f"Cooldown-Faktor nicht monoton: {f_hi} / {f_mid} / {f_lo}")
    if not (COOLDOWN_MIN_FACTOR <= f_hi and f_lo <= COOLDOWN_MAX_FACTOR):
        failures.append("Cooldown-Faktor verlässt die erlaubten Grenzen")

    # Leere Eingabe darf nie knallen – nur ein leeres Ergebnis liefern.
    empty = build_performance([], {}, {})
    if empty.get("channels") != {}:
        failures.append("Leere Historie erzeugt trotzdem Kanaldaten")

    # Report für einen datenlosen Kanal darf nicht crashen und muss den
    # Standby-Hinweis enthalten.
    report = render_report(empty, ["bluesky"])
    if "Noch keine Daten" not in report:
        failures.append("Report meldet datenlosen Kanal nicht als Standby")

    # Idempotenz: zweimal denselben Input aggregieren liefert denselben Score.
    agg_again = _aggregate({"gut": [20.0, 22.0, 18.0, 21.0], "schlecht": [1.0, 0.0, 2.0, 1.0]})
    if agg_again != agg:
        failures.append("Aggregation ist nicht deterministisch")

    # History-Anhang darf bei echten Kanaldaten nicht crashen (Regressionstest
    # für einen Bug, bei dem `or`-Operator-Vorrang .items() auf das falsche
    # Objekt anwendete). Schreibt bewusst in eine Temp-Datei, nie ins Repo.
    import tempfile

    global HISTORY_FILE
    real_history_file = HISTORY_FILE
    try:
        with tempfile.TemporaryDirectory() as tmp:
            HISTORY_FILE = os.path.join(tmp, "performance_history.jsonl")
            _append_history(perf_one)
            with open(HISTORY_FILE, encoding="utf-8") as fh:
                last_line = fh.readlines()[-1]
            if "mythos" not in last_line:
                failures.append("History-Zeile enthält nicht den erwarteten Top-Winkel")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"_append_history crasht bei echten Kanaldaten: {exc}")
    finally:
        HISTORY_FILE = real_history_file

    if failures:
        print("❌ SOCIAL-PERF-FEEDBACK-SELFTEST FEHLGESCHLAGEN:")
        for f in failures:
            print("   -", f)
        return 2
    print("✅ SOCIAL-PERF-FEEDBACK-SELFTEST bestanden (Signal-Gewichtung, "
         "Mindeststichprobe, Cooldown-Grenzen, Standby-Robustheit, Determinismus).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Social-Perf-Feedback – Rückkanal des Autopiloten")
    ap.add_argument("--fetch", action="store_true",
                    help="frische Kennzahlen je Kanal nachladen (Netzzugriff)")
    ap.add_argument("--dry-run", action="store_true", help="nur anzeigen, nichts schreiben")
    ap.add_argument("--selftest", action="store_true", help="eingefrorene Testfälle")
    args = ap.parse_args()

    if args.selftest:
        return _selftest()
    return run(fetch=args.fetch, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
