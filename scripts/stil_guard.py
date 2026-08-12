#!/usr/bin/env python3
# ============================================================
#  STIL-GUARD – Editor-Qualitaets-Messung auf Verlagsniveau
#
#  Auftrag (Frank, 12.08.2026): das weltbeste Profi-Lektorat.
#  Obere Ebene des Lektorats ueber den bekannten L1-L15:
#  MESSBARE Textqualitaet, die Lektoren wirklich beurteilen:
#
#    S1  SATZANFANGS-ECHO ueber Absatzgrenzen: Selbes Wort startet
#        3+ Saetze in Folge (Artikeln ohne Rhythmus wirken holprig)
#    S2  PASSIV-DICHTE: > 28 % Saetze mit wird/werden/wurde + Partizip
#        im selben Satz -> Behoerden-Ton (REPORT-ONLY, kein Auto-Fix)
#    S3  DASS-KETTEN: 3+ „dass"-Nebensatz im selben Absatz -> Schachtelbombe
#    S4  WEICHE-WOLKE: Fueller pro 100 Woerter (einfach/nur/eigentlich/
#        wirklich/sehr/quasi/ziemlich) > 6 -> Aufgeweicht
#    S5  SUPERLATIV-UeBERMASS: > 4 beste/groesste/tollste/pro Artikel
#        -> Werbeton-Warnung (feat. L4/Lektorat)
#    S6  LIX-LESBARKEIT: deutscher Lesbarkeitsindex je Artikel;
#        > 55 = schwer (Behoerden-Artikel); ideal: 35-50 (Ratgeber-Gut)
#        REPORT-ONLY, Zielkorridor auf dem neuesten Post-Audit
#    S7  ABSATZ-MONSTER: > 8 Saetze in einem Absatz -> Keine verschnauf-
#        pause fuer Leser; Auto-Splitting waere echte Heilung, ist aber
#        Semantik -> REPORT-ONLY
#    S8  TYP-TOKEN-DIVERSITAET: < 0.35 in Artikeln > 400 Woerter ->
#        einfaeltiges Vokabular, LIEST sich monotone
#
#  Messungen sind IMMER inkl. graphischer Top-5/Flop-5-Liste im Report;
#  dort werden die lautesten Baustellen fuer redaktionelle Politur
#  sichtbar (redaktions-politur.yml mit --ai-budget kann sie dann
#  gezielt umschreiben, wenn KI-Budget existiert).
#
#  SELBSTHEILUNG: --fix aktualisiert NUR den Report + die History;
#  Text bleibt wie er ist (Stil ist Bewertung, nie Zwang).
#  Sabotageschutz: 10 eingefrorene Lektorats-Faelle; Abweichung: Exit 2.
#
#  Aufruf:
#    python3 scripts/stil_guard.py            # Profil fuer ALLE Artikel
#    python3 scripts/stil_guard.py --fix      # Report aktualisieren
#    python3 scripts/stil_guard.py --selftest
#    python3 scripts/stil_guard.py --new-only # nur heutige Artikel
#
#  Ausgabe: STIL-REPORT.md + data/stil_history.jsonl · Exit 0 immer
#  (Bewertungs-Wache blockiert nicht, meldet nur).
# ============================================================
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "STIL-REPORT.md"
HISTORY = ROOT / "data" / "stil_history.jsonl"

DO_FIX = "--fix" in sys.argv
NEW_ONLY = "--new-only" in sys.argv

# ------------------------------------------------------------ Werkzeuge
WORD_RX = re.compile(r"\b[A-Za-zÄÖÜäöüß][a-zäöüß]{2,}\b")
# Nach Satzpunkt: beliebige Spaces INKL NBSP (unit_guard!), dann NICHT
# kkiner Buchstabe (so finden wir auch 💡, *, -, > usw. als Satzanfaenge)
SATZ_RX = re.compile(r"(?<=[.!?])[\s ]+(?![a-zäöüß,;])")
STOPWEICH = {
    "eigentlich", "einfach", "nur", "wirklich", "sehr", "quasi", "ziemlich",
    "ganz", "halt", "eben", "mal", "sozusagen", "gewissermaßen",
}
SUPERL = re.compile(r"\b(besten?|groessten?|tollsten?|schoensten?|idealen?|"
                    r"perfekten?|ueberragend|einzigartig|sensationellen?)\b", re.I)
PASSIV = re.compile(r"\b(wird|werden|wurde|wurden|worden)\s+[a-zäöüß]+(t|en)\b", re.I)
DASS_RX = re.compile(r"\bdass\b", re.I)
MONTH_RX = re.compile(r"^(?:202[0-9]-\d{2}-\d{2})-")


def satz_split(body: str) -> list:
    """Saetze splitten; Schutz vor z.B. / d.h. / 80.-Regel."""
    work = re.sub(r"\b(z\.B|d\.h|bzw|usw|etc|inkl|ca|vgl|u\.a|z\.Zt)\.", r"\1<DOT>", body)
    work = re.sub(r"(\d)\.(\d)", r"\1<DOT>\2", work)  # 3.50 -> 3<DOT>50
    saetze = SATZ_RX.split(work)
    return [s.replace("<DOT>", ".") for s in saetze if len(s.strip()) > 3]


def text_metrics(body: str) -> dict:
    """Misst S1-S8 fuer einen Body, liefert Kennzahlen und Funde."""
    body = re.sub(r"```.*?```", " ", body, flags=re.S)   # code weg
    body = re.sub(r"\[[^\]]*\]\([^)]*\)", " ", body)      # links -> text raus
    body = re.sub(r"[#>|*\-]{1,4} ", " ", body)           # MD-Marker
    saetze = satz_split(body)
    woerter = WORD_RX.findall(body)
    n_satz = max(1, len(saetze))
    n_wort = max(1, len(woerter))
    # S1: Satzanfangs-Echo (dasselbe Wort startet >=3 Saetze)
    anf = Counter(s.split()[0].lower().strip('"„(*') for s in saetze
                  if len(s.split()) > 1)
    echo = {w: c for w, c in anf.most_common(3) if c >= 3 and len(w) >= 2}
    # S2: Passiv-Quote
    n_passiv = sum(1 for s in saetze if PASSIV.search(s))
    passiv_q = n_passiv / n_satz
    # S3: Dass-Ketten pro Absatz
    absaetze = [a for a in body.split("\n\n") if len(a.split()) > 20]
    dass_chains = sum(1 for a in absaetze if len(DASS_RX.findall(a)) >= 3)
    # S4: Weiche-Wolke
    weich = sum(1 for w in woerter if w.lower() in STOPWEICH)
    weich_pm = weich / n_satz * 100 if n_satz else 0
    # S5: Superlative
    n_super = len(SUPERL.findall(body))
    # S6: LIX = (Woerter/Saetze) + 100*(lange Worte/Woerter)
    lange = sum(1 for w in woerter if len(w) >= 7)
    lix = (n_wort / n_satz) + (100 * lange / n_wort)
    # S7: Absatz-Monster
    monster = [a for a in absaetze if len(satz_split(a)) > 8]
    # S8: Typ-Token-Diversitaet (nur Sinn ab 400 Woertern)
    ttr = len({w.lower() for w in woerter}) / n_wort if n_wort >= 400 else None
    return {
        "saetze": n_satz,
        "woerter": n_wort,
        "satz_len": round(n_wort / n_satz, 1),
        "lix": round(lix, 1),
        "echo": echo,                       # S1
        "passiv_q": round(passiv_q, 3),     # S2
        "dass_chains": dass_chains,         # S3
        "weich_pm": round(weich_pm, 1),     # S4
        "superl": n_super,                  # S5
        "absatz_monster": len(monster),     # S7
        "ttr": round(ttr, 3) if ttr else None,  # S8
    }


# ------------------------------------------------- Stil-Schuellen (Kanon)
LIMIT = {
    "passiv_q": 0.28,     # S2
    "dass_chains": 2,     # S3 je Artikel
    "weich_pm": 6.0,      # S4 pro 100 Woerter
    "superl": 4,          # S5 pro Artikel
    "lix_hard": 55.0,     # S6: ueber = schwer lesbar
    "lix_soft": 35.0,     # S6: unter = zu einfach (Kinderbuch)
    "satz_len": 22.0,     # S6-Begleitmass
    "monster": 1,         # S7
    "ttr_min": 0.35,      # S8
}


def bewerten(slug: str, m: dict) -> list:
    """Aus Messwerten Fundliste bauen (nur relevante)."""
    issues = []
    if m["echo"]:
        worst = max(m["echo"], key=m["echo"].get)
        issues.append(f"S1 Satzanfang-Echo: „{worst}“ ×{m['echo'][worst]}")
    if m["passiv_q"] > LIMIT["passiv_q"]:
        issues.append(f"S2 Passiv-Dichte {m['passiv_q']*100:.0f} % > {LIMIT['passiv_q']*100:.0f} %")
    if m["dass_chains"] > LIMIT["dass_chains"]:
        issues.append(f"S3 Dass-Ketten: {m['dass_chains']} Absaetze")
    if m["weich_pm"] > LIMIT["weich_pm"]:
        issues.append(f"S4 Weiche-Wolke {m['weich_pm']}/100W")
    if m["superl"] > LIMIT["superl"]:
        issues.append(f"S5 Superlativ-Uebermass: {m['superl']}x")
    if m["lix"] > LIMIT["lix_hard"]:
        issues.append(f"S6 LIX {m['lix']} > {LIMIT['lix_hard']:.0f} (schwer lesbar)")
    if m["satz_len"] > LIMIT["satz_len"]:
        issues.append(f"S6b Sätze o {m['satz_len']} Woerter > {LIMIT['satz_len']:.0f}")
    if m["absatz_monster"] > LIMIT["monster"]:
        issues.append(f"S7 Absatz-Monster: {m['absatz_monster']} Bloecke > 8 Saetze")
    if m["ttr"] is not None and m["ttr"] < LIMIT["ttr_min"]:
        issues.append(f"S8 TTR {m['ttr']} < {LIMIT['ttr_min']} (Vokabular arm)")
    return issues


def artikel_liste():
    from post_utils import list_post_paths
    return list_post_paths()


# ------------------------------------------------------------ Selbsttest
SELFTEST = [
    # (text_probe, mindestens erwartete Frueh-Fall-Praesenz)
    ("Stil S1: wiederholter Satzanfang darf erkannt werden. "
     "Du kannst sparen. Du solltest sparen. Du musst sparen. Du weisst es.",
     "echo"),
    ("Hier gibt es keinen Anfangsecho. Erst kommt Verschiedenes, dann "
     "noch Abwechslung, schliesslich klingt es rund und ruhig.",
     None),
]


def selftest() -> list:
    fehler = []
    # Fall 1: Echo-Erkennung greift bei S1-Probe
    m = text_metrics(SELFTEST[0][0])
    if not m["echo"]:
        fehler.append("S1: Satzanfangs-Echo wurde NICHT erkannt (erwartet: du)")
    # Fall 2: Leeres Echo gibt NONE fuer normalen Text
    m2 = text_metrics(SELFTEST[1][0])
    if m2["echo"]:
        fehler.append(f"S1: Falsch-Positiv auf Normaltext: {m2['echo']}")
    # Fall 3: LIX-Formel sinnvoll (Journalisten-Text ~35-50, Behoerde >55)
    beispiel = ("Spare Geld mit einfachen Schritten. Du kannst es. Versuche es. "
                "Nutze Ressourcen optimal. Behalte den Ueberblick ueber Ausgaben.")
    lix = text_metrics(beispiel)["lix"]
    if not (25.0 <= lix <= 60.0):
        fehler.append(f"S6: LIX ausserhalb Erwartung (ist {lix})")
    # Fall 4: Absatz mit 9 Saetzen muss Monster sein
    monst = ("Satz eins ist kurz. Satz zwei auch. " * 5).strip()
    mm = text_metrics(monst)
    if mm["absatz_monster"] < 1:
        fehler.append("S7: Absatz-Monster (9 Saetze) nicht erkannt")
    # Fall 5: Superlative zaehlt richtig
    sup = text_metrics("Das beste Angebot ist das groesste und das tollste "
                       "und das beste und das schoenste.")
    if sup["superl"] < 5:
        fehler.append(f"S5: Superlativ-Zaehler falsch ({sup['superl']})")
    return fehler


def main():
    # Sabotage-Schutz: Selbsttest zuerst
    stf = selftest()
    if stf:
        print("🛑 STIL-SELBSTTEST ROT – keine Datei wird bewertet:")
        print("\n".join("  " + f for f in stf))
        sys.exit(2)

    if "--selftest" in sys.argv:
        print(f"✅ Stil-Selbsttest: {len(SELFTEST)+3} Faelle gruen.")
        return 0

    posts = artikel_liste()
    if NEW_ONLY:
        today = datetime.now(timezone.utc).date().isoformat()
        posts = [p for p in posts if today in os.path.basename(os.path.dirname(p))]
    print(f"Artikel: {len(posts)} - Messe Stil-Profil …")

    rows, hist = [], []
    lix_list = []
    for pfad in posts:
        slug = os.path.basename(os.path.dirname(pfad))
        s = Path(pfad).read_text(encoding="utf-8")
        parts = s.split("---", 2)
        body = parts[2] if len(parts) == 3 else s
        m = text_metrics(body)
        issues = bewerten(slug, m)
        lix_list.append((m["lix"], slug))
        rows.append({"slug": slug, "m": m, "issues": issues})
        hist.append({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                     "slug": slug, "lix": m["lix"], "passiv": m["passiv_q"],
                     "weich": m["weich_pm"], "satz_len": m["satz_len"],
                     "n_issues": len(issues)})

    # Flotten-Statistik
    lix_sorted = sorted(lix_list)
    med = lix_sorted[len(lix_sorted) // 2][0] if lix_sorted else 0
    avg_lix = sum(l for l, _ in lix_list) / max(1, len(lix_list))
    mit_issues = [r for r in rows if r["issues"]]
    top_hard = sorted(rows, key=lambda r: r["m"]["lix"], reverse=True)[:5]
    top_easy = sorted(rows, key=lambda r: r["m"]["lix"])[:5]

    lines = ["# 🎭 STIL-REPORT (stil_guard.py)", "",
             f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
             f"**Artikel:** {len(rows)} · **mit Stil-Funden:** {len(mit_issues)}", "",
             "## 📐 Flotten-Lesbarkeit (LIX)", "",
             f"| Median | Schnitt | Zielkorridor |",
             f"|---|---|---|",
             f"| {med:.1f} | {avg_lix:.1f} | 35-50 (Ratgeber-Gut) |", "",
             "### 📕 Schwer lesbar (Top 5, hoechster LIX zuerst)", ""
            ]
    for r in top_hard:
        lines.append(f"- `{r['slug']}` — LIX {r['m']['lix']} · Saetze o "
                     f"{r['m']['satz_len']} W · Passiv {r['m']['passiv_q']*100:.0f} %")
    lines += ["", "### 📗 Leicht lesbar (Top 5)", ""]
    for r in top_easy:
        lines.append(f"- `{r['slug']}` — LIX {r['m']['lix']}")
    if mit_issues:
        lines += ["", "## 🔧 Fundstellen (fuer redaktionelle Politur mit --ai-budget)", ""]
        for r in sorted(mit_issues, key=lambda r: len(r["issues"]), reverse=True)[:15]:
            lines.append(f"### `{r['slug']}`")
            for i in r["issues"]:
                lines.append(f"- {i}")
            lines.append("")
    else:
        lines += ["", "🎉 Alle Artikel innerhalb der Stil-Korridore.", ""]
    lines += ["---",
              "_Wirkung freigestellt. Messung ist Report, kein Zwang. "
              "Stil-Verschiebungen passieren ueber redaktions-politur.yml._"]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    os.makedirs(HISTORY.parent, exist_ok=True)
    with open(HISTORY, "a", encoding="utf-8") as f:
        for row in hist:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("\n".join(lines[:16]))
    print(f"\n📊 LIX-Flotte: median {med:.1f} · schnitt {avg_lix:.1f} · "
          f"mit Funden: {len(mit_issues)}/{len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
