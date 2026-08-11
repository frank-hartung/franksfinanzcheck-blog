#!/usr/bin/env python3
# ============================================================
#  UNIT-GUARD – Einheiten-/Währungs-Typografie (selbst entscheidend)
#
#  AUFTRAG (11.08.2026): Blog herrschte Stil-Mischung (346× „Euro" gegen
#  499× „€"; 134× „Prozent" gegen 227× „%"). Hausstil-Entscheidung durch
#  Chefredaktion: EINHEITLICH kompakt: „X €" und „X %".
#
#  REGELN (deterministisch, Duden-konform, Web-typografisch):
#    U1  „1.000 Euro" / „50 Euro"      → „1.000 €" / „50 €"
#         (nur mit Zahl davor; „Eurozone", „1000-Euro-Schein" bleiben!)
#    U2  „5 Prozent"                    → „5 %"
#    U3  Nach Umwandlung: GESCHÜTZTES Leerzeichen (NBSP) zwischen
#         Zahl und €/% – kein Zeilenbruch möglich (ersetzt das frühere
#         fix_nbsp.py, das seit dem Archiv-Cleaning nicht mehr lief).
#    U4  Doppelraum & NBSP-Kaskaden aufräumen („X  €" / bereits gesetzt)
#
#  SELBSTHEILUNG: --fix korrigiert sofort; in der Engine (Phase 2) bei
#  jedem neuen Artikel automatisch. Idempotent. UNIT-REPORT.md.
#
#  GESCHÜTZT (nie anfassen): Front-Matter (klammern SEO & Cover-Texte),
#  URLs/Linkziele, Code-Fences/Inline-Code, Hashtags, zusammengesetzte
#  Wörter mit Bindestrich (1000-Euro-Schein), Lehnwörter (Eurozone).
#
#  Aufruf:
#    python3 scripts/unit_guard.py             # Report
#    python3 scripts/unit_guard.py --fix       # Auto-Fix
#    python3 scripts/unit_guard.py --new-only  # Engine-Modus
# ============================================================

import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "UNIT-REPORT.md"

DO_FIX = "--fix" in sys.argv
DRY_RUN = "--dry-run" in sys.argv
NEW_ONLY = "--new-only" in sys.argv

NBSP = "\u00a0"
Z = r"(\d[\d.]*,?\d*)"       # eine Zahl (mit . Tausender / , Komma)

# U5: „zwischen 3 und 6 %" -> „zwischen 3 % und 6 %" (Einheit beiden Zahlen)
#     Lektorats-Strenge, Fund 11.08.2026 (Artikel zinseszinseffekt).
R_RANGE_UND = re.compile(
    r"\b(zwischen|von)\s+(\d[\d.]*,?\d*)\s+und\s+(\d[\d.]*,?\d*)[\s" + NBSP + r"]+([€%])")

# U1/U2 Muster (Wortgrenze links sichert keine Komposita?); wir schützen über
# Nachbar-Regeln: kein Bindestrich direkt vor „Euro" („…-Euro" bleibt!)
R_EURO = re.compile(Z + r"[\s" + NBSP + r"]*Euro\b(?![a-zäöüß])")
R_PROZ = re.compile(Z + r"[\s" + NBSP + r"]*Prozent\b")
# Bereinigung: NBSP/Doppelplatz vor € oder % vereinheitlichen:
R_EURO_NBSP = re.compile(Z + r"(?:[" + NBSP + r" ]+)(€)")
R_PROZ_NBSP = re.compile(Z + r"(?:[" + NBSP + r" ]+)(%)")

WHITELIST_SUFFIX = ("eurozone", "euroschulden", "eurokrise")


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


def fix_line(body: str) -> tuple[str, int]:
    n = 0
    # U5 zuerst (greift vor U3b, damit Einheiten-Verdopplung sauber zuerst)
    def r_und(m):
        nonlocal n
        n += 1
        return f"{m.group(1)} {m.group(2)}{NBSP}{m.group(4)} und {m.group(3)}{NBSP}{m.group(4)}"
    body = R_RANGE_UND.sub(r_und, body)
    # U1: Euro -> €
    def r_euro(m):
        nonlocal n
        prefix = body[max(0, m.start()-2):m.start()]
        if prefix.endswith("-"):      # „1000-Euro" Kompositum bleibt
            return m.group(0)
        n += 1
        return m.group(1) + NBSP + "€"
    body = R_EURO.sub(r_euro, body)
    # U2: Prozent -> %
    def r_proz(m):
        nonlocal n
        n += 1
        return m.group(1) + NBSP + "%"
    body = R_PROZ.sub(r_proz, body)
    # U3/U4: Leerraum-Form normalisieren (falls €/ % schon stand)
    def r_sp(m):
        nonlocal n
        want = m.group(1) + NBSP + m.group(2)
        if want != m.group(0):
            n += 1
        return want
    body = R_EURO_NBSP.sub(r_sp, body)
    body = R_PROZ_NBSP.sub(r_sp, body)
    # U3b: komplett ohne Leerraum zusammengeklebt („20%" / „50€") -> NBSP setzen
    def r_gap(m):
        nonlocal n
        n += 1
        return m.group(1) + NBSP + m.group(2)
    body = re.sub(Z + r"(?<!\s)([" + NBSP + r"]?€)", lambda m: m.group(0), body)  # Platzhalter sicher
    body = re.sub(r"(\d)([€%])", lambda m: f"{m.group(1)}{NBSP}{m.group(2)}", body)
    return body, n


def process_full(path: Path):
    rel = str(path.relative_to(ROOT))
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    out, changes = [], 0
    in_code = False
    fence_hits = 0
    for raw in lines:
        s = raw.strip()
        if s.startswith("```"):
            in_code = not in_code
            out.append(raw); continue
        if in_code:
            out.append(raw); continue
        if s.startswith("---") and fence_hits == 0:
            fence_hits = 1       # Öffnende Fence
            out.append(raw); continue
        if fence_hits == 1 and (s.startswith("---") or s == ""):
            if s.startswith("---"):
                fence_hits = 2  # Schließende Fence (sauber oder geklebt)
            if s.startswith("---") and s != "---":
                # Geklebter Fence: Rest verarbeiten
                rest = s[3:]
                if re.search(r"[A-Za-zäöü]", rest):
                    m_rest, store = mask(rest)
                    fixed, n = fix_line(m_rest)
                    out.append("---" + unmask(fixed, store))
                    changes += n
                    continue
            out.append(raw); continue
        if fence_hits == 1:
            out.append(raw); continue   # innerhalb Front-Matter
        # Listen-/Zitat-Marker schützen, Inhalt fixen
        m = re.match(r"^(\s*[-*>#]+\s+)(.*)$", raw)
        prefix, body = (m.group(1), m.group(2)) if m else ("", raw)
        masked, store = mask(body)
        fixed, n = fix_line(masked)
        changes += n
        out.append(prefix + unmask(fixed, store))
    return changes, "\n".join(out)


def target_files():
    files = []
    for d in ("posts", "pillar"):
        dd = ROOT / "content" / d
        if dd.is_dir():
            files += sorted(dd.rglob("index.md"))
    if NEW_ONLY:
        changed = set()
        try:
            out = subprocess.run(["git", "diff", "--name-only", "HEAD~2", "HEAD", "--", "content/"],
                                 capture_output=True, text=True, cwd=ROOT, timeout=30).stdout
            changed = {ROOT / l.strip() for l in out.splitlines() if l.strip()}
        except Exception:
            pass
        today = date.today().isoformat()
        changed |= {f for f in (ROOT / "content").rglob("index.md") if f.parent.name.startswith(today)}
        files = [f for f in files if f in changed]
    return files


def main() -> None:
    files = target_files()
    touched = []
    for p in files:
        n, new_text = process_full(p)
        if n:
            if DO_FIX and not DRY_RUN and new_text != p.read_text(encoding="utf-8"):
                p.write_text(new_text, encoding="utf-8")
            touched.append((str(p.relative_to(ROOT)), n))

    mode = "DRY-RUN" if DRY_RUN else ("FIX" if DO_FIX else "REPORT")
    L = ["# 💶 UNIT-REPORT (unit_guard.py)", "",
         f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · Modus: {mode}",
         "**Hausstil:** X € / X % (mit NBSP, umburchfest)", ""]
    if touched:
        L += [f"## {'✅ korrigiert' if DO_FIX else '🔍 Befunde'} ({len(touched)} Dateien)", ""]
        L += [f"- `{f}`: {n} Stelle(n)" for f, n in touched[:40]]
    else:
        L.append("🎉 Einheiten-Stil einheitlich (Hausstil).")
    L += ["", "---", "_U1 Euro→€ · U2 Prozent→% · U3 NBSP-Setzung · "
          "U4 Doppelraum-Bereinigung. Komposita mit Bindestrich bleiben._"]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:20]))


if __name__ == "__main__":
    main()
