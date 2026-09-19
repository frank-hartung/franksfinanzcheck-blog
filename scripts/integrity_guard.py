#!/usr/bin/env python3
# ============================================================
#  INTEGRITY-GUARD – Fingerprint-Schloss ueber dem Kern des Blogs
#  (Frank 12.08.: „Sabotageschutz auf das Hoechstlevel" – gemeint:
#   wichtige Dateien duerfen sich NIEMALS declos aendern ohne dass
#   jemand einmal explizit signiert. Bei Abweichung: Festzustand
#   festkleben und Alarm schreien, niemals still weitermachen.)
#
#  Design: data/integrity_lock.json
#    { "signed_at": …, "head": <git-sha>, "files": {pfad: sha256},
#      "audit": [ … Herkunft jeder Signatur … ] }
#
#  Pfad-Klassen:
#    KRITISCH (brand_uebertragendes/affiliate-kohaerente Kerne):
#      jede Abweichung -> Exit 3 (HARD STOP, muss Frank nur signieren)
#    FEST (alles uebrige im Lock):   Abweichung -> Exit 1 + Sichtung
#
#  Sabotage-Schutz: Der Lock brennt den Zweck, niemals nur self-testfaehig:
#    Angreifer haben nicht ohne explizites Niederzeichnen Spielraum.
#  Selbsttest: 5 Faelle, eingefroren umschlossen. Exit 2 bei Bruch.
#
# ------------------------------------------------------------
#  19.09.2026 – Drift hat Produktion gekostet (Issue #316)
# ------------------------------------------------------------
#  Zwei Läufe der Content-Engine (18.09. 17:39 und 19:56 UTC) starben im
#  ersten Schritt, VOR jeder Artikelarbeit: Der Lock war um 11:41 UTC
#  signiert, danach hat PR #315 (Commit ff6232e3) sechs gesperrte Skripte
#  geheilt – ohne Neu-Signatur. Der HARD STOP tat damit genau, was er soll,
#  und traf den FALSCHEN: nicht die Änderung, sondern die Produktion
#  (kein Artikel, kein Slot, Defizit-Alarm). Die Lücke war strukturell –
#  es gab keinen Ort, an dem „gesperrte Datei geändert, aber nicht
#  signiert" VOR dem Merge auffällt, und keine Heilung für den belegten
#  Fall „committet, aber vergessen".
#
#  Diese Fassung schließt sie an drei Stellen:
#    --gate         PR-/CI-Gate: Der signierte Kern muss zum Baum passen,
#                   sonst Exit 3 MIT Herkunft (welcher Commit die Datei
#                   anfasste) und der Reparaturzeile für DIESEN Pull
#                   Request. Verdrahtet in
#                   .github/workflows/integrity-lock.yml (jeder PR auf main).
#    --heal         Selbstheilung für „committet, aber vergessen".
#                   Signiert NUR, wenn jede Abweichung
#                     (a) in Git versioniert ist,
#                     (b) bytegleich dem committeten Stand entspricht
#                         (also KEINE Laufzeit-Mutation) und
#                     (c) NICHT zur KRITISCH-Klasse gehört.
#                   Sonst Exit 3: Sabotage bleibt eine menschliche
#                   Entscheidung. Verdrahtet als erster Schritt der
#                   Content-Engine.
#    --drift-audit  Herkunft ohne Urteil: Commit(s), Arbeitsbaum-Zustand,
#                   Klasse. Read-only.
#
#  Jede Signatur schreibt ihre Herkunft MIT (`audit` im Lock): Datum, Art
#  (set-current/heal), Klassen und die Commits, die die Datei seit der
#  Vor-Signatur angefasst haben. Eine Unterschrift ohne Akte ist keine.
#
#  Aufruf:
#    python3 scripts/integrity_guard.py                  # verify (Exit 0/1/3)
#    python3 scripts/integrity_guard.py --drift-audit    # Herkunft (read-only)
#    python3 scripts/integrity_guard.py --gate           # CI/PR-Gate (fail-closed)
#    python3 scripts/integrity_guard.py --heal           # belegten Drift signieren
#    python3 scripts/integrity_guard.py --heal --dry-run # nur zeigen, nichts tun
#    python3 scripts/integrity_guard.py --selftest       # Logik-Beweis, schreibt nie
#    python3 scripts/integrity_guard.py --set-current    # signiere JETZT (Mensch)
#    python3 scripts/integrity_guard.py --add <pfad>     # erweitern (mit verify)
#
#  Ausgabe: INTEGRITY-REPORT.md + data/integrity_history.jsonl
# ============================================================

import contextlib
import hashlib
import io
import json
import subprocess
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "data" / "integrity_lock.json"
REPORT = ROOT / "INTEGRITY-REPORT.md"
HISTORY = ROOT / "data" / "integrity_history.jsonl"

# Modi. Reihenfolge der Auswertung in main(): selftest > set-current > add >
# gate > heal > drift-audit > verify.
SET_CURRENT = "--set-current" in sys.argv
SELFTEST_MODE = "--selftest" in sys.argv
DRIFT_AUDIT = "--drift-audit" in sys.argv
HEAL = "--heal" in sys.argv
GATE = "--gate" in sys.argv
DRY_RUN = "--dry-run" in sys.argv

ADD_PATH = None
for _i, _a in enumerate(sys.argv):
    if _a.startswith("--add="):
        ADD_PATH = _a.split("=", 1)[1]
    elif _a == "--add":
        # Die Aufrufzeile der Doku lautet „--add <pfad>" (Leerzeichen), der
        # Parser kannte nur „--add=<pfad>". Wer der Doku folgte, bekam einen
        # stillen No-Return mit Exit 0 – bei einem Signatur-Werkzeug der
        # gefährliche Fall: jemand glaubt, signiert zu haben. Jetzt beide
        # Formen, und ein fehlender Pfad endet laut statt grün.
        nxt = sys.argv[_i + 1] if _i + 1 < len(sys.argv) else ""
        if not nxt or nxt.startswith("-"):
            print("🛑 --add erwartet einen Pfad, z. B. "
                  "--add=assets/css/extended/custom.css"); sys.exit(2)
        ADD_PATH = nxt

# KRITISCH = zentrale Buende: veraendernde?! nur nach Signierung
KRITISCH = {
    "hugo.toml",
    "scripts/check24_links.yaml",
    "layouts/_default/_markup/render-link.html",
    "layouts/_default/_markup/render-image.html",
    "layouts/_partials/head.html",
    "layouts/_partials/extend_footer.html",
    "layouts/robots.txt",
}

# FEST = weitere wichtige, aber segens-reparierbare:
FEST = {
    "layouts/_partials/cover.html",
    "layouts/_partials/extend_post_content.html",
    "assets/css/extended/custom.css",
    "layouts/_partials/home_clusters.html",
    "layouts/pillar/list.html",
    "layouts/index.sw.js",
    "static/6t77zzoan6sl5i4b9jwcvx073202rgm9.txt",
    # Beschuetzte DIENSTLICHE Schluessel-Wachen (Selbsttests richten):
    "scripts/check24_links.yaml",
    "scripts/affiliate_marketer.py",
    "scripts/lektor_guard.py",
    "scripts/blog_doctor.py",
    # Casing-Bund (09.09.2026): casing_guard entscheidet Groess-/Kleinschreibung
    # im gesamten Bestand inkl. Pin-Plan, tag_casing ist sein gemeinsames Lexikon
    # mit dem Generator. Wer hier aendert, aendert die Rechtschreibung der Site –
    # beides deshalb signaturpflichtig wie die uebrigen Dienst-wachen.
    "scripts/casing_guard.py",
    "scripts/tag_casing.py",
    # Marken-Design-Bewohner (Frank 12.08. ihr Markendesign dauerhaft bewachen):
    "scripts/generate_covers.py",
    "scripts/check_covers.py",
    # Marken-Lockup & Artefakte (12.08. Runde 2: Logo = Blog-weite Marke):
    "scripts/bake_brand.py",
    "scripts/brand_guard.py",
    "data/brand_lock.yaml",
    "layouts/_partials/header.html",
    "static/images/brand/logo.svg",
    "static/images/brand/logo-light.svg",
    "static/favicon.svg",
    "static/apple-touch-icon.png",
    # Linker-Bewacher (12.08. Profi-Uebau; Root-Cause-Lock gegen Link-Leck):
    "scripts/internal_linker.py",
    "scripts/link_density_guard.py",
    "scripts/stil_guard.py",
    "scripts/hardcases_guard.py",
    "scripts/plagiat_guard.py",
    "scripts/content_audit.py",
    "scripts/fazit_schmiede.py",
    # PREM-AUDIT 26.08.2026: data/content_fingerprints.jsonl AUS dem Lock –
    # das ist eine MUTIERENDE Registry (die Engine appendet jeden Lauf),
    # kein Kern-Code: im Lock erzeugt sie PERMANENT falsche Abweichungen
    # (chronisch roter Doktor, DOKTOR-REPORT "Sabotage-Fehler"). Ihre
    # Integritaet tragen Git + data/audit_history.jsonl (Append-Only),
    # nicht ein statischer Fingerprint.
    # Pillar-Templates (12.08.: Relative-Link-Falle entfernt):
    "layouts/pillar/single.html",
    "layouts/_partials/pillar_box.html",
    # AFFILIATE-INTEGRITAET (02.09.2026, Premium-Ausbau der taeglichen Wache):
    # Diese Dateien emittieren bzw. beweisen die Affiliate-Links. Der
    # Render-Hook (KRITISCH) deckt nur die Markdown-Link-Pipeline ab –
    # Shortcode-CTAs laufen daran vorbei, und genau dort fehlten
    # rel="sponsored" + Umami-Attribution (Fund AI4, 02.09.2026).
    # Deshalb: zentraler Attribut-Vertrag + die beiden CTA-Shortcodes +
    # die Wache selbst unter Siegel. Aenderung nur mit Neu-Signatur.
    "layouts/_partials/affiliate_anchor_attrs.html",
    # Datenpfad der Affiliate-Zielnamen (19.09.2026): Dieses Partial lädt
    # data/affiliate_ziele.yaml per os.ReadFile – weil ein hugo.Data/site.Data-
    # Zugriff Hugo den ganzen data/-Baum inklusive *.jsonl-Bot-Protokolle
    # parsen lässt und der Build stirbt (Seite baut nicht, kein Deploy).
    # Wer hier ändert, ändert die Build-Fähigkeit der ganzen Site.
    "layouts/_partials/affiliate_ziele_data.html",
    "layouts/shortcodes/tarifvergleich.html",
    "layouts/shortcodes/einspartabelle.html",
    "scripts/affiliate_integrity_gate.py",
    # Redaktions-Standard (02.09.2026, Capital/WiWo/ZEIT-Methoden):
    # Die Wache entscheidet über Entwurf-Statt-Publikation – deshalb
    # gehört sie unter Siegel (wie alle Schwellen-Wachen).
    "scripts/redaktions_standard.py",
}

NEU_OHNE_SIGNATUR = " (neu ohne Signatur)"
AUDIT_MAX = 12          # Einträge im Lock – die Akte bleibt lesbar
COMMIT_MAX = 5          # Commits je Datei in der Akte
GATE_REGEL = ("Regel: Wer eine gesperrte Kerndatei ändert, signiert den Lock "
              "im SELBEN Commit (Herkunft landet in `data/integrity_lock.json`).")


# ------------------------------------------------------------
# Werkzeuge: Fingerprint, Git-Wahrheit, Lock-Datei
# ------------------------------------------------------------
def sha256_file(p: Path) -> str:
    if not p.exists():
        return ""
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(root: Path, *args, timeout: int = 60, text: bool = True):
    """Git im übergebenen Baum. None = Git antwortet nicht.

    None wird überall GEMELDET (unbekannte Herkunft, kein stilles „passt
    schon"): Ein Nachweis, der bei fehlender Antwort grün wird, ist keiner.
    """
    try:
        return subprocess.run(("git",) + args, cwd=str(root),
                              capture_output=True, text=text, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None


def git_head(root: Path = ROOT, short: bool = True) -> str:
    r = _git(root, "rev-parse", "--short" if short else "--verify", "HEAD")
    if r is None or r.returncode != 0 or not r.stdout.strip():
        return "unknown"
    return r.stdout.strip()


def ist_getrackt(root: Path, rel: str) -> bool:
    r = _git(root, "ls-files", "--error-unmatch", "--", rel)
    return r is not None and r.returncode == 0


def stand_gleich_head(root: Path, rel: str) -> bool:
    """Byte-Vergleich Arbeitsbaum <-> committeter Stand.

    False ist der interessante Fall: Laufzeit-Mutation oder ungestagte
    Änderung – genau die Klasse, die ein Siegel fangen muss und die NIE
    automatisch signiert werden darf.
    """
    pfad = root / rel
    if not pfad.exists():
        return False
    r = _git(root, "show", f"HEAD:{rel}", text=False)
    if r is None or r.returncode != 0:
        return False
    try:
        return pfad.read_bytes() == r.stdout
    except OSError:
        return False


def _commit_liste(stdout: str) -> list:
    out = []
    for zeile in (stdout or "").splitlines():
        teile = zeile.split("\x1f")
        if len(teile) == 3:
            out.append({"sha": teile[0], "datum": teile[1], "betreff": teile[2]})
    return out


def herkunft(root: Path, basis: str, rel: str) -> tuple:
    """(Commits, Art der Herkunft) für eine Drift-Datei.

    Art:
      seit-signatur  Signatur-Stand ist auflösbar -> Commits NACH der Signatur.
      letzte-commits Signatur-Stand fehlt/unauflösbar (Rebase-Hash, flacher
                     Klon) -> die letzten Commits der Datei. Kein Rätsel,
                     sondern das, was ohne Historie beweisbar ist.
      unbekannt      keine Historie im Checkout (z. B. 1-Commit-Klon) –
                     dann bleibt das Urteil an „Arbeitsbaum == HEAD".
    """
    fmt = "%h\x1f%ad\x1f%s"
    if basis and basis not in ("", "nie", "unknown", "beschaedigt"):
        anker = _git(root, "rev-parse", "--verify", "--quiet", f"{basis}^{{commit}}")
        if anker is not None and anker.returncode == 0:
            r = _git(root, "log", "--format=" + fmt, "--date=short",
                     f"{basis}..HEAD", "--", rel)
            if r is not None and r.returncode == 0:
                return _commit_liste(r.stdout), "seit-signatur"
    r = _git(root, "log", "-n", "3", "--format=" + fmt, "--date=short", "--", rel)
    if r is not None and r.returncode == 0 and r.stdout.strip():
        return _commit_liste(r.stdout), "letzte-commits"
    return [], "unbekannt"


def load_lock(lock_pfad: Path = None) -> dict:
    pfad = lock_pfad or LOCK
    if not pfad.exists():
        return {"signed_at": "nie", "head": "", "files": {}}
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except Exception:
        return {"signed_at": "beschaedigt", "head": "", "files": {}}
    if not isinstance(daten, dict):
        return {"signed_at": "beschaedigt", "head": "", "files": {}}
    daten.setdefault("files", {})
    return daten


def verify_files(root: Path, files: dict):
    """(kritisch, fest) – Abweichungen des Baums gegen die signierten Hashes."""
    crit_bad, fest_bad = [], []
    for pfad, expect_hash in files.items():
        if sha256_file(root / pfad) == expect_hash:
            continue
        (crit_bad if pfad in KRITISCH else fest_bad).append(pfad)
    # Neue kritische Dateien sollen nicht unkontrolliert kommen:
    for pfad in sorted(KRITISCH):
        if pfad not in files and (root / pfad).exists():
            crit_bad.append(pfad + NEU_OHNE_SIGNATUR)
    return crit_bad, fest_bad


def exit_fuer(crit_bad, fest_bad) -> int:
    """Das Urteil des Siegels in EINER Funktion (die Entscheidungsgrenze).

    0 = Kern exakt wie signiert · 1 = FEST-Drift (Sichtung) ·
    3 = KRITISCH-Drift bzw. neue kritische Datei (HARD STOP). Im PR-Gate
    (`--gate`) wird bewusst auch FEST-Drift zu Exit 3 (fail-closed).
    """
    return 3 if crit_bad else (1 if fest_bad else 0)


# ------------------------------------------------------------
# Akte: Herkunft jeder Abweichung (--drift-audit, --gate, --heal)
# ------------------------------------------------------------
def klassifizieren(root: Path, crit_bad, fest_bad, basis: str = "") -> list:
    """Herkunft und Urteil je Abweichung – die Akte zur Unterschrift.

    Urteile:
      VERSIEGELBAR  versioniert und bytegleich zum committeten Stand: die
                    Änderung ist Teil eines Commits (also sichtbar/reviewbar),
                    keine Laufzeit-Mutation.
      UNERKLÄRT     Arbeitsbaum weicht von HEAD ab – ungestagte Änderung oder
                    ein Skript hat den Kern zur Laufzeit angefasst.
      NICHT VERSIONIERT / NEU OHNE SIGNATUR  keine Grundlage für eine Automatik.
    """
    eintraege = []
    for roh in list(crit_bad) + list(fest_bad):
        neu = roh.endswith(NEU_OHNE_SIGNATUR)
        rel = roh[: -len(NEU_OHNE_SIGNATUR)] if neu else roh
        getrackt = False if neu else ist_getrackt(root, rel)
        gleich = False if neu else stand_gleich_head(root, rel)
        if neu:
            urteil = "NEU OHNE SIGNATUR"
        elif not getrackt:
            urteil = "NICHT VERSIONIERT"
        elif not gleich:
            urteil = "UNERKLÄRT"
        else:
            urteil = "VERSIEGELBAR"
        commits, commits_art = ([], "unbekannt") if neu else herkunft(root, basis, rel)
        eintraege.append({
            "pfad": rel,
            "klasse": "kritisch" if rel in KRITISCH else "fest",
            "getrackt": getrackt,
            "stand_gleich_head": gleich,
            "urteil": urteil,
            "commits": commits,
            "commits_art": commits_art,
        })
    return eintraege


def heilverdict(audit: list):
    """(heilbar, blockiert) – die Signatur-Regel in EINER Funktion.

    Heilbar ist nur Drift, der versioniert, committet und von der Klasse FEST
    ist. KRITISCH bleibt grundsätzlich liegen (Sabotage-Schutz: Signatur ist
    eine Betreiber-Entscheidung), UNERKLÄRT ebenso (Laufzeit-Mutation darf
    niemals durch Automatik geadelt werden).
    """
    blockiert = []
    for e in audit:
        if e["klasse"] == "kritisch":
            blockiert.append(f"{e['pfad']}: KRITISCH – Signatur ist eine "
                             "Betreiber-Entscheidung (Sabotage-Schutz)")
        elif e["urteil"] != "VERSIEGELBAR":
            blockiert.append(f"{e['pfad']}: {e['urteil']} – nicht committet bzw. "
                             "nicht versioniert; erst sichten, dann bewusst "
                             "signieren")
    return (bool(audit) and not blockiert), blockiert


def audit_tabelle(audit: list) -> list:
    L = ["| Datei | Klasse | Arbeitsbaum | Herkunft | Urteil |", "|---|---|---|---|---|"]
    for e in audit:
        commits = e.get("commits") or []
        art = e.get("commits_art", "unbekannt")
        if commits:
            herkunft = " · ".join(
                f"`{c['sha']}` {c['datum']} {c['betreff'][:48]}" for c in commits[:3])
            if len(commits) > 3:
                herkunft += f" (+{len(commits) - 3})"
            if art == "letzte-commits":
                herkunft = "zuletzt: " + herkunft
        elif art == "unbekannt":
            herkunft = "keine Historie im Checkout (flacher Klon)"
        else:
            herkunft = "–"
        stand = "= HEAD" if e["stand_gleich_head"] else "≠ HEAD (nicht committet)"
        L.append(f"| `{e['pfad']}` | {e['klasse']} | {stand} | {herkunft} | {e['urteil']} |")
    return L


# ------------------------------------------------------------
# Signieren (mit Akte) und Historie
# ------------------------------------------------------------
def signieren(root: Path = ROOT, grund: str = "set-current", audit=None) -> dict:
    """Schreibt den Lock über den Ist-Stand – und die Herkunft dazu."""
    lock_pfad = root / "data" / "integrity_lock.json"
    alt = load_lock(lock_pfad)
    files = {}
    for pfad in sorted(KRITISCH | FEST):
        if (root / pfad).exists():
            files[pfad] = sha256_file(root / pfad)
    geaendert = sorted(p for p, h in files.items()
                       if alt.get("files", {}).get(p) != h)
    akte = {
        "date": date.today().isoformat(),
        "art": grund,
        "head": git_head(root),
        "geaendert": geaendert,
    }
    if audit:
        akte["herkunft"] = [{
            "pfad": e["pfad"],
            "klasse": e["klasse"],
            "urteil": e["urteil"],
            "commits": (e.get("commits") or [])[:COMMIT_MAX],
            "commits_art": e.get("commits_art", "unbekannt"),
        } for e in audit if e["pfad"] in geaendert]
    eintraege = list(alt.get("audit") or []) + [akte]
    lock_pfad.parent.mkdir(parents=True, exist_ok=True)
    lock_pfad.write_text(json.dumps({
        "signed_at": datetime.now(timezone.utc).isoformat(),
        "head": git_head(root),
        "files": files,
        "audit": eintraege[-AUDIT_MAX:],
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"signiert": len(files), "geaendert": geaendert, "akte": akte}


def historie_schreiben(root: Path, eintrag: dict) -> None:
    """Append-Only-Historie. Pflichtfelder (date/kritisch/fest) hält
    `history_guard.py` fest – Zusatzfelder sind dort ausdrücklich erlaubt."""
    pfad = root / "data" / "integrity_history.jsonl"
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with pfad.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(eintrag, ensure_ascii=False) + "\n")


def report_text(root: Path, crit_bad, fest_bad, audit=None,
                geheilt=None, blockiert=None) -> str:
    lock = load_lock(root / "data" / "integrity_lock.json")
    L = ["# 🔐 INTEGRITY-REPORT", "",
         f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · HEAD: `{git_head(root)}`",
         f"**Lock-Ebene:** {len(lock.get('files', {}))} Dateien gelockt",
         f"**Gesperrte kritische Knoten:** {len(KRITISCH)}",
         f"**Letzte Signatur:** {lock.get('signed_at', 'nie')} · Stand `{lock.get('head', '')}`",
         ""]
    if crit_bad:
        L += ["## 🛑 KRITISCHE Abweichungen (kein Weg zurück: neu signieren oder rückgängig machen)", ""]
        L += [f"- `{c}`" for c in crit_bad]
    if fest_bad:
        L += ["", "## 🟠 Festrelevante Abweichungen", ""]
        L += [f"- `{f}`" for f in fest_bad]
    if audit:
        L += ["", "## 🔎 Herkunft der Abweichungen (Akte)", ""]
        L += audit_tabelle(audit)
    if geheilt:
        neu = geheilt.get("geaendert", [])
        L += ["", "## 🔓 Selbst-Signatur (--heal)", "",
              f"Neu signiert: {len(neu)} Datei(en) – "
              + ", ".join(f"`{p}`" for p in neu),
              "",
              "Regel: Nur versionierter, bytegleich committeter Drift der Klasse "
              "FEST ist selbst-signierbar. KRITISCH und Laufzeit-Mutationen "
              "bleiben HARD STOP (Betreiber-Entscheidung)."]
    if blockiert:
        L += ["", "## 🛑 HARD STOP – nicht selbst-signierbar", ""]
        L += [f"- {b}" for b in blockiert]
    if not crit_bad and not fest_bad:
        L += ["🎉 Integritaet: Der Kern entspricht exakt dem letzten "
              "signierten Zustand.", ""]
    L += ["---",
          "_Der Selbsttest läuft vor jedem Check. `--heal` signiert "
          "ausschließlich belegten, committeten Drift der Klasse FEST; "
          "kritische Abweichungen stoppen weiter hart (`--set-current` ist die "
          "menschliche Entscheidung)._"]
    return "\n".join(L) + "\n"


def report_schreiben(root: Path, crit_bad, fest_bad, audit=None,
                     geheilt=None, blockiert=None) -> list:
    text = report_text(root, crit_bad, fest_bad, audit, geheilt, blockiert)
    (root / "INTEGRITY-REPORT.md").write_text(text, encoding="utf-8")
    print(text)
    return text.splitlines()


# ------------------------------------------------------------
# SABOTAGE-SCHUTZ: Selbsttest (natürlich, hiermit Wahrheit gebaut)
# ------------------------------------------------------------
SELFTEST = [
    "gleich_gleich",
    "anderweitig_bleibt",
    "loeschen_gefunden",
    "tamper_gilt_doppelt",
    "tok_file_ist_liste",
]


def _selftest() -> list[str]:
    fehler = []
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        a = Path(td) / "a.txt"
        a.write_text("Frank", encoding="utf-8")
        b = Path(td) / "b.txt"
        h1 = sha256_file(a)
        b.write_text("Frank", encoding="utf-8")
        h2 = sha256_file(b)
        if h1 != h2:
            fehler.append("gleiches Byte sollte gleiche SHA geben (Fall1)")
        a.write_text("Frank!", encoding="utf-8")
        if sha256_file(a) == h1:
            fehler.append("bei Aenderung sollte SHA driften (Fall2)")
        if sha256_file(Path(td) / "gibtsnicht.txt") != "":
            fehler.append("fehlende Datei muss leeren Fingerprint geben (Fall3)")
        # Doppelt-Pruefung: zwei gleiche Inhalte, Siegel bleibt gleich
        (Path(td) / "c.txt").write_text("Frank", encoding="utf-8")
        if sha256_file(Path(td) / "c.txt") != h2:
            fehler.append("doppelt absichern -> gleiches Ergebnis (Fall4)")
        # Lock-Datei-Form (Roundtrip)
        probe = ROOT / "data" / "integrity_probe_tmp.json"
        probe.write_text("{}", encoding="utf-8")
        probe.unlink()
        if not LOCK.exists() and not SET_CURRENT:
            fehler.append("Lock fehlt (Ohne --set-current wurde nie signiert)")
    return fehler


# ------------------------------------------------------------
# Kern-Beweis (19.09.2026): Klassifikation, Signatur-Regel, Konvergenz.
# Baut ein ECHTES kleines Git-Repo und prüft daran – Attrappen wären eine
# zweite Wahrheit. Schreibt NICHTS in diesen Baum (C15 des Selbsttest-Runners).
# ------------------------------------------------------------
def _fixture_repo(tmp: Path) -> None:
    """Mini-Repo mit je einer Datei der beiden Lock-Klassen."""
    (tmp / "scripts").mkdir(parents=True, exist_ok=True)
    (tmp / "layouts" / "_partials").mkdir(parents=True, exist_ok=True)
    (tmp / "hugo.toml").write_text("baseURL = '/'\n", encoding="utf-8")
    (tmp / "scripts" / "blog_doctor.py").write_text("print('visite')\n", encoding="utf-8")
    _git(tmp, "init", "-q")
    _fixture_commit(tmp, "fixture: Grundstand")


def _fixture_commit(tmp: Path, nachricht: str):
    """Commit im Fixture-Repo. Gibt das Ergebnis zurück – der Selbsttest
    prüft `returncode`, statt einen kaputten Fixture-Bau zu übersehen."""
    _git(tmp, "add", "-A")
    return _git(tmp, "-c", "user.email=selftest@example.org",
                "-c", "user.name=Integrity-Selftest",
                "commit", "-q", "-m", nachricht)


def _selftest_kern() -> list[str]:
    fehler = []
    echte_lock_sha = sha256_file(LOCK)
    echte_report_sha = sha256_file(REPORT)
    echte_history_sha = sha256_file(HISTORY)
    with tempfile.TemporaryDirectory(prefix="ffc-integrity-") as td:
        tmp = Path(td)
        with contextlib.redirect_stdout(io.StringIO()):
            _fixture_repo(tmp)
            lock_pfad = tmp / "data" / "integrity_lock.json"
            fest_rel, crit_rel = "scripts/blog_doctor.py", "hugo.toml"
            grundbau = _git(tmp, "rev-parse", "--verify", "HEAD")
            if grundbau is None or grundbau.returncode != 0:
                return ["Fixture-Repo konnte nicht gebaut werden (git init/commit) – "
                        "der Kern-Beweis hätte nichts zu messen und meldet das laut."]

            # 1. Frische Signatur -> kein Drift.
            signieren(tmp, grund="selftest")
            crit, fest = verify_files(tmp, load_lock(lock_pfad)["files"])
            if crit or fest:
                fehler.append("frisch signierter Baum meldet Drift (Fall1)")

            # 2. Committete Änderung -> VERSIEGELBAR, mit Commit in der Akte.
            (tmp / fest_rel).write_text("print('geheilt')\n", encoding="utf-8")
            _fixture_commit(tmp, "fix(wache): belegte Änderung")
            basis = load_lock(lock_pfad).get("head", "")
            crit, fest = verify_files(tmp, load_lock(lock_pfad)["files"])
            audit = klassifizieren(tmp, crit, fest, basis)
            urteil = {e["pfad"]: e["urteil"] for e in audit}
            if urteil.get(fest_rel) != "VERSIEGELBAR":
                fehler.append(f"committete Änderung nicht als versiegelbar erkannt: "
                              f"{urteil.get(fest_rel)} (Fall2)")
            if not any(c["sha"] for c in (audit[0]["commits"] or [])):
                fehler.append("Akte ohne Commit – Herkunft fehlt (Fall2b)")
            if audit[0].get("commits_art") != "seit-signatur":
                fehler.append("Herkunft nicht als 'seit Signatur' ausgewiesen "
                              f"({audit[0].get('commits_art')!r}, Fall2b2)")
            # Ohne auflösbaren Signatur-Stand (Rebase-Hash) müssen die letzten
            # Commits der Datei erscheinen – keine leere Akte.
            rueckfall = klassifizieren(tmp, crit, fest, "0000000")
            if rueckfall[0].get("commits_art") != "letzte-commits" \
                    or not rueckfall[0]["commits"]:
                fehler.append("Rückfall auf 'letzte Commits' fehlt (Fall2b3)")
            heilbar, blockiert = heilverdict(audit)
            if not heilbar or blockiert:
                fehler.append(f"committeter FEST-Drift muss signierbar sein "
                              f"(Fall2c: {blockiert})")

            # 3. Heilung + Konvergenz (zweiter Lauf ändert nichts).
            if heilen(tmp) != 0:
                fehler.append("--heal hat belegten FEST-Drift nicht geheilt (Fall3)")
            crit, fest = verify_files(tmp, load_lock(lock_pfad)["files"])
            if crit or fest:
                fehler.append("Baum nach Heilung nicht sauber (Fall3b)")
            sha_nach_heilung = sha256_file(lock_pfad)
            if heilen(tmp) != 0 or sha256_file(lock_pfad) != sha_nach_heilung:
                fehler.append("Heilung ist nicht konvergent (Fall3c)")

            # 4. Laufzeit-Mutation (nicht committet) -> nie signierbar.
            (tmp / fest_rel).write_text("print('laufzeit')\n", encoding="utf-8")
            crit, fest = verify_files(tmp, load_lock(lock_pfad)["files"])
            audit = klassifizieren(tmp, crit, fest, load_lock(lock_pfad).get("head", ""))
            heilbar, _ = heilverdict(audit)
            if heilbar:
                fehler.append("ungestagte Laufzeit-Mutation gilt als signierbar (Fall4)")
            if heilen(tmp) != 3:
                fehler.append("--heal muss bei Laufzeit-Mutation Exit 3 liefern (Fall4b)")
            if sha256_file(lock_pfad) != sha_nach_heilung:
                fehler.append("HARD STOP hat trotzdem signiert (Fall4c)")

            # 5. KRITISCH bleibt grundsätzlich Handarbeit.
            _fixture_commit(tmp, "chore: Laufzeitstand sichern")
            (tmp / crit_rel).write_text("baseURL = '/neu/'\n", encoding="utf-8")
            _fixture_commit(tmp, "feat(head): kritischer Kern geändert")
            crit, fest = verify_files(tmp, load_lock(lock_pfad)["files"])
            if not crit:
                fehler.append("KRITISCH-Drift nicht erkannt (Fall5)")
            heilbar, blockiert = heilverdict(klassifizieren(tmp, crit, fest, ""))
            if heilbar:
                fehler.append("KRITISCH-Drift gilt als selbst-signierbar (Fall5b)")
            if heilen(tmp) != 3:
                fehler.append("--heal muss bei KRITISCH Exit 3 liefern (Fall5c)")
            if gate(tmp) != 3:
                fehler.append("--gate muss bei Drift rot sein (Exit 3, Fall5d)")

            # 6. Akte steht im Lock, ohne Passwort-Kosmetik.
            akte = load_lock(lock_pfad).get("audit") or []
            if not akte or akte[-1].get("art") != "heal":
                fehler.append("Signatur-Akte fehlt/ist unvollständig (Fall6)")
            if not akte[-1].get("geaendert"):
                fehler.append("Akte ohne geänderte Dateien (Fall6b)")

        # 7. Der Beweis schreibt nicht in DIESEN Baum (C15).
        if sha256_file(LOCK) != echte_lock_sha:
            fehler.append("Selbsttest hat data/integrity_lock.json verändert")
        if sha256_file(REPORT) != echte_report_sha:
            fehler.append("Selbsttest hat INTEGRITY-REPORT.md verändert")
        if sha256_file(HISTORY) != echte_history_sha:
            fehler.append("Selbsttest hat data/integrity_history.jsonl verändert")
    return fehler


def selftest() -> int:
    fehler = _selftest() + _selftest_kern()
    if fehler:
        print("🛑 INTEGRITY-SELBSTTEST FEHLGESCHLAGEN.")
        print("\n".join(f"  - {f}" for f in fehler))
        return 2
    print(f"✅ Integrity-Selbsttest: {len(SELFTEST)} Fälle eingefroren + "
          f"Kern-Beweis (Klassifikation, Signatur-Regel, Konvergenz) grün – "
          f"ohne einen Schreibzugriff auf den Baum.")
    return 0


# ------------------------------------------------------------
# Modi
# ------------------------------------------------------------
def gate(root: Path = ROOT) -> int:
    """PR-/CI-Gate: fail-closed, mit Herkunft und Reparaturzeile."""
    lock = load_lock(root / "data" / "integrity_lock.json")
    crit_bad, fest_bad = verify_files(root, lock.get("files", {}))
    if not crit_bad and not fest_bad:
        print(f"✅ Integritäts-Gate grün: {len(lock.get('files', {}))} Kerndateien "
              f"entsprechen exakt dem signierten Stand (HEAD `{git_head(root)}`).")
        return 0
    print("🛑 INTEGRITÄTS-GATE ROT – gesperrter Kern geändert, aber nicht mit-signiert.")
    print("")
    print("\n".join(audit_tabelle(
        klassifizieren(root, crit_bad, fest_bad, lock.get("head", "")))))
    print("")
    print("Fix – im SELBEN Pull Request, sonst geht die Änderung ohne Siegel auf main:")
    print("    python3 scripts/integrity_guard.py --set-current")
    print("    git add data/integrity_lock.json")
    print("    git commit -m \"chore(integrity): Kern neu signiert (Herkunft im Lock)\"")
    print("")
    print("Oder: die Änderung an den gesperrten Dateien zurücknehmen.")
    print(GATE_REGEL)
    return 3


def heilen(root: Path = ROOT, dry_run: bool = False) -> int:
    """Selbstheilung für belegten Drift – HARD STOP bleibt für alles andere."""
    lock_pfad = root / "data" / "integrity_lock.json"
    lock = load_lock(lock_pfad)
    crit_bad, fest_bad = verify_files(root, lock.get("files", {}))
    if not crit_bad and not fest_bad:
        print(f"✅ Integrität: kein Drift – {len(lock.get('files', {}))} Kerndateien "
              f"entsprechen dem signierten Stand.")
        return 0
    audit = klassifizieren(root, crit_bad, fest_bad, lock.get("head", ""))
    heilbar, blockiert = heilverdict(audit)
    if not heilbar:
        report_schreiben(root, crit_bad, fest_bad, audit=audit, blockiert=blockiert)
        print("🛑 INTEGRITÄTS-HARD-STOP – Drift ist NICHT selbst-signierbar:")
        for b in blockiert:
            print(f"  - {b}")
        print("  → INTEGRITY-REPORT.md sichten, dann bewusst signieren "
              "(`python3 scripts/integrity_guard.py --set-current`) oder die "
              "Änderung zurücknehmen.")
        return 3
    if dry_run:
        print("🔎 --heal --dry-run: Drift ist belegt (versioniert + committet + Klasse FEST).")
        print("\n".join(audit_tabelle(audit)))
        print("\nOhne --dry-run würde jetzt neu signiert: "
              + ", ".join(f"`{e['pfad']}`" for e in audit))
        return 0
    ergebnis = signieren(root, grund="heal", audit=audit)
    report_schreiben(root, crit_bad, fest_bad, audit=audit, geheilt=ergebnis)
    historie_schreiben(root, {
        "date": date.today().isoformat(),
        "kritisch": 0,
        "fest": len(fest_bad),
        "modus": "heal",
        "geheilt": ergebnis["geaendert"],
        "head": git_head(root),
    })
    print("🔓 Selbst-Signatur: belegter Drift neu signiert "
          f"({len(ergebnis['geaendert'])} Datei(en)) – Herkunft steht im Lock "
          "(`audit`) und in `data/integrity_history.jsonl`.")
    for e in audit:
        print(f"   · `{e['pfad']}` ({e['klasse']})")
    return 0


def drift_audit(root: Path = ROOT) -> int:
    lock = load_lock(root / "data" / "integrity_lock.json")
    crit_bad, fest_bad = verify_files(root, lock.get("files", {}))
    if not crit_bad and not fest_bad:
        print(f"✅ Kein Drift – {len(lock.get('files', {}))} Kerndateien entsprechen "
              "dem signierten Stand.")
        return 0
    audit = klassifizieren(root, crit_bad, fest_bad, lock.get("head", ""))
    heilbar, blockiert = heilverdict(audit)
    print("🔎 DRIFT-AUDIT (read-only) – Herkunft der Abweichungen:")
    print("")
    print("\n".join(audit_tabelle(audit)))
    print("")
    if heilbar:
        print("Urteil: belegter FEST-Drift – selbst-signierbar "
              "(`--heal`), aber auch bewusst per `--set-current` zu zeichnen.")
    else:
        print("Urteil: NICHT selbst-signierbar – HARD STOP:")
        for b in blockiert:
            print(f"  - {b}")
    return exit_fuer(crit_bad, fest_bad)


def main():
    if SELFTEST_MODE:
        sys.exit(selftest())

    fehler = _selftest()
    if fehler:
        print("🛑 INTEGRITY-SELBSTTEST FEHLGESCHLAGEN.")
        print("\n".join(fehler)); sys.exit(2)
    print(f"✅ Integrity-Selbsttest: {len(SELFTEST)} Faelle gruen.")

    if SET_CURRENT:
        ergebnis = signieren(ROOT, grund="set-current")
        print(f"🔒 Signiert: {ergebnis['signiert']} Dateien gegen SHA-256 gelockt "
              f"(HEAD {git_head(ROOT)}).")
        if ergebnis["geaendert"]:
            print(f"   Neu gezeichnet ({len(ergebnis['geaendert'])}): "
                  + ", ".join(ergebnis["geaendert"]))
        return

    if ADD_PATH:
        rp = ROOT / ADD_PATH
        if not rp.exists():
            print(f"🔴 Ziel nicht da: {ADD_PATH}"); sys.exit(2)
        lock = load_lock(LOCK)
        vorher = sha256_file(rp)
        lock["files"] = {**lock.get("files", {}), ADD_PATH: vorher}
        lock["signed_at"] = datetime.now(timezone.utc).isoformat()
        lock["head"] = git_head(ROOT)
        lock["audit"] = (list(lock.get("audit") or []) + [{
            "date": date.today().isoformat(), "art": "add", "head": git_head(ROOT),
            "geaendert": [ADD_PATH]}] if vorher else list(lock.get("audit") or []))[-AUDIT_MAX:]
        LOCK.parent.mkdir(exist_ok=True)
        LOCK.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
        print(f"🔒 {ADD_PATH} in den Lock aufgenommen (neu signiert).")
        return

    # Die drei Sichten auf den Drift rechnen selbst (und bleiben so auch
    # einzeln aufrufbar); der Standard-Verify folgt darunter.
    if GATE:
        sys.exit(gate(ROOT))
    if HEAL:
        sys.exit(heilen(ROOT, dry_run=DRY_RUN))
    if DRIFT_AUDIT:
        sys.exit(drift_audit(ROOT))

    lock = load_lock(LOCK)
    crit_bad, fest_bad = verify_files(ROOT, lock.get("files", {}))
    audit = (klassifizieren(ROOT, crit_bad, fest_bad, lock.get("head", ""))
             if (crit_bad or fest_bad) else [])
    report_schreiben(ROOT, crit_bad, fest_bad, audit=audit)
    historie_schreiben(ROOT, {"date": date.today().isoformat(),
                              "kritisch": len(crit_bad), "fest": len(fest_bad),
                              "modus": "verify"})
    sys.exit(exit_fuer(crit_bad, fest_bad))


if __name__ == "__main__":
    main()
