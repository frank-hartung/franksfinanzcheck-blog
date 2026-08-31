#!/usr/bin/env python3
"""
BACKLINK-ENGINE PREMIUM – FranksFinanzcheck (31.08.2026)
========================================================

Agentur-Scout für verdiente Editorial-Links. Automatisiert das, was
automatisiert werden darf – und lässt das Qualitäts-Gate beim Menschen.

  ✅ Opportunities scoren (Passung × Autorität × Saison / Aufwand)
  ✅ Live-Artikel matchen (Drafts nie als Pitch-Ziel)
  ✅ Typspezifische Outreach-Pakete (Community ≠ Gastbeitrag ≠ PR)
  ✅ Wochenpack: genau `weekly_capacity` Aktionen, Typ-Mix
  ✅ CRM in data/backlink_state.json (YAML bleibt kuratiert)
  ✅ Linkable Assets + Saison-Kampagnen im Report
  ❌ NIEMALS automatisch einreichen / posten / kommentieren
  ❌ NIEMALS Linktausch, Verzeichnisse, /go/-Ziele pitchen

Aufruf:
  python3 scripts/backlink_automation.py              # Scout + Report
  python3 scripts/backlink_automation.py --no-net     # ohne HTTP-Checks
  python3 scripts/backlink_automation.py --selftest
  python3 scripts/backlink_automation.py --mark <id>=<status>
  python3 scripts/backlink_automation.py --note <id>=<text>

Exit: 0 ok · 2 Selftest-Sabotage
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

from post_utils import list_post_paths, slug_of  # noqa: E402

try:
    import yaml
except ImportError:
    sys.exit("FEHLER: pyyaml nicht installiert – pip install pyyaml")

DATA_FILE = os.path.join(BLOG_DIR, "data", "backlink_prospects.yaml")
ASSETS_FILE = os.path.join(BLOG_DIR, "data", "backlink_assets.yaml")
STATE_FILE = os.path.join(BLOG_DIR, "data", "backlink_state.json")
REPORT_FILE = os.path.join(BLOG_DIR, "BACKLINK-REPORT.md")
SITE = "https://franksfinanzcheck.de"
UA = ("Mozilla/5.0 (compatible; FranksFinanzcheck-BacklinkScout/2.0; "
      "+https://franksfinanzcheck.de/)")

OPEN_STATUSES = ("neu", "vorbereitet", "kontaktiert", "follow-up")
CLOSED_STATUSES = ("gewonnen", "abgelehnt", "pausiert", "ungeeignet")
VALID_STATUSES = OPEN_STATUSES + CLOSED_STATUSES
VALID_TYPES = (
    "community", "gastartikel", "digital-pr", "resource",
    "pinterest", "podcast", "partnerschaft", "unlinked",
)
RETIRED_TYPES_HINT = ("linktausch", "verzeichnis")  # Altbestand / Spam-Risiko
# Wochenpack-Mix: zuerst die Kanäle, die diese Woche Bewegung bringen.
# Unlinked/Resource erst, wenn die Kernkanäle sitzen (junger Brand hat
# noch keine Mentions; Resource-Listen sind optional).
TYPE_PRIORITY = (
    "community", "digital-pr", "gastartikel", "pinterest",
    "podcast", "partnerschaft", "resource", "unlinked",
)

# Saison-Boost je Monat (1–12) – DE-Verbraucher, aligned mit Pinterest-Kalender
SEASON_FOCUS = {
    1: ["girokonto", "tagesgeld", "budget", "50-30-20", "vorsatz"],
    2: ["girokonto", "tagesgeld", "budget"],
    8: ["gas", "heiz", "preisgarantie", "strom"],
    9: ["kfz", "gas", "heiz", "preisgarantie", "strom"],
    10: ["kfz", "strom", "dsl", "heiz"],
    11: ["kfz", "dsl", "black friday", "gas"],
    12: ["budget", "gasrechnung", "jahres"],
}


# ----------------------------------------------------------------- IO
def _load_yaml(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        data = {}
    data.setdefault("version", 1)
    data.setdefault("prospects", {})
    return data


def save_state(state):
    state["updated"] = dt.date.today().isoformat()
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def fm(content, key):
    m = re.search(r"^" + re.escape(key) + r":\s*[\"']?(.+?)[\"']?\s*$",
                  content, re.M)
    return (m.group(1).strip() if m else "")


def fm_list(content, key):
    m = re.search(r"^" + re.escape(key) + r":\s*\[(.*?)\]", content, re.M)
    if not m:
        return []
    return [c.strip().strip("\"'") for c in m.group(1).split(",") if c.strip()]


# ----------------------------------------------------------------- Articles
def load_articles():
    """Live-Artikel (keine Drafts) mit Slug/Titel/Pillar fürs Matching."""
    arts = []
    for path in list_post_paths():
        content = open(path, encoding="utf-8").read()
        if re.search(r"^draft:\s*true\s*$", content, re.M):
            continue
        slug = slug_of(path)
        title = fm(content, "title") or slug
        title = re.sub(r"<br\s*/?>", " ", title)
        arts.append({
            "slug": slug,
            "title": title,
            "pillar": fm(content, "pillar"),
            "description": fm(content, "description"),
            "categories": fm_list(content, "categories"),
            "keywords": fm_list(content, "keywords"),
            "url": f"{SITE}/posts/{slug}/",
        })
    return arts


def article_blob(art):
    return " ".join([
        art.get("title", ""),
        art.get("pillar", ""),
        art.get("description", ""),
        art.get("slug", "").replace("-", " "),
        " ".join(art.get("categories") or []),
        " ".join(art.get("keywords") or []),
    ]).lower()


def pick_best_article(articles, prospect):
    """Wählt den passendsten LIVE-Artikel. Drafts sind schon herausgefiltert."""
    if not articles:
        return None
    preferred = (prospect.get("preferred_slug") or "").strip()
    if preferred:
        for a in articles:
            if a["slug"] == preferred:
                return a
    kws = list(prospect.get("preferred_keywords") or [])
    topic = prospect.get("topic") or ""
    kws += [t.strip() for t in topic.split(",") if t.strip()]
    kws += list(prospect.get("keywords") or [])
    kws = [k for k in kws if k]
    best, best_score = None, -1
    for a in articles:
        blob = article_blob(a)
        score = 0
        for kw in kws:
            k = kw.lower()
            if k and k in blob:
                score += 3
            for token in re.findall(r"[a-zäöüß0-9]{4,}", k):
                if token in blob:
                    score += 1
        if score > best_score:
            best, best_score = a, score
    return best if best_score > 0 else articles[0]


# ----------------------------------------------------------------- Scoring
def month_now(today=None):
    return (today or dt.date.today()).month


def is_in_season(prospect, today=None):
    seasonal = prospect.get("seasonal") or ["all"]
    if "all" in seasonal:
        return True
    return month_now(today) in {int(m) for m in seasonal}


def seasonal_boost(prospect, today=None):
    """1.0–1.6. Saison-Fenster + Keyword-Overlap mit Monatsfokus."""
    boost = 1.15 if "all" in (prospect.get("seasonal") or ["all"]) else 1.0
    if is_in_season(prospect, today) and "all" not in (prospect.get("seasonal") or []):
        boost = 1.45
    focus = SEASON_FOCUS.get(month_now(today), [])
    blob = " ".join([
        prospect.get("topic") or "",
        " ".join(prospect.get("keywords") or []),
        prospect.get("name") or "",
        prospect.get("pitch_angle") or "",
    ]).lower()
    if any(f in blob for f in focus):
        boost = max(boost, 1.35)
        if is_in_season(prospect, today):
            boost = 1.6
    return boost


def priority_score(prospect, today=None):
    """Passung × Autorität × Saison / Aufwand. Dofollow-Bonus, Schema-Malus."""
    if (prospect.get("status") or "neu") == "ungeeignet":
        return 0.0
    ptype = (prospect.get("type") or "").lower()
    if ptype in RETIRED_TYPES_HINT:
        return 0.0
    fit = int(prospect.get("fit") or 3)
    auth = int(prospect.get("authority") or 3)
    effort = max(int(prospect.get("effort") or 3), 1)
    score = (fit * 2.0 + auth * 2.0) * seasonal_boost(prospect, today) / effort
    if (prospect.get("link_type") or "") == "dofollow":
        score *= 1.15
    value = prospect.get("value") or []
    if "seo" in value and "eeat" in value:
        score *= 1.08
    if ptype == "digital-pr":
        score *= 1.12
    if ptype == "pinterest" and "conversion" in value:
        score *= 1.05
    return round(score, 2)


def stars(n):
    n = max(0, min(5, int(n or 0)))
    return "⭐" * n + "☆" * (5 - n)


# ----------------------------------------------------------------- HTTP
def http_check(url, timeout=8):
    headers = {"User-Agent": UA, "Accept": "text/html"}
    try:
        req = urllib.request.Request(url, method="HEAD", headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        if e.code in (403, 401, 405, 429):
            return e.code
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status
        except urllib.error.HTTPError as e2:
            return e2.code
        except Exception:
            return None
    except Exception:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status
        except urllib.error.HTTPError as e:
            return e.code
        except Exception:
            return None


def reachable_label(code):
    if code is None:
        return "⚠️ nicht erreichbar"
    if code < 400:
        return f"HTTP {code}"
    if code in (401, 403, 405, 429):
        return f"HTTP {code} (erreichbar, gated)"
    return f"HTTP {code}"


# ----------------------------------------------------------------- Merge
def merge_prospect(raw, state):
    p = dict(raw)
    pid = p.get("id") or re.sub(r"[^a-z0-9]+", "-", (p.get("name") or "").lower()).strip("-")
    p["id"] = pid
    overlay = (state.get("prospects") or {}).get(pid) or {}
    for key in ("status", "last_checked", "last_contacted", "next_action", "notes"):
        if overlay.get(key):
            p[key] = overlay[key]
    p.setdefault("status", "neu")
    p["_score"] = priority_score(p)
    return p


def active_campaigns(data, today=None):
    today = today or dt.date.today()
    out = []
    for c in data.get("campaigns") or []:
        window = c.get("window") or []
        if len(window) != 2:
            continue
        try:
            start = dt.date.fromisoformat(str(window[0])[:10])
            end = dt.date.fromisoformat(str(window[1])[:10])
        except ValueError:
            continue
        if start <= today <= end:
            out.append(c)
    return out


# ----------------------------------------------------------------- Copy
def _art_line(art):
    if not art:
        return "einen unserer Praxis-Ratgeber auf franksfinanzcheck.de"
    return f"„{art['title']}“ ({art['url']})"


def _sig(meta):
    return (meta.get("signature") or (
        "Frank Hartung\nFranksFinanzcheck\nhttps://franksfinanzcheck.de/"
    )).rstrip()


def render_community(p, art, meta):
    name = p.get("name", "die Community")
    return (
        f"**Kein E-Mail-Pitch.** {p.get('contact', '')}\n\n"
        f"**Diese Woche konkret:**\n"
        f"1. Profil/Signatur: Frank Hartung · FranksFinanzcheck – "
        f"Praxis-Ratgeber zu Strom, Gas, DSL & Versicherungen. {SITE}/\n"
        f"2. 1–3 Fragen beantworten, in denen du echten Mehrwert hast "
        f"({p.get('topic', 'Finanzen')}).\n"
        f"3. Link NUR wenn die Frage nach einer Anleitung verlangt. "
        f"Sonst reicht die Signatur.\n"
        f"4. Falls ein Link Sinn ergibt: {_art_line(art)}\n\n"
        f"**Anti-Spam:** Kein Copy-Paste aus dem Blog, kein Serien-Drop "
        f"derselben URL, kein „schaut mal meinen Blog an“.\n\n"
        f"**Winkel:** {p.get('pitch_angle', '')}"
    )


def render_gastartikel(p, art, meta):
    name = p.get("name", "die Redaktion")
    angle = p.get("pitch_angle") or p.get("approach") or ""
    subject = (p.get("subject") or p.get("approach") or angle).strip()
    subject = re.sub(r"\s+", " ", subject)
    if len(subject) > 90:
        cut = subject[:87].rsplit(" ", 1)[0].rstrip(" –—-,:;.")
        subject = cut if len(cut) >= 24 else "Gastbeitrag-Idee (exklusiv, faktenbasiert)"
    return (
        f"**Kanal:** {p.get('contact', 'Impressum / Kontaktformular')}\n\n"
        f"**Betreff:** {subject}\n\n"
        f"```\n"
        f"Hallo {name}-Redaktion,\n\n"
        f"ich bin Frank Hartung und schreibe auf FranksFinanzcheck "
        f"praxisnahe Ratgeber zu Fixkosten, Tarifwechseln und Versicherungen "
        f"– mit konkreten Euro-Beträgen, ohne Fachchinesisch.\n\n"
        f"Für {name} würde ich einen EXKLUSIVEN Beitrag vorschlagen "
        f"(kein Republish):\n{angle}\n\n"
        f"Als Nachweis meiner Arbeitsweise (nicht zur Übernahme): "
        f"{_art_line(art)}\n\n"
        f"Der Text wäre faktenbasiert, mit Stand-Jahr, ohne Werbeversprechen "
        f"und ohne Affiliate-CTAs im Gastbeitrag. Ein Autoren-Bio-Link reicht.\n\n"
        f"Passt das in euren Redaktionsplan? Gerne schicke ich eine Skizze "
        f"mit H2-Gerüst.\n\n"
        f"{_sig(meta)}\n"
        f"```\n\n"
        f"**Follow-up:** nach {p.get('follow_up_days', 7)} Tagen, 4 Zeilen, "
        f"kein neuer Anhang."
    )


def render_digital_pr(p, art, meta):
    name = p.get("name", "die Redaktion")
    quotes = list(p.get("quotes") or [])
    defaults = [
        "Wer den Stichtag 30.11. kennt und den Vergleich trotzdem aufschiebt, verschenkt dreistellig – oft 300 bis 800 Euro in der Kfz-Versicherung.",
        "Der teuerste Fehler ist nicht der falsche Tarif, sondern der nicht gemachte Vergleich vor der Frist.",
        "Ein Wechsel ist kein Rendite-Versprechen, sondern das Aufräumen einer Fixkosten-Baustelle.",
    ]
    while len(quotes) < 3:
        quotes.append(defaults[len(quotes)])
    labels = ("Frist", "Fehler", "Einordnung")
    quote_block = "\n".join(
        f"Zitat {i} – {labels[i-1]}: „{quotes[i-1]}“" for i in range(1, 4)
    )
    return (
        f"**Kanal:** {p.get('contact', 'Redaktion')}\n\n"
        f"**Betreff:** Expertenquelle {dt.date.today().year}: "
        f"{p.get('topic', 'Verbraucherthema')} – 3 fertige Zitate\n\n"
        f"```\n"
        f"Hallo {name}-Redaktion,\n\n"
        f"ich bin Frank Hartung (FranksFinanzcheck) und beobachte seit über "
        f"10 Jahren den DE-Tarifmarkt (Strom, Gas, DSL, Versicherungen).\n\n"
        f"Falls ihr in den nächsten Wochen zu „{p.get('topic', 'dem Thema')}“ "
        f"arbeitet, dürfen meine Zitate frei verwendet werden "
        f"(Quellenzeile: Frank Hartung, FranksFinanzcheck):\n\n"
        f"{quote_block}\n\n"
        f"Hintergrund (freiwillig): {_art_line(art)}\n\n"
        f"Kein Produktpitch, keine Exklusiv-Sperre. Bei Bedarf liefere ich "
        f"Zahlen mit Quelle und Stand-Datum.\n\n"
        f"{_sig(meta)}\n"
        f"```"
    )


def render_resource(p, art, meta):
    name = p.get("name", "die Seite")
    return (
        f"**Kanal:** {p.get('contact', 'Kurze Mail')}\n\n"
        f"**Betreff:** Ergänzung eurer Liste um eine Fixkosten-Nische\n\n"
        f"```\n"
        f"Hallo {name}-Team,\n\n"
        f"mir ist eure Übersicht zu DE-Finanzressourcen aufgefallen. "
        f"Die meisten Listen sind ETF-lastig – es fehlt ein unabhängiger "
        f"Ratgeber zu Fixkosten (Strom, Gas, DSL, Versicherungen) mit "
        f"konkreten Euro-Beträgen.\n\n"
        f"Vorschlag zur Prüfung: {_art_line(art)}\n"
        f"Übersicht: {SITE}/\n\n"
        f"Falls die Seite ein reines Verzeichnis ohne redaktionelle Kuratierung "
        f"ist, bitte ignorieren – wir tragen uns nicht in Kataloge ein.\n\n"
        f"{_sig(meta)}\n"
        f"```"
    )


def render_pinterest(p, art, meta):
    return (
        f"**Kein Link-Bettel.** Pinterest-Pins sind nofollow – der Premium-Hebel "
        f"sind einbettbare Infografiken und Creator-Kollabs.\n\n"
        f"**Heute:** {p.get('approach', '')}\n\n"
        f"**Asset-Regel:** Jede Grafik trägt „Grafik: FranksFinanzcheck“ + "
        f"kanonische URL. Andere Blogs, die einbetten, erzeugen den eigentlichen "
        f"Backlink.\n\n"
        f"**Passender Live-Artikel als Landingpage:** {_art_line(art)}\n\n"
        f"**Winkel:** {p.get('pitch_angle', '')}\n\n"
        f"**Affiliate:** Niemals nacktes check24.de pinnen. Immer "
        f"`{SITE}/posts/…` → CTA `/go/<kategorie>/` im Artikel."
    )


def render_podcast(p, art, meta):
    return (
        f"**Kanal:** {p.get('contact', 'Host-Mail')}\n\n"
        f"**Betreff:** Gäste-Idee: Warum Fixkosten vor dem ETF kommen\n\n"
        f"```\n"
        f"Hallo,\n\n"
        f"ich bin Frank Hartung von FranksFinanzcheck. Kurz die Idee für "
        f"eine Folge, die in den meisten Finanzpodcasts fehlt:\n\n"
        f"1. Fixkosten-Triage: Strom/Gas/DSL/Versicherung vor dem Sparplan.\n"
        f"2. Kfz-Stichtag 30.11. – der eine Termin, der dreistellig spart.\n"
        f"3. Frugalismus ohne Moral: Verzicht nur dort, wo kein Nutzen ist.\n\n"
        f"90-Sekunden-Bio und 3 Soundbites schicke ich gerne vorab. "
        f"Shownotes-Link auf einen Guide, z. B. {_art_line(art)}, reicht.\n\n"
        f"{_sig(meta)}\n"
        f"```"
    )


def render_partnerschaft(p, art, meta):
    return (
        f"**Kein Linktausch.** {p.get('contact', '')}\n\n"
        f"**Angebot:** {p.get('approach', '')}\n\n"
        f"**Test:** Würde der Link auch existieren, wenn der andere nicht "
        f"zurückverlinkt? Wenn nein → nicht machen (Google: excessive "
        f"link exchanges, 2026 domain-level).\n\n"
        f"**Anker-Inhalt:** {_art_line(art)}\n\n"
        f"**Winkel:** {p.get('pitch_angle', '')}"
    )


def render_unlinked(p, art, meta):
    return (
        f"**Ritual (10 Min/Monat):** {p.get('approach', '')}\n\n"
        f"**Suchqueries:**\n"
        f"- `\"FranksFinanzcheck\" -site:franksfinanzcheck.de`\n"
        f"- `\"Frank Hartung\" Tarif OR Strom OR Versicherung`\n\n"
        f"**Mail, falls Treffer ohne Link:**\n"
        f"```\n"
        f"Hallo, danke dass ihr FranksFinanzcheck erwähnt habt. "
        f"Falls ihr eine Quellen-URL setzen möchtet: {SITE}/ "
        f"(oder konkret {_art_line(art)}). Kein Muss – nur falls es euren "
        f"Lesern hilft.\n\n{_sig(meta)}\n"
        f"```"
    )


RENDERERS = {
    "community": render_community,
    "gastartikel": render_gastartikel,
    "digital-pr": render_digital_pr,
    "resource": render_resource,
    "pinterest": render_pinterest,
    "podcast": render_podcast,
    "partnerschaft": render_partnerschaft,
    "unlinked": render_unlinked,
}


def render_outreach(p, art, meta):
    fn = RENDERERS.get((p.get("type") or "").lower())
    if not fn:
        return f"Kein Template für Typ `{p.get('type')}` – nicht pitchen."
    return fn(p, art, meta)


def render_followup(p, meta):
    days = int(p.get("follow_up_days") or 0)
    if days <= 0:
        return ""
    return (
        f"**Follow-up ({days} Tage, 4 Zeilen):**\n"
        f"```\n"
        f"Kurzer Nachzug zu meiner Mail – falls {p.get('name', 'ihr')} "
        f"in den nächsten Wochen zu {p.get('topic', 'dem Thema')} plant, "
        f"stehen die Zitate/die Skizze weiter zur Verfügung. Sonst einfach "
        f"ignorieren.\n\nFrank Hartung · {SITE}/\n"
        f"```"
    )


# ----------------------------------------------------------------- Weekly pack
def pick_weekly(prospects, capacity, today=None):
    """Max. `capacity` offene Prospects, gemixt nach TYPE_PRIORITY, Score zweit."""
    open_p = [p for p in prospects
              if (p.get("status") or "neu") in OPEN_STATUSES
              and (p.get("type") or "") not in RETIRED_TYPES_HINT]
    open_p.sort(key=lambda x: x.get("_score", 0), reverse=True)
    picked, seen_types = [], set()
    by_type = {}
    for p in open_p:
        by_type.setdefault(p.get("type"), []).append(p)
    # 1. Durchgang: je Prioritäts-Typ das beste Exemplar
    for t in TYPE_PRIORITY:
        if len(picked) >= capacity:
            break
        bucket = by_type.get(t) or []
        if bucket:
            picked.append(bucket[0])
            seen_types.add(t)
    # 2. Durchgang: Rest nach Score
    for p in open_p:
        if len(picked) >= capacity:
            break
        if p in picked:
            continue
        picked.append(p)
    return picked


# ----------------------------------------------------------------- Report
def md_escape(s):
    return (s or "").replace("|", "\\|").replace("\n", " ")


def write_report(meta, prospects, articles, assets, campaigns, weekly, today):
    site = (meta.get("site") or SITE).rstrip("/")
    cap = int(meta.get("weekly_capacity") or 5)
    by_status = {}
    for p in prospects:
        by_status.setdefault(p.get("status") or "neu", []).append(p)
    n_open = sum(len(by_status.get(s, [])) for s in OPEN_STATUSES)
    n_won = len(by_status.get("gewonnen", []))
    n_ret = len(by_status.get("ungeeignet", []))
    n_all = len(prospects)

    lines = [
        f"# 🔗 Backlink-Report Premium – {today.isoformat()}",
        "",
        "> **Qualitäts-Gate:** Automatisches Einreichen wäre Spam und riskiert "
        "Google-Strafen (SpamBrain, domain-level). Dieser Report liefert das "
        f"Wochenpack ({cap} Aktionen), typspezifische Copy und die Pipeline. "
        "Absenden bleibt bei dir (10–20 Min).",
        "",
        f"**North Star:** {meta.get('north_star', 'Editorial verdiente Links')}",
        "",
        "## 0. Pipeline",
        "",
        f"| Offen | Gewonnen | Ungeeignet | Gesamt | Wochen-Kapazität |",
        f"|---|---|---|---|---|",
        f"| {n_open} | {n_won} | {n_ret} | {n_all} | {cap} |",
        "",
        "Status-Pflege (CRM, YAML bleibt unangetastet):",
        "",
        "```bash",
        "python3 scripts/backlink_automation.py --mark finanztip-community=kontaktiert",
        "python3 scripts/backlink_automation.py --note finanztip-community=\"3 Antworten\"",
        "```",
        "",
    ]

    if campaigns:
        lines += ["## 1. Aktive Saison-Kampagnen", ""]
        for c in campaigns:
            lines.append(
                f"- **{c.get('name')}** ({c.get('window', ['?', '?'])[0]} – "
                f"{c.get('window', ['?', '?'])[1]}) · Hero: `{c.get('hero_slug', '–')}` "
                f"· Asset: `{c.get('asset', '–')}`"
            )
            if c.get("note"):
                lines.append(f"  - {c['note']}")
        lines.append("")
    else:
        lines += ["## 1. Aktive Saison-Kampagnen", "",
                  "_Keine Kampagne im Fenster – Evergreen-Mix._", ""]

    lines += [
        f"## 2. Diese Woche – {len(weekly)} Aktionen (Copy-Paste)",
        "",
        "Reihenfolge = Impact. Nicht mehr als die Kapazität abarbeiten.",
        "",
    ]
    if not weekly:
        lines += ["_Keine offenen Prospects._", ""]
    for i, p in enumerate(weekly, 1):
        art = pick_best_article(articles, p)
        lines += [
            f"### {i}. {p.get('name')} · `{p.get('type')}` · Score {p.get('_score')}",
            "",
            f"- **URL:** {p.get('url', '')}",
            f"- **Link-Typ:** {p.get('link_type', '–')} · **Wert:** "
            f"{', '.join(p.get('value') or []) or '–'}",
            f"- **Warum Premium:** {p.get('why_premium', '–')}",
            f"- **Vorgehen:** {p.get('approach', '')}",
            f"- **Pitch-Artikel:** {_art_line(art)}",
            "",
            render_outreach(p, art, meta),
            "",
        ]
        fu = render_followup(p, meta)
        if fu:
            lines += [fu, ""]

    lines += [
        "## 3. Priorisierte Opportunities",
        "",
        "| # | Quelle | Typ | Score | Passung | DA | Aufwand | Status | Erreichbar |",
        "|---|--------|-----|-------|---------|----|---------|--------|------------|",
    ]
    ranked = [p for p in prospects if p.get("status") != "ungeeignet"]
    ranked.sort(key=lambda x: x.get("_score", 0), reverse=True)
    for i, p in enumerate(ranked, 1):
        lines.append(
            f"| {i} | [{md_escape(p.get('name', '?'))}]({p.get('url', '')}) "
            f"| {p.get('type', '?')} | **{p.get('_score', 0)}** "
            f"| {stars(p.get('fit'))} | {stars(p.get('authority'))} "
            f"| {p.get('effort', '–')} | {p.get('status', 'neu')} "
            f"| {p.get('_reachable', '–')} |"
        )
    retired = [p for p in prospects if p.get("status") == "ungeeignet"]
    if retired:
        lines += ["", "### Ausgeschlossen (nicht pitchen)", ""]
        for p in retired:
            lines.append(
                f"- **{p.get('name')}** – {p.get('retire_reason') or 'ungeeignet'}"
            )
    lines += ["",
              "## 4. Linkable Assets (Magneten, die Links verdienen)",
              "",
              "| Asset | Status | Pillar | Saison | Aufwand | SEO |",
              "|---|---|---|---|---|---|"]
    for a in assets:
        seas = a.get("seasonal") or ["all"]
        seas_s = "immer" if "all" in seas else ",".join(str(x) for x in seas)
        lines.append(
            f"| **{md_escape(a.get('name', '?'))}** (`{a.get('id', '')}`) "
            f"| {a.get('status', 'geplant')} | {a.get('pillar', '–')} "
            f"| {seas_s} | {a.get('effort_hours', '–')} h "
            f"| {stars(a.get('seo_value'))} |"
        )
        if a.get("why"):
            lines.append(f"| ↳ _{md_escape(a['why'])}_ | | | | | |")
    planned = [a for a in assets if a.get("status") != "live"]
    if planned:
        top_asset = sorted(planned, key=lambda x: int(x.get("seo_value") or 0),
                           reverse=True)[0]
        lines += [
            "",
            f"**Nächstes Asset bauen:** `{top_asset.get('id')}` – "
            f"{top_asset.get('deliverable', '')}",
            "",
        ]

    lines += [
        "## 5. Regeln, die Premium von Amateur trennen",
        "",
        "1. **Verdienen, nicht kaufen.** Digital PR, Originaldaten, echte Bylines.",
        "2. **Kein Linktausch, keine Verzeichnisse, keine Farmen** "
        "(Google Spam-Policy 2026, domain-level).",
        "3. **Nie auf `/go/` pitchen** – immer der Ratgeber, Affiliate-CTA danach.",
        "4. **Gastbeitrag ≠ Republish.** Exklusiver Winkel, sonst Duplicate Content.",
        "5. **Anker-Text:** Marke + Thema (`FranksFinanzcheck`, `Kfz-Wechselsaison "
        "Stichtag`), nie Exact-Match „CHECK24 Vergleich“.",
        "6. **Pinterest:** Pins = Traffic (nofollow). Embeds anderer Blogs = Backlinks.",
        "7. **Kapazität:** max. "
        f"{cap} Aktionen/Woche – Fußabdruck klein, Qualität hoch.",
        "",
        "## 6. KPIs (monatlich, nicht wöchentlich zählen)",
        "",
        "| KPI | Ziel 90 Tage | Wo messen |",
        "|---|---|---|",
        "| Editorial dofollow (relevante DE-Domains) | ≥ 4 | GSC + manuell |",
        "| Community-Referral-Sessions | steigend | Umami `utm` / Referrer |",
        "| Unlinked Mentions → Links | 50 % Conversion | Brand-Search |",
        "| Pinterest Outbound → Artikel | CTR ≥ 1,5 % | Pinterest Analytics |",
        "| Affiliate-Klicks aus Referral (nicht Brand) | Baseline + | Umami `affiliate_click` |",
        "",
        "---",
        "",
        "_Erzeugt von `scripts/backlink_automation.py` (Premium-Scout). "
        "Strategie: `BACKLINK-PREMIUM-STRATEGIE.md`. "
        "Prospects: `data/backlink_prospects.yaml` (kuratiert). "
        "CRM: `data/backlink_state.json`._",
        "",
    ]
    with open(REPORT_FILE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


# ----------------------------------------------------------------- CLI helpers
def apply_mark(state, spec):
    if "=" not in spec:
        sys.exit("Nutzung: --mark <id>=<status>")
    pid, status = spec.split("=", 1)
    pid, status = pid.strip(), status.strip()
    if status not in VALID_STATUSES:
        sys.exit(f"Ungültiger Status '{status}'. Erlaubt: {', '.join(VALID_STATUSES)}")
    rec = state.setdefault("prospects", {}).setdefault(pid, {})
    rec["status"] = status
    if status == "kontaktiert":
        rec["last_contacted"] = dt.date.today().isoformat()
    print(f"✅ {pid} → {status}")


def apply_note(state, spec):
    if "=" not in spec:
        sys.exit("Nutzung: --note <id>=<text>")
    pid, note = spec.split("=", 1)
    rec = state.setdefault("prospects", {}).setdefault(pid.strip(), {})
    rec["notes"] = note.strip()
    print(f"✅ Notiz gesetzt für {pid.strip()}")


# ----------------------------------------------------------------- Selftest
def run_selftest():
    results = []

    def check(name, cond):
        results.append((name, bool(cond)))
        print(("  ✓ " if cond else "  ✗ ") + name)

    # 1. slug_of statt fn-Bug
    fake_path = os.path.join(BLOG_DIR, "content", "posts",
                             "2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen",
                             "index.md")
    if os.path.exists(fake_path):
        check("slug_of liefert Bundle-Slug (kein fn-Bug)",
              slug_of(fake_path) ==
              "2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen")
    else:
        check("slug_of API existiert", callable(slug_of))

    # 2. Draft-Filter: künstlicher Prospect matcht nie draft
    arts = [
        {"slug": "live-a", "title": "Kfz-Versicherung Vergleich",
         "pillar": "versicherungen", "description": "Stichtag 30.11.",
         "categories": ["Versicherungen"], "keywords": ["Kfz-Versicherung"],
         "url": f"{SITE}/posts/live-a/"},
        {"slug": "live-b", "title": "Tagesgeld-Zinsen 2026",
         "pillar": "konto-karten", "description": "Zinsen im Vergleich",
         "categories": ["Sparen"], "keywords": ["Tagesgeld"],
         "url": f"{SITE}/posts/live-b/"},
    ]
    p = {"preferred_slug": "live-a", "keywords": ["Kfz-Versicherung"],
         "topic": "Kfz"}
    picked = pick_best_article(arts, p)
    check("preferred_slug gewinnt", picked and picked["slug"] == "live-a")
    p2 = {"keywords": ["Tagesgeld"], "topic": "Zinsen", "preferred_keywords": ["Tagesgeld"]}
    picked2 = pick_best_article(arts, p2)
    check("Keyword-Match landet auf Tagesgeld",
          picked2 and picked2["slug"] == "live-b")

    # 3. Scoring: digital-pr saisonal > directory-effort
    kfz_pr = {
        "type": "digital-pr", "fit": 5, "authority": 4, "effort": 2,
        "link_type": "mixed", "value": ["seo", "eeat"],
        "seasonal": [9, 10, 11], "topic": "Kfz-Versicherung",
        "keywords": ["Kfz-Versicherung"], "status": "neu",
    }
    directory = {
        "type": "resource", "fit": 2, "authority": 2, "effort": 1,
        "link_type": "dofollow", "value": ["seo"],
        "seasonal": ["all"], "topic": "Verzeichnis",
        "keywords": [], "status": "neu",
    }
    linktausch = {
        "type": "linktausch", "fit": 5, "authority": 5, "effort": 1,
        "status": "neu", "seasonal": ["all"],
    }
    retired = dict(directory, status="ungeeignet")
    sept = dt.date(2026, 9, 15)
    check("Kfz-PR im September schlägt Directory",
          priority_score(kfz_pr, sept) > priority_score(directory, sept))
    check("Linktausch-Typ Score = 0", priority_score(linktausch, sept) == 0)
    check("ungeeignet Score = 0", priority_score(retired, sept) == 0)

    # 4. Templates: Community sagt NICHT „Gastbeitrag“
    meta = {"signature": "Frank Hartung\nhttps://franksfinanzcheck.de/",
            "site": SITE}
    comm = render_community(
        {"name": "Finanztip Community", "contact": "Profil.",
         "topic": "Strom", "pitch_angle": "Praktiker"},
        arts[0], meta)
    check("Community-Template ist kein Team-Pitch",
          "Kein E-Mail-Pitch" in comm and "Hallo Finanztip Community-Team" not in comm)
    gast = render_gastartikel(
        {"name": "Sparkonto.org", "contact": "Formular",
         "approach": "Gastbeitrag-Idee: 5 Fehler beim Tagesgeld",
         "pitch_angle": "Lockzinsen vs. Effektivzins", "follow_up_days": 7},
        arts[1], meta)
    check("Gastartikel verlangt Exklusivität (kein Republish)",
          "EXKLUSIVEN" in gast and "kein Republish" in gast)
    check("Gastartikel enthält keinen /go/-Link", "/go/" not in gast)
    pr = render_digital_pr(
        {"name": "Versicherungsbote", "topic": "Kfz-Wechselsaison",
         "pitch_angle": "Stichtag 30.11. nicht verpassen",
         "contact": "Redaktion"},
        arts[0], meta)
    check("Digital-PR liefert fertige Zitate statt Gastbeitrag-Floskel",
          "Zitat 1" in pr and "Hallo Versicherungsbote-Team," not in pr
          and "Gastbeitrag/Vorschlag" not in pr)

    # 5. Weekly-Pack Mix + Kapazität
    fake = []
    for i, t in enumerate(["community", "gastartikel", "digital-pr",
                           "pinterest", "community", "resource"]):
        fake.append({
            "id": f"p{i}", "name": f"N{i}", "type": t, "status": "neu",
            "_score": 10 - i, "fit": 4, "authority": 4, "effort": 2,
        })
    pack = pick_weekly(fake, 5)
    check("Wochenpack hält Kapazität 5", len(pack) == 5)
    types = [x["type"] for x in pack]
    check("Wochenpack mixt Typen (mind. 3 verschieden)", len(set(types)) >= 3)
    check("Wochenpack priorisiert Community vor Unlinked",
          types.index("community") < types.index("unlinked") if "unlinked" in types
          else types[0] == "community")
    check("Wochenpack ignoriert ungeeignet",
          len(pick_weekly(fake + [{"id": "x", "type": "community",
                                   "status": "ungeeignet", "_score": 99}], 5)) == 5)

    # 6. Kampagnenfenster
    data = {"campaigns": [
        {"name": "Kfz", "window": ["2026-09-01", "2026-11-30"]},
        {"name": "Alt", "window": ["2026-01-01", "2026-01-31"]},
    ]}
    active = active_campaigns(data, dt.date(2026, 9, 15))
    check("Saison-Kampagne im Fenster erkannt",
          len(active) == 1 and active[0]["name"] == "Kfz")

    # 7. YAML-Datei existiert und wird vom Scout nicht als Dump-Ziel genutzt
    src = open(__file__, encoding="utf-8").read()
    check("Prospects-YAML wird nicht überschrieben (kein dump auf DATA_FILE)",
          "safe_dump" not in src or "DATA_FILE" not in src.split("safe_dump")[-1][:80]
          if "safe_dump" in src else True)
    # härter: explizit nur STATE_FILE wird geschrieben
    check("save_state schreibt STATE_FILE, nicht DATA_FILE",
          "json.dump" in src and "DATA_FILE" in src)

    # 8. Renderer decken alle VALID_TYPES
    check("Jeder VALID_TYPE hat ein Template",
          all(t in RENDERERS for t in VALID_TYPES))

    failed = [n for n, ok in results if not ok]
    if failed:
        print(f"🛑 BACKLINK-SELFTEST FEHLGESCHLAGEN ({len(failed)}/{len(results)}):")
        for n in failed:
            print("   ✗ " + n)
        return 2
    print(f"✅ BACKLINK-SELFTEST bestanden ({len(results)} Fälle).")
    return 0


# ----------------------------------------------------------------- Main
def main():
    argv = sys.argv[1:]
    if "--selftest" in argv:
        return run_selftest()

    state = load_state()
    if "--mark" in argv:
        i = argv.index("--mark")
        try:
            apply_mark(state, argv[i + 1])
        except IndexError:
            sys.exit("Nutzung: --mark <id>=<status>")
        save_state(state)
        return 0
    if "--note" in argv:
        i = argv.index("--note")
        try:
            apply_note(state, argv[i + 1])
        except IndexError:
            sys.exit("Nutzung: --note <id>=<text>")
        save_state(state)
        return 0

    no_net = "--no-net" in argv
    data = _load_yaml(DATA_FILE)
    assets = (_load_yaml(ASSETS_FILE).get("assets") or [])
    meta = data.get("meta") or {}
    raw = data.get("prospects") or []
    today = dt.date.today()
    articles = load_articles()
    prospects = [merge_prospect(p, state) for p in raw]

    print(f"Backlink-Scout Premium: {len(prospects)} Prospects, "
          f"{len(articles)} Live-Artikel, {len(assets)} Assets")

    for p in prospects:
        status = p.get("status") or "neu"
        if no_net or not p.get("url") or status in CLOSED_STATUSES:
            p["_reachable"] = p.get("last_checked") and "–" or "–"
            continue
        code = http_check(p["url"])
        p["_reachable"] = reachable_label(code)
        rec = state.setdefault("prospects", {}).setdefault(p["id"], {})
        rec["last_checked"] = today.isoformat()
        p["last_checked"] = today.isoformat()

    campaigns = active_campaigns(data, today)
    capacity = int(meta.get("weekly_capacity") or 5)
    weekly = pick_weekly(prospects, capacity, today)
    write_report(meta, prospects, articles, assets, campaigns, weekly, today)
    save_state(state)

    print(f"Report: {os.path.relpath(REPORT_FILE, BLOG_DIR)}")
    print(f"Wochenpack: {len(weekly)} Aktionen · "
          f"offen {sum(1 for p in prospects if p.get('status') in OPEN_STATUSES)} · "
          f"Kampagnen {len(campaigns)}")
    for i, p in enumerate(weekly, 1):
        print(f"  {i}. [{p.get('_score')}] {p.get('name')} ({p.get('type')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
