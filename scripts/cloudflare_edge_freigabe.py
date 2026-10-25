#!/usr/bin/env python3
# ============================================================
#  CLOUDFLARE EDGE-FREIGABE – A1 + B7 in einem Griff (WF-E813 / #809 / #815)
#  ------------------------------------------------------------
#  WARUM ES DAS GIBT (19.10.2026, gehärtet 24.10.2026 für #815):
#    Die Sicherheits-Wache meldet täglich denselben BEFUND, solange die Zone
#    nicht hinter dem Cloudflare-Proxy liegt und die Transform Rule A1 nicht
#    aktiv ist. Statt einer 20-Punkte-Klickstrecke im Dashboard liefert dieses
#    Werkzeug Messung, idempotente Herstellung und den nachgelagerten B7-
#    Datenschutz-Angleich aus EINER Quelle (cloudflare/edge-schutz.md).
#
#  HÄRTUNGEN 24.10.2026 (WF-E813 / #815):
#    1. KEIN TLS-DOWNGRADE MEHR: Runbook A1 verlangt bevorzugt „Full (strict)“
#       (API-Wert `strict`), mindestens „Full“ (`full`). Früher wies --pruefen
#       `strict` als Fehler ab und --apply stufte `strict` still auf `full`
#       herab! Jetzt gelten beide sicheren Modi (`strict` bevorzugt, `full`
#       zulässig); ein vorhandenes `strict` wird NIEMALS heruntergestuft.
#    2. VOLLSTÄNDIGE REGEL-PRÜFUNG: --pruefen prüft neben den acht Werten auch
#       `enabled != False` (deaktivierte Regel im Dashboard!), `action ==
#       "rewrite"`, den exakten Host-Filter (`AUSDRUCK` für Hauptdomain + www)
#       sowie `operation == "set"` je Kopfzeile.
#    3. KREUZBEWEIS GEGEN DIE LIVE-WACHE: --selftest beweist maschinell, dass
#       die Vorlagen-Kopfzeilen `blog_header_gate.befunde_fuer()` mit 0 Fehlern
#       und 0 Warnungen bestehen.
#    4. REDIRECT- UND TOKEN-SCHUTZ: Bearer-Token wird niemals über HTTP-3xx
#       weitergereicht und erscheint in keiner Fehlermeldung.
#    5. B7-DATENSCHUTZ PER BEFEHL (--b7-check / --b7-apply): gleicht nach dem
#       Proxy-Start `content/datenschutz/index.md` idempotent an Runbook B7 an.
# ============================================================
"""Edge-Freigabe für die Zone franksfinanzcheck.de (Runbook A1 + B7, WF-E813 / #815)."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
VORLAGE = WURZEL / "cloudflare" / "edge-schutz.md"
DATENSCHUTZ = WURZEL / "content" / "datenschutz" / "index.md"
API = "https://api.cloudflare.com/client/v4"
REGEL = "FF Sicherheits-Header"
PHASE = "http_response_headers_transform"
HOSTS = ("franksfinanzcheck.de", "www.franksfinanzcheck.de")
WEB_DNS_TYPEN = frozenset(("A", "AAAA", "CNAME"))
AUSDRUCK = ('(http.host eq "franksfinanzcheck.de" or '
            'http.host eq "www.franksfinanzcheck.de")')
SSL_ERLAUBT = ("strict", "full")
TABELLE = re.compile(r"^\|\s*`(?P<name>[^`]+)`\s*\|\s*`(?P<wert>[^`]*)`\s*\|", re.M)

# B7-Textbausteine (exakt nach docs/SICHERHEIT-BETRIEB-RUNBOOK.md, B7 – ohne
# eingebettete URLs, damit die bestehenden Markdown-Links in datenschutz/index.md
# unangetastet bleiben und der T6-Hostvertrag rein auf api.cloudflare.com bleibt).
B7_VOR_PROXY_SATZ = (
    "Diese Website wird von **GitHub Pages** ausgeliefert "
    "(GitHub, Inc., 88 Colin P. Kelly Jr. Street, San Francisco, CA 94107, USA). "
    "Die Domain franksfinanzcheck.de zeigt direkt auf die Server von GitHub Pages. "
    "Zum Stand 11. Oktober 2026 ist kein Proxy von Cloudflare vor die Website geschaltet."
)
B7_MIT_PROXY_SATZ = (
    "Diese Website wird von **GitHub Pages** ausgeliefert "
    "(GitHub, Inc., 88 Colin P. Kelly Jr. Street, San Francisco, CA 94107, USA). "
    "**Vorgeschaltet ist das CDN von Cloudflare, Inc.** "
    "(101 Townsend St., San Francisco, CA 94107, USA), das Zugriffe entgegennimmt, "
    "technisch absichert und beschleunigt. Cloudflare verarbeitet dabei technische "
    "Zugriffsdaten wie IP-Adresse, Zeitpunkt, angeforderte Adresse, Browsertyp und "
    "Referrer sowie Sicherheitsmerkmale zur Abwehr von Angriffen. Die Server-Logfiles "
    "und Aufbewahrungsfristen richten sich nach Cloudflare."
)
B7_DNS_NUR_AUFLOESUNG = (
    "Cloudflare erhält dabei keine Informationen über Seitenaufrufe, "
    "sondern nur die Auflösung des Domainnamens. "
)
B7_TABELLE_ALT = "| GitHub (Hosting); Cloudflare (DNS) |"
B7_TABELLE_NEU = "| GitHub (Hosting); Cloudflare (CDN, Schutz und DNS) |"
B7_DIENSTLEISTER_ALT = "| Cloudflare, Inc. | DNS, Cloudflare Workers, Workers KV, Datenbank |"
B7_DIENSTLEISTER_NEU = "| Cloudflare, Inc. | CDN, Schutz, DNS, Cloudflare Workers, Workers KV, Datenbank |"


class _KeineWeiterleitung(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError(f"Cloudflare-API leitet unerwartet um (HTTP {code}); "
                           "Bearer-Token wird nicht an Umleitungsziele weitergereicht.")


def _ausdruck_norm(text: str) -> str:
    return " ".join(str(text or "").split())


def vorlage_kopfzeilen(text: str | None = None) -> list[tuple[str, str]]:
    """Sollstand der acht Kopfzeilen – EINE Quelle: die Tabelle in
    cloudflare/edge-schutz.md, Abschnitt A1. Nur der A1-Abschnitt zählt –
    die Tabellen der Abschnitte A2/A3 haben dasselbe Aussehen."""
    roh = text if text is not None else VORLAGE.read_text(encoding="utf-8")
    abschnitte = re.split(r"^## ", roh, flags=re.M)
    a1 = next((a for a in abschnitte
               if "A1" in ((a.splitlines() or [""])[0])), "")
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
        "enabled": True,
    }


def regel_abweichungen(regel: dict | None, kopfzeilen: list[tuple[str, str]]) -> list[str]:
    """Prüft die vollständige Wirksamkeit der Transform Rule (WF-E813 / #815):
    aktiviert, richtige Aktion, beide Hosts im Filter, Operation `set` und Werte."""
    if regel is None:
        return [f"Transform Rule „{REGEL}“ fehlt"]
    gruende: list[str] = []
    if regel.get("enabled") is False:
        gruende.append("Regel ist im Dashboard deaktiviert (`enabled: false`)")
    if regel.get("action") != "rewrite":
        gruende.append(f"Aktion ist `{regel.get('action') or '?'}`, soll `rewrite`")
    if _ausdruck_norm(regel.get("expression") or "") != _ausdruck_norm(AUSDRUCK):
        gruende.append("Host-Filter (`expression`) weicht vom Soll für Hauptdomain + www ab")
    parameter = regel.get("action_parameters") or {}
    if not isinstance(parameter, dict):
        gruende.append("Aktionsparameter fehlen oder sind kein Objekt")
        return gruende
    ist = parameter.get("headers") or {}
    if not isinstance(ist, dict):
        gruende.append("Header-Parameter fehlen oder sind kein Objekt")
        return gruende
    soll = dict(kopfzeilen)
    for name, wert in soll.items():
        eintrag = ist.get(name)
        if not isinstance(eintrag, dict):
            gruende.append(f"`{name}` fehlt")
        elif eintrag.get("operation") != "set":
            gruende.append(f"`{name}` hat Operation `{eintrag.get('operation')}`, soll `set`")
        elif str(eintrag.get("value") or "") != wert:
            gruende.append(f"`{name}` hat abweichenden Wert")
    fremd = sorted(set(ist) - set(soll))
    if fremd:
        gruende.append("überzählige Kopfzeilen in derselben Regel: " + ", ".join(fremd))
    return gruende


def regelsatz_abweichungen(regeln: list[dict], kopfzeilen: list[tuple[str, str]]) -> list[str]:
    """Genau eine eigene Regel; Duplikate sind Drift, keine doppelte Absicherung."""
    if len(regeln) != 1:
        return [f"Transform Rule „{REGEL}“ muss genau einmal vorhanden sein; gefunden: {len(regeln)}"]
    return regel_abweichungen(regeln[0], kopfzeilen)


def ssl_bewerten(wert: str) -> tuple[bool, str]:
    """Runbook A1 Schritt 2: `strict` bevorzugt, `full` zulässig, `flexible`/`off` verboten."""
    modus = str(wert or "").strip().lower()
    if modus == "strict":
        return True, "SSL-Modus `strict` (`Full (strict)`, bevorzugter Sollstand)."
    if modus == "full":
        return True, ("SSL-Modus `full` (im Soll; nach aktivem GitHub-Pages-Zertifikat "
                      "kann optional auf `Full (strict)` gehärtet werden).")
    return False, (f"SSL-Modus `{modus or '?'}` ist unsicher – mindestens `full`, "
                   "bevorzugt `strict` (`Full (strict)`), niemals `flexible` oder `off`.")


def ssl_ziel_bestimmen(ist_wert: str, wunsch: str = "full") -> str | None:
    """Kein Downgrade (#815): Ein aktives `strict` bleibt IMMER `strict`.
    Liefert None, wenn keine Änderung nötig ist, sonst den Zielwert für PATCH."""
    ist = str(ist_wert or "").strip().lower()
    ziel = "strict" if str(wunsch or "").strip().lower() == "strict" else "full"
    if ist == "strict":
        return None
    if ist == "full":
        return "strict" if ziel == "strict" else None
    return ziel


def plan_dns(satz: list[dict]) -> list[str]:
    """Welche DNS-Einträge fehlen auf Proxied? (Idempotent, nur Abweichungen.)"""
    offene: list[str] = []
    for eintrag in satz:
        if not eintrag.get("proxied"):
            offene.append(eintrag.get("name") or "?")
    return offene


def dns_eintraege(token: str, zid: str) -> dict[str, list[dict]]:
    """Liest beide Web-Hosts gezielt und vollständig, ohne Mail-DNS anzufassen.

    Eine unselektierte Standardseite der Cloudflare-API kann bei mehr als 20
    Einträgen unvollständig sein. Der exakte Namensfilter vermeidet diese
    Blindstelle; nur A/AAAA/CNAME sind für den HTTP-Proxy relevant.
    """
    ergebnis: dict[str, list[dict]] = {}
    for name in HOSTS:
        weg = f"/zones/{zid}/dns_records?name={urllib.parse.quote(name, safe='')}&per_page=100"
        daten = _resultat(_api(token, weg), f"DNS-Lesung für {name}")
        if not isinstance(daten, list):
            raise RuntimeError(f"DNS-Lesung für {name} hat kein Listenformat.")
        web = [eintrag for eintrag in daten
               if isinstance(eintrag, dict) and eintrag.get("name") == name
               and eintrag.get("type") in WEB_DNS_TYPEN]
        if any(not isinstance(eintrag.get("id"), str) or not eintrag["id"] for eintrag in web):
            raise RuntimeError(f"DNS-Lesung für {name} enthält einen Eintrag ohne eindeutige ID.")
        ergebnis[name] = web
    return ergebnis


# ------------------------------------------------------------------ Datenschutz B7
def datenschutz_b7_offen(text: str) -> list[str]:
    """Welche Vor-Proxy-Aussagen stehen noch in `content/datenschutz/index.md`?"""
    offen: list[str] = []
    if "kein Proxy von Cloudflare" in text:
        offen.append("Abschnitt 3 nennt noch „kein Proxy von Cloudflare“")
    if "keine Informationen über Seitenaufrufe" in text:
        offen.append("Abschnitt 3 nennt noch „keine Informationen über Seitenaufrufe“")
    if B7_TABELLE_ALT in text:
        offen.append("Abschnitt 2 nennt Cloudflare noch ausschließlich als DNS-Empfänger")
    return offen


def datenschutz_b7_anwenden(text: str) -> tuple[str, bool]:
    """Wendet Runbook B7 idempotent auf den Text der Datenschutzerklärung an."""
    neu = text
    if B7_VOR_PROXY_SATZ in neu:
        neu = neu.replace(B7_VOR_PROXY_SATZ, B7_MIT_PROXY_SATZ, 1)
    if B7_DNS_NUR_AUFLOESUNG in neu:
        neu = neu.replace(B7_DNS_NUR_AUFLOESUNG, "", 1)
    if B7_TABELLE_ALT in neu:
        neu = neu.replace(B7_TABELLE_ALT, B7_TABELLE_NEU, 1)
    if B7_DIENSTLEISTER_ALT in neu:
        neu = neu.replace(B7_DIENSTLEISTER_ALT, B7_DIENSTLEISTER_NEU, 1)
    rest = datenschutz_b7_offen(neu)
    if rest:
        raise RuntimeError("Datenschutz-Vorlage hat unerwartetes Format; offen geblieben: "
                           + "; ".join(rest))
    return neu, (neu != text)


def b7_kommando(pfad: Path, *, schreiben: bool) -> tuple[int, str]:
    if not pfad.is_file():
        raise RuntimeError(f"Datenschutzerklärung fehlt: {pfad}")
    text = pfad.read_text(encoding="utf-8")
    if not schreiben:
        offen = datenschutz_b7_offen(text)
        if not offen:
            return 0, ("✅ Datenschutz B7 bereits auf Cloudflare-Proxy umgestellt "
                       f"(`{pfad.relative_to(WURZEL) if pfad.is_relative_to(WURZEL) else pfad}`).")
        zeilen = ["# Datenschutz B7 — Vor-Proxy-Stand aktiv", ""]
        zeilen += [f"- ℹ️ {punkt}" for punkt in offen]
        zeilen += ["", "Sobald der Cloudflare-Proxy eingeschaltet ist: `npm run edge:b7:apply` "
                   "ausführen und committen."]
        return 1, "\n".join(zeilen)
    neu, geaendert = datenschutz_b7_anwenden(text)
    if geaendert:
        pfad.write_text(neu, encoding="utf-8")
        return 0, ("✅ Datenschutz B7 angewendet: Cloudflare-Proxy, Zugriffsdaten und "
                   "Empfänger in `content/datenschutz/index.md` aktualisiert. Bitte committen.")
    return 0, "✅ Datenschutz B7 war bereits eingearbeitet (keine Änderung nötig)."


# ------------------------------------------------------------------ HTTP-API
def _fehler_kurz(roh: str) -> str:
    """Extrahiert nur API-Fehlermeldungen ohne Reflexion von Headern/Tokens."""
    try:
        daten = json.loads(roh)
        fehler = daten.get("errors") if isinstance(daten, dict) else None
        if isinstance(fehler, list) and fehler:
            teile = []
            for eintrag in fehler[:3]:
                if isinstance(eintrag, dict):
                    code = eintrag.get("code", "?")
                    msg = str(eintrag.get("message") or "").replace("\n", " ").strip()[:120]
                    teile.append(f"[{code}] {msg}")
            if teile:
                return "; ".join(teile)
    except ValueError:
        pass
    return "API-Antwort ohne lesbare Fehlerstruktur"


def _api(token: str, weg: str, *, methode: str = "GET", daten=None):
    sauber = (token or "").strip()
    if not sauber or any(ord(z) < 33 or ord(z) > 126 for z in sauber):
        raise RuntimeError("CLOUDFLARE_API_TOKEN hat kein gültiges HTTP-Headerformat.")
    if not weg.startswith("/zones"):
        raise RuntimeError("Sicherheitsgrenze: Dieses Werkzeug darf nur /zones-Pfade aufrufen.")
    koerper = None if daten is None else json.dumps(daten).encode("utf-8")
    anfrage = urllib.request.Request(
        API + weg, data=koerper, method=methode,
        headers={"authorization": f"Bearer {sauber}",
                 "content-type": "application/json",
                 "user-agent": "franksfinanzcheck-edge-freigabe/2.0"})
    opener = urllib.request.build_opener(_KeineWeiterleitung())
    try:
        with opener.open(anfrage, timeout=30) as antwort:
            return json.loads(antwort.read(1_000_000).decode("utf-8"))
    except urllib.error.HTTPError as fehler:
        roh = fehler.read(65_536).decode("utf-8", "replace")
        fehler.close()
        raise RuntimeError(f"API {methode} {weg} → HTTP {fehler.code}: {_fehler_kurz(roh)}") from None
    except (OSError, ValueError) as fehler:
        raise RuntimeError(f"API {methode} {weg} nicht auswertbar ({type(fehler).__name__}).") from None


def _resultat(antwort: dict, was: str):
    if not isinstance(antwort, dict) or not antwort.get("success"):
        roh = json.dumps({"errors": (antwort or {}).get("errors") if isinstance(antwort, dict) else []})
        raise RuntimeError(f"{was} fehlgeschlagen: {_fehler_kurz(roh)}")
    return antwort.get("result")


def zone_id_holen(token: str, zone: str) -> str:
    result = _resultat(_api(token, f"/zones?name={urllib.parse.quote(zone, safe='')}"), "Zonensuche")
    if not isinstance(result, list):
        raise RuntimeError("Zonensuche hat kein Listenformat; keine Ersatz-Zone wird geraten.")
    treffer = [eintrag for eintrag in result
               if isinstance(eintrag, dict) and eintrag.get("name") == zone]
    # Nur die ausdrücklich benannte Zone ist zulässig. Fehlende Namen oder
    # Mehrdeutigkeit sind ein harter Stopp, niemals eine Einladung zum Raten.
    if len(treffer) != 1 or not isinstance(treffer[0].get("id"), str) or not treffer[0]["id"]:
        raise RuntimeError(f"Zone {zone} nicht eindeutig im Konto des Tokens – Rechte prüfen "
                           "(Zone.DNS:Edit für genau diese Zone). Keine Änderung an einer Ersatz-Zone.")
    return treffer[0]["id"]


# ------------------------------------------------------------------ Prüfen
def pruefen(token: str, zone: str) -> tuple[int, str]:
    kopfzeilen = vorlage_kopfzeilen()
    zeilen = [f"# Edge-Freigabe — Ist gegen Soll (Zone {zone})", ""]
    fehlt: list[str] = []
    zid = zone_id_holen(token, zone)
    zeilen.append(f"- ✅ Zone erreichbar (id …{zid[-6:]}).")

    # 1. DNS-Proxy (Runbook A1, Schritt 1; nur Web-Einträge, keine Mail-DNS)
    dns = dns_eintraege(token, zid)
    for name in HOSTS:
        treffer = dns[name]
        if not treffer:
            fehlt.append(f"DNS: kein proxyfähiger A/AAAA/CNAME-Eintrag für {name}")
            zeilen.append(f"- ❌ DNS `{name}`: kein proxyfähiger Web-Eintrag gefunden.")
        elif all(e.get("proxied") is True for e in treffer):
            zeilen.append(f"- ✅ DNS `{name}`: proxied (orange Wolke; {len(treffer)} Web-Einträge).")
        else:
            fehlt.append(f"DNS: {name} nicht vollständig proxied")
            zeilen.append(f"- ❌ DNS `{name}`: **nicht vollständig proxied** – die Transform Rule "
                          "kann nicht zuverlässig wirken (Runbook A1, Schritt 1).")

    # 2. SSL-Modus (Runbook A1, Schritt 2 – `strict` bevorzugt, `full` zulässig)
    ssl = _resultat(_api(token, f"/zones/{zid}/settings/ssl"), "SSL-Lesung")
    if not isinstance(ssl, dict):
        raise RuntimeError("SSL-Lesung hat kein Objektformat; der Modus wird nicht geraten.")
    wert = str(ssl.get("value") or "")
    ssl_ok, ssl_text = ssl_bewerten(wert)
    if ssl_ok:
        zeilen.append(f"- ✅ {ssl_text}")
    else:
        fehlt.append(f"SSL-Modus ist '{wert or 'unbekannt'}', erlaubt: strict oder full")
        zeilen.append(f"- ❌ {ssl_text}")

    # 3. Transform Rule (Runbook A1, Schritt 3 / cloudflare/edge-schutz.md)
    regeln = _regeln_finden(token, zid)
    abweichungen = regelsatz_abweichungen(regeln, kopfzeilen)
    if not abweichungen:
        zeilen.append(f"- ✅ Transform Rule „{REGEL}“ aktiv und vollständig "
                      f"({len(kopfzeilen)} Kopfzeilen + Host-Filter im Soll).")
    else:
        fehlt.append("Transform Rule: " + "; ".join(abweichungen))
        zeilen.append("- ❌ Transform Rule „" + REGEL + "“: " + "; ".join(abweichungen) + ".")

    # 4. Lokaler Datenschutz-Abgleich B7 als Sichtprüfung
    if DATENSCHUTZ.is_file():
        b7_offen = datenschutz_b7_offen(DATENSCHUTZ.read_text(encoding="utf-8"))
        if not fehlt and b7_offen:
            zeilen.append("- ⚠️ **Pflichtschritt B7 offen:** Proxy ist aktiv, aber "
                          "`content/datenschutz/index.md` trägt noch den Vor-Proxy-Text "
                          "(`npm run edge:b7:apply` ausführen und committen).")
        elif not b7_offen:
            zeilen.append("- ✅ Datenschutz B7 in `content/datenschutz/index.md` eingearbeitet.")

    zeilen += ["", f"## Ergebnis: {'IM SOLL' if not fehlt else 'OFFEN'}"]
    if fehlt:
        zeilen += ["", "Nächster Schritt: `npm run edge:freigabe:apply` "
                       "(mit CLOUDFLARE_API_TOKEN) oder Runbook A1 Schritt 1–3 von Hand.",
                   "**Danach zwingend Runbook B7** (`npm run edge:b7:apply` – "
                   "Datenschutz-Text für den Proxy)."]
        return 1, "\n".join(zeilen)
    zeilen += ["", "Danach misst die Sicherheits-Wache (Live-Job) selbst und wird grün."]
    return 0, "\n".join(zeilen)


def _regeln_finden(token: str, zid: str) -> list[dict]:
    try:
        result = _resultat(
            _api(token, f"/zones/{zid}/rulesets/phases/{PHASE}/entrypoint"),
            "Ruleset-Lesung")
    except RuntimeError as fehler:
        if "HTTP 404" in str(fehler):
            return []
        raise
    if not isinstance(result, dict):
        raise RuntimeError("Ruleset-Lesung hat kein Objektformat; fehlende Regel wird nicht geraten.")
    regeln = result.get("rules") or []
    if not isinstance(regeln, list) or not all(isinstance(regel, dict) for regel in regeln):
        raise RuntimeError("Ruleset-Lesung enthält keine gültige Regelliste.")
    return [regel for regel in regeln if regel.get("description") == REGEL]


# ------------------------------------------------------------------ Anwenden
def anwenden(token: str, zone: str, *, ssl_wunsch: str = "full",
             b7: bool = False) -> tuple[int, str]:
    """Stellt A1 in sicherer Reihenfolge her und misst danach erneut.

    Preflight liest DNS, SSL und Ruleset VOR der ersten Änderung. Die Header-
    Regel wird zuerst geschrieben, SSL danach und der öffentliche DNS-Proxy
    erst zuletzt aktiviert. Ein fehlendes Transform-Recht kann so niemals eine
    bereits umgestellte, aber headerlose Website hinterlassen. `b7=True` wird
    erst nach erfolgreicher API-Gegenmessung angewendet (nur CLI --apply).
    """
    kopfzeilen = vorlage_kopfzeilen()
    zeilen = [f"# Edge-Freigabe — kontrollierte Herstellung (Zone {zone})", ""]
    zid = zone_id_holen(token, zone)

    # PREFLIGHT: Alle Ist-Daten und benötigten IDs müssen vor dem ersten Write
    # vorliegen. Fehlende Web-Hosts oder kaputte Antworten ändern nichts.
    dns = dns_eintraege(token, zid)
    fehlende_hosts = [name for name in HOSTS if not dns[name]]
    if fehlende_hosts:
        raise RuntimeError(
            "Preflight ohne Änderung: kein proxyfähiger A/AAAA/CNAME-Eintrag für "
            + ", ".join(fehlende_hosts) + ". DNS zuerst im Dashboard vervollständigen."
        )
    ssl = _resultat(_api(token, f"/zones/{zid}/settings/ssl"), "SSL-Lesung")
    if not isinstance(ssl, dict):
        raise RuntimeError("Preflight ohne Änderung: SSL-Lesung hat kein Objektformat.")
    ist_ssl = str(ssl.get("value") or "")
    ziel_ssl = ssl_ziel_bestimmen(ist_ssl, ssl_wunsch)
    try:
        ruleset = _resultat(
            _api(token, f"/zones/{zid}/rulesets/phases/{PHASE}/entrypoint"),
            "Ruleset-Lesung")
    except RuntimeError as fehler:
        if "HTTP 404" in str(fehler):
            ruleset = None
        else:
            raise
    if ruleset is not None and not isinstance(ruleset, dict):
        raise RuntimeError("Preflight ohne Änderung: Ruleset-Lesung hat kein Objektformat.")
    regeln = (ruleset.get("rules") or []) if isinstance(ruleset, dict) else []
    if not isinstance(regeln, list) or not all(isinstance(regel, dict) for regel in regeln):
        raise RuntimeError("Preflight ohne Änderung: Ruleset enthält keine gültige Regelliste.")
    if ruleset is not None and (not isinstance(ruleset.get("id"), str) or not ruleset["id"]):
        raise RuntimeError("Preflight ohne Änderung: Ruleset-ID fehlt.")
    eigene = [regel for regel in regeln if regel.get("description") == REGEL]
    abweichungen = regelsatz_abweichungen(eigene, kopfzeilen)
    neue_regel = regel_koerper(kopfzeilen)

    # WRITE 1/3: Erst die Schutzregel. Bei fehlendem Recht bleibt DNS unverändert.
    if abweichungen:
        if ruleset is None:
            _resultat(_api(token, f"/zones/{zid}/rulesets", methode="POST",
                           daten={"phase": PHASE, "rules": [neue_regel]}), "Regel anlegen")
            zeilen.append(f"- ✅ Transform Rule „{REGEL}“ zuerst aktiv angelegt "
                          f"({len(kopfzeilen)} Kopfzeilen; DNS noch unverändert).")
        else:
            # Die eigene Regel an ihrer bisherigen Position ersetzen. Dadurch
            # bleibt auch ihre Reihenfolge zu fremden Regeln stabil; Duplikate
            # werden dennoch deterministisch auf genau eine Regel reduziert.
            neue_regeln = []
            ersetzt = False
            for regel in regeln:
                if regel.get("description") != REGEL:
                    neue_regeln.append(regel)
                elif not ersetzt:
                    neue_regeln.append(neue_regel)
                    ersetzt = True
            if not ersetzt:
                neue_regeln.append(neue_regel)
            bestand_anzahl = len(regeln) - len(eigene)
            _resultat(_api(token, f"/zones/{zid}/rulesets/{ruleset['id']}", methode="PUT",
                           daten={"rules": neue_regeln}), "Regel ersetzen")
            zeilen.append(f"- ✅ Transform Rule „{REGEL}“ zuerst gesetzt/aktualisiert "
                          f"({len(kopfzeilen)} Kopfzeilen, {bestand_anzahl} andere Regeln "
                          "mit stabiler Reihenfolge).")
    else:
        zeilen.append(f"- ✅ Transform Rule „{REGEL}“ bereits vollständig (kein Rewrite nötig).")

    # WRITE 2/3: Sicherer Ursprungsmodus; strict wird niemals herabgestuft.
    if ziel_ssl is not None:
        _resultat(_api(token, f"/zones/{zid}/settings/ssl",
                       methode="PATCH", daten={"value": ziel_ssl}), "SSL-Modus")
        zeilen.append(f"- ✅ SSL-Modus `{ist_ssl or '?'}` → `{ziel_ssl}`.")
    else:
        zeilen.append(f"- ✅ SSL-Modus bereits `{ist_ssl}` (kein Downgrade, keine Änderung nötig).")

    # WRITE 3/3: Erst jetzt öffentlichen Verkehr durch den geschützten Proxy führen.
    dns_geaendert = 0
    for name in HOSTS:
        for eintrag in dns[name]:
            if eintrag.get("proxied") is not True:
                _resultat(_api(token, f"/zones/{zid}/dns_records/{eintrag['id']}",
                               methode="PATCH", daten={"proxied": True}), f"DNS-Proxy für {name}")
                dns_geaendert += 1
    zeilen.append(f"- ✅ DNS-Proxy zuletzt geprüft/hergestellt ({dns_geaendert} Web-Einträge geändert; "
                  "Mail-/Sonstigeinträge unangetastet).")

    # GEGENMESSUNG: Kein HERGESTELLT allein aufgrund erfolgreicher Write-Calls.
    pruefcode, nachweis = pruefen(token, zone)
    zeilen += ["", "## API-Gegenmessung", "", nachweis]
    if pruefcode != 0:
        zeilen += ["", "## Ergebnis: NICHT VOLLSTÄNDIG – Live-Wache und #815 bleiben offen."]
        return pruefcode, "\n".join(zeilen)

    if b7:
        b7code, b7bericht = b7_kommando(DATENSCHUTZ, schreiben=True)
        zeilen += ["", "## Datenschutz B7", "", b7bericht]
        if b7code != 0:
            return b7code, "\n".join(zeilen)
        zeilen.append("Die aktualisierte Datenschutzerklärung muss noch committed und auf `main` veröffentlicht werden.")

    zeilen += ["", "## Ergebnis: API-SOLL NACHGEWIESEN",
               "", "Abschließend muss die unabhängige Live-Wache beide Säulen "
               "(F-01 und Worker-Zustand) vollständig messen; erst ihr Erfolg darf #815 schließen."]
    return 0, "\n".join(zeilen)


# ------------------------------------------------------------------ Selbsttest
def selftest() -> int:
    faelle = 0
    kopfzeilen = vorlage_kopfzeilen()
    namen = [n for n, _ in kopfzeilen]
    # 1. Die Vorlage ist die Quelle des Solls – acht Kopfzeilen.
    assert len(kopfzeilen) == 8, f"8 Kopfzeilen erwartet, {len(kopfzeilen)} gefunden: {namen}"
    for pflicht in ("Strict-Transport-Security", "X-Content-Type-Options",
                    "X-Frame-Options", "Content-Security-Policy"):
        assert pflicht in namen, f"Pflichtkopfzeile fehlt in der Vorlage: {pflicht}"
    faelle += 1

    # 2. Kreuzbeweis (#815): Was dieses Werkzeug setzt, MUSS die Live-Header-Wache
    #    (blog_header_gate.befunde_fuer) mit 0 Fehlern UND 0 Warnungen bestehen.
    if str(WURZEL / "scripts") not in sys.path:
        sys.path.insert(0, str(WURZEL / "scripts"))
    import blog_header_gate
    fehlend, warnungen, _ = blog_header_gate.befunde_fuer(
        {name.lower(): wert for name, wert in kopfzeilen}
    )
    assert fehlend == [] and warnungen == [], (
        f"Vorlage und blog_header_gate driften auseinander: fehlend={fehlend}, warnungen={warnungen}"
    )
    faelle += 1

    # 3. Regelkörper und vollständige Abweichungsprüfung (enabled, expression, operation).
    koerper = regel_koerper(kopfzeilen)
    assert koerper["description"] == REGEL and koerper["enabled"] is True
    assert koerper["expression"] == AUSDRUCK
    assert regel_abweichungen(koerper, kopfzeilen) == []
    assert any("deaktiviert" in x for x in regel_abweichungen({**koerper, "enabled": False}, kopfzeilen))
    assert any("Host-Filter" in x for x in regel_abweichungen(
        {**koerper, "expression": '(http.host eq "franksfinanzcheck.de")'}, kopfzeilen))
    kaputt_op = json.loads(json.dumps(koerper))
    kaputt_op["action_parameters"]["headers"]["X-Frame-Options"]["operation"] = "add"
    assert any("Operation" in x for x in regel_abweichungen(kaputt_op, kopfzeilen))
    faelle += 1

    # 4. SSL-Bewertung & Downgrade-Sperre (#815): `strict` ist gültig und wird nie
    #    auf `full` herabgestuft; `flexible`/`off` werden abgelehnt und angehoben.
    assert ssl_bewerten("strict")[0] is True
    assert ssl_bewerten("full")[0] is True
    assert ssl_bewerten("flexible")[0] is False
    assert ssl_bewerten("off")[0] is False
    assert ssl_ziel_bestimmen("strict", "full") is None, "strict darf niemals auf full fallen"
    assert ssl_ziel_bestimmen("full", "full") is None
    assert ssl_ziel_bestimmen("full", "strict") == "strict"
    assert ssl_ziel_bestimmen("flexible", "full") == "full"
    faelle += 1

    # 5. DNS-Plan: nur Abweichungen, idempotent.
    assert plan_dns([{"name": "franksfinanzcheck.de", "proxied": True},
                     {"name": "www.franksfinanzcheck.de", "proxied": True}]) == []
    ab = plan_dns([{"name": "franksfinanzcheck.de", "proxied": False}])
    assert ab == ["franksfinanzcheck.de"], ab
    faelle += 1

    # 6. Nur die A1-Tabelle zählt (keine Verunreinigung aus A2/A3).
    gemischt = ("## 1. A1 — Sicherheits-Header (Finding F-01)\n\n"
                "| Kopfzeile | Wert |\n|---|---|\n| `X-Test` | `wert` |\n\n"
                "## 2. A2 — Mengenregeln (Finding F-03)\n\n"
                "| Name | Ausdruck (Filter) |\n|---|---|\n"
                "| `FF Anmeldung/Tor` | `(http.host eq \"abos.example\")` |\n")
    assert vorlage_kopfzeilen(gemischt) == [("X-Test", "wert")], vorlage_kopfzeilen(gemischt)
    faelle += 1

    # 7. B7-Datenschutz-Transformation (C15-sauber im Temp-Verzeichnis, idempotent).
    if DATENSCHUTZ.is_file():
        original = DATENSCHUTZ.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            kopie = Path(tmp) / "datenschutz.md"
            kopie.write_text(original, encoding="utf-8")
            code1, _ = b7_kommando(kopie, schreiben=True)
            code2, _ = b7_kommando(kopie, schreiben=False)
            code3, _ = b7_kommando(kopie, schreiben=True)
            inhalt = kopie.read_text(encoding="utf-8")
            assert code1 == 0 and code2 == 0 and code3 == 0
            assert datenschutz_b7_offen(inhalt) == []
            assert "Cloudflare-CDN" not in inhalt, "Vertrag test_datenschutz_freigabe verletzt"
        faelle += 1

    print(f"✅ SELBSTTEST OK — {faelle} Fälle grün (Vorlage {VORLAGE.name}: "
          f"{len(kopfzeilen)} Kopfzeilen = 0 Wachen-Befunde, SSL-Downgrade-Sperre, "
          f"Regel-Vollprüfung, B7-Automatik).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Cloudflare Edge-Freigabe: Runbook A1 + B7 prüfen/herstellen (WF-E813 / #815).")
    parser.add_argument("--selftest", action="store_true", help="prüft die Prüfung (ohne Netz)")
    parser.add_argument("--pruefen", action="store_true",
                        help="nur messen (Standard; schreibt nichts)")
    parser.add_argument("--apply", action="store_true",
                        help="Sollstand herstellen (schreibt; Standard liest nur)")
    parser.add_argument("--ssl", choices=("full", "strict"), default="full",
                        help="Mindest-SSL-Modus bei --apply (bestehendes strict bleibt immer strict)")
    parser.add_argument("--b7-check", action="store_true",
                        help="prüft lokal, ob content/datenschutz/index.md auf Proxy (B7) steht")
    parser.add_argument("--b7-apply", action="store_true",
                        help="stellt content/datenschutz/index.md idempotent auf Proxy (B7) um")
    parser.add_argument("--zone", default=os.environ.get("CLOUDFLARE_ZONE", "franksfinanzcheck.de"))
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    if args.b7_check or args.b7_apply:
        try:
            code, bericht = b7_kommando(DATENSCHUTZ, schreiben=bool(args.b7_apply))
        except (RuntimeError, OSError) as fehler:
            print(f"❌ B7-Werkzeugfehler: {fehler}", file=sys.stderr)
            return 2
        print(bericht)
        return code

    token = os.environ.get("CLOUDFLARE_API_TOKEN") or ""
    if not token.strip():
        print("❌ CLOUDFLARE_API_TOKEN fehlt – ohne Token ist nichts gemessen "
              "(und nichts behauptet). Token mit Zone.DNS:Edit, Zone.Settings:Edit, "
              "Zone.Transform Rules:Edit für diese Zone.", file=sys.stderr)
        return 2
    try:
        funktion = anwenden if args.apply else pruefen
        code, bericht = (funktion(token, args.zone.strip(), ssl_wunsch=args.ssl, b7=True)
                         if args.apply else funktion(token, args.zone.strip()))
    except (RuntimeError, OSError) as fehler:
        print(f"❌ Werkzeugfehler oder unvollständiger Lauf: {fehler} "
              "Bei --apply können einzelne sichere Teilschritte bereits ausgeführt sein; "
              "Ist-Zustand mit --pruefen erneut messen, nichts auf Verdacht ändern.", file=sys.stderr)
        return 2
    print(bericht)
    return code


if __name__ == "__main__":
    sys.exit(main())
