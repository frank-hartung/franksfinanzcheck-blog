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
_AWIN_P = DATA("awin_provisions.json")


def _read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


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
        return None
    scores = []
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
    if not scores:
        return None
    return round(statistics.mean(scores), 1)


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


def collect():
    """Sammelt alle Daten für die Scorecard."""
    live, drafts = _count_live_drafts()
    pillars = _pillar_counts()
    decay = _read_json(_DECAY_Q, {"count": 0, "queue": []})
    cwv = _read_json(_CWV_M, {})
    secrets = _read_json(_SECRETS_S, {"entries": {}})
    clicks = _read_json(_CLICK_S, {})
    awin = _read_json(_AWIN_P, {})
    readability = _avg_readability()
    lektor = _lektor_findings()

    # Affiliate-Klick-Attribution: summiert Klicks über Pillars / Artikel.
    click_articles = (clicks.get("articles") or {})
    click_pillars = (clicks.get("pillars") or {})
    total_clicks = sum(int(v.get("clicks", 0)) for v in click_articles.values())
    top_article = ""
    if click_articles:
        top_article = max(click_articles.items(), key=lambda kv: kv[1].get("clicks", 0))[0]

    # Secrets: Anzahl fehlender/"roter" Einträge über Env
    # (SCORECARD nutzt denselben Ansatz minimal: nur rot, wenn gesetzt aber stale)
    secret_red = 0
    for var, ent in (secrets.get("entries") or {}).items():
        ls = ent.get("last_success")
        if ls:
            age = (TODAY - datetime.date.fromisoformat(ls)).days
            if age > 60:
                secret_red += 1

    # Awin-Provisions-Import (Klicks → Umsatz): aggregiert, DSGVO-sicher.
    _awin_un = awin.get("unmatched", 0)
    if isinstance(_awin_un, (list, tuple)):
        _awin_un = len(_awin_un)

    return {
        "date": TODAY.isoformat(),
        "live": live, "drafts": drafts,
        "pillars": pillars, "pillar_count": len(pillars),
        "decay_count": decay.get("count", 0),
        "cwv_verdict": cwv.get("verdict", "UNKNOWN"),
        "cwv_findings": len(cwv.get("findings", [])),
        "readability": readability,
        # `lektor` = auto-behebbare Befunde (steuert Score & Empfehlung),
        # `lektor_advisory` = reine Stil-Hinweise (Info, nicht abstrafend).
        "lektor": (lektor or {}).get("auto") if lektor is not None else None,
        "lektor_advisory": (lektor or {}).get("advisory") if lektor is not None else None,
        "secret_red": secret_red,
        "secret_entries": len(secrets.get("entries") or {}),
        "click_articles": len(click_articles),
        "total_clicks": total_clicks,
        "top_article": top_article,
        "awin_total": awin.get("total_commission", 0),
        "awin_paid": awin.get("total_paid", 0),
        "awin_articles": len(awin.get("articles", {})),
        "awin_unmatched": int(_awin_un or 0),
    }


def _readability_lamp(v):
    """Ampel für den Ø-Flesch-Wert (deutsche Amstad-Skala).

    Unbekannt ist NICHT grün – eine fehlende Messung ist ein Befund, kein
    Erfolg (vorher färbte `(v or 100) >= 70` sowohl `None` als auch 0 grün).
    """
    if v is None:
        return "⚪"
    if v >= 60:
        return "🟢"
    if v >= 50:
        return "🟡"
    return "🔴"


def _score(d) -> int:
    """Gesamtscore 0..100."""
    s = 100
    # Content-Gesundheit: ein leerer/dünner Bestand = Problemlage
    if d["live"] < 15:
        s -= 15
    # Freshness blass: viele decay = Frische-Druck
    s -= min(30, d["decay_count"] * 3)
    # CWV rot
    if d["cwv_verdict"] == "RED":
        s -= 15
    elif d["cwv_verdict"] == "AMBER":
        s -= 7
    # Lesbarkeit (wenn bekannt)
    if d["readability"] is not None:
        if d["readability"] < 60:
            s -= 10
        elif d["readability"] < 70:
            s -= 4
    # Lektorat
    if d["lektor"] is not None:
        if d["lektor"] > 60:
            s -= 10
        elif d["lektor"] > 25:
            s -= 4
    # Secrets tot
    s -= min(15, d["secret_red"] * 5)
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
    lines = [
        "# 🏆 Chefredakteur-Scorecard",
        f"**Stand:** {d['date']} · **Auftrag:** Redaktionelle Gesamt-Steuerung",
        "",
        f"## Gesamt-Score: **{score}/100** · Ampel: **{ampel}**",
        "",
        "| Kennzahl | Wert | Ampel |",
        "|---|---|---|",
        f"| Veröffentlichte Artikel | {d['live']} | {'🟢' if d['live'] >= 15 else '🔴'} |",
        f"| Entwürfe (Warteschlange) | {d['drafts']} | 🟡 |",
        f"| Pillars / Themen-Cluster | {d['pillar_count']} | 🟢 |",
        f"| Decay-Kandidaten (STALE+DECAYING) | {d['decay_count']} | "
        f"{'🟢' if d['decay_count'] == 0 else ('🟡' if d['decay_count'] <= 5 else '🔴')} |",
        f"| Core-Web-Vitals | {d['cwv_verdict']} | "
        f"{'🟢' if d['cwv_verdict'] == 'GREEN' else ('🟡' if d['cwv_verdict'] == 'AMBER' else '🔴')} |",
        f"| Ø Lesbarkeit (Flesch) | {'n/a' if d['readability'] is None else d['readability']} | "
        f"{_readability_lamp(d['readability'])} |",
        f"| Lektorat-Befunde (auto-behebbar) | "
        f"{'n/a' if d['lektor'] is None else d['lektor']} | "
        f"{'⚪' if d['lektor'] is None else ('🟢' if d['lektor'] == 0 else '🟡')} |",
        f"| Stil-Hinweise (Lektorat, nur Info) | "
        f"{'n/a' if d.get('lektor_advisory') is None else d['lektor_advisory']} | ℹ️ |",
        f"| Tote Secrets | {d['secret_red']} | "
        f"{'🟢' if d['secret_red'] == 0 else '🔴'} |",
        f"| Affiliate-Klicks (Umsatz-Hebel) | {d['total_clicks']} über "
        f"{d['click_articles']} Artikel | {'🟢' if d['total_clicks'] >= 100 else ('🟡' if d['total_clicks'] > 0 else '🟡')} |",
        f"| Awin-Provision (Klicks→Umsatz) | {d['awin_total']:.2f} € "
        f"({d['awin_paid']:.2f} € bezahlt) über {d['awin_articles']} Artikel | "
        f"{'🟢' if d['awin_total'] > 0 else '🟡'} |",
        "",
        "## Affiliate-Klick-Attribution",
        "",
        _render_clicks(d),
        "",
        "## Awin-Provisions-Import (Monetarisierung)",
        "",
        _render_awin(d),
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
    if d["cwv_verdict"] != "GREEN":
        recs.append("Core-Web-Vitals unter Soll – `scripts/cwv_guard.py` für Befunde; "
                    "Covers als AVIF/WebP, Bilder < 220 KB, `<img>` mit width/height.")
    if d["secret_red"] > 0:
        recs.append("Tote/schwache Secrets – `scripts/secrets_age_guard.py` prüfen "
                    "(Pinterest 30-Tage-Token, Mastodon, KI-Keys).")
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
    if d["drafts"] > 0:
        recs.append(f"**{d['drafts']}** Artikel in der Entwurf-Warteschlange – manuelle "
                    "Qualitätsfreigabe prüfen (Kadenz- bzw. Qualitäts-Gate).")
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
    print(rep)
    if "--issue" in sys.argv and score < 75:
        print("\n===== ISSUE BODY =====\n")
        print(f"## 🏆 Chefredakteur-Scorecard: **{score}/100** ({_ampel(score)})\n\n{rep}")
    return 0 if score >= 75 else 1


if __name__ == "__main__":
    sys.exit(main())
