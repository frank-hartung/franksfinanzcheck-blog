#!/usr/bin/env python3
"""Seitenbezogene Agent-Reach-Recherche für den gesamten Redaktionsbestand.

Die allgemeine Agent-Reach-Signalsammlung beantwortet „Was bewegt sich?".
Diese Lane beantwortet zusätzlich „Welche bestehende oder neue Seite muss jetzt
fachlich geprüft werden?". Sie recherchiert bei Erstellung/Strukturänderung
sofort und danach in einem zur Seitengattung passenden Intervall.

Wichtig: Treffer sind ein Quellen-Dossier, kein automatisch publizierter Fakt.
Nur öffentliches RSS (Google-News-Suche, über die Agent-Reach-RSS-Schicht),
keine Cookies/Logins/Schreiboperationen. Eine Quellen-URL und ein Datum bleiben
an jedem Signal erhalten. Das Dossier wird als Prüfkontext für Redaktion und
nachgelagerte Claude-Läufe bereitgestellt; Zahlen dürfen erst nach Gegenprüfung
übernommen werden.
"""
from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import hashlib
import html
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import sprachkern as sk  # noqa: E402

STATE = ROOT / "data" / "agent_reach" / "content_research_state.json"
OUT = ROOT / "data" / "research" / "editorial"
USER_AGENT = "FranksFinanzcheck-Agent-Reach/2.0 (+https://franksfinanzcheck.de/methodik/)"

INTERVALS = {
    "Blogartikel": 30,
    "Ratgeberseite": 21,
    "Newsletter-Landingpage": 45,
    "redaktionelle Unterseite": 90,
    "Startseite": 45,
}

# Suchraum bevorzugt Primär-/Verbraucherquellen. Der zweite, offene Query fängt
# relevante Marktänderungen auf; das Dossier trennt beide Klassen sichtbar.
TRUSTED_DOMAINS = (
    "bundesnetzagentur.de", "bafin.de", "destatis.de", "bundesregierung.de",
    "gesetze-im-internet.de", "verbraucherzentrale.de", "finanztip.de",
)


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def load_state(path: Path = STATE) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"version": 1, "pages": {}}
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "pages": {}}


def research_fingerprint(item: dict) -> str:
    """Nur Themen-/Strukturdrift triggert Recherche, nicht jede Stilpolitur."""
    headings = re.findall(r"(?m)^#{2,3}\s+(.+)$", item.get("body", ""))
    keywords = re.findall(r"(?m)^keywords:\s*(.+)$", item.get("fm", ""))
    raw = "\n".join([item.get("title", ""), item.get("description", ""),
                      *keywords, *headings])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def due_reason(item: dict, state: dict, now: dt.datetime, force=False) -> str | None:
    if force:
        return "manuell erzwungen"
    entry = (state.get("pages") or {}).get(item["key"])
    fp = research_fingerprint(item)
    if not entry:
        return "neu im Recherche-Inventar"
    if entry.get("fingerprint") != fp:
        return "Thema oder Gliederung geändert"
    try:
        last = dt.datetime.fromisoformat(str(entry.get("researched_at", "")).replace("Z", "+00:00"))
        if last.tzinfo is None:
            last = last.replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return "Recherche-Datum fehlt"
    age = (now - last).days
    interval = INTERVALS.get(item.get("kind"), 60)
    return f"Turnus fällig ({age}/{interval} Tage)" if age >= interval else None


def clean_query(item: dict) -> str:
    title = re.sub(r"\b20\d{2}\b", "", item.get("title", ""))
    title = re.sub(r"\s*[|:–—-]\s*FranksFinanzcheck.*$", "", title, flags=re.I)
    title = re.sub(r"[^0-9A-Za-zÄÖÜäöüß &/-]+", " ", title)
    words = [w for w in title.split() if len(w) > 2]
    return " ".join(words[:10]).strip() or item.get("slug", "Finanzen")


def news_url(query: str) -> str:
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode({
        "q": query, "hl": "de", "gl": "DE", "ceid": "DE:de",
    })


def parse_rss(payload: bytes, limit=5) -> list[dict]:
    root = ET.fromstring(payload)
    out = []
    for node in root.findall(".//item")[:limit]:
        title = html.unescape((node.findtext("title") or "").strip())
        link = (node.findtext("link") or "").strip()
        source_node = node.find("source")
        source = (source_node.text or "").strip() if source_node is not None else ""
        published = (node.findtext("pubDate") or "").strip()
        try:
            parsed = email.utils.parsedate_to_datetime(published)
            published = parsed.date().isoformat()
        except (TypeError, ValueError, OverflowError):
            published = published[:16]
        if title and link:
            out.append({"title": title, "url": link, "source": source,
                        "published": published})
    return out


def fetch_query(query: str, timeout=25, opener=urllib.request.urlopen) -> tuple[list[dict], str | None]:
    request = urllib.request.Request(news_url(query), headers={"User-Agent": USER_AGENT})
    try:
        with opener(request, timeout=timeout) as response:
            return parse_rss(response.read()), None
    except Exception as exc:  # Netzwerkfehler pro Seite isolieren
        return [], f"{exc.__class__.__name__}: {exc}"


def research(item: dict, timeout=25) -> dict:
    query = clean_query(item)
    trusted = "(" + " OR ".join(f"site:{d}" for d in TRUSTED_DOMAINS) + ") " + query
    primary, err_primary = fetch_query(trusted, timeout)
    market, err_market = fetch_query(query, timeout)
    seen = set()
    sources = []
    for source_class, rows in (("Primär-/Verbraucherquelle", primary),
                               ("Marktsignal – gegenprüfen", market)):
        for row in rows:
            marker = row["url"]
            if marker in seen:
                continue
            seen.add(marker)
            sources.append({**row, "class": source_class})
    return {"page": item["key"], "kind": item["kind"], "title": item["title"],
            "query": query, "sources": sources,
            "errors": [e for e in (err_primary, err_market) if e]}


def render(rows: list[dict], generated: str) -> str:
    lines = [f"# Agent-Reach Seitenrecherche · {generated[:10]}", "",
             f"> Lauf: {generated} · RSS/Web, nur lesend · {len(rows)} Seiten.",
             "> **Prüfdossier, kein Publikationsmaterial:** Titel und Snippets sind Signale.",
             "> Jede fachliche Aussage, Zahl oder Frist vor Übernahme an der Originalquelle prüfen.", ""]
    for row in rows:
        lines += [f"## {row['title']}", "", f"- **Seite:** `{row['page']}`",
                  f"- **Typ:** {row['kind']}", f"- **Anlass:** {row['reason']}",
                  f"- **Suchkern:** `{row['query']}`", ""]
        if row["sources"]:
            for source in row["sources"]:
                stamp = f" · {source['published']}" if source.get("published") else ""
                publisher = f" ({source['source']})" if source.get("source") else ""
                lines.append(f"- [{source['title']}]({source['url']}){publisher}{stamp} — *{source['class']}*")
        else:
            lines.append("- ⚠ Keine Quelle geliefert; Seite bleibt im nächsten Lauf fällig.")
        for error in row.get("errors", []):
            lines.append(f"  - Abruffehler: `{error}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def save(rows: list[dict], state: dict, now: dt.datetime, out_dir: Path = OUT,
         state_path: Path = STATE) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = now.isoformat(timespec="seconds").replace("+00:00", "Z")
    day = now.date().isoformat()
    md = out_dir / f"{day}-seitenrecherche.md"
    js = out_dir / f"{day}-seitenrecherche.json"
    md.write_text(render(rows, stamp), encoding="utf-8")
    js.write_text(json.dumps({"generated": stamp, "pages": rows}, ensure_ascii=False, indent=2) + "\n",
                  encoding="utf-8")
    pool = state.setdefault("pages", {})
    for row in rows:
        # Fehlgeschlagene Seiten bleiben fällig und werden nicht fälschlich als frisch markiert.
        if row["sources"]:
            pool[row["page"]] = {"researched_at": stamp,
                                  "fingerprint": row["fingerprint"],
                                  "source_count": len(row["sources"])}
    state["version"] = 1
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return md, js


def selftest() -> int:
    sample = """<rss><channel><item><title>Strompreise &amp; Netzentgelte</title><link>https://example.org/a</link><source>Behörde</source><pubDate>Sat, 26 Sep 2026 10:00:00 GMT</pubDate></item></channel></rss>""".encode("utf-8")
    assert parse_rss(sample)[0]["title"] == "Strompreise & Netzentgelte"
    item = {"key": "content/posts/x/index.md", "kind": "Blogartikel", "title": "Strom sparen 2026: Ratgeber", "description": "x", "body": "## Eins", "fm": ""}
    assert clean_query(item).startswith("Strom sparen")
    assert due_reason(item, {"pages": {}}, now_utc())
    fp = research_fingerprint(item)
    fresh = {"pages": {item["key"]: {"fingerprint": fp, "researched_at": now_utc().isoformat()}}}
    assert due_reason(item, fresh, now_utc()) is None
    print("✅ Agent-Reach-Seitenrecherche: Selbsttest grün")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=("posts", "guides", "pages", "editorial"), default="editorial")
    ap.add_argument("--new-only", action="store_true", help="nur heute datierte Inhalte")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--limit", type=int, default=8, help="Netzbudget pro Lauf, 0 = unbegrenzt")
    ap.add_argument("--timeout", type=int, default=25)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()

    now = now_utc()
    state = load_state()
    items = sk.load_articles(scope=args.scope, new_only=args.new_only, include_drafts=True)
    due = []
    for item in items:
        reason = due_reason(item, state, now, args.force)
        if reason:
            date_match = re.search(r"(?m)^date:\s*[\"']?(\d{4})-(\d{2})-(\d{2})", item.get("fm", ""))
            recency = int("".join(date_match.groups())) if date_match else 0
            due.append((0 if "neu" in reason or "geändert" in reason else 1,
                        -recency, item["key"], reason, item))
    # Neue/geänderte Inhalte zuerst, innerhalb der Gruppe die jüngsten zuerst.
    due.sort(key=lambda row: (row[0], row[1], row[2]))
    if args.limit:
        due = due[:max(args.limit, 0)]
    if args.dry_run:
        for _, _, key, reason, _ in due:
            print(f"{key}: {reason}")
        print(f"{len(due)} Seite(n) fällig")
        return 0

    rows = []
    for _, _, _, reason, item in due:
        result = research(item, args.timeout)
        result["reason"] = reason
        result["fingerprint"] = research_fingerprint(item)
        rows.append(result)
        print(f"🔎 {item['key']}: {len(result['sources'])} Quellen ({reason})")
    if not rows:
        print("✅ Kein redaktioneller Inhalt zur Recherche fällig.")
        return 0
    md, js = save(rows, state, now)
    successful = sum(bool(row["sources"]) for row in rows)
    print(f"Dossier: {md.relative_to(ROOT)} + {js.relative_to(ROOT)} · {successful}/{len(rows)} erfolgreich")
    return 0 if successful else 3


if __name__ == "__main__":
    raise SystemExit(main())
