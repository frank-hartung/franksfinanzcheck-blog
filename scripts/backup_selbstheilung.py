#!/usr/bin/env python3
# ============================================================
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
import json
import os
import re
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

# Die Frischwache selbst – sie ist der Aufrufer und liefert den Rückweg-Nachweis
# (Schritt „Kurzpruefung Wiederherstellbarkeit“). Getrennt von WORKFLOW, weil
# „keine Sicherung gelaufen“ und „der Nachweis wurde übersprungen“ zwei
# verschiedene Aussagen sind (WF-9E5A / #923).
FRISCHE_WORKFLOW = "backup-frischwache.yml"

# Ohne ausdrückliche Wahl misst das Urteil BEIDE Höhen (#1030, 12.11.2026):
# Der Offsite-Lauf trägt den Leerlauf des Jobs „backup“, die Frischwache den
# einzigen automatischen Rückweg-Nachweis („Kurzpruefung Wiederherstellbarkeit“).
# Vorher las `--leerlauf` ausschließlich den Offsite-Lauf – ein übersprungener
# Rückweg-Nachweis war damit für dieses Modul unsichtbar, obwohl genau er der
# Befund ist, den `pruefe_scheinbeweis` beschreibt.
URTEIL_QUELLEN = (WORKFLOW, FRISCHE_WORKFLOW)

# =====================================================================
#  KLASSEN – was darf dieses Modul selbst, und was nie? (H2)
#  ------------------------------------------------------------
#  Ein Selbstheiler, der „alles“ reparieren darf, ist ein Freibrief. Heilbar
#  ist hier GENAU eine Klasse: der nicht gestartete Lauf. Alles andere hat
#  einen Inhaber (Zugänge, Passphrase, Environment-Regeln) oder ist eine
#  Code-Frage (übersprungener Nachweis) – ein Anstoß würde dort nur denselben
#  Fehler wiederholen und das Grün erkaufen, statt es zu belegen.
# =====================================================================
KLASSEN = {
    "scheduler": {
        "heilbar": True,
        "grund": ("Der geplante Lauf fehlt (Scheduler-Aussetzer, verworfenes Token, "
                  "Environment-Regel) – ein Anstoß von `backup-offsite.yml` auf `main` "
                  "ist der geprüfte Weg und wird nach 15 Min. erneut gemessen."),
    },
    "leerlauf": {
        "heilbar": False,
        "grund": ("Ein grüner Lauf ohne `BACKUP_REPO`/`BACKUP_PASSPHRASE` sichert nur "
                  "eine Kurzzeitkopie im selben Konto. Das ist eine Einrichtungs-"
                  "aufgabe (E1/E3) – ein Neustart erzeugt nur einen weiteren grünen "
                  "Leerlauf."),
    },
    "scheinbeweis": {
        "heilbar": False,
        "grund": ("Der Rückweg-Nachweis wurde übersprungen oder ist gescheitert. „Nicht "
                  "geprüft“ ist kein Grün; ein Anstoß ändert an einem übersprungenen "
                  "Schritt nichts."),
    },
    "einrichtung": {
        "heilbar": False,
        "grund": ("E1–E8 sind Zugänge und Regeln des Inhabers. Dieses Modul legt keine "
                  "Secrets, Variablen oder Environment-Regeln an (Rechte-Trennung) – "
                  "es nennt nur, was fehlt."),
    },
}

# Exit-Codes des Betriebs-Urteils (dieselbe Sprache wie das Alerting):
# 0 = kein Befund · 1 = Befund ohne Beweis (Scheinbeweis) · 3 = Inhaber-Schritt
# (Einrichtung hat Vorrang) · 4 = grüner Leerlauf bei vollständiger Einrichtung.
EXIT_BEFUND = 1
EXIT_EINRICHTUNG = 3
EXIT_LEERLAUF = 4
EXIT_WERKZEUG = 2


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
                 http=None, per_page: int = 30) -> tuple[int, list[dict] | None, str]:
    if not quelle or "/" not in quelle:
        return 0, None, "Kein Quell-Repository (GITHUB_REPOSITORY) angegeben."
    if not token:
        return 401, None, "Kein Aktion-Token (actions: write) vorhanden."
    http = http or HTTP
    url = (f"{GH_API}/repos/{quelle}/actions/workflows/{urllib.parse.quote(workflow)}"
           f"/runs?per_page={max(1, min(int(per_page), 100))}")
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
#  ZEUGEN UND MESSHÖHE (WF-9E5A / #923, 07.11.2026)
#  ------------------------------------------------------------
#  Die Lehre des Tages: „Ein System, das an der falschen Höhe misst, ist
#  nicht halb richtig – es ist in beide Richtungen falsch.“
#    · Gemessen wird der JOB („backup“), nicht der Gesamtlauf: Ein KV-Job
#      kann rot sein, während der Repo-Job grün ist – und umgekehrt.
#    · Gemessen wird der jüngste Lauf, der Schritte HAT: Ein `workflow_dispatch`
#      auf einem fremden Branch steht als `skipped` mit NULL Schritten in der
#      Liste (Job-Guard `refs/heads/main`). Wer den liest, löscht den Befund
#      genau dann, wenn er ihn braucht.
# =====================================================================
def _zeugt_lauf(lauf) -> bool:
    """Ist dieser Lauf ein Zeuge – oder nur ein Platzhalter?

    Ein Lauf ohne Ausführung (`skipped`, kein Abschluss) bezeugt nichts. Er
    ist kein Fehler, aber er ist auch kein Beweis: Er wird ÜBERSPRUNGEN, nicht
    als „grün“ oder „rot“ gelesen.
    """
    if not isinstance(lauf, dict):
        return False
    return str(lauf.get("conclusion") or "").strip() not in ("", "skipped")


def _jobs_url(lauf: dict, quelle: str) -> str:
    """Job-Liste eines Laufs – bevorzugt die von GitHub gelieferte `jobs_url`.

    Die API nennt die Adresse im Lauf selbst (`jobs_url`). Sie zu benutzen
    hält die Endpunkt-Liste dieses Moduls bei DREI Pfaden: Es entsteht kein
    vierter, hartkodierter GitHub-Pfad, und die Rechte-Zusage des Vertrags
    bleibt lesbar.
    """
    direkt = str(lauf.get("jobs_url") or "").strip()
    if not direkt:
        direkt = GH_API + f"/repos/{quelle}/actions/runs/{int(lauf.get('id') or 0)}/jobs"
    return direkt if "?" in direkt else direkt + "?per_page=50"


def _jobs_des_juengsten(quelle: str, token: str, workflow: str = FRISCHE_WORKFLOW,
                        http=None) -> tuple[int, list[dict], str]:
    """Jobs des jüngsten Laufs, der tatsächlich Schritte hat (fail-closed)."""
    http = http or HTTP
    status, laeufe, meldung = laeufe_holen(quelle, workflow, token, http, per_page=20)
    if status != 200 or laeufe is None:
        return status, [], meldung or f"HTTP {status}"
    zeugen = [l for l in laeufe if _zeugt_lauf(l)]
    zeugen.sort(key=lambda l: _iso(l.get("created_at")) or dt.datetime.min.replace(
        tzinfo=dt.timezone.utc), reverse=True)
    for lauf in zeugen:
        status, daten, netz = http("GET", _jobs_url(lauf, quelle), token)
        if status != 200 or not isinstance(daten, dict):
            continue
        jobs = [j for j in (daten.get("jobs") or []) if isinstance(j, dict)]
        if any(j.get("steps") for j in jobs):
            return 200, jobs, ""
    return 200, [], "Kein abgeschlossener Lauf mit Schritten gefunden."


def _schritte_des_juengsten(quelle: str, token: str, workflow: str = FRISCHE_WORKFLOW,
                            http=None) -> list[dict]:
    """Alle Schritte des jüngsten zeugenden Laufs (leer, wenn keiner zeugt)."""
    status, jobs, _ = _jobs_des_juengsten(quelle, token, workflow, http)
    if status != 200:
        return []
    return [s for j in jobs for s in (j.get("steps") or []) if isinstance(s, dict)]


def pruefe_leerlauf(jobs, ziel_gesetzt, pflicht_gesetzt, jetzt=None) -> list[dict]:
    """Der grüne Leerlauf: Job „backup“ success – und trotzdem nichts gesichert.

    Ohne dauerhaftes Ziel (`BACKUP_REPO`) bzw. ohne Passphrase legt der Job
    ausschließlich eine 7-Tage-Kurzzeitkopie im SELBEN Konto ab. Bei
    Kontoverlust ist sie mit weg. „Gelaufen“ ist dann wahr, „gesichert“ nicht –
    und dieses Grün ist gefährlicher als jedes Rot im Backup: Rot sieht man,
    Grün glaubt man.

    Der KV-Job ist kein Zeuge: Er legt nie ein Repo-Artefakt an, sein Grün
    sagt nichts über das Offsite-Backup.
    """
    gemessen = jetzt or dt.datetime.now(dt.timezone.utc)
    # Nur die ANWESENHEIT wird gelesen, nie der Wert – und der Name sagt das
    # auch: `ziel_gesetzt`/`pflicht_gesetzt` sind JA/NEIN, keine Geheimnisse.
    # (Klartext-Wache FLUSS; ein Name wie `passphrase` behauptete einen Wert,
    # den diese Prüfung nie sieht – CODE-SCANNING-80.)
    ziel_da, pflicht_da = bool(ziel_gesetzt), bool(pflicht_gesetzt)
    befund: list[dict] = []
    for job in jobs or []:
        if not isinstance(job, dict):
            continue
        name = str(job.get("name") or "").strip()
        if name.lower() != "backup":
            continue
        if str(job.get("conclusion") or "").strip() != "success":
            continue
        fehlt = [kennung for kennung, gesetzt in (("BACKUP_REPO", ziel_da),
                                                  ("BACKUP_PASSPHRASE", pflicht_da))
                 if not gesetzt]
        if not fehlt:
            continue
        befund.append({
            "klasse": "leerlauf",
            "praefix": "backup",
            "heilbar": False,
            "stufe": "warnung",
            "text": (f"Job „{name}“ ist grün, gesichert wurde aber nichts "
                     f"({', '.join(fehlt)} fehlt) – es existiert nur eine "
                     "Kurzzeitkopie im selben Konto, kein Offsite-Schutz."),
            "beleg": {"job": name, "conclusion": "success", "fehlt": fehlt,
                      "gemessen": gemessen.isoformat()},
        })
    return befund


def _leerlauf_urteil(jobs: list[dict], umgebung: dict, jetzt, *,
                     einrichtung_offen=None) -> dict:
    """`betreibe_urteil` ohne Netz – der Selbsttest braucht keinen Dispatch."""
    def http(methode: str, url: str, kopf, koerper=None):
        if url.endswith("/runs?per_page=20"):
            return 200, {"workflow_runs": [{"id": 7, "conclusion": "success",
                                            "created_at": "2026-11-07T03:00:00Z"}]}, ""
        return 200, {"jobs": [{**j, "steps": j.get("steps") or [
            {"name": "Bundle + Arbeitskopie erstellen", "conclusion": "success"}]}
            for j in jobs]}, ""

    # `einrichtung_offen=None` heißt hier: die Einrichtungsprüfung LIEF und hat
    # nichts offen (ein leeres Ergebnis). Nur so unterscheidet der Aufrufer
    # „geprüft, alles gut“ von „gar nicht geprüft“ (#1030).
    return betreibe_urteil({**umgebung, "GITHUB_REPOSITORY": "a/b", "GH_TOKEN": "t"},
                           jetzt=jetzt, http=http, einrichtung_offen=einrichtung_offen,
                           setup_geprueft=True)


def pruefe_scheinbeweis(schritte, jetzt=None) -> list[dict]:
    """Ein übersprungener Rückweg-Nachweis ist ein Befund, kein Nichts."""
    gemessen = jetzt or dt.datetime.now(dt.timezone.utc)
    befund: list[dict] = []
    for schritt in schritte or []:
        if not isinstance(schritt, dict):
            continue
        name = str(schritt.get("name") or "")
        if "Wiederherstellbarkeit" not in name:
            continue
        if str(schritt.get("conclusion") or "") != "skipped":
            continue
        befund.append({
            "klasse": "scheinbeweis",
            "praefix": "rueckweg",
            "heilbar": False,
            "stufe": "warnung",
            "text": (f"Schritt „{name}“ wurde übersprungen – der Rückweg ist damit "
                     "nicht belegt („nicht geprüft“ ist kein Grün)."),
            "beleg": {"schritt": name, "conclusion": "skipped",
                      "gemessen": gemessen.isoformat()},
        })
    return befund


# =====================================================================
#  WER HAT ES GESEHEN? (Vorgang WF-3150 / #1030, 10.11.2026)
#  ------------------------------------------------------------
#  BEFUND (Lauf 42715328453): Derselbe Lauf hatte ZWEI rote Schritte –
#  „Voraussetzungen prüfen“ (richtig, Einrichtungs-Rat) und „Leerlauf
#  prüfen“ (falsch: es war kein Lauf grün). Ursache: Der zweite Schritt
#  bekam den Befund des ersten nicht. Er riet – und riet anders.
#  `betreibe_urteil(..., einrichtung_offen=…)` gab es dafür seit dem
#  07.11. schon; der Workflow füllte den Parameter nie.
#
#  Jetzt gilt: Der Schritt, der es WEISS, sagt es in `GITHUB_OUTPUT`
#  (`offene_einrichtung=E1 E3`). Der nächste Schritt liest genau diesen
#  Wert. Fehlt er, obwohl der Vorgänger „Voraussetzungen prüfen“ nicht
#  durchgelaufen ist, wird NICHT geraten: dann ist die Prüfung „nicht
#  entscheidbar“ (Exit 2, rot) – „weiß nicht“ ist nie ein Grün.
# =====================================================================
UMGEBUNG_OFFEN = "OFFENE_EINRICHTUNG"
# Nur die Kennungen des Einrichtungsvertrags (E1 … E8). Alles andere ist
# „nicht lesbar“ – ein Tippfehler darf nicht als Einrichtungspunkt gelten.
KENNUNG = re.compile(r"^E[1-8]$")


def einrichtung_offen_aus_umgebung(umgebung: dict | None = None) -> list[str] | None:
    """Offene Kennungen aus der Umgebung – oder `None`, wenn niemand sie weiß.

    Bewusst DREI Antworten, nicht zwei:

      `[]`   – die Einrichtungsprüfung ist durchgelaufen und hat nichts offen.
      `[..]` – sie hat diese Punkte offen gemeldet (Ursache bekannt).
      `None` – sie lief nicht oder nicht lesbar: Der Aufrufer darf nicht
               raten und muss fail-closed antworten.

    Die Kennungen sind `E1` … `E8`. Die Trennzeichen werden breit
    akzeptiert (Leerzeichen, Komma, Semikolon), damit ein Aufruf von Hand
    nicht an einem Komma scheitert; alles andere ist „nicht lesbar“.
    """
    umgebung = dict(os.environ) if umgebung is None else umgebung
    if UMGEBUNG_OFFEN not in umgebung:
        return None
    roh = str(umgebung.get(UMGEBUNG_OFFEN) or "").strip()
    if not roh:
        return []
    teile = [t.strip() for t in roh.replace(";", " ").replace(",", " ").split() if t.strip()]
    if not all(KENNUNG.match(t) for t in teile):
        return None
    return teile


def betreibe_urteil(umgebung: dict | None = None, *, jetzt: dt.datetime | None = None,
                    http=None, quelle: str = "", workflow: str = "",
                    einrichtung_offen: list[str] | None = None,
                    setup_geprueft: bool = False) -> dict:
    """Urteil auf JOB-Ebene – ohne Anstoß, ohne Schreibzugriff.

    Struktur: `{"messbar": bool, "befunde": [...], "exit": int, "text": str,
    "quellen": [...]}`.
    Die Reihenfolge der Klassen ist die Reihenfolge der Antworten: offene
    Einrichtung zuerst (sie ist die Ursache), dann Leerlauf, dann Scheinbeweis.

    Ohne ausdrückliches `workflow` misst das Urteil BEIDE Höhen
    (`URTEIL_QUELLEN`): den Offsite-Lauf für den Leerlauf, die Frischwache für
    den Rückweg-Nachweis. `quellen` nennt, was tatsächlich gelesen wurde – eine
    leere Liste ist die ehrliche Auskunft „nichts gemessen“.

    `einrichtung_offen` ist die Antwort der Einrichtungsprüfung dieses Laufs
    (siehe `einrichtung_offen_aus_umgebung`). Ist sie `None` UND meldet
    `setup_geprueft=False`, dass sie gar nicht gelaufen ist, gibt es keine
    Entscheidungsgrundlage: dann Exit 2 (Werkzeugfehler), nicht Exit 0.
    """
    umgebung = dict(os.environ) if umgebung is None else umgebung
    http = http or HTTP
    jetzt = jetzt or dt.datetime.now(dt.timezone.utc)
    quelle = quelle or _quelle_bestimmen(umgebung=umgebung)
    token = aktion_token(umgebung) or lese_token(umgebung)

    if einrichtung_offen is None and not setup_geprueft:
        return {"messbar": False, "befunde": [], "exit": EXIT_WERKZEUG,
                "text": ("Die Einrichtungsprüfung dieses Laufs hat ihr Ergebnis nicht "
                         "hinterlassen – ohne sie wäre jede Antwort geraten. Kein Grün, "
                         "kein Leerlauf-Rat (Vorgang WF-3150)."),
                "quellen": []}

    # Zwei Aussagen, zwei Läufe (#1030, 12.11.2026): Ohne `workflow` werden
    # BEIDE Höhen gemessen. Eine nicht lesbare Quelle ist kein Grund, das
    # ganze Urteil zu verweigern – solange EINE gelesen wurde, ist sie im
    # `quellen`-Feld benannt („nicht geprüft“ bleibt so sichtbar statt still).
    dateien = (workflow.strip(),) if workflow and workflow.strip() else URTEIL_QUELLEN
    jobs: list[dict] = []
    gelesen: list[str] = []
    fehlschlaege: list[tuple[str, int, str]] = []
    for datei in dateien:
        status, teil, meldung = _jobs_des_juengsten(quelle, token, datei, http)
        if status != 200:
            fehlschlaege.append((datei, status, meldung))
            continue
        gelesen.append(datei)
        jobs.extend(teil)

    if not gelesen:
        datei, status, meldung = fehlschlaege[0]
        return {"messbar": False, "befunde": [], "exit": EXIT_WERKZEUG,
                "text": f"Lauf-Historie nicht lesbar ({datei}: HTTP {status}: {meldung}).",
                "quellen": []}

    leerlauf = pruefe_leerlauf(jobs, bool(umgebung.get("BACKUP_REPO")),
                               bool(umgebung.get("BACKUP_PASSPHRASE")), jetzt)
    schritte = [s for j in jobs for s in (j.get("steps") or []) if isinstance(s, dict)]
    schein = pruefe_scheinbeweis(schritte, jetzt)
    befunde = leerlauf + schein

    # Vorrang ist Absicht: Ist die Einrichtung offen, ist SIE die Antwort –
    # der Leerlauf ist dann die Folge, nicht die Ursache. Ob E1–E8 offen sind,
    # weiß nur die Einrichtungsprüfung des Workflows (Schritt „Voraussetzungen
    # prüfen“); hier wird sie übergeben, nicht geraten. Der Workflow ruft
    # diesen Schritt erst NACH einer grünen Einrichtungsprüfung auf – deshalb
    # ist der Leerlauf dort erreichbar (Exit 4).
    if einrichtung_offen:
        return {"messbar": True, "befunde": befunde, "exit": EXIT_EINRICHTUNG,
                "text": (f"Einrichtung offen ({', '.join(einrichtung_offen)}) – das ist "
                         "der Inhaber-Weg, ein Anstoß ändert daran nichts."),
                "quellen": gelesen}
    if leerlauf:
        return {"messbar": True, "befunde": befunde, "exit": EXIT_LEERLAUF,
                "text": "Ein Lauf ist grün, gesichert wurde aber nichts.",
                "quellen": gelesen}
    if schein:
        return {"messbar": True, "befunde": befunde, "exit": EXIT_BEFUND,
                "text": "Der Rückweg-Nachweis fehlt – der Befund ist nicht bewiesen.",
                "quellen": gelesen}
    return {"messbar": True, "befunde": [], "exit": 0,
            "text": "Kein Befund auf Job-Ebene: Der jüngste zeugende Lauf ist belegt.",
            "quellen": gelesen}


def vertrag() -> int:
    """Gibt den Klassen- und Rechte-Vertrag aus und prüft ihn (echter Vertrag).

    Ein Vertrag, den niemand prüft, ist eine Beschreibung. Deshalb endet dieser
    Aufruf rot, wenn die Zusagen nicht mehr stimmen – er läuft im Workflow
    VOR der Heilung (fail-closed).
    """
    fehler: list[str] = []
    heilbar = {k for k, v in KLASSEN.items() if v.get("heilbar")}
    if heilbar != {"scheduler"}:
        fehler.append(f"Nur `scheduler` darf heilbar sein – gefunden: {sorted(heilbar)}")
    for klasse, eintrag in KLASSEN.items():
        if not str(eintrag.get("grund") or "").strip():
            fehler.append(f"Klasse `{klasse}` nennt keinen Grund")
    post = [p for p in ENDPUNKTE if "dispatches" in p]
    if len(post) != 1:
        fehler.append("Genau EIN Schreib-Endpunkt (dispatches) ist erlaubt")
    if not any("dispatches" in p for p in ENDPUNKTE):
        fehler.append("Der Anstoß-Endpunkt fehlt in ENDPUNKTE")

    print("Backup-Selbstheilung · Vertrag")
    print(f"  Endpunkte: {len(ENDPUNKTE)} (nur `/dispatches` schreibt)")
    for klasse in sorted(KLASSEN):
        eintrag = KLASSEN[klasse]
        marke = "heilbar" if eintrag["heilbar"] else "nicht heilbar"
        print(f"  [{klasse}/{marke}] {eintrag['grund']}")
    print(f"  Exit: 0 kein Befund · {EXIT_BEFUND} Scheinbeweis · "
          f"{EXIT_EINRICHTUNG} Einrichtung (Vorrang) · {EXIT_LEERLAUF} Leerlauf · "
          f"{EXIT_WERKZEUG} Werkzeugfehler")
    print(f"  Messhöhe: Job-Ebene, jüngster Lauf MIT Schritten ({FRISCHE_WORKFLOW}, {WORKFLOW})")
    if fehler:
        for eintrag in fehler:
            print(f"❌ {eintrag}")
        print(f"🛑 Vertrag verletzt: {len(fehler)} Abweichung(en).")
        return 1
    print("✅ Vertrag eingehalten.")
    return 0


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

    # S19: Der Klassenvertrag – heilbar ist GENAU der nicht gestartete Lauf (H2)
    if {k for k, v in KLASSEN.items() if v["heilbar"]} != {"scheduler"}:
        fehler.append("S19a: es darf nur `scheduler` heilbar sein")
    for klasse in ("leerlauf", "scheinbeweis", "einrichtung"):
        if klasse not in KLASSEN or KLASSEN[klasse]["heilbar"]:
            fehler.append(f"S19b: `{klasse}` fehlt oder gilt als heilbar")
        elif not str(KLASSEN[klasse]["grund"]).strip():
            fehler.append(f"S19c: `{klasse}` nennt keinen Grund")

    # S20: Der grüne Leerlauf – Job-Ebene, der KV-Job ist KEIN Zeuge
    gruen = [{"name": "backup", "conclusion": "success"}]
    if len(pruefe_leerlauf(gruen, "", False, jetzt)) != 1:
        fehler.append("S20a: grüner backup-Job ohne Ziel/Passphrase muss gemeldet werden")
    if pruefe_leerlauf(gruen, "a/b", True, jetzt) != []:
        fehler.append("S20b: mit Ziel und Passphrase ist derselbe Job kein Befund")
    kv = [{"name": "KV-/D1-Backup (Abonnenten + Einwilligungsnachweise)",
           "conclusion": "success"}]
    if pruefe_leerlauf(kv, "", False, jetzt) != []:
        fehler.append("S20c: der KV-Job ist kein Zeuge für das Repo-Artefakt")
    if pruefe_leerlauf([{"name": "backup", "conclusion": "failure"}], "", False, jetzt) != []:
        fehler.append("S20d: ein roter Job ist kein Leerlauf (er ist rot)")
    if not pruefe_scheinbeweis([{"name": "Kurzpruefung Wiederherstellbarkeit "
                                         "(strukturell, ohne Secrets)",
                                 "conclusion": "skipped"}], jetzt):
        fehler.append("S20e: ein übersprungener Rückweg-Nachweis ist ein Befund")

    # S20f: Reihenfolge der Antworten – offene Einrichtung hat Vorrang (Exit 3)
    if _leerlauf_urteil(gruen, {"BACKUP_REPO": "", "BACKUP_PASSPHRASE": ""}, jetzt,
                        einrichtung_offen=["BACKUP_REPO"])["exit"] != EXIT_EINRICHTUNG:
        fehler.append("S20f: offene Einrichtung muss Vorrang vor dem Leerlauf haben")
    if _leerlauf_urteil(gruen, {"BACKUP_REPO": "", "BACKUP_PASSPHRASE": ""},
                        jetzt)["exit"] != EXIT_LEERLAUF:
        fehler.append("S20g: nach grüner Einrichtungsprüfung ist der Leerlauf Exit 4")
    if _leerlauf_urteil(gruen, {"BACKUP_REPO": "a/b", "BACKUP_PASSPHRASE": "x"},
                        jetzt)["exit"] != 0:
        fehler.append("S20h: ein belegter grüner Job ist kein Leerlauf")

    # S22 (#1030, 10.11.2026): OHNE Auskunft der Einrichtungsprüfung wird nicht
    # geraten. Lauf 42715328453 zeigte, was Raten kostet: derselbe Lauf trug
    # zwei Rote Stellen mit zwei verschiedenen Ratschlägen – und der zweite
    # („ein Lauf ist grün, gesichert wurde nichts“) war schlicht falsch.
    if einrichtung_offen_aus_umgebung({}) is not None:
        fehler.append("S22a: ohne OFFENE_EINRICHTUNG darf es keine Antwort geben (None)")
    if einrichtung_offen_aus_umgebung({UMGEBUNG_OFFEN: ""}) != []:
        fehler.append("S22b: leerer Wert heißt „geprüft, nichts offen“")
    if einrichtung_offen_aus_umgebung({UMGEBUNG_OFFEN: "E1,E3; E5"}) != ["E1", "E3", "E5"]:
        fehler.append("S22c: Kennungen müssen auch mit Komma/Semikolon gelesen werden")
    if einrichtung_offen_aus_umgebung({UMGEBUNG_OFFEN: "E9 BACKUP_REPO"}) is not None:
        fehler.append("S22d: unbekannte Kennung ist „nicht lesbar“, kein Einrichtungspunkt")
    ohne_auskunft = betreibe_urteil({"GITHUB_REPOSITORY": "a/b", "GH_TOKEN": "t"}, jetzt=jetzt,
                                    http=lambda *a, **k: (_ for _ in ()).throw(
                                        AssertionError("ohne Auskunft darf niemand gefragt werden")))
    if ohne_auskunft["exit"] != EXIT_WERKZEUG or "nicht hinterlassen" not in ohne_auskunft["text"]:
        fehler.append(f"S22e: ohne Auskunft muss Exit 2 kommen, war {ohne_auskunft}")
    # Gegenprobe: MIT Auskunft (leer = geprüft) ist derselbe Aufruf grün.
    geprueft = _leerlauf_urteil([], {"BACKUP_REPO": "a/b", "BACKUP_PASSPHRASE": "x"}, jetzt)
    if geprueft["exit"] != 0 or not geprueft["messbar"]:
        fehler.append(f"S22f: geprüfte, leere Auskunft muss grün sein: {geprueft}")

    # S21: Ein geskippter Lauf ist kein Zeuge – er darf gar nicht befragt werden
    leer = {"id": 2, "conclusion": "skipped", "created_at": "2026-11-07T15:24:31Z"}
    echt = {"id": 1, "conclusion": "failure", "created_at": "2026-11-06T19:48:59Z"}
    gelesen: list[str] = []

    def zeugen_http(methode, url, kopf):
        gelesen.append(url)
        if url.endswith("/runs?per_page=20"):
            return 200, {"workflow_runs": [leer, echt]}, ""
        return 200, {"jobs": [{"name": "backup", "conclusion": "failure", "steps": [
            {"name": "Bundle + Arbeitskopie erstellen", "conclusion": "failure"}]}]}, ""

    schritte = _schritte_des_juengsten("a/b", "t", FRISCHE_WORKFLOW, zeugen_http)
    if not schritte:
        fehler.append("S21a: der zeugende Lauf hätte Schritte liefern müssen")
    if any("/runs/2/jobs" in u for u in gelesen):
        fehler.append("S21b: der geskippte Lauf darf gar nicht erst befragt werden")
    if _zeugt_lauf(leer) or not _zeugt_lauf(echt):
        fehler.append("S21c: `_zeugt_lauf` verwechselt Platzhalter und Zeugen")

    # S23 (#1030, 12.11.2026): ZWEI AUSSAGEN, ZWEI LÄUFE – ohne `--workflow`
    # misst `betreibe_urteil` BEIDE Höhen. Vorher las `--leerlauf`
    # ausschließlich `backup-offsite.yml`; ein übersprungener Rückweg-Nachweis
    # in der Frischwache war für dieses Modul unsichtbar, obwohl
    # `pruefe_scheinbeweis` genau ihn beschreibt (eine Prüfung, die nur eine
    # Quelle liest, meldet für die andere „kein Befund“ – das ist kein Grün,
    # das ist eine Lücke).
    offsite_jobs = [{"name": "backup", "conclusion": "success",
                     "steps": [{"name": "Bundle + Arbeitskopie erstellen",
                                "conclusion": "success"}]}]
    frisch_jobs = [{"name": "Backup-Frische pruefen (RPO 24 h / 52 h)",
                    "conclusion": "failure",
                    "steps": [{"name": "Kurzpruefung Wiederherstellbarkeit "
                                       "(strukturell, ohne Secrets)",
                               "conclusion": "skipped"}]}]
    umgebung_voll = {"GITHUB_REPOSITORY": "a/b", "GH_TOKEN": "t",
                     "BACKUP_REPO": "a/b", "BACKUP_PASSPHRASE": "x"}
    zustand = {"frisch": False}

    def verbund_http(methode, url, kopf, koerper=None):
        if "/runs?per_page=" in url:
            frisch = FRISCHE_WORKFLOW in url
            zustand["frisch"] = frisch
            return 200, {"workflow_runs": [{"id": 2 if frisch else 1,
                                            "conclusion": "failure",
                                            "created_at": "2026-11-11T19:57:09Z"}]}, ""
        return 200, {"jobs": frisch_jobs if zustand["frisch"] else offsite_jobs}, ""

    verbund = betreibe_urteil(umgebung_voll, jetzt=jetzt, http=verbund_http,
                              einrichtung_offen=[], setup_geprueft=True)
    if verbund.get("quellen") != list(URTEIL_QUELLEN):
        fehler.append(f"S23a: ohne --workflow müssen beide Läufe gelesen werden "
                      f"(gelesen: {verbund.get('quellen')})")
    if "scheinbeweis" not in [b["klasse"] for b in verbund["befunde"]]:
        fehler.append("S23b: der übersprungene Rückweg-Nachweis aus der Frischwache "
                      "fehlt im Urteil (gemessen wurde die falsche Höhe)")
    if verbund["exit"] != EXIT_BEFUND:
        fehler.append(f"S23c: erwartet Exit {EXIT_BEFUND} (Scheinbeweis), "
                      f"bekommen {verbund['exit']}")
    # Gegenprobe: MIT `--workflow` bleibt die Messung auf EINE Quelle begrenzt.
    einzeln = betreibe_urteil(umgebung_voll, jetzt=jetzt, http=verbund_http,
                              workflow=WORKFLOW, einrichtung_offen=[], setup_geprueft=True)
    if "scheinbeweis" in [b["klasse"] for b in einzeln["befunde"]]:
        fehler.append("S23d: mit --workflow darf nicht in der anderen Quelle gemessen werden")
    if einzeln.get("quellen") != [WORKFLOW]:
        fehler.append(f"S23e: mit --workflow muss genau diese Quelle gelesen werden "
                      f"(gelesen: {einzeln.get('quellen')})")
    # Eine nicht lesbare Quelle allein ist kein Werkzeugfehler, solange die
    # andere gelesen wurde – die Lücke steht dann in `quellen`, nicht im Stillschweigen.
    def halb_http(methode, url, kopf, koerper=None):
        if "/runs?per_page=" in url:
            if FRISCHE_WORKFLOW in url:
                return 404, {}, "Not Found"
            return 200, {"workflow_runs": [{"id": 1, "conclusion": "success",
                                            "created_at": "2026-11-11T19:57:09Z"}]}, ""
        return 200, {"jobs": offsite_jobs}, ""

    halb = betreibe_urteil(umgebung_voll, jetzt=jetzt, http=halb_http,
                           einrichtung_offen=[], setup_geprueft=True)
    if halb.get("quellen") != [WORKFLOW]:
        fehler.append(f"S23f: nicht lesbare Quelle darf die lesbare nicht verdrängen "
                      f"(gelesen: {halb.get('quellen')})")
    if halb["exit"] != 0:
        fehler.append(f"S23g: eine lesbare grüne Quelle bleibt grün, war {halb['exit']}")

    if fehler:
        for eintrag in fehler:
            print(f"❌ {eintrag}")
        print(f"🛑 backup_selbstheilung-Selbsttest: {len(fehler)} Abweichung(en).")
        return 1
    print("✅ backup_selbstheilung-Selbsttest: 23 Fallgruppen – Tagesfenster, Grenzen, "
          "laufende Sicherung, Mindestabstand, Budget, Lauf-Auswertung, ein Anstoß je Lauf, "
          "zweite Messung als einziger Grün-Nachweis, gescheiterter Lauf, 403, unlesbare "
          "Historie, Probe-Modus, Rechte-Trennung, Eingabe-Auflösung, Klassenvertrag, "
          "grüner Leerlauf (Job-Ebene), Zeugen-Filter, die Regel „ohne Auskunft der "
          "Einrichtungsprüfung wird nicht geraten“ und zwei Messhöhen (Offsite + "
          "Frischwache, #1030).")
    return 0


# =====================================================================
#  Kommandozeile
# =====================================================================
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Heilt eine fehlende oder überfällige Offsite-Sicherung (RPO-Kreis).")
    gruppe = ap.add_mutually_exclusive_group()
    gruppe.add_argument("--probe", action="store_true",
                        help="messen und entscheiden, aber nichts anstoßen (Standard)")
    gruppe.add_argument("--heilen", action="store_true",
                        help="messen, Sicherung anstoßen, warten, erneut messen")
    gruppe.add_argument("--plan", action="store_true",
                        help="Befunde auf Job-Ebene nach Klassen ordnen (nichts anstoßen)")
    gruppe.add_argument("--leerlauf", action="store_true",
                        help="nur den grünen Leerlauf und den Rückweg-Nachweis messen")
    ap.add_argument("--vertrag", action="store_true",
                    help="Klassen- und Rechte-Vertrag ausgeben und prüfen")
    ap.add_argument("--selftest", action="store_true", help="Offline-Selbsttest")
    ap.add_argument("--json", action="store_true", help="Maschinenlesbares Ergebnis")
    ap.add_argument("--ausgabe", default="", help="Ergebnis zusätzlich als JSON-Datei schreiben")
    ap.add_argument("--repo", default="", help="Backup-Repository (besitzer/name)")
    ap.add_argument("--quelle", default="", help="Quell-Repository (besitzer/name)")
    ap.add_argument("--workflow", default="",
                    help=("nur diese Workflow-Datei messen (Standard bei --leerlauf/--plan: "
                          "beide Höhen – Offsite-Lauf und Frischwache)"))
    ap.add_argument("--wartezeit", type=int, default=WARTEZEIT_S,
                    help="Sekunden, die auf den angestoßenen Lauf gewartet wird")
    ap.add_argument("--ohne-setup", action="store_true",
                    help=("Aufruf ohne Einrichtungsprüfung dieses Laufs (nur lokal von Hand): "
                          "OFFENE_EINRICHTUNG wird nicht gelesen und nicht geraten"))
    args = ap.parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.selftest:
        return selbsttest()
    if args.vertrag:
        return vertrag()

    umgebung = dict(os.environ)
    if args.plan or args.leerlauf:
        # Reine LESUNG: kein Dispatch, kein Schreibzugriff. Die Job-Ebene ist
        # die Messhöhe (WF-9E5A / #923) – ein KV-Job darf das Urteil über den
        # Repo-Job nicht verfälschen.
        #
        # #1030 (10.11.2026): Die Ursache kommt aus der Einrichtungsprüfung
        # DIESES Laufs, nicht aus einer Vermutung. `--ohne-setup` sagt
        # ausdrücklich, dass es sie nicht gab (lokaler Aufruf von Hand:
        # dann bleibt nur der Job-Befund, und der Grund wird als solcher
        # benannt). Im Workflow steht die Prüfung davor und füllt
        # `OFFENE_EINRICHTUNG`.
        #
        # 12.11.2026: Ohne `--workflow` misst das Urteil BEIDE Höhen – der
        # Rückweg-Nachweis steht in der Frischwache, nicht im Offsite-Lauf.
        offen = None if args.ohne_setup else einrichtung_offen_aus_umgebung(umgebung)
        urteil = betreibe_urteil(umgebung, quelle=args.quelle.strip(),
                                 workflow=args.workflow.strip(),
                                 einrichtung_offen=offen,
                                 setup_geprueft=bool(args.ohne_setup))
        if offen:
            print(f"Ursache zuerst: Die Einrichtung ist offen ({', '.join(offen)}) – "
                  "der Einrichtungsschritt desselben Laufs trägt den Rat.")
        for befund in urteil.get("befunde", []):
            print(f"  ⚠️ [{befund['klasse']}/nicht heilbar] {befund['text']}")
        quellen = urteil.get("quellen") or []
        if quellen:
            print(f"Gemessen: {', '.join(quellen)} (Job-Ebene, jüngster Lauf mit Schritten)")
        print(urteil["text"])
        print(f"Anleitung: {ANLEITUNG} (Abschnitt „Selbstheilung“)")
        if umgebung.get("GITHUB_ACTIONS") == "true":
            _anhaengen(umgebung.get("GITHUB_STEP_SUMMARY", ""),
                       "\n".join([f"- [{b['klasse']}] {b['text']}"
                                  for b in urteil.get("befunde", [])]) + "\n")
        return int(urteil["exit"])

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
