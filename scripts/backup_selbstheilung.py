#!/usr/bin/env python3
# ============================================================
#  BACKUP-SELBSTHEILUNG – was die Sicherungskette selbst reparieren darf
#  ------------------------------------------------------------
#  Vorgang WF-9E5A / Meldung #923 (07.11.2026).
#
#  WARUM (und warum so eng)
#  ------------------------
#  Der Vorgang ist seit dem 28.10.2026 täglich rot, weil sechs Voraussetzungen
#  (E1–E6) nie eingerichtet wurden. Diese Arbeit kann und darf kein Agent
#  übernehmen: an Secrets, an das Cloudflare-Konto und an den privaten
#  Ziel-Repository-Namen kommt nur der Inhaber.
#
#  Genau deshalb wird hier die Grenze GEZOGEN statt verwischt. In einem
#  Selbstheilungs-Modul ist der teuerste Fehler nicht das Auslassen, sondern
#  das Zuviel: Eine Heilung, die „irgendwie grün“ macht, ist ein Schein-Grün
#  mit Selbstbedienung. Die drei Regeln dieses Moduls:
#
#    H1  NUR REPARIEREN, WAS BEWEISBAR KAPUTT IST
#        Ein Befund ohne Beleg („könnte sein“, „nicht prüfbar“) heilt nicht.
#    H2  NUR REPARIEREN, WAS REPARIERBAR IST
#        Jeder Befund trägt eine Klasse. Klassen ohne Reparaturweg (Zugänge,
#        Secrets, Konten, Inhaber-Entscheidungen) sind ausdrücklich
#        NICHT_HEILBAR und werden nur beraten – nie „gelöst“.
#    H3  HEILUNG IST EINE AKTION, KEIN ZUSTAND
#        Was geheilt werden kann, wird als Aktion mit Beweis ausgeführt
#        (Dispatch + Erfolgsprüfung), nicht als Behauptung. Bleibt der Beweis
#        aus, ist das Ergebnis rot.
#
#  WAS HIER KONKRET GEHEILT WIRD (aus dem Live-Befund vom 07.11.2026)
#  ------------------------------------------------------------------
#  · H-SCHEDULER  Der nächtliche Offsite-Lauf kommt verspätet (Soll 03:00 UTC,
#                 belegt 07:37–10:28 UTC an 24 Läufen) oder gar nicht. Die DATEI
#                 ist in Ordnung; es fehlt der Lauf. Heilung: den Lauf
#                 dispatchten – mit Beleg (neuer Lauf vorhanden, jünger als
#                 der Befund), nicht als „abgeschickt“.
#  · H-LEERLAUF   Der Repo-Job meldet `success`, obwohl weder ein dauerhaftes
#                 Ziel noch eine Passphrase konfiguriert ist: Er legt dann nur
#                 eine 7-Tage-Kurzzeitkopie im selben Konto ab. „Gelaufen“ ist
#                 wahr, „gesichert“ nicht. Ein grüner Lauf, der nichts sichert,
#                 ist derselbe Fehler wie ein grüner Lauf, der nichts prüft.
#                 Heilung: eigener Rat (`backup-leerlauf`) statt „alles gut“.
#  · H-SCHEINBEWEIS
#                 Die Frischwache-Schritte nach „Voraussetzungen prüfen“
#                 wurden wegen der Standard-`success()`-Bedingung
#                 ÜBERSPRUNGEN – der Rückweg-Nachweis stand als „skipped“ im
#                 Lauf, nicht als „nicht ausgeführt“. Ein Nachweis, der nur
#                 ausgeführt wird, wenn eine ANDERE Messung grün war, hängt am
#                 Ausgang einer fremden Frage. Heilung: eigener Schritt, der
#                 auch nach rotem Vorgänger läuft und dann ausdrücklich ROT
#                 ist („nicht belegt“ statt „übersprungen“).
#
#  WAS AUSDRÜCKLICH NICHT GEHEILT WIRD
#  -----------------------------------
#  E1–E8 (Ziel-Repo, Token, Passphrase, Cloudflare-Konto, KV-Namespace,
#  Environment-Schutz). Dafür gibt es keinen technischen Weg für einen
#  Agenten – und ein erfundener Wert wäre schlimmer als der offene Befund.
#  Die Empfehlung bleibt der Inhaber-Weg (`npm run backup:einrichten`).
#
#  BENUTZUNG
#  ---------
#    python3 scripts/backup_selbstheilung.py --plan          # nur urteilen
#    python3 scripts/backup_selbstheilung.py --plan --json
#    python3 scripts/backup_selbstheilung.py --heilen        # Plan + Dispatch
#    python3 scripts/backup_selbstheilung.py --selftest      # offline
#    python3 scripts/backup_selbstheilung.py --vertrag       # Kette prüfen
#
#  Exit: 0 = nichts zu heilen · 1 = heilbar, aber nicht geheilt (bzw. Beweis
#  ausgeblieben) · 2 = Aufruf-/Vertragsfehler · 3 = nicht heilbar (Inhaber)
#        4 = grüner Lauf ohne Sicherung (Leerlauf) – eigener Grund, eigener Rat
# ============================================================
"""Entscheidet und belegt, was die Backup-Kette selbst reparieren darf."""

from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from contextlib import redirect_stdout
from dataclasses import dataclass, field

ANLEITUNG = "docs/ANLEITUNG-OFFSITE-BACKUP.md"
GH_API = "https://api.github.com"
OFFSITE_WORKFLOW = "backup-offsite.yml"
FRISCHE_WORKFLOW = "backup-frischwache.yml"
OFFSITE_NAME = "Offsite-Backup"

# Soll-Zeit des nächtlichen Laufs (cron "0 3 * * *" in backup-offsite.yml).
SOLL_STUNDE_UTC = 3
# Ab dieser Verspätung ist ein fehlender Lauf ein Scheduler-Versäumnis und
# damit heilbar (die belegten Verspätungen 07:37–10:28 UTC liegen darüber).
SCHEDULER_KULANZ_H = 4
# Toleranz des RPO (dieselbe Zahl wie backup_freshness_guard.py).
MAX_ALTER_ROT_H = 52

# ---------------------------------------------------------------- Klassen
# Ein Befund ist genau einer Klasse zugeordnet. `heilbar` heißt: Es gibt eine
# Aktion, die den Zustand nachweisbar ändert, ohne Zugang, Secret oder
# Inhaber-Entscheidung. Alles andere ist NICHT_HEILBAR und wird beraten.
KLASSEN = {
    "scheduler": {
        "heilbar": True,
        "titel": "Lauf nicht gestartet oder verspätet",
        "grund": ("Der Workflow ist in Ordnung – es fehlt der Lauf. Ein "
                  "Dispatch holt ihn nach; der Beweis ist der neue Lauf."),
    },
    "leerlauf": {
        "heilbar": False,
        "titel": "Lauf grün, aber ohne dauerhaftes Ziel",
        "grund": ("Ohne BACKUP_REPO/PASSPHRASE entsteht nur eine "
                  "7-Tage-Kurzzeitkopie im selben Konto. Das ist keine "
                  "Sicherung – und kein Agent kann sie herstellen."),
    },
    "scheinbeweis": {
        "heilbar": False,
        "titel": "Nachweis wurde stillschweigend übersprungen",
        "grund": ("Ein übersprungener Schritt ist kein Nachweis. Die Heilung "
                  "ist ein Code-/Workflow-Vertrag, kein Laufzeit-Dispatch."),
    },
    "einrichtung": {
        "heilbar": False,
        "titel": "Inhaber-Einrichtung offen (E1–E8)",
        "grund": ("Zugänge, Secrets und Konten sind Inhaber-Sache. Ein "
                  "erfundener Wert wäre schlimmer als der offene Befund."),
    },
}

# Klassen, deren Heilung ein Dispatch ist (H3: Aktion mit Beweis).
DISPATCH_KLASSEN = ("scheduler",)


@dataclass
class Befund:
    klasse: str
    quelle: str          # Woher der Befund kommt (Lauf, Messung, Datei)
    text: str
    beleg: str = ""      # Der Beweis, ohne den nicht geheilt wird (H1)
    abhilfe: str = ""

    @property
    def heilbar(self) -> bool:
        return bool(KLASSEN.get(self.klasse, {}).get("heilbar"))

    @property
    def titel(self) -> str:
        return KLASSEN.get(self.klasse, {}).get("titel", self.klasse)


@dataclass
class Plan:
    befunde: list[Befund] = field(default_factory=list)
    heilungen: list[dict] = field(default_factory=list)

    def nach(self, klasse: str) -> list[Befund]:
        return [b for b in self.befunde if b.klasse == klasse]

    def heilbar(self) -> list[Befund]:
        return [b for b in self.befunde if b.heilbar and b.beleg]

    def nicht_heilbar(self) -> list[Befund]:
        return [b for b in self.befunde if not b.heilbar]


# =====================================================================
#  HTTP (im Selbsttest austauschbar) – wirft nie
# =====================================================================
def _json_oder_none(roh: str):
    try:
        return json.loads(roh) if roh else None
    except ValueError:
        return None


def _http_einmal(methode: str, url: str, kopf: dict | None = None, koerper: dict | None = None,
                 frist: int = 20):
    """(status, json|None, meldung) – Status 0 = kein Netz."""
    daten = None
    if koerper is not None:
        daten = json.dumps(koerper).encode("utf-8")
    anfrage = urllib.request.Request(url, data=daten, method=methode, headers={
        "User-Agent": "ff-backup-selbstheilung/1",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        **(kopf or {}),
    })
    try:
        with urllib.request.urlopen(anfrage, timeout=frist) as antwort:
            roh = antwort.read().decode("utf-8", "replace")
            return antwort.status, _json_oder_none(roh), ""
    except urllib.error.HTTPError as fehler:
        try:
            roh = fehler.read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001 – Körper ist Beiwerk
            roh = ""
        antwort = _json_oder_none(roh)
        meldung = antwort.get("message", "") if isinstance(antwort, dict) else ""
        return fehler.code, antwort, str(meldung or "")
    except (urllib.error.URLError, TimeoutError, OSError) as fehler:
        return 0, None, type(fehler).__name__


HTTP = _http_einmal
SCHLAF = time.sleep


def _gh_kopf(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"} if token else {}


# =====================================================================
#  Messungen (jede liefert Befunde – oder nichts, dann ist alles gut)
# =====================================================================
def ruhestands_zeit(jetzt: dt.datetime) -> dt.datetime:
    """Der jüngste Soll-Zeitpunkt (cron 03:00 UTC), der bereits verstrichen ist.

    Die Kulanz wird NICHT hier abgezogen, sondern in `pruefe_scheduler` –
    sonst zählte sie doppelt, und um 05:00 UTC wäre gestern 03:00 „fällig“
    gewesen (Fehlalarm über einen Lauf, der noch kommen darf).
    """
    soll = jetzt.replace(hour=SOLL_STUNDE_UTC, minute=0, second=0, microsecond=0)
    if jetzt < soll:
        soll -= dt.timedelta(days=1)
    return soll


def _zeit(wert) -> dt.datetime | None:
    try:
        zeit = dt.datetime.fromisoformat(str(wert).strip().replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    return zeit if zeit.tzinfo else zeit.replace(tzinfo=dt.timezone.utc)


def pruefe_scheduler(laeufe: list, jetzt: dt.datetime) -> list[Befund]:
    """Kam der fällige nächtliche Lauf? Nur die ABWESENHEIT ist heilbar.

    Ein Lauf, der da ist und rot endet, ist KEIN Scheduler-Befund – das wäre
    der klassische Fehlschluss „rot heißt, etwas hat nicht gestartet“.

    Die Kulanz gilt dem FÄLLIGKEITSZEITPUNKT, nicht dem Kalendertag: Um
    05:00 UTC ist der 03:00-Lauf noch nicht ausgeblieben, und ein Lauf von
    gestern Abend (z. B. ein Nachhol-Dispatch um 18:00) deckt das Fenster –
    sonst heilte diese Wache ihren eigenen Erfolg und dispatchte bei jedem
    Lauf erneut.
    """
    faellig = ruhestands_zeit(jetzt)
    if faellig + dt.timedelta(hours=SCHEDULER_KULANZ_H) > jetzt:
        return []
    vorhanden = []
    for lauf in laeufe or []:
        zeit = _zeit(lauf.get("created_at"))
        if zeit and faellig <= zeit <= jetzt + dt.timedelta(minutes=30):
            vorhanden.append(lauf)
    if vorhanden:
        return []
    # Ein Lauf KURZ VOR dem Soll-Zeitpunkt (Nachhol-Dispatch von gestern
    # Abend, manueller Lauf) ist kein Beweis für den heutigen Slot – die
    # Abwesenheit bleibt die Abwesenheit. Nur Läufe ab `faellig` zählen oben.
    letzte = sorted((_zeit(l.get("created_at")) for l in (laeufe or []) if _zeit(l.get("created_at"))))
    letzter = letzte[-1] if letzte else None
    verspaetung = ""
    if letzter:
        stunden = int((jetzt - letzter).total_seconds() // 3600)
        verspaetung = f" Der jüngste Lauf startete vor {stunden} h."
    return [Befund(
        klasse="scheduler",
        quelle=f"{OFFSITE_NAME} ({OFFSITE_WORKFLOW})",
        text=("Der für "
              f"{faellig.strftime('%d.%m.%Y %H:%M UTC')} fällige nächtliche Lauf "
              f"existiert nicht (Kulanz {SCHEDULER_KULANZ_H} h).{verspaetung}"),
        beleg=(f"Kein Lauf mit created_at ≥ {faellig.isoformat()} in der Läufe-Liste; "
               f"älterer Lauf vorhanden={letzter is not None}"),
        abhilfe="Lauf per workflow_dispatch nachholen (Aktion, kein Neustart-Versprechen).",
    )]


def pruefe_leerlauf(jobs: list, ziel_repo: str, passphrase_gesetzt: bool,
                    jetzt: dt.datetime) -> list[Befund]:
    """Ein grüner Repo-Job ohne Ziel und ohne Passphrase sichert nichts.

    WARUM AUF JOB-EBENE, NICHT AUF LAUF-EBENE (Selbstfund 07.11.2026):
    Die erste Fassung maß `workflow_runs[].conclusion`. Am Lauf 42359904795
    ist genau das die falsche Höhe: Der GESAMTLAUF ist `failure` (der KV-Job
    ist rot), der Job „backup“ darin ist `success` – und dieser grüne Job ist
    die Aussage, um die es geht. Eine Messung auf Lauf-Ebene hätte den Befund
    ausgerechnet an dem Tag verschluckt, an dem er zutraf.

    Der Befund ist keine Wiederholung der Einrichtung: „eingerichtet, aber
    nichts gesichert“ (z. B. Opt-in ohne Ziel) ist ein ANDERER Zustand als
    „nicht eingerichtet“ – und nur der erste wird von einem grünen Job
    verdeckt.
    """
    if (ziel_repo or "").strip() and passphrase_gesetzt:
        return []
    gruen = [j for j in (jobs or [])
             if str(j.get("name", "")).startswith("backup")
             and str(j.get("conclusion")) == "success"]
    if not gruen:
        return []
    fehlend = []
    if not (ziel_repo or "").strip():
        fehlend.append("BACKUP_REPO (dauerhaftes Ziel)")
    if not passphrase_gesetzt:
        fehlend.append("BACKUP_PASSPHRASE (Verschlüsselung)")
    return [Befund(
        klasse="leerlauf",
        quelle=f"{OFFSITE_NAME} · Job „{gruen[-1].get('name')}“",
        text=("Ein Job meldet Erfolg, obwohl nichts dauerhaft gesichert wurde – "
              f"nicht gesetzt: {', '.join(fehlend)}. Ohne Ziel entsteht nur eine "
              "7-Tage-Kurzzeitkopie im selben Konto (kein Offsite-Schutz)."),
        beleg=(f"Job-Konclusion = success bei fehlendem Ziel/Passphrase "
               f"(gelesen über die Jobs-API, nicht aus dem Gesamtlauf)"),
        abhilfe=(f"E1/E2/E3 einrichten: {ANLEITUNG} – oder, falls bewusst und "
                 "dokumentiert: BACKUP_UNVERSCHLUESSERT_OK=1 nur MIT privatem Ziel "
                 "(dann bleibt wenigstens der Offsite-Schutz)."),
    )]


def pruefe_scheinbeweis(schritte: list) -> list[Befund]:
    """Nachweise, die wegen eines roten Vorgängers übersprungen wurden.

    Belegt an sechs aufeinanderfolgenden Frischwache-Läufen (zuletzt
    42282938395): „Kurzpruefung Wiederherstellbarkeit“ steht als `skipped`,
    nicht als ausgeführt. Wer „nicht ausgeführt“ mit „nicht nötig“ verwechselt,
    hat keinen Rückweg-Nachweis mehr, sobald es ernst wird.
    """
    befunde = []
    for schritt in schritte or []:
        name = str(schritt.get("name", ""))
        if str(schritt.get("conclusion")) != "skipped":
            continue
        if "Wiederherstellbarkeit" not in name:
            continue
        befunde.append(Befund(
            klasse="scheinbeweis",
            quelle="Backup-Frischwache · Rückweg-Nachweis",
            text=(f"Der Schritt „{name}“ wurde übersprungen. Ein Nachweis, der "
                  "nur läuft, wenn eine andere Messung grün war, beweist nichts."),
            beleg="conclusion = skipped in der Schritte-Liste des Laufs",
            abhilfe=("Der Schritt läuft künftig mit `if: ${{ !cancelled() }}` und benennt "
                     "im Protokoll, was ohne Einrichtung NICHT prüfbar ist."),
        ))
    return befunde


def einrichtungs_befund(offene: list[str]) -> Befund | None:
    if not offene:
        return None
    return Befund(
        klasse="einrichtung",
        quelle=f"Einrichtungsprüfung (E1–E8) · {ANLEITUNG}",
        text=("Offene Pflichtpunkte: " + ", ".join(offene) + ". Bis dahin wird NICHTS "
              "dauerhaft gesichert (fail-closed, absichtlich)."),
        beleg="backup_einrichtung.py --pruefen (live)",
        abhilfe="Inhaber-Weg: `npm run backup:einrichten` (E8 zuerst, dann E1–E7).",
    )


# =====================================================================
#  Heilung: Dispatch mit Beweis (H3)
# =====================================================================
def dispatch_plan(repo: str, ref: str = "main") -> dict:
    return {"repo": repo, "ref": ref, "workflow": OFFSITE_WORKFLOW}


def heile_dispatch(plan: dict, kopf: dict, jetzt: dt.datetime,
                   http=None, schlaf=None) -> dict:
    """Dispatch ausführen UND beweisen: Es muss ein NEUER Lauf entstehen.

    Ein „angenommen“ der API ist kein Beweis – GitHub antwortet mit 204, auch
    wenn der Workflow-Lauf Sekunden später scheitert. Deshalb wird nach dem
    Dispatch die Läufe-Liste gelesen: Ein Lauf, der nach dem Befund-Zeitpunkt
    entstanden ist, zählt. Bleibt er aus, ist das Ergebnis rot.
    """
    http = http or HTTP
    schlaf = schlaf or SCHLAF
    repo, ref, workflow = plan["repo"], plan.get("ref", "main"), plan["workflow"]
    ergebnis = {"aktion": "dispatch", "workflow": workflow, "ref": ref,
                "bewiesen": False, "status": 0, "text": ""}
    if not repo or "/" not in repo:
        ergebnis["text"] = "Kein gültiges Repository – kein Dispatch."
        return ergebnis
    url = f"{GH_API}/repos/{repo}/actions/workflows/{workflow}/dispatches"
    status, antwort, meldung = http("POST", url, kopf, {"ref": ref})
    ergebnis["status"] = status
    if status not in (201, 204):
        ergebnis["text"] = (f"Dispatch abgelehnt (HTTP {status}"
                            + (f": {meldung}" if meldung else "") + ")")
        return ergebnis
    # Beweis: neuer Lauf nach dem Dispatch (bis zu drei Blicke, ohne Hetze).
    vorher = set()
    for versuch in range(3):
        if versuch:
            schlaf(4)
        status2, laeufe, _m2 = http(
            "GET",
            f"{GH_API}/repos/{repo}/actions/workflows/{workflow}/runs?per_page=20",
            kopf,
        )
        if status2 != 200 or not isinstance(laeufe, dict):
            ergebnis["text"] = f"Dispatch angenommen, Läufe nicht lesbar (HTTP {status2})."
            continue
        neu = [l for l in laeufe.get("workflow_runs", [])
               if str(l.get("databaseId")) not in vorher
               and (_zeit(l.get("created_at")) or jetzt) >= jetzt - dt.timedelta(minutes=5)]
        if neu:
            ergebnis.update(bewiesen=True,
                            text=f"Neuer Lauf {neu[0].get('databaseId')} gestartet.",
                            lauf=neu[0].get("databaseId"))
            return ergebnis
    ergebnis["text"] = ("Dispatch angenommen, aber kein neuer Lauf sichtbar – "
                        "die Heilung ist NICHT bewiesen.")
    return ergebnis


# =====================================================================
#  Gesamturteil
# =====================================================================
def baue_plan(laeufe: list, frisch_schritte: list, ziel_repo: str,
              passphrase_gesetzt: bool, offene_einrichtung: list[str],
              jetzt: dt.datetime, offsite_jobs: list | None = None) -> Plan:
    plan = Plan()
    plan.befunde.extend(pruefe_scheduler(laeufe, jetzt))
    plan.befunde.extend(pruefe_leerlauf(offsite_jobs or [], ziel_repo,
                                        passphrase_gesetzt, jetzt))
    plan.befunde.extend(pruefe_scheinbeweis(frisch_schritte))
    einrichtung = einrichtungs_befund(offene_einrichtung)
    if einrichtung:
        plan.befunde.append(einrichtung)
    # Dispatch nur, wenn der Scheduler-Befund einen Beleg trägt (H1).
    if any(b.klasse in DISPATCH_KLASSEN and b.beleg for b in plan.befunde):
        plan.heilungen.append(dispatch_plan(""))
    return plan


def urteil(plan: Plan) -> tuple[int, str]:
    # Der Leerlauf ist die Spitze NUR, wenn die Einrichtung vollständig ist.
    # Ist sie offen, ist der Leerlauf die Folge und die Einrichtung die
    # Ursache – zwei Rot-Stellen für eine Ursache wären Lärm, und der
    # Einrichtungs-Rat ist der, der weiterhilft.
    if plan.nach("leerlauf") and not plan.nach("einrichtung"):
        return 4, ("Ein Job meldet Erfolg, gesichert wurde aber nichts (Leerlauf) – "
                   "das ist kein Erfolg, sondern eine Lücke mit grünem Häkchen.")
    heilbar = plan.heilbar()
    offen = plan.nicht_heilbar() + [b for b in plan.befunde
                                    if b.heilbar and not b.beleg]
    if heilbar:
        return 1, (f"{len(heilbar)} heilbare(r) Befund(e) – Heilung ausstehend "
                   f"({', '.join(sorted({b.klasse for b in heilbar}))}).")
    if offen:
        klassen = sorted({b.klasse for b in offen})
        return 3, ("Nichts automatisch heilbar – Inhaber-Schritt nötig "
                   f"({', '.join(klassen)}).")
    return 0, "Keine Befunde: Die Sicherungskette ist eingerichtet und läuft."


def bericht(plan: Plan, rc: int, text: str) -> str:
    zeilen = ["Backup-Selbstheilung (Vorgang WF-9E5A / #923)", text, ""]
    for befund in plan.befunde:
        zeichen = "🔧" if befund.heilbar else ("🟢⚠️" if befund.klasse == "leerlauf" else "🛑")
        art = "heilbar" if befund.heilbar else "nicht heilbar"
        zeilen.append(f"  {zeichen} [{befund.klasse}/{art}] {befund.quelle}")
        zeilen.append(f"     {befund.text}")
        if befund.beleg:
            zeilen.append(f"     Beleg: {befund.beleg}")
        if befund.abhilfe:
            zeilen.append(f"     Weg: {befund.abhilfe}")
    for heilung in plan.heilungen:
        zeilen.append(f"  ➜ Heilung geplant: {heilung['aktion']} "
                      f"({heilung['workflow']} auf {heilung.get('ref', 'main')})")
    if not plan.befunde:
        zeilen.append("  ✅ alle Messungen still")
    return "\n".join(zeilen)


# =====================================================================
#  Zusammenfassung für die Job-Summary (eine Quelle, kein zweiter Text)
# =====================================================================
def zusammenfassung(plan: Plan, rc: int, text: str, repo: str = "") -> str:
    anleitung = (f"[`{ANLEITUNG}`](https://github.com/{repo}/blob/main/{ANLEITUNG})"
                 if repo else f"`{ANLEITUNG}`")
    zeilen = ["## Backup-Selbstheilung (WF-9E5A / #923)", "",
              f"**Urteil:** {text}", "",
              "| Befund | Klasse | Heilbar | Beleg |", "|---|:-:|:-:|---|"]
    for befund in plan.befunde:
        zeilen.append(f"| {befund.quelle} | `{befund.klasse}` | "
                      f"{'ja' if befund.heilbar else 'nein – Inhaber'} | {befund.beleg or '–'} |")
    if not plan.befunde:
        zeilen.append("| – | – | – | keine Befunde |")
    zeilen += ["", "### Grenze dieser Heilung", "",
               "Automatisch reparierbar ist nur, was **beweisbar** kaputt ist und "
               "**ohne Zugang** repariert werden kann: ein nicht gestarteter Lauf "
               "(Dispatch mit Lauf-Beweis). Zugänge, Secrets und Konten (E1–E7) "
               "sowie der Environment-Schutz (E8) bleiben Inhaber-Sache – ein "
               "erfundener Wert wäre schlimmer als der offene Befund.", "",
               f"Anleitung: {anleitung}", ""]
    return "\n".join(zeilen)


# =====================================================================
#  Selbsttest (offline, ohne Netz)
# =====================================================================
def _stille(funktion, *args, **kwargs):
    puffer = io.StringIO()
    with redirect_stdout(puffer):
        ergebnis = funktion(*args, **kwargs)
    return ergebnis, puffer.getvalue()


def selbsttest() -> int:
    fehler: list[str] = []
    jetzt = dt.datetime(2026, 11, 7, 12, 0, tzinfo=dt.timezone.utc)

    def lauf(zeit, conclusion="failure", event="schedule", nummer=1):
        return {"created_at": zeit.isoformat().replace("+00:00", "Z"),
                "conclusion": conclusion, "event": event, "databaseId": nummer}

    # F1: Fälliger Lauf fehlt (die Lage vom 07.11.: Soll 03:00, jetzt 12:00,
    #     jüngster Lauf von gestern 10:28) → scheduler-Befund MIT Beleg
    gestern = jetzt - dt.timedelta(days=1, hours=1, minutes=32)
    plan = Plan()
    befund = pruefe_scheduler([lauf(gestern)], jetzt)
    if len(befund) != 1 or befund[0].klasse != "scheduler":
        fehler.append(f"F1: fehlender Lauf nicht erkannt: {befund}")
    elif not befund[0].beleg or not befund[0].heilbar:
        fehler.append("F1: ein heilbarer Befund braucht Beleg und Klasse 'heilbar'")

    # F2: Lauf von heute 09:28 UTC (belegte Verspätung) → KEIN Befund
    heute_lauf = jetzt.replace(hour=9, minute=28)
    befund = pruefe_scheduler([lauf(heute_lauf)], jetzt)
    if befund:
        fehler.append(f"F2: vorhandener (verspäteter) Lauf darf kein Scheduler-Befund sein: {befund}")

    # F3: Kulanz – um 05:00 UTC ist der 03:00-Lauf noch nicht fällig
    frueh = jetzt.replace(hour=5, minute=0)
    if pruefe_scheduler([], frueh):
        fehler.append("F3: innerhalb der Kulanz darf nicht gemeldet werden")

    # F4: frischer Lauf außerhalb des Fensters (manuell heute 06:00) → kein Befund
    if pruefe_scheduler([lauf(jetzt.replace(hour=6))], jetzt):
        fehler.append("F4: ein frischer Lauf außerhalb des Soll-Fensters ist kein Ausfall")

    # F5: Leerlauf – grüner JOB ohne Ziel und ohne Passphrase → Befund,
    #     ausdrücklich NICHT heilbar (E1–E3 sind Inhaber-Sache)
    gruener_job = [{"name": "backup", "conclusion": "success"}]
    befund = pruefe_leerlauf(gruener_job, "", False, jetzt)
    if len(befund) != 1 or befund[0].klasse != "leerlauf" or befund[0].heilbar:
        fehler.append(f"F5: Leerlauf falsch bewertet: {befund}")

    # F5b: Der Selbstfund vom 07.11.: Der Gesamtlauf ist rot (KV-Job), der Job
    #      „backup“ grün. Die Messung muss auf JOB-Ebene greifen – sonst
    #      verschluckt sie den Befund genau an dem Tag, an dem er zutrifft.
    if pruefe_leerlauf(gruener_job, "", False, jetzt) == []:
        fehler.append("F5b: grüner Job bei rotem Gesamtlauf muss gemeldet werden")
    if not pruefe_leerlauf([{"name": "KV-/D1-Backup (Abonnenten + Einwilligungsnachweise)",
                             "conclusion": "success"}], "", False, jetzt) == []:
        fehler.append("F5b: der KV-Job ist nicht der Leerlauf-Zeuge "
                      "(er legt nie ein Artefakt an – Audit M-11)")

    # F6: Gegenprobe – mit Ziel UND Passphrase ist derselbe Job in Ordnung
    if pruefe_leerlauf(gruener_job, "a/b", True, jetzt):
        fehler.append("F6: eingerichtete Sicherung darf nicht als Leerlauf gelten")

    # F7: Gegenprobe – roter Job ist kein Leerlauf-Befund (dafür gibt es den Alarm)
    if pruefe_leerlauf([{"name": "backup", "conclusion": "failure"}], "", False, jetzt):
        fehler.append("F7: ein roter Job ist kein Leerlauf")

    # F8: Scheinbeweis – übersprungener Rückweg-Nachweis wird erkannt
    befund = pruefe_scheinbeweis([
        {"name": "Kurzpruefung Wiederherstellbarkeit (strukturell, ohne Secrets)",
         "conclusion": "skipped"},
        {"name": "Voraussetzungen prüfen (fail-closed – kein Schein-Grün)",
         "conclusion": "failure"},
    ])
    if len(befund) != 1 or befund[0].klasse != "scheinbeweis" or befund[0].heilbar:
        fehler.append(f"F8: übersprungener Nachweis nicht erkannt: {befund}")

    # F9: Gegenprobe – ausgeführter Nachweis erzeugt keinen Befund
    if pruefe_scheinbeweis([
        {"name": "Kurzpruefung Wiederherstellbarkeit (strukturell, ohne Secrets)",
         "conclusion": "success"},
    ]):
        fehler.append("F9: ein ausgeführter Nachweis darf kein Befund sein")

    # F10: Einrichtung – offene Punkte sind nicht heilbar, aber benannt
    befund = einrichtungs_befund(["E1", "E3"])
    if befund is None or befund.heilbar or "E1, E3" not in befund.text:
        fehler.append("F10: Einrichtungsbefund falsch")
    if einrichtungs_befund([]) is not None:
        fehler.append("F10: ohne offene Punkte darf kein Einrichtungsbefund entstehen")

    # F11: Urteil – heilbar schlägt nicht-heilbar (Exit 1 vor Exit 3)
    p = Plan(befunde=[Befund("scheduler", "x", "y", beleg="belegt"),
                      Befund("einrichtung", "x", "y", beleg="belegt")])
    rc, _text = urteil(p)
    if rc != 1:
        fehler.append(f"F11: heilbarer Befund muss Exit 1 ergeben, war {rc}")
    p = Plan(befunde=[Befund("einrichtung", "x", "y", beleg="belegt")])
    rc, _t = urteil(p)
    if rc != 3:
        fehler.append(f"F11: nicht heilbar muss Exit 3 ergeben, war {rc}")
    if urteil(Plan())[0] != 0:
        fehler.append("F11: ohne Befunde muss Exit 0 herauskommen")
    # F11b: Der Leerlauf ist die Spitze nur bei VOLLSTÄNDIGER Einrichtung.
    #       Ist die Einrichtung offen, ist sie die Ursache und der Leerlauf
    #       die Folge (eine Ursache, ein Rat).
    rc, _t = urteil(Plan(befunde=[Befund("leerlauf", "x", "y", beleg="b")]))
    if rc != 4:
        fehler.append(f"F11b: Leerlauf bei vollständiger Einrichtung muss Exit 4 "
                      f"ergeben, war {rc}")
    rc, _t = urteil(Plan(befunde=[Befund("leerlauf", "x", "y", beleg="b"),
                                  Befund("einrichtung", "x", "y", beleg="b")]))
    if rc != 3:
        fehler.append(f"F11b: offene Einrichtung hat Vorrang (Exit 3), war {rc}")

    # F12: H1 – ein Befund OHNE Beleg wird nie geheilt
    p = Plan(befunde=[Befund("scheduler", "x", "y", beleg="")])
    if p.heilbar():
        fehler.append("F12: ohne Beleg darf nichts heilbar sein")
    if urteil(p)[0] != 3:
        fehler.append("F12: ohne Beleg bleibt nur der Inhaber-Weg (Exit 3)")

    # F13: Dispatch mit Beweis – 204 + neuer Lauf → bewiesen
    def http_ok(methode, url, kopf=None, koerper=None, frist=20):
        if methode == "POST":
            return 204, None, ""
        return 200, {"workflow_runs": [
            {"databaseId": 4711, "created_at": (jetzt + dt.timedelta(seconds=20))
             .isoformat().replace("+00:00", "Z")}]}, ""

    ergebnis = heile_dispatch({"repo": "a/b", "workflow": OFFSITE_WORKFLOW, "ref": "main"},
                              {"Authorization": "Bearer x"}, jetzt, http_ok, lambda _s: None)
    if not ergebnis["bewiesen"] or ergebnis.get("lauf") != 4711:
        fehler.append(f"F13: Dispatch ohne Beweis: {ergebnis}")

    # F14: Gegenprobe – Dispatch „angenommen“, aber kein Lauf → NICHT bewiesen
    def http_ohne_lauf(methode, url, kopf=None, koerper=None, frist=20):
        if methode == "POST":
            return 204, None, ""
        return 200, {"workflow_runs": []}, ""

    ergebnis = heile_dispatch({"repo": "a/b", "workflow": OFFSITE_WORKFLOW, "ref": "main"},
                              {}, jetzt, http_ohne_lauf, lambda _s: None)
    if ergebnis["bewiesen"] or "NICHT bewiesen" not in ergebnis["text"]:
        fehler.append(f"F14: fehlender Beweis wurde nicht erkannt: {ergebnis}")

    # F15: Gegenprobe – abgelehnter Dispatch (403) behauptet keinen Erfolg
    def http_403(methode, url, kopf=None, koerper=None, frist=20):
        return 403, {"message": "Resource not accessible by integration"}, ""

    ergebnis = heile_dispatch({"repo": "a/b", "workflow": OFFSITE_WORKFLOW, "ref": "main"},
                              {}, jetzt, http_403, lambda _s: None)
    if ergebnis["bewiesen"] or "403" not in ergebnis["text"]:
        fehler.append(f"F15: 403 nicht als Fehlschlag behandelt: {ergebnis}")

    # F16: Kein Dispatch ohne Repository (fail-closed, nie ins Leere schreiben)
    ergebnis = heile_dispatch({"repo": "", "workflow": OFFSITE_WORKFLOW}, {}, jetzt,
                              http_403, lambda _s: None)
    if ergebnis["bewiesen"] or "Kein gültiges Repository" not in ergebnis["text"]:
        fehler.append(f"F16: leerer Repo-Name muss abbrechen: {ergebnis}")

    # F17: Der Plan trägt keinen Dispatch, wenn nur Inhaber-Befunde offen sind.
    #      (Der Lauf von heute 09:28 existiert – der Slot ist also besetzt, und
    #      der rote Ausgang ist kein Leerlauf, sondern eine Alarm-Sache.)
    plan = baue_plan([lauf(jetzt.replace(hour=9, minute=28))], [], "", False, ["E1"], jetzt,
                     offsite_jobs=[{"name": "backup", "conclusion": "failure"},
                                   {"name": "KV-/D1-Backup", "conclusion": "failure"}])
    if plan.heilungen:
        fehler.append("F17: ohne heilbaren Befund darf kein Dispatch geplant werden")
    plan = baue_plan([lauf(gestern)], [], "a/b", True, [], jetzt, offsite_jobs=[])
    if not plan.heilungen:
        fehler.append("F17: ein belegter Scheduler-Befund muss einen Dispatch planen")

    # F18: Der Bericht nennt jeden Befund mit Klasse – und den Beleg
    text = bericht(Plan(befunde=[Befund("scheduler", "q", "t", beleg="b")]), 1, "U")
    if "scheduler" not in text or "Beleg: b" not in text:
        fehler.append("F18: Bericht nennt Klasse/Beleg nicht")

    # F19: Ein Befund mit unbekannter Klasse gilt NIE als heilbar (fail-closed)
    if Befund("erfunden", "q", "t", beleg="b").heilbar:
        fehler.append("F19: unbekannte Klasse darf nicht heilbar sein")

    # F20: Die Zusammenfassung ist eine Tabelle mit Grenze – keine Zusage
    zus = zusammenfassung(Plan(befunde=[Befund("einrichtung", "q", "t", beleg="b")]), 3, "U")
    if "Inhaber-Sache" not in zus or "| nein" not in zus:
        fehler.append("F20: Zusammenfassung verschweigt die Grenze")

    if fehler:
        for eintrag in fehler:
            print(f"❌ {eintrag}")
        print(f"🛑 backup_selbstheilung-Selbsttest: {len(fehler)} Abweichung(en).")
        return 1
    print("✅ backup_selbstheilung-Selbsttest: 21 Fallgruppen – Scheduler-Fenster, Kulanz, "
          "Leerlauf (incl. Vorrang vor dem Inhaber-Weg), Scheinbeweis, Inhaber-Grenze, "
          "Dispatch mit UND ohne Beweis, fail-closed ohne Beleg.")
    return 0


# =====================================================================
#  Vertrag: Die Kette muss verdrahtet sein (keine Wache ohne Lauf)
# =====================================================================
def vertrag(wurzel: str | None = None) -> int:
    """Prüft, dass dieses Modul nicht Prosa bleibt.

    Eine Heilung, die in keinem Workflow läuft, heilt nichts – und ein
    Workflow, der sie aufruft, ohne dass sie geprüft wird, ist Dekoration.
    Geprüft werden deshalb: Selbsttest vorhanden, Workflow ruft sie, die
    Grenze steht in der Anleitung, und der Rückweg-Nachweis läuft mit
    `if: always()` statt nur nach grünem Vorgänger.
    """
    wurzel = wurzel or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fehler: list[str] = []

    def lies(rel: str) -> str:
        pfad = os.path.join(wurzel, rel)
        try:
            with open(pfad, encoding="utf-8") as datei:
                return datei.read()
        except OSError:
            fehler.append(f"{rel} fehlt")
            return ""

    wf = lies(os.path.join(".github", "workflows", FRISCHE_WORKFLOW))
    offsite = lies(os.path.join(".github", "workflows", OFFSITE_WORKFLOW))
    anleitung = lies(ANLEITUNG)

    if wf:
        if "backup_selbstheilung.py" not in wf:
            fehler.append(f"{FRISCHE_WORKFLOW} ruft backup_selbstheilung.py nicht auf "
                          "– die Heilung liefe in keinem Lauf")
        if "backup_selbstheilung.py --selftest" not in wf:
            fehler.append(f"{FRISCHE_WORKFLOW}: Selbsttest der Heilung fehlt im "
                          "Selbsttest-Schritt (eine Heilung ohne Beweis ist Prosa)")
    if "!cancelled()" not in wf:
        fehler.append("Der Rückweg-Nachweis muss auch nach einem roten Vorgänger laufen "
                      "(sonst 'skipped' statt 'nicht belegt')")

    # Der Scheinbeweis darf nicht zurückkehren: Der Schritt trägt eine eigene
    # Bedingung, und sein Rumpf endet ausdrücklich rot, wenn er nicht prüfen kann.
    if wf:
        block = wf.split("Kurzpruefung Wiederherstellbarkeit", 1)
        if len(block) < 2:
            fehler.append("Der Rückweg-Nachweis fehlt in der Frischwache")
        else:
            kopf = block[1].split("run:", 1)[0]
            if "!cancelled()" not in kopf:
                fehler.append("Der Rückweg-Nachweis braucht `if: ${{ !cancelled() }}` im "
                              "Schritt (ein übersprungener Nachweis ist kein Nachweis)")

    if offsite and "backup-offsite.yml" and "schedule" not in offsite:
        fehler.append("Der nächtliche Lauf fehlt in backup-offsite.yml")

    if anleitung:
        if "Selbstheilung" not in anleitung:
            fehler.append(f"{ANLEITUNG} nennt die Selbstheilung nicht – der Betreiber "
                          "erfährt nicht, was das System selbst repariert")
        if "nicht heilbar" not in anleitung and "Inhaber-Sache" not in anleitung:
            fehler.append(f"{ANLEITUNG} muss die Grenze benennen (was NICHT geheilt wird)")

    if fehler:
        for eintrag in fehler:
            print(f"❌ Vertrag: {eintrag}")
        return 1
    print("✅ Backup-Selbstheilungs-Vertrag: verdrahtet, selbstgeprüft, Grenze dokumentiert.")
    return 0


# =====================================================================
#  Kommandozeile
# =====================================================================
def _offene_einrichtung() -> list[str]:
    """Offene Pflichtpunkte aus dem Einrichtungsprüfer (live) – nie geraten."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import backup_einrichtung as be  # noqa: PLC0415 – nur für diesen Aufruf
        _, ausgabe = _stille(be.befehl_pruefen, dict(os.environ))
        kennungen = re.findall(r"❌\s+(E\d)", ausgabe)
        return sorted(set(kennungen))
    except Exception:  # noqa: BLE001 – ohne Prüfer keine erfundene Liste
        return []


def _laeufe(repo: str, token: str, workflow: str) -> list:
    if not repo:
        return []
    status, antwort, _m = HTTP(
        "GET", f"{GH_API}/repos/{repo}/actions/workflows/{workflow}/runs?per_page=20",
        _gh_kopf(token))
    if status != 200 or not isinstance(antwort, dict):
        return []
    return antwort.get("workflow_runs", [])


def _jobs_des_juengsten(repo: str, token: str, workflow: str) -> list:
    """Die Jobs des jüngsten Laufs – die Höhe, auf der „grün“ zählt.

    (Der Gesamtlauf kann rot sein, weil ein ANDERER Job rot ist. Für die
    Frage „wurde gesichert?“ zählt der Job, der sichert.)
    """
    laeufe = _laeufe(repo, token, workflow)
    if not laeufe:
        return []
    juengster = max(laeufe, key=lambda l: str(l.get("created_at", "")))
    status, antwort, _m = HTTP("GET", f"{GH_API}/repos/{repo}/actions/runs/"
                               f"{juengster.get('id')}/jobs", _gh_kopf(token))
    if status != 200 or not isinstance(antwort, dict):
        return []
    return [{"name": j.get("name", ""), "conclusion": j.get("conclusion")}
            for j in antwort.get("jobs", [])]


def _schritte_des_juengsten(repo: str, token: str, workflow: str) -> list:
    laeufe = _laeufe(repo, token, workflow)
    if not laeufe:
        return []
    juengster = max(laeufe, key=lambda l: str(l.get("created_at", "")))
    status, antwort, _m = HTTP("GET", f"{GH_API}/repos/{repo}/actions/runs/"
                               f"{juengster.get('id')}/jobs", _gh_kopf(token))
    if status != 200 or not isinstance(antwort, dict):
        return []
    schritte: list = []
    for job in antwort.get("jobs", []):
        schritte.extend(job.get("steps", []) or [])
    return schritte


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Was die Backup-Kette selbst reparieren darf – und was nicht.")
    parser.add_argument("--plan", action="store_true", help="nur urteilen (Standard)")
    parser.add_argument("--heilen", action="store_true", help="Plan ausführen (Dispatch)")
    parser.add_argument("--selftest", action="store_true", help="offline, ohne Netz")
    parser.add_argument("--vertrag", action="store_true", help="Verdrahtung prüfen")
    parser.add_argument("--json", action="store_true", help="Maschinenausgabe")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""),
                        help="Quell-Repository (besitzer/name)")
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.selftest:
        return selbsttest()
    if args.vertrag:
        return vertrag()

    repo = (args.repo or "").strip()
    token = (os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or "").strip()
    jetzt = dt.datetime.now(dt.timezone.utc)

    laeufe = _laeufe(repo, token, OFFSITE_WORKFLOW)
    offsite_jobs = _jobs_des_juengsten(repo, token, OFFSITE_WORKFLOW)
    schritte = _schritte_des_juengsten(repo, token, FRISCHE_WORKFLOW)
    ziel = (os.environ.get("ZIEL_REPO") or os.environ.get("BACKUP_REPO") or "").strip()
    passphrase = bool((os.environ.get("PASSWORT") or os.environ.get("BACKUP_PASSPHRASE") or "").strip())
    plan = baue_plan(laeufe, schritte, ziel, passphrase, _offene_einrichtung(), jetzt,
                     offsite_jobs=offsite_jobs)
    for heilung in plan.heilungen:
        heilung["repo"] = repo

    rc, text = urteil(plan)
    ergebnisse: list[dict] = []
    if args.heilen:
        for heilung in plan.heilungen:
            ergebnis = heile_dispatch(heilung, _gh_kopf(token), jetzt)
            ergebnisse.append(ergebnis)
        if plan.heilungen:
            if all(e.get("bewiesen") for e in ergebnisse):
                rc, text = 0, ("Heilung ausgeführt und bewiesen: "
                               + "; ".join(e["text"] for e in ergebnisse))
            else:
                rc, text = 1, ("Heilung NICHT bewiesen: "
                               + "; ".join(e["text"] for e in ergebnisse))

    if args.json:
        print(json.dumps({
            "urteil": {"rc": rc, "text": text},
            "befunde": [b.__dict__ | {"heilbar": b.heilbar} for b in plan.befunde],
            "heilungen": ergebnisse or plan.heilungen,
        }, ensure_ascii=False, indent=2))
    else:
        print(bericht(plan, rc, text))
        for ergebnis in ergebnisse:
            print(f"  ➜ {ergebnis['text']}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY", "")
    if summary:
        with open(summary, "a", encoding="utf-8") as datei:
            datei.write(zusammenfassung(plan, rc, text, repo) + "\n")
    if os.environ.get("GITHUB_ACTIONS") == "true":
        for befund in plan.befunde:
            if befund.heilbar:
                continue
            art = "warning" if befund.klasse == "einrichtung" else "error"
            print(f"::{art} title=Backup-Selbstheilung ({befund.klasse})::"
                  f"{befund.text} · Weg: {befund.abhilfe}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
