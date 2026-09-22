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
# ------------------------------------------------------------
#  22.09.2026 – nicht der Kern war kaputt, sondern das SIEGEL
#  (Content-Engine v2 rot, Issue #346)
# ------------------------------------------------------------
#  Am 21.09.2026, 19:23 UTC starb die Content-Engine erneut im ersten
#  Schritt. Diesmal war aber KEINE Kerndatei verändert: Der Lock selbst war
#  zerstört – und zwar als *Merge-Artefakt*. Commit d364e039 (Merge von
#  `main` in einen Arena-Zweig) hat zwei Lock-Fassungen zusammengeschnitten,
#  statt eine zu wählen: Das Ergebnis (7.185 Bytes) bricht bei Byte 7.171 ab
#  (`"art": "set-current",` mitten im jüngsten Akteneintrag) und hängt daran
#  den Rest einer ANDEREN Fassung. Beide Mergeseiten waren für sich gültig
#  (7.983 / 7.339 Bytes).
#
#  Damit griff die ganze Kette falsch:
#    · `load_lock()` verschluckte den Syntaxfehler zu „0 Dateien gelockt".
#    · Der Guard meldete deshalb das SYMPTOM („6 kritische Knoten neu ohne
#      Signatur") und nicht die URSACHE („Siegel bei Byte 7.171 zerstört").
#    · `--heal` lehnt in diesem Zustand alles ab – es gab keinen Weg zurück.
#    · Der Alarm riet dem Menschen zu API-Keys statt zum Siegel.
#    · Produktion stand, obwohl der Kern nachweislich unversehrt war: alle
#      43 signierten Dateien stimmten Byte für Byte mit der letzten gültigen
#      Signatur (da493edf) überein.
#
#  Diese Fassung macht das Siegel erstmals selbst prüfbar (Zustand, Kette,
#  Rückleseprobe) und reparierbar:
#    · SCHREIBEN ist atomar (Temp-Datei + Rename + fsync) und wird
#      ZURÜCKGELESEN. Ein abgebrochener Lauf kann kein halbes Siegel mehr
#      hinterlassen; die vorige Fassung bleibt bei jedem Zweifel stehen.
#    · Der Lock trägt jetzt `schema`, `files_sha256` (Prüfsumme der
#      Datei-Map) und eine HASH-KETTE über die ganze Akte (`prev_sha256`).
#      Ein Zusammenschnitt zweier Fassungen – auch wenn er syntaktisch
#      gültig ist – bricht die Kette und wird als CHIMÄRE erkannt.
#    · `--repair-lock` heilt ein beschädigtes Siegel BELEGT: aus dem
#      committeten Stand, sonst aus der jüngsten gültigen Fassung der
#      lokalen Historie, sonst durch BERGEN der noch lesbaren Teile des
#      Artefakts – und nur, wenn die geborgene Datei-Map den Baum exakt und
#      vollständig deckt. Sonst bleibt es HARD STOP (Mensch entscheidet).
#      Der Vorgang landet mit Quelle, Bruchstelle und Bytes in der Akte.
#    · `--heal` fährt diesen Weg automatisch, wenn das Siegel beschädigt
#      ist – die Engine heilt also künftig ihr Siegel, statt daran zu
#      sterben. Hat der Baum daneben echten Drift, gelten unverändert die
#      harten Regeln (KRITISCH/Laufzeit-Mutation = Mensch).
#
#  Gegen die Ursache selbst (ein Maschinen-Artefakt wurde wie Quelltext
#  gemergt) steht in `.gitattributes` jetzt `merge=binary` für den Lock:
#  Git versucht dann keinen Text-Zusammenschnitt mehr, sondern meldet einen
#  sichtbaren Konflikt, der bewusst aufgelöst werden muss.
#
#  Aufruf:
#    python3 scripts/integrity_guard.py                  # verify (Exit 0/1/3)
#    python3 scripts/integrity_guard.py --drift-audit    # Herkunft (read-only)
#    python3 scripts/integrity_guard.py --gate           # CI/PR-Gate (fail-closed)
#    python3 scripts/integrity_guard.py --heal           # belegten Drift signieren
#    python3 scripts/integrity_guard.py --heal --dry-run # nur zeigen, nichts tun
#    python3 scripts/integrity_guard.py --repair-lock    # beschädigtes Siegel belegt heilen
#    python3 scripts/integrity_guard.py --repair-lock --dry-run
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
import os
import re
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
REPAIR_LOCK = "--repair-lock" in sys.argv
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

# Siegel-Format (22.09.2026, Issue #346): `schema` macht die Fassung
# erkennbar, `files_sha256` prüft die Datei-Map gegen sich selbst, und
# `prev_sha256` verkettet die Akte. Ein Lock ohne diese Felder ist eine
# Fassung von vor dem 22.09.2026 (`ok-legacy`): gültig, aber schwächer
# belegt – jede neue Signatur hebt ihn automatisch auf `schema` 2.
SCHEMA = 2
SCHEMA_FELD = "schema"
KETTE_FELD = "prev_sha256"
MAP_FELD = "files_sha256"
START_FELD = "audit_start_sha256"   # Anker des ältesten erhaltenen Eintrags

# Zustände des Siegels SELBST. Sie stehen VOR jeder Drift-Aussage: Ein
# kaputtes Siegel kann keine Kerndatei freisprechen und keine anklagen –
# ohne diese Unterscheidung meldete der Guard am 21.09.2026 sechs
# „neu ohne Signatur"-Knoten, während in Wahrheit nur die Akte zerbrochen war.
ZUSTAND_FEHLT = "fehlt"
ZUSTAND_FREMD = "fremdformat"
ZUSTAND_BESCHAEDIGT = "beschaedigt"
ZUSTAND_CHIMAERE = "chimäre"
ZUSTAND_LEGACY = "ok-legacy"
ZUSTAND_OK = "ok"

ZUSTAND_KLARTEXT = {
    ZUSTAND_FEHLT: "kein Siegel vorhanden (nie signiert)",
    ZUSTAND_FREMD: "Datei vorhanden, aber kein Siegel (fremdes Format)",
    ZUSTAND_BESCHAEDIGT: "Siegel ZERSTÖRT (kein gültiges JSON)",
    ZUSTAND_CHIMAERE: "Siegel GEFÄLSCHT/ZUSAMMENGESETZT (Kette oder Map bricht)",
    ZUSTAND_LEGACY: "Siegel gültig (Fassung vor dem 22.09.2026, ohne Kette)",
    ZUSTAND_OK: "Siegel gültig und verkettet",
}
GESUND = (ZUSTAND_OK, ZUSTAND_LEGACY)


def _kanonisch(obj) -> str:
    """Stabile Schreibweise für Prüfsummen (Reihenfolge/Abstände egal)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def _eintrag_sha(eintrag: dict) -> str:
    """Prüfsumme eines Akteneintrags – OHNE sein eigenes Kettenglied.

    `prev_sha256` zeigt auf den Vorgänger und darf darum nicht in die eigene
    Prüfsumme eingehen; alles andere (Datum, Art, Head, Änderungen, Herkunft)
    ist gedeckt.
    """
    kern = {k: v for k, v in eintrag.items() if k != KETTE_FELD}
    return hashlib.sha256(_kanonisch(kern).encode("utf-8")).hexdigest()


def files_sha(files: dict) -> str:
    """Prüfsumme der Datei-Map – die Generation, an der die Akte hängt."""
    return hashlib.sha256(_kanonisch(files).encode("utf-8")).hexdigest()


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


def _siegel_ende_offen(text: str) -> bool:
    """Endet der Text MITTEN in einer Struktur? (Beweis für einen Abbruch.)

    Gezählt werden Klammern außerhalb von Zeichenketten. Endet die Datei
    offen – oder mitten in einer Zeichenkette –, hat ein Schreiber nicht zu
    Ende geschrieben. Endet sie GESCHLOSSEN, aber unlesbar, wurden zwei
    Stände zusammengesetzt: Ein einzelner Schreiber erzeugt sonst gültiges
    JSON.
    """
    tiefe, im_string, escape = 0, False, False
    for z in text:
        if im_string:
            if escape:
                escape = False
            elif z == "\\":
                escape = True
            elif z == '"':
                im_string = False
            continue
        if z == '"':
            im_string = True
        elif z in "{[":
            tiefe += 1
        elif z in "}]":
            tiefe -= 1
    return im_string or tiefe > 0


def _bruch_verdacht(text: str, pos: int) -> str:
    """Sieht die Bruchstelle nach Zusammenschnitt aus – oder nach Abbruch?

    Der Unterschied ist die Reparatur: Ein Abbruch endet OFFEN (mitten in
    Klammern oder Zeichenkette), ein Zusammenschnitt endet geschlossen und
    trägt hinter der Bruchstelle den Rest einer anderen Fassung. Am
    21.09.2026 war es ein Zusammenschnitt (`...art": "set-current",` plus
    Rest `]}`-Ende eines 7.339-Byte-Stands).
    """
    if re.search(r"^(<<<<<<<|=======|>>>>>>>)", text, re.MULTILINE):
        return "konfliktmarker"
    if pos < 0:
        return "unbekannt"
    return "abbruch" if _siegel_ende_offen(text) else "zusammenschnitt"


def _kette_pruefen(daten: dict, files: dict) -> list:
    """Fehler der Ketten-/Map-Prüfung des Siegels (leer = gesund).

    Geprüft wird, was sich ohne Annahmen prüfen lässt:
      · Map-Prüfsumme == aktuelle Datei-Map,
      · der jüngste Akteneintrag hängt an DIESER Map (Generation),
      · jeder Kettenglied-Verweis trifft die Prüfsumme seines Vorgängers.
    Ein syntaktisch gültiges, aber aus zwei Ständen zusammengesetztes Siegel
    fällt hier durch – genau der Fall, den ein Merge erzeugt.
    """
    fehler = []
    if SCHEMA_FELD in daten:
        try:
            fassung = int(daten[SCHEMA_FELD])
        except (TypeError, ValueError):
            return [f"`{SCHEMA_FELD}` ist keine Zahl: {daten[SCHEMA_FELD]!r}"]
        if fassung > SCHEMA:
            return [f"Fassung {fassung} ist diesem Guard unbekannt (hier gilt "
                    f"{SCHEMA}) – fail-closed statt Raten"]
    akte = daten.get("audit") or []
    map_hash = files_sha(files)
    if MAP_FELD in daten and daten[MAP_FELD] != map_hash:
        fehler.append(f"`{MAP_FELD}` passt nicht zur Datei-Map "
                      f"({str(daten[MAP_FELD])[:12]}… ≠ {map_hash[:12]}…)")
    anker_da = (MAP_FELD in daten or START_FELD in daten
                or any(MAP_FELD in e for e in akte if isinstance(e, dict)))
    if anker_da and not akte:
        fehler.append("Kette angekündigt, aber keine Akte vorhanden")
    if akte and START_FELD in daten and daten[START_FELD] != _eintrag_sha(akte[0]):
        # Auch der ÄLTESTE erhaltene Eintrag ist verankert: Sonst könnte ein
        # Zusammenschnitt genau dort ungestraft Inhalte austauschen.
        fehler.append("ältester Akteneintrag passt nicht zu seinem Anker "
                      f"`{START_FELD}`")
    if akte:
        juengster = akte[-1]
        if anker_da and MAP_FELD not in juengster:
            fehler.append("jüngster Akteneintrag nennt die Datei-Map nicht "
                          "(Generation nicht belegt)")
        elif MAP_FELD in juengster and juengster[MAP_FELD] != map_hash:
            fehler.append("jüngster Akteneintrag hängt an einer ANDEREN "
                          "Datei-Map als der Lock (Zusammenschnitt)")
    for i in range(len(akte) - 1, 0, -1):
        eintrag = akte[i] if isinstance(akte[i], dict) else {}
        vor = eintrag.get(KETTE_FELD)
        if vor is None:
            break          # Kette beginnt hier (Legacy/Kappung) – zulässig
        if vor != _eintrag_sha(akte[i - 1]):
            fehler.append(f"Akteneintrag {i} verweist nicht auf seinen "
                          f"Vorgänger (Kette gebrochen)")
            break
    return fehler


def _zustand_aus_bytes(roh: bytes) -> tuple:
    """(Daten|None, Zustand) – die Wahrheit über das Siegel, aus Bytes."""
    gross = len(roh)
    try:
        text = roh.decode("utf-8")
    except UnicodeDecodeError as exc:
        return None, {"zustand": ZUSTAND_BESCHAEDIGT, "groesse": gross,
                      "offset": exc.start, "verdacht": "unbekannt",
                      "detail": [f"kein UTF-8 (Byte {exc.start}): {exc}"]}
    try:
        daten = json.loads(text)
    except ValueError as exc:
        pos = getattr(exc, "pos", -1)
        verdacht = _bruch_verdacht(text, pos)
        detail = [f"JSON nicht lesbar: {exc}",
                  f"Bruchstelle: Byte {pos} von {gross} "
                  f"(Zeile {getattr(exc, 'lineno', '?')})"]
        if verdacht == "konfliktmarker":
            detail.append("Git-Merge-Konfliktmarker (<<<<<<< / ======= / >>>>>>>) im Siegel gefunden.")
        elif verdacht == "zusammenschnitt":
            detail.append("Hinter der Bruchstelle steht der Rest einer ANDEREN "
                          "Fassung – Muster: zwei Stände wurden zusammen"
                          "gesetzt (Merge-Konflikt in einer Maschinendatei).")
        elif verdacht == "abbruch":
            detail.append("Die Datei endet AN der Bruchstelle – Muster: ein "
                          "Schreibvorgang wurde abgebrochen (halbes Siegel).")
        return None, {"zustand": ZUSTAND_BESCHAEDIGT, "groesse": gross,
                      "offset": pos, "verdacht": verdacht, "detail": detail}
    if not isinstance(daten, dict):
        return None, {"zustand": ZUSTAND_FREMD, "groesse": gross, "offset": None,
                      "verdacht": "unbekannt",
                      "detail": [f"JSON ist kein Objekt, sondern "
                                 f"{type(daten).__name__}"]}
    files = daten.get("files")
    if not isinstance(files, dict) or not files:
        return daten, {"zustand": ZUSTAND_FREMD, "groesse": gross, "offset": None,
                       "verdacht": "unbekannt",
                       "detail": ["keine `files`-Map (leer oder falsch typisiert)"
                                  " – das ist kein Siegel"]}
    kaputt = [p for p, h in files.items()
              if not isinstance(h, str) or len(h) != 64]
    if kaputt:
        return daten, {"zustand": ZUSTAND_FREMD, "groesse": gross, "offset": None,
                       "verdacht": "unbekannt",
                       "detail": [f"{len(kaputt)} Eintrag/Einträge ohne "
                                  f"SHA-256-Fingerprint"]}
    akte = daten.get("audit")
    if akte is not None and not isinstance(akte, list):
        return daten, {"zustand": ZUSTAND_FREMD, "groesse": gross, "offset": None,
                       "verdacht": "unbekannt",
                       "detail": ["`audit` ist keine Liste"]}
    daten.setdefault("audit", [])
    fehler = _kette_pruefen(daten, files)
    juengster = (daten.get("audit") or [{}])[-1]
    verankert = MAP_FELD in daten or MAP_FELD in juengster
    zustand = ZUSTAND_OK if (verankert and not fehler) else ZUSTAND_LEGACY
    if fehler:
        zustand = ZUSTAND_CHIMAERE
    return daten, {"zustand": zustand, "groesse": gross, "offset": None,
                   "verdacht": "unbekannt" if not fehler else "zusammenschnitt",
                   "detail": fehler or ["Kette, Map-Prüfsumme und Generation "
                                        "sind in Ordnung"]}


def lock_zustand(lock_pfad: Path = None) -> dict:
    """Zustand des Siegels selbst – die ERSTE Frage jeder Prüfung.

    Ohne sie meldete der Guard am 21.09.2026 das Symptom (sechs „neu ohne
    Signatur") statt der Ursache (Siegel bei Byte 7.171 zerstört).
    """
    pfad = lock_pfad or LOCK
    if not pfad.exists():
        return {"zustand": ZUSTAND_FEHLT, "groesse": 0, "offset": None,
                "verdacht": "unbekannt", "datei": str(pfad),
                "detail": ["kein `data/integrity_lock.json` vorhanden"]}
    try:
        roh = pfad.read_bytes()
    except OSError as exc:
        return {"zustand": ZUSTAND_BESCHAEDIGT, "groesse": 0, "offset": None,
                "verdacht": "unbekannt", "datei": str(pfad),
                "detail": [f"nicht lesbar: {exc}"]}
    _, befund = _zustand_aus_bytes(roh)
    befund["datei"] = str(pfad)
    return befund


def lock_zustand_text(befund: dict, praefix: str = "- ") -> list:
    """Der Siegel-Zustand als Report-Zeilen (Diagnose, nie nur ein Kreuz)."""
    return [f"{praefix}**{ZUSTAND_KLARTEXT.get(befund['zustand'], befund['zustand'])}** "
            f"· {befund.get('groesse', 0)} Bytes"
            f"{' · Bruchstelle Byte ' + str(befund['offset']) if befund.get('offset', -1) not in (None, -1) else ''}"
            f" · Verdacht: {befund.get('verdacht', 'unbekannt')}"] + \
        [f"{praefix}{d}" for d in befund.get("detail", [])]


def load_lock(lock_pfad: Path = None) -> dict:
    pfad = lock_pfad or LOCK
    if not pfad.exists():
        return {"signed_at": "nie", "head": "", "files": {}}
    try:
        daten, befund = _zustand_aus_bytes(pfad.read_bytes())
    except OSError:
        daten, befund = None, {"zustand": ZUSTAND_BESCHAEDIGT, "detail":
                               ["nicht lesbar"], "verdacht": "unbekannt"}
    if daten is None:
        # Ein kaputtes Siegel ist KEIN leeres Siegel: die Diagnose reist mit,
        # damit kein Aufrufer „0 Dateien gelockt" für eine Tatsache hält.
        return {"signed_at": "beschaedigt", "head": "", "files": {},
                "_zustand": befund}
    daten.setdefault("files", {})
    daten["_zustand"] = befund
    return daten


# ------------------------------------------------------------
# SCHREIBEN: atomar, verkettet, rückgelesen (22.09.2026, Issue #346)
# ------------------------------------------------------------
class LockSchreibfehler(RuntimeError):
    """Das Siegel konnte nicht sicher geschrieben werden – alter Stand bleibt.

    Der Aufrufer MUSS daraus einen lauten, roten Abbruch machen: Eine
    Signatur, die nicht auf der Platte steht, ist keine.
    """


def _verzeichnis_syncen(pfad: Path) -> None:
    """Den Rename-Eintrag selbst auf die Platte bringen (best effort)."""
    try:
        fd = os.open(str(pfad), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _atomar_schreiben(pfad: Path, inhalt: str) -> None:
    """Neben die Zieldatei schreiben und umbenennen – nie hineinschreiben.

    `Path.write_text()` kürzt die Zieldatei zuerst. Wird der Lauf genau dann
    abgebrochen (Timeout, Kill, Runner-Recycling), bleibt ein halbes Siegel
    liegen – genau die Klasse, die hier niemand mehr sehen soll. Rename ist
    atomar: Es gibt entweder die alte oder die neue Fassung, nie etwas dazwischen.
    """
    rohdaten = inhalt.encode("utf-8")
    tmp = pfad.with_name(pfad.name + ".tmp")
    tmp.unlink(missing_ok=True)      # Rest eines früheren Abbruchs (Kill) zuerst weg
    try:
        with open(tmp, "wb") as fh:
            fh.write(rohdaten)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, pfad)
        _verzeichnis_syncen(pfad.parent)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)   # kein Rest, auch nicht nach Absturz


def _lock_text(daten: dict) -> str:
    return json.dumps(daten, indent=2, ensure_ascii=False) + "\n"


def lock_schreiben(root: Path, daten: dict) -> tuple:
    """Schreibt das Siegel und liest es ZURÜCK: (ok, Meldung).

    Drei Sicherungen vor dem Commit eines Siegels: (1) der Text muss sich
    wieder als gesundes Siegel lesen lassen, (2) geschrieben wird atomar,
    (3) danach wird die PLATTE gelesen und gegen den Soll-Stand geprüft.
    Scheitert etwas, wird die vorige Fassung wiederhergestellt – der Aufrufer
    bekommt `False` und macht daraus einen roten Lauf.
    """
    pfad = root / "data" / "integrity_lock.json"
    alt = pfad.read_bytes() if pfad.exists() else None
    soll_map = daten.get("files") or {}
    pfad.parent.mkdir(parents=True, exist_ok=True)
    text = _lock_text(daten)
    _, probe = _zustand_aus_bytes(text.encode("utf-8"))
    if probe["zustand"] != ZUSTAND_OK:
        return False, (f"Signatur verworfen: der erzeugte Lock wäre selbst "
                       f"nicht gesund ({ZUSTAND_KLARTEXT.get(probe['zustand'])}"
                       f": {'; '.join(probe['detail'])})")
    try:
        _atomar_schreiben(pfad, text)
    except OSError as exc:
        return False, f"Schreiben fehlgeschlagen (alter Stand bleibt): {exc}"
    zurueck, befund = _zustand_aus_bytes(pfad.read_bytes())
    if befund["zustand"] != ZUSTAND_OK:
        if alt is not None:
            _atomar_schreiben(pfad, alt.decode("utf-8"))
        return False, (f"Rück-Leseprobe fehlgeschlagen "
                       f"({ZUSTAND_KLARTEXT.get(befund['zustand'])}): "
                       f"{'; '.join(befund['detail'])} – vorige Fassung "
                       f"wiederhergestellt")
    if (zurueck or {}).get("files") != soll_map:
        if alt is not None:
            _atomar_schreiben(pfad, alt.decode("utf-8"))
        return False, ("Rück-Leseprobe: Datei-Map auf der Platte weicht vom "
                       "Soll-Stand ab – vorige Fassung wiederhergestellt")
    return True, f"{len(soll_map)} Dateien, Fassung {SCHEMA}, Kette + Map-Prüfsumme"


def _lock_dokument(root: Path, files: dict, akte: list, neuer: dict) -> dict:
    """Siegel-Dokument bauen: neuer Eintrag + Kette über die ganze Akte.

    Die Kette wird bei JEDER Signatur für alle erhaltenen Einträge neu
    gezogen (nur Metadaten, keine Inhalte). Damit ist die Akte als Ganzes
    prüfbar – ein Zusammenschnitt zweier Fassungen kann sich nicht mehr
    hinter „historischen" Einträgen verstecken.
    """
    eintraege = list(akte) + [dict(neuer)]
    eintraege = eintraege[-AUDIT_MAX:]
    karte = files_sha(files)
    kette, vorgaenger = [], None
    for e in eintraege:
        k = {kk: vv for kk, vv in e.items() if kk != KETTE_FELD}
        k[KETTE_FELD] = vorgaenger
        if e is eintraege[-1] or MAP_FELD in e:
            k[MAP_FELD] = k.get(MAP_FELD) or karte
        vorgaenger = _eintrag_sha(k)
        kette.append(k)
    return {
        SCHEMA_FELD: SCHEMA,
        "signed_at": datetime.now(timezone.utc).isoformat(),
        "head": git_head(root),
        "files": files,
        MAP_FELD: karte,
        # Der Anker bindet den ältesten erhaltenen Eintrag an das Dokument –
        # die Kette deckt damit die GANZE Akte, nicht nur ihren Schwanz.
        START_FELD: _eintrag_sha(kette[0]) if kette else None,
        "audit": kette,
    }


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
    """Schreibt den Lock über den Ist-Stand – und die Herkunft dazu.

    Seit dem 22.09.2026 mit drei Sicherungen: Der Eintrag wird verkettet
    (Kette über die ganze Akte), die Datei-Map bekommt eine eigene Prüfsumme,
    und geschrieben wird atomar mit Rück-Leseprobe (`lock_schreiben`). Ein
    abgebrochener Lauf kann damit kein halbes Siegel mehr hinterlassen.
    """
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
    dokument = _lock_dokument(root, files, list(alt.get("audit") or []), akte)
    ok, meldung = lock_schreiben(root, dokument)
    if not ok:
        # Laut scheitern statt still „signiert" melden: Eine Unterschrift, die
        # nicht auf der Platte steht, ist keine (und der Baum ist unverändert).
        raise LockSchreibfehler(meldung)
    return {"signiert": len(files), "geaendert": geaendert, "akte": akte,
            "kontrolle": meldung}


# ------------------------------------------------------------
# REPARATUR DES SIEGELS (22.09.2026, Issue #346)
# ------------------------------------------------------------
SIEGEL_REL = "data/integrity_lock.json"


def melde(text: str, art: str = "warning") -> None:
    """CI-Annotation in Actions, lesbarer Satz überall sonst (Hausmuster)."""
    print(f"::{art}::{text}" if os.environ.get("GITHUB_ACTIONS") else f"⚠️  {text}")


def _lock_revisionen(root: Path) -> list:
    """Committete Fassungen des Siegels, jüngste zuerst.

    In einem flachen CI-Klon (fetch-depth 1) ist die Liste leer oder enthält
    nur HEAD – dann trägt die Bergung (unten) den Nachweis, nicht das Raten.
    """
    r = _git(root, "log", "--format=%H", "--", SIEGEL_REL)
    if r is None or r.returncode != 0:
        return []
    return [z.strip() for z in r.stdout.splitlines() if z.strip()]


def lock_bergen(text: str) -> dict:
    """Bergen, was im beschädigten Artefakt BELEGBAR ist.

    Ein Zusammenschnitt ist vorne vollständig: die `files`-Map und alle
    Akteneinträge VOR der Bruchstelle. Geborgen wird ausschließlich, was
    vollständig dasteht – nichts wird ergänzt, nichts geraten. Ob die
    geborgene Map den Baum wirklich deckt, entscheidet danach die Prüfung
    gegen den Baum (jede Datei, kompletter Satz); sonst gibt es keine Bergung.
    """
    dec = json.JSONDecoder()

    def _wert(schluessel: str):
        i = text.find(f'"{schluessel}"')
        if i < 0:
            return None
        j = text.find(":", i)
        if j < 0:
            return None
        k = j + 1
        while k < len(text) and text[k] in " \t\r\n":
            k += 1
        if k >= len(text) or text[k] not in "[{":
            return None
        try:
            return dec.raw_decode(text, k)[0]
        except ValueError:      # Wert selbst liegt hinter der Bruchstelle
            return None

    def _akte() -> list:
        i = text.find('"audit"')
        j = text.find("[", i) if i >= 0 else -1
        if j < 0:
            return []
        pos, out = j + 1, []
        while True:
            while pos < len(text) and text[pos] in " \t\r\n,":
                pos += 1
            if pos >= len(text) or text[pos] == "]":
                break
            try:
                obj, pos = dec.raw_decode(text, pos)
            except ValueError:
                break           # ab hier ist nichts mehr Beweis
            if isinstance(obj, dict):
                out.append(obj)
        return out

    files = _wert("files")
    if not isinstance(files, dict) or not files:
        return {}
    akte = [e for e in _akte()
            if isinstance(e.get("geaendert", []), list) and "art" in e]
    return {"files": files, "audit": akte}


def _reparatur_quelle(root: Path, befund: dict) -> tuple:
    """(Quelle|{}, Protokoll) – die belegte Quelle für ein neues Siegel.

    Beweiskraft, nicht Bequemlichkeit: Zuerst der committete Stand (deckt
    eine Laufzeit-Mutation des Locks ab), dann die jüngste gültige Fassung
    der lokalen Historie, zuletzt die Bergung aus dem beschädigten Artefakt.
    Jede Abweisung wird protokolliert – ein abgelehnter Weg ist ein Befund,
    kein Schweigen.
    """
    protokoll = []

    def _aus_bytes(roh: bytes, art: str, extra: dict):
        daten, zustand = _zustand_aus_bytes(roh)
        if daten is None or zustand["zustand"] not in GESUND:
            protokoll.append(f"{art}: verworfen "
                             f"({ZUSTAND_KLARTEXT.get(zustand['zustand'])})")
            return {}
        qu = {"art": art, "files": daten.get("files") or {},
              "audit": list(daten.get("audit") or []), "zustand": zustand}
        qu.update(extra)
        return qu

    r = _git(root, "show", f"HEAD:{SIEGEL_REL}", text=False)
    if r is not None and r.returncode == 0:
        qu = _aus_bytes(r.stdout, "git-head", {})
        if qu:
            qu["beschreibung"] = "committeter Stand (HEAD)"
            return qu, protokoll
    else:
        protokoll.append("git-head: kein committeter Stand lesbar")

    for sha in _lock_revisionen(root):
        r = _git(root, "show", f"{sha}:{SIEGEL_REL}", text=False)
        if r is None or r.returncode != 0:
            continue
        qu = _aus_bytes(r.stdout, "git-historie", {"commit": sha[:8]})
        if qu:
            betreff = _git(root, "log", "-1", "--format=%s", sha)
            qu["beschreibung"] = (
                f"jüngste gültige Fassung der Historie ({sha[:8]}"
                + (f", {betreff.stdout.strip()[:60]}" if betreff and betreff.returncode == 0 else "")
                + ")")
            return qu, protokoll
    protokoll.append("git-historie: keine gültige Fassung in der lokalen "
                     "Historie (flacher Klon?)")

    # Bergung: nur aus dem COMMITTETEN Artefakt. Eine Laufzeit-Mutation des
    # Locks ist die Klasse, die ein Siegel fangen muss – sie wird nicht geadelt.
    if not stand_gleich_head(root, SIEGEL_REL):
        protokoll.append("bergung: verworfen – das beschädigte Siegel ist "
                         "NICHT committet (Laufzeit-Mutation, Mensch entscheidet)")
        return {}, protokoll
    pfad = root / SIEGEL_REL
    geborgen = lock_bergen(pfad.read_text(encoding="utf-8", errors="replace"))
    if not geborgen:
        protokoll.append("bergung: nichts Verwertbares vor der Bruchstelle")
        return {}, protokoll
    crit, fest = verify_files(root, geborgen["files"])
    soll = {p for p in (KRITISCH | FEST) if (root / p).exists()}
    fehlend = sorted(soll - set(geborgen["files"]))
    fremd = sorted(set(geborgen["files"]) - soll)
    gruende = []
    if crit or fest:
        gruende.append(f"Baum weicht ab (kritisch={crit or '–'}, fest={fest or '–'})")
    if fehlend:
        gruende.append(f"{len(fehlend)} gesperrte Datei(en) fehlen in der "
                       f"geborgenen Map (z. B. {fehlend[:3]})")
    if fremd:
        gruende.append(f"{len(fremd)} unbekannte(r) Pfad(e) in der Map "
                       f"(z. B. {fremd[:3]})")
    if gruende:
        protokoll.append("bergung: verworfen – " + "; ".join(gruende))
        return {}, protokoll
    return {"art": "bergung", "files": geborgen["files"],
            "audit": geborgen["audit"], "zustand": befund,
            "beschreibung": (f"Bergung aus dem beschädigten Artefakt "
                             f"({len(geborgen['audit'])} lesbare "
                             f"Akteneinträge, Map deckt den Baum exakt)")}, protokoll


def lock_reparatur(root: Path = ROOT, dry_run: bool = False,
                   aus_heal: bool = False) -> int:
    """Heilt ein beschädigtes Siegel BELEGT – oder stoppt hart.

    Der Unterschied zum Signieren ist der Nachweis: Es wird nichts neu
    gezeichnet, was nicht aus dem Git stammt oder aus dem Artefakt geborgen
    und gegen den Baum geprüft ist. Bleibt Drift übrig, gilt die gewohnte
    Regel (KRITISCH/Laufzeit-Mutation = Mensch); die Exit-Codes sind dieselben.
    """
    pfad = root / SIEGEL_REL
    befund = lock_zustand(pfad)
    if befund["zustand"] in GESUND:
        print("✅ Integritäts-Siegel ist intakt – nichts zu reparieren "
              f"({ZUSTAND_KLARTEXT[befund['zustand']]}).")
        return 0
    print("🛠️  INTEGRITÄTS-SIEGEL BESCHÄDIGT – Diagnose:")
    print("\n".join("   " + z for z in lock_zustand_text(befund, praefix="")))
    quelle, protokoll = _reparatur_quelle(root, befund)
    if not quelle:
        print("🛑 KEINE BELEGTE QUELLE – Reparatur ist eine Betreiber-Entscheidung:")
        for z in protokoll:
            print(f"   - {z}")
        if not dry_run:
            report_schreiben(root, [], [], lockzustand=befund,
                             blockiert=protokoll)
        print("   → Lock aus dem Git prüfen (volle Historie auschecken), dann "
              "bewusst signieren: python3 scripts/integrity_guard.py --set-current")
        return 3
    print(f"   Quelle: {quelle['beschreibung']}")
    for z in protokoll:
        print(f"   - {z}")
    neuer = {
        "date": date.today().isoformat(),
        "art": "repair",
        "head": git_head(root),
        # Der geborgene/historische Stand ist die Signatur; neu GEZEICHNET
        # wird keine Datei – das steht hier ausdrücklich als leere Liste,
        # damit niemand eine stille Neuzeichnung hineinliest.
        "geaendert": [],
        "quelle": {
            "art": quelle["art"],
            "beschreibung": quelle["beschreibung"],
            **({"commit": quelle["commit"]} if quelle.get("commit") else {}),
            "geborgene_akteneintraege": len(quelle["audit"]),
        },
        "beschaedigung": {
            "zustand": befund["zustand"],
            "groesse": befund.get("groesse"),
            "offset": befund.get("offset"),
            "verdacht": befund.get("verdacht"),
            "detail": befund.get("detail", []),
        },
    }
    dokument = _lock_dokument(root, quelle["files"], quelle["audit"], neuer)
    if dry_run:
        print(f"🔎 --repair-lock --dry-run: würde {len(quelle['files'])} Dateien "
              f"aus „{quelle['art']}" f"“ übernehmen und die Akte verketten "
              f"({len(quelle['audit'])} Einträge + Reparatur-Eintrag). "
              f"Nichts geschrieben.")
        return 0
    ok, meldung = lock_schreiben(root, dokument)
    if not ok:
        print(f"🛑 Reparatur NICHT geschrieben: {meldung}")
        return 3
    crit_bad, fest_bad = verify_files(root, quelle["files"])
    audit = (klassifizieren(root, crit_bad, fest_bad, dokument.get("head", ""))
             if (crit_bad or fest_bad) else [])
    blockiert = ([f"{SIEGEL_REL}: Siegel wurde belegt repariert – Drift danach "
                  f"nicht selbst-signierbar"] if crit_bad else [])
    report_schreiben(root, crit_bad, fest_bad, audit=audit,
                     reparatur={"quelle": quelle, "befund": befund,
                                "kontrolle": meldung},
                     blockiert=blockiert, lockzustand=lock_zustand(pfad))
    historie_schreiben(root, {
        "date": date.today().isoformat(),
        "kritisch": len(crit_bad), "fest": len(fest_bad),
        "modus": "repair", "quelle": quelle["art"],
        "geaendert": [], "head": dokument.get("head", ""),
    })
    melde(f"Integritäts-Siegel war beschädigt ({befund['zustand']}, Byte "
          f"{befund.get('offset')}) – belegt aus „{quelle['art']}“ "
          f"wiederhergestellt: {meldung}.")
    if crit_bad or fest_bad:
        print("🛑 Nach der Reparatur bleibt Drift – HARD STOP (Mensch entscheidet):")
        for z in list(crit_bad) + list(fest_bad):
            print(f"   - {z}")
        return exit_fuer(crit_bad, fest_bad)
    print(f"🔧 SIEGEL REPARIERT ({quelle['art']}): {len(quelle['files'])} "
          f"Kerndateien entsprechen wieder exakt dem signierten Stand. "
          f"Keine Datei wurde neu gezeichnet – nur die zerstörte Akte ersetzt.")
    if aus_heal:
        print("   Der Lauf fährt danach mit der normalen Heilungsprüfung fort.")
    print(f"   Kontrolle: {meldung}")
    return 0


def historie_schreiben(root: Path, eintrag: dict) -> None:
    """Append-Only-Historie. Pflichtfelder (date/kritisch/fest) hält
    `history_guard.py` fest – Zusatzfelder sind dort ausdrücklich erlaubt."""
    pfad = root / "data" / "integrity_history.jsonl"
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with pfad.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(eintrag, ensure_ascii=False) + "\n")


def report_text(root: Path, crit_bad, fest_bad, audit=None,
                geheilt=None, blockiert=None, lockzustand=None,
                reparatur=None) -> str:
    lock = load_lock(root / "data" / "integrity_lock.json")
    befund = lockzustand or lock.get("_zustand") or {"zustand": ZUSTAND_FEHLT,
                                                     "groesse": 0, "offset": None,
                                                     "verdacht": "unbekannt",
                                                     "detail": []}
    L = ["# 🔐 INTEGRITY-REPORT", "",
         f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · HEAD: `{git_head(root)}`",
         f"**Siegel-Fassung:** {lock.get(SCHEMA_FELD, 'legacy')} · "
         f"**Zustand:** {ZUSTAND_KLARTEXT.get(befund['zustand'], befund['zustand'])}",
         f"**Lock-Ebene:** {len(lock.get('files', {}))} Dateien gelockt",
         f"**Gesperrte kritische Knoten:** {len(KRITISCH)}",
         f"**Letzte Signatur:** {lock.get('signed_at', 'nie')} · Stand `{lock.get('head', '')}`",
         ""]
    if befund["zustand"] not in GESUND:
        # ERST die Ursache, dann das Bild: Am 21.09.2026 stand hier die
        # Symptomliste („6 Knoten ohne Signatur"), während nur die Akte
        # zerbrochen war – der Mensch suchte an der falschen Stelle.
        L += ["## 🧨 Zustand des Siegels (Ursache vor Symptom)", ""]
        L += lock_zustand_text(befund)
        L += ["", "**Die Abweichungsliste unten ist in diesem Zustand NICHT "
              "belastbar** – ein zerstörtes Siegel kennt weder Zusagen noch "
              "Vorwürfe. Reparatur: `python3 scripts/integrity_guard.py "
              "--repair-lock` (die Engine heilt das selbst), sonst "
              "`--set-current` als Betreiber-Entscheidung.", ""]
    if reparatur:
        qu = reparatur.get("quelle", {})
        bef = reparatur.get("befund", {})
        L += ["## 🔧 Siegel belegt repariert", "",
              f"- Quelle: **{qu.get('art', '?')}** – {qu.get('beschreibung', '')}",
              f"- Übernommen: {len(qu.get('files', {}))} Dateien, "
              f"{len(qu.get('audit', []))} Akteneinträge",
              f"- Beschädigung: {bef.get('zustand')} · "
              f"{bef.get('groesse')} Bytes · Bruchstelle Byte {bef.get('offset')} · "
              f"Verdacht: {bef.get('verdacht')}",
              f"- Rück-Leseprobe: {reparatur.get('kontrolle', '')}",
              "- **Keine Datei wurde neu gezeichnet** – nur die zerstörte Akte "
              "wurde durch den belegten Stand ersetzt.", ""]
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
                     geheilt=None, blockiert=None, lockzustand=None,
                     reparatur=None) -> list:
    text = report_text(root, crit_bad, fest_bad, audit, geheilt, blockiert,
                       lockzustand, reparatur)
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
    # 22.09.2026 (Issue #346): das Siegel selbst ist prüfbar geworden.
    "siegel_zerstoert_erkannt",
    "siegel_zusammenschnitt_erkannt",
    "reparatur_belegt_beendet",
    "abbruch_laesst_alten_stand",
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
        # Lock-Datei-Form (Roundtrip). Die Probe läuft IM Temp-Verzeichnis:
        # Ein Beweis-Modus, der den Baum anfasst (früher
        # `ROOT/data/integrity_probe_tmp.json` – und auf einem Baum ohne
        # `data/` zusätzlich abstürzte), widerspricht C15 und dem eigenen
        # Versprechen „ohne einen Schreibzugriff".
        probe = Path(td) / "integrity_probe_tmp.json"
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

            # 8. SIEGEL-DIAGNOSE + BELEGTE REPARATUR (22.09.2026, Issue #346).
            pfad = lock_pfad
            # Der Vorfall in klein: ein gültiges Siegel wird committet, dann
            # zu einem Zusammenschnitt verstümmelt (vorne vollständig, hinten
            # der Rest einer anderen Fassung) und genau so committet.
            # Vorbereitung: Der Fixture-Baum steht nach Fall 4/5 bewusst im
            # Drift (HARD STOPs, nie signiert). Erst die Betreiber-Signatur
            # macht daraus wieder eine kohärente, committete Generation – die
            # Grundlage, ohne die eine Reparatur nichts beweisen könnte.
            with contextlib.redirect_stdout(io.StringIO()):
                set_current(tmp)
            _fixture_commit(tmp, "chore(integrity): Stand bewusst signiert")
            gut = pfad.read_text(encoding="utf-8")
            pfad.write_text(gut[: int(len(gut) * 0.55)] + "\n      ]\n    }\n  ]\n}\n",
                            encoding="utf-8")
            _fixture_commit(tmp, "chore: Siegel zusammengeschnitten (Vorfall-Simulation)")
            zustand = lock_zustand(pfad)
            if zustand["zustand"] != ZUSTAND_BESCHAEDIGT:
                fehler.append(f"zerstörtes Siegel nicht erkannt ({zustand['zustand']}, Fall8)")
            if not isinstance(zustand.get("offset"), int) or zustand["offset"] <= 0:
                fehler.append("Bruchstelle nicht benannt (Fall8b)")
            if lock_reparatur(tmp) != 0:
                fehler.append("belegte Reparatur des Siegels fehlgeschlagen (Fall8c)")
            if lock_zustand(pfad)["zustand"] != ZUSTAND_OK:
                fehler.append("Siegel nach der Reparatur nicht gesund (Fall8d)")
            crit, fest = verify_files(tmp, load_lock(pfad)["files"])
            if crit or fest:
                fehler.append(f"Baum nach der Reparatur nicht sauber (Fall8e: {crit}{fest})")
            if (load_lock(pfad)["audit"][-1] or {}).get("art") != "repair":
                fehler.append("Reparatur ohne Akteneintrag (Fall8f)")
            history_zeilen = [json.loads(z) for z in
                              (tmp / "data" / "integrity_history.jsonl")
                              .read_text(encoding="utf-8").splitlines() if z.strip()]
            if not history_zeilen or history_zeilen[-1].get("modus") != "repair":
                fehler.append("Reparatur ohne Spur in der Historie (Fall8g)")

            # 9. CHIMÄRE: syntaktisch gültig, aber aus zwei Ständen gemischt –
            # genau der Fall, den ein Text-Merge erzeugt (und den ein Blick
            # auf „parst doch" nicht fängt).
            alt = json.loads(pfad.read_text(encoding="utf-8"))
            (tmp / fest_rel).write_text("print('zweite generation')\n", encoding="utf-8")
            _fixture_commit(tmp, "fix: Änderung vor der zweiten Signatur")
            signieren(tmp, grund="selftest-2")
            zweite = json.loads(pfad.read_text(encoding="utf-8"))
            gemischt = dict(alt)
            gemischt["audit"] = list(alt["audit"][:-1]) + [zweite["audit"][-1]]
            pfad.write_text(json.dumps(gemischt, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
            if lock_zustand(pfad)["zustand"] != ZUSTAND_CHIMAERE:
                fehler.append("Zusammengeschnittenes Siegel (Map aus anderer "
                              "Generation) nicht erkannt (Fall9)")
            # 9b. Kette gebrochen: Inhalt eines alten Eintrags verändert.
            verkettet = json.loads(pfad.read_text(encoding="utf-8"))
            verkettet["audit"] = list(zweite["audit"])
            verkettet["audit"][0] = {**verkettet["audit"][0], "head": "0000000"}
            pfad.write_text(json.dumps(verkettet, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
            if lock_zustand(pfad)["zustand"] != ZUSTAND_CHIMAERE:
                fehler.append("Gebrochene Akten-Kette nicht erkannt (Fall9b)")

            # 10. ABBRUCH SICHER: Stirbt der Schreiber mitten im Vorgang, steht
            # die vorige Fassung unverändert da – kein halbes Siegel, kein Rest.
            with contextlib.redirect_stdout(io.StringIO()):
                signieren(tmp, grund="selftest-3")
            vorher_bytes = pfad.read_bytes()
            aktuell = load_lock(pfad)
            echt_replace = os.replace

            def _platzt(*_a, **_k):
                raise OSError("Abbruch simuliert (Runner-Kill)")

            os.replace = _platzt
            try:
                ok_schreiben, _ = lock_schreiben(tmp, _lock_dokument(
                    tmp, aktuell["files"], aktuell["audit"],
                    {"date": date.today().isoformat(), "art": "abriss",
                     "head": git_head(tmp), "geaendert": []}))
            finally:
                os.replace = echt_replace
            if ok_schreiben:
                fehler.append("abgebrochener Schreibvorgang galt als Erfolg (Fall10)")
            if pfad.read_bytes() != vorher_bytes:
                fehler.append("abgebrochener Schreibvorgang hat das Siegel "
                              "verändert (Fall10b)")
            if (tmp / "data" / "integrity_lock.json.tmp").exists():
                fehler.append("Temp-Rest nach Abbruch (Fall10c)")

            # 11. KONFLIKTMARKER: Git-Merge-Konfliktmarker im Siegel werden
            # erkannt (Bruchverdacht: konfliktmarker) und von lock_reparatur geheilt.
            pfad.write_text("<<<<<<< HEAD\n{\"schema\": 2}\n=======\n{\"schema\": 2}\n>>>>>>> branch\n",
                            encoding="utf-8")
            befund_km = lock_zustand(pfad)
            if befund_km["zustand"] != ZUSTAND_BESCHAEDIGT or befund_km.get("verdacht") != "konfliktmarker":
                fehler.append("Konfliktmarker im Siegel nicht erkannt (Fall11)")
            rc_km = lock_reparatur(tmp, dry_run=False)
            if rc_km not in (0, 1) or lock_zustand(pfad)["zustand"] != ZUSTAND_OK:
                fehler.append("Reparatur bei Konfliktmarkern scheiterte (Fall11b)")

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
          f"Kern-Beweis (Klassifikation, Signatur-Regel, Konvergenz, "
          f"Siegel-Diagnose, Reparatur, Abbruchsicherheit) grün – "
          f"ohne einen Schreibzugriff auf den Baum.")
    return 0


# ------------------------------------------------------------
# Modi
# ------------------------------------------------------------
def gate(root: Path = ROOT) -> int:
    """PR-/CI-Gate: fail-closed, mit Herkunft und Reparaturzeile.

    Seit dem 22.09.2026 prüft das Gate ZUERST das Siegel selbst: Ein
    beschädigtes oder zusammengesetztes Siegel ist ein eigener Befund (mit
    Bruchstelle und Reparaturzeile), kein „Drift in sechs Dateien".
    """
    befund = lock_zustand(root / "data" / "integrity_lock.json")
    if befund["zustand"] not in GESUND:
        print("🛑 INTEGRITÄTS-GATE ROT – das Siegel selbst ist nicht gesund "
              f"({ZUSTAND_KLARTEXT.get(befund['zustand'])}).")
        print("")
        print("\n".join(lock_zustand_text(befund)))
        print("")
        print("In diesem Zustand ist keine Aussage über den Kern möglich – "
              "auch keine grüne. Deshalb fail-closed (Exit 3).")
        print("")
        print("Fix (auf `main` heilt die Engine das im ersten Schritt selbst):")
        print("    python3 scripts/integrity_guard.py --repair-lock")
        print("    python3 scripts/integrity_guard.py --set-current   # nur wenn "
              "die Reparatur keine belegte Quelle findet")
        print("    git add data/integrity_lock.json data/integrity_history.jsonl")
        print("Hinweis: `data/integrity_lock.json` ist ein MASCHINEN-Artefakt – "
              "bei einem Merge-Konflikt NICHT zusammensetzen, sondern eine "
              "Fassung wählen und neu signieren (.gitattributes: merge=binary).")
        print(GATE_REGEL)
        return 3
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
    """Selbstheilung für belegten Drift – HARD STOP bleibt für alles andere.

    Seit dem 22.09.2026 heilt der Schritt ZUERST ein beschädigtes Siegel
    (`--repair-lock`, belegt aus Git/Bergung). Genau daran ist die Engine am
    21.09.2026 gestorben: Der Kern war unversehrt, nur die Akte zerbrochen,
    und es gab keinen Weg zurück außer einer menschlichen Signatur.
    """
    lock_pfad = root / "data" / "integrity_lock.json"
    befund = lock_zustand(lock_pfad)
    if befund["zustand"] not in GESUND:
        melde(f"Integritäts-Siegel ist beschädigt "
              f"({ZUSTAND_KLARTEXT.get(befund['zustand'])}, Byte "
              f"{befund.get('offset')}) – Reparatur wird geprüft.")
        rc = lock_reparatur(root, dry_run=dry_run, aus_heal=True)
        if dry_run or rc in (0, 3):
            return rc
        # rc == 1: FEST-Drift gegen die wiederhergestellte Signatur – dafür
        # gilt unten die normale, belegte Heilungsregel.
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
    try:
        ergebnis = signieren(root, grund="heal", audit=audit)
    except LockSchreibfehler as exc:
        # Kein stilles Weiterlaufen: Wer nicht schreiben kann, hat nicht
        # signiert – der Baum bleibt unangetastet, der Lauf wird rot.
        print(f"🛑 Selbst-Signatur NICHT geschrieben: {exc}")
        return 3
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
    befund = lock_zustand(root / "data" / "integrity_lock.json")
    if befund["zustand"] not in GESUND and not SET_CURRENT:
        print("🧨 SIEGEL NICHT GESUND – die Drift-Aufstellung unten ist darum "
              "zweitrangig:")
        print("\n".join(lock_zustand_text(befund, praefix="  ")))
        print("  Reparatur: python3 scripts/integrity_guard.py --repair-lock "
              "(oder --set-current als Betreiber-Entscheidung).")
    lock = load_lock(root / "data" / "integrity_lock.json")
    crit_bad, fest_bad = verify_files(root, lock.get("files", {}))
    if not crit_bad and not fest_bad and befund["zustand"] in GESUND:
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


def set_current(root: Path = ROOT) -> int:
    """Die bewusste Betreiber-Signatur – sie NENNT, was sie zeichnet.

    Nachgetragen am 21.09.2026 (#338/#344). Vorher schrieb genau dieser Weg
    keine Herkunft in die Akte, während `--heal` sie immer mit-schreibt – und
    `--set-current` ist der Weg, den das Gate selbst in seiner Reparaturzeile
    empfiehlt. Damit war die kommentarlose Neuzeichnung der bequemste und
    zugleich der einzige Weg ohne Spur: Wer eine gesperrte Kerndatei ändert
    (wie #344 den `head.html`), konnte den Lock zeichnen, ohne dass im Lock
    steht, welcher Commit das ausgelöst hat. Gefunden wurde das erst, als
    `main` deshalb am Gate rot war und der nächste Content-Engine-Lauf in den
    Hard Stop gelaufen wäre.

    Die Signatur bleibt eine menschliche Entscheidung – aber keine stumme:
    Klasse, Urteil und die belegenden Commits stehen danach im Lock, und der
    Vorgang hinterlässt eine Zeile in `data/integrity_history.jsonl`.
    """
    lock_pfad = root / "data" / "integrity_lock.json"
    lock = load_lock(lock_pfad)
    crit_bad, fest_bad = verify_files(root, lock.get("files", {}))
    audit = (klassifizieren(root, crit_bad, fest_bad, lock.get("head", ""))
             if (crit_bad or fest_bad) else [])
    try:
        ergebnis = signieren(root, grund="set-current", audit=audit or None)
    except LockSchreibfehler as exc:
        print(f"🛑 Signatur NICHT geschrieben: {exc}")
        return 3
    print(f"🔒 Signiert: {ergebnis['signiert']} Dateien gegen SHA-256 gelockt "
          f"(HEAD {git_head(root)}).")
    if not ergebnis["geaendert"]:
        print("   Kein Drift – die Signatur war schon aktuell.")
    else:
        print(f"   Neu gezeichnet ({len(ergebnis['geaendert'])}): "
              + ", ".join(ergebnis["geaendert"]))
        for e in audit:
            if e["pfad"] not in ergebnis["geaendert"]:
                continue
            commits = ", ".join(c["sha"] for c in (e.get("commits") or [])[:3]) \
                or "keine belegten Commits"
            print(f"   Herkunft: {e['pfad']} [{e['klasse']}, {e['urteil']}] {commits}")
    historie_schreiben(root, {
        "date": date.today().isoformat(),
        "kritisch": len(crit_bad), "fest": len(fest_bad),
        "modus": "set-current", "geaendert": ergebnis["geaendert"],
    })
    return 0


def main():
    if SELFTEST_MODE:
        sys.exit(selftest())

    fehler = _selftest()
    if fehler:
        print("🛑 INTEGRITY-SELBSTTEST FEHLGESCHLAGEN.")
        print("\n".join(fehler)); sys.exit(2)
    print(f"✅ Integrity-Selbsttest: {len(SELFTEST)} Faelle gruen.")

    if SET_CURRENT:
        sys.exit(set_current(ROOT))

    if REPAIR_LOCK:
        sys.exit(lock_reparatur(ROOT, dry_run=DRY_RUN))

    if ADD_PATH:
        rp = ROOT / ADD_PATH
        if not rp.exists():
            print(f"🔴 Ziel nicht da: {ADD_PATH}"); sys.exit(2)
        lock = load_lock(LOCK)
        vorher = sha256_file(rp)
        files = {**lock.get("files", {}), ADD_PATH: vorher}
        eintrag = {"date": date.today().isoformat(), "art": "add",
                   "head": git_head(ROOT), "geaendert": [ADD_PATH] if vorher else []}
        dokument = _lock_dokument(ROOT, files, list(lock.get("audit") or []),
                                  eintrag)
        ok, meldung = lock_schreiben(ROOT, dokument)
        if not ok:
            print(f"🛑 {ADD_PATH} NICHT aufgenommen – {meldung}")
            sys.exit(3)
        print(f"🔒 {ADD_PATH} in den Lock aufgenommen (neu signiert, {meldung}).")
        return

    # Die drei Sichten auf den Drift rechnen selbst (und bleiben so auch
    # einzeln aufrufbar); der Standard-Verify folgt darunter.
    if GATE:
        sys.exit(gate(ROOT))
    if HEAL:
        sys.exit(heilen(ROOT, dry_run=DRY_RUN))
    if DRIFT_AUDIT:
        sys.exit(drift_audit(ROOT))

    befund = lock_zustand(LOCK)
    lock = load_lock(LOCK)
    crit_bad, fest_bad = verify_files(ROOT, lock.get("files", {}))
    audit = (klassifizieren(ROOT, crit_bad, fest_bad, lock.get("head", ""))
             if (crit_bad or fest_bad) else [])
    report_schreiben(ROOT, crit_bad, fest_bad, audit=audit, lockzustand=befund)
    historie_schreiben(ROOT, {"date": date.today().isoformat(),
                              "kritisch": len(crit_bad), "fest": len(fest_bad),
                              "modus": "verify"})
    if befund["zustand"] not in GESUND:
        # Ein zerstörtes Siegel ist ein eigener, lauter Befund mit Reparaturweg.
        print("🧨 SIEGEL NICHT GESUND – " + ZUSTAND_KLARTEXT.get(
            befund["zustand"], befund["zustand"]))
        for z in lock_zustand_text(befund, praefix="   "):
            print(z)
        print("   Reparatur: python3 scripts/integrity_guard.py --repair-lock")
        sys.exit(3)
    sys.exit(exit_fuer(crit_bad, fest_bad))


if __name__ == "__main__":
    main()
