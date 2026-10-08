#!/usr/bin/env python3
# ============================================================
#  ANTWORTWERK – die kostenlose Antwortmaschine des Hauses
#  ------------------------------------------------------------
#  AUFTRAG (Frank, 03.10.2026): „Eine kostenlose Alternative für
#  Perplexity einbauen, die gleichwertig oder besser ist.“
#
#  WAS ES TUT
#    Frage rein → belegte Antwort raus. Vier Schritte:
#      1. SUCHEN       SearXNG (selbst gehostet) → DuckDuckGo → Themenpool
#      2. LESEN        Crawl4AI holt den VOLLTEXT, nicht den Schnipsel
#      3. SYNTHESE     extraktiv (Standard, ohne Schlüssel) oder
#                      Gratis-LLM (Groq/Gemini), streng an die Belege gebunden
#      4. BELEGEN      Domain-Disziplin + optionaler Browser-Beweis
#
#  WARUM DAS BESSER IST ALS PERPLEXITY
#    · Volltext statt Snippet: Crawl4AI liest die ganze Seite.
#    · Beleg-PRÜFUNG: Playwright rendert die zitierte Seite und schaut
#      nach, ob sie die Aussage überhaupt trägt. Perplexity listet
#      Quellen – es prüft sie nicht.
#    · Domain-Disziplin: Affiliate-Partner sind nie belegfähig. Eine
#      Antwortmaschine, die CHECK24 als Faktenquelle zitiert, ist für
#      diesen Blog wertlos.
#    · Ohne Schlüssel läuft der extraktive Modus: wörtliche Zitate,
#      keine Halluzination, reproduzierbar.
#    · Kosten: 0 €. Keine Abfragegebühr, kein Abo, kein Limit.
#
#  LEITPLANKEN
#    · NUR LESEN. Dieses Skript postet nichts und ändert keinen Artikel.
#    · Das Dossier ist ein Signal-Pool für Menschen. Faktenübernahme in
#      Artikel läuft über scripts/faktenfrische.py und dessen
#      Anti-Halluzinations-Vertrag – nicht von hier aus.
#    · --selftest läuft offline, ohne einen einzigen Netzaufruf.
#
#  AUFRUF
#    python3 scripts/antwortwerk.py --frage "Wie hoch ist ...?"
#    python3 scripts/antwortwerk.py --plan            # fällige Fragen
#    python3 scripts/antwortwerk.py --plan --dry-run  # nur zeigen
#    python3 scripts/antwortwerk.py --status          # Lage der Gewerke
#    python3 scripts/antwortwerk.py --selftest        # offline, fail-closed
#
#  Exit: 0 = Antwort(en) erzeugt oder nichts fällig, 2 = Fehler,
#        3 = keine Quelle erreichbar (CI warnt, bricht nicht ab).
# ============================================================
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import urllib.request
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import werkbank_adapters as wa  # noqa: E402
import llm_client  # noqa: E402 – einziger Modell-Transportweg

ROOT = wa.ROOT
AUSGABE_DIR = ROOT / "data" / "werkbank" / "antworten"
STATE_PFAD = ROOT / "data" / "werkbank" / "antwortwerk_state.json"

# Satzende-Erkennung, die an deutschen Abkürzungen und Zahlen nicht zerbricht.
_SATZ = re.compile(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ])")
_WORT = re.compile(r"[A-Za-zÄÖÜäöüß]{4,}")

# Füllwörter, die keine Relevanz anzeigen.
_STOPP = {
    "oder", "und", "aber", "dass", "diese", "dieser", "dieses", "eine", "einen",
    "einer", "eines", "nicht", "auch", "noch", "schon", "wenn", "dann", "wird",
    "werden", "wurde", "sind", "sein", "haben", "hatte", "kann", "können",
    "muss", "müssen", "soll", "sollen", "sich", "nach", "über", "unter", "beim",
    "durch", "gegen", "ohne", "mehr", "sehr", "aktuell", "deutschland",
    "welche", "wieviel", "wie", "was", "warum", "wann",
}


# ---------------------------------------------------------------- Hilfen
def heute() -> dt.date:
    return dt.date.today()


def begriffe_aus(frage: str) -> list[str]:
    """Inhaltstragende Begriffe einer Frage, kleingeschrieben, ohne Dubletten."""
    gesehen: list[str] = []
    for w in _WORT.findall(frage.lower()):
        if w not in _STOPP and w not in gesehen:
            gesehen.append(w)
    return gesehen


def lade_allowlist(ssot: dict) -> dict:
    """Belegfähige Domains – dieselbe SSOT wie die Faktenfrische (B9)."""
    import yaml

    quelle = ((ssot.get("antwortwerk") or {}).get("belege") or {}).get(
        "allowlist_quelle", "data/agent_reach/faktenfrische.yaml")
    pfad = ROOT / quelle
    index: dict[str, dict] = {}
    try:
        daten = yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001 – fehlende Allowlist = nichts ist belegfähig
        return index
    for eintrag in daten.get("quellen_allowlist") or []:
        dom = (eintrag.get("domain") or "").lower().lstrip(".")
        if dom:
            index[dom] = {"herausgeber": eintrag.get("herausgeber", dom),
                          "rang": int(eintrag.get("rang", 3))}
    return index


def belegfaehig(url: str, allowlist: dict, sperrliste: list[str]) -> dict | None:
    """Darf diese URL als Beleg dienen? Sperrliste schlägt Allowlist."""
    dom = wa.domain_von(url)
    if not dom:
        return None
    for gesperrt in sperrliste:
        g = gesperrt.lower().lstrip(".")
        if dom == g or dom.endswith("." + g):
            return None
    for erlaubt, meta in allowlist.items():
        if dom == erlaubt or dom.endswith("." + erlaubt):
            return {"domain": dom, **meta}
    return None


# ------------------------------------------------------- Passagen bewerten
def passagen(text: str, begriffe: list[str], max_saetze: int = 4) -> list[dict]:
    """Die aussagekräftigsten Sätze einer Seite, nach Begriffsdeckung.

    Bewusst schlicht und deterministisch: Wer nachvollziehen will, warum
    ein Satz im Dossier steht, soll das in zehn Sekunden können.
    """
    roh = re.sub(r"\s+", " ", text or "").strip()
    if not roh:
        return []
    treffer: list[dict] = []
    for satz in _SATZ.split(roh):
        satz = satz.strip(" -•·|")
        # Zu kurz = Navigationsrest, zu lang = unzitierbarer Absatzklumpen.
        if not (60 <= len(satz) <= 400):
            continue
        klein = satz.lower()
        deckung = sum(1 for b in begriffe if b in klein)
        if not deckung:
            continue
        # Zahlen sind in einem Finanzblog das Wertvollste an einem Satz.
        zahlen = len(re.findall(r"\d", satz))
        punkte = deckung * 10 + min(zahlen, 12)
        treffer.append({"satz": satz, "punkte": punkte, "deckung": deckung})
    treffer.sort(key=lambda t: t["punkte"], reverse=True)
    return treffer[:max_saetze]


# ------------------------------------------------------------- Synthese
def synthese_extraktiv(frage: str, belege: list[dict]) -> dict:
    """Standardweg ohne Schlüssel: Antwort aus wörtlichen Passagen.

    Kann per Konstruktion nicht halluzinieren – jeder Satz der Antwort
    steht so auf einer belegfähigen Seite und trägt seine Fundstelle.
    """
    if not belege:
        return {"weg": "extraktiv", "text": "", "aussagen": [],
                "hinweis": "Keine belegfähige Fundstelle."}
    aussagen = []
    for nummer, beleg in enumerate(belege, start=1):
        for p in beleg["passagen"]:
            aussagen.append({"satz": p["satz"], "beleg": nummer,
                             "punkte": p["punkte"]})
    aussagen.sort(key=lambda a: a["punkte"], reverse=True)
    aussagen = aussagen[:8]
    zeilen = [f"- {a['satz']} [{a['beleg']}]" for a in aussagen]
    return {
        "weg": "extraktiv",
        "text": "\n".join(zeilen),
        "aussagen": aussagen,
        "hinweis": "Wörtliche Passagen, nach Relevanz geordnet. Keine Umformulierung.",
    }


def _llm_prompt(frage: str, belege: list[dict]) -> str:
    """Streng gebundener Prompt: Nur das Material, nichts aus dem Gedächtnis."""
    bloecke = []
    for nummer, b in enumerate(belege, start=1):
        text = " ".join(p["satz"] for p in b["passagen"])
        bloecke.append(f"[{nummer}] {b['herausgeber']} – {b['url']}\n{text}")
    material = "\n\n".join(bloecke)
    return (
        "Du bist Faktenassistent für einen deutschen Verbraucher-Finanzblog.\n"
        "Beantworte die Frage AUSSCHLIESSLICH aus dem folgenden Material.\n"
        "Regeln, die du nicht brechen darfst:\n"
        "1. Kein Wissen aus deinem Gedächtnis. Steht es nicht im Material, "
        "schreibst du: 'Das Material deckt diesen Punkt nicht ab.'\n"
        "2. Jede Aussage endet mit der Belegnummer in eckigen Klammern, z. B. [2].\n"
        "3. Keine Empfehlung, keine Werbung, kein Anbietername als Tipp.\n"
        "4. Höchstens 150 Wörter, nüchterner Ton, Sie-Form vermeiden "
        "(der Blog duzt).\n\n"
        f"FRAGE: {frage}\n\nMATERIAL:\n{material}\n"
    )


def _synthese_llm(provider: str, frage: str, belege: list[dict],
                  anbieter: dict, timeout: int) -> dict | None:
    """LLM-Synthese über den zentralen Transport – Belege bleiben Pflicht."""
    if not belege or not llm_client.available(provider):
        return None
    try:
        text = llm_client.chat(
            provider, prompt=_llm_prompt(frage, belege),
            model=anbieter.get("modell"), temperature=0.1,
            max_tokens=600, timeout=timeout, attempts=2,
        )
    except Exception as exc:  # noqa: BLE001 – LLM-Ausfall ist kein Laufabbruch
        return {"weg": provider, "text": "",
                "fehler": f"{type(exc).__name__}: {exc}"}
    if not text:
        return {"weg": provider, "text": "", "fehler": "keine Antwort"}
    hinweis = ("Freier Groq-Zugang, streng an die Belege gebunden."
               if provider == "groq" else
               "Freier Gemini-Zugang, streng an die Belege gebunden.")
    return {"weg": provider, "text": text, "hinweis": hinweis}


def synthese_groq(frage: str, belege: list[dict], anbieter: dict, timeout: int) -> dict | None:
    return _synthese_llm("groq", frage, belege, anbieter, timeout)


def synthese_gemini(frage: str, belege: list[dict], anbieter: dict, timeout: int) -> dict | None:
    return _synthese_llm("gemini", frage, belege, anbieter, timeout)

def synthetisiere(frage: str, belege: list[dict], ssot: dict) -> dict:
    """Extraktiv ist Pflicht, LLM ist Kür. Beides landet im Dossier."""
    budget = (ssot.get("antwortwerk") or {}).get("budget") or {}
    timeout = int(budget.get("timeout_sekunden", 30))
    basis = synthese_extraktiv(frage, belege)
    for anbieter in (ssot.get("antwortwerk") or {}).get("synthese") or []:
        if not anbieter.get("schluessel_noetig"):
            continue
        fn = {"groq": synthese_groq, "gemini": synthese_gemini}.get(anbieter.get("id"))
        if not fn:
            continue
        ergebnis = fn(frage, belege, anbieter, timeout)
        if ergebnis and ergebnis.get("text"):
            ergebnis["beleglage"] = basis
            return ergebnis
    return basis


# ----------------------------------------------------------- Hauptlauf
def beantworte(frage: str, ssot: dict, mit_browser: bool = True,
               offline: bool = False) -> dict:
    """Ein voller Durchlauf: suchen → lesen → belegen → synthetisieren."""
    budget = (ssot.get("antwortwerk") or {}).get("budget") or {}
    beleg_cfg = (ssot.get("antwortwerk") or {}).get("belege") or {}
    sperrliste = beleg_cfg.get("sperrliste") or []
    allowlist = lade_allowlist(ssot)
    begriffe = begriffe_aus(frage)

    ergebnis: dict = {
        "frage": frage, "zeitpunkt": wa.jetzt_iso(), "abrufdatum": heute().isoformat(),
        "begriffe": begriffe, "suche": {}, "belege": [], "verworfen": [],
        "antwort": {}, "browser_beweis": [],
    }

    if offline:
        ergebnis["suche"] = {"anbieter": None, "versuche": [
            {"anbieter": "-", "ergebnis": "offline", "hinweis": "--offline gesetzt"}]}
        ergebnis["antwort"] = synthese_extraktiv(frage, [])
        return ergebnis

    # --- 1. Suchen ---------------------------------------------------
    treffer_lage = wa.suche(frage, ssot)
    ergebnis["suche"] = {"anbieter": treffer_lage["anbieter"],
                         "versuche": treffer_lage["versuche"],
                         "anzahl": len(treffer_lage["treffer"])}
    if not treffer_lage["treffer"]:
        ergebnis["antwort"] = synthese_extraktiv(frage, [])
        return ergebnis

    # --- 2. Vorfiltern: nur belegfähige Domains lesen -----------------
    # Spart Lesezeit und verhindert, dass Werbeseiten überhaupt ins
    # Material geraten. Das ist der entscheidende Unterschied zu einer
    # generischen Antwortmaschine.
    kandidaten: list[dict] = []
    for t in treffer_lage["treffer"]:
        meta = belegfaehig(t["url"], allowlist, sperrliste)
        if meta:
            kandidaten.append({**t, **meta})
        else:
            ergebnis["verworfen"].append(
                {"url": t["url"], "grund": "nicht belegfähig (Sperrliste/Allowlist)"})
    # Amtliche Quellen zuerst lesen (Rang 1 vor Rang 3).
    kandidaten.sort(key=lambda k: k.get("rang", 3))
    kandidaten = kandidaten[: int(budget.get("max_seiten_lesen", 5))]

    if not kandidaten:
        ergebnis["antwort"] = synthese_extraktiv(frage, [])
        return ergebnis

    # --- 3. Lesen (Crawl4AI → Jina → urllib) --------------------------
    gelesen = wa.lies([k["url"] for k in kandidaten], ssot)

    for k in kandidaten:
        inhalt = gelesen.get(k["url"]) or {}
        if not inhalt.get("text"):
            ergebnis["verworfen"].append(
                {"url": k["url"], "grund": inhalt.get("fehler", "nicht lesbar")})
            continue
        gefunden = passagen(inhalt["text"], begriffe)
        if not gefunden:
            ergebnis["verworfen"].append(
                {"url": k["url"], "grund": "keine Passage mit Bezug zur Frage"})
            continue
        ergebnis["belege"].append({
            "url": k["url"], "titel": k.get("titel", ""), "domain": k["domain"],
            "herausgeber": k["herausgeber"], "rang": k["rang"],
            "leseweg": inhalt.get("weg", "?"), "abgerufen_am": heute().isoformat(),
            "passagen": gefunden,
        })

    ergebnis["belege"] = ergebnis["belege"][: int(budget.get("max_belege_antwort", 6))]

    # --- 4. Browser-Beweis: trägt die Quelle die Aussage? -------------
    if mit_browser and (beleg_cfg.get("browser_beweis") or {}).get("aktiv"):
        for beleg in ergebnis["belege"]:
            beweis = wa.browser_beweis(beleg["url"], ssot, begriffe[:3])
            ergebnis["browser_beweis"].append(beweis)
            beleg["browser_belegt"] = beweis.get("belegt")

    ergebnis["antwort"] = synthetisiere(frage, ergebnis["belege"], ssot)
    return ergebnis


# ------------------------------------------------------------- Dossier
def dossier_schreiben(lauf: dict, ssot: dict) -> Path:
    """Ein Dossier je Frage: Markdown zum Lesen, JSON zum Weiterverarbeiten."""
    AUSGABE_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", lauf["frage"].lower()[:60]).strip("-") or "frage"
    basis = AUSGABE_DIR / f"{heute().isoformat()}-{slug}"

    z: list[str] = [
        f"# {lauf['frage']}",
        "",
        f"> Antwortwerk-Dossier vom {lauf['abrufdatum']}, erzeugt von",
        "> `scripts/antwortwerk.py` (kostenlose Antwortmaschine des Hauses).",
        "> **Status: Signalsammlung.** Nichts hier ist redaktionell freigegeben.",
        "> Faktenübernahme in Artikel läuft über `scripts/faktenfrische.py`.",
        "",
    ]

    antwort = lauf.get("antwort") or {}
    z += ["## Antwort", ""]
    if antwort.get("text"):
        z += [antwort["text"], "",
              f"*Syntheseweg: {antwort.get('weg', '?')} – "
              f"{antwort.get('hinweis', '')}*", ""]
    else:
        z += ["Keine belegfähige Fundstelle. Die Frage bleibt offen – das ist",
              "ein ehrliches Ergebnis, kein Fehler.", ""]

    if antwort.get("weg") in {"groq", "gemini"} and antwort.get("beleglage", {}).get("text"):
        z += ["<details><summary>Extraktive Beleglage (wörtliche Passagen)</summary>", "",
              antwort["beleglage"]["text"], "", "</details>", ""]

    z += ["## Belege", ""]
    if lauf["belege"]:
        for nummer, b in enumerate(lauf["belege"], start=1):
            beweis = {True: "✅ im Browser bestätigt", False: "⚠ Begriff nicht gefunden",
                      None: "—"}.get(b.get("browser_belegt"), "—")
            z += [f"**[{nummer}] {b['herausgeber']}** · Rang {b['rang']} · "
                  f"gelesen via `{b['leseweg']}` · Browser-Beweis: {beweis}",
                  "",
                  f"<{b['url']}> (abgerufen am {b['abgerufen_am']})", ""]
            for p in b["passagen"]:
                z += [f"> {p['satz']}", ""]
    else:
        z += ["Keine. Siehe „Verworfen“ – meist, weil die Treffer nicht auf der",
              "Beleg-Allowlist stehen.", ""]

    z += ["## Suchlage", ""]
    for v in lauf["suche"].get("versuche", []):
        z += [f"- `{v['anbieter']}` → **{v['ergebnis']}** ({v['hinweis']})"]
    z += [""]

    if lauf["verworfen"]:
        z += ["## Verworfen", ""]
        for v in lauf["verworfen"][:15]:
            z += [f"- {v['url']} – {v['grund']}"]
        z += [""]

    z += ["---", "",
          "*Kosten dieses Dossiers: 0 €. Suche über selbst gehostetes SearXNG bzw.*",
          "*schlüsselfreie Rückfallebenen, Lektüre über Crawl4AI, Beleg-Prüfung*",
          "*über Playwright. Siehe `docs/ANLEITUNG-WERKBANK.md`.*"]

    basis.with_suffix(".md").write_text("\n".join(z) + "\n", encoding="utf-8")
    basis.with_suffix(".json").write_text(
        json.dumps(lauf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return basis.with_suffix(".md")


# ----------------------------------------------------------- Fragenplan
def lade_state() -> dict:
    try:
        return json.loads(STATE_PFAD.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def speichere_state(state: dict) -> None:
    STATE_PFAD.parent.mkdir(parents=True, exist_ok=True)
    STATE_PFAD.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")


def faellige_fragen(ssot: dict, state: dict, stichtag: dt.date | None = None) -> list[dict]:
    """Welche Fragen sind nach ihrem Takt wieder dran?"""
    stichtag = stichtag or heute()
    faellig = []
    for f in ssot.get("fragen") or []:
        letzter = (state.get(f["id"]) or {}).get("zuletzt")
        if not letzter:
            faellig.append({**f, "grund": "noch nie beantwortet"})
            continue
        try:
            datum = dt.date.fromisoformat(letzter)
        except ValueError:
            faellig.append({**f, "grund": "Zustand unlesbar"})
            continue
        alter = (stichtag - datum).days
        takt = int(f.get("takt_tage", 90))
        if alter >= takt:
            faellig.append({**f, "grund": f"{alter} Tage alt (Takt {takt})"})
    return faellig


# ------------------------------------------------------------ Selbsttest
def selftest() -> list[str]:
    """Offline, fail-closed. Jede Regel hat eine Sabotage-Probe."""
    fehler: list[str] = []

    def pruefe(name: str, bedingung: bool, hinweis: str = "") -> None:
        if not bedingung:
            fehler.append(f"{name}: {hinweis}")

    ssot = wa.lade_ssot()

    # ST1 – SSOT trägt die vier Gewerke.
    ids = {g.get("id") for g in ssot.get("gewerke") or []}
    pruefe("ST1", ids == {"antwortwerk", "leser", "browser", "konnektor"},
           f"Gewerke unvollständig: {sorted(ids)}")

    # ST2 – Kein Suchanbieter und kein Standard-Syntheseweg kostet Geld.
    aw = ssot.get("antwortwerk") or {}
    pruefe("ST2", all(not a.get("kostenpflichtig") for a in aw.get("suche") or []),
           "kostenpflichtiger Suchanbieter im Vertrag")
    pruefe("ST2b", all(not s.get("kostenpflichtig") for s in aw.get("synthese") or []),
           "kostenpflichtiger Syntheseweg im Vertrag")

    # ST3 – Es gibt genau einen schlüsselfreien Standard-Syntheseweg.
    standard = [s for s in aw.get("synthese") or [] if s.get("standard")]
    pruefe("ST3", len(standard) == 1 and not standard[0].get("schluessel_noetig"),
           "Standard-Synthese fehlt oder braucht einen Schlüssel")

    # ST4 – Sperrliste greift VOR der Allowlist (Sabotage: Partner einschleusen).
    allowlist = {"test.de": {"herausgeber": "Stiftung Warentest", "rang": 2},
                 "check24.de": {"herausgeber": "CHECK24", "rang": 3}}
    sperre = (aw.get("belege") or {}).get("sperrliste") or []
    pruefe("ST4", belegfaehig("https://www.check24.de/strom/", allowlist, sperre) is None,
           "Affiliate-Partner wurde als Beleg zugelassen")
    pruefe("ST4b", belegfaehig("https://www.test.de/strom", allowlist, sperre) is not None,
           "legitime Quelle wurde abgelehnt")

    # ST5 – Kein Selbstbeleg (Zirkelschluss).
    pruefe("ST5",
           belegfaehig("https://franksfinanzcheck.de/strom/", allowlist, sperre) is None,
           "eigene Domain als Beleg zugelassen")

    # ST6 – Subdomains werden mitgesperrt bzw. miterlaubt.
    pruefe("ST6", belegfaehig("https://m.check24.de/x", allowlist, sperre) is None,
           "Subdomain eines Partners nicht gesperrt")

    # ST7 – Extraktive Synthese erfindet nichts: ohne Belege kein Text.
    leer = synthese_extraktiv("Testfrage", [])
    pruefe("ST7", leer["text"] == "" and leer["aussagen"] == [],
           "extraktive Synthese erzeugt Text ohne Belege")

    # ST8 – Extraktive Synthese zitiert wörtlich, nie umformuliert.
    probe_satz = ("Der durchschnittliche Strompreis lag im Jahr 2026 bei "
                  "41,5 Cent je Kilowattstunde für Haushaltskunden.")
    belege = [{"url": "https://www.test.de/x", "herausgeber": "Stiftung Warentest",
               "rang": 2, "passagen": [{"satz": probe_satz, "punkte": 30}]}]
    erg = synthese_extraktiv("Wie hoch ist der Strompreis?", belege)
    pruefe("ST8", probe_satz in erg["text"] and erg["text"].endswith("[1]"),
           "extraktive Synthese zitiert nicht wörtlich mit Belegnummer")

    # ST9 – Passagen-Auswahl ignoriert Sätze ohne Bezug zur Frage.
    text = ("Cookie-Hinweis akzeptieren. " + probe_satz +
            " Impressum und Datenschutz finden Sie hier.")
    p = passagen(text, begriffe_aus("Wie hoch ist der Strompreis 2026?"))
    pruefe("ST9", len(p) == 1 and "Strompreis" in p[0]["satz"],
           f"Passagen-Filter unsauber: {p}")

    # ST10 – verfuegbar()-Prüfungen machen keinen Netzaufruf.
    # Sabotage-Probe: urlopen wird verboten; Statusabfrage muss trotzdem laufen.
    original = urllib.request.urlopen

    def verboten(*_a, **_k):  # noqa: ANN002, ANN003
        raise AssertionError("Netzaufruf im Statuspfad")

    urllib.request.urlopen = verboten  # type: ignore[assignment]
    try:
        wa.gesamtlage(ssot)
    except AssertionError as exc:
        fehler.append(f"ST10: {exc}")
    except Exception as exc:  # noqa: BLE001
        fehler.append(f"ST10: Statuspfad wirft ({type(exc).__name__}: {exc})")
    finally:
        urllib.request.urlopen = original  # type: ignore[assignment]

    # ST11 – Fälligkeitsrechnung: frisch beantwortet = nicht fällig.
    fragen = ssot.get("fragen") or []
    if fragen:
        fid = fragen[0]["id"]
        state = {fid: {"zuletzt": heute().isoformat()}}
        offen = {f["id"] for f in faellige_fragen(ssot, state)}
        pruefe("ST11", fid not in offen, "frisch beantwortete Frage gilt als fällig")
        alt = (heute() - dt.timedelta(days=400)).isoformat()
        offen2 = {f["id"] for f in faellige_fragen(ssot, {fid: {"zuletzt": alt}})}
        pruefe("ST11b", fid in offen2, "überfällige Frage wird nicht erkannt")

    # ST12 – Offline-Lauf erzeugt niemals Belege.
    ol = beantworte("Testfrage ohne Netz", ssot, mit_browser=False, offline=True)
    pruefe("ST12", ol["belege"] == [] and ol["antwort"]["text"] == "",
           "Offline-Lauf erfindet Belege")

    # ST13 – Der Konnektor ist das einzige schreibende Gewerk.
    schreibend = {g["id"] for g in ssot.get("gewerke") or [] if g.get("schreibend")}
    pruefe("ST13", schreibend == {"konnektor"},
           f"Schreibrecht falsch verteilt: {sorted(schreibend)}")

    # ST14 – Nicht freigegebene Konnektor-Aktion wird verweigert.
    verweigert = wa.konnektor_ausfuehren("GITHUB_CREATE_AN_ISSUE", {}, ssot, trocken=False)
    pruefe("ST14", verweigert["zustand"] == "verweigert",
           f"nicht freigegebene Aktion nicht blockiert: {verweigert['zustand']}")

    # ST15 – In der SSOT steht kein Geheimnis, nur ENV-Namen (B6).
    roh = (ROOT / "data" / "werkbank.yaml").read_text(encoding="utf-8")
    verdacht = re.findall(r"(?:sk-|gsk_|ak_|pplx-)[A-Za-z0-9_\-]{12,}", roh)
    pruefe("ST15", not verdacht, f"Schlüsselverdacht in der SSOT: {verdacht}")

    return fehler


# ------------------------------------------------------------------ CLI
def main() -> int:
    ap = argparse.ArgumentParser(
        description="Antwortwerk – kostenlose Antwortmaschine mit Belegpflicht")
    ap.add_argument("--frage", help="Einzelne Frage beantworten")
    ap.add_argument("--plan", action="store_true", help="Fällige Fragen aus der SSOT")
    ap.add_argument("--alle", action="store_true", help="Mit --plan: alle, nicht nur fällige")
    ap.add_argument("--dry-run", action="store_true", help="Nur zeigen, nichts schreiben")
    ap.add_argument("--offline", action="store_true", help="Ohne Netz (Probelauf)")
    ap.add_argument("--ohne-browser", action="store_true", help="Browser-Beweis auslassen")
    ap.add_argument("--status", action="store_true", help="Lage der vier Gewerke")
    ap.add_argument("--json", action="store_true", help="Maschinenlesbar")
    ap.add_argument("--selftest", action="store_true", help="Offline-Selbsttest")
    args = ap.parse_args()

    if args.selftest:
        fehler = selftest()
        if fehler:
            print("❌ Antwortwerk-Selbsttest fehlgeschlagen:")
            for f in fehler:
                print(f"   · {f}")
            return 2
        print("✅ Antwortwerk-Selbsttest grün (15 Proben, offline).")
        return 0

    ssot = wa.lade_ssot()

    if args.status:
        lage = wa.gesamtlage(ssot)
        if args.json:
            print(json.dumps(lage, ensure_ascii=False, indent=2))
            return 0
        symbol = {wa.BEREIT: "✅", wa.STANDBY: "⏸", wa.DEFEKT: "❌"}
        print("Werkbank – Lage der Gewerke\n")
        for g in lage["gewerke"]:
            print(f"  {symbol.get(g['zustand'], '?')} {g['id']:<12} {g['grund']}")
            for unter in g.get("suche", []) + g.get("synthese", []):
                print(f"        {symbol.get(unter['zustand'], '?')} "
                      f"{unter['id']:<12} {unter['grund']}")
        print("\n  ⏸ = Standby. Das ist ein Zustand, kein Fehler.")
        return 0

    fragen: list[dict] = []
    state = lade_state()
    if args.frage:
        fragen = [{"id": "adhoc", "frage": args.frage}]
    elif args.plan:
        budget = (ssot.get("antwortwerk") or {}).get("budget") or {}
        kandidaten = (ssot.get("fragen") or []) if args.alle else faellige_fragen(ssot, state)
        fragen = kandidaten[: int(budget.get("max_fragen_pro_lauf", 3))]
    else:
        ap.print_help()
        return 0

    if not fragen:
        print("Nichts fällig – das Antwortwerk bleibt still.")
        return 0

    erzeugt, leer = 0, 0
    for f in fragen:
        print(f"→ {f['frage']}")
        lauf = beantworte(f["frage"], ssot, mit_browser=not args.ohne_browser,
                          offline=args.offline)
        if args.dry_run:
            print(f"   (Probelauf) Belege: {len(lauf['belege'])}, "
                  f"Suche: {lauf['suche'].get('anbieter')}")
            continue
        pfad = dossier_schreiben(lauf, ssot)
        if lauf["belege"]:
            erzeugt += 1
            print(f"   ✅ {len(lauf['belege'])} Beleg(e) → {pfad.relative_to(ROOT)}")
            if f["id"] != "adhoc":
                state.setdefault(f["id"], {})["zuletzt"] = heute().isoformat()
        else:
            leer += 1
            print(f"   ⏸ keine belegfähige Fundstelle → {pfad.relative_to(ROOT)}")

    if not args.dry_run:
        speichere_state(state)

    if erzeugt == 0 and leer > 0:
        print("\n⚠ Keine einzige Quelle lieferte belegfähiges Material.")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
