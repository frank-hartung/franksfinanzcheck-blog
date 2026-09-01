#!/usr/bin/env python3
"""
TEXTVERSTÄNDNIS-GUARD (R2–R8) für FranksFinanzcheck.

Die Verständnis-Regeln aus dem Textverständnis-Audit (01.09.2026), die
KEIN bestehendes Gate misst:

  R2  Keyword-Dump-Guard   Komma-Ketten > 200 Zeichen mit > 12 Kommas
                           bzw. > 40 Tokens ohne Verb im Fließtext
                           („300 Begriffe“-Listen)
  R3  Terminologie-Guard   1 Konzept = 1 Leitbegriff (data/terminologie.yaml);
                           > max_synonyme Vorkommen von Synonymen -> Fund
  R4  Satzanfangs-Guard    derselbe Satzanfang in > 20 % der Fließtext-
                           sätze oder > 4× pro 1.000 Wörter
  R5  Absatz-Guard         Fließtext-Absatz > 4 Sätze -> Fund, > 6 Sätze -> hart
  R7  Intro-Formel-Guard   „In diesem Ratgeber/Artikel/Beitrag …“ -> 0 Toleranz
  R8  Ankertext-Ziel-Kohärenz  Ankertext passt nicht zu Slug des Ziels;
                           Leerzeichen in URL = harter Fehler

MODI:
  python3 scripts/textverstaendnis_guard.py            # Report (alle Artikel)
  python3 scripts/textverstaendnis_guard.py --json     # maschinenlesbar
  python3 scripts/textverstaendnis_guard.py --new-only # Engine-Modus (heute);
                                                       # harte Regeln -> Exit 1
  python3 scripts/textverstaendnis_guard.py --selftest # Sabotage-Schutz

Ausgabe: TEXTVERSTAENDNIS-REPORT.md + data/verstaendnis_history.jsonl
"""

import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "content" / "posts"
REPORT = ROOT / "TEXTVERSTAENDNIS-REPORT.md"
HISTORY = ROOT / "data" / "verstaendnis_history.jsonl"
TERMINOLOGIE = ROOT / "data" / "terminologie.yaml"

NEW_ONLY = "--new-only" in sys.argv
AS_JSON = "--json" in sys.argv
SELFTEST_ONLY = "--selftest" in sys.argv

# R2
R2_MAX_LEN = 200
R2_MAX_COMMAS = 12
R2_MAX_TOKENS = 40
# R4
R4_MAX_PCT = 20.0
R4_MAX_PER_1K = 4.0
# R5
R5_SOFT = 4
R5_HARD = 6
# R7
INTRO_FORMELN = [
    "in diesem ratgeber", "in diesem artikel", "in diesem beitrag",
    "in dieser anleitung", "in diesem guide", "in diesem blogbeitrag",
]
# R8
R8_STOPWORDS = {"der", "die", "das", "den", "dem", "des", "ein", "eine", "einer",
                "eines", "einem", "einen", "und", "oder", "aber", "für", "fur",
                "mit", "von", "vom", "zum", "zur", "auf", "bei", "nach", "aus",
                "im", "in", "am", "an", "so", "wie", "nicht", "auch", "du", "dein",
                "deine", "deinen", "deinem", "ihr", "ihre", "ihren", "die", "das",
                "vor", "nur", "was", "sich", "dich", "dir"}


def normalize_umlauts(text: str) -> str:
    """ä→ae, ö→oe, ü→ue, ß→ss (für Slug↔Ankertext-Abgleich R8)."""
    return (text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
                .replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue")
                .replace("ß", "ss"))


# Normalisierte Stoppwörter („für“→„fuer“) dürfen im Slug ebenfalls nicht als
# Treffer gelten – sonst maskiert jeder Anker mit „für“ echte Ziel-Mismatches.
R8_STOPWORDS_NORM = {normalize_umlauts(w) for w in R8_STOPWORDS}

FLOW_LINE_EXCLUDE = re.compile(r"^\s*(#|[*>\|\-]|\d+\.|!\[)")


def split_body(raw: str) -> str:
    parts = raw.split("---", 2)
    return parts[2] if len(parts) >= 3 else raw


def flow_paragraphs(body: str) -> list:
    """Fließtext-Absätze (keine Listen/Tabellen/Zitate/Überschriften/Code)."""
    out = []
    for chunk in body.split("\n\n"):
        lines = [l for l in chunk.split("\n") if l.strip()]
        if not lines:
            continue
        first = lines[0].strip()
        if re.match(r"^\s*([#>*|\-\d.])", first):
            continue
        if first.startswith("```") or first.startswith("{{<"):
            continue
        # Ab der ersten Listen-/Tabellen-/Zitat-Zeile endet der Fließtext:
        # eine Einleitung mit anschließender Liste („…belohnen Rabatten:“
        # gefolgt von „- Punkt“) ist EIN Satz, kein 5-Satz-Absatz.
        cut = len(lines)
        for n, l in enumerate(lines):
            if re.match(r"^\s*([*\-]|\d+\.|>|\|)", l.strip()):
                cut = n
                break
        lines = lines[:cut] or lines[:1]
        text = " ".join(lines)
        # Hugo-Shortcodes rausfiltern (z. B. {{< tarifvergleich ... >}})
        text = re.sub(r"\{\{<.*?>\}\}", " ", text, flags=re.S)
        text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
        text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
        text = text.replace("&nbsp;", " ")
        if len(re.findall(r"\b\w+\b", text)) < 6:
            continue
        out.append(text)
    return out


def flow_sentences(body: str) -> list:
    """Fließtext-Sätze (ohne Listen/Tabellen/Überschriften)."""
    sents = []
    for para in flow_paragraphs(body):
        t = re.sub(r"(?<=\d)\.\s+(?=[A-ZÄÖÜ])", " ", para)
        parts = re.split(r"[.!?](\s+|$)", t)
        for s in parts:
            words = re.findall(r"\b\w+\b", s)
            if len(words) >= 5:
                sents.append(" ".join(words))
    return sents


def load_terminologie() -> dict:
    if not yaml or not TERMINOLOGIE.exists():
        return {}
    data = yaml.safe_load(TERMINOLOGIE.read_text(encoding="utf-8"))
    return data.get("begriffe", {}) if isinstance(data, dict) else {}


def check_article(rel: str, body: str, term: dict) -> list:
    finds = []
    paras = flow_paragraphs(body)

    # ---------- R2 Keyword-Dump ----------
    for para in paras:
        commas = para.count(",")
        tokens = re.findall(r"[a-zäöüßA-ZÄÖÜ0-9]+", para)
        verbs = re.findall(r"\b(ist|sind|war|waren|wird|werden|wurde|hat|haben|kann|können|soll|sollte|muss|müssen|fährt|fährst|öffnet|erklärt|zeigt|gibt|kommt|steht|liegt|folgt|hilft|bringt|spart|kostet|zahlt|zahlst|wechselt|wechselst|findet|findest|erfährst|läuft|lädt|geht|gehst)\b", para, re.I)
        if len(para) > R2_MAX_LEN and commas > R2_MAX_COMMAS and len(tokens) > R2_MAX_TOKENS and len(verbs) <= 2:
            finds.append((rel, "R2-KEYWORD-DUMP",
                          f"{len(para)} Zeichen, {commas} Kommas, kaum Verben: {para[:110]}…", para[:40]))

    # ---------- R3 Terminologie ----------
    for konzept, cfg in term.items():
        leit = cfg.get("leitbegriff", "")
        syns = cfg.get("synonyme", [])
        if not leit or not syns:
            continue
        if cfg.get("kontext") and cfg["kontext"] not in body:
            continue
        leit_count = len(re.findall(re.escape(leit), body, re.I))
        syn_counts = [(s, len(re.findall(re.escape(s), body, re.I))) for s in syns]
        total_syn = sum(c for _, c in syn_counts)
        max_syn = cfg.get("max_synonyme", 2)
        if leit_count >= 3 and total_syn > max_syn:
            detail = ", ".join(f"{s}×{c}" for s, c in syn_counts if c)
            finds.append((rel, "R3-TERMINOLOGIE",
                          f"Konzept „{leit}“: {total_syn} Synonym-Vorkommen ({detail}) – Leitbegriff verwenden", konzept))

    # ---------- R4 Satzanfangs-Echo ----------
    starts = []
    for s in flow_sentences(body):
        w = re.findall(r"[a-zäöüß]+", s.lower())
        if w:
            starts.append(w[0])
    if starts:
        from collections import Counter
        n = len(starts)
        for word, cnt in Counter(starts).most_common(3):
            pct = 100.0 * cnt / n
            if pct >= R4_MAX_PCT or (cnt >= 4 and 1000.0 * cnt / max(1, sum(len(x.split()) for x in [])) >= 0):
                pass
        # pro 1.000 Wörter
        words_total = sum(len(s.split()) for s in flow_sentences(body))
        top = Counter(starts).most_common(1)[0]
        word, cnt = top
        per1k = 1000.0 * cnt / max(1, words_total)
        if cnt >= 5 and (100.0 * cnt / n >= R4_MAX_PCT or per1k >= R4_MAX_PER_1K):
            finds.append((rel, "R4-SATZANFANG",
                          f"„{word}“ startet {cnt}/{n} Sätze ({per1k:.1f}/1k Wörter)", word))

    # ---------- R5 Absatzlänge ----------
    for para in paras:
        t = re.sub(r"(?<=\d)\.\s+(?=[A-ZÄÖÜ])", " ", para)
        n_sents = sum(1 for s in re.split(r"[.!?](\s+|$)", t) if len(s.split()) >= 4)
        if n_sents > R5_HARD:
            finds.append((rel, "R5-ABSATZ-HART",
                          f"Absatz mit {n_sents} Sätzen (Limit {R5_HARD}): {para[:90]}…", para[:30]))
        elif n_sents > R5_SOFT:
            finds.append((rel, "R5-ABSATZ",
                          f"Absatz mit {n_sents} Sätzen (Limit {R5_SOFT}): {para[:90]}…", para[:30]))

    # ---------- R7 Intro-Formel ----------
    body_l = body.lower()
    for phrase in INTRO_FORMELN:
        c = body_l.count(phrase)
        if c:
            finds.append((rel, "R7-INTRO-FORMEL",
                          f"„{phrase}“ ×{c} (Template-Sprache – umformulieren)", phrase))

    # ---------- R8 Ankertext-Ziel + URL-Hygiene ----------
    for m in re.finditer(r"\[([^\]]*)\]\(([^)]+)\)", body):
        anker, url = m.group(1), m.group(2)
        if url.startswith(("http", "mailto:", "#")) or url.startswith("/go/"):
            continue
        if " " in url:
            finds.append((rel, "R8-URL-LEERZEICHEN",
                          f"URL mit Leerzeichen: „{url}“ (Anker: „{anker[:40]}“)", url))
            continue
        if not url.endswith("/"):
            continue
        slug = url.rstrip("/").split("/")[-1]
        if not slug or slug.startswith("."):
            continue
        # Datums-Präfix + Stoppwörter aus dem Slug ziehen.
        # Mindestlänge 3 (statt 4): Kurz-Kernbegriffe des Blogs (dsl, gas,
        # dns, kwh) sind inhaltstragend und sollen Ankertext-Kohärenz prüfen.
        tokens = [t for t in re.split(r"[-_]", slug)
                  if len(t) >= 3 and t not in R8_STOPWORDS
                  and normalize_umlauts(t) not in R8_STOPWORDS_NORM
                  and not re.fullmatch(r"\d{4}|\d{2}", t)]
        if not tokens:
            continue
        # Weiche Trennzeichen (U+00AD, von umbruch_guard) vor dem Abgleich entfernen
        anker_l = anker.lower().replace("\u00ad", "").replace("\u2011", "-")
        # Umlaute normalisieren: ä→ae, ö→oe, ü→ue, ß→ss
        # Damit "spätsommer" auch "spaetsommer" erkennt
        anker_norm = normalize_umlauts(anker_l)
        tokens_norm = [normalize_umlauts(t) for t in tokens]
        hits = [t for t in tokens_norm if t in anker_l or t in anker_norm]
        if not hits:
            finds.append((rel, "R8-ANKER-ZIEL",
                          f"Ankertext „{anker[:45]}“ passt nicht zum Ziel „{slug}“", slug))
    return finds


def run_selftest() -> list:
    fehler = []
    term = {"dns": {"leitbegriff": "DNS-Server", "synonyme": ["Resolver", "Namensauflösung"],
                    "max_synonyme": 3, "kontext": "DNS"}}

    # R2
    body = "TEXT\n\nAnycast, Auflösungszeit, Blockliste, Cache-Flush, DDoS-Schutz, Edgerouter, Failover, Geofencing, Hijacking, IPv6-Resolver, Jitter, Kabelmodem, Latenzmessung, Meshknoten, Nameserver, Overhead, Paketlaufzeit, Query-Log, Root-Server, Spoofing, TTL-Wert, UDP-Fragmentierung, Whois-Abfrage, XDP-Filter, Zertifikatspinning, Backbone, Content-Delivery, Datenpaket, Endpunkt, Firewall-Regel, Gateway, Hop, Infrastruktur."
    if not any(f[1] == "R2-KEYWORD-DUMP" for f in check_article("t", body, {})):
        fehler.append("R2: Keyword-Dump nicht erkannt")

    # R3
    body3 = "DNS erklärt. Der DNS-Server ist wichtig. Der DNS-Server löst Namen auf. Der DNS-Server ist schnell. Der Resolver fragt nach, die Namensauflösung antwortet, der Resolver speichert, die Namensauflösung liefert."
    if not any(f[1] == "R3-TERMINOLOGIE" for f in check_article("t", body3, term)):
        fehler.append("R3: Terminologie-Mix nicht erkannt")

    # R4
    body4 = ("TEXT\n\n" + "Der Wechsel dauert fünf Minuten. Der Wechsel kostet nichts. Der Wechsel ist sicher. "
             "Der Wechsel bringt mehr Tempo. Der Wechsel lohnt sich. Der Wechsel ist simpel. " * 3)
    if not any(f[1] == "R4-SATZANFANG" for f in check_article("t", body4, {})):
        fehler.append("R4: Satzanfangs-Echo nicht erkannt")

    # R5
    body5 = "TEXT\n\nDieser Absatz hat viele Sätze. Der erste Satz ist kurz. Der zweite Satz ist kurz. Der dritte Satz ist kurz. Der vierte Satz ist kurz. Der fünfte Satz ist kurz. Der sechste Satz ist kurz. Der siebte Satz ist kurz."
    if not any(f[1] == "R5-ABSATZ-HART" for f in check_article("t", body5, {})):
        fehler.append("R5: Absatz-Monster nicht erkannt")

    # R7
    body7 = "TEXT\n\nIn diesem Ratgeber zeige ich dir alles. In diesem Ratgeber erfährst du mehr."
    if not any(f[1] == "R7-INTRO-FORMEL" for f in check_article("t", body7, {})):
        fehler.append("R7: Intro-Formel nicht erkannt")

    # R8
    body8 = "TEXT\n\nMehr dazu [die wichtigsten Anbieter](../../posts/2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich/) und [kaputter Link](../../posts/2026-08-20-falscher-slug/)."
    r8 = [f for f in check_article("t", body8, {}) if f[1] in ("R8-ANKER-ZIEL", "R8-URL-LEERZEICHEN")]
    if not any(f[1] == "R8-ANKER-ZIEL" for f in r8):
        fehler.append("R8: Ankertext-Ziel-Kohärenz nicht erkannt")
    body8b = "TEXT\n\n[Text](../../posts/2026-08-20-dsl-tarif-zu Hause/)"
    if not any(f[1] == "R8-URL-LEERZEICHEN" for f in check_article("t", body8b, {})):
        fehler.append("R8: URL-Leerzeichen nicht erkannt")
    # R8 Umlaut: "spätsommer" im Anker muss "spaetsommer" im Slug erkennen
    body8c = "TEXT\n\n[Heizung im Spätsommer](../../posts/2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden/)"
    r8c = [f for f in check_article("t", body8c, {}) if f[1] == "R8-ANKER-ZIEL"]
    if r8c:
        fehler.append("R8: Umlaut-Normalisierung fehlgeschlagen – „Spätsommer“ sollte „spaetsommer“ erkennen")
    return fehler


def main() -> int:
    fehler = run_selftest()
    if fehler or SELFTEST_ONLY:
        for f in fehler:
            print("🛑 " + f)
        if fehler:
            print("SELFTEST FEHLGESCHLAGEN – nichts geschrieben.")
            return 2
        print("✅ Verständnis-Selbsttest: 8 Fälle grün.")
        return 0

    term = load_terminologie()
    today = date.today().isoformat()
    paths = sorted(POSTS.glob("*/index.md"))
    paths = [p for p in paths if p.name != "_index.md"]
    if NEW_ONLY:
        paths = [p for p in paths
                 if re.search(rf"^date:\s*\"?{today}", p.read_text(encoding="utf-8"), re.M)
                 and "draft: false" in p.read_text(encoding="utf-8")]
        if not paths:
            print("Verständnis-Gate: keine neuen Artikel heute – OK.")
            return 0

    all_finds = []
    for p in paths:
        rel = str(p.relative_to(ROOT))
        body = split_body(p.read_text(encoding="utf-8"))
        all_finds += check_article(rel, body, term)

    # dedup
    uniq, seen = [], set()
    for f in all_finds:
        k = (f[0], f[1], f[2][:70])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(f)

    # R8-ANKER-ZIEL ist bewusst NUR weich (semantische Kohärenz ist nicht
    # deterministisch prüfbar – Funde sind Review-Kandidaten, keine Blocker).
    hard_rules = ("R2-KEYWORD-DUMP", "R3-TERMINOLOGIE", "R5-ABSATZ-HART", "R7-INTRO-FORMEL", "R8-URL-LEERZEICHEN")
    hard = [f for f in uniq if f[1] in hard_rules]
    soft = [f for f in uniq if f[1] not in hard_rules]

    lines = [f"# 🧠 TEXTVERSTÄNDNIS-REPORT (textverstaendnis_guard.py)",
             f"**Stand:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · Artikel: {len(paths)}" +
             (" · Engine (nur heute)" if NEW_ONLY else ""),
             "",
             f"**Harte Regeln (R2/R3/R5-hart/R7/R8-URL):** {len(hard)} Funde",
             f"**Weiche Regeln (R4/R5/R8-Anker):** {len(soft)} Funde",
             ""]
    for rel, regel, detail, pos in uniq[:60]:
        lines.append(f"- `{rel}` **{regel}**: {detail}")
    lines.append("")
    lines.append("_Textverständnis: 1 Konzept = 1 Leitbegriff, 1 Absatz = 1 Gedanke, keine Komma-Listen, keine Template-Sprache._")
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    with HISTORY.open("a", encoding="utf-8") as h:
        h.write(json.dumps({"date": today, "hard": len(hard), "soft": len(soft),
                            "articles": len(paths)}, ensure_ascii=False) + "\n")

    if AS_JSON:
        print(json.dumps({"finds": [{"file": f[0], "rule": f[1], "detail": f[2]} for f in uniq]},
                         ensure_ascii=False, indent=2))
        return 1 if hard and NEW_ONLY else 0

    print(f"Verständnis-Audit: {len(paths)} Artikel | hart {len(hard)} · weich {len(soft)}")
    for rel, regel, detail, pos in uniq[:30]:
        mark = "❌" if regel in hard_rules else "⚠️"
        print(f"  {mark} [{regel:>16}] {rel}: {detail[:120]}")
    if NEW_ONLY and hard:
        print("❌ Verständnis-Gate nicht bestanden – harte Verstöße in neuen Artikeln!")
        return 1
    if not uniq:
        print("✅ Keine Verständnis-Funde.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
