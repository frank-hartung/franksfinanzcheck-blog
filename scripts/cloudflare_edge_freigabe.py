#!/usr/bin/env python3
# ============================================================
#  CLOUDFLARE EDGE-FREIGABE – A1 in einem Griff (WF-E813 / #809)
#  ------------------------------------------------------------
#  WARUM ES DAS GIBT (19.10.2026):
#    Die Sicherheits-Wache meldet seit dem 15.10.2026 täglich denselben
#    BEFUND: „Proxy nicht aktiv – die Transform Rule aus A1 kann gar nicht
#    wirken.“ Der Weg dorthin war ein 20-Punkte-Checkliste im Dashboard
#    (Runbook A1, Schritt 1–3). Eine Profi-Agentur liefert so etwas nicht
#    als Klickstrecke, sondern als Werkzeug: ein Befehl, der den Sollstand
#    KENNT (aus der Vorlage in cloudflare/edge-schutz.md), den IST-Stand
#    MISST und – ausdrücklich auf Zuruf – herstellt.
#
#  WAS ES TUT:
#    · --selftest   ohne Netz: die Vorlage ist lesbar, die Regel ist
#                   vollständig (acht Kopfzeilen), die Pläne sind korrekt.
#    · --pruefen    (Standard, SCHREIBT NICHTS): Zone, DNS-Proxy für
#                   franksfinanzcheck.de + www, SSL-Modus und die
#                   Transform Rule „FF Sicherheits-Header“ werden gemessen
#                   und gegen die Vorlage verglichen. Exit 0 = alles im
#                   Soll, 1 = Lücken (mit genauem nächstem Schritt),
#                   2 = Werkzeugfehler (Token/Netz/API).
#    · --apply      stellt den Sollstand IDEMPOTENT her: DNS auf Proxied,
#                   SSL-Modus Full, Regel anlegen/ersetzen. Andere Regeln
#                   der Phase bleiben unangetastet.
#
#  ZULESSIGKEIT: Das Werkzeug braucht einen API-Token mit
#    Zone.DNS:Edit, Zone.Settings:Edit, Zone.Transform Rules:Edit
#    (Cloudflare → My Profile → API Tokens → Edit zone DNS + Transform
#    Rules, nur Zone franksfinanzcheck.de). Der Token steht in der Umgebung
#    CLOUDFLARE_API_TOKEN – er wird NIE geloggt oder geschrieben.
#    Danach ZWINGEND Runbook B7 (Datenschutz-Text): Der Proxy ist rechtlich
#    eine Änderung, nicht nur eine technische.
#
#  WACHE: Danach misst die Sicherheits-Wache (täglich, Live-Job) selbst –
#    sie wird grün, sobald die acht Kopfzeilen live sind.
# ============================================================
"""Edge-Freigabe für die Zone franksfinanzcheck.de (Runbook A1, WF-E813 / #809)."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
VORLAGE = WURZEL / "cloudflare" / "edge-schutz.md"
API = "https://api.cloudflare.com/client/v4"
REGEL = "FF Sicherheits-Header"
PHASE = "http_response_headers_transform"
HOSTS = ("franksfinanzcheck.de", "www.franksfinanzcheck.de")
AUSDRUCK = ('(http.host eq "franksfinanzcheck.de" or '
            'http.host eq "www.franksfinanzcheck.de")')
TABELLE = re.compile(r"^\|\s*`(?P<name>[^`]+)`\s*\|\s*`(?P<wert>[^`]*)`\s*\|", re.M)


def vorlage_kopfzeilen(text: str | None = None) -> list[tuple[str, str]]:
    """Sollstand der acht Kopfzeilen – EINE Quelle: die Tabelle in
    cloudflare/edge-schutz.md, Abschnitt A1. Wer dort eine Zeile ändert,
    ändert auch die Regel und die Wache; eine zweite Liste im Code wäre die
    klassische Stelle, an der beide auseinanderlaufen. Nur der A1-Abschnitt
    zählt – die Tabellen der Abschnitte A2/A3 (Mengenregeln, Turnstile)
    haben dasselbe Aussehen und wären sonst Verunreinigung."""
    roh = text if text is not None else VORLAGE.read_text(encoding="utf-8")
    abschnitte = re.split(r"^## ", roh, flags=re.M)
    a1 = next((a for a in abschnitte if "A1" in a.splitlines()[0]), "")
    return [(m.group("name").strip(), m.group("wert").strip())
            for m in TABELLE.finditer(a1)]


def regel_koerper(kopfzeilen: list[tuple[str, str]]) -> dict:
    return {
        "action": "rewrite",
        "action_parameters": {
            "headers": {name: {"operation": "set", "value": wert}
                        for name, wert in kopfzeilen}
        },
        "expression": AUSDRUCK,
        "description": REGEL,
    }


def plan_dns(satz: list[dict]) -> list[str]:
    """Welche DNS-Einträge fehlen auf Proxied? (Idempotent, nur Abweichungen.)"""
    offene: list[str] = []
    for eintrag in satz:
        if not eintrag.get("proxied"):
            offene.append(eintrag.get("name") or "?")
    return offene


# ------------------------------------------------------------------ HTTP-API
def _api(token: str, weg: str, *, methode: str = "GET", daten=None):
    koerper = None if daten is None else json.dumps(daten).encode("utf-8")
    anfrage = urllib.request.Request(
        API + weg, data=koerper, method=methode,
        headers={"authorization": f"Bearer {token}",
                 "content-type": "application/json",
                 "user-agent": "franksfinanzcheck-edge-freigabe/1.0"})
    try:
        with urllib.request.urlopen(anfrage, timeout=30) as antwort:
            return json.loads(antwort.read().decode("utf-8"))
    except urllib.error.HTTPError as fehler:
        roh = fehler.read().decode("utf-8", "replace")
        raise RuntimeError(f"API {methode} {weg} → HTTP {fehler.code}: {roh[:300]}") from fehler


def _resultat(antwort: dict, was: str):
    if not antwort.get("success"):
        raise RuntimeError(f"{was} fehlgeschlagen: "
                           + json.dumps(antwort.get("errors") or [], ensure_ascii=False)[:300])
    return antwort.get("result")


def zone_id_holen(token: str, zone: str) -> str:
    result = _resultat(_api(token, f"/zones?name={zone}"), "Zonensuche")
    if not result:
        raise RuntimeError(f"Zone {zone} nicht im Konto des Tokens – Rechte prüfen "
                           "(Zone.DNS:Edit für genau diese Zone).")
    return result[0]["id"]


# ------------------------------------------------------------------ Prüfen
def pruefen(token: str, zone: str) -> tuple[int, str]:
    kopfzeilen = vorlage_kopfzeilen()
    zeilen = [f"# Edge-Freigabe — Ist gegen Soll (Zone {zone})", ""]
    fehlt: list[str] = []
    zid = zone_id_holen(token, zone)
    zeilen.append(f"- ✅ Zone erreichbar (id …{zid[-6:]}).")

    # 1. DNS-Proxy (Runbook A1, Schritt 1)
    eintraege = _resultat(_api(token, f"/zones/{zid}/dns_records"), "DNS-Lesung")
    host_satz = [e for e in eintraege if e.get("name") in HOSTS]
    for name in HOSTS:
        treffer = [e for e in host_satz if e.get("name") == name]
        if not treffer:
            fehlt.append(f"DNS: kein Eintrag für {name}")
            zeilen.append(f"- ❌ DNS `{name}`: kein Eintrag gefunden.")
        elif all(e.get("proxied") for e in treffer):
            zeilen.append(f"- ✅ DNS `{name}`: proxied (orange Wolke).")
        else:
            fehlt.append(f"DNS: {name} nicht proxied")
            zeilen.append(f"- ❌ DNS `{name}`: **nicht proxied** – die Transform Rule "
                          "kann nicht wirken (Runbook A1, Schritt 1).")

    # 2. SSL-Modus (Runbook A1, Schritt 2)
    ssl = _resultat(_api(token, f"/zones/{zid}/settings/ssl"), "SSL-Lesung")
    wert = str((ssl or {}).get("value") or "")
    if wert == "full":
        zeilen.append("- ✅ SSL-Modus `full`.")
    else:
        fehlt.append(f"SSL-Modus ist '{wert or 'unbekannt'}', soll 'full'")
        zeilen.append(f"- ❌ SSL-Modus `{wert or '?'}` – soll `full` "
                      "(`flexible` überträgt unverschlüsselt zur Ursache).")

    # 3. Transform Rule (Runbook A1, Schritt 3 / cloudflare/edge-schutz.md)
    regel = _regel_finden(token, zid)
    soll = {n: w for n, w in kopfzeilen}
    if regel is None:
        fehlt.append("Transform Rule fehlt")
        zeilen.append(f"- ❌ Transform Rule „{REGEL}“ fehlt – acht Kopfzeilen sind "
                      "nicht gesetzt (cloudflare/edge-schutz.md, A1).")
    else:
        ist = ((regel.get("action_parameters") or {}).get("headers")) or {}
        abweichend = [n for n, w in soll.items()
                      if str((ist.get(n) or {}).get("value") or "") != w]
        if not abweichend and len(ist) == len(soll):
            zeilen.append(f"- ✅ Transform Rule „{REGEL}“ vollständig "
                          f"({len(soll)} Kopfzeilen im Soll).")
        else:
            fehlt.append("Transform Rule unvollständig: " + ", ".join(abweichend or sorted(ist)))
            zeilen.append("- ❌ Transform Rule „" + REGEL + "“ weicht ab: "
                          + ", ".join(abweichend or sorted(ist)) + ".")

    zeilen += ["", f"## Ergebnis: {'IM SOLL' if not fehlt else 'OFFEN'}"]
    if fehlt:
        zeilen += ["", "Nächster Schritt: `npm run edge:freigabe:apply` "
                       "(mit CLOUDFLARE_API_TOKEN) oder Runbook A1 Schritt 1–3 von Hand.",
                   "**Danach zwingend Runbook B7** (Datenschutz-Text für den Proxy)."]
        return 1, "\n".join(zeilen)
    zeilen += ["", "Danach misst die Sicherheits-Wache (Live-Job) selbst und wird grün."]
    return 0, "\n".join(zeilen)


def _regel_finden(token: str, zid: str) -> dict | None:
    try:
        result = _resultat(
            _api(token, f"/zones/{zid}/rulesets/phases/{PHASE}/entrypoint"),
            "Ruleset-Lesung")
    except RuntimeError as fehler:
        if "HTTP 404" in str(fehler):
            return None
        raise
    for regel in (result or {}).get("rules") or []:
        if regel.get("description") == REGEL:
            return regel
    return None


# ------------------------------------------------------------------ Anwenden
def anwenden(token: str, zone: str) -> tuple[int, str]:
    kopfzeilen = vorlage_kopfzeilen()
    zeilen = [f"# Edge-Freigabe — Sollstand hergestellt (Zone {zone})", ""]
    zid = zone_id_holen(token, zone)

    # 1. DNS auf Proxied (idempotent)
    eintraege = _resultat(_api(token, f"/zones/{zid}/dns_records"), "DNS-Lesung")
    for eintrag in eintraege:
        if eintrag.get("name") in HOSTS and not eintrag.get("proxied"):
            _resultat(_api(token, f"/zones/{zid}/dns_records/{eintrag['id']}",
                           methode="PATCH", daten={"proxied": True}), "DNS-Proxy")
            zeilen.append(f"- ✅ DNS `{eintrag['name']}` → proxied.")
    if not any(f"- ✅ DNS" in z for z in zeilen):
        zeilen.append("- ✅ DNS bereits proxied (keine Änderung nötig).")

    # 2. SSL-Modus Full (idempotent)
    ssl = _resultat(_api(token, f"/zones/{zid}/settings/ssl"), "SSL-Lesung")
    if str((ssl or {}).get("value") or "") != "full":
        _resultat(_api(token, f"/zones/{zid}/settings/ssl",
                       methode="PATCH", daten={"value": "full"}), "SSL-Modus")
        zeilen.append("- ✅ SSL-Modus → `full`.")
    else:
        zeilen.append("- ✅ SSL-Modus bereits `full` (keine Änderung nötig).")

    # 3. Transform Rule anlegen oder ersetzen (andere Regeln bleiben)
    try:
        ruleset = _resultat(
            _api(token, f"/zones/{zid}/rulesets/phases/{PHASE}/entrypoint"),
            "Ruleset-Lesung")
    except RuntimeError as fehler:
        if "HTTP 404" in str(fehler):
            ruleset = None
        else:
            raise
    neue_regel = regel_koerper(kopfzeilen)
    if ruleset is None:
        _resultat(_api(token, f"/zones/{zid}/rulesets", methode="POST",
                       daten={"phase": PHASE, "rules": [neue_regel]}),
                  "Regel anlegen")
        zeilen.append(f"- ✅ Transform Rule „{REGEL}“ angelegt ({len(kopfzeilen)} Kopfzeilen).")
    else:
        bestand = [r for r in (ruleset.get("rules") or []) if r.get("description") != REGEL]
        _resultat(_api(token, f"/zones/{zid}/rulesets/{ruleset['id']}", methode="PUT",
                       daten={"rules": bestand + [neue_regel]}), "Regel ersetzen")
        zeilen.append(f"- ✅ Transform Rule „{REGEL}“ gesetzt/aktualisiert "
                      f"({len(kopfzeilen)} Kopfzeilen, {len(bestand)} andere Regeln unangetastet).")

    zeilen += ["", "## Ergebnis: HERGESTELLT",
               "", "**Nächster Schritt: Runbook B7** (Datenschutz-Text für den "
               "Cloudflare-Proxy) – der Proxy ist rechtlich eine Änderung.",
               "Danach: `npm run header:check:live` oder den täglichen Live-Job "
               "der Sicherheits-Wache abwarten – er wird grün und schließt die Meldung."]
    return 0, "\n".join(zeilen)


# ------------------------------------------------------------------ Selbsttest
def selftest() -> int:
    faelle = 0
    kopfzeilen = vorlage_kopfzeilen()
    namen = [n for n, _ in kopfzeilen]
    # 1. Die Vorlage ist die Quelle des Solls – acht Kopfzeilen, die Wache
    #    (blog_header_gate.py) kennt jede davon.
    assert len(kopfzeilen) == 8, f"8 Kopfzeilen erwartet, {len(kopfzeilen)} gefunden: {namen}"
    for pflicht in ("Strict-Transport-Security", "X-Content-Type-Options",
                    "X-Frame-Options", "Content-Security-Policy"):
        assert pflicht in namen, f"Pflichtkopfzeile fehlt in der Vorlage: {pflicht}"
    faelle += 1

    # 2. Die Regel braucht Filter und Namen – sonst ist sie unkenntlich.
    koerper = regel_koerper(kopfzeilen)
    assert koerper["description"] == REGEL
    assert koerper["expression"] == AUSDRUCK
    assert set(koerper["action_parameters"]["headers"]) == set(namen)
    faelle += 1

    # 3. DNS-Plan: nur Abweichungen, idempotent.
    assert plan_dns([{"name": "franksfinanzcheck.de", "proxied": True},
                     {"name": "www.franksfinanzcheck.de", "proxied": True}]) == []
    ab = plan_dns([{"name": "franksfinanzcheck.de", "proxied": False}])
    assert ab == ["franksfinanzcheck.de"], ab
    faelle += 1

    # 4. Der Selbsttest selbst braucht kein Netz und keinen Token.
    assert "api.cloudflare.com" not in json.dumps(kopfzeilen)
    faelle += 1

    print(f"✅ SELBSTTEST OK — {faelle} Fälle grün (Vorlage {VORLAGE.name}: "
          f"{len(kopfzeilen)} Kopfzeilen, Regel „{REGEL}“, idempotente Pläne).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Cloudflare Edge-Freigabe: Runbook A1 prüfen/herstellen (WF-E813 / #809).")
    parser.add_argument("--selftest", action="store_true", help="prüft die Prüfung (ohne Netz)")
    parser.add_argument("--pruefen", action="store_true",
                        help="nur messen (Standard; schreibt nichts)")
    parser.add_argument("--apply", action="store_true",
                        help="Sollstand herstellen (schreibt; Standard liest nur)")
    parser.add_argument("--zone", default=os.environ.get("CLOUDFLARE_ZONE", "franksfinanzcheck.de"))
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    token = os.environ.get("CLOUDFLARE_API_TOKEN") or ""
    if not token:
        print("❌ CLOUDFLARE_API_TOKEN fehlt – ohne Token ist nichts gemessen "
              "(und nichts behauptet). Token mit Zone.DNS:Edit, Zone.Settings:Edit, "
              "Zone.Transform Rules:Edit für diese Zone.", file=sys.stderr)
        return 2
    try:
        code, bericht = (anwenden if args.apply else pruefen)(token, args.zone.strip())
    except RuntimeError as fehler:
        print(f"❌ Werkzeugfehler (nichts verändert/behauptet): {fehler}", file=sys.stderr)
        return 2
    print(bericht)
    return code


if __name__ == "__main__":
    sys.exit(main())
