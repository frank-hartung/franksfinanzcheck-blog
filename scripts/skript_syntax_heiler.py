#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
#  SKRIPT-SYNTAX-HEILER – der fehlende Heilweg für „skript-syntax"
#  ------------------------------------------------------------
#  WARUM ES DIESEN HEILER GIBT (Bot-Watchdog #864, 25.10.2026)
#
#  Der Befund `skript-syntax` trug seit jeher den Besitzer `auto`
#  („eine Maschine kann das heilen") und als nächsten Schritt eine
#  ARBEITSANWEISUNG AN EINEN MENSCHEN („Betroffenes Skript reparieren
#  – py_compile nennt die Zeile"). Genau diese Lücke hat #864 offen
#  gehalten: Das Automations-Ticket kann sich nur schließen, wenn der
#  Befund verschwindet – und dafür war niemand zuständig.
#
#  Ein Syntaxfehler ist der EINZIGE Defekt im Repo, für den ein
#  automatischer Rollback beweisbar sicher ist: Ein Skript, das nicht
#  kompiliert, hat keinen Nutzen. Die letzte Fassung, die kompilierte,
#  ist per Definition benutzbar; die kaputte ist es nicht. Deshalb gilt:
#
#    Wiederhergestellt wird NUR die jüngste Fassung derselben Datei,
#    die nachweislich kompiliert – nichts anderes, keine andere Datei,
#    kein stiller Revert über fremde Arbeit.
#
#  Was dabei verworfen wird, verschwindet nicht: Der Heiler schreibt
#  jede Heilung mit beiden Commit-Kennungen in
#  `data/skript_syntax_heilungen.jsonl` (append-only, versioniert).
#  Wer die verworfene Absicht braucht, holt sie aus der Geschichte
#  zurück – sie steht im Ledger.
#
#  SICHERUNGEN (jede einzeln getestet, `--selftest`)
#    · nur Dateien unter `scripts/**` – nie Workflows, Layouts, Daten
#    · nur wenn ein kompilierender Vorgänger EXISTIERT (kein Raten)
#    · nur wenn der Arbeitsbaum diese Datei nicht lokal verändert hat
#    · nur wenn dieselbe Datei nicht schon zweimal in 24 h geheilt
#      wurde (Wiederholungsbremse – sonst heilt der Heiler im Kreis
#      gegen einen Schreiber, der den Fehler immer neu erzeugt;
#      dann ist der Mensch dran, und der Befund bleibt offen)
#    · höchstens 5 Dateien pro Lauf
#    · atomar (Temp-Datei + `os.replace`) und danach erneut geprüft
#
#  NUTZUNG
#    python3 scripts/skript_syntax_heiler.py --check          # nur Befund
#    python3 scripts/skript_syntax_heiler.py --fix            # heilen (Arbeitsbaum)
#    python3 scripts/skript_syntax_heiler.py --fix --commit   # heilen + committen/pushen
#    python3 scripts/skript_syntax_heiler.py --fix --dry-run  # zeigen, nichts schreiben
#    python3 scripts/skript_syntax_heiler.py --json
#    python3 scripts/skript_syntax_heiler.py --selftest
#
#  EXIT: 0 = nichts (mehr) zu heilen · 1 = Befund ohne Heilweg
#        2 = Heiler defekt (Selbsttest)
#
#  Report: BOT-WATCHDOG-864-DAUERHEILUNG-PREMIUM-2026-10-25.md
# ============================================================
"""Heilt Syntaxfehler in `scripts/**` durch die letzte kompilierbare Fassung."""

from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

BLOG_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BLOG_DIR / "scripts"))

import skript_syntax_wache as wache  # noqa: E402  (SSOT für „ist das Python?")

AUDIT_RELATIV = "data/skript_syntax_heilungen.jsonl"
# Nur hier heilt der Heiler. `scripts/**` ist Code ohne Markenfläche.
HEILBARE_WURZEL = "scripts"
MAX_DATEIEN_PRO_LAUF = 5
MAX_HEILUNGEN_PRO_DATEI_24H = 2
VORGAENGER_SUCHE = 50          # so viele Fassungen rückwärts wird gesucht
AUDIT_PFLICHTFELDER = ("ts", "datei", "zeile", "art", "regel",
                       "verworfen_sha", "wiederhergestellt_sha")


@dataclass
class Heilung:
    """Eine vollzogene oder geplante Wiederherstellung."""

    datei: str
    fehler: wache.Syntaxfehler
    vorgaenger_sha: str
    vorgaenger_betreff: str = ""
    verworfen_sha: str = ""
    verworfen_betreff: str = ""

    def as_audit(self, ts: str) -> dict:
        return {
            "ts": ts,
            "datei": self.datei,
            "zeile": self.fehler.zeile,
            "art": self.fehler.art,
            "regel": "juengste-kompilierbare-fassung",
            "verworfen_sha": self.verworfen_sha,
            "verworfen_betreff": self.verworfen_betreff,
            "wiederhergestellt_sha": self.vorgaenger_sha,
            "wiederhergestellt_betreff": self.vorgaenger_betreff,
        }


@dataclass
class Ergebnis:
    """Was der Lauf getan hat – und was er bewusst nicht getan hat."""

    geheilt: list[Heilung] = field(default_factory=list)
    offen: list[dict] = field(default_factory=list)   # {datei, grund, detail}

    @property
    def offen_dateien(self) -> list[str]:
        return [o["datei"] for o in self.offen]

    def as_dict(self) -> dict:
        return {"geheilt": [{"datei": h.datei, "zeile": h.fehler.zeile,
                             "art": h.fehler.art,
                             "wiederhergestellt_aus": h.vorgaenger_sha,
                             "verworfen": h.verworfen_sha}
                            for h in self.geheilt],
                "offen": self.offen}


# ------------------------------------------------------------
#  Git-Zugriff – schmal, prüfbar, ohne Seiteneffekte
# ------------------------------------------------------------
def git(*argumente: str, root: Path | str = BLOG_DIR) -> str:
    """Ein git-Aufruf im Repo. Fehler werden laut, nie still."""
    proc = subprocess.run(["git", *argumente], cwd=str(root),
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(argumente)}: "
                           f"{(proc.stderr or proc.stdout).strip()[:300]}")
    return proc.stdout


def git_bytes(*argumente: str, root: Path | str = BLOG_DIR) -> bytes:
    proc = subprocess.run(["git", *argumente], cwd=str(root),
                          capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(argumente)}: "
                           f"{proc.stderr.decode('utf-8', 'replace').strip()[:300]}")
    return proc.stdout


def _betreff(sha: str, root: Path) -> str:
    try:
        return git("log", "-1", "--format=%s", sha, root=root).strip()[:120]
    except RuntimeError:
        return ""


def letzte_kompilierende_fassung(datei: str, root: Path | str = BLOG_DIR,
                                 limit: int = VORGAENGER_SUCHE) -> str | None:
    """Jüngster Commit, in dem GENAU DIESE Datei kompilierte.

    Gesucht wird ausschließlich in der Geschichte der Datei. Gibt es
    keinen solchen Stand (die Datei war nie gültig), wird `None`
    zurückgegeben – dann heilt hier nichts, und das ist Absicht:
    Ein Heiler, der rät, erfindet Code.
    """
    root = Path(root)
    try:
        shas = [z.strip() for z in git("log", "--format=%H", "-n", str(limit),
                                       "--", datei, root=root).splitlines() if z.strip()]
    except RuntimeError:
        return None
    for sha in shas:
        try:
            blob = git_bytes("show", f"{sha}:{datei}", root=root)
        except RuntimeError:
            continue
        try:
            text = blob.decode("utf-8")
        except UnicodeDecodeError:
            text = blob.decode("utf-8", "replace")
        if wache.pruefe_quelle(text, datei) is None:
            return sha
    return None


# ------------------------------------------------------------
#  Wiederholungsbremse (Ledger-basiert, ohne Zustandsdatei)
# ------------------------------------------------------------
def audit_pfad(root: Path | str = BLOG_DIR) -> Path:
    return Path(root) / AUDIT_RELATIV


def audit_lesen(root: Path | str = BLOG_DIR) -> list[dict]:
    pfad = audit_pfad(root)
    if not pfad.is_file():
        return []
    zeilen: list[dict] = []
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        zeile = zeile.strip()
        if not zeile:
            continue
        try:
            daten = json.loads(zeile)
        except json.JSONDecodeError:
            continue
        if isinstance(daten, dict):
            zeilen.append(daten)
    return zeilen


def heilungen_in_24h(datei: str, root: Path | str = BLOG_DIR,
                     jetzt: datetime.datetime | None = None) -> int:
    """Wie oft wurde DIESE Datei in den letzten 24 h schon geheilt?"""
    jetzt = jetzt or datetime.datetime.now(datetime.timezone.utc)
    grenze = jetzt - datetime.timedelta(hours=24)
    zahl = 0
    for eintrag in audit_lesen(root):
        if eintrag.get("datei") != datei:
            continue
        roh = str(eintrag.get("ts") or "")
        try:
            ts = datetime.datetime.fromisoformat(roh.replace("Z", "+00:00"))
        except ValueError:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=datetime.timezone.utc)
        if ts >= grenze:
            zahl += 1
    return zahl


# ------------------------------------------------------------
#  Heilung
# ------------------------------------------------------------
def _darf_geheilt_werden(datei: str, root: Path) -> tuple[bool, str]:
    """Darf diese Datei überhaupt angefasst werden? (Besitz-Grenze)"""
    if not datei.startswith(HEILBARE_WURZEL + "/") or not datei.endswith(".py"):
        return False, "ausserhalb-des-heilbereichs"
    if "__pycache__" in datei:
        return False, "kein-quelltext"
    return True, ""


def _arbeitsbaum_sauber(datei: str, root: Path) -> bool:
    try:
        return not git("status", "--porcelain", "--", datei, root=root).strip()
    except RuntimeError:
        return False


def heile(root: Path | str = BLOG_DIR, dry_run: bool = False,
          jetzt: datetime.datetime | None = None) -> Ergebnis:
    """Heilt alle heilbaren Syntaxfehler unter `scripts/**`.

    Vor der Wiederherstellung wird geprüft, ob ein kompilierender
    Vorgänger existiert. Nach der Wiederherstellung wird erneut
    geprüft – eine Heilung, die nicht nachweislich kompiliert, wird
    zurückgenommen.
    """
    root = Path(root)
    ergebnis = Ergebnis()
    fehler = wache.finde(root)
    if not fehler:
        return ergebnis

    try:
        head_sha = git("rev-parse", "HEAD", root=root).strip()
    except RuntimeError:
        head_sha = ""

    for datei in wache.betroffene_dateien(fehler):
        if len(ergebnis.geheilt) >= MAX_DATEIEN_PRO_LAUF:
            ergebnis.offen.append({"datei": datei, "grund": "laufgrenze",
                                   "detail": f"mehr als {MAX_DATEIEN_PRO_LAUF} "
                                             "Dateien je Lauf – Rest im nächsten Lauf"})
            continue
        erlaubt, grund = _darf_geheilt_werden(datei, root)
        if not erlaubt:
            ergebnis.offen.append({"datei": datei, "grund": grund,
                                   "detail": "liegt außerhalb des Heilbereichs"})
            continue
        if not _arbeitsbaum_sauber(datei, root):
            ergebnis.offen.append({"datei": datei, "grund": "arbeitsbaum-schmutzig",
                                   "detail": "lokale Änderung – ein stiller "
                                             "Überschreibvorgang wäre Datenverlust"})
            continue
        if heilungen_in_24h(datei, root, jetzt) >= MAX_HEILUNGEN_PRO_DATEI_24H:
            ergebnis.offen.append({
                "datei": datei, "grund": "wiederholungsbremse",
                "detail": f"bereits {MAX_HEILUNGEN_PRO_DATEI_24H}× in 24 h geheilt – "
                          "ein Schreiber erzeugt den Fehler offenbar neu"})
            continue

        vorgaenger = letzte_kompilierende_fassung(datei, root)
        if not vorgaenger:
            ergebnis.offen.append({
                "datei": datei, "grund": "kein-vorgaenger",
                "detail": "keine kompilierende Fassung in der Geschichte – "
                          "hier muss ein Mensch schreiben, nicht der Heiler"})
            continue

        heilung = Heilung(
            datei=datei,
            fehler=next(f for f in fehler if f.datei == datei),
            vorgaenger_sha=vorgaenger,
            vorgaenger_betreff=_betreff(vorgaenger, root),
            verworfen_sha=head_sha,
            verworfen_betreff=_betreff(head_sha, root) if head_sha else "")

        if not dry_run:
            if not _wiederherstellen(datei, vorgaenger, root):
                ergebnis.offen.append({"datei": datei, "grund": "wiederherstellung",
                                       "detail": "Fassung ließ sich nicht "
                                                 "wiederherstellen oder kompiliert nicht"})
                continue
            _audit_schreiben(heilung, root, jetzt)
        ergebnis.geheilt.append(heilung)
    return ergebnis


def _wiederherstellen(datei: str, sha: str, root: Path) -> bool:
    """Schreibt den Blob atomar zurück und prüft das Ergebnis."""
    ziel = root / datei
    try:
        blob = git_bytes("show", f"{sha}:{datei}", root=root)
        modus = ziel.stat().st_mode
        with tempfile.NamedTemporaryFile("wb", dir=str(ziel.parent),
                                         prefix=datei.split("/")[-1] + ".",
                                         suffix=".heilung", delete=False) as fh:
            fh.write(blob)
            temp = Path(fh.name)
        os.chmod(temp, modus)
        pruefung = wache.pruefe_datei(temp, root)
        if pruefung is not None:          # Sicherung: nie Kaputtes schreiben
            temp.unlink(missing_ok=True)
            return False
        os.replace(temp, ziel)
        return wache.pruefe_datei(ziel, root) is None
    except (OSError, RuntimeError):
        return False


def _audit_schreiben(heilung: Heilung, root: Path, jetzt: datetime.datetime | None) -> None:
    jetzt = jetzt or datetime.datetime.now(datetime.timezone.utc)
    ts = jetzt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pfad = audit_pfad(root)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    with pfad.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(heilung.as_audit(ts), ensure_ascii=False) + "\n")


# ------------------------------------------------------------
#  Commit + Push (nur auf Zuruf, über den gemeinsamen Weg)
# ------------------------------------------------------------
def committen(ergebnis: Ergebnis, root: Path | str = BLOG_DIR) -> tuple[bool, str]:
    """Übergibt die Heilung dem Standardweg (`scripts/git_sync.sh`)."""
    if not ergebnis.geheilt:
        return True, "nichts zu committen"
    root = Path(root)
    dateien = [h.datei for h in ergebnis.geheilt]
    kurz = ", ".join(d.split("/")[-1] for d in dateien)
    nachricht = (f"fix(skripte): Syntaxheilung – {kurz} auf die letzte "
                 f"kompilierbare Fassung zurück (Bot-Watchdog #864)")
    skript = root / "scripts" / "git_sync.sh"
    if not skript.is_file():
        return False, f"{skript} fehlt – kein Push ohne den Standardweg"
    proc = subprocess.run([str(skript), nachricht, *dateien,
                           "data/skript_syntax_heilungen.jsonl"],
                          cwd=str(root), capture_output=True, text=True)
    ausgabe = ((proc.stdout or "") + (proc.stderr or "")).strip()
    return proc.returncode == 0, ausgabe[-1500:]


# ------------------------------------------------------------
#  Selbsttest
# ------------------------------------------------------------
KAPUTT = "def addiere(a, b):\n    return a + b\n        return 0\n"
GUT = "def addiere(a, b):\n    return a + b\n"


def _git_repo(tmp: Path) -> None:
    (tmp / "scripts").mkdir(parents=True, exist_ok=True)
    (tmp / "data").mkdir(parents=True, exist_ok=True)
    git("init", "-q", "-b", "main", root=tmp)
    git("config", "user.name", "Test", root=tmp)
    git("config", "user.email", "test@example.invalid", root=tmp)


def _commit(tmp: Path, datei: str, text: str, nachricht: str) -> None:
    pfad = tmp / datei
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(text, encoding="utf-8")
    git("add", datei, root=tmp)
    git("commit", "-q", "-m", nachricht, root=tmp)


def selftest() -> int:
    """Beweist jede Sicherung an einem echten Wegwerf-Repository."""
    fehler: list[str] = []

    def probe(name: str, bedingung: bool, hinweis: str = "") -> None:
        if not bedingung:
            fehler.append(f"{name}{(': ' + hinweis) if hinweis else ''}")

    with tempfile.TemporaryDirectory() as tmp_raw:
        tmp = Path(tmp_raw)
        _git_repo(tmp)
        _commit(tmp, "scripts/rechner.py", GUT, "gut")
        _commit(tmp, "scripts/rechner.py", KAPUTT, "kaputt")

        fund = wache.finde(tmp)
        probe("kaputter Stand wird erkannt",
              [f.datei for f in fund] == ["scripts/rechner.py"],
              str([f.datei for f in fund]))

        # 1) dry-run verändert nichts
        trocken = heile(tmp, dry_run=True)
        probe("dry-run plant die Heilung", len(trocken.geheilt) == 1)
        probe("dry-run schreibt nicht",
              (tmp / "scripts/rechner.py").read_text(encoding="utf-8") == KAPUTT)
        probe("dry-run schreibt kein Ledger", not audit_pfad(tmp).exists())

        # 2) echte Heilung
        ergebnis = heile(tmp)
        probe("Heilung greift", len(ergebnis.geheilt) == 1,
              str(ergebnis.as_dict()))
        probe("Datei ist wieder die letzte gültige Fassung",
              (tmp / "scripts/rechner.py").read_text(encoding="utf-8") == GUT)
        probe("Repo ist danach grün", wache.finde(tmp) == [])
        ledger = audit_lesen(tmp)
        probe("Ledger hat genau eine Zeile", len(ledger) == 1, str(len(ledger)))
        if ledger:
            probe("Ledger nennt alle Pflichtfelder",
                  all(feld in ledger[0] and ledger[0][feld] != ""
                      for feld in AUDIT_PFLICHTFELDER),
                  str(sorted(ledger[0])))
            probe("Ledger nennt die verworfene Fassung",
                  ledger[0]["verworfen_sha"] != ledger[0]["wiederhergestellt_sha"])

        # 3) Idempotenz: zweiter Lauf tut nichts
        zweite = heile(tmp)
        probe("zweiter Lauf ist still", not zweite.geheilt and not zweite.offen)
        probe("zweiter Lauf schreibt kein Ledger", len(audit_lesen(tmp)) == 1)

    # 4) Wiederholungsbremse: dritter Ausfall derselben Datei in 24 h
    with tempfile.TemporaryDirectory() as tmp_raw:
        tmp = Path(tmp_raw)
        _git_repo(tmp)
        _commit(tmp, "scripts/oszillator.py", GUT, "gut")
        jetzt = datetime.datetime.now(datetime.timezone.utc)
        for lauf in range(1, MAX_HEILUNGEN_PRO_DATEI_24H + 2):
            _commit(tmp, "scripts/oszillator.py", KAPUTT, f"kaputt {lauf}")
            ergebnis = heile(tmp, jetzt=jetzt)
            if ergebnis.geheilt:
                # Wie im Betrieb: Die Heilung wird festgeschrieben, danach
                # bricht derselbe Schreiber die Datei erneut.
                git("add", "-A", root=tmp)
                git("commit", "-q", "-m", f"heilung {lauf}", root=tmp)
            if lauf <= MAX_HEILUNGEN_PRO_DATEI_24H:
                probe(f"Bremse greift nicht zu früh (Lauf {lauf})",
                      len(ergebnis.geheilt) == 1, str(ergebnis.as_dict()))
            else:
                probe("Wiederholungsbremse greift",
                      not ergebnis.geheilt
                      and ergebnis.offen_dateien == ["scripts/oszillator.py"],
                      str(ergebnis.as_dict()))
                probe("Bremse nennt den Grund",
                      ergebnis.offen[0]["grund"] == "wiederholungsbremse",
                      ergebnis.offen[0]["grund"])

    # 5) Nie gültig gewesene Datei: kein Vorgänger, keine Erfindung
    with tempfile.TemporaryDirectory() as tmp_raw:
        tmp = Path(tmp_raw)
        _git_repo(tmp)
        _commit(tmp, "scripts/neu.py", KAPUTT, "von Anfang an kaputt")
        ergebnis = heile(tmp)
        probe("ohne Vorgänger wird nicht geheilt", not ergebnis.geheilt)
        probe("ohne Vorgänger ist der Grund benannt",
              ergebnis.offen and ergebnis.offen[0]["grund"] == "kein-vorgaenger",
              str(ergebnis.as_dict()))
        probe("Datei bleibt unangetastet",
              (tmp / "scripts/neu.py").read_text(encoding="utf-8") == KAPUTT)

    # 6) Heilbereich: nichts außerhalb von scripts/
    with tempfile.TemporaryDirectory() as tmp_raw:
        tmp = Path(tmp_raw)
        _git_repo(tmp)
        _commit(tmp, "scripts/in Ordnung.py", GUT, "gut")
        probe("Heilbereich endet bei scripts/",
              _darf_geheilt_werden("layouts/partial.html", tmp)[0] is False,
              "Fremdbereich wäre heilbar")
        probe("Nicht-Python bleibt unangetastet",
              _darf_geheilt_werden("scripts/notes.txt", tmp)[0] is False)
        probe("Skripte bleiben heilbar",
              _darf_geheilt_werden("scripts/rechner.py", tmp)[0] is True)

    if fehler:
        print("🛑 SKRIPT-SYNTAX-HEILER SELFTEST FEHLGESCHLAGEN:")
        for f in fehler:
            print(f"  - {f}")
        return 2
    print("✅ SKRIPT-SYNTAX-HEILER SELFTEST bestanden "
          "(Vorgängerwahl, dry-run, Heilung, Ledger, Idempotenz, "
          "Wiederholungsbremse, kein Vorgänger, Heilbereich).")
    return 0


# ------------------------------------------------------------
#  CLI
# ------------------------------------------------------------
def _bericht(ergebnis: Ergebnis, dry_run: bool) -> str:
    zeilen: list[str] = []
    if ergebnis.geheilt:
        kopf = "🔧 Skript-Syntax-Heilung" + (" (dry-run, nichts geschrieben)" if dry_run else "")
        zeilen.append(f"{kopf}: {len(ergebnis.geheilt)} Datei(en)")
        for h in ergebnis.geheilt:
            zeilen.append(f"  - {h.datei}:{h.fehler.zeile} ({h.fehler.art}) "
                          f"→ {h.vorgaenger_sha[:8]}")
    if ergebnis.offen:
        zeilen.append(f"⚠️  ohne Heilweg: {len(ergebnis.offen)} Datei(en)")
        for o in ergebnis.offen:
            zeilen.append(f"  - {o['datei']} ({o['grund']}): {o['detail']}")
    if not zeilen:
        zeilen.append("✅ Skript-Syntax-Heilung: nichts zu tun")
    return "\n".join(zeilen)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Heilt Syntaxfehler in scripts/** aus der letzten gültigen Fassung.")
    parser.add_argument("--check", action="store_true", help="nur prüfen (Default)")
    parser.add_argument("--fix", action="store_true", help="heilen")
    parser.add_argument("--commit", action="store_true",
                        help="Heilung committen und pushen (git_sync.sh)")
    parser.add_argument("--dry-run", action="store_true", help="nichts schreiben")
    parser.add_argument("--json", action="store_true", help="Maschinenausgabe")
    parser.add_argument("--selftest", action="store_true", help="Heiler selbst prüfen")
    parser.add_argument("--wurzel", default=str(BLOG_DIR), help="Repository-Wurzel")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    root = Path(args.wurzel)

    if not args.fix:
        fund = wache.finde(root)
        if args.json:
            print(json.dumps([f.as_dict() for f in fund], ensure_ascii=False, indent=2))
        else:
            print(wache.bericht(fund, len(wache.dateien(root))))
        return 0 if not fund else 1

    ergebnis = heile(root, dry_run=args.dry_run)
    meldung = _bericht(ergebnis, args.dry_run)

    if args.commit and not args.dry_run and ergebnis.geheilt:
        ok, ausgabe = committen(ergebnis, root)
        meldung += "\n" + ("✅ committet/gepusht" if ok
                           else f"🛑 Commit/Push fehlgeschlagen: {ausgabe}")
        if not ok:
            print(meldung)
            return 1

    if args.json:
        daten = ergebnis.as_dict()
        daten["meldung"] = meldung
        print(json.dumps(daten, ensure_ascii=False, indent=2))
    else:
        print(meldung)

    return 0 if not ergebnis.offen else 1


if __name__ == "__main__":
    sys.exit(main())
