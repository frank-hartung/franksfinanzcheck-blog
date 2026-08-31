#!/usr/bin/env python3
"""park_state.py – PARK-/RE-QUEUE-ZUSTAND eines Posts (Single Source of Truth)

WARUM DIESE DATEI EXISTIER (31.08.2026, Premium-Level-Fix zu Issue #129/#130):
  Die Automatik schreibt an einem Post vier Dinge, die gemeinsam entscheiden, ob
  und wann er wieder live geht:

      draft: true|false      → Hugo-Ausschalter (buildDrafts = false)
      cadence_wait: true     → "wartet auf den nächsten freien Slot"
      cadence_demoted: <iso> → wann zurückgestuft
      cadence_grund: "<text>" → WARUM (und damit: darf die Automatik sie
                                zurückholen – oder blockiert etwas bewusst?)

  Der alte Zustand war MEHRDEUTIG: "draft: true ohne cadence_wait" konnte
  bedeuten (a) Franks manueller Entwurf (darf die Automatik nie anfassen),
  (b) bewusste Zurückhaltung durch ein Qualitäts-Gate (darf NICHT
  automatisch zurückgeholt werden) oder (c) ein VERLORENES Flag – der Post ist
  für immer unsichtbar, weil ihn kein Re-Queue mehr kennt. Fall (c) war
  real: vier fertige Artikel lagen so im Bestand (heute 1 statt 2–3 Live-
  Artikel laut CADENCE-GATE-REPORT.md), und dieselben vier waren Auslöser der
  defekten internen Links in Issue #129.

  Ab jetzt ist jede Zustandsänderung EINE Funktion dieses Moduls, und jeder
  Schreibende nennt einen Grund. Das macht den Zustand unterscheidbar und
  damit reparierbar – ohne dass jemals ein manueller Entwurf oder ein bewusst
  gehaltenes Artefakt automatisch veröffentlicht wird.

ZUSTANDSMASCHINE (read() liefert genau einen davon):

    live      draft: false, keine cadence_*-Felder            (normal)
    queue     draft: true  + cadence_wait: true               → wird am
              nächsten Publikationstag bis zum Tageslimit
              promoted (cadence_guard.requeue_to_capacity)
    hold      draft: true  + cadence_grund, OHNE cadence_wait → blockiert,
              wartet auf menschliche Korrektur (publish_gate,
              check_uniqueness). NIEMALS automatisch promoted.
    manual    draft: true  ohne jegliche cadence_*-Felder     → Franks
              Entwurf, von der Automatik unangetastet (Draft-Schutz)
    lost      draft: true  + cadence_demoted/cadence_grund, aber OHNE
              cadence_wait und OHNE Grund                      → Bug-Zustand,
              wird von cadence_guard --fix rearmt (nur das Flag, nie Content)

    (live + Park-Feld = Rest einer Promotion ohne Bereinigung → "stale",
     bereinigt von cadence_guard --fix über clean_stale())

SICHERHEITSREGELN (harte Grenzen, im Selbsttest eingefroren):
  * Kein Schreibgriff dieses Moduls veröffentlicht jemals einen Post –
    promotion entscheidet allein cadence_guard (Publikationstag + Limit).
  * park()/hold()/rearm()/release() ändern ausschließlich Frontmatter-Zeilen,
    nie den Body; der Grund wird YAML-sicher zitisiert (kein kaputtes
    Frontmatter durch Anführungszeichen im Text).
  * manual wird nie angefasst (kein Grund-Feld => keine Automatik-Handchrift).
  * Alle Operationen sind idempotent: zweiter Lauf = keine Änderung.

AUFRUF (Bibliothek; kein CLI-Sinn – Kontrolle bleibt bei cadence_guard):
    from park_state import read, park, hold, release, rearm, state_of
"""
import datetime
import os
import re

# Die von diesem Modul verwalteten Frontmatter-Schlüssel.
FIELDS = ("cadence_wait", "cadence_demoted", "cadence_grund")

_DRAFT_RE = re.compile(r"(?m)^draft:\s*(true|false)\s*$")


def _fm_span(lines):
    """(start, end) des Frontmatter-Bereichs oder None."""
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return (1, i)
    return None


def _frontmatter(content):
    parts = content.split("---", 2)
    if len(parts) == 3 and parts[0] == "":
        return parts[1]
    return ""


def _field(fm, key):
    m = re.search(rf"(?m)^{re.escape(key)}:\s*(.*?)\s*$", fm)
    if not m:
        return None
    return m.group(1).strip("\"'")


def _truthy(value):
    if value is None:
        return False
    return str(value).strip().lower() in ("true", "yes", "1")


def state_of(content):
    """Zustand der Post-Park-Maschine: live | queue | hold | manual | lost
    (plus Sonderfall "stale" über is_stale_flag())."""
    fm = _frontmatter(content)
    m = _DRAFT_RE.search(fm)
    draft = (m.group(1) == "true") if m else False
    wait = _truthy(_field(fm, "cadence_wait"))
    grund = _field(fm, "cadence_grund")
    demoted = _field(fm, "cadence_demoted")

    if not draft:
        return "live"
    if wait:
        return "queue"
    if grund:
        return "hold"
    if demoted:
        return "lost"          # Automatik hat geparkt, Flag ist verloren
    return "manual"             # kein cadence_* → menschlicher Entwurf


def rest_fields(post):
    """Park-Felder, die an einem LIVE-Post noch stehen – Rest einer Promotion
    ohne Bereinigung (cadence_wait allein wäre nur ein Teil des Bildes).
    Leere Liste = sauber. Akzeptiert das dict aus read()/load_posts(), damit
    kein zweiter Lesevorgang nötig ist; die Zustands-Semantik bleibt hier."""
    keys = (("cadence_wait", "wait"), ("cadence_demoted", "demoted"),
            ("cadence_grund", "grund"))
    return [name for name, key in keys
            if post.get(key) not in (None, "", False)]


def read(content):
    """Vollständiger Park-Zustand eines Post-Inhalts (lesbar, keine Änderung).

    Rückgabe: dict(state, draft, wait, demoted, grund, age_days).
    `age_days` = Tage seit cadence_demoted (None ohne Zeitstempel)."""
    fm = _frontmatter(content)
    m = _DRAFT_RE.search(fm)
    state = state_of(content)
    demoted = _field(fm, "cadence_demoted")
    age = None
    if demoted:
        try:
            iso = str(demoted)[:10]
            age = (datetime.date.today()
                   - datetime.date.fromisoformat(iso)).days
        except (ValueError, TypeError):
            age = None
    return {
        "state": state,
        "draft": bool(m and m.group(1) == "true"),
        "wait": _truthy(_field(fm, "cadence_wait")),
        "demoted": demoted,
        "grund": _field(fm, "cadence_grund"),
        "age_days": age,
    }


def _yaml_str(text):
    """Zitiert einen freien Text als sichere YAML-Zeile. Ein Grund wie
    publish-gate: „Zeichenlänge nicht „bestanden"“ würde mit rohem
    Anführungszeichen das ganze Frontmatter unlesbar machen – und ein
    kaputtes Frontmatter ist ein nicht gebauter Post."""
    safe = str(text).replace('"', "'").replace("\n", " ").strip()
    return f'"{safe}"'


def now_utc_iso():
    """UTC-Zeitstempel (1 Minute zurück – nie ein Future-Post)."""
    return (datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")


def set_field(path, key, value):
    """Setzt/entfernt EINE Frontmatter-Zeile (Wert None/False = entfernen).

    Verankert direkt nach `draft:`, damit die Park-Felder beieinanderbleiben.
    Idempotent, berührt sonst nichts, Body wird nie angefasst.
    Rückgabe: True bei tatsächlicher Änderung."""
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    span = _fm_span(lines)
    if span is None:
        return False
    start, end = span

    existing = [i for i in range(start, end)
                if lines[i].startswith(key + ":")]
    draft_i = next((i for i in range(start, end)
                    if lines[i].startswith("draft:")), None)
    anchor = (draft_i + 1) if draft_i is not None else end

    if value is None or value is False:
        if not existing:
            return False
        for i in reversed(existing):
            del lines[i]
    else:
        text = f"{key}: {value}\n" if not isinstance(value, bool) else \
            f"{key}: {'true' if value else 'false'}\n"
        if existing:
            lines[existing[0]] = text
            for dup in reversed(existing[1:]):   # Duplikate sind ein Fehler
                del lines[dup]
        else:
            lines.insert(anchor, text)

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return True


def _apply(path, wanted):
    """Setzt mehrere Felder; True wenn irgendetwas geändert wurde.

    Reihenfolge ist Absicht: erst `draft`, dann die cadence_*-Felder in
    kanonischer Reihenfolge (wait · demoted · grund). Neue Zeilen werden alle
    an denselben Anker (direkt nach `draft:`) gesetzt – in umgekehrter
    Reihenfolge eingesetzt, entsteht trotzdem die kanonische Lesereihenfolge.
    Das hält Frontmatter-Diffs zwischen park()/hold()/rearm() stabil und
    verhindert, dass je nach Aufruf unterschiedliche Feldordnungen entstehen."""
    keys = sorted((k for k in wanted if k != "draft"),
                  key=lambda k: FIELDS.index(k) if k in FIELDS else 99)
    changed = False
    if "draft" in wanted:
        changed = set_draft(path, bool(wanted["draft"])) or changed
    for key in reversed(keys):
        changed = set_field(path, key, wanted[key]) or changed
    return changed


def set_draft(path, draft):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    new = _DRAFT_RE.sub(f"draft: {'true' if draft else 'false'}", content,
                        count=1)
    if new == content:
        return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)
    return True


# ---------------------------------------------------------------------------
# Die drei Schreibgriffe der Automatik
# ---------------------------------------------------------------------------

def park(path, grund, when=None, do_fix=True):
    """Zurückstufen UND in die Re-Queue legen (kadenz-/kapazitätsbedingt).

    Der Post darf beim nächsten freien Slot automatisch wieder promotioniert
    werden – deshalb ist `cadence_wait: true` hier zwingend, nicht optional."""
    if not do_fix:
        return True
    return _apply(path, {
        "draft": True,
        "cadence_wait": True,
        "cadence_demoted": when or now_utc_iso(),
        "cadence_grund": _yaml_str(grund),
    })


def hold(path, grund, when=None, do_fix=True):
    """Zurückstufen mit BLOCKADE: Inhalt braucht Korrektur (Gate-Fund,
    Duplikat). Bewusst OHNE cadence_wait – die Automatik soll ihn nicht
    zurückholen, aber der Grund steht jetzt dokumentiert im Frontmatter,
    damit "draft ohne cadence_wait" nie wieder mehrdeutig ist."""
    if not do_fix:
        return True
    return _apply(path, {
        "draft": True,
        "cadence_wait": None,
        "cadence_demoted": when or now_utc_iso(),
        "cadence_grund": _yaml_str(grund),
    })


def release(path, do_fix=True):
    """Promotion/ Freigabe: live + alle Park-Felder weg (sonst hinterlässt
    jede Promotion müde Flag-Reste, die wie ein verlorener Zustand aussehen).
    body: unverändert."""
    if not do_fix:
        return True
    return _apply(path, {
        "draft": False,
        "cadence_wait": None,
        "cadence_demoted": None,
        "cadence_grund": None,
    })


def rearm(path, grund, when=None, do_fix=True):
    """Reparatur des Bug-Zustands "lost": Re-Queue-Flag wiederherstellen.

    Ändert NIE draft und NIE den Inhalt – der Post bleibt Entwurf, bis
    cadence_guard ihn am nächsten Publikationstag bis zum Tageslimit
    promotioniert. Das ursprüngliche `cadence_demoted`-Datum BLEIBT stehen
    (es ist die Wahrheit darüber, wann der Post verschwand – der Report
    führt sein Wartealter sonst zu schön)."""
    if not do_fix:
        return True
    wanted = {
        "cadence_wait": True,
        "cadence_grund": _yaml_str(grund),
    }
    with open(path, encoding="utf-8") as f:
        ist = read(f.read())
    if not ist["demoted"]:
        wanted["cadence_demoted"] = when or now_utc_iso()
    return _apply(path, wanted)


def clean_stale(path, do_fix=True):
    """Rest-Feldbereinigung bei live-Posts (cadence_wait/demoted/grund)."""
    if not do_fix:
        return True
    return _apply(path, {
        "cadence_wait": None,
        "cadence_demoted": None,
        "cadence_grund": None,
    })
