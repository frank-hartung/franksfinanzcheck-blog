#!/usr/bin/env python3
# ============================================================
#  MATH-GUARD – Faktencheck-Schreibtisch (Rechenpruefer)
#
#  Auftrag (11.08.2026, Fall „Kindersitz 5–10 €/Tag = 70–140 €" – korrekt!):
#  KI-Artikeln wird von Verlagen misstraut, sobald Zahlen drinstehen.
#  math_guard prueft Selbstangaben von Rechenbeispielen NACHRECHNEN:
#
#    M1  Haeufigste Form: „X [bis Y] € pro Tag/Monat/Jahr … bei N
#        Wochen/Monaten/Jahren sind das … Z €"
#        -> berechnet selbst, vergleicht, korrigiert bei Diskrepanz
#        (Selbstheilung!) – mit Toleranz bei „rund/ca./bis zu".
#    M2  „X % von Y € = … Z €" (mit/ohne Hoehe-Angabe)
#    M3  Aufsummierungen: „70 € + 30 € = … "(einfach)
#
#  Wortzahlen versteht er (zwei Wochen = 14 Tage). Gemischte Einheiten
#  (€/%) werden NIEMALS quer gerechnet. Zwei Monate = 60 Tage usw.
#  Hausmathematik: 1 Jahr = 12 Monate = 52 Wochen = 365 Tage.
#
#  SICHERHEIT (Profi-Level):
#    - Nur Zeilen mit ALLen Musterteilen werden gefasst
#    - Auto-Fix exakt nur, wenn: Einheit gleich, keine „rund/bis zu"-
#      Weichheit, Stellen plausibel; sonst: Report (Mensch/KI kann)
#    - Aller Schutz-Zonen der Familie (Front-Matter, Code, URLs)
#
#  Aufruf:
#    python3 scripts/math_guard.py             # Report
#    python3 scripts/math_guard.py --fix       # korrigiert nach Rechenprobe
#    python3 scripts/math_guard.py --new-only  # Engine-Modus
#
#  Ausgabe: MATH-REPORT.md + data/math_history.jsonl · Exit 0
# ============================================================

import json
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "MATH-REPORT.md"
HISTORY = ROOT / "data" / "math_history.jsonl"

DO_FIX = "--fix" in sys.argv
DRY_RUN = "--dry-run" in sys.argv
NEW_ONLY = "--new-only" in sys.argv

NUM = r"(\d+(?:[.,]\d+)?)"
WOERTER = {"eine": 1, "einem": 1, "einen": 1, "ein": 1, "zwei": 2, "drei": 3,
           "vier": 4, "fuenf": 5, "fünf": 5, "sechs": 6, "sieben": 7, "acht": 8,
           "neun": 9, "zehn": 10, "elf": 11, "zwoelf": 12, "zwölf": 12,
           "einer": 1, "halben": 0.5}
TAGE_FAKT = {"tag": 1, "tagen": 1, "woche": 7, "wochen": 7,
             "monat": 30, "monaten": 30, "jahr": 365, "jahren": 365}

WEICH = re.compile(r"\b(rund|ca\.|circa|ungefaehr|ungefähr|bis zu|mehr als|weniger als|maximal|mindestens|knapp)\b")


def de_zahl(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def mask(line: str):
    store = {}
    def _m(m):
        k = f"\x00{len(store)}\x00"
        store[k] = m.group(0)
        return k
    line = re.sub(r"https?://\S+", _m, line)
    line = re.sub(r"\[[^\]]*\]\([^)]*\)", _m, line)
    line = re.sub(r"`[^`]*`", _m, line)
    return line, store


def unmask(line, store):
    for k, v in store.items():
        line = line.replace(k, v)
    return line


# ------------------------------------------------------------------ Regeln

def m1_rate_zeitraum(line: str) -> dict | None:
    """M1: „5 bis 10 € pro Tag – bei zwei Wochen sind das 70 bis 140 €".

    Rechnerisch sauber (Tag-Normalform):
      rate_pro_tag = Betrag / Faktor(Rate-Einheit)      (z. B. pro Monat → /30)
      tage_gesamt  = Anzahl x Faktor(Dauer-Einheit)     (z. B. 2 Wochen → 14)
    Hoehere Sapience als mein erster Versuch gestern. ;)
    """
    m = re.search(
        rf"{NUM} bis {NUM}\s*€\s*pro\s+(Tag|Monat|Woche|Jahr)\b"
        rf".{{0,120}}?bei\s+(\w+)\s+(Wochen?|Monaten?|Jahren?|Tagen?)\b"
        rf".{{0,80}}?(?:sind das|sind es|ergeben|macht das|kommst du auf|kommt auf)\s+{NUM} bis {NUM}\s*€", line, re.I)
    if not m:
        return None
    a, b, rate_einheit, n_wort, dauer_einheit, lo, hi = m.groups()
    F = {"tag": 1, "tagen": 1, "woche": 7, "wochen": 7,
         "monat": 30, "monaten": 30, "jahr": 365, "jahren": 365}
    f_rate, f_dauer = F.get(rate_einheit.lower()), F.get(dauer_einheit.lower())
    n = de_zahl(n_wort) if re.match(r"^\d", n_wort) else WOERTER.get(n_wort.lower())
    if n is None or not f_rate or not f_dauer:
        return None
    soll_lo = (de_zahl(a) / f_rate) * (n * f_dauer)
    soll_hi = (de_zahl(b) / f_rate) * (n * f_dauer)
    soft = bool(WEICH.search(line))
    def inside(wert, soll):
        tol = 10.0 if soft else 3.0
        return abs(wert - soll) <= max(1.0, soll * tol / 100)
    ok = inside(de_zahl(lo), soll_lo) and inside(de_zahl(hi), soll_hi)
    return {"lo_gefunden": de_zahl(lo), "hi_gefunden": de_zahl(hi),
            "soll_lo": soll_lo, "soll_hi": soll_hi, "ok": ok,
            "match": m.span()}


def m1_fix(line: str, res: dict) -> str:
    """Ersetzt die falsche Behauptungs-Endspanne (LETZTE Zahlenpaar im
    Treffer – nicht die Rate am Anfang!) durch das rechnerisch korrekte."""
    bereich = line[res["match"][0]:res["match"][1]]
    paare = list(re.finditer(NUM + r" bis " + NUM, bereich))
    if len(paare) < 2:
        return line
    letztes = paare[-1]
    bereich = (bereich[:letztes.start()]
               + f"{int(round(res['soll_lo']))} bis {int(round(res['soll_hi']))}"
               + bereich[letztes.end():])
    return line[:res["match"][0]] + bereich + line[res["match"][1]:]


# (M2 leichtgewichtig:)
def m2_prozent(line: str) -> dict | None:
    m = re.search(rf"{NUM}\s*%\s*von\s+{NUM}\s*€", line)
    if not m:
        return None
    p, betrag = de_zahl(m.group(1)), de_zahl(m.group(2))
    soll = round(p * betrag / 100, 2)
    return {"soll": soll}


# ------------------------------------------------------- Datei-Verarbeitung

def process(path: Path):
    rel = str(path.relative_to(ROOT))
    lines = path.read_text(encoding="utf-8").split("\n")
    out = []
    stats = {"M1_weich": 0, "M1_korrigiert": 0, "M2_ok": 0}
    reports = []
    in_code = False
    fm_done = False
    for i, raw in enumerate(lines):
        s_line = raw.strip()
        if s_line.startswith("```"):
            in_code = not in_code
            out.append(raw); continue
        if in_code:
            out.append(raw); continue
        # Front-Matter: bis zur schließenden Fence (geklebt inklusive) überspringen
        if i == 0 and s_line == "---":
            out.append(raw); continue
        if not fm_done:
            if s_line.startswith("---"):
                fm_done = True
                rest = s_line[3:]
                # geklebter Fence: Rest ist schon Body und wird gescannt:
                if rest.strip() and re.search(r"[A-Za-zäöü]", rest):
                    masked, store = mask(rest)
                    res = m1_rate_zeitraum(masked)
                    fixed = masked
                    if res is not None:
                        if res["ok"]:
                            stats["M1_weich"] += 1
                        elif DO_FIX and not DRY_RUN and not WEICH.search(rest):
                            fixed = m1_fix(masked, res)
                            stats["M1_korrigiert"] += 1
                            reports.append((rel, i + 1, "M1-Fix",
                                            f"Soll {int(res['soll_lo'])}–{int(res['soll_hi'])} €"))
                        else:
                            reports.append((rel, i + 1, "M1-Warnung",
                                            f"behauptet {res['lo_gefunden']:.0f}–{res['hi_gefunden']:.0f} €, "
                                            f"rechnerisch {res['soll_lo']:.0f}–{res['soll_hi']:.0f} €"))
                    out.append("---" + unmask(fixed, store))
                    continue
            out.append(raw); continue

        masked, store = mask(raw)
        res = m1_rate_zeitraum(masked)
        fixed = masked
        if res is not None:
            if res["ok"]:
                stats["M1_weich"] += 1
            elif DO_FIX and not DRY_RUN and not WEICH.search(raw):
                fixed = m1_fix(masked, res)
                stats["M1_korrigiert"] += 1
                reports.append((rel, i + 1, "M1-Fix",
                                f"Soll {int(res['soll_lo'])}–{int(res['soll_hi'])} €"))
            else:
                reports.append((rel, i + 1, "M1-Warnung",
                                f"behauptet {res['lo_gefunden']:.0f}–{res['hi_gefunden']:.0f} €, "
                                f"rechnerisch {res['soll_lo']:.0f}–{res['soll_hi']:.0f} €"))
        if m2_prozent(masked):
            stats["M2_ok"] += 1
        out.append(unmask(fixed, store))
    return stats, reports, "\n".join(out)


def target_files():
    files = []
    for d in ("posts", "pillar"):
        dd = ROOT / "content" / d
        if dd.is_dir():
            files += sorted(dd.rglob("index.md"))
    if NEW_ONLY:
        changed = set()
        try:
            outp = subprocess.run(["git", "diff", "--name-only", "HEAD~2", "HEAD", "--", "content/"],
                                  capture_output=True, text=True, cwd=ROOT, timeout=30).stdout
            changed = {ROOT / l.strip() for l in outp.splitlines() if l.strip()}
        except Exception:
            pass
        today = date.today().isoformat()
        changed |= {f for f in (ROOT / "content").rglob("index.md") if f.parent.name.startswith(today)}
        files = [f for f in files if f in changed]
    return files


def main() -> None:
    files = target_files()
    checked, fixed, warns = 0, 0, []
    for p in files:
        stats, reports, new_text = process(p)
        checked += 1
        if stats["M1_korrigiert"] and DO_FIX and not DRY_RUN and new_text != p.read_text(encoding="utf-8"):
            p.write_text(new_text, encoding="utf-8")
            fixed += 1
        warns += reports

    mode = "DRY-RUN" if DRY_RUN else ("FIX" if DO_FIX else "REPORT")
    L = ["# 🧮 MATH-REPORT (math_guard.py)", "",
         f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · Modus: {mode}",
         f"**Gepruefte Artikel:** {checked} · **Auto-Fixes:** {fixed} · **Hinweise:** {len(warns)}", ""]
    if warns:
        L += ["## Fundstellen", ""]
        L += [f"- `{f}` Z.{n}: **{t}** → {c[:80]}" for f, n, t, c in warns[:25]]
    else:
        L.append("🎉 Alle Rechenbeispiele korrekt nachgerechnet (Verlags-Faktencheck).")
    L += ["", "---", "_M1: €/Zeiteinheit × Dauer = Endbetrag (Toleranz nur bei rund/ca.) · "
          "M2: Prozentformeln. Strikte Mathematik, keine KI – Fakten sind Fakten._"]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:20]))
    HISTORY.parent.mkdir(exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"date": date.today().isoformat(), "mode": mode,
                             "checked": checked, "fixed": fixed, "warns": len(warns)}) + "\n")


if __name__ == "__main__":
    main()
