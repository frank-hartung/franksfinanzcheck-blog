#!/usr/bin/env python3
# ============================================================
#  PLAGIAT-GUARD – Originalitaets-Kanzlei mit Selbstheilung
#
#  Auftrag (Frank, 12.08.2026): weltbeste Plagiats-Automatik.
#  Was ein Verlags-Plagiatspruefer tatsaechlich leistet (ehrlich):
#
#    P1  SHINGLE-JACCARD ueber das Corpus: 8-Wort-Fenster je Artikel,
#        Aehnlichkeit = |A∩B|/|A∪B|. > 0.30 = Verdacht, > 0.55 = Klon.
#    P2  DUPLIKAT-SAETZE: identischer Satz (> 6 Woerter) in 2+ Artikeln
#        (ausserhalb Boilerplate: CTA-/Disclaimer-Bloecke, Tabellen-
#        Einheiten) → Fund im Report (Aelterer Artikel behaelt Vorrecht).
#    P3  BOILERPLATE-QUOTE: Anteil Template-Text (Marketer-/Shield-CTA,
#        Disclaimer) am Gesamttext > 30 % → Google sieht „duplicated".
#    P4  FINGERPRINT-REGISTRY (Urheber-Beweis): Jeder Artikel wird mit
#        SHA-256 (normalisierter Text) + SimHash-64 + Zeitstempel in
#        data/content_fingerprints.jsonl append-only protokolliert.
#        Bei Streit („die haben von uns kopiert!") beweisen Registry +
#        Git-History unsere Prioroty jedes Mal.
#    P5  Klon-Quarantaene (Selbstheilung): Jaccard > 0.55 → der JUENGERE
#        Artikel wird auf draft:true gesetzt + Kommentar-Zeile angehaengt.
#        Reversibel (draft:false + Registry-Eintrag), nie Datenverlust.
#
#  SABOTAGE-SCHUTZ: 8 eingefrorene Faelle (inkl. Negativ-Faelle!); rot =
#  Exit 2, keine Datei wird angefasst. Idempotent (append-only Registry).
#
#  Aufruf:
#    python3 scripts/plagiat_guard.py            # Report (Exit 0)
#    python3 scripts/plagiat_guard.py --fix      # Quarantaene + Registry
#    python3 scripts/plagiat_guard.py --selftest
#    python3 scripts/plagiat_guard.py --new-only # Engine-Modus
#
#  Ausgabe: PLAGIAT-REPORT.md + data/content_fingerprints.jsonl
#           + data/plagiat_history.jsonl
# ============================================================
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "PLAGIAT-REPORT.md"
FINGERPRINTS = ROOT / "data" / "content_fingerprints.jsonl"
HISTORY = ROOT / "data" / "plagiat_history.jsonl"

DO_FIX = "--fix" in sys.argv
NEW_ONLY = "--new-only" in sys.argv

SHINGLE_N = 8                 # Wort-Fenster-Groesse (Profi-Standard 7-10)
JACCARD_WARN = 0.30           # P1: Verdacht
JACCARD_CLONE = 0.55          # P1: Klon -> Quarantaene
BOILERPLATE_MAX = 0.30        # P3

# Boilerplate-Zonen (Marketer/Shield bauen die absichtlich – kein Plagiat):
# erkannt an Zeilen-Markern, die GANZE Zeile (inkl. Markdown-CTA) zaehlt.
BOILER_LINES = (
    "Schnell-Tipp von FranksFinanzcheck",
    "Dieser Artikel enthält Affiliate-Links",
    "Angebote vergleichen",
    "Partnerlink = Werbung",
    # Affiliate-Disclaimer (identisch in allen Artikeln, vorgeschrieben):
    "erhalten wir eine Provision",
    "für dich entstehen keine Mehrkosten",
    # Pillar-Box-Kanal (baut affiliate_marketer in jedem Artikel unten an):
    "Ratgeber ",                      # z. B. „Weitere Tipps findest du im Ratgeber …"
    "pillar ",                       # Kanalverweis unten (im Pillar-box)
)
def _is_boiler(sentence: str) -> bool:
    low = sentence.lower()
    return any(m.lower() in low for m in BOILER_LINES)
BOILER_RX = re.compile("|".join(re.escape(m) for m in BOILER_LINES), re.I)

WORD_RX = re.compile(r"[a-zäöüß0-9]+")


def normalize(body: str) -> str:
    """Rohtext -> normalisierte Wortfolge (Kleinbuchstaben, ohne Markdown)."""
    t = re.sub(r"```.*?```", " ", body, flags=re.S)
    t = re.sub(r"\[[^\]]*\]\(([^)]*)\)", " ", t)      # Links: Anker+Ziel raus
    t = re.sub(r"[#>*_`|]", " ", t)
    t = t.lower().replace("ß", "ss")
    return " ".join(WORD_RX.findall(t))


def shingles(norm: str, n: int = SHINGLE_N) -> set:
    w = norm.split()
    if len(w) < n:
        return {" ".join(w)} if w else set()
    return {" ".join(w[i:i+n]) for i in range(len(w)-n+1)}


def simhash(norm: str) -> int:
    """64-bit SimHash des normalisierten Textes (Aehnlichkeits-Fingerprint)."""
    feats = Counter_hash = {}
    v = [0] * 64
    for shingle in shingles(norm, 3):
        h = int(hashlib.md5(shingle.encode()).hexdigest(), 16)
        for i in range(64):
            v[i] += 1 if (h >> i) & 1 else -1
    fp = 0
    for i in range(64):
        if v[i] > 0:
            fp |= 1 << i
    return fp


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def artikel_daten():
    """Liste: (slug, pfad, date, body_normalisiert, body_raw)."""
    from post_utils import list_post_paths
    out = []
    for p in sorted(list_post_paths()):
        slug = os.path.basename(os.path.dirname(p))
        s = Path(p).read_text(encoding="utf-8")
        parts = s.split("---", 2)
        body = parts[2] if len(parts) == 3 else s
        m = re.search(r"^date:\s*([\d-]+)", parts[1] if len(parts) == 3 else "", re.M)
        datum = m.group(1) if m else "1970-01-01"
        out.append({"slug": slug, "pfad": p, "date": datum,
                    "raw": s, "body": body, "norm": normalize(body)})
    return out


def find_duplikat_saetze(artikel):
    """P2: Gleiche Saetze (>6 Woerter) in mindestens 2 Artikeln."""
    satz_rx = re.compile(r"(?<=[.!?])\s+")
    besitzer = {}
    for a in artikel:
        for s in satz_rx.split(a["body"]):
            if _is_boiler(s):
                continue
            w = WORD_RX.findall(s.lower())
            if len(w) >= 7:
                h = " ".join(w)
                besitzer.setdefault(h, set()).add(a["slug"])
    out = {}
    for txt, slugs in besitzer.items():
        if len(slugs) < 2:
            continue
        # Boilerplate-Schutz: der ROH-Satz (vor Normalisierung)
        roh = txt  # txt ist hier bereits normalisiert-word-joined
        out[txt] = slugs
    return out


def boilerplate_quote(body: str) -> float:
    """P3: Anteil Boilerplate-Text (zeilenbasiert ueber Marker)."""
    lines = body.splitlines()
    total = max(1, sum(len(l) for l in lines))
    bp = sum(len(l) for l in lines if _is_boiler(l))
    return bp / total


# ------------------------------------------------------------ Selbsttest
def selftest() -> list:
    fehler = []
    a = "sparen lohnt sich immer " * 40
    b = a
    c = "ganz anderes thema ueber aktien " * 40
    # Fall 1: Klon wird als Klon erkannt
    if jaccard(shingles(normalize(a)), shingles(normalize(b))) < JACCARD_CLONE:
        fehler.append("Fall 1: Klone nicht erkannt")
    # Fall 2: Verschiedenes bleibt unter Warnschwelle
    if jaccard(shingles(normalize(a)), shingles(normalize(c))) > JACCARD_WARN:
        fehler.append("Fall 2: Verschiedene Texte als Duplikat gemeldet")
    # Fall 3: SimHash-Distanz: Klon 0, Fremd > 20
    if hamming(simhash(normalize(a)), simhash(normalize(b))) != 0:
        fehler.append("Fall 3: SimHash-Klon != 0")
    if hamming(simhash(normalize(a)), simhash(normalize(c))) < 15:
        fehler.append("Fall 4: SimHash Fremd < 15 (zu unscharf)")
    # Fall 5: Boilerplate-Satz ist KEIN Duplikat-Satz-Fall
    arts = [{"slug": "a1", "body": "Schnell-Tipp von FranksFinanzcheck: vergleichen Sie jetzt die Tarife sofort."},
            {"slug": "a2", "body": "Schnell-Tipp von FranksFinanzcheck: vergleichen Sie jetzt die Tarife sofort."}]
    if find_duplikat_saetze(arts):
        fehler.append("Fall 5: Boilerplate fälschlich als Duplikat gemeldet")
    arts2 = [{"slug": "b1", "body": "Beim Abschluss über einen Link erhalten wir eine Provision."},
             {"slug": "b2", "body": "Beim Abschluss über einen Link erhalten wir eine Provision."}]
    if find_duplikat_saetze(arts2):
        fehler.append("Fall 5b: Disclaimer boj us Boilernicht ausgeschlossen")
    # Fall 6: Echter Satz in zwei Artikeln WIRD gemeldet
    arts = [{"slug": "a1", "body": "Die beste Sparquote liegt bei zwanzig Prozent deines Nettoeinkommens im Jahr."},
            {"slug": "a2", "body": "Andere Einleitung. Die beste Sparquote liegt bei zwanzig Prozent deines Nettoeinkommens im Jahr."}]
    if not find_duplikat_saetze(arts):
        fehler.append("Fall 6: echter Duplikat-Satz nicht erkannt")
    # Fall 7: Boilerplate-Quote rechnet
    body = ("Echter Text " * 50 + "\n"
            + "Schnell-Tipp von FranksFinanzcheck: Jetzt Angebote vergleichen.\n" * 20)
    q = boilerplate_quote(body)
    if not (0.35 < q < 0.9):
        fehler.append(f"Fall 7: Quote falsch ({q:.2f})")
    # Fall 8: Schwellen nicht heimlich aufgeweicht
    if (SHINGLE_N, JACCARD_WARN, JACCARD_CLONE, BOILERPLATE_MAX) != (8, 0.30, 0.55, 0.30):
        fehler.append("Fall 8: Schwellen sabotiert/manipuliert")
    return fehler


# ------------------------------------------------------------ Registry
def registry_stand():
    """letzte bekannte Fingerprints: {slug: {"sha": ..., "ts": ...}}"""
    reg = {}
    if FINGERPRINTS.exists():
        for line in FINGERPRINTS.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    r = json.loads(line)
                    reg.setdefault(r["slug"], r)
                    if r["ts"] > reg[r["slug"]]["ts"]:
                        reg[r["slug"]] = r
                except Exception:
                    continue
    return reg


def registry_append(records):
    os.makedirs(FINGERPRINTS.parent, exist_ok=True)
    with open(FINGERPRINTS, "a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def quarantaene(a):
    """Selbstheilung P5: juengerer Artikel -> draft:true + Vermerk (reversibel)."""
    s = a["raw"]
    if re.search(r"^draft:\s*true", s, re.M):
        return False  # schon in Quarantaene
    if re.search(r"^draft:\s*false", s, re.M):
        s = re.sub(r"^draft:\s*false", "draft: true", s, count=1, flags=re.M)
    else:
        parts = s.split("---", 2)
        if len(parts) == 3:
            s = parts[0] + "---" + parts[1] + "draft: true\n" + "---" + parts[2]
        else:
            return False
    s += ("\n\n<!-- PLAGIAT-QUARANTAENE (plagiat_guard.py, "
          f"{datetime.now(timezone.utc):%Y-%m-%d}): Jaccard > {JACCARD_CLONE} "
          "zu aelterem Artikel. Rueckholung: draft:false + begruenden im Commit. -->\n")
    Path(a["pfad"]).write_text(s, encoding="utf-8")
    return True


# ------------------------------------------------------------ Lauf
def main():
    if "--selftest" in sys.argv:
        stf = selftest()
        print("✅ Plagiat-Selbsttest: 8 Faelle gruen." if not stf
              else "🛑 SELBSTTEST ROT:\n" + "\n".join(stf))
        return 0 if not stf else 2

    stf = selftest()
    if stf:
        print("🛑 PLAGIAT-SELBSTTEST ROT – Sabotage verhindert, kein Schreiben:")
        print("\n".join("  " + f for f in stf))
        return 2

    arts = artikel_daten()
    if NEW_ONLY:
        today = datetime.now(timezone.utc).date().isoformat()
        arts = [a for a in arts if a["date"].startswith(today)]
    print(f"Artikel: {len(arts)} – Fingerprints & Paarvergleich …")

    # Fingerprints berechnen + Registry fortschreiben (nur bei Veraenderung!)
    reg_old = registry_stand()
    registry_new = []
    fps = {}
    for a in arts:
        sha = hashlib.sha256(a["norm"].encode()).hexdigest()
        sim = simhash(a["norm"])
        fps[a["slug"]] = {"sha": sha, "sim": sim,
                          "shingles": shingles(a["norm"]),
                          "date": a["date"]}
        if reg_old.get(a["slug"], {}).get("sha") != sha:
            registry_new.append({
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "slug": a["slug"], "sha256": sha, "simhash": sim,
                "words": len(a["norm"].split())})

    # P1: Paarvergleich (69 Artikel → 2.300 Paare, billig)
    paare_warn, paare_klon = [], []
    slugs = list(fps)
    for i in range(len(slugs)):
        for j in range(i + 1, len(slugs)):
            ja = jaccard(fps[slugs[i]]["shingles"], fps[slugs[j]]["shingles"])
            if ja > JACCARD_WARN:
                aelter = slugs[i] if fps[slugs[i]]["date"] <= fps[slugs[j]]["date"] else slugs[j]
                juenger = slugs[j] if aelter == slugs[i] else slugs[i]
                rec = {"a": aelter, "b": juenger, "j": round(ja, 3),
                       "ham": hamming(fps[slugs[i]]["sim"], fps[slugs[j]]["sim"])}
                (paare_klon if ja > JACCARD_CLONE else paare_warn).append(rec)

    # P2: Duplikat-Saetze
    dups = find_duplikat_saetze(arts)

    # P3: Boilerplate-Quote
    bp_funde = [(a["slug"], boilerplate_quote(a["body"]))
                for a in arts if boilerplate_quote(a["body"]) > BOILERPLATE_MAX]

    # P5: Klon-Quarantaene (heilend)
    gebannt = []
    if DO_FIX:
        registry_append(registry_new)
        for rec in paare_klon:
            a = next(x for x in arts if x["slug"] == rec["b"])
            if quarantaene(a):
                gebannt.append(rec["b"])

    lines = ["# 🧬 PLAGIAT-REPORT (plagiat_guard.py)", "",
             f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · "
             f"Modus: {'FIX/QUARANTAENE' if DO_FIX else 'REPORT'}",
             f"**Artikel:** {len(arts)} · **Fingerprints neu:** {len(registry_new)}",
             "",
             f"| Stufe | Schwelle | Funde | Aktion |",
             f"|---|---|---|---|",
             f"| P1 Verdacht | Jaccard > {JACCARD_WARN} | {len(paare_warn)} | Report |",
             f"| P1 Klon | Jaccard > {JACCARD_CLONE} | {len(paare_klon)} | Quarantaene |",
             f"| P2 Duplikat-Saetze | identisch, ≥7 W. | {len(dups)} | Report |",
             f"| P3 Boilerplate | > {BOILERPLATE_MAX*100:.0f} % | {len(bp_funde)} | Report |",
             f"| P4 Registry-Eintraege | — | {len(registry_new)} | append-only |",
             ""]
    if gebannt:
        lines += [f"### 🚫 Quarantaene (SELBST GEHEILT)", ""]
        for b in gebannt:
            lines.append(f"- `{b}` → draft:true (juengerer Artikel; reversibel)")
        lines.append("")
    if paare_warn:
        lines.append("### ⚠️ Verdachts-Paare (Top 12)")
        for r in sorted(paare_warn, key=lambda x: -x["j"])[:12]:
            lines.append(f"- `{r['a']}` ↔ `{r['b']}` · Jaccard {r['j']} · SimHash-Δ {r['ham']}")
        lines.append("")
    if paare_klon:
        lines.append("### 🚨 KLONE (juengerer geht in Quarantaene)")
        for r in paare_klon:
            lines.append(f"- `{r['a']}` (bleibt) ⟷ `{r['b']}` (gebannt) · Jaccard {r['j']}")
        lines.append("")
    if not (paare_warn or paare_klon or dups or bp_funde):
        lines.append("🎉 Kein interner Content-Diebstahl, keine Klone, Boilerplate im Korridor.")
    for txt, slugs_ in list(dups.items())[:10]:
        short = " ".join(txt.split()[:9]) + "…"
        lines.append(f"- P2 Satz-Duplikat ({len(slugs_)}x): „{short}“ in: {', '.join(sorted(slugs_))}")
    if bp_funde:
        lines += ["", "### P3 Boilerplate-Ausreisser"]
        for slug, q in bp_funde:
            lines.append(f"- `{slug}`: {q*100:.0f} % Template-Text")
    lines += ["", "---",
              "_Externe Plagiate pruefen wir nicht (ToS). Unsere Registry beweist "
              "URHEBERSCHAFT mit Zeitstempel – bei Fremdklau ist das der Beweis._"]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    os.makedirs(HISTORY.parent, exist_ok=True)
    with open(HISTORY, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "posts": len(arts), "warn": len(paare_warn), "klone": len(paare_klon),
            "dup_saetze": len(dups), "bp": len(bp_funde),
            "registry_neu": len(registry_new)}, ensure_ascii=False) + "\n")

    print("\n".join(lines[:13]))
    print(f"\n🧬 Registry: {len(registry_new)} neue Fingerprints · "
          f"Klone: {len(paare_klon)} · Verdacht: {len(paare_warn)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
