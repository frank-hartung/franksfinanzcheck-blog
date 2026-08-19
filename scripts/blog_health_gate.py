#!/usr/bin/env python3
# ============================================================
#  BLOG-HEALTH-GATE – dauerhafte, sichere Blog-Gesundheitsprüfung
#  mit Selbstheilung (läuft täglich via blog-health-daily.yml).
#
#  WARUM DIESE NEUFASSUNG (19.08.2026): Die Vorgängerversion hatte
#  zwei produktionskritische Fehler, die die "Selbstheilung" leer
#  laufen ließen bzw. aktiv schädigten:
#    1. REPO = "/home/user/repo" war hartkodiert. In GitHub Actions
#       liegt das Repo aber unter $GITHUB_WORKSPACE (ein völlig
#       anderer Pfad) – glob fand dort KEINE Dateien, das Skript
#       endete "erfolgreich", heilte aber NIEMALS etwas. Die
#       tägliche Selbstheilung war seit Monaten lautlos kaputt.
#    2. Es hat pauschal "draft: true" → "draft: false" ersetzt –
#       auch in halbfertigen Entwürfen der Content-Engine. Ein
#       unleserlicher Roh-Entwurf wäre so ungewollt live gegangen.
#       (Zudem wurde H1 unsauber injiziert und das schließende ---
#       klebte am letzten Frontmatter-Wert – TOML kaputt.)
#
#  DIESE NEUFASSUNG IST SICHER UND EHRLICH:
#    • Pfad-Auflösung: GITHUB_WORKSPACE-Env, Fallback Skript-relativ.
#    • SELBSTTEST VOR JEDER HEILUNG (Exit 2 = nichts wird geschrieben).
#    • DRAFT-SCHUTZ: Dateien mit draft:true werden KOMPLETT übersprungen
#      (Veröffentlichung ist ausschließlich Sache von publish.py /
#      Content-Engine – niemals der Gesundheits-Wache).
#    • EINZIGE sichere Heilung: fehlende description aus dem Titel
#      ableiten (SEO-Pflichtfeld). Kein automatisches H1-Injizieren
#      (Posts bringen H1 selbst mit, Listen-Seiten liefert der Theme).
#    • Report: BLOG-GESUNDHEIT-REPORT.md (transparent, was passierte).
#
#  Bewusst KEINE Duplikate der spezialisierten Wachen (casing/dash/
#  unit/lektor/affiliate/…) – deren Aufgabe bleibt deren Kette über
#  blog_doctor.py / seo-weekly.yml. Dieses Gate ist das schnelle,
#  risikofreie tägliche Sicherheitsnetz.
#
#  Aufruf:
#    python3 scripts/blog_health_gate.py           # prüfen + heilen
#    python3 scripts/blog_health_gate.py --dry-run # nur prüfen
# ============================================================

import datetime
import glob
import os
import re
import sys
import tempfile

# ---------------------------------------------------------------- Pfad-Auflösung
# GITHUB_WORKSPACE (CI) hat Vorrang; lokal Skript-relativ. Niemals hartkodierte
# Pfade – das war der ursprüngliche Fehler (Pfad stimmte in CI nie).
ROOT = os.environ.get("GITHUB_WORKSPACE") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

REPORT = os.path.join(ROOT, "BLOG-GESUNDHEIT-REPORT.md")
DRY_RUN = "--dry-run" in sys.argv

FRONT_RX = re.compile(r"\A---\n(.*?)\n---\n", re.S)
DRAFT_RX = re.compile(r"^draft:\s*true\s*$", re.M)


# ---------------------------------------------------------------- Heilung

def fix_article(path: str) -> list[str]:
    """Sichere Heilung EINER Seite. Liefert Liste der durchgeführten Fixes
    (leer = nichts verändert). DRAFT-SCHUTZ: Entwürfe werden nie angefasst."""
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return []
    if DRAFT_RX.search(content):          # niemals Entwürfe veröffentlichen
        return []
    fm_match = FRONT_RX.match(content)
    if not fm_match:
        return []                          # kein sauberer Frontmatter → nichts riskieren
    fm = fm_match.group(1)
    body = content[fm_match.end():]
    title_m = re.search(r'^title:\s*"([^"]+)"', fm, re.M) or re.search(r"^title:\s*(.+)$", fm, re.M)
    title = title_m.group(1).strip().strip('"') if title_m else ""

    # EINZIGE sichere Heilung: description fehlt → aus title ableiten.
    if not (title and not re.search(r"^description:", fm, re.M)):
        return []                          # nichts zu heilen
    desc = f'{title} – bei FranksFinanzcheck lesen, verstehen und sofort sparen.'
    fm = f'description: "{desc}"\n' + fm

    # WICHTIG: schließendes --- braucht einen eigenen Zeilenumbruch davor,
    # sonst klebt es am letzten Frontmatter-Wert (TOML kaputt). FRONT_RX hat
    # das \n vor --- konsumiert → hier wiederherstellen.
    new_content = f"---\n{fm}\n---\n{body}"
    if new_content != content and not DRY_RUN:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
    return ["description ergänzt (aus Titel)"] if new_content != content else []


# ---------------------------------------------------------------- Selbsttest

def _selftest() -> list[str]:
    """Path-Auflösung & Draft-Schutz müssen impftestbar sein (Exit 2 verhindert
    JEDE Dateischreibung, wenn hier etwas nicht stimmt)."""
    fehler = []
    if not os.path.isdir(os.path.join(ROOT, "content")):
        fehler.append(f"ROOT/content existiert nicht – ROOT={ROOT!r} (Pfad-Auflösung kaputt?)")
    # Draft-Schutz: ein Entwurf (draft: true) DARF nie verändert werden.
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as tf:
        tf.write('---\ntitle: "Entwurf"\ndraft: true\n---\n\nUnfertiger Text ohne Description')
        tmp = tf.name
    try:
        before = open(tmp, encoding="utf-8").read()
        fx = fix_article(tmp)
        after = open(tmp, encoding="utf-8").read()
        if fx or after != before:
            fehler.append("Draft-Schutz verletzt: Entwurf wurde angefasst (Veröffentlichungs-Gefahr!)")
    finally:
        os.unlink(tmp)
    # Beschreibungs-Heilung muss eine description-lose Seite korrekt heilen.
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as tf:
        tf.write('---\ntitle: "Testseite"\n---\n\nText')
        tmp2 = tf.name
    try:
        fx = fix_article(tmp2)
        healed = open(tmp2, encoding="utf-8").read()
        if not fx or "description:" not in healed or 'author: "Frank Hartung"---' in healed:
            fehler.append("description-Heilung defekt oder Frontmatter kaputt reconstruiert")
    finally:
        os.unlink(tmp2)
    return fehler


# ---------------------------------------------------------------- main

def main() -> int:
    st = _selftest()
    if st:
        print("🛑 BLOG-HEALTH-SELBSTTEST FEHLGESCHLAGEN – keine Heilung, keine Writes.")
        for e in st:
            print(f"   {e}")
        return 2

    pages = sorted(glob.glob(os.path.join(ROOT, "content", "**", "*.md"), recursive=True))
    drafts = 0
    healed = []   # (relpath, [fixes])
    for p in pages:
        try:
            with open(p, encoding="utf-8") as f:
                txt = f.read()
        except OSError:
            continue
        if DRAFT_RX.search(txt):
            drafts += 1
            continue
        fx = fix_article(p)
        if fx:
            healed.append((os.path.relpath(p, ROOT), fx))

    now = datetime.datetime.now(datetime.timezone.utc)
    lines = [
        "# 🩺 BLOG-GESUNDHEIT-REPORT (blog_health_gate.py)", "",
        f"**Stand:** {now:%Y-%m-%d %H:%M} UTC · Modus: {'DRY-RUN' if DRY_RUN else 'HEAL'} · "
        f"ROOT: `{ROOT}`", "",
        f"Geprüfte Seiten: {len(pages)} · davon Drafts (übersprungen): {drafts} · "
        f"Geheilt: {len(healed)}",
        "",
    ]
    if healed:
        lines.append("| Seite | Heilung |")
        lines.append("|---|---|")
        for rel, fx in healed:
            lines.append(f"| `{rel}` | {'; '.join(fx)} |")
    else:
        lines.append("✅ Keine sicherheitsrelevanten Lücken gefunden (Description überall vorhanden).")
    lines += [
        "",
        "_Drafts werden bewusst nie angefasst (Veröffentlichung = publish.py/Content-Engine). "
        "Spezial-Heilungen (Typografie, Affiliate, SEO-Tiefe …) laufen über die eigene Wachen-Kette._",
    ]
    report = "\n".join(lines) + "\n"
    if not DRY_RUN:
        with open(REPORT, "w", encoding="utf-8") as f:
            f.write(report)

    print(report)
    for rel, fx in healed:
        print(f"  ✅ {rel}: {'; '.join(fx)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
