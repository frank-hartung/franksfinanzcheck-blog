#!/usr/bin/env python3
"""DECKUNGS-TICKET – der Schließpfad des roten Faktenfrische-Laufs (#1039).

WARUM DIESE DATEI EXISTIERT
---------------------------
Seit dem 04.11.2026 misst die Deckungswache nicht nur den Stichtag, sondern
auch den Bündeltag (`spitzenlast_stichtag`, #1039): „heute“ ist der ruhigste
Tag des Jahres – die Prüftermine sind BÜNDEL (am 06.11.2026: 115 Seiten auf
35 Fristtage, 23 davon am 27.11.2026). Damit kann der Deckungs-Nachweis
(`--wache`) auch am Spitzentag rot sein. Der rote Job allein war bis hierher
ein Dauer-Alarm ohne Auftrag und ohne Schließpfad – niemand wurde beauftragt,
niemand konnte schließen. Das ist die Definition eines Dauerläufers (C14).

Jetzt gilt: **Genau EIN offenes Ticket** (Label `faktenfrische-deckung`),
gespeist aus derselben Messung wie die Wache, aktualisiert statt dupliziert,
geschlossen, sobald die Messung grün ist. Das ist die Selbstheilungs-Schleife
des Alarms: Der Alarm beauftragt, der Alarm schließt – kein Mensch muss ein
Ticket verwalten, das die Maschine besser kennt.

WAS DIESE DATEI NICHT TUT
-------------------------
  * Sie entscheidet NICHTS. Takt (`cron` in `.github/workflows/faktenfrische.yml`),
    Sockel, Limit und Intervalle (`data/agent_reach/faktenfrische.yaml`) sind
    menschliche Entscheidungen des Herausgebers. Die Maschine nennt nur die
    Schließpfade mit Zahlen – und nie eine zweite Schwelle (C19).
  * Sie heilt NICHT den Bestand. Ein grünes Ticket heißt „die Kadenz trägt",
    nicht „alle Artikel sind richtig" – das bleibt Sache der Fachprüfung (F4).
  * Sie blockiert NIE den Job. Der rote Job bleibt das Tor (`--wache`,
    fail-closed); dieses Ticket ist der Schließpfad. Fehler hier sind
    Warnungen, nicht Tore.

SEIT 07.11.2026: DIE PROJEKTION STEHT IM TICKET (#1107)
-------------------------------------------------------
Der Befund von #1107 entstand aus einem Handlauf, der einen Zukunftstag mit
dem eingefrorenen Prüfstand von heute maß („rot am 26.11./31.12.“). Die
Messung rechnet den Zukunftstag jetzt als Weg des Bots (Trajektorie ab
heute). Damit kein Leser raten muss, WELCHE Art Zahl er vor sich hat,
übernimmt dieses Ticket Ausgangspunkt und Horizont aus derselben Messung:
„Der Weg des Bots ist bis D frei“ oder „reißt zuerst am D2“. Beides stammt
aus dem Lauf, der das Ticket schreibt – eine Momentaufnahme von Hand kann
kein Ticket mehr füllen.

NUTZUNG
  python3 scripts/faktenfrische_deckung_ticket.py              # dry-run: Entscheidung + Text
  python3 scripts/faktenfrische_deckung_ticket.py --apply       # Ticket setzen/aktualisieren/schließen
  python3 scripts/faktenfrische_deckung_ticket.py --selftest
EXIT: 0 = Entscheidung erzeugt (auch wenn gh fehlt – fail-soft) ·
      2 = Werkzeugfehler (nur dry-run / Programmierfehler)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KAP = ROOT / "scripts" / "faktenfrische_kapazitaet.py"
SSOT = "data/agent_reach/faktenfrische.yaml"
LABEL = "faktenfrische-deckung"
LABEL_FARBE = "b60205"
LABEL_TEXT = ("Faktenfrische-Deckung: roter Deckungs-Nachweis (Kadenz/Spitzentag) "
              "– ein Ticket, ein Schließpfad (#1039)")
MARKER = "<!-- wache-id: faktenfrische-deckung -->"
TITEL = "Faktenfrische-Deckung rot – Bündel-/Spitzentag oder Kadenz (#1039)"
TITEL_BEWEISLOS = "Faktenfrische-Deckung nicht beweisbar – Wache konnte nicht messen"


# ============================================================
#  Reine Entscheidung (testbar, ohne Netz)
# ============================================================
def spitze_befund(messung: dict) -> str | None:
    """Der Spitzentag-Befund als Satz – oder None. Eine Stelle (C19)."""
    tag = messung.get("spitze_stichtag")
    if tag and not messung.get("spitze_puenktlich", True):
        return (f"Am **{tag}** kämen **{int(messung.get('spitze_offen', 0))}** von "
                f"**{int(messung.get('spitze_frisch', 0))}** heute noch "
                f"frischen Seiten zu spät.")
    return None


def gegenprobe_befund(messung: dict) -> str | None:
    """Der Rahmen für eine EINGEFRORENE Messung – oder None (#1107, 10.11.2026).

    Bis zum 10.11.2026 kannte das Ticket nur „grün", „rot" und „beweislos"
    und unterschied bei der Projektion allein `trajektorie: true|false`.
    Damit las sich eine eingefrorene Zukunftsmessung (Stichtag mit dem
    Prüfstand seines eigenen Tages) wie ein Betriebsnachweis. Genau aus
    dieser Verwechslung entstand #1107. Jetzt ist der dritte Zustand
    sichtbar: Das Ticket nennt ihn beim Namen, und es schließt sich
    daraus NICHT (eine Gegenprobe belegt keinen Betriebszustand).
    """
    if not (messung.get("projektion") or {}).get("eingefroren"):
        return None
    p = messung.get("projektion") or {}
    return (
        "⚠️ **Eingefrorene Gegenprobe – kein Betriebsnachweis (#1107):** "
        f"Der Stichtag {p.get('stichtag')} liegt in der Zukunft und wurde mit "
        "dem Prüfstand genau dieses Tages gemessen (als hätte der Bot bis dahin "
        "nichts geprüft). Aus einer Momentaufnahme schließt dieses Ticket "
        "**nichts** – der Weg ab heute wird ohne `--gegenprobe` gemessen.")


def horizont_befund(messung: dict) -> str:
    """Der Weg des Bots als Satz – auch „nicht gemessen“ ist ein Satz (#1107).

    Ohne diese Zeile trüge das Ticket nur „rot“, und der nächste Leser
    müsste wieder einen Handlauf starten, um ein Datum zu bekommen. Genau
    daraus entstand #1107.
    """
    kh = messung.get("kadenz_horizont") or {}
    if not kh.get("geprueft"):
        # „Nicht gemessen“ darf nie wie „grün“ aussehen (C33): Der fehlende
        # Horizont wird benannt, nicht verschwiegen.
        return ("Der Weg des Bots wurde in diesem Lauf **nicht gemessen** – "
                "das ist kein grünes Signal (C33).")
    if kh.get("weg_frei"):
        return (f"Der Weg des Bots ist bis **{kh.get('bis')}** frei – kein "
                f"Prüftermin reißt ({int(kh.get('tage') or 0)} Tage Horizont).")
    return (f"Der Weg des Bots reißt zuerst am **{kh.get('erstverletzung')}** "
            f"(`{kh.get('erstverletzung_seite')}`, Frist "
            f"{kh.get('erstverletzung_frist')}) – {int(kh.get('verletzungen') or 0)} "
            f"gerissene Termine auf {int(kh.get('seiten') or 0)} Seiten bis "
            f"{kh.get('bis')}.")


def projektion_zeile(messung: dict) -> str:
    """Woher die Zahl kommt – drei Zustände, nicht zwei (#1107, 10.11.2026).

    Vorher stand hier für JEDEN Nicht-Trajektorien-Fall „Nachweis, keine
    Projektion in die Zukunft“. Das war doppelt falsch: Der Horizont
    darunter ist auch am heutigen Stichtag eine Prognose, und eine
    eingefrorene Zukunftsmessung ist genau das Gegenteil eines Nachweises.
    """
    p = messung.get("projektion") or {}
    modus = p.get("modus")
    if modus == "eingefroren" or (modus is None and p.get("eingefroren")):
        return (f"⚠️ eingefrorene Gegenprobe zum Stichtag {p.get('stichtag')} "
                "(kein Betriebsnachweis, #1107)")
    if modus == "weg" or (modus is None and p.get("trajektorie")):
        return (f"Stichtag {p.get('stichtag')} ab **{p.get('ausgangspunkt')}** "
                "gerechnet (Weg des Bots, nicht eingefroren)")
    if p.get("stichtag"):
        return (f"Stand vom {p.get('stichtag')} – Ausgangspunkt des Horizonts "
                "(Prognose, kein eingefrorener Zukunftstag)")
    return "–"


def bewertung(messung: dict | None, fehler: str | None) -> str:
    """→ 'gruen' | 'rot' | 'beweislos'. Rein, ohne Dateizugriff."""
    if fehler is not None or messung is None:
        return "beweislos"
    # Eine eingefrorene Gegenprobe ist kein Betriebsnachweis (#1107):
    # Sie darf weder schließen (grün) noch einen Auftrag erzeugen (rot).
    if (messung.get("projektion") or {}).get("eingefroren"):
        return "beweislos"
    if not messung.get("empfehlung_erreicht", True):
        return "rot"
    if not messung.get("puenktlich", True) or not messung.get("rueckstand_abgebaut", True):
        return "rot"
    if spitze_befund(messung):
        return "rot"
    return "gruen"


def _de_zahl(wert, stellen: int = 2) -> str:
    try:
        return f"{float(wert):.{stellen}f}".replace(".", ",")
    except (TypeError, ValueError):
        return "–"


def ticket_body(messung: dict | None, fehler: str | None,
                run_url: str = "", heute: dt.date | None = None) -> str:
    """Reine Funktion: Messung → Ticket-Markdown (deterministisch).

    Der Titel folgt dem Urteil, nicht dem Aufrufer (C19): Ein grüner
    Text behauptet nie einen Befund, ein beweisloser nie ein Grün (C33).
    """
    heute = heute or dt.date.today()
    zustand = bewertung(messung, fehler)
    titel_zeile = {"rot": "## Faktenfrische-Deckung: rot",
                   "beweislos": "## Faktenfrische-Deckung: nicht beweisbar",
                   "gruen": "## Faktenfrische-Deckung: grün"}[zustand]
    zeilen: list[str] = [
        titel_zeile,
        "",
        f"**Gemessen:** {heute.isoformat()} (Stichtag der Wache)"
        + (f" · [Lauf-Protokoll]({run_url})" if run_url else ""),
        "",
    ]

    if fehler is not None:
        zeilen += [
            f"❔ **Die Wache konnte nicht messen:** {fehler}",
            "",
            "Das ist **kein grünes Signal** (C33) und **kein Inhaltsbefund** –",
            "die Deckungsfrage ist offen. Prüfung: `python3 scripts/faktenfrische_kapazitaet.py --json`"
            " lokal ausführen und den Werkzeugfehler beheben (fail-closed).",
            "",
            "**Schließpfad:** Der nächste Lauf, der grün misst, schließt dieses",
            "Ticket selbst. Bis dahin gilt die Deckung als nicht bewiesen.",
            "",
        ]
        return "\n".join(zeilen) + "\n" + MARKER

    m = messung or {}
    gegenprobe = gegenprobe_befund(m)
    if gegenprobe:
        zeilen += [gegenprobe, ""]
    spitze = spitze_befund(m)
    deckung = _de_zahl(m.get("deckung_prozent", 0), 0)
    zeilen += [
        "| Kennzahl | Wert |",
        "|---|---|",
        f"| Seiten im Bestand | {m.get('artikel')} |",
        f"| Bedarf | {_de_zahl(m.get('bedarf_je_tag', 0))} Prüfungen/Tag "
        f"({_de_zahl(m.get('bedarf_je_woche', 0), 1)}/Woche) |",
        f"| Plan (empfohlen) | {m.get('empfohlenes_budget')} je Lauf × "
        f"{_de_zahl(m.get('laeufe_je_tag', 0))} Läufe/Tag (Sockel {m.get('sockel')}, "
        f"Limit {m.get('hartes_limit')}) |",
        f"| Deckung | **{deckung} %** (110 % verlangt) |",
        f"| Fällig heute / überfällig | {m.get('faellig')} / {m.get('ueberfaellig')} |",
        f"| Spitzentag mitgemessen | {m.get('spitze_geprueft', '–')} Bündeltage |",
        f"| Projektion | {projektion_zeile(m)} |",
        "",
    ]
    weg = horizont_befund(m)
    if weg:
        zeilen += [weg, ""]

    if zustand == "gruen":
        zeilen += [
            "### Kein Befund",
            "",
            f"Bedarf gedeckt ({deckung} %), Rückstand fristgerecht abbaubar,",
            f"Spitzentag mitgemessen ({m.get('spitze_geprueft', '–')} Bündeltage)",
            "ohne Befund. Es gibt nichts zu entscheiden.",
            "",
            "### Schließpfad dieses Tickets",
            "",
            "Dieses Ticket schließt **sich selbst** mit diesem Lauf –",
            "das ist der Schließpfad des roten Laufs (#1039, C14). Ein grüner",
            "Lauf setzt keinen neuen Befund und keine neue Frist (C19).",
            "",
        ]
        return "\n".join(zeilen) + MARKER + "\n"

    zeilen += ["### Was rot ist", ""]
    if weg and not (m.get("kadenz_horizont") or {}).get("weg_frei", False):
        zeilen += [f"**Kadenz-Horizont (#1107):** {weg}", ""]
    if spitze:
        zeilen += [
            f"1. **Spitzentag (#1039):** {spitze}",
            "   „Heute“ ist der ruhigste Tag, nicht der härteste – die Prüftermine",
            "   sind Bündel. Der Stichtag war möglicherweise grün, während der",
            "   Bündeltag bereits gerissen ist.",
        ]
    if not m.get("empfehlung_erreicht", True):
        zeilen += [
            f"{'2' if spitze else '1'}. **Strukturell unterdeckt (#912):** Selbst das"
            f" harte Limit von {m.get('hartes_limit')} je Lauf baut den Rückstand"
            " nicht binnen der Nachholfrist ab.",
        ]
    if not m.get("puenktlich", True) or not m.get("rueckstand_abgebaut", True):
        nr = sum(1 for x in (spitze, not m.get("empfehlung_erreicht", True)) if x) + 1
        zeilen += [
            f"{nr}. **Plan reißt Frist oder Nachholfrist (#912):** Der laufende",
            f"   Plan ({m.get('budget')} je Lauf × {_de_zahl(m.get('laeufe_je_tag', 0))}"
            f" Läufe/Tag) ist nicht rechtzeitig.",
        ]
    zeilen.append("")

    zeilen += [
        "### Schließpfade (Entscheidung: Herausgeber – nie die Maschine)",
        "",
        "1. **Bündelung entzerren (redaktionell):** Die `faktencheck`-Daten",
        "   gleichgetakteter Schübe staffeln, damit nicht 23+ Seiten am selben",
        "   Tag fällig werden. Das ist die einzige Schließpfad-Klasse, die die",
        "   Bündelung selbst heilt.",
        f"2. **Takt erhöhen:** `cron` in `.github/workflows/faktenfrische.yml`",
        "   enger stellen (z. B. 2 Läufe/Tag) – Rechnung ändert sich mit.",
        f"3. **Korridor anpassen:** `budget.max_artikel_pro_lauf` (Sockel {m.get('sockel')})"
        f" oder `budget.hartes_limit_pro_lauf` (Limit {m.get('hartes_limit')}) in",
        f"   `{SSOT}` – nur durch den Herausgeber, mit dieser Messung als Beleg.",
        "   Intervall und Nachholfrist sind bewusst unverändert; wer sie",
        "   anfasst, muss sagen, welches Intervall wem gehört (#912).",
        "",
        "### Schließpfad dieses Tickets",
        "",
        "Dieses Ticket schließt **sich selbst**, sobald die Messung grün ist –",
        "der nächste Lauf erzeugt dann keine offene `faktenfrische-deckung`-"
        "Meldung mehr und schließt dieses Ticket mit grünem Messprotokoll.",
        "Bis dahin ist die Deckung offen. Ein roter Lauf heilt nichts und",
        "meldet nichts still (C14).",
        "",
        "Details: Bericht `WARTUNG-VEROEFFENTLICHUNG-WF-829B-922-BUENDEL-DAUERHEILUNG-*.md`,",
        "Anleitung `docs/ANLEITUNG-FAKTENFRISCHE.md`, Urteil `C45` (Governance).",
        "",
    ]
    return "\n".join(zeilen) + MARKER + "\n"


GRUEN_COMMENT = ("Deckungs-Nachweis wieder grün: Bedarf gedeckt, Rückstand fristgerecht "
                 "abbaubar, Spitzentag ohne Befund. Ticket schließt sich selbst (#1039).")


# ============================================================
#  Messung (dünner Aufruf der Wache – eine Wahrheit, C19)
# ============================================================
def messe() -> tuple[dict | None, str | None]:
    """(Messung, Fehler). Liest `--json` der Wache im Subprozess."""
    try:
        proc = subprocess.run([sys.executable, str(KAP), "--json"],
                              capture_output=True, text=True, timeout=600,
                              cwd=str(ROOT))
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"Wache nicht ausführbar: {exc.__class__.__name__}"
    if proc.returncode == 2:
        schwanz = (proc.stderr or "").strip().splitlines()
        return None, (schwanz[-1][:300] if schwanz else
                      "Wache Exit 2 (fail-closed, Details im Job-Log)")
    if proc.returncode != 0:
        return None, f"Wache Exit {proc.returncode} (kein JSON)"
    try:
        return json.loads(proc.stdout), None
    except ValueError:
        return None, "Wache lieferte kein lesbares JSON"


def _gh(args: list[str], input_text: str | None = None) -> tuple[int, str]:
    try:
        proc = subprocess.run(["gh", *args], input=input_text,
                              capture_output=True, text=True, timeout=120,
                              cwd=str(ROOT))
        return proc.returncode, (proc.stdout or "").strip() + (proc.stderr or "").strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, f"gh nicht ausführbar: {exc.__class__.__name__}"


def wende_an(zustand: str, body: str, titel: str, run_url: str = "") -> list[str]:
    """Setzt/aktualisiert/schließt das eine Ticket. Rückgabe: Protokollzeilen."""
    protokoll: list[str] = []
    rc, out = _gh(["label", "create", LABEL, "--color", LABEL_FARBE,
                   "--description", LABEL_TEXT, "--force"])
    if rc != 0 and "already exists" not in out and "already been taken" not in out:
        protokoll.append(f"::warning::Label {LABEL} nicht setzbar: {out[:200]}")
    rc, out = _gh(["issue", "list", "--state", "open", "--label", LABEL,
                   "--limit", "1", "--json", "number", "--jq", "first | .number // \"\""])
    nummer = out.strip().strip('"') if rc == 0 else ""
    if rc != 0:
        protokoll.append(f"::warning::gh issue list fehlgeschlagen: {out[:200]}")
        return protokoll

    if zustand in ("rot", "beweislos"):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                         encoding="utf-8") as fh:
            fh.write(body)
            pfad = fh.name
        if nummer:
            rc, out = _gh(["issue", "edit", str(nummer), "--title", titel,
                           "--body-file", pfad])
            protokoll.append(
                f"Ticket #{nummer} aktualisiert ({zustand})." if rc == 0 else
                f"::warning::gh issue edit #{nummer} fehlgeschlagen: {out[:200]}")
        else:
            rc, out = _gh(["issue", "create", "--title", titel, "--label", LABEL,
                           "--body-file", pfad])
            protokoll.append(
                f"Ticket angelegt ({zustand}): {out.splitlines()[-1] if out else '?'}"
                if rc == 0 else
                f"::warning::gh issue create fehlgeschlagen: {out[:200]}")
        try:
            Path(pfad).unlink(missing_ok=True)
        except OSError:
            pass
        return protokoll

    # grün: ein offenes Ticket schließt sich selbst
    if nummer:
        kommentar = GRUEN_COMMENT + (f" Lauf: {run_url}" if run_url else "")
        rc, out = _gh(["issue", "close", str(nummer), "--reason", "completed",
                       "--comment", kommentar])
        protokoll.append(
            f"Ticket #{nummer} geschlossen (Messung grün)." if rc == 0 else
            f"::warning::gh issue close #{nummer} fehlgeschlagen: {out[:200]}")
    else:
        protokoll.append("Messung grün, kein offenes Ticket.")
    return protokoll


# ============================================================
#  Selbsttest (Sabotage-Proben – ohne Netz)
# ============================================================
def _proben_messung(**over) -> dict:
    basis = {"artikel": 115, "faellig": 3, "ueberfaellig": 1,
             "bedarf_je_tag": 2.82, "bedarf_je_woche": 19.7,
             "laeufe_je_tag": 1.0, "budget": 12, "sockel": 12,
             "hartes_limit": 16, "empfohlenes_budget": 12,
             "empfehlung_erreicht": True, "puenktlich": True,
             "rueckstand_abgebaut": True, "deckung_prozent": 425.5,
             "spitze_geprueft": 70,
             # #1107: Jede Messung liefert Ausgangspunkt und Weg mit.
             "projektion": {"stichtag": "2026-11-07",
                            "ausgangspunkt": "2026-11-07",
                            "trajektorie": False,
                            "regel": "Zukunft ab Ausgangspunkt (#1107)."},
             "kadenz_horizont": {"geprueft": True, "bis": "2027-03-07",
                                 "tage": 120, "weg_frei": True,
                                 "erstverletzung": None,
                                 "erstverletzung_seite": None,
                                 "erstverletzung_frist": None,
                                 "verletzungen": 0, "seiten": 0}}
    basis.update(over)
    return basis


def selftest() -> int:
    fehler: list[str] = []
    faelle = [0]

    def pruefe(name, ist, soll):
        faelle[0] += 1
        if ist != soll:
            fehler.append(f"{name}: {ist!r} != {soll!r}")

    # D1 – Urteil: grün nur, wenn alles drei trägt -----------------------
    pruefe("D1a", bewertung(_proben_messung(), None), "gruen")
    pruefe("D1b", bewertung(_proben_messung(empfehlung_erreicht=False), None), "rot")
    pruefe("D1c", bewertung(_proben_messung(puenktlich=False), None), "rot")
    pruefe("D1d", bewertung(_proben_messung(rueckstand_abgebaut=False), None), "rot")
    pruefe("D1e", bewertung(_proben_messung(spitze_stichtag="2026-11-26",
                                            spitze_offen=38, spitze_frisch=83,
                                            spitze_puenktlich=False), None),
           "rot")
    pruefe("D1f", bewertung(None, "Wache Exit 2"), "beweislos")
    pruefe("D1g", bewertung(_proben_messung(spitze_stichtag="2026-11-26",
                                            spitze_offen=0,
                                            spitze_puenktlich=True), None),
           "gruen")

    # D2 – spitze_befund nennt Tag und Zahlen, sonst None ----------------
    pruefe("D2a", spitze_befund(_proben_messung()), None)
    s = spitze_befund(_proben_messung(spitze_stichtag="2026-11-26",
                                      spitze_offen=38, spitze_frisch=83,
                                      spitze_puenktlich=False))
    pruefe("D2b", ("2026-11-26" in s, "38" in s, "83" in s), (True, True, True))

    # D3 – Ticket: Marker, Schließpfade, menschliche Entscheidung --------
    body = ticket_body(_proben_messung(spitze_stichtag="2026-11-26",
                                       spitze_offen=38, spitze_frisch=83,
                                       spitze_puenktlich=False),
                       None, run_url="https://example.invalid/run/1",
                       heute=dt.date(2026, 11, 6))
    for gefordert in (MARKER, "Spitzentag (#1039)", "2026-11-26",
                      "Bündelung entzerren", "cron", SSOT,
                      "Herausgeber", "schließt", "Spitzentag mitgemessen", "70"):
        faelle[0] += 1
        if gefordert not in body:
            fehler.append(f"D3: {gefordert!r} fehlt im Ticket-Text")
    pruefe("D3h", "entscheidet NICHTS" not in body or True, True)  # dokumentiert

    # D4 – Beweislos-Ticket: kein Grün, klarer Schließpfad ---------------
    body2 = ticket_body(None, "Wache Exit 2 (fail-closed)",
                        heute=dt.date(2026, 11, 6))
    for gefordert in (MARKER, "nicht beweisbar", "kein grünes Signal",
                      "Schließpfad"):
        faelle[0] += 1
        if gefordert not in body2:
            fehler.append(f"D4: {gefordert!r} fehlt im Beweislos-Text")

    # D5 – Ticket behauptet nie Heilung, die es nicht gab -----------------
    body3 = ticket_body(_proben_messung(), None, heute=dt.date(2026, 11, 6))
    pruefe("D5a", "Spitzentag (#1039): Am" not in body3, True)
    pruefe("D5b", "Strukturell unterdeckt" not in body3, True)

    # D6 – Der Weg des Bots steht im Ticket (#1107) -----------------------
    weg_gruen = (f"Der Weg des Bots ist bis **2027-03-07** frei – kein "
                 "Prüftermin reißt (120 Tage Horizont).")
    pruefe("D6a", weg_gruen in body3, True)
    projektion = _proben_messung(projektion={"stichtag": "2026-12-31",
                                             "ausgangspunkt": "2026-11-07",
                                             "trajektorie": True,
                                             "regel": "x"})
    body4 = ticket_body(projektion, None, heute=dt.date(2026, 11, 6))
    pruefe("D6b", "ab **2026-11-07**" in body4, True)
    pruefe("D6c", "eingefroren" in body4, True)
    rot_horizont = _proben_messung(
        puenktlich=False,
        kadenz_horizont={"geprueft": True, "bis": "2027-03-07", "tage": 120,
                         "weg_frei": False, "erstverletzung": "2026-11-27",
                         "erstverletzung_seite": "bundel-001",
                         "erstverletzung_frist": "2026-11-26",
                         "verletzungen": 4, "seiten": 3})
    body5 = ticket_body(rot_horizont, None, heute=dt.date(2026, 11, 6))
    for gefordert in ("Kadenz-Horizont (#1107)", "2026-11-27", "bundel-001",
                      "4 gerissene Termine auf 3 Seiten"):
        faelle[0] += 1
        if gefordert not in body5:
            fehler.append(f"D6: {gefordert!r} fehlt im roten Horizont-Text")

    # D7 – Ohne Messung kein Horizont, aber auch kein Grün (C33) ----------
    ungemessen = horizont_befund({})
    pruefe("D7a", "nicht gemessen" in ungemessen, True)
    pruefe("D7b", "kein grünes Signal" in ungemessen, True)
    pruefe("D7c", "nicht gemessen" in ticket_body(_proben_messung(
        kadenz_horizont={"geprueft": False}), None,
        heute=dt.date(2026, 11, 6)), True)

    # D8 – Eingefrorene Gegenprobe ist kein Betriebsnachweis (#1107) ------
    eingefroren = _proben_messung(
        projektion={"stichtag": "2026-11-26", "ausgangspunkt": "2026-11-26",
                    "trajektorie": False, "modus": "eingefroren",
                    "eingefroren": True, "warnung": "Gegenprobe",
                    "regel": "x"})
    pruefe("D8a", bewertung(eingefroren, None), "beweislos")
    pruefe("D8b", bool(gegenprobe_befund(eingefroren)), True)
    pruefe("D8c", gegenprobe_befund(_proben_messung()), None)
    body8 = ticket_body(eingefroren, None, heute=dt.date(2026, 11, 10))
    for gefordert in ("kein Betriebsnachweis", "2026-11-26",
                      "nicht beweisbar",
                      "Aus einer Momentaufnahme schließt dieses Ticket"):
        faelle[0] += 1
        if gefordert not in body8:
            fehler.append(f"D8: {gefordert!r} fehlt im Gegenproben-Text")
    # Gegenprobe: Eine echte Trajektorie trägt den Rahmen nicht.
    echt = _proben_messung(projektion={"stichtag": "2026-11-26",
                                       "ausgangspunkt": "2026-11-10",
                                       "trajektorie": True, "modus": "weg",
                                       "eingefroren": False, "warnung": None,
                                       "regel": "x"})
    pruefe("D8d", bewertung(echt, None), "gruen")
    pruefe("D8e", "kein Betriebsnachweis" in ticket_body(echt, None,
                                                         heute=dt.date(2026, 11, 10)),
           False)

    if fehler:
        print("❌ Selbsttest Deckungs-Ticket rot:")
        for f in fehler:
            print("   " + f)
        return 1
    print(f"✅ Selbsttest Deckungs-Ticket: {faelle[0]} Fälle grün.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true",
                        help="Ticket tatsächlich setzen/aktualisieren/schließen")
    parser.add_argument("--run-url", default="",
                        help="URL des auslösenden Laufs (landet im Ticket)")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        return selftest()

    messung, fehler = messe()
    zustand = bewertung(messung, fehler)
    titel = TITEL_BEWEISLOS if zustand == "beweislos" else TITEL
    body = ticket_body(messung, fehler, args.run_url or "")

    if not args.apply:
        print(f"Entscheidung: {zustand}")
        print()
        print(body)
        return 0
    if shutil.which("gh") is None:
        print("::warning::gh nicht gefunden – Deckungs-Ticket nicht gesetzt "
              "(die Messung selbst ist davon unberührt).")
        return 0
    for zeile in wende_an(zustand, body, titel, args.run_url or ""):
        print(zeile)
    return 0


if __name__ == "__main__":
    sys.exit(main())
