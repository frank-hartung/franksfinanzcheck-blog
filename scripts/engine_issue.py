#!/usr/bin/env python3
"""engine_issue.py – Tagesdefizit der Content-Engine als GitHub-Issue.

Aufruf: python3 scripts/engine_issue.py --deficit
        python3 scripts/engine_issue.py --lage        (Trockenlauf: nur messen)
        python3 scripts/engine_issue.py --selftest

Öffnet (oder aktualisiert) das Fach-Issue `engine-deficit`, wenn ein
Publikationstag unter dem Mindestziel liegt, und schließt es, sobald das
Ziel nachweislich erreicht ist. Benötigt GH_TOKEN (github.token im Workflow);
ohne Token: Exit 0 + Hinweis.

=========================================================================
 ZUSTANDSKANAL-VERTRAG (WF-1F8C #608, 07.10.2026)
=========================================================================
Der Vorfall:
  Der 05.10.2026 endete mit 1/2 LIVE. Um 19:23 legte diese Wache dafür
  das Fach-Issue #601 an – korrekt. Um 21:21 wurde #601 durch den
  zusammengeführten Reparatur-Vorschlag #603 geschlossen („Closes #601“),
  obwohl der gemessene Tag rot blieb. Am 06.10. (Ruhetag) übersprang diese
  Wache den Tag vollständig („Kein Publikationstag“), also gab es keinen
  frischen Fachkanal. Die Kadenz-Endkontrolle lief um 00:55 UTC als
  verspäteter Montags-Slot, meldete ehrlich rot („TAGESDEFIZIT –
  Fachmeldung engine-deficit ist zuständig“) – und das zentrale
  Fehler-Alerting fand keinen offenen, frischen Fachkanal. Es musste
  fail-open melden und legte das generische Wartungs-Issue #608 mit
  API-Key-/GitHub-Ausfall-Runbook an: eine doppelte Meldung mit falscher
  Handlungsanweisung.

Die Ursache ist keine Alarmregel, sondern eine Besitzfrage: Die Quote ist
ein ZUSTAND, kein Arbeitsauftrag. Ein Arbeitsauftrag ist mit einem Merge
erledigt; ein Zustand nur durch eine neue Messung.

Deshalb gilt ab hier:
  * BESITZER des Kanals ist die Messung selbst (dieses Werkzeug) – nicht
    der Änderungsvorschlag, der die Ursache heilt, und nicht die Hand.
  * KADENZ ist JEDER Tag. Gemessen wird immer der jüngste Publikationstag
    (`cadence_guard.letzter_publikationstag`) – an Ruhetagen wie an
    Publikationstagen. Ein Ruhetag ist kein Grund, einen offenen Zustand
    zu vergessen.
  * SCHLIESSFAD ist ausschließlich die eigene Messung, in zwei ehrlichen
    Fällen:
      1. Der gemessene Tag hat das Ziel noch erreicht (`erfuellt`) – etwa
         durch einen späteren Slot desselben Tages.
      2. Der gemessene Tag liegt hinter uns, ist also nicht mehr
         nachholbar (Nachtragen ist verboten – „never backdate content“),
         und ein FOLGENDER Publikationstag erreicht das Ziel nachweislich.
         Dann wird das Defizit als verbucht geschlossen – mit dem
         ausdrücklichen Vermerk, dass der verlorene Tag nicht nachgeholt
         wurde. Repariert wird die Ursache, nicht die Statistik.
  * REOPEN: Wurde der Kanal geschlossen, während der gemessene Tag rot
    war (Merge, Hand, Missverständnis), öffnet die Messung ihn beim
    nächsten Lauf wieder – mit Begründung. Ein Zustand verschwindet nicht
    dadurch, dass jemand ein Issue schließt. Der Kanal schließt sich
    danach von selbst, sobald ein Publikationstag das Ziel messbar
    erreicht; es entsteht kein Dauerläufer.

Nur so kann das zentrale Fehler-Alerting die ehrlich rote Kadenz-Endkontrolle
stumm schalten, ohne eine echte Störung zu verschlucken (#602-Regel): Es
prüft den offenen, für diesen Lauf frisch aktualisierten Fachkanal.
Wer diesen Kanal an einem Tag nicht belegt, erzeugt am nächsten roten Lauf
wieder ein generisches Wartungs-Issue – genau die Klasse #608.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import cadence_guard as cg  # noqa: E402

MARKER = "<!-- engine-deficit-id: tagesdefizit -->"
LABEL = "engine-deficit"

# Zustände der Tagesquote (SSOT für Melder, Tests und Dokumentation).
ZUSTAND_ERFUELLT = "erfuellt"     # Ziel erreicht – Kanal darf zu
ZUSTAND_OFFEN = "offen"           # Publikationstag läuft, Ziel noch nicht erreicht
ZUSTAND_VERBUCHT = "verbucht"     # Tag vorbei, nicht nachholbar (kein Backdating)

TAG_MARKER = "<!-- engine-deficit-tag: {tag} -->"
REOPEN_MARKER = "<!-- engine-deficit-reopen: {tag} -->"
_TAG_IM_BODY = re.compile(r"<!--\s*engine-deficit-tag:\s*(\d{4}-\d{2}-\d{2})\s*-->")
_TAG_ALTBESTAND = re.compile(r"(?m)^-\s*\*\*Tag:\*\*\s*(\d{4}-\d{2}-\d{2})\s*$")


# =====================================================================
#  Messung (reine Funktionen – ohne Netz, ohne Uhr, deshalb prüfbar)
# =====================================================================
def quoten_lage(heute, posts, minimum) -> dict:
    """Zustand der Tagesquote – der einzige Maßstab dieses Werkzeugs.

    Gemessen wird immer der jüngste Publikationstag ≤ heute
    (`cadence_guard.letzter_publikationstag`), nie „irgendein Tag“:
      * Publikationstag, Ziel erreicht        → `erfuellt`
      * Publikationstag, Ziel offen           → `offen`    (Slots laufen noch)
      * Ruhetag, jüngster Publikationstag rot → `verbucht` (nicht nachholbar)
      * Ruhetag, jüngster Publikationstag ok  → `erfuellt`
    """
    publikationstag_heute = cg.is_publication_day(heute)
    tag = cg.letzter_publikationstag(heute)
    n = len(cg.published_on(posts, tag))
    if n >= minimum:
        zustand = ZUSTAND_ERFUELLT
    elif publikationstag_heute:
        zustand = ZUSTAND_OFFEN
    else:
        zustand = ZUSTAND_VERBUCHT
    return {
        "heute": heute,
        "tag": tag,
        "n": n,
        "ziel": minimum,
        "zustand": zustand,
        "publikationstag_heute": publikationstag_heute,
    }


def urteil(lage: dict, offen: dict | None, geschlossen: dict | None) -> dict:
    """Was ist zu tun? (reine Entscheidung, damit sie beweisbar ist)

    `offen`/`geschlossen` sind `{"nummer": int, "tag": date|None}` des
    offenen bzw. zuletzt geschlossenen Fachkanals.
    """
    if lage["zustand"] == ZUSTAND_ERFUELLT:
        if offen:
            erreicht_am_gemessenen_tag = offen.get("tag") in (None, lage["tag"])
            return {
                "aktion": "schliessen",
                "nummer": offen["nummer"],
                "grund": ("Ziel am gemessenen Tag noch erreicht"
                          if erreicht_am_gemessenen_tag
                          else "Ziel nachweislich wieder erreicht – Defizit "
                               "wird als verbucht geschlossen"),
                "wieder_erreicht": not erreicht_am_gemessenen_tag,
            }
        return {"aktion": "nichts", "grund": f"Ziel erfüllt "
                                             f"({lage['n']}/{lage['ziel']} am "
                                             f"{lage['tag']})"}
    if offen:
        return {"aktion": "kommentieren", "nummer": offen["nummer"],
                "grund": "Kanal ist offen – Zustand wird täglich belegt"}
    if geschlossen and geschlossen.get("tag") == lage["tag"]:
        return {"aktion": "wieder_oeffnen", "nummer": geschlossen["nummer"],
                "grund": "Kanal wurde geschlossen, obwohl der gemessene Tag "
                         "rot ist – ein Zustand endet nicht durch Schließen"}
    return {"aktion": "oeffnen",
            "grund": f"Kein Fachkanal vorhanden – {lage['tag']} liegt bei "
                     f"{lage['n']}/{lage['ziel']}"}


def titel(lage: dict) -> str:
    """Titel des Fachkanals (markenneutral, Status im Klartext)."""
    basis = (f"Content-Engine: Tagesdefizit {lage['tag'].isoformat()} "
             f"({lage['n']}/{lage['ziel']} LIVE)")
    if lage["zustand"] == ZUSTAND_VERBUCHT:
        return basis + " – nicht nachholbar"
    return basis


def zustandszeile(lage: dict) -> str:
    """Eine Zeile, die den Zustand vollständig beschreibt (Kommentare)."""
    wort = {
        ZUSTAND_ERFUELLT: "Ziel erreicht",
        ZUSTAND_OFFEN: "Ziel noch offen (Slots laufen)",
        ZUSTAND_VERBUCHT: "Defizit verbucht, nicht nachholbar",
    }[lage["zustand"]]
    zurueck = ", ".join(f"{t.isoformat()}: {n}/{lage['ziel']}"
                        for t, n in rueckstand_zeilen(lage))
    zeile = (f"**{lage['heute'].isoformat()}** – gemessener Publikationstag "
             f"**{lage['tag'].isoformat()}**: {lage['n']}/{lage['ziel']} LIVE "
             f"→ {wort}.")
    if zurueck:
        zeile += f"\nRückstand (letzte Publikationstage): {zurueck}."
    return zeile


def rueckstand_zeilen(lage: dict, anzahl: int = 3) -> list[tuple]:
    """Letzte `anzahl` Publikationstage (≤ gemessener Tag) mit LIVE-Zahlen.

    Damit verschwindet ein verbuchter Tag nicht aus dem Alarm, nur weil ein
    neuerer Tag gemessen wird (Lehre aus #601: der 05.10. fiel aus jedem
    Report, während der Alarm über ihn sprach).
    """
    tage = cg.publikationstage_zurueck(lage["tag"], anzahl)
    posts = lage.get("_posts") or []
    return [(t, len(cg.published_on(posts, t))) for t in tage]


def _als_md_zeile(tag, n, ziel, gemessener_tag) -> str:
    marke = " ← gemessen" if tag == gemessener_tag else ""
    urteil = "✅" if n >= ziel else "❌"
    return f"| {urteil} {tag.isoformat()} | {n}/{ziel} |{marke} |"


# =====================================================================
#  Texte (ebenfalls rein – der Wortlaut ist Teil des Vertrags)
# =====================================================================
def koerper(lage: dict, *, oeffnend: bool = False,
            vorgaenger: int | None = None) -> str:
    """Der Issue-Body: Zustand, Rückstand, Ursachen-Diagnose, Runbook."""
    zeilen = [
        MARKER,
        TAG_MARKER.format(tag=lage["tag"].isoformat()),
        "",
        "## Content-Engine: LIVE unter Mindestziel",
        "",
        f"- **Tag:** {lage['tag'].isoformat()} "
        f"({cg.DAYS_DE[lage['tag'].weekday()]})",
        f"- **LIVE:** {lage['n']} (Ziel ≥ {lage['ziel']})",
        f"- **Gemessen am:** {lage['heute'].isoformat()} "
        f"({cg.DAYS_DE[lage['heute'].weekday()]})",
        f"- **Zustand:** `{lage['zustand']}`",
        "",
    ]
    if lage["zustand"] == ZUSTAND_VERBUCHT:
        zeilen += [
            "> Der Publikationstag liegt hinter uns und wird **nicht "
            "nachgeholt** (Nachtragen von Inhalten ist verboten). Dieser "
            "Kanal bleibt offen, bis ein folgender Publikationstag das Ziel "
            "nachweislich erreicht – ein Zustand endet durch Messung, nicht "
            "durch Schließen.",
            "",
        ]
    if oeffnend and vorgaenger is not None:
        zeilen += [
            f"> Vorgänger: #{vorgaenger}. Der Kanal war zum Zeitpunkt des "
            f"Schließens rot; die Messung hat ihn deshalb wieder geöffnet.",
            "",
        ]
    zeilen += [
        "| Publikationstag | LIVE | |",
        "|---|---:|---|",
    ]
    for tag, n in rueckstand_zeilen(lage):
        zeilen.append(_als_md_zeile(tag, n, lage["ziel"], lage["tag"]))
    zeilen.append("")
    zeilen.append(_diagnose())
    zeilen.append(
        "\n### Erste Schritte\n\n"
        "```bash\n"
        "python3 scripts/engine_issue.py --lage            # Zustand in einem Blick\n"
        "python3 scripts/engine_capacity.py               # Lage der Themen\n"
        "python3 scripts/slot_wache.py --pruefen --ohne-dispatch  # Slot-Lage\n"
        "python3 scripts/reserve_topics.py --abgleich     # Phantom-Sperren lösen\n"
        "```\n\n"
        "Hintergrund: `CONTENT-ENGINE-KAPAZITAET-PREMIUM-2026-10-02.md` · "
        "`TAGESDEFIZIT-ENGINE-601-DAUERHEILUNG-PREMIUM-2026-10-05.md` · "
        "`WF-1F8C-608-DAUERHEILUNG-PREMIUM-2026-10-07.md` (Zustandskanal)\n")
    return "".join(zeilen)


def kommentar(lage: dict) -> str:
    """Kurzer Zustandsbeleg (jeder Lauf braucht ihn – er ist der Frischebeweis
    für das zentrale Fehler-Alerting)."""
    return (f"<!-- engine-deficit-update: {lage['heute'].isoformat()} -->\n"
            f"{zustandszeile(lage)}\n\n"
            f"Zustand: `{lage['zustand']}` · "
            f"gemessen gegen `cadence_guard` (Mo/Mi/Fr, Ziel "
            f"{lage['ziel']}–{_maximum()}).")


def schluss_kommentar(lage: dict) -> str:
    """Der Schließvermerk der Messung – ohne Statistik-Kosmetik."""
    ziel = lage["ziel"]
    if lage["zustand"] == ZUSTAND_ERFUELLT and lage.get("_offen_tag") == lage["tag"]:
        return (f"✅ **{lage['tag'].isoformat()}: Ziel erreicht** – "
                f"{lage['n']}/{ziel} LIVE am gemessenen Tag. "
                f"Der Kanal schließt sich durch seine eigene Messung.")
    rueck = ", ".join(f"{t.isoformat()}: {n}/{ziel}"
                      for t, n in rueckstand_zeilen(lage)) or "–"
    return (f"✅ **Ziel wieder erreicht** – der Publikationstag "
            f"{lage['tag'].isoformat()} liegt bei {lage['n']}/{ziel} LIVE. "
            f"Der zuvor verbuchte Fehltag bleibt verbucht: Er wurde **nicht** "
            f"nachgeholt (kein Nachtragen von Inhalten), sondern die Kadenz "
            f"läuft nachweislich wieder im Ziel. "
            f"Rückstand: {rueck}.")


def reopen_kommentar(lage: dict, geschlossen_am: str = "") -> str:
    """Begründung, warum ein geschlossener Zustandskanal wieder offen ist."""
    am = f" (geschlossen am {geschlossen_am})" if geschlossen_am else ""
    return (
        f"{REOPEN_MARKER.format(tag=lage['tag'].isoformat())}\n"
        f"🔁 **Wieder offen{am}.**\n\n"
        f"{zustandszeile(lage)}\n\n"
        f"Die Meldung war geschlossen, **bevor** der gemessene Tag das Ziel "
        f"erreicht hatte. Der Zustand ist damit nicht erledigt: Ein "
        f"Änderungsvorschlag kann eine Ursache beheben, aber keinen "
        f"Messwert. Dieser Kanal wird von seiner eigenen Messung geführt "
        f"(Besitzer, tägliche Kadenz, Schließpfad – siehe Modulkopf von "
        f"`scripts/engine_issue.py`) und schließt sich, sobald ein "
        f"Publikationstag das Ziel wieder erreicht.")


def _maximum() -> int:
    _minimum, maximum = cg.effective_limits()
    return maximum


def _diagnose() -> str:
    """Warum war zu wenig LIVE? – Ursachen statt Symptom.

    ISSUE #521 (02.10.2026): Das alte Defizit-Issue meldete „0/2 LIVE“ und
    verwies auf das Runbook. Es stand damit genau so ratlos da wie der
    Leser: Dass vier Themen produziert, aber von Gates gestoppt wurden,
    dass 47 Themen durch Phantom-Erfolge gesperrt waren und dass der
    Prüfstapel der Fachfreigabe mit 11 Artikeln dicht war, musste man sich
    aus drei Reports zusammensuchen. Ein Alarm ohne Diagnose erzeugt
    Arbeit statt sie zu ersparen – deshalb trägt das Issue die Lage jetzt
    bei sich.

    Fail-open: Eine kaputte Diagnose darf den Alarm nie verschlucken.
    """
    zeilen = []
    try:
        sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
        import engine_capacity as ec
        lage = ec.lage()
        symbol = {"ok": "✅", "knapp": "⚠️", "erschoepft": "🛑"}[lage["verdikt"]]
        zeilen.append("### Lage der Engine\n\n")
        zeilen.append(f"{symbol} {lage['befund']}\n\n")
        zeilen.append(
            f"| Bahn | Themen | frei disponierbar |\n"
            f"|---|---:|---:|\n"
            f"| AUTO (darf live gehen) | {lage['themen_auto']} "
            f"| **{lage['frei_auto']}** |\n"
            f"| FACHFREIGABE (YMYL, braucht Mensch) "
            f"| {lage['themen_fachfreigabe']} "
            f"| {lage['frei_fachfreigabe']} |\n")
        fach = lage["fachfreigabe"]
        if not fach["geoeffnet"]:
            zeilen.append(
                f"\n**Fachfreigabe-Bahn ist geschlossen:** {fach['grund']}. "
                f"Hochrisiko-Themen können heute also nicht ausweichen – "
                f"sie warten, statt einen LIVE-Slot zu verbrennen.\n")
        for w in lage["warnungen"]:
            zeilen.append(f"\n- ⚠️ {w}")
        if lage["naechste_auto"]:
            zeilen.append(
                f"\n\n**Nächste freie AUTO-Themen:** "
                f"{' · '.join(lage['naechste_auto'][:3])}\n")
    except Exception as e:  # noqa: BLE001 – Alarm geht IMMER raus
        zeilen.append(f"\n_(Kapazitäts-Diagnose nicht verfügbar: {e})_\n")

    # Slot-Protokoll des Tages (ISSUE #601, 05.10.2026): Die Kapazitäts-
    # Diagnose meldete an diesem Montag „29 frei disponierbare AUTO-Themen –
    # Tagesziel gedeckt“, und trotzdem blieb der Tag bei 1/2 LIVE. Die
    # Ursache stand in keinem der drei Reports, die das Issue empfahl:
    # GitHubs Scheduler hatte 4 von 7 planmäßigen Slots der Content-Linie
    # nie gestartet. Ein Defizit-Issue, das die Lauf-Realität des Tages
    # verschweigt, nennt Zahlen, aber nicht die Ursache – deshalb hängt
    # die Slot-Wache ihr Protokoll jetzt direkt an den Alarm (fail-open).
    try:
        import slot_wache as sw
        zeilen.append(sw.diagnose_zeilen(
            repo=os.environ.get("GITHUB_REPOSITORY", "")))
    except Exception as e:  # noqa: BLE001 – Alarm geht IMMER raus
        zeilen.append(f"\n_(Slot-Protokoll nicht verfügbar: {e})_\n")

    # Entwürfe, die fertig sind, aber auf einen Menschen warten.
    try:
        q = os.path.join(BLOG_DIR, "data", "editorial_review_queue.json")
        if os.path.exists(q):
            with open(q, encoding="utf-8") as fh:
                daten = json.load(fh)
            offen_live = int(daten.get("open_live") or 0)
            offen_entw = int(daten.get("open_drafts") or 0)
            if offen_live or offen_entw:
                zeilen.append(
                    f"\n### Wartet auf fachliche Freigabe\n\n"
                    f"{offen_entw} Entwürfe und {offen_live} Live-Artikel "
                    f"liegen in der YMYL-Prüfqueue. Diese Arbeit ist "
                    f"**nicht automatisierbar** – sie läuft über "
                    f"„Redaktionelle YMYL-Prüfqueue“.\\n")
    except Exception:  # noqa: BLE001
        pass
    return "".join(zeilen)


# =====================================================================
#  GitHub (dünn, austauschbar – der Selbsttest ersetzt es)
# =====================================================================
def _gh(*args: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    return subprocess.run(
        ["gh", *args],
        cwd=BLOG_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _ensure_label(gh=_gh) -> None:
    listed = gh("label", "list", "--json", "name", "--jq", ".[].name")
    if LABEL not in (listed.stdout or "").splitlines():
        gh("label", "create", LABEL, "--color", "d93f0b",
           "--description", "Content-Engine: LIVE unter Tagesmindestziel")


def tag_aus_body(body: str) -> dt.date | None:
    """Der gemessene Tag eines Kanals – Marker zuerst, Altauflage als Pfad.

    Die Altauflage („- **Tag:** 2026-10-05“) ist kein Luxus: #601 wurde von
    der Vorgängerversion ohne Marker angelegt und muss wiedererkannt werden,
    sonst entstünde beim Wiederöffnen ein zweiter Kanal.
    """
    for muster in (_TAG_IM_BODY, _TAG_ALTBESTAND):
        treffer = muster.search(body or "")
        if treffer:
            try:
                return dt.date.fromisoformat(treffer.group(1))
            except ValueError:
                continue
    return None


def _issue_liste(*args: str, gh=_gh) -> list[dict]:
    r = gh("issue", "list", *args, "--json", "number,body,title")
    if r.returncode != 0:
        raise RuntimeError(f"gh issue list: {(r.stderr or r.stdout or '').strip()[:200]}")
    try:
        return json.loads(r.stdout or "[]")
    except json.JSONDecodeError:
        return []


def _offenes_issue(gh=_gh) -> dict | None:
    for e in _issue_liste("--label", LABEL, "--state", "open",
                          "--limit", "20", gh=gh):
        if MARKER in (e.get("body") or ""):
            return {"nummer": int(e["number"]), "tag": tag_aus_body(e.get("body") or ""),
                    "titel": e.get("title") or ""}
    return None


def _letztes_geschlossenes_issue(tag=None, gh=_gh) -> dict | None:
    """Der jüngste geschlossene Kanal – bevorzugt der zum gemessenen Tag.

    Wird #601 (Tag 05.10.) rot geschlossen, während der 05.10. noch rot ist,
    soll genau DIESER Kanal wieder aufgehen (kein zweiter in der Historie).
    Gehört der geschlossene Kanal zu einem älteren Tag, ist ein NEUER Kanal
    richtig – dann bleibt das Defizit des alten Tages als eigener Vorgang
    ablesbar.
    """
    treffer = []
    for e in _issue_liste("--label", LABEL, "--state", "closed",
                          "--limit", "30", gh=gh):
        if MARKER in (e.get("body") or ""):
            treffer.append({"nummer": int(e["number"]),
                            "tag": tag_aus_body(e.get("body") or "")})
    for t in treffer:
        if tag is not None and t["tag"] == tag:
            return t
    return treffer[0] if treffer else None


# =====================================================================
#  Abgleich (die eine Zustandsmaschine, mit Netz)
# =====================================================================
def abgleichen(lage: dict, gh=_gh) -> tuple[int, str]:
    """Den Fachkanal in den zur Lage passenden Zustand bringen.

    Rückgabe (rc, Meldung): 0 = Zustand belegt (auch »nichts zu tun«),
    2 = Werkzeugfehler (der Kanal konnte NICHT belegt werden – das ist
    ein Befund, kein Betriebsgeräusch, und muss von den Aufrufern laut
    gemeldet werden).
    """
    _ensure_label(gh=gh)
    offen = _offenes_issue(gh=gh)
    geschlossen = None if offen else _letztes_geschlossenes_issue(lage["tag"], gh=gh)
    beschluss = urteil(lage, offen, geschlossen)
    aktion = beschluss["aktion"]

    if aktion == "nichts":
        return 0, f"Kein Defizit ({lage['n']}/{lage['ziel']} am {lage['tag']})."

    if aktion == "schliessen":
        nr = str(beschluss["nummer"])
        lage["_offen_tag"] = (offen or {}).get("tag")
        r = gh("issue", "close", nr, "--comment", schluss_kommentar(lage))
        if r.returncode != 0:
            return 2, f"Kanal #{nr} konnte nicht geschlossen werden: {(r.stderr or '').strip()[:200]}"
        return 0, f"Fachkanal #{nr} geschlossen ({beschluss['grund']})."

    if aktion == "kommentieren":
        nr = str(beschluss["nummer"])
        texte = [kommentar(lage)]
        if offen and offen.get("tag") and offen["tag"] != lage["tag"]:
            texte.append(f"Gemessener Publikationstag jetzt "
                         f"**{lage['tag'].isoformat()}** (vorher "
                         f"{offen['tag'].isoformat()}).")
        r = gh("issue", "comment", nr, "--body", "\n\n".join(texte))
        if r.returncode != 0:
            return 2, f"Fachkanal #{nr} konnte nicht belegt werden: {(r.stderr or '').strip()[:200]}"
        _titel_setzen(nr, lage, gh=gh)
        return 0, f"Fachkanal #{nr} belegt ({lage['n']}/{lage['ziel']})."

    if aktion == "wieder_oeffnen":
        nr = str(beschluss["nummer"])
        r = gh("issue", "reopen", nr, "--comment", reopen_kommentar(lage))
        if r.returncode != 0:
            return 2, f"Fachkanal #{nr} konnte nicht wieder geöffnet werden: {(r.stderr or '').strip()[:200]}"
        _titel_setzen(nr, lage, gh=gh)
        return 0, f"Fachkanal #{nr} wieder geöffnet (Zustand war rot)."

    # öffnen
    zeilen = [koerper(lage, oeffnend=True,
                      vorgaenger=(geschlossen or {}).get("nummer"))]
    r = gh("issue", "create", "--title", titel(lage), "--label", LABEL,
           "--body", "\n".join(zeilen))
    if r.returncode != 0:
        return 2, f"Fachkanal konnte nicht angelegt werden: {(r.stderr or '').strip()[:200]}"
    return 0, f"Fachkanal angelegt: {(r.stdout or '').strip().splitlines()[0][:120]}"


def _titel_setzen(nr: str, lage: dict, gh=_gh) -> None:
    """Titel spiegelt den gemessenen Tag/Status (Identität ist der Marker)."""
    r = gh("issue", "view", nr, "--json", "title")
    if r.returncode == 0:
        try:
            if json.loads(r.stdout or "{}").get("title") == titel(lage):
                return
        except json.JSONDecodeError:
            pass
    gh("issue", "edit", nr, "--title", titel(lage))


# =====================================================================
#  Aufrufe
# =====================================================================
def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return selftest()
    if "--deficit" not in argv and "--lage" not in argv:
        print("Nutzung: python3 scripts/engine_issue.py --deficit | --lage | --selftest")
        return 0

    heute = dt.datetime.now(dt.timezone.utc).date()
    minimum = _minimum_wache()
    posts = cg.load_posts()
    lage = quoten_lage(heute, posts, minimum)
    lage["_posts"] = posts

    if "--lage" in argv:
        print(json.dumps({k: (v.isoformat() if isinstance(v, dt.date) else v)
                          for k, v in lage.items() if not k.startswith("_")},
                         ensure_ascii=False, indent=2))
        if "--deficit" not in argv:
            return 0

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Kein GH_TOKEN – Defizit nur geloggt, kein Issue.")
        print(f"{heute.isoformat()}: gemessen {lage['tag']} mit "
              f"{lage['n']}/{lage['ziel']} LIVE (Zustand {lage['zustand']}).")
        return 0

    try:
        rc, meldung = abgleichen(lage)
    except Exception as e:  # noqa: BLE001 – fail-loud, aber nie ein Crash
        print(f"::warning::Zustandskanal nicht belegbar: {e}")
        return 2
    print(meldung)
    if rc != 0:
        print(f"::warning::Zustandskanal NICHT belegt – {meldung}")
    return rc


def _minimum_wache() -> int:
    """Mindestziel wie überall: Env übersteuerbar, Floor 2 (SSOT cadence_guard)."""
    minimum, _maximum = cg.effective_limits()
    return minimum


# =====================================================================
#  Selbsttest (ohne Netz, ohne Wanduhr – der Vorfall wird nachgestellt)
# =====================================================================
def selftest() -> int:
    fehler: list[str] = []

    def posts(*tage):
        return [{"draft": False, "date": t, "slug": f"p{i}"}
                for i, t in enumerate(tage)]

    mo, di, mi, do, fr = (dt.date(2026, 10, d) for d in (5, 6, 7, 8, 9))

    def pruefe(name, ist, soll):
        if ist != soll:
            fehler.append(f"{name}: {ist!r} statt {soll!r}")

    # --- Der Vorfall vom 05./06.10.2026 -----------------------------------
    # 05.10. (Mo) 19:23: 1 LIVE, Publikationstag läuft → offen (Kanal #601)
    lage_mo_abend = quoten_lage(mo, posts(mo), 2)
    pruefe("05.10. abends", lage_mo_abend["zustand"], ZUSTAND_OFFEN)
    pruefe("05.10. abends Tag", lage_mo_abend["tag"], mo)
    # 06.10. (Di) 00:55: der verspätete Montags-Slot. Der Tag ist vorbei,
    # nachholbar ist er nicht → verbucht – und der Kanal MUSS existieren,
    # sonst entsteht wieder #608.
    lage_di = quoten_lage(di, posts(mo), 2)
    pruefe("06.10. Zustand", lage_di["zustand"], ZUSTAND_VERBUCHT)
    pruefe("06.10. gemessener Tag", lage_di["tag"], mo)
    # 06.10. mit erfülltem Montag (2 LIVE) → erfüllt, Kanal darf schließen.
    pruefe("06.10. erfüllt", quoten_lage(di, posts(mo, mo), 2)["zustand"],
           ZUSTAND_ERFUELLT)
    # 07.10. (Mi) mit 2 LIVE am Mittwoch → erfüllt (neuer Tag, neue Messung).
    pruefe("07.10. erfüllt", quoten_lage(mi, posts(mi, mi), 2)["zustand"],
           ZUSTAND_ERFUELLT)
    # 07.10. mittags 0 LIVE → offen (die Slots laufen noch).
    pruefe("07.10. mittags", quoten_lage(mi, [], 2)["zustand"], ZUSTAND_OFFEN)
    # Ruhetag Do mit erfülltem Mittwoch → erfüllt; mit rotem Mittwoch → verbucht.
    pruefe("08.10. nach grünem Mi", quoten_lage(do, posts(mi, mi), 2)["zustand"],
           ZUSTAND_ERFUELLT)
    pruefe("08.10. nach rotem Mi", quoten_lage(do, posts(mi), 2)["zustand"],
           ZUSTAND_VERBUCHT)

    # --- Die Entscheidungen ------------------------------------------------
    ohne = None
    offen601 = {"nummer": 601, "tag": mo}
    pruefe("Urteil erfüllt, kein Kanal",
           urteil(dict(lage_mo_abend, zustand=ZUSTAND_ERFUELLT), ohne, ohne)["aktion"],
           "nichts")
    pruefe("Urteil rot mit offenem Kanal",
           urteil(lage_di, offen601, ohne)["aktion"], "kommentieren")
    pruefe("Urteil rot ohne Kanal (Neuanlage)",
           urteil(lage_di, ohne, ohne)["aktion"], "oeffnen")
    # Der Kernfall: #601 wurde am 21:21 geschlossen, während der Tag rot war.
    pruefe("Urteil rot mit geschlossenem Kanal",
           urteil(lage_di, ohne, offen601)["aktion"], "wieder_oeffnen")
    # Ein geschlossener Kanal zu einem ANDEREN Tag wird nicht wiederbelebt –
    # dann entsteht ein neuer Kanal (kein Titel-Wirrwarr in der Historie).
    pruefe("Urteil rot, geschlossener Alt-Kanal → neu",
           urteil(lage_di, ohne, {"nummer": 500, "tag": fr - dt.timedelta(days=7)})["aktion"],
           "oeffnen")
    # Erfüllt und offener Kanal → schließen (mit dem richtigen Vermerk).
    beschluss = urteil(dict(lage_di, zustand=ZUSTAND_ERFUELLT), offen601, ohne)
    pruefe("Urteil erfüllt mit offenem Kanal", beschluss["aktion"], "schliessen")
    pruefe("Schließvermerk: nicht nachgeholt",
           beschluss["wieder_erreicht"], False)
    # Ein Kanal, der einen ÄLTEREN Tag beschreibt, während ein neuerer Tag
    # das Ziel erreicht: dann wird das Defizit als verbucht geschlossen.
    alt = {"nummer": 601, "tag": dt.date(2026, 10, 2)}
    beschluss2 = urteil(dict(lage_di, zustand=ZUSTAND_ERFUELLT), alt, ohne)
    pruefe("Schließvermerk: wieder erreicht (älterer Fehltag)",
           beschluss2["wieder_erreicht"], True)

    # --- Marker, Titel, Rückstand -----------------------------------------
    kopf = koerper(dict(lage_di, _posts=posts(mo)), oeffnend=True, vorgaenger=601)
    pruefe("Body trägt den Tagesmarker", TAG_MARKER.format(tag=mo.isoformat()) in kopf,
           True)
    pruefe("Tag aus Marker lesbar", tag_aus_body(kopf), mo)
    pruefe("Tag aus Altauflage (#601) lesbar",
           tag_aus_body(f"{MARKER}\n\n## Content-Engine: LIVE unter Mindestziel\n\n"
                        f"- **Tag:** 2026-10-05\n- **LIVE heute:** 1 (Ziel ≥ 2)\n"),
           mo)
    pruefe("Tag ohne Angabe bleibt leer", tag_aus_body(MARKER), None)
    pruefe("Titel nennt Tag und Quote", titel(lage_mo_abend),
           "Content-Engine: Tagesdefizit 2026-10-05 (1/2 LIVE)")
    pruefe("Titel verbucht den Fehltag",
           titel(dict(lage_di, _posts=posts(mo))),
           "Content-Engine: Tagesdefizit 2026-10-05 (1/2 LIVE) – nicht nachholbar")
    rueck = rueckstand_zeilen(dict(lage_di, _posts=posts(mo)), 3)
    pruefe("Rückstand zeigt drei Publikationstage", [t for t, _ in rueck],
           [mo, dt.date(2026, 10, 2), dt.date(2026, 9, 30)])
    pruefe("Rückstand nennt die Quote", [n for _, n in rueck], [1, 0, 0])
    zeile = zustandszeile(dict(lage_di, _posts=posts(mo)))
    pruefe("Zustandszeile nennt Tag, Quote und Urteil",
           ("2026-10-05" in zeile and "1/2 LIVE" in zeile
            and "verbucht" in zeile), True)
    pruefe("Reopen-Vermerk nennt den Grund",
           "Wieder offen" in reopen_kommentar(dict(lage_di, _posts=posts(mo)), "21:21"),
           True)
    pruefe("Reopen-Vermerk trägt den Marker",
           REOPEN_MARKER.format(tag=mo.isoformat()) in
           reopen_kommentar(dict(lage_di, _posts=posts(mo))), True)

    # --- Der Abgleich als Ganzes (mit gestubbtem GitHub) ------------------
    #
    # Ein Kanal, der geschlossen wurde, obwohl der Tag rot war, MUSS wieder
    # offen sein – sonst legt das zentrale Fehler-Alerting beim nächsten
    # roten Lauf wieder ein generisches Wartungs-Issue an (#608).
    aufrufe: list[tuple] = []

    def gh_stub(*args):
        aufrufe.append(args)
        if args[:2] == ("label", "list"):
            return subprocess.CompletedProcess(args, 0, LABEL + "\n", "")
        if args[:2] == ("issue", "list"):
            zustand = args[args.index("--state") + 1]
            if "--label" in args and zustand == "closed":
                return subprocess.CompletedProcess(
                    args, 0, json.dumps([{
                        "number": 601, "title": "Content-Engine: Tagesdefizit 2026-10-05 (1/2 LIVE)",
                        "body": f"{MARKER}\n- **Tag:** 2026-10-05\n"}] * 1), "")
            return subprocess.CompletedProcess(args, 0, "[]", "")
        if args[0] == "issue" and args[1] in ("reopen", "comment", "close", "edit", "view"):
            return subprocess.CompletedProcess(args, 0, "{}" if args[1] == "view" else "", "")
        return subprocess.CompletedProcess(args, 0, "https://github.com/x/y/issues/700", "")

    rc, meldung = abgleichen(dict(lage_di, _posts=posts(mo)), gh=gh_stub)
    if rc != 0:
        fehler.append(f"Abgleich (reopen) endet {rc}: {meldung}")
    if not any(a[:2] == ("issue", "reopen") for a in aufrufe):
        fehler.append("Abgleich hat den rot geschlossenen Kanal NICHT wieder geöffnet")
    if not any("Wieder offen" in " ".join(a) for a in aufrufe):
        fehler.append("Reopen ohne Begründung (der Betreiber erfährt nicht, warum)")

    # Ruhetag, Kanal offen → kommentieren (Frischebeweis für das Alerting).
    aufrufe.clear()

    def gh_stub_offen(*args):
        aufrufe.append(args)
        if args[:2] == ("label", "list"):
            return subprocess.CompletedProcess(args, 0, LABEL + "\n", "")
        if args[:2] == ("issue", "list"):
            return subprocess.CompletedProcess(
                args, 0, json.dumps([{
                    "number": 601, "title": "t",
                    "body": f"{MARKER}\n- **Tag:** 2026-10-05\n"}]), "")
        if args[0] == "issue" and args[1] == "view":
            return subprocess.CompletedProcess(args, 0, '{"title": "t"}', "")
        return subprocess.CompletedProcess(args, 0, "", "")

    rc, meldung = abgleichen(dict(lage_di, _posts=posts(mo)), gh=gh_stub_offen)
    if rc != 0:
        fehler.append(f"Abgleich (kommentieren) endet {rc}: {meldung}")
    if not any(a[:2] == ("issue", "comment") for a in aufrufe):
        fehler.append("Offener Kanal wurde nicht belegt – das Alerting "
                      "würde wieder fail-open melden (#608)")

    # Erfüllter Tag → Kanal schließt sich, Vermerk nennt die Nicht-Nachholbarkeit.
    aufrufe.clear()
    lage_di_gruen = dict(quoten_lage(di, posts(mo, mo), 2), _posts=posts(mo, mo))
    lage_di_gruen["zustand"] = ZUSTAND_ERFUELLT
    lage_di_gruen["tag"] = dt.date(2026, 10, 2)   # Kanal gehört zu einem älteren Tag
    rc, meldung = abgleichen(lage_di_gruen, gh=gh_stub_offen)
    if rc != 0:
        fehler.append(f"Abgleich (schließen) endet {rc}: {meldung}")
    schluss = " ".join(" ".join(a) for a in aufrufe if a[:2] == ("issue", "close"))
    if not ("nachgeholt" in schluss and "verbucht" in schluss):
        fehler.append("Schließvermerk behauptet Fortschritt, der nicht da ist "
                      "(der Fehltag ist nicht nachholbar)")

    # Kein Defizit und kein Kanal → nichts tun (und nichts anlegen).
    aufrufe.clear()

    def gh_stub_ruhig(*args):
        aufrufe.append(args)
        if args[:2] == ("label", "list"):
            return subprocess.CompletedProcess(args, 0, LABEL + "\n", "")
        if args[:2] == ("issue", "list"):
            return subprocess.CompletedProcess(args, 0, "[]", "")
        return subprocess.CompletedProcess(args, 0, "", "")

    rc, meldung = abgleichen(dict(quoten_lage(mi, posts(mi, mi), 2),
                                  _posts=posts(mi, mi)), gh=gh_stub_ruhig)
    if rc != 0 or [a for a in aufrufe if a[0] == "issue" and a[1] in
                   ("create", "comment", "reopen", "close")]:
        fehler.append("Ruhiger Zustand erzeugt Betrieb (Alarm-Müdigkeit)")

    if fehler:
        print("🛑 ENGINE-ISSUE-SELFTEST FEHLGESCHLAGEN – der Zustandskanal ist defekt:")
        for f in fehler:
            print(f"   - {f}")
        return 2
    print("✅ ENGINE-ISSUE-SELFTEST bestanden (Vorfall 05./06.10. nachgestellt: "
          "Ruhetag gemessen, rot Geschlossenes wieder geöffnet, verbucht "
          "geschlossen, ruhiger Zustand bleibt still).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
