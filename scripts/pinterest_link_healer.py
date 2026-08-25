#!/usr/bin/env python3
"""
Pinterest-Link-Healer (Premium)
===============================

Zweck
-----
Jeder Pin muss auf die *richtige* Zielseite im eigenen Blog zeigen –
nicht auf das Pinterest-Profil (Sackgasse, kein Traffic, kein Umsatz)
und nicht direkt auf CHECK24 (Pinterest stuft direkte Affiliate-Ziele
als Spam-Signal ein; ausserdem verschenkt man den SEO-Wert der eigenen
Domain).

Premium-Regel (Agentur-Standard):
    Pin  ->  eigener Blogartikel  ->  Affiliate-CTA (CHECK24)

Das Skript
  1. liest alle veröffentlichten Artikel aus content/posts/ (+ Pillar-Seiten),
  2. matcht jeden Pin aus data/pinterest_plan.yaml per Keyword-/Titel-Scoring
     auf den besten Artikel (Fallback: thematische Pillar-Seite),
  3. schreibt das Ziel in das Feld `blog_url` (und korrigiert `url`),
  4. erzeugt PINTEREST-LINK-REPORT.md mit Score, Quelle und Restrisiken.

Aufrufe:
    python3 scripts/pinterest_link_healer.py            # Dry-Run (nur Report)
    python3 scripts/pinterest_link_healer.py --apply    # schreibt den Plan
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
import unicodedata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PLAN = ROOT / "data" / "pinterest_plan.yaml"
POSTS = ROOT / "content" / "posts"
PILLARS = ROOT / "content" / "pillar"
REPORT = ROOT / "PINTEREST-LINK-REPORT.md"
BASE = "https://franksfinanzcheck.de"
# identisch zu scripts/pinterest_engine.py – Pin-Traffic muss messbar sein
PIN_UTM = "?utm_source=pinterest&utm_medium=social&utm_campaign=pins"

# Pin-Ziele, die als "kaputt" gelten und geheilt werden müssen
BAD_HOST_PAT = re.compile(r"pinterest\.[a-z.]+", re.I)
CHECK24_PAT = re.compile(r"check24\.de", re.I)

# Thematische Zuordnung Board/Keywords -> Pillar-Seite (Fallback-Ebene)
PILLAR_HINTS = {
    "strom-sparen": ["strom", "gas", "energie", "heiz", "kwh", "stromfresser", "standby"],
    "internet-dsl": ["internet", "dsl", "wlan", "router", "glasfaser", "handytarif", "mobilfunk", "dns"],
    "frugalismus": ["frugal", "sparen", "haushaltsbuch", "budget", "50-30-20", "50 30 20",
                    "minimalismus", "no-spend", "spartipps", "alltag"],
    "versicherungen": ["versicherung", "haftpflicht", "kfz", "wohngebäude", "hausrat", "vorsorge"],
    "mietwagen": ["mietwagen", "reise", "urlaub", "flug", "hotel", "reisebudget"],
    "konto-karten": ["girokonto", "konto", "kreditkarte", "tagesgeld", "zinsen", "depot", "bank"],
}

STOP = {
    "der", "die", "das", "und", "oder", "für", "fuer", "mit", "von", "im", "in", "den", "dem",
    "ein", "eine", "einen", "einer", "eines", "auf", "aus", "zu", "zum", "zur", "so", "du",
    "dein", "deine", "dich", "dir", "ist", "sind", "wie", "was", "wer", "warum", "es", "sie",
    "man", "auch", "nicht", "mehr", "beste", "besten", "bester", "tipps", "tipp", "guide",
    "einfach", "einfache", "clever", "richtig", "richtige", "neu", "neue", "jahr", "jetzt",
    "werbung", "pro", "bis", "ohne", "am", "an", "als", "bei", "je", "euro", "prozent",
}


# --------------------------------------------------------------- Hilfsfunktionen
def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = text.replace("ä", "a").replace("ö", "o").replace("ü", "u").replace("ß", "ss")
    return "".join(c for c in text if not unicodedata.combining(c))


def tokens(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", norm(text)) if len(t) > 2 and t not in STOP}


def read_front_matter(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        return {}
    end = raw.find("\n---", 3)
    if end == -1:
        return {}
    try:
        return yaml.safe_load(raw[3:end]) or {}
    except yaml.YAMLError:
        return {}


def slug_to_url(slug: str, section: str = "posts") -> str:
    """Hugo erzeugt die URL aus dem vollen Ordnernamen INKLUSIVE Datumspraefix
    (kein permalinks-Override in hugo.toml, kein slug im Front Matter).
    Muss identisch zu scripts/pinterest_engine.py bleiben, sonst 404."""
    return f"{BASE}/{section}/{slug}/{PIN_UTM}"


# --------------------------------------------------------------- Index aufbauen
def load_targets() -> list[dict]:
    targets: list[dict] = []
    for d in sorted(POSTS.iterdir()):
        f = d / "index.md" if d.is_dir() else d
        if not f.exists() or f.suffix != ".md":
            continue
        fm = read_front_matter(f)
        if not fm or fm.get("draft") is True:
            continue
        slug = d.stem if d.is_file() else d.name
        url_slug = slug  # Hugo behaelt das Datumspraefix in der URL
        bag = " ".join(
            [str(fm.get("title", "")), str(fm.get("description", "")),
             " ".join(fm.get("tags", []) or []), " ".join(fm.get("keywords", []) or []),
             re.sub(r"^\d{4}-\d{2}-\d{2}-", "", url_slug).replace("-", " ")]
        )
        targets.append({
            "kind": "post",
            "title": fm.get("title", url_slug),
            "url": slug_to_url(url_slug),
            "pillar": fm.get("pillar", ""),
            "tokens": tokens(bag),
            "date": str(fm.get("date", "")),
        })
    for d in sorted(PILLARS.iterdir()):
        if not d.is_dir():
            continue
        idx = d / "_index.md"
        if not idx.exists():
            idx = d / "index.md"   # Repo nutzt index.md fuer Pillar-Seiten
        fm = read_front_matter(idx) if idx.exists() else {}
        if not idx.exists():
            continue
        bag = " ".join([str(fm.get("title", d.name)), str(fm.get("description", "")),
                        d.name.replace("-", " "), " ".join(PILLAR_HINTS.get(d.name, []))])
        targets.append({
            "kind": "pillar",
            "title": fm.get("title", d.name),
            "url": slug_to_url(d.name, "pillar"),
            "pillar": d.name,
            "tokens": tokens(bag),
            "date": "",
        })
    return targets


def guess_pillar(text: str) -> str | None:
    n = norm(text)
    best, best_hits = None, 0
    for pillar, hints in PILLAR_HINTS.items():
        hits = sum(1 for h in hints if norm(h) in n)
        if hits > best_hits:
            best, best_hits = pillar, hits
    return best


# --------------------------------------------------------------- Matching
def score(pin: dict, target: dict) -> float:
    pin_text = " ".join([str(pin.get("titel", "")), str(pin.get("keywords", "")),
                         str(pin.get("beschreibung", "")), str(pin.get("pinwand", ""))])
    pt = tokens(pin_text)
    tt = target["tokens"]
    if not pt or not tt:
        return 0.0
    overlap = pt & tt
    base = len(overlap) / len(pt | tt)  # Jaccard

    # Titel-Treffer wiegen schwerer (Pin-Titel ~ Artikel-Titel)
    title_tokens = tokens(str(pin.get("titel", "")))
    if title_tokens:
        base += 1.2 * len(title_tokens & tt) / len(title_tokens)
    # Keyword-Treffer (echte Suchintention)
    kw_tokens = tokens(str(pin.get("keywords", "")))
    if kw_tokens:
        base += 0.8 * len(kw_tokens & tt) / len(kw_tokens)
    # Pillar-Konsistenz
    p = guess_pillar(pin_text)
    if p and target.get("pillar") == p:
        base += 0.35
    # Artikel schlagen Pillar-Seiten bei Gleichstand
    if target["kind"] == "post":
        base += 0.05
    return round(base, 4)


MIN_SCORE = 1.10  # darunter: kein Artikel wirklich passgenau -> thematische Pillar-Seite


def match(pin: dict, targets: list[dict]) -> tuple[dict, float, str]:
    posts = [t for t in targets if t["kind"] == "post"]
    ranked = sorted(((score(pin, t), t) for t in posts), key=lambda x: -x[0])
    if ranked and ranked[0][0] >= MIN_SCORE:
        return ranked[0][1], ranked[0][0], "artikel"

    pin_text = " ".join([str(pin.get("titel", "")), str(pin.get("keywords", "")),
                         str(pin.get("pinwand", ""))])
    p = guess_pillar(pin_text)
    for t in targets:
        if t["kind"] == "pillar" and t["pillar"] == p:
            return t, ranked[0][0] if ranked else 0.0, "pillar"
    if ranked:
        return ranked[0][1], ranked[0][0], "artikel (schwach)"
    return {"title": "Startseite", "url": f"{BASE}/{PIN_UTM}", "kind": "home"}, 0.0, "startseite"


# --------------------------------------------------------------- Hauptlauf
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Plan tatsächlich schreiben")
    args = ap.parse_args()

    plan = yaml.safe_load(PLAN.read_text(encoding="utf-8"))
    pins = plan.get("pins", [])
    targets = load_targets()
    posts_n = sum(1 for t in targets if t["kind"] == "post")

    rows, healed, already = [], 0, 0
    for pin in pins:
        old = str(pin.get("url", "")).strip()
        tgt, sc, how = match(pin, targets)
        new = tgt["url"]

        was_broken = (not old) or bool(BAD_HOST_PAT.search(old))
        was_affiliate_direct = bool(CHECK24_PAT.search(old))

        if was_broken or was_affiliate_direct:
            healed += 1
            status = "geheilt (Profil-Sackgasse)" if was_broken else "geheilt (Direkt-Affiliate)"
        else:
            already += 1
            status = "war ok"

        if args.apply:
            # CHECK24-Kategorie erhalten (der Bot braucht sie für den CTA im Artikel)
            if was_affiliate_direct:
                pin["check24_kategorie"] = old
            pin["url"] = new
            pin["blog_url"] = new
            pin["link_score"] = sc
            pin["link_quelle"] = how

        rows.append({
            "tag": pin.get("tag"), "typ": pin.get("typ", ""), "titel": pin.get("titel", ""),
            "alt": old, "neu": new, "ziel": tgt["title"], "score": sc,
            "how": how, "status": status,
        })

    if args.apply:
        header = PLAN.read_text(encoding="utf-8").split("pins:")[0]
        body = yaml.safe_dump(plan, allow_unicode=True, sort_keys=False, width=4000)
        # Kopfkommentar erhalten
        body = body[body.index("pins:"):] if "pins:" in body else body
        PLAN.write_text(header + body, encoding="utf-8")

    write_report(rows, posts_n, healed, already, args.apply)
    weak = [r for r in rows if r["how"] != "artikel"]
    print(f"Pins: {len(rows)} | geheilt: {healed} | war ok: {already} | "
          f"ohne exakten Artikel: {len(weak)} | Modus: {'APPLY' if args.apply else 'DRY-RUN'}")
    print(f"Report: {REPORT.relative_to(ROOT)}")
    return 0


def write_report(rows, posts_n, healed, already, applied) -> None:
    now = dt.datetime.now(dt.timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    weak = [r for r in rows if r["how"] != "artikel"]
    lines = [
        "# 🔗 PINTEREST-LINK-REPORT (Premium-Zielseiten-Check)",
        "",
        f"**Stand:** {now} · **Modus:** {'APPLY (Plan geschrieben)' if applied else 'DRY-RUN'}",
        "",
        "**Premium-Regel:** Pin → eigener Blogartikel → Affiliate-CTA. "
        "Nie direkt auf CHECK24 (Spam-Signal + verschenkter SEO-Wert) und nie zurück "
        "aufs Pinterest-Profil (Traffic-Sackgasse).",
        "",
        "## Überblick",
        "",
        "| Kennzahl | Wert |",
        "|---|---|",
        f"| Pins im Masterplan | {len(rows)} |",
        f"| Veröffentlichte Artikel als Ziel verfügbar | {posts_n} |",
        f"| Links geheilt | **{healed}** |",
        f"| Links schon korrekt | {already} |",
        f"| Pins ohne exakt passenden Artikel (→ Pillar-Seite) | {len(weak)} |",
        "",
        "## Zuordnung aller Pins",
        "",
        "| Tag | Typ | Pin | Neues Ziel | Score | Quelle | Status |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['tag']} | {r['typ']} | {r['titel'][:52]} | "
            f"[{r['ziel'][:42]}]({r['neu']}) | {r['score']:.2f} | {r['how']} | {r['status']} |"
        )
    if weak:
        lines += [
            "", "## ⚠️ Content-Lücken (höchste Umsatz-Hebel)", "",
            "Für diese Pins existiert noch kein passgenauer Artikel – sie zeigen aktuell auf die "
            "thematische Pillar-Seite. Jeder eigene Artikel hier hebt die Klickrate messbar:", "",
        ]
        seen = set()
        for r in weak:
            if r["titel"] in seen:
                continue
            seen.add(r["titel"])
            lines.append(f"- **{r['titel']}** → aktuell: {r['neu']}")
    lines += ["", "---", "", "_Erzeugt von `scripts/pinterest_link_healer.py`._", ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
