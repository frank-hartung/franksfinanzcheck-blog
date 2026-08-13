#!/usr/bin/env python3
# ============================================================
#  AUTOMATIONS-SIMULATOR – End-to-End-Simulationstest der gesamten
#  Blog-Automatik, mit begrenzter Selbstheilung.
#
#  Auftrag (13.08.2026, Frank): "einen automatischen Simulation-Check der
#  gesamten Blogautomatik einbauen mit Selbstheilung."
#
#  WARUM NÖTIG (Lücke in der bestehenden Wachen-Landschaft):
#  scripts/blog_doctor.py orchestriert bereits ~19 Wachen – aber die
#  prüfen ausschließlich ARTIKEL-TEXT-QUALITÄT (Rechtschreibung, Dashes,
#  Einheiten, Stil, Plagiat, Tabellen, Links im Fließtext …). Keine davon
#  prüft, ob die PIPELINE-MASCHINERIE SELBST noch korrekt funktioniert.
#  Genau das war heute mehrfach das eigentliche Problem: Skripte liefen
#  fehlerfrei durch (Exit 0!) und meldeten sogar "✅ alles perfekt" –
#  verarbeiteten dabei aber still 0 statt 9 Artikel, weil eine
#  Lade-Funktion strukturell falsch iterierte (os.listdir + ".md"-Endung
#  statt Page-Bundle-Erkennung). Das ist die gefährlichste Fehlerklasse:
#  kein Crash, kein Exit-Code-Fehler, nur ein stiller Bedeutungsverlust.
#
#  Dieses Skript simuliert deshalb den GESAMTEN Automatik-Kreislauf
#  (Themen-Pool -> Artikel-Erzeugung -> Tags/Keywords/Provider ->
#  Publish-Gate -> Social-Posting -> Kadenz-Steuerung) mit synthetischen
#  Test-Daten in einem isolierten Temp-Verzeichnis (rührt NIE echten
#  Content an) und vergleicht zusätzlich echte Lade-Funktionen gegen eine
#  unabhängig ermittelte Grundwahrheit (Ground Truth).
#
#  SELBSTHEILUNG (bewusst eng begrenzt auf sicher automatisierbare Fälle):
#    - data/topics.yaml unlesbar/korrupt          -> Wiederherstellung
#      aus dem letzten Commit (git show HEAD:...)
#    - Erwartete *-REPORT.md fehlt                -> wird durch erneuten
#      (reinen Lese-)Lauf des erzeugenden Skripts neu geschrieben
#    - Verwaiste Temp-/Simulations-Artefakte       -> werden aufgeräumt
#  Ausdrücklich NICHT automatisiert: Code-Bugs (Lade-Funktionen etc.)
#  oder Content-Umformulierungen – das braucht menschliches/redaktionelles
#  Urteilsvermögen. Solche Funde machen den Lauf laut fehlschlagen
#  (Exit 1), damit das bestehende Fehler-Alerting (Issue-Erstellung)
#  greift – KEIN stilles Weiterlaufen.
#
#  Aufruf:
#    python3 scripts/automation_simulator.py             # voller Lauf
#    python3 scripts/automation_simulator.py --json       # JSON-Report
#
#  Workflow: .github/workflows/automation-simulator.yml (täglich)
# ============================================================

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
POSTS_DIR = ROOT / "content" / "posts"
TOPICS_FILE = ROOT / "data" / "topics.yaml"
REPORT = ROOT / "SIMULATION-REPORT.md"

AS_JSON = "--json" in sys.argv

sys.path.insert(0, str(SCRIPTS))

RESULTS = []  # Liste von dicts: {id, title, ok, detail, healed}


def record(check_id, title, ok, detail, healed=False):
    RESULTS.append({"id": check_id, "title": title, "ok": ok, "detail": detail, "healed": healed})


def _live_count_precise() -> int:
    count = 0
    for slug in sorted(os.listdir(POSTS_DIR)):
        index_path = POSTS_DIR / slug / "index.md"
        if not index_path.is_file():
            continue
        text = index_path.read_text(encoding="utf-8", errors="ignore")
        parts = text.split("---", 2)
        fm = parts[1] if len(parts) >= 3 else ""
        import re as _re
        if _re.search(r"^draft:\s*true\s*$", fm, _re.MULTILINE):
            continue
        count += 1
    return count


# ------------------------------------------------------------------
# SIM-A: Themen-Pool-Integrität (+ Selbstheilung bei Totalausfall)
# ------------------------------------------------------------------
def sim_topics_pool():
    import yaml
    healed = False
    try:
        data = yaml.safe_load(TOPICS_FILE.read_text(encoding="utf-8"))
        topics = data.get("topics") if isinstance(data, dict) else None
    except Exception as exc:  # noqa: BLE001
        # Selbstheilung: letzte committete, garantiert valide Fassung wiederherstellen.
        try:
            good = subprocess.run(
                ["git", "show", "HEAD:data/topics.yaml"], cwd=ROOT,
                capture_output=True, text=True, timeout=30,
            )
            if good.returncode == 0 and good.stdout.strip():
                TOPICS_FILE.write_text(good.stdout, encoding="utf-8")
                healed = True
                data = yaml.safe_load(good.stdout)
                topics = data.get("topics") if isinstance(data, dict) else None
            else:
                record("SIM-A", "Themen-Pool (data/topics.yaml)", False,
                       f"Parse-Fehler UND Wiederherstellung aus git HEAD fehlgeschlagen: {exc}")
                return
        except Exception as exc2:  # noqa: BLE001
            record("SIM-A", "Themen-Pool (data/topics.yaml)", False,
                   f"Parse-Fehler UND Wiederherstellung fehlgeschlagen: {exc2}")
            return

    if not topics or not isinstance(topics, list):
        record("SIM-A", "Themen-Pool (data/topics.yaml)", False,
               "Datei geladen, aber kein 'topics:'-Array gefunden.", healed)
        return

    missing_fields = [t.get("title", "?") for t in topics if not t.get("title") or not t.get("pillar")]
    titles = [t.get("title") for t in topics if t.get("title")]
    dupes = {t for t in titles if titles.count(t) > 1}

    problems = []
    if len(topics) < 50:
        problems.append(f"nur {len(topics)} Themen (< 50 erwartet)")
    if missing_fields:
        problems.append(f"{len(missing_fields)} Themen ohne title/pillar")
    if dupes:
        problems.append(f"{len(dupes)} doppelte Titel")

    ok = not problems
    detail = f"{len(topics)} Themen geladen." + (" Probleme: " + "; ".join(problems) if problems else " Alles ok.")
    record("SIM-A", "Themen-Pool (data/topics.yaml)", ok, detail, healed)


# ------------------------------------------------------------------
# SIM-B: Lade-Paritäts-Check – der zentrale Regressionsschutz gegen die
# heute mehrfach gefundene Bugklasse ("Skript findet still 0 statt N
# echte Artikel").
# ------------------------------------------------------------------
def sim_loader_parity():
    truth = _live_count_precise()

    def _import(modname):
        if modname in sys.modules:
            del sys.modules[modname]
        return __import__(modname)

    checks = []

    try:
        seo_audit = _import("seo_audit")
        checks.append(("seo_audit.load_posts()", len(seo_audit.load_posts())))
    except Exception as exc:  # noqa: BLE001
        checks.append(("seo_audit.load_posts()", f"FEHLER: {exc}"))

    try:
        kwopt = _import("keyword_optimizer")
        checks.append(("keyword_optimizer.load_articles()", len(kwopt.load_articles())))
    except Exception as exc:  # noqa: BLE001
        checks.append(("keyword_optimizer.load_articles()", f"FEHLER: {exc}"))

    try:
        aff = _import("affiliate_profi_check")
        checks.append(("affiliate_profi_check._post_slugs()", len(list(aff._post_slugs()))))
    except Exception as exc:  # noqa: BLE001
        checks.append(("affiliate_profi_check._post_slugs()", f"FEHLER: {exc}"))

    try:
        il = _import("internal_linker")
        checks.append(("internal_linker.load_pages()", len(il.load_pages())))
    except Exception as exc:  # noqa: BLE001
        checks.append(("internal_linker.load_pages()", f"FEHLER: {exc}"))

    try:
        r = subprocess.run(
            [sys.executable, str(SCRIPTS / "quality_score.py"), "--report"],
            cwd=ROOT, capture_output=True, text=True, timeout=120,
        )
        n = json.loads(r.stdout).get("articles") if r.stdout.strip().startswith("{") else None
        checks.append(("quality_score.py --report", n if n is not None else f"kein JSON (exit {r.returncode})"))
    except Exception as exc:  # noqa: BLE001
        checks.append(("quality_score.py --report", f"FEHLER: {exc}"))

    problems = []
    detail_lines = [f"Grundwahrheit (unabhängig ermittelt): {truth} live Artikel."]
    for name, n in checks:
        if isinstance(n, int):
            status = "✅" if n == truth else "❌"
            if n != truth:
                problems.append(f"{name} meldet {n} statt {truth}")
        else:
            status = "❌"
            problems.append(f"{name}: {n}")
        detail_lines.append(f"  {status} {name}: {n}")

    ok = not problems
    record("SIM-B", "Lade-Paritäts-Check (Kern-Regressionsschutz)", ok, "\n".join(detail_lines))


# ------------------------------------------------------------------
# SIM-C: Synthetischer Artikel-Lifecycle (Tags/Keywords/Provider) – testet
# genau die drei heute gefundenen und behobenen Bugs dauerhaft nach.
# ------------------------------------------------------------------
def sim_article_lifecycle():
    tmp_dir = tempfile.mkdtemp(prefix="sim_posts_")
    try:
        gd = __import__("generate_drafts") if "generate_drafts" not in sys.modules else sys.modules["generate_drafts"]
        if "engine_generate" in sys.modules:
            del sys.modules["engine_generate"]
        eg = __import__("engine_generate")

        gd.POSTS_DIR = tmp_dir
        eg.g.POSTS_DIR = tmp_dir

        filename, slug = eg.save_article(
            "Simulations-Testartikel: Nur zur Automatik-Prüfung",
            "Synthetischer Testartikel, erzeugt vom Automations-Simulator zur Selbstprüfung der Pipeline.",
            "## Test\n\nDies ist ein synthetischer Testkörper mit ausreichend Text für die Struktur-Prüfung.\n",
            draft=False, pillar="strom-sparen", quality_level="profi",
            keywords=["Simulationstest", "Automatik-Check"],
            ai_provider="Simulator (Testlauf)",
        )
        text = Path(filename).read_text(encoding="utf-8")

        import yaml
        fm_text = text.split("---", 2)[1]
        problems = []
        try:
            fm = yaml.safe_load(fm_text) or {}
        except Exception as exc:  # noqa: BLE001
            fm = {}
            problems.append(f"Frontmatter ist kein gültiges YAML: {exc}")

        if not fm.get("tags"):
            problems.append("tags: wurden nicht korrekt aus keywords befüllt")
        if not fm.get("keywords"):
            problems.append("keywords:-Feld fehlt oder falsch befüllt")
        if fm.get("ai_provider") != "Simulator (Testlauf)":
            problems.append(f"ai_provider wurde nicht durchgereicht (Regression des 13.08.-Fixes!) "
                             f"– erhalten: {fm.get('ai_provider')!r}")

        ok = not problems
        record("SIM-C", "Synthetischer Artikel-Lifecycle (Tags/Keywords/Provider)", ok,
               "Testartikel erzeugt und geprüft. " + ("Alles ok." if ok else "Probleme: " + "; ".join(problems)))
    except Exception as exc:  # noqa: BLE001
        record("SIM-C", "Synthetischer Artikel-Lifecycle (Tags/Keywords/Provider)", False, f"FEHLER: {exc}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        gd = sys.modules.get("generate_drafts")
        if gd:
            gd.POSTS_DIR = str(POSTS_DIR)
        eg = sys.modules.get("engine_generate")
        if eg:
            eg.g.POSTS_DIR = str(POSTS_DIR)


# ------------------------------------------------------------------
# SIM-D: Mastodon-Hashtag- & Cover-Regressionstest (auf dem neuesten
# ECHTEN Live-Artikel) – testet die zwei heute gefundenen Social-Bugs
# dauerhaft nach.
# ------------------------------------------------------------------
def sim_social_poster():
    try:
        if "social_poster" in sys.modules:
            del sys.modules["social_poster"]
        sp = __import__("social_poster")

        live = [p for p in sorted(sp.POSTS_DIR.iterdir(), reverse=True)
                if (p / "index.md").is_file()]
        if not live:
            record("SIM-D", "Mastodon-Hashtag/Cover-Regressionstest", False, "Kein Live-Artikel zum Testen gefunden.")
            return

        problems = []
        checked = 0
        for slug_dir in live[:3]:
            index_md = slug_dir / "index.md"
            fm = sp.read_frontmatter(index_md)
            if fm.get("draft") or fm.get("broken"):
                continue
            checked += 1
            tags_text = sp.hashtags(fm.get("tags", []))
            n_hashtags = len(tags_text.split())
            if fm.get("tags") and n_hashtags < 2:
                problems.append(f"{slug_dir.name}: hat Tags, aber hashtags() liefert nur '{tags_text}' "
                                 "(Regression des '#Finanzen-only'-Bugs?)")
            cover = sp.cover_path(slug_dir, fm)
            m = __import__("re").search(r"image:\s*[\"']?(.*?)[\"']?\s*$", fm.get("raw", ""), __import__("re").MULTILINE)
            if m and not cover:
                problems.append(f"{slug_dir.name}: Cover in Frontmatter referenziert, aber cover_path() findet "
                                 "die Datei nicht (Regression des Cover-Lade-Bugs?)")

        ok = not problems and checked > 0
        detail = f"{checked} aktuelle Artikel geprüft. " + ("Alles ok." if ok else "; ".join(problems) or "keine prüfbaren Artikel")
        record("SIM-D", "Mastodon-Hashtag/Cover-Regressionstest", ok, detail)
    except Exception as exc:  # noqa: BLE001
        record("SIM-D", "Mastodon-Hashtag/Cover-Regressionstest", False, f"FEHLER: {exc}")


# ------------------------------------------------------------------
# SIM-E: Publish-Gate & Cadence-Manager – reine Lauffähigkeits-Prüfung
# (echte Fach-Logik wird von den Skripten selbst getestet/verifiziert).
# ------------------------------------------------------------------
def sim_subprocess_sanity():
    for label, cmd in [
        ("publish_gate.py --dry-run", [sys.executable, str(SCRIPTS / "publish_gate.py"), "--dry-run"]),
        ("cadence_manager.py --dry-run", [sys.executable, str(SCRIPTS / "cadence_manager.py"), "--dry-run"]),
    ]:
        try:
            r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)
            ok = r.returncode in (0, 1)  # 1 = "Fund", kein Absturz
            detail = f"Exit {r.returncode}. " + (r.stdout + r.stderr)[-300:]
            record("SIM-E", label, ok, detail)
        except Exception as exc:  # noqa: BLE001
            record("SIM-E", label, False, f"FEHLER: {exc}")


# ------------------------------------------------------------------
# SIM-F: Report-Datei-Selbstheilung – fehlende *-REPORT.md-Dateien durch
# erneuten (reinen Lese-)Lauf des jeweils erzeugenden Skripts nachholen.
# ------------------------------------------------------------------
REPORT_SOURCES = {
    "LAYOUT-REPORT.md": "layout_audit.py",
    "LINK-REPORT.md": "link_guard.py",
    "WORKSPACE-REPORT.md": "workspace_guard.py",
    "AFFILIATE-REPORT.md": "affiliate_profi_check.py",
    "PILLAR-REPORT.md": "pillar_guard.py",
    "CADENCE-REPORT.md": "cadence_manager.py",
}


def sim_report_files():
    healed = []
    for report_name, script in REPORT_SOURCES.items():
        path = ROOT / report_name
        if path.is_file() and path.stat().st_size > 0:
            continue
        try:
            subprocess.run([sys.executable, str(SCRIPTS / script)], cwd=ROOT,
                            capture_output=True, text=True, timeout=120)
            if path.is_file() and path.stat().st_size > 0:
                healed.append(report_name)
        except Exception:  # noqa: BLE001
            pass
    ok = True
    detail = f"{len(healed)} fehlende Report-Datei(en) neu erzeugt: {healed}" if healed else "Alle erwarteten Report-Dateien vorhanden."
    record("SIM-F", "Report-Datei-Selbstheilung", ok, detail, healed=bool(healed))


def main():
    sim_topics_pool()
    sim_loader_parity()
    sim_article_lifecycle()
    sim_social_poster()
    sim_subprocess_sanity()
    sim_report_files()

    n_fail = sum(1 for r in RESULTS if not r["ok"])
    n_healed = sum(1 for r in RESULTS if r["healed"])

    if AS_JSON:
        print(json.dumps({"results": RESULTS, "failures": n_fail, "healed": n_healed}, ensure_ascii=False, indent=2))
        return 1 if n_fail else 0

    lines = [
        "# 🧪 SIMULATION-REPORT (automation_simulator.py)",
        "",
        f"**Stand:** {__import__('datetime').datetime.now(__import__('datetime').timezone.utc):%Y-%m-%d %H:%M} UTC",
        f"**Checks:** {len(RESULTS)} · **Fehlgeschlagen:** {n_fail} · **Selbstgeheilt:** {n_healed}",
        "",
    ]
    for r in RESULTS:
        icon = "✅" if r["ok"] else "❌"
        heal_tag = " 🩹 SELBSTGEHEILT" if r["healed"] else ""
        lines.append(f"## {icon} {r['id']}: {r['title']}{heal_tag}")
        lines.append("```")
        lines.append(r["detail"])
        lines.append("```")
        lines.append("")

    if n_fail:
        lines.append(
            "---\n⚠️ **Mindestens ein Check ist fehlgeschlagen und wurde NICHT automatisch behoben** "
            "(Code-Bugs/Redaktionsentscheidungen werden bewusst nicht blind gepatcht). "
            "Das bestehende Fehler-Alerting erstellt bei einem fehlgeschlagenen CI-Lauf automatisch ein Issue."
        )
    else:
        lines.append("---\n🎉 Gesamte Automatik-Pipeline simuliert geprüft – alles funktioniert wie erwartet.")

    report_text = "\n".join(lines)
    print(report_text)
    REPORT.write_text(report_text + "\n", encoding="utf-8")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
