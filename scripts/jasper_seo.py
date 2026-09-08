#!/usr/bin/env python3
# ============================================================
#  KI-REDAKTION – Rolle 3 „JASPER": SEO-Pass
#  ------------------------------------------------------------
#  Bildet den Jasper-Part des Schemas („Jasper für SEO") mit
#  möglichst gleichem Funktionsumfang ab. Da Jasper keine
#  öffentliche API anbietet (nur Enterprise), ist diese Rolle als
#  DETERMINISTISCHE SEO-Werkbank mit identischem Feature-Umfang
#  gebaut – plus optionalem Gratis-KI-Feinschliff (Groq/Gemini):
#
#    Jasper-Feature               →  Umsetzung hier
#    ────────────────────────────────────────────────────────────
#    SEO-Mode / Surfer-Integration → Keyword-Dichte, -Platzierung,
#                                    H-Struktur, WDF-artige Analyse
#    Content Improvements          → Befundliste + optionale KI-
#                                    Varianten (--ai, nur Vorschläge)
#    Meta Title/Description        → SERP-Längen-Check (length_policy),
#                                    CTA-/Frage-Heuristik
#    Briefs & Templates            → Pflichtstruktur-Check (FAQ,
#                                    Tabelle, Rechenbeispiel, CTA)
#    Score                         → SEO-Score 0–100 je Artikel
#
#  KOSTEN-REGEL: Kern ist komplett KI-frei (0 €). --ai nutzt nur
#  Gratis-Provider für Varianten-Vorschläge (nie automatisch
#  übernommen – Jasper-Stil: Mensch entscheidet).
#
#  Nutzung:
#    python3 scripts/jasper_seo.py --new-only          # KI-Entwürfe prüfen
#    python3 scripts/jasper_seo.py --slug <slug>       # Einzel-Artikel
#    python3 scripts/jasper_seo.py --new-only --fix    # sichere Auto-Fixes
#    python3 scripts/jasper_seo.py --new-only --ai     # + Titel-Varianten
# ============================================================
from __future__ import annotations

import argparse
import datetime
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import ki_shared as ks  # noqa: E402
import post_utils  # noqa: E402
from post_utils import safe_title_cut  # noqa: E402

try:
    import length_policy
except Exception:  # noqa: BLE001
    length_policy = None
try:
    import llm_client
except Exception:  # noqa: BLE001
    llm_client = None

REPORT_FILE = os.path.join(BLOG_DIR, "KI-SEO-REPORT.md")
SERP_TITLE_MIN, SERP_TITLE_MAX = 30, 60
META_MIN, META_MAX = 120, 160


# ---------------------------------------------------------------- Analyse
def split_post(content: str) -> tuple[dict, str]:
    """Frontmatter (simpel) + Body trennen."""
    fm: dict = {"_raw": {}}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            body = parts[2]
            for line in parts[1].splitlines():
                m = re.match(r"^([A-Za-z0-9_\-]+):\s*(.*)$", line)
                if m:
                    fm["_raw"][m.group(1)] = m.group(2).strip()
    for key in ("title", "description", "pillar", "ki_redaktion"):
        v = fm["_raw"].get(key, "")
        fm[key] = v.strip().strip('"')

    def _list(key):
        raw = fm["_raw"].get(key, "")
        if not raw:
            return []
        items = re.findall(r'"([^"]*)"|\'([^\']*)\'|([^,\[\]]+)', raw)
        out = []
        for a, b, c in items:
            v = (a or b or c).strip()
            if v:
                out.append(v)
        return out

    fm["tags"] = [x for x in _list("tags") if x]
    fm["keywords"] = [x for x in _list("keywords") if x]
    fm["draft"] = fm["_raw"].get("draft", "").lower() == "true"
    return fm, body


def _body_plain(body: str) -> str:
    t = re.sub(r"```.*?```", "", body, flags=re.S)
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"[#>*_|`\-]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def analyze(path: str) -> dict:
    """Vollständiger SEO-Befund eines Artikels (Score + Einzelposten)."""
    with open(path, encoding="utf-8") as fh:
        content = fh.read()
    fm, body = split_post(content)
    plain = _body_plain(body)
    words = plain.lower().split()
    n_words = max(1, len(words))
    checks: list[tuple[str, bool, str]] = []   # (Name, ok, Detail)
    score = 0

    title = fm.get("title", "")
    desc = fm.get("description", "")
    kws = [k for k in (fm.get("keywords") or fm.get("tags") or []) if k]
    main_kw = kws[0].lower() if kws else ""

    # 1. Titel-Länge (SERP)
    ok = SERP_TITLE_MIN <= len(title) <= SERP_TITLE_MAX
    checks.append(("Titel-Länge (SERP 30–60)", ok,
                   f"{len(title)} Zeichen"))
    score += 15 if ok else (8 if 20 <= len(title) <= 70 else 0)

    # 2. Hauptkeyword im Titel
    ok = bool(main_kw) and main_kw.split()[0] in title.lower()
    checks.append(("Hauptkeyword im Titel", ok, main_kw or "kein Keyword"))
    score += 15 if ok else 0

    # 3. Meta-Description-Länge
    ok = META_MIN <= len(desc) <= META_MAX
    checks.append(("Meta-Description 120–160", ok, f"{len(desc)} Zeichen"))
    score += 10 if ok else (5 if 80 <= len(desc) <= 190 else 0)

    # 4. Meta-Description mit Nutzen/CTA
    ok = bool(re.search(r"[€%]|spar|vergleich|kostenlos|prüfen|sichern|wie du",
                        desc, re.I))
    checks.append(("Meta mit Nutzen-/CTA-Signal", ok, ""))
    score += 5 if ok else 0

    # 5. Keyword in den ersten 100 Wörtern
    head = " ".join(words[:100])
    ok = bool(main_kw) and main_kw.split()[0] in head
    checks.append(("Keyword in den ersten 100 Wörtern", ok, ""))
    score += 10 if ok else 0

    # 6. Keyword-Dichte (0,4–2,5 % auf Stammwort)
    density = 0.0
    if main_kw:
        stem = main_kw.split()[0]
        density = sum(1 for w in words if stem in w) / n_words * 100
        ok = 0.4 <= density <= 2.5
        checks.append(("Keyword-Dichte 0,4–2,5 %", ok,
                       f"{density:.2f} %"))
        score += 10 if ok else (5 if density <= 4 else 0)

    # 7. H2-Struktur
    h2 = re.findall(r"(?m)^## .+$", body)
    ok = len(h2) >= 4
    checks.append(("≥ 4 H2-Zwischenüberschriften", ok, f"{len(h2)} H2"))
    score += 10 if ok else (5 if len(h2) >= 2 else 0)

    # 8. Keyword in mind. einer H2
    ok = bool(main_kw) and any(main_kw.split()[0] in h.lower() for h in h2)
    checks.append(("Keyword in einer H2", ok, ""))
    score += 5 if ok else 0

    # 9. Pflichtstruktur (Hausstil der Engine)
    faq = bool(re.search(r"(?im)^##+.*FAQ", body)) or body.count("### ") >= 3
    tabelle = "|" in body and "---" in body
    rechen = "Rechenbeispiel" in body or "Beispielrechnung" in body
    checks.append(("FAQ-Abschnitt", faq, ""))
    checks.append(("Tabelle vorhanden", tabelle, ""))
    checks.append(("Rechenbeispiel", rechen, ""))
    score += (5 if faq else 0) + (5 if tabelle else 0) + (5 if rechen else 0)

    # 10. Interne Verlinkung
    intern = len(re.findall(r"\]\((?:\.\./|\.\./\.\./|/)(?!go/)[^)]+\)", body))
    ok = intern >= 2
    checks.append(("≥ 2 interne Links", ok, f"{intern} gefunden"))
    score += 5 if ok else 0

    # 11. Werbekennzeichnung + Disclaimer (Compliance)
    ok = ("Werbung" in body or "Affiliate" in body) and (
        "keine Anlage" in body or "ausschließlich der allgemeinen" in body
        or "Disclaimer" in body.lower())
    checks.append(("Werbekennzeichnung + Hinweis", ok, ""))
    score += 5 if ok else 0

    return {
        "path": path,
        "slug": post_utils.slug_of(path),
        "title": title,
        "description": desc,
        "main_kw": main_kw,
        "density": density,
        "words": n_words,
        "chars": len(plain),
        "score": min(100, score),
        "checks": checks,
        "fm": fm,
        "body": body,
    }


# ---------------------------------------------------------------- Fixes
def apply_safe_fixes(res: dict, do_fix: bool) -> list:
    """Konservative Auto-Fixes (nur Frontmatter, nur Erweiterungen).

    Wie alle Guards im Repo: niemals Inhalt überschreiben, nur
    fehlende Metadaten ergänzen und Titel SICHER kürzen
    (post_utils.safe_title_cut – bricht nur an Wortgrenzen).
    """
    fixes = []
    fm_raw = res["fm"]["_raw"]
    title = res["title"]

    if len(title) > SERP_TITLE_MAX:
        new_title = safe_title_cut(title, SERP_TITLE_MAX)
        if new_title != title and do_fix:
            _replace_fm_field(res["path"], "title", new_title)
        fixes.append(f"Titel {len(title)}→{len(new_title)} Zeichen: "
                     f"„{new_title}“" + ("" if do_fix else " (mit --fix)"))

    if not fm_raw.get("keywords") and res["fm"]["tags"]:
        if do_fix:
            _set_fm_list(res["path"], "keywords", res["fm"]["tags"])
        fixes.append("keywords aus tags ergänzt"
                     + ("" if do_fix else " (mit --fix)"))
    elif not fm_raw.get("tags") and res["fm"]["keywords"]:
        if do_fix:
            _set_fm_list(res["path"], "tags", res["fm"]["keywords"][:4])
        fixes.append("tags aus keywords ergänzt"
                     + ("" if do_fix else " (mit --fix)"))
    return fixes


def _replace_fm_field(path: str, key: str, value: str) -> None:
    with open(path, encoding="utf-8") as fh:
        content = fh.read()
    safe = value.replace("\\", "\\\\").replace('"', '\\"')
    new = re.sub(rf"(?m)^{key}:.*$", f'{key}: "{safe}"', content, count=1)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new)


def _set_fm_list(path: str, key: str, values: list) -> None:
    with open(path, encoding="utf-8") as fh:
        content = fh.read()
    import json as _json
    line = f"{key}: {_json.dumps(values, ensure_ascii=False)}\n"
    if re.search(rf"(?m)^{key}:", content):
        new = re.sub(rf"(?m)^{key}:.*$", line.rstrip("\n"), content, count=1)
    else:
        new = content.replace("---\n", "---\n" + line, 1)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new)


# ---------------------------------------------------------------- KI-Zusatz
def ai_variants(res: dict) -> list:
    """Jasper-Stil „Content Improvements": Titel-/Meta-Varianten per
    Gratis-KI. Reine VORSCHLÄGE – niemals automatisch übernommen."""
    if llm_client is None:
        return []
    prompt = (
        f"Artikel: {res['title']}\nThema/Keyword: {res['main_kw']}\n"
        "Liefere als deutscher SEO-Profi genau 3 Alternative SERP-Titel "
        "(je 30–60 Zeichen, Keyword vorn, keine Clickbait-Lügen) und "
        "2 alternative Meta-Descriptions (je 120–160 Zeichen, mit "
        "Nutzenversprechen). Format: je eine Zeile, Titel mit 'T1:', "
        "'T2:', 'T3:', Descriptions mit 'D1:', 'D2:'. Nichts weiter."
    )
    for prov in ("groq", "gemini"):
        text = llm_client.chat(prov, prompt=prompt,
                               temperature=0.6, max_tokens=600, timeout=120)
        if text:
            return [l.strip(" -•") for l in text.splitlines()
                    if re.match(r"^[TD][123]:", l.strip())]
    return []


# ---------------------------------------------------------------- Report
def write_report(results: list, fixes_by_slug: dict,
                 variants_by_slug: dict) -> None:
    stamp = datetime.datetime.now(datetime.timezone.utc)
    lines = [
        "# KI-SEO-REPORT (Rolle Jasper der KI-Redaktion)",
        "",
        f"_Stand: {stamp.strftime('%d.%m.%Y %H:%M UTC')} – erzeugt durch "
        "scripts/jasper_seo.py. Jasper-Feature-Äquivalent: SEO-Score, "
        "Keyword-/Struktur-Analyse, Meta-Optimierung, Content "
        "Improvements (Vorschläge)._",
        "",
        "| Artikel | Score | Wörter | Dichte | Befund |",
        "|---|---|---|---|---|",
    ]
    for r in sorted(results, key=lambda x: x["score"]):
        fails = [c[0] for c in r["checks"] if not c[1]]
        lines.append(f"| {r['slug']} | **{r['score']}/100** | "
                     f"{r['words']:,} | {r['density']:.2f} % | "
                     f"{len(fails)} offen |")
    for r in results:
        lines += ["", f"## {r['slug']} – {r['score']}/100", ""]
        for name, ok, detail in r["checks"]:
            icon = "✅" if ok else "❌"
            lines.append(f"- {icon} {name}"
                         + (f" – {detail}" if detail else ""))
        for fx in fixes_by_slug.get(r["slug"], []):
            lines.append(f"- 🔧 Fix: {fx}")
        for v in variants_by_slug.get(r["slug"], []):
            lines.append(f"- 💡 Vorschlag (nicht übernommen): {v}")
    lines += ["", "_Legende: Score ≥ 85 = bereit für die Engine-Gates; "
              "< 70 = vor Freigabe nacharbeiten._", ""]
    with open(REPORT_FILE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def select_posts(args) -> list:
    if args.slug:
        p = post_utils.post_path(args.slug)
        return [p] if os.path.exists(p) else []
    paths = post_utils.list_post_paths()
    if args.new_only:
        out = []
        for p in paths:
            try:
                with open(p, encoding="utf-8") as fh:
                    head = fh.read(2500)
            except OSError:
                continue
            if "ki_redaktion:" in head:
                out.append(p)
        return out
    return paths


def main() -> int:
    ap = argparse.ArgumentParser(
        description="KI-Redaktion, Rolle Jasper: SEO-Analyse & -Fixes")
    ap.add_argument("--slug", help="nur diesen Artikel prüfen")
    ap.add_argument("--new-only", action="store_true",
                    help="nur Entwürfe der KI-Redaktion prüfen")
    ap.add_argument("--fix", action="store_true",
                    help="sichere Auto-Fixes anwenden (nur Metadaten)")
    ap.add_argument("--ai", action="store_true",
                    help="Gratis-KI-Varianten für Titel/Meta vorschlagen")
    ap.add_argument("--limit", type=int, default=0,
                    help="max. Artikelzahl (0 = alle)")
    args = ap.parse_args()

    posts = select_posts(args)
    if args.limit:
        posts = posts[:args.limit]
    if not posts:
        print("❌ Keine passenden Artikel gefunden "
              "(Tipp: --new-only prüft die KI-Entwürfe).")
        return 1

    results, fixes_by_slug, variants_by_slug = [], {}, {}
    for p in posts:
        res = analyze(p)
        fixes = apply_safe_fixes(res, args.fix)
        if fixes:
            fixes_by_slug[res["slug"]] = fixes
        if args.ai:
            variants = ai_variants(res)
            if variants:
                variants_by_slug[res["slug"]] = variants
        results.append(res)
        print(f"{'✅' if res['score'] >= 85 else '⚠️'} "
              f"{res['slug']}: Score {res['score']}/100 "
              f"({res['words']:,} Wörter, Dichte {res['density']:.2f} %)")

    write_report(results, fixes_by_slug, variants_by_slug)
    print(f"\n📄 Report: {os.path.relpath(REPORT_FILE, BLOG_DIR)}")
    ks.write_report([
        f"- **Letzter SEO-Pass (Rolle Jasper):** {len(results)} Artikel "
        "analysiert, Details im `KI-SEO-REPORT.md`.",
        "- Auto-Fixes betreffen ausschließlich Metadaten – Inhalt wird "
        "nie überschrieben.",
    ])
    return 0


if __name__ == "__main__":
    sys.exit(main())
