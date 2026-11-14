#!/usr/bin/env python3
# ============================================================
#  FRISTEN-CHECK (Recht) – kostenloses Erinnerungssystem mit
#  Issue-Eskalation für FranksFinanzcheck
#
#  Datenquelle:  data/recht-fristen.yaml   (Fristen-Kalender, redaktionell)
#  Zustand:      data/fristen_state.json   (Erledigungen, Issue-Nummern,
#                                           bereits gesendete Eskalationen)
#  Report:       FRISTEN-REPORT.md         (wird bei jedem Lauf neu erzeugt)
#  Workflow:     .github/workflows/fristen-check.yml (täglich 07:55 MESZ)
#
#  WAS DAS SKRIPT TUT (jeder Lauf):
#    1. Fristen auswerten:
#         - OK          → noch lange hin (grün)
#         - ERINNERUNG  → Fälligkeit naht (gelb) → grünes Issue `frist`
#         - FÄLLIG      → Stichtag erreicht      → Eskalation Stufe 1
#         - ÜBERFÄLLIG  → Stichtag vorbei        → Eskalation nach 14/30 Tagen
#         - ABGESCHLOSSEN (einmalige Frist, erledigt)
#    2. Sofort-Prüfungen (unabhängig vom Kalender, täglich):
#         - Veraltungs-Scan: alte Rechtsbegriffe im Live-Content
#           (TMG, TTDSG, OS-Plattform, ODR-Link, Privacy Shield, Safe Harbor)
#           → Fund = hartes Issue `frist-eskalation`
#         - Stand-Alter: "Stand: <Datum>" in Impressum & Datenschutz
#           älter als 12 Monate → Erinnerungs-Issue
#    3. Issue-Eskalation (dedupliziert, stufenweise):
#         Stufe 0: Erinnerungs-Issue (Label `frist`)
#         Stufe 1: Kommentar "🚨 Eskalation" am Stichtag + Label `frist-eskalation`
#         Stufe 2: Kommentar nach +14 Tagen
#         Stufe 3: Kommentar nach +30 Tagen (letzte Mahnung)
#       Jede Stufe wird genau EINMAL gesendet (state file).
#    4. Erledigte Fristen: Issue schließen; bei #1028 ausschließlich nach
#       Belegen, Gegenproben, State-Push und separatem Readback-Job.
#
#  ERLEDIGT MARKIEREN (Frist neu terminieren):
#      python3 scripts/fristen_check.py --done <frist-id>[,<id2>,...]
#      oder im GitHub-UI: Actions → "Fristen-Check (Recht)" →
#      Run workflow → Eingabefeld "erledigt".
#      (Wiederkehrende Fristen = letztes Erledigungsdatum + Intervall,
#       einmalige Fristen = dauerhaft abgeschlossen.)
#
#  HINWEIS: Ein einfach geschlossenes Issue OHNE --done gilt NICHT
#  als erledigt – der Fristen-Bot legt die Erinnerung beim nächsten
#  Lauf erneut an (gewolltes Nachfassen). Immer --done nutzen.
#
#  Exit-Codes: 0 = Lauf ok (auch bei überfälligen Fristen – die
#  Eskalation läuft über eigene Issues, nicht über rote Runs).
#  2 = Konfigurations-/Systemfehler; 3 = geschützte KI-Freigabe/Überwachung
#  oder Issue-Zuordnung unbestätigt (andere Fristen separat sichern).
# ============================================================

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import tempfile
import sys
from pathlib import Path

try:
    from . import ki_frist_freigabe as ki_freigabe
except ImportError:  # direkter Aufruf als Skript
    import ki_frist_freigabe as ki_freigabe

REPO = Path(__file__).resolve().parent.parent
YAML_PATH = REPO / "data" / "recht-fristen.yaml"
STATE_PATH = REPO / "data" / "fristen_state.json"
REPORT_PATH = REPO / "FRISTEN-REPORT.md"

SCAN_DIRS = ["content", "layouts", "static"]  # Live-Texte (nicht _archiv/Reports)
SCAN_PATTERNS = [
    (r"\bTTDSG\b", "TTDSG (seit 14.05.2024: TDDDG)"),
    (r"\bTMG\b", "TMG (seit 14.05.2024: DDG)"),
    (r"OS-Plattform", "OS-Plattform-Hinweis (Pflicht entfallen seit 20.07.2025)"),
    (r"ec\.europa\.eu/consumers/odr", "Link zur abgeschalteten EU-OS-Plattform"),
    (r"Privacy-?Shield", "Privacy Shield (ersetzt durch EU-US Data Privacy Framework)"),
    (r"\bSafe Harbor\b", "Safe Harbor (seit 2015 gekippt)"),
]
SCAN_EXCLUDE_SUBSTR = ["_archiv", "patches/"]  # Historische Doku bewusst ausnehmen

STAND_DATEIEN = [
    ("content/impressum/index.md", "Impressum"),
    ("content/datenschutz/index.md", "Datenschutzerklärung"),
]
STAND_MAX_ALTER_TAGE = 365

MONATE = {
    "januar": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4, "mai": 5,
    "juni": 6, "juli": 7, "august": 8, "september": 9, "oktober": 10,
    "november": 11, "dezember": 12,
}

LABEL_FRIST = "frist"
LABEL_ESKALATION = "frist-eskalation"


# ------------------------------------------------------------
#  Hilfsfunktionen
# ------------------------------------------------------------
def heute(now_arg: str | None) -> dt.date:
    if now_arg:
        return dt.date.fromisoformat(now_arg)
    return dt.date.today()


def lade_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"⚠️  State-Datei defekt ({e}) – starte neu. "
                  f"(Vorherige Eskalations-Marker gehen verloren.)")
    return {}


def schreibe_state(state: dict, dry_run: bool) -> None:
    if dry_run:
        print("   (dry-run: State wird NICHT geschrieben)")
        return
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def lade_fristen() -> list[dict]:
    try:
        import yaml
    except ImportError:
        sys.exit("❌ PyYAML fehlt. Installation: python3 -m pip install pyyaml")
    with open(YAML_PATH, encoding="utf-8") as f:
        daten = yaml.safe_load(f) or {}
    fristen = daten.get("fristen") or []
    if not fristen:
        sys.exit(f"❌ Keine Fristen in {YAML_PATH} gefunden.")
    ids = [f.get("id") for f in fristen]
    duplikate = {i for i in ids if ids.count(i) > 1}
    if duplikate:
        sys.exit(f"❌ Doppelte Frist-IDs in recht-fristen.yaml: {sorted(duplikate)}")
    if ki_freigabe.FRIST_ID not in ids:
        # Löschen aus der Konfiguration darf die laufende Frist nicht
        # unsichtbar machen – die übrigen Fristen laufen trotzdem weiter.
        print("::warning title=KI-Fristkonfiguration fehlt::Frist bleibt offen; recht-fristen.yaml wiederherstellen")
        fristen.append({
            "id": ki_freigabe.FRIST_ID,
            "titel": ki_freigabe.FRIST_TITEL,
            "kategorie": "KI-Verordnung", "faellig_am": ki_freigabe.FRIST_DATUM,
            "einmalig": True, "erinnerung_ab_tage": 30,
            "beschreibung": "KI-Fristkonfiguration fehlt; Wiederherstellung und Belege nach docs/KI-TRANSPARENZ-ABNAHME.md §5 prüfen.",
            "checkliste": ["KI-Fristkonfiguration und offene Nachweise fachkundig prüfen"],
            "_konfiguration_fehlt": True,
        })
    return fristen


def ki_frist_konform(frist: dict) -> bool:
    erinnerung = frist.get("erinnerung_ab_tage", 30)
    eskalation = frist.get("eskalation_nach_tagen", [0, 14, 30])
    return (not frist.get("_konfiguration_fehlt") and frist.get("einmalig") is True
            and frist.get("titel") == ki_freigabe.FRIST_TITEL
            and str(frist.get("faellig_am")) == ki_freigabe.FRIST_DATUM
            and not frist.get("intervall_tage") and type(erinnerung) is int and erinnerung >= 30
            and isinstance(eskalation, list) and all(type(x) is int for x in eskalation)
            and {0, 14, 30}.issubset(eskalation))


def frist_due(frist: dict, state: dict) -> dt.date:
    """Fälligkeit: bei Intervall-Fristen zählt das LETZTE Erledigungsdatum
    aus dem State (falls jünger als die konfigurierte Fälligkeit)."""
    due = dt.date.fromisoformat(str(frist["faellig_am"]))
    intervall = frist.get("intervall_tage")
    if intervall:
        erledigt = (state.get(frist["id"]) or {}).get("last_done")
        if erledigt:
            neu = dt.date.fromisoformat(erledigt) + dt.timedelta(days=int(intervall))
            due = max(due, neu)
    return due


# ------------------------------------------------------------
#  GitHub-Issues (via gh CLI; ohne Token/gh → nur berichten)
# ------------------------------------------------------------
class Issues:
    def __init__(self, aktiv: bool):
        self.aktiv = aktiv and bool(os.environ.get("GH_TOKEN")) \
            and shutil_which("gh") is not None
        self.repo = os.environ.get("GITHUB_REPOSITORY", "")
        if aktiv and not self.aktiv:
            print("ℹ️  Issue-Eskalation deaktiviert (kein gh/GH_TOKEN) – nur Report.")

    def _run(self, *args: str) -> str | None:
        cmd = ["gh", *args]
        if self.repo:
            cmd += ["--repo", self.repo]
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if out.returncode != 0:
                print(f"   ⚠️  gh-Fehler: {' '.join(args)} → {out.stderr.strip()[:200]}")
                return None
            return out.stdout.strip()
        except Exception as e:  # Netzwerk/Timeout soll den Lauf nicht killen
            print(f"   ⚠️  gh nicht ausführbar ({e}) – übersprungen.")
            return None

    def _ensure_label(self, name: str, farbe: str, beschreibung: str) -> None:
        self._run("label", "create", name, "--color", farbe,
                  "--description", beschreibung)

    def offene_issues(self) -> list[dict]:
        out = self._run("issue", "list", "--state", "open", "--limit", "300",
                        "--json", "number,title")
        if not out:
            return []
        try:
            return json.loads(out)
        except json.JSONDecodeError:
            return []

    def erstellen(self, titel: str, body: str, labels: list[str]) -> int | None:
        for lab, farbe, beschr in [
            (LABEL_FRIST, "0e8a16", "Fristenerinnerung (Fristen-Check)"),
            (LABEL_ESKALATION, "d73a4a", "Frist überfällig – Eskalation"),
        ]:
            if lab in labels:
                self._ensure_label(lab, farbe, beschr)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", prefix="fristen_issue_", encoding="utf-8", delete=False
        ) as fh:
            fh.write(body)
            tmp_pfad = Path(fh.name)
        try:
            out = self._run("issue", "create", "--title", titel,
                            "--body-file", str(tmp_pfad), "--label", ",".join(labels))
        finally:
            tmp_pfad.unlink(missing_ok=True)
        # gh gibt die Issue-URL zurück → Nummer extrahieren
        if out and "/issues/" in out:
            try:
                return int(out.rstrip("/").rsplit("/", 1)[-1])
            except ValueError:
                return None
        return None

    def kommentieren(self, nummer: int, body: str) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", prefix="fristen_comment_", encoding="utf-8", delete=False
        ) as fh:
            fh.write(body)
            tmp_pfad = Path(fh.name)
        try:
            self._run("issue", "comment", str(nummer), "--body-file", str(tmp_pfad))
        finally:
            tmp_pfad.unlink(missing_ok=True)

    def label_setzen(self, nummer: int, label: str) -> None:
        self._run("issue", "edit", str(nummer), "--add-label", label)

    def schliessen(self, nummer: int, kommentar: str) -> bool:
        return self._run("issue", "close", str(nummer), "--reason", "completed",
                         "--comment", kommentar) is not None

    def wieder_oeffnen(self, nummer: int, kommentar: str) -> bool:
        return self._run("issue", "reopen", str(nummer), "--comment", kommentar) is not None


def ki_quittung_ist_aktuell(quittung) -> bool:
    return (isinstance(quittung, dict)
            and str(quittung.get("workflow_run_id")) == os.environ.get("GITHUB_RUN_ID")
            and str(quittung.get("workflow_attempt")) == os.environ.get("GITHUB_RUN_ATTEMPT")
            and quittung.get("workflow_sha") == os.environ.get("GITHUB_SHA"))


def fremdes_issue_erlaubt(nummer) -> bool:
    """Andere Fristen dürfen #1028 auch bei beschädigtem State nie verändern.

    Nur positive, echte JSON-Integer sind gültige Issue-Nummern; insbesondere
    URL- und String-Aliase dürften nicht am Schutz vorbeigereicht werden.
    """
    return type(nummer) is int and nummer > 0 and nummer != ki_freigabe.FRIST_ISSUE


def ki_issue_lesen(issues: Issues, fstate: dict, *, zuordnen: bool = False) -> dict:
    """Nur das identifizierte #1028 im vorgesehenen Repository anfassen."""
    nummer = fstate.get("issue")
    if nummer is None and zuordnen:
        nummer = ki_freigabe.FRIST_ISSUE
    if (not isinstance(issues.repo, str) or issues.repo.lower() != ki_freigabe.REPOSITORY
            or type(nummer) is not int or nummer != ki_freigabe.FRIST_ISSUE):
        raise ki_freigabe.FreigabeFehler("KI-Frist ist nicht eindeutig Issue #1028 im vorgesehenen Repository zugeordnet")
    ausgabe = issues._run("issue", "view", str(nummer), "--json", "number,title,state")
    try:
        issue = json.loads(ausgabe or "")
    except (TypeError, json.JSONDecodeError) as exc:
        raise ki_freigabe.FreigabeFehler("Issue #1028 ist nicht messbar") from exc
    if (not isinstance(issue, dict) or type(issue.get("number")) is not int or issue["number"] != nummer
            or issue.get("title") != f"⏰ Frist: {ki_freigabe.FRIST_TITEL}"
            or issue.get("state") not in ("OPEN", "CLOSED")):
        raise ki_freigabe.FreigabeFehler("Identität oder Zustand von Issue #1028 widerspricht dem Fristenvertrag")
    return issue


def shutil_which(prog: str) -> str | None:
    from shutil import which
    return which(prog)


# ------------------------------------------------------------
#  Fristen-Auswertung
# ------------------------------------------------------------
def bewerte_fristen(fristen: list[dict], state: dict, heute_d: dt.date,
                    issues: Issues, dry_run: bool) -> list[dict]:
    ergebnisse = []
    offene = issues.offene_issues() if issues.aktiv and not dry_run else []
    titel_map = {i["title"].strip(): i["number"] for i in offene if i.get("title")}

    for frist in fristen:
        fid = frist["id"]
        fstate = state.get(fid) or {}
        einmalig = bool(frist.get("einmalig"))
        erledigt_am = fstate.get("erledigt_am")
        ki_konfig_fehlt = fid == ki_freigabe.FRIST_ID and not ki_frist_konform(frist)
        ki_schutz_fehler = ""
        ki_issue_pruefung_gescheitert = False
        if ki_konfig_fehlt:
            # Eine beschädigte Erinnerungskonfiguration darf nicht ihrerseits
            # die Eskalation verzögern oder die übrigen Fristen abstürzen lassen.
            frist = dict(frist, titel=ki_freigabe.FRIST_TITEL,
                         erinnerung_ab_tage=30, eskalation_nach_tagen=[0, 14, 30])
        if fid == ki_freigabe.FRIST_ID:
            # Ein nicht messbarer historischer Abschluss wird aus den aktiven
            # Statusfeldern in Quarantäne verschoben. So ist auch ein direkter
            # State-Leser nicht versehentlich grün. Bei vorübergehendem API-
            # Ausfall darf die identische Quittung nach vollständiger erneuter
            # Prüfung wiederhergestellt werden; Issue-Close bleibt immer manuell.
            alt = fstate.get("ki_abschluss_unbestaetigt")
            kandidat = dict(fstate)
            if not erledigt_am and isinstance(alt, dict):
                kandidat.update(alt)
                kandidat.pop("ki_abschluss_unbestaetigt", None)
                erledigt_am = kandidat.get("erledigt_am")
            fehler = []
            if ki_konfig_fehlt:
                fehler = [f"Konfiguration beschädigt; maßgebliche Frist bleibt {ki_freigabe.FRIST_DATUM}"]
            elif erledigt_am:
                fehler = ki_freigabe.quittung_pruefen(REPO, issues.repo, heute_d, kandidat)
            if fehler:
                ki_schutz_fehler = "; ".join(fehler)
                print(f"::warning title=KI-Frist nicht abgeschlossen::{ki_schutz_fehler}")
                if not dry_run and fstate.get("erledigt_am"):
                    fstate["ki_abschluss_unbestaetigt"] = {
                        k: fstate.pop(k) for k in ("erledigt_am", "last_done", "ki_abschluss") if k in fstate}
                    state[fid] = fstate
                erledigt_am = None
            elif erledigt_am and isinstance(alt, dict):
                if not dry_run:
                    state[fid] = kandidat
                    fstate = kandidat
        if einmalig and erledigt_am and fid == ki_freigabe.FRIST_ID and issues.aktiv and not dry_run:
            # Eine gültige historische Quittung belegt nicht, dass das Issue
            # weiterhin geschlossen ist. Eine Wiedereröffnung wird respektiert:
            # Abschlussfelder in Quarantäne, keine automatische Neuschließung.
            try:
                issue = ki_issue_lesen(issues, fstate, zuordnen=True)
                if issue["state"] != "CLOSED":
                    raise ki_freigabe.FreigabeFehler(
                        "Issue #1028 ist trotz Abschlussquittung offen; Betreiberprüfung und neuer vollständiger Abschluss erforderlich")
                fstate["issue"] = ki_freigabe.FRIST_ISSUE
                state[fid] = fstate
            except ki_freigabe.FreigabeFehler as exc:
                ki_schutz_fehler = str(exc)
                ki_issue_pruefung_gescheitert = True
                print(f"::error title=KI-Abschluss nicht bestätigt::{ki_schutz_fehler}")
                fstate["ki_abschluss_unbestaetigt"] = {
                    k: fstate.pop(k) for k in ("erledigt_am", "last_done", "ki_abschluss") if k in fstate}
                state[fid] = fstate
                erledigt_am = None

        if einmalig and erledigt_am:
            ergebnis = {"frist": frist, "status": "abgeschlossen",
                        "due": frist_due(frist, state), "tage": None}
            ergebnisse.append(ergebnis)
            # Die KI-Frist darf NIE aus einem gespeicherten Flag heraus schließen.
            # Sie hat einen separaten manuellen Abschluss nach Tests und State-Push.
            if fid != ki_freigabe.FRIST_ID:
                num = fstate.get("issue")
                if num is None:
                    num = titel_map.get(f"⏰ Frist: {frist['titel']}")
                if num is not None and issues.aktiv and not dry_run:
                    if not fremdes_issue_erlaubt(num):
                        ergebnis["ki_schutz_fehler"] = f"Issue-Zuordnung für {fid} ist ungültig oder verweist auf #1028"
                        print(f"::error title=Issue-Zuordnung beschädigt::{ergebnis['ki_schutz_fehler']}")
                    elif issues.schliessen(
                            num, f"✅ Frist **{fid}** wurde am {erledigt_am} als erledigt "
                                 f"markiert (`--done`) – Issue automatisch geschlossen."):
                        fstate.pop("issue", None)
            continue

        due = (dt.date.fromisoformat(ki_freigabe.FRIST_DATUM) if ki_konfig_fehlt
               else frist_due(frist, state))
        tage = (due - heute_d).days
        erinnerung_ab = int(frist.get("erinnerung_ab_tage", 21))
        eskalation_nach = frist.get("eskalation_nach_tagen") or [0, 14, 30]
        ist_erinnerung = 0 < tage <= erinnerung_ab
        ist_ueberfaellig = tage < 0

        status = ("überfällig" if ist_ueberfaellig else
                  "fällig" if tage == 0 else
                  "Erinnerung" if ist_erinnerung else "OK")
        ergebnis = {"frist": frist, "status": status, "due": due, "tage": tage}
        if ki_schutz_fehler:
            ergebnis["ki_schutz_fehler"] = ki_schutz_fehler
        ergebnisse.append(ergebnis)

        if fid == ki_freigabe.FRIST_ID and issues.aktiv and not dry_run:
            # Bei einem fehlgeschlagenen Abschluss-/Issue-Readback keine
            # zweite, möglicherweise widersprüchliche Aktion im selben Lauf.
            # Bei beschädigtem Kalender bleibt die Issue-Eskalation dagegen
            # aktiv – der Ersatzkalender soll nicht bloß im Report stehen.
            if ki_issue_pruefung_gescheitert:
                continue
            try:
                issue = ki_issue_lesen(issues, fstate, zuordnen=True)
                if issue["state"] == "CLOSED":
                    pending = fstate.get("ki_abschluss_vorgemerkt")
                    im_lauf = isinstance(pending, dict) and ki_quittung_ist_aktuell(pending.get("quittung"))
                    unklar = (fstate.get("ki_abschluss_unbestaetigt") or fstate.get("ki_abschluss")
                              or (pending and not im_lauf))
                    if unklar:
                        # Ein Close könnte vor einem Workflow-/API-Abbruch noch
                        # erfolgreich gewesen sein. Nicht blind wieder öffnen,
                        # sondern laut melden und den Betreiber prüfen lassen.
                        raise ki_freigabe.FreigabeFehler("Issue #1028 ist geschlossen, Abschluss jedoch nicht bestätigt")
                    if not im_lauf:
                        if not issues.wieder_oeffnen(
                                ki_freigabe.FRIST_ISSUE,
                                "Die KI-Frist ist noch nicht nach dem dokumentierten Nachweisverfahren "
                                "abgeschlossen. Bitte Anbieter-, Bild-, Register- und Live-Nachweise "
                                "sowie Betreiberfreigabe nach docs/KI-TRANSPARENZ-ABNAHME.md §5 prüfen."):
                            raise ki_freigabe.FreigabeFehler("Vorzeitig geschlossenes Issue #1028 konnte nicht geöffnet werden")
                        if ki_issue_lesen(issues, fstate, zuordnen=True)["state"] != "OPEN":
                            raise ki_freigabe.FreigabeFehler("Wiederöffnung von Issue #1028 nicht bestätigt")
                        print("   ↩️  Issue #1028 war ohne bestätigten Abschluss geschlossen und wurde wieder geöffnet.")
                fstate["issue"] = ki_freigabe.FRIST_ISSUE
                state[fid] = fstate
            except ki_freigabe.FreigabeFehler as exc:
                print(f"::error title=KI-Issue-Überwachung unbestätigt::{exc}")
                ergebnis["ki_schutz_fehler"] = str(exc)
                state[fid] = fstate
                # Niemals ersatzweise ein anderes Issue erstellen, kommentieren
                # oder schließen, wenn Identität/Zustand nicht messbar sind.
                continue

        if status == "OK" or dry_run or not issues.aktiv:
            continue

        titel = f"⏰ Frist: {frist['titel']}"
        num = fstate.get("issue")
        if num is None:
            num = titel_map.get(titel)
        if fid != ki_freigabe.FRIST_ID and num is not None and not fremdes_issue_erlaubt(num):
            ergebnis["ki_schutz_fehler"] = f"Issue-Zuordnung für {fid} ist ungültig oder verweist auf #1028"
            print(f"::error title=Issue-Zuordnung beschädigt::{ergebnis['ki_schutz_fehler']}")
            continue

        # --- Stufe 0: Erinnerungs-Issue anlegen -------------------
        if num is None:
            checkliste = "\n".join(
                f"- [ ] {punkt}" for punkt in frist.get("checkliste", []))
            abschluss_hinweis = (
                "**Erledigt?** Erst Anbieter-, Bild- und Register-Nachweise, "
                "Live-Abnahme und Betreiberfreigabe dokumentieren. Der Abschluss "
                "erfordert den manuellen Fristen-Workflow auf main und die "
                "Nachweisprüfung in `docs/KI-TRANSPARENZ-ABNAHME.md` §5."
                if fid == ki_freigabe.FRIST_ID else
                "**Erledigt?** Nicht nur schließen, sondern *Actions → „Fristen-Check "
                f"(Recht)\" → Run workflow → `erledigt={fid}`* eingeben* – nur dann wird "
                "die Frist neu terminiert und dieses Issue automatisch geschlossen."
            )
            body = "\n".join([
                f"**Frist-ID:** `{fid}` · **Kategorie:** {frist.get('kategorie', '–')}"
                + (" · **Gewicht:** Empfehlung" if frist.get("gewicht") == "empfohlen" else ""),
                "",
                f"**Fällig am:** {due.isoformat()} "
                f"(in {tage} Tag{'en' if abs(tage) != 1 else ''})" if tage >= 0
                else f"**Fällig am:** {due.isoformat()} (**{abs(tage)} Tage überfällig!**)",
                "",
                str(frist.get("beschreibung", "")).strip(),
                "",
                "### Was zu tun ist",
                checkliste or "- [ ] Frist prüfen",
                "",
                "### Eskalationsplan",
                f"- Erinnerung: {erinnerung_ab} Tage vor Fälligkeit (dieses Issue)",
                f"- 🚨 Eskalation: am Stichtag, nach 14 und nach 30 Tagen (Kommentar)",
                "",
                "---",
                abschluss_hinweis,
                "*Automatisch erstellt vom Fristen-Check (Recht).*",
            ])
            num = issues.erstellen(titel, body, [LABEL_FRIST])
            if fid != ki_freigabe.FRIST_ID and num is not None and not fremdes_issue_erlaubt(num):
                ergebnis["ki_schutz_fehler"] = f"Neues Issue für {fid} ist ungültig oder verweist auf #1028"
                print(f"::error title=Issue-Zuordnung beschädigt::{ergebnis['ki_schutz_fehler']}")
                continue
            if num:
                fstate["issue"] = num
                print(f"   📌 Issue #{num} erstellt: {titel}")

        # --- Stufen 1..n: Eskalations-Kommentare ------------------
        if num and ist_ueberfaellig or num and tage == 0:
            tage_danach = max(0, -tage)
            bereits = fstate.get("eskaliert", [])
            for stufe_delta in sorted(int(x) for x in eskalation_nach):
                if tage_danach >= stufe_delta and stufe_delta not in bereits:
                    level = (f"🚨 **ESKALATION – Frist überfällig "
                             f"({tage_danach} Tage)**")
                    kommentar = "\n".join([
                        level,
                        "",
                        f"Die Frist **{fid}** ({frist['titel']}) wäre am "
                        f"{due.isoformat()} fällig gewesen und ist **nicht als "
                        "erledigt markiert**.",
                        "",
                        ("- Vor Abschluss die Nachweise und die ausdrückliche "
                         "Betreiberfreigabe nach `docs/KI-TRANSPARENZ-ABNAHME.md` §5 prüfen."
                         if fid == ki_freigabe.FRIST_ID else
                         "- Bitte PRÜFEN und dann `erledigt="
                         f"{fid}` im Workflow „Fristen-Check (Recht)\" setzen."),
                        ("- Bei neuer Rechtslage Kalender und Schutzvertrag bewusst gemeinsam prüfen."
                         if fid == ki_freigabe.FRIST_ID else
                         "- Oder Frist bewusst neu terminieren (data/recht-fristen.yaml)."),
                        "",
                        f"*Eskalationsstufe +{stufe_delta} Tage · "
                        "Automatisch erstellt vom Fristen-Check.*",
                    ])
                    issues.kommentieren(num, kommentar)
                    issues.label_setzen(num, LABEL_ESKALATION)
                    bereits.append(stufe_delta)
                    fstate["eskaliert"] = bereits
                    print(f"   🚨 Eskalation (+{stufe_delta} d) in #{num}: {fid}")

        state[fid] = fstate

    return ergebnisse


def markiere_erledigt(ids: list[str], fristen: list[dict], state: dict,
                      heute_d: dt.date, issues: Issues, dry_run: bool = False,
                      nur_simulation: bool = False) -> bool:
    """True signalisiert eine verweigerte KI-Freigabe oder unklare Issue-Zuordnung."""
    bekannt = {f["id"]: f for f in fristen}
    ki_verweigert = False
    for fid in ids:
        fid = fid.strip()
        if not fid:
            continue
        frist = bekannt.get(fid)
        if not frist:
            print(f"⚠️  Unbekannte Frist-ID „{fid}\" – verfügbar: "
                  f"{', '.join(bekannt)}")
            continue
        quittung = None
        if fid == ki_freigabe.FRIST_ID:
            fehler = ki_freigabe.pruefen(REPO, issues.repo, heute_d)
            if not ki_frist_konform(frist):
                fehler.append(f"KI-Fristkonfiguration muss Titel, Datum {ki_freigabe.FRIST_DATUM}, "
                               "Einmaligkeit, Erinnerung und Eskalation erhalten")
            if not dry_run:
                if nur_simulation:
                    fehler.append("Simuliertes Datum oder --scan-only sind kein echter Abschlusslauf")
                if not issues.aktiv:
                    fehler.append("GitHub-Issue-Zugang ist für den Abschluss erforderlich")
                try:
                    quittung = ki_freigabe.quittung_erstellen(REPO, heute=heute_d)
                except ki_freigabe.FreigabeFehler as exc:
                    fehler.append(str(exc))
            if fehler:
                print(f"::error title=KI-Frist bleibt offen::{'; '.join(fehler)}")
                ki_verweigert = True
                continue
            if dry_run:
                print("   (dry-run: KI-Belege formal geprüft; keine Freigabe und kein Issue-Close)")
                continue
        fstate = state.get(fid) or {}
        if quittung is not None:
            # Nur beantragt: Vor den unabhängigen Tests und dem zweiten
            # State-Push darf KEIN Erledigt-Flag auf main erscheinen.
            fstate.pop("last_done", None)
            fstate.pop("erledigt_am", None)
            fstate.pop("ki_abschluss", None)
            fstate.pop("ki_abschluss_unbestaetigt", None)
            fstate["ki_abschluss_vorgemerkt"] = {
                "datum": heute_d.isoformat(), "quittung": quittung}
        else:
            fstate["last_done"] = heute_d.isoformat()
            if frist.get("einmalig"):
                fstate["erledigt_am"] = heute_d.isoformat()
            fstate.pop("eskaliert", None)
        num = fstate.get("issue")
        # KI-Close ausschließlich im nachgelagerten Job, NACH State-Push und
        # Gegenproben. Eine fremde Frist darf auch bei defektem State niemals
        # #1028 oder einen mehrdeutigen URL-/String-Alias schließen.
        if num is not None and issues.aktiv and not dry_run and fid != ki_freigabe.FRIST_ID:
            if not fremdes_issue_erlaubt(num):
                print(f"::error title=Issue-Zuordnung beschädigt::{fid}: ungültige Nummer oder Verweis auf #1028")
                ki_verweigert = True
            else:
                neu = ("" if frist.get("einmalig") else
                       f" Nächster Termin: "
                       f"{(heute_d + dt.timedelta(days=int(frist.get('intervall_tage', 0)))).isoformat()}.")
                if issues.schliessen(num, f"✅ Frist **{fid}** als erledigt markiert "
                                    f"({heute_d.isoformat()}).{neu}"):
                    fstate.pop("issue", None)
        state[fid] = fstate
        if quittung is not None:
            print(f"   ⏳ {fid}: Abschluss beantragt; Tests und zweiter State-Push stehen noch aus.")
        else:
            print(f"   ✅ {fid}: erledigt am {heute_d.isoformat()}" +
                  (" (einmalig → abgeschlossen)" if frist.get("einmalig") else ""))
    return ki_verweigert


def bereite_ki_frist_vor(state: dict, issues: Issues, heute_d: dt.date) -> int:
    """Nach bestandenen Gegenproben die vorgemerkte Freigabe erneut prüfen."""
    try:
        if not issues.aktiv or os.environ.get("GITHUB_JOB") != "ki-freigabe":
            raise ki_freigabe.FreigabeFehler("Vorbereitung nur im nachgelagerten KI-Freigabe-Job")
        ki_freigabe.dispatcher_pruefen(REPO)
        fstate = state.get(ki_freigabe.FRIST_ID)
        vorgemerkt = fstate.get("ki_abschluss_vorgemerkt") if isinstance(fstate, dict) else None
        if not isinstance(vorgemerkt, dict):
            raise ki_freigabe.FreigabeFehler("Keine vorgemerkte KI-Freigabe")
        if not ki_quittung_ist_aktuell(vorgemerkt.get("quittung")):
            raise ki_freigabe.FreigabeFehler("Vormerkung stammt nicht aus diesem Workflow-Versuch")
        # Nicht erst nach dem zweiten Push feststellen, dass das Ziel-Issue
        # fehlt oder der State auf ein anderes Issue zeigt.
        ki_issue_lesen(issues, fstate)
        datum = vorgemerkt.get("datum")
        ki_freigabe._datum(datum, "vorgemerkter Abschluss", heute_d)
        neu = dict(fstate, erledigt_am=datum, last_done=datum,
                   ki_abschluss=vorgemerkt.get("quittung"))
        fehler = ki_freigabe.quittung_pruefen(REPO, issues.repo, heute_d, neu)
        if fehler:
            raise ki_freigabe.FreigabeFehler("; ".join(fehler))
        ki_freigabe.remote_state_pruefen(REPO, issues.repo, fstate, heute=heute_d)
        neu.pop("ki_abschluss_vorgemerkt", None)
        neu.pop("eskaliert", None)
        state[ki_freigabe.FRIST_ID] = neu
        schreibe_state(state, False)
        print("✅ KI-Abschluss vorbereitet; vor Issue-Close muss dieser State gepusht werden.")
        return 0
    except (ki_freigabe.FreigabeFehler, OSError, ValueError, TypeError) as exc:
        print(f"::error title=KI-Frist bleibt offen::{exc}")
        return 2


def schliesse_ki_frist(fristen: list[dict], state: dict, issues: Issues,
                        heute_d: dt.date) -> int:
    """Zweiter Workflow-Job: niemals vor Commit/Push und erfolgreichem Testjob."""
    try:
        if not issues.aktiv or os.environ.get("GITHUB_JOB") != "ki-freigabe":
            raise ki_freigabe.FreigabeFehler("Issue-Close nur im nachgelagerten KI-Freigabe-Job")
        ki_freigabe.dispatcher_pruefen(REPO)
        fstate = state.get(ki_freigabe.FRIST_ID)
        if not isinstance(fstate, dict) or not fstate.get("erledigt_am"):
            raise ki_freigabe.FreigabeFehler("Keine vorbereitete KI-Freigabe")
        if not ki_quittung_ist_aktuell(fstate.get("ki_abschluss")):
            raise ki_freigabe.FreigabeFehler("KI-Abschluss stammt nicht aus diesem Workflow-Versuch")
        fehler = ki_freigabe.quittung_pruefen(REPO, issues.repo, heute_d, fstate)
        if fehler:
            raise ki_freigabe.FreigabeFehler("; ".join(fehler))
        sha, deployment_id = ki_freigabe.remote_state_pruefen(REPO, issues.repo, fstate, heute=heute_d)
        frist = next((f for f in fristen if f.get("id") == ki_freigabe.FRIST_ID), None)
        if not frist or not ki_frist_konform(frist):
            raise ki_freigabe.FreigabeFehler("KI-Fristkonfiguration fehlt oder ist beschädigt")
        issue = ki_issue_lesen(issues, fstate)
        nummer = issue["number"]
        # Der Readback oben ist nicht atomar mit dem Close. Nach dem Issue-Read
        # nochmals main und laufende Deploys prüfen und erst dann schließen.
        ki_freigabe.letzte_freigabe_pruefen(issues.repo, sha, deployment_id)
        if issue["state"] == "CLOSED":
            print(f"ℹ️  KI-Fristen-Issue #{nummer} ist bereits geschlossen; kein erneuter Close.")
            return 0
        if not issues.schliessen(
                nummer, "✅ KI-Frist nach dokumentierten Nachweisen, Live-Abnahme und "
                        "ausdrücklicher Betreiberfreigabe im Fristen-Workflow abgeschlossen. "
                        "Die formale Prüfung ersetzt keine fachliche Bewertung."):
            raise ki_freigabe.FreigabeFehler("GitHub-Issue konnte nicht geschlossen werden")
        if ki_issue_lesen(issues, fstate)["state"] != "CLOSED":
            raise ki_freigabe.FreigabeFehler("GitHub bestätigt den Issue-Close nicht")
        print(f"✅ KI-Fristen-Issue #{nummer} nach State- und Issue-Readback geschlossen.")
        return 0
    except (ki_freigabe.FreigabeFehler, OSError, ValueError, TypeError) as exc:
        print(f"::error title=KI-Issue bleibt offen::{exc}")
        return 2


# ------------------------------------------------------------
#  Sofort-Prüfungen: Veraltungs-Scan + Stand-Alter
# ------------------------------------------------------------
def veraltungs_scan() -> list[tuple[str, str, str]]:
    funde = []
    for verz in SCAN_DIRS:
        basis = REPO / verz
        if not basis.exists():
            continue
        for pfad in sorted(basis.rglob("*")):
            if not pfad.is_file() or pfad.suffix.lower() not in {
                    ".md", ".html", ".xml", ".txt", ".toml", ".yaml", ".yml", ".js"}:
                continue
            rel = pfad.relative_to(REPO).as_posix()
            if any(ausschluss in rel for ausschluss in SCAN_EXCLUDE_SUBSTR):
                continue
            try:
                text = pfad.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for regex, grund in SCAN_PATTERNS:
                if re.search(regex, text):
                    funde.append((rel, regex, grund))
    return funde


def stand_datum_parsen(text: str) -> dt.date | None:
    # Formate: "Stand: August 2026", "Stand: 30. August 2026", "Stand: 2026-08-30"
    m = re.search(r"Stand:\s*(\d{4}-\d{2}-\d{2})", text)
    if m:
        return dt.date.fromisoformat(m.group(1))
    m = re.search(
        r"Stand:\s*(?:(\d{1,2})\.\s*)?([A-Za-zÄÖÜäöü]+)\s+(\d{4})", text)
    if m:
        monat = MONATE.get(m.group(2).lower())
        if monat:
            tag = int(m.group(1)) if m.group(1) else 1
            return dt.date(int(m.group(3)), monat, min(tag, 28))
    return None


# ------------------------------------------------------------
#  Report
# ------------------------------------------------------------
def schreibe_report(ergebnisse, scan_funde, stand_ergebnisse, heute_d, state):
    ki_abgeschlossen = any(e["frist"].get("id") == ki_freigabe.FRIST_ID
                           and e["status"] == "abgeschlossen" for e in ergebnisse)
    emoji = {"OK": "🟢", "Erinnerung": "🟡", "fällig": "🟠",
             "überfällig": "🔴", "abgeschlossen": "✅"}
    zeilen = [
        "# ⏰ FRISTEN-REPORT – Recht & Compliance",
        "",
        f"**Stand:** {heute_d.isoformat()} · **Generator:** `scripts/fristen_check.py` "
        "(läuft täglich 07:55 MESZ via `.github/workflows/fristen-check.yml`)",
        "",
        "> Kostenloses Erinnerungssystem für Rechtspflichten: Fristen aus "
        "`data/recht-fristen.yaml`, Eskalation über GitHub-Issues "
        "(`frist` → `frist-eskalation`). Erledigen = Workflow „Fristen-Check "
        "(Recht)“ starten mit `erledigt=<Frist-ID>`.",
        "",
        "## Fristen-Kalender",
        "",
        "| Status | Frist | Fällig am | Tage | Kategorie |",
        "|---|---|---|---|---|",
    ]
    for e in sorted(ergebnisse, key=lambda x: (x["status"] not in ("überfällig", "fällig"),
                                               x["due"])):
        f, s, due, tage = e["frist"], e["status"], e["due"], e["tage"]
        tage_txt = "–" if tage is None else (
            f"**+{abs(tage)} überfällig**" if tage < 0 else
            f"heute" if tage == 0 else f"in {tage}")
        zeilen.append(
            f"| {emoji.get(s, '⚪')} {s} | {f['titel']} (`{f['id']}`) "
            f"| {due.isoformat()} | {tage_txt} | {f.get('kategorie', '–')} |")

    for e in ergebnisse:
        if e.get("ki_schutz_fehler"):
            zeilen += ["", f"⚠️ **KI-Abschluss/Issue-Überwachung nicht bestätigt:** {e['ki_schutz_fehler']}"]
    zeilen += ["", "## Sofort-Prüfungen (heute, automatisch)", ""]

    # Veraltungs-Scan
    if scan_funde:
        zeilen += ["### 🔴 Veraltete Rechtsbegriffe im Live-Content "
                   "(sofort entfernen!)", "",
                   "| Datei | Fund | Problem |", "|---|---|---|"]
        for rel, regex, grund in scan_funde:
            zeilen.append(f"| `{rel}` | `{regex}` | {grund} |")
    else:
        zeilen += ["### 🟢 Veraltungs-Scan: keine Funde",
                   "",
                   "Keine veralteten Rechtsbegriffe (TMG, TTDSG, OS-Plattform, "
                   "Privacy Shield, Safe Harbor) in `content/`, `layouts/`, `static/`."]

    # Stand-Alter
    zeilen += ["", "### Stand-Datum der Rechtstexte", ""]
    for name, stand, alter in stand_ergebnisse:
        if stand is None:
            zeilen.append(f"- 🔴 **{name}:** kein „Stand:\"-Datum gefunden – nachtragen!")
        elif alter > STAND_MAX_ALTER_TAGE:
            zeilen.append(f"- 🟠 **{name}:** Stand {stand.isoformat()} "
                          f"({alter} Tage alt) → aktualisieren!")
        else:
            zeilen.append(f"- 🟢 {name}: Stand {stand.isoformat()} ({alter} Tage alt)")

    zeilen += [
        "",
        "## So bedienst du das System",
        "",
        "1. **Issue erhalten:** Ab Fälligkeits-Nähe legt der Bot ein Issue an "
        "(Label `frist`), am Stichtag und danach eskaliert er "
        "(Kommentare + Label `frist-eskalation`).",
        "2. **Abarbeiten:** Checkliste im Issue abarbeiten.",
        "3. **Erledigt markieren:** Actions → „Fristen-Check (Recht)“ → "
        "*Run workflow* → Eingabe `erledigt=<Frist-ID>` (mehrere mit Komma). "
        "Bei #1028 erst Nachweise und Betreiberfreigabe gemäß "
        "`docs/KI-TRANSPARENZ-ABNAHME.md` §5 prüfen. "
        "Nur schließen reicht **nicht** – der Bot legt sonst neu an.",
        "4. **Fristen pflegen:** Neue Pflichten in `data/recht-fristen.yaml` "
        "eintragen (Intervall oder einmaliges Datum) – fertig.",
        "",
        "---",
        f"*Automatisch generiert am {heute_d.isoformat()} vom Fristen-Check "
        "(Recht). Letzte Erledigungen: " +
        (", ".join(f"{k}: {v.get('last_done')}" for k, v in sorted(state.items())
                   if v.get("last_done") and (k != ki_freigabe.FRIST_ID or ki_abgeschlossen))
         or "–") + ".*",
    ]
    REPORT_PATH.write_text("\n".join(zeilen) + "\n", encoding="utf-8")


# ------------------------------------------------------------
#  main
# ------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fristen-Check (Recht) mit Issue-Eskalation")
    parser.add_argument("--now", help="Simuliertes Datum (YYYY-MM-DD, für Tests)")
    parser.add_argument("--done", default="",
                        help="Frist-ID(s) als erledigt markieren (kommagetrennt)")
    parser.add_argument("--scan-only", action="store_true",
                        help="Nur Sofort-Prüfungen (Scan + Stand-Alter)")
    parser.add_argument("--no-issues", action="store_true",
                        help="Keine GitHub-Issues anfassen (nur Report)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Nichts schreiben, nichts posten")
    intern = parser.add_mutually_exclusive_group()
    intern.add_argument("--prepare-ki", action="store_true",
                        help="Interner zweiter Workflow-Job: vorgemerkten KI-Abschluss prüfen")
    intern.add_argument("--finalize-ki", action="store_true",
                        help="Interner zweiter Workflow-Job: KI-Issue nach State-Readback schließen")
    args = parser.parse_args()

    heute_d = heute(args.now)
    fristen = lade_fristen()
    state = lade_state()
    issues = Issues(aktiv=not args.no_issues and not args.dry_run)
    if args.prepare_ki or args.finalize_ki:
        if args.dry_run or args.now or args.done or args.scan_only:
            print("::error title=KI-Issue bleibt offen::Abschluss nicht mit Simulations- oder anderen Optionen kombinieren")
            return 2
        ki_frist = next((f for f in fristen if f.get("id") == ki_freigabe.FRIST_ID), None)
        if not ki_frist or not ki_frist_konform(ki_frist):
            print("::error title=KI-Issue bleibt offen::KI-Fristkonfiguration fehlt oder ist beschädigt")
            return 2
        if args.prepare_ki:
            return bereite_ki_frist_vor(state, issues, heute_d)
        return schliesse_ki_frist(fristen, state, issues, heute_d)

    print(f"⏰ Fristen-Check (Recht) – {heute_d.isoformat()}")
    print(f"   {len(fristen)} Fristen geladen aus {YAML_PATH.name}")

    # 1) Erledigungen entgegennehmen (setzt Fristen neu)
    ki_verweigert = False
    if args.done:
        print("✅ Erledigungen werden geprüft:")
        ki_verweigert = markiere_erledigt(
            [x for x in args.done.split(",") if x.strip()],
            fristen, state, heute_d, issues, dry_run=args.dry_run,
            nur_simulation=bool(args.now or args.scan_only))

    # 2) Fristen bewerten + ggf. Issues anlegen/eskalieren
    ergebnisse = ([]
                  if args.scan_only else
                  bewerte_fristen(fristen, state, heute_d, issues, args.dry_run))

    # 3) Sofort-Prüfungen
    scan_funde = veraltungs_scan()
    if scan_funde:
        print(f"🔴 Veraltungs-Scan: {len(scan_funde)} Funde!")
        if issues.aktiv and not args.dry_run:
            titel = "🚨 Veraltete Rechtsbegriffe im Live-Content (Fristen-Scan)"
            offene = issues.offene_issues()
            if not any(i.get("title") == titel for i in offene):
                body = "\n".join([
                    "Der tägliche Fristen-Scan hat **veraltete Rechtsbegriffe** "
                    "im Live-Content gefunden. Diese sind abmahnbar bzw. "
                    "irreführend (z. B. OS-Plattform-Hinweis nach Abschaltung "
                    "am 20.07.2025):",
                    "",
                    "| Datei | Fund | Problem |", "|---|---|---|",
                    *[f"| `{r}` | `{rx}` | {g} |" for r, rx, g in scan_funde],
                    "",
                    "**Sofort Maßnahmen:** Texte aktualisieren (RECHT-UPDATE-REPORT.md "
                    "sehen), Deploy, Issue schließen.",
                    "",
                    "*Automatisch erstellt vom Fristen-Check (Recht).*",
                ])
                issues.erstellen(titel, body, [LABEL_ESKALATION])
    else:
        print("🟢 Veraltungs-Scan: sauber.")

    stand_ergebnisse = []
    stand_kritisch = False
    for pfad, name in STAND_DATEIEN:
        datei = REPO / pfad
        stand = None
        if datei.exists():
            stand = stand_datum_parsen(datei.read_text(encoding="utf-8"))
        alter = (heute_d - stand).days if stand else None
        stand_ergebnisse.append((name, stand, alter))
        if stand is None or alter > STAND_MAX_ALTER_TAGE:
            stand_kritisch = True
            print(f"🟠 {name}: Stand {stand or 'FEHLT'} "
                  f"({alter if stand else '–'} Tage) → aktualisieren!")

    # 4) Report schreiben + State persistieren; dry-run hat KEINE Schreibwirkung.
    if not args.dry_run:
        schreibe_report(ergebnisse, scan_funde, stand_ergebnisse, heute_d, state)
        schreibe_state(state, False)
        print(f"📄 Report: {REPORT_PATH}")
    else:
        print("   (dry-run: weder Report noch State werden geschrieben)")

    ki_schutz_fehler = any(e.get("ki_schutz_fehler") for e in ergebnisse)
    kritisch = (stand_kritisch or bool(scan_funde) or ki_schutz_fehler
                or any(e["status"] in ("überfällig", "fällig") for e in ergebnisse))
    erinnerung = any(e["status"] == "Erinnerung" for e in ergebnisse)
    print("➡️  Ergebnis: " + ("🔴 Handlungsbedarf – siehe Issues/Report."
                             if kritisch else
                             "🟡 Frist in Erinnerung – siehe Report." if erinnerung else
                             "🟢 Alles im grünen Bereich (nächste Frist im Report)."))
    # 3 = geschützter Abschluss, Überwachung oder Issue-Zuordnung unbestätigt.
    # Andere Fristen wurden verarbeitet; der Workflow pusht ihren State vor Exit 3.
    return 3 if ki_verweigert or ki_schutz_fehler else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit as e:
        if e.code not in (0, None):
            raise
        sys.exit(0)
