#!/usr/bin/env python3
"""blog_header_gate.py — Sicherheits-Header der ausgelieferten Seite prüfen (F-01).

Warum diese Wache existiert
--------------------------
Die Seite liegt auf GitHub Pages, und **GitHub Pages ignoriert
`static/_headers`**. Das steht als Kommentar in der Datei selbst — und ist der
Grund, warum live jahrelang HSTS, `X-Frame-Options` und `nosniff` fehlten:
Der Blog war in fremde Seiten einbettbar (Clickjacking auf „Jetzt anmelden“),
und der erste Aufruf über `http://` blieb ungeschützt.

Seit 15.10.2026 soll die Zone hinter Cloudflare liegen; die Header sind in
einer **Transform Rule** beschrieben (`cloudflare/edge-schutz.md`, Abschnitt A1). Diese
Wache prüft die Wirkung, nicht die Absicht: Sie holt die Startseite und eine
Unterseite und vergleicht die Kopfzeilen mit dem Soll.

Bauarten
--------
  --selftest   prüft die Prüfung (feste Fälle, kein Netz)  → in CI vor dem Lauf
  --offline    prüft nur die Konfigurationsdateien (Repo-Stand)
  (Vorgabe)    fragt die echte Seite ab (Netz nötig)

Ausgabe: Markdown-Bericht, Exit-Code nach Klasse (siehe unten). Optionale
Header (Permissions-Policy, COOP/CORP) werden gemeldet, aber nicht erzwungen —
sie sind Härtung, kein Muss.

EIN MELDER DARF NICHT RATEN, WAS ER GEMESSEN HAT (Dauerheilung WF-E813,
15.10.2026)
------------------------------------------------------------------------
Der erste planmäßige Live-Lauf der Sicherheits-Wache (15.10.2026, 11:11 UTC)
wurde rot — und die automatische Meldung nannte als „häufigste Ursache“ einen
abgelaufenen API-Schlüssel. Diese Wache kennt keinen Schlüssel: Sie misst
Kopfzeilen. Schlimmer war der zweite Fehler derselben Zeile: **Jede
Netzstörung landete in der Liste der fehlenden Pflicht-Header.** Eine
abgebrochene TLS-Verbindung wurde damit zu „❌ Pflicht-Header fehlen oder sind
falsch“ umgedeutet — obwohl im selben Satz daneben stand, dass ohne Messung
der Stand *ungeprüft* gilt. Ungeprüft ist aber nicht dasselbe wie fehlend, und
ein Melder, der eine Nicht-Messung als Befund ausgibt, produziert genau die
Alarm-Müdigkeit, die er verhindern soll (Governance-Vertrag C4).

Seitdem unterscheidet diese Wache vier Klassen und benennt die Ursache:

    OK          alle Ziele gemessen, kein Pflicht-Fehler          → Exit 0
    TEILWEISE   ein Ziel gemessen und sauber, ein Ziel nicht      → Exit 0
                erreichbar. Die Transform Rule aus A1 gilt je
                Host, nicht je Pfad – ein sauber gemessenes Ziel
                auf dem Host belegt die Regel. Das nicht
                erreichbare Ziel wird ausdrücklich als
                „nicht gemessen“ geführt, nie als „in Ordnung“.
    BEFUND      ein erreichbares Ziel verfehlt das Soll           → Exit 1
    STOERUNG    kein einziges Ziel messbar                        → Exit 2
                (KEIN Header-Befund, sondern eine nicht
                durchgeführte Messung)

Transiente Netzfehler heilt die Wache selbst: bis zu vier Versuche mit
ansteigender Pause (2 s, 8 s, 30 s), und antwortet ein Proxy auf `HEAD` mit
einem Fehlerstatus, wird einmal per `GET` nachgefragt, bevor daraus ein Befund
gebaut wird. Erst was danach noch rot ist, ist ein Befund.

Zusätzlich nennt der Bericht die **Diagnose**, nicht nur das Symptom: Fehlt
`cf-ray`/`server: cloudflare`, liegt die Zone nicht hinter dem Proxy — dann
kann die Regel aus A1 gar nicht wirken und der nächste Schritt ist das
Dashboard (Runbook A1, Schritt 1), nicht die Regel selbst.
"""

from __future__ import annotations

import argparse
from http.client import HTTPException
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]

# ------------------------------------------------------------------ Exit-Codes
# Bewusst mehr als „rot oder grün“: Der Auswerteschritt im Workflow entscheidet
# anhand dieser Codes, WAS er meldet (Vertrag C34 – Auswertung statt
# Durchreichen). Ein Mess-Schritt, der nur 0 oder 1 kennt, zwingt den Melder
# zur Lüge.
EXIT_OK = 0
EXIT_BEFUND = 1
EXIT_STOERUNG = 2
EXIT_WACHE = 3

KLASSE_OK = "OK"
KLASSE_TEILWEISE = "TEILWEISE"
KLASSE_BEFUND = "BEFUND"
KLASSE_STOERUNG = "STOERUNG"

PROXY_AKTIV = "PROXY_AKTIV"
PROXY_FEHLT = "PROXY_FEHLT"
PROXY_UNBEKANNT = "PROXY_UNBEKANNT"

# Muss in der Antwort stehen (Finding F-01) — Name: (Muster, Begründung)
PFLICHT: dict[str, tuple[str, str]] = {
    "strict-transport-security": (
        r"max-age=\d{6,}",
        "Erzwingt HTTPS beim ersten Aufruf (HSTS) – nur ein Header kann das, "
        "die Meta-Angaben im HTML nicht."),
    "x-content-type-options": (
        r"nosniff",
        "Verhindert, dass der Browser eine Datei als Skript deutet, die keine ist."),
    "x-frame-options": (
        r"(?i)^(deny|sameorigin)$",
        "Kein Einbetten in fremde Seiten – sonst wäre „Jetzt anmelden“ in einem "
        "unsichtbaren Frame klickbar (Clickjacking)."),
    "referrer-policy": (
        r"(?i)strict-origin|no-referrer",
        "Keine vollen Adressen an fremde Seiten (Leak von Filtern/Parametern)."),
    "content-security-policy": (
        r"default-src",
        "Grundregel gegen eingeschleuste Skripte; ergänzt die Meta-CSP um "
        "frame-ancestors und form-action (im <meta> nicht möglich)."),
}

# Soll-Werte: geprüft wird die Anwesenheit ganzer Anweisungen.
CSP_SOLL = [
    "default-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "frame-ancestors 'none'",
]
CSP_SOLL_FRAME_SRC = "frame-src https://challenges.cloudflare.com"
CSP_SOLL_FORM_ACTION = "form-action 'self' https://abos.franksfinanzcheck.de"

# Für die Menschen: empfohlen, nicht erzwungen.
OPTIONAL = {
    "permissions-policy": "Schaltet Geräte-Schnittstellen ab (Kamera, Mikrofon, Ort).",
    "cross-origin-opener-policy": "Trennt Fensterkontexte (Spectre-Klasse).",
    "cross-origin-resource-policy": "Verhindert Fremdeinbettung von Dateien.",
}

# Wo wird geprüft? Startseite und eine Inhaltsseite – Content-Type und Pfad
# unterscheiden sich, die Header dürfen das nicht.
ZIELE = ["https://franksfinanzcheck.de/", "https://franksfinanzcheck.de/methodik/"]

MIN_HSTS_JAHR = 31_536_000

# Selbstheilung gegen transiente Netzstörungen (WF-E813): erst nach vier
# Versuchen über gut 40 Sekunden gilt eine Messung als gescheitert. Ein
# einzelner TLS-Abbruch – genau der Fehler, der am 15.10.2026 den Alarm
# ausgelöst hat – heilt damit im Lauf, statt Frank zu wecken.
PAUSEN = (2.0, 8.0, 30.0)
ZEITLIMIT = 20.0

# Kopfzeilen, mit denen Cloudflare eine proxied Zone kennzeichnet.
PROXY_SPUREN = ("cf-ray", "cf-cache-status", "cf-ray-id")


def kopfzeilen_holen(url: str, weg: str = "HEAD", *,
                     timeout: float = ZEITLIMIT) -> tuple[int, dict[str, str]]:
    """HTTP-Anfrage; folgt Weiterleitungen und sammelt die letzten Kopfzeilen."""
    anfrage = urllib.request.Request(url, method=weg, headers={
        "user-agent": "franksfinanzcheck-header-wache/1.0 (+https://franksfinanzcheck.de/)",
        "accept": "text/html",
    })
    try:
        with urllib.request.urlopen(anfrage, timeout=timeout) as antwort:
            return antwort.status, {k.lower(): v for k, v in antwort.headers.items()}
    except urllib.error.HTTPError as fehler:
        return fehler.code, {k.lower(): v for k, v in (fehler.headers or {}).items()}


def proxy_lage(kopf: dict[str, str]) -> str:
    """Liegt die Zone hinter Cloudflare? Ohne Proxy kann A1 gar nicht wirken.

    Das ist der Unterschied zwischen „die Regel ist falsch eingestellt“ und
    „die Regel kann nicht wirken“ – zwei Befunde mit zwei völlig verschiedenen
    nächsten Schritten. Wer nur das Symptom meldet, schickt den Menschen auf
    die Suche.
    """
    if not kopf:
        return PROXY_UNBEKANNT
    if any(kopf.get(spur) for spur in PROXY_SPUREN):
        return PROXY_AKTIV
    if "cloudflare" in (kopf.get("server") or "").lower():
        return PROXY_AKTIV
    return PROXY_FEHLT


def befunde_fuer(kopf: dict[str, str]) -> tuple[list[str], list[str], list[str]]:
    """Soll/Ist-Vergleich. Gibt (fehlend, warnungen, vorhanden) zurück."""
    fehlend: list[str] = []
    warnungen: list[str] = []
    vorhanden: list[str] = []
    for name, (muster, begruendung) in PFLICHT.items():
        wert = kopf.get(name)
        if not wert:
            fehlend.append(f"**{name}** fehlt — {begruendung}")
            continue
        if not re.search(muster, wert):
            fehlend.append(f"**{name}** ist gesetzt, entspricht aber nicht dem Soll "
                           f"(`{muster}`): `{wert[:120]}` — {begruendung}")
            continue
        vorhanden.append(f"{name}: {wert[:160]}")
    csp = kopf.get("content-security-policy", "")
    if csp:
        for anweisung in CSP_SOLL:
            if anweisung not in csp:
                fehlend.append(f"CSP ohne `{anweisung}` — die Regel aus "
                               f"cloudflare/edge-schutz.md ist unvollständig.")
        if CSP_SOLL_FRAME_SRC not in csp:
            warnungen.append("CSP ohne `frame-src https://challenges.cloudflare.com` — "
                             "das Turnstile-Widget erscheint dann nicht (Anmeldung "
                             "scheitert ohne Bot-Schutz).")
        if CSP_SOLL_FORM_ACTION not in csp:
            warnungen.append("CSP ohne `form-action 'self' https://abos.franksfinanzcheck.de` — "
                             "das Anmeldeformular wird dann vom Browser blockiert.")
        if re.search(r"script-src[^;]*'unsafe-eval'", csp):
            fehlend.append("CSP erlaubt `'unsafe-eval'` — Skripte dürfen dann Code aus "
                           "Daten erzeugen; das gehört nicht in diese Seite.")
    for name, warum in OPTIONAL.items():
        if not kopf.get(name):
            warnungen.append(f"`{name}` fehlt (empfohlen): {warum}")
    return fehlend, warnungen, vorhanden


def ziel_messen(url: str, *, holen=kopfzeilen_holen, pausen=PAUSEN,
                schlaf=time.sleep) -> dict:
    """Misst EIN Ziel mit Selbstheilung.

    Transiente Fehler (TLS-Abbruch, DNS-Schluckauf, kurzer 5xx) werden
    wiederholt; antwortet die Kante auf `HEAD` mit einem Fehlerstatus, wird
    einmal per `GET` nachgefragt, weil manche Proxys `HEAD` anders behandeln
    als `GET` – ohne diese Gegenprobe würde aus einem Proxy-Verhalten ein
    Sicherheitsbefund gebaut.
    """
    protokoll: list[str] = []
    letzter_fehler = "unbekannt"
    for nr in range(len(pausen) + 1):
        if nr:
            schlaf(pausen[nr - 1])
        for weg in ("HEAD", "GET"):
            try:
                status, kopf = holen(url, weg)
            except (OSError, HTTPException) as fehler:
                letzter_fehler = f"{type(fehler).__name__}: {fehler}"
                protokoll.append(f"Versuch {nr + 1} · {weg}: {letzter_fehler}")
                continue
            if status >= 400 and weg == "HEAD":
                protokoll.append(f"Versuch {nr + 1} · HEAD: HTTP {status} "
                                 "– per GET nachgefragt")
                continue
            if not 200 <= status < 300:
                # Eine Fehler-/Challenge-Seite ist kein Nachweis für die
                # Sicherheits-Header der Website (#809). Auch GET-5xx/429
                # müssen erneut gemessen werden, nicht zu BEFUND werden.
                letzter_fehler = f"HTTP {status} – keine erfolgreiche Seitenantwort"
                protokoll.append(f"Versuch {nr + 1} · {weg}: {letzter_fehler}")
                continue
            return {
                "url": url, "status": status, "weg": weg, "kopf": kopf,
                "klasse": "GEMESSEN", "versuche": nr + 1, "protokoll": protokoll,
                "fehler": "", "proxy": proxy_lage(kopf),
            }
    return {
        "url": url, "status": None, "weg": None, "kopf": {},
        "klasse": "STOERUNG", "versuche": len(pausen) + 1, "protokoll": protokoll,
        "fehler": letzter_fehler, "proxy": PROXY_UNBEKANNT,
    }


def naechster_schritt(klasse: str, proxy: str) -> str:
    """Der eine Satz, der Frank wirklich weiterhilft – je Klasse ein anderer."""
    if klasse == KLASSE_STOERUNG:
        return ("Erreichbarkeit der Seite prüfen "
                "(`curl -sI https://franksfinanzcheck.de/`), danach den Lauf neu "
                "starten. Kein Eingriff in Cloudflare nötig – es wurde nichts "
                "gemessen, also auch keine Lücke belegt.")
    if klasse == KLASSE_BEFUND:
        if proxy == PROXY_FEHLT:
            return ("docs/SICHERHEIT-BETRIEB-RUNBOOK.md → A1 Schritt 1: die Zone "
                    "franksfinanzcheck.de in Cloudflare auf *Proxied* (orange Wolke) "
                    "stellen, Schritt 2 (SSL-Modus `Full (strict)` oder `Full`, "
                    "niemals `Flexible`), danach Schritt 3 "
                    "(Transform Rule aus cloudflare/edge-schutz.md). Ohne Proxy "
                    "kann die Regel nicht wirken.")
        if proxy == PROXY_AKTIV:
            return ("cloudflare/edge-schutz.md → Abschnitt A1: die Regel "
                    "`FF Sicherheits-Header` prüfen (alle acht Kopfzeilen, Filter "
                    "auf beide Hosts). Der Proxy ist aktiv, die Regel ist also "
                    "unvollständig oder überschrieben.")
        return ("cloudflare/edge-schutz.md → Abschnitt A1 abgleichen; die "
                "Zusammenfassung nennt die fehlenden Kopfzeilen einzeln.")
    if klasse == KLASSE_TEILWEISE:
        return ("Nichts zu tun am Edge – der gemessene Teil belegt die Regel. Beim "
                "nächsten Lauf werden die nicht erreichbaren Ziele erneut gemessen.")
    return ""


def offline_pruefen() -> tuple[int, str]:
    """Ohne Netz: Prüft, dass Vorlage und Wachen zusammenpassen."""
    zeilen: list[str] = ["# Sicherheits-Header — Repo-Prüfung (offline)", ""]
    fehler: list[str] = []
    vorlage = WURZEL / "cloudflare" / "edge-schutz.md"
    text = vorlage.read_text(encoding="utf-8") if vorlage.exists() else ""
    if not text:
        fehler.append("`cloudflare/edge-schutz.md` fehlt — ohne die Vorlage weiß "
                      "niemand, welche Regel im Dashboard liegen muss.")
    klein = text.lower()
    for name in PFLICHT:
        if name not in klein:
            fehler.append(f"`{name}` steht nicht in der Header-Vorlage.")
    for anweisung in CSP_SOLL + [CSP_SOLL_FRAME_SRC, CSP_SOLL_FORM_ACTION]:
        if anweisung not in text:
            fehler.append(f"CSP-Anweisung `{anweisung}` fehlt in der Vorlage.")
    # Die Meta-CSP im Layout darf nicht behaupten, was sie nicht kann.
    head = WURZEL / "layouts" / "_partials" / "head.html"
    if head.exists():
        h = head.read_text(encoding="utf-8")
        # Nur die Wirkung zählt: der Inhalt der Meta-CSP. Ein Kommentar, der
        # erklärt, dass `frame-ancestors` NUR als Header wirkt, ist richtig
        # und darf die Wache nicht auslösen.
        meta = re.search(r'http-equiv="Content-Security-Policy"\s+content="([^"]*)"', h)
        inhalt = (meta.group(1) if meta else "")
        for wirkungslos in ("frame-ancestors", "strict-transport-security", "x-frame-options"):
            if wirkungslos in inhalt:
                fehler.append(f"Meta-CSP in head.html nennt `{wirkungslos}` — im "
                              "`<meta>`-Tag ist das wirkungslos und suggeriert Schutz, "
                              "den nur der HTTP-Header liefert.")
        # Die Meta-CSP muss die wirksamen Teile weiterhin tragen: Sie ist die
        # einzige CSP, wenn Cloudflare ausfällt (Ausfall heißt nicht schutzlos).
        for pflicht in ("base-uri 'self'", "object-src 'none'", "form-action 'self'"):
            if pflicht not in inhalt:
                fehler.append(f"Meta-CSP ohne `{pflicht}` — dieser Teil ist per "
                              "<meta> wirksam und darf nicht verschwinden.")
    if fehler:
        zeilen += ["## Befunde", ""] + [f"- ❌ {f}" for f in fehler]
        return 1, "\n".join(zeilen)
    zeilen.append("✅ Header-Vorlage vollständig, Meta-CSP ohne Scheinschutz, "
                  "Wachen-Regeln deckungsgleich.")
    return 0, "\n".join(zeilen)


def netz_pruefen(*, holen=kopfzeilen_holen, pausen=PAUSEN, schlaf=time.sleep,
                 ziele: list[str] | None = None) -> tuple[int, str, dict]:
    """Misst alle Ziele und klassifiziert das Ergebnis.

    Die Unterscheidung ist der Kern der Dauerheilung WF-E813: Eine
    Nicht-Messung (STOERUNG) wird nie als fehlender Header gemeldet, und ein
    echter Befund wird nie von einem nicht erreichbaren Zweitziel verdeckt.
    """
    ziele = list(ziele if ziele is not None else ZIELE)
    messungen = [ziel_messen(z, holen=holen, pausen=pausen, schlaf=schlaf) for z in ziele]

    fehlend_gesamt: list[str] = []
    warnungen_gesamt: list[str] = []
    stoerung_gesamt: list[str] = []
    nicht_gemessen: list[str] = []

    zeilen = ["# Sicherheits-Header — Live-Prüfung", ""]

    for m in messungen:
        if m["klasse"] != "GEMESSEN":
            nicht_gemessen.append(m["url"])
            stoerung_gesamt.append(
                f"`{m['url']}` war nach {m['versuche']} Versuchen nicht messbar "
                f"({m['fehler']})")
            zeilen.append(f"## {m['url']} — nicht messbar")
            zeilen.append("")
            zeilen.append(f"- ⚠️ **Keine Messung.** {m['fehler']}")
            for eintrag in m["protokoll"]:
                zeilen.append(f"  - {eintrag}")
            zeilen.append("")
            continue

        fehlend, warnungen, vorhanden = befunde_fuer(m["kopf"])
        m["fehlend"] = fehlend
        m["warnungen"] = warnungen
        m["vorhanden"] = vorhanden
        zeilen.append(f"## {m['url']} (HTTP {m['status']}, via {m['weg']}, "
                      f"Versuch {m['versuche']})")
        zeilen.append("")
        for z in vorhanden:
            zeilen.append(f"- ✅ `{z}`")
        for z in fehlend:
            zeilen.append(f"- ❌ {z}")
        for z in warnungen:
            zeilen.append(f"- ⚠️ {z}")
        zeilen.append("")
        fehlend_gesamt += [f"`{m['url']}`: {f}" for f in fehlend]
        warnungen_gesamt += [f"`{m['url']}`: {w}" for w in warnungen]

    gemessen = [m for m in messungen if m["klasse"] == "GEMESSEN"]
    lagen = {m["proxy"] for m in gemessen}
    if PROXY_AKTIV in lagen:
        proxy = PROXY_AKTIV
    elif lagen == {PROXY_FEHLT}:
        proxy = PROXY_FEHLT
    elif lagen:
        proxy = PROXY_UNBEKANNT
    else:
        proxy = PROXY_UNBEKANNT

    if not gemessen:
        klasse = KLASSE_STOERUNG
        code = EXIT_STOERUNG
    elif fehlend_gesamt:
        klasse = KLASSE_BEFUND
        code = EXIT_BEFUND
    elif nicht_gemessen:
        klasse = KLASSE_TEILWEISE
        code = EXIT_OK
    else:
        klasse = KLASSE_OK
        code = EXIT_OK

    zeilen.append("## Ergebnis")
    zeilen.append("")
    if klasse == KLASSE_STOERUNG:
        zeilen.append(f"❌ **STOERUNG — {len(nicht_gemessen)} von {len(ziele)} Zielen "
                      "nicht messbar.**")
        zeilen.append("")
        zeilen.append("Das ist **kein Header-Befund**: Ohne Antwort lässt sich weder "
                      "Schutz noch Lücke belegen. Der Stand gilt als **ungeprüft** — "
                      "nicht als sicher und nicht als unsicher. Deshalb ist dieser "
                      "Lauf rot: Eine ausgefallene Sicherheitsmessung darf nicht "
                      "still verschwinden.")
    elif klasse == KLASSE_BEFUND:
        zeilen.append(f"❌ **BEFUND — {len(fehlend_gesamt)} Pflicht-Header fehlen oder "
                      "sind falsch.**")
        zeilen.append("")
        zeilen.append(f"**Diagnose:** {_proxy_satz(proxy)}")
        for f in fehlend_gesamt:
            zeilen.append(f"  - {f}")
    else:
        if klasse == KLASSE_TEILWEISE:
            zeilen.append(f"⚠️ **TEILWEISE geprüft** — {len(gemessen)} von "
                          f"{len(ziele)} Zielen gemessen, alle im Sollbereich.")
            zeilen.append("")
            zeilen.append("Die Transform Rule aus A1 gilt je **Host**, nicht je Pfad: "
                          "Ein sauber gemessenes Ziel belegt die Regel für die Zone. "
                          "Die folgenden Ziele wurden ausdrücklich **nicht** gemessen "
                          "und sind damit nicht als „in Ordnung“ belegt:")
            for url in nicht_gemessen:
                zeilen.append(f"  - {url}")
        else:
            zeilen.append(f"✅ Alle Pflicht-Header vorhanden und im Sollbereich "
                          f"({len(gemessen)} von {len(ziele)} Zielen gemessen).")
        if warnungen_gesamt:
            zeilen.append(f"⚠️ {len(warnungen_gesamt)} Hinweise (Härtung, kein Fehler).")

    schritt = naechster_schritt(klasse, proxy)
    if schritt:
        zeilen.append("")
        zeilen.append(f"**Nächster Schritt:** {schritt}")

    daten = {
        "exit": code,
        "klasse": klasse,
        "proxy": proxy,
        "gemessen": len(gemessen),
        "nicht_gemessen": nicht_gemessen,
        "fehlend": fehlend_gesamt,
        "warnungen": warnungen_gesamt,
        "stoerung": stoerung_gesamt,
        "naechster_schritt": schritt,
        # Keine Cookies/sonstigen Roh-Header in öffentliche Messartefakte.
        "ziele": [{**m, "kopf": {k: v for k, v in m["kopf"].items()
                                 if k in PFLICHT or k in OPTIONAL
                                 or k in PROXY_SPUREN or k == "server"}}
                  for m in messungen],
    }
    return code, "\n".join(zeilen), daten


def _proxy_satz(proxy: str) -> str:
    if proxy == PROXY_FEHLT:
        return ("Die Antwort kommt ohne `cf-ray` und ohne `server: cloudflare` — die "
                "Zone liegt **nicht** hinter dem Cloudflare-Proxy. Die Transform Rule "
                "aus A1 kann deshalb gar nicht wirken, ganz gleich wie sie "
                "eingestellt ist.")
    if proxy == PROXY_AKTIV:
        return ("Der Proxy ist **aktiv** (`cf-ray` vorhanden), aber die Regel liefert "
                "nicht das Soll. Es handelt sich um eine unvollständige oder "
                "überschriebene Transform Rule, nicht um einen fehlenden Proxy.")
    return ("Die Proxy-Lage war nicht eindeutig zu bestimmen — bitte beide Fälle "
            "aus `cloudflare/edge-schutz.md`, Abschnitt A1 durchgehen.")


# ------------------------------------------------------------------ Selbsttest
GUTE_KOPFZEILEN = {
    "strict-transport-security": "max-age=31536000; includeSubDomains; preload",
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
    "content-security-policy": ("default-src 'self'; object-src 'none'; base-uri 'self'; "
                                "frame-ancestors 'none'; "
                                "frame-src https://challenges.cloudflare.com; "
                                "form-action 'self' https://abos.franksfinanzcheck.de"),
}

# Cloudflare kennzeichnet eine proxied Zone; ohne diese Spur kann A1 nicht
# wirken – genau daran hängt die Diagnose des Berichts.
PROXY_KENNUNG = {"cf-ray": "9a1b2c3d4e5f6a7b-FRA", "server": "cloudflare"}


class _Probe:
    """Netz-Attrappe für den Selbsttest: spielt eine Ablaufliste ab und zählt mit."""

    def __init__(self, ablauf):
        self.ablauf = list(ablauf)
        self.aufrufe: list[tuple[str, str]] = []

    def holen(self, url, weg):
        self.aufrufe.append((url, weg))
        index = min(len(self.aufrufe) - 1, len(self.ablauf) - 1)
        schritt = self.ablauf[index]
        if isinstance(schritt, BaseException):
            raise schritt
        return schritt

    @property
    def anzahl(self) -> int:
        return len(self.aufrufe)

    @property
    def wege(self) -> list[str]:
        return [w for _, w in self.aufrufe]


def _ein_ziel() -> list[str]:
    return [ZIELE[0]]


def selftest() -> int:
    gut = dict(GUTE_KOPFZEILEN)
    faelle = 0

    f, w, v = befunde_fuer(gut)
    assert not f, f"Vollständige Header wurden beanstandet: {f}"
    faelle += 1

    # Gegenprobe 1: gar keine Header (der Zustand vor dem Fix).
    f, _, _ = befunde_fuer({})
    assert len(f) == 5, f"Leere Antwort muss alle fünf Pflicht-Header melden, nicht {len(f)}"
    faelle += 1

    # Gegenprobe 2: HSTS zu kurz.
    f, _, _ = befunde_fuer({**gut, "strict-transport-security": "max-age=300"})
    assert any("max-age" in x for x in f), "Kurze HSTS-Frist nicht erkannt"
    faelle += 1

    # Gegenprobe 3: Clickjacking-Schutz aufgehoben.
    for boese in ("ALLOWALL", "SAMEORIGIN2"):
        f, _, _ = befunde_fuer({**gut, "x-frame-options": boese})
        assert any("x-frame-options" in x for x in f), f"{boese} nicht erkannt"
        faelle += 1

    # Gegenprobe 4: CSP ohne frame-ancestors.
    f, _, _ = befunde_fuer({**gut, "content-security-policy": "default-src 'self'"})
    assert any("frame-ancestors" in x for x in f), "Unvollständige CSP nicht erkannt"
    faelle += 1

    # Gegenprobe 5: unsafe-eval.
    f, _, _ = befunde_fuer({**gut, "content-security-policy":
                            gut["content-security-policy"] + "; script-src 'self' 'unsafe-eval'"})
    assert any("unsafe-eval" in x for x in f), "unsafe-eval nicht erkannt"
    faelle += 1

    # Gegenprobe 6: fehlendes form-action / frame-src nur Warnung, kein Fehler.
    f, w, _ = befunde_fuer({**gut, "content-security-policy":
                            "default-src 'self'; object-src 'none'; base-uri 'self'; "
                            "frame-ancestors 'none'"})
    assert not f and any("frame-src" in x for x in w), "frame-src-Hinweis fehlt"
    assert any("form-action" in x for x in w), "form-action-Hinweis fehlt"
    faelle += 1

    # Positiv: Optionale Header werden nicht als Fehler geführt.
    f, _, _ = befunde_fuer({**gut, "permissions-policy": "camera=()",
                            "cross-origin-opener-policy": "same-origin",
                            "cross-origin-resource-policy": "same-origin"})
    assert not f, "Optionale Header dürfen keinen Fehler erzeugen"
    faelle += 1

    code, bericht = offline_pruefen()
    assert code == 0, f"Offline-Prüfung des echten Stands fehlgeschlagen:\n{bericht}"
    faelle += 1

    # ------------------------------------------------------------------
    #  Ab hier: die Netz-Klassen. Das ist die eigentliche WF-E813-Lehre —
    #  eine Wache, die „nicht gemessen“ als „Befund“ meldet, ist schlimmer
    #  als keine Wache. Jede Klasse hat eine eigene Gegenprobe.
    # ------------------------------------------------------------------

    # Fall 10: Vollständige Header über das Netz → grün.
    probe = _Probe([(200, {**PROXY_KENNUNG, **gut})])
    code, bericht, daten = netz_pruefen(holen=probe.holen, pausen=(),
                                        schlaf=lambda _: None, ziele=_ein_ziel())
    assert code == EXIT_OK, f"Saubere Seite muss grün sein:\n{bericht}"
    assert daten["klasse"] == KLASSE_OK, daten["klasse"]
    assert daten["fehlend"] == []
    faelle += 1

    # Fall 11: STOERUNG – kein Ziel erreichbar. Der Kern von WF-E813:
    # Eine Netzstörung darf NICHT als fehlender Header gemeldet werden.
    stoerung = OSError("TLS/SSL connection has been closed (EOF)")
    probe = _Probe([stoerung])
    code, bericht, daten = netz_pruefen(holen=probe.holen, pausen=(),
                                        schlaf=lambda _: None, ziele=_ein_ziel())
    assert code == EXIT_STOERUNG, f"Unmessbare Seite muss STOERUNG sein, nicht {code}"
    assert daten["klasse"] == KLASSE_STOERUNG, daten["klasse"]
    assert daten["gemessen"] == 0
    assert daten["nicht_gemessen"] == _ein_ziel()
    assert daten["fehlend"] == [], ("Eine Netzstörung darf nie in die Liste der "
                                    "fehlenden Header wandern (WF-E813)")
    assert daten["stoerung"], "Die Störung muss benannt werden"
    assert "kein Header-Befund" in bericht, f"Bericht verheimlicht die Klasse:\n{bericht}"
    assert "fehlen oder sind falsch" not in bericht, (
        "Der Bericht behauptet fehlende Header, obwohl nichts gemessen wurde "
        "(genau dieser Satz hat WF-E813 ausgelöst)")
    faelle += 1

    # Fall 12: Selbstheilung – der erste Versuch bricht ab, der zweite
    # liefert saubere Header. Genau der TLS-Schluckauf von WF-E813.
    probe = _Probe([stoerung, stoerung, (200, {**PROXY_KENNUNG, **gut})])
    code, bericht, daten = netz_pruefen(holen=probe.holen, pausen=(0.0,),
                                        schlaf=lambda _: None, ziele=_ein_ziel())
    assert code == EXIT_OK, f"Ein transienter Fehler muss sich selbst heilen:\n{bericht}"
    assert daten["klasse"] == KLASSE_OK, daten["klasse"]
    assert probe.anzahl == 3, f"Erwartet: HEAD, GET, HEAD(2. Versuch) – war {probe.wege}"
    faelle += 1

    # Fall 13: TEILWEISE – ein Ziel sauber, das andere nicht erreichbar.
    # Kein Alarm (die Regel gilt je Host), aber das tote Ziel wird genannt.
    def teilweise(url, weg):
        if url == ZIELE[0]:
            return (200, {**PROXY_KENNUNG, **gut})
        raise OSError("Name or service not known")
    code, bericht, daten = netz_pruefen(holen=teilweise, pausen=(),
                                        schlaf=lambda _: None)
    assert code == EXIT_OK, f"Ein sauber gemessener Host darf nicht alarmieren:\n{bericht}"
    assert daten["klasse"] == KLASSE_TEILWEISE, daten["klasse"]
    assert daten["nicht_gemessen"] == [ZIELE[1]]
    assert ZIELE[1] in bericht, "Das nicht gemessene Ziel muss im Bericht stehen"
    faelle += 1

    # Fall 14: Ein Ziel mit echtem Befund, das andere nicht erreichbar.
    # Der echte Befund sticht – er darf nicht von der Störung verdeckt werden.
    def befund_und_stoerung(url, weg):
        if url == ZIELE[0]:
            return (200, {**PROXY_KENNUNG, "x-content-type-options": "nosniff"})
        raise OSError("Connection reset by peer")
    code, bericht, daten = netz_pruefen(holen=befund_und_stoerung, pausen=(),
                                        schlaf=lambda _: None)
    assert code == EXIT_BEFUND, f"Ein gemessener Befund muss rot sein:\n{bericht}"
    assert daten["klasse"] == KLASSE_BEFUND, daten["klasse"]
    assert daten["gemessen"] == 1
    assert any(ZIELE[0] in f for f in daten["fehlend"])
    assert daten["nicht_gemessen"] == [ZIELE[1]]
    faelle += 1

    # Fall 15: Diagnose „Proxy fehlt“ – die Zone liegt nicht hinter
    # Cloudflare, die Regel aus A1 kann gar nicht wirken.
    probe = _Probe([(200, {"server": "GitHub.com"})])
    code, bericht, daten = netz_pruefen(holen=probe.holen, pausen=(),
                                        schlaf=lambda _: None, ziele=_ein_ziel())
    assert code == EXIT_BEFUND
    assert daten["proxy"] == PROXY_FEHLT, daten["proxy"]
    assert "Proxied" in daten["naechster_schritt"], daten["naechster_schritt"]
    assert "A1 Schritt 1" in daten["naechster_schritt"], daten["naechster_schritt"]
    assert "kann die Regel nicht wirken" in bericht or "gar nicht wirken" in bericht
    faelle += 1

    # Fall 16: Diagnose „Proxy aktiv, Regel unvollständig“ – ein völlig
    # anderer nächster Schritt als in Fall 15.
    probe = _Probe([(200, {**PROXY_KENNUNG, "content-security-policy": "default-src 'self'",
                           "x-content-type-options": "nosniff",
                           "x-frame-options": "DENY",
                           "referrer-policy": "strict-origin-when-cross-origin",
                           "strict-transport-security": "max-age=300"})])
    code, bericht, daten = netz_pruefen(holen=probe.holen, pausen=(),
                                        schlaf=lambda _: None, ziele=_ein_ziel())
    assert code == EXIT_BEFUND
    assert daten["proxy"] == PROXY_AKTIV, daten["proxy"]
    assert "FF Sicherheits-Header" in daten["naechster_schritt"], daten["naechster_schritt"]
    assert "Proxied" not in daten["naechster_schritt"], (
        "Bei aktivem Proxy darf der Rat nicht zum Proxy-Einschalten wechseln")
    faelle += 1

    # Fall 17: HEAD wird mit einem Fehlerstatus beantwortet – die Wache
    # fragt per GET nach, statt daraus einen Befund zu bauen.
    def head_verboten(url, weg):
        if weg == "HEAD":
            return (405, {"server": "cloudflare"})
        return (200, {**PROXY_KENNUNG, **gut})
    code, bericht, daten = netz_pruefen(holen=head_verboten, pausen=(),
                                        schlaf=lambda _: None, ziele=_ein_ziel())
    assert code == EXIT_OK, f"GET-Fallback muss greifen:\n{bericht}"
    assert daten["ziele"][0]["weg"] == "GET", daten["ziele"][0]["weg"]
    faelle += 1

    # Fall 18: Retry-Erschöpfung wird protokolliert – der Mensch muss im
    # Bericht sehen, wie oft versucht wurde und woran es scheiterte.
    probe = _Probe([stoerung])
    code, bericht, daten = netz_pruefen(holen=probe.holen, pausen=(0.0, 0.0),
                                        schlaf=lambda _: None, ziele=_ein_ziel())
    assert code == EXIT_STOERUNG
    assert daten["ziele"][0]["versuche"] == 3, daten["ziele"][0]["versuche"]
    assert "Versuch 3" in bericht, "Das Versuchsprotokoll fehlt im Bericht"
    faelle += 1

    # #809: Auch eine erreichbare Fehler-/Challenge-Seite ist keine
    # erfolgreiche Messung der Website. Sie darf nicht als Header-Befund
    # oder (mit zufällig guten Headern) als geheilt gelten.
    for status in (403, 429, 503):
        probe = _Probe([(status, {**PROXY_KENNUNG, **gut})])
        code, _, daten = netz_pruefen(holen=probe.holen, pausen=(),
                                      schlaf=lambda _: None, ziele=_ein_ziel())
        assert code == EXIT_STOERUNG and daten["gemessen"] == 0 and not daten["fehlend"]
        faelle += 1

    print(f"✅ SELBSTTEST OK — {faelle} Fälle grün (Pflicht-Header, CSP-Anweisungen, "
          "Clickjacking, HSTS-Frist, Repo-Stand, Netz-Klassen BEFUND/STOERUNG/"
          "TEILWEISE, Selbstheilung, GET-Fallback, Proxy-Diagnose).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prüft die Sicherheits-Header der Seite (F-01).")
    parser.add_argument("--selftest", action="store_true", help="prüft die Prüfung (ohne Netz)")
    parser.add_argument("--offline", action="store_true", help="nur Repo-Stand prüfen")
    parser.add_argument("--json", action="store_true", help="Befunde als JSON")
    parser.add_argument("--report", metavar="PFAD",
                        help="schreibt den Markdown-Bericht zusätzlich in diese Datei")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    if args.offline:
        code, bericht = offline_pruefen()
        daten = {"exit": code, "klasse": "OFFLINE", "bericht": bericht}
    else:
        code, bericht, daten = netz_pruefen()
    daten["bericht"] = bericht

    if args.report:
        Path(args.report).write_text(bericht, encoding="utf-8")

    if args.json:
        print(json.dumps(daten, ensure_ascii=False, indent=2))
    else:
        print(bericht)
    return code


if __name__ == "__main__":
    sys.exit(main())
