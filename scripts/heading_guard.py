#!/usr/bin/env python3
# ============================================================
#  HEADING-GUARD – Überschriften-Hygiene H1–H3 (selbstheilend)
#
#  ANLASS (27.08.2026, Premium-Befund): 101 Überschriften im
#  Bestand trugen Layout-HTML „<br>“ – z. B.
#      ## Fazit:<br> Ein 30-Minuten-Vergleich, der sich auszahlt
#  Das ist ein bekanntes Anti-Pattern mit drei echten Folgen:
#    1. INHALTSVERZEICHNIS: Die TOC-Wache (PaperMod toc.html)
#       strippt das Tag → sichtbarer Artefakt „Fazit:\ Ein …“
#       (Backslash-Leiche) statt „Fazit: Ein …“.
#    2. LESER/SEO: Aus dem erwarteten Leerzeichen wird ein
#       harter Zeilenumbruch – Screenreader, Google-Snippets,
#       AI Overviews und RSS/Pinterest-Sync sehen verklebte
#       Texte („Fazit:Ein“-Wirkung).
#    3. ROBUSTHEIT: Anker-IDs aus Tag-Suppe sind undefiniertes
#       Verhalten über Hugo-/Theme-Updates hinweg.
#
#  REGELN:
#    H1  „<br>“ (alle Varianten: <br>, <br/>, <br />, <br >)
#        in ATX-Überschriften (# … ######) → GENAU EIN
#        Leerzeichen; mehrfache Leerzeichen kollabieren.
#        NUR WENN DER GOLDMARK-ANKER (id=…) VOR/NACH IDENTISCH
#        BLEIBT → externe Links (Pinterest-Pins!, Backlinks,
#        YouTube-Beschreibungen) brechen NIE.
#    H2  „<br>“ am Überschriften-Ende (ohne Folgetext) → Tag
#        entfernen (Anker unverändert, gleiche Logik wie H1).
#    H3  Sonstiges Roh-HTML in Überschriften (z. B. <span>) →
#        NUR MELDEN (kein Auto-Fix – zu riskant, Redaktion
#        entscheidet). Aktuell: 0 Funde im Bestand.
#
#  GESCHÜTZT: Fließtext-„<br>“ (bewusste Umbrüche z. B. in
#  CTA-Zeilen), Frontmatter, Code-Blöcke, Tabellen, Archetypen.
#  Die Wache liest AUSSCHLIESSLICH Zeilen, die mit #{1–6} beginnen.
#
#  Selbstheilungs-Prinzip des Hauses: zweiter Lauf findet nichts
#  mehr (idempotent). Jede Heilung wird mit Anker-Beweis in
#  data/heading_guard_history.jsonl protokolliert.
#
#  Aufruf:
#    python3 scripts/heading_guard.py             # Report (Check)
#    python3 scripts/heading_guard.py --fix       # heilen (H1/H2)
#    python3 scripts/heading_guard.py --dry-run   # zeigen, nichts schreiben
#    python3 scripts/heading_guard.py --selftest  # eingefrorene Fälle (Exit 2 = Wache kaputt)
#
#  Ausgabe: HEADING-REPORT.md + Konsole.
#  Exit: 0 = sauber/geheilt · 1 = nicht heilbare Funde · 2 = Selbsttest fehlerhaft.
#  Eingehängt: blog_doctor.py (Kette, Phase A) · deploy.yml · blog-health-daily.yml.
# ============================================================

import datetime
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(os.environ.get("GITHUB_WORKSPACE")
            or Path(__file__).resolve().parent.parent)
CONTENT_DIR = ROOT / "content"
REPORT = ROOT / "HEADING-REPORT.md"
HISTORY = ROOT / "data" / "heading_guard_history.jsonl"

DO_FIX = "--fix" in sys.argv
DRY_RUN = "--dry-run" in sys.argv

# ATX-Überschrift: 1–6 Rauten, danach Text (ohne führende/abschließende Spaces)
HEADING_RX = re.compile(r"^(#{1,6})[ \t]+(.*?)[ \t]*$", re.M)
# <br> in allen Schreibweisen, inkl. umgebender Leerzeichen
BR_RX = re.compile(r"[ \t]*<br[ \t]*/?>[ \t]*", re.I)
# beliebiges weiteres Roh-HTML (für Regel H3, nur Meldung)
TAG_RX = re.compile(r"<[a-zA-Z/][^>]*>")
MULTISPACE_RX = re.compile(r" {2,}")

# ------------------------------------------------------------ Anker-Beweis

def goldmark_slug(heading_text: str) -> str:
    """Hugo/Goldmark-Anker (autoHeadingIDType: github, Haus-Standard)
    nachgebaut – NUR für den Vor/Nach-Vergleich, nie fürs Setzen:
      • HTML-Tags tragen NICHT zum Anker bei (fallen weg)
      • Kleinbuchstaben, Leerzeichen → '-', Unicode-Buchstaben bleiben
      • Satzzeichen (.:,!?…) fallen weg, '-'/'_' bleiben
      • doppelte '-' kollabieren, führende/folgende '-' entfallen
    Beleg aus dem Live-Blog:
      'Mein eigener Spar-Erfolg: von 1.040 € auf 412 €'
        → mein-eigener-spar-erfolg-von-1040-auf-412
      'Fazit:<br> Ein 30-Minuten-Vergleich, der sich auszahlt'
        → fazit-ein-30-minuten-vergleich-der-sich-auszahlt
    """
    text = TAG_RX.sub("", heading_text).strip()
    out = []
    for ch in text:
        if ch == " ":
            out.append("-")
        elif ch.isalnum():
            out.append(ch.lower())
        elif ch in ("-", "_"):
            out.append(ch)
        # alle anderen Zeichen: weg (wie Goldmark)
    slug = "".join(out)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug

# ------------------------------------------------------------ Kern-Logik

def heal_headings(text: str, rel_path: str, do_fix: bool):
    """Läuft über alle ATX-Überschriften EINER Datei.
    Rückgabe: (neuer_text|None, funde[]) – funde[] auch im Check-Modus."""
    findings = []
    changed = False

    def repl(m):
        nonlocal changed
        hashes, body = m.group(1), m.group(2)
        if not BR_RX.search(body):
            # H3: anderes Roh-HTML? (nur melden, niemals anfassen)
            other = TAG_RX.search(body)
            if other:
                findings.append({
                    "id": "H3", "file": rel_path, "level": len(hashes),
                    "alt": body.strip(),
                    "problem": f"Roh-HTML in Überschrift ({other.group(0)}) – nur gemeldet, kein Auto-Fix",
                    "geheilt": False,
                })
            return m.group(0)
        # H1/H2: Heilungskandidat – Anker-Beweis ZUERST (Pin-Schutz!)
        healed_body = MULTISPACE_RX.sub(" ", BR_RX.sub(" ", body)).strip()
        slug_vorher = goldmark_slug(body)
        slug_nachher = goldmark_slug(healed_body)
        if slug_vorher != slug_nachher:
            findings.append({
                "id": "H1-BLOCKIERT", "file": rel_path, "level": len(hashes),
                "alt": body.strip(),
                "problem": (f"Heilung würde Anker ändern "
                            f"(#{slug_vorher} → #{slug_nachher}) – "
                            f"manuelle Entscheidung, externe Links geschützt"),
                "geheilt": False,
            })
            return m.group(0)
        findings.append({
            "id": "H1", "file": rel_path, "level": len(hashes),
            "alt": body.strip(), "neu": healed_body,
            "anker": slug_nachher, "geheilt": bool(do_fix and not DRY_RUN),
        })
        if do_fix and not DRY_RUN:
            changed = True
            return f"{hashes} {healed_body}"
        return m.group(0)

    neuer_text = HEADING_RX.sub(repl, text)
    return (neuer_text if changed else None), findings


def scan(do_fix: bool):
    """Über alle Markdown-Dateien unter content/ (Posts, Pillar, Pages)."""
    all_findings, healed_files = [], 0
    if not CONTENT_DIR.is_dir():
        print(f"🛑 HEADING-GUARD: {CONTENT_DIR} nicht gefunden (Pfad auflösen!)")
        return all_findings, healed_files
    for path in sorted(CONTENT_DIR.rglob("*.md")):
        rel = str(path.relative_to(ROOT))
        text = path.read_text(encoding="utf-8")
        neuer_text, findings = heal_headings(text, rel, do_fix)
        all_findings += findings
        if neuer_text is not None:
            path.write_text(neuer_text, encoding="utf-8")
            healed_files += 1
    return all_findings, healed_files

# ------------------------------------------------------------ Report

def write_report(findings: list, healed_files: int, mode: str) -> None:
    jetzt = datetime.datetime.now(datetime.timezone.utc)
    fixbar = [f for f in findings if f["id"] == "H1"]
    blockiert = [f for f in findings if f["id"] == "H1-BLOCKIERT"]
    info = [f for f in findings if f["id"] == "H3"]

    lines = [
        "# 🧱 HEADING-REPORT (heading_guard.py)",
        "",
        f"**Stand:** {jetzt:%Y-%m-%d %H:%M} UTC · Modus: {mode}",
        "",
        "Regeln: **H1** `<br>` in Überschriften → Leerzeichen (nur bei "
        "anker-stabilem Beweis, Auto-Fix) · **H2** `<br>` am Ende → Wegfall "
        "(anker-stabil) · **H3** sonstiges Roh-HTML → nur Meldung.",
        "",
    ]
    if fixbar:
        n_dateien = len({f["file"] for f in fixbar}) if mode != "FIX" else healed_files
        lines.append(f"## {'✅ Geheilt' if mode == 'FIX' else '🔧 Funde'}: "
                     f"{len(fixbar)} Überschrift(en) mit `<br>` "
                     f"in {n_dateien} Datei(en)")
        lines.append("")
        for f in fixbar[:120]:
            zustand = "→ geheilt" if f["geheilt"] else "→ Funde"
            lines.append(f"- `{f['file']}` H{f['level']}: „{f['alt'][:90]}“ "
                         f"{zustand} · Anker `#{f['anker']}` unverändert")
        if len(fixbar) > 120:
            lines.append(f"- … und {len(fixbar) - 120} weitere")
        lines.append("")
    if blockiert:
        lines.append("## 🛑 H1-BLOCKIERT (Anker würde sich ändern – kein Auto-Fix)")
        lines.append("")
        lines += [f"- `{b['file']}`: {b['problem']} · Überschrift: „{b['alt'][:80]}“"
                  for b in blockiert]
        lines.append("")
    if info:
        lines.append("## ⚠️ H3: Roh-HTML in Überschriften (nur Meldung)")
        lines.append("")
        lines += [f"- `{i['file']}`: {i['problem']} · „{i['alt'][:80]}“" for i in info]
        lines.append("")
    if not findings:
        lines.append("🎉 Alle Überschriften frei von `<br>`/Roh-HTML – "
                     "Anker stabil, TOC sauber, Profi-Niveau.")
        # Audit-Spur: letzte Heilung aus der Historie (Transparenz)
        letzte = None
        if HISTORY.exists():
            try:
                eintraege = [json.loads(l) for l in
                             HISTORY.read_text(encoding="utf-8").splitlines() if l.strip()]
                letzte = eintraege[-1] if eintraege else None
            except (ValueError, OSError):
                letzte = None
        if letzte and letzte.get("geheilt"):
            lines.append("")
            lines.append(f"**Letzte Heilung (Audit-Spur):** "
                         f"{letzte['geheilt']} Überschrift(en) am "
                         f"{letzte['zeit'][:16].replace('T', ' ')} UTC – "
                         f"Details: `data/heading_guard_history.jsonl`.")
        lines.append("")
    lines += [
        "---",
        "_Warum: `<br>` in Überschriften zerstört TOC-Texte („Fazit:\\\\ Ein“), "
        "fühlt sich für Leser wie ein fehlendes Leerzeichen an und ist ein "
        "SEO-/Barrierefreiheits-Risiko. Der Guard heilt anker-stabil – externe "
        "Links (Pinterest-Pins, Backlinks) brechen nie._",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:25]))


def log_history(findings: list) -> None:
    if not findings:
        return
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    jetzt = datetime.datetime.now(datetime.timezone.utc).isoformat()
    eintrag = {
        "zeit": jetzt,
        "wache": "heading_guard.py",
        "funde": len(findings),
        "geheilt": sum(1 for f in findings if f.get("geheilt")),
        "details": [
            {"datei": f["file"], "regel": f["id"], "anker": f.get("anker", ""),
             "vorher": f["alt"], "nachher": f.get("neu", "")}
            for f in findings if f["id"] in ("H1", "H1-BLOCKIERT")
        ],
    }
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(eintrag, ensure_ascii=False) + "\n")

# ------------------------------------------------------------ Selbsttest

def run_selftest() -> int:
    """Eingefrorene Fälle (inkl. LIVE-Anker-Beweis). Fehlschlag → Exit 2."""
    results = []

    def check(name, cond):
        results.append((name, bool(cond)))
        print(("  ✓ " if cond else "  ✗ ") + name)

    # (name, eingabe, erwartete Überschrift nach Fix, erwarteter Anker|None)
    heil_faelle = [
        ("H1: Fazit-Heilung (Live-Fall Kfz-Artikel, 26.08.2026)",
         "## Fazit:<br> Ein 30-Minuten-Vergleich, der sich auszahlt",
         "## Fazit: Ein 30-Minuten-Vergleich, der sich auszahlt",
         "fazit-ein-30-minuten-vergleich-der-sich-auszahlt"),
        ("H1: Variante <br/> (H3-Ebene)",
         "### Fehler 2:<br/> Verstaubte Heizkörper",
         "### Fehler 2: Verstaubte Heizkörper", None),
        ("H1: Variante <br />",
         "## Tarifvergleich:<br /> Alt vs. Neu",
         "## Tarifvergleich: Alt vs. Neu", None),
        ("H2: <br> am Überschriften-Ende (ohne Folgetext)",
         "## Checkliste:<br>",
         "## Checkliste:", None),
        ("H1: doppelte Leerzeichen nach Heilung kollabieren",
         "## Spartabelle:<br>  Banking-Gebühren im Vergleich",
         "## Spartabelle: Banking-Gebühren im Vergleich", None),
    ]
    for name, zeile, erwartet, anker in heil_faelle:
        _neu, funden = heal_headings(zeile + "\n\nText", "selftest.md", do_fix=True)
        geheilt = bool(funden) and f"{'#' * funden[0]['level']} {funden[0].get('neu', '')}" == erwartet
        check(f"{name} – heilt korrekt", geheilt)
        if anker:
            check(f"{name} – Anker exakt live-kompatibel: #{anker}",
                  bool(funden) and funden[0].get("anker") == anker)

    # Ankerschutz: OHNE Leerzeichen nach <br> würde der Anker kollabieren
    # („fazitein“ statt „fazit-ein“) → Heilung MUSS blockiert werden.
    _neu, funden = heal_headings(
        "## Fazit:<br>Ein Vergleich\n", "selftest.md", do_fix=True)
    check("SCHUTZ: Ankeränderung blockiert (kein Leerzeichen nach <br>)",
          bool(funden) and funden[0]["id"] == "H1-BLOCKIERT")

    # Fließtext-<br> bleibt unangetastet (nur Überschriften-Zeilen!)
    text_fließ = "Normaler Absatz mit<br> bewusstem Umbruch bleibt.\n"
    neu, funden = heal_headings(text_fließ, "selftest.md", do_fix=True)
    check("SCHUTZ: Fließtext-<br> bleibt stehen", neu is None and not funden)

    # H3: anderes Roh-HTML nur gemeldet
    _n, funden = heal_headings("## Titel mit <span>Span</span>\n", "st.md", do_fix=True)
    check("H3: anderes Roh-HTML nur gemeldet, nicht angefasst",
          len(funden) == 1 and funden[0]["id"] == "H3" and not funden[0]["geheilt"])

    # Idempotenz: heilter Text liefert keine Funden mehr
    geheilt_text = "## Fazit: Ein 30-Minuten-Vergleich, der sich auszahlt\n"
    _n, funden = heal_headings(geheilt_text, "st.md", do_fix=True)
    check("Idempotenz: geheilte Überschrift → keine Funde", not funden)

    failed = [n for n, ok in results if not ok]
    if failed:
        print(f"🛑 HEADING-SELFTEST FEHLGESCHLAGEN ({len(failed)}): {failed}")
        return 2
    print(f"✅ HEADING-SELFTEST bestanden ({len(results)} Fälle).")
    return 0

# ------------------------------------------------------------ Main

def main() -> int:
    if "--selftest" in sys.argv:
        return run_selftest()

    mode = "DRY-RUN" if DRY_RUN else ("FIX" if DO_FIX else "CHECK")
    findings, healed_files = scan(do_fix=DO_FIX and not DRY_RUN)
    write_report(findings, healed_files, mode)
    if not DRY_RUN:
        log_history(findings)

    blockiert = [f for f in findings if f["id"] == "H1-BLOCKIERT"]
    if DO_FIX or DRY_RUN:
        modus = "DRY-RUN" if DRY_RUN else "FIX"
        print(f"Heading-Guard [{modus}]: {len(findings)} Fund(e), {healed_files} "
              f"Datei(en) {'würden geheilt' if DRY_RUN else 'geheilt'}, "
              f"{len(blockiert)} blockiert (Ankerschutz).")
    return 1 if blockiert else 0


if __name__ == "__main__":
    sys.exit(main())
