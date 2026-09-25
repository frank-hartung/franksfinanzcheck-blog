#!/usr/bin/env python3
"""newsletter_cadence.py – die Kadenz-Wache des Newsletter-Daily-Laufs.

WARUM (23.09.2026): Der planmäßige Cron des Newsletter-Daily (05:05 UTC,
Mo–Fr) blieb an diesem Werktag KOMPLETT aus – kein Lauf, kein Rotton, keine
Meldung. GitHub verwirft oder verschiebt `schedule`-Ereignisse unter Last
(am Vortag kam der 05:05-Cron erst ~10:05 UTC, an diesem Tag gar nicht).
Ein Lauf, der nie startet, kann nicht rot werden: Er erzeugt kein Ereignis
für das Fehler-Alerting, keine Annotation, nichts. Ein täglicher Newsletter,
der still nicht läuft, ist die schlimmste Fehlerart, die dieses Repo kennt –
sie war genau die Lücke, die das Qualitäts-Gate-Vorfall-Dokument (18.09.)
„ausgefallen ist nicht bestanden“ nennt, nur für Workflows statt Rechtstexte.

Diese Wache zählt daher NACH, dienstags und freitags vormittags:

  * Existiert seit 03:30 UTC des Tages ÜBERHAUPT EIN Versuch des
    Newsletter-Daily-Laufs (queued, in_progress, success oder failure)?
  * NEIN → der planmäßige Digest ist still ausgefallen. Die Wache holt ihn
    nach: `gh workflow run newsletter-daily.yml -f planmaessig=true` – der
    Lauf verhält sich exakt wie der verpasste Cron (dieselbe Freigabestufe,
    echter Listen-Versand, sofern Secrets + Absender + Freischaltung es
    hergeben). Der Digest-Schutz des Skripts macht den Doppel-Fall ungefährlich:
    kommt der verschobene Cron doch noch, findet er einen leeren Digest vor
    („nichts zu senden“) und legt keine zweite Kampagne an.
  * JA → keine Aktion. Ein FEHLGESCHLAGENER Lauf ist kein Fall dieser Wache:
    er ist laut (roter Lauf, Annotation, Fehler-Alerting) und ein automatischer
    zweiter Sendeversuch wäre eine Betreiber-Entscheidung – der Versand ist
    bewusst fail-closed verriegelt, und genau so bleibt es.

Sicherheitshierarchie (unverändert gegenüber dem Cron):
  * Der Dispatch trägt `planmaessig=true` und damit dieselbe Freigabe wie der
    planmäßige Lauf – nicht mehr. Ohne Secrets wird weiterhin nur gebaut.
  * Die Wache selbst sendet nichts, kennt keine Adressen und keinen API-Key.

WER DIE WACHE RUFT (seit 25.09.2026 – der zweite Vorfall):
  Am Freitag, 25.09.2026 fiel der 04:30-Cron erneut aus – und die Wache
  gleich mit: ihr eigener 08:11-Cron kam ebenfalls nie (null Läufe seit
  ihrer Erstellung). Gemessen über alle Workflows des Repos lieferte GitHubs
  Scheduler an diesem Tag jedes Ereignis 5–5,5 h zu spät oder gar nicht. Ein
  Netz, das am selben Haken hängt wie die Last, ist kein Netz. Deshalb ruft
  jetzt der Cloudflare-Worker (newsletter-worker/, Cron Trigger, minuten-
  genau) diese Wache um 05:05 UTC per workflow_dispatch – 35 Minuten nach
  dem Soll-Termin. Der GitHub-Cron 08:11 bleibt als drittes Netz stehen.
  Folge für die Logik: „fällig“ ist der Tag ab SOLL + 30 Minuten
  (FAELLIG_AB, aus dem Versandvertrag gerechnet), nicht erst ab 08:11.

Nutzung:
    python3 scripts/newsletter_cadence.py --pruefen                 # zählt + holt ggf. nach
    python3 scripts/newsletter_cadence.py --pruefen --ohne-dispatch # nur zählen (Trockenlauf)
    python3 scripts/newsletter_cadence.py --selftest

Exit: 0 = Kadenz in Ordnung oder nachgeholt · 1 = Befund (Nachholen nicht
möglich oder fehlgeschlagen) · 2 = Selbsttest rot.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
from newsletter_schedule import VERSANDTAGE, RUECKBLICK_TAGE, send_uhrzeit_utc

WORKFLOW_DATEI = "newsletter-daily.yml"
WORKFLOW_NAME = "Newsletter-Daily (Capture-Wache + Digest)"

# Erwartung: cron „30 4 * * 2,5“ (SOLL_UTC aus dem Versandvertrag gerechnet,
# nicht abgeschrieben). Der Tag gilt als bedient, wenn ab 03:30 UTC (eine
# Stunde Gnade vor dem Soll-Termin) irgendein Versuch existiert.
# Fällig zur Nachkontrolle ist der Tag ab SOLL + 30 Minuten (05:00 UTC): der
# Worker-Taktgeber ruft die Wache um 05:05 UTC, GitHubs eigener Cron um 08:11
# UTC – beide dürfen entscheiden. Vor 05:00 ist ein Aufruf ein Ruhetag: der
# Digest ist noch gar nicht überfällig.
SOLL_UTC = send_uhrzeit_utc()
FENSTER_START_UHRZEIT = (dt.datetime.combine(dt.date(2026, 1, 1), SOLL_UTC)
                         - dt.timedelta(hours=1)).time()
FAELLIG_AB = (dt.datetime.combine(dt.date(2026, 1, 1), SOLL_UTC)
              + dt.timedelta(minutes=30)).time()
DISPATCH_VERSUCHE = 3           # der Nachhol-Call selbst ist ein Netz-Call
DISPATCH_PAUSE = (3.0, 8.0)


def parse_ts(wert: str) -> dt.datetime:
    ts = dt.datetime.fromisoformat(wert.strip().replace("Z", "+00:00"))
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=dt.timezone.utc)
    return ts.astimezone(dt.timezone.utc)


def iso(ts: dt.datetime) -> str:
    return ts.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def fenster_start(jetzt: dt.datetime) -> dt.datetime:
    """03:30 UTC des Tages, an dem der Cron erwartet wurde."""
    start = jetzt.astimezone(dt.timezone.utc).replace(hour=FENSTER_START_UHRZEIT.hour,
                                                      minute=FENSTER_START_UHRZEIT.minute,
                                                      second=0, microsecond=0)
    if jetzt < start:
        # Die Wache läuft nie vor 03:30 UTC; für Tests und manuelle Aufrufe
        # vor dem Soll-Fenster zählt der VORTAG als erwarteter Tag nicht –
        # ein Aufruf um 02:00 UTC prüft den KOMMENDEN Tag (der Cron um 04:30
        # ist noch gar nicht fällig → Ruhetag-Logik greift ohnehin).
        start -= dt.timedelta(days=1)
    return start


def entscheide(laeufe: list[dict], jetzt: dt.datetime) -> dict:
    """Die reine Entscheidung – ohne Netz, ohne Schreibzugriff, getestet.

    laeufe: Liste der letzten Runs des Workflows (jede Statuslage), je
    {"id", "status", "conclusion", "created_at" (ISO), "url", "event"}.
    → {"handlung": "ruhetag" | "bedient" | "nachholen" | "nachgeholen-moeglich",
       ...}
    """
    jetzt = jetzt.astimezone(dt.timezone.utc)
    if jetzt.weekday() not in VERSANDTAGE:
        return {"handlung": "ruhetag",
                "befund": f"{iso(jetzt)} ist kein Versandtag (Di/Fr ist der planmäßige "
                          f"Lauf erwartet) – keine Kadenz-Forderung.",
                "heutiger_lauf": None}
    if jetzt.time() < FAELLIG_AB:
        return {"handlung": "ruhetag",
                "befund": (f"Der Planlauf ist noch nicht zur Nachkontrolle fällig "
                           f"(Soll {SOLL_UTC:%H:%M} UTC, fällig ab {FAELLIG_AB:%H:%M} UTC)."),
                "heutiger_lauf": None}
    start = fenster_start(jetzt)
    versuche = []
    for l in laeufe:
        try:
            erstellt = parse_ts(l["created_at"])
        except (KeyError, ValueError):
            continue
        if start <= erstellt <= jetzt:
            versuche.append({**l, "_erstellt": erstellt})
    versuche.sort(key=lambda x: x["_erstellt"], reverse=True)
    if versuche:
        frisch = versuche[0]
        rot = (frisch.get("status") in ("completed",)
               and frisch.get("conclusion") not in ("success",))
        vermerk = ""
        if rot:
            vermerk = ("Der heutige Lauf ist ROT – das ist die Sache des "
                       "Fehler-Alertings (Meldung + Betreiber-Entscheid), nicht "
                       "einer automatischen Wiederholung: der Versand ist "
                       "fail-closed verriegelt und bleibt es.")
        elif frisch.get("status") != "completed":
            vermerk = "Der heutige Lauf ist noch unterwegs (queued/in_progress)."
        return {"handlung": "bedient",
                "befund": (f"Planlauf {frisch.get('id')} ({frisch.get('status')}"
                           f"/{frisch.get('conclusion')}) um {iso(frisch['_erstellt'])} "
                           f"existiert – Kadenz gewahrt. {vermerk}".strip()),
                "heutiger_lauf": {"id": frisch.get("id"), "status": frisch.get("status"),
                                  "conclusion": frisch.get("conclusion"),
                                  "created_at": iso(frisch["_erstellt"]),
                                  "url": frisch.get("url")}}
    return {"handlung": "nachholen",
            "befund": (f"Kein einziger Laufversuch von „{WORKFLOW_NAME}“ seit "
                       f"{iso(start)} (Soll: {SOLL_UTC:%H:%M} UTC) – der planmäßige "
                       f"Cron wurde von GitHub still verworfen oder ist nie angekommen. "
                       f"Der Digest wird planmäßig nachgeholt."),
            "heutiger_lauf": None}


def _gh(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], capture_output=True, text=True, timeout=120)


def lade_laeufe(repo: str) -> list[dict]:
    """Die letzten Runs des Newsletter-Daily (jede Statuslage)."""
    pfad = (f"repos/{repo}/actions/workflows/{WORKFLOW_DATEI}/runs"
            f"?per_page=40")
    r = _gh(["api", pfad, "--jq",
             '.workflow_runs[] | {id: (.id|tostring), status: .status, '
             'conclusion: .conclusion, created_at: .created_at, '
             'url: .html_url, event: .event}'])
    if r.returncode != 0:
        raise RuntimeError(f"gh api {pfad}: {(r.stderr or r.stdout or '').strip()[:300]}")
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


def hole_nach(repo: str, ref: str) -> tuple[int, str]:
    """Den verpassten Planlauf dispatchen (planmaessig=true = Cron-Freigabestufe)."""
    letzte_fehler = ""
    for versuch in range(DISPATCH_VERSUCHE):
        r = _gh(["workflow", "run", WORKFLOW_DATEI, "--repo", repo, "--ref", ref,
                 "-f", "planmaessig=true", "-f", f"tage={RUECKBLICK_TAGE}"])
        if r.returncode == 0:
            return 0, "Nachhol-Dispatch angenommen."
        letzte_fehler = (r.stderr or r.stdout or "").strip()[:300]
        # 422 „could not create workflow dispatch“ in den ersten Sekunden kann
        # ein Race mit einem parallel startenden Lauf sein – kurz warten, dann
        # erneut. Alles andere (Auth, fehlende actions:write) wiederholt sich
        # nicht sinnlos: sofort melden.
        if "422" not in letzte_fehler:
            break
        if versuch + 1 < DISPATCH_VERSUCHE:
            import time
            time.sleep(DISPATCH_PAUSE[min(versuch, len(DISPATCH_PAUSE) - 1)])
    return 1, f"Nachhol-Dispatch fehlgeschlagen: {letzte_fehler}"


def pruefen(repo: str, *, jetzt: dt.datetime | None = None, ref: str = "main",
            ohne_dispatch: bool = False,
            laeufe: list[dict] | None = None) -> dict:
    jetzt = jetzt or dt.datetime.now(dt.timezone.utc)
    if laeufe is None:
        laeufe = lade_laeufe(repo)
    erg = entscheide(laeufe, jetzt)
    erg["jetzt"] = iso(jetzt)
    erg["repo"] = repo
    erg["ref"] = ref
    if erg["handlung"] == "nachholen":
        if ohne_dispatch:
            erg["dispatch"] = "uebersprungen (Trockenlauf)"
            erg["rc"] = 1
        else:
            code, meldung = hole_nach(repo, ref)
            erg["dispatch"] = meldung
            erg["rc"] = 0 if code == 0 else 1
    elif erg["handlung"] == "ruhetag":
        erg["dispatch"] = "nicht nötig (Ruhetag)"
        erg["rc"] = 0
    else:
        erg["dispatch"] = "nicht nötig (Lauf existiert)"
        erg["rc"] = 0
    return erg


def als_md(erg: dict) -> str:
    zeilen = ["## 📮 Newsletter-Kadenz", "",
              f"**Gefunden ({erg['jetzt']}):** {erg['befund']}", "",
              f"**Aktion:** {erg['dispatch']}"]
    if erg.get("heutiger_lauf"):
        l = erg["heutiger_lauf"]
        zeilen += ["", f"Letzter Lauf heute: [{l['id']}]({l.get('url', '')}) – "
                       f"{l['status']}/{l.get('conclusion')} um {l['created_at']}"]
    return "\n".join(zeilen)


def _selftest() -> int:
    fehler: list[str] = []
    zaehler = 0

    def pruefe(bedingung: bool, meldung: str) -> None:
        nonlocal zaehler
        if bedingung:
            zaehler += 1
        else:
            fehler.append(meldung)

    # Der ursprüngliche Ausfall vom Mittwoch wird mit der neuen Di/Fr-Kadenz
    # an einem Freitag (25.09.2026) nachgestellt.
    freitag = dt.datetime(2026, 9, 25, 8, 11, tzinfo=dt.timezone.utc)
    dienstag_spaet = dt.datetime(2026, 9, 22, 10, 5, tzinfo=dt.timezone.utc)
    samstag = dt.datetime(2026, 9, 26, 8, 11, tzinfo=dt.timezone.utc)

    def lauf(cid: str, erstellt: str, status: str = "completed",
             conclusion: str = "success") -> dict:
        return {"id": cid, "status": status, "conclusion": conclusion,
                "created_at": erstellt, "url": f"https://example.invalid/{cid}",
                "event": "schedule"}

    # 1) Ruhetag: kein Lauf nötig, keine Forderung
    e = entscheide([], samstag)
    pruefe(e["handlung"] == "ruhetag", f"Samstag ≠ Ruhetag: {e}")

    # 2) Der Vorfall: Freitag, kein einziger Versuch → nachholen
    e = entscheide([lauf("alt", "2026-09-22T10:05:00Z")], freitag)
    pruefe(e["handlung"] == "nachholen", f"Vorfall nicht erkannt: {e}")
    pruefe("04:30" in e["befund"], f"Befund nennt den Soll-Termin nicht: {e['befund']}")

    # 3) Grenze des Fensters: ein Lauf um 03:29 zählt nicht, 03:30 zählt
    e = entscheide([lauf("frueh", "2026-09-25T03:29:00Z")], freitag)
    pruefe(e["handlung"] == "nachholen", f"03:29-Lauf fälschlich gezählt: {e}")
    e = entscheide([lauf("puenktlich", "2026-09-25T03:30:00Z")], freitag)
    pruefe(e["handlung"] == "bedient", f"03:30-Lauf nicht gezählt: {e}")

    # 4) Verschobener Cron ist auch bedient (10:05 am Vortag ist KEIN Fall –
    #    gestern zählt nicht, heute zählt nur heute)
    e = entscheide([lauf("gestern", "2026-09-22T10:05:00Z")], freitag)
    pruefe(e["handlung"] == "nachholen", f"gestriger Lauf als heutiger gezählt: {e}")

    # 5) Lauf unterwegs (queued/in_progress) = bedient, kein Doppel-Dispatch
    e = entscheide([lauf("unterwegs", "2026-09-25T06:30:00Z", status="in_progress")],
                   freitag)
    pruefe(e["handlung"] == "bedient" and "unterwegs" in e["befund"],
           f"laufender Lauf nicht als bedient erkannt: {e}")

    # 6) Roter Lauf = bedient (laut!), aber mit Vermerk – kein Auto-Retry
    e = entscheide([lauf("rot", "2026-09-25T05:07:00Z", conclusion="failure")], freitag)
    pruefe(e["handlung"] == "bedient" and "ROT" in e["befund"],
           f"roter Lauf ohne Vermerk: {e}")

    # 7) Unverständliche Zeitstempel werfen den Lauf nicht um
    e = entscheide([{"id": "x", "status": "completed", "conclusion": "success",
                     "created_at": "Müll", "url": "", "event": "schedule"}], freitag)
    pruefe(e["handlung"] == "nachholen", f"ungültiger Timestamp bricht die Zählung: {e}")

    # 8) pruefen()-Verdrahtung mit injizierten Läufen + Trockenlauf
    erg = pruefen("org/repo", jetzt=freitag, ohne_dispatch=True,
                  laeufe=[lauf("alt", "2026-09-22T10:05:00Z")])
    pruefe(erg["rc"] == 1 and erg["dispatch"].startswith("uebersprungen"),
           f"Trockenlauf soll Befund rc=1 liefern: {erg}")
    erg = pruefen("org/repo", jetzt=freitag, ohne_dispatch=True,
                  laeufe=[lauf("heute", "2026-09-25T05:06:00Z")])
    pruefe(erg["rc"] == 0, f"bedienter Tag soll rc=0 liefern: {erg}")
    erg = pruefen("org/repo", jetzt=samstag, ohne_dispatch=True, laeufe=[])
    pruefe(erg["rc"] == 0, f"Ruhetag soll rc=0 liefern: {erg}")

    # 9) Fensterlogik in den Morgenstunden: ein Aufruf um 02:00 UTC liegt
    #    VOR dem Fensterstart 03:30 – der Start fällt damit auf den Vortag.
    #    Bewusst so: zwischen 00:00 und 03:30 UTC ist der laufende Tag noch
    #    nicht fällig (Soll ist 04:30), die Wache läuft regulär erst 08:11.
    frueh = dt.datetime(2026, 9, 25, 2, 0, tzinfo=dt.timezone.utc)
    start = fenster_start(frueh)
    pruefe(start == dt.datetime(2026, 9, 24, 3, 30, tzinfo=dt.timezone.utc),
           f"Fensterstart vor 03:30 falsch: {iso(start)}")

    # 10) Dienstag 10:05 mit heutigem (dienstägigem) Lauf = bedient – der
    #     verspätet gekommene Cron zählt als heutiger Lauf
    e = entscheide([lauf("spaet", "2026-09-22T10:05:00Z")], dienstag_spaet)
    pruefe(e["handlung"] == "bedient", f"verspäteter Cron nicht als bedient: {e}")

    # 11) Der Taktgeber-Ruf (Worker, 05:05 UTC): fällig ab SOLL+30 min –
    #     ein leerer Freitag um 05:05 ist ein Fall, um 04:45 noch keiner.
    pruefe(SOLL_UTC == dt.time(4, 30), f"SOLL_UTC aus dem Vertrag: {SOLL_UTC}")
    pruefe(FAELLIG_AB == dt.time(5, 0), f"FAELLIG_AB = SOLL+30min: {FAELLIG_AB}")
    pruefe(FENSTER_START_UHRZEIT == dt.time(3, 30),
           f"Fensterstart = SOLL-1h: {FENSTER_START_UHRZEIT}")
    takt = dt.datetime(2026, 9, 25, 5, 5, tzinfo=dt.timezone.utc)
    e = entscheide([], takt)
    pruefe(e["handlung"] == "nachholen", f"Taktgeber-Ruf 05:05 ohne Lauf muss nachholen: {e}")
    e = entscheide([lauf("takt", "2026-09-25T04:30:20Z")], takt)
    pruefe(e["handlung"] == "bedient", f"vom Taktgeber gestarteter Lauf nicht gezählt: {e}")
    zu_frueh = dt.datetime(2026, 9, 25, 4, 45, tzinfo=dt.timezone.utc)
    e = entscheide([], zu_frueh)
    pruefe(e["handlung"] == "ruhetag" and "fällig" in e["befund"],
           f"04:45 ist noch nicht fällig: {e}")

    if fehler:
        print("🛑 newsletter_cadence-Selbsttest FEHLGESCHLAGEN:")
        for f in fehler:
            print("  -", f)
        return 2
    print(f"✅ newsletter_cadence-Selbsttest: {zaehler} Fälle grün (Ruhetag, "
          f"Vorfall-Erkennung, Fenstergrenze, Vortags-Abgrenzung, laufender/"
          f"roter Lauf, Müll-Timestamp, Trockenlauf-Verdrahtung, "
          f"Fensterlogik, Taktgeber-Ruf ab SOLL+30min).")
    return 0


def main(argv=None) -> int:
    ap = __import__("argparse").ArgumentParser(
        description="Newsletter-Kadenz-Wache: zählt den planmäßigen Lauf nach")
    ap.add_argument("--pruefen", action="store_true")
    ap.add_argument("--ohne-dispatch", action="store_true",
                    help="nur zählen und melden – nichts nachholen (Trockenlauf)")
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    ap.add_argument("--ref", default=os.environ.get("GITHUB_REF_NAME", "main"),
                    help="Branch, auf dem der Nachhol-Lauf startet (default: ausgelöster Ref, sonst main)")
    ap.add_argument("--md", action="store_true", help="Report als Markdown (Step-Summary)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    if not args.pruefen:
        ap.error("entweder --pruefen oder --selftest")
    if not args.repo:
        print("❌ kein Repo bekannt (GITHUB_REPOSITORY oder --repo) – Zählung wäre blind.")
        return 1
    erg = pruefen(args.repo, ref=args.ref, ohne_dispatch=args.ohne_dispatch)
    if args.md:
        print(als_md(erg))
    else:
        print(erg["befund"])
        print(f"Aktion: {erg['dispatch']}")
    return erg["rc"]


if __name__ == "__main__":
    sys.exit(main())
