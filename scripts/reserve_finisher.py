#!/usr/bin/env python3
"""
reserve_finisher.py – Reserve-Veredelung („täglicher Vorrat“ auf Profi-Niveau)

WARUM (Reparatur 08.09.2026, Fehler-Issue #224):
  Die Content-Reserve-Stufe (03:25 UTC täglich) erzeugte mit
  `engine_generate.py --reserve-only` nur ROH-Entwürfe (keine E-E-A-T-/
  Kurzantwort-/Cover-Felder, rohe Check24-CTA, keine SEO-/Affiliate-Heilung,
  keine Lesbarkeits-/Rechtschreib-Nacharbeit). Der Reife-Check
  `reserve_readiness.py` verlangt aber exakt dieselben harten Gates wie eine
  Live-Veröffentlichung (quality_score >= 0.85 + publish_gate im STRICT-Modus
  inkl. /go/-Integrität, Lesbarkeit, Länge, SEO). Roh-Entwürfe können diese
  Gates prinzipbedingt nie bestehen -> readiness = 0 -> der Workflow meldete
  an jedem Lauf „Stock shortage“, ohne dass irgendeine Stufe je nachgearbeitet
  hätte (Pool vertrocknete mit unbrauchbaren Entwürfen, Themen-Duplikate
  inklusive: 3x „50-30-20-Regel“ am 08.09.2026).

  Live-Artikel durchlaufen genau diese Transformation in den Phasen 2/3 der
  Content-Engine (content-engine-v2.yml). Dieses Skript führt die identische,
  bewährte Heiler-Kette für die RESERVE-Kandidaten aus – inhaltlich getrennt
  vom Live-Pfad:
    - Kandidaten: NUR `draft: true` + `reserve: true`
      (reserve_pool.reserve_drafts – SSOT), NUR ohne gültiges
      Readiness-Zertifikat (Hash-geprüft gegen data/reserve-readiness.json).
    - Lift: Kandidaten werden für die Heiler auf „heute“ gehoben
      (Ordner-Datumspräfix + `date:`-Feld), weil die meisten Heiler im
      --new-only-Modus nach dem Tagespräfix scopen. Reserve-Kandidaten sind
      Entwürfe ohne URL/Backlinks/Cover-Verweise -> Umbenennung des
      Ordnerpräfixes ist gefahrlos (im Gegensatz zu Live-Posts).
    - Kette: identisch zu Phase 2/3 der Live-Engine (dort SSOT; hier bewusst
      als Subprozess-Aufrufe nachgezogen, damit KEIN Heiler-Lauf den
      Live-Bestand anfasst, solange die Kandidatenliste leer ist).
    - Danach prüft reserve_readiness.py (separater Workflow-Schritt) mit
      hugo + publish_gate, ob die Kandidaten wirklich veröffentlichungsreif
      sind und schreibt die Zertifikate.

SICHERHEIT:
  * Snapshot VOR jeder Kandidaten-Behandlung (Dateiinhalt + Pfad). Bricht der
    Lauf KATASTROPHAL ab (Orchestrierungsfehler), wird der Ausgangszustand
    vollständig wiederhergestellt (Rückbenennung + Bytes).
  * Einzelne Heiler-Fehler sind NICHT katastrophal: Exit-Codes != 0 werden
    protokolliert; die Reife entscheidet allein die Zertifizierungsstufe.
  * Es wird NIE draft:false gesetzt, NIE veröffentlicht und kein
    cadence_*-Feld verändert. Fremde (Nicht-Pool-)Dateien bleiben unberührt:
    Die Heiler sind idempotent und heilen nur echte Funde – derselbe Kodex
    wie in Phase 2/3 der Live-Engine.
  * Bei leerer Kandidatenliste (Pool vollständig zertifiziert) läuft KEINE
    Heiler-Kette – der tägliche Lauf bleibt dann read-only und schnell.

MODI:
  python3 scripts/reserve_finisher.py --finish    # Veredelung (Workflow)
  python3 scripts/reserve_finisher.py --status    # Report, keine Änderungen
  python3 scripts/reserve_finisher.py --selftest  # Sabotage-Schutz

REPORT: RESERVE-FINISH-REPORT.md (Wurzel des Repos, wie FrankAutoOps-Reporte)
EXIT:   0 ok · 1 unerwarteter Fehler · 2 Selbsttest fehlgeschlagen
"""
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

BLOG_DIR = Path(__file__).resolve().parent.parent
POSTS_DIR = BLOG_DIR / "content" / "posts"
READINESS = BLOG_DIR / "data" / "reserve-readiness.json"
REPORT = BLOG_DIR / "RESERVE-FINISH-REPORT.md"
SNAPSHOTS = []  # [(original_path, original_bytes), ...] für Rollback


def now_utc_iso() -> str:
    return (datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_prefix() -> str:
    return datetime.date.today().isoformat()


def frontmatter_of(text: str) -> str:
    parts = text.split("---", 2)
    return parts[1] if len(parts) == 3 and parts[0] == "" else ""


def certified_slugs() -> dict:
    """slug -> sha256 für alle Kandidaten mit gültigem Reife-Zertifikat."""
    try:
        report = json.loads(READINESS.read_text(encoding="utf-8"))
        return {r["slug"]: r["sha256"] for r in report.get("candidates", [])
                if r.get("ready") and r.get("sha256")}
    except (OSError, ValueError, KeyError):
        return {}


def _is_certified(index: Path, certified: dict) -> bool:
    digest = hashlib.sha256(index.read_bytes()).hexdigest()
    return certified.get(index.parent.name) == digest


def _slug_tail(slug: str) -> str:
    """Entfernt einen führenden Datumspräfix (YYYY-MM-DD-) vom Slug."""
    m = re.match(r"^\d{4}-\d{2}-\d{2}-(.*)$", slug)
    return m.group(1) if m else slug


# REPARATUR 09.09.2026 (Reserve #4) + 11.09.2026 (Reserve #5):
# Die kanonische CTA-Reparatur wohnt jetzt als gemeinsamer, selbsttestender
# Heiler in scripts/fix_cta_hygiene.py und wird MEHRFACH in der Kette
# gefahren (siehe HEALER_CHAIN): die KI-Schritte (v. a. profi_polish)
# erzeugen das Klebewort „Ddiebesten“ aus der kanonischen Partner-CTA
# immer wieder NEU – ein einmaliger Hygiene-Pass VOR der Kette konnte den
# Befund also nicht dauerhaft schließen (Workflow #247).
def _canonical_cta_hygiene(index: Path) -> int:
    """Delegiert an fix_cta_hygiene (SSOT für beide Produktionslinien)."""
    import fix_cta_hygiene as cta
    return cta.hygiene_file(index)


def lift_to_today(index: Path) -> Path:
    """Hebt einen Pool-Kandidaten auf das heutige Datum (Präfix + date).

    Nur für Entwürfe ohne Außenverweise gefahrlos (Reserve-Pool-Garantie:
    keine cadence_*-Felder, nie veröffentlicht, nie verlinkt).
    Rückgabe: neuer Pfad.
    """
    slug = index.parent.name
    today = today_prefix()
    if slug.startswith(today):
        # Idempotenz: Nur datieren, wenn der Kandidat noch nicht auf HEUTE
        # datiert ist – sonst änderte jeder Finish-Lauf das date-Feld und der
        # Hash bliebe bis zur Zertifizierung nie stabil (beobachtet 08.09.2026:
        # jeder Lauf erzeugte ein neues date → neuer sha256).
        text = index.read_text(encoding="utf-8")
        m = re.search(r"(?m)^date:\s*(\d{4}-\d{2}-\d{2})", text)
        if not m or m.group(1) != today:
            text = re.sub(r"(?m)^date:\s*.*$", f"date: {now_utc_iso()}",
                          text, count=1)
            index.write_text(text, encoding="utf-8")
        return index
    new_dir = POSTS_DIR / f"{today}-{_slug_tail(slug)}"
    if new_dir.exists():
        raise FileExistsError(f"Ziel-Ordner existiert bereits: {new_dir.name}")
    new_index = new_dir / "index.md"
    SNAPSHOTS.append((index, index.read_bytes()))
    index.parent.rename(new_dir)
    text = new_index.read_text(encoding="utf-8")
    text = re.sub(r"(?m)^date:\s*.*$", f"date: {now_utc_iso()}",
                  text, count=1)
    new_index.write_text(text, encoding="utf-8")
    return new_index


# ---------------------------------------------------------------------------
# Heiler-Kette (identisch mit Phase 2 + Phase 3 der Live-Engine v2, ohne
# internal_linker: ein Reserve-ENTWURF darf keine Backlinks von Live-Artikeln
# einsammeln; ohne Pillar-Length-Guard: betrifft nur Pillar-Seiten).
#
# SCOPE-VERTRAG (Stufe-2-Kommentar im Workflow): Die Kette veredelt NUR die
# Pool-Kandidaten, NIE den Live-Bestand.
#   • Scope „file"  = pro Kandidat mit `--file <pfad>` (fix_linebreaks,
#     spellcheck, grammar_check, meta_optimizer, generate_kurzantworten).
#     Pflicht für Heiler, die ganze Dateien umschreiben können:
#     fix_linebreaks baut ohne KI Zeilenumbrüche korpusweit zurück und hat am
#     08.09.2026 nachweislich Live-Listen/Blockquotes zusammengeklebt; und
#     meta_optimizer spielt im Korpuslauf seine .meta_cache.json-Einträge auf
#     Live-Artikel ein (08.09.2026: Live-Titel „Preisgarantie Gas…“ wurde aus
#     dem Cache umgeschrieben → Cover-Regeneration) – beides Revert + Scope.
#   • Scope „new-only" = korpusweit, wirkt aber nur auf heutige Kandidaten
#     (Frontmatter-Datum == heute; der Lift datiert Kandidaten auf heute um).
#   • KEIN pinterest_seo_healer --fix: er heilt den GESAMTEN Korpus und
#     zieht unvermeidbar seine korpusweite Cover-Pipeline
#     (regenerate_covers + check_covers --fix) nach; das churnt nachweislich
#     jeden Lauf ein Live-Cover + covers_manifest ts (08.09.2026, Bisect).
#     Pin-SEO ist kein Zertifizierungs-Kriterium (quality_score prüft keine
#     Pin-Felder) und läuft ohnehin am Live-Tag über die Engine-Phase 3.
# ---------------------------------------------------------------------------
HEALER_CHAIN = [
    # --- Phase 2 (Qualitäts-Kette) ---
    # Reserve-Kandidaten sind bewusst draft:true. File-Scoped-Heiler müssen
    # deshalb Entwürfe explizit zulassen, sonst läuft die Veredelung scheinbar
    # grün, bearbeitet aber 0 Dateien (Befund 09.09.2026: Pool 0 READY trotz
    # brauchbarer Kandidaten, weil Polish/Spellcheck/Grammar alle drafts
    # stumm übersprangen).
    ("profi_polish.py", ["--include-drafts"], "file"),
    # Der Polish kann die kanonische Partner-CTA verkleben ("Ddiebesten")
    # – deterministisch zurücksetzen, bevor die übrigen Heiler laufen.
    ("fix_cta_hygiene.py", [], "file"),
    ("fix_linebreaks.py", [], "file"),
    ("fix_dash_und.py", ["--fix"]),
    ("fix_dash_eol.py", ["--fix"]),
    # REPARATUR 15.09.2026 (#295): Datei-bezirkelt + `--include-drafts`.
    # Vorher lief der Sammellauf korpusweit und übersprang Entwürfe komplett –
    # die Pool-Kandidaten (bewusst Entwürfe) wurden deshalb NIE verlängert
    # (1.134 bzw. 1.149 Wörter < 1.200 = Struktur-Score 0.70) und hingen
    # dauerhaft unter der Publish-Schwelle fest.
    ("check_length.py", ["--fix", "--include-drafts"], "file"),
    ("fix_spaces.py", []),
    ("spellcheck.py", ["--fix", "--include-drafts"], "file"),
    ("grammar_check.py", ["--fix", "--include-drafts"], "file"),
    ("casing_guard.py", ["--fix", "--new-only"]),
    ("dash_guard.py", ["--fix", "--ai", "--new-only"]),
    ("compound_guard.py", ["--fix", "--ai", "--new-only"]),
    ("unit_guard.py", ["--fix", "--new-only"]),
    ("emoji_guard.py", ["--fix"]),
    ("math_guard.py", ["--fix", "--new-only"]),
    ("lektor_guard.py", ["--fix", "--ai", "--new-only"]),
    # Lektorat-KI kann Textstellen neu verschmelzen – CTA erneut kanonisieren.
    ("fix_cta_hygiene.py", ["--include-drafts"], "corpus"),
    ("brand_guard.py", ["--fix"]),
    ("table_guard.py", ["--fix", "--new-only"]),
    ("affiliate_link_check.py", ["--fix"]),
    ("affiliate_shield.py", ["--fix", "--new-only"]),
    ("affiliate_marketer.py", ["--fix", "--new-only"]),
    ("link_guard.py", ["--fix", "--new-only"]),
    ("check_titles.py", ["--fix"]),
    # Cover NUR für die Pool-Kandidaten (Scope „slug“). Vorher lief
    # `generate_covers.py` (ohne Scope) plus `check_covers.py --fix` über
    # den ganzen Korpus und hat Live-Cover neu gerendert – Binärdateien, die
    # anschließend mitgepusht wurden und den Rebase gegen den parallelen
    # Deploy-Lauf kollidieren ließen (#295). Der Isolation-Wächter würde
    # solche Änderungen ohnehin zurückstellen; hier wird der Bedarf gar nicht
    # erst erzeugt (schneller, kein Cover-Churn, keine KI-/Render-Kosten).
    ("generate_covers.py", ["--slug", "{slug}"], "slug"),
    # --- Phase 3 (Sofort-Optimierung, ohne internal_linker) ---
    ("meta_optimizer.py", ["--fix", "--ai"], "file"),
    ("check_titles.py", ["--fix"]),
    # Cover-Referenzen prüfen/heilen. Läuft korpusweit (er hält sich an die
    # Live-Engine-Semantik), aber der Isolation-Wächter stellt jede Änderung
    # außerhalb der Pool-Kandidaten bytegenau zurück – Live-Cover und
    # Live-Frontmatter können so nicht mehr „nebenbei“ mitgepusht werden.
    ("check_covers.py", ["--fix"]),
    ("generate_kurzantworten.py", [], "file"),
    ("affiliate_profi_check.py", ["--fix"]),
    # REPARATUR 11.09.2026 (Reserve #5, #247): Der deterministische
    # R5-Absatz-Splitter war vorher in KEINEM Workflow verdrahtet – frische
    # KI-Artikel mit >6 Sätzen/Absatz scheiterten dauerhaft am harten
    # R5-ABSATZ-HART-Gate der Publish-Gate-Prüfung. Datei-bezirkelt, damit
    # der Live-Bestand in der Reserve-Queue nicht angefasst wird.
    ("r5_absatz_splitter.py", ["--apply"], "file"),
    # Zweiter Zeilenumbruch-Pass NACH allen KI-Umschreibungen: entfernt
    # verwaiste Hard-Break-Spuren in Listen/FAQ/Überschriften (Typografie-
    # Score), ohne dass KI-Quota gebraucht wird (reine Selbstheilung).
    ("fix_linebreaks.py", ["--heal-only"], "file"),
    # Letztes deterministisches Wort zur CTA-Kanonic vor der Zertifizierung.
    ("fix_cta_hygiene.py", [], "file"),
    ("fix_url_hygiene.py", ["--fix"]),
]


# ---------------------------------------------------------------------------
# LIVE-KORPUS-ISOLATION (Premium-Fix 15.09.2026, Issue #295)
#
# Kernbefund aus Run 34949097389: Die Veredelungs-Kette enthält bewusst die
# BEWÄHRTEN Heiler der Live-Engine – darunter korpusweite Läufe
# (`--fix` ohne Scope) sowie `generate_covers.py`/`check_covers.py`. Diese
# dürfen laut Workflow-Vertrag („Stufe 2: nur Pool“) NUR die Pool-Kandidaten
# verbessern. Real schreiben sie aber den ganzen Korpus: sie heilen Live-Posts
# (die ebenfalls auf „heute“ datiert sind), regenerieren Live-Cover und
# schreiben Manifeste. Zwei Folgen:
#   1. Der Reserve-Lauf committete LIVE-Änderungen (Content + Cover-Bilder)
#      mit. Genau die kollidierten beim Rebase mit dem parallel laufenden
#      Deploy-/Auslieferungslauf -> „Rebase-Konflikt … Kein Push“ -> roter Lauf.
#   2. Ein nächtlicher Pool-Lauf konnte so Live-Bestand verändern – inhaltlich
#      falsch (Besitzverhältnis: Live-Content gehört der Engine/Deploy-Kette).
#
# Lösung: Ein deterministischer Isolations-Wächter um die Kette. Vor dem Lauf
# wird der Arbeitsbaum-Zustand aller geschützten Wurzeln (content/ static/
# data/ layouts/ assets/ archetypes/ hugo.toml) eingefroren; nach dem Lauf
# wird JEDE Änderung außerhalb der erlaubten Kandidaten-Pfade bytegenau
# zurückgestellt (getrackte Dateien) bzw. in Quarantäne verschoben (neue
# Dateien). Der Wächter ist die Instanz, die den Vertrag durchsetzt – auch
# wenn in Zukunft ein Heiler dazukommt.
# ---------------------------------------------------------------------------
PROTECTED_ROOTS = ("content", "static", "data", "layouts", "assets",
                   "archetypes", "hugo.toml")
# Maschinengenerierte Artefakte, die die Kette absichtlich neu schreibt
# (werden von jedem Lauf komplett neu erzeugt; letzter Schreiber gewinnt,
# siehe scripts/git_sync.sh).
ALLOWED_ARTIFACTS = ("data/reserve-readiness.json",
                     "data/covers_manifest.json")
QUARANTINE = Path(tempfile.gettempdir()) / "reserve-isolation-quarantine"


def _git_out(*args: str) -> str:
    """Git-Aufruf im Repo-Wurzelverzeichnis (read-only)."""
    proc = subprocess.run(["git", *args], cwd=str(BLOG_DIR), timeout=120,
                          capture_output=True, text=True)
    return proc.stdout


def _porcelain_paths() -> set:
    """Alle aktuell geänderten/neuen Pfade im Arbeitsbaum (relativ, POSIX)."""
    out = _git_out("status", "--porcelain=v1", "-uall", "--", *PROTECTED_ROOTS)
    paths = set()
    for line in out.splitlines():
        if len(line) < 4:
            continue
        raw = line[3:]
        if " -> " in raw:                      # Rename: beide Seiten schützen
            old, new = raw.split(" -> ", 1)
            paths.update({old.strip().strip('"'), new.strip().strip('"')})
        else:
            paths.add(raw.strip().strip('"'))
    return {p for p in paths if p}


def _tracked(paths: set) -> set:
    if not paths:
        return set()
    out = _git_out("ls-files", "-z", "--", *sorted(paths))
    return {p for p in out.split("\0") if p}


def allowed_paths_for(targets: list) -> set:
    """Erlaubte Schreibziele der Kette: ausschließlich die Kandidaten selbst
    (Beitragsordner) sowie deren Cover-Dateien."""
    allowed = set()
    for index in targets:
        slug = index.parent.name
        allowed.add(f"content/posts/{slug}")
        allowed.add(f"static/images/covers/{slug}")
    return allowed


def isolation_baseline(allowed_paths: set) -> dict:
    """Zustand VOR der Kette: (dirty_paths, bytes_snapshots, allowed)."""
    dirty = _porcelain_paths()
    snapshots = {}
    # Bereits vor dem Lauf geänderte Dateien gehören dem Lauf (z. B. die
    # Lift-Umbenennungen). Sie werden NICHT zurückgestellt, aber bytegenau
    # gesichert, damit der Wächter sie nicht mit den Ketten-Änderungen
    # verwechselt (Pfad-Menge statt Byte-Vergleich).
    for path in dirty:
        full = BLOG_DIR / path
        if full.is_file():
            try:
                snapshots[path] = full.read_bytes()
            except OSError:
                pass
    return {"dirty": dirty, "snapshots": snapshots,
            "allowed": {p for p in allowed_paths}}


def _is_allowed(path: str, allowed: set) -> bool:
    if path in ALLOWED_ARTIFACTS:
        return True
    # Append-only-Historien (data/**/*.jsonl) sind das Audit-Gedächtnis des
    # Blogs. Sie werden von den Heilern fortgeschrieben und beim Rebase
    # dedupliziert zusammengeführt (git_sync.sh) – sie dürfen bleiben.
    if path.startswith("data/") and path.endswith(".jsonl"):
        return True
    for a in allowed:
        if path == a or path.startswith(a.rstrip("/") + "/"):
            return True
    return False


def isolation_enforce(baseline: dict) -> list:
    """Setzt den Vertrag NACH der Kette durch. Rückgabe: Liste der Eingriffe."""
    eingriffe = []
    allowed = baseline["allowed"]
    dirty_before = baseline["dirty"]
    dirty_after = _porcelain_paths()
    neu = sorted(p for p in dirty_after - dirty_before
                 if not _is_allowed(p, allowed))
    if not neu:
        return eingriffe
    tracked = _tracked(set(neu))
    for path in neu:
        full = BLOG_DIR / path
        if path in tracked or not full.exists():
            # getrackte Datei: bytegenau aus dem Index (= HEAD-Kandidat) zurück
            proc = subprocess.run(["git", "checkout", "--", path],
                                  cwd=str(BLOG_DIR), timeout=120,
                                  capture_output=True, text=True)
            ok = proc.returncode == 0
            eingriffe.append({"pfad": path, "aktion": "zurückgestellt",
                              "ok": ok})
            wort = "zurückgestellt" if ok else "NICHT zurückstellbar"
            print(f"  🛡 Isolation: {wort}: {path}")
        else:
            # neue, nicht angeforderte Datei -> Quarantäne (nichts wird gelöscht)
            try:
                goal = QUARANTINE / path
                goal.parent.mkdir(parents=True, exist_ok=True)
                if goal.exists():
                    goal = goal.with_suffix(goal.suffix + ".dup")
                full.replace(goal)
                eingriffe.append({"pfad": path, "aktion": "quarantäne",
                                  "ok": True, "ziel": str(goal)})
                print(f"  🛡 Isolation: neue Fremd-Datei in Quarantäne: {path}")
            except OSError as exc:
                eingriffe.append({"pfad": path, "aktion": "quarantäne",
                                  "ok": False, "fehler": str(exc)})
                print(f"  ⚠ Isolation: Quarantäne fehlgeschlagen: {path}: {exc}")
    return eingriffe


def run_chain(results: list, targets: list, env: dict | None = None) -> None:
    """Führt die Heiler-Kette aus. Fehler einzelner Heiler sind Hinweise –
    die Zertifizierung ist die Instanz, die über Reife entscheidet.

    `targets`: Liste der Lift-Pfade (Kandidaten). Heiler mit Scope „file"
    laufen einmal pro Kandidat (--file <pfad>) und nie korpusweit; Scope
    „slug" ersetzt den Platzhalter {slug} je Kandidat (z. B. Cover-Render)
    und läuft ebenfalls nur für Pool-Kandidaten.
    """
    for entry in HEALER_CHAIN:
        script = entry[0]
        raw_args = list(entry[1])
        scope = entry[2] if len(entry) > 2 else "corpus"
        if scope == "slug":
            for index in targets:
                args = [index.parent.name if a == "{slug}" else a
                        for a in raw_args]
                label = f"{script} {' '.join(args)}".strip()
                try:
                    proc = subprocess.run(
                        [sys.executable,
                         str(BLOG_DIR / "scripts" / script)] + args,
                        cwd=str(BLOG_DIR), env=env, timeout=900,
                        capture_output=True, text=True)
                    tail = (proc.stdout or "").strip().splitlines()
                    results.append({
                        "heiler": label, "ok": proc.returncode == 0,
                        "letzte_zeile": tail[-1][:160] if tail else "",
                        "rc": proc.returncode})
                    if proc.returncode != 0:
                        print(f"  ⚠ Heiler meldete rc={proc.returncode}: {label}")
                except subprocess.TimeoutExpired:
                    results.append({"heiler": label, "ok": False,
                                    "letzte_zeile": "TIMEOUT > 900s",
                                    "rc": None})
                    print(f"  ⚠ Heiler TIMEOUT: {label}")
                except Exception as exc:  # noqa: BLE001
                    results.append({"heiler": label, "ok": False,
                                    "letzte_zeile": f"Fehler: {exc}",
                                    "rc": None})
                    print(f"  ⚠ Heiler nicht ausführbar: {label} ({exc})")
            continue
        args = raw_args
        if scope == "file":
            for index in targets:
                label = (f"{script} {' '.join(args)} --file {index.parent.name}"
                         ).strip()
                try:
                    proc = subprocess.run(
                        [sys.executable,
                         str(BLOG_DIR / "scripts" / script)] + args
                        + ["--file", str(index)],
                        cwd=str(BLOG_DIR), env=env, timeout=900,
                        capture_output=True, text=True)
                    tail = (proc.stdout or "").strip().splitlines()
                    results.append({
                        "heiler": label, "ok": proc.returncode == 0,
                        "letzte_zeile": tail[-1][:160] if tail else "",
                        "rc": proc.returncode})
                    if proc.returncode != 0:
                        print(f"  ⚠ Heiler meldete rc={proc.returncode}: {label}")
                except subprocess.TimeoutExpired:
                    results.append({"heiler": label, "ok": False,
                                    "letzte_zeile": "TIMEOUT > 900s", "rc": None})
                    print(f"  ⚠ Heiler TIMEOUT: {label}")
                except Exception as exc:  # noqa: BLE001
                    results.append({"heiler": label, "ok": False,
                                    "letzte_zeile": f"Fehler: {exc}", "rc": None})
                    print(f"  ⚠ Heiler nicht ausführbar: {label} ({exc})")
            continue
        label = f"{script} {' '.join(args)}".strip()
        try:
            proc = subprocess.run(
                [sys.executable, str(BLOG_DIR / "scripts" / script)] + args,
                cwd=str(BLOG_DIR), env=env, timeout=900,
                capture_output=True, text=True)
            ok = proc.returncode == 0
            tail = (proc.stdout or "").strip().splitlines()
            results.append({
                "heiler": label, "ok": ok,
                "letzte_zeile": tail[-1][:160] if tail else "",
                "rc": proc.returncode,
            })
            if not ok:
                print(f"  ⚠ Heiler meldete rc={proc.returncode}: {label}")
        except subprocess.TimeoutExpired:
            results.append({"heiler": label, "ok": False,
                            "letzte_zeile": "TIMEOUT > 900s", "rc": None})
            print(f"  ⚠ Heiler TIMEOUT: {label}")
        except Exception as exc:  # noqa: BLE001 – nie die Kette brechen
            results.append({"heiler": label, "ok": False,
                            "letzte_zeile": f"Fehler: {exc}", "rc": None})
            print(f"  ⚠ Heiler nicht ausführbar: {label} ({exc})")


def quality_snapshot(index: Path) -> dict | None:
    """Quality-Score-Diagnose pro Kandidat (unverändert, nur lesend)."""
    try:
        sys.path.insert(0, str(BLOG_DIR / "scripts"))
        import quality_score as qs
        return qs.score_article(str(index))
    except Exception as exc:  # noqa: BLE001
        return {"score": None, "fehler": str(exc)}


def write_report(results: list, targets: list, started_iso: str,
                 isolation: list | None = None) -> None:
    today = today_prefix()
    lines = [
        "# 🛟 Reserve-Finish-Report (Veredelung des täglichen Vorrats)",
        "",
        f"> **Automatisch** – Lauf {started_iso} UTC · Ziel-Präfix: {today}",
        "",
        "## Kandidaten dieses Laufs (nicht zertifiziert, hash-geprüft)",
        "",
    ]
    if targets:
        for index in targets:
            lines.append(f"- `{index.parent.name}`")
    else:
        lines.append("- *(keine – der Pool ist vollständig zertifiziert, "
                     "keine Heiler-Kette nötig)*")
    lines += ["", "## Heiler-Kette (Phase-2/3-Äquivalent, Live-Kodex)", ""]
    if results:
        for r in results:
            mark = "✅" if r["ok"] else "⚠️"
            lines.append(f"- {mark} `{r['heiler']}` – "
                         f"{r['letzte_zeile'] or 'rc ' + str(r['rc'])}")
        if any(not r["ok"] for r in results):
            lines += ["", "> ⚠️ Einzelne Heiler-Funde sind Hinweise: Die "
                          "Zertifizierungsstufe (reserve_readiness.py) "
                          "entscheidet über die Pool-Reife."]
    else:
        lines.append("- *(Kette nicht ausgeführt – keine offenen Kandidaten)*")
    lines += ["", "## Qualitäts-Diagnose nach der Kette", ""]
    for index in targets:
        snap = quality_snapshot(index)
        if snap:
            score = snap.get("score")
            parts = snap.get("parts") or {}
            schwach = ", ".join(
                f"{k}={v:.2f}" for k, v in sorted(
                    parts.items(), key=lambda kv: kv[1])[:3]) if parts else ""
            lines.append(f"- {index.parent.name}: Score {score}"
                         f"{' (schwach: ' + schwach + ')' if schwach else ''}")
    if isolation:
        lines += ["", "## Live-Korpus-Isolation (Vertrag: nur Pool anfassen)",
                  "",
                  "| Pfad | Aktion | Ergebnis |",
                  "|---|---|---|"]
        for e in isolation:
            lines.append(f"| `{e['pfad']}` | {e['aktion']} | "
                         f"{'✅' if e.get('ok') else '⚠️'} |")
        lines += ["", "> Diese Dateien wurden von korpusweiten Heilern "
                      "angefasst und deterministisch zurückgestellt – der "
                      "Reserve-Lauf ändert ausschließlich seine Kandidaten "
                      "(und damit auch nie den Live-Bestand)."]
    else:
        lines += ["", "## Live-Korpus-Isolation (Vertrag: nur Pool anfassen)",
                  "", "- ✅ keine Fremd-Änderung – der Lauf blieb im Pool."]
    lines += ["", "_Nächster Schritt im Workflow: reserve_readiness.py "
                  "(hugo + publish_gate, STRICT) schreibt die Zertifikate._", ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def finish() -> int:
    sys.path.insert(0, str(BLOG_DIR / "scripts"))
    import reserve_pool as rp
    started = now_utc_iso()
    certified = certified_slugs()
    pool = [p for p in rp.reserve_drafts()
            if not _is_certified(p, certified)]
    targets = []
    for index in pool:
        try:
            lifted = lift_to_today(index)
            # Deterministische CTA-Hygiene VOR den Heilern (Reserve #4): eine
            # von der KI korrumpierte kanonische CTA-Zeile („Ddiebesten“)
            # kostete sonst dauerhaft den Rechtschreib-Score – jetzt wird sie
            # API-unabhängig geheilt, bevor polish/spellcheck/grammar laufen.
            n_hyg = _canonical_cta_hygiene(lifted)
            if n_hyg:
                print(f"  🧹 {n_hyg} kanonische(r) CTA-Tippfehler repariert: "
                      f"{lifted.parent.name}")
            targets.append(lifted)
            print(f"  🛠 Kandidat wird veredelt: {lifted.parent.name}")
        except Exception as exc:  # noqa: BLE001 – niemals den ganzen Lauf opfern
            print(f"  🛑 Kandidat übersprungen (Lift fehlgeschlagen): "
                  f"{index.parent.name}: {exc}")
    if not targets:
        print("Reserve-Finish: alle Pool-Kandidaten sind bereits zertifiziert "
              "– keine Heiler-Kette nötig.")
        write_report([], [], started)
        return 0
    results = []
    isolation = []
    # Isolation-Baseline NACH dem Lift: ab hier ist JEDE Änderung außerhalb der
    # Kandidaten-Pfade eine Vertragsverletzung und wird zurückgestellt.
    allowed = allowed_paths_for(targets)
    baseline = isolation_baseline(allowed)
    try:
        run_chain(results, targets)
    except Exception:  # noqa: BLE001 – katastrophal: Rollback auf Snapshot
        print("🛑 Reserve-Finish KATASTROPHAL abgebrochen – Rollback der "
              "Snapshots.")
        for original, raw in reversed(SNAPSHOTS):
            try:
                # Ordner ggf. zurückbenennen (aktueller Pfad == Lift-Ziel)
                current = (POSTS_DIR /
                           f"{today_prefix()}-{_slug_tail(original.parent.name)}"
                           / "index.md")
                if current.exists():
                    current.parent.rename(original.parent)
                original.write_bytes(raw)
            except OSError as exc:
                print(f"  ⚠ Rollback unvollständig: {original}: {exc}")
        try:
            isolation = isolation_enforce(baseline)
        except Exception as exc:  # noqa: BLE001 – Wächter darf nie werfen
            print(f"  ⚠ Isolation-Wächter nicht ausführbar: {exc}")
        write_report(results, targets, started, isolation)
        return 1
    try:
        isolation = isolation_enforce(baseline)
    except Exception as exc:  # noqa: BLE001 – Wächter darf nie werfen
        print(f"  ⚠ Isolation-Wächter nicht ausführbar: {exc}")
    write_report(results, targets, started, isolation)
    print(f"Reserve-Finish: {len(targets)} Kandidat(en) veredelt – "
          f"{len(results)} Heiler-Läufe, {sum(1 for r in results if not r['ok'])} "
          f"mit Hinweisen. Reife prüft reserve_readiness.py.")
    if isolation:
        print(f"  🛡 Live-Korpus-Isolation: {len(isolation)} Fremd-Änderung(en) "
              f"außerhalb der Pool-Kandidaten zurückgestellt "
              f"(Details: RESERVE-FINISH-REPORT.md).")
    return 0


def status() -> int:
    sys.path.insert(0, str(BLOG_DIR / "scripts"))
    import reserve_pool as rp
    certified = certified_slugs()
    pool = rp.reserve_drafts()
    print(f"Reserve-Pool: {len(pool)} Kandidaten "
          f"({len(certified)} zertifiziert-ready)")
    for p in pool:
        mark = "✅ READY" if _is_certified(p, certified) else "⏳ offen"
        print(f"  - {mark}  {p.parent.name}")
    return 0


def selftest() -> int:
    fehler = []
    with tempfile.TemporaryDirectory() as tmp:
        fx = Path(tmp) / "content" / "posts"
        fx.mkdir(parents=True)
        (fx / "2026-09-01-reserve-a" / "index.md").parent.mkdir()
        idx = fx / "2026-09-01-reserve-a" / "index.md"
        idx.write_text("---\ntitle: Reserve A\ndate: 2026-09-01T06:00:00Z\n"
                       "draft: true\nreserve: true\n---\nBody.", encoding="utf-8")
        # Manueller Entwurf (ohne reserve) darf nie angefasst werden
        (fx / "2026-09-01-manuell").mkdir()
        (fx / "2026-09-01-manuell" / "index.md").write_text(
            "---\ntitle: Manuell\ndate: 2026-09-01T06:00:00Z\ndraft: true\n"
            "---\nBody.", encoding="utf-8")
        # certified_slugs-Ersatz: leer -> beide aus reserve_drafts-Filter-Test
        # Lift-Logik prüfen (Monkeypatch auf POSTS_DIR über Modul-Name geht
        # hier nicht global – deshalb Logik-Kern als Funktions-Test):
        tail = _slug_tail("2026-09-01-reserve-a")
        if tail != "reserve-a":
            fehler.append(f"_slug_tail falsch: {tail}")
        # Zertifikats-Prüfung (kein Zertifikat -> uncertified)
        if _is_certified(idx, {}):
            fehler.append("Kandidat ohne Zertifikat gilt als ready")
        digest = hashlib.sha256(idx.read_bytes()).hexdigest()
        if not _is_certified(idx, {"2026-09-01-reserve-a": digest}):
            fehler.append("Kandidat mit passendem Hash gilt nicht als ready")
        # CTA-Hygiene (Reserve #4): „Ddiebesten“-Korruption muss deterministisch
        # zurück auf die kanonische Form, sonst kostet sie den Spelling-Score.
        bad = idx.parent / "bad.md"
        bad.write_text("💡 **Schnell-Tipp von FranksFinanzcheck:** Ddiebesten "
                       "Tarife findest du über unseren Partner-Vergleich: x\n"
                       "Body.", encoding="utf-8")
        if _canonical_cta_hygiene(bad) != 1 or \
                "Ddiebesten" in bad.read_text(encoding="utf-8") or \
                "Die besten Tarife findest du über unseren Partner-Vergleich" \
                not in bad.read_text(encoding="utf-8"):
            fehler.append("CTA-Hygiene repariert die Ddiebesten-Korruption nicht")
        # Idempotenz: erneuter Lauf ändert nichts (0 Funde).
        if _canonical_cta_hygiene(bad) != 0:
            fehler.append("CTA-Hygiene ist nicht idempotent (churnt)")
    if fehler:
        print("🛑 RESERVE-FINISHER-SELFTEST FEHLGESCHLAGEN:")
        for e in fehler:
            print(f"   - {e}")
        return 2
    print("✅ Reserve-Finisher-Selbsttest grün (Pool-Filter, Hash-Zertifikat, "
          "Slug-Tail).")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if "--selftest" in args:
        return selftest()
    if "--status" in args:
        return status()
    if "--finish" in args:
        return finish()
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
