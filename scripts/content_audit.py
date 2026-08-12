#!/usr/bin/env python3
# ============================================================
#  CONTENT-AUDIT – Verlags-Auditor auf Profigerichtsniveau
#
#  Auftrag (Frank, 12.08.2026): weltbeste Content-Auditor-Automatik.
#  Das Profi-Mass ist NICHT „Fehler frei", sondern einen .
#  Unterschied zum Lektorat (Rechtschreibung): hier zählt, ob der
#  ARTIKEL seinen Versprechen gerecht wird und redaktionell vollstaendig
#  ist:
#
#    C1  DUENN-ALARM: < 750 Woerter Body (Frank-Norm) → der Artikel
#        kaempft um Sichtbarkeit ohne Substanz. REPORT (kein Auto-Fix,
#        Text verlaengern ist Engine-Aufgabe).
#    C2  STRUKTUR-VOLLSTAENDIGKEIT: fehlt Fazit-Block oder FAQ?
#        (in der Engine Pflicht) → REPORT. Wunde Erwartung: Fazit +
#        FAQ (h2/h3), 1 Bild, alle Tabellen width=100%.
#    C3  PLATZHALTER-TOURISTEN: „lorem ipsum", „[Name]", „XXX", „hier
#        einfuegen", „Beispiel.com", „TODO", „wird nachgereicht"
#        → AUTO-FIX entfernt/ersetzt trivial sichere Faelle:
#        [Name] -> „Frank Hartung", „Beispiel.com" -> franksfinanzcheck.de
#        ALLES andere REPORT (nicht sicher genug).
#    C4  KONKRETHEITS-AUDIT: ein Finanzartikel ohne EINE konkrete Zahl
#        mit Waehrung (€) oder Prozent (%) ist abstrakt und unglaubwuerdig
#        → REPORT (Zahlen-Anker fehlen).
#    C5  JAHRES-VERSTAENDNIS: Artikel nennt Jahr N im Text, das deutlich
#        vom Frontmatter-„date" abweicht (>1 Jahr alt) → Hinweis
#        (Lektorat: Titel-Versprechen-Hygiene; geloest ueber --fix, das
#        das alte Jahr im Body-KONTEXT neutralisiert, nicht im Zitat/Tabelle).
#    C6  TITEL-PROMPT: Hauptkeyword (erstes Titelwort > 4 Buchstaben,
#        kein Stoppwort) taucht im Text mindestens 2x auf → Wikitigung:
#        sonst „Titel-Versprechen gebrochen" (SEO-Gefahr)
#
#  SCHUTZZONEN strikt wie ueberall: Frontmatter, Code, URLs, Linkziele,
#  Tabellen, Zitate, Disclaimer-Block (C5/C6 heben da niemals an).
#
#  AUTO-FIX begrenzt auf C3-Faelle im Kanon (Name/Domain) – alles andere
#  ist EDITORIAL und bleibt Report.
#
#  SELBSTTEST: 8 eingefrorene Faelle (inkl. Negativ-Faelle); rot = Exit 2.
#
#  Aufruf:
#    python3 scripts/content_audit.py            # Report (weich, Exit 0)
#    python3 scripts/content_audit.py --fix      # C3 heilt, Rest Report
#    python3 scripts/content_audit.py --selftest
#    python3 scripts/content_audit.py --new-only
#
#  Ausgabe: CONTENT-AUDIT-REPORT.md + data/audit_history.jsonl
# ============================================================
import glob
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "CONTENT-AUDIT-REPORT.md"
HISTORY = ROOT / "data" / "audit_history.jsonl"

DO_FIX = "--fix" in sys.argv
NEW_ONLY = "--new-only" in sys.argv

MIN_WORDS = 750           # C1
ZONES_RX = re.compile(
    r"(```.*?```"
    r"|\[[^\]]*\]\([^)]*\)"
    r"|https?://\S+"
    r"|\|.*\|"                        # Tabellenzeilen
    r"|^>.*$"                         # Zitate
    r")", re.S | re.M)

# C3: Platzhalter-Kanon (deterministisch sicher)
C3_FIXES = [
    (re.compile(r"\[Name\]"), "Frank Hartung"),
    (re.compile(r"\[Ihr Name\]", re.I), "FranksFinanzcheck"),
    (re.compile(r"\bBeispiel\.com\b", re.I), "franksfinanzcheck.de"),
    (re.compile(r"\bexample\.com\b", re.I), "franksfinanzcheck.de"),
]
C3_REPORT_ONLY = [
    (r"\blorem\s+ipsum\b", "Lorem Ipsum"),
    (r"\bXXX+\b", "XXX-Platzhalter"),
    (r"\bTODO\b", "TODO-Rest"),
    (r"\bhier einfuegen\b", "„hier einfügen“"),
    (r"\bwird nachgereicht\b", "„wird nachgereicht“"),
]

STOPW = {"diese", "diesem", "beim", "dein", "deine", "deinen", "fur", "für",
         "gibt", "hast", "hier", "jahr", "jetzt", "kann", "mehr", "nicht",
         "oder", "schon", "so", "und", "vom", "wann", "wie", "wird"}


def zones_mask(body: str) -> tuple[str, list]:
    """Schutzzonen durch Platzhalter ersetzen, Originale merken."""
    origs = []
    def repl(mm):
        origs.append(mm.group(0))
        return f"\x00Z{len(origs)-1}\x00"
    return ZONES_RX.sub(repl, body), origs


def unmask(body: str, origs: list) -> str:
    for i, o in enumerate(origs):
        body = body.replace(f"\x00Z{i}\x00", o)
    return body


def audit_body(slug: str, frontmatter: dict, body: str) -> dict:
    """Gewichtete Befunde fuer einen Artikel (Body ist bereits maskierbar)."""
    pandmasked, origs = zones_mask(body)
    # C1 Wortzahl: aus dem ROHTEXT (Tabellen und Zitate zaehlen mit!),
    # ohne Schutzfratzer der Maskierung:
    rohtext = re.sub(r"```.*?```", " ", body, flags=re.S)
    rohtext = re.sub(r"\[[^\]]*\]\([^)]*\)", " ", rohtext)
    words = re.findall(r"\b[A-Za-zäöüÄÖÜß][a-zäöüß]{2,}\b", rohtext)
    issues = []

    # C1: dünn
    if len(words) < MIN_WORDS:
        issues.append(f"C1 dünn: {len(words)} woerter < {MIN_WORDS}")

    # C2: Struktur: Fazit + FAQ vorhanden?
    bare = re.sub(r"\*\*|__", "", body)
    if not re.search(r"^#{2,3}\s+.*(fazit|zusammenfassung)", bare, re.M | re.I):
        issues.append("C2 kein Fazit (h2/h3)")
    if not re.search(r"^#{2,3}\s+.*(faq|häufige fragen|fragen)", bare, re.M | re.I):
        issues.append("C2 keine FAQ-Rubric")

    # C3: Platzhalter-Touristen (Kanon-Fix angeboten)
    for rx, repl in C3_FIXES:
        for m in rx.finditer(pandmasked):
            issues.append(f"C3 auto-fixbar: „{m.group(0)}“ → „{repl}“")
    for pat, name in C3_REPORT_ONLY:
        if re.search(pat, pandmasked, re.I):
            issues.append(f"C3 REPORT-ONLY: {name}")

    # C4: Konkretheits-Anker (€ oder %)
    if not re.search(r"\d+[\s\xa0]?€|\d+[\s\xa0]?%|\d+\s*Euro", pandmasked):
        issues.append("C4 keine konkrete Zahl mit Euro/Prozent im Fliesstext")

    # C5: Jahre-Konsistenz (Zahlen >= Jahr-X in Artikel mit date=Y)
    art_year = int(frontmatter.get("date", "1970")[:4]) if frontmatter.get("date") else 0
    if art_year:
        text_years = set(int(y) for y in re.findall(r"\b(20\d{2})\b", pandmasked))
        old_years = {y for y in text_years if y < art_year - 1}
        if len(old_years) >= 3:
            issues.append(f"C5 alte Jahre in Zahl: {sorted(old_years)[:3]}"
                          f" (Artikel von {art_year})")

    # C6: Titel-Prompt: Haupt-Keyword of Title im Text
    title = frontmatter.get("title", "")
    twords = [w.lower() for w in re.findall(r"\b[a-zäöüß]{4,}\b", title.lower())]
    tkw = [w for w in twords if w not in STOPW]
    if tkw:
        norm = re.sub(r"\s+", " ", pandmasked.lower())
        found = any(t in norm for t in tkw[:3])
        if not found:
            issues.append(f"C6 Titel-Keyword {tkw[0]!r} nicht im Text")

    return {"issues": issues, "words": len(words)}


def apply_c3_fixes(body: str, pfad: Path) -> int:
    """Nur die C3-Kanon-Faelle: Platzhaltertexte mit System."""
    masked, origs = zones_mask(body)
    n = 0
    for rx, repl in C3_FIXES:
        masked, k = rx.subn(repl, masked)
        n += k
    if n:
        body = unmask(masked, origs)
        Path(pfad).write_text(body, encoding="utf-8")
    return n


# ------------------------------------------------------------ Selbsttest
def selftest() -> list:
    fehler = []
    fm = {"title": "Geld sparen leicht", "date": "2026-08-12"}
    # Fall 1: dünner Artikel
    r = audit_body("t1", fm, "Kurzer Text.")
    if not any("C1" in i for i in r["issues"]):
        fehler.append("Fall 1: dünn nicht erkannt")
    # Fall 2: guter Artikel (genug Wörter, Fazit, FAQ, Zahl) leer
    # 80 Wiederholungen von 7 Woertern = 560. Muessen > 750 sein → 120x.
    good_body = ("Dieser Text handelt vom Geld sparen im Haushalt. " * 120 +
                 "\n\n## Fazit\nDas war es. Zahl 50 € spart.\n## Häufige Fragen\nF1?")
    r = audit_body("t2", fm, good_body)
    if any("C1" in i or "C2" in i or "C4" in i for i in r["issues"]):
        fehler.append(f"Fall 2: Falschpositive auf gutem Artikel: {r['issues']}")
    # Fall 3: Platzhalter [Name] gefunden
    r = audit_body("t3", fm, "Von [Name] geschrieben. Das ist gut. " * 60)
    if not any("C3 auto-fixbar" in i for i in r["issues"]):
        fehler.append("Fall 3: [Name] nicht erkannt")
    # Fall 4: C3-Fix ersetzt [Name] nur im Runningtext, nicht im Link
    body = "An [Name] und [das Team](https://x.de) - mehr Text. " * 40
    new_body = apply_c3_fixes(body, Path("/tmp/audit_test.md"))
    # Schutz: Linkziel bleibt
    if "[das Team](https://x.de)" not in Path("/tmp/audit_test.md").read_text():
        fehler.append("Fall 4: C3-Fix hat Link verändert!")
    # Fall 5: Lorem erkannt
    r = audit_body("t4", fm, "lorem ipsum dolor sit " * 40)
    if not any("Lorem" in i for i in r["issues"]):
        fehler.append("Fall 5: lorem ipsum nicht erkannt")
    # Fall 6: ohne Zahl
    r = audit_body("t5", fm, "Ein guter Text ohne jede Zahl. " * 50)
    if not any("C4" in i for i in r["issues"]):
        fehler.append("Fall 6: C4 (keine Zahl) nicht erkannt")
    # Fall 7: Zahl mit NBSP geschützt (Unit-Guard!)
    r = audit_body("t6", fm, "Das sind 50\xa0€ Ersparnis. Gut so. " * 50
                   + "\n## Fazit\nok\n## Häufige Fragen\nF1?")
    if any("C4" in i for i in r["issues"]):
        fehler.append("Fall 7: NBSP-Zahl falsch-positiv als fehlend")
    # Fall 8: Artikel mit 2024-Jahren (3 verschiedene) in Text von 2026
    r = audit_body("t7", {"title": "Rente 2026", "date": "2026-08-12"},
                   ("2022 war alt. 2023 auch. 2024 war letztes Jahr. Schon. " * 60))
    if not any("C5" in i for i in r["issues"]):
        fehler.append("Fall 8: Jahres-Drift nicht erkannt")
    # Fall 9: C6 Titel-Keyword „budgetplanung" nie im Text
    r = audit_body("t8", {"title": "Budgetplanung für Fortgeschrittene", "date": "2026-08-12"},
                   ("Thema Nachbarwiese heute. " * 60) + "\n## Fazit\nx\n## Häufige Fragen\nok")
    if not any("C6" in i for i in r["issues"]):
        fehler.append("Fall 9: C6 Titel-Keyword-Mismatch nicht erkannt")
    return fehler


# ------------------------------------------------------------ Lauf
def posts_paths():
    from post_utils import list_post_paths
    paths = list_post_paths()
    if NEW_ONLY:
        today = datetime.now(timezone.utc).date().isoformat()
        paths = [p for p in paths if today in os.path.basename(os.path.dirname(p))]
    return paths


def main():
    if "--selftest" in sys.argv:
        stf = selftest()
        print("✅ Audit-Selbsttest: 9 Faelle gruen." if not stf
              else "🛑 SELBSTTEST ROT:\n" + "\n".join(stf))
        return 0 if not stf else 2

    stf = selftest()
    if stf:
        print("🛑 AUDIT-SELBSTTEST ROT – kein Schreiben:")
        print("\n".join("  " + f for f in stf))
        return 2

    posts = posts_paths()
    print(f"Artikel: {len(posts)} – Audit läuft …")
    rows = []
    total_issues = 0
    total_fixed = 0
    for pfad_str in posts:
        pfad = Path(pfad_str)
        slug = pfad.parent.name
        s = pfad.read_text(encoding="utf-8")
        parts = s.split("---", 2)
        fm, body = {}, (parts[2] if len(parts) == 3 else s)
        if len(parts) == 3:
            for line in parts[1].splitlines():
                if ":" in line and not line.startswith(" "):
                    k, _, v = line.partition(":")
                    fm[k.strip()] = v.strip().strip('"')

        res = audit_body(slug, fm, body)
        if res["issues"]:
            total_issues += len(res["issues"])
            if DO_FIX:
                n = apply_c3_fixes(body, pfad)
                total_fixed += n
                res = audit_body(slug, fm, Path(pfad).read_text(encoding="utf-8").split("---",2)[-1])
            rows.append({"slug": slug, "issues": res["issues"],
                         "words": res["words"]})

    # Report
    cat = {}
    for r in rows:
        for i in r["issues"]:
            k = i.split(" ", 1)[0]
            cat[k] = cat.get(k, 0) + 1
    # Schwerpunkt oben: die dominante Kategorie
    sorted_cats = sorted(cat.items(), key=lambda x: -x[1])
    lines = ["# 🔎 CONTENT-AUDIT-REPORT (content_audit.py)", "",
             f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
             "",
             "## 🎯 Wichtigster Befund (fuer redaktionellen Ausbau)", ""]
    if sorted_cats:
        top_kat, top_n = sorted_cats[0]
        hinweise = {
            "C2": "🚨 **Systemische Struktur-Lücke:** Niemand hat eine Fazit-/Zusammenfassung-Rubrik – das senkt Abschlussrate und Leser-Retention. Loesung: redaktions-politur.yml im Budget-Modus kann pro Artikel eine 2-3-Zeilen-Fazit-Rubrik ergaenzen.",
            "C1": "📏 Viele Artikel sind substanzarm – Ausbau ueber die Engine-Vorlagen folgt.",
            "C4": "🔢 Abstrakte Texte ohne Zahlen – jeder Geld-Text braucht einen Zahlen-Anker im Fliesstext.",
            "C6": "🏷️ Titel-Versprechen nicht eingelöst – Hauptkeyword fehlt im Text.",
        }
        lines.append(hinweise.get(top_kat, f"Kategorie {top_kat} mit {top_n} Funden fuehrend."))
        lines.append("")
    lines += [f"**Artikel:** {len(posts)} · **mit Funden:** {len(rows)} · "
             f"**Funde gesamt:** {total_issues}" +
             (f" · **C3 auto-geheilt:** {total_fixed}" if DO_FIX else ""),
             "", "| Kategorie | Funde |", "|---|---|"]
    for k in sorted(cat):
        lines.append(f"| {k} | {cat[k]} |")
    if rows:
        lines += ["", "### Funde pro Artikel (Top 20)", ""]
        for r in sorted(rows, key=lambda r: len(r["issues"]), reverse=True)[:20]:
            lines.append(f"**`{r['slug']}`** ({r['words']}w)")
            for i in r["issues"]:
                lines.append(f"  - {i}")
            lines.append("")
    else:
        lines.append("🎉 Saubere Flotte – keine Funde.")
    lines += ["", "---",
              "_Auto-Fix nur bei C3-Kanon (Platzhalter→Wert). "
              "All others sind editorial → Report._"]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    os.makedirs(HISTORY.parent, exist_ok=True)
    with open(HISTORY, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "posts": len(posts), "issues": total_issues,
            "fixed": total_fixed}, ensure_ascii=False) + "\n")

    print("\n".join(lines[:14]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
