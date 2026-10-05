#!/usr/bin/env python3
"""slot_wache.py – die Slot-Wache der Content-Linie (Engine + Kadenz-Backstop).

WARUM (05.10.2026, Issue #601 „Content-Engine: Tagesdefizit (1/2 LIVE)“):
An diesem Montag lieferte GitHubs Scheduler die planmäßigen Läufe der
Content-Linie nicht:

  * Content-Engine v2, Haupt-Slot 06:10 UTC  – kein einziger Lauf.
  * Content-Engine v2, Fallback 17:40 UTC    – kein einziger Lauf.
  * Kadenz-Endkontrolle, 10:35-Slot          – kein einziger Lauf.
  * Kadenz-Endkontrolle, 16:35-Slot          – erst 19:22 UTC (2 h 47 min
    später – als Einziger überhaupt angekommen).

Der einzige Engine-Lauf des Tages (14:32) verlor seine fertige Arbeit
außerdem an den Synchronverlust (#590/#597) – aber selbst ohne diesen
Zufallstreff hätte die Tagesspitze auf 4 nie gestarteten Slots geruht.
Ein Lauf, der nie startet, wird nie rot: kein Ereignis für das
Fehler-Alerting, keine Annotation, kein Issue. Am Abend schaufelte der
einzige nachgekommene Backstop genau EINEN Reserve-Artikel live (1/2) –
und die Defizit-Wache meldete ein Symptom, dessen Ursache („4 Slots nie
gestartet“) nirgendwo stand.

Das Repo kannte diese Fehlerklasse bereits: Die Newsletter-Kadenz-Wache
(23.09.2026, `newsletter_cadence.py`) existiert genau deshalb – „GitHub
verwirft schedule-Ereignisse unter Last“ steht dort wörtlich, inklusive
Gemessenes vom 25.09. („jedes Ereignis 5–5,5 h zu spät oder gar nicht“).
Nur die Content-Linie, das Herzstück, hatte denselben Schutz nie bekommen.

DIESE WACHE (Netz Nr. 4 hinter Worker-Taktgeber, Cron-Kette und
Produktions-Wache):

  1. Sie kennt die Soll-Slots aus den Workflow-Dateien selbst
     (`content-engine-v2.yml`, `kadenz-endkontrolle.yml`) – geparst, nicht
     abgetippt. Wer den Plan verschiebt, verschiebt die Wache mit.
  2. An Publikationstagen (Mo/Mi/Fr, SSOT `cadence_guard.PUBLICATION_DAYS`)
     gilt ein Slot nach Soll + GNADENFRIST als VERPASST, wenn seither kein
     einziger Lauf des Workflows existiert ( queued / in_progress / success
     / failure – ein FEHLGESCHLAGENER Lauf ist laut und kein Fall dieser
     Wache, exakt wie bei der Newsletter-Wache).
  3. Ist das Tagesziel (LIVE ≥ MIN_ARTIKEL_PRO_TAG) schon erreicht, schweigt
     die Wache: Ihr Auftrag ist die Quote, nicht der Prozess.
  4. Verpasster Slot + Quote offen → Nachhol-Dispatch über die GitHub-API
     (`gh workflow run`, workflow_dispatch ist in beiden Workflows
     vorhanden und vertraglich eingefroren). Pro Workflow und Wachen-Lauf
     wird höchstens EIN Lauf nachgeholt – der älteste verpasste Slot. Der
     nächste Tick (alle 20 min) bewertet neu; der nachgeholte Lauf zählt
     selbst als „bedient“, eine Schleife ist ausgeschlossen.
  5. Nach dem letzten Slot + Gnadenfrist mit weiter offener Quote meldet
     die Wache das Defizit selbst (`engine_issue.py --deficit`, nur wenn
     noch kein offenes Defizit-Issue existiert) – damit der Alarm auch dann
     rausgeht, wenn jeder Kadenz-Cron und jeder Nachhol-Dispatch versagt.
  6. Sie ist selbst nur ein weiteres Netz am selben Haken: Ihr eigener Cron
     läuft alle 20 Minuten – fällt die Hälfte aller Ticks aus, bleibt immer
     noch ein Tick pro Stunde. Und sie beweist sich bei jedem Merge
     (push-Trigger auf die eigenen Pfade).

Doppel-Fall ungefährlich: Kommt ein verschobener Cron doch noch, während
der Nachhol-Lauf schon läuft, reiht ihn die gemeinsame
concurrency-Gruppe `content-bot` ein; das Kadenz-Gate (2–3 LIVE) und der
Mitternachts-Wächter in `reserve_pool` verhindern Über- wie Rückdatierung.

Sicherheitshierarchie (unverändert):
  * Die Wache veröffentlicht nichts, erzeugt nichts und fasst keinen
    Content an – sie ruft nur Workflows auf, die ohnehin cron-fähig sind.
  * Alle Diagnose-Pfade sind fail-open (eine kaputte Diagnose darf den
    Alarm nie verschlucken); die Eingriffe selbst sind fail-laut.

Nutzung:
    python3 scripts/slot_wache.py --pruefen                 # zählen + nachholen
    python3 scripts/slot_wache.py --pruefen --ohne-dispatch # Trockenlauf
    python3 scripts/slot_wache.py --selftest

Exit: 0 = Ruhe / Ziel erreicht / nachgeholt · 1 = Befund (Slot verpasst
und nicht nachholbar, Quote offen und Defizit nicht meldbar, oder die
Wache ist blind) · 2 = Selbsttest rot.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys
import time

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import cadence_guard as cg  # noqa: E402 – PUBLICATION_DAYS/Limits (SSOT)

# Die beobachtete Content-Linie: Produktion (Engine) und Backstop (Kadenz).
# Die Content-Reserve (Nachschub) hat mit bot_watchdog + reserve_readiness
# eine eigene, bestandsorientierte Wache – sie zählt nicht zur Tagesquote.
WORKFLOWS = (
    ("content-engine-v2.yml", "Content-Engine v2"),
    ("kadenz-endkontrolle.yml", "Kadenz-Endkontrolle (Mo/Mi/Fr – 2–3 LIVE erzwingen)"),
)

# Beobachtete Scheduler-Latenz am 05.10.2026: 22 min (14:10 → 14:32) und
# 2 h 47 min (16:35 → 19:22). Die Gnadenfrist darf so knapp sein, dass ein
# regulär verspäteter Cron meist noch selbst ankommt (der Doppel-Lauf ist
# durch concurrency + Kadenz-Gate harmlos), aber so groß, dass kein halber
# Tag ungenutzt verstreicht. 45 min ist der Kompromiss; der Selbsttest
# friert die Grenze exakt ein.
GNADENFRIST = dt.timedelta(minutes=45)

DISPATCH_VERSUCHE = 3           # der Nachhol-Call selbst ist ein Netz-Call
DISPATCH_PAUSE = (3.0, 8.0)

CRON_ZEILE = re.compile(r"-\s*cron:\s*[\"']([^\"']+)[\"']")


# ----------------------------------------------------------------------
# Zeit-Helfer (gleiche Disziplin wie newsletter_cadence)
# ----------------------------------------------------------------------

def parse_ts(wert: str) -> dt.datetime:
    ts = dt.datetime.fromisoformat(str(wert).strip().replace("Z", "+00:00"))
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=dt.timezone.utc)
    return ts.astimezone(dt.timezone.utc)


def iso(ts: dt.datetime) -> str:
    return ts.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


# ----------------------------------------------------------------------
# Soll-Slots aus den Workflow-Dateien (geparst, nie abgetippt)
# ----------------------------------------------------------------------

def parse_crons(text: str) -> list[str]:
    """Alle cron-Ausdrücke aus dem on:-Block einer Workflow-Datei."""
    return [m.group(1).strip() for m in CRON_ZEILE.finditer(text or "")]


def _cron_feld_ints(feld: str) -> list[int] | None:
    """„10,16,19,21“ → [10,16,19,21] · „7“ → [7] · sonst (*/n, Bereiche) None."""
    feld = feld.strip()
    if not feld or feld == "*":
        return None
    teile = feld.split(",")
    werte: list[int] = []
    for t in teile:
        if not t.strip().isdigit():
            return None
        werte.append(int(t.strip()))
    return werte


def cron_zeiten_heute(cron: str, tag: dt.date) -> list[dt.datetime]:
    """Geplante Startzeiten (UTC) eines cron-Ausdrucks an `tag`.

    Unterstützt ist bewusst nur die in diesem Repo benutzte Syntax
    „M H * * D“ (H und D je fest, Liste oder *). Alles andere
    (Schritte, Bereiche, Monate) gilt als nicht verstanden und liefert
    [] – die Wache warnt dann; eine Wache, die einen Plan nur
    GIBT zu verstehen, wäre schlimmer als keine.
    """
    felder = (cron or "").split()
    if len(felder) != 5:
        return []
    minute_s, stunde_s, dom_s, monat_s, dow_s = felder
    if dom_s != "*" or monat_s != "*":
        return []  # datumgebundene Ausnahmen: nicht unterstützt, nicht geraten
    minuten = _cron_feld_ints(minute_s)
    if minuten is None or len(minuten) != 1:
        return []  # Minuten-Listen/Schritte benutzt dieses Repo nicht
    stunden = _cron_feld_ints(stunde_s)
    if stunden is None:
        stunden = list(range(24))  # „*“
    dows = _cron_feld_ints(dow_s)
    if dows is None:
        pass  # „*“ – jeder Tag
    else:
        # cron zählt Sonntag=0/7, Python weekday() Montag=0.
        py_dows = {(d - 1) % 7 for d in dows}
        if tag.weekday() not in py_dows:
            return []
    try:
        return [dt.datetime(tag.year, tag.month, tag.day, s, minuten[0],
                            tzinfo=dt.timezone.utc)
                for s in sorted(set(stunden))]
    except ValueError:
        return []


def slots_fuer_tag(tag: dt.date, workflows: tuple = WORKFLOWS,
                   workflows_dir: str | None = None) -> tuple[list[dict], list[str]]:
    """(Slots, Warnungen) – Slots aufsteigend nach Soll-Zeit.

    Jeder Slot: {"datei", "name", "soll" (UTC-Datetime), "cron"}.
    Fehlt eine Workflow-Datei, ist das kein Grund zu schweigen: Die
    Warnung steht im Bericht, und ein Publikationstag OHNE einzigen Slot
    macht die Wache später laut (Blindheit ist ein Befund).
    """
    workflows_dir = workflows_dir or os.path.join(BLOG_DIR, ".github", "workflows")
    slots: list[dict] = []
    warnungen: list[str] = []
    for datei, name in workflows:
        pfad = os.path.join(workflows_dir, datei)
        try:
            with open(pfad, encoding="utf-8") as fh:
                text = fh.read()
        except OSError as exc:
            warnungen.append(f"{datei} nicht lesbar ({exc.__class__.__name__}) – "
                             f"Soll-Slots dieser Linie unbekannt.")
            continue
        crons = parse_crons(text)
        if not crons:
            warnungen.append(f"{datei} enthält keinen cron-Ausdruck – "
                             f"Soll-Slots dieser Linie unbekannt.")
            continue
        for cron in crons:
            zeiten = cron_zeiten_heute(cron, tag)
            if not zeiten:
                warnungen.append(f"{datei}: cron „{cron}“ an {tag.isoformat()} "
                                 f"nicht fällig oder Syntax nicht unterstützt.")
                continue
            for soll in zeiten:
                slots.append({"datei": datei, "name": name, "soll": soll,
                              "cron": cron})
    slots.sort(key=lambda s: (s["soll"], s["datei"]))
    return slots, warnungen


# ----------------------------------------------------------------------
# Die reine Entscheidung – ohne Netz, ohne Schreibzugriff, getestet
# ----------------------------------------------------------------------

def _bedient_durch(slot: dict, laeufe: list[dict], jetzt: dt.datetime) -> dict | None:
    """Der erste Lauf ab Slot-Soll-Zeit (der spät gekommene Cron zählt)."""
    treffer = []
    for l in laeufe or []:
        try:
            erstellt = parse_ts(l["created_at"])
        except (KeyError, ValueError, TypeError):
            continue  # unverständliche Zeitstempel werfen die Zählung nicht um
        if slot["soll"] <= erstellt <= jetzt:
            treffer.append((erstellt, l))
    if not treffer:
        return None
    treffer.sort(key=lambda x: x[0])
    erstellt, l = treffer[0]
    return {"id": l.get("id"), "status": l.get("status"),
            "conclusion": l.get("conclusion"),
            "created_at": iso(erstellt), "url": l.get("url"),
            "event": l.get("event")}


def entscheide(jetzt: dt.datetime, slots: list[dict],
               laeufe_je_workflow: dict, live_heute: int,
               minimum: int) -> dict:
    """Slot-Protokoll + Nachhol-Plan für diesen Wachen-Tick.

    → {"handlung": "ruhetag" | "warten" | "ziel-erreicht" | "nachholen"
                     | "beobachten" | "defizit-melden",
       "slots": [...], "nachholen": [datei, ...], "defizit": bool, ...}
    """
    jetzt = jetzt.astimezone(dt.timezone.utc)
    tag = jetzt.date()
    erg = {
        "jetzt": iso(jetzt),
        "tag": tag.isoformat(),
        "publikationstag": cg.is_publication_day(tag),
        "live_heute": live_heute,
        "minimum": minimum,
        "ziel_erreicht": live_heute >= minimum,
        "slots": [],
        "nachholen": [],
        "defizit": False,
        "handlung": "ruhetag",
        "befund": "",
    }
    if not erg["publikationstag"]:
        erg["befund"] = (f"{cg.DAYS_DE[tag.weekday()]} ist kein Publikationstag "
                         f"(Mo/Mi/Fr) – keine Slot-Forderung.")
        return erg
    if not slots:
        erg["handlung"] = "blind"
        erg["befund"] = ("Kein einziger Soll-Slot bekannt – die Wache ist blind. "
                         "Workflow-Dateien prüfen (content-engine-v2.yml, "
                         "kadenz-endkontrolle.yml).")
        return erg

    protokoll = []
    for slot in slots:
        eintrag = {"datei": slot["datei"], "name": slot["name"],
                   "soll": iso(slot["soll"]), "cron": slot["cron"]}
        if jetzt < slot["soll"] + GNADENFRIST:
            eintrag["zustand"] = "wartet"
            eintrag["hinweis"] = (f"Soll {slot['soll']:%H:%M} UTC + "
                                  f"{int(GNADENFRIST.total_seconds() // 60)} min "
                                  f"Gnadenfrist noch nicht erreicht.")
        else:
            lauf = _bedient_durch(slot, laeufe_je_workflow.get(slot["datei"], []),
                                  jetzt)
            if lauf is not None:
                eintrag["zustand"] = "bedient"
                eintrag["lauf"] = lauf
            else:
                eintrag["zustand"] = "verpasst"
        protokoll.append(eintrag)
    erg["slots"] = protokoll

    letzter_slot = max(s["soll"] for s in slots)
    defizit_fenster = jetzt >= letzter_slot + GNADENFRIST
    erg["defizit"] = bool(defizit_fenster and not erg["ziel_erreicht"])

    if erg["ziel_erreicht"]:
        erg["handlung"] = "ziel-erreicht"
        erg["befund"] = (f"Tagesziel erreicht: {live_heute}/{minimum} LIVE – "
                         f"verpasste Slots sind heute ohne Folge.")
        return erg

    # Pro Workflow der ÄLTESTE verpasste Slot – genau ein Nachhol-Lauf.
    nachholen: list[str] = []
    for datei, _name in WORKFLOWS:
        verpasst = [e for e in protokoll
                    if e["datei"] == datei and e["zustand"] == "verpasst"]
        if verpasst:
            nachholen.append(datei)
            erg.setdefault("nachholgrund", {})[datei] = verpasst[0]["soll"]
    erg["nachholen"] = nachholen

    if nachholen:
        erg["handlung"] = "nachholen"
        erg["befund"] = (f"Quote offen ({live_heute}/{minimum} LIVE) und "
                         f"{len(nachholen)} Workflow(s) mit verpasstem Slot – "
                         f"Nachhol-Dispatch: {', '.join(nachholen)}.")
    elif defizit_fenster:
        erg["handlung"] = "defizit-melden"
        erg["befund"] = (f"Alle Soll-Slots bedient oder vorbei, Quote weiterhin "
                         f"offen ({live_heute}/{minimum} LIVE) – Defizit wird "
                         f"gemeldet (falls noch nicht geschehen).")
    else:
        erg["handlung"] = "beobachten"
        erg["befund"] = (f"Quote offen ({live_heute}/{minimum} LIVE), aber kein "
                         f"Slot ist überfällig-ungebedient – Restslots des Tages "
                         f"laufen noch.")
    return erg


# ----------------------------------------------------------------------
# Messung: Runs je Workflow + heutige LIVE-Zahl
# ----------------------------------------------------------------------

def _gh(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], capture_output=True, text=True, timeout=120)


def lade_laeufe(repo: str, workflow_datei: str) -> list[dict]:
    """Die letzten Runs eines Workflows (jede Statuslage)."""
    pfad = (f"repos/{repo}/actions/workflows/{workflow_datei}/runs"
            f"?per_page=50")
    r = _gh(["api", pfad, "--jq",
             '.workflow_runs[] | {id: (.id|tostring), status: .status, '
             'conclusion: .conclusion, created_at: .created_at, '
             'url: .html_url, event: .event}'])
    if r.returncode != 0:
        raise RuntimeError(f"gh api {pfad}: "
                           f"{(r.stderr or r.stdout or '').strip()[:300]}")
    laeufe = []
    for zeile in (r.stdout or "").splitlines():
        zeile = zeile.strip()
        if not zeile:
            continue
        try:
            laeufe.append(json.loads(zeile))
        except json.JSONDecodeError:
            continue
    return laeufe


def _offenes_defizit_issue() -> str:
    """Nummer des offenen Tagesdefizit-Issues (engine-deficit), sonst "".

    Nutzt dieselbe Markierung wie engine_issue.py – keine zweite
    Duplikat-Regel, die auseinanderlaufen könnte.
    """
    try:
        import engine_issue
    except Exception:  # noqa: BLE001 – Bestandsaufnahme ist optional
        return ""
    listed = _gh(["issue", "list", "--label", engine_issue.LABEL,
                  "--state", "open", "--json", "number,body"])
    if listed.returncode != 0:
        return ""
    try:
        eintraege = json.loads(listed.stdout or "[]")
    except json.JSONDecodeError:
        return ""
    for e in eintraege:
        if engine_issue.MARKER in (e.get("body") or ""):
            return str(e.get("number") or "")
    return ""


def melde_defizit() -> tuple[int, str]:
    """Defizit-Issue über die bestehende Defizit-Wache anlegen.

    Nur aufrufen, wenn noch kein offenes existiert – engine_issue
    kommentiert sonst jedesmal erneut (Spam).
    """
    nummer = _offenes_defizit_issue()
    if nummer:
        return 0, f"Defizit bereits als Issue #{nummer} gemeldet."
    r = subprocess.run([sys.executable,
                        os.path.join(BLOG_DIR, "scripts", "engine_issue.py"),
                        "--deficit"],
                       cwd=BLOG_DIR, capture_output=True, text=True, timeout=180)
    auszug = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
    letzte = auszug[-1][:200] if auszug else f"Exit {r.returncode}"
    if r.returncode != 0:
        return 1, f"Defizit-Meldung fehlgeschlagen: {letzte}"
    return 0, f"Defizit gemeldet: {letzte}"


def hole_nach(repo: str, workflow_datei: str, ref: str) -> tuple[int, str]:
    """Den verpassten Slot-Lauf dispatchen (gleiche Freigabe wie der Cron)."""
    letzte_fehler = ""
    for versuch in range(DISPATCH_VERSUCHE):
        r = _gh(["workflow", "run", workflow_datei, "--repo", repo, "--ref", ref])
        if r.returncode == 0:
            return 0, f"Nachhol-Dispatch {workflow_datei} angenommen."
        letzte_fehler = (r.stderr or r.stdout or "").strip()[:300]
        # 422 „could not create workflow dispatch“ in den ersten Sekunden kann
        # ein Race mit einem parallel startenden Lauf sein – kurz warten, dann
        # erneut. Alles andere (Auth, fehlende actions:write) wiederholt sich
        # nicht sinnvoll: sofort melden.
        if "422" not in letzte_fehler:
            break
        if versuch + 1 < DISPATCH_VERSUCHE:
            time.sleep(DISPATCH_PAUSE[min(versuch, len(DISPATCH_PAUSE) - 1)])
    return 1, f"Nachhol-Dispatch {workflow_datei} fehlgeschlagen: {letzte_fehler}"


def _lese_quote() -> tuple[int, int]:
    """(live_heute, minimum) aus dem Bestand – dieselbe SSOT wie die Engine."""
    heute = dt.datetime.now(dt.timezone.utc).date()
    posts = cg.load_posts()
    minimum, _maximum = cg.effective_limits()
    return len(cg.published_on(posts, heute)), minimum


def pruefen(repo: str, *, jetzt: dt.datetime | None = None, ref: str = "main",
            ohne_dispatch: bool = False,
            laeufe_je_workflow: dict | None = None,
            live_heute: int | None = None,
            minimum: int | None = None,
            slots: list[dict] | None = None,
            lade_laeufe_fn=None) -> dict:
    jetzt = jetzt or dt.datetime.now(dt.timezone.utc)
    tag = jetzt.date()

    # Ruhetag früh entscheiden: An Di/Do/Sa/So gibt es keine Slot-Forderung –
    # Laufbücher und Quoten werden dann gar nicht erst gelesen (die Wache
    # tickt alle 20 Minuten, auch an vier Tagen pro Woche umsonst).
    if not cg.is_publication_day(tag):
        erg = entscheide(jetzt, [], {}, 0, 2)
        erg.update({"repo": repo, "ref": ref, "warnungen": [],
                    "dispatches": [], "defizit_meldung": "", "rc": 0})
        return erg

    if slots is None:
        slots, warnungen = slots_fuer_tag(tag)
    else:
        warnungen = []
    if live_heute is None or minimum is None:
        try:
            live_heute, minimum = _lese_quote()
        except Exception as exc:  # noqa: BLE001 – Quoten-Messung darf brechen
            live_heute, minimum = live_heute or 0, minimum or 2
            warnungen.append(f"Quoten-Messung aus dem Bestand fehlgeschlagen "
                             f"({exc.__class__.__name__}: {exc}) – gezählt mit "
                             f"{live_heute}/{minimum}.")

    messbar = bool(repo)
    messfehler: dict[str, str] = {}
    if laeufe_je_workflow is None:
        laeufe_je_workflow = {}
        if messbar:
            lader = lade_laeufe_fn or lade_laeufe
            for datei, _name in WORKFLOWS:
                try:
                    laeufe_je_workflow[datei] = lader(repo, datei)
                except Exception as exc:  # noqa: BLE001 – ein Workflow blind
                    messfehler[datei] = f"{exc.__class__.__name__}: {str(exc)[:160]}"
                    laeufe_je_workflow[datei] = []
                    warnungen.append(f"Laufstands-Messung {datei} fehlgeschlagen "
                                     f"({messfehler[datei]}) – Slots dieser "
                                     f"Linie gelten als UNBEKANNT, es wird "
                                     f"nicht blind nachgeholt.")

    erg = entscheide(jetzt, slots, laeufe_je_workflow, live_heute, minimum)
    erg["repo"] = repo
    erg["ref"] = ref
    erg["warnungen"] = warnungen
    erg["dispatches"] = []
    erg["defizit_meldung"] = ""
    erg["rc"] = 0

    # Eine Wache, deren Laufbuch blinde Flecken hat, handelt nicht: Ein
    # vermeintlich verpasster Slot könnte längst laufen. Stattdessen wird
    # der Zustand ehrlich „unbekannt“ und der Befund laut (rc=1).
    if messfehler:
        for eintrag in erg.get("slots", []):
            if eintrag["datei"] in messfehler and eintrag["zustand"] == "verpasst":
                eintrag["zustand"] = "unbekannt"
                eintrag["hinweis"] = "Laufbuch nicht lesbar – keine Aussage."
        gestrichen = [d for d in erg.get("nachholen", []) if d in messfehler]
        if gestrichen:
            erg["nachholen"] = [d for d in erg["nachholen"]
                                if d not in messfehler]
            for d in gestrichen:
                erg["dispatches"].append(
                    f"{d}: nicht nachgeholt – Laufbuch nicht lesbar (blind "
                    f"handeln wäre schlimmer als warten).")
            if not erg["nachholen"]:
                erg["handlung"] = ("beobachten" if not erg.get("defizit")
                                   else "defizit-melden")
            erg["rc"] = 1

    if erg["handlung"] == "blind":
        erg["rc"] = 1
        return erg

    if erg["handlung"] == "nachholen":
        if ohne_dispatch:
            erg["dispatches"] = [f"{d}: übersprungen (Trockenlauf)"
                                 for d in erg["nachholen"]]
            erg["rc"] = 1  # ein Befund, der Nachholung verlangt
        elif not messbar:
            erg["dispatches"] = [f"{d}: nicht möglich (kein Repo/gh)"
                                 for d in erg["nachholen"]]
            erg["rc"] = 1
        else:
            for datei in erg["nachholen"]:
                code, meldung = hole_nach(repo, datei, ref)
                erg["dispatches"].append(meldung)
                if code != 0:
                    erg["rc"] = 1

    # Defizit melden – aber NIE, solange noch ein Nachhol-Lauf das Tagesziel
    # erreichen könnte: Der nachgeholte Lauf meldet sein eigenes Defizit
    # (engine_issue --deficit läuft in beiden Workflows). Gemeldet wird erst,
    # wenn nichts mehr nachholbar ist oder ein Nachhol-Dispatch gescheitert
    # ist – sonst klänge der Alarm, während die Heilung schon läuft.
    nachholbar_ohne_erfolg = (erg.get("nachholen")
                              and (ohne_dispatch or not messbar
                                   or erg["rc"] != 0))
    if erg.get("defizit") and (not erg.get("nachholen") or nachholbar_ohne_erfolg):
        if ohne_dispatch:
            erg["defizit_meldung"] = ("übersprungen (Trockenlauf) – Quote "
                                      "weiterhin offen.")
            if erg["rc"] == 0:
                erg["rc"] = 1
        else:
            code, meldung = melde_defizit()
            erg["defizit_meldung"] = meldung
            if code != 0:
                erg["rc"] = 1
    return erg


# ----------------------------------------------------------------------
# Bericht
# ----------------------------------------------------------------------

def als_md(erg: dict) -> str:
    zeilen = ["## 🎰 Slot-Wache (Content-Linie)", "",
              f"**Stand ({erg['jetzt']}):** {erg['befund']}", ""]
    zeilen += [f"- Tagesziel: **{erg['live_heute']}/{erg['minimum']} LIVE**"
               f"{' ✅' if erg['ziel_erreicht'] else ''}",
               f"- Handlung: `{erg['handlung']}`"]
    if erg.get("dispatches"):
        for d in erg["dispatches"]:
            zeilen.append(f"- Dispatch: {d}")
    if erg.get("defizit_meldung"):
        zeilen.append(f"- Defizit: {erg['defizit_meldung']}")
    for w in erg.get("warnungen") or []:
        zeilen.append(f"- ⚠️ {w}")
    if erg.get("slots"):
        zeilen += ["", "| Workflow | Soll (UTC) | Zustand | Lauf |",
                   "|---|---|---|---|"]
        for s in erg["slots"]:
            lauf = s.get("lauf")
            if lauf:
                lauf_txt = (f"[{lauf.get('id')}]({lauf.get('url', '')}) "
                            f"{lauf.get('status')}/{lauf.get('conclusion')} "
                            f"um {lauf.get('created_at', '')[:19]}")
            elif s.get("hinweis"):  # wartet / unbekannt
                lauf_txt = s["hinweis"]
            else:
                lauf_txt = "– kein einziger Laufversuch seit Soll"
            zeilen.append(f"| {s['name']} | {s['soll'][11:16]} | "
                          f"{s['zustand']} | {lauf_txt} |")
    return "\n".join(zeilen)


def diagnose_zeilen(repo: str = "", *, jetzt: dt.datetime | None = None) -> str:
    """Kompaktes Slot-Protokoll für das Tagesdefizit-Issue (fail-open).

    Issue #601 zeigte Themen-Kapazität („29 frei disponierbar“), aber nicht
    die Ursache des Tages („4 von 7 Slots nie gestartet“). Dieser Abschnitt
    hängt die Lauf-Realität des Tages an den Alarm.
    """
    try:
        jetzt = jetzt or dt.datetime.now(dt.timezone.utc)
        slots, warnungen = slots_fuer_tag(jetzt.date())
        live_heute, minimum = _lese_quote()
        laeufe: dict = {}
        # Kann das Laufbuch eines Workflows nicht gelesen werden, entfällt
        # das GANZE Protokoll – eine Tabelle, die „verpasst“ zeigt, weil die
        # Messung blind war, wäre schlimmer als keine Tabelle (Issue #601:
        # der Alarm darf die Ursache nicht erfinden).
        if repo:
            for datei, _name in WORKFLOWS:
                laeufe[datei] = lade_laeufe(repo, datei)
        erg = entscheide(jetzt, slots, laeufe, live_heute, minimum)
        out = ["\n### Slot-Protokoll des Tages\n",
               f"**Soll-Slots heute:** {len(slots)} · "
               f"**verpasst:** "
               f"{len([s for s in erg['slots'] if s['zustand'] == 'verpasst'])} · "
               f"**LIVE:** {live_heute}/{minimum}\n"]
        out.append("| Workflow | Soll (UTC) | Zustand | Lauf |")
        out.append("|---|---|---|---|")
        for s in erg["slots"]:
            lauf = s.get("lauf")
            lauf_txt = "–" if not lauf else (
                f"{lauf.get('status')}/{lauf.get('conclusion')} "
                f"um {lauf.get('created_at', '')[11:19]}")
            out.append(f"| {s['name']} | {s['soll'][11:16]} | {s['zustand']} "
                       f"| {lauf_txt} |")
        if warnungen:
            out.append("")
            for w in warnungen:
                out.append(f"- ⚠️ {w}")
        out.append("\nHintergrund: `TAGESDEFIZIT-ENGINE-601-DAUERHEILUNG-"
                   "PREMIUM-2026-10-05.md` (Slot-Wache).\n")
        return "\n".join(out)
    except Exception as exc:  # noqa: BLE001 – Alarm geht IMMER raus
        return (f"\n_(Slot-Protokoll nicht verfügbar: "
                f"{exc.__class__.__name__}: {exc})_\n")


# ----------------------------------------------------------------------
# Selbsttest – der Vorfall vom 05.10.2026 nachgestellt (ohne Netz)
# ----------------------------------------------------------------------

def _selftest() -> int:
    fehler: list[str] = []
    zaehler = 0

    def pruefe(bedingung: bool, meldung: str) -> None:
        nonlocal zaehler
        if bedingung:
            zaehler += 1
        else:
            fehler.append(meldung)

    def lauf(cid: str, erstellt: str, status: str = "completed",
             conclusion: str = "success") -> dict:
        return {"id": cid, "status": status, "conclusion": conclusion,
                "created_at": erstellt,
                "url": f"https://example.invalid/{cid}", "event": "schedule"}

    montag = dt.date(2026, 10, 5)          # der Vorfallstag
    samstag = dt.date(2026, 10, 10)

    # 1) Soll-Slots aus den ECHTEN Workflow-Dateien: Engine 3 + Kadenz 4.
    slots, warn = slots_fuer_tag(montag)
    engine_slots = [s for s in slots if s["datei"] == "content-engine-v2.yml"]
    kadenz_slots = [s for s in slots
                    if s["datei"] == "kadenz-endkontrolle.yml"]
    pruefe(len(engine_slots) == 3 and len(kadenz_slots) == 4,
           f"Soll-Slots falsch: Engine {len(engine_slots)}, "
           f"Kadenz {len(kadenz_slots)} (Warnungen: {warn})")
    pruefe([s["soll"].hour for s in engine_slots] == [6, 14, 17],
           f"Engine-Soll-Stunden falsch: {[s['soll'].hour for s in engine_slots]}")
    pruefe([s["soll"].hour for s in kadenz_slots] == [10, 16, 19, 21],
           f"Kadenz-Soll-Stunden falsch: {[s['soll'].hour for s in kadenz_slots]}")
    pruefe(all(s["soll"].minute in (10, 35, 40) for s in slots),
           f"Soll-Minuten falsch: {[s['soll'].minute for s in slots]}")

    # 2) Kein Publikationstag → keine Slots, Ruhetag.
    samstag_slots, _ = slots_fuer_tag(samstag)
    pruefe(samstag_slots == [], f"Samstag darf keine Slots haben: {samstag_slots}")

    # 3) Der Vorfall, 19:30 UTC: Engine lief nur 14:32 (deckt 06:10+14:10),
    #    Kadenz nur 19:22 (deckt 10:35+16:35) → nachholen: Engine (17:40)
    #    UND Kadenz (19:35 wartet noch). Quote 1/2.
    jetzt = dt.datetime(2026, 10, 5, 19, 30, tzinfo=dt.timezone.utc)
    laeufe = {
        "content-engine-v2.yml": [lauf("e1", "2026-10-05T14:32:15Z",
                                       conclusion="failure")],
        "kadenz-endkontrolle.yml": [lauf("k1", "2026-10-05T19:22:22Z",
                                         conclusion="failure")],
    }
    erg = entscheide(jetzt, slots, laeufe, live_heute=1, minimum=2)
    zustaende = {(s["datei"], s["soll"][11:16]): s["zustand"] for s in erg["slots"]}
    pruefe(zustaende[("content-engine-v2.yml", "06:10")] == "bedient",
           f"06:10 durch den 14:32-Lauf gedeckt: {zustaende}")
    pruefe(zustaende[("content-engine-v2.yml", "14:10")] == "bedient",
           f"14:10 durch den 14:32-Lauf gedeckt: {zustaende}")
    pruefe(zustaende[("content-engine-v2.yml", "17:40")] == "verpasst",
           f"17:40 muss verpasst sein: {zustaende}")
    pruefe(zustaende[("kadenz-endkontrolle.yml", "10:35")] == "bedient"
           and zustaende[("kadenz-endkontrolle.yml", "16:35")] == "bedient",
           f"Kadenz 10:35/16:35 durch den 19:22-Lauf gedeckt: {zustaende}")
    pruefe(zustaende[("kadenz-endkontrolle.yml", "19:35")] == "wartet",
           f"19:35 liegt noch in der Gnadenfrist: {zustaende}")
    pruefe(erg["handlung"] == "nachholen" and erg["nachholen"] ==
           ["content-engine-v2.yml"],
           f"Nachhol-Plan falsch: {erg['handlung']} {erg['nachholen']}")

    # 4) Ziel erreicht → keine Dispatches, auch mit verpassten Slots.
    erg = entscheide(jetzt, slots, laeufe, live_heute=2, minimum=2)
    pruefe(erg["handlung"] == "ziel-erreicht" and not erg["nachholen"],
           f"Ziel erreicht muss schweigen: {erg['handlung']}")

    # 5) Gnadenfrist exakt: 06:10-Slot um 06:54 wartet, um 06:56 ist er
    #    verpasst (45 min).
    def zustand(datei: str, uhr: str, erg_: dict) -> str:
        for s in erg_["slots"]:
            if s["datei"] == datei and s["soll"][11:16] == uhr:
                return s["zustand"]
        return "?"

    frueh = dt.datetime(2026, 10, 5, 6, 54, tzinfo=dt.timezone.utc)
    erg = entscheide(frueh, slots, {}, live_heute=0, minimum=2)
    pruefe(zustand("content-engine-v2.yml", "06:10", erg) == "wartet",
           f"06:54 muss noch warten: {erg['slots']}")
    frueh = dt.datetime(2026, 10, 5, 6, 56, tzinfo=dt.timezone.utc)
    erg = entscheide(frueh, slots, {}, live_heute=0, minimum=2)
    pruefe(zustand("content-engine-v2.yml", "06:10", erg) == "verpasst",
           f"06:56 muss verpasst sein: {erg['slots']}")

    # 6) Ein FEHLGESCHLAGENER Lauf bedient den Slot (laut, kein Auto-Retry),
    #    ein LAUFENDER (queued/in_progress) ebenfalls.
    erg = entscheide(dt.datetime(2026, 10, 5, 7, 0, tzinfo=dt.timezone.utc),
                     slots, {"content-engine-v2.yml": [
                         lauf("rot", "2026-10-05T06:12:00Z", conclusion="failure"),
                         lauf("weg", "2026-10-05T06:15:00Z", status="in_progress"),
                     ]}, live_heute=0, minimum=2)
    pruefe(erg["slots"][0]["zustand"] == "bedient"
           and erg["slots"][0]["lauf"]["id"] == "rot",
           f"roter/laufender Lauf muss als bedient zählen: {erg['slots'][0]}")
    pruefe("content-engine-v2.yml" not in erg["nachholen"],
           f"kein Dispatch bei vorhandenem (rotem) Lauf: {erg['nachholen']}")

    # 7) Pro Workflow nur der ÄLTESTE verpasste Slot → genau ein Dispatch.
    erg = entscheide(dt.datetime(2026, 10, 5, 20, 30, tzinfo=dt.timezone.utc),
                     slots, {"content-engine-v2.yml": [],
                             "kadenz-endkontrolle.yml": []},
                     live_heute=1, minimum=2)
    pruefe(erg["nachholen"] == ["content-engine-v2.yml",
                                "kadenz-endkontrolle.yml"],
           f"ein Dispatch je Workflow erwartet: {erg['nachholen']}")

    # 8) Defizit-Fenster: nach letztem Slot + Gnadenfrist (22:20 UTC) mit
    #    offener Quote wird gemeldet – sind dagegen noch Slots nachholbar,
    #    wiegt der Nachhol-Dispatch schwerer (der nachgeholte Lauf meldet
    #    sein Defizit selbst).
    spaet = dt.datetime(2026, 10, 5, 22, 21, tzinfo=dt.timezone.utc)
    erg = entscheide(spaet, slots, laeufe, live_heute=1, minimum=2)
    pruefe(erg["defizit"] and erg["handlung"] == "nachholen",
           f"Defizit-Fenster mit nachholbarem Slot: Dispatch zuerst ({erg['handlung']})")
    alles_bedient = {**laeufe,
                     "content-engine-v2.yml": laeufe["content-engine-v2.yml"] + [
                         lauf("e2", "2026-10-05T18:00:00Z", conclusion="failure")],
                     "kadenz-endkontrolle.yml": laeufe["kadenz-endkontrolle.yml"] + [
                         lauf("k2", "2026-10-05T21:40:00Z", conclusion="failure")]}
    erg = entscheide(spaet, slots, alles_bedient, live_heute=1, minimum=2)
    pruefe(erg["handlung"] == "defizit-melden" and erg["defizit"],
           f"Defizit-Fenster nicht erkannt: {erg['handlung']}")
    vor_fenster = dt.datetime(2026, 10, 5, 22, 19, tzinfo=dt.timezone.utc)
    erg = entscheide(vor_fenster, slots, alles_bedient, live_heute=1, minimum=2)
    pruefe(erg["handlung"] != "defizit-melden" and not erg["defizit"],
           f"vor dem Fenster darf nicht gemeldet werden: {erg['handlung']}")

    # 9) Samstag ist Ruhetag – keine Forderung, egal was gelaufen ist.
    erg = entscheide(dt.datetime(2026, 10, 10, 12, 0, tzinfo=dt.timezone.utc),
                     slots_fuer_tag(samstag)[0], {}, live_heute=0, minimum=2)
    pruefe(erg["handlung"] == "ruhetag", f"Samstag ≠ Ruhetag: {erg}")

    # 10) Unverständliche Zeitstempel und unkopierbare Syntax.
    erg = entscheide(dt.datetime(2026, 10, 5, 7, 0, tzinfo=dt.timezone.utc),
                     slots, {"content-engine-v2.yml": [
                         {"id": "x", "status": "completed",
                          "conclusion": "success", "created_at": "Müll",
                          "url": "", "event": "schedule"}]},
                     live_heute=0, minimum=2)
    pruefe(erg["slots"][0]["zustand"] == "verpasst",
           f"Müll-Timestamp darf keinen Slot bedienen: {erg['slots'][0]}")
    pruefe(cron_zeiten_heute("*/20 * * * *", montag) == [],
           "Schritt-Syntax muss als nicht unterstützt gelten")
    pruefe(cron_zeiten_heute("10 6 5 10 *", montag) == [],
           "Datumgebundene cron-Syntax muss abgelehnt werden")
    pruefe(cron_zeiten_heute("10 6 * * 1,3,5", dt.date(2026, 10, 6)) == [],
           "Dienstag darf für Mo/Mi/Fr-cron nicht fällig sein")
    # Sonntag=0 in cron muss Python-Sonntag=6 sein (Kalenderwandlung).
    sonntag_cron = cron_zeiten_heute("10 6 * * 0", dt.date(2026, 10, 11))
    pruefe(sonntag_cron and sonntag_cron[0].weekday() == 6,
           f"cron-Sonntag (0) muss den Python-Sonntag treffen: {sonntag_cron}")

    # 11) Blindheit ist ein Befund: Publikationstag ohne bekannte Slots.
    erg = entscheide(jetzt, [], {}, live_heute=0, minimum=2)
    pruefe(erg["handlung"] == "blind",
           f"blinde Wache muss auffallen: {erg['handlung']}")

    # 12) Trockenlauf-Verdrahtung (rc=1 bei Befund, 0 im Ziel).
    erg = pruefen("org/repo", jetzt=jetzt, ohne_dispatch=True,
                  laeufe_je_workflow=laeufe, live_heute=1, minimum=2, slots=slots)
    pruefe(erg["rc"] == 1, f"Trockenlauf mit Befund muss rc=1: {erg['rc']}")
    erg = pruefen("org/repo", jetzt=jetzt, ohne_dispatch=True,
                  laeufe_je_workflow=laeufe, live_heute=2, minimum=2, slots=slots)
    pruefe(erg["rc"] == 0, f"Ziel erreicht muss rc=0: {erg['rc']}")
    erg = pruefen("", jetzt=jetzt, ohne_dispatch=False,
                  laeufe_je_workflow=laeufe, live_heute=1, minimum=2, slots=slots)
    pruefe(erg["rc"] == 1
           and all("nicht möglich" in d for d in erg["dispatches"]),
           f"ohne Repo darf nicht still nachgeholt werden: {erg['dispatches']}")

    # 13) Blinde Messung: Ist das Laufbuch nicht lesbar, zeigt der Bericht
    #     „unbekannt“ statt „verpasst“ und es wird NICHT blind dispatcht –
    #     ein vermeintlich verpasster Slot könnte längst laufen.
    def kaputter_lader(_repo, datei):
        if datei == "content-engine-v2.yml":
            raise RuntimeError("Laufbuch nicht lesbar")
        return laeufe.get(datei, [])

    erg = pruefen("org/repo", jetzt=jetzt, ohne_dispatch=False,
                  live_heute=1, minimum=2, slots=slots,
                  lade_laeufe_fn=kaputter_lader)
    pruefe(erg["rc"] == 1, f"blinde Messung muss laut sein (rc=1): {erg['rc']}")
    pruefe("content-engine-v2.yml" not in erg["nachholen"],
           f"blindes Nachholen verboten: {erg['nachholen']}")
    unbekannt = [s for s in erg["slots"]
                 if s["datei"] == "content-engine-v2.yml"
                 and s["zustand"] == "unbekannt"]
    verpasst_bleibt = [s for s in erg["slots"]
                       if s["datei"] == "content-engine-v2.yml"
                       and s["zustand"] == "verpasst"]
    pruefe(unbekannt and not verpasst_bleibt,
           f"blinde Slots müssen „unbekannt“ zeigen, nie „verpasst“: "
           f"{[(s['soll'][11:16], s['zustand']) for s in erg['slots'] if s['datei'] == 'content-engine-v2.yml']}")

    if fehler:
        print("🛑 slot_wache-Selbsttest FEHLGESCHLAGEN:")
        for f in fehler:
            print("  -", f)
        return 2
    print(f"✅ slot_wache-Selbsttest: {zaehler} Fälle grün (Soll-Slots aus "
          f"den echten Workflow-Dateien, Vorfall 05.10. nachgestellt, "
          f"Gnadenfrist-Grenze, roter/laufender Lauf, ein Dispatch je "
          f"Workflow, Defizit-Fenster, Ruhetag, Müll-Timestamp, "
          f"cron-Syntax-Kanone, Blindheit, Trockenlauf).")
    return 0


def main(argv=None) -> int:
    ap = __import__("argparse").ArgumentParser(
        description="Slot-Wache: zählt verpasste Content-Slots nach und holt sie")
    ap.add_argument("--pruefen", action="store_true")
    ap.add_argument("--ohne-dispatch", action="store_true",
                    help="nur zählen und melden – nichts nachholen (Trockenlauf)")
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    ap.add_argument("--ref", default=os.environ.get("GITHUB_REF_NAME", "main"),
                    help="Branch, auf dem der Nachhol-Lauf startet (default: main)")
    ap.add_argument("--md", action="store_true", help="Report als Markdown")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    if not args.pruefen:
        ap.error("entweder --pruefen oder --selftest")
    erg = pruefen(args.repo, ref=args.ref, ohne_dispatch=args.ohne_dispatch)
    if args.md:
        print(als_md(erg))
    else:
        print(erg["befund"])
        for d in erg.get("dispatches") or []:
            print(f"Dispatch: {d}")
        if erg.get("defizit_meldung"):
            print(f"Defizit: {erg['defizit_meldung']}")
        for w in erg.get("warnungen") or []:
            print(f"⚠️ {w}")
    return erg["rc"]


if __name__ == "__main__":
    sys.exit(main())
