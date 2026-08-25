#!/usr/bin/env python3
"""
PINTEREST-PIN-TEXT-SYNC (Premium, 25.08.2026)
==============================================

Sorgt dafür, dass **bestehende und zukünftige Pins die Premium-Texte**
aus dem Masterplan (data/pinterest_plan.yaml) tragen – und dass jeder
Artikel das Board-Routings-Feld `pinwand` kennt.

Warum: Die 62 Masterplan-Pins haben kuratierte Titel (≤ 100 Z.) und
Beschreibungen (Hook → Nutzen mit Zahl → CTA, ≤ 500 Z.). Ohne Sync
würde die deterministische Heilung generische Texte aus der
Meta-Description bauen und die Board-Zuordnung per Pillar-Fallback
raten. Der Sync schließt diese Lücke in beiden Richtungen:

  S1  pin_title        ← Plan-Pin-Titel (kuratiert, keyword-first)
  S2  pin_description  ← Plan-Pin-Beschreibung (mit *Werbung |, ≤ 500 Z.)
  S3  pinwand          ← Board-Name aus dem Plan (Multi-Board-Routing)

Matching: Artikel → bester Plan-Pin via Token-Scoring (identische
Norm/Stop-Logik wie scripts/pinterest_link_healer.py, umgekehrte
Richtung). Schwelle MIN_SYNC_SCORE – darunter bleibt der
deterministische Text (kein Zwangspaarung).

Eigenschaften:
  - deterministisch + idempotent (zweiter Lauf = keine Änderungen)
  - Sabotage-Schutz: Selbsttest vor jeder Schreibaktion
  - DRAFTs werden mitgesetzt (sind beim Publizieren sofort pin-fertig)

Aufruf:
  python3 scripts/pinterest_pin_text_sync.py             # Dry-Run (Report)
  python3 scripts/pinterest_pin_text_sync.py --apply     # Frontmatter schreiben
  python3 scripts/pinterest_pin_text_sync.py --json      # zusätzlich JSON

Exit: 0 = ok · 1 = offene Probleme · 2 = Selbsttest-Sabotage
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import unicodedata

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import yaml  # noqa: E402
from post_utils import list_post_paths, slug_of  # noqa: E402

PLAN_FILE = os.path.join(BLOG_DIR, "data", "pinterest_plan.yaml")
REPORT = os.path.join(BLOG_DIR, "PINTEREST-PIN-TEXT-SYNC-REPORT.md")

DO_APPLY = "--apply" in sys.argv
AS_JSON = "--json" in sys.argv

PIN_TITLE_MAX = 100
PIN_DESC_MAX = 500
PIN_DESC_MIN = 40          # kürzer = sicherheitshalber deterministisch neu
MIN_SYNC_SCORE = 1.20      # etwas konservativer als Link-Healer (1.10):
                           # hier wird Text ÜBERSCHRIEBEN – nur klare Matches
                           # dürfen fremden Premium-Text übernehmen

# Identisch zu scripts/pinterest_link_healer.py (bewusst nicht importiert –
# der Sync muss auch ohne yaml-Datei-Probleme des Healers laufen)
STOP = {
    "der", "die", "das", "und", "oder", "für", "fuer", "mit", "von", "im", "in", "den", "dem",
    "ein", "eine", "einen", "einer", "eines", "auf", "aus", "zu", "zum", "zur", "so", "du",
    "dein", "deine", "dich", "dir", "ist", "sind", "wie", "was", "wer", "warum", "es", "sie",
    "man", "auch", "nicht", "mehr", "beste", "besten", "bester", "tipps", "tipp", "guide",
    "einfach", "einfache", "clever", "richtig", "richtige", "neu", "neue", "jahr", "jetzt",
    "werbung", "pro", "bis", "ohne", "am", "an", "als", "bei", "je", "euro", "prozent",
}


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text).lower())
    text = text.replace("ä", "a").replace("ö", "o").replace("ü", "u").replace("ß", "ss")
    return "".join(c for c in text if not unicodedata.combining(c))


def tokens(text: str) -> set:
    return {t for t in re.split(r"[^a-z0-9]+", norm(text)) if len(t) > 2 and t not in STOP}


# ---------------------------------------------------------------- Frontmatter
def split_fm(content: str) -> tuple[str, str, str]:
    """(fm, body, original) – Semantik wie scripts/pinterest_seo_healer.py:
    fm enthält die umgebenden Newlines, body startet mit Newline.
    Roundtrip: '---' + fm + '---' + body == original."""
    if not content.startswith("---"):
        return "", content, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return "", content, content
    return parts[1], parts[2], content


def fm_set(content: str, key: str, value: str) -> str:
    """Setzt/ersetzt ein Top-Level-String-Feld IM FRONTMATTER (YAML-sicher).

    Wichtig: Nur innerhalb des Frontmatter-Blocks (zwischen dem ersten und
    dem zweiten ---) suchen/einfügen – Artikel-Body enthält eigene ---
    Trennlinien (z. B. vor dem Affiliate-CTA-Block)."""
    v = str(value)
    if any(ch in v for ch in ":#{}[]&*!|>%@`\"'") or v != v.strip():
        v = '"' + v.replace('"', '\\"') + '"'
    fm, body, _ = split_fm(content)
    if not fm:
        return content  # kein Frontmatter → nicht anfassen
    line = f"{key}: {v}"
    if re.search(rf"^{re.escape(key)}\s*:", fm, re.M):
        fm2 = re.sub(rf"^{re.escape(key)}\s*:.*$", line, fm, count=1, flags=re.M)
    else:
        fm2 = fm.rstrip("\n") + "\n" + line + "\n"
    return "---" + fm2 + "---" + body


# ---------------------------------------------------------------- Validierung
def pin_title_valid(t: str) -> bool:
    """Pin-TITEL: & ist erlaubt (API-Titel; nur Button-Beschreibungen
    müssen &-frei sein – die sanitized clean_pin_description)."""
    t = (t or "").strip()
    return bool(t) and len(t) <= PIN_TITLE_MAX


def clean_pin_description(beschreibung: str) -> str:
    """Premium-Beschreibung aus dem Plan → pin_description-fertig."""
    t = (beschreibung or "").strip().replace("&", "und")
    t = re.sub(r"\s+", " ", t)
    if not t.startswith("*Werbung"):
        t = f"*Werbung | {t}"
    return t[:PIN_DESC_MAX]


def pin_desc_valid(d: str) -> bool:
    d = (d or "").strip()
    return len(d) >= PIN_DESC_MIN and len(d) <= PIN_DESC_MAX and "&" not in d


# ---------------------------------------------------------------- Matching
def load_board_pillar_map() -> dict:
    """Pinwand → Pillar aus data/pinterest_boards.yaml (Single Source of Truth)."""
    path = os.path.join(BLOG_DIR, "data", "pinterest_boards.yaml")
    try:
        cfg = yaml.safe_load(open(path, encoding="utf-8")) or {}
    except Exception:
        return {}
    m = {}
    for b in cfg.get("boards", []):
        pillars = b.get("pillars") or []
        if pillars and b.get("name"):
            m[norm(b["name"])] = str(pillars[0]).strip().lower()
    return m


def score(post: dict, pin: dict, board_pillar: dict | None = None) -> float:
    """Bag-of-Words-Score + HARTE Board-Konsistenz:

    Weicht die Pinwand des Pins (→ Pillar) von der Pillar des Artikels ab,
    gibt es KEINEN Match mehr (Score -1). Das verhindert semantisch
    falsche Paarungen à la „Handytarif" × „Frugalismus-Pin" – beide
    Seiten kennen ihr Silo, ein Cross-Silo-Pin wäre Spam-Text auf dem
    falschen Board.
    """
    # Gate: Pinwand-Pillar vs. Artikel-Pillar (nur wenn beide bekannt)
    if board_pillar:
        pin_pillar = board_pillar.get(norm(pin.get("pinwand", "")))
        post_pillar = str(post.get("pillar", "")).strip().lower()
        if pin_pillar and post_pillar and pin_pillar != post_pillar:
            return -1.0

    pin_text = " ".join([str(pin.get("titel", "")), str(pin.get("keywords", "")),
                         str(pin.get("beschreibung", "")), str(pin.get("pinwand", ""))])
    pt = tokens(pin_text)
    tt = tokens(" ".join([post["title"], post["description"],
                          " ".join(post["tags"]), " ".join(post["keywords"]),
                          post["slug"].replace("-", " ")]))
    if not pt or not tt:
        return 0.0
    base = len(pt & tt) / len(pt | tt)
    title_t = tokens(post["title"])
    if title_t:
        base += 1.2 * len(title_t & pt) / len(title_t)
    kw_t = tokens(" ".join(post["keywords"]))
    if kw_t:
        base += 0.8 * len(kw_t & pt) / len(kw_t)
    # Board-Konsistenz: Artikel-Pillar ↔ Pin-Pinwand
    if post.get("pinwand") and norm(pin.get("pinwand", "")) == norm(post["pinwand"]):
        base += 0.35
    return round(base, 4)


# ---------------------------------------------------------------- Laden
def load_pins() -> list:
    try:
        plan = yaml.safe_load(open(PLAN_FILE, encoding="utf-8")) or {}
    except Exception:
        return []
    return [p for p in plan.get("pins", []) if p.get("titel")]


def load_posts() -> list:
    posts = []
    for path in list_post_paths():
        content = open(path, encoding="utf-8").read()
        # NUR aus dem Frontmatter-Block lesen (Body kann ähnliche Zeilen
        # enthalten, z. B. in Tabellen oder Trennlinien-Kontexten)
        _fm_block = split_fm(content)[0]
        def fm(key, default=""):
            m = re.search(rf"^{key}:\s*[\"']?(.+?)[\"']?\s*$", _fm_block, re.M)
            return m.group(1).strip() if m else default
        def fm_list(key):
            m = re.search(rf"^{key}:\s*\[(.*?)\]", _fm_block, re.M)
            if not m:
                return []
            return [t.strip().strip('"') for t in m.group(1).split(",") if t.strip()]
        posts.append({
            "slug": slug_of(path), "path": path, "content": content,
            "title": fm("title"), "description": fm("description"),
            "tags": fm_list("tags"), "keywords": fm_list("keywords"),
            "pin_title": fm("pin_title"), "pin_description": fm("pin_description"),
            "pinwand": fm("pinwand"), "pillar": fm("pillar"),
            "draft": re.search(r"^draft:\s*true", content, re.M) is not None,
        })
    return posts


# ---------------------------------------------------------------- Selbsttest
def _selftest() -> list[str]:
    fehler = []
    if PIN_TITLE_MAX != 100 or PIN_DESC_MAX != 500:
        fehler.append("PIN-Limits verändert")
    # fm_set: ersetzen + anlegen
    c = "---\ntitle: A\npin_title: alt\n---\nBody"
    c2 = fm_set(c, "pin_title", "neu mit: Doppelpunkt")
    if 'pin_title: "neu mit: Doppelpunkt"' not in c2:
        fehler.append("fm_set ersetzen defekt")
    c3 = fm_set(c, "pinwand", "Strom & Gas sparen | Tarife clever wechseln")
    if "pinwand:" not in c3 or c3.count("pinwand:") != 1:
        fehler.append("fm_set anlegen defekt")
    # Werbekennzeichnung
    d = clean_pin_description("Heizkosten senken: 6 Tipps")
    if not d.startswith("*Werbung | "):
        fehler.append("Werbung-Prefix defekt")
    d2 = clean_pin_description("*Werbung | schon gekennzeichnet")
    if d2.count("*Werbung") != 1:
        fehler.append("Werbung-Prefix doppelt")
    # &-Sanierung
    if "&" in clean_pin_description("Strom & Gas"):
        fehler.append("&-Sanierung defekt")
    # Scoring: gleiche Themen müssen > MIN scoren
    p = {"titel": "Stromfresser im Haushalt entlarven: Die 5 größten Energiediebe",
         "keywords": "stromfresser finden, strom sparen tipps",
         "beschreibung": "Welche Geräte treiben deine Stromrechnung in die Höhe?",
         "pinwand": "Strom & Gas sparen | Tarife clever wechseln"}
    a = {"title": "Energiediebe stoppen: So findest du Stromfresser",
         "description": "Stromfresser finden und Strom sparen", "tags": ["Strom sparen"],
         "keywords": ["stromfresser finden", "strom sparen"], "slug": "2026-08-19-energiediebe-stromfresser",
         "pinwand": "", "pillar": "strom-sparen"}
    if score(a, p) < MIN_SYNC_SCORE:
        fehler.append(f"Scoring zu schwach ({score(a, p)})")
    # Board-Gate: cross-Silo-Match MUSS abgelehnt werden
    wrong = {"title": "Handytarif vergleichen 2026", "description": "Günstige Tarife",
             "tags": ["Handytarif"], "keywords": ["tarife vergleichen"],
             "slug": "2026-08-28-handytarif", "pinwand": "", "pillar": "internet-dsl"}
    frugal_pin = {"titel": "Frugalismus für Einsteiger", "keywords": "frugalismus tipps",
                  "beschreibung": "Geld sparen ohne Verzicht",
                  "pinwand": "Geld sparen im Alltag | Frugalismus-Tipps"}
    if score(wrong, frugal_pin, load_board_pillar_map()) != -1.0:
        fehler.append("Board-Gate funktioniert nicht (Cross-Silo nicht abgelehnt)")
    return fehler


# ---------------------------------------------------------------- Main
def main() -> int:
    st = _selftest()
    if st:
        print("🛑 PIN-TEXT-SYNC-SELBSTTEST FEHLGESCHLAGEN – Sabotage verhindert.")
        for e in st:
            print(f"   {e}")
        return 2

    pins = load_pins()
    posts = load_posts()
    if not pins:
        print("⚠ data/pinterest_plan.yaml fehlt/leer – Sync übersprungen.")
        return 0

    changed, rows, issues = 0, [], []
    board_pillar = load_board_pillar_map()

    # 1:1-Zuordnung (Premium): Jeder Plan-Pin wird NUR an den Artikel
    # vergeben, der sein BSTER Ziel ist (>= Schwelle, kein Board-Gate).
    # Ein Artikel erhält dann den besten Pin, der ihn gewählt hat.
    # Folge: Kein Artikel kriegt fremden Premium-Text ("DNS-Pin" auf
    # "DSL-Wechsel-Artikel"), und mehrere Pins dürfen denselben Artikel
    # als Ziel haben (Rotation-Kandidaten), der Artikel nimmt den stärksten.
    pin_best: dict[int, tuple[float, int]] = {}
    for i, pin in enumerate(pins):
        best_sc, best_j = -1.0, -1
        for j, post in enumerate(posts):
            if post["draft"]:
                continue  # Drafts sind nicht live → kein Pin-Ziel
            sc = score(post, pin, board_pillar)
            if sc > best_sc:
                best_sc, best_j = sc, j
        if best_sc >= MIN_SYNC_SCORE and best_j >= 0:
            pin_best[i] = (best_sc, best_j)

    for j, post in enumerate(posts):
        if post["draft"]:
            rows.append({"slug": post["slug"], "pin": "-", "score": 0.0,
                         "match": "keine (Draft – beim Publizieren automatisch)",
                         "changed": False})
            continue
        candidates = [(sc, i) for i, (sc, aj) in pin_best.items() if aj == j]
        if not candidates:
            rows.append({"slug": post["slug"], "pin": "-", "score": 0.0,
                         "match": "keine (Pin-Ziel ist ein anderer Artikel)",
                         "changed": False})
            continue
        sc, idx = max(candidates)
        pin = pins[idx]
        new_title = str(pin.get("titel", "")).strip()[:PIN_TITLE_MAX]
        new_desc = clean_pin_description(str(pin.get("beschreibung", "")))
        new_pinwand = str(pin.get("pinwand", "")).strip()

        # Plausibilität: Premium-Text muss auch gültig sein
        if not pin_title_valid(new_title) or not pin_desc_valid(new_desc):
            issues.append(f"{post['slug']}: Plan-Pin-Text ungültig (Tag {pin.get('tag')})")
            rows.append({"slug": post["slug"], "pin": pin.get("tag"), "score": sc,
                         "match": "Text ungültig", "changed": False})
            continue

        # Der Pin hat diesen Artikel als SEIN Ziel gewählt (1:1-Zuordnung +
        # Board-Gate + Schwelle) → Premium-Text wird übernommen und ersetzt
        # auch den deterministischen Build – das ist die Absicht (Premium-
        # Level). Der SEO-Healer schützt den Stand danach vor
        # deterministischem Überschreiben (H6 „gültiger Text bleibt“).
        content = post["content"]
        do_t = (post["pin_title"] != new_title)
        do_d = (post["pin_description"] != new_desc)
        do_w = (post["pinwand"] != new_pinwand)
        if not (do_t or do_d or do_w):
            rows.append({"slug": post["slug"], "pin": pin.get("tag"), "score": sc,
                         "match": "identisch", "changed": False})
            continue
        if do_t:
            content = fm_set(content, "pin_title", new_title)
        if do_d:
            content = fm_set(content, "pin_description", new_desc)
        if do_w:
            content = fm_set(content, "pinwand", new_pinwand)
        if DO_APPLY:
            open(post["path"], "w", encoding="utf-8").write(content)
        changed += 1
        rows.append({"slug": post["slug"], "pin": pin.get("tag"), "score": sc,
                     "match": f"Pin {pin.get('tag')} „{new_title[:40]}…“",
                     "changed": True,
                     "feld": [f for f, d in (("pin_title", do_t),
                                              ("pin_description", do_d),
                                              ("pinwand", do_w)) if d],
                     "pinwand": new_pinwand})

    # Report
    now = dt.datetime.now(dt.timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    lines = [
        "# 🖋 PINTEREST-PIN-TEXT-SYNC-REPORT (Premium-Pin-Texte)",
        "",
        f"**Stand:** {now} · **Modus:** {'APPLY' if DO_APPLY else 'DRY-RUN'}",
        "",
        "**Regel:** Jeder Artikel trägt die Premium-Texte des besten Masterplan-Pins",
        f"(Schwelle {MIN_SYNC_SCORE}) + das `pinwand`-Feld für das Multi-Board-Routing.",
        "",
        f"Artikel: {len(posts)} · geänderte: {changed} · Pins im Plan: {len(pins)}",
        "",
        "| Artikel | Plan-Pin | Score | Status |",
        "|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['slug'][:60]} | {r['pin']} | {r['score']:.2f} | {r['match']} |")
    if issues:
        lines += ["", "## ⚠️ Probleme", ""] + [f"- {i}" for i in issues]
    lines += ["", "---", "", "_Erzeugt von `scripts/pinterest_pin_text_sync.py`._", ""]
    open(REPORT, "w", encoding="utf-8").write("\n".join(lines))

    print(f"Pin-Text-Sync: {len(posts)} Artikel, {changed} mit Premium-Texten "
          f"({'geschrieben' if DO_APPLY else 'Dry-Run'}), {len(issues)} Probleme")
    print(f"Report: {os.path.relpath(REPORT, BLOG_DIR)}")
    try:
        from audit_log import log_event
        log_event(module="pinterest_pin_text_sync", action="apply" if DO_APPLY else "check",
                  input={"posts": len(posts)}, output={"changed": changed},
                  status="ok" if not issues else "issues")
    except Exception:
        pass
    if AS_JSON:
        print(json.dumps({"rows": rows, "issues": issues}, ensure_ascii=False))
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
