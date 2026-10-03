#!/usr/bin/env python3
# ============================================================
#  KI-TRANSPORTWEG-GATE – der Vertrag T1–T9
#  ------------------------------------------------------------
#  Rollout 03.10.2026. SSOT: data/ki_transportweg.yaml
#  Runbook: docs/ANLEITUNG-KI-TRANSPORTWEG.md
#  Cockpit: KI-TRANSPORTWEG-STATUS.md
#
#  Dieses Gate beantwortet zwei Fragen und verwechselt sie nie:
#    1. Ist der VERTRAG eingehalten?    → darf rot werden (Exit 1)
#    2. Ist gerade alles EINSATZBEREIT? → Standby ist gelb, nicht rot
#
#  SEIT 03.10.2026 IST T1 EINE DAUERSPERRE, KEIN HINWEIS: Es existiert
#  kein kostenpflichtiger Weg mehr – nicht in der SSOT, nicht im
#  Client, nicht als Schlüssel oder Endpunkt in Skripten und
#  Workflows. Rückkehr = Exit 1.
#
#  Die Trennung ist der Kern. Ein fehlender NVIDIA_API_KEY ist ein
#  Betriebszustand – die Writer haben einen Offline-Modus. Eine Kette
#  mit nur einem Gratis-Glied ist ein Vertragsbruch: Sie hält die
#  ganze Produktion an, sobald ein Hoster sein Tageskontingent
#  verbraucht hat.
#
#  WARUM ES DIESES GATE GIBT
#  Issue #514: Zwei Automatiken liefen monatelang gegen ein Konto,
#  das es nie gab. Sie fielen nicht aus – sie meldeten „übersprungen"
#  und galten als grün. Eine Automatik, die strukturell nie gelingen
#  kann, ist schlimmer als keine. Dieses Gate macht genau diesen
#  Zustand sichtbar, BEVOR er zum Dauerzustand wird.
#
#  AUFRUF
#    python3 scripts/ki_transportweg.py              # Bericht + Cockpit
#    python3 scripts/ki_transportweg.py --status     # nur Betriebslage
#    python3 scripts/ki_transportweg.py --json       # maschinenlesbar
#    python3 scripts/ki_transportweg.py --selftest   # Sabotage-Proben
#    python3 scripts/ki_transportweg.py --ping       # echte Live-Probe
#    python3 scripts/ki_transportweg.py --strict     # Standby wird rot
#
#  Exit: 0 = Vertrag gehalten, 1 = Vertragsbruch, 2 = Gate selbst defekt.
# ============================================================
from __future__ import annotations

import argparse
import copy
import datetime
import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import yaml  # noqa: E402

import llm_client  # noqa: E402

SSOT = ROOT / "data" / "ki_transportweg.yaml"
COCKPIT = ROOT / "KI-TRANSPORTWEG-STATUS.md"
RUNBOOK = "docs/ANLEITUNG-KI-TRANSPORTWEG.md"

BEREIT, STANDBY, DEFEKT = "bereit", "standby", "defekt"

REGELN = {
    "T1": "Kostenfreiheit – kein kostenpflichtiger Weg existiert (SSOT/Client/Code/CI)",
    "T2": "Nur implementierte Anbieter – keine Phantom-Provider",
    "T3": "Redundanz – mindestens zwei Gratis-Glieder je Kette",
    "T4": "OpenAI-Bahn – mindestens ein echter OpenAI-Modell-Hoster je Kette",
    "T5": "Keine Brücken – kein UI-Scraping, kein geteiltes Fremdkonto",
    "T6": "Ein Transportweg – alle Rufer nutzen scripts/llm_client.py",
    "T7": "Routing vollständig – jede Pflicht-Aufgabe hat eine Kette",
    "T8": "Verdrahtung – Runbook, Cockpit und npm-Skripte existieren",
    "T9": "Schlüssel-Durchreichung – KI-Workflows bekommen ≥2 Gratis-Schlüssel",
    "T10": "Kostensperre – jede Geldfläche außerhalb der Textkette ist verriegelt",
}

# Aufgaben, für die eine Kette existieren MUSS (T7). Jede entspricht
# einer real laufenden Automatik im Repo.
PFLICHT_AUFGABEN = ("lang", "news", "faktenpruefung", "politur")

# npm-Skripte, die laut Vertrag existieren müssen (T8).
NPM_PFLICHT = ("ki:transportweg", "ki:status", "test:ki")

# Skripte, die ein Modell rufen – sie müssen über den gemeinsamen
# Client gehen (T6). Wer hier etwas hinzufügt, erweitert den Vertrag.
RUFER = (
    "scripts/claude_writer.py",
    "scripts/news_writer.py",
    "scripts/faktenfrische.py",
    "scripts/saisonaler_hero_refresh.py",
)

# Workflows, die ein Sprachmodell rufen → die Aufgabe, die sie bedienen.
# T9 verlangt, dass jeder davon mindestens ZWEI Gratis-Schlüssel
# durchreicht. Ein Workflow mit nur einem Schlüssel ist genau der
# Dauerausfall-Kandidat aus Issue #514: Ist das Kontingent leer, meldet
# die Automatik „übersprungen" und gilt als grün.
SCHLUESSEL_WORKFLOWS = {
    ".github/workflows/saisonaler-hero-refresh.yml": "politur",
    ".github/workflows/faktenfrische.yml": "faktenpruefung",
    ".github/workflows/ki-redaktion.yml": "lang",
    ".github/workflows/content-engine-v2.yml": "news",
}

# Die Brückendatei aus Issue #514 bleibt gelöscht (T5).
GELOESCHTE_BRUECKEN = ("scripts/puter_chat.mjs",)

# ------------------------------------------------------------------
#  DAUERSPERRE FÜR KOSTENPFLICHTIGE WEGE (T1, seit 03.10.2026)
#  Die Namen sind zusammengesetzt, damit diese Erklärdatei nicht selbst
#  auf der Sperrliste landet – das Gate schließt sich ohnehin aus, aber
#  die Absicht soll im Quelltext lesbar sein.
# ------------------------------------------------------------------
PAID_PROVIDER_IDS = ("openai", "claude", "anthropic", "perplexity", "jasper")

_OAI = "OPENAI"
_ANT = "ANTHROPIC"
PAID_SPUREN = (
    (rf"{_OAI}_API_KEY", "kostenpflichtiger OpenAI-Schlüssel"),
    (rf"{_ANT}_API_KEY", "kostenpflichtiger Anthropic-Schlüssel"),
    (r"PERPLEXITY_API_KEY", "kostenpflichtiger Perplexity-Schlüssel"),
    (r"api\.openai\.com", "Endpunkt der kostenpflichtigen OpenAI-API"),
    (r"api\.anthropic\.com", "Endpunkt der kostenpflichtigen Anthropic-API"),
    (r"api\.perplexity\.ai", "Endpunkt der kostenpflichtigen Perplexity-API"),
)


def paid_spuren_in(text: str) -> list[str]:
    """Kostenpflichtige Schlüssel/Endpunkte in einem Text benennen.

    EIN Erkenner für T1 (Code + CI) und T9 (KI-Workflows) – zwei
    Listen würden irgendwann auseinanderlaufen, und die Lücke fiele
    erst mit der Rechnung auf.
    """
    return [klartext for muster, klartext in PAID_SPUREN
            if re.search(muster, text)]


def _quelltexte():
    """Alle Dateien, die T1/T5 prüfen: Skripte und Workflows.

    Dokumentation ist bewusst NICHT dabei – Reports und Runbooks müssen
    erklären dürfen, was entfernt wurde und warum.
    """
    kandidaten = (sorted((ROOT / "scripts").glob("*.py"))
                  + sorted((ROOT / "scripts").glob("*.mjs"))
                  + sorted((ROOT / ".github" / "workflows").glob("*.yml")))
    for pfad in kandidaten:
        if pfad.name == Path(__file__).name:
            continue        # diese Datei benennt die Spuren ja gerade
        try:
            yield pfad, pfad.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

# Spuren verbotener Brücken (T5). Bewusst auf AUSFÜHRBARE Spuren
# geprüft, nicht auf das bloße Wort – die Dokumentation darf die
# Abschaltung ja erklären (scripts/faktenfrische.py tut genau das).
# Geprüft werden Skripte UND Workflows: Der Token-Durchreicher in der
# CI war bei Issue #514 die eigentliche Fehlerquelle. Diese Liste ist
# der Nachfolger der anbieterspezifischen Puter-Sperre (gelöscht am
# 03.10.2026) – sie verbietet die Bauweise, nicht einen Namen.
BRUECKEN_SPUREN = (
    (r"secrets\.PUTER_AUTH_TOKEN", "Puter-Token aus CI-Secrets"),
    (r"@heyputer/puter\.js", "Puter-Browserbrücke als Abhängigkeit"),
    (r"os\.environ(?:\.get)?\(\s*[\"']PUTER_AUTH_TOKEN", "Puter-Token gelesen"),
    (r"environ\[[\"']PUTER_AUTH_TOKEN", "Puter-Token gelesen"),
    (r"(?:chat\.openai\.com|chatgpt\.com)/backend-api",
     "ChatGPT-Web-UI angezapft (verstößt gegen die OpenAI-Bedingungen)"),
    (r"__Secure-next-auth\.session-token",
     "ChatGPT-Sitzungscookie im Code (Konto-Hack)"),
)


# ====================================================================
#  SSOT
# ====================================================================
def lade_ssot(pfad: Path | None = None) -> dict:
    with open(pfad or SSOT, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _anbieter_karte(ssot: dict) -> dict:
    return {a.get("id"): a for a in (ssot.get("anbieter") or [])
            if isinstance(a, dict) and a.get("id")}


def _ketten(ssot: dict) -> dict:
    out = {}
    for aufgabe, block in (ssot.get("routing") or {}).items():
        if isinstance(block, dict):
            out[aufgabe] = list(block.get("kette") or [])
    return out


# ====================================================================
#  VERTRAGSREGELN T1–T8
#  Jede Funktion gibt eine Liste von Befunden zurück. Leer = grün.
# ====================================================================
def t1_kostenregel(ssot: dict) -> list[str]:
    """Es existiert kein kostenpflichtiger Weg – nirgends.

    Verschärft am 03.10.2026 (Auftrag Frank). Vorher galt: Paid darf
    nicht in einer automatischen Kette stehen, bleibt aber als Opt-in
    erlaubt. Das war zu weich. Ein Opt-in, das man vergessen kann, ist
    eine Rechnung, die man vergisst – bis dahin reichten zwei
    nächtliche Workflows klaglos Paid-Schlüssel durch, und zwei
    Anbieter-Reihenfolgen begannen sogar damit.

    Geprüft wird darum an vier Orten: SSOT, Client, Skripte, Workflows.
    """
    befunde = []
    karte = _anbieter_karte(ssot)

    # (a) SSOT: kein Anbieter darf sich als kostenpflichtig deklarieren.
    for pid, a in karte.items():
        if a.get("kostenklasse") != "gratis":
            befunde.append(
                f"T1: Anbieter '{pid}' ist mit kostenklasse "
                f"'{a.get('kostenklasse')}' eingetragen. Die Blog-Automatik "
                "läuft vollständig kostenfrei.")

    # (b) SSOT + Client: kein gesperrter Anbietername taucht wieder auf.
    for pid in karte:
        if pid in PAID_PROVIDER_IDS:
            befunde.append(
                f"T1: '{pid}' ist ein kostenpflichtiger Anbieter und am "
                "03.10.2026 entfernt worden – er gehört nicht zurück in die "
                "SSOT.")
    for pid in llm_client.PROVIDERS:
        if pid in PAID_PROVIDER_IDS:
            befunde.append(
                f"T1: llm_client.PROVIDERS enthält wieder '{pid}'.")
    for aufgabe, kette in _ketten(ssot).items():
        for pid in kette:
            if pid in PAID_PROVIDER_IDS:
                befunde.append(
                    f"T1: Kette '{aufgabe}' enthält den kostenpflichtigen "
                    f"Anbieter '{pid}'.")

    # (c) Skripte + Workflows: keine Paid-Schlüssel, keine Paid-Endpunkte.
    for pfad, text in _quelltexte():
        for klartext in paid_spuren_in(text):
            befunde.append(
                f"T1: {pfad.relative_to(ROOT)} – {klartext}. "
                "Kostenpflichtige Wege sind dauerhaft entfernt "
                "(03.10.2026).")
    return befunde


def t2_nur_implementierte(ssot: dict) -> list[str]:
    """Jeder Anbieter existiert wirklich – in SSOT und im Client."""
    befunde = []
    karte = _anbieter_karte(ssot)
    for pid, a in karte.items():
        if pid not in llm_client.PROVIDERS:
            befunde.append(
                f"T2: Anbieter '{pid}' steht in der SSOT, aber nicht in "
                "llm_client.PROVIDERS – ein Ruf ginge ins Leere.")
            continue
        soll = a.get("kostenklasse")
        ist = llm_client.KOSTENKLASSE.get(pid)
        if soll != ist:
            befunde.append(
                f"T2: Kostenklasse von '{pid}' widerspricht sich: SSOT sagt "
                f"'{soll}', llm_client sagt '{ist}'. Zwei Wahrheiten über "
                "Geld sind eine zu viel.")
    for aufgabe, kette in _ketten(ssot).items():
        for pid in kette:
            if pid not in karte:
                befunde.append(
                    f"T2: Kette '{aufgabe}' zeigt auf '{pid}' – dieser "
                    "Anbieter ist in der SSOT gar nicht beschrieben.")
    return befunde


def t3_redundanz(ssot: dict) -> list[str]:
    """Mindestens zwei Gratis-Glieder je Kette.

    Ein Hoster, der sein Tageskontingent verbraucht hat, darf die
    Produktion nicht anhalten. Genau das ist der Unterschied zwischen
    „wir nutzen ein Gratis-Modell" und einem Betrieb auf Agenturniveau.
    """
    befunde = []
    minimum = int((ssot.get("regeln") or {}).get("mindest_redundanz") or 2)
    karte = _anbieter_karte(ssot)
    for aufgabe, kette in _ketten(ssot).items():
        frei = [p for p in kette
                if (karte.get(p) or {}).get("kostenklasse") == "gratis"]
        if len(frei) < minimum:
            befunde.append(
                f"T3: Kette '{aufgabe}' hat nur {len(frei)} Gratis-Glied(er) "
                f"(Minimum {minimum}). Fällt eines aus, steht die Automatik.")
    return befunde


def t4_openai_bahn(ssot: dict) -> list[str]:
    """Mindestens ein echter OpenAI-Modell-Hoster je Kette.

    Das ist die eingelöste Fassung des Auftrags „ChatGPT einbauen":
    nicht die Oberfläche, sondern OpenAIs Modell – kostenlos, über
    eine dokumentierte API.
    """
    befunde = []
    if not (ssot.get("regeln") or {}).get("openai_bahn_pflicht"):
        return befunde
    karte = _anbieter_karte(ssot)
    for aufgabe, kette in _ketten(ssot).items():
        bahn = [p for p in kette
                if (karte.get(p) or {}).get("bahn") == "openai"
                and (karte.get(p) or {}).get("kostenklasse") == "gratis"]
        if not bahn:
            befunde.append(
                f"T4: Kette '{aufgabe}' enthält keinen kostenlosen "
                "OpenAI-Modell-Hoster (Groq/NVIDIA/Cloudflare).")
    return befunde


def t5_keine_bruecken(_ssot: dict) -> list[str]:
    """Kein UI-Scraping, keine Browser-Brücke, kein Fremdkonto.

    Historie: Issue #514. Eine Brücke über ein geteiltes Fremdkonto
    sieht im Code aus wie eine Integration und ist in Wahrheit ein
    Dauerausfall mit Ansage – dazu ein Verstoß gegen die Nutzungs-
    bedingungen des jeweiligen Anbieters.
    """
    befunde = []
    for rel in GELOESCHTE_BRUECKEN:
        if (ROOT / rel).exists():
            befunde.append(
                f"T5: {rel} ist zurück. Diese Brücke wurde mit Issue #514 "
                "entfernt – der Transportweg ist scripts/llm_client.py.")

    for pfad, text in _quelltexte():
        for muster, klartext in BRUECKEN_SPUREN:
            if re.search(muster, text):
                befunde.append(
                    f"T5: {pfad.relative_to(ROOT)} – {klartext}. "
                    "Transportweg ist immer eine dokumentierte API mit "
                    "eigenem Schlüssel.")
    return befunde


def t6_ein_transportweg(_ssot: dict) -> list[str]:
    """Alle Rufer gehen über scripts/llm_client.py."""
    befunde = []
    for rel in RUFER:
        pfad = ROOT / rel
        if not pfad.exists():
            befunde.append(f"T6: {rel} fehlt – Vertrag zeigt ins Leere.")
            continue
        text = pfad.read_text(encoding="utf-8", errors="ignore")
        if "import llm_client" not in text:
            befunde.append(
                f"T6: {rel} ruft ein Modell, ohne den gemeinsamen Client zu "
                "importieren. Ein zweiter Transportweg heißt: zwei Orte für "
                "Schlüssel, Retries und Kosten.")
    return befunde


def t7_routing_vollstaendig(ssot: dict) -> list[str]:
    befunde = []
    ketten = _ketten(ssot)
    for aufgabe in PFLICHT_AUFGABEN:
        if aufgabe not in ketten:
            befunde.append(
                f"T7: Für die Pflicht-Aufgabe '{aufgabe}' fehlt eine Kette.")
        elif not ketten[aufgabe]:
            befunde.append(f"T7: Kette '{aufgabe}' ist leer.")
    return befunde


def t8_verdrahtung(_ssot: dict) -> list[str]:
    befunde = []
    if not (ROOT / RUNBOOK).exists():
        befunde.append(f"T8: Runbook fehlt: {RUNBOOK}")
    pkg = ROOT / "package.json"
    if pkg.exists():
        try:
            scripts = (json.loads(pkg.read_text(encoding="utf-8"))
                       .get("scripts") or {})
        except (ValueError, OSError):
            scripts = {}
        for name in NPM_PFLICHT:
            if name not in scripts:
                befunde.append(f"T8: npm-Skript '{name}' fehlt in package.json")
    return befunde


def t9_schluessel_durchreichung(ssot: dict) -> list[str]:
    """Jeder KI-Workflow bekommt mindestens zwei Gratis-Schlüssel.

    Das ist die Lehre aus Issue #514 in Vertragsform. Dort lief eine
    Automatik gegen ein Konto, das es nicht gab, und meldete brav
    „übersprungen". Ein Workflow, der nur EINEN Schlüssel durchreicht,
    ist derselbe Fall mit Verzögerung: Sobald das Tageskontingent
    dieses einen Hosters leer ist, produziert die Automatik nichts mehr
    und sieht dabei grün aus.

    Geprüft wird die Durchreichung (`secrets.X`), nicht der Wert – ob
    ein Secret wirklich gesetzt ist, weiß nur GitHub.
    """
    befunde = []
    karte = _anbieter_karte(ssot)
    ketten = _ketten(ssot)

    for rel, aufgabe in SCHLUESSEL_WORKFLOWS.items():
        pfad = ROOT / rel
        if not pfad.exists():
            befunde.append(f"T9: Workflow fehlt: {rel}")
            continue
        text = pfad.read_text(encoding="utf-8", errors="ignore")

        # Welche Anbieter stehen laut SSOT in der Kette dieses Workflows?
        kette = ketten.get(aufgabe) or []
        gratis = [p for p in kette
                  if (karte.get(p) or {}).get("kostenklasse") == "gratis"]

        versorgt = []
        for pid in gratis:
            noetig = (karte.get(pid) or {}).get("schluessel") or []
            if noetig and all(f"secrets.{s}" in text for s in noetig):
                versorgt.append(pid)

        if len(versorgt) < 2:
            fehlt = [p for p in gratis if p not in versorgt]
            befunde.append(
                f"T9: {rel} reicht nur {len(versorgt)} Gratis-Schlüssel durch "
                f"({', '.join(versorgt) or 'keinen'}) – nötig sind zwei. "
                f"Nicht versorgt: {', '.join(fehlt) or '–'}. "
                "Ein leeres Tageskontingent legt sonst die Aufgabe "
                f"'{aufgabe}' still, ohne rot zu werden.")

        # Ein Paid-Schlüssel in einem nächtlichen Workflow ist ein
        # Kostenrisiko, das niemand bemerkt, bis die Rechnung kommt.
        # Die Liste kommt aus der Dauersperre, nicht aus der SSOT: Dort
        # steht seit 03.10.2026 kein kostenpflichtiger Anbieter mehr,
        # und genau deshalb braucht die Prüfung ein eigenes Gedächtnis.
        for klartext in paid_spuren_in(text):
            befunde.append(
                f"T9: {rel} – {klartext}. Ein Zeitplan darf keine "
                "kostenpflichtige API anrufen können.")
    return befunde


def t10_kostensperre(ssot: dict) -> list[str]:
    """Die Geldflächen AUSSERHALB der Textkette müssen verriegelt sein.

    WARUM DIESE REGEL ZUM TRANSPORTWEG GEHÖRT (03.10.2026)
    T1 sichert, dass im LLM-Pfad kein kostenpflichtiger Weg mehr
    EXISTIERT. Zwei Flächen daneben – Vorlese-Stimme und
    Rechtschreibung – blieben bewusst erhalten, weil sie echte Qualität
    liefern und je einen kostenlosen Normalbetrieb haben. Sie wurden
    deshalb nicht gelöscht, sondern verriegelt (data/kostensperre.yaml).

    Ohne diese Regel hinge der Schutz an einer zweiten Wache, die
    niemand aufruft. Zwei Verträge, die voneinander nichts wissen,
    laufen auseinander – und zwar immer in die teure Richtung. T10
    fragt die Kostensperre also aus dieser Richtung ab und meldet
    zusätzlich, wenn eine Fläche offen steht.
    """
    befunde: list[str] = []
    try:
        import kostensperre
    except ImportError:
        return ["T10: scripts/kostensperre.py fehlt – die Geldflächen "
                "außerhalb der Textkette wären ungeschützt."]

    sperr_ssot = kostensperre.lade_ssot()
    for fund in kostensperre.pruefen(sperr_ssot):
        befunde.append(f"T10: {fund}")

    for eintrag in sperr_ssot.get("flaechen", []):
        if not isinstance(eintrag, dict):
            continue
        fid = eintrag.get("id", "")
        if fid and kostensperre.erlaubt(fid, sperr_ssot):
            befunde.append(
                f"T10: Geldfläche `{fid}` ({eintrag.get('name', fid)}) ist "
                "ENTSICHERT. Das darf vorkommen – aber nie unbemerkt. "
                f"Begründung: {eintrag.get('grund', '—')} "
                f"({eintrag.get('datum', 'ohne Datum')}).")
    return befunde


PRUEFER = {
    "T1": t1_kostenregel,
    "T2": t2_nur_implementierte,
    "T3": t3_redundanz,
    "T4": t4_openai_bahn,
    "T5": t5_keine_bruecken,
    "T6": t6_ein_transportweg,
    "T7": t7_routing_vollstaendig,
    "T8": t8_verdrahtung,
    "T9": t9_schluessel_durchreichung,
    "T10": t10_kostensperre,
}


def pruefe_vertrag(ssot: dict) -> dict:
    return {rid: fn(ssot) for rid, fn in PRUEFER.items()}


# ====================================================================
#  BETRIEBSLAGE (Zustand, nicht Vertrag)
# ====================================================================
def lage(ssot: dict) -> dict:
    karte = _anbieter_karte(ssot)
    anbieter = []
    for pid, a in karte.items():
        erreichbar = llm_client.available(pid)
        if a.get("kostenklasse") == "paid":
            zustand = BEREIT if erreichbar else STANDBY
            grund = ("Opt-in-Schlüssel gesetzt (läuft NIE automatisch)"
                     if erreichbar else "kein Schlüssel – korrekt so")
        elif erreichbar:
            zustand, grund = BEREIT, "Schlüssel gesetzt"
        else:
            fehlend = [s for s in (a.get("schluessel") or [])
                       if not (__import__("os").environ.get(s) or "").strip()]
            zustand = STANDBY
            grund = f"kein Schlüssel ({', '.join(fehlend) or '–'})"
        anbieter.append({
            "id": pid,
            "name": a.get("name", pid),
            "modell": a.get("modell", ""),
            "kostenklasse": a.get("kostenklasse", "?"),
            "bahn": a.get("bahn", "?"),
            "kontingent": a.get("kontingent", ""),
            "zustand": zustand,
            "grund": grund,
        })

    gratis_bereit = [a["id"] for a in anbieter
                     if a["kostenklasse"] == "gratis" and a["zustand"] == BEREIT]
    bahn_bereit = [a["id"] for a in anbieter
                   if a["bahn"] == "openai" and a["kostenklasse"] == "gratis"
                   and a["zustand"] == BEREIT]

    ketten = []
    for aufgabe, kette in _ketten(ssot).items():
        aktiv = [p for p in kette if llm_client.available(p)]
        ketten.append({
            "aufgabe": aufgabe,
            "kette": kette,
            "aktiv": aktiv,
            "zustand": BEREIT if aktiv else STANDBY,
        })

    betrieb = ssot.get("betrieb") or {}
    soll = int(betrieb.get("soll_hoster_erreichbar") or 2)
    return {
        "anbieter": anbieter,
        "ketten": ketten,
        "gratis_bereit": gratis_bereit,
        "bahn_bereit": bahn_bereit,
        "soll_hoster": soll,
        "redundanz_erfuellt": len(gratis_bereit) >= soll,
        "offline_modus": not gratis_bereit,
    }


def ping(ssot: dict, timeout: int = 45) -> list[dict]:
    """Echte Live-Probe: ein Satz je erreichbarem Gratis-Anbieter.

    Bewusst NICHT Teil des normalen Laufs – ein Gate darf kein
    Kontingent verbrauchen. Nur für `--ping` und die Wochenwache.
    """
    ergebnis = []
    for a in (ssot.get("anbieter") or []):
        pid = a.get("id")
        if a.get("kostenklasse") != "gratis" or not llm_client.available(pid):
            continue
        antwort = llm_client.chat(
            pid,
            prompt="Antworte mit genau einem Wort: Transportweg",
            system="Du antwortest knapp und auf Deutsch.",
            max_tokens=24, temperature=0.0, timeout=timeout, attempts=1)
        ergebnis.append({
            "id": pid,
            "modell": llm_client.model_for(pid),
            "ok": bool(antwort),
            "antwort": (antwort or "")[:80],
        })
    return ergebnis


# ====================================================================
#  COCKPIT
# ====================================================================
def schreibe_cockpit(befunde: dict, zustand: dict) -> None:
    symbol = {BEREIT: "✅", STANDBY: "⏸", DEFEKT: "❌"}
    heute = datetime.date.today().isoformat()
    gebrochen = [r for r, v in befunde.items() if v]

    z = ["# KI-Transportweg – Status", "",
         f"> Stand: {heute} · SSOT `data/ki_transportweg.yaml` · "
         f"Gate `scripts/ki_transportweg.py` · Runbook `{RUNBOOK}`", "",
         "Ein Modell, mehrere Wege, 0 €. Dieses Cockpit beantwortet die "
         "Frage, die bei Issue #514 niemand stellen konnte: **Läuft die "
         "KI-Automatik gerade wirklich – und worüber?**", ""]

    z += ["## Vertrag T1–T9", ""]
    for rid, titel in REGELN.items():
        if befunde[rid]:
            z.append(f"- ❌ **{rid}** {titel}")
            for b in befunde[rid]:
                z.append(f"  - {b}")
        else:
            z.append(f"- ✅ **{rid}** {titel}")
    z.append("")

    z += ["## Anbieter", "",
          "| Anbieter | Modell | Kosten | Bahn | Kontingent | Zustand |",
          "|---|---|---|---|---|---|"]
    for a in zustand["anbieter"]:
        z.append(f"| {a['name']} | `{a['modell']}` | {a['kostenklasse']} | "
                 f"{a['bahn']} | {a['kontingent']} | "
                 f"{symbol.get(a['zustand'], '?')} {a['grund']} |")
    z.append("")

    z += ["## Routing", "",
          "| Aufgabe | Kette | aktiv |", "|---|---|---|"]
    for k in zustand["ketten"]:
        aktiv = ", ".join(k["aktiv"]) if k["aktiv"] else "– (Offline-Gerüst)"
        z.append(f"| {k['aufgabe']} | {' → '.join(k['kette'])} | {aktiv} |")
    z.append("")

    z += ["## Betriebslage", ""]
    n, soll = len(zustand["gratis_bereit"]), zustand["soll_hoster"]
    if zustand["offline_modus"]:
        z.append("⏸ **Standby** – kein einziger Gratis-Schlüssel gesetzt. "
                 "Die Writer laufen im Offline-Gerüst-Modus. Das ist kein "
                 "Fehler, aber auch kein Betrieb: Es entsteht kein Text.")
    elif n < soll:
        z.append(f"⚠️ **Dünn** – {n} von {soll} Gratis-Hostern erreichbar. "
                 "Fällt dieser eine aus oder ist sein Tageskontingent "
                 "verbraucht, steht die Produktion still.")
    else:
        z.append(f"✅ **Redundant** – {n} Gratis-Hoster erreichbar "
                 f"({', '.join(zustand['gratis_bereit'])}).")
    z.append("")
    z.append(f"OpenAI-Bahn (`openai/gpt-oss-120b`): "
             f"{len(zustand['bahn_bereit'])} von 3 Hostern erreichbar"
             + (f" – {', '.join(zustand['bahn_bereit'])}."
                if zustand["bahn_bereit"] else "."))
    z.append("")

    z += ["## Warum kein ChatGPT-Konto", "",
          "„ChatGPT (Free)\" ist eine Oberfläche ohne Schnittstelle. Sie "
          "lässt sich nicht automatisieren, das Web-UI nachzubauen verstößt "
          "gegen die Nutzungsbedingungen, und GitHub Models – der letzte "
          "offizielle Gratis-Weg zu echten GPT-Modellen – ist seit dem "
          "30.07.2026 abgeschaltet. Was bleibt, ist besser als ein "
          "Konto-Hack: `openai/gpt-oss-120b`, OpenAIs eigenes offenes "
          "Modell, kostenlos bei drei unabhängigen Hostern.", ""]

    if gebrochen:
        z.append(f"> **Vertrag gebrochen:** {', '.join(gebrochen)} – "
                 f"Reparatur nach `{RUNBOOK}`.")
    COCKPIT.write_text("\n".join(z) + "\n", encoding="utf-8")


# ====================================================================
#  SELBSTTEST – das Gate sabotiert sich selbst
# ====================================================================
def selftest() -> list[str]:
    """Positivprobe + Sabotage-Proben. Rückgabe: Liste der Fehler."""
    fehler = []
    try:
        echt = lade_ssot()
    except Exception as e:  # noqa: BLE001
        return [f"SSOT nicht lesbar: {e}"]

    # Positivprobe: Die echte SSOT muss den Vertrag halten.
    for rid, treffer in pruefe_vertrag(echt).items():
        if treffer:
            fehler.append(f"Positivprobe: {rid} meldet am echten Stand: "
                          f"{treffer[0]}")

    def sabotiere(name, mutator, regel):
        kaputt = copy.deepcopy(echt)
        mutator(kaputt)
        if not PRUEFER[regel](kaputt):
            fehler.append(f"Sabotage '{name}': {regel} hat den Defekt NICHT "
                          "bemerkt – die Wache verspricht nur.")

    # ST1: Paid-Anbieter in eine Kette schmuggeln.
    sabotiere("paid in Kette",
              lambda s: s["routing"]["lang"]["kette"].insert(0, "openai"),
              "T1")

    # ST2: Kostenklasse umlügen – SSOT und Client dürfen nie driften.
    def _luege(s):
        for a in s["anbieter"]:
            if a["id"] == "groq":
                a["kostenklasse"] = "paid"
    sabotiere("Kostenklasse driftet", _luege, "T2")

    # ST3: Phantom-Provider in eine Kette setzen.
    sabotiere("Phantom-Provider",
              lambda s: s["routing"]["news"]["kette"].append("chatgpt-free"),
              "T2")

    # ST4: Redundanz auf ein Glied zusammenstreichen.
    sabotiere("Kette auf ein Glied gekürzt",
              lambda s: s["routing"]["lang"].__setitem__("kette", ["groq"]),
              "T3")

    # ST5: OpenAI-Bahn aus einer Kette entfernen.
    sabotiere("OpenAI-Bahn entfernt",
              lambda s: s["routing"]["news"].__setitem__("kette",
                                                         ["gemini", "gemini"]),
              "T4")

    # ST6: Pflicht-Aufgabe löschen.
    sabotiere("Pflicht-Aufgabe gelöscht",
              lambda s: s["routing"].pop("faktenpruefung", None),
              "T7")

    # ST7: Leere Kette.
    sabotiere("Kette geleert",
              lambda s: s["routing"]["politur"].__setitem__("kette", []),
              "T7")

    # ST8a: Workflow versorgt nur noch einen Hoster (Kontingent-Falle).
    def _schluessel_verbiegen(s):
        # Alle Gratis-Hoster bis auf einen aus der Durchreichung nehmen:
        # übrig bleibt ein einziger Weg – genau der Zustand, den T9
        # verbietet.
        for a in s["anbieter"]:
            if a.get("kostenklasse") == "gratis" and a["id"] != "groq":
                a["schluessel"] = [f"NIE_DURCHGEREICHT_{a['id'].upper()}"]
    sabotiere("Workflow unterversorgt", _schluessel_verbiegen, "T9")

    # ST8b: Der Paid-Erkenner selbst muss anschlagen – er ist die
    # gemeinsame Grundlage von T1 (Code/CI) und T9 (Zeitpläne).
    for probe_text, name in (
            ("OPENAI" + "_API_KEY: x", "OpenAI-Schlüssel"),
            ("ANTHROPIC" + "_API_KEY: x", "Anthropic-Schlüssel"),
            ("url = https://api." + "openai.com/v1/chat", "OpenAI-Endpunkt"),
            ("url = https://api." + "anthropic.com/v1/messages",
             "Anthropic-Endpunkt")):
        if not paid_spuren_in(probe_text):
            fehler.append(f"Sabotage '{name}': Der Paid-Erkenner hat die "
                          "Spur nicht gefunden.")
    if paid_spuren_in("GROQ_API_KEY und NVIDIA_API_KEY sind kostenlos"):
        fehler.append("Der Paid-Erkenner meldet Gratis-Schlüssel als "
                      "kostenpflichtig (Fehlalarm).")

    # ST9a: Eine eingeschleuste Paid-Spur im Code muss T1 auslösen.
    paid_probe = ROOT / "scripts" / ".transportweg_paid_probe.py"
    try:
        paid_probe.write_text(
            f'KEY = os.environ.get("{"OPENAI"}_API_KEY")\n', encoding="utf-8")
        if not t1_kostenregel(echt):
            fehler.append("Sabotage 'Paid-Schlüssel eingeschleust': T1 hat "
                          "die Spur im Code nicht gefunden.")
    finally:
        paid_probe.unlink(missing_ok=True)

    # ST9c: T10 muss eine aufgeweichte Kostensperre bemerken.
    #       Geprüft wird an einer KOPIE der SSOT – die echte Datei bleibt
    #       unangetastet, ein Prüf-Aufruf heilt und beschädigt nichts (C15).
    try:
        import tempfile

        import kostensperre
        echte_ssot = kostensperre.SSOT
        with tempfile.TemporaryDirectory(prefix="t10-probe-") as ordner:
            gefaelscht = Path(ordner) / "kostensperre.yaml"
            daten = kostensperre.lade_ssot()
            # Freigabe ohne Begründung: muss als Versehen abgelehnt werden.
            if daten.get("flaechen"):
                daten["flaechen"][0]["freigegeben"] = True
                daten["flaechen"][0].pop("grund", None)
                daten["flaechen"][0].pop("datum", None)
            gefaelscht.write_text(yaml.safe_dump(daten, allow_unicode=True),
                                  encoding="utf-8")
            kostensperre.SSOT = gefaelscht
            try:
                if not t10_kostensperre(echt):
                    fehler.append("Sabotage 'Kostensperre aufgeweicht': T10 "
                                  "hat die unbegründete Freigabe nicht "
                                  "bemerkt.")
            finally:
                kostensperre.SSOT = echte_ssot
    except ImportError:
        fehler.append("Sabotage 'Kostensperre': scripts/kostensperre.py "
                      "nicht importierbar.")

    # ST9b: Die Brücken-Erkennung muss auf einer Probe anschlagen.
    probe = ROOT / "scripts" / ".transportweg_sabotage_probe.py"
    try:
        # Literal bewusst zusammengesetzt: Sonst fände die eigene
        # Sperrliste (T5) diese Zeile und meldete das Gate als Defekt.
        spur = "PUTER" + "_AUTH_TOKEN"
        probe.write_text(f'TOK = os.environ.get("{spur}")\n',
                         encoding="utf-8")
        if not t5_keine_bruecken(echt):
            fehler.append("Sabotage 'Brücke eingeschleust': T5 hat die Spur "
                          "nicht gefunden.")
    finally:
        probe.unlink(missing_ok=True)

    # ST9: Kostenklassen-Karte und Client müssen deckungsgleich bleiben.
    for a in (echt.get("anbieter") or []):
        pid = a.get("id")
        if llm_client.KOSTENKLASSE.get(pid) != a.get("kostenklasse"):
            fehler.append(f"Kostenklasse '{pid}' driftet zwischen SSOT und "
                          "llm_client.")

    # ST10: Die OpenAI-Bahn der SSOT muss der des Clients entsprechen.
    bahn_ssot = {a["id"] for a in (echt.get("anbieter") or [])
                 if a.get("bahn") == "openai" and a.get("kostenklasse") == "gratis"}
    if bahn_ssot != set(llm_client.OPENAI_BAHN):
        fehler.append(f"OpenAI-Bahn driftet: SSOT {sorted(bahn_ssot)} vs. "
                      f"llm_client {sorted(llm_client.OPENAI_BAHN)}.")

    return fehler


# ====================================================================
#  CLI
# ====================================================================
def main() -> int:
    ap = argparse.ArgumentParser(
        description="KI-Transportweg: Vertrag T1–T9 + Betriebslage "
                    "(ein Modell, mehrere Wege, 0 €)")
    ap.add_argument("--status", action="store_true",
                    help="nur die Betriebslage zeigen (kein Vertragsurteil)")
    ap.add_argument("--json", action="store_true", help="maschinenlesbar")
    ap.add_argument("--selftest", action="store_true",
                    help="Positivprobe + Sabotage-Proben (Exit 2 = defekt)")
    ap.add_argument("--ping", action="store_true",
                    help="echte Live-Probe je Gratis-Anbieter (kostet "
                         "Kontingent)")
    ap.add_argument("--strict", action="store_true",
                    help="Standby wird rot (für die Wochenwache)")
    ap.add_argument("--no-cockpit", action="store_true",
                    help="KI-TRANSPORTWEG-STATUS.md nicht schreiben")
    args = ap.parse_args()

    if args.selftest:
        fehler = selftest()
        if fehler:
            print("❌ Transportweg-Selbsttest fehlgeschlagen:")
            for f in fehler:
                print(f"   · {f}")
            return 2
        print("✅ Transportweg-Selbsttest grün "
              "(Positivprobe + 16 Sabotage-Proben + 2 Driftproben).")
        return 0

    try:
        ssot = lade_ssot()
    except Exception as e:  # noqa: BLE001
        print(f"::error::SSOT data/ki_transportweg.yaml nicht lesbar: {e}")
        return 2

    zustand = lage(ssot)

    if args.ping:
        print("Live-Probe (verbraucht Kontingent):")
        proben = ping(ssot)
        if not proben:
            print("  ⏸ Kein Gratis-Schlüssel gesetzt – nichts zu prüfen.")
        for p in proben:
            print(f"  {'✅' if p['ok'] else '❌'} {p['id']:<10} "
                  f"{p['modell']:<26} {p['antwort'] or 'keine Antwort'}")
        if proben and not any(p["ok"] for p in proben):
            print("::error::Kein einziger Gratis-Hoster antwortet.")
            return 1
        return 0

    befunde = pruefe_vertrag(ssot)
    if not args.no_cockpit:
        schreibe_cockpit(befunde, zustand)

    gebrochen = {r: v for r, v in befunde.items() if v}

    if args.json:
        print(json.dumps({"vertrag": befunde, "lage": zustand,
                          "gebrochen": sorted(gebrochen)},
                         ensure_ascii=False, indent=2))
    else:
        symbol = {BEREIT: "✅", STANDBY: "⏸", DEFEKT: "❌"}
        if not args.status:
            print("KI-Transportweg – Vertrag T1–T9\n")
            for rid, titel in REGELN.items():
                if befunde[rid]:
                    print(f"  ❌ {rid}  {titel}")
                    for b in befunde[rid]:
                        print(f"        {b}")
                else:
                    print(f"  ✅ {rid}  {titel}")
            print()
        print("Anbieter:")
        for a in zustand["anbieter"]:
            print(f"  {symbol.get(a['zustand'], '?')} {a['id']:<10} "
                  f"{a['kostenklasse']:<7} {a['modell']:<26} {a['grund']}")
        print("\nRouting:")
        for k in zustand["ketten"]:
            aktiv = ", ".join(k["aktiv"]) or "– (Offline-Gerüst)"
            print(f"  {symbol.get(k['zustand'], '?')} {k['aufgabe']:<15} "
                  f"{' → '.join(k['kette']):<40} aktiv: {aktiv}")
        n, soll = len(zustand["gratis_bereit"]), zustand["soll_hoster"]
        print()
        if zustand["offline_modus"]:
            print("  ⏸ Standby: kein Gratis-Schlüssel gesetzt – die Writer "
                  "erzeugen nur Offline-Gerüste.")
            print(f"     Nachrüsten (je 0 €): {RUNBOOK}")
        elif n < soll:
            print(f"  ⚠️ Nur {n} von {soll} Gratis-Hostern erreichbar – "
                  "ein Ausfall hält die Produktion an.")
        else:
            print(f"  ✅ {n} Gratis-Hoster erreichbar: "
                  f"{', '.join(zustand['gratis_bereit'])}")
        if not args.no_cockpit:
            print(f"\nCockpit geschrieben: {COCKPIT.name}")

    if gebrochen:
        print(f"\n::error::Transportweg-Vertrag gebrochen: "
              f"{', '.join(sorted(gebrochen))}")
        return 1
    if args.strict and zustand["offline_modus"]:
        print("\n::error::--strict: kein einziger Gratis-Hoster erreichbar.")
        return 1
    if args.strict and not zustand["redundanz_erfuellt"]:
        print(f"\n::error::--strict: nur {len(zustand['gratis_bereit'])} "
              f"von {zustand['soll_hoster']} Gratis-Hostern erreichbar.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
