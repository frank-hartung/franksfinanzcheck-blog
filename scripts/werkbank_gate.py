#!/usr/bin/env python3
# ============================================================
#  WERKBANK-GATE – der Vertrag B1–B9
#  ------------------------------------------------------------
#  Rollout 03.10.2026. SSOT: data/werkbank.yaml
#  Runbook: docs/ANLEITUNG-WERKBANK.md · Cockpit: WERKBANK-STATUS.md
#
#  Dieses Gate beantwortet zwei Fragen und verwechselt sie nie:
#    1. Ist der VERTRAG eingehalten?   → darf rot werden (Exit 1)
#    2. Ist gerade alles EINSATZBEREIT? → Standby ist gelb, nicht rot
#
#  Diese Trennung ist der Kern. Ein fehlender COMPOSIO_API_KEY ist ein
#  Betriebszustand. Ein kostenpflichtiger Anbieter im Pflichtpfad ist
#  ein Vertragsbruch. Wer beides gleich behandelt, bekommt entweder
#  Dauer-Alarm oder ein Gate, das nichts mehr aussagt.
#
#  AUFRUF
#    python3 scripts/werkbank_gate.py              # Bericht + Cockpit
#    python3 scripts/werkbank_gate.py --json       # maschinenlesbar
#    python3 scripts/werkbank_gate.py --selftest   # Sabotage-Proben
#    python3 scripts/werkbank_gate.py --strict     # Standby wird rot
#
#  Exit: 0 = Vertrag gehalten, 1 = Vertragsbruch, 2 = Gate selbst defekt.
# ============================================================
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import werkbank_adapters as wa  # noqa: E402

ROOT = wa.ROOT
COCKPIT = ROOT / "WERKBANK-STATUS.md"

PFLICHT_GEWERKE = {"antwortwerk", "leser", "browser", "konnektor"}
RUNBOOK = "docs/ANLEITUNG-WERKBANK.md"
WORKFLOW = ".github/workflows/werkbank.yml"
BRUECKE = "tools/werkbank/render.mjs"

# npm-Skripte, die laut Vertrag existieren müssen (B8).
NPM_PFLICHT = ("werkbank", "werkbank:status", "test:werkbank", "antwortwerk")


# ====================================================================
#  VERTRAGSREGELN B1–B9
#  Jede Funktion gibt eine Liste von Befunden zurück. Leer = grün.
# ====================================================================
def b1_kostenregel(ssot: dict) -> list[str]:
    """Kein kostenpflichtiger Anbieter im Pflichtpfad."""
    befunde = []
    aw = ssot.get("antwortwerk") or {}
    for anbieter in aw.get("suche") or []:
        if anbieter.get("kostenpflichtig"):
            befunde.append(
                f"B1: Suchanbieter '{anbieter.get('id')}' ist kostenpflichtig. "
                "Die Antwortmaschine muss kostenlos bleiben (Auftrag 03.10.2026).")
    for s in aw.get("synthese") or []:
        if s.get("kostenpflichtig"):
            befunde.append(
                f"B1: Syntheseweg '{s.get('id')}' ist kostenpflichtig.")
        if s.get("standard") and s.get("kostenpflichtig"):
            befunde.append(f"B1: Standardweg '{s.get('id')}' kostet Geld.")
    return befunde


def b2_schluesselfreier_weg(ssot: dict) -> list[str]:
    """Jedes Pflicht-Gewerk hat mindestens einen schlüsselfreien Weg."""
    befunde = []
    aw = ssot.get("antwortwerk") or {}

    frei_suche = [a for a in aw.get("suche") or [] if not a.get("schluessel_noetig")]
    if not frei_suche:
        befunde.append("B2: Kein schlüsselfreier Suchanbieter – das Antwortwerk "
                       "wäre ohne Secret tot.")
    frei_synthese = [s for s in aw.get("synthese") or [] if not s.get("schluessel_noetig")]
    if not frei_synthese:
        befunde.append("B2: Kein schlüsselfreier Syntheseweg (extraktiv fehlt).")

    leser = wa.gewerk(ssot, "leser")
    if leser.get("pflicht") and not (leser.get("rueckfall") or []):
        befunde.append("B2: Gewerk 'leser' ist Pflicht, hat aber keine Rückfallkette.")

    for g in ssot.get("gewerke") or []:
        if g.get("pflicht") and g.get("env") and not g.get("standby_ok"):
            befunde.append(
                f"B2: Gewerk '{g.get('id')}' ist Pflicht, braucht {g.get('env')} "
                "und erlaubt kein Standby – das friert den Betrieb ein.")
    return befunde


def b3_standby_ist_kein_fehler(ssot: dict) -> list[str]:
    """Jedes Gewerk mit Secret-Bedarf muss Standby dürfen."""
    befunde = []
    for g in ssot.get("gewerke") or []:
        if g.get("env") and not g.get("standby_ok"):
            befunde.append(
                f"B3: Gewerk '{g.get('id')}' kennt keinen Standby-Zustand. "
                "Fehlendes Secret würde zum Dauer-Alarm ohne Schließpfad.")
    return befunde


def b4_leseregel(ssot: dict) -> list[str]:
    """Nur der Konnektor darf schreiben – und nur mit Freigabe."""
    befunde = []
    schreibend = {g.get("id") for g in ssot.get("gewerke") or [] if g.get("schreibend")}
    unerlaubt = schreibend - {"konnektor"}
    if unerlaubt:
        befunde.append(
            f"B4: Schreibrecht bei {sorted(unerlaubt)}. Recherche-Gewerke lesen "
            "ausschließlich (KI-Redaktions-Statut).")

    k = wa.gewerk(ssot, "konnektor")
    if k:
        freigabe = k.get("freigabe") or {}
        if freigabe.get("modus") != "mensch":
            befunde.append("B4: konnektor.freigabe.modus muss 'mensch' sein – "
                           "kein Autopilot auf fremden Konten.")
        if not freigabe.get("trockenlauf_pflicht"):
            befunde.append("B4: konnektor.freigabe.trockenlauf_pflicht fehlt.")
        if not isinstance(freigabe.get("erlaubte_aktionen"), list):
            befunde.append("B4: konnektor.freigabe.erlaubte_aktionen muss eine "
                           "Liste sein (leer = nichts erlaubt).")
    return befunde


def b5_belegpflicht(ssot: dict) -> list[str]:
    """Jede Antwort braucht Quelle und Abrufdatum."""
    befunde = []
    belege = (ssot.get("antwortwerk") or {}).get("belege") or {}
    if not belege.get("abrufdatum_pflicht"):
        befunde.append("B5: belege.abrufdatum_pflicht ist nicht gesetzt – "
                       "Belege ohne Datum sind in YMYL-Themen wertlos.")
    if not belege.get("allowlist_quelle"):
        befunde.append("B5: Keine Allowlist-Quelle hinterlegt.")
    else:
        pfad = ROOT / belege["allowlist_quelle"]
        if not pfad.is_file():
            befunde.append(f"B5: Allowlist-Quelle fehlt: {belege['allowlist_quelle']}")
    budget = (ssot.get("antwortwerk") or {}).get("budget") or {}
    if int(budget.get("max_belege_antwort", 0)) < 1:
        befunde.append("B5: budget.max_belege_antwort < 1 – Antworten ohne Beleg.")
    return befunde


def b6_keine_secrets(ssot_text: str) -> list[str]:
    """In der SSOT stehen ENV-Namen, niemals Werte."""
    befunde = []
    muster = [
        (r"(?:sk-|gsk_|pplx-|ak_live|uak_)[A-Za-z0-9_\-]{12,}", "API-Schlüssel"),
        (r"(?i)\b(api[_-]?key|token|secret)\s*:\s*[\"']?[A-Za-z0-9_\-]{16,}", "Secret-Wert"),
    ]
    for regex, was in muster:
        for fund in re.findall(regex, ssot_text):
            treffer = fund if isinstance(fund, str) else fund[0]
            befunde.append(f"B6: {was} im Klartext in data/werkbank.yaml: "
                           f"{str(treffer)[:12]}… – gehört in GitHub-Secrets.")
    return befunde


def b7_selbsttest_offline() -> list[str]:
    """Der Selbsttest des Antwortwerks muss ohne Netz grün sein."""
    try:
        import antwortwerk
    except Exception as exc:  # noqa: BLE001
        return [f"B7: antwortwerk.py nicht importierbar ({exc})."]
    try:
        fehler = antwortwerk.selftest()
    except Exception as exc:  # noqa: BLE001
        return [f"B7: Selbsttest wirft ({type(exc).__name__}: {exc})."]
    return [f"B7: Selbsttest-Befund – {f}" for f in fehler]


def b8_verdrahtung() -> list[str]:
    """Runbook, Workflow, Brücke und npm-Skripte existieren wirklich."""
    befunde = []
    for rel, was in ((RUNBOOK, "Runbook"), (WORKFLOW, "Workflow"),
                     (BRUECKE, "Playwright-Brücke")):
        if not (ROOT / rel).is_file():
            befunde.append(f"B8: {was} fehlt: {rel}")

    wf = ROOT / WORKFLOW
    if wf.is_file():
        text = wf.read_text(encoding="utf-8")
        if "--selftest" not in text:
            befunde.append("B8: Workflow ruft keinen Selbsttest – ein Lauf ohne "
                           "fail-closed-Prüfung darf nichts erzeugen.")
        if "werkbank_gate.py" not in text:
            befunde.append("B8: Workflow ruft das Gate nicht auf.")

    pkg = ROOT / "package.json"
    if pkg.is_file():
        try:
            skripte = json.loads(pkg.read_text(encoding="utf-8")).get("scripts") or {}
        except json.JSONDecodeError:
            befunde.append("B8: package.json nicht lesbar.")
            skripte = {}
        for name in NPM_PFLICHT:
            if name not in skripte:
                befunde.append(f"B8: npm-Skript '{name}' fehlt in package.json.")
    return befunde


def b9_domain_disziplin(ssot: dict) -> list[str]:
    """Sperrliste deckt eigene Domain und Affiliate-Partner ab."""
    befunde = []
    belege = (ssot.get("antwortwerk") or {}).get("belege") or {}
    sperre = {s.lower().lstrip(".") for s in belege.get("sperrliste") or []}
    if "franksfinanzcheck.de" not in sperre:
        befunde.append("B9: Eigene Domain fehlt auf der Sperrliste – "
                       "Selbstbeleg wäre ein Zirkelschluss.")

    # Alles, was im Repo als Affiliate-Partner geführt wird, muss gesperrt sein.
    partner = _affiliate_domains()
    offen = sorted(p for p in partner if p not in sperre)
    if offen:
        befunde.append(
            f"B9: Affiliate-Domains ohne Sperreintrag: {', '.join(offen)} – "
            "Provisionsquelle darf nie Faktenquelle sein.")

    # Sperrliste und Allowlist dürfen sich nicht widersprechen.
    import antwortwerk
    allow = antwortwerk.lade_allowlist(ssot)
    kollision = sorted(set(allow) & sperre)
    if kollision:
        befunde.append(f"B9: Domain steht gleichzeitig auf Allow- und Sperrliste: "
                       f"{', '.join(kollision)}")
    return befunde


def _affiliate_domains() -> set[str]:
    """Affiliate-Partner aus dem Bestand lesen – ohne harte Zweitliste.

    Quelle ist die vorhandene Partnerliste des Repos. Aus `a.check24.net`
    wird `check24.net`: Gesperrt wird die Domain, nicht der Einstiegshost –
    sonst genügt ein neuer Subdomain-Name, um die Sperre zu umgehen.
    """
    gefunden: set[str] = set()
    kandidat = ROOT / "scripts" / "check24_links.yaml"
    if not kandidat.is_file():
        return gefunden
    for host in re.findall(r"https?://([a-z0-9.\-]+\.[a-z]{2,})",
                           kandidat.read_text(encoding="utf-8")):
        teile = host.lower().split(".")
        if len(teile) >= 2:
            gefunden.add(".".join(teile[-2:]))
    return gefunden


REGELN = {
    "B1": "Kostenregel – kein kostenpflichtiger Anbieter im Pflichtpfad",
    "B2": "Schlüsselfreiheit – jedes Pflicht-Gewerk läuft ohne Secret",
    "B3": "Standby ist ein Zustand, kein Fehler",
    "B4": "Leseregel – nur der Konnektor schreibt, nur mit Freigabe",
    "B5": "Belegpflicht – Quelle und Abrufdatum je Aussage",
    "B6": "Keine Secrets in der SSOT",
    "B7": "Selbsttest läuft offline und ist grün",
    "B8": "Verdrahtung – Runbook, Workflow, Brücke, npm-Skripte",
    "B9": "Domain-Disziplin – Sperrliste vor Allowlist",
}


def pruefe_vertrag(ssot: dict | None = None, ssot_text: str | None = None) -> dict:
    """Alle neun Regeln. Rein, testbar, ohne Netzaufruf."""
    ssot = ssot if ssot is not None else wa.lade_ssot()
    if ssot_text is None:
        pfad = ROOT / "data" / "werkbank.yaml"
        ssot_text = pfad.read_text(encoding="utf-8") if pfad.is_file() else ""

    befunde: dict[str, list[str]] = {
        "B1": b1_kostenregel(ssot),
        "B2": b2_schluesselfreier_weg(ssot),
        "B3": b3_standby_ist_kein_fehler(ssot),
        "B4": b4_leseregel(ssot),
        "B5": b5_belegpflicht(ssot),
        "B6": b6_keine_secrets(ssot_text),
        "B7": b7_selbsttest_offline(),
        "B8": b8_verdrahtung(),
        "B9": b9_domain_disziplin(ssot),
    }
    return befunde


# ====================================================================
#  COCKPIT
# ====================================================================
def schreibe_cockpit(befunde: dict, lage: dict) -> None:
    symbol = {wa.BEREIT: "✅", wa.STANDBY: "⏸", wa.DEFEKT: "❌"}
    gebrochen = sum(1 for v in befunde.values() if v)

    z = [
        "# Werkbank – Status",
        "",
        f"> Erzeugt von `scripts/werkbank_gate.py` am {lage['zeitpunkt']}.",
        "> Diese Datei ist ein Lauf-Artefakt und wird nicht versioniert.",
        "",
        "## Vertrag",
        "",
        f"**{len(REGELN) - gebrochen} von {len(REGELN)} Regeln gehalten.**",
        "",
        "| Regel | Inhalt | Stand |",
        "|---|---|---|",
    ]
    for rid, titel in REGELN.items():
        stand = "✅ gehalten" if not befunde[rid] else f"❌ {len(befunde[rid])} Befund(e)"
        z.append(f"| {rid} | {titel} | {stand} |")

    z += ["", "## Gewerke", "",
          "| Gewerk | Zustand | Bemerkung |", "|---|---|---|"]
    for g in lage["gewerke"]:
        z.append(f"| `{g['id']}` | {symbol.get(g['zustand'], '?')} {g['zustand']} "
                 f"| {g['grund']} |")

    antwort = next((g for g in lage["gewerke"] if g["id"] == "antwortwerk"), {})
    if antwort.get("suche"):
        z += ["", "### Antwortwerk – Suchkette", "",
              "| Anbieter | Zustand | Bemerkung |", "|---|---|---|"]
        for s in antwort["suche"]:
            z.append(f"| `{s['id']}` | {symbol.get(s['zustand'], '?')} {s['zustand']} "
                     f"| {s['grund']} |")
    if antwort.get("synthese"):
        z += ["", "### Antwortwerk – Synthesewege", "",
              "| Weg | Zustand | Bemerkung |", "|---|---|---|"]
        for s in antwort["synthese"]:
            z.append(f"| `{s['id']}` | {symbol.get(s['zustand'], '?')} {s['zustand']} "
                     f"| {s['grund']} |")

    if gebrochen:
        z += ["", "## Befunde", ""]
        for rid, liste in befunde.items():
            for b in liste:
                z.append(f"- {b}")

    z += ["", "---", "",
          "**⏸ Standby heißt: Das Gewerk schläft, weil ihm eine Voraussetzung",
          "fehlt. Das ist Absicht und kein Defekt.** Was fehlt und wie man es",
          f"nachrüstet, steht in `{RUNBOOK}`.", "",
          "Laufende Kosten der Antwortmaschine: **0 €**."]

    COCKPIT.write_text("\n".join(z) + "\n", encoding="utf-8")


# ====================================================================
#  SELBSTTEST – jede Regel muss brechen, wenn man sie sabotiert
# ====================================================================
def selftest() -> list[str]:
    fehler: list[str] = []
    echt = wa.lade_ssot()
    echt_text = (ROOT / "data" / "werkbank.yaml").read_text(encoding="utf-8")

    def pruefe(name: str, bedingung: bool, hinweis: str) -> None:
        if not bedingung:
            fehler.append(f"{name}: {hinweis}")

    # Positivprobe: Der echte Vertrag ist grün.
    echte_befunde = pruefe_vertrag(echt, echt_text)
    for rid, liste in echte_befunde.items():
        pruefe(f"GT-{rid}", not liste, f"echte SSOT bricht {rid}: {liste}")

    # --- Sabotage B1: Suchanbieter kostenpflichtig machen -------------
    s = copy.deepcopy(echt)
    s["antwortwerk"]["suche"][0]["kostenpflichtig"] = True
    pruefe("SB1", bool(b1_kostenregel(s)), "kostenpflichtiger Anbieter nicht erkannt")

    # --- Sabotage B2: letzten schlüsselfreien Syntheseweg entfernen ----
    s = copy.deepcopy(echt)
    s["antwortwerk"]["synthese"] = [x for x in s["antwortwerk"]["synthese"]
                                    if x.get("schluessel_noetig")]
    pruefe("SB2", bool(b2_schluesselfreier_weg(s)),
           "fehlender schlüsselfreier Syntheseweg nicht erkannt")

    # --- Sabotage B3: Standby verbieten -------------------------------
    s = copy.deepcopy(echt)
    for g in s["gewerke"]:
        if g.get("env"):
            g["standby_ok"] = False
    pruefe("SB3", bool(b3_standby_ist_kein_fehler(s)), "Standby-Verbot nicht erkannt")

    # --- Sabotage B4a: Leser bekommt Schreibrecht ----------------------
    s = copy.deepcopy(echt)
    wa.gewerk(s, "leser")["schreibend"] = True
    pruefe("SB4a", bool(b4_leseregel(s)), "Schreibrecht beim Leser nicht erkannt")

    # --- Sabotage B4b: Konnektor auf Autopilot -------------------------
    s = copy.deepcopy(echt)
    wa.gewerk(s, "konnektor")["freigabe"]["modus"] = "auto"
    pruefe("SB4b", bool(b4_leseregel(s)), "Autopilot-Freigabe nicht erkannt")

    # --- Sabotage B5: Abrufdatum abschalten ----------------------------
    s = copy.deepcopy(echt)
    s["antwortwerk"]["belege"]["abrufdatum_pflicht"] = False
    pruefe("SB5", bool(b5_belegpflicht(s)), "fehlende Datumspflicht nicht erkannt")

    # --- Sabotage B6: Schlüssel in die SSOT schreiben -------------------
    gift = echt_text + '\n  api_key: "sk-abcdefghijklmnopqrstuvwxyz123456"\n'
    pruefe("SB6", bool(b6_keine_secrets(gift)), "Schlüssel im Klartext nicht erkannt")
    pruefe("SB6b", not b6_keine_secrets(echt_text),
           "Fehlalarm auf der echten, sauberen SSOT")

    # --- Sabotage B9a: eigene Domain von der Sperrliste nehmen ----------
    s = copy.deepcopy(echt)
    s["antwortwerk"]["belege"]["sperrliste"] = [
        d for d in s["antwortwerk"]["belege"]["sperrliste"]
        if d != "franksfinanzcheck.de"]
    pruefe("SB9a", bool(b9_domain_disziplin(s)), "fehlender Selbstbeleg-Schutz nicht erkannt")

    # --- Sabotage B9b: Partner gleichzeitig erlauben und sperren --------
    s = copy.deepcopy(echt)
    s["antwortwerk"]["belege"]["sperrliste"] = (
        s["antwortwerk"]["belege"]["sperrliste"] + ["test.de"])
    pruefe("SB9b", bool(b9_domain_disziplin(s)), "Allow-/Sperrlisten-Kollision nicht erkannt")

    return fehler


# ------------------------------------------------------------------ CLI
def main() -> int:
    ap = argparse.ArgumentParser(description="Werkbank-Gate – Vertrag B1–B9")
    ap.add_argument("--json", action="store_true", help="maschinenlesbar")
    ap.add_argument("--strict", action="store_true",
                    help="Standby zählt als Fehler (nur für Freigabe-Läufe)")
    ap.add_argument("--selftest", action="store_true", help="Sabotage-Proben")
    ap.add_argument("--no-cockpit", action="store_true", help="WERKBANK-STATUS.md nicht schreiben")
    args = ap.parse_args()

    if args.selftest:
        fehler = selftest()
        if fehler:
            print("❌ Werkbank-Gate-Selbsttest fehlgeschlagen:")
            for f in fehler:
                print(f"   · {f}")
            return 2
        print("✅ Werkbank-Gate-Selbsttest grün (Positivprobe + 10 Sabotage-Proben).")
        return 0

    ssot = wa.lade_ssot()
    befunde = pruefe_vertrag(ssot)
    lage = wa.gesamtlage(ssot)

    if not args.no_cockpit:
        schreibe_cockpit(befunde, lage)

    gebrochen = {r: v for r, v in befunde.items() if v}
    standby = [g for g in lage["gewerke"] if g["zustand"] == wa.STANDBY]
    defekt = [g for g in lage["gewerke"] if g["zustand"] == wa.DEFEKT]

    if args.json:
        print(json.dumps({"vertrag": befunde, "lage": lage,
                          "gebrochen": sorted(gebrochen),
                          "standby": [g["id"] for g in standby],
                          "defekt": [g["id"] for g in defekt]},
                         ensure_ascii=False, indent=2))
    else:
        symbol = {wa.BEREIT: "✅", wa.STANDBY: "⏸", wa.DEFEKT: "❌"}
        print("Werkbank-Gate – Vertrag B1–B9\n")
        for rid, titel in REGELN.items():
            if befunde[rid]:
                print(f"  ❌ {rid}  {titel}")
                for b in befunde[rid]:
                    print(f"        {b}")
            else:
                print(f"  ✅ {rid}  {titel}")
        print("\nGewerke:")
        for g in lage["gewerke"]:
            print(f"  {symbol.get(g['zustand'], '?')} {g['id']:<12} {g['grund']}")
        if standby:
            print("\n  ⏸ Standby ist ein Zustand, kein Fehler. "
                  f"Nachrüsten: {RUNBOOK}")
        if not args.no_cockpit:
            print(f"\nCockpit geschrieben: {COCKPIT.name}")

    if gebrochen:
        print(f"\n::error::Werkbank-Vertrag gebrochen: {', '.join(sorted(gebrochen))}")
        return 1
    if defekt:
        print(f"\n::error::Gewerk defekt: {', '.join(g['id'] for g in defekt)}")
        return 1
    if args.strict and standby:
        print(f"\n::error::--strict: Standby bei {', '.join(g['id'] for g in standby)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
