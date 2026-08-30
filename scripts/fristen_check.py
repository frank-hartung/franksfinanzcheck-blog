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
#    4. Erledigte Fristen: offenes Issue wird automatisch geschlossen.
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
#  2 = Konfigurations-/Systemfehler.
# ============================================================

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

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
    return fristen


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
        tmp = Path("/tmp/fristen_issue_body.md")
        tmp.write_text(body, encoding="utf-8")
        out = self._run("issue", "create", "--title", titel,
                        "--body-file", str(tmp), "--label", ",".join(labels))
        # gh gibt die Issue-URL zurück → Nummer extrahieren
        if out and "/issues/" in out:
            try:
                return int(out.rstrip("/").rsplit("/", 1)[-1])
            except ValueError:
                return None
        return None

    def kommentieren(self, nummer: int, body: str) -> None:
        tmp = Path("/tmp/fristen_comment.md")
        tmp.write_text(body, encoding="utf-8")
        self._run("issue", "comment", str(nummer), "--body-file", str(tmp))

    def label_setzen(self, nummer: int, label: str) -> None:
        self._run("issue", "edit", str(nummer), "--add-label", label)

    def schliessen(self, nummer: int, kommentar: str) -> None:
        self._run("issue", "close", str(nummer), "--reason", "completed",
                  "--comment", kommentar)


def shutil_which(prog: str) -> str | None:
    from shutil import which
    return which(prog)


# ------------------------------------------------------------
#  Fristen-Auswertung
# ------------------------------------------------------------
def bewerte_fristen(fristen: list[dict], state: dict, heute_d: dt.date,
                    issues: Issues, dry_run: bool) -> list[dict]:
    ergebnisse = []
    offene = issues.offene_issues() if issues.aktiv else []
    titel_map = {i["title"].strip(): i["number"] for i in offene if i.get("title")}

    for frist in fristen:
        fid = frist["id"]
        fstate = state.get(fid) or {}
        einmalig = bool(frist.get("einmalig"))
        erledigt_am = fstate.get("erledigt_am")
        if einmalig and erledigt_am:
            ergebnisse.append({"frist": frist, "status": "abgeschlossen",
                               "due": frist_due(frist, state), "tage": None})
            # Eventuell noch offenes Issue automatisch schließen
            num = fstate.get("issue") or titel_map.get(f"⏰ Frist: {frist['titel']}")
            if num and issues.aktiv and not dry_run:
                issues.schliessen(
                    num, f"✅ Frist **{fid}** wurde am {erledigt_am} als erledigt "
                         f"markiert (`--done`) – Issue automatisch geschlossen.")
                fstate.pop("issue", None)
            continue

        due = frist_due(frist, state)
        tage = (due - heute_d).days
        erinnerung_ab = int(frist.get("erinnerung_ab_tage", 21))
        eskalation_nach = frist.get("eskalation_nach_tagen") or [0, 14, 30]
        ist_erinnerung = 0 < tage <= erinnerung_ab
        ist_ueberfaellig = tage < 0

        status = ("überfällig" if ist_ueberfaellig else
                  "fällig" if tage == 0 else
                  "Erinnerung" if ist_erinnerung else "OK")
        ergebnisse.append({"frist": frist, "status": status, "due": due, "tage": tage})

        if status == "OK" or dry_run or not issues.aktiv:
            continue

        titel = f"⏰ Frist: {frist['titel']}"
        num = fstate.get("issue") or titel_map.get(titel)

        # --- Stufe 0: Erinnerungs-Issue anlegen -------------------
        if num is None:
            checkliste = "\n".join(
                f"- [ ] {punkt}" for punkt in frist.get("checkliste", []))
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
                "**Erledigt?** Nicht nur schließen, sondern *Actions → „Fristen-Check "
                f"(Recht)\" → Run workflow → `erledigt={fid}`* eingeben* – nur dann wird "
                "die Frist neu terminiert und dieses Issue automatisch geschlossen.",
                "*Automatisch erstellt vom Fristen-Check (Recht).*",
            ])
            num = issues.erstellen(titel, body, [LABEL_FRIST])
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
                        "- Bitte PRÜFEN und dann `erledigt="
                        f"{fid}` im Workflow „Fristen-Check (Recht)\" setzen.",
                        "- Oder Frist bewusst neu terminieren (data/recht-fristen.yaml).",
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
                      heute_d: dt.date, issues: Issues) -> None:
    bekannt = {f["id"]: f for f in fristen}
    for fid in ids:
        fid = fid.strip()
        if not fid:
            continue
        frist = bekannt.get(fid)
        if not frist:
            print(f"⚠️  Unbekannte Frist-ID „{fid}\" – verfügbar: "
                  f"{', '.join(bekannt)}")
            continue
        fstate = state.get(fid) or {}
        fstate["last_done"] = heute_d.isoformat()
        if frist.get("einmalig"):
            fstate["erledigt_am"] = heute_d.isoformat()
        fstate.pop("eskaliert", None)
        num = fstate.get("issue")
        if num and issues.aktiv:
            neu = ("" if frist.get("einmalig") else
                   f" Nächster Termin: "
                   f"{(heute_d + dt.timedelta(days=int(frist.get('intervall_tage', 0)))).isoformat()}.")
            issues.schliessen(num, f"✅ Frist **{fid}** als erledigt markiert "
                              f"({heute_d.isoformat()}).{neu}")
            fstate.pop("issue", None)
        state[fid] = fstate
        print(f"   ✅ {fid}: erledigt am {heute_d.isoformat()}" +
              (" (einmalig → abgeschlossen)" if frist.get("einmalig") else ""))


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
        "Nur schließen reicht **nicht** – der Bot legt sonst neu an.",
        "4. **Fristen pflegen:** Neue Pflichten in `data/recht-fristen.yaml` "
        "eintragen (Intervall oder einmaliges Datum) – fertig.",
        "",
        "---",
        f"*Automatisch generiert am {heute_d.isoformat()} vom Fristen-Check "
        "(Recht). Letzte Erledigungen: " +
        (", ".join(f"{k}: {v.get('last_done')}" for k, v in
                   sorted(state.items()) if v.get("last_done")) or "–") + ".*",
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
    args = parser.parse_args()

    heute_d = heute(args.now)
    fristen = lade_fristen()
    state = lade_state()
    issues = Issues(aktiv=not args.no_issues)

    print(f"⏰ Fristen-Check (Recht) – {heute_d.isoformat()}")
    print(f"   {len(fristen)} Fristen geladen aus {YAML_PATH.name}")

    # 1) Erledigungen entgegennehmen (setzt Fristen neu)
    if args.done:
        print("✅ Erledigungen werden verbucht:")
        markiere_erledigt([x for x in args.done.split(",") if x.strip()],
                          fristen, state, heute_d, issues)

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

    # 4) Report schreiben + State persistieren
    schreibe_report(ergebnisse, scan_funde, stand_ergebnisse, heute_d, state)
    schreibe_state(state, args.dry_run)
    print(f"📄 Report: {REPORT_PATH}")

    kritisch = (stand_kritisch or bool(scan_funde)
                or any(e["status"] in ("überfällig", "fällig") for e in ergebnisse))
    print("➡️  Ergebnis: " + ("🔴 Handlungsbedarf – siehe Issues/Report."
                             if kritisch else
                             "🟢 Alles im grünen Bereich (nächste Frist im Report)."))
    return 0  # Absichtlich 0: Eskalation läuft über Issues, nicht rote Runs.


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit as e:
        if e.code not in (0, None):
            raise
        sys.exit(0)
