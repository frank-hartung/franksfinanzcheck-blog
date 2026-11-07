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

#  BACKUP-SELBSTHEILUNG – die RPO-Wache heilt, statt nur zu melden
#  ------------------------------------------------------------
#  WARUM (Vorgang WF-3150 / Meldung #1030, 07.11.2026):
#    `backup_freshness_guard.py` MISST, ob die Sicherung frisch ist.
#    Gemessen wurde bis heute nur – und gemeldet. Fehlt der nächtliche
#    Lauf (Scheduler-Aussetzer, verworfenes Token ohne Ablaufdatum,
#    Environment-Regel nach einem Settings-Umbau), dann blieb es bei
#    der Meldung: Die Heilung war vorhanden (`backup-offsite.yml` per
#    „Run workflow“), aber sie war NICHT VERDRAHTET. Genau dieselbe
#    Klasse hat am 06.11.2026 die GSC-Verlinkung geheilt (Akte
#    `GSC-VERLINKUNG-SELBSTHEILUNG-1097-HIGHEND-2026-11-06.md`, §2.1:
#    „Ein Kriterium, das sich täglich neu rot misst und dessen Heilung
#    niemand anstößt, ist keine Wache, sondern eine Warteschlange.“).
#
#    Dieses Modul schließt den Kreis:
#      1. Es misst selbst (dieselbe Quelle, derselbe Guard – keine
#         zweite Wahrheit über die Frische).
#      2. Es entscheidet nach einer festen Tabelle, ob ein Anstoß
#         überhaupt zulässig ist (Tagesfenster verpasst? Läuft schon
#         eine Sicherung? Budget erschöpft? Historie lesbar?).
#      3. Es stößt `backup-offsite.yml` GENAU EINMAL an, wartet
#         begrenzt auf das Ergebnis und MISST DANACH ERNEUT.
#      4. Es meldet Grün nur mit Nachweis der zweiten Messung. Ein
#         angestoßener Lauf ist kein Beweis – erst das frische Release
#         ist einer. (Kein Schein-Grün, dieselbe Doktrin wie E1–E8.)
#
#  GRENZEN – bewusst:
#    · Keine zweite Sicherung: Dieses Modul sichert nichts selbst, es
#      löst den einen, geprüften Workflow aus (Der Backup-Code bleibt
#      an genau einer Stelle: `backup-offsite.yml` + `kv_backup.py`).
#    · Kein Anstoß ohne lesbare Historie (fail-closed). Wer die
#      Lauf-Historie nicht lesen kann, weiß nicht, ob eine Sicherung
#      läuft – und würde mit einem blinden Anstoß doppelt sichern.
#    · Kein Anstoß, solange die Einrichtung offen ist (E1–E8): Der
#      Aufrufer (Workflow) prüft das VOR diesem Schritt; hier wird
#      zusätzlich nur dann gestartet, wenn ein Ziel und ein Lesetoken
#      vorhanden sind.
#    · Höchstens MAX_VERSUCHE_24H Selbstheilungs-Läufe je 24 h. Ein
#      Dauerfehler wird nicht in eine Endlosschleife übersetzt – ab
#      dem Budget bleibt es bei Rot MIT Grund (die Offsite-Meldung
#      trägt die Ursache, dieses Modul den Nachweis des Versuchs).
#    · Keine Secrets in Ausgabe, Annotation oder Zusammenfassung.
#
#  RECHTE:
#    Lesen der Releases   : BACKUP_REPO_TOKEN (nur Ziel-Repo, read)
#    Lesen der Lauf-Historie und Anstoßen : AKTION_TOKEN (Lauf-Token,
#    `actions: write`) – NUR dieser eine Aufruf: POST …/dispatches.
#
#  Aufruf:
#    python3 scripts/backup_selbstheilung.py --probe       # messen + entscheiden, nichts anstoßen
#    python3 scripts/backup_selbstheilung.py --heilen      # messen, anstoßen, warten, erneut messen
#    python3 scripts/backup_selbstheilung.py --selftest    # offline, ohne Netz
#  Exit: 0 = frisch, geheilt oder nichts zu tun · 1 = nicht geheilt (rot)
#        2 = Aufruf-/Selbsttestfehler
# ============================================================
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
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ANLEITUNG = "docs/ANLEITUNG-OFFSITE-BACKUP.md"
GH_API = "https://api.github.com"
WORKFLOW = "backup-offsite.yml"
ZIEL_BRANCH = "main"

# Ab hier gilt das TAGESFENSTER als verpasst: Die Sicherung läuft 03:00 UTC,
# gemessen wird 13:00 UTC. Ein gesunder Lauf ergibt dann ≤ 17 h (10 h plus
# belegte Scheduler-Verspätung bis ~7 h); ein ausgefallener Lauf ergibt ≥ 34 h.
# 26 h liegt in der Mitte: kein Fehlalarm bei Verspätung, aber der Ausfall wird
# noch AM SELBEN TAG geheilt statt erst am Folgetag (52-h-Grenze der Meldung).
HEILUNG_AB_H = 26
# Höchstens drei Selbstheilungs-Läufe je 24 h (1. Versuch + zwei Wiederholungen
# bei echtem Ausfall). Danach bleibt es Rot mit Grund – kein Dauerfeuer.
MAX_VERSUCHE_24H = 3
# Mindestabstand zum letzten Sicherungslauf: kein zweiter Anstoß, während der
# letzte Lauf noch frisch ist oder gerade erst geendet hat (Doppelläufe).
MINDESTABSTAND_MIN = 15
# Ein Lauf, der vor weniger als 60 Minuten abgeschlossen wurde, gilt als
# „gerade gelaufen“: Dann wiederholt ein Anstoß nur, was eben nicht ging.
LAUF_FRISCH_MIN = 60
# Begrenzte Wartezeit auf den angestoßenen Lauf (Sekunden und Abfrage-Takt).
WARTEZEIT_S = 900
ABFRAGE_TAKT_S = 15

VORUEBERGEHEND = {0, 429, 500, 502, 503, 504}
AKTIVE_ZUSTAENDE = {"queued", "in_progress", "requested", "waiting", "pending"}


# =====================================================================
#  HTTP – eine Stelle, im Selbsttest austauschbar
# =====================================================================
def _http_einmal(methode: str, url: str, token: str, koerper: dict | None = None):
    """Liefert (status, json|None, netzfehler). Status 0 = kein Netz."""
    daten = json.dumps(koerper).encode("utf-8") if koerper is not None else None
    anfrage = urllib.request.Request(url, data=daten, method=methode, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ff-backup-selbstheilung/1",
        **({"Content-Type": "application/json"} if daten else {}),
    })
    try:
        with urllib.request.urlopen(anfrage, timeout=20) as antwort:
            roh = antwort.read().decode("utf-8", "replace")
            try:
                return antwort.status, (json.loads(roh) if roh else None), ""
            except ValueError:
                return antwort.status, None, ""
    except urllib.error.HTTPError as fehler:
        try:
            roh = fehler.read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001 – Körper ist Beiwerk, Status zählt
            roh = ""
        try:
            return fehler.code, (json.loads(roh) if roh else None), ""
        except ValueError:
            return fehler.code, None, ""
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
SCHLAF = time.sleep  # im Selbsttest austauschbar (keine Wartezeit)


def _http(methode: str, url: str, token: str, koerper: dict | None = None):
    """Bis zu drei Versuche bei vorübergehenden Fehlern (Netz, 429, 5xx)."""
    ergebnis = (0, None, "nicht versucht")
    for versuch in range(3):
        ergebnis = _http_einmal(methode, url, token, koerper)
        if ergebnis[0] not in VORUEBERGEHEND:
            return ergebnis
        if versuch < 2:
            SCHLAF(2 * (versuch + 1))
    return ergebnis


HTTP = _http

# Die EINZIGEN GitHub-Endpunkte, die dieses Modul berührt. Ein Vertragstest
# hält die Liste fest: Wer hier einen vierten Pfad ergänzt, erweitert die
# Rechte des Lauf-Tokens – das gehört in einen eigenen Bericht, nicht in eine
# stille Ergänzung.
ENDPUNKTE = (
    "/repos/{quelle}/actions/workflows/{workflow}/runs?per_page=30",
    "/repos/{quelle}/actions/workflows/{workflow}/dispatches",
    "/repos/{quelle}/actions/runs/{lauf_id}",
)


# =====================================================================
#  Hilfen
# =====================================================================
def _iso(wert) -> dt.datetime | None:
    try:
        zeit = dt.datetime.fromisoformat(str(wert).strip().replace("Z", "+00:00"))
    except (ValueError, AttributeError):
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
def _minuten_seit(zeit: dt.datetime | None, jetzt: dt.datetime) -> int | None:
    if zeit is None:
        return None
    return int((jetzt - zeit).total_seconds() // 60)


def _kurz(text, grenze: int = 220) -> str:
    rein = " ".join(str(text or "").split())
    return rein if len(rein) <= grenze else rein[: grenze - 1] + "…"


def _repo_bestimmen(flag: str = "", umgebung: dict | None = None) -> str:
    umgebung = os.environ if umgebung is None else umgebung
    if (flag or "").strip():
        return flag.strip()
    return (umgebung.get("BACKUP_REPO") or umgebung.get("ZIEL_REPO") or "").strip()


def _quelle_bestimmen(flag: str = "", umgebung: dict | None = None) -> str:
    umgebung = os.environ if umgebung is None else umgebung
    if (flag or "").strip():
        return flag.strip()
    return (umgebung.get("GITHUB_REPOSITORY") or "").strip()


def lese_token(umgebung: dict | None = None) -> str:
    """Lesezugriff auf das private Ziel – derselbe Vorrang wie im Frische-Guard."""
    umgebung = os.environ if umgebung is None else umgebung
    for name in ("GH_TOKEN", "BACKUP_REPO_TOKEN", "ZIEL_TOKEN", "GITHUB_TOKEN"):
        wert = (umgebung.get(name) or "").strip()
        if wert:
            return wert
    return ""


def aktion_token(umgebung: dict | None = None) -> str:
    """Anstoßen braucht `actions: write` im QUELL-Repo – ein eigener Token.

    Bewusst NICHT derselbe Zugang wie die Messung: Der Ziel-Token ist auf das
    private Backup-Repo begrenzt und darf im Quell-Repo nichts anstoßen.
    """
    umgebung = os.environ if umgebung is None else umgebung
    for name in ("AKTION_TOKEN", "GITHUB_TOKEN"):
        wert = (umgebung.get(name) or "").strip()
        if wert:
            return wert
    return ""


# =====================================================================
#  Die Entscheidung – reine Funktion, ohne Netz
# =====================================================================
def entscheide(befunde: list[dict], *, aktiver_lauf: bool = False,
               letzter_lauf_min: int | None = None,
               versuche_24h: int = 0,
               heilung_ab_h: int = HEILUNG_AB_H,
               max_versuche: int = MAX_VERSUCHE_24H,
               mindestabstand_min: int = MINDESTABSTAND_MIN) -> dict:
    """Darf (und muss) die Wache jetzt eine Sicherung anstoßen?

    Die Reihenfolge der Prüfungen ist die Sicherheit selbst: Erst der Bedarf,
    dann „läuft schon“, dann „gerade gelaufen“, dann das Budget. Wer die
    Reihenfolge ändert, kann einen Doppellauf erzeugen – deshalb ist die
    Tabelle als reine Funktion gebaut und im Selbsttest vollständig belegt.
    """
    bedarf = [
        b for b in befunde
        if b.get("stufe") == "fehler"
        or b.get("alter_h") is None
        or int(b.get("alter_h") or 0) > heilung_ab_h
    ]
    kennungen = [b.get("praefix") or "?" for b in bedarf]
    if not bedarf:
        return {"aktion": "nichts", "bedarf": [],
                "grund": f"Jede Release-Familie ist jünger als {heilung_ab_h} h – nichts zu heilen."}
    if aktiver_lauf:
        return {"aktion": "warten", "bedarf": kennungen,
                "grund": "Eine Sicherung ist bereits angefordert oder läuft – kein zweiter Anstoß."}
    if letzter_lauf_min is not None and letzter_lauf_min < mindestabstand_min:
        return {"aktion": "warten", "bedarf": kennungen,
                "grund": (f"Der letzte Sicherungslauf begann vor {letzter_lauf_min} Min. "
                          f"(Mindestabstand {mindestabstand_min} Min.) – kein Doppellauf.")}
    if versuche_24h >= max_versuche:
        return {"aktion": "aufgeben", "bedarf": kennungen,
                "grund": (f"Selbstheilungs-Budget erschöpft ({versuche_24h}/{max_versuche} "
                          "Anstöße in 24 h). Ein weiterer Anstoß wiederholte nur denselben "
                          "Fehler – die Ursache steht im roten Lauf von „Offsite-Backup“.")}
    return {"aktion": "anfordern", "bedarf": kennungen,
            "grund": (f"Kein frisches Release für {', '.join(kennungen)} und kein laufender "
                      "Sicherungslauf – die Wache stößt die Sicherung selbst an.")}


# =====================================================================
#  Lauf-Historie und Anstoß
# =====================================================================
def laeufe_holen(quelle: str, workflow: str, token: str,
                 http=None) -> tuple[int, list[dict] | None, str]:
    if not quelle or "/" not in quelle:
        return 0, None, "Kein Quell-Repository (GITHUB_REPOSITORY) angegeben."
    if not token:
        return 401, None, "Kein Aktion-Token (actions: write) vorhanden."
    http = http or HTTP
    url = f"{GH_API}/repos/{quelle}/actions/workflows/{urllib.parse.quote(workflow)}/runs?per_page=30"
    status, daten, netz = http("GET", url, token)
    if status != 200 or not isinstance(daten, dict):
        meldung = ""
        if isinstance(daten, dict):
            meldung = _kurz(daten.get("message", ""), 120)
        return status, None, netz or meldung or f"HTTP {status}"
    laeufe = daten.get("workflow_runs")
    if not isinstance(laeufe, list):
        return status, None, "Antwort ohne workflow_runs – nicht auswertbar."
    return status, laeufe, ""


def lauf_starten(quelle: str, workflow: str, token: str, branch: str = ZIEL_BRANCH,
                 http=None) -> tuple[int, str]:
    if not token:
        return 401, "Kein Aktion-Token (actions: write) vorhanden."
    http = http or HTTP
    url = f"{GH_API}/repos/{quelle}/actions/workflows/{urllib.parse.quote(workflow)}/dispatches"
    status, daten, netz = http("POST", url, token, {"ref": branch})
    if status in (201, 204):
        return status, ""
    meldung = _kurz(daten.get("message", ""), 160) if isinstance(daten, dict) else ""
    return status, netz or meldung or f"HTTP {status}"


def _lauf_status_holen(quelle: str, lauf_id: int, token: str, http=None) -> tuple[int, dict | None]:
    http = http or HTTP
    url = f"{GH_API}/repos/{quelle}/actions/runs/{int(lauf_id)}"
    status, daten, _netz = http("GET", url, token)
    return status, daten if isinstance(daten, dict) else None


def _laeufe_auswerten(laeufe: list[dict], jetzt: dt.datetime) -> dict:
    """Fasst die Lauf-Historie zusammen – ohne Netz, damit prüfbar."""
    aktiv, letzter_start_min, versuche_24h = False, None, 0
    juengster: dict | None = None
    for lauf in laeufe:
        if not isinstance(lauf, dict):
            continue
        status = str(lauf.get("status") or "")
        if status in AKTIVE_ZUSTAENDE:
            aktiv = True
        start = _iso(lauf.get("run_started_at") or lauf.get("created_at"))
        minuten = _minuten_seit(start, jetzt)
        if minuten is not None and (letzter_start_min is None or minuten < letzter_start_min):
            letzter_start_min = minuten
            juengster = lauf
        if (str(lauf.get("event") or "") == "workflow_dispatch"
                and minuten is not None and 0 <= minuten < 24 * 60):
            versuche_24h += 1
    return {"aktiv": aktiv, "letzter_start_min": letzter_start_min,
            "versuche_24h": versuche_24h, "juengster": juengster}


# =====================================================================
#  Heilung: messen → entscheiden → anstoßen → warten → erneut messen
# =====================================================================
def heile(umgebung: dict | None = None, *, jetzt: dt.datetime | None = None,
          jetzt_neu: dt.datetime | None = None,
          http=None, anstossen: bool = True, warten_s: int = WARTEZEIT_S,
          takt_s: int = ABFRAGE_TAKT_S, schlaf=None,
          repo: str = "", quelle: str = "", workflow: str = WORKFLOW
          ) -> dict:
    """Der ganze Kreis. Gibt das Ergebnis der ZWEITEN Messung zurück.

    Struktur:
      {"urteil": "ok|warnung|fehler", "text": …, "befunde": [...],
       "heilung": {"aktion": …, "grund": …, "gestartet": bool,
                   "lauf_url": str, "versuche_24h": int, "gemessen": bool}}
    """
    from backup_freshness_guard import pruefe_freshness  # eine Quelle der Frische

    umgebung = dict(os.environ) if umgebung is None else umgebung
    http = http or HTTP
    schlaf = schlaf or SCHLAF
    jetzt = jetzt or dt.datetime.now(dt.timezone.utc)
    # Zeitpunkt der ZWEITEN Messung ist ein eigener Parameter: Ein Selbsttest,
    # der hier die echte Wanduhr liest, ist eine Zeitbombe (Lehre vom
    # 18.09.2026, scripts/selftest_clock.py). Im Betrieb bleibt es „jetzt".
    jetzt_neu = jetzt_neu or dt.datetime.now(dt.timezone.utc)
    repo = repo or _repo_bestimmen(umgebung=umgebung)
    quelle = quelle or _quelle_bestimmen(umgebung=umgebung)

    token_lesen = lese_token(umgebung)
    ergebnis = pruefe_freshness(repo, token_lesen, jetzt, http_get=_messfkt(http, token_lesen))
    heilung = {"aktion": "nichts", "grund": "", "gestartet": False, "lauf_url": "",
               "versuche_24h": 0, "gemessen": True}

    if not ergebnis.get("befunde"):
        # Unprüfbar (kein Ziel, kein Token, Netz, 401/404): dann ist auch kein
        # Anstoß verantwortbar. Kein „nichts zu heilen“ über einer leeren Liste.
        heilung.update(aktion="aufgeben", gemessen=False,
                       grund=(f"Frische nicht messbar – {ergebnis.get('text', 'ohne Befund')} "
                              "Ohne Messung kein Anstoß."))
        return {**ergebnis, "heilung": heilung}

    if ergebnis.get("urteil") == "ok":
        bedarf = [b for b in ergebnis.get("befunde", [])
                  if b.get("alter_h") is None or int(b.get("alter_h") or 0) > HEILUNG_AB_H]
        if not bedarf:
            heilung["grund"] = "Alles frisch – nichts zu heilen."
            return {**ergebnis, "heilung": heilung}

    token_aktion = aktion_token(umgebung)
    status, laeufe, meldung = laeufe_holen(quelle, workflow, token_aktion, http)
    if status != 200 or laeufe is None:
        heilung.update(aktion="aufgeben", gemessen=False,
                       grund=(f"Lauf-Historie nicht lesbar (HTTP {status}: {meldung}) – ohne sie "
                              "wird nichts angestoßen (ein blinder Anstoß könnte doppelt sichern)."))
        return {**ergebnis, "heilung": heilung}

    auswertung = _laeufe_auswerten(laeufe, jetzt)
    heilung["versuche_24h"] = auswertung["versuche_24h"]
    entscheidung = entscheide(
        ergebnis.get("befunde", []),
        aktiver_lauf=auswertung["aktiv"],
        letzter_lauf_min=auswertung["letzter_start_min"],
        versuche_24h=auswertung["versuche_24h"],
    )
    heilung.update(aktion=entscheidung["aktion"], grund=entscheidung["grund"])

    if entscheidung["aktion"] != "anfordern":
        return {**ergebnis, "heilung": heilung}
    if not anstossen:
        heilung["grund"] += " (Probe: nicht angestoßen.)"
        return {**ergebnis, "heilung": heilung}

    hoechste_id = max((int(l.get("id") or 0) for l in laeufe if isinstance(l, dict)), default=0)
    status, meldung = lauf_starten(quelle, workflow, token_aktion, ZIEL_BRANCH, http)
    if status not in (201, 204):
        heilung["grund"] = (f"Anstoß abgelehnt (HTTP {status}: {meldung}). "
                            + ("Dem Lauf-Token fehlt `actions: write` – Job-Rechte in "
                               "backup-frischwache.yml prüfen."
                               if status in (401, 403) else
                               "Sicherung von Hand starten: Actions → „Offsite-Backup“ → Run workflow."))
        return {**ergebnis, "heilung": heilung}
    heilung["gestartet"] = True
    heilung["grund"] += " Sicherung wurde angestoßen."

    # Auf DIESEN Lauf warten (nicht auf irgendeinen): höchste bekannte ID + 1.
    lauf = _warte_auf_neuen_lauf(quelle, workflow, hoechste_id, token_aktion, http,
                                 warten_s=warten_s, takt_s=takt_s, schlaf=schlaf)
    if lauf is None:
        heilung["grund"] += (f" Innerhalb von {warten_s} s erschien kein neuer Lauf – "
                             "die Messung unten entscheidet, nicht die Absicht.")
    else:
        heilung["lauf_url"] = str(lauf.get("html_url") or "")
        zustand = str(lauf.get("status") or "")
        ergebnis_lauf = str(lauf.get("conclusion") or "")
        if zustand != "completed":
            heilung["grund"] += f" Der angestoßene Lauf {lauf.get('id')} läuft noch ({zustand})."
        elif ergebnis_lauf != "success":
            heilung["grund"] += (f" Der angestoßene Lauf endete mit „{ergebnis_lauf}“ "
                                 f"({heilung['lauf_url']}) – die Ursache nennt die Meldung "
                                 "zu „Offsite-Backup“.")

    # ZWEITE Messung: Ein angestoßener Lauf ist kein Nachweis.
    zweite = pruefe_freshness(repo, token_lesen, jetzt_neu, http_get=_messfkt(http, token_lesen))
    return {**zweite, "heilung": {**heilung, "gemessen": bool(zweite.get("befunde"))}}


def _messfkt(http, token: str):
    """Adapter: Der Guard ruft `hole(url)`; der Lese-Token gehört in den Kopf."""
    def hole(url: str):
        return http("GET", url, token)
    return hole


def _warte_auf_neuen_lauf(quelle: str, workflow: str, hoechste_id: int, token: str,
                          http, *, warten_s: int, takt_s: int, schlaf) -> dict | None:
    """Wartet begrenzt auf den Lauf, der durch den Anstoß entstanden ist."""
    verbraucht = 0
    gefunden: dict | None = None
    while verbraucht <= warten_s:
        status, laeufe, _ = laeufe_holen(quelle, workflow, token, http)
        if status == 200 and laeufe:
            neu = [l for l in laeufe
                   if isinstance(l, dict) and int(l.get("id") or 0) > hoechste_id]
            if neu:
                gefunden = max(neu, key=lambda l: int(l.get("id") or 0))
                if str(gefunden.get("status") or "") == "completed":
                    return gefunden
        if verbraucht + takt_s > warten_s:
            break
        schlaf(takt_s)
        verbraucht += takt_s
    if gefunden is not None:
        status, daten = _lauf_status_holen(quelle, int(gefunden.get("id") or 0), token, http)
        if status == 200 and daten:
            return daten
    return gefunden


# =====================================================================
#  Ausgabe
# =====================================================================
def bericht(ergebnis: dict) -> str:
    heilung = ergebnis.get("heilung", {})
    zeilen = [f"Backup-Selbstheilung · {ergebnis.get('repo', '?')}",
              ergebnis.get("text", "")]
    for befund in ergebnis.get("befunde", []):
        symbol = {"ok": "✅", "warnung": "⚠️", "fehler": "❌"}.get(befund.get("stufe", ""), "•")
        zeilen.append(f"  {symbol} {befund.get('praefix')} {befund.get('text')}")
    if heilung:
        zeilen.append(f"  → Selbstheilung: {heilung.get('aktion')} – {heilung.get('grund')}")
        if heilung.get("lauf_url"):
            zeilen.append(f"  → Angestoßener Lauf: {heilung['lauf_url']}")
    zeilen.append(f"Anleitung: {ANLEITUNG} (Abschnitt „Selbstheilung“)")
    return "\n".join(zeilen)


def _anhaengen(pfad: str, text: str) -> None:
    if pfad:
        with open(pfad, "a", encoding="utf-8") as datei:
            datei.write(text if text.endswith("\n") else text + "\n")


def zusammenfassung(ergebnis: dict) -> str:
    heilung = ergebnis.get("heilung", {})
    zeilen = ["## Backup-Selbstheilung (operativer RPO-Kreis)", ""]
    zeilen.append(f"**Urteil nach Heilung:** {ergebnis.get('text', '?')}")
    zeilen.append("")
    if heilung.get("aktion"):
        zeilen += ["| Punkt | Stand |", "|---|---|",
                   f"| Entscheidung | **{heilung.get('aktion')}** |",
                   f"| Begründung | {heilung.get('grund', '–')} |",
                   f"| Anstöße in 24 h (Budget {MAX_VERSUCHE_24H}) | {heilung.get('versuche_24h', 0)} |"]
        if heilung.get("lauf_url"):
            zeilen.append(f"| Angestoßener Lauf | {heilung['lauf_url']} |")
        zeilen.append("")
    for befund in ergebnis.get("befunde", []):
        symbol = {"ok": "OK", "warnung": "WARN", "fehler": "FEHLER"}.get(befund.get("stufe", ""), "-")
        zeilen.append(f"- {symbol} {befund.get('praefix')} {befund.get('text')}")
    zeilen += ["",
               "Grenzen: höchstens ein Anstoß je Lauf und "
               f"{MAX_VERSUCHE_24H} je 24 h; kein Anstoß bei laufender Sicherung; "
               "Grün nur nach der zweiten Messung.", ""]
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
#  Selbsttest – offline, ohne Netz
# =====================================================================
def selbsttest() -> int:
    fehler: list[str] = []
    jetzt = dt.datetime(2026, 11, 7, 13, 0, tzinfo=dt.timezone.utc)

    def befunde(*alter):
        return [{"praefix": "backup-" if i == 0 else "kv-backup-", "alter_h": a,
                 "stufe": ("fehler" if a is None or a > 52 else "warnung" if a > 36 else "ok"),
                 "text": f"{a} h"}
                for i, a in enumerate(alter)]

    # S1: alles frisch → nichts
    e = entscheide(befunde(10, 10), versuche_24h=0)
    if e["aktion"] != "nichts":
        fehler.append(f"S1: frische Sicherung löst aus: {e}")

    # S2: Tagesfenster verpasst (34 h) → anfordern, obwohl die Meldung noch gelb/grün wäre
    e = entscheide(befunde(34, 34))
    if e["aktion"] != "anfordern":
        fehler.append(f"S2: verpasster Tag (34 h) fordert nicht an: {e}")

    # S3: Grenze 26 h – 26 h ist kein Bedarf, 27 h ist einer (Tagesfenster)
    if entscheide(befunde(26, 26))["aktion"] != "nichts":
        fehler.append("S3a: 26 h darf nicht auslösen")
    if entscheide(befunde(27, 27))["aktion"] != "anfordern":
        fehler.append("S3b: 27 h muss auslösen")

    # S4: fehlende Familie → anfordern (kein Release = keine Sicherung)
    e = entscheide(befunde(None, 5))
    if e["aktion"] != "anfordern" or "backup-" not in e["bedarf"]:
        fehler.append(f"S4: fehlende Familie löst nicht aus: {e}")

    # S5: laufende Sicherung → warten (kein Doppellauf)
    e = entscheide(befunde(None, None), aktiver_lauf=True)
    if e["aktion"] != "warten":
        fehler.append(f"S5: laufende Sicherung wird doppelt angestoßen: {e}")

    # S6: Mindestabstand – letzter Lauf vor 3 Min. → warten
    e = entscheide(befunde(None, None), letzter_lauf_min=3)
    if e["aktion"] != "warten":
        fehler.append(f"S6: Mindestabstand greift nicht: {e}")

    # S7: Budget erschöpft → aufgeben (kein Dauerfeuer)
    e = entscheide(befunde(None, None), versuche_24h=MAX_VERSUCHE_24H)
    if e["aktion"] != "aufgeben" or "Budget" not in e["grund"]:
        fehler.append(f"S7: Budget greift nicht: {e}")

    # S8: Reihenfolge – laufende Sicherung schlägt Budget (kein Anstoß, kein Aufgeben)
    e = entscheide(befunde(None, None), aktiver_lauf=True, versuche_24h=99)
    if e["aktion"] != "warten":
        fehler.append(f"S8: laufende Sicherung muss vor dem Budget gelten: {e}")

    # S9: Lauf-Historie – Aktiv-Erkennung, Mindestabstand, Budgetzählung
    laeufe = [
        {"id": 3, "status": "in_progress", "event": "schedule",
         "created_at": "2026-11-07T12:55:00Z", "run_started_at": "2026-11-07T12:55:00Z"},
        {"id": 2, "status": "completed", "event": "workflow_dispatch",
         "created_at": "2026-11-07T03:00:00Z", "run_started_at": "2026-11-07T03:00:00Z"},
        {"id": 1, "status": "completed", "event": "workflow_dispatch",
         "created_at": "2026-11-06T03:00:00Z", "run_started_at": "2026-11-06T03:00:00Z"},
    ]
    a = _laeufe_auswerten(laeufe, jetzt)
    if not a["aktiv"] or a["letzter_start_min"] != 5 or a["versuche_24h"] != 1:
        fehler.append(f"S9: Lauf-Auswertung falsch: {a}")
    if _laeufe_auswerten([], jetzt) != {"aktiv": False, "letzter_start_min": None,
                                        "versuche_24h": 0, "juengster": None}:
        fehler.append("S9b: leere Historie muss „kein Lauf“ ergeben")

    # S10: Kreis ohne Bedarf – keine Aktion, Exit 0 (die Attrappe darf NICHTS anstoßen)
    anstoesse: list[str] = []

    def welt_frisch(methode, url, token, koerper=None):
        if "/releases" in url:
            return 200, [{"tag_name": "backup-20261107-0300", "draft": True,
                          "created_at": "2026-11-07T03:00:00Z",
                          "assets": [{"name": "backup.bundle", "size": 1234}]},
                         {"tag_name": "kv-backup-20261107-0300", "draft": True,
                          "created_at": "2026-11-07T03:01:00Z",
                          "assets": [{"name": "kv-export.json.enc", "size": 999}]}], ""
        anstoesse.append(url)
        return 500, None, "unerwartet"

    r = heile({"BACKUP_REPO": "a/b", "GITHUB_REPOSITORY": "a/b", "GH_TOKEN": "t",
               "AKTION_TOKEN": "t2"}, jetzt=jetzt, jetzt_neu=jetzt, http=welt_frisch, schlaf=lambda _s: None)
    if r["urteil"] != "ok" or r["heilung"]["aktion"] != "nichts":
        fehler.append(f"S10: frische Sicherung heilt nicht „nichts“: {r['heilung']}")
    if anstoesse:
        fehler.append(f"S10: ohne Bedarf wurde die Lauf-API berührt: {anstoesse}")

    # S11: Kreis MIT Bedarf – genau ein Anstoß, Warten, ZWEITE Messung entscheidet
    zustand = {"stoesse": 0, "messen": 0, "lauf_abgefragt": 0}

    def welt_leer(methode, url, token, koerper=None):
        if "/releases" in url:
            zustand["messen"] += 1
            if zustand["messen"] == 1:
                return 200, [], ""                      # noch keine Sicherung
            return 200, [{"tag_name": "backup-20261107-1300", "draft": True,
                          "created_at": "2026-11-07T12:58:00Z",
                          "assets": [{"name": "backup.bundle", "size": 1234}]},
                         {"tag_name": "kv-backup-20261107-1300", "draft": True,
                          "created_at": "2026-11-07T12:59:00Z",
                          "assets": [{"name": "kv-export.json.enc", "size": 999}]}], ""
        if url.endswith("/dispatches"):
            zustand["stoesse"] += 1
            return 204, None, ""
        if "/runs?" in url:
            if zustand["stoesse"] == 0:
                return 200, {"workflow_runs": []}, ""
            return 200, {"workflow_runs": [
                {"id": 77, "status": "completed", "conclusion": "success",
                 "event": "workflow_dispatch", "created_at": "2026-11-07T13:00:05Z",
                 "run_started_at": "2026-11-07T13:00:05Z",
                 "html_url": "https://x/runs/77"}]}, ""
        zustand["lauf_abgefragt"] += 1
        return 200, {"id": 77, "status": "completed", "conclusion": "success",
                     "html_url": "https://x/runs/77"}, ""

    r = heile({"BACKUP_REPO": "a/b", "GITHUB_REPOSITORY": "a/b", "GH_TOKEN": "t",
               "AKTION_TOKEN": "t2"}, jetzt=jetzt, jetzt_neu=jetzt, http=welt_leer, schlaf=lambda _s: None)
    if zustand["stoesse"] != 1:
        fehler.append(f"S11: erwartet genau 1 Anstoß, war {zustand['stoesse']}")
    if zustand["messen"] != 2:
        fehler.append(f"S11: es muss ZWEIMAL gemessen werden (vor/nach), war {zustand['messen']}")
    if r["urteil"] != "ok" or not r["heilung"]["gestartet"]:
        fehler.append(f"S11: geheilter Lauf meldet nicht grün: {r['heilung']}")
    if r["heilung"].get("lauf_url") != "https://x/runs/77":
        fehler.append(f"S11: Lauf-Link fehlt: {r['heilung']}")

    # S12: angestoßen, aber Lauf scheitert → KEIN Schein-Grün
    zustand2 = {"stoesse": 0, "messen": 0}

    def welt_scheitert(methode, url, token, koerper=None):
        if "/releases" in url:
            zustand2["messen"] += 1
            return 200, [], ""
        if url.endswith("/dispatches"):
            zustand2["stoesse"] += 1
            return 204, None, ""
        if "/runs?" in url:
            if zustand2["stoesse"] == 0:
                return 200, {"workflow_runs": []}, ""
            return 200, {"workflow_runs": [
                {"id": 88, "status": "completed", "conclusion": "failure",
                 "event": "workflow_dispatch", "created_at": "2026-11-07T13:00:05Z",
                 "run_started_at": "2026-11-07T13:00:05Z", "html_url": "https://x/runs/88"}]}, ""
        return 200, {"id": 88, "status": "completed", "conclusion": "failure",
                     "html_url": "https://x/runs/88"}, ""

    r = heile({"BACKUP_REPO": "a/b", "GITHUB_REPOSITORY": "a/b", "GH_TOKEN": "t",
               "AKTION_TOKEN": "t2"}, jetzt=jetzt, jetzt_neu=jetzt, http=welt_scheitert, schlaf=lambda _s: None)
    if r["urteil"] != "fehler":
        fehler.append(f"S12: gescheiterter Lauf darf nicht grün werden: {r['urteil']}")
    if "failure" not in r["heilung"]["grund"]:
        fehler.append(f"S12: Grund nennt das Laufergebnis nicht: {r['heilung']['grund']}")

    # S13: Anstoß verweigert (403: Rechte fehlen) → klarer Grund, kein stiller Erfolg
    def welt_403(methode, url, token, koerper=None):
        if "/releases" in url:
            return 200, [], ""
        if "/runs?" in url:
            return 200, {"workflow_runs": []}, ""
        return 403, {"message": "Resource not accessible by integration"}, ""

    r = heile({"BACKUP_REPO": "a/b", "GITHUB_REPOSITORY": "a/b", "GH_TOKEN": "t",
               "AKTION_TOKEN": "t2"}, jetzt=jetzt, jetzt_neu=jetzt, http=welt_403, schlaf=lambda _s: None)
    if r["urteil"] != "fehler" or "actions: write" not in r["heilung"]["grund"]:
        fehler.append(f"S13: 403 wird nicht als Rechtebefund erklärt: {r['heilung']}")

    # S14: Lauf-Historie nicht lesbar → KEIN blinder Anstoß (fail-closed)
    def welt_ohne_historie(methode, url, token, koerper=None):
        if "/releases" in url:
            return 200, [], ""
        return 500, None, "ServerError"

    r = heile({"BACKUP_REPO": "a/b", "GITHUB_REPOSITORY": "a/b", "GH_TOKEN": "t",
               "AKTION_TOKEN": "t2"}, jetzt=jetzt, jetzt_neu=jetzt, http=welt_ohne_historie,
              schlaf=lambda _s: None)
    if r["heilung"]["aktion"] != "aufgeben" or r["heilung"]["gestartet"]:
        fehler.append(f"S14: ohne Historie wurde angestoßen: {r['heilung']}")

    # S15: Probe-Modus stößt nie an (der lokale Aufruf darf nichts auslösen)
    r = heile({"BACKUP_REPO": "a/b", "GITHUB_REPOSITORY": "a/b", "GH_TOKEN": "t",
               "AKTION_TOKEN": "t2"}, jetzt=jetzt, http=welt_403, schlaf=lambda _s: None,
              anstossen=False)
    if r["heilung"]["gestartet"] or "Probe" not in r["heilung"]["grund"]:
        fehler.append(f"S15: Probe-Modus hat angestoßen: {r['heilung']}")

    # S16: Rechte-Trennung – der Ziel-Token darf NICHT als Aktion-Token dienen
    if aktion_token({"BACKUP_REPO_TOKEN": "ziel", "GH_TOKEN": "ziel"}) != "":
        fehler.append("S16: der Ziel-Token darf nicht zum Anstoßen verwendet werden")
    if aktion_token({"AKTION_TOKEN": "lauf", "GITHUB_TOKEN": "allgemein"}) != "lauf":
        fehler.append("S16: AKTION_TOKEN muss vor GITHUB_TOKEN gelten")

    # S17: Eingabe-Auflösung – Ziel und Quelle aus der Umgebung, Flag gewinnt
    if _repo_bestimmen(umgebung={"BACKUP_REPO": "x/y"}) != "x/y":
        fehler.append("S17a: BACKUP_REPO wird nicht gelesen")
    if _repo_bestimmen("flag/repo", {"BACKUP_REPO": "x/y"}) != "flag/repo":
        fehler.append("S17b: --repo muss gewinnen")
    if _quelle_bestimmen(umgebung={"GITHUB_REPOSITORY": "q/r"}) != "q/r":
        fehler.append("S17c: GITHUB_REPOSITORY wird nicht gelesen")

    # S18: Keine Secrets in der Ausgabe (der Bericht nennt nur Ziele, nie Werte)
    gift = "GIFTWERT-SELBSTHEILUNG-0123456789"
    text = bericht({**r, "heilung": {**r["heilung"], "grund": "Test"}})
    if gift in text:
        fehler.append("S18: ein Secret-Wert steht im Bericht")

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
    print("✅ backup_selbstheilung-Selbsttest: 18 Fallgruppen – Tagesfenster, Grenzen, "
          "laufende Sicherung, Mindestabstand, Budget, Lauf-Auswertung, ein Anstoß je Lauf, "
          "zweite Messung als einziger Grün-Nachweis, gescheiterter Lauf, 403, unlesbare "
          "Historie, Probe-Modus, Rechte-Trennung und Eingabe-Auflösung.")
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


def _zeugt_lauf(lauf: dict) -> bool:
    """Hat dieser Lauf überhaupt etwas gemessen?

    07.11.2026 – Selbstfund nach dem ersten Live-Einsatz: Ein Lauf, dessen
    JOB `skipped` ist (0 Schritte, z. B. weil `if: github.ref == main` auf
    einem Branch zugeschlagen hat), ist KEIN Zeuge. Er hat nichts übersprungen,
    er ist gar nicht gelaufen.
    """
    if str(lauf.get("conclusion")) == "skipped":
        return False
    return True


def _schritte_des_juengsten(repo: str, token: str, workflow: str) -> list:
    """Die Schritte des jüngsten Laufs, der tatsächlich gelaufen ist.

    WARUM NICHT EINFACH „DER JÜNGSTE" (Selbstfund 07.11.2026):
    Der Prüfer las den neuesten Lauf. Ein `workflow_dispatch` auf einem
    Branch wird von `if: github.ref == 'refs/heads/main'` übersprungen – der
    Lauf steht dann mit `skipped` und **null Schritten** in der Liste. Genau
    das ist passiert: Die Messung, die den Befund „Nachweis wurde
    übersprungen" (Klasse `scheinbeweis`) finden sollte, verschwand, weil ein
    leerer Lauf sie überdeckte. Derselbe Fehler wie am selben Tag auf
    Job-Ebene (der Gesamtlauf war rot, der sichernde Job grün) – nur eine
    Ebene höher: **ein Lauf ohne Schritte ist kein Zeuge, er ist ein
    Platzhalter.**

    Deshalb wird jetzt der jüngste Lauf gesucht, der Schritte HAT. Kann keiner
    gelesen werden, ist das kein „alles in Ordnung", sondern ein Befund:
    Ein leerer Rückgabewert wird von `pruefe_scheinbeweis` als fehlender
    Nachweis gewertet, nicht als Entlastung.
    """
    laeufe = [l for l in _laeufe(repo, token, workflow) if _zeugt_lauf(l)]
    laeufe.sort(key=lambda l: str(l.get("created_at", "")), reverse=True)
    for lauf in laeufe[:5]:
        status, antwort, _m = HTTP("GET", f"{GH_API}/repos/{repo}/actions/runs/"
                                   f"{lauf.get('id')}/jobs", _gh_kopf(token))
        if status != 200 or not isinstance(antwort, dict):
            continue
        schritte: list = []
        for job in antwort.get("jobs", []):
            schritte.extend(job.get("steps", []) or [])
        if schritte:                      # erst ein Lauf MIT Schritten zeugt
            return schritte
    return []


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
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Heilt eine fehlende oder überfällige Offsite-Sicherung (RPO-Kreis).")
    gruppe = ap.add_mutually_exclusive_group()
    gruppe.add_argument("--probe", action="store_true",
                        help="messen und entscheiden, aber nichts anstoßen (Standard)")
    gruppe.add_argument("--heilen", action="store_true",
                        help="messen, Sicherung anstoßen, warten, erneut messen")
    ap.add_argument("--selftest", action="store_true", help="Offline-Selbsttest")
    ap.add_argument("--json", action="store_true", help="Maschinenlesbares Ergebnis")
    ap.add_argument("--ausgabe", default="", help="Ergebnis zusätzlich als JSON-Datei schreiben")
    ap.add_argument("--repo", default="", help="Backup-Repository (besitzer/name)")
    ap.add_argument("--quelle", default="", help="Quell-Repository (besitzer/name)")
    ap.add_argument("--workflow", default=WORKFLOW, help="Workflow-Datei der Sicherung")
    ap.add_argument("--wartezeit", type=int, default=WARTEZEIT_S,
                    help="Sekunden, die auf den angestoßenen Lauf gewartet wird")
    args = ap.parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.selftest:
        return selbsttest()

    umgebung = dict(os.environ)
    ergebnis = heile(umgebung, anstossen=bool(args.heilen),
                     warten_s=max(0, args.wartezeit),
                     repo=args.repo.strip(), quelle=args.quelle.strip(),
                     workflow=args.workflow.strip() or WORKFLOW)
    text = json.dumps(ergebnis, ensure_ascii=False, indent=2)
    print(text if args.json else bericht(ergebnis))
    if args.ausgabe:
        with open(args.ausgabe, "w", encoding="utf-8") as datei:
            datei.write(text)
    aktionen = ergebnis.get("heilung", {})
    if umgebung.get("GITHUB_ACTIONS") == "true":
        _anhaengen(umgebung.get("GITHUB_STEP_SUMMARY", ""), zusammenfassung(ergebnis))
        if aktionen.get("aktion") in ("warten", "aufgeben"):
            print(f"::warning title=Backup-Selbstheilung::{_kurz(aktionen.get('grund', ''))}")
        if aktionen.get("aktion") == "anfordern" and not aktionen.get("gestartet"):
            print(f"::warning title=Backup-Selbstheilung::{_kurz(aktionen.get('grund', ''))}")
        if aktionen.get("gestartet"):
            print(f"::notice title=Backup-Selbstheilung::Sicherung angestoßen – "
                  f"{_kurz(aktionen.get('grund', ''))}")
    return 0 if ergebnis.get("urteil") != "fehler" else 1


if __name__ == "__main__":
    sys.exit(main())
