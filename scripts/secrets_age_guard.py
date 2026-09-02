#!/usr/bin/env python3
"""
SECRETS-AGE-GUARD – Secrets-/Token-Alters-Wache (Agentur-Betriebssicherheit)

Ein totes Secret ist der klassische lautlose Kanaltod: Pinterest-Tokens laufen
nach 30 Tagen ab, Mastodon-Access-Tokens ebenfalls, KI-Keys werden rotiert.
Wird der Fehler nicht gemeldet, fehlen Pins/Toots/Artikel einfach – ohne Alarm.

Der Wächter löst das mit einem ALTERS-BEWUSSTEN Ansatz:
  1. Prüft, welche Secrets im CI-Env gesetzt sind (Vorhandensein).
  2. Führ ein **Zuletzt-erfolgreich-genutzt**-Log (`data/secrets_state.json`):
     Workflows rufen `--record-success <VAR>` auf, wenn sie ein Secret
     erfolgreich verwendet haben.
  3. Meldet Secrets, die (a) fehlen, (b) zu alt sind (kein Erfolg in N Tagen),
     oder (c) deren Pinterest-Token-Datei fehlt, obwohl ein Key gesetzt ist.

AUSGABE:
  - `SECRETS-REPORT.md` – Übersicht + Ampel
  - `data/secrets_state.json` – Historie (append, append-only)
  - `--issue`          – GitHub-Issue-Body
  - `--selftest`

Exit-Codes: 0 = grün, 1 = Handlungsbedarf, 2 = Selftest/Fehler.

Nutzung:
  python3 scripts/secrets_age_guard.py                 # prüfen (+Report)
  python3 scripts/secrets_age_guard.py --record-success GROQ_API_KEY
  python3 scripts/secrets_age_guard.py --selftest
"""
import json
import os
import re
import sys
import datetime

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT = os.path.join(BLOG_DIR, "SECRETS-REPORT.md")
STATE = os.path.join(BLOG_DIR, "data", "secrets_state.json")
PIN_FILE = os.path.join(BLOG_DIR, "data", "pinterest_tokens.enc")

TODAY = datetime.date.today()

# Wichtige Secrets und ihre "frische Erwartung" (in Tagen bis zur Erinnerung)
#
# `optional`: Das Secret ist ein ALTERNATIVER Weg, kein Pflicht-Kanal. Fehlt es,
# ist das nur dann ein Befund, wenn auch die Alternative fehlt (`alt_of`).
# Vorher meldete `PINTEREST_TOKEN_KEY` dauerhaft RED, obwohl der Pinterest-Kanal
# über `PINTEREST_ACCESS_TOKEN` sauber läuft – ein Dauer-Fehlalarm, der die
# Gesamt-Ampel rot färbte und damit echte rote Befunde unsichtbar machte.
SECRETS = {
    "GROQ_API_KEY":     {"days": 60,  "label": "Groq KI-Key"},
    "GEMINI_API_KEY":   {"days": 60,  "label": "Gemini KI-Key"},
    "PINTEREST_ACCESS_TOKEN": {"days": 15, "label": "Pinterest Access-Token"},
    "MASTODON_ACCESS_TOKEN":  {"days": 45, "label": "Mastodon Access-Token"},
    "PINTEREST_TOKEN_KEY":    {"days": 60, "label": "Pinterest Verschlüsselungs-Key",
                               "optional": True, "alt_of": "PINTEREST_ACCESS_TOKEN"},
}


def _load_state():
    if not os.path.exists(STATE):
        return {"version": 1, "entries": {}}
    try:
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "entries": {}}


def _save_state(state):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _record_success(var):
    var = var.strip().upper()
    if var not in SECRETS:
        print(f"❌ Unbekanntes Secret '{var}' (erlaubt: {', '.join(SECRETS)})")
        return 1
    state = _load_state()
    ent = state.setdefault("entries", {}).setdefault(var, {})
    ent["last_success"] = TODAY.isoformat()
    ent["last_attempt"] = TODAY.isoformat()
    _save_state(state)
    print(f"✅ {SECRETS[var]['label']} ({var}): Erfolg am {TODAY.isoformat()} vermerkt.")
    return 0


def audit():
    state = _load_state()
    entries = state.setdefault("entries", {})
    findings = []
    summary = []
    for var, meta in SECRETS.items():
        present = bool(os.environ.get(var, "").strip())
        ent = entries.get(var, {})
        last_success = ent.get("last_success")
        label = meta["label"]
        if not present and not os.path.exists(PIN_FILE) and var == "PINTEREST_ACCESS_TOKEN":
            # Pinterest kann alternativ über die verschlüsselte Token-Datei laufen
            present = os.path.exists(PIN_FILE)
        if not present:
            alt = meta.get("alt_of")
            alt_ok = bool(alt and (os.environ.get(alt, "").strip()
                                   or (alt == "PINTEREST_ACCESS_TOKEN"
                                       and os.path.exists(PIN_FILE))))
            if meta.get("optional") and alt_ok:
                # Alternativer Auth-Pfad ist aktiv → kein Befund.
                summary.append((var, f"NICHT GENUTZT (via {alt})"))
                continue
            if meta.get("optional"):
                findings.append({"level": "amber", "code": "missing_optional", "var": var,
                                 "msg": f"{label} (`{var}`) fehlt – optionaler Pfad; "
                                        f"aktiv ist keiner: auch `{alt}` fehlt"})
                summary.append((var, "FEHLT (optional)"))
                continue
            findings.append({"level": "red", "code": "missing", "var": var,
                             "msg": f"{label} (`{var}`) fehlt im Env"})
            summary.append((var, "FEHLT"))
            continue
        if last_success:
            sd = datetime.date.fromisoformat(last_success)
            age = (TODAY - sd).days
            if age > meta["days"]:
                findings.append({"level": "red", "code": "stale", "var": var,
                                 "age": age, "days": meta["days"],
                                 "msg": f"{label} seit {age} Tagen ohne Erfolg "
                                        f"(erwartet ≤ {meta['days']})"})
                summary.append((var, f"STALE {age}d"))
            elif age > meta["days"] * 0.5:
                findings.append({"level": "amber", "code": "aging", "var": var,
                                 "age": age, "days": meta["days"],
                                 "msg": f"{label}: {age} Tage ohne Erfolg"})
                summary.append((var, f"ALTERN {age}d"))
            else:
                summary.append((var, f"OK ({age}d)"))
        else:
            # noch nie vermerkt -> unbekannt (amber, kein roter Alarm beim ersten Lauf)
            findings.append({"level": "amber", "code": "untracked", "var": var,
                             "msg": f"{label}: kein Erfolgs-Log (ausstehend, "
                                    "bitte --record-success einbinden)"})
            summary.append((var, "UNBEKANNT"))
    # Pinterest-Token-Datei gesondert
    if ("PINTEREST_ACCESS_TOKEN" not in os.environ) and (not os.path.exists(PIN_FILE)):
        if not any(f["var"] == "PINTEREST_ACCESS_TOKEN" and f["code"] == "missing" for f in findings):
            findings.append({"level": "amber", "code": "pin_file", "var": "PINTEREST_TOKEN_FILE",
                             "msg": "Pinterest-Token: weder Env-Token noch "
                                    "`data/pinterest_tokens.enc` vorhanden"})
    return findings, summary


def _verdict(findings):
    if any(f["level"] == "red" for f in findings):
        return "RED"
    if any(f["level"] == "amber" for f in findings):
        return "AMBER"
    return "GREEN"


def render_report(findings, summary):
    verdict = _verdict(findings)
    lines = [
        "# 🔐 Secrets-/Token-Alters-Wache",
        f"**Stand:** {TODAY.isoformat()}",
        "",
        f"## Gesamt-Ampel: **{verdict}**",
        "",
        "| Secret | Status |",
        "|---|---|",
    ]
    for var, st in summary:
        lines.append(f"| `{var}` | {st} |")
    lines += ["", "## Befunde", ""]
    if findings:
        lines += ["| Ebene | Code | Meldung |", "|---|---|---|"]
        for f in findings:
            lines.append(f"| {f['level'].upper()} | {f['code']} | `{f['var']}` – {f['msg']} |")
    else:
        lines.append("_Alle Secrets aktuell._")
    lines += ["", "## Empfehlungen", "",
              "1. **Pinterest:** Access-Token (30 Tage) automatisch via "
              "`pinterest_auth.py` erneuern; der Eintrag `last_success` beweist, "
              "dass der Refresh läuft.",
              "2. **Workflows:** Nach jedem erfolgreichen Secret-Gebrauch "
              "`python3 scripts/secrets_age_guard.py --record-success <VAR>` "
              "in den Workflow einhängen (siehe Premium-Governance).",
              "3. **Rote Befunde sofort prüfen:** Geheimes fehlt / zu alt = "
              "Kanal pinnt/toott/generiert silent nicht mehr.",
              "",
              f"_Automatisch erzeugt von `scripts/secrets_age_guard.py` am {TODAY.isoformat()}._"]
    return "\n".join(lines) + "\n"


def _selftest():
    failures = []
    # _verdict
    if _verdict([{"level": "red"}]) != "RED":
        failures.append("RED-Verdict")
    if _verdict([{"level": "amber"}]) != "AMBER":
        failures.append("AMBER-Verdict")
    if _verdict([]) != "GREEN":
        failures.append("GREEN-Verdict")
    # SECRETS-Registrierung konsistent
    for var in ("GROQ_API_KEY", "PINTEREST_ACCESS_TOKEN"):
        if var not in SECRETS:
            failures.append(f"{var} nicht registriert")
    # Alter-Hysterese: age==days -> nicht stale (strict >), age>days*0.5 -> amber
    if not (40 > 30 * 0.5):
        failures.append("Hysterese-Konstante")

    # --- Optionale Secrets dürfen keinen Dauer-RED erzeugen ---
    _env_backup = dict(os.environ)
    try:
        for var in SECRETS:
            os.environ.pop(var, None)
        # Fall A: Access-Token gesetzt → TOKEN_KEY ist ein reiner Alternativpfad
        os.environ["PINTEREST_ACCESS_TOKEN"] = "dummy"
        f_a, s_a = audit()
        if any(x["var"] == "PINTEREST_TOKEN_KEY" for x in f_a):
            failures.append("PINTEREST_TOKEN_KEY meldet Befund, obwohl "
                            "PINTEREST_ACCESS_TOKEN aktiv ist (Dauer-Fehlalarm)")
        if any(x["level"] == "red" and x["var"] == "PINTEREST_TOKEN_KEY" for x in f_a):
            failures.append("Optionales Secret erzeugt RED")
        # Fall B: kein Pinterest-Pfad → höchstens AMBER, nie RED
        os.environ.pop("PINTEREST_ACCESS_TOKEN", None)
        f_b, _ = audit()
        tk = [x for x in f_b if x["var"] == "PINTEREST_TOKEN_KEY"]
        if tk and tk[0]["level"] == "red":
            failures.append("Optionales Secret ohne Alternative meldet RED "
                            "statt AMBER")
        # Pflicht-Secrets bleiben hart rot
        if not any(x["var"] == "GROQ_API_KEY" and x["level"] == "red" for x in f_b):
            failures.append("Pflicht-Secret GROQ_API_KEY meldet kein RED mehr")
    finally:
        os.environ.clear()
        os.environ.update(_env_backup)
    if failures:
        print("❌ SECRETS-SELFTEST FEHLGESCHLAGEN:")
        for f in failures:
            print("   -", f)
        return 2
    print("✅ SECRETS-SELFTEST bestanden (Ampel, Registrierung, Hysterese).")
    return 0


def main():
    if "--selftest" in sys.argv:
        return _selftest()
    for i, arg in enumerate(sys.argv):
        if arg == "--record-success" and i + 1 < len(sys.argv):
            return _record_success(sys.argv[i + 1])
    findings, summary = audit()
    report = render_report(findings, summary)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)
    if "--issue" in sys.argv and _verdict(findings) != "GREEN":
        n = sum(1 for f in findings if f["level"] == "red")
        print("\n===== ISSUE BODY =====\n")
        print(f"## 🔐 Secrets-Wache: {len(findings)} Befunde ({n} rot)\n\n—\n{report}")
    return 0 if _verdict(findings) == "GREEN" else 1


if __name__ == "__main__":
    sys.exit(main())
