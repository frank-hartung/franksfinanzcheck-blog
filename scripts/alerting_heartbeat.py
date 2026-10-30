#!/usr/bin/env python3
"""alerting_heartbeat.py – zählt die `workflow_run`-Zustellung des Fehler-Alertings nach.

WARUM (18.09.2026 – Befund E des Qualitäts-Gate-Vorfalls)
---------------------------------------------------------
Das zentrale Fehler-Alerting (`alert-on-failure.yml` = „Fehler-Alerting") ist
KORREKT konfiguriert: 39 gelistete Workflow-Namen stimmen byteweise,
`types: [completed]` steht, der Alarm-Job hängt an `failure/cancelled` und der
Schließ-Job an `success`. Trotzdem kam binnen zehn Tagen rund ein Drittel der
Ereignisse nie an (repo-weit 602 Alerting-Läufe auf 922 abgeschlossene Läufe
gelisteter Workflows, 08.–18.09.2026). Vierzehn rote Läufe des Qualitäts-Gates
erzeugten null Meldungen; der Betreiber erfuhr vom roten Gate nur durch
Nachschauen. Der operative Schaden blieb derselbe wie beim Gate: Deploy hatte 13 rote
Läufe ohne Meldung, das Lesehilfen-Gate 9 – Rot, von dem niemand erfährt.

Ereignisse, auf die man sich verlässt, ohne sie zu zählen, sind Wunschdenken.
Dieser Herzschlag macht dieselbe Rechnung wie der Vorfall-Bericht – jeden Tag:

    abgeschlossene Läufe gelisteter Workflows (letzte 26 h, mit Gnadenfrist)
        GEGEN
    erstellte Läufe von „Fehler-Alerting" (Event workflow_run)

Jeder abgeschlossene Lauf eines gelisteten Workflows MÜSSTE genau einen
Alerting-Lauf auslösen (bei Erfolg der Schließpfad, bei Rot der Alarm). Ein
Lauf ohne zugehörigen Alerting-Lauf ist ein verlorenes Ereignis.

Urteil:
  · EIN ungedeckter ROTER Lauf (failure/timed_out) ist immer ein Befund –
    genau das ist der Vorfall: Rot, von dem niemand erfährt.
  · Zwei oder mehr verlorene Ereignisse im Fenster sind ein Befund –
    Einzelverluste kommen als GitHub-Flake vor (Hinweis), Muster nicht.
  · Ein einzelner Verlust ist ein Hinweis (beobachten, nicht eskalieren).

KANAL-PROBE (WF-829B / #922, 30.10.2026)
----------------------------------------
Am 29./30.10.2026 war der Meldeweg selbst tot: In
`alert-on-failure.yml` stand nach zwei Zusammenschnitten eine doppelte
`const`-Deklaration im `github-script`-Block. Der Runner führt den Block als
Funktion aus, also starb JEDER Lauf mit `SyntaxError` – und jede Zustellung
blieb aus. Die Erkennung dafür existierte bereits (`workflow_js_wache.py`,
seit #949) und schlug auch an: Der Lauf „Skript-Syntax" war rot. Gemeldet hat
es niemand, denn der Melder war derselbe tote Kanal.
    Ein Wächter, der über die gestörte Leitung alarmiert werden will,
    schweigt genau dann, wenn er gebraucht wird.
Dieser Herzschlag läuft per CRON und ist damit der EINZIGE Weg, der einen
toten Meldeweg noch melden kann. Er prüft ihn deshalb selbst, vor jeder
Zählung: `--kanal`.

Meldung: Das Skript schreibt nichts ins Repo (C15) und öffnet selbst nichts –
der Workflow `.github/workflows/alerting-heartbeat.yml` läuft per CRON (nie
per workflow_run – das wäre der beobachtete Kanal, der bewiesenermaßen
verliert) und meldet sich selbst wie das Qualitäts-Gate: Issue öffnen/
aktualisieren bei Befund (`if: failure()`) und schließen bei Grün
(`if: success()`), Label `auto-report`, Titel HEARTBEAT_TITEL.

Nutzung:
    python3 scripts/alerting_heartbeat.py              # Zählung gegen GitHub-API
    python3 scripts/alerting_heartbeat.py --md         # Bericht als Markdown
    python3 scripts/alerting_heartbeat.py --selftest   # REINE Logik, ohne Netz

Exit: 0 = Zustellung vollständig (oder nur Einzel-Flake) · 1 = Befund ·
2 = Werkzeugfehler (kein gh/Token, API defekt)
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
from typing import Callable

import workflow_js_wache

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALERTING_DATEI = os.path.join(".github", "workflows", "alert-on-failure.yml")
ALERTING_NAME = "Fehler-Alerting"
ISSUE_TITEL = "🫀 Alerting-Herzschlag: workflow_run-Zustellung verliert Ereignisse"
# Eigene Meldung für den Fall, dass der MELDEWEG selbst nicht lauffähig ist.
# Ein eigener Titel (nicht der Zustell-Titel): Die Zählung ist dann nicht
# „verloren", sondern gar nicht erst möglich – der Rat ist ein anderer.
ISSUE_TITEL_KANAL = "🫀 Alerting-Kanal: das Fehler-Alerting selbst ist nicht lauffähig"

# Fenster-Modell: gezählt wird [jetzt-26 h, jetzt-90 min]. Die Gnadenfrist
# deckelt Fehlmeldungen: ein Lauf, der gerade eben endete, darf sein
# Ereignis noch ausliefern (gemessene echte Verzögerung im Vorfall: 43 min —
# 90 min ist doppelt großzügig). Zuordnung: ein Alerting-Lauf, der zwischen
# (Abschluss − 5 min) und (Abschluss + 90 min) erstellt wurde, gehört zum
# abgeschlossenen Lauf.
FENSTER_STUNDEN = 26
GNADE_MINUTEN = 90
MATCH_MINUTEN = 90
VORLAUF_MINUTEN = 5

ABGESCHLOSSEN = {"success", "failure", "cancelled", "timed_out"}
ROT = {"failure", "timed_out"}


def parse_ts(wert: str) -> dt.datetime:
    """ISO-8601 aus der Actions-API → aware UTC (Ṅ schluckt 'Z' unter 3.11+,
    wir ersetzen trotzdem, damit die Funktion überall dasselbe tut)."""
    ts = dt.datetime.fromisoformat(wert.strip().replace("Z", "+00:00"))
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=dt.timezone.utc)
    return ts.astimezone(dt.timezone.utc)


def iso(ts: dt.datetime) -> str:
    return ts.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def gelistete_workflows(text: str, use_yaml: bool = True) -> list[str]:
    """Die beobachteten Workflows der `alert-on-failure.yml` – aus der Datei
    selbst, nie abgetippt (die Handkopie ist die Fehlerklasse, die dieses
    Haus am 18.09.2026 zweimal gebissen hat: Wachen-Liste im Gate,
    Selbsttest-Liste in der Reserve).

    Zwei Wege, gleiche Erwartung:
      · PyYAML, mit Augenmerk auf die YAML-1.1-Falle: der Schlüssel `on`
        wird von safe_load zu `True` konvertiert. Wer nur daten["on"]
        probiert, liest eine leere Wache – und die Zählung wäre blind,
        ohne dass es jemand merkt.
      · Regex-Fallback über den `workflows:`-Block, falls PyYAML fehlt:
        Zeilen `- "Name"` / `- 'Name'` bis zum Ende der Einrückung.
    """
    if use_yaml:
        try:
            import yaml
            daten = yaml.safe_load(text) or {}
            on = daten.get("on", daten.get(True)) or {}
            if isinstance(on, str):           # on: push  (ohne workflow_run)
                return []
            wfr = (on.get("workflow_run") or {})
            namen = wfr.get("workflows") or []
            aus, gesehen = [], set()
            for n in namen:
                n = str(n).strip()
                if n and n not in gesehen:
                    aus.append(n)
                    gesehen.add(n)
            return aus
        except Exception:                     # noqa: BLE001 – Fallback unten
            pass
    # Fallback: Rohtext. Der `workflows:`-Block beginnt eingerückt unter
    # `workflow_run:` und endet, sobald eine Zeile wieder weniger weit
    # einrückt (z. B. `types:`).
    aus, gesehen, in_block, basis = [], set(), False, 0
    eintrag = re.compile(r"""^(\s*)-\s+["']?([^"'\n]+?)["']?\s*(?:#.*)?$""")
    for zeile in text.splitlines():
        streifen = zeile.strip()
        if re.match(r"""^workflow_run\s*:""", streifen):
            in_block, basis = False, 0
        if in_block:
            m = eintrag.match(zeile)
            if m and len(m.group(1)) > basis:
                name = m.group(2).strip()
                if name and name not in gesehen:
                    aus.append(name)
                    gesehen.add(name)
                continue
            if streifen and not streifen.startswith("#"):
                in_block = False
        if re.match(r"""^\s*workflows\s*:\s*(?:#.*)?$""", zeile):
            einr = re.match(r"""^(\s*)""", zeile).group(1)
            in_block, basis = True, len(einr)
    return aus


def fenster(jetzt: dt.datetime) -> tuple[dt.datetime, dt.datetime]:
    """(von, bis): gezählt wird, was im Fenster ABGESCHLOSSEN wurde – bis
    endet um die Gnadenfrist vor jetzt, damit gerade laufende Zustellungen
    nicht als verloren gelten."""
    bis = jetzt - dt.timedelta(minutes=GNADE_MINUTEN)
    return jetzt - dt.timedelta(hours=FENSTER_STUNDEN), bis


def abgleich(laeufe: list, alarme: list, jetzt: dt.datetime) -> dict:
    """Zählt Zustellung gegen Abschluss.

    laeufe: [{"name", "conclusion", "id", "url", "created_at", "completed_at"}]
            – nur gelistete Workflows, alle Conclusion-Arten roh.
    alarme: [dt.datetime] – created_at aller „Fehler-Alerting"-Läufe.
    """
    von, bis = fenster(jetzt)
    relevant = []
    uebersprungen = {"skipped": 0, "gnade": 0, "ausserhalb": 0}
    for lauf in laeufe:
        if lauf["conclusion"] not in ABGESCHLOSSEN:
            uebersprungen["skipped"] += 1
            continue
        fertig = lauf["completed_at"]
        if fertig > bis:
            uebersprungen["gnade"] += 1
            continue
        if fertig < von:
            uebersprungen["ausserhalb"] += 1
            continue
        relevant.append(lauf)

    def gedeckt(lauf) -> bool:
        lo = lauf["completed_at"] - dt.timedelta(minutes=VORLAUF_MINUTEN)
        hi = lauf["completed_at"] + dt.timedelta(minutes=MATCH_MINUTEN)
        return any(lo <= a <= hi for a in alarme)

    fehlend = [l for l in relevant if not gedeckt(l)]
    rot_offen = [l for l in fehlend if l["conclusion"] in ROT]

    befunde, hinweise = [], []
    if rot_offen:
        namen = ", ".join(f"`{l['name']}` ({l['conclusion']}, {iso(l['completed_at'])})"
                          for l in rot_offen)
        befunde.append(
            f"{len(rot_offen)} rote Läufe gelisteter Workflows erreichten nie das "
            f"Fehler-Alerting – niemand wurde informiert: {namen}. Genau das ist "
            "Befund E (14 rote Gate-Läufe ohne eine einzige Meldung).")
    if len(fehlend) >= 2:
        quote = round(100.0 * len(fehlend) / len(relevant), 1) if relevant else 0.0
        befunde.append(
            f"{len(fehlend)} von {len(relevant)} Ereignissen kamen nie an "
            f"({quote} % Verlust in {FENSTER_STUNDEN} h, Gnadenfrist {GNADE_MINUTEN} min). "
            "Vorfalls-Messung 08.–18.09.2026: ~35 % repo-weit.")
    elif len(fehlend) == 1:
        l = fehlend[0]
        hinweise.append(
            f"1 verlorenes Ereignis (`{l['name']}`, {l['conclusion']}, "
            f"{iso(l['completed_at'])}) – Einzel-Flake möglich, Beobachtung läuft.")

    return {"gesamt": len(relevant),
            "alarme": len(alarme),
            "fehlend": len(fehlend),
            "fehlend_laeufe": fehlend,
            "rot_offen": rot_offen,
            "uebersprungen": uebersprungen,
            "von": von, "bis": bis, "jetzt": jetzt,
            "befunde": befunde, "hinweise": hinweise}


def kanal_pruefen(datei: str = ALERTING_DATEI,
                  pruefen: Callable | None = None) -> dict:
    """Kann der Meldeweg selbst überhaupt laufen?

    Der `github-script`-Block in `alert-on-failure.yml` ist JavaScript in YAML
    und wird von keiner Python-Wache gesehen. Kompiliert er nicht, starb jeder
    Lauf an einem `SyntaxError` – und mit ihm jede Meldung. Geprüft wird mit
    derselben Wache, die auch im „Skript-Syntax"-Lauf steht (eine Wahrheit,
    zwei Orte): `workflow_js_wache.pruefen`.
    """
    messen = pruefen or workflow_js_wache.pruefen
    status, befunde, _md = messen()
    if status == 2:
        # Ohne `node` ist kein Block bestätigt: ausgefallene Messung ist kein
        # Grün (C33) – die Probe darf sich dann nicht beruhigt zurückziehen.
        return {"datei": datei, "status": 2, "befunde": list(befunde), "kanal": False}
    eigene = [b for b in befunde if datei in b]
    return {"datei": datei, "status": 1 if eigene else 0, "befunde": eigene,
            "kanal": not eigene}


def kanal_md(erg: dict) -> str:
    zeilen = [f"### {ISSUE_TITEL_KANAL}", "",
              f"**Geprüft:** `{erg['datei']}` · "
              "jeder `github-script`-Block kompiliert wie im Runner "
              "(`node --check`, umhüllt mit `(async () => { … })()`).", ""]
    if erg["status"] == 2:
        zeilen += ["🛑 **Nicht prüfbar** – ohne Kompilierung ist kein Block "
                   "bestätigt (C33)."] + [f"- {b}" for b in erg["befunde"]] + [""]
    elif erg["befunde"]:
        zeilen += ["🔴 **Der Meldeweg ist nicht lauffähig.** Jeder Lauf des "
                   "Fehler-Alertings stirbt an einem Syntaxfehler – es werden "
                   "keine Meldungen zugestellt, auch keine über diesen Befund.",
                   ""] + [f"- `{b}`" for b in erg["befunde"]] + [
            "", "Häufigste Ursache: ein Zusammenschnitt beim Zusammenführen "
                "(doppelte `const`-Zeile, zwei Zeichenketten ohne Komma). "
                "Heilung: die betroffene Datei in EINER Fassung setzen; "
                "lokal `python3 scripts/workflow_js_wache.py --check`.",
        ]
    else:
        zeilen += ["✅ Alle `github-script`-Blöcke des Fehler-Alertings "
                   "kompilieren – der Kanal ist lauffähig.", ""]
    zeilen += ["---",
               "Gemeldet vom Alerting-Herzschlag (`cron` – absichtlich NICHT "
               "über `workflow_run`). Dieser Befund kann NICHT über das "
               "Fehler-Alerting gemeldet werden: Er sagt ja gerade, dass es "
               "nicht läuft. Bei Grün wird die Meldung automatisch geschlossen."]
    return "\n".join(zeilen) + "\n"


def als_md(erg: dict) -> str:
    quote = round(100.0 * erg["fehlend"] / erg["gesamt"], 1) if erg["gesamt"] else 0.0
    L = [f"### {ISSUE_TITEL}", "",
         f"**Fenster:** {iso(erg['von'])} – {iso(erg['bis'])} UTC "
         f"(Gnadenfrist {GNADE_MINUTEN} min) · **Stand:** {iso(erg['jetzt'])}", "",
         "| Größe | Wert |", "|---|---|",
         f"| Abgeschlossene Läufe gelisteter Workflows | {erg['gesamt']} |",
         f"| Alerting-Läufe (workflow_run, gesamt im Fenster) | {erg['alarme']} |",
         f"| Ereignisse OHNE Alerting-Lauf | **{erg['fehlend']}** ({quote} %) |",
         f"| davon ROTE Läufe (failure/timed_out) | **{len(erg['rot_offen'])}** |",
         f"| Übersprungen: skipped / Gnadenfrist / außerhalb | "
         f"{erg['uebersprungen']['skipped']} / {erg['uebersprungen']['gnade']} / "
         f"{erg['uebersprungen']['ausserhalb']} |", ""]
    if erg["rot_offen"]:
        L += ["#### 🔴 Rote Läufe, über die nie alarmiert wurde", "",
              "| Workflow | Abschluss (UTC) | Run |", "|---|---|---|"]
        L += [f"| `{l['name']}` | {iso(l['completed_at'])} | "
              f"[{l['id']}]({l['url']}) |" for l in erg["rot_offen"]]
        L.append("")
    if erg["befunde"]:
        L += ["**Befunde:**"] + [f"- {b}" for b in erg["befunde"]] + [""]
    else:
        L += ["✅ Zustellung im Fenster vollständig: jedem abgeschlossenen "
              "Lauf eines gelisteten Workflows folgte ein Alerting-Lauf.", ""]
    for h in erg["hinweise"]:
        L += [f"⚠ Hinweis: {h}", ""]
    L += ["---",
          "Gemeldet vom Alerting-Herzschlag (`cron` – absichtlich NICHT über "
          "`workflow_run`: das ist der beobachtete Kanal). Grundlage und "
          "Vorfalls-Messung: docs/INCIDENT-2026-09-18-qualitaets-gate-zeitbombe.md, "
          "Befund E. Bei Grün wird diese Meldung automatisch geschlossen."]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------- GitHub
def _api(repo: str, pfad: str, jq: str) -> list[str]:
    """Eine API-Seite(nfolge) zeilenweise. Fehler sind Befund-Klasse 2 –
    ein Herzschlag, der nicht messen kann, darf nicht grün statt blind sein."""
    r = subprocess.run(["gh", "api", pfad, "--paginate", "--jq", jq],
                       capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        raise RuntimeError(f"gh api {pfad}: {(r.stderr or '').strip()[:200]}")
    return [z for z in (r.stdout or "").splitlines() if z.strip()]


def lade(repo: str, jetzt: dt.datetime) -> dict:
    """Läuft im Fenster abrufen (gelistete, abgeschlossene) + Alerting-Läufe.

    Die API filtert `created` taggenau; die minutengenaue Fenster-Zuordnung
    macht `abgleich` anhand eigener Zeitstempel. Geladen wird großzügig
    zurück bis zum Fensteranfang UND vorwärts bis jetzt (ein Alerting-Lauf
    kann nach dem Abschluss liegen).
    """
    von, _ = fenster(jetzt)
    tag_von = (von - dt.timedelta(days=1)).date().isoformat()
    tag_bis = (jetzt.date() + dt.timedelta(days=1)).isoformat()
    felder = ('[.workflow_runs[] | [.name, .event, (.conclusion // "-"), '
              '(.id | tostring), .html_url, .created_at, .updated_at] | @tsv] | .[]')
    zeilen = _api(repo,
                  f"repos/{repo}/actions/runs?created={tag_von}..{tag_bis}&per_page=100",
                  felder)
    laeufe, alarme = [], []
    for z in zeilen:
        t = z.split("\t")
        if len(t) < 7:
            continue
        name, event, conclusion, rid, url, created, updated = t[:7]
        if name == ALERTING_NAME and event == "workflow_run":
            try:
                alarme.append(parse_ts(created))
            except ValueError:
                continue
            continue
        try:
            abgeschlossen = parse_ts(updated)
        except ValueError:
            continue
        laeufe.append({"name": name, "conclusion": conclusion, "id": rid,
                       "url": url, "created_at": parse_ts(created),
                       "completed_at": abgeschlossen})
    return {"laeufe": laeufe, "alarme": alarme}


def pruefen(repo: str, jetzt: dt.datetime | None = None,
            gelistet: list | None = None) -> dict:
    jetzt = jetzt or dt.datetime.now(dt.timezone.utc)
    if gelistet is None:
        with open(os.path.join(BLOG_DIR, *ALERTING_DATEI.split("/")), encoding="utf-8") as fh:
            gelistet = gelistete_workflows(fh.read())
    if not gelistet:
        raise RuntimeError(f"Keine beobachteten Workflows in {ALERTING_DATEI} gefunden – "
                           "die Zählung wäre blind (das darf nie still passieren).")
    daten = lade(repo, jetzt)
    gelistet_menge = set(gelistet)
    zaehllaeufe = [l for l in daten["laeufe"] if l["name"] in gelistet_menge]
    erg = abgleich(zaehllaeufe, daten["alarme"], jetzt)
    erg["gelistet"] = len(gelistet)
    erg["repo"] = repo
    # Ausführungsdetails: welche Workflows fehlen wo
    for l in erg["fehlend_laeufe"]:
        l["workflow"] = l["name"]
    return erg


# ---------------------------------------------------------------------- Selbsttest
def _mk(name: str, conclusion: str, fertig: dt.datetime, rid: str = "1") -> dict:
    return {"name": name, "conclusion": conclusion, "id": rid,
            "url": f"https://example.invalid/runs/{rid}",
            "created_at": fertig - dt.timedelta(minutes=3),
            "completed_at": fertig}


def _selftest() -> int:
    fehler: list[str] = []
    J = dt.datetime(2026, 9, 18, 12, 0, tzinfo=dt.timezone.utc)
    von, bis = fenster(J)
    if iso(bis) != "2026-09-18T10:30:00Z" or iso(von) != "2026-09-17T10:00:00Z":
        fehler.append(f"Fenster falsch: {iso(von)}..{iso(bis)}")

    # --- Zähl-Logik -------------------------------------------------------
    basis = [parse_ts("2026-09-18T05:00:00+00:00")]
    ok = abgleich([_mk("A", "success", parse_ts("2026-09-18T04:58:00+00:00"))],
                  basis, J)
    if ok["befunde"] or ok["fehlend"] != 0:
        fehler.append("gedeckter Lauf wird als verloren gemeldet")
    ein = abgleich([_mk("A", "success", parse_ts("2026-09-18T04:58:00+00:00"))], [], J)
    if ein["fehlend"] != 1 or ein["befunde"] or len(ein["hinweise"]) != 1:
        fehler.append("Einzelverlust muss Hinweis bleiben, kein Befund")
    zwei = abgleich([_mk("A", "success", parse_ts("2026-09-18T04:58:00+00:00"), "1"),
                     _mk("B", "cancelled", parse_ts("2026-09-18T06:00:00+00:00"), "2")],
                    [], J)
    if not any("2 von 2" in b for b in zwei["befunde"]):
        fehler.append("zwei verlorene Ereignisse müssen ein Befund sein")
    rot = abgleich([_mk("Gate", "failure", parse_ts("2026-09-18T04:58:00+00:00"))], [], J)
    if not rot["befunde"] or not any("rote Läufe" in b for b in rot["befunde"]):
        fehler.append("ein ungedeckter ROTER Lauf muss SOFORT ein Befund sein")
    rot_ok = abgleich([_mk("Gate", "failure", parse_ts("2026-09-18T04:58:00+00:00"))],
                      basis, J)
    if rot_ok["befunde"]:
        fehler.append("gedeckter roter Lauf darf kein Befund sein")
    to = abgleich([_mk("X", "timed_out", parse_ts("2026-09-18T04:58:00+00:00"))], [], J)
    if not to["befunde"]:
        fehler.append("timed_out muss wie failure zählen (Timeout-Abbrüche sind rot)")
    skip = abgleich([_mk("A", "skipped", parse_ts("2026-09-18T04:58:00+00:00")),
                     _mk("A", None, parse_ts("2026-09-18T04:58:00+00:00"))], [], J)
    if skip["gesamt"] != 0 or skip["uebersprungen"]["skipped"] != 2:
        fehler.append("skipped/ohne Conclusion dürfen nicht in die Zählung")
    gnade = abgleich([_mk("A", "success", parse_ts("2026-09-18T11:30:00+00:00"))], [], J)
    if gnade["gesamt"] != 0 or gnade["uebersprungen"]["gnade"] != 1:
        fehler.append("Gnadenfrist: frisch beendete Läufe zählen noch nicht")
    alt = abgleich([_mk("A", "success", parse_ts("2026-09-16T09:59:00+00:00"))], [], J)
    if alt["gesamt"] != 0:
        fehler.append("Läufe außerhalb des Fensters zählen nicht")
    # Zuordnungs-Grenzen: +89 min OK, +91 min verloren, −6 min zu früh
    fertig = parse_ts("2026-09-18T04:00:00+00:00")
    for delta_min, soll in ((89, 0), (91, 1), (-6, 1), (-4, 0)):
        e = abgleich([_mk("A", "success", fertig)],
                     [fertig + dt.timedelta(minutes=delta_min)], J)
        if e["fehlend"] != soll:
            fehler.append(f"Zuordnungsfenster falsch bei {delta_min} min: "
                          f"fehlend={e['fehlend']}, erwartet {soll}")

    # --- Listen-Lesen (SSOT) ----------------------------------------------
    probe = ('name: Fehler-Alerting\non:\n  workflow_run:\n    workflows:\n'
             '      - "Deploy auf GitHub Pages"\n      - Qualitäts-Gate (X)\n'
             '      - "Deploy auf GitHub Pages"   # doppelt muss dedupliziert werden\n'
             '    types:\n      - completed\njobs: {}\n')
    y = gelistete_workflows(probe, use_yaml=True)
    r = gelistete_workflows(probe, use_yaml=False)
    for tag, lst in (("yaml", y), ("regex", r)):
        if lst != ["Deploy auf GitHub Pages", "Qualitäts-Gate (X)"]:
            fehler.append(f"{tag}-Parser liest die Wacht-Liste falsch: {lst}")
    # Die YAML-1.1-Falle: safe_load macht aus `on:` den Schlüssel True.
    try:
        import yaml
        if "on" in (yaml.safe_load(probe) or {}):
            fehler.append("Test-Umgebung parst `on:` unerwartet als Text – Prüfung anpassen")
    except Exception:   # noqa: BLE001
        pass
    leer = "name: x\non: push\njobs: {}\n"
    if gelistete_workflows(leer) != []:
        fehler.append("Workflow ohne workflow_run muss eine leere Wacht-Liste geben")

    # --- Zeitstempel -------------------------------------------------------
    if parse_ts("2026-09-18T05:56:34Z") != parse_ts("2026-09-18T07:56:34+02:00"):
        fehler.append("parse_ts muss Zonen vereinheitlichen")
    if iso(parse_ts("2026-09-18T05:56:34+00:00")) != "2026-09-18T05:56:34Z":
        fehler.append("iso() muss kanonisches Z liefern")

    # --- Markdown -----------------------------------------------------------
    md = als_md(rot)
    for nadel in (ISSUE_TITEL, "**1** (100.0 %)", "🔴 Rote Läufe",
                  "cron", "Befund E"):
        if nadel not in md:
            fehler.append(f"Markdown verschluckt {nadel!r}")
    md_gruen = als_md(ok)
    if "✅" not in md_gruen or "Befunde" in md_gruen:
        fehler.append("Markdown meldet den grünen Fall nicht sauber")

    # --- Am echten Bestand (falls erreichbar – kein Netz nötig) -------------
    pfad = os.path.join(BLOG_DIR, *ALERTING_DATEI.split("/"))
    if os.path.isfile(pfad):
        with open(pfad, encoding="utf-8") as fh:
            echt = gelistete_workflows(fh.read())
        if len(echt) < 25:
            fehler.append(f"echte Wacht-Liste kleinlaut: {len(echt)} Einträge")
        if ALERTING_NAME in echt:
            fehler.append("das Alerting darf sich nicht selbst beobachten – "
                          "ein Kanal, der sich melden soll, wenn er selbst "
                          "verliert, meldet dann gerade nicht")
        if "Qualitäts-Gate (Build + interne Links)" not in echt:
            fehler.append("das Qualitäts-Gate fehlt in der Wacht-Liste – "
                          "genau sein Blindflug löste den Vorfall aus")

    # --- Kanal-Probe: kann der Meldeweg selbst laufen? ----------------------
    # WF-829B / #922 (30.10.2026): Ein doppeltes `const` im github-script-Block
    # von alert-on-failure.yml tötete JEDEN Alerting-Lauf. Der „Skript-Syntax"-
    # Lauf sah es und wurde rot – gemeldet hat es niemand, weil der Melder
    # derselbe tote Kanal war. Diese Probe ist der Weg, der es trotzdem meldet.
    original = workflow_js_wache.pruefen

    def js(status, befunde):
        return lambda *a, **k: (status, list(befunde), "")

    try:
        # K1 · Ein kaputter Block im Fehler-Alerting ist ein Befund.
        workflow_js_wache.pruefen = js(1, ["J1 .github/workflows/alert-on-failure.yml:218: "
                                           "github-script-Block kompiliert nicht"])
        erg = kanal_pruefen()
        if erg["status"] != 1 or not erg["befunde"] or erg["kanal"]:
            fehler.append("K1 kaputter Meldeweg nicht erkannt")

        # K2 · Ein Befund in einer ANDEREN Datei ist kein Kanal-Befund.
        workflow_js_wache.pruefen = js(1, ["J1 .github/workflows/andere.yml:12: …"])
        if kanal_pruefen()["status"] != 0:
            fehler.append("K2 fremder Befund als Kanal-Befund gezählt")

        # K3 · Fehlt `node`, ist die Probe rot (keine Messung ist kein Grün, C33).
        workflow_js_wache.pruefen = js(2, ["J0 Prüfung nicht möglich: `node` fehlt"])
        if kanal_pruefen()["status"] != 2:
            fehler.append("K3 fehlendes node nicht als nicht prüfbar gemeldet")

        # K4 · Grün heißt grün.
        workflow_js_wache.pruefen = js(0, [])
        erg = kanal_pruefen()
        if erg["status"] != 0 or not erg["kanal"]:
            fehler.append("K4 lauffähiger Kanal nicht als grün erkannt")

        # K5 · Der Befundbericht nennt den Weg zur Heilung, nicht nur das Leid.
        if "workflow_js_wache.py --check" not in kanal_md(kanal_pruefen(pruefen=js(1, [
                "J1 .github/workflows/alert-on-failure.yml:218: x"]))):
            fehler.append("K5 Befundbericht ohne Heilungsschritt")

        # K6 · Die Meldung über einen toten Kanal trägt ihren eigenen Titel.
        if ISSUE_TITEL_KANAL == ISSUE_TITEL or "Kanal" not in ISSUE_TITEL_KANAL:
            fehler.append("K6 keine eigene Meldungsidentität für den Kanal-Befund")
    finally:
        workflow_js_wache.pruefen = original

    if fehler:
        print("🛑 alerting_heartbeat-Selbsttest FEHLGESCHLAGEN:")
        for f in fehler:
            print("  -", f)
        return 2
    print("✅ Herzschlag-Selbsttest grün: Fenster+Gnadenfrist, Zählung, "
          "Zuordnungsgrenzen (±90/5 min), Rot-sofort-Befund, skipped-Ausschluss, "
          "YAML-1.1-Falle (`on:`→True) + Regex-Fallback, echter Bestand.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Zählt die workflow_run-Zustellung "
                                             "des Fehler-Alertings nach")
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY",
                                                     "frank-hartung/franksfinanzcheck-blog"))
    ap.add_argument("--md", action="store_true")
    ap.add_argument("--kanal", action="store_true",
                    help="prüft nur, ob der Meldeweg selbst lauffähig ist")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    if args.kanal:
        erg = kanal_pruefen()
        text = kanal_md(erg)
        if args.md:
            summary = os.environ.get("GITHUB_STEP_SUMMARY")
            if summary:
                try:
                    with open(summary, "a", encoding="utf-8") as fh:
                        fh.write(text)
                except OSError:
                    pass
        print(text)
        for b in erg["befunde"]:
            if os.environ.get("GITHUB_ACTIONS"):
                print(f"::error::{b.replace('%', '%25').replace(chr(10), '%0A')}")
        return erg["status"]
    if not os.environ.get("GH_TOKEN") and not os.environ.get("GITHUB_TOKEN"):
        print("🛑 Kein GH_TOKEN/GITHUB_TOKEN – der Herzschlag kann nicht messen.")
        return 2
    env = dict(os.environ)
    env.setdefault("GH_TOKEN", env.get("GITHUB_TOKEN", ""))
    try:
        os.environ["GH_TOKEN"] = env["GH_TOKEN"]
        erg = pruefen(args.repo)
    except Exception as exc:  # noqa: BLE001 – Messwerzeug kaputt = Klasse 2
        print(f"🛑 Herzschlag-Messung unmöglich: {exc.__class__.__name__}: {exc}")
        return 2
    if args.md:
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            try:
                with open(summary, "a", encoding="utf-8") as fh:
                    fh.write(als_md(erg))
            except OSError:
                pass
    print(als_md(erg) if args.md else
          f"ALERTING-HERZSCHLAG · {erg['gesamt']} Läufe im Fenster · "
          f"{erg['alarme']} Alerting-Läufe · {erg['fehlend']} verloren · "
          f"{len(erg['rot_offen'])} davon rot")
    github = bool(os.environ.get("GITHUB_ACTIONS"))
    for b in erg["befunde"]:
        print(f"  ❌ {b}")
        if github:
            print(f"::error::{b.replace('%', '%25').replace(chr(10), '%0A')}")
    for h in erg["hinweise"]:
        print(f"  ⚠ {h}")
        if github:
            print(f"::warning::{h.replace('%', '%25').replace(chr(10), '%0A')}")
    return 1 if erg["befunde"] else 0


if __name__ == "__main__":
    sys.exit(main())
